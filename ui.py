import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.graph_objects as go
import json
from config import *
from chart import build_metadata, build_chart
from company_details import render_company_details

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

def _bottom_line_text(m):
    action=m.get('action_label','').strip() or m.get('judgment','NEUTRAL')
    es=float(m.get('ensemble_score',0));ctx=m.get('context_label','기본')
    if 'BUY' in str(m.get('judgment','')):
        return f"결론: {action}. 지금은 매수 우위 구간이며, 분할 진입 관점이 유효합니다. (ES {es:+.1f}, {ctx})"
    if 'SELL' in str(m.get('judgment','')):
        return f"결론: {action}. 지금은 매도/리스크 관리 우위 구간이며, 비중 축소가 우선입니다. (ES {es:+.1f}, {ctx})"
    if str(m.get('judgment',''))=='MIXED':
        return f"결론: {action}. 방향성 혼재 구간이라 신규 진입보다 관망이 유리합니다. (ES {es:+.1f}, {ctx})"
    return f"결론: {action}. 확정 신호가 약해 관망 후 확인 진입이 적절합니다. (ES {es:+.1f}, {ctx})"

def _narrative_text(m):
    rsi=float(m.get('rsi',50));wt=float(m.get('wt1',0));mom=float(m.get('buy_layers',{}).get('Momentum',0)-m.get('sell_layers',{}).get('Momentum',0))
    cmf=float(m.get('cmf',0));bbp=float(m.get('percent_b',0.5))
    if rsi>=70 and mom>0:
        return "RSI가 과매수권이지만 모멘텀 레이어가 여전히 우세해 추세 관성은 살아 있습니다."
    if rsi<=30 and mom<0:
        return "RSI가 과매도권이며 모멘텀도 약세라, 반등은 확인 신호 동반 시에만 유효합니다."
    if wt<-55 and cmf>0:
        return "WaveTrend 과매도와 자금 유입(CMF+)이 겹쳐 바닥 반전 시나리오 확률이 높아지는 구간입니다."
    if wt>55 and cmf<0:
        return "WaveTrend 과매수와 자금 이탈(CMF-)이 동반되어 고점 소진 가능성을 경계해야 합니다."
    if bbp<0.2 and mom>0:
        return "가격이 밴드 하단 근처이면서 모멘텀이 개선되어 눌림 이후 재상승 구조로 해석됩니다."
    if bbp>0.8 and mom<0:
        return "가격이 밴드 상단에 위치한 상태에서 모멘텀이 둔화되어 단기 조정 리스크가 커졌습니다."
    return "추세·모멘텀·자금흐름이 뚜렷하게 한쪽으로 쏠리진 않아, 확인형 대응이 유리합니다."

def _render_ensemble_gauge(es, chart_key=None):
    gauge=go.Figure(go.Indicator(
        mode="gauge+number",
        value=es,
        number={'suffix':'', 'font':{'size':28}},
        gauge={
            'axis':{'range':[-100,100], 'tickwidth':1, 'tickcolor':'#64748B'},
            'bar':{'color':'#A5B4FC', 'thickness':0.35},
            'bgcolor':'rgba(0,0,0,0)',
            'borderwidth':0,
            'steps':[
                {'range':[-100,-30],'color':'rgba(243,165,165,0.32)'},
                {'range':[-30,30],'color':'rgba(245,199,123,0.22)'},
                {'range':[30,100],'color':'rgba(126,216,182,0.32)'},
            ],
            'threshold':{'line':{'color':'#E2E8F0','width':2},'thickness':0.8,'value':es}
        }
    ))
    gauge.update_layout(height=180,margin=dict(l=6,r=6,t=8,b=8),paper_bgcolor='rgba(0,0,0,0)',font=dict(color='#E2E8F0'))
    st.plotly_chart(gauge,use_container_width=True,theme=None,config={'displayModeBar':False}, key=chart_key)

def render_price_header(m, key_prefix="analysis"):
    chg = m['price_change']
    cp = m['price_change_pct']
    cc = 'price-change-up' if chg >= 0 else 'price-change-down'
    ci = '+' if chg >= 0 else '-'

    vr_ = m['volume'] / max(m['avg_volume'], 1)
    jg = m['judgment']
    cf = m['confidence']
    es = float(m.get('ensemble_score', 0))
    jc = SOFT_GREEN if 'BUY' in jg else (SOFT_RED if 'SELL' in jg else SOFT_AMBER)

    act = m.get('action_label', '')
    hero_chip = f"<span class='ind-mini' style='background:{jc}22;color:{jc};border:1px solid {jc}44' title='Final action and confidence'>[{act}] {cf:.0f}%</span>"
    specs = [
        ('ind-b' if m['wt1'] < -20 else ('ind-s' if m['wt1'] > 20 else 'ind-n'), f"WT{m['wt1']:.0f}", "WaveTrend pressure"),
        ('ind-b' if m['rsi'] < 40 else ('ind-s' if m['rsi'] > 60 else 'ind-n'), f"RSI{m['rsi']:.0f}", "RSI momentum"),
        ('ind-b' if vr_ > 1.5 else 'ind-n', f"Vol{vr_:.1f}x", "Volume vs average"),
        ('ind-b' if m['adx'] > 25 else 'ind-n', f"ADX{m['adx']:.0f}", "Trend strength"),
        ('ind-b' if m.get('utbot_dir', 0) == 1 else ('ind-s' if m.get('utbot_dir', 0) == -1 else 'ind-n'), '[UT] B' if m.get('utbot_dir', 0) == 1 else ('[UT] S' if m.get('utbot_dir', 0) == -1 else '[UT] -'), "UT direction"),
        ('ind-b' if m.get('hma_rising') else 'ind-s', '[HMA] UP' if m.get('hma_rising') else '[HMA] DN', "Hull direction"),
    ]
    ih = hero_chip + "".join([f"<span class='ind-mini {c}' title='{tip}'>{l}</span>" for c, l, tip in specs])

    bottom = _bottom_line_text(m).strip()
    narrative = _narrative_text(m).strip()
    insight_body = f"<p style='margin:0;color:#F8FAFC;font-weight:700'>{bottom}</p>"
    if narrative and narrative not in bottom:
        insight_body += f"<p style='margin:6px 0 0;color:#CBD5E1;font-size:.86rem;font-weight:500'>{narrative}</p>"

    st.markdown(
        f"""
        <div class="price-header fade-up">
            <p style="color:#64748B;font-size:.8rem;margin:0">{m['ticker']} - {m['last_date']} - <b style="color:#A5B4FC">{m['regime_label']}</b> - <span style='color:#A5B4FC'>[CTX] {m.get('context_label', 'default')}</span></p>
            <p class="price-big" style="color:#F8FAFC">${m['price']:.2f}<span class="{cc}" style="font-size:1.1rem;margin-left:10px;font-weight:700">{ci}{abs(chg):.2f}({abs(cp):.2f}%)</span></p>
            <div style="margin-top:10px;display:flex;gap:4px;flex-wrap:wrap">{ih}</div>
            <div style='margin-top:12px;background:linear-gradient(140deg,rgba(99,102,241,.13),rgba(15,23,42,.75));border:1px solid rgba(99,102,241,.28);border-radius:10px;padding:10px 12px'>
                {insight_body}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    esc = SOFT_GREEN if es > 0 else (SOFT_RED if es < 0 else SOFT_AMBER)
    es_pct = min(abs(es) / 80 * 100, 100)
    bt_ = float(m.get('buy_total', 0))
    st_ = float(m.get('sell_total', 0))
    ba_ = int(m.get('buy_active', 0))
    sa_ = int(m.get('sell_active', 0))
    bt_pct = min(bt_ / 40 * 100, 100)
    st_pct = min(st_ / 40 * 100, 100)

    h52 = float(m.get('high_52w', m['price']))
    l52 = float(m.get('low_52w', m['price']))
    rng = max(h52 - l52, 0.01)
    pos52 = min(max((m['price'] - l52) / rng * 100, 0), 100)

    def metric_card(title, value, sub, color, fill, bar_color):
        return f"""
        <div style='background:linear-gradient(165deg,rgba(15,23,42,.92),rgba(2,6,23,.86));border:1px solid rgba(148,163,184,.18);border-left:3px solid {color};border-radius:12px;padding:12px 14px;min-height:108px'>
            <p style='margin:0 0 6px;color:#94A3B8;font-size:.74rem;font-weight:700;letter-spacing:.2px'>{title}</p>
            <p style='margin:0;color:{color};font-size:1.55rem;font-weight:800;line-height:1.1'>{value}</p>
            <p style='margin:4px 0 8px;color:#CBD5E1;font-size:.78rem'>{sub}</p>
            <div style='height:7px;background:rgba(148,163,184,.15);border-radius:999px;overflow:hidden'>
                <div style='height:100%;width:{fill:.1f}%;background:{bar_color};border-radius:999px;box-shadow:0 0 10px rgba(148,163,184,.25)'></div>
            </div>
        </div>
        """

    metric_html = "".join([
        metric_card('Ensemble Score', f"{es:+.1f}", f"B{m.get('buy_agree', 0)} : S{m.get('sell_agree', 0)}", esc, es_pct, esc),
        metric_card('BUY Score (10L)', f"{bt_:.1f}", f"{ba_}/10 layers active", SOFT_GREEN, bt_pct, 'linear-gradient(90deg,#237650,#63D9A2)'),
        metric_card('SELL Score (10L)', f"{st_:.1f}", f"{sa_}/10 layers active", SOFT_RED, st_pct, 'linear-gradient(90deg,#FF8F96,#8A4B54)'),
        metric_card('52W Price Position', f"{pos52:.0f}%", f"${l52:.1f} - ${h52:.1f}", '#A5B4FC', pos52, 'linear-gradient(90deg,#FF8F96,#F6C35E,#63D9A2)'),
    ])

    st.markdown(
        f"""
        <div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:16px'>
            {metric_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

    _render_ensemble_gauge(es, chart_key=f"{key_prefix}_ensemble_gauge")

def _risk_size_hint(atr_pct):
    if atr_pct >= 6:
        return 'Small', SOFT_RED
    if atr_pct >= 3.5:
        return 'Reduced', SOFT_AMBER_TEXT
    return 'Standard', SOFT_GREEN

def render_judgment_card(m):
    jg=m['judgment'];es=m.get('ensemble_score',0);cf=m['confidence']
    cc='score-card-buy' if 'BUY' in jg else('score-card-sell' if 'SELL' in jg else 'score-card-neutral')
    jc=SOFT_GREEN if 'BUY' in jg else(SOFT_RED if 'SELL' in jg else SOFT_AMBER)
    ba=m.get('buy_agree',0);sa=m.get('sell_agree',0);veto=m.get('veto_flags','');syn=m.get('reversal_synergy',0);pred=m.get('prediction_boost',0)
    reason=m.get('judgment_reason','');detail=m.get('judgment_detail','');action=m.get('action_label','')
    detail_text=(detail or '').strip() or (reason or '').strip()
    detail_norm=" ".join(detail_text.split())
    detail_html=f"""<div style="margin:16px 0;background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.06);border-radius:12px;padding:14px 18px;border-left:3px solid {jc}">
            <p style="color:#94A3B8;font-size:.72rem;font-weight:700;margin:0 0 6px">근거 요약</p>
            <p style="color:#CBD5E1;font-size:.82rem;margin:0">{detail_text}</p>
        </div>""" if detail_text else ""
    contrast=(m.get('contrast_notes','') or '').strip()
    contrast_norm=" ".join(contrast.split())
    long_rr=float(m.get('vp_long_rr',1) or 1);short_rr=float(m.get('vp_short_rr',1) or 1)
    volume_ratio=float(m.get('volume_ratio_20',1) or 1)
    risk_tags=[]
    if m.get('smart_money_bearish_div'):
        risk_tags.append(("Smart money divergence", SOFT_RED))
    elif m.get('smart_money_bullish_div'):
        risk_tags.append(("Money flow support", SOFT_GREEN))
    if 'BUY' in jg and long_rr < 1:
        risk_tags.append((f"Long RR {long_rr:.2f}", SOFT_AMBER_TEXT))
    if 'SELL' in jg and short_rr < 1:
        risk_tags.append((f"Short RR {short_rr:.2f}", SOFT_AMBER_TEXT))
    if volume_ratio < 0.7:
        risk_tags.append((f"Low vol {volume_ratio:.1f}x", SOFT_AMBER_TEXT))
    if m.get('blowoff_top_hard'):
        risk_tags.append(("Blow-off risk", SOFT_RED))
    risk_html=""
    if contrast or risk_tags:
        chips="".join([f"<span style='display:inline-flex;align-items:center;gap:4px;padding:4px 9px;border-radius:999px;background:{col}22;border:1px solid {col}44;color:{col};font-size:.72rem;font-weight:700'>{label}</span>" for label,col in risk_tags])
        show_contrast=bool(contrast) and contrast_norm not in detail_norm and detail_norm not in contrast_norm
        contrast_html=f"<p style='color:#CBD5E1;font-size:.8rem;margin:0 0 10px'>{contrast}</p>" if show_contrast else ""
        risk_html=f"""<div style="margin:14px 0 0;background:rgba(15,23,42,.58);border:1px solid rgba(148,163,184,.14);border-radius:12px;padding:14px 16px">
            <p style="color:#94A3B8;font-size:.72rem;font-weight:700;margin:0 0 8px">Risk Check</p>
            {contrast_html}
            <div style='display:flex;gap:8px;flex-wrap:wrap'>{chips}</div>
        </div>"""
    circ=2*3.14159*36;offset=circ*(1-cf/100)
    # Committee vote dots
    committee=m.get('committee',{})
    dots_html=""
    if committee:
        dots=[]
        abbr={'Trend':'TR','Momentum':'MO','Money':'MN','Structure':'ST','Leading':'LD'}
        for cm in COMMITTEE_NAMES:
            data=committee.get(cm,{});vote=data.get('vote','NEUTRAL')
            dcls='buy' if vote=='BUY' else ('sell' if vote=='SELL' else ('abstain' if vote=='ABSTAIN' else 'neutral'))
            vc=SOFT_GREEN if vote=='BUY' else(SOFT_RED if vote=='SELL' else '#475569')
            dots.append(f"<span style='display:inline-flex;align-items:center;gap:2px;margin:0 3px'><span class='vote-dot {dcls}'></span><span style='color:{vc};font-size:.6rem;font-weight:600'>{abbr.get(cm,cm[:2])}</span></span>")
        dots_html=f"<div style='margin-top:10px;display:flex;align-items:center;justify-content:center;gap:2px'><span style='color:#475569;font-size:.65rem;margin-right:4px'>위원회</span>{''.join(dots)}</div>"
    veto_html=f"<div style='margin-top:8px;text-align:center'><span style='background:rgba(243,165,165,.15);color:{SOFT_RED_TEXT};padding:4px 10px;border-radius:6px;font-size:.72rem;font-weight:700'>VETO {veto}</span></div>" if veto else ""
    # Badges
    badges=""
    if abs(syn)>5:badges+=f"<span style='background:rgba({'52,211,153' if syn>0 else '248,113,113'},.12);color:{SOFT_GREEN if syn>0 else SOFT_RED};padding:3px 8px;border-radius:6px;font-size:.72rem;font-weight:700'>SYN {syn:+.1f}</span> "
    if abs(pred)>3:badges+=f"<span style='background:rgba({'52,211,153' if pred>0 else '248,113,113'},.12);color:{SOFT_GREEN if pred>0 else SOFT_RED};padding:3px 8px;border-radius:6px;font-size:.72rem;font-weight:700'>PRED {pred:+.1f}</span>"
    # Ensemble gauge
    es_norm=min(max((es+80)/160*100,0),100)
    es_c=SOFT_GREEN if es>0 else SOFT_RED if es<0 else SOFT_AMBER
    # Agree ratio bar
    total_agree=max(ba+sa,1);ba_pct=ba/total_agree*100
    st.markdown(f"""<div class="score-card {cc} fade-up">
        <div style="display:flex;align-items:center;justify-content:center;gap:28px;flex-wrap:wrap">
            <div class="conf-ring"><svg viewBox="0 0 80 80"><circle class="ring-bg" cx="40" cy="40" r="36"/><circle class="ring-fg" cx="40" cy="40" r="36" stroke="{jc}" stroke-dasharray="{circ:.1f}" stroke-dashoffset="{offset:.1f}"/></svg><span class="ring-text" style="color:{jc}">{cf:.0f}%</span></div>
            <div>
                <p style="font-size:1.8rem;font-weight:800;color:{jc};margin:0;letter-spacing:-.5px">{action}</p>
                {dots_html}
            </div>
        </div>
        {detail_html}
        {risk_html}
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-top:14px">
            <div style="background:rgba(255,255,255,.03);border-radius:10px;padding:12px;text-align:center">
                <p style="color:#64748B;font-size:.68rem;font-weight:700;margin:0 0 4px">Ensemble</p>
                <p style="color:{es_c};font-size:1.3rem;font-weight:800;margin:0">{es:+.1f}</p>
                <div style="height:3px;background:rgba(255,255,255,.06);border-radius:2px;margin-top:6px;overflow:hidden"><div style="height:100%;width:{es_norm}%;background:{es_c};border-radius:2px"></div></div>
            </div>
            <div style="background:rgba(255,255,255,.03);border-radius:10px;padding:12px;text-align:center">
                <p style="color:#64748B;font-size:.68rem;font-weight:700;margin:0 0 4px">Agree B:S</p>
                <p style="color:#F8FAFC;font-size:1.3rem;font-weight:800;margin:0">{ba}:{sa}</p>
                <div style="height:3px;background:rgba(243,165,165,.28);border-radius:2px;margin-top:6px;overflow:hidden"><div style="height:100%;width:{ba_pct}%;background:{SOFT_GREEN};border-radius:2px"></div></div>
            </div>
            <div style="background:rgba(255,255,255,.03);border-radius:10px;padding:12px;text-align:center">
                <p style="color:#64748B;font-size:.68rem;font-weight:700;margin:0 0 4px">Context</p>
                <p style="color:#A5B4FC;font-size:1.05rem;font-weight:800;margin:0">{m.get('context_label','기본')}</p>
                <div style="height:3px;background:rgba(165,180,252,.15);border-radius:2px;margin-top:6px;overflow:hidden"><div style="height:100%;width:100%;background:#A5B4FC;border-radius:2px;opacity:.4"></div></div>
            </div>
        </div>
        <div style='margin-top:10px;display:flex;justify-content:center;gap:8px;flex-wrap:wrap'>{badges}</div>{veto_html}</div>""",unsafe_allow_html=True)

def render_committee_panel(m):
    committee=m.get('committee',{})
    if not committee:return
    ctx_code=m.get('context',0);ctx_name=CTX_LABELS.get(ctx_code,'default');weights=CONTEXT_WEIGHTS.get(ctx_name,CONTEXT_WEIGHTS['default'])
    cards_html=""
    for ci,cm in enumerate(COMMITTEE_NAMES):
        data=committee.get(cm,{});score=data.get('score',0);conv=data.get('conviction',0);vote=data.get('vote','NEUTRAL');weight=weights[ci] if ci<len(weights) else 0.2
        sc=SOFT_GREEN if score>0 else(SOFT_RED if score<0 else '#94A3B8')
        vc=f'background:rgba(126,216,182,.14);color:{SOFT_GREEN}' if vote=='BUY' else(f'background:rgba(243,165,165,.14);color:{SOFT_RED}' if vote=='SELL' else('background:rgba(71,85,105,.3);color:#64748B' if vote=='ABSTAIN' else f'background:rgba(245,199,123,.14);color:{SOFT_AMBER}'))
        bar_w=min(abs(score)/40*100,100)
        bdr=f'border-left:3px solid {sc}' if abs(score)>10 else ''
        cards_html+=f"""<div class='cm-card' style='{bdr}'>
            <p class='cm-name'>{cm} ×{weight:.0%}</p>
            <p class='cm-score' style='color:{sc}'>{score:+.0f}</p>
            <span class='cm-vote' style='{vc}'>{vote}</span>
            <p style='color:#64748B;font-size:.65rem;margin:4px 0 0'>확신 {conv:.0f}%</p>
            <div class='cm-mini-bar'><div class='cm-mini-fill' style='width:{bar_w}%;background:{sc}'></div></div>
        </div>"""
    st.markdown(f"<div style='display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-top:12px'>{cards_html}</div>",unsafe_allow_html=True)
    veto=m.get('veto_flags','')
    if veto:st.warning(f"**[VETO]** {veto}")
    syn=m.get('reversal_synergy',0)
    if abs(syn)>5:st.info(f"**[SYNERGY]** {syn:+.1f}")

def render_10layer_bars(m, html_key="analysis"):
    layer_names = ['Trend', 'Momentum', 'Candle', 'BB', 'Volume', 'MF', 'Pattern', 'Combined', 'Leading', 'Lagging']
    buy_layers = m.get('buy_layers', {})
    sell_layers = m.get('sell_layers', {})
    max_val = 12.0

    rows = []
    for name in layer_names:
        bv = max(float(buy_layers.get(name, 0)), 0.0)
        sv = max(float(sell_layers.get(name, 0)), 0.0)
        bpct = min((bv / max_val) * 50.0, 50.0)
        spct = min((sv / max_val) * 50.0, 50.0)
        bop = 1.0 if bv > 0 else 0.35
        sop = 1.0 if sv > 0 else 0.35
        row_glow = "box-shadow:0 0 10px rgba(99,102,241,.18);" if abs(bv - sv) >= 4 else ""

        rows.append(
            f"<div style='display:grid;grid-template-columns:58px 1fr 58px;gap:10px;align-items:center;margin-bottom:8px;padding:2px;border-radius:10px;{row_glow}'>"
            f"<div style='text-align:right;color:{SOFT_GREEN};font-size:.88rem;font-weight:700;opacity:{bop:.2f}'>{bv:.1f}</div>"
            "<div style='position:relative;height:30px;border-radius:10px;border:1px solid rgba(148,163,184,.2);background:linear-gradient(90deg,rgba(126,216,182,.08),rgba(148,163,184,.04),rgba(243,165,165,.08));overflow:hidden'>"
            f"<div style='position:absolute;left:{50.0 - bpct:.2f}%;top:4px;bottom:4px;width:{bpct:.2f}%;background:linear-gradient(90deg,#237650,#63D9A2);border-radius:6px 0 0 6px;opacity:{bop:.2f}'></div>"
            f"<div style='position:absolute;left:50%;top:4px;bottom:4px;width:{spct:.2f}%;background:linear-gradient(90deg,#FF8F96,#8A4B54);border-radius:0 6px 6px 0;opacity:{sop:.2f}'></div>"
            "<div style='position:absolute;left:50%;top:0;bottom:0;width:1px;background:rgba(226,232,240,.55)'></div>"
            f"<div style='position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);font-size:.72rem;color:#CBD5E1;font-weight:700;background:rgba(2,6,23,.78);padding:2px 8px;border-radius:999px;border:1px solid rgba(148,163,184,.25)'>{name}</div>"
            "</div>"
            f"<div style='text-align:left;color:{SOFT_RED};font-size:.88rem;font-weight:700;opacity:{sop:.2f}'>{sv:.1f}</div>"
            "</div>"
        )

    buy_active = int(m.get('buy_active', 0))
    sell_active = int(m.get('sell_active', 0))

    rows_html = "".join(rows)
    panel_html = (
        "<div style='background:rgba(15,19,32,.55);backdrop-filter:blur(12px);border:1px solid rgba(255,255,255,.08);border-radius:14px;padding:16px 14px;margin-bottom:12px'>"
        "<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:8px'>"
        f"<span style='color:{SOFT_GREEN};font-weight:800;font-size:.86rem'>BUY ({buy_active}/10)</span>"
        "<span style='color:#94A3B8;font-size:.76rem;font-weight:700'>10-Layer Buy/Sell comparison</span>"
        f"<span style='color:{SOFT_RED};font-weight:800;font-size:.86rem'>SELL ({sell_active}/10)</span>"
        "</div>"
        "<div style='display:flex;justify-content:center;gap:10px;margin:0 0 10px'>"
        f"<span style='color:{SOFT_GREEN};font-size:.7rem'>left = buy pressure</span>"
        f"<span style='color:{SOFT_RED};font-size:.7rem'>right = sell pressure</span>"
        "</div>"
        f"{rows_html}"
        "</div>"
    )
    panel_h=max(430,120+len(layer_names)*44)
    html_doc=f"""<!doctype html><html><head><meta charset='utf-8'></head><body style='margin:0;background:transparent;color:#E2E8F0;font-family:Pretendard,system-ui,sans-serif'><!-- {html_key} -->{panel_html}</body></html>"""
    components.html(html_doc,height=panel_h,scrolling=False)
def render_leading_lagging(m):
    lv=m['leading_verdict'];lgv=m['lagging_verdict'];ac=m['composite_accel']
    lc=SOFT_GREEN if '상승' in lv else(SOFT_RED if '하락' in lv else SOFT_AMBER)
    lgc=SOFT_GREEN if '상승' in lgv else(SOFT_RED if '하락' in lgv else SOFT_AMBER)
    # Setup Pressure tug-of-war
    spb=m.get('setup_pressure_buy',0);sps=m.get('setup_pressure_sell',0)
    maxsp=max(spb,sps,1);bw=min(spb/maxsp*50,50);sw=min(sps/maxsp*50,50)
    tow_label=f"매수 압력 {spb:.1f}" if spb>sps else(f"매도 압력 {sps:.1f}" if sps>spb else "균형")
    tow_color=SOFT_GREEN if spb>sps else(SOFT_RED if sps>spb else SOFT_AMBER)
    # Tech snapshot stats
    pb_=m.get('percent_b',0.5);pb_pct=pb_*100
    cmf_=m.get('cmf',0);cmf_c=SOFT_GREEN if cmf_>0.05 else(SOFT_RED if cmf_<-0.05 else '#94A3B8')
    obv_c=SOFT_GREEN if m.get('obv_trend')=='rising' else SOFT_RED
    obv_slope=m.get('obv_slope',0);obv_slope_c=SOFT_GREEN if obv_slope>0 else(SOFT_RED if obv_slope<0 else '#94A3B8')
    atr_pct=m.get('atr_pct',0)
    volume_ratio=m.get('volume_ratio_20',1);vol_c=SOFT_GREEN if volume_ratio>=1 else(SOFT_AMBER_TEXT if volume_ratio>=0.7 else SOFT_RED)
    long_rr=m.get('vp_long_rr',1);short_rr=m.get('vp_short_rr',1)
    long_rr_c=SOFT_GREEN if long_rr>=1.35 else(SOFT_AMBER_TEXT if long_rr>=1 else SOFT_RED)
    short_rr_c=SOFT_GREEN if short_rr>=1.35 else(SOFT_AMBER_TEXT if short_rr>=1 else SOFT_RED)
    ma50d=m.get('ma50_dist',0);ma200d=m.get('ma200_dist',0)
    ma50c=SOFT_GREEN if ma50d>0 else SOFT_RED
    ma200c=SOFT_GREEN if ma200d>0 else SOFT_RED
    size_label,size_color=_risk_size_hint(atr_pct)
    flow_text='하락 다이버전스' if m.get('smart_money_bearish_div') else('상승 지지' if m.get('smart_money_bullish_div') else '정렬')
    flow_color=SOFT_RED if m.get('smart_money_bearish_div') else(SOFT_GREEN if m.get('smart_money_bullish_div') else '#94A3B8')
    st.markdown(f"""<div style='display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px'>
        <div style='background:rgba(255,255,255,.03);border:1px solid #1E293B;border-radius:12px;padding:16px'>
            <p style='font-weight:700;color:#A5B4FC;margin:0 0 8px;font-size:.85rem'>선행 지표 (Leading)</p>
            <p style='color:{lc};font-weight:800;font-size:1.15rem;margin:0 0 8px'>{lv}</p>
            <div style='display:flex;gap:10px;flex-wrap:wrap'>
                <span style='color:#94A3B8;font-size:.78rem'>가속도: <b style='color:{SOFT_GREEN if ac>0 else SOFT_RED}'>{ac:+.2f}</b></span>
                <span style='color:#94A3B8;font-size:.78rem'>UT: {'Buy' if m.get('utbot_dir',0)==1 else('Sell' if m.get('utbot_dir',0)==-1 else 'N')}</span>
                <span style='color:#94A3B8;font-size:.78rem'>Hull: {'Up' if m.get('hma_rising') else 'Down'}</span>
            </div>
        </div>
        <div style='background:rgba(255,255,255,.03);border:1px solid #1E293B;border-radius:12px;padding:16px'>
            <p style='font-weight:700;color:#A5B4FC;margin:0 0 8px;font-size:.85rem'>후행 지표 (Lagging)</p>
            <p style='color:{lgc};font-weight:800;font-size:1.15rem;margin:0 0 8px'>{lgv}</p>
            <div style='display:flex;gap:14px'>
                <span style='color:#94A3B8;font-size:.78rem'>Context: <b>{m['regime_label']}</b></span>
                <span style='color:#94A3B8;font-size:.78rem'>RS: <b style='color:{SOFT_GREEN if m["rs_ratio"]>1.03 else(SOFT_RED if m["rs_ratio"]<.97 else SOFT_AMBER)}'>{m['rs_ratio']:.3f}</b></span>
            </div>
        </div>
    </div>""",unsafe_allow_html=True)
    # Setup Pressure
    st.markdown(f"""<div style='background:rgba(255,255,255,.03);border:1px solid #1E293B;border-radius:12px;padding:14px;margin-bottom:12px'>
        <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:4px'>
            <span style='color:{SOFT_GREEN};font-size:.78rem;font-weight:700'>매수 셋업 {spb:.1f}</span>
            <span style='color:{tow_color};font-size:.78rem;font-weight:700'>{tow_label}</span>
            <span style='color:{SOFT_RED};font-size:.78rem;font-weight:700'>매도 셋업 {sps:.1f}</span>
        </div>
        <div class='tow-bar'><div class='tow-buy' style='width:{bw}%'></div><div class='tow-sell' style='width:{sw}%'></div><div class='tow-center'></div></div>
    </div>""",unsafe_allow_html=True)
    # Tech snapshot
    snapshot_cards = "".join([
        _mini_stat_card('BB %B', f"{pb_pct:.0f}%", SOFT_GREEN if pb_<0.3 else(SOFT_RED if pb_>0.7 else SOFT_AMBER), '볼린저 밴드 내 현재 위치입니다. 30% 이하는 눌림, 70% 이상은 과열 가능성으로 읽습니다.'),
        _mini_stat_card('CMF', f"{cmf_:+.3f}", cmf_c, 'Chaikin Money Flow. 0 위면 자금 유입 우위, 0 아래면 자금 이탈 우위입니다.'),
        _mini_stat_card('Money Flow', flow_text, flow_color, '가격과 수급이 같은 방향인지 확인합니다. 다이버전스면 추세 신뢰도가 떨어질 수 있습니다.'),
        _mini_stat_card('OBV Slope', f"{obv_slope:+.2f}", obv_slope_c, 'OBV 기울기입니다. 가격 상승 중 OBV가 꺾이면 스마트 머니 경고로 해석합니다.'),
        _mini_stat_card('Vol 20d', f"{volume_ratio:.1f}x", vol_c, '최근 거래량이 20일 평균 대비 얼마나 붙는지 보여줍니다. 1배 미만이면 추격 신호 신뢰도가 낮아질 수 있습니다.'),
        _mini_stat_card('Long RR', f"{long_rr:.2f}", long_rr_c, '현재가에서 저항(VAH)과 지지(POC/VAL)까지의 비율입니다. 1 미만이면 롱 손익비가 답답합니다.'),
        _mini_stat_card('Short RR', f"{short_rr:.2f}", short_rr_c, '현재가에서 하방 공간과 상단 저항을 비교한 값입니다. 숏 관점의 구조적 공간을 확인할 때 봅니다.'),
        _mini_stat_card('ATR%', f"{atr_pct:.1f}%", SOFT_BLUE, '평균 변동폭이 현재가 대비 얼마나 큰지 보여줍니다. 값이 높을수록 포지션 크기를 줄이는 편이 안전합니다.'),
        _mini_stat_card('Risk Size', size_label, size_color, 'ATR 기반 권장 비중 힌트입니다. Standard보다 Reduced/Small이면 손절 폭과 비중을 함께 낮추는 편이 좋습니다.'),
        _mini_stat_card('MA50 이격', f"{ma50d:+.1f}%", ma50c, '현재가가 50일선에서 얼마나 벌어졌는지 보여줍니다. 이격이 과하면 눌림 없이 추격하기 어렵습니다.'),
        _mini_stat_card('MA200 이격', f"{ma200d:+.1f}%", ma200c, '중장기 추세선과의 거리입니다. 장기 추세 위/아래 여부를 가장 빠르게 읽을 수 있습니다.'),
    ])
    st.markdown(f"""<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:8px'>{snapshot_cards}</div>""",unsafe_allow_html=True)

def render_combined_scans(m):
    scans=m.get('combined_scans',[])
    if not scans:st.info("활성 Combined Scan 없음");return
    bn=sum(1 for s in scans if s['dir']=='buy');sn_=sum(1 for s in scans if s['dir']=='sell');t1=sum(1 for s in scans if s['tier']==1)
    hc='#E8C56C' if t1>0 else(SOFT_GREEN if bn>sn_ else(SOFT_RED if sn_>bn else SOFT_AMBER))
    st.markdown(f"<div style='background:rgba(255,215,0,.06);border:1px solid {hc}33;border-radius:12px;padding:12px;margin-bottom:10px'><span style='font-size:1.2rem;font-weight:800;color:{hc}'>[COMBO] {len(scans)} Active</span> <span style='color:#94A3B8;margin-left:12px'>T1:{t1} B:{bn} S:{sn_}</span></div>",unsafe_allow_html=True)
    cards=[]
    for s in scans:
        tb={1:'T1',2:'T2',3:'T3'}.get(s['tier'],'T?');is_buy=s['dir']=='buy';is_sell=s['dir']=='sell'
        dc_=SOFT_GREEN if is_buy else(SOFT_RED if is_sell else SOFT_AMBER)
        bg='linear-gradient(160deg,rgba(5,46,22,.55),rgba(15,23,42,.6))' if is_buy else('linear-gradient(160deg,rgba(69,10,10,.55),rgba(30,41,59,.6))' if is_sell else 'linear-gradient(160deg,rgba(120,53,15,.5),rgba(30,41,59,.6))')
        ic='🟢' if is_buy else('🔴' if is_sell else '🟠')
        td="<span style='background:#FFD700;color:#111827;padding:2px 6px;border-radius:999px;font-size:.64rem;font-weight:800'>TODAY</span>" if s['is_today'] else f"<span style='color:#94A3B8;font-size:.72rem'>{s['date']}</span>"
        cards.append(f"""<div style='background:{bg};border:1px solid {dc_}55;border-radius:14px;padding:12px 12px 10px;box-shadow:0 8px 24px rgba(0,0,0,.25)'>
            <div style='display:flex;justify-content:space-between;align-items:center;gap:8px'>
                <span style='color:{dc_};font-weight:800'>{ic} {s['kor']}</span>
                <span style='color:#E2E8F0;font-size:.68rem;background:rgba(15,23,42,.6);padding:2px 8px;border-radius:999px'>{tb}</span>
            </div>
            <div style='margin-top:8px;display:flex;justify-content:space-between;align-items:center'>
                <span style='color:#60A5FA;font-size:.72rem'>WinRate {s['win']}</span>
                {td}
            </div>
        </div>""")
    st.markdown(f"<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px'>{''.join(cards)}</div>",unsafe_allow_html=True)

def render_indicator_help():
    with st.expander("ℹ️ 화면 읽는 법 / 지표 도움말"):
        st.markdown(
            "- `Action / Confidence`: 현재 결론과 신뢰도입니다. 첫 화면에서 가장 먼저 보시면 됩니다.\n"
            "- `Risk Check`: 수급 다이버전스, 손익비, 저거래량, 과열 경고를 모아 보여줍니다.\n"
            "- `WT`: 과매수/과매도 반전 압력입니다.\n"
            "- `ADX`: 추세 강도이며 방향 지표는 아닙니다.\n"
            "- `CMF / OBV Slope`: 자금 유입/이탈과 스마트 머니 방향성을 읽는 핵심 지표입니다.\n"
            "- `Ensemble Score`: -100~+100 종합 방향 점수입니다.\n"
            "- `10-Layer`: 추세, 모멘텀, 구조, 자금 등 레이어별 기여도 비교입니다."
        )

def render_analysis(msg, key_prefix="analysis"):
    m,fj=msg.get('meta'),msg.get('fig_json')
    if m:
        render_price_header(m, key_prefix=key_prefix)
    if m or fj:
        t0,t1,t2,t3,t4=st.tabs(["차트","판단·리스크","10-Layer","콤보스캔","기업정보"])
        with t0:
            if fj:fig=go.Figure(json.loads(fj));st.plotly_chart(fig,use_container_width=True,theme=None,config={'displaylogo':False,'modeBarButtonsToRemove':['lasso2d','select2d']}, key=f"{key_prefix}_price_chart");st.caption("*캔들 오버 시 툴팁, 강/약 시그널 캔들 하이라이트, 우측 매물대(VP) 오버레이를 제공합니다. 모바일에서는 판단 카드 확인 후 차트를 열면 더 읽기 쉽습니다.")
        with t1:
            if m:
                render_judgment_card(m)
                st.markdown("#### 🏛️ 5-Committee Ensemble")
                render_committee_panel(m)
                st.markdown("---")
                render_leading_lagging(m)
                render_indicator_help()
        with t2:
            if m:render_10layer_bars(m, html_key=f"{key_prefix}_10layer")
        with t3:
            if m:render_combined_scans(m)
        with t4:
            if m:render_company_details(m['ticker'], key_prefix=f"{key_prefix}_company")
