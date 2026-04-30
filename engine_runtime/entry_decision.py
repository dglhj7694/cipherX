from __future__ import annotations

import math
from typing import Any, Mapping

import pandas as pd


BUY_DIRECTION_LABELS = {"STRONG_BUY", "BUY", "WATCH_BUY"}
SELL_DIRECTION_LABELS = {"STRONG_SELL", "SELL", "WATCH_SELL"}

ENTRY_DECISION_FIELDS: tuple[str, ...] = (
    "direction_judgment",
    "entry_judgment",
    "risk_judgment",
    "position_action",
    "final_entry_score_v2",
    "trend_quality_score",
    "entry_timing_score",
    "volume_flow_score",
    "risk_penalty_score",
    "rr_score",
    "entry_chase_risk",
    "nearest_support",
    "nearest_resistance",
    "entry_zone_low",
    "entry_zone_high",
    "invalidation_level",
    "invalidation_text",
    "target_1",
    "target_2",
    "rr",
    "entry_reason",
    "risk_notes",
)

ADJUSTED_DECISION_FIELDS: tuple[str, ...] = (
    "final_adjusted_score",
    "final_adjusted_confidence",
    "final_adjustment_reasons",
)


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except Exception:
        return False


def _is_finite_number(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return default
    return numeric if math.isfinite(numeric) else default


def _optional_float(value: Any) -> float | None:
    if _is_missing(value):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if _is_missing(value):
        return False
    text = str(value).strip().lower()
    if text in {"y", "yes", "true", "1", "t"}:
        return True
    if text in {"n", "no", "false", "0", "", "-", "none", "n/a"}:
        return False
    return bool(value)


def _get(row: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in row:
            value = row.get(key)
            if not _is_missing(value):
                return value
    return default


def _num(row: Mapping[str, Any], *keys: str, default: float = 0.0) -> float:
    return _safe_float(_get(row, *keys, default=default), default)


def _opt_num(row: Mapping[str, Any], *keys: str) -> float | None:
    for key in keys:
        if key in row:
            value = _optional_float(row.get(key))
            if value is not None:
                return value
    return None


def _bool_any(row: Mapping[str, Any], *keys: str) -> bool:
    return any(_truthy(_get(row, key, default=False)) for key in keys)


def _clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def _round_or_none(value: float | None, digits: int = 4) -> float | None:
    if value is None or not math.isfinite(float(value)):
        return None
    return round(float(value), digits)


def _first_positive_below(price: float, values: list[float | None]) -> float | None:
    candidates = [float(value) for value in values if value is not None and math.isfinite(float(value)) and float(value) > 0 and float(value) <= price]
    return max(candidates) if candidates else None


def _first_positive_above(price: float, values: list[float | None]) -> float | None:
    candidates = [float(value) for value in values if value is not None and math.isfinite(float(value)) and float(value) > 0 and float(value) >= price]
    return min(candidates) if candidates else None


def compute_direction_judgment(row: Mapping[str, Any]) -> str:
    label = str(_get(row, "Trade_Judgment", "trade_judgment", "jg_key", "judgment", default="NEUTRAL") or "NEUTRAL").strip().upper()
    if label in BUY_DIRECTION_LABELS:
        return "BUY"
    if label in SELL_DIRECTION_LABELS:
        return "SELL"
    return "NEUTRAL"


def _risk_flags(row: Mapping[str, Any]) -> dict[str, bool]:
    conflict = str(_get(row, "strategy_conflict_level", "Strategy_Conflict_Level", default="") or "").strip().upper()
    chg = _num(row, "chg", "Change_Pct", default=0.0)
    chg_5d = _num(row, "chg_5d", "Change_5D", default=0.0)
    zscore20 = _num(row, "zscore20", "ZScore20", default=0.0)
    bb_percent_b = _num(row, "bb_percent_b", "Percent_B", default=0.0)
    dist_bb_upper = _num(row, "dist_bb_upper_pct", "Dist_BB_Upper_Pct", default=-999.0)
    near_52w = _bool_any(row, "near_52w_high_2pct", "Near_52W_High_2Pct")
    sell_turn = _bool_any(
        row,
        "same_session_sell_turn",
        "latest_session_utbot_sell_turn",
        "latest_session_hull_sell_turn",
        "UTBot_Sell",
        "Hull_Turn_Bear",
        "System_Turn_Bear",
        "system_turn_bear",
    )
    hma_short = _bool_any(row, "hma_ema_short_entry", "hma_ema_short_aligned", "HMA_EMA_Short_Entry", "HMA_EMA_Short_Aligned")
    entry_chase = bool(
        chg >= 12.0
        or chg_5d >= 20.0
        or (near_52w and chg >= 8.0)
        or zscore20 >= 2.5
        or bb_percent_b >= 1.0
        or dist_bb_upper >= 0.0
    )
    return {
        "high_conflict": conflict == "HIGH",
        "medium_conflict": conflict == "MEDIUM",
        "low_conflict": conflict == "LOW" or _bool_any(row, "low_conflict_bullish", "Low_Conflict_Bullish"),
        "sell_turn": sell_turn,
        "thin_trade": _bool_any(row, "thin_trade_risk", "Thin_Trade_Risk"),
        "bearish_gap_failure": _bool_any(row, "bearish_gap_failure", "Bearish_Gap_Failure"),
        "hma_short_conflict": hma_short,
        "multi_sell": _num(row, "multi_sell", "Multi_Sell", default=0.0) >= 2.0,
        "entry_chase_risk": entry_chase,
        "extreme_chase": chg >= 20.0 or chg_5d >= 30.0 or zscore20 >= 3.5,
        "mild_extension": chg >= 8.0 or chg_5d >= 15.0 or zscore20 >= 2.0 or _num(row, "dist_sma20_pct", "Dist_SMA20_Pct", default=0.0) >= 12.0,
        "low_volume": _num(row, "volume_ratio_20", "Volume_Ratio_20", default=0.0) < 1.0,
    }


def _has_hard_risk(flags: Mapping[str, bool]) -> bool:
    return bool(
        flags.get("sell_turn")
        or flags.get("thin_trade")
        or flags.get("bearish_gap_failure")
        or flags.get("hma_short_conflict")
        or flags.get("multi_sell")
    )


def _is_breakout_wait(row: Mapping[str, Any]) -> bool:
    compression = bool(
        _bool_any(row, "gap_setup_candidate", "Gap_Setup_Candidate")
        or _bool_any(row, "nr7_flag", "NR7")
        or _bool_any(row, "inside_day_flag", "Inside_Day")
        or _bool_any(row, "three_weeks_tight", "Three_Weeks_Tight")
        or (
            _bool_any(row, "atr_contracting", "ATR_Contracting")
            and 0.55 <= _num(row, "bb_percent_b", "Percent_B", default=0.0) <= 0.90
        )
        or (
            _bool_any(row, "near_52w_high_2pct", "Near_52W_High_2Pct")
            and _num(row, "breakout_dist_20d_high_pct", "Breakout_Dist_20D_High_Pct", default=-999.0) >= -2.0
        )
    )
    confirmed = _bool_any(
        row,
        "CS_Breakout_Confirm_Buy",
        "Box_Breakout_Bull",
        "Channel_Breakout_Bull",
        "Triangle_Breakout_Bull",
        "BB_Upper_Break",
        "New_52W_High",
        "new_52w_high",
    )
    return bool(compression and not confirmed)


def compute_trade_plan(row: Mapping[str, Any]) -> dict[str, Any]:
    direction = compute_direction_judgment(row)
    price = _opt_num(row, "price", "Close", "close")
    atr = _num(row, "atr", "ATR", default=0.0)

    existing_rr = _opt_num(row, "rr", "RR")
    if existing_rr is None:
        existing_rr = _opt_num(row, "vp_long_rr", "VP_Long_RR") if direction != "SELL" else _opt_num(row, "vp_short_rr", "VP_Short_RR")

    if price is None or price <= 0:
        return {
            "nearest_support": None,
            "nearest_resistance": None,
            "entry_zone_low": None,
            "entry_zone_high": None,
            "invalidation_level": None,
            "invalidation_text": "",
            "target_1": None,
            "target_2": None,
            "rr": _round_or_none(existing_rr),
            "entry_reason": "",
            "risk_notes": "",
        }

    supports = [
        _opt_num(row, "entry_zone_low", "Entry_Zone_Low"),
        _opt_num(row, "invalidation_level", "Invalidation_Level"),
        _opt_num(row, "hma_ema_long_virtual_stop", "HMA_EMA_Long_Virtual_Stop"),
        _opt_num(row, "MA20", "ma20"),
        _opt_num(row, "EMA21", "ema21"),
        _opt_num(row, "EMA25", "ema25"),
        _opt_num(row, "EMA50", "ema50"),
        _opt_num(row, "MA50", "ma50"),
        _opt_num(row, "VP_VAL", "vp_val"),
        _opt_num(row, "VP_POC", "vp_poc"),
        _opt_num(row, "Fib_382", "fib_382"),
        _opt_num(row, "Fib_50", "fib_50"),
        _opt_num(row, "Fib_618", "fib_618"),
        _opt_num(row, "Price_Channel_Low", "price_channel_low"),
        _opt_num(row, "BB_Low", "bb_low"),
    ]
    resistances = [
        _opt_num(row, "entry_zone_high", "Entry_Zone_High"),
        _opt_num(row, "target_1", "Target_1"),
        _opt_num(row, "hma_ema_long_target_2r", "HMA_EMA_Long_Target_2R"),
        _opt_num(row, "BB_Up", "bb_up"),
        _opt_num(row, "Price_Channel_Up", "price_channel_up"),
        _opt_num(row, "VP_VAH", "vp_vah"),
        _opt_num(row, "Fib_Ext_1618_Up", "fib_ext_1618_up"),
        _opt_num(row, "Fib_382", "fib_382"),
        _opt_num(row, "Fib_50", "fib_50"),
        _opt_num(row, "Fib_618", "fib_618"),
    ]
    nearest_support = _first_positive_below(price, supports)
    nearest_resistance = _first_positive_above(price, resistances)

    entry_zone_low = _opt_num(row, "entry_zone_low", "Entry_Zone_Low")
    entry_zone_high = _opt_num(row, "entry_zone_high", "Entry_Zone_High")
    if direction == "BUY" and entry_zone_low is None and nearest_support is not None:
        entry_zone_low = nearest_support
        gap = max(price - nearest_support, 0.0)
        entry_zone_high = nearest_support + (gap * 0.35) if gap > 0 else nearest_support

    invalidation_level = _opt_num(row, "invalidation_level", "Invalidation_Level")
    if direction == "BUY" and invalidation_level is None and nearest_support is not None:
        buffer_value = atr * 0.5 if atr > 0 else nearest_support * 0.03
        invalidation_level = max(0.0, nearest_support - buffer_value)

    target_1 = _opt_num(row, "target_1", "Target_1")
    if direction == "BUY" and target_1 is None:
        target_1 = nearest_resistance
    target_2 = _opt_num(row, "target_2", "Target_2")
    if direction == "BUY" and target_2 is None and price > 0 and invalidation_level is not None:
        risk = max(price - invalidation_level, 0.0)
        fallback_target_1 = price + (risk * 1.5) if risk > 0 else None
        if target_1 is None:
            target_1 = fallback_target_1
        target_2 = price + (risk * 2.0) if risk > 0 else None

    rr = existing_rr
    if rr is None and direction == "BUY" and target_1 is not None and invalidation_level is not None:
        risk = price - invalidation_level
        reward = target_1 - price
        if risk > 0 and reward > 0:
            rr = reward / risk

    invalidation_text = ""
    if invalidation_level is not None:
        invalidation_text = f"{invalidation_level:.2f} breakdown"

    return {
        "nearest_support": _round_or_none(nearest_support),
        "nearest_resistance": _round_or_none(nearest_resistance),
        "entry_zone_low": _round_or_none(entry_zone_low),
        "entry_zone_high": _round_or_none(entry_zone_high),
        "invalidation_level": _round_or_none(invalidation_level),
        "invalidation_text": invalidation_text,
        "target_1": _round_or_none(target_1),
        "target_2": _round_or_none(target_2),
        "rr": _round_or_none(rr, 2),
        "entry_reason": "",
        "risk_notes": "",
    }


def _score_context(row: Mapping[str, Any], rr: float | None, flags: Mapping[str, bool], direction: str) -> dict[str, float]:
    trend = 0.0
    if direction == "BUY":
        trend += 20.0
    if _bool_any(row, "uptrend_persistent", "Uptrend_Persistent"):
        trend += 18.0
    if _bool_any(row, "strong_trend_persistent", "Strong_Trend_Persistent"):
        trend += 14.0
    if _bool_any(row, "bull_strength_recent", "Bull_Strength_Recent"):
        trend += 12.0
    if _bool_any(row, "hma_ema_long_entry", "HMA_EMA_Long_Entry"):
        trend += 14.0
    elif _bool_any(row, "hma_ema_long_aligned", "HMA_EMA_Long_Aligned"):
        trend += 9.0
    if _num(row, "adx", "ADX", default=0.0) >= 25.0:
        trend += 10.0
    elif _num(row, "adx", "ADX", default=0.0) >= 20.0:
        trend += 6.0
    if flags.get("low_conflict"):
        trend += 12.0

    timing = 0.0
    if _bool_any(row, "latest_session_utbot_buy_turn", "latest_session_hull_buy_turn", "UTBot_Buy", "Hull_Turn_Bull", "System_Turn_Bull"):
        timing += 25.0
    if _bool_any(row, "hma_ema_long_entry", "HMA_EMA_Long_Entry"):
        timing += 20.0
    if _bool_any(row, "first_close_above_ma20_after_5bars", "First_Close_Above_MA20_After_5Bars"):
        timing += 15.0
    if _bool_any(row, "pullback_ready", "pullback_reentry", "Pullback_Ready", "Pullback_Reentry"):
        timing += 15.0
    if _bool_any(row, "pocket_pivot_candidate", "Pocket_Pivot_Candidate"):
        timing += 10.0
    if _bool_any(row, "final_entry_eligible", "final_entry_selected"):
        timing += 10.0
    if flags.get("entry_chase_risk"):
        timing -= 20.0

    volume_ratio = _num(row, "volume_ratio_20", "Volume_Ratio_20", default=0.0)
    volume = 10.0 if volume_ratio < 0.8 else 30.0 if volume_ratio < 1.0 else 45.0 if volume_ratio < 1.2 else 60.0 if volume_ratio < 1.5 else 75.0 if volume_ratio < 2.0 else 88.0
    if _num(row, "cmf", "CMF", default=0.0) > 0.05:
        volume += 6.0
    if _num(row, "obv_slope", "OBV_Slope", default=0.0) > 0.1:
        volume += 6.0

    rr_score = 0.0
    if rr is not None:
        if rr >= 3.0:
            rr_score = 100.0
        elif rr >= 2.0:
            rr_score = 80.0
        elif rr >= 1.5:
            rr_score = 65.0
        elif rr >= 1.3:
            rr_score = 52.0
        elif rr >= 1.0:
            rr_score = 30.0
        elif rr > 0:
            rr_score = 12.0

    penalty = 0.0
    if flags.get("thin_trade"):
        penalty += 30.0
    if flags.get("bearish_gap_failure") or flags.get("sell_turn"):
        penalty += 30.0
    if flags.get("high_conflict"):
        penalty += 18.0
    elif flags.get("medium_conflict"):
        penalty += 8.0
    if flags.get("entry_chase_risk"):
        penalty += 12.0
    if flags.get("extreme_chase"):
        penalty += 12.0
    if flags.get("multi_sell") or flags.get("hma_short_conflict"):
        penalty += 20.0

    return {
        "trend_quality_score": round(_clip(trend, 0.0, 100.0), 4),
        "entry_timing_score": round(_clip(timing, 0.0, 100.0), 4),
        "volume_flow_score": round(_clip(volume, 0.0, 100.0), 4),
        "risk_penalty_score": round(_clip(penalty, 0.0, 100.0), 4),
        "rr_score": round(_clip(rr_score, 0.0, 100.0), 4),
    }


def compute_entry_judgment(row: Mapping[str, Any]) -> str:
    context = _build_context(row)
    direction = str(context["direction"])
    flags = context["flags"]
    rr = context["rr"]
    timing = float(context["scores"]["entry_timing_score"])
    volume_ratio = _num(row, "volume_ratio_20", "Volume_Ratio_20", default=0.0)

    if direction == "SELL" or flags.get("sell_turn") or flags.get("bearish_gap_failure") or flags.get("hma_short_conflict") or flags.get("multi_sell"):
        return "EXIT_OR_AVOID"
    if direction != "BUY":
        return "NO_TRADE"
    if flags.get("thin_trade"):
        return "NO_TRADE"
    if flags.get("entry_chase_risk"):
        return "CHASE_RISK"
    if flags.get("mild_extension") or _bool_any(row, "pullback_reentry", "Pullback_Reentry"):
        return "WAIT_PULLBACK"
    if _is_breakout_wait(row):
        return "WAIT_BREAKOUT_CONFIRM"
    if flags.get("high_conflict") or flags.get("medium_conflict"):
        return "NO_TRADE"
    if volume_ratio < 1.0:
        return "NO_TRADE"
    if rr is not None and rr < 1.3:
        return "NO_TRADE"
    if flags.get("low_conflict") and (rr is None or rr >= 1.3) and timing >= 35.0:
        return "ENTER_NOW"
    return "NO_TRADE"


def compute_risk_judgment(row: Mapping[str, Any]) -> str:
    context = _build_context(row)
    flags = context["flags"]
    rr = context["rr"]
    volume_ratio = _num(row, "volume_ratio_20", "Volume_Ratio_20", default=0.0)

    if (
        flags.get("high_conflict")
        or flags.get("sell_turn")
        or flags.get("thin_trade")
        or flags.get("bearish_gap_failure")
        or flags.get("extreme_chase")
        or flags.get("multi_sell")
        or (rr is not None and rr < 1.0)
    ):
        return "HIGH"
    if (
        flags.get("low_conflict")
        and not _has_hard_risk(flags)
        and not flags.get("entry_chase_risk")
        and volume_ratio >= 1.0
        and (rr is not None and rr >= 1.5)
    ):
        return "LOW"
    return "MEDIUM"


def _position_action(entry_judgment: str, flags: Mapping[str, bool]) -> str:
    if entry_judgment == "ENTER_NOW":
        return "BUY_NOW"
    if entry_judgment in {"WAIT_PULLBACK", "CHASE_RISK"}:
        return "WATCHLIST"
    if entry_judgment == "WAIT_BREAKOUT_CONFIRM":
        return "WAIT"
    if entry_judgment == "EXIT_OR_AVOID":
        return "SELL_OR_EXIT"
    if flags.get("thin_trade") or _has_hard_risk(flags):
        return "AVOID"
    return "WAIT"


def _reason_text(row: Mapping[str, Any], entry_judgment: str, flags: Mapping[str, bool]) -> str:
    parts: list[str] = []
    if _bool_any(row, "hma_ema_long_entry", "HMA_EMA_Long_Entry"):
        parts.append("HMA/EMA long entry")
    elif _bool_any(row, "hma_ema_long_aligned", "HMA_EMA_Long_Aligned"):
        parts.append("HMA/EMA aligned")
    if flags.get("low_conflict"):
        parts.append("low conflict")
    if _num(row, "volume_ratio_20", "Volume_Ratio_20", default=0.0) >= 1.0:
        parts.append(f"volume {_num(row, 'volume_ratio_20', 'Volume_Ratio_20', default=0.0):.2f}x")
    if _is_breakout_wait(row):
        parts.append("breakout confirmation pending")
    if entry_judgment == "CHASE_RISK":
        parts.append("short-term extension")
    if entry_judgment == "WAIT_PULLBACK":
        parts.append("pullback preferred")
    return " + ".join(parts[:4])


def _risk_notes(flags: Mapping[str, bool]) -> str:
    notes = []
    for key, label in (
        ("thin_trade", "thin_trade_risk"),
        ("bearish_gap_failure", "bearish_gap_failure"),
        ("sell_turn", "sell_turn"),
        ("high_conflict", "high_conflict"),
        ("medium_conflict", "medium_conflict"),
        ("entry_chase_risk", "entry_chase_risk"),
        ("extreme_chase", "extreme_chase"),
        ("multi_sell", "multi_sell"),
        ("hma_short_conflict", "hma_ema_short_conflict"),
        ("low_volume", "low_volume"),
    ):
        if flags.get(key):
            notes.append(label)
    return "+".join(notes)


def _build_context(row: Mapping[str, Any]) -> dict[str, Any]:
    direction = compute_direction_judgment(row)
    flags = _risk_flags(row)
    plan = compute_trade_plan(row)
    rr = _optional_float(plan.get("rr"))
    scores = _score_context(row, rr, flags, direction)
    return {"direction": direction, "flags": flags, "plan": plan, "rr": rr, "scores": scores}


def compute_entry_decision_row(row: Mapping[str, Any]) -> dict[str, Any]:
    context = _build_context(row)
    direction = str(context["direction"])
    flags = context["flags"]
    plan = dict(context["plan"])
    scores = dict(context["scores"])
    entry_judgment = compute_entry_judgment(row)
    risk_judgment = compute_risk_judgment(row)
    position_action = _position_action(entry_judgment, flags)
    final_entry_score_v2 = (
        scores["trend_quality_score"] * 0.35
        + scores["entry_timing_score"] * 0.30
        + scores["volume_flow_score"] * 0.20
        + scores["rr_score"] * 0.15
        - scores["risk_penalty_score"]
    )

    plan["entry_reason"] = _reason_text(row, entry_judgment, flags)
    plan["risk_notes"] = _risk_notes(flags)

    return {
        "direction_judgment": direction,
        "entry_judgment": entry_judgment,
        "risk_judgment": risk_judgment,
        "position_action": position_action,
        "final_entry_score_v2": round(_clip(final_entry_score_v2, 0.0, 100.0), 4),
        **scores,
        "entry_chase_risk": bool(flags.get("entry_chase_risk")),
        **plan,
    }


def compute_adjusted_decision_fields(row: Mapping[str, Any]) -> dict[str, Any]:
    return _adjustment_payload(row)


def _adjustment_payload(row: Mapping[str, Any]) -> dict[str, Any]:
    score = _num(row, "Final_Decision_Score", "final_decision_score", "Ensemble_Score", "es", default=0.0)
    confidence = _num(row, "Judgment_Confidence", "cf", "confidence", default=0.0)
    adjusted_score = score
    adjusted_confidence = confidence
    reasons: list[str] = []

    downgrade = int(_num(row, "Downgrade_Count", "downgrade_count", default=0.0))
    if downgrade > 0:
        adjusted_score -= downgrade * 8.0
        adjusted_confidence -= downgrade * 5.0
        reasons.append(f"downgrade_count:{downgrade}")

    contrast = str(_get(row, "Contrast_Notes", "contrast_notes", default="") or "")
    objective_alignment = str(_get(row, "Objective_Alignment", "objective_alignment", default="") or "").upper()
    if "OBJECTIVE CONFLICT" in contrast.upper() or objective_alignment == "CONFLICT":
        adjusted_score -= 10.0
        adjusted_confidence -= 10.0
        reasons.append("objective_conflict")

    if _bool_any(row, "Leading_Noise_Block", "leading_noise_block"):
        adjusted_score *= 0.75
        adjusted_confidence -= 8.0
        reasons.append("leading_noise_block")

    macro_risk_off = int(_num(row, "Macro_Risk_Off_Count", "macro_risk_off_count", default=0.0))
    if macro_risk_off > 0:
        adjusted_score -= macro_risk_off * 3.0
        adjusted_confidence -= macro_risk_off * 3.0
        reasons.append(f"macro_risk_off:{macro_risk_off}")

    flags = _risk_flags(row)
    if flags.get("high_conflict"):
        adjusted_score -= 10.0
        adjusted_confidence -= 10.0
        reasons.append("high_conflict")
    if flags.get("entry_chase_risk"):
        adjusted_score -= 5.0
        reasons.append("entry_chase_risk")
    if _has_hard_risk(flags):
        adjusted_score -= 20.0
        reasons.append("hard_risk")

    return {
        "final_adjusted_score": round(adjusted_score, 4),
        "final_adjusted_confidence": round(_clip(adjusted_confidence, 0.0, 100.0), 4),
        "final_adjustment_reasons": "+".join(reasons),
    }


def apply_entry_decision_fields(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    rows = [compute_entry_decision_row(row) for _, row in df.iterrows()]
    for field in ENTRY_DECISION_FIELDS:
        df[field] = [row.get(field) for row in rows]
    return df


def apply_adjusted_decision_fields(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    rows = [_adjustment_payload(row) for _, row in df.iterrows()]
    for field in ADJUSTED_DECISION_FIELDS:
        df[field] = [row.get(field) for row in rows]
    return df
