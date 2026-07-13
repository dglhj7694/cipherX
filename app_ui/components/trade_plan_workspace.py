from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence

import streamlit as st

from services.beginner_trade_guide import build_beginner_trade_guide
from services.trade_plan_service import (
    MAX_SESSION_PLANS,
    PLAN_STATUS_LABELS,
    PLAN_STATUS_OPTIONS,
    PLAN_TYPE_LABELS,
    add_trade_plan,
    assess_trade_plan,
    decode_trade_plan_bundle,
    delete_trade_plan,
    encode_trade_plan_bundle,
    merge_trade_plans,
    update_trade_plan_status,
)
from .portfolio_risk_workspace import render_portfolio_risk_workspace


TRADE_PLAN_SESSION_KEY = "_trade_plans_v1"
TRADE_PLAN_DELETE_KEY = "_trade_plan_pending_delete_id"
TRADE_PLAN_FLASH_KEY = "trade_plan_ui_flash"
PORTFOLIO_RISK_STATE_PREFIX = "trade_plan_sensitive_portfolio"


def _session_plans() -> list[dict[str, Any]]:
    plans = st.session_state.get(TRADE_PLAN_SESSION_KEY)
    return list(plans) if isinstance(plans, list) else []


def _clear_portfolio_risk_state() -> None:
    """Drop stale account, holding, and confirmation widgets after plan deletion."""

    keys = [
        key
        for key in list(st.session_state.keys())
        if str(key).startswith(PORTFOLIO_RISK_STATE_PREFIX)
    ]
    for key in keys:
        del st.session_state[key]


def save_trade_plan_to_session(plan_result: Mapping[str, Any]) -> dict[str, Any]:
    """Save a validated plan to this Streamlit session only."""

    if not plan_result.get("valid") or not isinstance(plan_result.get("plan"), Mapping):
        return {
            "valid": False,
            "reason": str(plan_result.get("reason") or "매매계획을 저장할 수 없습니다."),
            "added": 0,
            "duplicates": 0,
        }
    result = add_trade_plan(_session_plans(), plan_result["plan"])
    if result.get("valid"):
        st.session_state[TRADE_PLAN_SESSION_KEY] = list(result.get("plans") or [])
    return result


def queue_trade_plan_flash(message: str, *, warnings: Sequence[str] | None = None) -> None:
    """Show one post-rerun plan result in the workspace rendered earlier on the page."""

    st.session_state[TRADE_PLAN_FLASH_KEY] = {
        "message": str(message or "").strip(),
        "warnings": [str(item).strip() for item in list(warnings or []) if str(item).strip()],
    }


def _render_trade_plan_flash() -> None:
    flash = st.session_state.pop(TRADE_PLAN_FLASH_KEY, None)
    if not isinstance(flash, Mapping):
        return
    message = str(flash.get("message") or "").strip()
    warnings = [str(item).strip() for item in list(flash.get("warnings") or []) if str(item).strip()]
    if message:
        st.success(message)
    if warnings:
        st.warning("저장 시 조정 사항: " + " · ".join(warnings))


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


def _freshness_text(code: str) -> tuple[str, str]:
    return {
        "MATCHED": ("현재 분석 일치", "success"),
        "STALE": ("새 분석과 달라 재검토", "warning"),
        "CONTEXT_MISMATCH": ("다른 종목 분석 화면", "info"),
        "UNVERIFIED": ("현재 분석과 미대조", "info"),
        "INVALID": ("계획 검증 실패", "warning"),
    }.get(code, ("현재 분석과 미대조", "info"))


def _render_plan_body(plan: Mapping[str, Any], assessment: Mapping[str, Any]) -> None:
    snapshot = dict(plan.get("analysis_snapshot") or {})
    inputs = dict(plan.get("user_inputs") or {})
    calculation = dict(assessment.get("calculation") or {})
    currency_hint = str(snapshot.get("currency_hint") or "계좌 통화")

    st.caption(
        f"분석 기준일 {snapshot.get('as_of') or '확인 필요'} · "
        f"저장 {plan.get('created_at', '-')} · 버전 {plan.get('plan_version', 1)}"
    )
    st.write(f"저장 당시 판단: {snapshot.get('judgment') or '-'} · {snapshot.get('action_title') or '-'}")
    st.write(f"참고 전략: {snapshot.get('strategy_label') or '전략 없음'} · {snapshot.get('entry_reference') or '진입 기준 확인 필요'}")

    if plan.get("plan_type") == "ENTRY_LONG":
        entry_col, stop_col, target_col, rr_col = st.columns(4)
        entry_col.metric("가정 진입가", _format_price(inputs.get("entry_price"), currency_hint))
        stop_col.metric("가정 손절가", _format_price(inputs.get("stop_price"), currency_hint))
        target_col.metric("가정 1차 목표", _format_price(inputs.get("target_1"), currency_hint))
        rr_col.metric("재검산 손익비", f"{float(calculation.get('rr') or 0):.2f}R")
        quantity = inputs.get("planned_quantity")
        if quantity is not None:
            st.caption(
                f"저장 당시 참고 수량 {int(quantity):,}주 · 거래당 손실 한도 {float(inputs.get('risk_pct') or 0):.2f}% · "
                f"종목당 최대 비중 {float(inputs.get('max_allocation_pct') or 0):.2f}%"
            )
            st.warning("계좌금액은 저장되지 않았습니다. 실제 주문 전 현재 계좌금액으로 수량을 다시 계산하세요.")
        else:
            st.caption("계획 수량과 계좌 평가금액은 저장하지 않았습니다. 실제 주문 전 수량을 다시 계산하세요.")
        if inputs.get("target_2") is not None:
            st.caption(f"가정 2차 목표 {_format_price(inputs.get('target_2'), currency_hint)}")
    else:
        value_col, pnl_col, return_col, stop_col = st.columns(4)
        value_col.metric("저장 시 평가금액", _format_money(calculation.get("position_value"), currency_hint))
        pnl_col.metric("저장 시 단순 손익", _format_money(calculation.get("unrealized_pnl"), currency_hint, signed=True))
        return_col.metric("저장 시 단순 수익률", f"{float(calculation.get('unrealized_pnl_pct') or 0):+.2f}%")
        stop_col.metric("내 방어 기준", _format_price(inputs.get("user_stop_price"), currency_hint))
        st.caption(
            f"평단 {_format_price(inputs.get('average_entry'), currency_hint)} · 보유 수량 {float(inputs.get('quantity') or 0):,.4f}주 · "
            f"점검 가격 {_format_price(inputs.get('evaluation_price'), currency_hint)}"
        )
        target_text = []
        if calculation.get("target_1") is not None:
            target_text.append(f"엔진 1차 목표 {_format_price(calculation.get('target_1'), currency_hint)}")
        if calculation.get("target_2") is not None:
            target_text.append(f"엔진 2차 목표 {_format_price(calculation.get('target_2'), currency_hint)}")
        if target_text:
            st.caption("저장 당시 참고값 · " + " · ".join(target_text))

    risk_flags = list(snapshot.get("risk_flags") or [])
    if risk_flags:
        st.warning("저장 당시 주의 신호: " + " · ".join(str(item) for item in risk_flags))
    if plan.get("note"):
        st.write("메모:", str(plan.get("note")))
    st.caption("계좌 평가금액은 저장하지 않았습니다. 주문 전송·체결 보장·수수료·세금·환율·슬리피지 반영 기능이 아닙니다.")


def _render_plan_controls(
    plan: Mapping[str, Any],
    *,
    key_prefix: str,
    on_select_ticker: Callable[[str], None] | None,
) -> None:
    plan_id = str(plan.get("plan_id") or "")
    plan_type = str(plan.get("plan_type") or "")
    options = list(PLAN_STATUS_OPTIONS.get(plan_type, ()))
    current_status = str(plan.get("status") or "")
    status_index = options.index(current_status) if current_status in options else 0
    status_col, save_col, analyze_col = st.columns([2, 1, 1])
    selected_status = status_col.selectbox(
        "수동 상태",
        options,
        index=status_index,
        format_func=lambda value: PLAN_STATUS_LABELS.get(value, value),
        key=f"{key_prefix}_status_{plan_id}",
        help="브로커 체결 상태가 아니라 사용자가 직접 관리하는 참고 상태입니다.",
    )
    if save_col.button("상태 저장", key=f"{key_prefix}_status_save_{plan_id}", width="stretch"):
        result = update_trade_plan_status(_session_plans(), plan_id, selected_status)
        if result.get("valid"):
            st.session_state[TRADE_PLAN_SESSION_KEY] = list(result.get("plans") or [])
            _clear_portfolio_risk_state()
            st.toast("계획 상태를 현재 세션에 반영했습니다.", icon="✅")
            st.rerun()
        else:
            st.warning(str(result.get("reason") or "계획 상태를 변경할 수 없습니다."))
    if on_select_ticker is not None and analyze_col.button(
        "다시 분석", key=f"{key_prefix}_reanalyze_{plan_id}", width="stretch"
    ):
        on_select_ticker(str(plan.get("analysis_snapshot", {}).get("ticker") or ""))

    pending = st.session_state.get(TRADE_PLAN_DELETE_KEY)
    if pending == plan_id:
        st.warning("이 계획을 현재 세션에서 삭제할까요? JSON 백업이 없다면 복구할 수 없습니다.")
        confirm_col, cancel_col = st.columns(2)
        if confirm_col.button("삭제 확정", key=f"{key_prefix}_delete_confirm_{plan_id}", type="primary"):
            result = delete_trade_plan(_session_plans(), plan_id)
            if result.get("valid"):
                st.session_state[TRADE_PLAN_SESSION_KEY] = list(result.get("plans") or [])
                st.session_state[TRADE_PLAN_DELETE_KEY] = None
                _clear_portfolio_risk_state()
                st.rerun()
            st.warning(str(result.get("reason") or "계획을 삭제할 수 없습니다."))
        if cancel_col.button("삭제 취소", key=f"{key_prefix}_delete_cancel_{plan_id}"):
            st.session_state[TRADE_PLAN_DELETE_KEY] = None
            st.rerun()
    elif st.button("삭제 요청", key=f"{key_prefix}_delete_request_{plan_id}"):
        st.session_state[TRADE_PLAN_DELETE_KEY] = plan_id
        st.rerun()


def render_trade_plan_workspace(
    *,
    current_meta: Mapping[str, Any] | None = None,
    current_audit: Mapping[str, Any] | None = None,
    on_select_ticker: Callable[[str], None] | None = None,
    key_prefix: str = "trade_plan_ui_workspace",
) -> None:
    """Render the single session-only plan workspace for the analysis screen."""

    plans = _session_plans()
    current_guide = build_beginner_trade_guide(current_meta, audit=current_audit) if current_meta else None
    with st.expander(f"내 매매계획 · {len(plans)}/{MAX_SESSION_PLANS}", expanded=bool(plans)):
        st.caption(
            "계획은 현재 Streamlit 세션에만 보관됩니다. 초기화·세션 종료 시 사라질 수 있으므로 필요한 경우 JSON으로 백업하세요."
        )
        st.warning(
            "JSON은 암호화되지 않은 평문 파일입니다. 보유 방어계획에는 평단·수량이, 선택한 신규 계획에는 계획 수량이 포함될 수 있습니다. "
            "계좌 평가금액·API 키·차트·프롬프트는 저장하지 않습니다."
        )
        _render_trade_plan_flash()

        if plans and st.toggle(
            "계좌 전체 위험예산 점검 사용",
            value=False,
            key=f"{key_prefix}_portfolio_risk_enabled",
            help="실제 보유와 미체결 진입계획을 분리해 현재 계좌 기준으로 다시 계산합니다.",
        ):
            with st.container(border=True):
                render_portfolio_risk_workspace(plans)

        export_result = encode_trade_plan_bundle(plans)
        action_col, import_col = st.columns(2)
        with action_col:
            if plans and export_result.get("valid"):
                st.download_button(
                    "JSON 백업 다운로드",
                    data=export_result["data"],
                    file_name="cipherx_trade_plans.json",
                    mime="application/json",
                    key=f"{key_prefix}_download",
                    on_click="ignore",
                    use_container_width=True,
                )
            elif plans:
                st.warning(str(export_result.get("reason") or "계획 백업 파일을 만들 수 없습니다."))
            else:
                st.info("아직 저장된 계획이 없습니다. 최신 분석의 초보자 가이드에서 계획을 저장할 수 있습니다.")
        with import_col:
            uploaded = st.file_uploader(
                "JSON 백업 가져오기",
                type=["json"],
                accept_multiple_files=False,
                max_upload_size=1,
                key=f"{key_prefix}_upload",
                help="최대 512KiB, 20개 계획까지 원자적으로 검증한 뒤 기존 목록에 추가합니다.",
            )
            if uploaded is not None and st.button(
                "검증 후 추가",
                key=f"{key_prefix}_import_submit",
                use_container_width=True,
            ):
                decoded = decode_trade_plan_bundle(uploaded.getvalue())
                if not decoded.get("valid"):
                    st.warning(str(decoded.get("reason") or "계획 파일을 가져올 수 없습니다."))
                else:
                    merged = merge_trade_plans(plans, decoded.get("plans") or [])
                    if not merged.get("valid"):
                        st.warning(str(merged.get("reason") or "가져온 계획을 합칠 수 없습니다."))
                    else:
                        st.session_state[TRADE_PLAN_SESSION_KEY] = list(merged.get("plans") or [])
                        queue_trade_plan_flash(
                            f"계획 {int(merged.get('added') or 0)}개 추가 · "
                            f"중복 {int(merged.get('duplicates') or 0)}개 건너뜀",
                            warnings=list(decoded.get("warnings") or []),
                        )
                        st.rerun()

        if not plans:
            return

        st.caption("가져온 계획은 현재 분석과 다시 대조할 때까지 `재검토 필요` 상태로 유지됩니다.")
        ordered = sorted(plans, key=lambda item: str(item.get("created_at") or ""), reverse=True)
        for plan in ordered:
            assessment = assess_trade_plan(plan, current_guide=current_guide)
            freshness_label, freshness_tone = _freshness_text(str(assessment.get("freshness") or "UNVERIFIED"))
            title = (
                f"{plan.get('analysis_snapshot', {}).get('ticker', '-')} · "
                f"{PLAN_TYPE_LABELS.get(str(plan.get('plan_type')), str(plan.get('plan_type')))} · "
                f"{PLAN_STATUS_LABELS.get(str(plan.get('status')), str(plan.get('status')))}"
            )
            with st.container(border=True):
                st.markdown(f"##### {title}")
                if freshness_tone == "success":
                    st.success(freshness_label)
                elif freshness_tone == "warning":
                    st.warning(freshness_label)
                else:
                    st.info(freshness_label)
                if not assessment.get("valid"):
                    st.warning(str(assessment.get("reason") or "계획을 검증할 수 없습니다."))
                    continue
                if assessment.get("readiness") == "REVIEW_REQUIRED":
                    if plan.get("plan_type") == "ENTRY_LONG":
                        st.warning(
                            "이 신규 진입 계획은 현재 계좌 기준 재검토가 필요합니다. "
                            "저장 수량이 있다면 다시 계산하세요."
                        )
                    else:
                        scenario_code = str((assessment.get("calculation") or {}).get("scenario_code") or "")
                        detail = (
                            "방어선 도달 또는 위험 신호를 먼저 확인하세요."
                            if scenario_code in {"STOP_REACHED", "DEFEND_REVIEW"}
                            else "현재 분석과 사용자 방어 기준을 다시 확인하세요."
                        )
                        st.warning(f"이 보유 방어계획은 재검토가 필요합니다. {detail}")
                _render_plan_body(plan, assessment)
                _render_plan_controls(plan, key_prefix=key_prefix, on_select_ticker=on_select_ticker)
