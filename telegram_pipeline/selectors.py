from __future__ import annotations

from datetime import date
from typing import Any, Iterable, Mapping

from .rankers import (
    buy_turn_sort_key,
    final_top_sort_key,
    five_day_top_sort_key,
    gap_setup_sort_key,
    hma_ema_long_sort_key,
    is_truthy,
    new_52w_high_sort_key,
    parse_iso_date,
    pocket_pivot_sort_key,
    pullback_sort_key,
    safe_float,
    same_session_buy_turn,
    same_session_sell_turn,
    sell_turn_sort_key,
    trend_sort_key,
)

FINAL_TOP_LIMIT = 20
FIVE_DAY_TOP_LIMIT = 30
HMA_EMA_TOP_LIMIT = 20
GAP_SETUP_MIN_SCORE = 8.0
GAP_SETUP_MIN_GATE_COUNT = 4.0
GAP_SETUP_MIN_SCAN_SCORE = 110.0
GAP_SETUP_MIN_DRY_UP_SCORE = 8.0
GAP_SETUP_MAX_VOLUME_RATIO_20 = 1.10

MANDATORY_SECTION_KEYS: tuple[str, ...] = (
    "final_top",
    "buy_turn",
    "pullback_reentry",
    "trend_continuation",
    "sell_turn",
)

CORE_SECTION_ORDER: tuple[str, ...] = (
    "final_top",
    "buy_turn",
    "pullback_reentry",
    "trend_continuation",
    "hma_ema_trend",
    "sell_turn",
    "gap_setup",
    "pocket_pivot",
    "five_day_top",
    "new_52w_high",
)

CORE_SECTION_TITLES: dict[str, str] = {
    "final_top": "오늘 최우선 후보",
    "buy_turn": "오늘 매수전환",
    "pullback_reentry": "눌림목 재진입",
    "trend_continuation": "추세 지속 / 추격 후보",
    "sell_turn": "오늘 매도전환",
    "gap_setup": "에너지 압축 → 돌파 임박",
    "pocket_pivot": "기관 매집 포착",
    "five_day_top": "5일 상승률 상위종목",
    "new_52w_high": "52주 신고가",
}

CORE_QUALITY_FLOORS: dict[str, str] = {
    "final_top": "final_entry eligible + same-session sell 없음 + multi_sell<2 + thin_trade_risk=N + conflict!=HIGH",
    "buy_turn": "당일 UTBot/HULL 매수전환",
    "pullback_reentry": "상승 구조 유지 + 적정 눌림 + 거래량 건조 + 최근 매도전환 없음",
    "trend_continuation": "상대강도/ADX/기울기 양호 + 거래량 동반 + 과열 제한 + 최근 매도전환 없음",
    "sell_turn": "당일 UTBot/HULL 매도전환",
    "gap_setup": "gap_setup_candidate=True + score/gate 강화 + 상승구조 + 건조거래량 + 하락전환없음",
    "pocket_pivot": "pocket_pivot_candidate=True",
    "five_day_top": "chg_5d > 0, Top 30",
    "new_52w_high": "new_52w_high=True + latest_bar_date == target session",
}

CORE_SECTION_TITLES["hma_ema_trend"] = "HMA/EMA 추세정렬 후보"
CORE_QUALITY_FLOORS["hma_ema_trend"] = (
    "long_entry/aligned + thin_trade_risk=N + bearish_gap_failure=N + "
    "vol>=0.9 + adx>=16 + risk_to_ema50<=10 + close>ema50"
)


def _base_rows(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [dict(row or {}) for row in (rows or [])]


def _dedupe_within_section(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique_rows: list[dict[str, Any]] = []
    for raw_row in rows or []:
        row = dict(raw_row or {})
        ticker = str(row.get("ticker") or "").strip().upper()
        if not ticker or ticker in seen:
            continue
        seen.add(ticker)
        unique_rows.append(row)
    return unique_rows


def _is_high_conflict(row: Mapping[str, Any]) -> bool:
    return str(row.get("strategy_conflict_level", "")).strip().upper() == "HIGH"


def _has_recent_sell_signal(row: Mapping[str, Any]) -> bool:
    return bool(is_truthy(row.get("utbot_sell_recent")) or is_truthy(row.get("hull_turn_bear_recent")))


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
    selected = _dedupe_within_section(selected)
    selected.sort(key=final_top_sort_key)
    return selected[:FINAL_TOP_LIMIT]


def select_buy_turn_rows(rows: Iterable[Mapping[str, Any]], *, target_date: date) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for row in _base_rows(rows):
        if not same_session_buy_turn(row, target_date):
            continue
        selected.append(row)
    selected = _dedupe_within_section(selected)
    selected.sort(key=lambda row: buy_turn_sort_key(row, target_date))
    return selected


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
    selected = _dedupe_within_section(selected)
    selected.sort(key=pullback_sort_key)
    return selected


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
    selected = _dedupe_within_section(selected)
    selected.sort(key=trend_sort_key)
    return selected


def select_hma_ema_trend_rows(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for row in _base_rows(rows):
        if is_truthy(row.get("thin_trade_risk")):
            continue
        if is_truthy(row.get("bearish_gap_failure")):
            continue
        if not (
            is_truthy(row.get("hma_ema_long_entry"))
            or is_truthy(row.get("hma_ema_long_aligned"))
        ):
            continue
        if safe_float(row.get("volume_ratio_20", 0.0)) < 0.9:
            continue
        if safe_float(row.get("adx", 0.0)) < 16.0:
            continue
        if safe_float(row.get("hma_ema_risk_to_ema50_pct", 999.0)) > 10.0:
            continue

        price_value = safe_float(row.get("price", row.get("close", 0.0)), 0.0)
        ema50_value = safe_float(row.get("ema50", row.get("EMA50", 0.0)), 0.0)
        if price_value <= ema50_value:
            continue

        selected.append(row)

    selected = _dedupe_within_section(selected)
    selected.sort(key=hma_ema_long_sort_key)
    return selected[:HMA_EMA_TOP_LIMIT]


def select_sell_turn_rows(rows: Iterable[Mapping[str, Any]], *, target_date: date) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for row in _base_rows(rows):
        if not same_session_sell_turn(row, target_date):
            continue
        selected.append(row)
    selected = _dedupe_within_section(selected)
    selected.sort(key=lambda row: sell_turn_sort_key(row, target_date))
    return selected


def select_gap_setup_rows(rows: Iterable[Mapping[str, Any]], *, target_date: date) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for row in _base_rows(rows):
        if not is_truthy(row.get("gap_setup_candidate")):
            continue
        if is_truthy(row.get("thin_trade_risk")):
            continue
        if is_truthy(row.get("bearish_gap_failure")):
            continue
        if same_session_sell_turn(row, target_date):
            continue
        if not is_truthy(row.get("uptrend_persistent")):
            continue
        if safe_float(row.get("gap_setup_score", 0.0)) < GAP_SETUP_MIN_SCORE:
            continue
        if safe_float(row.get("gap_setup_gate_count", 0.0)) < GAP_SETUP_MIN_GATE_COUNT:
            continue
        if safe_float(row.get("scan_score", 0.0)) < GAP_SETUP_MIN_SCAN_SCORE:
            continue
        dry_up_ok = safe_float(row.get("volume_dry_up_score", 0.0)) >= GAP_SETUP_MIN_DRY_UP_SCORE
        low_volume_ok = safe_float(row.get("volume_ratio_20", 0.0)) <= GAP_SETUP_MAX_VOLUME_RATIO_20
        if not (dry_up_ok or low_volume_ok):
            continue
        selected.append(row)
    selected = _dedupe_within_section(selected)
    selected.sort(key=gap_setup_sort_key)
    return selected


def select_pocket_pivot_rows(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    selected = [row for row in _base_rows(rows) if is_truthy(row.get("pocket_pivot_candidate"))]
    selected = _dedupe_within_section(selected)
    selected.sort(key=pocket_pivot_sort_key)
    return selected


def select_five_day_top_rows(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    selected = [row for row in _base_rows(rows) if safe_float(row.get("chg_5d", 0.0)) > 0.0]
    selected = _dedupe_within_section(selected)
    selected.sort(key=five_day_top_sort_key)
    return selected[:FIVE_DAY_TOP_LIMIT]


def select_new_52w_high_rows(rows: Iterable[Mapping[str, Any]], *, target_date: date) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for row in _base_rows(rows):
        if not is_truthy(row.get("new_52w_high")):
            continue
        if parse_iso_date(row.get("latest_bar_date")) != target_date:
            continue
        selected.append(row)
    selected = _dedupe_within_section(selected)
    selected.sort(key=new_52w_high_sort_key)
    return selected


def select_post_close_sections(rows: Iterable[Mapping[str, Any]], *, target_date: date) -> dict[str, list[dict[str, Any]]]:
    return {
        "final_top": select_final_top_rows(rows, target_date=target_date),
        "buy_turn": select_buy_turn_rows(rows, target_date=target_date),
        "pullback_reentry": select_pullback_reentry_rows(rows),
        "trend_continuation": select_trend_continuation_rows(rows),
        "hma_ema_trend": select_hma_ema_trend_rows(rows),
        "sell_turn": select_sell_turn_rows(rows, target_date=target_date),
        "gap_setup": select_gap_setup_rows(rows, target_date=target_date),
        "pocket_pivot": select_pocket_pivot_rows(rows),
        "five_day_top": select_five_day_top_rows(rows),
        "new_52w_high": select_new_52w_high_rows(rows, target_date=target_date),
    }
