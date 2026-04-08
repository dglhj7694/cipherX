from __future__ import annotations

from ..models import StrategyDefinition, StrategyResult
from ..risk import default_conflicts, reversal_invalidation_text, risk_template_reversal
from .common import build_result, build_result_from_groups, score_group, side


def evaluate_reversal_cluster(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    trend = state["trend"]
    structure = state["structure"]
    volume_flow = state["volume_flow"]
    momentum = state["momentum"]
    patterns = state["patterns"]
    signals = state["signals"]

    setup_items = [
        (side(long_side, momentum["deep_oversold"] or structure["price_change_5"] <= -5.0, momentum["deep_overbought"] or structure["price_change_5"] >= 5.0), "과매도 / 과매수 스트레치", 15),
        (side(long_side, structure["lower_zone"], structure["upper_zone"]), "밴드/구조 하단 접근", 10),
        (side(long_side, patterns["bullish_divergence"] or volume_flow["money_flow_improving"], patterns["bearish_divergence"] or volume_flow["money_flow_weakening"]), "다이버전스 또는 자금흐름 개선", 12),
        (side(long_side, trend["bearish_trend_stack"] or trend["close_below_vwap"], trend["bullish_trend_stack"] or trend["close_above_vwap"]), "추세 말단 / 반전 후보 구간", 8),
    ]
    trigger_items = [
        (side(long_side, patterns["bullish_reversal_candle"] or patterns["volume_climax_buy"] or patterns["parabolic_bottom"], patterns["bearish_reversal_candle"] or patterns["volume_climax_sell"] or patterns["parabolic_top"]), "반전 캔들 또는 클라이맥스", 15),
        (side(long_side, momentum["macd_hist_rising"] and momentum["wt_rising"], momentum["macd_hist_falling"] and momentum["wt_falling"]), "모멘텀 개선", 10),
        (side(long_side, signals["VWAP_Bounce_Buy"] or trend["close_above_vwap"] or signals["UTBot_Buy"] or signals["Hull_Turn_Bull"], signals["VWAP_Reject_Sell"] or trend["close_below_vwap"] or signals["UTBot_Sell"] or signals["Hull_Turn_Bear"]), "기준선 / 확인 신호 회복", 10),
    ]
    setup_score, setup_matched, setup_missing = score_group(setup_items)
    trigger_score, trigger_matched, trigger_missing = score_group(trigger_items)
    trigger_passed = trigger_score >= 20
    phase = "TRIGGERED" if trigger_passed else "REVERSAL_READY" if setup_score >= 20 else "SETUP_INVALID"
    stop_loss, target_1, target_2, rr = risk_template_reversal(state, long_side)
    conflicts = default_conflicts(state, long_side)
    if side(long_side, not trend["close_above_vwap"], not trend["close_below_vwap"]):
        conflicts.append("기준선 회복/재이탈 확인이 더 필요합니다.")
    return build_result(
        definition=definition,
        state=state,
        long_side=long_side,
        family="reversal",
        setup_score=setup_score,
        trigger_score=trigger_score,
        trigger_passed=trigger_passed,
        phase=phase,
        stop_loss=stop_loss,
        target_1=target_1,
        target_2=target_2,
        rr=rr,
        matched=setup_matched + trigger_matched,
        missing=setup_missing + trigger_missing,
        conflict_reasons=conflicts,
        invalidation_builder=reversal_invalidation_text,
    )


def evaluate_obv_divergence(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    trend = state["trend"]
    structure = state["structure"]
    volume_flow = state["volume_flow"]
    momentum = state["momentum"]
    patterns = state["patterns"]
    signals = state["signals"]

    setup_items = [
        (side(long_side, patterns["obv_div_buy"], patterns["obv_div_sell"]), "OBV / 스마트머니 다이버전스", 20),
        (side(long_side, structure["lower_zone"] or structure["price_change_5"] <= -4.0, structure["upper_zone"] or structure["price_change_5"] >= 4.0), "가격은 극단 구간 접근", 10),
        (side(long_side, volume_flow["money_flow_improving"], volume_flow["money_flow_weakening"]), "자금흐름 보조 확인", 5),
        (side(long_side, momentum["oversold"], momentum["overbought"]), "오실레이터 극단 구간", 10),
    ]
    trigger_items = [
        (side(long_side, patterns["bullish_reversal_candle"], patterns["bearish_reversal_candle"]), "확인 트리거 캔들", 15),
        (side(long_side, signals["VWAP_Bounce_Buy"] or state["price"]["close"] >= state["price"]["ema8"] or trend["close_above_vwap"], signals["VWAP_Reject_Sell"] or state["price"]["close"] <= state["price"]["ema8"] or trend["close_below_vwap"]), "VWAP / EMA8 회복", 10),
        (side(long_side, signals["UTBot_Buy"] or momentum["macd_hist_rising"], signals["UTBot_Sell"] or momentum["macd_hist_falling"]), "보조 모멘텀 확인", 10),
    ]
    setup_score, setup_matched, setup_missing = score_group(setup_items)
    trigger_score, trigger_matched, trigger_missing = score_group(trigger_items)
    trigger_passed = trigger_score >= 15
    phase = "DIVERGENCE_CONFIRMED" if trigger_passed else "DIVERGENCE_READY" if setup_score >= 20 else "SETUP_INVALID"
    stop_loss, target_1, target_2, rr = risk_template_reversal(state, long_side)
    conflicts = default_conflicts(state, long_side)
    if side(long_side, not trend["close_above_vwap"], not trend["close_below_vwap"]):
        conflicts.append("다이버전스 이후 기준선 확인이 아직 약합니다.")
    return build_result(
        definition=definition,
        state=state,
        long_side=long_side,
        family="obv_divergence",
        setup_score=setup_score,
        trigger_score=trigger_score,
        trigger_passed=trigger_passed,
        phase=phase,
        stop_loss=stop_loss,
        target_1=target_1,
        target_2=target_2,
        rr=rr,
        matched=setup_matched + trigger_matched,
        missing=setup_missing + trigger_missing,
        conflict_reasons=conflicts,
        invalidation_builder=reversal_invalidation_text,
    )


def evaluate_keltner_mean_reversion(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    structure = state["structure"]
    volume_flow = state["volume_flow"]
    momentum = state["momentum"]
    patterns = state["patterns"]
    signals = state["signals"]
    trend = state["trend"]

    setup_items = [
        (side(long_side, structure["outside_keltner_lower"], structure["outside_keltner_upper"]), "Keltner 외곽 과확장", 15),
        (side(long_side, momentum["deep_oversold"], momentum["deep_overbought"]), "오실레이터 극단 구간", 10),
        (side(long_side, volume_flow["money_flow_improving"], volume_flow["money_flow_weakening"]), "자금흐름 개선", 10),
        (side(long_side, structure["price_change_5"] <= -3.0, structure["price_change_5"] >= 3.0), "단기 과매도/과매수 확인", 10),
    ]
    trigger_items = [
        (side(long_side, patterns["bullish_reversal_candle"] or patterns["volume_climax_buy"], patterns["bearish_reversal_candle"] or patterns["volume_climax_sell"]), "반전 캔들 확인", 15),
        (side(long_side, state["price"]["close"] >= state["price"]["kc_mid"] or signals["VWAP_Bounce_Buy"], state["price"]["close"] <= state["price"]["kc_mid"] or signals["VWAP_Reject_Sell"]), "Keltner mid 복귀", 10),
        (side(long_side, momentum["macd_hist_rising"], momentum["macd_hist_falling"]), "반전 모멘텀 개선", 10),
    ]
    extra_conflicts = ["VWAP 방향 회복이 아직 완전하지 않습니다."] if side(long_side, not trend["close_above_vwap"], not trend["close_below_vwap"]) else []
    return build_result_from_groups(
        definition,
        state,
        long_side,
        "keltner_mean_reversion",
        setup_items,
        trigger_items,
        trigger_threshold=20,
        setup_threshold=20,
        triggered_phase="TRIGGERED",
        ready_phase="MEAN_REVERSION_READY",
        risk_template=risk_template_reversal,
        invalidation_builder=reversal_invalidation_text,
        extra_conflicts=extra_conflicts,
    )


def evaluate_morning_star_fib(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    volume_flow = state["volume_flow"]
    momentum = state["momentum"]
    signals = state["signals"]
    patterns = state["patterns"]
    structure = state["structure"]

    fib_support_long = any(signals[key] for key in ("Fib_50_Support", "Fib_618_Support", "Fib_618_Reclaim", "Fib_Confluence_Buy"))
    fib_support_short = any(signals[key] for key in ("Fib_50_Resistance", "Fib_618_Resistance", "Fib_618_Breakdown", "Fib_Confluence_Sell"))
    setup_items = [
        (side(long_side, fib_support_long, fib_support_short), "Fib 0.5 / 0.618 골든존 지지", 18),
        (side(long_side, structure["lower_zone"] or structure["pullback_near_fixed_vwap_long"], structure["upper_zone"] or structure["pullback_near_fixed_vwap_short"]), "가격 구조상 되돌림 완료", 12),
        (side(long_side, volume_flow["money_flow_improving"], volume_flow["money_flow_weakening"]), "자금흐름 확인", 8),
        (side(long_side, structure["price_change_5"] < 0, structure["price_change_5"] > 0), "직전 조정 파동 존재", 7),
    ]
    trigger_items = [
        (side(long_side, patterns["morning_star"] or patterns["bullish_reversal_candle"], patterns["evening_star"] or patterns["bearish_reversal_candle"]), "패턴 캔들 완성", 15),
        (side(long_side, signals["VWAP_Bounce_Buy"] or state["price"]["close"] >= state["price"]["ema8"], signals["VWAP_Reject_Sell"] or state["price"]["close"] <= state["price"]["ema8"]), "3번째 봉 기준선 회복", 10),
        (side(long_side, momentum["macd_hist_rising"], momentum["macd_hist_falling"]), "모멘텀 개선", 10),
    ]
    return build_result_from_groups(
        definition,
        state,
        long_side,
        "morning_star_fib",
        setup_items,
        trigger_items,
        trigger_threshold=18,
        setup_threshold=20,
        triggered_phase="FIB_CONFIRM",
        ready_phase="FIB_GOLDEN_ZONE_WAIT",
        risk_template=risk_template_reversal,
        invalidation_builder=reversal_invalidation_text,
    )
