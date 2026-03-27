# ══════════════════════════════════════════════════════════════
#  SIGN — PART 1/4
#  설정, 레지스트리, 유틸리티, 기술지표
# ══════════════════════════════════════════════════════════════

import streamlit as st, google.generativeai as genai
import time, math, html
import re
import textwrap
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import yfinance as yf
from sectors import SECTOR_GROUPS
from config import GEMINI_API_KEY, COMBINED_SCAN_REGISTRY, CTX_KOR
from utils import _valid_fmt, _sf, fetch_fundamentals, validate_ticker, compute_and_cache, _compute_cached
from chart import build_chart, build_metadata
from ui import render_market_home_dashboard
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
MODE_MARKET_DAILY = "US MARKET DAILY"
MODE_ANALYSIS = "분석"
MODE_SCANNER = "스캐너"
_APP_MODE_OPTIONS = [MODE_MARKET_DAILY, MODE_ANALYSIS, MODE_SCANNER]
_QUICK_ANALYSIS_TICKERS = ["NVDA", "TSLA", "AAPL", "GOOGL", "AMZN", "META", "MSFT", "PLTR", "HIMS", "SNDK", "LITE", "COHR", "IREN", "ORCL", "RKLB", "ASTS"]


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
        '_mode': MODE_MARKET_DAILY,
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
        'selected_sectors': [],
        'scan_tickers_override': None,
        'scan_etf_items': [],
        'scan_etf_tickers_override': None,
        'scan_etf_note': '',
        'scan_etf_errors': [],
        'scan_etf_picker': [],
        'scan_sector_picker': [],
        '_clear_scan_pending': False,
    }
    for k, v in defs.items():
        if k not in st.session_state:
            st.session_state[k] = v


def reset_session():
    st.session_state['_mode'] = MODE_MARKET_DAILY
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
    st.session_state['selected_sectors'] = []
    st.session_state['scan_tickers_override'] = None
    st.session_state['scan_etf_items'] = []
    st.session_state['scan_etf_tickers_override'] = None
    st.session_state['scan_etf_note'] = ''
    st.session_state['scan_etf_errors'] = []
    st.session_state['scan_etf_picker'] = []
    st.session_state['scan_sector_picker'] = []

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
    if symbol in {"QQQ", "SPY"}:
        try:
            wiki_payload = _fetch_wikipedia_index_constituents(symbol)
            if wiki_payload.get("tickers"):
                return wiki_payload
        except Exception as exc:
            print(f"[ETF-WIKI]{symbol}: {exc}")
    official_fetchers = {
        "SKYY": _fetch_first_trust_holdings,
        "IGV": _fetch_ishares_holdings,
        "QMOM": _fetch_alpha_architect_holdings,
        "FFTY": _fetch_innovator_holdings,
        "IVES": _fetch_wedbush_holdings,
        "ARKK": _fetch_ark_holdings,
        "ARKQ": _fetch_ark_holdings,
        "ARKW": _fetch_ark_holdings,
        "ARKG": _fetch_ark_holdings,
        "ARKF": _fetch_ark_holdings,
        "WCBR": _fetch_wisdomtree_holdings,
    }
    if symbol in official_fetchers:
        try:
            official_payload = official_fetchers[symbol](symbol)
            if official_payload.get("tickers"):
                return official_payload
        except Exception as exc:
            print(f"[ETF-OFFICIAL]{symbol}: {exc}")
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


def _render_scanner_selection_panel(selected_sectors, selected_list):
    selected_sectors = _normalized_selected_sectors(selected_sectors)
    if not selected_sectors:
        return
    count = len(selected_list)
    title = _sector_selection_title(selected_sectors) or "선택 없음"
    sector_chips = "".join(
        _sigl_badge(name, 'accent' if name == '🌐 전체' else 'muted')
        for name in selected_sectors
    )
    chips = "".join(
        f"<span class='sigl-code-chip'>{html.escape(str(t))}</span>"
        for t in selected_list
    ) or "<span class='sigl-empty'>선택된 종목이 없습니다.</span>"
    panel_html = f"""
        <div class="sigl-card sigl-card--accent sigl-scanner-scope">
            <div class="sigl-page-head">
                <div>
                    <p class="sigl-page-head__eyebrow">Scanner Scope</p>
                    <p class="sigl-page-head__title">{html.escape(str(title))}</p>
                    <p class="sigl-page-head__copy">여러 섹터를 묶어 하나의 스캔 유니버스로 사용할 수 있습니다.</p>
                </div>
                <div class="sigl-inline sigl-scanner-scope__meta">
                    {_sigl_badge(f'{count} 종목', 'accent')}
                    {_sigl_badge('점수 높은 순 정렬', 'muted')}
                </div>
            </div>
            <div class="sigl-chip-row sigl-scanner-scope__sectors">{sector_chips}</div>
            <div class="sigl-code-list sigl-scanner-scope__codes">{chips}</div>
        </div>
        """
    _render_surface_html(panel_html, 0)


def _render_etf_universe_panel(etf_items, selected_list, note=""):
    if not etf_items:
        return
    count = len(selected_list)
    title = _short_collection_title([item.get("resolved") for item in etf_items]) or "ETF"
    etf_chips = "".join(
        _sigl_badge(
            item["resolved"] if item.get("requested", "").upper() == item.get("resolved", "") else f"{item['requested']}→{item['resolved']}",
            'warning' if item.get("requested", "").upper() != item.get("resolved", "") else 'muted'
        )
        for item in etf_items
    )
    chips = "".join(
        f"<span class='sigl-code-chip'>{html.escape(str(t))}</span>"
        for t in selected_list
    ) or "<span class='sigl-empty'>선택된 종목이 없습니다.</span>"
    panel_html = f"""
        <div class="sigl-card sigl-card--accent sigl-scanner-scope">
            <div class="sigl-page-head">
                <div>
                    <p class="sigl-page-head__eyebrow">ETF 구성종목</p>
                    <p class="sigl-page-head__title">{html.escape(str(title))}</p>
                    <p class="sigl-page-head__copy">{html.escape(note or 'ETF 또는 지수 입력으로 임시 스캔 유니버스를 구성했습니다.')}</p>
                </div>
                <div class="sigl-inline sigl-scanner-scope__meta">
                    {_sigl_badge(f'{count} 종목', 'warning')}
                </div>
            </div>
            <div class="sigl-chip-row sigl-scanner-scope__sectors">{etf_chips}</div>
            <div class="sigl-code-list sigl-scanner-scope__codes">{chips}</div>
        </div>
        """
    _render_surface_html(panel_html, 0)


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
            <div class="sigl-chip-row">{combo_hits}</div>
            {reason_html}
        </div>
        """
    _render_surface_html(panel_html, 0)

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
    if current_mode == MODE_SCANNER:
        mode_label = 'SCANNER'
    elif current_mode == MODE_MARKET_DAILY:
        mode_label = 'US MARKET DAILY'
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
        st.session_state.pop('scan_in', None)
        st.session_state['scan_sector_picker'] = []
        current_sector_selection = []
    _apply_sector_selection(current_sector_selection)
    selected_sector = st.session_state.get('selected_sector', None)
    manual_preview = _parse_ticker_input(st.session_state.get('scan_in'))
    current_etf_selection = _normalized_selected_etf_presets(st.session_state.get('scan_etf_picker'))
    active_etf_items = st.session_state.get('scan_etf_items') or []
    active_etf_tickers = st.session_state.get('scan_etf_tickers_override') or []

    _render_page_intro(
        "Scanner",
        "대상을 구성하고 스캔을 실행하세요.",
        "스캔 결과를 확인하고, 분석 모드로 자세한 분석을 이어가실 수 있습니다.",
        badges=[
            (f"선택 섹터 {len(current_sector_selection)}", "accent"),
            (f"ETF 선택 {len(current_etf_selection)}", "warning"),
            (f"직접 입력 {len(manual_preview)}개", "warning"),
            (f"전체 후보 {len(all_universe)}개", "muted"),
        ],
    )

    _render_section_heading(
        "섹터, ETF, 직접 티커 입력으로 스캔 대상을 구성하세요.",
        badges=[
            ("멀티 섹터 선택", "accent"),
            ("ETF 임시 유니버스", "warning"),
            ("직접 입력 우선 적용", "muted"),
        ],
        eyebrow="스캔 대상 구성",
    )
    with st.container():
        st.markdown("<div class='sigl-sector-picker-anchor'></div>", unsafe_allow_html=True)
        _render_sector_button_picker(sector_names, current_sector_selection)

    selected_sectors = _normalized_selected_sectors(
        st.session_state.get('selected_sectors') or current_sector_selection
    )
    selected_sector = st.session_state.get('selected_sector', None)

    if selected_sectors:
        sel_list = st.session_state.get('scan_tickers_override') or _sector_selection_tickers(selected_sectors) or []
        sel_list = list(dict.fromkeys([str(t).strip().upper() for t in sel_list if str(t).strip()]))
        _render_scanner_selection_panel(selected_sectors, sel_list)

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
    if active_etf_tickers:
        _render_etf_universe_panel(active_etf_items, active_etf_tickers, st.session_state.get('scan_etf_note', ''))
    if st.session_state.get('scan_etf_errors'):
        st.caption("일부 ETF는 불러오지 못했습니다: " + " | ".join(st.session_state['scan_etf_errors']))

    active_preview = manual_preview or active_etf_tickers or st.session_state.get('scan_tickers_override') or []

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
    if manual_tickers:
        tickers = manual_tickers
        scan_source = "직접 입력"
    elif active_etf_tickers:
        tickers = active_etf_tickers
        scan_source = _short_collection_title([item.get("resolved") for item in active_etf_items]) or "ETF"
    elif st.session_state.get('scan_tickers_override'):
        tickers = st.session_state['scan_tickers_override']
        scan_source = selected_sector or ("섹터" if selected_sectors else "직접")
    else:
        tickers = []
        scan_source = "직접"
    tickers = list(dict.fromkeys([t for t in tickers if t]))

    if scan_btn and not tickers:
        st.warning("스캔할 티커가 없습니다. 섹터를 고르거나 ETF 종목을 불러오거나 직접 티커를 입력해 주세요.")

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
        _render_section_heading(
            "스캔 결과",
            "현재 유니버스에서 조건과 점수가 높은 종목을 우선순위대로 정렬했습니다.",
            badges=[
                (f"매치 {len(results)}개", "accent"),
                (f"전체 대상 {scan_total}개", "muted"),
            ],
            eyebrow="Result Board",
            tight=True,
        )
        st.caption("정렬 기준: 스캔 점수 → 강도 → 최근 시그널 순서입니다.")
        _render_scanner_summary(results, scan_total)

        for rk, r in enumerate(results, start=1):
            _render_scanner_result_card(rk, r)

            if st.button(f"{r['ticker']} 분석", key=f"sc_{r['ticker']}", use_container_width=True):
                _set_scan_focus(r['ticker'], rk - 1)
                _queue_analysis_target(r['ticker'])
    else:
        _render_empty_state(
            "아직 스캔 결과가 없습니다",
            "섹터를 선택하거나 직접 티커를 입력한 뒤 `스캔 실행`을 누르면 결과 카드가 정렬되어 표시됩니다.",
            badges=[
                ("유니버스 선택 필요", "warning"),
                ("직접 입력 가능", "muted"),
            ],
            tone="accent",
        )

# ══════════════════════════════════════════════════════════════
#  US MARKET DAILY 모드
# ══════════════════════════════════════════════════════════════
elif current_mode == MODE_MARKET_DAILY:
    _render_brand_board(main_board_payload)
    render_market_home_dashboard()
    _render_section_heading(
        "브리핑에서 바로 분석",
        "티커를 입력하거나 빠른 시작에서 선택하면 분석 모드로 전환되어 상세 분석을 이어갑니다.",
        badges=[
            ("US MARKET DAILY", "accent"),
            ("즉시 분석 전환", "warning"),
        ],
        eyebrow="Daily To Analysis",
        tight=True,
    )
    _render_quick_analysis_grid(key_prefix="briefing_quick")
    if ti := st.chat_input("분석할 티커를 입력하세요."):
        parsed = _parse_ticker_input(ti)
        if not parsed:
            st.toast("분석할 티커를 입력해 주세요.", icon="⌨️")
        else:
            if len(parsed) > 1:
                st.toast(f"{parsed[0]} 기준으로 먼저 분석합니다.", icon="📌")
            _queue_analysis_target(parsed[0])

# ══════════════════════════════════════════════════════════════
#  분석 모드
# ══════════════════════════════════════════════════════════════
else:
    _render_brand_board(main_board_payload)

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
                ("QUANT AUDIT 연동", "muted"),
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
    if ti := st.chat_input("분석할 티커를 입력하세요."):
        parsed = _parse_ticker_input(ti)
        if not parsed:
            st.toast("분석할 티커를 입력해 주세요.", icon="⌨️")
        else:
            if len(parsed) > 1:
                st.toast(f"{parsed[0]} 기준으로 먼저 분석합니다.", icon="📌")
            process_ticker(parsed[0])
