import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.signal import find_peaks
from config import *
from utils import _sf
from localization import (
    explain_signal_meaning,
    localize_action_label,
    localize_combo,
    localize_context_label,
    localize_judgment_label,
    localize_legend_name,
    localize_pattern_name,
    localize_pattern_state,
    localize_regime_label,
    localize_signal,
    localize_subplot_title,
    translate_chart_text,
)
from domain import AnalysisViewModel
from strategy import build_strategy_payload
from theme import PLOTLY_FONT_FAMILY

SOFT_GREEN = '#63D9A2'
SOFT_GREEN_FILL = 'rgba(99,217,162,.8)'
SOFT_RED = '#FF8F96'
SOFT_RED_FILL = 'rgba(255,143,150,.8)'
SOFT_AMBER = '#F6C35E'

def _build_candle_hover(dc):
    n=len(dc)
    bar_buy=[[] for _ in range(n)];bar_sell=[[] for _ in range(n)];bar_neutral=[[] for _ in range(n)]
    bar_cs=[[] for _ in range(n)];bar_sb=[[] for _ in range(n)];bar_ss=[[] for _ in range(n)]
    for sn,cfg in SIGNAL_REGISTRY.items():
        if sn not in dc.columns:continue
        vals=dc[sn].fillna(False).values
        if not vals.any():continue
        label_text,desc=localize_signal(sn,cfg.get('kor'),cfg.get('desc'));ix=np.flatnonzero(vals);lbl=f"{cfg['icon']}{label_text}";isb=sn in STRONG_BUY_SIGS;iss=sn in STRONG_SELL_SIGS
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
        label_text,desc=localize_combo(cn,ccfg.get('kor'),ccfg.get('desc'));ix=np.flatnonzero(vals);lbl=f"{ccfg['icon']}{label_text}"
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

def _add_volume_profile_overlay(fig,dc,default_visible='legendonly'):
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
    first_profile=True
    for bi,pv in enumerate(prof):
        if pv<=0:continue
        f=float(pv/vmax);alpha=min(.30,max(.08,.08+.22*f))
        x0=x_right-max_width*f;x1=x_right;y0=float(edges[bi]);y1=float(edges[bi+1])
        fig.add_trace(go.Scatter(
            x=[x0,x1,x1,x0,x0],
            y=[y0,y0,y1,y1,y0],
            mode='lines',
            line=dict(width=0,color='rgba(0,0,0,0)'),
            fill='toself',
            fillcolor=f'rgba(99,102,241,{alpha})',
            name='VP Overlay',
            legendgroup='vp_overlay',
            hoverinfo='skip',
            showlegend=first_profile,
            visible=default_visible
        ),row=1,col=1)
        first_profile=False
    vp_colors=[('VP_POC','#A5B4FC','dot','POC'),('VP_VAH','#60A5FA','dash','VAH'),('VP_VAL',SOFT_GREEN,'dash','VAL')]
    for col,clr,sty,label in vp_colors:
        if col in dc.columns:
            val=float(dc[col].iloc[-1])
            if np.isfinite(val):
                fig.add_trace(go.Scatter(x=[dc.index[0],x_right],y=[val,val],mode='lines',line=dict(color=clr,width=1.5,dash=sty),name=label,legendgroup='vp_overlay',hoverinfo='skip',showlegend=False,visible=default_visible),row=1,col=1)
    fig.add_trace(go.Scatter(x=[x_right],y=[dc['Close'].iloc[-1]],mode='markers',marker=dict(size=.1,color='rgba(0,0,0,0)'),hoverinfo='skip',showlegend=False),row=1,col=1)
    fig.add_trace(go.Scatter(x=[x_right],y=[high],mode='text',text=['VP'],textfont=dict(size=9,color='#94A3B8'),name='VP Label',legendgroup='vp_overlay',hoverinfo='skip',showlegend=False,visible=default_visible),row=1,col=1)

def _add_fibonacci_overlay(fig,dc,default_visible='legendonly'):
    if dc.empty:
        return
    x_left=dc.index[0]
    x_right=dc.index[-1]+pd.Timedelta(days=3)
    fib_specs=[
        ('Fib_382','#60A5FA','dash','Fib 38.2%'),
        ('Fib_50','#A78BFA','dot','Fib 50%'),
        ('Fib_618','#F59E0B','solid','Fib 61.8%'),
        ('Fib_Ext_1618_Up','#F97316','dash','Fib 161.8% Up'),
        ('Fib_Ext_1618_Down','#14B8A6','dash','Fib 161.8% Down'),
    ]
    first=True
    for col,color,dash,label in fib_specs:
        if col not in dc.columns:
            continue
        val=float(dc[col].iloc[-1])
        if not np.isfinite(val) or val <= 0:
            continue
        fig.add_trace(go.Scatter(
            x=[x_left,x_right],
            y=[val,val],
            mode='lines',
            line=dict(color=color,width=1.3,dash=dash),
            name='Fib Overlay' if first else label,
            legendgroup='fib_overlay',
            hovertemplate=f"{label}: %{{y:.2f}}<extra></extra>",
            showlegend=first,
            visible=default_visible,
        ),row=1,col=1)
        first=False

def _sig_marker(fig,dc,sn,row,y,clr,sym,sz,lbl,legendgroup=None,showlegend=False,visible=True,legend_name=None):
    reg=SIGNAL_REGISTRY.get(sn) or COMBINED_SCAN_REGISTRY.get(sn,{})
    if sn not in dc.columns:return
    mask=dc[sn].fillna(False)
    if not mask.any():return
    sr=dc[mask];yv=y[mask] if isinstance(y,pd.Series) else pd.Series(y,index=dc.index)[mask]
    valid=yv.notna()
    if not valid.any():return
    sr=sr[valid];yv=yv[valid]
    is_combo=sn in COMBINED_SCAN_REGISTRY
    if is_combo:
        kor,desc=localize_combo(sn,reg.get('kor'),reg.get('desc'))
    else:
        kor,desc=localize_signal(sn,reg.get('kor'),reg.get('desc'))
    meaning=explain_signal_meaning(sn, desc, is_combo=is_combo)
    dir_text='매수 신호' if reg.get('dir')=='buy' else ('매도 신호' if reg.get('dir')=='sell' else '상태 / 주의 신호')
    hover_lines=[f"<b>{legend_name or lbl}</b>"]
    if kor:
        hover_lines.append(f"신호: {kor}")
    hover_lines.append(f"<span style='color:#E2E8F0'>{dir_text}</span>")
    if meaning:
        hover_lines.append(f"<span style='color:#94A3B8'>{meaning}</span>")
    if desc and desc != meaning:
        hover_lines.append(f"<span style='color:#64748B'>조건: {desc}</span>")
    hover_lines.append("%{x|%Y-%m-%d}")
    ht="<br>".join(hover_lines)+"<extra></extra>"
    if row==1 and legendgroup is None and visible is True:
        visible='legendonly'
    fig.add_trace(go.Scatter(x=sr.index,y=yv,mode='markers',marker=dict(symbol=sym,size=sz,color=clr,line=dict(width=1.5,color='#FFF'),opacity=.95),name=legend_name or lbl,legendgroup=legendgroup,showlegend=showlegend,visible=visible,hovertemplate=ht),row=row,col=1)


def _indicator_hover(label, value_line, guide, raw_line=None, extra_line=None):
    parts=[f"<b>{label}</b>", value_line]
    if raw_line:
        parts.append(raw_line)
    if extra_line:
        parts.append(extra_line)
    if guide:
        parts.append(f"<span style='color:#94A3B8'>{guide}</span>")
    return "<br>".join(parts)+"<extra></extra>"


def _state_marker(fig,dc,mask,row,y,clr,sym,sz,lbl,guide,legendgroup=None,showlegend=False,visible=True):
    mask_series=mask if isinstance(mask,pd.Series) else pd.Series(mask,index=dc.index)
    mask_series=mask_series.fillna(False).astype(bool)
    if not mask_series.any():
        return
    yv=y[mask_series] if isinstance(y,pd.Series) else pd.Series(y,index=dc.index)[mask_series]
    valid=yv.notna()
    if not valid.any():
        return
    yv=yv[valid]
    sr=dc.loc[yv.index]
    texts=[f"<b>{lbl}</b><br><span style='color:#94A3B8'>{guide}</span><br>{ts.strftime('%Y-%m-%d')}<extra></extra>" for ts in sr.index]
    fig.add_trace(go.Scatter(x=sr.index,y=yv,mode='markers',marker=dict(symbol=sym,size=sz,color=clr,line=dict(width=1.2,color='#FFF'),opacity=.92),name=lbl,legendgroup=legendgroup,showlegend=showlegend,visible=visible,text=texts,hovertemplate="%{text}"),row=row,col=1)

def _bool_weight(series, weight, index):
    base=series if isinstance(series,pd.Series) else pd.Series(series,index=index)
    return base.fillna(False).astype(np.int16)*weight

def _signed_state(values, weak=5.0, strong=20.0, pos='상승 우위', neg='하락 우위', neutral='중립 / 균형', strong_pos='강한 상승 우위', strong_neg='강한 하락 우위'):
    arr=pd.Series(values).replace([np.inf,-np.inf],np.nan).fillna(0).astype(float).values
    out=np.full(len(arr), neutral, dtype=object)
    out[arr>=weak]=pos
    out[arr>=strong]=strong_pos
    out[arr<=-weak]=neg
    out[arr<=-strong]=strong_neg
    return out

def _oscillator_state(values, oversold=30.0, overbought=70.0, extreme_oversold=20.0, extreme_overbought=80.0, oversold_text='약세권 / 눌림 구간', neutral='중립권', overbought_text='강세권 / 과열 접근', extreme_oversold_text='과매도권 반등 후보', extreme_overbought_text='과열권 숨고르기 경계'):
    arr=pd.Series(values).replace([np.inf,-np.inf],np.nan).fillna(50).astype(float).values
    out=np.full(len(arr), neutral, dtype=object)
    out[arr<=oversold]=oversold_text
    out[arr>=overbought]=overbought_text
    out[arr<=extreme_oversold]=extreme_oversold_text
    out[arr>=extreme_overbought]=extreme_overbought_text
    return out

def _macd_state(macd_line, macd_hist):
    line=pd.Series(macd_line).replace([np.inf,-np.inf],np.nan).fillna(0).astype(float).values
    hist=pd.Series(macd_hist).replace([np.inf,-np.inf],np.nan).fillna(0).astype(float).values
    out=np.full(len(line), '중립 / 전환 관찰 구간', dtype=object)
    out[(line>0)&(hist>=0)]='상승 모멘텀 강화'
    out[(line>0)&(hist<0)]='상승 추세 유지 but 탄력 둔화'
    out[(line<0)&(hist<=0)]='하락 모멘텀 강화'
    out[(line<0)&(hist>0)]='하락 둔화 / 반등 시도'
    return out

def _adx_state(adx, plus_di, minus_di):
    ax=pd.Series(adx).replace([np.inf,-np.inf],np.nan).fillna(0).astype(float).values
    pdm=pd.Series(plus_di).replace([np.inf,-np.inf],np.nan).fillna(0).astype(float).values
    mdm=pd.Series(minus_di).replace([np.inf,-np.inf],np.nan).fillna(0).astype(float).values
    out=np.full(len(ax), '추세 약함 / 횡보 가능성', dtype=object)
    out[(ax>=20)&(pdm>=mdm)]='상승 추세 형성 중'
    out[(ax>=20)&(mdm>pdm)]='하락 추세 형성 중'
    out[(ax>=25)&(pdm>=mdm)]='상승 추세 강화'
    out[(ax>=25)&(mdm>pdm)]='하락 추세 강화'
    return out

def _squeeze_state(values, squeeze_on, positive, rising):
    val=pd.Series(values).replace([np.inf,-np.inf],np.nan).fillna(0).astype(float).values
    sq=pd.Series(squeeze_on).fillna(False).astype(bool).values
    pos=pd.Series(positive).fillna(False).astype(bool).values
    up=pd.Series(rising).fillna(False).astype(bool).values
    out=np.full(len(val), '에너지 균형 / 방향 대기', dtype=object)
    out[sq]='압축 진행 중, 방향 선택 대기'
    out[(~sq)&pos&up]='상방 에너지 강화'
    out[(~sq)&pos&(~up)]='상방 우위 but 탄력 둔화'
    out[(~sq)&(~pos)&up]='하락 압력 둔화 / 반등 시도'
    out[(~sq)&(~pos)&(~up)]='하방 에너지 강화'
    return out

def _volatility_state(values):
    arr=pd.Series(values).replace([np.inf,-np.inf],np.nan).fillna(0).astype(float).values
    out=np.full(len(arr), '보통 변동성', dtype=object)
    out[arr>=2.5]='변동성 확대'
    out[arr>=4.0]='매우 큰 변동성 / 손절 관리 중요'
    out[arr<=1.0]='조용한 구간 / 에너지 축적 가능성'
    return out

def _rs_state(values):
    arr=pd.Series(values).replace([np.inf,-np.inf],np.nan).fillna(1).astype(float).values
    out=np.full(len(arr), '시장과 비슷한 상대강도', dtype=object)
    out[arr>=1.00]='시장 대비 상대강도 우위'
    out[arr>=1.05]='강한 리더주 성격'
    out[arr<=0.98]='시장 대비 약한 편'
    out[arr<=0.95]='뚜렷한 언더퍼폼 구간'
    return out

def _level_state(values, near=5.0, strong=20.0, above='기준선 위 우위', below='기준선 아래 약세', near_text='기준선 부근 / 방향 대기', strong_above='기준선 위 강한 우위', strong_below='기준선 아래 강한 약세'):
    arr=pd.Series(values).replace([np.inf,-np.inf],np.nan).fillna(0).astype(float).values
    out=np.full(len(arr), near_text, dtype=object)
    out[arr>near]=above
    out[arr>=strong]=strong_above
    out[arr<-near]=below
    out[arr<=-strong]=strong_below
    return out

def _trendline_atr(dc):
    atr=dc.get('ATR',pd.Series(index=dc.index,dtype=float)).astype(float).replace([np.inf,-np.inf],np.nan)
    fallback=((dc['High']-dc['Low']).replace([np.inf,-np.inf],np.nan)).rolling(14,min_periods=1).mean()
    atr=atr.fillna(fallback)
    atr_med=float(atr.median()) if len(atr)>0 else 0.0
    if not np.isfinite(atr_med) or atr_med<=0:
        atr_med=max(float((dc['Close'].astype(float).median() if 'Close' in dc.columns else 1.0)*0.01),1e-6)
    return atr.fillna(atr_med).clip(lower=max(atr_med*0.15,1e-6))

def _line_values(length,start_idx,start_price,end_idx,end_price):
    xs=np.arange(length,dtype=float)
    slope=(float(end_price)-float(start_price))/max(float(end_idx-start_idx),1.0)
    return float(start_price)+(xs-float(start_idx))*slope

def _score_trendline(length,start_idx,end_idx,intrusion_ratio):
    if length<=1:return 0.0
    recency=float(end_idx)/float(length-1)
    span=float(end_idx-start_idx)/float(length-1)
    cleanliness=max(0.0,1.0-min(float(intrusion_ratio)/0.2,1.0))
    return recency*0.45+span*0.35+cleanliness*0.20

def _collect_trendline_candidates(dc,column,kind):
    if dc.empty or column not in dc.columns:return []
    values=dc[column].astype(float).values
    if len(values)<12:return []
    atr=_trendline_atr(dc)
    atr_values=atr.values.astype(float)
    distance=max(5,len(dc)//18)
    prominence=max(float(np.nanmedian(atr_values))*0.35,float(np.nanmedian(np.abs(values)))*0.001,1e-6)
    series=values if kind=='resistance' else -values
    pivots,_=find_peaks(series,distance=distance,prominence=prominence)
    if len(pivots)<2:return []
    candidates=[]
    for left_pos in range(len(pivots)-1):
        start_idx=int(pivots[left_pos]);start_price=float(values[start_idx])
        for right_pos in range(left_pos+1,len(pivots)):
            end_idx=int(pivots[right_pos]);end_price=float(values[end_idx])
            if end_idx-start_idx<distance:continue
            if kind=='support' and end_price<=start_price:continue
            if kind=='resistance' and end_price>=start_price:continue
            line_vals=_line_values(len(dc),start_idx,start_price,end_idx,end_price)
            window=slice(start_idx,end_idx+1)
            line_window=line_vals[window]
            tol=atr_values[window]*0.35
            price_window=values[window]
            if kind=='support':
                intrusions=price_window<(line_window-tol)
            else:
                intrusions=price_window>(line_window+tol)
            intrusion_ratio=float(np.mean(intrusions)) if len(price_window)>0 else 1.0
            if intrusion_ratio>0.20:continue
            projected=float(line_vals[-1]);current_tol=float(atr_values[-1]*0.35)
            current_close=float(dc['Close'].iloc[-1])
            is_active=current_close>=projected-current_tol if kind=='support' else current_close<=projected+current_tol
            candidates.append({
                'kind':kind,
                'start_idx':start_idx,
                'end_idx':end_idx,
                'start_price':start_price,
                'end_price':end_price,
                'line_values':line_vals,
                'intrusion_ratio':intrusion_ratio,
                'projected_price':projected,
                'active':bool(is_active),
                'score':_score_trendline(len(dc),start_idx,end_idx,intrusion_ratio),
            })
    return candidates

def _select_trendlines(candidates,limit,spacing):
    selected=[]
    for cand in sorted(candidates,key=lambda x:(x['score'],x['end_idx']),reverse=True):
        too_close=False
        for chosen in selected:
            if cand['start_idx']==chosen['start_idx'] or cand['end_idx']==chosen['end_idx']:
                too_close=True
                break
            if abs(cand['projected_price']-chosen['projected_price'])<=spacing:
                too_close=True
                break
        if too_close:continue
        selected.append(cand)
        if len(selected)>=limit:break
    return selected

def _compute_trendlines(dc,max_per_side=2):
    atr=_trendline_atr(dc)
    spacing=max(float(np.nanmedian(atr.values))*0.5,1e-6)
    supports=_select_trendlines(_collect_trendline_candidates(dc,'Low','support'),max_per_side,spacing)
    resistances=_select_trendlines(_collect_trendline_candidates(dc,'High','resistance'),max_per_side,spacing)
    for line in supports:
        window=slice(line['start_idx'],line['end_idx']+1)
        base_window=line['line_values'][window]
        channel_offset=float(np.max(dc['High'].astype(float).values[window]-base_window))
        if np.isfinite(channel_offset) and channel_offset>spacing:
            line['channel_offset']=channel_offset
            line['channel_values']=line['line_values']+channel_offset
            line['channel_projected_price']=line['projected_price']+channel_offset
    for line in resistances:
        window=slice(line['start_idx'],line['end_idx']+1)
        base_window=line['line_values'][window]
        channel_offset=float(np.min(dc['Low'].astype(float).values[window]-base_window))
        if np.isfinite(channel_offset) and abs(channel_offset)>spacing:
            line['channel_offset']=channel_offset
            line['channel_values']=line['line_values']+channel_offset
            line['channel_projected_price']=line['projected_price']+channel_offset
    return supports,resistances

def _trendline_hover(line,label):
    kind='지지 추세선' if line['kind']=='support' else '저항 추세선'
    start_date=line['start_date'].strftime('%Y-%m-%d')
    end_date=line['end_date'].strftime('%Y-%m-%d')
    channel_text=f"<br>채널 예상가: {line['channel_projected_price']:.2f}" if 'channel_projected_price' in line else ''
    return (
        f"<b>{translate_chart_text(label)}</b><br>"
        f"유형: {kind}<br>"
        f"기준점: {start_date} ({line['start_price']:.2f}) -> {end_date} ({line['end_price']:.2f})<br>"
        f"현재 값: %{{y:.2f}}<br>"
        f"최종 예상가: {line['projected_price']:.2f}{channel_text}<extra></extra>"
    )

def _overlay_hover_x(dc,slot=0):
    return dc.index[-1]+pd.Timedelta(days=5+slot)

def _add_overlay_hover_anchor(fig,x,y,hovertemplate,legendgroup,visible,color,row=1,col=1):
    fig.add_trace(go.Scatter(
        x=[x],
        y=[y],
        mode='markers',
        marker=dict(symbol='circle-open',size=9,color='rgba(0,0,0,0)',line=dict(width=1,color=color)),
        name='',
        legendgroup=legendgroup,
        showlegend=False,
        visible=visible,
        hovertemplate=hovertemplate,
    ),row=row,col=col)

def _add_trendline_overlays(fig,dc,max_per_side=2,default_visible='legendonly'):
    supports,resistances=_compute_trendlines(dc,max_per_side=max_per_side)
    palette={
        'support':['#2DD4BF','#6EE7B7'],
        'resistance':['#FB7185','#FDBA74'],
    }
    trend_legend_shown=False
    for idx,line in enumerate(supports,1):
        line['start_date']=dc.index[line['start_idx']]
        line['end_date']=dc.index[line['end_idx']]
        xs=dc.index[line['start_idx']:]
        ys=line['line_values'][line['start_idx']:]
        channel_color=palette['support'][min(idx-1,len(palette['support'])-1)]
        channel_dash='solid' if line['active'] else 'dot'
        if 'channel_values' in line:
            fig.add_trace(go.Scatter(
                x=xs,
                y=line['channel_values'][line['start_idx']:],
                mode='lines',
                line=dict(color=channel_color,width=1.3,dash='dash'),
                name='Trend Overlay',
                legendgroup='trend_overlay',
                showlegend=not trend_legend_shown,
                visible=default_visible,
                hoverinfo='skip'
            ),row=1,col=1)
            _add_overlay_hover_anchor(fig,_overlay_hover_x(dc,0),float(line['channel_projected_price']),_trendline_hover(line,f'Channel S{idx}'),'trend_overlay',default_visible,channel_color)
            trend_legend_shown=True
        fig.add_trace(go.Scatter(
            x=xs,
            y=ys,
            mode='lines',
            line=dict(color=channel_color,width=2,dash=channel_dash),
            name='Trend Overlay',
            legendgroup='trend_overlay',
            showlegend=not trend_legend_shown,
            visible=default_visible,
            hoverinfo='skip',
            fill='tonexty' if 'channel_values' in line else None,
            fillcolor='rgba(45,212,191,0.06)' if 'channel_values' in line else None
        ),row=1,col=1)
        _add_overlay_hover_anchor(fig,_overlay_hover_x(dc,1),float(line['projected_price']),_trendline_hover(line,f'Trendline S{idx}'),'trend_overlay',default_visible,channel_color)
        trend_legend_shown=True
    for idx,line in enumerate(resistances,1):
        line['start_date']=dc.index[line['start_idx']]
        line['end_date']=dc.index[line['end_idx']]
        xs=dc.index[line['start_idx']:]
        ys=line['line_values'][line['start_idx']:]
        channel_color=palette['resistance'][min(idx-1,len(palette['resistance'])-1)]
        channel_dash='solid' if line['active'] else 'dot'
        fig.add_trace(go.Scatter(
            x=xs,
            y=ys,
            mode='lines',
            line=dict(color=channel_color,width=2,dash=channel_dash),
            name='Trend Overlay',
            legendgroup='trend_overlay',
            showlegend=not trend_legend_shown,
            visible=default_visible,
            hoverinfo='skip'
        ),row=1,col=1)
        _add_overlay_hover_anchor(fig,_overlay_hover_x(dc,1),float(line['projected_price']),_trendline_hover(line,f'Trendline R{idx}'),'trend_overlay',default_visible,channel_color)
        trend_legend_shown=True
        if 'channel_values' in line:
            fig.add_trace(go.Scatter(
                x=xs,
                y=line['channel_values'][line['start_idx']:],
                mode='lines',
                line=dict(color=channel_color,width=1.3,dash='dash'),
                name='Trend Overlay',
                legendgroup='trend_overlay',
                showlegend=False,
                visible=default_visible,
                hoverinfo='skip',
                fill='tonexty',
                fillcolor='rgba(251,113,133,0.05)'
            ),row=1,col=1)
            _add_overlay_hover_anchor(fig,_overlay_hover_x(dc,0),float(line['channel_projected_price']),_trendline_hover(line,f'Channel R{idx}'),'trend_overlay',default_visible,channel_color)
    return supports,resistances

def _line_slope(line):
    return (float(line['end_price'])-float(line['start_price']))/max(float(line['end_idx']-line['start_idx']),1.0)

def _pattern_state(dc,upper_vals,lower_vals,start_idx,atr_values):
    close=dc['Close'].astype(float).values
    recent_start=max(int(start_idx)+1,len(dc)-3)
    for idx in range(recent_start,len(dc)):
        tol_now=float(atr_values[idx]*0.35)
        tol_prev=float(atr_values[idx-1]*0.35)
        if close[idx]>upper_vals[idx]+tol_now and close[idx-1]<=upper_vals[idx-1]+tol_prev:
            return 'BREAKOUT_UP',idx
        if close[idx]<lower_vals[idx]-tol_now and close[idx-1]>=lower_vals[idx-1]-tol_prev:
            return 'BREAKOUT_DOWN',idx
    last_idx=len(dc)-1
    tol_last=float(atr_values[last_idx]*0.35)
    if close[last_idx]<=upper_vals[last_idx]+tol_last and close[last_idx]>=lower_vals[last_idx]-tol_last:
        return 'FORMING',last_idx
    return None,None

def _detect_flag_pole(dc,start_idx,avg_slope,flat_threshold,atr_med):
    close=dc['Close'].astype(float).values
    best_name=None;best_bonus=0.0
    max_pole=min(20,int(start_idx))
    for pole_len in range(6,max_pole+1):
        pole_start=int(start_idx-pole_len)
        move=float(close[start_idx-1]-close[pole_start])
        strength=abs(move)/(atr_med+1e-10)
        if strength<3.0:continue
        pole_slope=move/max(float(pole_len),1.0)
        if move>0 and avg_slope<=flat_threshold*2 and abs(avg_slope)<=abs(pole_slope)*0.35:
            bonus=0.25+min(strength/12.0,0.45)
            if bonus>best_bonus:
                best_name='Bull Flag';best_bonus=bonus
        if move<0 and avg_slope>=-flat_threshold*2 and abs(avg_slope)<=abs(pole_slope)*0.35:
            bonus=0.25+min(strength/12.0,0.45)
            if bonus>best_bonus:
                best_name='Bear Flag';best_bonus=bonus
    return best_name,best_bonus

def _pattern_base_score(pattern_end_idx,dc_len,upper_intrusion,lower_intrusion,shape_score,freshness,pole_bonus=0.0):
    recency=1.0-min(max((dc_len-1-pattern_end_idx),0)/12.0,1.0)
    fit=max(0.0,1.0-min((upper_intrusion+lower_intrusion)/0.45,1.0))
    return recency*0.22+fit*0.26+shape_score*0.22+freshness*0.16+pole_bonus*0.14

def _build_pattern_candidate(dc,support,resistance,atr_values,atr_med):
    start_idx=max(int(support['start_idx']),int(resistance['start_idx']))
    if start_idx>=len(dc)-5:return None
    upper_vals=resistance['line_values']
    lower_vals=support['line_values']
    widths=upper_vals-lower_vals
    if np.any(widths[start_idx:]<=max(atr_med*0.2,1e-6)):return None
    upper_slope=_line_slope(resistance);lower_slope=_line_slope(support)
    span=max(len(dc)-1-start_idx,1)
    flat_threshold=max((atr_med/max(span,1))*0.15,atr_med*0.0025)
    parallel_threshold=max(max(abs(upper_slope),abs(lower_slope))*0.25,flat_threshold*1.5)
    width_start=float(widths[start_idx]);width_end=float(widths[-1])
    width_change=(width_end-width_start)/(abs(width_start)+1e-10)
    converging=width_change<=-0.18
    stable_width=abs(width_change)<=0.22
    window=slice(start_idx,len(dc))
    upper_intrusion=float(np.mean(dc['High'].astype(float).values[window]>(upper_vals[window]+atr_values[window]*0.35)))
    lower_intrusion=float(np.mean(dc['Low'].astype(float).values[window]<(lower_vals[window]-atr_values[window]*0.35)))
    if upper_intrusion>0.22 or lower_intrusion>0.22:return None
    state,trigger_idx=_pattern_state(dc,upper_vals,lower_vals,start_idx,atr_values)
    if state is None:return None
    freshness=1.0 if state=='FORMING' else max(0.55,1.0-((len(dc)-1-trigger_idx)/3.0)*0.25)
    upper_flat=abs(upper_slope)<=flat_threshold
    lower_flat=abs(lower_slope)<=flat_threshold
    same_direction=np.sign(upper_slope)==np.sign(lower_slope) and not upper_flat and not lower_flat
    name=None;shape_score=0.0;pole_bonus=0.0
    avg_slope=(upper_slope+lower_slope)/2.0
    if same_direction and stable_width and abs(upper_slope-lower_slope)<=parallel_threshold:
        if 5<=span<=20:
            flag_name,pole_bonus=_detect_flag_pole(dc,start_idx,avg_slope,flat_threshold,atr_med)
            if flag_name is not None:
                name=flag_name;shape_score=0.92
        if name is None:
            name='Channel';shape_score=0.82
    elif converging:
        if upper_slope<-flat_threshold and lower_slope>flat_threshold:
            name='Symmetrical Triangle';shape_score=0.90
        elif upper_flat and lower_slope>flat_threshold:
            name='Ascending Triangle';shape_score=0.94
        elif lower_flat and upper_slope<-flat_threshold:
            name='Descending Triangle';shape_score=0.94
        elif upper_slope>flat_threshold and lower_slope>flat_threshold and lower_slope>upper_slope+flat_threshold:
            name='Rising Wedge';shape_score=0.90
        elif upper_slope<-flat_threshold and lower_slope<-flat_threshold and abs(upper_slope)>abs(lower_slope)+flat_threshold:
            name='Falling Wedge';shape_score=0.90
    if name is None:return None
    score=_pattern_base_score(max(int(support['end_idx']),int(resistance['end_idx'])),len(dc),upper_intrusion,lower_intrusion,shape_score,freshness,pole_bonus)
    return {
        'name':name,
        'state':state,
        'start_idx':start_idx,
        'end_idx':len(dc)-1,
        'anchor_end_idx':max(int(support['end_idx']),int(resistance['end_idx'])),
        'upper_line':upper_vals,
        'lower_line':lower_vals,
        'upper_intrusion':upper_intrusion,
        'lower_intrusion':lower_intrusion,
        'score':score,
        'trigger_idx':trigger_idx,
        'upper_projected_price':float(upper_vals[-1]),
        'lower_projected_price':float(lower_vals[-1]),
    }

def _detect_active_pattern(dc):
    if dc.empty or len(dc)<24:return None
    atr=_trendline_atr(dc)
    atr_values=atr.values.astype(float)
    atr_med=max(float(np.nanmedian(atr_values)),1e-6)
    spacing=max(atr_med*0.35,1e-6)
    supports=_select_trendlines(_collect_trendline_candidates(dc,'Low','support'),6,spacing)
    resistances=_select_trendlines(_collect_trendline_candidates(dc,'High','resistance'),6,spacing)
    candidates=[]
    for support in supports:
        for resistance in resistances:
            candidate=_build_pattern_candidate(dc,support,resistance,atr_values,atr_med)
            if candidate is not None:candidates.append(candidate)
    if not candidates:return None
    best=sorted(candidates,key=lambda x:(x['score'],x['anchor_end_idx'],-(x['upper_intrusion']+x['lower_intrusion'])),reverse=True)[0]
    best['start_date']=dc.index[best['start_idx']]
    best['end_date']=dc.index[best['end_idx']]
    return best

def _pattern_style(pattern):
    bullish={'Ascending Triangle','Falling Wedge','Bull Flag'}
    bearish={'Descending Triangle','Rising Wedge','Bear Flag'}
    if pattern['state']=='BREAKOUT_UP':
        return '#34D399','rgba(52,211,153,0.08)'
    if pattern['state']=='BREAKOUT_DOWN':
        return '#FB7185','rgba(251,113,133,0.08)'
    if pattern['name'] in bullish:
        return '#6EE7B7','rgba(110,231,183,0.05)'
    if pattern['name'] in bearish:
        return '#FDA4AF','rgba(253,164,175,0.05)'
    return '#A5B4FC','rgba(165,180,252,0.05)'

def _pattern_hover(pattern,boundary_name):
    return (
        f"<b>{localize_pattern_name(pattern['name'])}</b><br>"
        f"경계: {'하단' if boundary_name=='Lower' else '상단'}<br>"
        f"상태: {localize_pattern_state(pattern['state'])}<br>"
        f"기간: {pattern['start_date'].strftime('%Y-%m-%d')} -> {pattern['end_date'].strftime('%Y-%m-%d')}<br>"
        f"상단 예상가: {pattern['upper_projected_price']:.2f}<br>"
        f"하단 예상가: {pattern['lower_projected_price']:.2f}<extra></extra>"
    )

def _add_pattern_overlay(fig,dc,pattern,default_visible='legendonly'):
    if pattern is None:return
    xs=dc.index[pattern['start_idx']:]
    lower_vals=pattern['lower_line'][pattern['start_idx']:]
    upper_vals=pattern['upper_line'][pattern['start_idx']:]
    edge_color,fill_color=_pattern_style(pattern)
    fig.add_trace(go.Scatter(
        x=xs,
        y=lower_vals,
        mode='lines',
        line=dict(color=edge_color,width=2,dash='dash'),
        name='Pattern Overlay',
        legendgroup='pattern_overlay',
        showlegend=False,
        visible=default_visible,
        hoverinfo='skip',
    ),row=1,col=1)
    fig.add_trace(go.Scatter(
        x=xs,
        y=upper_vals,
        mode='lines',
        line=dict(color=edge_color,width=2,dash='dash'),
        name='Pattern Overlay',
        legendgroup='pattern_overlay',
        showlegend=True,
        visible=default_visible,
        hoverinfo='skip',
        fill='tonexty',
        fillcolor=fill_color,
    ),row=1,col=1)
    _add_overlay_hover_anchor(
        fig,
        _overlay_hover_x(dc,2),
        float((pattern['upper_projected_price']+pattern['lower_projected_price'])/2.0),
        _pattern_hover(pattern,'Upper'),
        'pattern_overlay',
        default_visible,
        edge_color,
    )
    fig.add_trace(go.Scatter(
        x=[dc.index[-1]],
        y=[float(max(pattern['upper_projected_price'],pattern['lower_projected_price']))],
        mode='text',
        text=[f"{localize_pattern_name(pattern['name'])} · {localize_pattern_state(pattern['state'])}"],
        textposition='top right',
        textfont=dict(size=10,color=edge_color,family=PLOTLY_FONT_FAMILY),
        name='Pattern Overlay',
        legendgroup='pattern_overlay',
        showlegend=False,
        visible=default_visible,
        hoverinfo='skip'
    ),row=1,col=1)

def _build_chart_legacy(dc,ticker):
    mac={20:'#f1c40f',50:'#e74c3c',200:'#2ecc71'}
    fig=make_subplots(
        rows=17,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.017,
        row_heights=[.24,.04,.065,.065,.065,.065,.065,.05,.05,.05,.05,.055,.06,.06,.06,.08,.1],
        subplot_titles=(
            ticker,
            "Vol",
            "WaveTrend",
            "MACD",
            "Money Flow",
            "Stoch Slow",
            "Squeeze Mom",
            "Reversal Pack",
            "Momentum Pack",
            "Flow Pack",
            "ADX / DMI",
            "BB / VWAP Position",
            "RSI / Stoch RSI",
            "CMF / OBV / AD Line",
            "Ichimoku / Mass",
            "Objective Engine",
            "5-Committee Ensemble",
        ),
    )
    hover=_build_candle_hover(dc)
    fig.add_trace(go.Candlestick(x=dc.index,open=dc['Open'],high=dc['High'],low=dc['Low'],close=dc['Close'],name="Price",increasing_line_color=SOFT_GREEN,decreasing_line_color=SOFT_RED,increasing_fillcolor=SOFT_GREEN_FILL,decreasing_fillcolor=SOFT_RED_FILL,text=hover,hoverinfo='text',hoverlabel=dict(bgcolor='rgba(11,14,20,.97)',bordercolor='#334155',font=dict(size=11,family=PLOTLY_FONT_FAMILY,color='#F1F5F9'),align='left'),showlegend=False),row=1,col=1)
    for mp in [20,50,200]:fig.add_trace(go.Scatter(x=dc.index,y=dc[f'MA{mp}'],line=dict(color=mac[mp],width=1.2),name=f'{mp}MA',legendgroup='moving_average',hoverinfo='skip',showlegend=True,visible=True),row=1,col=1)
    for ep,color in [(12,'#22D3EE'),(26,'#A78BFA')]:fig.add_trace(go.Scatter(x=dc.index,y=dc[f'EMA{ep}'],line=dict(color=color,width=1.2,dash='dot'),name=f'EMA{ep}',legendgroup='ema_overlay',hoverinfo='skip',showlegend=True,visible='legendonly'),row=1,col=1)
    for idx,(mc,clr) in enumerate([(dc['ST_Direction']==1,SOFT_GREEN),(dc['ST_Direction']==-1,SOFT_RED)],start=1):fig.add_trace(go.Scatter(x=dc.index,y=dc['SuperTrend'].where(mc),line=dict(color=clr,width=2),name='SuperTrend',legendgroup='supertrend',connectgaps=False,hoverinfo='skip',showlegend=(idx==1),visible='legendonly'),row=1,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['BB_Up'],line=dict(color='#475569',width=1,dash='dot'),name='Bollinger Band',legendgroup='bollinger_band',hoverinfo='skip',showlegend=True,visible='legendonly'),row=1,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['BB_Low'],line=dict(color='#475569',width=1,dash='dot'),legendgroup='bollinger_band',fill='tonexty',fillcolor='rgba(71,85,105,.06)',hoverinfo='skip',showlegend=False,visible='legendonly'),row=1,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['Envelope_Up'],line=dict(color='rgba(250,204,21,.9)',width=1,dash='dot'),name='Envelope',legendgroup='envelope_overlay',hoverinfo='skip',showlegend=True,visible='legendonly'),row=1,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['Envelope_Low'],line=dict(color='rgba(250,204,21,.9)',width=1,dash='dot'),legendgroup='envelope_overlay',fill='tonexty',fillcolor='rgba(250,204,21,.05)',hoverinfo='skip',showlegend=False,visible='legendonly'),row=1,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['Price_Channel_Up'],line=dict(color='rgba(248,113,113,.85)',width=1,dash='dash'),name='Price Channel',legendgroup='price_channel',hoverinfo='skip',showlegend=True,visible='legendonly'),row=1,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['Price_Channel_Low'],line=dict(color='rgba(74,222,128,.85)',width=1,dash='dash'),legendgroup='price_channel',fill='tonexty',fillcolor='rgba(148,163,184,.05)',hoverinfo='skip',showlegend=False,visible='legendonly'),row=1,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['VWAP'],line=dict(color='#38BDF8',width=1.4),name='VWAP',legendgroup='vwap_overlay',hoverinfo='skip',showlegend=True,visible='legendonly'),row=1,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['Fixed_VWAP'],line=dict(color='#F59E0B',width=1.4,dash='dot'),name='Fixed VWAP',legendgroup='vwap_overlay',hoverinfo='skip',showlegend=True,visible='legendonly'),row=1,col=1)
    if 'HMA' in dc.columns:
        hup=dc.get('HMA_Rising',pd.Series(False,index=dc.index)).fillna(False)
        fig.add_trace(go.Scatter(x=dc.index,y=dc['HMA'].where(hup),line=dict(color=SOFT_GREEN,width=2.5),name='Hull MA',legendgroup='hull_ma',connectgaps=False,hoverinfo='skip',showlegend=True,visible=True),row=1,col=1)
        fig.add_trace(go.Scatter(x=dc.index,y=dc['HMA'].where(~hup),line=dict(color=SOFT_RED,width=2.5),legendgroup='hull_ma',connectgaps=False,hoverinfo='skip',showlegend=False,visible=True),row=1,col=1)
    if 'UTBot_Stop' in dc.columns:
        ub=dc['UTBot_Dir']==1;us=dc['UTBot_Dir']==-1
        fig.add_trace(go.Scatter(x=dc.index,y=dc['UTBot_Stop'].where(ub),line=dict(color='rgba(126,216,182,.5)',width=2,dash='dot'),name='UTBot Stop',legendgroup='utbot_stop',connectgaps=False,hoverinfo='skip',showlegend=True,visible='legendonly'),row=1,col=1)
        fig.add_trace(go.Scatter(x=dc.index,y=dc['UTBot_Stop'].where(us),line=dict(color='rgba(243,165,165,.5)',width=2,dash='dot'),name='UTBot Stop',legendgroup='utbot_stop',connectgaps=False,hoverinfo='skip',showlegend=False,visible='legendonly'),row=1,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['Parabolic_SAR'],mode='markers',marker=dict(size=5,color=np.where(dc['PSAR_Direction']>=0,'rgba(74,222,128,.95)','rgba(248,113,113,.95)').tolist(),symbol='circle'),name='Parabolic SAR',legendgroup='psar_overlay',hovertemplate="PSAR:%{y:.2f}<extra></extra>",showlegend=True,visible='legendonly'),row=1,col=1)
    for sn,clr,sym,sz,lbl in [('Hull_Turn_Bull',SOFT_GREEN,'circle',8,'🟢Hull▲'),('Hull_Turn_Bear',SOFT_RED,'circle',8,'🔴Hull▼'),('UTBot_Buy',SOFT_GREEN,'triangle-up',12,'🤖UTBot▲'),('UTBot_Sell',SOFT_RED,'triangle-down',12,'🤖UTBot▼'),('VuManChu_Bull',SOFT_GREEN,'diamond',12,'💎VuMC▲'),('VuManChu_Bear',SOFT_RED,'diamond',12,'💎VuMC▼')]:
        yoff=dc['Low']-dc['ATR']*(0.8 if 'Hull' in sn else 1.2 if 'UTBot' in sn else 1.8) if 'Bull' in sn or 'Buy' in sn else dc['High']+dc['ATR']*(0.8 if 'Hull' in sn else 1.2 if 'UTBot' in sn else 1.8)
        _sig_marker(fig,dc,sn,1,yoff,clr,sym,sz,lbl)
    for sn,clr,sym,sz,lbl,legendgroup,showlegend,visible in [
        ('Hull_Turn_Bull',SOFT_GREEN,'circle',8,'Hull Turn','hull_signal',True,True),
        ('Hull_Turn_Bear',SOFT_RED,'circle',8,'Hull Turn','hull_signal',False,True),
        ('UTBot_Buy',SOFT_GREEN,'triangle-up',12,'UTBot Signal','utbot_signal',True,'legendonly'),
        ('UTBot_Sell',SOFT_RED,'triangle-down',12,'UTBot Signal','utbot_signal',False,'legendonly'),
        ('VuManChu_Bull',SOFT_GREEN,'diamond',12,'VuManChu Signal','vumanchu_signal',True,'legendonly'),
        ('VuManChu_Bear',SOFT_RED,'diamond',12,'VuManChu Signal','vumanchu_signal',False,'legendonly')
    ]:
        yoff=dc['Low']-dc['ATR']*(0.8 if 'Hull' in sn else 1.2 if 'UTBot' in sn else 1.8) if 'Bull' in sn or 'Buy' in sn else dc['High']+dc['ATR']*(0.8 if 'Hull' in sn else 1.2 if 'UTBot' in sn else 1.8)
        _sig_marker(fig,dc,sn,1,yoff,clr,sym,sz,lbl,legendgroup=legendgroup,showlegend=showlegend,visible=visible)
    sb,ss=_collect_strong_markers(dc)
    _add_trendline_overlays(fig,dc,max_per_side=2,default_visible='legendonly')
    _add_pattern_overlay(fig,dc,_detect_active_pattern(dc),default_visible='legendonly')
    _add_volume_profile_overlay(fig,dc,default_visible='legendonly')
    _add_fibonacci_overlay(fig,dc,default_visible='legendonly')
    if sb.any():
        sr=dc[sb];yv=sr['Low']-sr['ATR']*2;ht=[]
        for bi in sr.index:
            br=[SIGNAL_REGISTRY.get(s,COMBINED_SCAN_REGISTRY.get(s,{})).get('kor',s) for s in STRONG_BUY_SIGS if s in dc.columns and dc.loc[bi,s]]
            ht.append(f"<b>⭐강력매수</b><br><span style='color:#94A3B8'>{', '.join(br[:5]) or '다중강세'}</span><br>{bi.strftime('%Y-%m-%d')}")
        fig.add_trace(go.Scatter(x=sr.index,y=yv,mode='markers',marker=dict(symbol='star',size=8,color='#E8C56C',line=dict(width=2,color=SOFT_GREEN),opacity=.95),name='Strong Buy',legendgroup='strong_buy',hovertemplate="%{text}<extra></extra>",text=ht,showlegend=True,visible='legendonly'),row=1,col=1)
    if ss.any():
        sr=dc[ss];yv=sr['High']+sr['ATR']*2;ht=[]
        for bi in sr.index:
            br=[SIGNAL_REGISTRY.get(s,COMBINED_SCAN_REGISTRY.get(s,{})).get('kor',s) for s in STRONG_SELL_SIGS if s in dc.columns and dc.loc[bi,s]]
            ht.append(f"<b>⭐강력매도</b><br><span style='color:#94A3B8'>{', '.join(br[:5]) or '다중약세'}</span><br>{bi.strftime('%Y-%m-%d')}")
        fig.add_trace(go.Scatter(x=sr.index,y=yv,mode='markers',marker=dict(symbol='star',size=8,color='#E8C56C',line=dict(width=2,color=SOFT_RED),opacity=.95),name='Strong Sell',legendgroup='strong_sell',hovertemplate="%{text}<extra></extra>",text=ht,showlegend=True,visible='legendonly'),row=1,col=1)
    if dc.get('Fractal_Low',pd.Series(False,index=dc.index)).fillna(False).any():
        lows=dc[dc['Fractal_Low'].fillna(False)]
        fig.add_trace(go.Scatter(x=lows.index,y=lows['Low']-(lows['ATR']*0.9),mode='markers',marker=dict(symbol='triangle-up',size=8,color='#22C55E',line=dict(width=1,color='#E2E8F0')),name='Williams Fractal',legendgroup='fractal_overlay',hovertemplate="Fractal Low<br>%{x|%Y-%m-%d}<extra></extra>",showlegend=True,visible='legendonly'),row=1,col=1)
    if dc.get('Fractal_High',pd.Series(False,index=dc.index)).fillna(False).any():
        highs=dc[dc['Fractal_High'].fillna(False)]
        fig.add_trace(go.Scatter(x=highs.index,y=highs['High']+(highs['ATR']*0.9),mode='markers',marker=dict(symbol='triangle-down',size=8,color='#EF4444',line=dict(width=1,color='#E2E8F0')),name='Williams Fractal',legendgroup='fractal_overlay',hovertemplate="Fractal High<br>%{x|%Y-%m-%d}<extra></extra>",showlegend=False,visible='legendonly'),row=1,col=1)
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
    # R8 Reversal pack
    wr=(dc.get('Williams_R',pd.Series(-50,index=dc.index))+100).clip(0,100)
    rmi=dc.get('RMI',pd.Series(50,index=dc.index)).clip(0,100)
    cci=dc.get('CCI',pd.Series(0,index=dc.index))
    cci_scaled=(50+cci.clip(-200,200)/4).clip(0,100)
    fig.add_trace(go.Bar(x=dc.index,y=cci_scaled-50,base=50,marker_color=np.where(cci>=0,'rgba(248,113,113,.30)','rgba(74,222,128,.30)').tolist(),name='CCI Band',hovertemplate="CCI:%{customdata:.0f}<extra></extra>",customdata=cci.values,showlegend=False),row=8,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=wr,line=dict(color='#38BDF8',width=2),name='Williams %R',hovertemplate="Williams %R:%{customdata:.0f}<extra></extra>",customdata=dc.get('Williams_R',pd.Series(-50,index=dc.index)).values),row=8,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=rmi,line=dict(color='#F472B6',width=1.8,dash='dot'),name='RMI',hovertemplate="RMI:%{y:.1f}<extra></extra>"),row=8,col=1)
    if dc.get('Fractal_Low',pd.Series(False,index=dc.index)).fillna(False).any():
        lows=dc[dc['Fractal_Low'].fillna(False)]
        fig.add_trace(go.Scatter(x=lows.index,y=(lows['Williams_R']+100).clip(0,100),mode='markers',marker=dict(symbol='diamond',size=8,color='#22C55E',line=dict(width=1,color='#E2E8F0')),name='Fractal Low',hovertemplate="Fractal Low<br>%{x|%Y-%m-%d}<extra></extra>",showlegend=False),row=8,col=1)
    if dc.get('Fractal_High',pd.Series(False,index=dc.index)).fillna(False).any():
        highs=dc[dc['Fractal_High'].fillna(False)]
        fig.add_trace(go.Scatter(x=highs.index,y=(highs['Williams_R']+100).clip(0,100),mode='markers',marker=dict(symbol='diamond',size=8,color='#EF4444',line=dict(width=1,color='#E2E8F0')),name='Fractal High',hovertemplate="Fractal High<br>%{x|%Y-%m-%d}<extra></extra>",showlegend=False),row=8,col=1)
    for y_,clr in [(20,'#38BDF8'),(50,'#64748B'),(80,'#F87171')]:fig.add_hline(y=y_,line_dash='dash',line_color=clr,line_width=1,row=8,col=1)
    # R9 Momentum pack
    roc=dc.get('ROC',pd.Series(0,index=dc.index))
    trix=dc.get('TRIX',pd.Series(0,index=dc.index))
    posc=dc.get('Price_Oscillator',pd.Series(0,index=dc.index))
    fig.add_trace(go.Bar(x=dc.index,y=roc,marker_color=np.where(roc>=0,'rgba(34,197,94,.65)','rgba(239,68,68,.65)').tolist(),name='ROC',hovertemplate="ROC:%{y:+.2f}<extra></extra>",showlegend=False),row=9,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=trix,line=dict(color='#F59E0B',width=2),name='TRIX',hovertemplate="TRIX:%{y:+.3f}<extra></extra>"),row=9,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=posc,line=dict(color='#A78BFA',width=1.8,dash='dot'),name='Price Osc',hovertemplate="Price Osc:%{y:+.2f}<extra></extra>"),row=9,col=1)
    fig.add_hline(y=0,line_color="#64748B",line_width=1,row=9,col=1)
    # R10 Flow pack
    vol_osc=dc.get('Volume_Oscillator',pd.Series(0,index=dc.index))
    chaikin=dc.get('Chaikin_Oscillator',pd.Series(0,index=dc.index))
    intensity=dc.get('Intraday_Intensity_Index',pd.Series(0,index=dc.index))
    fig.add_trace(go.Bar(x=dc.index,y=vol_osc,marker_color=np.where(vol_osc>=0,'rgba(16,185,129,.68)','rgba(244,63,94,.68)').tolist(),name='Vol Osc',hovertemplate="Vol Osc:%{y:+.2f}<extra></extra>"),row=10,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=chaikin,line=dict(color='#22D3EE',width=1.8),name='Chaikin',hovertemplate="Chaikin:%{y:+.2f}<extra></extra>"),row=10,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=intensity,line=dict(color='#F472B6',width=1.8,dash='dot'),name='Intensity',hovertemplate="Intraday Intensity:%{y:+.2f}<extra></extra>"),row=10,col=1)
    fig.add_hline(y=0,line_color="#64748B",line_width=1,row=10,col=1)
    # R11 Objective engine
    obuy=dc.get('Objective_Buy_Score',pd.Series(0,index=dc.index))
    osell=dc.get('Objective_Sell_Score',pd.Series(0,index=dc.index))
    oconf=dc.get('Objective_Conflict_Score',pd.Series(0,index=dc.index))
    fig.add_trace(go.Bar(x=dc.index,y=obuy,marker_color='rgba(99,217,162,.82)',name='Objective Buy',hovertemplate="Objective Buy:%{y:.1f}<extra></extra>"),row=11,col=1)
    fig.add_trace(go.Bar(x=dc.index,y=-osell,marker_color='rgba(255,143,150,.82)',name='Objective Sell',hovertemplate="Objective Sell:%{customdata:.1f}<extra></extra>",customdata=osell.values),row=11,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=oconf,line=dict(color='#F6C35E',width=1.8),name='Conflict',hovertemplate="Conflict:%{y:.1f}<extra></extra>"),row=11,col=1)
    fig.add_hline(y=0,line_color="#64748B",line_width=1,row=11,col=1)
    # R12 Ensemble
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
    chart_height = 1540 if len(dc) <= 126 else 1680
    fig.update_layout(template="plotly_dark",paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",margin=dict(l=18,r=18,t=72,b=16),height=chart_height,showlegend=True,hovermode="closest",legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="center",x=.5,font=dict(size=8,color='#94A3B8'),bgcolor='rgba(0,0,0,0)',traceorder='normal',groupclick='togglegroup'))
    for i in range(1,9):fig.update_layout(**{(f'yaxis{i}' if i>1 else 'yaxis'):dict(gridcolor='rgba(51,65,85,.3)',tickfont=dict(size=9,color='#64748B'))})
    fig.update_yaxes(range=[-50,50],row=5,col=1);fig.update_yaxes(range=[0,100],row=6,col=1)
    ad=pd.date_range(start=dc.index[0],end=dc.index[-1],freq='D');nt=ad.difference(dc.index.normalize())
    fig.update_xaxes(rangeslider_visible=False,rangebreaks=[dict(values=nt.tolist())],gridcolor='rgba(51,65,85,.3)',tickfont=dict(size=9,color='#64748B'),automargin=True)
    for ann in fig['layout']['annotations']:
        ann['font']=dict(size=11,color='#94A3B8',family=PLOTLY_FONT_FAMILY)
        ann['yshift']=8
    return fig

def _build_indicator_lab_chart_legacy(dc,ticker):
    fig=make_subplots(
        rows=4,cols=1,shared_xaxes=True,vertical_spacing=0.035,
        row_heights=[.24,.22,.22,.32],
        subplot_titles=("추가 반전 팩","추가 모멘텀 팩","추가 수급 팩","객관 엔진 시계열")
    )
    idx=dc.index
    wr=(dc.get('Williams_R',pd.Series(-50,index=idx))+100).clip(0,100)
    rmi=dc.get('RMI',pd.Series(50,index=idx)).clip(0,100)
    cci_scaled=(50+dc.get('CCI',pd.Series(0,index=idx)).clip(-200,200)/4).clip(0,100)
    roc=dc.get('ROC',pd.Series(0,index=idx))
    trix=dc.get('TRIX',pd.Series(0,index=idx))
    posc=dc.get('Price_Oscillator',pd.Series(0,index=idx))
    vol_osc=dc.get('Volume_Oscillator',pd.Series(0,index=idx))
    chaikin=dc.get('Chaikin_Oscillator',pd.Series(0,index=idx))
    intensity=dc.get('Intraday_Intensity_Index',pd.Series(0,index=idx))
    obuy=dc.get('Objective_Buy_Score',pd.Series(0,index=idx))
    osell=dc.get('Objective_Sell_Score',pd.Series(0,index=idx))
    oconf=dc.get('Objective_Conflict_Score',pd.Series(0,index=idx))

    fig.add_trace(go.Bar(x=idx,y=cci_scaled-50,base=50,marker_color=np.where(dc.get('CCI',pd.Series(0,index=idx))>=0,'rgba(248,113,113,.30)','rgba(74,222,128,.30)').tolist(),name='CCI Band',hovertemplate="CCI:%{customdata:.0f}<extra></extra>",customdata=dc.get('CCI',pd.Series(0,index=idx)).values,showlegend=False),row=1,col=1)
    fig.add_trace(go.Scatter(x=idx,y=wr,line=dict(color='#38BDF8',width=2),name='Williams %R',hovertemplate="Williams %R:%{customdata:.0f}<extra></extra>",customdata=dc.get('Williams_R',pd.Series(-50,index=idx)).values),row=1,col=1)
    fig.add_trace(go.Scatter(x=idx,y=rmi,line=dict(color='#F472B6',width=1.8,dash='dot'),name='RMI',hovertemplate="RMI:%{y:.1f}<extra></extra>"),row=1,col=1)
    if dc.get('Fractal_Low',pd.Series(False,index=idx)).fillna(False).any():
        lows=dc[dc['Fractal_Low'].fillna(False)]
        fig.add_trace(go.Scatter(x=lows.index,y=(lows['Williams_R']+100).clip(0,100),mode='markers',marker=dict(symbol='diamond',size=8,color='#22C55E',line=dict(width=1,color='#E2E8F0')),name='Fractal Low',hovertemplate="Fractal Low<br>%{x|%Y-%m-%d}<extra></extra>",showlegend=False),row=1,col=1)
    if dc.get('Fractal_High',pd.Series(False,index=idx)).fillna(False).any():
        highs=dc[dc['Fractal_High'].fillna(False)]
        fig.add_trace(go.Scatter(x=highs.index,y=(highs['Williams_R']+100).clip(0,100),mode='markers',marker=dict(symbol='diamond',size=8,color='#EF4444',line=dict(width=1,color='#E2E8F0')),name='Fractal High',hovertemplate="Fractal High<br>%{x|%Y-%m-%d}<extra></extra>",showlegend=False),row=1,col=1)
    for y_,clr in [(20,'#38BDF8'),(50,'#64748B'),(80,'#F87171')]:fig.add_hline(y=y_,line_dash='dash',line_color=clr,line_width=1,row=1,col=1)

    fig.add_trace(go.Bar(x=idx,y=roc,marker_color=np.where(roc>=0,'rgba(34,197,94,.65)','rgba(239,68,68,.65)').tolist(),name='ROC',hovertemplate="ROC:%{y:+.2f}<extra></extra>",showlegend=False),row=2,col=1)
    fig.add_trace(go.Scatter(x=idx,y=trix,line=dict(color='#F59E0B',width=2),name='TRIX',hovertemplate="TRIX:%{y:+.3f}<extra></extra>"),row=2,col=1)
    fig.add_trace(go.Scatter(x=idx,y=posc,line=dict(color='#A78BFA',width=1.8,dash='dot'),name='Price Osc',hovertemplate="Price Osc:%{y:+.2f}<extra></extra>"),row=2,col=1)
    fig.add_hline(y=0,line_color="#64748B",line_width=1,row=2,col=1)

    fig.add_trace(go.Bar(x=idx,y=vol_osc,marker_color=np.where(vol_osc>=0,'rgba(16,185,129,.68)','rgba(244,63,94,.68)').tolist(),name='Vol Osc',hovertemplate="Vol Osc:%{y:+.2f}<extra></extra>"),row=3,col=1)
    fig.add_trace(go.Scatter(x=idx,y=chaikin,line=dict(color='#22D3EE',width=1.8),name='Chaikin',hovertemplate="Chaikin:%{y:+.2f}<extra></extra>"),row=3,col=1)
    fig.add_trace(go.Scatter(x=idx,y=intensity,line=dict(color='#F472B6',width=1.8,dash='dot'),name='Intensity',hovertemplate="Intraday Intensity:%{y:+.2f}<extra></extra>"),row=3,col=1)
    fig.add_hline(y=0,line_color="#64748B",line_width=1,row=3,col=1)

    fig.add_trace(go.Bar(x=idx,y=obuy,marker_color='rgba(99,217,162,.82)',name='Objective Buy',hovertemplate="Objective Buy:%{y:.1f}<extra></extra>"),row=4,col=1)
    fig.add_trace(go.Bar(x=idx,y=-osell,marker_color='rgba(255,143,150,.82)',name='Objective Sell',hovertemplate="Objective Sell:%{customdata:.1f}<extra></extra>",customdata=osell.values),row=4,col=1)
    fig.add_trace(go.Scatter(x=idx,y=oconf,line=dict(color='#F6C35E',width=1.8),name='Conflict',hovertemplate="Conflict:%{y:.1f}<extra></extra>"),row=4,col=1)
    fig.add_hline(y=0,line_color="#64748B",line_width=1,row=4,col=1)

    ad=pd.date_range(start=dc.index[0],end=dc.index[-1],freq='D');nt=ad.difference(dc.index.normalize())
    fig.update_layout(
        template="plotly_dark",paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20,r=20,t=72,b=16),height=1080,showlegend=True,hovermode="x unified",
        legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="center",x=.5,font=dict(size=9,color='#94A3B8'),bgcolor='rgba(0,0,0,0)',traceorder='normal',groupclick='togglegroup')
    )
    for i in range(1,5):
        fig.update_layout(**{(f'yaxis{i}' if i>1 else 'yaxis'):dict(gridcolor='rgba(51,65,85,.28)',tickfont=dict(size=9,color='#64748B'),automargin=True)})
        fig.update_xaxes(rangeslider_visible=False,rangebreaks=[dict(values=nt.tolist())],gridcolor='rgba(51,65,85,.28)',tickfont=dict(size=9,color='#64748B'),automargin=True,row=i,col=1)
    fig.update_yaxes(range=[0,100],row=1,col=1)
    for ann in fig['layout']['annotations']:
        ann['font']=dict(size=12,color='#94A3B8',family=PLOTLY_FONT_FAMILY)
        ann['yshift']=8
    return fig

def _build_summary_snapshot(dc):
    snapshot={
        'price':0.0,
        'price_change':0.0,
        'price_change_pct':0.0,
        'summary_price_available':False,
        'summary_change_available':False,
        'summary_date':'',
    }
    if dc is None or dc.empty or 'Close' not in dc.columns:
        return snapshot
    close_series=pd.to_numeric(dc['Close'],errors='coerce')
    valid_close=close_series[close_series.notna() & np.isfinite(close_series) & (close_series>0)]
    if valid_close.empty:
        return snapshot
    latest_idx=valid_close.index[-1]
    latest_price=_sf(valid_close.iloc[-1])
    summary_date=latest_idx.strftime('%Y-%m-%d') if hasattr(latest_idx,'strftime') else str(latest_idx)
    snapshot.update({'price':latest_price,'summary_price_available':True,'summary_date':summary_date})
    if len(valid_close)<2:
        return snapshot
    prev_price=_sf(valid_close.iloc[-2])
    if prev_price<=0:
        return snapshot
    price_change=latest_price-prev_price
    snapshot.update({
        'price_change':price_change,
        'price_change_pct':(price_change/prev_price)*100.0,
        'summary_change_available':True,
    })
    return snapshot


def _build_ensemble_snapshot(dc):
    snapshot = {
        'ensemble_score': 0.0,
        'ensemble_score_available': False,
        'ensemble_score_source': 'unavailable',
    }
    if dc is None or dc.empty:
        return snapshot

    latest = dc.iloc[-1]
    for column in ('Final_Decision_Score', 'Ensemble_Score'):
        value = latest.get(column)
        numeric = pd.to_numeric(pd.Series([value]), errors='coerce').iloc[0]
        if pd.notna(numeric) and np.isfinite(float(numeric)):
            source = 'final_decision' if column == 'Final_Decision_Score' else 'ensemble'
            snapshot.update({'ensemble_score': float(numeric), 'ensemble_score_available': True, 'ensemble_score_source': source})
            return snapshot

    for column in ('Final_Decision_Score', 'Ensemble_Score'):
        if column not in dc.columns:
            continue
        series = pd.to_numeric(dc[column], errors='coerce')
        series = series.replace([np.inf, -np.inf], np.nan).dropna()
        if not series.empty:
            source = 'recent_final_decision' if column == 'Final_Decision_Score' else 'recent_ensemble'
            snapshot.update({'ensemble_score': float(series.iloc[-1]), 'ensemble_score_available': True, 'ensemble_score_source': source})
            return snapshot

    buy_total = pd.to_numeric(pd.Series([latest.get('Buy_Total')]), errors='coerce').iloc[0]
    sell_total = pd.to_numeric(pd.Series([latest.get('Sell_Total')]), errors='coerce').iloc[0]
    if pd.notna(buy_total) and pd.notna(sell_total):
        snapshot.update({
            'ensemble_score': float(np.clip((float(buy_total) - float(sell_total)) * 0.55, -100.0, 100.0)),
            'ensemble_score_available': True,
            'ensemble_score_source': 'layer_edge_fallback',
        })
    return snapshot


def build_metadata(dc,ticker):
    lat=dc.iloc[-1]
    summary_snapshot=_build_summary_snapshot(dc)
    ensemble_snapshot=_build_ensemble_snapshot(dc)
    summary_price=_sf(summary_snapshot['price'])
    summary_price_available=bool(summary_snapshot['summary_price_available'])
    display_close=max(summary_price if summary_price_available else _sf(lat.get('Close')),0.01)
    pc=summary_snapshot['price_change'];pp=summary_snapshot['price_change_pct']
    LN=['Trend','Momentum','Candle','BB','Volume','MF','Pattern','Combined','Leading','Lagging']
    bl={n:_sf(lat.get(f'BL_{n}',0)) for n in LN};sl={n:_sf(lat.get(f'SL_{n}',0)) for n in LN}
    acs=[]
    for cn,ccfg in COMBINED_SCAN_REGISTRY.items():
        if cn in dc.columns and dc[cn].tail(5).any():
            combo_kor,combo_desc=localize_combo(cn,ccfg.get('kor'),ccfg.get('desc'))
            ld=dc[cn].tail(5)[dc[cn].tail(5)].index[-1];acs.append({'key':cn,'name':ccfg['name'],'kor':combo_kor,'desc':combo_desc,'dir':ccfg['dir'],'tier':ccfg['tier'],'icon':ccfg['icon'],'color':ccfg['color'],'win':ccfg['win'],'date':ld.strftime('%m/%d'),'is_today':(dc.index[-1]-ld).days==0,'days_ago':(dc.index[-1]-ld).days})
    acs.sort(key=lambda x:(x['tier'],x['days_ago']))
    recent=[]
    for ir,row in dc.tail(15).iterrows():
        ds=ir.strftime('%m/%d')
        for col,cfg in SIGNAL_REGISTRY.items():
            if col in dc.columns and row.get(col,False):
                signal_kor,signal_desc=localize_signal(col,cfg.get('kor'),cfg.get('desc'))
                recent.append({
                    'key': col,
                    'icon': cfg['icon'],
                    'label': signal_kor,
                    'date': ds,
                    'dir': cfg['dir'],
                    'is_combined': False,
                    'desc': signal_desc,
                    'meaning': explain_signal_meaning(col, signal_desc, is_combo=False),
                })
        for col,cfg in COMBINED_SCAN_REGISTRY.items():
            if col in dc.columns and row.get(col,False):
                combo_kor,combo_desc=localize_combo(col,cfg.get('kor'),cfg.get('desc'))
                recent.append({
                    'key': col,
                    'icon': cfg['icon'],
                    'label': combo_kor,
                    'date': ds,
                    'dir': cfg['dir'],
                    'is_combined': True,
                    'desc': combo_desc,
                    'meaning': explain_signal_meaning(col, combo_desc, is_combo=True),
                })
    derived_signal_events=[];derived_reason_states=[];latest_signal_date=dc.index[-1].strftime('%m/%d')
    for key,cfg in DERIVED_SIGNAL_REGISTRY.items():
        if bool(lat.get(key,False)):
            desc_text = str(cfg.get('desc') or '')
            payload={'key':key,'icon':'','label':str(cfg.get('kor') or key),'date':latest_signal_date,'dir':str(cfg.get('dir') or 'neutral'),'is_combined':False,'desc':desc_text,'meaning':explain_signal_meaning(key, desc_text, is_combo=False)}
            if str(cfg.get('surface') or 'reason')=='badge':derived_signal_events.append(payload)
            else:derived_reason_states.append(payload)
    strategy_payload=build_strategy_payload(dc)
    strategy_summary=strategy_payload.get('summary',{})
    strategy_results=strategy_payload.get('results',[])
    strategy_visible_results=strategy_payload.get('visible_results',[])
    rg=int(lat.get('Regime',0));rl={2:'STRONG BULL 🟢🟢',1:'BULL 🟢',0:'NEUTRAL ⚪',-1:'BEAR 🔴',-2:'STRONG BEAR 🔴🔴'}.get(rg,'N/A')
    committee={}
    for cm in COMMITTEE_NAMES:vv=int(_sf(lat.get(f'CM_{cm}_Vote',0)));committee[cm]={'score':_sf(lat.get(f'CM_{cm}_EffScore',0)),'conviction':_sf(lat.get(f'CM_{cm}_EffConv',0)),'vote':'BUY' if vv==1 else('SELL' if vv==-1 else('ABSTAIN' if vv==-99 else 'NEUTRAL')),'vote_int':vv}
    ctx_code=int(_sf(lat.get('Market_Context',0)))
    close_latest=display_close
    dollar_volume_20=_sf(lat.get('Dollar_Volume_20'))
    dollar_volume_log=np.log10(dc.get('Dollar_Volume_20',pd.Series(0,index=dc.index)).clip(lower=1))
    dollar_volume_z=_sf((((dollar_volume_log-dollar_volume_log.rolling(60,min_periods=20).mean())/(dollar_volume_log.rolling(60,min_periods=20).std()+1e-10))*1.0).iloc[-1])
    ad_line_series=dc.get('AD_Line',pd.Series(0,index=dc.index))
    ad_line_z=_sf((((ad_line_series-ad_line_series.rolling(60,min_periods=20).mean())/(ad_line_series.rolling(60,min_periods=20).std()+1e-10))*1.0).iloc[-1])
    channel_up=_sf(lat.get('Price_Channel_Up'))
    channel_low=_sf(lat.get('Price_Channel_Low'))
    channel_span=(channel_up-channel_low)
    channel_position=0.0 if abs(channel_span) < 1e-10 else (((close_latest-channel_low)/(channel_span+1e-10))-0.5)*100.0
    supertrend_gap=((close_latest-_sf(lat.get('SuperTrend')))/(close_latest+1e-10))*100.0
    tenkan_gap=((close_latest-_sf(lat.get('Ichimoku_Tenkan')))/(close_latest+1e-10))*100.0
    kijun_gap=((close_latest-_sf(lat.get('Ichimoku_Kijun')))/(close_latest+1e-10))*100.0
    cloud_spread=((_sf(lat.get('Ichimoku_SenkouA'))-_sf(lat.get('Ichimoku_SenkouB')))/(close_latest+1e-10))*100.0
    stock_return_20=_sf(lat.get('Stock_Return'))*100.0
    spy_return_20=_sf(lat.get('SPY_Return'))*100.0
    excess_return_20=stock_return_20-spy_return_20
    payload={'ticker':ticker.upper(),'price':summary_price,'price_change':pc,'price_change_pct':pp,'summary_price_available':summary_snapshot['summary_price_available'],'summary_change_available':summary_snapshot['summary_change_available'],'summary_date':summary_snapshot['summary_date'],'volume':_sf(lat['Volume']),'avg_volume':_sf(dc['Volume'].rolling(20).mean().iloc[-1]),
        'wt1':_sf(lat.get('WT1')),'rsi':_sf(lat.get('RSI'),50),'mfi':_sf(lat.get('MFI'),50),'stochk':_sf(lat.get('StochK'),50),'adx':_sf(lat.get('ADX')),'atr':_sf(lat.get('ATR')),'atr_pct':_sf(lat.get('ATR'))/(close_latest)*100,
        'macd_hist':_sf(lat.get('MACD_Hist')),'cmf':_sf(lat.get('CMF')),'composite_accel':_sf(lat.get('Composite_Accel')),'rs_ratio':_sf(lat.get('RS_Ratio'),1),
        'regime':rg,'regime_label':rl,'regime_score':_sf(lat.get('Regime_Score')),'last_date':dc.index[-1].strftime('%Y-%m-%d'),'squeeze_on':bool(lat.get('Squeeze_On',False)),
        'bias_mode':str(lat.get('Bias_Mode', DEFAULT_BIAS_MODE)),
        'buy_total':_sf(lat.get('Buy_Total')),'sell_total':_sf(lat.get('Sell_Total')),'buy_active':int(_sf(lat.get('Buy_Active_Layers'))),'sell_active':int(_sf(lat.get('Sell_Active_Layers'))),
        'buy_layers':bl,'sell_layers':sl,'judgment':str(lat.get('Trade_Judgment','NEUTRAL')),'confidence':_sf(lat.get('Judgment_Confidence')),
        'objective_buy_score':_sf(lat.get('Objective_Buy_Score')),'objective_sell_score':_sf(lat.get('Objective_Sell_Score')),'objective_conflict_score':_sf(lat.get('Objective_Conflict_Score')),
        'objective_trend_buy':_sf(lat.get('Objective_Trend_Buy')),'objective_trend_sell':_sf(lat.get('Objective_Trend_Sell')),
        'objective_momentum_buy':_sf(lat.get('Objective_Momentum_Buy')),'objective_momentum_sell':_sf(lat.get('Objective_Momentum_Sell')),
        'objective_money_buy':_sf(lat.get('Objective_Money_Buy')),'objective_money_sell':_sf(lat.get('Objective_Money_Sell')),
        'objective_reversal_buy':_sf(lat.get('Objective_Reversal_Buy')),'objective_reversal_sell':_sf(lat.get('Objective_Reversal_Sell')),
        'objective_location_buy':_sf(lat.get('Objective_Location_Buy')),'objective_location_sell':_sf(lat.get('Objective_Location_Sell')),
        'objective_signal_buy':_sf(lat.get('Objective_Signal_Buy')),'objective_signal_sell':_sf(lat.get('Objective_Signal_Sell')),
        'objective_combo_buy':_sf(lat.get('Objective_Combo_Buy')),'objective_combo_sell':_sf(lat.get('Objective_Combo_Sell')),
        'objective_judgment':str(lat.get('Objective_Judgment','NEUTRAL')),'objective_confidence':_sf(lat.get('Objective_Confidence')),
        'objective_buy_agree':int(_sf(lat.get('Objective_Buy_Agree'))),'objective_sell_agree':int(_sf(lat.get('Objective_Sell_Agree'))),
        'objective_reason':str(lat.get('Objective_Reason','')),'objective_detail':str(lat.get('Objective_Detail','')),
        'objective_action_label':str(lat.get('Objective_Action_Label','')),'objective_alignment':str(lat.get('Objective_Alignment','MIXED')),
        'objective_adjustment':str(lat.get('Objective_Adjustment','NONE')),
        'ensemble_score':ensemble_snapshot['ensemble_score'],'ensemble_score_available':ensemble_snapshot['ensemble_score_available'],'ensemble_score_source':ensemble_snapshot['ensemble_score_source'],'prediction_boost':_sf(lat.get('Prediction_Boost')),
        'leading_verdict':str(lat.get('Leading_Verdict','중립')),'lagging_verdict':str(lat.get('Lagging_Verdict','비추세/횡보')),
        'setup_pressure_buy':_sf(lat.get('Setup_Pressure_Buy')),'setup_pressure_sell':_sf(lat.get('Setup_Pressure_Sell')),
        'utbot_dir':int(_sf(lat.get('UTBot_Dir'))),'hma_rising':bool(lat.get('HMA_Rising',False)),'slowk':_sf(lat.get('SlowK'),50),'squeeze_mom':_sf(lat.get('Squeeze_Momentum')),
        'context':ctx_code,'context_label':CTX_KOR.get(ctx_code,'기본'),'committee':committee,
        'buy_agree':int(_sf(lat.get('Buy_Agree'))),'sell_agree':int(_sf(lat.get('Sell_Agree'))),'veto_flags':str(lat.get('Veto_Flags','')),'reversal_synergy':_sf(lat.get('Reversal_Synergy')),
        'judgment_reason':str(lat.get('Judgment_Reason','')),'judgment_detail':str(lat.get('Judgment_Detail','')),'action_label':str(lat.get('Action_Label','')),
        'pre_veto_judgment':str(lat.get('PreVeto_Judgment','')),'downgrade_count':int(_sf(lat.get('Downgrade_Count'))),
        'macro_risk_off_count':int(_sf(lat.get('Macro_Risk_Off_Count'))),'macro_risk_on_count':int(_sf(lat.get('Macro_Risk_On_Count'))),
        'market_filter_bias':_sf(lat.get('Market_Filter_Bias')),'flip_guard_triggered':bool(lat.get('Flip_Guard_Triggered',False)),
        'macro_pressure_score':_sf(lat.get('Macro_Pressure_Score')),'market_breadth_score':_sf(lat.get('Market_Breadth_Score')),
        'breadth_risk_on':bool(lat.get('Breadth_Risk_On',False)),'breadth_risk_off':bool(lat.get('Breadth_Risk_Off',False)),
        'spy_risk_on':bool(lat.get('SPY_Risk_On',False)),'spy_risk_off':bool(lat.get('SPY_Risk_Off',False)),
        'vix_risk_on':bool(lat.get('VIX_Risk_On',False)),'vix_risk_off':bool(lat.get('VIX_Risk_Off',False)),
        'tnx_tailwind':bool(lat.get('TNX_Tailwind',False)),'tnx_headwind':bool(lat.get('TNX_Headwind',False)),
        'dxy_tailwind':bool(lat.get('DXY_Tailwind',False)),'dxy_headwind':bool(lat.get('DXY_Headwind',False)),
        'vix_pressure_score':_sf(lat.get('VIX_Pressure_Score')),'tnx_pressure_score':_sf(lat.get('TNX_Pressure_Score')),'dxy_pressure_score':_sf(lat.get('DXY_Pressure_Score')),
        'narrow_leadership':bool(lat.get('Narrow_Leadership',False)),'leader_stock_mode':bool(lat.get('Leader_Stock_Mode',False)),'leader_stock_score':_sf(lat.get('Leader_Stock_Score')),
        'trend_inflection_buy_score':_sf(lat.get('Trend_Inflection_Buy_Score')),'trend_inflection_sell_score':_sf(lat.get('Trend_Inflection_Sell_Score')),
        'trend_inflection_bull':bool(lat.get('Trend_Inflection_Bull',False)),'trend_inflection_bear':bool(lat.get('Trend_Inflection_Bear',False)),
        'market_turn_bull_score':_sf(lat.get('Market_Turn_Bull_Score')),'market_turn_bear_score':_sf(lat.get('Market_Turn_Bear_Score')),
        'market_turn_bull':bool(lat.get('Market_Turn_Bull',False)),'market_turn_bear':bool(lat.get('Market_Turn_Bear',False)),
        'continuation_buy_score':_sf(lat.get('Continuation_Buy_Score')),'continuation_sell_score':_sf(lat.get('Continuation_Sell_Score')),
        'signal_conflict_layers':int(_sf(lat.get('Signal_Conflict_Layers'))),
        'utbot_stop_atr_gap':_sf(lat.get('UTBot_Stop_ATR_Gap')),
        'bullish_gap_reversal':bool(lat.get('Bullish_Gap_Reversal',False)),'bearish_gap_failure':bool(lat.get('Bearish_Gap_Failure',False)),
        'thin_trade_risk':bool(lat.get('Thin_Trade_Risk',False)),
        'diag_support_hold':bool(lat.get('Diag_Support_Hold',False)),'diag_breakout_bull':bool(lat.get('Diag_Breakout_Bull',False)),
        'diag_resistance_reject':bool(lat.get('Diag_Resistance_Reject',False)),'diag_breakdown_bear':bool(lat.get('Diag_Breakdown_Bear',False)),
        'box_support_hold':bool(lat.get('Box_Support_Hold',False)),'box_resistance_reject':bool(lat.get('Box_Resistance_Reject',False)),
        'box_breakout_bull':bool(lat.get('Box_Breakout_Bull',False)),'box_breakdown_bear':bool(lat.get('Box_Breakdown_Bear',False)),
        'channel_support_hold':bool(lat.get('Channel_Support_Hold',False)),'channel_resistance_reject':bool(lat.get('Channel_Resistance_Reject',False)),
        'channel_breakout_bull':bool(lat.get('Channel_Breakout_Bull',False)),'channel_breakdown_bear':bool(lat.get('Channel_Breakdown_Bear',False)),
        'asc_triangle':bool(lat.get('Asc_Triangle',False)),'desc_triangle':bool(lat.get('Desc_Triangle',False)),'sym_triangle':bool(lat.get('Sym_Triangle',False)),
        'triangle_breakout_bull':bool(lat.get('Triangle_Breakout_Bull',False)),'triangle_breakdown_bear':bool(lat.get('Triangle_Breakdown_Bear',False)),
        'ma20':_sf(lat.get('MA20')),'ma50':_sf(lat.get('MA50')),'ma200':_sf(lat.get('MA200')),'vp_poc':_sf(lat.get('VP_POC')),'vp_vah':_sf(lat.get('VP_VAH')),'vp_val':_sf(lat.get('VP_VAL')),
        'fib_382':_sf(lat.get('Fib_382')),'fib_50':_sf(lat.get('Fib_50')),'fib_618':_sf(lat.get('Fib_618')),
        'fib_ext_1618_up':_sf(lat.get('Fib_Ext_1618_Up')),'fib_ext_1618_down':_sf(lat.get('Fib_Ext_1618_Down')),
        'fib_382_support':bool(lat.get('Fib_382_Support',False)),'fib_50_support':bool(lat.get('Fib_50_Support',False)),'fib_618_support':bool(lat.get('Fib_618_Support',False)),
        'fib_382_resistance':bool(lat.get('Fib_382_Resistance',False)),'fib_50_resistance':bool(lat.get('Fib_50_Resistance',False)),'fib_618_resistance':bool(lat.get('Fib_618_Resistance',False)),
        'fib_618_breakdown':bool(lat.get('Fib_618_Breakdown',False)),'fib_618_reclaim':bool(lat.get('Fib_618_Reclaim',False)),
        'fib_confluence_buy':bool(lat.get('Fib_Confluence_Buy',False)),'fib_confluence_sell':bool(lat.get('Fib_Confluence_Sell',False)),
        'fib_ext_1618_up_hit':bool(lat.get('Fib_Ext_1618_Up_Hit',False)),'fib_ext_1618_down_hit':bool(lat.get('Fib_Ext_1618_Down_Hit',False)),
        'percent_b':_sf(lat.get('Percent_B'),0.5),'rsi_mfi':_sf(lat.get('RSI_MFI')),'bb_up':_sf(lat.get('BB_Up')),'bb_low':_sf(lat.get('BB_Low')),
        'ema8':_sf(lat.get('EMA8')),'ema21':_sf(lat.get('EMA21')),'ema12':_sf(lat.get('EMA12')),'ema26':_sf(lat.get('EMA26')),
        'vwap':_sf(lat.get('VWAP')),'fixed_vwap':_sf(lat.get('Fixed_VWAP')),
        'envelope_mid':_sf(lat.get('Envelope_Mid')),'envelope_up':_sf(lat.get('Envelope_Up')),'envelope_low':_sf(lat.get('Envelope_Low')),'envelope_percent':_sf(lat.get('Envelope_Percent')),
        'price_channel_up':_sf(lat.get('Price_Channel_Up')),'price_channel_low':_sf(lat.get('Price_Channel_Low')),'price_channel_mid':_sf(lat.get('Price_Channel_Mid')),
        'psar':_sf(lat.get('Parabolic_SAR')),'psar_dir':int(_sf(lat.get('PSAR_Direction'))),
        'fractal_high':bool(lat.get('Fractal_High',False)),'fractal_low':bool(lat.get('Fractal_Low',False)),
        'mass_index':_sf(lat.get('Mass_Index')),'momentum_10':_sf(lat.get('Momentum_10')),'volume_oscillator':_sf(lat.get('Volume_Oscillator')),
        'williams_r':_sf(lat.get('Williams_R')),'disparity_20':_sf(lat.get('Disparity_20')),'disparity_50':_sf(lat.get('Disparity_50')),'disparity_200':_sf(lat.get('Disparity_200')),
        'intraday_intensity':_sf(lat.get('Intraday_Intensity')),'intraday_intensity_index':_sf(lat.get('Intraday_Intensity_Index')),
        'ad_line':_sf(lat.get('AD_Line')),'chaikin_oscillator':_sf(lat.get('Chaikin_Oscillator')),
        'trix':_sf(lat.get('TRIX')),'price_oscillator':_sf(lat.get('Price_Oscillator')),'cci':_sf(lat.get('CCI')),'roc':_sf(lat.get('ROC')),'rmi':_sf(lat.get('RMI')),
        'obv_trend':'rising' if _sf(lat.get('OBV'))>_sf(dc['OBV'].rolling(20).mean().iloc[-1]) else 'falling',
        'obv_slope':_sf(lat.get('OBV_Slope')),'price_slope_5':_sf(lat.get('Price_Slope_5')),'price_slope_5_pct':_sf(lat.get('Price_Slope_5'))*100.0,
        'volume_ratio_20':_sf(lat.get('Volume_Ratio_20'),1),'volume_ratio_50':_sf(lat.get('Volume_Ratio_50'),1),
        'dollar_volume_20':dollar_volume_20,'dollar_volume_z':dollar_volume_z,
        'stock_return_20':stock_return_20,'spy_return_20':spy_return_20,'excess_return_20':excess_return_20,
        'ma20_atr_gap':_sf(lat.get('MA20_ATR_Gap')),'channel_position':channel_position,'supertrend_gap':supertrend_gap,
        'ad_line_z':ad_line_z,'tenkan_gap':tenkan_gap,'kijun_gap':kijun_gap,'cloud_spread':cloud_spread,
        'vp_long_rr':_sf(lat.get('VP_Long_RR'),1),'vp_short_rr':_sf(lat.get('VP_Short_RR'),1),'contrast_notes':str(lat.get('Contrast_Notes','')),
        'smart_money_bearish_div':bool(lat.get('Smart_Money_Bearish_Div',False)),'smart_money_bullish_div':bool(lat.get('Smart_Money_Bullish_Div',False)),
        'blowoff_top_hard':bool(lat.get('Blowoff_Top_Hard',False)),
        'combined_scans':acs,'recent_signals':recent,'derived_signal_events':derived_signal_events,'derived_reason_states':derived_reason_states,
        'strategy_summary':strategy_summary,'strategy_results':strategy_results,'strategy_visible_results':strategy_visible_results,'top_strategy':strategy_summary.get('top_strategy'),
        'high_52w':float(dc['High'].max()),'low_52w':float(dc['Low'].min()),
        'ma20_dist':round((summary_price-_sf(lat.get('MA20',summary_price)))/close_latest*100,2) if summary_price_available and _sf(lat.get('MA20')) else 0,
        'ma50_dist':round((summary_price-_sf(lat.get('MA50',summary_price)))/close_latest*100,2) if summary_price_available and _sf(lat.get('MA50')) else 0,
        'ma200_dist':round((summary_price-_sf(lat.get('MA200',summary_price)))/close_latest*100,2) if summary_price_available and _sf(lat.get('MA200')) else 0}
    return AnalysisViewModel.from_payload(payload).to_dict()


def _trendline_hover(line,label):
    kind='지지 추세선' if line['kind']=='support' else '저항 추세선'
    start_date=line['start_date'].strftime('%Y-%m-%d')
    end_date=line['end_date'].strftime('%Y-%m-%d')
    channel_text=f"<br>채널 예상 가격: {line['channel_projected_price']:.2f}" if 'channel_projected_price' in line else ''
    return (
        f"<b>{translate_chart_text(label)}</b><br>"
        f"유형: {kind}<br>"
        f"기준점: {start_date} ({line['start_price']:.2f}) → {end_date} ({line['end_price']:.2f})<br>"
        f"현재 값: %{{y:.2f}}<br>"
        f"예상 가격: {line['projected_price']:.2f}{channel_text}<extra></extra>"
    )


def _pattern_hover(pattern,boundary_name):
    return (
        f"<b>{localize_pattern_name(pattern['name'])}</b><br>"
        f"경계: {'하단' if boundary_name=='Lower' else '상단'}<br>"
        f"상태: {localize_pattern_state(pattern['state'])}<br>"
        f"기간: {pattern['start_date'].strftime('%Y-%m-%d')} → {pattern['end_date'].strftime('%Y-%m-%d')}<br>"
        f"상단 예상 가격: {pattern['upper_projected_price']:.2f}<br>"
        f"하단 예상 가격: {pattern['lower_projected_price']:.2f}<extra></extra>"
    )


def _configure_primary_chart_legend(fig):
    top_yaxes={None,'y','y1'}
    short_names={
        'Bollinger Band':'BB',
        'Envelope':'Env',
        'Price Channel':'Channel',
        'Fixed VWAP':'F-VWAP',
        'SuperTrend':'SuperT',
        'Hull MA':'HMA',
        'UTBot Stop':'UT Stop',
        'Parabolic SAR':'PSAR',
        'Hull Turn':'H Turn',
        'UTBot Signal':'UT Sig',
        'VuManChu Signal':'VuMC',
        'Trend Overlay':'Trend',
        'Pattern Overlay':'Pattern',
        'VP Overlay':'VP',
        'Fib Overlay':'Fib',
        'Williams Fractal':'Fractal',
        'Strong Buy':'S-Buy',
        'Strong Sell':'S-Sell',
    }

    for trace in fig.data:
        yaxis=getattr(trace,'yaxis',None)
        legendgroup=getattr(trace,'legendgroup',None)
        name=getattr(trace,'name',None)

        if yaxis not in top_yaxes:
            trace.showlegend=False
            continue

        if name == 'Price':
            trace.showlegend=False

        if name in {'20MA','50MA','200MA'}:
            trace.visible=True

        if legendgroup in {'trend_overlay','pattern_overlay'}:
            trace.visible='legendonly'

        if name in short_names:
            trace.name=short_names[name]

    fig.update_layout(
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.01,
            xanchor='left',
            x=0,
            font=dict(size=7,color='#94A3B8'),
            bgcolor='rgba(0,0,0,0)',
            traceorder='grouped',
            groupclick='togglegroup',
            itemsizing='constant',
            tracegroupgap=6,
        )
    )
    return fig


def _localize_chart_figure(fig):
    legend_hover_map = {
        "웨이브트렌드(WT1)": "웨이브트렌드(WT1): %{y:.1f}<br><span style='color:#94A3B8'>과매수/과매도 압력 지표</span><extra></extra>",
        "MACD": "MACD: %{y:.3f}<br><span style='color:#94A3B8'>0 위면 상승 모멘텀이, 0 아래면 하락 모멘텀이 우세합니다.</span><extra></extra>",
        "자금 흐름(MFI)": "자금 흐름(MFI): %{customdata:.1f}<br><span style='color:#94A3B8'>자금 유입과 이탈 강도를 보여줍니다.</span><extra></extra>",
        "스토캐스틱 SlowK": "스토캐스틱 SlowK: %{y:.1f}<br><span style='color:#94A3B8'>20 아래는 과매도, 80 위는 과매수 구간으로 봅니다.</span><extra></extra>",
        "스퀴즈 모멘텀(SqMom)": "스퀴즈 모멘텀(SqMom): %{y:.3f}<br><span style='color:#94A3B8'>스퀴즈 이후 에너지 방향을 보여줍니다.</span><extra></extra>",
    }
    for trace in fig.data:
        if getattr(trace, 'name', None):
            trace.name=localize_legend_name(trace.name)
        if getattr(trace, 'name', '') in legend_hover_map:
            trace.hovertemplate=legend_hover_map[trace.name]
        elif getattr(trace,'hovertemplate',None):
            trace.hovertemplate=translate_chart_text(trace.hovertemplate)
        text_value=getattr(trace,'text',None)
        if text_value is not None:
            if isinstance(text_value,(list,tuple,np.ndarray,pd.Series)):
                trace.text=[translate_chart_text(v) for v in list(text_value)]
            else:
                trace.text=translate_chart_text(text_value)
    for ann in getattr(fig.layout,'annotations',[]) or []:
        if getattr(ann,'text',None):
            translated=translate_chart_text(ann.text)
            ann.text=localize_subplot_title(translated)
    return fig


def build_indicator_lab_chart(dc,ticker):
    fig=_build_indicator_lab_chart_legacy(dc,ticker)
    return _localize_chart_figure(fig)


def _build_unified_timeline_chart(dc,ticker):
    mac={20:'#f1c40f',50:'#e74c3c',200:'#2ecc71'}
    fig=make_subplots(
        rows=25,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.017,
        row_heights=[.22,.04,.06,.06,.06,.06,.06,.05,.05,.05,.05,.062,.055,.055,.055,.055,.062,.062,.055,.06,.06,.06,.062,.08,.1],
        subplot_titles=(
            ticker,
            "Vol",
            "WaveTrend",
            "MACD",
            "Money Flow",
            "Stoch Slow",
            "Squeeze Mom",
            "Reversal Pack",
            "Momentum Pack",
            "Flow Pack",
            "ADX / DMI",
            "BB / VWAP Position",
            "RSI / Stoch RSI",
            "CMF / OBV / AD Line",
            "Ichimoku / Mass",
            "Volatility / Liquidity",
            "RS / Acceleration",
            "Position / Structure",
            "HMA / UTBot",
            "VP / POC / RR",
            "Fib Structure",
            "MA / EMA Alignment",
            "Trendline / Pattern Structure",
            "Objective Engine",
            "5-Committee Ensemble",
        ),
    )

    idx=dc.index
    hover=_build_candle_hover(dc)
    fig.add_trace(go.Candlestick(x=idx,open=dc['Open'],high=dc['High'],low=dc['Low'],close=dc['Close'],name="Price",increasing_line_color=SOFT_GREEN,decreasing_line_color=SOFT_RED,increasing_fillcolor=SOFT_GREEN_FILL,decreasing_fillcolor=SOFT_RED_FILL,text=hover,hoverinfo='text',hoverlabel=dict(bgcolor='rgba(11,14,20,.97)',bordercolor='#334155',font=dict(size=11,family=PLOTLY_FONT_FAMILY,color='#F1F5F9'),align='left'),showlegend=False),row=1,col=1)
    for mp in [20,50,200]:
        fig.add_trace(go.Scatter(x=idx,y=dc[f'MA{mp}'],line=dict(color=mac[mp],width=1.2),name=f'{mp}MA',legendgroup='moving_average',hoverinfo='skip',showlegend=True,visible=True),row=1,col=1)
    for ep,color in [(12,'#22D3EE'),(26,'#A78BFA')]:
        fig.add_trace(go.Scatter(x=idx,y=dc[f'EMA{ep}'],line=dict(color=color,width=1.2,dash='dot'),name=f'EMA{ep}',legendgroup='ema_overlay',hoverinfo='skip',showlegend=True,visible='legendonly'),row=1,col=1)
    for trace_idx,(mask,color) in enumerate([(dc['ST_Direction']==1,SOFT_GREEN),(dc['ST_Direction']==-1,SOFT_RED)],start=1):
        fig.add_trace(go.Scatter(x=idx,y=dc['SuperTrend'].where(mask),line=dict(color=color,width=2),name='SuperTrend',legendgroup='supertrend',connectgaps=False,hoverinfo='skip',showlegend=(trace_idx==1),visible='legendonly'),row=1,col=1)
    fig.add_trace(go.Scatter(x=idx,y=dc['BB_Up'],line=dict(color='#475569',width=1,dash='dot'),name='Bollinger Band',legendgroup='bollinger_band',hoverinfo='skip',showlegend=True,visible='legendonly'),row=1,col=1)
    fig.add_trace(go.Scatter(x=idx,y=dc['BB_Low'],line=dict(color='#475569',width=1,dash='dot'),legendgroup='bollinger_band',fill='tonexty',fillcolor='rgba(71,85,105,.06)',hoverinfo='skip',showlegend=False,visible='legendonly'),row=1,col=1)
    fig.add_trace(go.Scatter(x=idx,y=dc['Envelope_Up'],line=dict(color='rgba(250,204,21,.9)',width=1,dash='dot'),name='Envelope',legendgroup='envelope_overlay',hoverinfo='skip',showlegend=True,visible='legendonly'),row=1,col=1)
    fig.add_trace(go.Scatter(x=idx,y=dc['Envelope_Low'],line=dict(color='rgba(250,204,21,.9)',width=1,dash='dot'),legendgroup='envelope_overlay',fill='tonexty',fillcolor='rgba(250,204,21,.05)',hoverinfo='skip',showlegend=False,visible='legendonly'),row=1,col=1)
    fig.add_trace(go.Scatter(x=idx,y=dc['Price_Channel_Up'],line=dict(color='rgba(248,113,113,.85)',width=1,dash='dash'),name='Price Channel',legendgroup='price_channel',hoverinfo='skip',showlegend=True,visible='legendonly'),row=1,col=1)
    fig.add_trace(go.Scatter(x=idx,y=dc['Price_Channel_Low'],line=dict(color='rgba(74,222,128,.85)',width=1,dash='dash'),legendgroup='price_channel',fill='tonexty',fillcolor='rgba(148,163,184,.05)',hoverinfo='skip',showlegend=False,visible='legendonly'),row=1,col=1)
    fig.add_trace(go.Scatter(x=idx,y=dc['VWAP'],line=dict(color='#38BDF8',width=1.4),name='VWAP',legendgroup='vwap_overlay',hoverinfo='skip',showlegend=True,visible='legendonly'),row=1,col=1)
    fig.add_trace(go.Scatter(x=idx,y=dc['Fixed_VWAP'],line=dict(color='#F59E0B',width=1.4,dash='dot'),name='Fixed VWAP',legendgroup='vwap_overlay',hoverinfo='skip',showlegend=True,visible='legendonly'),row=1,col=1)
    hma=dc.get('HMA')
    if hma is not None:
        hma_up=dc.get('HMA_Rising',pd.Series(False,index=idx)).fillna(False)
        fig.add_trace(go.Scatter(x=idx,y=hma.where(hma_up),line=dict(color=SOFT_GREEN,width=2.5),name='Hull MA',legendgroup='hull_ma',connectgaps=False,hoverinfo='skip',showlegend=True,visible=True),row=1,col=1)
        fig.add_trace(go.Scatter(x=idx,y=hma.where(~hma_up),line=dict(color=SOFT_RED,width=2.5),legendgroup='hull_ma',connectgaps=False,hoverinfo='skip',showlegend=False,visible=True),row=1,col=1)
    if 'UTBot_Stop' in dc.columns:
        ut_buy=dc['UTBot_Dir']==1
        ut_sell=dc['UTBot_Dir']==-1
        fig.add_trace(go.Scatter(x=idx,y=dc['UTBot_Stop'].where(ut_buy),line=dict(color='rgba(126,216,182,.5)',width=2,dash='dot'),name='UTBot Stop',legendgroup='utbot_stop',connectgaps=False,hoverinfo='skip',showlegend=True,visible='legendonly'),row=1,col=1)
        fig.add_trace(go.Scatter(x=idx,y=dc['UTBot_Stop'].where(ut_sell),line=dict(color='rgba(243,165,165,.5)',width=2,dash='dot'),legendgroup='utbot_stop',connectgaps=False,hoverinfo='skip',showlegend=False,visible='legendonly'),row=1,col=1)
    fig.add_trace(go.Scatter(x=idx,y=dc['Parabolic_SAR'],mode='markers',marker=dict(size=5,color=np.where(dc['PSAR_Direction']>=0,'rgba(74,222,128,.95)','rgba(248,113,113,.95)').tolist(),symbol='circle'),name='Parabolic SAR',legendgroup='psar_overlay',hovertemplate="PSAR:%{y:.2f}<extra></extra>",showlegend=True,visible='legendonly'),row=1,col=1)
    for sn,color,symbol,size,label,legendgroup,showlegend,visible in [
        ('Hull_Turn_Bull',SOFT_GREEN,'circle',8,'Hull Turn','hull_signal',True,True),
        ('Hull_Turn_Bear',SOFT_RED,'circle',8,'Hull Turn','hull_signal',False,True),
        ('UTBot_Buy',SOFT_GREEN,'triangle-up',12,'UTBot Signal','utbot_signal',True,'legendonly'),
        ('UTBot_Sell',SOFT_RED,'triangle-down',12,'UTBot Signal','utbot_signal',False,'legendonly'),
        ('VuManChu_Bull',SOFT_GREEN,'diamond',12,'VuManChu Signal','vumanchu_signal',True,'legendonly'),
        ('VuManChu_Bear',SOFT_RED,'diamond',12,'VuManChu Signal','vumanchu_signal',False,'legendonly'),
    ]:
        yoff=dc['Low']-dc['ATR']*(0.8 if 'Hull' in sn else 1.2 if 'UTBot' in sn else 1.8) if 'Bull' in sn or 'Buy' in sn else dc['High']+dc['ATR']*(0.8 if 'Hull' in sn else 1.2 if 'UTBot' in sn else 1.8)
        _sig_marker(fig,dc,sn,1,yoff,color,symbol,size,label,legendgroup=legendgroup,showlegend=showlegend,visible=visible)
    sb,ss=_collect_strong_markers(dc)
    _add_trendline_overlays(fig,dc,max_per_side=2,default_visible='legendonly')
    _add_pattern_overlay(fig,dc,_detect_active_pattern(dc),default_visible='legendonly')
    _add_volume_profile_overlay(fig,dc,default_visible='legendonly')
    _add_fibonacci_overlay(fig,dc,default_visible='legendonly')
    if sb.any():
        sr=dc[sb]
        yv=sr['Low']-sr['ATR']*2
        ht=[]
        for bi in sr.index:
            br=[SIGNAL_REGISTRY.get(s,COMBINED_SCAN_REGISTRY.get(s,{})).get('kor',s) for s in STRONG_BUY_SIGS if s in dc.columns and dc.loc[bi,s]]
            ht.append(f"<b>Strong Buy</b><br><span style='color:#94A3B8'>{', '.join(br[:5]) or 'Multiple bullish signals'}</span><br>{bi.strftime('%Y-%m-%d')}")
        fig.add_trace(go.Scatter(x=sr.index,y=yv,mode='markers',marker=dict(symbol='star',size=8,color='#E8C56C',line=dict(width=2,color=SOFT_GREEN),opacity=.95),name='Strong Buy',legendgroup='strong_buy',hovertemplate="%{text}<extra></extra>",text=ht,showlegend=True,visible='legendonly'),row=1,col=1)
    if ss.any():
        sr=dc[ss]
        yv=sr['High']+sr['ATR']*2
        ht=[]
        for bi in sr.index:
            br=[SIGNAL_REGISTRY.get(s,COMBINED_SCAN_REGISTRY.get(s,{})).get('kor',s) for s in STRONG_SELL_SIGS if s in dc.columns and dc.loc[bi,s]]
            ht.append(f"<b>Strong Sell</b><br><span style='color:#94A3B8'>{', '.join(br[:5]) or 'Multiple bearish signals'}</span><br>{bi.strftime('%Y-%m-%d')}")
        fig.add_trace(go.Scatter(x=sr.index,y=yv,mode='markers',marker=dict(symbol='star',size=8,color='#E8C56C',line=dict(width=2,color=SOFT_RED),opacity=.95),name='Strong Sell',legendgroup='strong_sell',hovertemplate="%{text}<extra></extra>",text=ht,showlegend=True,visible='legendonly'),row=1,col=1)
    if dc.get('Fractal_Low',pd.Series(False,index=idx)).fillna(False).any():
        lows=dc[dc['Fractal_Low'].fillna(False)]
        fig.add_trace(go.Scatter(x=lows.index,y=lows['Low']-(lows['ATR']*0.9),mode='markers',marker=dict(symbol='triangle-up',size=8,color='#22C55E',line=dict(width=1,color='#E2E8F0')),name='Williams Fractal',legendgroup='fractal_overlay',hovertemplate="Fractal Low<br>%{x|%Y-%m-%d}<extra></extra>",showlegend=True,visible='legendonly'),row=1,col=1)
    if dc.get('Fractal_High',pd.Series(False,index=idx)).fillna(False).any():
        highs=dc[dc['Fractal_High'].fillna(False)]
        fig.add_trace(go.Scatter(x=highs.index,y=highs['High']+(highs['ATR']*0.9),mode='markers',marker=dict(symbol='triangle-down',size=8,color='#EF4444',line=dict(width=1,color='#E2E8F0')),name='Williams Fractal',legendgroup='fractal_overlay',hovertemplate="Fractal High<br>%{x|%Y-%m-%d}<extra></extra>",showlegend=False,visible='legendonly'),row=1,col=1)

    bb=dc['Close']<dc['Open']
    fig.add_trace(go.Bar(x=idx,y=dc['Volume'],marker_color=np.where(bb,'rgba(243,165,165,.5)','rgba(126,216,182,.5)').tolist(),name="Vol",opacity=.8,hoverinfo='skip',showlegend=False),row=2,col=1)

    wt1=dc.get('WT1',pd.Series(0,index=idx))
    wt2=dc.get('WT2',pd.Series(0,index=idx))
    wd=wt1-wt2
    wt1_state=_signed_state(wt1,weak=6,strong=40,pos='상승 모멘텀 우위',neg='하락 모멘텀 우위',neutral='중립 / 전환 구간',strong_pos='과열권 근처의 강한 상승 모멘텀',strong_neg='과매도권 근처의 강한 하락 모멘텀')
    fig.add_trace(go.Scatter(x=idx,y=wt1,line=dict(color=SOFT_GREEN,width=2),name="WT1",text=wt1_state,hovertemplate=_indicator_hover("WT1","값 %{y:.1f}","WaveTrend가 위쪽이면 단기 모멘텀이 강하고, 아래쪽이면 약해집니다.",extra_line="현재 해석: %{text}")),row=3,col=1)
    fig.add_trace(go.Scatter(x=idx,y=wt2,line=dict(color=SOFT_RED,width=1.5,dash='dot'),name="WT2",hoverinfo='skip',showlegend=False),row=3,col=1)
    fig.add_trace(go.Bar(x=idx,y=wd,marker_color=np.where(wd>=0,'rgba(126,216,182,.25)','rgba(243,165,165,.25)').tolist(),hoverinfo='skip',showlegend=False),row=3,col=1)
    for y_,c_,d_ in [(OB1,'#FF5252','solid'),(0,'#475569','dot'),(OS1,'#4FC3F7','solid')]:
        fig.add_hline(y=y_,line_dash=d_,line_color=c_,line_width=1,row=3,col=1)
    for sn,color,symbol,size,label in [('Gold_Dot','#FFD700','star',14,'Gold Dot'),('Green_Dot_T1','#00E676','circle',10,'Green Dot'),('Green_Dot_T2','#69F0AE','circle',8,'Green Dot'),('Blood_Diamond','#DC143C','star',14,'Blood Diamond'),('Red_Dot_T1','#FF1744','circle',10,'Red Dot'),('Red_Dot_T2','#FF5252','circle',8,'Red Dot'),('Bull_Divergence','#AA00FF','triangle-up',10,'Bull Div'),('Bear_Divergence','#AA00FF','triangle-down',10,'Bear Div'),('RSI_Bull_Divergence','#CE93D8','triangle-up',8,'RSI Bull Div'),('RSI_Bear_Divergence','#CE93D8','triangle-down',8,'RSI Bear Div')]:
        _sig_marker(fig,dc,sn,3,wt1,color,symbol,size,label)

    macd_line=dc.get('MACD_Line',pd.Series(0,index=idx))
    macd_signal=dc.get('MACD_Signal',pd.Series(0,index=idx))
    macd_hist=dc.get('MACD_Hist',pd.Series(0,index=idx))
    macd_state=_macd_state(macd_line,macd_hist)
    fig.add_trace(go.Scatter(x=idx,y=macd_line,line=dict(color='#29B6F6',width=1.5),name="MACD",text=macd_state,hovertemplate=_indicator_hover("MACD","값 %{y:.3f}","0선과 히스토그램 방향을 함께 보면 추세 강화인지 둔화인지 읽기 쉽습니다.",extra_line="현재 해석: %{text}")),row=4,col=1)
    fig.add_trace(go.Scatter(x=idx,y=macd_signal,line=dict(color='#FFA726',width=1.5),name='Signal',hoverinfo='skip',showlegend=False),row=4,col=1)
    fig.add_trace(go.Bar(x=idx,y=macd_hist,marker_color=np.where(macd_hist>=0,'#26A69A','#EF5350').tolist(),opacity=.7,hoverinfo='skip',showlegend=False),row=4,col=1)
    fig.add_hline(y=0,line_color="#475569",line_width=1,row=4,col=1)
    for sn,color,symbol,size,label in [('MACD_Cross_Buy','#00E676','triangle-up',10,'MACD Cross'),('MACD_Cross_Sell','#FF1744','triangle-down',10,'MACD Cross'),('MACD_Zero_Cross_Buy','#4CAF50','diamond',8,'MACD Zero'),('MACD_Zero_Cross_Sell','#E57373','diamond',8,'MACD Zero')]:
        _sig_marker(fig,dc,sn,4,macd_line,color,symbol,size,label)

    mfi=dc.get('MFI',pd.Series(50,index=idx))
    mfi_centered=mfi-50
    rsi_mfi=dc.get('RSI_MFI',pd.Series(0,index=idx))
    fig.add_trace(go.Bar(x=idx,y=rsi_mfi,marker_color=np.where(rsi_mfi>=0,'rgba(0,230,118,.35)','rgba(255,23,68,.35)').tolist(),opacity=.7,hoverinfo='skip',showlegend=False),row=5,col=1)
    mfi_state=_oscillator_state(mfi,oversold=30,overbought=70,extreme_oversold=20,extreme_overbought=80,oversold_text='매도 압력 우위 / 눌림 구간',neutral='중립 수급 구간',overbought_text='매수 압력 우위 / 과열 접근',extreme_oversold_text='과매도권 반등 후보',extreme_overbought_text='과열권 경계')
    fig.add_trace(go.Scatter(x=idx,y=mfi_centered,line=dict(color='#AB47BC',width=2.5),name="MFI",customdata=mfi.values,text=mfi_state,hovertemplate=_indicator_hover("MFI","값 %{customdata:.1f}","거래량이 실린 매수/매도 압력의 균형을 보여줍니다.",extra_line="현재 해석: %{text}")),row=5,col=1)
    fig.add_hrect(y0=30,y1=50,fillcolor="rgba(239,68,68,.08)",line_width=0,row=5,col=1)
    fig.add_hrect(y0=-50,y1=-30,fillcolor="rgba(16,185,129,.08)",line_width=0,row=5,col=1)
    for y_,c_,d_ in [(30,'#FF5252','dash'),(-30,'#4FC3F7','dash'),(0,'#475569','solid')]:
        fig.add_hline(y=y_,line_dash=d_,line_color=c_,line_width=1,row=5,col=1)
    for sn,color,symbol,size,label in [('MF_Cross_Bull','#00E676','triangle-up',10,'MF Cross'),('MF_Cross_Bear','#FF1744','triangle-down',10,'MF Cross'),('MF_Bull_Div','#7C4DFF','diamond',10,'MF Bull Div'),('MF_Bear_Div','#E040FB','diamond',10,'MF Bear Div'),('CMF_Bull','#00BCD4','circle',8,'CMF'),('CMF_Bear','#FF5722','circle',8,'CMF')]:
        _sig_marker(fig,dc,sn,5,mfi_centered,color,symbol,size,label)

    slowk=dc.get('SlowK',pd.Series(50,index=idx))
    slowd=dc.get('SlowD',pd.Series(50,index=idx))
    slowk_state=_oscillator_state(slowk,oversold=20,overbought=80,extreme_oversold=10,extreme_overbought=90,oversold_text='약세권 / 눌림 구간',neutral='중립권',overbought_text='강세권 / 과열 접근',extreme_oversold_text='극단 과매도권',extreme_overbought_text='극단 과열권')
    fig.add_trace(go.Scatter(x=idx,y=slowk,line=dict(color='#00BCD4',width=2),name="SlowK",text=slowk_state,hovertemplate=_indicator_hover("SlowK","값 %{y:.1f}","스토캐스틱은 최근 범위 안에서 현재가 위치를 보여줍니다.",extra_line="현재 해석: %{text}")),row=6,col=1)
    fig.add_trace(go.Scatter(x=idx,y=slowd,line=dict(color='#FF9800',width=1.5,dash='dot'),name='SlowD',hoverinfo='skip',showlegend=False),row=6,col=1)
    fig.add_hrect(y0=80,y1=100,fillcolor="rgba(239,68,68,.08)",line_width=0,row=6,col=1)
    fig.add_hrect(y0=0,y1=20,fillcolor="rgba(16,185,129,.08)",line_width=0,row=6,col=1)
    for y_,c_,d_ in [(80,'#FF5252','dash'),(20,'#4FC3F7','dash'),(50,'#475569','dot')]:
        fig.add_hline(y=y_,line_dash=d_,line_color=c_,line_width=1,row=6,col=1)
    for sn,color,symbol,size,label in [('StochSlow_Cross_Buy','#00E676','triangle-up',12,'Stoch Cross'),('StochSlow_Cross_Sell','#FF1744','triangle-down',12,'Stoch Cross'),('Stoch_Oversold','#69F0AE','square',6,'Stoch OS'),('Stoch_Overbought','#FF5252','square',6,'Stoch OB')]:
        _sig_marker(fig,dc,sn,6,slowk,color,symbol,size,label)

    sqmom=dc.get('Squeeze_Momentum',pd.Series(0,index=idx))
    sq_rising=dc.get('Squeeze_Mom_Rising',pd.Series(False,index=idx)).fillna(False)
    sq_positive=dc.get('Squeeze_Mom_Positive',pd.Series(False,index=idx)).fillna(False)
    sq_on=dc.get('Squeeze_On',pd.Series(False,index=idx)).fillna(False)
    sq_colors=np.where(sq_positive&sq_rising,'#00E676',np.where(sq_positive&~sq_rising,'#69F0AE',np.where(~sq_positive&sq_rising,'#FF8A80','#FF1744')))
    sq_state=_squeeze_state(sqmom,sq_on,sq_positive,sq_rising)
    fig.add_trace(go.Bar(x=idx,y=sqmom,marker_color=sq_colors.tolist(),name="SqMom",opacity=.85,text=sq_state,hovertemplate=_indicator_hover("SqMom","값 %{y:.3f}","압축이 끝난 뒤 에너지가 어느 방향으로 풀리는지 보여줍니다.",extra_line="현재 해석: %{text}")),row=7,col=1)
    fig.add_hline(y=0,line_color="#475569",line_width=1,row=7,col=1)
    if sq_on.any():
        sq_min=float(sqmom.min()) if len(sqmom)>0 else -0.1
        sq_y=sq_min*1.1 if sq_min<0 else -0.05
        fig.add_trace(go.Scatter(x=idx[sq_on],y=[sq_y]*int(sq_on.sum()),mode='markers',marker=dict(symbol='circle',size=5,color='#000',line=dict(width=1,color='#FFC107'),opacity=.9),name='Squeeze On',hovertemplate="Squeeze On<br>%{x|%Y-%m-%d}<extra></extra>"),row=7,col=1)
    for sn,color,symbol,size,label in [('Squeeze_Fire_Buy','#00FFFF','star-diamond',14,'Sq Fire'),('Squeeze_Fire_Sell','#FF6600','star-diamond',14,'Sq Fire'),('Squeeze_Mom_Cross_Up','#00E676','diamond',10,'Sq Mom'),('Squeeze_Mom_Cross_Down','#FF1744','diamond',10,'Sq Mom')]:
        _sig_marker(fig,dc,sn,7,sqmom,color,symbol,size,label)

    williams_r=(dc.get('Williams_R',pd.Series(-50,index=idx))+100).clip(0,100)
    rmi=dc.get('RMI',pd.Series(50,index=idx)).clip(0,100)
    cci=dc.get('CCI',pd.Series(0,index=idx))
    cci_scaled=(50+cci.clip(-200,200)/4).clip(0,100)
    fig.add_trace(go.Bar(x=idx,y=cci_scaled-50,base=50,marker_color=np.where(cci>=0,'rgba(248,113,113,.30)','rgba(74,222,128,.30)').tolist(),name='CCI Band',hovertemplate=_indicator_hover("CCI Band","정규화 값: %{y:+.1f}","CCI가 -100 아래면 과매도, +100 위면 과열 가능성이 커집니다.","CCI: %{customdata:.0f}"),customdata=cci.values,showlegend=False),row=8,col=1)
    wr_state=_oscillator_state(williams_r,oversold=20,overbought=80,extreme_oversold=10,extreme_overbought=90,oversold_text='약세권 / 눌림 구간',neutral='중립권',overbought_text='강세권 / 과열 접근',extreme_oversold_text='극단 과매도권',extreme_overbought_text='극단 과열권')
    fig.add_trace(go.Scatter(x=idx,y=williams_r,line=dict(color='#38BDF8',width=2),name='Williams %R',text=wr_state,hovertemplate=_indicator_hover("Williams %R","표시 값 %{y:.1f}","20 아래는 과매도권 반등 후보, 80 위는 과열권 경계 구간입니다.","원래 값 %{customdata:.0f}",extra_line="현재 해석: %{text}"),customdata=dc.get('Williams_R',pd.Series(-50,index=idx)).values),row=8,col=1)
    fig.add_trace(go.Scatter(x=idx,y=rmi,line=dict(color='#F472B6',width=1.8,dash='dot'),name='RMI',hovertemplate=_indicator_hover("RMI","값: %{y:.1f}","추세형 RSI로, 50 위는 상승 우위, 50 아래는 약세 우위로 읽습니다.")),row=8,col=1)
    if dc.get('Fractal_Low',pd.Series(False,index=idx)).fillna(False).any():
        lows=dc[dc['Fractal_Low'].fillna(False)]
        fig.add_trace(go.Scatter(x=lows.index,y=(lows['Williams_R']+100).clip(0,100),mode='markers',marker=dict(symbol='diamond',size=8,color='#22C55E',line=dict(width=1,color='#E2E8F0')),name='Fractal Low',hovertemplate=_indicator_hover("Fractal Low","날짜: %{x|%Y-%m-%d}","저점 프랙탈이 잡힌 자리로, 과매도권 반등 후보 구간을 알려줍니다."),showlegend=False),row=8,col=1)
    if dc.get('Fractal_High',pd.Series(False,index=idx)).fillna(False).any():
        highs=dc[dc['Fractal_High'].fillna(False)]
        fig.add_trace(go.Scatter(x=highs.index,y=(highs['Williams_R']+100).clip(0,100),mode='markers',marker=dict(symbol='diamond',size=8,color='#EF4444',line=dict(width=1,color='#E2E8F0')),name='Fractal High',hovertemplate=_indicator_hover("Fractal High","날짜: %{x|%Y-%m-%d}","고점 프랙탈이 잡힌 자리로, 과열권 되돌림 후보 구간을 알려줍니다."),showlegend=False),row=8,col=1)
    for y_,clr in [(20,'#38BDF8'),(50,'#64748B'),(80,'#F87171')]:
        fig.add_hline(y=y_,line_dash='dash',line_color=clr,line_width=1,row=8,col=1)

    roc=dc.get('ROC',pd.Series(0,index=idx))
    trix=dc.get('TRIX',pd.Series(0,index=idx))
    price_osc=dc.get('Price_Oscillator',pd.Series(0,index=idx))
    fig.add_trace(go.Bar(x=idx,y=roc,marker_color=np.where(roc>=0,'rgba(34,197,94,.65)','rgba(239,68,68,.65)').tolist(),name='ROC',hovertemplate=_indicator_hover("ROC","값: %{y:+.2f}","변화율이 0 위면 최근 속도가 상승 쪽, 0 아래면 하락 쪽으로 기웁니다."),showlegend=False),row=9,col=1)
    fig.add_trace(go.Scatter(x=idx,y=trix,line=dict(color='#F59E0B',width=2),name='TRIX',hovertemplate=_indicator_hover("TRIX","값: %{y:+.3f}","완만한 추세 모멘텀 지표로, 0선 위 복귀는 추세 회복 확인에 도움됩니다.")),row=9,col=1)
    fig.add_trace(go.Scatter(x=idx,y=price_osc,line=dict(color='#A78BFA',width=1.8,dash='dot'),name='Price Osc',hovertemplate=_indicator_hover("Price Oscillator","값: %{y:+.2f}","단기 평균이 장기 평균보다 얼마나 강한지 보여주는 가격 모멘텀입니다.")),row=9,col=1)
    fig.add_hline(y=0,line_color="#64748B",line_width=1,row=9,col=1)

    volume_osc=dc.get('Volume_Oscillator',pd.Series(0,index=idx))
    chaikin=dc.get('Chaikin_Oscillator',pd.Series(0,index=idx))
    intensity=dc.get('Intraday_Intensity_Index',pd.Series(0,index=idx))
    vol_osc_state=_signed_state(volume_osc,weak=5,strong=15,pos='거래량 유입 우위',neg='거래량 위축 / 매도 우위',neutral='평균 수준 거래량',strong_pos='강한 거래량 확장',strong_neg='강한 거래량 축소 / 매도 우세')
    fig.add_trace(go.Bar(x=idx,y=volume_osc,marker_color=np.where(volume_osc>=0,'rgba(16,185,129,.68)','rgba(244,63,94,.68)').tolist(),name='Vol Osc',text=vol_osc_state,hovertemplate=_indicator_hover("Volume Oscillator","값 %{y:+.2f}","거래량이 평소보다 늘어나는지 줄어드는지 보여줘 움직임 신뢰도를 판단할 때 씁니다.",extra_line="현재 해석: %{text}")),row=10,col=1)
    fig.add_trace(go.Scatter(x=idx,y=chaikin,line=dict(color='#22D3EE',width=1.8),name='Chaikin',hovertemplate=_indicator_hover("Chaikin Oscillator","값: %{y:+.2f}","자금 유입이 강하면 플러스, 분산이 강하면 마이너스로 기울기 쉽습니다.")),row=10,col=1)
    fig.add_trace(go.Scatter(x=idx,y=intensity,line=dict(color='#F472B6',width=1.8,dash='dot'),name='Intensity',hovertemplate=_indicator_hover("Intraday Intensity","값: %{y:+.2f}","당일 종가가 고가 쪽에 붙을수록 매수 압력, 저가 쪽이면 매도 압력으로 읽습니다.")),row=10,col=1)
    fig.add_hline(y=0,line_color="#64748B",line_width=1,row=10,col=1)

    adx=dc.get('ADX',pd.Series(0,index=idx))
    plus_di=dc.get('Plus_DI',pd.Series(0,index=idx))
    minus_di=dc.get('Minus_DI',pd.Series(0,index=idx))
    adx_state=_adx_state(adx,plus_di,minus_di)
    fig.add_trace(go.Scatter(x=idx,y=adx,line=dict(color='#FBBF24',width=2),name='ADX',text=adx_state,hovertemplate=_indicator_hover("ADX","값 %{y:.1f}","20 이하는 횡보 가능성, 25 이상은 추세가 살아나는 구간으로 많이 봅니다.",extra_line="현재 해석: %{text}")),row=11,col=1)
    fig.add_trace(go.Scatter(x=idx,y=plus_di,line=dict(color='#22C55E',width=1.8),name='+DI',hovertemplate=_indicator_hover("+DI","값: %{y:.1f}","상승 방향 힘의 크기입니다. -DI 위에 있으면 강세 우위를 뜻합니다.")),row=11,col=1)
    fig.add_trace(go.Scatter(x=idx,y=minus_di,line=dict(color='#EF4444',width=1.8,dash='dot'),name='-DI',hovertemplate=_indicator_hover("-DI","값: %{y:.1f}","하락 방향 힘의 크기입니다. +DI 위에 있으면 약세 우위를 뜻합니다.")),row=11,col=1)
    fig.add_hline(y=20,line_color='rgba(148,163,184,.35)',line_dash='dot',line_width=1,row=11,col=1)
    fig.add_hline(y=25,line_color='rgba(251,191,36,.35)',line_dash='dash',line_width=1,row=11,col=1)
    for sn,color,symbol,size,label in [('DMI_Cross_Bull','#22C55E','triangle-up',10,'DMI Bull'),('DMI_Cross_Bear','#EF4444','triangle-down',10,'DMI Bear'),('ADX_New_Uptrend','#84CC16','arrow-up',11,'ADX Trend Up'),('ADX_New_Downtrend','#F97316','arrow-down',11,'ADX Trend Down'),('ADX_Momentum_Buy','#A3E635','diamond',9,'ADX Ignite'),('ADX_Momentum_Sell','#FB7185','diamond',9,'ADX Fade')]:
        _sig_marker(fig,dc,sn,11,adx,color,symbol,size,label)

    percent_b_centered=(dc.get('Percent_B',pd.Series(0.5,index=idx))-0.5)*100
    bb_width_scaled=dc.get('BB_Width',pd.Series(0,index=idx))*100
    vwap_osc=dc.get('VWAP_Osc',pd.Series(0,index=idx))
    disparity_20=dc.get('Disparity_20',pd.Series(0,index=idx))
    disparity_50=dc.get('Disparity_50',pd.Series(0,index=idx))
    fig.add_trace(go.Bar(x=idx,y=bb_width_scaled,marker_color='rgba(148,163,184,.38)',name='BB Width',hovertemplate=_indicator_hover("BB Width","표시 값: %{y:.2f}","밴드 폭이 좁아지면 압축, 넓어지면 변동성 확대 구간으로 읽습니다."),showlegend=False),row=12,col=1)
    percent_b_state=_level_state(percent_b_centered,near=10,strong=25,above='상단 밴드 쪽 우위',below='하단 밴드 쪽 약세',near_text='밴드 중심 부근 / 방향 대기',strong_above='상단 밴드 근접 / 과열 경계',strong_below='하단 밴드 근접 / 눌림 구간')
    fig.add_trace(go.Scatter(x=idx,y=percent_b_centered,line=dict(color='#38BDF8',width=2),name='%B (centered)',text=percent_b_state,hovertemplate=_indicator_hover("%B","중심 대비 %{y:+.1f}","0 위면 밴드 중단보다 위, +25 이상은 상단 근접, -25 이하는 하단 근접입니다.","원래 값 %{customdata:.2f}",extra_line="현재 해석: %{text}"),customdata=dc.get('Percent_B',pd.Series(0.5,index=idx)).values),row=12,col=1)
    fig.add_trace(go.Scatter(x=idx,y=vwap_osc,line=dict(color='#F59E0B',width=1.8),name='VWAP Osc',hovertemplate=_indicator_hover("VWAP Osc","값: %{y:+.2f}","VWAP 위면 단기 평균 매수 우위, 아래면 단기 평균 매도 우위로 해석합니다.")),row=12,col=1)
    fig.add_trace(go.Scatter(x=idx,y=disparity_20,line=dict(color='#A78BFA',width=1.8),name='Disparity 20',hovertemplate=_indicator_hover("Disparity 20","값: %{y:+.2f}","20일선에서 얼마나 멀어졌는지 보여주며 과열 / 이격을 확인할 때 씁니다.")),row=12,col=1)
    fig.add_trace(go.Scatter(x=idx,y=disparity_50,line=dict(color='#F472B6',width=1.4,dash='dot'),name='Disparity 50',hovertemplate=_indicator_hover("Disparity 50","값: %{y:+.2f}","50일선 기준 이격으로, 중기 과열이나 눌림 깊이를 보는 데 유용합니다.")),row=12,col=1)
    fig.add_hline(y=0,line_color="#64748B",line_width=1,row=12,col=1)
    for y_,clr in [(-25,'rgba(56,189,248,.35)'),(25,'rgba(248,113,113,.35)')]:
        fig.add_hline(y=y_,line_color=clr,line_dash='dash',line_width=1,row=12,col=1)
    for sn,color,symbol,size,label in [('VWAP_Bounce_Buy','#22D3EE','triangle-up',10,'VWAP Bounce'),('VWAP_Reject_Sell','#F97316','triangle-down',10,'VWAP Reject')]:
        _sig_marker(fig,dc,sn,12,percent_b_centered,color,symbol,size,label)

    rsi=dc.get('RSI',pd.Series(50,index=idx))
    stoch_rsi_k=dc.get('StochK',pd.Series(50,index=idx))
    stoch_rsi_d=dc.get('StochD',pd.Series(50,index=idx))
    rsi_state=_oscillator_state(rsi,oversold=30,overbought=70,extreme_oversold=20,extreme_overbought=80,oversold_text='약세권 / 눌림 구간',neutral='중립권',overbought_text='강세권 / 과열 접근',extreme_oversold_text='과매도권 반등 후보',extreme_overbought_text='과열권 경계')
    fig.add_trace(go.Scatter(x=idx,y=rsi,line=dict(color='#F97316',width=2),name='RSI',text=rsi_state,hovertemplate=_indicator_hover("RSI","값 %{y:.1f}","70 위는 과열, 30 아래는 과매도 후보로 많이 보지만 추세에서는 오래 머물 수 있습니다.",extra_line="현재 해석: %{text}")),row=13,col=1)
    fig.add_trace(go.Scatter(x=idx,y=stoch_rsi_k,line=dict(color='#22D3EE',width=1.8),name='Stoch RSI K',hovertemplate=_indicator_hover("Stoch RSI K","값: %{y:.1f}","RSI의 속도를 다시 빠르게 본 값으로, 단기 꺾임을 빨리 보여주는 편입니다.")),row=13,col=1)
    fig.add_trace(go.Scatter(x=idx,y=stoch_rsi_d,line=dict(color='#A78BFA',width=1.4,dash='dot'),name='Stoch RSI D',hovertemplate=_indicator_hover("Stoch RSI D","값: %{y:.1f}","K선과의 교차가 단기 타이밍 신호로 자주 쓰입니다.")),row=13,col=1)
    for y_,clr in [(20,'rgba(56,189,248,.35)'),(50,'rgba(148,163,184,.35)'),(80,'rgba(248,113,113,.35)')]:
        fig.add_hline(y=y_,line_color=clr,line_dash='dash',line_width=1,row=13,col=1)
    for sn,color,symbol,size,label in [('StochRSI_Cross_Buy','#22C55E','triangle-up',10,'Stoch RSI Buy'),('StochRSI_Cross_Sell','#EF4444','triangle-down',10,'Stoch RSI Sell')]:
        _sig_marker(fig,dc,sn,13,stoch_rsi_k,color,symbol,size,label)

    cmf=dc.get('CMF',pd.Series(0,index=idx))
    obv=dc.get('OBV',pd.Series(0,index=idx))
    ad_line=dc.get('AD_Line',pd.Series(0,index=idx))
    obv_slope=dc.get('OBV_Slope',pd.Series(0,index=idx))*100
    obv_z=(((obv-obv.rolling(60,min_periods=20).mean())/(obv.rolling(60,min_periods=20).std()+1e-10))*12).clip(-60,60)
    ad_line_z=(((ad_line-ad_line.rolling(60,min_periods=20).mean())/(ad_line.rolling(60,min_periods=20).std()+1e-10))*12).clip(-60,60)
    fig.add_trace(go.Bar(x=idx,y=obv_slope.clip(-60,60),marker_color=np.where(obv_slope>=0,'rgba(34,197,94,.38)','rgba(239,68,68,.38)').tolist(),name='OBV Slope',hovertemplate=_indicator_hover("OBV Slope","표시 값: %{y:+.2f}","거래량 누적 흐름이 가격보다 먼저 개선 / 악화되는지 확인할 때 씁니다."),showlegend=False),row=14,col=1)
    cmf_state=_signed_state(cmf*100,weak=4,strong=12,pos='매집 우위',neg='분산 우위',neutral='중립 수급',strong_pos='강한 매집 우위',strong_neg='강한 분산 우위')
    fig.add_trace(go.Scatter(x=idx,y=(cmf*100).clip(-60,60),line=dict(color='#14B8A6',width=2),name='CMF x100',text=cmf_state,hovertemplate=_indicator_hover("CMF","표시 값 %{y:+.1f}","0 위는 매집 성격, 0 아래는 분산 성격으로 보는 대표 수급 지표입니다.","원래 값 %{customdata:+.3f}",extra_line="현재 해석: %{text}"),customdata=cmf.values),row=14,col=1)
    fig.add_trace(go.Scatter(x=idx,y=obv_z,line=dict(color='#FBBF24',width=1.8),name='OBV Z',hovertemplate=_indicator_hover("OBV Z","값: %{y:+.1f}","최근 평균 대비 거래량 누적 흐름이 얼마나 강한지 보여줍니다.")),row=14,col=1)
    fig.add_trace(go.Scatter(x=idx,y=ad_line_z,line=dict(color='#F472B6',width=1.6,dash='dot'),name='AD Line Z',hovertemplate=_indicator_hover("AD Line Z","값: %{y:+.1f}","상승 종목 수급이 넓게 퍼지는지, 일부 종목만 오르는지 볼 때 도움이 됩니다.")),row=14,col=1)
    fig.add_hline(y=0,line_color="#64748B",line_width=1,row=14,col=1)
    for sn,color,symbol,size,label in [('Smart_Money_Bullish_Div','#22C55E','diamond',10,'Smart Money Bull'),('Smart_Money_Bearish_Div','#EF4444','diamond',10,'Smart Money Bear')]:
        _state_marker(fig,dc,dc.get(sn,pd.Series(False,index=idx)).fillna(False),14,obv_z,color,symbol,size,label,"가격과 수급이 엇갈린 자리입니다. 추세가 약해지거나 반전이 나올 단서가 될 수 있습니다.")

    tenkan=dc.get('Ichimoku_Tenkan',pd.Series(np.nan,index=idx))
    kijun=dc.get('Ichimoku_Kijun',pd.Series(np.nan,index=idx))
    senkou_a=dc.get('Ichimoku_SenkouA',pd.Series(np.nan,index=idx))
    senkou_b=dc.get('Ichimoku_SenkouB',pd.Series(np.nan,index=idx))
    mass_index=dc.get('Mass_Index',pd.Series(25,index=idx))
    disparity_200=dc.get('Disparity_200',pd.Series(0,index=idx))
    close_base=dc.get('Close',pd.Series(0,index=idx)).replace(0,np.nan)
    tenkan_gap=((dc['Close']-tenkan)/(close_base+1e-10)*100).replace([np.inf,-np.inf],np.nan).fillna(0).clip(-25,25)
    kijun_gap=((dc['Close']-kijun)/(close_base+1e-10)*100).replace([np.inf,-np.inf],np.nan).fillna(0).clip(-25,25)
    cloud_spread=((senkou_a-senkou_b)/(close_base+1e-10)*100).replace([np.inf,-np.inf],np.nan).fillna(0).clip(-25,25)
    mass_bias=((mass_index-26.5)*4).clip(-25,25)
    fig.add_trace(go.Bar(x=idx,y=mass_bias,marker_color=np.where(mass_bias>=0,'rgba(250,204,21,.30)','rgba(148,163,184,.22)').tolist(),name='Mass Bias',hovertemplate=_indicator_hover("Mass Index","표시 값: %{y:+.1f}","26.5 근처 이상으로 올라오면 변동성 확장 뒤 방향 전환 가능성을 경계합니다.","원래 값: %{customdata:.2f}"),customdata=mass_index.values,showlegend=False),row=15,col=1)
    tenkan_state=_level_state(tenkan_gap,near=1.5,strong=6,above='전환선 위 탄력 우위',below='전환선 아래 눌림 / 약세 우위',near_text='전환선 부근 균형',strong_above='전환선 위 강한 탄력 / 과열 접근',strong_below='전환선 아래 강한 이탈 / 약세 심화')
    fig.add_trace(go.Scatter(x=idx,y=tenkan_gap,line=dict(color='#22D3EE',width=1.8),name='Tenkan Gap',text=tenkan_state,hovertemplate=_indicator_hover("Tenkan Gap","값 %{y:+.2f}%","전환선과 현재 가격 간격입니다. 단기 과열 / 눌림 깊이를 볼 때 유용합니다.",extra_line="현재 해석: %{text}")),row=15,col=1)
    fig.add_trace(go.Scatter(x=idx,y=kijun_gap,line=dict(color='#FB7185',width=1.8),name='Kijun Gap',hovertemplate=_indicator_hover("Kijun Gap","값: %{y:+.2f}%","기준선과의 거리로, 중기 기준에서 얼마나 멀어졌는지 보여줍니다.")),row=15,col=1)
    fig.add_trace(go.Scatter(x=idx,y=cloud_spread,line=dict(color='#4ADE80',width=1.5,dash='dot'),name='Cloud Spread',hovertemplate=_indicator_hover("Cloud Spread","값: %{y:+.2f}%","구름 두께가 두꺼울수록 지지 / 저항 구조가 더 뚜렷하다고 보는 편입니다.")),row=15,col=1)
    fig.add_trace(go.Scatter(x=idx,y=disparity_200.clip(-25,25),line=dict(color='#A78BFA',width=1.6,dash='dash'),name='Disparity 200',hovertemplate=_indicator_hover("Disparity 200","값: %{y:+.2f}","장기선과의 이격으로 큰 과열 / 깊은 눌림을 파악할 때 좋습니다.")),row=15,col=1)
    fig.add_hline(y=0,line_color="#64748B",line_width=1,row=15,col=1)
    fig.add_hline(y=2.0,line_color='rgba(250,204,21,.35)',line_dash='dash',line_width=1,row=15,col=1)
    for sn,color,symbol,size,label in [('TK_Cross_Bull','#22C55E','triangle-up',10,'TK Bull'),('TK_Cross_Bear','#EF4444','triangle-down',10,'TK Bear'),('Kumo_Breakout_Bull','#4ADE80','diamond',10,'Kumo Breakout'),('Kumo_Breakout_Bear','#FB7185','diamond',10,'Kumo Breakdown')]:
        _sig_marker(fig,dc,sn,15,tenkan_gap,color,symbol,size,label)
    _state_marker(fig,dc,mass_index>=26.5,15,mass_bias,'#FBBF24','hexagon',8,'Mass Expansion',"변동성 압축이 끝나고 방향 전환이 나올 수 있는 경고 구간입니다.")

    atr_pct=((dc.get('ATR',pd.Series(0,index=idx))/(dc.get('Close',pd.Series(0,index=idx)).replace(0,np.nan)+1e-10))*100).replace([np.inf,-np.inf],np.nan).fillna(0)
    volume_ratio_20=dc.get('Volume_Ratio_20',pd.Series(1,index=idx))
    volume_ratio_50=dc.get('Volume_Ratio_50',pd.Series(1,index=idx))
    dollar_volume_20=dc.get('Dollar_Volume_20',pd.Series(0,index=idx))
    dollar_volume_log=np.log10(dollar_volume_20.clip(lower=1))
    dollar_volume_z=(((dollar_volume_log-dollar_volume_log.rolling(60,min_periods=20).mean())/(dollar_volume_log.rolling(60,min_periods=20).std()+1e-10))*14).replace([np.inf,-np.inf],np.nan).fillna(0).clip(-60,60)
    vol_ratio20_scaled=((volume_ratio_20-1.0)*40).clip(-60,120)
    vol_ratio50_scaled=((volume_ratio_50-1.0)*40).clip(-60,120)
    atr_pct_scaled=(atr_pct*10).clip(0,100)
    fig.add_trace(go.Bar(x=idx,y=dollar_volume_z,marker_color=np.where(dollar_volume_z>=0,'rgba(56,189,248,.38)','rgba(148,163,184,.26)').tolist(),name='Dollar Vol Z',hovertemplate=_indicator_hover("Dollar Volume 20d","정규화 값: %{y:+.1f}","거래대금이 늘수록 움직임 신뢰도가 좋아지고, 너무 얇으면 신호를 보수적으로 봐야 합니다.","log10 값: %{customdata:.2f}"),customdata=dollar_volume_log.values,showlegend=False),row=16,col=1)
    atr_state=_volatility_state(atr_pct)
    fig.add_trace(go.Scatter(x=idx,y=atr_pct_scaled,line=dict(color='#F97316',width=2),name='ATR % x10',text=atr_state,hovertemplate=_indicator_hover("ATR %","표시 값 %{y:.1f}","변동성이 커질수록 손절 폭과 리스크 관리가 더 중요해집니다.","원래 값 %{customdata:.2f}%",extra_line="현재 해석: %{text}"),customdata=atr_pct.values),row=16,col=1)
    fig.add_trace(go.Scatter(x=idx,y=vol_ratio20_scaled,line=dict(color='#22C55E',width=1.8),name='Vol Ratio 20',hovertemplate=_indicator_hover("Volume Ratio 20","표시 값: %{y:+.1f}","1.0 위면 최근 20일 평균보다 거래량이 많은 상태입니다.","원래 값: %{customdata:.2f}"),customdata=volume_ratio_20.values),row=16,col=1)
    fig.add_trace(go.Scatter(x=idx,y=vol_ratio50_scaled,line=dict(color='#A78BFA',width=1.5,dash='dot'),name='Vol Ratio 50',hovertemplate=_indicator_hover("Volume Ratio 50","표시 값: %{y:+.1f}","긴 기준 평균 대비 거래량 우위인지 확인하는 보조 축입니다.","원래 값: %{customdata:.2f}"),customdata=volume_ratio_50.values),row=16,col=1)
    fig.add_hline(y=0,line_color="#64748B",line_width=1,row=16,col=1)
    fig.add_hline(y=20,line_color='rgba(56,189,248,.30)',line_dash='dash',line_width=1,row=16,col=1)
    for sn,color,symbol,size,label in [('Volume_Surge','#22D3EE','hexagram',11,'Volume Surge'),('Volume_Dry_Up','#FCD34D','square-open',8,'Volume Dry-Up'),('Volume_Dry_Breakout_Buy','#22C55E','triangle-up',10,'Dry Breakout'),('Volume_Dry_Breakout_Sell','#EF4444','triangle-down',10,'Dry Breakdown'),('Volume_Climax_Buy','#06B6D4','diamond',10,'Volume Climax Buy'),('Volume_Climax_Sell','#F97316','diamond',10,'Volume Climax Sell')]:
        _sig_marker(fig,dc,sn,16,vol_ratio20_scaled,color,symbol,size,label)
    _state_marker(fig,dc,dc.get('Thin_Trade_Risk',pd.Series(False,index=idx)).fillna(False),16,dollar_volume_z,'#94A3B8','x',9,'Thin Trade Risk',"거래대금이 얇아 급등락과 슬리피지가 커질 수 있는 구간입니다.")
    _state_marker(fig,dc,dc.get('Low_Volume_Caution',pd.Series(False,index=idx)).fillna(False),16,vol_ratio20_scaled,'#FCD34D','square',7,'Low Volume',"거래량이 부족해 현재 방향의 신뢰도를 낮춰서 봐야 하는 구간입니다.")
    _state_marker(fig,dc,dc.get('Washout_Bottom_Hard',pd.Series(False,index=idx)).fillna(False),16,atr_pct_scaled,'#22C55E','triangle-up',9,'Washout Bottom',"과도한 투매 뒤 반전 시도가 나올 수 있는 과매도 세척 구간입니다.")
    _state_marker(fig,dc,dc.get('Blowoff_Top_Hard',pd.Series(False,index=idx)).fillna(False),16,atr_pct_scaled,'#EF4444','triangle-down',9,'Blowoff Top',"과열이 심해 추격 매수보다 이익 실현 경계가 필요한 구간입니다.")

    rs_ratio=dc.get('RS_Ratio',pd.Series(1,index=idx))
    composite_accel=dc.get('Composite_Accel',pd.Series(0,index=idx))
    price_slope_5=(dc.get('Price_Slope_5',pd.Series(0,index=idx))*100).clip(-20,20)
    stock_return=(dc.get('Stock_Return',pd.Series(0,index=idx))*100).clip(-30,30)
    spy_return=(dc.get('SPY_Return',pd.Series(0,index=idx))*100).clip(-30,30)
    excess_return=(stock_return-spy_return).clip(-25,25)
    rs_ratio_scaled=((rs_ratio-1.0)*220).clip(-25,25)
    composite_accel_scaled=(composite_accel*25).clip(-25,25)
    fig.add_trace(go.Bar(x=idx,y=price_slope_5,marker_color=np.where(price_slope_5>=0,'rgba(34,197,94,.55)','rgba(239,68,68,.55)').tolist(),name='Slope 5d',hovertemplate=_indicator_hover("Price Slope 5d","값: %{y:+.2f}%","최근 5일 가격 각도입니다. 0 위면 단기 속도가 위쪽으로 기울고 있음을 뜻합니다."),showlegend=False),row=17,col=1)
    rs_state=_rs_state(rs_ratio)
    fig.add_trace(go.Scatter(x=idx,y=rs_ratio_scaled,line=dict(color='#38BDF8',width=2),name='RS Ratio',text=rs_state,hovertemplate=_indicator_hover("RS Ratio","정규화 값 %{y:+.1f}","시장(SPY) 대비 얼마나 강한지 보여줍니다. 1.0 위에서 우상향이면 리더주 성격이 강합니다.","원래 값 %{customdata:.3f}",extra_line="현재 해석: %{text}"),customdata=rs_ratio.values),row=17,col=1)
    fig.add_trace(go.Scatter(x=idx,y=composite_accel_scaled,line=dict(color='#F59E0B',width=1.8),name='Comp Accel',hovertemplate=_indicator_hover("Composite Accel","정규화 값: %{y:+.1f}","여러 모멘텀의 가속도를 합친 값으로, 추세가 붙는 초기 구간 확인에 도움됩니다.","원래 값: %{customdata:+.2f}"),customdata=composite_accel.values),row=17,col=1)
    fig.add_trace(go.Scatter(x=idx,y=excess_return,line=dict(color='#F472B6',width=1.5,dash='dot'),name='Excess Ret 20',hovertemplate=_indicator_hover("Stock - SPY 20d","값: %{y:+.2f}%","시장보다 더 강하게 오르면 플러스, 덜 오르거나 더 약하면 마이너스로 봅니다.")),row=17,col=1)
    fig.add_hline(y=0,line_color="#64748B",line_width=1,row=17,col=1)
    for sn,color,symbol,size,label in [('Relative_Strength_Buy','#22D3EE','star-diamond',10,'RS Buy'),('Relative_Strength_Sell','#F97316','star-diamond',10,'RS Sell')]:
        _sig_marker(fig,dc,sn,17,rs_ratio_scaled,color,symbol,size,label)
    _state_marker(fig,dc,dc.get('Leader_Stock_Mode',pd.Series(False,index=idx)).fillna(False),17,composite_accel_scaled,'#8B5CF6','hexagon',9,'Leader Mode',"리더주 / 테마주 장세가 강해 약한 종목보다 강한 종목이 더 유리한 환경입니다.")

    envelope_position=((dc.get('Envelope_Percent',pd.Series(0.5,index=idx))-0.5)*100).clip(-50,50)
    ma20_atr_gap=(dc.get('MA20_ATR_Gap',pd.Series(0,index=idx))*15).clip(-50,50)
    channel_up=dc.get('Price_Channel_Up',pd.Series(np.nan,index=idx))
    channel_low=dc.get('Price_Channel_Low',pd.Series(np.nan,index=idx))
    channel_span=(channel_up-channel_low).replace(0,np.nan)
    channel_position=(((dc.get('Close',pd.Series(0,index=idx))-channel_low)/(channel_span+1e-10))-0.5)*100
    channel_position=channel_position.replace([np.inf,-np.inf],np.nan).fillna(0).clip(-50,50)
    supertrend_gap=((dc.get('Close',pd.Series(0,index=idx))-dc.get('SuperTrend',pd.Series(np.nan,index=idx)))/(dc.get('Close',pd.Series(0,index=idx)).replace(0,np.nan)+1e-10)*100*8)
    supertrend_gap=supertrend_gap.replace([np.inf,-np.inf],np.nan).fillna(0).clip(-50,50)
    fig.add_trace(go.Bar(x=idx,y=ma20_atr_gap,marker_color=np.where(ma20_atr_gap>=0,'rgba(250,204,21,.35)','rgba(148,163,184,.22)').tolist(),name='MA20 ATR Gap',hovertemplate=_indicator_hover("MA20 ATR Gap","표시 값: %{y:+.1f}","20일선에서 ATR 몇 배만큼 멀어졌는지 보여줘 과열 / 세척 정도를 판단할 때 씁니다.","원래 값: %{customdata:+.2f}"),customdata=dc.get('MA20_ATR_Gap',pd.Series(0,index=idx)).values,showlegend=False),row=18,col=1)
    envelope_state=_level_state(envelope_position,near=10,strong=30,above='상단 근접 / 탄력 우위',below='하단 근접 / 눌림 우위',near_text='채널 중심 부근 / 중립',strong_above='상단 과열권 접근',strong_below='하단 과매도권 접근')
    fig.add_trace(go.Scatter(x=idx,y=envelope_position,line=dict(color='#22D3EE',width=2),name='Envelope Pos',text=envelope_state,hovertemplate=_indicator_hover("Envelope Position","값 %{y:+.1f}","상단에 가까우면 과열, 하단에 가까우면 눌림 / 과매도 쪽으로 읽기 쉽습니다.","원래 값 %{customdata:.2f}",extra_line="현재 해석: %{text}"),customdata=dc.get('Envelope_Percent',pd.Series(0.5,index=idx)).values),row=18,col=1)
    fig.add_trace(go.Scatter(x=idx,y=channel_position,line=dict(color='#FB7185',width=1.8),name='Channel Pos',hovertemplate=_indicator_hover("Channel Position","값: %{y:+.1f}","가격 채널 안에서 어디쯤 있는지 보여주며, 상단 근접 / 하단 근접을 직관적으로 볼 수 있습니다.")),row=18,col=1)
    fig.add_trace(go.Scatter(x=idx,y=supertrend_gap,line=dict(color='#A78BFA',width=1.5,dash='dot'),name='SuperTrend Gap',hovertemplate=_indicator_hover("SuperTrend Gap","정규화 값: %{y:+.1f}","SuperTrend 기준선과의 거리입니다. 플러스면 기준선 위, 마이너스면 아래에 있습니다.","원래 값: %{customdata:+.2f}%"),customdata=((dc.get('Close',pd.Series(0,index=idx))-dc.get('SuperTrend',pd.Series(np.nan,index=idx)))/(dc.get('Close',pd.Series(0,index=idx)).replace(0,np.nan)+1e-10)*100).replace([np.inf,-np.inf],np.nan).fillna(0).values),row=18,col=1)
    fig.add_hline(y=0,line_color="#64748B",line_width=1,row=18,col=1)
    fig.add_hline(y=25,line_color='rgba(248,113,113,.30)',line_dash='dash',line_width=1,row=18,col=1)
    fig.add_hline(y=-25,line_color='rgba(56,189,248,.30)',line_dash='dash',line_width=1,row=18,col=1)
    for sn,color,symbol,size,label in [('SuperTrend_Buy','#22D3EE','triangle-up',10,'SuperTrend Buy'),('SuperTrend_Sell','#EF4444','triangle-down',10,'SuperTrend Sell'),('Parabolic_Bottom_Buy','#22C55E','diamond',10,'Parabolic Bottom'),('Parabolic_Top_Sell','#FB7185','diamond',10,'Parabolic Top')]:
        _sig_marker(fig,dc,sn,18,supertrend_gap,color,symbol,size,label)

    atr_base=dc.get('ATR',pd.Series(np.nan,index=idx)).replace(0,np.nan)
    hma_series=hma if hma is not None else pd.Series(np.nan,index=idx)
    hma_gap_atr=((dc.get('Close',pd.Series(0,index=idx))-hma_series)/(atr_base+1e-10)).replace([np.inf,-np.inf],np.nan).fillna(0).clip(-4.2,4.2)*12
    ut_stop_gap=(dc.get('UTBot_Stop_ATR_Gap',pd.Series(0,index=idx))*12).replace([np.inf,-np.inf],np.nan).fillna(0).clip(-50,50)
    ut_dir_line=(dc.get('UTBot_Dir',pd.Series(0,index=idx)).fillna(0)*18).clip(-22,22)
    hma_bias=pd.Series(np.where(dc.get('HMA_Rising',pd.Series(False,index=idx)).fillna(False),12,-12),index=idx)
    fig.add_trace(go.Bar(x=idx,y=hma_bias,marker_color=np.where(hma_bias>=0,'rgba(34,197,94,.22)','rgba(239,68,68,.20)').tolist(),name='HMA Bias',hovertemplate=_indicator_hover("HMA Bias","값 %{y:+.1f}","Hull MA가 상승 기울기면 초록, 하락 기울기면 빨간 영역으로 보여줘서 방향 전환을 빠르게 읽게 도와줍니다."),showlegend=False),row=19,col=1)
    hma_state=_level_state(hma_gap_atr,near=4,strong=18,above='HMA 위에서 추세 유지',below='HMA 아래에서 약세 압박',near_text='HMA 재시험 / 전환 구간',strong_above='HMA 위 강한 추세 지속',strong_below='HMA 아래 강한 약세 지속')
    fig.add_trace(go.Scatter(x=idx,y=hma_gap_atr,line=dict(color='#22D3EE',width=2),name='Price-HMA Gap',text=hma_state,hovertemplate=_indicator_hover("Price - HMA","값 %{y:+.1f}","가격이 HMA 위에 있을수록 플러스, 아래에 있을수록 마이너스입니다. 0선 부근은 추세 전환 시험 구간으로 보기 좋습니다.","원값 %{customdata:+.2f} ATR",extra_line="현재 해석: %{text}"),customdata=((dc.get('Close',pd.Series(0,index=idx))-hma_series)/(atr_base+1e-10)).replace([np.inf,-np.inf],np.nan).fillna(0).values),row=19,col=1)
    fig.add_trace(go.Scatter(x=idx,y=ut_stop_gap,line=dict(color='#F59E0B',width=1.8,dash='dot'),name='UT Stop Gap',hovertemplate=_indicator_hover("UTBot Stop Gap","값 %{y:+.1f}","UTBot 손절선에서 얼마나 여유가 있는지를 ATR 기준으로 보여줍니다. 값이 높을수록 롱 쪽 공간이 넓고, 낮을수록 숏 쪽 압박이 강합니다.","원값 %{customdata:+.2f} ATR"),customdata=dc.get('UTBot_Stop_ATR_Gap',pd.Series(0,index=idx)).replace([np.inf,-np.inf],np.nan).fillna(0).values),row=19,col=1)
    fig.add_trace(go.Scatter(x=idx,y=ut_dir_line,line=dict(color='#CBD5E1',width=1.2,dash='dash'),name='UT Direction',hovertemplate=_indicator_hover("UTBot Direction","값 %{y:+.0f}","UTBot 방향이 위쪽이면 매수 추세, 아래쪽이면 매도 추세 쪽으로 정렬돼 있음을 뜻합니다.","원값 %{customdata:+.0f}"),customdata=dc.get('UTBot_Dir',pd.Series(0,index=idx)).fillna(0).values),row=19,col=1)
    fig.add_hline(y=0,line_color="#64748B",line_width=1,row=19,col=1)
    fig.add_hline(y=20,line_color='rgba(34,197,94,.25)',line_dash='dash',line_width=1,row=19,col=1)
    fig.add_hline(y=-20,line_color='rgba(239,68,68,.25)',line_dash='dash',line_width=1,row=19,col=1)
    for sn,color,symbol,size,label,anchor in [
        ('Hull_Turn_Bull','#22C55E','circle',8,'Hull Turn',hma_gap_atr),
        ('Hull_Turn_Bear','#EF4444','circle',8,'Hull Turn',hma_gap_atr),
        ('UTBot_Buy','#22C55E','triangle-up',11,'UTBot Signal',ut_stop_gap),
        ('UTBot_Sell','#EF4444','triangle-down',11,'UTBot Signal',ut_stop_gap),
    ]:
        _sig_marker(fig,dc,sn,19,anchor,color,symbol,size,label,visible='legendonly')
    _state_marker(fig,dc,dc.get('HMA_Rising',pd.Series(False,index=idx)).fillna(False),19,hma_bias,'#22C55E','line-ew-open',8,'HMA Rising',"Hull MA가 위로 기울어져 추세 받침이 살아 있는 구간입니다.",visible='legendonly')
    _state_marker(fig,dc,dc.get('UTBot_Dir',pd.Series(0,index=idx)).fillna(0)==1,19,ut_dir_line,'#F8FAFC','circle-open',7,'UT Long Regime',"UTBot 방향이 매수 쪽으로 정렬된 구간입니다.",visible='legendonly')

    vp_poc_gap=((dc.get('Close',pd.Series(0,index=idx))-dc.get('VP_POC',pd.Series(np.nan,index=idx)))/(atr_base+1e-10)).replace([np.inf,-np.inf],np.nan).fillna(0).clip(-5,5)*10
    vp_vah_gap=((dc.get('Close',pd.Series(0,index=idx))-dc.get('VP_VAH',pd.Series(np.nan,index=idx)))/(atr_base+1e-10)).replace([np.inf,-np.inf],np.nan).fillna(0).clip(-5,5)*10
    vp_val_gap=((dc.get('Close',pd.Series(0,index=idx))-dc.get('VP_VAL',pd.Series(np.nan,index=idx)))/(atr_base+1e-10)).replace([np.inf,-np.inf],np.nan).fillna(0).clip(-5,5)*10
    vp_long_rr=dc.get('VP_Long_RR',pd.Series(0,index=idx)).replace([np.inf,-np.inf],np.nan).fillna(0)
    vp_short_rr=dc.get('VP_Short_RR',pd.Series(0,index=idx)).replace([np.inf,-np.inf],np.nan).fillna(0)
    vp_rr_edge=((vp_long_rr-vp_short_rr)*10).clip(-50,50)
    fig.add_trace(go.Bar(x=idx,y=vp_rr_edge,marker_color=np.where(vp_rr_edge>=0,'rgba(34,197,94,.55)','rgba(239,68,68,.55)').tolist(),name='VP RR Edge',hovertemplate=_indicator_hover("VP Risk/Reward Edge","값 %{y:+.1f}","롱 RR이 우세하면 플러스, 숏 RR이 우세하면 마이너스입니다. 어떤 방향의 보상이 더 나은지 빠르게 읽게 도와줍니다.","롱 %{customdata[0]:.1f} / 숏 %{customdata[1]:.1f}"),customdata=np.column_stack([vp_long_rr.values,vp_short_rr.values]),showlegend=False),row=20,col=1)
    vp_state=_level_state(vp_poc_gap,near=4,strong=18,above='POC 위 안착 / 상방 우위',below='POC 아래 체류 / 하방 우위',near_text='POC 근처 균형 / 방향 대기',strong_above='POC 위 강한 상방 우위',strong_below='POC 아래 강한 하방 우위')
    fig.add_trace(go.Scatter(x=idx,y=vp_poc_gap,line=dict(color='#38BDF8',width=2),name='POC Gap',text=vp_state,hovertemplate=_indicator_hover("Price - POC","값 %{y:+.1f}","현재가가 거래량 중심 가격대(POC) 위에 있으면 플러스, 아래면 마이너스입니다.","원값 %{customdata:+.2f} ATR",extra_line="현재 해석: %{text}"),customdata=((dc.get('Close',pd.Series(0,index=idx))-dc.get('VP_POC',pd.Series(np.nan,index=idx)))/(atr_base+1e-10)).replace([np.inf,-np.inf],np.nan).fillna(0).values),row=20,col=1)
    fig.add_trace(go.Scatter(x=idx,y=vp_vah_gap,line=dict(color='#FB7185',width=1.7,dash='dot'),name='VAH Gap',hovertemplate=_indicator_hover("Price - VAH","값 %{y:+.1f}","Value Area High 위로 올라서면 저항 돌파, 아래면 아직 저항 아래에 머무는 상태로 해석하기 좋습니다.","원값 %{customdata:+.2f} ATR"),customdata=((dc.get('Close',pd.Series(0,index=idx))-dc.get('VP_VAH',pd.Series(np.nan,index=idx)))/(atr_base+1e-10)).replace([np.inf,-np.inf],np.nan).fillna(0).values),row=20,col=1)
    fig.add_trace(go.Scatter(x=idx,y=vp_val_gap,line=dict(color='#4ADE80',width=1.7,dash='dot'),name='VAL Gap',hovertemplate=_indicator_hover("Price - VAL","값 %{y:+.1f}","Value Area Low 위에서 버티면 지지 성격, 아래로 밀리면 방어 실패 구간으로 해석하기 좋습니다.","원값 %{customdata:+.2f} ATR"),customdata=((dc.get('Close',pd.Series(0,index=idx))-dc.get('VP_VAL',pd.Series(np.nan,index=idx)))/(atr_base+1e-10)).replace([np.inf,-np.inf],np.nan).fillna(0).values),row=20,col=1)
    fig.add_hline(y=0,line_color="#64748B",line_width=1,row=20,col=1)
    fig.add_hline(y=15,line_color='rgba(34,197,94,.22)',line_dash='dash',line_width=1,row=20,col=1)
    fig.add_hline(y=-15,line_color='rgba(239,68,68,.22)',line_dash='dash',line_width=1,row=20,col=1)
    for sn,color,symbol,size,label in [('Volume_POC_Breakout','#22C55E','triangle-up',10,'POC Breakout'),('Volume_POC_Breakdown','#EF4444','triangle-down',10,'POC Breakdown'),('VP_VAL_Support','#4ADE80','circle',8,'VAL Support'),('VP_VAH_Resistance','#FB7185','circle',8,'VAH Resistance')]:
        _sig_marker(fig,dc,sn,20,vp_poc_gap,color,symbol,size,label,visible='legendonly')
    _state_marker(fig,dc,vp_poc_gap.abs()<=4,20,vp_poc_gap,'#CBD5E1','circle-open',7,'Near POC',"가격이 거래량 중심(P0C) 근처에 있어 방향 선택을 준비하는 구간입니다.",visible='legendonly')

    fib_382_gap=((dc.get('Close',pd.Series(0,index=idx))-dc.get('Fib_382',pd.Series(np.nan,index=idx)))/(atr_base+1e-10)).replace([np.inf,-np.inf],np.nan).fillna(0).clip(-5,5)*10
    fib_50_gap=((dc.get('Close',pd.Series(0,index=idx))-dc.get('Fib_50',pd.Series(np.nan,index=idx)))/(atr_base+1e-10)).replace([np.inf,-np.inf],np.nan).fillna(0).clip(-5,5)*10
    fib_618_gap=((dc.get('Close',pd.Series(0,index=idx))-dc.get('Fib_618',pd.Series(np.nan,index=idx)))/(atr_base+1e-10)).replace([np.inf,-np.inf],np.nan).fillna(0).clip(-5,5)*10
    fib_support_state=(dc.get('Fib_382_Support',pd.Series(False,index=idx)).fillna(False)|dc.get('Fib_50_Support',pd.Series(False,index=idx)).fillna(False)|dc.get('Fib_618_Support',pd.Series(False,index=idx)).fillna(False))
    fib_resistance_state=(dc.get('Fib_382_Resistance',pd.Series(False,index=idx)).fillna(False)|dc.get('Fib_50_Resistance',pd.Series(False,index=idx)).fillna(False)|dc.get('Fib_618_Resistance',pd.Series(False,index=idx)).fillna(False))
    fib_bias=(
        _bool_weight(fib_support_state,10,idx)
        +_bool_weight(dc.get('Fib_618_Reclaim',pd.Series(False,index=idx)),14,idx)
        +_bool_weight(dc.get('Fib_Confluence_Buy',pd.Series(False,index=idx)),18,idx)
        -_bool_weight(fib_resistance_state,10,idx)
        -_bool_weight(dc.get('Fib_618_Breakdown',pd.Series(False,index=idx)),14,idx)
        -_bool_weight(dc.get('Fib_Confluence_Sell',pd.Series(False,index=idx)),18,idx)
    ).clip(-40,40)
    fig.add_trace(go.Bar(x=idx,y=fib_bias,marker_color=np.where(fib_bias>=0,'rgba(34,197,94,.26)','rgba(239,68,68,.24)').tolist(),name='Fib Bias',hovertemplate=_indicator_hover("Fib Bias","값 %{y:+.1f}","피보나치 지지/저항, 61.8% 회복/이탈, 컨플루언스 여부를 한 줄로 압축한 보조 해석 축입니다."),showlegend=False),row=21,col=1)
    fig.add_trace(go.Scatter(x=idx,y=fib_382_gap,line=dict(color='#60A5FA',width=1.7),name='Fib 38.2 Gap',hovertemplate=_indicator_hover("Price - Fib 38.2","값 %{y:+.1f}","38.2% 되돌림 레벨과의 거리입니다. 지지 전환이 자주 나오는 첫 구간입니다.","원값 %{customdata:+.2f} ATR"),customdata=((dc.get('Close',pd.Series(0,index=idx))-dc.get('Fib_382',pd.Series(np.nan,index=idx)))/(atr_base+1e-10)).replace([np.inf,-np.inf],np.nan).fillna(0).values),row=21,col=1)
    fig.add_trace(go.Scatter(x=idx,y=fib_50_gap,line=dict(color='#FBBF24',width=1.7,dash='dot'),name='Fib 50 Gap',hovertemplate=_indicator_hover("Price - Fib 50","값 %{y:+.1f}","50% 되돌림과의 거리입니다. 중립 중심선처럼 읽기 좋아 추세 유지와 반전의 경계선 역할을 합니다.","원값 %{customdata:+.2f} ATR"),customdata=((dc.get('Close',pd.Series(0,index=idx))-dc.get('Fib_50',pd.Series(np.nan,index=idx)))/(atr_base+1e-10)).replace([np.inf,-np.inf],np.nan).fillna(0).values),row=21,col=1)
    fib_state=_level_state(fib_618_gap,near=5,strong=18,above='61.8% 위 재장악 시도',below='61.8% 이탈 압박',near_text='61.8% 레벨 테스트 중',strong_above='61.8% 위 강한 안착 시도',strong_below='61.8% 아래 강한 훼손')
    fig.add_trace(go.Scatter(x=idx,y=fib_618_gap,line=dict(color='#F472B6',width=1.9),name='Fib 61.8 Gap',text=fib_state,hovertemplate=_indicator_hover("Price - Fib 61.8","값 %{y:+.1f}","61.8% 황금비 레벨과의 거리입니다. 회복하면 지지 재장악, 이탈하면 추세 훼손 신호로 해석하기 좋습니다.","원값 %{customdata:+.2f} ATR",extra_line="현재 해석: %{text}"),customdata=((dc.get('Close',pd.Series(0,index=idx))-dc.get('Fib_618',pd.Series(np.nan,index=idx)))/(atr_base+1e-10)).replace([np.inf,-np.inf],np.nan).fillna(0).values),row=21,col=1)
    fig.add_hline(y=0,line_color="#64748B",line_width=1,row=21,col=1)
    fig.add_hline(y=20,line_color='rgba(34,197,94,.22)',line_dash='dash',line_width=1,row=21,col=1)
    fig.add_hline(y=-20,line_color='rgba(239,68,68,.22)',line_dash='dash',line_width=1,row=21,col=1)
    for sn,color,symbol,size,label in [('Fib_382_Support','#60A5FA','circle',8,'Fib 38.2 Support'),('Fib_382_Resistance','#F87171','circle',8,'Fib 38.2 Resistance'),('Fib_50_Support','#FBBF24','diamond',8,'Fib 50 Support'),('Fib_50_Resistance','#FB7185','diamond',8,'Fib 50 Resistance'),('Fib_618_Reclaim','#22C55E','triangle-up',10,'Fib Reclaim'),('Fib_618_Breakdown','#EF4444','triangle-down',10,'Fib Breakdown'),('Fib_Confluence_Buy','#22D3EE','diamond',9,'Fib Confluence'),('Fib_Confluence_Sell','#F97316','diamond',9,'Fib Confluence')]:
        _sig_marker(fig,dc,sn,21,fib_618_gap,color,symbol,size,label,visible='legendonly')
    _state_marker(fig,dc,fib_support_state,21,fib_bias,'#22C55E','circle-open',7,'Fib Support',"피보나치 되돌림 레벨이 지지처럼 작동한 구간입니다.",visible='legendonly')
    _state_marker(fig,dc,fib_resistance_state,21,fib_bias,'#EF4444','circle-open',7,'Fib Resistance',"피보나치 되돌림 레벨이 저항처럼 작동한 구간입니다.",visible='legendonly')

    close_series=dc.get('Close',pd.Series(0,index=idx))
    ma20_series=dc.get('MA20',pd.Series(np.nan,index=idx))
    ma50_series=dc.get('MA50',pd.Series(np.nan,index=idx))
    ma200_series=dc.get('MA200',pd.Series(np.nan,index=idx))
    ema12_series=dc.get('EMA12',pd.Series(np.nan,index=idx))
    ema26_series=dc.get('EMA26',pd.Series(np.nan,index=idx))
    ema_spread=((ema12_series-ema26_series)/(atr_base+1e-10)).replace([np.inf,-np.inf],np.nan).fillna(0).clip(-4,4)*12
    ma50_gap=((close_series-ma50_series)/(atr_base+1e-10)).replace([np.inf,-np.inf],np.nan).fillna(0).clip(-5,5)*10
    ma200_gap=((close_series-ma200_series)/(atr_base+1e-10)).replace([np.inf,-np.inf],np.nan).fillna(0).clip(-5,5)*10
    ma_alignment_bias=(
        _bool_weight(close_series>ma20_series,6,idx)
        +_bool_weight(close_series>ma50_series,9,idx)
        +_bool_weight(close_series>ma200_series,12,idx)
        +_bool_weight(ema12_series>ema26_series,7,idx)
        +_bool_weight(ma50_series>ma200_series,10,idx)
        -_bool_weight(close_series<ma20_series,6,idx)
        -_bool_weight(close_series<ma50_series,9,idx)
        -_bool_weight(close_series<ma200_series,12,idx)
        -_bool_weight(ema12_series<ema26_series,7,idx)
        -_bool_weight(ma50_series<ma200_series,10,idx)
    ).clip(-40,40)
    ma_state=_signed_state(ma_alignment_bias,weak=8,strong=24,pos='이평 정렬 강세',neg='이평 정렬 약세',neutral='정렬 혼합 / 중립',strong_pos='강한 상승 정배열',strong_neg='강한 하락 역배열')
    fig.add_trace(go.Bar(x=idx,y=ma_alignment_bias,marker_color=np.where(ma_alignment_bias>=0,'rgba(34,197,94,.26)','rgba(239,68,68,.24)').tolist(),name='MA Stack Bias',text=ma_state,hovertemplate=_indicator_hover("MA / EMA Stack Bias","값 %{y:+.1f}","가격과 이평선 정렬을 한 줄로 압축한 강세/약세 구조 축입니다.",extra_line="현재 해석: %{text}"),showlegend=False),row=22,col=1)
    fig.add_trace(go.Scatter(x=idx,y=ema_spread,line=dict(color='#22D3EE',width=2),name='EMA12-26 Spread',hovertemplate=_indicator_hover("EMA12 - EMA26","값 %{y:+.1f}","단기 EMA가 중기 EMA 위로 벌어질수록 플러스입니다. 추세 가속이 붙으면 위로 벌어지고, 약해지면 0선으로 되돌아옵니다.","원값 %{customdata:+.2f} ATR"),customdata=((ema12_series-ema26_series)/(atr_base+1e-10)).replace([np.inf,-np.inf],np.nan).fillna(0).values),row=22,col=1)
    fig.add_trace(go.Scatter(x=idx,y=ma50_gap,line=dict(color='#FBBF24',width=1.8),name='Price-MA50 Gap',hovertemplate=_indicator_hover("Price - MA50","값 %{y:+.1f}","중기 추세선인 50일선과의 거리입니다. 플러스면 위에서 추세 유지, 마이너스면 아래에서 약세 압박으로 읽기 좋습니다.","원값 %{customdata:+.2f} ATR"),customdata=((close_series-ma50_series)/(atr_base+1e-10)).replace([np.inf,-np.inf],np.nan).fillna(0).values),row=22,col=1)
    fig.add_trace(go.Scatter(x=idx,y=ma200_gap,line=dict(color='#A78BFA',width=1.8,dash='dot'),name='Price-MA200 Gap',hovertemplate=_indicator_hover("Price - MA200","값 %{y:+.1f}","장기 기준선인 200일선과의 거리입니다. 중장기 추세 건강도를 가장 직관적으로 보는 축입니다.","원값 %{customdata:+.2f} ATR"),customdata=((close_series-ma200_series)/(atr_base+1e-10)).replace([np.inf,-np.inf],np.nan).fillna(0).values),row=22,col=1)
    fig.add_hline(y=0,line_color="#64748B",line_width=1,row=22,col=1)
    fig.add_hline(y=20,line_color='rgba(34,197,94,.22)',line_dash='dash',line_width=1,row=22,col=1)
    fig.add_hline(y=-20,line_color='rgba(239,68,68,.22)',line_dash='dash',line_width=1,row=22,col=1)
    for sn,color,symbol,size,label,anchor in [
        ('Golden_Cross','#22C55E','star-diamond',11,'Golden Cross',ma200_gap),
        ('Death_Cross','#EF4444','star-diamond',11,'Death Cross',ma200_gap),
        ('Cross_Above_50MA','#4ADE80','triangle-up',9,'Above 50MA',ma50_gap),
        ('Fell_Below_50MA','#FB7185','triangle-down',9,'Below 50MA',ma50_gap),
        ('EMA_Pullback_Buy','#22D3EE','triangle-up',10,'EMA Pullback',ema_spread),
        ('EMA_Pullback_Sell','#F97316','triangle-down',10,'EMA Pullback',ema_spread),
        ('MA20_Support','#4ADE80','circle',8,'MA20 Support',ma50_gap),
        ('MA20_Resistance','#FB7185','circle',8,'MA20 Resistance',ma50_gap),
        ('MA50_Support','#22C55E','diamond',8,'MA50 Support',ma50_gap),
        ('MA50_Resistance','#EF4444','diamond',8,'MA50 Resistance',ma50_gap),
    ]:
        _sig_marker(fig,dc,sn,22,anchor,color,symbol,size,label,visible='legendonly')
    bullish_stack=(ema12_series>ema26_series).fillna(False)&(ma50_series>ma200_series).fillna(False)
    bearish_stack=(ema12_series<ema26_series).fillna(False)&(ma50_series<ma200_series).fillna(False)
    _state_marker(fig,dc,bullish_stack,22,ma_alignment_bias,'#22C55E','circle-open',7,'Bullish Stack',"단기와 장기 이동평균이 모두 위쪽 정렬을 이루는 구간입니다.",visible='legendonly')
    _state_marker(fig,dc,bearish_stack,22,ma_alignment_bias,'#EF4444','circle-open',7,'Bearish Stack',"단기와 장기 이동평균이 모두 아래쪽 정렬을 이루는 구간입니다.",visible='legendonly')

    trendline_dist=(dc.get('Trendline_Dist_ATR',pd.Series(0,index=idx))*12).replace([np.inf,-np.inf],np.nan).fillna(0).clip(-50,50)
    trendline_slope=(dc.get('Trendline_Slope_Pct',pd.Series(0,index=idx))*20).replace([np.inf,-np.inf],np.nan).fillna(0).clip(-40,40)
    box_state_line=(
        _bool_weight(dc.get('Box_Base',pd.Series(False,index=idx)),10,idx)
        +_bool_weight(dc.get('Box_Support_Hold',pd.Series(False,index=idx)),16,idx)
        +_bool_weight(dc.get('Box_Breakout_Bull',pd.Series(False,index=idx)),24,idx)
        -_bool_weight(dc.get('Box_Resistance_Reject',pd.Series(False,index=idx)),16,idx)
        -_bool_weight(dc.get('Box_Breakdown_Bear',pd.Series(False,index=idx)),24,idx)
    ).clip(-40,40)
    channel_state_line=(
        _bool_weight(dc.get('Channel_Up',pd.Series(False,index=idx)),12,idx)
        +_bool_weight(dc.get('Channel_Support_Hold',pd.Series(False,index=idx)),16,idx)
        +_bool_weight(dc.get('Channel_Breakout_Bull',pd.Series(False,index=idx)),24,idx)
        -_bool_weight(dc.get('Channel_Down',pd.Series(False,index=idx)),12,idx)
        -_bool_weight(dc.get('Channel_Resistance_Reject',pd.Series(False,index=idx)),16,idx)
        -_bool_weight(dc.get('Channel_Breakdown_Bear',pd.Series(False,index=idx)),24,idx)
        +_bool_weight(dc.get('Asc_Triangle',pd.Series(False,index=idx)),8,idx)
        -_bool_weight(dc.get('Desc_Triangle',pd.Series(False,index=idx)),8,idx)
    ).clip(-40,40)
    pattern_bias=(
        _bool_weight(dc.get('Diag_Support_Hold',pd.Series(False,index=idx)),8,idx)
        +_bool_weight(dc.get('Diag_Breakout_Bull',pd.Series(False,index=idx)),12,idx)
        +_bool_weight(dc.get('Box_Support_Hold',pd.Series(False,index=idx)),8,idx)
        +_bool_weight(dc.get('Box_Breakout_Bull',pd.Series(False,index=idx)),12,idx)
        +_bool_weight(dc.get('Channel_Support_Hold',pd.Series(False,index=idx)),9,idx)
        +_bool_weight(dc.get('Channel_Breakout_Bull',pd.Series(False,index=idx)),13,idx)
        +_bool_weight(dc.get('Triangle_Breakout_Bull',pd.Series(False,index=idx)),14,idx)
        -_bool_weight(dc.get('Diag_Resistance_Reject',pd.Series(False,index=idx)),8,idx)
        -_bool_weight(dc.get('Diag_Breakdown_Bear',pd.Series(False,index=idx)),12,idx)
        -_bool_weight(dc.get('Box_Resistance_Reject',pd.Series(False,index=idx)),8,idx)
        -_bool_weight(dc.get('Box_Breakdown_Bear',pd.Series(False,index=idx)),12,idx)
        -_bool_weight(dc.get('Channel_Resistance_Reject',pd.Series(False,index=idx)),9,idx)
        -_bool_weight(dc.get('Channel_Breakdown_Bear',pd.Series(False,index=idx)),13,idx)
        -_bool_weight(dc.get('Triangle_Breakdown_Bear',pd.Series(False,index=idx)),14,idx)
    ).clip(-45,45)
    pattern_state=_signed_state(pattern_bias,weak=8,strong=24,pos='상방 구조 우위',neg='하방 구조 우위',neutral='구조 혼합 / 대기',strong_pos='강한 상방 돌파 구조',strong_neg='강한 하방 이탈 구조')
    fig.add_trace(go.Bar(x=idx,y=pattern_bias,marker_color=np.where(pattern_bias>=0,'rgba(34,197,94,.26)','rgba(239,68,68,.24)').tolist(),name='Pattern Bias',text=pattern_state,hovertemplate=_indicator_hover("Pattern Bias","값 %{y:+.1f}","추세선 지지/이탈, 박스와 채널 지지/돌파, 삼각형 돌파 여부를 한 줄로 압축한 구조 해석 축입니다.",extra_line="현재 해석: %{text}"),showlegend=False),row=23,col=1)
    fig.add_trace(go.Scatter(x=idx,y=trendline_dist,line=dict(color='#38BDF8',width=1.8),name='Trendline Dist',hovertemplate=_indicator_hover("Trendline Distance","값 %{y:+.1f}","대각 추세선에서 얼마나 떨어져 있는지를 ATR 기준으로 보여줍니다. 0선 부근은 추세선 테스트 구간입니다.","원값 %{customdata:+.2f} ATR"),customdata=dc.get('Trendline_Dist_ATR',pd.Series(0,index=idx)).replace([np.inf,-np.inf],np.nan).fillna(0).values),row=23,col=1)
    fig.add_trace(go.Scatter(x=idx,y=trendline_slope,line=dict(color='#F59E0B',width=1.7,dash='dot'),name='Trendline Slope',hovertemplate=_indicator_hover("Trendline Slope","값 %{y:+.1f}","추세선 기울기가 커질수록 위로, 약해질수록 0선에 가까워집니다. 방향성과 힘의 변화를 함께 읽기 좋습니다.","원값 %{customdata:+.2f}%"),customdata=dc.get('Trendline_Slope_Pct',pd.Series(0,index=idx)).replace([np.inf,-np.inf],np.nan).fillna(0).values),row=23,col=1)
    fig.add_trace(go.Scatter(x=idx,y=box_state_line,line=dict(color='#A78BFA',width=1.6),name='Box State',hovertemplate=_indicator_hover("Box Structure State","값 %{y:+.1f}","박스 기반 횡보 구조가 지지/돌파로 발전하면 위쪽으로, 저항/이탈로 약해지면 아래쪽으로 움직입니다.")),row=23,col=1)
    fig.add_trace(go.Scatter(x=idx,y=channel_state_line,line=dict(color='#FB7185',width=1.6,dash='dash'),name='Channel/Triangle State',hovertemplate=_indicator_hover("Channel / Triangle State","값 %{y:+.1f}","상승 채널, 하락 채널, 삼각형 구조가 어느 방향으로 정렬되는지 상태값으로 요약한 선입니다.")),row=23,col=1)
    fig.add_hline(y=0,line_color="#64748B",line_width=1,row=23,col=1)
    fig.add_hline(y=25,line_color='rgba(34,197,94,.20)',line_dash='dash',line_width=1,row=23,col=1)
    fig.add_hline(y=-25,line_color='rgba(239,68,68,.20)',line_dash='dash',line_width=1,row=23,col=1)
    for sn,color,symbol,size,label,anchor in [
        ('Diag_Support_Hold','#22C55E','circle',8,'Diag Support',trendline_dist),
        ('Diag_Resistance_Reject','#EF4444','circle',8,'Diag Reject',trendline_dist),
        ('Diag_Breakout_Bull','#22D3EE','triangle-up',10,'Diag Breakout',trendline_dist),
        ('Diag_Breakdown_Bear','#F97316','triangle-down',10,'Diag Breakdown',trendline_dist),
        ('Box_Support_Hold','#4ADE80','square',8,'Box Support',box_state_line),
        ('Box_Resistance_Reject','#FB7185','square',8,'Box Reject',box_state_line),
        ('Box_Breakout_Bull','#22C55E','square-open',9,'Box Breakout',box_state_line),
        ('Box_Breakdown_Bear','#EF4444','square-open',9,'Box Breakdown',box_state_line),
        ('Channel_Support_Hold','#4ADE80','diamond',8,'Channel Support',channel_state_line),
        ('Channel_Resistance_Reject','#FB7185','diamond',8,'Channel Reject',channel_state_line),
        ('Channel_Breakout_Bull','#22C55E','diamond-open',9,'Channel Breakout',channel_state_line),
        ('Channel_Breakdown_Bear','#EF4444','diamond-open',9,'Channel Breakdown',channel_state_line),
        ('Triangle_Breakout_Bull','#22D3EE','triangle-up',10,'Triangle Breakout',channel_state_line),
        ('Triangle_Breakdown_Bear','#F97316','triangle-down',10,'Triangle Breakdown',channel_state_line),
    ]:
        _sig_marker(fig,dc,sn,23,anchor,color,symbol,size,label,visible='legendonly')
    _state_marker(fig,dc,dc.get('Asc_Triangle',pd.Series(False,index=idx)).fillna(False),23,pd.Series(32,index=idx),'#22C55E','triangle-ne',9,'Ascending Triangle',"상단 저항 압축과 하단 상승 지지가 함께 보이는 상승 삼각형 구간입니다.",visible='legendonly')
    _state_marker(fig,dc,dc.get('Desc_Triangle',pd.Series(False,index=idx)).fillna(False),23,pd.Series(-32,index=idx),'#EF4444','triangle-se',9,'Descending Triangle',"하단 지지 압박과 상단 하락 저항이 함께 보이는 하락 삼각형 구간입니다.",visible='legendonly')
    _state_marker(fig,dc,dc.get('Sym_Triangle',pd.Series(False,index=idx)).fillna(False),23,pd.Series(0,index=idx),'#F8FAFC','diamond-wide-open',8,'Sym Triangle',"고점과 저점이 함께 수렴하는 대칭 삼각형 구간입니다.",visible='legendonly')

    objective_buy=dc.get('Objective_Buy_Score',pd.Series(0,index=idx))
    objective_sell=dc.get('Objective_Sell_Score',pd.Series(0,index=idx))
    objective_conflict=dc.get('Objective_Conflict_Score',pd.Series(0,index=idx))
    fig.add_trace(go.Bar(x=idx,y=objective_buy,marker_color='rgba(99,217,162,.82)',name='Objective Buy',hovertemplate="Objective Buy:%{y:.1f}<extra></extra>"),row=24,col=1)
    fig.add_trace(go.Bar(x=idx,y=-objective_sell,marker_color='rgba(255,143,150,.82)',name='Objective Sell',hovertemplate="Objective Sell:%{customdata:.1f}<extra></extra>",customdata=objective_sell.values),row=24,col=1)
    fig.add_trace(go.Scatter(x=idx,y=objective_conflict,line=dict(color='#F6C35E',width=1.8),name='Conflict',hovertemplate="Conflict:%{y:.1f}<extra></extra>"),row=24,col=1)
    fig.add_hline(y=0,line_color="#64748B",line_width=1,row=24,col=1)

    if 'Ensemble_Score' in dc.columns:
        es=dc['Ensemble_Score']
        ensemble_colors=np.where(es>=30,SOFT_GREEN,np.where(es>=10,'#A7E7CF',np.where(es<=-30,SOFT_RED,np.where(es<=-10,'#F6C2C2',SOFT_AMBER))))
        cmd=[dc.get(f'CM_{cm}_EffScore',pd.Series(0,index=idx)).values for cm in COMMITTEE_NAMES]
        cma=np.column_stack(cmd) if cmd else np.zeros((len(dc),5))
        jgv=dc.get('Trade_Judgment',pd.Series('N/A',index=idx)).values
        cfv=dc.get('Judgment_Confidence',pd.Series(0,index=idx)).values
        ctxv=dc.get('Market_Context',pd.Series(0,index=idx)).values
        bav=dc.get('Buy_Agree',pd.Series(0,index=idx)).values
        sav=dc.get('Sell_Agree',pd.Series(0,index=idx)).values
        fig.add_trace(go.Bar(
            x=idx,
            y=es,
            marker_color=ensemble_colors.tolist(),
            name="Ensemble",
            opacity=.85,
            customdata=np.column_stack([jgv,cfv,bav,sav,cma[:,0],cma[:,1],cma[:,2],cma[:,3],cma[:,4],[CTX_KOR.get(int(c),'-') for c in ctxv]]),
            hovertemplate="<b>%{customdata[0]}</b> (%{customdata[1]:.0f}%) ES:%{y:+.1f}<br>B%{customdata[2]}:S%{customdata[3]} [%{customdata[9]}]<br>T%{customdata[4]:+.0f} M%{customdata[5]:+.0f} F%{customdata[6]:+.0f}<br>R%{customdata[7]:+.0f} L%{customdata[8]:+.0f}<extra></extra>",
        ),row=25,col=1)
        fig.add_hline(y=0,line_color="#475569",line_width=1,row=25,col=1)
        fig.add_hline(y=JT.STRONG_BUY_TH,line_dash='dot',line_color='rgba(0,230,118,.3)',line_width=1,row=25,col=1)
        fig.add_hline(y=JT.STRONG_SELL_TH,line_dash='dot',line_color='rgba(255,23,68,.3)',line_width=1,row=25,col=1)
        ctx_colors={CTX_EXTREME_OS:'rgba(0,230,118,.06)',CTX_EXTREME_OB:'rgba(255,23,68,.06)',CTX_ACCUMULATION:'rgba(0,188,212,.06)',CTX_DISTRIBUTION:'rgba(255,87,34,.06)',CTX_STRONG_UP:'rgba(0,230,118,.03)',CTX_STRONG_DN:'rgba(255,23,68,.03)',CTX_BOTTOMING:'rgba(0,188,212,.04)',CTX_TOPPING:'rgba(255,152,0,.04)'}
        prev_ctx=-1
        start_idx=0
        ctx_series=dc.get('Market_Context',pd.Series(0,index=idx)).values
        for ci in range(len(dc)):
            cur=int(ctx_series[ci])
            if cur!=prev_ctx:
                if prev_ctx in ctx_colors and ci>start_idx:
                    fig.add_vrect(x0=idx[start_idx],x1=idx[ci-1],fillcolor=ctx_colors[prev_ctx],line_width=0,row=25,col=1)
                start_idx=ci
                prev_ctx=cur
        if prev_ctx in ctx_colors:
            fig.add_vrect(x0=idx[start_idx],x1=idx[-1],fillcolor=ctx_colors[prev_ctx],line_width=0,row=25,col=1)

    chart_height=4700 if len(dc)<=126 else 5100
    fig.update_layout(template="plotly_dark",paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",margin=dict(l=24,r=28,t=92,b=20),height=chart_height,showlegend=True,hovermode="closest",hoverdistance=40,spikedistance=1000,legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="center",x=.5,font=dict(size=8,color='#94A3B8'),bgcolor='rgba(0,0,0,0)',traceorder='normal',groupclick='togglegroup'),hoverlabel=dict(bgcolor='rgba(11,14,20,.96)',bordercolor='#334155',font=dict(size=11,family=PLOTLY_FONT_FAMILY,color='#F8FAFC'),align='left',namelength=-1))
    for i in range(1,26):
        fig.update_layout(**{(f'yaxis{i}' if i>1 else 'yaxis'):dict(gridcolor='rgba(51,65,85,.3)',tickfont=dict(size=9,color='#64748B'),automargin=True)})
    fig.update_yaxes(range=[-50,50],row=5,col=1)
    fig.update_yaxes(range=[0,100],row=6,col=1)
    fig.update_yaxes(range=[0,100],row=8,col=1)
    fig.update_yaxes(range=[-65,65],row=12,col=1)
    fig.update_yaxes(range=[0,100],row=13,col=1)
    fig.update_yaxes(range=[-60,60],row=14,col=1)
    fig.update_yaxes(range=[-25,25],row=15,col=1)
    fig.update_yaxes(range=[-60,120],row=16,col=1)
    fig.update_yaxes(range=[-32,32],row=17,col=1)
    fig.update_yaxes(range=[-60,60],row=18,col=1)
    fig.update_yaxes(range=[-50,50],row=19,col=1)
    fig.update_yaxes(range=[-50,50],row=20,col=1)
    fig.update_yaxes(range=[-50,50],row=21,col=1)
    fig.update_yaxes(range=[-50,50],row=22,col=1)
    fig.update_yaxes(range=[-50,50],row=23,col=1)
    all_days=pd.date_range(start=idx[0],end=idx[-1],freq='D')
    non_trading=all_days.difference(idx.normalize())
    fig.update_xaxes(rangeslider_visible=False,rangebreaks=[dict(values=non_trading.tolist())],gridcolor='rgba(51,65,85,.3)',tickfont=dict(size=9,color='#64748B'),automargin=True,showspikes=True,spikemode='across',spikesnap='cursor',spikecolor='rgba(148,163,184,.45)',spikethickness=1,spikedash='dot')
    for ann in fig['layout']['annotations']:
        ann['font']=dict(size=11,color='#94A3B8',family=PLOTLY_FONT_FAMILY)
        ann['yshift']=10
    return fig


def build_chart(dc,ticker):
    try:
        fig=_build_unified_timeline_chart(dc,ticker)
    except Exception as exc:
        if "row, col" not in str(exc):
            raise
        fig=_build_chart_legacy(dc,ticker)
    fig=_configure_primary_chart_legend(fig)
    return _localize_chart_figure(fig)


_build_metadata_base = build_metadata


def build_metadata(dc,ticker):
    meta=_build_metadata_base(dc,ticker)
    def _localize_strategy_item(item):
        payload=dict(item)
        for key in ('label','entry_hint','explanation','invalidation_text','note'):
            payload[key]=translate_chart_text(payload.get(key))
        for key in ('matched_conditions','missing_conditions','failed_conditions','conflict_reasons','last5_change'):
            payload[key]=[translate_chart_text(text) for text in payload.get(key,[]) if str(text).strip()]
        return payload
    meta['regime_label']=localize_regime_label(meta.get('regime'), meta.get('regime_label'))
    meta['context_label']=localize_context_label(meta.get('context'))
    meta['judgment']=localize_judgment_label(meta.get('judgment'))
    meta['pre_veto_judgment']=localize_judgment_label(meta.get('pre_veto_judgment'))
    meta['objective_judgment']=localize_judgment_label(meta.get('objective_judgment'))
    meta['action_label']=localize_action_label(meta.get('action_label') or meta.get('judgment'))
    meta['objective_action_label']=localize_action_label(meta.get('objective_action_label') or meta.get('objective_judgment'))
    meta['leading_verdict']=translate_chart_text(meta.get('leading_verdict'))
    meta['lagging_verdict']=translate_chart_text(meta.get('lagging_verdict'))
    meta['judgment_reason']=translate_chart_text(meta.get('judgment_reason'))
    meta['judgment_detail']=translate_chart_text(meta.get('judgment_detail'))
    meta['contrast_notes']=translate_chart_text(meta.get('contrast_notes'))
    meta['objective_reason']=translate_chart_text(meta.get('objective_reason'))
    meta['objective_detail']=translate_chart_text(meta.get('objective_detail'))
    localized_scans=[]
    for scan in meta.get('combined_scans',[]):
        label,desc=localize_combo(scan.get('key', scan.get('name','')), scan.get('kor'), scan.get('desc'))
        item=dict(scan)
        item['kor']=label
        item['desc']=desc
        localized_scans.append(item)
    meta['combined_scans']=localized_scans
    localized_recent=[]
    for item in meta.get('recent_signals',[]):
        if isinstance(item,dict):
            payload=dict(item)
            payload['label']=translate_chart_text(payload.get('label'))
            payload['desc']=translate_chart_text(payload.get('desc'))
            payload['meaning']=translate_chart_text(payload.get('meaning'))
            localized_recent.append(payload)
            continue
        if isinstance(item,(list,tuple)) and len(item) >= 5:
            icon,label,date_text,direction,is_combo=item[:5]
            localized_recent.append((icon,translate_chart_text(label),date_text,direction,is_combo))
        else:
            localized_recent.append(item)
    meta['recent_signals']=localized_recent
    localized_derived_events=[]
    for item in meta.get('derived_signal_events',[]):
        payload=dict(item)
        payload['label']=translate_chart_text(payload.get('label'))
        payload['desc']=translate_chart_text(payload.get('desc'))
        payload['meaning']=translate_chart_text(payload.get('meaning'))
        localized_derived_events.append(payload)
    meta['derived_signal_events']=localized_derived_events
    localized_derived_states=[]
    for item in meta.get('derived_reason_states',[]):
        payload=dict(item)
        payload['label']=translate_chart_text(payload.get('label'))
        payload['desc']=translate_chart_text(payload.get('desc'))
        payload['meaning']=translate_chart_text(payload.get('meaning'))
        localized_derived_states.append(payload)
    meta['derived_reason_states']=localized_derived_states
    meta['strategy_results']=[_localize_strategy_item(item) for item in meta.get('strategy_results',[])]
    meta['strategy_visible_results']=[_localize_strategy_item(item) for item in meta.get('strategy_visible_results',[])]
    strategy_summary=dict(meta.get('strategy_summary') or {})
    if isinstance(strategy_summary.get('top_strategy'),dict):
        strategy_summary['top_strategy']=_localize_strategy_item(strategy_summary.get('top_strategy'))
    strategy_summary['secondary_strategies']=[_localize_strategy_item(item) for item in strategy_summary.get('secondary_strategies',[])]
    strategy_summary['dominant_reasons']=[translate_chart_text(text) for text in strategy_summary.get('dominant_reasons',[]) if str(text).strip()]
    strategy_summary['opposing_reasons']=[translate_chart_text(text) for text in strategy_summary.get('opposing_reasons',[]) if str(text).strip()]
    meta['strategy_summary']=strategy_summary
    meta['top_strategy']=strategy_summary.get('top_strategy')
    return meta

# ━━━ UI ━━━
