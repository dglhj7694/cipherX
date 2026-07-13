from __future__ import annotations

import math
from typing import Any


SELL_JUDGMENTS = {"STRONG_SELL", "SELL", "WATCH_SELL"}


def _finite_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _required_positive(value: Any, label: str) -> tuple[float | None, str]:
    number = _finite_float(value)
    if number is None or number <= 0:
        return None, f"{label}은 0보다 큰 유한한 숫자여야 합니다."
    return number, ""


def _optional_positive(value: Any, label: str) -> tuple[float | None, str]:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None, ""
    return _required_positive(value, label)


def _round_optional(value: float | None, digits: int = 2) -> float | None:
    return round(value, digits) if value is not None and math.isfinite(value) else None


def _invalid_result(reason: str, *, as_of: str = "") -> dict[str, Any]:
    return {
        "valid": False,
        "reason": reason,
        "scenario_code": "INVALID_INPUT",
        "scenario_title": "입력값 확인 필요",
        "scenario_summary": reason,
        "scenario_tone": "risk",
        "scenario_reasons": [],
        "as_of": str(as_of or "").strip(),
        "warnings": [],
    }


def calculate_long_holding_scenario(
    *,
    current_price: Any,
    average_entry: Any,
    quantity: Any,
    user_stop_price: Any | None = None,
    account_size: Any | None = None,
    engine_invalidation_price: Any | None = None,
    target_1: Any | None = None,
    target_2: Any | None = None,
    judgment: str = "NEUTRAL",
    hard_conflict: bool = False,
    liquidity_risk: bool = False,
    price_available: bool = True,
    as_of: str = "",
) -> dict[str, Any]:
    """Calculate a read-only spot-long holding review scenario.

    This function never creates an order instruction. A user stop is kept
    separate from the engine invalidation level so the analysis cannot silently
    overwrite the holder's own risk rule.
    """

    current, error = _required_positive(current_price, "현재가")
    if error:
        return _invalid_result(error, as_of=as_of)
    average, error = _required_positive(average_entry, "평균단가")
    if error:
        return _invalid_result(error, as_of=as_of)
    shares, error = _required_positive(quantity, "보유 수량")
    if error:
        return _invalid_result(error, as_of=as_of)
    user_stop, error = _optional_positive(user_stop_price, "사용자 방어 기준")
    if error:
        return _invalid_result(error, as_of=as_of)
    account, error = _optional_positive(account_size, "계좌 평가금액")
    if error:
        return _invalid_result(error, as_of=as_of)
    engine_stop, error = _optional_positive(engine_invalidation_price, "엔진 무효화 기준")
    if error:
        return _invalid_result(error, as_of=as_of)
    first_target, error = _optional_positive(target_1, "1차 목표")
    if error:
        return _invalid_result(error, as_of=as_of)
    second_target, error = _optional_positive(target_2, "2차 목표")
    if error:
        return _invalid_result(error, as_of=as_of)
    target_order_warning = bool(
        first_target is not None and second_target is not None and second_target < first_target
    )
    if target_order_warning:
        second_target = None

    if not price_available:
        return {
            **_invalid_result("분석 기준 가격이 유효하지 않아 보유 손익을 계산하지 않습니다.", as_of=as_of),
            "scenario_code": "PRICE_UNAVAILABLE",
            "scenario_title": "가격 확인 후 재점검",
        }

    cost_value = average * shares
    position_value = current * shares
    unrealized_pnl = (current - average) * shares
    unrealized_pnl_pct = (current / average - 1.0) * 100.0
    position_pct = position_value / account * 100.0 if account is not None else None
    required_values = [cost_value, position_value, unrealized_pnl, unrealized_pnl_pct]
    if position_pct is not None:
        required_values.append(position_pct)
    if not all(math.isfinite(value) for value in required_values):
        return _invalid_result("입력값의 범위가 너무 커 보유 손익을 안전하게 계산할 수 없습니다.", as_of=as_of)

    stop_triggered = user_stop is not None and current <= user_stop
    signed_distance_to_stop = current - user_stop if user_stop is not None else None
    distance_to_stop_pct = signed_distance_to_stop / current * 100.0 if signed_distance_to_stop is not None else None
    giveback_to_stop = max(current - user_stop, 0.0) * shares if user_stop is not None else None
    pnl_at_stop = (user_stop - average) * shares if user_stop is not None else None
    pnl_at_stop_pct = (user_stop / average - 1.0) * 100.0 if user_stop is not None else None
    pnl_at_stop_pct_of_account = pnl_at_stop / account * 100.0 if pnl_at_stop is not None and account is not None else None
    engine_invalidation_breached = engine_stop is not None and current <= engine_stop

    target_1_pnl = (first_target - average) * shares if first_target is not None else None
    target_2_pnl = (second_target - average) * shares if second_target is not None else None
    target_1_reached = first_target is not None and current >= first_target
    target_2_reached = second_target is not None and current >= second_target

    optional_values = [
        signed_distance_to_stop,
        distance_to_stop_pct,
        giveback_to_stop,
        pnl_at_stop,
        pnl_at_stop_pct,
        pnl_at_stop_pct_of_account,
        target_1_pnl,
        target_2_pnl,
    ]
    if not all(value is None or math.isfinite(value) for value in optional_values):
        return _invalid_result("입력값의 범위가 너무 커 방어 시나리오를 안전하게 계산할 수 없습니다.", as_of=as_of)

    judgment_code = str(judgment or "NEUTRAL").strip().upper()
    defend_reasons: list[str] = []
    warnings: list[str] = []
    if target_order_warning:
        warnings.append("2차 목표가 1차 목표보다 낮아 2차 목표 시나리오는 제외했습니다.")
    if judgment_code in SELL_JUDGMENTS:
        defend_reasons.append(f"현재 엔진 판단 {judgment_code}")
    if engine_invalidation_breached:
        defend_reasons.append("분석 엔진 무효화 기준 이탈")
    if hard_conflict:
        defend_reasons.append("매수·매도 신호 충돌")
    if liquidity_risk:
        defend_reasons.append("얇은 거래대금")
    if account is not None and position_pct is not None and position_pct > 100:
        warnings.append("입력 계좌금액보다 현재 포지션 평가금액이 큽니다.")
    if not str(as_of or "").strip():
        warnings.append("분석 가격 기준일을 확인할 수 없습니다.")
    if target_1_reached:
        warnings.append("입력 현재가가 1차 목표 이상입니다. 목표와 잔여 보유 계획을 다시 확인하세요.")
    if target_2_reached:
        warnings.append("입력 현재가가 2차 목표 이상입니다. 목표와 잔여 보유 계획을 다시 확인하세요.")

    if stop_triggered:
        scenario_code = "STOP_REACHED"
        scenario_title = "사용자 방어 기준 도달 확인"
        scenario_summary = "입력 현재가가 사용자 방어 기준 이하입니다. 최신 시세와 주문 상태를 직접 확인하고 계획을 재검토하세요."
        scenario_tone = "risk"
        scenario_reasons = ["사용자 방어 기준 도달"]
    elif defend_reasons:
        scenario_code = "DEFEND_REVIEW"
        scenario_title = "보유분 방어 재검토"
        scenario_summary = "현재 판단과 위험 신호를 보유 계획에 다시 반영할 시점입니다. 자동 매도 지시가 아니며 사용자 방어 기준을 우선 확인하세요."
        scenario_tone = "risk"
        scenario_reasons = defend_reasons
    elif user_stop is None:
        scenario_code = "NO_STOP_SET"
        scenario_title = "사용자 방어 기준 먼저 정하기"
        scenario_summary = "평가손익은 계산했지만 사용자가 정한 방어 기준이 없습니다. 감당 가능한 손실과 이익 반납 범위를 먼저 기록하세요."
        scenario_tone = "wait"
        scenario_reasons = ["사용자 방어 기준 미설정"]
    else:
        scenario_code = "HOLD_REVIEW"
        scenario_title = "보유 계획 범위 점검"
        scenario_summary = "입력 현재가는 사용자 방어 기준 위에 있습니다. 평가손익보다 방어선까지의 반납 가능 금액과 다음 재점검 조건을 함께 보세요."
        scenario_tone = "positive" if unrealized_pnl >= 0 else "wait"
        scenario_reasons = []

    return {
        "valid": True,
        "reason": "",
        "scenario_code": scenario_code,
        "scenario_title": scenario_title,
        "scenario_summary": scenario_summary,
        "scenario_tone": scenario_tone,
        "scenario_reasons": scenario_reasons,
        "as_of": str(as_of or "").strip(),
        "current_price": _round_optional(current, 4),
        "average_entry": _round_optional(average, 4),
        "quantity": _round_optional(shares, 6),
        "cost_value": _round_optional(cost_value),
        "position_value": _round_optional(position_value),
        "unrealized_pnl": _round_optional(unrealized_pnl),
        "unrealized_pnl_pct": _round_optional(unrealized_pnl_pct, 3),
        "position_pct": _round_optional(position_pct, 3),
        "user_stop_price": _round_optional(user_stop, 4),
        "stop_triggered": bool(stop_triggered),
        "signed_distance_to_stop": _round_optional(signed_distance_to_stop, 4),
        "distance_to_stop_pct": _round_optional(distance_to_stop_pct, 3),
        "giveback_to_stop": _round_optional(giveback_to_stop),
        "pnl_at_stop": _round_optional(pnl_at_stop),
        "pnl_at_stop_pct": _round_optional(pnl_at_stop_pct, 3),
        "pnl_at_stop_pct_of_account": _round_optional(pnl_at_stop_pct_of_account, 3),
        "engine_invalidation_price": _round_optional(engine_stop, 4),
        "engine_invalidation_breached": bool(engine_invalidation_breached),
        "target_1": _round_optional(first_target, 4),
        "target_2": _round_optional(second_target, 4),
        "target_1_pnl": _round_optional(target_1_pnl),
        "target_2_pnl": _round_optional(target_2_pnl),
        "target_1_reached": bool(target_1_reached),
        "target_2_reached": bool(target_2_reached),
        "warnings": warnings,
        "calculation_note": "단순 평단·수량 기준 평가 시나리오이며 수수료·세금·배당·환율·슬리피지와 실제 체결가는 반영하지 않습니다.",
    }
