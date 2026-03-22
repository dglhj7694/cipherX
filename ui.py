import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
from config import *
from chart import build_metadata, build_chart
from company_details import render_company_details

def render_price_header(m):
    chg=m['price_change'];cp=m['price_change_pct'];cc='price-change-up' if chg>=0 else 'price-change-down';ci='▲' if chg>=0 else '▼'
    vr_=m['volume']/max(m['avg_volume'],1);jg=m['judgment'];cf=m['confidence'];es=m.get('ensemble_score',0)
    jc='#34D399' if 'BUY' in jg else('#F87171' if 'SELL' in jg else '#FF9800')
    act=m.get('action_label','');rsn=m.get('judgment_reason','')
    specs=[(jc,f"[{act}] {cf:.0f}%"),('ind-b' if m['wt1']<-20 else('ind-s' if m['wt1']>20 else 'ind-n'),f"WT{m['wt1']:.0f}"),('ind-b' if m['rsi']<40 else('ind-s' if m['rsi']>60 else 'ind-n'),f"RSI{m['rsi']:.0f}"),('ind-b' if vr_>1.5 else 'ind-n',f"Vol{vr_:.1f}x"),('ind-b' if m['adx']>25 else 'ind-n',f"ADX{m['adx']:.0f}"),('ind-b' if m.get('utbot_dir',0)==1 else('ind-s' if m.get('utbot_dir',0)==-1 else 'ind-n'),'[UT] B' if m.get('utbot_dir',0)==1 else('[UT] S' if m.get('utbot_dir',0)==-1 else '[UT] -')),('ind-b' if m.get('hma_rising') else 'ind-s','[HMA] UP' if m.get('hma_rising') else '[HMA] DN')]
    ih="".join([f"<span class='ind-mini {c}'>{l}</span>" for c,l in specs])
    rsn_html=f"<p style='color:#94A3B8;font-size:.82rem;margin:6px 0 0'>{rsn}</p>" if rsn else ""
    st.markdown(f"""<div class="price-header fade-up"><p style="color:#64748B;font-size:.8rem;margin:0">■ {m['ticker']} · {m['last_date']} · <b style="color:#A5B4FC">{m['regime_label']}</b> · <span style='color:#A5B4FC'>[CTX] {m.get('context_label','기본')}</span></p>
        <p class="price-big" style="color:#F8FAFC">${m['price']:.2f}<span class="{cc}" style="font-size:1.1rem;margin-left:10px;font-weight:700">{ci}{abs(chg):.2f}({abs(cp):.2f}%)</span></p>{rsn_html}
        <div style="margin-top:10px;display:flex;gap:4px;flex-wrap:wrap">{ih}</div></div>""",unsafe_allow_html=True)
    # Glass metric cards
    esc='#34D399' if es>0 else('#F87171' if es<0 else '#FF9800')
    es_pct=min(abs(es)/80*100,100)
    bt_=m['buy_total'];st_=m['sell_total'];ba_=m['buy_active'];sa_=m['sell_active']
    bt_pct=min(bt_/40*100,100);st_pct=min(st_/40*100,100)
    # 52w position bar
    h52=m.get('high_52w',m['price']);l52=m.get('low_52w',m['price']);rng=max(h52-l52,0.01);pos52=min(max((m['price']-l52)/rng*100,0),100)
    st.markdown(f"""<div style='display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px'>
        <div class='glass-metric'><p class='gm-label'>Ensemble Score</p><p class='gm-value' style='color:{esc}'>{es:+.1f}</p><p class='gm-sub'>B{m.get('buy_agree',0)} : S{m.get('sell_agree',0)}</p><div class='gm-bar'><div class='gm-bar-fill' style='width:{es_pct}%;background:{esc}'></div></div></div>
        <div class='glass-metric'><p class='gm-label'>BUY Score (10L)</p><p class='gm-value' style='color:#34D399'>{bt_:.1f}</p><p class='gm-sub'>{ba_}/10 레이어 활성</p><div class='gm-bar'><div class='gm-bar-fill' style='width:{bt_pct}%;background:#34D399'></div></div></div>
        <div class='glass-metric'><p class='gm-label'>SELL Score (10L)</p><p class='gm-value' style='color:#F87171'>{st_:.1f}</p><p class='gm-sub'>{sa_}/10 레이어 활성</p><div class='gm-bar'><div class='gm-bar-fill' style='width:{st_pct}%;background:#F87171'></div></div></div>
        <div class='glass-metric'><p class='gm-label'>52주 가격 위치</p><p class='gm-value' style='color:#A5B4FC'>{pos52:.0f}%</p><p class='gm-sub'>${l52:.1f} — ${h52:.1f}</p><div class='gm-bar'><div class='gm-bar-fill' style='width:{pos52}%;background:linear-gradient(90deg,#F87171,#FF9800,#34D399)'></div></div></div>
    </div>""",unsafe_allow_html=True)

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
    LN=['Trend','Momentum','Candle','BB','Volume','MF','Pattern','Combined','Leading','Lagging']
    bd=m['buy_layers'];sd=m['sell_layers']
    max_val=12
    rows_html=""
    for n in LN:
        bv=max(bd.get(n,0),0);sv=max(sd.get(n,0),0)
        bpct=min(bv/max_val*50,50);spct=min(sv/max_val*50,50)
        bop='1' if bv>0 else '.35';sop='1' if sv>0 else '.35'
        glow=''
        if abs(bv-sv)>4:glow='box-shadow:0 0 8px rgba(99,102,241,.2);'
        rows_html+=f"""<div class='dual-layer' style='{glow}'>
            <span class='dl-val' style='color:#34D399;opacity:{bop}'>{bv:.1f}</span>
            <div class='dl-bar-wrap'>
                <div class='dl-fill-b' style='width:{bpct}%;opacity:{bop}'></div>
                <div class='dl-fill-s' style='width:{spct}%;opacity:{sop}'></div>
                <div class='dl-center'></div>
            </div>
            <span class='dl-name'>{n}</span>
            <span class='dl-val' style='color:#F87171;opacity:{sop}'>{sv:.1f}</span>
        </div>"""
    ba_=m['buy_active'];sa_=m['sell_active']
    st.markdown(f"""<div style='background:rgba(15,19,32,.5);backdrop-filter:blur(12px);border:1px solid rgba(255,255,255,.05);border-radius:14px;padding:18px;margin-bottom:12px'>
        <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:14px'>
            <span style='color:#34D399;font-weight:700;font-size:.85rem'>▲ BUY ({ba_}/10)</span>
            <span style='color:#94A3B8;font-size:.75rem;font-weight:600'>10-Layer 매수/매도 비교</span>
            <span style='color:#F87171;font-weight:700;font-size:.85rem'>▼ SELL ({sa_}/10)</span>
        </div>{rows_html}</div>""",unsafe_allow_html=True)

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
    for s in scans:
        tb={1:'T1',2:'T2',3:'T3'}.get(s['tier'],'T?');dc_='#34D399' if s['dir']=='buy' else('#F87171' if s['dir']=='sell' else '#FF6D00')
        bg='rgba(0,230,118,.04)' if s['dir']=='buy' else('rgba(255,23,68,.04)' if s['dir']=='sell' else 'rgba(255,152,0,.04)')
        td="<span style='background:#FFD700;color:#000;padding:2px 6px;border-radius:4px;font-size:.65rem;font-weight:700'>TODAY</span>" if s['is_today'] else f"<span style='color:#64748B;font-size:.75rem'>{s['date']}</span>"
        st.markdown(f"<div class='cs-card' style='background:{bg};border-color:{dc_}'><div style='display:flex;justify-content:space-between;align-items:center'><span style='color:{dc_};font-weight:700'>■ {s['kor']} <span style='color:#64748B;font-size:.7rem'>{tb}</span></span><div>{td} <span style='color:#4FC3F7;font-size:.65rem;margin-left:6px'>WinRate:{s['win']}</span></div></div></div>",unsafe_allow_html=True)

def render_analysis(msg):
    m,fj=msg.get('meta'),msg.get('fig_json')
    if m:render_price_header(m)
    if m or fj:
        t0,t1,t2,t3,t4=st.tabs(["차트","종합판단","10-Layer","콤보스캔","기업정보"])
        with t0:
            if fj:fig=go.Figure(json.loads(fj));st.plotly_chart(fig,use_container_width=True,theme=None,config={'displaylogo':False,'modeBarButtonsToRemove':['lasso2d','select2d']});st.caption("*차트에 마우스를 올리면 상세 판단 사유 및 위원회 투표 현황 툴팁이 표시됩니다.")
        with t1:
            if m:
                render_judgment_card(m)
                st.markdown("#### 🏛️ 5-Committee Ensemble")
                render_committee_panel(m)
                st.markdown("---")
                render_leading_lagging(m)
        with t2:
            if m:render_10layer_bars(m)
        with t3:
            if m:render_combined_scans(m)
        with t4:
            if m:render_company_details(m['ticker'])
