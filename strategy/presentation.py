from __future__ import annotations

from typing import Iterable

import numpy as np

from .explainer import build_strategy_explanation
from .models import StrategyDefinition
from .state_builder import finite_max, finite_min, pct_change, scalar


def strategy_public_label(definition: StrategyDefinition) -> str:
    return str(definition.ui_label or definition.label)


def strategy_explanation(
    definition: StrategyDefinition,
    status: str,
    matched: list[str],
    missing: list[str],
    conflicts: list[str],
) -> str:
    return build_strategy_explanation(
        label=strategy_public_label(definition),
        canonical_label=definition.label,
        family=definition.family,
        direction=definition.direction,
        status=status,
        matched=matched,
        missing=missing,
        conflicts=conflicts,
        presentation_type=definition.presentation_type,
        implementation_level=definition.implementation_level,
    )


def recent_change_notes(state: dict, long_side: bool) -> list[str]:
    frame = state["frame"]
    if frame.empty:
        return []
    recent = frame.tail(5)
    notes: list[str] = []
    close_now = scalar(recent.iloc[-1].get("Close"))
    close_then = scalar(recent.iloc[0].get("Close"), close_now)
    change_pct = pct_change(close_now, close_then)
    notes.append(f"최근 5봉 가격 변화 {change_pct:+.1f}%")
    volume_ratio = scalar(recent.iloc[-1].get("Volume_Ratio_20"), 1.0)
    notes.append(f"최근 거래량은 20일 평균 대비 {volume_ratio:.1f}배")
    macd_delta = scalar(recent.iloc[-1].get("MACD_Hist")) - scalar(recent.iloc[0].get("MACD_Hist"))
    notes.append(f"MACD 히스토그램은 5봉 기준 {macd_delta:+.3f} 변화")
    if long_side:
        notes.append("VWAP 위 안착 여부가 마지막 확인 포인트입니다." if state["trend"]["close_above_vwap"] else "VWAP 재회복 여부가 마지막 확인 포인트입니다.")
    else:
        notes.append("VWAP 아래 유지 여부가 마지막 확인 포인트입니다." if state["trend"]["close_below_vwap"] else "VWAP 재이탈 여부가 마지막 확인 포인트입니다.")
    return notes[:4]


def sorted_finite(values: Iterable[float]) -> list[float]:
    cleaned: list[float] = []
    for value in values:
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if np.isfinite(number):
            cleaned.append(number)
    return sorted(cleaned)


def range_pair(values: Iterable[float], fallback: float | None = None) -> tuple[float | None, float | None]:
    ordered = sorted_finite(values)
    if ordered:
        return ordered[0], ordered[-1]
    if fallback is None:
        return None, None
    return fallback, fallback


def format_price_text(value: float | None) -> str:
    if value is None:
        return "-"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "-"
    if not np.isfinite(number):
        return "-"
    return f"{number:.2f}"


def format_range_text(low: float | None, high: float | None) -> str:
    low_text = format_price_text(low)
    high_text = format_price_text(high)
    if low_text == "-" and high_text == "-":
        return "-"
    if low_text == high_text:
        return low_text
    return f"{low_text}~{high_text}"


def confirmation_level(state: dict, long_side: bool, family: str, phase: str) -> float | None:
    price = state["price"]
    levels = state["levels"]
    structure = state["structure"]
    if family in {"breakout", "squeeze"}:
        return structure["breakout_level"] if long_side else structure["breakdown_level"]
    if family == "keltner_breakout":
        return price["kc_upper"] if long_side else price["kc_lower"]
    if family == "ichimoku_breakout":
        return levels["cloud_top"] if long_side else levels["cloud_bottom"]
    if family in {"fractal_breakout", "fractal_alligator"}:
        return structure["recent_fractal_high"] if long_side else structure["recent_fractal_low"]
    if family in {"reversal", "obv_divergence", "chaikin_flow", "vwap_reclaim"}:
        return finite_max([price["ema8"], levels["vwap"]], np.nan) if long_side else finite_min([price["ema8"], levels["vwap"]], np.nan)
    if family == "morning_star_fib":
        return finite_max([levels["fib_50"], levels["fib_618"], levels["vwap"]], np.nan) if long_side else finite_min([levels["fib_50"], levels["fib_618"], levels["vwap"]], np.nan)
    if family == "poc_rotation":
        return levels["vp_poc"]
    if family == "accumulation_pattern":
        return finite_max([levels["vp_poc"], levels["fixed_vwap"], structure["breakout_level"]], np.nan)
    if family == "supertrend_psar":
        return price["ema21"]
    if phase in {"BREAKOUT_PENDING", "KELTNER_BREAKOUT_PENDING", "FRACTAL_BREAKOUT_PENDING", "ICHI_PENDING"}:
        return structure["breakout_level"] if long_side else structure["breakdown_level"]
    return None


def interest_zone(state: dict, long_side: bool, family: str) -> tuple[float | None, float | None]:
    price = state["price"]
    levels = state["levels"]
    structure = state["structure"]
    atr = price["atr"]
    if family in {"trend_pullback", "supertrend_psar"}:
        return range_pair([price["ema21"], price["ma20"], price["kc_mid"]], fallback=price["ema21"])
    if family == "keltner_pullback":
        return range_pair([price["kc_mid"] - (0.25 * atr), price["kc_mid"] + (0.25 * atr)], fallback=price["kc_mid"])
    if family == "anchored_vwap":
        return range_pair([levels["fixed_vwap"] - (0.3 * atr), levels["fixed_vwap"] + (0.3 * atr)], fallback=levels["fixed_vwap"])
    if family in {"reversal", "obv_divergence", "chaikin_flow"}:
        return range_pair([price["ema8"], levels["vwap"], structure["swing_low_5"] if long_side else structure["swing_high_5"]])
    if family == "vwap_reclaim":
        return range_pair([levels["vwap"], levels["fixed_vwap"], price["ema21"]])
    if family == "morning_star_fib":
        return range_pair([levels["fib_50"], levels["fib_618"], levels["fixed_vwap"]], fallback=levels["fib_50"])
    if family == "accumulation_pattern":
        return range_pair([levels["vp_poc"], levels["fixed_vwap"], levels["vp_val"]], fallback=levels["vp_poc"])
    if family == "poc_rotation":
        if long_side:
            return range_pair([levels["vp_val"], levels["vp_poc"]], fallback=levels["vp_poc"])
        return range_pair([levels["vp_poc"], levels["vp_vah"]], fallback=levels["vp_poc"])
    if family == "ichimoku_breakout":
        if long_side:
            return range_pair([levels["cloud_top"], levels["kijun"]], fallback=levels["cloud_top"])
        return range_pair([levels["cloud_bottom"], levels["kijun"]], fallback=levels["cloud_bottom"])
    if family in {"fractal_breakout", "fractal_alligator"}:
        ref = structure["recent_fractal_high"] if long_side else structure["recent_fractal_low"]
        return range_pair([ref - (0.2 * atr), ref + (0.2 * atr)], fallback=ref)
    return range_pair([price["entry"] - (0.3 * atr), price["entry"] + (0.3 * atr)], fallback=price["entry"])


def entry_reference_payload(
    state: dict,
    long_side: bool,
    family: str,
    phase: str,
    status: str,
    entry_price_value: float | None,
    stop_loss: float | None,
) -> dict:
    confirm_level = confirmation_level(state, long_side, family, phase)
    interest_low, interest_high = interest_zone(state, long_side, family)
    invalidation_level = stop_loss
    reference_type = "ENTRY_PRICE"
    reference_text = ""
    confirmation_phases = {
        "BREAKOUT_PENDING",
        "KELTNER_BREAKOUT_PENDING",
        "VWAP_RECLAIM_PENDING",
        "FIB_GOLDEN_ZONE_WAIT",
        "FRACTAL_BREAKOUT_PENDING",
        "VALUE_ROTATION_READY",
        "ICHI_PENDING",
        "CHAIKIN_READY",
        "DIVERGENCE_READY",
        "REVERSAL_READY",
    }
    if status in {"ACTIVE", "CONFIRMING"}:
        price_text = format_price_text(entry_price_value)
        reference_type = "ENTRY_PRICE" if status == "ACTIVE" else "CONFIRMATION"
        reference_text = ("진입가 " if status == "ACTIVE" else "확인 진행 ") + price_text
    elif phase in confirmation_phases:
        reference_type = "CONFIRMATION"
        reference_text = f"확인선 {format_price_text(confirm_level)}"
    else:
        reference_type = "ZONE"
        reference_text = f"관심구간 {format_range_text(interest_low, interest_high)}"
    return {
        "entry_reference_type": reference_type,
        "entry_reference_text": reference_text,
        "interest_low": interest_low,
        "interest_high": interest_high,
        "confirmation_level": confirm_level,
        "invalidation_level": invalidation_level,
    }


def entry_price(state: dict, long_side: bool, family: str, phase: str, status: str) -> float | None:
    if status == "INVALID":
        return None
    current = state["price"]["entry"]
    price = state["price"]
    levels = state["levels"]
    structure = state["structure"]

    if status in {"ACTIVE", "CONFIRMING"}:
        return current
    if family in {"breakout", "squeeze"}:
        return structure["breakout_level"] if long_side else structure["breakdown_level"]
    if family == "keltner_breakout":
        return price["kc_upper"] if long_side else price["kc_lower"]
    if family == "ichimoku_breakout":
        ref = levels["cloud_top"] if long_side else levels["cloud_bottom"]
        return ref if np.isfinite(ref) else current
    if family in {"fractal_breakout", "fractal_alligator"}:
        ref = structure["recent_fractal_high"] if long_side else structure["recent_fractal_low"]
        return ref if np.isfinite(ref) else current
    if family in {"trend_pullback", "supertrend_psar"}:
        return finite_max([price["ema21"], price["ma20"]], current) if long_side else finite_min([price["ema21"], price["ma20"]], current)
    if family == "keltner_pullback":
        return price["kc_mid"]
    if family == "anchored_vwap":
        return levels["fixed_vwap"]
    if family == "vwap_reclaim":
        return levels["vwap"]
    if family == "keltner_mean_reversion":
        return levels["kc_mid"]
    if family in {"reversal", "obv_divergence", "chaikin_flow"}:
        return finite_max([price["ema8"], levels["vwap"]], current) if long_side else finite_min([price["ema8"], levels["vwap"]], current)
    if family == "morning_star_fib":
        ref = finite_max([levels["fib_618"], levels["fib_50"]], current) if long_side else finite_min([levels["fib_618"], levels["fib_50"]], current)
        return ref if np.isfinite(ref) else current
    if family == "accumulation_pattern":
        ref = finite_max([levels["vp_poc"], levels["fixed_vwap"], structure["breakout_level"]], current)
        return ref if np.isfinite(ref) else current
    if family == "poc_rotation":
        ref = finite_max([levels["vp_poc"], levels["vp_val"]], current) if long_side else finite_min([levels["vp_poc"], levels["vp_vah"]], current)
        return ref if np.isfinite(ref) else current
    if phase in {"BREAKOUT_PENDING", "KELTNER_BREAKOUT_PENDING", "FRACTAL_BREAKOUT_PENDING", "ICHI_PENDING"}:
        return structure["breakout_level"] if long_side else structure["breakdown_level"]
    return current


def entry_hint(status: str, phase: str, long_side: bool, family: str) -> str:
    if status == "INVALID":
        return "무효"
    phase_hints = {
        "BREAKOUT_PENDING": "돌파 확인 대기",
        "KELTNER_BREAKOUT_PENDING": "Keltner 돌파 확인 대기",
        "SQUEEZE_READY": "압축 해제 대기",
        "PULLBACK_WAIT": "눌림 대기",
        "REVERSAL_READY": "확인 캔들 대기",
        "DIVERGENCE_READY": "확인 캔들 대기",
        "TREND_ALIGNED": "추세 확인 대기",
        "MEAN_REVERSION_READY": "평균회귀 확인 대기",
        "VWAP_RECLAIM_PENDING": "VWAP 재장악 확인 대기",
        "FIB_GOLDEN_ZONE_WAIT": "골든존 반응 대기",
        "FRACTAL_BREAKOUT_PENDING": "fractal 돌파 대기",
        "AVWAP_HOLD": "AVWAP 지지 확인 대기",
        "ACCUMULATION_READY": "박스 상단 돌파 대기",
        "VALUE_ROTATION_READY": "POC 재장악 대기",
        "ICHI_PENDING": "구름 돌파 확인 대기",
        "ALLIGATOR_AWAKENING": "추세 각성 확인 대기",
        "CHAIKIN_READY": "자금 유입 확인 대기",
    }
    if phase in phase_hints:
        return phase_hints[phase]
    if family in {"breakout", "keltner_breakout", "fractal_breakout", "ichimoku_breakout"}:
        return "현재가 추격 가능" if status == "ACTIVE" else "돌파 확인 대기"
    if family in {"trend_pullback", "keltner_pullback", "anchored_vwap"}:
        return "현재가 추격 가능" if status == "ACTIVE" else ("눌림 대기" if long_side else "반등 대기")
    if family in {"reversal", "keltner_mean_reversion", "morning_star_fib", "chaikin_flow", "vwap_reclaim", "obv_divergence"}:
        return "현재가 추격 가능" if status == "ACTIVE" else "확인 캔들 대기"
    if family == "accumulation_pattern":
        return "박스 상단 돌파 대기" if status != "ACTIVE" else "현재가 추격 가능"
    if family == "poc_rotation":
        return "POC 재장악 확인 대기" if status != "ACTIVE" else "현재가 추격 가능"
    if family == "fractal_alligator":
        return "fractal 돌파 추격 가능" if status == "ACTIVE" else "추세 각성 대기"
    return "현재가 추격 가능" if status == "ACTIVE" else ("눌림 대기" if long_side else "반등 대기")


def phase_note(phase: str, conflicts: list[str]) -> str:
    phase_notes = {
        "TRIGGERED": "실제 트리거가 확인된 상태입니다.",
        "PULLBACK_WAIT": "눌림 뒤 재반등 확인을 기다리는 구간입니다.",
        "BREAKOUT_PENDING": "첫 돌파는 나왔지만 확인 봉이 더 필요합니다.",
        "BREAKOUT_CONFIRMED": "돌파와 유지 조건이 함께 충족됐습니다.",
        "KELTNER_BREAKOUT_PENDING": "Keltner 외곽 밴드 안착 확인이 남아 있습니다.",
        "KELTNER_BREAKOUT_CONFIRMED": "Keltner 밴드 돌파가 추세 확장으로 이어지고 있습니다.",
        "SQUEEZE_READY": "압축은 충분하지만 방향 분출이 아직 필요합니다.",
        "REVERSAL_READY": "반전 환경은 좋지만 확인 캔들이 더 필요합니다.",
        "DOUBLE_CONFIRMED": "SuperTrend와 PSAR가 같은 방향으로 정렬됐습니다.",
        "TREND_ALIGNED": "추세 기준선은 정렬됐지만 진입 트리거는 약합니다.",
        "DIVERGENCE_READY": "다이버전스는 있지만 확인 트리거가 부족합니다.",
        "DIVERGENCE_CONFIRMED": "다이버전스 뒤 확인 신호가 붙었습니다.",
        "MEAN_REVERSION_READY": "과확장 되돌림은 시작됐지만 평균 복귀 확인이 더 필요합니다.",
        "VWAP_RECLAIM_PENDING": "VWAP 재장악 직전 단계로 확인 봉이 남아 있습니다.",
        "VWAP_RECLAIM_CONFIRMED": "VWAP 재장악과 종가 유지가 확인됐습니다.",
        "FIB_GOLDEN_ZONE_WAIT": "Fib 골든존 반응은 좋지만 패턴 완성은 아직입니다.",
        "FIB_CONFIRM": "Fib 골든존에서 반전 패턴이 확인됐습니다.",
        "FRACTAL_BREAKOUT_PENDING": "fractal 레벨은 준비됐지만 돌파는 아직입니다.",
        "FRACTAL_BREAKOUT_CONFIRMED": "fractal 돌파와 유지가 확인됐습니다.",
        "AVWAP_HOLD": "Anchored VWAP 지지 여부를 확인하는 단계입니다.",
        "AVWAP_CONFIRMED": "Anchored VWAP 위 유지와 반등이 확인됐습니다.",
        "ACCUMULATION_READY": "매집 유사 구조는 좋지만 박스 상단 돌파가 필요합니다.",
        "ACCUMULATION_CONFIRMED": "매집 유사 패턴 뒤 수급 동반 돌파가 확인됐습니다.",
        "VALUE_ROTATION_READY": "POC / Value Area 회전은 시작됐지만 확인 봉이 필요합니다.",
        "POC_RECLAIM_CONFIRMED": "POC 재장악 또는 이탈이 방향성 있게 확인됐습니다.",
        "ICHI_PENDING": "구름 돌파 직전 단계로 TK 확인이 더 필요합니다.",
        "ICHI_BREAKOUT_CONFIRMED": "Ichimoku 구름 돌파와 TK 정렬이 함께 확인됐습니다.",
        "ALLIGATOR_AWAKENING": "추세 스택은 각성 중이지만 fractal 돌파가 남아 있습니다.",
        "CHAIKIN_READY": "Chaikin 흐름은 개선됐지만 가격 확인 봉이 더 필요합니다.",
        "CHAIKIN_CONFIRMED": "Chaikin / CMF 흐름과 가격 확인이 함께 나왔습니다.",
        "SETUP_INVALID": "환경 자체가 아직 전략 성립에 부족합니다.",
    }
    note = phase_notes.get(phase, "")
    if conflicts:
        note = f"{note} 반대 근거도 함께 확인해야 합니다."
    return note
