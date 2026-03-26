# ══════════════════════════════════════════════════════════════
#  SIGL — PART 1/4
#  설정, 레지스트리, 유틸리티, 기술지표
# ══════════════════════════════════════════════════════════════

import streamlit as st, google.generativeai as genai
import streamlit.components.v1 as components
import time, math
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
st.set_page_config(page_title=BRAND_PAGE_TITLE, page_icon=BRAND_PAGE_ICON, layout="wide", initial_sidebar_state="collapsed")

# ━━━ CSS ━━━
st.markdown("""<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
html,body,[class*="css"]{font-family:'Pretendard',sans-serif!important}
.stApp{background-color:#0B0E14}
p,li{color:#E8ECF1!important} h1,h2{color:#FFF!important;font-weight:800!important}
h3{color:#F0F4F8!important;font-weight:700!important}
h4{color:#CBD5E1!important;font-weight:600!important;font-size:1rem!important}
.block-container{padding-top:1rem!important;max-width:1400px}
div.stButton>button[kind="primary"]{background:linear-gradient(135deg,#6366F1,#8B5CF6)!important;color:#fff!important;border:none!important;border-radius:12px!important;font-weight:700!important;width:100%}
div.stButton>button[kind="secondary"]{background-color:#12161F!important;color:#C4CDD8!important;border:1px solid #2A3040!important;border-radius:12px!important;width:100%}
.price-header{background:linear-gradient(160deg,#0F1320,#141926);border:1px solid #1C2233;border-radius:16px;padding:20px 24px;margin-bottom:18px}
.price-big{font-size:2.2rem;font-weight:800;margin:0}
.price-change-up{color:#63D9A2!important} .price-change-down{color:#FF8F96!important}
.ind-mini{display:inline-block;padding:4px 10px;margin:2px;border-radius:8px;font-size:.76rem;font-weight:600}
.ind-b{background:rgba(99,217,162,.16);color:#B8F1D5}
.ind-s{background:rgba(255,143,150,.16);color:#FFD2D7}
.ind-n{background:rgba(246,195,94,.14);color:#F8DE9A}
.layer-row{display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid rgba(255,255,255,.04)}
.layer-bar{background:#151921;border-radius:4px;height:8px;flex:1;margin:0 8px;overflow:hidden}
.layer-fill-b{height:8px;border-radius:4px;background:linear-gradient(90deg,#247A55,#63D9A2)}
.layer-fill-s{height:8px;border-radius:4px;background:linear-gradient(90deg,#B85B65,#FF8F96)}
.score-card{border-radius:14px;padding:20px;text-align:center;position:relative;overflow:hidden}
.score-card-buy{background:linear-gradient(160deg,#0E261D,#101C24);border:1px solid rgba(99,217,162,.26)}
.score-card-sell{background:linear-gradient(160deg,#281518,#16131B);border:1px solid rgba(255,143,150,.26)}
.score-card-neutral{background:linear-gradient(160deg,#21180B,#19160F);border:1px solid rgba(246,195,94,.22)}
.fade-up{animation:fadeUp .35s ease both}
@keyframes fadeUp{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
.conf-ring{position:relative;width:80px;height:80px;display:inline-block}
.conf-ring svg{width:80px;height:80px;transform:rotate(-90deg)}
.ring-bg{fill:none;stroke:rgba(148,163,184,.2);stroke-width:8}
.ring-fg{fill:none;stroke-width:8;stroke-linecap:round}
.ring-text{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:.92rem;font-weight:800}
.vote-dot{width:8px;height:8px;border-radius:999px;display:inline-block}
.vote-dot.buy{background:#63D9A2;box-shadow:0 0 7px rgba(99,217,162,.58)}
.vote-dot.sell{background:#FF8F96;box-shadow:0 0 7px rgba(255,143,150,.58)}
.vote-dot.neutral{background:#F6C35E;box-shadow:0 0 7px rgba(246,195,94,.48)}
.vote-dot.abstain{background:#64748B}
.cm-card{background:rgba(255,255,255,.03);border:1px solid rgba(148,163,184,.12);border-radius:10px;padding:10px}
.cm-name{color:#94A3B8;font-size:.7rem;font-weight:700;margin:0 0 4px}
.cm-score{font-size:1.15rem;font-weight:800;margin:0 0 6px}
.cm-vote{display:inline-block;padding:2px 8px;border-radius:999px;font-size:.65rem;font-weight:700}
.cm-mini-bar{height:4px;background:rgba(148,163,184,.18);border-radius:999px;overflow:hidden;margin-top:6px}
.cm-mini-fill{height:100%;border-radius:999px}
.tow-bar{position:relative;height:14px;border-radius:999px;background:rgba(148,163,184,.15);overflow:hidden}
.tow-buy{position:absolute;right:50%;top:0;bottom:0;background:linear-gradient(90deg,#237650,#63D9A2)}
.tow-sell{position:absolute;left:50%;top:0;bottom:0;background:linear-gradient(90deg,#FF8F96,#8A4B54)}
.tow-center{position:absolute;left:50%;top:0;bottom:0;width:1px;background:rgba(226,232,240,.55)}
.stat-mini{background:rgba(255,255,255,.025);border:1px solid rgba(148,163,184,.16);border-radius:10px;padding:10px 8px;text-align:center;min-height:78px;display:flex;flex-direction:column;justify-content:center}
.sm-label{color:#64748B;font-size:.66rem;font-weight:700;margin:0 0 4px}
.sm-value{color:#E2E8F0;font-size:1rem;font-weight:800;margin:0}
.cs-card{border-radius:10px;padding:10px 14px;margin:5px 0;border-left:4px solid}
.reason-card{background:rgba(255,255,255,.04);border-radius:10px;padding:12px 16px;margin-top:12px;text-align:left}
div[data-baseweb="select"]>div{background-color:#12161F!important;border-color:#2A3040!important;color:#E8ECF1!important}
div[data-baseweb="popover"] ul{background-color:#FFFFFF!important;border-radius:10px!important}
div[data-baseweb="popover"] li{color:#1E293B!important}
div[data-testid="stRadio"] label p{color:#CBD5E1!important}
div[data-testid="stTextInput"] input{background-color:#12161F!important;border-color:#2A3040!important;color:#E8ECF1!important}
div[data-testid="stTabs"] button{color:#64748B!important;font-weight:700!important;border-bottom:3px solid transparent!important}
div[data-testid="stTabs"] button[aria-selected="true"]{color:#A5B4FC!important;border-bottom-color:#6366F1!important}
section[data-testid="stSidebar"]{background-color:#080A10;border-right:1px solid #151921}
header{background-color:transparent!important}
div[data-testid="stMetricValue"]{color:#F8FAFC!important}
::-webkit-scrollbar{width:6px} ::-webkit-scrollbar-track{background:#0B0E14} ::-webkit-scrollbar-thumb{background:#2A3040;border-radius:3px}
div[data-testid="stToastContainer"]{top:4.75rem!important}
div[data-testid="stToast"]{background:linear-gradient(160deg,rgba(15,23,42,.96),rgba(17,24,39,.94))!important;border:1px solid rgba(99,102,241,.30)!important;border-radius:14px!important;box-shadow:0 18px 40px rgba(2,6,23,.42)!important;backdrop-filter:blur(12px)}
div[data-testid="stToast"] p{color:#E8ECF1!important;font-weight:600!important}
.analysis-nav{background:linear-gradient(160deg,rgba(15,23,42,.94),rgba(17,24,39,.86));border:1px solid rgba(99,102,241,.22);border-radius:16px;padding:14px 16px;margin:0 0 14px;box-shadow:0 14px 34px rgba(2,6,23,.26)}
.analysis-nav-meta{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:10px}
.analysis-nav-title{color:#F8FAFC;font-weight:800;font-size:1rem}
.analysis-nav-sub{color:#94A3B8;font-size:.78rem}
.analysis-nav-chip{display:inline-flex;align-items:center;gap:6px;padding:4px 10px;border-radius:999px;background:rgba(99,102,241,.12);border:1px solid rgba(99,102,241,.24);color:#C7D2FE;font-size:.74rem;font-weight:700}
.prompt-caption{color:#94A3B8;font-size:.74rem;font-weight:700;margin-bottom:8px}
.guide-card{background:
linear-gradient(180deg,rgba(99,102,241,.08),rgba(99,102,241,0) 34%),
linear-gradient(160deg,rgba(10,14,24,.96),rgba(16,24,39,.88));
border:1px solid rgba(99,102,241,.28);border-radius:16px;padding:14px 16px;margin:0 0 14px;box-shadow:0 16px 36px rgba(2,6,23,.22);position:relative;overflow:hidden}
.guide-card:before{content:"";position:absolute;inset:0 0 auto 0;height:1px;background:linear-gradient(90deg,rgba(99,102,241,0),rgba(165,180,252,.8),rgba(99,102,241,0))}
.guide-kicker{color:#C7D2FE;font-size:.75rem;font-weight:800;letter-spacing:.04em;text-transform:uppercase;margin:0 0 8px}
.guide-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px}
.guide-step{background:linear-gradient(160deg,rgba(15,23,42,.9),rgba(15,23,42,.72));border:1px solid rgba(148,163,184,.14);border-radius:12px;padding:12px 13px}
.guide-step-title{color:#F8FAFC;font-size:.84rem;font-weight:800;margin:0 0 4px}
.guide-step-copy{color:#94A3B8;font-size:.77rem;line-height:1.55;margin:0}
.soft-note{color:#94A3B8;font-size:.76rem;line-height:1.55;margin-top:10px}
div[data-testid="stExpander"]{
  background:linear-gradient(160deg,rgba(15,23,42,.94),rgba(17,24,39,.86))!important;
  border:1px solid rgba(148,163,184,.16)!important;
  border-radius:14px!important;
  overflow:hidden!important;
}
div[data-testid="stExpander"] details{
  background:transparent!important;
  border:none!important;
}
div[data-testid="stExpander"] summary{
  background:transparent!important;
}
div[data-testid="stExpander"] summary > div,
div[data-testid="stExpander"] summary > div > div{
  background:transparent!important;
}
div[data-testid="stExpander"] summary:hover{
  background:rgba(255,255,255,.02)!important;
}
div[data-testid="stExpander"] summary p{
  color:#E8ECF1!important;
  font-weight:700!important;
}
div[data-testid="stExpander"] summary svg{
  color:#CBD5E1!important;
  fill:#CBD5E1!important;
}
div[data-testid="stExpander"] div[data-testid="stExpanderDetails"]{
  background:linear-gradient(180deg,rgba(15,23,42,.86),rgba(15,23,42,.72))!important;
  border-top:1px solid rgba(148,163,184,.12)!important;
}
div[data-testid="stExpander"] div[data-testid="stMarkdownContainer"] p,
div[data-testid="stExpander"] div[data-testid="stMarkdownContainer"] span,
div[data-testid="stExpander"] div[data-testid="stMarkdownContainer"] li{
  color:#E8ECF1!important;
}
div[data-testid="stExpander"] pre,
div[data-testid="stExpander"] code{
  background:#0F172A!important;
}
div[data-testid="stExpander"] div[data-testid="stMarkdownContainer"]{
  font-size:.95rem!important;
  line-height:1.72!important;
}
div[data-testid="stExpander"] div[data-testid="stMarkdownContainer"] h1,
div[data-testid="stExpander"] div[data-testid="stMarkdownContainer"] h2,
div[data-testid="stExpander"] div[data-testid="stMarkdownContainer"] h3,
div[data-testid="stExpander"] div[data-testid="stMarkdownContainer"] h4,
div[data-testid="stExpander"] div[data-testid="stMarkdownContainer"] h5,
div[data-testid="stExpander"] div[data-testid="stMarkdownContainer"] h6{
  color:#F8FAFC!important;
  font-weight:800!important;
  letter-spacing:-.01em!important;
  line-height:1.35!important;
  margin:1.05rem 0 .55rem!important;
}
div[data-testid="stExpander"] div[data-testid="stMarkdownContainer"] h1{font-size:1.12rem!important}
div[data-testid="stExpander"] div[data-testid="stMarkdownContainer"] h2{font-size:1.05rem!important}
div[data-testid="stExpander"] div[data-testid="stMarkdownContainer"] h3{font-size:.99rem!important}
div[data-testid="stExpander"] div[data-testid="stMarkdownContainer"] h4,
div[data-testid="stExpander"] div[data-testid="stMarkdownContainer"] h5,
div[data-testid="stExpander"] div[data-testid="stMarkdownContainer"] h6{font-size:.95rem!important}
div[data-testid="stExpander"] div[data-testid="stMarkdownContainer"] p,
div[data-testid="stExpander"] div[data-testid="stMarkdownContainer"] li{
  color:#E5E7EB!important;
  font-size:.95rem!important;
  line-height:1.72!important;
  margin:.2rem 0 .62rem!important;
}
div[data-testid="stExpander"] div[data-testid="stMarkdownContainer"] ul,
div[data-testid="stExpander"] div[data-testid="stMarkdownContainer"] ol{
  padding-left:1.15rem!important;
  margin:.25rem 0 .8rem!important;
}
div[data-testid="stExpander"] div[data-testid="stMarkdownContainer"] strong,
div[data-testid="stExpander"] div[data-testid="stMarkdownContainer"] b{
  color:#F8FAFC!important;
  font-size:inherit!important;
  font-weight:800!important;
}
div[data-testid="stExpander"] div[data-testid="stMarkdownContainer"] em{
  color:#CBD5E1!important;
  font-size:inherit!important;
}
div[data-testid="stExpander"] div[data-testid="stMarkdownContainer"] hr{
  border:none!important;
  border-top:1px solid rgba(148,163,184,.18)!important;
  margin:.95rem 0!important;
}
div[data-testid="stExpander"] div[data-testid="stMarkdownContainer"] blockquote{
  border-left:3px solid rgba(99,102,241,.45)!important;
  background:rgba(15,23,42,.55)!important;
  color:#CBD5E1!important;
  margin:.8rem 0!important;
  padding:.65rem .9rem!important;
  border-radius:0 10px 10px 0!important;
}
@media (max-width:900px){
  .block-container{padding-left:1rem!important;padding-right:1rem!important}
  .price-header{padding:16px 18px}
  .price-big{font-size:1.78rem}
  .analysis-nav{padding:12px}
  .guide-grid{grid-template-columns:1fr}
}
</style>""", unsafe_allow_html=True)

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

def _recent_analysis_tape_items(limit=6):
    items = []
    seen = set()
    for msg in reversed(st.session_state.get('messages', [])):
        if msg.get("type") != "analysis":
            continue
        ticker = _format_board_code(msg.get('ticker'), "")
        if not ticker or ticker in seen:
            continue
        seen.add(ticker)
        meta = msg.get('meta') or {}
        signal = _format_board_code(meta.get('judgment') or meta.get('action_label'), "IDLE")
        items.append(f"{ticker} ES {_format_board_es(meta.get('ensemble_score'))} [{signal}]")
        if len(items) >= limit:
            break
    return items

def _scan_tape_items(limit=6):
    items = []
    for row in st.session_state.get('scan_results', [])[:limit]:
        ticker = _format_board_code(row.get('ticker'), "")
        if not ticker:
            continue
        signal = _format_board_code(row.get('jg_key') or row.get('action') or row.get('jg'), "READY")
        items.append(f"{ticker} ES {_format_board_es(row.get('es'))} [{signal}]")
    return items

def _build_board_marquee(base_items):
    history_items = _recent_analysis_tape_items()
    if history_items:
        return _dedupe_board_items([*base_items, *history_items])
    scan_items = _scan_tape_items()
    if scan_items:
        return _dedupe_board_items([*base_items, *scan_items])
    return _dedupe_board_items([
        *base_items,
        f"[ {BRAND_NAME} ] READY",
        "TARGET WAIT",
        "ES --",
        "SIGNAL IDLE",
    ])

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
        judgment = _format_board_code(focus_row.get('jg_key') if focus_row else 'READY', fallback='READY')
        context = _format_board_code(
            focus_row.get('ctx') if focus_row else (selected_sector if selected_sector != 'READY' else 'STANDBY'),
            fallback='STANDBY'
        )
        scan_source = _format_board_code(st.session_state.get('scan_source'), fallback='WATCHLIST')
        system_status = 'ACTIVE' if focus_row else 'READY'
        feed_status = 'WATCH_SYNC'
        summary = "Sweep the tape, rank the field, then drill into the strongest setup."
        marquee_items = _build_board_marquee([
            f"[ {BRAND_NAME} ] {mode_label} DESK",
            f"STATUS {system_status}",
            f"TARGET {focus}",
            f"ES {_format_board_es(es_value)}",
            f"SIGNAL {judgment}",
            f"CTX {context}",
            f"SPAN {period_label}",
            f"SOURCE {scan_source}",
            f"COUNT {len(results)}",
        ])
        return {
            'brand_code': BRAND_NAME,
            'mode': mode_label,
            'focus': focus,
            'es': _format_board_es(es_value),
            'judgment': judgment,
            'context': context,
            'period': period_label,
            'marquee_items': marquee_items,
            'summary': summary,
            'system_status': system_status,
            'feed_status': feed_status,
            'status_tone': _resolve_board_tone(mode_label, judgment, es_value),
        }

    analysis_msg = _latest_analysis_message()
    meta = analysis_msg.get('meta') if analysis_msg else None
    focus = _format_board_code((analysis_msg or {}).get('ticker'), fallback='WAIT')
    es_value = meta.get('ensemble_score') if meta else None
    judgment = _format_board_code(meta.get('judgment') if meta else 'IDLE', fallback='IDLE')
    context = _format_board_code(meta.get('context_label') if meta else 'STANDBY', fallback='STANDBY')
    system_status = 'ACTIVE' if meta else 'READY'
    feed_status = 'MARKET_SYNC'
    summary = (
        f"Signal first. Structure next. {_format_board_text(meta.get('action_label'), 'READY')} is active on {focus}."
        if meta and meta.get('action_label')
        else "Read the quieter signal before price gets loud."
    )
    marquee_items = [
        f"[ {BRAND_NAME} ] {mode_label} DESK",
        f"STATUS {system_status}",
        f"TARGET {focus}",
        f"ES {_format_board_es(es_value)}",
        f"SIGNAL {judgment}",
        f"CTX {context}",
        f"SPAN {period_label}",
    ]
    if meta:
        marquee_items.append(f"B{int(meta.get('buy_agree', 0))}:S{int(meta.get('sell_agree', 0))}")
    marquee_items = _build_board_marquee(marquee_items)
    return {
        'brand_code': BRAND_NAME,
        'mode': mode_label,
        'focus': focus,
        'es': _format_board_es(es_value),
        'judgment': judgment,
        'context': context,
        'period': period_label,
        'marquee_items': marquee_items,
        'summary': summary,
        'system_status': system_status,
        'feed_status': feed_status,
        'status_tone': _resolve_board_tone(mode_label, judgment, es_value),
    }

def _render_brand_board(payload, compact=False):
    height = 320 if compact else 290
    components.html(build_brand_board(payload, compact=compact), height=height, scrolling=False)

def _render_scanner_guide(tickers, scan_source):
    target_count = len(tickers)
    source_label = scan_source or "직접"
    st.markdown(
        f"""
        <div class="guide-card fade-up">
            <p class="guide-kicker">Scanner Guide · 스캐너 안내</p>
            <div class="guide-grid">
                <div class="guide-step">
                    <p class="guide-step-title">1. 유니버스 선택</p>
                    <p class="guide-step-copy">섹터 버튼이나 직접 입력으로 스캔 대상을 정합니다. 지금 준비된 종목은 <b style="color:#F8FAFC">{target_count}개</b>, 출처는 <b style="color:#F8FAFC">{source_label}</b>입니다.</p>
                </div>
                <div class="guide-step">
                    <p class="guide-step-title">2. 점수와 강도 확인</p>
                    <p class="guide-step-copy"><b>스캔 점수</b>는 우선순위, <b>ES</b>는 방향성입니다. 멀티 시그널과 최근 콤보가 겹칠수록 상단에 배치됩니다.</p>
                </div>
                <div class="guide-step">
                    <p class="guide-step-title">3. 바로 분석으로 이동</p>
                    <p class="guide-step-copy">카드의 <b>분석</b> 버튼을 누르면 분석 모드로 넘어가고, 사이드바의 스캔 내비게이터에서 이전/다음 종목을 빠르게 넘길 수 있습니다.</p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def _render_analysis_guide():
    st.markdown(
        """
        <div class="guide-card fade-up">
            <p class="guide-kicker">How To Use · 사용 방법</p>
            <div class="guide-grid">
                <div class="guide-step">
                    <p class="guide-step-title">1. 최종 판단 / 신뢰도</p>
                    <p class="guide-step-copy">먼저 최종 판단과 신뢰도를 보고, 그 아래 근거 요약으로 방향성의 중심 논리를 빠르게 확인합니다.</p>
                </div>
                <div class="guide-step">
                    <p class="guide-step-title">2. 위험 점검</p>
                    <p class="guide-step-copy">스마트 머니 다이버전스, 손익비, 저거래량, 과열 위험이 있으면 여기서 먼저 경고를 확인하세요.</p>
                </div>
                <div class="guide-step">
                    <p class="guide-step-title">3. 차트와 AI 리포트</p>
                    <p class="guide-step-copy">차트 탭에서 거래량 프로파일(VP), 패턴, 캔들 툴팁으로 타이밍을 보고, AI 리포트는 마지막 정리용 보조 의견으로 활용하면 좋습니다.</p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with st.sidebar:
    _mi = 0 if st.session_state.get('_mode', '분석') == '분석' else 1
    app_mode = st.radio("모드", ['분석', '스캐너'], index=_mi)
    st.session_state['_mode'] = app_mode
    chart_period = st.radio("기간", ['3개월', '6개월', '1년', '2년'], index=1, horizontal=True, key="period")
    chart_days = {'3개월': 63, '6개월': 126, '1년': 252, '2년': 504}[chart_period]
    _render_brand_board(_build_brand_payload(app_mode, chart_period), compact=True)
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
        sel_cnt = len(sel_list)
        st.markdown(f"<div style='background:rgba(99,102,241,.08);border:1px solid #6366F133;border-radius:10px;padding:10px 14px;margin:8px 0'>"
                    f"<span style='color:#A5B4FC;font-weight:700'>{selected_sector}</span>"
                    f"<span style='color:#64748B;margin-left:8px'>{sel_cnt}종목</span>"
                    f"<span style='color:#64748B;margin-left:8px'>· 점수 높은 순 정렬</span></div>", unsafe_allow_html=True)
        if sel_list:
            chips = "".join([f"<span style='display:inline-block;margin:3px 4px 0 0;padding:3px 8px;border-radius:999px;"
                             f"background:rgba(30,41,59,.8);border:1px solid #334155;color:#CBD5E1;font-size:.76rem;font-weight:600'>{t}</span>"
                             for t in sel_list])
            st.markdown(f"<div style='background:rgba(15,23,42,.55);border:1px solid #1E293B;border-radius:10px;padding:10px 12px;margin:6px 0 10px'>"
                        f"<p style='margin:0 0 6px;color:#94A3B8;font-size:.74rem;font-weight:700'>선택 종목 목록</p>"
                        f"<div style='max-height:110px;overflow:auto'>{chips}</div></div>", unsafe_allow_html=True)

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

    _render_scanner_guide(tickers, scan_source)

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
        bt_  = [r for r in results if 'BUY'  in str(r.get('jg_key', ''))]
        st_  = [r for r in results if 'SELL' in str(r.get('jg_key', ''))]
        scan_total = st.session_state.get('scan_total', 0)
        st.caption("정렬 기준: 스캔 점수 → 강도 → 최근 시그널 순서입니다.")

        st.markdown(
            f"<div style='display:flex;gap:12px;margin-bottom:12px'>"
            f"<div style='flex:1;background:rgba(99,217,162,.10);border:1px solid rgba(99,217,162,.28);border-radius:10px;padding:10px;text-align:center'>"
            f"<span style='color:#63D9A2;font-weight:800;font-size:1.3rem'>{len(bt_)}</span>"
            f"<span style='color:#64748B;font-size:.8rem'> 매수</span></div>"
            f"<div style='flex:1;background:rgba(255,143,150,.10);border:1px solid rgba(255,143,150,.28);border-radius:10px;padding:10px;text-align:center'>"
            f"<span style='color:#FF8F96;font-weight:800;font-size:1.3rem'>{len(st_)}</span>"
            f"<span style='color:#64748B;font-size:.8rem'> 매도</span></div>"
            f"<div style='flex:1;background:rgba(99,102,241,.06);border:1px solid #6366F133;border-radius:10px;padding:10px;text-align:center'>"
            f"<span style='color:#A5B4FC;font-weight:800;font-size:1.3rem'>{len(results)}</span>"
            f"<span style='color:#64748B;font-size:.8rem'>/{scan_total}</span></div></div>",
            unsafe_allow_html=True
        )

        for rk, r in enumerate(results, start=1):
            chc = '#63D9A2' if r['chg'] >= 0 else '#FF8F96'
            chi = '▲' if r['chg'] >= 0 else '▼'
            jg_key = str(r.get('jg_key', ''))
            jc  = '#63D9A2' if 'BUY' in jg_key else ('#FF8F96' if 'SELL' in jg_key else '#F8DE9A')

            # 콤보 스캔 목록은 mx 배지 태그로만 표시 — 불릿 리스트(sh) 제거

            # UT/Hull 전환 배지
            th = "".join([
                f"<span style='display:inline-flex;align-items:center;gap:4px;padding:2px 8px;border-radius:999px;"
                f"background:rgba({'52,211,153' if t['dir']=='buy' else '248,113,113'},.12);"
                f"color:{'#63D9A2' if t['dir']=='buy' else '#FF8F96'};"
                f"font-size:.72rem;font-weight:700;margin-right:6px'>{t['icon']} {t['label']} {t['date']}</span>"
                for t in r.get('transitions', [])
            ]) if r.get('transitions') else "<span style='color:#475569;font-size:.78rem'>UT/HULL 전환 없음</span>"

            # Multi-Signal 배지 — 엔진 컬럼 기반 (오늘 기준)
            mh = (
                f"<div style='margin:6px 0 2px'>"
                f"<span style='display:inline-block;padding:2px 8px;border-radius:999px;"
                f"background:rgba({'52,211,153' if r.get('multi_sig') else '148,163,184'},.16);"
                f"color:{'#63D9A2' if r.get('multi_sig') else '#94A3B8'};"
                f"font-size:.72rem;font-weight:700'>"
                f"MULTI-SIGNAL {'ON' if r.get('multi_sig') else 'OFF'} ({r.get('multi_cnt', 0)})</span>"
                f"<span style='color:#64748B;font-size:.7rem;margin-left:6px'>"
                f"ENGINE B:{r.get('multi_buy', 0)} S:{r.get('multi_sell', 0)} N:{r.get('multi_neutral', 0)} "
                f"| Imb:{r.get('multi_imb', 0):+.0f}</span></div>"
            )

            # 최근 콤보 태그 (acs 기반, 표시 전용)
            mx = "".join([
                f"<span style='display:inline-flex;align-items:center;gap:4px;padding:2px 7px;border-radius:999px;"
                f"background:rgba({'52,211,153' if m['dir']=='buy' else '248,113,113' if m['dir']=='sell' else '148,163,184'},.10);"
                f"border:1px solid rgba(148,163,184,.25);"
                f"color:{'#A7E7CF' if m['dir']=='buy' else '#F6C2C2' if m['dir']=='sell' else '#CBD5E1'};"
                f"font-size:.7rem;font-weight:600;margin:2px 4px 2px 0'>"
                f"{m['icon']} {m['label']} {m['date']}</span>"
                for m in r.get('multi_hits', [])
            ]) if r.get('multi_hits') else "<span style='color:#475569;font-size:.74rem'>최근 3일 다중시그널 후보 없음</span>"

            esc = '#63D9A2' if r['es'] > 10 else ('#FF8F96' if r['es'] < -10 else '#F8DE9A')
            bd  = '#1E293B' if r['scans'] else '#0F172A'
            op  = '1' if r['scans'] else '.6'
            sc  = '#63D9A2' if r['scan_score'] > 0 else ('#FF8F96' if r['scan_score'] < 0 else '#F8DE9A')

            rh = ""
            if r.get('reason'):
                rc = '#A7E7CF' if 'BUY' in jg_key else ('#F6C2C2' if 'SELL' in jg_key else '#F5D79A')
                rh = (f"<div style='padding:4px 0;border-top:1px solid rgba(255,255,255,.04);margin-top:4px'>"
                      f"<span style='color:{rc};font-size:.78rem'>💬 {r['reason'][:80]}</span></div>")

            st.markdown(
                f"<div style='background:linear-gradient(160deg,#0F1320,#141926);"
                f"border:1px solid {bd};border-radius:14px;padding:14px 18px;margin:6px 0;opacity:{op}'>"
                f"<div style='display:flex;justify-content:space-between;margin-bottom:8px'>"
                f"<span style='color:#A5B4FC;font-weight:800;font-size:1.15rem'>#{rk} {r['ticker']}</span>"
                f"<div style='display:flex;align-items:center;gap:8px'>"
                f"<span style='color:{sc};font-size:.75rem;font-weight:700'>SCAN:{r['scan_score']:+.1f}</span>"
                f"<span style='color:{esc};font-size:.75rem;font-weight:700'>ES:{r['es']:+.0f}</span>"
                f"<span style='color:{jc};font-size:.8rem;font-weight:600'>{r['jg']}({r['cf']:.0f}%)</span>"
                f"<span style='color:{chc};font-size:.8rem'>{chi}{abs(r['chg']):.1f}%</span>"
                f"</div></div>"
                f"<div style='margin:4px 0 8px'>{th}</div>"
                f"{mh}"
                f"<div style='margin:2px 0 7px'>{mx}</div>"
                f"{rh}</div>",
                unsafe_allow_html=True
            )

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
    _render_analysis_guide()

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
