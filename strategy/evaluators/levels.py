from __future__ import annotations

from ..models import StrategyDefinition, StrategyResult
from ..risk import breakout_invalidation_text, risk_template_breakout
from .common import build_result_from_groups, side


def evaluate_poc_rotation(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    structure = state["structure"]
    volume_flow = state["volume_flow"]
    trend = state["trend"]
    momentum = state["momentum"]
    signals = state["signals"]

    setup_items = [
        (side(long_side, structure["near_vp_poc"] or structure["near_vp_val"] or structure["inside_value_area"], structure["near_vp_poc"] or structure["near_vp_vah"] or structure["inside_value_area"]), "POC / Value Area 근접", 15),
        (side(long_side, signals["VP_VAL_Support"] or trend["close_above_vwap"], signals["VP_VAH_Resistance"] or trend["close_below_vwap"]), "Value Area 지지/저항 확인", 10),
        (side(long_side, volume_flow["volume_support"], volume_flow["volume_support"]), "회전 매매용 거래량 유지", 8),
        (side(long_side, volume_flow["money_flow_improving"], volume_flow["money_flow_weakening"]), "수급 방향 일치", 7),
    ]
    trigger_items = [
        (side(long_side, signals["Volume_POC_Breakout"] or (structure["near_vp_poc"] and trend["close_above_vwap"]), signals["Volume_POC_Breakdown"] or (structure["near_vp_poc"] and trend["close_below_vwap"])), "POC 재장악 / 이탈", 15),
        (side(long_side, momentum["macd_hist_rising"], momentum["macd_hist_falling"]), "회전 모멘텀 확인", 10),
        (side(long_side, volume_flow["volume_burst"] or signals["VP_VAL_Support"], volume_flow["volume_burst"] or signals["VP_VAH_Resistance"]), "Value Area 리액션 동반", 10),
    ]
    return build_result_from_groups(
        definition,
        state,
        long_side,
        "poc_rotation",
        setup_items,
        trigger_items,
        trigger_threshold=18,
        setup_threshold=18,
        triggered_phase="POC_RECLAIM_CONFIRMED",
        ready_phase="VALUE_ROTATION_READY",
        risk_template=risk_template_breakout,
        invalidation_builder=breakout_invalidation_text,
    )
