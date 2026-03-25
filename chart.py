import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from config import *
from utils import _sf

SOFT_GREEN = '#7ED8B6'
SOFT_GREEN_FILL = 'rgba(126,216,182,.78)'
SOFT_RED = '#F3A5A5'
SOFT_RED_FILL = 'rgba(243,165,165,.78)'
SOFT_AMBER = '#F5C77B'

def _build_candle_hover(dc):
    n=len(dc)
    bar_buy=[[] for _ in range(n)];bar_sell=[[] for _ in range(n)];bar_neutral=[[] for _ in range(n)]
    bar_cs=[[] for _ in range(n)];bar_sb=[[] for _ in range(n)];bar_ss=[[] for _ in range(n)]
    for sn,cfg in SIGNAL_REGISTRY.items():
        if sn not in dc.columns:continue
        vals=dc[sn].fillna(False).values
        if not vals.any():continue
        ix=np.flatnonzero(vals);lbl=f"{cfg['icon']}{cfg['kor']}";desc=cfg['desc'];isb=sn in STRONG_BUY_SIGS;iss=sn in STRONG_SELL_SIGS
        if cfg['dir']=='buy':
            for i in ix:bar_buy[i].append((lbl,desc));
            if isb:
                for i in ix:bar_sb[i].append((lbl,desc))
        elif cfg['dir']=='sell':
            for i in ix:bar_sell[i].append((lbl,desc));
            if iss:
                for i in ix:bar_ss[i].append((lbl,desc))
        else:
            for i in ix:bar_neutral[i].append((lbl,desc))
    for cn,ccfg in COMBINED_SCAN_REGISTRY.items():
        if cn not in dc.columns:continue
        vals=dc[cn].fillna(False).values
        if not vals.any():continue
        ix=np.flatnonzero(vals);lbl=f"{ccfg['icon']}{ccfg['kor']}";desc=ccfg['desc']
        for i in ix:
            bar_cs[i].append((lbl,desc,ccfg['dir']))
            if cn in STRONG_BUY_SIGS:bar_sb[i].append((lbl,desc))
            if cn in STRONG_SELL_SIGS:bar_ss[i].append((lbl,desc))
    dates=dc.index.strftime('%Y-%m-%d').values
    def _g(c,d=0):return dc[c].values if c in dc.columns else np.full(n,d)
    def _gs(c,d=''):return dc[c].values if c in dc.columns else np.full(n,d,dtype=object)
    ov=_g('Open');hv=_g('High');lv=_g('Low');cv=_g('Close');vol=_g('Volume');atr=_g('ATR')
    wt=_g('WT1');rs=_g('RSI',50);mf=_g('MFI',50);jg=_gs('Trade_Judgment','');cf=_g('Judgment_Confidence')
    esv=_g('Ensemble_Score');ctxv=_g('Market_Context');ut=_g('UTBot_Dir')
    hma=dc.get('HMA_Rising',pd.Series(False,index=dc.index)).fillna(False).values
    veto=_gs('Veto_Flags','');pred=_g('Prediction_Boost');reason=_gs('Judgment_Reason','');action=_gs('Action_Label','')
    lv_v=_gs('Leading_Verdict','');lgv=_gs('Lagging_Verdict','')
    cms={cm:_g(f'CM_{cm}_EffScore') for cm in COMMITTEE_NAMES};cmv={cm:_g(f'CM_{cm}_Vote') for cm in COMMITTEE_NAMES}
    texts=[]
    for i in range(n):
        p=[]
        p.append(f"<b>{dates[i]}</b> O:{ov[i]:.2f} H:{hv[i]:.2f} L:{lv[i]:.2f} C:{cv[i]:.2f}")
        p.append(f"Vol:{vol[i]:,.0f} ATR:{atr[i]:.2f}")
        p.append("─"*28)
        cl=CTX_KOR.get(int(ctxv[i]),'기본');act=str(action[i]) if action[i] else ''
        p.append(f"<b>📍{act}</b> ({cf[i]:.0f}%) ES:{esv[i]:+.1f} [{cl}]")
        rsn=str(reason[i])
        if rsn:
            rc='#6EE7B7' if 'BUY' in str(jg[i]) or '매수' in act else('#FCA5A5' if 'SELL' in str(jg[i]) or '매도' in act else '#FCD34D')
            p.append(f"<span style='color:{rc};font-size:11px'>💬 {rsn}</span>")
        p.append(f"WT:{wt[i]:.0f} RSI:{rs[i]:.0f} MFI:{mf[i]:.0f} UT:{'B' if ut[i]==1 else 'S' if ut[i]==-1 else '-'} Hull:{'🟢' if hma[i] else '🔴'}")
        if abs(pred[i])>3:p.append(f"<span style='color:{'#6EE7B7' if pred[i]>0 else '#FCA5A5'}'>🔮예측:{pred[i]:+.1f}</span>")
        vp=[]
        for cm in COMMITTEE_NAMES:
            v=cmv[cm][i];s=cms[cm][i];ic=COMMITTEE_ICONS.get(cm,'•')
            if v==1:vp.append(f"<span style='color:#6EE7B7'>{ic}B{s:+.0f}</span>")
            elif v==-1:vp.append(f"<span style='color:#FCA5A5'>{ic}S{s:+.0f}</span>")
            elif v==-99:vp.append(f"<span style='color:#475569'>{ic}—</span>")
            else:vp.append(f"<span style='color:#FCD34D'>{ic}N{s:+.0f}</span>")
        p.append(' '.join(vp))
        vs=str(veto[i]) if veto[i] else ''
        if vs:p.append(f"<span style='color:#FCA5A5'>🚫{vs}</span>")
        if lv_v[i]!='중립' or lgv[i]!='비추세/횡보':p.append(f"⏳{lv_v[i]}|📊{lgv[i]}")
        if bar_sb[i] or bar_ss[i]:
            p.append("─"*28)
            for l,d in bar_sb[i]:p.append(f"<span style='color:#6EE7B7'>⭐{l}: {d}</span>")
            for l,d in bar_ss[i]:p.append(f"<span style='color:#FCA5A5'>⭐{l}: {d}</span>")
        if bar_cs[i]:
            p.append("─"*28)
            for l,d,dr in bar_cs[i]:
                c='#6EE7B7' if dr=='buy' else('#FCA5A5' if dr=='sell' else '#FCD34D')
                p.append(f"<span style='color:{c}'>🎯{l}: {d}</span>")
        bs=bar_buy[i];ss=bar_sell[i];ns=bar_neutral[i]
        if bs or ss or ns:p.append("─"*28)
        if bs:
            p.append(f"<span style='color:#6EE7B7'><b>▲매수({len(bs)})</b></span>")
            for l,d in bs:p.append(f"<span style='color:#6EE7B7'> {l} <span style='color:#94A3B8;font-size:10px'>({d})</span></span>")
        if ss:
            p.append(f"<span style='color:#FCA5A5'><b>▼매도({len(ss)})</b></span>")
            for l,d in ss:p.append(f"<span style='color:#FCA5A5'> {l} <span style='color:#94A3B8;font-size:10px'>({d})</span></span>")
        if ns:
            p.append(f"<span style='color:#FCD34D'><b>◆중립({len(ns)})</b></span>")
            for l,d in ns:p.append(f"<span style='color:#FCD34D'> {l} <span style='color:#94A3B8;font-size:10px'>({d})</span></span>")
        texts.append("<br>".join(p))
    return texts

def _collect_strong_markers(dc):
    idx=dc.index;sb=pd.Series(False,index=idx);ss=pd.Series(False,index=idx)
    for sn in STRONG_BUY_SIGS:
        if sn in dc.columns:sb|=dc[sn].fillna(False)
    for sn in STRONG_SELL_SIGS:
        if sn in dc.columns:ss|=dc[sn].fillna(False)
    return sb,ss

def _add_signal_boxes(fig,dc,strong_buy,strong_sell):
    half=pd.Timedelta(hours=12)
    for ts in dc.index[strong_buy.fillna(False)]:
        fig.add_vrect(x0=ts-half,x1=ts+half,fillcolor='rgba(16,185,129,.10)',line_width=0,row=1,col=1,layer='below')
    for ts in dc.index[strong_sell.fillna(False)]:
        fig.add_vrect(x0=ts-half,x1=ts+half,fillcolor='rgba(239,68,68,.10)',line_width=0,row=1,col=1,layer='below')

def _add_volume_profile_overlay(fig,dc):
    if dc.empty:return
    low=float(dc['Low'].min());high=float(dc['High'].max())
    if not np.isfinite(low) or not np.isfinite(high) or high<=low:return
    bins=24;edges=np.linspace(low,high,bins+1);prof=np.zeros(bins,dtype=float)
    tp=((dc['High']+dc['Low']+dc['Close'])/3).values
    vol=dc['Volume'].fillna(0).values.astype(float)
    bidx=np.clip(np.digitize(tp,edges)-1,0,bins-1)
    for bi,v in zip(bidx,vol):
        if np.isfinite(v) and v>0:prof[int(bi)]+=float(v)
    vmax=float(prof.max()) if len(prof)>0 else 0.0
    if vmax<=0:return
    span=max(int((dc.index[-1]-dc.index[0]).days),20)
    x_right=dc.index[-1]+pd.Timedelta(days=3)
    max_width=pd.Timedelta(days=max(4,int(span*0.18)))
    for bi,pv in enumerate(prof):
        if pv<=0:continue
        f=float(pv/vmax);alpha=min(.30,max(.08,.08+.22*f))
        fig.add_shape(type='rect',x0=x_right-max_width*f,x1=x_right,y0=float(edges[bi]),y1=float(edges[bi+1]),
            fillcolor=f'rgba(99,102,241,{alpha})',line=dict(width=0),row=1,col=1,layer='below')
    vp_colors=[('VP_POC','#A5B4FC','dot'),('VP_VAH','#60A5FA','dash'),('VP_VAL',SOFT_GREEN,'dash')]
    for col,clr,sty in vp_colors:
        if col in dc.columns:
            val=float(dc[col].iloc[-1])
            if np.isfinite(val):fig.add_hline(y=val,line_color=clr,line_dash=sty,line_width=1,row=1,col=1)
    fig.add_trace(go.Scatter(x=[x_right],y=[dc['Close'].iloc[-1]],mode='markers',marker=dict(size=.1,color='rgba(0,0,0,0)'),hoverinfo='skip',showlegend=False),row=1,col=1)
    fig.add_annotation(x=x_right,y=high,text='VP',showarrow=False,font=dict(size=9,color='#94A3B8'),xanchor='right',yanchor='top',row=1,col=1)

def _sig_marker(fig,dc,sn,row,y,clr,sym,sz,lbl):
    reg=SIGNAL_REGISTRY.get(sn) or COMBINED_SCAN_REGISTRY.get(sn,{})
    if sn not in dc.columns:return
    mask=dc[sn].fillna(False)
    if not mask.any():return
    sr=dc[mask];yv=y[mask] if isinstance(y,pd.Series) else pd.Series(y,index=dc.index)[mask]
    valid=yv.notna()
    if not valid.any():return
    sr=sr[valid];yv=yv[valid];kor=reg.get('kor','');desc=reg.get('desc','')
    ht=f"<b>{lbl}</b> ({kor})<br><span style='color:#94A3B8'>{desc}</span><br>%{{x|%Y-%m-%d}}<extra></extra>" if kor else f"<b>{lbl}</b><br>%{{x|%Y-%m-%d}}<extra></extra>"
    fig.add_trace(go.Scatter(x=sr.index,y=yv,mode='markers',marker=dict(symbol=sym,size=sz,color=clr,line=dict(width=1.5,color='#FFF'),opacity=.95),name=lbl,showlegend=False,hovertemplate=ht),row=row,col=1)

def build_chart(dc,ticker):
    mac={20:'#f1c40f',50:'#e74c3c',200:'#2ecc71'}
    fig=make_subplots(rows=8,cols=1,shared_xaxes=True,vertical_spacing=0.02,row_heights=[.32,.04,.09,.09,.09,.09,.09,.19],subplot_titles=(ticker,"Vol","WaveTrend","MACD","Money Flow","Stoch Slow","Squeeze Mom","5-Committee Ensemble"))
    hover=_build_candle_hover(dc)
    fig.add_trace(go.Candlestick(x=dc.index,open=dc['Open'],high=dc['High'],low=dc['Low'],close=dc['Close'],name="Price",increasing_line_color=SOFT_GREEN,decreasing_line_color=SOFT_RED,increasing_fillcolor=SOFT_GREEN_FILL,decreasing_fillcolor=SOFT_RED_FILL,text=hover,hoverinfo='text',hoverlabel=dict(bgcolor='rgba(11,14,20,.97)',bordercolor='#334155',font=dict(size=11,family='Pretendard',color='#F1F5F9'),align='left')),row=1,col=1)
    for mp in [20,50,200]:fig.add_trace(go.Scatter(x=dc.index,y=dc[f'MA{mp}'],line=dict(color=mac[mp],width=1.2),name=f'{mp}MA',hoverinfo='skip',showlegend=(mp==200)),row=1,col=1)
    for mc,clr,nm in [(dc['ST_Direction']==1,SOFT_GREEN,'ST▲'),(dc['ST_Direction']==-1,SOFT_RED,'ST▼')]:fig.add_trace(go.Scatter(x=dc.index,y=dc['SuperTrend'].where(mc),line=dict(color=clr,width=2),name=nm,connectgaps=False,hoverinfo='skip',showlegend=False),row=1,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['BB_Up'],line=dict(color='#475569',width=1,dash='dot'),name='BB',hoverinfo='skip',showlegend=False),row=1,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['BB_Low'],line=dict(color='#475569',width=1,dash='dot'),fill='tonexty',fillcolor='rgba(71,85,105,.06)',hoverinfo='skip',showlegend=False),row=1,col=1)
    if 'HMA' in dc.columns:
        hup=dc.get('HMA_Rising',pd.Series(False,index=dc.index)).fillna(False)
        fig.add_trace(go.Scatter(x=dc.index,y=dc['HMA'].where(hup),line=dict(color=SOFT_GREEN,width=2.5),name='HMA▲',connectgaps=False,hoverinfo='skip'),row=1,col=1)
        fig.add_trace(go.Scatter(x=dc.index,y=dc['HMA'].where(~hup),line=dict(color=SOFT_RED,width=2.5),name='HMA▼',connectgaps=False,hoverinfo='skip',showlegend=False),row=1,col=1)
    if 'UTBot_Stop' in dc.columns:
        ub=dc['UTBot_Dir']==1;us=dc['UTBot_Dir']==-1
        fig.add_trace(go.Scatter(x=dc.index,y=dc['UTBot_Stop'].where(ub),line=dict(color='rgba(126,216,182,.5)',width=2,dash='dot'),name='UTBot▲',connectgaps=False,hoverinfo='skip'),row=1,col=1)
        fig.add_trace(go.Scatter(x=dc.index,y=dc['UTBot_Stop'].where(us),line=dict(color='rgba(243,165,165,.5)',width=2,dash='dot'),name='UTBot▼',connectgaps=False,hoverinfo='skip',showlegend=False),row=1,col=1)
    for sn,clr,sym,sz,lbl in [('Hull_Turn_Bull',SOFT_GREEN,'circle',8,'🟢Hull▲'),('Hull_Turn_Bear',SOFT_RED,'circle',8,'🔴Hull▼'),('UTBot_Buy',SOFT_GREEN,'triangle-up',12,'🤖UTBot▲'),('UTBot_Sell',SOFT_RED,'triangle-down',12,'🤖UTBot▼'),('VuManChu_Bull',SOFT_GREEN,'diamond',12,'💎VuMC▲'),('VuManChu_Bear',SOFT_RED,'diamond',12,'💎VuMC▼')]:
        yoff=dc['Low']-dc['ATR']*(0.8 if 'Hull' in sn else 1.2 if 'UTBot' in sn else 1.8) if 'Bull' in sn or 'Buy' in sn else dc['High']+dc['ATR']*(0.8 if 'Hull' in sn else 1.2 if 'UTBot' in sn else 1.8)
        _sig_marker(fig,dc,sn,1,yoff,clr,sym,sz,lbl)
    sb,ss=_collect_strong_markers(dc)
    _add_signal_boxes(fig,dc,sb,ss)
    _add_volume_profile_overlay(fig,dc)
    if sb.any():
        sr=dc[sb];yv=sr['Low']-sr['ATR']*2;ht=[]
        for bi in sr.index:
            br=[SIGNAL_REGISTRY.get(s,COMBINED_SCAN_REGISTRY.get(s,{})).get('kor',s) for s in STRONG_BUY_SIGS if s in dc.columns and dc.loc[bi,s]]
            ht.append(f"<b>⭐강력매수</b><br><span style='color:#94A3B8'>{', '.join(br[:5]) or '다중강세'}</span><br>{bi.strftime('%Y-%m-%d')}")
        fig.add_trace(go.Scatter(x=sr.index,y=yv,mode='markers',marker=dict(symbol='star',size=8,color='#E8C56C',line=dict(width=2,color=SOFT_GREEN),opacity=.95),name='⭐강력매수',hovertemplate="%{text}<extra></extra>",text=ht),row=1,col=1)
    if ss.any():
        sr=dc[ss];yv=sr['High']+sr['ATR']*2;ht=[]
        for bi in sr.index:
            br=[SIGNAL_REGISTRY.get(s,COMBINED_SCAN_REGISTRY.get(s,{})).get('kor',s) for s in STRONG_SELL_SIGS if s in dc.columns and dc.loc[bi,s]]
            ht.append(f"<b>⭐강력매도</b><br><span style='color:#94A3B8'>{', '.join(br[:5]) or '다중약세'}</span><br>{bi.strftime('%Y-%m-%d')}")
        fig.add_trace(go.Scatter(x=sr.index,y=yv,mode='markers',marker=dict(symbol='star',size=8,color='#E8C56C',line=dict(width=2,color=SOFT_RED),opacity=.95),name='⭐강력매도',hovertemplate="%{text}<extra></extra>",text=ht),row=1,col=1)
    # R2 Vol
    bb=dc['Close']<dc['Open'];fig.add_trace(go.Bar(x=dc.index,y=dc['Volume'],marker_color=np.where(bb,'rgba(243,165,165,.5)','rgba(126,216,182,.5)').tolist(),name="Vol",opacity=.8,hoverinfo='skip',showlegend=False),row=2,col=1)
    # R3 WT
    fig.add_trace(go.Scatter(x=dc.index,y=dc['WT1'],line=dict(color=SOFT_GREEN,width=2),name="WT1",hovertemplate="WT1:%{y:.1f}<br><span style='color:#94A3B8'>과매수/과매도 압력 지표</span><extra></extra>"),row=3,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['WT2'],line=dict(color=SOFT_RED,width=1.5,dash='dot'),hoverinfo='skip',showlegend=False),row=3,col=1)
    wd=dc['WT1']-dc['WT2'];fig.add_trace(go.Bar(x=dc.index,y=wd,marker_color=np.where(wd>=0,'rgba(126,216,182,.25)','rgba(243,165,165,.25)').tolist(),hoverinfo='skip',showlegend=False),row=3,col=1)
    for y_,c_,d_ in [(OB1,'#FF5252','solid'),(0,'#475569','dot'),(OS1,'#4FC3F7','solid')]:fig.add_hline(y=y_,line_dash=d_,line_color=c_,line_width=1,row=3,col=1)
    for sn,clr,sym,sz,lbl in [('Gold_Dot','#FFD700','star',14,'🏆Gold'),('Green_Dot_T1','#00E676','circle',10,'🟢T1'),('Green_Dot_T2','#69F0AE','circle',8,'🟩T2'),('Blood_Diamond','#DC143C','star',14,'🩸Blood'),('Red_Dot_T1','#FF1744','circle',10,'🔴T1'),('Red_Dot_T2','#FF5252','circle',8,'🟥T2'),('Bull_Divergence','#AA00FF','triangle-up',10,'📈BullDiv'),('Bear_Divergence','#AA00FF','triangle-down',10,'📉BearDiv'),('RSI_Bull_Divergence','#CE93D8','triangle-up',8,'📊RSIDiv▲'),('RSI_Bear_Divergence','#CE93D8','triangle-down',8,'📊RSIDiv▼')]:_sig_marker(fig,dc,sn,3,dc['WT1'],clr,sym,sz,lbl)
    # R4 MACD
    fig.add_trace(go.Scatter(x=dc.index,y=dc['MACD_Line'],line=dict(color='#29B6F6',width=1.5),name="MACD",hovertemplate="MACD:%{y:.3f}<br><span style='color:#94A3B8'>0 상향이면 상승 모멘텀 우위</span><extra></extra>"),row=4,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['MACD_Signal'],line=dict(color='#FFA726',width=1.5),hoverinfo='skip',showlegend=False),row=4,col=1)
    mh_=dc['MACD_Hist'];fig.add_trace(go.Bar(x=dc.index,y=mh_,marker_color=np.where(mh_>=0,'#26A69A','#EF5350').tolist(),opacity=.7,hoverinfo='skip',showlegend=False),row=4,col=1)
    fig.add_hline(y=0,line_color="#475569",line_width=1,row=4,col=1)
    for sn,clr,sym,sz,lbl in [('MACD_Cross_Buy','#00E676','triangle-up',10,'〽️MCD▲'),('MACD_Cross_Sell','#FF1744','triangle-down',10,'〽️MCD▼'),('MACD_Zero_Cross_Buy','#4CAF50','diamond',8,'⬆️MC0▲'),('MACD_Zero_Cross_Sell','#E57373','diamond',8,'⬇️MC0▼')]:_sig_marker(fig,dc,sn,4,dc['MACD_Line'],clr,sym,sz,lbl)
    # R5 MFI
    mfr=dc.get('MFI',pd.Series(50,index=dc.index));mfc=mfr-50;rmfi=dc.get('RSI_MFI',pd.Series(0,index=dc.index))
    fig.add_trace(go.Bar(x=dc.index,y=rmfi,marker_color=np.where(rmfi>=0,'rgba(0,230,118,.35)','rgba(255,23,68,.35)').tolist(),opacity=.7,hoverinfo='skip',showlegend=False),row=5,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=mfc,line=dict(color='#AB47BC',width=2.5),name="MFI",hovertemplate="MFI:%{customdata:.1f}<br><span style='color:#94A3B8'>자금 유입/이탈 강도</span><extra></extra>",customdata=mfr.values),row=5,col=1)
    fig.add_hrect(y0=30,y1=50,fillcolor="rgba(239,68,68,.08)",line_width=0,row=5,col=1);fig.add_hrect(y0=-50,y1=-30,fillcolor="rgba(16,185,129,.08)",line_width=0,row=5,col=1)
    for y_,c_,d_ in [(30,'#FF5252','dash'),(-30,'#4FC3F7','dash'),(0,'#475569','solid')]:fig.add_hline(y=y_,line_dash=d_,line_color=c_,line_width=1,row=5,col=1)
    for sn,clr,sym,sz,lbl in [('MF_Cross_Bull','#00E676','triangle-up',10,'💰MF▲'),('MF_Cross_Bear','#FF1744','triangle-down',10,'💸MF▼'),('MF_Bull_Div','#7C4DFF','diamond',10,'💹MFDiv▲'),('MF_Bear_Div','#E040FB','diamond',10,'💹MFDiv▼'),('CMF_Bull','#00BCD4','circle',8,'🌀CMF▲'),('CMF_Bear','#FF5722','circle',8,'🌀CMF▼')]:_sig_marker(fig,dc,sn,5,mfc,clr,sym,sz,lbl)
    # R6 Stoch
    slk=dc.get('SlowK',pd.Series(50,index=dc.index));sld=dc.get('SlowD',pd.Series(50,index=dc.index))
    fig.add_trace(go.Scatter(x=dc.index,y=slk,line=dict(color='#00BCD4',width=2),name="SlowK",hovertemplate="SlK:%{y:.1f}<br><span style='color:#94A3B8'>20↓ 과매도, 80↑ 과매수</span><extra></extra>"),row=6,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=sld,line=dict(color='#FF9800',width=1.5,dash='dot'),hoverinfo='skip',showlegend=False),row=6,col=1)
    fig.add_hrect(y0=80,y1=100,fillcolor="rgba(239,68,68,.08)",line_width=0,row=6,col=1);fig.add_hrect(y0=0,y1=20,fillcolor="rgba(16,185,129,.08)",line_width=0,row=6,col=1)
    for y_,c_,d_ in [(80,'#FF5252','dash'),(20,'#4FC3F7','dash'),(50,'#475569','dot')]:fig.add_hline(y=y_,line_dash=d_,line_color=c_,line_width=1,row=6,col=1)
    for sn,clr,sym,sz,lbl in [('StochSlow_Cross_Buy','#00E676','triangle-up',12,'🔄StSl▲'),('StochSlow_Cross_Sell','#FF1744','triangle-down',12,'🔄StSl▼'),('Stoch_Oversold','#69F0AE','square',6,'🟢StOS'),('Stoch_Overbought','#FF5252','square',6,'🔴StOB')]:_sig_marker(fig,dc,sn,6,slk,clr,sym,sz,lbl)
    # R7 SqMom
    sqm=dc.get('Squeeze_Momentum',pd.Series(0,index=dc.index));sqr=dc.get('Squeeze_Mom_Rising',pd.Series(False,index=dc.index)).fillna(False);sqp=dc.get('Squeeze_Mom_Positive',pd.Series(False,index=dc.index)).fillna(False);sqo=dc.get('Squeeze_On',pd.Series(False,index=dc.index)).fillna(False)
    sqc=np.where(sqp&sqr,'#00E676',np.where(sqp&~sqr,'#69F0AE',np.where(~sqp&sqr,'#FF8A80','#FF1744')))
    fig.add_trace(go.Bar(x=dc.index,y=sqm,marker_color=sqc.tolist(),name="SqMom",opacity=.85,hovertemplate="SqMom:%{y:.3f}<br><span style='color:#94A3B8'>스퀴즈 에너지 방향</span><extra></extra>"),row=7,col=1)
    fig.add_hline(y=0,line_color="#475569",line_width=1,row=7,col=1)
    if sqo.any():
        smn=float(sqm.min()) if len(sqm)>0 else -0.1;dy=smn*1.1 if smn<0 else -0.05
        fig.add_trace(go.Scatter(x=dc.index[sqo],y=[dy]*int(sqo.sum()),mode='markers',marker=dict(symbol='circle',size=5,color='#000',line=dict(width=1,color='#FFC107'),opacity=.9),name='⚫SqON',hovertemplate="⚡Squeeze ON<br>%{x|%Y-%m-%d}<extra></extra>"),row=7,col=1)
    for sn,clr,sym,sz,lbl in [('Squeeze_Fire_Buy','#00FFFF','star-diamond',14,'💥SqFire▲'),('Squeeze_Fire_Sell','#FF6600','star-diamond',14,'🧨SqFire▼'),('Squeeze_Mom_Cross_Up','#00E676','diamond',10,'💥SqMom▲'),('Squeeze_Mom_Cross_Down','#FF1744','diamond',10,'💥SqMom▼')]:_sig_marker(fig,dc,sn,7,sqm,clr,sym,sz,lbl)
    # R8 Ensemble
    if 'Ensemble_Score' in dc.columns:
        es=dc['Ensemble_Score'];colors=np.where(es>=30,SOFT_GREEN,np.where(es>=10,'#A7E7CF',np.where(es<=-30,SOFT_RED,np.where(es<=-10,'#F6C2C2',SOFT_AMBER))))
        cmd=[dc.get(f'CM_{cm}_EffScore',pd.Series(0,index=dc.index)).values for cm in COMMITTEE_NAMES];cma=np.column_stack(cmd) if cmd else np.zeros((len(dc),5))
        jgv=dc.get('Trade_Judgment',pd.Series('N/A',index=dc.index)).values;cfv=dc.get('Judgment_Confidence',pd.Series(0,index=dc.index)).values
        ctxv=dc.get('Market_Context',pd.Series(0,index=dc.index)).values;bav=dc.get('Buy_Agree',pd.Series(0,index=dc.index)).values;sav=dc.get('Sell_Agree',pd.Series(0,index=dc.index)).values
        fig.add_trace(go.Bar(x=dc.index,y=es,marker_color=colors.tolist(),name="Ensemble",opacity=.85,
            customdata=np.column_stack([jgv,cfv,bav,sav,cma[:,0],cma[:,1],cma[:,2],cma[:,3],cma[:,4],[CTX_KOR.get(int(c),'-') for c in ctxv]]),
            hovertemplate="<b>%{customdata[0]}</b> (%{customdata[1]:.0f}%) ES:%{y:+.1f}<br>B%{customdata[2]}:S%{customdata[3]} [%{customdata[9]}]<br>📈%{customdata[4]:+.0f} 🔥%{customdata[5]:+.0f} 💰%{customdata[6]:+.0f}<br>🏗️%{customdata[7]:+.0f} ⏳%{customdata[8]:+.0f}<extra></extra>"),row=8,col=1)
        fig.add_hline(y=0,line_color="#475569",line_width=1,row=8,col=1);fig.add_hline(y=JT.STRONG_BUY_TH,line_dash='dot',line_color='rgba(0,230,118,.3)',line_width=1,row=8,col=1);fig.add_hline(y=JT.STRONG_SELL_TH,line_dash='dot',line_color='rgba(255,23,68,.3)',line_width=1,row=8,col=1)
        ctx_colors={CTX_EXTREME_OS:'rgba(0,230,118,.06)',CTX_EXTREME_OB:'rgba(255,23,68,.06)',CTX_ACCUMULATION:'rgba(0,188,212,.06)',CTX_DISTRIBUTION:'rgba(255,87,34,.06)',CTX_STRONG_UP:'rgba(0,230,118,.03)',CTX_STRONG_DN:'rgba(255,23,68,.03)',CTX_BOTTOMING:'rgba(0,188,212,.04)',CTX_TOPPING:'rgba(255,152,0,.04)'}
        pc=-1;ss_=0;cvs=dc.get('Market_Context',pd.Series(0,index=dc.index)).values
        for ci in range(len(dc)):
            cur=int(cvs[ci])
            if cur!=pc:
                if pc in ctx_colors and ci>ss_:fig.add_vrect(x0=dc.index[ss_],x1=dc.index[ci-1],fillcolor=ctx_colors[pc],line_width=0,row=8,col=1)
                ss_=ci;pc=cur
        if pc in ctx_colors:fig.add_vrect(x0=dc.index[ss_],x1=dc.index[-1],fillcolor=ctx_colors[pc],line_width=0,row=8,col=1)
    chart_height = 1360 if len(dc) <= 126 else 1460
    fig.update_layout(template="plotly_dark",paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",margin=dict(l=2,r=2,t=40,b=2),height=chart_height,showlegend=True,hovermode="closest",legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="center",x=.5,font=dict(size=8,color='#94A3B8'),bgcolor='rgba(0,0,0,0)'))
    for i in range(1,9):fig.update_layout(**{(f'yaxis{i}' if i>1 else 'yaxis'):dict(gridcolor='rgba(51,65,85,.3)',tickfont=dict(size=9,color='#64748B'))})
    fig.update_yaxes(range=[-50,50],row=5,col=1);fig.update_yaxes(range=[0,100],row=6,col=1)
    ad=pd.date_range(start=dc.index[0],end=dc.index[-1],freq='D');nt=ad.difference(dc.index.normalize())
    fig.update_xaxes(rangeslider_visible=False,rangebreaks=[dict(values=nt.tolist())],gridcolor='rgba(51,65,85,.3)',tickfont=dict(size=9,color='#64748B'))
    for ann in fig['layout']['annotations']:ann['font']=dict(size=11,color='#94A3B8',family='Pretendard')
    return fig

def build_metadata(dc,ticker):
    lat=dc.iloc[-1];prev=dc.iloc[-2] if len(dc)>=2 else lat;pc=lat['Close']-prev['Close'];pp=pc/(prev['Close']+1e-10)*100
    LN=['Trend','Momentum','Candle','BB','Volume','MF','Pattern','Combined','Leading','Lagging']
    bl={n:_sf(lat.get(f'BL_{n}',0)) for n in LN};sl={n:_sf(lat.get(f'SL_{n}',0)) for n in LN}
    acs=[]
    for cn,ccfg in COMBINED_SCAN_REGISTRY.items():
        if cn in dc.columns and dc[cn].tail(5).any():
            ld=dc[cn].tail(5)[dc[cn].tail(5)].index[-1];acs.append({'name':ccfg['name'],'kor':ccfg['kor'],'dir':ccfg['dir'],'tier':ccfg['tier'],'icon':ccfg['icon'],'color':ccfg['color'],'win':ccfg['win'],'date':ld.strftime('%m/%d'),'is_today':(dc.index[-1]-ld).days==0,'days_ago':(dc.index[-1]-ld).days})
    acs.sort(key=lambda x:(x['tier'],x['days_ago']))
    recent=[]
    for ir,row in dc.tail(15).iterrows():
        ds=ir.strftime('%m/%d')
        for col,cfg in SIGNAL_REGISTRY.items():
            if col in dc.columns and row.get(col,False):recent.append((cfg['icon'],cfg['kor'],ds,cfg['dir'],False))
        for col,cfg in COMBINED_SCAN_REGISTRY.items():
            if col in dc.columns and row.get(col,False):recent.append((cfg['icon'],cfg['kor'],ds,cfg['dir'],True))
    rg=int(lat.get('Regime',0));rl={2:'STRONG BULL 🟢🟢',1:'BULL 🟢',0:'NEUTRAL ⚪',-1:'BEAR 🔴',-2:'STRONG BEAR 🔴🔴'}.get(rg,'N/A')
    committee={}
    for cm in COMMITTEE_NAMES:vv=int(_sf(lat.get(f'CM_{cm}_Vote',0)));committee[cm]={'score':_sf(lat.get(f'CM_{cm}_EffScore',0)),'conviction':_sf(lat.get(f'CM_{cm}_EffConv',0)),'vote':'BUY' if vv==1 else('SELL' if vv==-1 else('ABSTAIN' if vv==-99 else 'NEUTRAL')),'vote_int':vv}
    ctx_code=int(_sf(lat.get('Market_Context',0)))
    return {'ticker':ticker.upper(),'price':_sf(lat['Close']),'price_change':pc,'price_change_pct':pp,'volume':_sf(lat['Volume']),'avg_volume':_sf(dc['Volume'].rolling(20).mean().iloc[-1]),
        'wt1':_sf(lat.get('WT1')),'rsi':_sf(lat.get('RSI'),50),'mfi':_sf(lat.get('MFI'),50),'stochk':_sf(lat.get('StochK'),50),'adx':_sf(lat.get('ADX')),'atr':_sf(lat.get('ATR')),'atr_pct':_sf(lat.get('ATR'))/(max(_sf(lat['Close']),0.01))*100,
        'macd_hist':_sf(lat.get('MACD_Hist')),'cmf':_sf(lat.get('CMF')),'composite_accel':_sf(lat.get('Composite_Accel')),'rs_ratio':_sf(lat.get('RS_Ratio'),1),
        'regime':rg,'regime_label':rl,'regime_score':_sf(lat.get('Regime_Score')),'last_date':dc.index[-1].strftime('%Y-%m-%d'),'squeeze_on':bool(lat.get('Squeeze_On',False)),
        'buy_total':_sf(lat.get('Buy_Total')),'sell_total':_sf(lat.get('Sell_Total')),'buy_active':int(_sf(lat.get('Buy_Active_Layers'))),'sell_active':int(_sf(lat.get('Sell_Active_Layers'))),
        'buy_layers':bl,'sell_layers':sl,'judgment':str(lat.get('Trade_Judgment','NEUTRAL')),'confidence':_sf(lat.get('Judgment_Confidence')),
        'ensemble_score':_sf(lat.get('Ensemble_Score')),'prediction_boost':_sf(lat.get('Prediction_Boost')),
        'leading_verdict':str(lat.get('Leading_Verdict','중립')),'lagging_verdict':str(lat.get('Lagging_Verdict','비추세/횡보')),
        'setup_pressure_buy':_sf(lat.get('Setup_Pressure_Buy')),'setup_pressure_sell':_sf(lat.get('Setup_Pressure_Sell')),
        'utbot_dir':int(_sf(lat.get('UTBot_Dir'))),'hma_rising':bool(lat.get('HMA_Rising',False)),'slowk':_sf(lat.get('SlowK'),50),'squeeze_mom':_sf(lat.get('Squeeze_Momentum')),
        'context':ctx_code,'context_label':CTX_KOR.get(ctx_code,'기본'),'committee':committee,
        'buy_agree':int(_sf(lat.get('Buy_Agree'))),'sell_agree':int(_sf(lat.get('Sell_Agree'))),'veto_flags':str(lat.get('Veto_Flags','')),'reversal_synergy':_sf(lat.get('Reversal_Synergy')),
        'judgment_reason':str(lat.get('Judgment_Reason','')),'judgment_detail':str(lat.get('Judgment_Detail','')),'action_label':str(lat.get('Action_Label','')),
        'ma50':_sf(lat.get('MA50')),'ma200':_sf(lat.get('MA200')),'vp_poc':_sf(lat.get('VP_POC')),'vp_vah':_sf(lat.get('VP_VAH')),'vp_val':_sf(lat.get('VP_VAL')),
        'percent_b':_sf(lat.get('Percent_B'),0.5),'rsi_mfi':_sf(lat.get('RSI_MFI')),'bb_up':_sf(lat.get('BB_Up')),'bb_low':_sf(lat.get('BB_Low')),
        'ema8':_sf(lat.get('EMA8')),'ema21':_sf(lat.get('EMA21')),'obv_trend':'rising' if _sf(lat.get('OBV'))>_sf(dc['OBV'].rolling(20).mean().iloc[-1]) else 'falling',
        'obv_slope':_sf(lat.get('OBV_Slope')),'price_slope_5':_sf(lat.get('Price_Slope_5')),'volume_ratio_20':_sf(lat.get('Volume_Ratio_20'),1),
        'vp_long_rr':_sf(lat.get('VP_Long_RR'),1),'vp_short_rr':_sf(lat.get('VP_Short_RR'),1),'contrast_notes':str(lat.get('Contrast_Notes','')),
        'smart_money_bearish_div':bool(lat.get('Smart_Money_Bearish_Div',False)),'smart_money_bullish_div':bool(lat.get('Smart_Money_Bullish_Div',False)),
        'blowoff_top_hard':bool(lat.get('Blowoff_Top_Hard',False)),
        'combined_scans':acs,'recent_signals':recent,
        'high_52w':float(dc['High'].max()),'low_52w':float(dc['Low'].min()),
        'ma50_dist':round((_sf(lat['Close'])-_sf(lat.get('MA50',_sf(lat['Close']))))/_sf(lat['Close'])*100,2) if _sf(lat.get('MA50')) else 0,
        'ma200_dist':round((_sf(lat['Close'])-_sf(lat.get('MA200',_sf(lat['Close']))))/_sf(lat['Close'])*100,2) if _sf(lat.get('MA200')) else 0}

# ━━━ UI ━━━
