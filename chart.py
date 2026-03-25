import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.signal import find_peaks
from config import *
from utils import _sf
from localization import (
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
            name='Volume Profile',
            legendgroup='vp_profile',
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
                fig.add_trace(go.Scatter(x=[dc.index[0],x_right],y=[val,val],mode='lines',line=dict(color=clr,width=1.5,dash=sty),name=label,legendgroup=f'vp_{label.lower()}',hoverinfo='skip',showlegend=True,visible=default_visible),row=1,col=1)
    fig.add_trace(go.Scatter(x=[x_right],y=[dc['Close'].iloc[-1]],mode='markers',marker=dict(size=.1,color='rgba(0,0,0,0)'),hoverinfo='skip',showlegend=False),row=1,col=1)
    fig.add_trace(go.Scatter(x=[x_right],y=[high],mode='text',text=['VP'],textfont=dict(size=9,color='#94A3B8'),name='VP Label',legendgroup='vp_profile',hoverinfo='skip',showlegend=False,visible=default_visible),row=1,col=1)

def _sig_marker(fig,dc,sn,row,y,clr,sym,sz,lbl,legendgroup=None,showlegend=False,visible=True,legend_name=None):
    reg=SIGNAL_REGISTRY.get(sn) or COMBINED_SCAN_REGISTRY.get(sn,{})
    if sn not in dc.columns:return
    mask=dc[sn].fillna(False)
    if not mask.any():return
    sr=dc[mask];yv=y[mask] if isinstance(y,pd.Series) else pd.Series(y,index=dc.index)[mask]
    valid=yv.notna()
    if not valid.any():return
    sr=sr[valid];yv=yv[valid];kor=reg.get('kor','');desc=reg.get('desc','')
    ht=f"<b>{lbl}</b> ({kor})<br><span style='color:#94A3B8'>{desc}</span><br>%{{x|%Y-%m-%d}}<extra></extra>" if kor else f"<b>{lbl}</b><br>%{{x|%Y-%m-%d}}<extra></extra>"
    if row==1 and legendgroup is None and visible is True:
        visible='legendonly'
    fig.add_trace(go.Scatter(x=sr.index,y=yv,mode='markers',marker=dict(symbol=sym,size=sz,color=clr,line=dict(width=1.5,color='#FFF'),opacity=.95),name=legend_name or lbl,legendgroup=legendgroup,showlegend=showlegend,visible=visible,hovertemplate=ht),row=row,col=1)

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
                hovertemplate=_trendline_hover(line,f'Channel S{idx}')
            ),row=1,col=1)
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
            hovertemplate=_trendline_hover(line,f'Trendline S{idx}'),
            fill='tonexty' if 'channel_values' in line else None,
            fillcolor='rgba(45,212,191,0.06)' if 'channel_values' in line else None
        ),row=1,col=1)
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
            hovertemplate=_trendline_hover(line,f'Trendline R{idx}')
        ),row=1,col=1)
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
                hovertemplate=_trendline_hover(line,f'Channel R{idx}'),
                fill='tonexty',
                fillcolor='rgba(251,113,133,0.05)'
            ),row=1,col=1)
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
        hovertemplate=_pattern_hover(pattern,'Lower'),
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
        hovertemplate=_pattern_hover(pattern,'Upper'),
        fill='tonexty',
        fillcolor=fill_color,
    ),row=1,col=1)
    fig.add_trace(go.Scatter(
        x=[dc.index[-1]],
        y=[float(max(pattern['upper_projected_price'],pattern['lower_projected_price']))],
        mode='text',
        text=[f"{localize_pattern_name(pattern['name'])} · {localize_pattern_state(pattern['state'])}"],
        textposition='top right',
        textfont=dict(size=10,color=edge_color,family='Pretendard'),
        name='Pattern Overlay',
        legendgroup='pattern_overlay',
        showlegend=False,
        visible=default_visible,
        hoverinfo='skip'
    ),row=1,col=1)

def build_chart(dc,ticker):
    mac={20:'#f1c40f',50:'#e74c3c',200:'#2ecc71'}
    fig=make_subplots(rows=8,cols=1,shared_xaxes=True,vertical_spacing=0.02,row_heights=[.32,.04,.09,.09,.09,.09,.09,.19],subplot_titles=(ticker,"Vol","WaveTrend","MACD","Money Flow","Stoch Slow","Squeeze Mom","5-Committee Ensemble"))
    hover=_build_candle_hover(dc)
    fig.add_trace(go.Candlestick(x=dc.index,open=dc['Open'],high=dc['High'],low=dc['Low'],close=dc['Close'],name="Price",increasing_line_color=SOFT_GREEN,decreasing_line_color=SOFT_RED,increasing_fillcolor=SOFT_GREEN_FILL,decreasing_fillcolor=SOFT_RED_FILL,text=hover,hoverinfo='text',hoverlabel=dict(bgcolor='rgba(11,14,20,.97)',bordercolor='#334155',font=dict(size=11,family='Pretendard',color='#F1F5F9'),align='left')),row=1,col=1)
    for mp in [20,50,200]:fig.add_trace(go.Scatter(x=dc.index,y=dc[f'MA{mp}'],line=dict(color=mac[mp],width=1.2),name=f'{mp}MA',legendgroup='moving_average',hoverinfo='skip',showlegend=True,visible='legendonly'),row=1,col=1)
    for idx,(mc,clr) in enumerate([(dc['ST_Direction']==1,SOFT_GREEN),(dc['ST_Direction']==-1,SOFT_RED)],start=1):fig.add_trace(go.Scatter(x=dc.index,y=dc['SuperTrend'].where(mc),line=dict(color=clr,width=2),name='SuperTrend',legendgroup='supertrend',connectgaps=False,hoverinfo='skip',showlegend=(idx==1),visible='legendonly'),row=1,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['BB_Up'],line=dict(color='#475569',width=1,dash='dot'),name='Bollinger Band',legendgroup='bollinger_band',hoverinfo='skip',showlegend=True,visible='legendonly'),row=1,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['BB_Low'],line=dict(color='#475569',width=1,dash='dot'),legendgroup='bollinger_band',fill='tonexty',fillcolor='rgba(71,85,105,.06)',hoverinfo='skip',showlegend=False,visible='legendonly'),row=1,col=1)
    if 'HMA' in dc.columns:
        hup=dc.get('HMA_Rising',pd.Series(False,index=dc.index)).fillna(False)
        fig.add_trace(go.Scatter(x=dc.index,y=dc['HMA'].where(hup),line=dict(color=SOFT_GREEN,width=2.5),name='Hull MA',legendgroup='hull_ma',connectgaps=False,hoverinfo='skip',showlegend=True,visible=True),row=1,col=1)
        fig.add_trace(go.Scatter(x=dc.index,y=dc['HMA'].where(~hup),line=dict(color=SOFT_RED,width=2.5),legendgroup='hull_ma',connectgaps=False,hoverinfo='skip',showlegend=False,visible=True),row=1,col=1)
    if 'UTBot_Stop' in dc.columns:
        ub=dc['UTBot_Dir']==1;us=dc['UTBot_Dir']==-1
        fig.add_trace(go.Scatter(x=dc.index,y=dc['UTBot_Stop'].where(ub),line=dict(color='rgba(126,216,182,.5)',width=2,dash='dot'),name='UTBot Stop',legendgroup='utbot_stop',connectgaps=False,hoverinfo='skip',showlegend=True,visible='legendonly'),row=1,col=1)
        fig.add_trace(go.Scatter(x=dc.index,y=dc['UTBot_Stop'].where(us),line=dict(color='rgba(243,165,165,.5)',width=2,dash='dot'),name='UTBot Stop',legendgroup='utbot_stop',connectgaps=False,hoverinfo='skip',showlegend=False,visible='legendonly'),row=1,col=1)
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
    _add_trendline_overlays(fig,dc,max_per_side=2,default_visible=True)
    _add_pattern_overlay(fig,dc,_detect_active_pattern(dc),default_visible=True)
    _add_volume_profile_overlay(fig,dc,default_visible='legendonly')
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
    fig.update_layout(template="plotly_dark",paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",margin=dict(l=2,r=2,t=40,b=2),height=chart_height,showlegend=True,hovermode="closest",legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="center",x=.5,font=dict(size=8,color='#94A3B8'),bgcolor='rgba(0,0,0,0)',traceorder='normal',groupclick='togglegroup'))
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
            combo_kor,combo_desc=localize_combo(cn,ccfg.get('kor'),ccfg.get('desc'))
            ld=dc[cn].tail(5)[dc[cn].tail(5)].index[-1];acs.append({'key':cn,'name':ccfg['name'],'kor':combo_kor,'desc':combo_desc,'dir':ccfg['dir'],'tier':ccfg['tier'],'icon':ccfg['icon'],'color':ccfg['color'],'win':ccfg['win'],'date':ld.strftime('%m/%d'),'is_today':(dc.index[-1]-ld).days==0,'days_ago':(dc.index[-1]-ld).days})
    acs.sort(key=lambda x:(x['tier'],x['days_ago']))
    recent=[]
    for ir,row in dc.tail(15).iterrows():
        ds=ir.strftime('%m/%d')
        for col,cfg in SIGNAL_REGISTRY.items():
            if col in dc.columns and row.get(col,False):
                signal_kor,_=localize_signal(col,cfg.get('kor'),cfg.get('desc'))
                recent.append((cfg['icon'],signal_kor,ds,cfg['dir'],False))
        for col,cfg in COMBINED_SCAN_REGISTRY.items():
            if col in dc.columns and row.get(col,False):
                combo_kor,_=localize_combo(col,cfg.get('kor'),cfg.get('desc'))
                recent.append((cfg['icon'],combo_kor,ds,cfg['dir'],True))
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


_build_chart_base = build_chart


def build_chart(dc,ticker):
    fig=_build_chart_base(dc,ticker)
    return _localize_chart_figure(fig)


_build_metadata_base = build_metadata


def build_metadata(dc,ticker):
    meta=_build_metadata_base(dc,ticker)
    meta['regime_label']=localize_regime_label(meta.get('regime'), meta.get('regime_label'))
    meta['context_label']=localize_context_label(meta.get('context'))
    meta['judgment']=localize_judgment_label(meta.get('judgment'))
    meta['action_label']=localize_action_label(meta.get('action_label') or meta.get('judgment'))
    meta['leading_verdict']=translate_chart_text(meta.get('leading_verdict'))
    meta['lagging_verdict']=translate_chart_text(meta.get('lagging_verdict'))
    meta['judgment_reason']=translate_chart_text(meta.get('judgment_reason'))
    meta['judgment_detail']=translate_chart_text(meta.get('judgment_detail'))
    meta['contrast_notes']=translate_chart_text(meta.get('contrast_notes'))
    localized_scans=[]
    for scan in meta.get('combined_scans',[]):
        label,desc=localize_combo(scan.get('key', scan.get('name','')), scan.get('kor'), scan.get('desc'))
        item=dict(scan)
        item['kor']=label
        item['desc']=desc
        localized_scans.append(item)
    meta['combined_scans']=localized_scans
    return meta

# ━━━ UI ━━━
