from __future__ import annotations

from .models import StrategyResult, StrategySummary


def build_summary(visible: list[StrategyResult], results: list[StrategyResult]) -> StrategySummary:
    bullish = [item for item in visible if item.direction == "LONG"]
    bearish = [item for item in visible if item.direction == "SHORT"]
    active_statuses = {"ACTIVE", "LONG_ENTRY", "SHORT_ENTRY"}
    active_count = sum(1 for item in visible if item.status in active_statuses)
    top_strategy = visible[0].to_dict() if visible else None
    secondary = [item.to_dict() for item in visible[1:3]]
    long_short_bias = "BALANCED"
    if len(bullish) > len(bearish):
        long_short_bias = "LONG"
    elif len(bearish) > len(bullish):
        long_short_bias = "SHORT"
    elif bullish and bearish:
        top_long = max(item.score for item in bullish)
        top_short = max(item.score for item in bearish)
        if top_long > top_short:
            long_short_bias = "LONG"
        elif top_short > top_long:
            long_short_bias = "SHORT"
    conflict_level = conflict_level_for(bullish, bearish)
    dominant_reasons = top_strategy.get("matched_conditions", [])[:3] if top_strategy else []
    opposing_reasons: list[str] = []
    if top_strategy:
        opposite_pool = bearish if top_strategy["direction"] == "LONG" else bullish
        if opposite_pool:
            opposing_reasons = [f"{opposite_pool[0].label} {opposite_pool[0].score:.0f}점"] + opposite_pool[0].conflict_reasons[:2]
        else:
            opposing_reasons = top_strategy.get("conflict_reasons", [])[:2]
    return StrategySummary(
        active_count=active_count,
        visible_count=len(visible),
        bullish_count=len(bullish),
        bearish_count=len(bearish),
        long_short_bias=long_short_bias,
        conflict_level=conflict_level,
        top_strategy=top_strategy,
        secondary_strategies=secondary,
        hidden_invalid_count=max(len(results) - len(visible), 0),
        dominant_reasons=dominant_reasons,
        opposing_reasons=opposing_reasons,
    )


def conflict_level_for(bullish: list[StrategyResult], bearish: list[StrategyResult]) -> str:
    if not bullish or not bearish:
        return "LOW"
    top_long = max(item.score for item in bullish)
    top_short = max(item.score for item in bearish)
    diff = abs(top_long - top_short)
    score = 1.0
    if min(len(bullish), len(bearish)) >= 2:
        score += 1.0
    if diff <= 10:
        score += 1.0
    elif diff <= 20:
        score += 0.5
    if min(top_long, top_short) >= 60:
        score += 1.0
    if score >= 3.0:
        return "HIGH"
    if score >= 1.5:
        return "MEDIUM"
    return "LOW"
