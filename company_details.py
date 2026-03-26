import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import html as html_module
import logging
from datetime import datetime
import plotly.graph_objects as go
from theme import COMPANY_DETAILS_THEME_OVERRIDES, PLOTLY_FONT_FAMILY

# [SURGE] 로깅 설정
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# 🛠️ API 변동성 대응을 위한 동의어(Alias) 설정
# ═══════════════════════════════════════════════════════════════
REV_ALIASES = ['Total Revenue', 'TotalRevenue', 'Operating Revenue', 'OperatingRevenue', 'Revenue']
NI_ALIASES = [
    'Net Income', 'NetIncome', 'Net Income Common Stockholders', 'NetIncomeCommonStockholders',
    'Net Income Continuous Operations', 'NetIncomeContinuousOperations', 'Net Income From Continuing Ops', 
    'NetIncomeFromContinuingOps', 'Net Income Applicable To Common Shares', 'Net Income Including Noncontrolling Interests',
    'NetIncomeIncludingNoncontrollingInterests'
]
EPS_ALIASES = ['Basic EPS', 'BasicEPS', 'Diluted EPS', 'DilutedEPS', 'Earnings Per Share', 'EarningsPerShare']

BS_ASSETS_ALIASES = ['Total Assets', 'TotalAssets', 'Assets']
BS_LIAB_ALIASES = [
    'Total Liabilities Net Minority Interest', 'TotalLiabilitiesNetMinorityInterest',
    'Total Liab', 'TotalLiab', 'Total Liabilities', 'TotalLiabilities',
    'Total Non Current Liabilities Net Minority Interest', 'TotalNonCurrentLiabilitiesNetMinorityInterest'
]
EQ_ALIASES = [
    'Total Stockholder Equity', 'TotalStockholderEquity', 'Stockholders Equity', 'StockholdersEquity',
    'Common Stock Equity', 'CommonStockEquity', 'Total Equity Gross Minority Interest', 
    'TotalEquityGrossMinorityInterest', 'Total Equity', 'TotalEquity', 'Net Tangible Assets', 'NetTangibleAssets'
]
DEBT_ALIASES = [
    'Total Debt', 'TotalDebt', 'Long Term Debt', 'LongTermDebt',
    'Long Term Debt And Capital Lease Obligation', 'LongTermDebtAndCapitalLeaseObligation',
    'Current Debt', 'CurrentDebt', 'Current Debt And Capital Lease Obligation', 'CurrentDebtAndCapitalLeaseObligation'
]
CFO_ALIASES = [
    'Operating Cash Flow', 'OperatingCashFlow',
    'Cash Flow From Continuing Operating Activities', 'Total Cash From Operating Activities'
]
FCF_ALIASES = ['Free Cash Flow', 'FreeCashFlow']

# ═══════════════════════════════════════════════════════════════
# 🛠️ 유틸리티 함수
# ═══════════════════════════════════════════════════════════════

def _fmt_num(num, is_currency=True):
    if pd.isna(num) or num is None: return "N/A"
    prefix = "$" if is_currency else ""
    sign = "-" if num < 0 else ""
    a = abs(num)
    if   a >= 1e12: return f"{sign}{prefix}{a/1e12:.2f}T"
    elif a >= 1e9:  return f"{sign}{prefix}{a/1e9:.2f}B"
    elif a >= 1e6:  return f"{sign}{prefix}{a/1e6:.2f}M"
    elif a >= 1e3:  return f"{sign}{prefix}{a/1e3:.2f}K"
    return f"{sign}{prefix}{num:,.2f}"

def _fmt_pct(num):
    if num is None or (isinstance(num, float) and np.isnan(num)): return "N/A"
    if isinstance(num, str): return num
    try: return f"{float(num) * 100:.2f}%"
    except Exception: return "N/A"

def _first_valid_number(*values):
    for val in values:
        if val is None:
            continue
        try:
            if pd.isna(val):
                continue
        except Exception:
            pass
        if isinstance(val, (int, float, np.integer, np.floating)):
            return float(val)
    return None

def _normalize_ratio_value(val):
    numeric = _first_valid_number(val)
    if numeric is None:
        return None
    if 1 < numeric <= 100:
        return numeric / 100
    return numeric

def _resolve_dividend_yield(info, price=None):
    raw_yield = _normalize_ratio_value(
        info.get('dividendYield'),
    )
    if raw_yield is None:
        raw_yield = _normalize_ratio_value(info.get('trailingAnnualDividendYield'))
    if raw_yield is None:
        raw_yield = _normalize_ratio_value(info.get('fiveYearAvgDividendYield'))
    if raw_yield is not None and raw_yield >= 0:
        return raw_yield

    dividend_rate = _first_valid_number(
        info.get('dividendRate'),
        info.get('trailingAnnualDividendRate'),
    )
    ref_price = _first_valid_number(
        price,
        info.get('currentPrice'),
        info.get('regularMarketPrice'),
        info.get('previousClose'),
    )
    if dividend_rate is not None and ref_price and ref_price > 0:
        return max(dividend_rate / ref_price, 0)
    return None

def _resolve_peg_ratio(info, *growth_candidates):
    peg = _first_valid_number(info.get('pegRatio'))
    if peg is not None and peg > 0:
        return peg

    pe_val = _first_valid_number(info.get('forwardPE'), info.get('trailingPE'))
    if pe_val is None or pe_val <= 0:
        return None

    for growth in [info.get('earningsGrowth'), info.get('revenueGrowth'), *growth_candidates]:
        growth_val = _normalize_ratio_value(growth)
        if growth_val is not None and growth_val > 0:
            return pe_val / (growth_val * 100)
    return None

def _safe(val, fallback="N/A"):
    if val is None or (isinstance(val, float) and np.isnan(val)): return fallback
    return val

def _esc(text):
    return html_module.escape(str(text)) if text else ""

def _find_idx(df, candidates):
    if df is None or df.empty: return None
    for name in candidates:
        if name in df.index: return name
    norm_cands = [str(c).lower().replace(" ", "") for c in candidates]
    for idx in df.index:
        if str(idx).lower().replace(" ", "") in norm_cands:
            return idx
    return None

def _get_val_from_series(series, aliases):
    if series is None or series.empty: return None
    for alias in aliases:
        if alias in series.index:
            val = series[alias]
            if pd.notna(val): return float(val)
    norm_aliases = [str(a).lower().replace(" ", "") for a in aliases]
    for idx in series.index:
        if str(idx).lower().replace(" ", "") in norm_aliases:
            val = series[idx]
            if pd.notna(val): return float(val)
    return None

def _get_row_series(df, candidates):
    idx = _find_idx(df, candidates)
    if idx is not None:
        try:
            row = df.loc[idx]
            if isinstance(row, pd.DataFrame): row = row.iloc[0]
            return row.dropna()
        except Exception: pass
    return pd.Series(dtype=float)

def _calc_cagr_with_years(financials, row_candidates):
    try:
        rc = row_candidates if isinstance(row_candidates, list) else [row_candidates]
        series = _get_row_series(financials, rc)
        if len(series) >= 2:
            series = series.sort_index()
            s_val, e_val = series.iloc[0], series.iloc[-1]
            years = len(series) - 1
            if s_val > 0 and e_val > 0:
                return (e_val / s_val) ** (1 / years) - 1, years
            elif s_val < 0 and e_val > 0: return "흑자전환 [SURGE]", years
            elif s_val > 0 and e_val < 0: return "적자전환 ⚠️", years
            elif s_val < 0 and e_val < 0:
                if e_val > s_val: return "적자축소 [UP]", years
                else: return "적자지속 [DOWN]", years
    except Exception: pass
    return None, 0

def _fmt_cagr(val):
    if isinstance(val, float): return _fmt_pct(val)
    if isinstance(val, str): return val
    return "N/A"

def _annual_values(financials, row_candidates):
    try:
        rc = row_candidates if isinstance(row_candidates, list) else [row_candidates]
        series = _get_row_series(financials, rc)
        if len(series) > 0:
            series = series.sort_index(ascending=False)
            return series.tolist(), series.index.tolist()
    except Exception: pass
    return [], []

# ── 시각 요소 및 Plotly 차트 생성기 ─────────────────────────────────────

def _verdict_badge(color, emoji, text):
    bg = {"green": "rgba(126,216,182,.15)", "red": "rgba(243,165,165,.15)",
          "yellow": "rgba(245,199,123,.15)", "blue": "rgba(33,150,243,.15)", "gray": "rgba(96,125,139,.15)", "orange": "rgba(255,171,102,.15)"}
    bdr = {"green": "#63D9A2", "red": "#FF8F96", "yellow": "#F6C35E", "blue": "#2196F3", "gray": "#8b949e", "orange": "#FFAB66"}
    return (f'<div style="background:{bg.get(color, bg["gray"])}; border:1px solid {bdr.get(color, bdr["gray"])};border-radius:12px; padding:16px 20px;margin-top:20px;text-align:center; box-shadow: 0 4px 12px {bg.get(color, bg["gray"])};">'
            f'<span style="font-size:1.1rem;font-weight:800; color:{bdr.get(color, bdr["gray"])}">{emoji} {text}</span></div>')

def _metric_row(label, value, value_class="m-value"):
    return f'<div class="m-row"><span class="m-label">{label}</span><span class="{value_class}">{value}</span></div>'

def _gauge_bar(pct, color="#63D9A2", height=8):
    pct = max(0, min(100, pct))
    return (f'<div style="background:rgba(255,255,255,0.1);border-radius:{height}px; height:{height}px;overflow:hidden;margin:6px 0">'
            f'<div style="width:{pct:.1f}%;height:100%;background:{color}; border-radius:{height}px;transition:width .8s"></div></div>')

def _traffic_light(status):
    return "■"

def _score_dot_row(items):
    cells = ""
    colors_map = {"green": "#63D9A2", "yellow": "#F6C35E", "red": "#FF8F96", "blue": "#2196F3", "gray": "#8b949e", "orange": "#FFAB66"}
    for name, color in items:
        c_code = colors_map.get(color, "#8b949e")
        cells += (f'<div style="display:inline-flex;flex-direction:column;align-items:center; min-width:60px;padding:6px 4px">'
                  f'<span style="font-size:1.4rem;color:{c_code}">■</span>'
                  f'<span style="font-size:.75rem;font-weight:700;color:#94a3b8;margin-top:2px; text-align:center;line-height:1.2">{name}</span></div>')
    return f'<div style="display:flex;flex-wrap:wrap;justify-content:center;gap:4px;margin:12px 0">{cells}</div>'

def _apply_cipherx_chart_theme(fig, title_text, height=320, show_legend=True):
    fig.update_layout(
        title=dict(text=f"<b>{title_text}</b>", font=dict(size=16, color='#F8FAFC', family=PLOTLY_FONT_FAMILY)),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(15,23,42,.35)',
        font=dict(color='#E5E7EB', size=12, family=PLOTLY_FONT_FAMILY),
        margin=dict(l=14, r=14, t=48, b=14),
        height=height,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color='#CBD5E1', size=11),
            bgcolor='rgba(0,0,0,0)'
        ),
        showlegend=show_legend,
        hoverlabel=dict(
            bgcolor='rgba(11,14,20,.96)',
            bordercolor='#334155',
            font=dict(color='#F8FAFC', size=11, family=PLOTLY_FONT_FAMILY)
        ),
    )
    fig.update_xaxes(
        showgrid=False,
        tickfont=dict(color='#94A3B8', size=11),
        zeroline=False,
        linecolor='rgba(148,163,184,.16)'
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor='rgba(148,163,184,.12)',
        zeroline=False,
        tickfont=dict(color='#94A3B8', size=11),
        linecolor='rgba(148,163,184,.16)'
    )
    return fig

def _get_plotly_combo_chart(rv, nv, rd):
    if not rv or not rd or len(rv) < 2: return None
    rd_rev, rv_rev, nv_rev = rd[::-1], rv[::-1], nv[::-1]
    labels = [d.strftime('%Y') if hasattr(d, 'strftime') else str(d)[:4] for d in rd_rev]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=labels, y=rv_rev, name='매출',
        marker=dict(color='rgba(96,165,250,.78)', line=dict(color='rgba(165,180,252,.28)', width=1)),
        opacity=0.92,
        text=[_fmt_num(v, False) for v in rv_rev],
        textposition='auto',
        textfont=dict(color='#E5E7EB', size=12, family=PLOTLY_FONT_FAMILY),
        hovertemplate="Revenue<br>%{x}: %{y:$,.0f}<extra></extra>"
    ))
    fig.add_trace(go.Scatter(
        x=labels, y=nv_rev, name='순이익', mode='lines+markers+text',
        line=dict(color='#63D9A2', width=3),
        marker=dict(size=9, color='#0F172A', line=dict(color='#63D9A2', width=2)),
        fill='tozeroy',
        fillcolor='rgba(99,217,162,.12)',
        yaxis='y2',
        text=[_fmt_num(v, False) for v in nv_rev],
        textposition='top center',
        textfont=dict(color='#B8F1D5', size=12, family=PLOTLY_FONT_FAMILY),
        hovertemplate="Net income<br>%{x}: %{y:$,.0f}<extra></extra>"
    ))
    _apply_cipherx_chart_theme(fig, "연도별 재무 추이", height=320, show_legend=True)
    fig.update_layout(
        hovermode='x unified',
        yaxis2=dict(overlaying='y', side='right', showgrid=False, tickfont=dict(color='#63D9A2', size=11))
    )
    return fig

def _get_plotly_yearly_bar(dates, y1, y2, name1, name2, c1, c2):
    if not dates or not y1 or len(y1) < 2: return None
    labels = [d.strftime('%Y') if hasattr(d, 'strftime') else str(d)[:4] for d in dates[::-1]]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=labels, y=y1[::-1], name=name1,
        marker=dict(color=c1, line=dict(color='rgba(148,163,184,.24)', width=1)),
        opacity=0.92,
        text=[_fmt_num(v, False) for v in y1[::-1]],
        textposition='auto',
        textfont=dict(color='#E5E7EB', size=12, family=PLOTLY_FONT_FAMILY)
    ))
    fig.add_trace(go.Bar(
        x=labels, y=y2[::-1], name=name2,
        marker=dict(color=c2, line=dict(color='rgba(148,163,184,.24)', width=1)),
        opacity=0.92,
        text=[_fmt_num(v, False) for v in y2[::-1]],
        textposition='auto',
        textfont=dict(color='#E5E7EB', size=12, family=PLOTLY_FONT_FAMILY)
    ))
    _apply_cipherx_chart_theme(fig, "연도별 자산/부채 추이", height=320, show_legend=True)
    fig.update_layout(barmode='group')
    return fig

def _get_plotly_target_price(curr, low, mean, median, high):
    values = [v for v in [curr, low, mean, median, high] if isinstance(v, (int, float))]
    if len(values) < 2:
        return None

    band_low = low if isinstance(low, (int, float)) else min(values)
    band_high = high if isinstance(high, (int, float)) else max(values)
    span = max(band_high - band_low, max(abs(v) for v in values) * 0.08, 1)
    pad = span * 0.18

    fig = go.Figure()
    fig.add_shape(
        type='rect',
        x0=-0.32, x1=0.32, y0=band_low, y1=band_high,
        fillcolor='rgba(99,102,241,.12)',
        line=dict(color='rgba(99,102,241,.26)', width=1.2),
        layer='below'
    )
    fig.add_shape(
        type='line',
        x0=0, x1=0, y0=band_low - pad, y1=band_high + pad,
        line=dict(color='rgba(148,163,184,.38)', width=8),
        layer='below'
    )
    if isinstance(curr, (int, float)):
        fig.add_shape(
            type='line',
            x0=-0.54, x1=0.54, y0=curr, y1=curr,
            line=dict(color='rgba(246,195,94,.28)', width=1.4, dash='dot'),
            layer='below'
        )

    marker_specs = [
        ('최저가', band_low, -0.22, '#94A3B8', 'circle', 'right', -16),
        ('평균', mean, 0.22, '#38BDF8', 'diamond', 'left', 0),
        ('중앙값', median, -0.22, '#63D9A2', 'diamond', 'right', 8),
        ('최고가', band_high, 0.22, '#E2E8F0', 'circle', 'left', 16),
        ('현재가', curr, 0.0, '#F6C35E', 'star', 'center', 34),
    ]
    annotations = []
    for name, val, xpos, color, symbol, anchor, yshift in marker_specs:
        if not isinstance(val, (int, float)):
            continue
        fig.add_trace(go.Scatter(
            x=[xpos], y=[val], mode='markers',
            marker=dict(
                color=color,
                size=18 if name == '현재가' else 13,
                symbol=symbol,
                line=dict(color='#F8FAFC', width=2 if name == '현재가' else 1.2)
            ),
            hovertemplate=f"{name}<br>${val:,.2f}<extra></extra>",
            showlegend=False
        ))
        annotations.append(dict(
            x=xpos,
            y=val,
            text=f"<b>{name}</b><br>${val:,.2f}",
            showarrow=False,
            xanchor=anchor,
            yanchor='middle' if name != '현재가' else 'bottom',
            xshift=-16 if anchor == 'right' else (16 if anchor == 'left' else 0),
            yshift=yshift,
            font=dict(
                color=color if name in ['현재가', '중앙값', '평균'] else '#E5E7EB',
                size=12,
                family=PLOTLY_FONT_FAMILY
            )
        ))

    _apply_cipherx_chart_theme(fig, "목표가", height=380, show_legend=False)
    fig.update_xaxes(showgrid=False, zeroline=False, showticklabels=False, range=[-0.65, 0.65], fixedrange=True)
    fig.update_yaxes(
        showgrid=True,
        gridcolor='rgba(148,163,184,.10)',
        zeroline=False,
        tickfont=dict(color='#94A3B8', size=11),
        range=[band_low - pad, band_high + pad],
        side='right',
        fixedrange=True,
    )
    fig.update_layout(annotations=annotations)
    return fig

def _get_plotly_donut(labels, values, colors):
    if sum(values) == 0: return None
    fig = go.Figure(data=[go.Pie(
        labels=labels, values=values, hole=.62,
        marker=dict(colors=colors, line=dict(color='rgba(15,23,42,.92)', width=2)),
        textinfo='label+percent',
        textfont=dict(color='#F8FAFC', size=13, family=PLOTLY_FONT_FAMILY),
        hoverinfo='label+percent'
    )])
    _apply_cipherx_chart_theme(fig, "지분 구성 비율", height=280, show_legend=False)
    return fig

def _get_plotly_gauge(val, color):
    val_pct = val * 100
    fig = go.Figure(go.Indicator(
        mode = "gauge+number", value = val_pct, number = {'suffix': "%", 'font': {'size': 32, 'color': color, 'weight':'bold'}},
        gauge = {'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#94A3B8"}, 'bar': {'color': color, 'thickness': 0.76}, 'bgcolor': "rgba(255,255,255,0.06)", 'borderwidth': 0, 'steps': [{'range': [0, 10], 'color': 'rgba(99,217,162,0.20)'}, {'range': [10, 20], 'color': 'rgba(246,195,94,0.20)'}, {'range': [20, 100], 'color': 'rgba(255,143,150,0.20)'}]}
    ))
    _apply_cipherx_chart_theme(fig, "공매도 비율 (100% 기준)", height=280, show_legend=False)
    return fig

# ── 분석 함수들 ─────────────────────────────────────────

def _prepare_story_series(values, dates=None, limit=4):
    if not values:
        return [], []
    points = []
    for idx, raw in enumerate(values[:limit]):
        numeric = _first_valid_number(raw)
        if numeric is None:
            continue
        label = ""
        if dates and idx < len(dates):
            stamp = dates[idx]
            label = stamp.strftime('%Y') if hasattr(stamp, 'strftime') else str(stamp)[:4]
        points.append((label, numeric))
    points.reverse()
    return [value for _, value in points], [label for label, _ in points]

def _story_period_label(labels):
    labels = [label for label in labels if label]
    if not labels:
        return "최근 흐름"
    if len(labels) == 1:
        return labels[0]
    return f"{labels[0]}-{labels[-1]}"

def _sparkline_svg(values, stroke, fill, width=240, height=82):
    if len(values) < 2:
        return "<div class='story-empty'>데이터가 더 필요합니다.</div>"
    low, high = min(values), max(values)
    span = high - low
    if span == 0:
        span = max(abs(high), 1)
        low -= span * 0.5
        high += span * 0.5
        span = high - low
    x_step = width / max(len(values) - 1, 1)
    points = []
    for idx, value in enumerate(values):
        x_pos = idx * x_step
        y_pos = height - 12 - ((value - low) / span) * (height - 24)
        points.append((x_pos, y_pos))
    line_points = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
    area_points = f"0,{height - 8:.2f} {line_points} {width:.2f},{height - 8:.2f}"
    end_x, end_y = points[-1]
    return (
        f"<svg class='story-sparkline' viewBox='0 0 {width} {height}' preserveAspectRatio='none' aria-hidden='true'>"
        f"<line class='story-sparkline__baseline' x1='0' y1='{height - 8:.2f}' x2='{width}' y2='{height - 8:.2f}'></line>"
        f"<polygon points='{area_points}' fill='{fill}'></polygon>"
        f"<polyline class='story-sparkline__line' points='{line_points}' style='stroke:{stroke}'></polyline>"
        f"<circle class='story-sparkline__end' cx='{end_x:.2f}' cy='{end_y:.2f}' r='4.5' style='stroke:{stroke}'></circle>"
        f"</svg>"
    )

def _story_range_strip(current, low, median, high):
    values = [v for v in [current, low, median, high] if isinstance(v, (int, float))]
    if len(values) < 2:
        return "<div class='story-empty'>목표가 데이터가 충분하지 않습니다.</div>"
    low_bound = min(values)
    high_bound = max(values)
    span = max(high_bound - low_bound, max(abs(v) for v in values) * 0.08, 1)
    floor = low_bound - span * 0.15
    ceiling = high_bound + span * 0.15

    def _pos(value):
        if not isinstance(value, (int, float)):
            return None
        ratio = (value - floor) / max(ceiling - floor, 1e-9)
        return max(4.0, min(96.0, ratio * 100))

    low_pos = _pos(low)
    high_pos = _pos(high)
    band_style = ""
    if low_pos is not None and high_pos is not None:
        band_left = min(low_pos, high_pos)
        band_width = max(abs(high_pos - low_pos), 4)
        band_style = f"<span class='story-range-band' style='left:{band_left:.2f}%;width:{band_width:.2f}%'></span>"

    markers = []
    for tone, value, label in [
        ("low", low, "저점"),
        ("median", median, "중간"),
        ("high", high, "고점"),
        ("current", current, "현재"),
    ]:
        pos = _pos(value)
        if pos is None:
            continue
        markers.append(
            f"<span class='story-range-marker story-range-marker--{tone}' style='left:{pos:.2f}%'>"
            f"<b>{label}</b><i>{_fmt_num(value)}</i></span>"
        )
    return (
        "<div class='story-range-shell'>"
        "<div class='story-range-track'>"
        f"{band_style}{''.join(markers)}"
        "</div>"
        "</div>"
    )

def _story_card_html(kicker, value, note, visual_html, footer, tone="accent"):
    footer_html = f"<div class='story-foot'>{footer}</div>" if footer else ""
    return (
        f"<article class='story-card story-card--{tone}'>"
        f"<p class='story-kicker'>{_esc(kicker)}</p>"
        f"<p class='story-value'>{_esc(value)}</p>"
        f"<p class='story-note'>{_esc(note)}</p>"
        f"<div class='story-visual'>{visual_html}</div>"
        f"{footer_html}"
        f"</article>"
    )

def _build_target_corridor_html(curr, low, mean, median, high, coverage_count=0):
    values = [v for v in [curr, low, mean, median, high] if isinstance(v, (int, float))]
    if len(values) < 2:
        return ""

    band_low = low if isinstance(low, (int, float)) else min(values)
    band_high = high if isinstance(high, (int, float)) else max(values)
    span = max(band_high - band_low, max(abs(v) for v in values) * 0.08, 1)
    axis_min = band_low - span * 0.18
    axis_max = band_high + span * 0.18
    band_width = band_high - band_low
    focus_value = median if isinstance(median, (int, float)) else mean
    focus_gap_abs = (focus_value - curr) if isinstance(focus_value, (int, float)) and isinstance(curr, (int, float)) else None
    focus_gap_pct = ((focus_value - curr) / curr * 100) if isinstance(focus_value, (int, float)) and isinstance(curr, (int, float)) and curr else None

    def _pos(value):
        if not isinstance(value, (int, float)):
            return None
        ratio = (value - axis_min) / max(axis_max - axis_min, 1e-9)
        return max(2.0, min(98.0, ratio * 100))

    def _tag_html(label, value, tone, position):
        pos = _pos(value)
        if pos is None:
            return ""
        return (
            f"<div class='consensus-corridor__tag consensus-corridor__tag--{position}' "
            f"style='left:{pos:.2f}%;--corridor-tone:{tone}'>"
            f"<b>{_esc(label)}</b>"
            f"<span>{_fmt_num(value)}</span>"
            f"</div>"
        )

    def _dot_html(label, value, tone, emphasis=False):
        pos = _pos(value)
        if pos is None:
            return ""
        emphasis_class = " consensus-corridor__dot--focus" if emphasis else ""
        return (
            f"<span class='consensus-corridor__dot{emphasis_class}' "
            f"title='{_esc(label)} {_fmt_num(value)}' "
            f"style='left:{pos:.2f}%;--corridor-tone:{tone}'></span>"
        )

    band_left = _pos(band_low)
    band_right = _pos(band_high)
    focus_left = None
    focus_right = None
    if isinstance(mean, (int, float)) and isinstance(median, (int, float)):
        focus_left = _pos(min(mean, median))
        focus_right = _pos(max(mean, median))

    top_tags = "".join([
        _tag_html("평균", mean, "#38BDF8", "top"),
        _tag_html("최고가", band_high, "#E2E8F0", "top"),
        _tag_html("현재가", curr, "#F6C35E", "top"),
    ])
    bottom_tags = "".join([
        _tag_html("최저가", band_low, "#94A3B8", "bottom"),
        _tag_html("중앙값", median, "#63D9A2", "bottom"),
    ])
    dots = "".join([
        _dot_html("최저가", band_low, "#94A3B8"),
        _dot_html("평균", mean, "#38BDF8"),
        _dot_html("중앙값", median, "#63D9A2"),
        _dot_html("최고가", band_high, "#E2E8F0"),
        _dot_html("현재가", curr, "#F6C35E", emphasis=True),
    ])

    focus_band_html = ""
    if focus_left is not None and focus_right is not None:
        focus_width = max(abs(focus_right - focus_left), 2.5)
        focus_band_html = (
            f"<span class='consensus-corridor__band consensus-corridor__band--focus' "
            f"style='left:{min(focus_left, focus_right):.2f}%;width:{focus_width:.2f}%'></span>"
        )

    base_band_html = ""
    if band_left is not None and band_right is not None:
        base_band_html = (
            f"<span class='consensus-corridor__band' "
            f"style='left:{min(band_left, band_right):.2f}%;width:{max(abs(band_right - band_left), 4):.2f}%'></span>"
        )

    gap_text = f"{focus_gap_pct:+.1f}%" if isinstance(focus_gap_pct, (int, float)) else "N/A"
    gap_cash = (
        f"{'+' if focus_gap_abs >= 0 else '-'}${abs(focus_gap_abs):,.2f}"
        if isinstance(focus_gap_abs, (int, float))
        else "N/A"
    )
    summary_stats = (
        f"<div class='consensus-corridor__stats'>"
        f"<div class='consensus-corridor__stat'><p>목표 밴드 폭</p><strong>{_fmt_num(band_width)}</strong></div>"
        f"<div class='consensus-corridor__stat'><p>현재가 vs 기준</p><strong>{gap_text}</strong><span>{gap_cash}</span></div>"
        f"<div class='consensus-corridor__stat'><p>커버리지</p><strong>{coverage_count}명</strong><span>애널리스트 참여 수</span></div>"
        f"</div>"
    )

    return (
        "<div class='consensus-corridor'>"
        "<div class='consensus-corridor__head'>"
        "<div>"
        "<p class='consensus-corridor__kicker'>CONSENSUS PRICE CORRIDOR</p>"
        "</div>"
        f"{summary_stats}"
        "</div>"
        "<div class='consensus-corridor__stage'>"
        f"<div class='consensus-corridor__labels'>{top_tags}</div>"
        "<div class='consensus-corridor__track'>"
        "<span class='consensus-corridor__rail'></span>"
        f"{base_band_html}{focus_band_html}{dots}"
        "</div>"
        f"<div class='consensus-corridor__labels consensus-corridor__labels--bottom'>{bottom_tags}</div>"
        f"<div class='consensus-corridor__axis'><span>{_fmt_num(axis_min)}</span><span>{_fmt_num(axis_max)}</span></div>"
        "</div>"
        "<div class='consensus-corridor__legend'>"
        "<span><i class='consensus-corridor__legend-dot consensus-corridor__legend-dot--slate'></i>저점/고점 밴드</span>"
        "<span><i class='consensus-corridor__legend-dot consensus-corridor__legend-dot--green'></i>중앙값/평균 포커스 존</span>"
        "<span><i class='consensus-corridor__legend-dot consensus-corridor__legend-dot--gold'></i>현재가 포지션</span>"
        "</div>"
        "</div>"
    )

def _growth_stage(info, fin, bs, cf):
    # ─── 기본 지표 추출 ───────────────────────────────────
    rev_g    = info.get('revenueGrowth', 0) or 0
    op_margin= info.get('operatingMargins', 0) or 0
    margin   = info.get('profitMargins', 0) or 0
    rev      = info.get('totalRevenue', 0) or 0
    div_y    = info.get('dividendYield', 0) or 0
    roe      = info.get('returnOnEquity', 0) or 0
    mkt_cap  = info.get('marketCap', 0) or 0
    total_debt= info.get('totalDebt', 0) or 0
    eq       = info.get('bookValue', 0) or 0
    shares   = info.get('sharesOutstanding', 1) or 1
    book_val = eq * shares if eq > 0 else 1
    debt_ratio = (total_debt / book_val) if book_val > 0 else 0

    op_cf = 0
    try:
        if cf is not None:
            for n in ['Operating Cash Flow', 'Total Cash From Operating Activities']:
                if n in cf.index:
                    op_cf = cf.loc[n].dropna().iloc[0] or 0
                    break
    except Exception: pass

    # FCF 수익률: opCF / 시가총액
    fcf_yield = (op_cf / mkt_cap) if mkt_cap > 0 else 0

    # ─── 매출 규모 등급 (S/M/L/XL) ──────────────────────
    if   rev < 5e8:   revenue_scale = 'S'   # ~5억달러 미만
    elif rev < 1e10:  revenue_scale = 'M'   # 5억~100억
    elif rev < 1e11:  revenue_scale = 'L'   # 100억~1000억
    else:             revenue_scale = 'XL'  # 1000억 이상

    # ─── 업력 추정 (IPO 연도 기반 / yfinance 실제 지원 키 사용) ────
    try:
        ipo_ts = info.get('firstTradeDateEpochUtc') or info.get('firstTradeDateMilliseconds')
        if ipo_ts:
            ipo_year = datetime.utcfromtimestamp(int(str(ipo_ts)[:10])).year
        else:
            ipo_year = info.get('ipoYear') or info.get('foundedYear') or 2000
        company_age = max(2026 - int(ipo_year), 1)
    except Exception:
        company_age = 20

    # ─── 매출 추세 분석 (declining / rev_declining) ─────
    rev_declining = False
    rev_series_sorted = None
    try:
        rs = _get_row_series(fin, REV_ALIASES)
        if len(rs) >= 3:
            rev_series_sorted = rs.sort_index(ascending=False)
            if sum(1 for i in range(len(rev_series_sorted) - 1) if rev_series_sorted.iloc[i] < rev_series_sorted.iloc[i + 1]) >= 2:
                rev_declining = True
    except Exception: pass

    # ─── 3년 CAGR 산출 ───────────────────────────────────
    rev_cagr_3y = rev_g  # fallback
    try:
        if rev_series_sorted is not None and len(rev_series_sorted) >= 4:
            r_new = rev_series_sorted.iloc[0]
            r_old = rev_series_sorted.iloc[3]
            if r_old > 0:
                rev_cagr_3y = (r_new / r_old) ** (1/3) - 1
    except Exception: pass

    # ─── 이익률 추세 (up / flat / down) ─────────────────
    margin_trend = 'flat'
    try:
        ni_s = _get_row_series(fin, NI_ALIASES)
        rv_s = _get_row_series(fin, REV_ALIASES)
        common_idx = ni_s.index.intersection(rv_s.index).sort_values()
        margins_ts = [(i, ni_s[i] / rv_s[i]) for i in common_idx if rv_s[i] != 0]
        if len(margins_ts) >= 2:
            delta = margins_ts[-1][1] - margins_ts[0][1]
            if   delta >  0.02: margin_trend = 'up'
            elif delta < -0.02: margin_trend = 'down'
    except Exception: pass

    # ─── 성장률 추세 (accel / flat / decel) ─────────────
    growth_trend = 'flat'
    try:
        if rev_series_sorted is not None and len(rev_series_sorted) >= 3:
            g_rates = [(rev_series_sorted.iloc[i] - rev_series_sorted.iloc[i+1]) / abs(rev_series_sorted.iloc[i+1])
                       for i in range(len(rev_series_sorted)-1) if rev_series_sorted.iloc[i+1] != 0]
            if len(g_rates) >= 2:
                recent_g  = g_rates[0]
                past_g    = np.mean(g_rates[1:]) if len(g_rates) > 1 else g_rates[0]
                if   recent_g > past_g + 0.05: growth_trend = 'accel'
                elif recent_g < past_g - 0.05: growth_trend = 'decel'
    except Exception: pass

    # ─── 연속 흑자 연수 (profit_streak) ─────────────────
    profit_streak = 0
    consec_loss   = 0
    try:
        ni_s2 = _get_row_series(fin, NI_ALIASES).sort_index(ascending=False)
        for v in ni_s2:
            if v > 0: profit_streak += 1
            else: break
        for v in ni_s2:
            if v < 0: consec_loss += 1
            else: break
    except Exception: pass

    net_profit = margin > 0

    stages = {
        1:  ("[STAGE 1] 스타트업",          "매출 규모가 작고 아직 수익 모델이 검증되지 않은 초기 생존 테스트 단계입니다."),
        2:  ("[STAGE 2] 초기 고성장",        "30% 이상의 폭발적 매출 성장으로 시장 점유율을 빠르게 확장하고 있습니다."),
        3:  ("[STAGE 3] 스케일업 & 흑자전환","20~50% 성장과 함께 흑자 진입에 성공한 황금 모멘텀 구간입니다."),
        4:  ("[STAGE 4] 초고속 흑자성장",    "50% 이상 폭증과 고이익률을 동시에 달성한 초우량 주도주 입니다."),
        5:  ("[STAGE 5] 성숙 우량성장",      "5~20% 성장과 높은 ROE를 유지하는 장기 우량주 구간입니다."),
        6:  ("[STAGE 6] 초우량 캐시카우",    "성장이 낮아졌지만 잉여현금흐름·ROE가 탁월하며 주주환원이 강력한 단계입니다."),
        7:  ("[STAGE 7] 애매한 정체기",      "성장이 정체(0~3%)되고 이익률 개선 모멘텀이 보이지 않는 경계 구간입니다."),
        8:  ("[STAGE 8] 초기 쇠퇴",          "매출 역성장이 시작됐으나 이익률은 아직 방어 중인 경고 단계입니다."),
        9:  ("[STAGE 9] 구조적 쇠퇴",        "연속 적자 + 매출 급감 + 높은 부채비율로 구조적 위기에 빠진 고위험군입니다."),
        10: ("[STAGE 10] 극적 턴어라운드",   "과거 쇠퇴를 딛고 최근 매출/이익 개선이 확인된 회생 반등 단계입니다."),
    }
    colors = {
        1: "#FF7043", 2: "#FFA726", 3: "#FF9800", 4: "#FF6D00", 5: "#00E676",
        6: "#00C853", 7: "#E57373", 8: "#F44336", 9: "#C62828", 10: "#FFC107"
    }

    # algo_ctx는 모든 return 경로에서 공통으로 포함됩니다
    def _mk_ctx():
        return {
            'revenue_scale': revenue_scale,
            'profit_streak': profit_streak,
            'consec_loss': consec_loss,
            'roe': roe,
            'margin_trend': margin_trend,
            'growth_trend': growth_trend,
            'rev_cagr_3y': rev_cagr_3y,
            'rev_g': rev_g,
        }

    # ══════════════════════════════════════════════
    # Phase 0: 턴어라운드 (최우선 판별)
    # ══════════════════════════════════════════════
    if rev_declining and (rev_g > 0 or margin_trend == 'up'):
        return 10, stages[10][0], stages[10][1], colors[10], _mk_ctx()

    # ══════════════════════════════════════════════
    # Phase 1: 쇠퇴 영역 (위험 → 안전 순)
    # ══════════════════════════════════════════════
    if consec_loss >= 3 and rev_g < -0.15 and debt_ratio > 2.0:
        return 9, stages[9][0], stages[9][1], colors[9], _mk_ctx()

    if rev_g < -0.05 and margin_trend == 'down':
        return 8, stages[8][0], stages[8][1], colors[8], _mk_ctx()

    if -0.05 <= rev_g <= 0.03 and growth_trend == 'decel' and margin_trend in ('flat', 'down'):
        return 7, stages[7][0], stages[7][1], colors[7], _mk_ctx()

    # ══════════════════════════════════════════════
    # Phase 2: 초기 기업
    # ══════════════════════════════════════════════
    if company_age <= 5 and revenue_scale == 'S' and (not net_profit or op_margin < 0.05):
        return 1, stages[1][0], stages[1][1], colors[1], _mk_ctx()

    if rev_g > 0.30 and revenue_scale in ('S', 'M') and (not net_profit or profit_streak <= 1):
        return 2, stages[2][0], stages[2][1], colors[2], _mk_ctx()

    # ══════════════════════════════════════════════
    # Phase 3: 고성장 영역
    # ══════════════════════════════════════════════
    # 초고속 성장: accel이 아닌 경우도 감속 추세만 아니면 인정 (ex. 고성장 유지 중)
    if (rev_g > 0.50
            and revenue_scale in ('L', 'XL')
            and net_profit
            and op_margin > 0.15
            and growth_trend != 'decel'):
        return 4, stages[4][0], stages[4][1], colors[4], _mk_ctx()

    if (0.20 <= rev_g <= 0.50
            and net_profit
            and op_margin > 0.10):
        return 3, stages[3][0], stages[3][1], colors[3], _mk_ctx()

    # ══════════════════════════════════════════════
    # Phase 4: 성숙 우량 영역
    # ══════════════════════════════════════════════
    if (0.05 <= rev_g <= 0.20
            and profit_streak >= 5
            and roe > 0.15
            and margin_trend in ('up', 'flat')):
        return 5, stages[5][0], stages[5][1], colors[5], _mk_ctx()

    if (0.00 <= rev_g <= 0.10
            and profit_streak >= 10
            and fcf_yield > 0.05
            and roe > 0.12
            and (div_y > 0.01 or op_cf > rev * 0.1)):
        return 6, stages[6][0], stages[6][1], colors[6], _mk_ctx()


    # ══════════════════════════════════════════════
    # Fallback: 스코어링 매트릭스 (경계 케이스 처리)
    # ══════════════════════════════════════════════
    def _clamp(v, lo=0, hi=100): return max(lo, min(hi, v))

    g_score = _clamp((rev_g * 200) + (rev_cagr_3y * 100) + (20 if growth_trend == 'accel' else -20 if growth_trend == 'decel' else 0))
    p_score = _clamp((op_margin * 200) + (roe * 200) + (profit_streak * 5))
    s_score = _clamp((-debt_ratio * 10 + 50) + (fcf_yield * 500) + (20 if margin_trend == 'up' else -10 if margin_trend == 'down' else 0))
    m_score = _clamp(({'S':0,'M':30,'L':70,'XL':100}[revenue_scale] + min(company_age * 2, 40)) / 1.4)
    mo_score= _clamp(50 + rev_g * 300)

    total = g_score * 0.30 + p_score * 0.25 + s_score * 0.20 + m_score * 0.15 + mo_score * 0.10

    if   total >= 75: s = 4 if rev_g > 0.30 else 5
    elif total >= 55: s = 5 if net_profit else 3
    elif total >= 40: s = 6 if div_y > 0.01 else 7
    elif total >= 25: s = 8 if rev_g < 0 else 7
    else:             s = 9 if consec_loss >= 2 else 8

    algo_ctx = {
        'revenue_scale': revenue_scale,
        'profit_streak': profit_streak,
        'consec_loss': consec_loss,
        'roe': roe,
        'margin_trend': margin_trend,
        'growth_trend': growth_trend,
        'rev_cagr_3y': rev_cagr_3y,
        'rev_g': rev_g,
    }
    return s, stages[s][0], stages[s][1], colors[s], algo_ctx

def _stability(financials, rc):
    vals, _ = _annual_values(financials, rc)
    arr = np.array([v for v in vals if v is not None and not np.isnan(v)])
    if len(arr) < 2 or np.mean(arr) == 0: return "데이터 부족", "", "gray"
    cv = np.std(arr) / abs(np.mean(arr))
    if   cv < 0.10: return "매우 안정적 ✅", f"CV {cv:.3f}", "green"
    elif cv < 0.25: return "안정적 ✅",     f"CV {cv:.3f}", "green"
    elif cv < 0.50: return "보통 ⚠️",       f"CV {cv:.3f}", "orange"
    else:           return "불안정 ❌",      f"CV {cv:.3f}", "red"

def _margin_trend(fin):
    try:
        rs, ns = _get_row_series(fin, REV_ALIASES), _get_row_series(fin, NI_ALIASES)
        idx = rs.index.intersection(ns.index).sort_values()
        margins = [(i, ns[i] / rs[i]) for i in idx if rs[i] != 0]
        if len(margins) < 2: return "N/A", [], "gray"
        f_m, l_m = margins[0][1], margins[-1][1]
        if l_m > f_m + 0.02: return f"증가 추세 [UP] ({f_m * 100:.1f}% → {l_m * 100:.1f}%)", margins, "green"
        if l_m < f_m - 0.02: return f"감소 추세 [DOWN] ({f_m * 100:.1f}% → {l_m * 100:.1f}%)", margins, "red"
        return f"유지 [FLAT] ({l_m * 100:.1f}%)", margins, "yellow"
    except Exception: return "N/A", [], "gray"

def _growth_accel(fin, rc):
    vals, _ = _annual_values(fin, rc)
    if len(vals) < 3: return "N/A", "gray"
    g = [(vals[i] - vals[i + 1]) / abs(vals[i + 1]) for i in range(len(vals) - 1) if vals[i + 1] and vals[i + 1] != 0]
    if len(g) < 2: return "N/A", "gray"
    recent_g, past_g_avg = g[0], np.mean(g[1:4]) if len(g) > 2 else g[1]
    if recent_g > past_g_avg + 0.05: return f"가속화 [SURGE] (최근 {recent_g * 100:.1f}% vs 과거 {past_g_avg * 100:.1f}%)", "green"
    elif recent_g < past_g_avg - 0.05: return f"감속 [SLOW] (최근 {recent_g * 100:.1f}% vs 과거 {past_g_avg * 100:.1f}%)", "yellow"
    return f"유지 [FLAT] (최근 {recent_g * 100:.1f}% vs 과거 {past_g_avg * 100:.1f}%)", "green"

def _debt_trend(bs_df):
    for nc in [BS_LIAB_ALIASES, ['Long Term Debt'], ['Total Debt']]:
        series = _get_row_series(bs_df, nc)
        if len(series) >= 2:
            latest, oldest = series.sort_index(ascending=False).iloc[0], series.sort_index(ascending=False).iloc[-1]
            if oldest != 0:
                chg = (latest - oldest) / abs(oldest)
                if   chg < -0.10: return f"감소 추세 ✅ ({chg * 100:.1f}%)", "green"
                elif chg >  0.10: return f"증가 추세 ⚠️ (+{chg * 100:.1f}%)", "red"
                else:             return f"안정 유지 [FLAT] ({chg * 100:.1f}%)", "orange"
    return "데이터 부족", "gray"

def _interest_burden(fin, info):
    ebit_series = _get_row_series(fin, ['EBIT', 'Operating Income'])
    interest_series = _get_row_series(fin, ['Interest Expense', 'Interest Expense Non Operating'])
    ebit = ebit_series.iloc[-1] if not ebit_series.empty else None
    interest = interest_series.iloc[-1] if not interest_series.empty else None
    
    if ebit is not None and interest is not None and abs(interest) > 0:
        if ebit < 0: return "위험 ❌ (영업적자)", "red"
        icr = abs(ebit / interest)
        if   icr > 10: return f"매우 낮음 ✅ (ICR {icr:.1f}x)", "green"
        elif icr >  5: return f"낮음 ✅ (ICR {icr:.1f}x)", "green"
        elif icr >  2: return f"보통 ⚠️ (ICR {icr:.1f}x)", "yellow"
        else:          return f"높음 ❌ (ICR {icr:.1f}x)", "red"
        
    ebitda, debt = info.get('ebitda', 0) or 0, info.get('totalDebt', 0) or 0
    if ebitda and debt and debt > 0:
        if ebitda < 0: return "위험 ❌ (EBITDA 적자)", "red"
        cov = ebitda / (debt * 0.05)
        if   cov > 10: return f"매우 낮음 ✅ (추정 {cov:.1f}x)", "green"
        elif cov >  5: return f"낮음 ✅ (추정 {cov:.1f}x)", "green"
        elif cov >  2: return f"보통 ⚠️ (추정 {cov:.1f}x)", "yellow"
        else:          return f"높음 ❌ (추정 {cov:.1f}x)", "red"
    return "N/A", "gray"

def _vol_trend(info):
    vol, avg3m = info.get('volume', 0) or 0, info.get('averageVolume', 0) or 0
    if avg3m == 0: return "데이터 부족", "gray"
    r = vol / avg3m
    if   r > 1.5: return f"급증 [HOT] ({r:.1f}배)", "yellow"
    elif r > 1.1: return f"증가 [UP] ({r:.1f}배)", "yellow"
    elif r > 0.9: return f"평균 수준 [FLAT] ({r:.1f}배)", "green"
    elif r > 0.5: return f"감소 [DOWN] ({r:.1f}배)", "yellow"
    else:         return f"급감 ⚠️ ({r:.1f}배)", "red"

def _max_pain(tkr):
    try:
        dates = tkr.options
        if not dates: return None, None, None, None, False
        exp = dates[0]
        c, p = tkr.option_chain(exp).calls.copy(), tkr.option_chain(exp).puts.copy()
        for col in ['openInterest', 'volume']:
            c[col], p[col] = c.get(col, pd.Series(0, index=c.index)).fillna(0), p.get(col, pd.Series(0, index=p.index)).fillna(0)
            
        c_oi_sum, p_oi_sum, is_vol_weight = c['openInterest'].sum(), p['openInterest'].sum(), False
        if c_oi_sum == 0 or p_oi_sum == 0 or (c_oi_sum / max(p_oi_sum, 1) < 0.02) or (p_oi_sum / max(c_oi_sum, 1) < 0.02):
            weight_c, weight_p, is_vol_weight = c['volume'], p['volume'], True 
            if weight_c.sum() == 0 and weight_p.sum() == 0: return exp, None, [], [], False 
        else: weight_c, weight_p = c['openInterest'], p['openInterest']

        strikes = sorted(set(c['strike']).union(set(p['strike'])))
        pain = {s: (np.sum(weight_c * np.maximum(0, s - c['strike'])) + np.sum(weight_p * np.maximum(0, p['strike'] - s))) for s in strikes}
        mp = min(pain, key=pain.get) if pain and max(pain.values()) > 0 else None
        return exp, mp, c.nlargest(3, 'volume')[['strike', 'volume']].to_dict('records'), p.nlargest(3, 'volume')[['strike', 'volume']].to_dict('records'), is_vol_weight
    except Exception: return None, None, None, None, False

@st.cache_data(ttl=3600, show_spinner=False)
def _sector_pe_live(sector):
    etf = {"Technology": "XLK", "Financial Services": "XLF", "Healthcare": "XLV", "Energy": "XLE", "Consumer Cyclical": "XLY", "Consumer Defensive": "XLP", "Industrials": "XLI", "Communication Services": "XLC", "Utilities": "XLU", "Real Estate": "XLRE", "Basic Materials": "XLB"}.get(sector)
    if etf:
        try:
            pe = yf.Ticker(etf).info.get('trailingPE')
            if pe and isinstance(pe, (int, float)) and pe > 0: return pe, "실시간"
        except Exception: pass
    fb = {"Technology": 30, "Communication Services": 22, "Consumer Cyclical": 25, "Consumer Defensive": 22, "Financial Services": 14, "Healthcare": 22, "Industrials": 20, "Energy": 12, "Basic Materials": 15, "Real Estate": 35, "Utilities": 18}.get(sector)
    return (fb, "추정치") if fb else (None, "")

# ═══════════════════════════════════════════════════════════════
# 🎨 CSS
# ═══════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════
# 🎨 CSS
# ═══════════════════════════════════════════════════════════════
def _is_rate_limited_error(err):
    msg = str(err).lower()
    return "too many requests" in msg or "rate limit" in msg or "429" in msg

@st.cache_data(ttl=1800, show_spinner=False)
def _fetch_company_bundle(ticker_str):
    result = {
        "info": {},
        "fin": pd.DataFrame(),
        "q_fin": pd.DataFrame(),
        "bs": pd.DataFrame(),
        "cf": pd.DataFrame(),
        "error": None,
        "rate_limited": False,
    }
    try:
        tkr = yf.Ticker(ticker_str)
        result["info"] = tkr.info or {}
        try:
            fin = tkr.financials if not tkr.financials.empty else tkr.income_stmt
            result["fin"] = fin if fin is not None else pd.DataFrame()
        except Exception:
            pass
        try:
            q_fin = tkr.quarterly_financials if not tkr.quarterly_financials.empty else tkr.quarterly_income_stmt
            result["q_fin"] = q_fin if q_fin is not None else pd.DataFrame()
        except Exception:
            pass
        try:
            bs = getattr(tkr, 'balance_sheet', None)
            if bs is None or bs.empty: bs = getattr(tkr, 'balancesheet', None)
            if bs is None or bs.empty: bs = tkr.get_balance_sheet(pretty=True)
            if bs is None or bs.empty: bs = tkr.get_balance_sheet(pretty=False)
            result["bs"] = bs if bs is not None else pd.DataFrame()
        except Exception:
            pass
        try:
            cf = tkr.cashflow
            result["cf"] = cf if cf is not None else pd.DataFrame()
        except Exception:
            pass
    except Exception as e:
        result["error"] = str(e)
        result["rate_limited"] = _is_rate_limited_error(e)
    return result

@st.cache_data(ttl=900, show_spinner=False)
def _fetch_option_snapshot(ticker_str):
    try:
        return {"data": _max_pain(yf.Ticker(ticker_str)), "error": None, "rate_limited": False}
    except Exception as e:
        return {"data": (None, None, None, None, False), "error": str(e), "rate_limited": _is_rate_limited_error(e)}

@st.cache_data(ttl=900, show_spinner=False)
def _fetch_company_news_items(ticker_str):
    try:
        news_list = yf.Ticker(ticker_str).news
        items = []
        for n in (news_list or [])[:8]:
            title = n.get('title') or n.get('content', {}).get('title', '제목 없음')
            link = n.get('link') or n.get('content', {}).get('canonicalUrl', {}).get('url', '#')
            pub_name = n.get('publisher') or n.get('content', {}).get('provider', {}).get('displayName', '')
            ts = n.get('providerPublishTime', 0)
            dt_str = (n.get('content', {}).get('pubDate', '') or '')[:16] if not ts else datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')
            items.append({"title": title, "link": link, "publisher": pub_name, "date": dt_str})
        return {"items": items, "error": None, "rate_limited": False}
    except Exception as e:
        return {"items": [], "error": str(e), "rate_limited": _is_rate_limited_error(e)}

CSS = """
<style>
__SIGL_COMPANY_THEME__
@keyframes fadeUp{from{opacity:0;transform:translateY(20px);}to{opacity:1;transform:translateY(0);}}
[data-testid="stVerticalBlockBorderWrapper"] {
    background:
        linear-gradient(180deg,rgba(99,102,241,.05),rgba(99,102,241,0) 26%),
        linear-gradient(160deg,rgba(15,23,42,.94),rgba(17,24,39,.84)) !important;
    backdrop-filter: blur(16px) !important;
    -webkit-backdrop-filter: blur(16px) !important;
    border: 1px solid rgba(99,102,241,.16) !important;
    border-radius: 18px !important;
    box-shadow: 0 16px 34px rgba(2,6,23,.28) !important;
    transition: all 0.4s cubic-bezier(0.16,1,0.3,1) !important; 
    max-width: 960px; margin-left: auto; margin-right: auto; margin-bottom: 35px !important; 
    animation: fadeUp 0.6s cubic-bezier(0.16,1,0.3,1) forwards;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover { 
    transform: translateY(-3px) !important;
    border-color: rgba(99,102,241,0.28) !important;
    box-shadow: 0 18px 42px rgba(2,6,23,.34) !important;
}
[data-testid="stVerticalBlockBorderWrapper"] > div { padding: 28px 32px !important; }
.s-title{ font-size:1.18rem;font-weight:800;color:#C7D2FE; margin-bottom:22px;padding-bottom:12px; border-bottom:1px solid rgba(148,163,184,.12); display:flex;align-items:center;gap:12px}
.s-title .s-num{ background:rgba(99,102,241,.14);border:1px solid rgba(99,102,241,.26);border-radius:999px;padding:4px 10px; font-size:.8rem;color:#C7D2FE;font-weight:900}
.m-row{display:flex;justify-content:space-between; padding:12px 0;font-size:.95rem;align-items:center; border-bottom:1px solid rgba(255,255,255,.04); transition:all 0.3s ease;}
.m-row:hover{background:rgba(255,255,255,0.025); padding-left:8px; padding-right:8px; border-radius:8px;}
.m-row:last-child{border-bottom:none}
.m-label{color:#94A3B8;font-weight:600}
.m-value{color:#F8FAFC;font-weight:800;text-align:right;max-width:55%}
.m-green{color:#63D9A2 !important;font-weight:800}
.m-red{color:#FF8F96 !important;font-weight:800}
.m-yellow{color:#F8DE9A !important;font-weight:800}
.m-blue{color:#38BDF8 !important;font-weight:800}
.m-big{font-size:1.15rem;font-weight:900}
.divider{border-top:1px dashed rgba(148,163,184,.16);margin:20px 0}
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:20px}
@media(max-width:900px){
  .two-col{grid-template-columns:1fr}
  [data-testid="stVerticalBlockBorderWrapper"] > div { padding: 20px 18px !important; }
  .header-wrap{align-items:flex-start}
  .s-title{font-size:1.05rem;flex-wrap:wrap}
}
.opt-box{background:linear-gradient(160deg,rgba(15,23,42,.9),rgba(15,23,42,.72));backdrop-filter:blur(8px);padding:16px;border-radius:14px;border:1px solid rgba(148,163,184,.12); transition:all .3s;}
.opt-box:hover{background:linear-gradient(160deg,rgba(15,23,42,.94),rgba(15,23,42,.78)); transform:translateY(-2px);}
.opt-list{margin:8px 0 0;padding-left:18px;font-size:.9rem;color:#F8FAFC;line-height:2.0;font-weight:600}
.m-table{width:100%;border-collapse:collapse;font-size:.9rem;margin-top:8px}
.m-table th{color:#94A3B8;text-align:left;padding:12px 10px;border-bottom:1px solid rgba(148,163,184,.16);font-weight:700}
.m-table td{color:#E8ECF1;padding:12px 10px;border-bottom:1px solid rgba(255,255,255,.02);font-weight:600; transition:all .3s;}
.m-table tr:hover td{background:rgba(255,255,255,0.025);}
.header-wrap{display:flex;justify-content:space-between;align-items:flex-end; flex-wrap:wrap;gap:12px;max-width:960px;margin:0 auto 18px; animation:fadeUp 0.6s forwards;}
.cd-summary{max-width:960px;margin:0 auto 18px;background:
    linear-gradient(180deg,rgba(99,102,241,.08),rgba(99,102,241,0) 30%),
    linear-gradient(160deg,rgba(10,14,24,.96),rgba(16,24,39,.88));
    border:1px solid rgba(99,102,241,.22);border-radius:16px;padding:14px 16px;box-shadow:0 14px 32px rgba(2,6,23,.18)}
.cd-summary-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}
.cd-chip{background:rgba(255,255,255,.03);border:1px solid rgba(148,163,184,.12);border-radius:12px;padding:10px 12px}
.cd-chip-label{color:#94A3B8;font-size:.7rem;font-weight:700;margin:0 0 4px}
.cd-chip-value{color:#F8FAFC;font-size:1rem;font-weight:800;margin:0}
.note-box{font-size:.85rem;color:#CBD5E1;line-height:1.6;font-weight:600; padding:12px;background:linear-gradient(160deg,rgba(15,23,42,.92),rgba(15,23,42,.74));border-radius:12px;margin-top:12px; border:1px solid rgba(99,102,241,.14); border-left:4px solid #6366F1}
.spotlight-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:0 0 16px}
.spotlight-card{background:linear-gradient(160deg,rgba(15,23,42,.9),rgba(15,23,42,.72));border:1px solid rgba(148,163,184,.12);border-radius:14px;padding:12px 14px}
.spotlight-label{color:#94A3B8;font-size:.72rem;font-weight:700;margin:0 0 6px}
.spotlight-value{color:#F8FAFC;font-size:1.28rem;font-weight:900;line-height:1.15;margin:0}
.spotlight-sub{color:#CBD5E1;font-size:.78rem;font-weight:600;margin:6px 0 0}
.section-pill{display:inline-flex;align-items:center;gap:6px;padding:5px 11px;border-radius:999px;font-size:.74rem;font-weight:800;border:1px solid transparent}
.pill-green{background:rgba(99,217,162,.12);border-color:rgba(99,217,162,.28);color:#B8F1D5}
.pill-red{background:rgba(255,143,150,.12);border-color:rgba(255,143,150,.28);color:#FFD2D7}
.pill-amber{background:rgba(246,195,94,.12);border-color:rgba(246,195,94,.28);color:#F8DE9A}
.ownership-stack{display:flex;flex-direction:column;gap:10px;margin:6px 0 0}
.ownership-row{display:flex;justify-content:space-between;align-items:center;padding:11px 12px;border-radius:12px;background:linear-gradient(160deg,rgba(15,23,42,.9),rgba(15,23,42,.72));border:1px solid rgba(148,163,184,.12)}
.ownership-left{display:flex;align-items:center;gap:10px;color:#E5E7EB;font-weight:700}
.ownership-dot{width:10px;height:10px;border-radius:999px;display:inline-block}
.ownership-right{color:#F8FAFC;font-weight:900}
.hero-bento{max-width:960px;margin:0 auto 18px;display:grid;grid-template-columns:1.55fr .95fr;gap:14px}
.hero-card{background:
    linear-gradient(180deg,rgba(99,102,241,.07),rgba(99,102,241,0) 34%),
    linear-gradient(160deg,rgba(10,14,24,.96),rgba(16,24,39,.88));
    border:1px solid rgba(99,102,241,.16);border-radius:18px;padding:18px 18px 16px;box-shadow:0 16px 32px rgba(2,6,23,.16)}
.hero-kicker{display:inline-flex;align-items:center;gap:8px;padding:5px 10px;border-radius:999px;background:rgba(99,102,241,.12);border:1px solid rgba(99,102,241,.22);color:#C7D2FE;font-size:.72rem;font-weight:900;letter-spacing:.02em}
.hero-headline{font-size:1.1rem;font-weight:900;color:#F8FAFC;line-height:1.4;margin:14px 0 8px}
.hero-copy{color:#CBD5E1;font-size:.9rem;line-height:1.75;font-weight:500}
.meta-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-top:16px}
.meta-item{padding:11px 12px;border-radius:12px;background:rgba(255,255,255,.03);border:1px solid rgba(148,163,184,.12)}
.meta-label{color:#94A3B8;font-size:.7rem;font-weight:800;margin:0 0 5px}
.meta-value{color:#F8FAFC;font-size:.98rem;font-weight:800;line-height:1.35;margin:0}
.signal-stack{display:flex;flex-direction:column;gap:10px}
.signal-card{padding:12px 13px;border-radius:14px;background:linear-gradient(160deg,rgba(15,23,42,.9),rgba(15,23,42,.74));border:1px solid rgba(148,163,184,.12)}
.signal-label{color:#94A3B8;font-size:.7rem;font-weight:800;margin:0 0 6px}
.signal-value{color:#F8FAFC;font-size:1.15rem;font-weight:900;line-height:1.15;margin:0}
.signal-sub{color:#CBD5E1;font-size:.78rem;font-weight:600;margin:6px 0 0}
.coverage-wrap{max-width:960px;margin:0 auto 18px}
.coverage-grid{display:flex;flex-wrap:wrap;gap:8px}
.coverage-pill{display:inline-flex;align-items:center;gap:7px;padding:8px 11px;border-radius:999px;font-size:.77rem;font-weight:800;border:1px solid rgba(148,163,184,.14);background:rgba(255,255,255,.03);color:#E5E7EB}
.coverage-pill::before{content:'';width:8px;height:8px;border-radius:999px;display:inline-block}
.coverage-ok::before{background:#63D9A2;box-shadow:0 0 12px rgba(99,217,162,.55)}
.coverage-warn::before{background:#F6C35E;box-shadow:0 0 12px rgba(246,195,94,.45)}
.coverage-miss::before{background:#FF8F96;box-shadow:0 0 12px rgba(255,143,150,.45)}
.section-nav{max-width:960px;margin:0 auto 22px;display:flex;flex-wrap:wrap;gap:8px}
.nav-chip{display:inline-flex;align-items:center;gap:8px;padding:8px 11px;border-radius:999px;background:rgba(255,255,255,.03);border:1px solid rgba(148,163,184,.12);color:#CBD5E1;font-size:.78rem;font-weight:800}
.nav-chip b{color:#C7D2FE;font-size:.72rem}
.n-item{padding:14px 16px;border-radius:14px;background:
    linear-gradient(160deg,rgba(15,23,42,.9),rgba(15,23,42,.72));
    border:1px solid rgba(148,163,184,.12);margin:0 0 10px;transition:all .28s ease}
.n-item:hover{transform:translateY(-2px);border-color:rgba(99,102,241,.24);box-shadow:0 12px 24px rgba(2,6,23,.18)}
.n-title{display:block;color:#F8FAFC !important;font-size:.96rem;font-weight:800;line-height:1.55;text-decoration:none !important}
.n-title:hover{color:#C7D2FE !important}
.n-meta{margin-top:8px;color:#94A3B8;font-size:.76rem;font-weight:700}
.hero-bento{display:none}
.invest-hero{max-width:960px;margin:0 auto 20px;display:grid;grid-template-columns:1.45fr .95fr;gap:14px}
.invest-card{background:
    linear-gradient(180deg,rgba(99,102,241,.08),rgba(99,102,241,0) 34%),
    linear-gradient(160deg,rgba(10,14,24,.96),rgba(16,24,39,.88));
    border:1px solid rgba(99,102,241,.16);border-radius:18px;padding:18px 18px 16px;box-shadow:0 16px 32px rgba(2,6,23,.16)}
.invest-kicker{display:inline-flex;align-items:center;gap:8px;padding:5px 10px;border-radius:999px;background:rgba(99,102,241,.12);border:1px solid rgba(99,102,241,.22);color:#C7D2FE;font-size:.72rem;font-weight:900}
.invest-title{font-size:1.14rem;font-weight:900;color:#F8FAFC;line-height:1.45;margin:14px 0 8px}
.invest-copy{color:#CBD5E1;font-size:.92rem;line-height:1.7;font-weight:500}
.invest-points{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}
.invest-point{display:inline-flex;align-items:center;gap:6px;padding:7px 10px;border-radius:999px;background:rgba(255,255,255,.03);border:1px solid rgba(148,163,184,.12);color:#E5E7EB;font-size:.78rem;font-weight:800}
.coverage-pill,.nav-chip,.invest-point{transition:transform .22s ease,border-color .22s ease,background .22s ease,box-shadow .22s ease}
.coverage-pill:hover,.nav-chip:hover,.invest-point:hover{transform:translateY(-2px);border-color:rgba(99,102,241,.28);background:rgba(255,255,255,.05);box-shadow:0 12px 24px rgba(2,6,23,.18)}
.story-board{max-width:960px;margin:0 auto 22px}
.story-board__head{display:flex;justify-content:space-between;align-items:flex-end;gap:12px;flex-wrap:wrap;margin-bottom:12px}
.story-board__eyebrow{display:inline-flex;align-items:center;gap:8px;padding:5px 10px;border-radius:999px;background:rgba(99,102,241,.12);border:1px solid rgba(99,102,241,.22);color:#C7D2FE;font-size:.72rem;font-weight:900;letter-spacing:.05em;margin:0}
.story-board__copy{color:#CBD5E1;font-size:.88rem;line-height:1.7;font-weight:600;max-width:680px;margin:0}
.story-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}
.story-card{position:relative;overflow:hidden;padding:15px 15px 14px;border-radius:16px;background:linear-gradient(180deg,rgba(19,28,45,.98),rgba(15,23,42,.92));border:1px solid rgba(148,163,184,.12);box-shadow:0 14px 28px rgba(2,6,23,.14);transition:transform .24s ease,border-color .24s ease,box-shadow .24s ease}
.story-card::before{content:'';position:absolute;inset:0 0 auto 0;height:42%;background:linear-gradient(180deg,rgba(255,255,255,.05),rgba(255,255,255,0));opacity:.85;pointer-events:none}
.story-card:hover{transform:translateY(-3px);border-color:rgba(99,102,241,.26);box-shadow:0 18px 32px rgba(2,6,23,.2)}
.story-card--accent{background:linear-gradient(180deg,rgba(99,102,241,.08),rgba(99,102,241,0) 34%),linear-gradient(180deg,rgba(19,28,45,.98),rgba(15,23,42,.92))}
.story-card--positive{background:linear-gradient(180deg,rgba(99,217,162,.08),rgba(99,217,162,0) 34%),linear-gradient(180deg,rgba(19,28,45,.98),rgba(15,23,42,.92))}
.story-card--negative{background:linear-gradient(180deg,rgba(255,143,150,.08),rgba(255,143,150,0) 34%),linear-gradient(180deg,rgba(19,28,45,.98),rgba(15,23,42,.92))}
.story-card--warning{background:linear-gradient(180deg,rgba(246,195,94,.08),rgba(246,195,94,0) 34%),linear-gradient(180deg,rgba(19,28,45,.98),rgba(15,23,42,.92))}
.story-kicker{color:#94A3B8;font-size:.72rem;font-weight:800;letter-spacing:.03em;text-transform:uppercase;margin:0 0 8px}
.story-value{color:#F8FAFC;font-size:1.16rem;font-weight:900;line-height:1.2;margin:0 0 6px}
.story-note{color:#CBD5E1;font-size:.8rem;line-height:1.55;font-weight:600;min-height:40px;margin:0 0 12px}
.story-visual{display:flex;align-items:center;min-height:92px}
.story-foot{display:flex;align-items:center;justify-content:space-between;gap:8px;color:#94A3B8;font-size:.72rem;font-weight:700;margin-top:10px;padding-top:10px;border-top:1px solid rgba(148,163,184,.12)}
.story-empty{display:flex;align-items:center;justify-content:center;width:100%;min-height:82px;border-radius:12px;border:1px dashed rgba(148,163,184,.18);background:rgba(255,255,255,.02);color:#94A3B8;font-size:.78rem;font-weight:700}
.story-sparkline{width:100%;height:84px;display:block}
.story-sparkline__baseline{stroke:rgba(148,163,184,.16);stroke-width:1}
.story-sparkline__line{fill:none;stroke-width:3.2;stroke-linecap:round;stroke-linejoin:round;filter:drop-shadow(0 0 10px rgba(148,163,184,.14))}
.story-sparkline__end{fill:#0F172A;stroke-width:2}
.story-range-shell{width:100%;padding-top:8px}
.story-range-track{position:relative;height:20px;border-radius:999px;background:linear-gradient(90deg,rgba(255,143,150,.24),rgba(246,195,94,.2),rgba(99,217,162,.24));border:1px solid rgba(148,163,184,.12);overflow:visible}
.story-range-band{position:absolute;top:2px;bottom:2px;border-radius:999px;background:linear-gradient(90deg,rgba(99,102,241,.18),rgba(99,217,162,.2));box-shadow:0 0 18px rgba(99,102,241,.18)}
.story-range-marker{position:absolute;top:-10px;transform:translateX(-50%);display:flex;flex-direction:column;align-items:center;gap:3px}
.story-range-marker::before{content:'';width:12px;height:12px;border-radius:999px;border:2px solid #F8FAFC;box-shadow:0 0 0 4px rgba(15,23,42,.4)}
.story-range-marker b{color:#E5E7EB;font-size:.65rem;line-height:1;font-weight:800}
.story-range-marker i{color:#94A3B8;font-size:.64rem;line-height:1;font-style:normal;font-weight:700}
.story-range-marker--low::before{background:#94A3B8}
.story-range-marker--median::before{background:#63D9A2}
.story-range-marker--high::before{background:#CBD5E1}
.story-range-marker--current::before{background:#F6C35E}
.consensus-corridor{padding:16px 16px 14px;border-radius:18px;background:linear-gradient(180deg,rgba(99,102,241,.08),rgba(99,102,241,0) 34%),linear-gradient(180deg,rgba(19,28,45,.98),rgba(15,23,42,.92));border:1px solid rgba(99,102,241,.20);box-shadow:0 16px 32px rgba(2,6,23,.16)}
.consensus-corridor__head{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap;margin-bottom:16px}
.consensus-corridor__kicker{color:#94A3B8;font-size:.72rem;font-weight:800;letter-spacing:.04em;text-transform:uppercase;margin:0 0 6px}
.consensus-corridor__title{color:#F8FAFC;font-size:1rem;font-weight:900;line-height:1.4;margin:0}
.consensus-corridor__stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;flex:1 1 320px}
.consensus-corridor__stat{padding:10px 11px;border-radius:14px;background:rgba(255,255,255,.03);border:1px solid rgba(148,163,184,.12)}
.consensus-corridor__stat p{color:#94A3B8;font-size:.68rem;font-weight:800;margin:0 0 5px}
.consensus-corridor__stat strong{display:block;color:#F8FAFC;font-size:.98rem;font-weight:900;line-height:1.2}
.consensus-corridor__stat span{display:block;color:#CBD5E1;font-size:.68rem;font-weight:700;line-height:1.35;margin-top:4px}
.consensus-corridor__stage{padding:4px 2px 0}
.consensus-corridor__labels{position:relative;min-height:44px}
.consensus-corridor__labels--bottom{min-height:50px;margin-top:16px}
.consensus-corridor__tag{position:absolute;transform:translateX(-50%);display:flex;flex-direction:column;align-items:center;gap:2px;text-align:center;white-space:nowrap}
.consensus-corridor__tag b{color:var(--corridor-tone);font-size:.67rem;font-weight:900;line-height:1}
.consensus-corridor__tag span{color:#CBD5E1;font-size:.68rem;font-weight:700;line-height:1.2}
.consensus-corridor__tag--top{top:0}
.consensus-corridor__tag--bottom{top:0}
.consensus-corridor__track{position:relative;height:34px}
.consensus-corridor__rail{position:absolute;left:0;right:0;top:12px;height:10px;border-radius:999px;background:rgba(148,163,184,.10);border:1px solid rgba(148,163,184,.12)}
.consensus-corridor__band{position:absolute;top:7px;height:20px;border-radius:999px;background:linear-gradient(90deg,rgba(142,164,255,.22),rgba(99,217,162,.18));border:1px solid rgba(142,164,255,.24);box-shadow:0 0 18px rgba(99,102,241,.14)}
.consensus-corridor__band--focus{top:3px;height:28px;background:linear-gradient(90deg,rgba(56,189,248,.18),rgba(99,217,162,.22));border-color:rgba(99,217,162,.24)}
.consensus-corridor__dot{position:absolute;top:4px;transform:translateX(-50%);width:26px;height:26px;border-radius:999px;background:rgba(15,23,42,.94);border:1px solid rgba(248,250,252,.14);box-shadow:0 8px 18px rgba(2,6,23,.18)}
.consensus-corridor__dot::before{content:'';position:absolute;inset:6px;border-radius:999px;background:var(--corridor-tone)}
.consensus-corridor__dot--focus{top:0;width:34px;height:34px;border-color:rgba(246,195,94,.24);box-shadow:0 0 0 1px rgba(246,195,94,.18),0 12px 22px rgba(2,6,23,.22)}
.consensus-corridor__dot--focus::before{inset:7px}
.consensus-corridor__axis{display:flex;justify-content:space-between;gap:12px;color:#94A3B8;font-size:.7rem;font-weight:700;margin-top:10px}
.consensus-corridor__legend{display:flex;flex-wrap:wrap;gap:10px 14px;color:#CBD5E1;font-size:.72rem;font-weight:700;margin-top:12px}
.consensus-corridor__legend span{display:inline-flex;align-items:center;gap:7px}
.consensus-corridor__legend-dot{width:8px;height:8px;border-radius:999px;display:inline-block}
.consensus-corridor__legend-dot--slate{background:#94A3B8;box-shadow:0 0 10px rgba(148,163,184,.35)}
.consensus-corridor__legend-dot--green{background:#63D9A2;box-shadow:0 0 10px rgba(99,217,162,.35)}
.consensus-corridor__legend-dot--gold{background:#F6C35E;box-shadow:0 0 10px rgba(246,195,94,.35)}
.invest-grid{display:grid;grid-template-columns:1fr;gap:10px}
.invest-metric{padding:13px 14px;border-radius:14px;background:linear-gradient(160deg,rgba(15,23,42,.9),rgba(15,23,42,.74));border:1px solid rgba(148,163,184,.12)}
.invest-label{color:#94A3B8;font-size:.72rem;font-weight:800;margin:0 0 6px}
.invest-value{color:#F8FAFC;font-size:1.22rem;font-weight:900;line-height:1.15;margin:0}
.invest-sub{color:#CBD5E1;font-size:.78rem;font-weight:600;line-height:1.5;margin:6px 0 0}
.score-pillar-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:18px 0 0}
.score-pillar{background:linear-gradient(160deg,rgba(15,23,42,.9),rgba(15,23,42,.72));border:1px solid rgba(148,163,184,.12);border-radius:14px;padding:13px 14px}
.score-pillar-label{color:#94A3B8;font-size:.72rem;font-weight:800;margin:0 0 6px}
.score-pillar-value{color:#F8FAFC;font-size:1.28rem;font-weight:900;margin:0}
.score-pillar-sub{color:#CBD5E1;font-size:.76rem;font-weight:600;line-height:1.45;margin:6px 0 0}
.section-lead{color:#CBD5E1;font-size:.88rem;line-height:1.7;font-weight:600;margin:-6px 0 14px}
.cluster-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-top:16px}
.cluster-card{padding:14px 15px;border-radius:16px;background:linear-gradient(160deg,rgba(15,23,42,.92),rgba(15,23,42,.76));border:1px solid rgba(148,163,184,.12)}
.cluster-title{color:#F8FAFC;font-size:.96rem;font-weight:900;margin:0 0 6px}
.cluster-sub{color:#94A3B8;font-size:.76rem;font-weight:700;margin:0 0 10px}
.compact-chip-row{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0 0}
.compact-chip{display:inline-flex;align-items:center;gap:6px;padding:7px 10px;border-radius:999px;background:rgba(255,255,255,.04);border:1px solid rgba(148,163,184,.12);color:#E5E7EB;font-size:.76rem;font-weight:800}
.compact-chip b{color:#F8FAFC}
.consensus-scale{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px;margin:16px 0 14px}
.consensus-step{padding:12px 8px;border-radius:14px;background:linear-gradient(160deg,rgba(15,23,42,.92),rgba(15,23,42,.74));border:1px solid rgba(148,163,184,.12);text-align:center}
.consensus-step strong{display:block;color:#E5E7EB;font-size:.78rem;font-weight:900;line-height:1.35}
.consensus-step span{display:block;color:#94A3B8;font-size:.68rem;font-weight:700;margin-top:4px}
.consensus-step-label{display:block;color:#CBD5E1;font-size:.72rem;font-weight:800;line-height:1.3}
.consensus-step-score{display:block;color:#94A3B8;font-size:.68rem;font-weight:700;margin-top:4px}
.consensus-step.active{box-shadow:0 0 0 1px rgba(248,250,252,.05) inset,0 12px 24px rgba(2,6,23,.18)}
.consensus-step.active.buy{border-color:rgba(99,217,162,.34)}
.consensus-step.active.hold{border-color:rgba(246,195,94,.34)}
.consensus-step.active.sell{border-color:rgba(255,143,150,.34)}
.range-strip{position:relative;height:14px;border-radius:999px;background:linear-gradient(90deg,rgba(255,143,150,.24),rgba(246,195,94,.2),rgba(99,217,162,.24));border:1px solid rgba(148,163,184,.12);overflow:hidden;margin:14px 0 12px}
.range-marker{position:absolute;top:-5px;width:14px;height:24px;border-radius:999px;border:2px solid #F8FAFC;transform:translateX(-50%);box-shadow:0 0 0 5px rgba(15,23,42,.38)}
.range-marker.low{background:#94A3B8}
.range-marker.high{background:#CBD5E1}
.range-marker.mean{background:#38BDF8}
.range-marker.median{background:#63D9A2}
.range-marker.current{background:#F6C35E}
.range-legend{display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:8px}
.range-legend-item{padding:10px 11px;border-radius:12px;background:rgba(255,255,255,.03);border:1px solid rgba(148,163,184,.12)}
.range-legend-item p{margin:0}
.range-legend-label{color:#94A3B8;font-size:.7rem;font-weight:800}
.range-legend-value{color:#F8FAFC;font-size:.92rem;font-weight:900;margin-top:4px}
.range-legend-sub{color:#CBD5E1;font-size:.72rem;font-weight:700;margin-top:4px}
.stack-col{display:flex;flex-direction:column;gap:12px}
.target-mini-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;margin-top:12px}
.target-mini-card{padding:12px 13px;border-radius:14px;background:linear-gradient(160deg,rgba(15,23,42,.9),rgba(15,23,42,.72));border:1px solid rgba(148,163,184,.12)}
.target-mini-label{color:#94A3B8;font-size:.72rem;font-weight:800;margin:0 0 6px}
.target-mini-value{color:#F8FAFC;font-size:1rem;font-weight:900;margin:0}
.target-mini-sub{color:#CBD5E1;font-size:.72rem;font-weight:700;margin:6px 0 0}
.insight-shell{padding:14px 15px;border-radius:16px;background:linear-gradient(180deg,rgba(99,102,241,.08),rgba(99,102,241,0) 34%),linear-gradient(160deg,rgba(10,14,24,.96),rgba(16,24,39,.88));border:1px solid rgba(99,102,241,.16);box-shadow:0 16px 32px rgba(2,6,23,.16)}
.insight-shell .cluster-title{margin-bottom:4px}
.insight-shell .cluster-sub{margin-bottom:12px}
.metric-rail-card{padding:14px 15px;border-radius:16px;background:linear-gradient(160deg,rgba(15,23,42,.92),rgba(15,23,42,.76));border:1px solid rgba(148,163,184,.12)}
.metric-rail-row{margin-top:12px}
.metric-rail-head{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:7px}
.metric-rail-head span{color:#CBD5E1;font-size:.78rem;font-weight:800}
.metric-rail-head strong{color:#F8FAFC;font-size:.82rem;font-weight:900}
.metric-rail-track{height:8px;border-radius:999px;background:rgba(148,163,184,.12);overflow:hidden}
.metric-rail-fill{height:100%;border-radius:999px}
.metric-rail-note{color:#94A3B8;font-size:.72rem;font-weight:700;margin:6px 0 0}
.spotlight-grid.tight{grid-template-columns:repeat(auto-fit,minmax(130px,1fr))}
@media(max-width:900px){
  .hero-bento{grid-template-columns:1fr}
  .meta-grid{grid-template-columns:1fr}
  .invest-hero{grid-template-columns:1fr}
  .story-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
  .consensus-corridor__stats{grid-template-columns:1fr}
  .cluster-grid{grid-template-columns:1fr}
  .consensus-scale{grid-template-columns:repeat(2,minmax(0,1fr))}
  .target-mini-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
}
@media(max-width:640px){
  .story-grid{grid-template-columns:1fr}
  .story-board__copy{font-size:.82rem}
  .consensus-corridor{padding:14px 14px 12px}
  .consensus-corridor__labels{min-height:50px}
  .consensus-corridor__tag b{font-size:.64rem}
  .consensus-corridor__tag span{font-size:.64rem}
}
</style>
""".replace("__SIGL_COMPANY_THEME__", COMPANY_DETAILS_THEME_OVERRIDES)

# ═══════════════════════════════════════════════════════════════
# 🏗️ 메인 렌더링
# ═══════════════════════════════════════════════════════════════

def render_company_details(ticker_str: str, key_prefix: str = "company"):
    st.markdown(CSS, unsafe_allow_html=True)

    with st.spinner(f"{ticker_str} 기업 정보를 정리하고 있습니다..."):
        bundle = _fetch_company_bundle(ticker_str)
        info = bundle.get("info") or {}
        if bundle.get("rate_limited"):
            st.warning("Yahoo 요청이 잠시 제한되었습니다. 잠시 후 다시 시도하거나 뉴스 같은 부가 데이터를 나중에 불러와 주세요."); return
        if bundle.get("error") and not info:
            st.error(f"데이터를 불러오지 못했습니다: {bundle.get('error')}"); return
        if not info or 'shortName' not in info:
            st.error("❌ 유효하지 않은 종목이거나 데이터가 없습니다."); return

        fin = bundle.get("fin")
        q_fin = bundle.get("q_fin")
        bs = bundle.get("bs")
        cf = bundle.get("cf")

        sector, industry = info.get('sector', 'N/A'), info.get('industry', 'N/A')
        price = info.get('currentPrice') or info.get('regularMarketPrice') or 0
        prev_c = info.get('previousClose') or price or 1
        day_chg = ((price - prev_c) / prev_c * 100) if prev_c else 0
        chg_c, chg_s = ("#63D9A2" if day_chg >= 0 else "#FF8F96"), ("+" if day_chg >= 0 else "")

        if price == 0: st.warning("⚠️ 현재가를 불러올 수 없습니다. 일부 데이터가 정확하지 않을 수 있습니다.")

        ocf = info.get('operatingCashflow')
        fcf = info.get('freeCashflow')
        if cf is not None and not cf.empty:
            try:
                ocf_series = _get_row_series(cf, CFO_ALIASES)
                if (ocf is None or pd.isna(ocf)) and not ocf_series.empty:
                    ocf = ocf_series.sort_index(ascending=False).iloc[0]
            except Exception:
                pass
            try:
                fcf_series = _get_row_series(cf, FCF_ALIASES)
                if (fcf is None or pd.isna(fcf)) and not fcf_series.empty:
                    fcf = fcf_series.sort_index(ascending=False).iloc[0]
            except Exception:
                pass

        cagr_rev, yr_rev = _calc_cagr_with_years(fin, REV_ALIASES)
        cagr_ni,  yr_ni  = _calc_cagr_with_years(fin, NI_ALIASES)
        cagr_eps, yr_eps = _calc_cagr_with_years(fin, EPS_ALIASES)

        ann_rev_g, qoq_rev_g, yoy_q_rev_g = "N/A", "N/A", info.get('revenueGrowth')
        try:
            rv_ann, _ = _annual_values(fin, REV_ALIASES)
            if len(rv_ann) >= 2 and rv_ann[1] > 0: ann_rev_g = (rv_ann[0] / rv_ann[1]) - 1
            q_rs = _get_row_series(q_fin, REV_ALIASES).sort_index(ascending=False)
            if len(q_rs) >= 2 and q_rs.iloc[1] > 0: qoq_rev_g = (q_rs.iloc[0] / q_rs.iloc[1]) - 1
            if len(q_rs) >= 5 and q_rs.iloc[4] > 0: yoy_q_rev_g = (q_rs.iloc[0] / q_rs.iloc[4]) - 1
        except Exception: pass

        dividend_yield = _resolve_dividend_yield(info, price)
        peg_resolved = _resolve_peg_ratio(info, cagr_eps, cagr_ni, yoy_q_rev_g, ann_rev_g)
        target_mean = _first_valid_number(info.get('targetMeanPrice'))
        target_median = _first_valid_number(info.get('targetMedianPrice'))
        target_high = _first_valid_number(info.get('targetHighPrice'))
        target_low = _first_valid_number(info.get('targetLowPrice'))
        upside_ref_top = target_median if target_median is not None else target_mean
        upside_pct_top = ((upside_ref_top - price) / price * 100) if isinstance(upside_ref_top, (int, float)) and price else None

    # ═══════════════════════════════════════════════════
    # 🏷️ 헤더
    # ═══════════════════════════════════════════════════
    header_html = (
        f'<div class="header-wrap">'
        f'<div><span style="font-size:1.8rem;font-weight:900;color:#ffffff">{_esc(info.get("shortName", ticker_str))}</span>'
        f'<span style="font-size:1.1rem;color:#adbac7;margin-left:8px;font-weight:800">({_esc(ticker_str)})</span><br>'
        f'<span style="font-size:.9rem;color:#8b949e;font-weight:700">{_esc(sector)} · {_esc(industry)}</span></div>'
        f'<div style="text-align:right"><span style="font-size:2.2rem;font-weight:900;color:{chg_c}">${price:,.2f}</span><br>'
        f'<span style="font-size:1.1rem;font-weight:800;color:{chg_c}">{chg_s}{day_chg:.2f}% 오늘</span></div></div>'
    )
    st.markdown(header_html, unsafe_allow_html=True)
    st.markdown(
        """
        <div class="note-box" style="max-width:960px;margin:0 auto 18px;">
            데이터는 Yahoo Finance 기반이며 일부 항목은 추정치 또는 지연 데이터일 수 있습니다.
        </div>
        """,
        unsafe_allow_html=True,
    )
    summary_items = [
        ("시가총액", _fmt_num(info.get('marketCap'))),
        ("PEG 비율", f"{peg_resolved:.2f}" if isinstance(peg_resolved, (int, float)) else "N/A"),
        ("배당수익률", _fmt_pct(dividend_yield)),
        ("목표가 여력", f"{upside_pct_top:+.1f}%" if isinstance(upside_pct_top, (int, float)) else "N/A"),
    ]
    summary_html = "".join([
        f"<div class='cd-chip'><p class='cd-chip-label'>{label}</p><p class='cd-chip-value'>{value}</p></div>"
        for label, value in summary_items
    ])
    st.markdown(
        f"""
        <div class="cd-summary">
            <div class="cd-summary-grid">{summary_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    employees = info.get('fullTimeEmployees')
    exchange = info.get('fullExchangeName') or info.get('exchange') or "N/A"
    country = info.get('country') or "N/A"
    city = info.get('city') or ""
    website = info.get('website') or ""
    summary_text = (info.get('longBusinessSummary') or "").strip()
    summary_preview = _esc(summary_text[:240] + ("..." if len(summary_text) > 240 else "")) if summary_text else "사업 개요 데이터가 아직 충분하지 않습니다."
    headquarters = f"{city}, {country}" if city else country
    analyst_count = info.get('numberOfAnalystOpinions') or 0
    inst_hold = info.get('heldPercentInstitutions')

    coverage_specs = [
        ("연간 재무", fin is not None and not fin.empty),
        ("분기 재무", q_fin is not None and not q_fin.empty),
        ("대차대조표", bs is not None and not bs.empty),
        ("현금흐름", cf is not None and not cf.empty),
        ("애널리스트", analyst_count > 0),
        ("소유구조", any(info.get(k) is not None for k in ['heldPercentInstitutions', 'heldPercentInsiders', 'sharesOutstanding'])),
    ]
    coverage_html = "".join(
        f"<span class='coverage-pill {'coverage-ok' if ok else 'coverage-warn'}'>{label}</span>"
        for label, ok in coverage_specs
    )
    nav_labels = [
        "01 성장", "02 수익성", "03 실적", "04 성장성", "05 재무건전",
        "06 거래량", "07 변동성", "08 밸류에이션", "09 애널리스트",
        "10 지분구조", "11 옵션", "12 공매도", "13 뉴스"
    ]
    nav_html = "".join(
        f"<span class='nav-chip'><b>{label.split()[0]}</b>{label.split()[1]}</span>"
        for label in nav_labels
    )
    hero_html = (
        f"<div class='hero-bento'>"
        f"<div class='hero-card'>"
        f"<span class='hero-kicker'>회사 브리프</span>"
        f"<div class='hero-headline'>{_esc(info.get('shortName', ticker_str))}의 사업 구조와 핵심 지표를 빠르게 읽을 수 있도록 요약했습니다.</div>"
        f"<div class='hero-copy'>{summary_preview}</div>"
        f"<div class='meta-grid'>"
        f"<div class='meta-item'><p class='meta-label'>본사</p><p class='meta-value'>{_esc(headquarters)}</p></div>"
        f"<div class='meta-item'><p class='meta-label'>상장 거래소</p><p class='meta-value'>{_esc(exchange)}</p></div>"
        f"<div class='meta-item'><p class='meta-label'>직원 수</p><p class='meta-value'>{_fmt_num(employees, False) if employees else 'N/A'}</p></div>"
        f"<div class='meta-item'><p class='meta-label'>웹사이트</p><p class='meta-value'>{_esc(website.replace('https://', '').replace('http://', '')[:34]) if website else 'N/A'}</p></div>"
        f"</div>"
        f"</div>"
        f"<div class='signal-stack'>"
        f"<div class='signal-card'><p class='signal-label'>현금 창출력</p><p class='signal-value'>{_fmt_num(fcf)}</p><p class='signal-sub'>잉여현금흐름 {'' if fcf is not None else '데이터 부족'}</p></div>"
        f"<div class='signal-card'><p class='signal-label'>영업활동 현금흐름</p><p class='signal-value'>{_fmt_num(ocf)}</p><p class='signal-sub'>본업 현금흐름</p></div>"
        f"<div class='signal-card'><p class='signal-label'>애널리스트 커버리지</p><p class='signal-value'>{analyst_count or 0}명</p><p class='signal-sub'>평균 목표가 {f'${target_mean:,.2f}' if isinstance(target_mean, (int, float)) else 'N/A'} · 기관보유 {_fmt_pct(inst_hold) if inst_hold is not None else 'N/A'}</p></div>"
        f"</div>"
        f"</div>"
    )
    st.markdown(hero_html, unsafe_allow_html=True)
    st.markdown(f"<div class='coverage-wrap'><div class='coverage-grid'>{coverage_html}</div></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='section-nav'>{nav_html}</div>", unsafe_allow_html=True)

    upside_ref = upside_ref_top
    short_float_top = info.get('shortPercentOfFloat')
    debt_ratio_top = info.get('debtToEquity')

    thesis_points = []
    if isinstance(cagr_rev, float):
        thesis_points.append("매출 성장 유지" if cagr_rev > 0.12 else "저성장 구간" if cagr_rev > 0 else "매출 둔화")
    if isinstance(fcf, (int, float)):
        thesis_points.append("잉여현금흐름 플러스" if fcf > 0 else "잉여현금흐름 마이너스")
    if isinstance(debt_ratio_top, (int, float)):
        thesis_points.append("저레버리지" if debt_ratio_top < 80 else "레버리지 부담" if debt_ratio_top > 150 else "레버리지 보통")
    if isinstance(upside_pct_top, (int, float)):
        thesis_points.append(f"스트리트 여력 {upside_pct_top:+.0f}%")
    if isinstance(short_float_top, (int, float)) and short_float_top > 0.10:
        thesis_points.append(f"숏비중 {_fmt_pct(short_float_top)}")
    thesis_line = " · ".join(thesis_points[:4]) if thesis_points else "핵심 투자 포인트를 계산 중입니다."

    cash_flow_label = "플러스" if isinstance(fcf, (int, float)) and fcf > 0 else "부담" if isinstance(fcf, (int, float)) and fcf < 0 else "확인 필요"
    positioning_note = f"기관보유 {_fmt_pct(inst_hold) if inst_hold is not None else 'N/A'}"
    if isinstance(short_float_top, (int, float)):
        positioning_note += f" · 공매도 {_fmt_pct(short_float_top)}"

    invest_points_html = "".join([f"<span class='invest-point'>{_esc(point)}</span>" for point in thesis_points[:5]])
    invest_html = (
        f"<div class='invest-hero'>"
        f"<div class='invest-card'>"
        f"<span class='invest-kicker'>투자 스냅샷</span>"
        f"<div class='invest-title'>{_esc(info.get('shortName', ticker_str))} 한줄 요약: {thesis_line}</div>"
        f"<div class='invest-copy'>{summary_preview}</div>"
        f"<div class='invest-points'>{invest_points_html}</div>"
        f"</div>"
        f"<div class='invest-grid'>"
        f"<div class='invest-metric'><p class='invest-label'>목표가 기대여력</p><p class='invest-value'>{f'{upside_pct_top:+.1f}%' if isinstance(upside_pct_top, (int, float)) else 'N/A'}</p><p class='invest-sub'>중앙값·평균 목표가 기준 기대 여력</p></div>"
        f"<div class='invest-metric'><p class='invest-label'>현금흐름 품질</p><p class='invest-value'>{cash_flow_label}</p><p class='invest-sub'>영업현금흐름 {_fmt_num(ocf)} · 잉여현금흐름 {_fmt_num(fcf)}</p></div>"
        f"<div class='invest-metric'><p class='invest-label'>수급 포지셔닝</p><p class='invest-value'>{_fmt_pct(inst_hold) if inst_hold is not None else 'N/A'}</p><p class='invest-sub'>{positioning_note}</p></div>"
        f"</div>"
        f"</div>"
    )
    st.markdown(invest_html, unsafe_allow_html=True)

    revenue_story_raw, revenue_story_dates = _annual_values(fin, REV_ALIASES)
    profit_story_raw, profit_story_dates = _annual_values(fin, NI_ALIASES)
    cash_story_raw, cash_story_dates = _annual_values(cf, FCF_ALIASES)
    cash_story_name = "잉여현금흐름"
    if not cash_story_raw:
        cash_story_raw, cash_story_dates = _annual_values(cf, CFO_ALIASES)
        cash_story_name = "영업현금흐름"

    revenue_story_values, revenue_story_labels = _prepare_story_series(revenue_story_raw, revenue_story_dates)
    profit_story_values, profit_story_labels = _prepare_story_series(profit_story_raw, profit_story_dates)
    cash_story_values, cash_story_labels = _prepare_story_series(cash_story_raw, cash_story_dates)

    cash_total = _first_valid_number(info.get('totalCash'))
    debt_total = _first_valid_number(info.get('totalDebt'))
    cash_cover = cash_total / debt_total if cash_total is not None and debt_total not in (None, 0) else None
    target_reference = target_median if isinstance(target_median, (int, float)) else target_mean

    revenue_note = f"3년 CAGR {_fmt_cagr(cagr_rev)}" if cagr_rev is not None else "최근 연간 매출 흐름"
    profit_note = f"순이익률 {_fmt_pct(info.get('profitMargins'))}" if info.get('profitMargins') is not None else "최근 연간 순이익 흐름"
    cash_note = f"현금/부채 {cash_cover:.2f}x" if isinstance(cash_cover, (int, float)) else "현금 창출 체력 점검"
    street_note = f"중간 목표가 {upside_pct_top:+.1f}%" if isinstance(upside_pct_top, (int, float)) else f"애널리스트 {analyst_count}명"

    revenue_visual = _sparkline_svg(revenue_story_values, "#7AA2FF", "rgba(122,162,255,.14)")
    profit_visual = _sparkline_svg(
        profit_story_values,
        "#63D9A2" if not profit_story_values or profit_story_values[-1] >= 0 else "#FF8F96",
        "rgba(99,217,162,.12)" if not profit_story_values or profit_story_values[-1] >= 0 else "rgba(255,143,150,.12)",
    )
    cash_visual = _sparkline_svg(
        cash_story_values,
        "#63D9A2" if not cash_story_values or cash_story_values[-1] >= 0 else "#F6C35E",
        "rgba(99,217,162,.12)" if not cash_story_values or cash_story_values[-1] >= 0 else "rgba(246,195,94,.12)",
    )
    street_visual = _story_range_strip(price, target_low, target_reference, target_high)

    story_cards = [
        _story_card_html(
            "매출 흐름",
            _fmt_num(revenue_story_values[-1]) if revenue_story_values else "N/A",
            revenue_note,
            revenue_visual,
            _story_period_label(revenue_story_labels),
            "accent" if isinstance(cagr_rev, float) and cagr_rev >= 0 else "negative" if isinstance(cagr_rev, float) and cagr_rev < 0 else "accent",
        ),
        _story_card_html(
            "이익 흐름",
            _fmt_num(profit_story_values[-1]) if profit_story_values else "N/A",
            profit_note,
            profit_visual,
            _story_period_label(profit_story_labels),
            "positive" if not profit_story_values or profit_story_values[-1] >= 0 else "negative",
        ),
        _story_card_html(
            cash_story_name,
            _fmt_num(cash_story_values[-1]) if cash_story_values else "N/A",
            cash_note,
            cash_visual,
            _story_period_label(cash_story_labels),
            "positive" if not cash_story_values or cash_story_values[-1] >= 0 else "warning",
        ),
        _story_card_html(
            "목표가 범위",
            f"{upside_pct_top:+.1f}%" if isinstance(upside_pct_top, (int, float)) else "N/A",
            street_note,
            street_visual,
            f"현재가 {_fmt_num(price)} · 커버리지 {analyst_count}명",
            "warning",
        ),
    ]
    story_html = (
        "<div class='story-board'>"
        "<div class='story-board__head'>"
        "<p class='story-board__eyebrow'>COMPANY STORY</p>"
        "</div>"
        f"<div class='story-grid'>{''.join(story_cards)}</div>"
        "</div>"
    )
    st.markdown(story_html, unsafe_allow_html=True)

    all_verdicts = []

    # ═══════════════════════════════════════════════════
    # 01 성장 사이클
    # ═══════════════════════════════════════════════════
    sn, sname, sdesc, scolor, algo_ctx = _growth_stage(info, fin, bs, cf)
    revenue_scale = algo_ctx.get('revenue_scale', '')
    profit_streak = algo_ctx.get('profit_streak', 0)
    consec_loss   = algo_ctx.get('consec_loss', 0)
    roe           = algo_ctx.get('roe', 0)
    margin_trend  = algo_ctx.get('margin_trend', 'flat')
    growth_trend  = algo_ctx.get('growth_trend', 'flat')
    rev_cagr_3y   = algo_ctx.get('rev_cagr_3y', 0)
    rev_g_stage   = algo_ctx.get('rev_g', 0)
    
    # UI 렌더링에 필요한 색상과 라벨 매핑 (1~10단계)
    stage_map = {1: "#FF7043", 2: "#FFA726", 3: "#FF9800", 4: "#FF6D00", 5: "#00E676", 6: "#00C853", 7: "#E57373", 8: "#F44336", 9: "#C62828", 10: "#FFC107"}
    stage_lbl = {1: "스타트업", 2: "초기성장", 3: "스케일업", 4: "초고속성장", 5: "성숙성장", 6: "캐시카우", 7: "정체기", 8: "초기쇠퇴", 9: "구조적쇠퇴", 10: "턴어라운드"}

    bar_html = "".join([f'<div style="flex:1;background:{stage_map[i] if i == sn else "rgba(0,0,0,0.2)"};opacity:{"1" if i == sn else (str(0.25 + i * 0.02))};text-align:center;padding:14px 2px;font-size:.7rem;color:#ffffff;border:{"3px solid " + stage_map[i] if i == sn else "1px solid #444c56"};border-radius:{"10px 0 0 10px" if i == 1 else ("0 10px 10px 0" if i == 10 else "0")};font-weight:{"800" if i == sn else "600"};box-shadow:{"0 0 16px " + stage_map[i] + "88" if i == sn else "none"};transition:all .3s">{i}<br>{stage_lbl[i]}</div>' for i in range(1, 11)])
    
    v1_c = "green" if sn in [5, 6] else ("orange" if sn in [1, 2, 3, 4, 10] else "red")
    v1_map = {
        1: "초기 — 높은 위험·생존 테스트 중", 
        2: "점유율 확대 — 적자이나 최고 속도 팽창", 
        3: "흑자 모멘텀 — 스케일업 파워 폭발", 
        4: "주도권 획득 — 무결점의 초우량 흑자성장", 
        5: "안정적 우량주 — 성장/수익 증명", 
        6: "현금 창출 극대화 — 자사주 매입/안정성", 
        7: "수익 방어 — 정체된 매출, 새 대안 필요", 
        8: "위험 — 역성장이나 흑자로 겨우 버티기", 
        9: "심각 — 구조적 하락장과 심대한 타격", 
        10: "역발상 기회 — 턴어라운드(V자반등) 돌입"
    }
    all_verdicts.append(("성장사이클", v1_c))

    # 알고리즘 판단 근거 인포박스
    _algo_hints = []
    if revenue_scale: _algo_hints.append(f"규모 {revenue_scale}")
    if profit_streak > 0: _algo_hints.append(f"연속흑자 {profit_streak}년")
    if consec_loss > 0: _algo_hints.append(f"연속적자 {consec_loss}년")
    if roe > 0: _algo_hints.append(f"ROE {roe*100:.1f}%")
    if margin_trend != 'flat': _algo_hints.append(f"이익률추세 {'↑' if margin_trend == 'up' else '↓'}")
    if growth_trend != 'flat': _algo_hints.append(f"성장추세 {'가속' if growth_trend == 'accel' else '감속'}")
    if rev_cagr_3y and rev_cagr_3y != rev_g_stage: _algo_hints.append(f"3Y CAGR {rev_cagr_3y*100:.1f}%")
    algo_hint_html = (f"<div style='background:rgba(255,109,0,0.06);border:1px solid rgba(255,109,0,0.2);border-radius:8px;padding:8px 14px;margin-top:12px;font-size:.8rem;color:#adbac7;font-weight:600'>" +
                      f"<span style='color:#FF9800;font-weight:800'>⚙️ 알고리즘 판단 근거:</span> " +
                      " · ".join(_algo_hints) + "</div>") if _algo_hints else ""

    with st.container(border=True):
        html_s1 = (
            f'<div class="s-title"><span class="s-num">01</span> 이 회사, 지금 어느 단계인가요?</div>'
            f'<div style="display:flex;gap:3px;margin-bottom:24px">{bar_html}</div>'
            f'<div style="text-align:center;margin:20px 0"><span style="display:inline-block;padding:12px 32px;border-radius:24px;font-weight:800;background:{scolor};color:#fff;font-size:1.2rem;box-shadow:0 6px 20px {scolor}66">{sname}</span><div style="font-size:1rem;color:#e6edf3;font-weight:700;margin-top:16px;line-height:1.7">{sdesc}</div></div>'
            f'{algo_hint_html}'
            f'<div class="divider"></div>'
            f'<div class="two-col"><div>'
            f'{_metric_row("최근 연간 매출성장 (YoY)", _fmt_pct(ann_rev_g))}'
            f'{_metric_row("최근 분기 매출성장 (YoY)", _fmt_pct(yoy_q_rev_g))}'
            f'{_metric_row("직전 분기 대비 성장 (QoQ)", _fmt_pct(qoq_rev_g))}'
            f'</div><div>'
            f'{_metric_row("순이익률", _fmt_pct(info.get("profitMargins")))}'
            f'{_metric_row("ROE", _fmt_pct(info.get("returnOnEquity")))}'
            f'{_metric_row("배당수익률", _fmt_pct(dividend_yield))}'
            f'</div></div>'
            f'{_verdict_badge(v1_c, "", f"종합: {v1_map.get(sn, "")}")}'
        )
        st.markdown(html_s1, unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════
    # 02 돈을 잘 버는 회사인가요?
    # ═══════════════════════════════════════════════════
    gross_m, net_m, mcap = info.get('grossMargins'), info.get('profitMargins'), info.get('marketCap')
    ttm_eps, ttm_rev, ttm_ni = info.get('trailingEps'), info.get('totalRevenue'), info.get('netIncomeToCommon')

    ps = sum(1 for x in [gross_m and gross_m > 0.4, net_m and net_m > 0.1, cagr_rev and isinstance(cagr_rev, float) and cagr_rev > 0.05, cagr_ni and isinstance(cagr_ni, float) and cagr_ni > 0.05, ttm_ni and ttm_ni > 0] if x)
    if   ps >= 4: v2_c, v2_t = "green",  "[CASH] 매우 우수 — 높은 마진 + 지속 성장"
    elif ps >= 3: v2_c, v2_t = "green",  "✅ 양호 — 수익성과 성장 겸비"
    elif ps >= 2: v2_c, v2_t = "yellow", "⚠️ 보통 — 일부 지표 개선 필요"
    else:         v2_c, v2_t = "red",    "❌ 수익성 미흡 — 적자 또는 마진 악화"
    all_verdicts.append(("수익성", v2_c))

    ni_cls = "m-green" if ttm_ni and ttm_ni > 0 else "m-red"
    cr_cls = lambda v: "m-green" if (isinstance(v, float) and v > 0) or "전환" in str(v) else "m-red"
    gm_gauge = _gauge_bar((gross_m or 0) * 100, "#63D9A2", 10)
    nm_gauge = _gauge_bar((net_m or 0) * 100, "#60A5FA", 10)

    rev_lbl = f"{yr_rev}년 매출 평균성장" if yr_rev else "매출 성장추세"
    ni_lbl  = f"{yr_ni}년 순이익 평균성장" if yr_ni else "순이익 추세"
    if yr_eps and yr_eps == 1 and cagr_eps is not None:
        eps_lbl = f"{yr_eps}년 EPS 추세 (Forward 추정)" if isinstance(cagr_eps, float) else f"{yr_eps}년 EPS 추세 (SEC)"
    elif yr_eps: eps_lbl = f"{yr_eps}년 EPS 추세 (SEC)"
    else: eps_lbl = "EPS 추세"

    with st.container(border=True):
        html_s2 = (
            f'<div class="s-title"><span class="s-num">02</span> 돈을 잘 버는 회사인가요? <span style="font-size:.8rem;color:#768390">SEC 데이터</span></div>'
            f'<div class="two-col"><div>'
            f'{_metric_row("시가총액", _fmt_num(mcap), "m-value m-big")}'
            f'{_metric_row("TTM EPS (주당순이익)", f"${_safe(ttm_eps)}")}'
            f'{_metric_row("최근 12개월 매출", _fmt_num(ttm_rev))}'
            f'{_metric_row("최근 12개월 순이익", _fmt_num(ttm_ni), ni_cls)}'
            f'</div><div>'
            f'<div style="margin-bottom:16px"><div style="display:flex;justify-content:space-between;font-size:.95rem"><span style="color:#adbac7;font-weight:700">총이익률 (Gross)</span><span style="color:#ffffff;font-weight:800">{_fmt_pct(gross_m)}</span></div>{gm_gauge}</div>'
            f'<div style="margin-bottom:16px"><div style="display:flex;justify-content:space-between;font-size:.95rem"><span style="color:#adbac7;font-weight:700">순이익률 (Net)</span><span style="color:#ffffff;font-weight:800">{_fmt_pct(net_m)}</span></div>{nm_gauge}</div>'
            f'</div></div>'
            f'<div class="divider"></div>'
            f'<div class="two-col"><div>'
            f'{_metric_row(rev_lbl, _fmt_cagr(cagr_rev), cr_cls(cagr_rev))}'
            f'{_metric_row(ni_lbl, _fmt_cagr(cagr_ni), cr_cls(cagr_ni))}'
            f'</div><div>'
            f'{_metric_row(eps_lbl, _fmt_cagr(cagr_eps), cr_cls(cagr_eps))}'
            f'<div class="note-box">※ 이익이 적자(-)에서 시작된 경우 수학적 한계로 비율(%) 대신 텍스트로 표기됩니다.</div>'
            f'</div></div>'
            f'{_verdict_badge(v2_c, "", v2_t)}'
        )
        st.markdown(html_s2, unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════
    # 03 지금까지 성적
    # ═══════════════════════════════════════════════════
    rev_stab, rev_cv, stab_c = _stability(fin, REV_ALIASES)
    mtrend, _, mtrend_c      = _margin_trend(fin)
    accel, accel_c           = _growth_accel(fin, REV_ALIASES)

    roe_val = info.get('returnOnEquity')
    roe_c = "green" if roe_val and roe_val > 0.1 else ("yellow" if roe_val and roe_val > 0 else "red")

    rv, rd = _annual_values(fin, REV_ALIASES)
    nv, _ = _annual_values(fin, NI_ALIASES)

    tbl_rows = ""
    for i in range(min(len(rv), len(nv), 4)):
        yr = rd[i].strftime('%Y') if hasattr(rd[i], 'strftime') else str(rd[i])[:4]
        mg = (nv[i] / rv[i] * 100) if rv[i] and rv[i] != 0 else 0
        tbl_rows += f"<tr><td>{yr}</td><td>{_fmt_num(rv[i])}</td><td style='color: {'#63D9A2' if nv[i]>0 else '#FF8F96'}'>{_fmt_num(nv[i])}</td><td style='color: {'#63D9A2' if mg>0 else '#FF8F96'}'>{mg:.1f}%</td></tr>"

    fig3 = _get_plotly_combo_chart(rv[:4] if rv else [], nv[:4] if nv else [], rd[:4] if rd else [])

    s3 = sum(1 for c in [stab_c, mtrend_c, accel_c, roe_c] if c == "green")
    if   s3 >= 3: v3_c, v3_t = "green",  "✅ 우수한 트랙 레코드 — 안정 성장 + 높은 ROE"
    elif s3 >= 2: v3_c, v3_t = "yellow", "⚠️ 보통 — 일부 양호, 개선 여지"
    else:         v3_c, v3_t = "red",    "❌ 주의 — 수익 불안정 또는 하락 추세"
    all_verdicts.append(("과거성적", v3_c))

    with st.container(border=True):
        col1, col2 = st.columns([1.1, 1])
        html_s3_1 = (
            f'<div class="s-title"><span class="s-num">03</span> 지금까지 성적 <span style="font-size:.8rem;color:#768390">SEC 데이터</span></div>'
            f'{_metric_row("수익 안정성", f"{rev_stab} <span style=\'font-size:.8rem;color:#8b949e;font-weight:600\'>{rev_cv}</span>")}'
            f'{_metric_row("이익 마진 추이", mtrend)}'
            f'{_metric_row("성장 가속화", accel)}'
            f'{_metric_row("ROE 수준", f"{_fmt_pct(roe_val)}")}'
            f'<div class="divider"></div>'
            f'<table class="m-table"><tr><th>연도</th><th>매출</th><th>순이익</th><th>이익률</th></tr>{tbl_rows}</table>'
        )
        with col1:
            st.markdown(html_s3_1, unsafe_allow_html=True)
        with col2:
            if fig3: st.plotly_chart(fig3, use_container_width=True, config={'displayModeBar': False}, key=f"{key_prefix}_fig3")
        st.markdown(_verdict_badge(v3_c, "", v3_t), unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════
    # 04 성장 가능성 
    # ═══════════════════════════════════════════════════
    t_pe, f_pe = info.get('trailingPE'), info.get('forwardPE')
    fwd_eps = info.get('forwardEps')
    
    payout, roe_v = info.get('payoutRatio', 0) or 0, info.get('returnOnEquity', 0) or 0
    retention, sust_g = max(0, 1 - payout), (roe_v * max(0, 1 - payout) if roe_v else None)
    eg = info.get('earningsGrowth')
    
    peg = peg_resolved

    if peg and not pd.isna(peg):
        if peg < 0.5: peg_txt, peg_cls = f"{peg:.2f} (매우 저평가)", "m-blue"
        elif peg <= 1.5: peg_txt, peg_cls = f"{peg:.2f} (적정 가치)", "m-green"
        else: peg_txt, peg_cls = f"{peg:.2f} (고평가)", "m-red"
    else: peg_txt, peg_cls = "N/A", "m-value"

    gs = sum(1 for x in [eg and eg > 0.15, yoy_q_rev_g and isinstance(yoy_q_rev_g, float) and yoy_q_rev_g > 0.10, retention > 0.60, sust_g and sust_g > 0.10, peg and 0 < peg <= 1.5] if x)
    if   gs >= 4: v4_c, v4_t = "green",  "[SURGE] 높은 성장 잠재력 — 수익 재투자 + 고성장"
    elif gs >= 2: v4_c, v4_t = "yellow", "⚠️ 보통 — 성장 가능성 있으나 모니터링 필요"
    else:         v4_c, v4_t = "red",    "❌ 성장 둔화 — 새 동력 부재"
    all_verdicts.append(("성장성", v4_c))

    eg_cls = "m-green" if eg and eg > 0 else "m-red"
    rg_cls = "m-green" if yoy_q_rev_g and isinstance(yoy_q_rev_g, float) and yoy_q_rev_g > 0 else "m-red"

    with st.container(border=True):
        html_s4 = (
            f'<div class="s-title"><span class="s-num">04</span> 성장 가능성 <span style="font-size:.8rem;color:#768390">SEC + Yahoo</span></div>'
            f'<div class="two-col"><div>'
            f'{_metric_row("분기 이익 성장률 (YoY)", _fmt_pct(eg), eg_cls)}'
            f'{_metric_row("분기 매출 성장률 (YoY)", _fmt_pct(yoy_q_rev_g), rg_cls)}'
            f'{_metric_row("Forward EPS", f"${_safe(fwd_eps)}")}'
            f'{_metric_row("PEG 비율", peg_txt, peg_cls)}'
            f'</div><div>'
            f'{_metric_row("ROE", _fmt_pct(roe_v))}'
            f'{_metric_row("수익 유보율 (1 - 배당성향)", _fmt_pct(retention))}'
            f'{_metric_row("지속가능 성장률 (g)", _fmt_pct(sust_g), "m-green" if sust_g and sust_g > 0.1 else "m-value")}'
            f'<div class="note-box">💡 <b>지속가능 성장률(g)</b> = ROE × 유보율.<br>'
            f'💡 <b>PEG (주가수익성장비율)</b> = P/E Ratio ÷ 이익 성장률<br>'
            f'&nbsp;&nbsp;• <b>PEG &lt; 0.5</b> : 매우 저평가 &nbsp; • <b>0.5 ~ 1.5</b> : 적정 가치 &nbsp; • <b>PEG &gt; 1.5</b> : 고평가</div>'
            f'</div></div>'
            f'{_verdict_badge(v4_c, "", v4_t)}'
        )
        st.markdown(html_s4, unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════
    # 05 재무 건전성 
    # ═══════════════════════════════════════════════════
    na = None
    info_total_debt = None
    ta = None
    tl = None
    
    try:
        if bs is not None and not bs.empty:
            latest_bs = bs.iloc[:, 0]
            
            eq_idx = _find_idx(bs, EQ_ALIASES)
            if eq_idx: na = latest_bs.get(eq_idx)
            
            debt_idx = _find_idx(bs, DEBT_ALIASES)
            if debt_idx: info_total_debt = latest_bs.get(debt_idx)
            
            ta_idx = _find_idx(bs, BS_ASSETS_ALIASES)
            if ta_idx: ta = latest_bs.get(ta_idx)
            
            tl_idx = _find_idx(bs, BS_LIAB_ALIASES)
            if tl_idx: tl = latest_bs.get(tl_idx)
            
    except Exception as e:
        logger.warning(f"iloc extraction failed: {e}")

    if pd.isna(na) or na is None:
        if ta is not None and tl is not None and ta > 0 and tl > 0:
            na = ta - tl
    if pd.isna(na) or na is None:
        bv = info.get('bookValue', 0)
        shares = info.get('sharesOutstanding', 0)
        if bv and shares: na = bv * shares

    if pd.isna(info_total_debt) or info_total_debt is None:
        info_total_debt = info.get('totalDebt', 0)
        
    na_display = _fmt_num(na) if (na is not None and not pd.isna(na)) else "N/A"
    debt_display = _fmt_num(info_total_debt) if (info_total_debt is not None and not pd.isna(info_total_debt)) else "N/A"
    
    try:
        ta_s = _get_row_series(bs, BS_ASSETS_ALIASES)
        tl_s = _get_row_series(bs, BS_LIAB_ALIASES)
        common_idx = [i for i in ta_s.index if i in tl_s.index]
        common_idx = sorted(common_idx, reverse=True)[:4]
        
        if len(common_idx) > 0:
            fig5 = _get_plotly_yearly_bar(common_idx, [ta_s[i] for i in common_idx], [tl_s[i] for i in common_idx], "총 자산", "총 부채", "#60A5FA", "#FF8F96")
        else:
            fig5 = None
    except Exception:
        fig5 = None

    cash = info.get('totalCash', 0) or 0
    dt_trend, dt_c = _debt_trend(bs)
    ib_txt, ib_c   = _interest_burden(fin, info)

    # [SURGE] D/E 비율 강제 계산
    if na and na > 0 and info_total_debt is not None and info_total_debt >= 0:
        dte = (info_total_debt / na) * 100
    else:
        dte = info.get('debtToEquity')

    if isinstance(dte, (int, float)):
        if   dte < 50:  dl, dl_c = "낮음 ✅", "green"
        elif dte < 100: dl, dl_c = "보통 ⚠️", "yellow"
        elif dte < 200: dl, dl_c = "높음 ⚠️", "red"
        else:           dl, dl_c = "매우 높음 ❌", "red"
    else:
        dl, dl_c = "N/A", "gray"

    hs = sum(1 for x in [dl_c == "green", dt_c == "green", ib_c == "green", cash > (tl or 0) * 0.2 if tl else False] if x)
    if   hs >= 3: v5_c, v5_t = "green",  "💪 재무 건전 — 낮은 부채, 충분한 현금"
    elif hs >= 2: v5_c, v5_t = "yellow", "⚠️ 보통 — 부채 관리 모니터링 필요"
    else:         v5_c, v5_t = "red",    "❌ 주의 — 부채 높거나 현금 부족"
    all_verdicts.append(("재무건전", v5_c))
    v5_pill_cls = "pill-green" if v5_c == "green" else ("pill-amber" if v5_c == "yellow" else "pill-red")
    dl_pill_cls = "pill-green" if dl_c == "green" else ("pill-amber" if dl_c == "yellow" else "pill-red")

    debt_value = _first_valid_number(info_total_debt)
    cash_value = _first_valid_number(cash)
    net_cash = (cash_value - debt_value) if cash_value is not None and debt_value is not None else None
    cash_to_debt = (cash_value / debt_value) if cash_value is not None and debt_value not in (None, 0) else None
    cash_to_debt_text = f"{cash_to_debt:.2f}x" if isinstance(cash_to_debt, (int, float)) else "N/A"
    net_cash_text = _fmt_num(net_cash) if isinstance(net_cash, (int, float)) else "N/A"
    net_cash_cls = "m-green" if isinstance(net_cash, (int, float)) and net_cash >= 0 else "m-red"
    ocf_cls = "m-green" if isinstance(ocf, (int, float)) and ocf > 0 else "m-red"
    fcf_cls = "m-green" if isinstance(fcf, (int, float)) and fcf > 0 else "m-red"
    cash_fill = min(max(cash_to_debt, 0), 2) / 2 * 100 if isinstance(cash_to_debt, (int, float)) else 0
    dte_fill = 100 - (min(max(dte, 0), 220) / 220 * 100) if isinstance(dte, (int, float)) else 0
    cash_tone = "#63D9A2" if isinstance(cash_to_debt, (int, float)) and cash_to_debt >= 1 else "#F6C35E" if isinstance(cash_to_debt, (int, float)) and cash_to_debt >= 0.5 else "#FF8F96"
    dte_tone = "#63D9A2" if dl_c == "green" else "#F6C35E" if dl_c == "yellow" else "#FF8F96"

    with st.container(border=True):
        debt_ratio_text = f"{dte:.1f}%" if isinstance(dte, (int, float)) else "N/A"
        s5_title_html = '<div class="s-title"><span class="s-num">05</span> 회사에 돈이 얼마나 있나요? <span style="font-size:.8rem;color:#768390">SEC + Yahoo</span></div>'
        s5_spotlight = (
            f"<div class='spotlight-grid tight'>"
            f"<div class='spotlight-card'><p class='spotlight-label'>보유 현금</p><p class='spotlight-value' style='color:#63D9A2'>{_fmt_num(cash)}</p><p class='spotlight-sub'>현금 및 현금성 자산</p></div>"
            f"<div class='spotlight-card'><p class='spotlight-label'>영업현금흐름</p><p class='spotlight-value' style='color:{'#B8F1D5' if ocf_cls == 'm-green' else '#FFD2D7'}'>{_fmt_num(ocf)}</p><p class='spotlight-sub'>본업에서 버는 현금</p></div>"
            f"<div class='spotlight-card'><p class='spotlight-label'>잉여현금흐름</p><p class='spotlight-value' style='color:{'#B8F1D5' if fcf_cls == 'm-green' else '#FFD2D7'}'>{_fmt_num(fcf)}</p><p class='spotlight-sub'>투자 후 남는 현금</p></div>"
            f"<div class='spotlight-card'><p class='spotlight-label'>부채/자본 비율</p><p class='spotlight-value' style='color:{'#B8F1D5' if dl_c == 'green' else '#F8DE9A' if dl_c == 'yellow' else '#FFD2D7'}'>{debt_ratio_text}</p><p class='spotlight-sub'>{dl}</p></div>"
            f"</div>"
        )
        s5_chip_row = (
            f"<div class='compact-chip-row'>"
            f"<span class='compact-chip'>현금/부채 {cash_to_debt_text}</span>"
            f"<span class='compact-chip'>순현금 {net_cash_text}</span>"
            f"<span class='compact-chip'>이자 부담 {_esc(ib_txt)}</span>"
            f"</div>"
        )
        s5_header_html = (
            f"<div style='display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:14px'><span class='section-pill {v5_pill_cls}'>{v5_t}</span><span class='section-pill {dl_pill_cls}'>D/E {dl}</span></div>"
            f"{s5_spotlight}"
            f"{s5_chip_row}"
        )
        s5_health_board = (
            f"<div class='metric-rail-card'>"
            f"<div class='cluster-title'>재무 체력 보드</div>"
            f"<div class='cluster-sub'>현금 여력과 레버리지 강도를 한 번에 읽을 수 있게 요약했습니다.</div>"
            f"<div class='metric-rail-row'><div class='metric-rail-head'><span>차입 상환 완충력</span><strong>{cash_to_debt_text}</strong></div><div class='metric-rail-track'><div class='metric-rail-fill' style='width:{cash_fill:.1f}%;background:{cash_tone}'></div></div><div class='metric-rail-note'>1.0x 이상이면 보유 현금만으로 총부채를 대부분 커버할 수 있습니다.</div></div>"
            f"<div class='metric-rail-row'><div class='metric-rail-head'><span>레버리지 강도</span><strong>{debt_ratio_text}</strong></div><div class='metric-rail-track'><div class='metric-rail-fill' style='width:{dte_fill:.1f}%;background:{dte_tone}'></div></div><div class='metric-rail-note'>부채/자본 비율은 낮을수록 방어력이 좋습니다.</div></div>"
            f"<div class='target-mini-grid'>"
            f"<div class='target-mini-card'><p class='target-mini-label'>순현금</p><p class='target-mini-value {net_cash_cls}'>{net_cash_text}</p><p class='target-mini-sub'>현금 - 총부채</p></div>"
            f"<div class='target-mini-card'><p class='target-mini-label'>부채 추세</p><p class='target-mini-value'>{dt_trend}</p><p class='target-mini-sub'>최근 재무제표 흐름</p></div>"
            f"<div class='target-mini-card'><p class='target-mini-label'>이자 부담</p><p class='target-mini-value'>{ib_txt}</p><p class='target-mini-sub'>상환 여력 체크</p></div>"
            f"</div>"
            f"</div>"
        )
        s5_stack_html = (
            f"<div class='stack-col'>"
            f"<div class='cluster-card'>"
            f"<div class='cluster-title'>유동성 / 현금창출</div>"
            f"<div class='cluster-sub'>현금이 있는가보다, 현금이 계속 들어오는 구조인가가 더 중요합니다.</div>"
            f'{_metric_row("보유 현금", _fmt_num(cash), "m-value m-green m-big")}'
            f'{_metric_row("영업활동 현금흐름", _fmt_num(ocf), ocf_cls)}'
            f'{_metric_row("잉여현금흐름", _fmt_num(fcf), fcf_cls)}'
            f'{_metric_row("현금/부채", cash_to_debt_text, "m-green" if isinstance(cash_to_debt, (int, float)) and cash_to_debt >= 1 else "m-value")}'
            f'{_metric_row("순현금", net_cash_text, net_cash_cls)}'
            f"</div>"
            f"<div class='cluster-card'>"
            f"<div class='cluster-title'>레버리지 / 상환부담</div>"
            f"<div class='cluster-sub'>총부채 규모보다 상환 여력과 추세가 더 중요합니다.</div>"
            f'{_metric_row("총 부채", debt_display, "m-value")}'
            f'{_metric_row("순자산(자본)", na_display, "m-green" if (na and na > 0) else "m-red")}'
            f'{_metric_row("부채 수준(D/E)", dl)}'
            f'{_metric_row("부채 추세", dt_trend)}'
            f'{_metric_row("이자 부담(ICR)", ib_txt)}'
            f"</div>"
            f"<div class='insight-shell'>"
            f"<div class='cluster-title'>해석 포인트</div>"
            f"<div class='cluster-sub'>현금이 많아도 현금흐름이 마이너스면 빠르게 소진될 수 있고, 부채가 있어도 영업활동 현금흐름이 안정적이면 부담이 낮아집니다.</div>"
            f"{_metric_row('실질 재무 포지션', '순현금 우위' if isinstance(net_cash, (int, float)) and net_cash >= 0 else '순부채 구조', net_cash_cls)}"
            f"{_metric_row('핵심 체크', '현금흐름 지속성 > 현금 절대규모', 'm-value')}"
            f"</div>"
            f'<div class="note-box">※ <b>부채/자본 비율</b>은 총부채를 순자산으로 나눈 값으로 직접 교차 계산합니다.<br>※ 현금 잔고와 함께 영업활동 현금흐름, 잉여현금흐름까지 같이 봐야 재무 체력을 제대로 읽을 수 있습니다.</div>'
            f"</div>"
        )
        st.markdown(s5_title_html, unsafe_allow_html=True)
        st.markdown("<div class='section-lead'>현금 자체보다 영업활동 현금흐름과 상환 여력을 함께 보면 재무 체력이 더 정확하게 보입니다.</div>", unsafe_allow_html=True)
        st.markdown(s5_header_html, unsafe_allow_html=True)
        col1, col2 = st.columns([1.02, 0.98])
        with col1:
            if fig5: st.plotly_chart(fig5, use_container_width=True, config={'displayModeBar': False}, key=f"{key_prefix}_fig5")
            else: st.markdown("<div class='note-box'>※ 자산/부채 데이터를 모두 불러올 수 없어 차트가 생략되었습니다.</div>", unsafe_allow_html=True)
            st.markdown(s5_health_board, unsafe_allow_html=True)
        with col2:
            st.markdown(s5_stack_html, unsafe_allow_html=True)
        st.markdown(_verdict_badge(v5_c, "", v5_t), unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════
    # 06 거래량
    # ═══════════════════════════════════════════════════
    vol, avg10, avg3m = info.get('volume', 0) or 0, info.get('averageVolume10days', 0) or 0, info.get('averageVolume', 0) or 0
    vt_txt, vt_c = _vol_trend(info)
    all_verdicts.append(("거래량", vt_c))

    max_vol = max(vol, avg10, avg3m, 1)
    vol_bars = "".join([f'<div style="display:flex;align-items:center;gap:12px;margin:8px 0"><span style="min-width:70px;font-size:.85rem;font-weight:700;color:#adbac7;text-align:right">{lbl}</span><div style="flex:1;background:rgba(0,0,0,0.3);border-radius:6px;height:24px;overflow:hidden"><div style="width:{v/max_vol*100:.1f}%;height:100%;background:{c};border-radius:6px;display:flex;align-items:center;padding-left:10px;font-size:.85rem;color:white;font-weight:800">{_fmt_num(v, False)}</div></div></div>' for lbl, v, c in [("현재", vol, "#60A5FA"), ("10일평균", avg10, "#94A3B8"), ("3개월평균", avg3m, "#475569")]])

    with st.container(border=True):
        html_s6 = (
            f'<div class="s-title"><span class="s-num">06</span> 현재 사람들이 많이 사고 있나요? <span style="font-size:.8rem;color:#768390">Yahoo</span></div>'
            f'<div class="two-col"><div>'
            f'{_metric_row("현재 거래량", f"{_fmt_num(vol, False)} 주")}'
            f'{_metric_row("10일 평균", f"{_fmt_num(avg10, False)} 주")}'
            f'{_metric_row("3개월 평균", f"{_fmt_num(avg3m, False)} 주")}'
            f'<div class="divider"></div>'
            f'{_metric_row("거래량 변동 추이", vt_txt)}'
            f'</div><div>'
            f'<div style="font-size:.95rem;color:#ffffff;margin-bottom:10px;font-weight:800">거래량 비교</div>{vol_bars}'
            f'</div></div>'
            f'{_verdict_badge(vt_c, "", {"green": "✅ 거래량 정상 — 유동성 양호", "yellow": "⚠️ 거래량 변동 — 추이 주시 필요", "red": "[HOT] 거래량 이상 — 급변 가능성"}.get(vt_c, "데이터 부족"))}'
        )
        st.markdown(html_s6, unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════
    # 07 변동성
    # ═══════════════════════════════════════════════════
    beta = info.get('beta')
    if isinstance(beta, (int, float)):
        if   beta < 0.8: bl, bc = "저변동 — 시장보다 안정", "green"
        elif beta < 1.2: bl, bc = "시장과 유사", "yellow"
        elif beta < 1.5: bl, bc = "높은 변동성 ⚠️", "red"
        else:            bl, bc = "매우 높은 변동성 [HOT]", "red"
    else: bl, bc = "N/A", "gray"
    all_verdicts.append(("변동성", bc))

    w52h, w52l, w52c = info.get('fiftyTwoWeekHigh'), info.get('fiftyTwoWeekLow'), info.get('52WeekChange')
    pos_bar = f"<div style='margin:16px 0'><div style='display:flex;justify-content:space-between;font-size:.85rem;font-weight:700;color:#adbac7;margin-bottom:6px'><span>저 ${w52l:,.2f}</span><span style='color:#ffffff;font-size:1.1rem;font-weight:900'>현재 ${price:,.2f}</span><span>고 ${w52h:,.2f}</span></div><div style='background:rgba(0,0,0,0.4);border-radius:8px;height:16px;position:relative'><div style='background:linear-gradient(90deg,#FF8F96 0%,#F6C35E 50%,#63D9A2 100%);width:100%;height:100%;border-radius:8px;opacity:0.35'></div><div style='position:absolute;top:-4px;left:{max(0, min(100, (price - w52l) / (w52h - w52l) * 100)):.1f}%;width:24px;height:24px;background:#60A5FA;border-radius:50%;transform:translateX(-50%);border:3px solid #ffffff;box-shadow:0 0 12px rgba(96,165,250,.55)'></div></div></div>" if price and w52h and w52l and w52h != w52l else ""

    with st.container(border=True):
        html_s7 = (
            f'<div class="s-title"><span class="s-num">07</span> 변동성이 큰가요? <span style="font-size:.8rem;color:#768390">Yahoo</span></div>'
            f'<div class="two-col"><div>'
            f'{_metric_row("베타 (β)", f"{beta:.2f} ({bl})" if isinstance(beta, (int, float)) else "N/A")}'
            f'{_metric_row("52주 가격 변화율", _fmt_pct(w52c), "m-green" if w52c and w52c > 0 else "m-red")}'
            f'{_metric_row("52주 최고가", f"${w52h:,.2f}" if w52h else "N/A")}'
            f'{_metric_row("52주 최저가", f"${w52l:,.2f}" if w52l else "N/A")}'
            f'</div><div>'
            f'<div style="font-size:.95rem;color:#ffffff;margin-bottom:8px;font-weight:800">📍 52주 범위 내 위치</div>{pos_bar}'
            f'<div class="note-box">💡 베타 &lt; 1 = 시장(S&amp;P500) 대비 안정적<br>베타 &gt; 1 = 시장보다 변동성이 큽니다.</div>'
            f'</div></div>'
            f'{_verdict_badge(bc, "", f"베타 {beta:.2f} — {bl}" if isinstance(beta, (int, float)) else "변동성 데이터 부족")}'
        )
        st.markdown(html_s7, unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════
    # 08 밸류에이션 ([SURGE] 레이아웃 및 변수 노출 버그 완벽 수정)
    # ═══════════════════════════════════════════════════
    p_s, p_b = info.get('priceToSalesTrailing12Months'), info.get('priceToBook')
    
    s_pe, pe_source = _sector_pe_live(sector)

    pe_comp = ""
    if t_pe and s_pe:
        diff = ((t_pe - s_pe) / s_pe) * 100
        if   diff > 30:  pe_comp = f"섹터 대비 <b style='color:#FF8F96'>고평가 (+{diff:.0f}%)</b>"
        elif diff > 0:   pe_comp = f"섹터 대비 <b style='color:#F6C35E'>약간 고평가 (+{diff:.0f}%)</b>"
        elif diff > -20: pe_comp = f"섹터 대비 <b style='color:#63D9A2'>적정 ({diff:.0f}%)</b>"
        else:            pe_comp = f"섹터 대비 <b style='color:#63D9A2'>저평가 ({diff:.0f}%)</b>"

    if t_pe and s_pe:
        if   t_pe < s_pe * 0.8: v8_c, v8_t = "green",  "💎 저평가 가능성 — 섹터 평균 대비 할인"
        elif t_pe < s_pe * 1.3: v8_c, v8_t = "yellow", "⚖️ 적정 — 섹터 평균과 유사"
        else:                   v8_c, v8_t = "red",    "💸 고평가 가능성 — 프리미엄 가격"
    else:
        v8_c, v8_t = "gray", "비교 데이터 부족"
    all_verdicts.append(("밸류에이션", v8_c))

    pe_visual = f"<div style='margin:16px 0'><div style='font-size:.95rem;color:#ffffff;margin-bottom:12px;font-weight:800'>P/E 비교</div><div style='display:flex;align-items:center;gap:12px;margin:8px 0'><span style='min-width:60px;font-size:.85rem;font-weight:700;color:#60A5FA'>이 종목</span><div style='flex:1;background:rgba(0,0,0,0.3);border-radius:6px;height:24px;overflow:hidden'><div style='width:{t_pe / (max(t_pe, s_pe) * 1.3) * 100:.1f}%;height:100%;background:#60A5FA;border-radius:6px;display:flex;align-items:center;justify-content:flex-end;padding-right:10px;font-size:.85rem;color:white;font-weight:800'>{t_pe:.1f}</div></div></div><div style='display:flex;align-items:center;gap:12px;margin:8px 0'><span style='min-width:60px;font-size:.85rem;font-weight:700;color:#adbac7'>섹터평균</span><div style='flex:1;background:rgba(0,0,0,0.3);border-radius:6px;height:24px;overflow:hidden'><div style='width:{s_pe / (max(t_pe, s_pe) * 1.3) * 100:.1f}%;height:100%;background:#64748B;border-radius:6px;display:flex;align-items:center;justify-content:flex-end;padding-right:10px;font-size:.85rem;color:white;font-weight:800'>{s_pe:.1f}</div></div></div></div>" if t_pe and s_pe else ""

    pe_src_lbl = f"평균 P/E ≈ {s_pe:.1f} ({pe_source})" if s_pe else "N/A"
    pe_warning = "<div class='note-box' style='border-left-color:#FFC107;'>⚠️ <b>주의:</b> Forward P/E가 Trailing P/E보다 비정상적으로 높습니다. 향후 실적 악화 전망이거나 yfinance 추정치 오류일 수 있습니다.</div>" if t_pe and f_pe and f_pe > t_pe * 1.5 else ""

    t_pe_str = f"{t_pe:.2f}" if isinstance(t_pe, (int, float)) else "N/A"
    f_pe_str = f"{f_pe:.2f}" if isinstance(f_pe, (int, float)) else "N/A"
    p_s_str  = f"{p_s:.2f}" if isinstance(p_s, (int, float)) else "N/A"
    p_b_str  = f"{p_b:.2f}" if isinstance(p_b, (int, float)) else "N/A"

    with st.container(border=True):
        html_s8 = (
            f'<div class="s-title"><span class="s-num">08</span> 이 종목 비싼가요? <span style="font-size:.8rem;color:#768390">Yahoo</span></div>'
            f'<div class="two-col"><div>'
            f'{_metric_row("Trailing P/E", t_pe_str)}'
            f'{_metric_row("Forward P/E", f_pe_str)}'
            f'{_metric_row("P/S (TTM)", p_s_str)}'
            f'{_metric_row("P/B", p_b_str)}'
            f'<div class="divider"></div>'
            f'{_metric_row(f"섹터 ({_esc(sector)})", pe_src_lbl)}'
            f'{_metric_row("섹터 대비", pe_comp if pe_comp else "N/A")}'
            f'</div><div>'
            f'{pe_visual}'
            f'{pe_warning}'
            f'<div class="note-box">※ P/E는 현재가 ÷ EPS로 교차 검증되었습니다.<br>'
            f'<b>Trailing P/E</b> = 현재가 ÷ 과거 12개월 실적 EPS<br>'
            f'<b>Forward P/E</b> = 현재가 ÷ 향후 12개월 추정 EPS<br>섹터 P/E는 실시간 기준입니다.</div>'
            f'</div></div>'
            f'{_verdict_badge(v8_c, "", v8_t)}'
        )
        st.markdown(html_s8, unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════
    # 9️⃣ 전문가 의견
    # ═══════════════════════════════════════════════════
    rm, rk = info.get('recommendationMean'), str(info.get('recommendationKey', 'N/A')).upper()
    if isinstance(rm, (int, float)):
        if   rm <= 1.5: con, cc = "🟢 강력 매수",  "green"
        elif rm <= 2.0: con, cc = "🟢 매수",       "green"
        elif rm <= 2.5: con, cc = "🟡 매수 우위",  "yellow"
        elif rm <= 3.0: con, cc = "🟡 보유",       "yellow"
        elif rm <= 3.5: con, cc = "🔴 매도 우위",  "red"
        elif rm <= 4.0: con, cc = "🔴 매도",       "red"
        else:           con, cc = "🔴 강력 매도",  "red"
    else: con, cc = "N/A", "gray"
    all_verdicts.append(("전문가", cc))

    t_mean, t_median, t_high, t_low = target_mean, target_median, target_high, target_low
    n_ana = info.get('numberOfAnalystOpinions', 0)
    up_ref = t_median if t_median is not None else t_mean
    up_pct = ((up_ref - price) / price * 100) if isinstance(up_ref, (int, float)) and price else None
    up_str = f"{up_pct:+.1f}%" if isinstance(up_pct, (int, float)) else "N/A"

    target_corridor_html = _build_target_corridor_html(price, t_low, t_mean, t_median, t_high, n_ana)
    cc_pill_cls = "pill-green" if cc == "green" else ("pill-amber" if cc == "yellow" else "pill-red")
    if isinstance(rm, (int, float)):
        if rm <= 1.5: scale_idx = 0
        elif rm <= 2.0: scale_idx = 1
        elif rm <= 3.0: scale_idx = 2
        elif rm <= 4.0: scale_idx = 3
        else: scale_idx = 4
    else:
        scale_idx = None
    scale_tone = "buy" if scale_idx in (0, 1) else "hold" if scale_idx == 2 else "sell" if scale_idx in (3, 4) else ""
    scale_items = [
        ("강력 매수", "1.0-1.5"),
        ("매수", "1.6-2.0"),
        ("보유", "2.1-3.0"),
        ("매도", "3.1-4.0"),
        ("강력 매도", "4.1-5.0"),
    ]
    scale_html = "".join(
        f"<div class='consensus-step {'active ' + scale_tone if scale_idx == idx and scale_tone else 'active' if scale_idx == idx else ''}'><strong>{label}</strong><span>{band}</span></div>"
        for idx, (label, band) in enumerate(scale_items)
    )
    raw_range_position = ((price - t_low) / (t_high - t_low) * 100) if isinstance(price, (int, float)) and isinstance(t_low, (int, float)) and isinstance(t_high, (int, float)) and t_high != t_low else None
    range_position_pct = max(0.0, min(100.0, raw_range_position)) if isinstance(raw_range_position, (int, float)) else None
    if isinstance(raw_range_position, (int, float)):
        if raw_range_position > 100:
            range_state = "범위 상단 돌파"
        elif raw_range_position < 0:
            range_state = "범위 하단 이탈"
        elif raw_range_position >= 85:
            range_state = "범위 상단 근접"
        elif raw_range_position >= 65:
            range_state = "범위 상단권"
        elif raw_range_position >= 35:
            range_state = "범위 중앙권"
        else:
            range_state = "범위 하단권"
    else:
        range_state = "범위 정보 부족"
    target_gap_abs = (up_ref - price) if isinstance(up_ref, (int, float)) and isinstance(price, (int, float)) else None
    target_gap_text = f"{'+' if target_gap_abs >= 0 else '-'}${abs(target_gap_abs):,.2f}" if isinstance(target_gap_abs, (int, float)) else "N/A"

    with st.container(border=True):
        st.markdown('<div class="s-title"><span class="s-num">09</span> 전문가들의 의견 <span style="font-size:.8rem;color:#768390">Yahoo</span></div>', unsafe_allow_html=True)
        s9_spotlight = (
            f"<div style='display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:14px'><span class='section-pill {cc_pill_cls}'>{con}</span><span class='section-pill pill-amber'>{rk}</span></div>"
            f"<div class='spotlight-grid tight'>"
            f"<div class='spotlight-card'><p class='spotlight-label'>컨센서스</p><p class='spotlight-value'>{con}</p><p class='spotlight-sub'>평균 의견 {f'{rm:.2f}/5.0' if isinstance(rm, (int, float)) else 'N/A'}</p></div>"
            f"<div class='spotlight-card'><p class='spotlight-label'>목표가 기대여력</p><p class='spotlight-value' style='color:{'#63D9A2' if isinstance(up_pct, (int, float)) and up_pct >= 0 else '#FF8F96'}'>{up_str}</p><p class='spotlight-sub'>중앙값 또는 평균 목표가 기준</p></div>"
            f"<div class='spotlight-card'><p class='spotlight-label'>현재가 위치</p><p class='spotlight-value'>{f'{range_position_pct:.0f}%' if isinstance(range_position_pct, (int, float)) else 'N/A'}</p><p class='spotlight-sub'>{range_state}</p></div>"
            f"<div class='spotlight-card'><p class='spotlight-label'>커버리지 수</p><p class='spotlight-value'>{n_ana}명</p><p class='spotlight-sub'>의견을 낸 애널리스트 수</p></div>"
            f"</div>"
        )
        s9_target_tiles = (
            f"<div class='target-mini-grid'>"
            f"<div class='target-mini-card'><p class='target-mini-label'>현재가</p><p class='target-mini-value'>{f'${price:,.2f}' if isinstance(price, (int, float)) else 'N/A'}</p><p class='target-mini-sub'>{range_state}</p></div>"
            f"<div class='target-mini-card'><p class='target-mini-label'>중앙값 목표가</p><p class='target-mini-value'>{f'${t_median:,.2f}' if isinstance(t_median, (int, float)) else 'N/A'}</p><p class='target-mini-sub'>기대여력 {up_str}</p></div>"
            f"<div class='target-mini-card'><p class='target-mini-label'>평균 목표가</p><p class='target-mini-value'>{f'${t_mean:,.2f}' if isinstance(t_mean, (int, float)) else 'N/A'}</p><p class='target-mini-sub'>가격 간극 {target_gap_text}</p></div>"
            f"<div class='target-mini-card'><p class='target-mini-label'>최저 / 최고</p><p class='target-mini-value'>{f'${t_low:,.2f}' if isinstance(t_low, (int, float)) else 'N/A'} · {f'${t_high:,.2f}' if isinstance(t_high, (int, float)) else 'N/A'}</p><p class='target-mini-sub'>스트리트 밴드</p></div>"
            f"</div>"
        )
        s9_scale_html = (
            f"<div class='cluster-card'>"
            f"<div class='cluster-title'>컨센서스 스케일</div>"
            f"<div class='cluster-sub'>1.0에 가까울수록 강한 매수, 5.0에 가까울수록 강한 매도 의견입니다.</div>"
            f"<div class='consensus-scale'>{scale_html}</div>"
            f"{_metric_row('평균 의견', f'{rm:.2f} / 5.0' if isinstance(rm, (int, float)) else 'N/A', 'm-value m-blue')}"
            f"{_metric_row('현재가 위치', f'{range_position_pct:.0f}%' if isinstance(range_position_pct, (int, float)) else 'N/A', 'm-value')}"
            f"</div>"
        )
        s9_read_html = (
            f"<div class='insight-shell'>"
            f"<div class='cluster-title'>읽는 법</div>"
            f"<div class='cluster-sub'>현재가가 목표가 상단에 가까우면 기대가 이미 많이 반영된 상태일 수 있고, 하단에 가까우면 리레이팅 여지가 남아 있을 수 있습니다. 컨센서스는 방향 힌트이지 확정 시그널은 아닙니다.</div>"
            f"{_metric_row('현재가 vs 목표가', up_str, 'm-green' if isinstance(up_pct, (int, float)) and up_pct >= 0 else 'm-red')}"
            f"{_metric_row('참여 애널리스트', f'{n_ana}명', 'm-value')}"
            f"{_metric_row('추천 키', rk, 'm-value m-blue')}"
            f"{_metric_row('가격대 해석', range_state, 'm-value')}"
            f"</div>"
        )
        st.markdown(s9_spotlight, unsafe_allow_html=True)
        col1, col2 = st.columns([1.12, 0.88])
        with col1:
            if target_corridor_html: st.markdown(target_corridor_html, unsafe_allow_html=True)
            else: st.markdown("<div class='note-box'>※ 목표가 데이터가 충분하지 않아 코리도어 뷰가 생략되었습니다.</div>", unsafe_allow_html=True)
            st.markdown(s9_target_tiles, unsafe_allow_html=True)
        with col2:
            st.markdown(s9_scale_html, unsafe_allow_html=True)
            st.markdown(s9_read_html, unsafe_allow_html=True)
        st.markdown(_verdict_badge(cc, "", f"애널리스트 {n_ana}명 {rk} (목표가 {up_str})"), unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════
    # 🔟 지분 구조
    # ═══════════════════════════════════════════════════
    inst, ins = info.get('heldPercentInstitutions', 0) or 0, info.get('heldPercentInsiders', 0) or 0
    pub = max(0, 1 - inst - ins)
    
    if   inst > 0.7: v10_c, v10_t = "green",  "✅ 기관 선호 — 높은 기관 보유"
    elif inst > 0.4: v10_c, v10_t = "yellow", "⚠️ 혼합 지분 구조"
    else:            v10_c, v10_t = "red",    "⚠️ 기관 보유 낮음 — 개인 중심"
    all_verdicts.append(("지분구조", v10_c))

    fig10 = _get_plotly_donut(['기관', '내부자', '개인/기타'], [inst, ins, pub], ['#60A5FA', '#F6C35E', '#63D9A2'])
    pub_warning = "<br><span style='color:#FFC107;'>※ 기관/내부자 지분 합계가 100%를 초과하여 개인 지분이 0%로 표시됩니다.</span>" if inst + ins > 1 else ""
    v10_pill_cls = "pill-green" if v10_c == "green" else ("pill-amber" if v10_c == "yellow" else "pill-red")
    ownership_cards = (
        f"<div class='spotlight-grid'>"
        f"<div class='spotlight-card'><p class='spotlight-label'>총 발행 주식수</p><p class='spotlight-value'>{_fmt_num(info.get('sharesOutstanding', 0), False)} 주</p><p class='spotlight-sub'>Shares Outstanding</p></div>"
        f"<div class='spotlight-card'><p class='spotlight-label'>유통 주식수</p><p class='spotlight-value'>{_fmt_num(info.get('floatShares', 0), False)} 주</p><p class='spotlight-sub'>Float</p></div>"
        f"</div>"
    )
    ownership_stack = (
        f"<div class='ownership-stack'>"
        f"<div class='ownership-row'><div class='ownership-left'><span class='ownership-dot' style='background:#60A5FA'></span>기관 비율</div><div class='ownership-right'>{_fmt_pct(inst)}</div></div>"
        f"<div class='ownership-row'><div class='ownership-left'><span class='ownership-dot' style='background:#F6C35E'></span>내부자 비율</div><div class='ownership-right'>{_fmt_pct(ins)}</div></div>"
        f"<div class='ownership-row'><div class='ownership-left'><span class='ownership-dot' style='background:#63D9A2'></span>개인/기타(추정)</div><div class='ownership-right'>{_fmt_pct(pub)}</div></div>"
        f"</div>"
    )

    with st.container(border=True):
        st.markdown('<div class="s-title"><span class="s-num">10</span> 이 회사 누가 들고 있나요? <span style="font-size:.8rem;color:#768390">Yahoo</span></div>', unsafe_allow_html=True)
        col1, col2 = st.columns([1.1, 1])
        html_s10_1 = (
            f"<div style='display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:14px'><span class='section-pill {v10_pill_cls}'>{v10_t}</span><span class='section-pill pill-amber'>혼합 지분 구조</span></div>"
            f'{ownership_cards}'
            f'{ownership_stack}'
            f'<div class="note-box">※ "기관"에는 연기금, 뮤추얼펀드, ETF, 헤지펀드가 포함됩니다.<br>'
            f'※ "개인/기타"는 (100% - 기관 - 내부자)로 추정한 값입니다.{pub_warning}</div>'
        )
        with col1:
            st.markdown(html_s10_1, unsafe_allow_html=True)
        with col2:
            if fig10: st.plotly_chart(fig10, use_container_width=True, config={'displayModeBar': False}, key=f"{key_prefix}_fig10")
        st.markdown(_verdict_badge(v10_c, "", v10_t), unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════
    # 1️⃣01 옵션 / Max Pain 
    # ═══════════════════════════════════════════════════
    option_snapshot = _fetch_option_snapshot(ticker_str)
    exp, mp, tc, tp, is_vol_weight = option_snapshot.get("data", (None, None, None, None, False))

    mp_note, mp_c = "", "gray"
    if mp and price and price > 0:
        d = ((mp - price) / price) * 100
        if d > 2: mp_note, mp_c = f"현재가보다 <b style='color:#63D9A2'>{d:+.1f}% 위</b> → 상승 수렴 가능성", "green"
        elif d < -2: mp_note, mp_c = f"현재가보다 <b style='color:#FF8F96'>{d:+.1f}% 아래</b> → 하락 수렴 가능성", "red"
        else: mp_note, mp_c = f"현재가와 유사 ({d:+.1f}%) → 가격 유지 가능성", "yellow"
    all_verdicts.append(("옵션", mp_c))

    ch = "".join([f"<li>${ci['strike']:.1f} <span style='color:#8b949e;font-size:.8rem'>(Vol {int(ci['volume']):,})</span></li>" for ci in (tc or [])]) or "<li>N/A</li>"
    ph = "".join([f"<li>${pi['strike']:.1f} <span style='color:#8b949e;font-size:.8rem'>(Vol {int(pi['volume']):,})</span></li>" for pi in (tp or [])]) or "<li>N/A</li>"
    mp_val = f"${mp:.2f}" if mp else ""
    mp_html = f"<span style='font-size:1.8rem;font-weight:900;color:#ffffff'>{mp_val}</span>" if mp else "<span style='color:#768390;font-size:1.2rem;font-weight:700'>데이터 없음</span>"
    exp_html = f"<span style='font-size:.85rem;color:#adbac7;font-weight:700'>(만기: {exp})</span>" if exp else ""
    vol_warning = "<div style='color:#FFC107; font-size:.85rem; margin-top:12px; font-weight:700;'>⚠️ 미결제약정(OI) 부족으로 임시로 거래량(Volume) 가중치를 사용했습니다.</div>" if is_vol_weight else ""

    with st.container(border=True):
        html_s11 = (
            f'<div class="s-title"><span class="s-num">11</span> 시장은 어떤 가격을 보고 있을까요? <span style="font-size:.8rem;color:#768390">Yahoo 옵션</span></div>'
            f'<div style="text-align:center;margin:10px 0 20px">'
            f'<div style="font-size:.9rem;color:#adbac7;font-weight:700;margin-bottom:8px">Max Pain 가격 {exp_html}</div>'
            f'{mp_html}<div style="font-size:1.05rem;color:#ffffff;font-weight:700;margin-top:10px">{mp_note}</div>{vol_warning}</div>'
            f'<div class="divider"></div>'
            f'<div style="display:flex;gap:16px;flex-wrap:wrap">'
            f'<div class="opt-box" style="flex:1;min-width:220px"><b style="color:#63D9A2;font-size:1rem">🟢 Call (상승 베팅) Top 3</b><ul class="opt-list">{ch}</ul></div>'
            f'<div class="opt-box" style="flex:1;min-width:220px"><b style="color:#FF8F96;font-size:1rem">🔴 Put (하락 베팅) Top 3</b><ul class="opt-list">{ph}</ul></div></div>'
            f'<div class="note-box" style="margin-top:20px">💡 <b>Max Pain 이론</b>: 옵션 만기 시 가장 많은 옵션 매수자가 손실을 보는 가격.<br>옵션 매도자(마켓메이커)의 이익이 극대화되는 지점으로, 주가가 만기일에 이 가격 부근으로 수렴하는 경향이 있습니다.</div>'
            f'{_verdict_badge(mp_c, "", f"Max Pain {mp_val} — {mp_note.replace("<b>", "").replace("</b>", "")}" if mp else "옵션 데이터 없음")}'
        )
        st.markdown(html_s11, unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════
    # 1️⃣02 공매도
    # ═══════════════════════════════════════════════════
    sp  = info.get('shortPercentOfFloat')
    ss  = info.get('sharesShort', 0) or 0
    sr  = info.get('shortRatio')
    pss = info.get('sharesShortPriorMonth', 0) or 0

    if isinstance(sp, (int, float)):
        if   sp > 0.20: sl, sc = "매우 높음 🔴 (숏스퀴즈 가능)", "red"
        elif sp > 0.10: sl, sc = "높음 🔴", "red"
        elif sp > 0.05: sl, sc = "보통 🟡", "yellow"
        else:           sl, sc = "낮음 🟢", "green"
    else:
        sl, sc = "N/A", "gray"
    all_verdicts.append(("공매도", sc))

    short_trend = ""
    if ss > 0 and pss > 0:
        s_chg = ((ss - pss) / pss) * 100
        if   s_chg > 5:  short_trend = f"증가 [UP] ({s_chg:+.1f}% vs 전월)"
        elif s_chg < -5: short_trend = f"감소 [DOWN] ({s_chg:+.1f}% vs 전월)"
        else:            short_trend = f"유지 [FLAT] ({s_chg:+.1f}% vs 전월)"

    gauge_color = "#FF8F96" if (sp or 0) > 0.1 else ("#F6C35E" if (sp or 0) > 0.05 else "#63D9A2")
    fig12 = _get_plotly_gauge(sp or 0, gauge_color) if sp else None

    with st.container(border=True):
        st.markdown('<div class="s-title"><span class="s-num">12</span> 공매도 비율 <span style="font-size:.8rem;color:#768390">Yahoo</span></div>', unsafe_allow_html=True)
        col1, col2 = st.columns([1.1, 1])
        html_s12_1 = (
            f'{_metric_row("유통주식 대비 공매도", _fmt_pct(sp), "m-red" if sc == "red" else "m-value")}'
            f'{_metric_row("공매도 수준", sl)}'
            f'{("<div class=\'m-row\'><span class=\'m-label\'>전월 대비</span><span class=\'m-value\'>" + short_trend + "</span></div>") if short_trend else ""}'
            f'<div class="divider"></div>'
            f'{_metric_row("공매도 주식수", f"{_fmt_num(ss, False)} 주")}'
            f'{_metric_row("숏커버 일수 (DTC)", f"{sr:.2f} 일" if isinstance(sr, (int, float)) else "N/A")}'
            f'<div class="note-box">💡 공매도 비율 &gt; 10% = 높은 숏 관심<br>DTC(Days To Cover)가 높으면 숏스퀴즈 가능성 ↑<br>※ 공매도 데이터는 약 2주 지연 발표됩니다.</div>'
        )
        with col1:
            st.markdown(html_s12_1, unsafe_allow_html=True)
        with col2:
            if fig12: st.plotly_chart(fig12, use_container_width=True, config={'displayModeBar': False}, key=f"{key_prefix}_fig12")
        st.markdown(_verdict_badge(sc, "", f"공매도 {_fmt_pct(sp)} — {sl.replace('🔴', '').replace('🟡', '').replace('🟢', '').strip()}"), unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════
    # 📰 13. 최신 뉴스 
    # ═══════════════════════════════════════════════════
    try:
        news_payload = _fetch_company_news_items(ticker_str)
        if news_payload.get("items"):
            items = ""
            for n in news_payload["items"]:
                title    = n.get('title') or n.get('content', {}).get('title', '제목 없음')
                link     = n.get('link') or n.get('content', {}).get('canonicalUrl', {}).get('url', '#')
                pub_name = n.get('publisher') or n.get('content', {}).get('provider', {}).get('displayName', '')
                ts       = n.get('providerPublishTime', 0) if 'providerPublishTime' in n else 0
                if not ts: dt_str = n.get('date', (n.get('content', {}).get('pubDate', '') or '')[:16])
                else: dt_str = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')
                items += f'<div class="n-item"><a href="{_esc(link)}" target="_blank" class="n-title">{_esc(title)}</a><div class="n-meta">{_esc(pub_name)} · {dt_str}</div></div>'
            with st.container(border=True):
                st.markdown(f'<div class="s-title"><span class="s-num">13</span> 최신 뉴스 <span style="font-size:.8rem;color:#768390">Yahoo Finance</span></div>{items}', unsafe_allow_html=True)
        else: raise ValueError("No news")
    except Exception as e:
        logger.warning(f"News fetch failed: {e}")
        with st.container(border=True):
            st.markdown('<div class="s-title"><span class="s-num">13</span> 최신 뉴스</div><div style="color:#8b949e;padding:10px 0;text-align:center;">뉴스 데이터를 불러올 수 없습니다.</div>', unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════
    # 📋 종합 점수 ([SURGE] 직관적인 100점 만점 스케일로 개편)
    # ═══════════════════════════════════════════════════
    total_score, valid_count = 0, 0
    for _, c in all_verdicts:
        if c != "gray":
            valid_count += 1
            if   c == "green":  total_score += 100
            elif c == "blue":   total_score += 85
            elif c == "orange": total_score += 65   # 주황 = 잠재력 있는 고성장 구간
            elif c == "yellow": total_score += 50
            elif c == "red":    total_score += 20

    pct = (total_score / valid_count) if valid_count > 0 else 0

    score_map = {"green": 88, "blue": 78, "orange": 66, "yellow": 54, "red": 28}
    weight_map = {
        "성장사이클": 0.75, "수익성": 1.20, "과거성적": 1.10, "성장성": 0.95,
        "재무건전": 1.25, "거래량": 0.45, "변동성": 0.45, "밸류에이션": 1.00,
        "전문가": 0.55, "지분구조": 0.60, "옵션": 0.35, "공매도": 0.50,
    }
    pillar_map = {
        "성장사이클": "퀄리티", "수익성": "퀄리티", "과거성적": "퀄리티", "재무건전": "퀄리티",
        "성장성": "성장", "밸류에이션": "밸류", "전문가": "밸류",
        "거래량": "포지셔닝", "변동성": "포지셔닝", "지분구조": "포지셔닝", "옵션": "포지셔닝", "공매도": "포지셔닝",
    }
    pillar_sums = {"퀄리티": 0.0, "성장": 0.0, "밸류": 0.0, "포지셔닝": 0.0}
    pillar_weights = {"퀄리티": 0.0, "성장": 0.0, "밸류": 0.0, "포지셔닝": 0.0}
    weighted_sum, used_weight, possible_weight = 0.0, 0.0, 0.0
    for label, color in all_verdicts:
        weight = weight_map.get(label, 0.6)
        possible_weight += weight
        if color == "gray":
            continue
        score = score_map.get(color)
        if score is None:
            continue
        weighted_sum += score * weight
        used_weight += weight
        pillar = pillar_map.get(label, "포지셔닝")
        pillar_sums[pillar] += score * weight
        pillar_weights[pillar] += weight
    pct = (weighted_sum / used_weight) if used_weight > 0 else pct
    confidence = (used_weight / possible_weight * 100) if possible_weight > 0 else 0
    pillar_scores = {
        key: (pillar_sums[key] / pillar_weights[key]) if pillar_weights[key] > 0 else None
        for key in pillar_sums
    }
    pillar_cards = "".join(
        f"<div class='score-pillar'><p class='score-pillar-label'>{label}</p><p class='score-pillar-value'>{pillar_scores[label]:.0f}</p><p class='score-pillar-sub'>{desc}</p></div>"
        if pillar_scores[label] is not None else
        f"<div class='score-pillar'><p class='score-pillar-label'>{label}</p><p class='score-pillar-value'>N/A</p><p class='score-pillar-sub'>{desc}</p></div>"
        for label, desc in [
            ("퀄리티", "수익성·실적·재무체력"),
            ("성장", "향후 성장 여지"),
            ("밸류", "가격 대비 매력도"),
            ("포지셔닝", "수급·옵션·공매도"),
        ]
    ) + f"<div class='score-pillar'><p class='score-pillar-label'>데이터 신뢰도</p><p class='score-pillar-value'>{confidence:.0f}</p><p class='score-pillar-sub'>점수화 가능한 항목 커버리지</p></div>"

    if   pct >= 80: oc, oe, ot = "#63D9A2", "🟢", "매우 양호"
    elif pct >= 60: oc, oe, ot = "#F6C35E", "🟡", "양호/보통"
    elif pct >= 40: oc, oe, ot = "#FFAB66", "🟠", "주의 필요"
    else:           oc, oe, ot = "#FF8F96", "🔴", "위험"

    with st.container(border=True):
        html_s14 = (
            f'<div class="s-title" style="border:none; justify-content:center; font-size:1.6rem;">📋 종합 분석 요약</div>'
            f'<div style="text-align:center;margin:8px 0 24px"><span style="font-size:2.8rem;font-weight:900;color:{oc}">{oe} {pct:.0f}</span><span style="font-size:1.4rem;color:{oc}"> / 100점</span><br><span style="font-size:1.25rem;color:{oc};font-weight:800">{ot}</span></div>'
            f'<div style="background:rgba(0,0,0,0.4);border-radius:10px;height:16px;overflow:hidden;margin:0 40px;border:1px solid #3b424a"><div style="width:{pct:.1f}%;height:100%;background:{oc};border-radius:10px;transition:width 1s;box-shadow:0 0 10px {oc}"></div></div>'
            f'<div style="margin-top:24px">{_score_dot_row(all_verdicts)}</div>'
            f"<div class='score-pillar-grid'>{pillar_cards}</div>"
            f'<div class="note-box" style="margin-top:20px;text-align:center">종합점수는 단순 평균이 아니라 가중 평균입니다.<br>재무건전·수익성·과거실적은 더 크게, 옵션·공매도·거래량 같은 전술 항목은 더 작게 반영하고, 데이터 누락 정도는 별도 신뢰도로 표시합니다.</div>'
        )
        st.markdown(html_s14, unsafe_allow_html=True)
    st.caption("⚠️ 본 분석은 참고용 지표이며 어떠한 경우에도 투자 조언이 아닙니다. 투자에 대한 최종 결정은 본인의 판단과 책임 하에 이루어져야 합니다.")

if __name__ == "__main__":
    st.set_page_config(page_title="종목 상세 분석", page_icon="📊", layout="wide")
    st.title("종목 상세 분석 대시보드")
    t = st.text_input("🔍 티커 심볼 입력", value="AAPL", placeholder="예: AAPL, MSFT, TSLA")
    if t: render_company_details(t.strip().upper())
