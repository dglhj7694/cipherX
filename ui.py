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
    jc='#34D399' if 'BUY' in jg else('#F87171' if 'SELL' in jg else '#FCD34D')
    act=m.get('action_label','');rsn=m.get('judgment_reason','')
    specs=[(jc,f"📍{act}({cf:.0f}%)"),('ind-b' if m['wt1']<-20 else('ind-s' if m['wt1']>20 else 'ind-n'),f"WT{m['wt1']:.0f}"),('ind-b' if m['rsi']<40 else('ind-s' if m['rsi']>60 else 'ind-n'),f"RSI{m['rsi']:.0f}"),('ind-b' if vr_>1.5 else 'ind-n',f"Vol{vr_:.1f}x"),('ind-b' if m['adx']>25 else 'ind-n',f"ADX{m['adx']:.0f}"),('ind-b' if m.get('utbot_dir',0)==1 else('ind-s' if m.get('utbot_dir',0)==-1 else 'ind-n'),'🤖B' if m.get('utbot_dir',0)==1 else('🤖S' if m.get('utbot_dir',0)==-1 else '🤖—')),('ind-b' if m.get('hma_rising') else 'ind-s','🟢H' if m.get('hma_rising') else '🔴H')]
    ih="".join([f"<span class='ind-mini {c}'>{l}</span>" for c,l in specs])
    rsn_html=f"<p style='color:#94A3B8;font-size:.82rem;margin:6px 0 0'>💬 {rsn}</p>" if rsn else ""
    st.markdown(f"""<div class="price-header"><p style="color:#64748B;font-size:.8rem;margin:0">🚦 {m['ticker']} · {m['last_date']} · <b style="color:#A5B4FC">{m['regime_label']}</b> · <span style='color:#A5B4FC'>🌐{m.get('context_label','기본')}</span></p>
        <p class="price-big" style="color:#F8FAFC">${m['price']:.2f}<span class="{cc}" style="font-size:1.1rem;margin-left:10px;font-weight:700">{ci}{abs(chg):.2f}({abs(cp):.2f}%)</span></p>{rsn_html}
        <div style="margin-top:10px;display:flex;gap:4px;flex-wrap:wrap">{ih}</div></div>""",unsafe_allow_html=True)
    c1,c2,c3,c4=st.columns(4)
    with c1:st.metric("Ensemble",f"{es:+.1f}",delta=f"B{m.get('buy_agree',0)}:S{m.get('sell_agree',0)}")
    with c2:st.metric("BUY(10L)",f"{m['buy_total']:.1f}",delta=f"{m['buy_active']}/{NUM_LAYERS}")
    with c3:st.metric("SELL(10L)",f"{m['sell_total']:.1f}",delta=f"{m['sell_active']}/{NUM_LAYERS}",delta_color="inverse")
    with c4:st.metric("Conf",f"{m['confidence']:.0f}%",delta=f"⏳{m['leading_verdict']}")

def render_judgment_card(m):
    jg=m['judgment'];es=m.get('ensemble_score',0);cf=m['confidence']
    cc='score-card-buy' if 'BUY' in jg else('score-card-sell' if 'SELL' in jg else 'score-card-neutral')
    jc='#34D399' if 'BUY' in jg else('#F87171' if 'SELL' in jg else '#FCD34D')
    labels={'STRONG_BUY':'🟢🟢🟢 STRONG BUY','BUY':'🟢🟢 BUY','WATCH_BUY':'🟡🟢 WATCH BUY','NEUTRAL':'⚪ NEUTRAL','MIXED':'🟠 MIXED','WATCH_SELL':'🟡🔴 WATCH SELL','SELL':'🔴🔴 SELL','STRONG_SELL':'🔴🔴🔴 STRONG SELL'}
    ba=m.get('buy_agree',0);sa=m.get('sell_agree',0);veto=m.get('veto_flags','');syn=m.get('reversal_synergy',0);pred=m.get('prediction_boost',0)
    reason=m.get('judgment_reason','');detail=m.get('judgment_detail','');action=m.get('action_label','')
    reason_html=""
    if reason:reason_html=f"<div class='reason-card'><p style='color:{jc};font-weight:800;font-size:.95rem;margin:0 0 4px'>🏷️ {action}</p><p style='color:#E8ECF1;font-size:.88rem;margin:0 0 4px'>💬 {reason}</p><p style='color:#94A3B8;font-size:.78rem;margin:0'>📋 {detail}</p></div>"
    veto_html=f"<div style='margin-top:6px'><span style='background:rgba(239,68,68,.15);color:#FCA5A5;padding:3px 8px;border-radius:6px;font-size:.7rem;font-weight:700'>🚫 {veto}</span></div>" if veto else ""
    extra=""
    if abs(syn)>5:extra+=f"<span style='color:{'#34D399' if syn>0 else '#F87171'};font-size:.8rem;margin:0 4px'>🔄시너지:{syn:+.1f}</span>"
    if abs(pred)>3:extra+=f"<span style='color:{'#34D399' if pred>0 else '#F87171'};font-size:.8rem;margin:0 4px'>🔮예측:{pred:+.1f}</span>"
    st.markdown(f"""<div class="score-card {cc}"><p style="font-size:2rem;font-weight:800;color:{jc};margin:0">{labels.get(jg,jg)}</p>
        <div style="display:flex;align-items:center;gap:10px;justify-content:center;margin-top:8px"><div style="flex:0 0 200px;height:8px;background:#1E293B;border-radius:4px;overflow:hidden"><div style="width:{min(cf,100)}%;height:8px;background:{jc};border-radius:4px"></div></div><span style="color:{jc};font-weight:800;font-size:1.1rem">{cf:.0f}%</span></div>
        {reason_html}
        <div style="display:flex;justify-content:center;gap:32px;margin-top:14px"><div><p style="color:#64748B;font-size:.7rem;margin:0">Ensemble</p><p style="color:{'#34D399' if es>0 else '#F87171' if es<0 else '#FCD34D'};font-size:1.4rem;font-weight:800;margin:2px 0">{es:+.1f}</p></div>
        <div style="border-left:1px solid rgba(255,255,255,.08);padding-left:32px"><p style="color:#64748B;font-size:.7rem;margin:0">찬성</p><p style="color:#F8FAFC;font-size:1.4rem;font-weight:800;margin:2px 0">B{ba}:S{sa}</p></div>
        <div style="border-left:1px solid rgba(255,255,255,.08);padding-left:32px"><p style="color:#64748B;font-size:.7rem;margin:0">컨텍스트</p><p style="color:#A5B4FC;font-size:1rem;font-weight:700;margin:2px 0">🌐{m.get('context_label','기본')}</p></div></div>
        <div style='margin-top:8px'>{extra}</div>{veto_html}</div>""",unsafe_allow_html=True)

def render_committee_panel(m):
    committee=m.get('committee',{})
    if not committee:return
    ctx_code=m.get('context',0);ctx_name=CTX_LABELS.get(ctx_code,'default');weights=CONTEXT_WEIGHTS.get(ctx_name,CONTEXT_WEIGHTS['default'])
    st.markdown(f"#### 🌐 컨텍스트: {m.get('context_label','기본')}")
    cols=st.columns(5)
    for ci,cm in enumerate(COMMITTEE_NAMES):
        data=committee.get(cm,{});score=data.get('score',0);conv=data.get('conviction',0);vote=data.get('vote','NEUTRAL');weight=weights[ci] if ci<len(weights) else 0.2
        with cols[ci]:st.metric(label=f"{COMMITTEE_ICONS.get(cm,'•')} {cm} ×{weight:.0%}",value=f"{score:+.0f}",delta=f"{vote} ({conv:.0f}%)",delta_color="normal" if score>0 else "inverse" if score<0 else "off")
    veto=m.get('veto_flags','')
    if veto:st.warning(f"🚫 **거부권:** {veto}")
    syn=m.get('reversal_synergy',0)
    if abs(syn)>5:st.info(f"🔄 **교차시너지:** {syn:+.1f}")

def render_10layer_bars(m):
    LN=['Trend','Momentum','Candle','BB','Volume','MF','Pattern','Combined','Leading','Lagging'];icons={'Trend':'📈','Momentum':'🔥','Candle':'🕯️','BB':'📊','Volume':'📦','MF':'💰','Pattern':'⭐','Combined':'🎯','Leading':'⏳','Lagging':'📊'}
    c1,c2=st.columns(2)
    for col_st,side,data,color,fcls in [(c1,'BUY',m['buy_layers'],'#34D399','layer-fill-b'),(c2,'SELL',m['sell_layers'],'#F87171','layer-fill-s')]:
        with col_st:
            st.markdown(f"<p style='color:{color};font-weight:700;font-size:.85rem'>{'▲' if side=='BUY' else '▼'} {side}</p>",unsafe_allow_html=True)
            for n in LN:v_=data.get(n,0);pct=min(max(v_,0)/12*100,100);op='1' if v_>0 else '.3';st.markdown(f"<div class='layer-row'><span style='color:#94A3B8;font-size:.78rem;opacity:{op};width:80px'>{icons.get(n,'•')} {n}</span><div class='layer-bar'><div class='{fcls}' style='width:{pct}%;opacity:{op}'></div></div><span style='color:{color};font-weight:700;font-size:.78rem;width:35px;text-align:right;opacity:{op}'>{v_:.1f}</span></div>",unsafe_allow_html=True)

def render_leading_lagging(m):
    lv=m['leading_verdict'];lgv=m['lagging_verdict'];ac=m['composite_accel']
    lc='#34D399' if '상승' in lv else('#F87171' if '하락' in lv else '#FCD34D');lgc='#34D399' if '상승' in lgv else('#F87171' if '하락' in lgv else '#FCD34D')
    st.markdown(f"""<div style="background:rgba(255,255,255,.03);border:1px solid #1E293B;border-radius:12px;padding:14px;margin-bottom:10px"><p style="font-weight:700;color:#A5B4FC;margin:0 0 8px">⏳ 선행지표</p><p style="color:{lc};font-weight:800;font-size:1.1rem;margin:0">{lv}</p>
        <div style="display:flex;gap:10px;margin-top:8px;flex-wrap:wrap"><span style="color:#94A3B8;font-size:.8rem">가속도:<b style="color:{'#34D399' if ac>0 else '#F87171'}">{ac:+.2f}</b></span><span style="color:#94A3B8;font-size:.8rem">UT:{'🤖매수' if m.get('utbot_dir',0)==1 else('🤖매도' if m.get('utbot_dir',0)==-1 else '🤖중립')}</span><span style="color:#94A3B8;font-size:.8rem">Hull:{'🟢상승' if m.get('hma_rising') else '🔴하락'}</span></div></div>""",unsafe_allow_html=True)
    st.markdown(f"""<div style="background:rgba(255,255,255,.03);border:1px solid #1E293B;border-radius:12px;padding:14px"><p style="font-weight:700;color:#A5B4FC;margin:0 0 8px">📊 후행지표</p><p style="color:{lgc};font-weight:800;font-size:1.1rem;margin:0">{lgv}</p>
        <div style="display:flex;gap:16px;margin-top:8px"><span style="color:#94A3B8;font-size:.8rem">국면:<b>{m['regime_label']}</b></span><span style="color:#94A3B8;font-size:.8rem">RS:<b style="color:{'#34D399' if m['rs_ratio']>1.03 else('#F87171' if m['rs_ratio']<.97 else '#FCD34D')}">{m['rs_ratio']:.3f}</b></span></div></div>""",unsafe_allow_html=True)

def render_combined_scans(m):
    scans=m.get('combined_scans',[])
    if not scans:st.info("🔍 활성 CS 없음");return
    bn=sum(1 for s in scans if s['dir']=='buy');sn_=sum(1 for s in scans if s['dir']=='sell');t1=sum(1 for s in scans if s['tier']==1)
    hc='#FFD700' if t1>0 else('#00E676' if bn>sn_ else('#FF1744' if sn_>bn else '#FFC107'))
    st.markdown(f"<div style='background:rgba(255,215,0,.06);border:1px solid {hc}33;border-radius:12px;padding:12px;margin-bottom:10px'><span style='font-size:1.2rem;font-weight:800;color:{hc}'>🎯 CS:{len(scans)}개</span> <span style='color:#94A3B8;margin-left:12px'>T1:{t1} B:{bn} S:{sn_}</span></div>",unsafe_allow_html=True)
    for s in scans:
        tb={1:'🥇T1',2:'🥈T2',3:'🥉T3'}.get(s['tier'],'T?');dc_='#34D399' if s['dir']=='buy' else('#F87171' if s['dir']=='sell' else '#FFC107')
        bg='rgba(0,230,118,.04)' if s['dir']=='buy' else('rgba(255,23,68,.04)' if s['dir']=='sell' else 'rgba(255,193,7,.04)')
        td="<span style='background:#FFD700;color:#000;padding:2px 6px;border-radius:4px;font-size:.65rem;font-weight:700'>TODAY</span>" if s['is_today'] else f"<span style='color:#64748B;font-size:.75rem'>{s['date']}</span>"
        st.markdown(f"<div class='cs-card' style='background:{bg};border-color:{dc_}'><div style='display:flex;justify-content:space-between;align-items:center'><span style='color:{dc_};font-weight:700'>{s['icon']} {s['kor']} <span style='color:#64748B;font-size:.7rem'>{tb}</span></span><div>{td} <span style='color:#4FC3F7;font-size:.65rem;margin-left:6px'>승률:{s['win']}</span></div></div></div>",unsafe_allow_html=True)

def render_analysis(msg):
    m,fj=msg.get('meta'),msg.get('fig_json')
    if m:render_price_header(m)
    if m or fj:
        t0,t1,t2,t3,t4,t5=st.tabs(["차트","위원회","매매판단","Combined Scan","선행/후행","기업 상세"])
        with t0:
            if fj:fig=go.Figure(json.loads(fj));st.plotly_chart(fig,use_container_width=True,theme=None,config={'displaylogo':False,'modeBarButtonsToRemove':['lasso2d','select2d']});st.caption("💡 캔들 호버 → 판단이유 + 모든 시그널 + 위원회 투표")
        with t1:
            if m:render_judgment_card(m);st.markdown("#### 🏛️ 5-Committee");render_committee_panel(m)
        with t2:
            if m:st.markdown("#### 📊 10-Layer (참고)");render_10layer_bars(m)
        with t3:
            if m:render_combined_scans(m)
        with t4:
            if m:render_leading_lagging(m)
        with t5:
            if m:render_company_details(m['ticker'])
