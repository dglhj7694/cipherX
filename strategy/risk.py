from __future__ import annotations

import numpy as np

from .state_builder import ordered_unique


def rr(entry: float, stop_loss: float | None, target_1: float | None) -> float | None:
    if stop_loss is None or target_1 is None:
        return None
    risk = abs(entry - stop_loss)
    reward = abs(target_1 - entry)
    if risk <= 1e-9:
        return None
    return reward / risk


def risk_template_trend(state: dict, long_side: bool) -> tuple[float | None, float | None, float | None, float | None]:
    entry = state["price"]["entry"]
    atr = state["price"]["atr"]
    ma50 = state["price"]["ma50"]
    swing_low = state["structure"]["swing_low_5"]
    swing_high = state["structure"]["swing_high_5"]
    prev_extreme_high = state["structure"]["swing_high_20"]
    prev_extreme_low = state["structure"]["swing_low_20"]
    channel_up = state["price"]["price_channel_up"]
    channel_low = state["price"]["price_channel_low"]
    if long_side:
        stop_loss = min(swing_low, ma50) - (0.3 * atr)
        target_1 = max(prev_extreme_high, entry + (1.2 * atr))
        target_2 = max(channel_up, entry + (2.0 * atr))
    else:
        stop_loss = max(swing_high, ma50) + (0.3 * atr)
        target_1 = min(prev_extreme_low, entry - (1.2 * atr))
        target_2 = min(channel_low, entry - (2.0 * atr))
    return stop_loss, target_1, target_2, rr(entry, stop_loss, target_1)


def risk_template_breakout(state: dict, long_side: bool) -> tuple[float | None, float | None, float | None, float | None]:
    entry = state["price"]["entry"]
    atr = state["price"]["atr"]
    breakout_level = state["structure"]["breakout_level"]
    breakdown_level = state["structure"]["breakdown_level"]
    latest_low = state["price"]["low"]
    latest_high = state["price"]["high"]
    channel_up = state["price"]["price_channel_up"]
    channel_low = state["price"]["price_channel_low"]
    if long_side:
        stop_loss = min(breakout_level, latest_low) - (0.5 * atr)
        target_1 = entry + (1.5 * atr)
        target_2 = max(channel_up, entry + (2.5 * atr))
    else:
        stop_loss = max(breakdown_level, latest_high) + (0.5 * atr)
        target_1 = entry - (1.5 * atr)
        target_2 = min(channel_low, entry - (2.5 * atr))
    return stop_loss, target_1, target_2, rr(entry, stop_loss, target_1)


def risk_template_reversal(state: dict, long_side: bool) -> tuple[float | None, float | None, float | None, float | None]:
    entry = state["price"]["entry"]
    atr = state["price"]["atr"]
    swing_low = state["structure"]["swing_low_5"]
    swing_high = state["structure"]["swing_high_5"]
    vwap = state["levels"]["vwap"]
    ema21 = state["levels"]["ema21"]
    prev_extreme_high = state["structure"]["swing_high_20"]
    prev_extreme_low = state["structure"]["swing_low_20"]
    if long_side:
        stop_loss = swing_low - (0.5 * atr)
        target_1 = max(vwap, ema21, entry + (1.0 * atr))
        target_2 = max(prev_extreme_high, entry + (2.0 * atr))
    else:
        stop_loss = swing_high + (0.5 * atr)
        target_1 = min(vwap, ema21, entry - (1.0 * atr))
        target_2 = min(prev_extreme_low, entry - (2.0 * atr))
    return stop_loss, target_1, target_2, rr(entry, stop_loss, target_1)


def risk_score(stop_loss: float | None, target_1: float | None, entry: float, rr_value: float | None, conflicts: list[str]) -> float:
    if stop_loss is None or target_1 is None:
        return 0.0
    score = 5.0
    if rr_value is not None:
        if rr_value >= 2.0:
            score += 10.0
        elif rr_value >= 1.5:
            score += 8.0
        elif rr_value >= 1.3:
            score += 6.0
        elif rr_value >= 1.0:
            score += 3.0
    stop_gap = abs(entry - stop_loss) / max(entry, 0.01)
    if stop_gap <= 0.08:
        score += 5.0
    elif stop_gap <= 0.12:
        score += 3.0
    elif stop_gap <= 0.2:
        score += 1.0
    penalty = min(len(conflicts) * 2.5, 10.0)
    return max(0.0, min(20.0, score - penalty))


def default_conflicts(state: dict, long_side: bool) -> list[str]:
    conflicts: list[str] = []
    price = state["price"]
    levels = state["levels"]
    trend = state["trend"]
    patterns = state["patterns"]
    atr = price["atr"]
    close = price["close"]
    nearest_resistance = levels["nearest_resistance"]
    nearest_support = levels["nearest_support"]
    if long_side:
        if np.isfinite(nearest_resistance) and (nearest_resistance - close) <= atr:
            conflicts.append("가까운 저항대가 1 ATR 안쪽에 있습니다.")
        if patterns["bearish_divergence"]:
            conflicts.append("반대 방향 다이버전스가 남아 있습니다.")
        if trend["bearish_trend_stack"] and trend["close_below_vwap"]:
            conflicts.append("상위 추세가 아직 완전히 상방으로 돌지 않았습니다.")
    else:
        if np.isfinite(nearest_support) and (close - nearest_support) <= atr:
            conflicts.append("가까운 지지대가 1 ATR 안쪽에 있습니다.")
        if patterns["bullish_divergence"]:
            conflicts.append("반대 방향 다이버전스가 남아 있습니다.")
        if trend["bullish_trend_stack"] and trend["close_above_vwap"]:
            conflicts.append("상위 추세가 아직 완전히 하방으로 돌지 않았습니다.")
    if state["signals"].get("CS_Conflict_Warning"):
        conflicts.append("기존 엔진도 방향 충돌을 경고하고 있습니다.")
    return ordered_unique(conflicts)


def trend_invalidation_text(state: dict, long_side: bool, stop_loss: float | None) -> str:
    if stop_loss is None:
        return "핵심 지지/저항 이탈 시 무효"
    if long_side:
        return f"EMA50 또는 최근 스윙로우 하향 이탈 시 무효 ({stop_loss:.2f} 아래)."
    return f"EMA50 또는 최근 스윙하이 상향 회복 시 무효 ({stop_loss:.2f} 위)."


def breakout_invalidation_text(state: dict, long_side: bool, stop_loss: float | None) -> str:
    level = state["structure"]["breakout_level"] if long_side else state["structure"]["breakdown_level"]
    if stop_loss is None:
        return "돌파/이탈 레벨 재진입 시 무효"
    if long_side:
        return f"돌파 레벨 {level:.2f} 재이탈 또는 {stop_loss:.2f} 하향 시 무효."
    return f"이탈 레벨 {level:.2f} 재회복 또는 {stop_loss:.2f} 상향 시 무효."


def reversal_invalidation_text(state: dict, long_side: bool, stop_loss: float | None) -> str:
    if stop_loss is None:
        return "직전 저점/고점 이탈 시 무효"
    if long_side:
        return f"직전 저점 또는 {stop_loss:.2f} 이탈 시 반전 시나리오 무효."
    return f"직전 고점 또는 {stop_loss:.2f} 회복 시 반전 시나리오 무효."
