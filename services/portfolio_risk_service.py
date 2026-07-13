from __future__ import annotations

import copy
import math
import re
from collections import Counter, defaultdict
from typing import Any, Mapping, Sequence

from .beginner_trade_guide import calculate_execution_ticket
from .holding_scenario import calculate_long_holding_scenario
from .trade_plan_service import MAX_SESSION_PLANS, PLAN_STATUS_LABELS, PLAN_TYPE_LABELS, validate_trade_plan


PORTFOLIO_RISK_VERSION = 1
_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
_HOLDING_CONFIRMATION_KEYS = {
    "confirmed",
    "average_entry",
    "quantity",
    "current_price",
    "user_stop_price",
}


class _PortfolioRiskError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _error(code: str, message: str) -> dict[str, Any]:
    return {
        "valid": False,
        "reason": message,
        "errors": [{"code": code, "message": message}],
        "warnings": [],
        "inspection": None,
        "summary": None,
    }


def _strict_bool(value: Any, label: str) -> bool:
    if type(value) is not bool:
        raise _PortfolioRiskError("INVALID_BOOLEAN", f"{label}은 true 또는 false여야 합니다.")
    return value


def _positive_number(value: Any, label: str, *, maximum: float = 1e18) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _PortfolioRiskError("INVALID_NUMBER", f"{label}은 숫자여야 합니다.")
    try:
        number = float(value)
    except (OverflowError, TypeError, ValueError) as exc:
        raise _PortfolioRiskError("NUMBER_RANGE", f"{label}의 범위를 확인하세요.") from exc
    if not math.isfinite(number) or number <= 0 or number > maximum:
        raise _PortfolioRiskError("NUMBER_RANGE", f"{label}은 0보다 큰 유한한 숫자여야 합니다.")
    return number


def _optional_percent(value: Any, label: str) -> float | None:
    if value is None:
        return None
    number = _positive_number(value, label, maximum=100.0)
    if number > 100:
        raise _PortfolioRiskError("PERCENT_RANGE", f"{label}은 100% 이하여야 합니다.")
    return number


def _id_list(value: Any, label: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise _PortfolioRiskError("INVALID_ID_LIST", f"{label}은 계획 ID 배열이어야 합니다.")
    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise _PortfolioRiskError("INVALID_PLAN_ID", f"{label}에 올바르지 않은 계획 ID가 있습니다.")
        plan_id = item.strip()
        if plan_id in normalized:
            raise _PortfolioRiskError("DUPLICATE_SELECTION", f"{label}에 중복 계획 ID가 있습니다.")
        normalized.append(plan_id)
    if len(normalized) > MAX_SESSION_PLANS:
        raise _PortfolioRiskError("PLAN_LIMIT", f"최대 {MAX_SESSION_PLANS}개 계획만 점검할 수 있습니다.")
    return normalized


def _ticker_list(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise _PortfolioRiskError("INVALID_TICKER_LIST", "동시 진입 확인 종목은 문자열 배열이어야 합니다.")
    result: set[str] = set()
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise _PortfolioRiskError("INVALID_TICKER", "동시 진입 확인 종목을 확인하세요.")
        result.add(item.strip().upper())
    return result


def _round(value: float | None, digits: int = 4) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)


def inspect_portfolio_risk_plans(plans: Sequence[Any]) -> dict[str, Any]:
    """Validate plans and expose only the fields needed for an explicit risk check."""

    try:
        if isinstance(plans, (str, bytes)) or not isinstance(plans, Sequence):
            raise _PortfolioRiskError("INVALID_PLAN_LIST", "매매계획 목록 형식을 확인하세요.")
        items = list(plans)
        if len(items) > MAX_SESSION_PLANS:
            raise _PortfolioRiskError("PLAN_LIMIT", f"최대 {MAX_SESSION_PLANS}개 계획만 점검할 수 있습니다.")

        candidates: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        for index, item in enumerate(items):
            checked = validate_trade_plan(item)
            if not checked.get("valid"):
                reason = str(checked.get("reason") or "계획을 검증할 수 없습니다.")
                raise _PortfolioRiskError("INVALID_TRADE_PLAN", f"{index + 1}번째 계획: {reason}")
            plan = checked["plan"]
            if plan["plan_id"] in seen_ids:
                raise _PortfolioRiskError("DUPLICATE_PLAN_ID", "매매계획 목록에 중복 계획 ID가 있습니다.")
            seen_ids.add(plan["plan_id"])
            snapshot = plan["analysis_snapshot"]
            inputs = plan["user_inputs"]
            plan_type = plan["plan_type"]
            status = plan["status"]
            if plan_type == "ENTRY_LONG":
                selectable = status == "PLANNED"
                reason_code = "" if selectable else "ENTRY_STATUS_REVIEW"
                reason = "" if selectable else "진입 계획 상태를 재검토한 뒤 `진입 계획`으로 바꾸세요."
            else:
                selectable = True
                reason_code = "" if status == "MONITORING" else "HOLDING_STATUS_RECONFIRM"
                reason = "" if status == "MONITORING" else "상태만으로 실제 보유 종료를 판단할 수 없어 직접 재확인이 필요합니다."
            candidates.append(
                {
                    "plan_id": plan["plan_id"],
                    "plan_type": plan_type,
                    "plan_type_label": PLAN_TYPE_LABELS.get(plan_type, plan_type),
                    "status": status,
                    "status_label": PLAN_STATUS_LABELS.get(status, status),
                    "ticker": snapshot["ticker"],
                    "currency_hint": snapshot["currency_hint"],
                    "as_of": snapshot["as_of"],
                    "selectable": selectable,
                    "review_required": status not in {"PLANNED", "MONITORING"},
                    "reason_code": reason_code,
                    "reason": reason,
                    "entry_price": inputs.get("entry_price"),
                    "stop_price": inputs.get("stop_price"),
                    "risk_pct": inputs.get("risk_pct"),
                    "max_allocation_pct": inputs.get("max_allocation_pct"),
                    "stored_quantity": inputs.get("planned_quantity")
                    if plan_type == "ENTRY_LONG"
                    else inputs.get("quantity"),
                    "stored_average_entry": inputs.get("average_entry"),
                    "stored_current_price": inputs.get("evaluation_price"),
                    "stored_user_stop_price": inputs.get("user_stop_price"),
                }
            )

        currencies = sorted({str(item["currency_hint"]) for item in candidates})
        return {
            "valid": True,
            "reason": "",
            "errors": [],
            "warnings": [],
            "inspection": {
                "version": PORTFOLIO_RISK_VERSION,
                "candidates": copy.deepcopy(candidates),
                "currencies": currencies,
                "plan_count": len(candidates),
            },
        }
    except _PortfolioRiskError as exc:
        return _error(exc.code, exc.message)


def calculate_portfolio_risk_summary(
    plans: Sequence[Any],
    *,
    source_currency_hint: str,
    currency_code: str = "",
    currency_confirmed: bool = False,
    account_size: Any | None = None,
    selected_entry_ids: Sequence[str] | None = None,
    holding_confirmations: Mapping[str, Mapping[str, Any]] | None = None,
    multiple_entry_tickers_confirmed: Sequence[str] | None = None,
    include_combined_scenario: bool = False,
    completeness_confirmed: bool = False,
    max_total_risk_pct: Any | None = None,
    max_total_exposure_pct: Any | None = None,
    max_single_ticker_exposure_pct: Any | None = None,
) -> dict[str, Any]:
    """Calculate explicit, currency-isolated holding and pending-entry risk scenarios.

    The function never infers executions or live holdings from a plan status. Passing
    ``selected_entry_ids`` means the caller has explicitly rechecked each saved
    analysis date, entry, and stop as a still-active pending scenario. Current holding
    values and simultaneous entry selections must be supplied by the user.
    """

    try:
        if isinstance(plans, (str, bytes)) or not isinstance(plans, Sequence):
            raise _PortfolioRiskError("INVALID_PLAN_LIST", "매매계획 목록 형식을 확인하세요.")
        original = copy.deepcopy(list(plans))
        inspection_result = inspect_portfolio_risk_plans(plans)
        if not inspection_result.get("valid"):
            error = inspection_result["errors"][0]
            raise _PortfolioRiskError(str(error["code"]), str(error["message"]))
        inspection = inspection_result["inspection"]
        candidates = list(inspection["candidates"])
        candidate_by_id = {item["plan_id"]: item for item in candidates}

        source_hint = str(source_currency_hint or "").strip()
        if not source_hint or source_hint not in inspection["currencies"]:
            raise _PortfolioRiskError("UNKNOWN_CURRENCY_GROUP", "점검할 저장 계획의 통화 그룹을 확인하세요.")
        confirmed_currency = _strict_bool(currency_confirmed, "통화 확인")
        code = str(currency_code or "").strip().upper()
        if confirmed_currency and not _CURRENCY_RE.fullmatch(code):
            raise _PortfolioRiskError("INVALID_CURRENCY", "확인 통화는 USD, KRW 같은 3자리 영문 코드여야 합니다.")
        if code and not _CURRENCY_RE.fullmatch(code):
            raise _PortfolioRiskError("INVALID_CURRENCY", "통화 코드는 3자리 영문이어야 합니다.")
        normalized_source_code = source_hint.upper()
        if confirmed_currency and _CURRENCY_RE.fullmatch(normalized_source_code) and code != normalized_source_code:
            raise _PortfolioRiskError(
                "CURRENCY_MISMATCH",
                f"저장 계획 통화 {normalized_source_code}와 확인한 계좌 통화 {code}가 다릅니다.",
            )

        account = None if account_size is None else _positive_number(account_size, "계좌 평가금액")
        risk_limit_pct = _optional_percent(max_total_risk_pct, "계좌 전체 위험 한도")
        exposure_limit_pct = _optional_percent(max_total_exposure_pct, "총 노출 한도")
        ticker_limit_pct = _optional_percent(max_single_ticker_exposure_pct, "동일 종목 노출 한도")
        combined_requested = _strict_bool(include_combined_scenario, "합산 시나리오 확인")
        complete = _strict_bool(completeness_confirmed, "계획 선택 완료 확인")

        entry_ids = _id_list(selected_entry_ids, "선택 진입 계획")
        holding_values = {} if holding_confirmations is None else holding_confirmations
        if not isinstance(holding_values, Mapping):
            raise _PortfolioRiskError("INVALID_HOLDING_INPUTS", "보유 확인값 형식을 확인하세요.")
        allowed_multiple_entries = _ticker_list(multiple_entry_tickers_confirmed)

        selected_candidates: list[dict[str, Any]] = []
        for plan_id in entry_ids:
            candidate = candidate_by_id.get(plan_id)
            if candidate is None:
                raise _PortfolioRiskError("PLAN_NOT_FOUND", "선택한 신규 진입 계획을 찾을 수 없습니다.")
            if candidate["plan_type"] != "ENTRY_LONG" or not candidate["selectable"]:
                raise _PortfolioRiskError("ENTRY_NOT_SELECTABLE", "재검토·취소·만료 상태의 신규 진입 계획은 합산할 수 없습니다.")
            if candidate["currency_hint"] != source_hint:
                raise _PortfolioRiskError("MIXED_CURRENCY", "서로 다른 저장 통화 그룹은 합산할 수 없습니다.")
            selected_candidates.append(candidate)

        normalized_holdings: dict[str, Mapping[str, Any]] = {}
        for raw_plan_id, raw_values in holding_values.items():
            plan_id = str(raw_plan_id or "").strip()
            candidate = candidate_by_id.get(plan_id)
            if candidate is None:
                raise _PortfolioRiskError("PLAN_NOT_FOUND", "확인한 보유 계획을 찾을 수 없습니다.")
            if candidate["plan_type"] != "HOLDING_LONG":
                raise _PortfolioRiskError("INVALID_HOLDING_PLAN", "보유 확인값이 신규 진입 계획을 가리킵니다.")
            if candidate["currency_hint"] != source_hint:
                raise _PortfolioRiskError("MIXED_CURRENCY", "서로 다른 저장 통화 그룹은 합산할 수 없습니다.")
            if not isinstance(raw_values, Mapping) or set(raw_values.keys()) != _HOLDING_CONFIRMATION_KEYS:
                raise _PortfolioRiskError("INVALID_HOLDING_INPUTS", "보유 확인값의 필드를 확인하세요.")
            normalized_holdings[plan_id] = raw_values
            selected_candidates.append(candidate)

        if combined_requested and not (entry_ids and normalized_holdings):
            raise _PortfolioRiskError(
                "COMBINED_SCENARIO_UNAVAILABLE",
                "동시 체결 합산은 실제 보유와 신규 진입계획을 모두 확인한 경우에만 계산할 수 있습니다.",
            )

        duplicate_holding_tickers = [
            ticker
            for ticker, count in Counter(
                item["ticker"] for item in selected_candidates if item["plan_type"] == "HOLDING_LONG"
            ).items()
            if count > 1
        ]
        if duplicate_holding_tickers:
            raise _PortfolioRiskError(
                "AMBIGUOUS_HOLDING_SELECTION",
                "동일 종목의 복수 보유계획은 계좌·포지션 구분 정보가 없어 함께 합산할 수 없습니다: "
                + ", ".join(sorted(duplicate_holding_tickers)),
            )
        duplicate_entry_tickers = [
            ticker
            for ticker, count in Counter(
                item["ticker"] for item in selected_candidates if item["plan_type"] == "ENTRY_LONG"
            ).items()
            if count > 1 and ticker not in allowed_multiple_entries
        ]
        if duplicate_entry_tickers:
            raise _PortfolioRiskError(
                "AMBIGUOUS_ENTRY_SELECTION",
                "동일 종목의 복수 진입계획은 분할·동시 계획임을 확인해야 합니다: "
                + ", ".join(sorted(duplicate_entry_tickers)),
            )

        plan_by_id: dict[str, dict[str, Any]] = {}
        for item in original:
            checked = validate_trade_plan(item)
            if not checked.get("valid"):
                raise _PortfolioRiskError("INVALID_TRADE_PLAN", str(checked.get("reason") or "계획 검증 실패"))
            plan_by_id[checked["plan"]["plan_id"]] = checked["plan"]

        entry_rows: list[dict[str, Any]] = []
        if entry_ids and account is None:
            raise _PortfolioRiskError("ACCOUNT_REQUIRED", "신규 진입 수량을 재계산하려면 현재 계좌 평가금액이 필요합니다.")
        for plan_id in entry_ids:
            plan = plan_by_id[plan_id]
            inputs = plan["user_inputs"]
            ticket = calculate_execution_ticket(
                entry_price=inputs["entry_price"],
                stop_price=inputs["stop_price"],
                target_price=inputs["target_1"],
                account_size=account,
                risk_pct=inputs["risk_pct"],
                max_allocation_pct=inputs["max_allocation_pct"],
                direction="LONG",
                minimum_rr=1.0,
            )
            if not ticket.get("valid"):
                raise _PortfolioRiskError(
                    "ENTRY_RECALCULATION_FAILED",
                    f"{plan['analysis_snapshot']['ticker']} 진입계획: {ticket.get('reason') or '수량 재계산 실패'}",
                )
            quantity = int(ticket["quantity"])
            entry_price = float(ticket["entry_price"])
            stop_price = float(ticket["stop_price"])
            exposure = entry_price * quantity
            risk_at_stop = (entry_price - stop_price) * quantity
            entry_rows.append(
                {
                    "plan_id": plan_id,
                    "ticker": plan["analysis_snapshot"]["ticker"],
                    "as_of": plan["analysis_snapshot"]["as_of"],
                    "status": plan["status"],
                    "quantity": quantity,
                    "entry_price": entry_price,
                    "stop_price": stop_price,
                    "exposure": exposure,
                    "risk_at_stop": risk_at_stop,
                    "risk_pct_of_account": risk_at_stop / account * 100.0,
                    "stored_quantity_ignored": inputs.get("planned_quantity"),
                    "limited_by": ticket.get("limited_by"),
                }
            )

        holding_rows: list[dict[str, Any]] = []
        urgent_rows: list[dict[str, Any]] = []
        for plan_id, values in normalized_holdings.items():
            confirmed = _strict_bool(values["confirmed"], "현재 실제 보유 확인")
            if not confirmed:
                raise _PortfolioRiskError("HOLDING_NOT_CONFIRMED", "현재 실제 보유임을 확인하지 않은 계획은 합산할 수 없습니다.")
            plan = plan_by_id[plan_id]
            average = _positive_number(values["average_entry"], "현재 확인 평단")
            quantity = _positive_number(values["quantity"], "현재 확인 보유 수량")
            current_price = _positive_number(values["current_price"], "현재 확인 가격")
            user_stop = _positive_number(values["user_stop_price"], "현재 확인 사용자 방어선")
            scenario = calculate_long_holding_scenario(
                current_price=current_price,
                average_entry=average,
                quantity=quantity,
                user_stop_price=user_stop,
                account_size=account,
                engine_invalidation_price=None,
                target_1=None,
                target_2=None,
                judgment="NEUTRAL",
                hard_conflict=False,
                liquidity_risk=False,
                price_available=True,
                as_of=plan["analysis_snapshot"]["as_of"],
            )
            if not scenario.get("valid"):
                raise _PortfolioRiskError(
                    "HOLDING_RECALCULATION_FAILED",
                    f"{plan['analysis_snapshot']['ticker']} 보유계획: {scenario.get('reason') or '보유 재계산 실패'}",
                )
            exposure = current_price * quantity
            giveback_to_stop = max(current_price - user_stop, 0.0) * quantity
            pnl_at_stop = (user_stop - average) * quantity
            row = {
                "plan_id": plan_id,
                "ticker": plan["analysis_snapshot"]["ticker"],
                "as_of": plan["analysis_snapshot"]["as_of"],
                "status": plan["status"],
                "average_entry": average,
                "quantity": quantity,
                "current_price": current_price,
                "user_stop_price": user_stop,
                "exposure": exposure,
                "giveback_to_stop": giveback_to_stop,
                "pnl_at_stop": pnl_at_stop,
                "capital_loss_at_stop": max(-pnl_at_stop, 0.0),
                "locked_profit_at_stop": max(pnl_at_stop, 0.0),
                "stop_triggered": bool(scenario["stop_triggered"]),
                "review_required": plan["status"] != "MONITORING",
            }
            if row["stop_triggered"]:
                urgent_rows.append(row)
            else:
                holding_rows.append(row)

        def checked_sum(values: Sequence[float], label: str) -> float:
            total = math.fsum(values)
            if not math.isfinite(total):
                raise _PortfolioRiskError("ARITHMETIC_OVERFLOW", f"{label} 합계가 허용 범위를 벗어났습니다.")
            return total

        all_holding_rows = holding_rows + urgent_rows
        holding_exposure = checked_sum([row["exposure"] for row in all_holding_rows], "보유 노출")
        holding_risk = checked_sum([row["giveback_to_stop"] for row in holding_rows], "보유 방어선 위험")
        holding_capital_loss = checked_sum(
            [row["capital_loss_at_stop"] for row in holding_rows], "보유 방어선 원금손실"
        )
        entry_exposure = checked_sum([row["exposure"] for row in entry_rows], "신규 진입 노출")
        entry_risk = checked_sum([row["risk_at_stop"] for row in entry_rows], "신규 진입 위험")

        holding_summary = {
            "selected_count": len(holding_rows) + len(urgent_rows),
            "quantified_count": len(holding_rows),
            "urgent_count": len(urgent_rows),
            "exposure": _round(holding_exposure),
            "giveback_to_stop": None if urgent_rows else _round(holding_risk),
            "quantified_giveback_to_stop": _round(holding_risk),
            "capital_loss_at_stop": None if urgent_rows else _round(holding_capital_loss),
            "quantified_capital_loss_at_stop": _round(holding_capital_loss),
            "risk_complete": not bool(urgent_rows),
            "exposure_pct_of_account": _round(holding_exposure / account * 100.0) if account else None,
            "risk_pct_of_account": _round(holding_risk / account * 100.0)
            if account and not urgent_rows
            else None,
        }
        entry_summary = {
            "selected_count": len(entry_rows),
            "exposure": _round(entry_exposure),
            "risk_at_stop": _round(entry_risk),
            "exposure_pct_of_account": _round(entry_exposure / account * 100.0) if account else None,
            "risk_pct_of_account": _round(entry_risk / account * 100.0) if account else None,
        }

        combined_summary = None
        has_holding = bool(all_holding_rows)
        has_entry = bool(entry_rows)
        if combined_requested:
            combined_exposure = holding_exposure + entry_exposure
            combined_risk = holding_risk + entry_risk if not urgent_rows else None
            combined_summary = {
                "scenario_label": "선택한 모든 신규 진입이 계획가에 체결된 동시 가정",
                "exposure": _round(combined_exposure),
                "risk_at_stop": _round(combined_risk),
                "quantified_risk_at_stop": _round(holding_risk + entry_risk),
                "risk_complete": not bool(urgent_rows),
                "exposure_pct_of_account": _round(combined_exposure / account * 100.0) if account else None,
                "risk_pct_of_account": _round(combined_risk / account * 100.0)
                if account and combined_risk is not None
                else None,
            }
        elif has_entry and has_holding:
            combined_exposure = None
            combined_risk = None
        elif has_entry:
            combined_exposure = entry_exposure
            combined_risk = entry_risk
        else:
            combined_exposure = holding_exposure
            combined_risk = holding_risk if not urgent_rows else None

        holding_ticker_exposure: dict[str, float] = defaultdict(float)
        holding_ticker_risk: dict[str, float] = defaultdict(float)
        holding_ticker_unquantified: dict[str, int] = defaultdict(int)
        for row in holding_rows:
            holding_ticker_exposure[row["ticker"]] += row["exposure"]
            holding_ticker_risk[row["ticker"]] += row["giveback_to_stop"]
        for row in urgent_rows:
            holding_ticker_exposure[row["ticker"]] += row["exposure"]
            holding_ticker_unquantified[row["ticker"]] += 1

        entry_ticker_exposure: dict[str, float] = defaultdict(float)
        entry_ticker_risk: dict[str, float] = defaultdict(float)
        for row in entry_rows:
            entry_ticker_exposure[row["ticker"]] += row["exposure"]
            entry_ticker_risk[row["ticker"]] += row["risk_at_stop"]

        def public_ticker_rows(
            exposure_by_ticker: Mapping[str, float],
            risk_by_ticker: Mapping[str, float],
            *,
            scope: str,
            unquantified_by_ticker: Mapping[str, int] | None = None,
        ) -> list[dict[str, Any]]:
            missing = unquantified_by_ticker or {}
            return [
                {
                    "scope": scope,
                    "ticker": ticker,
                    "exposure": _round(exposure),
                    "exposure_pct_of_account": _round(exposure / account * 100.0) if account else None,
                    "risk_at_stop": None if missing.get(ticker, 0) else _round(risk_by_ticker.get(ticker, 0.0)),
                    "quantified_risk_at_stop": _round(risk_by_ticker.get(ticker, 0.0)),
                    "risk_pct_of_account": _round(risk_by_ticker.get(ticker, 0.0) / account * 100.0)
                    if account and not missing.get(ticker, 0)
                    else None,
                    "risk_unquantified_count": int(missing.get(ticker, 0)),
                }
                for ticker, exposure in sorted(exposure_by_ticker.items(), key=lambda item: (-item[1], item[0]))
            ]

        holding_ticker_rows = public_ticker_rows(
            holding_ticker_exposure,
            holding_ticker_risk,
            scope="HOLDING",
            unquantified_by_ticker=holding_ticker_unquantified,
        )
        entry_ticker_rows = public_ticker_rows(
            entry_ticker_exposure,
            entry_ticker_risk,
            scope="PENDING_ENTRY",
        )
        if combined_requested:
            combined_ticker_exposure: dict[str, float] = defaultdict(float, holding_ticker_exposure)
            combined_ticker_risk: dict[str, float] = defaultdict(float, holding_ticker_risk)
            for ticker, exposure in entry_ticker_exposure.items():
                combined_ticker_exposure[ticker] += exposure
            for ticker, risk in entry_ticker_risk.items():
                combined_ticker_risk[ticker] += risk
            ticker_rows = public_ticker_rows(
                combined_ticker_exposure,
                combined_ticker_risk,
                scope="COMBINED",
                unquantified_by_ticker=holding_ticker_unquantified,
            )
        elif has_holding and has_entry:
            ticker_rows = holding_ticker_rows + entry_ticker_rows
        elif has_holding:
            ticker_rows = holding_ticker_rows
        else:
            ticker_rows = entry_ticker_rows

        limit_breaches: list[dict[str, Any]] = []
        risk_budget = account * risk_limit_pct / 100.0 if account and risk_limit_pct is not None else None
        scenario_limits: list[tuple[str, float, float, bool, Mapping[str, float]]] = []
        if combined_requested:
            scenario_limits.append(
                (
                    "COMBINED",
                    combined_exposure,
                    holding_risk + entry_risk,
                    not bool(urgent_rows),
                    combined_ticker_exposure,
                )
            )
        else:
            if has_holding:
                scenario_limits.append(
                    ("HOLDING", holding_exposure, holding_risk, not bool(urgent_rows), holding_ticker_exposure)
                )
            if has_entry:
                scenario_limits.append(("PENDING_ENTRY", entry_exposure, entry_risk, True, entry_ticker_exposure))

        for scope, scenario_exposure, quantified_risk, risk_complete, scenario_tickers in scenario_limits:
            if risk_budget is not None and quantified_risk > risk_budget:
                limit_breaches.append(
                    {
                        "code": "TOTAL_RISK",
                        "scope": scope,
                        "actual_pct": quantified_risk / account * 100.0,
                        "limit_pct": risk_limit_pct,
                        "partial": not risk_complete,
                    }
                )
            if account and exposure_limit_pct is not None:
                exposure_pct = scenario_exposure / account * 100.0
                if exposure_pct > exposure_limit_pct:
                    limit_breaches.append(
                        {
                            "code": "TOTAL_EXPOSURE",
                            "scope": scope,
                            "actual_pct": exposure_pct,
                            "limit_pct": exposure_limit_pct,
                        }
                    )
            if account and ticker_limit_pct is not None:
                for ticker, ticker_exposure_value in scenario_tickers.items():
                    actual_pct = ticker_exposure_value / account * 100.0
                    if actual_pct > ticker_limit_pct:
                        limit_breaches.append(
                            {
                                "code": "TICKER_EXPOSURE",
                                "scope": scope,
                                "ticker": ticker,
                                "actual_pct": actual_pct,
                                "limit_pct": ticker_limit_pct,
                            }
                        )

        warnings: list[str] = []
        review_holdings = [row["ticker"] for row in holding_rows + urgent_rows if row["review_required"]]
        if review_holdings:
            warnings.append("재검토·취소·만료 상태지만 실제 보유로 다시 확인한 종목: " + ", ".join(sorted(set(review_holdings))))
        if urgent_rows:
            warnings.append(
                "현재 확인 가격이 사용자 방어선 이하인 보유 종목은 평가 노출에는 포함했지만 "
                "방어선 위험금액과 남은 위험예산은 미확정으로 두고 긴급 재검토로 분리했습니다."
            )
        if not complete:
            warnings.append("이번 점검에 반영할 실제 보유와 동시 진입계획을 모두 선택했는지 확인하지 않았습니다.")
        if not confirmed_currency:
            warnings.append("선택 계획과 계좌금액의 실제 통화가 같다는 확인이 필요합니다.")
        if account is None:
            warnings.append("계좌 평가금액이 없어 계좌 대비 비율과 한도 판정을 계산하지 않습니다.")
        if has_entry and has_holding and not combined_requested:
            warnings.append("보유와 신규 진입을 합친 동시 체결 가정을 선택하지 않아 전체 합계 판정을 하지 않습니다.")

        review_required = bool(urgent_rows or review_holdings)
        if urgent_rows:
            decision_code = "STOP_REVIEW_REQUIRED"
        elif limit_breaches:
            decision_code = "OVER_USER_LIMIT"
        elif not complete or not confirmed_currency:
            decision_code = "INCOMPLETE_CONFIRMATION"
        elif has_entry and has_holding and not combined_requested:
            decision_code = "COMBINED_SCENARIO_NOT_CONFIRMED"
        elif review_required:
            decision_code = "REVIEW_REQUIRED"
        elif not has_entry and not has_holding:
            decision_code = "NO_SELECTION"
        elif account is None:
            decision_code = "ACCOUNT_REQUIRED_FOR_DECISION"
        elif risk_limit_pct is None:
            decision_code = "RISK_LIMIT_NOT_SET"
        else:
            decision_code = "WITHIN_USER_LIMITS"

        summary = {
            "version": PORTFOLIO_RISK_VERSION,
            "decision_code": decision_code,
            "source_currency_hint": source_hint,
            "currency_code": code if confirmed_currency else "",
            "currency_confirmed": confirmed_currency,
            "account_size": account,
            "completeness_confirmed": complete,
            "holding": holding_summary,
            "pending_entry": entry_summary,
            "combined_scenario": combined_summary,
            "holding_rows": copy.deepcopy(holding_rows),
            "entry_rows": copy.deepcopy(entry_rows),
            "urgent_rows": copy.deepcopy(urgent_rows),
            "holding_ticker_rows": holding_ticker_rows,
            "pending_entry_ticker_rows": entry_ticker_rows,
            "ticker_rows": ticker_rows,
            "limits": {
                "max_total_risk_pct": risk_limit_pct,
                "max_total_exposure_pct": exposure_limit_pct,
                "max_single_ticker_exposure_pct": ticker_limit_pct,
                "risk_budget": _round(risk_budget),
                "remaining_risk_budget": _round(risk_budget - combined_risk)
                if risk_budget is not None and combined_risk is not None
                else None,
            },
            "limit_breaches": copy.deepcopy(limit_breaches),
            "warnings": warnings,
            "limitations": [
                "STOP_FILL_NOT_GUARANTEED",
                "FEES_TAXES_FX_SLIPPAGE_GAP_EXCLUDED",
                "SAVED_PRICES_NOT_LIVE",
                "SECTOR_ETF_OVERLAP_NOT_MEASURED",
                "NO_ORDER_OR_EXECUTION_STATE",
            ],
        }
        if original != list(plans):
            raise _PortfolioRiskError("INPUT_MUTATED", "위험 계산 중 원본 계획이 변경되었습니다.")
        return {
            "valid": True,
            "reason": "",
            "errors": [],
            "warnings": warnings,
            "inspection": copy.deepcopy(inspection),
            "summary": summary,
        }
    except _PortfolioRiskError as exc:
        return _error(exc.code, exc.message)
