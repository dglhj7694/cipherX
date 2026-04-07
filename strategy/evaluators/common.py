from __future__ import annotations


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
