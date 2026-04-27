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
BOARD_SECTION_LIMIT = 10
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

BOARD_SECTION_ORDER: tuple[str, ...] = (
    "confluence",
    "entry_now",
    "pullback_reentry",
    "steady_uptrend",
    "breakout_wait",
    "accumulation",
    "rs_leader",
    "chase_risk",
    "sell_risk",
)

BOARD_SECTION_TITLES: dict[str, str] = {
    "confluence": "고확률 컨플루언스 후보",
    "entry_now": "지금 진입형 후보",
    "pullback_reentry": "눌림목 / 재진입 후보",
    "steady_uptrend": "추세 지속 / 꾸준상승 후보",
    "breakout_wait": "돌파 대기 / 압축 후보",
    "accumulation": "수급 / 기관매집 후보",
    "rs_leader": "신고가 / 상대강도 리더 후보",
    "chase_risk": "단기 급등 / 추격주의 후보",
    "sell_risk": "매도전환 / 위험 후보",
}

BOARD_QUALITY_FLOORS: dict[str, str] = {
    "confluence": "membership_count>=3 또는 QBS 상위 + source 2개 이상",
    "entry_now": "매수전환 / MA20 재탈환 / HMA·EMA long entry / final top",
    "pullback_reentry": "상승추세 내 눌림목 또는 재진입",
    "steady_uptrend": "trend_continuation 또는 HMA/EMA 정렬 기반 추세 지속",
    "breakout_wait": "gap setup / 저변동 압축 / 신고가 직전",
    "accumulation": "pocket pivot / CMF / OBV / 거래량 매집",
    "rs_leader": "52주 신고가 / RS rank / 20D 수익률 리더",
    "chase_risk": "5일 급등 / 당일 급등 / 과열 이격",
    "sell_risk": "매도전환 / 갭 실패 / high conflict / hard risk",
}

BOARD_MANDATORY_SECTION_KEYS: tuple[str, ...] = BOARD_SECTION_ORDER

BOARD_LABELS: dict[str, str] = {
    "confluence": "CONFLUENCE",
    "entry_now": "ENTRY",
    "pullback_reentry": "PULLBACK",
    "steady_uptrend": "STEADY",
    "breakout_wait": "BREAKOUT_WAIT",
    "accumulation": "ACCUMULATION",
    "rs_leader": "RS_LEADER",
    "chase_risk": "CHASE_RISK",
    "sell_risk": "SELL_RISK",
}

SOURCE_TAGS: dict[str, str] = {
    "final_top": "final",
    "buy_turn": "buy_turn",
    "pullback_reentry": "pullback",
    "trend_continuation": "trend",
    "hma_ema_trend": "HMA",
    "sell_turn": "sell_turn",
    "gap_setup": "gap",
    "pocket_pivot": "pocket",
    "five_day_top": "5D",
    "new_52w_high": "52W",
}


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


def _ticker(row: Mapping[str, Any]) -> str:
    return str(row.get("ticker") or "").strip().upper()


def _unique_append(items: list[str], value: str) -> None:
    text = str(value or "").strip()
    if text and text not in items:
        items.append(text)


def _source_membership(
    section_rows: Mapping[str, Iterable[Mapping[str, Any]]],
) -> tuple[dict[str, set[str]], dict[str, dict[str, dict[str, Any]]]]:
    membership: dict[str, set[str]] = {}
    rows_by_section: dict[str, dict[str, dict[str, Any]]] = {}

    for section_key in CORE_SECTION_ORDER:
        section_map: dict[str, dict[str, Any]] = {}
        for raw_row in section_rows.get(section_key) or []:
            row = dict(raw_row or {})
            ticker = _ticker(row)
            if not ticker or ticker in section_map:
                continue
            section_map[ticker] = row
            membership.setdefault(ticker, set()).add(section_key)
        rows_by_section[section_key] = section_map

    return membership, rows_by_section


def _canonical_source_row(ticker: str, rows_by_section: Mapping[str, Mapping[str, Mapping[str, Any]]]) -> dict[str, Any]:
    priority = (
        "sell_turn",
        "final_top",
        "buy_turn",
        "pullback_reentry",
        "trend_continuation",
        "hma_ema_trend",
        "gap_setup",
        "pocket_pivot",
        "new_52w_high",
        "five_day_top",
    )
    for section_key in priority:
        row = dict(rows_by_section.get(section_key, {}).get(ticker) or {})
        if row:
            return row
    return {"ticker": ticker}


def _is_ma20_reclaim(row: Mapping[str, Any]) -> bool:
    return is_truthy(row.get("first_close_above_ma20_after_5bars"))


def _is_compression(row: Mapping[str, Any]) -> bool:
    tight_pattern = (
        is_truthy(row.get("nr7_flag"))
        or is_truthy(row.get("inside_day_flag"))
        or is_truthy(row.get("three_weeks_tight"))
    )
    volatility_contracting = is_truthy(row.get("atr_contracting")) and 0.45 <= safe_float(row.get("bb_percent_b", 0.0)) <= 0.90
    volume_quiet = safe_float(row.get("volume_ratio_20", 0.0)) <= 1.10 or safe_float(row.get("volume_dry_up_score", 0.0)) >= 20.0
    return bool(tight_pattern or (volatility_contracting and volume_quiet))


def _is_pre_high(row: Mapping[str, Any]) -> bool:
    return bool(
        is_truthy(row.get("near_52w_high_2pct"))
        or safe_float(row.get("breakout_dist_20d_high_pct", -999.0)) >= -2.0
        or safe_float(row.get("drawdown_from_52w_high_pct", -999.0)) > -2.0
    )


def _is_rs_leader(row: Mapping[str, Any]) -> bool:
    return bool(
        safe_float(row.get("rs_rank_vs_index", 0.0)) >= 80.0
        or safe_float(row.get("ret20_percentile", 0.0)) >= 85.0
        or safe_float(row.get("ret60_percentile", 0.0)) >= 85.0
    )


def _is_accumulation(row: Mapping[str, Any], membership: set[str]) -> bool:
    if "pocket_pivot" in membership:
        return True
    return bool(
        safe_float(row.get("volume_ratio_20", 0.0)) >= 1.5
        and safe_float(row.get("cmf", 0.0)) > 0.05
        and safe_float(row.get("obv_slope", 0.0)) > 0.1
    )


def _is_chase_risk(row: Mapping[str, Any], membership: set[str]) -> bool:
    return bool(
        "five_day_top" in membership
        or safe_float(row.get("chg", 0.0)) >= 8.0
        or safe_float(row.get("chg_5d", 0.0)) >= 15.0
        or safe_float(row.get("dist_sma20_pct", 0.0)) >= 15.0
        or safe_float(row.get("zscore20", 0.0)) >= 2.5
    )


def _board_risk_flags(row: Mapping[str, Any], membership: set[str], target_date: date) -> list[str]:
    flags: list[str] = []
    if "sell_turn" in membership or same_session_sell_turn(row, target_date):
        _unique_append(flags, "sell_turn")
    if is_truthy(row.get("thin_trade_risk")):
        _unique_append(flags, "thin_trade")
    if is_truthy(row.get("bearish_gap_failure")):
        _unique_append(flags, "gap_failure")
    if _is_high_conflict(row):
        _unique_append(flags, "high_conflict")
    if safe_float(row.get("multi_sell", 0.0)) >= 2.0:
        _unique_append(flags, "multi_sell")
    if safe_float(row.get("chg", 0.0)) >= 12.0:
        _unique_append(flags, "extended_day")
    elif safe_float(row.get("chg_5d", 0.0)) >= 20.0 or safe_float(row.get("zscore20", 0.0)) >= 2.5:
        _unique_append(flags, "chase_risk")
    if safe_float(row.get("volume_ratio_20", 0.0)) < 0.8:
        _unique_append(flags, "low_volume")
    return flags


def _is_sell_risk(row: Mapping[str, Any], membership: set[str], target_date: date) -> bool:
    hard_flags = {"sell_turn", "thin_trade", "gap_failure", "high_conflict", "multi_sell"}
    return bool(hard_flags.intersection(_board_risk_flags(row, membership, target_date)))


def _board_tags(row: Mapping[str, Any], membership: set[str]) -> list[str]:
    tags: list[str] = []
    for section_key in CORE_SECTION_ORDER:
        if section_key in membership:
            _unique_append(tags, SOURCE_TAGS.get(section_key, section_key))
    if _is_ma20_reclaim(row):
        _unique_append(tags, "MA20_reclaim")
    if _is_compression(row):
        _unique_append(tags, "compression")
    if _is_pre_high(row):
        _unique_append(tags, "pre_high")
    if _is_rs_leader(row):
        _unique_append(tags, f"RS{int(safe_float(row.get('rs_rank_vs_index', 0.0))):d}")
    if safe_float(row.get("cmf", 0.0)) > 0.05:
        _unique_append(tags, "CMF+")
    if safe_float(row.get("obv_slope", 0.0)) > 0.1:
        _unique_append(tags, "OBV+")
    return tags


def _board_reason(tags: list[str]) -> str:
    return "+".join(tags[:6]) if tags else "-"


def _board_sort_key(section_key: str, row: Mapping[str, Any]) -> tuple[float, float, float, float, float, float, str]:
    if section_key == "sell_risk":
        return (
            -safe_float(row.get("same_session_sell_rank", 0.0)),
            -safe_float(row.get("multi_sell", 0.0)),
            -safe_float(row.get("volume_ratio_20", 0.0)),
            -abs(safe_float(row.get("chg", 0.0))),
            -safe_float(row.get("scan_score", 0.0)),
            -safe_float(row.get("membership_count", 0.0)),
            str(row.get("ticker", "")),
        )
    if section_key == "chase_risk":
        return (
            -safe_float(row.get("chg_5d", 0.0)),
            -safe_float(row.get("chg", 0.0)),
            -safe_float(row.get("dist_sma20_pct", 0.0)),
            -safe_float(row.get("scan_score", 0.0)),
            -safe_float(row.get("membership_count", 0.0)),
            -safe_float(row.get("volume_ratio_20", 0.0)),
            str(row.get("ticker", "")),
        )
    if section_key == "breakout_wait":
        return (
            -safe_float(row.get("gap_setup_score", 0.0)),
            -safe_float(row.get("gap_setup_gate_count", 0.0)),
            -safe_float(row.get("volume_dry_up_score", 0.0)),
            -safe_float(row.get("rs_rank_vs_index", 0.0)),
            -safe_float(row.get("scan_score", 0.0)),
            -safe_float(row.get("membership_count", 0.0)),
            str(row.get("ticker", "")),
        )
    return (
        -safe_float(row.get("qbs_top_bonus", 0.0)),
        -safe_float(row.get("membership_count", 0.0)),
        -safe_float(row.get("final_entry_score", 0.0)),
        -safe_float(row.get("scan_score", 0.0)),
        -safe_float(row.get("rs_rank_vs_index", 0.0)),
        -safe_float(row.get("volume_ratio_20", 0.0)),
        str(row.get("ticker", "")),
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


def _board_qualifiers(
    *,
    ticker: str,
    row: Mapping[str, Any],
    membership: set[str],
    target_date: date,
    qbs_top_tickers: set[str],
) -> set[str]:
    if _is_sell_risk(row, membership, target_date):
        return {"sell_risk"}

    qualifiers: set[str] = set()
    membership_count = len(membership)
    if membership_count >= 3 or (ticker in qbs_top_tickers and membership_count >= 2):
        qualifiers.add("confluence")
    if (
        "final_top" in membership
        or "buy_turn" in membership
        or is_truthy(row.get("hma_ema_long_entry"))
        or _is_ma20_reclaim(row)
    ):
        qualifiers.add("entry_now")
    if "pullback_reentry" in membership:
        qualifiers.add("pullback_reentry")
    if (
        "trend_continuation" in membership
        or "hma_ema_trend" in membership
        or is_truthy(row.get("strong_trend_persistent"))
    ):
        qualifiers.add("steady_uptrend")
    if "gap_setup" in membership or _is_compression(row) or _is_pre_high(row):
        qualifiers.add("breakout_wait")
    if _is_accumulation(row, membership):
        qualifiers.add("accumulation")
    if "new_52w_high" in membership or _is_rs_leader(row):
        qualifiers.add("rs_leader")
    if _is_chase_risk(row, membership):
        qualifiers.add("chase_risk")
    return qualifiers


def _decorate_board_row(
    *,
    section_key: str,
    row: Mapping[str, Any],
    membership: set[str],
    target_date: date,
    qbs_top_tickers: set[str],
) -> dict[str, Any]:
    row_dict = dict(row or {})
    ticker = _ticker(row_dict)
    tags = _board_tags(row_dict, membership)
    risk_flags = _board_risk_flags(row_dict, membership, target_date)
    row_dict["ticker"] = ticker
    row_dict["board_label"] = BOARD_LABELS.get(section_key, section_key.upper())
    row_dict["board_tags"] = tags
    row_dict["board_reason"] = _board_reason(tags)
    row_dict["board_risk_flags"] = risk_flags
    row_dict["board_risk"] = "+".join(risk_flags) if risk_flags else "-"
    row_dict["source_membership"] = [key for key in CORE_SECTION_ORDER if key in membership]
    row_dict["membership_count"] = len(membership)
    row_dict["qbs_top_bonus"] = 1 if ticker in qbs_top_tickers else 0
    row_dict["same_session_sell_rank"] = 1 if same_session_sell_turn(row_dict, target_date) else 0
    return row_dict


def select_post_close_board_sections(
    section_rows: Mapping[str, Iterable[Mapping[str, Any]]],
    *,
    target_date: date,
    all_rows: Iterable[Mapping[str, Any]] | None = None,
    qbs_top_tickers: Iterable[str] | None = None,
    limit: int = BOARD_SECTION_LIMIT,
) -> dict[str, list[dict[str, Any]]]:
    qbs_tickers = {str(ticker or "").strip().upper() for ticker in (qbs_top_tickers or []) if str(ticker or "").strip()}
    membership, rows_by_section = _source_membership(section_rows)
    raw_rows_by_ticker: dict[str, dict[str, Any]] = {}
    for raw_row in all_rows or []:
        row = dict(raw_row or {})
        ticker = _ticker(row)
        if ticker and ticker not in raw_rows_by_ticker:
            raw_rows_by_ticker[ticker] = row

    candidate_rows: dict[str, dict[str, Any]] = {}
    candidate_qualifiers: dict[str, set[str]] = {}

    all_tickers = sorted(set(membership) | set(raw_rows_by_ticker))
    for ticker in all_tickers:
        ticker_membership = set(membership.get(ticker) or set())
        row = _canonical_source_row(ticker, rows_by_section)
        if not row or row == {"ticker": ticker}:
            row = dict(raw_rows_by_ticker.get(ticker) or {"ticker": ticker})
        qualifiers = _board_qualifiers(
            ticker=ticker,
            row=row,
            membership=ticker_membership,
            target_date=target_date,
            qbs_top_tickers=qbs_tickers,
        )
        if not qualifiers:
            continue
        base_row = _decorate_board_row(
            section_key="",
            row=row,
            membership=ticker_membership,
            target_date=target_date,
            qbs_top_tickers=qbs_tickers,
        )
        candidate_rows[ticker] = base_row
        candidate_qualifiers[ticker] = qualifiers

    output: dict[str, list[dict[str, Any]]] = {section_key: [] for section_key in BOARD_SECTION_ORDER}
    assigned: set[str] = set()
    section_limit = max(0, int(limit or 0))

    for section_key in BOARD_SECTION_ORDER:
        section_pool = [
            row
            for ticker, row in candidate_rows.items()
            if ticker not in assigned and section_key in candidate_qualifiers.get(ticker, set())
        ]
        section_pool.sort(key=lambda row: _board_sort_key(section_key, row))
        selected: list[dict[str, Any]] = []
        for row in section_pool:
            if len(selected) >= section_limit:
                break
            ticker = _ticker(row)
            if not ticker or ticker in assigned:
                continue
            selected_row = _decorate_board_row(
                section_key=section_key,
                row=row,
                membership=set(row.get("source_membership") or []),
                target_date=target_date,
                qbs_top_tickers=qbs_tickers,
            )
            selected.append(selected_row)
            assigned.add(ticker)
        output[section_key] = selected

    return output
