from __future__ import annotations


STATUS_TEXT = {
    "ACTIVE": "성립 단계입니다.",
    "CONFIRMING": "확인 진행 단계입니다.",
    "TRIGGER_WAIT": "트리거 대기 단계입니다.",
    "READY": "준비 단계입니다.",
    "INTEREST": "관심 단계입니다.",
    "LONG_ENTRY": "롱 진입 단계입니다.",
    "LONG_ALIGNED": "롱 정렬 단계입니다.",
    "LONG_WAIT": "롱 대기 단계입니다.",
    "SHORT_ENTRY": "숏 진입 단계입니다.",
    "SHORT_ALIGNED": "숏 정렬 단계입니다.",
    "SHORT_WAIT": "숏 대기 단계입니다.",
    "EXIT_WARNING": "청산 경고 단계입니다.",
    "INVALID": "아직 조건이 부족합니다.",
}


def build_strategy_explanation(
    *,
    label: str,
    canonical_label: str,
    family: str,
    direction: str,
    status: str,
    matched: list[str],
    missing: list[str],
    conflicts: list[str],
    presentation_type: str,
    implementation_level: str,
) -> str:
    status_text = STATUS_TEXT.get(str(status or "").upper(), "준비 단계입니다.")
    direction_text = "LONG" if str(direction or "").upper() == "LONG" else "SHORT"
    intro = _family_intro(
        family=family,
        direction=direction_text,
        label=label,
        canonical_label=canonical_label,
        presentation_type=presentation_type,
        implementation_level=implementation_level,
    )
    matched_text = ", ".join(matched[:3]) or "핵심 조건 확인 중"
    weak_text = ", ".join((missing + conflicts)[:3])
    if weak_text:
        return f"{intro} 현재 {status_text} {matched_text}. 추가 확인: {weak_text}."
    return f"{intro} 현재 {status_text} {matched_text}."


def _family_intro(
    *,
    family: str,
    direction: str,
    label: str,
    canonical_label: str,
    presentation_type: str,
    implementation_level: str,
) -> str:
    direction_word = "상방" if direction == "LONG" else "하방"
    if family == "ichimoku_breakout":
        base = f"{label}은 Ichimoku {direction_word} 돌파를 추적합니다."
    elif family == "anchored_vwap":
        base = f"{label}은 Anchored VWAP 컨텍스트를 추적합니다."
    elif family == "fractal_alligator":
        base = f"{label}은 Fractal + Alligator 컨텍스트를 추적합니다."
    elif family == "supertrend_psar":
        base = f"{label}은 SuperTrend + PSAR 정렬을 확인합니다."
    elif family == "fractal_breakout":
        base = f"{label}은 Fractal 구조 돌파를 확인합니다."
    elif family == "chaikin_flow":
        base = f"{label}은 Chaikin/CMF 자금 흐름을 추적합니다."
    elif family == "hma_ema_trend":
        base = f"{label}은 EMA200 기준 HMA/EMA 정렬을 추적합니다."
    else:
        base = f"{label}은 {canonical_label} 기반 전략입니다."
    if presentation_type == "context":
        return f"{base} 현재는 컨텍스트형 모델입니다."
    if implementation_level in {"partial", "proxy"}:
        return f"{base} 현재 구현 단계는 {implementation_level}입니다."
    return base

