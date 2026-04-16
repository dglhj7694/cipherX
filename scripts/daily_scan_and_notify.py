from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime, time as dt_time, timedelta
from pathlib import Path
from typing import Any, Iterable, Mapping
from zoneinfo import ZoneInfo

import requests
import yfinance as yf

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import COMBINED_SCAN_REGISTRY, DEFAULT_BIAS_MODE, JT, resolve_bias_mode
from engine import detect_all_signals
from indicators import compute_indicators
from localization import (
    localize_action_label,
    localize_combo,
    localize_context_label,
    localize_judgment_label,
    localize_signal,
)
from scanner_csv import (
    CORE_SIGNAL_GROUP as SCANNER_CORE_SIGNAL_CFG,
    build_detected_signal_payload,
    scanner_rows_to_csv_bytes,
)
from scanner_filters import (
    WATCH_BUY_PLUS,
    compute_scanner_profile_flags,
    has_long_pullback_strategy,
    has_pullback_combo,
)
from sectors import SECTOR_GROUPS
from strategy import build_strategy_payload
from etf_sources import resolve_etf_universe

KST = ZoneInfo("Asia/Seoul")
US_EASTERN = ZoneInfo("America/New_York")
_SCAN_SYMBOL_PATTERN = re.compile(r"\b[A-Z]{1,6}(?:[.-][A-Z0-9]{1,4})?\b")

ETF_UNIVERSE_ITEMS: tuple[dict[str, str], ...] = (
    {"requested": "러셀1000", "resolved": "IWB"},
    {"requested": "MSCI(USA)", "resolved": "EUSA"},
    {"requested": "나스닥100", "resolved": "QQQ"},
    {"requested": "S&P500", "resolved": "SPY"},
)

SCANNER_TRANSITION_CFG = {
    "UTBot_Buy": {"label": "UTBot 전환↑", "icon": "🟢", "dir": "buy"},
    "UTBot_Sell": {"label": "UTBot 전환↓", "icon": "🔴", "dir": "sell"},
    "Hull_Turn_Bull": {"label": "HULL 전환↑", "icon": "🟢", "dir": "buy"},
    "Hull_Turn_Bear": {"label": "HULL 전환↓", "icon": "🔴", "dir": "sell"},
}


@dataclass
class ScanRunResult:
    rows: list[dict[str, Any]]
    skips: list[dict[str, str]]
    perf: dict[str, Any]


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        numeric = float(value)
        if math.isnan(numeric):
            return default
        return numeric
    except Exception:
        return default


def _ordered_unique(values: Iterable[Any]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values or []:
        text = str(value or "").strip().upper().replace(".", "-")
        if not text or text in seen:
            continue
        if not _SCAN_SYMBOL_PATTERN.fullmatch(text):
            continue
        seen.add(text)
        ordered.append(text)
    return ordered


def _stable_shard_index(symbol: str, shard_count: int) -> int:
    if shard_count <= 0:
        raise ValueError("shard_count must be > 0")
    digest = hashlib.sha1(str(symbol or "").strip().upper().encode("utf-8")).hexdigest()
    return int(digest[:12], 16) % shard_count


def split_tickers_for_shard(tickers: Iterable[str], shard_count: int, shard_index: int) -> list[str]:
    if shard_count <= 0:
        raise ValueError("shard_count must be > 0")
    if shard_index < 0 or shard_index >= shard_count:
        raise ValueError("shard_index out of range")
    normalized = _ordered_unique(tickers or [])
    return [ticker for ticker in normalized if _stable_shard_index(ticker, shard_count) == shard_index]


def _row_sort_key(row: Mapping[str, Any]) -> tuple[float, float, float, str]:
    return (
        -_safe_float(row.get("scan_score", 0)),
        -_safe_float(row.get("strength", 0)),
        -_safe_float(row.get("latest_sig_ts", 0)),
        str(row.get("ticker", "")),
    )


def _dedupe_rows_by_ticker(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    best_by_ticker: dict[str, dict[str, Any]] = {}
    for row in rows or []:
        row_dict = dict(row or {})
        ticker = str(row_dict.get("ticker") or "").strip().upper()
        if not ticker:
            continue
        current = best_by_ticker.get(ticker)
        if current is None:
            best_by_ticker[ticker] = row_dict
            continue
        if _row_sort_key(row_dict) < _row_sort_key(current):
            best_by_ticker[ticker] = row_dict
    deduped = list(best_by_ticker.values())
    deduped.sort(key=_row_sort_key)
    return deduped


def _recent_frame_flag(frame: Any, column: str, window: int = 5) -> bool:
    if frame is None or column not in getattr(frame, "columns", []):
        return False
    series = frame[column].tail(window)
    try:
        return bool(series.fillna(False).astype(bool).any())
    except Exception:
        return bool(series.any())


def _build_sector_universe() -> list[str]:
    return _ordered_unique(
        ticker
        for tickers in SECTOR_GROUPS.values()
        for ticker in tickers
    )


def build_scan_universe(etf_items: Iterable[Mapping[str, str]] | None = None) -> dict[str, Any]:
    sector_tickers = _build_sector_universe()
    resolver_payload = resolve_etf_universe(list(etf_items or ETF_UNIVERSE_ITEMS))
    etf_tickers = _ordered_unique(resolver_payload.get("tickers") or [])
    combined = _ordered_unique([*sector_tickers, *etf_tickers])
    return {
        "tickers": combined,
        "sector_count": len(sector_tickers),
        "etf_count": len(etf_tickers),
        "etf_items": list(resolver_payload.get("items") or []),
        "etf_note": str(resolver_payload.get("note") or ""),
        "etf_errors": [str(err) for err in (resolver_payload.get("errors") or [])],
    }


def _compute_signal_frame(ticker: str, *, bias_mode: str) -> Any | None:
    history = yf.Ticker(ticker).history(period="2y", auto_adjust=True)
    if history is None or history.empty:
        return None
    indicator_frame = compute_indicators(history)
    return detect_all_signals(indicator_frame, bias_mode=resolve_bias_mode(bias_mode))


def _build_scanner_row(ticker: str, *, bias_mode: str, recent_window: int = 5) -> dict[str, Any]:
    ticker = str(ticker or "").strip().upper()
    if not ticker:
        return {"ok": False, "ticker": "", "skip_reason": "invalid_ticker", "detail": "empty ticker"}

    try:
        frame = _compute_signal_frame(ticker, bias_mode=bias_mode)
    except Exception as exc:
        return {"ok": False, "ticker": ticker, "skip_reason": "compute_error", "detail": str(exc)[:220]}

    if frame is None:
        return {"ok": False, "ticker": ticker, "skip_reason": "missing_frame", "detail": "no frame returned"}
    if len(frame) < 50:
        return {"ok": False, "ticker": ticker, "skip_reason": "insufficient_history", "detail": f"bars={len(frame)}"}

    try:
        dc_ = frame.tail(63)
        latest = dc_.iloc[-1]
        prev_close = _safe_float(dc_.iloc[-2].get("Close", latest.get("Close", 0))) if len(dc_) >= 2 else _safe_float(latest.get("Close", 0))
        current_close = _safe_float(latest.get("Close", 0))

        strategy_payload = build_strategy_payload(dc_)
        strategy_summary = strategy_payload.get("summary", {})
        strategy_results = list(strategy_payload.get("visible_results") or [])
        top_strategy = strategy_summary.get("top_strategy")

        detected_payload = build_detected_signal_payload(
            frame=dc_,
            recent_window=recent_window,
            combo_registry=COMBINED_SCAN_REGISTRY,
            transition_cfg=SCANNER_TRANSITION_CFG,
            core_signal_cfg=SCANNER_CORE_SIGNAL_CFG,
            localize_combo_fn=localize_combo,
            localize_signal_fn=localize_signal,
            summary_limit=8,
        )

        combos = [
            {
                "icon": str(item.get("icon", "")),
                "kor": str(item.get("label", "")),
                "dir": str(item.get("dir", "neutral")),
                "tier": int(item.get("tier", 9) or 9),
                "date": str(item.get("date_short", "")),
                "days_ago": int(item.get("days_ago", 99) or 99),
            }
            for item in detected_payload.get("combo_items", [])
        ]
        latest_combo_ts = detected_payload.get("latest_combo_ts")
        transitions = [
            {
                "icon": str(item.get("icon", "")),
                "label": str(item.get("label", "")),
                "dir": str(item.get("dir", "neutral")),
                "date": str(item.get("date_short", "")),
                "date_iso": str(item.get("date", "")),
                "days_ago": int(item.get("days_ago", 99) or 99),
                "key": str(item.get("key", "")),
            }
            for item in detected_payload.get("transition_items", [])
        ]

        chg_value = _safe_float(current_close - prev_close)
        chg_pct = _safe_float((current_close - prev_close) / prev_close * 100) if prev_close else 0.0
        buy_total = _safe_float(latest.get("Buy_Total", 0))
        sell_total = _safe_float(latest.get("Sell_Total", 0))
        buy_agree = int(_safe_float(latest.get("Buy_Agree", 0)))
        sell_agree = int(_safe_float(latest.get("Sell_Agree", 0)))
        es = _safe_float(latest.get("Ensemble_Score", 0))
        cf = _safe_float(latest.get("Judgment_Confidence", 0))
        market_bias = _safe_float(latest.get("Market_Filter_Bias", 0))
        downgrade_count = _safe_float(latest.get("Downgrade_Count", 0))
        flip_guard_triggered = bool(latest.get("Flip_Guard_Triggered", False))
        continuation_buy = _safe_float(latest.get("Continuation_Buy_Score", 0))
        continuation_sell = _safe_float(latest.get("Continuation_Sell_Score", 0))
        thin_trade_risk = bool(latest.get("Thin_Trade_Risk", False))
        bullish_gap_reversal = bool(latest.get("Bullish_Gap_Reversal", False))
        bearish_gap_failure = bool(latest.get("Bearish_Gap_Failure", False))
        raw_jg = str(latest.get("Trade_Judgment", "N/A"))

        tier1_buy = sum(1 for item in combos if item["tier"] == 1 and item["dir"] == "buy")
        tier1_sell = sum(1 for item in combos if item["tier"] == 1 and item["dir"] == "sell")
        tier2_buy = sum(1 for item in combos if item["tier"] == 2 and item["dir"] == "buy")
        tier2_sell = sum(1 for item in combos if item["tier"] == 2 and item["dir"] == "sell")
        scan_score = (
            es
            + (buy_total - sell_total) * 0.55
            + (buy_agree - sell_agree) * 2.5
            + tier1_buy * 4.0
            - tier1_sell * 4.0
            + tier2_buy * 1.6
            - tier2_sell * 1.6
            + cf * 0.04
            + market_bias * 0.55
            + continuation_buy * 0.9
            - continuation_sell * 0.9
        )
        scan_score -= downgrade_count * 2.2
        if thin_trade_risk:
            scan_score -= 4.0
        if bullish_gap_reversal:
            scan_score += 1.8
        if bearish_gap_failure:
            scan_score -= 2.2
        judgment_bias = {
            "STRONG_BUY": 10.0,
            "BUY": 5.0,
            "WATCH_BUY": JT.WATCH_BUY_SCAN_BIAS,
            "WATCH_SELL": JT.WATCH_SELL_SCAN_BIAS,
            "SELL": JT.SELL_SCAN_BIAS,
            "STRONG_SELL": JT.STRONG_SELL_SCAN_BIAS,
        }.get(raw_jg, 0.0)
        scan_score += judgment_bias
        if raw_jg in ("NEUTRAL", "MIXED"):
            scan_score *= 0.7
        if flip_guard_triggered:
            scan_score *= 0.82

        strength = (
            abs(es)
            + (buy_total + sell_total) * 0.35
            + abs(buy_agree - sell_agree) * 1.8
            + (tier1_buy + tier1_sell) * 3.0
            + cf * 0.02
        )

        multi_buy = sum(1 for item in combos if item["dir"] == "buy")
        multi_sell = sum(1 for item in combos if item["dir"] == "sell")
        multi_neutral = sum(1 for item in combos if item["dir"] == "neutral")
        multi_count = len(combos)
        multi_imbalance = multi_buy - multi_sell
        has_tier1 = any(item["tier"] == 1 for item in combos)
        multi_sig = (multi_count >= 3) or (has_tier1 and multi_count >= 2)

        recent_hits = sorted(
            [item for item in combos if item.get("days_ago", 99) <= 3],
            key=lambda item: (item.get("tier", 9), item.get("days_ago", 99)),
        )
        multi_hits = [{"icon": h["icon"], "label": h["kor"], "dir": h["dir"], "date": h["date"]} for h in recent_hits]
        if not multi_hits:
            fallback_hits = sorted(combos, key=lambda item: (item.get("tier", 9), item.get("days_ago", 99)))[:6]
            multi_hits = [{"icon": h["icon"], "label": h["kor"], "dir": h["dir"], "date": h["date"]} for h in fallback_hits]

        volume_ratio_20 = _safe_float(latest.get("Volume_Ratio_20", 0))
        volume_ratio_50 = _safe_float(latest.get("Volume_Ratio_50", 0))
        volume_oscillator = _safe_float(latest.get("Volume_Oscillator", 0))
        dollar_volume_20 = _safe_float(latest.get("Dollar_Volume_20", 0))
        volume_surge = bool(latest.get("Volume_Surge", False))
        volume_climax_buy = bool(latest.get("Volume_Climax_Buy", False))
        volume_abnormal = bool(volume_surge or volume_ratio_20 >= 2.0)
        volume_bullish = bool((volume_ratio_20 >= 1.2) and (volume_surge or volume_climax_buy or volume_oscillator > 0))

        system_turn_bull = _recent_frame_flag(dc_, "System_Turn_Bull", recent_window)
        trend_inflect_bull = _recent_frame_flag(dc_, "Trend_Inflection_Bull", recent_window)
        ut_turn_bull = _recent_frame_flag(dc_, "UTBot_Buy", recent_window)
        hull_turn_bull = _recent_frame_flag(dc_, "Hull_Turn_Bull", recent_window)
        bull_turn_recent = bool(system_turn_bull or trend_inflect_bull or ut_turn_bull or hull_turn_bull)

        ma20 = _safe_float(latest.get("MA20", 0))
        ma50 = _safe_float(latest.get("MA50", 0))
        ma20_prev = _safe_float(dc_.iloc[-2].get("MA20", ma20)) if len(dc_) >= 2 else ma20
        ma50_prev = _safe_float(dc_.iloc[-2].get("MA50", ma50)) if len(dc_) >= 2 else ma50
        uptrend_ready = bool(current_close > ma20 > ma50) if ma20 and ma50 else False
        pullback_ready = _recent_frame_flag(dc_, "EMA_Pullback_Buy", recent_window)
        uptrend_or_pullback = bool(uptrend_ready or pullback_ready)
        recent_utbot_sell = _recent_frame_flag(dc_, "UTBot_Sell", recent_window)
        recent_hull_bear = _recent_frame_flag(dc_, "Hull_Turn_Bear", recent_window)
        strategy_conflict_level = str(strategy_summary.get("conflict_level", "LOW"))
        strategy_bias = str(strategy_summary.get("long_short_bias", "BALANCED"))
        strategy_active_count = int(strategy_summary.get("active_count", 0) or 0)
        buy_combo_present = any(item["dir"] == "buy" for item in combos)
        pullback_combo_present = has_pullback_combo(detected_payload.get("combo_items", []))
        long_pullback_strategy_visible = has_long_pullback_strategy(strategy_results)
        watch_buy_plus = raw_jg in WATCH_BUY_PLUS
        bull_strength_recent = bool(
            watch_buy_plus
            and (bull_turn_recent or uptrend_or_pullback)
            and (strategy_active_count > 0 or buy_combo_present)
            and volume_bullish
        )
        profile_flags = compute_scanner_profile_flags(
            current_close=current_close,
            ma20=ma20,
            ma50=ma50,
            ma20_prev=ma20_prev,
            ma50_prev=ma50_prev,
            watch_buy_plus=watch_buy_plus,
            strategy_bias=strategy_bias,
            recent_utbot_sell=recent_utbot_sell,
            recent_hull_bear=recent_hull_bear,
            adx=_safe_float(latest.get("ADX", 0)),
            es=es,
            cf=cf,
            volume_bullish=volume_bullish,
            strategy_conflict_level=strategy_conflict_level,
            pullback_ready=pullback_ready,
            pullback_combo_present=pullback_combo_present,
            long_pullback_strategy_visible=long_pullback_strategy_visible,
            multi_sell=multi_sell,
            thin_trade_risk=thin_trade_risk,
            flip_guard_triggered=flip_guard_triggered,
        )

        row = {
            "ticker": ticker,
            "price": _safe_float(current_close),
            "chg_value": chg_value,
            "chg": chg_pct,
            "scans": sorted(combos, key=lambda item: item["tier"]),
            "transitions": transitions,
            "multi_sig": multi_sig,
            "multi_cnt": multi_count,
            "multi_buy": multi_buy,
            "multi_sell": multi_sell,
            "multi_neutral": multi_neutral,
            "multi_imb": multi_imbalance,
            "multi_hits": multi_hits,
            "jg_key": raw_jg,
            "jg": localize_judgment_label(raw_jg),
            "cf": cf,
            "es": es,
            "strategies": strategy_results,
            "top_strategy": top_strategy,
            "strategy_conflict_level": strategy_conflict_level,
            "strategy_bias": strategy_bias,
            "strategy_active_count": strategy_active_count,
            "ctx": localize_context_label(int(_safe_float(latest.get("Market_Context", 0)))),
            "ba": buy_agree,
            "sa": sell_agree,
            "buy_total": buy_total,
            "sell_total": sell_total,
            "scan_score": _safe_float(scan_score),
            "strength": _safe_float(strength),
            "latest_sig": latest_combo_ts.strftime("%Y-%m-%d") if latest_combo_ts else "9999-99-99",
            "latest_sig_ts": latest_combo_ts.timestamp() if latest_combo_ts else 0.0,
            "reason": str(latest.get("Judgment_Reason", "")),
            "action": localize_action_label(str(latest.get("Action_Label", ""))),
            "volume_ratio_20": volume_ratio_20,
            "volume_ratio_50": volume_ratio_50,
            "volume_oscillator": volume_oscillator,
            "dollar_volume_20": dollar_volume_20,
            "volume_surge": volume_surge,
            "volume_abnormal": volume_abnormal,
            "volume_bullish": volume_bullish,
            "thin_trade_risk": thin_trade_risk,
            "bull_turn_recent": bull_turn_recent,
            "uptrend_or_pullback": uptrend_or_pullback,
            "pullback_ready": pullback_ready,
            "bull_strength_recent": bull_strength_recent,
            "uptrend_persistent": bool(profile_flags.get("uptrend_persistent", False)),
            "strong_trend_persistent": bool(profile_flags.get("strong_trend_persistent", False)),
            "pullback_reentry": bool(profile_flags.get("pullback_reentry", False)),
            "low_conflict_bullish": bool(profile_flags.get("low_conflict_bullish", False)),
            "utbot_buy_recent": bool(detected_payload.get("utbot_buy_recent", False)),
            "utbot_buy_last_date": str(detected_payload.get("utbot_buy_last_date", "없음")),
            "utbot_sell_recent": bool(detected_payload.get("utbot_sell_recent", False)),
            "utbot_sell_last_date": str(detected_payload.get("utbot_sell_last_date", "없음")),
            "hull_turn_bull_recent": bool(detected_payload.get("hull_turn_bull_recent", False)),
            "hull_turn_bull_last_date": str(detected_payload.get("hull_turn_bull_last_date", "없음")),
            "hull_turn_bear_recent": bool(detected_payload.get("hull_turn_bear_recent", False)),
            "hull_turn_bear_last_date": str(detected_payload.get("hull_turn_bear_last_date", "없음")),
            "detected_combo_count": int(detected_payload.get("detected_combo_count", 0) or 0),
            "detected_combo_summary": str(detected_payload.get("detected_combo_summary", "없음")),
            "detected_transition_count": int(detected_payload.get("detected_transition_count", 0) or 0),
            "detected_transition_summary": str(detected_payload.get("detected_transition_summary", "없음")),
            "detected_core_count": int(detected_payload.get("detected_core_count", 0) or 0),
            "detected_core_summary": str(detected_payload.get("detected_core_summary", "없음")),
            "detected_signal_total_count": int(detected_payload.get("detected_signal_total_count", 0) or 0),
            "detected_signal_latest_date": str(detected_payload.get("detected_signal_latest_date", "없음")),
            "detected_signals": list(detected_payload.get("all_items", [])),
            "watch_buy_plus": watch_buy_plus,
            "buy_combo_present": buy_combo_present,
        }
        return {"ok": True, "ticker": ticker, "row": row, "skip_reason": "", "detail": ""}
    except Exception as exc:
        return {"ok": False, "ticker": ticker, "skip_reason": "row_build_error", "detail": str(exc)[:220]}


def _scan_ticker_worker(ticker: str, *, bias_mode: str) -> dict[str, Any]:
    started = time.perf_counter()
    payload = dict(_build_scanner_row(ticker, bias_mode=bias_mode))
    payload["elapsed_sec"] = _safe_float(time.perf_counter() - started)
    return payload


def scan_universe(tickers: list[str], *, max_workers: int, bias_mode: str) -> ScanRunResult:
    run_started = time.perf_counter()
    results: list[dict[str, Any]] = []
    skip_reasons: list[dict[str, str]] = []
    ticker_latencies: list[float] = []

    if not tickers:
        return ScanRunResult(rows=[], skips=[], perf={"workers": 0, "total_seconds": 0.0, "ticker_count": 0})

    effective_workers = min(12, max(4, int(max_workers or 4)), len(tickers))

    setup_started = time.perf_counter()
    try:
        from engine import _ensure_runtime_combo_registry

        _ensure_runtime_combo_registry()
    except Exception as exc:
        skip_reasons.append({"ticker": "-", "reason": "registry_error", "detail": str(exc)[:220]})
    setup_seconds = _safe_float(time.perf_counter() - setup_started)

    scan_started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=effective_workers) as executor:
        futures = {
            executor.submit(_scan_ticker_worker, ticker, bias_mode=bias_mode): ticker
            for ticker in tickers
        }
        for future in as_completed(futures):
            done_ticker = futures[future]
            try:
                payload = future.result()
            except Exception as exc:
                skip_reasons.append({"ticker": done_ticker, "reason": "future_error", "detail": str(exc)[:220]})
                continue
            if payload.get("ok") and isinstance(payload.get("row"), dict):
                row = dict(payload["row"])
                row["scan_source"] = "daily_batch"
                row["scan_latency_sec"] = _safe_float(payload.get("elapsed_sec", 0))
                results.append(row)
                ticker_latencies.append(_safe_float(payload.get("elapsed_sec", 0)))
            else:
                skip_reasons.append(
                    {
                        "ticker": str(payload.get("ticker") or done_ticker),
                        "reason": str(payload.get("skip_reason") or "unknown"),
                        "detail": str(payload.get("detail") or "")[:220],
                    }
                )
    scan_seconds = _safe_float(time.perf_counter() - scan_started)

    sort_started = time.perf_counter()
    results.sort(key=_row_sort_key)
    sort_seconds = _safe_float(time.perf_counter() - sort_started)

    perf_stats = {
        "workers": effective_workers,
        "setup_seconds": setup_seconds,
        "scan_seconds": scan_seconds,
        "sort_seconds": sort_seconds,
        "total_seconds": _safe_float(time.perf_counter() - run_started),
        "ticker_count": len(tickers),
        "match_count": len(results),
        "skip_count": len(skip_reasons),
        "avg_row_seconds": _safe_float(sum(ticker_latencies) / len(ticker_latencies)) if ticker_latencies else 0.0,
    }
    return ScanRunResult(rows=results, skips=skip_reasons, perf=perf_stats)


def write_scan_csv(rows: list[dict[str, Any]], *, out_dir: Path, run_label: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / f"scanner_full_{run_label}.csv"
    output_path.write_bytes(scanner_rows_to_csv_bytes(rows))
    return output_path


def write_json(payload: Mapping[str, Any], *, out_dir: Path, filename: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / filename
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def write_scan_rows_json(rows: list[dict[str, Any]], *, out_dir: Path, run_label: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / f"scan_rows_{run_label}.json"
    output_path.write_text(json.dumps(list(rows or []), ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def _load_json_file(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def merge_shard_scan_rows(merge_dir: Path) -> dict[str, Any]:
    files = sorted(Path(merge_dir).glob("**/scan_rows_*.json"))
    if not files:
        raise RuntimeError(f"No shard row files found in {merge_dir}")

    all_rows: list[dict[str, Any]] = []
    for file_path in files:
        payload = _load_json_file(file_path)
        if isinstance(payload, dict):
            rows = payload.get("rows") or []
        elif isinstance(payload, list):
            rows = payload
        else:
            rows = []
        for row in rows:
            if isinstance(row, dict):
                all_rows.append(dict(row))

    merged_rows = _dedupe_rows_by_ticker(all_rows)

    meta_files = sorted(Path(merge_dir).glob("**/run_meta_*.json"))
    shard_universe_sum = 0
    full_universe_max = 0
    skip_count_sum = 0
    result_count_sum = 0
    shard_meta_count = 0
    shard_errors: list[str] = []
    for meta_file in meta_files:
        payload = _load_json_file(meta_file)
        if not isinstance(payload, dict):
            continue
        shard_meta_count += 1
        shard_universe_sum += int(_safe_float(payload.get("shard_ticker_count", 0)))
        full_universe_max = max(full_universe_max, int(_safe_float(payload.get("full_universe_count", 0))))
        performance = payload.get("performance") or {}
        skip_count_sum += int(_safe_float(performance.get("skip_count", 0)))
        result_count_sum += int(_safe_float(payload.get("result_count", 0)))
        for err in payload.get("etf_errors", []) or []:
            shard_errors.append(str(err))

    universe_count = full_universe_max or shard_universe_sum
    return {
        "rows": merged_rows,
        "row_files": [str(path) for path in files],
        "meta_files": [str(path) for path in meta_files],
        "source_row_count": len(all_rows),
        "merged_row_count": len(merged_rows),
        "source_result_count_sum": result_count_sum,
        "skip_count_sum": skip_count_sum,
        "universe_count": universe_count,
        "shard_meta_count": shard_meta_count,
        "etf_errors": _ordered_unique(shard_errors),
    }


def _parse_iso_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text or text in {"없음", "-", "N/A"}:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except Exception:
        return None


def _last_us_market_session_date(run_at_kst: datetime) -> date:
    us_now = run_at_kst.astimezone(US_EASTERN)
    session_date = us_now.date()
    if us_now.weekday() >= 5 or us_now.time() < dt_time(16, 0):
        session_date -= timedelta(days=1)
    while session_date.weekday() >= 5:
        session_date -= timedelta(days=1)
    return session_date


def _transition_signals_on_date(row: Mapping[str, Any], target_date: date) -> list[str]:
    signals: list[str] = []
    utbot_buy_date = _parse_iso_date(row.get("utbot_buy_last_date"))
    hull_buy_date = _parse_iso_date(row.get("hull_turn_bull_last_date"))
    if utbot_buy_date == target_date:
        signals.append("UTBot 매수")
    if hull_buy_date == target_date:
        signals.append("HULL 매수")
    return signals


def select_us_session_turn_rows(rows: Iterable[Mapping[str, Any]], *, run_at_kst: datetime) -> list[dict[str, Any]]:
    target_date = _last_us_market_session_date(run_at_kst)
    selected: list[dict[str, Any]] = []
    for row in rows or []:
        row_dict = dict(row or {})
        signals = _transition_signals_on_date(row_dict, target_date)
        if not signals:
            continue
        row_dict["transition_signals"] = signals
        selected.append(row_dict)
    selected.sort(key=lambda row: (-_safe_float(row.get("scan_score", 0)), -_safe_float(row.get("es", 0)), str(row.get("ticker", ""))))
    return selected


def filter_turn_rows_for_telegram(
    rows: Iterable[Mapping[str, Any]],
    *,
    min_volume_ratio_20_exclusive: float = 1.0,
) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for row in rows or []:
        row_dict = dict(row or {})
        volume_ratio = _safe_float(row_dict.get("volume_ratio_20", 0))
        if volume_ratio <= float(min_volume_ratio_20_exclusive):
            continue
        filtered.append(row_dict)
    filtered.sort(key=lambda row: (-_safe_float(row.get("scan_score", 0)), -_safe_float(row.get("es", 0)), str(row.get("ticker", ""))))
    return filtered


def _fmt_signed_number(value: Any, decimals: int = 2) -> str:
    try:
        return f"{float(value):+.{decimals}f}"
    except Exception:
        return "--"


def _fmt_ratio(value: Any, decimals: int = 2) -> str:
    try:
        return f"{float(value):.{decimals}f}x"
    except Exception:
        return "--"


def build_transition_summary(
    turn_rows: Iterable[Mapping[str, Any]],
    *,
    run_at_kst: datetime,
    universe_count: int,
    result_count: int,
    skip_count: int,
    detected_turn_count: int | None = None,
    summary_limit: int = 0,
) -> str:
    rows = list(turn_rows or [])
    detected_count = len(rows) if detected_turn_count is None else max(0, int(detected_turn_count))
    target_us_session_date = _last_us_market_session_date(run_at_kst)
    lines = [
        f"[자동 스캔] {run_at_kst.strftime('%Y-%m-%d %H:%M:%S')} KST",
        f"- 전일 미국장 전환일: {target_us_session_date.isoformat()} (US/Eastern)",
        "- 필터 기준: 전일 미국장(US/Eastern)에서 UTBot/HULL 매수 신호 발생",
        "- 추가 필터: 20일 평균대비 거래량 > 1.0x",
        f"- 유니버스: {universe_count}개",
        f"- 전체 스캔 결과: {result_count}개 (제외 {skip_count}개)",
        f"- 전환 감지 {detected_count}개 -> 필터 통과 {len(rows)}개",
        "",
        "당일 전환 목록:",
    ]
    if not rows:
        lines.append("- 해당 없음")
        return "\n".join(lines)

    limited_rows = rows if int(summary_limit) <= 0 else rows[: int(summary_limit)]
    for idx, row in enumerate(limited_rows, start=1):
        signals = list(row.get("transition_signals") or [])
        signal_text = ", ".join(signals) if signals else "-"
        lines.append(
            f"{idx}. {row.get('ticker', '-')}"
            f" | ({_fmt_signed_number(row.get('chg_value', 0), 2)}, {_fmt_signed_number(row.get('chg', 0), 2)}%)"
            f" | 거래량 {_fmt_ratio(row.get('volume_ratio_20', 0), 2)}"
            f" | {row.get('jg_key', '-')}"
            f" | {signal_text}"
        )
    remain = len(rows) - len(limited_rows)
    if remain > 0:
        lines.append(f"... 외 {remain}개")
    return "\n".join(lines)


def _telegram_api(token: str, method: str) -> str:
    return f"https://api.telegram.org/bot{token}/{method}"


def split_telegram_message_text(text: str, *, chunk_size: int = 3500) -> list[str]:
    raw = str(text or "")
    limit = max(1, int(chunk_size))
    if len(raw) <= limit:
        return [raw]
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for line in raw.splitlines():
        line_text = str(line)
        line_len = len(line_text) + 1
        if line_len > limit:
            if current:
                chunks.append("\n".join(current))
                current = []
                current_len = 0
            start = 0
            while start < len(line_text):
                end = min(start + limit, len(line_text))
                chunks.append(line_text[start:end])
                start = end
            continue
        if current and (current_len + line_len > limit):
            chunks.append("\n".join(current))
            current = [line_text]
            current_len = line_len
        else:
            current.append(line_text)
            current_len += line_len
    if current:
        chunks.append("\n".join(current))
    return chunks or [raw]


def send_telegram_message(token: str, chat_id: str, text: str, *, chunk_size: int = 3500) -> None:
    chunks = split_telegram_message_text(text, chunk_size=chunk_size)
    for chunk in chunks:
        if not str(chunk or "").strip():
            continue
        response = requests.post(
            _telegram_api(token, "sendMessage"),
            json={"chat_id": chat_id, "text": chunk},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("ok"):
            raise RuntimeError(f"Telegram sendMessage failed: {payload}")


def send_telegram_document(token: str, chat_id: str, file_path: Path, caption: str = "") -> None:
    with file_path.open("rb") as handle:
        response = requests.post(
            _telegram_api(token, "sendDocument"),
            data={"chat_id": chat_id, "caption": caption},
            files={"document": (file_path.name, handle, "text/csv")},
            timeout=60,
        )
    response.raise_for_status()
    payload = response.json()
    if not payload.get("ok"):
        raise RuntimeError(f"Telegram sendDocument failed: {payload}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Daily scanner batch + Telegram notification")
    parser.add_argument("--out-dir", default="artifacts/daily_scan", help="Output directory for CSV and metadata")
    parser.add_argument("--max-workers", type=int, default=12, help="Maximum concurrent workers")
    parser.add_argument("--summary-limit", type=int, default=0, help="Maximum rows in trend-turn summary message (<=0 means all)")
    parser.add_argument("--bias-mode", default=DEFAULT_BIAS_MODE, help="Engine bias mode")
    parser.add_argument("--skip-telegram", action="store_true", help="Skip Telegram notification")
    parser.add_argument("--dry-run", action="store_true", help="Run scan and write files only")
    parser.add_argument("--shard-count", type=int, default=1, help="Total number of shards")
    parser.add_argument("--shard-index", type=int, default=0, help="Current shard index")
    parser.add_argument("--merge-dir", default="", help="Directory that contains shard artifacts to merge")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_at_kst = datetime.now(KST)
    stamp = run_at_kst.strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out_dir)
    shard_count = int(args.shard_count or 1)
    shard_index = int(args.shard_index or 0)
    merge_dir_arg = str(args.merge_dir or "").strip()
    merge_dir = Path(merge_dir_arg).expanduser().resolve() if merge_dir_arg else None
    if shard_count <= 0:
        raise RuntimeError("--shard-count must be > 0")
    if shard_index < 0 or shard_index >= shard_count:
        raise RuntimeError("--shard-index out of range")

    if merge_dir:
        run_label = f"{stamp}_merged"
        print(f"[MERGE] Loading shard artifacts from {merge_dir}")
        merged_payload = merge_shard_scan_rows(merge_dir)
        merged_rows = list(merged_payload.get("rows") or [])
        print(
            f"[MERGE] Completed: merged={len(merged_rows)} "
            f"source_rows={int(merged_payload.get('source_row_count', 0))} "
            f"source_sum={int(merged_payload.get('source_result_count_sum', 0))}"
        )
        csv_path = write_scan_csv(merged_rows, out_dir=out_dir, run_label=run_label)
        rows_path = write_scan_rows_json(merged_rows, out_dir=out_dir, run_label=run_label)

        detected_turn_rows = select_us_session_turn_rows(merged_rows, run_at_kst=run_at_kst)
        turn_rows = filter_turn_rows_for_telegram(detected_turn_rows, min_volume_ratio_20_exclusive=1.0)
        summary_text = build_transition_summary(
            turn_rows,
            run_at_kst=run_at_kst,
            universe_count=int(_safe_float(merged_payload.get("universe_count", 0))),
            result_count=len(merged_rows),
            skip_count=int(_safe_float(merged_payload.get("skip_count_sum", 0))),
            detected_turn_count=len(detected_turn_rows),
            summary_limit=int(args.summary_limit),
        )
        summary_path = out_dir / f"trend_turn_summary_{run_label}.txt"
        summary_path.write_text(summary_text, encoding="utf-8")

        write_json(
            {
                "run_at_kst": run_at_kst.isoformat(),
                "mode": "merge",
                "merged_payload": merged_payload,
                "result_count": len(merged_rows),
                "detected_turn_count": len(detected_turn_rows),
                "trend_turn_count": len(turn_rows),
                "csv_path": str(csv_path),
                "rows_path": str(rows_path),
                "summary_path": str(summary_path),
            },
            out_dir=out_dir,
            filename=f"run_meta_{run_label}.json",
        )
        print(f"[MERGE] CSV saved: {csv_path}")
        print(f"[MERGE] Summary saved: {summary_path}")
    else:
        run_label = f"{stamp}_shard{shard_index}of{shard_count}"
        print("[SCAN] Building universe...")
        universe_payload = build_scan_universe()
        full_tickers = list(universe_payload.get("tickers") or [])
        tickers = split_tickers_for_shard(full_tickers, shard_count, shard_index)
        print(
            f"[SCAN] Universe ready: full={len(full_tickers)} shard={len(tickers)} "
            f"(shard={shard_index}/{shard_count - 1}, "
            f"sector={universe_payload.get('sector_count', 0)}, etf={universe_payload.get('etf_count', 0)})"
        )
        if universe_payload.get("etf_errors"):
            print("[SCAN] ETF resolve errors:", " | ".join(universe_payload["etf_errors"]))

        scan_result = scan_universe(tickers, max_workers=int(args.max_workers), bias_mode=str(args.bias_mode))
        print(
            f"[SCAN] Completed: results={len(scan_result.rows)} "
            f"skips={len(scan_result.skips)} total_sec={_safe_float(scan_result.perf.get('total_seconds', 0)):.1f}"
        )

        csv_path = write_scan_csv(scan_result.rows, out_dir=out_dir, run_label=run_label)
        rows_path = write_scan_rows_json(scan_result.rows, out_dir=out_dir, run_label=run_label)
        detected_turn_rows = select_us_session_turn_rows(scan_result.rows, run_at_kst=run_at_kst)
        turn_rows = filter_turn_rows_for_telegram(detected_turn_rows, min_volume_ratio_20_exclusive=1.0)
        summary_text = build_transition_summary(
            turn_rows,
            run_at_kst=run_at_kst,
            universe_count=len(tickers),
            result_count=len(scan_result.rows),
            skip_count=len(scan_result.skips),
            detected_turn_count=len(detected_turn_rows),
            summary_limit=int(args.summary_limit),
        )
        summary_path = out_dir / f"trend_turn_summary_{run_label}.txt"
        summary_path.write_text(summary_text, encoding="utf-8")

        write_json(
            {
                "run_at_kst": run_at_kst.isoformat(),
                "mode": "scan",
                "full_universe_count": len(full_tickers),
                "shard_ticker_count": len(tickers),
                "shard_count": shard_count,
                "shard_index": shard_index,
                "universe": universe_payload,
                "etf_errors": list(universe_payload.get("etf_errors") or []),
                "performance": scan_result.perf,
                "skip_reasons": scan_result.skips,
                "result_count": len(scan_result.rows),
                "detected_turn_count": len(detected_turn_rows),
                "trend_turn_count": len(turn_rows),
                "csv_path": str(csv_path),
                "rows_path": str(rows_path),
                "summary_path": str(summary_path),
            },
            out_dir=out_dir,
            filename=f"run_meta_{run_label}.json",
        )

        print(f"[SCAN] CSV saved: {csv_path}")
        print(f"[SCAN] Summary saved: {summary_path}")

    if args.dry_run or args.skip_telegram:
        print("[SCAN] Telegram send skipped by option.")
        return 0

    token = str(os.getenv("TELEGRAM_BOT_TOKEN", "")).strip()
    chat_id = str(os.getenv("TELEGRAM_CHAT_ID", "")).strip()
    if not token or not chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID must be set")

    print("[SCAN] Sending Telegram summary...")
    send_telegram_message(token, chat_id, summary_text)
    print("[SCAN] Sending Telegram CSV...")
    send_telegram_document(
        token,
        chat_id,
        csv_path,
        caption=f"전체 스캔 CSV ({run_at_kst.strftime('%Y-%m-%d %H:%M')} KST)",
    )
    print("[SCAN] Telegram notification completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
