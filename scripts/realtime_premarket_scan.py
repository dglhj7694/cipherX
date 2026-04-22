import argparse
import json
import logging
import math
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime, time as dt_time
from pathlib import Path
from typing import Any, Iterable, Mapping
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
from localization import (
    localize_action_label,
    localize_context_label,
    localize_judgment_label,
    localize_combo,
    localize_signal,
)
from scanner_csv import CORE_SIGNAL_GROUP as SCANNER_CORE_SIGNAL_CFG, build_detected_signal_payload
from scanner_filters import WATCH_BUY_PLUS, compute_scanner_profile_flags, has_long_pullback_strategy, has_pullback_combo
from scripts.daily_scan_and_notify import (
    POST_CLOSE_INDEX_TITLES,
    POST_CLOSE_SECTION_TITLES,
    SCANNER_TRANSITION_CFG,
    _build_summary_section_lines,
    _compute_post_close_row_metrics,
    _last_us_market_session_date,
    _safe_float,
    _with_latest_session_buy_turn_flags,
    _with_post_close_cross_section_metrics,
    _with_post_close_setup_scores,
    build_scan_universe,
    filter_turn_rows_for_telegram,
    select_post_close_buy_turn_rows_for_telegram,
    select_post_close_chase_rows_for_telegram,
    select_post_close_gap_setup_rows_for_telegram,
    select_post_close_pocket_pivot_rows_for_telegram,
    select_post_close_pullback_rows_for_telegram,
    select_post_close_top_5d_rows_for_telegram,
    select_pullback_reentry_rows_for_telegram,
    select_us_session_52w_high_rows,
    select_us_session_hull_bear_rows,
    select_us_session_turn_rows,
    send_telegram_document,
    send_telegram_message,
    split_tickers_for_shard,
)
from strategy import build_strategy_payload

KST = ZoneInfo("Asia/Seoul")
US_EASTERN = ZoneInfo("America/New_York")
US_MARKET_OPEN_ET = dt_time(9, 30)

DEFAULT_SCAN_LABEL = "프리마켓 실시간 스캔"
DEFAULT_MIN_TURNOVER_PCT = 0.001
DEFAULT_DOLLAR_FLOOR_EARLY = 20_000.0
DEFAULT_DOLLAR_FLOOR_MID = 40_000.0
DEFAULT_DOLLAR_FLOOR_LATE = 80_000.0
DEFAULT_SUMMARY_LIMIT = 30
PREMARKET_CORE_TOP_N = 20
PREMARKET_SUMMARY_SECTION_TOTAL = 13
PREMARKET_GAP_MOMENTUM_SECTION_NAME = "갭상승 모멘텀 Top20"
PREMARKET_INFLOW_SECTION_NAME = "시총대비 집중 자금 유입 Top20"
PREMARKET_OPTIMAL_ENTRY_SECTION_NAME = "현시점 최적진입 Top20 (21시 전용)"
PREMARKET_GAP_MOMENTUM_INDEX_TITLE = "갭상승모멘텀"
PREMARKET_INFLOW_INDEX_TITLE = "집중유입"
PREMARKET_OPTIMAL_ENTRY_INDEX_TITLE = "최적진입"

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


def _clip(value: float, low: float, high: float) -> float:
    if value < low:
        return low
    if value > high:
        return high
    return value


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"y", "yes", "true", "1", "t"}:
        return True
    if text in {"n", "no", "false", "0", "", "-", "none", "n/a"}:
        return False
    return bool(value)


def _parse_iso_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    if "T" in text:
        text = text.split("T", 1)[0]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


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


def _format_pm_tag(row: dict[str, Any]) -> str:
    change_pct = _safe_float(row.get("change_pct", 0.0))
    effective_dollar = _safe_float(row.get("effective_dollar_volume", row.get("dollar_volume", 0.0)))
    turnover_pct = _safe_float(row.get("mcap_turnover_pct", row.get("mcap_ratio", 0.0)))
    pm_close = _safe_float(row.get("pm_close", 0.0))
    pm_vwap = _safe_float(row.get("pm_vwap", 0.0))
    vwap_text = "VWAP상" if pm_close >= pm_vwap else "VWAP하"
    return f"PM {change_pct:+.2f}% | {vwap_text} | ${effective_dollar / 1000.0:,.0f}k | 회전율 {turnover_pct:.4f}%"


def _combine_pm_tag(row: dict[str, Any], base_tag: str) -> str:
    pm_tag = str(row.get("pm_tag") or "").strip()
    base = str(base_tag or "").strip()
    if pm_tag and base and base != "-":
        return f"{pm_tag} || {base}"
    if pm_tag:
        return pm_tag
    return base or "-"


def _confirmed_signal_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame()
    if len(frame) <= 1:
        return frame.iloc[0:0].copy()
    return frame.iloc[:-1].copy()


def _recent_flag(frame: pd.DataFrame, column: str, window: int = 5) -> bool:
    if frame is None or frame.empty or column not in frame.columns:
        return False
    series = frame[column].tail(window)
    try:
        return bool(series.fillna(False).astype(bool).any())
    except Exception:
        return bool(series.any())


def _strategy_payload_or_empty(frame: pd.DataFrame) -> dict[str, Any]:
    if frame is None or frame.empty:
        return {"summary": {}, "results": [], "visible_results": []}
    return build_strategy_payload(frame)


def _build_recent_payload(frame: pd.DataFrame, *, recent_window: int) -> dict[str, Any]:
    return build_detected_signal_payload(
        frame=frame,
        recent_window=recent_window,
        combo_registry={},
        transition_cfg=SCANNER_TRANSITION_CFG,
        core_signal_cfg=SCANNER_CORE_SIGNAL_CFG,
        localize_combo_fn=localize_combo,
        localize_signal_fn=localize_signal,
        summary_limit=8,
    )


def _build_full_detected_payload(frame: pd.DataFrame, *, recent_window: int) -> dict[str, Any]:
    from config import COMBINED_SCAN_REGISTRY

    return build_detected_signal_payload(
        frame=frame,
        recent_window=recent_window,
        combo_registry=COMBINED_SCAN_REGISTRY,
        transition_cfg=SCANNER_TRANSITION_CFG,
        core_signal_cfg=SCANNER_CORE_SIGNAL_CFG,
        localize_combo_fn=localize_combo,
        localize_signal_fn=localize_signal,
        summary_limit=8,
    )


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
        if signal_frame is None or len(signal_frame) < 2:
            return {"ok": False, "ticker": ticker, "skip_reason": "insufficient_signal_frame"}

        recent_window = 5
        dc_ = signal_frame.tail(63).copy()
        confirmed_frame = _confirmed_signal_frame(dc_)
        confirmed_metrics = _compute_post_close_row_metrics(confirmed_frame) if not confirmed_frame.empty else {}
        advanced_metrics = _compute_post_close_row_metrics(dc_)
        for key in (
            "days_since_utbot_buy",
            "days_since_hull_turn_bull",
            "days_since_hull_turn_bear",
            "days_since_pocket_pivot",
            "pocket_pivot_recent",
            "system_turn_bull_last_date",
        ):
            if key in confirmed_metrics:
                advanced_metrics[key] = confirmed_metrics[key]

        latest = signal_frame.iloc[-1]
        prev = signal_frame.iloc[-2] if len(signal_frame) > 1 else latest
        prev2 = signal_frame.iloc[-3] if len(signal_frame) > 2 else prev
        confirmed_latest = confirmed_frame.iloc[-1] if not confirmed_frame.empty else prev

        strategy_payload = _strategy_payload_or_empty(dc_)
        strategy_summary = strategy_payload.get("summary", {}) or {}
        strategy_results = list(strategy_payload.get("visible_results") or [])
        top_strategy = strategy_summary.get("top_strategy")
        detected_payload_full = _build_full_detected_payload(dc_, recent_window=recent_window)
        detected_payload_confirmed = _build_recent_payload(confirmed_frame, recent_window=recent_window)

        combos = [
            {
                "icon": str(item.get("icon", "")),
                "kor": str(item.get("label", "")),
                "dir": str(item.get("dir", "neutral")),
                "tier": int(item.get("tier", 9) or 9),
                "date": str(item.get("date_short", "")),
                "days_ago": int(item.get("days_ago", 99) or 99),
                "key": str(item.get("key", "")),
            }
            for item in detected_payload_full.get("combo_items", [])
        ]
        latest_combo_ts = detected_payload_full.get("latest_combo_ts")
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
            for item in detected_payload_confirmed.get("transition_items", [])
        ]

        current_close = _safe_float(latest.get("Close", 0.0))
        prev_close = _safe_float(prev.get("Close", current_close))
        close_5d_ago = _safe_float(dc_.iloc[-6].get("Close", 0.0)) if len(dc_) >= 6 else 0.0
        chg_value = _safe_float(current_close - prev_close)
        chg_pct = _safe_float((current_close - prev_close) / prev_close * 100.0) if prev_close else 0.0
        chg_5d_pct = _safe_float((current_close - close_5d_ago) / close_5d_ago * 100.0) if close_5d_ago else 0.0
        buy_total = _safe_float(latest.get("Buy_Total", 0.0))
        sell_total = _safe_float(latest.get("Sell_Total", 0.0))
        buy_agree = int(_safe_float(latest.get("Buy_Agree", 0.0)))
        sell_agree = int(_safe_float(latest.get("Sell_Agree", 0.0)))
        es = _safe_float(latest.get("Ensemble_Score", 0.0))
        cf = _safe_float(latest.get("Judgment_Confidence", 0.0))
        market_bias = _safe_float(latest.get("Market_Filter_Bias", 0.0))
        downgrade_count = _safe_float(latest.get("Downgrade_Count", 0.0))
        flip_guard_triggered = bool(latest.get("Flip_Guard_Triggered", False))
        continuation_buy = _safe_float(latest.get("Continuation_Buy_Score", 0.0))
        continuation_sell = _safe_float(latest.get("Continuation_Sell_Score", 0.0))
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
            "WATCH_BUY": 2.5,
            "WATCH_SELL": -2.5,
            "SELL": -5.0,
            "STRONG_SELL": -10.0,
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
        multi_sig = bool((multi_count >= 3) or (any(item["tier"] == 1 for item in combos) and multi_count >= 2))
        recent_hits = sorted(
            [item for item in combos if item.get("days_ago", 99) <= 3],
            key=lambda item: (item.get("tier", 9), item.get("days_ago", 99)),
        )
        multi_hits = [{"icon": h["icon"], "label": h["kor"], "dir": h["dir"], "date": h["date"]} for h in recent_hits]
        if not multi_hits:
            fallback_hits = sorted(combos, key=lambda item: (item.get("tier", 9), item.get("days_ago", 99)))[:6]
            multi_hits = [{"icon": h["icon"], "label": h["kor"], "dir": h["dir"], "date": h["date"]} for h in fallback_hits]

        volume_ratio_20 = _safe_float(latest.get("Volume_Ratio_20", 0.0))
        volume_ratio_50 = _safe_float(latest.get("Volume_Ratio_50", 0.0))
        volume_oscillator = _safe_float(latest.get("Volume_Oscillator", 0.0))
        dollar_volume_20 = _safe_float(latest.get("Dollar_Volume_20", 0.0))
        volume_surge = bool(latest.get("Volume_Surge", False))
        volume_climax_buy = bool(latest.get("Volume_Climax_Buy", False))
        volume_abnormal = bool(volume_surge or volume_ratio_20 >= 2.0)
        volume_bullish = bool((volume_ratio_20 >= 1.2) and (volume_surge or volume_climax_buy or volume_oscillator > 0))

        system_turn_bull = _recent_flag(confirmed_frame, "System_Turn_Bull", recent_window)
        trend_inflect_bull = _recent_flag(confirmed_frame, "Trend_Inflection_Bull", recent_window)
        ut_turn_bull = _recent_flag(confirmed_frame, "UTBot_Buy", recent_window)
        ut_turn_bear = _recent_flag(confirmed_frame, "UTBot_Sell", recent_window)
        hull_turn_bull = _recent_flag(confirmed_frame, "Hull_Turn_Bull", recent_window)
        hull_turn_bear = _recent_flag(confirmed_frame, "Hull_Turn_Bear", recent_window)
        bull_turn_recent = bool(system_turn_bull or trend_inflect_bull or ut_turn_bull or hull_turn_bull)

        prev_hull_bull = bool(
            prev.get("Hull_Turn_Bull", False)
            or prev.get("Hull_Trend", "") == "bullish"
            or prev2.get("Hull_Turn_Bull", False)
            or prev2.get("Hull_Trend", "") == "bullish"
        )
        prev_uptrend = bool(_safe_float(prev.get("Close", 0)) > _safe_float(prev.get("MA20", 0)))
        ma20 = _safe_float(latest.get("MA20", 0.0))
        ma50 = _safe_float(latest.get("MA50", 0.0))
        ma20_prev = _safe_float(prev.get("MA20", ma20))
        ma50_prev = _safe_float(prev.get("MA50", ma50))
        uptrend_ready = bool(current_close > ma20 > ma50) if ma20 and ma50 else False
        pullback_ready = _recent_flag(dc_, "EMA_Pullback_Buy", recent_window)
        uptrend_or_pullback = bool(uptrend_ready or pullback_ready)
        recent_utbot_sell = _recent_flag(confirmed_frame, "UTBot_Sell", recent_window)
        recent_hull_bear = _recent_flag(confirmed_frame, "Hull_Turn_Bear", recent_window)
        strategy_conflict_level = str(strategy_summary.get("conflict_level", "LOW"))
        strategy_bias = str(strategy_summary.get("long_short_bias", "BALANCED"))
        strategy_active_count = int(strategy_summary.get("active_count", 0) or 0)
        buy_combo_present = any(item["dir"] == "buy" for item in combos)
        pullback_combo_present = has_pullback_combo(detected_payload_full.get("combo_items", []))
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
            adx=_safe_float(latest.get("ADX", 0.0)),
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
        confirmed_latest_bar = confirmed_frame.index[-1] if not confirmed_frame.empty else prev.name
        latest_bar_date = confirmed_latest_bar.date().isoformat() if hasattr(confirmed_latest_bar, "date") else str(confirmed_latest_bar)[:10]
        new_52w_high = bool(confirmed_latest.get("New_52W_High", False))

        row = {
            "ticker": ticker,
            "price": _safe_float(current_close),
            "chg_value": chg_value,
            "chg": chg_pct,
            "chg_5d": chg_5d_pct,
            **metrics,
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
            "ctx": localize_context_label(int(_safe_float(latest.get("Market_Context", 0.0)))),
            "action": localize_action_label(str(latest.get("Action_Label", ""))),
            "ut_turn_bull": ut_turn_bull,
            "ut_turn_bear": ut_turn_bear,
            "hull_turn_bull": hull_turn_bull,
            "hull_turn_bear": hull_turn_bear,
            "prev_hull_bull": prev_hull_bull,
            "new_52w_high": new_52w_high,
            "new_52w_closing_high": bool(confirmed_latest.get("New_52W_Closing_High", False)),
            "es": es,
            "cf": cf,
            "scan_score": _safe_float(scan_score),
            "strength": _safe_float(strength),
            "latest_sig": latest_combo_ts.strftime("%Y-%m-%d") if latest_combo_ts is not None else "9999-99-99",
            "latest_sig_ts": latest_combo_ts.timestamp() if latest_combo_ts is not None else 0.0,
            "reason": str(latest.get("Judgment_Reason", "")),
            "ba": buy_agree,
            "sa": sell_agree,
            "buy_total": buy_total,
            "sell_total": sell_total,
            "strategy_conflict_level": strategy_conflict_level,
            "strategy_bias": strategy_bias,
            "strategy_active_count": strategy_active_count,
            "strategies": strategy_results,
            "top_strategy": top_strategy,
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
            "utbot_buy_recent": bool(detected_payload_confirmed.get("utbot_buy_recent", False)),
            "utbot_buy_last_date": str(detected_payload_confirmed.get("utbot_buy_last_date", "없음")),
            "utbot_sell_recent": bool(detected_payload_confirmed.get("utbot_sell_recent", False)),
            "utbot_sell_last_date": str(detected_payload_confirmed.get("utbot_sell_last_date", "없음")),
            "hull_turn_bull_recent": bool(detected_payload_confirmed.get("hull_turn_bull_recent", False)),
            "hull_turn_bull_last_date": str(detected_payload_confirmed.get("hull_turn_bull_last_date", "없음")),
            "hull_turn_bear_recent": bool(detected_payload_confirmed.get("hull_turn_bear_recent", False)),
            "hull_turn_bear_last_date": str(detected_payload_confirmed.get("hull_turn_bear_last_date", "없음")),
            "detected_combo_count": int(detected_payload_full.get("detected_combo_count", 0) or 0),
            "detected_combo_summary": str(detected_payload_full.get("detected_combo_summary", "없음")),
            "detected_transition_count": int(detected_payload_confirmed.get("detected_transition_count", 0) or 0),
            "detected_transition_summary": str(detected_payload_confirmed.get("detected_transition_summary", "없음")),
            "detected_core_count": int(detected_payload_full.get("detected_core_count", 0) or 0),
            "detected_core_summary": str(detected_payload_full.get("detected_core_summary", "없음")),
            "detected_signal_total_count": int(detected_payload_full.get("detected_signal_total_count", 0) or 0),
            "detected_buy_signal_latest_date": str(detected_payload_full.get("detected_buy_signal_latest_date", "없음")),
            "detected_signal_latest_date": str(detected_payload_full.get("detected_signal_latest_date", "없음")),
            "detected_signals": list(detected_payload_full.get("all_items", [])),
            "watch_buy_plus": watch_buy_plus,
            "buy_combo_present": buy_combo_present,
            "latest_bar_date": str(latest_bar_date or "없음"),
            "liquidity_min_dollar": _safe_float(min_dollar_volume),
            "liquidity_min_turnover_pct": _safe_float(min_turnover_pct),
            **advanced_metrics,
        }
        row["pm_supports_bullish"] = not (row["pm_close"] < row["pm_vwap"] and row["change_pct"] < -1.0)
        row["pm_supports_bearish"] = bool((row["pm_close"] < row["pm_vwap"]) or (row["change_pct"] < 0.0))
        row["pm_tag"] = _format_pm_tag(row)

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


def _pm_combined_tag(row: Mapping[str, Any], base_tag: str) -> str:
    return _combine_pm_tag(dict(row or {}), str(base_tag or "-"))


def _ensure_premarket_state_fields(row: Mapping[str, Any]) -> dict[str, Any]:
    row_dict = dict(row or {})
    pm_close = _safe_float(row_dict.get("pm_close", 0.0))
    pm_vwap = _safe_float(row_dict.get("pm_vwap", 0.0))
    change_pct = _safe_float(row_dict.get("change_pct", 0.0))
    row_dict["pm_supports_bullish"] = bool(
        row_dict.get("pm_supports_bullish", not (pm_close < pm_vwap and change_pct < -1.0))
    )
    row_dict["pm_supports_bearish"] = bool(
        row_dict.get("pm_supports_bearish", (pm_close < pm_vwap) or (change_pct < 0.0))
    )
    if not str(row_dict.get("pm_tag", "")).strip():
        row_dict["pm_tag"] = _format_pm_tag(row_dict)
    return row_dict


def _prepare_premarket_rows(rows: Iterable[Mapping[str, Any]], *, run_at_kst: datetime) -> list[dict[str, Any]]:
    target_date = _last_us_market_session_date(run_at_kst)
    prepared = [_ensure_premarket_state_fields(row) for row in (rows or [])]
    prepared = _with_latest_session_buy_turn_flags(prepared, target_date=target_date)
    prepared = _with_post_close_cross_section_metrics(prepared, enabled=True)
    prepared = _with_post_close_setup_scores(prepared)
    return [_ensure_premarket_state_fields(row) for row in prepared]


def _filter_premarket_direction(rows: Iterable[Mapping[str, Any]], *, bullish: bool) -> list[dict[str, Any]]:
    field_name = "pm_supports_bullish" if bullish else "pm_supports_bearish"
    filtered: list[dict[str, Any]] = []
    for row in rows or []:
        row_dict = _ensure_premarket_state_fields(row)
        if bool(row_dict.get(field_name, False)):
            filtered.append(row_dict)
    return filtered


def _is_buy_turn_signal(signal: Any, *, engine: str) -> bool:
    text = str(signal or "").strip().lower()
    if engine not in text:
        return False
    return "buy" in text or "매수" in str(signal or "")


def _premarket_buy_turn_label(row: Mapping[str, Any]) -> str:
    row_dict = dict(row or {})
    signals = list(row_dict.get("transition_signals") or [])
    utbot = (
        any(_is_buy_turn_signal(signal, engine="utbot") for signal in signals)
        or _coerce_bool(row_dict.get("latest_session_utbot_buy_turn", False))
        or _coerce_bool(row_dict.get("utbot_buy_recent", False))
    )
    hull = (
        any(_is_buy_turn_signal(signal, engine="hull") for signal in signals)
        or _coerce_bool(row_dict.get("latest_session_hull_buy_turn", False))
        or _coerce_bool(row_dict.get("hull_turn_bull_recent", False))
    )
    if utbot and hull:
        return "UTBOT+HULL"
    if utbot:
        return "UTBOT"
    if hull:
        return "HULL"
    return ""


def _build_premarket_core_row_line(
    row: Mapping[str, Any],
    index: int,
    *,
    include_intersect: bool = False,
    include_buy_label: bool = False,
) -> str:
    parts = [
        f"{index}. {str(row.get('ticker', '-')).upper()}",
        f"GAP{_safe_float(row.get('gap_pct', 0.0)):+.2f}%",
        f"PM{_safe_float(row.get('change_pct', 0.0)):+.2f}%",
        f"${_safe_float(row.get('effective_dollar_volume', row.get('dollar_volume', 0.0))):,.0f}",
        f"회전율{_safe_float(row.get('mcap_turnover_pct', row.get('mcap_ratio', 0.0))):.3f}%",
    ]
    if include_intersect and _coerce_bool(row.get("pm_core_intersect", False)):
        parts.append("INTERSECT")
    if include_buy_label:
        buy_label = _premarket_buy_turn_label(row)
        if buy_label:
            parts.append(buy_label)
    return " | ".join(parts)


def _with_premarket_gap_momentum_scores(rows: list[dict[str, Any]], *, top_n: int = PREMARKET_CORE_TOP_N) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for row_dict in rows:
        row_dict["pm_gap_momo_score"] = 0.0
        if _coerce_bool(row_dict.get("thin_trade_risk", False)):
            continue
        if not _coerce_bool(row_dict.get("pm_supports_bullish", False)):
            continue
        gap_pct = _safe_float(row_dict.get("gap_pct", 0.0))
        change_pct = _safe_float(row_dict.get("change_pct", 0.0))
        pm_close = _safe_float(row_dict.get("pm_close", 0.0))
        pm_vwap = _safe_float(row_dict.get("pm_vwap", 0.0))
        if gap_pct <= 0.0 or change_pct <= 0.0 or pm_close < pm_vwap:
            continue
        effective_dollar = _safe_float(row_dict.get("effective_dollar_volume", row_dict.get("dollar_volume", 0.0)))
        gap_norm = _clip(gap_pct / 10.0, 0.0, 1.0)
        change_norm = _clip(change_pct / 8.0, 0.0, 1.0)
        dollar_norm = _clip(math.log10(max(1.0, effective_dollar)) / 7.0, 0.0, 1.0)
        score = (gap_norm * 70.0) + (change_norm * 20.0) + (dollar_norm * 10.0)
        row_dict["pm_gap_momo_score"] = round(score, 4)
        selected.append(row_dict)
    selected.sort(
        key=lambda row: (
            -_safe_float(row.get("pm_gap_momo_score", 0.0)),
            -_safe_float(row.get("gap_pct", 0.0)),
            -_safe_float(row.get("change_pct", 0.0)),
            -_safe_float(row.get("effective_dollar_volume", row.get("dollar_volume", 0.0))),
            str(row.get("ticker", "")),
        )
    )
    return selected[: max(0, int(top_n))]


def _with_premarket_inflow_scores(rows: list[dict[str, Any]], *, top_n: int = PREMARKET_CORE_TOP_N) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for row_dict in rows:
        row_dict["pm_inflow_score"] = 0.0
        if _coerce_bool(row_dict.get("thin_trade_risk", False)):
            continue
        if not _coerce_bool(row_dict.get("pm_supports_bullish", False)):
            continue
        turnover_pct = _safe_float(row_dict.get("mcap_turnover_pct", row_dict.get("mcap_ratio", 0.0)))
        effective_dollar = _safe_float(row_dict.get("effective_dollar_volume", row_dict.get("dollar_volume", 0.0)))
        if turnover_pct <= 0.0 or effective_dollar <= 0.0:
            continue
        turnover_norm = _clip(turnover_pct / 0.08, 0.0, 1.0)
        dollar_norm = _clip(math.log10(max(1.0, effective_dollar)) / 7.0, 0.0, 1.0)
        score = (turnover_norm * 80.0) + (dollar_norm * 20.0)
        row_dict["pm_inflow_score"] = round(score, 4)
        selected.append(row_dict)
    selected.sort(
        key=lambda row: (
            -_safe_float(row.get("pm_inflow_score", 0.0)),
            -_safe_float(row.get("mcap_turnover_pct", row.get("mcap_ratio", 0.0))),
            -_safe_float(row.get("effective_dollar_volume", row.get("dollar_volume", 0.0))),
            -_safe_float(row.get("gap_pct", 0.0)),
            str(row.get("ticker", "")),
        )
    )
    return selected[: max(0, int(top_n))]


def _premarket_optimal_entry_sort_key(row: Mapping[str, Any]) -> tuple[float, float, float, float, float, str]:
    return (
        -_safe_float(row.get("pm_entry_score", 0.0)),
        -_safe_float(row.get("pm_entry_b_score", 0.0)),
        -_safe_float(row.get("pm_entry_c_score", 0.0)),
        -_safe_float(row.get("scan_score", 0.0)),
        -_safe_float(row.get("es", 0.0)),
        str(row.get("ticker", "")),
    )


def _with_premarket_optimal_entry_scores(
    rows: list[dict[str, Any]],
    *,
    run_at_kst: datetime,
    top_n: int = PREMARKET_CORE_TOP_N,
) -> list[dict[str, Any]]:
    target_date = _last_us_market_session_date(run_at_kst)
    selected_limit = max(0, int(top_n or 0))
    eligible_rows: list[dict[str, Any]] = []

    for row_dict in rows:
        a_score = int(
            sum(
                [
                    str(row_dict.get("weekly_trend_context", "")).strip().upper() in {"STRONG_UPTREND", "UPTREND"},
                    _coerce_bool(row_dict.get("ichimoku_above_cloud", False)),
                    _safe_float(row_dict.get("drawdown_from_52w_high_pct", -999.0)) >= -20.0,
                    _safe_float(row_dict.get("adx", 0.0)) >= 20.0,
                    _safe_float(row_dict.get("hma60_slope_pct", 0.0)) > 0.0,
                ]
            )
        )

        latest_buy_date = _parse_iso_date(row_dict.get("detected_buy_signal_latest_date"))
        latest_buy_within_2d = bool(latest_buy_date is not None and 0 <= int((target_date - latest_buy_date).days) <= 2)
        b_score = int(
            sum(
                [
                    _coerce_bool(row_dict.get("pullback_reentry", False))
                    or _coerce_bool(row_dict.get("pocket_pivot_candidate", False))
                    or _coerce_bool(row_dict.get("gap_setup_candidate", False)),
                    _safe_float(row_dict.get("pm_close", 0.0)) >= _safe_float(row_dict.get("pm_vwap", 0.0)),
                    _safe_float(row_dict.get("gap_pct", 0.0)) > 0.0 and _safe_float(row_dict.get("change_pct", 0.0)) > 0.0,
                    latest_buy_within_2d,
                    _coerce_bool(row_dict.get("latest_session_utbot_buy_turn", False))
                    or _coerce_bool(row_dict.get("latest_session_hull_buy_turn", False))
                    or _coerce_bool(row_dict.get("utbot_buy_recent", False))
                    or _coerce_bool(row_dict.get("hull_turn_bull_recent", False)),
                ]
            )
        )

        c_score = int(
            sum(
                [
                    _safe_float(row_dict.get("mcap_turnover_pct", row_dict.get("mcap_ratio", 0.0))) >= 0.005,
                    _safe_float(row_dict.get("effective_dollar_volume", row_dict.get("dollar_volume", 0.0))) >= 150_000.0,
                    _safe_float(row_dict.get("cmf", 0.0)) > 0.05,
                    _safe_float(row_dict.get("obv_slope", 0.0)) > 0.1,
                ]
            )
        )

        hard_gate_pass = (not _coerce_bool(row_dict.get("thin_trade_risk", False))) and _coerce_bool(
            row_dict.get("pm_supports_bullish", False)
        )
        freshness_pass = latest_buy_within_2d
        a_pass = a_score >= 4
        b_pass = b_score >= 3
        c_pass = c_score >= 2
        eligible = bool(hard_gate_pass and freshness_pass and a_pass and b_pass and c_pass)

        abc_norm = ((_safe_float(a_score) / 5.0) + (_safe_float(b_score) / 5.0) + (_safe_float(c_score) / 4.0)) / 3.0
        scan_norm = _clip(_safe_float(row_dict.get("scan_score", 0.0)) / 200.0, 0.0, 1.0)
        es_norm = _clip(_safe_float(row_dict.get("es", 0.0)) / 100.0, 0.0, 1.0)
        pm_change_norm = _clip(_safe_float(row_dict.get("change_pct", 0.0)) / 8.0, 0.0, 1.0)
        turnover_norm = _clip(_safe_float(row_dict.get("mcap_turnover_pct", row_dict.get("mcap_ratio", 0.0))) / 0.08, 0.0, 1.0)
        final_score = (abc_norm * 100.0) + (scan_norm * 8.0) + (es_norm * 4.0) + (pm_change_norm * 6.0) + (turnover_norm * 4.0)

        row_dict["pm_entry_a_score"] = a_score
        row_dict["pm_entry_b_score"] = b_score
        row_dict["pm_entry_c_score"] = c_score
        row_dict["pm_entry_score"] = round(final_score, 4)
        row_dict["pm_entry_rank"] = 0
        row_dict["pm_entry_selected"] = False

        score_text = f"A{a_score}/B{b_score}/C{c_score}"
        if not hard_gate_pass:
            row_dict["pm_entry_reason"] = f"{score_text} | HARD_FAIL:thin_trade_or_pm_bearish"
        elif eligible:
            row_dict["pm_entry_reason"] = f"{score_text} | PASS"
        else:
            failed_dims: list[str] = []
            if not freshness_pass:
                failed_dims.append("FRESH")
            if not a_pass:
                failed_dims.append("A")
            if not b_pass:
                failed_dims.append("B")
            if not c_pass:
                failed_dims.append("C")
            row_dict["pm_entry_reason"] = f"{score_text} | GATE_FAIL:{'/'.join(failed_dims) if failed_dims else '-'}"

        if eligible:
            eligible_rows.append(row_dict)

    selected_rows = sorted(eligible_rows, key=_premarket_optimal_entry_sort_key)[:selected_limit]
    for rank, row_dict in enumerate(selected_rows, start=1):
        row_dict["pm_entry_rank"] = rank
        row_dict["pm_entry_selected"] = True

    return rows


def _select_premarket_optimal_entry_rows(rows: Iterable[Mapping[str, Any]], *, top_n: int = PREMARKET_CORE_TOP_N) -> list[dict[str, Any]]:
    selected = [dict(row or {}) for row in (rows or []) if _coerce_bool(dict(row or {}).get("pm_entry_selected", False))]
    if not selected:
        return []
    selected.sort(
        key=lambda row: (
            _safe_float(row.get("pm_entry_rank", 0.0)) if _safe_float(row.get("pm_entry_rank", 0.0)) > 0.0 else 1e9,
            str(row.get("ticker", "")),
        )
    )
    return selected[: max(0, int(top_n))]


def _mark_core_intersections(
    gap_rows: list[dict[str, Any]],
    inflow_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    gap_tickers = {str(row.get("ticker", "")).strip().upper() for row in gap_rows}
    inflow_tickers = {str(row.get("ticker", "")).strip().upper() for row in inflow_rows}
    intersection = {ticker for ticker in gap_tickers.intersection(inflow_tickers) if ticker}
    for row_dict in gap_rows:
        ticker = str(row_dict.get("ticker", "")).strip().upper()
        row_dict["pm_core_intersect"] = ticker in intersection
    for row_dict in inflow_rows:
        ticker = str(row_dict.get("ticker", "")).strip().upper()
        row_dict["pm_core_intersect"] = ticker in intersection
    return gap_rows, inflow_rows


def _build_premarket_summary_sections(
    rows: Iterable[Mapping[str, Any]],
    *,
    run_at_kst: datetime,
) -> dict[str, list[dict[str, Any]]]:
    prepared_rows = _prepare_premarket_rows(rows, run_at_kst=run_at_kst)
    gap_momentum_rows = _with_premarket_gap_momentum_scores(prepared_rows, top_n=PREMARKET_CORE_TOP_N)
    inflow_top_rows = _with_premarket_inflow_scores(prepared_rows, top_n=PREMARKET_CORE_TOP_N)
    gap_momentum_rows, inflow_top_rows = _mark_core_intersections(gap_momentum_rows, inflow_top_rows)
    _with_premarket_optimal_entry_scores(prepared_rows, run_at_kst=run_at_kst, top_n=PREMARKET_CORE_TOP_N)
    optimal_entry_rows = _select_premarket_optimal_entry_rows(prepared_rows, top_n=PREMARKET_CORE_TOP_N)

    legacy_turn_rows = _filter_premarket_direction(
        filter_turn_rows_for_telegram(select_us_session_turn_rows(prepared_rows, run_at_kst=run_at_kst)),
        bullish=True,
    )
    legacy_pullback_rows = _filter_premarket_direction(
        select_pullback_reentry_rows_for_telegram(prepared_rows),
        bullish=True,
    )
    legacy_hull_bear_rows = _filter_premarket_direction(
        select_us_session_hull_bear_rows(prepared_rows, run_at_kst=run_at_kst),
        bullish=False,
    )
    legacy_52w_high_rows = _filter_premarket_direction(
        select_us_session_52w_high_rows(prepared_rows, run_at_kst=run_at_kst),
        bullish=True,
    )
    pullback_filter_rows = _filter_premarket_direction(
        select_post_close_pullback_rows_for_telegram(prepared_rows),
        bullish=True,
    )
    chase_filter_rows = _filter_premarket_direction(
        select_post_close_chase_rows_for_telegram(prepared_rows),
        bullish=True,
    )
    buy_turn_filter_rows = _filter_premarket_direction(
        select_post_close_buy_turn_rows_for_telegram(prepared_rows, run_at_kst=run_at_kst),
        bullish=True,
    )
    gap_setup_rows = _filter_premarket_direction(
        select_post_close_gap_setup_rows_for_telegram(prepared_rows),
        bullish=True,
    )
    pocket_pivot_rows = _filter_premarket_direction(
        select_post_close_pocket_pivot_rows_for_telegram(prepared_rows),
        bullish=True,
    )
    five_day_top_rows = _filter_premarket_direction(
        select_post_close_top_5d_rows_for_telegram(prepared_rows),
        bullish=True,
    )

    return {
        "prepared_rows": prepared_rows,
        "gap_momentum_rows": gap_momentum_rows,
        "inflow_top_rows": inflow_top_rows,
        "optimal_entry_rows": optimal_entry_rows,
        "legacy_turn_rows": legacy_turn_rows,
        "legacy_pullback_rows": legacy_pullback_rows,
        "legacy_hull_bear_rows": legacy_hull_bear_rows,
        "legacy_52w_high_rows": legacy_52w_high_rows,
        "pullback_filter_rows": pullback_filter_rows,
        "chase_filter_rows": chase_filter_rows,
        "buy_turn_filter_rows": buy_turn_filter_rows,
        "gap_setup_rows": gap_setup_rows,
        "pocket_pivot_rows": pocket_pivot_rows,
        "five_day_top_rows": five_day_top_rows,
    }


def _build_premarket_index_line(section_rows: Mapping[str, list[dict[str, Any]]]) -> str:
    return (
        f"- 요약 인덱스: {PREMARKET_GAP_MOMENTUM_INDEX_TITLE} {len(section_rows['gap_momentum_rows'])}"
        f" | {PREMARKET_INFLOW_INDEX_TITLE} {len(section_rows['inflow_top_rows'])}"
        f" | {PREMARKET_OPTIMAL_ENTRY_INDEX_TITLE} {len(section_rows['optimal_entry_rows'])}"
        f" | {POST_CLOSE_INDEX_TITLES['legacy_turn']} {len(section_rows['legacy_turn_rows'])}"
        f" | {POST_CLOSE_INDEX_TITLES['legacy_pullback']} {len(section_rows['legacy_pullback_rows'])}"
        f" | {POST_CLOSE_INDEX_TITLES['legacy_hull_bear']} {len(section_rows['legacy_hull_bear_rows'])}"
        f" | {POST_CLOSE_INDEX_TITLES['legacy_52w_high']} {len(section_rows['legacy_52w_high_rows'])}"
        f" | {POST_CLOSE_INDEX_TITLES['pullback_filter']} {len(section_rows['pullback_filter_rows'])}"
        f" | {POST_CLOSE_INDEX_TITLES['chase_filter']} {len(section_rows['chase_filter_rows'])}"
        f" | {POST_CLOSE_INDEX_TITLES['buy_turn_filter']} {len(section_rows['buy_turn_filter_rows'])}"
        f" | {POST_CLOSE_INDEX_TITLES['gap_setup']} {len(section_rows['gap_setup_rows'])}"
        f" | {POST_CLOSE_INDEX_TITLES['pocket_pivot']} {len(section_rows['pocket_pivot_rows'])}"
        f" | {POST_CLOSE_INDEX_TITLES['five_day_top']} {len(section_rows['five_day_top_rows'])}"
    )


def _render_premarket_summary(
    *,
    section_rows: Mapping[str, list[dict[str, Any]]],
    run_at_kst: datetime,
    universe_count: int,
    skip_count: int,
    scan_label: str,
    summary_limit: int,
) -> str:
    target_us_session_date = _last_us_market_session_date(run_at_kst)
    prepared_rows = list(section_rows.get("prepared_rows", []))
    total_limit = max(0, int(summary_limit))
    effective_universe_count = int(universe_count) if int(universe_count) > 0 else len(prepared_rows)

    lines = [
        f"[{str(scan_label or DEFAULT_SCAN_LABEL)}] {run_at_kst.strftime('%Y-%m-%d %H:%M:%S')} KST",
        f"- 대상 미국 세션일: {target_us_session_date.isoformat()} (US/Eastern)",
        "- 프리마켓 기준: 합성 프리장 일봉 + 미완성 일봉 보수 적용",
        f"- 유니버스: {effective_universe_count}",
        f"- 스캔 결과: {len(prepared_rows)} | 제외: {max(0, int(skip_count))}",
        _build_premarket_index_line(section_rows),
        "",
    ]

    sections = [
        _build_summary_section_lines(
            section_index=1,
            section_total=PREMARKET_SUMMARY_SECTION_TOTAL,
            section_name=PREMARKET_GAP_MOMENTUM_SECTION_NAME,
            criteria="thin_trade_risk=N + pm_supports_bullish=Y + gap>0 + PM>0 + pm_close>=pm_vwap | score=gap 중심 + PM + dollar 보조",
            rows=section_rows["gap_momentum_rows"],
            summary_limit=total_limit,
            tag_builder=lambda row: "-",
            row_builder=lambda row, idx: _build_premarket_core_row_line(row, idx, include_intersect=True),
        ),
        _build_summary_section_lines(
            section_index=2,
            section_total=PREMARKET_SUMMARY_SECTION_TOTAL,
            section_name=PREMARKET_INFLOW_SECTION_NAME,
            criteria="thin_trade_risk=N + pm_supports_bullish=Y + turnover>0 + dollar>0 | score=turnover 중심 + dollar 보조",
            rows=section_rows["inflow_top_rows"],
            summary_limit=total_limit,
            tag_builder=lambda row: "-",
            row_builder=lambda row, idx: _build_premarket_core_row_line(row, idx, include_intersect=True),
        ),
        _build_summary_section_lines(
            section_index=3,
            section_total=PREMARKET_SUMMARY_SECTION_TOTAL,
            section_name=PREMARKET_OPTIMAL_ENTRY_SECTION_NAME,
            criteria="A>=4/5 + B>=3/5 + C>=2/4 + thin_trade_risk=N + pm_supports_bullish=Y",
            rows=section_rows["optimal_entry_rows"],
            summary_limit=total_limit,
            tag_builder=lambda row: "-",
            row_builder=lambda row, idx: _build_premarket_core_row_line(row, idx, include_buy_label=True),
        ),
        _build_summary_section_lines(
            section_index=4,
            section_total=PREMARKET_SUMMARY_SECTION_TOTAL,
            section_name=POST_CLOSE_SECTION_TITLES["legacy_turn"],
            criteria="legacy UTBot/HULL buy-turn + volume>1.0x + pm_supports_bullish",
            rows=section_rows["legacy_turn_rows"],
            summary_limit=total_limit,
            tag_builder=lambda row: _pm_combined_tag(
                row,
                ", ".join(list(dict(row or {}).get("transition_signals") or [])) or "-",
            ),
        ),
        _build_summary_section_lines(
            section_index=5,
            section_total=PREMARKET_SUMMARY_SECTION_TOTAL,
            section_name=POST_CLOSE_SECTION_TITLES["legacy_pullback"],
            criteria="pullback_reentry=True + volume>1.0x + pm_supports_bullish",
            rows=section_rows["legacy_pullback_rows"],
            summary_limit=total_limit,
            tag_builder=lambda row: _pm_combined_tag(row, "Pullback reentry"),
        ),
        _build_summary_section_lines(
            section_index=6,
            section_total=PREMARKET_SUMMARY_SECTION_TOTAL,
            section_name=POST_CLOSE_SECTION_TITLES["legacy_hull_bear"],
            criteria=f"hull_turn_bear_last_date == {target_us_session_date.isoformat()} + pm_supports_bearish",
            rows=section_rows["legacy_hull_bear_rows"],
            summary_limit=total_limit,
            tag_builder=lambda row: _pm_combined_tag(row, "HULL sell turn"),
        ),
        _build_summary_section_lines(
            section_index=7,
            section_total=PREMARKET_SUMMARY_SECTION_TOTAL,
            section_name=POST_CLOSE_SECTION_TITLES["legacy_52w_high"],
            criteria=f"new_52w_high=True + latest_bar_date == {target_us_session_date.isoformat()} + pm_supports_bullish",
            rows=section_rows["legacy_52w_high_rows"],
            summary_limit=total_limit,
            tag_builder=lambda row: _pm_combined_tag(row, "52W high"),
        ),
        _build_summary_section_lines(
            section_index=8,
            section_total=PREMARKET_SUMMARY_SECTION_TOTAL,
            section_name=POST_CLOSE_SECTION_TITLES["pullback_filter"],
            criteria=(
                "uptrend_persistent=Y + hma60_slope_pct>0 + pullback_from_swing_high_pct<-2 + "
                "drawdown_from_20d_high_pct<-1 + pullback_atr_multiple<=3.5 + "
                "(pullback_ready or pullback_reentry) + volume_dry_up_score>=1 + "
                "no recent UT/HULL sell + pm_supports_bullish"
            ),
            rows=section_rows["pullback_filter_rows"],
            summary_limit=total_limit,
            tag_builder=lambda row: _pm_combined_tag(row, "Pullback filter"),
        ),
        _build_summary_section_lines(
            section_index=9,
            section_total=PREMARKET_SUMMARY_SECTION_TOTAL,
            section_name=POST_CLOSE_SECTION_TITLES["chase_filter"],
            criteria=(
                "bull_strength_recent=Y + uptrend_persistent=Y + hma20/60 slope>0 + volume_bullish=Y + "
                "adx>=18 + rs_rank_vs_index>=55 + multi_buy>=2 + dist_sma20_pct<30 + "
                "zscore20<3.5 + scan_score>=120 + pm_supports_bullish"
            ),
            rows=section_rows["chase_filter_rows"],
            summary_limit=total_limit,
            tag_builder=lambda row: _pm_combined_tag(row, "Chase filter"),
        ),
        _build_summary_section_lines(
            section_index=10,
            section_total=PREMARKET_SUMMARY_SECTION_TOTAL,
            section_name=POST_CLOSE_SECTION_TITLES["buy_turn_filter"],
            criteria=(
                "(latest_session_turn or days<=2) + (utbot_buy_recent or hull_turn_bull_recent or bull_turn_recent) + "
                "cmf>-0.10 + obv_slope>0 + volume_ratio_20>0.9 + no sell on target session + pm_supports_bullish"
            ),
            rows=section_rows["buy_turn_filter_rows"],
            summary_limit=total_limit,
            tag_builder=lambda row: _pm_combined_tag(
                row,
                str(dict(row or {}).get("buy_turn_filter_tag") or "Buy turn filter"),
            ),
        ),
        _build_summary_section_lines(
            section_index=11,
            section_total=PREMARKET_SUMMARY_SECTION_TOTAL,
            section_name=POST_CLOSE_SECTION_TITLES["gap_setup"],
            criteria=(
                "gate>=3/5 + score(sorted by score/gate/scan/es) | "
                "DryUp + 20DHigh proximity + BB/ATR compression + RS leadership + HMA/ADX trend + pm_supports_bullish"
            ),
            rows=section_rows["gap_setup_rows"],
            summary_limit=total_limit,
            tag_builder=lambda row: _pm_combined_tag(
                row,
                str(dict(row or {}).get("gap_setup_tag") or "Gap setup"),
            ),
        ),
        _build_summary_section_lines(
            section_index=12,
            section_total=PREMARKET_SUMMARY_SECTION_TOTAL,
            section_name=POST_CLOSE_SECTION_TITLES["pocket_pivot"],
            criteria=(
                "gate>=3/5 + score(sorted by score/gate/scan/es) | "
                "Volume expansion + recent UT buy + shallow pullback + CMF/OBV accumulation + multi-buy + pm_supports_bullish"
            ),
            rows=section_rows["pocket_pivot_rows"],
            summary_limit=total_limit,
            tag_builder=lambda row: _pm_combined_tag(
                row,
                str(dict(row or {}).get("pocket_pivot_tag") or "Pocket pivot"),
            ),
        ),
        _build_summary_section_lines(
            section_index=13,
            section_total=PREMARKET_SUMMARY_SECTION_TOTAL,
            section_name=POST_CLOSE_SECTION_TITLES["five_day_top"],
            criteria="chg_5d > 0 sorted by chg_5d/scan_score/es + pm_supports_bullish",
            rows=section_rows["five_day_top_rows"],
            summary_limit=total_limit,
            tag_builder=lambda row: _pm_combined_tag(
                row,
                str(dict(row or {}).get("five_day_top_tag") or f"5D {_safe_float(dict(row or {}).get('chg_5d', 0.0)):+.2f}%"),
            ),
        ),
    ]
    for block in sections:
        lines.extend(block)
        lines.append("")

    if lines and not str(lines[-1]).strip():
        lines.pop()
    return "\n".join(lines)


def format_telegram_summary(
    rows: list[dict[str, Any]],
    run_at_kst: datetime,
    universe_count: int,
    *,
    skip_count: int = 0,
    scan_label: str = DEFAULT_SCAN_LABEL,
    summary_limit: int = DEFAULT_SUMMARY_LIMIT,
) -> str:
    section_rows = _build_premarket_summary_sections(rows, run_at_kst=run_at_kst)
    return _render_premarket_summary(
        section_rows=section_rows,
        run_at_kst=run_at_kst,
        universe_count=universe_count,
        skip_count=skip_count,
        scan_label=scan_label,
        summary_limit=summary_limit,
    )


def _merge_run_stats(merge_dir: Path) -> dict[str, Any]:
    meta_files = sorted(Path(merge_dir).glob("**/run_meta_*.json"))
    universe_count = 0
    skip_count = 0
    shard_ticker_count = 0
    performance_summaries: list[dict[str, Any]] = []
    for file_path in meta_files:
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        universe_count = max(universe_count, int(_safe_float(payload.get("universe_count", 0))))
        shard_ticker_count += int(_safe_float(payload.get("shard_ticker_count", 0)))
        perf = payload.get("performance") or {}
        skip_count += int(_safe_float(perf.get("skip_count", 0)))
        performance_summaries.append(dict(perf))
    return {
        "meta_file_count": len(meta_files),
        "universe_count": universe_count,
        "skip_count": skip_count,
        "shard_ticker_count": shard_ticker_count,
        "shard_performance": performance_summaries,
    }


def _premarket_section_counts(section_rows: Mapping[str, list[dict[str, Any]]]) -> dict[str, int]:
    return {
        "gap_momo_count": len(section_rows.get("gap_momentum_rows", [])),
        "inflow_top_count": len(section_rows.get("inflow_top_rows", [])),
        "optimal_entry_count": len(section_rows.get("optimal_entry_rows", [])),
        "legacy_turn_count": len(section_rows.get("legacy_turn_rows", [])),
        "legacy_pullback_count": len(section_rows.get("legacy_pullback_rows", [])),
        "legacy_hull_bear_count": len(section_rows.get("legacy_hull_bear_rows", [])),
        "legacy_52w_high_count": len(section_rows.get("legacy_52w_high_rows", [])),
        "pullback_filter_count": len(section_rows.get("pullback_filter_rows", [])),
        "chase_filter_count": len(section_rows.get("chase_filter_rows", [])),
        "buy_turn_filter_count": len(section_rows.get("buy_turn_filter_rows", [])),
        "gap_setup_count": len(section_rows.get("gap_setup_rows", [])),
        "pocket_pivot_count": len(section_rows.get("pocket_pivot_rows", [])),
        "five_day_top_count": len(section_rows.get("five_day_top_rows", [])),
    }


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
    parser.add_argument("--summary-limit", type=int, default=DEFAULT_SUMMARY_LIMIT)
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
        merge_stats = _merge_run_stats(merge_dir)
        summary_limit = max(0, int(args.summary_limit))
        section_rows = _build_premarket_summary_sections(rows, run_at_kst=run_at_kst)
        prepared_rows = list(section_rows.get("prepared_rows", []))
        section_counts = _premarket_section_counts(section_rows)
        effective_universe_count = int(merge_stats.get("universe_count", 0) or 0) or len(prepared_rows)
        summary_text = _render_premarket_summary(
            section_rows=section_rows,
            run_at_kst=run_at_kst,
            universe_count=effective_universe_count,
            skip_count=int(merge_stats.get("skip_count", 0) or 0),
            scan_label=str(args.scan_label),
            summary_limit=summary_limit,
        )

        summary_path = out_dir / "premarket_summary.txt"
        summary_path.write_text(summary_text, encoding="utf-8")
        csv_path = out_dir / "premarket_results.csv"
        merged_json_path = out_dir / "scan_rows_merged.json"
        merged_json_path.write_text(json.dumps(prepared_rows, ensure_ascii=False, indent=2), encoding="utf-8")
        df = pd.DataFrame(prepared_rows)
        if not df.empty:
            df.to_csv(csv_path, index=False)
        merge_meta_path = out_dir / "run_meta_merged.json"
        merge_meta_payload = {
            "run_at_kst": run_at_kst.isoformat(),
            "scan_label": str(args.scan_label),
            "merge_dir": str(merge_dir),
            "universe_count": effective_universe_count,
            "merged_row_count": len(prepared_rows),
            "summary_limit": summary_limit,
            "performance": {
                "match_count": len(prepared_rows),
                "skip_count": int(merge_stats.get("skip_count", 0) or 0),
                "source_meta_count": int(merge_stats.get("meta_file_count", 0) or 0),
                "source_shard_ticker_count": int(merge_stats.get("shard_ticker_count", 0) or 0),
            },
            **section_counts,
        }
        merge_meta_path.write_text(json.dumps(merge_meta_payload, ensure_ascii=False, indent=2), encoding="utf-8")

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
        "summary_limit": max(0, int(args.summary_limit)),
        "performance": scan_result.perf,
    }
    meta_path.write_text(json.dumps(meta_payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()


