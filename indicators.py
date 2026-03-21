import pandas as pd
import numpy as np
from scipy.signal import find_peaks
from utils import fetch_spy

def compute_rsi(s,p=14):d=s.diff();g,l_=d.clip(lower=0),-d.clip(upper=0);return 100-(100/(1+g.ewm(alpha=1/p,min_periods=p).mean()/(l_.ewm(alpha=1/p,min_periods=p).mean()+1e-10)))
def compute_mfi(h,l,c,v,p=14):tp=(h+l+c)/3;r=tp*v;d=tp.diff();return 100-(100/(1+r.where(d>=0,0.).rolling(p).sum()/(r.where(d<0,0.).rolling(p).sum()+1e-10)))
def compute_rsi_mfi(h,l,c,v,p=60):rf,mf=compute_rsi(c,20),compute_mfi(h,l,c,v,20);rs,ms=compute_rsi(c,p),compute_mfi(h,l,c,v,p);return (((rf-50)+(mf-50))/2)*.6+(((rs-50)+(ms-50))/2)*.4
def compute_wavetrend(h,l,c,ch=9,avg=12,ma=3):ap=(h+l+c)/3;esa=ap.ewm(span=ch,adjust=False).mean();d=abs(ap-esa).ewm(span=ch,adjust=False).mean();ci=(ap-esa)/(0.015*d+1e-10);w1=ci.ewm(span=avg,adjust=False).mean();w2=w1.rolling(ma).mean();return w1,w2,(w1>w2)&(w1.shift(1)<=w2.shift(1)),(w1<w2)&(w1.shift(1)>=w2.shift(1))
def compute_stoch_rsi(c,rl=14,sl=14,ks=3,ds=3):r=compute_rsi(c,rl);mn,mx=r.rolling(sl).min(),r.rolling(sl).max();k=(((r-mn)/(mx-mn+1e-10))*100).rolling(ks).mean();return k,k.rolling(ds).mean()
def compute_tr(h,l,c):pc=c.shift(1);return pd.concat([h-l,(h-pc).abs(),(l-pc).abs()],axis=1).max(axis=1)
def compute_adx(h,l,c,p=14):tr=compute_tr(h,l,c);ph,pl=h.shift(1),l.shift(1);plus_dm=pd.Series(np.where((h-ph)>(pl-l),np.maximum(h-ph,0),0),index=h.index,dtype=float);minus_dm=pd.Series(np.where((pl-l)>(h-ph),np.maximum(pl-l,0),0),index=h.index,dtype=float);a=tr.ewm(alpha=1/p,min_periods=p).mean();pdi=100*plus_dm.ewm(alpha=1/p,min_periods=p).mean()/(a+1e-10);mdi=100*minus_dm.ewm(alpha=1/p,min_periods=p).mean()/(a+1e-10);dx=100*(pdi-mdi).abs()/(pdi+mdi+1e-10);return dx.ewm(alpha=1/p,min_periods=p).mean(),pdi,mdi
def compute_obv(c,v):return (v*np.sign(c.diff()).fillna(0)).cumsum()
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

def compute_indicators(df):
    c,h,l,v=df['Close'],df['High'],df['Low'],df['Volume']
    for ma in [5,10,20,50,200]:df[f'MA{ma}']=c.rolling(ma).mean()
    df['EMA8']=c.ewm(span=8,adjust=False).mean();df['EMA21']=c.ewm(span=21,adjust=False).mean()
    df['BB_Mid']=df['MA20'];s20=c.rolling(20).std();df['BB_Up'],df['BB_Low']=df['BB_Mid']+s20*2,df['BB_Mid']-s20*2
    df['BB_Width']=(df['BB_Up']-df['BB_Low'])/(df['BB_Mid']+1e-10);df['Percent_B']=(c-df['BB_Low'])/(df['BB_Up']-df['BB_Low']+1e-10)
    tr=compute_tr(h,l,c);df['ATR']=tr.rolling(14).mean();df['SuperTrend'],df['ST_Direction']=compute_supertrend(h,l,c,tr)
    ak=tr.rolling(10).mean();mk=c.ewm(span=20,adjust=False).mean();df['KC_Upper']=mk+ak*1.5;df['KC_Mid']=mk;df['KC_Lower']=mk-ak*1.5
    w1,w2,wu,wd=compute_wavetrend(h,l,c);df['WT1'],df['WT2'],df['WT_Up'],df['WT_Down']=w1,w2,wu,wd
    df['RSI']=compute_rsi(c,14);df['StochK'],df['StochD']=compute_stoch_rsi(c);df['MFI']=compute_mfi(h,l,c,v,14).fillna(50)
    df['RSI_MFI']=compute_rsi_mfi(h,l,c,v,60);vw=(c*v).rolling(20).sum()/(v.rolling(20).sum()+1e-10);df['VWAP_Osc']=((c-vw)/(vw+1e-10))*100
    df['ADX'],df['Plus_DI'],df['Minus_DI']=compute_adx(h,l,c);df['OBV']=compute_obv(c,v)
    df['MACD_Line'],df['MACD_Signal'],df['MACD_Hist']=compute_macd(c)
    tk,kj,sa,sb=compute_ichimoku(h,l,c);df['Ichimoku_Tenkan']=tk;df['Ichimoku_Kijun']=kj;df['Ichimoku_SenkouA']=sa;df['Ichimoku_SenkouB']=sb
    df['CMF']=compute_cmf(h,l,c,v,20)
    rv=df['RSI']-df['RSI'].shift(3);df['RSI_Accel']=rv-rv.shift(3);wv=df['WT1']-df['WT1'].shift(3);df['WT_Accel']=wv-wv.shift(3);df['MACD_Accel']=df['MACD_Hist']-df['MACD_Hist'].shift(3)
    rn=df['RSI_Accel']/(df['RSI_Accel'].rolling(50,min_periods=10).std()+1e-10);wn=df['WT_Accel']/(df['WT_Accel'].rolling(50,min_periods=10).std()+1e-10);mn=df['MACD_Accel']/(df['MACD_Accel'].rolling(50,min_periods=10).std()+1e-10)
    df['Composite_Accel']=(rn+wn+mn)/3;wg=df['WT1']-df['WT2'];df['WT_Gap']=wg;df['WT_Gap_Abs']=wg.abs();df['WT_Conv_Speed']=df['WT_Gap_Abs'].shift(3)-df['WT_Gap_Abs']
    df['VP_POC'],df['VP_VAH'],df['VP_VAL']=compute_vp(h,l,c,v)
    try:
        spy=fetch_spy()
        if not spy.empty:sc_=c.copy();spc=spy['Close'].reindex(sc_.index,method='ffill');sr=sc_.pct_change(20).fillna(0);spr=spc.pct_change(20).fillna(0);df['Stock_Return']=sr;df['SPY_Return']=spr;df['RS_Ratio']=((1+sr)/(1+spr+1e-10)).rolling(10,min_periods=5).mean()
    except:df['RS_Ratio']=1.;df['SPY_Return']=0.;df['Stock_Return']=0.
    rsc=pd.Series(0.,index=df.index);rsc+=np.where(c>df['MA200'],1,-1);rsc+=np.where(c>df['MA50'],1,-1);rsc+=np.where(c>df['MA20'],.5,-.5)
    rsc+=np.where(df['MA50']>df['MA50'].shift(10),1,-1);rsc+=np.where(df['ST_Direction']==1,1,-1);rsc+=np.where(df['Plus_DI']>df['Minus_DI'],.5,-.5);rsc+=np.where(df['MACD_Line']>0,.5,-.5)
    rr_=rsc.rolling(5,min_periods=3).mean();df['Regime_Score']=rr_.clip(-8,8);df['Regime']=np.select([rr_>=4,rr_>=1.5,rr_<=-4,rr_<=-1.5],[2,1,-2,-1],default=0)
    df['HMA'],df['HMA_Rising'],df['Hull_Turn_Bull_Raw'],df['Hull_Turn_Bear_Raw']=compute_hull_ma(c,20)
    df['UTBot_Stop'],df['UTBot_Dir'],df['UTBot_Buy_Raw'],df['UTBot_Sell_Raw']=compute_ut_bot(c,h,l,df['ATR'],1)
    df['SlowK'],df['SlowD']=compute_stochastic_slow(h,l,c)
    sqe=compute_squeeze_mom_enh(c,h,l,df['BB_Up'],df['BB_Low'],df['KC_Upper'],df['KC_Lower'],df['KC_Mid'])
    df['Squeeze_On']=sqe['squeeze_on'];df['Squeeze_Momentum']=sqe['momentum'];df['Squeeze_Mom_Rising']=sqe['mom_rising'];df['Squeeze_Mom_Positive']=sqe['mom_positive']
    df['Squeeze_Mom_Cross_Up_Raw']=sqe['mom_cross_up'];df['Squeeze_Mom_Cross_Down_Raw']=sqe['mom_cross_down']
    return df
