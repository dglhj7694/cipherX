from __future__ import annotations

import math
import re
from typing import Any, Iterable, Mapping


ACTIVE_STATUSES = {"ACTIVE", "LONG_ENTRY", "SHORT_ENTRY"}
CONFIRMING_STATUSES = {"CONFIRMING"}
WAIT_STATUSES = {
    "TRIGGER_WAIT",
    "READY",
    "INTEREST",
    "LONG_ALIGNED",
    "SHORT_ALIGNED",
    "LONG_WAIT",
    "SHORT_WAIT",
    "WATCH",
    "WEAK_WATCH",
}
BUY_JUDGMENTS = {"STRONG_BUY", "BUY", "WATCH_BUY"}
EXECUTABLE_BUY_JUDGMENTS = {"STRONG_BUY", "BUY"}
SELL_JUDGMENTS = {"STRONG_SELL", "SELL", "WATCH_SELL"}
MIN_AUDIT_SAMPLES = 20
GUIDE_VISIBLE_STATUSES = ACTIVE_STATUSES | CONFIRMING_STATUSES | WAIT_STATUSES | {"EXIT_WARNING"}

STATUS_LABELS = {
    "ACTIVE": "활성",
    "CONFIRMING": "확인 진행",
    "TRIGGER_WAIT": "트리거 대기",
    "READY": "준비",
    "INTEREST": "관심 구간",
    "LONG_ENTRY": "매수 진입",
    "LONG_ALIGNED": "매수 정렬",
    "LONG_WAIT": "매수 대기",
    "SHORT_ENTRY": "매도 진입",
    "SHORT_ALIGNED": "매도 정렬",
    "SHORT_WAIT": "매도 대기",
    "EXIT_WARNING": "청산 경고",
    "WATCH": "관찰",
    "WEAK_WATCH": "약한 관찰",
}


def _finite_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _positive_float(value: Any) -> float | None:
    number = _finite_float(value)
    return number if number is not None and number > 0 else None


def _unique_text(items: Iterable[Any]) -> list[str]:
    result: list[str] = []
    for item in items or []:
        text = str(item or "").strip()
        if text and text not in result:
            result.append(text)
    return result


def _text_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return _unique_text(re.split(r"[,+|;/\n]+", value))
    if isinstance(value, Mapping):
        items: list[Any] = []
        for key, item in value.items():
            if isinstance(item, bool):
                if item:
                    items.append(key)
            elif item is not None:
                items.extend(_text_list(item))
        return _unique_text(items)
    if isinstance(value, Iterable):
        return _unique_text(value)
    return _unique_text([value])


def _direction(value: Any) -> str:
    text = str(value or "").strip().upper()
    if text in {"LONG", "BUY", "BULL", "BULLISH"}:
        return "LONG"
    if text in {"SHORT", "SELL", "BEAR", "BEARISH"}:
        return "SHORT"
    return "NEUTRAL"


def _judgment(meta: Mapping[str, Any]) -> str:
    raw = str(meta.get("judgment") or meta.get("decision") or meta.get("final_label") or "").strip()
    code = raw.upper()
    if code in BUY_JUDGMENTS | SELL_JUDGMENTS | {"MIXED", "NEUTRAL"}:
        return code

    display = " ".join((raw, str(meta.get("action_label") or ""))).strip()
    if "강한 매수" in display:
        return "STRONG_BUY"
    if "매수 관심" in display or "매수 관찰" in display:
        return "WATCH_BUY"
    if "매수" in display:
        return "BUY"
    if "강한 매도" in display:
        return "STRONG_SELL"
    if "매도 관심" in display or "매도 관찰" in display:
        return "WATCH_SELL"
    if "매도" in display or "축소" in display or "방어" in display:
        return "SELL"
    if "혼조" in display:
        return "MIXED"
    return "NEUTRAL"


def _strategy_candidates(meta: Mapping[str, Any]) -> list[dict[str, Any]]:
    if "strategy_visible_results" in meta:
        candidates = list(meta.get("strategy_visible_results") or [])
    else:
        candidates = list(meta.get("strategy_results") or [])
    return [
        dict(item)
        for item in candidates
        if isinstance(item, Mapping) and str(item.get("status") or "").strip().upper() in GUIDE_VISIBLE_STATUSES
    ]


def _same_strategy(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    left_id = str(left.get("id") or "").strip()
    right_id = str(right.get("id") or "").strip()
    if left_id and right_id:
        return left_id == right_id
    left_label = str(left.get("label") or "").strip()
    right_label = str(right.get("label") or "").strip()
    return bool(left_label and right_label and left_label == right_label)


def _implemented_strategy(item: Mapping[str, Any]) -> bool:
    presentation = str(item.get("presentation_type") or "").strip().lower()
    implementation = str(item.get("implementation_level") or "").strip().lower()
    deterministic = item.get("deterministic")
    return presentation == "strategy" and implementation == "implemented" and deterministic is True


def _status_priority(status: Any) -> int:
    code = str(status or "").strip().upper()
    if code in ACTIVE_STATUSES:
        return 4
    if code in CONFIRMING_STATUSES:
        return 3
    if code in WAIT_STATUSES:
        return 2
    if code == "EXIT_WARNING":
        return 0
    return 1


def resolve_top_strategy(meta: Mapping[str, Any] | None) -> dict[str, Any]:
    """Pick an implemented strategy aligned with the final engine judgment.

    The engine's raw top strategy can be SHORT, contextual, or a proxy. That is
    useful in the expert strategy table but unsafe as the default beginner plan.
    """

    meta = dict(meta or {})
    summary = dict(meta.get("strategy_summary") or {})
    raw_top = summary.get("top_strategy") if isinstance(summary.get("top_strategy"), Mapping) else meta.get("top_strategy")
    top = dict(raw_top) if isinstance(raw_top, Mapping) else {}
    has_candidate_collection = "strategy_visible_results" in meta or "strategy_results" in meta
    candidates = _strategy_candidates(meta)

    if top:
        for index, candidate in enumerate(candidates):
            if _same_strategy(candidate, top):
                candidates[index] = {**candidate, **top}
                break
        else:
            # A normal summary top must also exist in visible_results. Only
            # accept a standalone top when no candidate collection exists.
            # This prevents a sparse or stale summary from becoming a plan.
            if has_candidate_collection:
                top = {}
            else:
                candidates.append(top)

    safe_candidates = [
        item
        for item in candidates
        if _implemented_strategy(item)
        and str(item.get("status") or "").strip().upper() in GUIDE_VISIBLE_STATUSES
    ]
    judgment = _judgment(meta)
    desired_direction = "LONG" if judgment in BUY_JUDGMENTS else "SHORT" if judgment in SELL_JUDGMENTS else ""
    if not desired_direction:
        return {}
    safe_candidates = [item for item in safe_candidates if _direction(item.get("direction")) == desired_direction]
    if not safe_candidates:
        return {}

    return max(
        safe_candidates,
        key=lambda item: (
            _status_priority(item.get("status")),
            _finite_float(item.get("score")) or 0.0,
            int(bool(top and _same_strategy(item, top))),
        ),
    )


def _entry_reference(strategy: Mapping[str, Any], entry: float | None) -> str:
    text = str(strategy.get("entry_reference_text") or "").strip()
    if text:
        return text
    reference_type = str(strategy.get("entry_reference_type") or "").strip().upper()
    confirmation = _positive_float(strategy.get("confirmation_level"))
    interest_low = _positive_float(strategy.get("interest_low"))
    interest_high = _positive_float(strategy.get("interest_high"))
    if reference_type == "CONFIRMATION" and confirmation is not None:
        return f"확인선 {confirmation:.2f}"
    if reference_type == "ZONE" and interest_low is not None and interest_high is not None:
        low, high = sorted((interest_low, interest_high))
        return f"관심구간 {low:.2f}~{high:.2f}"
    if entry is not None:
        return f"진입 기준 {entry:.2f}"
    return "전략 상세의 확인 조건을 먼저 확인하세요."


def _valid_stop(direction: str, entry: float | None, stop: float | None) -> bool:
    if entry is None or stop is None:
        return False
    if direction == "LONG":
        return stop < entry
    if direction == "SHORT":
        return stop > entry
    return False


def _valid_target(direction: str, entry: float | None, target: float | None) -> bool:
    if entry is None or target is None:
        return False
    if direction == "LONG":
        return target > entry
    if direction == "SHORT":
        return target < entry
    return False


def _reward_risk(
    direction: str,
    entry: float | None,
    stop: float | None,
    target: float | None,
) -> float | None:
    if not _valid_stop(direction, entry, stop) or not _valid_target(direction, entry, target):
        return None
    risk = abs(entry - stop)
    return abs(target - entry) / risk if risk > 1e-12 else None


def _action_state(
    *,
    judgment: str,
    direction: str,
    status: str,
    hard_conflict: bool,
    liquidity_risk: bool,
    has_strategy: bool,
    stop_valid: bool,
    target_valid: bool,
    reward_risk_acceptable: bool,
) -> tuple[str, str, str, str]:
    if judgment in SELL_JUDGMENTS or direction == "SHORT" or status == "EXIT_WARNING":
        return (
            "DEFEND",
            "신규 매수 보류",
            "보유 중이라면 지지 이탈과 비중을 먼저 점검하고, 신규 진입은 매도 압력이 완화될 때까지 기다리세요.",
            "risk",
        )
    if not has_strategy:
        return (
            "NO_SETUP",
            "관망 우선",
            "현재 판단과 같은 방향의 독립 구현 전략이 없습니다. 가격을 예측하기보다 새 확인 신호를 기다리세요.",
            "wait",
        )
    if hard_conflict:
        return (
            "CONFLICT",
            "방향 충돌 해소 대기",
            "상승·하락 근거가 강하게 충돌합니다. 어느 한쪽 조건이 무효화될 때까지 신규 진입을 서두르지 마세요.",
            "risk",
        )
    if liquidity_risk:
        return (
            "LIQUIDITY_WAIT",
            "거래대금 회복 대기",
            "거래대금이 얇으면 표시 가격과 실제 체결 가격의 차이가 커질 수 있습니다. 유동성이 회복될 때까지 신규 진입을 보류하세요.",
            "risk",
        )
    if judgment == "WATCH_BUY":
        return (
            "WAIT_TRIGGER",
            "매수 판단 강화 대기",
            "매수 관심 단계입니다. 활성 전략이 있어도 최종 판단이 BUY 이상으로 강화되기 전에는 신규 진입 수량을 계산하지 않습니다.",
            "wait",
        )
    if status in WAIT_STATUSES or judgment not in BUY_JUDGMENTS:
        return (
            "WAIT_TRIGGER",
            "확인 조건 대기",
            "관심 전략은 있지만 아직 실행 단계가 아닙니다. 표시된 확인선이나 관심구간 조건이 충족되는지 먼저 보세요.",
            "wait",
        )
    if status in CONFIRMING_STATUSES:
        return (
            "CONFIRMING",
            "종가 확인 후 재검토",
            "전략 확인이 진행 중입니다. 아래 가격은 조건부 시나리오이며, 실제 진입이 확인되면 손절·목표와 수량을 다시 계산하세요.",
            "caution",
        )
    if status in ACTIVE_STATUSES and judgment in EXECUTABLE_BUY_JUDGMENTS:
        if not stop_valid:
            return (
                "MISSING_RISK",
                "손절 기준 확인 전 대기",
                "매수 방향 전략은 활성 상태지만 유효한 손절 기준이 없습니다. 손실 한도를 정하기 전에는 수량을 계산하지 마세요.",
                "risk",
            )
        if not target_valid:
            return (
                "MISSING_REWARD",
                "목표가 확인 전 대기",
                "매수 방향 전략과 손절 기준은 있지만 유효한 1차 목표가가 없습니다. 손익비를 확인하기 전에는 수량을 계산하지 마세요.",
                "risk",
            )
        if not reward_risk_acceptable:
            return (
                "LOW_REWARD_RISK",
                "손익비 개선 대기",
                "1차 목표의 예상 보상이 손절 위험보다 작습니다. 진입가·손절·목표 조합이 최소 1R 이상이 될 때까지 기다리세요.",
                "risk",
            )
        return (
            "PLAN_READY",
            "조건 확인 후 분할 접근 검토",
            "전략은 활성 상태입니다. 진입 기준·손절·목표를 한 세트로 확인하고 감당 가능한 수량만 검토하세요.",
            "positive",
        )
    return (
        "WAIT_TRIGGER",
        "확인 조건 대기",
        "현재 상태만으로는 실행 판단이 충분하지 않습니다. 전략의 다음 확인 조건을 기다리세요.",
        "wait",
    )


def _checklist_item(key: str, label: str, status: str, text: str) -> dict[str, str]:
    return {"key": key, "label": label, "status": status, "text": text}


def _audit_snapshot(
    audit: Mapping[str, Any] | None,
    judgment: str,
    minimum_samples: int = MIN_AUDIT_SAMPLES,
) -> dict[str, Any]:
    payload = dict(audit or {})
    note = "과거 동일 판단 라벨 통계이며, 개별 전략 성과나 미래 수익을 보장하지 않습니다."
    if not payload.get("available"):
        return {
            "available": False,
            "matched": False,
            "reason": str(payload.get("reason") or "검증 표본이 아직 없습니다."),
            "note": note,
        }

    row = next(
        (
            dict(item)
            for item in payload.get("label_rows") or []
            if isinstance(item, Mapping) and str(item.get("name") or "").strip().upper() == judgment
        ),
        None,
    )
    if row is None:
        return {
            "available": True,
            "matched": False,
            "reason": "현재 판단과 같은 과거 라벨 표본이 없습니다.",
            "note": note,
        }

    horizon_value = _finite_float(payload.get("reference_horizon"))
    horizon = int(horizon_value) if horizon_value is not None and horizon_value > 0 else 5
    sample_value = _finite_float(row.get("samples"))
    samples = max(0, int(sample_value or 0))
    return {
        "available": True,
        "matched": True,
        "label": judgment,
        "samples": samples,
        "minimum_samples": minimum_samples,
        "sufficient_samples": samples >= minimum_samples,
        "horizon": horizon,
        "hit_rate": _finite_float(row.get(f"hit_{horizon}")),
        "edge": _finite_float(row.get(f"edge_{horizon}")),
        "note": note,
    }


def build_beginner_trade_guide(
    meta: Mapping[str, Any] | None,
    audit: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    meta = dict(meta or {})
    ticker = str(meta.get("ticker") or "").strip().upper()
    summary = dict(meta.get("strategy_summary") or {})
    strategy = resolve_top_strategy(meta)
    has_strategy = bool(strategy.get("label") or strategy.get("id"))
    direction = _direction(strategy.get("direction"))
    status = str(strategy.get("status") or "").strip().upper()
    judgment = _judgment(meta)
    objective_alignment = str(meta.get("objective_alignment") or "MIXED").strip().upper()
    conflict_level = str(summary.get("conflict_level") or meta.get("strategy_conflict_level") or "LOW").strip().upper()
    if conflict_level not in {"LOW", "MEDIUM", "HIGH"}:
        conflict_level = "LOW"
    conflict_layers = _finite_float(meta.get("signal_conflict_layers"))
    hard_conflict = (
        conflict_level == "HIGH"
        or objective_alignment == "CONFLICT"
        or (conflict_layers is not None and conflict_layers >= 3)
    )
    liquidity_risk = bool(meta.get("thin_trade_risk"))

    price_data_available = meta.get("summary_price_available") is not False
    entry = _positive_float(strategy.get("entry_price"))
    if entry is None and has_strategy and status in ACTIVE_STATUSES | CONFIRMING_STATUSES:
        entry = _positive_float(meta.get("price"))
    raw_stop = _positive_float(strategy.get("stop_loss")) or _positive_float(strategy.get("invalidation_level"))
    raw_target_1 = _positive_float(strategy.get("target_1"))
    raw_target_2 = _positive_float(strategy.get("target_2"))
    raw_stop_valid = price_data_available and _valid_stop(direction, entry, raw_stop)
    raw_target_1_valid = price_data_available and _valid_target(direction, entry, raw_target_1)
    raw_target_2_valid = price_data_available and _valid_target(direction, entry, raw_target_2)
    raw_target_2_ordered = bool(
        raw_target_1_valid
        and raw_target_2_valid
        and (
            (direction == "LONG" and raw_target_2 >= raw_target_1)
            or (direction == "SHORT" and raw_target_2 <= raw_target_1)
        )
    )

    levels_visible = bool(
        has_strategy
        and direction == "LONG"
        and price_data_available
        and status in ACTIVE_STATUSES | CONFIRMING_STATUSES
    )
    levels_conditional = (
        status in CONFIRMING_STATUSES
        or judgment == "WATCH_BUY"
        or hard_conflict
        or liquidity_risk
    )
    stop = raw_stop if levels_visible and raw_stop_valid else None
    target_1 = raw_target_1 if levels_visible and raw_target_1_valid else None
    target_2 = raw_target_2 if levels_visible and raw_target_2_ordered else None
    rr_value = _reward_risk(direction, entry, stop, target_1)
    reward_risk_acceptable = rr_value is not None and rr_value >= 1.0

    action_code, action_title, action_summary, action_tone = _action_state(
        judgment=judgment,
        direction=direction,
        status=status,
        hard_conflict=hard_conflict,
        liquidity_risk=liquidity_risk,
        has_strategy=has_strategy,
        stop_valid=raw_stop_valid,
        target_valid=raw_target_1_valid,
        reward_risk_acceptable=reward_risk_acceptable,
    )

    if direction == "LONG":
        direction_state = "pass" if judgment in EXECUTABLE_BUY_JUDGMENTS else "wait"
        direction_text = (
            "매수 방향 전략과 엔진 판단이 같은 쪽입니다."
            if judgment in EXECUTABLE_BUY_JUDGMENTS
            else "매수 방향은 같지만 최종 판단의 강화가 더 필요합니다."
        )
    elif direction == "SHORT":
        direction_state = "risk"
        direction_text = "하락 방향 전략입니다. 초보자 화면에서는 신규 공매도 수량을 계산하지 않습니다."
    else:
        direction_state = "wait"
        direction_text = "뚜렷한 매수·매도 방향이 아직 없습니다."

    if status in ACTIVE_STATUSES:
        trigger_state, trigger_text = "pass", f"전략 상태가 {STATUS_LABELS.get(status, status)}입니다."
    elif status in CONFIRMING_STATUSES:
        trigger_state, trigger_text = "wait", "확인 진행 중입니다. 종가 유지 여부를 추가로 확인하세요."
    elif status:
        trigger_state, trigger_text = "wait", f"현재는 {STATUS_LABELS.get(status, status)} 단계입니다."
    else:
        trigger_state, trigger_text = "info", "표시할 독립 구현 전략 단계가 없습니다."

    stop_gap_pct: float | None = None
    if direction == "SHORT":
        stop_state = "info"
        stop_text = "하락 전략의 손절·목표는 공매도 계획값이므로 초보자 현물 가이드에서는 표시하지 않습니다."
    elif status in WAIT_STATUSES:
        stop_state = "info"
        stop_text = "대기 전략의 손절·목표는 실제 진입이 확인된 뒤 새 진입가로 다시 계산합니다."
    elif raw_stop_valid and entry is not None and stop is not None:
        stop_gap_pct = abs(entry - stop) / entry * 100.0
        stop_state = "wait" if levels_conditional else "pass"
        qualifier = "조건부 무효화 기준" if levels_conditional else "무효화 기준"
        stop_text = f"{qualifier} {stop:.2f}, 진입 기준 대비 위험폭 {stop_gap_pct:.2f}%입니다."
    elif has_strategy:
        stop_state = "risk"
        stop_text = "유효한 손절/무효화 가격이 없어 수량 계산을 중단합니다."
    else:
        stop_state = "info"
        stop_text = "전략이 생기면 손절/무효화 가격도 함께 확인하세요."

    if direction == "SHORT":
        rr_state = "info"
        rr_text = "초보자 현물 가이드에서는 공매도 손익비를 실행값으로 사용하지 않습니다."
    elif status in WAIT_STATUSES:
        rr_state = "info"
        rr_text = "대기 중에는 저장된 목표·손익비를 실행값으로 사용하지 않습니다. 진입 확인 후 다시 계산합니다."
    elif rr_value is None:
        rr_state = "info"
        rr_text = "방향에 맞는 손절과 1차 목표가가 모두 있어야 손익비를 계산할 수 있습니다."
    elif rr_value >= 1.5:
        rr_state = "wait" if levels_conditional else "pass"
        rr_text = f"1차 목표 기준 손익비는 {rr_value:.2f}R입니다."
    elif rr_value >= 1.0:
        rr_state = "wait"
        rr_text = f"1차 목표 기준 손익비는 {rr_value:.2f}R로 여유가 크지 않습니다."
    else:
        rr_state = "risk"
        rr_text = f"1차 목표 기준 손익비는 {rr_value:.2f}R로 예상 손실폭보다 작습니다."

    conflict_state = "risk" if hard_conflict else "wait" if conflict_level == "MEDIUM" else "pass"
    if conflict_layers is not None and conflict_layers >= 3:
        conflict_text = f"매수·매도 신호가 {int(conflict_layers)}개 레이어에서 충돌하므로 신규 진입을 서두르지 마세요."
    elif objective_alignment == "CONFLICT":
        conflict_text = "객관 엔진과 최종 판단이 충돌하므로 신규 진입을 서두르지 마세요."
    else:
        conflict_text = {
            "LOW": "전략 간 충돌이 낮습니다.",
            "MEDIUM": "일부 반대 근거가 있어 수량을 보수적으로 검토하세요.",
            "HIGH": "반대 전략이 강하게 충돌하므로 신규 진입을 서두르지 마세요.",
        }[conflict_level]

    leading_noise = meta.get("leading_noise_flags")
    leading_noise_summary = leading_noise.get("summary") if isinstance(leading_noise, Mapping) else leading_noise
    risk_flags = _unique_text(
        [
            *_text_list(meta.get("veto_flags")),
            *_text_list(leading_noise_summary),
            *_text_list(strategy.get("conflict_reasons")),
            *_text_list(strategy.get("failed_conditions")),
            *_text_list(summary.get("opposing_reasons")),
        ]
    )
    if not price_data_available:
        risk_flags.insert(0, "유효한 대표 가격 없음")
    if isinstance(leading_noise, Mapping) and any(
        bool(leading_noise.get(key)) for key in ("noise_block", "buy_noise_block", "sell_noise_block")
    ):
        risk_flags.insert(0, "선행 신호 노이즈 차단")
    if liquidity_risk:
        risk_flags.insert(0, "거래대금이 얇아 체결 오차 주의")
    if objective_alignment == "CONFLICT":
        risk_flags.insert(0, "객관 엔진과 최종 판단 충돌")
    if conflict_level == "HIGH":
        risk_flags.insert(0, "전략 충돌 HIGH")
    if levels_visible and not raw_stop_valid:
        risk_flags.insert(0, "손절 기준 확인 필요")
    if levels_visible and raw_target_2 is not None and not raw_target_2_ordered:
        risk_flags.insert(0, "2차 목표 순서 확인 필요")
    if conflict_layers is not None and conflict_layers >= 3:
        risk_flags.insert(0, f"신호 충돌 {int(conflict_layers)}개 레이어")
    risk_flags = _unique_text(risk_flags)

    entry_reference_type = str(strategy.get("entry_reference_type") or "").strip().upper()
    if not entry_reference_type and status in ACTIVE_STATUSES:
        entry_reference_type = "ENTRY_PRICE"
    sizing_available = bool(
        has_strategy
        and direction == "LONG"
        and judgment in EXECUTABLE_BUY_JUDGMENTS
        and status in ACTIVE_STATUSES
        and entry_reference_type == "ENTRY_PRICE"
        and raw_stop_valid
        and raw_target_1_valid
        and reward_risk_acceptable
        and not hard_conflict
        and not liquidity_risk
        and price_data_available
    )
    if sizing_available:
        sizing_block_reason = ""
    elif not has_strategy:
        sizing_block_reason = "판단 방향과 맞는 독립 구현 전략이 없어 수량 계산을 열지 않습니다."
    elif direction != "LONG" or judgment not in BUY_JUDGMENTS:
        sizing_block_reason = "초보자 가이드는 신규 공매도 수량을 계산하지 않습니다."
    elif judgment == "WATCH_BUY":
        sizing_block_reason = "매수 관심 판단이 BUY 이상으로 강화되기 전에는 수량을 계산하지 않습니다."
    elif not price_data_available:
        sizing_block_reason = "유효한 대표 가격을 확인할 수 없어 수량 계산을 중단합니다."
    elif hard_conflict:
        sizing_block_reason = "신호 충돌이 해소될 때까지 수량 계산을 중단합니다."
    elif liquidity_risk:
        sizing_block_reason = "거래대금이 얇아 체결 오차 위험이 있으므로 수량 계산을 중단합니다."
    elif status not in ACTIVE_STATUSES or entry_reference_type != "ENTRY_PRICE":
        sizing_block_reason = "실제 진입 상태가 확인된 뒤 새 진입가로 수량을 계산합니다."
    elif not raw_stop_valid:
        sizing_block_reason = "방향에 맞는 손절·무효화 가격이 없어 수량을 계산하지 않습니다."
    elif not raw_target_1_valid:
        sizing_block_reason = "유효한 1차 목표와 손익비를 확인하기 전에는 수량을 계산하지 않습니다."
    elif not reward_risk_acceptable:
        sizing_block_reason = "1차 목표 손익비가 1R 미만이어서 수량을 계산하지 않습니다."
    else:
        sizing_block_reason = "현재 조건에서는 수량 계산을 열지 않습니다."

    checklist = [
        _checklist_item("direction", "방향 일치", direction_state, direction_text),
        _checklist_item("trigger", "진입 조건", trigger_state, trigger_text),
        _checklist_item("stop", "손실 제한", stop_state, stop_text),
        _checklist_item("reward_risk", "손익비", rr_state, rr_text),
        _checklist_item("conflict", "반대 근거", conflict_state, conflict_text),
    ]

    strategy_score = _finite_float(strategy.get("score"))
    return {
        "available": bool(meta),
        "ticker": ticker,
        "as_of": str(meta.get("summary_date") or meta.get("last_date") or "").strip(),
        "judgment": judgment,
        "action_code": action_code,
        "action_title": action_title,
        "action_summary": action_summary,
        "action_tone": action_tone,
        "strategy_label": str(strategy.get("label") or "전략 없음").strip(),
        "strategy_status": status,
        "strategy_status_label": STATUS_LABELS.get(status, status or "-"),
        "strategy_score": strategy_score,
        "direction": direction,
        "conflict_level": conflict_level,
        "hard_conflict": hard_conflict,
        "liquidity_risk": liquidity_risk,
        "objective_alignment": objective_alignment,
        "current_price": _positive_float(meta.get("price")),
        "price_data_available": price_data_available,
        "entry_reference_type": entry_reference_type,
        "entry_price": entry if levels_visible else None,
        "entry_reference": "매도 압력 완화와 지지 회복 확인" if direction == "SHORT" else _entry_reference(strategy, entry),
        "levels_visible": levels_visible,
        "levels_conditional": levels_conditional,
        "stop_loss": stop,
        "stop_valid": bool(stop is not None),
        "stop_gap_pct": stop_gap_pct,
        "target_1": target_1,
        "target_2": target_2,
        "target_valid": bool(target_1 is not None),
        "rr": rr_value,
        "sizing_available": sizing_available,
        "sizing_block_reason": sizing_block_reason,
        "risk_flags": risk_flags[:8],
        "checklist": checklist,
        "invalidation_text": str(strategy.get("invalidation_text") or "").strip(),
        "currency_hint": "KRW" if ticker.endswith((".KS", ".KQ")) or bool(re.fullmatch(r"\d{6}", ticker)) else "계좌 통화",
        "source_note": "프로그램의 기술적 전략 시나리오를 초보자용으로 재구성한 참고 정보입니다.",
        "audit_snapshot": _audit_snapshot(audit, judgment),
    }


def calculate_position_size(
    *,
    entry_price: Any,
    stop_price: Any,
    account_size: Any,
    risk_pct: Any,
    max_allocation_pct: Any,
    direction: str = "LONG",
) -> dict[str, Any]:
    entry = _positive_float(entry_price)
    stop = _positive_float(stop_price)
    account = _positive_float(account_size)
    risk_percent = _positive_float(risk_pct)
    allocation_percent = _positive_float(max_allocation_pct)
    side = _direction(direction)

    error = ""
    if entry is None or stop is None:
        error = "진입가와 손절가는 0보다 큰 유한한 숫자여야 합니다."
    elif side not in {"LONG", "SHORT"}:
        error = "매수 또는 매도 방향이 필요합니다."
    elif not _valid_stop(side, entry, stop):
        error = "매수는 손절가가 진입가보다 낮아야 하고, 매도는 손절가가 진입가보다 높아야 합니다."
    elif account is None:
        error = "계좌 평가금액은 0보다 커야 합니다."
    elif risk_percent is None or risk_percent > 100:
        error = "거래당 손실 한도는 0% 초과 100% 이하로 입력하세요."
    elif allocation_percent is None or allocation_percent > 100:
        error = "종목당 최대 사용 비중은 0% 초과 100% 이하로 입력하세요."
    if error:
        return {"valid": False, "reason": error, "quantity": 0}

    per_share_risk = abs(entry - stop)
    if per_share_risk <= 1e-12:
        return {"valid": False, "reason": "진입가와 손절가의 간격이 너무 작아 수량을 계산할 수 없습니다.", "quantity": 0}
    risk_budget = account * risk_percent / 100.0
    allocation_budget = account * allocation_percent / 100.0
    risk_units = risk_budget / per_share_risk
    allocation_units = allocation_budget / entry
    if not all(math.isfinite(value) for value in (risk_budget, allocation_budget, risk_units, allocation_units)):
        return {"valid": False, "reason": "입력값의 범위가 너무 커 수량을 안전하게 계산할 수 없습니다.", "quantity": 0}
    risk_quantity = math.floor(risk_units)
    allocation_quantity = math.floor(allocation_units)
    quantity = max(0, min(risk_quantity, allocation_quantity))
    position_value = quantity * entry
    estimated_loss = quantity * per_share_risk
    limited_by = "risk" if risk_quantity <= allocation_quantity else "allocation"
    if risk_quantity == allocation_quantity:
        limited_by = "both"
    reason = "계산 결과가 1주 미만입니다. 계좌·손실 한도·가격 간격을 다시 확인하세요." if quantity < 1 else ""
    return {
        "valid": quantity >= 1,
        "reason": reason,
        "quantity": quantity,
        "risk_budget": round(risk_budget, 2),
        "allocation_budget": round(allocation_budget, 2),
        "per_share_risk": round(per_share_risk, 4),
        "risk_based_quantity": risk_quantity,
        "allocation_based_quantity": allocation_quantity,
        "limited_by": limited_by,
        "position_value": round(position_value, 2),
        "position_pct": round(position_value / account * 100.0, 2),
        "estimated_loss": round(estimated_loss, 2),
        "estimated_loss_pct": round(estimated_loss / account * 100.0, 3),
        "formula": "min(손실예산 ÷ 1주당 위험, 최대투입금 ÷ 진입가), 소수점 이하는 버림",
    }


def validate_execution_levels(
    *,
    entry_price: Any,
    stop_price: Any,
    target_price: Any,
    direction: str = "LONG",
    minimum_rr: Any = 1.0,
) -> dict[str, Any]:
    """Validate one coherent entry/stop/target scenario without account data."""

    entry = _positive_float(entry_price)
    stop = _positive_float(stop_price)
    target = _positive_float(target_price)
    side = _direction(direction)
    threshold = _positive_float(minimum_rr)
    if entry is None or stop is None or target is None:
        return {"valid": False, "reason": "진입가·손절가·1차 목표는 모두 0보다 큰 유한한 숫자여야 합니다.", "quantity": 0, "rr": None}
    if side not in {"LONG", "SHORT"}:
        return {"valid": False, "reason": "매수 또는 매도 방향이 필요합니다.", "quantity": 0, "rr": None}
    if not _valid_stop(side, entry, stop):
        return {"valid": False, "reason": "방향에 맞지 않는 손절가입니다. 진입가와 손절가의 순서를 확인하세요.", "quantity": 0, "rr": None}
    if not _valid_target(side, entry, target):
        return {"valid": False, "reason": "방향에 맞지 않는 1차 목표입니다. 진입가와 목표가의 순서를 확인하세요.", "quantity": 0, "rr": None}
    if threshold is None:
        return {"valid": False, "reason": "최소 손익비는 0보다 큰 유한한 숫자여야 합니다.", "quantity": 0, "rr": None}

    rr_value = _reward_risk(side, entry, stop, target)
    if rr_value is None:
        return {"valid": False, "reason": "입력 가격으로 손익비를 계산할 수 없습니다.", "quantity": 0, "rr": None}
    if rr_value < threshold:
        return {
            "valid": False,
            "reason": f"가정 손익비가 {rr_value:.2f}R로 프로그램 안전 게이트 {threshold:.2f}R보다 낮습니다.",
            "quantity": 0,
            "rr": round(rr_value, 4),
            "minimum_rr": round(threshold, 4),
        }
    return {
        "valid": True,
        "reason": "",
        "entry_price": round(entry, 4),
        "stop_price": round(stop, 4),
        "target_price": round(target, 4),
        "direction": side,
        "rr": round(rr_value, 4),
        "minimum_rr": round(threshold, 4),
    }


def calculate_execution_ticket(
    *,
    entry_price: Any,
    stop_price: Any,
    target_price: Any,
    account_size: Any,
    risk_pct: Any,
    max_allocation_pct: Any,
    direction: str = "LONG",
    minimum_rr: Any = 1.0,
) -> dict[str, Any]:
    """Validate one coherent entry/stop/target scenario before sizing it."""

    levels = validate_execution_levels(
        entry_price=entry_price,
        stop_price=stop_price,
        target_price=target_price,
        direction=direction,
        minimum_rr=minimum_rr,
    )
    if not levels.get("valid"):
        return {**levels, "quantity": 0}

    sizing = calculate_position_size(
        entry_price=levels["entry_price"],
        stop_price=levels["stop_price"],
        account_size=account_size,
        risk_pct=risk_pct,
        max_allocation_pct=max_allocation_pct,
        direction=levels["direction"],
    )
    if not sizing.get("valid"):
        return {
            **sizing,
            "rr": levels["rr"],
            "minimum_rr": levels["minimum_rr"],
        }
    return {
        **sizing,
        "entry_price": levels["entry_price"],
        "stop_price": levels["stop_price"],
        "target_price": levels["target_price"],
        "rr": levels["rr"],
        "minimum_rr": levels["minimum_rr"],
        "ticket_note": "입력한 진입·손절·1차 목표를 하나의 가정 시나리오로 검증한 결과입니다.",
    }
