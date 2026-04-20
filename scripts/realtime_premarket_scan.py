import argparse
import json
import logging
import math
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, time as dt_time, timedelta
from pathlib import Path
from typing import Any, Iterable, Mapping
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import yfinance as yf

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# engine, indicators, config from backend
from config import DEFAULT_BIAS_MODE, resolve_bias_mode
from engine import detect_all_signals
from indicators import compute_indicators
from sectors import SECTOR_GROUPS
from etf_sources import resolve_etf_universe
from scanner_csv import scanner_rows_to_csv_bytes

# reuse some utilities from daily_scan_and_notify
from scripts.daily_scan_and_notify import (
    _safe_float,
    _stable_shard_index,
    _ordered_unique,
    split_tickers_for_shard,
    build_scan_universe,
    split_telegram_message_text,
    send_telegram_document,
    send_telegram_message,
    _time_adjusted_volume_threshold,
)

KST = ZoneInfo("Asia/Seoul")
US_EASTERN = ZoneInfo("America/New_York")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("pm1800")

@dataclass
class PMScanResult:
    rows: list[dict[str, Any]]
    skips: list[dict[str, str]]
    perf: dict[str, Any]


def fetch_and_synthesize_daily(ticker: str) -> tuple[pd.DataFrame | None, dict[str, Any] | None]:
    """1년치 일봉 데이터와 오늘 치 프리장 데이터를 합성하여 가시적인 오늘 일봉 생성"""
    tkr = yf.Ticker(ticker)
    
    # 1. Fetch 1 year daily history
    hist = tkr.history(period="1y", interval="1d", auto_adjust=True)
    if hist is None or hist.empty:
        return None, {"error": "no_daily_history"}
        
    # 2. Fetch today's pre-market 5m data
    intra = tkr.history(period="1d", interval="5m", prepost=True)
    if intra is None or intra.empty:
        return None, {"error": "no_intraday_data"}
        
    us_now = datetime.now(US_EASTERN)
    today_date = us_now.date()
    
    market_open = pd.to_datetime(us_now.replace(hour=9, minute=30, second=0, microsecond=0))
    if intra.index.tz is not None:
        market_open = market_open.tz_convert(intra.index.tz) if market_open.tz is not None else market_open.tz_localize(intra.index.tz)
    
    # Calculate premarket specific metrics
    intra_pm = intra[intra.index < market_open]
        
    if intra_pm.empty:
        return None, {"error": "no_premarket_data_found_in_intraday"}

    pm_open = _safe_float(intra_pm["Open"].iloc[0])
    pm_high = _safe_float(intra_pm["High"].max())
    pm_low = _safe_float(intra_pm["Low"].min())
    pm_close = _safe_float(intra_pm["Close"].iloc[-1])
    pm_volume = _safe_float(intra_pm["Volume"].sum())
    
    # Calculate VWAP
    intra_pm = intra_pm.copy()
    intra_pm["Typical_Price"] = (intra_pm["High"] + intra_pm["Low"] + intra_pm["Close"]) / 3.0
    intra_pm["VP"] = intra_pm["Typical_Price"] * intra_pm["Volume"]
    cum_vp = intra_pm["VP"].cumsum()
    cum_vol = intra_pm["Volume"].cumsum()
    vwap_series = cum_vp / cum_vol
    pm_vwap = _safe_float(vwap_series.iloc[-1]) if cum_vol.iloc[-1] > 0 else pm_close
    
    # Clean historical dataframe to not include today if it mistakenly does
    clean_hist = hist[hist.index.date < today_date]
    
    prev_close = _safe_float(clean_hist["Close"].iloc[-1]) if not clean_hist.empty else pm_open
    prev_high = _safe_float(clean_hist["High"].iloc[-1]) if not clean_hist.empty else pm_high
    
    gap_pct = ((pm_open - prev_close) / prev_close * 100.0) if prev_close > 0 else 0.0
    change_pct = ((pm_close - prev_close) / prev_close * 100.0) if prev_close > 0 else 0.0
    dollar_volume = pm_vwap * pm_volume
    
    # Market cap approximation using fast_info
    market_cap = _safe_float(tkr.fast_info.get("marketCap", 0))
    mcap_ratio = (dollar_volume / market_cap * 100.0) if market_cap > 0 else 0.0
    
    # Create synthesized candle
    today_dt = pd.to_datetime(today_date).tz_localize(clean_hist.index.tz if not clean_hist.empty else "America/New_York")
    synthetic_row = pd.DataFrame({
        "Open": [pm_open],
        "High": [max(prev_high, pm_high)],
        "Low": [pm_low],
        "Close": [pm_close],
        "Volume": [pm_volume] # Only premarket volume is recorded for today 
    }, index=[today_dt])
    
    combined_hist = pd.concat([clean_hist, synthetic_row])
    
    metrics = {
        "pm_open": pm_open,
        "pm_high": pm_high,
        "pm_low": pm_low,
        "pm_close": pm_close,
        "pm_volume": pm_volume,
        "pm_vwap": pm_vwap,
        "prev_close": prev_close,
        "prev_high": prev_high,
        "gap_pct": gap_pct,
        "change_pct": change_pct,
        "dollar_volume": dollar_volume,
        "market_cap": market_cap,
        "mcap_ratio": mcap_ratio
    }
    
    return combined_hist, metrics

def _build_pm_scanner_row(ticker: str, bias_mode: str, min_dollar_volume: float = 0.0) -> dict[str, Any]:
    ticker = str(ticker or "").strip().upper()
    if not ticker:
        return {"ok": False, "ticker": "", "skip_reason": "invalid_ticker"}
        
    combined_hist, metrics = fetch_and_synthesize_daily(ticker)
    
    if combined_hist is None or metrics is None:
        err = metrics.get("error", "fetch_error") if metrics else "unknown_error"
        return {"ok": False, "ticker": ticker, "skip_reason": err}
        
    if len(combined_hist) < 50:
        return {"ok": False, "ticker": ticker, "skip_reason": "insufficient_history", "detail": f"bars={len(combined_hist)}"}

    try:
        indicator_frame = compute_indicators(combined_hist)
        from engine import _ensure_runtime_combo_registry
        _ensure_runtime_combo_registry()
        signal_frame = detect_all_signals(indicator_frame, bias_mode=resolve_bias_mode(bias_mode))
        
        latest = signal_frame.iloc[-1]
        prev = signal_frame.iloc[-2] if len(signal_frame) > 1 else latest
        
        # Extract necessary indicators for categorization
        ut_turn_bull = bool(latest.get("UTBot_Buy", False))
        ut_turn_bear = bool(latest.get("UTBot_Sell", False))
        hull_turn_bull = bool(latest.get("Hull_Turn_Bull", False))
        hull_turn_bear = bool(latest.get("Hull_Turn_Bear", False))
        
        # Check condition for 'pullback strong candidate'
        prev_hull_bull = bool(prev.get("Hull_Turn_Bull", False) or prev.get("Hull_Trend", "") == "bullish")
        prev_uptrend = bool(_safe_float(prev.get("Close", 0)) > _safe_float(prev.get("MA20", 0)))
        
        # New 52w high
        new_52w_high = bool(latest.get("New_52W_High", False) or prev.get("New_52W_High", False))
        
        es = _safe_float(latest.get("Ensemble_Score", 0))
        cf = _safe_float(latest.get("Judgment_Confidence", 0))
        
        row = {
            "ticker": ticker,
            **metrics,
            "ut_turn_bull": ut_turn_bull,
            "ut_turn_bear": ut_turn_bear,
            "hull_turn_bull": hull_turn_bull,
            "hull_turn_bear": hull_turn_bear,
            "prev_hull_bull": prev_hull_bull,
            "new_52w_high": new_52w_high,
            "es": es,
            "cf": cf
        }
        
        # Filter purely empty premarket early
        if metrics["dollar_volume"] < min_dollar_volume:
            return {"ok": False, "ticker": ticker, "skip_reason": f"low_volume ({metrics['dollar_volume']:.1f} < {min_dollar_volume})"}
            
        row["group"] = "None"
        
        is_pm_strong = (
            metrics["gap_pct"] > 0 and 
            metrics["pm_close"] > metrics["pm_vwap"] and 
            metrics["pm_close"] > metrics["prev_high"]
        )
        
        if is_pm_strong:
            row["group"] = "G1_PR_STRONG"
        elif ut_turn_bull or hull_turn_bull:
            row["group"] = "G2_BUY_TURN"
        elif ut_turn_bear or hull_turn_bear:
            row["group"] = "G3_SELL_TURN"
        elif (prev_hull_bull or prev_uptrend) and (metrics["pm_close"] >= metrics["pm_vwap"]) and metrics["change_pct"] > -1.0:
            row["group"] = "G4_PULLBACK_HOLD"
        elif new_52w_high and metrics["change_pct"] > 0 and metrics["pm_close"] > metrics["pm_vwap"]:
            row["group"] = "G5_NEW_HIGH_CHALLENGE"
        elif es >= 2.0 and cf >= 4.0:
            row["group"] = "G6_WATCHLIST"
        else:
            return {"ok": False, "ticker": ticker, "skip_reason": "no_group_matched"}
            
        return {"ok": True, "ticker": ticker, "row": row}
        
    except Exception as exc:
        return {"ok": False, "ticker": ticker, "skip_reason": "engine_error", "detail": str(exc)[:200]}

def _scan_ticker_worker(ticker: str, bias_mode: str, min_dollar_volume: float) -> dict[str, Any]:
    started = time.perf_counter()
    payload = _build_pm_scanner_row(ticker, bias_mode, min_dollar_volume)
    payload["elapsed_sec"] = _safe_float(time.perf_counter() - started)
    return payload

def scan_universe(tickers: list[str], max_workers: int, bias_mode: str, min_dollar_volume: float) -> PMScanResult:
    run_started = time.perf_counter()
    results: list[dict[str, Any]] = []
    skip_reasons: list[dict[str, str]] = []
    ticker_latencies: list[float] = []

    if not tickers:
        return PMScanResult(rows=[], skips=[], perf={"workers": 0, "total_seconds": 0.0, "ticker_count": 0})

    effective_workers = min(max_workers, max(1, len(tickers)))

    with ThreadPoolExecutor(max_workers=effective_workers) as executor:
        futures = {
            executor.submit(_scan_ticker_worker, ticker, bias_mode, min_dollar_volume): ticker
            for ticker in tickers
        }
        for future in as_completed(futures):
            done_ticker = futures[future]
            try:
                payload = future.result()
                if payload.get("ok") and isinstance(payload.get("row"), dict):
                    results.append(payload["row"])
                else:
                    skip_reasons.append({
                        "ticker": done_ticker, 
                        "reason": str(payload.get("skip_reason")), 
                        "detail": str(payload.get("detail", ""))
                    })
            except Exception as exc:
                skip_reasons.append({"ticker": done_ticker, "reason": "future_error", "detail": str(exc)[:220]})

    perf_stats = {
        "workers": effective_workers,
        "total_seconds": _safe_float(time.perf_counter() - run_started),
        "ticker_count": len(tickers),
        "match_count": len(results),
        "skip_count": len(skip_reasons),
    }
    return PMScanResult(rows=results, skips=skip_reasons, perf=perf_stats)

def _fmt_row(row: dict) -> str:
    ticker = row.get("ticker", "UNKN")
    gap = _safe_float(row.get("gap_pct", 0))
    chg = _safe_float(row.get("change_pct", 0))
    d_vol = _safe_float(row.get("dollar_volume", 0)) / 1_000
    m_ratio = _safe_float(row.get("mcap_ratio", 0)) * 100
    
    # 갭/등락 표기
    sign_gap = "+" if gap > 0 else ""
    sign_chg = "+" if chg > 0 else ""
    
    if m_ratio > 0:
        vol_info = f"${d_vol:.0f}k (시총대비 {m_ratio:.3f}%)"
    else:
        vol_info = f"${d_vol:.0f}k"
        
    return f"{ticker} | 갭 {sign_gap}{gap:.1f}% / 등락 {sign_chg}{chg:.1f}% | {vol_info}"

def format_telegram_summary(rows: list[dict], run_at_kst: datetime, universe_count: int) -> str:
    g1 = [r for r in rows if r["group"] == "G1_PR_STRONG"]
    g2 = [r for r in rows if r["group"] == "G2_BUY_TURN"]
    g3 = [r for r in rows if r["group"] == "G3_SELL_TURN"]
    g4 = [r for r in rows if r["group"] == "G4_PULLBACK_HOLD"]
    g5 = [r for r in rows if r["group"] == "G5_NEW_HIGH_CHALLENGE"]
    g6 = [r for r in rows if r["group"] == "G6_WATCHLIST"]
    
    lines = [
        f"[프리마켓 18시 리얼타임 스캔] {run_at_kst.strftime('%Y-%m-%d %H:%M:%S')} KST",
        f"- 프리장 실시간(5m) 및 가상 일봉 기반 평가",
        f"- 유니버스: {universe_count}개 | 포착: {len(rows)}개",
        ""
    ]
    
    sections = [
        ("🔥 프리장 강세 종목 (갭 + VWAP지지 + 전고개당)", g1),
        ("🟢 오늘 잠정 매수전환 (UTBot/HULL 상승반전 예상)", g2),
        ("🔴 오늘 잠정 매도전환 (UTBot/HULL 하락반전 ⚠️)", g3),
        ("🛡️ 눌림목 강세 후보 (전일 강세 + 프리장 VWAP 지지)", g4),
        ("🚀 신고가 도전 후보 (52W고가 근방 + 프리장 상승)", g5),
        ("👀 본장 선점 Watchlist (스코어 우수 + 체결강도 양호)", g6),
    ]
    
    for title, group_rows in sections:
        group_rows.sort(key=lambda x: -x["dollar_volume"]) # 거래대금 순 정렬
        lines.append(f"=== {title} ({len(group_rows)}개) ===")
        if not group_rows:
            lines.append("- 해당 종목 없음")
        else:
            for i, row in enumerate(group_rows[:15], 1):
                lines.append(f"{i}. {_fmt_row(row)}")
            if len(group_rows) > 15:
                lines.append(f"... 외 {len(group_rows)-15}개")
        lines.append("")
        
    return "\n".join(lines).strip()

def merge_shard_scan_rows(merge_dir: Path) -> list[dict]:
    all_rows = []
    files = sorted(Path(merge_dir).glob("**/scan_rows_*.json"))
    for file_path in files:
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                all_rows.extend(data)
    
    # Deduplicate
    seen = set()
    dedup = []
    for r in all_rows:
        if r["ticker"] not in seen:
            seen.add(r["ticker"])
            dedup.append(r)
    return dedup

def parse_args():
    parser = argparse.ArgumentParser("Realtime Premarket Scan (18:00 KST)")
    parser.add_argument("--out-dir", default="artifacts/pm1800_scan", help="Output directory")
    parser.add_argument("--max-workers", type=int, default=12)
    parser.add_argument("--bias-mode", default=DEFAULT_BIAS_MODE)
    parser.add_argument("--skip-telegram", action="store_true")
    parser.add_argument("--shard-count", type=int, default=1)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--merge-dir", default="", help="Directory with shard json to merge")
    parser.add_argument("--universe-profile", default="default")
    return parser.parse_args()

def main():
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    run_at_kst = datetime.now(KST)
    
    if args.merge_dir:
        merge_dir = Path(args.merge_dir)
        logger.info(f"Merging shards from {merge_dir}")
        rows = merge_shard_scan_rows(merge_dir)
        
        summary_text = format_telegram_summary(rows, run_at_kst, -1) # exact universe count unknown here, omit or read meta
        summary_path = out_dir / "pm1800_summary.txt"
        summary_path.write_text(summary_text, encoding="utf-8")
        
        csv_path = out_dir / "pm1800_results.csv"
        df = pd.DataFrame(rows)
        if not df.empty:
            df.to_csv(csv_path, index=False)
            
        if not args.skip_telegram:
            token = str(os.getenv("TELEGRAM_BOT_TOKEN", "")).strip()
            chat_id = str(os.getenv("TELEGRAM_CHAT_ID", "")).strip()
            if token and chat_id:
                logger.info("Sending Telegram summary...")
                send_telegram_message(token, chat_id, summary_text)
                if df.empty == False:
                    send_telegram_document(token, chat_id, csv_path, "pm1800_results.csv")
    else:
        logger.info(f"Shard {args.shard_index}/{args.shard_count} initialized.")
        universe_payload = build_scan_universe(universe_profile=args.universe_profile)
        full_tickers = universe_payload.get("tickers", [])
        tickers = split_tickers_for_shard(full_tickers, args.shard_count, args.shard_index)
        
        # Calculate time-adjusted threshold
        # Base threshold is e.g. $10,000 premarket volume 
        # But adjusted smoothly via _time_adjusted_volume_threshold
        time_ratio = _time_adjusted_volume_threshold(run_at_kst, base_threshold=1.0)
        # Assuming typical base premarket required to trigger is $20,000
        min_dollar_volume = 20000.0 * time_ratio
        
        logger.info(f"Shard tickers: {len(tickers)}, Threshold: ${min_dollar_volume:.0f}")
        
        scan_result = scan_universe(tickers, args.max_workers, args.bias_mode, min_dollar_volume)
        logger.info(f"Completed scan. Matches: {scan_result.perf['match_count']}, Skips: {scan_result.perf['skip_count']}")
        
        json_path = out_dir / f"scan_rows_shard{args.shard_index}.json"
        with json_path.open("w", encoding="utf-8") as f:
            json.dump(scan_result.rows, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
