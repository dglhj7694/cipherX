import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import html as html_module
from datetime import datetime
import plotly.graph_objects as go

# ═══════════════════════════════════════════════════════════════
# 🛠️ API 변동성 대응을 위한 동의어(Alias) 설정
# ═══════════════════════════════════════════════════════════════
REV_ALIASES = ['Total Revenue', 'Operating Revenue', 'Revenue']
NI_ALIASES = ['Net Income', 'Net Income Common Stockholders', 'Net Income Continuous Operations',
              'Net Income From Continuing Ops', 'Net Income Applicable To Common Shares',
              'Net Income Including Noncontrolling Interests']
EPS_ALIASES = ['Basic EPS', 'Diluted EPS', 'Earnings Per Share']
BS_ASSETS_ALIASES = ['Total Assets', 'Assets', 'TotalAssets']
BS_LIAB_ALIASES = ['Total Liabilities Net Minority Interest', 'Total Liab',
                   'Total Liabilities', 'TotalLiabilities']

# ═══════════════════════════════════════════════════════════════
# 🛠️ 유틸리티 함수
# ═══════════════════════════════════════════════════════════════

def _fmt_num(num, is_currency=True):
    if pd.isna(num) or num is None:
        return "N/A"
    prefix = "$" if is_currency else ""
    sign = "-" if num < 0 else ""
    a = abs(num)
    if   a >= 1e12: return f"{sign}{prefix}{a/1e12:.2f}T"
    elif a >= 1e9:  return f"{sign}{prefix}{a/1e9:.2f}B"
    elif a >= 1e6:  return f"{sign}{prefix}{a/1e6:.2f}M"
    elif a >= 1e3:  return f"{sign}{prefix}{a/1e3:.2f}K"
    return f"{sign}{prefix}{num:,.2f}"

def _fmt_pct(num):
    if pd.isna(num) or num is None:
        return "N/A"
    return f"{num * 100:.2f}%"

def _safe(val, fallback="N/A"):
    if val is None:
        return fallback
    if isinstance(val, float) and np.isnan(val):
        return fallback
    return val

def _esc(text):
    return html_module.escape(str(text)) if text else ""

def _get_row(df, candidates, col_idx=0):
    if df is None:
        return None
    for name in candidates:
        if name in df.index:
            try:
                val = df.loc[name].dropna()
                if len(val) > col_idx:
                    return val.iloc[col_idx]
            except Exception:
                pass
    return None

def _get_row_series(df, candidates):
    if df is None:
        return pd.Series(dtype=float)
    for name in candidates:
        if name in df.index:
            try:
                return df.loc[name].dropna().sort_index()
            except Exception:
                pass
    return pd.Series(dtype=float)

def _calc_cagr_with_years(financials, row_candidates):
    try:
        rc = row_candidates if isinstance(row_candidates, list) else [row_candidates]
        series = _get_row_series(financials, rc)
        if len(series) >= 2:
            series = series.sort_index()
            s_val, e_val = float(series.iloc[0]), float(series.iloc[-1])
            years = len(series) - 1
            if s_val > 0 and e_val > 0:
                return (e_val / s_val) ** (1 / years) - 1, years
            # 🔧 개선: 음수→양수 전환 시 턴어라운드 표시
            if s_val < 0 and e_val > 0:
                return None, years  # years 반환하여 "턴어라운드" 표시 가능
    except Exception:
        pass
    return None, 0

def _annual_values(financials, row_candidates):
    try:
        rc = row_candidates if isinstance(row_candidates, list) else [row_candidates]
        series = _get_row_series(financials, rc)
        if len(series) > 0:
            series = series.sort_index(ascending=False)
            return series.tolist(), series.index.tolist()
    except Exception:
        pass
    return [], []

# ── 시각 요소 및 Plotly 차트 생성기 ─────────────────────────────────────

def _verdict_badge(color, emoji, text):
    bg = {"green": "rgba(0,230,118,.12)", "red": "rgba(255,23,68,.12)",
          "yellow": "rgba(255,193,7,.12)", "blue": "rgba(33,150,243,.12)",
          "gray": "rgba(96,125,139,.12)"}
    bdr = {"green": "#00E676", "red": "#FF1744", "yellow": "#FFC107",
           "blue": "#2196F3", "gray": "#607D8B"}
    return (f'<div style="background:{bg.get(color, bg["gray"])};'
            f'border:1px solid {bdr.get(color, bdr["gray"])};border-radius:10px;'
            f'padding:14px 18px;margin-top:16px;text-align:center">'
            f'<span style="font-size:1.05rem;font-weight:700;'
            f'color:{bdr.get(color, bdr["gray"])}">{emoji} {text}</span></div>')

def _metric_row(label, value, value_class="m-value"):
    return (f'<div class="m-row"><span class="m-label">{label}</span>'
            f'<span class="{value_class}">{value}</span></div>')

def _gauge_bar(pct, color="#00E676", height=8):
    pct = max(0, min(100, pct))
    return (f'<div style="background:#21262d;border-radius:{height}px;'
            f'height:{height}px;overflow:hidden;margin:6px 0">'
            f'<div style="width:{pct:.1f}%;height:100%;background:{color};'
            f'border-radius:{height}px;transition:width .8s"></div></div>')

def _traffic_light(status):
    return {"green": "🟢", "yellow": "🟡", "red": "🔴", "blue": "🔵", "gray": "⚪"}.get(status, "⚪")

def _score_dot_row(items):
    cells = ""
    for name, color in items:
        dot = _traffic_light(color)
        cells += (f'<div style="display:inline-flex;flex-direction:column;align-items:center;'
                  f'min-width:60px;padding:6px 4px">'
                  f'<span style="font-size:1.2rem">{dot}</span>'
                  f'<span style="font-size:.65rem;color:#8b949e;margin-top:2px;'
                  f'text-align:center;line-height:1.2">{name}</span></div>')
    return f'<div style="display:flex;flex-wrap:wrap;justify-content:center;gap:2px;margin:10px 0">{cells}</div>'

# Plotly 차트 생성 함수들
def _get_plotly_combo_chart(rv, nv, rd):
    if not rv or not rd: return None
    rd_rev, rv_rev, nv_rev = rd[::-1], rv[::-1], nv[::-1]
    labels = [d.strftime('%Y') if hasattr(d, 'strftime') else str(d)[:4] for d in rd_rev]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=labels, y=rv_rev, name='매출', marker_color='#2196F3', opacity=0.85))
    fig.add_trace(go.Scatter(x=labels, y=nv_rev, name='순이익', mode='lines+markers',
                             line=dict(color='#00E676', width=3), marker=dict(size=8), yaxis='y2'))
    fig.update_layout(
        title=dict(text="📊 연도별 재무 추이", font=dict(size=14, color='#8b949e')),
        paper_bgcolor='#161A22', plot_bgcolor='#161A22',
        font=dict(color='#8b949e', size=11), margin=dict(l=10, r=10, t=40, b=20), height=350,
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='rgba(45,51,59,0.5)', zeroline=False),
        yaxis2=dict(overlaying='y', side='right', showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig

def _get_plotly_yearly_bar(dates, y1, y2, name1, name2, c1, c2):
    if not dates or not y1: return None
    labels = [d.strftime('%Y') if hasattr(d, 'strftime') else str(d)[:4] for d in dates[::-1]]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=labels, y=y1[::-1], name=name1, marker_color=c1))
    fig.add_trace(go.Bar(x=labels, y=y2[::-1], name=name2, marker_color=c2))
    fig.update_layout(
        title=dict(text="📊 연도별 자산/부채 추이", font=dict(size=14, color='#8b949e')),
        barmode='group', paper_bgcolor='#161A22', plot_bgcolor='#161A22',
        font=dict(color='#8b949e', size=11),
        margin=dict(l=10, r=10, t=40, b=20), height=320,
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='rgba(45,51,59,0.5)', zeroline=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig

def _get_plotly_donut(labels, values, colors):
    if sum(values) == 0: return None
    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.55,
                                  marker_colors=colors, textinfo='percent', hoverinfo='label+percent')])
    fig.update_layout(
        title=dict(text="📊 지분 구성 비율", font=dict(size=14, color='#8b949e')),
        margin=dict(t=40, b=10, l=10, r=10), paper_bgcolor='#161A22', plot_bgcolor='#161A22',
        font=dict(color='#8b949e', size=12), showlegend=True, height=300,
        legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1))
    return fig

def _get_plotly_gauge(val, color):
    val_pct = val * 100
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=val_pct,
        number={'suffix': "%", 'font': {'size': 26, 'color': color}},
        gauge={'axis': {'range': [0, max(20, val_pct * 1.2)], 'tickwidth': 1, 'tickcolor': "#8b949e"},
               'bar': {'color': color, 'thickness': 0.75}, 'bgcolor': "rgba(0,0,0,0)", 'borderwidth': 0,
               'steps': [{'range': [0, 5], 'color': 'rgba(0,230,118,0.1)'},
                         {'range': [5, 10], 'color': 'rgba(255,193,7,0.1)'},
                         {'range': [10, 100], 'color': 'rgba(255,23,68,0.1)'}]}))
    fig.update_layout(
        title=dict(text="📊 공매도 비율 위험도", font=dict(size=14, color='#8b949e')),
        paper_bgcolor='#161A22', font=dict(color='#8b949e'),
        margin=dict(l=20, r=20, t=40, b=20), height=300)
    return fig

# ── 분석 함수들 ─────────────────────────────────────────

def _growth_stage(info, fin, bs, cf):
    # 🔧 개선: None 데이터 명시 처리
    rev_g_raw = info.get('revenueGrowth')
    margin_raw = info.get('profitMargins')

    if rev_g_raw is None and margin_raw is None:
        return (0, "❓ 판별 불가",
                "매출 성장률·순이익률 데이터가 부족하여 성장 단계를 판별할 수 없습니다.",
                "#607D8B")

    rev_g  = float(rev_g_raw) if rev_g_raw is not None else 0.0
    margin = float(margin_raw) if margin_raw is not None else 0.0
    rev    = info.get('totalRevenue', 0) or 0
    div_y  = info.get('dividendYield', 0) or 0

    op_cf = 0
    try:
        if cf is not None:
            for n in ['Operating Cash Flow', 'Total Cash From Operating Activities']:
                if n in cf.index:
                    # 🔧 개선: 정렬 후 최신 데이터 가져오기
                    s = cf.loc[n].dropna().sort_index(ascending=False)
                    op_cf = float(s.iloc[0]) if len(s) > 0 else 0
                    break
    except Exception:
        pass

    rev_declining = False
    try:
        rs = _get_row_series(fin, REV_ALIASES)
        if len(rs) >= 3:
            rd = rs.sort_index(ascending=False)
            if sum(1 for i in range(len(rd) - 1) if rd.iloc[i] < rd.iloc[i + 1]) >= 2:
                rev_declining = True
    except Exception:
        pass

    stages = {
        1: ("🌱 1단계 : 스타트업 / 개발", "매출 미미·R&D 집중. 시장 검증 전, 높은 리스크·높은 잠재력."),
        2: ("🚀 2단계 : 초기 고성장", "매출 폭발적 증가, 아직 적자. 시장점유율 확대에 올인하는 단계."),
        3: ("📈 3단계 : 고성장 흑자전환", "높은 매출 성장 + 이익 창출 시작. 성장·수익 균형점 진입."),
        4: ("💪 4단계 : 성숙한 성장", "안정적 매출 성장 + 높은 수익성. 우량 성장주의 전형."),
        5: ("💰 5단계 : 캐시카우", "성장 둔화, 현금 창출 극대화. 배당·자사주매입 등 주주환원 활발."),
        6: ("⏸️ 6단계 : 정체기", "매출 성장 멈춤, 이익 유지. 새 성장 동력이 필요한 시점."),
        7: ("📉 7단계 : 쇠퇴기", "매출·이익 동반 하락. 구조적 변화 없이는 위험 증가."),
        8: ("🔧 8단계 : 구조조정 / 턴어라운드", "적극적 사업 재편·회생 시도. 성공 시 큰 반등 가능."),
    }
    colors = {1: "#9C27B0", 2: "#FF5722", 3: "#FF9800", 4: "#4CAF50",
              5: "#2196F3", 6: "#607D8B", 7: "#F44336", 8: "#795548"}

    if rev < 1e8 and margin < -0.20: s = 1
    elif rev_g > 0.30 and margin < 0: s = 2
    elif rev_g > 0.20 and margin > 0: s = 3
    elif rev_g > 0.05 and margin > 0.10: s = 4
    elif 0 <= rev_g <= 0.05 and margin > 0.10 and (div_y > 0.01 or (rev > 0 and op_cf > rev * 0.1)): s = 5
    elif -0.05 <= rev_g <= 0.02 and margin > 0: s = 6
    elif rev_declining and margin < 0: s = 7
    elif rev_g < -0.05 and margin <= 0: s = 8
    elif rev_g < 0 and margin <= 0: s = 8
    elif rev_g > 0.30: s = 2
    elif margin > 0.15 and rev_g > 0.05: s = 4
    elif margin > 0.15: s = 5
    elif margin > 0: s = 6
    elif margin < -0.10: s = 8
    else: s = 6
    return s, stages[s][0], stages[s][1], colors[s]

def _stability(financials, rc):
    vals, _ = _annual_values(financials, rc)
    arr = np.array([v for v in vals if v is not None and not np.isnan(v)])
    if len(arr) < 2 or np.mean(arr) == 0: return "데이터 부족", "", "gray"
    cv = np.std(arr) / abs(np.mean(arr))
    if   cv < 0.10: return "매우 안정적 ✅", f"CV {cv:.3f}", "green"
    elif cv < 0.25: return "안정적 ✅",     f"CV {cv:.3f}", "green"
    elif cv < 0.50: return "보통 ⚠️",       f"CV {cv:.3f}", "yellow"
    else:           return "불안정 ❌",      f"CV {cv:.3f}", "red"

def _margin_trend(fin):
    try:
        rs = _get_row_series(fin, REV_ALIASES)
        ns = _get_row_series(fin, NI_ALIASES)
        idx = rs.index.intersection(ns.index).sort_values()
        margins = [(i, ns[i] / rs[i]) for i in idx if rs[i] != 0]
        if len(margins) < 2: return "N/A", [], "gray"
        f_m, l_m = margins[0][1], margins[-1][1]
        # 🔧 개선: "과거→현재" 방향 명시
        if l_m > f_m + 0.02:
            return f"증가 추세 📈 ({f_m*100:.1f}% → {l_m*100:.1f}%, 과거→현재)", margins, "green"
        if l_m < f_m - 0.02:
            return f"감소 추세 📉 ({f_m*100:.1f}% → {l_m*100:.1f}%, 과거→현재)", margins, "red"
        return f"유지 ➡️ ({l_m * 100:.1f}%)", margins, "yellow"
    except Exception:
        return "N/A", [], "gray"

def _growth_accel(fin, rc):
    vals, _ = _annual_values(fin, rc)
    if len(vals) < 3: return "N/A", "gray"
    g = []
    for i in range(len(vals) - 1):
        if vals[i + 1] and vals[i + 1] != 0:
            rate = (vals[i] - vals[i + 1]) / abs(vals[i + 1])
            # 🔧 개선: 비정상 성장률 필터 (10000% 이상은 데이터 오류)
            if abs(rate) < 100:
                g.append(rate)
    if len(g) < 2: return "N/A", "gray"

    recent_g = g[0]
    past_g_avg = np.mean(g[1:4]) if len(g) > 2 else g[1]

    if recent_g > past_g_avg + 0.05:
        return f"가속화 🚀 (최근 {recent_g*100:.1f}% vs 과거 {past_g_avg*100:.1f}%)", "green"
    elif recent_g < past_g_avg - 0.05:
        return f"감속 🐌 (최근 {recent_g*100:.1f}% vs 과거 {past_g_avg*100:.1f}%)", "yellow"
    return f"유지 ➡️ (최근 {recent_g*100:.1f}% vs 과거 {past_g_avg*100:.1f}%)", "green"

def _debt_trend(bs):
    for nc in [BS_LIAB_ALIASES, ['Long Term Debt'], ['Total Debt']]:
        series = _get_row_series(bs, nc)
        if len(series) >= 2:
            series = series.sort_index(ascending=False)
            latest, oldest = series.iloc[0], series.iloc[-1]
            if oldest != 0:
                chg = (latest - oldest) / abs(oldest)
                if   chg < -0.10: return f"감소 추세 ✅ ({chg*100:.1f}%)", "green"
                elif chg >  0.10: return f"증가 추세 ⚠️ (+{chg*100:.1f}%)", "red"
                else:             return f"안정 유지 ➡️ ({chg*100:.1f}%)", "yellow"
    return "데이터 부족", "gray"

# 🔧 개선: 섹터별 차등 D/E 판정 함수
def _debt_level(dte, sector):
    """부채/자본 비율을 섹터 특성에 맞게 판정"""
    if not isinstance(dte, (int, float)):
        return "N/A", "gray"
    d = float(dte)
    # 금융/부동산: 구조적으로 레버리지가 높음
    if sector in {"Financial Services", "Real Estate"}:
        if   d < 200: return f"낮음 ✅ ({d:.0f}%, 금융/부동산 기준)", "green"
        elif d < 500: return f"보통 ⚠️ ({d:.0f}%, 금융/부동산 기준)", "yellow"
        else:         return f"높음 ❌ ({d:.0f}%, 금융/부동산 기준)", "red"
    # 유틸리티
    elif sector == "Utilities":
        if   d < 100: return f"낮음 ✅ ({d:.0f}%)", "green"
        elif d < 200: return f"보통 ⚠️ ({d:.0f}%)", "yellow"
        else:         return f"높음 ❌ ({d:.0f}%)", "red"
    # 일반 섹터
    else:
        if   d < 50:  return f"낮음 ✅ ({d:.0f}%)", "green"
        elif d < 100: return f"보통 ⚠️ ({d:.0f}%)", "yellow"
        elif d < 200: return f"높음 ⚠️ ({d:.0f}%)", "red"
        else:         return f"매우 높음 ❌ ({d:.0f}%)", "red"

def _interest_burden(fin, info):
    ebit = _get_row(fin, ['EBIT', 'Operating Income'])
    interest = _get_row(fin, ['Interest Expense', 'Interest Expense Non Operating'])

    if ebit is not None and interest is not None and abs(interest) > 0:
        if ebit < 0:
            return "위험 ❌ (영업적자로 이자 지급 불가)", "red"
        icr = abs(ebit / interest)
        src = "SEC 실제"
        if   icr > 10: return f"매우 낮음 ✅ (ICR {icr:.1f}x, {src})", "green"
        elif icr >  5: return f"낮음 ✅ (ICR {icr:.1f}x, {src})", "green"
        elif icr >  2: return f"보통 ⚠️ (ICR {icr:.1f}x, {src})", "yellow"
        else:          return f"높음 ❌ (ICR {icr:.1f}x, {src})", "red"

    ebitda = info.get('ebitda', 0) or 0
    debt = info.get('totalDebt', 0) or 0
    if ebitda is not None and debt is not None and debt > 0:
        if ebitda < 0:
            return "위험 ❌ (EBITDA 적자)", "red"
        est_rate = 0.05
        cov = ebitda / (debt * est_rate)
        src = f"추정, 이자율 {est_rate * 100:.0f}% 가정"
        if   cov > 10: return f"매우 낮음 ✅ ({cov:.1f}x, {src})", "green"
        elif cov >  5: return f"낮음 ✅ ({cov:.1f}x, {src})", "green"
        elif cov >  2: return f"보통 ⚠️ ({cov:.1f}x, {src})", "yellow"
        else:          return f"높음 ❌ ({cov:.1f}x, {src})", "red"
    return "N/A", "gray"

def _vol_trend(info):
    vol   = info.get('volume', 0) or 0
    avg3m = info.get('averageVolume', 0) or 0
    if avg3m == 0: return "데이터 부족", "gray"
    r = vol / avg3m
    if   r > 1.5: return f"급증 🔥 ({r:.1f}배)", "yellow"
    elif r > 1.1: return f"증가 📈 ({r:.1f}배)", "yellow"
    elif r > 0.9: return f"평균 수준 ➡️ ({r:.1f}배)", "green"
    elif r > 0.5: return f"감소 📉 ({r:.1f}배)", "yellow"
    else:         return f"급감 ⚠️ ({r:.1f}배)", "red"

def _max_pain(tkr):
    """Max Pain — OI 기반 계산, 폴백으로 Volume 사용"""
    try:
        dates = tkr.options
        if not dates: return None, None, None, None, False
        exp = dates[0]
        o = tkr.option_chain(exp)
        c, p = o.calls.copy(), o.puts.copy()

        for col in ['openInterest', 'volume']:
            if col not in c.columns: c[col] = 0
            if col not in p.columns: p[col] = 0
            c[col] = pd.to_numeric(c[col], errors='coerce').fillna(0)
            p[col] = pd.to_numeric(p[col], errors='coerce').fillna(0)

        c_oi_sum = c['openInterest'].sum()
        p_oi_sum = p['openInterest'].sum()

        is_vol_weight = False

        if c_oi_sum > 0 and p_oi_sum > 0:
            # OI 데이터 양쪽 다 있으면 OI 사용
            if (c_oi_sum / max(p_oi_sum, 1) < 0.02) or (p_oi_sum / max(c_oi_sum, 1) < 0.02):
                weight_c = c['volume']
                weight_p = p['volume']
                is_vol_weight = True
            else:
                weight_c = c['openInterest']
                weight_p = p['openInterest']
        else:
            weight_c = c['volume']
            weight_p = p['volume']
            is_vol_weight = True
            if weight_c.sum() == 0 and weight_p.sum() == 0:
                return exp, None, [], [], False

        # 🔧 개선: .values 사용으로 인덱스 정렬 문제 방지
        strikes = sorted(set(c['strike']).union(set(p['strike'])))
        pain = {}
        for s in strikes:
            call_payout = float(np.sum(weight_c.values * np.maximum(0, s - c['strike'].values)))
            put_payout  = float(np.sum(weight_p.values * np.maximum(0, p['strike'].values - s)))
            pain[s] = call_payout + put_payout

        if not pain or max(pain.values()) == 0:
            mp = None
        else:
            mp = min(pain, key=pain.get)

        tc = c.nlargest(3, 'volume')[['strike', 'volume']].to_dict('records')
        tp = p.nlargest(3, 'volume')[['strike', 'volume']].to_dict('records')
        return exp, mp, tc, tp, is_vol_weight
    except Exception:
        return None, None, None, None, False

def _sector_pe_live(sector):
    etf = {"Technology": "XLK", "Financial Services": "XLF", "Healthcare": "XLV",
           "Energy": "XLE", "Consumer Cyclical": "XLY", "Consumer Defensive": "XLP",
           "Industrials": "XLI", "Communication Services": "XLC",
           "Utilities": "XLU", "Real Estate": "XLRE", "Basic Materials": "XLB"}.get(sector)
    if etf:
        try:
            pe = yf.Ticker(etf).info.get('trailingPE')
            if pe and isinstance(pe, (int, float)) and pe > 0:
                return pe, "실시간"
        except Exception:
            pass
    fb = {"Technology": 30, "Communication Services": 22, "Consumer Cyclical": 25,
          "Consumer Defensive": 22, "Financial Services": 14, "Healthcare": 22,
          "Industrials": 20, "Energy": 12, "Basic Materials": 15,
          "Real Estate": 35, "Utilities": 18}.get(sector)
    return (fb, "추정치") if fb else (None, "")

# 🔧 개선: 종합 점수 가중치
WEIGHTS = {"성장사이클": 3, "수익성": 3, "과거성적": 2, "성장성": 3, "재무건전": 3,
           "거래량": 1, "변동성": 1, "밸류에이션": 2, "전문가": 2, "지분구조": 1,
           "옵션": 1, "공매도": 1}

# ═══════════════════════════════════════════════════════════════
# 🎨 CSS
# ═══════════════════════════════════════════════════════════════

CSS = """
<style>
.s-card{background:#161A22;border:1px solid #2D333B;border-radius:16px;padding:28px 30px;margin-bottom:24px;box-shadow:0 6px 24px rgba(0,0,0,.3);transition:all .3s;max-width:960px;margin-left:auto;margin-right:auto;height:100%;box-sizing:border-box}
.s-card:hover{transform:translateY(-2px);border-color:#444c56;box-shadow:0 12px 36px rgba(0,0,0,.4)}
.s-title{font-size:1.15rem;font-weight:700;color:#82aaff;margin-bottom:20px;padding-bottom:12px;border-bottom:2px solid #21262d;display:flex;align-items:center;gap:10px}
.s-title .s-num{background:#21262d;border-radius:8px;padding:4px 10px;font-size:.8rem;color:#82aaff;font-weight:800}
.m-row{display:flex;justify-content:space-between;padding:8px 0;font-size:.93rem;align-items:center;border-bottom:1px solid rgba(45,51,59,.4)}.m-row:last-child{border-bottom:none}
.m-label{color:#8b949e;font-weight:500}.m-value{color:#c9d1d9;font-weight:600;text-align:right;max-width:55%}
.m-green{color:#00E676!important;font-weight:700}.m-red{color:#FF1744!important;font-weight:700}
.m-yellow{color:#FFC107!important;font-weight:700}.m-blue{color:#448aff!important;font-weight:700}.m-big{font-size:1.1rem;font-weight:800}
.divider{border-top:1px dashed #2D333B;margin:18px 0}
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:16px}@media(max-width:640px){.two-col{grid-template-columns:1fr}}
.opt-box{background:rgba(0,0,0,.25);padding:14px;border-radius:12px;border:1px solid #2D333B}
.opt-list{margin:8px 0 0;padding-left:18px;font-size:.85rem;color:#c9d1d9;line-height:1.9}
.m-table{width:100%;border-collapse:collapse;font-size:.85rem;margin-top:8px}
.m-table th{color:#6e7681;text-align:left;padding:8px;border-bottom:2px solid #21262d;font-weight:600}
.m-table td{color:#c9d1d9;padding:8px;border-bottom:1px solid #1c2029}
.p-container{background:#21262d;border-radius:10px;height:30px;display:flex;overflow:hidden;margin:10px 0}
.p-bar{height:100%;display:flex;align-items:center;justify-content:center;font-size:.72rem;font-weight:700;color:#fff;transition:width .6s}
.n-item{padding:12px 0;border-bottom:1px solid #2D333B}.n-item:last-child{border-bottom:none}
.n-title{color:#82aaff;font-weight:600;font-size:.93rem;text-decoration:none}.n-title:hover{text-decoration:underline;color:#a8c7ff}
.n-meta{color:#6e7681;font-size:.78rem;margin-top:3px}
.header-wrap{display:flex;justify-content:space-between;align-items:flex-end;flex-wrap:wrap;gap:12px;max-width:960px;margin:0 auto 8px}
.note-box{font-size:.73rem;color:#6e7681;line-height:1.6;padding:10px;background:rgba(0,0,0,.15);border-radius:8px;margin-top:10px}
</style>
"""

# ═══════════════════════════════════════════════════════════════
# 🏗️ 메인 렌더링
# ═══════════════════════════════════════════════════════════════

def render_company_details(ticker_str: str):
    st.markdown(CSS, unsafe_allow_html=True)

    with st.spinner(f"📡  {ticker_str}  분석 중 …"):
        try:
            tkr = yf.Ticker(ticker_str)
            info = tkr.info or {}
        except Exception as e:
            st.error(f"❌ 데이터를 불러올 수 없습니다 — {e}")
            return
        if not info or 'shortName' not in info:
            st.error("❌ 유효하지 않은 종목이거나 데이터가 없습니다.")
            return

        try:
            fin = tkr.financials
            if fin is None or fin.empty:
                fin = tkr.income_stmt
        except Exception:
            fin = None
        try: bs = tkr.balance_sheet
        except Exception: bs = None
        try: cf = tkr.cashflow
        except Exception: cf = None

        sector   = info.get('sector', 'N/A')
        industry = info.get('industry', 'N/A')
        price    = info.get('currentPrice') or info.get('regularMarketPrice') or 0
        prev_c   = info.get('previousClose') or price or 1
        day_chg  = ((price - prev_c) / prev_c * 100) if prev_c else 0
        chg_c    = "#00E676" if day_chg >= 0 else "#FF1744"
        chg_s    = "+" if day_chg >= 0 else ""
        if price == 0:
            st.warning("⚠️ 현재가를 불러올 수 없습니다.")

        cagr_rev, yr_rev = _calc_cagr_with_years(fin, REV_ALIASES)
        cagr_ni,  yr_ni  = _calc_cagr_with_years(fin, NI_ALIASES)
        cagr_eps, yr_eps = _calc_cagr_with_years(fin, EPS_ALIASES)

    # 헤더
    name_safe = _esc(info.get('shortName', ticker_str))
    st.markdown(f"""
    <div class="header-wrap"><div>
        <span style="font-size:1.6rem;font-weight:800;color:#e6edf3">🏢 {name_safe}</span>
        <span style="font-size:.95rem;color:#6e7681;margin-left:8px">({_esc(ticker_str)})</span><br>
        <span style="font-size:.85rem;color:#8b949e">{_esc(sector)} · {_esc(industry)}</span>
    </div><div style="text-align:right">
        <span style="font-size:1.7rem;font-weight:800;color:{chg_c}">${price:,.2f}</span><br>
        <span style="font-size:.9rem;color:{chg_c}">{chg_s}{day_chg:.2f}% 오늘</span>
    </div></div>""", unsafe_allow_html=True)
    st.markdown("---")

    all_verdicts = []

    # ═══ 1. 성장 사이클 ═══
    sn, sname, sdesc, scolor = _growth_stage(info, fin, bs, cf)
    stage_map = {1:"#9C27B0",2:"#FF5722",3:"#FF9800",4:"#4CAF50",5:"#2196F3",6:"#607D8B",7:"#F44336",8:"#795548"}
    stage_lbl = {1:"스타트업",2:"초기성장",3:"고성장",4:"성숙성장",5:"캐시카우",6:"정체",7:"쇠퇴",8:"턴어라운드"}

    bar_html = ""
    for i in range(1, 9):
        curr = (i == sn)
        bg = stage_map.get(i, "#21262d") if curr else "#21262d"
        op = "1" if curr else "0.3"; fw = "700" if curr else "400"
        brd = f"3px solid {stage_map.get(i,'#2D333B')}" if curr else "1px solid #2D333B"
        rad = "10px 0 0 10px" if i==1 else ("0 10px 10px 0" if i==8 else "0")
        shadow = f"0 0 12px {stage_map.get(i,'#000')}66" if curr else "none"
        bar_html += (f'<div style="flex:1;background:{bg};opacity:{op};text-align:center;'
                     f'padding:12px 2px;font-size:.6rem;color:#fff;border:{brd};'
                     f'border-radius:{rad};font-weight:{fw};box-shadow:{shadow};'
                     f'transition:all .3s">{i}<br>{stage_lbl.get(i,"")}</div>')

    # 🔧 개선: sn=0 처리
    v1_c = ("green" if sn in [3,4] else ("blue" if sn==5 else
            ("yellow" if sn in [1,2,6] else ("red" if sn in [7,8] else "gray"))))
    v1_map = {0:"데이터 부족으로 판별 불가", 1:"초기 — 높은 리스크·높은 잠재력",
              2:"폭풍 성장 중 — 적자이지만 매출 급증", 3:"성장+이익 = 최적 타이밍 가능",
              4:"안정 성장 우량주 — 핵심 보유 후보", 5:"현금 창출 극대화 — 배당·안정성",
              6:"새 성장 동력 필요", 7:"위험 — 구조적 하락 주의", 8:"턴어라운드 성공 여부가 핵심"}
    all_verdicts.append(("성장사이클", v1_c))

    st.markdown(f"""
    <div class="s-card">
        <div class="s-title"><span class="s-num">01</span> 이 회사, 지금 어느 단계인가요?</div>
        <div style="display:flex;gap:3px;margin-bottom:20px">{bar_html}</div>
        <div style="text-align:center;margin:16px 0">
            <span style="display:inline-block;padding:10px 28px;border-radius:24px;font-weight:700;background:{scolor};color:#fff;font-size:1.1rem;box-shadow:0 4px 16px {scolor}44">{sname}</span>
            <div style="font-size:.88rem;color:#8b949e;margin-top:12px;line-height:1.7">{sdesc}</div>
        </div>
        <div class="divider"></div>
        <div class="two-col"><div>
            {_metric_row("분기 매출 성장률 (YoY)", _fmt_pct(info.get('revenueGrowth')))}
            {_metric_row("순이익률", _fmt_pct(info.get('profitMargins')))}
        </div><div>
            {_metric_row("배당수익률", _fmt_pct(info.get('dividendYield')))}
            {_metric_row("ROE", _fmt_pct(info.get('returnOnEquity')))}
        </div></div>
        <div class="note-box">💡 성장률은 Yahoo Finance 기준 분기(QoQ) YoY 수치입니다.</div>
        {_verdict_badge(v1_c, "📌", f"종합: {v1_map.get(sn, '')}")}
    </div>""", unsafe_allow_html=True)

    # ═══ 2. 수익성 ═══
    gross_m = info.get('grossMargins'); net_m = info.get('profitMargins')
    mcap = info.get('marketCap'); ttm_eps = info.get('trailingEps')
    ttm_rev = info.get('totalRevenue'); ttm_ni = info.get('netIncomeToCommon')
    op_m = info.get('operatingMargins')  # 🔧 개선: 영업이익률 추가

    # 🔧 개선: ttm_ni>0 중복 제거 → operatingMargins>0.15 대체
    ps = sum(1 for x in [
        gross_m and gross_m > 0.4,
        net_m and net_m > 0.1,
        cagr_rev and cagr_rev > 0.05,
        cagr_ni and cagr_ni > 0.05,
        op_m and op_m > 0.15,
    ] if x)
    if   ps >= 4: v2_c, v2_t = "green",  "💰 매우 우수 — 높은 마진 + 지속 성장"
    elif ps >= 3: v2_c, v2_t = "green",  "✅ 양호 — 수익성과 성장 겸비"
    elif ps >= 2: v2_c, v2_t = "yellow", "⚠️ 보통 — 일부 지표 개선 필요"
    else:         v2_c, v2_t = "red",    "❌ 수익성 미흡 — 적자 또는 마진 악화"
    all_verdicts.append(("수익성", v2_c))

    ni_cls = "m-green" if ttm_ni and ttm_ni > 0 else "m-red"
    cr_cls = lambda v: "m-green" if v and v > 0 else "m-red"
    gm_pct = (gross_m or 0) * 100; nm_pct = (net_m or 0) * 100
    gm_gauge = _gauge_bar(max(0, gm_pct), "#4CAF50", 10)
    nm_gauge = _gauge_bar(max(0, nm_pct), "#2196F3", 10)

    # 🔧 개선: CAGR 라벨 — 턴어라운드 표시
    def _cagr_display(name, cagr, yr):
        if cagr is not None:
            return f"{yr}년 {name} CAGR (SEC)", _fmt_pct(cagr)
        elif yr > 0:
            return f"{name} CAGR", "턴어라운드 (음→양 전환)"
        return f"{name} CAGR", "N/A"

    rev_lbl, rev_val = _cagr_display("매출", cagr_rev, yr_rev)
    ni_lbl, ni_val = _cagr_display("순이익", cagr_ni, yr_ni)
    eps_lbl, eps_val = _cagr_display("EPS", cagr_eps, yr_eps)

    st.markdown(f"""
    <div class="s-card">
        <div class="s-title"><span class="s-num">02</span> 돈을 잘 버는 회사인가요? <span style="font-size:.75rem;color:#6e7681">SEC 데이터</span></div>
        <div class="two-col"><div>
            {_metric_row("시가총액", _fmt_num(mcap), "m-value m-big")}
            {_metric_row("TTM EPS (주당순이익)", f"${_safe(ttm_eps)}")}
            {_metric_row("최근 12개월 매출", _fmt_num(ttm_rev))}
            {_metric_row("최근 12개월 순이익", _fmt_num(ttm_ni), ni_cls)}
        </div><div>
            <div style="margin-bottom:12px">
                <div style="display:flex;justify-content:space-between;font-size:.88rem">
                    <span style="color:#8b949e">총이익률 (Gross)</span>
                    <span style="color:#c9d1d9;font-weight:700">{_fmt_pct(gross_m)}</span>
                </div>{gm_gauge}
            </div>
            <div style="margin-bottom:12px">
                <div style="display:flex;justify-content:space-between;font-size:.88rem">
                    <span style="color:#8b949e">순이익률 (Net)</span>
                    <span style="color:#c9d1d9;font-weight:700">{_fmt_pct(net_m)}</span>
                </div>{nm_gauge}
            </div>
            {_metric_row("영업이익률 (Operating)", _fmt_pct(op_m))}
        </div></div>
        <div class="divider"></div>
        <div class="two-col"><div>
            {_metric_row(rev_lbl, rev_val, cr_cls(cagr_rev))}
            {_metric_row(ni_lbl, ni_val, cr_cls(cagr_ni))}
        </div><div>
            {_metric_row(eps_lbl, eps_val, cr_cls(cagr_eps))}
            <div class="note-box" style="margin-top:6px;">※ 이익이 적자(-)에서 시작된 경우 CAGR은 '턴어라운드'로 표시됩니다.</div>
        </div></div>
        {_verdict_badge(v2_c, "📌", v2_t)}
    </div>""", unsafe_allow_html=True)

    # ═══ 3. 지금까지 성적 ═══
    rev_stab, rev_cv, stab_c = _stability(fin, REV_ALIASES)
    mtrend, _, mtrend_c = _margin_trend(fin)
    accel, accel_c = _growth_accel(fin, REV_ALIASES)

    roe_val = info.get('returnOnEquity')
    roe_lbl = f"{_fmt_pct(roe_val)}" if roe_val else "N/A"
    roe_c = "green" if roe_val and roe_val > 0.1 else ("yellow" if roe_val and roe_val > 0 else "red")

    rv, rd = _annual_values(fin, REV_ALIASES)
    nv, nd = _annual_values(fin, NI_ALIASES)

    tbl_rows = ""
    for i in range(min(len(rv), len(nv), 4)):
        yr = rd[i].strftime('%Y') if hasattr(rd[i], 'strftime') else str(rd[i])[:4]
        mg = (nv[i] / rv[i] * 100) if rv[i] and rv[i] != 0 else 0
        nc = "#00E676" if nv[i] and nv[i] > 0 else "#FF1744"
        mc = "#00E676" if mg > 0 else "#FF1744"
        tbl_rows += (f"<tr><td>{yr}</td><td>{_fmt_num(rv[i])}</td>"
                     f"<td style='color:{nc}'>{_fmt_num(nv[i])}</td>"
                     f"<td style='color:{mc}'>{mg:.1f}%</td></tr>")

    fig3 = _get_plotly_combo_chart(rv[:4] if rv else [], nv[:4] if nv else [], rd[:4] if rd else [])

    s3 = sum(1 for c in [stab_c, mtrend_c, accel_c, roe_c] if c == "green")
    if   s3 >= 3: v3_c, v3_t = "green",  "✅ 우수한 트랙 레코드 — 안정 성장 + 높은 ROE"
    elif s3 >= 2: v3_c, v3_t = "yellow", "⚠️ 보통 — 일부 양호, 개선 여지"
    else:         v3_c, v3_t = "red",    "❌ 주의 — 수익 불안정 또는 하락 추세"
    all_verdicts.append(("과거성적", v3_c))

    col1, col2 = st.columns([1.1, 1])
    with col1:
        st.markdown(f"""
        <div class="s-card">
            <div class="s-title"><span class="s-num">03</span> 지금까지 성적 <span style="font-size:.75rem;color:#6e7681">SEC 데이터</span></div>
            {_metric_row("수익 안정성", f'{rev_stab} <span style="font-size:.75rem;color:#555">{rev_cv}</span>')}
            {_metric_row("이익 마진 추이", mtrend)}
            {_metric_row("성장 가속화", accel)}
            {_metric_row("ROE 수준", roe_lbl)}
            <div class="divider"></div>
            <table class="m-table"><tr><th>연도</th><th>매출</th><th>순이익</th><th>순이익률</th></tr>{tbl_rows}</table>
            {_verdict_badge(v3_c, "📌", v3_t)}
        </div>""", unsafe_allow_html=True)
    with col2:
        if fig3:
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.markdown("<div style='text-align:center;color:#6e7681;padding:100px 0;background:#161A22;border:1px solid #2D333B;border-radius:16px;height:100%;box-sizing:border-box;'>차트 데이터를 불러올 수 없습니다.</div>", unsafe_allow_html=True)

    # ═══ 4. 성장 가능성 ═══
    payout = info.get('payoutRatio', 0) or 0
    retention = max(0, 1 - payout)
    roe_v = info.get('returnOnEquity', 0) or 0
    sust_g = roe_v * retention if roe_v else None
    eg = info.get('earningsGrowth'); rg = info.get('revenueGrowth')
    fwd_eps = info.get('forwardEps')

    peg = info.get('pegRatio')
    if (peg is None or pd.isna(peg)):
        t_pe_val = info.get('trailingPE')
        if t_pe_val and eg and eg > 0:
            peg = t_pe_val / (eg * 100)

    gs = sum(1 for x in [eg and eg > 0.15, rg and rg > 0.10, retention > 0.60,
                          sust_g and sust_g > 0.10, peg and 0 < peg < 1.5] if x)
    if   gs >= 4: v4_c, v4_t = "green",  "🚀 높은 성장 잠재력 — 수익 재투자 + 고성장"
    elif gs >= 2: v4_c, v4_t = "yellow", "⚠️ 보통 — 성장 가능성 있으나 모니터링 필요"
    else:         v4_c, v4_t = "red",    "❌ 성장 둔화 — 새 동력 부재"
    all_verdicts.append(("성장성", v4_c))

    eg_cls = "m-green" if eg and eg > 0 else "m-red"
    rg_cls = "m-green" if rg and rg > 0 else "m-red"

    # 🔧 개선: "분기 이익 성장률" → "분기 EPS 성장률"
    st.markdown(f"""
    <div class="s-card">
        <div class="s-title"><span class="s-num">04</span> 성장 가능성 <span style="font-size:.75rem;color:#6e7681">SEC + Yahoo</span></div>
        <div class="two-col"><div>
            {_metric_row("분기 EPS 성장률 (YoY)", _fmt_pct(eg), eg_cls)}
            {_metric_row("분기 매출 성장률 (YoY)", _fmt_pct(rg), rg_cls)}
            {_metric_row("Forward EPS", f"${_safe(fwd_eps)}")}
            {_metric_row("PEG 비율", f"{peg:.2f}" if peg else "N/A", "m-green" if peg and 0 < peg < 1.5 else "m-value")}
        </div><div>
            {_metric_row("ROE", _fmt_pct(roe_v))}
            {_metric_row("수익 유보율 (1 - 배당성향)", _fmt_pct(retention))}
            {_metric_row("지속가능 성장률 (g = ROE × 유보율)", _fmt_pct(sust_g),
                         "m-green" if sust_g and sust_g > 0.1 else "m-value")}
            <div class="note-box">
                💡 <b>지속가능 성장률(g)</b>: 외부 자금 없이 내부 유보만으로 달성 가능한 이론적 최대 성장률.<br>
                PEG &lt; 1.5 면 EPS 성장률 대비 현재 주가가 저평가 가능성.
            </div>
        </div></div>
        {_verdict_badge(v4_c, "📌", v4_t)}
    </div>""", unsafe_allow_html=True)

    # ═══ 5. 재무 건전성 ═══
    try:
        curr_d = _get_row(bs, ['Current Debt', 'Current Portion Of Long Term Debt']) or 0
        lt_d = _get_row(bs, ['Long Term Debt', 'Long Term Debt And Capital Lease Obligation']) or 0
        ta = _get_row(bs, BS_ASSETS_ALIASES) or info.get('totalAssets', 0) or 0
        tl = _get_row(bs, BS_LIAB_ALIASES) or 0
        eq = _get_row(bs, ['Stockholders Equity', 'Total Stockholder Equity']) or 0
        na = ta - tl

        ta_s = _get_row_series(bs, BS_ASSETS_ALIASES)
        tl_s = _get_row_series(bs, BS_LIAB_ALIASES)
        idx5 = ta_s.index.intersection(tl_s.index).sort_values(ascending=False)[:4]
        fig5 = _get_plotly_yearly_bar(idx5, [ta_s[i] for i in idx5], [tl_s[i] for i in idx5],
                                       "총 자산", "총 부채", "#2196F3", "#FF5722") if len(idx5) > 0 else None
    except Exception:
        curr_d = lt_d = ta = tl = eq = na = 0; fig5 = None

    cash = info.get('totalCash', 0) or 0
    dte = info.get('debtToEquity')
    dt_trend, dt_c = _debt_trend(bs)
    ib_txt, ib_c = _interest_burden(fin, info)

    # 🔧 개선: 섹터별 차등 D/E 판정
    dl, dl_c = _debt_level(dte, sector)

    hs = sum(1 for x in [dl_c == "green", dt_c == "green", ib_c == "green",
                          cash > tl * 0.2 if tl else False] if x)
    if   hs >= 3: v5_c, v5_t = "green",  "💪 재무 건전 — 낮은 부채, 충분한 현금"
    elif hs >= 2: v5_c, v5_t = "yellow", "⚠️ 보통 — 부채 관리 모니터링 필요"
    else:         v5_c, v5_t = "red",    "❌ 주의 — 부채 높거나 현금 부족"
    all_verdicts.append(("재무건전", v5_c))

    col1, col2 = st.columns([1.1, 1])
    with col1:
        st.markdown(f"""
        <div class="s-card">
            <div class="s-title"><span class="s-num">05</span> 회사에 돈이 얼마나 있나요? <span style="font-size:.75rem;color:#6e7681">SEC + Yahoo</span></div>
            {_metric_row("💵 보유 현금", _fmt_num(cash), "m-value m-green m-big")}
            {_metric_row("순 자산 (자산-부채)", _fmt_num(na), "m-green" if na > 0 else "m-red")}
            <div class="divider"></div>
            {_metric_row("부채 수준 (D/E)", dl)}
            {_metric_row("부채 추세", dt_trend)}
            {_metric_row("이자 부담 (ICR)", ib_txt)}
            {_metric_row("부채/자본 비율", f'{dte:.1f}%' if isinstance(dte, (int, float)) else 'N/A')}
            <div class="note-box">※ D/E 판정은 섹터({_esc(sector)}) 특성을 반영한 기준입니다.<br>
            ※ 순자산과 자본은 비지배지분에 의해 차이가 날 수 있습니다.</div>
            {_verdict_badge(v5_c, "📌", v5_t)}
        </div>""", unsafe_allow_html=True)
    with col2:
        if fig5:
            st.plotly_chart(fig5, use_container_width=True)
        else:
            st.markdown("<div style='text-align:center;color:#6e7681;padding:100px 0;background:#161A22;border:1px solid #2D333B;border-radius:16px;height:100%;box-sizing:border-box;'>차트 데이터 없음</div>", unsafe_allow_html=True)

    # ═══ 6. 거래량 ═══
    vol = info.get('volume', 0) or 0; avg10 = info.get('averageVolume10days', 0) or 0
    avg3m = info.get('averageVolume', 0) or 0; vt_txt, vt_c = _vol_trend(info)
    v6_t = {"green":"✅ 거래량 정상","yellow":"⚠️ 거래량 변동","red":"🔥 거래량 이상"}.get(vt_c, "데이터 부족")
    all_verdicts.append(("거래량", vt_c))

    max_vol = max(vol, avg10, avg3m, 1)
    vol_bars = ""
    for lbl, v, c in [("현재", vol, "#82aaff"), ("10일평균", avg10, "#607D8B"), ("3개월평균", avg3m, "#444c56")]:
        w = v / max_vol * 100
        vol_bars += (f'<div style="display:flex;align-items:center;gap:10px;margin:6px 0">'
                     f'<span style="min-width:70px;font-size:.78rem;color:#8b949e;text-align:right">{lbl}</span>'
                     f'<div style="flex:1;background:#21262d;border-radius:6px;height:22px;overflow:hidden">'
                     f'<div style="width:{w:.1f}%;height:100%;background:{c};border-radius:6px;'
                     f'display:flex;align-items:center;padding-left:8px;font-size:.72rem;color:#fff;font-weight:600">'
                     f'{_fmt_num(v, False)}</div></div></div>')

    st.markdown(f"""
    <div class="s-card">
        <div class="s-title"><span class="s-num">06</span> 현재 사람들이 많이 사고 있나요? <span style="font-size:.75rem;color:#6e7681">Yahoo</span></div>
        <div class="two-col"><div>
            {_metric_row("현재 거래량", f"{_fmt_num(vol, False)} 주")}
            {_metric_row("10일 평균", f"{_fmt_num(avg10, False)} 주")}
            {_metric_row("3개월 평균", f"{_fmt_num(avg3m, False)} 주")}
            <div class="divider"></div>{_metric_row("거래량 변동 추이", vt_txt)}
        </div><div>
            <div style="font-size:.82rem;color:#6e7681;margin-bottom:6px;font-weight:600">📊 거래량 비교</div>
            {vol_bars}
        </div></div>
        {_verdict_badge(vt_c, "📌", v6_t)}
    </div>""", unsafe_allow_html=True)

    # ═══ 7. 변동성 ═══
    beta = info.get('beta')
    if isinstance(beta, (int, float)):
        if   beta < 0.8: bl, bc = "저변동 — 시장보다 안정", "green"
        elif beta < 1.2: bl, bc = "시장과 유사", "yellow"
        elif beta < 1.5: bl, bc = "높은 변동성 ⚠️", "red"
        else:            bl, bc = "매우 높은 변동성 🔥", "red"
    else: bl, bc = "N/A", "gray"
    all_verdicts.append(("변동성", bc))

    w52h = info.get('fiftyTwoWeekHigh'); w52l = info.get('fiftyTwoWeekLow'); w52c = info.get('52WeekChange')
    pos_str, pos_bar = "N/A", ""
    if price and w52h and w52l and w52h != w52l:
        pos52 = max(0, min(100, (price - w52l) / (w52h - w52l) * 100))
        pos_str = f"{pos52:.1f}%"
        pos_bar = f"<div style='margin:14px 0'><div style='display:flex;justify-content:space-between;font-size:.73rem;color:#6e7681;margin-bottom:4px'><span>저 ${w52l:,.2f}</span><span style='color:#82aaff;font-weight:600'>현재 ${price:,.2f}</span><span>고 ${w52h:,.2f}</span></div><div style='background:#21262d;border-radius:6px;height:12px;position:relative'><div style='background:linear-gradient(90deg,#FF1744 0%,#FFC107 50%,#00E676 100%);width:100%;height:100%;border-radius:6px;opacity:0.25'></div><div style='position:absolute;top:-3px;left:{pos52:.1f}%;width:18px;height:18px;background:#82aaff;border-radius:50%;transform:translateX(-50%);border:2px solid #fff;box-shadow:0 0 8px #82aaff88'></div></div></div>"

    v7_t = f"베타 {beta:.2f} — {bl}" if isinstance(beta, (int, float)) else "변동성 데이터 부족"

    st.markdown(f"""
    <div class="s-card">
        <div class="s-title"><span class="s-num">07</span> 변동성이 큰가요? <span style="font-size:.75rem;color:#6e7681">Yahoo</span></div>
        <div class="two-col"><div>
            {_metric_row("베타 (β)", f"{beta:.2f} ({bl})" if isinstance(beta, (int, float)) else "N/A")}
            {_metric_row("52주 가격 변화율", _fmt_pct(w52c), "m-green" if w52c and w52c > 0 else "m-red")}
            {_metric_row("52주 최고가", f"${w52h:,.2f}" if w52h else "N/A")}
            {_metric_row("52주 최저가", f"${w52l:,.2f}" if w52l else "N/A")}
            {_metric_row("현재가 위치 (52주 내)", pos_str)}
        </div><div>
            <div style="font-size:.82rem;color:#6e7681;margin-bottom:4px;font-weight:600">📍 52주 범위 내 위치</div>
            {pos_bar}
            <div class="note-box">💡 베타 &lt; 1 = 시장(S&amp;P500) 대비 안정적 / 베타 &gt; 1 = 시장보다 변동성 큼</div>
        </div></div>
        {_verdict_badge(bc, "📌", v7_t)}
    </div>""", unsafe_allow_html=True)

    # ═══ 8. 밸류에이션 ═══
    t_pe = info.get('trailingPE'); f_pe = info.get('forwardPE')
    p_s = info.get('priceToSalesTrailing12Months'); p_b = info.get('priceToBook')
    s_pe, pe_source = _sector_pe_live(sector)

    pe_comp = ""
    if t_pe and s_pe:
        diff = ((t_pe - s_pe) / s_pe) * 100
        if   diff > 30:  pe_comp = f"섹터 대비 <b style='color:#FF1744'>고평가 (+{diff:.0f}%)</b>"
        elif diff > 0:   pe_comp = f"섹터 대비 <b style='color:#FFC107'>약간 고평가 (+{diff:.0f}%)</b>"
        elif diff > -20: pe_comp = f"섹터 대비 <b style='color:#00E676'>적정 ({diff:.0f}%)</b>"
        else:            pe_comp = f"섹터 대비 <b style='color:#00E676'>저평가 ({diff:.0f}%)</b>"

    if t_pe and s_pe:
        if   t_pe < s_pe * 0.8: v8_c, v8_t = "green",  "💎 저평가 가능성"
        elif t_pe < s_pe * 1.3: v8_c, v8_t = "yellow", "⚖️ 적정 수준"
        else:                   v8_c, v8_t = "red",    "💸 고평가 가능성"
    else: v8_c, v8_t = "gray", "비교 데이터 부족"
    all_verdicts.append(("밸류에이션", v8_c))

    pe_visual = ""
    if t_pe and s_pe:
        max_pe = max(t_pe, s_pe) * 1.3
        pe_visual = f"<div style='margin:10px 0'><div style='font-size:.78rem;color:#8b949e;margin-bottom:6px'>P/E 비교</div><div style='display:flex;align-items:center;gap:8px;margin:4px 0'><span style='min-width:50px;font-size:.75rem;color:#82aaff'>이 종목</span><div style='flex:1;background:#21262d;border-radius:4px;height:18px;overflow:hidden'><div style='width:{t_pe/max_pe*100:.1f}%;height:100%;background:#82aaff;border-radius:4px;display:flex;align-items:center;justify-content:flex-end;padding-right:6px;font-size:.7rem;color:#fff;font-weight:600'>{t_pe:.1f}</div></div></div><div style='display:flex;align-items:center;gap:8px;margin:4px 0'><span style='min-width:50px;font-size:.75rem;color:#607D8B'>섹터평균</span><div style='flex:1;background:#21262d;border-radius:4px;height:18px;overflow:hidden'><div style='width:{s_pe/max_pe*100:.1f}%;height:100%;background:#607D8B;border-radius:4px;display:flex;align-items:center;justify-content:flex-end;padding-right:6px;font-size:.7rem;color:#fff;font-weight:600'>{s_pe:.1f}</div></div></div></div>"
    pe_src_lbl = f"평균 P/E ≈ {s_pe:.1f} ({pe_source})" if s_pe else "N/A"

    st.markdown(f"""
    <div class="s-card">
        <div class="s-title"><span class="s-num">08</span> 이 종목 비싼가요? <span style="font-size:.75rem;color:#6e7681">Yahoo</span></div>
        <div class="two-col"><div>
            {_metric_row("Trailing P/E", f"{t_pe:.2f}" if isinstance(t_pe, (int, float)) else "N/A")}
            {_metric_row("Forward P/E", f"{f_pe:.2f}" if isinstance(f_pe, (int, float)) else "N/A")}
            {_metric_row("P/S (TTM)", f"{p_s:.2f}" if isinstance(p_s, (int, float)) else "N/A")}
            {_metric_row("P/B", f"{p_b:.2f}" if isinstance(p_b, (int, float)) else "N/A")}
            <div class="divider"></div>
            {_metric_row(f"섹터 ({_esc(sector)})", pe_src_lbl)}
            {_metric_row("섹터 대비", pe_comp if pe_comp else "N/A")}
        </div><div>
            {pe_visual}
            <div class="note-box">※ 섹터 P/E는 {pe_source} 기준.</div>
        </div></div>
        {_verdict_badge(v8_c, "📌", v8_t)}
    </div>""", unsafe_allow_html=True)

    # ═══ 9. 전문가 의견 ═══
    rm = info.get('recommendationMean'); rk = str(info.get('recommendationKey', 'N/A')).upper()
    if isinstance(rm, (int, float)):
        if   rm <= 1.5: con, cc = "🟢 강력 매수", "green"
        elif rm <= 2.0: con, cc = "🟢 매수", "green"
        elif rm <= 2.5: con, cc = "🟡 매수 우위", "yellow"
        elif rm <= 3.0: con, cc = "🟡 보유", "yellow"
        elif rm <= 3.5: con, cc = "🟠 매도 우위", "red"
        elif rm <= 4.0: con, cc = "🔴 매도", "red"
        else:           con, cc = "🔴 강력 매도", "red"
    else: con, cc = "N/A", "gray"
    all_verdicts.append(("전문가", cc))

    t_mean = info.get('targetMeanPrice'); t_median = info.get('targetMedianPrice')
    t_high = info.get('targetHighPrice'); t_low = info.get('targetLowPrice')
    n_ana = info.get('numberOfAnalystOpinions', 0)
    up_pct, up_str = 0, "N/A"
    try:
        if t_median and price and price > 0:
            up_pct = ((t_median - price) / price) * 100
            up_str = f"{'📈' if up_pct > 0 else '📉'} {up_pct:+.1f}%"
    except Exception: pass

    target_bar = ""
    if t_low and t_high and t_median and price and t_high > t_low:
        rng = t_high - t_low
        curr_pos = max(0, min(100, (price - t_low) / rng * 100))
        med_pos = max(0, min(100, (t_median - t_low) / rng * 100))
        target_bar = f"<div style='margin:14px 0'><div style='font-size:.78rem;color:#6e7681;margin-bottom:6px'>목표가 범위</div><div style='display:flex;justify-content:space-between;font-size:.7rem;color:#6e7681;margin-bottom:3px'><span>${t_low:,.0f}</span><span>${t_high:,.0f}</span></div><div style='background:#21262d;border-radius:6px;height:14px;position:relative'><div style='position:absolute;top:-2px;left:{curr_pos:.1f}%;width:18px;height:18px;background:#FF9800;border-radius:50%;transform:translateX(-50%);border:2px solid #fff;z-index:2'></div><div style='position:absolute;top:-1px;left:{med_pos:.1f}%;width:14px;height:16px;background:#00E676;border-radius:3px;transform:translateX(-50%);z-index:1'></div></div><div style='display:flex;justify-content:center;gap:16px;margin-top:6px;font-size:.7rem'><span style='color:#FF9800'>● 현재가</span><span style='color:#00E676'>● 중앙 목표가</span></div></div>"

    st.markdown(f"""
    <div class="s-card">
        <div class="s-title"><span class="s-num">09</span> 전문가들의 의견 <span style="font-size:.75rem;color:#6e7681">Yahoo</span></div>
        <div class="two-col"><div>
            {_metric_row("컨센서스 등급", rk, "m-value m-blue m-big")}
            {_metric_row("평균 의견 (1매수~5매도)", f"{rm:.2f}" if isinstance(rm, (int, float)) else "N/A")}
            {_metric_row("종합 의견", con)}{_metric_row("참여 애널리스트", f"{n_ana}명")}
            <div class="divider"></div>
            {_metric_row("평균 목표가", f"${_safe(t_mean)}")}{_metric_row("중앙값 목표가", f"${_safe(t_median)}")}
            {_metric_row("최고 목표가", f"${_safe(t_high)}")}{_metric_row("최저 목표가", f"${_safe(t_low)}")}
        </div><div>
            {target_bar}
            <div style="text-align:center;margin-top:16px;padding:14px;background:rgba(0,0,0,.2);border-radius:12px;border:1px solid #2D333B">
                <div style="font-size:.82rem;color:#8b949e">목표가 대비 여력</div>
                <div style="font-size:1.5rem;font-weight:800;color:{'#00E676' if up_pct > 0 else '#FF1744'};margin-top:4px">{up_str}</div>
            </div>
        </div></div>
        {_verdict_badge(cc, "📌", f"애널리스트 {n_ana}명 {rk} ({up_str})")}
    </div>""", unsafe_allow_html=True)

    # ═══ 10. 지분 구조 ═══
    inst = info.get('heldPercentInstitutions', 0) or 0
    ins = info.get('heldPercentInsiders', 0) or 0
    pub = max(0, 1 - inst - ins)
    s_out = info.get('sharesOutstanding', 0) or 0
    s_flt = info.get('floatShares', 0) or 0

    if   inst > 0.7: v10_c, v10_t = "green",  "✅ 기관 선호 — 높은 기관 보유"
    elif inst > 0.4: v10_c, v10_t = "yellow", "⚠️ 혼합 지분 구조"
    else:            v10_c, v10_t = "red",    "⚠️ 기관 보유 낮음 — 개인 중심"
    all_verdicts.append(("지분구조", v10_c))

    fig10 = _get_plotly_donut(['기관', '내부자', '개인/기타'], [inst, ins, pub], ['#2196F3', '#FF9800', '#4CAF50'])

    col1, col2 = st.columns([1.1, 1])
    with col1:
        st.markdown(f"""
        <div class="s-card">
            <div class="s-title"><span class="s-num">10</span> 이 회사 누가 들고 있나요? <span style="font-size:.75rem;color:#6e7681">Yahoo</span></div>
            {_metric_row("총 발행 주식수", f"{_fmt_num(s_out, False)} 주")}
            {_metric_row("유통 주식수 (Float)", f"{_fmt_num(s_flt, False)} 주")}
            <div class="divider"></div>
            {_metric_row("🏛️ 기관 (연기금·펀드·정부기관 포함)", _fmt_pct(inst))}
            {_metric_row("👔 내부자 (임원·이사회)", _fmt_pct(ins))}
            {_metric_row("👤 개인/기타 (추정)", _fmt_pct(pub))}
            <div class="note-box">※ '기관'에는 정부 연기금, 뮤추얼펀드, ETF, 헤지펀드 포함.<br>※ '개인/기타'는 (100%-기관-내부자) 추정값.</div>
            {_verdict_badge(v10_c, "📌", v10_t)}
        </div>""", unsafe_allow_html=True)
    with col2:
        if fig10:
            st.plotly_chart(fig10, use_container_width=True)
        else:
            st.markdown("<div style='text-align:center;color:#6e7681;padding:100px 0;background:#161A22;border:1px solid #2D333B;border-radius:16px;height:100%;box-sizing:border-box;'>차트 데이터 없음</div>", unsafe_allow_html=True)

    # ═══ 11. 옵션 / Max Pain ═══
    exp, mp, tc, tp, is_vol_weight = _max_pain(tkr)
    mp_val = f"${mp:.2f}" if mp else ""
    mp_html = (f"<span style='font-size:1.3rem;font-weight:800;color:#82aaff'>{mp_val}</span>"
               if mp else "<span style='color:#6e7681'>데이터 없음</span>")
    exp_html = f"<span style='font-size:.78rem;color:#6e7681'>(만기: {exp})</span>" if exp else ""

    mp_note, mp_c = "", "gray"
    if mp and price and price > 0:
        d = ((mp - price) / price) * 100
        if d > 2:
            mp_note = f"Max Pain이 현재가보다 {d:+.1f}% 위 → 만기 시 상승 방향 수렴 가능성"
            mp_c = "green"
        elif d < -2:
            mp_note = f"Max Pain이 현재가보다 {d:+.1f}% 아래 → 만기 시 하락 방향 수렴 가능성"
            mp_c = "red"
        else:
            mp_note = f"현재가와 Max Pain 유사 ({d:+.1f}%) → 현재 가격대 유지 가능성"
            mp_c = "yellow"
    all_verdicts.append(("옵션", mp_c))

    ch = "".join([f"<li>${ci['strike']:.1f} <span style='color:#6e7681'>(Vol {int(ci['volume']):,})</span></li>"
                  for ci in (tc or [])]) or "<li>N/A</li>"
    ph = "".join([f"<li>${pi['strike']:.1f} <span style='color:#6e7681'>(Vol {int(pi['volume']):,})</span></li>"
                  for pi in (tp or [])]) or "<li>N/A</li>"
    mp_badge = f"Max Pain {mp_val} — {mp_note}" if mp else "옵션 데이터 없음"
    vol_warning = ("<div style='color:#FFC107;font-size:0.8rem;margin-top:8px;'>"
                   "⚠️ OI 데이터 부족으로 거래량(Volume) 가중치 사용. 신뢰도 낮을 수 있음.</div>") if is_vol_weight else ""

    st.markdown(f"""
    <div class="s-card">
        <div class="s-title"><span class="s-num">11</span> 시장은 어떤 가격을 보고 있을까요? <span style="font-size:.75rem;color:#6e7681">Yahoo 옵션</span></div>
        <div style="text-align:center;margin:10px 0 16px">
            <div style="font-size:.82rem;color:#8b949e;margin-bottom:4px">Max Pain 가격 {exp_html}</div>
            {mp_html}
            <div style="font-size:.85rem;color:#c9d1d9;margin-top:6px">{mp_note}</div>
            {vol_warning}
        </div>
        <div class="divider"></div>
        <div style="display:flex;gap:16px;flex-wrap:wrap">
            <div class="opt-box" style="flex:1;min-width:220px"><b style="color:#00E676;font-size:.9rem">🟢 Call Top 3</b><ul class="opt-list">{ch}</ul></div>
            <div class="opt-box" style="flex:1;min-width:220px"><b style="color:#FF1744;font-size:.9rem">🔴 Put Top 3</b><ul class="opt-list">{ph}</ul></div>
        </div>
        <div class="note-box" style="margin-top:14px">
            💡 <b>Max Pain 이론</b>: 옵션 만기 시 가장 많은 옵션 매수자(보유자)가 손실을 보는 가격.
            옵션 매도자(마켓메이커)의 이익이 극대화되는 지점으로, 주가가 만기일에 이 가격 부근으로 수렴하는 경향이 있다는 이론입니다.<br>
            ※ 참고 지표이며 항상 수렴하지는 않습니다.
        </div>
        {_verdict_badge(mp_c, "📌", mp_badge)}
    </div>""", unsafe_allow_html=True)

    # ═══ 12. 공매도 ═══
    sp = info.get('shortPercentOfFloat'); ss = info.get('sharesShort', 0) or 0
    sr = info.get('shortRatio'); pss = info.get('sharesShortPriorMonth', 0) or 0

    if isinstance(sp, (int, float)):
        if   sp > 0.20: sl, sc = "매우 높음 🔴 (숏스퀴즈 가능)", "red"
        elif sp > 0.10: sl, sc = "높음 🟠", "red"
        elif sp > 0.05: sl, sc = "보통 🟡", "yellow"
        else:           sl, sc = "낮음 🟢", "green"
    else: sl, sc = "N/A", "gray"
    all_verdicts.append(("공매도", sc))

    short_trend = ""
    if ss > 0 and pss > 0:
        s_chg = ((ss - pss) / pss) * 100
        if   s_chg > 5:  short_trend = f"증가 📈 ({s_chg:+.1f}% vs 전월)"
        elif s_chg < -5: short_trend = f"감소 📉 ({s_chg:+.1f}% vs 전월)"
        else:            short_trend = f"유지 ➡️ ({s_chg:+.1f}% vs 전월)"

    gauge_color = "#FF1744" if (sp or 0) > 0.1 else ("#FFC107" if (sp or 0) > 0.05 else "#00E676")
    fig12 = _get_plotly_gauge(sp or 0, gauge_color)

    col1, col2 = st.columns([1.1, 1])
    with col1:
        st.markdown(f"""
        <div class="s-card">
            <div class="s-title"><span class="s-num">12</span> 공매도 비율 <span style="font-size:.75rem;color:#6e7681">Yahoo</span></div>
            {_metric_row("유통주식 대비 공매도", _fmt_pct(sp), "m-red" if sc == "red" else "m-value")}
            {_metric_row("공매도 수준", sl)}
            {('<div class="m-row"><span class="m-label">전월 대비</span><span class="m-value">' + short_trend + '</span></div>') if short_trend else ''}
            <div class="divider"></div>
            {_metric_row("공매도 주식수", f"{_fmt_num(ss, False)} 주")}
            {_metric_row("숏커버 일수 (DTC)", f"{sr:.2f} 일" if isinstance(sr, (int, float)) else "N/A")}
            <div class="note-box">💡 공매도 &gt; 10% = 높은 숏 관심 / DTC 높으면 숏스퀴즈 ↑<br>※ 약 2주 지연 데이터</div>
            {_verdict_badge(sc, "📌", f"공매도 {_fmt_pct(sp)} — {sl}")}
        </div>""", unsafe_allow_html=True)
    with col2:
        if fig12:
            st.plotly_chart(fig12, use_container_width=True)
        else:
            st.markdown("<div style='text-align:center;color:#6e7681;padding:100px 0;background:#161A22;border:1px solid #2D333B;border-radius:16px;height:100%;box-sizing:border-box;'>차트 데이터 없음</div>", unsafe_allow_html=True)

    # ═══ 13. 뉴스 ═══
    try:
        news_list = tkr.news
        if news_list and len(news_list) > 0:
            items = ""
            for n in news_list[:8]:
                title = n.get('title') or n.get('content', {}).get('title', '제목 없음')
                link = n.get('link') or n.get('content', {}).get('canonicalUrl', {}).get('url', '#')
                pub_name = n.get('publisher') or n.get('content', {}).get('provider', {}).get('displayName', '')
                ts = n.get('providerPublishTime', 0)
                dt_str = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M') if ts else (
                    n.get('content', {}).get('pubDate', '')[:16] if not ts else "")
                items += (f'<div class="n-item"><a href="{_esc(link)}" target="_blank" class="n-title">{_esc(title)}</a>'
                          f'<div class="n-meta">{_esc(pub_name)} · {dt_str}</div></div>')
            st.markdown(f"""<div class="s-card"><div class="s-title"><span class="s-num">13</span> 최신 뉴스 <span style="font-size:.75rem;color:#6e7681">Yahoo Finance</span></div>{items}</div>""", unsafe_allow_html=True)
        else: raise ValueError
    except Exception:
        st.markdown("""<div class="s-card"><div class="s-title"><span class="s-num">13</span> 최신 뉴스</div><div style="color:#6e7681;padding:10px 0">뉴스 데이터를 불러올 수 없습니다.</div></div>""", unsafe_allow_html=True)

    # ═══ 종합 점수 (🔧 개선: 가중치 적용) ═══
    total, mx = 0.0, 0.0
    for name, c in all_verdicts:
        if c != "gray":
            w = WEIGHTS.get(name, 1)
            mx += 2 * w
            if   c == "green":  total += 2 * w
            elif c == "yellow": total += 1 * w
            elif c == "blue":   total += 1.5 * w

    pct = (total / mx * 100) if mx > 0 else 0
    if   pct >= 75: oc, oe, ot = "#00E676", "🟢", "매우 양호"
    elif pct >= 55: oc, oe, ot = "#FFC107", "🟡", "보통"
    elif pct >= 35: oc, oe, ot = "#FF9800", "🟠", "주의 필요"
    else:           oc, oe, ot = "#FF1744", "🔴", "위험"

    dots = _score_dot_row(all_verdicts)
    st.markdown(f"""
    <div class="s-card" style="border-color:{oc};border-width:2px">
        <div class="s-title">📋 종합 분석 요약</div>
        <div style="text-align:center;margin:8px 0 18px">
            <span style="font-size:2.4rem;font-weight:900;color:{oc}">{oe} {pct:.0f}</span>
            <span style="font-size:1.2rem;color:{oc}"> / 100점</span><br>
            <span style="font-size:1.15rem;color:{oc};font-weight:700">{ot}</span>
        </div>
        <div style="background:#21262d;border-radius:10px;height:16px;overflow:hidden;margin:0 40px">
            <div style="width:{pct:.1f}%;height:100%;background:{oc};border-radius:10px;transition:width 1s"></div>
        </div>
        <div style="margin-top:18px">{dots}</div>
        <div class="note-box" style="margin-top:12px;text-align:center">
            핵심 지표(수익성·성장성·재무건전 ×3배)와 보조 지표(거래량·옵션 등 ×1배) 가중치가 적용된 종합 점수. 데이터 누락 항목 제외.
        </div>
    </div>""", unsafe_allow_html=True)

    st.caption("⚠️ 본 분석은 참고용이며 투자 조언이 아닙니다. 투자 결정은 본인의 판단과 책임 하에 이루어져야 합니다.")


# ═══════════════════════════════════════════════════════════════
# ▶️ 실행
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    st.set_page_config(page_title="종목 상세 분석", page_icon="📊", layout="wide")
    st.title("📊 종목 상세 분석 대시보드")
    t = st.text_input("🔍 티커 심볼 입력", value="AAPL", placeholder="예: AAPL, MSFT, GOOGL")
    if t:
        render_company_details(t.strip().upper())