from __future__ import annotations

from ..models import StrategyDefinition, StrategyResult
from ..risk import reversal_invalidation_text, risk_template_reversal
from .common import build_result_from_groups, side


def evaluate_vwap_reclaim(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    trend = state["trend"]
    structure = state["structure"]
    volume_flow = state["volume_flow"]
    momentum = state["momentum"]
    signals = state["signals"]

    setup_items = [
        (side(long_side, structure["pullback_near_fixed_vwap_long"] or structure["pullback_near_kc_mid_long"], structure["pullback_near_fixed_vwap_short"] or structure["pullback_near_kc_mid_short"]), "VWAP / AVWAP 재테스트 구간", 12),
        (side(long_side, trend["close_above_ema21"], trend["close_below_ema21"]), "단기 추세 정렬", 10),
        (side(long_side, volume_flow["money_flow_improving"], volume_flow["money_flow_weakening"]), "수급 방향 일치", 10),
        (side(long_side, volume_flow["volume_support"], volume_flow["volume_support"]), "거래량 지지", 8),
    ]
    trigger_items = [
        (side(long_side, signals["VWAP_Bounce_Buy"] or trend["vwap_reclaimed_long"], signals["VWAP_Reject_Sell"] or trend["vwap_reclaimed_short"]), "VWAP 재장악 / 거절 확인", 15),
        (side(long_side, trend["close_above_vwap"], trend["close_below_vwap"]), "종가 기준 VWAP 우위", 10),
        (side(long_side, signals["UTBot_Buy"] or momentum["macd_hist_rising"], signals["UTBot_Sell"] or momentum["macd_hist_falling"]), "후속 확인 신호", 10),
    ]
    return build_result_from_groups(
        definition,
        state,
        long_side,
        "vwap_reclaim",
        setup_items,
        trigger_items,
        trigger_threshold=20,
        setup_threshold=18,
        triggered_phase="VWAP_RECLAIM_CONFIRMED",
        ready_phase="VWAP_RECLAIM_PENDING",
        risk_template=risk_template_reversal,
        invalidation_builder=reversal_invalidation_text,
    )


def evaluate_chaikin_flow(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    volume_flow = state["volume_flow"]
    momentum = state["momentum"]
    structure = state["structure"]
    trend = state["trend"]
    signals = state["signals"]

    setup_items = [
        (side(long_side, volume_flow["chaikin_positive"], volume_flow["chaikin_negative"]), "Chaikin 방향 전환", 15),
        (side(long_side, volume_flow["cmf_positive"], volume_flow["cmf_negative"]), "CMF 방향 동조", 10),
        (side(long_side, structure["lower_zone"] or structure["price_change_5"] <= -2.0, structure["upper_zone"] or structure["price_change_5"] >= 2.0), "가격은 아직 바닥/천장권", 10),
        (side(long_side, volume_flow["volume_support"], volume_flow["volume_support"]), "수급 유입 유지", 10),
    ]
    trigger_items = [
        (side(long_side, volume_flow["chaikin_cross_up"] or signals["CMF_Bull"], volume_flow["chaikin_cross_down"] or signals["CMF_Bear"]), "Chaikin / CMF 트리거", 15),
        (side(long_side, trend["close_above_vwap"] or state["price"]["close"] >= state["price"]["ema8"], trend["close_below_vwap"] or state["price"]["close"] <= state["price"]["ema8"]), "가격 확인 봉", 10),
        (side(long_side, momentum["macd_hist_rising"], momentum["macd_hist_falling"]), "모멘텀 개선", 10),
    ]
    return build_result_from_groups(
        definition,
        state,
        long_side,
        "chaikin_flow",
        setup_items,
        trigger_items,
        trigger_threshold=18,
        setup_threshold=18,
        triggered_phase="CHAIKIN_CONFIRMED",
        ready_phase="CHAIKIN_READY",
        risk_template=risk_template_reversal,
        invalidation_builder=reversal_invalidation_text,
    )
