from __future__ import annotations


STATUS_TEXT = {
    "ACTIVE": "성립 단계입니다.",
    "CONFIRMING": "확인 진행 단계입니다.",
    "TRIGGER_WAIT": "트리거 대기 단계입니다.",
    "READY": "준비 단계입니다.",
    "INTEREST": "관심 단계입니다.",
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
    matched_text = ", ".join(matched[:3]) or "핵심 근거가 아직 충분하지 않습니다"
    weak_text = ", ".join((missing + conflicts)[:3])
    if weak_text:
        return f"{intro} 현재 {status_text} {matched_text}는 확인됐지만, {weak_text}은 추가 확인이 필요합니다."
    return f"{intro} 현재 {status_text} {matched_text}가 함께 맞물리고 있습니다."


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
        if direction == "LONG":
            base = f"{label}은 구름 상단 돌파와 bullish TK 정렬을 추적하는 전략입니다."
        else:
            base = f"{label}은 구름 하단 이탈과 bearish TK 정렬을 추적하는 전략입니다."
    elif family == "anchored_vwap":
        base = f"{label}는 현재 이벤트 앵커 AVWAP이 아니라 Fixed VWAP 기준으로 보는 컨텍스트 평가입니다."
    elif family == "fractal_alligator":
        base = f"{label}는 현재 Alligator jaw/teeth/lips 대신 EMA 추세 스택과 fractal 구조로 보는 컨텍스트 평가입니다."
    elif family == "supertrend_psar":
        base = f"{label}는 SuperTrend와 PSAR의 {direction_word} 정렬을 확인하는 컨텍스트 평가입니다."
    elif family == "fractal_breakout":
        base = f"{label}는 fractal breakout 구조를 감시하는 컨텍스트 평가입니다."
    elif family == "chaikin_flow":
        base = f"{label}는 Chaikin/CMF 자금흐름을 중심으로 보는 컨텍스트 평가입니다."
    else:
        base = f"{label}은 {canonical_label} 기준으로 평가한 전략입니다."
    if presentation_type == "context" and "컨텍스트 평가" not in base:
        return f"{base} 현재는 완전 독립 전략명보다 컨텍스트형 표시를 사용합니다."
    if implementation_level in {"partial", "proxy"} and family not in {
        "anchored_vwap",
        "fractal_alligator",
        "supertrend_psar",
        "fractal_breakout",
        "chaikin_flow",
    }:
        return f"{base} 현재 구현은 부분형입니다."
    return base
