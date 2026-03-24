import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
from config import *
from chart import build_metadata, build_chart
from company_details import render_company_details

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

def _render_ensemble_gauge(es):
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
                {'range':[-100,-30],'color':'rgba(248,113,113,0.35)'},
                {'range':[-30,30],'color':'rgba(255,152,0,0.25)'},
                {'range':[30,100],'color':'rgba(52,211,153,0.35)'},
            ],
            'threshold':{'line':{'color':'#E2E8F0','width':2},'thickness':0.8,'value':es}
        }
    ))
    gauge.update_layout(height=180,margin=dict(l=6,r=6,t=8,b=8),paper_bgcolor='rgba(0,0,0,0)',font=dict(color='#E2E8F0'))
    st.plotly_chart(gauge,use_container_width=True,theme=None,config={'displayModeBar':False})

def render_price_header(m):
    chg = m['price_change']
    cp = m['price_change_pct']
    cc = 'price-change-up' if chg >= 0 else 'price-change-down'
    ci = '+' if chg >= 0 else '-'

    vr_ = m['volume'] / max(m['avg_volume'], 1)
    jg = m['judgment']
    cf = m['confidence']
    es = float(m.get('ensemble_score', 0))
    jc = '#34D399' if 'BUY' in jg else ('#F87171' if 'SELL' in jg else '#FF9800')

    act = m.get('action_label', '')
    specs = [
        (jc, f"[{act}] {cf:.0f}%", "Final action and confidence"),
        ('ind-b' if m['wt1'] < -20 else ('ind-s' if m['wt1'] > 20 else 'ind-n'), f"WT{m['wt1']:.0f}", "WaveTrend pressure"),
        ('ind-b' if m['rsi'] < 40 else ('ind-s' if m['rsi'] > 60 else 'ind-n'), f"RSI{m['rsi']:.0f}", "RSI momentum"),
        ('ind-b' if vr_ > 1.5 else 'ind-n', f"Vol{vr_:.1f}x", "Volume vs average"),
        ('ind-b' if m['adx'] > 25 else 'ind-n', f"ADX{m['adx']:.0f}", "Trend strength"),
        ('ind-b' if m.get('utbot_dir', 0) == 1 else ('ind-s' if m.get('utbot_dir', 0) == -1 else 'ind-n'), '[UT] B' if m.get('utbot_dir', 0) == 1 else ('[UT] S' if m.get('utbot_dir', 0) == -1 else '[UT] -'), "UT direction"),
        ('ind-b' if m.get('hma_rising') else 'ind-s', '[HMA] UP' if m.get('hma_rising') else '[HMA] DN', "Hull direction"),
    ]
    ih = "".join([f"<span class='ind-mini {c}' title='{tip}'>{l}</span>" for c, l, tip in specs])

    bottom = _bottom_line_text(m).strip()
    narrative = _narrative_text(m).strip()
    insight_body = f"<p style='margin:0;color:#F8FAFC;font-weight:700'>{bottom}</p>"
    if narrative and narrative not in bottom:
        insight_body += f"<p style='margin:6px 0 0;color:#CBD5E1;font-size:.86rem;font-weight:500'>{narrative}</p>"

    st.markdown(
        f"""
        <div style='background:linear-gradient(140deg,rgba(99,102,241,.15),rgba(15,23,42,.75));border:1px solid rgba(99,102,241,.35);border-radius:12px;padding:12px 14px;margin-bottom:12px'>
            {insight_body}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="price-header fade-up">
            <p style="color:#64748B;font-size:.8rem;margin:0">{m['ticker']} - {m['last_date']} - <b style="color:#A5B4FC">{m['regime_label']}</b> - <span style='color:#A5B4FC'>[CTX] {m.get('context_label', 'default')}</span></p>
            <p class="price-big" style="color:#F8FAFC">${m['price']:.2f}<span class="{cc}" style="font-size:1.1rem;margin-left:10px;font-weight:700">{ci}{abs(chg):.2f}({abs(cp):.2f}%)</span></p>
            <div style="margin-top:10px;display:flex;gap:4px;flex-wrap:wrap">{ih}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    esc = '#34D399' if es > 0 else ('#F87171' if es < 0 else '#FF9800')
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
        metric_card('BUY Score (10L)', f"{bt_:.1f}", f"{ba_}/10 layers active", '#34D399', bt_pct, 'linear-gradient(90deg,#065F46,#34D399)'),
        metric_card('SELL Score (10L)', f"{st_:.1f}", f"{sa_}/10 layers active", '#F87171', st_pct, 'linear-gradient(90deg,#F87171,#7F1D1D)'),
        metric_card('52W Price Position', f"{pos52:.0f}%", f"${l52:.1f} - ${h52:.1f}", '#A5B4FC', pos52, 'linear-gradient(90deg,#F87171,#FF9800,#34D399)'),
    ])

    st.markdown(
        f"""
        <div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:16px'>
            {metric_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

    _render_ensemble_gauge(es)
def render_judgment_card(m):
    jg=m['judgment'];es=m.get('ensemble_score',0);cf=m['confidence']
    cc='score-card-buy' if 'BUY' in jg else('score-card-sell' if 'SELL' in jg else 'score-card-neutral')
    jc='#34D399' if 'BUY' in jg else('#F87171' if 'SELL' in jg else '#FF9800')
    ba=m.get('buy_agree',0);sa=m.get('sell_agree',0);veto=m.get('veto_flags','');syn=m.get('reversal_synergy',0);pred=m.get('prediction_boost',0)
    reason=m.get('judgment_reason','');detail=m.get('judgment_detail','');action=m.get('action_label','')
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
            vc='#34D399' if vote=='BUY' else('#F87171' if vote=='SELL' else '#475569')
            dots.append(f"<span style='display:inline-flex;align-items:center;gap:2px;margin:0 3px'><span class='vote-dot {dcls}'></span><span style='color:{vc};font-size:.6rem;font-weight:600'>{abbr.get(cm,cm[:2])}</span></span>")
        dots_html=f"<div style='margin-top:10px;display:flex;align-items:center;justify-content:center;gap:2px'><span style='color:#475569;font-size:.65rem;margin-right:4px'>위원회</span>{''.join(dots)}</div>"
    veto_html=f"<div style='margin-top:8px;text-align:center'><span style='background:rgba(239,68,68,.15);color:#FCA5A5;padding:4px 10px;border-radius:6px;font-size:.72rem;font-weight:700'>VETO {veto}</span></div>" if veto else ""
    # Badges
    badges=""
    if abs(syn)>5:badges+=f"<span style='background:rgba({'52,211,153' if syn>0 else '248,113,113'},.12);color:{'#34D399' if syn>0 else '#F87171'};padding:3px 8px;border-radius:6px;font-size:.72rem;font-weight:700'>SYN {syn:+.1f}</span> "
    if abs(pred)>3:badges+=f"<span style='background:rgba({'52,211,153' if pred>0 else '248,113,113'},.12);color:{'#34D399' if pred>0 else '#F87171'};padding:3px 8px;border-radius:6px;font-size:.72rem;font-weight:700'>PRED {pred:+.1f}</span>"
    # Ensemble gauge
    es_norm=min(max((es+80)/160*100,0),100)
    es_c='#34D399' if es>0 else '#F87171' if es<0 else '#FF9800'
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
        <div style="margin:16px 0;background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.06);border-radius:12px;padding:14px 18px;border-left:3px solid {jc}">
            <p style="color:#E2E8F0;font-size:.9rem;font-weight:600;margin:0 0 6px">{reason}</p>
            <p style="color:#64748B;font-size:.78rem;margin:0">{detail}</p>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-top:14px">
            <div style="background:rgba(255,255,255,.03);border-radius:10px;padding:12px;text-align:center">
                <p style="color:#64748B;font-size:.68rem;font-weight:700;margin:0 0 4px">Ensemble</p>
                <p style="color:{es_c};font-size:1.3rem;font-weight:800;margin:0">{es:+.1f}</p>
                <div style="height:3px;background:rgba(255,255,255,.06);border-radius:2px;margin-top:6px;overflow:hidden"><div style="height:100%;width:{es_norm}%;background:{es_c};border-radius:2px"></div></div>
            </div>
            <div style="background:rgba(255,255,255,.03);border-radius:10px;padding:12px;text-align:center">
                <p style="color:#64748B;font-size:.68rem;font-weight:700;margin:0 0 4px">Agree B:S</p>
                <p style="color:#F8FAFC;font-size:1.3rem;font-weight:800;margin:0">{ba}:{sa}</p>
                <div style="height:3px;background:rgba(248,113,113,.3);border-radius:2px;margin-top:6px;overflow:hidden"><div style="height:100%;width:{ba_pct}%;background:#34D399;border-radius:2px"></div></div>
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
        sc='#34D399' if score>0 else('#F87171' if score<0 else '#94A3B8')
        vc='background:rgba(52,211,153,.15);color:#34D399' if vote=='BUY' else('background:rgba(248,113,113,.15);color:#F87171' if vote=='SELL' else('background:rgba(71,85,105,.3);color:#64748B' if vote=='ABSTAIN' else 'background:rgba(255,152,0,.15);color:#FF9800'))
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

def render_10layer_bars(m):
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
            f"<div style='text-align:right;color:#34D399;font-size:.88rem;font-weight:700;opacity:{bop:.2f}'>{bv:.1f}</div>"
            "<div style='position:relative;height:30px;border-radius:10px;border:1px solid rgba(148,163,184,.2);background:linear-gradient(90deg,rgba(16,185,129,.08),rgba(148,163,184,.04),rgba(239,68,68,.08));overflow:hidden'>"
            f"<div style='position:absolute;left:{50.0 - bpct:.2f}%;top:4px;bottom:4px;width:{bpct:.2f}%;background:linear-gradient(90deg,#065F46,#34D399);border-radius:6px 0 0 6px;opacity:{bop:.2f}'></div>"
            f"<div style='position:absolute;left:50%;top:4px;bottom:4px;width:{spct:.2f}%;background:linear-gradient(90deg,#F87171,#7F1D1D);border-radius:0 6px 6px 0;opacity:{sop:.2f}'></div>"
            "<div style='position:absolute;left:50%;top:0;bottom:0;width:1px;background:rgba(226,232,240,.55)'></div>"
            f"<div style='position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);font-size:.72rem;color:#CBD5E1;font-weight:700;background:rgba(2,6,23,.78);padding:2px 8px;border-radius:999px;border:1px solid rgba(148,163,184,.25)'>{name}</div>"
            "</div>"
            f"<div style='text-align:left;color:#F87171;font-size:.88rem;font-weight:700;opacity:{sop:.2f}'>{sv:.1f}</div>"
            "</div>"
        )

    buy_active = int(m.get('buy_active', 0))
    sell_active = int(m.get('sell_active', 0))

    rows_html = "".join(rows)
    panel_html = (
        "<div style='background:rgba(15,19,32,.55);backdrop-filter:blur(12px);border:1px solid rgba(255,255,255,.08);border-radius:14px;padding:16px 14px;margin-bottom:12px'>"
        "<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:8px'>"
        f"<span style='color:#34D399;font-weight:800;font-size:.86rem'>BUY ({buy_active}/10)</span>"
        "<span style='color:#94A3B8;font-size:.76rem;font-weight:700'>10-Layer Buy/Sell comparison</span>"
        f"<span style='color:#F87171;font-weight:800;font-size:.86rem'>SELL ({sell_active}/10)</span>"
        "</div>"
        "<div style='display:flex;justify-content:center;gap:10px;margin:0 0 10px'>"
        "<span style='color:#34D399;font-size:.7rem'>left = buy pressure</span>"
        "<span style='color:#F87171;font-size:.7rem'>right = sell pressure</span>"
        "</div>"
        f"{rows_html}"
        "</div>"
    )
    st.markdown(panel_html, unsafe_allow_html=True)
def render_leading_lagging(m):
    lv=m['leading_verdict'];lgv=m['lagging_verdict'];ac=m['composite_accel']
    lc='#34D399' if '상승' in lv else('#F87171' if '하락' in lv else '#FF9800')
    lgc='#34D399' if '상승' in lgv else('#F87171' if '하락' in lgv else '#FF9800')
    # Setup Pressure tug-of-war
    spb=m.get('setup_pressure_buy',0);sps=m.get('setup_pressure_sell',0)
    maxsp=max(spb,sps,1);bw=min(spb/maxsp*50,50);sw=min(sps/maxsp*50,50)
    tow_label=f"매수 압력 {spb:.1f}" if spb>sps else(f"매도 압력 {sps:.1f}" if sps>spb else "균형")
    tow_color='#34D399' if spb>sps else('#F87171' if sps>spb else '#FF9800')
    # Tech snapshot stats
    pb_=m.get('percent_b',0.5);pb_pct=pb_*100
    cmf_=m.get('cmf',0);cmf_c='#34D399' if cmf_>0.05 else('#F87171' if cmf_<-0.05 else '#94A3B8')
    obv_c='#34D399' if m.get('obv_trend')=='rising' else '#F87171'
    atr_pct=m.get('atr_pct',0)
    ma50d=m.get('ma50_dist',0);ma200d=m.get('ma200_dist',0)
    ma50c='#34D399' if ma50d>0 else '#F87171'
    ma200c='#34D399' if ma200d>0 else '#F87171'
    st.markdown(f"""<div style='display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px'>
        <div style='background:rgba(255,255,255,.03);border:1px solid #1E293B;border-radius:12px;padding:16px'>
            <p style='font-weight:700;color:#A5B4FC;margin:0 0 8px;font-size:.85rem'>선행 지표 (Leading)</p>
            <p style='color:{lc};font-weight:800;font-size:1.15rem;margin:0 0 8px'>{lv}</p>
            <div style='display:flex;gap:10px;flex-wrap:wrap'>
                <span style='color:#94A3B8;font-size:.78rem'>가속도: <b style='color:{"#34D399" if ac>0 else "#F87171"}'>{ac:+.2f}</b></span>
                <span style='color:#94A3B8;font-size:.78rem'>UT: {'Buy' if m.get('utbot_dir',0)==1 else('Sell' if m.get('utbot_dir',0)==-1 else 'N')}</span>
                <span style='color:#94A3B8;font-size:.78rem'>Hull: {'Up' if m.get('hma_rising') else 'Down'}</span>
            </div>
        </div>
        <div style='background:rgba(255,255,255,.03);border:1px solid #1E293B;border-radius:12px;padding:16px'>
            <p style='font-weight:700;color:#A5B4FC;margin:0 0 8px;font-size:.85rem'>후행 지표 (Lagging)</p>
            <p style='color:{lgc};font-weight:800;font-size:1.15rem;margin:0 0 8px'>{lgv}</p>
            <div style='display:flex;gap:14px'>
                <span style='color:#94A3B8;font-size:.78rem'>Context: <b>{m['regime_label']}</b></span>
                <span style='color:#94A3B8;font-size:.78rem'>RS: <b style='color:{"#34D399" if m["rs_ratio"]>1.03 else("#F87171" if m["rs_ratio"]<.97 else "#FF9800")}'>{m['rs_ratio']:.3f}</b></span>
            </div>
        </div>
    </div>""",unsafe_allow_html=True)
    # Setup Pressure
    st.markdown(f"""<div style='background:rgba(255,255,255,.03);border:1px solid #1E293B;border-radius:12px;padding:14px;margin-bottom:12px'>
        <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:4px'>
            <span style='color:#34D399;font-size:.78rem;font-weight:700'>매수 셋업 {spb:.1f}</span>
            <span style='color:{tow_color};font-size:.78rem;font-weight:700'>{tow_label}</span>
            <span style='color:#F87171;font-size:.78rem;font-weight:700'>매도 셋업 {sps:.1f}</span>
        </div>
        <div class='tow-bar'><div class='tow-buy' style='width:{bw}%'></div><div class='tow-sell' style='width:{sw}%'></div><div class='tow-center'></div></div>
    </div>""",unsafe_allow_html=True)
    # Tech snapshot
    st.markdown(f"""<div style='display:grid;grid-template-columns:repeat(6,1fr);gap:8px'>
        <div class='stat-mini'><p class='sm-label'>BB %B</p><p class='sm-value' style='color:{"#34D399" if pb_<0.3 else("#F87171" if pb_>0.7 else "#FF9800")}'>{pb_pct:.0f}%</p></div>
        <div class='stat-mini'><p class='sm-label'>CMF</p><p class='sm-value' style='color:{cmf_c}'>{cmf_:+.3f}</p></div>
        <div class='stat-mini'><p class='sm-label'>OBV 추세</p><p class='sm-value' style='color:{obv_c}'>{"상승" if m.get("obv_trend")=="rising" else "하락"}</p></div>
        <div class='stat-mini'><p class='sm-label'>ATR%</p><p class='sm-value' style='color:#A5B4FC'>{atr_pct:.1f}%</p></div>
        <div class='stat-mini'><p class='sm-label'>MA50 이격</p><p class='sm-value' style='color:{ma50c}'>{ma50d:+.1f}%</p></div>
        <div class='stat-mini'><p class='sm-label'>MA200 이격</p><p class='sm-value' style='color:{ma200c}'>{ma200d:+.1f}%</p></div>
    </div>""",unsafe_allow_html=True)

def render_combined_scans(m):
    scans=m.get('combined_scans',[])
    if not scans:st.info("활성 Combined Scan 없음");return
    bn=sum(1 for s in scans if s['dir']=='buy');sn_=sum(1 for s in scans if s['dir']=='sell');t1=sum(1 for s in scans if s['tier']==1)
    hc='#FFD700' if t1>0 else('#00E676' if bn>sn_ else('#FF1744' if sn_>bn else '#FF6D00'))
    st.markdown(f"<div style='background:rgba(255,215,0,.06);border:1px solid {hc}33;border-radius:12px;padding:12px;margin-bottom:10px'><span style='font-size:1.2rem;font-weight:800;color:{hc}'>[COMBO] {len(scans)} Active</span> <span style='color:#94A3B8;margin-left:12px'>T1:{t1} B:{bn} S:{sn_}</span></div>",unsafe_allow_html=True)
    cards=[]
    for s in scans:
        tb={1:'T1',2:'T2',3:'T3'}.get(s['tier'],'T?');is_buy=s['dir']=='buy';is_sell=s['dir']=='sell'
        dc_='#34D399' if is_buy else('#F87171' if is_sell else '#FF9800')
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
    with st.expander("ℹ️ 지표 도움말 (마우스 오버용 요약)"):
        st.markdown(
            "- `WT`: 과매수/과매도 반전 압력\n"
            "- `RSI`: 70↑ 과열, 30↓ 침체\n"
            "- `ADX`: 추세 강도(방향 아님)\n"
            "- `CMF`: 자금 유입/이탈 강도\n"
            "- `Ensemble Score`: -100~+100 종합 방향 점수\n"
            "- `10-Layer`: 추세, 모멘텀, 구조, 자금 등 레이어별 점수"
        )

def render_analysis(msg):
    m,fj=msg.get('meta'),msg.get('fig_json')
    if m:render_price_header(m)
    if m or fj:
        t0,t1,t2,t3,t4=st.tabs(["차트","종합판단","10-Layer","콤보스캔","기업정보"])
        with t0:
            if fj:fig=go.Figure(json.loads(fj));st.plotly_chart(fig,use_container_width=True,theme=None,config={'displaylogo':False,'modeBarButtonsToRemove':['lasso2d','select2d']});st.caption("*캔들 오버 시 툴팁, 강/약 시그널 캔들 하이라이트, 우측 매물대(VP) 오버레이를 함께 제공합니다.")
        with t1:
            if m:
                render_judgment_card(m)
                st.markdown("#### 🏛️ 5-Committee Ensemble")
                render_committee_panel(m)
                st.markdown("---")
                render_leading_lagging(m)
                render_indicator_help()
        with t2:
            if m:render_10layer_bars(m)
        with t3:
            if m:render_combined_scans(m)
        with t4:
            if m:render_company_details(m['ticker'])
