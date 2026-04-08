from __future__ import annotations

import numpy as np

from ..models import StrategyDefinition, StrategyResult
from ..risk import breakout_invalidation_text, default_conflicts, risk_template_breakout
from .common import build_result, build_result_from_groups, score_group, side


def evaluate_breakout_confirmation(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    trend = state["trend"]
    structure = state["structure"]
    volume_flow = state["volume_flow"]
    momentum = state["momentum"]
    signals = state["signals"]

    setup_items = [
        (side(long_side, structure["near_breakout_long"], structure["near_breakout_short"]), "돌파 후보 레벨 인접", 12),
        (side(long_side, volume_flow["volume_support"], volume_flow["volume_support"]), "거래량 점증", 8),
        (side(long_side, trend["adx_strong"], trend["adx_strong"]), "ADX로 추세 힘 확인", 8),
        (side(long_side, trend["close_above_ema21"] and trend["close_above_vwap"], trend["close_below_ema21"] and trend["close_below_vwap"]), "기준선 정렬", 10),
        (side(long_side, trend["plus_di_dominant"], trend["minus_di_dominant"]), "방향성 우위", 7),
    ]
    trigger_signal_long = any(signals[key] for key in ("Expansion_BO", "Kumo_Breakout_Bull", "BB_Upper_Break", "Box_Breakout_Bull", "Channel_Breakout_Bull", "Triangle_Breakout_Bull", "CS_Breakout_Confirm_Buy"))
    trigger_signal_short = any(signals[key] for key in ("Expansion_BD", "Kumo_Breakout_Bear", "BB_Lower_Break", "Box_Breakdown_Bear", "Channel_Breakdown_Bear", "Triangle_Breakdown_Bear", "CS_Breakout_Confirm_Sell"))
    hold_long = state["price"]["close"] >= structure["breakout_level"] * 0.995
    hold_short = state["price"]["close"] <= structure["breakdown_level"] * 1.005
    trigger_items = [
        (side(long_side, trigger_signal_long, trigger_signal_short), "돌파 시그널 발생", 15),
        (side(long_side, hold_long, hold_short), "돌파 레벨 종가 유지", 10),
        (side(long_side, volume_flow["volume_burst"], volume_flow["volume_burst"]), "돌파봉 거래량 증가", 5),
        (side(long_side, momentum["macd_hist_rising"], momentum["macd_hist_falling"]), "모멘텀 후속 확인", 5),
    ]
    setup_score, setup_matched, setup_missing = score_group(setup_items)
    trigger_score, trigger_matched, trigger_missing = score_group(trigger_items)
    trigger_passed = trigger_score >= 25
    phase = "BREAKOUT_CONFIRMED" if trigger_passed else "BREAKOUT_PENDING" if trigger_score >= 15 else "SETUP_INVALID"
    stop_loss, target_1, target_2, rr = risk_template_breakout(state, long_side)
    conflicts = default_conflicts(state, long_side)
    if side(long_side, not hold_long and trigger_signal_long, not hold_short and trigger_signal_short):
        conflicts.append("돌파 레벨 위/아래 안착이 아직 부족합니다.")
    return build_result(
        definition=definition,
        state=state,
        long_side=long_side,
        family="breakout",
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
        invalidation_builder=breakout_invalidation_text,
    )


def evaluate_squeeze_expansion(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    trend = state["trend"]
    momentum = state["momentum"]
    volume_flow = state["volume_flow"]
    signals = state["signals"]

    setup_items = [
        (side(long_side, momentum["squeeze_recent"], momentum["squeeze_recent"]), "Squeeze On / BB 압축 지속", 20),
        (side(long_side, momentum["bb_width_contracting"], momentum["bb_width_contracting"]), "밴드 폭 축소", 10),
        (side(long_side, momentum["macd_hist_rising"] or momentum["wt_rising"], momentum["macd_hist_falling"] or momentum["wt_falling"]), "압축 속 모멘텀 방향성 준비", 8),
        (side(long_side, volume_flow["volume_dry_up"] or not volume_flow["volume_burst"], volume_flow["volume_dry_up"] or not volume_flow["volume_burst"]), "변동성 압축 구간", 7),
    ]
    trigger_items = [
        (side(long_side, signals["Squeeze_Fire_Buy"] or signals["BB_Squeeze_End_Bull"] or signals["CS_Squeeze_Breakout_Buy"], signals["Squeeze_Fire_Sell"] or signals["BB_Squeeze_End_Bear"] or signals["CS_Squeeze_Breakdown_Sell"]), "Squeeze Off / 방향 분출", 15),
        (side(long_side, signals["Squeeze_Mom_Cross_Up"] or momentum["macd_hist_rising"], signals["Squeeze_Mom_Cross_Down"] or momentum["macd_hist_falling"]), "모멘텀 히스토그램 확장", 8),
        (side(long_side, volume_flow["volume_burst"], volume_flow["volume_burst"]), "거래량 동반", 7),
        (side(long_side, trend["close_above_ema21"] or trend["close_above_vwap"], trend["close_below_ema21"] or trend["close_below_vwap"]), "기준선 정렬 가산", 5),
    ]
    setup_score, setup_matched, setup_missing = score_group(setup_items)
    trigger_score, trigger_matched, trigger_missing = score_group(trigger_items)
    trigger_passed = trigger_score >= 20
    phase = "TRIGGERED" if trigger_passed else "SQUEEZE_READY" if setup_score >= 20 else "SETUP_INVALID"
    stop_loss, target_1, target_2, rr = risk_template_breakout(state, long_side)
    conflicts = default_conflicts(state, long_side)
    if side(long_side, momentum["squeeze_on"], momentum["squeeze_on"]) and not trigger_passed:
        conflicts.append("아직 Squeeze Off가 확정되지 않았습니다.")
    return build_result(
        definition=definition,
        state=state,
        long_side=long_side,
        family="squeeze",
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
        invalidation_builder=breakout_invalidation_text,
    )


def evaluate_keltner_breakout(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    trend = state["trend"]
    volume_flow = state["volume_flow"]
    momentum = state["momentum"]
    structure = state["structure"]
    signals = state["signals"]

    setup_items = [
        (side(long_side, structure["near_breakout_long"], structure["near_breakout_short"]), "Keltner 상단/하단 돌파 구간 접근", 12),
        (side(long_side, trend["close_above_ema21"], trend["close_below_ema21"]), "EMA21 방향 정렬", 10),
        (side(long_side, trend["adx_strong"], trend["adx_strong"]), "추세 강도 확보", 8),
        (side(long_side, volume_flow["volume_support"], volume_flow["volume_support"]), "돌파 전 거래량 준비", 10),
        (side(long_side, momentum["bb_width_contracting"] or momentum["squeeze_recent"], momentum["bb_width_contracting"] or momentum["squeeze_recent"]), "돌파 전 변동성 수축", 5),
    ]
    trigger_items = [
        (side(long_side, state["price"]["close"] >= state["price"]["kc_upper"] or signals["Expansion_BO"], state["price"]["close"] <= state["price"]["kc_lower"] or signals["Expansion_BD"]), "Keltner 밴드 돌파 종가 확정", 15),
        (side(long_side, signals["Channel_Breakout_Bull"] or signals["Box_Breakout_Bull"] or signals["CS_Breakout_Confirm_Buy"], signals["Channel_Breakdown_Bear"] or signals["Box_Breakdown_Bear"] or signals["CS_Breakout_Confirm_Sell"]), "돌파 확인 시그널 발생", 10),
        (side(long_side, volume_flow["volume_burst"], volume_flow["volume_burst"]), "돌파봉 거래량 증가", 5),
        (side(long_side, momentum["macd_hist_rising"], momentum["macd_hist_falling"]), "돌파 후 모멘텀 확장", 5),
    ]
    extra_conflicts: list[str] = []
    if side(long_side, state["price"]["close"] < state["price"]["kc_upper"], state["price"]["close"] > state["price"]["kc_lower"]):
        extra_conflicts.append("Keltner 외곽 밴드 안착이 아직 완전하지 않습니다.")
    return build_result_from_groups(
        definition,
        state,
        long_side,
        "keltner_breakout",
        setup_items,
        trigger_items,
        trigger_threshold=20,
        setup_threshold=20,
        triggered_phase="KELTNER_BREAKOUT_CONFIRMED",
        ready_phase="KELTNER_BREAKOUT_PENDING",
        risk_template=risk_template_breakout,
        invalidation_builder=breakout_invalidation_text,
        extra_conflicts=extra_conflicts,
    )


def evaluate_fractal_breakout(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    trend = state["trend"]
    volume_flow = state["volume_flow"]
    momentum = state["momentum"]
    patterns = state["patterns"]
    structure = state["structure"]
    signals = state["signals"]

    setup_items = [
        (side(long_side, trend["close_above_ema21"], trend["close_below_ema21"]), "EMA21 방향 우위", 12),
        (side(long_side, np.isfinite(structure["recent_fractal_high"]), np.isfinite(structure["recent_fractal_low"])), "최근 유효 fractal 존재", 10),
        (side(long_side, volume_flow["volume_support"], volume_flow["volume_support"]), "거래량 준비", 8),
        (side(long_side, trend["adx_strong"], trend["adx_strong"]), "추세 강도 확인", 8),
    ]
    trigger_items = [
        (side(long_side, structure["fractal_breakout_long"], structure["fractal_breakout_short"]), "fractal 돌파 / 이탈 확정", 15),
        (side(long_side, patterns["fractal_high"] or signals["Channel_Breakout_Bull"], patterns["fractal_low"] or signals["Channel_Breakdown_Bear"]), "fractal 시그널 동반", 10),
        (side(long_side, volume_flow["volume_burst"], volume_flow["volume_burst"]), "돌파 거래량 증가", 5),
        (side(long_side, momentum["macd_hist_rising"], momentum["macd_hist_falling"]), "후속 모멘텀 정렬", 5),
    ]
    return build_result_from_groups(
        definition,
        state,
        long_side,
        "fractal_breakout",
        setup_items,
        trigger_items,
        trigger_threshold=18,
        setup_threshold=18,
        triggered_phase="FRACTAL_BREAKOUT_CONFIRMED",
        ready_phase="FRACTAL_BREAKOUT_PENDING",
        risk_template=risk_template_breakout,
        invalidation_builder=breakout_invalidation_text,
    )


def evaluate_ichimoku_breakout(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    levels = state["levels"]
    trend = state["trend"]
    volume_flow = state["volume_flow"]
    momentum = state["momentum"]
    signals = state["signals"]

    above_cloud = np.isfinite(levels["cloud_top"]) and state["price"]["close"] >= levels["cloud_top"]
    below_cloud = np.isfinite(levels["cloud_bottom"]) and state["price"]["close"] <= levels["cloud_bottom"]
    tk_bull = signals["TK_Cross_Bull"] or (levels["tenkan"] >= levels["kijun"])
    tk_bear = signals["TK_Cross_Bear"] or (levels["tenkan"] <= levels["kijun"])
    setup_items = [
        (side(long_side, above_cloud, below_cloud), "구름대 상/하단 이탈", 15),
        (side(long_side, tk_bull, tk_bear), "Tenkan / Kijun 정렬", 10),
        (side(long_side, trend["adx_strong"], trend["adx_strong"]), "추세 강도 확인", 10),
        (side(long_side, volume_flow["volume_support"], volume_flow["volume_support"]), "구름 돌파 거래량 준비", 10),
    ]
    trigger_items = [
        (side(long_side, signals["Kumo_Breakout_Bull"] or signals["CS_Ichimoku_Breakout_Buy"], signals["Kumo_Breakout_Bear"] or signals["CS_Ichimoku_Breakout_Sell"]), "Kumo 돌파 신호 발생", 15),
        (side(long_side, signals["TK_Cross_Bull"] or tk_bull, signals["TK_Cross_Bear"] or tk_bear), "TK 교차 확인", 10),
        (side(long_side, momentum["macd_hist_rising"], momentum["macd_hist_falling"]), "모멘텀 후속 확장", 10),
    ]
    return build_result_from_groups(
        definition,
        state,
        long_side,
        "ichimoku_breakout",
        setup_items,
        trigger_items,
        trigger_threshold=18,
        setup_threshold=18,
        triggered_phase="ICHI_BREAKOUT_CONFIRMED",
        ready_phase="ICHI_PENDING",
        risk_template=risk_template_breakout,
        invalidation_builder=breakout_invalidation_text,
    )
