from __future__ import annotations

import hashlib
from collections import Counter
from typing import Any, Mapping, Sequence

import streamlit as st

from services.portfolio_risk_service import calculate_portfolio_risk_summary, inspect_portfolio_risk_plans


def _key_token(value: str) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:10]


def _number(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return number if number > 0 else default


def _amount(value: Any, currency_code: str) -> str:
    if value is None:
        return "-"
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return "-"
    return f"{number:,.0f}" if currency_code == "KRW" else f"{number:,.2f}"


def _amount_with_pct(amount: Any, percent: Any, currency_code: str) -> str:
    base = _amount(amount, currency_code)
    return f"{base} ({float(percent):.2f}%)" if percent is not None else f"{base} (계좌금액 미입력)"


def _candidate_label(candidate: Mapping[str, Any]) -> str:
    as_of = str(candidate.get("as_of") or "기준일 확인 필요")
    return (
        f"{candidate.get('ticker', '-')} · {candidate.get('plan_type_label', '-')} · "
        f"{candidate.get('status_label', '-')} · {as_of} · {str(candidate.get('plan_id') or '')[:8]}"
    )


def _render_decision(summary: Mapping[str, Any]) -> None:
    decision = str(summary.get("decision_code") or "")
    messages = {
        "WITHIN_USER_LIMITS": (
            "success",
            "입력한 위험예산 기준 이내입니다. 안전·매수 가능 판정이 아니며 실제 주문 전 가격과 수량을 다시 확인하세요.",
        ),
        "OVER_USER_LIMIT": ("error", "입력한 위험예산 또는 노출 한도를 넘는 시나리오가 있습니다."),
        "STOP_REVIEW_REQUIRED": ("error", "사용자 방어선 이하인 보유 종목이 있습니다. 최신 시세와 주문 상태를 먼저 확인하세요."),
        "INCOMPLETE_CONFIRMATION": ("warning", "통화와 반영 범위를 확인해야 계좌 전체 판정을 표시할 수 있습니다."),
        "COMBINED_SCENARIO_NOT_CONFIRMED": (
            "warning",
            "현재 보유와 미체결 진입계획을 따로 계산했습니다. 동시 체결 가정을 확인해야 전체 합계를 판정합니다.",
        ),
        "REVIEW_REQUIRED": ("warning", "재검토 상태의 보유 계획이 포함되어 현재 보유 여부와 값을 다시 확인해야 합니다."),
        "ACCOUNT_REQUIRED_FOR_DECISION": ("info", "계좌 평가금액을 입력하면 계좌 대비 비율과 한도 판정을 계산합니다."),
        "RISK_LIMIT_NOT_SET": ("info", "본인이 정한 계좌 전체 위험 한도를 입력해야 한도 판정을 표시합니다."),
        "NO_SELECTION": ("info", "이번 점검에 포함할 실제 보유 또는 동시 진입계획을 선택하세요."),
    }
    tone, message = messages.get(decision, ("warning", "계산 결과를 다시 확인하세요."))
    getattr(st, tone)(message)


def _render_summary(summary: Mapping[str, Any]) -> None:
    currency_code = str(summary.get("currency_code") or summary.get("source_currency_hint") or "")
    _render_decision(summary)

    holding = dict(summary.get("holding") or {})
    pending = dict(summary.get("pending_entry") or {})
    st.markdown("##### 실제 보유 위험 · 저장값이 아닌 현재 확인값 기준")
    holding_cols = st.columns(3)
    holding_cols[0].metric(
        "보유 평가금액",
        _amount_with_pct(holding.get("exposure"), holding.get("exposure_pct_of_account"), currency_code),
    )
    holding_cols[1].metric(
        "방어선 미도달분의 평가액 감소",
        (
            f"{_amount(holding.get('quantified_giveback_to_stop'), currency_code)} + 긴급 미산정"
            if holding.get("quantified_count")
            else "긴급 미산정"
        )
        if holding.get("urgent_count")
        else _amount_with_pct(
            holding.get("giveback_to_stop"), holding.get("risk_pct_of_account"), currency_code
        ),
    )
    holding_cols[2].metric(
        "방어선 미도달분의 원금손실 가정",
        (
            f"{_amount(holding.get('quantified_capital_loss_at_stop'), currency_code)} + 긴급 미산정"
            if holding.get("quantified_count")
            else "긴급 미산정"
        )
        if holding.get("urgent_count")
        else _amount(holding.get("capital_loss_at_stop"), currency_code),
    )

    st.markdown("##### 미체결 신규 진입 시나리오 · 현재 계좌로 수량 재계산")
    entry_cols = st.columns(3)
    entry_cols[0].metric(
        "예정 투입금",
        _amount_with_pct(pending.get("exposure"), pending.get("exposure_pct_of_account"), currency_code),
    )
    entry_cols[1].metric(
        "손절가 체결 가정 위험",
        _amount_with_pct(pending.get("risk_at_stop"), pending.get("risk_pct_of_account"), currency_code),
    )
    entry_cols[2].metric("재계산 진입계획", f"{int(pending.get('selected_count') or 0)}개")

    combined = summary.get("combined_scenario")
    if isinstance(combined, Mapping):
        st.markdown("##### 모두 체결된 동시 가정")
        combined_cols = st.columns(3)
        combined_cols[0].metric(
            "합산 노출",
            _amount_with_pct(combined.get("exposure"), combined.get("exposure_pct_of_account"), currency_code),
        )
        combined_cols[1].metric(
            "합산 방어선 위험",
            "긴급 보유분 미산정"
            if combined.get("risk_complete") is False
            else _amount_with_pct(
                combined.get("risk_at_stop"), combined.get("risk_pct_of_account"), currency_code
            ),
        )
        remaining = (summary.get("limits") or {}).get("remaining_risk_budget")
        remaining_label = (
            "긴급 보유분 미산정"
            if combined.get("risk_complete") is False
            else (_amount(remaining, currency_code) if remaining is not None else "한도 미설정")
        )
        combined_cols[2].metric("남은 위험예산", remaining_label)
        st.caption(str(combined.get("scenario_label") or ""))

    urgent_rows = list(summary.get("urgent_rows") or [])
    if urgent_rows:
        st.error(
            "방어선 도달 확인: "
            + " · ".join(
                f"{row.get('ticker')} 현재 {_amount(row.get('current_price'), currency_code)} / "
                f"방어선 {_amount(row.get('user_stop_price'), currency_code)}"
                for row in urgent_rows
            )
        )

    ticker_rows = list(summary.get("ticker_rows") or [])
    if ticker_rows:
        st.markdown("##### 종목별 시나리오 기여도")
        scope_labels = {
            "HOLDING": "실제 보유",
            "PENDING_ENTRY": "미체결 진입",
            "COMBINED": "모두 체결 동시 가정",
        }
        st.dataframe(
            [
                {
                    "범위": scope_labels.get(str(row.get("scope") or ""), "확인 필요"),
                    "종목": row.get("ticker"),
                    "노출금액": _amount(row.get("exposure"), currency_code),
                    "계좌비중": f"{float(row['exposure_pct_of_account']):.2f}%"
                    if row.get("exposure_pct_of_account") is not None
                    else "-",
                    "방어선 위험": (
                        f"{_amount(row.get('quantified_risk_at_stop'), currency_code)} + 보유 "
                        f"{int(row.get('risk_unquantified_count') or 0)}건 긴급 확인"
                        if row.get("risk_unquantified_count")
                        else _amount(row.get("risk_at_stop"), currency_code)
                    ),
                    "위험비중": f"{float(row['risk_pct_of_account']):.2f}%"
                    if row.get("risk_pct_of_account") is not None
                    else "-",
                }
                for row in ticker_rows
            ],
            width="stretch",
            hide_index=True,
        )

    for breach in list(summary.get("limit_breaches") or []):
        scope = {
            "HOLDING": "실제 보유",
            "PENDING_ENTRY": "미체결 진입",
            "COMBINED": "모두 체결 동시 가정",
        }.get(str(breach.get("scope") or ""), "선택 시나리오")
        label = {
            "TOTAL_RISK": "계좌 전체 위험",
            "TOTAL_EXPOSURE": "총 노출",
            "TICKER_EXPOSURE": f"{breach.get('ticker', '-')} 종목 노출",
        }.get(str(breach.get("code") or ""), "입력 한도")
        st.error(
            f"{scope} · {label}{' (확정 계산분만)' if breach.get('partial') else ''}: "
            f"{float(breach.get('actual_pct') or 0):.2f}% · "
            f"입력 한도 {float(breach.get('limit_pct') or 0):.2f}%"
        )
    for warning in list(summary.get("warnings") or []):
        st.warning(str(warning))

    st.caption(
        "손절가는 보장 체결가가 아니며 수수료·세금·환율·슬리피지·스프레드·갭 변동, "
        "섹터 상관관계와 ETF 내부 중복은 반영하지 않습니다. 계좌금액과 현재 확인값은 계획 JSON에 저장하지 않습니다."
    )


def render_portfolio_risk_workspace(
    plans: Sequence[Mapping[str, Any]],
    *,
    key_prefix: str = "trade_plan_sensitive_portfolio",
) -> None:
    """Render an explicit, session-only portfolio risk scenario calculator."""

    inspection_result = inspect_portfolio_risk_plans(plans)
    st.markdown("#### 계좌 위험예산 점검")
    st.caption(
        "실제 보유와 미체결 진입계획을 자동으로 같은 것으로 간주하지 않습니다. "
        "이번 점검에 반영할 항목과 통화를 직접 확인하세요."
    )
    if not inspection_result.get("valid"):
        st.error(str(inspection_result.get("reason") or "매매계획을 점검할 수 없습니다."))
        return
    inspection = dict(inspection_result.get("inspection") or {})
    candidates = list(inspection.get("candidates") or [])
    currencies = list(inspection.get("currencies") or [])
    if not candidates or not currencies:
        st.info("위험예산을 점검할 저장 계획이 없습니다.")
        return

    source_hint = st.selectbox(
        "저장 계획 통화 그룹",
        currencies,
        key=f"{key_prefix}_source_currency",
        help="서로 다른 그룹은 환율 없이 합산하지 않습니다.",
    )
    token = _key_token(source_hint)
    same_currency = [item for item in candidates if item.get("currency_hint") == source_hint]
    normalized_source_code = str(source_hint).strip().upper()
    default_code = (
        normalized_source_code
        if len(normalized_source_code) == 3 and normalized_source_code.isascii() and normalized_source_code.isalpha()
        else "USD"
    )
    currency_col, confirm_col = st.columns([1, 2])
    currency_code = currency_col.text_input(
        "실제 통화 코드",
        value=default_code,
        max_chars=3,
        key=f"{key_prefix}_{token}_currency_code",
        help="예: USD, KRW. 자동 추정값을 증권사 계좌와 직접 대조하세요.",
    ).strip().upper()
    currency_value_token = _key_token(currency_code)
    currency_confirmed = confirm_col.checkbox(
        f"선택 계획과 계좌금액이 모두 {currency_code or '같은'} 통화임을 확인",
        value=False,
        key=f"{key_prefix}_{token}_currency_confirmed_{currency_value_token}",
    )

    account_col, risk_col, exposure_col, ticker_col = st.columns(4)
    account_size = account_col.number_input(
        f"현재 계좌 평가금액 ({currency_code or '통화 확인'})",
        min_value=0.0,
        value=0.0,
        step=100_000.0 if currency_code == "KRW" else 100.0,
        key=f"{key_prefix}_{token}_account_size",
        help="현금잔고가 아니라 같은 통화의 현재 계좌 평가금액입니다. 계획이나 JSON에는 저장하지 않습니다.",
    )
    max_risk_pct = risk_col.number_input(
        "내 전체 위험 한도 (%)",
        min_value=0.0,
        max_value=100.0,
        value=0.0,
        step=0.1,
        key=f"{key_prefix}_{token}_risk_limit",
        help="0이면 한도 판정을 하지 않습니다. 적정값은 투자기간과 감당 가능한 손실에 따라 직접 정해야 합니다.",
    )
    max_exposure_pct = exposure_col.number_input(
        "내 총 노출 한도 (%)",
        min_value=0.0,
        max_value=100.0,
        value=0.0,
        step=1.0,
        key=f"{key_prefix}_{token}_exposure_limit",
    )
    max_ticker_pct = ticker_col.number_input(
        "내 한 종목 한도 (%)",
        min_value=0.0,
        max_value=100.0,
        value=0.0,
        step=1.0,
        key=f"{key_prefix}_{token}_ticker_limit",
    )
    st.caption(
        "입력 한도는 프로그램 추천값이 아닙니다. 개인별 위험 감수 수준과 투자기간이 다릅니다. "
        "[Investor.gov 자산배분·분산 안내](https://www.investor.gov/additional-resources/general-resources/publications-research/info-sheets/beginners-guide-asset) · "
        "[FINRA 집중위험 안내](https://www.finra.org/investors/insights/concentration-risk)"
    )

    st.markdown("##### 미체결 신규 진입계획 선택")
    selected_entry_ids: list[str] = []
    entry_candidates = [item for item in same_currency if item.get("plan_type") == "ENTRY_LONG"]
    if not entry_candidates:
        st.caption("이 통화 그룹에는 신규 진입계획이 없습니다.")
    for candidate in entry_candidates:
        if not candidate.get("selectable"):
            st.caption(f"제외 · {_candidate_label(candidate)} — {candidate.get('reason')}")
            continue
        selected = st.checkbox(
            "저장 기준일·진입가·손절가를 다시 확인했고 동시에 유효한 진입계획으로 반영 · "
            + _candidate_label(candidate),
            value=False,
            key=f"{key_prefix}_entry_{candidate['plan_id']}",
        )
        if selected:
            selected_entry_ids.append(str(candidate["plan_id"]))

    selected_entry_tickers = [
        candidate["ticker"] for candidate in entry_candidates if candidate["plan_id"] in selected_entry_ids
    ]
    entry_selection_token = _key_token("|".join(sorted(selected_entry_ids)))
    multiple_entry_confirmed: list[str] = []
    for ticker, count in sorted(Counter(selected_entry_tickers).items()):
        if count > 1 and st.checkbox(
            f"{ticker} 복수 진입계획은 대안이 아니라 분할·동시 계획임을 확인",
            value=False,
            key=f"{key_prefix}_entry_multiple_{token}_{ticker}_{entry_selection_token}",
        ):
            multiple_entry_confirmed.append(ticker)

    st.markdown("##### 실제 보유 확인 · 증권사 최신값 재입력")
    holding_confirmations: dict[str, dict[str, Any]] = {}
    selected_holding_ids: list[str] = []
    confirmed_holding_tokens: list[str] = []
    holding_candidates = [item for item in same_currency if item.get("plan_type") == "HOLDING_LONG"]
    if not holding_candidates:
        st.caption("이 통화 그룹에는 보유 방어계획이 없습니다.")
    for candidate in holding_candidates:
        plan_id = str(candidate["plan_id"])
        confirmed = st.checkbox(
            "현재 실제 보유로 반영 · " + _candidate_label(candidate),
            value=False,
            key=f"{key_prefix}_holding_{plan_id}",
        )
        if candidate.get("review_required"):
            st.caption(f"재확인 필요 · {candidate.get('reason')}")
        if not confirmed:
            continue
        selected_holding_ids.append(plan_id)
        with st.container(border=True):
            average_col, quantity_col, price_col, stop_col = st.columns(4)
            average_entry = average_col.number_input(
                f"{candidate['ticker']} 현재 평단",
                min_value=0.0,
                value=_number(candidate.get("stored_average_entry")),
                key=f"{key_prefix}_holding_average_{plan_id}",
            )
            quantity = quantity_col.number_input(
                f"{candidate['ticker']} 현재 수량",
                min_value=0.0,
                value=_number(candidate.get("stored_quantity")),
                step=0.0001,
                format="%.4f",
                key=f"{key_prefix}_holding_quantity_{plan_id}",
            )
            current_price = price_col.number_input(
                f"{candidate['ticker']} 최신 확인 가격",
                min_value=0.0,
                value=_number(candidate.get("stored_current_price")),
                key=f"{key_prefix}_holding_price_{plan_id}",
            )
            user_stop = stop_col.number_input(
                f"{candidate['ticker']} 현재 방어선",
                min_value=0.0,
                value=_number(candidate.get("stored_user_stop_price")),
                key=f"{key_prefix}_holding_stop_{plan_id}",
            )
            st.caption("저장값은 기본 참고값일 뿐 실시간 값이 아닙니다. 증권사 최신 수량·가격과 현재 방어선을 직접 확인하세요.")
            values_token = _key_token(
                "|".join(
                    f"{float(value):.12g}"
                    for value in (average_entry, quantity, current_price, user_stop)
                )
            )
            values_confirmed = st.checkbox(
                "증권사 최신값과 대조했고 위 평단·수량·가격·방어선을 이번 계산에 사용",
                value=False,
                key=f"{key_prefix}_holding_values_confirmed_{plan_id}_{values_token}",
            )
            if values_confirmed:
                holding_confirmations[plan_id] = {
                    "confirmed": True,
                    "average_entry": average_entry,
                    "quantity": quantity,
                    "current_price": current_price,
                    "user_stop_price": user_stop,
                }
                confirmed_holding_tokens.append(f"{plan_id}:{values_token}")
            else:
                st.warning("최신값 대조 확인 전에는 이 보유분을 위험 합계에 넣지 않습니다.")

    if len({item["ticker"] for item in holding_candidates if item["plan_id"] in selected_holding_ids}) < len(
        selected_holding_ids
    ):
        st.warning("동일 종목의 복수 보유계획은 계좌·포지션 구분 정보가 없어 함께 합산할 수 없습니다. 하나만 선택하세요.")

    scope_signature = "|".join(
        [source_hint]
        + [f"E:{plan_id}" for plan_id in sorted(selected_entry_ids)]
        + [f"H:{plan_id}" for plan_id in sorted(selected_holding_ids)]
    )
    scope_token = _key_token(scope_signature)
    confirmed_values_token = _key_token("|".join(sorted(confirmed_holding_tokens)))
    all_selected_holdings_confirmed = len(holding_confirmations) == len(selected_holding_ids)
    both_types = bool(selected_entry_ids and holding_confirmations)
    combined_requested = st.checkbox(
        "선택한 신규 진입이 모두 계획가에 체결된 동시 가정도 계산",
        value=False,
        key=(
            f"{key_prefix}_{token}_combined_{scope_token}_{confirmed_values_token}_"
            f"{currency_value_token}"
        ),
        disabled=not both_types,
    )
    completeness_confirmed = st.checkbox(
        "이번 점검에 반영할 실제 보유와 동시에 유효한 진입계획을 모두 선택했습니다",
        value=False,
        key=f"{key_prefix}_{token}_complete_{scope_token}",
    )
    effective_completeness = completeness_confirmed and all_selected_holdings_confirmed

    result = calculate_portfolio_risk_summary(
        plans,
        source_currency_hint=source_hint,
        currency_code=currency_code,
        currency_confirmed=currency_confirmed,
        account_size=account_size if account_size > 0 else None,
        selected_entry_ids=selected_entry_ids,
        holding_confirmations=holding_confirmations,
        multiple_entry_tickers_confirmed=multiple_entry_confirmed,
        include_combined_scenario=bool(combined_requested),
        completeness_confirmed=effective_completeness,
        max_total_risk_pct=max_risk_pct if max_risk_pct > 0 else None,
        max_total_exposure_pct=max_exposure_pct if max_exposure_pct > 0 else None,
        max_single_ticker_exposure_pct=max_ticker_pct if max_ticker_pct > 0 else None,
    )
    if not result.get("valid"):
        reason = str(result.get("reason") or "계좌 위험예산을 계산할 수 없습니다.")
        if result.get("errors") and result["errors"][0].get("code") in {
            "ACCOUNT_REQUIRED",
            "AMBIGUOUS_ENTRY_SELECTION",
            "AMBIGUOUS_HOLDING_SELECTION",
        }:
            st.warning(reason)
        else:
            st.error(reason)
        return
    _render_summary(dict(result.get("summary") or {}))
