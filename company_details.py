import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# ═════════════════════════════════════════════════════════
# 🛠️  유틸리티 함수
# ═════════════════════════════════════════════════════════

def _fmt_num(num, is_currency=True):
    """숫자를 읽기 쉬운 형식으로 변환"""
    if pd.isna(num) or num is None:
        return "N/A"
    prefix = "$" if is_currency else ""
    sign = "-" if num < 0 else ""
    a = abs(num)
    if a >= 1e12:   return f"{sign}{prefix}{a/1e12:.2f}T"
    elif a >= 1e9:  return f"{sign}{prefix}{a/1e9:.2f}B"
    elif a >= 1e6:  return f"{sign}{prefix}{a/1e6:.2f}M"
    elif a >= 1e3:  return f"{sign}{prefix}{a/1e3:.2f}K"
    return f"{sign}{prefix}{num:,.0f}"

def _fmt_pct(num):
    """소수를 퍼센트 문자열로 변환"""
    if pd.isna(num) or num is None:
        return "N/A"
    return f"{num * 100:.2f}%"

def _safe(val, fallback="N/A"):
    return val if val is not None else fallback

def _calc_cagr(financials, row_name):
    """SEC 손익계산서 기반 CAGR (연평균 성장률) 계산"""
    try:
        if row_name in financials.index:
            # yfinance는 최신 데이터가 index 0에 위치함
            data = financials.loc[row_name].dropna()
            if len(data) >= 2:
                # 🚀 버그 수정: 과거 데이터는 맨 뒤(-1), 최신 데이터는 맨 앞(0)
                start_val = data.iloc[-1] 
                end_val   = data.iloc[0]  
                years = len(data) - 1
                if start_val > 0 and end_val > 0:
                    return (end_val / start_val) ** (1 / years) - 1
    except Exception:
        pass
    return None

def _annual_values(financials, row_name):
    """SEC 데이터에서 연간 값과 날짜 목록 반환 (최신→과거)"""
    try:
        if row_name in financials.index:
            s = financials.loc[row_name].dropna()
            return s.tolist(), s.index.tolist()
    except Exception:
        pass
    return [], []

# ─── 8단계 기업 생애주기 판별 ───────────────────────────
def _growth_stage(info, fin, bs, cf):
    """SEC 재무제표 기반 8단계 기업 성장 사이클"""
    rev_g   = info.get('revenueGrowth', 0) or 0
    margin  = info.get('profitMargins', 0) or 0
    rev     = info.get('totalRevenue', 0)  or 0
    div_y   = info.get('dividendYield', 0) or 0

    # 영업현금흐름
    op_cf = 0
    try:
        if cf is not None and 'Operating Cash Flow' in cf.index:
            op_cf = cf.loc['Operating Cash Flow'].dropna().iloc[0] or 0
    except Exception:
        pass

    stages = {
        1: ("🌱 1단계 : 스타트업 / 개발",    "매출 미미 · R&D 투자 집중"),
        2: ("🚀 2단계 : 초기 고성장",        "매출 폭발 · 적자 지속"),
        3: ("📈 3단계 : 고성장 흑자전환",      "높은 매출 성장 + 이익 창출 시작"),
        4: ("💪 4단계 : 성숙한 성장",          "안정 매출 성장 · 높은 수익성"),
        5: ("💰 5단계 : 캐시카우",             "성장 둔화 · 막대한 현금·배당"),
        6: ("⏸️ 6단계 : 정체기",              "매출 정체 · 이익 유지"),
        7: ("📉 7단계 : 쇠퇴기",              "매출·이익 동반 하락"),
        8: ("🔧 8단계 : 구조조정/턴어라운드",  "사업 재편 · 회생 시도"),
    }
    colors = {1:"#9C27B0",2:"#FF5722",3:"#FF9800",4:"#4CAF50",
              5:"#2196F3",6:"#607D8B",7:"#F44336",8:"#795548"}

    if rev < 1e8 and margin < -0.20:                               s = 1
    elif rev_g > 0.30 and margin < 0:                              s = 2
    elif rev_g > 0.20 and margin > 0:                              s = 3
    elif rev_g > 0.05 and margin > 0.10:                           s = 4
    elif 0 <= rev_g <= 0.05 and margin > 0.10 and (div_y > 0.01 or op_cf > 0): s = 5
    elif -0.05 <= rev_g <= 0.02 and margin > 0:                   s = 6
    elif rev_g < -0.05 and margin < 0:                             s = 7
    elif rev_g < 0 and margin <= 0:                                s = 8
    elif rev_g > 0.30:                                             s = 2
    elif margin > 0.15:                                            s = 4
    else:                                                          s = 4

    return s, stages[s][0], stages[s][1], colors[s]

# ─── 안정성 분석 ──────────────────────────────────────
def _stability(financials, row_name):
    """변동계수(CV) 기반 수익 안정성"""
    vals, _ = _annual_values(financials, row_name)
    arr = np.array([v for v in vals if v is not None and not np.isnan(v)])
    if len(arr) < 2 or np.mean(arr) == 0:
        return "데이터 부족", ""
    cv = np.std(arr) / abs(np.mean(arr))
    if   cv < 0.10: return "매우 안정적 ✅", f"CV {cv:.3f}"
    elif cv < 0.25: return "안정적 ✅",     f"CV {cv:.3f}"
    elif cv < 0.50: return "보통 ⚠️",       f"CV {cv:.3f}"
    else:           return "불안정 ❌",      f"CV {cv:.3f}"

def _margin_trend(fin):
    """순이익률 추이"""
    try:
        r = fin.loc['Total Revenue'].dropna()
        n = fin.loc['Net Income'].dropna()
        idx = r.index.intersection(n.index).sort_values() # 오래된순
        margins = [(i, n[i]/r[i]) for i in idx if r[i] != 0]
        if len(margins) < 2: return "N/A", []
        if margins[-1][1] > margins[0][1]: return "증가 추세 📈", margins
        if margins[-1][1] < margins[0][1]: return "감소 추세 📉", margins
        return "유지 ➡️", margins
    except Exception:
        return "N/A", []

def _growth_accel(fin, row):
    """성장 가속화 여부"""
    vals, _ = _annual_values(fin, row) # 최신순
    if len(vals) < 3: return "N/A"
    g = []
    for i in range(len(vals)-1):
        if vals[i+1] and vals[i+1] != 0:
            g.append((vals[i]-vals[i+1])/abs(vals[i+1]))
    if len(g) < 2: return "N/A"
    if g[0] > g[1]:
        return f"가속화 🚀 (최근 {g[0]*100:.1f}% vs 이전 {g[1]*100:.1f}%)"
    return f"감속 🐌 (최근 {g[0]*100:.1f}% vs 이전 {g[1]*100:.1f}%)"

def _debt_trend(bs):
    """부채 추세 분석"""
    for name in ['Total Debt','Long Term Debt','Total Liabilities Net Minority Interest']:
        if name in bs.index:
            d = bs.loc[name].dropna() # 최신순
            if len(d) >= 2:
                # 최신(0) - 과거(-1) / 과거(-1)
                chg = (d.iloc[0]-d.iloc[-1])/abs(d.iloc[-1]) if d.iloc[-1]!=0 else 0
                if   chg < -0.10: return f"감소 추세 ✅ ({chg*100:.1f}%)"
                elif chg >  0.10: return f"증가 추세 ⚠️ (+{chg*100:.1f}%)"
                else:             return f"안정적 유지 ➡️ ({chg*100:.1f}%)"
    return "데이터 부족"

def _interest_burden(info):
    """이자 부담 평가"""
    ebitda = info.get('ebitda', 0) or 0
    debt   = info.get('totalDebt', 0) or 0
    if ebitda > 0 and debt > 0:
        cov = ebitda / (debt * 0.05)          # 추정이자 5%
        if   cov > 10: return f"매우 낮음 ✅ ({cov:.1f}x)"
        elif cov >  5: return f"낮음 ✅ ({cov:.1f}x)"
        elif cov >  2: return f"보통 ⚠️ ({cov:.1f}x)"
        else:          return f"높음 ❌ ({cov:.1f}x)"
    return "N/A"

def _vol_trend(info):
    """거래량 변동 추이"""
    vol = info.get('volume', 0) or 0
    avg = info.get('averageVolume', 0) or 0
    if avg == 0: return "데이터 부족"
    r = vol / avg
    if   r > 1.5: return f"급증 🔥 (3개월 평균 ×{r:.1f})"
    elif r > 1.1: return f"증가 📈 (×{r:.1f})"
    elif r > 0.9: return f"평균 수준 ➡️ (×{r:.1f})"
    elif r > 0.5: return f"감소 📉 (×{r:.1f})"
    else:         return f"급감 ⚠️ (×{r:.1f})"

def _max_pain(tkr):
    """옵션 Max‑Pain + Call/Put Top 3"""
    try:
        dates = tkr.options
        if not dates: return None, None, None, None
        exp = dates[0]
        o = tkr.option_chain(exp)
        c, p = o.calls, o.puts
        
        # 🚀 에러 수정: volume이 NaN인 경우 0으로 채움
        c['volume'] = c['volume'].fillna(0)
        p['volume'] = p['volume'].fillna(0)
        
        strikes = sorted(set(c['strike']).union(set(p['strike'])))
        pain = {}
        for s in strikes:
            pain[s] = (np.sum(c['openInterest'] * np.maximum(0, s - c['strike']))
                     + np.sum(p['openInterest'] * np.maximum(0, p['strike'] - s)))
        mp = min(pain, key=pain.get)
        tc = c.nlargest(3,'volume')[['strike','volume']].to_dict('records')
        tp = p.nlargest(3,'volume')[['strike','volume']].to_dict('records')
        return exp, mp, tc, tp
    except Exception:
        return None, None, None, None

# ═════════════════════════════════════════════════════════
# 🎨  CSS
# ═════════════════════════════════════════════════════════
CSS = """
<style>
.info-card{background:#161A22;border:1px solid #2D333B;border-radius:12px;padding:22px;margin-bottom:20px;box-shadow:0 4px 15px rgba(0,0,0,.2);transition:transform .2s}
.info-card:hover{transform:translateY(-2px);border-color:#3e4c59}
.info-title{font-size:1.15rem;font-weight:700;color:#82aaff;margin-bottom:18px;border-bottom:1px solid #2D333B;padding-bottom:10px;display:flex;align-items:center;gap:8px}
.metric-row{display:flex;justify-content:space-between;margin-bottom:10px;font-size:.95rem;align-items:center}
.metric-label{color:#8b949e;font-weight:500}
.metric-value{color:#c9d1d9;font-weight:600;text-align:right}
.metric-highlight{color:#00E676;font-weight:700}
.metric-warn{color:#FF1744;font-weight:700}
.divider{border-top:1px dashed #2D333B;margin:15px 0}
.opt-box{background:rgba(0,0,0,.2);padding:10px;border-radius:8px;border:1px solid #2D333B;width:48%;}
.opt-list{margin:5px 0 0;padding-left:20px;font-size:.85rem;color:#c9d1d9}
.mini-table{width:100%;border-collapse:collapse;font-size:.85rem}
.mini-table th{color:#8b949e;text-align:left;padding:6px 8px;border-bottom:1px solid #2D333B;font-weight:500}
.mini-table td{color:#c9d1d9;padding:6px 8px;border-bottom:1px solid #1c2029}
.progress-container{background:#21262d;border-radius:8px;height:26px;display:flex;overflow:hidden;margin:10px 0}
.progress-bar{height:100%;display:flex;align-items:center;justify-content:center;font-size:.7rem;font-weight:600;color:#fff}
.news-item{padding:12px 0;border-bottom:1px solid #2D333B}
.news-title{color:#82aaff;font-weight:600;font-size:.95rem;text-decoration:none}
.news-title:hover{text-decoration:underline}
.news-meta{color:#6e7681;font-size:.8rem;margin-top:4px}
</style>
"""

# ═════════════════════════════════════════════════════════
# 🏗️  메인 렌더링  (1단 와이드 레이아웃 적용)
# ═════════════════════════════════════════════════════════
def render_company_details(ticker_str: str):
    st.markdown(CSS, unsafe_allow_html=True)

    with st.spinner(f"📡 {ticker_str} — SEC 공시 + 시장 데이터 딥 다이빙 중..."):
        tkr  = yf.Ticker(ticker_str)
        info = tkr.info
        if not info or 'shortName' not in info:
            st.error("❌ 종목 데이터를 불러올 수 없습니다.")
            return

        fin = tkr.financials        # 손익계산서
        bs  = tkr.balance_sheet     # 대차대조표
        cf  = tkr.cashflow          # 현금흐름표

        cagr_rev = _calc_cagr(fin, 'Total Revenue')
        cagr_ni  = _calc_cagr(fin, 'Net Income')
        cagr_eps = _calc_cagr(fin, 'Basic EPS')

        sector   = info.get('sector',   'N/A')
        industry = info.get('industry', 'N/A')
        price    = info.get('currentPrice', info.get('regularMarketPrice', 'N/A'))

    # ──────── 헤더 ────────
    st.markdown(
        f"### 🏢 {info.get('shortName', ticker_str)} "
        f"<span style='font-size:1rem;color:#888'>({ticker_str})</span> "
        f"<span style='font-size:.95rem;color:#6e7681'>| {sector} · {industry}</span>"
        f"<span style='font-size:1.2rem;color:#00E676;font-weight:700;float:right'>${price}</span>",
        unsafe_allow_html=True)
    st.markdown("---")

    # 🚀 개선: st.columns(2)를 모두 제거하여 한 줄에 1개의 카드가 꽉 차게 렌더링합니다.
    
    # ════ 1. 기업 성장 사이클 ════
    sn, sname, sdesc, scolor = _growth_stage(info, fin, bs, cf)
    stage_colors_map = {1:"#9C27B0",2:"#FF5722",3:"#FF9800",4:"#4CAF50",
                        5:"#2196F3",6:"#607D8B",7:"#F44336",8:"#795548"}
    bar = ""
    for i in range(1, 9):
        bg = stage_colors_map[i] if i == sn else "#21262d"
        op = "1" if i == sn else "0.35"
        br = f"2px solid {stage_colors_map[i]}" if i == sn else "1px solid #2D333B"
        rl = "border-radius:8px 0 0 8px;" if i==1 else ("border-radius:0 8px 8px 0;" if i==8 else "")
        bar += f"<div style='flex:1;background:{bg};opacity:{op};text-align:center;padding:8px 2px;font-size:.7rem;color:#fff;border:{br};{rl}'>{i}</div>"

    st.markdown(f"""
    <div class="info-card">
        <div class="info-title">🔄 1. 이 회사, 지금 어느 단계인가요?</div>
        <div style="display:flex;gap:2px;margin-bottom:15px">{bar}</div>
        <div style="text-align:center">
            <span style="display:inline-block;padding:6px 16px;border-radius:20px;font-weight:700;background:{scolor};color:#fff">{sname}</span>
            <div style="font-size:.85rem;color:#8b949e;margin-top:6px">{sdesc}</div>
        </div>
        <div class="divider"></div>
        <div class="metric-row"><span class="metric-label">YOY 매출 성장률:</span><span class="metric-value">{_fmt_pct(info.get('revenueGrowth'))}</span></div>
        <div class="metric-row"><span class="metric-label">순이익률:</span><span class="metric-value">{_fmt_pct(info.get('profitMargins'))}</span></div>
        <div class="metric-row"><span class="metric-label">배당수익률:</span><span class="metric-value">{_fmt_pct(info.get('dividendYield'))}</span></div>
    </div>""", unsafe_allow_html=True)

    # ════ 2. 수익성 ════
    st.markdown(f"""
    <div class="info-card">
        <div class="info-title">💵 2. 돈을 잘 버는 회사인가요? (SEC)</div>
        <div class="metric-row"><span class="metric-label">시가총액:</span><span class="metric-value">{_fmt_num(info.get('marketCap'))}</span></div>
        <div class="metric-row"><span class="metric-label">TTM EPS:</span><span class="metric-value">${_safe(info.get('trailingEps'))}</span></div>
        <div class="metric-row"><span class="metric-label">최근 12개월 매출:</span><span class="metric-value">{_fmt_num(info.get('totalRevenue'))}</span></div>
        <div class="metric-row"><span class="metric-label">최근 12개월 순이익:</span><span class="metric-value">{_fmt_num(info.get('netIncomeToCommon'))}</span></div>
        <div class="divider"></div>
        <div class="metric-row"><span class="metric-label">총이익률 (Gross):</span><span class="metric-value">{_fmt_pct(info.get('grossMargins'))}</span></div>
        <div class="metric-row"><span class="metric-label">순이익률 (Net):</span><span class="metric-value metric-highlight">{_fmt_pct(info.get('profitMargins'))}</span></div>
        <div class="divider"></div>
        <div class="metric-row"><span class="metric-label">5Y 매출 CAGR:</span><span class="metric-value">{_fmt_pct(cagr_rev)}</span></div>
        <div class="metric-row"><span class="metric-label">5Y 순이익 CAGR:</span><span class="metric-value">{_fmt_pct(cagr_ni)}</span></div>
        <div class="metric-row"><span class="metric-label">5Y EPS CAGR:</span><span class="metric-value">{_fmt_pct(cagr_eps)}</span></div>
    </div>""", unsafe_allow_html=True)

    # ════ 3. 지금까지 성적 ════
    rev_stab, rev_cv = _stability(fin, 'Total Revenue')
    mtrend, _        = _margin_trend(fin)
    accel            = _growth_accel(fin, 'Total Revenue')
    roe              = info.get('returnOnEquity')
    if roe is not None:
        if   roe > 0.20: roe_lbl = f"매우 높음 ✅ ({_fmt_pct(roe)})"
        elif roe > 0.10: roe_lbl = f"양호 ✅ ({_fmt_pct(roe)})"
        elif roe > 0:    roe_lbl = f"보통 ⚠️ ({_fmt_pct(roe)})"
        else:            roe_lbl = f"음수 ❌ ({_fmt_pct(roe)})"
    else:
        roe_lbl = "N/A"

    rv, rd = _annual_values(fin, 'Total Revenue')
    nv, nd = _annual_values(fin, 'Net Income')
    rows = ""
    for i in range(min(len(rv), len(nv), 4)):
        yr = rd[i].strftime('%Y') if hasattr(rd[i], 'strftime') else str(rd[i])[:4]
        mg = (nv[i]/rv[i]*100) if rv[i] else 0
        rows += f"<tr><td>{yr}</td><td>{_fmt_num(rv[i])}</td><td>{_fmt_num(nv[i])}</td><td>{mg:.1f}%</td></tr>"

    st.markdown(f"""
    <div class="info-card">
        <div class="info-title">📊 3. 지금까지 성적 (SEC)</div>
        <div class="metric-row"><span class="metric-label">수익 안정성:</span><span class="metric-value">{rev_stab} <span style="font-size:.8rem;color:#6e7681">{rev_cv}</span></span></div>
        <div class="metric-row"><span class="metric-label">이익 마진 추이:</span><span class="metric-value">{mtrend}</span></div>
        <div class="metric-row"><span class="metric-label">성장 가속화:</span><span class="metric-value">{accel}</span></div>
        <div class="metric-row"><span class="metric-label">ROE 수준:</span><span class="metric-value">{roe_lbl}</span></div>
        <div class="divider"></div>
        <table class="mini-table"><tr><th>연도</th><th>매출</th><th>순이익</th><th>이익률</th></tr>{rows}</table>
    </div>""", unsafe_allow_html=True)

    # ════ 4. 성장 가능성 ════
    payout    = info.get('payoutRatio', 0) or 0
    retention = 1 - payout
    roe_val   = info.get('returnOnEquity', 0) or 0
    fut_roe   = roe_val * retention if roe_val else None
    eg        = info.get('earningsGrowth')
    rg        = info.get('revenueGrowth')

    st.markdown(f"""
    <div class="info-card">
        <div class="info-title">🚀 4. 미래 성장 가능성 (SEC + Yahoo)</div>
        <div class="metric-row"><span class="metric-label">이익 성장률 (YOY):</span><span class="metric-value {'metric-highlight' if eg and eg>0 else 'metric-warn'}">{_fmt_pct(eg)}</span></div>
        <div class="metric-row"><span class="metric-label">매출 성장률 (YOY):</span><span class="metric-value {'metric-highlight' if rg and rg>0 else 'metric-warn'}">{_fmt_pct(rg)}</span></div>
        <div class="divider"></div>
        <div class="metric-row"><span class="metric-label">ROE:</span><span class="metric-value metric-highlight">{_fmt_pct(roe_val)}</span></div>
        <div class="metric-row"><span class="metric-label">수익 유보율(저축률):</span><span class="metric-value">{_fmt_pct(retention)}</span></div>
        <div class="metric-row"><span class="metric-label">미래 예상 ROE (ROE×유보율):</span><span class="metric-value">{_fmt_pct(fut_roe)}</span></div>
        <div class="divider"></div>
        <div class="metric-row"><span class="metric-label">Forward EPS:</span><span class="metric-value">${_safe(info.get('forwardEps'))}</span></div>
        <div class="metric-row"><span class="metric-label">PEG 비율:</span><span class="metric-value">{_safe(info.get('pegRatio'))}</span></div>
    </div>""", unsafe_allow_html=True)

    # ════ 5. 재무 건전성 ════
    try:
        curr_d = bs.loc['Current Debt'].iloc[0] if 'Current Debt' in bs.index else 0
        lt_d   = bs.loc['Long Term Debt'].iloc[0] if 'Long Term Debt' in bs.index else 0
        ta     = bs.loc['Total Assets'].iloc[0] if 'Total Assets' in bs.index else info.get('totalAssets',0)
        tl     = bs.loc['Total Liabilities Net Minority Interest'].iloc[0] if 'Total Liabilities Net Minority Interest' in bs.index else 0
        eq     = bs.loc['Stockholders Equity'].iloc[0] if 'Stockholders Equity' in bs.index else 0
        na     = ta - tl
    except Exception:
        curr_d = lt_d = ta = tl = eq = na = 0

    dt_trend = _debt_trend(bs)
    i_burden = _interest_burden(info)
    dte      = info.get('debtToEquity', 'N/A')
    if isinstance(dte, (int,float)):
        if   dte < 50:  dl = "낮음 ✅"
        elif dte < 100: dl = "보통 ⚠️"
        elif dte < 200: dl = "높음 ⚠️"
        else:           dl = "매우 높음 ❌"
    else:
        dl = "N/A"

    st.markdown(f"""
    <div class="info-card">
        <div class="info-title">🏦 5. 회사에 돈이 얼마나 있나요? (SEC + Yahoo)</div>
        <div class="metric-row"><span class="metric-label">보유 현금:</span><span class="metric-value metric-highlight">{_fmt_num(info.get('totalCash'))}</span></div>
        <div class="metric-row"><span class="metric-label">단기 부채:</span><span class="metric-value">{_fmt_num(curr_d)}</span></div>
        <div class="metric-row"><span class="metric-label">장기 부채:</span><span class="metric-value">{_fmt_num(lt_d)}</span></div>
        <div class="divider"></div>
        <div class="metric-row"><span class="metric-label">부채 수준:</span><span class="metric-value">{dl}</span></div>
        <div class="metric-row"><span class="metric-label">부채 추세:</span><span class="metric-value">{dt_trend}</span></div>
        <div class="metric-row"><span class="metric-label">이자 부담:</span><span class="metric-value">{i_burden}</span></div>
        <div class="metric-row"><span class="metric-label">부채/자본 비율:</span><span class="metric-value">{dte}{'%' if isinstance(dte,(int,float)) else ''}</span></div>
        <div class="divider"></div>
        <div class="metric-row"><span class="metric-label">총 자산:</span><span class="metric-value">{_fmt_num(ta)}</span></div>
        <div class="metric-row"><span class="metric-label">총 부채:</span><span class="metric-value">{_fmt_num(tl)}</span></div>
        <div class="metric-row"><span class="metric-label">자본 (Equity):</span><span class="metric-value">{_fmt_num(eq)}</span></div>
        <div class="metric-row"><span class="metric-label">순 자산:</span><span class="metric-value metric-highlight">{_fmt_num(na)}</span></div>
    </div>""", unsafe_allow_html=True)

    # ════ 6. 수급 동향 ════
    vt = _vol_trend(info)
    st.markdown(f"""
    <div class="info-card">
        <div class="info-title">📈 6. 지금 사람들이 많이 사고 있나요? (Yahoo)</div>
        <div class="metric-row"><span class="metric-label">현재 거래량:</span><span class="metric-value">{_fmt_num(info.get('volume'),False)} 주</span></div>
        <div class="metric-row"><span class="metric-label">10일 평균:</span><span class="metric-value">{_fmt_num(info.get('averageVolume10days'),False)} 주</span></div>
        <div class="metric-row"><span class="metric-label">3개월 평균:</span><span class="metric-value">{_fmt_num(info.get('averageVolume'),False)} 주</span></div>
        <div class="divider"></div>
        <div class="metric-row"><span class="metric-label">거래량 변동 추이:</span><span class="metric-value">{vt}</span></div>
    </div>""", unsafe_allow_html=True)

    # ════ 7. 변동성 ════
    beta = info.get('beta', 'N/A')
    if isinstance(beta, (int,float)):
        if   beta < 0.8: bl = "(저변동 — 시장보다 안정)"
        elif beta < 1.2: bl = "(시장과 유사)"
        elif beta < 1.5: bl = "(높은 변동성 ⚠️)"
        else:            bl = "(매우 높은 변동성 🔥)"
    else:
        bl = ""
    w52h = info.get('fiftyTwoWeekHigh','N/A')
    w52l = info.get('fiftyTwoWeekLow','N/A')
    try:
        pos52 = f"{((price-w52l)/(w52h-w52l)*100):.1f}%" if isinstance(price,(int,float)) and isinstance(w52h,(int,float)) and w52h!=w52l else "N/A"
    except:
        pos52 = "N/A"

    st.markdown(f"""
    <div class="info-card">
        <div class="info-title">🎢 7. 변동성이 큰가요? (Yahoo)</div>
        <div class="metric-row"><span class="metric-label">베타:</span><span class="metric-value">{beta} {bl}</span></div>
        <div class="metric-row"><span class="metric-label">52주 가격 변동률:</span><span class="metric-value">{_fmt_pct(info.get('52WeekChange'))}</span></div>
        <div class="divider"></div>
        <div class="metric-row"><span class="metric-label">52주 최고가:</span><span class="metric-value">${w52h}</span></div>
        <div class="metric-row"><span class="metric-label">52주 최저가:</span><span class="metric-value">${w52l}</span></div>
        <div class="metric-row"><span class="metric-label">현재가 위치 (52주 내):</span><span class="metric-value">{pos52}</span></div>
    </div>""", unsafe_allow_html=True)

    # ════ 8. 밸류에이션 ════
    st.markdown(f"""
    <div class="info-card">
        <div class="info-title">⚖️ 8. 이 종목 비싼가요? (Yahoo)</div>
        <div class="metric-row"><span class="metric-label">Trailing P/E:</span><span class="metric-value">{_safe(info.get('trailingPE'))}</span></div>
        <div class="metric-row"><span class="metric-label">Forward P/E:</span><span class="metric-value">{_safe(info.get('forwardPE'))}</span></div>
        <div class="metric-row"><span class="metric-label">P/S (TTM):</span><span class="metric-value">{_safe(info.get('priceToSalesTrailing12Months'))}</span></div>
        <div class="metric-row"><span class="metric-label">P/B:</span><span class="metric-value">{_safe(info.get('priceToBook'))}</span></div>
        <div class="divider"></div>
        <div class="metric-row"><span class="metric-label">섹터:</span><span class="metric-value">{sector}</span></div>
        <div style="font-size:.8rem;color:#6e7681;margin-top:8px">※ 동일 섹터 평균 P/E 와 비교하여 고평가·저평가를 판단하세요.</div>
    </div>""", unsafe_allow_html=True)

    # ════ 9. 애널리스트 ════
    rm = info.get('recommendationMean','N/A')
    if isinstance(rm,(int,float)):
        if   rm <= 1.5: con = "🟢 강력 매수"
        elif rm <= 2.0: con = "🟢 매수"
        elif rm <= 2.5: con = "🟡 매수 우위"
        elif rm <= 3.0: con = "🟡 보유"
        elif rm <= 3.5: con = "🟠 매도 우위"
        elif rm <= 4.0: con = "🔴 매도"
        else:           con = "🔴 강력 매도"
    else:
        con = "N/A"

    tm   = info.get('targetMedianPrice','N/A')
    try:
        upside = f"{'📈' if (tm-price)>0 else '📉'} {((tm-price)/price*100):+.1f}%" if isinstance(tm,(int,float)) and isinstance(price,(int,float)) and price>0 else ""
    except:
        upside = ""

    st.markdown(f"""
    <div class="info-card">
        <div class="info-title">👨‍💼 9. 전문가들의 의견 (Yahoo)</div>
        <div class="metric-row"><span class="metric-label">컨센서스 등급:</span><span class="metric-value metric-highlight">{str(info.get('recommendationKey','N/A')).upper()}</span></div>
        <div class="metric-row"><span class="metric-label">평균 의견 점수 (1매수~5매도):</span><span class="metric-value">{rm}</span></div>
        <div class="metric-row"><span class="metric-label">종합 의견:</span><span class="metric-value">{con}</span></div>
        <div class="divider"></div>
        <div class="metric-row"><span class="metric-label">평균 목표가:</span><span class="metric-value">${_safe(info.get('targetMeanPrice'))}</span></div>
        <div class="metric-row"><span class="metric-label">중앙값 목표가:</span><span class="metric-value">${tm}</span></div>
        <div class="metric-row"><span class="metric-label">최고 목표가:</span><span class="metric-value">${_safe(info.get('targetHighPrice'))}</span></div>
        <div class="metric-row"><span class="metric-label">최저 목표가:</span><span class="metric-value">${_safe(info.get('targetLowPrice'))}</span></div>
        <div class="metric-row"><span class="metric-label">참여 애널리스트:</span><span class="metric-value">{info.get('numberOfAnalystOpinions',0)}명</span></div>
        <div class="divider"></div>
        <div style="text-align:center;font-size:.95rem;color:#82aaff;font-weight:600">목표가 대비 현재가 여력: {upside}</div>
    </div>""", unsafe_allow_html=True)

    # ════ 10. 지분 구조 ════
    inst = info.get('heldPercentInstitutions', 0) or 0
    ins  = info.get('heldPercentInsiders',     0) or 0
    pub  = max(0, 1 - inst - ins)

    st.markdown(f"""
    <div class="info-card">
        <div class="info-title">👥 10. 이 회사 누가 들고 있나요? (Yahoo)</div>
        <div class="metric-row"><span class="metric-label">총 발행 주식수:</span><span class="metric-value">{_fmt_num(info.get('sharesOutstanding'),False)} 주</span></div>
        <div class="metric-row"><span class="metric-label">유통 주식수 (Float):</span><span class="metric-value">{_fmt_num(info.get('floatShares'),False)} 주</span></div>
        <div class="divider"></div>
        <div class="metric-row"><span class="metric-label">기관 투자자:</span><span class="metric-value">{_fmt_pct(inst)}</span></div>
        <div class="metric-row"><span class="metric-label">내부자 / 임원:</span><span class="metric-value">{_fmt_pct(ins)}</span></div>
        <div class="metric-row"><span class="metric-label">일반 / 개인 (추정):</span><span class="metric-value">{_fmt_pct(pub)}</span></div>
        <div class="divider"></div>
        <div style="font-size:.85rem;color:#6e7681">지분 구성 비율</div>
        <div class="progress-container">
            <div class="progress-bar" style="width:{max(inst*100, 5):.1f}%;background:#2196F3">기관 {inst*100:.0f}%</div>
            <div class="progress-bar" style="width:{max(ins*100, 5):.1f}%;background:#FF9800">내부자 {ins*100:.0f}%</div>
            <div class="progress-bar" style="width:{max(pub*100, 5):.1f}%;background:#4CAF50">일반 {pub*100:.0f}%</div>
        </div>
    </div>""", unsafe_allow_html=True)

    # ════ 11. 시장은 어떤 가격을 보고 있을까요 (Max Pain) ════
    exp, mp, tc, tp = _max_pain(tkr)
    mp_html = f"<span class='metric-value metric-warn' style='font-size:1.1rem'>${mp}</span>" if mp else "<span class='metric-value'>데이터 없음</span>"
    exp_html = f"(만기일: {exp})" if exp else ""

    mp_note = ""
    if mp and isinstance(price,(int,float)) and price>0:
        d = ((mp-price)/price)*100
        mp_note = f"현재가보다 {d:+.1f}% {'위 → 상승 압력' if d>0 else '아래 → 하락 압력'} 가능"

    ch = "".join([f"<li>${c['strike']:.1f} (Vol: {int(c['volume']):,})</li>" for c in tc]) if tc else "<li>N/A</li>"
    ph = "".join([f"<li>${p['strike']:.1f} (Vol: {int(p['volume']):,})</li>" for p in tp]) if tp else "<li>N/A</li>"

    st.markdown(f"""
    <div class="info-card">
        <div class="info-title">🎯 11. 시장은 어떤 가격을 보고 있을까요? (Yahoo 옵션)</div>
        <div class="metric-row"><span class="metric-label">Max Pain 가격 {exp_html}:</span>{mp_html}</div>
        <div class="metric-row"><span class="metric-label">해석:</span><span class="metric-value">{mp_note}</span></div>
        <div class="divider"></div>
        <div style="display:flex;justify-content:space-between;margin-top:10px">
            <div class="opt-box">
                <b style="color:#00E676;font-size:.9rem">🟢 Call 거래량 Top 3</b>
                <ul class="opt-list">{ch}</ul>
            </div>
            <div class="opt-box">
                <b style="color:#FF1744;font-size:.9rem">🔴 Put 거래량 Top 3</b>
                <ul class="opt-list">{ph}</ul>
            </div>
        </div>
    </div>""", unsafe_allow_html=True)

    # ════ 12. 공매도 비율 ════
    sp = info.get('shortPercentOfFloat')
    if isinstance(sp,(int,float)):
        if   sp > 0.20: sl = "매우 높음 🔴 (숏 스퀴즈 가능성)"
        elif sp > 0.10: sl = "높음 🟠"
        elif sp > 0.05: sl = "보통 🟡"
        else:           sl = "낮음 🟢"
    else:
        sl = "N/A"

    st.markdown(f"""
    <div class="info-card">
        <div class="info-title">📉 12. 공매도 비율 (Yahoo)</div>
        <div class="metric-row"><span class="metric-label">유통주식 대비 공매도 비율:</span><span class="metric-value metric-warn">{_fmt_pct(sp)}</span></div>
        <div class="metric-row"><span class="metric-label">공매도 수준:</span><span class="metric-value">{sl}</span></div>
        <div class="metric-row"><span class="metric-label">공매도 주식수:</span><span class="metric-value">{_fmt_num(info.get('sharesShort'),False)} 주</span></div>
        <div class="metric-row"><span class="metric-label">발행 주식수:</span><span class="metric-value">{_fmt_num(info.get('sharesOutstanding'),False)} 주</span></div>
        <div class="metric-row"><span class="metric-label">숏 커버 일수 (DTC):</span><span class="metric-value">{_safe(info.get('shortRatio'))} 일</span></div>
    </div>""", unsafe_allow_html=True)

    # ════ 13. 뉴스 (에러 발생 방지 처리) ════
    try:
        news_list = tkr.news
        if news_list:
            items = ""
            for n in news_list[:10]:
                title = n.get('title', '제목 없음')
                link  = n.get('link', '#')
                pub   = n.get('publisher', '')
                
                # 🚀 버그 수정: providerPublishTime이 없을 때 에러 방지
                ts    = n.get('providerPublishTime') or n.get('publishTime')
                dt_str = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M') if ts else ""
                
                items += f"""<div class="news-item">
                    <a href="{link}" target="_blank" class="news-title">{title}</a>
                    <div class="news-meta">{pub} · {dt_str}</div>
                </div>"""
            st.markdown(f"""
            <div class="info-card">
                <div class="info-title">📰 13. 최신 뉴스 (Yahoo Finance)</div>
                {items}
            </div>""", unsafe_allow_html=True)
    except Exception:
        st.markdown("""
        <div class="info-card">
            <div class="info-title">📰 13. 최신 뉴스</div>
            <div style="color:#6e7681">뉴스 데이터를 불러올 수 없습니다.</div>
        </div>""", unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════
# ▶️  실행 (테스트용)
# ═════════════════════════════════════════════════════════
if __name__ == "__main__":
    st.set_page_config(page_title="종목 상세 분석", layout="wide")
    ticker_input = st.text_input("티커 입력", value="AAPL")
    if ticker_input:
        render_company_details(ticker_input.upper())