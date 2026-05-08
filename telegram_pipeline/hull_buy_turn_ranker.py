from __future__ import annotations

from datetime import date
from typing import Any, Iterable, Mapping

from .rankers import (
    is_truthy,
    safe_float,
    same_day_hull_buy_turn,
    same_day_utbot_buy_turn,
    same_session_sell_turn,
)

HULL_BUY_TURN_KEY = "hull_buy_turn"
HULL_BUY_TURN_SECTION_TITLE = "당일 HULL 매수전환"
HULL_BUY_TURN_QUALITY_FLOOR = "latest-session HULL buy turn; no quality exclusions"


def _ticker(row: Mapping[str, Any]) -> str:
    return str(row.get("ticker") or "").strip().upper()


def _unique_append(values: list[str], value: str) -> None:
    if value and value not in values:
        values.append(value)


def _optional_number(row: Mapping[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = row.get(key)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if number == number:
            return number
    return None


def _is_hull_buy_turn(row: Mapping[str, Any], target_date: date) -> bool:
    return bool(is_truthy(row.get("latest_session_hull_buy_turn")) or same_day_hull_buy_turn(row, target_date))


def _is_utbot_same_turn(row: Mapping[str, Any], target_date: date) -> bool:
    return bool(is_truthy(row.get("latest_session_utbot_buy_turn")) or same_day_utbot_buy_turn(row, target_date))


def _hull_tags(row: Mapping[str, Any], target_date: date) -> list[str]:
    tags: list[str] = ["HULL"]
    if _is_utbot_same_turn(row, target_date):
        _unique_append(tags, "UTBot동시")
    if is_truthy(row.get("first_close_above_ma20_after_5bars")):
        _unique_append(tags, "MA20회복")
    if safe_float(row.get("volume_ratio_20", 0.0)) >= 1.2 or is_truthy(row.get("volume_bullish")):
        _unique_append(tags, "거래량동반")
    if safe_float(row.get("cmf", 0.0)) > 0.0:
        _unique_append(tags, "CMF+")
    if safe_float(row.get("obv_slope", 0.0)) > 0.0:
        _unique_append(tags, "OBV+")
    if safe_float(row.get("rs_rank_vs_index", 0.0)) >= 70.0:
        _unique_append(tags, "RS70+")
    return tags


def _hull_risk_flags(row: Mapping[str, Any], target_date: date) -> list[str]:
    flags: list[str] = []
    if same_session_sell_turn(row, target_date):
        _unique_append(flags, "sell_turn")
    if is_truthy(row.get("thin_trade_risk")):
        _unique_append(flags, "thin_trade")
    if is_truthy(row.get("bearish_gap_failure")):
        _unique_append(flags, "gap_failure")
    if str(row.get("strategy_conflict_level") or "").strip().upper() == "HIGH":
        _unique_append(flags, "high_conflict")
    if safe_float(row.get("multi_sell", 0.0)) >= 2.0:
        _unique_append(flags, "multi_sell")
    if safe_float(row.get("volume_ratio_20", 0.0)) < 0.8:
        _unique_append(flags, "low_volume")
    if safe_float(row.get("chg_5d", 0.0)) >= 15.0 or safe_float(row.get("dist_sma20_pct", 0.0)) >= 15.0 or safe_float(row.get("zscore20", 0.0)) >= 2.5:
        _unique_append(flags, "chase_risk")
    if safe_float(row.get("chg", 0.0)) >= 12.0:
        _unique_append(flags, "extended_day")
    return flags


def _hull_confirm_text(row: Mapping[str, Any]) -> str:
    ma20_dist = _optional_number(row, "ma20_dist_pct", "dist_sma20_pct")
    days_since = _optional_number(row, "days_since_hull_turn_bull")
    parts: list[str] = []
    if ma20_dist is not None:
        parts.append(f"MA20 {ma20_dist:+.1f}%")
    if days_since is None:
        days_since = 0.0
    parts.append(f"HULL D+{int(days_since)}")
    return " / ".join(parts)


def _decorate_hull_row(row: Mapping[str, Any], *, target_date: date) -> dict[str, Any] | None:
    row_dict = dict(row or {})
    ticker = _ticker(row_dict)
    if not ticker or not _is_hull_buy_turn(row_dict, target_date):
        return None
    tags = _hull_tags(row_dict, target_date)
    risk_flags = _hull_risk_flags(row_dict, target_date)
    row_dict["ticker"] = ticker
    row_dict["hull_bucket"] = "HULL_BUY_TURN"
    row_dict["hull_reason"] = "+".join(tags) if tags else "HULL"
    row_dict["hull_tags"] = tags
    row_dict["hull_risk_flags"] = risk_flags
    row_dict["hull_confirm"] = _hull_confirm_text(row_dict)
    row_dict["hull_utbot_same_turn"] = 1 if _is_utbot_same_turn(row_dict, target_date) else 0
    row_dict["entry_type"] = str(row_dict.get("entry_type") or "hull_buy_turn_watch")
    return row_dict


def _sort_key(row: Mapping[str, Any]) -> tuple[float, float, float, float, float, float, str]:
    return (
        -safe_float(row.get("hull_utbot_same_turn", 0.0)),
        -safe_float(row.get("volume_ratio_20", 0.0)),
        -safe_float(row.get("cmf", 0.0)),
        -safe_float(row.get("obv_slope", 0.0)),
        -safe_float(row.get("scan_score", 0.0)),
        -safe_float(row.get("rs_rank_vs_index", 0.0)),
        str(row.get("ticker", "")),
    )


def select_hull_buy_turn_rows(rows: Iterable[Mapping[str, Any]], *, target_date: date) -> list[dict[str, Any]]:
    best_by_ticker: dict[str, dict[str, Any]] = {}
    for raw_row in rows or []:
        row = _decorate_hull_row(raw_row, target_date=target_date)
        if not row:
            continue
        ticker = _ticker(row)
        existing = best_by_ticker.get(ticker)
        if existing is None or _sort_key(row) < _sort_key(existing):
            best_by_ticker[ticker] = row
    selected = list(best_by_ticker.values())
    selected.sort(key=_sort_key)
    return selected
