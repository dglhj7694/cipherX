from __future__ import annotations

import numpy as np

from ..models import StrategyDefinition, StrategyResult
from ..risk import default_conflicts, risk_template_trend, trend_invalidation_text
from .common import build_result, build_result_from_groups, score_group, side


def evaluate_trend_pullback(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    trend = state["trend"]
    structure = state["structure"]
    volume_flow = state["volume_flow"]
    momentum = state["momentum"]
    patterns = state["patterns"]
    signals = state["signals"]

    setup_items = [
        (side(long_side, trend["ema21_above_ma50"] and trend["ema21_rising"], trend["ema21_below_ma50"] and trend["ema21_falling"]), "EMA21 / MA50 추세 정렬", 15),
        (side(long_side, trend["close_above_ema21"], trend["close_below_ema21"]), "가격이 EMA21 방향 위상 유지", 10),
        (side(long_side, structure["pullback_near_ema21_long"] or structure["pullback_near_ma20_long"] or structure["pullback_near_kc_mid_long"], structure["pullback_near_ema21_short"] or structure["pullback_near_ma20_short"] or structure["pullback_near_kc_mid_short"]), "눌림 구간 접근", 12),
        (side(long_side, trend["higher_high_recent"] or signals["CS_Trend_Continuation_Buy"], trend["lower_low_recent"] or signals["CS_Trend_Continuation_Sell"]), "최근 추세 재개 이력", 5),
        (side(long_side, volume_flow["volume_support"], volume_flow["volume_support"]), "거래량 바닥 이탈 없음", 3),
    ]
    trigger_items = [
        (side(long_side, signals["EMA_Pullback_Buy"] or patterns["bullish_reversal_candle"], signals["EMA_Pullback_Sell"] or patterns["bearish_reversal_candle"]), "눌림 뒤 방향 전환 캔들", 15),
        (side(long_side, signals["UTBot_Buy"] or signals["Hull_Turn_Bull"], signals["UTBot_Sell"] or signals["Hull_Turn_Bear"]), "보조 추세 신호 정렬", 10),
        (side(long_side, trend["psar_bullish"], trend["psar_bearish"]), "PSAR 추세 유지", 5),
        (side(long_side, momentum["macd_hist_rising"] and momentum["wt_rising"], momentum["macd_hist_falling"] and momentum["wt_falling"]), "모멘텀 재가속", 5),
    ]
    setup_score, setup_matched, setup_missing = score_group(setup_items)
    trigger_score, trigger_matched, trigger_missing = score_group(trigger_items)
    trigger_passed = trigger_score >= 20
    phase = "TRIGGERED" if trigger_passed else "PULLBACK_WAIT" if setup_score >= 25 else "SETUP_INVALID"
    stop_loss, target_1, target_2, rr = risk_template_trend(state, long_side)
    conflicts = default_conflicts(state, long_side)
    return build_result(
        definition=definition,
        state=state,
        long_side=long_side,
        family="trend_pullback",
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
        invalidation_builder=trend_invalidation_text,
    )


def evaluate_supertrend_psar(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    trend = state["trend"]
    momentum = state["momentum"]
    signals = state["signals"]

    setup_items = [
        (side(long_side, trend["supertrend_bullish"], trend["supertrend_bearish"]), "SuperTrend 방향 일치", 15),
        (side(long_side, trend["psar_bullish"], trend["psar_bearish"]), "PSAR 방향 일치", 15),
        (side(long_side, trend["close_above_supertrend"] and trend["close_above_ema21"], trend["close_below_supertrend"] and trend["close_below_ema21"]), "가격이 추세 기준선 위상 유지", 10),
        (side(long_side, trend["adx_strong"] and trend["plus_di_dominant"], trend["adx_strong"] and trend["minus_di_dominant"]), "추세 강도 확인", 5),
    ]
    trigger_items = [
        (side(long_side, signals["SuperTrend_Buy"] or signals["CS_Triple_Confirm_Buy"], signals["SuperTrend_Sell"] or signals["CS_Triple_Confirm_Sell"]), "SuperTrend 전환 / 3중 확인", 15),
        (side(long_side, signals["UTBot_Buy"] or signals["Hull_Turn_Bull"], signals["UTBot_Sell"] or signals["Hull_Turn_Bear"]), "보조 추세 신호 정렬", 10),
        (side(long_side, momentum["macd_hist_rising"] or momentum["wt_rising"], momentum["macd_hist_falling"] or momentum["wt_falling"]), "모멘텀 동조화", 10),
    ]
    setup_score, setup_matched, setup_missing = score_group(setup_items)
    trigger_score, trigger_matched, trigger_missing = score_group(trigger_items)
    trigger_passed = trigger_score >= 15 and side(long_side, trend["supertrend_bullish"] and trend["psar_bullish"], trend["supertrend_bearish"] and trend["psar_bearish"])
    phase = "DOUBLE_CONFIRMED" if trigger_passed else "TREND_ALIGNED" if setup_score >= 20 else "SETUP_INVALID"
    stop_loss, target_1, target_2, rr = risk_template_trend(state, long_side)
    conflicts = default_conflicts(state, long_side)
    if side(long_side, not trend["psar_bullish"], not trend["psar_bearish"]):
        conflicts.append("PSAR 방향 전환이 아직 완전하지 않습니다.")
    return build_result(
        definition=definition,
        state=state,
        long_side=long_side,
        family="supertrend_psar",
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
        invalidation_builder=trend_invalidation_text,
    )


def evaluate_keltner_pullback(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    trend = state["trend"]
    structure = state["structure"]
    volume_flow = state["volume_flow"]
    momentum = state["momentum"]
    patterns = state["patterns"]
    signals = state["signals"]

    setup_items = [
        (side(long_side, trend["ema21_above_ma50"] and trend["close_above_ma20"], trend["ema21_below_ma50"] and trend["close_below_ma20"]), "상위 추세와 Keltner 기준선 정렬", 15),
        (side(long_side, structure["pullback_near_kc_mid_long"], structure["pullback_near_kc_mid_short"]), "Keltner mid 눌림 구간 접근", 15),
        (side(long_side, trend["close_above_vwap"], trend["close_below_vwap"]), "VWAP 방향 우위 유지", 8),
        (side(long_side, volume_flow["volume_support"], volume_flow["volume_support"]), "눌림 중 거래량 지지", 7),
    ]
    trigger_items = [
        (side(long_side, signals["EMA_Pullback_Buy"] or patterns["bullish_reversal_candle"], signals["EMA_Pullback_Sell"] or patterns["bearish_reversal_candle"]), "Keltner 눌림 뒤 반전 캔들", 15),
        (side(long_side, signals["UTBot_Buy"] or signals["Hull_Turn_Bull"], signals["UTBot_Sell"] or signals["Hull_Turn_Bear"]), "보조 추세 신호 정렬", 10),
        (side(long_side, momentum["macd_hist_rising"], momentum["macd_hist_falling"]), "모멘텀 재확장", 10),
    ]
    return build_result_from_groups(
        definition,
        state,
        long_side,
        "keltner_pullback",
        setup_items,
        trigger_items,
        trigger_threshold=20,
        setup_threshold=20,
        triggered_phase="TRIGGERED",
        ready_phase="PULLBACK_WAIT",
        risk_template=risk_template_trend,
        invalidation_builder=trend_invalidation_text,
    )


def evaluate_anchored_vwap(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    trend = state["trend"]
    structure = state["structure"]
    volume_flow = state["volume_flow"]
    momentum = state["momentum"]
    patterns = state["patterns"]
    signals = state["signals"]

    setup_items = [
        (side(long_side, trend["fixed_vwap_holding_long"], trend["fixed_vwap_holding_short"]), "Anchored VWAP 방향 유지", 15),
        (side(long_side, structure["pullback_near_fixed_vwap_long"], structure["pullback_near_fixed_vwap_short"]), "AVWAP 리테스트 구간", 12),
        (side(long_side, trend["ema21_above_ma50"], trend["ema21_below_ma50"]), "상위 추세 정렬", 10),
        (side(long_side, volume_flow["volume_support"], volume_flow["volume_support"]), "거래량 바닥 붕괴 없음", 8),
    ]
    trigger_items = [
        (side(long_side, signals["VWAP_Bounce_Buy"] or patterns["bullish_reversal_candle"], signals["VWAP_Reject_Sell"] or patterns["bearish_reversal_candle"]), "AVWAP 반등 / 거절 캔들", 15),
        (side(long_side, trend["close_above_fixed_vwap"], trend["close_below_fixed_vwap"]), "종가 기준 AVWAP 유지", 10),
        (side(long_side, signals["UTBot_Buy"] or momentum["macd_hist_rising"], signals["UTBot_Sell"] or momentum["macd_hist_falling"]), "후속 추세 확인", 10),
    ]
    return build_result_from_groups(
        definition,
        state,
        long_side,
        "anchored_vwap",
        setup_items,
        trigger_items,
        trigger_threshold=20,
        setup_threshold=20,
        triggered_phase="AVWAP_CONFIRMED",
        ready_phase="AVWAP_HOLD",
        risk_template=risk_template_trend,
        invalidation_builder=trend_invalidation_text,
    )


def evaluate_accumulation_pattern(definition: StrategyDefinition, state: dict) -> StrategyResult:
    volume_flow = state["volume_flow"]
    structure = state["structure"]
    trend = state["trend"]
    momentum = state["momentum"]
    patterns = state["patterns"]
    signals = state["signals"]

    setup_items = [
        (signals["CS_Institutional_Accumulation"] or patterns["pocket_pivot"], "매집 유사 패턴 발생", 18),
        (volume_flow["obv_rising"] and volume_flow["cmf_positive"], "OBV / CMF 동반 개선", 12),
        (trend["close_above_ma50"] or structure["near_vp_poc"], "가격이 핵심 기준선 위 유지", 8),
        (trend["close_above_fixed_vwap"] or structure["pullback_near_fixed_vwap_long"], "AVWAP 방어", 7),
    ]
    trigger_items = [
        (patterns["pocket_pivot"] or signals["Volume_POC_Breakout"], "Pocket Pivot 또는 POC 돌파", 15),
        (volume_flow["volume_support"], "거래량 동반", 10),
        (momentum["macd_hist_rising"] or trend["close_above_vwap"], "초기 추세 확인", 10),
    ]
    return build_result_from_groups(
        definition,
        state,
        True,
        "accumulation_pattern",
        setup_items,
        trigger_items,
        trigger_threshold=18,
        setup_threshold=18,
        triggered_phase="ACCUMULATION_CONFIRMED",
        ready_phase="ACCUMULATION_READY",
        risk_template=risk_template_trend,
        invalidation_builder=trend_invalidation_text,
    )


def evaluate_fractal_alligator(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    trend = state["trend"]
    structure = state["structure"]
    volume_flow = state["volume_flow"]
    momentum = state["momentum"]
    signals = state["signals"]
    patterns = state["patterns"]

    setup_items = [
        (side(long_side, trend["close_above_ema21"] and trend["ema21_above_ma50"], trend["close_below_ema21"] and trend["ema21_below_ma50"]), "Alligator 대체 추세 정렬", 15),
        (side(long_side, np.isfinite(structure["recent_fractal_high"]), np.isfinite(structure["recent_fractal_low"])), "fractal 레벨 준비", 10),
        (side(long_side, trend["adx_expanding"], trend["adx_expanding"]), "sleeping → awakening 추세 강화", 10),
        (side(long_side, volume_flow["volume_support"], volume_flow["volume_support"]), "거래량 유지", 10),
    ]
    trigger_items = [
        (side(long_side, structure["fractal_breakout_long"], structure["fractal_breakout_short"]), "fractal 돌파", 15),
        (side(long_side, signals["Hull_Turn_Bull"] or signals["UTBot_Buy"], signals["Hull_Turn_Bear"] or signals["UTBot_Sell"]), "추세 전환 보조 신호", 10),
        (side(long_side, patterns["fractal_high"] or momentum["macd_hist_rising"], patterns["fractal_low"] or momentum["macd_hist_falling"]), "돌파 후 방향성 유지", 10),
    ]
    return build_result_from_groups(
        definition,
        state,
        long_side,
        "fractal_alligator",
        setup_items,
        trigger_items,
        trigger_threshold=18,
        setup_threshold=18,
        triggered_phase="FRACTAL_BREAKOUT_CONFIRMED",
        ready_phase="ALLIGATOR_AWAKENING",
        risk_template=risk_template_trend,
        invalidation_builder=trend_invalidation_text,
    )
