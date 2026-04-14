# ══════════════════════════════════════════════════════════════
#  SIGN — PART 1/4
#  설정, 레지스트리, 유틸리티, 기술지표
# ══════════════════════════════════════════════════════════════

import streamlit as st
import time, math, html
import re
import textwrap
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import yfinance as yf
from app_ui.pages import render_analysis_message, render_market_daily_dashboard
from sectors import SECTOR_GROUPS
from bootstrap import build_default_session_state, ensure_session_defaults as _ensure_session_defaults, reset_session_state as _reset_session_state
from chart import load_chart_figure, serialize_chart_figure
from config import GEMINI_API_KEY, GEMINI_API_KEY_FROM_SECRETS, COMBINED_SCAN_REGISTRY, CTX_KOR, JT
from domain import AnalysisRequest
from infrastructure.etf import FunctionHoldingsProvider, HoldingsProviderRegistry
from utils import _valid_fmt, _sf, resolve_analysis_ticker, _compute_cached
from ai_agent import build_prompt_text, build_ai_prompt, parse_ai_signal_assisted_response
from localization import (
    localize_action_label,
    localize_combo,
    localize_context_label,
    localize_judgment_label,
    localize_signal,
)
from scanner_csv import (
    CORE_SIGNAL_GROUP as SCANNER_CORE_SIGNAL_CFG,
    build_detected_signal_payload,
    scanner_csv_dictionary_to_csv_bytes,
    scanner_csv_field_specs,
    scanner_csv_help_lines,
    scanner_rows_to_csv_bytes,
)
from services.ai_signal_service import (
    build_ai_client,
    generate_ai_signal_assisted,
    mask_secret as _service_mask_secret,
    resolve_ai_key,
)
from workflows import AnalysisWorkflow
from strategy import build_strategy_payload
from branding import (
    BRAND_NAME,
    BRAND_PAGE_ICON,
    BRAND_PAGE_TITLE,
    BRAND_REPORT_SLUG,
    INITIAL_MESSAGE_CONTENT,
    build_brand_board,
)
from theme import build_app_theme_css
st.set_page_config(page_title=BRAND_PAGE_TITLE, page_icon=BRAND_PAGE_ICON, layout="wide", initial_sidebar_state="expanded")

# ━━━ CSS ━━━
st.markdown(build_app_theme_css(), unsafe_allow_html=True)

INITIAL_MESSAGE = {
    "role": "assistant",
    "type": "text",
    "content": INITIAL_MESSAGE_CONTENT,
}

_ANALYSIS_WORKFLOW = AnalysisWorkflow()

_SCAN_SYMBOL_PATTERN = re.compile(r"\b[A-Z]{1,6}(?:[.-][A-Z0-9]{1,4})?\b")
_ETF_UNIVERSE_PRESETS = [
    {"key": "IVES", "label": "IVES", "symbol": "IVES"},
    {"key": "FFTY", "label": "FFTY", "symbol": "FFTY"},
    {"key": "QMOM", "label": "QMOM", "symbol": "QMOM"},
    {"key": "ARKK", "label": "ARKK", "symbol": "ARKK"},
    {"key": "ARKQ", "label": "ARKQ", "symbol": "ARKQ"},
    {"key": "ARKW", "label": "ARKW", "symbol": "ARKW"},
    {"key": "ARKG", "label": "ARKG", "symbol": "ARKG"},
    {"key": "ARKF", "label": "ARKF", "symbol": "ARKF"},
    {"key": "NASDAQ100", "label": "나스닥100", "symbol": "QQQ"},
    {"key": "SP500", "label": "S&P500", "symbol": "SPY"},
    {"key": "IGV", "label": "IGV", "symbol": "IGV"},
    {"key": "SKYY", "label": "SKYY", "symbol": "SKYY"},
    {"key": "WCBR", "label": "WCBR", "symbol": "WCBR"},
]
_ETF_UNIVERSE_PRESET_MAP = {item["key"]: item for item in _ETF_UNIVERSE_PRESETS}
MODE_MARKET_DAILY = "오늘 미국장"
MODE_ANALYSIS = "분석"
MODE_SCANNER = "스캐너"
_APP_MODE_OPTIONS = [MODE_MARKET_DAILY, MODE_ANALYSIS, MODE_SCANNER]
_QUICK_ANALYSIS_TICKERS = ["NVDA", "TSLA", "AAPL", "GOOGL", "AMZN", "META", "MSFT", "PLTR", "HIMS", "SNDK", "LITE", "COHR", "IREN", "ORCL", "RKLB", "ASTS"]
CHAT_INPUT_PLACEHOLDER = "티커 입력: AAPL / 005930"
SCAN_FILTER_PRESETS = ["전체", "최근 추세전환", "최근 강세 발굴", "거래량 동반 강세"]
WATCH_BUY_PLUS = {"WATCH_BUY", "BUY", "STRONG_BUY"}

SCANNER_TRANSITION_CFG = {
    'UTBot_Buy': {'label': 'UTBot 전환▲', 'icon': '🟢', 'dir': 'buy'},
    'UTBot_Sell': {'label': 'UTBot 전환▼', 'icon': '🔴', 'dir': 'sell'},
    'Hull_Turn_Bull': {'label': 'HULL 전환▲', 'icon': '🟢', 'dir': 'buy'},
    'Hull_Turn_Bear': {'label': 'HULL 전환▼', 'icon': '🔴', 'dir': 'sell'},
}

_SESSION_SURROGATE_RE = re.compile(r"[\ud800-\udfff]")
_SESSION_UNSAFE_CODEPOINTS = re.compile(
    "["
    "\u0000-\u0008"
    "\u000b\u000c"
    "\u000e-\u001f"
    "\u007f"
    "\u0085"
    "\u2028\u2029"
    "\ufeff"
    "\ufffd"
    "\ufffe\uffff"
    "]"
)


def _sanitize_session_text(value):
    if not isinstance(value, str) or not value:
        return value
    value = _SESSION_SURROGATE_RE.sub("", value)
    value = _SESSION_UNSAFE_CODEPOINTS.sub("", value)
    return value


def _sanitize_session_payload(value):
    if isinstance(value, str):
        return _sanitize_session_text(value)
    if isinstance(value, list):
        return [_sanitize_session_payload(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_session_payload(item) for item in value]
    if isinstance(value, dict):
        return {
            _sanitize_session_text(key) if isinstance(key, str) else key: _sanitize_session_payload(item)
            for key, item in value.items()
        }
    return value


def _normalize_session_message(message):
    normalized = _sanitize_session_payload(message)
    if normalized.get("type") == "analysis" and normalized.get("fig_json"):
        try:
            normalized["fig_json"] = serialize_chart_figure(load_chart_figure(normalized["fig_json"]))
        except Exception:
            normalized["fig_json"] = None
    return normalized


def _sanitize_session_messages():
    messages = st.session_state.get("messages") or []
    normalized_messages = []
    changed = False
    for message in messages:
        normalized = _normalize_session_message(message if isinstance(message, dict) else {"role": "assistant", "type": "text", "content": str(message)})
        normalized_messages.append(normalized)
        if normalized != message:
            changed = True
    if changed:
        st.session_state.messages = normalized_messages


# ━━━ Constants ━━━
def _render_sidebar_choice_buttons(label, options, state_key, columns=2, default_value=None):
    items = [str(option) for option in options if str(option).strip()]
    if not items:
        return ""

    fallback = str(default_value) if default_value in items else items[0]
    current = str(st.session_state.get(state_key, fallback))
    if current not in items:
        current = fallback
        st.session_state[state_key] = current

    with st.container():
        st.markdown("<div class='sigl-sidebar-choice-anchor'></div>", unsafe_allow_html=True)
        st.markdown(
            f"<div class='sigl-sidebar-control-label'>{html.escape(str(label))}</div>",
            unsafe_allow_html=True,
        )

        for row_start in range(0, len(items), columns):
            row_items = items[row_start:row_start + columns]
            row_columns = st.columns(columns)
            for col_idx, col in enumerate(row_columns):
                with col:
                    if col_idx >= len(row_items):
                        st.markdown("<div class='sigl-sidebar-control-spacer'></div>", unsafe_allow_html=True)
                        continue

                    option = row_items[col_idx]
                    if st.button(
                        option,
                        key=f"{state_key}_choice_{row_start + col_idx}",
                        use_container_width=True,
                        type="primary" if option == current else "secondary",
                    ):
                        if option != current:
                            st.session_state[state_key] = option
                            st.rerun()

    return str(st.session_state.get(state_key, current))


def _active_gemini_api_key():
    key_state = resolve_ai_key(
        st.session_state.get("runtime_gemini_api_key"),
        GEMINI_API_KEY,
        GEMINI_API_KEY_FROM_SECRETS,
    )
    return key_state.active_key


def _mask_secret(value):
    return _service_mask_secret(value)


def get_gemini_model(api_key):
    return build_ai_client(api_key)


def _generate_ai_signal_assisted(ticker, prompt, engine_judgment=""):
    return generate_ai_signal_assisted(
        runtime_key=st.session_state.get("runtime_gemini_api_key"),
        configured_key=GEMINI_API_KEY,
        configured_from_secrets=GEMINI_API_KEY_FROM_SECRETS,
        prompt=prompt,
        engine_judgment=engine_judgment,
        parser=parse_ai_signal_assisted_response,
    )

def analyze(ticker, chart_days=252, refresh=False):
    try:
        response = _ANALYSIS_WORKFLOW.run(
            AnalysisRequest(ticker=ticker, chart_days=chart_days, refresh=refresh),
            prompt_builder=build_prompt_text,
        )
        meta = response.meta.to_dict() if response.meta else None
        return response.chart_json, None, response.prompt_text, meta, response.audit
    except Exception as e:
        import traceback
        print(f"[ERR]{ticker}:\n{traceback.format_exc()}")
        return None, None, f"분석 실패: {e}", None, None


def _initial_messages():
    return [dict(INITIAL_MESSAGE)]


def _session_defaults():
    return build_default_session_state(_initial_messages(), MODE_MARKET_DAILY)


# ━━━ Session + Main ━━━
def init_session():
    _ensure_session_defaults(_session_defaults())


def reset_session():
    _reset_session_state(_session_defaults())

init_session()

def _scan_tickers():
    return [str(r.get('ticker', '')).strip().upper() for r in st.session_state.get('scan_results', []) if str(r.get('ticker', '')).strip()]

def _set_scan_focus(ticker=None, idx=None):
    tickers = _scan_tickers()
    if not tickers:
        st.session_state['scan_focus_idx'] = None
        st.session_state['scan_focus_ticker'] = None
        return None
    if idx is None and ticker:
        try:
            idx = tickers.index(str(ticker).strip().upper())
        except ValueError:
            idx = None
    if idx is None or idx < 0 or idx >= len(tickers):
        return None
    st.session_state['scan_focus_idx'] = idx
    st.session_state['scan_focus_ticker'] = tickers[idx]
    return idx

def _get_scan_focus_context(current_ticker=None):
    results = st.session_state.get('scan_results', [])
    tickers = _scan_tickers()
    if not results or not tickers:
        return None
    current = str(current_ticker or st.session_state.get('last_ticker') or '').strip().upper()
    idx = st.session_state.get('scan_focus_idx')
    if current:
        if idx is None or idx >= len(tickers) or tickers[idx] != current:
            idx = _set_scan_focus(current)
    elif idx is None:
        return None
    if idx is None:
        return None
    return {
        'idx': idx,
        'total': len(results),
        'source': st.session_state.get('scan_source') or 'scan',
        'row': results[idx],
        'results': results,
    }

def _queue_scan_navigation(idx):
    ctx = _get_scan_focus_context()
    if not ctx:
        return
    idx = max(0, min(int(idx), ctx['total'] - 1))
    ticker = ctx['results'][idx]['ticker']
    _set_scan_focus(ticker, idx)
    st.session_state['scan_nav_select_idx'] = idx
    _queue_analysis_target(ticker)


def _queue_analysis_target(ticker):
    ticker = str(ticker or "").strip().upper()
    if not ticker:
        return
    st.session_state['_mode'] = MODE_ANALYSIS
    st.session_state['_auto'] = ticker
    st.session_state['quick'] = None
    st.rerun()


def _render_quick_analysis_grid(key_prefix="quick"):
    for start in range(0, len(_QUICK_ANALYSIS_TICKERS), 2):
        cols = st.columns(2)
        for idx, ticker in enumerate(_QUICK_ANALYSIS_TICKERS[start:start + 2]):
            with cols[idx]:
                if st.button(ticker, use_container_width=True, key=f"{key_prefix}_{ticker}"):
                    _queue_analysis_target(ticker)

def _build_scan_nav_labels(results):
    return [f"{i + 1}. {r['ticker']} · {r.get('jg', 'N/A')} · ES {r.get('es', 0):+.0f}" for i, r in enumerate(results)]

def _handle_scan_jump():
    ctx = _get_scan_focus_context()
    if not ctx:
        return
    selected_idx = st.session_state.get('scan_nav_select_idx')
    if selected_idx is None:
        return
    if int(selected_idx) != ctx['idx']:
        _queue_scan_navigation(int(selected_idx))

def _render_analysis_sidebar_nav():
    ctx = _get_scan_focus_context()
    if not ctx:
        return
    idx = ctx['idx']
    row = ctx['row']
    labels = _build_scan_nav_labels(ctx['results'])
    st.markdown("---")
    st.markdown("#### 스캔 내비게이터")
    st.caption(f"{ctx['source']} 스캔 · {idx + 1}/{ctx['total']} · {row['ticker']}")
    st.caption(f"판단 {row.get('jg', 'N/A')} · ES {row.get('es', 0):+.0f} · 스캔 점수 {row.get('scan_score', 0):+.1f}")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("이전", key="scan_nav_prev_sb", use_container_width=True, disabled=idx <= 0):
            _queue_scan_navigation(idx - 1)
    with c2:
        if st.button("다음", key="scan_nav_next_sb", use_container_width=True, disabled=idx >= ctx['total'] - 1):
            _queue_scan_navigation(idx + 1)

    current_select = st.session_state.get('scan_nav_select_idx')
    if current_select is None or current_select != idx or current_select >= len(labels):
        st.session_state['scan_nav_select_idx'] = idx

    st.selectbox(
        "종목 선택",
        options=list(range(len(labels))),
        format_func=lambda i: labels[i],
        key="scan_nav_select_idx",
        on_change=_handle_scan_jump,
        label_visibility="collapsed",
    )
    if st.button("스캐너로 돌아가기", key="scan_nav_back_sb", use_container_width=True):
        st.session_state['_mode'] = MODE_SCANNER
        st.rerun()

def _show_analysis_toasts(ticker, meta):
    judgment = str(meta.get('judgment', 'NEUTRAL'))
    action = str(meta.get('action_label', '')).strip() or localize_judgment_label(judgment)
    ensemble = float(meta.get('ensemble_score', 0))
    tone = _tone_suffix(judgment or action)
    primary_icon = '🟢' if tone == 'positive' else ('🔴' if tone == 'negative' else '🟡')
    st.toast(f"{ticker} {action} · ES {ensemble:+.1f}", icon=primary_icon)

    warning_parts = []
    veto = str(meta.get('veto_flags', '')).strip()
    if veto:
        warning_parts.append(f"제한 조건 {veto}")
    contrast = str(meta.get('contrast_notes', '')).strip()
    if contrast:
        warning_parts.append(contrast.split(';')[0][:90])
    tier1 = [str(s.get('kor', '')).strip() for s in meta.get('combined_scans', []) if s.get('tier') == 1 and s.get('is_today')]
    if tier1:
        warning_parts.append(f"핵심 콤보 {', '.join(tier1[:2])}")
    top_strategy = (meta.get('strategy_summary') or {}).get('top_strategy') or meta.get('top_strategy')
    if isinstance(top_strategy, dict) and top_strategy.get('label'):
        entry_reference_text = _format_strategy_entry_reference(top_strategy)
        entry_suffix = f" {entry_reference_text}" if entry_reference_text else ""
        status_text = _format_strategy_status(top_strategy.get('status'))
        status_suffix = f" {status_text}" if status_text else ""
        warning_parts.append(f"전략 {top_strategy.get('label')} {float(top_strategy.get('score', 0) or 0):.0f}점{status_suffix}{entry_suffix}")
    if warning_parts:
        st.toast(" · ".join(warning_parts[:2]), icon='⚠️')


def _tone_suffix(raw_text):
    text = str(raw_text or "").upper()
    if 'BUY' in text or '상승' in text or '긍정' in text:
        return 'positive'
    if 'SELL' in text or '하락' in text or '부정' in text:
        return 'negative'
    if 'WATCH' in text or 'HOLD' in text or 'NEUTRAL' in text or '관망' in text or '보유' in text:
        return 'warning'
    return 'muted'


def _format_strategy_status(value):
    return {
        "ACTIVE": "성립",
        "CONFIRMING": "확인 진행",
        "TRIGGER_WAIT": "트리거 대기",
        "READY": "준비",
        "INTEREST": "관심",
        "WATCH": "준비",
        "WEAK_WATCH": "관심",
        "INVALID": "무효",
    }.get(str(value or "").upper(), str(value or ""))


def _format_strategy_entry_price(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    if math.isnan(number):
        return ""
    return f"{number:.2f}"


def _format_strategy_entry_reference(item):
    if not isinstance(item, dict):
        return ""
    text = str(item.get("entry_reference_text") or "").strip()
    if text:
        return text
    price_text = _format_strategy_entry_price(item.get("entry_price"))
    return f"진입가 {price_text}" if price_text else ""


def _sigl_badge(label, tone='muted'):
    safe = html.escape(str(label or '').strip())
    if not safe:
        return ""
    return f"<span class='sigl-badge sigl-badge--{tone}'>{safe}</span>"


def _html_block(markup):
    text = textwrap.dedent(str(markup or "")).strip()
    text = re.sub(r"\n[ \t]+(?=<)", "\n", text)
    return text


def _render_surface_html(inner_html, height):
    del height
    st.markdown(f"<div class='sigl-html-block'>{_html_block(inner_html)}</div>", unsafe_allow_html=True)


def _normalized_selected_sectors(value):
    if not value:
        return []
    if isinstance(value, str):
        value = [value]
    seen = set()
    normalized = []
    for raw in value:
        text = str(raw).strip()
        if not text or text in seen:
            continue
        if text != '🌐 전체' and text not in SECTOR_GROUPS:
            continue
        seen.add(text)
        normalized.append(text)
    if '🌐 전체' in normalized:
        return ['🌐 전체']
    return normalized


def _sector_selection_title(selected_sectors):
    selected_sectors = _normalized_selected_sectors(selected_sectors)
    if not selected_sectors:
        return None
    if selected_sectors == ['🌐 전체']:
        return '🌐 전체'
    if len(selected_sectors) == 1:
        return selected_sectors[0]
    return f"{selected_sectors[0]} 외 {len(selected_sectors) - 1}"


def _sector_selection_tickers(selected_sectors):
    selected_sectors = _normalized_selected_sectors(selected_sectors)
    if not selected_sectors:
        return None
    if selected_sectors == ['🌐 전체']:
        return sorted({str(t).strip().upper() for ts in SECTOR_GROUPS.values() for t in ts if str(t).strip()})
    tickers = []
    for sector_name in selected_sectors:
        tickers.extend(SECTOR_GROUPS.get(sector_name, []))
    return list(dict.fromkeys([str(t).strip().upper() for t in tickers if str(t).strip()])) or None


def _apply_sector_selection(selected_sectors):
    normalized = _normalized_selected_sectors(selected_sectors)
    st.session_state['selected_sectors'] = normalized
    st.session_state['selected_sector'] = _sector_selection_title(normalized)
    st.session_state['scan_tickers_override'] = _sector_selection_tickers(normalized)
    st.session_state['scan_sector_picker'] = normalized


def _toggle_sector_selection(sector_name):
    current = _normalized_selected_sectors(
        st.session_state.get('selected_sectors') or st.session_state.get('selected_sector')
    )
    if sector_name == '🌐 전체':
        next_selection = [] if current == ['🌐 전체'] else ['🌐 전체']
        _apply_sector_selection(next_selection)
        return
    current = [name for name in current if name != '🌐 전체']
    if sector_name in current:
        current = [name for name in current if name != sector_name]
    else:
        current.append(sector_name)
    _apply_sector_selection(current)


def _render_sector_button_picker(sector_names, selected_sectors):
    selected_sectors = _normalized_selected_sectors(selected_sectors)
    options = ['🌐 전체', *sector_names]
    columns_per_row = 3
    for start in range(0, len(options), columns_per_row):
        cols = st.columns(columns_per_row)
        for idx, sector_name in enumerate(options[start:start + columns_per_row]):
            is_selected = (
                selected_sectors == ['🌐 전체']
                if sector_name == '🌐 전체'
                else sector_name in selected_sectors
            )
            with cols[idx]:
                if st.button(
                    sector_name,
                    key=f"sector_pick_{sector_name}",
                    use_container_width=True,
                    type="primary" if is_selected else "secondary",
                ):
                    _toggle_sector_selection(sector_name)
                    st.rerun()


def _parse_ticker_input(raw_text):
    raw = str(raw_text or "").upper()
    return list(dict.fromkeys(_SCAN_SYMBOL_PATTERN.findall(raw)))


def _recent_frame_flag(frame, column, window=5):
    if frame is None or column not in frame.columns:
        return False
    series = frame[column].tail(window)
    try:
        return bool(series.fillna(False).astype(bool).any())
    except Exception:
        return bool(series.any())


def _build_scan_universe_payload(selected_sectors, sector_tickers, etf_items, etf_tickers, manual_tickers):
    sector_unique = list(dict.fromkeys([str(t).strip().upper() for t in (sector_tickers or []) if str(t).strip()]))
    etf_unique = list(dict.fromkeys([str(t).strip().upper() for t in (etf_tickers or []) if str(t).strip()]))
    manual_unique = list(dict.fromkeys([str(t).strip().upper() for t in (manual_tickers or []) if str(t).strip()]))
    combined = list(dict.fromkeys([*sector_unique, *etf_unique, *manual_unique]))
    raw_total = len(sector_unique) + len(etf_unique) + len(manual_unique)
    dedup_removed = max(0, raw_total - len(combined))

    source_labels = []
    if sector_unique:
        source_labels.append("섹터")
    if etf_unique:
        source_labels.append("ETF")
    if manual_unique:
        source_labels.append("직접입력")
    source_label = "+".join(source_labels) if source_labels else "직접"

    return {
        "tickers": combined,
        "source_label": source_label,
        "selected_sectors": _normalized_selected_sectors(selected_sectors),
        "etf_items": list(etf_items or []),
        "sector_count": len(sector_unique),
        "etf_count": len(etf_unique),
        "manual_count": len(manual_unique),
        "raw_total": raw_total,
        "dedup_removed": dedup_removed,
        "final_count": len(combined),
    }


def _render_universe_builder_panel(universe_payload):
    if not universe_payload:
        return
    tickers = list(universe_payload.get("tickers") or [])
    preview_limit = 120
    preview = tickers[:preview_limit]
    hidden_count = max(0, len(tickers) - len(preview))

    source_badges = "".join(
        [
            _sigl_badge(f"섹터 {universe_payload.get('sector_count', 0)}", "accent"),
            _sigl_badge(f"ETF {universe_payload.get('etf_count', 0)}", "warning"),
            _sigl_badge(f"직접입력 {universe_payload.get('manual_count', 0)}", "muted"),
            _sigl_badge(f"중복제거 {universe_payload.get('dedup_removed', 0)}", "muted"),
            _sigl_badge(f"최종 {universe_payload.get('final_count', 0)}", "positive"),
        ]
    )
    sector_chips = "".join(
        _sigl_badge(name, "accent" if name == "🌐 전체" else "muted")
        for name in universe_payload.get("selected_sectors", [])
    ) or _sigl_badge("섹터 선택 없음", "muted")
    etf_chips = "".join(
        _sigl_badge(
            item["resolved"] if item.get("requested", "").upper() == item.get("resolved", "") else f"{item['requested']}→{item['resolved']}",
            "warning" if item.get("requested", "").upper() != item.get("resolved", "") else "muted",
        )
        for item in universe_payload.get("etf_items", [])
    ) or _sigl_badge("ETF 선택 없음", "muted")
    ticker_chips = "".join(
        f"<span class='sigl-code-chip'>{html.escape(str(t))}</span>"
        for t in preview
    ) or "<span class='sigl-empty'>현재 유니버스에 티커가 없습니다.</span>"
    footer = f"미리보기 {len(preview)}개 / 전체 {len(tickers)}개"
    if hidden_count:
        footer += f" (추가 {hidden_count}개 숨김)"
    panel_html = f"""
        <div class="sigl-card sigl-card--accent sigl-scanner-scope">
            <div class="sigl-page-head">
                <div>
                    <p class="sigl-page-head__eyebrow">Universe Builder</p>
                    <p class="sigl-page-head__title">{html.escape(str(universe_payload.get('source_label') or '직접'))}</p>
                    <p class="sigl-page-head__copy">섹터 + ETF + 직접입력을 합집합으로 결합해 스캔 대상을 구성합니다.</p>
                </div>
                <div class="sigl-inline sigl-scanner-scope__meta">{source_badges}</div>
            </div>
            <div class="sigl-chip-row sigl-scanner-scope__sectors">{sector_chips}</div>
            <div class="sigl-chip-row sigl-scanner-scope__sectors">{etf_chips}</div>
            <div class="sigl-code-list sigl-scanner-scope__codes">{ticker_chips}</div>
            <p class="sigl-note"><span class="sigl-summary">{html.escape(footer)}</span></p>
        </div>
    """
    _render_surface_html(panel_html, 0)


def _volume_badges_from_row(row):
    badges = []
    if bool(row.get("volume_abnormal", False)):
        badges.append(("비정상", "negative"))
    if bool(row.get("volume_surge", False)):
        badges.append(("급증", "warning"))
    elif float(row.get("volume_ratio_20", 0) or 0) >= 1.2:
        badges.append(("증가", "positive"))
    if bool(row.get("thin_trade_risk", False)):
        badges.append(("유동성주의", "warning"))
    if not badges:
        badges.append(("보통", "muted"))
    return badges


def _is_watch_buy_plus(row):
    return str(row.get("jg_key", "")).upper() in WATCH_BUY_PLUS


def _has_buy_combo(row):
    return any(str(item.get("dir", "")).lower() == "buy" for item in (row.get("scans") or []))


def _has_active_strategy(row):
    if int(row.get("strategy_active_count", 0) or 0) > 0:
        return True
    return bool(row.get("strategies"))


def _is_bull_discovery_candidate(row):
    return bool(
        _is_watch_buy_plus(row)
        and (bool(row.get("bull_turn_recent", False)) or bool(row.get("uptrend_or_pullback", False)))
        and (_has_active_strategy(row) or _has_buy_combo(row))
        and bool(row.get("volume_bullish", False))
    )


def _apply_scan_filter(results, preset):
    rows = list(results or [])
    if preset == "최근 추세전환":
        return [row for row in rows if bool(row.get("bull_turn_recent", False))]
    if preset == "최근 강세 발굴":
        return [row for row in rows if _is_bull_discovery_candidate(row)]
    if preset == "거래량 동반 강세":
        return [row for row in rows if bool(row.get("volume_bullish", False))]
    return rows


def _build_scan_snapshot(*, universe_payload, filter_preset, results, filtered_results, perf_stats, skip_reasons):
    return {
        "captured_at": datetime.now().isoformat(timespec="seconds"),
        "source": universe_payload.get("source_label", ""),
        "filter_preset": filter_preset,
        "universe": {
            "selected_sectors": list(universe_payload.get("selected_sectors") or []),
            "etf_items": list(universe_payload.get("etf_items") or []),
            "sector_count": int(universe_payload.get("sector_count", 0) or 0),
            "etf_count": int(universe_payload.get("etf_count", 0) or 0),
            "manual_count": int(universe_payload.get("manual_count", 0) or 0),
            "raw_total": int(universe_payload.get("raw_total", 0) or 0),
            "dedup_removed": int(universe_payload.get("dedup_removed", 0) or 0),
            "final_count": int(universe_payload.get("final_count", 0) or 0),
            "tickers": list(universe_payload.get("tickers") or []),
        },
        "result_counts": {
            "raw": len(results or []),
            "filtered": len(filtered_results or []),
            "skipped": len(skip_reasons or []),
        },
        "performance": dict(perf_stats or {}),
        "skips": list(skip_reasons or []),
        "rows": list(results or []),
    }


def _scanner_rows_to_csv_bytes(rows):
    return scanner_rows_to_csv_bytes(rows)


def _scanner_csv_dictionary_to_csv_bytes():
    return scanner_csv_dictionary_to_csv_bytes()


def _scanner_snapshot_to_json_bytes(snapshot):
    import json

    return json.dumps(snapshot or {}, ensure_ascii=False, indent=2).encode("utf-8")


@st.cache_data(ttl=300, max_entries=1200, show_spinner=False)
def _build_scanner_row_cached(ticker, cache_bucket):
    ticker = str(ticker or "").strip().upper()
    if not ticker:
        return {"ok": False, "ticker": "", "skip_reason": "invalid_ticker", "detail": "empty ticker"}

    try:
        frame = _compute_cached(ticker, f"{ticker}_{cache_bucket}")
    except Exception as exc:
        return {"ok": False, "ticker": ticker, "skip_reason": "compute_error", "detail": str(exc)[:220]}

    if frame is None:
        return {"ok": False, "ticker": ticker, "skip_reason": "missing_frame", "detail": "no frame returned"}
    if len(frame) < 50:
        return {"ok": False, "ticker": ticker, "skip_reason": "insufficient_history", "detail": f"bars={len(frame)}"}

    try:
        dc_ = frame.tail(63)
        lt = dc_.iloc[-1]
        prev_close = _sf(dc_.iloc[-2].get('Close', lt.get('Close', 0))) if len(dc_) >= 2 else _sf(lt.get('Close', 0))
        current_close = _sf(lt.get('Close', 0))

        strategy_payload = build_strategy_payload(dc_)
        strategy_summary = strategy_payload.get('summary', {})
        strategy_results = list(strategy_payload.get('visible_results') or [])
        top_strategy = strategy_summary.get('top_strategy')

        detected_payload = build_detected_signal_payload(
            frame=dc_,
            recent_window=5,
            combo_registry=COMBINED_SCAN_REGISTRY,
            transition_cfg=SCANNER_TRANSITION_CFG,
            core_signal_cfg=SCANNER_CORE_SIGNAL_CFG,
            localize_combo_fn=localize_combo,
            localize_signal_fn=localize_signal,
            summary_limit=8,
        )

        acs = [
            {
                "icon": str(item.get("icon", "")),
                "kor": str(item.get("label", "")),
                "dir": str(item.get("dir", "neutral")),
                "tier": int(item.get("tier", 9) or 9),
                "date": str(item.get("date_short", "")),
                "days_ago": int(item.get("days_ago", 99) or 99),
            }
            for item in detected_payload.get("combo_items", [])
        ]
        lsd = detected_payload.get("latest_combo_ts")
        transitions = [
            {
                "icon": str(item.get("icon", "")),
                "label": str(item.get("label", "")),
                "dir": str(item.get("dir", "neutral")),
                "date": str(item.get("date_short", "")),
                "date_iso": str(item.get("date", "")),
                "days_ago": int(item.get("days_ago", 99) or 99),
                "key": str(item.get("key", "")),
            }
            for item in detected_payload.get("transition_items", [])
        ]

        chv = _sf(current_close - prev_close)
        ch = _sf((current_close - prev_close) / prev_close * 100) if prev_close else 0.0
        bt = _sf(lt.get('Buy_Total', 0))
        stt = _sf(lt.get('Sell_Total', 0))
        ba = int(_sf(lt.get('Buy_Agree', 0)))
        sa = int(_sf(lt.get('Sell_Agree', 0)))
        es = _sf(lt.get('Ensemble_Score', 0))
        cf = _sf(lt.get('Judgment_Confidence', 0))
        market_bias = _sf(lt.get('Market_Filter_Bias', 0))
        downgrade_count = _sf(lt.get('Downgrade_Count', 0))
        flip_guard_triggered = bool(lt.get('Flip_Guard_Triggered', False))
        continuation_buy = _sf(lt.get('Continuation_Buy_Score', 0))
        continuation_sell = _sf(lt.get('Continuation_Sell_Score', 0))
        thin_trade_risk = bool(lt.get('Thin_Trade_Risk', False))
        bullish_gap_reversal = bool(lt.get('Bullish_Gap_Reversal', False))
        bearish_gap_failure = bool(lt.get('Bearish_Gap_Failure', False))
        raw_jg = str(lt.get('Trade_Judgment', 'N/A'))

        t1b = sum(1 for item in acs if item['tier'] == 1 and item['dir'] == 'buy')
        t1s = sum(1 for item in acs if item['tier'] == 1 and item['dir'] == 'sell')
        t2b = sum(1 for item in acs if item['tier'] == 2 and item['dir'] == 'buy')
        t2s = sum(1 for item in acs if item['tier'] == 2 and item['dir'] == 'sell')
        scan_score = (
            es
            + (bt - stt) * 0.55
            + (ba - sa) * 2.5
            + t1b * 4.0 - t1s * 4.0
            + t2b * 1.6 - t2s * 1.6
            + cf * 0.04
            + market_bias * 0.55
            + continuation_buy * 0.9
            - continuation_sell * 0.9
        )
        scan_score -= downgrade_count * 2.2
        if thin_trade_risk:
            scan_score -= 4.0
        if bullish_gap_reversal:
            scan_score += 1.8
        if bearish_gap_failure:
            scan_score -= 2.2
        judgment_bias = {
            'STRONG_BUY': 10.0,
            'BUY': 5.0,
            'WATCH_BUY': JT.WATCH_BUY_SCAN_BIAS,
            'WATCH_SELL': JT.WATCH_SELL_SCAN_BIAS,
            'SELL': JT.SELL_SCAN_BIAS,
            'STRONG_SELL': JT.STRONG_SELL_SCAN_BIAS,
        }.get(raw_jg, 0.0)
        scan_score += judgment_bias
        if raw_jg in ('NEUTRAL', 'MIXED'):
            scan_score *= 0.7
        if flip_guard_triggered:
            scan_score *= 0.82

        strength = (
            abs(es)
            + (bt + stt) * 0.35
            + abs(ba - sa) * 1.8
            + (t1b + t1s) * 3.0
            + cf * 0.02
        )

        mbc = sum(1 for item in acs if item['dir'] == 'buy')
        msc = sum(1 for item in acs if item['dir'] == 'sell')
        mnc = sum(1 for item in acs if item['dir'] == 'neutral')
        mcnt = len(acs)
        mimb = mbc - msc
        has_t1 = any(item['tier'] == 1 for item in acs)
        mflag = (mcnt >= 3) or (has_t1 and mcnt >= 2)

        recent_hits = sorted(
            [item for item in acs if item.get('days_ago', 99) <= 3],
            key=lambda item: (item.get('tier', 9), item.get('days_ago', 99)),
        )
        mhits = [{'icon': h['icon'], 'label': h['kor'], 'dir': h['dir'], 'date': h['date']} for h in recent_hits]
        if not mhits:
            fallback_hits = sorted(acs, key=lambda item: (item.get('tier', 9), item.get('days_ago', 99)))[:6]
            mhits = [{'icon': h['icon'], 'label': h['kor'], 'dir': h['dir'], 'date': h['date']} for h in fallback_hits]

        volume_ratio_20 = _sf(lt.get("Volume_Ratio_20", 0))
        volume_ratio_50 = _sf(lt.get("Volume_Ratio_50", 0))
        volume_oscillator = _sf(lt.get("Volume_Oscillator", 0))
        dollar_volume_20 = _sf(lt.get("Dollar_Volume_20", 0))
        volume_surge = bool(lt.get("Volume_Surge", False))
        volume_climax_buy = bool(lt.get("Volume_Climax_Buy", False))
        volume_abnormal = bool(volume_surge or volume_ratio_20 >= 2.0)
        volume_bullish = bool((volume_ratio_20 >= 1.2) and (volume_surge or volume_climax_buy or volume_oscillator > 0))

        system_turn_bull = _recent_frame_flag(dc_, "System_Turn_Bull", 5)
        trend_inflect_bull = _recent_frame_flag(dc_, "Trend_Inflection_Bull", 5)
        ut_turn_bull = _recent_frame_flag(dc_, "UTBot_Buy", 5)
        hull_turn_bull = _recent_frame_flag(dc_, "Hull_Turn_Bull", 5)
        bull_turn_recent = bool(system_turn_bull or trend_inflect_bull or ut_turn_bull or hull_turn_bull)

        ma20 = _sf(lt.get("MA20", 0))
        ma50 = _sf(lt.get("MA50", 0))
        uptrend_ready = bool(current_close > ma20 > ma50) if ma20 and ma50 else False
        pullback_ready = _recent_frame_flag(dc_, "EMA_Pullback_Buy", 5)
        uptrend_or_pullback = bool(uptrend_ready or pullback_ready)
        strategy_active_count = int(strategy_summary.get('active_count', 0) or 0)
        buy_combo_present = any(item['dir'] == 'buy' for item in acs)
        watch_buy_plus = raw_jg in WATCH_BUY_PLUS
        bull_strength_recent = bool(
            watch_buy_plus
            and (bull_turn_recent or uptrend_or_pullback)
            and (strategy_active_count > 0 or buy_combo_present)
            and volume_bullish
        )

        row = {
            'ticker': ticker,
            'price': _sf(current_close),
            'chg_value': chv,
            'chg': ch,
            'scans': sorted(acs, key=lambda item: item['tier']),
            'transitions': transitions,
            'multi_sig': mflag,
            'multi_cnt': mcnt,
            'multi_buy': mbc,
            'multi_sell': msc,
            'multi_neutral': mnc,
            'multi_imb': mimb,
            'multi_hits': mhits,
            'jg_key': raw_jg,
            'jg': localize_judgment_label(raw_jg),
            'cf': cf,
            'es': es,
            'strategies': strategy_results,
            'top_strategy': top_strategy,
            'strategy_conflict_level': str(strategy_summary.get('conflict_level', 'LOW')),
            'strategy_bias': str(strategy_summary.get('long_short_bias', 'BALANCED')),
            'strategy_active_count': strategy_active_count,
            'ctx': localize_context_label(int(_sf(lt.get('Market_Context', 0)))),
            'ba': ba,
            'sa': sa,
            'buy_total': bt,
            'sell_total': stt,
            'scan_score': _sf(scan_score),
            'strength': _sf(strength),
            'latest_sig': lsd.strftime('%Y-%m-%d') if lsd else '9999-99-99',
            'latest_sig_ts': lsd.timestamp() if lsd else 0.0,
            'reason': str(lt.get('Judgment_Reason', '')),
            'action': localize_action_label(str(lt.get('Action_Label', ''))),
            'volume_ratio_20': volume_ratio_20,
            'volume_ratio_50': volume_ratio_50,
            'volume_oscillator': volume_oscillator,
            'dollar_volume_20': dollar_volume_20,
            'volume_surge': volume_surge,
            'volume_abnormal': volume_abnormal,
            'volume_bullish': volume_bullish,
            'thin_trade_risk': thin_trade_risk,
            'bull_turn_recent': bull_turn_recent,
            'uptrend_or_pullback': uptrend_or_pullback,
            'pullback_ready': pullback_ready,
            'bull_strength_recent': bull_strength_recent,
            'utbot_buy_recent': bool(detected_payload.get('utbot_buy_recent', False)),
            'utbot_buy_last_date': str(detected_payload.get('utbot_buy_last_date', '없음')),
            'utbot_sell_recent': bool(detected_payload.get('utbot_sell_recent', False)),
            'utbot_sell_last_date': str(detected_payload.get('utbot_sell_last_date', '없음')),
            'hull_turn_bull_recent': bool(detected_payload.get('hull_turn_bull_recent', False)),
            'hull_turn_bull_last_date': str(detected_payload.get('hull_turn_bull_last_date', '없음')),
            'hull_turn_bear_recent': bool(detected_payload.get('hull_turn_bear_recent', False)),
            'hull_turn_bear_last_date': str(detected_payload.get('hull_turn_bear_last_date', '없음')),
            'detected_combo_count': int(detected_payload.get('detected_combo_count', 0) or 0),
            'detected_combo_summary': str(detected_payload.get('detected_combo_summary', '없음')),
            'detected_transition_count': int(detected_payload.get('detected_transition_count', 0) or 0),
            'detected_transition_summary': str(detected_payload.get('detected_transition_summary', '없음')),
            'detected_core_count': int(detected_payload.get('detected_core_count', 0) or 0),
            'detected_core_summary': str(detected_payload.get('detected_core_summary', '없음')),
            'detected_signal_total_count': int(detected_payload.get('detected_signal_total_count', 0) or 0),
            'detected_signal_latest_date': str(detected_payload.get('detected_signal_latest_date', '없음')),
            'detected_signals': list(detected_payload.get('all_items', [])),
            'watch_buy_plus': watch_buy_plus,
            'buy_combo_present': buy_combo_present,
        }
        return {"ok": True, "ticker": ticker, "row": row, "skip_reason": "", "detail": ""}
    except Exception as exc:
        return {"ok": False, "ticker": ticker, "skip_reason": "row_build_error", "detail": str(exc)[:220]}


def _scan_ticker_worker(ticker, cache_bucket):
    started = time.perf_counter()
    payload = dict(_build_scanner_row_cached(ticker, cache_bucket))
    payload["elapsed_sec"] = _sf(time.perf_counter() - started)
    return payload


def _parse_analysis_ticker_input(raw_text):
    raw = str(raw_text or "").upper()
    tokens = []
    for token in re.split(r"[\s,;/]+", raw):
        cleaned = str(token or "").strip()
        if cleaned and _valid_fmt(cleaned):
            tokens.append(cleaned)
    return list(dict.fromkeys(tokens))


def _short_collection_title(values):
    items = [str(v).strip() for v in (values or []) if str(v).strip()]
    if not items:
        return None
    if len(items) == 1:
        return items[0]
    return f"{items[0]} 외 {len(items) - 1}"


def _normalized_selected_etf_presets(value):
    if not value:
        return []
    if isinstance(value, str):
        value = [value]
    seen = set()
    normalized = []
    for raw in value:
        text = str(raw or "").strip().upper()
        if not text or text in seen or text not in _ETF_UNIVERSE_PRESET_MAP:
            continue
        seen.add(text)
        normalized.append(text)
    return normalized


def _build_etf_payload(symbol, tickers, source_label, as_of=""):
    tickers = list(dict.fromkeys([str(t).strip().upper() for t in tickers if str(t).strip()]))
    if not tickers:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "스캔 가능한 종목이 없습니다.", "as_of": ""}
    basis = f"As of {as_of}" if as_of else "기준일 표기 없음"
    return {
        "symbol": symbol,
        "tickers": tickers,
        "note": f"{source_label} · {basis} · {len(tickers)}종목",
        "error": "",
        "as_of": as_of,
    }


@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def _fetch_wikipedia_index_constituents(symbol):
    symbol = str(symbol or "").strip().upper()
    page_map = {
        "QQQ": ("https://en.wikipedia.org/wiki/Nasdaq-100", "Ticker", "Wikipedia Nasdaq-100 구성종목 기준"),
        "SPY": ("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies", "Symbol", "Wikipedia S&P500 구성종목 기준"),
    }
    if symbol not in page_map:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "지원하지 않는 지수입니다.", "as_of": ""}

    import re
    import requests
    from bs4 import BeautifulSoup

    url, ticker_header, note = page_map[symbol]
    response = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    target_table = None
    for table in soup.select("table.wikitable"):
        headers = [th.get_text(" ", strip=True) for th in table.select("tr th")[:20]]
        if ticker_header in headers:
            target_table = table
            break
    if target_table is None:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "구성종목 표를 찾지 못했습니다.", "as_of": ""}

    tickers = []
    for row in target_table.select("tr")[1:]:
        cells = row.select("th,td")
        if not cells:
            continue
        ticker = str(cells[0].get_text(" ", strip=True) or "").upper().replace(".", "-")
        if _SCAN_SYMBOL_PATTERN.fullmatch(ticker):
            tickers.append(ticker)

    tickers = list(dict.fromkeys(tickers))
    if not tickers:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "구성종목 티커를 찾지 못했습니다.", "as_of": ""}
    lastmod = soup.select_one("#footer-info-lastmod")
    as_of = ""
    if lastmod:
        text = lastmod.get_text(" ", strip=True)
        date_match = re.search(r"edited on\s+(.+?)\s+\(UTC\)", text, flags=re.I)
        as_of = date_match.group(1).strip() if date_match else ""

    return _build_etf_payload(symbol, tickers, f"{note} (Wikipedia 페이지 수정일)", as_of)


@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def _fetch_first_trust_holdings(symbol):
    symbol = str(symbol or "").strip().upper()
    import requests
    from bs4 import BeautifulSoup

    url = f"https://www.ftportfolios.com/Retail/Etf/EtfHoldings.aspx?Ticker={symbol}&Print=Y"
    response = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    import re

    as_of_match = re.search(r'Holdings of the Fund as of\s+([0-9/]+)', response.text, flags=re.I)
    as_of = as_of_match.group(1) if as_of_match else ""

    collecting = False
    tickers = []
    for row in soup.find_all("tr"):
        cells = [cell.get_text(" ", strip=True) for cell in row.find_all("td")]
        if not cells:
            continue
        if cells[:2] == ["Security Name", "Identifier"]:
            collecting = True
            continue
        if not collecting or len(cells) < 7:
            continue
        ticker = str(cells[1] or "").strip().upper().replace(".", "-")
        if _SCAN_SYMBOL_PATTERN.fullmatch(ticker):
            tickers.append(ticker)

    tickers = list(dict.fromkeys(tickers))
    if not tickers:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "First Trust holdings 표를 찾지 못했습니다.", "as_of": as_of}

    return _build_etf_payload(symbol, tickers, "First Trust 공식 holdings", as_of)


@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def _fetch_ishares_holdings(symbol):
    symbol = str(symbol or "").strip().upper()
    import csv
    import io
    import requests
    import re

    page_map = {
        "IGV": "https://www.ishares.com/us/products/239771/ishares-north-american-techsoftware-etf",
    }
    page_url = page_map.get(symbol)
    if not page_url:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "지원하지 않는 iShares ETF입니다.", "as_of": ""}

    page_text = requests.get(page_url, timeout=20, headers={"User-Agent": "Mozilla/5.0"}).text
    match = re.search(
        rf'href="([^"]*fileType=csv[^"]*fileName={symbol}_holdings[^"]*dataType=fund)"',
        page_text,
        flags=re.I,
    )
    if not match:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "iShares CSV 링크를 찾지 못했습니다.", "as_of": ""}

    csv_url = requests.compat.urljoin("https://www.ishares.com", match.group(1))
    raw_csv = requests.get(csv_url, timeout=20, headers={"User-Agent": "Mozilla/5.0"}).content
    csv_text = raw_csv.decode("utf-8-sig", errors="ignore")
    as_of_match = re.search(r'Fund Holdings as of,\s*"?([^"\n]+)"?', csv_text, flags=re.I)
    as_of = as_of_match.group(1).strip() if as_of_match else ""
    reader = csv.DictReader(io.StringIO(csv_text))

    tickers = []
    for row in reader:
        ticker = str(row.get("Ticker") or "").strip().upper().replace(".", "-")
        if _SCAN_SYMBOL_PATTERN.fullmatch(ticker):
            tickers.append(ticker)

    tickers = list(dict.fromkeys(tickers))
    if not tickers:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "iShares holdings CSV에서 티커를 찾지 못했습니다.", "as_of": as_of}

    return _build_etf_payload(symbol, tickers, "iShares 공식 CSV", as_of)


@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def _fetch_alpha_architect_holdings(symbol):
    symbol = str(symbol or "").strip().upper()
    import requests
    from bs4 import BeautifulSoup

    url = f"https://funds.alphaarchitect.com/{symbol.lower()}/"
    response = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    target_table = None
    for table in soup.find_all("table"):
        headers = [th.get_text(" ", strip=True) for th in table.find_all("th")[:12]]
        if {"Ticker", "Name"}.issubset(set(headers)) and "% of Net Assets" in headers:
            target_table = table
            break
    if target_table is None:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "Alpha Architect holdings 표를 찾지 못했습니다.", "as_of": ""}

    import re
    date_hits = re.findall(r"\b\d{2}/\d{2}/\d{4}\b", response.text)
    as_of = date_hits[0] if date_hits else ""

    tickers = []
    for row in target_table.find_all("tr")[1:]:
        cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["th", "td"])]
        if not cells:
            continue
        ticker = str(cells[0] or "").strip().upper().replace(".", "-")
        if _SCAN_SYMBOL_PATTERN.fullmatch(ticker):
            tickers.append(ticker)

    tickers = list(dict.fromkeys(tickers))
    if not tickers:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "Alpha Architect 구성종목을 찾지 못했습니다.", "as_of": as_of}

    return _build_etf_payload(symbol, tickers, "Alpha Architect 공식 holdings", as_of)


@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def _fetch_innovator_holdings(symbol):
    symbol = str(symbol or "").strip().upper()
    import requests
    import re
    from bs4 import BeautifulSoup

    page_map = {
        "FFTY": "https://www.innovatoretfs.com/ffty",
    }
    page_url = page_map.get(symbol)
    if not page_url:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "지원하지 않는 Innovator ETF입니다.", "as_of": ""}

    response = requests.get(page_url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    date_hits = re.findall(r"As of\s+(\d{1,2}/\d{1,2}/\d{4})", response.text)
    as_of = date_hits[0] if date_hits else ""

    tickers = []
    for row in soup.select("tr.hold_row"):
        cells = [cell.get_text(" ", strip=True) for cell in row.find_all("td")]
        if not cells:
            continue
        ticker = str(cells[0] or "").strip().upper().replace(".", "-")
        if _SCAN_SYMBOL_PATTERN.fullmatch(ticker):
            tickers.append(ticker)

    tickers = list(dict.fromkeys(tickers))
    if not tickers:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "Innovator 공식 holdings 표에서 티커를 찾지 못했습니다.", "as_of": as_of}

    return _build_etf_payload(symbol, tickers, "Innovator 공식 holdings", as_of)


@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def _fetch_ark_holdings(symbol):
    symbol = str(symbol or "").strip().upper()
    import csv
    import io
    import json
    import re
    import urllib.parse
    import cloudscraper
    import requests
    from bs4 import BeautifulSoup

    page_text = cloudscraper.create_scraper().get(
        f"https://www.ark-funds.com/funds/{symbol}",
        timeout=20,
    ).text
    api_match = re.search(r"/api/fund/holdings/(\d+)\?fundHoldingData=", page_text)
    if not api_match:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "ARK holdings API를 찾지 못했습니다.", "as_of": ""}

    payload = {
        "Heading": "Top 10 Holdings",
        "PdfLinkText": "Full Holdings PDF",
        "CsvLinkText": "Full Holdings CSV",
        "Link": {"Style": "", "Href": "", "Aria": "", "Target": "", "Text": ""},
    }
    data_json = urllib.parse.quote(json.dumps(payload, separators=(",", ":")))
    api_url = f"https://www.ark-funds.com/api/fund/holdings/{api_match.group(1)}?fundHoldingData={data_json}"
    html = cloudscraper.create_scraper().get(api_url, timeout=20).text
    soup = BeautifulSoup(html, "html.parser")
    csv_link_el = soup.find("a", href=re.compile(r"csv", re.I))
    as_of_match = re.search(r"As of\s+([0-9/]+)", soup.get_text(" ", strip=True), flags=re.I)
    as_of = as_of_match.group(1) if as_of_match else ""
    if not csv_link_el:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "ARK 공식 CSV 링크를 찾지 못했습니다.", "as_of": as_of}

    csv_text = requests.get(csv_link_el["href"], timeout=20, headers={"User-Agent": "Mozilla/5.0"}).text
    reader = csv.DictReader(io.StringIO(csv_text))
    tickers = []
    for row in reader:
        ticker = str(row.get("ticker") or "").strip().upper().replace(".", "-")
        if _SCAN_SYMBOL_PATTERN.fullmatch(ticker):
            tickers.append(ticker)
        if not as_of and row.get("date"):
            as_of = str(row.get("date")).strip()

    tickers = list(dict.fromkeys(tickers))
    if not tickers:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "ARK 공식 CSV에서 티커를 찾지 못했습니다.", "as_of": as_of}

    return _build_etf_payload(symbol, tickers, "ARK 공식 CSV", as_of)


@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def _fetch_wisdomtree_holdings(symbol):
    symbol = str(symbol or "").strip().upper()
    import cloudscraper
    import re
    from bs4 import BeautifulSoup

    page_map = {
        "WCBR": "https://www.wisdomtree.com/investments/etfs/megatrends/wcbr",
    }
    page_url = page_map.get(symbol)
    if not page_url:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "지원하지 않는 WisdomTree ETF입니다.", "as_of": ""}

    scraper = cloudscraper.create_scraper()
    page_text = scraper.get(page_url, timeout=20).text
    modal_match = re.search(r'data-href="([^"]*all-holdings[^"]+)"', page_text)
    if not modal_match:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "WisdomTree holdings 모달 링크를 찾지 못했습니다.", "as_of": ""}

    modal_html = scraper.get(modal_match.group(1), timeout=20).text
    soup = BeautifulSoup(modal_html, "html.parser")
    timestamp = soup.select_one(".timestamp")
    as_of = ""
    if timestamp:
        date_parts = [span.get_text(" ", strip=True) for span in timestamp.select("span")]
        if date_parts:
            as_of = date_parts[-1]

    tickers = []
    for table in soup.select("table.table"):
        title_cell = table.select_one("tr.table-section-head td")
        if not title_cell or "Securities" not in title_cell.get_text(" ", strip=True):
            continue
        for row in table.select("tbody tr"):
            cells = [cell.get_text(" ", strip=True) for cell in row.select("td")]
            if len(cells) < 2:
                continue
            raw_ticker = str(cells[1] or "").strip().upper()
            ticker = raw_ticker.split()[0].replace(".", "-") if raw_ticker else ""
            if _SCAN_SYMBOL_PATTERN.fullmatch(ticker):
                tickers.append(ticker)

    tickers = list(dict.fromkeys(tickers))
    if not tickers:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "WisdomTree holdings 모달에서 티커를 찾지 못했습니다.", "as_of": as_of}

    return _build_etf_payload(symbol, tickers, "WisdomTree 공식 holdings", as_of)


@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def _fetch_wedbush_holdings(symbol):
    symbol = str(symbol or "").strip().upper()
    import csv
    import io
    import re
    import requests

    page_map = {
        "IVES": "https://wedbushfunds.com/funds/ives/",
    }
    page_url = page_map.get(symbol)
    if not page_url:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "지원하지 않는 Wedbush ETF입니다.", "as_of": ""}

    page_text = requests.get(page_url, timeout=20, headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.9"}).text
    date_match = re.search(r"Top Holdings\s+As of\s+([0-9/]+)", page_text, flags=re.I)
    csv_match = re.search(r'href="(https://wedbushfunds\.com/latest-sod-holdings-ives)"', page_text, flags=re.I)
    as_of = date_match.group(1) if date_match else ""
    if not csv_match:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "Wedbush 공식 CSV 링크를 찾지 못했습니다.", "as_of": as_of}

    csv_text = requests.get(csv_match.group(1), timeout=20, headers={"User-Agent": "Mozilla/5.0"}).text
    header_match = re.search(r'Holdings:,\s*"As of ([^"]+)"', csv_text, flags=re.I)
    if header_match:
        as_of = header_match.group(1).strip()

    lines = [line for line in csv_text.splitlines() if line.strip()]
    data_start = 0
    for idx, line in enumerate(lines):
        if line.startswith("Ticker,Name,"):
            data_start = idx
            break
    reader = csv.DictReader(io.StringIO("\n".join(lines[data_start:])))
    tickers = []
    for row in reader:
        ticker = str(row.get("Ticker") or "").strip().upper().replace(".", "-")
        if _SCAN_SYMBOL_PATTERN.fullmatch(ticker):
            tickers.append(ticker)

    tickers = list(dict.fromkeys(tickers))
    if not tickers:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "Wedbush 공식 CSV에서 티커를 찾지 못했습니다.", "as_of": as_of}

    return _build_etf_payload(symbol, tickers, "Wedbush 공식 CSV", as_of)


@st.cache_data(ttl=60 * 60, show_spinner=False)
def _fetch_etf_holdings_preview(symbol):
    symbol = str(symbol or "").strip().upper()
    if not symbol:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "ETF 심볼이 비어 있습니다.", "as_of": ""}
    registry = HoldingsProviderRegistry(
        providers=[
            FunctionHoldingsProvider(
                supported_symbols={"QQQ", "SPY"},
                fetcher=lambda ticker: _safe_fetch_etf_payload(_fetch_wikipedia_index_constituents, ticker, "[ETF-WIKI]"),
            ),
            FunctionHoldingsProvider(
                supported_symbols={"SKYY"},
                fetcher=lambda ticker: _safe_fetch_etf_payload(_fetch_first_trust_holdings, ticker, "[ETF-OFFICIAL]"),
            ),
            FunctionHoldingsProvider(
                supported_symbols={"IGV"},
                fetcher=lambda ticker: _safe_fetch_etf_payload(_fetch_ishares_holdings, ticker, "[ETF-OFFICIAL]"),
            ),
            FunctionHoldingsProvider(
                supported_symbols={"QMOM"},
                fetcher=lambda ticker: _safe_fetch_etf_payload(_fetch_alpha_architect_holdings, ticker, "[ETF-OFFICIAL]"),
            ),
            FunctionHoldingsProvider(
                supported_symbols={"FFTY"},
                fetcher=lambda ticker: _safe_fetch_etf_payload(_fetch_innovator_holdings, ticker, "[ETF-OFFICIAL]"),
            ),
            FunctionHoldingsProvider(
                supported_symbols={"IVES"},
                fetcher=lambda ticker: _safe_fetch_etf_payload(_fetch_wedbush_holdings, ticker, "[ETF-OFFICIAL]"),
            ),
            FunctionHoldingsProvider(
                supported_symbols={"ARKK", "ARKQ", "ARKW", "ARKG", "ARKF"},
                fetcher=lambda ticker: _safe_fetch_etf_payload(_fetch_ark_holdings, ticker, "[ETF-OFFICIAL]"),
            ),
            FunctionHoldingsProvider(
                supported_symbols={"WCBR"},
                fetcher=lambda ticker: _safe_fetch_etf_payload(_fetch_wisdomtree_holdings, ticker, "[ETF-OFFICIAL]"),
            ),
        ],
        fallback=FunctionHoldingsProvider(fetcher=_fetch_yahoo_holdings_payload),
    )
    return registry.fetch(symbol).to_dict()


def _safe_fetch_etf_payload(fetcher, symbol, log_prefix):
    try:
        return fetcher(symbol)
    except Exception as exc:
        print(f"{log_prefix}{symbol}: {exc}")
        return {"symbol": symbol, "tickers": [], "note": "", "error": str(exc), "as_of": ""}


def _fetch_yahoo_holdings_payload(symbol):
    try:
        holdings = yf.Ticker(symbol).funds_data.top_holdings
    except Exception as exc:
        return {"symbol": symbol, "tickers": [], "note": "", "error": str(exc), "as_of": ""}

    if holdings is None or holdings.empty:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "구성종목 정보를 찾지 못했습니다.", "as_of": ""}

    tickers = []
    for raw in holdings.index.tolist():
        ticker = str(raw or "").strip().upper()
        if not ticker or ticker in {symbol, "$USD", "USD", "CASH"}:
            continue
        if _SCAN_SYMBOL_PATTERN.fullmatch(ticker):
            tickers.append(ticker)

    tickers = list(dict.fromkeys(tickers))
    if not tickers:
        return {"symbol": symbol, "tickers": [], "note": "", "error": "스캔 가능한 종목이 없습니다.", "as_of": ""}
    return _build_etf_payload(symbol, tickers, "Yahoo Finance 상위 보유")


def _resolve_etf_universe(etf_items):
    resolved_items, combined, alias_notes, errors, date_notes = [], [], [], [], []
    for item in etf_items or []:
        requested = str(item.get("requested") or "").strip()
        resolved = str(item.get("resolved") or "").strip().upper()
        if not resolved:
            continue
        payload = _fetch_etf_holdings_preview(resolved)
        if payload.get("tickers"):
            resolved_items.append({
                "requested": requested or resolved,
                "resolved": resolved,
                "note": payload.get("note", ""),
                "as_of": payload.get("as_of", ""),
            })
            combined.extend(payload["tickers"])
            if requested and requested.upper() != resolved:
                alias_notes.append(f"{requested} -> {resolved}")
            date_notes.append(f"{resolved} {payload.get('as_of') or '기준일 표기 없음'}")
        else:
            errors.append(f"{requested or resolved}: {payload.get('error') or '불러오기 실패'}")

    combined = list(dict.fromkeys([str(t).strip().upper() for t in combined if str(t).strip()]))
    summary = ""
    if resolved_items and combined:
        summary = ""
    if date_notes:
        summary = f"{summary} 데이터 기준일: {' / '.join(date_notes)}".strip()
    if alias_notes:
        summary = f"{summary} 매핑: {' / '.join(alias_notes)}".strip()

    return {
        "items": resolved_items,
        "tickers": combined,
        "note": summary,
        "errors": errors,
    }


def _apply_etf_selection(selected_keys):
    normalized = _normalized_selected_etf_presets(selected_keys)
    st.session_state['scan_etf_picker'] = normalized
    if not normalized:
        st.session_state['scan_etf_items'] = []
        st.session_state['scan_etf_tickers_override'] = None
        st.session_state['scan_etf_note'] = ''
        st.session_state['scan_etf_errors'] = []
        return

    request_items = [
        {
            "requested": _ETF_UNIVERSE_PRESET_MAP[key]["label"],
            "resolved": _ETF_UNIVERSE_PRESET_MAP[key]["symbol"],
        }
        for key in normalized
    ]
    with st.spinner("ETF 구성종목을 불러오는 중입니다..."):
        etf_payload = _resolve_etf_universe(request_items)
    st.session_state['scan_etf_items'] = etf_payload['items']
    st.session_state['scan_etf_tickers_override'] = etf_payload['tickers'] or None
    st.session_state['scan_etf_note'] = etf_payload['note']
    st.session_state['scan_etf_errors'] = etf_payload['errors']


def _toggle_etf_selection(preset_key):
    current = _normalized_selected_etf_presets(st.session_state.get('scan_etf_picker'))
    if preset_key in current:
        current = [key for key in current if key != preset_key]
    else:
        current.append(preset_key)
    _apply_etf_selection(current)


def _render_etf_button_picker(selected_keys):
    selected_keys = _normalized_selected_etf_presets(selected_keys)
    columns_per_row = 4
    option_keys = [item["key"] for item in _ETF_UNIVERSE_PRESETS]
    for start in range(0, len(option_keys), columns_per_row):
        cols = st.columns(columns_per_row)
        for idx, key in enumerate(option_keys[start:start + columns_per_row]):
            with cols[idx]:
                if st.button(
                    _ETF_UNIVERSE_PRESET_MAP[key]["label"],
                    key=f"etf_pick_{key}",
                    use_container_width=True,
                    type="primary" if key in selected_keys else "secondary",
                ):
                    _toggle_etf_selection(key)
                    st.rerun()


def _render_scanner_summary(results, total_count):
    buy_count = len([r for r in results if 'BUY' in str(r.get('jg_key', ''))])
    sell_count = len([r for r in results if 'SELL' in str(r.get('jg_key', ''))])
    cards = [
        ("매수 후보", str(buy_count), "판단이 BUY 계열인 종목 수", "positive"),
        ("매도 후보", str(sell_count), "판단이 SELL 계열인 종목 수", "negative"),
        ("매치 수", f"{len(results)}/{total_count}", "전체 스캔 대상 대비 현재 결과", "accent"),
    ]
    cards_html = "".join(
        f"""
        <div class="sigl-metric-card sigl-metric-card--summary sigl-metric-card--{tone}">
            <p class="sigl-metric-label">{html.escape(label)}</p>
            <p class="sigl-metric-value">{html.escape(value)}</p>
            <p class="sigl-metric-sub">{html.escape(sub)}</p>
        </div>
        """
        for label, value, sub, tone in cards
    )
    _render_surface_html(f"<div class='sigl-result-summary'>{cards_html}</div>", 0)


def _render_scanner_result_card(rank, row):
    judgment_key = str(row.get('jg_key', ''))
    judgment_label = str(row.get('jg', 'N/A'))
    action_label = str(row.get('action', '')).strip()
    top_strategy = row.get('top_strategy') or {}
    tone = _tone_suffix(judgment_key or action_label)
    tone_class = {
        'positive': 'sigl-card--positive',
        'negative': 'sigl-card--negative',
        'warning': 'sigl-card--warning',
        'muted': '',
    }.get(tone, '')
    transitions = "".join(
        _sigl_badge(f"{t['icon']} {t['label']} {t['date']}", 'positive' if t.get('dir') == 'buy' else 'negative')
        for t in row.get('transitions', [])
    ) or _sigl_badge("UT/HULL 전환 없음", 'muted')
    combo_hits = "".join(
        _sigl_badge(f"{m['icon']} {m['label']} {m['date']}", _tone_suffix(m.get('dir')))
        for m in row.get('multi_hits', [])
    ) or _sigl_badge("최근 다중 시그널 없음", 'muted')
    strategy_hits = "".join(
        _sigl_badge(
            f"전략 {item.get('label')} {float(item.get('score', 0) or 0):.0f}점",
            'positive' if str(item.get('direction', '')).upper() == 'LONG' else 'negative' if str(item.get('direction', '')).upper() == 'SHORT' else 'muted'
        )
        for item in (row.get('strategies') or [])[:3]
    ) or _sigl_badge("활성 전략 없음", 'muted')
    volume_hits = "".join(
        _sigl_badge(
            f"거래량 {label} (R20 {float(row.get('volume_ratio_20', 0) or 0):.2f})",
            tone_name,
        )
        for label, tone_name in _volume_badges_from_row(row)
    )
    trend_hits = "".join(
        [
            _sigl_badge("최근 추세전환", "positive") if bool(row.get("bull_turn_recent", False)) else "",
            _sigl_badge("우상향/눌림", "accent") if bool(row.get("uptrend_or_pullback", False)) else "",
            _sigl_badge("강세 발굴 조건", "positive") if bool(row.get("bull_strength_recent", False)) else "",
        ]
    ) or _sigl_badge("추세 특이사항 없음", "muted")
    top_strategy_text = ""
    if isinstance(top_strategy, dict) and top_strategy.get('label'):
        entry_reference_text = _format_strategy_entry_reference(top_strategy)
        entry_suffix = f" · {html.escape(entry_reference_text)}" if entry_reference_text else ""
        status_text = _format_strategy_status(top_strategy.get('status'))
        status_suffix = f" · {html.escape(status_text)}" if status_text else ""
        top_strategy_text = (
            f"<div class='sigl-note'>"
            f"<span class='sigl-summary'>상위 전략 {html.escape(str(top_strategy.get('label')))} · "
            f"{html.escape(str(top_strategy.get('direction', '')))} · "
            f"{float(top_strategy.get('score', 0) or 0):.0f}점 · "
            f"충돌 {html.escape(str(row.get('strategy_conflict_level', 'LOW')))}{status_suffix}{entry_suffix}</span>"
            f"</div>"
        )
    reason_html = ""
    if row.get('reason'):
        reason_html = (
            f"<div class='sigl-note'>"
            f"<span class='sigl-summary'>{html.escape(str(row['reason'])[:120])}</span>"
            f"</div>"
        )
    change_prefix = "+" if float(row.get('chg', 0) or 0) >= 0 else ""
    panel_html = f"""
        <div class="sigl-result-card {tone_class}">
            <div class="sigl-result-head">
                <div>
                    <p class="sigl-result-title">#{rank} {html.escape(str(row.get('ticker', '')))}</p>
                    <p class="sigl-result-copy">
                        현재가 {float(row.get('price', 0) or 0):.2f} · 변동 {change_prefix}{float(row.get('chg', 0) or 0):.1f}%
                    </p>
                </div>
                <div class="sigl-result-tags">
                    {_sigl_badge(f"SCAN {float(row.get('scan_score', 0) or 0):+.1f}", 'accent')}
                    {_sigl_badge(f"ES {float(row.get('es', 0) or 0):+.0f}", tone)}
                    {_sigl_badge(f"{judgment_label} ({float(row.get('cf', 0) or 0):.0f}%)", tone)}
                    {_sigl_badge(f"CTX {row.get('ctx', 'N/A')}", 'muted')}
                </div>
            </div>
            <div class="sigl-chip-row">{transitions}</div>
            <div class="sigl-chip-row">{volume_hits}</div>
            <div class="sigl-chip-row">{trend_hits}</div>
            <div class="sigl-chip-row">{strategy_hits}</div>
            <div class="sigl-chip-row">{combo_hits}</div>
            {top_strategy_text}
            {reason_html}
        </div>
        """
    _render_surface_html(panel_html, 0)

def _format_board_text(value, fallback="--"):
    text = str(value).strip() if value is not None else ""
    return text or fallback

def _format_board_code(value, fallback="--"):
    return _format_board_text(value, fallback).upper()

def _strategy_focus_item(top_strategy, fallback_date="STRAT"):
    if not isinstance(top_strategy, dict):
        return None
    label = _format_board_text(top_strategy.get('label'), '')
    if not label:
        return None
    raw_direction = _format_board_text(top_strategy.get('direction') or top_strategy.get('dir'), 'neutral').upper()
    direction = 'buy' if raw_direction == 'LONG' else 'sell' if raw_direction == 'SHORT' else raw_direction.lower()
    score = top_strategy.get('score')
    score_text = f"{float(score):.0f}점" if isinstance(score, (int, float)) else ""
    status_text = _format_strategy_status(top_strategy.get('status'))
    status_suffix = f" {status_text}" if status_text else ""
    entry_reference_text = _format_strategy_entry_reference(top_strategy)
    entry_suffix = f" {entry_reference_text}" if entry_reference_text else ""
    return {
        'icon': '◆',
        'label': f"{label} {score_text}{status_suffix}{entry_suffix}".strip(),
        'date': fallback_date,
        'dir': direction,
        'is_combined': False,
    }

def _format_board_es(value):
    try:
        return f"{float(value):+.1f}"
    except (TypeError, ValueError):
        return "--"

def _format_board_price(value):
    try:
        return f"{float(value):,.2f}"
    except (TypeError, ValueError):
        return "--"

def _format_board_change_value(value):
    try:
        return f"{float(value):+,.2f}"
    except (TypeError, ValueError):
        return "--"

def _format_board_change_pct(value):
    try:
        return f"{float(value):+.1f}%"
    except (TypeError, ValueError):
        return "--"

def _short_period_label(period_label):
    return {
        '3개월': '3M',
        '6개월': '6M',
        '1년': '1Y',
        '2년': '2Y',
    }.get(str(period_label).strip(), _format_board_text(period_label))

def _latest_analysis_message():
    for msg in reversed(st.session_state.get('messages', [])):
        if msg.get("type") == "analysis":
            return msg
    return None

def _analysis_messages(limit=None):
    collected = []
    for msg in reversed(st.session_state.get('messages', [])):
        if msg.get("type") != "analysis":
            continue
        collected.append(msg)
        if limit is not None and len(collected) >= limit:
            break
    return collected

def _format_board_time(value, fallback="--:--"):
    text = str(value).strip() if value is not None else ""
    if not text:
        return fallback
    try:
        return datetime.fromisoformat(text).strftime("%H:%M")
    except ValueError:
        return text if len(text) <= 5 else text[-5:]

def _terminal_signal_label(meta=None, fallback="IDLE"):
    meta = meta or {}
    action = str(meta.get('action_label', '')).strip()
    judgment = str(meta.get('judgment', '')).strip()
    combined = " ".join(part for part in (action, judgment) if part).upper()
    if 'STRONG_BUY' in combined or '강한 매수' in action:
        return 'STRONG_BUY'
    if 'BUY' in combined or '매수' in action:
        return 'BUY'
    if 'STRONG_SELL' in combined or '강한 매도' in action:
        return 'STRONG_SELL'
    if 'SELL' in combined or '매도' in action:
        return 'SELL'
    if 'HOLD' in combined or '보유' in action:
        return 'HOLD'
    if 'WATCH' in combined or '관망' in action:
        return 'WATCH'
    if 'NEUTRAL' in combined or '중립' in action:
        return 'NEUTRAL'
    if judgment:
        return _format_board_code(judgment, fallback)
    if action:
        return _format_board_code(action, fallback)
    return fallback

def _latest_recent_signal_label(meta=None, fallback="STANDBY"):
    meta = meta or {}
    recent = list(meta.get('recent_signals') or []) + list(meta.get('derived_signal_events') or [])
    if recent:
        last_item = recent[-1]
        if isinstance(last_item, dict):
            return _format_board_text(last_item.get('label'), fallback)
        return _format_board_text(last_item[1], fallback)
    top_strategy = (meta.get('strategy_summary') or {}).get('top_strategy') or meta.get('top_strategy')
    if isinstance(top_strategy, dict):
        return _format_board_text(top_strategy.get('label'), fallback)
    scans = list(meta.get('combined_scans') or [])
    if scans:
        return _format_board_text(scans[0].get('kor') or scans[0].get('name'), fallback)
    return fallback

def _primary_recent_signal_label(signal_items, fallback="STANDBY"):
    if signal_items:
        return _format_board_text(signal_items[0].get('label'), fallback)
    return fallback

def _latest_recent_signal_tone(meta=None, fallback="neutral"):
    meta = meta or {}
    recent = list(meta.get('recent_signals') or []) + list(meta.get('derived_signal_events') or [])
    if recent:
        last_item = recent[-1]
        if isinstance(last_item, dict):
            return _format_board_text(last_item.get('dir'), fallback).lower()
        return _format_board_text(last_item[3], fallback).lower()
    top_strategy = (meta.get('strategy_summary') or {}).get('top_strategy') or meta.get('top_strategy')
    if isinstance(top_strategy, dict):
        raw_direction = _format_board_text(top_strategy.get('direction') or top_strategy.get('dir'), fallback).upper()
        return 'buy' if raw_direction == 'LONG' else 'sell' if raw_direction == 'SHORT' else raw_direction.lower()
    scans = list(meta.get('combined_scans') or [])
    if scans:
        return _format_board_text(scans[0].get('dir'), fallback).lower()
    return fallback

def _primary_recent_signal_tone(signal_items, fallback="neutral"):
    if signal_items:
        return _format_board_text(signal_items[0].get('dir'), fallback).lower()
    return fallback

def _history_signal_stack(meta=None, limit=3):
    meta = meta or {}
    items = []
    seen = set()

    merged_recent = list(meta.get('recent_signals') or []) + list(meta.get('derived_signal_events') or [])
    for raw in reversed(merged_recent[-limit:]):
        if isinstance(raw, dict):
            icon = raw.get('icon')
            label = raw.get('label')
            direction = raw.get('dir')
        else:
            icon, label, _date, direction, _is_combined = raw
        clean_label = _format_board_text(label, '')
        if not clean_label or clean_label in seen:
            continue
        seen.add(clean_label)
        items.append({
            'icon': _format_board_text(icon, '•'),
            'label': clean_label,
            'tone': _format_board_text(direction, 'neutral').lower(),
        })
        if len(items) >= limit:
            break

    if not items:
        top_strategy = (meta.get('strategy_summary') or {}).get('top_strategy') or meta.get('top_strategy')
        strategy_item = _strategy_focus_item(top_strategy)
        if strategy_item:
            clean_label = _format_board_text(strategy_item.get('label'), '')
            seen.add(clean_label)
            items.append({
                'icon': strategy_item['icon'],
                'label': clean_label,
                'tone': _format_board_text(strategy_item.get('dir'), 'neutral').lower(),
            })

    if len(items) < limit:
        for raw in list(meta.get('strategy_visible_results') or [])[:limit]:
            clean_label = _format_board_text(raw.get('label'), '')
            if not clean_label or clean_label in seen:
                continue
            seen.add(clean_label)
            score = raw.get('score')
            suffix = f" {float(score):.0f}점" if isinstance(score, (int, float)) else ""
            items.append({
                'icon': '◆',
                'label': f"{clean_label}{suffix}",
                'tone': 'buy' if _format_board_text(raw.get('direction'), '').upper() == 'LONG' else 'sell' if _format_board_text(raw.get('direction'), '').upper() == 'SHORT' else _format_board_text(raw.get('direction'), 'neutral').lower(),
            })
            if len(items) >= limit:
                break

    if len(items) < limit:
        for raw in list(meta.get('combined_scans') or [])[:limit]:
            clean_label = _format_board_text(raw.get('kor') or raw.get('name'), '')
            if not clean_label or clean_label in seen:
                continue
            seen.add(clean_label)
            items.append({
                'icon': _format_board_text(raw.get('icon'), '•'),
                'label': clean_label,
                'tone': _format_board_text(raw.get('dir'), 'neutral').lower(),
            })
            if len(items) >= limit:
                break

    return items

def _change_tone_from_value(value):
    if isinstance(value, (int, float)):
        if value > 0:
            return 'up'
        if value < 0:
            return 'down'
    return 'flat'

def _history_rows_from_messages(messages, limit=8):
    rows = []
    for idx, msg in enumerate(messages[:limit]):
        meta = msg.get('meta') or {}
        es_value = meta.get('ensemble_score')
        change_amount = meta.get('price_change')
        change_pct = meta.get('price_change_pct')
        rows.append({
            'time': _format_board_time(msg.get('analyzed_at')),
            'ticker': _format_board_code(msg.get('ticker'), 'WAIT'),
            'price': _format_board_price(meta.get('price')),
            'change_value': _format_board_change_value(change_amount),
            'change_pct': _format_board_change_pct(change_pct),
            'change_tone': _change_tone_from_value(change_amount if isinstance(change_amount, (int, float)) else change_pct),
            'signal': _terminal_signal_label(meta),
            'recent': _latest_recent_signal_label(meta),
            'recent_tone': _latest_recent_signal_tone(meta),
            'signal_stack': _history_signal_stack(meta, limit=3),
            'tone': _resolve_board_tone('ANALYSIS', meta.get('judgment') or meta.get('action_label'), es_value),
            'fresh': idx == 0,
        })
    return rows

def _focus_recent_signals_from_analysis(meta, limit=5):
    items = []
    top_strategy = (meta or {}).get('top_strategy') or ((meta or {}).get('strategy_summary') or {}).get('top_strategy')
    strategy_item = _strategy_focus_item(top_strategy)
    if strategy_item:
        items.append(strategy_item)
    for raw in list((meta or {}).get('strategy_visible_results') or [])[: max(limit - len(items), 0)]:
        items.append({
            'icon': '◆',
            'label': _format_board_text(raw.get('label'), '전략'),
            'date': _format_board_text(raw.get('phase'), '--'),
            'dir': 'buy' if _format_board_text(raw.get('direction'), '').upper() == 'LONG' else 'sell' if _format_board_text(raw.get('direction'), '').upper() == 'SHORT' else _format_board_text(raw.get('direction'), 'neutral').lower(),
            'is_combined': False,
        })
        if len(items) >= limit:
            return items[:limit]
    recent = list((meta or {}).get('recent_signals') or []) + list((meta or {}).get('derived_signal_events') or [])
    for raw in reversed(recent[-limit:]):
        if isinstance(raw, dict):
            icon = raw.get('icon')
            label = raw.get('label')
            date = raw.get('date')
            direction = raw.get('dir')
            is_combined = raw.get('is_combined')
        else:
            icon, label, date, direction, is_combined = raw
        items.append({
            'icon': _format_board_text(icon, '•'),
            'label': _format_board_text(label, 'NO SIGNAL'),
            'date': _format_board_text(date, '--/--'),
            'dir': _format_board_text(direction, 'neutral').lower(),
            'is_combined': bool(is_combined),
        })
        if len(items) >= limit:
            break
    return items[:limit]

def _focus_recent_signals_from_scan(focus_row, limit=5):
    if not focus_row:
        return []
    source_items = []
    strategy_item = _strategy_focus_item(focus_row.get('top_strategy'))
    if strategy_item:
        source_items.append(strategy_item)
    for raw in list(focus_row.get('strategies') or [])[: max(limit - len(source_items), 0)]:
        source_items.append({
            'icon': '◆',
            'label': _format_board_text(raw.get('label'), '전략'),
            'date': _format_board_text(raw.get('phase'), '--'),
            'dir': 'buy' if _format_board_text(raw.get('direction'), '').upper() == 'LONG' else 'sell' if _format_board_text(raw.get('direction'), '').upper() == 'SHORT' else _format_board_text(raw.get('direction'), 'neutral').lower(),
            'is_combined': False,
        })
        if len(source_items) >= limit:
            break
    if not source_items:
        source_items = list(focus_row.get('multi_hits') or focus_row.get('scans') or [])
    items = []
    for raw in source_items[:limit]:
        items.append({
            'icon': _format_board_text(raw.get('icon'), '•'),
            'label': _format_board_text(raw.get('label') or raw.get('kor'), 'SCAN READY'),
            'date': _format_board_text(raw.get('date'), '--/--'),
            'dir': _format_board_text(raw.get('dir'), 'neutral').lower(),
            'is_combined': bool(raw.get('is_combined') or ('tier' in raw)),
        })
    return items

def _focus_stack_summary_from_analysis(meta):
    meta = meta or {}
    return {
        'buy_agree': int(_sf(meta.get('buy_agree', 0))),
        'sell_agree': int(_sf(meta.get('sell_agree', 0))),
        'combined_scans': list(meta.get('combined_scans') or [])[:2],
        'top_strategy': (meta.get('strategy_summary') or {}).get('top_strategy') or meta.get('top_strategy'),
        'strategy_conflict_level': ((meta.get('strategy_summary') or {}).get('conflict_level') or 'LOW'),
        'veto_flags': _format_board_text(meta.get('veto_flags'), ''),
        'leading_verdict': _format_board_text(meta.get('leading_verdict'), 'STANDBY'),
        'lagging_verdict': _format_board_text(meta.get('lagging_verdict'), 'STANDBY'),
    }

def _focus_stack_summary_from_scan(focus_row):
    focus_row = focus_row or {}
    return {
        'buy_agree': int(_sf(focus_row.get('ba', 0))),
        'sell_agree': int(_sf(focus_row.get('sa', 0))),
        'combined_scans': list(focus_row.get('scans') or [])[:2],
        'top_strategy': focus_row.get('top_strategy'),
        'strategy_conflict_level': _format_board_text(focus_row.get('strategy_conflict_level'), 'LOW'),
        'veto_flags': '',
        'leading_verdict': _format_board_text(focus_row.get('action'), 'SCANNER_READY'),
        'lagging_verdict': _format_board_text(focus_row.get('ctx'), 'WATCHLIST'),
    }

def _dedupe_board_items(items, limit=12):
    unique = []
    seen = set()
    for item in items:
        text = str(item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        unique.append(text)
        if len(unique) >= limit:
            break
    return unique

def _scan_tape_items(limit=6):
    items = []
    for row in st.session_state.get('scan_results', [])[:limit]:
        ticker = _format_board_code(row.get('ticker'), "")
        if not ticker:
            continue
        signal = _format_board_code(row.get('jg_key') or row.get('action') or row.get('jg'), "READY")
        items.append(f"{ticker} ES {_format_board_es(row.get('es'))} [{signal}]")
    return items

def _history_marquee_items(history_rows, limit=8):
    return [
        f"{row.get('ticker', 'WAIT')} PX {row.get('price', '--')} {row.get('change_value', '--')} {row.get('change_pct', '--')} SIGNAL {row.get('signal', 'IDLE')} RECENT {row.get('recent', 'STANDBY')}"
        for row in (history_rows or [])[:limit]
    ]

def _focus_signal_marquee_items(signal_items, limit=5):
    items = []
    for item in (signal_items or [])[:limit]:
        label = _format_board_text(item.get('label'), 'SIGNAL')
        date = _format_board_text(item.get('date'), '')
        icon = _format_board_text(item.get('icon'), '•')
        parts = [icon, label]
        if date and date != '--/--':
            parts.append(date)
        items.append(" ".join(parts))
    return items

def _build_board_marquee(base_items, history_rows=None, focus_recent_signals=None):
    combined = [*base_items]
    history_items = _history_marquee_items(history_rows or [])
    focus_items = _focus_signal_marquee_items(focus_recent_signals or [])
    if history_items:
        combined.extend(history_items)
    if focus_items:
        combined.extend(focus_items)
    if not history_items or len(combined) < 10:
        combined.extend(_scan_tape_items())
    return _dedupe_board_items([
        *combined,
        f"[ {BRAND_NAME} ] READY",
        "TARGET WAIT",
        "ES --",
        "SIGNAL IDLE",
    ], limit=16)

def _resolve_board_tone(mode_label, judgment, es_value):
    judgment_text = str(judgment or "")
    judgment_key = judgment_text.upper()
    if 'BUY' in judgment_key or '매수' in judgment_text:
        return 'bull'
    if 'SELL' in judgment_key or '매도' in judgment_text:
        return 'bear'
    try:
        numeric_es = float(es_value)
    except (TypeError, ValueError):
        numeric_es = 0.0
    if mode_label == 'SCANNER':
        if numeric_es > 10:
            return 'bull'
        if numeric_es < -10:
            return 'bear'
        return 'scanner'
    return 'neutral'

def _build_brand_payload(current_mode, chart_period):
    if current_mode == MODE_SCANNER:
        mode_label = 'SCANNER'
    elif current_mode == MODE_MARKET_DAILY:
        mode_label = '오늘 미국장'
    else:
        mode_label = 'ANALYSIS'
    period_label = _short_period_label(chart_period)
    analysis_messages = _analysis_messages()
    analysis_count = len(analysis_messages)
    history_rows = _history_rows_from_messages(analysis_messages, limit=8)

    if current_mode == MODE_SCANNER:
        results = st.session_state.get('scan_results', [])
        focus_idx = st.session_state.get('scan_focus_idx')
        focus_row = None
        if results:
            if isinstance(focus_idx, int) and 0 <= focus_idx < len(results):
                focus_row = results[focus_idx]
            else:
                focus_row = results[0]

        selected_sector = _format_board_text(
            st.session_state.get('selected_sector') or _sector_selection_title(st.session_state.get('selected_sectors')),
            fallback='READY'
        )
        focus = _format_board_code(focus_row.get('ticker') if focus_row else selected_sector, fallback='READY')
        es_value = focus_row.get('es') if focus_row else None
        price_value = focus_row.get('price') if focus_row else None
        change_amount = focus_row.get('chg_value') if focus_row else None
        change_pct = focus_row.get('chg') if focus_row else None
        judgment_source = (focus_row.get('action') or focus_row.get('jg_key')) if focus_row else 'READY'
        judgment = _format_board_code(judgment_source, fallback='READY')
        context = _format_board_code(
            focus_row.get('ctx') if focus_row else (selected_sector if selected_sector != 'READY' else 'STANDBY'),
            fallback='STANDBY'
        )
        scan_source = _format_board_code(st.session_state.get('scan_source'), fallback='WATCHLIST')
        system_status = 'ACTIVE' if focus_row else 'READY'
        feed_status = 'WATCH_SYNC'
        focus_recent_signals = _focus_recent_signals_from_scan(focus_row)
        focus_stack_summary = _focus_stack_summary_from_scan(focus_row)
        recent_label = _primary_recent_signal_label(focus_recent_signals, 'SCAN READY')
        recent_tone = _primary_recent_signal_tone(focus_recent_signals, 'neutral')
        summary = "Analysis logs stay live while the scanner keeps the field ranked."
        marquee_items = _build_board_marquee([
            f"[ {BRAND_NAME} ] LOGBOARD",
            f"STATUS {system_status}",
            f"TARGET {focus}",
            f"ES {_format_board_es(es_value)}",
            f"SIGNAL {judgment}",
            f"CTX {context}",
            f"SPAN {period_label}",
            f"SOURCE {scan_source}",
            f"LOG {analysis_count:02d}",
        ], history_rows=history_rows, focus_recent_signals=focus_recent_signals)
        return {
            'brand_code': BRAND_NAME,
            'mode': mode_label,
            'focus': focus,
            'price': _format_board_price(price_value),
            'change_value': _format_board_change_value(change_amount),
            'change_pct': _format_board_change_pct(change_pct),
            'change_tone': _change_tone_from_value(change_amount if isinstance(change_amount, (int, float)) else change_pct),
            'es': _format_board_es(es_value),
            'judgment': judgment,
            'context': context,
            'period': period_label,
            'recent_label': recent_label,
            'recent_tone': recent_tone,
            'marquee_items': marquee_items,
            'summary': summary,
            'system_status': system_status,
            'feed_status': feed_status,
            'analysis_count': analysis_count,
            'history_rows': history_rows,
            'focus_recent_signals': focus_recent_signals,
            'focus_stack_summary': focus_stack_summary,
            'status_tone': _resolve_board_tone(mode_label, judgment, es_value),
        }

    if current_mode == MODE_MARKET_DAILY:
        focus = _format_board_code(st.session_state.get('last_ticker'), fallback='US CLOSE')
        judgment = 'BRIEFING'
        context = 'US CLOSE'
        system_status = 'ACTIVE'
        feed_status = 'MARKET_SYNC'
        recent_label = 'DAILY RECAP'
        recent_tone = 'accent'
        summary = "Macro, breadth, and leadership shifts are staged before the next analysis entry."
        marquee_items = _build_board_marquee([
            f"[ {BRAND_NAME} ] BRIEFING",
            f"STATUS {system_status}",
            f"FOCUS {focus}",
            f"SIGNAL {judgment}",
            f"CTX {context}",
            f"SPAN {period_label}",
            f"LOG {analysis_count:02d}",
        ], history_rows=history_rows)
        return {
            'brand_code': BRAND_NAME,
            'mode': mode_label,
            'focus': focus,
            'price': _format_board_price(None),
            'change_value': _format_board_change_value(None),
            'change_pct': _format_board_change_pct(None),
            'change_tone': 'neutral',
            'es': _format_board_es(None),
            'judgment': judgment,
            'context': context,
            'period': period_label,
            'recent_label': recent_label,
            'recent_tone': recent_tone,
            'marquee_items': marquee_items,
            'summary': summary,
            'system_status': system_status,
            'feed_status': feed_status,
            'analysis_count': analysis_count,
            'history_rows': history_rows,
            'focus_recent_signals': [],
            'focus_stack_summary': {'buy_agree': 0, 'sell_agree': 0, 'combined_scans': [], 'veto_flags': ''},
            'status_tone': 'neutral',
        }

    analysis_msg = _latest_analysis_message()
    meta = analysis_msg.get('meta') if analysis_msg else None
    focus = _format_board_code((analysis_msg or {}).get('ticker'), fallback='WAIT')
    es_value = meta.get('ensemble_score') if meta else None
    judgment = _terminal_signal_label(meta, fallback='IDLE')
    context = _format_board_code(meta.get('context_label') if meta else 'STANDBY', fallback='STANDBY')
    system_status = 'ACTIVE' if meta else 'READY'
    feed_status = 'MARKET_SYNC'
    focus_recent_signals = _focus_recent_signals_from_analysis(meta)
    focus_stack_summary = _focus_stack_summary_from_analysis(meta)
    price_value = meta.get('price') if meta else None
    change_amount = meta.get('price_change') if meta else None
    change_pct = meta.get('price_change_pct') if meta else None
    recent_label = _primary_recent_signal_label(focus_recent_signals, _latest_recent_signal_label(meta))
    recent_tone = _primary_recent_signal_tone(focus_recent_signals, _latest_recent_signal_tone(meta))
    summary = (
        f"Signal ingress is live. {focus} is the latest structured read on the board."
        if meta and meta.get('action_label')
        else "The logboard fills as new analyses arrive. Select a target ticker to light it up."
    )
    marquee_items = [
        f"[ {BRAND_NAME} ] LOGBOARD",
        f"STATUS {system_status}",
        f"TARGET {focus}",
        f"ES {_format_board_es(es_value)}",
        f"SIGNAL {judgment}",
        f"CTX {context}",
        f"SPAN {period_label}",
        f"LOG {analysis_count:02d}",
    ]
    marquee_items = _build_board_marquee(
        marquee_items,
        history_rows=history_rows,
        focus_recent_signals=focus_recent_signals,
    )
    return {
        'brand_code': BRAND_NAME,
        'mode': mode_label,
        'focus': focus,
        'price': _format_board_price(price_value),
        'change_value': _format_board_change_value(change_amount),
        'change_pct': _format_board_change_pct(change_pct),
        'change_tone': _change_tone_from_value(change_amount if isinstance(change_amount, (int, float)) else change_pct),
        'es': _format_board_es(es_value),
        'judgment': judgment,
        'context': context,
        'period': period_label,
        'recent_label': recent_label,
        'recent_tone': recent_tone,
        'marquee_items': marquee_items,
        'summary': summary,
        'system_status': system_status,
        'feed_status': feed_status,
        'analysis_count': analysis_count,
        'history_rows': history_rows,
        'focus_recent_signals': focus_recent_signals,
        'focus_stack_summary': focus_stack_summary,
        'status_tone': _resolve_board_tone(mode_label, judgment, es_value),
    }

def _render_brand_board(payload, compact=False):
    st.markdown(_html_block(build_brand_board(payload, compact=compact)), unsafe_allow_html=True)
    if not compact:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)


def _badge_html(badges):
    rendered = []
    for item in badges or []:
        if isinstance(item, tuple):
            label, tone = item
        else:
            label, tone = item, "muted"
        rendered.append(_sigl_badge(label, tone))
    return "".join(rendered)


def _render_page_intro(eyebrow, title, copy, badges=None, tone="accent"):
    tone_class = {
        "accent": "sigl-card--accent",
        "positive": "sigl-card--positive",
        "negative": "sigl-card--negative",
        "warning": "sigl-card--warning",
    }.get(tone, "sigl-card--accent")
    intro_html = f"""
        <div class="sigl-page-banner sigl-card {tone_class}">
            <div class="sigl-page-banner__grid">
                <div>
                    <p class="sigl-page-head__eyebrow">{html.escape(str(eyebrow))}</p>
                    <p class="sigl-page-head__title">{html.escape(str(title))}</p>
                    <p class="sigl-page-banner__copy">{html.escape(str(copy))}</p>
                </div>
                <div class="sigl-page-banner__meta">{_badge_html(badges)}</div>
            </div>
        </div>
    """
    st.markdown(_html_block(intro_html), unsafe_allow_html=True)


def _render_section_heading(title, copy="", badges=None, eyebrow=None, tight=False):
    shell_class = "sigl-section-shell sigl-section-shell--tight" if tight else "sigl-section-shell"
    eyebrow_html = f"<p class='sigl-page-head__eyebrow'>{html.escape(str(eyebrow))}</p>" if eyebrow else ""
    heading_html = f"""
        <div class="{shell_class}">
            <div class="sigl-page-head">
                <div>
                    {eyebrow_html}
                    <p class="sigl-page-head__title">{html.escape(str(title))}</p>
                    {f"<p class='sigl-page-head__copy'>{html.escape(str(copy))}</p>" if copy else ""}
                </div>
                <div class="sigl-inline">{_badge_html(badges)}</div>
            </div>
        </div>
    """
    st.markdown(_html_block(heading_html), unsafe_allow_html=True)


def _render_empty_state(title, copy, badges=None, tone="accent"):
    tone_class = {
        "accent": "sigl-card--accent",
        "positive": "sigl-card--positive",
        "negative": "sigl-card--negative",
        "warning": "sigl-card--warning",
    }.get(tone, "sigl-card--accent")
    empty_html = f"""
        <div class="sigl-empty-card sigl-card {tone_class}">
            <div class="sigl-section-head">
                <div>
                    <p class="sigl-empty-card__title">{html.escape(str(title))}</p>
                    <p class="sigl-empty-card__copy">{html.escape(str(copy))}</p>
                </div>
                <div class="sigl-inline">{_badge_html(badges)}</div>
            </div>
        </div>
    """
    st.markdown(_html_block(empty_html), unsafe_allow_html=True)

with st.sidebar:
    app_mode = _render_sidebar_choice_buttons(
        "모드",
        _APP_MODE_OPTIONS,
        "_mode",
        columns=1,
        default_value=MODE_MARKET_DAILY,
    )
    chart_period = _render_sidebar_choice_buttons(
        "기간",
        ['3개월', '6개월', '1년', '2년'],
        "period",
        columns=2,
        default_value='6개월',
    )
    chart_days = {'3개월': 63, '6개월': 126, '1년': 252, '2년': 504}[chart_period]
    st.markdown("---")
    if st.button("🗑️ 초기화", use_container_width=True, type="secondary"):
        reset_session()
        st.rerun()

    if st.session_state.get('_mode', MODE_MARKET_DAILY) == MODE_ANALYSIS:
        _render_analysis_sidebar_nav()

current_mode = st.session_state.get('_mode', MODE_MARKET_DAILY)
main_board_payload = _build_brand_payload(current_mode, chart_period)

# ══════════════════════════════════════════════════════════════
#  스캐너 모드
# ══════════════════════════════════════════════════════════════
if current_mode == MODE_SCANNER:
    _render_brand_board(main_board_payload)
    all_universe = sorted({str(t).strip().upper() for ts in SECTOR_GROUPS.values() for t in ts if str(t).strip()})
    sector_names = list(SECTOR_GROUPS.keys())
    current_sector_selection = _normalized_selected_sectors(
        st.session_state.get('selected_sectors') or st.session_state.get('selected_sector')
    )
    if st.session_state.pop('_clear_scan_pending', False):
        st.session_state.pop('selected_sector', None)
        st.session_state.pop('selected_sectors', None)
        st.session_state.pop('scan_tickers_override', None)
        st.session_state['scan_etf_picker'] = []
        st.session_state['scan_etf_items'] = []
        st.session_state['scan_etf_tickers_override'] = None
        st.session_state['scan_etf_note'] = ''
        st.session_state['scan_etf_errors'] = []
        st.session_state['scan_results'] = []
        st.session_state['scan_source'] = ''
        st.session_state['scan_total'] = 0
        st.session_state['scan_focus_idx'] = None
        st.session_state['scan_focus_ticker'] = None
        st.session_state['scan_nav_select_idx'] = None
        st.session_state['scan_filter_preset'] = SCAN_FILTER_PRESETS[0]
        st.session_state['scan_filtered_results'] = []
        st.session_state['scan_snapshots'] = []
        st.session_state['scan_perf_stats'] = {}
        st.session_state['scan_skip_reasons'] = []
        st.session_state.pop('scan_in', None)
        st.session_state['scan_sector_picker'] = []
        current_sector_selection = []
    _apply_sector_selection(current_sector_selection)
    manual_preview = _parse_ticker_input(st.session_state.get('scan_in'))
    current_etf_selection = _normalized_selected_etf_presets(st.session_state.get('scan_etf_picker'))
    active_etf_items = st.session_state.get('scan_etf_items') or []
    active_etf_tickers = st.session_state.get('scan_etf_tickers_override') or []
    sector_preview = st.session_state.get('scan_tickers_override') or _sector_selection_tickers(current_sector_selection) or []
    preview_universe = _build_scan_universe_payload(
        current_sector_selection,
        sector_preview,
        active_etf_items,
        active_etf_tickers,
        manual_preview,
    )

    _render_page_intro(
        "Scanner",
        "대상을 구성하고 스캔을 실행하세요.",
        "스캔 결과를 확인하고, 분석 모드로 자세한 분석을 이어가실 수 있습니다.",
        badges=[
            (f"선택 섹터 {len(current_sector_selection)}", "accent"),
            (f"ETF 선택 {len(current_etf_selection)}", "warning"),
            (f"직접 입력 {len(manual_preview)}개", "warning"),
            (f"합집합 유니버스 {preview_universe.get('final_count', 0)}개", "positive"),
            (f"전체 후보 {len(all_universe)}개", "muted"),
        ],
    )

    _render_section_heading(
        "섹터, ETF, 직접 티커 입력으로 스캔 대상을 구성하세요.",
        badges=[
            ("멀티 섹터 선택", "accent"),
            ("ETF 임시 유니버스", "warning"),
            ("3개 소스 합집합 결합", "positive"),
        ],
        eyebrow="스캔 대상 구성",
    )
    with st.container():
        st.markdown("<div class='sigl-sector-picker-anchor'></div>", unsafe_allow_html=True)
        _render_sector_button_picker(sector_names, current_sector_selection)

    selected_sectors = _normalized_selected_sectors(
        st.session_state.get('selected_sectors') or current_sector_selection
    )

    _render_section_heading(
        "ETF 또는 지수를 선택하여 스캔 대상을 구성할 수 있습니다.",
        badges=[
            ("전체 종목 미포함", "accent"),
            ("ETF 임시 유니버스", "warning"),
        ],
        eyebrow="ETF 선택",
        tight=True,
    )
    with st.container():
        st.markdown("<div class='sigl-sector-picker-anchor'></div>", unsafe_allow_html=True)
        _render_etf_button_picker(current_etf_selection)
    etf_clear_col1, etf_clear_col2 = st.columns([2, 1])
    with etf_clear_col2:
        if st.button("ETF 선택 해제", use_container_width=True):
            _apply_etf_selection([])
            st.rerun()

    current_etf_selection = _normalized_selected_etf_presets(st.session_state.get('scan_etf_picker'))
    active_etf_items = st.session_state.get('scan_etf_items') or []
    active_etf_tickers = st.session_state.get('scan_etf_tickers_override') or []
    if st.session_state.get('scan_etf_errors'):
        st.caption("일부 ETF는 불러오지 못했습니다: " + " | ".join(st.session_state['scan_etf_errors']))

    with st.form("scanner_direct_input", clear_on_submit=False):
        ci = st.text_input(
            "스캔 대상 티커 입력",
            placeholder="추가로 스캔할 티커를 쉼표(,)로 구분해서 입력하세요.",
            key="scan_in",
            label_visibility="collapsed",
        )
        action_col, clear_col = st.columns(2)
        with action_col:
            scan_btn = st.form_submit_button("스캔 실행", type="primary", use_container_width=True)
        with clear_col:
            clear_scan = st.form_submit_button("초기화", type="secondary", use_container_width=True)
  
    if clear_scan:
        st.session_state['_clear_scan_pending'] = True
        st.rerun()

    manual_tickers = _parse_ticker_input(ci)
    selected_sectors = _normalized_selected_sectors(st.session_state.get('selected_sectors') or current_sector_selection)
    sector_tickers = st.session_state.get('scan_tickers_override') or _sector_selection_tickers(selected_sectors) or []
    active_etf_items = st.session_state.get('scan_etf_items') or []
    active_etf_tickers = st.session_state.get('scan_etf_tickers_override') or []
    universe_payload = _build_scan_universe_payload(
        selected_sectors,
        sector_tickers,
        active_etf_items,
        active_etf_tickers,
        manual_tickers,
    )
    tickers = list(universe_payload.get("tickers") or [])
    scan_source = str(universe_payload.get("source_label") or "직접")
    _render_universe_builder_panel(universe_payload)

    if scan_btn and not tickers:
        st.warning("스캔할 티커가 없습니다. 섹터를 고르거나 ETF 종목을 불러오거나 직접 티커를 입력해 주세요.")

    if scan_btn and tickers:
        run_started = time.perf_counter()
        setup_started = time.perf_counter()
        pb = st.progress(0)
        scan_note = st.empty()
        results = []
        skip_reasons = []
        ticker_latencies = []
        cache_bucket = math.floor(time.time() / 300)
        max_workers = min(12, max(4, len(tickers) // 10), len(tickers))

        # 런타임 콤보 레지스트리 등록 보장
        try:
            from engine import _ensure_runtime_combo_registry
            _ensure_runtime_combo_registry()
        except Exception as exc:
            skip_reasons.append({"ticker": "-", "reason": "registry_error", "detail": str(exc)[:220]})
        setup_seconds = _sf(time.perf_counter() - setup_started)

        # TODO(scanner-architecture): ScannerWorkflow와 app.py 인라인 스캐너 경로를 단일 경계로 통합.
        with st.status(f"MARKET SWEEP ACTIVE · {len(tickers)} TICKERS", expanded=True) as scan_status:
            scan_note.caption(f"1/3 런타임 확인 완료 · 워커 {max_workers}개")
            scan_seconds_started = time.perf_counter()

            scan_note.caption("2/3 병렬 스캔을 시작합니다. 최근 완료 종목이 아래에 표시됩니다.")
            with ThreadPoolExecutor(max_workers=max_workers) as ex:
                futs = {ex.submit(_scan_ticker_worker, ticker, cache_bucket): ticker for ticker in tickers}
                for idx_f, future in enumerate(as_completed(futs)):
                    done_ticker = futs[future]
                    pb.progress((idx_f + 1) / len(tickers))
                    scan_note.caption(f"READING THE TAPE · {done_ticker} · {idx_f + 1}/{len(tickers)}")
                    payload = future.result()
                    if payload.get("ok") and isinstance(payload.get("row"), dict):
                        row = dict(payload["row"])
                        row["scan_source"] = scan_source
                        row["scan_latency_sec"] = _sf(payload.get("elapsed_sec", 0))
                        results.append(row)
                        ticker_latencies.append(float(payload.get("elapsed_sec", 0) or 0))
                    else:
                        skip_reasons.append(
                            {
                                "ticker": payload.get("ticker") or done_ticker,
                                "reason": payload.get("skip_reason") or "unknown",
                                "detail": str(payload.get("detail") or "")[:220],
                            }
                        )
            scan_seconds = _sf(time.perf_counter() - scan_seconds_started)

            scan_note.caption("3/3 결과를 정렬하고 스캐너 카드를 준비합니다.")
            sort_started = time.perf_counter()
            results.sort(key=lambda row: (-row['scan_score'], -row['strength'], -row['latest_sig_ts'], row['ticker']))
            sort_seconds = _sf(time.perf_counter() - sort_started)
            scan_status.update(label=f"SCAN BOOK READY · {len(results)} MATCHES", state="complete", expanded=False)
        pb.empty()
        scan_note.empty()

        perf_stats = {
            "workers": max_workers,
            "setup_seconds": setup_seconds,
            "scan_seconds": scan_seconds,
            "sort_seconds": sort_seconds,
            "total_seconds": _sf(time.perf_counter() - run_started),
            "ticker_count": len(tickers),
            "match_count": len(results),
            "skip_count": len(skip_reasons),
            "avg_row_seconds": _sf(sum(ticker_latencies) / len(ticker_latencies)) if ticker_latencies else 0.0,
        }
        filter_preset = str(st.session_state.get("scan_filter_preset") or SCAN_FILTER_PRESETS[0])
        filtered_results = _apply_scan_filter(results, filter_preset)
        snapshot = _build_scan_snapshot(
            universe_payload=universe_payload,
            filter_preset=filter_preset,
            results=results,
            filtered_results=filtered_results,
            perf_stats=perf_stats,
            skip_reasons=skip_reasons,
        )
        snapshots = list(st.session_state.get("scan_snapshots") or [])
        snapshots.append(snapshot)
        snapshots = snapshots[-20:]

        st.session_state['scan_results'] = results
        st.session_state['scan_filtered_results'] = filtered_results
        st.session_state['scan_source'] = scan_source
        st.session_state['scan_total'] = len(tickers)
        st.session_state['scan_perf_stats'] = perf_stats
        st.session_state['scan_skip_reasons'] = skip_reasons
        st.session_state['scan_snapshots'] = snapshots
        st.session_state['scan_focus_idx'] = 0 if results else None
        st.session_state['scan_focus_ticker'] = results[0]['ticker'] if results else None
        st.session_state['scan_nav_select_idx'] = 0 if results else None

    # ── 결과 렌더링 ──────────────────────────────────────────────────────────
    results = st.session_state.get('scan_results', [])
    filter_preset = st.radio(
        "결과 필터",
        options=SCAN_FILTER_PRESETS,
        horizontal=True,
        key="scan_filter_preset",
    )
    filtered_results = _apply_scan_filter(results, filter_preset)
    st.session_state["scan_filtered_results"] = filtered_results
    if results:
        scan_total = st.session_state.get('scan_total', 0)
        perf_stats = st.session_state.get("scan_perf_stats") or {}
        skip_reasons = st.session_state.get("scan_skip_reasons") or []
        _render_section_heading(
            "스캔 결과",
            "현재 유니버스에서 조건과 점수가 높은 종목을 우선순위대로 정렬했습니다.",
            badges=[
                (f"원본 {len(results)}개", "accent"),
                (f"필터 {len(filtered_results)}개", "positive"),
                (f"전체 대상 {scan_total}개", "muted"),
            ],
            eyebrow="Result Board",
            tight=True,
        )
        st.caption("정렬 기준: 스캔 점수 → 강도 → 최근 시그널 순서입니다.")
        _render_scanner_summary(filtered_results, scan_total)
        if perf_stats:
            st.caption(
                "성능: "
                f"총 {float(perf_stats.get('total_seconds', 0)):.2f}s · "
                f"설정 {float(perf_stats.get('setup_seconds', 0)):.2f}s · "
                f"스캔 {float(perf_stats.get('scan_seconds', 0)):.2f}s · "
                f"정렬 {float(perf_stats.get('sort_seconds', 0)):.2f}s · "
                f"평균행 {float(perf_stats.get('avg_row_seconds', 0)):.3f}s"
            )
        if skip_reasons:
            with st.expander(f"제외된 종목 {len(skip_reasons)}개 보기", expanded=False):
                reason_labels = {
                    "insufficient_history": "히스토리 부족",
                    "missing_frame": "데이터 미수신",
                    "compute_error": "계산 오류",
                    "row_build_error": "행 생성 오류",
                    "registry_error": "레지스트리 오류",
                    "invalid_ticker": "티커 형식 오류",
                }
                for item in skip_reasons[:30]:
                    label = reason_labels.get(str(item.get("reason")), str(item.get("reason")))
                    detail = str(item.get("detail") or "")
                    st.caption(f"{item.get('ticker', '-')} · {label}" + (f" · {detail}" if detail else ""))

        snapshot_for_download = (st.session_state.get("scan_snapshots") or [None])[-1]
        if snapshot_for_download is None:
            snapshot_for_download = _build_scan_snapshot(
                universe_payload=universe_payload,
                filter_preset=filter_preset,
                results=results,
                filtered_results=filtered_results,
                perf_stats=perf_stats,
                skip_reasons=skip_reasons,
            )
        csv_col, json_col, dict_col = st.columns(3)
        with csv_col:
            st.download_button(
                "CSV 다운로드 (현재 필터)",
                data=_scanner_rows_to_csv_bytes(filtered_results),
                file_name=f"scanner_filtered_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True,
                key="scanner_csv_download",
            )
        with json_col:
            st.download_button(
                "JSON 스냅샷 다운로드",
                data=_scanner_snapshot_to_json_bytes(snapshot_for_download),
                file_name=f"scanner_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True,
                key="scanner_json_download",
            )
        with dict_col:
            st.download_button(
                "CSV 컬럼사전 다운로드",
                data=_scanner_csv_dictionary_to_csv_bytes(),
                file_name=f"scanner_csv_dictionary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True,
                key="scanner_csv_dictionary_download",
            )

        with st.expander("CSV 도움말", expanded=False):
            for line in scanner_csv_help_lines():
                st.caption(line)
            st.caption("전체 컬럼 상세는 `CSV 컬럼사전 다운로드` 파일에서 확인할 수 있습니다.")
            spec_map = {str(spec.get("key")): spec for spec in scanner_csv_field_specs()}
            preview_keys = [
                "scan_score",
                "bull_turn_recent",
                "volume_bullish",
                "detected_transition_summary",
                "detected_core_summary",
                "detected_signal_total_count",
            ]
            for key in preview_keys:
                spec = spec_map.get(key)
                if not spec:
                    continue
                header = f"{spec.get('label')}({spec.get('key')})"
                description = str(spec.get("description", ""))
                rule = str(spec.get("rule", ""))
                st.caption(f"{header}: {description}" + (f" · 기준: {rule}" if rule else ""))

        for rk, r in enumerate(filtered_results, start=1):
            _render_scanner_result_card(rk, r)

            if st.button(f"{r['ticker']} 분석", key=f"sc_{r['ticker']}", use_container_width=True):
                _set_scan_focus(r['ticker'])
                _queue_analysis_target(r['ticker'])
    else:
        _render_empty_state(
            "아직 스캔 결과가 없습니다",
            "섹터/ETF/직접입력을 구성한 뒤 `스캔 실행`을 누르면 결과 카드가 정렬되어 표시됩니다.",
            badges=[
                ("유니버스 선택 필요", "warning"),
                ("직접 입력 가능", "muted"),
            ],
            tone="accent",
        )

# ══════════════════════════════════════════════════════════════
#  오늘 미국장 모드
# ══════════════════════════════════════════════════════════════
elif current_mode == MODE_MARKET_DAILY:
    _render_brand_board(main_board_payload)
    render_market_daily_dashboard()
    _render_section_heading(
        "브리핑에서 바로 분석",
        "티커를 입력하거나 빠른 시작에서 선택하면 분석 모드로 전환되어 상세 분석을 이어갑니다.",
        badges=[
            ("오늘 미국장", "accent"),
            ("즉시 분석 전환", "warning"),
        ],
        eyebrow="Daily To Analysis",
        tight=True,
    )
    _render_quick_analysis_grid(key_prefix="briefing_quick")
    if ti := st.chat_input(CHAT_INPUT_PLACEHOLDER):
        parsed = _parse_analysis_ticker_input(ti)
        if not parsed:
            st.toast("분석할 티커를 입력해 주세요. 예: AAPL / 005930", icon="⌨️")
        else:
            if len(parsed) > 1:
                st.toast(f"{parsed[0]} 기준으로 먼저 분석합니다.", icon="📌")
            _queue_analysis_target(parsed[0])

# ══════════════════════════════════════════════════════════════
#  분석 모드
# ══════════════════════════════════════════════════════════════
else:
    _render_brand_board(main_board_payload, compact=True)
    _sanitize_session_messages()

    analysis_indices = [i for i, msg in enumerate(st.session_state.messages) if msg.get("type") == "analysis"]
    report_indices = [i for i, msg in enumerate(st.session_state.messages) if msg.get("type") == "report"]
    latest_analysis_idx = analysis_indices[-1] if analysis_indices else None
    latest_report_idx = report_indices[-1] if report_indices else None

    if analysis_indices:
        _render_section_heading(
            "Analysis Feed",
            "최신 분석과 생성된 리포트가 시간순으로 쌓이며, 가장 최근 분석이 기본으로 펼쳐집니다.",
            badges=[
                (f"분석 {len(analysis_indices)}건", "accent"),
                (f"리포트 {len(report_indices)}건", "warning"),
            ],
            eyebrow="Workspace",
            tight=True,
        )
    else:
        _render_section_heading(
            "Analysis Workspace",
            "티커를 입력하거나 빠른 시작을 눌러 개별 종목 분석을 시작하세요.",
            badges=[
                ("직접 입력", "accent"),
                ("AI SIGNAL-ASSISTED", "muted"),
            ],
            eyebrow="Workspace",
            tight=True,
        )

    if not st.session_state.last_ticker:
        _render_section_heading(
            "빠른 시작",
            "자주 보는 종목을 눌러 바로 분석할 수 있습니다.",
            badges=[
                ("즉시 분석", "accent"),
                ("입력창으로 다른 티커 가능", "muted"),
            ],
            eyebrow="Quick Actions",
            tight=bool(analysis_indices),
        )
        _render_quick_analysis_grid(key_prefix="analysis_quick")

    key_state = resolve_ai_key(
        st.session_state.get("runtime_gemini_api_key"),
        GEMINI_API_KEY,
        GEMINI_API_KEY_FROM_SECRETS,
    )
    active_gemini_key = key_state.active_key
    key_source = key_state.source
    if GEMINI_API_KEY_FROM_SECRETS and not st.session_state.get("show_runtime_gemini_key_setup", False):
        info_col, action_col = st.columns([3, 1])
        info_col.caption(f"현재 AI 키: {key_source} · {_mask_secret(active_gemini_key)}")
        if action_col.button("AI 키 변경", key="show_runtime_gemini_key_setup_btn", use_container_width=True):
            st.session_state["show_runtime_gemini_key_setup"] = True
            st.rerun()
    else:
        with st.expander("AI Key Setup", expanded=not bool(active_gemini_key)):
            st.caption("Gemini API 키를 여기서 직접 입력해 현재 세션에만 적용할 수 있습니다.")
            if GEMINI_API_KEY_FROM_SECRETS:
                st.caption("`.streamlit/secrets.toml` 키가 기본으로 적용되어 있으며, 아래 입력값은 현재 세션에서만 덮어씁니다.")
            st.text_input(
                "Gemini API Key",
                key="runtime_gemini_api_key_input",
                type="password",
                placeholder="AIza...",
                help="세션 입력값이 있으면 `.streamlit/secrets.toml`이나 환경변수보다 우선합니다.",
            )
            c1, c2 = st.columns(2)
            if c1.button("적용", key="apply_runtime_gemini_key", use_container_width=True):
                entered_key = str(st.session_state.get("runtime_gemini_api_key_input", "")).strip()
                if entered_key:
                    st.session_state["runtime_gemini_api_key"] = entered_key
                    st.toast("AI 키를 현재 세션에 적용했습니다.", icon="🔐")
                    st.rerun()
                st.warning("적용할 API 키를 먼저 입력해 주세요.")
            if c2.button("초기화", key="clear_runtime_gemini_key", use_container_width=True):
                st.session_state["runtime_gemini_api_key"] = ""
                st.session_state["runtime_gemini_api_key_input"] = ""
                st.toast("세션 API 키를 초기화했습니다.", icon="🧹")
                st.rerun()
            st.caption(f"현재 상태: {key_source} · {_mask_secret(active_gemini_key)}")
            st.caption("영구 저장을 원하면 `.streamlit/secrets.toml` 또는 `GOOGLE_API_KEY` 환경변수를 사용하면 됩니다.")

    for i, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            if msg.get("type") == "analysis":
                is_latest_analysis = i == latest_analysis_idx
                if is_latest_analysis:
                    render_analysis_message(msg, key_prefix=f"analysis_{i}_{msg.get('ticker', 'na')}")
                else:
                    with st.expander(f"{msg.get('ticker', '')} 지난 분석", expanded=False):
                        render_analysis_message(msg, key_prefix=f"analysis_{i}_{msg.get('ticker', 'na')}")
            elif msg.get("type") == "report":
                with st.expander(f"{msg.get('ticker', '')} AI SIGNAL-ASSISTED", expanded=i == latest_report_idx):
                    st.markdown(msg["content"])
                st.download_button(
                    "📥", key=f"dl_{i}",
                    data=msg["content"].encode('utf-8'),
                    file_name=f"{BRAND_REPORT_SLUG}_{msg.get('ticker', '').lower()}_{datetime.now().strftime('%Y%m%d')}.md",
                    mime="text/markdown",
                    use_container_width=True
                )
            else:
                st.markdown(msg.get("content", ""))
            if msg.get("prompt") and msg.get("type") == "analysis":
                with st.expander(f"{msg.get('ticker', '')} PROMPT TAPE"):
                    st.markdown(
                        "<div class='prompt-caption'>독립 AI Signal-Assisted 판단에 실제로 사용된 프롬프트입니다. 코드 블록 우측 상단 복사 아이콘을 사용하세요.</div>",
                        unsafe_allow_html=True,
                    )
                    st.code(msg["prompt"], language="markdown")
            if msg.get("ai_raw") and msg.get("type") == "analysis":
                with st.expander(f"{msg.get('ticker', '')} AI SIGNAL-ASSISTED RAW"):
                    st.code(msg["ai_raw"], language="json")

    def process_ticker(tv, refresh=False):
        raw_tv = str(tv or "").strip().upper()
        st.session_state.pending_ai_ticker = None
        st.session_state.pending_ai_prompt = None
        resolved = resolve_analysis_ticker(raw_tv)
        if not resolved.get("valid"):
            sample_text = "예: AAPL / 005930"
            if resolved.get("reason") == "format":
                st.toast(f"⚠️ 형식 오류 · {sample_text}", icon="🚨")
            else:
                st.toast(f"⚠️ {raw_tv} 티커를 찾을 수 없습니다 · {sample_text}", icon="🔍")
            return
        tv = str(resolved.get("resolved") or raw_tv).strip().upper()
        st.session_state.messages.append(_normalize_session_message({"role": "user", "type": "text", "content": raw_tv}))
        st.session_state.last_ticker = tv
        _set_scan_focus(tv)
        if resolved.get("auto_resolved"):
            st.toast(f"{raw_tv} → {tv} 로 해석해 분석합니다.", icon="📌")
        with st.chat_message("assistant"):
            with st.status(f"READING THE TAPE · {tv}", expanded=True) as status:
                if resolved.get("auto_resolved"):
                    st.write(f"0. 입력값을 `{raw_tv}` → `{tv}` 로 해석했습니다.")
                st.write("1. 입력 형식과 티커 유효성을 확인했습니다.")
                status.update(label=f"VALIDATING TARGET · {tv}", state="running", expanded=True)
                st.write("2. 가격 데이터와 객관 지표를 계산할 준비를 합니다.")
                status.update(label=f"DATA FEED ESTABLISHED · {tv}", state="running", expanded=True)
                st.write("3. 가격 데이터, 기술 지표, 시그널, 차트 메타데이터를 계산합니다.")
                fj, lab_fj, phist, meta, audit = analyze(tv, chart_days, refresh)
                if fj and meta:
                    act = meta.get('action_label', '')
                    es  = meta.get('ensemble_score', 0)
                    status.update(label=f"ASSEMBLING AI SIGNAL-ASSISTED · {tv}", state="running", expanded=True)
                    st.write("4. 독립 AI Signal-Assisted 프롬프트를 구성합니다.")
                    st.write(f"📍 {act} | ES {es:+.1f}")
                    _show_analysis_toasts(tv, meta)
                    prompt = build_ai_prompt(tv, phist)
                    st.write("5. 같은 데이터만 사용한 독립 AI 2차 의견을 생성합니다.")
                    ai_result = _generate_ai_signal_assisted(tv, prompt, meta.get("judgment", ""))
                    ai_raw = ai_result.pop("raw_text", "")
                    meta["ai_signal_assisted"] = ai_result
                    if ai_result.get("available"):
                        st.write(
                            f"🤖 {ai_result.get('AI_Judgment', 'NEUTRAL')} | "
                            f"신뢰도 {ai_result.get('AI_Confidence', 0)}% | "
                            f"{ai_result.get('AI_Agreement', 'ALIGNED')}"
                        )
                    else:
                        st.write(f"🤖 AI 보조 판단 미사용: {ai_result.get('AI_Reason', '')}")
                    st.write("6. 엔진 판단과 AI 판단을 함께 표시할 준비가 끝났습니다.")
                    status.update(label=f"SIGNAL READY · {tv} | {act}", state="complete", expanded=False)
                else:
                    prompt = None
                    ai_raw = ""
                    status.update(label=f"SIGNAL BUILD FAILED · {tv}", state="error")
            if fj:
                syn  = meta.get('reversal_synergy', 0)
                pred = meta.get('prediction_boost', 0)
                content = f"**{tv}** - **{meta.get('action_label', '')}**\n💬 {meta.get('judgment_reason', '')}"
                content += f"\n🏛️ ES:{es:+.1f} | B{meta.get('buy_agree',0)}:S{meta.get('sell_agree',0)} | 🌐{meta.get('context_label','')}"
                if abs(syn) > 5:  content += f" | 🔄{syn:+.1f}"
                if abs(pred) > 3: content += f" | 🔮{pred:+.1f}"
                if meta.get('combined_scans'):
                    content += f"\n🎯 CS:매수{sum(1 for s in meta['combined_scans'] if s['dir']=='buy')} 매도{sum(1 for s in meta['combined_scans'] if s['dir']=='sell')}"
                top_strategy = (meta.get('strategy_summary') or {}).get('top_strategy') or meta.get('top_strategy')
                if isinstance(top_strategy, dict) and top_strategy.get('label'):
                    entry_reference_text = _format_strategy_entry_reference(top_strategy)
                    entry_suffix = f" / {entry_reference_text}" if entry_reference_text else ""
                    status_text = _format_strategy_status(top_strategy.get('status'))
                    status_suffix = f" / 상태 {status_text}" if status_text else ""
                    content += (
                        f"\n🧭 전략:{top_strategy.get('label')} {float(top_strategy.get('score', 0) or 0):.0f}점"
                        f" / 충돌 {str((meta.get('strategy_summary') or {}).get('conflict_level', 'LOW'))}{status_suffix}{entry_suffix}"
                    )
                content += f"\n⏳ {meta['leading_verdict']} | 📊 {meta['lagging_verdict']}"
                veto = meta.get('veto_flags', '')
                if veto:
                    content += f"\n🚫 {veto}"
                ai_meta = meta.get("ai_signal_assisted", {})
                if ai_meta:
                    if ai_meta.get("available"):
                        content += (
                            f"\n🤖 AI:{ai_meta.get('AI_Judgment', 'NEUTRAL')} "
                            f"{ai_meta.get('AI_Confidence', 0)}% · {ai_meta.get('AI_Agreement', 'ALIGNED')}"
                        )
                    else:
                        content += "\n🤖 AI: 사용 불가"
                st.session_state.messages.append(_normalize_session_message({
                    "role": "assistant", "type": "analysis",
                    "ticker": tv, "content": content,
                    "analyzed_at": datetime.now().isoformat(timespec="seconds"),
                    "fig_json": fj, "indicator_lab_json": lab_fj, "meta": meta, "prompt": prompt, "audit": audit, "ai_raw": ai_raw,
                }))
                st.rerun()
            else:
                st.session_state.messages.append(_normalize_session_message({
                    "role": "assistant", "type": "text",
                    "content": f"⚠️ **{tv}** 분석 실패: {phist}"
                }))
                st.rerun()

    if st.session_state.get('_auto'):
        process_ticker(st.session_state.pop('_auto'))
    if st.session_state.get('quick'):
        process_ticker(st.session_state.pop('quick'))
    if ti := st.chat_input(CHAT_INPUT_PLACEHOLDER):
        parsed = _parse_analysis_ticker_input(ti)
        if not parsed:
            st.toast("분석할 티커를 입력해 주세요. 예: AAPL / 005930", icon="⌨️")
        else:
            if len(parsed) > 1:
                st.toast(f"{parsed[0]} 기준으로 먼저 분석합니다.", icon="📌")
            process_ticker(parsed[0])
