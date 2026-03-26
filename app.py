# ══════════════════════════════════════════════════════════════
#  SIGL — PART 1/4
#  설정, 레지스트리, 유틸리티, 기술지표
# ══════════════════════════════════════════════════════════════

import streamlit as st, google.generativeai as genai
import streamlit.components.v1 as components
import time, math, html
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from sectors import SECTOR_GROUPS
from config import GEMINI_API_KEY, COMBINED_SCAN_REGISTRY, CTX_KOR
from utils import _valid_fmt, _sf, fetch_fundamentals, validate_ticker, compute_and_cache, _compute_cached
from chart import build_chart, build_metadata
from ui_localized import render_analysis
from ai_agent import build_prompt_text, build_ai_prompt
from localization import (
    localize_action_label,
    localize_combo,
    localize_context_label,
    localize_judgment_label,
)
from branding import (
    BRAND_NAME,
    BRAND_PAGE_ICON,
    BRAND_PAGE_TITLE,
    BRAND_REPORT_SLUG,
    INITIAL_MESSAGE_CONTENT,
    build_brand_board,
)
from theme import build_app_theme_css
st.set_page_config(page_title=BRAND_PAGE_TITLE, page_icon=BRAND_PAGE_ICON, layout="wide", initial_sidebar_state="collapsed")

# ━━━ CSS ━━━
st.markdown(build_app_theme_css(), unsafe_allow_html=True)

INITIAL_MESSAGE = {
    "role": "assistant",
    "type": "text",
    "content": INITIAL_MESSAGE_CONTENT,
}


# ━━━ Constants ━━━
@st.cache_resource
def get_gemini_model():
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
    return genai.GenerativeModel('gemini-flash-latest')

def analyze(ticker, chart_days=252, refresh=False):
    try:
        ts = int(time.time()) if refresh else None
        df = compute_and_cache(ticker, ts)
        if df is None or df.empty or len(df) < 50:
            return None, "데이터 부족", None
        dc = df.dropna(subset=['WT1', 'WT2']).tail(chart_days).copy()
        if dc.empty:
            return None, "차트 데이터 부족", None
        meta = build_metadata(dc, ticker)
        return build_chart(dc, ticker).to_json(), build_prompt_text(dc, meta), meta
    except Exception as e:
        import traceback
        print(f"[ERR]{ticker}:\n{traceback.format_exc()}")
        return None, f"분석 실패: {e}", None


def _initial_messages():
    return [dict(INITIAL_MESSAGE)]

# ━━━ Session + Main ━━━
def init_session():
    defs = {
        '_mode': '분석',
        '_auto': None,
        'quick': None,
        'messages': _initial_messages(),
        'pending_ai_ticker': None,
        'pending_ai_prompt': None,
        'last_ticker': None,
        'scan_results': [],
        'scan_source': '',
        'scan_total': 0,
        'scan_focus_idx': None,
        'scan_focus_ticker': None,
        'scan_nav_select_idx': None,
        'selected_sector': None,
        'scan_tickers_override': None,
    }
    for k, v in defs.items():
        if k not in st.session_state:
            st.session_state[k] = v


def reset_session():
    st.session_state['_mode'] = '분석'
    st.session_state['_auto'] = None
    st.session_state['quick'] = None
    st.session_state['messages'] = _initial_messages()
    st.session_state['pending_ai_ticker'] = None
    st.session_state['pending_ai_prompt'] = None
    st.session_state['last_ticker'] = None
    st.session_state['scan_results'] = []
    st.session_state['scan_source'] = ''
    st.session_state['scan_total'] = 0
    st.session_state['scan_focus_idx'] = None
    st.session_state['scan_focus_ticker'] = None
    st.session_state['scan_nav_select_idx'] = None
    st.session_state['selected_sector'] = None
    st.session_state['scan_tickers_override'] = None

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
    st.session_state['_mode'] = '분석'
    st.session_state['_auto'] = ticker
    st.rerun()

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
        st.session_state['_mode'] = '스캐너'
        st.rerun()

def _show_analysis_toasts(ticker, meta):
    judgment = str(meta.get('judgment', 'NEUTRAL'))
    action = str(meta.get('action_label', '')).strip() or localize_judgment_label(judgment)
    ensemble = float(meta.get('ensemble_score', 0))
    primary_icon = '🟢' if 'BUY' in judgment else ('🔴' if 'SELL' in judgment else '🟡')
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


def _sigl_badge(label, tone='muted'):
    safe = html.escape(str(label or '').strip())
    if not safe:
        return ""
    return f"<span class='sigl-badge sigl-badge--{tone}'>{safe}</span>"


def _render_scanner_selection_panel(selected_sector, selected_list):
    if not selected_sector:
        return
    count = len(selected_list)
    chips = "".join(
        f"<span class='sigl-code-chip'>{html.escape(str(t))}</span>"
        for t in selected_list
    ) or "<span class='sigl-empty'>선택된 종목이 없습니다.</span>"
    st.markdown(
        f"""
        <div class="sigl-card sigl-card--accent">
            <div class="sigl-page-head">
                <div>
                    <p class="sigl-page-head__eyebrow">Scanner Scope</p>
                    <p class="sigl-page-head__title">{html.escape(str(selected_sector))}</p>
                    <p class="sigl-page-head__copy">현재 스캔 범위와 티커 구성을 한눈에 확인할 수 있습니다.</p>
                </div>
                <div class="sigl-inline">
                    {_sigl_badge(f'{count} 종목', 'accent')}
                    {_sigl_badge('점수 높은 순 정렬', 'muted')}
                </div>
            </div>
            <div class="sigl-code-list">{chips}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_scanner_summary(results, total_count):
    buy_count = len([r for r in results if 'BUY' in str(r.get('jg_key', ''))])
    sell_count = len([r for r in results if 'SELL' in str(r.get('jg_key', ''))])
    cards = [
        ("매수 후보", str(buy_count), "판단이 BUY 계열인 종목 수", "positive"),
        ("매도 후보", str(sell_count), "판단이 SELL 계열인 종목 수", "negative"),
        ("매치 수", f"{len(results)}/{total_count}", "전체 스캔 대상 대비 현재 결과", "accent"),
    ]
    html_cards = "".join(
        f"""
        <div class="sigl-metric-card">
            <p class="sigl-metric-label">{html.escape(label)}</p>
            <p class="sigl-metric-value">{html.escape(value)}</p>
            <p class="sigl-metric-sub">{html.escape(sub)}</p>
        </div>
        """
        for label, value, sub, _tone in cards
    )
    st.markdown(f"<div class='sigl-result-summary'>{html_cards}</div>", unsafe_allow_html=True)


def _render_scanner_result_card(rank, row):
    judgment_key = str(row.get('jg_key', ''))
    judgment_label = str(row.get('jg', 'N/A'))
    action_label = str(row.get('action', '')).strip()
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
    reason_html = ""
    if row.get('reason'):
        reason_html = f"<p class='sigl-summary'>{html.escape(str(row['reason'])[:120])}</p>"
    change_prefix = "+" if float(row.get('chg', 0) or 0) >= 0 else ""
    st.markdown(
        f"""
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
            <div class="sigl-chip-row">{combo_hits}</div>
            {reason_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

def _format_board_text(value, fallback="--"):
    text = str(value).strip() if value is not None else ""
    return text or fallback

def _format_board_code(value, fallback="--"):
    return _format_board_text(value, fallback).upper()

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
    recent = list(meta.get('recent_signals') or [])
    if recent:
        return _format_board_text(recent[-1][1], fallback)
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
    recent = list(meta.get('recent_signals') or [])
    if recent:
        return _format_board_text(recent[-1][3], fallback).lower()
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

    for icon, label, _date, direction, _is_combined in reversed(list(meta.get('recent_signals') or [])[-limit:]):
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
    recent = list((meta or {}).get('recent_signals') or [])
    for icon, label, date, direction, is_combined in reversed(recent[-limit:]):
        items.append({
            'icon': _format_board_text(icon, '•'),
            'label': _format_board_text(label, 'NO SIGNAL'),
            'date': _format_board_text(date, '--/--'),
            'dir': _format_board_text(direction, 'neutral').lower(),
            'is_combined': bool(is_combined),
        })
    return items

def _focus_recent_signals_from_scan(focus_row, limit=5):
    if not focus_row:
        return []
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
    mode_label = 'SCANNER' if current_mode == '스캐너' else 'ANALYSIS'
    period_label = _short_period_label(chart_period)
    analysis_messages = _analysis_messages()
    analysis_count = len(analysis_messages)
    history_rows = _history_rows_from_messages(analysis_messages, limit=8)

    if current_mode == '스캐너':
        results = st.session_state.get('scan_results', [])
        focus_idx = st.session_state.get('scan_focus_idx')
        focus_row = None
        if results:
            if isinstance(focus_idx, int) and 0 <= focus_idx < len(results):
                focus_row = results[focus_idx]
            else:
                focus_row = results[0]

        selected_sector = _format_board_text(st.session_state.get('selected_sector'), fallback='READY')
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
    height = 230 if compact else 255
    components.html(build_brand_board(payload, compact=compact), height=height, scrolling=False)
    if not compact:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

with st.sidebar:
    _mi = 0 if st.session_state.get('_mode', '분석') == '분석' else 1
    app_mode = st.radio("모드", ['분석', '스캐너'], index=_mi)
    st.session_state['_mode'] = app_mode
    chart_period = st.radio("기간", ['3개월', '6개월', '1년', '2년'], index=1, horizontal=True, key="period")
    chart_days = {'3개월': 63, '6개월': 126, '1년': 252, '2년': 504}[chart_period]
    st.markdown("---")
    if st.button("🗑️ 초기화", use_container_width=True, type="secondary"):
        reset_session()
        st.rerun()

    if st.session_state.get('_mode', '분석') == '분석':
        _render_analysis_sidebar_nav()

current_mode = st.session_state.get('_mode', '분석')
main_board_payload = _build_brand_payload(current_mode, chart_period)

# ══════════════════════════════════════════════════════════════
#  스캐너 모드
# ══════════════════════════════════════════════════════════════
if current_mode == '스캐너':
    _render_brand_board(main_board_payload)
    all_universe = sorted({str(t).strip().upper() for ts in SECTOR_GROUPS.values() for t in ts if str(t).strip()})

    st.markdown("#### 📂 섹터 선택")
    sector_names = list(SECTOR_GROUPS.keys())
    selected_sector = st.session_state.get('selected_sector', None)
    for rs in range(0, len(sector_names), 3):
        ri = sector_names[rs:rs + 3]
        cols = st.columns(3)
        for i, sn in enumerate(ri):
            with cols[i]:
                if st.button(f"{sn}\n({len(SECTOR_GROUPS[sn])})", key=f"sec_{rs+i}", use_container_width=True,
                             type="primary" if selected_sector == sn else "secondary"):
                    st.session_state['selected_sector'] = sn
                    st.session_state['scan_tickers_override'] = SECTOR_GROUPS[sn]
                    st.rerun()
    if st.button(f"🌐 전체종목\n({len(all_universe)})", key="sec_all", use_container_width=True,
                 type="primary" if selected_sector == '🌐 전체' else "secondary"):
        st.session_state['selected_sector'] = '🌐 전체'
        st.session_state['scan_tickers_override'] = all_universe
        st.rerun()

    if selected_sector:
        sel_list = st.session_state.get('scan_tickers_override', []) if selected_sector == '🌐 전체' else SECTOR_GROUPS.get(selected_sector, [])
        sel_list = list(dict.fromkeys([str(t).strip().upper() for t in sel_list if str(t).strip()]))
        _render_scanner_selection_panel(selected_sector, sel_list)

    st.markdown("#### ✏️ 직접 입력")
    ci = st.text_input("티커", placeholder="NVDA,TSLA...", key="scan_in")
    if ci and ci.strip():
        tickers = [t.strip().upper() for t in ci.split(',') if t.strip()]
        scan_source = "직접"
    elif st.session_state.get('scan_tickers_override'):
        tickers = st.session_state['scan_tickers_override']
        scan_source = selected_sector or "섹터"
    else:
        tickers = []
        scan_source = "직접"
    tickers = list(dict.fromkeys([t for t in tickers if t]))

    cb1, cb2 = st.columns([3, 1])
    with cb1:
        scan_btn = st.button(f"🚀 스캔({len(tickers)})", type="primary", use_container_width=True)
    with cb2:
        if st.button("🗑️", use_container_width=True, key="sr"):
            st.session_state.pop('selected_sector', None)
            st.session_state.pop('scan_tickers_override', None)
            st.session_state['scan_results'] = []
            st.session_state['scan_source'] = ''
            st.session_state['scan_total'] = 0
            st.session_state['scan_focus_idx'] = None
            st.session_state['scan_focus_ticker'] = None
            st.session_state['scan_nav_select_idx'] = None
            st.rerun()

    if scan_btn and not tickers:
        st.warning("스캔할 티커가 없습니다. 섹터를 고르거나 직접 티커를 입력해 주세요.")

    if scan_btn and tickers:
        pb = st.progress(0)
        scan_note = st.empty()
        results = []
        sts = math.floor(time.time() / 300)

        # 런타임 콤보 레지스트리 등록 보장
        try:
            from engine import _ensure_runtime_combo_registry
            _ensure_runtime_combo_registry()
        except Exception:
            pass

        # UT/Hull 전환 시그널 표시용 설정
        trans_cfg = {
            'UTBot_Buy':      {'label': 'UTBot 전환▲', 'icon': '🟢', 'dir': 'buy'},
            'UTBot_Sell':     {'label': 'UTBot 전환▼', 'icon': '🔴', 'dir': 'sell'},
            'Hull_Turn_Bull': {'label': 'HULL 전환▲',  'icon': '🟢', 'dir': 'buy'},
            'Hull_Turn_Bear': {'label': 'HULL 전환▼',  'icon': '🔴', 'dir': 'sell'},
        }

        def _so(t):
            """
            스캐너 단일 종목 분석.

            [설계 원칙]
            - acs 루프: 최근 5일 이내 발화 콤보 수집 → 카드 날짜·표시 전용
            - multi-signal badge 수치(ON/OFF, 개수, B/S/N 분류):
              engine.py detect_combined_scans()가 미리 계산한 컬럼을 단독 사용.
              스캐너에서 재계산하지 않으므로 이중 계산 없음.
            - scan_score의 t1b/t2b 가중치: 5일 윈도우 acs 기반 유지
              (최근 활동도를 랭킹에 반영하는 의도적 설계)
            """
            try:
                df_ = _compute_cached(t, f"{t}_{sts}")
                if df_ is None or len(df_) < 50:
                    return None

                dc_ = df_.tail(63)
                lt = dc_.iloc[-1]   # 마지막 행 (오늘)

                # ── 1. 표시용: 최근 5일 발화 콤보 카드 수집 ──────────────────
                acs = []
                lsd = None  # 가장 최근 발화일
                for cn, ccfg in COMBINED_SCAN_REGISTRY.items():
                    if cn in dc_.columns and dc_[cn].tail(5).any():
                        ld = dc_[cn].tail(5)[dc_[cn].tail(5)].index[-1]
                        combo_kor, _ = localize_combo(cn, ccfg.get('kor'), ccfg.get('desc'))
                        acs.append({
                            'icon':     ccfg['icon'],
                            'kor':      combo_kor,
                            'dir':      ccfg['dir'],
                            'tier':     ccfg['tier'],
                            'date':     ld.strftime('%m/%d'),
                            'days_ago': int((dc_.index[-1] - ld).days),
                        })
                        lsd = ld if lsd is None or ld > lsd else lsd

                # ── 2. 표시용: UT/Hull 전환 수집 ──────────────────────────────
                trs = []
                for sn, cfg in trans_cfg.items():
                    if sn in dc_.columns and dc_[sn].tail(5).any():
                        td = dc_[sn].tail(5)[dc_[sn].tail(5)].index[-1]
                        trs.append({
                            'icon':  cfg['icon'],
                            'label': cfg['label'],
                            'dir':   cfg['dir'],
                            'date':  td.strftime('%m/%d'),
                        })

                # ── 3. 기본 지표 수치 ──────────────────────────────────────────
                chv = _sf(lt['Close'] - dc_.iloc[-2]['Close']) if len(dc_) >= 2 else 0
                ch  = _sf((lt['Close'] - dc_.iloc[-2]['Close']) / dc_.iloc[-2]['Close'] * 100) if len(dc_) >= 2 else 0
                bt  = _sf(lt.get('Buy_Total', 0))
                stt = _sf(lt.get('Sell_Total', 0))
                ba  = int(_sf(lt.get('Buy_Agree', 0)))
                sa  = int(_sf(lt.get('Sell_Agree', 0)))
                es  = _sf(lt.get('Ensemble_Score', 0))
                cf  = _sf(lt.get('Judgment_Confidence', 0))

                # ── 4. scan_score: acs 기반 tier 가중치 유지 (5일 활동도 반영) ─
                t1b = sum(1 for s in acs if s['tier'] == 1 and s['dir'] == 'buy')
                t1s = sum(1 for s in acs if s['tier'] == 1 and s['dir'] == 'sell')
                t2b = sum(1 for s in acs if s['tier'] == 2 and s['dir'] == 'buy')
                t2s = sum(1 for s in acs if s['tier'] == 2 and s['dir'] == 'sell')
                scan_score = (
                    es
                    + (bt - stt) * 0.55
                    + (ba - sa)  * 2.5
                    + t1b * 4.0  - t1s * 4.0
                    + t2b * 1.6  - t2s * 1.6
                    + cf  * 0.04
                )
                strength = (
                    abs(es)
                    + (bt + stt) * 0.35
                    + abs(ba - sa) * 1.8
                    + (t1b + t1s)  * 3.0
                    + cf * 0.02
                )

                # ── 5. Multi-Signal badge: acs 기반 (5일 윈도우) ──────────────
                #   엔진의 CS_Multi_Count 는 오늘 하루 기준이므로
                #   표시 중인 acs (최근 5일) 와 숫자가 불일치함.
                #   화면에 보이는 시그널 목록과 배지 카운트를 일치시키기 위해
                #   acs 를 직접 집계하는 것으로 통일.
                mbc   = sum(1 for s in acs if s['dir'] == 'buy')
                msc   = sum(1 for s in acs if s['dir'] == 'sell')
                mnc   = sum(1 for s in acs if s['dir'] == 'neutral')
                mcnt  = len(acs)
                mimb  = mbc - msc
                # ON 조건: tier-1 이상 1개 이상이면서 총 2개↑, 또는 총 3개↑
                has_t1 = any(s['tier'] == 1 for s in acs)
                mflag  = (mcnt >= 3) or (has_t1 and mcnt >= 2)

                # ── 6. multi_hits: 최근 3일 이내 발화 콤보 (표시용, acs 기반) ──
                recent = sorted(
                    [x for x in acs if x.get('days_ago', 99) <= 3],
                    key=lambda x: (x.get('tier', 9), x.get('days_ago', 99))
                )
                mhits = [{'icon': h['icon'], 'label': h['kor'], 'dir': h['dir'], 'date': h['date']} for h in recent]
                # 최근 3일 없으면 전체 acs 상위 6개로 폴백
                if not mhits:
                    fallback = sorted(acs, key=lambda x: (x.get('tier', 9), x.get('days_ago', 99)))[:6]
                    mhits = [{'icon': h['icon'], 'label': h['kor'], 'dir': h['dir'], 'date': h['date']} for h in fallback]

                raw_jg = str(lt.get('Trade_Judgment', 'N/A'))
                return {
                    'ticker':       t,
                    'price':        _sf(lt['Close']),
                    'chg_value':    chv,
                    'chg':          ch,
                    'scans':        sorted(acs, key=lambda x: x['tier']),
                    'transitions':  trs,
                    # badge (엔진 단독)
                    'multi_sig':    mflag,
                    'multi_cnt':    mcnt,
                    'multi_buy':    mbc,
                    'multi_sell':   msc,
                    'multi_neutral': mnc,
                    'multi_imb':    mimb,
                    # 표시용 최근 콤보
                    'multi_hits':   mhits,
                    # 판단
                    'jg_key':       raw_jg,
                    'jg':           localize_judgment_label(raw_jg),
                    'cf':           cf,
                    'es':           es,
                    'ctx':          localize_context_label(int(_sf(lt.get('Market_Context', 0)))),
                    'ba':           ba,
                    'sa':           sa,
                    'buy_total':    bt,
                    'sell_total':   stt,
                    'scan_score':   _sf(scan_score),
                    'strength':     _sf(strength),
                    'latest_sig':   lsd.strftime('%Y-%m-%d') if lsd else '9999-99-99',
                    'latest_sig_ts': lsd.timestamp() if lsd else 0.0,
                    'reason':       str(lt.get('Judgment_Reason', '')),
                    'action':       localize_action_label(str(lt.get('Action_Label', ''))),
                }
            except Exception:
                return None

        with st.status(f"MARKET SWEEP ACTIVE · {len(tickers)} TICKERS", expanded=True) as scan_status:
            scan_note.caption("1/3 시그널 레지스트리와 캐시 상태를 확인했습니다.")

            # 병렬 스캔 실행
            scan_note.caption("2/3 병렬 스캔을 시작합니다. 최근 완료 종목이 아래에 표시됩니다.")
            with ThreadPoolExecutor(max_workers=min(16, max(4, len(tickers) // 8), len(tickers))) as ex:
                futs = {ex.submit(_so, t): t for t in tickers}
                for idx_f, f in enumerate(as_completed(futs)):
                    done_ticker = futs[f]
                    pb.progress((idx_f + 1) / len(tickers))
                    scan_note.caption(f"READING THE TAPE · {done_ticker} · {idx_f + 1}/{len(tickers)}")
                    r = f.result()
                    if r:
                        results.append(r)
            scan_note.caption("3/3 결과를 정렬하고 스캐너 카드를 준비합니다.")
            scan_status.update(label=f"SCAN BOOK READY · {len(results)} MATCHES", state="complete", expanded=False)
        pb.empty()
        scan_note.empty()

        results.sort(key=lambda x: (-x['scan_score'], -x['strength'], -x['latest_sig_ts'], x['ticker']))
        st.session_state['scan_results'] = results
        st.session_state['scan_source']  = scan_source
        st.session_state['scan_total']   = len(tickers)
        st.session_state['scan_focus_idx'] = 0 if results else None
        st.session_state['scan_focus_ticker'] = results[0]['ticker'] if results else None
        st.session_state['scan_nav_select_idx'] = 0 if results else None

    # ── 결과 렌더링 ──────────────────────────────────────────────────────────
    results = st.session_state.get('scan_results', [])
    if results:
        scan_total = st.session_state.get('scan_total', 0)
        st.caption("정렬 기준: 스캔 점수 → 강도 → 최근 시그널 순서입니다.")
        _render_scanner_summary(results, scan_total)

        for rk, r in enumerate(results, start=1):
            _render_scanner_result_card(rk, r)

            if st.button(f"{r['ticker']} 분석", key=f"sc_{r['ticker']}", use_container_width=True):
                _set_scan_focus(r['ticker'], rk - 1)
                st.session_state['_mode'] = '분석'
                st.session_state['_auto'] = r['ticker']
                st.rerun()

# ══════════════════════════════════════════════════════════════
#  분석 모드
# ══════════════════════════════════════════════════════════════
else:
    _render_brand_board(main_board_payload)

    if not st.session_state.last_ticker:
        cols = st.columns(4)
        for i, t in enumerate(["NVDA", "TSLA", "AAPL", "QQQ"]):
            with cols[i]:
                if st.button(t, use_container_width=True):
                    st.session_state['quick'] = t

    analysis_indices = [i for i, msg in enumerate(st.session_state.messages) if msg.get("type") == "analysis"]
    report_indices = [i for i, msg in enumerate(st.session_state.messages) if msg.get("type") == "report"]
    latest_analysis_idx = analysis_indices[-1] if analysis_indices else None
    latest_report_idx = report_indices[-1] if report_indices else None

    for i, msg in enumerate(st.session_state.messages):
        av = "✨" if msg["role"] == "assistant" else "🧑‍💻"
        with st.chat_message(msg["role"], avatar=av):
            if msg.get("type") == "analysis":
                is_latest_analysis = i == latest_analysis_idx
                if is_latest_analysis:
                    render_analysis(msg, key_prefix=f"analysis_{i}_{msg.get('ticker', 'na')}")
                else:
                    with st.expander(f"{msg.get('ticker', '')} 지난 분석", expanded=False):
                        render_analysis(msg, key_prefix=f"analysis_{i}_{msg.get('ticker', 'na')}")
            elif msg.get("type") == "report":
                with st.expander(f"{msg.get('ticker', '')} QUANT AUDIT", expanded=i == latest_report_idx):
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
                        "<div class='prompt-caption'>QUANT AUDIT에 실제로 사용된 프롬프트입니다. 코드 블록 우측 상단 복사 아이콘을 사용하세요.</div>",
                        unsafe_allow_html=True,
                    )
                    st.code(msg["prompt"], language="markdown")

    def _run_ai():
        tp = st.session_state.pending_ai_ticker
        pp = st.session_state.pending_ai_prompt
        with st.chat_message("assistant", avatar="✨"):
            pb = st.progress(0)
            ai_note = st.empty()
            try:
                model = get_gemini_model()
                pb.progress(12)
                ai_note.caption("1/3 QUANT AUDIT 엔진을 준비하고 있습니다.")
                col_ = []

                def gen():
                    pb.progress(32)
                    ai_note.caption("2/3 QUANT AUDIT 초안을 생성하고 있습니다. 종목과 시장 컨텍스트를 함께 요약합니다.")
                    for ch in model.generate_content(pp, stream=True):
                        if ch.text:
                            col_.append(ch.text)
                            yield ch.text
                    pb.progress(88)
                    ai_note.caption("3/3 문장을 정리하고 화면에 반영합니다.")
                    pb.progress(100)

                with st.expander(f"{tp.upper()} QUANT AUDIT", expanded=True):
                    st.write_stream(gen())
                time.sleep(.3)
                pb.empty()
                ai_note.empty()
                st.session_state.messages.append({
                    "role": "assistant", "type": "report",
                    "ticker": tp.upper(), "content": "".join(col_)
                })
                st.session_state.pending_ai_ticker = None
                st.session_state.pending_ai_prompt = None
                st.rerun()
            except Exception as e:
                pb.empty()
                ai_note.empty()
                st.error(f"AI 오류: {e}")

    def process_ticker(tv, refresh=False):
        tv = tv.strip().upper()
        st.session_state.pending_ai_ticker = None
        st.session_state.pending_ai_prompt = None
        if not _valid_fmt(tv):
            st.toast(f"⚠️ {tv} 형식 오류", icon="🚨")
            return
        if not validate_ticker(tv):
            st.toast(f"⚠️ {tv} 티커를 찾을 수 없습니다", icon="🔍")
            return
        st.session_state.messages.append({"role": "user", "type": "text", "content": tv})
        st.session_state.last_ticker = tv
        _set_scan_focus(tv)
        with st.chat_message("assistant", avatar="✨"):
            with st.status(f"READING THE TAPE · {tv}", expanded=True) as status:
                st.write("1. 입력 형식과 티커 유효성을 확인했습니다.")
                status.update(label=f"VALIDATING TARGET · {tv}", state="running", expanded=True)
                st.write("2. 기업 기본 정보와 부가 메타데이터를 불러오고 있습니다.")
                fund = fetch_fundamentals(tv)
                status.update(label=f"DATA FEED ESTABLISHED · {tv}", state="running", expanded=True)
                st.write("3. 가격 데이터, 기술 지표, 위원회 점수, 차트 메타데이터를 계산합니다.")
                fj, phist, meta = analyze(tv, chart_days, refresh)
                if fj and meta:
                    act = meta.get('action_label', '')
                    es  = meta.get('ensemble_score', 0)
                    status.update(label=f"ASSEMBLING QUANT AUDIT · {tv}", state="running", expanded=True)
                    st.write("4. QUANT AUDIT용 프롬프트와 화면 카드 요약을 구성합니다.")
                    st.write(f"📍 {act} | ES {es:+.1f}")
                    _show_analysis_toasts(tv, meta)
                    prompt = build_ai_prompt(tv, phist, fund)
                    st.write("5. 분석 카드와 리포트 버튼을 표시할 준비가 끝났습니다.")
                    status.update(label=f"SIGNAL READY · {tv} | {act}", state="complete", expanded=False)
                else:
                    prompt = None
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
                content += f"\n⏳ {meta['leading_verdict']} | 📊 {meta['lagging_verdict']}"
                veto = meta.get('veto_flags', '')
                if veto:
                    content += f"\n🚫 {veto}"
                st.session_state.messages.append({
                    "role": "assistant", "type": "analysis",
                    "ticker": tv, "content": content,
                    "analyzed_at": datetime.now().isoformat(timespec="seconds"),
                    "fig_json": fj, "meta": meta, "prompt": prompt,
                })
                st.session_state.pending_ai_ticker = tv
                st.session_state.pending_ai_prompt = prompt
                st.rerun()
            else:
                st.session_state.messages.append({
                    "role": "assistant", "type": "text",
                    "content": f"⚠️ **{tv}** 분석 실패: {phist}"
                })
                st.rerun()

    if st.session_state.get('_auto'):
        process_ticker(st.session_state.pop('_auto'))
    if st.session_state.get('quick'):
        process_ticker(st.session_state.pop('quick'))
    if st.session_state.pending_ai_ticker and st.session_state.pending_ai_prompt:
        st.caption("QUANT AUDIT는 보통 10~20초 정도 걸립니다. 시스템 판단 요약과 반론 포인트를 함께 정리합니다.")
        if st.button(f"🚀 {st.session_state.pending_ai_ticker.upper()} QUANT AUDIT", type="primary", use_container_width=True):
            _run_ai()
    if ti := st.chat_input("SELECT TARGET TICKER (예: TSLA, AAPL, QQQ)"):
        process_ticker(ti)
