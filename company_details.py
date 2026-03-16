import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import html as html_module
import logging
from datetime import datetime
import plotly.graph_objects as go

# ═══════════════════════════════════════════════════════════════
# 📋 로깅 설정
# ═══════════════════════════════════════════════════════════════
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# 🛠️ API 변동성 대응을 위한 동의어(Alias) 설정
# ═══════════════════════════════════════════════════════════════
REV_ALIASES = ['Total Revenue', 'Operating Revenue', 'Revenue']
NI_ALIASES = [
    'Net Income', 'Net Income Common Stockholders',
    'Net Income Continuous Operations', 'Net Income From Continuing Ops',
    'Net Income Applicable To Common Shares',
    'Net Income Including Noncontrolling Interests',
]
EPS_ALIASES = ['Basic EPS', 'Diluted EPS', 'Earnings Per Share']
BS_ASSETS_ALIASES = ['Total Assets', 'Assets', 'TotalAssets']
BS_LIAB_ALIASES = [
    'Total Liabilities Net Minority Interest', 'Total Liab',
    'Total Liabilities', 'TotalLiabilities',
]
EQ_ALIASES = [
    'Stockholders Equity', 'Total Stockholder Equity',
    'Common Stock Equity', 'Total Equity Gross Minority Interest',
    'Total Equity', 'Net Tangible Assets',
]

# ═══════════════════════════════════════════════════════════════
# 🛠️ 유틸리티 함수
# ═══════════════════════════════════════════════════════════════

def _fmt_num(num, is_currency=True):
    """숫자를 읽기 좋은 형태로 포맷 (T/B/M/K 단위)"""
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
    """소수를 퍼센트 문자열로 변환 (예: 0.15 → '15.00%')"""
    if num is None or (isinstance(num, float) and np.isnan(num)):
        return "N/A"
    if isinstance(num, str):
        return num
    try:
        return f"{float(num) * 100:.2f}%"
    except Exception:
        return "N/A"


def _safe(val, fallback="N/A"):
    """None/NaN을 fallback으로 대체"""
    if val is None:
        return fallback
    if isinstance(val, float) and np.isnan(val):
        return fallback
    return val


def _esc(text):
    """HTML 이스케이프 (XSS 방지)"""
    return html_module.escape(str(text)) if text else ""


def _get_row(df, candidates, latest=True):
    """
    재무제표 DataFrame에서 candidates 행 이름을 찾아 값을 반환.
    latest=True → 가장 최근 컬럼 값, False → 가장 오래된 컬럼 값
    """
    if df is None or df.empty:
        return None
    for name in candidates:
        if name in df.index:
            try:
                row = df.loc[name]
                if isinstance(row, pd.DataFrame):
                    row = row.iloc[0]
                val = row.dropna().sort_index(ascending=not latest)
                if len(val) > 0:
                    return val.iloc[0]
            except Exception as e:
                logger.warning(f"_get_row failed for '{name}': {e}")
    return None


def _get_row_series(df, candidates):
    """재무제표 DataFrame에서 candidates 행 이름의 전체 시계열을 반환"""
    if df is None or df.empty:
        return pd.Series(dtype=float)
    for name in candidates:
        if name in df.index:
            try:
                row = df.loc[name]
                if isinstance(row, pd.DataFrame):
                    row = row.iloc[0]
                return row.dropna().sort_index()
            except Exception as e:
                logger.warning(f"_get_row_series failed for '{name}': {e}")
    return pd.Series(dtype=float)


def _calc_cagr_with_years(financials, row_candidates):
    """
    CAGR 계산: (최신값/과거값)^(1/년수) - 1
    적자 구간에서는 방향성 텍스트 반환
    """
    try:
        rc = row_candidates if isinstance(row_candidates, list) else [row_candidates]
        series = _get_row_series(financials, rc)
        if len(series) >= 2:
            series = series.sort_index()  # 오래된→최신 순
            oldest_val = series.iloc[0]
            newest_val = series.iloc[-1]
            years = len(series) - 1
            if oldest_val > 0 and newest_val > 0:
                return (newest_val / oldest_val) ** (1 / years) - 1, years
            elif oldest_val < 0 and newest_val > 0:
                return "흑자전환 🚀", years
            elif oldest_val > 0 and newest_val < 0:
                return "적자전환 ⚠️", years
            elif oldest_val < 0 and newest_val < 0:
                if newest_val > oldest_val:
                    return "적자축소 📈", years
                else:
                    return "적자지속 📉", years
    except Exception as e:
        logger.warning(f"CAGR calculation failed: {e}")
    return None, 0


def _fmt_cagr(val):
    """CAGR 결과를 포맷 (숫자→%, 문자열→그대로)"""
    if isinstance(val, float):
        return _fmt_pct(val)
    if isinstance(val, str):
        return val
    return "N/A"


def _annual_values(financials, row_candidates):
    """연도별 값을 최신→오래된 순으로 반환"""
    try:
        rc = row_candidates if isinstance(row_candidates, list) else [row_candidates]
        series = _get_row_series(financials, rc)
        if len(series) > 0:
            series = series.sort_index(ascending=False)
            return series.tolist(), series.index.tolist()
    except Exception as e:
        logger.warning(f"_annual_values failed: {e}")
    return [], []


# ── 시각 요소 및 Plotly 차트 생성기 ─────────────────────────────────

def _verdict_badge(color, emoji, text):
    """종합 판정 배지 HTML"""
    bg_map = {
        "green": "rgba(0,230,118,.15)", "red": "rgba(255,23,68,.15)",
        "yellow": "rgba(255,193,7,.15)", "blue": "rgba(33,150,243,.15)",
        "gray": "rgba(96,125,139,.15)",
    }
    bdr_map = {
        "green": "#00E676", "red": "#FF1744", "yellow": "#FFC107",
        "blue": "#2196F3", "gray": "#8b949e",
    }
    bg = bg_map.get(color, bg_map["gray"])
    bdr = bdr_map.get(color, bdr_map["gray"])
    return (
        f'<div style="background:{bg};border:1px solid {bdr};border-radius:12px;'
        f'padding:16px 20px;margin-top:20px;text-align:center;'
        f'box-shadow: 0 4px 12px {bg};">'
        f'<span style="font-size:1.1rem;font-weight:800;'
        f'color:{bdr}">{emoji} {text}</span></div>'
    )


def _metric_row(label, value, value_class="m-value"):
    """지표 한 줄 HTML"""
    return (
        f'<div class="m-row"><span class="m-label">{label}</span>'
        f'<span class="{value_class}">{value}</span></div>'
    )


def _gauge_bar(pct, color="#00E676", height=8):
    """수평 게이지 바 HTML"""
    pct = max(0, min(100, pct))
    return (
        f'<div style="background:rgba(255,255,255,0.1);border-radius:{height}px;'
        f'height:{height}px;overflow:hidden;margin:6px 0">'
        f'<div style="width:{pct:.1f}%;height:100%;background:{color};'
        f'border-radius:{height}px;transition:width .8s"></div></div>'
    )


def _traffic_light(status):
    """신호등 이모지"""
    return {"green": "🟢", "yellow": "🟡", "red": "🔴", "blue": "🔵", "gray": "⚪"}.get(status, "⚪")


def _score_dot_row(items):
    """종합 스코어보드의 점 행 HTML"""
    cells = ""
    for name, color in items:
        dot = _traffic_light(color)
        cells += (
            f'<div style="display:inline-flex;flex-direction:column;align-items:center;'
            f'min-width:60px;padding:6px 4px">'
            f'<span style="font-size:1.2rem">{dot}</span>'
            f'<span style="font-size:.75rem;font-weight:700;color:#c9d1d9;margin-top:4px;'
            f'text-align:center;line-height:1.2">{name}</span></div>'
        )
    return f'<div style="display:flex;flex-wrap:wrap;justify-content:center;gap:4px;margin:12px 0">{cells}</div>'


def _get_plotly_combo_chart(rev_vals, ni_vals, rev_dates):
    """매출(바) + 순이익(라인) 콤보 차트"""
    if not rev_vals or not rev_dates or len(rev_vals) < 2:
        return None
    dates_rev = rev_dates[::-1]
    rv_rev = rev_vals[::-1]
    nv_rev = ni_vals[::-1]
    labels = [d.strftime('%Y') if hasattr(d, 'strftime') else str(d)[:4] for d in dates_rev]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=labels, y=rv_rev, name='매출', marker_color='#2196F3', opacity=0.9,
        text=[_fmt_num(v, False) for v in rv_rev], textposition='auto',
        textfont=dict(color='white', size=13, weight='bold'),
    ))
    fig.add_trace(go.Scatter(
        x=labels, y=nv_rev, name='순이익', mode='lines+markers+text',
        line=dict(color='#00E676', width=4),
        marker=dict(size=10, color='white', line=dict(color='#00E676', width=2)),
        yaxis='y2',
        text=[_fmt_num(v, False) for v in nv_rev], textposition='top center',
        textfont=dict(color='#00E676', size=13, weight='bold'),
    ))

    fig.update_layout(
        title=dict(text="<b>📊 연도별 재무 추이</b>", font=dict(size=16, color='white', family="Arial")),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white', size=13, weight='bold'),
        margin=dict(l=10, r=10, t=40, b=10), height=320,
        xaxis=dict(showgrid=False, tickfont=dict(color='white')),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.15)', zeroline=False, tickfont=dict(color='white')),
        yaxis2=dict(overlaying='y', side='right', showgrid=False, tickfont=dict(color='#00E676')),
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1),
    )
    return fig


def _get_plotly_yearly_bar(dates, y1_vals, y2_vals, name1, name2, color1, color2):
    """연도별 2계열 그룹 바 차트"""
    if not dates or not y1_vals or len(y1_vals) < 2:
        return None
    labels = [d.strftime('%Y') if hasattr(d, 'strftime') else str(d)[:4] for d in dates[::-1]]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=labels, y=y1_vals[::-1], name=name1, marker_color=color1, opacity=0.9,
        text=[_fmt_num(v, False) for v in y1_vals[::-1]], textposition='auto',
        textfont=dict(color='white', size=13, weight='bold'),
    ))
    fig.add_trace(go.Bar(
        x=labels, y=y2_vals[::-1], name=name2, marker_color=color2, opacity=0.9,
        text=[_fmt_num(v, False) for v in y2_vals[::-1]], textposition='auto',
        textfont=dict(color='white', size=13, weight='bold'),
    ))
    fig.update_layout(
        title=dict(text="<b>📊 연도별 자산/부채 추이</b>", font=dict(size=16, color='white', family="Arial")),
        barmode='group', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white', size=13, weight='bold'),
        margin=dict(l=10, r=10, t=40, b=10), height=320,
        xaxis=dict(showgrid=False, tickfont=dict(color='white')),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.15)', zeroline=False, tickfont=dict(color='white')),
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1),
    )
    return fig


def _get_plotly_target_price(curr, low, mean, median, high):
    """목표가 범위 시각화"""
    if not low or not high:
        return None
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[low, high], y=[0, 0], mode='lines',
        line=dict(color='#768390', width=6), showlegend=False, hoverinfo='skip',
    ))

    points = [
        (low, '최저가', '#adbac7', 12, 'bottom center'),
        (high, '최고가', '#adbac7', 12, 'bottom center'),
        (mean, '평균', '#2196F3', 14, 'bottom center'),
        (median, '중앙값', '#00E676', 16, 'top center'),
        (curr, '현재가', '#FF9800', 22, 'top center'),
    ]

    for val, name, color, size, pos in points:
        if val:
            fig.add_trace(go.Scatter(
                x=[val], y=[0], mode='markers+text',
                marker=dict(
                    color=color, size=size,
                    symbol='star' if name == '현재가' else 'circle',
                    line=dict(width=2 if name == '현재가' else 1, color='white'),
                ),
                text=[f"<b>{name}</b><br>${val:,.2f}"],
                textposition=pos,
                textfont=dict(
                    color=color if name in ['현재가', '중앙값'] else 'white',
                    size=13, weight='bold',
                ),
                name=name,
            ))

    fig.update_layout(
        title=dict(text="<b>📊 목표가 범위 및 현재가 위치</b>", font=dict(size=16, color='white', family="Arial")),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white', size=13, weight='bold'),
        height=260, margin=dict(l=20, r=20, t=50, b=20),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-1.2, 1.2]),
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5, font=dict(color='white')),
    )
    return fig


def _get_plotly_donut(labels, values, colors):
    """도넛 차트"""
    if sum(values) == 0:
        return None
    fig = go.Figure(data=[go.Pie(
        labels=labels, values=values, hole=.55, marker_colors=colors,
        textinfo='label+percent',
        textfont=dict(color='white', size=14, weight='bold'),
        hoverinfo='label+percent',
    )])
    fig.update_layout(
        title=dict(text="<b>📊 지분 구성 비율</b>", font=dict(size=16, color='white', family="Arial")),
        margin=dict(t=50, b=10, l=10, r=10),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white', size=13, weight='bold'),
        showlegend=False, height=280,
    )
    return fig


def _get_plotly_gauge(val, color):
    """공매도 비율 게이지"""
    val_pct = val * 100
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=val_pct,
        number={'suffix': "%", 'font': {'size': 32, 'color': color, 'weight': 'bold'}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 2, 'tickcolor': "white"},
            'bar': {'color': color, 'thickness': 0.8},
            'bgcolor': "rgba(255,255,255,0.1)", 'borderwidth': 0,
            'steps': [
                {'range': [0, 10], 'color': 'rgba(0,230,118,0.2)'},
                {'range': [10, 20], 'color': 'rgba(255,193,7,0.2)'},
                {'range': [20, 100], 'color': 'rgba(255,23,68,0.2)'},
            ],
        },
    ))
    fig.update_layout(
        title=dict(text="<b>📊 공매도 비율 (100% 기준)</b>", font=dict(size=16, color='white', family="Arial")),
        paper_bgcolor='rgba(0,0,0,0)', font=dict(color='white', weight='bold'),
        margin=dict(l=20, r=20, t=50, b=20), height=280,
    )
    return fig


# ── 분석 함수들 ─────────────────────────────────────────

def _growth_stage(info, fin, bs, cf):
    """기업 성장 단계 판별 (1~8단계)"""
    rev_growth = info.get('revenueGrowth', 0) or 0
    margin = info.get('profitMargins', 0) or 0
    revenue = info.get('totalRevenue', 0) or 0
    div_yield = info.get('dividendYield', 0) or 0

    operating_cf = 0
    try:
        if cf is not None:
            for name in ['Operating Cash Flow', 'Total Cash From Operating Activities']:
                if name in cf.index:
                    operating_cf = cf.loc[name].dropna().iloc[0] or 0
                    break
    except Exception as e:
        logger.debug(f"Operating CF extraction failed: {e}")

    rev_declining = False
    try:
        rev_series = _get_row_series(fin, REV_ALIASES)
        if len(rev_series) >= 3:
            rev_desc = rev_series.sort_index(ascending=False)
            decline_count = sum(1 for i in range(len(rev_desc) - 1) if rev_desc.iloc[i] < rev_desc.iloc[i + 1])
            if decline_count >= 2:
                rev_declining = True
    except Exception as e:
        logger.debug(f"Revenue decline check failed: {e}")

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
    colors = {
        1: "#9C27B0", 2: "#FF5722", 3: "#FF9800", 4: "#4CAF50",
        5: "#2196F3", 6: "#607D8B", 7: "#F44336", 8: "#795548",
    }

    # 단계 판별 로직
    if revenue < 1e8 and margin < -0.20:
        stage = 1
    elif rev_growth > 0.30 and margin < 0:
        stage = 2
    elif rev_growth > 0.20 and margin > 0:
        stage = 3
    elif rev_growth > 0.05 and margin > 0.10:
        stage = 4
    elif 0 <= rev_growth <= 0.05 and margin > 0.10 and (div_yield > 0.01 or operating_cf > revenue * 0.1):
        stage = 5
    elif -0.05 <= rev_growth <= 0.02 and margin > 0:
        stage = 6
    elif rev_declining and margin < 0:
        stage = 7
    elif rev_growth < -0.05 and margin <= 0:
        stage = 8
    elif rev_growth < 0 and margin <= 0:
        stage = 8
    elif rev_growth > 0.30:
        stage = 2
    elif margin > 0.15 and rev_growth > 0.05:
        stage = 4
    elif margin > 0.15:
        stage = 5
    elif margin > 0:
        stage = 6
    elif margin < -0.10:
        stage = 8
    else:
        stage = 6

    return stage, stages[stage][0], stages[stage][1], colors[stage]


def _stability(financials, row_candidates):
    """수익 안정성 (변동계수 CV 기반)"""
    vals, _ = _annual_values(financials, row_candidates)
    arr = np.array([v for v in vals if v is not None and not np.isnan(v)])
    if len(arr) < 2 or np.mean(arr) == 0:
        return "데이터 부족", "", "gray"
    cv = np.std(arr) / abs(np.mean(arr))
    if   cv < 0.10: return "매우 안정적 ✅", f"CV {cv:.3f}", "green"
    elif cv < 0.25: return "안정적 ✅",      f"CV {cv:.3f}", "green"
    elif cv < 0.50: return "보통 ⚠️",        f"CV {cv:.3f}", "yellow"
    else:           return "불안정 ❌",       f"CV {cv:.3f}", "red"


def _margin_trend(fin):
    """이익률 추이 분석"""
    try:
        rev_series = _get_row_series(fin, REV_ALIASES)
        ni_series = _get_row_series(fin, NI_ALIASES)
        common_idx = rev_series.index.intersection(ni_series.index).sort_values()
        margins = [(i, ni_series[i] / rev_series[i]) for i in common_idx if rev_series[i] != 0]
        if len(margins) < 2:
            return "N/A", [], "gray"
        first_margin = margins[0][1]
        last_margin = margins[-1][1]
        if last_margin > first_margin + 0.02:
            return f"증가 추세 📈 ({first_margin * 100:.1f}% → {last_margin * 100:.1f}%)", margins, "green"
        if last_margin < first_margin - 0.02:
            return f"감소 추세 📉 ({first_margin * 100:.1f}% → {last_margin * 100:.1f}%)", margins, "red"
        return f"유지 ➡️ ({last_margin * 100:.1f}%)", margins, "yellow"
    except Exception as e:
        logger.warning(f"Margin trend analysis failed: {e}")
        return "N/A", [], "gray"


def _growth_accel(fin, row_candidates):
    """성장 가속/감속 판단 (최소 3개년 필요, 2개년이면 비교 불가 처리)"""
    vals, _ = _annual_values(fin, row_candidates)
    if len(vals) < 3:
        return "데이터 부족 (3개년 이상 필요)", "gray"
    growth_rates = []
    for i in range(len(vals) - 1):
        if vals[i + 1] and vals[i + 1] != 0:
            growth_rates.append((vals[i] - vals[i + 1]) / abs(vals[i + 1]))
    if len(growth_rates) < 2:
        return "계산 불가", "gray"

    recent = growth_rates[0]
    past_avg = np.mean(growth_rates[1:4]) if len(growth_rates) > 2 else growth_rates[1]
    data_note = f"(기반: {len(growth_rates)}개년)"

    if recent > past_avg + 0.05:
        return f"가속화 🚀 (최근 {recent * 100:.1f}% vs 과거 {past_avg * 100:.1f}%) {data_note}", "green"
    elif recent < past_avg - 0.05:
        return f"감속 🐌 (최근 {recent * 100:.1f}% vs 과거 {past_avg * 100:.1f}%) {data_note}", "yellow"
    return f"유지 ➡️ (최근 {recent * 100:.1f}% vs 과거 {past_avg * 100:.1f}%) {data_note}", "green"


def _debt_trend(bs):
    """부채 추이 분석"""
    for name_candidates in [BS_LIAB_ALIASES, ['Long Term Debt'], ['Total Debt']]:
        series = _get_row_series(bs, name_candidates)
        if len(series) >= 2:
            series = series.sort_index(ascending=False)
            latest, oldest = series.iloc[0], series.iloc[-1]
            if oldest != 0:
                chg = (latest - oldest) / abs(oldest)
                if   chg < -0.10: return f"감소 추세 ✅ ({chg * 100:.1f}%)", "green"
                elif chg >  0.10: return f"증가 추세 ⚠️ (+{chg * 100:.1f}%)", "red"
                else:             return f"안정 유지 ➡️ ({chg * 100:.1f}%)", "yellow"
    return "데이터 부족", "gray"


def _interest_burden(fin, info):
    """이자 부담 분석 (ICR 기반)"""
    ebit = _get_row(fin, ['EBIT', 'Operating Income'], latest=True)
    interest = _get_row(fin, ['Interest Expense', 'Interest Expense Non Operating'], latest=True)

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
    if ebitda and debt > 0:
        if ebitda < 0:
            return "위험 ❌ (EBITDA 적자)", "red"
        est_rate = 0.05
        coverage = ebitda / (debt * est_rate)
        src = f"추정, 이자율 {est_rate * 100:.0f}% 가정"
        if   coverage > 10: return f"매우 낮음 ✅ ({coverage:.1f}x, {src})", "green"
        elif coverage >  5: return f"낮음 ✅ ({coverage:.1f}x, {src})", "green"
        elif coverage >  2: return f"보통 ⚠️ ({coverage:.1f}x, {src})", "yellow"
        else:               return f"높음 ❌ ({coverage:.1f}x, {src})", "red"
    return "N/A", "gray"


def _vol_trend(info):
    """거래량 추이 분석"""
    vol = info.get('volume', 0) or 0
    avg3m = info.get('averageVolume', 0) or 0
    if avg3m == 0:
        return "데이터 부족", "gray"
    ratio = vol / avg3m
    if   ratio > 1.5: return f"급증 🔥 ({ratio:.1f}배)", "yellow"
    elif ratio > 1.1: return f"증가 📈 ({ratio:.1f}배)", "yellow"
    elif ratio > 0.9: return f"평균 수준 ➡️ ({ratio:.1f}배)", "green"
    elif ratio > 0.5: return f"감소 📉 ({ratio:.1f}배)", "yellow"
    else:             return f"급감 ⚠️ ({ratio:.1f}배)", "red"


def _max_pain(tkr):
    """Max Pain 가격 계산 (OI 우선, 부족 시 Volume 가중치)"""
    try:
        dates = tkr.options
        if not dates:
            return None, None, None, None, False
        exp = dates[0]
        chain = tkr.option_chain(exp)
        calls, puts = chain.calls.copy(), chain.puts.copy()

        for col in ['openInterest', 'volume']:
            if col not in calls.columns:
                calls[col] = 0
            if col not in puts.columns:
                puts[col] = 0
            calls[col] = calls[col].fillna(0)
            puts[col] = puts[col].fillna(0)

        call_oi_sum = calls['openInterest'].sum()
        put_oi_sum = puts['openInterest'].sum()

        is_vol_weight = False

        if (call_oi_sum == 0 or put_oi_sum == 0
                or (call_oi_sum / max(put_oi_sum, 1) < 0.02)
                or (put_oi_sum / max(call_oi_sum, 1) < 0.02)):
            weight_c = calls['volume']
            weight_p = puts['volume']
            is_vol_weight = True
            if weight_c.sum() == 0 and weight_p.sum() == 0:
                return exp, None, [], [], False
        else:
            weight_c = calls['openInterest']
            weight_p = puts['openInterest']

        strikes = sorted(set(calls['strike']).union(set(puts['strike'])))
        pain = {}
        for s in strikes:
            pain[s] = (
                np.sum(weight_c * np.maximum(0, s - calls['strike']))
                + np.sum(weight_p * np.maximum(0, puts['strike'] - s))
            )

        if not pain or max(pain.values()) == 0:
            max_pain_price = None
        else:
            max_pain_price = min(pain, key=pain.get)

        top_calls = calls.nlargest(3, 'volume')[['strike', 'volume']].to_dict('records')
        top_puts = puts.nlargest(3, 'volume')[['strike', 'volume']].to_dict('records')
        return exp, max_pain_price, top_calls, top_puts, is_vol_weight
    except Exception as e:
        logger.warning(f"Max Pain calculation failed: {e}")
        return None, None, None, None, False


@st.cache_data(ttl=3600, show_spinner=False)
def _sector_pe_cached(sector):
    """섹터 P/E를 ETF 기반으로 조회 (1시간 캐싱)"""
    etf_map = {
        "Technology": "XLK", "Financial Services": "XLF",
        "Healthcare": "XLV", "Energy": "XLE",
        "Consumer Cyclical": "XLY", "Consumer Defensive": "XLP",
        "Industrials": "XLI", "Communication Services": "XLC",
        "Utilities": "XLU", "Real Estate": "XLRE", "Basic Materials": "XLB",
    }
    etf = etf_map.get(sector)

    if etf:
        try:
            pe = yf.Ticker(etf).info.get('trailingPE')
            if pe and isinstance(pe, (int, float)) and pe > 0:
                return pe, "실시간"
        except Exception as e:
            logger.warning(f"Sector PE fetch failed for {etf}: {e}")

    fallback_map = {
        "Technology": 30, "Communication Services": 22, "Consumer Cyclical": 25,
        "Consumer Defensive": 22, "Financial Services": 14, "Healthcare": 22,
        "Industrials": 20, "Energy": 12, "Basic Materials": 15,
        "Real Estate": 35, "Utilities": 18,
    }
    fb = fallback_map.get(sector)
    return (fb, "추정치") if fb else (None, "")


def _cross_validate_pe(price, trailing_eps, forward_eps, info_trailing_pe, info_forward_pe):
    """
    P/E 교차 검증: info에서 받은 P/E와 직접 계산한 P/E를 비교.
    큰 괴리가 있으면 직접 계산값 우선 사용 + 경고 반환.
    """
    warnings = []
    validated_tpe = info_trailing_pe
    validated_fpe = info_forward_pe

    # Trailing P/E 검증
    if price and trailing_eps and trailing_eps > 0:
        calc_tpe = price / trailing_eps
        if info_trailing_pe and abs(calc_tpe - info_trailing_pe) / calc_tpe > 0.15:
            warnings.append(
                f"Trailing P/E: API값({info_trailing_pe:.2f}) vs 계산값({calc_tpe:.2f}) — 계산값 사용"
            )
            validated_tpe = calc_tpe
        elif info_trailing_pe is None or pd.isna(info_trailing_pe):
            validated_tpe = calc_tpe

    # Forward P/E 검증
    if price and forward_eps and forward_eps > 0:
        calc_fpe = price / forward_eps
        if info_forward_pe and abs(calc_fpe - info_forward_pe) / calc_fpe > 0.15:
            warnings.append(
                f"Forward P/E: API값({info_forward_pe:.2f}) vs 계산값({calc_fpe:.2f}) — 계산값 사용"
            )
            validated_fpe = calc_fpe
        elif info_forward_pe is None or pd.isna(info_forward_pe):
            validated_fpe = calc_fpe

    return validated_tpe, validated_fpe, warnings


# ═══════════════════════════════════════════════════════════════
# 🎨 CSS
# ═══════════════════════════════════════════════════════════════

CSS = """
<style>
[data-testid="stVerticalBlockBorderWrapper"] {
    background: #1e252c !important;
    border: 2px solid #535e6b !important;
    border-radius: 16px !important;
    box-shadow: 0 8px 32px rgba(0,0,0,0.6) !important;
    transition: all .3s;
    max-width: 960px;
    margin-left: auto;
    margin-right: auto;
    margin-bottom: 35px !important;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
    transform: translateY(-3px);
    border-color: #82aaff !important;
    box-shadow: 0 12px 40px rgba(130, 170, 255, 0.2) !important;
}
[data-testid="stVerticalBlockBorderWrapper"] > div {
    padding: 24px 28px !important;
}
.s-title{
    font-size:1.25rem;font-weight:800;color:#82aaff;
    margin-bottom:24px;padding-bottom:12px;
    border-bottom:2px solid #3b424a;
    display:flex;align-items:center;gap:12px}
.s-title .s-num{
    background:#3b424a;border-radius:8px;padding:4px 10px;
    font-size:.85rem;color:#82aaff;font-weight:900}
.m-row{display:flex;justify-content:space-between;
    padding:10px 0;font-size:.95rem;align-items:center;
    border-bottom:1px solid rgba(83,94,107,.3)}
.m-row:last-child{border-bottom:none}
.m-label{color:#adbac7;font-weight:600}
.m-value{color:#ffffff;font-weight:800;text-align:right;max-width:55%}
.m-green{color:#00E676 !important;font-weight:800}
.m-red{color:#FF1744 !important;font-weight:800}
.m-yellow{color:#FFC107 !important;font-weight:800}
.m-blue{color:#448aff !important;font-weight:800}
.m-big{font-size:1.15rem;font-weight:900}
.divider{border-top:1px dashed #535e6b;margin:20px 0}
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:20px}
@media(max-width:640px){.two-col{grid-template-columns:1fr}}
.opt-box{background:rgba(0,0,0,.3);padding:16px;border-radius:12px;border:1px solid #535e6b}
.opt-list{margin:8px 0 0;padding-left:18px;font-size:.9rem;color:#ffffff;line-height:2.0;font-weight:600}
.m-table{width:100%;border-collapse:collapse;font-size:.9rem;margin-top:8px}
.m-table th{color:#adbac7;text-align:left;padding:10px;border-bottom:2px solid #535e6b;font-weight:700}
.m-table td{color:#ffffff;padding:10px;border-bottom:1px solid #3b424a;font-weight:600}
.n-item{padding:14px 0;border-bottom:1px solid #3b424a}
.n-item:last-child{border-bottom:none}
.n-title{color:#82aaff;font-weight:700;font-size:1rem;text-decoration:none}
.n-title:hover{text-decoration:underline;color:#a8c7ff}
.n-meta{color:#8b949e;font-size:.8rem;margin-top:6px;font-weight:600}
.header-wrap{display:flex;justify-content:space-between;align-items:flex-end;
    flex-wrap:wrap;gap:12px;max-width:960px;margin:0 auto 16px}
.note-box{font-size:.85rem;color:#adbac7;line-height:1.6;font-weight:600;
    padding:12px;background:rgba(0,0,0,.25);border-radius:8px;margin-top:12px;border-left:4px solid #82aaff}
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
            logger.error(f"Ticker fetch failed for {ticker_str}: {e}")
            return

        if not info or 'shortName' not in info:
            st.error("❌ 유효하지 않은 종목이거나 데이터가 없습니다.")
            return

        # ── 재무제표 로드 (fallback 포함) ──
        fin = None
        try:
            fin = tkr.financials
            if fin is None or fin.empty:
                fin = tkr.income_stmt
            if fin is None or fin.empty:
                logger.warning(f"{ticker_str}: 연간 재무제표(financials/income_stmt) 모두 비어있음")
        except Exception as e:
            logger.warning(f"Financials load failed: {e}")

        q_fin = None
        try:
            q_fin = tkr.quarterly_financials
            if q_fin is None or q_fin.empty:
                q_fin = tkr.quarterly_income_stmt
            if q_fin is None or q_fin.empty:
                logger.warning(f"{ticker_str}: 분기 재무제표 비어있음")
        except Exception as e:
            logger.warning(f"Quarterly financials load failed: {e}")

        bs = None
        try:
            bs = tkr.balance_sheet
        except Exception as e:
            logger.warning(f"Balance sheet load failed: {e}")

        cf = None
        try:
            cf = tkr.cashflow
        except Exception as e:
            logger.warning(f"Cashflow load failed: {e}")

        sector = info.get('sector', 'N/A')
        industry = info.get('industry', 'N/A')
        price = info.get('currentPrice') or info.get('regularMarketPrice') or 0
        prev_close = info.get('previousClose') or price or 1
        day_change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0
        change_color = "#00E676" if day_change_pct >= 0 else "#FF1744"
        change_sign = "+" if day_change_pct >= 0 else ""

        if price == 0:
            st.warning("⚠️ 현재가를 불러올 수 없습니다. 일부 데이터가 정확하지 않을 수 있습니다.")

        cagr_rev, yr_rev = _calc_cagr_with_years(fin, REV_ALIASES)
        cagr_ni, yr_ni = _calc_cagr_with_years(fin, NI_ALIASES)
        cagr_eps, yr_eps = _calc_cagr_with_years(fin, EPS_ALIASES)

        ann_rev_growth = "N/A"
        try:
            rv_ann, _ = _annual_values(fin, REV_ALIASES)
            if len(rv_ann) >= 2 and rv_ann[1] and rv_ann[1] > 0:
                ann_rev_growth = (rv_ann[0] / rv_ann[1]) - 1
        except Exception as e:
            logger.debug(f"Annual revenue growth calc failed: {e}")

        qoq_rev_growth = "N/A"
        yoy_q_rev_growth = info.get('revenueGrowth')
        try:
            q_rev_series = _get_row_series(q_fin, REV_ALIASES).sort_index(ascending=False)
            if len(q_rev_series) >= 2 and q_rev_series.iloc[1] > 0:
                qoq_rev_growth = (q_rev_series.iloc[0] / q_rev_series.iloc[1]) - 1
            if len(q_rev_series) >= 5 and q_rev_series.iloc[4] > 0:
                yoy_q_rev_growth = (q_rev_series.iloc[0] / q_rev_series.iloc[4]) - 1
        except Exception as e:
            logger.debug(f"Quarterly revenue growth calc failed: {e}")

    # ═══════════════════════════════════════════════════
    # 🏷️ 헤더
    # ═══════════════════════════════════════════════════
    name_safe = _esc(info.get('shortName', ticker_str))
    st.markdown(f"""
    <div class="header-wrap">
        <div>
            <span style="font-size:1.8rem;font-weight:900;color:#ffffff">🏢 {name_safe}</span>
            <span style="font-size:1.1rem;color:#adbac7;margin-left:8px;font-weight:800">({_esc(ticker_str)})</span><br>
            <span style="font-size:.9rem;color:#8b949e;font-weight:700">{_esc(sector)} · {_esc(industry)}</span>
        </div>
        <div style="text-align:right">
            <span style="font-size:2.2rem;font-weight:900;color:{change_color}">${price:,.2f}</span><br>
            <span style="font-size:1.1rem;font-weight:800;color:{change_color}">{change_sign}{day_change_pct:.2f}% 오늘</span>
        </div>
    </div>""", unsafe_allow_html=True)

    all_verdicts = []

    # ═══════════════════════════════════════════════════
    # 1️⃣ 성장 사이클
    # ═══════════════════════════════════════════════════
    stage_num, stage_name, stage_desc, stage_color = _growth_stage(info, fin, bs, cf)
    stage_color_map = {
        1: "#9C27B0", 2: "#FF5722", 3: "#FF9800", 4: "#4CAF50",
        5: "#2196F3", 6: "#607D8B", 7: "#F44336", 8: "#795548",
    }
    stage_label_map = {
        1: "스타트업", 2: "초기성장", 3: "고성장", 4: "성숙성장",
        5: "캐시카우", 6: "정체", 7: "쇠퇴", 8: "턴어라운드",
    }

    bar_html = ""
    for i in range(1, 9):
        is_current = (i == stage_num)
        bg = stage_color_map[i] if is_current else "rgba(0,0,0,0.2)"
        opacity = "1" if is_current else "0.4"
        fw = "800" if is_current else "600"
        border = f"3px solid {stage_color_map[i]}" if is_current else "1px solid #444c56"
        radius = "10px 0 0 10px" if i == 1 else ("0 10px 10px 0" if i == 8 else "0")
        shadow = f"0 0 16px {stage_color_map[i]}88" if is_current else "none"
        bar_html += (
            f'<div style="flex:1;background:{bg};opacity:{opacity};text-align:center;'
            f'padding:14px 2px;font-size:.7rem;color:#ffffff;border:{border};'
            f'border-radius:{radius};font-weight:{fw};box-shadow:{shadow};'
            f'transition:all .3s">{i}<br>{stage_label_map[i]}</div>'
        )

    v1_color = "green" if stage_num in [3, 4] else ("blue" if stage_num == 5 else ("yellow" if stage_num in [1, 2, 6] else "red"))
    v1_text_map = {
        1: "초기 — 높은 리스크·높은 잠재력",
        2: "폭풍 성장 중 — 적자이지만 매출 급증",
        3: "성장+이익 = 최적 타이밍 가능",
        4: "안정 성장 우량주 — 핵심 보유 후보",
        5: "현금 창출 극대화 — 배당·안정성",
        6: "새 성장 동력 필요",
        7: "위험 — 구조적 하락 주의",
        8: "턴어라운드 성공 여부가 핵심",
    }
    all_verdicts.append(("성장사이클", v1_color))

    with st.container(border=True):
        st.markdown(f"""
        <div class="s-title"><span class="s-num">01</span> 이 회사, 지금 어느 단계인가요?</div>
        <div style="display:flex;gap:3px;margin-bottom:24px">{bar_html}</div>
        <div style="text-align:center;margin:20px 0">
            <span style="display:inline-block;padding:12px 32px;border-radius:24px;
                         font-weight:800;background:{stage_color};color:#fff;font-size:1.2rem;
                         box-shadow:0 6px 20px {stage_color}66">{stage_name}</span>
            <div style="font-size:1rem;color:#e6edf3;font-weight:700;margin-top:16px;line-height:1.7">{stage_desc}</div>
        </div>
        <div class="divider"></div>
        <div class="two-col">
            <div>
                {_metric_row("최근 연간 매출성장 (YoY)", _fmt_pct(ann_rev_growth))}
                {_metric_row("최근 분기 매출성장 (YoY)", _fmt_pct(yoy_q_rev_growth))}
                {_metric_row("직전 분기 대비 성장 (QoQ)", _fmt_pct(qoq_rev_growth))}
            </div>
            <div>
                {_metric_row("순이익률", _fmt_pct(info.get('profitMargins')))}
                {_metric_row("ROE", _fmt_pct(info.get('returnOnEquity')))}
                {_metric_row("배당수익률", _fmt_pct(info.get('dividendYield')))}
            </div>
        </div>
        {_verdict_badge(v1_color, "📌", f"종합: {v1_text_map.get(stage_num, '')}")}
        """, unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════
    # 2️⃣ 돈을 잘 버는 회사인가요?
    # ═══════════════════════════════════════════════════
    gross_margin = info.get('grossMargins')
    net_margin = info.get('profitMargins')
    market_cap = info.get('marketCap')
    ttm_eps = info.get('trailingEps')
    ttm_revenue = info.get('totalRevenue')
    ttm_net_income = info.get('netIncomeToCommon')

    profit_score = sum(1 for x in [
        gross_margin and gross_margin > 0.4,
        net_margin and net_margin > 0.1,
        cagr_rev and isinstance(cagr_rev, float) and cagr_rev > 0.05,
        cagr_ni and isinstance(cagr_ni, float) and cagr_ni > 0.05,
        ttm_net_income and ttm_net_income > 0,
    ] if x)

    if   profit_score >= 4: v2_color, v2_text = "green",  "💰 매우 우수 — 높은 마진 + 지속 성장"
    elif profit_score >= 3: v2_color, v2_text = "green",  "✅ 양호 — 수익성과 성장 겸비"
    elif profit_score >= 2: v2_color, v2_text = "yellow", "⚠️ 보통 — 일부 지표 개선 필요"
    else:                   v2_color, v2_text = "red",    "❌ 수익성 미흡 — 적자 또는 마진 악화"
    all_verdicts.append(("수익성", v2_color))

    ni_css_class = "m-green" if ttm_net_income and ttm_net_income > 0 else "m-red"
    cagr_css = lambda v: "m-green" if (isinstance(v, float) and v > 0) or "전환" in str(v) else "m-red"

    gm_pct = (gross_margin or 0) * 100
    nm_pct = (net_margin or 0) * 100
    gm_gauge = _gauge_bar(max(0, gm_pct), "#4CAF50", 10)
    nm_gauge = _gauge_bar(max(0, nm_pct), "#2196F3", 10)

    rev_label = f"{yr_rev}년 매출 평균성장" if yr_rev else "매출 성장추세"
    ni_label = f"{yr_ni}년 순이익 평균성장" if yr_ni else "순이익 추세"
    eps_label = f"{yr_eps}년 EPS 평균성장" if yr_eps else "EPS 추세"

    with st.container(border=True):
        st.markdown(f"""
        <div class="s-title"><span class="s-num">02</span> 돈을 잘 버는 회사인가요? <span style="font-size:.8rem;color:#768390">SEC 데이터</span></div>
        <div class="two-col">
            <div>
                {_metric_row("시가총액", _fmt_num(market_cap), "m-value m-big")}
                {_metric_row("TTM EPS (주당순이익)", _fmt_num(ttm_eps))}
                {_metric_row("최근 12개월 매출", _fmt_num(ttm_revenue))}
                {_metric_row("최근 12개월 순이익", _fmt_num(ttm_net_income), ni_css_class)}
            </div>
            <div>
                <div style="margin-bottom:16px">
                    <div style="display:flex;justify-content:space-between;font-size:.95rem">
                        <span style="color:#adbac7;font-weight:700">총이익률 (Gross)</span>
                        <span style="color:#ffffff;font-weight:800">{_fmt_pct(gross_margin)}</span>
                    </div>{gm_gauge}
                </div>
                <div style="margin-bottom:16px">
                    <div style="display:flex;justify-content:space-between;font-size:.95rem">
                        <span style="color:#adbac7;font-weight:700">순이익률 (Net)</span>
                        <span style="color:#ffffff;font-weight:800">{_fmt_pct(net_margin)}</span>
                    </div>{nm_gauge}
                </div>
            </div>
        </div>
        <div class="divider"></div>
        <div class="two-col">
            <div>
                {_metric_row(rev_label, _fmt_cagr(cagr_rev), cagr_css(cagr_rev))}
                {_metric_row(ni_label, _fmt_cagr(cagr_ni), cagr_css(cagr_ni))}
            </div>
            <div>
                {_metric_row(eps_label, _fmt_cagr(cagr_eps), cagr_css(cagr_eps))}
                <div class="note-box">※ 이익이 적자(-)에서 시작된 경우 수학적 한계로 비율(%) 대신 방향성 텍스트로 대체 표기합니다.</div>
            </div>
        </div>
        {_verdict_badge(v2_color, "📌", v2_text)}
        """, unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════
    # 3️⃣ 지금까지 성적
    # ═══════════════════════════════════════════════════
    rev_stability, rev_cv, stability_color = _stability(fin, REV_ALIASES)
    margin_trend_text, _, margin_trend_color = _margin_trend(fin)
    accel_text, accel_color = _growth_accel(fin, REV_ALIASES)

    roe_val = info.get('returnOnEquity')
    roe_display = f"{_fmt_pct(roe_val)}" if roe_val else "N/A"
    roe_color = "green" if roe_val and roe_val > 0.1 else ("yellow" if roe_val and roe_val > 0 else "red")

    rev_vals, rev_dates = _annual_values(fin, REV_ALIASES)
    ni_vals, ni_dates = _annual_values(fin, NI_ALIASES)

    tbl_rows = ""
    for i in range(min(len(rev_vals), len(ni_vals), 4)):
        yr = rev_dates[i].strftime('%Y') if hasattr(rev_dates[i], 'strftime') else str(rev_dates[i])[:4]
        margin_pct = (ni_vals[i] / rev_vals[i] * 100) if rev_vals[i] and rev_vals[i] != 0 else 0
        ni_color = "#00E676" if ni_vals[i] and ni_vals[i] > 0 else "#FF1744"
        mg_color = "#00E676" if margin_pct > 0 else "#FF1744"
        tbl_rows += (
            f"<tr><td>{yr}</td><td>{_fmt_num(rev_vals[i])}</td>"
            f"<td style='color:{ni_color}'>{_fmt_num(ni_vals[i])}</td>"
            f"<td style='color:{mg_color}'>{margin_pct:.1f}%</td></tr>"
        )

    fig3 = _get_plotly_combo_chart(rev_vals[:4] if rev_vals else [], ni_vals[:4] if ni_vals else [], rev_dates[:4] if rev_dates else [])

    s3 = sum(1 for c in [stability_color, margin_trend_color, accel_color, roe_color] if c == "green")
    if   s3 >= 3: v3_color, v3_text = "green",  "✅ 우수한 트랙 레코드 — 안정 성장 + 높은 ROE"
    elif s3 >= 2: v3_color, v3_text = "yellow", "⚠️ 보통 — 일부 양호, 개선 여지"
    else:         v3_color, v3_text = "red",    "❌ 주의 — 수익 불안정 또는 하락 추세"
    all_verdicts.append(("과거성적", v3_color))

    with st.container(border=True):
        st.markdown('<div class="s-title"><span class="s-num">03</span> 지금까지 성적 <span style="font-size:.8rem;color:#768390">SEC 데이터</span></div>', unsafe_allow_html=True)

        if fig3:
            col1, col2 = st.columns([1.1, 1])
            with col1:
                st.markdown(f"""
                {_metric_row("수익 안정성", f'{rev_stability} <span style="font-size:.8rem;color:#8b949e;font-weight:600">{rev_cv}</span>')}
                {_metric_row("이익 마진 추이", margin_trend_text)}
                {_metric_row("성장 가속화", accel_text)}
                {_metric_row("ROE 수준", roe_display)}
                <div class="divider"></div>
                <table class="m-table"><tr><th>연도</th><th>매출</th><th>순이익</th><th>이익률</th></tr>{tbl_rows}</table>
                """, unsafe_allow_html=True)
            with col2:
                st.plotly_chart(fig3, use_container_width=True, config={'displayModeBar': False})
        else:
            st.markdown(f"""
            {_metric_row("수익 안정성", f'{rev_stability} <span style="font-size:.8rem;color:#8b949e;font-weight:600">{rev_cv}</span>')}
            {_metric_row("이익 마진 추이", margin_trend_text)}
            {_metric_row("성장 가속화", accel_text)}
            {_metric_row("ROE 수준", roe_display)}
            <div class="divider"></div>
            <table class="m-table"><tr><th>연도</th><th>매출</th><th>순이익</th><th>이익률</th></tr>{tbl_rows}</table>
            """, unsafe_allow_html=True)

        st.markdown(_verdict_badge(v3_color, "📌", v3_text), unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════
    # 4️⃣ 성장 가능성
    # ═══════════════════════════════════════════════════
    trailing_pe_raw = info.get('trailingPE')
    forward_pe_raw = info.get('forwardPE')
    payout = info.get('payoutRatio', 0) or 0
    retention = max(0, 1 - payout)
    roe_v = info.get('returnOnEquity', 0) or 0
    sustainable_growth = roe_v * retention if roe_v else None
    earnings_growth = info.get('earningsGrowth')
    forward_eps = info.get('forwardEps')

    # PEG 비율 계산 (N/A 방어)
    peg = info.get('pegRatio')
    if peg is None or pd.isna(peg):
        pe_for_peg = forward_pe_raw if (forward_pe_raw and not pd.isna(forward_pe_raw)) else trailing_pe_raw
        growth_for_peg = earnings_growth
        if (growth_for_peg is None or growth_for_peg <= 0) and isinstance(cagr_eps, float) and cagr_eps > 0:
            growth_for_peg = cagr_eps
        if (growth_for_peg is None or growth_for_peg <= 0) and isinstance(cagr_ni, float) and cagr_ni > 0:
            growth_for_peg = cagr_ni

        if pe_for_peg and growth_for_peg and growth_for_peg > 0:
            peg = pe_for_peg / (growth_for_peg * 100)

    if peg and not pd.isna(peg):
        if peg < 0.5:
            peg_text, peg_css = f"{peg:.2f} (매우 저평가)", "m-blue"
        elif peg <= 1.5:
            peg_text, peg_css = f"{peg:.2f} (적정 가치)", "m-green"
        else:
            peg_text, peg_css = f"{peg:.2f} (고평가)", "m-red"
    else:
        peg_text, peg_css = "N/A", "m-value"

    growth_score = sum(1 for x in [
        earnings_growth and earnings_growth > 0.15,
        yoy_q_rev_growth and isinstance(yoy_q_rev_growth, float) and yoy_q_rev_growth > 0.10,
        retention > 0.60,
        sustainable_growth and sustainable_growth > 0.10,
        peg and 0 < peg <= 1.5,
    ] if x)

    if   growth_score >= 4: v4_color, v4_text = "green",  "🚀 높은 성장 잠재력 — 수익 재투자 + 고성장"
    elif growth_score >= 2: v4_color, v4_text = "yellow", "⚠️ 보통 — 성장 가능성 있으나 모니터링 필요"
    else:                   v4_color, v4_text = "red",    "❌ 성장 둔화 — 새 동력 부재"
    all_verdicts.append(("성장성", v4_color))

    eg_css = "m-green" if earnings_growth and earnings_growth > 0 else "m-red"
    rg_css = "m-green" if yoy_q_rev_growth and isinstance(yoy_q_rev_growth, float) and yoy_q_rev_growth > 0 else "m-red"

    with st.container(border=True):
        st.markdown(f"""
        <div class="s-title"><span class="s-num">04</span> 성장 가능성 <span style="font-size:.8rem;color:#768390">SEC + Yahoo</span></div>
        <div class="two-col">
            <div>
                {_metric_row("분기 이익 성장률 (YoY)", _fmt_pct(earnings_growth), eg_css)}
                {_metric_row("분기 매출 성장률 (YoY)", _fmt_pct(yoy_q_rev_growth), rg_css)}
                {_metric_row("Forward EPS", _fmt_num(forward_eps))}
                {_metric_row("PEG 비율", peg_text, peg_css)}
            </div>
            <div>
                {_metric_row("ROE", _fmt_pct(roe_v))}
                {_metric_row("수익 유보율 (1 - 배당성향)", _fmt_pct(retention))}
                {_metric_row("지속가능 성장률 (g)", _fmt_pct(sustainable_growth), "m-green" if sustainable_growth and sustainable_growth > 0.1 else "m-value")}
                <div class="note-box">
                    💡 <b>지속가능 성장률(g)</b> = ROE × 유보율. 외부 자금 없이 달성 가능한 이론적 최대 성장률.<br>
                    💡 <b>PEG (주가수익성장비율)</b> = P/E Ratio ÷ 이익 성장률<br>
                    &nbsp;&nbsp;• <b>PEG &lt; 0.5</b> : 매우 저평가 &nbsp; • <b>0.5 ~ 1.5</b> : 적정 가치 &nbsp; • <b>PEG &gt; 1.5</b> : 고평가
                </div>
            </div>
        </div>
        {_verdict_badge(v4_color, "📌", v4_text)}
        """, unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════
    # 5️⃣ 재무 건전성
    # ═══════════════════════════════════════════════════
    try:
        total_assets = _get_row(bs, BS_ASSETS_ALIASES, latest=True) or info.get('totalAssets', 0) or 0
        total_liab = _get_row(bs, BS_LIAB_ALIASES, latest=True) or 0
        equity = _get_row(bs, EQ_ALIASES, latest=True) or 0
        info_total_debt = info.get('totalDebt', 0) or 0

        if total_liab == 0 and total_assets > 0 and equity > 0:
            total_liab = total_assets - equity
        net_assets = equity if equity > 0 else (total_assets - total_liab)

        # 백업: 순자산이 0일 경우 BookValue × Shares
        if net_assets == 0:
            book_value = info.get('bookValue', 0)
            shares_out = info.get('sharesOutstanding', 0)
            if book_value and shares_out:
                net_assets = book_value * shares_out

        net_assets_display = _fmt_num(net_assets) if net_assets != 0 else "N/A"

        ta_series = _get_row_series(bs, BS_ASSETS_ALIASES)
        tl_series = _get_row_series(bs, BS_LIAB_ALIASES)
        common_dates = ta_series.index.intersection(tl_series.index).sort_values(ascending=False)[:4]
        fig5 = (
            _get_plotly_yearly_bar(common_dates, [ta_series[i] for i in common_dates], [tl_series[i] for i in common_dates], "총 자산", "총 부채", "#2196F3", "#FF5722")
            if len(common_dates) > 0 else None
        )
    except Exception as e:
        logger.warning(f"Balance sheet analysis failed: {e}")
        total_assets = total_liab = equity = net_assets = info_total_debt = 0
        fig5 = None
        net_assets_display = "N/A"

    cash = info.get('totalCash', 0) or 0
    debt_to_equity = info.get('debtToEquity')
    debt_trend_text, debt_trend_color = _debt_trend(bs)
    interest_text, interest_color = _interest_burden(fin, info)

    if isinstance(debt_to_equity, (int, float)):
        if   debt_to_equity < 50:  debt_level, debt_level_color = "낮음 ✅", "green"
        elif debt_to_equity < 100: debt_level, debt_level_color = "보통 ⚠️", "yellow"
        elif debt_to_equity < 200: debt_level, debt_level_color = "높음 ⚠️", "red"
        else:                      debt_level, debt_level_color = "매우 높음 ❌", "red"
    else:
        debt_level, debt_level_color = "N/A", "gray"

    health_score = sum(1 for x in [
        debt_level_color == "green",
        debt_trend_color == "green",
        interest_color == "green",
        cash > total_liab * 0.2 if total_liab else False,
    ] if x)

    if   health_score >= 3: v5_color, v5_text = "green",  "💪 재무 건전 — 낮은 부채, 충분한 현금"
    elif health_score >= 2: v5_color, v5_text = "yellow", "⚠️ 보통 — 부채 관리 모니터링 필요"
    else:                   v5_color, v5_text = "red",    "❌ 주의 — 부채 높거나 현금 부족"
    all_verdicts.append(("재무건전", v5_color))

    with st.container(border=True):
        st.markdown('<div class="s-title"><span class="s-num">05</span> 회사에 돈이 얼마나 있나요? <span style="font-size:.8rem;color:#768390">SEC + Yahoo</span></div>', unsafe_allow_html=True)

        if fig5:
            col1, col2 = st.columns([1.1, 1])
            with col1:
                st.markdown(f"""
                {_metric_row("💵 보유 현금", _fmt_num(cash), "m-value m-green m-big")}
                {_metric_row("순 자산 (자본)", net_assets_display, "m-green" if net_assets > 0 else "m-red")}
                <div class="divider"></div>
                {_metric_row("총 부채", _fmt_num(info_total_debt), "m-value")}
                {_metric_row("부채 수준 (D/E)", debt_level)}
                {_metric_row("부채 추세", debt_trend_text)}
                {_metric_row("이자 부담 (ICR)", interest_text)}
                {_metric_row("부채/자본 비율", f'{debt_to_equity:.1f}%' if isinstance(debt_to_equity, (int, float)) else 'N/A')}
                <div class="note-box">※ 순자산(총자산-총부채)과 자본(주주지분)은 이론상 같으나, 비지배지분 등에 의해 차이가 날 수 있습니다.</div>
                """, unsafe_allow_html=True)
            with col2:
                st.plotly_chart(fig5, use_container_width=True, config={'displayModeBar': False})
        else:
            st.markdown(f"""
            <div class="two-col">
                <div>
                    {_metric_row("💵 보유 현금", _fmt_num(cash), "m-value m-green m-big")}
                    {_metric_row("순 자산 (자본)", net_assets_display, "m-green" if net_assets > 0 else "m-red")}
                    {_metric_row("총 부채", _fmt_num(info_total_debt), "m-value")}
                    {_metric_row("부채 수준 (D/E)", debt_level)}
                </div>
                <div>
                    {_metric_row("부채 추세", debt_trend_text)}
                    {_metric_row("이자 부담 (ICR)", interest_text)}
                    {_metric_row("부채/자본 비율", f'{debt_to_equity:.1f}%' if isinstance(debt_to_equity, (int, float)) else 'N/A')}
                </div>
            </div>
            <div class="note-box">※ 자산/부채 데이터를 모두 불러올 수 없어 차트가 생략되었습니다.</div>
            """, unsafe_allow_html=True)

        st.markdown(_verdict_badge(v5_color, "📌", v5_text), unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════
    # 6️⃣ 거래량
    # ═══════════════════════════════════════════════════
    volume = info.get('volume', 0) or 0
    avg_vol_10d = info.get('averageVolume10days', 0) or 0
    avg_vol_3m = info.get('averageVolume', 0) or 0
    vol_trend_text, vol_trend_color = _vol_trend(info)
    v6_color = vol_trend_color
    v6_text = {
        "green": "✅ 거래량 정상 — 유동성 양호",
        "yellow": "⚠️ 거래량 변동 — 추이 주시 필요",
        "red": "🔥 거래량 이상 — 급변 가능성",
    }.get(vol_trend_color, "데이터 부족")
    all_verdicts.append(("거래량", v6_color))

    max_vol = max(volume, avg_vol_10d, avg_vol_3m, 1)
    vol_bars = ""
    for label, val, color in [("현재", volume, "#82aaff"), ("10일평균", avg_vol_10d, "#607D8B"), ("3개월평균", avg_vol_3m, "#444c56")]:
        width_pct = val / max_vol * 100
        vol_bars += (
            f'<div style="display:flex;align-items:center;gap:12px;margin:8px 0">'
            f'<span style="min-width:70px;font-size:.85rem;font-weight:700;color:#adbac7;text-align:right">{label}</span>'
            f'<div style="flex:1;background:rgba(0,0,0,0.3);border-radius:6px;height:24px;overflow:hidden">'
            f'<div style="width:{width_pct:.1f}%;height:100%;background:{color};border-radius:6px;'
            f'display:flex;align-items:center;padding-left:10px;font-size:.85rem;color:white;font-weight:800">'
            f'{_fmt_num(val, False)}</div></div></div>'
        )

    with st.container(border=True):
        st.markdown(f"""
        <div class="s-title"><span class="s-num">06</span> 현재 사람들이 많이 사고 있나요? <span style="font-size:.8rem;color:#768390">Yahoo</span></div>
        <div class="two-col">
            <div>
                {_metric_row("현재 거래량", f"{_fmt_num(volume, False)} 주")}
                {_metric_row("10일 평균", f"{_fmt_num(avg_vol_10d, False)} 주")}
                {_metric_row("3개월 평균", f"{_fmt_num(avg_vol_3m, False)} 주")}
                <div class="divider"></div>
                {_metric_row("거래량 변동 추이", vol_trend_text)}
            </div>
            <div>
                <div style="font-size:.95rem;color:#ffffff;margin-bottom:10px;font-weight:800">📊 거래량 비교</div>
                {vol_bars}
            </div>
        </div>
        {_verdict_badge(v6_color, "📌", v6_text)}
        """, unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════
    # 7️⃣ 변동성
    # ═══════════════════════════════════════════════════
    beta = info.get('beta')
    if isinstance(beta, (int, float)):
        if   beta < 0.8: beta_label, beta_color = "저변동 — 시장보다 안정", "green"
        elif beta < 1.2: beta_label, beta_color = "시장과 유사", "yellow"
        elif beta < 1.5: beta_label, beta_color = "높은 변동성 ⚠️", "red"
        else:            beta_label, beta_color = "매우 높은 변동성 🔥", "red"
    else:
        beta_label, beta_color = "N/A", "gray"
    all_verdicts.append(("변동성", beta_color))

    week52_high = info.get('fiftyTwoWeekHigh')
    week52_low = info.get('fiftyTwoWeekLow')
    week52_change = info.get('52WeekChange')

    if price and week52_high and week52_low and week52_high != week52_low:
        pos52 = max(0, min(100, (price - week52_low) / (week52_high - week52_low) * 100))
        pos_str = f"{pos52:.1f}%"
        pos_bar = (
            f"<div style='margin:16px 0'>"
            f"<div style='display:flex;justify-content:space-between;font-size:.85rem;font-weight:700;color:#adbac7;margin-bottom:6px'>"
            f"<span>저 ${week52_low:,.2f}</span>"
            f"<span style='color:#ffffff;font-size:1.1rem;font-weight:900'>현재 ${price:,.2f}</span>"
            f"<span>고 ${week52_high:,.2f}</span></div>"
            f"<div style='background:rgba(0,0,0,0.4);border-radius:8px;height:16px;position:relative'>"
            f"<div style='background:linear-gradient(90deg,#FF1744 0%,#FFC107 50%,#00E676 100%);width:100%;height:100%;border-radius:8px;opacity:0.3'></div>"
            f"<div style='position:absolute;top:-4px;left:{pos52:.1f}%;width:24px;height:24px;background:#82aaff;border-radius:50%;transform:translateX(-50%);border:3px solid #ffffff;box-shadow:0 0 12px #82aaff'></div>"
            f"</div></div>"
        )
    else:
        pos_str, pos_bar = "N/A", ""

    v7_text = f"베타 {beta:.2f} — {beta_label}" if isinstance(beta, (int, float)) else "변동성 데이터 부족"

    with st.container(border=True):
        st.markdown(f"""
        <div class="s-title"><span class="s-num">07</span> 변동성이 큰가요? <span style="font-size:.8rem;color:#768390">Yahoo</span></div>
        <div class="two-col">
            <div>
                {_metric_row("베타 (β)", f"{beta:.2f} ({beta_label})" if isinstance(beta, (int, float)) else "N/A")}
                {_metric_row("52주 가격 변화율", _fmt_pct(week52_change), "m-green" if week52_change and week52_change > 0 else "m-red")}
                {_metric_row("52주 최고가", f"${week52_high:,.2f}" if week52_high else "N/A")}
                {_metric_row("52주 최저가", f"${week52_low:,.2f}" if week52_low else "N/A")}
                {_metric_row("현재가 위치 (52주 내)", pos_str)}
            </div>
            <div>
                <div style="font-size:.95rem;color:#ffffff;margin-bottom:8px;font-weight:800">📍 52주 범위 내 위치</div>
                {pos_bar}
                <div class="note-box">
                    💡 베타 &lt; 1 = 시장(S&amp;P500) 대비 안정적<br>
                    베타 &gt; 1 = 시장보다 변동성이 큽니다.
                </div>
            </div>
        </div>
        {_verdict_badge(beta_color, "📌", v7_text)}
        """, unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════
    # 8️⃣ 밸류에이션
    # ═══════════════════════════════════════════════════
    price_to_sales = info.get('priceToSalesTrailing12Months')
    price_to_book = info.get('priceToBook')
    trailing_eps_val = info.get('trailingEps')
    forward_eps_val = info.get('forwardEps')

    # P/E 교차 검증
    validated_tpe, validated_fpe, pe_warnings = _cross_validate_pe(
        price, trailing_eps_val, forward_eps_val, trailing_pe_raw, forward_pe_raw
    )

    sector_pe, pe_source = _sector_pe_cached(sector)

    pe_comparison = ""
    if validated_tpe and sector_pe:
        diff = ((validated_tpe - sector_pe) / sector_pe) * 100
        if   diff > 30:  pe_comparison = f"섹터 대비 <b style='color:#FF1744'>고평가 (+{diff:.0f}%)</b>"
        elif diff > 0:   pe_comparison = f"섹터 대비 <b style='color:#FFC107'>약간 고평가 (+{diff:.0f}%)</b>"
        elif diff > -20: pe_comparison = f"섹터 대비 <b style='color:#00E676'>적정 ({diff:.0f}%)</b>"
        else:            pe_comparison = f"섹터 대비 <b style='color:#00E676'>저평가 ({diff:.0f}%)</b>"

    if validated_tpe and sector_pe:
        if   validated_tpe < sector_pe * 0.8: v8_color, v8_text = "green",  "💎 저평가 가능성 — 섹터 평균 대비 할인"
        elif validated_tpe < sector_pe * 1.3: v8_color, v8_text = "yellow", "⚖️ 적정 — 섹터 평균과 유사"
        else:                                 v8_color, v8_text = "red",    "💸 고평가 가능성 — 프리미엄 가격"
    else:
        v8_color, v8_text = "gray", "비교 데이터 부족"
    all_verdicts.append(("밸류에이션", v8_color))

    pe_visual = ""
    if validated_tpe and sector_pe:
        max_pe = max(validated_tpe, sector_pe) * 1.3
        pe_visual = (
            f"<div style='margin:16px 0'>"
            f"<div style='font-size:.95rem;color:#ffffff;margin-bottom:12px;font-weight:800'>P/E 비교</div>"
            f"<div style='display:flex;align-items:center;gap:12px;margin:8px 0'>"
            f"<span style='min-width:60px;font-size:.85rem;font-weight:700;color:#82aaff'>이 종목</span>"
            f"<div style='flex:1;background:rgba(0,0,0,0.3);border-radius:6px;height:24px;overflow:hidden'>"
            f"<div style='width:{validated_tpe / max_pe * 100:.1f}%;height:100%;background:#82aaff;border-radius:6px;"
            f"display:flex;align-items:center;justify-content:flex-end;padding-right:10px;font-size:.85rem;color:white;font-weight:800'>"
            f"{validated_tpe:.1f}</div></div></div>"
            f"<div style='display:flex;align-items:center;gap:12px;margin:8px 0'>"
            f"<span style='min-width:60px;font-size:.85rem;font-weight:700;color:#adbac7'>섹터평균</span>"
            f"<div style='flex:1;background:rgba(0,0,0,0.3);border-radius:6px;height:24px;overflow:hidden'>"
            f"<div style='width:{sector_pe / max_pe * 100:.1f}%;height:100%;background:#607D8B;border-radius:6px;"
            f"display:flex;align-items:center;justify-content:flex-end;padding-right:10px;font-size:.85rem;color:white;font-weight:800'>"
            f"{sector_pe:.1f}</div></div></div></div>"
        )

    pe_src_label = f"평균 P/E ≈ {sector_pe:.1f} ({pe_source})" if sector_pe else "N/A"

    # P/E 경고 텍스트
    pe_warning_html = ""
    if pe_warnings:
        pe_warning_html = '<div class="note-box" style="border-left-color:#FFC107">'
        pe_warning_html += "⚠️ <b>P/E 교차 검증 결과</b><br>"
        for w in pe_warnings:
            pe_warning_html += f"• {_esc(w)}<br>"
        pe_warning_html += "</div>"

    with st.container(border=True):
        st.markdown(f"""
        <div class="s-title"><span class="s-num">08</span> 이 종목 비싼가요? <span style="font-size:.8rem;color:#768390">Yahoo</span></div>
        <div class="two-col">
            <div>
                {_metric_row("Trailing P/E <span style='font-size:0.75rem;color:#768390;margin-left:4px'>(현재가÷과거EPS)</span>", f"{validated_tpe:.2f}" if isinstance(validated_tpe, (int, float)) else "N/A")}
                {_metric_row("Forward P/E <span style='font-size:0.75rem;color:#768390;margin-left:4px'>(현재가÷예상EPS)</span>", f"{validated_fpe:.2f}" if isinstance(validated_fpe, (int, float)) else "N/A")}
                {_metric_row("P/S (TTM)", f"{price_to_sales:.2f}" if isinstance(price_to_sales, (int, float)) else "N/A")}
                {_metric_row("P/B", f"{price_to_book:.2f}" if isinstance(price_to_book, (int, float)) else "N/A")}
                <div class="divider"></div>
                {_metric_row(f"섹터 ({_esc(sector)})", pe_src_label)}
                {_metric_row("섹터 대비", pe_comparison if pe_comparison else "N/A")}
            </div>
            <div>
                {pe_visual}
                {pe_warning_html}
                <div class="note-box">
                    ※ P/E는 현재가 ÷ EPS로 교차 검증되었습니다.<br>
                    <b>Trailing P/E</b> = 현재가 ÷ 과거 12개월 실적 EPS<br>
                    <b>Forward P/E</b> = 현재가 ÷ 향후 12개월 추정 EPS<br>
                    섹터 P/E는 실시간 기준입니다.
                </div>
            </div>
        </div>
        {_verdict_badge(v8_color, "📌", v8_text)}
        """, unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════
    # 9️⃣ 전문가 의견
    # ═══════════════════════════════════════════════════
    rec_mean = info.get('recommendationMean')
    rec_key = str(info.get('recommendationKey', 'N/A')).upper()
    if isinstance(rec_mean, (int, float)):
        if   rec_mean <= 1.5: consensus, consensus_color = "🟢 강력 매수",  "green"
        elif rec_mean <= 2.0: consensus, consensus_color = "🟢 매수",       "green"
        elif rec_mean <= 2.5: consensus, consensus_color = "🟡 매수 우위",  "yellow"
        elif rec_mean <= 3.0: consensus, consensus_color = "🟡 보유",       "yellow"
        elif rec_mean <= 3.5: consensus, consensus_color = "🟠 매도 우위",  "red"
        elif rec_mean <= 4.0: consensus, consensus_color = "🔴 매도",       "red"
        else:                 consensus, consensus_color = "🔴 강력 매도",  "red"
    else:
        consensus, consensus_color = "N/A", "gray"
    all_verdicts.append(("전문가", consensus_color))

    target_mean = info.get('targetMeanPrice')
    target_median = info.get('targetMedianPrice')
    target_high = info.get('targetHighPrice')
    target_low = info.get('targetLowPrice')
    num_analysts = info.get('numberOfAnalystOpinions', 0)

    try:
        if target_median and price and price > 0:
            upside_pct = ((target_median - price) / price) * 100
            upside_str = f"{'📈' if upside_pct > 0 else '📉'} {upside_pct:+.1f}%"
        else:
            upside_pct, upside_str = 0, "N/A"
    except Exception as e:
        logger.debug(f"Upside calc failed: {e}")
        upside_pct, upside_str = 0, "N/A"

    fig9 = _get_plotly_target_price(price, target_low, target_mean, target_median, target_high)
    v9_text = f"애널리스트 {num_analysts}명 {rec_key} (목표가 {upside_str})"

    with st.container(border=True):
        st.markdown('<div class="s-title"><span class="s-num">09</span> 전문가들의 의견 <span style="font-size:.8rem;color:#768390">Yahoo</span></div>', unsafe_allow_html=True)

        if fig9:
            col1, col2 = st.columns([1, 1.3])
            with col1:
                st.markdown(f"""
                {_metric_row("컨센서스 등급", _esc(rec_key), "m-value m-blue m-big")}
                {_metric_row("평균 의견 (1~5)", f"{rec_mean:.2f}" if isinstance(rec_mean, (int, float)) else "N/A")}
                {_metric_row("종합 의견", consensus)}
                {_metric_row("참여 애널리스트", f"{num_analysts}명")}
                <div class="divider"></div>
                {_metric_row("최저 목표가", f"${_safe(target_low)}")}
                {_metric_row("중앙값 목표가", f"${_safe(target_median)}")}
                {_metric_row("최고 목표가", f"${_safe(target_high)}")}
                <div style="text-align:center;margin-top:20px;padding:16px;background:rgba(0,0,0,.3);border-radius:12px;border:1px solid #3b424a">
                    <div style="font-size:.9rem;color:#adbac7;font-weight:700">목표가(중앙값) 대비 여력</div>
                    <div style="font-size:1.8rem;font-weight:900;color:{'#00E676' if upside_pct > 0 else '#FF1744'};margin-top:6px">{upside_str}</div>
                </div>
                """, unsafe_allow_html=True)
            with col2:
                st.plotly_chart(fig9, use_container_width=True, config={'displayModeBar': False})
        else:
            st.markdown(f"""
            <div class="two-col">
                <div>
                    {_metric_row("컨센서스 등급", _esc(rec_key), "m-value m-blue m-big")}
                    {_metric_row("평균 의견 (1매수~5매도)", f"{rec_mean:.2f}" if isinstance(rec_mean, (int, float)) else "N/A")}
                    {_metric_row("종합 의견", consensus)}
                    {_metric_row("참여 애널리스트", f"{num_analysts}명")}
                    <div class="divider"></div>
                    {_metric_row("평균 목표가", f"${_safe(target_mean)}")}
                    {_metric_row("중앙값 목표가", f"${_safe(target_median)}")}
                    {_metric_row("최고 목표가", f"${_safe(target_high)}")}
                    {_metric_row("최저 목표가", f"${_safe(target_low)}")}
                </div>
                <div>
                    <div style="text-align:center;margin-top:16px;padding:14px;background:rgba(0,0,0,.3);border-radius:12px;border:1px solid #3b424a">
                        <div style="font-size:.82rem;color:#adbac7;font-weight:700">목표가 대비 여력</div>
                        <div style="font-size:1.8rem;font-weight:900;color:{'#00E676' if upside_pct > 0 else '#FF1744'};margin-top:6px">{upside_str}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown(_verdict_badge(consensus_color, "📌", v9_text), unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════
    # 🔟 지분 구조
    # ═══════════════════════════════════════════════════
    inst_pct = info.get('heldPercentInstitutions', 0) or 0
    insider_pct = info.get('heldPercentInsiders', 0) or 0
    public_pct = max(0, 1 - inst_pct - insider_pct)
    shares_outstanding = info.get('sharesOutstanding', 0) or 0
    float_shares = info.get('floatShares', 0) or 0

    # 지분율 합계 초과 경고
    ownership_sum = inst_pct + insider_pct
    ownership_warning = ""
    if ownership_sum > 1.0:
        ownership_warning = (
            '<div class="note-box" style="border-left-color:#FFC107">'
            f'⚠️ 기관({inst_pct*100:.1f}%) + 내부자({insider_pct*100:.1f}%) = {ownership_sum*100:.1f}%로 100%를 초과합니다. '
            f'이는 Yahoo Finance에서 기관/내부자 지분이 중복 계산되기 때문이며, 개인/기타 비율은 참고용입니다.</div>'
        )

    if   inst_pct > 0.7: v10_color, v10_text = "green",  "✅ 기관 선호 — 높은 기관 보유"
    elif inst_pct > 0.4: v10_color, v10_text = "yellow", "⚠️ 혼합 지분 구조"
    else:                v10_color, v10_text = "red",    "⚠️ 기관 보유 낮음 — 개인 중심"
    all_verdicts.append(("지분구조", v10_color))

    fig10 = _get_plotly_donut(['기관', '내부자', '개인/기타'], [inst_pct, insider_pct, public_pct], ['#2196F3', '#FF9800', '#4CAF50'])

    with st.container(border=True):
        st.markdown('<div class="s-title"><span class="s-num">10</span> 이 회사 누가 들고 있나요? <span style="font-size:.8rem;color:#768390">Yahoo</span></div>', unsafe_allow_html=True)

        if fig10:
            col1, col2 = st.columns([1.1, 1])
            with col1:
                st.markdown(f"""
                {_metric_row("총 발행 주식수", f"{_fmt_num(shares_outstanding, False)} 주")}
                {_metric_row("유통 주식수 (Float)", f"{_fmt_num(float_shares, False)} 주")}
                <div class="divider"></div>
                {_metric_row("🏛️ 기관 비율", _fmt_pct(inst_pct))}
                {_metric_row("👔 내부자 비율", _fmt_pct(insider_pct))}
                {_metric_row("👤 개인/기타 (추정)", _fmt_pct(public_pct))}
                {ownership_warning}
                <div class="note-box">
                    ※ '기관'에는 정부 연기금, 뮤추얼펀드, ETF, 헤지펀드가 포함됩니다.<br>
                    ※ '개인/기타'는 (100% - 기관 - 내부자)로 추정한 값이며, 실제와 다를 수 있습니다.
                </div>
                """, unsafe_allow_html=True)
            with col2:
                st.plotly_chart(fig10, use_container_width=True, config={'displayModeBar': False})
        else:
            st.markdown(f"""
            {_metric_row("총 발행 주식수", f"{_fmt_num(shares_outstanding, False)} 주")}
            {_metric_row("유통 주식수 (Float)", f"{_fmt_num(float_shares, False)} 주")}
            <div class="divider"></div>
            {_metric_row("🏛️ 기관 비율", _fmt_pct(inst_pct))}
            {_metric_row("👔 내부자 비율", _fmt_pct(insider_pct))}
            {_metric_row("👤 개인/기타 (추정)", _fmt_pct(public_pct))}
            {ownership_warning}
            <div class="note-box">
                ※ '기관'에는 정부 연기금, 뮤추얼펀드, ETF, 헤지펀드가 포함됩니다.
            </div>
            """, unsafe_allow_html=True)

        st.markdown(_verdict_badge(v10_color, "📌", v10_text), unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════
    # 1️⃣1️⃣ 옵션 / Max Pain
    # ═══════════════════════════════════════════════════
    exp_date, max_pain_price, top_calls, top_puts, is_vol_weight = _max_pain(tkr)

    mp_display = f"${max_pain_price:.2f}" if max_pain_price else ""
    mp_html = (
        f"<span style='font-size:1.8rem;font-weight:900;color:#ffffff'>{mp_display}</span>"
        if max_pain_price else "<span style='color:#768390;font-size:1.2rem;font-weight:700'>데이터 없음</span>"
    )
    exp_html = f"<span style='font-size:.85rem;color:#adbac7;font-weight:700'>(만기: {exp_date})</span>" if exp_date else ""

    mp_note, mp_color = "", "gray"
    if max_pain_price and price and price > 0:
        mp_diff_pct = ((max_pain_price - price) / price) * 100
        if mp_diff_pct > 2:
            mp_note = f"Max Pain이 현재가보다 <b style='color:#00E676'>{mp_diff_pct:+.1f}% 위</b> → 상승 수렴 가능성"
            mp_color = "green"
        elif mp_diff_pct < -2:
            mp_note = f"Max Pain이 현재가보다 <b style='color:#FF1744'>{mp_diff_pct:+.1f}% 아래</b> → 하락 수렴 가능성"
            mp_color = "red"
        else:
            mp_note = f"현재가와 Max Pain 유사 ({mp_diff_pct:+.1f}%) → 현재 가격대 유지 가능성"
            mp_color = "yellow"
    all_verdicts.append(("옵션", mp_color))

    call_html = "".join([
        f"<li>${c['strike']:.1f} <span style='color:#8b949e;font-size:.8rem'>(Vol {int(c['volume']):,})</span></li>"
        for c in (top_calls or [])
    ]) or "<li>N/A</li>"
    put_html = "".join([
        f"<li>${p['strike']:.1f} <span style='color:#8b949e;font-size:.8rem'>(Vol {int(p['volume']):,})</span></li>"
        for p in (top_puts or [])
    ]) or "<li>N/A</li>"

    mp_badge_text = f"Max Pain {mp_display} — {mp_note.replace('<b>', '').replace('</b>', '')}" if max_pain_price else "옵션 데이터 없음"

    vol_weight_warning = (
        "<div style='color:#FFC107;font-size:.85rem;margin-top:12px;font-weight:700;'>"
        "⚠️ 미결제약정(OI) 데이터 부족으로 임시로 거래량(Volume) 가중치를 사용했습니다.</div>"
        if is_vol_weight else ""
    )

    with st.container(border=True):
        st.markdown(f"""
        <div class="s-title"><span class="s-num">11</span> 시장은 어떤 가격을 보고 있을까요? <span style="font-size:.8rem;color:#768390">Yahoo 옵션</span></div>
        <div style="text-align:center;margin:10px 0 20px">
            <div style="font-size:.9rem;color:#adbac7;font-weight:700;margin-bottom:8px">Max Pain 가격 {exp_html}</div>
            {mp_html}
            <div style="font-size:1.05rem;color:#ffffff;font-weight:700;margin-top:10px">{mp_note}</div>
            {vol_weight_warning}
        </div>
        <div class="divider"></div>
        <div style="display:flex;gap:16px;flex-wrap:wrap">
            <div class="opt-box" style="flex:1;min-width:220px">
                <b style="color:#00E676;font-size:1rem">🟢 Call (상승 베팅) Top 3</b>
                <ul class="opt-list">{call_html}</ul>
            </div>
            <div class="opt-box" style="flex:1;min-width:220px">
                <b style="color:#FF1744;font-size:1rem">🔴 Put (하락 베팅) Top 3</b>
                <ul class="opt-list">{put_html}</ul>
            </div>
        </div>
        <div class="note-box" style="margin-top:20px">
            💡 <b>Max Pain 이론</b>: 옵션 만기 시 가장 많은 옵션 매수자(보유자)가 손실을 보는 가격.<br>
            옵션 매도자(마켓메이커)의 이익이 극대화되는 지점으로, 주가가 만기일에 이 가격 부근으로 수렴하는 경향이 있다는 이론입니다.
        </div>
        {_verdict_badge(mp_color, "📌", mp_badge_text)}
        """, unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════
    # 1️⃣2️⃣ 공매도
    # ═══════════════════════════════════════════════════
    short_pct = info.get('shortPercentOfFloat')
    shares_short = info.get('sharesShort', 0) or 0
    short_ratio = info.get('shortRatio')
    prev_month_short = info.get('sharesShortPriorMonth', 0) or 0

    if isinstance(short_pct, (int, float)):
        if   short_pct > 0.20: short_level, short_color = "매우 높음 🔴 (숏스퀴즈 가능)", "red"
        elif short_pct > 0.10: short_level, short_color = "높음 🟠", "red"
        elif short_pct > 0.05: short_level, short_color = "보통 🟡", "yellow"
        else:                  short_level, short_color = "낮음 🟢", "green"
    else:
        short_level, short_color = "N/A", "gray"
    all_verdicts.append(("공매도", short_color))

    short_trend_text = ""
    if shares_short > 0 and prev_month_short > 0:
        short_chg = ((shares_short - prev_month_short) / prev_month_short) * 100
        if   short_chg > 5:  short_trend_text = f"증가 📈 ({short_chg:+.1f}% vs 전월)"
        elif short_chg < -5: short_trend_text = f"감소 📉 ({short_chg:+.1f}% vs 전월)"
        else:                short_trend_text = f"유지 ➡️ ({short_chg:+.1f}% vs 전월)"

    gauge_color = "#FF1744" if (short_pct or 0) > 0.1 else ("#FFC107" if (short_pct or 0) > 0.05 else "#00E676")
    fig12 = _get_plotly_gauge(short_pct or 0, gauge_color) if short_pct else None

    with st.container(border=True):
        st.markdown('<div class="s-title"><span class="s-num">12</span> 공매도 비율 <span style="font-size:.8rem;color:#768390">Yahoo</span></div>', unsafe_allow_html=True)

        if fig12:
            col1, col2 = st.columns([1.1, 1])
            with col1:
                st.markdown(f"""
                {_metric_row("유통주식 대비 공매도", _fmt_pct(short_pct), "m-red" if short_color == "red" else "m-value")}
                {_metric_row("공매도 수준", short_level)}
                {('<div class="m-row"><span class="m-label">전월 대비</span><span class="m-value">' + short_trend_text + '</span></div>') if short_trend_text else ''}
                <div class="divider"></div>
                {_metric_row("공매도 주식수", f"{_fmt_num(shares_short, False)} 주")}
                {_metric_row("숏커버 일수 (DTC)", f"{short_ratio:.2f} 일" if isinstance(short_ratio, (int, float)) else "N/A")}
                <div class="note-box">
                    💡 공매도 비율 &gt; 10% = 높은 숏 관심<br>
                    DTC(Days To Cover)가 높으면 숏스퀴즈 가능성 ↑<br>
                    ※ 공매도 데이터는 약 2주 지연 발표됩니다.
                </div>
                """, unsafe_allow_html=True)
            with col2:
                st.plotly_chart(fig12, use_container_width=True, config={'displayModeBar': False})
        else:
            st.markdown(f"""
            {_metric_row("유통주식 대비 공매도", _fmt_pct(short_pct), "m-red" if short_color == "red" else "m-value")}
            {_metric_row("공매도 수준", short_level)}
            {('<div class="m-row"><span class="m-label">전월 대비</span><span class="m-value">' + short_trend_text + '</span></div>') if short_trend_text else ''}
            <div class="divider"></div>
            {_metric_row("공매도 주식수", f"{_fmt_num(shares_short, False)} 주")}
            {_metric_row("숏커버 일수 (DTC)", f"{short_ratio:.2f} 일" if isinstance(short_ratio, (int, float)) else "N/A")}
            <div class="note-box">
                💡 공매도 비율 &gt; 10% = 높은 숏 관심
            </div>
            """, unsafe_allow_html=True)

        st.markdown(_verdict_badge(short_color, "📌", f"공매도 {_fmt_pct(short_pct)} — {short_level}"), unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════
    # 📰 13. 최신 뉴스
    # ═══════════════════════════════════════════════════
    try:
        news_list = tkr.news
        if news_list and len(news_list) > 0:
            items = ""
            for n in news_list[:8]:
                title = _esc(n.get('title') or n.get('content', {}).get('title', '제목 없음'))
                link = _esc(n.get('link') or n.get('content', {}).get('canonicalUrl', {}).get('url', '#'))
                pub_name = _esc(n.get('publisher') or n.get('content', {}).get('provider', {}).get('displayName', ''))
                ts = n.get('providerPublishTime', 0)
                if not ts:
                    pd_str = n.get('content', {}).get('pubDate', '')
                    dt_str = pd_str[:16] if pd_str else ""
                else:
                    dt_str = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M') if ts else ""
                items += (
                    f'<div class="n-item">'
                    f'<a href="{link}" target="_blank" class="n-title">{title}</a>'
                    f'<div class="n-meta">{pub_name} · {dt_str}</div></div>'
                )
            with st.container(border=True):
                st.markdown(f"""
                <div class="s-title"><span class="s-num">13</span> 최신 뉴스 <span style="font-size:.8rem;color:#768390">Yahoo Finance</span></div>
                {items}
                """, unsafe_allow_html=True)
        else:
            raise ValueError("No news data available")
    except Exception as e:
        logger.debug(f"News fetch failed: {e}")
        with st.container(border=True):
            st.markdown("""
            <div class="s-title"><span class="s-num">13</span> 최신 뉴스</div>
            <div style="color:#8b949e;padding:10px 0;text-align:center;">뉴스 데이터를 불러올 수 없습니다.</div>
            """, unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════
    # 📋 종합 점수
    # ═══════════════════════════════════════════════════
    total_score, max_score = 0, 0
    for _, color in all_verdicts:
        if color != "gray":
            max_score += 2
            if   color == "green":  total_score += 2
            elif color == "blue":   total_score += 1.5
            elif color == "yellow": total_score += 1
            elif color == "red":    total_score += 0  # 명시적 0점

    overall_pct = (total_score / max_score * 100) if max_score > 0 else 0
    if   overall_pct >= 75: overall_color, overall_emoji, overall_label = "#00E676", "🟢", "매우 양호"
    elif overall_pct >= 55: overall_color, overall_emoji, overall_label = "#FFC107", "🟡", "보통"
    elif overall_pct >= 35: overall_color, overall_emoji, overall_label = "#FF9800", "🟠", "주의 필요"
    else:                   overall_color, overall_emoji, overall_label = "#FF1744", "🔴", "위험"

    dots_html = _score_dot_row(all_verdicts)

    with st.container(border=True):
        st.markdown(f"""
        <div class="s-title" style="border:none;justify-content:center;font-size:1.6rem;">📋 종합 분석 요약</div>
        <div style="text-align:center;margin:8px 0 24px">
            <span style="font-size:2.8rem;font-weight:900;color:{overall_color}">{overall_emoji} {overall_pct:.0f}</span>
            <span style="font-size:1.4rem;color:{overall_color}"> / 100점</span><br>
            <span style="font-size:1.25rem;color:{overall_color};font-weight:800">{overall_label}</span>
        </div>
        <div style="background:rgba(0,0,0,0.4);border-radius:10px;height:16px;overflow:hidden;margin:0 40px;border:1px solid #3b424a">
            <div style="width:{overall_pct:.1f}%;height:100%;background:{overall_color};border-radius:10px;transition:width 1s;box-shadow:0 0 10px {overall_color}"></div>
        </div>
        <div style="margin-top:24px">{dots_html}</div>
        <div class="note-box" style="margin-top:20px;text-align:center">
            수집 가능한 분석 항목들(🟢=2점, 🔵=1.5점, 🟡=1점, 🔴=0점)만을 취합한 종합 점수입니다. (데이터가 누락된 항목은 점수 산정에서 제외됩니다.)
        </div>
        """, unsafe_allow_html=True)

    st.caption("⚠️ 본 분석은 참고용 지표이며 어떠한 경우에도 투자 조언이 아닙니다. 투자에 대한 최종 결정은 본인의 판단과 책임 하에 이루어져야 합니다.")


# ═══════════════════════════════════════════════════════════════
# ▶️ 실행
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    st.set_page_config(page_title="종목 상세 분석", page_icon="📊", layout="wide")
    st.title("📊 종목 상세 분석 대시보드")
    t = st.text_input("🔍 티커 심볼 입력", value="AAPL", placeholder="예: AAPL, MSFT, TSLA")
    if t:
        render_company_details(t.strip().upper())