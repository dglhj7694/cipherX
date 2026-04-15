from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Iterable, Mapping, Sequence


WATCH_BUY_PLUS = {"WATCH_BUY", "BUY", "STRONG_BUY"}

SCAN_FILTER_ALL = "\uc804\uccb4"
SCAN_FILTER_UPTREND_PERSISTENT = "\uc6b0\uc0c1\ud5a5 \uc9c0\uc18d"
SCAN_FILTER_STRONG_TREND_PERSISTENT = "\uac15\ud55c \ucd94\uc138 \uc9c0\uc18d"
SCAN_FILTER_PULLBACK_REENTRY = "\ub20c\ub9bc\ubaa9 \uc7ac\uc9c4\uc785"
SCAN_FILTER_LOW_CONFLICT_BULLISH = "\uc800\ucda9\ub3cc \uac15\uc138"
SCAN_FILTER_RECENT_TREND_TURN = "\ucd5c\uadfc \ucd94\uc138\uc804\ud658"
SCAN_FILTER_RECENT_BULL_DISCOVERY = "\ucd5c\uadfc \uac15\uc138 \ubc1c\uad74"
SCAN_FILTER_VOLUME_BULLISH = "\uac70\ub798\ub7c9 \ub3d9\ubc18 \uac15\uc138"
SCAN_FILTER_TODAY_UTBOT = "\uc624\ub298 UTBot \uc804\ud658"
SCAN_FILTER_TODAY_HULL = "\uc624\ub298 HULL \uc804\ud658"

SCAN_FILTER_PRESETS: tuple[str, ...] = (
    SCAN_FILTER_ALL,
    SCAN_FILTER_UPTREND_PERSISTENT,
    SCAN_FILTER_STRONG_TREND_PERSISTENT,
    SCAN_FILTER_PULLBACK_REENTRY,
    SCAN_FILTER_LOW_CONFLICT_BULLISH,
    SCAN_FILTER_RECENT_TREND_TURN,
    SCAN_FILTER_RECENT_BULL_DISCOVERY,
    SCAN_FILTER_VOLUME_BULLISH,
    SCAN_FILTER_TODAY_UTBOT,
    SCAN_FILTER_TODAY_HULL,
)

_PULLBACK_COMBO_KEYWORDS = ("PULLBACK", "TREND")
_LONG_PULLBACK_STRATEGY_KEYWORDS = ("TREND_PULLBACK", "KELTNER_PULLBACK", "ANCHORED_VWAP")


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _is_low_conflict(conflict_level: Any) -> bool:
    return str(conflict_level or "").strip().upper() == "LOW"


def _today_and_prev(today: date | None = None) -> tuple[date, date]:
    today = today or datetime.now().date()
    return today, today - timedelta(days=1)


def is_watch_buy_plus(row: Mapping[str, Any]) -> bool:
    return str(row.get("jg_key", "")).upper() in WATCH_BUY_PLUS


def has_buy_combo(row: Mapping[str, Any]) -> bool:
    return any(str(item.get("dir", "")).lower() == "buy" for item in (row.get("scans") or []))


def has_active_strategy(row: Mapping[str, Any]) -> bool:
    if int(row.get("strategy_active_count", 0) or 0) > 0:
        return True
    return bool(row.get("strategies"))


def is_bull_discovery_candidate(row: Mapping[str, Any]) -> bool:
    return bool(
        is_watch_buy_plus(row)
        and (bool(row.get("bull_turn_recent", False)) or bool(row.get("uptrend_or_pullback", False)))
        and (has_active_strategy(row) or has_buy_combo(row))
        and bool(row.get("volume_bullish", False))
    )


def is_today_or_prev_iso_date(value: Any, *, today: date | None = None) -> bool:
    text = str(value or "").strip()
    if not text or text in {"-", "N/A", "\uc5c6\uc74c"}:
        return False
    try:
        parsed = datetime.strptime(text, "%Y-%m-%d").date()
    except Exception:
        return False
    current_day, prev_day = _today_and_prev(today)
    return parsed in {current_day, prev_day}


def has_today_transition(
    row: Mapping[str, Any],
    target_keys: Sequence[str],
    date_fields: Sequence[str],
    *,
    today: date | None = None,
) -> bool:
    current_day, prev_day = _today_and_prev(today)
    allowed_iso = {current_day.strftime("%Y-%m-%d"), prev_day.strftime("%Y-%m-%d")}
    allowed_md = {current_day.strftime("%m/%d"), prev_day.strftime("%m/%d")}

    for field in date_fields:
        if is_today_or_prev_iso_date(row.get(field), today=today):
            return True

    keys = {str(key) for key in (target_keys or [])}
    for item in (row.get("transitions") or []):
        key = str(item.get("key", "")).strip()
        if key and key not in keys:
            continue
        date_iso = str(item.get("date_iso") or "").strip()
        date_short = str(item.get("date") or "").strip()
        if date_iso in allowed_iso or date_short in allowed_md:
            return True
    return False


def has_pullback_combo(combo_items: Iterable[Mapping[str, Any]]) -> bool:
    for item in combo_items or []:
        direction = str(item.get("dir", "")).lower()
        if direction != "buy":
            continue
        key = str(item.get("key", "")).upper()
        if any(keyword in key for keyword in _PULLBACK_COMBO_KEYWORDS):
            return True
    return False


def has_long_pullback_strategy(strategy_results: Iterable[Mapping[str, Any]]) -> bool:
    for item in strategy_results or []:
        if str(item.get("direction", "")).upper() != "LONG":
            continue
        strategy_id = str(item.get("id", "")).upper()
        if any(keyword in strategy_id for keyword in _LONG_PULLBACK_STRATEGY_KEYWORDS):
            return True
    return False


def compute_scanner_profile_flags(
    *,
    current_close: Any,
    ma20: Any,
    ma50: Any,
    ma20_prev: Any,
    ma50_prev: Any,
    watch_buy_plus: bool,
    strategy_bias: Any,
    recent_utbot_sell: bool,
    recent_hull_bear: bool,
    adx: Any,
    es: Any,
    cf: Any,
    volume_bullish: bool,
    strategy_conflict_level: Any,
    pullback_ready: bool,
    pullback_combo_present: bool,
    long_pullback_strategy_visible: bool,
    multi_sell: Any,
    thin_trade_risk: bool,
    flip_guard_triggered: bool,
) -> dict[str, bool]:
    close_value = _to_float(current_close)
    ma20_value = _to_float(ma20)
    ma50_value = _to_float(ma50)
    ma20_prev_value = _to_float(ma20_prev, ma20_value)
    ma50_prev_value = _to_float(ma50_prev, ma50_value)
    adx_value = _to_float(adx)
    es_value = _to_float(es)
    cf_value = _to_float(cf)
    multi_sell_count = int(_to_float(multi_sell, 0))

    uptrend_structure = bool(
        ma20_value > 0
        and ma50_value > 0
        and close_value > ma20_value > ma50_value
    )
    ma_slopes_non_decreasing = bool(ma20_value >= ma20_prev_value and ma50_value >= ma50_prev_value)
    strategy_bias_long = str(strategy_bias or "").strip().upper() == "LONG"
    recent_bear_turn = bool(recent_utbot_sell or recent_hull_bear)

    uptrend_persistent = bool(
        uptrend_structure
        and ma_slopes_non_decreasing
        and (watch_buy_plus or strategy_bias_long)
        and not recent_bear_turn
    )

    strong_trend_persistent = bool(
        uptrend_persistent
        and adx_value >= 20.0
        and es_value >= 8.0
        and cf_value >= 65.0
        and volume_bullish
        and _is_low_conflict(strategy_conflict_level)
    )

    pullback_reentry = bool(
        uptrend_persistent
        and (pullback_ready or pullback_combo_present)
        and long_pullback_strategy_visible
        and watch_buy_plus
    )

    low_conflict_bullish = bool(
        watch_buy_plus
        and _is_low_conflict(strategy_conflict_level)
        and str(strategy_bias or "").strip().upper() != "SHORT"
        and multi_sell_count <= 1
        and not thin_trade_risk
        and not flip_guard_triggered
    )

    return {
        "uptrend_persistent": uptrend_persistent,
        "strong_trend_persistent": strong_trend_persistent,
        "pullback_reentry": pullback_reentry,
        "low_conflict_bullish": low_conflict_bullish,
    }


def apply_scan_filter(results: Iterable[Mapping[str, Any]], preset: str, *, today: date | None = None) -> list[Mapping[str, Any]]:
    rows = list(results or [])
    if preset == SCAN_FILTER_UPTREND_PERSISTENT:
        return [row for row in rows if bool(row.get("uptrend_persistent", False))]
    if preset == SCAN_FILTER_STRONG_TREND_PERSISTENT:
        return [row for row in rows if bool(row.get("strong_trend_persistent", False))]
    if preset == SCAN_FILTER_PULLBACK_REENTRY:
        return [row for row in rows if bool(row.get("pullback_reentry", False))]
    if preset == SCAN_FILTER_LOW_CONFLICT_BULLISH:
        return [row for row in rows if bool(row.get("low_conflict_bullish", False))]
    if preset == SCAN_FILTER_RECENT_TREND_TURN:
        return [row for row in rows if bool(row.get("bull_turn_recent", False))]
    if preset == SCAN_FILTER_RECENT_BULL_DISCOVERY:
        return [row for row in rows if is_bull_discovery_candidate(row)]
    if preset == SCAN_FILTER_VOLUME_BULLISH:
        return [row for row in rows if bool(row.get("volume_bullish", False))]
    if preset == SCAN_FILTER_TODAY_UTBOT:
        return [
            row
            for row in rows
            if has_today_transition(
                row,
                target_keys={"UTBot_Buy", "UTBot_Sell"},
                date_fields=("utbot_buy_last_date", "utbot_sell_last_date"),
                today=today,
            )
        ]
    if preset == SCAN_FILTER_TODAY_HULL:
        return [
            row
            for row in rows
            if has_today_transition(
                row,
                target_keys={"Hull_Turn_Bull", "Hull_Turn_Bear"},
                date_fields=("hull_turn_bull_last_date", "hull_turn_bear_last_date"),
                today=today,
            )
        ]
    return rows
