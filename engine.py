# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
from config import *
from utils import _volf, _recent, _cd_dir, _cooldown, _vs
from indicators import detect_pivot_div, compute_indicators, compute_hull_ma, compute_ut_bot, compute_stochastic_slow, compute_squeeze_mom_enh
from engine_combo_registry import ensure_runtime_combo_registry
from engine_combo_scans import detect_combined_scans as _detect_combined_scans_impl
from engine_layers import compute_10layer_scores as _compute_10layer_scores_impl
from engine_committee import compute_committee_ensemble as _compute_committee_ensemble_impl
from engine_objective import compute_objective_judgment as _compute_objective_judgment_impl

def det_123pb(h,l,c,adx,pdi,mdi):
    sb=(adx>30)&(pdi>mdi);sbe=(adx>30)&(mdi>pdi);ins=(h<h.shift(1))&(l>l.shift(1))
    l1,l2,l3=l<l.shift(1),l.shift(1)<l.shift(2),l.shift(2)<l.shift(3);tl=l1&l2&l3;tli=(l1&l2&ins.shift(2))|(l1&ins.shift(1)&l2.shift(1))|(ins&l1&l2)
    h1,h2,h3=h>h.shift(1),h.shift(1)>h.shift(2),h.shift(2)>h.shift(3);th=h1&h2&h3;thi=(h1&h2&ins.shift(2))|(h1&ins.shift(1)&h2.shift(1))|(ins&h1&h2)
    return sb&(tl|tli),sbe&(th|thi)
def det_180(c,o,h,l,m10,m50):dr=h-l+1e-10;cp=(c-l)/dr;pp=(c.shift(1)-l.shift(1))/(h.shift(1)-l.shift(1)+1e-10);return (pp<=.25)&(cp>=.75)&(c>m10)&(c>m50),(pp>=.75)&(cp<=.25)&(c<m10)&(c<m50)
def det_boomer(h,l,adx,pdi,mdi):ins=(h<h.shift(1))&(l>l.shift(1));in2=ins&ins.shift(1);return in2.shift(1).fillna(False)&(adx>30)&(pdi>mdi),in2.shift(1).fillna(False)&(adx>30)&(mdi>pdi)
def det_expansion(h,l,c):dr=h-l;mr=dr.rolling(9).max();h60=h.rolling(60,min_periods=40).max();l60=l.rolling(60,min_periods=40).min();return (h>=h60)&(dr>=mr),(l<=l60)&(dr>=mr)
def det_exp_pivot(c,o,h,l,m50,atr):dr=h-l;mr=dr.rolling(9).max();bn=((c.shift(1)-m50.shift(1)).abs()<atr.shift(1))|((l<=m50)&(c>m50));sn=((c.shift(1)-m50.shift(1)).abs()<atr.shift(1))|((h>=m50)&(c<m50));return (dr>=mr)&bn&(c>m50)&(c>o),(dr>=mr)&sn&(c<m50)&(c<o)
def det_exp_dbl(c,o,h,l):dr=h-l;r=dr.rolling(10).rank(pct=True);h60=h.rolling(60,min_periods=40).max();return (h.shift(1)>=h60.shift(1))&(r.shift(1)>=.7)&(c<o)&(r>=.7)
def det_gilligans(o,c,h,l):dr=h-l+1e-10;cp=(c-l)/dr;l60=l.rolling(60,min_periods=40).min();h60=h.rolling(60,min_periods=40).max();return (o<=l60)&(o<l.shift(1))&(cp>=.5)&(c>=o),(o>=h60)&(o>h.shift(1))&(cp<=.5)&(c<=o)
def det_lizard(o,c,h,l):dr=h-l+1e-10;cp=(c-l)/dr;op=(o-l)/dr;return (cp>=.75)&(op>=.75)&(l<=l.rolling(10).min()),(cp<=.25)&(op<=.25)&(h>=h.rolling(10).max())
def det_slingshot(c,o,h,l,atr):t=atr*.3;h60=h.rolling(60,min_periods=40).max();l60=l.rolling(60,min_periods=40).min();return (h.shift(1)>=h60.shift(1))&(l<l.shift(1)-t),(l.shift(1)<=l60.shift(1))&(h>h.shift(1)+t)
def det_jack(h,l,c,df):ins=(h<h.shift(1))&(l>l.shift(1));xb=df.get('Expansion_BO',pd.Series(False,index=df.index)).fillna(False);xd=df.get('Expansion_BD',pd.Series(False,index=df.index)).fillna(False);return xb.shift(2).fillna(False)&ins.shift(1).fillna(False)&(c>h.shift(2)),xd.shift(2).fillna(False)&ins.shift(1).fillna(False)&(c<l.shift(2))
def det_nonadx(h,l,c,m50):ins=(h<h.shift(1))&(l>l.shift(1));l1,l2=l<l.shift(1),l.shift(1)<l.shift(2);tl=l1&l2&(l.shift(2)<l.shift(3));tli=(l1&l2&ins.shift(2))|(l1&ins.shift(1)&l2.shift(1))|(ins&l1&l2);h1,h2=h>h.shift(1),h.shift(1)>h.shift(2);th=h1&h2&(h.shift(2)>h.shift(3));thi=(h1&h2&ins.shift(2))|(h1&ins.shift(1)&h2.shift(1))|(ins&h1&h2);return (c>m50)&(tl|tli),(c<m50)&(th|thi)
def det_rev_hl(c,o,h,l):dr=h-l;mr=dr.rolling(5).max();h60=h.rolling(60,min_periods=40).max();l60=l.rolling(60,min_periods=40).min();out=(h>h.shift(1))&(l<l.shift(1));return (h>=h60)&out&(dr>=mr)&(c>o),(l<=l60)&out&(dr>=mr)&(c<o)
def det_ma_sr(c,o,h,l,ma,atr):md=(c-ma).abs()/(atr+1e-10);nr=md<.2;return nr&(c>ma)&(l<=ma*1.01)&(c>o),nr&(c<ma)&(h>=ma*.99)&(c<o)
def det_candles(c,o,h,l,wt1,atr,v):
    body=(c-o).abs();us=h-pd.concat([c,o],axis=1).max(axis=1);ls_=pd.concat([c,o],axis=1).min(axis=1)-l;fr=h-l+1e-10;ab=body.rolling(20).mean();sm=body<ab*.6;mr=atr*.5;vk=v>=v.rolling(10,min_periods=5).mean()*.5;vs_=v>v.rolling(10,min_periods=5).mean()*1.2
    ham=(ls_>=body*2)&(us<=body*.3)&sm&(wt1<-20)&(c>=o)&(fr>mr)&vk;sho=(us>=body*2)&(ls_<=body*.3)&sm&(wt1>20)&(c<=o)&(fr>mr)&vk
    doji=(body<=fr*.05)&(fr>atr*.3);db=doji&(wt1<-30)&(wt1>wt1.shift(1))&vk;dbe=doji&(wt1>30)&(wt1<wt1.shift(1))&vk
    d1b=(c.shift(2)<o.shift(2))&(body.shift(2)>ab.shift(2));d2s=body.shift(1)<ab.shift(1)*.5;d3u=(c>o)&(c>(o.shift(2)+c.shift(2))/2)&(body>ab*.8);ms_=d1b&d2s&d3u&(wt1<-15)&vs_
    d1u=(c.shift(2)>o.shift(2))&(body.shift(2)>ab.shift(2));d3d=(c<o)&(c<(o.shift(2)+c.shift(2))/2)&(body>ab*.8);es_=d1u&d2s&d3d&(wt1>15)&vs_
    return {'Hammer':ham,'Shooting_Star':sho,'Doji':doji,'Doji_Bullish':db,'Doji_Bearish':dbe,'Morning_Star':ms_,'Evening_Star':es_,'Spinning_Top':sm&(us>body*.5)&(ls_>body*.5)}
def det_engulf(c,o,wt1,m50,v):
    body=(c-o).abs();pb=(c.shift(1)-o.shift(1)).abs();ab=body.rolling(20).mean();big=(body>ab*.8)&(body>pb)
    ph=pd.concat([c.shift(1),o.shift(1)],axis=1).max(axis=1);pl=pd.concat([c.shift(1),o.shift(1)],axis=1).min(axis=1)
    ch=pd.concat([c,o],axis=1).max(axis=1);cl_=pd.concat([c,o],axis=1).min(axis=1)
    vi=v>v.shift(1)*1.1;vk=v>=v.rolling(10,min_periods=5).mean()*.5;vo=vi|vk
    return (c.shift(1)<o.shift(1))&(c>o)&(cl_<=pl)&(ch>=ph)&big&(wt1<-10)&vo,(c.shift(1)>o.shift(1))&(c<o)&(cl_<=pl)&(ch>=ph)&big&(wt1>10)&vo
def det_bb(c,o,h,l,bbu,bbl,bbw,kcu,kcl):
    ss_bb=(bbu<kcu)&(bbl>kcl);se=~ss_bb&ss_bb.shift(1).fillna(False);seb=se&(c>c.shift(1))&(c>o);ses=se&(c<c.shift(1))&(c<o)
    ut=h>=bbu;lt=l<=bbl;ub=c>bbu;lb_=(c<bbl)&(c<o);lbo=(c<bbl)&(c>o)&(c>c.shift(1));uw=ut.rolling(3).sum()>=3;lw=lt.rolling(3).sum()>=3
    wd=bbw.rolling(126,min_periods=60).rank(pct=True)>=.9;tight=bbw<=bbw.rolling(126,min_periods=60).min()*1.05
    return {'BB_Squeeze':tight,'BB_Squeeze_Started':ss_bb&~ss_bb.shift(1).fillna(False),'BB_Squeeze_End_Bull':seb,'BB_Squeeze_End_Bear':ses,'BB_Upper_Touch':ut&~ub,'BB_Lower_Touch':lt&~lb_,'BB_Upper_Break':ub,'BB_Lower_Break':lb_,'BB_Lower_Bounce':lbo,'BB_Upper_Walk':uw,'BB_Lower_Walk':lw,'BB_Wide_Bands':wd}

# ?곣봺??detect_all_signals ?곣봺??
def detect_all_signals(df):
    _ensure_runtime_combo_registry()
    H,L,C,O,V=df['High'],df['Low'],df['Close'],df['Open'],df['Volume']
    e8,e21=df['EMA8'],df['EMA21'];m10,m20,m50,m200=df['MA10'],df['MA20'],df['MA50'],df['MA200']
    wt1,wt2,atr=df['WT1'],df['WT2'],df['ATR'];adx,pdi,mdi=df['ADX'],df['Plus_DI'],df['Minus_DI']
    idx=df.index;vok=_volf(V,.5);avg_vol=V.rolling(50,min_periods=10).mean();vol_ratio=V/(avg_vol+1e-10)
    wur=_recent(df['WT_Up'],2);wdr=_recent(df['WT_Down'],2);htf=(e8>e21)&(e21>e21.shift(5))&(C>m50)&(m50>m50.shift(10))
    # MCB+
    df['Green_Dot_T1']=wur&(wt1<=OS1)&(df['RSI']<30)&(df['MFI']<30)&vok;df['Green_Dot_T2']=wur&(wt1<=OS1)&((df['RSI']<32)|(df['MFI']<32))&~df['Green_Dot_T1']&vok
    df['Red_Dot_T1']=wdr&(wt1>=OB1)&(df['RSI']>70)&(df['MFI']>70)&vok;df['Red_Dot_T2']=wdr&(wt1>=OB1)&((df['RSI']>68)|(df['MFI']>68))&~df['Red_Dot_T1']&vok
    df['Blue_Diamond']=(wt2<=0)&wur&htf&vok;df['Red_Diamond']=(wt2>=0)&wdr&~htf&vok
    df['Green_Circle']=wur&(wt1<=OS1)&~df['Green_Dot_T1']&~df['Green_Dot_T2']&vok&(df['RSI']<45)
    df['Red_Circle']=wdr&(wt1>=OB1)&~df['Red_Dot_T1']&~df['Red_Dot_T2']&vok&(df['RSI']>55)
    bd,brd,hb,hbr=detect_pivot_div(C,wt1,60,5,OS1,OB1,atr=atr);rbd,rbrd,_,_=detect_pivot_div(C,df['RSI'],60,5,35,65,atr=atr);obd,obrd,_,_=detect_pivot_div(C,df['OBV'],60,5,atr=atr)
    df['Gold_Dot']=df['Green_Dot_T1']&(wt1<=OS2)&_recent(bd,3);df['Blood_Diamond']=df['Red_Dot_T1']&(wt1>=OB2)&_recent(brd,3)
    df['Bull_Divergence']=bd&~df['Gold_Dot']&vok;df['Bear_Divergence']=brd&~df['Blood_Diamond']&vok
    df['RSI_Bull_Divergence']=rbd&(wt1<-20)&vok;df['RSI_Bear_Divergence']=rbrd&(wt1>20)&vok
    df['Hidden_Bull_Div']=hb&(wt1<-25)&htf&vok;df['Hidden_Bear_Div']=hbr&(wt1>25)&~htf&vok
    df['OBV_Div_Buy']=obd&(wt1<-30);df['OBV_Div_Sell']=obrd&(wt1>30)
    # Cooper
    df['Pullback_123_Bull'],df['Pullback_123_Bear']=det_123pb(H,L,C,adx,pdi,mdi);df['Setup_180_Bull'],df['Setup_180_Bear']=det_180(C,O,H,L,m10,m50)
    df['Boomer_Buy'],df['Boomer_Sell']=det_boomer(H,L,adx,pdi,mdi);df['Expansion_BO'],df['Expansion_BD']=det_expansion(H,L,C)
    df['Expansion_Pivot_Buy'],df['Expansion_Pivot_Sell']=det_exp_pivot(C,O,H,L,m50,atr);df['Expansion_Double_Sticks']=det_exp_dbl(C,O,H,L)
    df['Gilligans_Buy'],df['Gilligans_Sell']=det_gilligans(O,C,H,L);df['Lizard_Bull'],df['Lizard_Bear']=det_lizard(O,C,H,L)
    df['Slingshot_Bull'],df['Slingshot_Bear']=det_slingshot(C,O,H,L,atr);df['Jack_In_Box_Bull'],df['Jack_In_Box_Bear']=det_jack(H,L,C,df)
    df['NonADX_123_Bull'],df['NonADX_123_Bear']=det_nonadx(H,L,C,m50);df['Reversal_New_Highs'],df['Reversal_New_Lows']=det_rev_hl(C,O,H,L)
    # MA
    df['MA20_Support'],df['MA20_Resistance']=det_ma_sr(C,O,H,L,m20,atr);df['MA50_Support'],df['MA50_Resistance']=det_ma_sr(C,O,H,L,m50,atr);df['MA200_Support'],df['MA200_Resistance']=det_ma_sr(C,O,H,L,m200,atr)
    for tag,ma in [('20MA',m20),('50MA',m50),('200MA',m200)]:df[f'Cross_Above_{tag}']=(C>ma)&(C.shift(1)<=ma.shift(1));df[f'Fell_Below_{tag}']=(C<ma)&(C.shift(1)>=ma.shift(1))
    gc=(m50>m200)&(m50.shift(1)<=m200.shift(1));df['Golden_Cross']=gc&(adx>15);dc_=(m50<m200)&(m50.shift(1)>=m200.shift(1));df['Death_Cross']=dc_&(adx>15)
    df['MTF_All_Bullish']=(C>m10)&(C>m50)&(C>m200);df['MTF_All_Bearish']=(C<m10)&(C<m50)&(C<m200)
    df['Diag_Support_Hold']=df.get('Diag_Support_Hold',pd.Series(False,index=idx)).fillna(False)&vok
    df['Diag_Resistance_Reject']=df.get('Diag_Resistance_Reject',pd.Series(False,index=idx)).fillna(False)&vok
    df['Diag_Breakout_Bull']=df.get('Diag_Breakout_Bull',pd.Series(False,index=idx)).fillna(False)&(vol_ratio>=1.0)
    df['Diag_Breakdown_Bear']=df.get('Diag_Breakdown_Bear',pd.Series(False,index=idx)).fillna(False)&(vol_ratio>=1.0)
    df['Box_Support_Hold']=df.get('Box_Support_Hold',pd.Series(False,index=idx)).fillna(False)&vok
    df['Box_Resistance_Reject']=df.get('Box_Resistance_Reject',pd.Series(False,index=idx)).fillna(False)&vok
    df['Box_Breakout_Bull']=df.get('Box_Breakout_Bull',pd.Series(False,index=idx)).fillna(False)&(vol_ratio>=1.0)
    df['Box_Breakdown_Bear']=df.get('Box_Breakdown_Bear',pd.Series(False,index=idx)).fillna(False)&(vol_ratio>=1.0)
    df['Channel_Support_Hold']=df.get('Channel_Support_Hold',pd.Series(False,index=idx)).fillna(False)&vok
    df['Channel_Resistance_Reject']=df.get('Channel_Resistance_Reject',pd.Series(False,index=idx)).fillna(False)&vok
    df['Channel_Breakout_Bull']=df.get('Channel_Breakout_Bull',pd.Series(False,index=idx)).fillna(False)&(vol_ratio>=1.0)
    df['Channel_Breakdown_Bear']=df.get('Channel_Breakdown_Bear',pd.Series(False,index=idx)).fillna(False)&(vol_ratio>=1.0)
    df['Triangle_Breakout_Bull']=df.get('Triangle_Breakout_Bull',pd.Series(False,index=idx)).fillna(False)&(vol_ratio>=1.0)
    df['Triangle_Breakdown_Bear']=df.get('Triangle_Breakdown_Bear',pd.Series(False,index=idx)).fillna(False)&(vol_ratio>=1.0)
    # BB+罹붾뱾
    for k,v_ in det_bb(C,O,H,L,df['BB_Up'],df['BB_Low'],df['BB_Width'],df['KC_Upper'],df['KC_Lower']).items():df[k]=v_
    for k,v_ in det_candles(C,O,H,L,wt1,atr,V).items():df[k]=v_
    df['Bullish_Engulfing'],df['Bearish_Engulfing']=det_engulf(C,O,wt1,m50,V)
    ins=(H<H.shift(1))&(L>L.shift(1));out=(H>H.shift(1))&(L<L.shift(1))
    df['Inside_Day']=ins;df['Outside_Bullish']=out&(C>O)&(C>H.shift(1))&vok;df['Outside_Bearish']=out&(C<O)&(C<L.shift(1))&vok
    # MACD/Stoch/ADX/RSI
    ml,ms_=df['MACD_Line'],df['MACD_Signal'];df['MACD_Cross_Buy']=((ml>ms_)&(ml.shift(1)<=ms_.shift(1))&(ml<0))&vok;df['MACD_Cross_Sell']=((ml<ms_)&(ml.shift(1)>=ms_.shift(1))&(ml>0))&vok
    df['MACD_Zero_Cross_Buy']=(ml>0)&(ml.shift(1)<=0);df['MACD_Zero_Cross_Sell']=(ml<0)&(ml.shift(1)>=0)
    stk,std_=df['StochK'],df['StochD'];df['StochRSI_Cross_Buy']=(stk>std_)&(stk.shift(1)<=std_.shift(1))&(stk<25);df['StochRSI_Cross_Sell']=(stk<std_)&(stk.shift(1)>=std_.shift(1))&(stk>75)
    df['Stoch_Reached_OB']=(stk>=80)&(stk.shift(1)<80);df['Stoch_Reached_OS']=(stk<=20)&(stk.shift(1)>20);df['Stoch_Overbought']=(stk>80)&(std_>80);df['Stoch_Oversold']=(stk<20)&(std_<20)
    df['DMI_Cross_Bull']=((pdi>mdi)&(pdi.shift(1)<=mdi.shift(1)))&vok;df['DMI_Cross_Bear']=((mdi>pdi)&(mdi.shift(1)<=pdi.shift(1)))&vok
    df['ADX_New_Uptrend']=(adx>25)&(adx.shift(1)<=25)&(pdi>mdi)&vok;df['ADX_New_Downtrend']=(adx>25)&(adx.shift(1)<=25)&(mdi>pdi)&vok
    df['ADX_Momentum_Buy']=(adx>20)&(adx.shift(1)<=20)&(pdi>mdi)&vok;df['ADX_Momentum_Sell']=(adx>20)&(adx.shift(1)<=20)&(mdi>pdi)&vok
    rsi=df['RSI'];df['RSI_Cross_30_Up']=(rsi>30)&(rsi.shift(1)<=30);df['RSI_Cross_50_Up']=(rsi>50)&(rsi.shift(1)<=50);df['RSI_Cross_70_Down']=(rsi<70)&(rsi.shift(1)>=70);df['RSI_Cross_50_Down']=(rsi<50)&(rsi.shift(1)>=50)
    # 媛?踰붿쐞/52二??곗냽
    t=atr*.5;gu=(O>H.shift(1))&((O-H.shift(1))>t);gd=(O<L.shift(1))&((L.shift(1)-O)>t);df['Gap_Up']=gu;df['Gap_Down']=gd;df['Gap_Up_Closed']=gu.shift(1).fillna(False)&(L<=H.shift(2));df['Gap_Down_Closed']=gd.shift(1).fillna(False)&(H>=L.shift(2))
    dr=H-L;nr7m=dr.rolling(7).min();nr7=dr<=nr7m;df['NR7']=nr7;df['NR7_2']=nr7&nr7.shift(1).fillna(False);df['Narrow_Range_Bar']=dr<atr*.5;df['Wide_Range_Bar']=dr>atr*2
    df['Calm_After_Storm']=(dr>atr*2).rolling(5,min_periods=1).max().shift(1).fillna(False).astype(bool)&(dr<atr*.5)
    h252=H.rolling(252,min_periods=200).max().shift(1);l252=L.rolling(252,min_periods=200).min().shift(1);df['New_52W_High']=H>h252;df['New_52W_Low']=L<l252
    c252h=C.rolling(252,min_periods=200).max().shift(1);c252l=C.rolling(252,min_periods=200).min().shift(1);df['New_52W_Closing_High']=C>c252h;df['New_52W_Closing_Low']=C<c252l
    up_=C>C.shift(1);dn_=C<C.shift(1);us__=_vs(up_);ds__=_vs(dn_);df['Up_3_Days']=us__>=3;df['Up_4_Days']=us__>=4;df['Up_5_Days']=us__>=5;df['Down_3_Days']=ds__>=3;df['Down_4_Days']=ds__>=4;df['Down_5_Days']=ds__>=5
    # 湲고?
    n10=(C/10).round()*10;dist=(C-n10).abs();nrd=dist<atr*.5;df['Multiple_Ten_Bull']=nrd&(C.shift(1)<n10)&(C>n10)&(C>O);df['Multiple_Ten_Bear']=nrd&(C.shift(1)>n10)&(C<n10)&(C<O)
    dv_=V.where(C<C.shift(1),0);df['Pocket_Pivot']=(C>O)&(V>dv_.rolling(10).max())&(C>m50)&(C>C.shift(1));df['Parabolic_Rise']=(C-C.shift(10))/(C.shift(10)+1e-10)>.3
    df['Three_Weeks_Tight']=((C.rolling(15).max()-C.rolling(15).min())/(C.rolling(15).min()+1e-10))<.015
    vz=(V-avg_vol)/(V.rolling(20).std()+1e-10);df['Volume_Surge']=vol_ratio>=3;big=(C-O).abs()>atr*.5;ps=(vz.shift(1)>2.5)&big.shift(1)
    df['Volume_Climax_Buy']=ps&(C.shift(1)<O.shift(1))&(wt1.shift(1)<-40)&(C>O)&(C>(O+C.shift(1))/2);df['Volume_Climax_Sell']=ps&(C.shift(1)>O.shift(1))&(wt1.shift(1)>40)&(C<O)&(C<(O+C.shift(1))/2)
    mom=C-((H.rolling(20).max()+L.rolling(20).min())/2+df['KC_Mid'])/2;sf=~df['Squeeze_On']&df['Squeeze_On'].shift(1).fillna(False)
    df['Squeeze_Fire_Buy']=sf&(mom>0)&(mom>mom.shift(1))&vok;df['Squeeze_Fire_Sell']=sf&(mom<0)&(mom<mom.shift(1))&vok
    df['SuperTrend_Buy']=(df['ST_Direction']==1)&(df['ST_Direction'].shift(1)==-1);df['SuperTrend_Sell']=(df['ST_Direction']==-1)&(df['ST_Direction'].shift(1)==1)
    ar_=atr/(C+1e-10);vk2=_volf(V,.5);su_=e21>e21.shift(5);tu_=(e8>e21)&su_&(C>e8);tcu_=(L<=e8*(1+ar_*.15))&(L>=e21*(1-ar_*.25));bcu_=(C>=e8)&(C>H.shift(1))&(wt1>wt1.shift(1))&(wt1>wt2)&(wt1<60)
    df['EMA_Pullback_Buy']=tu_&_recent(tcu_,2)&bcu_&vk2
    sd__=e21<e21.shift(5);td_=(e8<e21)&sd__&(C<e8);tcd_=(H>=e8*(1-ar_*.15))&(H<=e21*(1+ar_*.25));bcd_=(C<=e8)&(C<L.shift(1))&(wt1<wt1.shift(1))&(wt1<wt2)&(wt1>-60)
    df['EMA_Pullback_Sell']=td_&_recent(tcd_,2)&bcd_&vk2
    body__=(C-O).abs();bb__=body__>atr*1.5;hv__=V>V.rolling(20).mean()*2;comp_=df['BB_Width'].shift(1)<df['BB_Width'].rolling(20).mean().shift(1)
    df['Momentum_Ignition_Buy']=(C>O)&bb__&hv__&(C>df['BB_Up'])&(e8>e21)&(wt1<50)&comp_;df['Momentum_Ignition_Sell']=(C<O)&bb__&hv__&(C<df['BB_Low'])&(e8<e21)&(wt1>-50)&comp_
    df['Parabolic_Bottom_Buy']=(((wt1<-80)&(wt1>wt1.shift(1))&(C>O))|((wt1<-70)&(wt1>wt1.shift(1))&(wt1>wt1.shift(2))&(C>O)&(C>C.shift(1)))|((C<df['BB_Low']-atr*1.5)&(C>O)))
    df['Parabolic_Top_Sell']=(((wt1>80)&(wt1<wt1.shift(1))&(C<O))|((wt1>70)&(wt1<wt1.shift(1))&(wt1<wt1.shift(2))&(C<O)&(C<C.shift(1)))|((C>df['BB_Up']+atr*1.5)&(C<O)))
    vk3=_volf(V,.7);df['VWAP_Bounce_Buy']=(df['VWAP_Osc']>0)&(df['VWAP_Osc'].shift(1)<-.5)&(wt1>wt2)&(wt1<30)&vk3;df['VWAP_Reject_Sell']=(df['VWAP_Osc']<0)&(df['VWAP_Osc'].shift(1)>.5)&(wt1<wt2)&(wt1>-30)&vk3
    tk_,kj_=df['Ichimoku_Tenkan'],df['Ichimoku_Kijun'];sa_,sb_=df['Ichimoku_SenkouA'],df['Ichimoku_SenkouB'];kt_=pd.concat([sa_,sb_],axis=1).max(axis=1);kb_=pd.concat([sa_,sb_],axis=1).min(axis=1)
    df['Kumo_Breakout_Bull']=(C>kt_)&(C.shift(1)<=kt_.shift(1))&(tk_>kj_)&vok;df['Kumo_Breakout_Bear']=(C<kb_)&(C.shift(1)>=kb_.shift(1))&(tk_<kj_)&vok
    df['TK_Cross_Bull']=(tk_>kj_)&(tk_.shift(1)<=kj_.shift(1))&(C>kt_)&vok;df['TK_Cross_Bear']=(tk_<kj_)&(tk_.shift(1)>=kj_.shift(1))&(C<kb_)&vok
    df['CMF_Bull']=(df['CMF']>.1)&(df['CMF'].shift(1)<=.1)&(C>m50)&vok;df['CMF_Bear']=(df['CMF']<-.1)&(df['CMF'].shift(1)>=-.1)&(C<m50)&vok
    rmfi=df['RSI_MFI'];mr__=rmfi>rmfi.shift(1);mf__=rmfi<rmfi.shift(1);df['MF_Cross_Bull']=((rmfi>0)&(rmfi.shift(1)<=0))&vok;df['MF_Cross_Bear']=((rmfi<0)&(rmfi.shift(1)>=0))&vok
    mus_=_vs(mr__);mds_=_vs(mf__);df['MF_Accel_Up']=(mus_>=5)&vok;df['MF_Accel_Dn']=(mds_>=5)&vok
    df['MF_Bull_Div']=(C<C.rolling(5).min().shift(1))&(rmfi>rmfi.rolling(5).min().shift(1))&(rmfi<0)&vok;df['MF_Bear_Div']=(C>C.rolling(5).max().shift(1))&(rmfi<rmfi.rolling(5).max().shift(1))&(rmfi>0)&vok
    if 'VP_POC' in df.columns:poc_=df['VP_POC'];df['Volume_POC_Breakout']=(C>poc_)&(C.shift(1)<=poc_.shift(1))&vok&(C>O);df['Volume_POC_Breakdown']=(C<poc_)&(C.shift(1)>=poc_.shift(1))&vok&(C<O)
    if 'VP_VAH' in df.columns:ap___=atr/(C+1e-10);df['VP_VAH_Resistance']=((df['VP_VAH']-C).abs()/(C+1e-10)<ap___*.5)&(C<O);df['VP_VAL_Support']=((C-df['VP_VAL']).abs()/(C+1e-10)<ap___*.5)&(C>O)
    rs_=df.get('RS_Ratio',pd.Series(1.,index=idx));rm_=rs_-rs_.shift(5);df['Relative_Strength_Buy']=(rs_>1.03)&(rm_>0.01)&(C>C.shift(1))&vok;df['Relative_Strength_Sell']=(rs_<.97)&(rm_<-0.01)&(C<C.shift(1))&vok
    df['Setup_Squeeze_Bull']=df.get('BB_Squeeze',pd.Series(False,index=idx)).fillna(False)&(df['MACD_Hist']<0)&(df['MACD_Hist']>df['MACD_Hist'].shift(1))&(wt1<30)
    df['Setup_Squeeze_Bear']=df.get('BB_Squeeze',pd.Series(False,index=idx)).fillna(False)&(df['MACD_Hist']>0)&(df['MACD_Hist']<df['MACD_Hist'].shift(1))&(wt1>-30)
    ca_=df.get('Composite_Accel',pd.Series(0,index=idx));df['Momentum_Accel_Buy']=(ca_>JT.ACCEL_MOD)&(wt1<40)&vok;df['Momentum_Accel_Sell']=(ca_<-JT.ACCEL_MOD)&(wt1>-40)&vok
    df['Volume_Dry_Up']=_vs(vol_ratio<.6)>=5
    cs__=df.get('WT_Conv_Speed',pd.Series(0,index=idx));ga__=df.get('WT_Gap_Abs',pd.Series(0,index=idx))
    df['WT_Convergence_Bull']=(cs__>3)&(ga__>2)&(ga__<15)&(wt1<wt2)&(wt1<20);df['WT_Convergence_Bear']=(cs__>3)&(ga__>2)&(ga__<15)&(wt1>wt2)&(wt1>-20)
    # ???좉퇋 6醫?
    vds=_vs(vol_ratio<0.6);vd5=vds>=5;df['Volume_Dry_Breakout_Buy']=vd5.shift(1).fillna(False)&(C>O)&(vol_ratio>=2)&(C>H.shift(1));df['Volume_Dry_Breakout_Sell']=vd5.shift(1).fillna(False)&(C<O)&(vol_ratio>=2)&(C<L.shift(1))
    br_=(C-O).abs();rr_=H-L+1e-10;idj=br_<rr_*0.1;djs=_vs(idj);df['Doji_Breakout_Buy']=(djs.shift(1)>=2)&(C>O)&(br_>atr*0.5)&(C>H.shift(1));df['Doji_Breakout_Sell']=(djs.shift(1)>=2)&(C<O)&(br_>atr*0.5)&(C<L.shift(1))
    tdn=(C.shift(1)<C.shift(2))&(C.shift(2)<C.shift(3));df['Three_Bar_Reversal_Buy']=tdn&(C>O)&(br_>atr*0.8)&(vol_ratio>=1.5)&(wt1<-20)
    tup=(C.shift(1)>C.shift(2))&(C.shift(2)>C.shift(3));df['Three_Bar_Reversal_Sell']=tup&(C<O)&(br_>atr*0.8)&(vol_ratio>=1.5)&(wt1>20)

    # ?먥븧??荑⑤떎???먥븧??
    PAIRED={('MACD_Cross_Buy','MACD_Cross_Sell'):12,('Bullish_Engulfing','Bearish_Engulfing'):5,('Hammer','Shooting_Star'):5,('Morning_Star','Evening_Star'):7,('DMI_Cross_Bull','DMI_Cross_Bear'):10,('Pullback_123_Bull','Pullback_123_Bear'):7,('Expansion_BO','Expansion_BD'):10,('Gilligans_Buy','Gilligans_Sell'):10,('Slingshot_Bull','Slingshot_Bear'):7,('MF_Cross_Bull','MF_Cross_Bear'):10,('Kumo_Breakout_Bull','Kumo_Breakout_Bear'):10,('StochRSI_Cross_Buy','StochRSI_Cross_Sell'):7,('ADX_Momentum_Buy','ADX_Momentum_Sell'):10,('EMA_Pullback_Buy','EMA_Pullback_Sell'):7,('SuperTrend_Buy','SuperTrend_Sell'):10,('Boomer_Buy','Boomer_Sell'):10,('Setup_180_Bull','Setup_180_Bear'):7,('VWAP_Bounce_Buy','VWAP_Reject_Sell'):7,('Momentum_Ignition_Buy','Momentum_Ignition_Sell'):10,('Volume_Dry_Breakout_Buy','Volume_Dry_Breakout_Sell'):7,('Doji_Breakout_Buy','Doji_Breakout_Sell'):5,('Three_Bar_Reversal_Buy','Three_Bar_Reversal_Sell'):5,('Box_Support_Hold','Box_Resistance_Reject'):5,('Box_Breakout_Bull','Box_Breakdown_Bear'):7,('Channel_Support_Hold','Channel_Resistance_Reject'):5,('Channel_Breakout_Bull','Channel_Breakdown_Bear'):7,('Triangle_Breakout_Bull','Triangle_Breakdown_Bear'):7}
    PAIRED.update({
        ('Fib_382_Support','Fib_382_Resistance'):5,
        ('Fib_50_Support','Fib_50_Resistance'):5,
        ('Fib_618_Support','Fib_618_Resistance'):7,
        ('Fib_618_Reclaim','Fib_618_Breakdown'):7,
    })
    ph__=set()
    for (bs,ss),cd in PAIRED.items():_cd_dir(df,bs,ss,cd);ph__.add(bs);ph__.add(ss)
    for s,cd in COOLDOWN_MAP.items():
        if s in df.columns and s not in ph__:df[s]=_cooldown(df[s],cd)
    # 蹂댁“吏??
    df['UTBot_Buy']=df.get('UTBot_Buy_Raw',pd.Series(False,index=idx)).fillna(False)&vok;df['UTBot_Sell']=df.get('UTBot_Sell_Raw',pd.Series(False,index=idx)).fillna(False)&vok
    hma_r=df.get('HMA_Rising',pd.Series(False,index=idx)).fillna(False);hma_r_v=hma_r.values
    df['Hull_Turn_Bull']=df.get('Hull_Turn_Bull_Raw',pd.Series(False,index=idx)).fillna(False)&(wt1>wt1.shift(1))&vok;df['Hull_Turn_Bear']=df.get('Hull_Turn_Bear_Raw',pd.Series(False,index=idx)).fillna(False)&(wt1<wt1.shift(1))&vok
    slk,sld=df.get('SlowK',pd.Series(50,index=idx)),df.get('SlowD',pd.Series(50,index=idx));df['StochSlow_Cross_Buy']=(slk>sld)&(slk.shift(1)<=sld.shift(1))&(slk<20);df['StochSlow_Cross_Sell']=(slk<sld)&(slk.shift(1)>=sld.shift(1))&(slk>80)
    df['Squeeze_Mom_Cross_Up']=df.get('Squeeze_Mom_Cross_Up_Raw',pd.Series(False,index=idx)).fillna(False)&vok;df['Squeeze_Mom_Cross_Down']=df.get('Squeeze_Mom_Cross_Down_Raw',pd.Series(False,index=idx)).fillna(False)&vok
    hrb=_recent(df.get('Hull_Turn_Bull_Raw',pd.Series(False,index=idx)).fillna(False),3);hrbe=_recent(df.get('Hull_Turn_Bear_Raw',pd.Series(False,index=idx)).fillna(False),3)
    df['VuManChu_Bull']=((wt1<-30)&(hrb|hma_r)&(df['Bull_Divergence'].fillna(False)|df['RSI_Bull_Divergence'].fillna(False)|df['Bullish_Engulfing'].fillna(False)|df['Hammer'].fillna(False)|df['Morning_Star'].fillna(False)))&vok
    df['VuManChu_Bear']=((wt1>30)&(hrbe|~hma_r)&(df['Bear_Divergence'].fillna(False)|df['RSI_Bear_Divergence'].fillna(False)|df['Bearish_Engulfing'].fillna(False)|df['Shooting_Star'].fillna(False)|df['Evening_Star'].fillna(False)))&vok
    for (bs,ss),cd in {('UTBot_Buy','UTBot_Sell'):10,('Hull_Turn_Bull','Hull_Turn_Bear'):7,('StochSlow_Cross_Buy','StochSlow_Cross_Sell'):7,('Squeeze_Mom_Cross_Up','Squeeze_Mom_Cross_Down'):5,('VuManChu_Bull','VuManChu_Bear'):10}.items():_cd_dir(df,bs,ss,cd)
    df=detect_combined_scans(df,vol_ratio,hma_r);df=compute_10layer_scores(df,vol_ratio,hma_r_v);df=compute_committee_ensemble(df,vol_ratio,hma_r_v);df=_compute_objective_judgment(df,vol_ratio)
    return df

def compute_10layer_scores(df, vol_ratio, hma_r_v):
    return _compute_10layer_scores_impl(df, vol_ratio, hma_r_v, COMBINED_SCAN_REGISTRY)

# Committee/objective wrappers keep the root pipeline stable
# while the heavy implementations live in dedicated modules.
def compute_committee_ensemble(df,vol_ratio,hma_r_v):
    return _compute_committee_ensemble_impl(df, vol_ratio, hma_r_v)


def _compute_objective_judgment(df,vol_ratio):
    return _compute_objective_judgment_impl(df, vol_ratio)
# Active combo path extracted into dedicated modules.
def _ensure_runtime_combo_registry():
    return ensure_runtime_combo_registry(COMBINED_SCAN_REGISTRY)


def detect_combined_scans(df,vol_ratio,hma_rising):
    return _detect_combined_scans_impl(df, vol_ratio, hma_rising, registry=COMBINED_SCAN_REGISTRY)


