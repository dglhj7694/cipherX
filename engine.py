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
    PAIRED={('MACD_Cross_Buy','MACD_Cross_Sell'):12,('Bullish_Engulfing','Bearish_Engulfing'):5,('Hammer','Shooting_Star'):5,('Morning_Star','Evening_Star'):7,('DMI_Cross_Bull','DMI_Cross_Bear'):10,('Pullback_123_Bull','Pullback_123_Bear'):7,('Expansion_BO','Expansion_BD'):10,('Gilligans_Buy','Gilligans_Sell'):10,('Slingshot_Bull','Slingshot_Bear'):7,('MF_Cross_Bull','MF_Cross_Bear'):10,('Kumo_Breakout_Bull','Kumo_Breakout_Bear'):10,('StochRSI_Cross_Buy','StochRSI_Cross_Sell'):7,('ADX_Momentum_Buy','ADX_Momentum_Sell'):10,('EMA_Pullback_Buy','EMA_Pullback_Sell'):7,('SuperTrend_Buy','SuperTrend_Sell'):10,('Boomer_Buy','Boomer_Sell'):10,('Setup_180_Bull','Setup_180_Bear'):7,('VWAP_Bounce_Buy','VWAP_Reject_Sell'):7,('Momentum_Ignition_Buy','Momentum_Ignition_Sell'):10,('Volume_Dry_Breakout_Buy','Volume_Dry_Breakout_Sell'):7,('Doji_Breakout_Buy','Doji_Breakout_Sell'):5,('Three_Bar_Reversal_Buy','Three_Bar_Reversal_Sell'):5}
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
    df=detect_combined_scans(df,vol_ratio,hma_r);df=compute_10layer_scores(df,vol_ratio,hma_r_v);df=compute_committee_ensemble(df,vol_ratio,hma_r_v)
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
    df['CS_Trend_Continuation_Buy']=up_&(C>N('MA20'))&(F('EMA_Pullback_Buy')|F('MA20_Support')|F('MA50_Support'))&(wr_|mr_)&(vr>=1.0)&(N('ADX')>=18)
    df['CS_Trend_Continuation_Sell']=dn_&(C<N('MA20'))&(F('EMA_Pullback_Sell')|F('MA20_Resistance')|F('MA50_Resistance'))&(wf_|mf_)&(vr>=1.0)&(N('ADX')>=18)
    df['CS_Reversal_Cluster_Buy']=(dbc_>=2)&os_ctx&(bc_|llw_|F('Parabolic_Bottom_Buy')|F('Volume_Climax_Buy'))&(wr_|F('UTBot_Buy')|F('Hull_Turn_Bull'))&vok_
    df['CS_Reversal_Cluster_Sell']=(dsc_>=2)&ob_ctx&(sc__|luw_|F('Parabolic_Top_Sell')|F('Volume_Climax_Sell'))&(wf_|F('UTBot_Sell')|F('Hull_Turn_Bear'))&vok_
    df['CS_Breakout_Confirm_Buy']=(F('Expansion_BO')|F('Kumo_Breakout_Bull')|F('BB_Upper_Break')|F('New_52W_High'))&(vr>=1.4)&(N('ADX')>=20)&(N('MACD_Hist')>N('MACD_Hist').shift(1))
    df['CS_Breakout_Confirm_Sell']=(F('Expansion_BD')|F('Kumo_Breakout_Bear')|F('BB_Lower_Break')|F('New_52W_Low'))&(vr>=1.4)&(N('ADX')>=20)&(N('MACD_Hist')<N('MACD_Hist').shift(1))

    df['CS_Momentum_Accel_Buy']=(N('Composite_Accel',0)>1.5)&vok_&(C>N('MA50'))
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
    a200=C>N('MA200');a50=C>N('MA50');a20=C>N('MA20');b200=C<N('MA200');b50=C<N('MA50');b20=C<N('MA20')
    mhr=N('MACD_Hist')>N('MACD_Hist').shift(1);mhf=N('MACD_Hist')<N('MACD_Hist').shift(1)
    rr_=N('RSI')>N('RSI').shift(1);rf_=N('RSI')<N('RSI').shift(1);wr_=N('WT1')>N('WT1').shift(1);wf_=N('WT1')<N('WT1').shift(1)
    obv=N('OBV');obvm=obv.rolling(20,min_periods=10).mean();regime=N('Regime');ca=N('Composite_Accel');pb=N('Percent_B');rmfi=N('RSI_MFI');cmf=N('CMF')
    kumo_top=pd.concat([N('Ichimoku_SenkouA'),N('Ichimoku_SenkouB')],axis=1).max(axis=1);kumo_bot=pd.concat([N('Ichimoku_SenkouA'),N('Ichimoku_SenkouB')],axis=1).min(axis=1);utbot_dir=N('UTBot_Dir')
    wt1=N('WT1');rsi=N('RSI');stochk=N('StochK');mfi=N('MFI')
    F=lambda c:df.get(c,pd.Series(False,index=idx)).fillna(False)
    os_base=((wt1<-60)|(rsi<32)|(stochk<20))&(wr_|(wt1>wt1.shift(1)))
    ob_base=((wt1>60)|(rsi>68)|(stochk>80))&(wf_|(wt1<wt1.shift(1)))
    os_turn=F('UTBot_Buy').rolling(3,min_periods=1).max().astype(bool)|F('MACD_Cross_Buy')|F('StochRSI_Cross_Buy')|F('WT_Up')
    ob_turn=F('UTBot_Sell').rolling(3,min_periods=1).max().astype(bool)|F('MACD_Cross_Sell')|F('StochRSI_Cross_Sell')|F('WT_Down')
    os_rev=os_base&(os_turn|F('Bull_Divergence')|F('RSI_Bull_Divergence')|F('CS_Bottom_Fishing_Buy'))
    ob_rev=ob_base&(ob_turn|F('Bear_Divergence')|F('RSI_Bear_Divergence')|F('CS_Top_Fishing_Sell'))
    # BUY
    # BUY
    bt=pd.Series(0.,index=idx);bt+=a200.astype(float)*2.5+a50.astype(float)*1.5+a20.astype(float)*1;bt+=np.where(N('MA50')>N('MA200'),1.5,0)+np.where(N('Plus_DI')>N('Minus_DI'),1,0)+np.where(N('ST_Direction')==1,1,0);bt+=_sp(df,'Cross_Above_50MA',1)+_sp(df,'Golden_Cross',1.5)+np.where(b200&b50,-2.,0);bt+=np.where((b50|b200)&os_rev,1.8,0)-np.where((a50|a200)&ob_rev,1.2,0);df['BL_Trend']=bt.clip(-2,JT.TREND_CAP)
    bm=pd.Series(0.,index=idx)
    for s,p in [('MACD_Cross_Buy',2.5),('MACD_Zero_Cross_Buy',2),('StochRSI_Cross_Buy',2),('ADX_Momentum_Buy',2),('VWAP_Bounce_Buy',1.5)]:bm+=_sp(df,s,p)
    bm=bm.clip(upper=6);bm+=np.select([(N('MACD_Hist')>0)&mhr,(N('MACD_Hist')>0)&mhf,(N('MACD_Hist')<0)&mhr],[2,.5,1.5],default=0.);
    bm+=np.clip((40-N('RSI'))*0.15,0,3)+rr_.astype(float)+np.clip((25-N('StochK'))*0.15,0,2.5)+np.clip((-10-N('WT1'))*0.05,0,3)+wr_.astype(float)
    bm+=_sp(df,'UTBot_Buy',2.5)+_sp(df,'StochSlow_Cross_Buy',1.5)+_sp(df,'Squeeze_Mom_Cross_Up',1.5)+np.where(hma_r_v&wr_.values,1,0);bm+=np.where(os_rev,1.5,0)-np.where(ob_rev,1.0,0);df['BL_Momentum']=bm.clip(-2,JT.MOMENTUM_CAP)
    bcc=pd.Series(0.,index=idx)
    for s,p in [('Morning_Star',3.5),('Bullish_Engulfing',3),('Hammer',2.5),('Outside_Bullish',2.5),('Doji_Bullish',1),('Three_Bar_Reversal_Buy',2.5)]:bcc=np.maximum(bcc,_sp(df,s,p))
    df['BL_Candle']=pd.Series(bcc,index=idx).clip(upper=JT.CANDLE_CAP)
    bb_=pd.Series(0.,index=idx);bb_+=_sp(df,'BB_Squeeze_End_Bull',3)+_sp(df,'NR7_2',1.5)+_sp(df,'Calm_After_Storm',1);
    bb_+=np.clip((0.5-pb)*6,-2,3)+_sp(df,'BB_Lower_Bounce',2);df['BL_BB']=bb_.clip(-1,JT.BB_CAP)
    bv=pd.Series(0.,index=idx);bv+=_sp(df,'Volume_Climax_Buy',3)+_sp(df,'Pocket_Pivot',2)+_sp(df,'OBV_Div_Buy',1.5)+_sp(df,'Volume_POC_Breakout',2.5)+_sp(df,'Volume_Dry_Breakout_Buy',2);
    bv+=np.clip((vr-1)*1.5,0,3)*(C>O).astype(float)+np.where(obv>obvm,1,np.where(obv<obvm,-1,0));df['BL_Volume']=bv.clip(-1,JT.VOLUME_CAP)
    bmf=pd.Series(0.,index=idx);bmf+=np.clip(-rmfi*0.2,-0.5,2)+_sp(df,'MF_Cross_Bull',2)+_sp(df,'MF_Bull_Div',2)+_sp(df,'MF_Accel_Up',1)+_sp(df,'CMF_Bull',1.5);
    bmf+=np.clip(cmf*8,-1,2);df['BL_MF']=bmf.clip(-1,JT.MF_CAP)
    bp=pd.Series(0.,index=idx);bp+=_spd(df,'Gold_Dot',4);bp+=np.where(bp==0,_spd(df,'Green_Dot_T1',2.5),0)
    for s,p in [('Bull_Divergence',2),('Pullback_123_Bull',2.5),('Setup_180_Bull',2),('Boomer_Buy',2),('Expansion_BO',3),('Gilligans_Buy',2.5),('Lizard_Bull',2),('NonADX_123_Bull',1.5),('EMA_Pullback_Buy',2),('Momentum_Ignition_Buy',3),('SuperTrend_Buy',2),('Parabolic_Bottom_Buy',3),('Kumo_Breakout_Bull',2.5),('Reversal_New_Highs',2.5),('Slingshot_Bull',2),('Jack_In_Box_Bull',2),('Relative_Strength_Buy',2.5),('VP_VAL_Support',1.5),('VuManChu_Bull',3),('Hull_Turn_Bull',2),('Doji_Breakout_Buy',1.5),('Three_Bar_Reversal_Buy',2),('CS_Bottom_Fishing_Buy',3),('CS_Oversold_Bounce_Buy',1.5)]:bp+=_sp(df,s,p)
    df['BL_Pattern']=bp.clip(upper=JT.PATTERN_CAP)
    bcs=pd.Series(0.,index=idx)
    for cn,cfg in COMBINED_SCAN_REGISTRY.items():
        if cfg['dir']!='buy' or cn not in df.columns:continue
        bcs+=np.where(df[cn].fillna(False),{1:JT.COMBO_T1,2:JT.COMBO_T2,3:JT.COMBO_T3}.get(cfg['tier'],1),0.)
    df['BL_Combined']=bcs.clip(upper=JT.COMBINED_CAP)
    bl_=pd.Series(0.,index=idx);bl_+=np.clip(ca*2.5,-1,3.5)+_sp(df,'Setup_Squeeze_Bull',1.5)+_sp(df,'Momentum_Accel_Buy',2)+_sp(df,'WT_Convergence_Bull',1.5)+_sp(df,'Volume_Dry_Up',.5)+np.where(os_rev,1.2,0)+_sp(df,'CS_Bottom_Fishing_Buy',2)
    bl_+=np.where(utbot_dir==1,1,np.where(utbot_dir==-1,-.5,0))+np.where(hma_r_v,.5,-.5)
    sp_buy=pd.Series(0.,index=idx);sp_buy+=np.clip((10-N('WT1'))*0.05,0,2)+np.clip((45-N('RSI'))*0.1,0,2)+np.clip((35-N('StochK'))*0.1,0,1)+np.clip((35-mfi)*0.08,0,1.5)+np.clip(ca*1.5,0,2);sp_buy+=np.where(os_rev,1.0,0)
    df['Setup_Pressure_Buy']=sp_buy;bl_+=np.clip(sp_buy*0.4,0,3);df['BL_Leading']=bl_.clip(-1,JT.LEADING_CAP)
    blag=pd.Series(0.,index=idx);blag+=a200.astype(float)*1.0+a50.astype(float)*1.0+(N('MA50')>N('MA200')).astype(float)*1.0;
    blag+=np.clip(regime.values*1.0,-1.5,3)+np.where(C>kumo_top,1.5,np.where(C<kumo_top,-1,0))+np.clip((N('RS_Ratio',1)-1.0)*30,-1.5,2);df['BL_Lagging']=blag.clip(-2,JT.LAGGING_CAP)
    
    # SELL
    st_=pd.Series(0.,index=idx);st_+=b200.astype(float)*2.5+b50.astype(float)*1.5+b20.astype(float)*1;st_+=np.where(N('MA50')<N('MA200'),1.5,0)+np.where(N('Minus_DI')>N('Plus_DI'),1,0)+np.where(N('ST_Direction')==-1,1,0);st_+=_sp(df,'Fell_Below_50MA',1)+_sp(df,'Death_Cross',1.5)+np.where(a200&a50,-2.,0);st_+=np.where((a50|a200)&ob_rev,1.8,0)-np.where((b50|b200)&os_rev,1.2,0);df['SL_Trend']=st_.clip(-2,JT.TREND_CAP)
    sm_=pd.Series(0.,index=idx)
    for s,p in [('MACD_Cross_Sell',2.5),('MACD_Zero_Cross_Sell',2),('StochRSI_Cross_Sell',2),('ADX_Momentum_Sell',2),('VWAP_Reject_Sell',1.5)]:sm_+=_sp(df,s,p)
    sm_=sm_.clip(upper=6);sm_+=np.select([(N('MACD_Hist')<0)&mhf,(N('MACD_Hist')<0)&mhr,(N('MACD_Hist')>0)&mhf],[2,.5,1.5],default=0.);
    sm_+=np.clip((N('RSI')-60)*0.15,0,3)+rf_.astype(float)+np.clip((N('StochK')-75)*0.15,0,2.5)+np.clip((N('WT1')-10)*0.05,0,3)+wf_.astype(float)
    sm_+=_sp(df,'UTBot_Sell',2.5)+_sp(df,'StochSlow_Cross_Sell',1.5)+_sp(df,'Squeeze_Mom_Cross_Down',1.5)+np.where(~hma_r_v&wf_.values,1,0);sm_+=np.where(ob_rev,1.5,0)-np.where(os_rev,1.0,0);df['SL_Momentum']=sm_.clip(-2,JT.MOMENTUM_CAP)
    scc_=pd.Series(0.,index=idx)
    for s,p in [('Evening_Star',3.5),('Bearish_Engulfing',3),('Shooting_Star',2.5),('Outside_Bearish',2.5),('Doji_Bearish',1),('Three_Bar_Reversal_Sell',2.5)]:scc_=np.maximum(scc_,_sp(df,s,p))
    df['SL_Candle']=pd.Series(scc_,index=idx).clip(upper=JT.CANDLE_CAP)
    sbb_=pd.Series(0.,index=idx);sbb_+=_sp(df,'BB_Squeeze_End_Bear',3)+_sp(df,'NR7_2',1.5)+_sp(df,'Calm_After_Storm',1);
    sbb_+=np.clip((pb-0.5)*6,-2,3)+_sp(df,'BB_Lower_Break',1.5);df['SL_BB']=sbb_.clip(-1,JT.BB_CAP)
    sv_=pd.Series(0.,index=idx);sv_+=_sp(df,'Volume_Climax_Sell',3)+_sp(df,'OBV_Div_Sell',1.5)+_sp(df,'Volume_POC_Breakdown',2.5)+_sp(df,'Volume_Dry_Breakout_Sell',2);
    sv_+=np.clip((vr-1)*1.5,0,3)*(C<O).astype(float)+np.where(obv<obvm,1,np.where(obv>obvm,-1,0));df['SL_Volume']=sv_.clip(-1,JT.VOLUME_CAP)
    smf_=pd.Series(0.,index=idx);smf_+=np.clip(rmfi*0.2,-0.5,2)+_sp(df,'MF_Cross_Bear',2)+_sp(df,'MF_Bear_Div',2)+_sp(df,'MF_Accel_Dn',1)+_sp(df,'CMF_Bear',1.5);
    smf_+=np.clip(-cmf*8,-1,2);df['SL_MF']=smf_.clip(-1,JT.MF_CAP)
    spp_=pd.Series(0.,index=idx);spp_+=_spd(df,'Blood_Diamond',4);spp_+=np.where(spp_==0,_spd(df,'Red_Dot_T1',2.5),0)
    for s,p in [('Bear_Divergence',2),('Pullback_123_Bear',2.5),('Setup_180_Bear',2),('Boomer_Sell',2),('Expansion_BD',3),('Gilligans_Sell',2.5),('Lizard_Bear',2),('NonADX_123_Bear',1.5),('EMA_Pullback_Sell',2),('Momentum_Ignition_Sell',3),('SuperTrend_Sell',2),('Parabolic_Top_Sell',3),('Kumo_Breakout_Bear',2.5),('Reversal_New_Lows',2.5),('Slingshot_Bear',2),('Jack_In_Box_Bear',2),('Relative_Strength_Sell',2),('VP_VAH_Resistance',1.5),('VuManChu_Bear',3),('Hull_Turn_Bear',2),('Doji_Breakout_Sell',1.5),('Three_Bar_Reversal_Sell',2),('CS_Top_Fishing_Sell',3),('CS_Overbought_Fade_Sell',1.5)]:spp_+=_sp(df,s,p)
    df['SL_Pattern']=spp_.clip(upper=JT.PATTERN_CAP)
    scs_=pd.Series(0.,index=idx)
    for cn,cfg in COMBINED_SCAN_REGISTRY.items():
        if cfg['dir']!='sell' or cn not in df.columns:continue
        scs_+=np.where(df[cn].fillna(False),{1:JT.COMBO_T1,2:JT.COMBO_T2,3:JT.COMBO_T3}.get(cfg['tier'],1),0.)
    df['SL_Combined']=scs_.clip(upper=JT.COMBINED_CAP)
    sl__=pd.Series(0.,index=idx);sl__+=np.clip(-ca*2.5,-1,3.5)+_sp(df,'Setup_Squeeze_Bear',1.5)+_sp(df,'Momentum_Accel_Sell',2)+_sp(df,'WT_Convergence_Bear',1.5)+np.where(ob_rev,1.2,0)+_sp(df,'CS_Top_Fishing_Sell',2)
    sl__+=np.where(utbot_dir==-1,1,np.where(utbot_dir==1,-.5,0))+np.where(~hma_r_v,.5,-.5)
    sp_sell=pd.Series(0.,index=idx);sp_sell+=np.clip((N('WT1')+10)*0.05,0,2)+np.clip((N('RSI')-55)*0.1,0,2)+np.clip((N('StochK')-65)*0.1,0,1)+np.clip((mfi-65)*0.08,0,1.5)+np.clip(-ca*1.5,0,2);sp_sell+=np.where(ob_rev,1.0,0)
    df['Setup_Pressure_Sell']=sp_sell;sl__+=np.clip(sp_sell*0.4,0,3);df['SL_Leading']=sl__.clip(-1,JT.LEADING_CAP)
    slag_=pd.Series(0.,index=idx);slag_+=b200.astype(float)*1.0+b50.astype(float)*1.0+(N('MA50')<N('MA200')).astype(float)*1.0;
    slag_+=np.clip(-regime.values*1.0,-1.5,3)+np.where(C<kumo_bot,1.5,np.where(C>kumo_top,-1,0))+np.clip((1.0-N('RS_Ratio',1))*30,-1.5,2);df['SL_Lagging']=slag_.clip(-2,JT.LAGGING_CAP)
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
    a50=C>N('MA50');a200=C>N('MA200');b50=C<N('MA50');b200=C<N('MA200');atr=N('ATR')
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

def _committee_trend(df,N):
    C=df['Close'];idx=df.index;score=pd.Series(0.,index=idx)
    a200=C>N('MA200');a50=C>N('MA50');a20=C>N('MA20');b200=C<N('MA200');b50=C<N('MA50');b20=C<N('MA20')
    score += a200.astype(float)*10 + a50.astype(float)*10 + a20.astype(float)*10
    score -= b200.astype(float)*10 + b50.astype(float)*10 + b20.astype(float)*10
    ma50s=(N('MA50')-N('MA50').shift(10))/(N('MA50').shift(10)+1e-10)*100;score+=np.clip(ma50s*3,-15,15)
    adx_val=N('ADX');pdi=N('Plus_DI');mdi=N('Minus_DI');di_diff=pdi-mdi;score+=np.where(adx_val>25,np.clip(di_diff*.5,-15,15),np.clip(di_diff*.2,-5,5))
    score+=np.where(N('ST_Direction')==1,10,np.where(N('ST_Direction')==-1,-10,0))
    kt=pd.concat([N('Ichimoku_SenkouA'),N('Ichimoku_SenkouB')],axis=1).max(axis=1);kb=pd.concat([N('Ichimoku_SenkouA'),N('Ichimoku_SenkouB')],axis=1).min(axis=1)
    score+=np.where(C>kt,10,np.where(C<kb,-10,0))
    atr=N('ATR');d50=(C-N('MA50'))/(atr+1e-10);d200=(C-N('MA200'))/(atr+1e-10)
    score += np.clip(-d50 * 3.2, -14, 14)
    score += np.clip(-d200 * 2.8, -12, 12)
    wt1=N('WT1');rsi=N('RSI')
    score += np.where((wt1<-60)&(wt1>wt1.shift(1)),10,0)+np.where((wt1>60)&(wt1<wt1.shift(1)),-10,0)
    score += np.where((rsi<35)&(rsi>rsi.shift(1)),6,0)+np.where((rsi>65)&(rsi<rsi.shift(1)),-6,0)
    ma50a=ma50s-ma50s.shift(5);score+=np.where((ma50s<0)&(ma50a>0.5),8,0)+np.where((ma50s>0)&(ma50a<-0.5),-8,0)
    ns=(score/JT.TREND_NORM*100).clip(-100,100);conv=np.clip(adx_val.values*2,5,95)
    wt1=wt1.values;rsi=rsi.values;eos=np.clip((-50-wt1)/30,0,1)*.7+np.clip((30-rsi)/20,0,1)*.3;eob=np.clip((wt1-50)/30,0,1)*.7+np.clip((rsi-70)/20,0,1)*.3
    conv=conv*(1-np.maximum(eos,eob)*0.8);conv=np.clip(conv,5,95)
    return ns,pd.Series(conv,index=idx)

def _committee_momentum(df,N):
    idx=df.index;score=pd.Series(0.,index=idx);rsi=N('RSI');wt1=N('WT1');wt2=N('WT2');mh=N('MACD_Hist');stk=N('StochK');std=N('StochD');ca=N('Composite_Accel')
    score+=(rsi-50)*.6+np.where(rsi>rsi.shift(1),5,np.where(rsi<rsi.shift(1),-5,0))
    score+=wt1*.3+np.where(wt1>wt2,8,np.where(wt1<wt2,-8,0))+np.where(wt1>wt1.shift(1),5,np.where(wt1<wt1.shift(1),-5,0))
    score+=np.where(mh>mh.shift(1),8,np.where(mh<mh.shift(1),-8,0))+np.where(mh>0,5,np.where(mh<0,-5,0))
    score+=(stk-50)*.2+np.where((stk>std)&(stk<30),10,np.where((stk<std)&(stk>70),-10,0));score+=np.clip(ca*5,-15,15)
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
    score+=N('Upside_Space_Score')
    score+=np.clip((N('VP_Long_RR')-JT.VP_RR_FLOOR)*12,-18,10)
    score-=np.clip((N('VP_Short_RR')-JT.VP_RR_FLOOR)*12,0,12)
    ns=(score/JT.STRUCTURE_NORM*100).clip(-100,100)
    ne=(pb<.2).astype(float)+(pb>.8).astype(float)+(cb>0).astype(float)+(cs>0).astype(float)+(((C-val_).abs()/(C+1e-10)<.03)|((vah-C).abs()/(C+1e-10)<.03)).astype(float)+F('BB_Squeeze_End_Bull').astype(float)+F('BB_Squeeze_End_Bear').astype(float)+(N('VP_Long_RR')>JT.VP_RR_STRONG).astype(float)+(N('VP_Short_RR')>JT.VP_RR_STRONG).astype(float)
    conv=np.clip(ne.values*20+15,10,90)
    return ns,pd.Series(conv,index=idx)

def _committee_leading(df,N):
    idx=df.index;score=pd.Series(0.,index=idx);ut=N('UTBot_Dir');hma=df.get('HMA_Rising',pd.Series(False,index=idx)).fillna(False)
    score+=np.where(ut==1,20,np.where(ut==-1,-20,0))+np.where(hma,15,-15)
    sq=N('Squeeze_Momentum');sr=df.get('Squeeze_Mom_Rising',pd.Series(False,index=idx)).fillna(False)
    score+=np.where(sq>0,10,np.where(sq<0,-10,0))+np.where((sq>0)&sr,5,np.where((sq<0)&~sr,-5,0))
    ca=N('Composite_Accel');score+=np.clip(ca*8,-20,20)
    spb=N('Setup_Pressure_Buy');sps=N('Setup_Pressure_Sell')
    score += np.clip(spb * 2, 0, 20) - np.clip(sps * 2, 0, 20)
    F=lambda c:df.get(c,pd.Series(False,index=idx)).fillna(False)
    ma_gap=N('MA20_ATR_Gap');score-=np.clip((ma_gap-1.5)*8,0,20);score+=np.clip((-ma_gap-1.5)*8,0,20)
    for cn,cfg in COMBINED_SCAN_REGISTRY.items():
        if cn not in df.columns:continue
        pts={1:15,2:8,3:3}.get(cfg['tier'],3)
        if cfg['dir']=='buy':score+=np.where(F(cn),pts,0)
        elif cfg['dir']=='sell':score-=np.where(F(cn),pts,0)
    score+=np.where(F('VuManChu_Bull'),20,0)-np.where(F('VuManChu_Bear'),20,0)
    score+=np.where(F('Washout_Bottom_Hard'),35,0)-np.where(F('Blowoff_Top_Hard'),45,0)
    ns=(score/JT.LEADING_NORM*100).clip(-100,100)
    ag=(ut==1).astype(float)+hma.astype(float)+(sq>0).astype(float)+(ca>0).astype(float);dg=(ut==-1).astype(float)+(~hma).astype(float)+(sq<0).astype(float)+(ca<0).astype(float)
    conv=np.clip(np.maximum(ag.values,dg.values)*20+10+np.where(F('Blowoff_Top_Hard')|F('Washout_Bottom_Hard'),12,0),10,90)
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


def compute_committee_ensemble(df,vol_ratio,hma_r_v):
    idx=df.index;n=len(df);N=lambda c,d=0:df.get(c,pd.Series(d,index=idx)).fillna(d);F=lambda c:df.get(c,pd.Series(False,index=idx)).fillna(False)
    ctx=_detect_context_vectorized(df);df['Market_Context']=ctx
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
    cav=N('Composite_Accel');ab=np.clip(cav.values*3,-15,15);mh=N('MACD_Hist');mu=_vs(mh>mh.shift(1));md=_vs(mh<mh.shift(1))
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
    for ci,cm in enumerate(COMMITTEE_NAMES):
        s=es[:,ci];c=ec[:,ci];v=np.full(n,0,dtype=int);v=np.where((s>15)&(c>=25),1,v);v=np.where((s<-15)&(c>=25),-1,v);v=np.where(c<15,-99,v)
        df[f'CM_{cm}_Vote']=v;df[f'CM_{cm}_EffScore']=es[:,ci];df[f'CM_{cm}_EffConv']=ec[:,ci]
    df['Ensemble_Score']=ens
    # 판단
    bag=np.zeros(n,dtype=int);sag=np.zeros(n,dtype=int)
    for ci in range(NUM_COMMITTEES):bag+=((es[:,ci]>15)&(ec[:,ci]>=25)).astype(int);sag+=((es[:,ci]<-15)&(ec[:,ci]>=25)).astype(int)
    bag+=((ba_layers>=6)&(buy_total_arr>=20)).astype(int)
    sag+=((sa_layers>=6)&(sell_total_arr>=20)).astype(int)
    cth=np.zeros(n);cth=np.where(ctx_v==CTX_EXTREME_OS,-10,cth);cth=np.where(ctx_v==CTX_EXTREME_OB,10,cth);cth=np.where(ctx_v==CTX_STRONG_UP,5,cth);cth=np.where(ctx_v==CTX_STRONG_DN,-5,cth);cth=np.where(ctx_v==CTX_BOTTOMING,-8,cth);cth=np.where(ctx_v==CTX_TOPPING,8,cth)
    j=np.full(n,'NEUTRAL',dtype=object);conf=np.zeros(n,dtype=float)
    rs=[];rd=[];al=[];contrast_notes=[]
    obv_v=N('OBV').values;obv_mav=N('OBV').rolling(20,min_periods=10).mean().values;mhv=N('MACD_Hist').values;mhpv=np.roll(mhv,1)
    ma50_v=N('MA50').values;ma200_v=N('MA200').values;wt1_v=N('WT1').values;rsi_v=N('RSI').values;mfi_v=N('MFI').values
    adx_v=N('ADX').values;stoch_v=N('StochK').values;ut_v=N('UTBot_Dir').values;sq_v=df.get('Squeeze_On',pd.Series(False,index=idx)).values
    atr_norm = (N('ATR').values / (C + 1e-10)) * 100
    atr_scale = np.clip(atr_norm / 2.5, 0.75, 1.25)
    buy_labels=('STRONG_BUY','BUY','WATCH_BUY');sell_labels=('STRONG_SELL','SELL','WATCH_SELL');money_eff=es[:,money_i]
    for i in range(n):
        e=ens[i];ba=bag[i];sl=sag[i];sy=syn[i];adj=cth[i];sr=1 if abs(sy)>=15 else 0
        asc = atr_scale[i]
        sbt=(JT.STRONG_BUY_TH * asc)+adj;bt=(JT.BUY_TH * asc)+adj;wbt=(JT.WATCH_BUY_TH * asc)+adj*.5;sst=(JT.STRONG_SELL_TH * asc)-adj;st=(JT.SELL_TH * asc)-adj;wst=(JT.WATCH_SELL_TH * asc)-adj*.5
        if e>=sbt and ba>=(JT.STRONG_MIN_AGREE-sr):j[i]='STRONG_BUY'
        elif e>=bt and ba>=(JT.BUY_MIN_AGREE-sr):j[i]='BUY'
        elif e>=wbt and ba>=max(JT.WATCH_MIN_AGREE-sr,1):j[i]='WATCH_BUY'
        elif e<=sst and sl>=(JT.STRONG_MIN_AGREE-sr):j[i]='STRONG_SELL'
        elif e<=st and sl>=(JT.BUY_MIN_AGREE-sr):j[i]='SELL'
        elif e<=wst and sl>=max(JT.WATCH_MIN_AGREE-sr,1):j[i]='WATCH_SELL'
        elif (ctx_v[i] in (CTX_EXTREME_OS,CTX_BOTTOMING)) and ba>=2 and (sy>6 or pred[i]>5) and e>=(wbt-6):j[i]='BUY'
        elif (ctx_v[i] in (CTX_EXTREME_OB,CTX_TOPPING)) and sl>=2 and (sy<-6 or pred[i]<-5) and e<=(wst+6):j[i]='SELL'
        elif ba>=3 and sl>=3:j[i]='MIXED'
        notes=[]
        if pv_bear_v[i]:notes.append("price up but OBV/CMF/volume diverged")
        elif pv_bull_v[i]:notes.append("price down but money flow improved")
        if low_vol_v[i] and price_slope_v[i]>0:notes.append("volume below 0.7x average")
        if long_rr_v[i]<JT.VP_RR_FLOOR and e>0:notes.append(f"long RR {long_rr_v[i]:.2f} vs VAH/POC")
        if short_rr_v[i]<JT.VP_RR_FLOOR and e<0:notes.append(f"short RR {short_rr_v[i]:.2f} vs VAL/POC")
        if hard_blowoff_v[i]:notes.append("blow-off top >3 ATR above MA20 with 2x red volume")
        severe_buy=(money_eff[i]<=JT.MONEY_VETO_NEUTRAL) or (cmf[i]<0 and obv_slope_v[i]<0 and long_rr_v[i]<0.9)
        severe_sell=(money_eff[i]>=abs(JT.MONEY_VETO_NEUTRAL)) or (cmf[i]>0 and obv_slope_v[i]>0 and short_rr_v[i]<0.9)
        if hard_blowoff_v[i]:
            if j[i] in buy_labels or j[i] in ('NEUTRAL','MIXED'):j[i]='STRONG_SELL' if (sl>=max(JT.WATCH_MIN_AGREE-sr,1) and e<=st) else 'SELL'
        elif j[i] in buy_labels:
            if pv_bear_v[i]:j[i]=_downgrade_buy(j[i],severe=(j[i]=='STRONG_BUY' and severe_buy))
            if long_rr_v[i]<JT.VP_RR_FLOOR:j[i]=_downgrade_buy(j[i],severe=(long_rr_v[i]<0.75 and money_eff[i]<0))
            if low_vol_v[i] and price_slope_v[i]>0:j[i]=_downgrade_buy(j[i],severe=False)
        elif j[i] in sell_labels:
            if pv_bull_v[i]:j[i]=_downgrade_sell(j[i],severe=(j[i]=='STRONG_SELL' and severe_sell))
            if short_rr_v[i]<JT.VP_RR_FLOOR:j[i]=_downgrade_sell(j[i],severe=(short_rr_v[i]<0.75 and money_eff[i]>0))
        contrast_notes.append('; '.join(notes[:3]))
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
        rs.append(r);rd.append(d);al.append(a)
    df['Trade_Judgment']=j;df['Judgment_Confidence']=conf;df['Buy_Agree']=bag;df['Sell_Agree']=sag
    df['Judgment_Reason']=rs;df['Judgment_Detail']=rd;df['Action_Label']=al;df['Contrast_Notes']=contrast_notes
    
    # 🎯 시스템 전면 전환(Macro Flip) 시그널 추가
    is_buy = pd.Series(j).isin(['STRONG_BUY', 'BUY', 'WATCH_BUY'])
    is_sell = pd.Series(j).isin(['STRONG_SELL', 'SELL', 'WATCH_SELL'])
    df['System_Turn_Bull'] = (is_buy & ~is_buy.shift(1).fillna(False)).values
    df['System_Turn_Bear'] = (is_sell & ~is_sell.shift(1).fillna(False)).values
    
    return df
