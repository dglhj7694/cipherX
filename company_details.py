import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# ═══════════════════════════════════════════════════════════════
# 🛠️  유틸리티 함수
# ═══════════════════════════════════════════════════════════════
def _fmt_num(num, is_currency=True):
    if pd.isna(num) or num is None: return "N/A"
    prefix = "$" if is_currency else ""
    sign = "-" if num < 0 else ""
    a = abs(num)
    if a >= 1e12:   return f"{sign}{prefix}{a/1e12:.2f}T"
    elif a >= 1e9:  return f"{sign}{prefix}{a/1e9:.2f}B"
    elif a >= 1e6:  return f"{sign}{prefix}{a/1e6:.2f}M"
    elif a >= 1e3:  return f"{sign}{prefix}{a/1e3:.2f}K"
    return f"{sign}{prefix}{num:,.2f}"

def _fmt_pct(num):
    if pd.isna(num) or num is None: return "N/A"
    return f"{num * 100:.2f}%"

def _safe(val, fallback="N/A"):
    return val if val is not None and not (isinstance(val, float) and np.isnan(val)) else fallback

def _get_row(df, candidates, col_idx=0):
    if df is None: return None
    for name in candidates:
        if name in df.index:
            try:
                val = df.loc[name].dropna()
                if len(val) > col_idx: return val.iloc[col_idx]
            except: pass
    return None

def _get_row_series(df, candidates):
    if df is None: return pd.Series(dtype=float)
    for name in candidates:
        if name in df.index:
            try:
                return df.loc[name].dropna().sort_index()
            except: pass
    return pd.Series(dtype=float)

def _calc_cagr(financials, row_candidates):
    try:
        series = _get_row_series(financials, row_candidates if isinstance(row_candidates, list) else [row_candidates])
        if len(series) >= 2:
            series = series.sort_index()
            start_val, end_val = series.iloc[0], series.iloc[-1]
            years = len(series) - 1
            if start_val > 0 and end_val > 0: return (end_val / start_val) ** (1 / years) - 1
            elif start_val < 0 and end_val > 0: return None
    except Exception: pass
    return None

def _annual_values(financials, row_candidates):
    try:
        series = _get_row_series(financials, row_candidates if isinstance(row_candidates, list) else [row_candidates])
        if len(series) > 0:
            series = series.sort_index(ascending=False)
            return series.tolist(), series.index.tolist()
    except Exception: pass
    return [], []

def _verdict_badge(color, emoji, text):
    bg_map = {"green": "rgba(0,230,118,0.1)", "red": "rgba(255,23,68,0.1)", "yellow": "rgba(255,193,7,0.1)", "blue": "rgba(33,150,243,0.1)", "gray": "rgba(96,125,139,0.1)"}
    border_map = {"green": "#00E676", "red": "#FF1744", "yellow": "#FFC107", "blue": "#2196F3", "gray": "#607D8B"}
    return f"""<div style="background:{bg_map.get(color,'rgba(96,125,139,0.1)')};border:1px solid {border_map.get(color,'#607D8B')};border-radius:10px;padding:12px 16px;margin-top:14px;text-align:center"><span style="font-size:1.05rem;font-weight:700;color:{border_map.get(color,'#607D8B')}">{emoji} {text}</span></div>"""

def _growth_stage(info, fin, bs, cf):
    rev_g = info.get('revenueGrowth', 0) or 0
    margin = info.get('profitMargins', 0) or 0
    rev = info.get('totalRevenue', 0) or 0
    div_y = info.get('dividendYield', 0) or 0
    op_cf = 0
    try:
        if cf is not None:
            for name in ['Operating Cash Flow', 'Total Cash From Operating Activities']:
                if name in cf.index:
                    op_cf = cf.loc[name].dropna().iloc[0] or 0
                    break
    except: pass

    rev_declining = False
    try:
        rev_series = _get_row_series(fin, ['Total Revenue'])
        if len(rev_series) >= 3:
            rev_sorted = rev_series.sort_index(ascending=False)
            declines = sum(1 for i in range(len(rev_sorted)-1) if rev_sorted.iloc[i] < rev_sorted.iloc[i+1])
            if declines >= 2: rev_declining = True
    except: pass

    stages = {
        1: ("🌱 1단계 : 스타트업 / 개발", "매출 미미 · R&D 투자 집중 단계입니다. 아직 시장 검증 전이며 높은 리스크를 동반합니다."),
        2: ("🚀 2단계 : 초기 고성장", "매출이 폭발적으로 증가하지만 수익화가 안 된 단계입니다. 시장 점유율 확대에 집중합니다."),
        3: ("📈 3단계 : 고성장 흑자전환", "높은 매출 성장과 함께 이익 창출이 시작된 단계입니다. 성장과 수익의 균형점에 진입했습니다."),
        4: ("💪 4단계 : 성숙한 성장", "안정적 매출 성장과 높은 수익성을 보여주는 우량 성장주 단계입니다."),
        5: ("💰 5단계 : 캐시카우", "성장은 둔화되었지만 막대한 현금을 창출합니다. 배당·자사주 매입 등 주주환원이 활발합니다."),
        6: ("⏸️ 6단계 : 정체기", "매출 성장이 멈추고 이익만 유지하는 단계입니다. 새로운 성장 동력이 필요합니다."),
        7: ("📉 7단계 : 쇠퇴기", "매출과 이익이 동반 하락하는 단계입니다. 사업 구조 변화가 없으면 위험할 수 있습니다."),
        8: ("🔧 8단계 : 구조조정/턴어라운드", "적극적인 사업 재편 · 회생을 시도하는 단계입니다. 성공 시 큰 반등이 가능합니다."),
    }
    colors = {1:"#9C27B0",2:"#FF5722",3:"#FF9800",4:"#4CAF50",5:"#2196F3",6:"#607D8B",7:"#F44336",8:"#795548"}

    if rev < 1e8 and margin < -0.20: s = 1
    elif rev_g > 0.30 and margin < 0: s = 2
    elif rev_g > 0.20 and margin > 0: s = 3
    elif rev_g > 0.05 and margin > 0.10: s = 4
    elif 0 <= rev_g <= 0.05 and margin > 0.10 and (div_y > 0.01 or op_cf > rev * 0.1): s = 5
    elif -0.05 <= rev_g <= 0.02 and margin > 0: s = 6
    elif rev_declining and margin < 0: s = 7
    elif rev_g < -0.05 and margin <= 0: s = 8
    elif rev_g < 0 and margin <= 0: s = 8
    elif rev_g > 0.30: s = 2
    elif margin > 0.15 and rev_g > 0.05: s = 4
    elif margin > 0.15: s = 5
    elif margin > 0: s = 6
    else: s = 6
    return s, stages[s][0], stages[s][1], colors[s]

def _stability(financials, row_candidates):
    vals, _ = _annual_values(financials, row_candidates)
    arr = np.array([v for v in vals if v is not None and not np.isnan(v)])
    if len(arr) < 2 or np.mean(arr) == 0: return "데이터 부족", "", "gray"
    cv = np.std(arr) / abs(np.mean(arr))
    if   cv < 0.10: return "매우 안정적 ✅", f"CV {cv:.3f}", "green"
    elif cv < 0.25: return "안정적 ✅",     f"CV {cv:.3f}", "green"
    elif cv < 0.50: return "보통 ⚠️",       f"CV {cv:.3f}", "yellow"
    else:           return "불안정 ❌",      f"CV {cv:.3f}", "red"

def _margin_trend(fin):
    try:
        r_series = _get_row_series(fin, ['Total Revenue'])
        n_series = _get_row_series(fin, ['Net Income'])
        idx = r_series.index.intersection(n_series.index).sort_values()
        margins = [(i, n_series[i]/r_series[i]) for i in idx if r_series[i] != 0]
        if len(margins) < 2: return "N/A", [], "gray"
        first_m, last_m = margins[0][1], margins[-1][1]
        if last_m > first_m + 0.02: return f"증가 추세 📈 ({first_m*100:.1f}% → {last_m*100:.1f}%)", margins, "green"
        if last_m < first_m - 0.02: return f"감소 추세 📉 ({first_m*100:.1f}% → {last_m*100:.1f}%)", margins, "red"
        return f"유지 ➡️ ({last_m*100:.1f}%)", margins, "yellow"
    except Exception: return "N/A", [], "gray"

def _growth_accel(fin, row_candidates):
    vals, _ = _annual_values(fin, row_candidates)
    if len(vals) < 3: return "N/A", "gray"
    g = [(vals[i]-vals[i+1])/abs(vals[i+1]) for i in range(len(vals)-1) if vals[i+1] and vals[i+1] != 0]
    if len(g) < 2: return "N/A", "gray"
    if g[0] > g[1]: return f"가속화 🚀 (최근 {g[0]*100:.1f}% vs 이전 {g[1]*100:.1f}%)", "green"
    return f"감속 🐌 (최근 {g[0]*100:.1f}% vs 이전 {g[1]*100:.1f}%)", "yellow"

def _debt_trend(bs):
    for name_candidates in [['Total Debt'], ['Long Term Debt'], ['Total Liabilities Net Minority Interest']]:
        series = _get_row_series(bs, name_candidates)
        if len(series) >= 2:
            series = series.sort_index(ascending=False)
            latest, oldest = series.iloc[0], series.iloc[-1]
            if oldest != 0:
                chg = (latest - oldest) / abs(oldest)
                if   chg < -0.10: return f"감소 추세 ✅ ({chg*100:.1f}%)", "green"
                elif chg >  0.10: return f"증가 추세 ⚠️ (+{chg*100:.1f}%)", "red"
                else:             return f"안정적 유지 ➡️ ({chg*100:.1f}%)", "yellow"
    return "데이터 부족", "gray"

def _interest_burden(fin, info):
    ebit = _get_row(fin, ['EBIT', 'Operating Income'])
    interest = _get_row(fin, ['Interest Expense', 'Interest Expense Non Operating'])
    if ebit and interest and abs(interest) > 0:
        icr = abs(ebit / interest)
        if   icr > 10: return f"매우 낮음 ✅ (ICR {icr:.1f}x)", "green"
        elif icr >  5: return f"낮음 ✅ (ICR {icr:.1f}x)", "green"
        elif icr >  2: return f"보통 ⚠️ (ICR {icr:.1f}x)", "yellow"
        else:          return f"높음 ❌ (ICR {icr:.1f}x)", "red"

    ebitda, debt = info.get('ebitda', 0) or 0, info.get('totalDebt', 0) or 0
    if ebitda > 0 and debt > 0:
        cov = ebitda / (debt * 0.05)
        if   cov > 10: return f"매우 낮음 ✅ ({cov:.1f}x)", "green"
        elif cov >  5: return f"낮음 ✅ ({cov:.1f}x)", "green"
        elif cov >  2: return f"보통 ⚠️ ({cov:.1f}x)", "yellow"
        else:          return f"높음 ❌ ({cov:.1f}x)", "red"
    return "N/A", "gray"

def _vol_trend(info):
    vol, avg3m = info.get('volume', 0) or 0, info.get('averageVolume', 0) or 0
    if avg3m == 0: return "데이터 부족", "gray"
    r = vol / avg3m
    if   r > 1.5: return f"급증 🔥 (3개월 평균 대비 {r:.1f}배)", "red"
    elif r > 1.1: return f"증가 📈 ({r:.1f}배)", "yellow"
    elif r > 0.9: return f"평균 수준 ➡️ ({r:.1f}배)", "green"
    elif r > 0.5: return f"감소 📉 ({r:.1f}배)", "yellow"
    else:         return f"급감 ⚠️ ({r:.1f}배)", "red"

def _max_pain(tkr):
    try:
        dates = tkr.options
        if not dates: return None, None, None, None
        exp = dates[0]
        o = tkr.option_chain(exp)
        c, p = o.calls, o.puts
        if 'openInterest' not in c.columns: c['openInterest'] = 0
        if 'openInterest' not in p.columns: p['openInterest'] = 0
        c['openInterest'], p['openInterest'] = c['openInterest'].fillna(0), p['openInterest'].fillna(0)

        strikes = sorted(set(c['strike']).union(set(p['strike'])))
        pain = {s: (np.sum(c['openInterest'] * np.maximum(0, s - c['strike'])) + np.sum(p['openInterest'] * np.maximum(0, p['strike'] - s))) for s in strikes}
        mp = min(pain, key=pain.get) if pain else None

        c['volume'], p['volume'] = c['volume'].fillna(0), p['volume'].fillna(0)
        tc = c.nlargest(3, 'volume')[['strike','volume']].to_dict('records')
        tp = p.nlargest(3, 'volume')[['strike','volume']].to_dict('records')
        return exp, mp, tc, tp
    except: return None, None, None, None

def _sector_pe(sector):
    SECTOR_PE_APPROX = {"Technology": 30, "Communication Services": 22, "Consumer Cyclical": 25, "Consumer Defensive": 22, "Financial Services": 14, "Healthcare": 22, "Industrials": 20, "Energy": 12, "Basic Materials": 15, "Real Estate": 35, "Utilities": 18}
    return SECTOR_PE_APPROX.get(sector, None)

# ═══════════════════════════════════════════════════════════════
# 🎨 CSS
# ═══════════════════════════════════════════════════════════════
CSS = """
<style>
.info-card{background:#161A22;border:1px solid #2D333B;border-radius:14px;padding:24px 26px;margin-bottom:22px;box-shadow:0 6px 20px rgba(0,0,0,.25);transition:all .25s}
.info-card:hover{transform:translateY(-3px);border-color:#3e4c59;box-shadow:0 10px 30px rgba(0,0,0,.35)}
.info-title{font-size:1.1rem;font-weight:700;color:#82aaff;margin-bottom:18px;border-bottom:1px solid #2D333B;padding-bottom:12px;display:flex;align-items:center;gap:8px}
.metric-row{display:flex;justify-content:space-between;margin-bottom:10px;font-size:.93rem;align-items:center}
.metric-label{color:#8b949e;font-weight:500}
.metric-value{color:#c9d1d9;font-weight:600;text-align:right;max-width:60%}
.metric-highlight{color:#00E676 !important;font-weight:700}
.metric-warn{color:#FF1744 !important;font-weight:700}
.metric-yellow{color:#FFC107 !important;font-weight:700}
.divider{border-top:1px dashed #2D333B;margin:15px 0}
.opt-box{background:rgba(0,0,0,.2);padding:12px;border-radius:10px;border:1px solid #2D333B}
.opt-list{margin:6px 0 0;padding-left:18px;font-size:.85rem;color:#c9d1d9;line-height:1.8}
.mini-table{width:100%;border-collapse:collapse;font-size:.85rem}
.mini-table th{color:#8b949e;text-align:left;padding:7px 8px;border-bottom:1px solid #2D333B;font-weight:500}
.mini-table td{color:#c9d1d9;padding:7px 8px;border-bottom:1px solid #1c2029}
.progress-container{background:#21262d;border-radius:10px;height:28px;display:flex;overflow:hidden;margin:10px 0}
.progress-bar{height:100%;display:flex;align-items:center;justify-content:center;font-size:.7rem;font-weight:600;color:#fff;transition:width .6s}
.header-wrap{display:flex;justify-content:space-between;align-items:flex-end;flex-wrap:wrap;gap:10px;margin-bottom:6px}
</style>
"""

# ═══════════════════════════════════════════════════════════════
# 🏗️ 메인 렌더링
# ═══════════════════════════════════════════════════════════════
def render_company_details(ticker_str: str):
    st.markdown(CSS, unsafe_allow_html=True)

    with st.spinner(f"📡 {ticker_str} — SEC 공시 + 시장 데이터 분석 중 …"):
        try:
            tkr  = yf.Ticker(ticker_str)
            info = tkr.info or {}
        except:
            st.error("❌ 종목 데이터를 불러올 수 없습니다.")
            return

        if not info or 'shortName' not in info:
            st.error("❌ 유효하지 않은 종목이거나 데이터가 없습니다.")
            return

        fin = tkr.financials if hasattr(tkr, 'financials') else None
        bs = tkr.balance_sheet if hasattr(tkr, 'balance_sheet') else None
        cf = tkr.cashflow if hasattr(tkr, 'cashflow') else None

        cagr_rev = _calc_cagr(fin, ['Total Revenue'])
        cagr_ni  = _calc_cagr(fin, ['Net Income'])
        cagr_eps = _calc_cagr(fin, ['Basic EPS', 'Diluted EPS'])

        sector   = info.get('sector',   'N/A')
        industry = info.get('industry', 'N/A')
        price    = info.get('currentPrice', info.get('regularMarketPrice', None))
        prev_close = info.get('previousClose', price)
        day_chg  = ((price - prev_close) / prev_close * 100) if price and prev_close and prev_close > 0 else 0
        chg_color = "#00E676" if day_chg >= 0 else "#FF1744"
        chg_sign = "+" if day_chg >= 0 else ""

    st.markdown(f"""
    <div class="header-wrap">
        <div>
            <span style="font-size:1.5rem;font-weight:800;color:#e6edf3">🏢 {info.get('shortName', ticker_str)}</span>
            <span style="font-size:1rem;color:#6e7681;margin-left:6px">({ticker_str})</span><br>
            <span style="font-size:.85rem;color:#8b949e">{sector} · {industry}</span>
        </div>
        <div style="text-align:right">
            <span style="font-size:1.6rem;font-weight:800;color:{chg_color}">${price if price else 'N/A'}</span><br>
            <span style="font-size:.9rem;color:{chg_color}">{chg_sign}{day_chg:.2f}% 오늘</span>
        </div>
    </div>""", unsafe_allow_html=True)
    st.markdown("---")

    sn, sname, sdesc, scolor = _growth_stage(info, fin, bs, cf)
    stage_colors_map = {1:"#9C27B0",2:"#FF5722",3:"#FF9800",4:"#4CAF50",5:"#2196F3",6:"#607D8B",7:"#F44336",8:"#795548"}
    stage_labels = {1:"스타트업",2:"초기성장",3:"고성장",4:"성숙성장",5:"캐시카우",6:"정체",7:"쇠퇴",8:"턴어라운드"}
    bar = ""
    for i in range(1, 9):
        is_current = (i == sn)
        bg  = stage_colors_map[i] if is_current else "#21262d"
        op  = "1" if is_current else "0.35"
        brd = f"2px solid {stage_colors_map[i]}" if is_current else "1px solid #2D333B"
        rl  = "border-radius:10px 0 0 10px;" if i==1 else ("border-radius:0 10px 10px 0;" if i==8 else "")
        fw  = "700" if is_current else "400"
        bar += f"<div style='flex:1;background:{bg};opacity:{op};text-align:center;padding:10px 2px;font-size:.65rem;color:#fff;border:{brd};{rl};font-weight:{fw}'>{i}<br>{stage_labels[i]}</div>"

    verdict_1_color = "green" if sn in [3,4] else ("blue" if sn == 5 else ("yellow" if sn in [1,2,6] else "red"))
    verdict_1_text = {1: "초기 단계 — 높은 리스크, 높은 잠재력", 2: "폭풍 성장 중 — 적자이지만 매출 급증", 3: "성장 + 이익 = 투자 최적 시점 가능", 4: "안정 성장 우량주 — 핵심 보유 후보", 5: "현금 창출 기계 — 배당·안정성 우선", 6: "새 성장 동력이 필요한 시점", 7: "위험 — 구조적 하락 가능성 주의", 8: "턴어라운드 성공 여부가 핵심"}

    st.markdown(f"""
    <div class="info-card">
        <div class="info-title">🔄 1. 이 회사, 지금 어느 단계인가요?</div>
        <div style="display:flex;gap:2px;margin-bottom:18px">{bar}</div>
        <div style="text-align:center">
            <span style="display:inline-block;padding:8px 20px;border-radius:22px;font-weight:700;background:{scolor};color:#fff;font-size:1.05rem">{sname}</span>
            <div style="font-size:.88rem;color:#8b949e;margin-top:10px;line-height:1.6">{sdesc}</div>
        </div>
        <div class="divider"></div>
        <div class="metric-row"><span class="metric-label">YOY 매출 성장률</span><span class="metric-value">{_fmt_pct(info.get('revenueGrowth'))}</span></div>
        <div class="metric-row"><span class="metric-label">순이익률</span><span class="metric-value">{_fmt_pct(info.get('profitMargins'))}</span></div>
        <div class="metric-row"><span class="metric-label">배당수익률</span><span class="metric-value">{_fmt_pct(info.get('dividendYield'))}</span></div>
        <div class="metric-row"><span class="metric-label">ROE</span><span class="metric-value">{_fmt_pct(info.get('returnOnEquity'))}</span></div>
        {_verdict_badge(verdict_1_color, "📌", f"종합: {verdict_1_text.get(sn, '')}")}
    </div>""", unsafe_allow_html=True)

    gross_m = info.get('grossMargins')
    net_m   = info.get('profitMargins')
    mcap    = info.get('marketCap')
    ttm_eps = info.get('trailingEps')
    ttm_rev = info.get('totalRevenue')
    ttm_ni  = info.get('netIncomeToCommon')

    profit_score = sum([1 for c in [gross_m and gross_m > 0.4, net_m and net_m > 0.1, cagr_rev and cagr_rev > 0.05, cagr_ni and cagr_ni > 0.05, ttm_ni and ttm_ni > 0] if c])
    if   profit_score >= 4: v2_color, v2_text = "green",  "💰 매우 우수 — 높은 마진 + 지속 성장"
    elif profit_score >= 3: v2_color, v2_text = "green",  "✅ 양호 — 수익성과 성장을 겸비"
    elif profit_score >= 2: v2_color, v2_text = "yellow", "⚠️ 보통 — 일부 지표 개선 필요"
    else:                   v2_color, v2_text = "red",    "❌ 수익성 미흡 — 적자 또는 마진 악화"

    st.markdown(f"""
    <div class="info-card">
        <div class="info-title">💵 2. 돈을 잘 버는 회사인가요? (SEC)</div>
        <div class="metric-row"><span class="metric-label">시가총액</span><span class="metric-value">{_fmt_num(mcap)}</span></div>
        <div class="metric-row"><span class="metric-label">TTM 주당순이익 (EPS)</span><span class="metric-value">${_safe(ttm_eps)}</span></div>
        <div class="metric-row"><span class="metric-label">최근 12개월 매출</span><span class="metric-value">{_fmt_num(ttm_rev)}</span></div>
        <div class="metric-row"><span class="metric-label">최근 12개월 순이익</span><span class="metric-value {'metric-highlight' if ttm_ni and ttm_ni > 0 else 'metric-warn'}">{_fmt_num(ttm_ni)}</span></div>
        <div class="divider"></div>
        <div class="metric-row"><span class="metric-label">총이익률 (Gross Margin)</span><span class="metric-value">{_fmt_pct(gross_m)}</span></div>
        <div class="metric-row"><span class="metric-label">순이익률 (Net Margin)</span><span class="metric-value">{_fmt_pct(net_m)}</span></div>
        <div class="divider"></div>
        <div class="metric-row"><span class="metric-label">5년 매출 CAGR</span><span class="metric-value {'metric-highlight' if cagr_rev and cagr_rev > 0 else 'metric-warn'}">{_fmt_pct(cagr_rev)}</span></div>
        <div class="metric-row"><span class="metric-label">5년 순이익 CAGR</span><span class="metric-value {'metric-highlight' if cagr_ni and cagr_ni > 0 else 'metric-warn'}">{_fmt_pct(cagr_ni)}</span></div>
        <div class="metric-row"><span class="metric-label">5년 EPS CAGR</span><span class="metric-value {'metric-highlight' if cagr_eps and cagr_eps > 0 else 'metric-warn'}">{_fmt_pct(cagr_eps)}</span></div>
        {_verdict_badge(v2_color, "📌", v2_text)}
    </div>""", unsafe_allow_html=True)

    rev_stab, rev_cv, stab_color = _stability(fin, ['Total Revenue'])
    mtrend, _, mtrend_color = _margin_trend(fin)
    accel, accel_color = _growth_accel(fin, ['Total Revenue'])
    roe = info.get('returnOnEquity')

    if roe is not None:
        if   roe > 0.20: roe_lbl, roe_c = f"매우 높음 ✅ ({_fmt_pct(roe)})", "green"
        elif roe > 0.10: roe_lbl, roe_c = f"양호 ✅ ({_fmt_pct(roe)})", "green"
        elif roe > 0:    roe_lbl, roe_c = f"보통 ⚠️ ({_fmt_pct(roe)})", "yellow"
        else:            roe_lbl, roe_c = f"음수 ❌ ({_fmt_pct(roe)})", "red"
    else: roe_lbl, roe_c = "N/A", "gray"

    rv, rd = _annual_values(fin, ['Total Revenue'])
    nv, nd = _annual_values(fin, ['Net Income'])
    rows = ""
    for i in range(min(len(rv), len(nv), 4)):
        yr = rd[i].strftime('%Y') if hasattr(rd[i], 'strftime') else str(rd[i])[:4]
        mg = (nv[i] / rv[i] * 100) if rv[i] and rv[i] != 0 else 0
        rev_color = "#00E676" if rv[i] and rv[i] > 0 else "#FF1744"
        ni_color  = "#00E676" if nv[i] and nv[i] > 0 else "#FF1744"
        mg_color  = "#00E676" if mg > 0 else "#FF1744"
        rows += f"<tr><td>{yr}</td><td style='color:{rev_color}'>{_fmt_num(rv[i])}</td><td style='color:{ni_color}'>{_fmt_num(nv[i])}</td><td style='color:{mg_color}'>{mg:.1f}%</td></tr>"

    score3 = sum([1 for c in [stab_color, mtrend_color, accel_color, roe_c] if c == "green"])
    if   score3 >= 3: v3_color, v3_text = "green",  "✅ 우수한 트랙 레코드 — 안정적 성장과 높은 ROE"
    elif score3 >= 2: v3_color, v3_text = "yellow", "⚠️ 보통 — 일부 지표는 양호하나 개선 여지 있음"
    else:             v3_color, v3_text = "red",    "❌ 주의 — 수익 불안정 또는 하락 추세"

    st.markdown(f"""
    <div class="info-card">
        <div class="info-title">📊 3. 지금까지 성적 (SEC)</div>
        <div class="metric-row"><span class="metric-label">수익 안정성</span><span class="metric-value">{rev_stab} <span style="font-size:.78rem;color:#6e7681"> {rev_cv}</span></span></div>
        <div class="metric-row"><span class="metric-label">이익 마진 추이</span><span class="metric-value">{mtrend}</span></div>
        <div class="metric-row"><span class="metric-label">성장 가속화</span><span class="metric-value">{accel}</span></div>
        <div class="metric-row"><span class="metric-label">ROE 수준</span><span class="metric-value">{roe_lbl}</span></div>
        <div class="divider"></div>
        <table class="mini-table"><tr><th>연도</th><th>매출</th><th>순이익</th><th>순이익률</th></tr>{rows}</table>
        {_verdict_badge(v3_color, "📌", v3_text)}
    </div>""", unsafe_allow_html=True)

    payout    = info.get('payoutRatio', 0) or 0
    retention = max(0, 1 - payout)
    roe_val   = info.get('returnOnEquity', 0) or 0
    fut_roe   = roe_val * retention if roe_val else None
    eg        = info.get('earningsGrowth')
    rg        = info.get('revenueGrowth')
    peg       = info.get('pegRatio')
    fwd_eps   = info.get('forwardEps')

    g_score = sum([1 for c in [eg and eg > 0.15, rg and rg > 0.10, retention > 0.60, fut_roe and fut_roe > 0.10, peg and 0 < peg < 1.5] if c])
    if   g_score >= 4: v4_color, v4_text = "green",  "🚀 높은 성장 잠재력 — 수익 재투자 + 고성장"
    elif g_score >= 2: v4_color, v4_text = "yellow", "⚠️ 보통 — 성장 가능성은 있으나 모니터링 필요"
    else:              v4_color, v4_text = "red",    "❌ 성장 둔화 — 새로운 동력 부재"

    st.markdown(f"""
    <div class="info-card">
        <div class="info-title">🚀 4. 성장 가능성 (SEC + Yahoo)</div>
        <div class="metric-row"><span class="metric-label">이익 성장률 (YOY)</span><span class="metric-value {'metric-highlight' if eg and eg>0 else 'metric-warn'}">{_fmt_pct(eg)}</span></div>
        <div class="metric-row"><span class="metric-label">매출 성장률 (YOY)</span><span class="metric-value {'metric-highlight' if rg and rg>0 else 'metric-warn'}">{_fmt_pct(rg)}</span></div>
        <div class="divider"></div>
        <div class="metric-row"><span class="metric-label">ROE</span><span class="metric-value">{_fmt_pct(roe_val)}</span></div>
        <div class="metric-row"><span class="metric-label">수익 유보율(저축률)</span><span class="metric-value">{_fmt_pct(retention)}</span></div>
        <div class="metric-row"><span class="metric-label">미래 예상 ROE (ROE×유보율)</span><span class="metric-value {'metric-highlight' if fut_roe and fut_roe > 0.1 else 'metric-value'}">{_fmt_pct(fut_roe)}</span></div>
        <div class="divider"></div>
        <div class="metric-row"><span class="metric-label">Forward EPS</span><span class="metric-value">${_safe(fwd_eps)}</span></div>
        <div class="metric-row"><span class="metric-label">PEG 비율</span><span class="metric-value {'metric-highlight' if peg and 0 < peg < 1.5 else 'metric-value'}">{_safe(peg)}</span></div>
        {_verdict_badge(v4_color, "📌", v4_text)}
    </div>""", unsafe_allow_html=True)

    try:
        curr_d = _get_row(bs, ['Current Debt', 'Current Portion Of Long Term Debt']) or 0
        lt_d   = _get_row(bs, ['Long Term Debt', 'Long Term Debt And Capital Lease Obligation']) or 0
        ta     = _get_row(bs, ['Total Assets']) or info.get('totalAssets', 0) or 0
        tl     = _get_row(bs, ['Total Liabilities Net Minority Interest', 'Total Liab']) or 0
        eq     = _get_row(bs, ['Stockholders Equity', 'Total Stockholder Equity']) or 0
        na     = ta - tl
    except: curr_d = lt_d = ta = tl = eq = na = 0

    dt_trend, dt_color = _debt_trend(bs)
    i_burden, ib_color = _interest_burden(fin, info)
    dte = info.get('debtToEquity', None)
    cash = info.get('totalCash', 0) or 0

    if isinstance(dte, (int, float)):
        if   dte < 50:  dl, dl_c = "낮음 ✅", "green"
        elif dte < 100: dl, dl_c = "보통 ⚠️", "yellow"
        elif dte < 200: dl, dl_c = "높음 ⚠️", "red"
        else:           dl, dl_c = "매우 높음 ❌", "red"
    else: dl, dl_c = "N/A", "gray"

    h_score = sum([1 for c in [dl_c == "green", dt_color == "green", ib_color == "green", cash > tl * 0.2] if c])
    if   h_score >= 3: v5_color, v5_text = "green",  "💪 재무 건전 — 낮은 부채, 충분한 현금"
    elif h_score >= 2: v5_color, v5_text = "yellow", "⚠️ 보통 — 부채 관리 모니터링 필요"
    else:              v5_color, v5_text = "red",    "❌ 주의 — 부채 수준이 높거나 현금 부족"

    st.markdown(f"""
    <div class="info-card">
        <div class="info-title">🏦 5. 회사에 돈이 얼마나 있나요? (SEC + Yahoo)</div>
        <div class="metric-row"><span class="metric-label">💵 보유 현금</span><span class="metric-value metric-highlight">{_fmt_num(cash)}</span></div>
        <div class="metric-row"><span class="metric-label">단기 부채</span><span class="metric-value">{_fmt_num(curr_d)}</span></div>
        <div class="metric-row"><span class="metric-label">장기 부채</span><span class="metric-value">{_fmt_num(lt_d)}</span></div>
        <div class="divider"></div>
        <div class="metric-row"><span class="metric-label">부채 수준</span><span class="metric-value">{dl}</span></div>
        <div class="metric-row"><span class="metric-label">부채 추세</span><span class="metric-value">{dt_trend}</span></div>
        <div class="metric-row"><span class="metric-label">이자 부담 (ICR)</span><span class="metric-value">{i_burden}</span></div>
        <div class="metric-row"><span class="metric-label">부채/자본 비율 (D/E)</span><span class="metric-value">{f'{dte:.1f}%' if isinstance(dte,(int,float)) else 'N/A'}</span></div>
        <div class="divider"></div>
        <div class="metric-row"><span class="metric-label">총 자산</span><span class="metric-value">{_fmt_num(ta)}</span></div>
        <div class="metric-row"><span class="metric-label">총 부채</span><span class="metric-value">{_fmt_num(tl)}</span></div>
        <div class="metric-row"><span class="metric-label">자본 (Equity)</span><span class="metric-value">{_fmt_num(eq)}</span></div>
        <div class="metric-row"><span class="metric-label">순 자산 (자산-부채)</span><span class="metric-value {'metric-highlight' if na > 0 else 'metric-warn'}">{_fmt_num(na)}</span></div>
        {_verdict_badge(v5_color, "📌", v5_text)}
    </div>""", unsafe_allow_html=True)

    vol   = info.get('volume', 0) or 0
    avg10 = info.get('averageVolume10days', 0) or 0
    avg3m = info.get('averageVolume', 0) or 0
    vt, vt_color = _vol_trend(info)

    if   vt_color == "green":  v6_color, v6_text = "green",  "✅ 거래량 정상 — 유동성 양호"
    elif vt_color == "yellow": v6_color, v6_text = "yellow", "⚠️ 거래량 변동 감지 — 추이 주시"
    else:                      v6_color, v6_text = "red",    "🔥 거래량 이상 — 급변 가능성 주의"

    st.markdown(f"""
    <div class="info-card">
        <div class="info-title">📈 6. 지금 사람들이 많이 사고 있나요? (Yahoo)</div>
        <div class="metric-row"><span class="metric-label">현재 거래량</span><span class="metric-value">{_fmt_num(vol, False)} 주</span></div>
        <div class="metric-row"><span class="metric-label">10일 평균 거래량</span><span class="metric-value">{_fmt_num(avg10, False)} 주</span></div>
        <div class="metric-row"><span class="metric-label">3개월 평균 거래량</span><span class="metric-value">{_fmt_num(avg3m, False)} 주</span></div>
        <div class="divider"></div>
        <div class="metric-row"><span class="metric-label">거래량 변동 추이</span><span class="metric-value">{vt}</span></div>
        {_verdict_badge(v6_color, "📌", v6_text)}
    </div>""", unsafe_allow_html=True)

    beta = info.get('beta', None)
    if isinstance(beta, (int, float)):
        if   beta < 0.8: bl, beta_c = "저변동 — 시장보다 안정", "green"
        elif beta < 1.2: bl, beta_c = "시장과 유사", "yellow"
        elif beta < 1.5: bl, beta_c = "높은 변동성 ⚠️", "red"
        else:            bl, beta_c = "매우 높은 변동성 🔥", "red"
    else: bl, beta_c = "N/A", "gray"

    w52h = info.get('fiftyTwoWeekHigh', None)
    w52l = info.get('fiftyTwoWeekLow', None)
    w52_change = info.get('52WeekChange', None)
    
    # 🚀 HTML 코드 블록으로 파싱되는 것을 방지하기 위해 1줄짜리 평탄화(Flatten) 된 문자열 사용
    if price and w52h and w52l and w52h != w52l:
        pos52 = (price - w52l) / (w52h - w52l) * 100
        pos52_str = f"{pos52:.1f}%"
        pos_bar = f"<div style='margin:8px 0'><div style='display:flex;justify-content:space-between;font-size:.75rem;color:#6e7681;margin-bottom:3px'><span>${w52l:.2f}</span><span>현재 ${price:.2f}</span><span>${w52h:.2f}</span></div><div style='background:#21262d;border-radius:6px;height:10px;position:relative'><div style='background:linear-gradient(90deg,#FF1744,#FFC107,#00E676);width:100%;height:100%;border-radius:6px;opacity:0.3'></div><div style='position:absolute;top:-2px;left:{pos52:.1f}%;width:14px;height:14px;background:#82aaff;border-radius:50%;transform:translateX(-50%);border:2px solid #fff'></div></div></div>"
    else:
        pos52_str, pos_bar = "N/A", ""

    v7_color = beta_c
    v7_text = f"베타 {beta:.2f} — {bl}" if isinstance(beta, (int,float)) else "변동성 데이터 부족"

    st.markdown(f"""
    <div class="info-card">
        <div class="info-title">🎢 7. 변동성이 큰가요? (Yahoo)</div>
        <div class="metric-row"><span class="metric-label">베타 (β)</span><span class="metric-value">{f'{beta:.2f}' if isinstance(beta,(int,float)) else 'N/A'} ({bl})</span></div>
        <div class="metric-row"><span class="metric-label">52주 가격 변화율</span><span class="metric-value {'metric-highlight' if w52_change and w52_change > 0 else 'metric-warn'}">{_fmt_pct(w52_change)}</span></div>
        <div class="divider"></div>
        <div class="metric-row"><span class="metric-label">52주 최고가</span><span class="metric-value">${w52h if w52h else 'N/A'}</span></div>
        <div class="metric-row"><span class="metric-label">52주 최저가</span><span class="metric-value">${w52l if w52l else 'N/A'}</span></div>
        <div class="metric-row"><span class="metric-label">현재가 위치 (52주 내)</span><span class="metric-value">{pos52_str}</span></div>
        {pos_bar}
        {_verdict_badge(v7_color, "📌", v7_text)}
    </div>""", unsafe_allow_html=True)

    t_pe = info.get('trailingPE')
    f_pe = info.get('forwardPE')
    ps   = info.get('priceToSalesTrailing12Months')
    pb   = info.get('priceToBook')
    s_pe = _sector_pe(sector)

    pe_comp = ""
    if t_pe and s_pe:
        diff = ((t_pe - s_pe) / s_pe) * 100
        if   diff > 30:  pe_comp = f"섹터 대비 <b style='color:#FF1744'>고평가 (+{diff:.0f}%)</b>"
        elif diff > 0:   pe_comp = f"섹터 대비 <b style='color:#FFC107'>약간 고평가 (+{diff:.0f}%)</b>"
        elif diff > -20: pe_comp = f"섹터 대비 <b style='color:#00E676'>적정 ({diff:.0f}%)</b>"
        else:            pe_comp = f"섹터 대비 <b style='color:#00E676'>저평가 ({diff:.0f}%)</b>"

    if t_pe and s_pe:
        if t_pe < s_pe * 0.8:  v8_color, v8_text = "green",  "💎 저평가 가능성 — 섹터 평균 대비 할인"
        elif t_pe < s_pe * 1.3:  v8_color, v8_text = "yellow", "⚖️ 적정 수준 — 섹터 평균과 유사"
        else:                    v8_color, v8_text = "red",    "💸 고평가 가능성 — 프리미엄 가격"
    else: v8_color, v8_text = "gray", "비교 데이터 부족"

    st.markdown(f"""
    <div class="info-card">
        <div class="info-title">⚖️ 8. 이 종목 비싼가요? (Yahoo)</div>
        <div class="metric-row"><span class="metric-label">Trailing P/E (주가수익비율)</span><span class="metric-value">{f'{t_pe:.2f}' if isinstance(t_pe,(int,float)) else 'N/A'}</span></div>
        <div class="metric-row"><span class="metric-label">Forward P/E</span><span class="metric-value">{f'{f_pe:.2f}' if isinstance(f_pe,(int,float)) else 'N/A'}</span></div>
        <div class="metric-row"><span class="metric-label">P/S (주가매출비율, TTM)</span><span class="metric-value">{f'{ps:.2f}' if isinstance(ps,(int,float)) else 'N/A'}</span></div>
        <div class="metric-row"><span class="metric-label">P/B (주가순자산비율)</span><span class="metric-value">{f'{pb:.2f}' if isinstance(pb,(int,float)) else 'N/A'}</span></div>
        <div class="divider"></div>
        <div class="metric-row"><span class="metric-label">섹터 ({sector})</span><span class="metric-value">평균 P/E ≈ {s_pe if s_pe else 'N/A'}</span></div>
        <div class="metric-row"><span class="metric-label">섹터 대비 평가</span><span class="metric-value">{pe_comp if pe_comp else 'N/A'}</span></div>
        {_verdict_badge(v8_color, "📌", v8_text)}
    </div>""", unsafe_allow_html=True)

    rm = info.get('recommendationMean', None)
    rk = str(info.get('recommendationKey', 'N/A')).upper()
    if isinstance(rm, (int, float)):
        if   rm <= 1.5: con, con_c = "🟢 강력 매수 (Strong Buy)",  "green"
        elif rm <= 2.0: con, con_c = "🟢 매수 (Buy)",             "green"
        elif rm <= 2.5: con, con_c = "🟡 매수 우위 (Outperform)", "yellow"
        elif rm <= 3.0: con, con_c = "🟡 보유 (Hold)",            "yellow"
        elif rm <= 3.5: con, con_c = "🟠 매도 우위 (Underperform)", "red"
        elif rm <= 4.0: con, con_c = "🔴 매도 (Sell)",            "red"
        else:           con, con_c = "🔴 강력 매도 (Strong Sell)", "red"
    else: con, con_c = "N/A", "gray"

    target_mean   = info.get('targetMeanPrice')
    target_median = info.get('targetMedianPrice')
    target_high   = info.get('targetHighPrice')
    target_low    = info.get('targetLowPrice')
    n_analysts    = info.get('numberOfAnalystOpinions', 0)

    try:
        if target_median and price and price > 0:
            upside_pct = ((target_median - price) / price) * 100
            upside_str = f"{'📈' if upside_pct > 0 else '📉'} {upside_pct:+.1f}%"
        else: upside_str, upside_pct = "N/A", 0
    except: upside_str, upside_pct = "N/A", 0

    v9_text = f"애널리스트 {n_analysts}명 컨센서스: {rk} (목표가 대비 {upside_str})"

    st.markdown(f"""
    <div class="info-card">
        <div class="info-title">👨‍💼 9. 전문가들의 의견 (Yahoo)</div>
        <div class="metric-row"><span class="metric-label">컨센서스 등급</span><span class="metric-value metric-highlight">{rk}</span></div>
        <div class="metric-row"><span class="metric-label">평균 의견 점수 (1매수~5매도)</span><span class="metric-value">{f'{rm:.2f}' if isinstance(rm,(int,float)) else 'N/A'}</span></div>
        <div class="metric-row"><span class="metric-label">종합 의견</span><span class="metric-value">{con}</span></div>
        <div class="divider"></div>
        <div class="metric-row"><span class="metric-label">평균 목표가</span><span class="metric-value">${_safe(target_mean)}</span></div>
        <div class="metric-row"><span class="metric-label">중앙값 목표가</span><span class="metric-value">${_safe(target_median)}</span></div>
        <div class="metric-row"><span class="metric-label">최고 목표가</span><span class="metric-value">${_safe(target_high)}</span></div>
        <div class="metric-row"><span class="metric-label">최저 목표가</span><span class="metric-value">${_safe(target_low)}</span></div>
        <div class="metric-row"><span class="metric-label">참여 애널리스트</span><span class="metric-value">{n_analysts}명</span></div>
        <div class="divider"></div>
        <div style="text-align:center;font-size:1rem;color:{'#00E676' if upside_pct > 0 else '#FF1744'};font-weight:700;padding:6px 0">
            목표가 대비 현재가 여력: {upside_str}
        </div>
        {_verdict_badge(con_c, "📌", v9_text)}
    </div>""", unsafe_allow_html=True)

    inst = info.get('heldPercentInstitutions', 0) or 0
    ins  = info.get('heldPercentInsiders', 0)     or 0
    pub  = max(0, 1 - inst - ins)
    shares_out = info.get('sharesOutstanding', 0) or 0
    float_shares = info.get('floatShares', 0) or 0

    if inst > 0.7: v10_color, v10_text = "green", "✅ 기관 선호 종목 — 높은 기관 보유 비율"
    elif inst > 0.4: v10_color, v10_text = "yellow", "⚠️ 기관 보유 보통 — 혼합 지분 구조"
    else: v10_color, v10_text = "red", "⚠️ 기관 보유 낮음 — 개인 중심 거래"

    st.markdown(f"""
    <div class="info-card">
        <div class="info-title">👥 10. 이 회사 누가 들고 있나요? (Yahoo)</div>
        <div class="metric-row"><span class="metric-label">총 발행 주식수</span><span class="metric-value">{_fmt_num(shares_out, False)} 주</span></div>
        <div class="metric-row"><span class="metric-label">유통 주식수 (Float)</span><span class="metric-value">{_fmt_num(float_shares, False)} 주</span></div>
        <div class="divider"></div>
        <div class="metric-row"><span class="metric-label">🏛️ 기관 투자자</span><span class="metric-value">{_fmt_pct(inst)}</span></div>
        <div class="metric-row"><span class="metric-label">👔 내부자 / 임원</span><span class="metric-value">{_fmt_pct(ins)}</span></div>
        <div class="metric-row"><span class="metric-label">👤 일반 / 개인 (추정)</span><span class="metric-value">{_fmt_pct(pub)}</span></div>
        <div class="divider"></div>
        <div style="font-size:.83rem;color:#6e7681;margin-bottom:4px">지분 구성 비율</div>
        <div class="progress-container">
            <div class="progress-bar" style="width:{inst*100:.1f}%;background:#2196F3">{'기관 ' + str(round(inst*100)) + '%' if inst > 0.08 else ''}</div>
            <div class="progress-bar" style="width:{ins*100:.1f}%;background:#FF9800">{'내부 ' + str(round(ins*100)) + '%' if ins > 0.05 else ''}</div>
            <div class="progress-bar" style="width:{pub*100:.1f}%;background:#4CAF50">{'일반 ' + str(round(pub*100)) + '%' if pub > 0.08 else ''}</div>
        </div>
        {_verdict_badge(v10_color, "📌", v10_text)}
    </div>""", unsafe_allow_html=True)

    exp, mp, tc, tp = _max_pain(tkr)
    
    # 🚀 버그 수정: ValueError 해결을 위해 f-string 포맷팅 안전 처리
    mp_val_str = f"${mp:.2f}" if mp else ""
    mp_html = f"<span class='metric-value' style='font-size:1.15rem;font-weight:800;color:#82aaff'>{mp_val_str}</span>" if mp else "<span class='metric-value'>데이터 없음</span>"
    exp_html = f"(만기일: {exp})" if exp else ""

    mp_note = ""
    mp_color = "gray"
    if mp and isinstance(price, (int, float)) and price > 0:
        d = ((mp - price) / price) * 100
        if d > 2:
            mp_note = f"현재가보다 {d:+.1f}% 위 → 상승 압력 가능"
            mp_color = "green"
        elif d < -2:
            mp_note = f"현재가보다 {d:+.1f}% 아래 → 하락 압력 가능"
            mp_color = "red"
        else:
            mp_note = f"현재가와 유사 ({d:+.1f}%) → 횡보 가능"
            mp_color = "yellow"

    ch = "".join([f"<li>${c_item['strike']:.1f} <span style='color:#6e7681'>(Vol: {int(c_item['volume']):,})</span></li>" for c_item in (tc or [])]) or "<li>N/A</li>"
    ph = "".join([f"<li>${p_item['strike']:.1f} <span style='color:#6e7681'>(Vol: {int(p_item['volume']):,})</span></li>" for p_item in (tp or [])]) or "<li>N/A</li>"
    
    mp_badge_text = f"Max Pain {mp_val_str} — {mp_note}" if mp else "옵션 데이터 없음"

    st.markdown(f"""
    <div class="info-card">
        <div class="info-title">🎯 11. 시장은 어떤 가격을 보고 있을까요? (Yahoo 옵션)</div>
        <div class="metric-row"><span class="metric-label">Max Pain 가격 {exp_html}</span><span style="margin-left:12px">{mp_html}</span></div>
        <div class="metric-row"><span class="metric-label">해석</span><span class="metric-value">{mp_note}</span></div>
        <div class="divider"></div>
        <div style="display:flex;justify-content:space-between;gap:16px;margin-top:10px;flex-wrap:wrap">
            <div class="opt-box" style="flex:1;min-width:200px">
                <b style="color:#00E676;font-size:.9rem">🟢 Call (상승 베팅) Top 3</b>
                <ul class="opt-list">{ch}</ul>
            </div>
            <div class="opt-box" style="flex:1;min-width:200px">
                <b style="color:#FF1744;font-size:.9rem">🔴 Put (하락 베팅) Top 3</b>
                <ul class="opt-list">{ph}</ul>
            </div>
        </div>
        {_verdict_badge(mp_color, "📌", mp_badge_text)}
    </div>""", unsafe_allow_html=True)

    sp = info.get('shortPercentOfFloat')
    shares_short = info.get('sharesShort', 0) or 0
    short_ratio  = info.get('shortRatio')
    prev_shares_short = info.get('sharesShortPriorMonth', 0) or 0

    if isinstance(sp, (int, float)):
        if   sp > 0.20: sl, sl_c = "매우 높음 🔴 (숏 스퀴즈 가능성)", "red"
        elif sp > 0.10: sl, sl_c = "높음 🟠", "red"
        elif sp > 0.05: sl, sl_c = "보통 🟡", "yellow"
        else:           sl, sl_c = "낮음 🟢", "green"
    else: sl, sl_c = "N/A", "gray"

    short_trend = ""
    if shares_short > 0 and prev_shares_short > 0:
        s_chg = ((shares_short - prev_shares_short) / prev_shares_short) * 100
        if s_chg > 5:    short_trend = f"증가 📈 ({s_chg:+.1f}% vs 전월)"
        elif s_chg < -5: short_trend = f"감소 📉 ({s_chg:+.1f}% vs 전월)"
        else:            short_trend = f"유지 ➡️ ({s_chg:+.1f}% vs 전월)"

    v12_text = f"공매도 {_fmt_pct(sp)} — {sl}"

    st.markdown(f"""
    <div class="info-card">
        <div class="info-title">📉 12. 공매도 비율 (Yahoo)</div>
        <div class="metric-row"><span class="metric-label">유통주식 대비 공매도 비율</span><span class="metric-value {'metric-warn' if sl_c == 'red' else 'metric-value'}">{_fmt_pct(sp)}</span></div>
        <div class="metric-row"><span class="metric-label">공매도 수준</span><span class="metric-value">{sl}</span></div>
        <div class="metric-row"><span class="metric-label">공매도 주식수</span><span class="metric-value">{_fmt_num(shares_short, False)} 주</span></div>
        <div class="metric-row"><span class="metric-label">발행 주식수</span><span class="metric-value">{_fmt_num(info.get('sharesOutstanding'), False)} 주</span></div>
        <div class="metric-row"><span class="metric-label">숏 커버 일수 (DTC)</span><span class="metric-value">{f'{short_ratio:.2f}' if isinstance(short_ratio,(int,float)) else 'N/A'} 일</span></div>
        {'<div class="metric-row"><span class="metric-label">전월 대비 공매도 추세</span><span class="metric-value">' + short_trend + '</span></div>' if short_trend else ''}
        {_verdict_badge(sl_c, "📌", v12_text)}
    </div>""", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════
    # 📋  종합 점수 요약
    # ════════════════════════════════════════════════════
    total_score = 0
    max_score = 0
    # 🚀 11번 옵션 항목까지 12개 모두 추가 완료
    score_items = [
        ("성장 사이클", verdict_1_color),
        ("수익성", v2_color),
        ("과거 성적", v3_color),
        ("성장성", v4_color),
        ("재무 건전", v5_color),
        ("시장 수급", v6_color),
        ("변동성", v7_color),
        ("밸류에이션", v8_color),
        ("전문가", con_c),
        ("지분 구조", v10_color),
        ("옵션/파생", mp_color), 
        ("공매도", sl_c),
    ]
    for name, color in score_items:
        max_score += 2
        if   color == "green":  total_score += 2
        elif color == "yellow": total_score += 1
        elif color == "blue":   total_score += 1.5

    pct_score = (total_score / max_score * 100) if max_score > 0 else 0

    if   pct_score >= 75: overall_color, overall_emoji, overall_text = "#00E676", "🟢", "매우 양호"
    elif pct_score >= 55: overall_color, overall_emoji, overall_text = "#FFC107", "🟡", "보통"
    elif pct_score >= 35: overall_color, overall_emoji, overall_text = "#FF9800", "🟠", "주의 필요"
    else:                 overall_color, overall_emoji, overall_text = "#FF1744", "🔴", "위험"

    score_rows = ""
    for name, color in score_items:
        dot = {"green":"🟢","yellow":"🟡","red":"🔴","blue":"🔵","gray":"⚪"}.get(color, "⚪")
        score_rows += f"<td style='text-align:center'>{dot}<br><span style='font-size:.7rem;color:#8b949e'>{name}</span></td>"

    st.markdown(f"""
    <div class="info-card" style="border-color:{overall_color}">
        <div class="info-title">📋 종합 분석 요약</div>
        <div style="text-align:center;margin-bottom:15px">
            <span style="font-size:2rem;font-weight:900;color:{overall_color}">
                {overall_emoji} {pct_score:.0f}점 / 100점
            </span>
            <br>
            <span style="font-size:1.1rem;color:{overall_color};font-weight:600">{overall_text}</span>
        </div>
        <div style="background:#21262d;border-radius:10px;height:14px;margin:10px 0;overflow:hidden">
            <div style="width:{pct_score:.1f}%;height:100%;background:{overall_color};
                        border-radius:10px;transition:width 1s"></div>
        </div>
        <div style="overflow-x:auto;">
            <table style="width:100%;margin-top:12px;border:none;">
                <tr>{score_rows}</tr>
            </table>
        </div>
    </div>""", unsafe_allow_html=True)

    st.caption("⚠️ 본 분석은 참고용이며 투자 조언이 아닙니다. 투자 결정은 본인의 판단과 책임 하에 이루어져야 합니다.")

if __name__ == "__main__":
    st.set_page_config(page_title="종목 상세 분석", layout="wide")
    ticker_input = st.text_input("티커 입력", value="AAPL")
    if ticker_input:
        render_company_details(ticker_input.upper())