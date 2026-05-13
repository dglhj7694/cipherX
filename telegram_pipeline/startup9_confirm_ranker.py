from __future__ import annotations

import ast
import json
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable, Mapping

from .rankers import is_truthy, parse_iso_date, safe_float, same_session_buy_turn, same_session_sell_turn

STARTUP9_CONFIRM_KEY = "startup9_confirm"
STARTUP9_CONFIRM_LIMIT = 20
STARTUP9_CONFIRM_TITLE = "Startup식 9개 강세확인 Top 20"
STARTUP9_CONFIRM_QUALITY_FLOOR = "9개 추정 강세조건 중 6개 이상 + 최근 매도전환 없음 + 유동성 통과"

STARTUP9_MIN_CONFIRM_COUNT = 6
STARTUP9_MIN_DOLLAR_VOLUME_20 = 20_000_000.0
STARTUP9_RECENT_WINDOW = 5

TREND_BULLISH_KEY = "startup9_trend_bullish"
ABOVE_GOLD_ZONE_KEY = "startup9_above_gold_zone"
BLUE_DIAMOND_ENTRY_KEY = "startup9_blue_diamond_entry"
NO_PINK_DIAMOND_KEY = "startup9_no_pink_diamond"
MARKET_STRUCTURE_BULLISH_KEY = "startup9_market_structure_bullish"
SUPPORT_HOLD_KEY = "startup9_support_hold"
SMART_MONEY_FLOW_KEY = "startup9_smart_money_flow"
BULLISH_REVERSAL_KEY = "startup9_bullish_reversal"
HYPE_WAVE_MOMENTUM_KEY = "startup9_hype_wave_momentum"

STARTUP9_CONFIRM_KEYS: tuple[str, ...] = (
    TREND_BULLISH_KEY,
    ABOVE_GOLD_ZONE_KEY,
    BLUE_DIAMOND_ENTRY_KEY,
    NO_PINK_DIAMOND_KEY,
    MARKET_STRUCTURE_BULLISH_KEY,
    SUPPORT_HOLD_KEY,
    SMART_MONEY_FLOW_KEY,
    BULLISH_REVERSAL_KEY,
    HYPE_WAVE_MOMENTUM_KEY,
)

STARTUP9_CONFIRM_LABELS: dict[str, str] = {
    TREND_BULLISH_KEY: "Trend Pane Bullish",
    ABOVE_GOLD_ZONE_KEY: "Above Gold Zone",
    BLUE_DIAMOND_ENTRY_KEY: "Blue Diamond Entry",
    NO_PINK_DIAMOND_KEY: "No Pink Diamond",
    MARKET_STRUCTURE_BULLISH_KEY: "Market Structure Bullish",
    SUPPORT_HOLD_KEY: "Order Block / Support Hold",
    SMART_MONEY_FLOW_KEY: "Smart Money Flow",
    BULLISH_REVERSAL_KEY: "Bullish Divergence / Reversal",
    HYPE_WAVE_MOMENTUM_KEY: "Hype-Wave Momentum",
}

HARD_BUY_SIGNAL_KEYS = {
    "System_Turn_Bull",
    "Trend_Inflection_Bull",
    "UTBot_Buy",
    "Hull_Turn_Bull",
}

HARD_SELL_SIGNAL_KEYS = {
    "System_Turn_Bear",
    "Trend_Inflection_Bear",
    "UTBot_Sell",
    "Hull_Turn_Bear",
}

BLUE_DIAMOND_SIGNAL_KEYS = {
    "System_Turn_Bull",
    "Trend_Inflection_Bull",
    "UTBot_Buy",
    "Hull_Turn_Bull",
    "CS_Triple_Confirm_Buy",
    "CS_Ultimate_Buy",
}

STRUCTURE_SIGNAL_KEYS = {
    "New_52W_High",
    "New_52W_Closing_High",
    "Kumo_Breakout_Bull",
    "BB_Upper_Break",
    "CS_Breakout_Momentum_Buy",
    "CS_Squeeze_Breakout_Buy",
    "CS_Breakout_Confirm_Buy",
    "CS_Ichimoku_Breakout_Buy",
}

SUPPORT_SIGNAL_KEYS = {
    "EMA_Pullback_Buy",
    "MA20_Support",
    "MA50_Support",
    "Pullback_123_Bull",
    "NonADX_123_Bull",
    "CS_Trend_Pullback_Buy",
    "CS_Trend_Continuation_Buy",
    "CS_MA_Confluence_Buy",
    "CS_Structure_Support_Buy",
}

FLOW_STRONG_SIGNAL_KEYS = {
    "Pocket_Pivot",
    "CMF_Bull",
    "MF_Cross_Bull",
    "MF_Accel_Up",
    "CS_Institutional_Accumulation",
}

FLOW_WEAK_SIGNAL_KEYS = {
    "Volume_Surge",
    "Volume_Climax_Buy",
}

REVERSAL_SIGNAL_KEYS = {
    "Bull_Divergence",
    "RSI_Bull_Divergence",
    "OBV_Div_Buy",
    "MF_Bull_Div",
    "Morning_Star",
    "Hammer",
    "Bullish_Engulfing",
    "Outside_Bullish",
    "Green_Dot_T1",
    "Green_Dot_T2",
    "Gold_Dot",
    "CS_Divergence_Confluence_Buy",
    "CS_Reversal_Cluster_Buy",
    "CS_Bottom_Fishing_Buy",
    "CS_Triple_Oversold_Reversal",
    "CS_Capitulation_Bottom",
    "CS_Oversold_Bounce_Buy",
}

MOMENTUM_SIGNAL_KEYS = {
    "MACD_Cross_Buy",
    "MACD_Zero_Cross_Buy",
    "ADX_New_Uptrend",
    "ADX_Momentum_Buy",
    "Squeeze_Fire_Buy",
    "BB_Squeeze_End_Bull",
    "CS_Momentum_Accel_Buy",
    "CS_Squeeze_Breakout_Buy",
    "CS_Breakout_Momentum_Buy",
    "CS_VuManChu_Squeeze_Buy",
}


@dataclass
class Startup9ConfirmResult:
    ticker: str
    confirm_count: int
    grade: str
    hits: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    reason: str = ""
    risk_flags: list[str] = field(default_factory=list)
    startup9_score: float = 0.0
    rank: int = 0
    price: float | None = None
    chg_pct: float | None = None
    volume_ratio_20: float | None = None
    adx: float | None = None
    profile: str = "MIXED_BULL"
    direction_state: str = "NO_RECENT_TURN"
    confirm_map: dict[str, bool] = field(default_factory=dict)
    confirm_keys: list[str] = field(default_factory=list)
    missing_keys: list[str] = field(default_factory=list)
    hard_exclusions: list[str] = field(default_factory=list)
    soft_risk_flags: list[str] = field(default_factory=list)
    source_flags: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class _SignalEvent:
    key: str
    side: str
    event_date: date | None
    event_dt: datetime | None = None


def _ticker(row: Mapping[str, Any]) -> str:
    return str(row.get("ticker") or "").strip().upper()


def _unique_append(values: list[str], value: str) -> None:
    text = str(value or "").strip()
    if text and text not in values:
        values.append(text)


def _optional_number(row: Mapping[str, Any], *keys: str) -> float | None:
    for key in keys:
        if key not in row:
            continue
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


def _has_number(row: Mapping[str, Any], *keys: str) -> bool:
    return _optional_number(row, *keys) is not None


def _number(row: Mapping[str, Any], *keys: str, default: float = 0.0) -> float:
    value = _optional_number(row, *keys)
    return default if value is None else value


def _parse_detected_signals(raw_value: Any) -> list[Mapping[str, Any]]:
    if raw_value is None:
        return []
    if isinstance(raw_value, Mapping):
        return [raw_value]
    if isinstance(raw_value, (list, tuple)):
        return [item for item in raw_value if isinstance(item, Mapping)]
    if isinstance(raw_value, str):
        text = raw_value.strip()
        if not text or text in {"-", "없음", "N/A", "n/a", "none", "None"}:
            return []
        for loader in (json.loads, ast.literal_eval):
            try:
                parsed = loader(text)
            except Exception:
                continue
            if isinstance(parsed, Mapping):
                return [parsed]
            if isinstance(parsed, (list, tuple)):
                return [item for item in parsed if isinstance(item, Mapping)]
    return []


def _date_from_text(value: Any, target_date: date) -> date | None:
    parsed = parse_iso_date(value)
    if parsed is not None:
        return parsed
    text = str(value or "").strip()
    if not text or text in {"-", "없음", "N/A", "n/a"}:
        return None
    try:
        if len(text) == 5 and text[2] == "/":
            month = int(text[:2])
            day = int(text[3:])
            return date(target_date.year, month, day)
    except Exception:
        return None
    return None


def _datetime_from_value(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except Exception:
        return None
    if parsed.tzinfo is not None:
        return parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _event_datetime(item: Mapping[str, Any]) -> datetime | None:
    for key in ("timestamp", "datetime", "detected_at", "ts", "time"):
        parsed = _datetime_from_value(item.get(key))
        if parsed is not None:
            return parsed
    return None


def _item_date(item: Mapping[str, Any], target_date: date) -> date | None:
    item_dt = _event_datetime(item)
    if item_dt is not None:
        return item_dt.date()
    days_raw = item.get("days_ago")
    if days_raw is not None:
        days = int(safe_float(days_raw, default=999.0))
        if 0 <= days <= 999:
            return target_date - timedelta(days=days)
    return _date_from_text(item.get("date") or item.get("date_short"), target_date)


def _is_recent_item(item: Mapping[str, Any], target_date: date, window: int = STARTUP9_RECENT_WINDOW) -> bool:
    days_raw = item.get("days_ago")
    if days_raw is not None:
        days = int(safe_float(days_raw, default=999.0))
        return 0 <= days <= window
    item_date = _item_date(item, target_date)
    if item_date is None:
        return True
    days = (target_date - item_date).days
    return 0 <= days <= window


def _recent_date_field(row: Mapping[str, Any], key: str, target_date: date, window: int = STARTUP9_RECENT_WINDOW) -> bool:
    item_date = _date_from_text(row.get(key), target_date)
    if item_date is None:
        return False
    days = (target_date - item_date).days
    return 0 <= days <= window


def _normalized_signals(row: Mapping[str, Any], target_date: date) -> list[Mapping[str, Any]]:
    signals: list[Mapping[str, Any]] = []
    for raw_key in ("detected_signals", "recent_signals", "combined_scans", "derived_signal_events", "derived_reason_states"):
        for item in _parse_detected_signals(row.get(raw_key)):
            if _is_recent_item(item, target_date):
                signals.append(item)
    return signals


def _recent_signal_keys(row: Mapping[str, Any], target_date: date) -> set[str]:
    keys: set[str] = set()
    for item in _normalized_signals(row, target_date):
        key = str(item.get("key") or item.get("name") or "").strip()
        if key:
            keys.add(key)
    return keys


def _has_recent_signal(row: Mapping[str, Any], target_date: date, keys: set[str]) -> bool:
    signal_keys = _recent_signal_keys(row, target_date)
    if signal_keys.intersection(keys):
        return True
    for key in keys:
        if is_truthy(row.get(key)) or is_truthy(row.get(key.lower())):
            return True
    return False


def _row_event(row: Mapping[str, Any], key: str, side: str, date_key: str, recent_key: str, target_date: date) -> _SignalEvent | None:
    item_date = _date_from_text(row.get(date_key), target_date)
    if item_date is not None:
        days = (target_date - item_date).days
        if 0 <= days <= STARTUP9_RECENT_WINDOW:
            return _SignalEvent(key=key, side=side, event_date=item_date)
    if is_truthy(row.get(recent_key)) or is_truthy(row.get(key)) or is_truthy(row.get(key.lower())):
        return _SignalEvent(key=key, side=side, event_date=target_date)
    return None


def _direction_events(row: Mapping[str, Any], target_date: date) -> list[_SignalEvent]:
    events: list[_SignalEvent] = []
    for item in _normalized_signals(row, target_date):
        key = str(item.get("key") or item.get("name") or "").strip()
        if key not in HARD_BUY_SIGNAL_KEYS and key not in HARD_SELL_SIGNAL_KEYS:
            continue
        side = "buy" if key in HARD_BUY_SIGNAL_KEYS else "sell"
        events.append(_SignalEvent(key=key, side=side, event_date=_item_date(item, target_date), event_dt=_event_datetime(item)))

    row_events = (
        ("UTBot_Buy", "buy", "utbot_buy_last_date", "utbot_buy_recent"),
        ("Hull_Turn_Bull", "buy", "hull_turn_bull_last_date", "hull_turn_bull_recent"),
        ("System_Turn_Bull", "buy", "system_turn_bull_last_date", "system_turn_bull_recent"),
        ("Trend_Inflection_Bull", "buy", "trend_inflection_bull_last_date", "trend_inflection_bull_recent"),
        ("UTBot_Sell", "sell", "utbot_sell_last_date", "utbot_sell_recent"),
        ("Hull_Turn_Bear", "sell", "hull_turn_bear_last_date", "hull_turn_bear_recent"),
        ("System_Turn_Bear", "sell", "system_turn_bear_last_date", "system_turn_bear_recent"),
        ("Trend_Inflection_Bear", "sell", "trend_inflection_bear_last_date", "trend_inflection_bear_recent"),
    )
    for key, side, date_key, recent_key in row_events:
        event = _row_event(row, key, side, date_key, recent_key, target_date)
        if event is not None:
            events.append(event)

    if is_truthy(row.get("latest_session_utbot_buy_turn")):
        events.append(_SignalEvent(key="UTBot_Buy", side="buy", event_date=target_date))
    if is_truthy(row.get("latest_session_hull_buy_turn")):
        events.append(_SignalEvent(key="Hull_Turn_Bull", side="buy", event_date=target_date))
    if same_session_buy_turn(row, target_date):
        events.append(_SignalEvent(key="Session_Buy_Turn", side="buy", event_date=target_date))
    if same_session_sell_turn(row, target_date):
        events.append(_SignalEvent(key="Session_Sell_Turn", side="sell", event_date=target_date))
    return events


def _latest_side_event(events: Iterable[_SignalEvent], side: str) -> _SignalEvent | None:
    filtered = [event for event in events if event.side == side]
    if not filtered:
        return None
    return max(
        filtered,
        key=lambda event: (
            event.event_date or date.min,
            event.event_dt is not None,
            event.event_dt or datetime.min,
            event.key,
        ),
    )


def _direction_state(row: Mapping[str, Any], target_date: date) -> str:
    events = _direction_events(row, target_date)
    latest_buy = _latest_side_event(events, "buy")
    latest_sell = _latest_side_event(events, "sell")
    if latest_buy is None and latest_sell is None:
        return "NO_RECENT_TURN"
    if latest_buy is not None and latest_sell is None:
        return "BULL_ACTIVE"
    if latest_sell is not None and latest_buy is None:
        return "BEAR_ACTIVE"

    assert latest_buy is not None and latest_sell is not None
    if latest_buy.event_dt is not None and latest_sell.event_dt is not None and latest_buy.event_dt != latest_sell.event_dt:
        return "BULL_RECLAIMED" if latest_buy.event_dt > latest_sell.event_dt else "BEAR_ACTIVE"
    buy_date = latest_buy.event_date
    sell_date = latest_sell.event_date
    if buy_date is not None and sell_date is not None and buy_date != sell_date:
        return "BULL_RECLAIMED" if buy_date > sell_date else "BEAR_ACTIVE"
    if buy_date == sell_date:
        return "MIXED_SAME_DAY"
    return "MIXED_SAME_DAY"


def _above_gold_zone(row: Mapping[str, Any]) -> bool:
    ma20_dist = _optional_number(row, "ma20_dist_pct", "dist_sma20_pct", "ma20_dist")
    if ma20_dist is None:
        price = _optional_number(row, "price")
        ma20 = _optional_number(row, "ma20", "MA20")
        if price is not None and ma20 is not None and abs(ma20) > 1e-10:
            ma20_dist = ((price - ma20) / ma20) * 100.0
    if ma20_dist is None or ma20_dist < -2.0:
        return False

    percent_b = _optional_number(row, "bb_percent_b", "percent_b")
    if percent_b is not None and percent_b < 0.45:
        return False
    return True


def _trend_bullish(row: Mapping[str, Any]) -> bool:
    if is_truthy(row.get("uptrend_persistent")) or is_truthy(row.get("strong_trend_persistent")):
        return True
    if is_truthy(row.get("hma_ema_long_aligned")):
        return True
    price = _optional_number(row, "price")
    ma20 = _optional_number(row, "ma20", "MA20")
    ema20 = _optional_number(row, "ema20", "ema21", "EMA20", "EMA21")
    adx = _number(row, "adx", "ADX")
    reference = ma20 if ma20 is not None else ema20
    if price is not None and reference is not None and reference > 0:
        dist = ((price - reference) / reference) * 100.0
        return bool(dist >= -2.0 and adx >= 18.0)
    return False


def _blue_diamond_entry(row: Mapping[str, Any], target_date: date) -> bool:
    if _has_recent_signal(row, target_date, BLUE_DIAMOND_SIGNAL_KEYS):
        return True
    return bool(
        is_truthy(row.get("latest_session_utbot_buy_turn"))
        or is_truthy(row.get("latest_session_hull_buy_turn"))
        or _recent_date_field(row, "utbot_buy_last_date", target_date)
        or _recent_date_field(row, "hull_turn_bull_last_date", target_date)
        or _recent_date_field(row, "system_turn_bull_last_date", target_date)
        or _recent_date_field(row, "trend_inflection_bull_last_date", target_date)
        or is_truthy(row.get("bull_turn_recent"))
    )


def _market_structure_bullish(row: Mapping[str, Any], target_date: date) -> bool:
    if _has_recent_signal(row, target_date, STRUCTURE_SIGNAL_KEYS):
        return True
    return bool(
        is_truthy(row.get("first_higher_low_pivot2"))
        or is_truthy(row.get("first_higher_high_pivot2"))
        or is_truthy(row.get("new_52w_high"))
        or is_truthy(row.get("new_52w_closing_high"))
        or _number(row, "breakout_dist_20d_high_pct", default=-999.0) >= 0.0
        or _number(row, "breakout_dist_channel_up_pct", default=-999.0) >= 0.0
        or is_truthy(row.get("box_breakout_bull"))
        or is_truthy(row.get("channel_breakout_bull"))
        or is_truthy(row.get("diag_breakout_bull"))
        or is_truthy(row.get("triangle_breakout_bull"))
        or is_truthy(row.get("near_52w_high_2pct"))
    )


def _support_hold(row: Mapping[str, Any], target_date: date) -> bool:
    if _has_recent_signal(row, target_date, SUPPORT_SIGNAL_KEYS):
        return True
    return bool(
        is_truthy(row.get("pullback_reentry"))
        or is_truthy(row.get("pullback_ready"))
        or is_truthy(row.get("MA20_Support"))
        or is_truthy(row.get("MA50_Support"))
        or is_truthy(row.get("ma20_support"))
        or is_truthy(row.get("ma50_support"))
        or is_truthy(row.get("first_close_above_ma20_after_5bars"))
        or is_truthy(row.get("diag_support_hold"))
        or is_truthy(row.get("box_support_hold"))
        or is_truthy(row.get("channel_support_hold"))
        or is_truthy(row.get("fib_382_support"))
        or is_truthy(row.get("fib_50_support"))
        or is_truthy(row.get("fib_618_support"))
        or is_truthy(row.get("fib_618_reclaim"))
        or _number(row, "dist_vwap_pct", default=-999.0) >= 0.0
        or _number(row, "dist_poc_pct", "dist_vp_poc_pct", default=-999.0) >= 0.0
    )


def _smart_money_flow(row: Mapping[str, Any], target_date: date) -> bool:
    signal_keys = _recent_signal_keys(row, target_date)
    strong = 0
    weak = 0
    if signal_keys.intersection(FLOW_STRONG_SIGNAL_KEYS):
        strong += 1
    if signal_keys.intersection(FLOW_WEAK_SIGNAL_KEYS):
        weak += 1
    if is_truthy(row.get("pocket_pivot_candidate")) or is_truthy(row.get("pocket_pivot_recent")) or is_truthy(row.get("Pocket_Pivot")):
        strong += 1
    if _number(row, "cmf", "CMF") >= 0.10:
        strong += 1
    elif _number(row, "cmf", "CMF") > 0.0:
        weak += 1
    if _number(row, "obv_slope", "OBV_Slope") >= 0.3:
        strong += 1
    elif _number(row, "obv_slope", "OBV_Slope") > 0.0:
        weak += 1
    if _number(row, "volume_ratio_20") >= 1.5:
        strong += 1
    elif _number(row, "volume_ratio_20") >= 1.2:
        weak += 1
    if is_truthy(row.get("volume_bullish")) or is_truthy(row.get("volume_surge")):
        weak += 1
    return bool(strong >= 1 or weak >= 2)


def _bullish_reversal(row: Mapping[str, Any], target_date: date) -> bool:
    if _has_recent_signal(row, target_date, REVERSAL_SIGNAL_KEYS):
        return True
    return any(is_truthy(row.get(key)) or is_truthy(row.get(key.lower())) for key in REVERSAL_SIGNAL_KEYS)


def _hype_wave_momentum(row: Mapping[str, Any], target_date: date) -> bool:
    if _has_recent_signal(row, target_date, MOMENTUM_SIGNAL_KEYS):
        return True
    return bool(
        _number(row, "adx", "ADX") >= 20.0
        or _number(row, "rs_rank_vs_index") >= 70.0
        or any(is_truthy(row.get(key)) or is_truthy(row.get(key.lower())) for key in MOMENTUM_SIGNAL_KEYS)
    )


def _grade(confirm_count: int) -> str:
    if confirm_count >= 8:
        return "FULL_BULL"
    if confirm_count >= 6:
        return "STRONG_BULL"
    if confirm_count >= 4:
        return "WATCH_BULL"
    return "WEAK"


def _soft_risk_flags(row: Mapping[str, Any], direction_state: str) -> list[str]:
    flags: list[str] = []
    if direction_state == "BULL_RECLAIMED":
        _unique_append(flags, "sell_signal_recovered")
        _unique_append(flags, "whipsaw_reclaim")
    if _number(row, "rsi", "RSI") >= 75.0:
        _unique_append(flags, "rsi_hot")
    if _number(row, "ma20_dist_pct", "dist_sma20_pct", "ma20_dist") >= 18.0:
        _unique_append(flags, "ma20_extended")
    if _number(row, "chg_5d") >= 25.0:
        _unique_append(flags, "extended_5d")
    if is_truthy(row.get("gap_chase_risk")) or is_truthy(row.get("gap_risk_2pct")) or is_truthy(row.get("gap_risk_atr")):
        _unique_append(flags, "gap_chase_risk")
    if is_truthy(row.get("bearish_gap_failure")) or is_truthy(row.get("bearish_gap_failure__2")):
        _unique_append(flags, "bearish_gap_failure")
    if is_truthy(row.get("high_conflict")) or str(row.get("strategy_conflict_level") or "").strip().upper() == "HIGH":
        _unique_append(flags, "high_conflict")
    return flags


def _hard_exclusions(row: Mapping[str, Any], direction_state: str) -> list[str]:
    flags: list[str] = []
    if direction_state == "BEAR_ACTIVE":
        _unique_append(flags, "recent_sell_turn")
        _unique_append(flags, "no_pink_diamond_false")
    elif direction_state == "MIXED_SAME_DAY":
        _unique_append(flags, "direction_conflict")
        _unique_append(flags, "no_pink_diamond_false")
    if is_truthy(row.get("thin_trade_risk")):
        _unique_append(flags, "thin_trade_risk")
    if is_truthy(row.get("low_dollar_volume")) or (
        _has_number(row, "dollar_volume_20") and _number(row, "dollar_volume_20") < STARTUP9_MIN_DOLLAR_VOLUME_20
    ):
        _unique_append(flags, "low_dollar_volume")
    return flags


def _profile(confirm_map: Mapping[str, bool], row: Mapping[str, Any]) -> str:
    scores: dict[str, int] = {
        "EARLY_REVERSAL": (
            int(confirm_map.get(BULLISH_REVERSAL_KEY, False)) * 2
            + int(confirm_map.get(BLUE_DIAMOND_ENTRY_KEY, False))
            + int(confirm_map.get(SUPPORT_HOLD_KEY, False))
            + int(confirm_map.get(SMART_MONEY_FLOW_KEY, False))
        ),
        "TREND_CONTINUATION": (
            int(confirm_map.get(TREND_BULLISH_KEY, False)) * 2
            + int(confirm_map.get(HYPE_WAVE_MOMENTUM_KEY, False)) * 2
            + int(confirm_map.get(ABOVE_GOLD_ZONE_KEY, False))
            + int(confirm_map.get(SMART_MONEY_FLOW_KEY, False))
        ),
        "PULLBACK_REENTRY": (
            int(confirm_map.get(SUPPORT_HOLD_KEY, False)) * 2
            + int(confirm_map.get(TREND_BULLISH_KEY, False))
            + int(confirm_map.get(ABOVE_GOLD_ZONE_KEY, False))
            + int(confirm_map.get(BLUE_DIAMOND_ENTRY_KEY, False))
        ),
        "BREAKOUT_MOMENTUM": (
            int(confirm_map.get(MARKET_STRUCTURE_BULLISH_KEY, False)) * 2
            + int(confirm_map.get(HYPE_WAVE_MOMENTUM_KEY, False)) * 2
            + int(confirm_map.get(SMART_MONEY_FLOW_KEY, False))
            + int(confirm_map.get(BLUE_DIAMOND_ENTRY_KEY, False))
        ),
        "HIGH_VOL_SATELLITE": (
            int(_number(row, "atr_pct") >= 6.0 or _number(row, "volume_ratio_20") >= 2.0 or _number(row, "chg") >= 8.0) * 2
            + int(confirm_map.get(HYPE_WAVE_MOMENTUM_KEY, False))
            + int(confirm_map.get(SMART_MONEY_FLOW_KEY, False))
        ),
    }
    top_score = max(scores.values() or [0])
    winners = [profile for profile, score in scores.items() if score == top_score]
    if top_score < 3 or len(winners) != 1:
        return "MIXED_BULL"
    return winners[0]


def _score(row: Mapping[str, Any], confirm_count: int, risk_flags: list[str]) -> float:
    score = confirm_count * 10.0
    volume_ratio = _number(row, "volume_ratio_20")
    if volume_ratio >= 2.0:
        score += 5.0
    elif volume_ratio >= 1.5:
        score += 3.0
    elif volume_ratio >= 1.2:
        score += 1.5
    adx = _number(row, "adx", "ADX")
    if adx >= 30.0:
        score += 4.0
    elif adx >= 25.0:
        score += 2.5
    elif adx >= 20.0:
        score += 1.0
    rs_rank = _number(row, "rs_rank_vs_index")
    if rs_rank >= 85.0:
        score += 3.0
    elif rs_rank >= 70.0:
        score += 1.5
    score -= len(risk_flags) * 2.0
    return round(score, 1)


def _reason(hits: list[str], profile: str, direction_state: str) -> str:
    parts = [profile, direction_state]
    if hits:
        parts.append(" + ".join(hits[:3]))
    return " / ".join(part for part in parts if part) or "-"


def evaluate_startup9_confirm(row: Mapping[str, Any], target_date: date) -> Startup9ConfirmResult:
    row_dict = dict(row or {})
    direction_state = _direction_state(row_dict, target_date)
    no_pink = direction_state in {"BULL_ACTIVE", "BULL_RECLAIMED", "NO_RECENT_TURN"}
    confirm_map = {
        TREND_BULLISH_KEY: _trend_bullish(row_dict),
        ABOVE_GOLD_ZONE_KEY: _above_gold_zone(row_dict),
        BLUE_DIAMOND_ENTRY_KEY: _blue_diamond_entry(row_dict, target_date),
        NO_PINK_DIAMOND_KEY: no_pink,
        MARKET_STRUCTURE_BULLISH_KEY: _market_structure_bullish(row_dict, target_date),
        SUPPORT_HOLD_KEY: _support_hold(row_dict, target_date),
        SMART_MONEY_FLOW_KEY: _smart_money_flow(row_dict, target_date),
        BULLISH_REVERSAL_KEY: _bullish_reversal(row_dict, target_date),
        HYPE_WAVE_MOMENTUM_KEY: _hype_wave_momentum(row_dict, target_date),
    }
    confirm_keys = [key for key in STARTUP9_CONFIRM_KEYS if confirm_map.get(key)]
    missing_keys = [key for key in STARTUP9_CONFIRM_KEYS if not confirm_map.get(key)]
    hits = [STARTUP9_CONFIRM_LABELS[key] for key in confirm_keys]
    missing = [STARTUP9_CONFIRM_LABELS[key] for key in missing_keys]
    hard_exclusions = _hard_exclusions(row_dict, direction_state)
    soft_risk_flags = _soft_risk_flags(row_dict, direction_state)
    risk_flags: list[str] = []
    for flag in [*hard_exclusions, *soft_risk_flags]:
        _unique_append(risk_flags, flag)
    confirm_count = len(confirm_keys)
    profile = _profile(confirm_map, row_dict)
    score = _score(row_dict, confirm_count, risk_flags)

    source_flags = {
        "startup9_confirm_count": confirm_count,
        "startup9_confirm_grade": _grade(confirm_count),
        "startup9_confirm_hits": hits,
        "startup9_confirm_missing": missing,
        "startup9_confirm_reason": _reason(hits, profile, direction_state),
        "startup9_risk_flags": risk_flags,
        "startup9_score": score,
        "startup9_confirm_map": dict(confirm_map),
        "startup9_confirm_keys": list(confirm_keys),
        "startup9_missing_keys": list(missing_keys),
        "startup9_profile": profile,
        "startup9_direction_state": direction_state,
        "startup9_hard_exclusions": list(hard_exclusions),
        "startup9_soft_risk_flags": list(soft_risk_flags),
    }
    return Startup9ConfirmResult(
        ticker=_ticker(row_dict),
        confirm_count=confirm_count,
        grade=_grade(confirm_count),
        hits=hits,
        missing=missing,
        reason=str(source_flags["startup9_confirm_reason"]),
        risk_flags=risk_flags,
        startup9_score=score,
        price=_optional_number(row_dict, "price"),
        chg_pct=_optional_number(row_dict, "chg", "price_change_pct"),
        volume_ratio_20=_optional_number(row_dict, "volume_ratio_20"),
        adx=_optional_number(row_dict, "adx", "ADX"),
        profile=profile,
        direction_state=direction_state,
        confirm_map=dict(confirm_map),
        confirm_keys=list(confirm_keys),
        missing_keys=list(missing_keys),
        hard_exclusions=list(hard_exclusions),
        soft_risk_flags=list(soft_risk_flags),
        source_flags=source_flags,
    )


def _candidate_sort_key(candidate: Startup9ConfirmResult) -> tuple[float, float, float, float, str]:
    return (
        -safe_float(candidate.confirm_count),
        -safe_float(candidate.startup9_score),
        -safe_float(candidate.volume_ratio_20),
        -safe_float(candidate.adx),
        str(candidate.ticker),
    )


def rank_startup9_confirm_candidates(
    rows: Iterable[Mapping[str, Any]],
    target_date: date,
    limit: int | None = STARTUP9_CONFIRM_LIMIT,
) -> list[Startup9ConfirmResult]:
    best_by_ticker: dict[str, Startup9ConfirmResult] = {}
    for raw_row in rows or []:
        candidate = evaluate_startup9_confirm(raw_row or {}, target_date)
        if not candidate.ticker:
            continue
        if candidate.confirm_count < STARTUP9_MIN_CONFIRM_COUNT:
            continue
        if candidate.hard_exclusions:
            continue
        existing = best_by_ticker.get(candidate.ticker)
        if existing is None or _candidate_sort_key(candidate) < _candidate_sort_key(existing):
            best_by_ticker[candidate.ticker] = candidate

    ranked = sorted(best_by_ticker.values(), key=_candidate_sort_key)
    selected = ranked if limit is None else ranked[:limit]
    for rank, candidate in enumerate(selected, start=1):
        candidate.rank = rank
    return selected


def _decorate_row_with_result(row: Mapping[str, Any], result: Startup9ConfirmResult) -> dict[str, Any]:
    row_dict = dict(row or {})
    row_dict["ticker"] = result.ticker or _ticker(row_dict)
    row_dict["startup9_confirm_count"] = result.confirm_count
    row_dict["startup9_confirm_grade"] = result.grade
    row_dict["startup9_confirm_hits"] = "+".join(result.hits)
    row_dict["startup9_confirm_missing"] = "+".join(result.missing)
    row_dict["startup9_confirm_reason"] = result.reason
    row_dict["startup9_risk_flags"] = "+".join(result.risk_flags) if result.risk_flags else "특이사항 없음"
    row_dict["startup9_score"] = f"{result.startup9_score:.1f}"
    row_dict["startup9_confirm_map"] = dict(result.confirm_map)
    row_dict["startup9_confirm_keys"] = list(result.confirm_keys)
    row_dict["startup9_missing_keys"] = list(result.missing_keys)
    row_dict["startup9_profile"] = result.profile
    row_dict["startup9_direction_state"] = result.direction_state
    row_dict["startup9_hard_exclusions"] = list(result.hard_exclusions)
    row_dict["startup9_soft_risk_flags"] = list(result.soft_risk_flags)
    if result.rank:
        row_dict["startup9_rank"] = result.rank
    return row_dict


def annotate_rows_with_startup9_confirm(
    rows: Iterable[Mapping[str, Any]],
    target_date: date,
) -> list[dict[str, Any]]:
    annotated: list[dict[str, Any]] = []
    for row in rows or []:
        row_dict = dict(row or {})
        result = evaluate_startup9_confirm(row_dict, target_date)
        annotated.append(_decorate_row_with_result(row_dict, result))
    return annotated


def select_startup9_confirm_rows(
    rows: Iterable[Mapping[str, Any]],
    target_date: date,
    limit: int = STARTUP9_CONFIRM_LIMIT,
) -> list[dict[str, Any]]:
    row_list = [dict(row or {}) for row in rows or []]
    candidates = rank_startup9_confirm_candidates(row_list, target_date, limit=limit)
    source_by_ticker = {_ticker(row): row for row in row_list if _ticker(row)}
    return [
        _decorate_row_with_result(source_by_ticker.get(candidate.ticker, {"ticker": candidate.ticker}), candidate)
        for candidate in candidates
    ]
