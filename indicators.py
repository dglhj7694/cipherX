import pandas as pd
import numpy as np
from scipy.signal import find_peaks
from config import JT
from utils import fetch_market_proxy, fetch_spy

def compute_rsi(s,p=14):d=s.diff();g,l_=d.clip(lower=0),-d.clip(upper=0);return 100-(100/(1+g.ewm(alpha=1/p,min_periods=p).mean()/(l_.ewm(alpha=1/p,min_periods=p).mean()+1e-10)))
def compute_mfi(h,l,c,v,p=14):tp=(h+l+c)/3;r=tp*v;d=tp.diff();return 100-(100/(1+r.where(d>=0,0.).rolling(p).sum()/(r.where(d<0,0.).rolling(p).sum()+1e-10)))
def compute_rsi_mfi(h,l,c,v,p=60):rf,mf=compute_rsi(c,20),compute_mfi(h,l,c,v,20);rs,ms=compute_rsi(c,p),compute_mfi(h,l,c,v,p);return (((rf-50)+(mf-50))/2)*.6+(((rs-50)+(ms-50))/2)*.4
def compute_wavetrend(h,l,c,ch=9,avg=12,ma=3):ap=(h+l+c)/3;esa=ap.ewm(span=ch,adjust=False).mean();d=abs(ap-esa).ewm(span=ch,adjust=False).mean();ci=(ap-esa)/(0.015*d+1e-10);w1=ci.ewm(span=avg,adjust=False).mean();w2=w1.rolling(ma).mean();return w1,w2,(w1>w2)&(w1.shift(1)<=w2.shift(1)),(w1<w2)&(w1.shift(1)>=w2.shift(1))
def compute_stoch_rsi(c,rl=14,sl=14,ks=3,ds=3):r=compute_rsi(c,rl);mn,mx=r.rolling(sl).min(),r.rolling(sl).max();k=(((r-mn)/(mx-mn+1e-10))*100).rolling(ks).mean();return k,k.rolling(ds).mean()
def compute_tr(h,l,c):pc=c.shift(1);return pd.concat([h-l,(h-pc).abs(),(l-pc).abs()],axis=1).max(axis=1)
def compute_adx(h,l,c,p=14):tr=compute_tr(h,l,c);ph,pl=h.shift(1),l.shift(1);plus_dm=pd.Series(np.where((h-ph)>(pl-l),np.maximum(h-ph,0),0),index=h.index,dtype=float);minus_dm=pd.Series(np.where((pl-l)>(h-ph),np.maximum(pl-l,0),0),index=h.index,dtype=float);a=tr.ewm(alpha=1/p,min_periods=p).mean();pdi=100*plus_dm.ewm(alpha=1/p,min_periods=p).mean()/(a+1e-10);mdi=100*minus_dm.ewm(alpha=1/p,min_periods=p).mean()/(a+1e-10);dx=100*(pdi-mdi).abs()/(pdi+mdi+1e-10);return dx.ewm(alpha=1/p,min_periods=p).mean(),pdi,mdi
def compute_obv(c,v):return (v*np.sign(c.diff()).fillna(0)).cumsum()
def compute_obv_slope(obv,v,p=5):
    scale=v.rolling(p*3,min_periods=p).mean()*max(p,1)
    return (obv-obv.shift(p))/(scale+1e-10)
def compute_macd(c,f=12,s=26,sig=9):ml=c.ewm(span=f,adjust=False).mean()-c.ewm(span=s,adjust=False).mean();sl=ml.ewm(span=sig,adjust=False).mean();return ml,sl,ml-sl
def compute_ichimoku(h,l,c,tp=9,kp=26,sp=52,d=26):tk=(h.rolling(tp).max()+l.rolling(tp).min())/2;kj=(h.rolling(kp).max()+l.rolling(kp).min())/2;sa=((tk+kj)/2).shift(d);sb=((h.rolling(sp).max()+l.rolling(sp).min())/2).shift(d);return tk,kj,sa,sb
def compute_cmf(h,l,c,v,p=20):m=((c-l)-(h-c))/(h-l+1e-10);return (m*v).rolling(p).sum()/(v.rolling(p).sum()+1e-10)
def compute_supertrend(h,l,c,tr,per=10,mult=3.):
    a=tr.rolling(per).mean();hl=(h+l)/2;up=(hl+mult*a).values.copy();dn=(hl-mult*a).values.copy();cl=c.values;n=len(c);sv=np.full(n,np.nan);dv=np.zeros(n,dtype=int);fv=per
    if fv>=n:return pd.Series(np.nan,index=c.index),pd.Series(0,index=c.index,dtype=int)
    dv[fv]=1;sv[fv]=dn[fv]
    for i in range(fv+1,n):
        if dv[i-1]==1:dn[i]=max(dn[i],dn[i-1]) if not np.isnan(dn[i-1]) else dn[i]
        else:up[i]=min(up[i],up[i-1]) if not np.isnan(up[i-1]) else up[i]
        if dv[i-1]==1:dv[i],sv[i]=(-1,up[i]) if cl[i]<dn[i] else (1,dn[i])
        else:dv[i],sv[i]=(1,dn[i]) if cl[i]>up[i] else (-1,up[i])
    return pd.Series(sv,index=c.index),pd.Series(dv,index=c.index)
def compute_vp(h,l,c,v,lb=20,nb=30,step=1):
    n=len(c);poc=np.full(n,np.nan);vah=np.full(n,np.nan);val_=np.full(n,np.nan);cv,hv,lv,vv=c.values,h.values,l.values,v.values;pp,pv_,pvl=np.nan,np.nan,np.nan
    for i in range(lb,n):
        if i>lb and abs(cv[i]-cv[i-1])/(cv[i-1]+1e-10)<0.001:poc[i]=pp;vah[i]=pv_;val_[i]=pvl;continue
        s=i-lb;hw,lw,vw=hv[s:i+1],lv[s:i+1],vv[s:i+1];plo,phi=lw.min(),hw.max()
        if phi-plo<1e-10:poc[i]=cv[i];vah[i]=phi;val_[i]=plo;pp=poc[i];pv_=vah[i];pvl=val_[i];continue
        tp_=(hw+lw+cv[s:i+1])/3;vp_,be=np.histogram(tp_,bins=nb,range=(plo,phi),weights=vw);bc=(be[:-1]+be[1:])/2;pb_=np.argmax(vp_);poc[i]=bc[pb_]
        tv=vp_.sum();tgt=tv*.7;cm=vp_[pb_];lo_i,hi_i=pb_,pb_
        while cm<tgt and (lo_i>0 or hi_i<nb-1):
            lv2=vp_[lo_i-1] if lo_i>0 else 0;hv2=vp_[hi_i+1] if hi_i<nb-1 else 0
            if lv2>=hv2 and lo_i>0:lo_i-=1;cm+=lv2
            elif hi_i<nb-1:hi_i+=1;cm+=hv2
            else:break
        vah[i]=be[min(hi_i+1,nb)];val_[i]=be[lo_i];pp=poc[i];pv_=vah[i];pvl=val_[i]
    return pd.Series(poc,index=c.index).ffill(),pd.Series(vah,index=c.index).ffill(),pd.Series(val_,index=c.index).ffill()
def detect_pivot_div(price,osc,lb=60,pw=5,os_lim=None,ob_lim=None,atr=None):
    n=len(price);pv=price.values.astype(float);ov=osc.values.astype(float);dl=np.full(n,lb,dtype=int)
    if atr is not None and len(atr)>0:ap=atr/(price+1e-10)*100;ar=ap/(ap.rolling(100,min_periods=20).median()+1e-10);ls__=np.clip(1.3-.35*ar.values,.5,1.5);dl=np.clip(lb*ls__,30,90).astype(int)
    pm=max(np.nanmean(np.nan_to_num((atr.rolling(20,min_periods=5).mean()*.3).values,nan=.01)),.01) if atr is not None else .01
    li,_=find_peaks(-pv,distance=pw,prominence=pm);hi,_=find_peaks(pv,distance=pw,prominence=pm)
    bd=np.zeros(n,dtype=bool);brd=np.zeros(n,dtype=bool);hb=np.zeros(n,dtype=bool);hbr=np.zeros(n,dtype=bool)
    for i in range(1,len(li)):
        ci,pi=li[i],li[i-1];gap=ci-pi
        if gap<pw*2 or gap>dl[ci]:continue
        if pv[ci]<pv[pi] and ov[ci]>ov[pi]:
            if os_lim is None or ov[ci]<=os_lim:bd[min(ci+pw,n-1)]=True
        if pv[ci]>pv[pi] and ov[ci]<ov[pi]:hb[min(ci+pw,n-1)]=True
    for i in range(1,len(hi)):
        ci,pi=hi[i],hi[i-1];gap=ci-pi
        if gap<pw*2 or gap>dl[ci]:continue
        if pv[ci]>pv[pi] and ov[ci]<ov[pi]:
            if ob_lim is None or ov[ci]>=ob_lim:brd[min(ci+pw,n-1)]=True
        if pv[ci]<pv[pi] and ov[ci]>ov[pi]:hbr[min(ci+pw,n-1)]=True
    return pd.Series(bd,index=price.index),pd.Series(brd,index=price.index),pd.Series(hb,index=price.index),pd.Series(hbr,index=price.index)
def compute_hull_ma(c,period=20):
    half_p=max(int(period/2),1);sqrt_p=max(int(np.sqrt(period)),1)
    def _wma(s,p):weights=np.arange(1,p+1,dtype=float);return s.rolling(p).apply(lambda x:np.dot(x,weights[-len(x):])/weights[-len(x):].sum(),raw=True)
    hma=_wma(2*_wma(c,half_p)-_wma(c,period),sqrt_p);rising=hma>hma.shift(1);return hma,rising,rising&~rising.shift(1).fillna(False),~rising&rising.shift(1).fillna(False)
def compute_ut_bot(c,h,l,atr,key_value=1):
    n=len(c);xatr=(atr*key_value).values;cv=c.values;ts_=np.zeros(n);dir_=np.zeros(n,dtype=int);ts_[0]=cv[0];dir_[0]=1
    for i in range(1,n):
        if np.isnan(xatr[i]) or np.isnan(cv[i]):ts_[i]=ts_[i-1];dir_[i]=dir_[i-1];continue
        if dir_[i-1]==1:ns=cv[i]-xatr[i];ts_[i]=max(ns,ts_[i-1]);dir_[i],ts_[i]=((-1,cv[i]+xatr[i]) if cv[i]<ts_[i] else (1,ts_[i]))
        else:ns=cv[i]+xatr[i];ts_[i]=min(ns,ts_[i-1]);dir_[i],ts_[i]=((1,cv[i]-xatr[i]) if cv[i]>ts_[i] else (-1,ts_[i]))
    ts_s=pd.Series(ts_,index=c.index);dir_s=pd.Series(dir_,index=c.index);return ts_s,dir_s,(dir_s==1)&(dir_s.shift(1)==-1),(dir_s==-1)&(dir_s.shift(1)==1)
def compute_stochastic_slow(h,l,c,k_period=14,smooth_k=3,d_period=3):ll=l.rolling(k_period).min();hh=h.rolling(k_period).max();fast_k=((c-ll)/(hh-ll+1e-10))*100;slow_k=fast_k.rolling(smooth_k).mean();return slow_k,slow_k.rolling(d_period).mean()
def compute_squeeze_mom_enh(c,h,l,bbu,bbl,kcu,kcl,kc_mid,period=20):sq=(bbu<kcu)&(bbl>kcl);mid_hl=(h.rolling(period).max()+l.rolling(period).min())/2;mom=c-(mid_hl+kc_mid)/2;ms_=mom.ewm(span=period,adjust=False).mean();return {'squeeze_on':sq,'momentum':ms_,'mom_rising':ms_>ms_.shift(1),'mom_positive':ms_>0,'mom_cross_up':(ms_>0)&(ms_.shift(1)<=0),'mom_cross_down':(ms_<0)&(ms_.shift(1)>=0)}
def compute_trendline_features(c,h,l,atr,window=20):
    idx=c.index;x=pd.Series(np.arange(len(c),dtype=float),index=idx)
    min_periods=max(10,window//2)
    x_mean=x.rolling(window,min_periods=min_periods).mean();y_mean=c.rolling(window,min_periods=min_periods).mean()
    cov=(x*c).rolling(window,min_periods=min_periods).mean()-x_mean*y_mean
    var=(x*x).rolling(window,min_periods=min_periods).mean()-(x_mean*x_mean)
    slope=cov/(var+1e-10);fit=(y_mean-(slope*x_mean))+(slope*x)
    slope_pct=(slope*window/(c.abs()+1e-10))*100
    dist_atr=(c-fit)/(atr+1e-10)
    valid=fit.notna()&atr.notna()
    support_hold=valid&(slope_pct>=JT.TRENDLINE_MIN_SLOPE_PCT)&(l<=fit+(atr*JT.TRENDLINE_TOUCH_ATR))&(c>=fit)&(c>=c.shift(1))
    resistance_reject=valid&(slope_pct<=-JT.TRENDLINE_MIN_SLOPE_PCT)&(h>=fit-(atr*JT.TRENDLINE_TOUCH_ATR))&(c<=fit)&(c<=c.shift(1))
    breakout_bull=valid&(slope_pct>=-0.15)&(dist_atr>=JT.TRENDLINE_BREAK_ATR)&(dist_atr.shift(1)<=0.25)
    breakdown_bear=valid&(slope_pct<=0.15)&(dist_atr<=-JT.TRENDLINE_BREAK_ATR)&(dist_atr.shift(1)>=-0.25)
    return {
        'slope_pct':slope_pct.fillna(0),
        'fit':fit,
        'dist_atr':dist_atr.fillna(0),
        'support_hold':support_hold.fillna(False),
        'resistance_reject':resistance_reject.fillna(False),
        'breakout_bull':breakout_bull.fillna(False),
        'breakdown_bear':breakdown_bear.fillna(False),
    }

def compute_indicators(df):
    o,c,h,l,v=df['Open'],df['Close'],df['High'],df['Low'],df['Volume']
    df['History_Bars']=pd.Series(np.arange(1,len(df)+1),index=df.index,dtype=float)
    df['Has_MA50_History']=df['History_Bars']>=JT.MIN_HISTORY_MA50
    df['Has_MA200_History']=df['History_Bars']>=JT.MIN_HISTORY_MA200
    df['Has_Long_History']=df['History_Bars']>=JT.MIN_HISTORY_LONG
    for ma in [5,10,20,50,200]:df[f'MA{ma}']=c.rolling(ma).mean()
    df['EMA8']=c.ewm(span=8,adjust=False).mean();df['EMA21']=c.ewm(span=21,adjust=False).mean()
    df['BB_Mid']=df['MA20'];s20=c.rolling(20).std();df['BB_Up'],df['BB_Low']=df['BB_Mid']+s20*2,df['BB_Mid']-s20*2
    df['BB_Width']=(df['BB_Up']-df['BB_Low'])/(df['BB_Mid']+1e-10);df['Percent_B']=(c-df['BB_Low'])/(df['BB_Up']-df['BB_Low']+1e-10)
    tr=compute_tr(h,l,c);df['ATR']=tr.rolling(14).mean();df['SuperTrend'],df['ST_Direction']=compute_supertrend(h,l,c,tr)
    ak=tr.rolling(10).mean();mk=c.ewm(span=20,adjust=False).mean();df['KC_Upper']=mk+ak*1.5;df['KC_Mid']=mk;df['KC_Lower']=mk-ak*1.5
    vol20=v.rolling(20,min_periods=5).mean();vol50=v.rolling(50,min_periods=10).mean()
    df['Volume_Ratio_20']=v/(vol20+1e-10);df['Volume_Ratio_50']=v/(vol50+1e-10)
    df['Dollar_Volume_20']=(c*v).rolling(20,min_periods=5).mean()
    w1,w2,wu,wd=compute_wavetrend(h,l,c);df['WT1'],df['WT2'],df['WT_Up'],df['WT_Down']=w1,w2,wu,wd
    df['RSI']=compute_rsi(c,14);df['StochK'],df['StochD']=compute_stoch_rsi(c);df['MFI']=compute_mfi(h,l,c,v,14).fillna(50)
    df['RSI_MFI']=compute_rsi_mfi(h,l,c,v,60);vw=(c*v).rolling(20).sum()/(v.rolling(20).sum()+1e-10);df['VWAP_Osc']=((c-vw)/(vw+1e-10))*100
    df['ADX'],df['Plus_DI'],df['Minus_DI']=compute_adx(h,l,c);df['OBV']=compute_obv(c,v)
    df['MACD_Line'],df['MACD_Signal'],df['MACD_Hist']=compute_macd(c)
    tk,kj,sa,sb=compute_ichimoku(h,l,c);df['Ichimoku_Tenkan']=tk;df['Ichimoku_Kijun']=kj;df['Ichimoku_SenkouA']=sa;df['Ichimoku_SenkouB']=sb
    df['CMF']=compute_cmf(h,l,c,v,20)
    df['OBV_Slope']=compute_obv_slope(df['OBV'],v,5);df['Price_Slope_5']=c.pct_change(5)
    df['Low_Volume_Caution']=df['Volume_Ratio_20']<0.7
    df['Thin_Trade_Risk']=(df['Dollar_Volume_20']<JT.MIN_DOLLAR_VOLUME_20).fillna(False)
    df['Smart_Money_Bearish_Div']=(df['Price_Slope_5']>0)&((df['OBV_Slope']<0)|(df['CMF']<0)|(df['Volume_Ratio_20']<0.7))
    df['Smart_Money_Bullish_Div']=(df['Price_Slope_5']<0)&((df['OBV_Slope']>0)|(df['CMF']>0))
    df['MA20_ATR_Gap']=(c-df['MA20'])/(df['ATR']+1e-10)
    df['Blowoff_Top_Hard']=(df['MA20_ATR_Gap']>=3)&(df['Volume_Ratio_20']>=2)&(c<o)&((c>df['BB_Up'])|(df['WT1']>60))
    df['Washout_Bottom_Hard']=(df['MA20_ATR_Gap']<=-3)&(df['Volume_Ratio_20']>=2)&(c>o)&((c<df['BB_Low'])|(df['WT1']<-60))
    tl=compute_trendline_features(c,h,l,df['ATR'],JT.TRENDLINE_WINDOW)
    df['Trendline_Slope_Pct']=tl['slope_pct'];df['Trendline_Fit']=tl['fit'];df['Trendline_Dist_ATR']=tl['dist_atr']
    df['Diag_Support_Hold']=tl['support_hold'];df['Diag_Resistance_Reject']=tl['resistance_reject']
    df['Diag_Breakout_Bull']=tl['breakout_bull'];df['Diag_Breakdown_Bear']=tl['breakdown_bear']
    rv=df['RSI']-df['RSI'].shift(3);df['RSI_Accel']=rv-rv.shift(3);wv=df['WT1']-df['WT1'].shift(3);df['WT_Accel']=wv-wv.shift(3);df['MACD_Accel']=df['MACD_Hist']-df['MACD_Hist'].shift(3)
    rn=df['RSI_Accel']/(df['RSI_Accel'].rolling(50,min_periods=10).std()+1e-10);wn=df['WT_Accel']/(df['WT_Accel'].rolling(50,min_periods=10).std()+1e-10);mn=df['MACD_Accel']/(df['MACD_Accel'].rolling(50,min_periods=10).std()+1e-10)
    df['Composite_Accel']=(rn+wn+mn)/3;wg=df['WT1']-df['WT2'];df['WT_Gap']=wg;df['WT_Gap_Abs']=wg.abs();df['WT_Conv_Speed']=df['WT_Gap_Abs'].shift(3)-df['WT_Gap_Abs']
    df['VP_POC'],df['VP_VAH'],df['VP_VAL']=compute_vp(h,l,c,v)
    risk_floor=(df['ATR'].fillna(c*0.01)*0.75).clip(lower=c*0.003)
    long_support=df['VP_POC'].where(df['VP_POC']<c,df['VP_VAL'])
    long_support=long_support.where(long_support<c,c-risk_floor)
    long_resist=df['VP_VAH'].where(df['VP_VAH']>c,df['VP_POC'])
    long_resist=long_resist.where(long_resist>c,c+risk_floor)
    short_support=df['VP_VAL'].where(df['VP_VAL']<c,df['VP_POC'])
    short_support=short_support.where(short_support<c,c-risk_floor)
    short_resist=df['VP_POC'].where(df['VP_POC']>c,df['VP_VAH'])
    short_resist=short_resist.where(short_resist>c,c+risk_floor)
    long_reward=(long_resist-c).clip(lower=0);long_risk=(c-long_support).where((c-long_support)>risk_floor,risk_floor)
    short_reward=(c-short_support).clip(lower=0);short_risk=(short_resist-c).where((short_resist-c)>risk_floor,risk_floor)
    df['VP_Long_RR']=long_reward/(long_risk+1e-10);df['VP_Short_RR']=short_reward/(short_risk+1e-10)
    df['Upside_Space_Score']=np.clip((df['VP_Long_RR']-1.0)*20,-20,12)
    df['RS_Ratio']=1.;df['SPY_Return']=0.;df['Stock_Return']=0.;df['SPY_Trend_Score']=0.;df['SPY_Drawdown_20']=0.;df['SPY_Risk_On']=False;df['SPY_Risk_Off']=False
    df['SPY_MA20']=0.;df['SPY_MA50']=0.;df['SPY_MA200']=0.;df['SPY_Close']=0.
    df['QQQ_RS_20']=0.;df['IWM_RS_20']=0.;df['RSP_RS_20']=0.;df['Market_Breadth_Score']=0.
    df['Breadth_Risk_On']=False;df['Breadth_Risk_Off']=False;df['Narrow_Leadership']=False
    df['VIX_Trend_10']=0.;df['VIX_Risk_On']=False;df['VIX_Risk_Off']=False
    df['TNX_Delta_20']=0.;df['TNX_Headwind']=False;df['TNX_Tailwind']=False
    df['DXY_Return_20']=0.;df['DXY_Headwind']=False;df['DXY_Tailwind']=False
    df['VIX_Pressure_Score']=0.;df['TNX_Pressure_Score']=0.;df['DXY_Pressure_Score']=0.;df['Macro_Pressure_Score']=0.
    df['Trend_Inflection_Buy_Score']=0.;df['Trend_Inflection_Sell_Score']=0.
    df['Trend_Inflection_Bull']=False;df['Trend_Inflection_Bear']=False
    df['Market_Turn_Bull_Score']=0.;df['Market_Turn_Bear_Score']=0.
    df['Market_Turn_Bull']=False;df['Market_Turn_Bear']=False
    try:
        spy=fetch_spy()
        if not spy.empty:
            sc_=c.copy();spc=spy['Close'].reindex(sc_.index,method='ffill');sr=sc_.pct_change(20).fillna(0);spr=spc.pct_change(20).fillna(0);df['Stock_Return']=sr;df['SPY_Return']=spr;df['RS_Ratio']=((1+sr)/(1+spr+1e-10)).rolling(10,min_periods=5).mean()
            spy_ma20=spc.rolling(20,min_periods=10).mean();spy_ma50=spc.rolling(50,min_periods=20).mean();spy_ma200=spc.rolling(200,min_periods=80).mean()
            spy_ma20_ready=spy_ma20.notna();spy_ma50_ready=spy_ma50.notna();spy_ma200_ready=spy_ma200.notna()
            spy_dd20=(spc/(spc.rolling(20,min_periods=5).max()+1e-10))-1.0
            spy_score=pd.Series(0.,index=sc_.index)
            spy_score+=np.where(spy_ma20_ready&(spc>spy_ma20),1,np.where(spy_ma20_ready&(spc<spy_ma20),-1,0))
            spy_score+=np.where(spy_ma50_ready&(spc>spy_ma50),1,np.where(spy_ma50_ready&(spc<spy_ma50),-1,0))
            spy_score+=np.where(spy_ma200_ready&(spc>spy_ma200),1,np.where(spy_ma200_ready&(spc<spy_ma200),-1,0))
            spy_score+=np.where(spy_ma20_ready&spy_ma50_ready&(spy_ma20>spy_ma50),1,np.where(spy_ma20_ready&spy_ma50_ready&(spy_ma20<spy_ma50),-1,0))
            spy_score+=np.where(spy_ma50_ready&spy_ma200_ready&(spy_ma50>spy_ma200),1,np.where(spy_ma50_ready&spy_ma200_ready&(spy_ma50<spy_ma200),-1,0))
            spy_score+=np.where(spr>0,1,np.where(spr<0,-1,0))
            df['SPY_Close']=spc;df['SPY_MA20']=spy_ma20;df['SPY_MA50']=spy_ma50;df['SPY_MA200']=spy_ma200;df['SPY_Drawdown_20']=spy_dd20.fillna(0);df['SPY_Trend_Score']=spy_score
            df['SPY_Risk_On']=(spy_score>=JT.MARKET_SCORE_TREND_ON)&spy_ma50_ready&spy_ma200_ready&(spc>spy_ma50)&(spy_ma50>spy_ma200)&(spr>=0)
            df['SPY_Risk_Off']=(spy_score<=JT.MARKET_SCORE_TREND_OFF)&spy_ma50_ready&spy_ma200_ready&(spc<spy_ma50)&(spy_ma50<spy_ma200)&(spy_dd20<=-0.04)
            qqq=fetch_market_proxy("QQQ")
            iwm=fetch_market_proxy("IWM")
            rsp=fetch_market_proxy("RSP")
            breadth_score=pd.Series(0.,index=sc_.index)
            if not qqq.empty:
                qqqc=qqq['Close'].reindex(sc_.index,method='ffill');qqq_ret20=qqqc.pct_change(20).fillna(0);qqq_rs20=qqq_ret20-spr
                df['QQQ_RS_20']=qqq_rs20
                breadth_score+=np.where(qqq_rs20>=JT.BREADTH_RS_POS,0.5,np.where(qqq_rs20<=JT.BREADTH_RS_NEG,-0.5,0))
            if not iwm.empty:
                iwmc=iwm['Close'].reindex(sc_.index,method='ffill');iwm_ret20=iwmc.pct_change(20).fillna(0);iwm_rs20=iwm_ret20-spr
                df['IWM_RS_20']=iwm_rs20
                breadth_score+=np.where(iwm_rs20>=JT.BREADTH_RS_POS,1.0,np.where(iwm_rs20<=JT.BREADTH_RS_NEG,-1.0,0))
            if not rsp.empty:
                rspc=rsp['Close'].reindex(sc_.index,method='ffill');rsp_ret20=rspc.pct_change(20).fillna(0);rsp_rs20=rsp_ret20-spr
                df['RSP_RS_20']=rsp_rs20
                breadth_score+=np.where(rsp_rs20>=JT.BREADTH_RS_POS,1.0,np.where(rsp_rs20<=JT.BREADTH_RS_NEG,-1.0,0))
            df['Market_Breadth_Score']=breadth_score
            df['Breadth_Risk_On']=(breadth_score>=1.5).fillna(False)
            df['Breadth_Risk_Off']=(breadth_score<=-1.5).fillna(False)
            df['Narrow_Leadership']=(
                (df['QQQ_RS_20']>=JT.NARROW_LEADERSHIP_GAP)
                & ((df['IWM_RS_20']<=JT.BREADTH_RS_NEG)|(df['RSP_RS_20']<=JT.BREADTH_RS_NEG))
            ).fillna(False)
        vix=fetch_market_proxy("^VIX")
        if not vix.empty:
            vixc=vix['Close'].reindex(c.index,method='ffill');vix_ma20=vixc.rolling(20,min_periods=10).mean();vix_ret10=vixc.pct_change(10).fillna(0)
            df['VIX_Trend_10']=vix_ret10
            df['VIX_Risk_Off']=((vixc>(vix_ma20*JT.VIX_RISK_OFF_RATIO))|(vix_ret10>=JT.VIX_RISK_OFF_PCT10)).fillna(False)
            df['VIX_Risk_On']=((vixc<(vix_ma20*JT.VIX_RISK_ON_RATIO))&(vix_ret10<=JT.VIX_RISK_ON_PCT10)).fillna(False)
            vix_dist=((vixc/(vix_ma20+1e-10))-1.0).fillna(0)
            df['VIX_Pressure_Score']=np.clip(vix_dist*12+vix_ret10*10,-3.5,3.5)
        tnx=fetch_market_proxy("^TNX")
        if not tnx.empty:
            tnxc=tnx['Close'].reindex(c.index,method='ffill');tnx_delta20=tnxc.diff(20).fillna(0)
            df['TNX_Delta_20']=tnx_delta20
            df['TNX_Headwind']=((tnx_delta20>=JT.TNX_HEADWIND_DELTA20)&(tnxc>tnxc.rolling(50,min_periods=20).mean())).fillna(False)
            df['TNX_Tailwind']=(tnx_delta20<=JT.TNX_TAILWIND_DELTA20).fillna(False)
            tnx_ma50=tnxc.rolling(50,min_periods=20).mean()
            tnx_dist=((tnxc/(tnx_ma50+1e-10))-1.0).fillna(0)
            df['TNX_Pressure_Score']=np.clip((tnx_delta20/(abs(JT.TNX_HEADWIND_DELTA20)+1e-10))*1.4+tnx_dist*6,-3,3)
        dxy=fetch_market_proxy("DX-Y.NYB")
        if not dxy.empty:
            dxyc=dxy['Close'].reindex(c.index,method='ffill');dxy_ret20=dxyc.pct_change(20).fillna(0)
            df['DXY_Return_20']=dxy_ret20
            df['DXY_Headwind']=(dxy_ret20>=JT.DXY_HEADWIND_PCT20).fillna(False)
            df['DXY_Tailwind']=(dxy_ret20<=JT.DXY_TAILWIND_PCT20).fillna(False)
            df['DXY_Pressure_Score']=np.clip((dxy_ret20/(abs(JT.DXY_HEADWIND_PCT20)+1e-10))*1.25,-3,3)
    except:
        pass
    df['Macro_Pressure_Score']=np.clip(
        df['VIX_Pressure_Score']
        +(df['TNX_Pressure_Score']*0.8)
        +(df['DXY_Pressure_Score']*0.8)
        -(df['Market_Breadth_Score']*0.6),
        -6,6
    )
    rsc=pd.Series(0.,index=df.index);rsc+=np.where(c>df['MA200'],1,-1);rsc+=np.where(c>df['MA50'],1,-1);rsc+=np.where(c>df['MA20'],.5,-.5)
    rsc+=np.where(df['MA50']>df['MA50'].shift(10),1,-1);rsc+=np.where(df['ST_Direction']==1,1,-1);rsc+=np.where(df['Plus_DI']>df['Minus_DI'],.5,-.5);rsc+=np.where(df['MACD_Line']>0,.5,-.5)
    rr_=rsc.rolling(5,min_periods=3).mean();df['Regime_Score']=rr_.clip(-8,8);df['Regime']=np.select([rr_>=4,rr_>=1.5,rr_<=-4,rr_<=-1.5],[2,1,-2,-1],default=0)
    df['HMA'],df['HMA_Rising'],df['Hull_Turn_Bull_Raw'],df['Hull_Turn_Bear_Raw']=compute_hull_ma(c,20)
    df['UTBot_Stop'],df['UTBot_Dir'],df['UTBot_Buy_Raw'],df['UTBot_Sell_Raw']=compute_ut_bot(c,h,l,df['ATR'],1)
    df['SlowK'],df['SlowD']=compute_stochastic_slow(h,l,c)
    sqe=compute_squeeze_mom_enh(c,h,l,df['BB_Up'],df['BB_Low'],df['KC_Upper'],df['KC_Lower'],df['KC_Mid'])
    df['Squeeze_On']=sqe['squeeze_on'];df['Squeeze_Momentum']=sqe['momentum'];df['Squeeze_Mom_Rising']=sqe['mom_rising'];df['Squeeze_Mom_Positive']=sqe['mom_positive']
    df['Squeeze_Mom_Cross_Up_Raw']=sqe['mom_cross_up'];df['Squeeze_Mom_Cross_Down_Raw']=sqe['mom_cross_down']

    ma20_slope=(df['MA20']-df['MA20'].shift(3))/(df['ATR']+1e-10)
    ma20_turn_up=(ma20_slope>0)&(ma20_slope>ma20_slope.shift(1))
    ma20_turn_down=(ma20_slope<0)&(ma20_slope<ma20_slope.shift(1))
    reclaim_ma20=(c>df['MA20'])&(c.shift(1)<=df['MA20'].shift(1))
    lose_ma20=(c<df['MA20'])&(c.shift(1)>=df['MA20'].shift(1))
    macd_inflect_bull=(df['MACD_Hist']<0)&(df['MACD_Hist']>df['MACD_Hist'].shift(1))&(df['MACD_Accel']>0)
    macd_inflect_bear=(df['MACD_Hist']>0)&(df['MACD_Hist']<df['MACD_Hist'].shift(1))&(df['MACD_Accel']<0)
    wt_inflect_bull=(df['WT1']>df['WT1'].shift(1))&(df['WT_Conv_Speed']>0)&(df['WT1']<20)
    wt_inflect_bear=(df['WT1']<df['WT1'].shift(1))&(df['WT_Conv_Speed']>0)&(df['WT1']>-20)
    money_turn_up=(df['MFI']>df['MFI'].shift(1))&(df['CMF']>=df['CMF'].shift(1))
    money_turn_down=(df['MFI']<df['MFI'].shift(1))&(df['CMF']<=df['CMF'].shift(1))
    bull_inflect_score=(
        reclaim_ma20.astype(int)
        +macd_inflect_bull.astype(int)
        +wt_inflect_bull.astype(int)
        +df['Hull_Turn_Bull_Raw'].fillna(False).astype(int)
        +df['UTBot_Buy_Raw'].fillna(False).astype(int)
        +ma20_turn_up.astype(int)
        +(df['Diag_Support_Hold']|df['Diag_Breakout_Bull']).astype(int)
        +money_turn_up.astype(int)
    )
    bear_inflect_score=(
        lose_ma20.astype(int)
        +macd_inflect_bear.astype(int)
        +wt_inflect_bear.astype(int)
        +df['Hull_Turn_Bear_Raw'].fillna(False).astype(int)
        +df['UTBot_Sell_Raw'].fillna(False).astype(int)
        +ma20_turn_down.astype(int)
        +(df['Diag_Resistance_Reject']|df['Diag_Breakdown_Bear']).astype(int)
        +money_turn_down.astype(int)
    )
    df['Trend_Inflection_Buy_Score']=bull_inflect_score
    df['Trend_Inflection_Sell_Score']=bear_inflect_score
    df['Trend_Inflection_Bull']=(bull_inflect_score>=JT.TREND_INFLECTION_STRONG).fillna(False)
    df['Trend_Inflection_Bear']=(bear_inflect_score>=JT.TREND_INFLECTION_STRONG).fillna(False)

    spy_score_delta=df['SPY_Trend_Score']-df['SPY_Trend_Score'].shift(3)
    breadth_delta=df['Market_Breadth_Score']-df['Market_Breadth_Score'].shift(3)
    spy_reclaim_ma20=(df['SPY_Close']>df['SPY_MA20'])&(df['SPY_Close'].shift(1)<=df['SPY_MA20'].shift(1))
    spy_lose_ma20=(df['SPY_Close']<df['SPY_MA20'])&(df['SPY_Close'].shift(1)>=df['SPY_MA20'].shift(1))
    vix_easing=(df['VIX_Pressure_Score']<=-0.8)|df['VIX_Risk_On']
    vix_worsening=(df['VIX_Pressure_Score']>=0.8)|df['VIX_Risk_Off']
    macro_easing=df['Macro_Pressure_Score']<=-1.2
    macro_worsening=df['Macro_Pressure_Score']>=1.2
    bull_market_turn_score=(
        (spy_score_delta>=2).astype(int)
        +spy_reclaim_ma20.fillna(False).astype(int)
        +(breadth_delta>=0.8).astype(int)
        +(df['Market_Breadth_Score']>0.5).astype(int)
        +df['Breadth_Risk_On'].astype(int)
        +vix_easing.astype(int)
        +macro_easing.astype(int)
    )
    bear_market_turn_score=(
        (spy_score_delta<=-2).astype(int)
        +spy_lose_ma20.fillna(False).astype(int)
        +(breadth_delta<=-0.8).astype(int)
        +(df['Market_Breadth_Score']<-0.5).astype(int)
        +df['Breadth_Risk_Off'].astype(int)
        +vix_worsening.astype(int)
        +macro_worsening.astype(int)
    )
    df['Market_Turn_Bull_Score']=bull_market_turn_score
    df['Market_Turn_Bear_Score']=bear_market_turn_score
    df['Market_Turn_Bull']=((bull_market_turn_score>=JT.MARKET_TURN_STRONG)&(bull_market_turn_score>bear_market_turn_score)).fillna(False)
    df['Market_Turn_Bear']=((bear_market_turn_score>=JT.MARKET_TURN_STRONG)&(bear_market_turn_score>bull_market_turn_score)).fillna(False)
    return df
