from __future__ import annotations

from datetime import date
from typing import Any, Iterable, Mapping

from .rankers import (
    buy_turn_sort_key,
    buy_turn_signal_count,
    final_top_sort_key,
    is_truthy,
    same_session_buy_turn,
    same_session_sell_turn,
    sell_turn_sort_key,
    safe_float,
    trend_sort_key,
    pullback_sort_key,
)

CORE_SECTION_ORDER: tuple[str, ...] = (
    "final_top",
    "buy_turn",
    "pullback_reentry",
    "trend_continuation",
    "sell_turn",
)

CORE_SECTION_TITLES: dict[str, str] = {
    "final_top": "오늘 최우선 후보",
    "buy_turn": "오늘 매수전환",
    "pullback_reentry": "눌림목 재진입",
    "trend_continuation": "추세 지속 / 추격 후보",
    "sell_turn": "오늘 매도전환 / 주의",
}

CORE_QUALITY_FLOORS: dict[str, str] = {
    "final_top": "final_entry eligible + same-session sell 없음 + multi_sell<2 + thin_trade_risk=N + conflict!=HIGH",
    "buy_turn": "당일/최근 매수전환 + CMF/OBV 양호 + 거래량 기준 통과 + 당일 매도전환 없음",
    "pullback_reentry": "상승 구조 유지 + 적정 눌림 + 거래량 건조 + 최근 매도전환 없음",
    "trend_continuation": "상대강도/ADX/기울기 양호 + 거래량 동반 + 과열 제한 + 최근 매도전환 없음",
    "sell_turn": "당일/최근 매도전환 or multi_sell>=2 or thin_trade_risk or bearish_gap_failure",
}

DEDUPE_PRIORITY: tuple[str, ...] = (
    "sell_turn",
    "buy_turn",
    "pullback_reentry",
    "trend_continuation",
)

SUMMARY_TOP_N = 5
DETAIL_TOP_N = 20
PRE_DEDUPE_LIMIT = 60


def _base_rows(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [dict(row or {}) for row in (rows or [])]


def _is_high_conflict(row: Mapping[str, Any]) -> bool:
    return str(row.get("strategy_conflict_level", "")).strip().upper() == "HIGH"


def _has_recent_sell_signal(row: Mapping[str, Any]) -> bool:
    return bool(is_truthy(row.get("utbot_sell_recent")) or is_truthy(row.get("hull_turn_bear_recent")))


def _has_recent_buy_signal(row: Mapping[str, Any]) -> bool:
    return bool(
        is_truthy(row.get("utbot_buy_recent"))
        or is_truthy(row.get("hull_turn_bull_recent"))
        or is_truthy(row.get("bull_turn_recent"))
    )


def select_final_top_rows(rows: Iterable[Mapping[str, Any]], *, target_date: date) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for row in _base_rows(rows):
        if not (is_truthy(row.get("final_entry_eligible")) or is_truthy(row.get("final_entry_selected"))):
            continue
        if same_session_sell_turn(row, target_date):
            continue
        if safe_float(row.get("multi_sell", 0.0)) >= 2.0:
            continue
        if is_truthy(row.get("thin_trade_risk")):
            continue
        if is_truthy(row.get("bearish_gap_failure")):
            continue
        if _is_high_conflict(row):
            continue
        selected.append(row)
    selected.sort(key=final_top_sort_key)
    return selected[:PRE_DEDUPE_LIMIT]


def select_buy_turn_rows(rows: Iterable[Mapping[str, Any]], *, target_date: date) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for row in _base_rows(rows):
        if is_truthy(row.get("thin_trade_risk")):
            continue
        if same_session_sell_turn(row, target_date):
            continue
        if not (same_session_buy_turn(row, target_date) or safe_float(row.get("days_since_utbot_buy", 99.0)) <= 2.0 or safe_float(row.get("days_since_hull_turn_bull", 99.0)) <= 2.0):
            continue
        if not _has_recent_buy_signal(row):
            continue
        if buy_turn_signal_count(row) <= 0:
            continue
        if safe_float(row.get("cmf", 0.0)) <= -0.10:
            continue
        if safe_float(row.get("obv_slope", 0.0)) <= 0.0:
            continue
        if safe_float(row.get("volume_ratio_20", 0.0)) <= 0.90:
            continue
        selected.append(row)
    selected.sort(key=lambda row: buy_turn_sort_key(row, target_date))
    return selected[:PRE_DEDUPE_LIMIT]


def select_pullback_reentry_rows(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for row in _base_rows(rows):
        if is_truthy(row.get("thin_trade_risk")):
            continue
        if not is_truthy(row.get("uptrend_persistent")):
            continue
        if safe_float(row.get("hma60_slope_pct", 0.0)) <= 0.0:
            continue
        if safe_float(row.get("pullback_from_swing_high_pct", 0.0)) >= -2.0:
            continue
        if safe_float(row.get("drawdown_from_20d_high_pct", 0.0)) >= -1.0:
            continue
        if safe_float(row.get("pullback_atr_multiple", 0.0)) > 3.5:
            continue
        if not (is_truthy(row.get("pullback_ready")) or is_truthy(row.get("pullback_reentry"))):
            continue
        if safe_float(row.get("volume_dry_up_score", 0.0)) < 1.0:
            continue
        if _has_recent_sell_signal(row):
            continue
        selected.append(row)
    selected.sort(key=pullback_sort_key)
    return selected[:PRE_DEDUPE_LIMIT]


def select_trend_continuation_rows(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for row in _base_rows(rows):
        if is_truthy(row.get("thin_trade_risk")):
            continue
        if not is_truthy(row.get("bull_strength_recent")):
            continue
        if not is_truthy(row.get("uptrend_persistent")):
            continue
        if safe_float(row.get("hma20_slope_pct", 0.0)) <= 0.0 or safe_float(row.get("hma60_slope_pct", 0.0)) <= 0.0:
            continue
        if not is_truthy(row.get("volume_bullish")):
            continue
        if safe_float(row.get("adx", 0.0)) < 18.0:
            continue
        if safe_float(row.get("rs_rank_vs_index", 0.0)) < 55.0:
            continue
        if safe_float(row.get("multi_buy", 0.0)) < 2.0:
            continue
        if safe_float(row.get("dist_sma20_pct", 0.0)) >= 30.0:
            continue
        if safe_float(row.get("zscore20", 0.0)) >= 3.5:
            continue
        if safe_float(row.get("scan_score", 0.0)) < 120.0:
            continue
        if _has_recent_sell_signal(row):
            continue
        selected.append(row)
    selected.sort(key=trend_sort_key)
    return selected[:PRE_DEDUPE_LIMIT]


def select_sell_turn_rows(rows: Iterable[Mapping[str, Any]], *, target_date: date) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for row in _base_rows(rows):
        severe_drawdown = safe_float(row.get("drawdown_from_20d_high_pct", 0.0)) <= -6.0
        has_signal = bool(
            same_session_sell_turn(row, target_date)
            or is_truthy(row.get("utbot_sell_recent"))
            or is_truthy(row.get("hull_turn_bear_recent"))
            or safe_float(row.get("multi_sell", 0.0)) >= 2.0
            or severe_drawdown
            or is_truthy(row.get("thin_trade_risk"))
            or is_truthy(row.get("bearish_gap_failure"))
        )
        if not has_signal:
            continue
        if safe_float(row.get("volume_ratio_20", 0.0)) <= 0.50 and not is_truthy(row.get("thin_trade_risk")):
            continue
        selected.append(row)
    selected.sort(key=lambda row: sell_turn_sort_key(row, target_date))
    return selected[:PRE_DEDUPE_LIMIT]


def select_post_close_sections(rows: Iterable[Mapping[str, Any]], *, target_date: date) -> dict[str, list[dict[str, Any]]]:
    return {
        "final_top": select_final_top_rows(rows, target_date=target_date),
        "buy_turn": select_buy_turn_rows(rows, target_date=target_date),
        "pullback_reentry": select_pullback_reentry_rows(rows),
        "trend_continuation": select_trend_continuation_rows(rows),
        "sell_turn": select_sell_turn_rows(rows, target_date=target_date),
    }
