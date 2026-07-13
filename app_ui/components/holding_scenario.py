from __future__ import annotations

from typing import Any, Mapping

import streamlit as st

from services.holding_scenario import calculate_long_holding_scenario
from services.trade_plan_service import build_holding_trade_plan
from .trade_plan_workspace import queue_trade_plan_flash, save_trade_plan_to_session


def _format_money(value: Any, currency_hint: str, *, signed: bool = False) -> str:
    if value is None:
        return "-"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "-"
    prefix = "+" if signed and number > 0 else ""
    if currency_hint == "KRW":
        return f"{prefix}{number:,.0f}원"
    return f"{prefix}{number:,.2f}"


def _format_quantity(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "-"
    if number.is_integer():
        return f"{int(number):,}주"
    return f"{number:,.4f}주"


def _render_scenario_banner(result: Mapping[str, Any]) -> None:
    message = f"**{result.get('scenario_title', '보유 계획 점검')}**  \n{result.get('scenario_summary', '')}"
    tone = result.get("scenario_tone")
    if tone == "positive":
        st.success(message)
    elif tone == "risk":
        st.warning(message)
    else:
        st.info(message)


def render_holding_scenario(
    guide: Mapping[str, Any],
    *,
    key_prefix: str,
    allow_plan_save: bool = False,
) -> None:
    """Render an opt-in, read-only spot-long holding review calculator."""

    st.markdown("#### 보유 포지션 점검")
    enabled = st.toggle(
        "현재 이 종목을 보유 중입니다",
        value=False,
        key=f"trade_plan_sensitive_{key_prefix}_enabled",
        help="현물 매수 보유분의 단순 평가손익과 사용자가 정한 방어 기준까지의 범위를 계산합니다.",
    )
    if not enabled:
        st.caption(
            "보유 중인 경우에만 켜세요. 입력값은 기본적으로 현재 브라우저 세션의 계산에만 사용하고, "
            "보유 방어계획 저장을 직접 누른 경우에만 세션 계획에 복사됩니다. 자동 주문을 만들지 않습니다."
        )
        return

    current_default = float(guide.get("current_price") or 0.0)
    currency_hint = str(guide.get("currency_hint") or "계좌 통화")
    as_of = str(guide.get("as_of") or "").strip()
    price_step = 1.0 if currency_hint == "KRW" else 0.01
    price_format = "%.0f" if currency_hint == "KRW" else "%.2f"
    quantity_format = "%.0f" if currency_hint == "KRW" else "%.4f"

    if guide.get("price_data_available") is False or current_default <= 0:
        st.warning("유효한 분석 기준 가격이 없어 보유 손익을 계산할 수 없습니다. 최신 가격을 확인한 뒤 분석을 다시 실행하세요.")
        return

    st.caption(
        f"분석 기준가 {_format_money(current_default, currency_hint)}"
        + (f" · 기준일 {as_of}" if as_of else " · 기준일 확인 필요")
        + " · 실시간 시세가 아닌 분석 스냅샷"
    )

    average_col, quantity_col, current_col = st.columns(3)
    average_entry = average_col.number_input(
        "실제 보유 평단",
        min_value=0.0,
        value=0.0,
        step=price_step,
        format=price_format,
        key=f"trade_plan_sensitive_{key_prefix}_average_entry",
        help="증권사에 표시된 실제 보유 평균단가를 직접 입력하세요.",
    )
    quantity = quantity_col.number_input(
        "실제 보유 수량",
        min_value=0.0,
        value=0.0,
        step=1.0,
        format=quantity_format,
        key=f"trade_plan_sensitive_{key_prefix}_quantity",
        help="미국주식 소수점 보유도 입력할 수 있습니다.",
    )
    current_price = current_col.number_input(
        "점검 현재가",
        min_value=0.0,
        value=current_default,
        step=price_step,
        format=price_format,
        key=f"trade_plan_sensitive_{key_prefix}_current_price",
        help="분석 종가가 기본값입니다. 실제 점검 시에는 증권사의 최신 가격을 확인해 수정하세요.",
    )

    engine_stop = guide.get("stop_loss")
    stop_col, account_col = st.columns(2)
    user_stop = stop_col.number_input(
        "내 방어 기준 (선택)",
        min_value=0.0,
        value=0.0,
        step=price_step,
        format=price_format,
        key=f"trade_plan_sensitive_{key_prefix}_user_stop",
        help="사용자가 실제로 정한 재점검 가격입니다. 엔진 무효화 가격은 자동 입력하지 않으며, 0이면 미설정으로 계산합니다.",
    )
    account_size = account_col.number_input(
        f"계좌 평가금액 ({currency_hint}, 선택)",
        min_value=0.0,
        value=0.0,
        step=100_000.0 if currency_hint == "KRW" else 100.0,
        key=f"trade_plan_sensitive_{key_prefix}_account_size",
        help="입력하면 현재 포지션 비중과 방어선 가정 손익의 계좌 대비 비율을 함께 계산합니다.",
    )
    if engine_stop is not None:
        st.caption(
            f"분석 엔진 무효화 참고 {_format_money(engine_stop, currency_hint)} · "
            "사용자가 정한 방어 기준이 아니므로 입력칸에 자동 반영하지 않습니다."
        )

    if average_entry <= 0 or quantity <= 0 or current_price <= 0:
        st.info("실제 보유 평단과 수량을 입력하면 방어 시나리오를 계산합니다.")
        return

    result = calculate_long_holding_scenario(
        current_price=current_price,
        average_entry=average_entry,
        quantity=quantity,
        user_stop_price=user_stop if user_stop > 0 else None,
        account_size=account_size if account_size > 0 else None,
        engine_invalidation_price=engine_stop,
        target_1=guide.get("target_1"),
        target_2=guide.get("target_2"),
        judgment=str(guide.get("judgment") or "NEUTRAL"),
        hard_conflict=bool(guide.get("hard_conflict")),
        liquidity_risk=bool(guide.get("liquidity_risk")),
        price_available=bool(guide.get("price_data_available", True)),
        as_of=as_of,
    )
    if not result.get("valid"):
        st.warning(str(result.get("reason") or "보유 시나리오를 계산할 수 없습니다."))
        return

    _render_scenario_banner(result)
    value_col, pnl_col, return_col, weight_col = st.columns(4)
    value_col.metric("현재 평가금액", _format_money(result.get("position_value"), currency_hint))
    pnl_col.metric("단순 평가손익", _format_money(result.get("unrealized_pnl"), currency_hint, signed=True))
    return_col.metric("단순 수익률", f"{float(result.get('unrealized_pnl_pct') or 0):+.2f}%")
    position_pct = result.get("position_pct")
    weight_col.metric("계좌 내 비중", f"{float(position_pct):.2f}%" if position_pct is not None else "계좌금액 미입력")

    if result.get("user_stop_price") is not None:
        stop_price_col, distance_col, giveback_col, stop_pnl_col = st.columns(4)
        stop_price_col.metric("내 방어 기준", _format_money(result.get("user_stop_price"), currency_hint))
        distance_col.metric("방어선까지 거리", f"{float(result.get('distance_to_stop_pct') or 0):+.2f}%")
        giveback_col.metric("방어선까지 반납 가능액", _format_money(result.get("giveback_to_stop"), currency_hint))
        stop_pnl_col.metric("방어선 체결 가정 손익", _format_money(result.get("pnl_at_stop"), currency_hint, signed=True))
        stop_account_pct = result.get("pnl_at_stop_pct_of_account")
        if stop_account_pct is not None:
            st.caption(f"방어선 체결 가정 손익의 계좌 대비 비율: {float(stop_account_pct):+.2f}%")
        st.caption("반납 가능액은 현재 평가금액에서 방어선까지의 가격 차이일 뿐 예상 손실이나 보장 체결액이 아닙니다.")
    else:
        st.info("사용자 방어 기준이 없습니다. 엔진 가격을 자동 손절로 간주하지 말고 본인의 재점검 기준을 따로 기록하세요.")

    target_rows: list[str] = []
    if result.get("target_1") is not None:
        target_rows.append(
            f"1차 목표 {_format_money(result.get('target_1'), currency_hint)} 도달 가정 손익 "
            f"{_format_money(result.get('target_1_pnl'), currency_hint, signed=True)}"
        )
    if result.get("target_2") is not None:
        target_rows.append(
            f"2차 목표 {_format_money(result.get('target_2'), currency_hint)} 도달 가정 손익 "
            f"{_format_money(result.get('target_2_pnl'), currency_hint, signed=True)}"
        )
    if target_rows:
        st.caption(" · ".join(target_rows))

    reasons = list(result.get("scenario_reasons") or [])
    if reasons:
        st.caption("재점검 근거: " + " · ".join(str(item) for item in reasons))
    warnings = list(result.get("warnings") or [])
    if warnings:
        st.warning("추가 확인: " + " · ".join(str(item) for item in warnings))

    st.caption(str(result.get("calculation_note") or ""))
    if allow_plan_save and result.get("user_stop_price") is not None:
        st.warning(
            "보유 방어계획을 저장하면 입력한 평단·수량·점검 가격·사용자 방어 기준이 현재 세션과 평문 JSON 백업에 포함됩니다. "
            "계좌 평가금액은 저장하지 않습니다."
        )
        if st.button(
            "보유 방어계획 저장 (평단·수량 포함)",
            key=f"trade_plan_ui_save_holding__{key_prefix}",
            use_container_width=True,
        ):
            evaluation_source = (
                "ANALYSIS_SNAPSHOT"
                if abs(float(current_price) - float(current_default)) <= max(abs(float(current_default)) * 1e-9, 1e-9)
                else "USER_INPUT"
            )
            plan_result = build_holding_trade_plan(
                guide,
                average_entry=average_entry,
                quantity=quantity,
                evaluation_price=current_price,
                evaluation_price_source=evaluation_source,
                user_stop_price=user_stop,
            )
            saved = save_trade_plan_to_session(plan_result)
            if saved.get("valid") and saved.get("added"):
                queue_trade_plan_flash(
                    "보유 방어계획을 현재 세션의 `내 매매계획`에 저장했습니다.",
                    warnings=list(plan_result.get("warnings") or []),
                )
                st.rerun()
            elif saved.get("valid"):
                st.info(str(saved.get("reason") or "동일한 계획이 이미 저장되어 있습니다."))
            else:
                st.warning(str(saved.get("reason") or plan_result.get("reason") or "보유 방어계획을 저장할 수 없습니다."))
    st.caption(
        "평단 입력은 세무상 조정 취득원가와 다를 수 있습니다. "
        "[FINRA 취득원가 안내](https://www.finra.org/investors/insights/cost-basis-basics) · "
        "[Investor.gov 스톱 주문 안내](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-15)"
    )
    st.caption(f"입력 보유 수량: {_format_quantity(result.get('quantity'))} · 자동 주문/매도 지시 없음")
