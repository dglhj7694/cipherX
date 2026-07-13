from __future__ import annotations

import copy
import hashlib
import json
import math
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

from .beginner_trade_guide import calculate_execution_ticket, validate_execution_levels
from .holding_scenario import calculate_long_holding_scenario


TRADE_PLAN_SCHEMA = "cipherx.trade-plan"
TRADE_PLAN_BUNDLE_SCHEMA = "cipherx.trade-plans"
TRADE_PLAN_SCHEMA_VERSION = 1
TRADE_PLAN_CALCULATOR_VERSION = 1
MAX_IMPORT_BYTES = 512 * 1024
MAX_SESSION_PLANS = 20
MAX_JSON_DEPTH = 8

PLAN_STATUS_OPTIONS: dict[str, tuple[str, ...]] = {
    "ENTRY_LONG": ("PLANNED", "REVIEW_REQUIRED", "REVIEWED", "CANCELLED", "EXPIRED"),
    "HOLDING_LONG": ("MONITORING", "REVIEW_REQUIRED", "REVIEWED", "CANCELLED", "EXPIRED"),
}

PLAN_STATUS_LABELS = {
    "PLANNED": "진입 계획",
    "MONITORING": "보유 점검 중",
    "REVIEW_REQUIRED": "재검토 필요",
    "REVIEWED": "검토 완료",
    "CANCELLED": "취소",
    "EXPIRED": "만료",
}

PLAN_TYPE_LABELS = {
    "ENTRY_LONG": "신규 진입 계획",
    "HOLDING_LONG": "보유 방어계획",
}

_TOP_LEVEL_KEYS = {
    "schema",
    "schema_version",
    "plan_id",
    "plan_version",
    "plan_type",
    "status",
    "created_at",
    "updated_at",
    "analysis_snapshot",
    "user_inputs",
    "privacy",
    "limitations",
    "note",
    "fingerprint",
}

_ANALYSIS_KEYS = {
    "snapshot_version",
    "ticker",
    "as_of",
    "currency_hint",
    "current_price",
    "price_data_available",
    "judgment",
    "action_code",
    "action_title",
    "action_summary",
    "strategy_label",
    "strategy_status",
    "strategy_score",
    "direction",
    "entry_reference_type",
    "entry_reference",
    "engine_entry_price",
    "engine_invalidation_price",
    "engine_target_1",
    "engine_target_2",
    "engine_rr",
    "sizing_available",
    "levels_conditional",
    "hard_conflict",
    "liquidity_risk",
    "conflict_level",
    "objective_alignment",
    "risk_flags",
    "snapshot_digest",
}

_ENTRY_INPUT_KEYS = {
    "calculator_version",
    "entry_price",
    "stop_price",
    "target_1",
    "target_2",
    "risk_pct",
    "max_allocation_pct",
    "planned_quantity",
    "quantity_included",
}

_HOLDING_INPUT_KEYS = {
    "calculator_version",
    "average_entry",
    "quantity",
    "evaluation_price",
    "evaluation_price_source",
    "user_stop_price",
}

_PRIVACY_KEYS = {"account_size_stored", "plaintext_json", "sensitive_fields"}
_LIMITATION_KEYS = {"order_instruction", "actual_fill_guaranteed", "costs_included", "excluded"}

_FORBIDDEN_KEYS = {
    "account_size",
    "account_equity",
    "available_cash",
    "cash_balance",
    "account_number",
    "broker_account",
    "bank_account",
    "api_key",
    "runtime_gemini_api_key",
    "token",
    "access_token",
    "refresh_token",
    "secret",
    "password",
    "cookie",
    "fig_json",
    "prompt",
    "messages",
    "meta",
}

_TICKER_RE = re.compile(r"^[A-Z0-9]{1,12}(?:[.-][A-Z0-9]{1,8})?$")
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_MAX_ABS_NUMBER = 1e15


class _PlanError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _result_error(code: str, message: str) -> dict[str, Any]:
    return {
        "valid": False,
        "reason": message,
        "errors": [{"code": code, "message": message}],
        "warnings": [],
        "plan": None,
        "calculation": None,
    }


def _strict_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise _PlanError("INVALID_TYPE", f"{label}은 JSON 객체여야 합니다.")
    return value


def _require_exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    actual = set(value.keys())
    unknown = sorted(str(key) for key in actual - expected)
    missing = sorted(expected - actual)
    if unknown:
        raise _PlanError("UNKNOWN_FIELD", f"{label}에 허용되지 않은 필드가 있습니다: {', '.join(unknown[:5])}")
    if missing:
        raise _PlanError("MISSING_FIELD", f"{label}에 필수 필드가 없습니다: {', '.join(missing[:5])}")


def _reject_forbidden_keys(value: Any) -> None:
    if isinstance(value, Mapping):
        for raw_key, item in value.items():
            key = str(raw_key).strip().lower().replace("-", "_").replace(" ", "_")
            if key in _FORBIDDEN_KEYS:
                raise _PlanError("SENSITIVE_FIELD", f"저장하거나 가져올 수 없는 민감 필드입니다: {raw_key}")
            _reject_forbidden_keys(item)
    elif isinstance(value, list):
        for item in value:
            _reject_forbidden_keys(item)


def _strict_text(value: Any, label: str, *, maximum: int, allow_blank: bool = True) -> str:
    if not isinstance(value, str):
        raise _PlanError("INVALID_TEXT", f"{label}은 문자열이어야 합니다.")
    if len(value) > maximum:
        raise _PlanError("TEXT_TOO_LONG", f"{label}은 {maximum}자를 넘을 수 없습니다.")
    if _CONTROL_RE.search(value):
        raise _PlanError("CONTROL_CHARACTER", f"{label}에 허용되지 않은 제어문자가 있습니다.")
    if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
        raise _PlanError("INVALID_UNICODE", f"{label}에 허용되지 않은 Unicode surrogate가 있습니다.")
    cleaned = value.strip()
    if not allow_blank and not cleaned:
        raise _PlanError("MISSING_TEXT", f"{label}이 필요합니다.")
    return cleaned


def _strict_bool(value: Any, label: str) -> bool:
    if type(value) is not bool:
        raise _PlanError("INVALID_BOOLEAN", f"{label}은 true 또는 false여야 합니다.")
    return value


def _strict_int(value: Any, label: str, *, minimum: int = 0, maximum: int = 1_000_000_000) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise _PlanError("INVALID_INTEGER", f"{label}은 정수여야 합니다.")
    if value < minimum or value > maximum:
        raise _PlanError("INTEGER_RANGE", f"{label}의 범위를 확인하세요.")
    return value


def _strict_number(
    value: Any,
    label: str,
    *,
    positive: bool = False,
    minimum: float | None = None,
    maximum: float = _MAX_ABS_NUMBER,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _PlanError("INVALID_NUMBER", f"{label}은 숫자여야 합니다.")
    try:
        number = float(value)
    except (OverflowError, TypeError, ValueError) as exc:
        raise _PlanError("NUMBER_RANGE", f"{label}은 허용 범위의 유한한 숫자여야 합니다.") from exc
    if not math.isfinite(number) or abs(number) > maximum:
        raise _PlanError("NUMBER_RANGE", f"{label}은 허용 범위의 유한한 숫자여야 합니다.")
    if positive and number <= 0:
        raise _PlanError("POSITIVE_REQUIRED", f"{label}은 0보다 커야 합니다.")
    if minimum is not None and number < minimum:
        raise _PlanError("NUMBER_RANGE", f"{label}의 범위를 확인하세요.")
    return number


def _optional_number(value: Any, label: str, *, positive: bool = False) -> float | None:
    if value is None:
        return None
    return _strict_number(value, label, positive=positive)


def _timestamp(value: Any | None = None) -> str:
    if value is None:
        parsed = datetime.now(timezone.utc)
    elif isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        text = value.strip()
        try:
            parsed = datetime.fromisoformat(text[:-1] + "+00:00" if text.endswith("Z") else text)
        except (ValueError, OverflowError) as exc:
            raise _PlanError("INVALID_TIMESTAMP", "시간값은 ISO 8601 형식이어야 합니다.") from exc
    else:
        raise _PlanError("INVALID_TIMESTAMP", "시간값은 ISO 8601 문자열이어야 합니다.")
    try:
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        parsed = parsed.astimezone(timezone.utc).replace(microsecond=0)
    except (OverflowError, OSError, ValueError) as exc:
        raise _PlanError("INVALID_TIMESTAMP", "시간값이 지원 범위를 벗어났습니다.") from exc
    return parsed.isoformat().replace("+00:00", "Z")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _reject_invalid_unicode(value: Any) -> None:
    if isinstance(value, str):
        if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
            raise _PlanError("INVALID_UNICODE", "저장값에 허용되지 않은 Unicode surrogate가 있습니다.")
    elif isinstance(value, Mapping):
        for key, item in value.items():
            _reject_invalid_unicode(str(key))
            _reject_invalid_unicode(item)
    elif isinstance(value, list):
        for item in value:
            _reject_invalid_unicode(item)


def _sha256(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _analysis_digest(snapshot: Mapping[str, Any]) -> str:
    digest_payload = {
        key: snapshot[key]
        for key in sorted(_ANALYSIS_KEYS - {"snapshot_digest"})
        if key not in {"action_title", "action_summary"}
    }
    digest_payload["risk_flags"] = sorted({str(item).strip() for item in snapshot.get("risk_flags") or [] if str(item).strip()})
    return _sha256(digest_payload)


def _plan_fingerprint(plan: Mapping[str, Any]) -> str:
    return _sha256(
        {
            "schema_version": plan["schema_version"],
            "plan_type": plan["plan_type"],
            "analysis_snapshot": plan["analysis_snapshot"],
            "user_inputs": plan["user_inputs"],
            "privacy": plan["privacy"],
            "limitations": plan["limitations"],
            "note": plan["note"],
        }
    )


def _new_plan_id(value: Any | None = None) -> str:
    candidate = str(value).strip() if value is not None else str(uuid.uuid4())
    try:
        parsed = uuid.UUID(candidate)
    except (ValueError, AttributeError) as exc:
        raise _PlanError("INVALID_PLAN_ID", "계획 ID는 올바른 UUID여야 합니다.") from exc
    if parsed.version != 4 or str(parsed) != candidate.lower():
        raise _PlanError("INVALID_PLAN_ID", "계획 ID는 canonical UUID v4 형식이어야 합니다.")
    return str(parsed)


def _normalize_risk_flags(value: Any) -> list[str]:
    if not isinstance(value, list):
        raise _PlanError("INVALID_RISK_FLAGS", "위험 플래그는 문자열 배열이어야 합니다.")
    if len(value) > 8:
        raise _PlanError("TOO_MANY_RISK_FLAGS", "위험 플래그는 최대 8개까지 저장할 수 있습니다.")
    normalized: list[str] = []
    for item in value:
        text = _strict_text(item, "위험 플래그", maximum=200)
        if text and text not in normalized:
            normalized.append(text)
    return normalized


def _analysis_snapshot_from_guide(guide: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(guide, Mapping) or not guide.get("available"):
        raise _PlanError("GUIDE_UNAVAILABLE", "저장할 초보자 가이드가 없습니다.")
    ticker = str(guide.get("ticker") or "").strip().upper()
    if not _TICKER_RE.fullmatch(ticker):
        raise _PlanError("INVALID_TICKER", "저장할 종목 코드를 확인하세요.")

    def optional_number(key: str) -> float | None:
        raw = guide.get(key)
        if raw is None:
            return None
        try:
            number = float(raw)
        except (OverflowError, TypeError, ValueError):
            return None
        return round(number, 8) if math.isfinite(number) and abs(number) <= _MAX_ABS_NUMBER else None

    snapshot = {
        "snapshot_version": 1,
        "ticker": ticker,
        "as_of": str(guide.get("as_of") or "").strip()[:40],
        "currency_hint": str(guide.get("currency_hint") or "계좌 통화").strip()[:40],
        "current_price": optional_number("current_price"),
        "price_data_available": bool(guide.get("price_data_available", True)),
        "judgment": str(guide.get("judgment") or "NEUTRAL").strip().upper()[:40],
        "action_code": str(guide.get("action_code") or "").strip().upper()[:40],
        "action_title": str(guide.get("action_title") or "").strip()[:200],
        "action_summary": str(guide.get("action_summary") or "").strip()[:1000],
        "strategy_label": str(guide.get("strategy_label") or "전략 없음").strip()[:200],
        "strategy_status": str(guide.get("strategy_status") or "").strip().upper()[:40],
        "strategy_score": optional_number("strategy_score"),
        "direction": str(guide.get("direction") or "").strip().upper()[:10],
        "entry_reference_type": str(guide.get("entry_reference_type") or "").strip().upper()[:40],
        "entry_reference": str(guide.get("entry_reference") or "").strip()[:300],
        "engine_entry_price": optional_number("entry_price"),
        "engine_invalidation_price": optional_number("stop_loss"),
        "engine_target_1": optional_number("target_1"),
        "engine_target_2": optional_number("target_2"),
        "engine_rr": optional_number("rr"),
        "sizing_available": bool(guide.get("sizing_available")),
        "levels_conditional": bool(guide.get("levels_conditional")),
        "hard_conflict": bool(guide.get("hard_conflict")),
        "liquidity_risk": bool(guide.get("liquidity_risk")),
        "conflict_level": str(guide.get("conflict_level") or "LOW").strip().upper()[:20],
        "objective_alignment": str(guide.get("objective_alignment") or "MIXED").strip().upper()[:30],
        "risk_flags": [str(item).strip()[:200] for item in list(guide.get("risk_flags") or [])[:8] if str(item).strip()],
        "snapshot_digest": "",
    }
    _reject_invalid_unicode(snapshot)
    snapshot["snapshot_digest"] = _analysis_digest(snapshot)
    return snapshot


def _normalize_analysis_snapshot(value: Any) -> dict[str, Any]:
    snapshot = _strict_mapping(value, "분석 스냅샷")
    _require_exact_keys(snapshot, _ANALYSIS_KEYS, "분석 스냅샷")
    normalized = {
        "snapshot_version": _strict_int(snapshot["snapshot_version"], "스냅샷 버전", minimum=1, maximum=1),
        "ticker": _strict_text(snapshot["ticker"], "종목 코드", maximum=24, allow_blank=False).upper(),
        "as_of": _strict_text(snapshot["as_of"], "분석 기준일", maximum=40),
        "currency_hint": _strict_text(snapshot["currency_hint"], "통화", maximum=40, allow_blank=False),
        "current_price": _optional_number(snapshot["current_price"], "분석 가격", positive=True),
        "price_data_available": _strict_bool(snapshot["price_data_available"], "가격 사용 가능 여부"),
        "judgment": _strict_text(snapshot["judgment"], "엔진 판단", maximum=40, allow_blank=False).upper(),
        "action_code": _strict_text(snapshot["action_code"], "행동 코드", maximum=40).upper(),
        "action_title": _strict_text(snapshot["action_title"], "행동 제목", maximum=200),
        "action_summary": _strict_text(snapshot["action_summary"], "행동 요약", maximum=1000),
        "strategy_label": _strict_text(snapshot["strategy_label"], "전략명", maximum=200, allow_blank=False),
        "strategy_status": _strict_text(snapshot["strategy_status"], "전략 상태", maximum=40).upper(),
        "strategy_score": _optional_number(snapshot["strategy_score"], "전략 점수"),
        "direction": _strict_text(snapshot["direction"], "전략 방향", maximum=10).upper(),
        "entry_reference_type": _strict_text(snapshot["entry_reference_type"], "진입 기준 유형", maximum=40).upper(),
        "entry_reference": _strict_text(snapshot["entry_reference"], "진입 기준", maximum=300),
        "engine_entry_price": _optional_number(snapshot["engine_entry_price"], "엔진 진입가", positive=True),
        "engine_invalidation_price": _optional_number(snapshot["engine_invalidation_price"], "엔진 무효화 가격", positive=True),
        "engine_target_1": _optional_number(snapshot["engine_target_1"], "엔진 1차 목표", positive=True),
        "engine_target_2": _optional_number(snapshot["engine_target_2"], "엔진 2차 목표", positive=True),
        "engine_rr": _optional_number(snapshot["engine_rr"], "엔진 손익비", positive=True),
        "sizing_available": _strict_bool(snapshot["sizing_available"], "수량 계산 가능 여부"),
        "levels_conditional": _strict_bool(snapshot["levels_conditional"], "조건부 가격 여부"),
        "hard_conflict": _strict_bool(snapshot["hard_conflict"], "고위험 충돌 여부"),
        "liquidity_risk": _strict_bool(snapshot["liquidity_risk"], "유동성 위험 여부"),
        "conflict_level": _strict_text(snapshot["conflict_level"], "충돌 수준", maximum=20, allow_blank=False).upper(),
        "objective_alignment": _strict_text(snapshot["objective_alignment"], "객관 엔진 정렬", maximum=30, allow_blank=False).upper(),
        "risk_flags": _normalize_risk_flags(snapshot["risk_flags"]),
        "snapshot_digest": _strict_text(snapshot["snapshot_digest"], "분석 digest", maximum=80, allow_blank=False),
    }
    if not _TICKER_RE.fullmatch(normalized["ticker"]):
        raise _PlanError("INVALID_TICKER", "종목 코드 형식을 확인하세요.")
    if normalized["direction"] not in {"", "LONG", "SHORT", "NEUTRAL"}:
        raise _PlanError("INVALID_DIRECTION", "전략 방향은 LONG, SHORT 또는 NEUTRAL이어야 합니다.")
    if not _DIGEST_RE.fullmatch(normalized["snapshot_digest"]):
        raise _PlanError("INVALID_DIGEST", "분석 스냅샷 digest 형식을 확인하세요.")
    if _analysis_digest(normalized) != normalized["snapshot_digest"]:
        raise _PlanError("SNAPSHOT_DIGEST_MISMATCH", "분석 스냅샷이 저장 후 변경되었습니다.")
    return normalized


def _normalize_entry_inputs(value: Any, snapshot: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    inputs = _strict_mapping(value, "신규 진입 입력")
    _require_exact_keys(inputs, _ENTRY_INPUT_KEYS, "신규 진입 입력")
    normalized = {
        "calculator_version": _strict_int(inputs["calculator_version"], "계산기 버전", minimum=1, maximum=1),
        "entry_price": _strict_number(inputs["entry_price"], "진입가", positive=True),
        "stop_price": _strict_number(inputs["stop_price"], "손절가", positive=True),
        "target_1": _strict_number(inputs["target_1"], "1차 목표", positive=True),
        "target_2": _optional_number(inputs["target_2"], "2차 목표", positive=True),
        "risk_pct": _strict_number(inputs["risk_pct"], "거래당 손실 한도", positive=True, maximum=100.0),
        "max_allocation_pct": _strict_number(inputs["max_allocation_pct"], "종목당 최대 비중", positive=True, maximum=100.0),
        "planned_quantity": inputs["planned_quantity"],
        "quantity_included": _strict_bool(inputs["quantity_included"], "계획 수량 포함 여부"),
    }
    if normalized["risk_pct"] > 100 or normalized["max_allocation_pct"] > 100:
        raise _PlanError("PERCENT_RANGE", "손실 한도와 최대 비중은 100% 이하여야 합니다.")
    if normalized["quantity_included"]:
        normalized["planned_quantity"] = _strict_int(
            normalized["planned_quantity"], "계획 수량", minimum=1, maximum=1_000_000_000
        )
    elif normalized["planned_quantity"] is not None:
        raise _PlanError("QUANTITY_PRIVACY", "계획 수량을 포함하지 않을 때 수량 값은 null이어야 합니다.")
    if normalized["target_2"] is not None and normalized["target_2"] < normalized["target_1"]:
        raise _PlanError("TARGET_ORDER", "2차 목표는 1차 목표보다 같거나 높아야 합니다.")
    if not snapshot["sizing_available"] or snapshot["action_code"] != "PLAN_READY":
        raise _PlanError("ENTRY_NOT_READY", "저장 당시 신규 진입 안전 게이트가 열려 있지 않습니다.")
    if snapshot["hard_conflict"] or snapshot["liquidity_risk"] or snapshot["direction"] != "LONG":
        raise _PlanError("ENTRY_BLOCKED", "신규 현물 매수 계획으로 저장할 수 없는 분석 상태입니다.")
    calculation = validate_execution_levels(
        entry_price=normalized["entry_price"],
        stop_price=normalized["stop_price"],
        target_price=normalized["target_1"],
        direction="LONG",
        minimum_rr=1.0,
    )
    if not calculation.get("valid"):
        raise _PlanError("INVALID_ENTRY_LEVELS", str(calculation.get("reason") or "신규 진입 가격을 검증할 수 없습니다."))
    for key in ("entry_price", "stop_price", "target_1", "target_2", "risk_pct", "max_allocation_pct"):
        if normalized[key] is not None:
            normalized[key] = round(float(normalized[key]), 8)
    return normalized, calculation


def _normalize_holding_inputs(value: Any, snapshot: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    inputs = _strict_mapping(value, "보유 방어 입력")
    _require_exact_keys(inputs, _HOLDING_INPUT_KEYS, "보유 방어 입력")
    normalized = {
        "calculator_version": _strict_int(inputs["calculator_version"], "계산기 버전", minimum=1, maximum=1),
        "average_entry": _strict_number(inputs["average_entry"], "평균단가", positive=True),
        "quantity": _strict_number(inputs["quantity"], "보유 수량", positive=True),
        "evaluation_price": _strict_number(inputs["evaluation_price"], "점검 현재가", positive=True),
        "evaluation_price_source": _strict_text(
            inputs["evaluation_price_source"], "점검 가격 출처", maximum=30, allow_blank=False
        ).upper(),
        "user_stop_price": _strict_number(inputs["user_stop_price"], "사용자 방어 기준", positive=True),
    }
    if normalized["evaluation_price_source"] not in {"ANALYSIS_SNAPSHOT", "USER_INPUT"}:
        raise _PlanError("INVALID_PRICE_SOURCE", "점검 가격 출처를 확인하세요.")
    if normalized["evaluation_price_source"] == "ANALYSIS_SNAPSHOT":
        snapshot_price = snapshot.get("current_price")
        if snapshot_price is None or round(float(snapshot_price), 8) != round(normalized["evaluation_price"], 8):
            raise _PlanError(
                "SNAPSHOT_PRICE_MISMATCH",
                "분석 스냅샷 가격 출처를 선택한 점검 가격이 저장 당시 분석 가격과 다릅니다.",
            )

    engine_stop = snapshot.get("engine_invalidation_price")
    target_1 = snapshot.get("engine_target_1")
    target_2 = snapshot.get("engine_target_2")
    if target_1 is not None and target_2 is not None and float(target_2) < float(target_1):
        target_2 = None
    calculation = calculate_long_holding_scenario(
        current_price=normalized["evaluation_price"],
        average_entry=normalized["average_entry"],
        quantity=normalized["quantity"],
        user_stop_price=normalized["user_stop_price"],
        account_size=None,
        engine_invalidation_price=engine_stop,
        target_1=target_1,
        target_2=target_2,
        judgment=snapshot["judgment"],
        hard_conflict=snapshot["hard_conflict"],
        liquidity_risk=snapshot["liquidity_risk"],
        price_available=snapshot["price_data_available"],
        as_of=snapshot["as_of"],
    )
    if not calculation.get("valid"):
        raise _PlanError("INVALID_HOLDING", str(calculation.get("reason") or "보유 방어계획을 검증할 수 없습니다."))
    for key in (
        "average_entry",
        "quantity",
        "evaluation_price",
        "user_stop_price",
    ):
        if normalized[key] is not None:
            normalized[key] = round(float(normalized[key]), 8)
    return normalized, calculation


def _normalize_privacy(value: Any, plan_type: str, inputs: Mapping[str, Any]) -> dict[str, Any]:
    privacy = _strict_mapping(value, "개인정보 메타데이터")
    _require_exact_keys(privacy, _PRIVACY_KEYS, "개인정보 메타데이터")
    normalized = {
        "account_size_stored": _strict_bool(privacy["account_size_stored"], "계좌금액 저장 여부"),
        "plaintext_json": _strict_bool(privacy["plaintext_json"], "평문 JSON 여부"),
        "sensitive_fields": privacy["sensitive_fields"],
    }
    if normalized["account_size_stored"]:
        raise _PlanError("ACCOUNT_SIZE_FORBIDDEN", "계좌 평가금액은 매매계획에 저장할 수 없습니다.")
    if not normalized["plaintext_json"]:
        raise _PlanError("PRIVACY_MISMATCH", "내보내기 파일은 암호화되지 않은 평문 JSON임을 표시해야 합니다.")
    if not isinstance(normalized["sensitive_fields"], list):
        raise _PlanError("INVALID_SENSITIVE_LIST", "민감 필드 목록 형식을 확인하세요.")
    expected = ["planned_quantity"] if plan_type == "ENTRY_LONG" and inputs["quantity_included"] else []
    if plan_type == "HOLDING_LONG":
        expected = ["average_entry", "quantity"]
    actual = [_strict_text(item, "민감 필드", maximum=50, allow_blank=False) for item in normalized["sensitive_fields"]]
    if actual != expected:
        raise _PlanError("PRIVACY_MISMATCH", "민감 필드 표시가 실제 저장값과 일치하지 않습니다.")
    normalized["sensitive_fields"] = actual
    return normalized


def _normalize_limitations(value: Any) -> dict[str, Any]:
    limitations = _strict_mapping(value, "한계 메타데이터")
    _require_exact_keys(limitations, _LIMITATION_KEYS, "한계 메타데이터")
    normalized = {
        "order_instruction": _strict_bool(limitations["order_instruction"], "주문 지시 여부"),
        "actual_fill_guaranteed": _strict_bool(limitations["actual_fill_guaranteed"], "체결 보장 여부"),
        "costs_included": _strict_bool(limitations["costs_included"], "비용 반영 여부"),
        "excluded": limitations["excluded"],
    }
    if normalized["order_instruction"] or normalized["actual_fill_guaranteed"] or normalized["costs_included"]:
        raise _PlanError("LIMITATION_MISMATCH", "이 버전은 주문 지시·체결 보장·비용 반영을 지원하지 않습니다.")
    expected = ["FEES", "TAXES", "DIVIDENDS", "FX", "SLIPPAGE", "SPREAD_GAP", "EXCHANGE_ROUNDING"]
    if not isinstance(normalized["excluded"], list) or normalized["excluded"] != expected:
        raise _PlanError("LIMITATION_MISMATCH", "계산 제외 항목이 현재 계약과 일치하지 않습니다.")
    return normalized


def validate_trade_plan(value: Any) -> dict[str, Any]:
    """Strictly validate and recalculate a stored trade plan without mutating it."""

    try:
        plan = _strict_mapping(value, "매매계획")
        _reject_forbidden_keys(plan)
        _require_exact_keys(plan, _TOP_LEVEL_KEYS, "매매계획")
        if plan["schema"] != TRADE_PLAN_SCHEMA:
            raise _PlanError("SCHEMA_MISMATCH", "지원하지 않는 매매계획 스키마입니다.")
        schema_version = _strict_int(plan["schema_version"], "스키마 버전", minimum=1, maximum=1)
        plan_id = _new_plan_id(plan["plan_id"])
        plan_version = _strict_int(plan["plan_version"], "계획 버전", minimum=1, maximum=1_000_000)
        plan_type = _strict_text(plan["plan_type"], "계획 유형", maximum=30, allow_blank=False).upper()
        if plan_type not in PLAN_STATUS_OPTIONS:
            raise _PlanError("UNSUPPORTED_PLAN_TYPE", "지원하지 않는 매매계획 유형입니다.")
        status = _strict_text(plan["status"], "계획 상태", maximum=30, allow_blank=False).upper()
        if status not in PLAN_STATUS_OPTIONS[plan_type]:
            raise _PlanError("INVALID_STATUS", "계획 유형에 맞지 않는 상태입니다.")
        created_at = _timestamp(plan["created_at"])
        updated_at = _timestamp(plan["updated_at"])
        if updated_at < created_at:
            raise _PlanError("INVALID_TIMESTAMP_ORDER", "수정 시각이 생성 시각보다 빠를 수 없습니다.")
        snapshot = _normalize_analysis_snapshot(plan["analysis_snapshot"])
        if plan_type == "ENTRY_LONG":
            user_inputs, calculation = _normalize_entry_inputs(plan["user_inputs"], snapshot)
        else:
            user_inputs, calculation = _normalize_holding_inputs(plan["user_inputs"], snapshot)
        privacy = _normalize_privacy(plan["privacy"], plan_type, user_inputs)
        limitations = _normalize_limitations(plan["limitations"])
        note = _strict_text(plan["note"], "계획 메모", maximum=500)
        fingerprint = _strict_text(plan["fingerprint"], "계획 fingerprint", maximum=80, allow_blank=False)
        if not _DIGEST_RE.fullmatch(fingerprint):
            raise _PlanError("INVALID_FINGERPRINT", "계획 fingerprint 형식을 확인하세요.")
        normalized = {
            "schema": TRADE_PLAN_SCHEMA,
            "schema_version": schema_version,
            "plan_id": plan_id,
            "plan_version": plan_version,
            "plan_type": plan_type,
            "status": status,
            "created_at": created_at,
            "updated_at": updated_at,
            "analysis_snapshot": snapshot,
            "user_inputs": user_inputs,
            "privacy": privacy,
            "limitations": limitations,
            "note": note,
            "fingerprint": fingerprint,
        }
        if _plan_fingerprint(normalized) != fingerprint:
            raise _PlanError("FINGERPRINT_MISMATCH", "매매계획의 저장값이 fingerprint와 일치하지 않습니다.")
        return {
            "valid": True,
            "reason": "",
            "errors": [],
            "warnings": [],
            "plan": copy.deepcopy(normalized),
            "calculation": copy.deepcopy(calculation),
        }
    except _PlanError as exc:
        return _result_error(exc.code, exc.message)


def _base_plan(
    *,
    plan_type: str,
    status: str,
    snapshot: dict[str, Any],
    user_inputs: dict[str, Any],
    sensitive_fields: list[str],
    note: str,
    now: Any | None,
    plan_id: Any | None,
) -> dict[str, Any]:
    timestamp = _timestamp(now)
    plan = {
        "schema": TRADE_PLAN_SCHEMA,
        "schema_version": TRADE_PLAN_SCHEMA_VERSION,
        "plan_id": _new_plan_id(plan_id),
        "plan_version": 1,
        "plan_type": plan_type,
        "status": status,
        "created_at": timestamp,
        "updated_at": timestamp,
        "analysis_snapshot": copy.deepcopy(snapshot),
        "user_inputs": copy.deepcopy(user_inputs),
        "privacy": {
            "account_size_stored": False,
            "plaintext_json": True,
            "sensitive_fields": list(sensitive_fields),
        },
        "limitations": {
            "order_instruction": False,
            "actual_fill_guaranteed": False,
            "costs_included": False,
            "excluded": ["FEES", "TAXES", "DIVIDENDS", "FX", "SLIPPAGE", "SPREAD_GAP", "EXCHANGE_ROUNDING"],
        },
        "note": _strict_text(str(note or ""), "계획 메모", maximum=500),
        "fingerprint": "",
    }
    plan["fingerprint"] = _plan_fingerprint(plan)
    return plan


def build_entry_trade_plan(
    guide: Mapping[str, Any],
    *,
    entry_price: Any,
    stop_price: Any,
    target_1: Any,
    target_2: Any | None,
    risk_pct: Any,
    max_allocation_pct: Any,
    planned_quantity: Any | None = None,
    include_quantity: bool = False,
    account_size: Any | None = None,
    note: str = "",
    now: Any | None = None,
    plan_id: Any | None = None,
) -> dict[str, Any]:
    """Build an immutable, account-size-free long entry plan snapshot."""

    try:
        snapshot = _analysis_snapshot_from_guide(guide)
        if not snapshot["as_of"]:
            raise _PlanError("MISSING_AS_OF", "분석 기준일이 없는 결과는 신규 진입 계획으로 저장할 수 없습니다.")
        include_quantity = _strict_bool(include_quantity, "계획 수량 포함 여부")
        first_target = _strict_number(target_1, "1차 목표", positive=True)
        second_target = _optional_number(target_2, "2차 목표", positive=True)
        warnings: list[str] = []
        if second_target is not None and second_target < first_target:
            second_target = None
            warnings.append("2차 목표가 1차 목표보다 낮아 저장 계획에서 제외했습니다.")
        inputs = {
            "calculator_version": TRADE_PLAN_CALCULATOR_VERSION,
            "entry_price": _strict_number(entry_price, "진입가", positive=True),
            "stop_price": _strict_number(stop_price, "손절가", positive=True),
            "target_1": first_target,
            "target_2": second_target,
            "risk_pct": _strict_number(risk_pct, "거래당 손실 한도", positive=True, maximum=100.0),
            "max_allocation_pct": _strict_number(
                max_allocation_pct, "종목당 최대 비중", positive=True, maximum=100.0
            ),
            "planned_quantity": planned_quantity if include_quantity else None,
            "quantity_included": bool(include_quantity),
        }
        normalized_inputs, calculation = _normalize_entry_inputs(inputs, snapshot)
        if include_quantity:
            verified_ticket = calculate_execution_ticket(
                entry_price=normalized_inputs["entry_price"],
                stop_price=normalized_inputs["stop_price"],
                target_price=normalized_inputs["target_1"],
                account_size=account_size,
                risk_pct=normalized_inputs["risk_pct"],
                max_allocation_pct=normalized_inputs["max_allocation_pct"],
                direction="LONG",
                minimum_rr=1.0,
            )
            if not verified_ticket.get("valid"):
                raise _PlanError(
                    "QUANTITY_VERIFICATION_FAILED",
                    str(verified_ticket.get("reason") or "계획 수량을 계좌금액으로 재검산할 수 없습니다."),
                )
            if int(verified_ticket["quantity"]) != normalized_inputs["planned_quantity"]:
                raise _PlanError(
                    "QUANTITY_MISMATCH",
                    "계획 수량이 현재 계좌금액·손실 한도·최대 비중으로 다시 계산한 수량과 다릅니다.",
                )
        plan = _base_plan(
            plan_type="ENTRY_LONG",
            status="PLANNED",
            snapshot=snapshot,
            user_inputs=normalized_inputs,
            sensitive_fields=["planned_quantity"] if include_quantity else [],
            note=note,
            now=now,
            plan_id=plan_id,
        )
        validated = validate_trade_plan(plan)
        if not validated["valid"]:
            return validated
        return {**validated, "warnings": warnings, "calculation": calculation}
    except _PlanError as exc:
        return _result_error(exc.code, exc.message)


def build_holding_trade_plan(
    guide: Mapping[str, Any],
    *,
    average_entry: Any,
    quantity: Any,
    evaluation_price: Any,
    evaluation_price_source: str,
    user_stop_price: Any,
    note: str = "",
    now: Any | None = None,
    plan_id: Any | None = None,
) -> dict[str, Any]:
    """Build a spot-long holding defense snapshot without account size."""

    try:
        snapshot = _analysis_snapshot_from_guide(guide)
        if not snapshot["as_of"]:
            raise _PlanError("MISSING_AS_OF", "분석 기준일이 없는 결과는 보유 방어계획으로 저장할 수 없습니다.")
        inputs = {
            "calculator_version": TRADE_PLAN_CALCULATOR_VERSION,
            "average_entry": _strict_number(average_entry, "평균단가", positive=True),
            "quantity": _strict_number(quantity, "보유 수량", positive=True),
            "evaluation_price": _strict_number(evaluation_price, "점검 현재가", positive=True),
            "evaluation_price_source": str(evaluation_price_source or "").strip().upper(),
            "user_stop_price": _strict_number(user_stop_price, "사용자 방어 기준", positive=True),
        }
        normalized_inputs, calculation = _normalize_holding_inputs(inputs, snapshot)
        status = "REVIEW_REQUIRED" if calculation.get("scenario_code") in {"STOP_REACHED", "DEFEND_REVIEW"} else "MONITORING"
        plan = _base_plan(
            plan_type="HOLDING_LONG",
            status=status,
            snapshot=snapshot,
            user_inputs=normalized_inputs,
            sensitive_fields=["average_entry", "quantity"],
            note=note,
            now=now,
            plan_id=plan_id,
        )
        validated = validate_trade_plan(plan)
        if not validated["valid"]:
            return validated
        return {**validated, "calculation": calculation}
    except _PlanError as exc:
        return _result_error(exc.code, exc.message)


def assess_trade_plan(value: Any, current_guide: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Assess immutable plan freshness against the current analysis guide."""

    validated = validate_trade_plan(value)
    if not validated["valid"]:
        return {**validated, "freshness": "INVALID", "readiness": "INVALID"}
    plan = validated["plan"]
    if current_guide is None:
        return {**validated, "freshness": "UNVERIFIED", "readiness": "REVIEW_REQUIRED"}
    try:
        current_snapshot = _analysis_snapshot_from_guide(current_guide)
    except _PlanError:
        return {**validated, "freshness": "UNVERIFIED", "readiness": "REVIEW_REQUIRED"}
    saved_snapshot = plan["analysis_snapshot"]
    if current_snapshot["ticker"] != saved_snapshot["ticker"]:
        return {**validated, "freshness": "CONTEXT_MISMATCH", "readiness": "REVIEW_REQUIRED"}
    if (
        current_snapshot["as_of"] != saved_snapshot["as_of"]
        or current_snapshot["snapshot_digest"] != saved_snapshot["snapshot_digest"]
    ):
        return {**validated, "freshness": "STALE", "readiness": "REVIEW_REQUIRED"}
    calculation = validated["calculation"]
    if plan["plan_type"] == "ENTRY_LONG":
        readiness = (
            "READY"
            if calculation.get("valid")
            and plan["status"] == "PLANNED"
            and not plan["user_inputs"]["quantity_included"]
            else "REVIEW_REQUIRED"
        )
    else:
        readiness = (
            "MONITORING"
            if calculation.get("scenario_code") in {"HOLD_REVIEW", "NO_STOP_SET"}
            and plan["status"] == "MONITORING"
            else "REVIEW_REQUIRED"
        )
    return {**validated, "freshness": "MATCHED", "readiness": readiness}


def add_trade_plan(existing: Sequence[Any], plan: Any) -> dict[str, Any]:
    """Add one plan by fingerprint without mutating the existing collection."""

    validated_new = validate_trade_plan(plan)
    if not validated_new["valid"]:
        return {**validated_new, "plans": copy.deepcopy(list(existing)), "added": 0, "duplicates": 0}
    normalized_existing: list[dict[str, Any]] = []
    for item in list(existing):
        checked = validate_trade_plan(item)
        if not checked["valid"]:
            return {
                **_result_error("INVALID_EXISTING_PLAN", "기존 세션 계획 중 검증할 수 없는 항목이 있습니다."),
                "plans": copy.deepcopy(list(existing)),
                "added": 0,
                "duplicates": 0,
            }
        normalized_existing.append(checked["plan"])
    new_plan = validated_new["plan"]
    if any(item["fingerprint"] == new_plan["fingerprint"] for item in normalized_existing):
        return {
            "valid": True,
            "reason": "동일한 계획이 이미 저장되어 있습니다.",
            "warnings": ["동일한 계획은 중복 저장하지 않았습니다."],
            "errors": [],
            "plans": copy.deepcopy(normalized_existing),
            "added": 0,
            "duplicates": 1,
        }
    if any(item["plan_id"] == new_plan["plan_id"] for item in normalized_existing):
        return {
            **_result_error("PLAN_ID_CONFLICT", "같은 ID의 다른 계획이 이미 있습니다."),
            "plans": copy.deepcopy(normalized_existing),
            "added": 0,
            "duplicates": 0,
        }
    if len(normalized_existing) >= MAX_SESSION_PLANS:
        return {
            **_result_error("PLAN_LIMIT", f"세션에는 최대 {MAX_SESSION_PLANS}개 계획만 저장할 수 있습니다."),
            "plans": copy.deepcopy(normalized_existing),
            "added": 0,
            "duplicates": 0,
        }
    return {
        "valid": True,
        "reason": "",
        "warnings": [],
        "errors": [],
        "plans": [*copy.deepcopy(normalized_existing), copy.deepcopy(new_plan)],
        "added": 1,
        "duplicates": 0,
    }


def merge_trade_plans(existing: Sequence[Any], incoming: Sequence[Any]) -> dict[str, Any]:
    """Atomically merge imported plans, never overwriting IDs or economic duplicates."""

    original = copy.deepcopy(list(existing))
    current: list[dict[str, Any]] = []
    for item in original:
        checked = validate_trade_plan(item)
        if not checked["valid"]:
            return {**_result_error("INVALID_EXISTING_PLAN", "기존 세션 계획을 검증할 수 없습니다."), "plans": original}
        current.append(checked["plan"])
    normalized_incoming: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for item in list(incoming):
        checked = validate_trade_plan(item)
        if not checked["valid"]:
            return {**checked, "plans": original, "added": 0, "duplicates": 0}
        candidate = checked["plan"]
        if candidate["plan_id"] in seen_ids:
            return {
                **_result_error("DUPLICATE_IMPORT_ID", "가져오기 파일 안에 중복 계획 ID가 있습니다."),
                "plans": original,
                "added": 0,
                "duplicates": 0,
            }
        seen_ids.add(candidate["plan_id"])
        normalized_incoming.append(candidate)

    existing_ids = {item["plan_id"]: item["fingerprint"] for item in current}
    fingerprints = {item["fingerprint"] for item in current}
    additions: list[dict[str, Any]] = []
    duplicate_count = 0
    for candidate in normalized_incoming:
        existing_fp = existing_ids.get(candidate["plan_id"])
        if existing_fp is not None and existing_fp != candidate["fingerprint"]:
            return {
                **_result_error("PLAN_ID_CONFLICT", "가져온 계획 ID가 기존의 다른 계획과 충돌합니다."),
                "plans": original,
                "added": 0,
                "duplicates": 0,
            }
        if existing_fp == candidate["fingerprint"] or candidate["fingerprint"] in fingerprints:
            duplicate_count += 1
            continue
        additions.append(candidate)
        fingerprints.add(candidate["fingerprint"])
        existing_ids[candidate["plan_id"]] = candidate["fingerprint"]
    if len(current) + len(additions) > MAX_SESSION_PLANS:
        return {
            **_result_error("PLAN_LIMIT", f"가져온 계획을 더하면 세션 한도 {MAX_SESSION_PLANS}개를 넘습니다."),
            "plans": original,
            "added": 0,
            "duplicates": 0,
        }
    return {
        "valid": True,
        "reason": "",
        "warnings": [],
        "errors": [],
        "plans": [*copy.deepcopy(current), *copy.deepcopy(additions)],
        "added": len(additions),
        "duplicates": duplicate_count,
    }


def update_trade_plan_status(
    existing: Sequence[Any],
    plan_id: str,
    status: str,
    *,
    now: Any | None = None,
) -> dict[str, Any]:
    original = copy.deepcopy(list(existing))
    normalized_status = str(status or "").strip().upper()
    updated: list[dict[str, Any]] = []
    found = False
    for item in original:
        checked = validate_trade_plan(item)
        if not checked["valid"]:
            return {**checked, "plans": original, "updated": 0}
        plan = checked["plan"]
        if plan["plan_id"] == plan_id:
            found = True
            if normalized_status not in PLAN_STATUS_OPTIONS[plan["plan_type"]]:
                return {
                    **_result_error("INVALID_STATUS", "계획 유형에 맞지 않는 상태입니다."),
                    "plans": original,
                    "updated": 0,
                }
            if plan["status"] != normalized_status:
                if plan["plan_version"] >= 1_000_000:
                    return {
                        **_result_error("PLAN_VERSION_LIMIT", "계획 버전 한도에 도달해 상태를 변경할 수 없습니다."),
                        "plans": original,
                        "updated": 0,
                    }
                plan["status"] = normalized_status
                plan["plan_version"] += 1
                plan["updated_at"] = max(_timestamp(now), plan["updated_at"], plan["created_at"])
            rechecked = validate_trade_plan(plan)
            if not rechecked["valid"]:
                return {**rechecked, "plans": original, "updated": 0}
            plan = rechecked["plan"]
        updated.append(plan)
    if not found:
        return {**_result_error("PLAN_NOT_FOUND", "변경할 계획을 찾을 수 없습니다."), "plans": original, "updated": 0}
    return {"valid": True, "reason": "", "errors": [], "warnings": [], "plans": updated, "updated": 1}


def delete_trade_plan(existing: Sequence[Any], plan_id: str) -> dict[str, Any]:
    original = copy.deepcopy(list(existing))
    normalized: list[dict[str, Any]] = []
    for item in original:
        checked = validate_trade_plan(item)
        if not checked["valid"]:
            return {**checked, "plans": original, "deleted": 0}
        normalized.append(checked["plan"])
    kept = [item for item in normalized if item["plan_id"] != plan_id]
    if len(kept) == len(original):
        return {**_result_error("PLAN_NOT_FOUND", "삭제할 계획을 찾을 수 없습니다."), "plans": original, "deleted": 0}
    return {"valid": True, "reason": "", "errors": [], "warnings": [], "plans": kept, "deleted": 1}


def _json_depth(value: Any) -> int:
    maximum = 1
    stack: list[tuple[Any, int]] = [(value, 1)]
    while stack:
        item, depth = stack.pop()
        maximum = max(maximum, depth)
        if maximum > MAX_JSON_DEPTH:
            return maximum
        if isinstance(item, Mapping):
            stack.extend((child, depth + 1) for child in item.values())
        elif isinstance(item, list):
            stack.extend((child, depth + 1) for child in item)
    return maximum


def _no_duplicate_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _PlanError("DUPLICATE_JSON_KEY", f"JSON에 중복 필드가 있습니다: {key}")
        result[key] = value
    return result


def encode_trade_plan_bundle(plans: Sequence[Any], *, exported_at: Any | None = None) -> dict[str, Any]:
    plan_items = list(plans)
    normalized: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    if len(plan_items) > MAX_SESSION_PLANS:
        return {**_result_error("PLAN_LIMIT", f"최대 {MAX_SESSION_PLANS}개 계획만 내보낼 수 있습니다."), "data": None}
    for item in plan_items:
        checked = validate_trade_plan(item)
        if not checked["valid"]:
            return {**checked, "data": None}
        plan = checked["plan"]
        if plan["plan_id"] in seen_ids:
            return {
                **_result_error("DUPLICATE_EXPORT_ID", "내보낼 계획 목록에 중복 계획 ID가 있습니다."),
                "data": None,
            }
        seen_ids.add(plan["plan_id"])
        normalized.append(plan)
    try:
        bundle = {
            "schema": TRADE_PLAN_BUNDLE_SCHEMA,
            "schema_version": TRADE_PLAN_SCHEMA_VERSION,
            "exported_at": _timestamp(exported_at),
            "plans": normalized,
        }
        data = json.dumps(
            bundle,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        if len(data) > MAX_IMPORT_BYTES:
            return {**_result_error("EXPORT_TOO_LARGE", "내보내기 파일이 512KiB 제한을 넘습니다."), "data": None}
        return {"valid": True, "reason": "", "errors": [], "warnings": [], "data": data, "bundle": bundle}
    except (_PlanError, ValueError) as exc:
        if isinstance(exc, _PlanError):
            return {**_result_error(exc.code, exc.message), "data": None}
        return {**_result_error("EXPORT_ERROR", "매매계획 JSON을 만들 수 없습니다."), "data": None}


def decode_trade_plan_bundle(payload: Any, *, imported_at: Any | None = None) -> dict[str, Any]:
    """Strictly decode one UTF-8 JSON bundle. Failure is atomic."""

    try:
        if isinstance(payload, bytes):
            raw = payload
        elif isinstance(payload, str):
            try:
                raw = payload.encode("utf-8")
            except UnicodeEncodeError as exc:
                raise _PlanError("INVALID_UNICODE", "가져오기 값에 올바르지 않은 Unicode가 있습니다.") from exc
        else:
            raise _PlanError("INVALID_PAYLOAD", "가져오기 값은 UTF-8 JSON 파일이어야 합니다.")
        if not raw:
            raise _PlanError("EMPTY_IMPORT", "가져오기 파일이 비어 있습니다.")
        if len(raw) > MAX_IMPORT_BYTES:
            raise _PlanError("IMPORT_TOO_LARGE", "가져오기 파일은 512KiB를 넘을 수 없습니다.")
        try:
            text = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise _PlanError("INVALID_UTF8", "가져오기 파일은 UTF-8이어야 합니다.") from exc

        def reject_constant(value: str) -> Any:
            raise _PlanError("NON_FINITE_JSON", f"JSON에서 {value} 값은 허용되지 않습니다.")

        try:
            decoded = json.loads(text, object_pairs_hook=_no_duplicate_object, parse_constant=reject_constant)
        except _PlanError:
            raise
        except (json.JSONDecodeError, ValueError, RecursionError) as exc:
            raise _PlanError("INVALID_JSON", "올바른 매매계획 JSON 파일이 아닙니다.") from exc
        if _json_depth(decoded) > MAX_JSON_DEPTH:
            raise _PlanError("JSON_TOO_DEEP", "JSON 중첩 깊이가 허용 범위를 넘습니다.")
        root = _strict_mapping(decoded, "가져오기 파일")
        expected_root = {"schema", "schema_version", "exported_at", "plans"}
        _require_exact_keys(root, expected_root, "가져오기 파일")
        if root["schema"] != TRADE_PLAN_BUNDLE_SCHEMA:
            raise _PlanError("SCHEMA_MISMATCH", "지원하지 않는 매매계획 묶음입니다.")
        _strict_int(root["schema_version"], "묶음 스키마 버전", minimum=1, maximum=1)
        _timestamp(root["exported_at"])
        if not isinstance(root["plans"], list):
            raise _PlanError("INVALID_PLAN_LIST", "계획 목록은 배열이어야 합니다.")
        if len(root["plans"]) > MAX_SESSION_PLANS:
            raise _PlanError("PLAN_LIMIT", f"가져오기 파일에는 최대 {MAX_SESSION_PLANS}개 계획만 넣을 수 있습니다.")
        plans: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        import_timestamp = _timestamp(imported_at)
        for item in root["plans"]:
            checked = validate_trade_plan(item)
            if not checked["valid"]:
                error = checked["errors"][0]
                raise _PlanError(str(error["code"]), str(error["message"]))
            plan = checked["plan"]
            if plan["plan_id"] in seen_ids:
                raise _PlanError("DUPLICATE_IMPORT_ID", "가져오기 파일 안에 중복 계획 ID가 있습니다.")
            seen_ids.add(plan["plan_id"])
            if plan["status"] != "REVIEW_REQUIRED":
                if plan["plan_version"] >= 1_000_000:
                    raise _PlanError("PLAN_VERSION_LIMIT", "계획 버전 한도에 도달해 가져오기 상태를 변경할 수 없습니다.")
                plan["status"] = "REVIEW_REQUIRED"
                plan["plan_version"] += 1
                plan["updated_at"] = max(import_timestamp, plan["created_at"], plan["updated_at"])
                rechecked = validate_trade_plan(plan)
                if not rechecked["valid"]:
                    error = rechecked["errors"][0]
                    raise _PlanError(str(error["code"]), str(error["message"]))
                plan = rechecked["plan"]
            plans.append(plan)
        return {
            "valid": True,
            "reason": "",
            "errors": [],
            "warnings": ["가져온 계획은 현재 분석과 다시 대조할 때까지 재검토 필요 상태입니다."],
            "plans": copy.deepcopy(plans),
            "count": len(plans),
        }
    except _PlanError as exc:
        return {**_result_error(exc.code, exc.message), "plans": [], "count": 0}
