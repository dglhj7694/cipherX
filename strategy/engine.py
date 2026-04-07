from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

from .evaluators.common import (
    failed_from_conflicts as _failed_from_conflicts,
    score_group as _score_group,
    side as _side,
    status_from_score as _status_from_score,
    total_score as _total_score,
)
from .models import VISIBLE_STATUSES, StrategyDefinition, StrategyResult, StrategySummary
from .presentation import (
    entry_hint as _entry_hint,
    entry_price as _entry_price,
    entry_reference_payload as _entry_reference_payload,
    phase_note as _phase_note,
    recent_change_notes as _recent_change_notes,
    strategy_explanation as _strategy_explanation,
    strategy_public_label as _strategy_public_label,
)
from .registry import build_strategy_definitions
from .risk import (
    breakout_invalidation_text as _breakout_invalidation_text,
    default_conflicts as _default_conflicts,
    reversal_invalidation_text as _reversal_invalidation_text,
    risk_score as _risk_score,
    risk_template_breakout as _risk_template_breakout,
    risk_template_reversal as _risk_template_reversal,
    risk_template_trend as _risk_template_trend,
    trend_invalidation_text as _trend_invalidation_text,
)
from .state_builder import build_market_state as _build_market_state, ordered_unique as _ordered_unique
from .summary import build_summary as _build_summary


STRATEGY_DEFINITIONS: tuple[StrategyDefinition, ...] = build_strategy_definitions(StrategyDefinition)


def build_strategy_payload(dc: pd.DataFrame) -> dict:
    engine = StrategyEngine()
    return engine.build_payload(dc)


class StrategyEngine:
    def __init__(self, definitions: Iterable[StrategyDefinition] | None = None):
        self.definitions = tuple(definitions or STRATEGY_DEFINITIONS)

    def build_payload(self, dc: pd.DataFrame) -> dict:
        if dc is None or dc.empty:
            empty_summary = StrategySummary(
                active_count=0,
                visible_count=0,
                bullish_count=0,
                bearish_count=0,
                long_short_bias="BALANCED",
                conflict_level="LOW",
                top_strategy=None,
            )
            return {"summary": empty_summary.to_dict(), "results": [], "visible_results": []}
        market_state = _build_market_state(dc)
        results = [self._evaluate(definition, market_state) for definition in self.definitions]
        results.sort(key=lambda item: (item.score, item.trigger_score, item.setup_score), reverse=True)
        visible = [item for item in results if item.status in VISIBLE_STATUSES]
        summary = _build_summary(visible, results)
        return {
            "summary": summary.to_dict(),
            "results": [item.to_dict() for item in results],
            "visible_results": [item.to_dict() for item in visible],
        }

    def _evaluate(self, definition: StrategyDefinition, market_state: dict) -> StrategyResult:
        evaluators = {
            "trend_pullback": _evaluate_trend_pullback,
            "breakout_confirmation": _evaluate_breakout_confirmation,
            "squeeze_expansion": _evaluate_squeeze_expansion,
            "reversal_cluster": _evaluate_reversal_cluster,
            "supertrend_psar": _evaluate_supertrend_psar,
            "obv_divergence": _evaluate_obv_divergence,
            "keltner_pullback": _evaluate_keltner_pullback,
            "keltner_breakout": _evaluate_keltner_breakout,
            "keltner_mean_reversion": _evaluate_keltner_mean_reversion,
            "vwap_reclaim": _evaluate_vwap_reclaim,
            "morning_star_fib": _evaluate_morning_star_fib,
            "fractal_breakout": _evaluate_fractal_breakout,
            "anchored_vwap": _evaluate_anchored_vwap,
            "accumulation_pattern": _evaluate_accumulation_pattern,
            "poc_rotation": _evaluate_poc_rotation,
            "ichimoku_breakout": _evaluate_ichimoku_breakout,
            "fractal_alligator": _evaluate_fractal_alligator,
            "chaikin_flow": _evaluate_chaikin_flow,
        }
        return evaluators[definition.family](definition, market_state)


def _evaluate_trend_pullback(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    trend = state["trend"]
    structure = state["structure"]
    volume_flow = state["volume_flow"]
    momentum = state["momentum"]
    patterns = state["patterns"]
    signals = state["signals"]

    setup_items = [
        (_side(long_side, trend["ema21_above_ma50"] and trend["ema21_rising"], trend["ema21_below_ma50"] and trend["ema21_falling"]), "EMA21 / MA50 추세 정렬", 15),
        (_side(long_side, trend["close_above_ema21"], trend["close_below_ema21"]), "가격이 EMA21 방향 위상 유지", 10),
        (_side(long_side, structure["pullback_near_ema21_long"] or structure["pullback_near_ma20_long"] or structure["pullback_near_kc_mid_long"], structure["pullback_near_ema21_short"] or structure["pullback_near_ma20_short"] or structure["pullback_near_kc_mid_short"]), "눌림 구간 접근", 12),
        (_side(long_side, trend["higher_high_recent"] or signals["CS_Trend_Continuation_Buy"], trend["lower_low_recent"] or signals["CS_Trend_Continuation_Sell"]), "최근 추세 재개 이력", 5),
        (_side(long_side, volume_flow["volume_support"], volume_flow["volume_support"]), "거래량 바닥 이탈 없음", 3),
    ]
    trigger_items = [
        (_side(long_side, signals["EMA_Pullback_Buy"] or patterns["bullish_reversal_candle"], signals["EMA_Pullback_Sell"] or patterns["bearish_reversal_candle"]), "눌림 뒤 방향 전환 캔들", 15),
        (_side(long_side, signals["UTBot_Buy"] or signals["Hull_Turn_Bull"], signals["UTBot_Sell"] or signals["Hull_Turn_Bear"]), "보조 추세 신호 정렬", 10),
        (_side(long_side, trend["psar_bullish"], trend["psar_bearish"]), "PSAR 추세 유지", 5),
        (_side(long_side, momentum["macd_hist_rising"] and momentum["wt_rising"], momentum["macd_hist_falling"] and momentum["wt_falling"]), "모멘텀 재가속", 5),
    ]
    setup_score, setup_matched, setup_missing = _score_group(setup_items)
    trigger_score, trigger_matched, trigger_missing = _score_group(trigger_items)
    trigger_passed = trigger_score >= 20
    phase = "TRIGGERED" if trigger_passed else "PULLBACK_WAIT" if setup_score >= 25 else "SETUP_INVALID"
    stop_loss, target_1, target_2, rr = _risk_template_trend(state, long_side)
    conflict_reasons = _default_conflicts(state, long_side)
    risk_score = _risk_score(stop_loss, target_1, state["price"]["entry"], rr, conflict_reasons)
    total_score = _total_score(setup_score, trigger_score, risk_score)
    status = _status_from_score(total_score, trigger_passed, rr, setup_score, trigger_score, phase)
    entry_hint = _entry_hint(status, phase, long_side, "trend_pullback")
    entry_price = _entry_price(state, long_side, "trend_pullback", phase, status)
    entry_reference = _entry_reference_payload(state, long_side, "trend_pullback", phase, status, entry_price, stop_loss)
    matched = setup_matched + trigger_matched
    missing = setup_missing + trigger_missing
    failed = _failed_from_conflicts(conflict_reasons)
    explanation = _strategy_explanation(definition, status, matched, missing, conflict_reasons)
    return StrategyResult(
        id=definition.id,
        label=_strategy_public_label(definition),
        canonical_label=definition.label,
        direction=definition.direction,
        category=definition.category,
        score=total_score,
        status=status,
        phase=phase,
        entry_hint=entry_hint,
        presentation_type=definition.presentation_type,
        implementation_level=definition.implementation_level,
        deterministic=definition.deterministic,
        entry_reference_type=entry_reference["entry_reference_type"],
        entry_reference_text=entry_reference["entry_reference_text"],
        entry_price=entry_price,
        interest_low=entry_reference["interest_low"],
        interest_high=entry_reference["interest_high"],
        confirmation_level=entry_reference["confirmation_level"],
        invalidation_level=entry_reference["invalidation_level"],
        setup_score=setup_score,
        trigger_score=trigger_score,
        risk_score=risk_score,
        matched_conditions=matched,
        missing_conditions=missing,
        failed_conditions=failed,
        stop_loss=stop_loss,
        target_1=target_1,
        target_2=target_2,
        rr=rr,
        conflict_reasons=conflict_reasons,
        explanation=explanation,
        last5_change=_recent_change_notes(state, long_side),
        invalidation_text=_trend_invalidation_text(state, long_side, stop_loss),
        note=_phase_note(phase, conflict_reasons),
    )


def _evaluate_breakout_confirmation(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    trend = state["trend"]
    structure = state["structure"]
    volume_flow = state["volume_flow"]
    momentum = state["momentum"]
    signals = state["signals"]

    setup_items = [
        (_side(long_side, structure["near_breakout_long"], structure["near_breakout_short"]), "돌파 후보 레벨 인접", 12),
        (_side(long_side, volume_flow["volume_support"], volume_flow["volume_support"]), "거래량 점증", 8),
        (_side(long_side, trend["adx_strong"], trend["adx_strong"]), "ADX로 추세 힘 확인", 8),
        (_side(long_side, trend["close_above_ema21"] and trend["close_above_vwap"], trend["close_below_ema21"] and trend["close_below_vwap"]), "기준선 정렬", 10),
        (_side(long_side, trend["plus_di_dominant"], trend["minus_di_dominant"]), "방향성 우위", 7),
    ]
    trigger_signal_long = any(signals[key] for key in ("Expansion_BO", "Kumo_Breakout_Bull", "BB_Upper_Break", "Box_Breakout_Bull", "Channel_Breakout_Bull", "Triangle_Breakout_Bull", "CS_Breakout_Confirm_Buy"))
    trigger_signal_short = any(signals[key] for key in ("Expansion_BD", "Kumo_Breakout_Bear", "BB_Lower_Break", "Box_Breakdown_Bear", "Channel_Breakdown_Bear", "Triangle_Breakdown_Bear", "CS_Breakout_Confirm_Sell"))
    hold_long = state["price"]["close"] >= structure["breakout_level"] * 0.995
    hold_short = state["price"]["close"] <= structure["breakdown_level"] * 1.005
    trigger_items = [
        (_side(long_side, trigger_signal_long, trigger_signal_short), "돌파 시그널 발생", 15),
        (_side(long_side, hold_long, hold_short), "돌파 레벨 종가 유지", 10),
        (_side(long_side, volume_flow["volume_burst"], volume_flow["volume_burst"]), "돌파봉 거래량 증가", 5),
        (_side(long_side, momentum["macd_hist_rising"], momentum["macd_hist_falling"]), "모멘텀 후속 확인", 5),
    ]
    setup_score, setup_matched, setup_missing = _score_group(setup_items)
    trigger_score, trigger_matched, trigger_missing = _score_group(trigger_items)
    trigger_passed = trigger_score >= 25
    phase = "BREAKOUT_CONFIRMED" if trigger_passed else "BREAKOUT_PENDING" if trigger_score >= 15 else "SETUP_INVALID"
    stop_loss, target_1, target_2, rr = _risk_template_breakout(state, long_side)
    conflict_reasons = _default_conflicts(state, long_side)
    if _side(long_side, not hold_long and trigger_signal_long, not hold_short and trigger_signal_short):
        conflict_reasons.append("돌파 레벨 위/아래 안착이 아직 부족합니다.")
    risk_score = _risk_score(stop_loss, target_1, state["price"]["entry"], rr, conflict_reasons)
    total_score = _total_score(setup_score, trigger_score, risk_score)
    status = _status_from_score(total_score, trigger_passed, rr, setup_score, trigger_score, phase)
    entry_hint = _entry_hint(status, phase, long_side, "breakout")
    entry_price = _entry_price(state, long_side, "breakout", phase, status)
    entry_reference = _entry_reference_payload(state, long_side, "breakout", phase, status, entry_price, stop_loss)
    matched = setup_matched + trigger_matched
    missing = setup_missing + trigger_missing
    failed = _failed_from_conflicts(conflict_reasons)
    explanation = _strategy_explanation(definition, status, matched, missing, conflict_reasons)
    return StrategyResult(
        id=definition.id,
        label=_strategy_public_label(definition),
        canonical_label=definition.label,
        direction=definition.direction,
        category=definition.category,
        score=total_score,
        status=status,
        phase=phase,
        entry_hint=entry_hint,
        presentation_type=definition.presentation_type,
        implementation_level=definition.implementation_level,
        deterministic=definition.deterministic,
        entry_reference_type=entry_reference["entry_reference_type"],
        entry_reference_text=entry_reference["entry_reference_text"],
        entry_price=entry_price,
        interest_low=entry_reference["interest_low"],
        interest_high=entry_reference["interest_high"],
        confirmation_level=entry_reference["confirmation_level"],
        invalidation_level=entry_reference["invalidation_level"],
        setup_score=setup_score,
        trigger_score=trigger_score,
        risk_score=risk_score,
        matched_conditions=matched,
        missing_conditions=missing,
        failed_conditions=failed,
        stop_loss=stop_loss,
        target_1=target_1,
        target_2=target_2,
        rr=rr,
        conflict_reasons=conflict_reasons,
        explanation=explanation,
        last5_change=_recent_change_notes(state, long_side),
        invalidation_text=_breakout_invalidation_text(state, long_side, stop_loss),
        note=_phase_note(phase, conflict_reasons),
    )


def _evaluate_squeeze_expansion(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    trend = state["trend"]
    momentum = state["momentum"]
    volume_flow = state["volume_flow"]
    signals = state["signals"]

    setup_items = [
        (_side(long_side, momentum["squeeze_recent"], momentum["squeeze_recent"]), "Squeeze On / BB 압축 지속", 20),
        (_side(long_side, momentum["bb_width_contracting"], momentum["bb_width_contracting"]), "밴드 폭 축소", 10),
        (_side(long_side, momentum["macd_hist_rising"] or momentum["wt_rising"], momentum["macd_hist_falling"] or momentum["wt_falling"]), "압축 속 모멘텀 방향성 준비", 8),
        (_side(long_side, volume_flow["volume_dry_up"] or not volume_flow["volume_burst"], volume_flow["volume_dry_up"] or not volume_flow["volume_burst"]), "변동성 압축 구간", 7),
    ]
    trigger_items = [
        (_side(long_side, signals["Squeeze_Fire_Buy"] or signals["BB_Squeeze_End_Bull"] or signals["CS_Squeeze_Breakout_Buy"], signals["Squeeze_Fire_Sell"] or signals["BB_Squeeze_End_Bear"] or signals["CS_Squeeze_Breakdown_Sell"]), "Squeeze Off / 방향 분출", 15),
        (_side(long_side, signals["Squeeze_Mom_Cross_Up"] or momentum["macd_hist_rising"], signals["Squeeze_Mom_Cross_Down"] or momentum["macd_hist_falling"]), "모멘텀 히스토그램 확장", 8),
        (_side(long_side, volume_flow["volume_burst"], volume_flow["volume_burst"]), "거래량 동반", 7),
        (_side(long_side, trend["close_above_ema21"] or trend["close_above_vwap"], trend["close_below_ema21"] or trend["close_below_vwap"]), "기준선 정렬 가산", 5),
    ]
    setup_score, setup_matched, setup_missing = _score_group(setup_items)
    trigger_score, trigger_matched, trigger_missing = _score_group(trigger_items)
    trigger_passed = trigger_score >= 20
    phase = "TRIGGERED" if trigger_passed else "SQUEEZE_READY" if setup_score >= 20 else "SETUP_INVALID"
    stop_loss, target_1, target_2, rr = _risk_template_breakout(state, long_side)
    conflict_reasons = _default_conflicts(state, long_side)
    if _side(long_side, momentum["squeeze_on"], momentum["squeeze_on"]) and not trigger_passed:
        conflict_reasons.append("아직 Squeeze Off가 확정되지 않았습니다.")
    risk_score = _risk_score(stop_loss, target_1, state["price"]["entry"], rr, conflict_reasons)
    total_score = _total_score(setup_score, trigger_score, risk_score)
    status = _status_from_score(total_score, trigger_passed, rr, setup_score, trigger_score, phase)
    entry_hint = _entry_hint(status, phase, long_side, "squeeze")
    entry_price = _entry_price(state, long_side, "squeeze", phase, status)
    entry_reference = _entry_reference_payload(state, long_side, "squeeze", phase, status, entry_price, stop_loss)
    matched = setup_matched + trigger_matched
    missing = setup_missing + trigger_missing
    failed = _failed_from_conflicts(conflict_reasons)
    explanation = _strategy_explanation(definition, status, matched, missing, conflict_reasons)
    return StrategyResult(
        id=definition.id,
        label=_strategy_public_label(definition),
        canonical_label=definition.label,
        direction=definition.direction,
        category=definition.category,
        score=total_score,
        status=status,
        phase=phase,
        entry_hint=entry_hint,
        presentation_type=definition.presentation_type,
        implementation_level=definition.implementation_level,
        deterministic=definition.deterministic,
        entry_reference_type=entry_reference["entry_reference_type"],
        entry_reference_text=entry_reference["entry_reference_text"],
        entry_price=entry_price,
        interest_low=entry_reference["interest_low"],
        interest_high=entry_reference["interest_high"],
        confirmation_level=entry_reference["confirmation_level"],
        invalidation_level=entry_reference["invalidation_level"],
        setup_score=setup_score,
        trigger_score=trigger_score,
        risk_score=risk_score,
        matched_conditions=matched,
        missing_conditions=missing,
        failed_conditions=failed,
        stop_loss=stop_loss,
        target_1=target_1,
        target_2=target_2,
        rr=rr,
        conflict_reasons=conflict_reasons,
        explanation=explanation,
        last5_change=_recent_change_notes(state, long_side),
        invalidation_text=_breakout_invalidation_text(state, long_side, stop_loss),
        note=_phase_note(phase, conflict_reasons),
    )


def _evaluate_reversal_cluster(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    trend = state["trend"]
    structure = state["structure"]
    volume_flow = state["volume_flow"]
    momentum = state["momentum"]
    patterns = state["patterns"]
    signals = state["signals"]

    setup_items = [
        (_side(long_side, momentum["deep_oversold"] or structure["price_change_5"] <= -5.0, momentum["deep_overbought"] or structure["price_change_5"] >= 5.0), "과매도 / 과매수 스트레치", 15),
        (_side(long_side, structure["lower_zone"], structure["upper_zone"]), "밴드/구조 하단 접근", 10),
        (_side(long_side, patterns["bullish_divergence"] or volume_flow["money_flow_improving"], patterns["bearish_divergence"] or volume_flow["money_flow_weakening"]), "다이버전스 또는 자금흐름 개선", 12),
        (_side(long_side, trend["bearish_trend_stack"] or trend["close_below_vwap"], trend["bullish_trend_stack"] or trend["close_above_vwap"]), "추세 말단 / 반전 후보 구간", 8),
    ]
    trigger_items = [
        (_side(long_side, patterns["bullish_reversal_candle"] or patterns["volume_climax_buy"] or patterns["parabolic_bottom"], patterns["bearish_reversal_candle"] or patterns["volume_climax_sell"] or patterns["parabolic_top"]), "반전 캔들 또는 클라이맥스", 15),
        (_side(long_side, momentum["macd_hist_rising"] and momentum["wt_rising"], momentum["macd_hist_falling"] and momentum["wt_falling"]), "모멘텀 개선", 10),
        (_side(long_side, signals["VWAP_Bounce_Buy"] or trend["close_above_vwap"] or signals["UTBot_Buy"] or signals["Hull_Turn_Bull"], signals["VWAP_Reject_Sell"] or trend["close_below_vwap"] or signals["UTBot_Sell"] or signals["Hull_Turn_Bear"]), "기준선 / 확인 신호 회복", 10),
    ]
    setup_score, setup_matched, setup_missing = _score_group(setup_items)
    trigger_score, trigger_matched, trigger_missing = _score_group(trigger_items)
    trigger_passed = trigger_score >= 20
    phase = "TRIGGERED" if trigger_passed else "REVERSAL_READY" if setup_score >= 20 else "SETUP_INVALID"
    stop_loss, target_1, target_2, rr = _risk_template_reversal(state, long_side)
    conflict_reasons = _default_conflicts(state, long_side)
    if _side(long_side, not trend["close_above_vwap"], not trend["close_below_vwap"]):
        conflict_reasons.append("기준선 회복/재이탈 확인이 더 필요합니다.")
    risk_score = _risk_score(stop_loss, target_1, state["price"]["entry"], rr, conflict_reasons)
    total_score = _total_score(setup_score, trigger_score, risk_score)
    status = _status_from_score(total_score, trigger_passed, rr, setup_score, trigger_score, phase)
    entry_hint = _entry_hint(status, phase, long_side, "reversal")
    entry_price = _entry_price(state, long_side, "reversal", phase, status)
    entry_reference = _entry_reference_payload(state, long_side, "reversal", phase, status, entry_price, stop_loss)
    matched = setup_matched + trigger_matched
    missing = setup_missing + trigger_missing
    failed = _failed_from_conflicts(conflict_reasons)
    explanation = _strategy_explanation(definition, status, matched, missing, conflict_reasons)
    return StrategyResult(
        id=definition.id,
        label=_strategy_public_label(definition),
        canonical_label=definition.label,
        direction=definition.direction,
        category=definition.category,
        score=total_score,
        status=status,
        phase=phase,
        entry_hint=entry_hint,
        presentation_type=definition.presentation_type,
        implementation_level=definition.implementation_level,
        deterministic=definition.deterministic,
        entry_reference_type=entry_reference["entry_reference_type"],
        entry_reference_text=entry_reference["entry_reference_text"],
        entry_price=entry_price,
        interest_low=entry_reference["interest_low"],
        interest_high=entry_reference["interest_high"],
        confirmation_level=entry_reference["confirmation_level"],
        invalidation_level=entry_reference["invalidation_level"],
        setup_score=setup_score,
        trigger_score=trigger_score,
        risk_score=risk_score,
        matched_conditions=matched,
        missing_conditions=missing,
        failed_conditions=failed,
        stop_loss=stop_loss,
        target_1=target_1,
        target_2=target_2,
        rr=rr,
        conflict_reasons=conflict_reasons,
        explanation=explanation,
        last5_change=_recent_change_notes(state, long_side),
        invalidation_text=_reversal_invalidation_text(state, long_side, stop_loss),
        note=_phase_note(phase, conflict_reasons),
    )


def _evaluate_supertrend_psar(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    trend = state["trend"]
    momentum = state["momentum"]
    signals = state["signals"]

    setup_items = [
        (_side(long_side, trend["supertrend_bullish"], trend["supertrend_bearish"]), "SuperTrend 방향 일치", 15),
        (_side(long_side, trend["psar_bullish"], trend["psar_bearish"]), "PSAR 방향 일치", 15),
        (_side(long_side, trend["close_above_supertrend"] and trend["close_above_ema21"], trend["close_below_supertrend"] and trend["close_below_ema21"]), "가격이 추세 기준선 위상 유지", 10),
        (_side(long_side, trend["adx_strong"] and trend["plus_di_dominant"], trend["adx_strong"] and trend["minus_di_dominant"]), "추세 강도 확인", 5),
    ]
    trigger_items = [
        (_side(long_side, signals["SuperTrend_Buy"] or signals["CS_Triple_Confirm_Buy"], signals["SuperTrend_Sell"] or signals["CS_Triple_Confirm_Sell"]), "SuperTrend 전환 / 3중 확인", 15),
        (_side(long_side, signals["UTBot_Buy"] or signals["Hull_Turn_Bull"], signals["UTBot_Sell"] or signals["Hull_Turn_Bear"]), "보조 추세 신호 정렬", 10),
        (_side(long_side, momentum["macd_hist_rising"] or momentum["wt_rising"], momentum["macd_hist_falling"] or momentum["wt_falling"]), "모멘텀 동조화", 10),
    ]
    setup_score, setup_matched, setup_missing = _score_group(setup_items)
    trigger_score, trigger_matched, trigger_missing = _score_group(trigger_items)
    trigger_passed = trigger_score >= 15 and _side(long_side, trend["supertrend_bullish"] and trend["psar_bullish"], trend["supertrend_bearish"] and trend["psar_bearish"])
    phase = "DOUBLE_CONFIRMED" if trigger_passed else "TREND_ALIGNED" if setup_score >= 20 else "SETUP_INVALID"
    stop_loss, target_1, target_2, rr = _risk_template_trend(state, long_side)
    conflict_reasons = _default_conflicts(state, long_side)
    if _side(long_side, not trend["psar_bullish"], not trend["psar_bearish"]):
        conflict_reasons.append("PSAR 방향 전환이 아직 완전하지 않습니다.")
    risk_score = _risk_score(stop_loss, target_1, state["price"]["entry"], rr, conflict_reasons)
    total_score = _total_score(setup_score, trigger_score, risk_score)
    status = _status_from_score(total_score, trigger_passed, rr, setup_score, trigger_score, phase)
    entry_hint = _entry_hint(status, phase, long_side, "supertrend_psar")
    entry_price = _entry_price(state, long_side, "supertrend_psar", phase, status)
    entry_reference = _entry_reference_payload(state, long_side, "supertrend_psar", phase, status, entry_price, stop_loss)
    matched = setup_matched + trigger_matched
    missing = setup_missing + trigger_missing
    failed = _failed_from_conflicts(conflict_reasons)
    explanation = _strategy_explanation(definition, status, matched, missing, conflict_reasons)
    return StrategyResult(
        id=definition.id,
        label=_strategy_public_label(definition),
        canonical_label=definition.label,
        direction=definition.direction,
        category=definition.category,
        score=total_score,
        status=status,
        phase=phase,
        entry_hint=entry_hint,
        presentation_type=definition.presentation_type,
        implementation_level=definition.implementation_level,
        deterministic=definition.deterministic,
        entry_reference_type=entry_reference["entry_reference_type"],
        entry_reference_text=entry_reference["entry_reference_text"],
        entry_price=entry_price,
        interest_low=entry_reference["interest_low"],
        interest_high=entry_reference["interest_high"],
        confirmation_level=entry_reference["confirmation_level"],
        invalidation_level=entry_reference["invalidation_level"],
        setup_score=setup_score,
        trigger_score=trigger_score,
        risk_score=risk_score,
        matched_conditions=matched,
        missing_conditions=missing,
        failed_conditions=failed,
        stop_loss=stop_loss,
        target_1=target_1,
        target_2=target_2,
        rr=rr,
        conflict_reasons=conflict_reasons,
        explanation=explanation,
        last5_change=_recent_change_notes(state, long_side),
        invalidation_text=_trend_invalidation_text(state, long_side, stop_loss),
        note=_phase_note(phase, conflict_reasons),
    )


def _evaluate_obv_divergence(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    trend = state["trend"]
    structure = state["structure"]
    volume_flow = state["volume_flow"]
    momentum = state["momentum"]
    patterns = state["patterns"]
    signals = state["signals"]

    setup_items = [
        (_side(long_side, patterns["obv_div_buy"], patterns["obv_div_sell"]), "OBV / 스마트머니 다이버전스", 20),
        (_side(long_side, structure["lower_zone"] or structure["price_change_5"] <= -4.0, structure["upper_zone"] or structure["price_change_5"] >= 4.0), "가격은 극단 구간 접근", 10),
        (_side(long_side, volume_flow["money_flow_improving"], volume_flow["money_flow_weakening"]), "자금흐름 보조 확인", 5),
        (_side(long_side, momentum["oversold"], momentum["overbought"]), "오실레이터 극단 구간", 10),
    ]
    trigger_items = [
        (_side(long_side, patterns["bullish_reversal_candle"], patterns["bearish_reversal_candle"]), "확인 트리거 캔들", 15),
        (_side(long_side, signals["VWAP_Bounce_Buy"] or state["price"]["close"] >= state["price"]["ema8"] or trend["close_above_vwap"], signals["VWAP_Reject_Sell"] or state["price"]["close"] <= state["price"]["ema8"] or trend["close_below_vwap"]), "VWAP / EMA8 회복", 10),
        (_side(long_side, signals["UTBot_Buy"] or momentum["macd_hist_rising"], signals["UTBot_Sell"] or momentum["macd_hist_falling"]), "보조 모멘텀 확인", 10),
    ]
    setup_score, setup_matched, setup_missing = _score_group(setup_items)
    trigger_score, trigger_matched, trigger_missing = _score_group(trigger_items)
    trigger_passed = trigger_score >= 15
    phase = "DIVERGENCE_CONFIRMED" if trigger_passed else "DIVERGENCE_READY" if setup_score >= 20 else "SETUP_INVALID"
    stop_loss, target_1, target_2, rr = _risk_template_reversal(state, long_side)
    conflict_reasons = _default_conflicts(state, long_side)
    if _side(long_side, not trend["close_above_vwap"], not trend["close_below_vwap"]):
        conflict_reasons.append("다이버전스 이후 기준선 확인이 아직 약합니다.")
    risk_score = _risk_score(stop_loss, target_1, state["price"]["entry"], rr, conflict_reasons)
    total_score = _total_score(setup_score, trigger_score, risk_score)
    status = _status_from_score(total_score, trigger_passed, rr, setup_score, trigger_score, phase)
    entry_hint = _entry_hint(status, phase, long_side, "obv_divergence")
    entry_price = _entry_price(state, long_side, "obv_divergence", phase, status)
    entry_reference = _entry_reference_payload(state, long_side, "obv_divergence", phase, status, entry_price, stop_loss)
    matched = setup_matched + trigger_matched
    missing = setup_missing + trigger_missing
    failed = _failed_from_conflicts(conflict_reasons)
    explanation = _strategy_explanation(definition, status, matched, missing, conflict_reasons)
    return StrategyResult(
        id=definition.id,
        label=_strategy_public_label(definition),
        canonical_label=definition.label,
        direction=definition.direction,
        category=definition.category,
        score=total_score,
        status=status,
        phase=phase,
        entry_hint=entry_hint,
        presentation_type=definition.presentation_type,
        implementation_level=definition.implementation_level,
        deterministic=definition.deterministic,
        entry_reference_type=entry_reference["entry_reference_type"],
        entry_reference_text=entry_reference["entry_reference_text"],
        entry_price=entry_price,
        interest_low=entry_reference["interest_low"],
        interest_high=entry_reference["interest_high"],
        confirmation_level=entry_reference["confirmation_level"],
        invalidation_level=entry_reference["invalidation_level"],
        setup_score=setup_score,
        trigger_score=trigger_score,
        risk_score=risk_score,
        matched_conditions=matched,
        missing_conditions=missing,
        failed_conditions=failed,
        stop_loss=stop_loss,
        target_1=target_1,
        target_2=target_2,
        rr=rr,
        conflict_reasons=conflict_reasons,
        explanation=explanation,
        last5_change=_recent_change_notes(state, long_side),
        invalidation_text=_reversal_invalidation_text(state, long_side, stop_loss),
        note=_phase_note(phase, conflict_reasons),
    )


def _evaluate_keltner_pullback(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    trend = state["trend"]
    structure = state["structure"]
    volume_flow = state["volume_flow"]
    momentum = state["momentum"]
    patterns = state["patterns"]
    signals = state["signals"]

    setup_items = [
        (_side(long_side, trend["ema21_above_ma50"] and trend["close_above_ma20"], trend["ema21_below_ma50"] and trend["close_below_ma20"]), "상위 추세와 Keltner 기준선 정렬", 15),
        (_side(long_side, structure["pullback_near_kc_mid_long"], structure["pullback_near_kc_mid_short"]), "Keltner mid 눌림 구간 접근", 15),
        (_side(long_side, trend["close_above_vwap"], trend["close_below_vwap"]), "VWAP 방향 우위 유지", 8),
        (_side(long_side, volume_flow["volume_support"], volume_flow["volume_support"]), "눌림 중 거래량 지지", 7),
    ]
    trigger_items = [
        (_side(long_side, signals["EMA_Pullback_Buy"] or patterns["bullish_reversal_candle"], signals["EMA_Pullback_Sell"] or patterns["bearish_reversal_candle"]), "Keltner 눌림 뒤 반전 캔들", 15),
        (_side(long_side, signals["UTBot_Buy"] or signals["Hull_Turn_Bull"], signals["UTBot_Sell"] or signals["Hull_Turn_Bear"]), "보조 추세 신호 정렬", 10),
        (_side(long_side, momentum["macd_hist_rising"], momentum["macd_hist_falling"]), "모멘텀 재확장", 10),
    ]
    return _build_result_from_groups(
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
        risk_template=_risk_template_trend,
        invalidation_builder=_trend_invalidation_text,
    )


def _evaluate_keltner_breakout(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    trend = state["trend"]
    volume_flow = state["volume_flow"]
    momentum = state["momentum"]
    structure = state["structure"]
    signals = state["signals"]

    setup_items = [
        (_side(long_side, structure["near_breakout_long"], structure["near_breakout_short"]), "Keltner 상단/하단 돌파 구간 접근", 12),
        (_side(long_side, trend["close_above_ema21"], trend["close_below_ema21"]), "EMA21 방향 정렬", 10),
        (_side(long_side, trend["adx_strong"], trend["adx_strong"]), "추세 강도 확보", 8),
        (_side(long_side, volume_flow["volume_support"], volume_flow["volume_support"]), "돌파 전 거래량 준비", 10),
        (_side(long_side, momentum["bb_width_contracting"] or momentum["squeeze_recent"], momentum["bb_width_contracting"] or momentum["squeeze_recent"]), "돌파 전 변동성 수축", 5),
    ]
    trigger_items = [
        (_side(long_side, state["price"]["close"] >= state["price"]["kc_upper"] or signals["Expansion_BO"], state["price"]["close"] <= state["price"]["kc_lower"] or signals["Expansion_BD"]), "Keltner 밴드 돌파 종가 확정", 15),
        (_side(long_side, signals["Channel_Breakout_Bull"] or signals["Box_Breakout_Bull"] or signals["CS_Breakout_Confirm_Buy"], signals["Channel_Breakdown_Bear"] or signals["Box_Breakdown_Bear"] or signals["CS_Breakout_Confirm_Sell"]), "돌파 확인 시그널 발생", 10),
        (_side(long_side, volume_flow["volume_burst"], volume_flow["volume_burst"]), "돌파봉 거래량 증가", 5),
        (_side(long_side, momentum["macd_hist_rising"], momentum["macd_hist_falling"]), "돌파 후 모멘텀 확장", 5),
    ]
    extra_conflicts = []
    if _side(long_side, state["price"]["close"] < state["price"]["kc_upper"], state["price"]["close"] > state["price"]["kc_lower"]):
        extra_conflicts.append("Keltner 외곽 밴드 안착이 아직 완전하지 않습니다.")
    return _build_result_from_groups(
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
        risk_template=_risk_template_breakout,
        invalidation_builder=_breakout_invalidation_text,
        extra_conflicts=extra_conflicts,
    )


def _evaluate_keltner_mean_reversion(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    structure = state["structure"]
    volume_flow = state["volume_flow"]
    momentum = state["momentum"]
    patterns = state["patterns"]
    signals = state["signals"]
    trend = state["trend"]

    setup_items = [
        (_side(long_side, structure["outside_keltner_lower"], structure["outside_keltner_upper"]), "Keltner 외곽 과확장", 15),
        (_side(long_side, momentum["deep_oversold"], momentum["deep_overbought"]), "오실레이터 극단 구간", 10),
        (_side(long_side, volume_flow["money_flow_improving"], volume_flow["money_flow_weakening"]), "자금흐름 개선", 10),
        (_side(long_side, structure["price_change_5"] <= -3.0, structure["price_change_5"] >= 3.0), "단기 과매도/과매수 확인", 10),
    ]
    trigger_items = [
        (_side(long_side, patterns["bullish_reversal_candle"] or patterns["volume_climax_buy"], patterns["bearish_reversal_candle"] or patterns["volume_climax_sell"]), "반전 캔들 확인", 15),
        (_side(long_side, state["price"]["close"] >= state["price"]["kc_mid"] or signals["VWAP_Bounce_Buy"], state["price"]["close"] <= state["price"]["kc_mid"] or signals["VWAP_Reject_Sell"]), "Keltner mid 복귀", 10),
        (_side(long_side, momentum["macd_hist_rising"], momentum["macd_hist_falling"]), "반전 모멘텀 개선", 10),
    ]
    if _side(long_side, not trend["close_above_vwap"], not trend["close_below_vwap"]):
        extra_conflicts = ["VWAP 방향 회복이 아직 완전하지 않습니다."]
    else:
        extra_conflicts = []
    return _build_result_from_groups(
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
        risk_template=_risk_template_reversal,
        invalidation_builder=_reversal_invalidation_text,
        extra_conflicts=extra_conflicts,
    )


def _evaluate_vwap_reclaim(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    trend = state["trend"]
    structure = state["structure"]
    volume_flow = state["volume_flow"]
    momentum = state["momentum"]
    signals = state["signals"]

    setup_items = [
        (_side(long_side, structure["pullback_near_fixed_vwap_long"] or structure["pullback_near_kc_mid_long"], structure["pullback_near_fixed_vwap_short"] or structure["pullback_near_kc_mid_short"]), "VWAP / AVWAP 재테스트 구간", 12),
        (_side(long_side, trend["close_above_ema21"], trend["close_below_ema21"]), "단기 추세 정렬", 10),
        (_side(long_side, volume_flow["money_flow_improving"], volume_flow["money_flow_weakening"]), "수급 방향 일치", 10),
        (_side(long_side, volume_flow["volume_support"], volume_flow["volume_support"]), "거래량 지지", 8),
    ]
    trigger_items = [
        (_side(long_side, signals["VWAP_Bounce_Buy"] or trend["vwap_reclaimed_long"], signals["VWAP_Reject_Sell"] or trend["vwap_reclaimed_short"]), "VWAP 재장악 / 거절 확인", 15),
        (_side(long_side, trend["close_above_vwap"], trend["close_below_vwap"]), "종가 기준 VWAP 우위", 10),
        (_side(long_side, signals["UTBot_Buy"] or momentum["macd_hist_rising"], signals["UTBot_Sell"] or momentum["macd_hist_falling"]), "후속 확인 신호", 10),
    ]
    return _build_result_from_groups(
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
        risk_template=_risk_template_reversal,
        invalidation_builder=_reversal_invalidation_text,
    )


def _evaluate_morning_star_fib(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    volume_flow = state["volume_flow"]
    momentum = state["momentum"]
    signals = state["signals"]
    patterns = state["patterns"]
    structure = state["structure"]

    fib_support_long = any(signals[key] for key in ("Fib_50_Support", "Fib_618_Support", "Fib_618_Reclaim", "Fib_Confluence_Buy"))
    fib_support_short = any(signals[key] for key in ("Fib_50_Resistance", "Fib_618_Resistance", "Fib_618_Breakdown", "Fib_Confluence_Sell"))
    setup_items = [
        (_side(long_side, fib_support_long, fib_support_short), "Fib 0.5 / 0.618 골든존 지지", 18),
        (_side(long_side, structure["lower_zone"] or structure["pullback_near_fixed_vwap_long"], structure["upper_zone"] or structure["pullback_near_fixed_vwap_short"]), "가격 구조상 되돌림 완료", 12),
        (_side(long_side, volume_flow["money_flow_improving"], volume_flow["money_flow_weakening"]), "자금흐름 확인", 8),
        (_side(long_side, structure["price_change_5"] < 0, structure["price_change_5"] > 0), "직전 조정 파동 존재", 7),
    ]
    trigger_items = [
        (_side(long_side, patterns["morning_star"] or patterns["bullish_reversal_candle"], patterns["evening_star"] or patterns["bearish_reversal_candle"]), "패턴 캔들 완성", 15),
        (_side(long_side, signals["VWAP_Bounce_Buy"] or state["price"]["close"] >= state["price"]["ema8"], signals["VWAP_Reject_Sell"] or state["price"]["close"] <= state["price"]["ema8"]), "3번째 봉 기준선 회복", 10),
        (_side(long_side, momentum["macd_hist_rising"], momentum["macd_hist_falling"]), "모멘텀 개선", 10),
    ]
    return _build_result_from_groups(
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
        risk_template=_risk_template_reversal,
        invalidation_builder=_reversal_invalidation_text,
    )


def _evaluate_fractal_breakout(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    trend = state["trend"]
    volume_flow = state["volume_flow"]
    momentum = state["momentum"]
    patterns = state["patterns"]
    structure = state["structure"]
    signals = state["signals"]

    setup_items = [
        (_side(long_side, trend["close_above_ema21"], trend["close_below_ema21"]), "EMA21 방향 우위", 12),
        (_side(long_side, np.isfinite(structure["recent_fractal_high"]), np.isfinite(structure["recent_fractal_low"])), "최근 유효 fractal 존재", 10),
        (_side(long_side, volume_flow["volume_support"], volume_flow["volume_support"]), "거래량 준비", 8),
        (_side(long_side, trend["adx_strong"], trend["adx_strong"]), "추세 강도 확인", 8),
    ]
    trigger_items = [
        (_side(long_side, structure["fractal_breakout_long"], structure["fractal_breakout_short"]), "fractal 돌파 / 이탈 확정", 15),
        (_side(long_side, patterns["fractal_high"] or signals["Channel_Breakout_Bull"], patterns["fractal_low"] or signals["Channel_Breakdown_Bear"]), "fractal 시그널 동반", 10),
        (_side(long_side, volume_flow["volume_burst"], volume_flow["volume_burst"]), "돌파 거래량 증가", 5),
        (_side(long_side, momentum["macd_hist_rising"], momentum["macd_hist_falling"]), "후속 모멘텀 정렬", 5),
    ]
    return _build_result_from_groups(
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
        risk_template=_risk_template_breakout,
        invalidation_builder=_breakout_invalidation_text,
    )


def _evaluate_anchored_vwap(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    trend = state["trend"]
    structure = state["structure"]
    volume_flow = state["volume_flow"]
    momentum = state["momentum"]
    patterns = state["patterns"]
    signals = state["signals"]

    setup_items = [
        (_side(long_side, trend["fixed_vwap_holding_long"], trend["fixed_vwap_holding_short"]), "Anchored VWAP 방향 유지", 15),
        (_side(long_side, structure["pullback_near_fixed_vwap_long"], structure["pullback_near_fixed_vwap_short"]), "AVWAP 리테스트 구간", 12),
        (_side(long_side, trend["ema21_above_ma50"], trend["ema21_below_ma50"]), "상위 추세 정렬", 10),
        (_side(long_side, volume_flow["volume_support"], volume_flow["volume_support"]), "거래량 바닥 붕괴 없음", 8),
    ]
    trigger_items = [
        (_side(long_side, signals["VWAP_Bounce_Buy"] or patterns["bullish_reversal_candle"], signals["VWAP_Reject_Sell"] or patterns["bearish_reversal_candle"]), "AVWAP 반등 / 거절 캔들", 15),
        (_side(long_side, trend["close_above_fixed_vwap"], trend["close_below_fixed_vwap"]), "종가 기준 AVWAP 유지", 10),
        (_side(long_side, signals["UTBot_Buy"] or momentum["macd_hist_rising"], signals["UTBot_Sell"] or momentum["macd_hist_falling"]), "후속 추세 확인", 10),
    ]
    return _build_result_from_groups(
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
        risk_template=_risk_template_trend,
        invalidation_builder=_trend_invalidation_text,
    )


def _evaluate_accumulation_pattern(definition: StrategyDefinition, state: dict) -> StrategyResult:
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
    return _build_result_from_groups(
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
        risk_template=_risk_template_trend,
        invalidation_builder=_trend_invalidation_text,
    )


def _evaluate_poc_rotation(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    structure = state["structure"]
    volume_flow = state["volume_flow"]
    trend = state["trend"]
    momentum = state["momentum"]
    signals = state["signals"]

    setup_items = [
        (_side(long_side, structure["near_vp_poc"] or structure["near_vp_val"] or structure["inside_value_area"], structure["near_vp_poc"] or structure["near_vp_vah"] or structure["inside_value_area"]), "POC / Value Area 근접", 15),
        (_side(long_side, signals["VP_VAL_Support"] or trend["close_above_vwap"], signals["VP_VAH_Resistance"] or trend["close_below_vwap"]), "Value Area 지지/저항 확인", 10),
        (_side(long_side, volume_flow["volume_support"], volume_flow["volume_support"]), "회전 매매용 거래량 유지", 8),
        (_side(long_side, volume_flow["money_flow_improving"], volume_flow["money_flow_weakening"]), "수급 방향 일치", 7),
    ]
    trigger_items = [
        (_side(long_side, signals["Volume_POC_Breakout"] or (structure["near_vp_poc"] and trend["close_above_vwap"]), signals["Volume_POC_Breakdown"] or (structure["near_vp_poc"] and trend["close_below_vwap"])), "POC 재장악 / 이탈", 15),
        (_side(long_side, momentum["macd_hist_rising"], momentum["macd_hist_falling"]), "회전 모멘텀 확인", 10),
        (_side(long_side, volume_flow["volume_burst"] or signals["VP_VAL_Support"], volume_flow["volume_burst"] or signals["VP_VAH_Resistance"]), "Value Area 리액션 동반", 10),
    ]
    return _build_result_from_groups(
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
        risk_template=_risk_template_breakout,
        invalidation_builder=_breakout_invalidation_text,
    )


def _evaluate_ichimoku_breakout(definition: StrategyDefinition, state: dict) -> StrategyResult:
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
        (_side(long_side, above_cloud, below_cloud), "구름대 상/하단 이탈", 15),
        (_side(long_side, tk_bull, tk_bear), "Tenkan / Kijun 정렬", 10),
        (_side(long_side, trend["adx_strong"], trend["adx_strong"]), "추세 강도 확인", 10),
        (_side(long_side, volume_flow["volume_support"], volume_flow["volume_support"]), "구름 돌파 거래량 준비", 10),
    ]
    trigger_items = [
        (_side(long_side, signals["Kumo_Breakout_Bull"] or signals["CS_Ichimoku_Breakout_Buy"], signals["Kumo_Breakout_Bear"] or signals["CS_Ichimoku_Breakout_Sell"]), "Kumo 돌파 신호 발생", 15),
        (_side(long_side, signals["TK_Cross_Bull"] or tk_bull, signals["TK_Cross_Bear"] or tk_bear), "TK 교차 확인", 10),
        (_side(long_side, momentum["macd_hist_rising"], momentum["macd_hist_falling"]), "모멘텀 후속 확장", 10),
    ]
    return _build_result_from_groups(
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
        risk_template=_risk_template_breakout,
        invalidation_builder=_breakout_invalidation_text,
    )


def _evaluate_fractal_alligator(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    trend = state["trend"]
    structure = state["structure"]
    volume_flow = state["volume_flow"]
    momentum = state["momentum"]
    signals = state["signals"]
    patterns = state["patterns"]

    setup_items = [
        (_side(long_side, trend["close_above_ema21"] and trend["ema21_above_ma50"], trend["close_below_ema21"] and trend["ema21_below_ma50"]), "Alligator 대체 추세 정렬", 15),
        (_side(long_side, np.isfinite(structure["recent_fractal_high"]), np.isfinite(structure["recent_fractal_low"])), "fractal 레벨 준비", 10),
        (_side(long_side, trend["adx_expanding"], trend["adx_expanding"]), "sleeping → awakening 추세 강화", 10),
        (_side(long_side, volume_flow["volume_support"], volume_flow["volume_support"]), "거래량 유지", 10),
    ]
    trigger_items = [
        (_side(long_side, structure["fractal_breakout_long"], structure["fractal_breakout_short"]), "fractal 돌파", 15),
        (_side(long_side, signals["Hull_Turn_Bull"] or signals["UTBot_Buy"], signals["Hull_Turn_Bear"] or signals["UTBot_Sell"]), "추세 전환 보조 신호", 10),
        (_side(long_side, patterns["fractal_high"] or momentum["macd_hist_rising"], patterns["fractal_low"] or momentum["macd_hist_falling"]), "돌파 후 방향성 유지", 10),
    ]
    return _build_result_from_groups(
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
        risk_template=_risk_template_trend,
        invalidation_builder=_trend_invalidation_text,
    )


def _evaluate_chaikin_flow(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    volume_flow = state["volume_flow"]
    momentum = state["momentum"]
    structure = state["structure"]
    trend = state["trend"]
    signals = state["signals"]

    setup_items = [
        (_side(long_side, volume_flow["chaikin_positive"], volume_flow["chaikin_negative"]), "Chaikin 방향 전환", 15),
        (_side(long_side, volume_flow["cmf_positive"], volume_flow["cmf_negative"]), "CMF 방향 동조", 10),
        (_side(long_side, structure["lower_zone"] or structure["price_change_5"] <= -2.0, structure["upper_zone"] or structure["price_change_5"] >= 2.0), "가격은 아직 바닥/천장권", 10),
        (_side(long_side, volume_flow["volume_support"], volume_flow["volume_support"]), "수급 유입 유지", 10),
    ]
    trigger_items = [
        (_side(long_side, volume_flow["chaikin_cross_up"] or signals["CMF_Bull"], volume_flow["chaikin_cross_down"] or signals["CMF_Bear"]), "Chaikin / CMF 트리거", 15),
        (_side(long_side, trend["close_above_vwap"] or state["price"]["close"] >= state["price"]["ema8"], trend["close_below_vwap"] or state["price"]["close"] <= state["price"]["ema8"]), "가격 확인 봉", 10),
        (_side(long_side, momentum["macd_hist_rising"], momentum["macd_hist_falling"]), "모멘텀 개선", 10),
    ]
    return _build_result_from_groups(
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
        risk_template=_risk_template_reversal,
        invalidation_builder=_reversal_invalidation_text,
    )


def _build_result_from_groups(
    definition: StrategyDefinition,
    state: dict,
    long_side: bool,
    family: str,
    setup_items: list[tuple[bool, str, int]],
    trigger_items: list[tuple[bool, str, int]],
    trigger_threshold: float,
    setup_threshold: float,
    triggered_phase: str,
    ready_phase: str,
    risk_template,
    invalidation_builder,
    extra_conflicts: list[str] | None = None,
) -> StrategyResult:
    setup_score, setup_matched, setup_missing = _score_group(setup_items)
    trigger_score, trigger_matched, trigger_missing = _score_group(trigger_items)
    trigger_passed = trigger_score >= trigger_threshold
    phase = triggered_phase if trigger_passed else ready_phase if setup_score >= setup_threshold else "SETUP_INVALID"
    stop_loss, target_1, target_2, rr = risk_template(state, long_side)
    conflict_reasons = _default_conflicts(state, long_side)
    if extra_conflicts:
        conflict_reasons.extend(extra_conflicts)
    conflict_reasons = _ordered_unique(conflict_reasons)
    risk_score = _risk_score(stop_loss, target_1, state["price"]["entry"], rr, conflict_reasons)
    total_score = _total_score(setup_score, trigger_score, risk_score)
    status = _status_from_score(total_score, trigger_passed, rr, setup_score, trigger_score, phase)
    entry_hint = _entry_hint(status, phase, long_side, family)
    entry_price = _entry_price(state, long_side, family, phase, status)
    entry_reference = _entry_reference_payload(state, long_side, family, phase, status, entry_price, stop_loss)
    matched = setup_matched + trigger_matched
    missing = setup_missing + trigger_missing
    failed = _failed_from_conflicts(conflict_reasons)
    explanation = _strategy_explanation(definition, status, matched, missing, conflict_reasons)
    return StrategyResult(
        id=definition.id,
        label=_strategy_public_label(definition),
        canonical_label=definition.label,
        direction=definition.direction,
        category=definition.category,
        score=total_score,
        status=status,
        phase=phase,
        entry_hint=entry_hint,
        presentation_type=definition.presentation_type,
        implementation_level=definition.implementation_level,
        deterministic=definition.deterministic,
        entry_reference_type=entry_reference["entry_reference_type"],
        entry_reference_text=entry_reference["entry_reference_text"],
        entry_price=entry_price,
        interest_low=entry_reference["interest_low"],
        interest_high=entry_reference["interest_high"],
        confirmation_level=entry_reference["confirmation_level"],
        invalidation_level=entry_reference["invalidation_level"],
        setup_score=setup_score,
        trigger_score=trigger_score,
        risk_score=risk_score,
        matched_conditions=matched,
        missing_conditions=missing,
        failed_conditions=failed,
        stop_loss=stop_loss,
        target_1=target_1,
        target_2=target_2,
        rr=rr,
        conflict_reasons=conflict_reasons,
        explanation=explanation,
        last5_change=_recent_change_notes(state, long_side),
        invalidation_text=invalidation_builder(state, long_side, stop_loss),
        note=_phase_note(phase, conflict_reasons),
    )


