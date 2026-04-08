from __future__ import annotations

from typing import Callable

from ..models import StrategyDefinition, StrategyResult
from ..presentation import (
    entry_hint,
    entry_price,
    entry_reference_payload,
    phase_note,
    recent_change_notes,
    strategy_explanation,
    strategy_public_label,
)
from ..risk import default_conflicts, risk_score
from ..state_builder import ordered_unique


def score_group(items: list[tuple[bool, str, int]]) -> tuple[float, list[str], list[str]]:
    score = 0.0
    matched: list[str] = []
    missing: list[str] = []
    for condition, label, weight in items:
        if condition:
            score += float(weight)
            matched.append(label)
        else:
            missing.append(label)
    return score, matched, missing


def total_score(setup_score: float, trigger_score: float, risk_score: float) -> float:
    return max(0.0, min(100.0, setup_score + trigger_score + risk_score))


def status_from_score(
    total_score_value: float,
    trigger_passed: bool,
    rr: float | None,
    setup_score: float = 0.0,
    trigger_score: float = 0.0,
    phase: str = "",
) -> str:
    phase = str(phase or "").upper()
    trigger_wait_phases = {
        "PULLBACK_WAIT",
        "BREAKOUT_PENDING",
        "SQUEEZE_READY",
        "REVERSAL_READY",
        "DIVERGENCE_READY",
        "TREND_ALIGNED",
        "MEAN_REVERSION_READY",
        "VWAP_RECLAIM_PENDING",
        "FIB_GOLDEN_ZONE_WAIT",
        "FRACTAL_BREAKOUT_PENDING",
        "AVWAP_HOLD",
        "ACCUMULATION_READY",
        "VALUE_ROTATION_READY",
        "ICHI_PENDING",
        "ALLIGATOR_AWAKENING",
        "CHAIKIN_READY",
        "KELTNER_BREAKOUT_PENDING",
    }
    if total_score_value >= 80 and trigger_passed and (rr is None or rr >= 1.3):
        return "ACTIVE"
    if trigger_passed:
        return "CONFIRMING"
    if phase in trigger_wait_phases or trigger_score >= 15:
        if total_score_value >= 60 or (setup_score >= 25 and trigger_score >= 10):
            return "TRIGGER_WAIT"
        if setup_score >= 20 or total_score_value >= 55:
            return "READY"
        if setup_score >= 10 or total_score_value >= 35:
            return "INTEREST"
        return "INVALID"
    if setup_score >= 20 or total_score_value >= 55:
        return "READY"
    if setup_score >= 10 or total_score_value >= 35:
        return "INTEREST"
    return "INVALID"


def side(long_side: bool, long_value: bool, short_value: bool) -> bool:
    return bool(long_value if long_side else short_value)


def failed_from_conflicts(conflicts: list[str]) -> list[str]:
    return [text for text in conflicts[:3]]


def build_result(
    definition: StrategyDefinition,
    state: dict,
    long_side: bool,
    family: str,
    setup_score: float,
    trigger_score: float,
    trigger_passed: bool,
    phase: str,
    stop_loss: float | None,
    target_1: float | None,
    target_2: float | None,
    rr: float | None,
    matched: list[str],
    missing: list[str],
    conflict_reasons: list[str],
    invalidation_builder: Callable[[dict, bool, float | None], str],
) -> StrategyResult:
    conflict_reasons = ordered_unique(conflict_reasons)
    risk_value = risk_score(stop_loss, target_1, state["price"]["entry"], rr, conflict_reasons)
    total = total_score(setup_score, trigger_score, risk_value)
    status = status_from_score(total, trigger_passed, rr, setup_score, trigger_score, phase)
    hint = entry_hint(status, phase, long_side, family)
    price = entry_price(state, long_side, family, phase, status)
    reference = entry_reference_payload(state, long_side, family, phase, status, price, stop_loss)
    failed = failed_from_conflicts(conflict_reasons)
    explanation = strategy_explanation(definition, status, matched, missing, conflict_reasons)
    return StrategyResult(
        id=definition.id,
        label=strategy_public_label(definition),
        canonical_label=definition.label,
        direction=definition.direction,
        category=definition.category,
        score=total,
        status=status,
        phase=phase,
        entry_hint=hint,
        presentation_type=definition.presentation_type,
        implementation_level=definition.implementation_level,
        deterministic=definition.deterministic,
        entry_reference_type=reference["entry_reference_type"],
        entry_reference_text=reference["entry_reference_text"],
        entry_price=price,
        interest_low=reference["interest_low"],
        interest_high=reference["interest_high"],
        confirmation_level=reference["confirmation_level"],
        invalidation_level=reference["invalidation_level"],
        setup_score=setup_score,
        trigger_score=trigger_score,
        risk_score=risk_value,
        matched_conditions=matched,
        missing_conditions=missing,
        failed_conditions=failed,
        stop_loss=stop_loss,
        target_1=target_1,
        target_2=target_2,
        rr=rr,
        conflict_reasons=conflict_reasons,
        explanation=explanation,
        last5_change=recent_change_notes(state, long_side),
        invalidation_text=invalidation_builder(state, long_side, stop_loss),
        note=phase_note(phase, conflict_reasons),
    )


def build_result_from_groups(
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
    risk_template: Callable[[dict, bool], tuple[float | None, float | None, float | None, float | None]],
    invalidation_builder: Callable[[dict, bool, float | None], str],
    extra_conflicts: list[str] | None = None,
) -> StrategyResult:
    setup_score, setup_matched, setup_missing = score_group(setup_items)
    trigger_score, trigger_matched, trigger_missing = score_group(trigger_items)
    trigger_passed = trigger_score >= trigger_threshold
    phase = triggered_phase if trigger_passed else ready_phase if setup_score >= setup_threshold else "SETUP_INVALID"
    stop_loss, target_1, target_2, rr = risk_template(state, long_side)
    conflicts = default_conflicts(state, long_side)
    if extra_conflicts:
        conflicts.extend(extra_conflicts)
    return build_result(
        definition=definition,
        state=state,
        long_side=long_side,
        family=family,
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
        invalidation_builder=invalidation_builder,
    )
