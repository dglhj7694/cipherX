import streamlit as st
import google.generativeai as genai
import time
import random
import re
from datetime import datetime
from st_copy_to_clipboard import st_copy_to_clipboard
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from plotly.subplots import make_subplots
from collections import OrderedDict
from company_details import render_company_details

st.set_page_config(
    page_title="CipherX V13.0 - Regime Engine",
    page_icon="🎯",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
html,body,[class*="css"]{font-family:'Pretendard','Noto Sans KR',sans-serif!important}
span[class*="material-symbols"],span[class*="material-icons"],
i[class*="material-icons"],.stIcon,[data-testid="stIconMaterial"]{
    font-family:'Material Symbols Rounded','Material Icons',sans-serif!important}
.stApp{background-color:#0E1117}
p,div[data-testid="stMarkdownContainer"] p,div[data-testid="stChatMessageContent"] p,
h1,h2,h3,h4,h5,h6,li{color:#FAFAFA!important}
div[data-testid="stCodeBlock"],pre,code{background-color:#1A1D24!important;color:#FAFAFA!important}
div[data-testid="stCodeBlock"] span{text-shadow:none!important}
div[data-testid="stCodeBlock"] span[style*="color: rgb(0, 0, 0)"],
div[data-testid="stCodeBlock"] span[style*="color: black"],
div[data-testid="stCodeBlock"] code>span:not([class]){color:#FAFAFA!important}
div[data-testid="stChatMessage"]:nth-child(even){background-color:#161A22;border-radius:12px;padding:5px 15px}
.block-container{padding-top:1rem!important;max-width:950px}
@media (max-width: 768px){
    .block-container{padding-left:.5rem!important;padding-right:.5rem!important}
    .price-big{font-size:1.6rem!important}
    div[data-testid="stPlotlyChart"]{margin-left:-10px!important;margin-right:-10px!important}
}
div.stButton>button[kind="primary"]{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%)!important;
color:white!important;border:none!important;border-radius:12px!important;padding:.6rem 1.5rem!important;
font-weight:600!important;font-size:1rem!important;transition:all .3s ease!important;width:100%}
div.stButton>button[kind="primary"]:hover{transform:translateY(-2px);box-shadow:0 8px 20px rgba(118,75,162,.4)!important}
div.stButton>button[kind="secondary"]{background-color:#1E2127!important;color:#E2E8F0!important;
border:1px solid #333842!important;border-radius:12px!important;font-weight:500!important;
transition:all .2s ease!important;width:100%}
div.stButton>button[kind="secondary"]:hover{border-color:#667eea!important;color:#667eea!important}
.streamlit-expanderHeader{background-color:#161A22!important;border-radius:10px!important;font-weight:600!important}
.streamlit-expanderHeader p{color:#414df2!important}
div[data-testid="stExpander"]{border:1px solid #2D333B!important;border-radius:10px!important;background-color:#161A22}
header{background-color:transparent!important}
div[data-testid="collapsedControl"]{display:flex!important;z-index:999999!important}
section[data-testid="stSidebar"]{background-color:#0A0D12;border-right:1px solid #1E2127}
section[data-testid="stSidebar"] .stMarkdown p{color:#AAA!important}
section[data-testid="stSidebar"] [data-testid="stSidebarCollapsedControl"]{
    background:rgba(14,17,23,0.9)!important;border:1px solid #2D333B!important;border-radius:8px!important}
@media (max-width: 768px){
    section[data-testid="stSidebar"]{z-index:999!important}
    .sidebar-toggle-btn{position:fixed;top:10px;left:10px;z-index:1000;
        background:rgba(22,26,34,0.95);border:1px solid #2D333B;border-radius:8px;
        padding:6px 12px;cursor:pointer;color:#FAFAFA;font-size:1.2rem}
}
div[data-testid="stExpanderDetails"] h1{font-size:1.5rem!important;margin-bottom:.5rem!important;padding-bottom:.3rem!important;border-bottom:1px solid #2D333B}
div[data-testid="stExpanderDetails"] h2{font-size:1.3rem!important;margin-top:1.2rem!important;margin-bottom:.5rem!important}
div[data-testid="stExpanderDetails"] h3{font-size:1.15rem!important;margin-top:1.2rem!important;margin-bottom:.4rem!important;color:#82aaff!important}
div[data-testid="stExpanderDetails"] p,div[data-testid="stExpanderDetails"] li{font-size:.95rem!important;line-height:1.6!important;color:#D0D7DE!important;margin-bottom:.5rem!important}
div[data-testid="stExpanderDetails"] blockquote{font-size:.95rem!important;border-left-color:#667eea!important;color:#A0B2C6!important}
div[data-testid="stExpanderDetails"] table{font-size:.85rem!important;width:100%!important}
div[data-testid="stExpanderDetails"] th,div[data-testid="stExpanderDetails"] td{padding:.4rem .6rem!important}
.signal-card{border-radius:12px;padding:16px 20px;margin:6px 0;border:1px solid #2D333B}
.signal-card-buy{background:linear-gradient(135deg,rgba(0,230,118,.08),rgba(0,191,255,.05));border-left:4px solid #00E676}
.signal-card-sell{background:linear-gradient(135deg,rgba(255,23,68,.08),rgba(255,82,82,.05));border-left:4px solid #FF1744}
.signal-card-neutral{background:linear-gradient(135deg,rgba(255,193,7,.08),rgba(255,152,0,.05));border-left:4px solid #FFC107}
.price-header{background:linear-gradient(135deg,#161A22,#1A1F2E);border:1px solid #2D333B;border-radius:14px;padding:18px 24px;margin-bottom:16px}
.price-big{font-size:2rem;font-weight:700;margin:0}
.price-change-up{color:#00E676!important}.price-change-down{color:#FF1744!important}
.price-label{color:#666!important;font-size:.8rem;margin:0}
.indicator-mini{display:inline-block;padding:4px 10px;margin:2px;border-radius:6px;font-size:.78rem;font-weight:500}
.ind-bullish{background:rgba(0,230,118,.15);color:#00E676}
.ind-bearish{background:rgba(255,23,68,.15);color:#FF1744}
.ind-neutral{background:rgba(255,193,7,.15);color:#FFC107}
div[data-testid="stTabs"] button{color:#AAA!important;font-weight:600!important}
div[data-testid="stTabs"] button[aria-selected="true"]{color:#667eea!important;border-bottom-color:#667eea!important}
</style>""", unsafe_allow_html=True)

# ──────────────────────────────────────────
# 🎯 [V13.0 에디션] 11 Master Signals + ⚡ 액션 시그널
# ──────────────────────────────────────────
_B, _S, _N = 'buy', 'sell', 'neutral'
def _sig(w,d,icon,label,sym,sz,clr,base,atr_m,kor,desc):
    return {'w':w,'dir':d,'icon':icon,'label':label,'sym':sym,'sz':sz,'clr':clr,
            'base':base,'atr_m':atr_m,'kor':kor,'desc':desc}

SIGNAL_REGISTRY = {
    'Cat_Basing':             _sig(1.0, _N, '📦', 'Basing', 'square', 10, '#9E9E9E', 'Low', -1.0, '기지 구축(횡보)', '변동성이 극도로 축소되며 돌파 에너지를 모으는 중'),
    'Cat_Trending':           _sig(1.5, _B, '🌊', 'Trending', 'star', 12, '#AA00FF', 'High', 2.0, '추세 진행', '강력한 방향성을 띠며 추세가 지속되는 상태'),
    'Cat_Bullish':            _sig(1.0, _B, '🟢', 'Bullish', 'triangle-up', 12, '#00E676', 'Low', -1.2, '강세장 진입', '장단기 이평선 정배열 및 보조지표 강세 전환'),
    'Cat_Bearish':            _sig(1.0, _S, '🔴', 'Bearish', 'triangle-down', 12, '#FF1744', 'High', 1.2, '약세장 진입', '이평선 역배열 및 보조지표 약세 전환'),
    'Cat_Overbought':         _sig(1.5, _S, '🔥', 'Overbought', 'diamond-open', 14, '#FF5252', 'High', 1.5, '과매수 (단기상투)', '지표 극단적 고점 (횡보/하락장에서 유효)'),
    'Cat_Oversold':           _sig(1.5, _B, '🧊', 'Oversold', 'diamond-open', 14, '#00BFFF', 'Low', -1.5, '과매도 (단기바닥)', '지표 극단적 저점 (횡보/상승장에서 유효)'),
    'Cat_Pos_Breakout':       _sig(2.5, _B, '🚀', 'Pos Breakout', 'star-diamond', 16, '#FFD700', 'Low', -2.5, '돌파 예상', '횡보/저항을 뚫고 상방으로 폭발'),
    'Cat_Pos_Breakdown':      _sig(2.5, _S, '💣', 'Pos Breakdown', 'star-diamond', 16, '#D50000', 'High', 2.5, '붕괴 예상', '지지선을 깨고 하방으로 투매 시작'),
    'Cat_Pos_Reversal_Bull':  _sig(2.0, _B, '🔄', 'Reversal(Bull)', 'hexagon', 15, '#E040FB', 'Low', -2.0, '상승 반전', '하락세 끝, 대량 거래량 반전'),
    'Cat_Pos_Reversal_Bear':  _sig(2.0, _S, '🔄', 'Reversal(Bear)', 'hexagon', 15, '#E040FB', 'High', 2.0, '하락 반전', '상승세 끝, 대량 거래량 상투'),
    'Cat_Swing_Setup_Bull':   _sig(2.0, _B, '🎯', 'Swing(Bull)', 'cross', 14, '#00E5FF', 'Low', -1.8, '스윙 매수 타점', '상승장 중 완벽한 눌림목'),
    'Cat_Swing_Setup_Bear':   _sig(2.0, _S, '🎯', 'Swing(Bear)', 'cross', 14, '#FF9800', 'High', 1.8, '스윙 매도 타점', '하락장 중 기술적 반등 상투'),
    'Cat_SMC_Bull':           _sig(2.5, _B, '🏦', 'SmartMoney(Bull)', 'star-square', 16, '#00BFA5', 'Low', -2.5, '스마트머니 매수', '개미털기 스윕 방어 후 반등'),
    'Cat_SMC_Bear':           _sig(2.5, _S, '🏦', 'SmartMoney(Bear)', 'star-square', 16, '#FF6E40', 'High', 2.5, '스마트머니 매도', '고점 휩쏘 후 하락'),
}

COMPOSITE_SIGNALS = {
    'Ultra_Buy':  _sig(0,_B,'⚡','ULTRA BUY','star',24,'#FFD700','Low',-3.8,'적극 매수','복수 시그널의 완벽한 합류 (초강력 타점)'),
    'Strong_Buy': _sig(0,_B,'🔱','STRONG BUY','star',18,'#00E676','Low',-3.5,'매수','복수 시그널의 합류 (안정적 타점)'),
    'Ultra_Sell': _sig(0,_S,'🚨','ULTRA SELL','star',24,'#FF0000','High',3.8,'적극 매도','복수 시그널의 완벽한 합류 (초강력 타점)'),
    'Strong_Sell':_sig(0,_S,'⚠️','STRONG SELL','star',18,'#FF1744','High',3.5,'매도','복수 시그널의 합류 (안정적 타점)'),
}
ALL_CHART_SIGNALS = {**SIGNAL_REGISTRY, **COMPOSITE_SIGNALS}
NEUTRAL_SIGNALS = {'Cat_Basing'}

OB1, OB2, OS1, OS2 = 53, 60, -53, -60

GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GEMINI_API_KEY)

COOLDOWN_MAP = {
    'Cat_Basing': 7, 'Cat_Trending': 10, 'Cat_Bullish': 10, 'Cat_Bearish': 10,
    'Cat_Overbought': 5, 'Cat_Oversold': 5, 'Cat_Pos_Breakout': 7, 'Cat_Pos_Breakdown': 7,
    'Cat_Pos_Reversal_Bull': 7, 'Cat_Pos_Reversal_Bear': 7,
    'Cat_Swing_Setup_Bull': 5, 'Cat_Swing_Setup_Bear': 5,
    'Cat_SMC_Bull': 5, 'Cat_SMC_Bear': 5,
}

# ──────────────────────────────────────────
# 유틸리티 헬퍼
# ──────────────────────────────────────────
def _recent(s, lb=3): return s.astype(float).rolling(lb+1, min_periods=1).max().fillna(0).astype(bool)
def _cooldown(sig, bars=5):
    v = sig.astype(bool).values.copy(); last = -bars-1
    for i in range(len(v)):
        if v[i]:
            if (i-last)<=bars: v[i]=False
            else: last=i
    return pd.Series(v, index=sig.index)
def _volf(vol, ratio=0.5, period=20): return vol >= (vol.rolling(period, min_periods=5).mean() * ratio)
def _valid_fmt(t): return bool(re.match(r'^[A-Za-z]{1,5}([.\-][A-Za-z]{1,2})?$', t))
def _cls(val, lo, hi): return 'ind-bullish' if val<lo else ('ind-bearish' if val>hi else 'ind-neutral')

# ──────────────────────────────────────────
# 캐싱 및 데이터 처리
# ──────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_fundamentals(ticker):
    try:
        info = yf.Ticker(ticker).info
        def _get(key, fmt=None):
            val = info.get(key)
            if val is None: return "N/A"
            if fmt == 'currency': return f"${val:,.2f}"
            if fmt == 'large': return f"{val:,.0f}"
            if fmt == 'percent': return f"{val*100:.2f}%"
            if fmt == 'float': return f"{val:.2f}"
            return str(val)
        funds = [
            f"Market Cap: {_get('marketCap', 'large')}",
            f"Shares Outstanding: {_get('sharesOutstanding', 'large')}",
            f"Float: {_get('floatShares', 'large')}",
            f"Short % of Float: {_get('shortPercentOfFloat', 'percent')}",
            f"Trailing EPS: {_get('trailingEps', 'currency')}",
            f"P/E Ratio: {_get('trailingPE', 'float')}",
            f"52 Week High: {_get('fiftyTwoWeekHigh', 'currency')}",
            f"52 Week Low: {_get('fiftyTwoWeekLow', 'currency')}",
            f"Average Volume: {_get('averageVolume', 'large')}"
        ]
        return "\n".join(funds)
    except Exception: return "펀더멘탈 데이터 불가"

@st.cache_data(ttl=300, show_spinner=False)
def fetch_history(ticker, _ts=None):
    return yf.Ticker(ticker).history(period="2y")

@st.cache_data(ttl=600, show_spinner=False)
def validate_ticker(ticker):
    try:
        info = yf.Ticker(ticker).info
        return info.get('regularMarketPrice') is not None or info.get('currentPrice') is not None
    except: return False

@st.cache_data(ttl=300, show_spinner=False)
def compute_and_cache(ticker, _ts=None):
    df = fetch_history(ticker, _ts)
    if df.empty: return None
    return detect_10_master_signals(compute_indicators(df))

# ──────────────────────────────────────────
# 🚀 서브 계산 엔진 (지표 계산)
# ──────────────────────────────────────────
def compute_rsi(s, p=14):
    d=s.diff(); g,l=d.clip(lower=0),-d.clip(upper=0)
    return 100-(100/(1+g.ewm(alpha=1/p,min_periods=p).mean()/(l.ewm(alpha=1/p,min_periods=p).mean()+1e-10)))

def compute_mfi(h,l,c,v,p=14):
    tp=(h+l+c)/3; raw=tp*v; d=tp.diff()
    return 100-(100/(1+raw.where(d>=0,0.0).rolling(p).sum()/(raw.where(d<0,0.0).rolling(p).sum()+1e-10)))

def compute_rsi_mfi(h,l,c,v,p=60):
    rf,mf=compute_rsi(c,20),compute_mfi(h,l,c,v,20)
    rs,ms=compute_rsi(c,p),compute_mfi(h,l,c,v,p)
    return (((rf-50)+(mf-50))/2)*.6+(((rs-50)+(ms-50))/2)*.4

def compute_wavetrend(h,l,c,ch=9,avg=12,ma=3):
    ap=(h+l+c)/3; esa=ap.ewm(span=ch,adjust=False).mean()
    d=abs(ap-esa).ewm(span=ch,adjust=False).mean()
    ci=(ap-esa)/(0.015*d+1e-10); wt1=ci.ewm(span=avg,adjust=False).mean()
    wt2=wt1.rolling(ma).mean()
    return wt1,wt2,(wt1>wt2)&(wt1.shift(1)<=wt2.shift(1)),(wt1<wt2)&(wt1.shift(1)>=wt2.shift(1))

def compute_stoch_rsi(c, rl=14, sl=14, ks=3, ds=3):
    rsi=compute_rsi(c,rl); mn,mx=rsi.rolling(sl).min(),rsi.rolling(sl).max()
    k=(((rsi-mn)/(mx-mn+1e-10))*100).rolling(ks).mean()
    return k, k.rolling(ds).mean()

def compute_tr(h,l,c):
    pc=c.shift(1); return pd.concat([h-l,(h-pc).abs(),(l-pc).abs()],axis=1).max(axis=1)

def compute_adx(h,l,c,p=14):
    tr=compute_tr(h,l,c); ph,pl=h.shift(1),l.shift(1)
    pdm=pd.Series(np.where((h-ph)>(pl-l),np.maximum(h-ph,0),0),index=h.index,dtype=float)
    mdm=pd.Series(np.where((pl-l)>(h-ph),np.maximum(pl-l,0),0),index=h.index,dtype=float)
    atr=tr.ewm(alpha=1/p,min_periods=p).mean()
    pdi=100*pdm.ewm(alpha=1/p,min_periods=p).mean()/(atr+1e-10)
    mdi=100*mdm.ewm(alpha=1/p,min_periods=p).mean()/(atr+1e-10)
    dx=100*(pdi-mdi).abs()/(pdi+mdi+1e-10)
    return dx.ewm(alpha=1/p,min_periods=p).mean(),pdi,mdi

def compute_supertrend(h,l,c,period=10,mult=3.0):
    atr=compute_tr(h,l,c).rolling(period).mean(); hl2=(h+l)/2
    up=(hl2+mult*atr).values.copy(); dn=(hl2-mult*atr).values.copy()
    cl=c.values; n=len(c)
    sv=np.full(n,np.nan); dv=np.zeros(n,dtype=int)
    fv=period
    if fv>=n: return pd.Series(np.nan,index=c.index),pd.Series(0,index=c.index,dtype=int)
    dv[fv]=1; sv[fv]=dn[fv]
    for i in range(fv+1,n):
        if dv[i-1]==1: dn[i]=max(dn[i],dn[i-1]) if not np.isnan(dn[i-1]) else dn[i]
        else: up[i]=min(up[i],up[i-1]) if not np.isnan(up[i-1]) else up[i]
        if dv[i-1]==1: dv[i],sv[i]=(-1,up[i]) if cl[i]<dn[i] else (1,dn[i])
        else: dv[i],sv[i]=(1,dn[i]) if cl[i]>up[i] else (-1,up[i])
    return pd.Series(sv,index=c.index),pd.Series(dv,index=c.index)

def detect_smart_money(o, c, h, l, atr):
    fvg_bull = l > h.shift(2)
    fvg_bear = h < l.shift(2)
    l20 = l.shift(1).rolling(20).min()
    h20 = h.shift(1).rolling(20).max()
    sweep_bull = (l < l20) & (c > l20) & (c > o)
    sweep_bear = (h > h20) & (c < h20) & (c < o)
    body = (c-o).abs()
    smc_bull = sweep_bull | (fvg_bull & (body > atr*0.5) & (c > o))
    smc_bear = sweep_bear | (fvg_bear & (body > atr*0.5) & (c < o))
    return smc_bull, smc_bear

def detect_volume_climax(c, o, h, l, v, atr, z_thresh=2.5):
    v_mean=v.rolling(20).mean(); v_std=v.rolling(20).std()
    v_z=(v-v_mean)/(v_std+1e-10)
    body=(c-o).abs()
    upper_wick=h-np.maximum(o,c); lower_wick=np.minimum(o,c)-l
    ps=(v_z.shift(1)>z_thresh)
    buy=ps & (c>o) & (lower_wick>body*1.2) & (c.shift(1)<o.shift(1))
    sell=ps & (c<o) & (upper_wick>body*1.2) & (c.shift(1)>o.shift(1))
    return buy,sell

def detect_123_pullback(h, l, adx, pdi, mdi):
    strong_b = (adx > 30) & (pdi > mdi)
    strong_s = (adx > 30) & (mdi > pdi)
    inside = (h < h.shift(1)) & (l > l.shift(1))
    ll1 = l < l.shift(1); ll2 = l.shift(1) < l.shift(2); ll3 = l.shift(2) < l.shift(3)
    three_ll = ll1 & ll2 & ll3
    two_ll_in = ((ll1 & ll2 & inside.shift(2)) | (ll1 & inside.shift(1) & ll3) | (inside & ll2 & ll3))
    hh1 = h > h.shift(1); hh2 = h.shift(1) > h.shift(2); hh3 = h.shift(2) > h.shift(3)
    three_hh = hh1 & hh2 & hh3
    two_hh_in = ((hh1 & hh2 & inside.shift(2)) | (hh1 & inside.shift(1) & hh3) | (inside & hh2 & hh3))
    return strong_b & (three_ll | two_ll_in), strong_s & (three_hh | two_hh_in)

def detect_180_setup(c, o, h, l, ma10, ma50):
    dr = h - l + 1e-10
    cp = (c - l) / dr
    pp = (c.shift(1) - l.shift(1)) / (h.shift(1) - l.shift(1) + 1e-10)
    bull = (pp <= 0.25) & (cp >= 0.75) & (c > ma10) & (c > ma50)
    bear = (pp >= 0.75) & (cp <= 0.25) & (c < ma10) & (c < ma50)
    return bull, bear

# ──────────────────────────────────────────
# 지표 초기 계산 (compute_indicators)
# ──────────────────────────────────────────
def compute_indicators(df):
    c,h,l,v=df['Close'],df['High'],df['Low'],df['Volume']
    for ma in [5,10,20,50,100,125,200]: df[f'MA{ma}']=c.rolling(ma).mean()
    df['EMA8']=c.ewm(span=8,adjust=False).mean()
    df['EMA21']=c.ewm(span=21,adjust=False).mean()
    s20=c.rolling(20).std()
    df['BB_Up'] = df['MA20']+s20*2
    df['BB_Low'] = df['MA20']-s20*2
    df['ATR']=compute_tr(h,l,c).rolling(14).mean()
    df['SuperTrend'],df['ST_Direction']=compute_supertrend(h,l,c)
    wt1,wt2,wu,wd=compute_wavetrend(h,l,c)
    df['WT1'],df['WT2'],df['WT_Up'],df['WT_Down']=wt1,wt2,wu,wd
    df['RSI']=compute_rsi(c,14)
    df['StochK'],df['StochD']=compute_stoch_rsi(c)
    df['MFI']=compute_mfi(h,l,c,v,14)
    df['RSI_MFI']=compute_rsi_mfi(h,l,c,v,60)
    df['ADX'],df['Plus_DI'],df['Minus_DI']=compute_adx(h,l,c)
    
    ml=c.ewm(span=12).mean()-c.ewm(span=26).mean()
    ms=ml.ewm(span=9).mean()
    df['MACD_Line'],df['MACD_Signal'],df['MACD_Hist']=ml,ms,ml-ms
    
    atr10 = compute_tr(h,l,c).rolling(10).mean()
    df['KC_Upper'] = df['MA20'] + atr10 * 1.5
    df['KC_Lower'] = df['MA20'] - atr10 * 1.5
    return df

# ──────────────────────────────────────────
# 🚀 10 Master Signals + Regime Engine (국면 필터링)
# ──────────────────────────────────────────
def detect_10_master_signals(df):
    c, h, l, o, v = df['Close'], df['High'], df['Low'], df['Open'], df['Volume']
    
    # 1. 10대 마스터 카테고리 계산
    sq_on = (df['BB_Up'] < df['KC_Upper']) & (df['BB_Low'] > df['KC_Lower'])
    sq_fire = (~sq_on) & sq_on.shift(1).fillna(False)

    dr = h - l
    nr7 = dr <= dr.rolling(7).min()
    df['Cat_Basing'] = (sq_on & (~sq_on.shift(1).fillna(False))) | (nr7 & (df['ADX'] < 25))
    df['Cat_Trending'] = (df['ADX'] > 25) & (df['ADX'].shift(1) <= 25)
    df['Cat_Bullish'] = (df['MACD_Line'] > 0) & (df['MACD_Line'].shift(1) <= 0) & (c > df['MA50']) & (df['MA50'] > df['MA200'])
    df['Cat_Bearish'] = (df['MACD_Line'] < 0) & (df['MACD_Line'].shift(1) >= 0) & (c < df['MA50']) & (df['MA50'] < df['MA200'])
    df['Cat_Overbought'] = ((df['RSI'] > 70) & (df['RSI'].shift(1) <= 70)) | (c > df['BB_Up'])
    df['Cat_Oversold'] = ((df['RSI'] < 30) & (df['RSI'].shift(1) >= 30)) | (c < df['BB_Low'])
    
    xbo = (h > h.shift(1).rolling(60).max()) & (dr >= dr.rolling(9).max())
    momentum_up = c - ((h.rolling(20).max() + l.rolling(20).min())/2 + df['MA20'])/2
    sq_fire_buy = sq_fire & (momentum_up > 0)
    df['Cat_Pos_Breakout'] = xbo | sq_fire_buy | ((c > df['MA50']) & (c.shift(1) <= df['MA50']))
    
    xbd = (l < l.shift(1).rolling(60).min()) & (dr >= dr.rolling(9).max())
    sq_fire_sell = sq_fire & (momentum_up < 0)
    df['Cat_Pos_Breakdown'] = xbd | sq_fire_sell | ((c < df['MA50']) & (c.shift(1) >= df['MA50']))
    
    vol_buy, vol_sell = detect_volume_climax(c, o, h, l, v, df['ATR'])
    rbd = (c < c.shift(5)) & (df['RSI'] > df['RSI'].shift(5)) & (df['RSI'] < 35)
    rbrd = (c > c.shift(5)) & (df['RSI'] < df['RSI'].shift(5)) & (df['RSI'] > 65)
    df['Cat_Pos_Reversal_Bull'] = vol_buy | rbd
    df['Cat_Pos_Reversal_Bear'] = vol_sell | rbrd
    
    pb123_buy, pb123_sell = detect_123_pullback(h, l, df['ADX'], df['Plus_DI'], df['Minus_DI'])
    s180_buy, s180_sell = detect_180_setup(c, o, h, l, df['MA10'], df['MA50'])
    df['Cat_Swing_Setup_Bull'] = pb123_buy | s180_buy
    df['Cat_Swing_Setup_Bear'] = pb123_sell | s180_sell
    
    smc_bull, smc_bear = detect_smart_money(o, c, h, l, df['ATR'])
    df['Cat_SMC_Bull'] = smc_bull
    df['Cat_SMC_Bear'] = smc_bear

    # ══════════════════════════════════════════════════
    # 🧠 국면(Regime) 필터링 스위치 (The Core Logic)
    # ══════════════════════════════════════════════════
    # 국면 정의: 50일선, 200일선, 단기 8/21선 배열로 강세/약세/횡보 구분
    tc = pd.Series(0.0, index=df.index)
    tc += np.where(c > df['MA50'],  1.0, -1.0)
    tc += np.where(c > df['MA200'], 1.0, -1.0)
    tc += np.where(df['EMA8'] > df['EMA21'], 0.5, -0.5)
    tc += np.where(df['ST_Direction'] == 1, 0.5, -0.5)
    
    regime_bull = tc >= 1.5     # 강세장
    regime_bear = tc <= -1.5    # 약세장
    regime_side = (tc > -1.5) & (tc < 1.5) # 횡보장
    
    df['Regime_Status'] = np.where(regime_bull, 'BULL 🟢', np.where(regime_bear, 'BEAR 🔴', 'SIDEWAYS ⚪'))

    # 국면별 필터링 적용
    # 1. 강세장: 과매수(매도) 무시. 약한 역추세(매도) 무시.
    df['Cat_Overbought'] = df['Cat_Overbought'] & (~regime_bull)
    df['Cat_Swing_Setup_Bear'] = df['Cat_Swing_Setup_Bear'] & (~regime_bull)
    
    # 2. 약세장: 과매도(매수) 무시. 약한 역추세(매수) 무시.
    df['Cat_Oversold'] = df['Cat_Oversold'] & (~regime_bear)
    df['Cat_Swing_Setup_Bull'] = df['Cat_Swing_Setup_Bull'] & (~regime_bear)
    
    # 3. 횡보장: 거래량 없는 돌파/붕괴 무시 (휩쏘 방지)
    high_vol = v > v.rolling(20).mean() * 1.5
    df['Cat_Pos_Breakout'] = df['Cat_Pos_Breakout'] & (~regime_side | high_vol)
    df['Cat_Pos_Breakdown'] = df['Cat_Pos_Breakdown'] & (~regime_side | high_vol)

    # 쿨다운 적용
    for s, cd in COOLDOWN_MAP.items():
        if s in df.columns: df[s] = _cooldown(df[s], cd)
    
    # Confluence 연산 및 액션 시그널 산출
    compute_confluence(df)
    
    return df

def compute_confluence(df, dw=5, df_=0.75):
    bm = {k: v['w'] for k, v in SIGNAL_REGISTRY.items() if v['dir'] == 'buy'}
    sm = {k: v['w'] for k, v in SIGNAL_REGISTRY.items() if v['dir'] == 'sell'}
    dk=np.array([df_**i for i in range(dw+1)]); ones=np.ones(dw+1)
    s=np.zeros(len(df)); bc=np.zeros(len(df)); sc=np.zeros(len(df))
    
    for col,w in bm.items():
        if col in df.columns:
            raw=df[col].fillna(False).astype(float).values
            s+=np.convolve(raw*w,dk,mode='full')[:len(raw)]
            bc+=np.convolve(raw,ones,mode='full')[:len(raw)]
    for col,w in sm.items():
        if col in df.columns:
            raw=df[col].fillna(False).astype(float).values
            s-=np.convolve(raw*w,dk,mode='full')[:len(raw)]
            sc+=np.convolve(raw,ones,mode='full')[:len(raw)]
            
    wt1=df['WT1'].values
    s+=np.where(wt1<OS1,1.0,0)+np.where(wt1<OS2,0.5,0)-np.where(wt1>OB1,1.0,0)-np.where(wt1>OB2,0.5,0)
    adx=df['ADX'].values; pdi=df['Plus_DI'].values; mdi=df['Minus_DI'].values
    bull_trend=pdi>mdi; bear_trend=mdi>pdi
    adx_factor=np.clip((adx-20)/100,0.0,0.3)
    s+=np.where(bull_trend&(s>0),s*adx_factor,0)
    s-=np.where(bear_trend&(s<0),abs(s)*adx_factor,0)
    
    df['Confluence_Score']=s
    
    # 🌟 액션 시그널(Composite) 판정 로직
    df['Ultra_Buy']=(s>=6.5)|((s>=5)&(bc>=3))
    df['Ultra_Sell']=(s<=-6.5)|((s<=-5)&(sc>=3))
    df['Strong_Buy']=(s>=3.5)&(~df['Ultra_Buy'])
    df['Strong_Sell']=(s<=-3.5)&(~df['Ultra_Sell'])
    return s

def compute_signal_stats(df, col, direction, fwd=(2, 3, 5), mn=5):
    if col not in df.columns: return None
    mask = df[col].fillna(False).values.astype(bool)
    if mask.sum() < mn: return None
    st_res = {'count': int(mask.sum())}
    entry_price = df['Open'].shift(-1)
    for n in fwd:
        exit_price = df['Close'].shift(-(n + 1))
        pct_change = (exit_price - entry_price) / entry_price * 100
        valid_returns = pct_change[mask].dropna()
        if len(valid_returns) >= mn:
            st_res[f'{n}d_avg'] = float(valid_returns.mean())
            if direction == 'sell':
                st_res[f'{n}d_winrate'] = float((valid_returns < 0).sum() / len(valid_returns) * 100)
            else:
                st_res[f'{n}d_winrate'] = float((valid_returns > 0).sum() / len(valid_returns) * 100)
            st_res[f'{n}d_median'] = float(valid_returns.median())
        else:
            st_res[f'{n}d_avg'] = st_res[f'{n}d_winrate'] = st_res[f'{n}d_median'] = None
    return st_res

def compute_all_stats(dv):
    tgt={k:v['dir'] for k,v in SIGNAL_REGISTRY.items() if v['dir'] != 'neutral'}
    return {s:{**r,'direction':d} for s,d in tgt.items() if (r:=compute_signal_stats(dv, s, d)) and r['count']>0}

# ──────────────────────────────────────────
# 통합 분석 로직
# ──────────────────────────────────────────
def analyze(ticker,chart_days=252,refresh=False):
    try:
        ts=int(time.time()) if refresh else None
        df=compute_and_cache(ticker,ts)
        if df is None or df.empty: return None,"주가 데이터 없음",None
        dv=df.dropna(subset=['WT1']); dc=dv.tail(chart_days).copy()
        if dc.empty: return None,"차트 데이터 부족",None
        meta=build_metadata(dc,dv,ticker)
        fig=build_chart(dc,ticker)
        return fig,build_prompt_text(dc,meta),meta
    except Exception as e:
        return None,f"로딩 실패:{e}",None

def build_chart(dc,ticker):
    fig=make_subplots(rows=6,cols=1,shared_xaxes=True,vertical_spacing=0.035,
        row_heights=[.36,.07,.15,.12,.15,.15],
        subplot_titles=("Price & Master Signals","Volume","WaveTrend Oscillator","Money Flow","MACD (12, 26, 9)","Confluence Score"))

    enabled=st.session_state.get('enabled_signals',set(ALL_CHART_SIGNALS.keys()))
    active_masks={}
    for cn,cfg in ALL_CHART_SIGNALS.items():
        if cn not in dc.columns or cn not in enabled: continue
        active_masks[cn]=dc[cn].copy()

    daily_sig_texts=[]
    for i in range(len(dc)):
        day_sigs=[]
        for cn,mask in active_masks.items():
            if mask.iloc[i]:
                cfg=ALL_CHART_SIGNALS[cn]
                day_sigs.append(f"<span style='color:{cfg['clr']}'><b>{cfg['icon']} {cfg['label']}</b></span> <span style='font-size:11px;color:#AAA'>({cfg.get('kor','')})</span>")
        if day_sigs: daily_sig_texts.append("<br><br><b>🎯 포착 시그널:</b><br>"+"<br>".join(day_sigs))
        else: daily_sig_texts.append("")

    fig.add_trace(go.Candlestick(x=dc.index,open=dc['Open'],high=dc['High'],low=dc['Low'],close=dc['Close'],name="Price",
        increasing_line_color='#00E676',decreasing_line_color='#FF1744',
        increasing_fillcolor='rgba(0,230,118,0.8)',decreasing_fillcolor='rgba(255,23,68,0.8)',
        customdata=daily_sig_texts,hovertemplate="O:%{open:.2f}<br>H:%{high:.2f}<br>L:%{low:.2f}<br>C:%{close:.2f}%{customdata}<extra></extra>"),row=1,col=1)

    for ma, clr in [(20, '#f1c40f'), (50, '#e74c3c'), (200, '#2ecc71')]:
        fig.add_trace(go.Scatter(x=dc.index,y=dc[f'MA{ma}'],line=dict(color=clr,width=1.5),name=f'{ma}MA'),row=1,col=1)
    
    fig.add_trace(go.Scatter(x=dc.index,y=dc['BB_Up'],line=dict(color='gray',width=1,dash='dot'),name='BB↑'),row=1,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['BB_Low'],line=dict(color='gray',width=1,dash='dot'),name='BB↓',fill='tonexty',fillcolor='rgba(128,128,128,0.07)'),row=1,col=1)

    # 배경색으로 국면 표시 (Regime Shading)
    for i in range(len(dc)):
        regime = dc['Regime_Status'].iloc[i]
        if "BULL" in regime:
            fig.add_vrect(x0=dc.index[i], x1=dc.index[i], fillcolor="rgba(0,230,118,0.03)", line_width=0, row=1, col=1)
        elif "BEAR" in regime:
            fig.add_vrect(x0=dc.index[i], x1=dc.index[i], fillcolor="rgba(255,23,68,0.03)", line_width=0, row=1, col=1)

    def _at(s): return dc.loc[s.index,'ATR'].fillna(dc['ATR'].median())

    for cn,cfg in ALL_CHART_SIGNALS.items():
        if cn not in active_masks: continue
        sig=dc[active_masks[cn]]
        if sig.empty: continue
        yv=sig[cfg['base']]+_at(sig)*cfg['atr_m']
        lw=2 if cfg['sz']>=16 else (1.5 if cfg['sz']>=13 else 1)
        fig.add_trace(go.Scatter(x=sig.index,y=yv,mode='markers',
            marker=dict(symbol=cfg['sym'],size=cfg['sz'],color=cfg['clr'],
                line=dict(width=lw,color='white' if 'open' not in cfg['sym'] else cfg['clr'])),
            name=f"{cfg['icon']} {cfg['label']}",hoverinfo='skip'),row=1,col=1)

    br=dc['Close']<dc['Open']
    fig.add_trace(go.Bar(x=dc.index,y=dc['Volume'],
        marker_color=np.where(br,'rgba(255,23,68,0.6)','rgba(0,230,118,0.6)').tolist(),
        name="Volume",opacity=0.8),row=2,col=1)

    fig.add_trace(go.Scatter(x=dc.index,y=dc['WT1'],line=dict(color='#00E676',width=2),name="WT1"),row=3,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['WT2'],line=dict(color='#FF1744',width=1.5,dash='dot'),name="WT2"),row=3,col=1)
    wd=dc['WT1']-dc['WT2']
    fig.add_trace(go.Bar(x=dc.index,y=wd,marker_color=np.where(wd>=0,'#00E676','#FF1744').tolist(),name="WT Hist",opacity=0.3),row=3,col=1)
    
    for lv,c_color,d in [(OB2,'#ff3333','dash'),(OB1,'#ff3333','solid'),(0,'gray','dot'),(OS1,'#00bfff','solid'),(OS2,'#00bfff','dash')]:
        fig.add_hline(y=lv,line_dash=d,line_color=c_color,line_width=1,row=3,col=1)
    wmx=max(float(dc['WT1'].max()),100)+10; wmn=min(float(dc['WT1'].min()),-100)-10
    fig.add_hrect(y0=OB1,y1=wmx,fillcolor="rgba(255,23,68,0.08)",line_width=0,row=3,col=1)
    fig.add_hrect(y0=wmn,y1=OS1,fillcolor="rgba(0,191,255,0.08)",line_width=0,row=3,col=1)

    rmfi=dc['RSI_MFI']
    fig.add_trace(go.Bar(x=dc.index,y=rmfi,marker_color=np.where(rmfi>=0,'#3ee145','#ff3d2e').tolist(),
        name="Money Flow",opacity=0.7),row=4,col=1)
    fig.add_hline(y=0,line_dash="solid",line_color="gray",line_width=1,row=4,col=1)

    fig.add_trace(go.Scatter(x=dc.index,y=dc['MACD_Line'],line=dict(color='#29B6F6',width=1.5),name="MACD"),row=5,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['MACD_Signal'],line=dict(color='#FFA726',width=1.5),name="Signal"),row=5,col=1)
    mh=dc['MACD_Hist']
    fig.add_trace(go.Bar(x=dc.index,y=mh,marker_color=np.where(mh>=0,'#26A69A','#EF5350').tolist(),name="Hist",opacity=0.7),row=5,col=1)
    fig.add_hline(y=0,line_color="#444444",line_width=1,row=5,col=1)

    conf=dc['Confluence_Score']
    fig.add_trace(go.Bar(x=dc.index,y=conf,
        marker_color=np.where(conf>=3.5,'#00E676',np.where(conf<=-3.5,'#FF1744','#FFC107')).tolist(),
        name="Conf Score",opacity=0.8),row=6,col=1)
    for lv,c_color,d in [(6.5,'#00E676','dash'),(-6.5,'#FF1744','dash'),(3.5,'#00E676','dot'),(-3.5,'#FF1744','dot'),(0,'gray','solid')]:
        fig.add_hline(y=lv,line_dash=d,line_color=c_color,line_width=1 if d=='solid' else .8,row=6,col=1)

    fig.update_layout(
        yaxis_title="Price", yaxis2_title="Vol", yaxis3_title="WT",
        yaxis4_title="MF", yaxis5_title="MACD", yaxis6_title="Conf",
        template="plotly_dark",paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=2,r=2,t=40,b=2),height=1200,showlegend=True,hovermode="x unified",
        hoverlabel=dict(bgcolor="rgba(14,17,23,0.95)",font_size=12,font_family="Pretendard",bordercolor="#2D333B"),
        legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="center",x=0.5,
            font=dict(size=9.5,color='#CCC',family='Pretendard'),bgcolor='rgba(0,0,0,0)',itemsizing='constant'))
    
    for i in range(1,7):
        ya=f'yaxis{i}' if i>1 else 'yaxis'
        fig.update_layout(**{ya:dict(gridcolor='rgba(45,51,59,0.5)',gridwidth=1,
            zerolinecolor='rgba(60,63,70,0.6)',zerolinewidth=1,
            title_font=dict(size=11,color='#777'),tickfont=dict(size=10,color='#888'))})
            
    fig.update_xaxes(rangeslider_visible=False, showspikes=True, spikecolor="#667eea", spikemode="across", gridcolor='rgba(45,51,59,0.5)')
    has_weekends=dc.index.dayofweek.isin([5,6]).any()
    if not has_weekends: fig.update_xaxes(rangebreaks=[dict(bounds=["sat","mon"])])
    
    return fig

# ──────────────────────────────────────────
# V10.0 스타일 메타데이터 + AI 프롬프트
# ──────────────────────────────────────────
def build_metadata(dc,dv,ticker):
    lat,prev=dc.iloc[-1],dc.iloc[-2] if len(dc)>=2 else dc.iloc[-1]
    pc=lat['Close']-prev['Close']; pp=pc/prev['Close']*100
    
    regime = lat.get('Regime_Status', 'NEUTRAL ⚪')
    
    sig_checks=[(k,v['icon'],v['label'],v['dir']) for k,v in ALL_CHART_SIGNALS.items()]
    recent=[]
    for ir,row in dc.tail(15).iterrows():
        ds=ir.strftime('%m/%d')
        for col,icon,lbl,side in sig_checks:
            if row.get(col,False): recent.append((icon,lbl,ds,side))
            
    return {
        'ticker':ticker.upper(),'price':lat['Close'],'price_change':pc,'price_change_pct':pp,
        'volume':lat['Volume'],'avg_volume':dc['Volume'].rolling(20).mean().iloc[-1],
        'wt1':float(lat['WT1']),'wt2':float(lat['WT2']),'rsi':float(lat['RSI']),'mfi':float(lat['MFI']),
        'stochk':float(lat['StochK']),'stochd':float(lat['StochD']),
        'vwap_osc':float(lat['VWAP_Osc']),'mf_area':float(lat['RSI_MFI']),
        'atr':float(lat['ATR']),'atr_pct':float(lat['ATR'])/float(lat['Close'])*100,
        'adx':float(lat['ADX']),'plus_di':float(lat['Plus_DI']),'minus_di':float(lat['Minus_DI']),
        'confluence_score':float(dc['Confluence_Score'].iloc[-1]),
        'recent_signals':recent,'all_signal_stats':compute_all_stats(dv),
        'last_date':dc.index[-1].strftime('%Y-%m-%d'),
        'trend_regime':regime,
        'supertrend_dir':int(lat.get('ST_Direction',0)),'supertrend_val':float(lat.get('SuperTrend',0)),
        'ema8':float(lat.get('EMA8',0)),'ema21':float(lat.get('EMA21',0)),
        'bb_up':float(lat.get('BB_Up',0)),'bb_low':float(lat.get('BB_Low',0)),
        'ma50':float(lat.get('MA50',0)),'ma200':float(lat.get('MA200',0)),
        'macd_line':float(lat.get('MACD_Line',0)),'macd_signal':float(lat.get('MACD_Signal',0)),
        'macd_hist':float(lat.get('MACD_Hist',0)),
    }

def build_prompt_text(dc,meta):
    lat=dc.iloc[-1]; rd=dc.tail(60)
    ps=", ".join([f"'{d.strftime('%Y-%m-%d')}:{r['Close']:.2f}'" for d,r in rd.iterrows()])
    sl=[]
    for ir,row in dc.tail(30).iterrows():
        dd=ir.strftime('%Y-%m-%d')
        for k,v in ALL_CHART_SIGNALS.items():
            if row.get(k,False): sl.append(f"{v['icon']} {v['label']} {dd}")
    st_text="\n".join(sl) if sl else "최근 30일 내 주요 카테고리 시그널 없음"
    
    std=f"BULL▲({meta['supertrend_val']:.2f})" if meta['supertrend_dir']==1 else f"BEAR▼({meta['supertrend_val']:.2f})"
    inds=(f"WT1={lat['WT1']:.1f},WT2={lat['WT2']:.1f},RSI={lat['RSI']:.1f},MFI={lat['MFI']:.1f},"
        f"StK={lat['StochK']:.1f},StD={lat['StochD']:.1f},VWAP={lat['VWAP_Osc']:.2f},"
        f"MF={lat['RSI_MFI']:.1f},ADX={lat['ADX']:.1f},+DI={lat['Plus_DI']:.1f},-DI={lat['Minus_DI']:.1f},"
        f"E8={lat['EMA8']:.2f},E21={lat['EMA21']:.2f},ST={std},"
        f"BB=[{meta['bb_up']:.2f}/{meta['bb_low']:.2f}],M50={meta['ma50']:.2f},M200={meta['ma200']:.2f},"
        f"MACD={meta['macd_line']:.3f}/{meta['macd_signal']:.3f} H={meta['macd_hist']:.3f},"
        f"Conf={meta['confluence_score']:.1f}, Trend={meta['trend_regime']}")
    stats=meta.get('all_signal_stats',{})
    st_txt=""
    if stats:
        lines=[]
        for sn,sv in sorted(stats.items(),key=lambda x:x[1]['count'],reverse=True)[:10]:
            wr=sv.get('2d_winrate'); avg=sv.get('2d_avg')
            if wr is not None: lines.append(f"  {sn}:{sv['count']}회,2일승률{wr:.0f}%,평균주가변동{avg:+.1f}%")
        if lines: st_txt="\n📌 [시그널 백테스트]\n"+"\n".join(lines)
        
    return f"{ps}\n\n📌 [핵심 지표]\n{inds}\n\n📌 [최근 마스터 시그널 및 액션 발생 내역]\n{st_text}{st_txt}"

def build_ai_prompt(ticker,phist,fundamentals):
    return f"""━━━━━━━━━━━━━
【 🎯 Role & Persona 】
━━━━━━━━━━━━━
당신은 월스트리트 20년 경력의 베테랑 퀀트 트레이더입니다.
시장의 '핵심 국면(Master Signals)' 및 '스마트 머니 유동성 스윕(SMC)' 에 의존하여 매우 확신에 찬(High Conviction) 타점만 분석합니다.

---
━━━━━━━━━━━━━
【 🛠️ Task & Rules 】
━━━━━━━━━━━━━
1. 제공된 [최근 마스터 시그널 발생 내역]을 바탕으로 주가가 현재 11가지 국면 및 강력 매수/매도 액션 시점에 도달했는지 규명하세요.
2. 🚫 환각(Hallucination) 엄금: 제공되지 않은 지표나 펀더멘탈은 지어내지 마세요.
3. 🧮 손절가와 목표가는 반드시 **ATR** 데이터를 기반으로 산출하세요.
   - 손절 = 현재가 - (ATR * 1.5) / 목표가 = 현재가 + (ATR * 2.0)

---
━━━━━━━━━━━━━
【 📥 Input Data 】
━━━━━━━━━━━━━
[티커: {ticker}]

📌 [주가 + 핵심 지표 + 10대 시그널 내역]
{phist}

📌 [YFinance 펀더멘탈]
{fundamentals}

---
━━━━━━━━━━━━━
【 📄 Output Format 】
━━━━━━━━━━━━━
# 🎯 {ticker} 스나이퍼 퀀트 리포트
[🔵/🔴/🟠] [{ticker}] 현재 국면: [국면 및 강력 매수/매도 판정 기재]

### 1. 현재 시장 국면 (SMC 및 Master Signals 기반)
* **포착된 시그널:** [최근 발생한 시그널 목록]
* **국면 진단:** [이 시그널들이 뜻하는 현재의 시장 상태 분석]
* **신뢰도:** [제공된 백테스트 승률 데이터 기반으로 평가]

### 2. 기술적 핵심 요약 (Heavy Data)
* WaveTrend & MACD: [WT1/WT2 값, MACD 상태]
* 거래량 및 모멘텀: [과매수/과매도 여부, 추세 강도(ADX) 평가]
* 지지선 및 저항선: [MA50, MA200, 볼린저밴드 등 가격대 기재]

### 3. 실전 스나이퍼 트레이딩 전략
* **포지션 방향:** [LONG / SHORT / WAIT]
* **진입 타점:** [가격대]
* **손절가 (Stop-loss):** [ATR 기반 계산 가격]
* **목표가 (Take-profit):** [ATR 기반 계산 가격]

### 결론
[2~3문장으로 아주 명확하고 단호한 행동 지침 제시]
"""

# ──────────────────────────────────────────
# UI 렌더 부속
# ──────────────────────────────────────────
def _il(n,v):
    _IT={'wt1':[(-53,'극과매도'),(-20,'과매도'),(20,'중립'),(53,'과매수'),(999,'극과매수')],
         'rsi':[(30,'과매도'),(45,'약세'),(55,'중립'),(70,'강세'),(999,'과매수')],
         'mfi':[(30,'과매도'),(45,'약세'),(55,'중립'),(70,'강세'),(999,'과매수')],
         'stochk':[(20,'바닥'),(80,''),(999,'천장')]}
    for t,l in _IT.get(n,[]):
        if v<=t: return l
    return ''

def render_price_header(m):
    chg=m['price_change']; cp=m['price_change_pct']
    cc='price-change-up' if chg>=0 else 'price-change-down'
    ci='▲' if chg>=0 else '▼'
    vr=m['volume']/m['avg_volume'] if m['avg_volume'] else 0
    cv=m.get('confluence_score',0); sd=m.get('supertrend_dir',0)
    mh_val=m.get('macd_hist',0)
    specs=[(_cls(m['wt1'],-20,20),f"WT:{m['wt1']:.0f} {_il('wt1',m['wt1'])}"),
        (_cls(m['rsi'],40,60),f"RSI:{m['rsi']:.0f} {_il('rsi',m['rsi'])}"),
        (_cls(m['mfi'],40,60),f"MFI:{m['mfi']:.0f} {_il('mfi',m['mfi'])}"),
        ('ind-bullish' if m['mf_area']<0 else ('ind-bearish' if m['mf_area']>0 else 'ind-neutral'),f"MF:{m['mf_area']:.1f}"),
        ('ind-bullish' if vr>1.5 else 'ind-neutral',f"Vol:{vr:.1f}x"),
        ('ind-bullish' if m['adx']>25 else 'ind-neutral',f"ADX:{m['adx']:.0f}"),
        (_cls(m['stochk'],30,70),f"StK:{m['stochk']:.0f} {_il('stochk',m['stochk'])}"),
        ('ind-bullish' if cv>=3.5 else ('ind-bearish' if cv<=-3.5 else 'ind-neutral'),f"Conf:{cv:.1f}"),
        ('ind-bullish' if sd==1 else 'ind-bearish',f"ST:{'▲' if sd==1 else '▼'}"),
        ('ind-bullish' if mh_val>0 else ('ind-bearish' if mh_val<0 else 'ind-neutral'),f"MACD:{mh_val:+.2f}")]
    ih="".join([f"<span class='indicator-mini {c}'>{l}</span>" for c,l in specs])
    tr=m.get('trend_regime','NEUTRAL ⚪')
    st.markdown(f"""<div class="price-header">
        <div style="display:flex;justify-content:space-between;align-items:center">
            <div><p class="price-label">🎯 {m['ticker']} · {m['last_date']} · <b>{tr}</b></p>
            <p class="price-big" style="color:#FAFAFA">${m['price']:.2f}
                <span class="{cc}" style="font-size:1rem;margin-left:8px">
                    {ci} {abs(chg):.2f} ({abs(cp):.2f}%)</span></p></div>
            <div style="text-align:right"><p class="price-label">ATR (일일 변동성)</p>
            <p style="color:#FFC107;font-size:1.1rem;font-weight:600;margin:0">
                ${m['atr']:.2f} ({m['atr_pct']:.1f}%)</p></div></div>
        <div style="margin-top:10px;display:flex;gap:6px;flex-wrap:wrap">{ih}</div></div>""",unsafe_allow_html=True)

def render_signals(m):
    sigs=m['recent_signals']
    if not sigs:
        st.markdown("""<div class="signal-card signal-card-neutral">
            <p style="margin:0;color:#FFC107;font-weight:600">🟠 최근 15일 내 시그널 없음</p></div>""",unsafe_allow_html=True)
        return
    dg=OrderedDict()
    for icon,lbl,ds,side in sigs: dg.setdefault(ds,[]).append((icon,lbl,side))
    alls=m.get('all_signal_stats',{})
    for ds in reversed(dg):
        group=dg[ds]; bc=sum(1 for _,_,s in group if s=='buy'); sc_count=sum(1 for _,_,s in group if s=='sell')
        ct='signal-card-buy' if bc>sc_count else ('signal-card-sell' if sc_count>bc else 'signal-card-neutral')
        parts=[]
        for i,l,s in group:
            cn="ind-bullish" if s=="buy" else ("ind-bearish" if s=="sell" else "ind-neutral")
            sh=""
            for sn,sv in alls.items():
                if ALL_CHART_SIGNALS.get(sn,{}).get('label')==l:
                    wr=sv.get('2d_winrate')
                    if wr is not None: sh=f" ({wr:.0f}%)"
                    break
            parts.append(f'<span class="indicator-mini {cn}">{i} {l}{sh}</span>')
        st.markdown(f"""<div class="signal-card {ct}">
            <div style="display:flex;justify-content:space-between;align-items:center">
                <span style="font-weight:700;font-size:.9rem;color:#FAFAFA">📅 {ds}</span>
                <span style="color:#888;font-size:.75rem">{len(group)}개 국면 포착</span></div>
            <div style="margin-top:6px;display:flex;gap:4px;flex-wrap:wrap">{" ".join(parts)}</div></div>""",unsafe_allow_html=True)

def render_stats(m):
    with st.expander("📊 백테스트 (2년, 진입: 시그널 다음날 시가, 청산: 2일 후 종가)",expanded=True):
        alls=m.get('all_signal_stats',{})
        if not alls: st.caption("통계 없음"); return
        def _side(title, data, is_sell=False):
            st.markdown(f"##### {title}")
            for sn,sv in sorted(data.items(),key=lambda x:x[1]['count'],reverse=True):
                wr=sv.get('2d_winrate'); av=sv.get('2d_avg')
                if wr is None: continue
                kor_label=ALL_CHART_SIGNALS.get(sn,{}).get('kor',sn)
                c='#00E676' if wr>50 else ('#FFC107' if wr>40 else '#FF1744')
                lb=f"승률 <span style='color:{c}'>**{wr:.0f}%**</span>"
                if is_sell:
                    av_c='#00E676' if av<0 else '#FF1744'
                    av_text=f"<span style='color:{av_c}'>**{abs(av):.1f}% 하락**</span>" if av<0 else f"<span style='color:{av_c}'>**{av:+.1f}% 상승(실패)**</span>"
                else:
                    av_c='#00E676' if av>0 else '#FF1744'
                    av_text=f"<span style='color:{av_c}'>**{av:+.1f}% 상승**</span>" if av>0 else f"<span style='color:{av_c}'>**{abs(av):.1f}% 하락(실패)**</span>"
                ic=ALL_CHART_SIGNALS.get(sn,{}).get('icon','')
                st.markdown(f"<span style='font-size:.85rem'>{ic} **{kor_label}** ({sv['count']}회) · {lb} · 평균 변동: {av_text}</span>",unsafe_allow_html=True)
        c1,c2=st.columns(2)
        with c1: _side("🟢 BUY 전략 (롱)",{k:v for k,v in alls.items() if v['direction']=='buy'},is_sell=False)
        with c2: _side("🔴 SELL 전략 (숏)",{k:v for k,v in alls.items() if v['direction']=='sell'},is_sell=True)

def render_analysis(msg):
    m,fig=msg.get('meta'),msg.get('fig')
    if m:
        render_price_header(m)
    if m or fig:
        t1,t2,t3,t4=st.tabs(["📊 스나이퍼 차트","🔔 포착 국면","📈 백테스트 통계","🏢 기업 펀더멘탈 상세"])
        with t1:
            plotly_config={'displaylogo':False,
                'modeBarButtonsToRemove':['lasso2d','select2d','hoverCompareCartesian','hoverClosestCartesian']}
            if fig: st.plotly_chart(fig,use_container_width=True,theme=None,config=plotly_config)
        with t2:
            if m: render_signals(m)
        with t3:
            if m: render_stats(m)
        with t4:
            if m: render_company_details(m['ticker'])

# ──────────────────────────────────────────
# 사이드바 & 앱 뼈대
# ──────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎯 CipherX Sniper")
    st.markdown("<p style='color:#888;font-size:.8rem'>AI 퀀트 주가 분석 · V12.0</p>",unsafe_allow_html=True)
    st.markdown("---")
    chart_period=st.radio("표시 기간",['3개월','6개월','1년','2년'],index=0,horizontal=True)
    chart_days={'3개월':63,'6개월':126,'1년':252,'2년':504}[chart_period]
    st.markdown("---")
    with st.expander("🎛️ 시그널 활성화 필터",expanded=False):
        _sb=st.checkbox("🟢 매수 시그널",value=True,key="sb")
        _ss=st.checkbox("🔴 매도 시그널",value=True,key="ss")
        _sn=st.checkbox("⚪ 중립/횡보 국면 표시",value=True,key="sn")
        _mw=st.slider("최소 가중치 필터",0.0,3.0,0.0,0.5,key="mw")
        enabled=set()
        for k,v in ALL_CHART_SIGNALS.items():
            if v['dir']=='buy' and not _sb: continue
            if v['dir']=='sell' and not _ss: continue
            if v['dir']=='neutral' and not _sn: continue
            if v['w'] < _mw: continue
            enabled.add(k)
        st.session_state['enabled_signals']=enabled
    st.markdown("---")
    if st.button("🗑️ 대화 내역 지우기",use_container_width=True,type="secondary"):
        for key in ['messages','pending_ai_ticker','pending_ai_prompt','last_ticker']:
            st.session_state[key]=[{"role":"assistant","type":"text",
                "content":"안녕하세요! 🎯 **CipherX Sniper & SMC** 입니다.\n\n분석할 티커명을 입력하세요."}] if key=='messages' else None
        st.rerun()

if 'messages' not in st.session_state:
    st.session_state.messages=[{"role":"assistant","type":"text","content":"안녕하세요! 🎯 **CipherX Sniper & SMC** 입니다.\n\n티커명을 입력하세요."}]
for key in ['pending_ai_ticker','pending_ai_prompt','last_ticker']:
    if key not in st.session_state: st.session_state[key]=None
if 'enabled_signals' not in st.session_state:
    st.session_state['enabled_signals']=set(ALL_CHART_SIGNALS.keys())

st.markdown("<h2 style='text-align:center;color:#fff;margin-bottom:20px'>🎯 CipherX Sniper</h2>",unsafe_allow_html=True)

if not st.session_state.last_ticker:
    cols=st.columns(4)
    quick_tickers=["NVDA","TSLA","AAPL","MSTR"]
    for idx,col in enumerate(cols):
        with col:
            if st.button(f"{quick_tickers[idx]}",use_container_width=True):
                st.session_state['quick_ticker']=quick_tickers[idx]

for i,msg in enumerate(st.session_state.messages):
    av="✨" if msg["role"]=="assistant" else "🧑‍💻"
    with st.chat_message(msg["role"],avatar=av):
        if msg.get("type")=="analysis":
            st.markdown(msg.get("content",""))
            render_analysis(msg)
            if msg.get("prompt"):
                with st.expander("📝 퀀트 프롬프트 원문 확인",expanded=False):
                    st.code(msg["prompt"],language="markdown")
        elif msg.get("type")=="report":
            with st.expander(f"📊 {msg.get('ticker','')} 스나이퍼 리포트",expanded=True):
                st.markdown(msg["content"])
            st.download_button("📥 마크다운 파일 다운로드",key=f"dl_{i}_{msg.get('ticker','RPT')}",
                data=msg["content"].encode('utf-8'),
                file_name=f"{msg.get('ticker','RPT').upper()}_Quant_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
                mime="text/markdown",use_container_width=True)
        else: st.markdown(msg.get("content",""))

def _run_ai():
    tp=st.session_state.pending_ai_ticker
    pp=st.session_state.pending_ai_prompt
    with st.chat_message("assistant",avatar="✨"):
        pb=st.progress(0,text="스나이퍼 퀀트 엔진 로딩 중...")
        try:
            model=genai.GenerativeModel('gemini-2.5-flash')
            collected_chunks=[]
            def gemini_stream_generator():
                pb.progress(40,text="🚀 AI 리포트 생성 중...")
                response=model.generate_content(pp,stream=True)
                for chunk in response:
                    try: text=chunk.text
                    except ValueError: continue
                    if text:
                        collected_chunks.append(text)
                        yield text
                pb.progress(100,text="✅ 퀀트 분석 완료!")
            with st.expander(f"📊 {tp.upper()} 스나이퍼 퀀트 리포트",expanded=True):
                st.write_stream(gemini_stream_generator())
            pb.empty()
            st.session_state.messages.append({"role":"assistant","type":"report","ticker":tp.upper(),"content":"".join(collected_chunks)})
            st.session_state.pending_ai_ticker=None; st.session_state.pending_ai_prompt=None
            st.rerun()
        except Exception as e:
            pb.empty(); st.error(f"AI 오류: {e}")

def process_ticker(tv,refresh=False):
    tv=tv.strip().upper()
    if not validate_ticker(tv): return st.toast(f"⚠️ {tv} 데이터 없음",icon="🚨")
    st.session_state.messages.append({"role":"user","type":"text","content":tv})
    st.session_state.last_ticker=tv

    with st.chat_message("assistant",avatar="✨"):
        with st.status(f"🌐 {tv} 국면 분석 중...",expanded=True) as status:
            funds=fetch_fundamentals(tv)
            fig,phist,meta=analyze(tv,chart_days,refresh)
            if fig:
                prompt=build_ai_prompt(tv,phist,funds)
                status.update(label=f"✅ {tv} 마스터 시그널 진단 완료!",state="complete",expanded=False)
            else:
                status.update(label=f"⚠️ {tv} 데이터 실패",state="error",expanded=False)

        if fig:
            st.session_state.messages.append({"role":"assistant","type":"analysis","ticker":tv,
                "content":f"✅ **{tv}** 마스터 시그널 분석 완료.","fig":fig,"meta":meta,"prompt":prompt})
            st.session_state.pending_ai_ticker=tv; st.session_state.pending_ai_prompt=prompt
            st.rerun()

if st.session_state.get('quick_ticker'): process_ticker(st.session_state.pop('quick_ticker'))
if st.session_state.last_ticker:
    c1,c2=st.columns([3,1])
    with c1:
        if st.session_state.pending_ai_ticker:
            if st.button(f"🚀 {st.session_state.pending_ai_ticker.upper()} 스나이퍼 AI 분석 시작",type="primary",use_container_width=True): _run_ai()
    with c2:
        if st.button("🔄 새로고침",type="secondary",use_container_width=True): process_ticker(st.session_state.last_ticker,refresh=True)

if ticker_input:=st.chat_input("티커를 입력하세요 (예: TSLA)"): process_ticker(ticker_input)