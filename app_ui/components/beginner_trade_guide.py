from __future__ import annotations

from typing import Any, Mapping

import streamlit as st

from services.beginner_trade_guide import build_beginner_trade_guide, calculate_execution_ticket
from services.trade_plan_service import build_entry_trade_plan
from .holding_scenario import render_holding_scenario
from .trade_plan_workspace import queue_trade_plan_flash, save_trade_plan_to_session


_CHECK_ICONS = {
    "pass": "✅",
    "wait": "⏳",
    "risk": "⚠️",
    "info": "ℹ️",
}


def _format_price(value: Any, currency_hint: str) -> str:
    if value is None:
        return "-"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "-"
    if currency_hint == "KRW":
        return f"{number:,.0f}원"
    return f"{number:,.2f}"


def _format_percent(value: Any, *, signed: bool = False) -> str:
    try:
        number = float(value) * 100.0
    except (TypeError, ValueError):
        return "-"
    prefix = "+" if signed and number > 0 else ""
    return f"{prefix}{number:.1f}%"


def _render_action_banner(guide: Mapping[str, Any]) -> None:
    message = f"**지금 할 일: {guide.get('action_title', '관망 우선')}**  \n{guide.get('action_summary', '')}"
    tone = guide.get("action_tone")
    if tone == "positive":
        st.success(message)
    elif tone in {"risk", "caution"}:
        st.warning(message)
    else:
        st.info(message)


def _render_plan_snapshot(guide: Mapping[str, Any]) -> None:
    currency_hint = str(guide.get("currency_hint") or "")
    direction = str(guide.get("direction") or "")
    strategy_exists = guide.get("strategy_label") != "전략 없음"
    if direction == "SHORT":
        stop_text = "현물 가이드 미표시"
        target_text = "현물 가이드 미표시"
    elif not strategy_exists:
        stop_text = "전략 없음"
        target_text = "전략 없음"
    elif not guide.get("levels_visible"):
        stop_text = "진입 후 재계산"
        target_text = "진입 후 재계산"
    else:
        stop_text = _format_price(guide.get("stop_loss"), currency_hint) if guide.get("stop_loss") is not None else "확인 필요"
        targets = [
            _format_price(guide.get("target_1"), currency_hint) if guide.get("target_1") is not None else "",
            _format_price(guide.get("target_2"), currency_hint) if guide.get("target_2") is not None else "",
        ]
        target_text = " / ".join(value for value in targets if value) or "확인 필요"

    strategy_col, entry_col, stop_col, target_col = st.columns(4)
    strategy_col.metric("참고 전략", str(guide.get("strategy_label") or "전략 없음"))
    strategy_col.caption(f"상태: {guide.get('strategy_status_label') or '-'}")
    entry_col.metric("진입 기준", str(guide.get("entry_reference") or "확인 필요"))
    stop_col.metric("손절·무효화", stop_text)
    target_col.metric("1차 / 2차 목표", target_text)

    rr = guide.get("rr")
    if rr is not None:
        qualifier = "조건부 " if guide.get("levels_conditional") else ""
        st.caption(f"{qualifier}1차 목표 손익비: {float(rr):.2f}R · 저장값이 아닌 진입·손절·목표의 방향을 재검산한 값")
    elif guide.get("strategy_label") != "전략 없음":
        st.caption("현재 단계에서는 실행 가능한 손익비를 표시하지 않습니다.")


def _render_checklist(guide: Mapping[str, Any]) -> None:
    st.markdown("#### 매매 전 5가지 확인")
    for item in guide.get("checklist") or []:
        icon = _CHECK_ICONS.get(str(item.get("status") or "info"), "ℹ️")
        st.markdown(f"{icon} **{item.get('label', '-')}** — {item.get('text', '')}")


def _render_audit_snapshot(snapshot: Mapping[str, Any]) -> None:
    st.markdown("#### 과거 동일 판단 점검")
    if not snapshot.get("available") or not snapshot.get("matched"):
        st.info(str(snapshot.get("reason") or "현재 판단과 비교할 과거 표본이 없습니다."))
        st.caption(str(snapshot.get("note") or ""))
        return

    samples = int(snapshot.get("samples") or 0)
    minimum = int(snapshot.get("minimum_samples") or 20)
    horizon = int(snapshot.get("horizon") or 5)
    if not snapshot.get("sufficient_samples"):
        st.warning(f"표본 부족: 과거 동일 판단 {samples}건 · 최소 확인 기준 {minimum}건")
        st.caption(str(snapshot.get("note") or ""))
        return

    sample_col, hit_col, edge_col = st.columns(3)
    sample_col.metric("동일 판단 표본", f"{samples}건")
    hit_col.metric(f"{horizon}봉 방향 적중", _format_percent(snapshot.get("hit_rate")))
    edge_col.metric(f"{horizon}봉 평균 방향수익", _format_percent(snapshot.get("edge"), signed=True))
    st.caption(str(snapshot.get("note") or ""))


def _render_position_calculator(
    guide: Mapping[str, Any],
    key_prefix: str,
    *,
    allow_plan_save: bool,
) -> None:
    if not guide.get("sizing_available"):
        st.caption(str(guide.get("sizing_block_reason") or ""))
        return

    currency_hint = str(guide.get("currency_hint") or "계좌 통화")
    entry_default = float(guide.get("entry_price") or 0.0)
    stop_default = float(guide.get("stop_loss") or 0.0)
    target_default = float(guide.get("target_1") or 0.0)
    account_default = 10_000_000.0 if currency_hint == "KRW" else 10_000.0
    price_step = 1.0 if currency_hint == "KRW" else 0.01
    price_format = "%.0f" if currency_hint == "KRW" else "%.2f"

    with st.expander("주문 전 가정 티켓", expanded=True):
        st.caption(
            "기본 손실 한도 1%, 종목당 최대 20%는 계산 예시일 뿐 권고 비중이 아닙니다. "
            "아래 진입가·손절가·1차 목표를 한 묶음의 what-if 시나리오로 검증하고 손익비와 수량을 함께 다시 계산합니다."
        )
        account_col, risk_col, allocation_col = st.columns(3)
        account_size = account_col.number_input(
            f"계좌 평가금액 ({currency_hint})",
            min_value=0.0,
            value=account_default,
            step=max(account_default * 0.01, 1.0),
            key=f"trade_plan_sensitive_{key_prefix}_account_size",
            help="진입가와 같은 통화 기준으로 입력하세요.",
        )
        risk_pct = risk_col.number_input(
            "거래당 손실 한도 (%)",
            min_value=0.0,
            max_value=100.0,
            value=1.0,
            step=0.1,
            key=f"trade_plan_sensitive_{key_prefix}_risk_pct",
        )
        max_allocation_pct = allocation_col.number_input(
            "종목당 최대 사용 비중 (%)",
            min_value=0.0,
            max_value=100.0,
            value=20.0,
            step=1.0,
            key=f"trade_plan_sensitive_{key_prefix}_max_allocation_pct",
        )

        entry_col, stop_col, target_col = st.columns(3)
        entry_price = entry_col.number_input(
            "가정 진입가",
            min_value=0.0,
            value=entry_default,
            step=price_step,
            format=price_format,
            key=f"trade_plan_sensitive_{key_prefix}_entry_price",
        )
        stop_price = stop_col.number_input(
            "가정 손절가",
            min_value=0.0,
            value=stop_default,
            step=price_step,
            format=price_format,
            key=f"trade_plan_sensitive_{key_prefix}_stop_price",
        )
        target_price = target_col.number_input(
            "가정 1차 목표",
            min_value=0.0,
            value=target_default,
            step=price_step,
            format=price_format,
            key=f"trade_plan_sensitive_{key_prefix}_target_price",
        )

        result = calculate_execution_ticket(
            entry_price=entry_price,
            stop_price=stop_price,
            target_price=target_price,
            account_size=account_size,
            risk_pct=risk_pct,
            max_allocation_pct=max_allocation_pct,
            direction="LONG",
        )
        if not result.get("valid"):
            st.warning(str(result.get("reason") or "수량을 계산할 수 없습니다."))
            return

        quantity_col, value_col, loss_col, rr_col = st.columns(4)
        quantity_col.metric("계획 수량", f"{int(result['quantity']):,}주")
        value_col.metric("예상 투입금", _format_price(result.get("position_value"), currency_hint))
        loss_col.metric("계획상 최대손실", _format_price(result.get("estimated_loss"), currency_hint))
        rr_col.metric("가정 손익비", f"{float(result.get('rr') or 0):.2f}R")
        limit_label = {"risk": "손실 한도", "allocation": "최대 사용 비중", "both": "두 한도"}.get(
            str(result.get("limited_by")),
            "한도",
        )
        st.caption(
            f"계좌 사용 {float(result.get('position_pct') or 0):.2f}% · 제한 기준: {limit_label} · {result.get('formula')} · "
            "수수료·세금·슬리피지·갭 변동은 반영하지 않은 계획값"
        )
        if allow_plan_save:
            include_quantity = st.toggle(
                "계획 수량도 저장",
                value=False,
                key=f"trade_plan_ui_entry_quantity__{key_prefix}",
                help="끄면 진입·손절·목표·위험률만 저장하고 계획 수량은 저장하지 않습니다.",
            )
            st.caption(
                "계좌 평가금액·예상 투입금·계획 손실금액은 저장하지 않습니다. "
                "수량 포함을 켜면 계획 수량만 세션과 JSON 백업에 포함됩니다."
            )
            if st.button(
                "검증된 신규 진입 계획 저장",
                key=f"trade_plan_ui_save_entry__{key_prefix}",
                type="primary",
                use_container_width=True,
            ):
                plan_result = build_entry_trade_plan(
                    guide,
                    entry_price=entry_price,
                    stop_price=stop_price,
                    target_1=target_price,
                    target_2=guide.get("target_2"),
                    risk_pct=risk_pct,
                    max_allocation_pct=max_allocation_pct,
                    planned_quantity=result.get("quantity"),
                    include_quantity=include_quantity,
                    account_size=account_size if include_quantity else None,
                )
                saved = save_trade_plan_to_session(plan_result)
                if saved.get("valid") and saved.get("added"):
                    queue_trade_plan_flash(
                        "신규 진입 계획을 현재 세션의 `내 매매계획`에 저장했습니다.",
                        warnings=list(plan_result.get("warnings") or []),
                    )
                    st.rerun()
                elif saved.get("valid"):
                    st.info(str(saved.get("reason") or "동일한 계획이 이미 저장되어 있습니다."))
                else:
                    st.warning(str(saved.get("reason") or plan_result.get("reason") or "계획을 저장할 수 없습니다."))


def render_beginner_trade_guide(
    meta: Mapping[str, Any] | None,
    audit: Mapping[str, Any] | None = None,
    key_prefix: str = "beginner_trade_guide",
    *,
    allow_plan_save: bool = False,
) -> None:
    guide = build_beginner_trade_guide(meta, audit=audit)
    st.markdown("### 초보자용 매매 참고")
    st.caption("예측보다 진입 조건·손실 한도·반대 근거를 먼저 확인하는 체크리스트입니다.")
    if not guide.get("available"):
        st.info("분석 결과가 없어 매매 참고 가이드를 만들 수 없습니다.")
        return

    _render_action_banner(guide)
    _render_plan_snapshot(guide)
    render_holding_scenario(
        guide,
        key_prefix=f"{key_prefix}_holding",
        allow_plan_save=allow_plan_save,
    )
    _render_checklist(guide)

    risk_flags = list(guide.get("risk_flags") or [])
    if risk_flags:
        st.warning("주의 신호: " + " · ".join(str(item) for item in risk_flags))
    if guide.get("invalidation_text") and guide.get("levels_visible"):
        st.caption(f"시나리오 무효 조건: {guide['invalidation_text']}")

    _render_audit_snapshot(dict(guide.get("audit_snapshot") or {}))
    _render_position_calculator(guide, key_prefix=key_prefix, allow_plan_save=allow_plan_save)

    st.warning(
        "손절 기준가는 보장 체결가가 아닙니다. 급변·갭·거래량 부족 시 실제 체결가는 크게 달라질 수 있습니다. "
        "[FINRA의 스톱 주문 유의사항](https://www.finra.org/investors/insights/stop-orders-factors-consider-during-volatile-markets)"
    )
    st.caption(
        "계좌 목적·투자 기간·감당 가능한 손실은 사람마다 다르며 분산투자도 함께 고려해야 합니다. "
        "[Investor.gov 위험 감수 수준](https://www.investor.gov/introduction-investing/investing-basics/save-and-invest/gauge-your-risk-tolerance) · "
        "[자산배분과 분산](https://www.investor.gov/introduction-investing/getting-started/asset-allocation)"
    )
    st.caption("교육·정보 제공용이며 투자 권유나 수익 보장이 아닙니다. 실제 주문 전 가격·수수료·세금·호가 단위를 직접 확인하세요.")

    with st.expander("초보 용어 짧게 보기"):
        st.markdown(
            "- **진입 기준**: 전략을 검토하기 시작하는 가격 또는 확인 조건\n"
            "- **손절·무효화**: 처음 세운 시나리오가 틀렸다고 판단할 기준\n"
            "- **목표가**: 수익을 나눠 실현할 후보 가격이며 도달을 보장하지 않음\n"
            "- **1R**: 진입가와 손절가 사이의 계획상 손실폭\n"
            "- **방향 적중**: 과거 동일 판단 뒤 가격이 예상 방향으로 움직인 비율"
        )
