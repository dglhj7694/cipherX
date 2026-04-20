import argparse
import json
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, time as dt_time
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import yfinance as yf

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import DEFAULT_BIAS_MODE, resolve_bias_mode
from engine import _ensure_runtime_combo_registry, detect_all_signals
from indicators import compute_indicators
from scripts.daily_scan_and_notify import (
    _safe_float,
    build_scan_universe,
    send_telegram_document,
    send_telegram_message,
    split_tickers_for_shard,
)

KST = ZoneInfo("Asia/Seoul")
US_EASTERN = ZoneInfo("America/New_York")
US_MARKET_OPEN_ET = dt_time(9, 30)

DEFAULT_SCAN_LABEL = "프리마켓 실시간 스캔"
DEFAULT_MIN_TURNOVER_PCT = 0.001
DEFAULT_DOLLAR_FLOOR_EARLY = 20_000.0
DEFAULT_DOLLAR_FLOOR_MID = 40_000.0
DEFAULT_DOLLAR_FLOOR_LATE = 80_000.0

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("premarket_rt")


@dataclass
class PMScanResult:
    rows: list[dict[str, Any]]
    skips: list[dict[str, str]]
    perf: dict[str, Any]


def _premarket_min_dollar_floor(
    run_at_kst: datetime,
    *,
    dollar_floor_early: float,
    dollar_floor_mid: float,
    dollar_floor_late: float,
) -> float:
    """ET 기준 시간대별 최소 프리마켓 거래대금."""
    us_now = run_at_kst.astimezone(US_EASTERN)
    now_t = us_now.time()
    if now_t < dt_time(6, 0):
        return float(dollar_floor_early)
    if now_t < dt_time(8, 0):
        return float(dollar_floor_mid)
    if now_t < US_MARKET_OPEN_ET:
        return float(dollar_floor_late)
    return float(dollar_floor_late)


def _group_sort_key(row: dict[str, Any]) -> tuple[float, float, float, str]:
    effective_dollar = _safe_float(row.get("effective_dollar_volume", row.get("dollar_volume", 0.0)))
    turnover_pct = _safe_float(row.get("mcap_turnover_pct", row.get("mcap_ratio", 0.0)))
    gap_abs = abs(_safe_float(row.get("gap_pct", 0.0)))
    ticker = str(row.get("ticker", "")).strip().upper()
    return (-effective_dollar, -turnover_pct, -gap_abs, ticker)


def fetch_and_synthesize_daily(ticker: str) -> tuple[pd.DataFrame | None, dict[str, Any] | None]:
    tkr = yf.Ticker(ticker)

    hist = tkr.history(period="1y", interval="1d", auto_adjust=True)
    if hist is None or hist.empty:
        return None, {"error": "no_daily_history"}

    intra = tkr.history(period="1d", interval="5m", prepost=True)
    if intra is None or intra.empty:
        return None, {"error": "no_intraday_data"}

    us_now = datetime.now(US_EASTERN)
    today_date = us_now.date()
    market_open = datetime.combine(today_date, US_MARKET_OPEN_ET, tzinfo=US_EASTERN)
    if intra.index.tz is not None:
        market_open = market_open.astimezone(intra.index.tz)
    intra_pm = intra[intra.index < pd.Timestamp(market_open)]
    if intra_pm.empty:
        return None, {"error": "no_premarket_data_found_in_intraday"}

    pm_open = _safe_float(intra_pm["Open"].iloc[0])
    pm_high = _safe_float(intra_pm["High"].max())
    pm_low = _safe_float(intra_pm["Low"].min())
    pm_close = _safe_float(intra_pm["Close"].iloc[-1])
    pm_volume_yf = _safe_float(intra_pm["Volume"].sum())

    intra_pm = intra_pm.copy()
    intra_pm["Typical_Price"] = (intra_pm["High"] + intra_pm["Low"] + intra_pm["Close"]) / 3.0
    intra_pm["VP"] = intra_pm["Typical_Price"] * intra_pm["Volume"]
    cum_vp = intra_pm["VP"].cumsum()
    cum_vol = intra_pm["Volume"].cumsum()
    pm_vwap = _safe_float((cum_vp / cum_vol).iloc[-1]) if _safe_float(cum_vol.iloc[-1]) > 0 else pm_close

    clean_hist = hist[hist.index.date < today_date]
    prev_close = _safe_float(clean_hist["Close"].iloc[-1]) if not clean_hist.empty else pm_open
    prev_high = _safe_float(clean_hist["High"].iloc[-1]) if not clean_hist.empty else pm_high

    gap_pct = ((pm_open - prev_close) / prev_close * 100.0) if prev_close > 0 else 0.0
    change_pct = ((pm_close - prev_close) / prev_close * 100.0) if prev_close > 0 else 0.0

    fast_info = getattr(tkr, "fast_info", {}) or {}
    market_cap = _safe_float(fast_info.get("marketCap", 0))

    today_idx_tz = clean_hist.index.tz if not clean_hist.empty else "America/New_York"
    today_dt = pd.to_datetime(today_date).tz_localize(today_idx_tz)
    synthetic_row = pd.DataFrame(
        {
            "Open": [pm_open],
            "High": [max(prev_high, pm_high)],
            "Low": [pm_low],
            "Close": [pm_close],
            "Volume": [pm_volume_yf],
        },
        index=[today_dt],
    )
    combined_hist = pd.concat([clean_hist, synthetic_row])

    metrics = {
        "pm_open": pm_open,
        "pm_high": pm_high,
        "pm_low": pm_low,
        "pm_close": pm_close,
        "pm_vwap": pm_vwap,
        "prev_close": prev_close,
        "prev_high": prev_high,
        "gap_pct": gap_pct,
        "change_pct": change_pct,
        "market_cap": market_cap,
        "pm_volume_yf": pm_volume_yf,
        "pm_volume_tv": 0.0,
        "pm_volume_effective": pm_volume_yf,
        "pm_volume_source": "yfinance" if pm_volume_yf > 0 else "none",
    }
    _apply_effective_volume_metrics(metrics)
    return combined_hist, metrics


def _apply_effective_volume_metrics(metrics: dict[str, Any]) -> None:
    pm_volume_effective = _safe_float(metrics.get("pm_volume_effective", 0.0))
    pm_vwap = _safe_float(metrics.get("pm_vwap", 0.0))
    market_cap = _safe_float(metrics.get("market_cap", 0.0))
    effective_dollar_volume = pm_vwap * pm_volume_effective
    mcap_turnover_pct = (effective_dollar_volume / market_cap * 100.0) if market_cap > 0 else 0.0

    metrics["effective_dollar_volume"] = effective_dollar_volume
    metrics["mcap_turnover_pct"] = mcap_turnover_pct

    # Backward compatibility aliases.
    metrics["pm_volume"] = pm_volume_effective
    metrics["dollar_volume"] = effective_dollar_volume
    metrics["mcap_ratio"] = mcap_turnover_pct


def _apply_tv_volume_fallback(metrics: dict[str, Any], tv_volume: float) -> None:
    pm_volume_yf = _safe_float(metrics.get("pm_volume_yf", 0.0))
    pm_volume_tv = max(_safe_float(tv_volume), 0.0)
    if pm_volume_yf > 0:
        pm_volume_effective = pm_volume_yf
        source = "yfinance"
    elif pm_volume_tv > 0:
        pm_volume_effective = pm_volume_tv
        source = "tradingview"
    else:
        pm_volume_effective = 0.0
        source = "none"

    metrics["pm_volume_yf"] = pm_volume_yf
    metrics["pm_volume_tv"] = pm_volume_tv
    metrics["pm_volume_effective"] = pm_volume_effective
    metrics["pm_volume_source"] = source
    _apply_effective_volume_metrics(metrics)


def fetch_tv_pm_volumes(tickers: list[str]) -> dict[str, float]:
    if not tickers:
        return {}
    try:
        url = "https://scanner.tradingview.com/america/scan"
        req = {
            "filter": [{"left": "name", "operation": "in_range", "right": tickers}],
            "columns": ["name", "premarket_volume"],
            "range": [0, len(tickers) + 50],
        }
        res = requests.post(url, json=req, timeout=10).json()
        return {
            str(item["d"][0]).strip().upper(): _safe_float(item["d"][1])
            for item in res.get("data", [])
        }
    except Exception as exc:
        logger.warning("Failed to fetch TradingView premarket volumes: %s", exc)
        return {}


def _passes_liquidity_gate(
    metrics: dict[str, Any],
    *,
    min_dollar_volume: float,
    min_turnover_pct: float,
) -> tuple[bool, str]:
    effective_dollar = _safe_float(metrics.get("effective_dollar_volume", 0.0))
    turnover_pct = _safe_float(metrics.get("mcap_turnover_pct", 0.0))
    min_dollar = max(_safe_float(min_dollar_volume), 0.0)
    min_turnover = max(_safe_float(min_turnover_pct), 0.0)

    if effective_dollar < min_dollar:
        return False, f"low_effective_dollar_volume ({effective_dollar:.1f} < {min_dollar:.1f})"

    required_turnover = min_turnover
    if effective_dollar >= 3.0 * min_dollar:
        required_turnover = 0.0
    if required_turnover > 0 and turnover_pct < required_turnover:
        return False, f"low_mcap_turnover ({turnover_pct:.6f}% < {required_turnover:.6f}%)"

    return True, ""


def _build_pm_scanner_row(
    ticker: str,
    bias_mode: str,
    *,
    min_dollar_volume: float = 0.0,
    min_turnover_pct: float = DEFAULT_MIN_TURNOVER_PCT,
    tv_volume: float = 0.0,
) -> dict[str, Any]:
    ticker = str(ticker or "").strip().upper()
    if not ticker:
        return {"ok": False, "ticker": "", "skip_reason": "invalid_ticker"}

    combined_hist, metrics = fetch_and_synthesize_daily(ticker)
    if combined_hist is None or metrics is None:
        err = metrics.get("error", "fetch_error") if metrics else "unknown_error"
        return {"ok": False, "ticker": ticker, "skip_reason": err}

    _apply_tv_volume_fallback(metrics, tv_volume)
    if len(combined_hist) < 50:
        return {
            "ok": False,
            "ticker": ticker,
            "skip_reason": "insufficient_history",
            "detail": f"bars={len(combined_hist)}",
        }

    is_liquid, liquidity_reason = _passes_liquidity_gate(
        metrics,
        min_dollar_volume=min_dollar_volume,
        min_turnover_pct=min_turnover_pct,
    )
    if not is_liquid:
        return {"ok": False, "ticker": ticker, "skip_reason": liquidity_reason}

    try:
        indicator_frame = compute_indicators(combined_hist)
        _ensure_runtime_combo_registry()
        signal_frame = detect_all_signals(indicator_frame, bias_mode=resolve_bias_mode(bias_mode))
        latest = signal_frame.iloc[-1]
        recent_real = signal_frame.iloc[-4:-1] if len(signal_frame) >= 4 else signal_frame.iloc[:-1]
        prev = signal_frame.iloc[-2] if len(signal_frame) > 1 else latest
        prev2 = signal_frame.iloc[-3] if len(signal_frame) > 2 else prev

        def _any_recent(col: str) -> bool:
            if col not in recent_real.columns:
                return False
            try:
                return bool(recent_real[col].fillna(False).astype(bool).any())
            except Exception:
                return False

        ut_turn_bull = _any_recent("UTBot_Buy")
        ut_turn_bear = _any_recent("UTBot_Sell")
        hull_turn_bull = _any_recent("Hull_Turn_Bull")
        hull_turn_bear = _any_recent("Hull_Turn_Bear")
        prev_hull_bull = bool(
            prev.get("Hull_Turn_Bull", False)
            or prev.get("Hull_Trend", "") == "bullish"
            or prev2.get("Hull_Turn_Bull", False)
            or prev2.get("Hull_Trend", "") == "bullish"
        )
        prev_uptrend = bool(_safe_float(prev.get("Close", 0)) > _safe_float(prev.get("MA20", 0)))
        new_52w_high = bool(
            latest.get("New_52W_High", False)
            or prev.get("New_52W_High", False)
            or prev2.get("New_52W_High", False)
        )

        row = {
            "ticker": ticker,
            **metrics,
            "ut_turn_bull": ut_turn_bull,
            "ut_turn_bear": ut_turn_bear,
            "hull_turn_bull": hull_turn_bull,
            "hull_turn_bear": hull_turn_bear,
            "prev_hull_bull": prev_hull_bull,
            "new_52w_high": new_52w_high,
            "es": _safe_float(latest.get("Ensemble_Score", 0)),
            "cf": _safe_float(latest.get("Judgment_Confidence", 0)),
            "liquidity_min_dollar": _safe_float(min_dollar_volume),
            "liquidity_min_turnover_pct": _safe_float(min_turnover_pct),
        }

        is_pm_strong = (
            row["gap_pct"] > 0
            and row["pm_close"] >= row["pm_vwap"]
            and row["pm_close"] > row["prev_high"]
        )

        if is_pm_strong:
            row["group"] = "G1_PR_STRONG"
        elif ut_turn_bull or hull_turn_bull:
            row["group"] = "G2_BUY_TURN"
        elif ut_turn_bear or hull_turn_bear:
            row["group"] = "G3_SELL_TURN"
        elif (prev_hull_bull or prev_uptrend) and (row["pm_close"] >= row["pm_vwap"]) and row["change_pct"] > -1.0:
            row["group"] = "G4_PULLBACK_HOLD"
        elif new_52w_high and row["change_pct"] > 0 and row["pm_close"] >= row["pm_vwap"]:
            row["group"] = "G5_NEW_HIGH_CHALLENGE"
        elif row["es"] >= 2.0 and row["cf"] >= 4.0:
            row["group"] = "G6_WATCHLIST"
        else:
            return {"ok": False, "ticker": ticker, "skip_reason": "no_group_matched"}

        return {"ok": True, "ticker": ticker, "row": row}
    except Exception as exc:
        return {"ok": False, "ticker": ticker, "skip_reason": "engine_error", "detail": str(exc)[:200]}


def _scan_ticker_worker(
    ticker: str,
    bias_mode: str,
    min_dollar_volume: float,
    min_turnover_pct: float,
    tv_volume: float,
) -> dict[str, Any]:
    started = time.perf_counter()
    payload = _build_pm_scanner_row(
        ticker,
        bias_mode,
        min_dollar_volume=min_dollar_volume,
        min_turnover_pct=min_turnover_pct,
        tv_volume=tv_volume,
    )
    payload["elapsed_sec"] = _safe_float(time.perf_counter() - started)
    return payload


def scan_universe(
    tickers: list[str],
    max_workers: int,
    bias_mode: str,
    min_dollar_volume: float,
    min_turnover_pct: float,
) -> PMScanResult:
    run_started = time.perf_counter()
    results: list[dict[str, Any]] = []
    skip_reasons: list[dict[str, str]] = []
    if not tickers:
        return PMScanResult(rows=[], skips=[], perf={"workers": 0, "total_seconds": 0.0, "ticker_count": 0})

    effective_workers = min(max_workers, max(1, len(tickers)))
    logger.info("Fetching TradingView fallback volumes for %s tickers...", len(tickers))
    tv_volumes = fetch_tv_pm_volumes(tickers)
    tv_nonzero_count = sum(1 for value in tv_volumes.values() if _safe_float(value) > 0)

    with ThreadPoolExecutor(max_workers=effective_workers) as executor:
        futures = {
            executor.submit(
                _scan_ticker_worker,
                ticker,
                bias_mode,
                min_dollar_volume,
                min_turnover_pct,
                tv_volumes.get(ticker, 0.0),
            ): ticker
            for ticker in tickers
        }
        for future in as_completed(futures):
            done_ticker = futures[future]
            try:
                payload = future.result()
                if payload.get("ok") and isinstance(payload.get("row"), dict):
                    results.append(payload["row"])
                else:
                    skip_reasons.append(
                        {
                            "ticker": done_ticker,
                            "reason": str(payload.get("skip_reason")),
                            "detail": str(payload.get("detail", "")),
                        }
                    )
            except Exception as exc:
                skip_reasons.append({"ticker": done_ticker, "reason": "future_error", "detail": str(exc)[:220]})

    fallback_applied_count = sum(1 for row in results if str(row.get("pm_volume_source", "")) == "tradingview")
    perf_stats = {
        "workers": effective_workers,
        "total_seconds": _safe_float(time.perf_counter() - run_started),
        "ticker_count": len(tickers),
        "match_count": len(results),
        "skip_count": len(skip_reasons),
        "tv_nonzero_count": tv_nonzero_count,
        "fallback_applied_count": fallback_applied_count,
        "tv_fetch_success": bool(tv_volumes),
    }
    return PMScanResult(rows=results, skips=skip_reasons, perf=perf_stats)


def _fmt_row(row: dict[str, Any]) -> str:
    ticker = str(row.get("ticker", "UNKN"))
    gap = _safe_float(row.get("gap_pct", 0))
    chg = _safe_float(row.get("change_pct", 0))
    effective_dollar = _safe_float(row.get("effective_dollar_volume", row.get("dollar_volume", 0.0)))
    turnover_pct = _safe_float(row.get("mcap_turnover_pct", row.get("mcap_ratio", 0.0)))
    pm_volume_effective = _safe_float(row.get("pm_volume_effective", row.get("pm_volume", 0.0)))
    source = str(row.get("pm_volume_source", "none"))

    sign_gap = "+" if gap > 0 else ""
    sign_chg = "+" if chg > 0 else ""
    return (
        f"{ticker} | 갭 {sign_gap}{gap:.1f}% / 등락 {sign_chg}{chg:.1f}%"
        f" | 거래량 {pm_volume_effective:,.0f} ({source})"
        f" | 거래대금 ${effective_dollar / 1000.0:,.0f}k"
        f" | 시총대비 {turnover_pct:.4f}%"
    )


def format_telegram_summary(
    rows: list[dict[str, Any]],
    run_at_kst: datetime,
    universe_count: int,
    *,
    scan_label: str = DEFAULT_SCAN_LABEL,
) -> str:
    g1 = [r for r in rows if r.get("group") == "G1_PR_STRONG"]
    g2 = [r for r in rows if r.get("group") == "G2_BUY_TURN"]
    g3 = [r for r in rows if r.get("group") == "G3_SELL_TURN"]
    g4 = [r for r in rows if r.get("group") == "G4_PULLBACK_HOLD"]
    g5 = [r for r in rows if r.get("group") == "G5_NEW_HIGH_CHALLENGE"]
    g6 = [r for r in rows if r.get("group") == "G6_WATCHLIST"]

    lines = [
        f"[{str(scan_label or DEFAULT_SCAN_LABEL)}] {run_at_kst.strftime('%Y-%m-%d %H:%M:%S')} KST",
        "- 프리마켓 5분봉 + 실시간 거래량 보강(TradingView fallback) 기반",
        f"- 유니버스: {universe_count}개 | 선별: {len(rows)}개",
        "",
    ]

    sections = [
        ("🔥 프리마켓 강세 (갭+VWAP+전고점)", g1),
        ("🟢 매수 전환 (UTBot/HULL)", g2),
        ("🔴 매도 전환 (UTBot/HULL)", g3),
        ("🌙 눌림 유지 (전일 추세 + PM VWAP)", g4),
        ("⭐ 52주 고가 도전", g5),
        ("👀 Watchlist", g6),
    ]

    for title, group_rows in sections:
        sorted_rows = sorted(group_rows, key=_group_sort_key)
        lines.append(f"=== {title} ({len(sorted_rows)}개) ===")
        if not sorted_rows:
            lines.append("- 해당 종목 없음")
        else:
            for idx, row in enumerate(sorted_rows[:15], start=1):
                lines.append(f"{idx}. {_fmt_row(row)}")
            if len(sorted_rows) > 15:
                lines.append(f"... 외 {len(sorted_rows) - 15}개")
        lines.append("")

    return "\n".join(lines).strip()


def merge_shard_scan_rows(merge_dir: Path) -> list[dict[str, Any]]:
    all_rows: list[dict[str, Any]] = []
    files = sorted(Path(merge_dir).glob("**/scan_rows_*.json"))
    for file_path in files:
        with file_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
            if isinstance(data, list):
                all_rows.extend(data)

    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for row in all_rows:
        ticker = str(row.get("ticker", "")).strip().upper()
        if ticker and ticker not in seen:
            seen.add(ticker)
            deduped.append(row)
    return deduped


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser("Realtime Premarket Scan")
    parser.add_argument("--out-dir", default="artifacts/pm1800_scan", help="Output directory")
    parser.add_argument("--max-workers", type=int, default=12)
    parser.add_argument("--bias-mode", default=DEFAULT_BIAS_MODE)
    parser.add_argument("--skip-telegram", action="store_true")
    parser.add_argument("--shard-count", type=int, default=1)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--merge-dir", default="", help="Directory with shard json to merge")
    parser.add_argument("--universe-profile", default="default")
    parser.add_argument("--scan-label", default=DEFAULT_SCAN_LABEL)
    parser.add_argument("--min-turnover-pct", type=float, default=DEFAULT_MIN_TURNOVER_PCT)
    parser.add_argument("--dollar-floor-early", type=float, default=DEFAULT_DOLLAR_FLOOR_EARLY)
    parser.add_argument("--dollar-floor-mid", type=float, default=DEFAULT_DOLLAR_FLOOR_MID)
    parser.add_argument("--dollar-floor-late", type=float, default=DEFAULT_DOLLAR_FLOOR_LATE)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    run_at_kst = datetime.now(KST)

    if args.merge_dir:
        merge_dir = Path(args.merge_dir)
        logger.info("Merging shards from %s", merge_dir)
        rows = merge_shard_scan_rows(merge_dir)
        summary_text = format_telegram_summary(rows, run_at_kst, -1, scan_label=args.scan_label)

        summary_path = out_dir / "premarket_summary.txt"
        summary_path.write_text(summary_text, encoding="utf-8")
        csv_path = out_dir / "premarket_results.csv"
        df = pd.DataFrame(rows)
        if not df.empty:
            df.to_csv(csv_path, index=False)

        if not args.skip_telegram:
            token = str(os.getenv("TELEGRAM_BOT_TOKEN", "")).strip()
            chat_id = str(os.getenv("TELEGRAM_CHAT_ID", "")).strip()
            if token and chat_id:
                logger.info("Sending Telegram summary...")
                send_telegram_message(token, chat_id, summary_text)
                if not df.empty:
                    send_telegram_document(token, chat_id, csv_path, f"{args.scan_label} CSV")
        return

    logger.info("Shard %s/%s initialized.", args.shard_index, args.shard_count)
    universe_payload = build_scan_universe(universe_profile=args.universe_profile)
    full_tickers = list(universe_payload.get("tickers", []))
    tickers = split_tickers_for_shard(full_tickers, args.shard_count, args.shard_index)

    min_dollar_volume = _premarket_min_dollar_floor(
        run_at_kst,
        dollar_floor_early=args.dollar_floor_early,
        dollar_floor_mid=args.dollar_floor_mid,
        dollar_floor_late=args.dollar_floor_late,
    )
    min_turnover_pct = max(_safe_float(args.min_turnover_pct), 0.0)

    logger.info(
        "Shard tickers=%s, min_dollar=$%.0f, min_turnover=%.6f%%",
        len(tickers),
        min_dollar_volume,
        min_turnover_pct,
    )

    scan_result = scan_universe(
        tickers=tickers,
        max_workers=args.max_workers,
        bias_mode=args.bias_mode,
        min_dollar_volume=min_dollar_volume,
        min_turnover_pct=min_turnover_pct,
    )
    logger.info(
        "Completed scan. Matches=%s Skips=%s TV_nonzero=%s TV_fallback=%s",
        scan_result.perf.get("match_count", 0),
        scan_result.perf.get("skip_count", 0),
        scan_result.perf.get("tv_nonzero_count", 0),
        scan_result.perf.get("fallback_applied_count", 0),
    )

    json_path = out_dir / f"scan_rows_shard{args.shard_index}.json"
    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(scan_result.rows, handle, ensure_ascii=False, indent=2)

    meta_path = out_dir / f"run_meta_shard{args.shard_index}.json"
    meta_payload = {
        "run_at_kst": run_at_kst.isoformat(),
        "scan_label": str(args.scan_label),
        "shard_count": int(args.shard_count),
        "shard_index": int(args.shard_index),
        "universe_count": len(full_tickers),
        "shard_ticker_count": len(tickers),
        "min_dollar_volume": _safe_float(min_dollar_volume),
        "min_turnover_pct": _safe_float(min_turnover_pct),
        "performance": scan_result.perf,
    }
    meta_path.write_text(json.dumps(meta_payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
