from __future__ import annotations

from datetime import date, datetime
from typing import Any, Mapping


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def is_truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"y", "yes", "true", "1", "t"}:
        return True
    if text in {"n", "no", "false", "0", "", "-", "none", "n/a"}:
        return False
    return bool(value)


def parse_iso_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text or text in {"-", "없음", "N/A", "n/a"}:
        return None
    try:
        return datetime.strptime(text[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def same_day_utbot_buy_turn(row: Mapping[str, Any], target_date: date) -> bool:
    return parse_iso_date(row.get("utbot_buy_last_date")) == target_date


def same_day_hull_buy_turn(row: Mapping[str, Any], target_date: date) -> bool:
    return parse_iso_date(row.get("hull_turn_bull_last_date")) == target_date


def same_day_utbot_sell_turn(row: Mapping[str, Any], target_date: date) -> bool:
    return parse_iso_date(row.get("utbot_sell_last_date")) == target_date


def same_day_hull_sell_turn(row: Mapping[str, Any], target_date: date) -> bool:
    return parse_iso_date(row.get("hull_turn_bear_last_date")) == target_date


def same_session_buy_turn(row: Mapping[str, Any], target_date: date) -> bool:
    return (
        same_day_utbot_buy_turn(row, target_date)
        or same_day_hull_buy_turn(row, target_date)
    )


def same_session_sell_turn(row: Mapping[str, Any], target_date: date) -> bool:
    return (
        same_day_utbot_sell_turn(row, target_date)
        or same_day_hull_sell_turn(row, target_date)
    )


def same_day_buy_turn_count(row: Mapping[str, Any], target_date: date) -> int:
    utbot = same_day_utbot_buy_turn(row, target_date)
    hull = same_day_hull_buy_turn(row, target_date)
    return int(utbot) + int(hull)


def same_day_sell_turn_count(row: Mapping[str, Any], target_date: date) -> int:
    utbot = same_day_utbot_sell_turn(row, target_date)
    hull = same_day_hull_sell_turn(row, target_date)
    return int(utbot) + int(hull)


def final_top_sort_key(row: Mapping[str, Any]) -> tuple[float, float, float, float, float, float, float, float, str]:
    low_conflict_bonus = 1.0 if is_truthy(row.get("low_conflict_bullish")) or str(row.get("strategy_conflict_level", "")).strip().upper() == "LOW" else 0.0
    return (
        -safe_float(row.get("final_entry_score", 0.0)),
        -low_conflict_bonus,
        -safe_float(row.get("b_score", 0.0)),
        -safe_float(row.get("c_score", 0.0)),
        -safe_float(row.get("es", 0.0)),
        -safe_float(row.get("volume_ratio_20", 0.0)),
        -safe_float(row.get("dollar_volume_20", 0.0)),
        -safe_float(row.get("scan_score", 0.0)),
        str(row.get("ticker", "")),
    )


def buy_turn_sort_key(row: Mapping[str, Any], target_date: date) -> tuple[float, float, float, float, float, float, str]:
    return (
        -safe_float(same_day_buy_turn_count(row, target_date)),
        -safe_float(row.get("volume_ratio_20", 0.0)),
        -safe_float(row.get("cmf", 0.0)),
        -safe_float(row.get("obv_slope", 0.0)),
        -safe_float(row.get("scan_score", 0.0)),
        -safe_float(row.get("es", 0.0)),
        str(row.get("ticker", "")),
    )


def pullback_sort_key(row: Mapping[str, Any]) -> tuple[float, float, float, float, float, float, str]:
    drawdown = abs(safe_float(row.get("drawdown_from_20d_high_pct", 0.0)))
    pullback_quality = -abs(drawdown - 4.0)
    return (
        -safe_float(row.get("uptrend_persistent", False)),
        -safe_float(row.get("hma60_slope_pct", 0.0)),
        -safe_float(row.get("volume_dry_up_score", 0.0)),
        pullback_quality,
        -safe_float(row.get("scan_score", 0.0)),
        -safe_float(row.get("es", 0.0)),
        str(row.get("ticker", "")),
    )


def trend_sort_key(row: Mapping[str, Any]) -> tuple[float, float, float, float, float, float, float, str]:
    overheat_penalty = safe_float(row.get("zscore20", 0.0)) + max(0.0, safe_float(row.get("dist_sma20_pct", 0.0)) / 10.0)
    return (
        -safe_float(row.get("rs_rank_vs_index", 0.0)),
        -safe_float(row.get("adx", 0.0)),
        -(safe_float(row.get("hma20_slope_pct", 0.0)) + safe_float(row.get("hma60_slope_pct", 0.0))),
        -safe_float(row.get("volume_ratio_20", 0.0)),
        overheat_penalty,
        -safe_float(row.get("scan_score", 0.0)),
        -safe_float(row.get("es", 0.0)),
        str(row.get("ticker", "")),
    )


def sell_turn_sort_key(row: Mapping[str, Any], target_date: date) -> tuple[float, float, float, float, str]:
    return (
        -safe_float(same_day_sell_turn_count(row, target_date)),
        -safe_float(row.get("volume_ratio_20", 0.0)),
        -safe_float(row.get("scan_score", 0.0)),
        -safe_float(row.get("es", 0.0)),
        str(row.get("ticker", "")),
    )


def gap_setup_sort_key(row: Mapping[str, Any]) -> tuple[float, float, float, float, str]:
    return (
        -safe_float(row.get("gap_setup_score", 0.0)),
        -safe_float(row.get("gap_setup_gate_count", 0.0)),
        -safe_float(row.get("scan_score", 0.0)),
        -safe_float(row.get("es", 0.0)),
        str(row.get("ticker", "")),
    )


def pocket_pivot_sort_key(row: Mapping[str, Any]) -> tuple[float, float, float, float, str]:
    return (
        -safe_float(row.get("pocket_pivot_score", 0.0)),
        -safe_float(row.get("pocket_pivot_gate_count", 0.0)),
        -safe_float(row.get("scan_score", 0.0)),
        -safe_float(row.get("es", 0.0)),
        str(row.get("ticker", "")),
    )


def five_day_top_sort_key(row: Mapping[str, Any]) -> tuple[float, float, float, str]:
    return (
        -safe_float(row.get("chg_5d", 0.0)),
        -safe_float(row.get("scan_score", 0.0)),
        -safe_float(row.get("es", 0.0)),
        str(row.get("ticker", "")),
    )


def new_52w_high_sort_key(row: Mapping[str, Any]) -> tuple[float, float, str]:
    return (
        -safe_float(row.get("scan_score", 0.0)),
        -safe_float(row.get("es", 0.0)),
        str(row.get("ticker", "")),
    )
