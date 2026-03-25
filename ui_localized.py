import json
from textwrap import dedent

import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from company_details import render_company_details
from config import COMMITTEE_NAMES, CONTEXT_WEIGHTS, CTX_LABELS
from localization import (
    localize_action_label,
    localize_committee_name,
    localize_context_label,
    localize_judgment_label,
    localize_regime_label,
    translate_chart_text,
)


SOFT_GREEN = '#63D9A2'
SOFT_GREEN_TEXT = '#B8F1D5'
SOFT_RED = '#FF8F96'
SOFT_RED_TEXT = '#FFD2D7'
SOFT_AMBER = '#F6C35E'
SOFT_AMBER_TEXT = '#F8DE9A'
SOFT_BLUE = '#A5B4FC'


def _mini_stat_card(label, value, color, tooltip):
    return (
        f"<div class='stat-mini' title='{tooltip}'>"
        f"<p class='sm-label'>{label}</p>"
        f"<p class='sm-value' style='color:{color}'>{value}</p>"
        "</div>"
    )


def _render_ensemble_gauge(es, chart_key=None):
    gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=es,
        number={'font': {'size': 28}},
        gauge={
            'axis': {'range': [-100, 100], 'tickwidth': 1, 'tickcolor': '#64748B'},
            'bar': {'color': '#A5B4FC', 'thickness': 0.35},
            'bgcolor': 'rgba(0,0,0,0)',
            'borderwidth': 0,
            'steps': [
                {'range': [-100, -30], 'color': 'rgba(243,165,165,0.32)'},
                {'range': [-30, 30], 'color': 'rgba(245,199,123,0.22)'},
                {'range': [30, 100], 'color': 'rgba(126,216,182,0.32)'},
            ],
            'threshold': {'line': {'color': '#E2E8F0', 'width': 2}, 'thickness': 0.8, 'value': es},
        },
    ))
    gauge.update_layout(
        height=180,
        margin=dict(l=6, r=6, t=8, b=8),
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#E2E8F0'),
    )
    st.plotly_chart(gauge, use_container_width=True, theme=None, config={'displayModeBar': False}, key=chart_key)


def _risk_size_hint(atr_pct):
    if atr_pct >= 6:
        return '작게(Small)', SOFT_RED
    if atr_pct >= 3.5:
        return '줄여서(Reduced)', SOFT_AMBER_TEXT
    return '기본(Standard)', SOFT_GREEN


def _bottom_line_text(m):
    action = localize_action_label(m.get('action_label', '').strip() or m.get('judgment', 'NEUTRAL'))
    es = float(m.get('ensemble_score', 0))
    ctx = localize_context_label(m.get('context', 0))
    raw_judgment = str(m.get('judgment', ''))
    if 'BUY' in raw_judgment:
        return f"결론: {action}. 지금은 매수 우위 구간으로 보이며 분할 접근이 유리합니다. (ES {es:+.1f}, {ctx})"
    if 'SELL' in raw_judgment:
        return f"결론: {action}. 지금은 매도 우위 구간으로 보여 비중 축소나 리스크 관리가 먼저입니다. (ES {es:+.1f}, {ctx})"
    if 'MIXED' in raw_judgment:
        return f"결론: {action}. 방향성이 섞인 구간이라 추격 진입보다 관찰이 낫습니다. (ES {es:+.1f}, {ctx})"
    return f"결론: {action}. 확정 신호가 약해 확인 후 진입이 적절합니다. (ES {es:+.1f}, {ctx})"


def _narrative_text(m):
    rsi = float(m.get('rsi', 50))
    wt = float(m.get('wt1', 0))
    mom = float(m.get('buy_layers', {}).get('Momentum', 0) - m.get('sell_layers', {}).get('Momentum', 0))
    cmf = float(m.get('cmf', 0))
    bbp = float(m.get('percent_b', 0.5))
    if rsi >= 70 and mom > 0:
        return "RSI는 높지만 모멘텀이 남아 있어 과열 추세의 막바지인지 함께 봐야 합니다."
    if rsi <= 30 and mom < 0:
        return "RSI가 낮고 모멘텀도 약해 아직은 반등 기대보다 확인 신호가 더 중요합니다."
    if wt < -55 and cmf > 0:
        return "WaveTrend는 과매도권이지만 자금 흐름은 버티고 있어 바닥 반전 후보로 볼 수 있습니다."
    if wt > 55 and cmf < 0:
        return "WaveTrend는 과열권인데 자금 흐름이 약해 고점 소진 가능성을 경계해야 합니다."
    if bbp < 0.2 and mom > 0:
        return "가격은 밴드 하단 근처지만 모멘텀이 개선돼 눌림목 뒤 재상승 가능성을 볼 수 있습니다."
    if bbp > 0.8 and mom < 0:
        return "가격은 밴드 상단 근처인데 모멘텀이 둔해져 단기 조정 위험이 커진 구간입니다."
    return "추세, 모멘텀, 자금 흐름이 한쪽으로 강하게 정렬되지는 않아 확인 신호를 더 보는 편이 좋습니다."


def render_price_header(m, key_prefix="analysis"):
    chg = m['price_change']
    cp = m['price_change_pct']
    cc = 'price-change-up' if chg >= 0 else 'price-change-down'
    ci = '+' if chg >= 0 else '-'
    vr_ = m['volume'] / max(m['avg_volume'], 1)
    raw_jg = str(m.get('judgment', 'NEUTRAL'))
    cf = float(m.get('confidence', 0))
    es = float(m.get('ensemble_score', 0))
    jc = SOFT_GREEN if 'BUY' in raw_jg else (SOFT_RED if 'SELL' in raw_jg else SOFT_AMBER)
    act = localize_action_label(m.get('action_label', ''))
    regime_label = localize_regime_label(m.get('regime'), m.get('regime_label'))
    context_label = localize_context_label(m.get('context', 0))
    hero_chip = f"<span class='ind-mini' style='background:{jc}22;color:{jc};border:1px solid {jc}44' title='최종 판단과 신뢰도'>[{act}] {cf:.0f}%</span>"
    specs = [
        ('ind-b' if m['wt1'] < -20 else ('ind-s' if m['wt1'] > 20 else 'ind-n'), f"WT {m['wt1']:.0f}", "웨이브트렌드 압력"),
        ('ind-b' if m['rsi'] < 40 else ('ind-s' if m['rsi'] > 60 else 'ind-n'), f"RSI {m['rsi']:.0f}", "RSI 모멘텀"),
        ('ind-b' if vr_ > 1.5 else 'ind-n', f"거래량 {vr_:.1f}x", "평균 대비 거래량"),
        ('ind-b' if m['adx'] > 25 else 'ind-n', f"ADX {m['adx']:.0f}", "추세 강도"),
        ('ind-b' if m.get('utbot_dir', 0) == 1 else ('ind-s' if m.get('utbot_dir', 0) == -1 else 'ind-n'), 'UT 매수' if m.get('utbot_dir', 0) == 1 else ('UT 매도' if m.get('utbot_dir', 0) == -1 else 'UT 중립'), "UTBot 방향"),
        ('ind-b' if m.get('hma_rising') else 'ind-s', 'HMA 상승' if m.get('hma_rising') else 'HMA 하락', "헐 이동평균 방향"),
    ]
    chips = hero_chip + "".join([f"<span class='ind-mini {c}' title='{tip}'>{label}</span>" for c, label, tip in specs])
    insight = f"<p style='margin:0;color:#F8FAFC;font-weight:700'>{_bottom_line_text(m)}</p>"
    note = _narrative_text(m).strip()
    if note:
        insight += f"<p style='margin:6px 0 0;color:#CBD5E1;font-size:.86rem;font-weight:500'>{note}</p>"
    st.markdown(
        f"""
        <div class="price-header fade-up">
            <p style="color:#64748B;font-size:.8rem;margin:0">{m['ticker']} · {m['last_date']} · <b style="color:#A5B4FC">{regime_label}</b> · <span style='color:#A5B4FC'>시장 맥락 {context_label}</span></p>
            <p class="price-big" style="color:#F8FAFC">${m['price']:.2f}<span class="{cc}" style="font-size:1.1rem;margin-left:10px;font-weight:700">{ci}{abs(chg):.2f}({abs(cp):.2f}%)</span></p>
            <div style="margin-top:10px;display:flex;gap:4px;flex-wrap:wrap">{chips}</div>
            <div style='margin-top:12px;background:linear-gradient(140deg,rgba(99,102,241,.13),rgba(15,23,42,.75));border:1px solid rgba(99,102,241,.28);border-radius:10px;padding:10px 12px'>{insight}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    def metric_card(title, value, sub, color, fill):
        return (
            f"<div style='background:linear-gradient(165deg,rgba(15,23,42,.92),rgba(2,6,23,.86));border:1px solid rgba(148,163,184,.18);border-left:3px solid {color};border-radius:12px;padding:12px 14px;min-height:108px'>"
            f"<p style='margin:0 0 6px;color:#94A3B8;font-size:.74rem;font-weight:700'>{title}</p>"
            f"<p style='margin:0;color:{color};font-size:1.55rem;font-weight:800;line-height:1.1'>{value}</p>"
            f"<p style='margin:4px 0 8px;color:#CBD5E1;font-size:.78rem'>{sub}</p>"
            f"<div style='height:7px;background:rgba(148,163,184,.15);border-radius:999px;overflow:hidden'><div style='height:100%;width:{fill:.1f}%;background:{color};border-radius:999px'></div></div>"
            "</div>"
        )

    bt_ = float(m.get('buy_total', 0))
    st_ = float(m.get('sell_total', 0))
    ba_ = int(m.get('buy_active', 0))
    sa_ = int(m.get('sell_active', 0))
    h52 = float(m.get('high_52w', m['price']))
    l52 = float(m.get('low_52w', m['price']))
    rng = max(h52 - l52, 0.01)
    pos52 = min(max((m['price'] - l52) / rng * 100, 0), 100)
    metric_html = "".join([
        metric_card("종합 점수", f"{es:+.1f}", f"매수 합의 {m.get('buy_agree', 0)} · 매도 합의 {m.get('sell_agree', 0)}", jc, min(abs(es) / 80 * 100, 100)),
        metric_card("매수 압력", f"{bt_:.1f}", f"활성 레이어 {ba_}/10", SOFT_GREEN, min(bt_ / 40 * 100, 100)),
        metric_card("매도 압력", f"{st_:.1f}", f"활성 레이어 {sa_}/10", SOFT_RED, min(st_ / 40 * 100, 100)),
        metric_card("52주 위치", f"{pos52:.0f}%", f"저점 {l52:.2f} · 고점 {h52:.2f}", SOFT_BLUE, pos52),
    ])
    st.markdown(f"<div style='display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:10px 0 14px'>{metric_html}</div>", unsafe_allow_html=True)
    _render_ensemble_gauge(es, chart_key=f"{key_prefix}_ensemble_gauge")


def render_judgment_card(m):
    raw_jg = str(m.get('judgment', 'NEUTRAL'))
    jg = localize_judgment_label(raw_jg)
    action = localize_action_label(m.get('action_label', ''))
    es = float(m.get('ensemble_score', 0))
    cf = float(m.get('confidence', 0))
    ba = int(m.get('buy_agree', 0))
    sa = int(m.get('sell_agree', 0))
    veto = str(m.get('veto_flags', '')).strip()
    syn = float(m.get('reversal_synergy', 0))
    pred = float(m.get('prediction_boost', 0))
    detail_text = (str(m.get('judgment_detail', '')).strip() or str(m.get('judgment_reason', '')).strip())
    contrast = str(m.get('contrast_notes', '')).strip()
    jc = SOFT_GREEN if 'BUY' in raw_jg else (SOFT_RED if 'SELL' in raw_jg else SOFT_AMBER)
    cc = 'score-card-buy' if 'BUY' in raw_jg else ('score-card-sell' if 'SELL' in raw_jg else 'score-card-neutral')
    risk_tags = []
    if m.get('smart_money_bearish_div'):
        risk_tags.append(("스마트 머니 약세 다이버전스", SOFT_RED))
    elif m.get('smart_money_bullish_div'):
        risk_tags.append(("자금 흐름 지지", SOFT_GREEN))
    if float(m.get('volume_ratio_20', 1) or 1) < 0.7:
        risk_tags.append((f"저거래량 {float(m.get('volume_ratio_20', 1)):.1f}x", SOFT_AMBER_TEXT))
    if m.get('blowoff_top_hard'):
        risk_tags.append(("급등 과열 경고", SOFT_RED))
    chips = "".join([f"<span style='display:inline-flex;align-items:center;gap:4px;padding:4px 9px;border-radius:999px;background:{col}22;border:1px solid {col}44;color:{col};font-size:.72rem;font-weight:700'>{label}</span>" for label, col in risk_tags])
    detail_html = ""
    if detail_text:
        detail_html = (
            f"<div style='margin:16px 0;background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.06);border-radius:12px;padding:14px 18px;border-left:3px solid {jc}'>"
            "<p style='color:#94A3B8;font-size:.72rem;font-weight:700;margin:0 0 6px'>판단 근거 요약</p>"
            f"<p style='color:#CBD5E1;font-size:.82rem;margin:0'>{translate_chart_text(detail_text)}</p>"
            "</div>"
        )
    risk_html = ""
    if contrast or risk_tags:
        contrast_html = f"<p style='color:#CBD5E1;font-size:.8rem;margin:0 0 10px'>{translate_chart_text(contrast)}</p>" if contrast else ""
        risk_html = (
            "<div style='margin:14px 0 0;background:rgba(15,23,42,.58);border:1px solid rgba(148,163,184,.14);border-radius:12px;padding:14px 16px'>"
            "<p style='color:#94A3B8;font-size:.72rem;font-weight:700;margin:0 0 8px'>위험 점검(Risk Check)</p>"
            f"{contrast_html}<div style='display:flex;gap:8px;flex-wrap:wrap'>{chips}</div>"
            "</div>"
        )
    badge_parts = []
    if abs(syn) > 5:
        badge_parts.append(f"<span style='background:rgba({'52,211,153' if syn > 0 else '248,113,113'},.12);color:{SOFT_GREEN if syn > 0 else SOFT_RED};padding:3px 8px;border-radius:6px;font-size:.72rem;font-weight:700'>반전 시너지 {syn:+.1f}</span>")
    if abs(pred) > 3:
        badge_parts.append(f"<span style='background:rgba({'52,211,153' if pred > 0 else '248,113,113'},.12);color:{SOFT_GREEN if pred > 0 else SOFT_RED};padding:3px 8px;border-radius:6px;font-size:.72rem;font-weight:700'>예측 보정 {pred:+.1f}</span>")
    badges = "".join(badge_parts)
    veto_html = f"<div style='margin-top:8px;text-align:center'><span style='background:rgba(243,165,165,.15);color:{SOFT_RED_TEXT};padding:4px 10px;border-radius:6px;font-size:.72rem;font-weight:700'>제한 조건 {veto}</span></div>" if veto else ""
    circ = 2 * 3.14159 * 36
    offset = circ * (1 - cf / 100)
    es_norm = min(max((es + 80) / 160 * 100, 0), 100)
    ba_pct = ba / max(ba + sa, 1) * 100
    st.markdown(
        dedent(
            f"""
            <div class="score-card {cc} fade-up">
                <div style="display:flex;align-items:center;justify-content:center;gap:28px;flex-wrap:wrap">
                    <div class="conf-ring"><svg viewBox="0 0 80 80"><circle class="ring-bg" cx="40" cy="40" r="36"/><circle class="ring-fg" cx="40" cy="40" r="36" stroke="{jc}" stroke-dasharray="{circ:.1f}" stroke-dashoffset="{offset:.1f}"/></svg><span class="ring-text" style="color:{jc}">{cf:.0f}%</span></div>
                    <div>
                        <p style="font-size:1.8rem;font-weight:800;color:{jc};margin:0;letter-spacing:-.5px">{action or jg}</p>
                        <p style="margin:8px 0 0;color:#CBD5E1;font-size:.8rem;text-align:center">{jg}</p>
                    </div>
                </div>{detail_html}{risk_html}
                <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-top:14px">
                    <div style="background:rgba(255,255,255,.03);border-radius:10px;padding:12px;text-align:center">
                        <p style="color:#64748B;font-size:.68rem;font-weight:700;margin:0 0 4px">종합 점수</p>
                        <p style="color:{jc};font-size:1.3rem;font-weight:800;margin:0">{es:+.1f}</p>
                        <div style="height:3px;background:rgba(255,255,255,.06);border-radius:2px;margin-top:6px;overflow:hidden"><div style="height:100%;width:{es_norm}%;background:{jc};border-radius:2px"></div></div>
                    </div>
                    <div style="background:rgba(255,255,255,.03);border-radius:10px;padding:12px;text-align:center">
                        <p style="color:#64748B;font-size:.68rem;font-weight:700;margin:0 0 4px">매수:매도 합의</p>
                        <p style="color:#F8FAFC;font-size:1.3rem;font-weight:800;margin:0">{ba}:{sa}</p>
                        <div style="height:3px;background:rgba(243,165,165,.28);border-radius:2px;margin-top:6px;overflow:hidden"><div style="height:100%;width:{ba_pct}%;background:{SOFT_GREEN};border-radius:2px"></div></div>
                    </div>
                    <div style="background:rgba(255,255,255,.03);border-radius:10px;padding:12px;text-align:center">
                        <p style="color:#64748B;font-size:.68rem;font-weight:700;margin:0 0 4px">시장 맥락</p>
                        <p style="color:#A5B4FC;font-size:1.05rem;font-weight:800;margin:0">{localize_context_label(m.get('context', 0))}</p>
                        <div style="height:3px;background:rgba(165,180,252,.15);border-radius:2px;margin-top:6px;overflow:hidden"><div style="height:100%;width:100%;background:#A5B4FC;border-radius:2px;opacity:.4"></div></div>
                    </div>
                </div>
                <div style='margin-top:10px;display:flex;justify-content:center;gap:8px;flex-wrap:wrap'>{badges}</div>{veto_html}
            </div>
            """
        ).strip(),
        unsafe_allow_html=True,
    )


def render_committee_panel(m):
    committee = m.get('committee', {})
    if not committee:
        return
    ctx_code = m.get('context', 0)
    ctx_name = CTX_LABELS.get(ctx_code, 'default')
    weights = CONTEXT_WEIGHTS.get(ctx_name, CONTEXT_WEIGHTS['default'])
    vote_map = {'BUY': '매수', 'SELL': '매도', 'NEUTRAL': '중립', 'ABSTAIN': '보류'}
    cards = []
    for idx, cm in enumerate(COMMITTEE_NAMES):
        data = committee.get(cm, {})
        score = float(data.get('score', 0))
        conv = float(data.get('conviction', 0))
        vote = data.get('vote', 'NEUTRAL')
        weight = weights[idx] if idx < len(weights) else 0.2
        color = SOFT_GREEN if score > 0 else (SOFT_RED if score < 0 else '#94A3B8')
        vote_style = f'background:rgba(126,216,182,.14);color:{SOFT_GREEN}' if vote == 'BUY' else (f'background:rgba(243,165,165,.14);color:{SOFT_RED}' if vote == 'SELL' else ('background:rgba(71,85,105,.3);color:#64748B' if vote == 'ABSTAIN' else f'background:rgba(245,199,123,.14);color:{SOFT_AMBER}'))
        width = min(abs(score) / 40 * 100, 100)
        cards.append(
            f"<div class='cm-card' style='border-left:3px solid {color}'>"
            f"<p class='cm-name'>{localize_committee_name(cm)} · 비중 {weight:.0%}</p>"
            f"<p class='cm-score' style='color:{color}'>{score:+.0f}</p>"
            f"<span class='cm-vote' style='{vote_style}'>{vote_map.get(vote, vote)}</span>"
            f"<p style='color:#64748B;font-size:.65rem;margin:4px 0 0'>확신도 {conv:.0f}%</p>"
            f"<div class='cm-mini-bar'><div class='cm-mini-fill' style='width:{width}%;background:{color}'></div></div>"
            "</div>"
        )
    st.markdown(f"<div style='display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-top:12px'>{''.join(cards)}</div>", unsafe_allow_html=True)
    if m.get('veto_flags'):
        st.warning(f"제한 조건: {m.get('veto_flags')}")
    if abs(float(m.get('reversal_synergy', 0))) > 5:
        st.info(f"반전 시너지: {float(m.get('reversal_synergy', 0)):+.1f}")


def render_10layer_bars(m, html_key="analysis"):
    layer_names = ['Trend', 'Momentum', 'Candle', 'BB', 'Volume', 'MF', 'Pattern', 'Combined', 'Leading', 'Lagging']
    layer_labels = {'Trend': '추세', 'Momentum': '모멘텀', 'Candle': '캔들', 'BB': '볼린저', 'Volume': '거래량', 'MF': '자금 흐름', 'Pattern': '패턴', 'Combined': '콤보', 'Leading': '선행', 'Lagging': '후행'}
    rows = []
    for name in layer_names:
        bv = max(float(m.get('buy_layers', {}).get(name, 0)), 0.0)
        sv = max(float(m.get('sell_layers', {}).get(name, 0)), 0.0)
        bpct = min((bv / 12.0) * 50.0, 50.0)
        spct = min((sv / 12.0) * 50.0, 50.0)
        rows.append(
            f"<div style='display:grid;grid-template-columns:58px 1fr 58px;gap:10px;align-items:center;margin-bottom:8px;padding:2px;border-radius:10px'>"
            f"<div style='text-align:right;color:{SOFT_GREEN};font-size:.88rem;font-weight:700'>{bv:.1f}</div>"
            "<div style='position:relative;height:30px;border-radius:10px;border:1px solid rgba(148,163,184,.2);background:linear-gradient(90deg,rgba(126,216,182,.08),rgba(148,163,184,.04),rgba(243,165,165,.08));overflow:hidden'>"
            f"<div style='position:absolute;left:{50.0 - bpct:.2f}%;top:4px;bottom:4px;width:{bpct:.2f}%;background:linear-gradient(90deg,#237650,#63D9A2);border-radius:6px 0 0 6px'></div>"
            f"<div style='position:absolute;left:50%;top:4px;bottom:4px;width:{spct:.2f}%;background:linear-gradient(90deg,#FF8F96,#8A4B54);border-radius:0 6px 6px 0'></div>"
            "<div style='position:absolute;left:50%;top:0;bottom:0;width:1px;background:rgba(226,232,240,.55)'></div>"
            f"<div style='position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);font-size:.72rem;color:#CBD5E1;font-weight:700;background:rgba(2,6,23,.78);padding:2px 8px;border-radius:999px;border:1px solid rgba(148,163,184,.25)'>{layer_labels.get(name, name)}</div>"
            "</div>"
            f"<div style='text-align:left;color:{SOFT_RED};font-size:.88rem;font-weight:700'>{sv:.1f}</div>"
            "</div>"
        )
    panel_html = (
        "<div style='background:rgba(15,19,32,.55);backdrop-filter:blur(12px);border:1px solid rgba(255,255,255,.08);border-radius:14px;padding:16px 14px;margin-bottom:12px'>"
        "<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:8px'>"
        f"<span style='color:{SOFT_GREEN};font-weight:800;font-size:.86rem'>매수 ({int(m.get('buy_active', 0))}/10)</span>"
        "<span style='color:#94A3B8;font-size:.76rem;font-weight:700'>10개 레이어 비교</span>"
        f"<span style='color:{SOFT_RED};font-weight:800;font-size:.86rem'>매도 ({int(m.get('sell_active', 0))}/10)</span>"
        "</div>"
        "<div style='display:flex;justify-content:center;gap:10px;margin:0 0 10px'>"
        f"<span style='color:{SOFT_GREEN};font-size:.7rem'>왼쪽 = 매수 압력</span>"
        f"<span style='color:{SOFT_RED};font-size:.7rem'>오른쪽 = 매도 압력</span>"
        "</div>"
        + "".join(rows) +
        "</div>"
    )
    html_doc = f"<!doctype html><html><head><meta charset='utf-8'></head><body style='margin:0;background:transparent;color:#E2E8F0;font-family:Pretendard,system-ui,sans-serif'><!-- {html_key} -->{panel_html}</body></html>"
    components.html(html_doc, height=max(430, 120 + len(layer_names) * 44), scrolling=False)


def render_leading_lagging(m):
    lv = translate_chart_text(m.get('leading_verdict', ''))
    lgv = translate_chart_text(m.get('lagging_verdict', ''))
    ac = float(m.get('composite_accel', 0))
    spb = float(m.get('setup_pressure_buy', 0))
    sps = float(m.get('setup_pressure_sell', 0))
    maxsp = max(spb, sps, 1)
    bw = min(spb / maxsp * 50, 50)
    sw = min(sps / maxsp * 50, 50)
    tow_label = f"매수 압력 {spb:.1f}" if spb > sps else (f"매도 압력 {sps:.1f}" if sps > spb else "균형")
    tow_color = SOFT_GREEN if spb > sps else (SOFT_RED if sps > spb else SOFT_AMBER)
    flow_text = '하락 다이버전스' if m.get('smart_money_bearish_div') else ('상승 지지' if m.get('smart_money_bullish_div') else '중립')
    flow_color = SOFT_RED if m.get('smart_money_bearish_div') else (SOFT_GREEN if m.get('smart_money_bullish_div') else '#94A3B8')
    size_label, size_color = _risk_size_hint(float(m.get('atr_pct', 0)))
    st.markdown(f"""<div style='display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px'>
        <div style='background:rgba(255,255,255,.03);border:1px solid #1E293B;border-radius:12px;padding:16px'>
            <p style='font-weight:700;color:#A5B4FC;margin:0 0 8px;font-size:.85rem'>선행 지표(Leading)</p>
            <p style='color:{SOFT_GREEN if ac >= 0 else SOFT_RED};font-weight:800;font-size:1.15rem;margin:0 0 8px'>{lv}</p>
            <div style='display:flex;gap:10px;flex-wrap:wrap'>
                <span style='color:#94A3B8;font-size:.78rem'>가속도: <b style='color:{SOFT_GREEN if ac > 0 else SOFT_RED}'>{ac:+.2f}</b></span>
                <span style='color:#94A3B8;font-size:.78rem'>UT: {'매수' if m.get('utbot_dir', 0) == 1 else ('매도' if m.get('utbot_dir', 0) == -1 else '중립')}</span>
                <span style='color:#94A3B8;font-size:.78rem'>Hull: {'상승' if m.get('hma_rising') else '하락'}</span>
            </div>
        </div>
        <div style='background:rgba(255,255,255,.03);border:1px solid #1E293B;border-radius:12px;padding:16px'>
            <p style='font-weight:700;color:#A5B4FC;margin:0 0 8px;font-size:.85rem'>후행 지표(Lagging)</p>
            <p style='color:{SOFT_GREEN if "상승" in lgv else (SOFT_RED if "하락" in lgv else SOFT_AMBER)};font-weight:800;font-size:1.15rem;margin:0 0 8px'>{lgv}</p>
            <div style='display:flex;gap:14px'>
                <span style='color:#94A3B8;font-size:.78rem'>시장 국면: <b>{localize_regime_label(m.get('regime'), m.get('regime_label'))}</b></span>
                <span style='color:#94A3B8;font-size:.78rem'>RS: <b>{m.get('rs_ratio', 1):.3f}</b></span>
            </div>
        </div>
    </div>""", unsafe_allow_html=True)
    st.markdown(f"""<div style='background:rgba(255,255,255,.03);border:1px solid #1E293B;border-radius:12px;padding:14px;margin-bottom:12px'>
        <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:4px'>
            <span style='color:{SOFT_GREEN};font-size:.78rem;font-weight:700'>매수 압력 {spb:.1f}</span>
            <span style='color:{tow_color};font-size:.78rem;font-weight:700'>{tow_label}</span>
            <span style='color:{SOFT_RED};font-size:.78rem;font-weight:700'>매도 압력 {sps:.1f}</span>
        </div>
        <div class='tow-bar'><div class='tow-buy' style='width:{bw}%'></div><div class='tow-sell' style='width:{sw}%'></div><div class='tow-center'></div></div>
    </div>""", unsafe_allow_html=True)
    cards = "".join([
        _mini_stat_card('BB %B', f"{float(m.get('percent_b', 0.5)) * 100:.0f}%", SOFT_GREEN if float(m.get('percent_b', 0.5)) < 0.3 else (SOFT_RED if float(m.get('percent_b', 0.5)) > 0.7 else SOFT_AMBER), '볼린저 밴드 안에서 현재 위치를 보여줍니다.'),
        _mini_stat_card('CMF', f"{float(m.get('cmf', 0)):+.3f}", SOFT_GREEN if float(m.get('cmf', 0)) > 0.05 else (SOFT_RED if float(m.get('cmf', 0)) < -0.05 else '#94A3B8'), '0 위면 자금 유입 우위, 0 아래면 자금 이탈 우위로 봅니다.'),
        _mini_stat_card('자금 흐름', flow_text, flow_color, '가격과 자금 흐름의 방향이 같은지, 다이버전스가 있는지 봅니다.'),
        _mini_stat_card('OBV 기울기', f"{float(m.get('obv_slope', 0)):+.2f}", SOFT_GREEN if float(m.get('obv_slope', 0)) > 0 else (SOFT_RED if float(m.get('obv_slope', 0)) < 0 else '#94A3B8'), 'OBV 기울기로 거래량 흐름의 방향을 봅니다.'),
        _mini_stat_card('최근 거래량', f"{float(m.get('volume_ratio_20', 1)):.1f}x", SOFT_GREEN if float(m.get('volume_ratio_20', 1)) >= 1 else (SOFT_AMBER_TEXT if float(m.get('volume_ratio_20', 1)) >= 0.7 else SOFT_RED), '최근 거래량이 20일 평균 대비 얼마나 붙는지 보여줍니다.'),
        _mini_stat_card('매수 손익비', f"{float(m.get('vp_long_rr', 1)):.2f}", SOFT_GREEN if float(m.get('vp_long_rr', 1)) >= 1.35 else (SOFT_AMBER_TEXT if float(m.get('vp_long_rr', 1)) >= 1 else SOFT_RED), '현재가 기준 매수 관점 손익비입니다.'),
        _mini_stat_card('매도 손익비', f"{float(m.get('vp_short_rr', 1)):.2f}", SOFT_GREEN if float(m.get('vp_short_rr', 1)) >= 1.35 else (SOFT_AMBER_TEXT if float(m.get('vp_short_rr', 1)) >= 1 else SOFT_RED), '현재가 기준 매도 관점 손익비입니다.'),
        _mini_stat_card('ATR%', f"{float(m.get('atr_pct', 0)):.1f}%", SOFT_BLUE, '평균 변동폭이 현재가 대비 어느 정도인지 보여줍니다.'),
        _mini_stat_card('권장 비중', size_label, size_color, '변동성이 높을수록 포지션 크기를 줄이는 편이 안전합니다.'),
        _mini_stat_card('50일선 거리', f"{float(m.get('ma50_dist', 0)):+.1f}%", SOFT_GREEN if float(m.get('ma50_dist', 0)) > 0 else SOFT_RED, '현재가와 50일선 사이 거리입니다.'),
        _mini_stat_card('200일선 거리', f"{float(m.get('ma200_dist', 0)):+.1f}%", SOFT_GREEN if float(m.get('ma200_dist', 0)) > 0 else SOFT_RED, '현재가와 200일선 사이 거리입니다.'),
    ])
    st.markdown(f"<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:8px'>{cards}</div>", unsafe_allow_html=True)


def render_combined_scans(m):
    scans = m.get('combined_scans', [])
    if not scans:
        st.info("현재 활성화된 콤보 스캔이 없습니다.")
        return
    bn = sum(1 for s in scans if s['dir'] == 'buy')
    sn_ = sum(1 for s in scans if s['dir'] == 'sell')
    t1 = sum(1 for s in scans if s['tier'] == 1)
    hc = '#E8C56C' if t1 > 0 else (SOFT_GREEN if bn > sn_ else (SOFT_RED if sn_ > bn else SOFT_AMBER))
    st.markdown(f"<div style='background:rgba(255,215,0,.06);border:1px solid {hc}33;border-radius:12px;padding:12px;margin-bottom:10px'><span style='font-size:1.2rem;font-weight:800;color:{hc}'>콤보 스캔 {len(scans)}개 활성</span> <span style='color:#94A3B8;margin-left:12px'>T1:{t1} · 매수:{bn} · 매도:{sn_}</span></div>", unsafe_allow_html=True)
    cards = []
    for s in scans:
        tier = {1: '핵심 T1', 2: '보강 T2', 3: '참고 T3'}.get(s['tier'], '참고')
        is_buy = s['dir'] == 'buy'
        is_sell = s['dir'] == 'sell'
        color = SOFT_GREEN if is_buy else (SOFT_RED if is_sell else SOFT_AMBER)
        bg = 'linear-gradient(160deg,rgba(5,46,22,.55),rgba(15,23,42,.6))' if is_buy else ('linear-gradient(160deg,rgba(69,10,10,.55),rgba(30,41,59,.6))' if is_sell else 'linear-gradient(160deg,rgba(120,53,15,.5),rgba(30,41,59,.6))')
        side = '상승' if is_buy else ('하락' if is_sell else '중립')
        date_badge = "<span style='background:#FFD700;color:#111827;padding:2px 6px;border-radius:999px;font-size:.64rem;font-weight:800'>오늘</span>" if s.get('is_today') else f"<span style='color:#94A3B8;font-size:.72rem'>{s['date']}</span>"
        cards.append(
            f"<div style='background:{bg};border:1px solid {color}55;border-radius:14px;padding:12px 12px 10px;box-shadow:0 8px 24px rgba(0,0,0,.25)'>"
            f"<div style='display:flex;justify-content:space-between;align-items:center;gap:8px'><span style='color:{color};font-weight:800'>{side} · {s['kor']}</span><span style='color:#E2E8F0;font-size:.68rem;background:rgba(15,23,42,.6);padding:2px 8px;border-radius:999px'>{tier}</span></div>"
            f"<div style='margin-top:8px;display:flex;justify-content:space-between;align-items:center'><span style='color:#60A5FA;font-size:.72rem'>승률 {s['win']}</span>{date_badge}</div>"
            "</div>"
        )
    st.markdown(f"<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px'>{''.join(cards)}</div>", unsafe_allow_html=True)


def render_indicator_help():
    with st.expander("차트 읽는 법 / 지표 설명", expanded=False):
        st.markdown(
            "- `최종 판단 / 신뢰도`: 지금 시점에서 시스템이 보는 기본 방향과 신뢰도입니다.\n"
            "- `위험 점검(Risk Check)`: 스마트 머니 다이버전스, 손익비, 저거래량, 과열 경고를 모아 보여줍니다.\n"
            "- `WT1`: 과매수/과매도 압력을 빠르게 보는 지표입니다.\n"
            "- `ADX`: 추세의 강도를 보여주며 방향 자체를 뜻하지는 않습니다.\n"
            "- `CMF / OBV 기울기`: 자금 유입과 이탈 흐름을 보는 보조 지표입니다.\n"
            "- `종합 점수(Ensemble Score)`: -100~+100 범위의 종합 방향 점수입니다.\n"
            "- `10개 레이어`: 추세, 모멘텀, 구조, 자금 흐름 등이 매수/매도 쪽으로 얼마나 기여하는지 비교합니다."
        )


def render_analysis(msg, key_prefix="analysis"):
    m, fj = msg.get('meta'), msg.get('fig_json')
    if m:
        render_price_header(m, key_prefix=key_prefix)
    if m or fj:
        t0, t1, t2, t3, t4 = st.tabs(["차트", "판단/리스크", "10개 레이어", "콤보 스캔", "기업 정보"])
        with t0:
            if fj:
                fig = go.Figure(json.loads(fj))
                st.plotly_chart(fig, use_container_width=True, theme=None, config={'displaylogo': False, 'modeBarButtonsToRemove': ['lasso2d', 'select2d']}, key=f"{key_prefix}_price_chart")
                st.caption("*캔들 툴팁, 거래량 프로파일(VP), 자동 추세선/평행채널, 패턴 오버레이를 제공합니다. 모바일에서는 판단 카드 확인 후 차트를 열면 더 읽기 쉽습니다.")
        with t1:
            if m:
                render_judgment_card(m)
                st.markdown("#### 5위원회 종합 판단")
                render_committee_panel(m)
                st.markdown("---")
                render_leading_lagging(m)
                render_indicator_help()
        with t2:
            if m:
                render_10layer_bars(m, html_key=f"{key_prefix}_10layer")
        with t3:
            if m:
                render_combined_scans(m)
        with t4:
            if m:
                render_company_details(m['ticker'], key_prefix=f"{key_prefix}_company")
