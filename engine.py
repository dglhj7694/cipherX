import pandas as pd
import numpy as np
from config import *
from utils import _volf, _recent, _cd_dir, _cooldown, _vs, _sp, _spd, _sf, _cs_str
from indicators import detect_pivot_div, compute_indicators, compute_hull_ma, compute_ut_bot, compute_stochastic_slow, compute_squeeze_mom_enh

def _ensure_runtime_combo_registry():
    """
    Register additional practical combo scans at runtime.
    This keeps config.py stable while allowing faster algorithm iteration.
    """
    runtime_combos = {
        'CS_Trend_Continuation_Buy': {
            'name': 'Trend Continuation Buy',
            'kor': 'Trend continuation buy',
            'dir': 'buy',
            'tier': 2,
            'icon': 'UP',
            'color': '#34D399',
            'desc': 'Trend pullback hold + momentum restart',
            'win': '60-72%',
        },
        'CS_Trend_Continuation_Sell': {
            'name': 'Trend Continuation Sell',
            'kor': 'Trend continuation sell',
            'dir': 'sell',
            'tier': 2,
            'icon': 'DN',
            'color': '#F87171',
            'desc': 'Bear trend bounce fail + momentum rollover',
            'win': '60-72%',
        },
        'CS_Reversal_Cluster_Buy': {
            'name': 'Reversal Cluster Buy',
            'kor': 'Reversal cluster buy',
            'dir': 'buy',
            'tier': 1,
            'icon': 'REV',
            'color': '#22C55E',
            'desc': 'Divergence + oversold + turn signal cluster',
            'win': '68-80%',
        },
        'CS_Reversal_Cluster_Sell': {
            'name': 'Reversal Cluster Sell',
            'kor': 'Reversal cluster sell',
            'dir': 'sell',
            'tier': 1,
            'icon': 'REV',
            'color': '#EF4444',
            'desc': 'Divergence + overbought + turn signal cluster',
            'win': '68-80%',
        },
        'CS_Breakout_Confirm_Buy': {
            'name': 'Breakout Confirm Buy',
            'kor': 'Breakout confirm buy',
            'dir': 'buy',
            'tier': 2,
            'icon': 'BRK',
            'color': '#60A5FA',
            'desc': 'Breakout with volume and ADX/momentum confirmation',
            'win': '62-74%',
        },
        'CS_Breakout_Confirm_Sell': {
            'name': 'Breakout Confirm Sell',
            'kor': 'Breakdown confirm sell',
            'dir': 'sell',
            'tier': 2,
            'icon': 'BRK',
            'color': '#F97316',
            'desc': 'Breakdown with volume and ADX/momentum confirmation',
            'win': '62-74%',
        },
        'CS_Conflict_Warning': {
            'name': 'Conflict Warning',
            'kor': 'Direction conflict warning',
            'dir': 'neutral',
            'tier': 3,
            'icon': 'WARN',
            'color': '#F59E0B',
            'desc': 'Strong buy/sell conditions fired together',
            'win': 'N/A',
        },
    }
    for key, value in runtime_combos.items():
        COMBINED_SCAN_REGISTRY.setdefault(key, value)

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

# ━━━ detect_all_signals ━━━
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
    # BB+캔들
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
    # 갭/범위/52주/연속
    t=atr*.5;gu=(O>H.shift(1))&((O-H.shift(1))>t);gd=(O<L.shift(1))&((L.shift(1)-O)>t);df['Gap_Up']=gu;df['Gap_Down']=gd;df['Gap_Up_Closed']=gu.shift(1).fillna(False)&(L<=H.shift(2));df['Gap_Down_Closed']=gd.shift(1).fillna(False)&(H>=L.shift(2))
    dr=H-L;nr7m=dr.rolling(7).min();nr7=dr<=nr7m;df['NR7']=nr7;df['NR7_2']=nr7&nr7.shift(1).fillna(False);df['Narrow_Range_Bar']=dr<atr*.5;df['Wide_Range_Bar']=dr>atr*2
    df['Calm_After_Storm']=(dr>atr*2).rolling(5,min_periods=1).max().shift(1).fillna(False).astype(bool)&(dr<atr*.5)
    h252=H.rolling(252,min_periods=200).max().shift(1);l252=L.rolling(252,min_periods=200).min().shift(1);df['New_52W_High']=H>h252;df['New_52W_Low']=L<l252
    c252h=C.rolling(252,min_periods=200).max().shift(1);c252l=C.rolling(252,min_periods=200).min().shift(1);df['New_52W_Closing_High']=C>c252h;df['New_52W_Closing_Low']=C<c252l
    up_=C>C.shift(1);dn_=C<C.shift(1);us__=_vs(up_);ds__=_vs(dn_);df['Up_3_Days']=us__>=3;df['Up_4_Days']=us__>=4;df['Up_5_Days']=us__>=5;df['Down_3_Days']=ds__>=3;df['Down_4_Days']=ds__>=4;df['Down_5_Days']=ds__>=5
    # 기타
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
    # ★ 신규 6종
    vds=_vs(vol_ratio<0.6);vd5=vds>=5;df['Volume_Dry_Breakout_Buy']=vd5.shift(1).fillna(False)&(C>O)&(vol_ratio>=2)&(C>H.shift(1));df['Volume_Dry_Breakout_Sell']=vd5.shift(1).fillna(False)&(C<O)&(vol_ratio>=2)&(C<L.shift(1))
    br_=(C-O).abs();rr_=H-L+1e-10;idj=br_<rr_*0.1;djs=_vs(idj);df['Doji_Breakout_Buy']=(djs.shift(1)>=2)&(C>O)&(br_>atr*0.5)&(C>H.shift(1));df['Doji_Breakout_Sell']=(djs.shift(1)>=2)&(C<O)&(br_>atr*0.5)&(C<L.shift(1))
    tdn=(C.shift(1)<C.shift(2))&(C.shift(2)<C.shift(3));df['Three_Bar_Reversal_Buy']=tdn&(C>O)&(br_>atr*0.8)&(vol_ratio>=1.5)&(wt1<-20)
    tup=(C.shift(1)>C.shift(2))&(C.shift(2)>C.shift(3));df['Three_Bar_Reversal_Sell']=tup&(C<O)&(br_>atr*0.8)&(vol_ratio>=1.5)&(wt1>20)

    # ═══ 쿨다운 ═══
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
    # 보조지표
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

# ━━━ Combined Scan (동일) ━━━
def detect_combined_scans(df,vol_ratio,hma_rising):
    idx=df.index;C,O,H,L,V=df['Close'],df['Open'],df['High'],df['Low'],df['Volume']
    F=lambda c:df.get(c,pd.Series(False,index=idx)).fillna(False);N=lambda c,d=0:df.get(c,pd.Series(d,index=idx)).fillna(d)
    vr=vol_ratio;up_=(C>N('MA50'))&(N('MA50')>N('MA200'))&(N('Plus_DI')>N('Minus_DI'));dn_=(C<N('MA50'))&(N('MA50')<N('MA200'))&(N('Minus_DI')>N('Plus_DI'))
    adx_ok=N('ADX')>20;vs_=vr>=2;vok_=vr>=1
    bc_=F('Bullish_Engulfing')|F('Morning_Star')|F('Hammer')|F('Doji_Bullish');sc__=F('Bearish_Engulfing')|F('Evening_Star')|F('Shooting_Star')|F('Doji_Bearish')
    cb_=F('Pullback_123_Bull')|F('NonADX_123_Bull')|F('Setup_180_Bull')|F('Boomer_Buy')|F('Expansion_BO')|F('Gilligans_Buy')|F('Lizard_Bull')
    cs___=F('Pullback_123_Bear')|F('NonADX_123_Bear')|F('Setup_180_Bear')|F('Boomer_Sell')|F('Expansion_BD')|F('Gilligans_Sell')|F('Lizard_Bear')
    mfb_=(N('RSI_MFI')>N('RSI_MFI').shift(1))|(N('CMF')>.05)|F('MF_Cross_Bull');mfs_=(N('RSI_MFI')<N('RSI_MFI').shift(1))|(N('CMF')<-.05)|F('MF_Cross_Bear')
    n_bl=C<=N('BB_Low')*1.01;n_bu=C>=N('BB_Up')*.99;n_vp=((C-N('VP_VAL')).abs()/(C+1e-10)<.02)&(N('VP_VAL')>0);n_vr=((N('VP_VAH')-C).abs()/(C+1e-10)<.02)&(N('VP_VAH')>0)
    n50=((C-N('MA50')).abs()/(C+1e-10))<.03;wos_=N('WT1')<-53;wob_=N('WT1')>53;sos_=(N('StochK')<20)&(N('StochD')<20);sob_=(N('StochK')>80)&(N('StochD')>80)
    dbc_=F('Bull_Divergence').astype(int)+F('RSI_Bull_Divergence').astype(int)+F('MF_Bull_Div').astype(int)+F('OBV_Div_Buy').astype(int)
    dsc_=F('Bear_Divergence').astype(int)+F('RSI_Bear_Divergence').astype(int)+F('MF_Bear_Div').astype(int)+F('OBV_Div_Sell').astype(int)
    mr_=N('MACD_Hist')>N('MACD_Hist').shift(1);mf_=N('MACD_Hist')<N('MACD_Hist').shift(1);wr_=N('WT1')>N('WT1').shift(1);wf_=N('WT1')<N('WT1').shift(1)
    llw_=(pd.concat([C,O],axis=1).min(axis=1)-L)>(H-L)*.6;luw_=(H-pd.concat([C,O],axis=1).max(axis=1))>(H-L)*.6
    ma20=N('MA20');ma50=N('MA50')
    d20=(C-ma20)/(ma20+1e-10);d50=(C-ma50)/(ma50+1e-10)
    deep_os=(N('WT1')<-65)|(N('RSI')<30)|(N('StochK')<15)
    deep_ob=(N('WT1')>65)|(N('RSI')>70)|(N('StochK')>85)
    down_stretch=(d20<-0.06)|(d50<-0.1)|(C<=N('BB_Low')*0.985)
    up_stretch=(d20>0.06)|(d50>0.1)|(C>=N('BB_Up')*1.015)
    bull_turn=(C>O)&(C>C.shift(1))&(F('WT_Up')|F('MACD_Cross_Buy')|F('StochRSI_Cross_Buy')|F('UTBot_Buy')|F('Hull_Turn_Bull'))
    bear_turn=(C<O)&(C<C.shift(1))&(F('WT_Down')|F('MACD_Cross_Sell')|F('StochRSI_Cross_Sell')|F('UTBot_Sell')|F('Hull_Turn_Bear'))
    ub_=(up_|(C>N('MA50'))).astype(int)+((wr_|F('WT_Up'))&(mr_|(N('MACD_Hist')>0))).astype(int)+(bc_|cb_).astype(int)+vok_.astype(int)+mfb_.astype(int)+(n50|F('BB_Squeeze_End_Bull')|n_vp).astype(int);df['CS_Ultimate_Buy']=ub_>=6
    tos_=(wos_|(N('WT1')<-60))&((N('RSI')<30)|(N('RSI')<35))&sos_;df['CS_Triple_Oversold_Reversal']=tos_&(F('WT_Up')|wr_|bc_|llw_|F('Gold_Dot')|F('Green_Dot_T1'))&vok_
    df['CS_Breakout_Momentum_Buy']=(F('New_52W_High')|F('Expansion_BO')|(C>N('BB_Up')))&adx_ok&(N('Plus_DI')>N('Minus_DI'))&vs_&mr_
    df['CS_Institutional_Accumulation']=(F('Pocket_Pivot')|(F('NR7')&(N('OBV')>N('OBV').shift(5)))|(F('Calm_After_Storm')&(C>O)))&(C>N('MA50'))&(N('CMF')>.05)&(N('OBV')>N('OBV').shift(5))
    df['CS_Divergence_Confluence_Buy']=(dbc_>=2)&(n_bl|n_vp|n50)&(bc_|llw_|F('WT_Up'))&vok_
    el_=F('New_52W_Low')|(C<=C.rolling(252,min_periods=200).min()*1.02);eos_=(N('WT1')<-80)|(wos_&(N('RSI')<25));df['CS_Capitulation_Bottom']=el_&eos_&(vr>=3)&(llw_|F('Hammer')|F('Parabolic_Bottom_Buy'))&(N('MFI')<30)
    df['CS_Triple_Confirm_Buy']=F('UTBot_Buy')&hma_rising&(N('WT1')>N('WT2'))&vok_;df['CS_VuManChu_Squeeze_Buy']=F('VuManChu_Bull')&(F('Squeeze_Fire_Buy')|F('Squeeze_Mom_Cross_Up'))
    us__=(dn_|(C<N('MA50'))).astype(int)+((wf_|F('WT_Down'))&(mf_|(N('MACD_Hist')<0))).astype(int)+(sc__|cs___).astype(int)+vok_.astype(int)+mfs_.astype(int)+(n50|F('BB_Squeeze_End_Bear')|n_vr).astype(int);df['CS_Ultimate_Sell']=us__>=6
    tob_=(wob_|(N('WT1')>60))&((N('RSI')>70)|(N('RSI')>65))&sob_;df['CS_Triple_Overbought_Exhaustion']=tob_&(F('WT_Down')|wf_|sc__|luw_|F('Blood_Diamond')|F('Red_Dot_T1'))&vok_
    df['CS_Breakdown_Momentum_Sell']=(F('New_52W_Low')|F('Expansion_BD')|(C<N('BB_Low')))&adx_ok&(N('Minus_DI')>N('Plus_DI'))&vs_&mf_
    para_=(C>C.shift(10)*1.3)|F('Parabolic_Top_Sell');eob_=(N('WT1')>80)|(wob_&(N('RSI')>75));df['CS_Parabolic_Exhaustion_Sell']=para_&eob_&(luw_|F('Shooting_Star')|sc__)&(vr>=3)
    df['CS_Divergence_Confluence_Sell']=(dsc_>=2)&(n_bu|n_vr|n50)&(sc__|luw_|F('WT_Down'))&vok_
    eh_=F('New_52W_High')|(C>=C.rolling(252,min_periods=200).max()*.98);df['CS_Blow_Off_Top']=eh_&eob_&(vr>=3)&(luw_|F('Shooting_Star')|F('Parabolic_Top_Sell'))&(N('MFI')>70)
    df['CS_Triple_Confirm_Sell']=F('UTBot_Sell')&~hma_rising&(N('WT1')<N('WT2'))&vok_;df['CS_VuManChu_Squeeze_Sell']=F('VuManChu_Bear')&(F('Squeeze_Fire_Sell')|F('Squeeze_Mom_Cross_Down'))
    df['CS_Trend_Pullback_Buy']=up_&(n50|(L<=N('MA20'))&(C>N('MA20')))&(bc_|(C>O))&mfb_;df['CS_Squeeze_Breakout_Buy']=(F('BB_Squeeze_End_Bull')|(F('BB_Squeeze').shift(1)&(C>N('BB_Mid'))&(C>O)))&vok_&mr_
    df['CS_MA_Confluence_Buy']=((N('MA50')>N('MA200'))&(N('MA50')>N('MA50').shift(5)))&(F('MACD_Cross_Buy')|mr_)&vok_&(C>N('MA50'));df['CS_Cooper_Setup_Buy']=cb_&adx_ok&(N('Plus_DI')>N('Minus_DI'))&vok_&(C>N('MA50'))
    df['CS_Volume_Climax_Rev_Buy']=(F('Volume_Climax_Buy')|(vr>=2.5))&(wos_|sos_)&(bc_|llw_)&(n_bl|n_vp);df['CS_Ichimoku_Breakout_Buy']=F('Kumo_Breakout_Bull')&(F('TK_Cross_Bull')|adx_ok)&vok_
    df['CS_Trend_Rejection_Sell']=dn_&(n50|(H>=N('MA20'))&(C<N('MA20')))&(sc__|(C<O))&mfs_;df['CS_Squeeze_Breakdown_Sell']=(F('BB_Squeeze_End_Bear')|(F('BB_Squeeze').shift(1)&(C<N('BB_Mid'))&(C<O)))&vok_&mf_
    df['CS_MA_Breakdown_Sell']=((N('MA50')<N('MA200'))&(N('MA50')<N('MA50').shift(5)))&(F('MACD_Cross_Sell')|mf_)&vok_&(C<N('MA50'));df['CS_Cooper_Setup_Sell']=cs___&adx_ok&(N('Minus_DI')>N('Plus_DI'))&vok_&(C<N('MA50'))
    df['CS_Gap_Failure_Sell']=(F('Gap_Up').shift(1).fillna(False)&sc__&vok_&wf_)|(F('Gap_Up')&(C<O)&vok_)
    os_ctx=(N('WT1')<-55)|(N('RSI')<35)|(N('StochK')<25)
    ob_ctx=(N('WT1')>55)|(N('RSI')>65)|(N('StochK')>75)
    trend_favor_buy=(N('Plus_DI')>=N('Minus_DI'))|(N('ADX')<25)
    trend_favor_sell=(N('Minus_DI')>=N('Plus_DI'))|(N('ADX')<25)

    # Lower-tier mean-reversion setups tightened with momentum confirmation
    df['CS_Oversold_Bounce_Buy']=sos_&bc_&(n50|n_bl)&(wr_|mr_|mfb_)&trend_favor_buy
    df['CS_Overbought_Fade_Sell']=sob_&sc__&(n50|n_bu)&(wf_|mf_|mfs_)&trend_favor_sell

    # New practical combo families
    df['CS_Trend_Continuation_Buy']=up_&(C>N('MA20'))&(F('EMA_Pullback_Buy')|F('MA20_Support')|F('MA50_Support')|F('Diag_Support_Hold')|F('Diag_Breakout_Bull')|F('Box_Support_Hold')|F('Channel_Support_Hold')|F('Box_Breakout_Bull')|F('Channel_Breakout_Bull')|F('Triangle_Breakout_Bull'))&(wr_|mr_)&(vr>=1.0)&(N('ADX')>=18)
    df['CS_Trend_Continuation_Sell']=dn_&(C<N('MA20'))&(F('EMA_Pullback_Sell')|F('MA20_Resistance')|F('MA50_Resistance')|F('Diag_Resistance_Reject')|F('Diag_Breakdown_Bear')|F('Box_Resistance_Reject')|F('Channel_Resistance_Reject')|F('Box_Breakdown_Bear')|F('Channel_Breakdown_Bear')|F('Triangle_Breakdown_Bear'))&(wf_|mf_)&(vr>=1.0)&(N('ADX')>=18)
    df['CS_Trend_Continuation_Buy']=df['CS_Trend_Continuation_Buy']|(
        up_&(wr_|mr_)&(vr>=0.9)&(N('ADX')>=16)&(F('Fib_50_Support')|F('Fib_618_Support')|F('Fib_618_Reclaim')|F('Fib_Confluence_Buy'))
    )
    df['CS_Trend_Continuation_Sell']=df['CS_Trend_Continuation_Sell']|(
        dn_&(wf_|mf_)&(vr>=0.9)&(N('ADX')>=16)&(F('Fib_50_Resistance')|F('Fib_618_Resistance')|F('Fib_618_Breakdown')|F('Fib_Confluence_Sell'))
    )
    df['CS_Reversal_Cluster_Buy']=(dbc_>=2)&os_ctx&(bc_|llw_|F('Parabolic_Bottom_Buy')|F('Volume_Climax_Buy'))&(wr_|F('UTBot_Buy')|F('Hull_Turn_Bull'))&vok_
    df['CS_Reversal_Cluster_Sell']=(dsc_>=2)&ob_ctx&(sc__|luw_|F('Parabolic_Top_Sell')|F('Volume_Climax_Sell'))&(wf_|F('UTBot_Sell')|F('Hull_Turn_Bear'))&vok_
    df['CS_Breakout_Confirm_Buy']=(F('Expansion_BO')|F('Kumo_Breakout_Bull')|F('BB_Upper_Break')|F('New_52W_High')|F('Box_Breakout_Bull')|F('Channel_Breakout_Bull')|F('Triangle_Breakout_Bull'))&(vr>=1.4)&(N('ADX')>=20)&(N('MACD_Hist')>N('MACD_Hist').shift(1))
    df['CS_Breakout_Confirm_Sell']=(F('Expansion_BD')|F('Kumo_Breakout_Bear')|F('BB_Lower_Break')|F('New_52W_Low')|F('Box_Breakdown_Bear')|F('Channel_Breakdown_Bear')|F('Triangle_Breakdown_Bear'))&(vr>=1.4)&(N('ADX')>=20)&(N('MACD_Hist')<N('MACD_Hist').shift(1))
    df['CS_Breakout_Confirm_Buy']=df['CS_Breakout_Confirm_Buy']|(
        (F('Fib_618_Reclaim')|F('Fib_Confluence_Buy'))&(vr>=1.0)&(N('ADX')>=18)&(N('MACD_Hist')>=N('MACD_Hist').shift(1))
    )
    df['CS_Breakout_Confirm_Sell']=df['CS_Breakout_Confirm_Sell']|(
        (F('Fib_618_Breakdown')|F('Fib_Confluence_Sell'))&(vr>=1.0)&(N('ADX')>=18)&(N('MACD_Hist')<=N('MACD_Hist').shift(1))
    )

    df['CS_Momentum_Accel_Buy']=(N('Composite_Accel',0)>JT.ACCEL_STRONG)&vok_&(C>N('MA50'))
    df['CS_Structure_Support_Buy']=n_vp&n_bl&(C>O)
    df['CS_Volatility_Explosion']=(F('NR7_2').astype(int)+F('BB_Squeeze').astype(int)+(vr<.5).astype(int)+F('Inside_Day').astype(int))>=3
    df['CS_Bottom_Fishing_Buy']=deep_os&down_stretch&bull_turn&(dbc_>=1)&(llw_|bc_|cb_)&vok_
    df['CS_Top_Fishing_Sell']=deep_ob&up_stretch&bear_turn&(dsc_>=1)&(luw_|sc__|cs___)&vok_

    buy_cluster=(df['CS_Reversal_Cluster_Buy']|df['CS_Trend_Continuation_Buy']|df['CS_Breakout_Confirm_Buy'])
    sell_cluster=(df['CS_Reversal_Cluster_Sell']|df['CS_Trend_Continuation_Sell']|df['CS_Breakout_Confirm_Sell'])
    df['CS_Conflict_Warning']=buy_cluster&sell_cluster
    for sn,cfg in COMBINED_SCAN_REGISTRY.items():
        if sn in df.columns:df[sn]=_cooldown(df[sn],bars={1:5,2:7,3:10}.get(cfg.get('tier',2),7))

    # Engine-level multi-signal summary for scanner/metadata reuse.
    buy_cols=[sn for sn,cfg in COMBINED_SCAN_REGISTRY.items() if sn in df.columns and cfg.get('dir')=='buy']
    sell_cols=[sn for sn,cfg in COMBINED_SCAN_REGISTRY.items() if sn in df.columns and cfg.get('dir')=='sell']
    neutral_cols=[sn for sn,cfg in COMBINED_SCAN_REGISTRY.items() if sn in df.columns and cfg.get('dir')=='neutral']
    t1_cols=[sn for sn,cfg in COMBINED_SCAN_REGISTRY.items() if sn in df.columns and cfg.get('tier')==1]
    t2_cols=[sn for sn,cfg in COMBINED_SCAN_REGISTRY.items() if sn in df.columns and cfg.get('tier')==2]
    t3_cols=[sn for sn,cfg in COMBINED_SCAN_REGISTRY.items() if sn in df.columns and cfg.get('tier')==3]
    bcnt=sum(df[c].fillna(False).astype(int) for c in buy_cols) if buy_cols else pd.Series(0,index=idx,dtype=int)
    scnt=sum(df[c].fillna(False).astype(int) for c in sell_cols) if sell_cols else pd.Series(0,index=idx,dtype=int)
    ncnt=sum(df[c].fillna(False).astype(int) for c in neutral_cols) if neutral_cols else pd.Series(0,index=idx,dtype=int)
    t1cnt=sum(df[c].fillna(False).astype(int) for c in t1_cols) if t1_cols else pd.Series(0,index=idx,dtype=int)
    t2cnt=sum(df[c].fillna(False).astype(int) for c in t2_cols) if t2_cols else pd.Series(0,index=idx,dtype=int)
    t3cnt=sum(df[c].fillna(False).astype(int) for c in t3_cols) if t3_cols else pd.Series(0,index=idx,dtype=int)
    mcnt=bcnt+scnt+ncnt
    df['CS_Buy_Count']=bcnt
    df['CS_Sell_Count']=scnt
    df['CS_Neutral_Count']=ncnt
    df['CS_T1_Count']=t1cnt
    df['CS_T2_Count']=t2cnt
    df['CS_T3_Count']=t3cnt
    df['CS_Multi_Count']=mcnt
    df['CS_Multi_Imbalance']=bcnt-scnt
    df['CS_Multi_Signal_On']=(mcnt>=3)|((t1cnt>=1)&(mcnt>=2))
    return df

# ━━━ 10-Layer Scores (시각화용) ━━━
# 추세 추종 + 바닥/천장 반전 포착을 함께 반영하도록 가중치 보강

def compute_10layer_scores(df, vol_ratio, hma_r_v):
    """10-Layer 점수 계산 (추세 + 반전 하이브리드)"""
    C,O,H,L=df['Close'],df['Open'],df['High'],df['Low'];idx=df.index
    N=lambda c,d=0:df.get(c,pd.Series(d,index=idx)).fillna(d);vr=vol_ratio
    history_bars=N('History_Bars',0)
    ma50_ready=history_bars>=JT.MIN_HISTORY_MA50
    ma200_ready=history_bars>=JT.MIN_HISTORY_MA200
    a200=ma200_ready&(C>N('MA200',np.nan));a50=ma50_ready&(C>N('MA50',np.nan));a20=C>N('MA20',np.nan)
    b200=ma200_ready&(C<N('MA200',np.nan));b50=ma50_ready&(C<N('MA50',np.nan));b20=C<N('MA20',np.nan)
    mhr=N('MACD_Hist')>N('MACD_Hist').shift(1);mhf=N('MACD_Hist')<N('MACD_Hist').shift(1)
    rr_=N('RSI')>N('RSI').shift(1);rf_=N('RSI')<N('RSI').shift(1);wr_=N('WT1')>N('WT1').shift(1);wf_=N('WT1')<N('WT1').shift(1)
    obv=N('OBV');obvm=obv.rolling(20,min_periods=10).mean();regime=N('Regime');ca=N('Composite_Accel');pb=N('Percent_B');rmfi=N('RSI_MFI');cmf=N('CMF')
    kumo_a=N('Ichimoku_SenkouA',np.nan);kumo_b=N('Ichimoku_SenkouB',np.nan);kumo_ready=kumo_a.notna()&kumo_b.notna()
    kumo_top=pd.concat([kumo_a,kumo_b],axis=1).max(axis=1);kumo_bot=pd.concat([kumo_a,kumo_b],axis=1).min(axis=1);utbot_dir=N('UTBot_Dir')
    wt1=N('WT1');rsi=N('RSI');stochk=N('StochK');mfi=N('MFI')
    vwap=N('VWAP',np.nan);fixed_vwap=N('Fixed_VWAP',np.nan);psar_dir=N('PSAR_Direction',0)
    supertrend=N('SuperTrend',np.nan);tenkan=N('Ichimoku_Tenkan',np.nan);kijun=N('Ichimoku_Kijun',np.nan)
    willr=N('Williams_R',-50);cci=N('CCI',0);roc=N('ROC',0);rmi=N('RMI',50);trix=N('TRIX',0);price_osc=N('Price_Oscillator',0)
    vol_osc=N('Volume_Oscillator',0);intensity_idx=N('Intraday_Intensity_Index',0);chaikin=N('Chaikin_Oscillator',0)
    env_pct=N('Envelope_Percent',0.5);ma20_gap=N('MA20_ATR_Gap',0)
    channel_up=N('Price_Channel_Up',np.nan);channel_low=N('Price_Channel_Low',np.nan)
    channel_pos=((((C-channel_low)/((channel_up-channel_low)+1e-10))-0.5)*2).clip(-2,2)
    ad_line=N('AD_Line',0);ad_roll=ad_line.rolling(60,min_periods=20)
    ad_z=((ad_line-ad_roll.mean())/(ad_roll.std()+1e-10)).fillna(0)
    dv20=N('Dollar_Volume_20',0);dv_log=np.log10(dv20.clip(lower=1));dv_roll=dv_log.rolling(60,min_periods=20)
    dv_z=((dv_log-dv_roll.mean())/(dv_roll.std()+1e-10)).fillna(0)
    price_above_vwap=vwap.notna()&(C>vwap);price_above_fixed=fixed_vwap.notna()&(C>fixed_vwap)
    price_below_vwap=vwap.notna()&(C<vwap);price_below_fixed=fixed_vwap.notna()&(C<fixed_vwap)
    price_above_super=supertrend.notna()&(C>supertrend);price_below_super=supertrend.notna()&(C<supertrend)
    price_above_tk=tenkan.notna()&kijun.notna()&(C>tenkan)&(C>kijun);price_below_tk=tenkan.notna()&kijun.notna()&(C<tenkan)&(C<kijun)
    cloud_bull=kumo_ready&(C>kumo_top);cloud_bear=kumo_ready&(C<kumo_bot)
    wr_rebound=(willr<=-80)&(willr>willr.shift(1));wr_fade=(willr>=-20)&(willr<willr.shift(1))
    cci_rebound=(cci<=-100)&(cci>cci.shift(1));cci_fade=(cci>=100)&(cci<cci.shift(1))
    F=lambda c:df.get(c,pd.Series(False,index=idx)).fillna(False)
    os_base=((wt1<-60)|(rsi<32)|(stochk<20))&(wr_|(wt1>wt1.shift(1)))
    ob_base=((wt1>60)|(rsi>68)|(stochk>80))&(wf_|(wt1<wt1.shift(1)))
    os_turn=F('UTBot_Buy').rolling(3,min_periods=1).max().astype(bool)|F('Hull_Turn_Bull').rolling(3,min_periods=1).max().astype(bool)|F('MACD_Cross_Buy')|F('StochRSI_Cross_Buy')|F('WT_Up')
    ob_turn=F('UTBot_Sell').rolling(3,min_periods=1).max().astype(bool)|F('Hull_Turn_Bear').rolling(3,min_periods=1).max().astype(bool)|F('MACD_Cross_Sell')|F('StochRSI_Cross_Sell')|F('WT_Down')
    os_rev=os_base&(os_turn|F('Bull_Divergence')|F('RSI_Bull_Divergence')|F('CS_Bottom_Fishing_Buy'))
    ob_rev=ob_base&(ob_turn|F('Bear_Divergence')|F('RSI_Bear_Divergence')|F('CS_Top_Fishing_Sell'))
    # BUY
    # BUY
    bt=pd.Series(0.,index=idx);bt+=a200.astype(float)*2.5+a50.astype(float)*1.5+a20.astype(float)*1;bt+=np.where(N('MA50')>N('MA200'),1.5,0)+np.where(N('Plus_DI')>N('Minus_DI'),1,0)+np.where(N('ST_Direction')==1,1,0);bt+=_sp(df,'Cross_Above_50MA',1)+_sp(df,'Golden_Cross',1.5)+np.where(b200&b50,-2.,0);bt+=np.where((b50|b200)&os_rev,1.8,0)-np.where((a50|a200)&ob_rev,1.2,0)
    bt+=price_above_vwap.astype(float)*0.45+price_above_fixed.astype(float)*0.45+np.where(psar_dir>0,0.6,np.where(psar_dir<0,-0.45,0))
    bt+=price_above_super.astype(float)*0.7+price_above_tk.astype(float)*0.55+cloud_bull.astype(float)*0.8;df['BL_Trend']=bt.clip(-2,JT.TREND_CAP)
    bm=pd.Series(0.,index=idx)
    for s,p in [('MACD_Cross_Buy',2.5),('MACD_Zero_Cross_Buy',2),('StochRSI_Cross_Buy',2),('ADX_Momentum_Buy',2),('VWAP_Bounce_Buy',1.5)]:bm+=_sp(df,s,p)
    bm=bm.clip(upper=6);bm+=np.select([(N('MACD_Hist')>0)&mhr,(N('MACD_Hist')>0)&mhf,(N('MACD_Hist')<0)&mhr],[2,.5,1.5],default=0.);
    bm+=np.clip((40-N('RSI'))*0.15,0,3)+rr_.astype(float)+np.clip((25-N('StochK'))*0.15,0,2.5)+np.clip((-10-N('WT1'))*0.05,0,3)+wr_.astype(float)
    bm+=_sp(df,'UTBot_Buy',2.5)+_sp(df,'Hull_Turn_Bull',1.6)+_sp(df,'StochSlow_Cross_Buy',1.5)+_sp(df,'Squeeze_Mom_Cross_Up',1.5)+np.where(hma_r_v&wr_.values,1.2,0)
    bm+=np.where(os_rev,1.5,0)-np.where(ob_rev,1.0,0)+np.where(wr_rebound,0.8,0)+np.where(cci_rebound,0.7,0)
    bm+=np.where(rmi>=55,0.7,np.where(rmi<=45,-0.4,0))+np.where(trix>0,0.5,np.where(trix<0,-0.3,0))
    bm+=np.where(roc>0,0.6,np.where(roc<0,-0.4,0))+np.where(price_osc>0,0.55,np.where(price_osc<0,-0.35,0));df['BL_Momentum']=bm.clip(-2,JT.MOMENTUM_CAP)
    bcc=pd.Series(0.,index=idx)
    for s,p in [('Morning_Star',3.5),('Bullish_Engulfing',3),('Hammer',2.5),('Outside_Bullish',2.5),('Doji_Bullish',1),('Three_Bar_Reversal_Buy',2.5)]:bcc=np.maximum(bcc,_sp(df,s,p))
    df['BL_Candle']=pd.Series(bcc,index=idx).clip(upper=JT.CANDLE_CAP)
    bb_=pd.Series(0.,index=idx);bb_+=_sp(df,'BB_Squeeze_End_Bull',3)+_sp(df,'NR7_2',1.5)+_sp(df,'Calm_After_Storm',1);
    bb_+=np.clip((0.5-pb)*6,-2,3)+_sp(df,'BB_Lower_Bounce',2)+np.where((env_pct<=0.20)&(C>O),1.0,0)-np.where((env_pct>=0.80)&(C<O),0.7,0);df['BL_BB']=bb_.clip(-1,JT.BB_CAP)
    bv=pd.Series(0.,index=idx);bv+=_sp(df,'Volume_Climax_Buy',3)+_sp(df,'Pocket_Pivot',2)+_sp(df,'OBV_Div_Buy',1.5)+_sp(df,'Volume_POC_Breakout',2.5)+_sp(df,'Volume_Dry_Breakout_Buy',2);
    bv+=np.clip((vr-1)*1.5,0,3)*(C>O).astype(float)+np.where(obv>obvm,1,np.where(obv<obvm,-1,0))
    bv+=np.where((vol_osc>0)&(C>O),0.9,np.where((vol_osc<0)&(C<O),-0.7,0))+np.where(dv_z>0.35,0.6,np.where(dv_z<-0.35,-0.5,0))
    bv-=np.where(F('Thin_Trade_Risk'),1.4,0);df['BL_Volume']=bv.clip(-1,JT.VOLUME_CAP)
    bmf=pd.Series(0.,index=idx);bmf+=np.clip(-rmfi*0.2,-0.5,2)+_sp(df,'MF_Cross_Bull',2)+_sp(df,'MF_Bull_Div',2)+_sp(df,'MF_Accel_Up',1)+_sp(df,'CMF_Bull',1.5);
    bmf+=np.clip(cmf*8,-1,2)+np.where(intensity_idx>10,0.9,np.where(intensity_idx<-10,-0.7,0))
    bmf+=np.where(chaikin>0,0.8,np.where(chaikin<0,-0.8,0))+np.where(ad_z>0.4,0.7,np.where(ad_z<-0.4,-0.7,0));df['BL_MF']=bmf.clip(-1,JT.MF_CAP)
    bp=pd.Series(0.,index=idx);bp+=_spd(df,'Gold_Dot',4);bp+=np.where(bp==0,_spd(df,'Green_Dot_T1',2.5),0)
    for s,p in [('Bull_Divergence',2),('Pullback_123_Bull',2.5),('Setup_180_Bull',2),('Boomer_Buy',2),('Expansion_BO',3),('Gilligans_Buy',2.5),('Lizard_Bull',2),('NonADX_123_Bull',1.5),('EMA_Pullback_Buy',2),('Momentum_Ignition_Buy',3),('SuperTrend_Buy',2),('Parabolic_Bottom_Buy',3),('Kumo_Breakout_Bull',2.5),('Reversal_New_Highs',2.5),('Slingshot_Bull',2),('Jack_In_Box_Bull',2),('Relative_Strength_Buy',2.5),('VP_VAL_Support',1.5),('VuManChu_Bull',3),('Hull_Turn_Bull',JT.TURN_SIGNAL_PATTERN_BUY),('Doji_Breakout_Buy',1.5),('Three_Bar_Reversal_Buy',2),('CS_Bottom_Fishing_Buy',3),('CS_Oversold_Bounce_Buy',1.5)]:bp+=_sp(df,s,p)
    bp+=_sp(df,'Diag_Support_Hold',1.8)+_sp(df,'Diag_Breakout_Bull',2.2)
    bp+=_sp(df,'Box_Support_Hold',1.8)+_sp(df,'Channel_Support_Hold',2.0)
    bp+=_sp(df,'Box_Breakout_Bull',2.4)+_sp(df,'Channel_Breakout_Bull',2.5)+_sp(df,'Triangle_Breakout_Bull',2.8)
    bp+=_sp(df,'Fib_382_Support',1.2)+_sp(df,'Fib_50_Support',1.5)+_sp(df,'Fib_618_Support',2.0)
    bp+=_sp(df,'Fib_618_Reclaim',2.2)+_sp(df,'Fib_Confluence_Buy',2.5)
    df['BL_Pattern']=bp.clip(upper=JT.PATTERN_CAP)
    bcs=pd.Series(0.,index=idx)
    for cn,cfg in COMBINED_SCAN_REGISTRY.items():
        if cfg['dir']!='buy' or cn not in df.columns:continue
        bcs+=np.where(df[cn].fillna(False),{1:JT.COMBO_T1,2:JT.COMBO_T2,3:JT.COMBO_T3}.get(cfg['tier'],1),0.)
    df['BL_Combined']=bcs.clip(upper=JT.COMBINED_CAP)
    bl_=pd.Series(0.,index=idx);bl_+=np.clip(ca*2.5,-1,3.5)+_sp(df,'Setup_Squeeze_Bull',1.5)+_sp(df,'Momentum_Accel_Buy',2)+_sp(df,'WT_Convergence_Bull',1.5)+_sp(df,'Volume_Dry_Up',.5)+np.where(os_rev,1.2,0)+_sp(df,'CS_Bottom_Fishing_Buy',2)
    bl_+=np.where(utbot_dir==1,1,np.where(utbot_dir==-1,-.5,0))+np.where(hma_r_v,.5,-.5)
    sp_buy=pd.Series(0.,index=idx);sp_buy+=np.clip((10-N('WT1'))*0.05,0,2)+np.clip((45-N('RSI'))*0.1,0,2)+np.clip((35-N('StochK'))*0.1,0,1)+np.clip((35-mfi)*0.08,0,1.5)+np.clip(ca*1.5,0,2);sp_buy+=np.where(os_rev,1.0,0)
    bl_+=np.where((ma20_gap<=-1.6)&(C>O),1.0,0)-np.where(ma20_gap>=2.4,1.2,0)
    bl_+=np.where((channel_pos<=-0.6)&(C>O),0.7,0)+np.where(price_above_vwap&(channel_pos<0.15),0.45,0)
    bl_-=np.where(F('Fib_Ext_1618_Up_Hit'),1.1,0)
    df['Setup_Pressure_Buy']=sp_buy;bl_+=np.clip(sp_buy*0.4,0,3);df['BL_Leading']=bl_.clip(-1,JT.LEADING_CAP)
    blag=pd.Series(0.,index=idx);blag+=a200.astype(float)*1.0+a50.astype(float)*1.0+((ma50_ready&ma200_ready)&(N('MA50',np.nan)>N('MA200',np.nan))).astype(float)*1.0;
    blag+=np.clip(regime.values*1.0,-1.5,3)+np.where(kumo_ready&(C>kumo_top),1.5,np.where(kumo_ready&(C<kumo_top),-1,0))+np.clip((N('RS_Ratio',1)-1.0)*30,-1.5,2)
    blag+=np.where(price_above_tk,0.6,0)+np.where(price_above_super,0.5,0)+np.where(price_above_fixed,0.35,0);df['BL_Lagging']=blag.clip(-2,JT.LAGGING_CAP)
    
    # SELL
    st_=pd.Series(0.,index=idx);st_+=b200.astype(float)*2.5+b50.astype(float)*1.5+b20.astype(float)*1;st_+=np.where(N('MA50')<N('MA200'),1.5,0)+np.where(N('Minus_DI')>N('Plus_DI'),1,0)+np.where(N('ST_Direction')==-1,1,0);st_+=_sp(df,'Fell_Below_50MA',1)+_sp(df,'Death_Cross',1.5)+np.where(a200&a50,-2.,0);st_+=np.where((a50|a200)&ob_rev,1.8,0)-np.where((b50|b200)&os_rev,1.2,0)
    st_+=price_below_vwap.astype(float)*0.45+price_below_fixed.astype(float)*0.45+np.where(psar_dir<0,0.6,np.where(psar_dir>0,-0.45,0))
    st_+=price_below_super.astype(float)*0.7+price_below_tk.astype(float)*0.55+cloud_bear.astype(float)*0.8;df['SL_Trend']=st_.clip(-2,JT.TREND_CAP)
    sm_=pd.Series(0.,index=idx)
    for s,p in [('MACD_Cross_Sell',2.5),('MACD_Zero_Cross_Sell',2),('StochRSI_Cross_Sell',2),('ADX_Momentum_Sell',2),('VWAP_Reject_Sell',1.5)]:sm_+=_sp(df,s,p)
    sm_=sm_.clip(upper=6);sm_+=np.select([(N('MACD_Hist')<0)&mhf,(N('MACD_Hist')<0)&mhr,(N('MACD_Hist')>0)&mhf],[2,.5,1.5],default=0.);
    sm_+=np.clip((N('RSI')-60)*0.15,0,3)+rf_.astype(float)+np.clip((N('StochK')-75)*0.15,0,2.5)+np.clip((N('WT1')-10)*0.05,0,3)+wf_.astype(float)
    sm_+=_sp(df,'UTBot_Sell',2.1)+_sp(df,'Hull_Turn_Bear',0.9)+_sp(df,'StochSlow_Cross_Sell',1.5)+_sp(df,'Squeeze_Mom_Cross_Down',1.5)+np.where(~hma_r_v&wf_.values,0.8,0)
    sm_+=np.where(ob_rev,1.5,0)-np.where(os_rev,1.0,0)+np.where(wr_fade,0.8,0)+np.where(cci_fade,0.7,0)
    sm_+=np.where(rmi<=45,0.7,np.where(rmi>=55,-0.4,0))+np.where(trix<0,0.5,np.where(trix>0,-0.3,0))
    sm_+=np.where(roc<0,0.6,np.where(roc>0,-0.4,0))+np.where(price_osc<0,0.55,np.where(price_osc>0,-0.35,0));df['SL_Momentum']=sm_.clip(-2,JT.MOMENTUM_CAP)
    scc_=pd.Series(0.,index=idx)
    for s,p in [('Evening_Star',3.5),('Bearish_Engulfing',3),('Shooting_Star',2.5),('Outside_Bearish',2.5),('Doji_Bearish',1),('Three_Bar_Reversal_Sell',2.5)]:scc_=np.maximum(scc_,_sp(df,s,p))
    df['SL_Candle']=pd.Series(scc_,index=idx).clip(upper=JT.CANDLE_CAP)
    sbb_=pd.Series(0.,index=idx);sbb_+=_sp(df,'BB_Squeeze_End_Bear',3)+_sp(df,'NR7_2',1.5)+_sp(df,'Calm_After_Storm',1);
    sbb_+=np.clip((pb-0.5)*6,-2,3)+_sp(df,'BB_Lower_Break',1.5)+np.where((env_pct>=0.80)&(C<O),1.0,0)-np.where((env_pct<=0.20)&(C>O),0.7,0);df['SL_BB']=sbb_.clip(-1,JT.BB_CAP)
    sv_=pd.Series(0.,index=idx);sv_+=_sp(df,'Volume_Climax_Sell',3)+_sp(df,'OBV_Div_Sell',1.5)+_sp(df,'Volume_POC_Breakdown',2.5)+_sp(df,'Volume_Dry_Breakout_Sell',2);
    sv_+=np.clip((vr-1)*1.5,0,3)*(C<O).astype(float)+np.where(obv<obvm,1,np.where(obv>obvm,-1,0))
    sv_+=np.where((vol_osc<0)&(C<O),0.9,np.where((vol_osc>0)&(C>O),-0.7,0))+np.where(dv_z>0.35,0.25,np.where(dv_z<-0.35,0.55,0))
    sv_-=np.where(F('Thin_Trade_Risk'),1.2,0);df['SL_Volume']=sv_.clip(-1,JT.VOLUME_CAP)
    smf_=pd.Series(0.,index=idx);smf_+=np.clip(rmfi*0.2,-0.5,2)+_sp(df,'MF_Cross_Bear',2)+_sp(df,'MF_Bear_Div',2)+_sp(df,'MF_Accel_Dn',1)+_sp(df,'CMF_Bear',1.5);
    smf_+=np.clip(-cmf*8,-1,2)+np.where(intensity_idx<-10,0.9,np.where(intensity_idx>10,-0.7,0))
    smf_+=np.where(chaikin<0,0.8,np.where(chaikin>0,-0.8,0))+np.where(ad_z<-0.4,0.7,np.where(ad_z>0.4,-0.7,0));df['SL_MF']=smf_.clip(-1,JT.MF_CAP)
    spp_=pd.Series(0.,index=idx);spp_+=_spd(df,'Blood_Diamond',4);spp_+=np.where(spp_==0,_spd(df,'Red_Dot_T1',2.5),0)
    for s,p in [('Bear_Divergence',2),('Pullback_123_Bear',2.5),('Setup_180_Bear',2),('Boomer_Sell',2),('Expansion_BD',3),('Gilligans_Sell',2.5),('Lizard_Bear',2),('NonADX_123_Bear',1.5),('EMA_Pullback_Sell',2),('Momentum_Ignition_Sell',3),('SuperTrend_Sell',2),('Parabolic_Top_Sell',3),('Kumo_Breakout_Bear',2.5),('Reversal_New_Lows',2.5),('Slingshot_Bear',2),('Jack_In_Box_Bear',2),('Relative_Strength_Sell',2),('VP_VAH_Resistance',1.5),('VuManChu_Bear',3),('Hull_Turn_Bear',JT.TURN_SIGNAL_PATTERN_SELL),('Doji_Breakout_Sell',1.5),('Three_Bar_Reversal_Sell',2),('CS_Top_Fishing_Sell',3),('CS_Overbought_Fade_Sell',1.5)]:spp_+=_sp(df,s,p)
    spp_+=_sp(df,'Diag_Resistance_Reject',1.8)+_sp(df,'Diag_Breakdown_Bear',2.2)
    spp_+=_sp(df,'Box_Resistance_Reject',1.8)+_sp(df,'Channel_Resistance_Reject',2.0)
    spp_+=_sp(df,'Box_Breakdown_Bear',2.4)+_sp(df,'Channel_Breakdown_Bear',2.5)+_sp(df,'Triangle_Breakdown_Bear',2.8)
    spp_+=_sp(df,'Fib_382_Resistance',1.2)+_sp(df,'Fib_50_Resistance',1.5)+_sp(df,'Fib_618_Resistance',2.0)
    spp_+=_sp(df,'Fib_618_Breakdown',2.2)+_sp(df,'Fib_Confluence_Sell',2.5)
    df['SL_Pattern']=spp_.clip(upper=JT.PATTERN_CAP)
    scs_=pd.Series(0.,index=idx)
    for cn,cfg in COMBINED_SCAN_REGISTRY.items():
        if cfg['dir']!='sell' or cn not in df.columns:continue
        scs_+=np.where(df[cn].fillna(False),{1:JT.COMBO_T1,2:JT.COMBO_T2,3:JT.COMBO_T3}.get(cfg['tier'],1),0.)
    df['SL_Combined']=scs_.clip(upper=JT.COMBINED_CAP)
    sl__=pd.Series(0.,index=idx);sl__+=np.clip(-ca*2.5,-1,3.5)+_sp(df,'Setup_Squeeze_Bear',1.5)+_sp(df,'Momentum_Accel_Sell',2)+_sp(df,'WT_Convergence_Bear',1.5)+np.where(ob_rev,1.2,0)+_sp(df,'CS_Top_Fishing_Sell',2)
    sl__+=np.where(utbot_dir==-1,1,np.where(utbot_dir==1,-.5,0))+np.where(~hma_r_v,.5,-.5)
    sp_sell=pd.Series(0.,index=idx);sp_sell+=np.clip((N('WT1')+10)*0.05,0,2)+np.clip((N('RSI')-55)*0.1,0,2)+np.clip((N('StochK')-65)*0.1,0,1)+np.clip((mfi-65)*0.08,0,1.5)+np.clip(-ca*1.5,0,2);sp_sell+=np.where(ob_rev,1.0,0)
    sl__+=np.where((ma20_gap>=1.6)&(C<O),1.0,0)-np.where(ma20_gap<=-2.4,1.2,0)
    sl__+=np.where((channel_pos>=0.6)&(C<O),0.7,0)+np.where(price_below_vwap&(channel_pos>-0.15),0.45,0)
    sl__-=np.where(F('Fib_Ext_1618_Down_Hit'),1.0,0)
    df['Setup_Pressure_Sell']=sp_sell;sl__+=np.clip(sp_sell*0.4,0,3);df['SL_Leading']=sl__.clip(-1,JT.LEADING_CAP)
    slag_=pd.Series(0.,index=idx);slag_+=b200.astype(float)*1.0+b50.astype(float)*1.0+((ma50_ready&ma200_ready)&(N('MA50',np.nan)<N('MA200',np.nan))).astype(float)*1.0;
    slag_+=np.clip(-regime.values*1.0,-1.5,3)+np.where(kumo_ready&(C<kumo_bot),1.5,np.where(kumo_ready&(C>kumo_top),-1,0))+np.clip((1.0-N('RS_Ratio',1))*30,-1.5,2)
    slag_+=np.where(price_below_tk,0.6,0)+np.where(price_below_super,0.5,0)+np.where(price_below_fixed,0.35,0);df['SL_Lagging']=slag_.clip(-2,JT.LAGGING_CAP)
    LN=['Trend','Momentum','Candle','BB','Volume','MF','Pattern','Combined','Leading','Lagging']
    buy_raw=sum(df[f'BL_{n}'].clip(lower=0) for n in LN)
    sell_raw=sum(df[f'SL_{n}'].clip(lower=0) for n in LN)
    df['Buy_Active_Layers']=sum((df[f'BL_{n}']>0).astype(int) for n in LN)
    df['Sell_Active_Layers']=sum((df[f'SL_{n}']>0).astype(int) for n in LN)

    # Cross-layer conflict/quality modeling for more realistic trade scoring.
    conflict_layers=sum(((df[f'BL_{n}']>0)&(df[f'SL_{n}']>0)).astype(int) for n in LN)
    buy_core=(df['BL_Trend']+df['BL_Momentum']+df['BL_Leading']).clip(lower=0)
    sell_core=(df['SL_Trend']+df['SL_Momentum']+df['SL_Leading']).clip(lower=0)
    buy_quality=(1.0+np.clip((buy_core-sell_core)/36.0,-0.20,0.35)).astype(float)
    sell_quality=(1.0+np.clip((sell_core-buy_core)/36.0,-0.20,0.35)).astype(float)
    conflict_penalty=np.clip(conflict_layers*0.7,0,6).astype(float)

    t1_buy_cols=[cn for cn,cfg in COMBINED_SCAN_REGISTRY.items() if cfg.get('dir')=='buy' and cfg.get('tier')==1 and cn in df.columns]
    t1_sell_cols=[cn for cn,cfg in COMBINED_SCAN_REGISTRY.items() if cfg.get('dir')=='sell' and cfg.get('tier')==1 and cn in df.columns]
    t1_buy_boost=sum(df[col].fillna(False).astype(float) for col in t1_buy_cols) if t1_buy_cols else pd.Series(0.,index=idx)
    t1_sell_boost=sum(df[col].fillna(False).astype(float) for col in t1_sell_cols) if t1_sell_cols else pd.Series(0.,index=idx)

    df['Signal_Conflict_Layers']=conflict_layers
    df['Buy_Quality_Factor']=buy_quality
    df['Sell_Quality_Factor']=sell_quality
    df['Buy_Total']=((buy_raw*buy_quality)+(t1_buy_boost*0.8)-conflict_penalty).clip(lower=0)
    df['Sell_Total']=((sell_raw*sell_quality)+(t1_sell_boost*0.8)-conflict_penalty).clip(lower=0)
    ls_=df['BL_Leading']-df['SL_Leading'];lgs=df['BL_Lagging']-df['SL_Lagging']
    df['Leading_Verdict']=np.select([ls_>3,ls_>1,ls_<-3,ls_<-1],['강한 상승 가속','상승 임박','강한 하락 가속','하락 임박'],default='중립')
    df['Lagging_Verdict']=np.select([lgs>3,lgs>1,lgs<-3,lgs<-1],['강한 상승 추세','상승 추세','강한 하락 추세','하락 추세'],default='비추세/횡보')
    return df

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  🏷️ 판단 이유 자동 생성
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _gen_reason(j,es,ctx,veto,syn,pred,ba,sa,wt1,rsi,mfi,cmf,obv_up,adx,vr,ma50a,ma200a,mh_up,stk,hma_r,ut_dir,sq_on,cms):
    ts,ms,mns,ss,ls=cms.get('Trend',0),cms.get('Momentum',0),cms.get('Money',0),cms.get('Structure',0),cms.get('Leading',0)
    cl=CTX_KOR.get(ctx,'기본')
    if j=='STRONG_BUY':
        if 'Capitul' in veto:return "투매 항복 바닥 확인 — 극과매도+거래량 폭발+강한 반전 캔들",f"WT={wt1:.0f} RSI={rsi:.0f} + Vol {vr:.1f}x 폭발 + 양봉 전환","강력매수 🟢🟢🟢"
        if ctx==CTX_EXTREME_OS and syn>10:return "V자 급반등 가능성 고조 — 투매 종료+모멘텀 전환 확인",f"WT={wt1:.0f} 방향전환 + {ba}개 위원회 매수 + 시너지 {syn:+.1f}","강력매수 🟢🟢🟢"
        if ba>=4:
            f=[];
            if ms>30:f.append(f"모멘텀↑{ms:+.0f}");
            if mns>15:f.append(f"자금유입{mns:+.0f}");
            if ls>20:f.append(f"선행↑{ls:+.0f}")
            return "다중 확인 강세 — 4개 이상 위원회 매수 합의",' + '.join(f) or '전위원회 강세',"강력매수 🟢🟢🟢"
        return "복합 강세 시그널 다중 확인",f"ES={es:+.1f}, {ba}개 위원회 동의, {cl}","강력매수 🟢🟢🟢"
    if j=='STRONG_SELL':
        if 'Blowoff' in veto:return "블로우오프 천장 — 극과매수+거래량 폭발+강한 하락 전환",f"WT={wt1:.0f} RSI={rsi:.0f} + Vol {vr:.1f}x + 음봉","강력매도 🔴🔴🔴"
        if ctx==CTX_EXTREME_OB and syn<-10:return "오버슈팅 한계 도달 — 단기 급락+추세 반전 위험",f"WT={wt1:.0f} 꺾임 + {sa}개 위원회 매도 + 시너지 {syn:+.1f}","강력매도 🔴🔴🔴"
        if sa>=4:
            f=[];
            if ms<-30:f.append(f"모멘텀↓{ms:+.0f}");
            if mns<-15:f.append(f"자금이탈{mns:+.0f}")
            return "전면적 약세 — 다중 하락 확인",' + '.join(f) or '전위원회 약세',"강력매도 🔴🔴🔴"
        return "복합 약세 시그널 다중 확인",f"ES={es:+.1f}, {sa}개 위원회 매도","강력매도 🔴🔴🔴"
    if j=='BUY':
        if ctx in (CTX_ACCUMULATION,CTX_BOTTOMING):return "바닥권 매집 완료 — 박스권 상단 돌파 예상",f"CMF={cmf:.3f} 자금유입 + OBV {'↑' if obv_up else '↓'} + 에너지 축적","매수 🟢🟢"
        if ma50a and ma200a and ms>15:return "상승추세 내 눌림목 — 모멘텀 재가속 확인",f"정배열 + 모멘텀{ms:+.0f} + {'MACD개선' if mh_up else ''}","매수 🟢🟢"
        if sq_on or (ss>15 and ls>10):return "에너지 축적 후 상방 돌파",f"스퀴즈{'해소' if sq_on else ''} + 구조{ss:+.0f} + 선행{ls:+.0f}","매수 🟢🟢"
        if syn>5:return "모멘텀 전환 확인 — 선행지표 주도 추세 전환",f"교차시너지 {syn:+.1f}","매수 🟢🟢"
        return "상승 모멘텀 우위 — 매수 조건 충족",f"ES={es:+.1f}, B{ba}:S{sa}, {cl}","매수 🟢🟢"
    if j=='SELL':
        if ctx in (CTX_DISTRIBUTION,CTX_TOPPING):return "고점 매물 출회+세력 이탈 — 하락 전환 예상",f"CMF={cmf:.3f} 이탈 + OBV {'↓' if not obv_up else '↑'}","매도 🔴🔴"
        if not ma50a and not ma200a and ms<-15:return "하락추세 가속 — 역배열+모멘텀 악화",f"역배열 + 모멘텀{ms:+.0f}","매도 🔴🔴"
        if syn<-5:return "천장 전환 신호 — 모멘텀+선행 하락 경고",f"시너지 {syn:+.1f}","매도 🔴🔴"
        return "하락 모멘텀 우위 — 리스크 관리 필요",f"ES={es:+.1f}","매도 🔴🔴"
    if j=='WATCH_BUY':
        if ctx==CTX_EXTREME_OS:return "과매도 접근 — 반등 준비, 확인 후 진입",f"WT={wt1:.0f} RSI={rsi:.0f}","단기매수 관찰 🟡🟢"
        if pred>5:return "상승 모멘텀 형성 중 — 가속도 개선",f"예측+{pred:+.1f}","단기매수 관찰 🟡🟢"
        if hma_r and ut_dir==1:return "선행지표 강세 전환 — Hull+UTBot 매수",f"Hull↑ + UTBot 매수","단기매수 관찰 🟡🟢"
        return "상승 우위이나 확인 부족",f"ES={es:+.1f}","단기매수 관찰 🟡🟢"
    if j=='WATCH_SELL':
        if ctx==CTX_EXTREME_OB:return "과매수 접근 — 조정 준비, 확인 후 매도",f"WT={wt1:.0f} RSI={rsi:.0f}","단기매도 관찰 🟡🔴"
        if pred<-5:return "하락 모멘텀 형성 중 — 가속도 악화",f"예측{pred:+.1f}","단기매도 관찰 🟡🔴"
        if not hma_r and ut_dir==-1:return "선행지표 약세 전환",f"Hull↓ + UTBot 매도","단기매도 관찰 🟡🔴"
        return "하락 우위이나 확인 부족",f"ES={es:+.1f}","단기매도 관찰 🟡🔴"
    if j=='MIXED':
        if sq_on or ctx==CTX_VOL_DRY:return "에너지 응축 — 변동성 폭발(Squeeze) 직전",f"스퀴즈{'ON' if sq_on else 'OFF'} + 거래량 고갈","관망/대기 🟠"
        if ba>=2 and sa>=2:return "매수·매도 팽팽 — 방향 결정 이벤트 대기",f"B{ba}:S{sa} 균형","관망/대기 🟠"
        return "상반된 시그널 혼재",f"ES={es:+.1f}","관망/대기 🟠"
    # NEUTRAL
    if ctx==CTX_RANGING:return "방향성 부재 — 지지/저항선 이탈 확인 필요",f"ADX={adx:.0f} + 횡보","중립/관망 ⚪"
    if ctx==CTX_VOL_DRY:return "거래량 고갈 — 폭풍 전 고요, 방향성 돌파 대기","거래량↓ + BB수축","중립/관망 ⚪"
    if ctx==CTX_POST_EXPLOSION:return "변동성 폭발 직후 — 방향 확인 단계","대형캔들 후 정착 관찰","중립/관망 ⚪"
    if abs(es)<5:return "시그널 부족 — 명확한 근거 없음",f"ES={es:+.1f}","중립/관망 ⚪"
    return "혼조세 — 추가 확인 대기",f"ES={es:+.1f}, {cl}","중립/관망 ⚪"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  🏛️ 5-Committee Ensemble + 컨텍스트 + Veto + 시너지 + 예측 + 이유
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _detect_context_vectorized(df):
    n=len(df);idx=df.index;N=lambda c,d=0:df.get(c,pd.Series(d,index=idx)).fillna(d)
    C=df['Close'];wt1=N('WT1');rsi=N('RSI');adx=N('ADX');pdi=N('Plus_DI');mdi=N('Minus_DI');cmf=N('CMF');obv=N('OBV')
    history_bars=N('History_Bars',0)
    a50=(history_bars>=JT.MIN_HISTORY_MA50)&(C>N('MA50',np.nan));a200=(history_bars>=JT.MIN_HISTORY_MA200)&(C>N('MA200',np.nan))
    b50=(history_bars>=JT.MIN_HISTORY_MA50)&(C<N('MA50',np.nan));b200=(history_bars>=JT.MIN_HISTORY_MA200)&(C<N('MA200',np.nan));atr=N('ATR')
    vol_avg=df['Volume'].rolling(50,min_periods=10).mean();vr=df['Volume']/(vol_avg+1e-10);obv_ma=obv.rolling(10,min_periods=5).mean()
    prp=(C.rolling(20).max()-C.rolling(20).min())/(C.rolling(20).min()+1e-10);flat=prp<.08
    ma50s=(N('MA50')-N('MA50').shift(10))/(N('MA50').shift(10)+1e-10)*100
    ctx=np.full(n,CTX_DEFAULT,dtype=int)
    ctx=np.where((adx<20)&flat,CTX_RANGING,ctx);ctx=np.where(flat&(cmf<-.05)&(obv<obv_ma)&(vr>=.7),CTX_DISTRIBUTION,ctx)
    ctx=np.where(flat&(cmf>.05)&(obv>obv_ma)&(vr>=.7),CTX_ACCUMULATION,ctx);ctx=np.where((adx>30)&(mdi>pdi)&b50&b200,CTX_STRONG_DN,ctx)
    ctx=np.where((adx>30)&(pdi>mdi)&a50&a200,CTX_STRONG_UP,ctx)
    ctx=np.where((wt1>60)|(rsi>75)|((wt1>50)&(rsi>70)&(N('MFI')>75)),CTX_EXTREME_OB,ctx)
    ctx=np.where((wt1<-60)|(rsi<25)|((wt1<-50)&(rsi<30)&(N('MFI')<25)),CTX_EXTREME_OS,ctx)
    ctx=np.where((ma50s<0)&(ma50s>ma50s.shift(5))&flat&(cmf>0),CTX_BOTTOMING,ctx)
    ctx=np.where((ma50s>0)&(ma50s<ma50s.shift(5))&flat&(cmf<0),CTX_TOPPING,ctx)
    ctx=np.where((vr<0.5)&(N('BB_Width')<N('BB_Width').rolling(60,min_periods=30).quantile(0.1)),CTX_VOL_DRY,ctx)
    wb=(df['High']-df['Low'])>atr*2;pe=wb.shift(1).fillna(False)|wb.shift(2).fillna(False);ctx=np.where(pe&~wb,CTX_POST_EXPLOSION,ctx)
    return pd.Series(ctx,index=idx)


def _stabilize_context_sequence(df, raw_ctx):
    idx=df.index;N=lambda c,d=0:df.get(c,pd.Series(d,index=idx)).fillna(d)
    stable=raw_ctx.astype(int).values.copy();raw_vals=raw_ctx.astype(int).values
    if len(stable)<=1:
        return pd.Series(stable,index=idx)
    C=df['Close'].values;adx=N('ADX',0).values;pdi=N('Plus_DI',0).values;mdi=N('Minus_DI',0).values
    cmf=N('CMF',0).values;wt1=N('WT1',0).values;rsi=N('RSI',50).values;history_bars=N('History_Bars',0).values
    ma50=N('MA50',np.nan).values;ma200=N('MA200',np.nan).values;obv=N('OBV',0).values;obv_ma=N('OBV',0).rolling(10,min_periods=5).mean().values
    trend_inflect_bull=N('Trend_Inflection_Bull',False).values.astype(bool);trend_inflect_bear=N('Trend_Inflection_Bear',False).values.astype(bool)
    market_turn_bull=N('Market_Turn_Bull',False).values.astype(bool);market_turn_bear=N('Market_Turn_Bear',False).values.astype(bool)
    for i in range(1,len(stable)):
        prev=stable[i-1];cur=raw_vals[i]
        if cur==prev:
            continue
        above50=bool((history_bars[i]>=JT.MIN_HISTORY_MA50) and np.isfinite(ma50[i]) and C[i]>ma50[i])
        above200=bool((history_bars[i]>=JT.MIN_HISTORY_MA200) and np.isfinite(ma200[i]) and C[i]>ma200[i])
        below50=bool((history_bars[i]>=JT.MIN_HISTORY_MA50) and np.isfinite(ma50[i]) and C[i]<ma50[i])
        below200=bool((history_bars[i]>=JT.MIN_HISTORY_MA200) and np.isfinite(ma200[i]) and C[i]<ma200[i])
        obv_support=bool(np.isfinite(obv_ma[i]) and obv[i]>=obv_ma[i])
        obv_pressure=bool(np.isfinite(obv_ma[i]) and obv[i]<=obv_ma[i])
        if prev==CTX_STRONG_UP and cur in (CTX_DEFAULT,CTX_RANGING,CTX_EXTREME_OB):
            trend_intact=(adx[i]>=JT.CONTEXT_HOLD_ADX) and (pdi[i]>=mdi[i]) and above50 and above200
            if trend_intact and (rsi[i]>=52) and (wt1[i]>=-15) and not trend_inflect_bear[i] and not market_turn_bear[i]:
                stable[i]=prev
                continue
        if prev==CTX_STRONG_DN and cur in (CTX_DEFAULT,CTX_RANGING,CTX_EXTREME_OS):
            trend_intact=(adx[i]>=JT.CONTEXT_HOLD_ADX) and (mdi[i]>=pdi[i]) and below50 and below200
            if trend_intact and (rsi[i]<=48) and (wt1[i]<=15) and not trend_inflect_bull[i] and not market_turn_bull[i]:
                stable[i]=prev
                continue
        if prev==CTX_ACCUMULATION and cur==CTX_DEFAULT:
            if (cmf[i]>=0.03) and obv_support and not trend_inflect_bear[i]:
                stable[i]=prev
                continue
        if prev==CTX_DISTRIBUTION and cur==CTX_DEFAULT:
            if (cmf[i]<=-0.03) and obv_pressure and not trend_inflect_bull[i]:
                stable[i]=prev
                continue
        if prev==CTX_BOTTOMING and cur==CTX_EXTREME_OS:
            if (cmf[i]>=-0.02) and (wt1[i]>wt1[i-1]) and (rsi[i]>=rsi[i-1]):
                stable[i]=prev
                continue
        if prev==CTX_TOPPING and cur==CTX_EXTREME_OB:
            if (cmf[i]<=0.02) and (wt1[i]<wt1[i-1]) and (rsi[i]<=rsi[i-1]):
                stable[i]=prev
                continue
    return pd.Series(stable,index=idx)

def _committee_trend(df,N):
    C=df['Close'];idx=df.index;score=pd.Series(0.,index=idx)
    history_bars=N('History_Bars',0)
    a200=(history_bars>=JT.MIN_HISTORY_MA200)&(C>N('MA200',np.nan));a50=(history_bars>=JT.MIN_HISTORY_MA50)&(C>N('MA50',np.nan));a20=C>N('MA20',np.nan)
    b200=(history_bars>=JT.MIN_HISTORY_MA200)&(C<N('MA200',np.nan));b50=(history_bars>=JT.MIN_HISTORY_MA50)&(C<N('MA50',np.nan));b20=C<N('MA20',np.nan)
    score += a200.astype(float)*10 + a50.astype(float)*10 + a20.astype(float)*10
    score -= b200.astype(float)*10 + b50.astype(float)*10 + b20.astype(float)*10
    ma50s=(N('MA50')-N('MA50').shift(10))/(N('MA50').shift(10)+1e-10)*100;score+=np.clip(ma50s*3,-15,15)
    adx_val=N('ADX');pdi=N('Plus_DI');mdi=N('Minus_DI');di_diff=pdi-mdi;score+=np.where(adx_val>25,np.clip(di_diff*.5,-15,15),np.clip(di_diff*.2,-5,5))
    score+=np.where(N('ST_Direction')==1,10,np.where(N('ST_Direction')==-1,-10,0))
    senkou_a=N('Ichimoku_SenkouA',np.nan);senkou_b=N('Ichimoku_SenkouB',np.nan);kumo_ready=senkou_a.notna()&senkou_b.notna()
    kt=pd.concat([senkou_a,senkou_b],axis=1).max(axis=1);kb=pd.concat([senkou_a,senkou_b],axis=1).min(axis=1)
    score+=np.where(kumo_ready&(C>kt),10,np.where(kumo_ready&(C<kb),-10,0))
    atr=N('ATR');d50=(C-N('MA50'))/(atr+1e-10);d200=(C-N('MA200'))/(atr+1e-10)
    d50_score=np.where(
        d50>=0,
        np.clip(np.minimum(d50,2.5)*2.0,0,5)-np.clip((d50-4.0)*3.0,0,8),
        -np.clip(np.abs(d50)*3.2,0,14),
    )
    d200_score=np.where(
        d200>=0,
        np.clip(np.minimum(d200,3.0)*1.5,0,4.5)-np.clip((d200-5.0)*2.0,0,6),
        -np.clip(np.abs(d200)*2.8,0,12),
    )
    score += d50_score
    score += d200_score
    wt1=N('WT1');rsi=N('RSI')
    score += np.where((wt1<-60)&(wt1>wt1.shift(1)),10,0)+np.where((wt1>60)&(wt1<wt1.shift(1)),-10,0)
    score += np.where((rsi<35)&(rsi>rsi.shift(1)),6,0)+np.where((rsi>65)&(rsi<rsi.shift(1)),-6,0)
    ma50a=ma50s-ma50s.shift(5);score+=np.where((ma50s<0)&(ma50a>0.5),8,0)+np.where((ma50s>0)&(ma50a<-0.5),-8,0)
    score+=np.clip((N('Trend_Inflection_Buy_Score',0)*JT.TREND_INFLECTION_COMMITTEE_BUY_W)-(N('Trend_Inflection_Sell_Score',0)*JT.BEAR_TURN_SCORE_SCALE*JT.TREND_INFLECTION_COMMITTEE_SELL_W),-24,24)
    score+=np.clip((N('Market_Turn_Bull_Score',0)*3)-(N('Market_Turn_Bear_Score',0)*JT.MARKET_TURN_BEAR_SCALE*3),-12,12)
    ns=(score/JT.TREND_NORM*100).clip(-100,100);conv=np.clip(adx_val.values*2,5,95)
    wt1=wt1.values;rsi=rsi.values;eos=np.clip((-50-wt1)/30,0,1)*.7+np.clip((30-rsi)/20,0,1)*.3;eob=np.clip((wt1-50)/30,0,1)*.7+np.clip((rsi-70)/20,0,1)*.3
    conv=conv*(1-np.maximum(eos,eob)*0.8);conv=np.clip(conv,5,95)
    conv=np.clip(conv+np.maximum(N('Trend_Inflection_Buy_Score',0).values,N('Trend_Inflection_Sell_Score',0).values)*4+np.maximum(N('Market_Turn_Bull_Score',0).values,N('Market_Turn_Bear_Score',0).values)*2,5,95)
    return ns,pd.Series(conv,index=idx)

def _committee_momentum(df,N):
    idx=df.index;score=pd.Series(0.,index=idx);rsi=N('RSI');wt1=N('WT1');wt2=N('WT2');mh=N('MACD_Hist');stk=N('StochK');std=N('StochD');ca=N('Composite_Accel')
    score+=(rsi-50)*.6+np.where(rsi>rsi.shift(1),5,np.where(rsi<rsi.shift(1),-5,0))
    score+=wt1*.3+np.where(wt1>wt2,8,np.where(wt1<wt2,-8,0))+np.where(wt1>wt1.shift(1),5,np.where(wt1<wt1.shift(1),-5,0))
    score+=np.where(mh>mh.shift(1),8,np.where(mh<mh.shift(1),-8,0))+np.where(mh>0,5,np.where(mh<0,-5,0))
    score+=(stk-50)*.2+np.where((stk>std)&(stk<30),10,np.where((stk<std)&(stk>70),-10,0));score+=np.clip(ca*JT.ACCEL_COMMITTEE_MOM,-12,12)
    wv=wt1.values;rv=rsi.values;mv=N('MFI').values;mhv=mh.values
    wtu=(wv<-30)&(wv>np.roll(wv,1));wtd=(wv>30)&(wv<np.roll(wv,1));rtu=(rv<40)&(rv>np.roll(rv,1));rtd=(rv>60)&(rv<np.roll(rv,1))
    bp=wtu.astype(float)+rtu.astype(float)+(mv<35).astype(float)+(mhv>np.roll(mhv,1)).astype(float)
    brp=wtd.astype(float)+rtd.astype(float)+(mv>65).astype(float)+(mhv<np.roll(mhv,1)).astype(float)
    score += np.clip((bp-1)*8.5, 0, 30) - np.clip((brp-1)*8.5, 0, 30)
    score+=np.where((wv<-70)&(wv>np.roll(wv,1)),20,0)+np.where((wv>70)&(wv<np.roll(wv,1)),-20,0)
    ns=(score/JT.MOMENTUM_NORM*100).clip(-100,100)
    ext=np.maximum(np.clip((-wt1.values-30)/40,0,1),np.clip((wt1.values-30)/40,0,1))
    tb=np.where(wtu|wtd,20,0);pb=np.where(bp>=3,15,np.where(brp>=3,15,0));conv=np.clip(40+ext*50+tb+pb,15,98)
    return ns,pd.Series(conv,index=idx)

def _committee_money(df,N):
    idx=df.index;C=df['Close'];score=pd.Series(0.,index=idx);cmf=N('CMF');obv=N('OBV');obv_ma=obv.rolling(20,min_periods=10).mean();F=lambda c:df.get(c,pd.Series(False,index=idx)).fillna(False)
    score+=np.clip(cmf*100,-30,30);obv_r=(obv-obv_ma)/(obv_ma.abs()+1e-10)*100;score+=np.clip(obv_r*.3,-20,20)
    ou=_vs(obv>obv.shift(1));od=_vs(obv<obv.shift(1));score+=np.where(ou>=5,10,np.where(od>=5,-10,0))
    score+=(N('MFI')-50)*.5+np.clip(N('RSI_MFI')*.8,-15,15)
    vol=df['Volume'];va=vol.rolling(50,min_periods=10).mean();vr=vol/(va+1e-10);pd_=np.where(C>C.shift(1),1,np.where(C<C.shift(1),-1,0))
    score += np.clip(vr * 7.5, 0, 20) * pd_
    score+=np.clip(N('OBV_Slope')*12,-15,15)
    score+=np.where(F('Smart_Money_Bullish_Div'),12,0)-np.where(F('Smart_Money_Bearish_Div'),16,0)
    score-=np.where((N('Price_Slope_5')>0)&F('Low_Volume_Caution'),8,0)
    score-=np.where(F('Thin_Trade_Risk')&(N('Price_Slope_5')>0),10,0)
    ns=(score/JT.MONEY_NORM*100).clip(-100,100);vc=np.clip(vr.values*30,10,60);cc=np.clip(np.abs(cmf.values)*100,0,30);divc=np.where(F('Smart_Money_Bullish_Div')|F('Smart_Money_Bearish_Div'),10,0);conv=np.clip(vc+cc+divc,10,95)
    return ns,pd.Series(conv,index=idx)

def _committee_structure(df,N):
    idx=df.index;C=df['Close'];O=df['Open'];score=pd.Series(0.,index=idx);pb=N('Percent_B')
    score += np.clip((0.5 - pb) * 40, -25, 25)
    score+=np.where((pb<.1)&(C>O),10,0)+np.where((pb>.9)&(C<O),-10,0)
    poc=N('VP_POC');vah=N('VP_VAH');val_=N('VP_VAL');dp=(C-poc)/(poc+1e-10)*100
    va_vol = df['Volume'].rolling(50, min_periods=10).mean()
    vr_str = df['Volume'] / (va_vol + 1e-10)
    vp_scalar = np.clip(vr_str.rolling(5).mean().fillna(1.0), 0.5, 2.0)
    score += np.clip((3 - dp.abs()) * 2, -5, 10) * vp_scalar
    score+=np.where(((C-val_).abs()/(C+1e-10)<.02)&(C>O),10,0)+np.where(((vah-C).abs()/(C+1e-10)<.02)&(C<O),-10,0)
    F=lambda c:df.get(c,pd.Series(False,index=idx)).fillna(False)
    cb=F('Morning_Star').astype(float)*20+F('Bullish_Engulfing').astype(float)*15+F('Hammer').astype(float)*12+F('Outside_Bullish').astype(float)*10+F('Doji_Bullish').astype(float)*5+F('Three_Bar_Reversal_Buy').astype(float)*15
    cs=F('Evening_Star').astype(float)*20+F('Bearish_Engulfing').astype(float)*15+F('Shooting_Star').astype(float)*12+F('Outside_Bearish').astype(float)*10+F('Doji_Bearish').astype(float)*5+F('Three_Bar_Reversal_Sell').astype(float)*15
    score+=cb-cs+np.where(F('BB_Squeeze_End_Bull'),15,np.where(F('BB_Squeeze_End_Bear'),-15,0))
    score+=np.where(F('Gap_Down_Closed')&(C>O),10,0)-np.where(F('Gap_Up_Closed')&(C<O),10,0)
    score+=F('Multiple_Ten_Bull').astype(float)*5-F('Multiple_Ten_Bear').astype(float)*5
    score+=np.where(F('Three_Weeks_Tight')&(C>O)&(pb>.55),8,0)-np.where(F('Parabolic_Rise')&(C<O),10,0)
    score+=_sp(df,'Diag_Support_Hold',7)+_sp(df,'Diag_Breakout_Bull',9)-_sp(df,'Diag_Resistance_Reject',7)-_sp(df,'Diag_Breakdown_Bear',9)
    score+=_sp(df,'Box_Support_Hold',7)+_sp(df,'Channel_Support_Hold',8)+_sp(df,'Box_Breakout_Bull',9)+_sp(df,'Channel_Breakout_Bull',10)+_sp(df,'Triangle_Breakout_Bull',11)
    score-=_sp(df,'Box_Resistance_Reject',7)+_sp(df,'Channel_Resistance_Reject',8)+_sp(df,'Box_Breakdown_Bear',9)+_sp(df,'Channel_Breakdown_Bear',10)+_sp(df,'Triangle_Breakdown_Bear',11)
    score+=_sp(df,'Fib_382_Support',4)+_sp(df,'Fib_50_Support',5)+_sp(df,'Fib_618_Support',7)+_sp(df,'Fib_618_Reclaim',8)+_sp(df,'Fib_Confluence_Buy',9)
    score-=_sp(df,'Fib_382_Resistance',4)+_sp(df,'Fib_50_Resistance',5)+_sp(df,'Fib_618_Resistance',7)+_sp(df,'Fib_618_Breakdown',8)+_sp(df,'Fib_Confluence_Sell',9)
    score+=np.where(F('Asc_Triangle')&(C>O),5,0)-np.where(F('Desc_Triangle')&(C<O),5,0)
    score+=np.where(F('Sym_Triangle')&(C>O),2.5,np.where(F('Sym_Triangle')&(C<O),-2.5,0))
    score+=N('Upside_Space_Score')
    score+=np.clip((N('VP_Long_RR')-JT.VP_RR_FLOOR)*12,-18,10)
    score-=np.clip((N('VP_Short_RR')-JT.VP_RR_FLOOR)*12,0,12)
    ns=(score/JT.STRUCTURE_NORM*100).clip(-100,100)
    ne=(pb<.2).astype(float)+(pb>.8).astype(float)+(cb>0).astype(float)+(cs>0).astype(float)+(((C-val_).abs()/(C+1e-10)<.03)|((vah-C).abs()/(C+1e-10)<.03)).astype(float)+F('BB_Squeeze_End_Bull').astype(float)+F('BB_Squeeze_End_Bear').astype(float)+(N('VP_Long_RR')>JT.VP_RR_STRONG).astype(float)+(N('VP_Short_RR')>JT.VP_RR_STRONG).astype(float)+F('Gap_Down_Closed').astype(float)+F('Gap_Up_Closed').astype(float)+F('Three_Weeks_Tight').astype(float)+F('Box_Breakout_Bull').astype(float)+F('Box_Breakdown_Bear').astype(float)+F('Channel_Breakout_Bull').astype(float)+F('Channel_Breakdown_Bear').astype(float)+F('Triangle_Breakout_Bull').astype(float)+F('Triangle_Breakdown_Bear').astype(float)+F('Fib_618_Support').astype(float)+F('Fib_618_Breakdown').astype(float)+F('Fib_Confluence_Buy').astype(float)+F('Fib_Confluence_Sell').astype(float)
    conv=np.clip(ne.values*20+15,10,90)
    return ns,pd.Series(conv,index=idx)

def _committee_leading(df,N):
    idx=df.index;score=pd.Series(0.,index=idx);ut=N('UTBot_Dir');hma=df.get('HMA_Rising',pd.Series(False,index=idx)).fillna(False)
    score+=np.where(ut==1,20,np.where(ut==-1,-20,0))+np.where(hma,15,-15)
    sq=N('Squeeze_Momentum');sr=df.get('Squeeze_Mom_Rising',pd.Series(False,index=idx)).fillna(False)
    score+=np.where(sq>0,10,np.where(sq<0,-10,0))+np.where((sq>0)&sr,5,np.where((sq<0)&~sr,-5,0))
    ca=N('Composite_Accel');score+=np.clip(ca*JT.ACCEL_COMMITTEE_LEAD,-16,16)
    spb=N('Setup_Pressure_Buy');sps=N('Setup_Pressure_Sell')
    score += np.clip(spb * 2, 0, 20) - np.clip(sps * 2, 0, 20)
    F=lambda c:df.get(c,pd.Series(False,index=idx)).fillna(False)
    sq_pos=F('Squeeze_Mom_Positive')
    ut_stop_gap=(df['Close']-N('UTBot_Stop',np.nan))/(N('ATR')+1e-10)
    ut_valid=ut_stop_gap.replace([np.inf,-np.inf],np.nan).notna()
    ut_support_buy=ut_valid&(ut_stop_gap>=0)&(ut_stop_gap<=JT.UTBOT_SUPPORT_MAX_ATR)&(ut==1)
    ut_support_sell=ut_valid&(ut_stop_gap<=0)&((-ut_stop_gap)<=JT.UTBOT_SUPPORT_MAX_ATR)&(ut==-1)
    ut_overheat_buy=ut_valid&(ut_stop_gap>=JT.UTBOT_OVERHEAT_ATR)
    ut_overheat_sell=ut_valid&((-ut_stop_gap)>=JT.UTBOT_OVERHEAT_ATR)
    score+=np.where(sq_pos&(sq>0),6,np.where((~sq_pos)&(sq<0),-6,0))
    score+=np.where(F('Pocket_Pivot'),10,0)+np.where(F('Pocket_Pivot')&F('Three_Weeks_Tight'),8,0)
    score+=np.where(F('Gap_Down_Closed')&(F('Pocket_Pivot')|sq_pos),10,0)-np.where(F('Gap_Up_Closed')&(F('Parabolic_Rise')|F('Volume_Surge')),12,0)
    score+=F('Multiple_Ten_Bull').astype(float)*4-F('Multiple_Ten_Bear').astype(float)*4
    score+=np.where(F('Fib_50_Support'),5,0)+np.where(F('Fib_618_Support'),7,0)+np.where(F('Fib_618_Reclaim'),8,0)
    score-=np.where(F('Fib_50_Resistance'),5,0)+np.where(F('Fib_618_Resistance'),7,0)+np.where(F('Fib_618_Breakdown'),8,0)
    score+=np.where(F('Fib_Confluence_Buy'),8,0)-np.where(F('Fib_Confluence_Sell'),8,0)
    score+=np.where(F('Box_Support_Hold'),6,0)-np.where(F('Box_Resistance_Reject'),6,0)
    score+=np.where(F('Channel_Support_Hold'),7,0)-np.where(F('Channel_Resistance_Reject'),7,0)
    score+=np.where(F('Box_Breakout_Bull'),8,0)-np.where(F('Box_Breakdown_Bear'),8,0)
    score+=np.where(F('Channel_Breakout_Bull'),9,0)-np.where(F('Channel_Breakdown_Bear'),9,0)
    score+=np.where(F('Triangle_Breakout_Bull'),10,0)-np.where(F('Triangle_Breakdown_Bear'),10,0)
    score+=np.where(F('Triangle_Breakout_Bull')&(F('Pocket_Pivot')|sq_pos),6,0)-np.where(F('Triangle_Breakdown_Bear')&(F('Parabolic_Rise')|F('Volume_Surge')),6,0)
    score+=np.where(ut_support_buy,8,0)-np.where(ut_support_sell,8,0)
    score-=np.where(ut_overheat_buy,10,0)
    score+=np.where(ut_overheat_sell,10,0)
    score+=np.clip((N('Trend_Inflection_Buy_Score',0)*JT.TREND_INFLECTION_COMMITTEE_BUY_W*1.05)-(N('Trend_Inflection_Sell_Score',0)*JT.BEAR_TURN_SCORE_SCALE*JT.TREND_INFLECTION_COMMITTEE_SELL_W),-28,28)
    score+=np.clip((N('Market_Turn_Bull_Score',0)*3.5)-(N('Market_Turn_Bear_Score',0)*JT.MARKET_TURN_BEAR_SCALE*3.5),-14,14)
    ma_gap=N('MA20_ATR_Gap');score-=np.clip((ma_gap-1.5)*8,0,20);score+=np.clip((-ma_gap-1.5)*8,0,20)
    for cn,cfg in COMBINED_SCAN_REGISTRY.items():
        if cn not in df.columns:continue
        pts={1:15,2:8,3:3}.get(cfg['tier'],3)
        if cfg['dir']=='buy':score+=np.where(F(cn),pts,0)
        elif cfg['dir']=='sell':score-=np.where(F(cn),pts,0)
    score+=np.where(F('VuManChu_Bull'),20,0)-np.where(F('VuManChu_Bear'),20,0)
    score+=np.where(F('Washout_Bottom_Hard'),35,0)-np.where(F('Blowoff_Top_Hard'),45,0)
    ns=(score/JT.LEADING_NORM*100).clip(-100,100)
    ag=(ut==1).astype(float)+hma.astype(float)+(sq>0).astype(float)+(ca>0).astype(float)+ut_support_buy.astype(float)+F('Pocket_Pivot').astype(float)+F('Gap_Down_Closed').astype(float)+F('Box_Support_Hold').astype(float)+F('Channel_Support_Hold').astype(float)+F('Triangle_Breakout_Bull').astype(float)+F('Fib_618_Support').astype(float)+F('Fib_618_Reclaim').astype(float)+F('Fib_Confluence_Buy').astype(float)
    dg=(ut==-1).astype(float)+(~hma).astype(float)+(sq<0).astype(float)+(ca<0).astype(float)+ut_support_sell.astype(float)+F('Gap_Up_Closed').astype(float)+F('Parabolic_Rise').astype(float)+F('Box_Resistance_Reject').astype(float)+F('Channel_Resistance_Reject').astype(float)+F('Triangle_Breakdown_Bear').astype(float)+F('Fib_618_Resistance').astype(float)+F('Fib_618_Breakdown').astype(float)+F('Fib_Confluence_Sell').astype(float)
    conv=np.clip(np.maximum(ag.values,dg.values)*20+10+np.where(F('Blowoff_Top_Hard')|F('Washout_Bottom_Hard'),12,0),10,90)
    conv=np.clip(conv+np.maximum(N('Trend_Inflection_Buy_Score',0).values,N('Trend_Inflection_Sell_Score',0).values)*4+np.maximum(N('Market_Turn_Bull_Score',0).values,N('Market_Turn_Bear_Score',0).values)*2,10,95)
    return ns,pd.Series(conv,index=idx)

def _normalize_weight_rows(wa):
    wa=np.asarray(wa,dtype=float);rs=wa.sum(axis=1,keepdims=True);rs[rs<=0]=1.
    return wa/rs

def _apply_adx_weight_regime(wa,adx_values):
    wa=_normalize_weight_rows(wa)
    range_mult=np.array([0.70,0.95,1.15,1.25,0.95],dtype=float)
    trend_mult=np.array([1.25,1.20,0.90,0.80,0.95],dtype=float)
    low=np.isfinite(adx_values)&(adx_values<JT.ADX_RANGE_MAX);high=np.isfinite(adx_values)&(adx_values>JT.ADX_TREND_MIN)
    if low.any():wa[low]*=range_mult
    if high.any():wa[high]*=trend_mult
    return _normalize_weight_rows(wa)

def _downgrade_buy(label,severe=False):
    if severe:return 'NEUTRAL'
    return {'STRONG_BUY':'BUY','BUY':'WATCH_BUY','WATCH_BUY':'NEUTRAL'}.get(label,label)

def _downgrade_sell(label,severe=False):
    if severe:return 'NEUTRAL'
    return {'STRONG_SELL':'SELL','SELL':'WATCH_SELL','WATCH_SELL':'NEUTRAL'}.get(label,label)


def _promote_buy(label):
    return {'WATCH_BUY':'BUY','BUY':'STRONG_BUY'}.get(label,label)


def _promote_sell(label):
    return {'WATCH_SELL':'SELL','SELL':'STRONG_SELL'}.get(label,label)


def _judgment_side(label):
    text=str(label or '').upper()
    if text in _OBJECTIVE_BUY_LABELS:
        return 1
    if text in _OBJECTIVE_SELL_LABELS:
        return -1
    return 0


def _default_action_label(label):
    return {
        'STRONG_BUY':'BUY / strongest alignment',
        'BUY':'BUY / trend follow-through',
        'WATCH_BUY':'WATCH BUY / wait for confirmation',
        'NEUTRAL':'NEUTRAL / wait for clarity',
        'MIXED':'MIXED / conflicting evidence',
        'WATCH_SELL':'WATCH SELL / tighten risk',
        'SELL':'SELL / downside pressure',
        'STRONG_SELL':'SELL / strongest downside alignment',
    }.get(str(label or '').upper(),'NEUTRAL / wait for clarity')


def _append_note(base, extra, sep=' | '):
    left=str(base or '').strip()
    right=str(extra or '').strip()
    if not right:
        return left
    if not left:
        return right
    if right in left:
        return left
    return f"{left}{sep}{right}"


def _context_threshold_adjustments(ctx_code):
    buy_adj=0.;sell_adj=0.
    if ctx_code==CTX_EXTREME_OS:
        buy_adj-=10.;sell_adj-=8.
    elif ctx_code==CTX_EXTREME_OB:
        buy_adj+=8.;sell_adj+=10.
    elif ctx_code==CTX_STRONG_UP:
        buy_adj-=5.;sell_adj-=5.
    elif ctx_code==CTX_STRONG_DN:
        buy_adj+=8.;sell_adj+=5.
    elif ctx_code==CTX_ACCUMULATION:
        buy_adj-=4.;sell_adj-=3.
    elif ctx_code==CTX_DISTRIBUTION:
        buy_adj+=5.;sell_adj+=4.
    elif ctx_code==CTX_BOTTOMING:
        buy_adj-=6.;sell_adj-=4.
    elif ctx_code==CTX_TOPPING:
        buy_adj+=6.;sell_adj+=6.
    return buy_adj,sell_adj


def _market_filter_adjustments(
    spy_trend_score,
    breadth_score=0.,
    risk_on=False,
    risk_off=False,
    breadth_risk_on=False,
    breadth_risk_off=False,
    narrow_leadership=False,
    vix_risk_on=False,
    vix_risk_off=False,
    vix_pressure_score=0.,
    tnx_tailwind=False,
    tnx_headwind=False,
    tnx_pressure_score=0.,
    dxy_tailwind=False,
    dxy_headwind=False,
    dxy_pressure_score=0.,
    leader_stock_mode=False,
):
    buy_adj=0.;sell_adj=0.
    bias=np.clip(spy_trend_score*JT.MARKET_ENSEMBLE_SCALE,-6.,6.)
    if risk_off:
        buy_adj+=4.;sell_adj+=4.;bias-=JT.MARKET_RISK_OFF_PENALTY
    elif risk_on:
        buy_adj-=4.;sell_adj-=4.;bias+=JT.MARKET_RISK_ON_BONUS
    elif spy_trend_score>=JT.MARKET_SCORE_TREND_ON:
        buy_adj-=2.;sell_adj-=2.
    elif spy_trend_score<=JT.MARKET_SCORE_TREND_OFF:
        buy_adj+=3.;sell_adj+=2.
    bias+=np.clip(breadth_score*0.75,-1.8,1.8)
    buy_adj-=np.clip(max(breadth_score,0)*0.35,0,1.0)
    buy_adj+=np.clip(max(-breadth_score,0)*0.28,0,1.0)
    if breadth_risk_off:
        buy_adj+=1.5;sell_adj+=1.;bias-=1.6
    elif breadth_risk_on:
        buy_adj-=2.;sell_adj-=1.;bias+=1.2
    if narrow_leadership:
        buy_adj+=0.5;bias-=0.8
    if vix_pressure_score:
        buy_adj+=np.clip(max(vix_pressure_score,0)*0.55,0,2.0)
        sell_adj+=np.clip(max(vix_pressure_score,0)*0.4,0,1.4)
        buy_adj-=np.clip(max(-vix_pressure_score,0)*0.45,0,1.4)
        bias-=np.clip(vix_pressure_score*0.75,-2.2,2.2)
    if vix_risk_off:
        buy_adj+=2.5;sell_adj+=2.;bias-=2.2
    elif vix_risk_on:
        buy_adj-=2.;sell_adj-=1.;bias+=1.5
    if tnx_pressure_score:
        buy_adj+=np.clip(max(tnx_pressure_score,0)*0.3,0,1.1)
        buy_adj-=np.clip(max(-tnx_pressure_score,0)*0.25,0,0.9)
        bias-=np.clip(tnx_pressure_score*0.5,-1.5,1.5)
    if tnx_headwind:
        buy_adj+=1.25;bias-=1.1
    elif tnx_tailwind:
        buy_adj-=1.;bias+=0.8
    if dxy_pressure_score:
        buy_adj+=np.clip(max(dxy_pressure_score,0)*0.3,0,1.1)
        sell_adj+=np.clip(max(dxy_pressure_score,0)*0.25,0,0.8)
        buy_adj-=np.clip(max(-dxy_pressure_score,0)*0.25,0,0.9)
        bias-=np.clip(dxy_pressure_score*0.45,-1.5,1.5)
    if dxy_headwind:
        buy_adj+=1.25;sell_adj+=1.;bias-=1.1
    elif dxy_tailwind:
        buy_adj-=1.;bias+=0.8
    if leader_stock_mode:
        buy_adj-=JT.LEADER_BUY_SUPPORT
        sell_adj-=JT.LEADER_SELL_RELIEF
        if narrow_leadership or breadth_risk_on:
            sell_adj-=1.0
            bias+=0.8
    return np.clip(buy_adj,-12.,12.),np.clip(sell_adj,-12.,12.),np.clip(bias,-12.,12.)


def compute_committee_ensemble(df,vol_ratio,hma_r_v):
    idx=df.index;n=len(df);N=lambda c,d=0:df.get(c,pd.Series(d,index=idx)).fillna(d);F=lambda c:df.get(c,pd.Series(False,index=idx)).fillna(False)
    raw_ctx=_detect_context_vectorized(df);ctx=_stabilize_context_sequence(df,raw_ctx);df['Raw_Market_Context']=raw_ctx;df['Context_Smoothed']=(raw_ctx.values!=ctx.values);df['Market_Context']=ctx
    scores={};convictions={}
    scores['Trend'],convictions['Trend']=_committee_trend(df,N);scores['Momentum'],convictions['Momentum']=_committee_momentum(df,N)
    scores['Money'],convictions['Money']=_committee_money(df,N);scores['Structure'],convictions['Structure']=_committee_structure(df,N)
    scores['Leading'],convictions['Leading']=_committee_leading(df,N)
    for cm in COMMITTEE_NAMES:df[f'CM_{cm}_Score']=scores[cm];df[f'CM_{cm}_Conv']=convictions[cm]
    ctx_v=ctx.values;wa=np.zeros((n,NUM_COMMITTEES))
    for cc,cn in CTX_LABELS.items():
        m=(ctx_v==cc)
        if m.any():wa[m]=CONTEXT_WEIGHTS.get(cn,CONTEXT_WEIGHTS['default'])
    
    wa = pd.DataFrame(wa).ewm(span=3, adjust=False).mean().values
    wa = _apply_adx_weight_regime(wa, N('ADX').values)
    wt1=N('WT1').values;rsi=N('RSI').values;cmf=N('CMF').values;obv=N('OBV').values;obv_ma=N('OBV').rolling(20,min_periods=10).mean().values;C=df['Close'].values;O=df['Open'].values
    vr_v=vol_ratio.values;obv_slope_v=N('OBV_Slope').values;price_slope_v=N('Price_Slope_5').values;long_rr_v=N('VP_Long_RR',1.).values;short_rr_v=N('VP_Short_RR',1.).values
    pv_bear_v=F('Smart_Money_Bearish_Div').values;pv_bull_v=F('Smart_Money_Bullish_Div').values;low_vol_v=F('Low_Volume_Caution').values;hard_blowoff_v=F('Blowoff_Top_Hard').values
    spy_trend_score_v=N('SPY_Trend_Score',0.).values;spy_risk_on_v=F('SPY_Risk_On').values;spy_risk_off_v=F('SPY_Risk_Off').values
    breadth_score_v=N('Market_Breadth_Score',0.).values;breadth_risk_on_v=F('Breadth_Risk_On').values;breadth_risk_off_v=F('Breadth_Risk_Off').values;narrow_leadership_v=F('Narrow_Leadership').values
    vix_risk_on_v=F('VIX_Risk_On').values;vix_risk_off_v=F('VIX_Risk_Off').values;vix_pressure_v=N('VIX_Pressure_Score',0.).values
    tnx_tailwind_v=F('TNX_Tailwind').values;tnx_headwind_v=F('TNX_Headwind').values;tnx_pressure_v=N('TNX_Pressure_Score',0.).values
    dxy_tailwind_v=F('DXY_Tailwind').values;dxy_headwind_v=F('DXY_Headwind').values;dxy_pressure_v=N('DXY_Pressure_Score',0.).values
    macro_pressure_v=N('Macro_Pressure_Score',0.).values;thin_trade_v=F('Thin_Trade_Risk').values
    rs_ratio_v=N('RS_Ratio',1.).values;qqq_rs20_v=N('QQQ_RS_20',0.).values;leader_stock_base_v=F('Leader_Stock_Mode').values;leader_stock_score_v=N('Leader_Stock_Score',0.).values
    trend_inflect_buy_score_v=N('Trend_Inflection_Buy_Score',0.).values;trend_inflect_sell_score_v=N('Trend_Inflection_Sell_Score',0.).values
    trend_inflect_bull_v=F('Trend_Inflection_Bull').values;trend_inflect_bear_v=F('Trend_Inflection_Bear').values
    market_turn_bull_score_v=N('Market_Turn_Bull_Score',0.).values;market_turn_bear_score_v=N('Market_Turn_Bear_Score',0.).values
    market_turn_bull_v=F('Market_Turn_Bull').values;market_turn_bear_v=F('Market_Turn_Bear').values
    pocket_pivot_v=F('Pocket_Pivot').values;three_weeks_tight_v=F('Three_Weeks_Tight').values
    gap_up_closed_v=F('Gap_Up_Closed').values;gap_down_closed_v=F('Gap_Down_Closed').values
    volume_surge_v=F('Volume_Surge').values;parabolic_rise_v=F('Parabolic_Rise').values
    multiple_ten_bull_v=F('Multiple_Ten_Bull').values;multiple_ten_bear_v=F('Multiple_Ten_Bear').values
    squeeze_positive_v=F('Squeeze_Mom_Positive').values;vwap_osc_v=N('VWAP_Osc').values
    diag_support_v=F('Diag_Support_Hold').values;diag_breakout_v=F('Diag_Breakout_Bull').values
    diag_reject_v=F('Diag_Resistance_Reject').values;diag_breakdown_v=F('Diag_Breakdown_Bear').values
    box_support_v=F('Box_Support_Hold').values;box_breakout_v=F('Box_Breakout_Bull').values
    box_reject_v=F('Box_Resistance_Reject').values;box_breakdown_v=F('Box_Breakdown_Bear').values
    channel_support_v=F('Channel_Support_Hold').values;channel_breakout_v=F('Channel_Breakout_Bull').values
    channel_reject_v=F('Channel_Resistance_Reject').values;channel_breakdown_v=F('Channel_Breakdown_Bear').values
    triangle_breakout_v=F('Triangle_Breakout_Bull').values;triangle_breakdown_v=F('Triangle_Breakdown_Bear').values
    asc_triangle_v=F('Asc_Triangle').values;desc_triangle_v=F('Desc_Triangle').values;sym_triangle_v=F('Sym_Triangle').values
    fib_382_support_v=F('Fib_382_Support').values;fib_50_support_v=F('Fib_50_Support').values;fib_618_support_v=F('Fib_618_Support').values
    fib_382_resistance_v=F('Fib_382_Resistance').values;fib_50_resistance_v=F('Fib_50_Resistance').values;fib_618_resistance_v=F('Fib_618_Resistance').values
    fib_618_breakdown_v=F('Fib_618_Breakdown').values;fib_618_reclaim_v=F('Fib_618_Reclaim').values
    fib_confluence_buy_v=F('Fib_Confluence_Buy').values;fib_confluence_sell_v=F('Fib_Confluence_Sell').values
    fib_ext_up_hit_v=F('Fib_Ext_1618_Up_Hit').values;fib_ext_down_hit_v=F('Fib_Ext_1618_Down_Hit').values
    ut_v=N('UTBot_Dir').values;ut_stop_gap_v=((C-N('UTBot_Stop',np.nan).values)/(N('ATR').values+1e-10))
    ut_stop_gap_v=np.where(np.isfinite(ut_stop_gap_v),ut_stop_gap_v,np.nan)
    ut_support_buy_v=np.isfinite(ut_stop_gap_v)&(ut_stop_gap_v>=0)&(ut_stop_gap_v<=JT.UTBOT_SUPPORT_MAX_ATR)&(ut_v==1)
    ut_support_sell_v=np.isfinite(ut_stop_gap_v)&(ut_stop_gap_v<=0)&((-ut_stop_gap_v)<=JT.UTBOT_SUPPORT_MAX_ATR)&(ut_v==-1)
    ut_overheat_buy_v=np.isfinite(ut_stop_gap_v)&(ut_stop_gap_v>=JT.UTBOT_OVERHEAT_ATR)
    ut_overheat_sell_v=np.isfinite(ut_stop_gap_v)&((-ut_stop_gap_v)>=JT.UTBOT_OVERHEAT_ATR)
    hull_turn_bull_v=F('Hull_Turn_Bull').values
    hull_turn_bear_v=F('Hull_Turn_Bear').values
    ut_buy_v=F('UTBot_Buy').values
    ut_sell_v=F('UTBot_Sell').values
    continuation_buy_score_v=(
        pocket_pivot_v.astype(int)
        +(three_weeks_tight_v&squeeze_positive_v).astype(int)
        +(multiple_ten_bull_v&(vwap_osc_v>0)).astype(int)
        +(gap_down_closed_v&(pocket_pivot_v|squeeze_positive_v)).astype(int)
        +(diag_support_v|diag_breakout_v).astype(int)
        +(box_support_v|channel_support_v).astype(int)
        +(box_breakout_v|channel_breakout_v|triangle_breakout_v).astype(int)
        +(fib_382_support_v|fib_50_support_v).astype(int)
        +(fib_618_support_v|fib_618_reclaim_v|fib_confluence_buy_v).astype(int)
        +ut_support_buy_v.astype(int)
    )
    continuation_sell_score_v=(
        ((gap_up_closed_v&(volume_surge_v|parabolic_rise_v))|(multiple_ten_bear_v&(vwap_osc_v<0))).astype(int)
        +(gap_up_closed_v&(vwap_osc_v<0)).astype(int)
        +(diag_reject_v|diag_breakdown_v).astype(int)
        +(box_reject_v|channel_reject_v).astype(int)
        +(box_breakdown_v|channel_breakdown_v|triangle_breakdown_v).astype(int)
        +(fib_382_resistance_v|fib_50_resistance_v).astype(int)
        +(fib_618_resistance_v|fib_618_breakdown_v|fib_confluence_sell_v).astype(int)
        +ut_support_sell_v.astype(int)
        +ut_overheat_buy_v.astype(int)
    )
    bullish_gap_reversal_v=gap_down_closed_v&((pocket_pivot_v|three_weeks_tight_v|box_support_v|channel_support_v)&(squeeze_positive_v|(vwap_osc_v>0)|triangle_breakout_v))
    bearish_gap_failure_v=gap_up_closed_v&((volume_surge_v&parabolic_rise_v)|(vwap_osc_v<0)|multiple_ten_bear_v|box_breakdown_v|channel_breakdown_v|triangle_breakdown_v)
    turn_alignment_buy_v=(
        (hull_turn_bull_v&ut_buy_v)
        | (trend_inflect_bull_v&(hull_turn_bull_v|ut_buy_v))
        | (market_turn_bull_v&hull_turn_bull_v&(continuation_buy_score_v>=2))
    )
    turn_alignment_sell_v=(
        ((hull_turn_bear_v&ut_sell_v) | (trend_inflect_bear_v&(hull_turn_bear_v|ut_sell_v)))
        & ((continuation_sell_score_v>=2)|market_turn_bear_v)
    )
    leader_stock_mode_v=(
        leader_stock_base_v
        | (
            (rs_ratio_v>=JT.LEADER_RS_RATIO)
            & (qqq_rs20_v>=JT.LEADER_QQQ_RS_MIN)
            & ((continuation_buy_score_v>=2)|pocket_pivot_v|three_weeks_tight_v|bullish_gap_reversal_v)
            & (~thin_trade_v)
            & ((breadth_score_v>=-0.5)|breadth_risk_on_v|narrow_leadership_v)
        )
    )
    leader_stock_score_v=np.maximum(
        leader_stock_score_v,
        (
            (rs_ratio_v>=JT.LEADER_RS_RATIO).astype(int)
            +(qqq_rs20_v>=JT.LEADER_QQQ_RS_MIN).astype(int)
            +(continuation_buy_score_v>=2).astype(int)
            +(bullish_gap_reversal_v|pocket_pivot_v|three_weeks_tight_v).astype(int)
            +((breadth_score_v>=0)|breadth_risk_on_v|narrow_leadership_v).astype(int)
        )
    )
    df['UTBot_Stop_ATR_Gap']=ut_stop_gap_v
    df['Continuation_Buy_Score']=continuation_buy_score_v
    df['Continuation_Sell_Score']=continuation_sell_score_v
    df['Bullish_Gap_Reversal']=bullish_gap_reversal_v
    df['Bearish_Gap_Failure']=bearish_gap_failure_v
    df['Leader_Stock_Mode']=leader_stock_mode_v
    df['Leader_Stock_Score']=leader_stock_score_v
    df['Fib_Ext_1618_Up_Hit']=fib_ext_up_hit_v
    df['Fib_Ext_1618_Down_Hit']=fib_ext_down_hit_v
    df['Turn_Alignment_Buy']=turn_alignment_buy_v
    df['Turn_Alignment_Sell']=turn_alignment_sell_v
    wt_hook_up=(wt1>np.roll(wt1,1));wt_hook_dn=(wt1<np.roll(wt1,1))
    flat=((pd.Series(C).rolling(20).max()-pd.Series(C).rolling(20).min())/(pd.Series(C).rolling(20).min()+1e-10)<.08).values
    veto_masks={
        'ExOS':((wt1<-60)|(rsi<JT.VETO_EXTREME_RSI_LO))&wt_hook_up,
        'ExOB':((wt1>60)|(rsi>JT.VETO_EXTREME_RSI_HI))&wt_hook_dn,
        'Accum':flat&(cmf>JT.VETO_MONEY_CMF)&(obv>obv_ma),
        'Distrib':flat&(cmf<-JT.VETO_MONEY_CMF)&(obv<obv_ma),
        'Capitul':(((wt1<-60)|(rsi<JT.VETO_EXTREME_RSI_LO))&wt_hook_up)&(vr_v>=3)&(C>O),
        'Blowoff':(((wt1>60)|(rsi>JT.VETO_EXTREME_RSI_HI))&wt_hook_dn)&(vr_v>=3)&(C<O),
        'PVBearDiv':pv_bear_v,
        'PVBullDiv':pv_bull_v,
        'RRLong':(long_rr_v<JT.VP_RR_FLOOR)&(C>=N('VP_POC').values),
        'RRShort':(short_rr_v<JT.VP_RR_FLOOR)&(C<=N('VP_POC').values),
        'HardBlowoff':hard_blowoff_v,
    }
    veto_names=list(veto_masks.keys());vf=np.column_stack([veto_masks[nm] for nm in veto_names])
    df['Veto_Flags']=pd.Series([','.join([veto_names[j] for j in range(len(veto_names)) if vf[i,j]]) for i in range(n)],index=idx)
    sa=np.column_stack([scores[cm].values for cm in COMMITTEE_NAMES]);ca_=np.column_stack([convictions[cm].values for cm in COMMITTEE_NAMES])
    es=sa.copy();ec=ca_.copy();trend_i,mom_i,money_i,struct_i,lead_i=0,1,2,3,4
    om=veto_masks['ExOS'];tsm=np.abs(np.minimum(es[om,trend_i],0));es[om,trend_i]=np.clip(tsm*0.4,0,30);ec[om,trend_i]=np.minimum(ec[om,trend_i],25);ec[om,mom_i]*=1.4;ec[om,money_i]*=1.3;ec[om,lead_i]*=1.3
    obm=veto_masks['ExOB'];tbm=np.abs(np.maximum(es[obm,trend_i],0));es[obm,trend_i]=-np.clip(tbm*0.4,0,30);ec[obm,trend_i]=np.minimum(ec[obm,trend_i],25);ec[obm,mom_i]*=1.4;ec[obm,money_i]*=1.3;ec[obm,lead_i]*=1.3
    for nm in ('Accum','Distrib'):
        mm=veto_masks[nm];es[mm,trend_i]*=0.3;ec[mm,money_i]*=1.5
    cm_=veto_masks['Capitul']
    for ci in range(NUM_COMMITTEES):sm_=np.abs(np.minimum(es[cm_,ci],0));es[cm_,ci]=np.maximum(es[cm_,ci],0)+sm_*0.3
    ec[cm_,mom_i]=np.clip(ec[cm_,mom_i]*1.5,0,98)
    bom=veto_masks['Blowoff']
    for ci in range(NUM_COMMITTEES):bm_=np.abs(np.maximum(es[bom,ci],0));es[bom,ci]=np.minimum(es[bom,ci],0)-bm_*0.3
    ec[bom,mom_i]=np.clip(ec[bom,mom_i]*1.5,0,98)
    pvb=veto_masks['PVBearDiv']
    if pvb.any():
        es[pvb]=np.where(es[pvb]>0,es[pvb]*(1-JT.DIVERGENCE_PENALTY),es[pvb]);es[pvb,money_i]-=12;es[pvb,struct_i]-=6;ec[pvb,money_i]=np.clip(ec[pvb,money_i]*1.2,0,98)
    pvu=veto_masks['PVBullDiv']
    if pvu.any():
        es[pvu]=np.where(es[pvu]<0,es[pvu]*(1-JT.DIVERGENCE_PENALTY),es[pvu]);es[pvu,money_i]+=12;es[pvu,struct_i]+=6;ec[pvu,money_i]=np.clip(ec[pvu,money_i]*1.2,0,98)
    rrl=veto_masks['RRLong']
    if rrl.any():
        es[rrl]=np.where(es[rrl]>0,es[rrl]*0.85,es[rrl]);es[rrl,struct_i]-=16;ec[rrl,struct_i]=np.clip(ec[rrl,struct_i]*1.15,0,98)
    rrs=veto_masks['RRShort']
    if rrs.any():
        es[rrs]=np.where(es[rrs]<0,es[rrs]*0.85,es[rrs]);es[rrs,struct_i]+=16;ec[rrs,struct_i]=np.clip(ec[rrs,struct_i]*1.15,0,98)
    hbo=veto_masks['HardBlowoff']
    if hbo.any():
        es[hbo]=np.where(es[hbo]>0,es[hbo]*0.60,es[hbo]);es[hbo,trend_i]-=15;es[hbo,mom_i]-=20;es[hbo,lead_i]=np.minimum(es[hbo,lead_i],-55);ec[hbo,lead_i]=np.maximum(ec[hbo,lead_i],85)
    ec=np.clip(ec,0,100)
    # 시너지
    syn=np.zeros(n);ts_=es[:,0];ms_=es[:,1];mns_=es[:,2];ss_=es[:,3];ls_=es[:,4]
    bc=(ms_>20)&(ls_>10)&(ts_<10);bstr=np.clip((ms_+ls_)*0.15+np.abs(np.minimum(ts_,0))*0.1,0,25)
    syn+=np.where(bc,bstr,0)+np.where(bc&(mns_>5),8,0)+np.where(bc&(ss_>10),5,0)
    brc=(ms_<-20)&(ls_<-10)&(ts_>-10);brstr=np.clip((-ms_-ls_)*0.15+np.abs(np.maximum(ts_,0))*0.1,0,25)
    syn-=np.where(brc,brstr,0)+np.where(brc&(mns_<-5),8,0)+np.where(brc&(ss_<-10),5,0)
    df['Reversal_Synergy']=syn
    # 예측
    cav=N('Composite_Accel');ab=np.clip(cav.values*JT.ACCEL_PREDICTION_SCALE,-12,12);mh=N('MACD_Hist');mu=_vs(mh>mh.shift(1));md=_vs(mh<mh.shift(1))
    mb=np.where(mu.values>=3,8,np.where(md.values>=3,-8,0));stk=N('StochK');sb=np.where((stk.values<20)&(stk.values>N('StochD').values),5,np.where((stk.values>80)&(stk.values<N('StochD').values),-5,0))
    pred=ab+mb+sb;df['Prediction_Boost']=pred
    contribs=es*(ec/100.)*wa;ens=contribs.sum(axis=1)+syn+pred
    buy_total_arr=N('Buy_Total').values;sell_total_arr=N('Sell_Total').values
    ba_layers=N('Buy_Active_Layers').values;sa_layers=N('Sell_Active_Layers').values
    layer_edge=buy_total_arr-sell_total_arr
    ens+=np.clip(layer_edge*0.55,-24,24)
    ens+=np.where((ba_layers>=7)&(sa_layers<=2),5,0)
    ens-=np.where((sa_layers>=7)&(ba_layers<=2),5,0)
    conflict_adj=np.clip(np.minimum(ba_layers,sa_layers)*1.3,0,8)
    ens-=np.where(np.abs(layer_edge)<6,conflict_adj,conflict_adj*0.4)
    ens=np.where(veto_masks['PVBearDiv']&(ens>0),ens*(1-JT.DIVERGENCE_PENALTY),ens)
    ens=np.where(veto_masks['PVBullDiv']&(ens<0),ens*(1-JT.DIVERGENCE_PENALTY),ens)
    ens=np.where(veto_masks['RRLong']&(ens>0),ens*0.82,ens)
    ens=np.where(veto_masks['RRShort']&(ens<0),ens*0.82,ens)
    ens=np.where(veto_masks['HardBlowoff']&(ens>0),ens-22,ens)
    ens+=np.where(trend_inflect_buy_score_v>=JT.TREND_INFLECTION_STRONG,np.clip((trend_inflect_buy_score_v-(JT.TREND_INFLECTION_STRONG-1))*JT.TREND_INFLECTION_SIGNAL_BONUS,0,12),0)
    ens-=np.where(trend_inflect_sell_score_v>=JT.TREND_INFLECTION_STRONG,np.clip((trend_inflect_sell_score_v-(JT.TREND_INFLECTION_STRONG-1))*JT.TREND_INFLECTION_SIGNAL_BONUS*JT.BEAR_TURN_SCORE_SCALE,0,9),0)
    ens+=np.where(market_turn_bull_v,np.clip(market_turn_bull_score_v*JT.MARKET_TURN_SIGNAL_BONUS,0,10),0)
    ens-=np.where(market_turn_bear_v,np.clip(market_turn_bear_score_v*JT.MARKET_TURN_SIGNAL_BONUS*JT.MARKET_TURN_BEAR_SCALE,0,8),0)
    ens+=np.where(turn_alignment_buy_v,JT.TURN_ALIGNMENT_BONUS_BUY,0)
    ens-=np.where(turn_alignment_sell_v,JT.TURN_ALIGNMENT_BONUS_SELL,0)
    ens+=np.where(continuation_buy_score_v>=2,np.clip((continuation_buy_score_v-1)*JT.CONTINUATION_SIGNAL_BONUS,0,12),0)
    ens-=np.where(continuation_sell_score_v>=2,np.clip((continuation_sell_score_v-1)*JT.CONTINUATION_SIGNAL_BONUS,0,12),0)
    ens=np.where(bearish_gap_failure_v&(ens>0),ens-JT.TRAP_SIGNAL_PENALTY,ens)
    ens=np.where(bullish_gap_reversal_v&(ens<0),ens+JT.TRAP_SIGNAL_PENALTY*0.85,ens)
    ens=np.where(ut_overheat_buy_v&(ens>0),ens-4.5,ens)
    ens=np.where(ut_overheat_sell_v&(ens<0),ens+4.5,ens)
    ens=np.where(fib_ext_up_hit_v&(ens>0),ens-2.5,ens)
    ens=np.where(fib_ext_down_hit_v&(ens<0),ens+2.0,ens)
    market_buy_adj=np.zeros(n);market_sell_adj=np.zeros(n);market_bias=np.zeros(n)
    for i in range(n):
        market_buy_adj[i],market_sell_adj[i],market_bias[i]=_market_filter_adjustments(
            float(spy_trend_score_v[i]),
            float(breadth_score_v[i]),
            bool(spy_risk_on_v[i]),
            bool(spy_risk_off_v[i]),
            bool(breadth_risk_on_v[i]),
            bool(breadth_risk_off_v[i]),
            bool(narrow_leadership_v[i]),
            bool(vix_risk_on_v[i]),
            bool(vix_risk_off_v[i]),
            float(vix_pressure_v[i]),
            bool(tnx_tailwind_v[i]),
            bool(tnx_headwind_v[i]),
            float(tnx_pressure_v[i]),
            bool(dxy_tailwind_v[i]),
            bool(dxy_headwind_v[i]),
            float(dxy_pressure_v[i]),
            bool(leader_stock_mode_v[i]),
        )
    df['Market_Filter_Bias']=market_bias
    for ci,cm in enumerate(COMMITTEE_NAMES):
        s=es[:,ci];c=ec[:,ci];v=np.full(n,0,dtype=int);v=np.where((s>15)&(c>=25),1,v);v=np.where((s<-15)&(c>=25),-1,v);v=np.where(c<15,-99,v)
        df[f'CM_{cm}_Vote']=v;df[f'CM_{cm}_EffScore']=es[:,ci];df[f'CM_{cm}_EffConv']=ec[:,ci]
    df['Ensemble_Score']=ens
    # 판단
    bag=np.zeros(n,dtype=int);sag=np.zeros(n,dtype=int)
    for ci in range(NUM_COMMITTEES):bag+=((es[:,ci]>15)&(ec[:,ci]>=25)).astype(int);sag+=((es[:,ci]<-15)&(ec[:,ci]>=25)).astype(int)
    bag+=((ba_layers>=6)&(buy_total_arr>=20)).astype(int)
    sag+=((sa_layers>=6)&(sell_total_arr>=20)).astype(int)
    j=np.full(n,'NEUTRAL',dtype=object);pre_veto_j=np.full(n,'NEUTRAL',dtype=object);conf=np.zeros(n,dtype=float)
    downgrade_count=np.zeros(n,dtype=int);macro_risk_off_count_arr=np.zeros(n,dtype=int);macro_risk_on_count_arr=np.zeros(n,dtype=int);flip_guard_triggered=np.zeros(n,dtype=bool)
    rs=[];rd=[];al=[];contrast_notes=[]
    obv_v=N('OBV').values;obv_mav=N('OBV').rolling(20,min_periods=10).mean().values;mhv=N('MACD_Hist').values;mhpv=np.roll(mhv,1)
    ma50_v=N('MA50').values;ma200_v=N('MA200').values;wt1_v=N('WT1').values;rsi_v=N('RSI').values;mfi_v=N('MFI').values
    adx_v=N('ADX').values;stoch_v=N('StochK').values;ut_v=N('UTBot_Dir').values;sq_v=df.get('Squeeze_On',pd.Series(False,index=idx)).values
    washout_bottom_v=F('Washout_Bottom_Hard').values
    atr_norm = (N('ATR').values / (C + 1e-10)) * 100
    atr_scale = np.clip(atr_norm / 2.5, 0.75, 1.25)
    buy_labels=('STRONG_BUY','BUY','WATCH_BUY');sell_labels=('STRONG_SELL','SELL','WATCH_SELL');money_eff=es[:,money_i]
    for i in range(n):
        e=ens[i];ba=bag[i];sl=sag[i];sy=syn[i];sr=1 if abs(sy)>=15 else 0
        asc = atr_scale[i]
        above_ma50=bool(C[i]>ma50_v[i]) if not np.isnan(ma50_v[i]) else False
        above_ma200=bool(C[i]>ma200_v[i]) if not np.isnan(ma200_v[i]) else False
        leader_mode=bool(leader_stock_mode_v[i])
        macro_risk_off_count=int(bool(spy_risk_off_v[i]))+int(bool(breadth_risk_off_v[i]))+int(bool(vix_risk_off_v[i]))+int(bool(tnx_headwind_v[i]))+int(bool(dxy_headwind_v[i]))
        macro_risk_on_count=int(bool(spy_risk_on_v[i]))+int(bool(breadth_risk_on_v[i]))+int(bool(vix_risk_on_v[i]))+int(bool(tnx_tailwind_v[i]))+int(bool(dxy_tailwind_v[i]))
        buy_adj,sell_adj=_context_threshold_adjustments(int(ctx_v[i]))
        buy_adj+=market_buy_adj[i];sell_adj+=market_sell_adj[i]
        early_bull_turn=((trend_inflect_buy_score_v[i]>=JT.TREND_INFLECTION_STRONG) and (market_turn_bull_v[i] or continuation_buy_score_v[i]>=2 or ctx_v[i] in (CTX_BOTTOMING,CTX_EXTREME_OS)))
        early_bear_turn=((trend_inflect_sell_score_v[i]>=JT.TREND_INFLECTION_STRONG+1) and ((market_turn_bear_v[i] and continuation_sell_score_v[i]>=2) or ctx_v[i] in (CTX_TOPPING,CTX_EXTREME_OB)))
        if early_bull_turn:
            buy_adj-=3.2
            sell_adj-=1.0
        if early_bear_turn:
            sell_adj+=0.9
        if leader_mode:
            buy_adj-=0.6
            sell_adj-=5.5
        sbt=(JT.STRONG_BUY_TH * asc)+buy_adj;bt=(JT.BUY_TH * asc)+buy_adj;wbt=(JT.WATCH_BUY_TH * asc)+buy_adj*.5
        sst=(JT.STRONG_SELL_TH * asc)+sell_adj;st=(JT.SELL_TH * asc)+sell_adj;wst=(JT.WATCH_SELL_TH * asc)+sell_adj*.5
        if continuation_buy_score_v[i]>=2 and not ut_overheat_buy_v[i]:
            bt-=0.8
            wbt-=2.4
        if ut_overheat_buy_v[i] or bearish_gap_failure_v[i]:
            sbt+=4.0
        buy_supportive_stack=(
            (continuation_buy_score_v[i]>=3)
            or bullish_gap_reversal_v[i]
            or diag_support_v[i]
            or diag_breakout_v[i]
            or box_breakout_v[i]
            or channel_breakout_v[i]
            or triangle_breakout_v[i]
        )
        buy_supportive_stack_light=(
            (continuation_buy_score_v[i]>=2)
            or bullish_gap_reversal_v[i]
            or diag_support_v[i]
            or box_support_v[i]
            or channel_support_v[i]
            or leader_mode
        )
        sell_supportive_stack=(
            (continuation_sell_score_v[i]>=3)
            or bearish_gap_failure_v[i]
            or diag_reject_v[i]
            or diag_breakdown_v[i]
            or box_breakdown_v[i]
            or channel_breakdown_v[i]
            or triangle_breakdown_v[i]
            or hard_blowoff_v[i]
        )
        buy_confirm_count=(
            int(continuation_buy_score_v[i]>=2)
            +int(bullish_gap_reversal_v[i])
            +int(diag_support_v[i] or diag_breakout_v[i] or box_support_v[i] or channel_support_v[i] or box_breakout_v[i] or channel_breakout_v[i] or triangle_breakout_v[i])
            +int(market_turn_bull_v[i])
            +int(trend_inflect_buy_score_v[i]>=JT.TREND_INFLECTION_STRONG)
            +int(vr_v[i]>=JT.STRONG_BUY_MIN_VOL_RATIO)
            +int(above_ma50)
            +int(above_ma200)
        )
        sell_confirm_count=(
            int(continuation_sell_score_v[i]>=2)
            +int(bearish_gap_failure_v[i])
            +int(diag_reject_v[i] or diag_breakdown_v[i] or box_reject_v[i] or channel_reject_v[i] or box_breakdown_v[i] or channel_breakdown_v[i] or triangle_breakdown_v[i])
            +int(market_turn_bear_v[i])
            +int(trend_inflect_sell_score_v[i]>=JT.TREND_INFLECTION_STRONG+1)
            +int(macro_risk_off_count>=3)
            +int(breadth_risk_off_v[i])
            +int(not above_ma50)
            +int(not above_ma200)
        )
        strong_buy_ready=(
            (continuation_buy_score_v[i]>=JT.STRONG_BUY_CONTINUATION_MIN)
            and (buy_confirm_count>=5)
            and (bullish_gap_reversal_v[i] or diag_breakout_v[i] or box_breakout_v[i] or channel_breakout_v[i] or triangle_breakout_v[i] or pocket_pivot_v[i] or three_weeks_tight_v[i] or fib_confluence_buy_v[i])
            and (not ut_overheat_buy_v[i])
            and (not bearish_gap_failure_v[i])
            and (not thin_trade_v[i])
            and (vr_v[i]>=JT.STRONG_BUY_MIN_VOL_RATIO)
            and (long_rr_v[i]>=0.95)
            and above_ma50
            and (above_ma200 or leader_mode or bullish_gap_reversal_v[i])
            and (macro_risk_off_count<4)
        )
        buy_ready=(
            (buy_confirm_count>=3)
            and (
                (continuation_buy_score_v[i]>=2)
                or buy_supportive_stack_light
                or bullish_gap_reversal_v[i]
                or market_turn_bull_v[i]
                or trend_inflect_buy_score_v[i]>=JT.TREND_INFLECTION_STRONG
            )
        )
        watch_buy_ready=(
            (continuation_buy_score_v[i]>=2)
            or bullish_gap_reversal_v[i]
            or buy_supportive_stack_light
            or early_bull_turn
            or ut_support_buy_v[i]
        )
        sell_breakdown_stack=(
            bearish_gap_failure_v[i]
            or diag_breakdown_v[i]
            or box_breakdown_v[i]
            or channel_breakdown_v[i]
            or triangle_breakdown_v[i]
            or fib_618_breakdown_v[i]
            or fib_confluence_sell_v[i]
        )
        strong_sell_ready=(
            (sell_confirm_count>=JT.STRONG_SELL_CONFIRM_MIN)
            and (
                hard_blowoff_v[i]
                or (
                    sell_supportive_stack
                    and (continuation_sell_score_v[i]>=4)
                    and sell_breakdown_stack
                    and ((macro_risk_off_count>=3) or breadth_risk_off_v[i] or ctx_v[i] in (CTX_STRONG_DN,CTX_DISTRIBUTION,CTX_TOPPING,CTX_EXTREME_OB))
                    and (not above_ma50)
                    and (not above_ma200)
                )
            )
        )
        sell_ready=(
            (sell_confirm_count>=JT.SELL_CONFIRM_MIN)
            and (
                hard_blowoff_v[i]
                or (
                    (continuation_sell_score_v[i]>=3)
                    and (sell_breakdown_stack or diag_reject_v[i] or box_reject_v[i] or channel_reject_v[i])
                    and ((macro_risk_off_count>=2) or breadth_risk_off_v[i] or (not above_ma50) or (not above_ma200))
                )
            )
        )
        watch_sell_ready=(
            hard_blowoff_v[i]
            or (
                (sell_confirm_count>=JT.WATCH_SELL_CONFIRM_MIN)
                and (
                    continuation_sell_score_v[i]>=2
                    or bearish_gap_failure_v[i]
                    or diag_reject_v[i]
                    or box_reject_v[i]
                    or channel_reject_v[i]
                    or market_turn_bear_v[i]
                )
            )
        )
        if leader_mode:
            strong_sell_ready=strong_sell_ready and (
                hard_blowoff_v[i]
                or (
                    ((macro_risk_off_count>=3) or breadth_risk_off_v[i])
                    and bearish_gap_failure_v[i]
                    and (diag_breakdown_v[i] or box_breakdown_v[i] or channel_breakdown_v[i] or triangle_breakdown_v[i] or continuation_sell_score_v[i]>=4)
                    and (not above_ma50)
                    and (not above_ma200)
                )
            )
            sell_ready=sell_ready and (
                hard_blowoff_v[i]
                or (
                    ((macro_risk_off_count>=3) or breadth_risk_off_v[i])
                    and (bearish_gap_failure_v[i] or diag_breakdown_v[i] or box_breakdown_v[i] or channel_breakdown_v[i] or triangle_breakdown_v[i] or continuation_sell_score_v[i]>=4)
                )
            )
            if not (macro_risk_off_count>=2 or breadth_risk_off_v[i] or hard_blowoff_v[i] or bearish_gap_failure_v[i]):
                watch_sell_ready=False
        high_conflict=(
            (buy_total_arr[i]>=JT.HIGH_CONFLICT_TOTAL)
            and (sell_total_arr[i]>=JT.HIGH_CONFLICT_TOTAL)
            and (abs(layer_edge[i])<=JT.HIGH_CONFLICT_EDGE)
            and (abs(e)<=JT.HIGH_CONFLICT_ENSEMBLE)
            and (ba>=2)
            and (sl>=2)
        )
        if high_conflict:
            j[i]='MIXED'
        elif e>=sbt and ba>=(JT.STRONG_MIN_AGREE-sr) and strong_buy_ready:j[i]='STRONG_BUY'
        elif e>=bt and ba>=(JT.BUY_MIN_AGREE-sr):
            j[i]='BUY' if buy_ready else ('WATCH_BUY' if watch_buy_ready else 'NEUTRAL')
        elif e>=wbt and ba>=max(JT.WATCH_MIN_AGREE-sr,1) and watch_buy_ready:j[i]='WATCH_BUY'
        elif e<=sst and sl>=(JT.STRONG_MIN_AGREE-sr) and strong_sell_ready:j[i]='STRONG_SELL'
        elif e<=st and sl>=(JT.BUY_MIN_AGREE-sr):
            j[i]='SELL' if sell_ready else ('WATCH_SELL' if watch_sell_ready else 'NEUTRAL')
        elif e<=wst and sl>=max(JT.WATCH_MIN_AGREE-sr,1) and watch_sell_ready:j[i]='WATCH_SELL'
        elif (ctx_v[i] in (CTX_EXTREME_OS,CTX_BOTTOMING)) and ba>=2 and (sy>6 or pred[i]>5) and e>=(wbt-6):
            j[i]='BUY' if buy_ready else 'WATCH_BUY'
        elif (ctx_v[i] in (CTX_EXTREME_OB,CTX_TOPPING)) and sl>=2 and (sy<-6 or pred[i]<-5) and e<=(wst+6) and watch_sell_ready:
            j[i]='WATCH_SELL'
        elif ba>=3 and sl>=3:j[i]='MIXED'
        pre_veto_j[i]=j[i]
        notes=[];signal_notes=[]
        if high_conflict:notes.append("buy/sell pressure conflict stayed elevated")
        macro_risk_off_count_arr[i]=macro_risk_off_count;macro_risk_on_count_arr[i]=macro_risk_on_count
        if macro_risk_off_count>=3:notes.append("macro backdrop stayed risk-off")
        elif macro_risk_on_count>=2 and j[i] in sell_labels:notes.append("macro backdrop stayed risk-on")
        if macro_pressure_v[i]>=3.2:notes.append("macro pressure magnitude stayed elevated")
        elif macro_pressure_v[i]<=-2.5 and j[i] in sell_labels:notes.append("macro pressure eased materially")
        if market_turn_bull_v[i]:signal_notes.append("market turn stack improved early")
        if market_turn_bear_v[i]:
            if sell_supportive_stack or macro_risk_off_count>=3:
                notes.append("market turn stack turned defensive early")
            else:
                signal_notes.append("market turn stack turned cautious")
        if trend_inflect_bull_v[i]:signal_notes.append("early trend-turn stack fired")
        if trend_inflect_bear_v[i]:
            if sell_supportive_stack or macro_risk_off_count>=3:
                notes.append("early trend-turn stack rolled over")
            else:
                signal_notes.append("early trend-turn stack softened")
        if narrow_leadership_v[i]:notes.append("index leadership stayed narrow")
        if leader_mode:signal_notes.append("leader / theme-stock mode stayed active")
        if pv_bear_v[i]:notes.append("price up but OBV/CMF/volume diverged")
        elif pv_bull_v[i]:notes.append("price down but money flow improved")
        if low_vol_v[i] and price_slope_v[i]>0:notes.append("volume below 0.7x average")
        if thin_trade_v[i]:notes.append("20-day dollar volume stayed thin")
        if long_rr_v[i]<JT.VP_RR_FLOOR and e>0:notes.append(f"long RR {long_rr_v[i]:.2f} vs VAH/POC")
        if short_rr_v[i]<JT.VP_RR_FLOOR and e<0:notes.append(f"short RR {short_rr_v[i]:.2f} vs VAL/POC")
        if hard_blowoff_v[i]:notes.append("blow-off top >3 ATR above MA20 with 2x red volume")
        if continuation_buy_score_v[i]>=2:signal_notes.append("continuation-quality stack stayed aligned")
        if continuation_sell_score_v[i]>=2:notes.append("exhaustion / failure stack stayed aligned")
        if bullish_gap_reversal_v[i]:signal_notes.append("gap-down reversal recovered quickly")
        if bearish_gap_failure_v[i]:notes.append("gap-up failed to hold and looked trap-prone")
        if box_breakout_v[i]:signal_notes.append("box breakout confirmed with follow-through")
        elif box_support_v[i]:signal_notes.append("box support held on pullback")
        if channel_breakout_v[i]:signal_notes.append("rising channel pushed to a fresh breakout")
        elif channel_support_v[i]:signal_notes.append("channel support held and trend stayed intact")
        if triangle_breakout_v[i]:signal_notes.append("triangle compression resolved to the upside")
        if box_breakdown_v[i] or channel_breakdown_v[i] or triangle_breakdown_v[i]:
            notes.append("structure breakdown confirmed under support")
        elif box_reject_v[i] or channel_reject_v[i]:
            notes.append("overhead structure rejected the bounce")
        if asc_triangle_v[i] and not triangle_breakout_v[i]:
            signal_notes.append("ascending triangle stayed constructive")
        elif desc_triangle_v[i] and not triangle_breakdown_v[i]:
            notes.append("descending triangle kept pressure overhead")
        elif sym_triangle_v[i] and not triangle_breakout_v[i] and not triangle_breakdown_v[i]:
            notes.append("symmetrical triangle still needed resolution")
        if ut_overheat_buy_v[i] and j[i] in buy_labels:notes.append("price stretched far above UT stop")
        severe_buy=(money_eff[i]<=JT.MONEY_VETO_NEUTRAL) or (cmf[i]<0 and obv_slope_v[i]<0 and long_rr_v[i]<0.9)
        severe_sell=(money_eff[i]>=abs(JT.MONEY_VETO_NEUTRAL)) or (cmf[i]>0 and obv_slope_v[i]>0 and short_rr_v[i]<0.9)
        countertrend_buy_risk=(
            ctx_v[i] in (CTX_STRONG_DN,CTX_DISTRIBUTION)
            and (not above_ma50)
            and (not above_ma200)
            and (money_eff[i]<0 or long_rr_v[i]<1.15)
            and not washout_bottom_v[i]
            and 'Capitul' not in df['Veto_Flags'].iloc[i]
        )
        countertrend_sell_risk=(
            ctx_v[i] in (CTX_STRONG_UP,CTX_ACCUMULATION)
            and above_ma50
            and above_ma200
            and (money_eff[i]>0 or short_rr_v[i]<1.15)
            and not hard_blowoff_v[i]
        )
        market_sell_headwind=((macro_risk_on_count>=2) or leader_mode) and not hard_blowoff_v[i] and ((money_eff[i]>-5) or (short_rr_v[i]<1.45) or (continuation_buy_score_v[i]>=2))
        market_buy_headwind=(
            (
                (macro_risk_off_count>=5)
                or ((macro_risk_off_count>=4) and (macro_pressure_v[i]>=4.4))
                or ((macro_risk_off_count>=3) and breadth_risk_off_v[i] and market_turn_bear_v[i] and (continuation_sell_score_v[i]>=3))
            )
            and not washout_bottom_v[i]
            and (not leader_mode)
            and ((money_eff[i]<0) or (long_rr_v[i]<0.95))
        )
        if hard_blowoff_v[i]:
            if j[i] in buy_labels or j[i] in ('NEUTRAL','MIXED'):
                new_label='STRONG_SELL' if (sl>=max(JT.WATCH_MIN_AGREE-sr,1) and e<=st) else 'SELL'
                if new_label!=j[i]:downgrade_count[i]+=1
                j[i]=new_label
        elif j[i] in buy_labels:
            if bearish_gap_failure_v[i] and (
                (j[i]=='STRONG_BUY')
                or ((j[i]=='BUY') and (not leader_mode) and (macro_risk_off_count>=3) and not buy_supportive_stack)
            ):
                prev_label=j[i]
                j[i]=_downgrade_buy(j[i],severe=bool((parabolic_rise_v[i] and volume_surge_v[i]) and not leader_mode))
                downgrade_count[i]+=int(j[i]!=prev_label)
            if j[i]=='STRONG_BUY' and thin_trade_v[i] and (not buy_supportive_stack_light) and (long_rr_v[i]<1.0):
                prev_label=j[i]
                j[i]=_downgrade_buy(j[i],severe=False)
                downgrade_count[i]+=int(j[i]!=prev_label)
            if j[i]=='STRONG_BUY' and ut_overheat_buy_v[i] and (continuation_buy_score_v[i]<JT.STRONG_BUY_CONTINUATION_MIN) and not bullish_gap_reversal_v[i]:
                prev_label=j[i]
                j[i]=_downgrade_buy(j[i],severe=False)
                downgrade_count[i]+=int(j[i]!=prev_label)
            if countertrend_buy_risk and not buy_supportive_stack:
                if j[i]=='STRONG_BUY':
                    prev_label=j[i]
                    j[i]=_downgrade_buy(j[i],severe=False)
                    downgrade_count[i]+=int(j[i]!=prev_label)
                if j[i] in buy_labels and (macro_risk_off_count>=4) and (severe_buy or long_rr_v[i]<0.85) and not buy_supportive_stack_light:
                    if not leader_mode:
                        prev_label=j[i]
                        j[i]=_downgrade_buy(j[i],severe=True)
                        downgrade_count[i]+=int(j[i]!=prev_label)
            if j[i] in buy_labels and market_buy_headwind and not buy_supportive_stack:
                if j[i]=='STRONG_BUY':
                    prev_label=j[i]
                    j[i]=_downgrade_buy(j[i],severe=(spy_trend_score_v[i]<=JT.MARKET_SCORE_TREND_OFF-1 and long_rr_v[i]<JT.VP_RR_FLOOR))
                    downgrade_count[i]+=int(j[i]!=prev_label)
            if pv_bear_v[i] and (j[i]=='STRONG_BUY' or (severe_buy and j[i]=='BUY' and not leader_mode and not buy_supportive_stack_light and macro_risk_off_count>=3)):
                prev_label=j[i]
                j[i]=_downgrade_buy(j[i],severe=(j[i]=='STRONG_BUY' and severe_buy and not leader_mode))
                downgrade_count[i]+=int(j[i]!=prev_label)
            if long_rr_v[i]<JT.VP_RR_FLOOR:
                if (j[i]=='STRONG_BUY') or ((long_rr_v[i]<0.70) and not buy_supportive_stack_light and not leader_mode and macro_risk_off_count>=3):
                    prev_label=j[i]
                    j[i]=_downgrade_buy(j[i],severe=(long_rr_v[i]<0.75 and money_eff[i]<0 and not leader_mode))
                    downgrade_count[i]+=int(j[i]!=prev_label)
        elif j[i] in sell_labels:
            if bullish_gap_reversal_v[i]:
                prev_label=j[i]
                j[i]=_downgrade_sell(j[i],severe=bool((continuation_buy_score_v[i]>=2 and (diag_support_v[i] or macro_risk_on_count>=2)) or leader_mode))
                downgrade_count[i]+=int(j[i]!=prev_label)
            if j[i]=='STRONG_SELL' and thin_trade_v[i] and not sell_supportive_stack:
                prev_label=j[i]
                j[i]=_downgrade_sell(j[i],severe=False)
                downgrade_count[i]+=int(j[i]!=prev_label)
            if j[i] in sell_labels and continuation_buy_score_v[i]>=2 and (macro_risk_on_count>=1 or breadth_risk_on_v[i] or diag_support_v[i]) and not bearish_gap_failure_v[i]:
                prev_label=j[i]
                j[i]=_downgrade_sell(j[i],severe=bool(leader_mode or continuation_buy_score_v[i]>=3))
                downgrade_count[i]+=int(j[i]!=prev_label)
            if countertrend_sell_risk and not sell_supportive_stack:
                prev_label=j[i]
                j[i]=_downgrade_sell(j[i],severe=bool(leader_mode or macro_risk_on_count>=3))
                downgrade_count[i]+=int(j[i]!=prev_label)
                if j[i] in sell_labels and (severe_sell or short_rr_v[i]<JT.VP_RR_FLOOR) and not sell_supportive_stack:
                    prev_label=j[i]
                    j[i]=_downgrade_sell(j[i],severe=bool(leader_mode or continuation_buy_score_v[i]>=2))
                    downgrade_count[i]+=int(j[i]!=prev_label)
            if j[i] in sell_labels and market_sell_headwind and not sell_supportive_stack:
                prev_label=j[i]
                j[i]=_downgrade_sell(j[i],severe=(leader_mode or (spy_trend_score_v[i]>=JT.MARKET_SCORE_TREND_ON+1 and short_rr_v[i]<JT.VP_RR_FLOOR)))
                downgrade_count[i]+=int(j[i]!=prev_label)
            if pv_bull_v[i]:
                prev_label=j[i]
                j[i]=_downgrade_sell(j[i],severe=(leader_mode or (j[i]=='STRONG_SELL' and severe_sell)))
                downgrade_count[i]+=int(j[i]!=prev_label)
            if short_rr_v[i]<JT.VP_RR_FLOOR:
                prev_label=j[i]
                j[i]=_downgrade_sell(j[i],severe=(leader_mode or (short_rr_v[i]<0.75 and money_eff[i]>0)))
                downgrade_count[i]+=int(j[i]!=prev_label)
        if i>0:
            prev_final=j[i-1];prev_buy=prev_final in buy_labels;prev_sell=prev_final in sell_labels;cur_buy=j[i] in buy_labels;cur_sell=j[i] in sell_labels
            if prev_buy and cur_sell:
                strong_sell_flip=(
                    (e<=sst)
                    or (sl>=JT.STRONG_MIN_AGREE)
                    or (ctx_v[i] in (CTX_STRONG_DN,CTX_DISTRIBUTION,CTX_EXTREME_OB,CTX_TOPPING))
                    or (macro_risk_off_count>=JT.FLIP_GUARD_MACRO_CONFIRM)
                    or (market_turn_bear_v[i] and sell_supportive_stack)
                    or ((trend_inflect_sell_score_v[i]>=JT.TREND_INFLECTION_STRONG+1) and sell_supportive_stack)
                    or hard_blowoff_v[i]
                    or (sy<=-JT.FLIP_GUARD_SYNERGY)
                    or (pred[i]<=-JT.FLIP_GUARD_PREDICTION)
                )
                if leader_mode and not hard_blowoff_v[i] and not bearish_gap_failure_v[i] and continuation_sell_score_v[i]<3:
                    strong_sell_flip=False
                if not strong_sell_flip:
                    prev_label=j[i]
                    j[i]='MIXED'
                    flip_guard_triggered[i]=j[i]!=prev_label
                    downgrade_count[i]+=int(j[i]!=prev_label)
                    notes.append("direct buy-to-sell flip lacked follow-through")
            elif prev_sell and cur_buy:
                strong_buy_flip=(
                    (e>=sbt)
                    or (ba>=JT.STRONG_MIN_AGREE)
                    or (ctx_v[i] in (CTX_STRONG_UP,CTX_ACCUMULATION,CTX_EXTREME_OS,CTX_BOTTOMING))
                    or (macro_risk_on_count>=JT.FLIP_GUARD_MACRO_CONFIRM)
                    or market_turn_bull_v[i]
                    or (trend_inflect_buy_score_v[i]>=JT.TREND_INFLECTION_STRONG)
                    or washout_bottom_v[i]
                    or (sy>=JT.FLIP_GUARD_SYNERGY)
                    or (pred[i]>=JT.FLIP_GUARD_PREDICTION)
                )
                if not strong_buy_flip:
                    prev_label=j[i]
                    j[i]='MIXED'
                    flip_guard_triggered[i]=j[i]!=prev_label
                    downgrade_count[i]+=int(j[i]!=prev_label)
                    notes.append("direct sell-to-buy flip lacked follow-through")
        contrast_notes.append('; '.join(notes[:3]))
        signal_note_txt='; '.join(signal_notes[:2])
        ae=abs(e);dm=max(ba,sl);ap=dm/NUM_COMMITTEES*35;sp=min(ae/60*30,30);avp=np.mean(ec[i])/100*20;syp=min(abs(sy)/20*10,10);pp=min(abs(pred[i])/15*5,5)
        raw=ap+sp+avp+syp+pp
        layer_conf=0.
        if j[i] in buy_labels:
            layer_conf=min((ba_layers[i]*1.6)+(buy_total_arr[i]*0.22),14)
        elif j[i] in sell_labels:
            layer_conf=min((sa_layers[i]*1.6)+(sell_total_arr[i]*0.22),14)
        raw+=layer_conf
        if min(ba_layers[i],sa_layers[i])>=4:
            raw-=5
        if notes and not hard_blowoff_v[i]:
            raw-=min(6,2*len(notes))
        if hard_blowoff_v[i]:
            raw=min(99,raw+4)
        if j[i] in ('NEUTRAL','MIXED'):raw=max(15,min(55,raw))
        conf[i]=np.clip(raw,5,99)
        
        # ⚡ 스캐너 및 속도 최적화: 텍스트 이유는 최근 7일치만 생성
        if i < n - 7:
            rs.append("");rd.append("");al.append("")
            continue
            
        cms={cm:es[i,ci] for ci,cm in enumerate(COMMITTEE_NAMES)}
        vstr=df['Veto_Flags'].iloc[i] if i<len(df) else ''
        obr=bool(obv_v[i]>obv_mav[i]) if not np.isnan(obv_mav[i]) else True
        ma50a=bool(C[i]>ma50_v[i]) if not np.isnan(ma50_v[i]) else False
        ma200a=bool(C[i]>ma200_v[i]) if not np.isnan(ma200_v[i]) else False
        mhu=bool(mhv[i]>mhpv[i]) if i>0 else False
        r,d,a=_gen_reason(j[i],e,int(ctx_v[i]),vstr,sy,pred[i],ba,sl,wt1_v[i],rsi_v[i],mfi_v[i],cmf[i],obr,adx_v[i],vol_ratio.values[i],ma50a,ma200a,mhu,stoch_v[i],bool(hma_r_v[i]) if i<len(hma_r_v) else False,int(ut_v[i]),bool(sq_v[i]),cms)
        if j[i]=='WATCH_BUY' and continuation_buy_score_v[i]>=2:
            a="CONTINUATION WATCH / pullback-entry candidate"
        elif j[i]=='WATCH_SELL':
            a="RISK WARNING / trim or tighten stops"
            if leader_mode and not hard_blowoff_v[i]:
                r="Leader stock looked extended, but breakdown confirmation was incomplete"
        elif j[i]=='SELL' and leader_mode and not hard_blowoff_v[i]:
            a="REDUCE / wait for deeper breakdown confirmation"
        note_txt=contrast_notes[-1]
        if hard_blowoff_v[i]:
            r="Blow-off top detected - take profit / sell bias"
            a=f"TAKE_PROFIT / SELL | {a}" if a else "TAKE_PROFIT / SELL"
        elif j[i]=='NEUTRAL' and pv_bear_v[i] and e>0:
            r="Money veto: breakout quality deteriorated"
        elif j[i]=='NEUTRAL' and pv_bull_v[i] and e<0:
            r="Money veto: downside follow-through deteriorated"
        if note_txt:
            d=f"{d} | {note_txt}" if d else note_txt
            if j[i] in buy_labels and not hard_blowoff_v[i]:
                a=f"{a} | caution" if a else "BUY with caution"
            elif j[i] in sell_labels and not hard_blowoff_v[i] and (pv_bull_v[i] or short_rr_v[i]<JT.VP_RR_FLOOR):
                a=f"{a} | caution" if a else "SELL with caution"
        if signal_note_txt:
            d=f"{d} | {signal_note_txt}" if d else signal_note_txt
        rs.append(r);rd.append(d);al.append(a)
    df['PreVeto_Judgment']=pre_veto_j;df['Trade_Judgment']=j;df['Judgment_Confidence']=conf;df['Buy_Agree']=bag;df['Sell_Agree']=sag
    df['Downgrade_Count']=downgrade_count;df['Macro_Risk_Off_Count']=macro_risk_off_count_arr;df['Macro_Risk_On_Count']=macro_risk_on_count_arr
    df['Flip_Guard_Triggered']=flip_guard_triggered
    df['Judgment_Reason']=rs;df['Judgment_Detail']=rd;df['Action_Label']=al;df['Contrast_Notes']=contrast_notes
    
    # 🎯 시스템 전면 전환(Macro Flip) 시그널 추가
    is_buy = pd.Series(j).isin(['STRONG_BUY', 'BUY', 'WATCH_BUY'])
    is_sell = pd.Series(j).isin(['STRONG_SELL', 'SELL', 'WATCH_SELL'])
    df['System_Turn_Bull'] = (is_buy & ~is_buy.shift(1).fillna(False)).values
    df['System_Turn_Bear'] = (is_sell & ~is_sell.shift(1).fillna(False)).values
    
    return df


_OBJECTIVE_BUY_LABELS={'STRONG_BUY','BUY','WATCH_BUY'}
_OBJECTIVE_SELL_LABELS={'STRONG_SELL','SELL','WATCH_SELL'}
_OBJECTIVE_SIGNAL_EXCLUDE={'System_Turn_Bull','System_Turn_Bear'}


def _objective_event_name(name):
    return str(name).replace('_',' ')


def _objective_recent_registry_score(i,specs,bool_arrays,lookback,decay):
    score=0.;strong_hits=0;hits=[]
    for name,base,is_strong in specs:
        arr=bool_arrays.get(name)
        if arr is None:
            continue
        best=0.;best_age=None
        max_age=min(i,lookback-1)
        for age in range(max_age+1):
            if arr[i-age]:
                cur=base*(decay**age)
                if cur>best:
                    best=cur;best_age=age
        if best>0:
            score+=best;hits.append((best,name,best_age))
            if is_strong:
                strong_hits+=1
    hits.sort(key=lambda x:x[0],reverse=True)
    return score,strong_hits,hits


def _objective_action_label(label):
    return {
        'STRONG_BUY':'BUY / strongest objective alignment',
        'BUY':'BUY / objective trend follow-through',
        'WATCH_BUY':'WATCH BUY / wait for confirmation',
        'NEUTRAL':'NEUTRAL / wait for clearer alignment',
        'MIXED':'MIXED / conflicting objective evidence',
        'WATCH_SELL':'WATCH SELL / risk-off watch',
        'SELL':'SELL / objective downside pressure',
        'STRONG_SELL':'SELL / strongest downside alignment',
    }.get(label,'NEUTRAL / wait for clearer alignment')


def _compute_objective_judgment(df,vol_ratio):
    if df is None or df.empty:
        return df

    idx=df.index;n=len(df)
    N=lambda c,d=0:df.get(c,pd.Series(d,index=idx)).fillna(d)
    close_v=df['Close'].values;open_v=df['Open'].values;high_v=df['High'].values;low_v=df['Low'].values
    ma20_v=N('MA20',np.nan).values;ma50_v=N('MA50',np.nan).values;ma200_v=N('MA200',np.nan).values
    ema12_v=N('EMA12',np.nan).values;ema26_v=N('EMA26',np.nan).values
    hma_v=N('HMA',np.nan).values;hma_rising_v=df.get('HMA_Rising',pd.Series(False,index=idx)).fillna(False).values.astype(bool)
    wt1_v=N('WT1',0.).values;wt2_v=N('WT2',0.).values;rsi_v=N('RSI',50.).values;mfi_v=N('MFI',50.).values
    macd_hist_v=N('MACD_Hist',0.).values;adx_v=N('ADX',0.).values;pdi_v=N('Plus_DI',0.).values;mdi_v=N('Minus_DI',0.).values
    stochk_v=N('StochK',50.).values;stochd_v=N('StochD',50.).values;atr_v=N('ATR',0.).values;percent_b_v=N('Percent_B',0.5).values
    williams_r_v=N('Williams_R',-50.).values;cci_v=N('CCI',0.).values;roc_v=N('ROC',0.).values;rmi_v=N('RMI',50.).values
    trix_v=N('TRIX',0.).values;price_osc_v=N('Price_Oscillator',0.).values;vol_osc_v=N('Volume_Oscillator',0.).values
    mass_index_v=N('Mass_Index',0.).values;momentum_10_v=N('Momentum_10',0.).values
    disparity20_v=N('Disparity_20',0.).values;disparity50_v=N('Disparity_50',0.).values;disparity200_v=N('Disparity_200',0.).values
    intraday_intensity_v=N('Intraday_Intensity',0.).values;intraday_intensity_idx_v=N('Intraday_Intensity_Index',0.).values
    ad_line_v=N('AD_Line',0.).values;chaikin_osc_v=N('Chaikin_Oscillator',0.).values
    envelope_pct_v=N('Envelope_Percent',0.5).values;vwap_v=N('VWAP',np.nan).values;fixed_vwap_v=N('Fixed_VWAP',np.nan).values
    psar_dir_v=N('PSAR_Direction',0.).values;price_channel_up_v=N('Price_Channel_Up',np.nan).values;price_channel_low_v=N('Price_Channel_Low',np.nan).values;price_channel_mid_v=N('Price_Channel_Mid',np.nan).values
    supertrend_v=N('SuperTrend',np.nan).values;tenkan_v=N('Ichimoku_Tenkan',np.nan).values;kijun_v=N('Ichimoku_Kijun',np.nan).values
    senkou_a_v=N('Ichimoku_SenkouA',np.nan).values;senkou_b_v=N('Ichimoku_SenkouB',np.nan).values
    fractal_high_v=np.asarray(N('Fractal_High',False).values,dtype=bool);fractal_low_v=np.asarray(N('Fractal_Low',False).values,dtype=bool)
    vp_poc_v=N('VP_POC',np.nan).values;vp_vah_v=N('VP_VAH',np.nan).values;vp_val_v=N('VP_VAL',np.nan).values
    long_rr_v=N('VP_Long_RR',1.).values;short_rr_v=N('VP_Short_RR',1.).values
    vr_v=vol_ratio.values if isinstance(vol_ratio,pd.Series) else np.asarray(vol_ratio,dtype=float)
    if len(vr_v)!=n:
        vr_v=N('Volume_Ratio_20',1.).values
    thin_trade_v=np.asarray(N('Thin_Trade_Risk',False).values,dtype=bool)
    dollar_volume_20_v=N('Dollar_Volume_20',0.).values;ma20_atr_gap_v=N('MA20_ATR_Gap',0.).values
    excess_return_20_v=(N('Stock_Return',0.).values-N('SPY_Return',0.).values)*100.0
    continuation_buy_v=N('Continuation_Buy_Score',0.).values;continuation_sell_v=N('Continuation_Sell_Score',0.).values
    trend_inflect_buy_v=N('Trend_Inflection_Buy_Score',0.).values;trend_inflect_sell_v=N('Trend_Inflection_Sell_Score',0.).values
    market_turn_bull_v=N('Market_Turn_Bull_Score',0.).values;market_turn_bear_v=N('Market_Turn_Bear_Score',0.).values
    buy_total_v=N('Buy_Total',0.).values;sell_total_v=N('Sell_Total',0.).values
    base_labels=np.asarray(df.get('Trade_Judgment',pd.Series('NEUTRAL',index=idx)).astype(str).values,dtype=object)
    base_pre_labels=np.asarray(df.get('PreVeto_Judgment',pd.Series('NEUTRAL',index=idx)).astype(str).values,dtype=object)
    base_conf=N('Judgment_Confidence',0.).values.astype(float)
    base_buy_agree=N('Buy_Agree',0).values.astype(int);base_sell_agree=N('Sell_Agree',0).values.astype(int)
    base_downgrade=N('Downgrade_Count',0).values.astype(int)
    base_macro_off=N('Macro_Risk_Off_Count',0).values.astype(int);base_macro_on=N('Macro_Risk_On_Count',0).values.astype(int)
    base_flip_guard=np.asarray(N('Flip_Guard_Triggered',False).values,dtype=bool)
    base_reasons=np.asarray(df.get('Judgment_Reason',pd.Series('',index=idx)).astype(str).values,dtype=object)
    base_details=np.asarray(df.get('Judgment_Detail',pd.Series('',index=idx)).astype(str).values,dtype=object)
    base_actions=np.asarray(df.get('Action_Label',pd.Series('',index=idx)).astype(str).values,dtype=object)
    base_contrast=np.asarray(df.get('Contrast_Notes',pd.Series('',index=idx)).astype(str).values,dtype=object)

    signal_specs={'buy':[],'sell':[]};combo_specs={'buy':[],'sell':[]};bool_arrays={}
    for name,cfg in SIGNAL_REGISTRY.items():
        if name in _OBJECTIVE_SIGNAL_EXCLUDE or name not in df.columns:
            continue
        direction=cfg.get('dir')
        if direction not in signal_specs:
            continue
        bool_arrays[name]=df[name].fillna(False).values.astype(bool)
        signal_specs[direction].append((name,float(cfg.get('w',1.0))*1.05,name in (STRONG_BUY_SIGS if direction=='buy' else STRONG_SELL_SIGS)))
    combo_base={1:3.0,2:2.0,3:1.2}
    for name,cfg in COMBINED_SCAN_REGISTRY.items():
        if name not in df.columns:
            continue
        direction=cfg.get('dir')
        if direction not in combo_specs:
            continue
        bool_arrays[name]=df[name].fillna(False).values.astype(bool)
        tier=int(cfg.get('tier',3) or 3)
        combo_specs[direction].append((name,float(combo_base.get(tier,1.0)),tier==1))

    labels=np.full(n,'NEUTRAL',dtype=object);pre_labels=np.full(n,'NEUTRAL',dtype=object);conf=np.zeros(n,dtype=float)
    buy_agree=np.zeros(n,dtype=int);sell_agree=np.zeros(n,dtype=int)
    buy_score=np.zeros(n,dtype=float);sell_score=np.zeros(n,dtype=float);conflict_score=np.zeros(n,dtype=float)
    trend_buy_score=np.zeros(n,dtype=float);trend_sell_score=np.zeros(n,dtype=float)
    momentum_buy_score=np.zeros(n,dtype=float);momentum_sell_score=np.zeros(n,dtype=float)
    money_buy_score=np.zeros(n,dtype=float);money_sell_score=np.zeros(n,dtype=float)
    reversal_buy_score=np.zeros(n,dtype=float);reversal_sell_score=np.zeros(n,dtype=float)
    location_buy_score=np.zeros(n,dtype=float);location_sell_score=np.zeros(n,dtype=float)
    signal_buy_score=np.zeros(n,dtype=float);signal_sell_score=np.zeros(n,dtype=float)
    combo_buy_score=np.zeros(n,dtype=float);combo_sell_score=np.zeros(n,dtype=float)
    objective_alignment=np.full(n,'MIXED',dtype=object);objective_adjustment=np.full(n,'NONE',dtype=object)
    reasons=[];details=[];actions=[];contrast_notes=[]

    for i in range(n):
        price=float(close_v[i]);prev_close=float(close_v[i-1]) if i>0 else price
        prev_rsi=float(rsi_v[i-1]) if i>0 else float(rsi_v[i]);prev_mfi=float(mfi_v[i-1]) if i>0 else float(mfi_v[i])
        prev_wt1=float(wt1_v[i-1]) if i>0 else float(wt1_v[i]);prev_macd=float(macd_hist_v[i-1]) if i>0 else float(macd_hist_v[i])
        prev_poc=float(vp_poc_v[i-1]) if i>0 else float(vp_poc_v[i])
        prev_ad_line=float(ad_line_v[i-1]) if i>0 else float(ad_line_v[i])
        prev_chaikin=float(chaikin_osc_v[i-1]) if i>0 else float(chaikin_osc_v[i])
        prev_intraday_idx=float(intraday_intensity_idx_v[i-1]) if i>0 else float(intraday_intensity_idx_v[i])
        green=price>=float(open_v[i]);red=price<float(open_v[i]);close_up=price>prev_close;close_dn=price<prev_close
        bar_range=max(float(high_v[i]-low_v[i]),0.);atr_here=max(float(atr_v[i]),0.);atr_norm=atr_here/max(abs(price),1e-10)
        vp_tol=max(atr_norm*1.5,0.012)

        trend_buy=0.;trend_sell=0.;trend_note_buy='';trend_note_sell=''
        if np.isfinite(hma_v[i]):
            if price>float(hma_v[i]):
                trend_buy+=1.0;trend_note_buy=trend_note_buy or 'close stayed above HMA'
            elif price<float(hma_v[i]):
                trend_sell+=1.0;trend_note_sell=trend_note_sell or 'close stayed below HMA'
        if i>0 and np.isfinite(hma_v[i]) and np.isfinite(hma_v[i-1]):
            if bool(hma_rising_v[i]):
                trend_buy+=0.9;trend_note_buy=trend_note_buy or 'HMA kept rising'
            elif float(hma_v[i])<float(hma_v[i-1]):
                trend_sell+=0.7;trend_note_sell=trend_note_sell or 'HMA kept falling'
        if np.isfinite(ma20_v[i]):
            if price>float(ma20_v[i]):
                trend_buy+=0.7
            elif price<float(ma20_v[i]):
                trend_sell+=0.7
        if np.isfinite(ma50_v[i]):
            if price>float(ma50_v[i]):
                trend_buy+=1.1
            elif price<float(ma50_v[i]):
                trend_sell+=1.1
        if np.isfinite(ma200_v[i]):
            if price>float(ma200_v[i]):
                trend_buy+=1.2
            elif price<float(ma200_v[i]):
                trend_sell+=1.2
        if np.isfinite(ma50_v[i]) and np.isfinite(ma200_v[i]):
            if float(ma50_v[i])>float(ma200_v[i]):
                trend_buy+=0.8
            elif float(ma50_v[i])<float(ma200_v[i]):
                trend_sell+=0.8
        if np.isfinite(ema12_v[i]) and np.isfinite(ema26_v[i]):
            if price>float(ema12_v[i]) and float(ema12_v[i])>float(ema26_v[i]):
                trend_buy+=1.0;trend_note_buy=trend_note_buy or 'EMA12 stayed above EMA26'
            elif price<float(ema12_v[i]) and float(ema12_v[i])<float(ema26_v[i]):
                trend_sell+=1.0;trend_note_sell=trend_note_sell or 'EMA12 stayed below EMA26'
            elif float(ema12_v[i])>float(ema26_v[i]):
                trend_buy+=0.5
            elif float(ema12_v[i])<float(ema26_v[i]):
                trend_sell+=0.5
        if np.isfinite(adx_v[i]) and float(adx_v[i])>=18 and np.isfinite(pdi_v[i]) and np.isfinite(mdi_v[i]):
            if float(pdi_v[i])>float(mdi_v[i]):
                trend_buy+=1.1
            elif float(mdi_v[i])>float(pdi_v[i]):
                trend_sell+=1.1
        if float(psar_dir_v[i])>0:
            trend_buy+=0.7
        elif float(psar_dir_v[i])<0:
            trend_sell+=0.7
        if np.isfinite(vwap_v[i]):
            if price>float(vwap_v[i]):
                trend_buy+=0.5
            elif price<float(vwap_v[i]):
                trend_sell+=0.5
        if np.isfinite(fixed_vwap_v[i]):
            if price>float(fixed_vwap_v[i]):
                trend_buy+=0.5
            elif price<float(fixed_vwap_v[i]):
                trend_sell+=0.5
        if np.isfinite(price_channel_mid_v[i]):
            if price>float(price_channel_mid_v[i]):
                trend_buy+=0.4
            elif price<float(price_channel_mid_v[i]):
                trend_sell+=0.4
        if np.isfinite(supertrend_v[i]):
            if price>float(supertrend_v[i]):
                trend_buy+=0.7;trend_note_buy=trend_note_buy or 'price stayed above SuperTrend'
            elif price<float(supertrend_v[i]):
                trend_sell+=0.7;trend_note_sell=trend_note_sell or 'price stayed below SuperTrend'
        if np.isfinite(tenkan_v[i]) and np.isfinite(kijun_v[i]):
            if price>float(tenkan_v[i]) and price>float(kijun_v[i]):
                trend_buy+=0.7
            elif price<float(tenkan_v[i]) and price<float(kijun_v[i]):
                trend_sell+=0.7
        if np.isfinite(senkou_a_v[i]) and np.isfinite(senkou_b_v[i]):
            cloud_top=max(float(senkou_a_v[i]),float(senkou_b_v[i]));cloud_bot=min(float(senkou_a_v[i]),float(senkou_b_v[i]))
            if price>cloud_top:
                trend_buy+=0.8
            elif price<cloud_bot:
                trend_sell+=0.8
        if np.isfinite(disparity50_v[i]):
            if float(disparity50_v[i])>0:
                trend_buy+=0.35
            elif float(disparity50_v[i])<0:
                trend_sell+=0.35
        if np.isfinite(disparity200_v[i]):
            if float(disparity200_v[i])>0:
                trend_buy+=0.45
            elif float(disparity200_v[i])<0:
                trend_sell+=0.45
        trend_buy=min(trend_buy,6.0);trend_sell=min(trend_sell,6.0)

        momentum_buy=0.;momentum_sell=0.;momentum_note_buy='';momentum_note_sell=''
        if np.isfinite(macd_hist_v[i]):
            if float(macd_hist_v[i])>0:
                momentum_buy+=1.1;momentum_note_buy=momentum_note_buy or 'MACD histogram stayed positive'
            elif float(macd_hist_v[i])<0:
                momentum_sell+=1.1;momentum_note_sell=momentum_note_sell or 'MACD histogram stayed negative'
            if i>0:
                if float(macd_hist_v[i])>prev_macd:
                    momentum_buy+=0.8
                elif float(macd_hist_v[i])<prev_macd:
                    momentum_sell+=0.8
        if np.isfinite(wt1_v[i]) and np.isfinite(wt2_v[i]):
            if float(wt1_v[i])>float(wt2_v[i]):
                momentum_buy+=1.0;momentum_note_buy=momentum_note_buy or 'WT1 crossed above WT2'
            elif float(wt1_v[i])<float(wt2_v[i]):
                momentum_sell+=1.0;momentum_note_sell=momentum_note_sell or 'WT1 stayed below WT2'
            if float(wt1_v[i])>prev_wt1:
                momentum_buy+=0.8
            elif float(wt1_v[i])<prev_wt1:
                momentum_sell+=0.8
        if np.isfinite(rsi_v[i]):
            if float(rsi_v[i])>=52:
                momentum_buy+=0.8
            elif float(rsi_v[i])<=48:
                momentum_sell+=0.8
        if np.isfinite(mfi_v[i]):
            if float(mfi_v[i])>=52:
                momentum_buy+=0.7
            elif float(mfi_v[i])<=48:
                momentum_sell+=0.7
        if np.isfinite(stochk_v[i]) and np.isfinite(stochd_v[i]):
            if float(stochk_v[i])>float(stochd_v[i]):
                momentum_buy+=0.6
            elif float(stochk_v[i])<float(stochd_v[i]):
                momentum_sell+=0.6
        if np.isfinite(roc_v[i]):
            if float(roc_v[i])>0:
                momentum_buy+=0.7
            elif float(roc_v[i])<0:
                momentum_sell+=0.7
        if np.isfinite(rmi_v[i]):
            if float(rmi_v[i])>=52:
                momentum_buy+=0.7
            elif float(rmi_v[i])<=48:
                momentum_sell+=0.7
        if np.isfinite(trix_v[i]):
            if float(trix_v[i])>0:
                momentum_buy+=0.6
            elif float(trix_v[i])<0:
                momentum_sell+=0.6
        if np.isfinite(price_osc_v[i]):
            if float(price_osc_v[i])>0:
                momentum_buy+=0.7
            elif float(price_osc_v[i])<0:
                momentum_sell+=0.7
        if np.isfinite(momentum_10_v[i]):
            if float(momentum_10_v[i])>0:
                momentum_buy+=0.6
            elif float(momentum_10_v[i])<0:
                momentum_sell+=0.6
        if np.isfinite(disparity20_v[i]):
            if float(disparity20_v[i])>1.0:
                momentum_buy+=0.4
            elif float(disparity20_v[i])<-1.0:
                momentum_sell+=0.4
        momentum_buy=min(momentum_buy,5.0);momentum_sell=min(momentum_sell,5.0)

        money_buy=0.;money_sell=0.;money_note_buy='';money_note_sell=''
        if np.isfinite(mfi_v[i]):
            if float(mfi_v[i])>=55:
                money_buy+=0.6
            elif float(mfi_v[i])<=45:
                money_sell+=0.6
        if np.isfinite(vol_osc_v[i]):
            if float(vol_osc_v[i])>0:
                money_buy+=0.8 if close_up else 0.5
                money_note_buy=money_note_buy or 'volume oscillator expanded on the upside'
            elif float(vol_osc_v[i])<0:
                money_sell+=0.8 if close_dn else 0.5
                money_note_sell=money_note_sell or 'volume oscillator expanded on the downside'
        if np.isfinite(intraday_intensity_v[i]):
            if float(intraday_intensity_v[i])>0 and green:
                money_buy+=0.4
            elif float(intraday_intensity_v[i])<0 and red:
                money_sell+=0.4
        if np.isfinite(intraday_intensity_idx_v[i]):
            if float(intraday_intensity_idx_v[i])>=10:
                money_buy+=0.9;money_note_buy=money_note_buy or 'intraday intensity stayed positive'
            elif float(intraday_intensity_idx_v[i])<=-10:
                money_sell+=0.9;money_note_sell=money_note_sell or 'intraday intensity stayed negative'
            elif i>0:
                if float(intraday_intensity_idx_v[i])>prev_intraday_idx:
                    money_buy+=0.3
                elif float(intraday_intensity_idx_v[i])<prev_intraday_idx:
                    money_sell+=0.3
        if np.isfinite(chaikin_osc_v[i]):
            if float(chaikin_osc_v[i])>0:
                money_buy+=0.9;money_note_buy=money_note_buy or 'Chaikin flow turned supportive'
            elif float(chaikin_osc_v[i])<0:
                money_sell+=0.9;money_note_sell=money_note_sell or 'Chaikin flow turned defensive'
            if i>0:
                if float(chaikin_osc_v[i])>prev_chaikin:
                    money_buy+=0.3
                elif float(chaikin_osc_v[i])<prev_chaikin:
                    money_sell+=0.3
        if i>0 and np.isfinite(ad_line_v[i]):
            if float(ad_line_v[i])>prev_ad_line:
                money_buy+=0.5
            elif float(ad_line_v[i])<prev_ad_line:
                money_sell+=0.5
        if np.isfinite(dollar_volume_20_v[i]):
            if float(dollar_volume_20_v[i])>=JT.MIN_DOLLAR_VOLUME_20 and not thin_trade_v[i]:
                money_buy+=0.4 if close_up else 0.2
            elif thin_trade_v[i]:
                money_sell+=0.4 if close_dn else 0.2
        money_buy=min(money_buy,4.8);money_sell=min(money_sell,4.8)

        oversold_count=int(float(rsi_v[i])<35)+int(float(mfi_v[i])<35)+int(float(wt1_v[i])<-45)+int(float(stochk_v[i])<25)+int(float(percent_b_v[i])<0.20)+int(float(williams_r_v[i])<=-80)+int(float(cci_v[i])<=-100)+int(float(envelope_pct_v[i])<=0.20)
        overbought_count=int(float(rsi_v[i])>65)+int(float(mfi_v[i])>65)+int(float(wt1_v[i])>45)+int(float(stochk_v[i])>75)+int(float(percent_b_v[i])>0.80)+int(float(williams_r_v[i])>=-20)+int(float(cci_v[i])>=100)+int(float(envelope_pct_v[i])>=0.80)
        rebound_up=(green and close_up) or (float(rsi_v[i])>prev_rsi) or (float(mfi_v[i])>prev_mfi) or (float(wt1_v[i])>prev_wt1) or (float(stochk_v[i])>float(stochd_v[i]))
        rebound_dn=(red and close_dn) or (float(rsi_v[i])<prev_rsi) or (float(mfi_v[i])<prev_mfi) or (float(wt1_v[i])<prev_wt1) or (float(stochk_v[i])<float(stochd_v[i]))
        reversal_buy=min(oversold_count*0.95,4.5) if oversold_count>=2 and rebound_up else 0.
        reversal_sell=min(overbought_count*0.95,4.5) if overbought_count>=2 and rebound_dn else 0.
        reversal_note_buy='oversold cluster started rebounding' if reversal_buy>0 else ''
        reversal_note_sell='overbought cluster started fading' if reversal_sell>0 else ''
        if fractal_low_v[i] and rebound_up:
            reversal_buy+=0.8;reversal_note_buy=reversal_note_buy or 'Williams fractal low appeared with rebound'
        if fractal_high_v[i] and rebound_dn:
            reversal_sell+=0.8;reversal_note_sell=reversal_note_sell or 'Williams fractal high appeared with fade'
        if np.isfinite(disparity20_v[i]) and float(disparity20_v[i])<=-4 and rebound_up:
            reversal_buy+=0.6
        if np.isfinite(disparity20_v[i]) and float(disparity20_v[i])>=4 and rebound_dn:
            reversal_sell+=0.6
        if np.isfinite(mass_index_v[i]) and float(mass_index_v[i])>=26.5:
            if rebound_up and oversold_count>=1:
                reversal_buy+=0.7;reversal_note_buy=reversal_note_buy or 'Mass Index bulge reversed higher'
            if rebound_dn and overbought_count>=1:
                reversal_sell+=0.7;reversal_note_sell=reversal_note_sell or 'Mass Index bulge reversed lower'
        reversal_buy=min(reversal_buy,5.2);reversal_sell=min(reversal_sell,5.2)

        location_buy=0.;location_sell=0.;location_note_buy='';location_note_sell=''
        if np.isfinite(vp_poc_v[i]):
            if price>float(vp_poc_v[i]):
                location_buy+=0.9;location_note_buy=location_note_buy or 'price held above VP POC'
            elif price<float(vp_poc_v[i]):
                location_sell+=0.9;location_note_sell=location_note_sell or 'price stayed below VP POC'
            if i>0 and np.isfinite(prev_poc):
                if prev_close<=prev_poc and price>float(vp_poc_v[i]):
                    location_buy+=0.7
                elif prev_close>=prev_poc and price<float(vp_poc_v[i]):
                    location_sell+=0.7
        if np.isfinite(vp_val_v[i]) and price<=float(vp_val_v[i])*(1+vp_tol) and green:
            location_buy+=0.7
        if np.isfinite(vp_vah_v[i]) and price>=float(vp_vah_v[i])*(1-vp_tol) and red:
            location_sell+=0.7
        if np.isfinite(price_channel_low_v[i]) and price<=float(price_channel_low_v[i])*(1+vp_tol) and green:
            location_buy+=0.6
        if np.isfinite(price_channel_up_v[i]) and price>=float(price_channel_up_v[i])*(1-vp_tol) and red:
            location_sell+=0.6
        if np.isfinite(vwap_v[i]) and np.isfinite(fixed_vwap_v[i]):
            if price>float(vwap_v[i]) and price>float(fixed_vwap_v[i]):
                location_buy+=0.4
            elif price<float(vwap_v[i]) and price<float(fixed_vwap_v[i]):
                location_sell+=0.4
        if np.isfinite(ma20_atr_gap_v[i]):
            if float(ma20_atr_gap_v[i])<=-1.5 and green:
                location_buy+=0.6
            elif float(ma20_atr_gap_v[i])>=1.5 and red:
                location_sell+=0.6
        if np.isfinite(long_rr_v[i]):
            if float(long_rr_v[i])>=1.35:
                location_buy+=1.4;location_note_buy=location_note_buy or 'VP long RR stayed favorable'
            elif float(long_rr_v[i])>=1.10:
                location_buy+=0.8
        if np.isfinite(short_rr_v[i]):
            if float(short_rr_v[i])>=1.35:
                location_sell+=1.4;location_note_sell=location_note_sell or 'VP short RR stayed favorable'
            elif float(short_rr_v[i])>=1.10:
                location_sell+=0.8
        if close_up and float(vr_v[i])>=1.15:
            location_buy+=0.8
        elif close_dn and float(vr_v[i])>=1.15:
            location_sell+=0.8
        if np.isfinite(envelope_pct_v[i]) and float(envelope_pct_v[i])<=0.25 and green:
            location_buy+=0.5
        elif np.isfinite(envelope_pct_v[i]) and float(envelope_pct_v[i])>=0.75 and red:
            location_sell+=0.5
        if atr_here>0 and bar_range>=atr_here*1.2:
            if green:
                location_buy+=0.6
            elif red:
                location_sell+=0.6
        if np.isfinite(excess_return_20_v[i]):
            if float(excess_return_20_v[i])>=3:
                location_buy+=0.5
            elif float(excess_return_20_v[i])<=-3:
                location_sell+=0.5
        location_buy=min(location_buy,4.5);location_sell=min(location_sell,4.5)

        signal_buy,signal_buy_strong,signal_buy_hits=_objective_recent_registry_score(i,signal_specs['buy'],bool_arrays,4,0.72)
        signal_sell,signal_sell_strong,signal_sell_hits=_objective_recent_registry_score(i,signal_specs['sell'],bool_arrays,4,0.72)
        combo_buy,combo_buy_strong,combo_buy_hits=_objective_recent_registry_score(i,combo_specs['buy'],bool_arrays,6,0.78)
        combo_sell,combo_sell_strong,combo_sell_hits=_objective_recent_registry_score(i,combo_specs['sell'],bool_arrays,6,0.78)
        signal_buy=min(signal_buy,7.0);signal_sell=min(signal_sell,7.0);combo_buy=min(combo_buy,6.0);combo_sell=min(combo_sell,6.0)

        buy_groups={'trend':trend_buy,'momentum':momentum_buy,'money':money_buy,'reversal':reversal_buy,'location':location_buy,'signals':signal_buy,'combos':combo_buy}
        sell_groups={'trend':trend_sell,'momentum':momentum_sell,'money':money_sell,'reversal':reversal_sell,'location':location_sell,'signals':signal_sell,'combos':combo_sell}
        thresholds={'trend':2.2,'momentum':2.2,'money':1.6,'reversal':1.6,'location':1.4,'signals':1.5,'combos':1.2}
        buy_ag=sum(int(buy_groups[key]>=thresholds[key] and buy_groups[key]>sell_groups[key]*0.85) for key in thresholds)
        sell_ag=sum(int(sell_groups[key]>=thresholds[key] and sell_groups[key]>buy_groups[key]*0.85) for key in thresholds)
        conflict=sum(min(buy_groups[key],sell_groups[key]) for key in thresholds)/3.5
        buy_total=sum(buy_groups.values())+max(buy_ag-2,0)*0.8+min(signal_buy_strong,2)*0.6+min(combo_buy_strong,2)*0.8
        sell_total=sum(sell_groups.values())+max(sell_ag-2,0)*0.8+min(signal_sell_strong,2)*0.6+min(combo_sell_strong,2)*0.8
        buy_total=max(buy_total-min(conflict,2.6),0.);sell_total=max(sell_total-min(conflict,2.6),0.)
        diff=buy_total-sell_total

        if buy_ag>=2 and sell_ag>=2 and abs(diff)<=2.5:
            label='MIXED'
        elif diff>=10 and ((buy_ag>=4) or (buy_ag>=3 and combo_buy>=2.2)):
            label='STRONG_BUY'
        elif diff>=5 and (buy_ag>=3 or (buy_ag>=2 and (signal_buy+combo_buy)>=3.2)):
            label='BUY'
        elif diff>=2.2 and buy_ag>=2:
            label='WATCH_BUY'
        elif diff<=-10 and ((sell_ag>=4) or (sell_ag>=3 and combo_sell>=2.2)):
            label='STRONG_SELL'
        elif diff<=-5 and (sell_ag>=3 or (sell_ag>=2 and (signal_sell+combo_sell)>=3.2)):
            label='SELL'
        elif diff<=-2.2 and sell_ag>=2:
            label='WATCH_SELL'
        else:
            label='NEUTRAL'

        buy_reason_parts=[];sell_reason_parts=[]
        if trend_buy>=2.2 and trend_buy>trend_sell:
            buy_reason_parts.append(trend_note_buy or 'price/HMA/MA structure leaned bullish')
        if momentum_buy>=2.2 and momentum_buy>momentum_sell:
            buy_reason_parts.append(momentum_note_buy or 'momentum stack leaned bullish')
        if money_buy>=1.6 and money_buy>money_sell:
            buy_reason_parts.append(money_note_buy or 'money-flow stack leaned bullish')
        if reversal_buy>=1.6 and reversal_buy>reversal_sell:
            buy_reason_parts.append(reversal_note_buy)
        if location_buy>=1.4 and location_buy>location_sell:
            buy_reason_parts.append(location_note_buy or 'volume profile / RR favored longs')
        if signal_buy>=1.5:
            buy_reason_parts.append(f"recent buy signals fired ({', '.join(_objective_event_name(name) for _,name,_ in signal_buy_hits[:2])})")
        if combo_buy>=1.2:
            buy_reason_parts.append(f"recent buy combos fired ({', '.join(_objective_event_name(name) for _,name,_ in combo_buy_hits[:2])})")
        if trend_sell>=2.2 and trend_sell>trend_buy:
            sell_reason_parts.append(trend_note_sell or 'price/HMA/MA structure leaned bearish')
        if momentum_sell>=2.2 and momentum_sell>momentum_buy:
            sell_reason_parts.append(momentum_note_sell or 'momentum stack leaned bearish')
        if money_sell>=1.6 and money_sell>money_buy:
            sell_reason_parts.append(money_note_sell or 'money-flow stack leaned bearish')
        if reversal_sell>=1.6 and reversal_sell>reversal_buy:
            sell_reason_parts.append(reversal_note_sell)
        if location_sell>=1.4 and location_sell>location_buy:
            sell_reason_parts.append(location_note_sell or 'volume profile / RR favored shorts')
        if signal_sell>=1.5:
            sell_reason_parts.append(f"recent sell signals fired ({', '.join(_objective_event_name(name) for _,name,_ in signal_sell_hits[:2])})")
        if combo_sell>=1.2:
            sell_reason_parts.append(f"recent sell combos fired ({', '.join(_objective_event_name(name) for _,name,_ in combo_sell_hits[:2])})")

        if label in _OBJECTIVE_BUY_LABELS:
            reason=buy_reason_parts[0] if buy_reason_parts else 'objective bullish evidence stayed ahead of bearish evidence'
            contrast=sell_reason_parts[0] if sell_reason_parts else ''
        elif label in _OBJECTIVE_SELL_LABELS:
            reason=sell_reason_parts[0] if sell_reason_parts else 'objective bearish evidence stayed ahead of bullish evidence'
            contrast=buy_reason_parts[0] if buy_reason_parts else ''
        elif label=='MIXED':
            reason='buy and sell evidence fired in the same recent window'
            contrast=' | '.join((buy_reason_parts+sell_reason_parts)[:2])
        else:
            reason='objective evidence stayed below the conviction threshold'
            contrast=(buy_reason_parts or sell_reason_parts or ['signal confirmation stayed thin'])[0]

        raw_conf=32.+min(abs(diff)*4.2,34.)+max(buy_ag,sell_ag)*4.5+min(max(signal_buy,signal_sell)*1.2,9.)+min(max(combo_buy,combo_sell)*1.5,10.)-min(conflict*4.0,16.)
        if label=='NEUTRAL':
            conf_val=np.clip(18.+min(max(buy_total,sell_total)*1.2,22.),18.,44.)
        elif label=='MIXED':
            conf_val=np.clip(28.+min((buy_total+sell_total)*0.8,24.)-min(abs(diff)*2.0,10.),26.,58.)
        else:
            conf_val=np.clip(raw_conf,22.,97.)

        detail_parts=[
            f"objective buy {buy_total:.1f} vs sell {sell_total:.1f}",
            f"agreement B{buy_ag}/S{sell_ag}",
            f"trend {trend_buy:.1f}/{trend_sell:.1f}",
            f"momentum {momentum_buy:.1f}/{momentum_sell:.1f}",
            f"money {money_buy:.1f}/{money_sell:.1f}",
            f"signals {signal_buy:.1f}/{signal_sell:.1f}",
            f"combos {combo_buy:.1f}/{combo_sell:.1f}",
        ]
        if contrast:
            detail_parts.append(f"counter: {contrast}")

        labels[i]=label;pre_labels[i]=label;conf[i]=float(conf_val);buy_agree[i]=int(buy_ag);sell_agree[i]=int(sell_ag)
        buy_score[i]=float(buy_total);sell_score[i]=float(sell_total);conflict_score[i]=float(conflict)
        trend_buy_score[i]=float(trend_buy);trend_sell_score[i]=float(trend_sell)
        momentum_buy_score[i]=float(momentum_buy);momentum_sell_score[i]=float(momentum_sell)
        money_buy_score[i]=float(money_buy);money_sell_score[i]=float(money_sell)
        reversal_buy_score[i]=float(reversal_buy);reversal_sell_score[i]=float(reversal_sell)
        location_buy_score[i]=float(location_buy);location_sell_score[i]=float(location_sell)
        signal_buy_score[i]=float(signal_buy);signal_sell_score[i]=float(signal_sell)
        combo_buy_score[i]=float(combo_buy);combo_sell_score[i]=float(combo_sell)
        reasons.append(reason);details.append(' | '.join(detail_parts));actions.append(_objective_action_label(label));contrast_notes.append(contrast)

    objective_labels=labels.copy();objective_pre_labels=pre_labels.copy();objective_conf=conf.copy()
    objective_reasons=np.asarray(reasons,dtype=object);objective_details=np.asarray(details,dtype=object)
    objective_actions=np.asarray(actions,dtype=object);objective_contrasts=np.asarray(contrast_notes,dtype=object)

    final_labels=base_labels.copy();final_conf=base_conf.copy()
    final_buy_agree=base_buy_agree.copy();final_sell_agree=base_sell_agree.copy()
    final_downgrade=base_downgrade.copy();final_reasons=base_reasons.copy();final_details=base_details.copy()
    final_actions=base_actions.copy();final_contrast=base_contrast.copy()

    for i in range(n):
        base_label=str(base_labels[i] or 'NEUTRAL').upper();obj_label=str(objective_labels[i] or 'NEUTRAL').upper()
        base_side=_judgment_side(base_label);obj_side=_judgment_side(obj_label);obj_gap=abs(buy_score[i]-sell_score[i])
        layer_side=1 if buy_total_v[i]>(sell_total_v[i]+2) else (-1 if sell_total_v[i]>(buy_total_v[i]+2) else 0)
        support_count=0
        if layer_side==obj_side and obj_side!=0:support_count+=1
        if obj_side>0:
            support_count+=int(continuation_buy_v[i]>=2)+int(trend_inflect_buy_v[i]>=JT.TREND_INFLECTION_STRONG)+int(market_turn_bull_v[i]>=JT.MARKET_TURN_STRONG)
        elif obj_side<0:
            support_count+=int(continuation_sell_v[i]>=2)+int(trend_inflect_sell_v[i]>=JT.TREND_INFLECTION_STRONG)+int(market_turn_bear_v[i]>=JT.MARKET_TURN_STRONG)
        obj_summary=f"객관 B{buy_score[i]:.1f} / S{sell_score[i]:.1f}"
        objective_alignment[i]='MIXED';objective_adjustment[i]='NONE'
        if base_side!=0 and obj_side==base_side:
            objective_alignment[i]='ALIGNED';objective_adjustment[i]='CONFIRM'
            final_conf[i]=min(99.,max(final_conf[i],base_conf[i])+min(7.,objective_conf[i]*0.08+max(obj_gap-3,0)*0.25))
            final_details[i]=_append_note(final_details[i],f"객관 엔진 동일 방향 확인 ({obj_summary})")
            if not str(final_reasons[i] or '').strip():
                final_reasons[i]=objective_reasons[i]
            if base_label in ('WATCH_BUY','WATCH_SELL','BUY','SELL') and obj_gap>=6 and support_count>=2 and objective_conf[i]>=60:
                new_label=_promote_buy(base_label) if obj_side>0 else _promote_sell(base_label)
                if new_label!=base_label:
                    final_labels[i]=new_label;objective_adjustment[i]='UPGRADE'
                    final_actions[i]=_default_action_label(new_label)
                    final_reasons[i]=_append_note(final_reasons[i],f"객관 차트 점수도 {'매수' if obj_side>0 else '매도'} 우위라 판단 강도를 높였습니다",' ')
                    if obj_side>0:final_buy_agree[i]=max(final_buy_agree[i],buy_agree[i])
                    else:final_sell_agree[i]=max(final_sell_agree[i],sell_agree[i])
        elif base_side==0 and obj_side!=0:
            if obj_gap>=8 and support_count>=2 and objective_conf[i]>=62:
                if obj_side>0:
                    new_label='BUY' if obj_label in ('BUY','STRONG_BUY') and support_count>=3 else 'WATCH_BUY'
                else:
                    new_label='SELL' if obj_label in ('SELL','STRONG_SELL') and support_count>=3 else 'WATCH_SELL'
                final_labels[i]=new_label;objective_adjustment[i]='ACTIVATE'
                final_conf[i]=max(final_conf[i],min(72.,objective_conf[i]*0.88))
                final_reasons[i]=objective_reasons[i]
                final_details[i]=_append_note(final_details[i],f"객관 엔진 우세 ({obj_summary})")
                final_actions[i]=_default_action_label(new_label)
                final_contrast[i]=_append_note(final_contrast[i],objective_contrasts[i],'; ')
                if obj_side>0:final_buy_agree[i]=max(final_buy_agree[i],buy_agree[i])
                else:final_sell_agree[i]=max(final_sell_agree[i],sell_agree[i])
        elif base_side!=0 and obj_side!=0 and base_side!=obj_side:
            objective_alignment[i]='CONFLICT'
            final_contrast[i]=_append_note(final_contrast[i],f"객관 엔진은 {'매수' if obj_side>0 else '매도'} 우세 ({obj_summary})",'; ')
            final_details[i]=_append_note(final_details[i],f"objective conflict {obj_summary}")
            final_conf[i]=max(28.,final_conf[i]-min(14.,obj_gap*0.9+objective_conf[i]*0.04))
            if obj_gap>=8 and objective_conf[i]>=64 and support_count>=2:
                prev_label=final_labels[i]
                final_labels[i]=_downgrade_buy(base_label,severe=bool(obj_gap>=12 and support_count>=3)) if base_side>0 else _downgrade_sell(base_label,severe=bool(obj_gap>=12 and support_count>=3))
                if final_labels[i]==prev_label and obj_gap>=10:
                    final_labels[i]='MIXED'
                if final_labels[i]!=prev_label:
                    objective_adjustment[i]='DOWNGRADE';final_downgrade[i]+=1
                    final_actions[i]=_default_action_label(final_labels[i])
                    final_reasons[i]="위원회 판단과 객관 차트 점수가 엇갈려 최종 판단을 한 단계 보수적으로 조정했습니다."
        elif obj_label=='MIXED' and conflict_score[i]>=1.6:
            objective_adjustment[i]='MIXED'
            final_conf[i]=max(25.,final_conf[i]-4.)
            final_contrast[i]=_append_note(final_contrast[i],f"객관 엔진 충돌도 {conflict_score[i]:.1f}",'; ')

        if not str(final_actions[i] or '').strip():
            final_actions[i]=_default_action_label(final_labels[i])
        if not str(final_reasons[i] or '').strip():
            final_reasons[i]=objective_reasons[i] if obj_side!=0 else "추가 확인이 필요한 구간입니다."

    df['Objective_Buy_Score']=buy_score;df['Objective_Sell_Score']=sell_score;df['Objective_Conflict_Score']=conflict_score
    df['Objective_Trend_Buy']=trend_buy_score;df['Objective_Trend_Sell']=trend_sell_score
    df['Objective_Momentum_Buy']=momentum_buy_score;df['Objective_Momentum_Sell']=momentum_sell_score
    df['Objective_Money_Buy']=money_buy_score;df['Objective_Money_Sell']=money_sell_score
    df['Objective_Reversal_Buy']=reversal_buy_score;df['Objective_Reversal_Sell']=reversal_sell_score
    df['Objective_Location_Buy']=location_buy_score;df['Objective_Location_Sell']=location_sell_score
    df['Objective_Signal_Buy']=signal_buy_score;df['Objective_Signal_Sell']=signal_sell_score
    df['Objective_Combo_Buy']=combo_buy_score;df['Objective_Combo_Sell']=combo_sell_score
    df['Objective_Judgment']=objective_labels;df['Objective_PreVeto_Judgment']=objective_pre_labels;df['Objective_Confidence']=objective_conf
    df['Objective_Buy_Agree']=buy_agree;df['Objective_Sell_Agree']=sell_agree
    df['Objective_Reason']=objective_reasons;df['Objective_Detail']=objective_details;df['Objective_Action_Label']=objective_actions
    df['Objective_Contrast_Notes']=objective_contrasts;df['Objective_Alignment']=objective_alignment;df['Objective_Adjustment']=objective_adjustment

    df['PreVeto_Judgment']=base_pre_labels;df['Trade_Judgment']=final_labels;df['Judgment_Confidence']=final_conf
    df['Buy_Agree']=final_buy_agree;df['Sell_Agree']=final_sell_agree
    df['Downgrade_Count']=final_downgrade;df['Macro_Risk_Off_Count']=base_macro_off;df['Macro_Risk_On_Count']=base_macro_on;df['Flip_Guard_Triggered']=base_flip_guard
    df['Judgment_Reason']=final_reasons;df['Judgment_Detail']=final_details;df['Action_Label']=final_actions;df['Contrast_Notes']=final_contrast

    is_buy=pd.Series(final_labels,index=idx).isin(list(_OBJECTIVE_BUY_LABELS))
    is_sell=pd.Series(final_labels,index=idx).isin(list(_OBJECTIVE_SELL_LABELS))
    df['System_Turn_Bull']=(is_buy & ~is_buy.shift(1).fillna(False)).values
    df['System_Turn_Bear']=(is_sell & ~is_sell.shift(1).fillna(False)).values
    return df
