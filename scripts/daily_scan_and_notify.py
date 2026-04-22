from __future__ import annotations

import argparse
import bisect
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
from typing import Any, Callable, Iterable, Mapping
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
    scanner_csv_field_specs,
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

SCAN_MODE_LABELS: dict[str, str] = {
    "post_close": "자동 스캔",
    "pre_market": "프리마켓 스캔",
    "early_session": "얼리세션 스캔 장중 미확정 추세",
}
US_MARKET_OPEN_ET = dt_time(9, 30)
US_MARKET_CLOSE_ET = dt_time(16, 0)
US_REGULAR_SESSION_MINUTES = 390.0

ETF_UNIVERSE_ITEMS: tuple[dict[str, str], ...] = (
    {"requested": "러셀1000", "resolved": "IWB"},
    {"requested": "MSCI(USA)", "resolved": "EUSA"},
    {"requested": "나스닥100", "resolved": "QQQ"},
    {"requested": "S&P500", "resolved": "SPY"},
)
RUSSELL2000_UNIVERSE_ITEMS: tuple[dict[str, str], ...] = (
    {"requested": "러셀2000", "resolved": "IWM"},
)
UNIVERSE_PROFILE_ITEMS: dict[str, tuple[dict[str, str], ...]] = {
    "default": ETF_UNIVERSE_ITEMS,
    "russell2000": RUSSELL2000_UNIVERSE_ITEMS,
}

SCANNER_TRANSITION_CFG = {
    "UTBot_Buy": {"label": "UTBot 전환↑", "icon": "▲", "dir": "buy"},
    "UTBot_Sell": {"label": "UTBot 전환↓", "icon": "▼", "dir": "sell"},
    "Hull_Turn_Bull": {"label": "HULL 전환↑", "icon": "▲", "dir": "buy"},
    "Hull_Turn_Bear": {"label": "HULL 전환↓", "icon": "▼", "dir": "sell"},
}

POST_CLOSE_LATEST_SESSION_FIELD_SPECS: tuple[dict[str, str], ...] = (
    {"group": "session", "key": "latest_session_utbot_buy_turn", "label": "RecentSessionUTBotBuyTurn", "type": "bool", "description": "UTBot buy turn on latest US session", "rule": "utbot_buy_last_date == target session", "example": "Y"},
    {"group": "session", "key": "latest_session_hull_buy_turn", "label": "RecentSessionHULLBuyTurn", "type": "bool", "description": "Hull buy turn on latest US session", "rule": "hull_turn_bull_last_date == target session", "example": "N"},
    {"group": "price", "key": "chg_5d", "label": "Change5D(%)", "type": "number", "description": "5-session return", "rule": "(close-close_5d_ago)/close_5d_ago*100", "example": "3.42"},
    {"group": "trend", "key": "dist_sma20_pct", "label": "DistSMA20(%)", "type": "number", "description": "Distance from SMA20", "rule": "(close-MA20)/MA20*100", "example": "1.25"},
    {"group": "trend", "key": "dist_sma50_pct", "label": "DistSMA50(%)", "type": "number", "description": "Distance from SMA50", "rule": "(close-MA50)/MA50*100", "example": "4.20"},
    {"group": "trend", "key": "dist_sma120_pct", "label": "DistSMA120(%)", "type": "number", "description": "Distance from SMA120", "rule": "(close-MA120)/MA120*100", "example": "8.10"},
    {"group": "trend", "key": "dist_sma200_pct", "label": "DistSMA200(%)", "type": "number", "description": "Distance from SMA200", "rule": "(close-MA200)/MA200*100", "example": "11.50"},
    {"group": "trend", "key": "dist_ema8_pct", "label": "DistEMA8(%)", "type": "number", "description": "Distance from EMA8", "rule": "(close-EMA8)/EMA8*100", "example": "0.92"},
    {"group": "trend", "key": "dist_ema21_pct", "label": "DistEMA21(%)", "type": "number", "description": "Distance from EMA21", "rule": "(close-EMA21)/EMA21*100", "example": "2.31"},
    {"group": "trend", "key": "dist_ema50_pct", "label": "DistEMA50(%)", "type": "number", "description": "Distance from EMA50", "rule": "(close-EMA50)/EMA50*100", "example": "4.65"},
    {"group": "trend", "key": "hma20_slope_pct", "label": "HMA20Slope(%)", "type": "number", "description": "HMA20 one-bar slope", "rule": "(HMA-HMA[-1])/abs(HMA[-1])*100", "example": "0.44"},
    {"group": "trend", "key": "hma60_slope_pct", "label": "HMA60Slope(%)", "type": "number", "description": "HMA60 one-bar slope", "rule": "(HMA60-HMA60[-1])/abs(HMA60[-1])*100", "example": "0.18"},
    {"group": "trend", "key": "hma200_slope_pct", "label": "HMA200Slope(%)", "type": "number", "description": "HMA200 one-bar slope", "rule": "(HMA200-HMA200[-1])/abs(HMA200[-1])*100", "example": "0.07"},
    {"group": "trend", "key": "adx", "label": "ADX", "type": "number", "description": "Average directional index", "rule": "ADX", "example": "23.5"},
    {"group": "trend", "key": "ichimoku_above_cloud", "label": "AboveIchimokuCloud", "type": "bool", "description": "Close above cloud", "rule": "close > max(SenkouA,SenkouB)", "example": "Y"},
    {"group": "trend", "key": "ichimoku_below_cloud", "label": "BelowIchimokuCloud", "type": "bool", "description": "Close below cloud", "rule": "close < min(SenkouA,SenkouB)", "example": "N"},
    {"group": "pullback", "key": "drawdown_from_52w_high_pct", "label": "DrawdownFrom52WHigh(%)", "type": "number", "description": "Drawdown from 52-week high", "rule": "(close-52w_high)/52w_high*100", "example": "-14.8"},
    {"group": "pullback", "key": "drawdown_from_20d_high_pct", "label": "DrawdownFrom20DHigh(%)", "type": "number", "description": "Drawdown from 20-day high", "rule": "(close-20d_high)/20d_high*100", "example": "-4.3"},
    {"group": "pullback", "key": "pullback_from_swing_high_pct", "label": "PullbackFromSwingHigh(%)", "type": "number", "description": "Pullback from swing high", "rule": "(close-swing_high)/swing_high*100", "example": "-6.1"},
    {"group": "volatility", "key": "zscore20", "label": "ZScore20", "type": "number", "description": "20-bar close z-score", "rule": "(close-mean20)/std20", "example": "1.12"},
    {"group": "volatility", "key": "bb_percent_b", "label": "BBPercentB", "type": "number", "description": "Bollinger %B", "rule": "Percent_B", "example": "0.73"},
    {"group": "volatility", "key": "atr_pct", "label": "ATR(%)", "type": "number", "description": "ATR percentage of close", "rule": "ATR/close*100", "example": "2.15"},
    {"group": "volatility", "key": "pullback_atr_multiple", "label": "PullbackATRMultiple", "type": "number", "description": "Pullback in ATR multiples", "rule": "(20d_high-close)/ATR", "example": "1.84"},
    {"group": "turn", "key": "days_since_utbot_buy", "label": "DaysSinceUTBotBuy", "type": "number", "description": "Bars since latest UTBot buy turn", "rule": "as_of - last(UTBot_Buy)", "example": "2"},
    {"group": "turn", "key": "days_since_hull_turn_bull", "label": "DaysSinceHullBullTurn", "type": "number", "description": "Bars since latest hull bull turn", "rule": "as_of - last(Hull_Turn_Bull)", "example": "4"},
    {"group": "turn", "key": "days_since_hull_turn_bear", "label": "DaysSinceHullBearTurn", "type": "number", "description": "Bars since latest hull bear turn", "rule": "as_of - last(Hull_Turn_Bear)", "example": "12"},
    {"group": "turn", "key": "system_turn_bull_last_date", "label": "SystemTurnBullLastDate", "type": "date", "description": "Latest system bull turn date", "rule": "last(System_Turn_Bull)", "example": "2026-04-20"},
    {"group": "volume", "key": "volume_dry_up_score", "label": "VolumeDryUpScore", "type": "number", "description": "Dry-up score from volume ratio", "rule": "clip((1-R20)*100,0,100)", "example": "24"},
    {"group": "volume", "key": "volume_expansion_score", "label": "VolumeExpansionScore", "type": "number", "description": "Expansion score from volume ratio", "rule": "clip((R20-1)*100,0,100)", "example": "37"},
    {"group": "volume", "key": "obv_slope", "label": "OBVSlope", "type": "number", "description": "OBV slope", "rule": "OBV_Slope", "example": "0.13"},
    {"group": "volume", "key": "cmf", "label": "CMF", "type": "number", "description": "Chaikin money flow", "rule": "CMF", "example": "0.08"},
    {"group": "volume", "key": "volume_climax_flag", "label": "VolumeClimaxFlag", "type": "bool", "description": "Volume climax event flag", "rule": "Volume_Climax_Buy or Volume_Climax_Sell", "example": "N"},
    {"group": "distance", "key": "dist_vwap_pct", "label": "DistVWAP(%)", "type": "number", "description": "Distance from VWAP", "rule": "(close-VWAP)/VWAP*100", "example": "1.62"},
    {"group": "distance", "key": "dist_bb_mid_pct", "label": "DistBBMid(%)", "type": "number", "description": "Distance from Bollinger mid", "rule": "(close-BB_Mid)/BB_Mid*100", "example": "1.10"},
    {"group": "distance", "key": "dist_bb_upper_pct", "label": "DistBBUpper(%)", "type": "number", "description": "Distance from Bollinger upper", "rule": "(close-BB_Up)/BB_Up*100", "example": "-0.85"},
    {"group": "risk", "key": "gap_risk_2pct", "label": "GapRisk2Pct", "type": "bool", "description": "Absolute gap >= 2%", "rule": "abs((open-prev_close)/prev_close)*100 >= 2", "example": "Y"},
    {"group": "risk", "key": "gap_risk_atr", "label": "GapRiskATR", "type": "bool", "description": "Absolute gap >= ATR", "rule": "abs(open-prev_close) >= ATR", "example": "N"},
    {"group": "momentum", "key": "breakout_dist_20d_high_pct", "label": "BreakoutDist20DHigh(%)", "type": "number", "description": "Distance from 20-day high", "rule": "(close-20d_high)/20d_high*100", "example": "0.42"},
    {"group": "momentum", "key": "breakout_dist_channel_up_pct", "label": "BreakoutDistChannelUp(%)", "type": "number", "description": "Distance from channel upper", "rule": "(close-Price_Channel_Up)/Price_Channel_Up*100", "example": "-0.36"},
    {"group": "momentum", "key": "ret20_pct", "label": "Return20(%)", "type": "number", "description": "20-bar return", "rule": "(close-close_20)/close_20*100", "example": "8.4"},
    {"group": "momentum", "key": "ret60_pct", "label": "Return60(%)", "type": "number", "description": "60-bar return", "rule": "(close-close_60)/close_60*100", "example": "16.2"},
    {"group": "momentum", "key": "ret120_pct", "label": "Return120(%)", "type": "number", "description": "120-bar return", "rule": "(close-close_120)/close_120*100", "example": "24.1"},
    {"group": "momentum", "key": "rs_rank_vs_index", "label": "RSRankVsIndex", "type": "number", "description": "Cross-sectional rank of RS ratio", "rule": "percentile rank of RS_Ratio", "example": "86.5"},
    {"group": "momentum", "key": "ret20_percentile", "label": "Return20Percentile", "type": "number", "description": "Cross-sectional percentile of 20-bar return", "rule": "percentile rank of ret20_pct", "example": "82.1"},
    {"group": "momentum", "key": "ret60_percentile", "label": "Return60Percentile", "type": "number", "description": "Cross-sectional percentile of 60-bar return", "rule": "percentile rank of ret60_pct", "example": "79.4"},
    {"group": "momentum", "key": "ret120_percentile", "label": "Return120Percentile", "type": "number", "description": "Cross-sectional percentile of 120-bar return", "rule": "percentile rank of ret120_pct", "example": "74.8"},
    {"group": "turn", "key": "first_close_above_ma20_after_5bars", "label": "FirstCloseAboveMA20After5Bars", "type": "bool", "description": "First MA20 reclaim after 5 bars below", "rule": "previous 5 closes <= MA20 and current close > MA20", "example": "Y"},
    {"group": "turn", "key": "first_higher_low_pivot2", "label": "FirstHigherLowPivot2", "type": "bool", "description": "Confirmed higher-low with pivot=2", "rule": "pivot low > previous pivot low, confirmed at current bar", "example": "N"},
    {"group": "turn", "key": "first_higher_high_pivot2", "label": "FirstHigherHighPivot2", "type": "bool", "description": "Confirmed higher-high with pivot=2", "rule": "pivot high > previous pivot high, confirmed at current bar", "example": "N"},
    {"group": "volatility", "key": "atr_contracting", "label": "ATRContracting", "type": "bool", "description": "Latest ATR below previous ATR", "rule": "ATR[-1] < ATR[-2]", "example": "Y"},
    {"group": "pattern", "key": "nr7_flag", "label": "NR7Flag", "type": "bool", "description": "Latest bar is NR7", "rule": "NR7", "example": "Y"},
    {"group": "pattern", "key": "inside_day_flag", "label": "InsideDayFlag", "type": "bool", "description": "Latest bar is inside day", "rule": "Inside_Day", "example": "N"},
    {"group": "pattern", "key": "three_weeks_tight", "label": "ThreeWeeksTight", "type": "bool", "description": "Three-weeks-tight style compression", "rule": "Three_Weeks_Tight", "example": "N"},
    {"group": "pattern", "key": "tight_close_near_high_3d", "label": "TightCloseNearHigh3D", "type": "bool", "description": "Last 3 closes clustered near daily highs", "rule": "(high-close)/(high-low) <= 0.25 for 3 bars", "example": "Y"},
    {"group": "pattern", "key": "pin_bar_ratio", "label": "PinBarRatio", "type": "number", "description": "Dominant wick versus body ratio", "rule": "max(upper_wick,lower_wick)/max(body,range*0.05)", "example": "2.8"},
    {"group": "pattern", "key": "near_52w_high_2pct", "label": "Near52WHigh2Pct", "type": "bool", "description": "Within 2% of 52-week high", "rule": "drawdown_from_52w_high_pct > -2", "example": "Y"},
    {"group": "pattern", "key": "up_close_streak", "label": "UpCloseStreak", "type": "number", "description": "Consecutive higher closes", "rule": "trailing Close > Close[-1]", "example": "3"},
    {"group": "pattern", "key": "down_close_streak", "label": "DownCloseStreak", "type": "number", "description": "Consecutive lower closes", "rule": "trailing Close < Close[-1]", "example": "2"},
    {"group": "pattern", "key": "weekly_trend_context", "label": "WeeklyTrendContext", "type": "text", "description": "Weekly trend regime from weekly close and moving averages", "rule": "weekly close vs weekly MA10/MA20", "example": "STRONG_UPTREND"},
    {"group": "volume", "key": "volume_dry_up_score_3", "label": "VolumeDryUpScore3", "type": "number", "description": "3-bar dry-up score versus prior 20 bars", "rule": "clip((1-recent3/prior20)*100,0,100)", "example": "18"},
    {"group": "volume", "key": "volume_dry_up_score_5", "label": "VolumeDryUpScore5", "type": "number", "description": "5-bar dry-up score versus prior 20 bars", "rule": "clip((1-recent5/prior20)*100,0,100)", "example": "24"},
    {"group": "volume", "key": "volume_dry_up_score_10", "label": "VolumeDryUpScore10", "type": "number", "description": "10-bar dry-up score versus prior 20 bars", "rule": "clip((1-recent10/prior20)*100,0,100)", "example": "31"},
    {"group": "turn", "key": "days_since_pocket_pivot", "label": "DaysSincePocketPivot", "type": "number", "description": "Bars since latest pocket pivot", "rule": "as_of - last(Pocket_Pivot)", "example": "4"},
    {"group": "turn", "key": "pocket_pivot_recent", "label": "PocketPivotRecent", "type": "bool", "description": "Pocket pivot within last 10 bars", "rule": "days_since_pocket_pivot <= 10", "example": "Y"},
    {"group": "setup", "key": "gap_setup_score", "label": "GapSetupScore", "type": "number", "description": "Gap setup score", "rule": "weighted literal score, max 11", "example": "8"},
    {"group": "setup", "key": "gap_setup_gate_count", "label": "GapSetupGateCount", "type": "number", "description": "Gap setup gate hits", "rule": "sum(5 gate groups)", "example": "4"},
    {"group": "setup", "key": "gap_setup_candidate", "label": "GapSetupCandidate", "type": "bool", "description": "Gap setup candidate gate", "rule": "gap_setup_gate_count >= 3", "example": "Y"},
    {"group": "setup", "key": "pocket_pivot_score", "label": "PocketPivotScore", "type": "number", "description": "Pocket pivot score", "rule": "weighted literal score, max 12", "example": "9"},
    {"group": "setup", "key": "pocket_pivot_gate_count", "label": "PocketPivotGateCount", "type": "number", "description": "Pocket pivot gate hits", "rule": "sum(5 gate groups)", "example": "4"},
    {"group": "setup", "key": "pocket_pivot_candidate", "label": "PocketPivotCandidate", "type": "bool", "description": "Pocket pivot candidate gate", "rule": "pocket_pivot_gate_count >= 3", "example": "Y"},
)

POST_CLOSE_SETUP_TOP_N = 30
GAP_SETUP_MAX_SCORE = 11
POCKET_PIVOT_MAX_SCORE = 12
POST_CLOSE_SUMMARY_SECTION_TOTAL = 10
POST_CLOSE_SECTION_TITLES = {
    "legacy_turn": "매수전환 (이전버전)",
    "legacy_pullback": "눌림 재진입 (이전버전)",
    "legacy_hull_bear": "HULL 매도전환 (이전버전)",
    "legacy_52w_high": "52주 신고가 (이전버전)",
    "pullback_filter": "눌림목 필터",
    "chase_filter": "추세추종 필터",
    "buy_turn_filter": "매수전환 필터",
    "gap_setup": "에너지 압축 → 돌파 임박",
    "pocket_pivot": "기관 매집 포착",
    "five_day_top": "5일 변동률 상위종목",
}
POST_CLOSE_INDEX_TITLES = {
    "legacy_turn": "매수전환(이전버전)",
    "legacy_pullback": "눌림 재진입(이전버전)",
    "legacy_hull_bear": "HULL 매도전환(이전버전)",
    "legacy_52w_high": "52주 신고가(이전버전)",
    "pullback_filter": "눌림목 필터",
    "chase_filter": "추세추종 필터",
    "buy_turn_filter": "매수전환 필터",
    "gap_setup": "에너지 압축 → 돌파 임박",
    "pocket_pivot": "기관 매집 포착",
    "five_day_top": "5일 변동률 상위종목",
}
POST_CLOSE_FINAL_TOP_N = 30
POST_CLOSE_FINAL_SECTION_NAME = "오늘 진입 후보 Top30 (A/B/C 통과만)"
POST_CLOSE_FINAL_INDEX_TITLE = "오늘 진입 후보 Top30"
POST_CLOSE_FINAL_ENTRY_FIELD_SPECS: tuple[dict[str, str], ...] = (
    {"group": "final", "key": "a_score", "label": "AScore", "type": "number", "description": "Trend quality score (A)", "rule": "5-point score", "example": "4"},
    {"group": "final", "key": "b_score", "label": "BScore", "type": "number", "description": "Entry timing score (B)", "rule": "5-point score", "example": "3"},
    {"group": "final", "key": "c_score", "label": "CScore", "type": "number", "description": "Money inflow score (C)", "rule": "4-point score", "example": "2"},
    {"group": "final", "key": "final_entry_score", "label": "FinalEntryScore", "type": "number", "description": "Composite score for final entry ranking", "rule": "normalized A/B/C + scan/es bonus", "example": "96.25"},
    {"group": "final", "key": "final_entry_rank", "label": "FinalEntryRank", "type": "number", "description": "Top-N rank among eligible rows", "rule": "1..N when selected", "example": "1"},
    {"group": "final", "key": "final_entry_selected", "label": "FinalEntrySelected", "type": "bool", "description": "Selected for final Top-N", "rule": "within final rank top N", "example": "Y"},
    {"group": "final", "key": "final_entry_reason", "label": "FinalEntryReason", "type": "text", "description": "A/B/C score summary and gate result", "rule": "A#/B#/C# + PASS/FAIL reason", "example": "A4/B3/C2 | PASS"},
)
GAP_SETUP_HIT_LABELS = {
    "DryUp": "거래량건조",
    "20D": "20일고점근접",
    "RS": "상대강도",
    "BB": "밴드압축",
    "ADX": "추세강도",
    "HMA": "HMA상승",
    "CMF": "자금유입",
    "Cloud": "구름상단",
    "NR7": "NR7",
    "Inside": "인사이드",
    "3WT": "3주타이트",
    "Tight3": "3일타이트",
    "52W<2%": "52주고점-2%",
    "WUp": "주간상승",
}
POCKET_PIVOT_HIT_LABELS = {
    "VolExp": "거래량팽창",
    "Vol1.5x": "20일대비1.5배",
    "UT<=3": "UT최근3일",
    "MB4": "멀티매수4+",
    "PB<8%": "눌림8%이내",
    "OBV": "OBV상승",
    "CMF": "자금유입",
    "Cloud": "구름상단",
    "NR7": "NR7",
    "Inside": "인사이드",
    "WUp": "주간상승",
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


def _coerce_float(value: Any) -> float | None:
    try:
        number = float(value)
    except Exception:
        return None
    if not math.isfinite(number):
        return None
    return number


def _safe_ratio_pct(value: Any, base: Any) -> float:
    value_num = _coerce_float(value)
    base_num = _coerce_float(base)
    if value_num is None or base_num is None or abs(base_num) <= 1e-10:
        return 0.0
    return _safe_float((value_num - base_num) / base_num * 100.0)


def _safe_slope_pct(current: Any, previous: Any) -> float:
    current_num = _coerce_float(current)
    previous_num = _coerce_float(previous)
    if current_num is None or previous_num is None or abs(previous_num) <= 1e-10:
        return 0.0
    return _safe_float((current_num - previous_num) / abs(previous_num) * 100.0)


def _clip(value: float, lower: float, upper: float) -> float:
    return min(upper, max(lower, value))


def _series_last_true_timestamp(frame: Any, column: str) -> Any:
    if frame is None or column not in getattr(frame, "columns", []):
        return None
    try:
        series = frame[column].fillna(False).astype(bool)
    except Exception:
        try:
            series = frame[column].astype(bool)
        except Exception:
            return None
    try:
        if not bool(series.any()):
            return None
        return series[series].index[-1]
    except Exception:
        return None


def _timestamp_to_iso(ts: Any) -> str:
    if ts is None:
        return "없음"
    if hasattr(ts, "date"):
        try:
            return ts.date().isoformat()
        except Exception:
            pass
    text = str(ts or "").strip()
    return text[:10] if text else "없음"


def _days_since_timestamp(as_of: Any, ts: Any) -> int:
    if as_of is None or ts is None:
        return 0
    try:
        return max(0, int((as_of - ts).days))
    except Exception:
        return 0


def _series_return_pct(series: Any, periods: int) -> float:
    if series is None or periods <= 0:
        return 0.0
    try:
        if len(series) <= periods:
            return 0.0
        current = series.iloc[-1]
        previous = series.iloc[-(periods + 1)]
    except Exception:
        return 0.0
    return _safe_ratio_pct(current, previous)


def _compute_pivot2_first_flags(frame: Any, *, pivot: int = 2) -> tuple[bool, bool]:
    if frame is None or pivot <= 0:
        return False, False
    if "High" not in getattr(frame, "columns", []) or "Low" not in getattr(frame, "columns", []):
        return False, False
    if len(frame) < (pivot * 2 + 3):
        return False, False

    try:
        highs = [float(v) if math.isfinite(float(v)) else float("nan") for v in frame["High"].tolist()]
        lows = [float(v) if math.isfinite(float(v)) else float("nan") for v in frame["Low"].tolist()]
    except Exception:
        return False, False

    n = len(frame)
    pivot_highs: list[tuple[int, float]] = []
    pivot_lows: list[tuple[int, float]] = []
    for i in range(pivot, n - pivot):
        high_window = highs[i - pivot : i + pivot + 1]
        low_window = lows[i - pivot : i + pivot + 1]
        if any(not math.isfinite(v) for v in high_window) or any(not math.isfinite(v) for v in low_window):
            continue
        center_high = highs[i]
        center_low = lows[i]
        if center_high >= max(high_window) and any(center_high > v for j, v in enumerate(high_window) if j != pivot):
            pivot_highs.append((i, center_high))
        if center_low <= min(low_window) and any(center_low < v for j, v in enumerate(low_window) if j != pivot):
            pivot_lows.append((i, center_low))

    first_higher_low = False
    for i in range(1, len(pivot_lows)):
        prev_idx, prev_low = pivot_lows[i - 1]
        cur_idx, cur_low = pivot_lows[i]
        if cur_low > prev_low and (cur_idx + pivot) == (n - 1):
            first_higher_low = True
            break

    first_higher_high = False
    for i in range(1, len(pivot_highs)):
        prev_idx, prev_high = pivot_highs[i - 1]
        cur_idx, cur_high = pivot_highs[i]
        if cur_high > prev_high and (cur_idx + pivot) == (n - 1):
            first_higher_high = True
            break

    return first_higher_low, first_higher_high


def _tail_mean(series: Any, periods: int) -> float:
    if series is None or periods <= 0:
        return 0.0
    try:
        return _safe_float(series.tail(periods).mean())
    except Exception:
        return 0.0


def _recent_window_dry_up_score(volume_series: Any, *, recent_window: int, baseline_window: int = 20) -> float:
    if volume_series is None or recent_window <= 0:
        return 0.0
    try:
        prior_series = volume_series.iloc[:-1]
    except Exception:
        return 0.0
    if prior_series is None or len(prior_series) < recent_window:
        return 0.0
    recent_avg = _tail_mean(prior_series, recent_window)
    baseline_avg = _tail_mean(prior_series, max(baseline_window, recent_window))
    if baseline_avg <= 1e-10:
        return 0.0
    return _safe_float(_clip((1.0 - (recent_avg / baseline_avg)) * 100.0, 0.0, 100.0))


def _trailing_bool_streak(values: Iterable[Any]) -> int:
    streak = 0
    try:
        iterable = list(values)
    except Exception:
        return 0
    for value in reversed(iterable):
        if bool(value):
            streak += 1
            continue
        break
    return streak


def _compute_weekly_trend_context(frame: Any) -> str:
    if frame is None or "Close" not in getattr(frame, "columns", []):
        return "NEUTRAL"
    try:
        weekly_close = frame["Close"].resample("W-FRI").last().dropna()
    except Exception:
        return "NEUTRAL"
    if len(weekly_close) < 5:
        return "NEUTRAL"
    weekly_ma10 = weekly_close.rolling(10, min_periods=3).mean()
    weekly_ma20 = weekly_close.rolling(20, min_periods=5).mean()
    latest_close = _safe_float(weekly_close.iloc[-1], 0.0)
    latest_ma10 = _safe_float(weekly_ma10.iloc[-1], 0.0)
    latest_ma20 = _safe_float(weekly_ma20.iloc[-1], 0.0)
    prev_ma10 = _safe_float(weekly_ma10.iloc[-2] if len(weekly_ma10) >= 2 else latest_ma10, latest_ma10)
    if latest_close > latest_ma10 > latest_ma20 and latest_ma10 >= prev_ma10:
        return "STRONG_UPTREND"
    if latest_close > latest_ma10 and latest_ma10 >= latest_ma20:
        return "UPTREND"
    if latest_close < latest_ma10 < latest_ma20 and latest_ma10 <= prev_ma10:
        return "DOWNTREND"
    return "NEUTRAL"


def _compute_post_close_row_metrics(frame: Any) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "dist_sma20_pct": 0.0,
        "dist_sma50_pct": 0.0,
        "dist_sma120_pct": 0.0,
        "dist_sma200_pct": 0.0,
        "dist_ema8_pct": 0.0,
        "dist_ema21_pct": 0.0,
        "dist_ema50_pct": 0.0,
        "hma20_slope_pct": 0.0,
        "hma60_slope_pct": 0.0,
        "hma200_slope_pct": 0.0,
        "adx": 0.0,
        "ichimoku_above_cloud": False,
        "ichimoku_below_cloud": False,
        "drawdown_from_52w_high_pct": 0.0,
        "drawdown_from_20d_high_pct": 0.0,
        "pullback_from_swing_high_pct": 0.0,
        "zscore20": 0.0,
        "bb_percent_b": 0.0,
        "atr_pct": 0.0,
        "pullback_atr_multiple": 0.0,
        "days_since_utbot_buy": 0,
        "days_since_hull_turn_bull": 0,
        "days_since_hull_turn_bear": 0,
        "system_turn_bull_last_date": "없음",
        "volume_dry_up_score": 0.0,
        "volume_expansion_score": 0.0,
        "obv_slope": 0.0,
        "cmf": 0.0,
        "volume_climax_flag": False,
        "dist_vwap_pct": 0.0,
        "dist_bb_mid_pct": 0.0,
        "dist_bb_upper_pct": 0.0,
        "gap_risk_2pct": False,
        "gap_risk_atr": False,
        "breakout_dist_20d_high_pct": 0.0,
        "breakout_dist_channel_up_pct": 0.0,
        "ret20_pct": 0.0,
        "ret60_pct": 0.0,
        "ret120_pct": 0.0,
        "rs_ratio": 0.0,
        "rs_rank_vs_index": "",
        "ret20_percentile": "",
        "ret60_percentile": "",
        "ret120_percentile": "",
        "first_close_above_ma20_after_5bars": False,
        "first_higher_low_pivot2": False,
        "first_higher_high_pivot2": False,
        "atr_contracting": False,
        "nr7_flag": False,
        "inside_day_flag": False,
        "three_weeks_tight": False,
        "tight_close_near_high_3d": False,
        "pin_bar_ratio": 0.0,
        "near_52w_high_2pct": False,
        "up_close_streak": 0,
        "down_close_streak": 0,
        "weekly_trend_context": "NEUTRAL",
        "volume_dry_up_score_3": 0.0,
        "volume_dry_up_score_5": 0.0,
        "volume_dry_up_score_10": 0.0,
        "days_since_pocket_pivot": 0,
        "pocket_pivot_recent": False,
        "gap_setup_score": 0,
        "gap_setup_gate_count": 0,
        "gap_setup_candidate": False,
        "pocket_pivot_score": 0,
        "pocket_pivot_gate_count": 0,
        "pocket_pivot_candidate": False,
    }
    if frame is None or len(frame) == 0:
        return metrics
    if "Close" not in getattr(frame, "columns", []):
        return metrics

    latest = frame.iloc[-1]
    previous = frame.iloc[-2] if len(frame) >= 2 else latest
    as_of = frame.index[-1] if len(frame.index) else None
    close_series = frame["Close"]
    high_series = frame["High"] if "High" in frame.columns else None
    low_series = frame["Low"] if "Low" in frame.columns else None
    volume_series = frame["Volume"] if "Volume" in frame.columns else None

    current_close = _safe_float(latest.get("Close", 0))
    previous_close = _safe_float(previous.get("Close", current_close))
    current_open = _safe_float(latest.get("Open", current_close))
    current_high = _safe_float(latest.get("High", current_close))
    current_low = _safe_float(latest.get("Low", current_close))
    atr = _safe_float(latest.get("ATR", 0))
    previous_atr = _safe_float(previous.get("ATR", atr))
    ma20 = _safe_float(latest.get("MA20", 0))

    metrics["dist_sma20_pct"] = _safe_ratio_pct(current_close, latest.get("MA20"))
    metrics["dist_sma50_pct"] = _safe_ratio_pct(current_close, latest.get("MA50"))
    metrics["dist_sma120_pct"] = _safe_ratio_pct(current_close, latest.get("MA120"))
    metrics["dist_sma200_pct"] = _safe_ratio_pct(current_close, latest.get("MA200"))
    metrics["dist_ema8_pct"] = _safe_ratio_pct(current_close, latest.get("EMA8"))
    metrics["dist_ema21_pct"] = _safe_ratio_pct(current_close, latest.get("EMA21"))
    metrics["dist_ema50_pct"] = _safe_ratio_pct(current_close, latest.get("EMA50"))
    metrics["hma20_slope_pct"] = _safe_slope_pct(latest.get("HMA"), previous.get("HMA"))
    metrics["hma60_slope_pct"] = _safe_slope_pct(latest.get("HMA60"), previous.get("HMA60"))
    metrics["hma200_slope_pct"] = _safe_slope_pct(latest.get("HMA200"), previous.get("HMA200"))
    metrics["adx"] = _safe_float(latest.get("ADX", 0))

    senkou_a = _coerce_float(latest.get("Ichimoku_SenkouA"))
    senkou_b = _coerce_float(latest.get("Ichimoku_SenkouB"))
    if senkou_a is not None and senkou_b is not None:
        cloud_top = max(senkou_a, senkou_b)
        cloud_bottom = min(senkou_a, senkou_b)
        metrics["ichimoku_above_cloud"] = bool(current_close > cloud_top)
        metrics["ichimoku_below_cloud"] = bool(current_close < cloud_bottom)

    high_52w = _safe_float(high_series.tail(252).max()) if high_series is not None else 0.0
    high_20d = _safe_float(high_series.tail(20).max()) if high_series is not None else 0.0
    swing_high = _safe_float(latest.get("Fib_Swing_High", 0))
    metrics["drawdown_from_52w_high_pct"] = _safe_ratio_pct(current_close, high_52w)
    metrics["drawdown_from_20d_high_pct"] = _safe_ratio_pct(current_close, high_20d)
    metrics["pullback_from_swing_high_pct"] = _safe_ratio_pct(current_close, swing_high)
    metrics["near_52w_high_2pct"] = bool(metrics["drawdown_from_52w_high_pct"] > -2.0)

    try:
        mean20 = _safe_float(close_series.tail(20).mean())
        std20 = _safe_float(close_series.tail(20).std(ddof=0))
    except Exception:
        mean20 = 0.0
        std20 = 0.0
    metrics["zscore20"] = _safe_float((current_close - mean20) / std20) if std20 > 1e-10 else 0.0
    metrics["bb_percent_b"] = _safe_float(latest.get("Percent_B", 0))
    metrics["atr_pct"] = _safe_float((atr / current_close) * 100) if current_close > 1e-10 else 0.0
    metrics["pullback_atr_multiple"] = _safe_float((high_20d - current_close) / atr) if atr > 1e-10 else 0.0
    metrics["atr_contracting"] = bool(atr > 1e-10 and previous_atr > 1e-10 and atr < previous_atr)

    utbot_buy_ts = _series_last_true_timestamp(frame, "UTBot_Buy")
    hull_bull_ts = _series_last_true_timestamp(frame, "Hull_Turn_Bull")
    hull_bear_ts = _series_last_true_timestamp(frame, "Hull_Turn_Bear")
    system_bull_ts = _series_last_true_timestamp(frame, "System_Turn_Bull")
    pocket_pivot_ts = _series_last_true_timestamp(frame, "Pocket_Pivot")
    metrics["days_since_utbot_buy"] = _days_since_timestamp(as_of, utbot_buy_ts)
    metrics["days_since_hull_turn_bull"] = _days_since_timestamp(as_of, hull_bull_ts)
    metrics["days_since_hull_turn_bear"] = _days_since_timestamp(as_of, hull_bear_ts)
    metrics["days_since_pocket_pivot"] = _days_since_timestamp(as_of, pocket_pivot_ts)
    metrics["pocket_pivot_recent"] = bool(pocket_pivot_ts is not None and metrics["days_since_pocket_pivot"] <= 10)
    metrics["system_turn_bull_last_date"] = _timestamp_to_iso(system_bull_ts)

    volume_ratio_20 = _safe_float(latest.get("Volume_Ratio_20", 0))
    metrics["volume_dry_up_score"] = _safe_float(_clip((1.0 - volume_ratio_20) * 100.0, 0.0, 100.0))
    metrics["volume_expansion_score"] = _safe_float(_clip((volume_ratio_20 - 1.0) * 100.0, 0.0, 100.0))
    metrics["volume_dry_up_score_3"] = _recent_window_dry_up_score(volume_series, recent_window=3)
    metrics["volume_dry_up_score_5"] = _recent_window_dry_up_score(volume_series, recent_window=5)
    metrics["volume_dry_up_score_10"] = _recent_window_dry_up_score(volume_series, recent_window=10)
    metrics["obv_slope"] = _safe_float(latest.get("OBV_Slope", 0))
    metrics["cmf"] = _safe_float(latest.get("CMF", 0))
    metrics["volume_climax_flag"] = bool(latest.get("Volume_Climax_Buy", False) or latest.get("Volume_Climax_Sell", False))
    metrics["nr7_flag"] = bool(latest.get("NR7", False))
    metrics["inside_day_flag"] = bool(latest.get("Inside_Day", False))
    metrics["three_weeks_tight"] = bool(latest.get("Three_Weeks_Tight", False))

    metrics["dist_vwap_pct"] = _safe_ratio_pct(current_close, latest.get("VWAP"))
    metrics["dist_bb_mid_pct"] = _safe_ratio_pct(current_close, latest.get("BB_Mid"))
    metrics["dist_bb_upper_pct"] = _safe_ratio_pct(current_close, latest.get("BB_Up"))

    gap_pct = _safe_float(abs((current_open - previous_close) / previous_close) * 100) if previous_close > 1e-10 else 0.0
    gap_abs_value = _safe_float(abs(current_open - previous_close))
    metrics["gap_risk_2pct"] = bool(gap_pct >= 2.0)
    metrics["gap_risk_atr"] = bool(atr > 1e-10 and gap_abs_value >= atr)

    metrics["breakout_dist_20d_high_pct"] = _safe_ratio_pct(current_close, high_20d)
    metrics["breakout_dist_channel_up_pct"] = _safe_ratio_pct(current_close, latest.get("Price_Channel_Up"))

    metrics["ret20_pct"] = _series_return_pct(close_series, 20)
    metrics["ret60_pct"] = _series_return_pct(close_series, 60)
    metrics["ret120_pct"] = _series_return_pct(close_series, 120)
    metrics["rs_ratio"] = _safe_float(latest.get("RS_Ratio", 0))
    try:
        close_up = close_series.diff().gt(0).fillna(False)
        close_down = close_series.diff().lt(0).fillna(False)
    except Exception:
        close_up = []
        close_down = []
    metrics["up_close_streak"] = _trailing_bool_streak(close_up)
    metrics["down_close_streak"] = _trailing_bool_streak(close_down)
    metrics["weekly_trend_context"] = _compute_weekly_trend_context(frame)

    candle_range = max(current_high - current_low, 0.0)
    candle_body = abs(current_close - current_open)
    upper_wick = max(current_high - max(current_open, current_close), 0.0)
    lower_wick = max(min(current_open, current_close) - current_low, 0.0)
    body_floor = max(candle_body, candle_range * 0.05, 1e-10)
    metrics["pin_bar_ratio"] = _safe_float(max(upper_wick, lower_wick) / body_floor)
    if high_series is not None and low_series is not None and len(frame) >= 3:
        recent_ranges = (high_series.tail(3) - low_series.tail(3)).abs()
        near_high_series = ((high_series.tail(3) - close_series.tail(3)) <= (recent_ranges * 0.25)).fillna(False)
        metrics["tight_close_near_high_3d"] = bool(near_high_series.all())

    if len(frame) >= 6 and "MA20" in frame.columns:
        prev5_close = close_series.iloc[-6:-1]
        prev5_ma20 = frame["MA20"].iloc[-6:-1]
        prev_all_below = False
        try:
            prev_all_below = bool((prev5_close <= prev5_ma20).fillna(False).all())
        except Exception:
            prev_all_below = False
        metrics["first_close_above_ma20_after_5bars"] = bool(prev_all_below and current_close > ma20 and previous_close <= _safe_float(previous.get("MA20", ma20)))

    first_hl, first_hh = _compute_pivot2_first_flags(frame, pivot=2)
    metrics["first_higher_low_pivot2"] = bool(first_hl)
    metrics["first_higher_high_pivot2"] = bool(first_hh)
    return metrics


CROSS_SECTION_OUTPUT_KEYS: tuple[str, ...] = (
    "rs_rank_vs_index",
    "ret20_percentile",
    "ret60_percentile",
    "ret120_percentile",
)


def _coerce_optional_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return _coerce_float(value)


def _percentile_map_for_key(rows: list[dict[str, Any]], source_key: str) -> dict[int, float]:
    values: list[tuple[int, float]] = []
    for idx, row in enumerate(rows):
        number = _coerce_optional_float(row.get(source_key))
        if number is None:
            continue
        values.append((idx, number))
    if not values:
        return {}
    sorted_values = sorted(value for _, value in values)
    count = len(sorted_values)
    ranked: dict[int, float] = {}
    for idx, value in values:
        if count == 1:
            percentile = 100.0
        else:
            left = bisect.bisect_left(sorted_values, value)
            right = bisect.bisect_right(sorted_values, value)
            avg_rank = (left + right - 1) / 2.0
            percentile = (avg_rank / (count - 1)) * 100.0
        ranked[idx] = _safe_float(round(percentile, 2))
    return ranked


def _with_post_close_cross_section_metrics(
    rows: Iterable[Mapping[str, Any]],
    *,
    enabled: bool,
) -> list[dict[str, Any]]:
    row_list = [dict(row or {}) for row in (rows or [])]
    if not enabled:
        for row in row_list:
            for key in CROSS_SECTION_OUTPUT_KEYS:
                row[key] = ""
        return row_list

    rs_rank_map = _percentile_map_for_key(row_list, "rs_ratio")
    ret20_map = _percentile_map_for_key(row_list, "ret20_pct")
    ret60_map = _percentile_map_for_key(row_list, "ret60_pct")
    ret120_map = _percentile_map_for_key(row_list, "ret120_pct")

    for idx, row in enumerate(row_list):
        row["rs_rank_vs_index"] = rs_rank_map.get(idx, 0.0)
        row["ret20_percentile"] = ret20_map.get(idx, 0.0)
        row["ret60_percentile"] = ret60_map.get(idx, 0.0)
        row["ret120_percentile"] = ret120_map.get(idx, 0.0)
    return row_list


def _with_post_close_setup_scores(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    row_list = [dict(row or {}) for row in (rows or [])]
    for row in row_list:
        gap_gate_hits = [
            _safe_float(row.get("volume_ratio_20", 0.0)) < 0.8,
            _safe_float(row.get("drawdown_from_20d_high_pct", 0.0)) > -3.0,
            0.55 <= _safe_float(row.get("bb_percent_b", 0.0)) <= 0.90 and _coerce_bool(row.get("atr_contracting", False)),
            _safe_float(row.get("rs_rank_vs_index", 0.0)) > 65.0 and _safe_float(row.get("ret20_percentile", 0.0)) > 75.0,
            _safe_float(row.get("hma20_slope_pct", 0.0)) > 0.5 and _safe_float(row.get("adx", 0.0)) > 25.0,
        ]
        gap_score = 0
        gap_hits: list[str] = []
        if _safe_float(row.get("volume_dry_up_score", 0.0)) > 50.0:
            gap_score += 2
            gap_hits.append("DryUp")
        if _safe_float(row.get("drawdown_from_20d_high_pct", 0.0)) > -3.0:
            gap_score += 2
            gap_hits.append("20D")
        if _safe_float(row.get("rs_rank_vs_index", 0.0)) > 65.0:
            gap_score += 2
            gap_hits.append("RS")
        if 0.55 <= _safe_float(row.get("bb_percent_b", 0.0)) <= 0.90:
            gap_score += 1
            gap_hits.append("BB")
        if _safe_float(row.get("adx", 0.0)) > 25.0:
            gap_score += 1
            gap_hits.append("ADX")
        if _safe_float(row.get("hma20_slope_pct", 0.0)) > 0.5:
            gap_score += 1
            gap_hits.append("HMA")
        if _safe_float(row.get("cmf", 0.0)) > 0.05:
            gap_score += 1
            gap_hits.append("CMF")
        if _coerce_bool(row.get("ichimoku_above_cloud", False)):
            gap_score += 1
            gap_hits.append("Cloud")
        gap_quality_hits: list[str] = []
        if _coerce_bool(row.get("nr7_flag", False)):
            gap_quality_hits.append("NR7")
        if _coerce_bool(row.get("inside_day_flag", False)):
            gap_quality_hits.append("Inside")
        if _coerce_bool(row.get("three_weeks_tight", False)):
            gap_quality_hits.append("3WT")
        if _coerce_bool(row.get("tight_close_near_high_3d", False)):
            gap_quality_hits.append("Tight3")
        if _coerce_bool(row.get("near_52w_high_2pct", False)):
            gap_quality_hits.append("52W<2%")
        if str(row.get("weekly_trend_context", "")).upper() in {"STRONG_UPTREND", "UPTREND"}:
            gap_quality_hits.append("WUp")
        row["gap_setup_score"] = int(gap_score)
        row["gap_setup_gate_count"] = int(sum(1 for item in gap_gate_hits if item))
        row["gap_setup_candidate"] = bool(row["gap_setup_gate_count"] >= 3)
        row["gap_setup_hits"] = gap_hits
        row["gap_setup_quality_hits"] = gap_quality_hits

        pocket_gate_hits = [
            _safe_float(row.get("volume_expansion_score", 0.0)) > 50.0 and _safe_float(row.get("volume_ratio_20", 0.0)) > 1.5,
            _safe_float(row.get("days_since_utbot_buy", 999.0)) <= 3.0 and _coerce_bool(row.get("utbot_buy_recent", False)),
            _safe_float(row.get("pullback_from_swing_high_pct", -999.0)) > -8.0 and _coerce_bool(row.get("pullback_ready", False)),
            _safe_float(row.get("cmf", 0.0)) > 0.05 and _safe_float(row.get("obv_slope", 0.0)) > 0.3,
            _safe_float(row.get("multi_buy", 0.0)) >= 4.0 and _coerce_bool(row.get("low_conflict_bullish", False)),
        ]
        pocket_score = 0
        pocket_hits: list[str] = []
        if _safe_float(row.get("volume_expansion_score", 0.0)) > 50.0:
            pocket_score += 2
            pocket_hits.append("VolExp")
        if _safe_float(row.get("volume_ratio_20", 0.0)) > 1.5:
            pocket_score += 2
            pocket_hits.append("Vol1.5x")
        if _safe_float(row.get("days_since_utbot_buy", 999.0)) <= 3.0:
            pocket_score += 2
            pocket_hits.append("UT<=3")
        if _safe_float(row.get("multi_buy", 0.0)) >= 4.0:
            pocket_score += 2
            pocket_hits.append("MB4")
        if _safe_float(row.get("pullback_from_swing_high_pct", -999.0)) > -8.0:
            pocket_score += 1
            pocket_hits.append("PB<8%")
        if _safe_float(row.get("obv_slope", 0.0)) > 0.3:
            pocket_score += 1
            pocket_hits.append("OBV")
        if _safe_float(row.get("cmf", 0.0)) > 0.05:
            pocket_score += 1
            pocket_hits.append("CMF")
        if _coerce_bool(row.get("ichimoku_above_cloud", False)):
            pocket_score += 1
            pocket_hits.append("Cloud")
        pocket_quality_hits: list[str] = []
        if _coerce_bool(row.get("nr7_flag", False)):
            pocket_quality_hits.append("NR7")
        if _coerce_bool(row.get("inside_day_flag", False)):
            pocket_quality_hits.append("Inside")
        if _safe_float(row.get("up_close_streak", 0.0)) >= 2.0:
            pocket_quality_hits.append(f"Up{int(_safe_float(row.get('up_close_streak', 0.0)))}")
        if str(row.get("weekly_trend_context", "")).upper() in {"STRONG_UPTREND", "UPTREND"}:
            pocket_quality_hits.append("WUp")
        if _coerce_bool(row.get("pocket_pivot_recent", False)):
            pocket_quality_hits.append(f"PP{int(_safe_float(row.get('days_since_pocket_pivot', 0.0)))}")
        row["pocket_pivot_score"] = int(pocket_score)
        row["pocket_pivot_gate_count"] = int(sum(1 for item in pocket_gate_hits if item))
        row["pocket_pivot_candidate"] = bool(row["pocket_pivot_gate_count"] >= 3)
        row["pocket_pivot_hits"] = pocket_hits
        row["pocket_pivot_quality_hits"] = pocket_quality_hits
    return row_list


def _build_sector_universe() -> list[str]:
    return _ordered_unique(
        ticker
        for tickers in SECTOR_GROUPS.values()
        for ticker in tickers
    )


def _normalize_universe_profile(value: Any) -> str:
    profile = str(value or "default").strip().lower()
    if profile not in UNIVERSE_PROFILE_ITEMS:
        return "default"
    return profile


def _scan_label_for_profile(profile: str) -> str:
    normalized = _normalize_universe_profile(profile)
    if normalized == "russell2000":
        return "Extended Scan:RUSSELL2000"
    return "자동 스캔"


def build_scan_universe(
    etf_items: Iterable[Mapping[str, str]] | None = None,
    *,
    universe_profile: str = "default",
) -> dict[str, Any]:
    profile = _normalize_universe_profile(universe_profile)
    selected_items = list(etf_items or UNIVERSE_PROFILE_ITEMS.get(profile, ETF_UNIVERSE_ITEMS))
    sector_tickers = _build_sector_universe()
    resolver_payload = resolve_etf_universe(selected_items)
    etf_tickers = _ordered_unique(resolver_payload.get("tickers") or [])
    combined = _ordered_unique([*sector_tickers, *etf_tickers])
    return {
        "tickers": combined,
        "universe_profile": profile,
        "sector_count": len(sector_tickers),
        "etf_count": len(etf_tickers),
        "etf_items": list(resolver_payload.get("items") or []),
        "etf_note": str(resolver_payload.get("note") or ""),
        "etf_errors": [str(err) for err in (resolver_payload.get("errors") or [])],
    }


def _compute_signal_frame(ticker: str, *, bias_mode: str, history_period: str = "2y") -> Any | None:
    history = yf.Ticker(ticker).history(period=history_period, auto_adjust=True)
    if history is None or history.empty:
        return None
    indicator_frame = compute_indicators(history)
    return detect_all_signals(indicator_frame, bias_mode=resolve_bias_mode(bias_mode))


def _build_scanner_row(ticker: str, *, bias_mode: str, recent_window: int = 5, history_period: str = "2y") -> dict[str, Any]:
    ticker = str(ticker or "").strip().upper()
    if not ticker:
        return {"ok": False, "ticker": "", "skip_reason": "invalid_ticker", "detail": "empty ticker"}

    try:
        frame = _compute_signal_frame(ticker, bias_mode=bias_mode, history_period=history_period)
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
        close_5d_ago = _safe_float(dc_.iloc[-6].get("Close", 0)) if len(dc_) >= 6 else 0.0

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
        chg_5d_pct = _safe_float((current_close - close_5d_ago) / close_5d_ago * 100) if close_5d_ago else 0.0
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

        latest_bar = dc_.index[-1] if len(dc_.index) else None
        if hasattr(latest_bar, "date"):
            latest_bar_date = latest_bar.date().isoformat()
        else:
            latest_bar_date = str(latest_bar)[:10] if latest_bar is not None else ""
        advanced_metrics = _compute_post_close_row_metrics(frame)

        row = {
            "ticker": ticker,
            "price": _safe_float(current_close),
            "chg_value": chg_value,
            "chg": chg_pct,
            "chg_5d": chg_5d_pct,
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
            "latest_bar_date": str(latest_bar_date or "없음"),
            "new_52w_high": bool(latest.get("New_52W_High", False)),
            "new_52w_closing_high": bool(latest.get("New_52W_Closing_High", False)),
            "detected_combo_count": int(detected_payload.get("detected_combo_count", 0) or 0),
            "detected_combo_summary": str(detected_payload.get("detected_combo_summary", "없음")),
            "detected_transition_count": int(detected_payload.get("detected_transition_count", 0) or 0),
            "detected_transition_summary": str(detected_payload.get("detected_transition_summary", "없음")),
            "detected_core_count": int(detected_payload.get("detected_core_count", 0) or 0),
            "detected_core_summary": str(detected_payload.get("detected_core_summary", "없음")),
            "detected_signal_total_count": int(detected_payload.get("detected_signal_total_count", 0) or 0),
            "detected_buy_signal_latest_date": str(detected_payload.get("detected_buy_signal_latest_date", "없음")),
            "detected_signal_latest_date": str(detected_payload.get("detected_signal_latest_date", "없음")),
            "detected_signals": list(detected_payload.get("all_items", [])),
            "watch_buy_plus": watch_buy_plus,
            "buy_combo_present": buy_combo_present,
            **advanced_metrics,
        }
        return {"ok": True, "ticker": ticker, "row": row, "skip_reason": "", "detail": ""}
    except Exception as exc:
        return {"ok": False, "ticker": ticker, "skip_reason": "row_build_error", "detail": str(exc)[:220]}


def _scan_ticker_worker(ticker: str, *, bias_mode: str, history_period: str = "2y") -> dict[str, Any]:
    started = time.perf_counter()
    payload = dict(_build_scanner_row(ticker, bias_mode=bias_mode, history_period=history_period))
    payload["elapsed_sec"] = _safe_float(time.perf_counter() - started)
    return payload


def scan_universe(tickers: list[str], *, max_workers: int, bias_mode: str, history_period: str = "2y") -> ScanRunResult:
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
            executor.submit(_scan_ticker_worker, ticker, bias_mode=bias_mode, history_period=history_period): ticker
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


def write_scan_csv(
    rows: list[dict[str, Any]],
    *,
    out_dir: Path,
    run_label: str,
    extra_field_specs: Iterable[Mapping[str, str]] | None = None,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / f"scanner_full_{run_label}.csv"
    if extra_field_specs:
        field_specs = [*scanner_csv_field_specs(), *[dict(spec) for spec in extra_field_specs]]
        payload = scanner_rows_to_csv_bytes(rows, field_specs=field_specs)
    else:
        payload = scanner_rows_to_csv_bytes(rows)
    output_path.write_bytes(payload)
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


_SHARD_MARKER_PATTERN = re.compile(r"shard(?P<index>\d+)of(?P<count>\d+)", re.IGNORECASE)
_ARTIFACT_RUN_STAMP_PATTERN = re.compile(
    r"^(?:scan_rows|run_meta)_(?P<run_stamp>.+?)(?:_merged|_shard\d+of\d+)\.json$",
    re.IGNORECASE,
)


def _parse_shard_marker(value: Any) -> tuple[int, int] | None:
    match = _SHARD_MARKER_PATTERN.search(str(value or ""))
    if not match:
        return None
    try:
        index = int(match.group("index"))
        count = int(match.group("count"))
    except Exception:
        return None
    if index < 0 or count <= 0:
        return None
    return index, count


def _extract_run_stamp(value: Any) -> str | None:
    name = Path(str(value or "")).name
    match = _ARTIFACT_RUN_STAMP_PATTERN.match(name)
    if not match:
        return None
    run_stamp = str(match.group("run_stamp") or "").strip()
    return run_stamp or None


def _is_merged_artifact(value: Any) -> bool:
    return "_merged" in str(value or "").strip().lower()


def _prepend_summary_warning(summary_text: str, warning_line: str) -> str:
    warning = str(warning_line or "").strip()
    body = str(summary_text or "").strip()
    if not warning:
        return body
    if not body:
        return warning
    return f"{warning}\n{body}"


def _build_premarket_fallback_rows(tickers: Iterable[str]) -> list[dict[str, Any]]:
    fallback_rows: list[dict[str, Any]] = []
    for ticker in _ordered_unique(tickers):
        fallback_rows.append(
            {
                "ticker": ticker,
                "scan_source": "pre_market_fallback",
                "scan_score": 0.0,
                "strength": 0.0,
                "es": 0.0,
                "cf": 0.0,
                "jg_key": "N/A",
                "pullback_reentry": False,
                "volume_ratio_20": 0.0,
                "utbot_buy_last_date": "N/A",
                "hull_turn_bull_last_date": "N/A",
                "hull_turn_bear_last_date": "N/A",
                "new_52w_high": False,
                "latest_bar_date": "N/A",
                "price": 0.0,
            }
        )
    return fallback_rows


def merge_shard_scan_rows(merge_dir: Path, *, required_run_stamp: str | None = None) -> dict[str, Any]:
    all_row_files = sorted(Path(merge_dir).glob("**/scan_rows_*.json"))
    candidate_row_files = [
        path
        for path in all_row_files
        if not _is_merged_artifact(path.name) and _parse_shard_marker(path.name) is not None and _extract_run_stamp(path.name)
    ]
    if not candidate_row_files:
        raise RuntimeError(f"No shard row files found in {merge_dir}")
    requested_run_stamp = str(required_run_stamp or "").strip()
    if requested_run_stamp:
        selected_run_stamp = requested_run_stamp
        files = [path for path in candidate_row_files if _extract_run_stamp(path.name) == selected_run_stamp]
        if not files:
            raise RuntimeError(f"No shard row files found in {merge_dir} for run_stamp={selected_run_stamp}")
    else:
        selected_run_stamp = max(str(_extract_run_stamp(path.name) or "") for path in candidate_row_files)
        files = [path for path in candidate_row_files if _extract_run_stamp(path.name) == selected_run_stamp]

    all_rows: list[dict[str, Any]] = []
    expected_shard_count = 0
    found_shard_indices: set[int] = set()
    for file_path in files:
        shard_marker = _parse_shard_marker(file_path.name)
        if shard_marker:
            shard_index, shard_count = shard_marker
            expected_shard_count = max(expected_shard_count, int(shard_count))
            if shard_index < shard_count:
                found_shard_indices.add(shard_index)
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

    meta_files = [
        path
        for path in sorted(Path(merge_dir).glob("**/run_meta_*.json"))
        if not _is_merged_artifact(path.name)
        and _parse_shard_marker(path.name) is not None
        and _extract_run_stamp(path.name) == selected_run_stamp
    ]
    shard_universe_sum = 0
    full_universe_max = 0
    skip_count_sum = 0
    result_count_sum = 0
    shard_meta_count = 0
    shard_errors: list[str] = []
    shard_profiles: list[str] = []
    priority_modes: list[str] = []
    for meta_file in meta_files:
        shard_marker = _parse_shard_marker(meta_file.name)
        if shard_marker:
            shard_index, shard_count = shard_marker
            expected_shard_count = max(expected_shard_count, int(shard_count))
            if shard_index < shard_count:
                found_shard_indices.add(shard_index)
        payload = _load_json_file(meta_file)
        if not isinstance(payload, dict):
            continue
        shard_meta_count += 1
        shard_count = int(_safe_float(payload.get("shard_count", 0)))
        shard_index = int(_safe_float(payload.get("shard_index", -1)))
        if shard_count > 0:
            expected_shard_count = max(expected_shard_count, shard_count)
            if 0 <= shard_index < shard_count:
                found_shard_indices.add(shard_index)
        shard_universe_sum += int(_safe_float(payload.get("shard_ticker_count", 0)))
        full_universe_max = max(full_universe_max, int(_safe_float(payload.get("full_universe_count", 0))))
        performance = payload.get("performance") or {}
        skip_count_sum += int(_safe_float(performance.get("skip_count", 0)))
        result_count_sum += int(_safe_float(payload.get("result_count", 0)))
        for err in payload.get("etf_errors", []) or []:
            shard_errors.append(str(err))
        profile = _normalize_universe_profile(payload.get("universe_profile"))
        shard_profiles.append(profile)
        priority_mode = str(payload.get("priority_mode") or "").strip().lower()
        if priority_mode and priority_mode not in priority_modes:
            priority_modes.append(priority_mode)

    universe_count = full_universe_max or shard_universe_sum
    found_indices_sorted = sorted(found_shard_indices)
    missing_indices = (
        [idx for idx in range(expected_shard_count) if idx not in found_shard_indices]
        if expected_shard_count > 0
        else []
    )
    merge_ready = expected_shard_count > 0 and not missing_indices
    merge_block_reason = "" if merge_ready else "incomplete_shards"
    return {
        "rows": merged_rows,
        "run_stamp": selected_run_stamp,
        "row_files": [str(path) for path in files],
        "meta_files": [str(path) for path in meta_files],
        "source_row_count": len(all_rows),
        "merged_row_count": len(merged_rows),
        "source_result_count_sum": result_count_sum,
        "skip_count_sum": skip_count_sum,
        "universe_count": universe_count,
        "shard_meta_count": shard_meta_count,
        "etf_errors": _ordered_unique(shard_errors),
        "universe_profiles": _ordered_unique(shard_profiles),
        "expected_shard_count": int(expected_shard_count),
        "found_shard_count": len(found_indices_sorted),
        "found_shard_indices": found_indices_sorted,
        "missing_shard_indices": missing_indices,
        "merge_ready": merge_ready,
        "merge_block_reason": merge_block_reason,
        "priority_modes": priority_modes,
    }


def _parse_iso_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text or text in {"없음", "?놁쓬", "-", "N/A"}:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except Exception:
        return None


def _with_latest_session_buy_turn_flags(
    rows: Iterable[Mapping[str, Any]],
    *,
    target_date: date,
) -> list[dict[str, Any]]:
    flagged_rows: list[dict[str, Any]] = []
    for row in rows or []:
        row_dict = dict(row or {})
        row_dict["latest_session_utbot_buy_turn"] = _parse_iso_date(row_dict.get("utbot_buy_last_date")) == target_date
        row_dict["latest_session_hull_buy_turn"] = _parse_iso_date(row_dict.get("hull_turn_bull_last_date")) == target_date
        flagged_rows.append(row_dict)
    return flagged_rows


def _last_us_market_session_date(run_at_kst: datetime) -> date:
    us_now = run_at_kst.astimezone(US_EASTERN)
    session_date = us_now.date()
    if us_now.weekday() >= 5 or us_now.time() < dt_time(16, 0):
        session_date -= timedelta(days=1)
    while session_date.weekday() >= 5:
        session_date -= timedelta(days=1)
    return session_date


def _current_us_session_date(run_at_kst: datetime) -> date:
    """현재 진행 중이거나 가장 가까운 미국장 세션 날짜 반환 (early_session용)."""
    us_now = run_at_kst.astimezone(US_EASTERN)
    session_date = us_now.date()
    while session_date.weekday() >= 5:
        session_date -= timedelta(days=1)
    return session_date


def _resolve_target_session_date(run_at_kst: datetime, scan_mode: str) -> date:
    """scan_mode에 따라 적절한 타겟 세션 날짜 반환."""
    if scan_mode == "early_session":
        return _current_us_session_date(run_at_kst)
    return _last_us_market_session_date(run_at_kst)


def _scan_label_for_mode(scan_mode: str, universe_profile: str) -> str:
    """scan_mode와 universe_profile을 조합하여 라벨 생성."""
    base = SCAN_MODE_LABELS.get(scan_mode, "자동 스캔")
    if _normalize_universe_profile(universe_profile) == "russell2000":
        return f"{base}:RUSSELL2000"
    return base


def _history_period_for_mode(scan_mode: str) -> str:
    """scan_mode에 따라 yfinance history period 결정."""
    if scan_mode == "pre_market":
        return "5d"
    if scan_mode == "early_session":
        return "1y"
    return "2y"


def _time_adjusted_volume_threshold(
    run_at_kst: datetime,
    *,
    base_threshold: float = 1.0,
) -> float:
    """장개시 후 경과 시간에 비례한 거래량 임계값 반환.

    보정 모델 (U-shape 반영):
    - 처음 30분: 하루 거래대금의 약 25%
    - 30~60분: 추가 약 15%
    - 60분 이후: 나머지 약 60% 분포
    """
    us_now = run_at_kst.astimezone(US_EASTERN)
    market_open = us_now.replace(
        hour=US_MARKET_OPEN_ET.hour, minute=US_MARKET_OPEN_ET.minute,
        second=0, microsecond=0,
    )
    market_close = us_now.replace(
        hour=US_MARKET_CLOSE_ET.hour, minute=US_MARKET_CLOSE_ET.minute,
        second=0, microsecond=0,
    )

    if us_now <= market_open:
        return max(0.05, base_threshold * 0.05)
    if us_now >= market_close:
        return base_threshold

    elapsed = (us_now - market_open).total_seconds() / 60.0

    if elapsed <= 30:
        ratio = 0.25 * (elapsed / 30.0)
    elif elapsed <= 60:
        ratio = 0.25 + 0.15 * ((elapsed - 30) / 30.0)
    else:
        ratio = 0.40 + 0.60 * ((elapsed - 60) / (US_REGULAR_SESSION_MINUTES - 60))

    return max(0.05, base_threshold * min(1.0, ratio))



def _transition_signals_on_date(row: Mapping[str, Any], target_date: date) -> list[str]:
    signals: list[str] = []
    utbot_buy_date = _parse_iso_date(row.get("utbot_buy_last_date"))
    hull_buy_date = _parse_iso_date(row.get("hull_turn_bull_last_date"))
    if utbot_buy_date == target_date:
        signals.append("UTBot 매수")
    if hull_buy_date == target_date:
        signals.append("HULL 매수")
    return signals


def select_us_session_turn_rows(rows: Iterable[Mapping[str, Any]], *, run_at_kst: datetime, scan_mode: str = "post_close") -> list[dict[str, Any]]:
    target_date = _resolve_target_session_date(run_at_kst, scan_mode)
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


def select_pullback_reentry_rows_for_telegram(
    rows: Iterable[Mapping[str, Any]],
    *,
    min_volume_ratio_20_exclusive: float = 1.0,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for row in rows or []:
        row_dict = dict(row or {})
        if not bool(row_dict.get("pullback_reentry", False)):
            continue
        volume_ratio = _safe_float(row_dict.get("volume_ratio_20", 0))
        if volume_ratio <= float(min_volume_ratio_20_exclusive):
            continue
        selected.append(row_dict)
    selected.sort(key=lambda row: (-_safe_float(row.get("scan_score", 0)), -_safe_float(row.get("es", 0)), str(row.get("ticker", ""))))
    return selected


def count_pullback_reentry_detected_rows(rows: Iterable[Mapping[str, Any]]) -> int:
    count = 0
    for row in rows or []:
        row_dict = dict(row or {})
        if _coerce_bool(row_dict.get("pullback_reentry", False)):
            count += 1
    return count


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"y", "yes", "true", "1", "t"}:
        return True
    if text in {"n", "no", "false", "0", "", "-", "none", "n/a"}:
        return False
    return bool(value)


def _final_entry_sort_key(row: Mapping[str, Any]) -> tuple[float, float, float, float, float, str]:
    return (
        -_safe_float(row.get("final_entry_score", 0.0)),
        -_safe_float(row.get("b_score", 0.0)),
        -_safe_float(row.get("c_score", 0.0)),
        -_safe_float(row.get("scan_score", 0.0)),
        -_safe_float(row.get("es", 0.0)),
        str(row.get("ticker", "")),
    )


def _with_post_close_final_top20_scores(
    rows: Iterable[Mapping[str, Any]],
    *,
    run_at_kst: datetime,
    scan_mode: str = "post_close",
    top_n: int = POST_CLOSE_FINAL_TOP_N,
) -> list[dict[str, Any]]:
    row_list: list[dict[str, Any]] = [dict(row or {}) for row in (rows or [])]
    target_date = _resolve_target_session_date(run_at_kst, scan_mode)
    top_limit = max(0, int(top_n or 0))
    eligible_rows: list[dict[str, Any]] = []

    for row_dict in row_list:
        hard_gate_pass = not _coerce_bool(row_dict.get("thin_trade_risk", False))

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

        latest_detected_date = _parse_iso_date(row_dict.get("detected_buy_signal_latest_date"))
        latest_detected_within_2d = bool(
            latest_detected_date is not None and 0 <= int((target_date - latest_detected_date).days) <= 2
        )
        b_score = int(
            sum(
                [
                    _coerce_bool(row_dict.get("pullback_reentry", False)) or _coerce_bool(row_dict.get("pocket_pivot_candidate", False)),
                    _coerce_bool(row_dict.get("gap_setup_candidate", False)),
                    0.0 <= _safe_float(row_dict.get("pullback_atr_multiple", -999.0)) <= 1.5,
                    latest_detected_within_2d,
                    _coerce_bool(row_dict.get("latest_session_utbot_buy_turn", False))
                    or _coerce_bool(row_dict.get("latest_session_hull_buy_turn", False)),
                ]
            )
        )

        c_score = int(
            sum(
                [
                    _safe_float(row_dict.get("cmf", 0.0)) > 0.05,
                    _safe_float(row_dict.get("obv_slope", 0.0)) > 0.1,
                    _coerce_bool(row_dict.get("volume_bullish", False)),
                    not _coerce_bool(row_dict.get("volume_abnormal", False)),
                ]
            )
        )

        a_pass = a_score >= 4
        b_pass = b_score >= 3
        c_pass = c_score >= 2
        eligible = bool(hard_gate_pass and a_pass and b_pass and c_pass)

        abc_norm = ((_safe_float(a_score) / 5.0) + (_safe_float(b_score) / 5.0) + (_safe_float(c_score) / 4.0)) / 3.0
        scan_norm = _clip(_safe_float(row_dict.get("scan_score", 0.0)) / 200.0, 0.0, 1.0)
        es_norm = _clip(_safe_float(row_dict.get("es", 0.0)) / 100.0, 0.0, 1.0)
        final_score = (abc_norm * 100.0) + (scan_norm * 10.0) + (es_norm * 5.0)

        row_dict["a_score"] = a_score
        row_dict["b_score"] = b_score
        row_dict["c_score"] = c_score
        row_dict["final_entry_score"] = round(final_score, 4)
        row_dict["final_entry_rank"] = 0
        row_dict["final_entry_selected"] = False
        row_dict["final_entry_eligible"] = eligible

        score_text = f"A{a_score}/B{b_score}/C{c_score}"
        if not hard_gate_pass:
            row_dict["final_entry_reason"] = f"{score_text} | HARD_FAIL:thin_trade_risk"
        elif eligible:
            row_dict["final_entry_reason"] = f"{score_text} | PASS"
        else:
            failed_dims: list[str] = []
            if not a_pass:
                failed_dims.append("A")
            if not b_pass:
                failed_dims.append("B")
            if not c_pass:
                failed_dims.append("C")
            row_dict["final_entry_reason"] = f"{score_text} | GATE_FAIL:{'/'.join(failed_dims) if failed_dims else '-'}"

        if eligible:
            eligible_rows.append(row_dict)

    selected_rows = sorted(eligible_rows, key=_final_entry_sort_key)[:top_limit]
    for rank, row_dict in enumerate(selected_rows, start=1):
        row_dict["final_entry_rank"] = rank
        row_dict["final_entry_selected"] = True

    return row_list


def select_post_close_final_top_rows_for_telegram(
    rows: Iterable[Mapping[str, Any]],
    *,
    top_n: int = POST_CLOSE_FINAL_TOP_N,
) -> list[dict[str, Any]]:
    selected = [dict(row or {}) for row in (rows or []) if _coerce_bool(dict(row or {}).get("final_entry_selected", False))]
    if not selected:
        return []
    if any(_safe_float(row.get("final_entry_rank", 0.0)) > 0.0 for row in selected):
        selected.sort(
            key=lambda row: (
                _safe_float(row.get("final_entry_rank", 0.0)) if _safe_float(row.get("final_entry_rank", 0.0)) > 0.0 else 1e9,
                str(row.get("ticker", "")),
            )
        )
    else:
        selected.sort(key=_final_entry_sort_key)
    return selected[: max(0, int(top_n or 0))]


def _sort_telegram_rows(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    row_list = [dict(row or {}) for row in (rows or [])]
    row_list.sort(key=lambda row: (-_safe_float(row.get("scan_score", 0)), -_safe_float(row.get("es", 0)), str(row.get("ticker", ""))))
    return row_list


def _setup_sort_key(row: Mapping[str, Any], *, score_key: str, gate_key: str) -> tuple[float, float, float, float, str]:
    return (
        -_safe_float(row.get(score_key, 0.0)),
        -_safe_float(row.get(gate_key, 0.0)),
        -_safe_float(row.get("scan_score", 0.0)),
        -_safe_float(row.get("es", 0.0)),
        str(row.get("ticker", "")),
    )


def _translate_gap_setup_hit_label(label: Any) -> str:
    text = str(label or "").strip()
    return GAP_SETUP_HIT_LABELS.get(text, text)


def _translate_pocket_pivot_hit_label(label: Any) -> str:
    text = str(label or "").strip()
    up_match = re.fullmatch(r"Up(\d+)", text)
    if up_match:
        return f"연속상승{up_match.group(1)}"
    pivot_match = re.fullmatch(r"PP(\d+)", text)
    if pivot_match:
        return f"포켓피벗{pivot_match.group(1)}일"
    return POCKET_PIVOT_HIT_LABELS.get(text, text)


def _format_setup_hit_summary(
    core_hits: Iterable[Any],
    quality_hits: Iterable[Any],
    *,
    max_items: int = 6,
    label_mapper: Callable[[Any], str] | None = None,
) -> str:
    labels: list[str] = []
    for label in list(core_hits or []):
        text = str(label_mapper(label) if label_mapper is not None else label or "").strip()
        if text and text not in labels:
            labels.append(text)
        if len(labels) >= max_items:
            return ", ".join(labels)
    for label in list(quality_hits or []):
        text = str(label_mapper(label) if label_mapper is not None else label or "").strip()
        if text and text not in labels:
            labels.append(text)
        if len(labels) >= max_items:
            break
    return ", ".join(labels) if labels else "-"


def select_post_close_pullback_rows_for_telegram(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for row in rows or []:
        row_dict = dict(row or {})
        if _coerce_bool(row_dict.get("thin_trade_risk", False)):
            continue
        if not _coerce_bool(row_dict.get("uptrend_persistent", False)):
            continue
        if _safe_float(row_dict.get("hma60_slope_pct", 0)) <= 0.0:
            continue
        if _safe_float(row_dict.get("pullback_from_swing_high_pct", 0)) >= -2.0:
            continue
        if _safe_float(row_dict.get("drawdown_from_20d_high_pct", 0)) >= -1.0:
            continue
        if _safe_float(row_dict.get("pullback_atr_multiple", 0)) > 3.5:
            continue
        if not (_coerce_bool(row_dict.get("pullback_ready", False)) or _coerce_bool(row_dict.get("pullback_reentry", False))):
            continue
        if _safe_float(row_dict.get("volume_dry_up_score", 0)) < 1.0:
            continue
        if _coerce_bool(row_dict.get("utbot_sell_recent", False)) or _coerce_bool(row_dict.get("hull_turn_bear_recent", False)):
            continue
        selected.append(row_dict)
    return _sort_telegram_rows(selected)


def select_post_close_chase_rows_for_telegram(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for row in rows or []:
        row_dict = dict(row or {})
        if _coerce_bool(row_dict.get("thin_trade_risk", False)):
            continue
        if not _coerce_bool(row_dict.get("bull_strength_recent", False)):
            continue
        if not _coerce_bool(row_dict.get("uptrend_persistent", False)):
            continue
        if _safe_float(row_dict.get("hma20_slope_pct", 0)) <= 0.0 or _safe_float(row_dict.get("hma60_slope_pct", 0)) <= 0.0:
            continue
        if not _coerce_bool(row_dict.get("volume_bullish", False)):
            continue
        if _safe_float(row_dict.get("adx", 0)) < 18.0:
            continue
        if _safe_float(row_dict.get("rs_rank_vs_index", 0)) < 55.0:
            continue
        if _safe_float(row_dict.get("multi_buy", 0)) < 2.0:
            continue
        if _safe_float(row_dict.get("dist_sma20_pct", 0)) >= 30.0:
            continue
        if _safe_float(row_dict.get("zscore20", 0)) >= 3.5:
            continue
        if _safe_float(row_dict.get("scan_score", 0)) < 120.0:
            continue
        if _coerce_bool(row_dict.get("utbot_sell_recent", False)) or _coerce_bool(row_dict.get("hull_turn_bear_recent", False)):
            continue
        selected.append(row_dict)
    return _sort_telegram_rows(selected)


def _buy_turn_tier_tag(row: Mapping[str, Any]) -> str:
    days_candidates: list[int] = []
    utbot_buy_date = _parse_iso_date(row.get("utbot_buy_last_date"))
    hull_buy_date = _parse_iso_date(row.get("hull_turn_bull_last_date"))
    if utbot_buy_date is not None:
        days_candidates.append(max(0, int(_safe_float(row.get("days_since_utbot_buy", 0)))))
    if hull_buy_date is not None:
        days_candidates.append(max(0, int(_safe_float(row.get("days_since_hull_turn_bull", 0)))))
    if not days_candidates:
        return "SessionTurn"
    if min(days_candidates) <= 0:
        return "Tier1 D0"
    return "Tier2 D1-2"


def select_post_close_buy_turn_rows_for_telegram(
    rows: Iterable[Mapping[str, Any]],
    *,
    run_at_kst: datetime,
    scan_mode: str = "post_close",
    min_volume_ratio_20_exclusive: float = 0.9,
) -> list[dict[str, Any]]:
    target_date = _resolve_target_session_date(run_at_kst, scan_mode)
    selected: list[dict[str, Any]] = []
    for row in rows or []:
        row_dict = dict(row or {})
        if _coerce_bool(row_dict.get("thin_trade_risk", False)):
            continue
        latest_session_turn = _coerce_bool(row_dict.get("latest_session_utbot_buy_turn", False)) or _coerce_bool(
            row_dict.get("latest_session_hull_buy_turn", False)
        )
        utbot_buy_date = _parse_iso_date(row_dict.get("utbot_buy_last_date"))
        hull_buy_date = _parse_iso_date(row_dict.get("hull_turn_bull_last_date"))
        days_since_utbot = max(0, int(_safe_float(row_dict.get("days_since_utbot_buy", 0))))
        days_since_hull = max(0, int(_safe_float(row_dict.get("days_since_hull_turn_bull", 0))))
        recent_buy_turn = (utbot_buy_date is not None and days_since_utbot <= 2) or (hull_buy_date is not None and days_since_hull <= 2)
        if not (latest_session_turn or recent_buy_turn):
            continue
        if not (
            _coerce_bool(row_dict.get("utbot_buy_recent", False))
            or _coerce_bool(row_dict.get("hull_turn_bull_recent", False))
            or _coerce_bool(row_dict.get("bull_turn_recent", False))
        ):
            continue
        utbot_sell_date = _parse_iso_date(row_dict.get("utbot_sell_last_date"))
        hull_bear_date = _parse_iso_date(row_dict.get("hull_turn_bear_last_date"))
        if utbot_sell_date == target_date or hull_bear_date == target_date:
            continue
        if _safe_float(row_dict.get("cmf", 0)) <= -0.10:
            continue
        if _safe_float(row_dict.get("obv_slope", 0)) <= 0.0:
            continue
        if _safe_float(row_dict.get("volume_ratio_20", 0)) <= float(min_volume_ratio_20_exclusive):
            continue
        row_dict["buy_turn_filter_tag"] = _buy_turn_tier_tag(row_dict)
        selected.append(row_dict)
    return _sort_telegram_rows(selected)


def select_post_close_gap_setup_rows_for_telegram(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for row in rows or []:
        row_dict = dict(row or {})
        if _coerce_bool(row_dict.get("thin_trade_risk", False)):
            continue
        if not _coerce_bool(row_dict.get("gap_setup_candidate", False)):
            continue
        hit_summary = _format_setup_hit_summary(
            row_dict.get("gap_setup_hits"),
            row_dict.get("gap_setup_quality_hits"),
            label_mapper=_translate_gap_setup_hit_label,
        )
        row_dict["gap_setup_tag"] = (
            f"GAP {int(_safe_float(row_dict.get('gap_setup_score', 0))):d}/{GAP_SETUP_MAX_SCORE}"
            f" | G{int(_safe_float(row_dict.get('gap_setup_gate_count', 0))):d}/5"
            f" | {hit_summary}"
        )
        selected.append(row_dict)
    selected.sort(key=lambda row: _setup_sort_key(row, score_key="gap_setup_score", gate_key="gap_setup_gate_count"))
    return selected[:POST_CLOSE_SETUP_TOP_N]


def select_post_close_pocket_pivot_rows_for_telegram(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for row in rows or []:
        row_dict = dict(row or {})
        if _coerce_bool(row_dict.get("thin_trade_risk", False)):
            continue
        if not _coerce_bool(row_dict.get("pocket_pivot_candidate", False)):
            continue
        hit_summary = _format_setup_hit_summary(
            row_dict.get("pocket_pivot_hits"),
            row_dict.get("pocket_pivot_quality_hits"),
            label_mapper=_translate_pocket_pivot_hit_label,
        )
        row_dict["pocket_pivot_tag"] = (
            f"PP {int(_safe_float(row_dict.get('pocket_pivot_score', 0))):d}/{POCKET_PIVOT_MAX_SCORE}"
            f" | G{int(_safe_float(row_dict.get('pocket_pivot_gate_count', 0))):d}/5"
            f" | {hit_summary}"
        )
        selected.append(row_dict)
    selected.sort(key=lambda row: _setup_sort_key(row, score_key="pocket_pivot_score", gate_key="pocket_pivot_gate_count"))
    return selected[:POST_CLOSE_SETUP_TOP_N]


def select_post_close_top_5d_rows_for_telegram(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for row in rows or []:
        row_dict = dict(row or {})
        chg_5d = _safe_float(row_dict.get("chg_5d", 0.0))
        if chg_5d <= 0.0:
            continue
        row_dict["five_day_top_tag"] = f"5일 {chg_5d:+.2f}%"
        selected.append(row_dict)
    selected.sort(
        key=lambda row: (
            -_safe_float(row.get("chg_5d", 0.0)),
            -_safe_float(row.get("scan_score", 0.0)),
            -_safe_float(row.get("es", 0.0)),
            str(row.get("ticker", "")),
        )
    )
    return selected[:POST_CLOSE_SETUP_TOP_N]


def select_us_session_hull_bear_rows(rows: Iterable[Mapping[str, Any]], *, run_at_kst: datetime, scan_mode: str = "post_close") -> list[dict[str, Any]]:
    target_date = _resolve_target_session_date(run_at_kst, scan_mode)
    selected: list[dict[str, Any]] = []
    for row in rows or []:
        row_dict = dict(row or {})
        hull_bear_date = _parse_iso_date(row_dict.get("hull_turn_bear_last_date"))
        if hull_bear_date != target_date:
            continue
        selected.append(row_dict)
    selected.sort(key=lambda row: (-_safe_float(row.get("scan_score", 0)), -_safe_float(row.get("es", 0)), str(row.get("ticker", ""))))
    return selected


def select_us_session_52w_high_rows(rows: Iterable[Mapping[str, Any]], *, run_at_kst: datetime, scan_mode: str = "post_close") -> list[dict[str, Any]]:
    target_date = _resolve_target_session_date(run_at_kst, scan_mode)
    selected: list[dict[str, Any]] = []
    for row in rows or []:
        row_dict = dict(row or {})
        if not bool(row_dict.get("new_52w_high", False)):
            continue
        bar_date = _parse_iso_date(row_dict.get("latest_bar_date"))
        if bar_date != target_date:
            continue
        selected.append(row_dict)
    selected.sort(key=lambda row: (-_safe_float(row.get("scan_score", 0)), -_safe_float(row.get("es", 0)), str(row.get("ticker", ""))))
    return selected


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


def _is_buy_turn_signal(signal: Any, *, engine: str) -> bool:
    text = str(signal or "").strip().lower()
    if engine not in text:
        return False
    return "buy" in text or "매수" in str(signal or "")


def _post_close_buy_turn_label(row: Mapping[str, Any]) -> str:
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


def _build_post_close_section_row_line(
    row: Mapping[str, Any],
    index: int,
    *,
    include_buy_label: bool = False,
) -> str:
    parts = [
        f"{index}. {row.get('ticker', '-')}",
        f"({_fmt_signed_number(row.get('chg_value', 0), 2)}, {_fmt_signed_number(row.get('chg', 0), 2)}%)",
        f"거래량{_fmt_ratio(row.get('volume_ratio_20', 0), 2)}",
    ]
    if include_buy_label:
        buy_label = _post_close_buy_turn_label(row)
        if buy_label:
            parts.append(buy_label)
    return " | ".join(parts)


def _build_section_row_line(row: Mapping[str, Any], index: int, tag_text: str) -> str:
    return (
        f"{index}. {row.get('ticker', '-')}"
        f" | ({_fmt_signed_number(row.get('chg_value', 0), 2)}, {_fmt_signed_number(row.get('chg', 0), 2)}%)"
        f" | 거래량{_fmt_ratio(row.get('volume_ratio_20', 0), 2)}"
        f" | {row.get('jg_key', '-')}"
        f" | {str(tag_text or '-')}"
    )


def _build_summary_section_lines(
    *,
    section_index: int,
    section_total: int,
    section_name: str,
    criteria: str,
    rows: Iterable[Mapping[str, Any]],
    summary_limit: int,
    tag_builder: Any,
    row_builder: Callable[[Mapping[str, Any], int], str] | None = None,
) -> list[str]:
    all_rows = [dict(row or {}) for row in (rows or [])]
    limited_rows = all_rows if int(summary_limit) <= 0 else all_rows[: int(summary_limit)]
    lines = [
        f"=== [{section_index}/{section_total}] {section_name} ===",
        f"기준: {criteria}",
        f"건수: {len(all_rows)}개",
    ]
    if not all_rows:
        lines.append("- 해당 없음")
        return lines
    for idx, row in enumerate(limited_rows, start=1):
        if row_builder is not None:
            lines.append(row_builder(row, idx))
        else:
            lines.append(_build_section_row_line(row, idx, str(tag_builder(row) or "-")))
    remain = len(all_rows) - len(limited_rows)
    if remain > 0:
        lines.append(f"... 외 {remain}개")
    return lines


def build_transition_summary(
    turn_rows: Iterable[Mapping[str, Any]],
    *,
    run_at_kst: datetime,
    universe_count: int,
    result_count: int,
    skip_count: int,
    scan_label: str = "자동 스캔",
    detected_turn_count: int | None = None,
    summary_limit: int = 0,
    pullback_rows: Iterable[Mapping[str, Any]] | None = None,
    hull_bear_rows: Iterable[Mapping[str, Any]] | None = None,
    high_52w_rows: Iterable[Mapping[str, Any]] | None = None,
    scan_mode: str = "post_close",
    volume_threshold: float | None = None,
) -> str:
    buy_rows = [dict(row or {}) for row in (turn_rows or [])]
    pullback_rows_list = [dict(row or {}) for row in (pullback_rows or [])]
    hull_bear_rows_list = [dict(row or {}) for row in (hull_bear_rows or [])]
    high_52w_rows_list = [dict(row or {}) for row in (high_52w_rows or [])]
    detected_count = len(buy_rows) if detected_turn_count is None else max(0, int(detected_turn_count))
    target_us_session_date = _resolve_target_session_date(run_at_kst, scan_mode)

    index_line = (
        f"- 요약 인덱스: 매수전환 {len(buy_rows)}"
        f" | 눌림목 {len(pullback_rows_list)}"
        f" | HULL매도 {len(hull_bear_rows_list)}"
        f" | 52W 신고가 {len(high_52w_rows_list)}"
    )

    if scan_mode == "pre_market":
        lines = [
            f"[{str(scan_label or '프리마켓 스캔')}] {run_at_kst.strftime('%Y-%m-%d %H:%M:%S')} KST",
            f"- 기준: 전일 미국장 확정 데이터({target_us_session_date.isoformat()})",
            f"- 목적: 오늘 본장에서 주목할 종목 선점",
            f"- 유니버스: {universe_count}개 | 스캔 결과: {result_count}개",
            index_line,
            "",
        ]
    elif scan_mode == "early_session":
        vol_text = f"{volume_threshold:.3f}x" if volume_threshold is not None else "시간비례"
        lines = [
            f"[{str(scan_label or '얼리세션 스캔')}] {run_at_kst.strftime('%Y-%m-%d %H:%M:%S')} KST",
            f"- 기준: 당일 미국장 장중 스냅샷 데이터({target_us_session_date.isoformat()}) 추세 미확정",
            f"- 목적: 장 시작 전 강세 종목 빠른 포착",
            f"- 거래량 기준: {vol_text} (시간비례 보정 적용)",
            f"- 유니버스: {universe_count}개 | 스캔 결과: {result_count}개(제외 {skip_count}개)",
            "- 장중 추세 변동으로 신호/거래량은 장 마감 후 변경될 수 있습니다",
            index_line,
            "",
        ]
    else:
        lines = [
            f"[{str(scan_label or '자동 스캔')}] {run_at_kst.strftime('%Y-%m-%d %H:%M:%S')} KST",
            f"- 전일 미국장 기준일: {target_us_session_date.isoformat()} (US/Eastern)",
            f"- 유니버스: {universe_count}개",
            f"- 전체 스캔 결과: {result_count}개(제외 {skip_count}개)",
            index_line,
            "",
        ]

    if volume_threshold is not None and volume_threshold < 1.0:
        vol_precision = ".3f" if scan_mode == "early_session" else ".2f"
        vol_criteria_suffix = f" + 거래량> {format(volume_threshold, vol_precision)}x"
    else:
        vol_criteria_suffix = " + 거래량> 1.0x"
    session_label = "장중" if scan_mode == "early_session" else "전일 미국장(US/Eastern)"

    sections = [
        _build_summary_section_lines(
            section_index=1,
            section_total=4,
            section_name="매수전환",
            criteria=(f"{session_label} UTBot/HULL 매수전환{vol_criteria_suffix} (감지 {detected_count}개)"),
            rows=buy_rows,
            summary_limit=summary_limit,
            tag_builder=lambda row: ", ".join(list(dict(row or {}).get("transition_signals") or [])) or "-",
        ),
        _build_summary_section_lines(
            section_index=2,
            section_total=4,
            section_name="눌림목 재진입",
            criteria=f"pullback_reentry=True{vol_criteria_suffix}",
            rows=pullback_rows_list,
            summary_limit=summary_limit,
            tag_builder=lambda _row: "PULLBACK 재진입",
        ),
        _build_summary_section_lines(
            section_index=3,
            section_total=4,
            section_name="당일 HULL 매도",
            criteria=f"hull_turn_bear_last_date == {target_us_session_date.isoformat()}",
            rows=hull_bear_rows_list,
            summary_limit=summary_limit,
            tag_builder=lambda _row: "HULL 매도",
        ),
        _build_summary_section_lines(
            section_index=4,
            section_total=4,
            section_name="52주 신고가 갱신",
            criteria=f"New_52W_High=True + latest_bar_date == {target_us_session_date.isoformat()}",
            rows=high_52w_rows_list,
            summary_limit=summary_limit,
            tag_builder=lambda _row: "52W 신고가",
        ),
    ]
    for block in sections:
        lines.extend(block)
        lines.append("")

    if lines and not str(lines[-1]).strip():
        lines.pop()
    return "\n".join(lines)


def build_post_close_transition_summary(
    turn_rows: Iterable[Mapping[str, Any]],
    *,
    run_at_kst: datetime,
    universe_count: int,
    result_count: int,
    skip_count: int,
    scan_label: str = "Daily Scan",
    detected_turn_count: int | None = None,
    summary_limit: int = 0,
    pullback_rows: Iterable[Mapping[str, Any]] | None = None,
    hull_bear_rows: Iterable[Mapping[str, Any]] | None = None,
    high_52w_rows: Iterable[Mapping[str, Any]] | None = None,
    pullback_filter_rows: Iterable[Mapping[str, Any]] | None = None,
    chase_filter_rows: Iterable[Mapping[str, Any]] | None = None,
    buy_turn_filter_rows: Iterable[Mapping[str, Any]] | None = None,
    gap_setup_rows: Iterable[Mapping[str, Any]] | None = None,
    pocket_pivot_rows: Iterable[Mapping[str, Any]] | None = None,
    five_day_top_rows: Iterable[Mapping[str, Any]] | None = None,
    final_top_rows: Iterable[Mapping[str, Any]] | None = None,
) -> str:
    buy_rows = [dict(row or {}) for row in (turn_rows or [])]
    pullback_rows_list = [dict(row or {}) for row in (pullback_rows or [])]
    hull_bear_rows_list = [dict(row or {}) for row in (hull_bear_rows or [])]
    high_52w_rows_list = [dict(row or {}) for row in (high_52w_rows or [])]
    pullback_filter_rows_list = [dict(row or {}) for row in (pullback_filter_rows or [])]
    chase_filter_rows_list = [dict(row or {}) for row in (chase_filter_rows or [])]
    buy_turn_filter_rows_list = [dict(row or {}) for row in (buy_turn_filter_rows or [])]
    gap_setup_rows_list = [dict(row or {}) for row in (gap_setup_rows or [])]
    pocket_pivot_rows_list = [dict(row or {}) for row in (pocket_pivot_rows or [])]
    five_day_top_rows_list = [dict(row or {}) for row in (five_day_top_rows or [])]
    final_top_rows_list = [dict(row or {}) for row in (final_top_rows or [])]
    detected_count = len(buy_rows) if detected_turn_count is None else max(0, int(detected_turn_count))
    target_us_session_date = _resolve_target_session_date(run_at_kst, "post_close")

    index_line = (
        f"- 요약 인덱스: {POST_CLOSE_INDEX_TITLES['legacy_turn']} {len(buy_rows)}"
        f" | {POST_CLOSE_INDEX_TITLES['legacy_pullback']} {len(pullback_rows_list)}"
        f" | {POST_CLOSE_INDEX_TITLES['legacy_hull_bear']} {len(hull_bear_rows_list)}"
        f" | {POST_CLOSE_INDEX_TITLES['legacy_52w_high']} {len(high_52w_rows_list)}"
        f" | {POST_CLOSE_INDEX_TITLES['pullback_filter']} {len(pullback_filter_rows_list)}"
        f" | {POST_CLOSE_INDEX_TITLES['chase_filter']} {len(chase_filter_rows_list)}"
        f" | {POST_CLOSE_INDEX_TITLES['buy_turn_filter']} {len(buy_turn_filter_rows_list)}"
        f" | {POST_CLOSE_INDEX_TITLES['gap_setup']} {len(gap_setup_rows_list)}"
        f" | {POST_CLOSE_INDEX_TITLES['pocket_pivot']} {len(pocket_pivot_rows_list)}"
        f" | {POST_CLOSE_INDEX_TITLES['five_day_top']} {len(five_day_top_rows_list)}"
    )
    if final_top_rows is not None:
        index_line += f" | {POST_CLOSE_FINAL_INDEX_TITLE} {len(final_top_rows_list)}"

    lines = [
        f"[{str(scan_label or 'Daily Scan')}] {run_at_kst.strftime('%Y-%m-%d %H:%M:%S')} KST",
        f"- 대상 미국 세션일: {target_us_session_date.isoformat()} (US/Eastern)",
        f"- 유니버스: {universe_count}",
        f"- 스캔 결과: {result_count} | 제외: {skip_count}",
        index_line,
        "",
    ]

    section_total = POST_CLOSE_SUMMARY_SECTION_TOTAL + (1 if final_top_rows is not None else 0)

    sections = [
        _build_summary_section_lines(
            section_index=1,
            section_total=section_total,
            section_name=POST_CLOSE_SECTION_TITLES["legacy_turn"],
            criteria=f"legacy UTBot/HULL buy-turn + volume>1.0x (detected={detected_count})",
            rows=buy_rows,
            summary_limit=summary_limit,
            tag_builder=lambda row: ", ".join(list(dict(row or {}).get("transition_signals") or [])) or "-",
            row_builder=lambda row, idx: _build_post_close_section_row_line(row, idx, include_buy_label=True),
        ),
        _build_summary_section_lines(
            section_index=2,
            section_total=section_total,
            section_name=POST_CLOSE_SECTION_TITLES["legacy_pullback"],
            criteria="pullback_reentry=True + volume>1.0x",
            rows=pullback_rows_list,
            summary_limit=summary_limit,
            tag_builder=lambda _row: "눌림 재진입",
            row_builder=lambda row, idx: _build_post_close_section_row_line(row, idx),
        ),
        _build_summary_section_lines(
            section_index=3,
            section_total=section_total,
            section_name=POST_CLOSE_SECTION_TITLES["legacy_hull_bear"],
            criteria=f"hull_turn_bear_last_date == {target_us_session_date.isoformat()}",
            rows=hull_bear_rows_list,
            summary_limit=summary_limit,
            tag_builder=lambda _row: "HULL 매도전환",
            row_builder=lambda row, idx: _build_post_close_section_row_line(row, idx),
        ),
        _build_summary_section_lines(
            section_index=4,
            section_total=section_total,
            section_name=POST_CLOSE_SECTION_TITLES["legacy_52w_high"],
            criteria=f"new_52w_high=True + latest_bar_date == {target_us_session_date.isoformat()}",
            rows=high_52w_rows_list,
            summary_limit=summary_limit,
            tag_builder=lambda _row: "52주 신고가",
            row_builder=lambda row, idx: _build_post_close_section_row_line(row, idx),
        ),
        _build_summary_section_lines(
            section_index=5,
            section_total=section_total,
            section_name=POST_CLOSE_SECTION_TITLES["pullback_filter"],
            criteria=(
                "uptrend_persistent=Y + hma60_slope_pct>0 + pullback_from_swing_high_pct<-2 + "
                "drawdown_from_20d_high_pct<-1 + pullback_atr_multiple<=3.5 + "
                "(pullback_ready or pullback_reentry) + volume_dry_up_score>=1 + no recent UT/HULL sell"
            ),
            rows=pullback_filter_rows_list,
            summary_limit=summary_limit,
            tag_builder=lambda _row: "눌림목 필터",
            row_builder=lambda row, idx: _build_post_close_section_row_line(row, idx),
        ),
        _build_summary_section_lines(
            section_index=6,
            section_total=section_total,
            section_name=POST_CLOSE_SECTION_TITLES["chase_filter"],
            criteria=(
                "bull_strength_recent=Y + uptrend_persistent=Y + hma20/60 slope>0 + volume_bullish=Y + "
                "adx>=18 + rs_rank_vs_index>=55 + multi_buy>=2 + dist_sma20_pct<30 + zscore20<3.5 + scan_score>=120"
            ),
            rows=chase_filter_rows_list,
            summary_limit=summary_limit,
            tag_builder=lambda _row: "추세추종 필터",
            row_builder=lambda row, idx: _build_post_close_section_row_line(row, idx),
        ),
        _build_summary_section_lines(
            section_index=7,
            section_total=section_total,
            section_name=POST_CLOSE_SECTION_TITLES["buy_turn_filter"],
            criteria=(
                "(latest_session_turn or days<=2) + (utbot_buy_recent or hull_turn_bull_recent or bull_turn_recent) + "
                "cmf>-0.10 + obv_slope>0 + volume_ratio_20>0.9 + no sell on target session"
            ),
            rows=buy_turn_filter_rows_list,
            summary_limit=summary_limit,
            tag_builder=lambda row: str(dict(row or {}).get("buy_turn_filter_tag") or "매수전환 필터"),
            row_builder=lambda row, idx: _build_post_close_section_row_line(row, idx, include_buy_label=True),
        ),
        _build_summary_section_lines(
            section_index=8,
            section_total=section_total,
            section_name=POST_CLOSE_SECTION_TITLES["gap_setup"],
            criteria=(
                "gate>=3/5 + score(sorted by score/gate/scan/es) | "
                "DryUp + 20DHigh proximity + BB/ATR compression + RS leadership + HMA/ADX trend"
            ),
            rows=gap_setup_rows_list,
            summary_limit=summary_limit,
            tag_builder=lambda row: str(dict(row or {}).get("gap_setup_tag") or "에너지 압축"),
            row_builder=lambda row, idx: _build_post_close_section_row_line(row, idx),
        ),
        _build_summary_section_lines(
            section_index=9,
            section_total=section_total,
            section_name=POST_CLOSE_SECTION_TITLES["pocket_pivot"],
            criteria=(
                "gate>=3/5 + score(sorted by score/gate/scan/es) | "
                "Volume expansion + recent UT buy + shallow pullback + CMF/OBV accumulation + multi-buy"
            ),
            rows=pocket_pivot_rows_list,
            summary_limit=summary_limit,
            tag_builder=lambda row: str(dict(row or {}).get("pocket_pivot_tag") or "기관 매집"),
            row_builder=lambda row, idx: _build_post_close_section_row_line(row, idx),
        ),
        _build_summary_section_lines(
            section_index=10,
            section_total=section_total,
            section_name=POST_CLOSE_SECTION_TITLES["five_day_top"],
            criteria="chg_5d > 0 sorted by chg_5d/scan_score/es",
            rows=five_day_top_rows_list,
            summary_limit=summary_limit,
            tag_builder=lambda row: str(dict(row or {}).get("five_day_top_tag") or f"5일 {_fmt_signed_number(row.get('chg_5d', 0), 2)}%"),
            row_builder=lambda row, idx: _build_post_close_section_row_line(row, idx),
        ),
    ]
    if final_top_rows is not None:
        sections.append(
            _build_summary_section_lines(
                section_index=section_total,
                section_total=section_total,
                section_name=POST_CLOSE_FINAL_SECTION_NAME,
                criteria=(
                    "A>=4/5 + B>=3/5 + C>=2/4 + thin_trade_risk=N "
                    "(tie-break: B score > C score > scan_score > es)"
                ),
                rows=final_top_rows_list,
                summary_limit=summary_limit,
                tag_builder=lambda row: (
                    f"{str(dict(row or {}).get('final_entry_reason') or '-')}"
                    f" | 점수 {_safe_float(dict(row or {}).get('final_entry_score', 0.0)):.2f}"
                ),
                row_builder=lambda row, idx: _build_post_close_section_row_line(row, idx),
            )
        )
    for block in sections:
        lines.extend(block)
        lines.append("")

    if lines and not str(lines[-1]).strip():
        lines.pop()
    return "\n".join(lines)


def _telegram_api(token: str, method: str) -> str:
    return f"https://api.telegram.org/bot{token}/{method}"


def split_telegram_message_text(text: str, *, chunk_size: int = 3500) -> list[str]:
    raw = str(text or "")
    limit = max(1, int(chunk_size))
    if len(raw) <= limit:
        return [raw]

    def _split_by_lines(raw_text: str) -> list[str]:
        chunks: list[str] = []
        current: list[str] = []
        current_len = 0
        for line in str(raw_text or "").splitlines():
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
        return chunks or [raw_text]

    # Prefer section-aware chunking for daily scanner report blocks.
    if re.search(r"=== \[1/\d+\]", raw):
        lines = raw.splitlines()
        section_blocks: list[list[str]] = []
        current_block: list[str] = []
        for line in lines:
            if line.startswith("=== [") and current_block:
                section_blocks.append(current_block)
                current_block = [line]
            else:
                current_block.append(line)
        if current_block:
            section_blocks.append(current_block)

        # Keep header preface and first section together when present.
        if len(section_blocks) >= 2 and not str(section_blocks[0][0] if section_blocks[0] else "").startswith("=== ["):
            section_blocks[1] = list(section_blocks[0]) + list(section_blocks[1])
            section_blocks = section_blocks[1:]

        chunked: list[str] = []
        current_lines: list[str] = []
        current_len = 0
        for block_lines in section_blocks:
            block = [str(line) for line in block_lines]
            block_len = sum(len(line) + 1 for line in block)
            if block_len > limit:
                if current_lines:
                    chunked.append("\n".join(current_lines))
                    current_lines = []
                    current_len = 0
                # Fallback: split oversized block line-by-line.
                fallback_chunks = _split_by_lines("\n".join(block))
                chunked.extend(fallback_chunks)
                continue

            if current_lines and (current_len + block_len > limit):
                chunked.append("\n".join(current_lines))
                current_lines = list(block)
                current_len = block_len
            else:
                current_lines.extend(block)
                current_len += block_len

        if current_lines:
            chunked.append("\n".join(current_lines))
        if chunked:
            return chunked

    return _split_by_lines(raw)


def send_telegram_message(token: str, chat_id: str, text: str, *, chunk_size: int = 3500) -> None:
    chunks = split_telegram_message_text(text, chunk_size=chunk_size)
    for chunk_idx, chunk in enumerate(chunks, start=1):
        if not str(chunk or "").strip():
            continue
        success = False
        last_error = ""
        for attempt in range(1, 4):
            try:
                response = requests.post(
                    _telegram_api(token, "sendMessage"),
                    json={"chat_id": chat_id, "text": chunk},
                    timeout=30,
                )
                response.raise_for_status()
                payload = response.json()
                if payload.get("ok"):
                    success = True
                    break
                else:
                    last_error = f"Payload not ok: {payload}"
            except Exception as exc:
                last_error = str(exc)
            
            if attempt < 3:
                time.sleep(2)
        
        if not success:
            print(f"[ERROR] Failed to send Telegram message chunk {chunk_idx}/{len(chunks)} after 3 attempts. Last error: {last_error}")


def send_telegram_document(token: str, chat_id: str, file_path: Path, caption: str = "") -> None:
    success = False
    last_error = ""
    for attempt in range(1, 4):
        try:
            with file_path.open("rb") as handle:
                response = requests.post(
                    _telegram_api(token, "sendDocument"),
                    data={"chat_id": chat_id, "caption": caption},
                    files={"document": (file_path.name, handle, "text/csv")},
                    timeout=60,
                )
            response.raise_for_status()
            payload = response.json()
            if payload.get("ok"):
                success = True
                break
            else:
                last_error = f"Payload not ok: {payload}"
        except Exception as exc:
            last_error = str(exc)
            
        if attempt < 3:
            time.sleep(2)
            
    if not success:
        print(f"[ERROR] Failed to send Telegram document {file_path.name} after 3 attempts. Last error: {last_error}")


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
    parser.add_argument("--run-stamp", default="", help="Shared batch id for shard/merge grouping")
    parser.add_argument(
        "--universe-profile",
        default="default",
        choices=sorted(UNIVERSE_PROFILE_ITEMS.keys()),
        help="Universe profile (default or russell2000)",
    )
    parser.add_argument(
        "--scan-mode",
        default="post_close",
        choices=["post_close", "pre_market", "early_session"],
        help="post_close(05시 장마감), pre_market(21시 프리마켓), early_session(23시 장초반)",
    )
    parser.add_argument(
        "--prev-scan-dir",
        default="",
        help="pre_market 모드: 이전 post_close 스캔 결과를 로드할 디렉토리",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Phase 4: Pre-market helper functions
# ---------------------------------------------------------------------------

def _load_json_file(path: Path) -> Any:
    """JSON 파일 로드 유틸."""
    with path.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def _load_latest_scan_rows(scan_dir: Path) -> tuple[list[dict[str, Any]], Path | None]:
    """가장 최근의 scan_rows JSON 로드. merged 우선, 없으면 단일 shard."""
    merged = sorted(scan_dir.glob("scan_rows_*_merged.json"), reverse=True)
    if merged:
        data = _load_json_file(merged[0])
        rows = list(data) if isinstance(data, list) else list(data.get("rows", [])) if isinstance(data, dict) else []
        return rows, merged[0]
    singles = sorted(scan_dir.glob("scan_rows_*.json"), reverse=True)
    if singles:
        data = _load_json_file(singles[0])
        rows = list(data) if isinstance(data, list) else list(data.get("rows", [])) if isinstance(data, dict) else []
        return rows, singles[0]
    return [], None


def _fetch_premarket_gaps(
    tickers: list[str],
    *,
    max_workers: int = 8,
) -> dict[str, dict[str, float]]:
    """프리마켓 가격을 수집해 전일 종가 대비 갭 계산."""

    def _fetch_one(ticker: str) -> tuple[str, dict[str, float] | None]:
        try:
            hist = yf.Ticker(ticker).history(period="5d", prepost=True)
            if hist is None or len(hist) < 2:
                return ticker, None
            prev_close = float(hist["Close"].iloc[-2])
            current = float(hist["Close"].iloc[-1])
            if prev_close <= 0:
                return ticker, None
            gap_pct = (current - prev_close) / prev_close * 100
            return ticker, {
                "premarket_price": round(current, 4),
                "prev_close": round(prev_close, 4),
                "gap_pct": round(gap_pct, 4),
            }
        except Exception:
            return ticker, None

    results: dict[str, dict[str, float]] = {}
    effective_workers = min(max_workers, max(1, len(tickers)))
    with ThreadPoolExecutor(max_workers=effective_workers) as executor:
        futures = {executor.submit(_fetch_one, t): t for t in tickers}
        for future in as_completed(futures):
            ticker, data = future.result()
            if data is not None:
                results[ticker] = data
    return results


def _enrich_rows_with_gap(
    rows: list[dict[str, Any]],
    gap_data: dict[str, dict[str, float]],
) -> list[dict[str, Any]]:
    """기존 스캔 결과에 프리마켓 갭 데이터를 주입."""
    enriched = []
    for row in rows:
        row_dict = dict(row)
        ticker = str(row_dict.get("ticker", "")).strip().upper()
        gap = gap_data.get(ticker)
        if gap:
            row_dict["premarket_price"] = gap["premarket_price"]
            row_dict["prev_close"] = gap["prev_close"]
            row_dict["gap_pct"] = gap["gap_pct"]
        else:
            row_dict["premarket_price"] = _safe_float(row_dict.get("price", 0))
            row_dict["prev_close"] = _safe_float(row_dict.get("price", 0))
            row_dict["gap_pct"] = 0.0
        enriched.append(row_dict)
    return enriched


# ---------------------------------------------------------------------------
# Phase 6: Run mode functions
# ---------------------------------------------------------------------------

def _send_telegram_if_enabled(
    args: argparse.Namespace,
    *,
    summary_text: str,
    csv_path: Path,
    scan_label: str,
    run_at_kst: datetime,
) -> None:
    """Telegram 전송 공통 로직."""
    if args.dry_run or args.skip_telegram:
        print("[SCAN] Telegram send skipped by option.")
        return

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
        caption=f"{scan_label} CSV ({run_at_kst.strftime('%Y-%m-%d %H:%M')} KST)",
    )
    print("[SCAN] Telegram notification completed.")


def _resolve_cli_run_stamp(args: argparse.Namespace, *, run_at_kst: datetime) -> str:
    explicit_run_stamp = str(getattr(args, "run_stamp", "") or "").strip()
    if explicit_run_stamp:
        return explicit_run_stamp
    return run_at_kst.strftime("%Y%m%d_%H%M%S")


def _run_post_close(args: argparse.Namespace, *, run_at_kst: datetime, out_dir: Path) -> int:
    """기존 05시 post_close 로직."""
    run_stamp = _resolve_cli_run_stamp(args, run_at_kst=run_at_kst)
    shard_count = int(args.shard_count or 1)
    shard_index = int(args.shard_index or 0)
    merge_dir_arg = str(args.merge_dir or "").strip()
    merge_dir = Path(merge_dir_arg).expanduser().resolve() if merge_dir_arg else None
    universe_profile = _normalize_universe_profile(args.universe_profile)
    scan_label = _scan_label_for_profile(universe_profile)
    scan_mode = "post_close"
    latest_session_date = _last_us_market_session_date(run_at_kst)
    telegram_skipped_reason = ""

    if merge_dir:
        explicit_run_stamp = str(getattr(args, "run_stamp", "") or "").strip()
        if not explicit_run_stamp:
            raise RuntimeError("--run-stamp is required when --merge-dir is used in post_close mode")
        run_label = f"{run_stamp}_merged"
        print(f"[MERGE] Loading shard artifacts from {merge_dir}")
        merged_payload = merge_shard_scan_rows(merge_dir, required_run_stamp=run_stamp)
        merged_rows = list(merged_payload.get("rows") or [])
        profile_candidates = list(merged_payload.get("universe_profiles") or [])
        if universe_profile == "default" and len(profile_candidates) == 1:
            universe_profile = _normalize_universe_profile(profile_candidates[0])
            scan_label = _scan_label_for_profile(universe_profile)
        print(
            f"[MERGE] Completed: merged={len(merged_rows)} "
            f"source_rows={int(merged_payload.get('source_row_count', 0))} "
            f"source_sum={int(merged_payload.get('source_result_count_sum', 0))}"
        )
        csv_rows = _with_latest_session_buy_turn_flags(merged_rows, target_date=latest_session_date)
        csv_rows = _with_post_close_cross_section_metrics(csv_rows, enabled=True)
        csv_rows = _with_post_close_setup_scores(csv_rows)
        csv_rows = _with_post_close_final_top20_scores(
            csv_rows,
            run_at_kst=run_at_kst,
            scan_mode=scan_mode,
            top_n=POST_CLOSE_FINAL_TOP_N,
        )
        csv_path = write_scan_csv(
            csv_rows,
            out_dir=out_dir,
            run_label=run_label,
            extra_field_specs=[*POST_CLOSE_LATEST_SESSION_FIELD_SPECS, *POST_CLOSE_FINAL_ENTRY_FIELD_SPECS],
        )
        rows_path = write_scan_rows_json(merged_rows, out_dir=out_dir, run_label=run_label)

        detected_turn_rows = select_us_session_turn_rows(csv_rows, run_at_kst=run_at_kst, scan_mode=scan_mode)
        turn_rows = filter_turn_rows_for_telegram(detected_turn_rows, min_volume_ratio_20_exclusive=1.0)
        pullback_rows = select_pullback_reentry_rows_for_telegram(csv_rows, min_volume_ratio_20_exclusive=1.0)
        hull_bear_rows = select_us_session_hull_bear_rows(csv_rows, run_at_kst=run_at_kst, scan_mode=scan_mode)
        high_52w_rows = select_us_session_52w_high_rows(csv_rows, run_at_kst=run_at_kst, scan_mode=scan_mode)
        pullback_filter_rows = select_post_close_pullback_rows_for_telegram(csv_rows)
        chase_filter_rows = select_post_close_chase_rows_for_telegram(csv_rows)
        buy_turn_filter_rows = select_post_close_buy_turn_rows_for_telegram(csv_rows, run_at_kst=run_at_kst, scan_mode=scan_mode)
        gap_setup_rows = select_post_close_gap_setup_rows_for_telegram(csv_rows)
        pocket_pivot_rows = select_post_close_pocket_pivot_rows_for_telegram(csv_rows)
        five_day_top_rows = select_post_close_top_5d_rows_for_telegram(csv_rows)
        final_top_rows = select_post_close_final_top_rows_for_telegram(csv_rows, top_n=POST_CLOSE_FINAL_TOP_N)
        summary_text = build_post_close_transition_summary(
            turn_rows,
            run_at_kst=run_at_kst,
            universe_count=int(_safe_float(merged_payload.get("universe_count", 0))),
            result_count=len(merged_rows),
            skip_count=int(_safe_float(merged_payload.get("skip_count_sum", 0))),
            scan_label=scan_label,
            detected_turn_count=len(detected_turn_rows),
            summary_limit=int(args.summary_limit),
            pullback_rows=pullback_rows,
            hull_bear_rows=hull_bear_rows,
            high_52w_rows=high_52w_rows,
            pullback_filter_rows=pullback_filter_rows,
            chase_filter_rows=chase_filter_rows,
            buy_turn_filter_rows=buy_turn_filter_rows,
            gap_setup_rows=gap_setup_rows,
            pocket_pivot_rows=pocket_pivot_rows,
            five_day_top_rows=five_day_top_rows,
            final_top_rows=final_top_rows,
        )
        summary_path = out_dir / f"trend_turn_summary_{run_label}.txt"
        summary_path.write_text(summary_text, encoding="utf-8")
        merge_ready = bool(merged_payload.get("merge_ready", False))
        merge_block_reason = str(merged_payload.get("merge_block_reason") or "").strip()
        missing_shard_indices = [int(_safe_float(v)) for v in (merged_payload.get("missing_shard_indices") or [])]
        meta_payload = {
            "run_at_kst": run_at_kst.isoformat(),
            "run_stamp": run_stamp,
            "mode": "merge",
            "scan_mode": scan_mode,
            "universe_profile": universe_profile,
            "merged_payload": merged_payload,
            "merge_ready": merge_ready,
            "merge_block_reason": merge_block_reason,
            "expected_shard_count": int(_safe_float(merged_payload.get("expected_shard_count", 0))),
            "found_shard_count": int(_safe_float(merged_payload.get("found_shard_count", 0))),
            "missing_shard_indices": missing_shard_indices,
            "result_count": len(merged_rows),
            "detected_turn_count": len(detected_turn_rows),
            "trend_turn_count": len(turn_rows),
            "pullback_reentry_count": len(pullback_rows),
            "hull_bear_count": len(hull_bear_rows),
            "new_52w_high_count": len(high_52w_rows),
            "pullback_filter_count": len(pullback_filter_rows),
            "chase_filter_count": len(chase_filter_rows),
            "buy_turn_filter_count": len(buy_turn_filter_rows),
            "gap_setup_count": len(gap_setup_rows),
            "pocket_pivot_count": len(pocket_pivot_rows),
            "five_day_top_count": len(five_day_top_rows),
            "final_top_count": len(final_top_rows),
            "csv_path": str(csv_path),
            "rows_path": str(rows_path),
            "summary_path": str(summary_path),
        }
        if not merge_ready:
            telegram_skipped_reason = merge_block_reason or "incomplete_shards"
            meta_payload["telegram_skipped_reason"] = telegram_skipped_reason

        write_json(meta_payload, out_dir=out_dir, filename=f"run_meta_{run_label}.json")
        print(f"[MERGE] CSV saved: {csv_path}")
        print(f"[MERGE] Summary saved: {summary_path}")
        if not merge_ready:
            print(f"[MERGE] Blocked: {telegram_skipped_reason} missing={missing_shard_indices}")
            return 1
    else:
        run_label = f"{run_stamp}_shard{shard_index}of{shard_count}"
        print("[SCAN] Building universe...")
        universe_payload = build_scan_universe(universe_profile=universe_profile)
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

        csv_rows = _with_latest_session_buy_turn_flags(scan_result.rows, target_date=latest_session_date)
        csv_rows = _with_post_close_cross_section_metrics(csv_rows, enabled=shard_count <= 1)
        csv_rows = _with_post_close_setup_scores(csv_rows)
        csv_rows = _with_post_close_final_top20_scores(
            csv_rows,
            run_at_kst=run_at_kst,
            scan_mode=scan_mode,
            top_n=POST_CLOSE_FINAL_TOP_N,
        )
        csv_path = write_scan_csv(
            csv_rows,
            out_dir=out_dir,
            run_label=run_label,
            extra_field_specs=[*POST_CLOSE_LATEST_SESSION_FIELD_SPECS, *POST_CLOSE_FINAL_ENTRY_FIELD_SPECS],
        )
        rows_path = write_scan_rows_json(scan_result.rows, out_dir=out_dir, run_label=run_label)
        detected_turn_rows = select_us_session_turn_rows(csv_rows, run_at_kst=run_at_kst, scan_mode=scan_mode)
        turn_rows = filter_turn_rows_for_telegram(detected_turn_rows, min_volume_ratio_20_exclusive=1.0)
        pullback_rows = select_pullback_reentry_rows_for_telegram(csv_rows, min_volume_ratio_20_exclusive=1.0)
        hull_bear_rows = select_us_session_hull_bear_rows(csv_rows, run_at_kst=run_at_kst, scan_mode=scan_mode)
        high_52w_rows = select_us_session_52w_high_rows(csv_rows, run_at_kst=run_at_kst, scan_mode=scan_mode)
        pullback_filter_rows = select_post_close_pullback_rows_for_telegram(csv_rows)
        chase_filter_rows = select_post_close_chase_rows_for_telegram(csv_rows)
        buy_turn_filter_rows = select_post_close_buy_turn_rows_for_telegram(csv_rows, run_at_kst=run_at_kst, scan_mode=scan_mode)
        gap_setup_rows = select_post_close_gap_setup_rows_for_telegram(csv_rows)
        pocket_pivot_rows = select_post_close_pocket_pivot_rows_for_telegram(csv_rows)
        five_day_top_rows = select_post_close_top_5d_rows_for_telegram(csv_rows)
        final_top_rows = select_post_close_final_top_rows_for_telegram(csv_rows, top_n=POST_CLOSE_FINAL_TOP_N)
        summary_text = build_post_close_transition_summary(
            turn_rows,
            run_at_kst=run_at_kst,
            universe_count=len(tickers),
            result_count=len(scan_result.rows),
            skip_count=len(scan_result.skips),
            scan_label=scan_label,
            detected_turn_count=len(detected_turn_rows),
            summary_limit=int(args.summary_limit),
            pullback_rows=pullback_rows,
            hull_bear_rows=hull_bear_rows,
            high_52w_rows=high_52w_rows,
            pullback_filter_rows=pullback_filter_rows,
            chase_filter_rows=chase_filter_rows,
            buy_turn_filter_rows=buy_turn_filter_rows,
            gap_setup_rows=gap_setup_rows,
            pocket_pivot_rows=pocket_pivot_rows,
            five_day_top_rows=five_day_top_rows,
            final_top_rows=final_top_rows,
        )
        summary_path = out_dir / f"trend_turn_summary_{run_label}.txt"
        summary_path.write_text(summary_text, encoding="utf-8")
        if shard_count > 1:
            telegram_skipped_reason = "requires_merge_for_ranked_post_close_summary"

        meta_payload = {
            "run_at_kst": run_at_kst.isoformat(),
            "run_stamp": run_stamp,
            "mode": "scan",
            "scan_mode": scan_mode,
            "universe_profile": universe_profile,
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
            "pullback_reentry_count": len(pullback_rows),
            "hull_bear_count": len(hull_bear_rows),
            "new_52w_high_count": len(high_52w_rows),
            "pullback_filter_count": len(pullback_filter_rows),
            "chase_filter_count": len(chase_filter_rows),
            "buy_turn_filter_count": len(buy_turn_filter_rows),
            "gap_setup_count": len(gap_setup_rows),
            "pocket_pivot_count": len(pocket_pivot_rows),
            "five_day_top_count": len(five_day_top_rows),
            "final_top_count": len(final_top_rows),
            "csv_path": str(csv_path),
            "rows_path": str(rows_path),
            "summary_path": str(summary_path),
        }
        if telegram_skipped_reason:
            meta_payload["telegram_skipped_reason"] = telegram_skipped_reason
        write_json(
            meta_payload,
            out_dir=out_dir,
            filename=f"run_meta_{run_label}.json",
        )

        print(f"[SCAN] CSV saved: {csv_path}")
        print(f"[SCAN] Summary saved: {summary_path}")

    if telegram_skipped_reason:
        print(f"[SCAN] Telegram send skipped: {telegram_skipped_reason}")
    else:
        _send_telegram_if_enabled(args, summary_text=summary_text, csv_path=csv_path, scan_label=scan_label, run_at_kst=run_at_kst)
    return 0


def _run_pre_market(args: argparse.Namespace, *, run_at_kst: datetime, out_dir: Path) -> int:
    """21시 프리마켓 모드: 05시 결과 로드 + 프리마켓 갭 수집."""
    stamp = run_at_kst.strftime("%Y%m%d_%H%M%S")
    shard_count = int(args.shard_count or 1)
    shard_index = int(args.shard_index or 0)
    merge_dir_arg = str(args.merge_dir or "").strip()
    merge_dir = Path(merge_dir_arg).expanduser().resolve() if merge_dir_arg else None
    universe_profile = _normalize_universe_profile(args.universe_profile)
    scan_mode = "pre_market"
    scan_label = _scan_label_for_mode(scan_mode, universe_profile)
    prev_scan_dir = str(args.prev_scan_dir or args.out_dir or "").strip()

    if merge_dir:
        run_label = f"{stamp}_pre_market_merged"
        print(f"[PRE_MARKET:MERGE] Loading shard artifacts from {merge_dir}")
        merged_payload = merge_shard_scan_rows(merge_dir)
        merged_rows = list(merged_payload.get("rows") or [])
        print(f"[PRE_MARKET:MERGE] Completed: merged={len(merged_rows)}")

        csv_path = write_scan_csv(merged_rows, out_dir=out_dir, run_label=run_label)
        rows_path = write_scan_rows_json(merged_rows, out_dir=out_dir, run_label=run_label)

        detected_turn_rows = select_us_session_turn_rows(merged_rows, run_at_kst=run_at_kst, scan_mode=scan_mode)
        turn_rows = filter_turn_rows_for_telegram(detected_turn_rows, min_volume_ratio_20_exclusive=1.0)
        pullback_rows = select_pullback_reentry_rows_for_telegram(merged_rows, min_volume_ratio_20_exclusive=1.0)
        hull_bear_rows = select_us_session_hull_bear_rows(merged_rows, run_at_kst=run_at_kst, scan_mode=scan_mode)
        high_52w_rows = select_us_session_52w_high_rows(merged_rows, run_at_kst=run_at_kst, scan_mode=scan_mode)
        summary_text = build_transition_summary(
            turn_rows,
            run_at_kst=run_at_kst,
            universe_count=int(_safe_float(merged_payload.get("universe_count", 0))),
            result_count=len(merged_rows),
            skip_count=int(_safe_float(merged_payload.get("skip_count_sum", 0))),
            scan_label=scan_label,
            detected_turn_count=len(detected_turn_rows),
            summary_limit=int(args.summary_limit),
            pullback_rows=pullback_rows,
            hull_bear_rows=hull_bear_rows,
            high_52w_rows=high_52w_rows,
            scan_mode=scan_mode,
        )
        priority_modes = {str(mode or "").strip().lower() for mode in (merged_payload.get("priority_modes") or [])}
        if "empty_fallback" in priority_modes:
            summary_text = _prepend_summary_warning(
                summary_text,
                "※ 안내: 전일 daily-scan 결과 부재로 priority 비활성(전체 유니버스 fallback) 샤드가 포함되었습니다.",
            )
        summary_path = out_dir / f"trend_turn_summary_{run_label}.txt"
        summary_path.write_text(summary_text, encoding="utf-8")

        write_json(
            {
                "run_at_kst": run_at_kst.isoformat(),
                "mode": "merge",
                "scan_mode": scan_mode,
                "universe_profile": universe_profile,
                "merged_payload": merged_payload,
                "result_count": len(merged_rows),
                "detected_turn_count": len(detected_turn_rows),
                "csv_path": str(csv_path),
                "rows_path": str(rows_path),
                "summary_path": str(summary_path),
            },
            out_dir=out_dir,
            filename=f"run_meta_{run_label}.json",
        )
        print(f"[PRE_MARKET:MERGE] CSV saved: {csv_path}")
        print(f"[PRE_MARKET:MERGE] Summary saved: {summary_path}")

        _send_telegram_if_enabled(args, summary_text=summary_text, csv_path=csv_path, scan_label=scan_label, run_at_kst=run_at_kst)
    else:
        run_label = f"{stamp}_pre_market_shard{shard_index}of{shard_count}"
        # 1) 이전 post_close 결과 로드
        prev_rows, prev_path = _load_latest_scan_rows(Path(prev_scan_dir))
        prev_scan_found = bool(prev_rows)
        priority_mode = "from_prev_scan"
        fallback_reason = ""
        if prev_scan_found:
            print(f"[PRE_MARKET] Loaded {len(prev_rows)} rows from {prev_path}")
        else:
            priority_mode = "empty_fallback"
            fallback_reason = "missing_prev_scan_artifact"
            print(
                f"[PRE_MARKET] No previous scan results found in {prev_scan_dir}. "
                "Falling back to full universe scan without priority."
            )

        # 2) Shard 遺꾨━
        if prev_scan_found:
            all_tickers = [str(r.get("ticker", "")).strip().upper() for r in prev_rows if r.get("ticker")]
            shard_tickers = split_tickers_for_shard(all_tickers, shard_count, shard_index)
            shard_ticker_set = set(shard_tickers)
            shard_rows = [r for r in prev_rows if str(r.get("ticker", "")).strip().upper() in shard_ticker_set]
        else:
            universe_payload = build_scan_universe(universe_profile=universe_profile)
            all_tickers = list(universe_payload.get("tickers") or [])
            shard_tickers = split_tickers_for_shard(all_tickers, shard_count, shard_index)
            shard_rows = _build_premarket_fallback_rows(shard_tickers)
        print(f"[PRE_MARKET] Shard {shard_index}/{shard_count - 1}: {len(shard_tickers)} tickers for gap collection")

        # 3) 프리마켓 갭 수집
        gap_data = _fetch_premarket_gaps(shard_tickers, max_workers=int(args.max_workers))
        print(f"[PRE_MARKET] Gap data collected: {len(gap_data)}/{len(shard_tickers)}")

        # 4) shard 티커만 필터 + 갭 병합
        enriched_rows = _enrich_rows_with_gap(shard_rows, gap_data)

        # 5) 저장
        write_scan_rows_json(enriched_rows, out_dir=out_dir, run_label=run_label)
        write_json(
            {
                "run_at_kst": run_at_kst.isoformat(),
                "mode": "pre_market",
                "scan_mode": scan_mode,
                "universe_profile": universe_profile,
                "shard_count": shard_count,
                "shard_index": shard_index,
                "full_universe_count": len(all_tickers),
                "shard_ticker_count": len(shard_tickers),
                "gap_collected_count": len(gap_data),
                "result_count": len(enriched_rows),
                "priority_mode": priority_mode,
                "prev_scan_found": prev_scan_found,
                "prev_scan_path": str(prev_path) if prev_path else "",
                "fallback_reason": fallback_reason,
                "performance": {"skip_count": len(shard_tickers) - len(gap_data)},
            },
            out_dir=out_dir,
            filename=f"run_meta_{run_label}.json",
        )
        print(f"[PRE_MARKET] Shard results saved: {len(enriched_rows)} rows")

    return 0


def _run_early_session(args: argparse.Namespace, *, run_at_kst: datetime, out_dir: Path) -> int:
    """23시 얼리세션 모드: period=1y 풀스캔 + 시간비례 거래량 보정."""
    explicit_run_stamp = str(getattr(args, "run_stamp", "") or "").strip()
    run_stamp = explicit_run_stamp or _resolve_cli_run_stamp(args, run_at_kst=run_at_kst)
    run_stamp_key = f"{run_stamp}_early_session"
    shard_count = int(args.shard_count or 1)
    shard_index = int(args.shard_index or 0)
    merge_dir_arg = str(args.merge_dir or "").strip()
    merge_dir = Path(merge_dir_arg).expanduser().resolve() if merge_dir_arg else None
    universe_profile = _normalize_universe_profile(args.universe_profile)
    scan_mode = "early_session"
    scan_label = _scan_label_for_mode(scan_mode, universe_profile)
    history_period = _history_period_for_mode(scan_mode)
    vol_threshold = _time_adjusted_volume_threshold(run_at_kst, base_threshold=0.5)
    print(f"[EARLY_SESSION] Volume threshold: {vol_threshold:.3f}x (time-adjusted), period={history_period}")

    if merge_dir:
        print(f"[EARLY_SESSION:MERGE] Loading shard artifacts from {merge_dir}")
        merged_payload = merge_shard_scan_rows(
            merge_dir,
            required_run_stamp=(f"{explicit_run_stamp}_early_session" if explicit_run_stamp else None),
        )
        selected_run_stamp_key = str(merged_payload.get("run_stamp") or run_stamp_key)
        run_label = f"{selected_run_stamp_key}_merged"
        merged_rows = list(merged_payload.get("rows") or [])
        profile_candidates = list(merged_payload.get("universe_profiles") or [])
        if universe_profile == "default" and len(profile_candidates) == 1:
            universe_profile = _normalize_universe_profile(profile_candidates[0])
            scan_label = _scan_label_for_mode(scan_mode, universe_profile)
        print(
            f"[EARLY_SESSION:MERGE] Completed: merged={len(merged_rows)} "
            f"source_rows={int(merged_payload.get('source_row_count', 0))}"
        )
        csv_path = write_scan_csv(merged_rows, out_dir=out_dir, run_label=run_label)
        rows_path = write_scan_rows_json(merged_rows, out_dir=out_dir, run_label=run_label)

        detected_turn_rows = select_us_session_turn_rows(merged_rows, run_at_kst=run_at_kst, scan_mode=scan_mode)
        pullback_detected_raw_count = count_pullback_reentry_detected_rows(merged_rows)
        turn_rows = filter_turn_rows_for_telegram(detected_turn_rows, min_volume_ratio_20_exclusive=vol_threshold)
        pullback_rows = select_pullback_reentry_rows_for_telegram(merged_rows, min_volume_ratio_20_exclusive=vol_threshold)
        hull_bear_rows = select_us_session_hull_bear_rows(merged_rows, run_at_kst=run_at_kst, scan_mode=scan_mode)
        high_52w_rows = select_us_session_52w_high_rows(merged_rows, run_at_kst=run_at_kst, scan_mode=scan_mode)
        summary_text = build_transition_summary(
            turn_rows,
            run_at_kst=run_at_kst,
            universe_count=int(_safe_float(merged_payload.get("universe_count", 0))),
            result_count=len(merged_rows),
            skip_count=int(_safe_float(merged_payload.get("skip_count_sum", 0))),
            scan_label=scan_label,
            detected_turn_count=len(detected_turn_rows),
            summary_limit=int(args.summary_limit),
            pullback_rows=pullback_rows,
            hull_bear_rows=hull_bear_rows,
            high_52w_rows=high_52w_rows,
            scan_mode=scan_mode,
            volume_threshold=vol_threshold,
        )
        summary_path = out_dir / f"trend_turn_summary_{run_label}.txt"
        summary_path.write_text(summary_text, encoding="utf-8")

        merge_ready = bool(merged_payload.get("merge_ready", False))
        merge_block_reason = str(merged_payload.get("merge_block_reason") or "").strip()
        missing_shard_indices = [int(_safe_float(v)) for v in (merged_payload.get("missing_shard_indices") or [])]
        meta_payload = {
            "run_at_kst": run_at_kst.isoformat(),
            "run_stamp": run_stamp,
            "run_stamp_key": selected_run_stamp_key,
            "mode": "merge",
            "scan_mode": scan_mode,
            "universe_profile": universe_profile,
            "volume_threshold": vol_threshold,
            "history_period": history_period,
            "merged_payload": merged_payload,
            "merge_ready": merge_ready,
            "merge_block_reason": merge_block_reason,
            "expected_shard_count": int(_safe_float(merged_payload.get("expected_shard_count", 0))),
            "found_shard_count": int(_safe_float(merged_payload.get("found_shard_count", 0))),
            "missing_shard_indices": missing_shard_indices,
            "result_count": len(merged_rows),
            "detected_turn_count": len(detected_turn_rows),
            "trend_turn_count": len(turn_rows),
            "pullback_detected_raw_count": pullback_detected_raw_count,
            "pullback_reentry_count": len(pullback_rows),
            "hull_bear_count": len(hull_bear_rows),
            "new_52w_high_count": len(high_52w_rows),
            "csv_path": str(csv_path),
            "rows_path": str(rows_path),
            "summary_path": str(summary_path),
        }
        if not merge_ready:
            telegram_skipped_reason = merge_block_reason or "incomplete_shards"
            meta_payload["telegram_skipped_reason"] = telegram_skipped_reason

        write_json(meta_payload, out_dir=out_dir, filename=f"run_meta_{run_label}.json")
        print(f"[EARLY_SESSION:MERGE] CSV saved: {csv_path}")
        print(f"[EARLY_SESSION:MERGE] Summary saved: {summary_path}")
        if not merge_ready:
            print(f"[EARLY_SESSION:MERGE] Blocked: {telegram_skipped_reason} missing={missing_shard_indices}")
            return 1

        _send_telegram_if_enabled(args, summary_text=summary_text, csv_path=csv_path, scan_label=scan_label, run_at_kst=run_at_kst)
    else:
        run_label = f"{run_stamp_key}_shard{shard_index}of{shard_count}"
        print("[EARLY_SESSION] Building universe...")
        universe_payload = build_scan_universe(universe_profile=universe_profile)
        full_tickers = list(universe_payload.get("tickers") or [])
        tickers = split_tickers_for_shard(full_tickers, shard_count, shard_index)
        print(
            f"[EARLY_SESSION] Universe ready: full={len(full_tickers)} shard={len(tickers)} "
            f"(shard={shard_index}/{shard_count - 1})"
        )
        if universe_payload.get("etf_errors"):
            print("[EARLY_SESSION] ETF resolve errors:", " | ".join(universe_payload["etf_errors"]))

        scan_result = scan_universe(
            tickers, max_workers=int(args.max_workers), bias_mode=str(args.bias_mode), history_period=history_period,
        )
        print(
            f"[EARLY_SESSION] Completed: results={len(scan_result.rows)} "
            f"skips={len(scan_result.skips)} total_sec={_safe_float(scan_result.perf.get('total_seconds', 0)):.1f}"
        )

        csv_path = write_scan_csv(scan_result.rows, out_dir=out_dir, run_label=run_label)
        rows_path = write_scan_rows_json(scan_result.rows, out_dir=out_dir, run_label=run_label)
        detected_turn_rows = select_us_session_turn_rows(scan_result.rows, run_at_kst=run_at_kst, scan_mode=scan_mode)
        pullback_detected_raw_count = count_pullback_reentry_detected_rows(scan_result.rows)
        turn_rows = filter_turn_rows_for_telegram(detected_turn_rows, min_volume_ratio_20_exclusive=vol_threshold)
        pullback_rows = select_pullback_reentry_rows_for_telegram(scan_result.rows, min_volume_ratio_20_exclusive=vol_threshold)
        hull_bear_rows = select_us_session_hull_bear_rows(scan_result.rows, run_at_kst=run_at_kst, scan_mode=scan_mode)
        high_52w_rows = select_us_session_52w_high_rows(scan_result.rows, run_at_kst=run_at_kst, scan_mode=scan_mode)
        summary_text = build_transition_summary(
            turn_rows,
            run_at_kst=run_at_kst,
            universe_count=len(tickers),
            result_count=len(scan_result.rows),
            skip_count=len(scan_result.skips),
            scan_label=scan_label,
            detected_turn_count=len(detected_turn_rows),
            summary_limit=int(args.summary_limit),
            pullback_rows=pullback_rows,
            hull_bear_rows=hull_bear_rows,
            high_52w_rows=high_52w_rows,
            scan_mode=scan_mode,
            volume_threshold=vol_threshold,
        )
        summary_path = out_dir / f"trend_turn_summary_{run_label}.txt"
        summary_path.write_text(summary_text, encoding="utf-8")

        write_json(
            {
                "run_at_kst": run_at_kst.isoformat(),
                "run_stamp": run_stamp,
                "run_stamp_key": run_stamp_key,
                "mode": "scan",
                "scan_mode": scan_mode,
                "universe_profile": universe_profile,
                "volume_threshold": vol_threshold,
                "history_period": history_period,
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
                "pullback_detected_raw_count": pullback_detected_raw_count,
                "pullback_reentry_count": len(pullback_rows),
                "hull_bear_count": len(hull_bear_rows),
                "new_52w_high_count": len(high_52w_rows),
                "csv_path": str(csv_path),
                "rows_path": str(rows_path),
                "summary_path": str(summary_path),
            },
            out_dir=out_dir,
            filename=f"run_meta_{run_label}.json",
        )

        print(f"[EARLY_SESSION] CSV saved: {csv_path}")
        print(f"[EARLY_SESSION] Summary saved: {summary_path}")

    return 0


def main() -> int:
    args = parse_args()
    scan_mode = str(getattr(args, "scan_mode", "post_close") or "post_close")
    run_at_kst = datetime.now(KST)
    out_dir = Path(args.out_dir)

    shard_count = int(args.shard_count or 1)
    shard_index = int(args.shard_index or 0)
    if shard_count <= 0:
        raise RuntimeError("--shard-count must be > 0")
    if shard_index < 0 or shard_index >= shard_count:
        raise RuntimeError("--shard-index out of range")

    print(f"[MAIN] scan_mode={scan_mode}")

    if scan_mode == "pre_market":
        return _run_pre_market(args, run_at_kst=run_at_kst, out_dir=out_dir)
    elif scan_mode == "early_session":
        return _run_early_session(args, run_at_kst=run_at_kst, out_dir=out_dir)
    else:
        return _run_post_close(args, run_at_kst=run_at_kst, out_dir=out_dir)


if __name__ == "__main__":
    raise SystemExit(main())
