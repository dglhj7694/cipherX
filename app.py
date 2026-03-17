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
pd.set_option('future.no_silent_downcasting', True)
from plotly.subplots import make_subplots
from collections import OrderedDict
from company_details import render_company_details

st.set_page_config(
    page_title="CipherX V11.0",
    page_icon="📈",
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
# 🔧 시그널 레지스트리  (v11 — 통합 메타데이터)
# ──────────────────────────────────────────
_B, _S = 'buy', 'sell'
def _sig(w,d,icon,label,sym,sz,clr,base,atr_m,kor,desc):
    return {'w':w,'dir':d,'icon':icon,'label':label,'sym':sym,'sz':sz,'clr':clr,
            'base':base,'atr_m':atr_m,'kor':kor,'desc':desc}

SIGNAL_REGISTRY = {
    # MCB+ 기본 매수/매도
    'Gold_Dot':              _sig(3.0,_B,'🏆','GOLD DOT','circle',18,'#FFD700','Low',-3.0,'최강 매수','RSI<30+MFI<30+WT1<-60+상승 다이버전스'),
    'Green_Dot_T1':          _sig(2.5,_B,'🟢','BUY T1','circle',16,'#00E676','Low',-2.5,'강한 매수','WT과매도교차+RSI<30+MFI<30+MF<0'),
    'Green_Dot_T2':          _sig(2.0,_B,'🟩','BUY T2','circle',13,'#69F0AE','Low',-2.2,'매수','WT과매도+RSI또는MFI<32'),
    'Blue_Diamond':          _sig(2.0,_B,'🔹','BLUE DIA','diamond',14,'#00bfff','Low',-1.8,'추세 매수','WT2≤0 상승교차+HTF강세'),
    'Green_Circle':          _sig(0.8,_B,'✅','BUY Circle','circle-open',11,'#00E676','Low',-1.2,'과매도 반등','WT과매도교차+RSI<45'),
    'Bull_Divergence':       _sig(2.0,_B,'📈','Bull Div','triangle-up',12,'#AA00FF','Low',-2.0,'상승 다이버전스','가격 저점↓ vs WT 저점↑'),
    'RSI_Bull_Divergence':   _sig(1.5,_B,'📊','RSI Bull Div','triangle-up',11,'#CE93D8','Low',-1.8,'RSI 상승 다이버전스','가격↓ vs RSI↑'),
    'Squeeze_Fire_Buy':      _sig(1.5,_B,'💥','Squeeze BUY','star-diamond',14,'#00FFFF','Low',-1.5,'스퀴즈 매수','TTM Squeeze 해소+모멘텀↑'),
    'Volume_Climax_Buy':     _sig(2.0,_B,'🌊','Vol Climax BUY','hexagram',14,'#00BCD4','Low',-2.8,'거래량 클라이맥스','3배 거래량+하락장대봉+WT과매도→반등'),
    'ADX_Momentum_Buy':      _sig(1.5,_B,'🚀','ADX Ignition','arrow-up',11,'#76FF03','Low',-1.4,'ADX 점화','ADX>20돌파++DI>-DI'),
    'Bullish_Engulfing':     _sig(1.5,_B,'☀️','Bull Engulf','square',10,'#00E676','Low',-1.3,'상승 장악형','하락캔들 감싸는 상승캔들+WT<-20'),
    'Golden_Cross':          _sig(1.5,_B,'✨','Golden Cross','cross',12,'#FFD700','Low',-0.8,'골든 크로스','50MA>200MA+ADX>15'),
    'Parabolic_Bottom_Buy':  _sig(3.0,_B,'🧊','Parabolic Bot','diamond',16,'#00FFFF','Low',-3.0,'포물선 바닥','WT1<-85 꺾임+양봉'),
    
    'Blood_Diamond':         _sig(3.0,_S,'🩸','BLOOD DIA','diamond',18,'#DC143C','High',3.0,'최강 매도','RSI>70+MFI>70+WT1>60+하락 다이버전스'),
    'Red_Dot_T1':            _sig(2.5,_S,'🔴','SELL T1','circle',16,'#FF1744','High',2.5,'강한 매도','WT과매수하락교차+RSI>70+MFI>70'),
    'Red_Dot_T2':            _sig(2.0,_S,'🟥','SELL T2','circle',13,'#FF5252','High',2.2,'매도','WT과매수+RSI또는MFI>68'),
    'Red_Diamond':           _sig(2.0,_S,'🔸','RED DIA','diamond',14,'#ff3333','High',1.8,'추세 매도','WT2≥0 하락교차+HTF약세'),
    'Red_Circle':            _sig(0.8,_S,'⛔','SELL Circle','circle-open',11,'#FF1744','High',1.2,'과매수 하락','WT과매수하락교차+RSI>55'),
    'Bear_Divergence':       _sig(2.0,_S,'📉','Bear Div','triangle-down',12,'#AA00FF','High',2.0,'하락 다이버전스','가격 고점↑ vs WT↓'),
    'Squeeze_Fire_Sell':     _sig(1.5,_S,'🧨','Squeeze SELL','star-diamond',14,'#FF6600','High',1.5,'스퀴즈 매도','TTM Squeeze 해소+모멘텀↓'),
    'Volume_Climax_Sell':    _sig(2.0,_S,'🌋','Vol Climax SELL','hexagram',14,'#FF5722','High',2.8,'거래량 클라이맥스','3배 거래량+상승장대봉+WT과매수→하락'),
    'ADX_Momentum_Sell':     _sig(1.5,_S,'💨','ADX Down','arrow-down',11,'#FF3D00','High',1.4,'ADX 하락 점화','ADX>20돌파+-DI>+DI'),
    'Bearish_Engulfing':     _sig(1.5,_S,'🌑','Bear Engulf','x',10,'#D50000','High',1.3,'하락 장악형','상승캔들 감싸는 하락캔들+WT>20'),
    'Death_Cross':           _sig(1.5,_S,'☠️','Death Cross','cross',12,'#FF1744','High',0.8,'데드 크로스','50MA<200MA+ADX>15'),
    'Parabolic_Top_Sell':    _sig(3.0,_S,'🌡️','Parabolic Top','diamond',16,'#FF0000','High',3.0,'포물선 천장','WT1>85 꺾임+음봉'),

    # 패턴 및 보조지표
    'Hammer':               _sig(1.5,_B,'🔨','Hammer','triangle-up',11,'#00E676','Low',-1.5,'해머','긴하단꼬리+소형실체+WT<-20'),
    'Morning_Star':         _sig(2.0,_B,'🌅','MornStar','star',13,'#00E676','Low',-2.0,'모닝스타','큰음봉→소형봉→강한양봉(3봉반전)'),
    'Shooting_Star':        _sig(1.5,_S,'🌠','ShootStar','triangle-down',11,'#FF1744','High',1.5,'슈팅스타','긴상단꼬리+소형실체+WT>20'),
    'Evening_Star':         _sig(2.0,_S,'🌆','EveStar','star',13,'#FF1744','High',2.0,'이브닝스타','큰양봉→소형봉→강한음봉(3봉반전)'),
    'Cross_Above_20MA':     _sig(0.8,_B,'📈','X▲20MA','triangle-up',9,'#69F0AE','Low',-0.8,'20MA상향돌파','종가>20MA(전일≤)'),
    'Cross_Above_50MA':     _sig(1.2,_B,'📈','X▲50MA','triangle-up',10,'#00E676','Low',-1.0,'50MA상향돌파','종가>50MA(전일≤)'),
    'Cross_Above_200MA':    _sig(1.5,_B,'📈','X▲200MA','triangle-up',11,'#00BFA5','Low',-1.2,'200MA상향돌파','종가>200MA(전일≤)'),
    'Fell_Below_20MA':      _sig(0.8,_S,'📉','X▼20MA','triangle-down',9,'#FF5252','High',0.8,'20MA하향이탈','종가<20MA(전일≥)'),
    'Fell_Below_50MA':      _sig(1.2,_S,'📉','X▼50MA','triangle-down',10,'#FF1744','High',1.0,'50MA하향이탈','종가<50MA(전일≥)'),
    'Fell_Below_200MA':     _sig(1.5,_S,'📉','X▼200MA','triangle-down',11,'#D50000','High',1.2,'200MA하향이탈','종가<200MA(전일≥)'),
    'BB_Squeeze_End_Bull':  _sig(1.5,_B,'💥','SqEnd▲','star-diamond',12,'#00FFFF','Low',-1.5,'BB스퀴즈해소↑','BB확장+상승+WT↑'),
    'BB_Squeeze_End_Bear':  _sig(1.5,_S,'💥','SqEnd▼','star-diamond',12,'#FF6600','High',1.5,'BB스퀴즈해소↓','BB확장+하락+WT↓'),
    'MACD_Zero_Cross_Buy':  _sig(1.2,_B,'⬆️','MACD 0▲','triangle-up',10,'#4CAF50','Low',-1.0,'MACD 0선돌파','MACD>0(전일≤0)'),
    'MACD_Zero_Cross_Sell': _sig(1.2,_S,'⬇️','MACD 0▼','triangle-down',10,'#E57373','High',1.0,'MACD 0선이탈','MACD<0(전일≥0)'),
    'Gap_Up':               _sig(1.0,_B,'⏫','GapUp','arrow-up',10,'#00E676','Low',-1.0,'갭 상승','시가>전일고가(ATR50%↑)'),
    'Gap_Down':             _sig(1.0,_S,'⏬','GapDn','arrow-down',10,'#FF1744','High',1.0,'갭 하락','시가<전일저가(ATR50%↑)'),
    'NR7':                  _sig(0.3,_B,'🔲','NR7','square-open',7,'#B0BEC5','Low',-0.3,'NR7','7일중최소범위(돌파임박)'),
    
    # Jeff Cooper 전략
    'Pullback_123_Bull':    _sig(2.0,_B,'🎯','123PB▲','triangle-up',12,'#00E676','Low',-1.8,'1,2,3풀백매수','ADX>30+DI↑+3일저점↓후 되돌림매수'),
    'Pullback_123_Bear':    _sig(2.0,_S,'🎯','123PB▼','triangle-down',12,'#FF1744','High',1.8,'1,2,3풀백매도','ADX>30+DI↓+3일고점↑후 되돌림매도'),
    'Setup_180_Bull':       _sig(2.0,_B,'🔄','180▲','star-diamond',13,'#00E676','Low',-2.0,'180매수셋업','전일하위25%→당일상위25%+MA위'),
    'Setup_180_Bear':       _sig(2.0,_S,'🔄','180▼','star-diamond',13,'#FF1744','High',2.0,'180매도셋업','전일상위25%→당일하위25%+MA아래'),
    'Expansion_BO':         _sig(2.5,_B,'🚀','XBO','star-diamond',14,'#FFD700','Low',-2.5,'확장돌파','2개월신고가+9일최대범위→돌파매수'),
    'Expansion_BD':         _sig(2.5,_S,'💨','XBD','star-diamond',14,'#FF0000','High',2.5,'확장붕괴','2개월신저가+9일최대범위→공매도'),
    'Pocket_Pivot':         _sig(1.5,_B,'🧲','PocketPvt','triangle-up',11,'#7C4DFF','Low',-1.5,'포켓피봇','양봉+거래량>10일하락거래량최대+MA위'),
}

# 기존 COMPOSITE_SIGNALS 제거 (Action_Label로 대체됨)
ALL_CHART_SIGNALS = {**SIGNAL_REGISTRY}

OB1, OB2, OS1, OS2 = 53, 60, -53, -60
ST_MIN_BAR = 12

GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GEMINI_API_KEY)

COOLDOWN_MAP = {
    'Squeeze_Fire_Buy':5,'Squeeze_Fire_Sell':5, 'Bullish_Engulfing':5,'Bearish_Engulfing':5,
    'ADX_Momentum_Buy':10,'ADX_Momentum_Sell':10, 'Parabolic_Top_Sell':5,'Parabolic_Bottom_Buy':5,
    'Hammer':5,'Shooting_Star':5,'Morning_Star':7,'Evening_Star':7,
    'Cross_Above_20MA':5,'Fell_Below_20MA':5, 'Cross_Above_50MA':10,'Fell_Below_50MA':10,
    'MACD_Zero_Cross_Buy':12,'MACD_Zero_Cross_Sell':12, 'Gap_Up':3,'Gap_Down':3,
    'Pullback_123_Bull':7,'Pullback_123_Bear':7, 'Setup_180_Bull':7,'Setup_180_Bear':7,
    'Expansion_BO':10,'Expansion_BD':10, 'Pocket_Pivot':10,
}

SIGNAL_HIERARCHY = {
    'candle_bull': ['Morning_Star','Bullish_Engulfing','Hammer'],
    'candle_bear': ['Evening_Star','Bearish_Engulfing','Shooting_Star'],
    'ma_cross_bull': ['Cross_Above_200MA','Cross_Above_50MA','Cross_Above_20MA'],
    'ma_cross_bear': ['Fell_Below_200MA','Fell_Below_50MA','Fell_Below_20MA'],
    'cooper_bull': ['Expansion_BO','Pullback_123_Bull','Setup_180_Bull'],
    'cooper_bear': ['Expansion_BD','Pullback_123_Bear','Setup_180_Bear'],
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
# 캐싱 및 데이터 처리 (YFinance)
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
            f"Days to Cover (Short Ratio): {_get('shortRatio', 'float')}",
            f"Trailing EPS: {_get('trailingEps', 'currency')}",
            f"P/E Ratio: {_get('trailingPE', 'float')}",
            f"Price-to-Sales (P/S): {_get('priceToSalesTrailing12Months', 'float')}",
            f"Price-to-Book (P/B): {_get('priceToBook', 'float')}",
            f"PEG Ratio: {_get('pegRatio', 'float')}",
            f"52 Week High: {_get('fiftyTwoWeekHigh', 'currency')}",
            f"52 Week Low: {_get('fiftyTwoWeekLow', 'currency')}",
            f"Average Volume: {_get('averageVolume', 'large')}"
        ]
        return "\n".join(funds)
    except Exception:
        return "펀더멘탈 데이터를 불러올 수 없습니다."

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
    return detect_all_signals(compute_indicators(df))

# ──────────────────────────────────────────
# 핵심 기술 지표 계산 엔진
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

def compute_obv(c,v): return (v*np.sign(c.diff()).fillna(0)).cumsum()

def compute_macd(c, f=12, s=26, sig=9):
    ml=c.ewm(span=f,adjust=False).mean()-c.ewm(span=s,adjust=False).mean()
    sl=ml.ewm(span=sig,adjust=False).mean()
    return ml,sl,ml-sl

def detect_pivot_div(price,osc,lb=60,pw=5,os_lim=None,ob_lim=None):
    n=len(price); pv,ov=price.values,osc.values; half=pw
    p_lo,p_hi=[],[]
    for i in range(2*half,n):
        c=i-half; w=pv[i-2*half:i+1]
        if pv[c]==w.min(): p_lo.append((i,c))
        if pv[c]==w.max(): p_hi.append((i,c))
    bd=pd.Series(False,index=price.index); brd=pd.Series(False,index=price.index)
    hb=pd.Series(False,index=price.index); hbr=pd.Series(False,index=price.index)
    for idx in range(1,len(p_lo)):
        ci,pi=p_lo[idx]; cj,pj=p_lo[idx-1]
        if not (pw*2<=(pi-pj)<=lb): continue
        if (os_lim is None or ov[pi]<=os_lim) and pv[pi]<pv[pj] and ov[pi]>ov[pj]: bd.iloc[ci]=True
        if pv[pi]>pv[pj] and ov[pi]<ov[pj]: hb.iloc[ci]=True
    for idx in range(1,len(p_hi)):
        ci,pi=p_hi[idx]; cj,pj=p_hi[idx-1]
        if not (pw*2<=(pi-pj)<=lb): continue
        if (ob_lim is None or ov[pi]>=ob_lim) and pv[pi]>pv[pj] and ov[pi]<ov[pj]: brd.iloc[ci]=True
        if pv[pi]<pv[pj] and ov[pi]>ov[pj]: hbr.iloc[ci]=True
    return bd,brd,hb,hbr

def compute_keltner(h,l,c,el=20,al=10,m=1.5):
    mid=c.ewm(span=el,adjust=False).mean(); atr=compute_tr(h,l,c).rolling(al).mean()
    return mid+atr*m,mid,mid-atr*m

def detect_ttm_squeeze(bbu,bbl,kcu,kcl,c,h,l,kcm):
    sq=(bbu<kcu)&(bbl>kcl); fire=(~sq)&sq.shift(1).fillna(False)
    momentum = c - ((h.rolling(20).max() + l.rolling(20).min()) / 2 + kcm) / 2
    mom_up = momentum > momentum.shift(1)
    mom_dn = momentum < momentum.shift(1)
    return sq, fire & (momentum>0) & mom_up, fire & (momentum<0) & mom_dn

def detect_volume_climax(c,o,v,wt1,atr,z_thresh=2.5):
    v_mean=v.rolling(20).mean(); v_std=v.rolling(20).std()
    v_z=(v-v_mean)/(v_std+1e-10)
    big=(c-o).abs()>atr*0.5
    ps=(v_z.shift(1)>z_thresh)&big.shift(1)
    buy=ps&(c.shift(1)<o.shift(1))&(wt1.shift(1)<-40)&(c>o)
    sell=ps&(c.shift(1)>o.shift(1))&(wt1.shift(1)>40)&(c<o)
    return buy,sell

def _detect_engulfing_pair(c,o,wt1,wt_t=20):
    body=(c-o).abs(); big=body>body.rolling(20).mean()*0.8
    pb=c.shift(1)<o.shift(1); pp=c.shift(1)>o.shift(1)
    bull=pb&(c>o)&(o<=c.shift(1))&(c>=o.shift(1))&big&(wt1<-wt_t)
    bear=pp&(c<o)&(o>=c.shift(1))&(c<=o.shift(1))&big&(wt1>wt_t)
    return bull,bear

def _detect_parabolic_pair(c,o,wt1,bbu,bbl,atr):
    bot=((wt1<-85)&(wt1>wt1.shift(1))&(c>o)&(c>c.shift(1)))|((c<bbl-atr*1.5)&(c>o))
    top=((wt1>85)&(wt1<wt1.shift(1))&(c<o)&(c<c.shift(1)))|((c>bbu+atr*1.5)&(c<o))
    return bot,top

# ──────────────────────────────────────────
# 🆕 신규 시그널 탐지 함수들
# ──────────────────────────────────────────
def detect_candlestick_patterns(c, o, h, l, wt1, atr):
    body = (c - o).abs()
    upper_shadow = h - pd.concat([c, o], axis=1).max(axis=1)
    lower_shadow = pd.concat([c, o], axis=1).min(axis=1) - l
    avg_body = body.rolling(20).mean()
    is_small = body < avg_body * 0.8

    hammer = (lower_shadow >= body * 2) & (upper_shadow <= body * 0.5) & is_small & (wt1 < -20) & (c >= o)
    shooting = (upper_shadow >= body * 2) & (lower_shadow <= body * 0.5) & is_small & (wt1 > 20) & (c <= o)
    
    d1b = (c.shift(2) < o.shift(2)) & (body.shift(2) > avg_body.shift(2))
    d2s = body.shift(1) < avg_body.shift(1) * 0.5
    d3b = (c > o) & (c > (o.shift(2) + c.shift(2)) / 2)
    morning = d1b & d2s & d3b & (wt1 < -15)
    
    d1u = (c.shift(2) > o.shift(2)) & (body.shift(2) > avg_body.shift(2))
    d3s = (c < o) & (c < (o.shift(2) + c.shift(2)) / 2)
    evening = d1u & d2s & d3s & (wt1 > 15)
    
    return hammer, shooting, morning, evening

def detect_ma_crossovers(c, ma20, ma50, ma200):
    sigs = {}
    for tag, ma in [('20MA', ma20), ('50MA', ma50), ('200MA', ma200)]:
        sigs[f'Cross_Above_{tag}'] = (c > ma) & (c.shift(1) <= ma.shift(1))
        sigs[f'Fell_Below_{tag}'] = (c < ma) & (c.shift(1) >= ma.shift(1))
    return sigs

def detect_bb_extra(c, bb_up, bb_low, bb_w, wt1):
    bw_m = bb_w.rolling(20).mean()
    widening = (bb_w > bb_w.shift(1)) & (bb_w.shift(1) < bw_m.shift(1))
    sq_end_bull = widening & (c > c.shift(1)) & (wt1 > wt1.shift(1))
    sq_end_bear = widening & (c < c.shift(1)) & (wt1 < wt1.shift(1))
    return sq_end_bull, sq_end_bear

def detect_gaps(c, o, h, l, atr):
    thr = atr * 0.5
    gu = (o > h.shift(1)) & ((o - h.shift(1)) > thr)
    gd = (o < l.shift(1)) & ((l.shift(1) - o) > thr)
    return gu, gd

def detect_123_pullback(h, l, c, adx, pdi, mdi):
    strong_b = (adx > 30) & (pdi > mdi)
    strong_s = (adx > 30) & (mdi > pdi)
    inside = (h < h.shift(1)) & (l > l.shift(1))
    ll1 = l < l.shift(1); ll2 = l.shift(1) < l.shift(2); ll3 = l.shift(2) < l.shift(3)
    three_ll = ll1 & ll2 & ll3
    two_ll_in = (ll1 & ll2 & inside.shift(2)) | (ll1 & inside.shift(1) & ll2.shift(1)) | (inside & ll1 & ll2)
    hh1 = h > h.shift(1); hh2 = h.shift(1) > h.shift(2); hh3 = h.shift(2) > h.shift(3)
    three_hh = hh1 & hh2 & hh3
    two_hh_in = (hh1 & hh2 & inside.shift(2)) | (hh1 & inside.shift(1) & hh2.shift(1)) | (inside & hh1 & hh2)
    return strong_b & (three_ll | two_ll_in), strong_s & (three_hh | two_hh_in)

def detect_180_setup(c, o, h, l, ma10, ma50):
    dr = h - l + 1e-10
    cp = (c - l) / dr
    pp = (c.shift(1) - l.shift(1)) / (h.shift(1) - l.shift(1) + 1e-10)
    bull = (pp <= 0.25) & (cp >= 0.75) & (c > ma10) & (c > ma50)
    bear = (pp >= 0.75) & (cp <= 0.25) & (c < ma10) & (c < ma50)
    return bull, bear

def detect_expansion(h, l, c):
    dr = h - l
    mr9 = dr.rolling(9).max()
    h60 = h.rolling(60, min_periods=40).max()
    l60 = l.rolling(60, min_periods=40).min()
    xbo = (h >= h60) & (dr >= mr9)
    xbd = (l <= l60) & (dr >= mr9)
    return xbo, xbd

# ──────────────────────────────────────────
# 지표 통합 계산
# ──────────────────────────────────────────
def compute_indicators(df):
    c,h,l,v=df['Close'],df['High'],df['Low'],df['Volume']
    for ma in [5,10,20,50,100,125,200]: df[f'MA{ma}']=c.rolling(ma).mean()
    df['EMA8']=c.ewm(span=8,adjust=False).mean()
    df['EMA21']=c.ewm(span=21,adjust=False).mean()
    df['BB_Mid']=df['MA20']; s20=c.rolling(20).std()
    df['BB_Up'],df['BB_Low']=df['BB_Mid']+s20*2,df['BB_Mid']-s20*2
    df['BB_Width']=(df['BB_Up']-df['BB_Low'])/df['BB_Mid']
    df['Percent_B']=(c-df['BB_Low'])/(df['BB_Up']-df['BB_Low']+1e-10)
    df['ATR']=compute_tr(h,l,c).rolling(14).mean()
    
    wt1,wt2,wu,wd=compute_wavetrend(h,l,c)
    df['WT1'],df['WT2'],df['WT_Up'],df['WT_Down']=wt1,wt2,wu,wd
    df['RSI']=compute_rsi(c,14)
    df['StochK'],df['StochD']=compute_stoch_rsi(c)
    df['MFI']=compute_mfi(h,l,c,v,14)
    df['RSI_MFI']=compute_rsi_mfi(h,l,c,v,60)
    vwap=(c*v).rolling(20).sum()/(v.rolling(20).sum()+1e-10)
    df['VWAP_Osc']=((c-vwap)/(vwap+1e-10))*100
    df['ADX'],df['Plus_DI'],df['Minus_DI']=compute_adx(h,l,c)
    df['OBV']=compute_obv(c,v)
    df['KC_Upper'],df['KC_Mid'],df['KC_Lower']=compute_keltner(h,l,c)
    df['MACD_Line'],df['MACD_Signal'],df['MACD_Hist']=compute_macd(c)
    return df

def _deduplicate(df):
    for _cat, sigs in SIGNAL_HIERARCHY.items():
        for i, s in enumerate(sigs):
            if s not in df.columns: continue
            for higher in sigs[:i]:
                if higher in df.columns:
                    df[s] = df[s] & ~df[higher]
    return df

# ──────────────────────────────────────────
# 통합 시그널 탐지 & 시장 국면 동적 맵핑 (핵심 엔진)
# ──────────────────────────────────────────
def detect_all_signals(df):
    H,L,C,O,V=df['High'],df['Low'],df['Close'],df['Open'],df['Volume']
    e8,e21,m10,m20,m50,m200=df['EMA8'],df['EMA21'],df['MA10'],df['MA20'],df['MA50'],df['MA200']
    wt1,wt2,atr=df['WT1'],df['WT2'],df['ATR']

    # 1. 시장 국면 (Market Regime) 식별
    trend_up = (df['ADX'] > 20) & (df['Plus_DI'] > df['Minus_DI']) & (C > m50)
    trend_dn = (df['ADX'] > 20) & (df['Minus_DI'] > df['Plus_DI']) & (C < m50)
    df['Market_Regime'] = np.where(trend_up, 'Bull', np.where(trend_dn, 'Bear', 'Sideways'))

    htf1=(e8>e21)&(e21>e21.shift(5)); htf2=(C>m50)&(m50>m50.shift(10))
    wun=_recent(df['WT_Up'],2); wdn=_recent(df['WT_Down'],2)
    wur=_recent(df['WT_Up'],3); wdr=_recent(df['WT_Down'],3)
    vok=_volf(V,0.5)

    sb=trend_up; sbe=trend_dn
    xb=sb&(C>m200)&(m50>m50.shift(5)); xbe=sbe&(C<m200)&(m50<m50.shift(5))
    mfb=df['RSI_MFI']>-10; mfs=df['RSI_MFI']<10

    para_bot,para_top=_detect_parabolic_pair(C,O,wt1,df['BB_Up'],df['BB_Low'],atr)

    # ═══ 기존 MCB+ 시그널 ═══
    df['Green_Dot_T1']=wun&(wt1<=OS1)&(df['RSI']<30)&(df['MFI']<30)&(df['RSI_MFI']<0)&(~xbe)&vok
    df['Green_Dot_T2']=wun&(wt1<=OS1)&((df['RSI']<32)|(df['MFI']<32))&~df['Green_Dot_T1']&(~sbe)&vok
    _gd=df['Green_Dot_T1']|df['Green_Dot_T2']
    df['Red_Dot_T1']=wdn&(wt1>=OB1)&(df['RSI']>70)&(df['MFI']>70)&(df['RSI_MFI']>0)&(~xb)&vok
    df['Red_Dot_T2']=wdn&(wt1>=OB1)&((df['RSI']>68)|(df['MFI']>68))&~df['Red_Dot_T1']&(~sb)&vok
    _rd=df['Red_Dot_T1']|df['Red_Dot_T2']

    df['Blue_Diamond']=(wt2<=0)&wun&htf1&htf2&(~sbe)&mfb&vok
    df['Red_Diamond']=(wt2>=0)&wdn&~htf1&~htf2&(~sb)&mfs&vok
    df['Green_Circle']=wun&(wt1<=OS1)&~_gd&(~sbe)&vok&(df['RSI']<45)
    df['Red_Circle']=wdn&(wt1>=OB1)&~_rd&(~sb)&vok&(df['RSI']>55)

    bd,brd,hb,hbr=detect_pivot_div(C,wt1,60,5,OS1,OB1)
    bdr=_recent(bd,3); brdr=_recent(brd,3)
    rbd,rbrd,_,_=detect_pivot_div(C,df['RSI'],60,5,35,65)
    
    df['Gold_Dot']=df['Green_Dot_T1']&(wt1<=OS2)&bdr
    df['Blood_Diamond']=df['Red_Dot_T1']&(wt1>=OB2)&brdr
    df['Bull_Divergence']=bd&wur&~_gd&~df['Gold_Dot']&(~sbe)&vok
    df['Bear_Divergence']=brd&wdr&~_rd&(~sb)&vok
    df['RSI_Bull_Divergence']=rbd&(wt1<-20)&(~sbe)&vok&~bd
    
    sqo,sqb,sqs=detect_ttm_squeeze(df['BB_Up'],df['BB_Low'],df['KC_Upper'],df['KC_Lower'],C,H,L,df['KC_Mid'])
    df['Squeeze_On']=sqo
    df['Squeeze_Fire_Buy']=sqb&(~sbe)&vok
    df['Squeeze_Fire_Sell']=sqs&(~sb)&vok

    df['Volume_Climax_Buy'],df['Volume_Climax_Sell']=detect_volume_climax(C,O,V,wt1,atr)

    ax=(df['ADX']>20)&(df['ADX'].shift(1)<=20)
    df['ADX_Momentum_Buy']=ax&(df['Plus_DI']>df['Minus_DI'])&(wt1>wt2)&vok
    df['ADX_Momentum_Sell']=ax&(df['Minus_DI']>df['Plus_DI'])&(wt1<wt2)&vok

    df['Bullish_Engulfing'],df['Bearish_Engulfing']=_detect_engulfing_pair(C,O,wt1)
    df['Bullish_Engulfing']&=(~sbe)&vok; df['Bearish_Engulfing']&=(~sb)&vok

    gc=(m50>m200)&(m50.shift(1)<=m200.shift(1)); dc=(m50<m200)&(m50.shift(1)>=m200.shift(1))
    af=df['ADX']>15; vc=_volf(V,0.7)
    df['Golden_Cross']=gc&af&vc; df['Death_Cross']=dc&af&vc

    df['Parabolic_Top_Sell']=para_top
    df['Parabolic_Bottom_Buy']=para_bot

    # ═══ 신규 추가 시그널 ═══
    df['Hammer'], df['Shooting_Star'], df['Morning_Star'], df['Evening_Star'] = detect_candlestick_patterns(C, O, H, L, wt1, atr)
    
    ma_sigs = detect_ma_crossovers(C, m20, m50, m200)
    for k, v in ma_sigs.items(): df[k] = v

    df['BB_Squeeze_End_Bull'], df['BB_Squeeze_End_Bear'] = detect_bb_extra(C, df['BB_Up'], df['BB_Low'], df['BB_Width'], wt1)
    
    df['MACD_Zero_Cross_Buy'] = (df['MACD_Line'] > 0) & (df['MACD_Line'].shift(1) <= 0)
    df['MACD_Zero_Cross_Sell'] = (df['MACD_Line'] < 0) & (df['MACD_Line'].shift(1) >= 0)
    
    df['Gap_Up'], df['Gap_Down'] = detect_gaps(C, O, H, L, atr)
    df['NR7'], _ = detect_nr7(H, L)
    
    df['Pullback_123_Bull'], df['Pullback_123_Bear'] = detect_123_pullback(H, L, C, df['ADX'], df['Plus_DI'], df['Minus_DI'])
    df['Setup_180_Bull'], df['Setup_180_Bear'] = detect_180_setup(C, O, H, L, m10, m50)
    df['Expansion_BO'], df['Expansion_BD'] = detect_expansion(H, L, C)
    df['Pocket_Pivot'] = detect_pocket_pivot(C, O, V, m50, m200)

    for s, cd in COOLDOWN_MAP.items():
        if s in df.columns: df[s] = _cooldown(df[s], cd)
    _deduplicate(df)

    # 2. Confluence Score 계산 (다이나믹 스코어링)
    s_arr = np.zeros(len(df))
    for col, cfg in SIGNAL_REGISTRY.items():
        if col in df.columns:
            val = df[col].fillna(False).astype(float).values * cfg['w']
            if cfg['dir'] == 'buy': s_arr += val
            else: s_arr -= val
    
    s_arr += np.where(wt1<OS1, 1.0, 0) + np.where(wt1<OS2, 0.5, 0) - np.where(wt1>OB1, 1.0, 0) - np.where(wt1>OB2, 0.5, 0)
    adx_factor = np.clip((df['ADX'].values-20)/100, 0.0, 0.3)
    s_arr += np.where(trend_up & (s_arr>0), s_arr*adx_factor, 0)
    s_arr -= np.where(trend_dn & (s_arr<0), abs(s_arr)*adx_factor, 0)
    df['Confluence_Score'] = s_arr

    # 3. Action Label (시장 국면별 동적 임계값 적용)
    def get_action(row):
        score = row['Confluence_Score']
        regime = row['Market_Regime']
        if regime == 'Bull':
            if score >= 5.0: return 'Strong Buy'
            elif score >= 3.0: return 'Buy 1'
            elif score >= 1.5: return 'Buy 2'
            elif score <= -6.0: return 'Strong Sell'
            elif score <= -4.5: return 'Sell 1'
            elif score <= -3.0: return 'Sell 2'
        elif regime == 'Bear':
            if score <= -5.0: return 'Strong Sell'
            elif score <= -3.0: return 'Sell 1'
            elif score <= -1.5: return 'Sell 2'
            elif score >= 6.0: return 'Strong Buy'
            elif score >= 4.5: return 'Buy 1'
            elif score >= 3.0: return 'Buy 2'
        else: # Sideways
            if score >= 6.0: return 'Strong Buy'
            elif score >= 4.0: return 'Buy 1'
            elif score >= 2.5: return 'Buy 2'
            elif score <= -6.0: return 'Strong Sell'
            elif score <= -4.0: return 'Sell 1'
            elif score <= -2.5: return 'Sell 2'
        return 'Neutral'

    df['Action_Label'] = df.apply(get_action, axis=1)

    # 호환성 필드
    df['Strong_Bull'], df['Strong_Bear'] = sb, sbe
    df['_HTF1_Bull'], df['_HTF2_Bull'] = htf1, htf2
    df['Buy_Proximity'], df['Sell_Proximity'] = pd.Series(0, index=df.index), pd.Series(0, index=df.index) 
    df['overall_bias'] = np.where(s_arr >= 3.5, 'BUY', np.where(s_arr <= -3.5, 'SELL', 'NEUTRAL'))
    return df


# ──────────────────────────────────────────
# 통합 통계
# ──────────────────────────────────────────
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
    tgt={k:v['dir'] for k,v in SIGNAL_REGISTRY.items()}
    return {s:{**r,'direction':d} for s,d in tgt.items() if (r:=compute_signal_stats(dv, s, d)) and r['count']>0}


# ──────────────────────────────────────────
# 시각화 (Plotly) : 통합 동적 마커 렌더링
# ──────────────────────────────────────────
def build_chart(dc, ticker):
    mac={5:"#ff9900",10:"#ffb74d",20:'#f1c40f',50:'#e74c3c',100:'#9b59b6',125:'#3498db',200:'#2ecc71'}
    fig=make_subplots(rows=6,cols=1,shared_xaxes=True,vertical_spacing=0.035,
        row_heights=[.36,.07,.15,.12,.15,.15],
        subplot_titles=("Price & Action","Volume","WaveTrend Oscillator","Money Flow","MACD","Confluence Score"))

    enabled = st.session_state.get('enabled_signals', set(SIGNAL_REGISTRY.keys()))
    active_masks = {cn: dc[cn].copy() for cn in SIGNAL_REGISTRY.keys() if cn in dc.columns and cn in enabled}

    def _at(idx_pos):
        val = dc['ATR'].iloc[idx_pos]
        return val if not pd.isna(val) else dc['ATR'].median()

    # 마커 저장소
    b_str_x, b_str_y, b_str_txt = [], [], []
    b1_x, b1_y, b1_txt = [], [], []
    b2_x, b2_y, b2_txt = [], [], []
    s_str_x, s_str_y, s_str_txt = [], [], []
    s1_x, s1_y, s1_txt = [], [], []
    s2_x, s2_y, s2_txt = [], [], []
    candlestick_hover = []

    for i in range(len(dc)):
        day_buy_sigs, day_sell_sigs = [], []
        # 당일 발생한 시그널 내역 및 이유 수집
        for cn, mask in active_masks.items():
            if mask.iloc[i]:
                cfg = SIGNAL_REGISTRY[cn]
                sig_txt = f"{cfg['icon']} <b>{cfg['label']} ({cfg['kor']})</b><br>   └ <i>이유: {cfg['desc']}</i>"
                if cfg['dir'] == 'buy': day_buy_sigs.append(sig_txt)
                else: day_sell_sigs.append(sig_txt)

        act = dc['Action_Label'].iloc[i]
        regime = dc['Market_Regime'].iloc[i]
        conf = dc['Confluence_Score'].iloc[i]

        # 캔들 호버
        c_hover = ""
        if day_buy_sigs or day_sell_sigs:
            c_hover = "<br><br><b>🎯 당일 포착 시그널 (요약):</b><br>" + "<br>".join([s.split('<br>')[0] for s in day_buy_sigs + day_sell_sigs])
        candlestick_hover.append(c_hover)

        # 동적 액션 렌더링 세팅
        if act != 'Neutral':
            is_buy = 'Buy' in act
            y_base = dc['Low'].iloc[i] if is_buy else dc['High'].iloc[i]
            
            if 'Strong' in act:
                offset = _at(i) * 2.0
                clz, level_txt = ('#00E676', '🚀 STRONG BUY') if is_buy else ('#FF0000', '🚨 STRONG SELL')
            elif '1' in act:
                offset = _at(i) * 1.5
                clz, level_txt = ('#69F0AE', '🟢 BUY 1 (매수)') if is_buy else ('#FF5252', '🔴 SELL 1 (매도)')
            else:
                offset = _at(i) * 1.0
                clz, level_txt = ('#A5D6A7', '✅ BUY 2 (관심)') if is_buy else ('#EF9A9A', '⚠️ SELL 2 (주의)')

            y_val = y_base - offset if is_buy else y_base + offset
            
            txt = f"<span style='color:{clz}; font-size:14px;'><b>{level_txt} 판정</b></span><br>"
            txt += f"<b>📊 현재 시장 국면: {regime}</b> (총점: {conf:.1f})<br><br>"
            
            target_sigs = day_buy_sigs if is_buy else day_sell_sigs
            txt += "<br>".join(target_sigs) if target_sigs else f"<i>강력한 지표 결합에 의한 점수 충족</i>"

            idx = dc.index[i]
            if act == 'Strong Buy': b_str_x.append(idx); b_str_y.append(y_val); b_str_txt.append(txt)
            elif act == 'Buy 1': b1_x.append(idx); b1_y.append(y_val); b1_txt.append(txt)
            elif act == 'Buy 2': b2_x.append(idx); b2_y.append(y_val); b2_txt.append(txt)
            elif act == 'Strong Sell': s_str_x.append(idx); s_str_y.append(y_val); s_str_txt.append(txt)
            elif act == 'Sell 1': s1_x.append(idx); s1_y.append(y_val); s1_txt.append(txt)
            elif act == 'Sell 2': s2_x.append(idx); s2_y.append(y_val); s2_txt.append(txt)

    # 1. 캔들스틱 및 MA
    fig.add_trace(go.Candlestick(x=dc.index,open=dc['Open'],high=dc['High'],low=dc['Low'],close=dc['Close'],name="Price",
        increasing_line_color='#00E676',decreasing_line_color='#FF1744',
        increasing_fillcolor='rgba(0,230,118,0.8)',decreasing_fillcolor='rgba(255,23,68,0.8)',
        customdata=candlestick_hover,hovertemplate="O:%{open:.2f}<br>H:%{high:.2f}<br>L:%{low:.2f}<br>C:%{close:.2f}%{customdata}<extra></extra>"),row=1,col=1)

    for ma in [10,20,50,200]:
        fig.add_trace(go.Scatter(x=dc.index,y=dc[f'MA{ma}'],line=dict(color=mac[ma],width=1.2),name=f'{ma}MA',hovertemplate="%{y:.2f}"),row=1,col=1)
    for nm,col,clr,dash in [('EMA8','EMA8','#00FFFF','dot'),('EMA21','EMA21','#FF69B4','dot')]:
        fig.add_trace(go.Scatter(x=dc.index,y=dc[col],line=dict(color=clr,width=1.5,dash=dash),name=nm,hovertemplate="%{y:.2f}"),row=1,col=1)
    
    fig.add_trace(go.Scatter(x=dc.index,y=dc['BB_Up'],line=dict(color='gray',width=1,dash='dot'),name='BB↑',hovertemplate="%{y:.2f}"),row=1,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['BB_Low'],line=dict(color='gray',width=1,dash='dot'),name='BB↓',
        fill='tonexty',fillcolor='rgba(128,128,128,0.07)',hovertemplate="%{y:.2f}"),row=1,col=1)

    # 🌟 NEW 마커 렌더링
    fig.add_trace(go.Scatter(x=b_str_x, y=b_str_y, mode='markers', marker=dict(symbol='star-triangle-up', size=22, color='#00E676', line=dict(width=2,color='white')), customdata=b_str_txt, hovertemplate="%{customdata}<extra></extra>", name="Strong Buy"), row=1, col=1)
    fig.add_trace(go.Scatter(x=b1_x, y=b1_y, mode='markers', marker=dict(symbol='triangle-up', size=16, color='#69F0AE', line=dict(width=1,color='white')), customdata=b1_txt, hovertemplate="%{customdata}<extra></extra>", name="Buy 1"), row=1, col=1)
    fig.add_trace(go.Scatter(x=b2_x, y=b2_y, mode='markers', marker=dict(symbol='triangle-up', size=10, color='#A5D6A7'), customdata=b2_txt, hovertemplate="%{customdata}<extra></extra>", name="Buy 2"), row=1, col=1)
    
    fig.add_trace(go.Scatter(x=s_str_x, y=s_str_y, mode='markers', marker=dict(symbol='star-triangle-down', size=22, color='#FF0000', line=dict(width=2,color='white')), customdata=s_str_txt, hovertemplate="%{customdata}<extra></extra>", name="Strong Sell"), row=1, col=1)
    fig.add_trace(go.Scatter(x=s1_x, y=s1_y, mode='markers', marker=dict(symbol='triangle-down', size=16, color='#FF5252', line=dict(width=1,color='white')), customdata=s1_txt, hovertemplate="%{customdata}<extra></extra>", name="Sell 1"), row=1, col=1)
    fig.add_trace(go.Scatter(x=s2_x, y=s2_y, mode='markers', marker=dict(symbol='triangle-down', size=10, color='#EF9A9A'), customdata=s2_txt, hovertemplate="%{customdata}<extra></extra>", name="Sell 2"), row=1, col=1)

    # 2. 하단 서브플롯
    br=dc['Close']<dc['Open']
    fig.add_trace(go.Bar(x=dc.index,y=dc['Volume'],
        marker_color=np.where(br,'rgba(255,23,68,0.6)','rgba(0,230,118,0.6)').tolist(), name="Volume",opacity=0.8),row=2,col=1)

    fig.add_trace(go.Scatter(x=dc.index,y=dc['WT1'],line=dict(color='#00E676',width=2),name="WT1"),row=3,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['WT2'],line=dict(color='#FF1744',width=1.5,dash='dot'),name="WT2"),row=3,col=1)
    wd=dc['WT1']-dc['WT2']
    fig.add_trace(go.Bar(x=dc.index,y=wd,marker_color=np.where(wd>=0,'#00E676','#FF1744').tolist(),name="WT Hist",opacity=0.3),row=3,col=1)
    for lv,c_color,d in [(OB2,'#ff3333','dash'),(OB1,'#ff3333','solid'),(0,'gray','dot'),(OS1,'#00bfff','solid'),(OS2,'#00bfff','dash')]:
        fig.add_hline(y=lv,line_dash=d,line_color=c_color,line_width=1,row=3,col=1)

    rmfi=dc['RSI_MFI']
    fig.add_trace(go.Bar(x=dc.index,y=rmfi,marker_color=np.where(rmfi>=0,'#3ee145','#ff3d2e').tolist(), name="Money Flow",opacity=0.7),row=4,col=1)
    fig.add_hline(y=0,line_dash="solid",line_color="gray",line_width=1,row=4,col=1)

    fig.add_trace(go.Scatter(x=dc.index,y=dc['MACD_Line'],line=dict(color='#29B6F6',width=1.5),name="MACD"),row=5,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['MACD_Signal'],line=dict(color='#FFA726',width=1.5),name="Signal"),row=5,col=1)
    mh=dc['MACD_Hist']
    fig.add_trace(go.Bar(x=dc.index,y=mh,marker_color=np.where(mh>=0,'#26A69A','#EF5350').tolist(),name="Hist",opacity=0.7),row=5,col=1)
    fig.add_hline(y=0,line_color="#444444",line_width=1,row=5,col=1)

    conf=dc['Confluence_Score']
    fig.add_trace(go.Bar(x=dc.index,y=conf,
        marker_color=np.where(conf>=3.5,'#00E676',np.where(conf<=-3.5,'#FF1744','#FFC107')).tolist(), name="Conf Score",opacity=0.8),row=6,col=1)
    for lv,c_color,d in [(6.0,'#00E676','dash'),(-6.0,'#FF1744','dash'),(3.0,'#00E676','dot'),(-3.0,'#FF1744','dot'),(0,'gray','solid')]:
        fig.add_hline(y=lv,line_dash=d,line_color=c_color,line_width=1 if d=='solid' else .8,row=6,col=1)

    fig.update_layout(
        yaxis_title="Price",yaxis2_title="Vol",yaxis3_title="WT", yaxis4_title="MF",yaxis5_title="MACD",yaxis6_title="Conf",
        template="plotly_dark",paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=2,r=2,t=40,b=2),height=1200,showlegend=True,hovermode="x unified",
        hoverlabel=dict(bgcolor="rgba(14,17,23,0.95)",font_size=12,font_family="Pretendard",bordercolor="#2D333B"),
        legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="center",x=0.5, font=dict(size=9.5,color='#CCC',family='Pretendard'),bgcolor='rgba(0,0,0,0)'))
    for i in range(1,7):
        ya=f'yaxis{i}' if i>1 else 'yaxis'
        fig.update_layout(**{ya:dict(gridcolor='rgba(45,51,59,0.5)',gridwidth=1, zerolinecolor='rgba(60,63,70,0.6)',zerolinewidth=1, title_font=dict(size=11,color='#777'),tickfont=dict(size=10,color='#888'))})
    fig.update_xaxes(rangeslider_visible=False, showspikes=True,spikecolor="#667eea",spikemode="across",spikethickness=1,spikedash="dot", gridcolor='rgba(45,51,59,0.5)',gridwidth=1,tickfont=dict(size=10,color='#888'))
    fig.update_yaxes(showspikes=True,spikecolor="#667eea",spikemode="across",spikethickness=1,spikedash="dot")
    return fig

# ──────────────────────────────────────────
# 메타데이터 + AI 프롬프트 생성
# ──────────────────────────────────────────
def build_metadata(dc,dv,ticker):
    lat = dc.iloc[-1]
    prev = dc.iloc[-2] if len(dc)>=2 else lat
    pc=lat['Close']-prev['Close']; pp=pc/prev['Close']*100
    
    cf=float(lat['Confluence_Score'])
    regime=lat['Market_Regime']
    act=lat['Action_Label']
    
    recent=[]
    for ir,row in dc.tail(15).iterrows():
        ds=ir.strftime('%m/%d')
        for col,cfg in SIGNAL_REGISTRY.items():
            if row.get(col,False): recent.append((cfg['icon'],cfg['label'],ds,cfg['dir']))
            
    return {
        'ticker':ticker.upper(),'price':lat['Close'],'price_change':pc,'price_change_pct':pp,
        'volume':lat['Volume'],'avg_volume':dc['Volume'].rolling(20).mean().iloc[-1],
        'wt1':float(lat['WT1']),'wt2':float(lat['WT2']),'rsi':float(lat['RSI']),'mfi':float(lat['MFI']),
        'stochk':float(lat['StochK']),'stochd':float(lat['StochD']),
        'vwap_osc':float(lat['VWAP_Osc']),'mf_area':float(lat['RSI_MFI']),
        'atr':float(lat['ATR']),'atr_pct':float(lat['ATR'])/float(lat['Close'])*100,
        'adx':float(lat['ADX']),'plus_di':float(lat['Plus_DI']),'minus_di':float(lat['Minus_DI']),
        'confluence_score':cf, 'trend_regime':regime, 'action_label':act,
        'recent_signals':recent,'all_signal_stats':compute_all_stats(dv),
        'last_date':dc.index[-1].strftime('%Y-%m-%d'),
        'macd_line':float(lat.get('MACD_Line',0)),'macd_hist':float(lat.get('MACD_Hist',0)),
    }

def build_prompt_text(dc,meta):
    lat=dc.iloc[-1]; rd=dc.tail(60)
    ps=", ".join([f"'{d.strftime('%Y-%m-%d')}:{r['Close']:.2f}'" for d,r in rd.iterrows()])
    
    sl=[]
    for ir,row in dc.tail(30).iterrows():
        dd=ir.strftime('%Y-%m-%d')
        for k,v in SIGNAL_REGISTRY.items():
            if row.get(k,False): sl.append(f"{v['icon']} {v['label']} {dd}")
    st_text="\n".join(sl) if sl else "최근 30일 내 시그널 없음"
    
    inds=(f"WT1={lat['WT1']:.1f},WT2={lat['WT2']:.1f},RSI={lat['RSI']:.1f},MFI={lat['MFI']:.1f},"
        f"StK={lat['StochK']:.1f},ADX={lat['ADX']:.1f},+DI={lat['Plus_DI']:.1f},-DI={lat['Minus_DI']:.1f},"
        f"MACD H={meta['macd_hist']:.3f}, Conf={meta['confluence_score']:.1f}, Trend={meta['trend_regime']}, Action={meta['action_label']}")
    
    stats=meta.get('all_signal_stats',{})
    st_txt=""
    if stats:
        lines=[]
        for sn,sv in sorted(stats.items(),key=lambda x:x[1]['count'],reverse=True)[:15]:
            wr=sv.get('2d_winrate'); avg=sv.get('2d_avg')
            if wr is not None: lines.append(f"  {sn}:{sv['count']}회,2일승률{wr:.0f}%,평균주가변동{avg:+.1f}%")
        if lines: st_txt="\n📌 [백테스트(2년,상위15)]\n"+"\n".join(lines)
    return f"{ps}\n\n📌 [지표 요약]\n{inds}\n\n📌 [최근 시그널]\n{st_text}{st_txt}"

def build_ai_prompt(ticker,phist,fundamentals):
    return f"""━━━━━━━━━━━━━
【 🎯 Role & Persona 】
━━━━━━━━━━━━━
당신은 월스트리트 20년+ 경력 베테랑 주식 애널리스트이자 펀드 매니저입니다.
기술적 분석과 시장 심리 파악에 탁월하며, 시장 국면(Market Regime)과 다이나믹 스코어링 시스템을 활용한 리스크 관리에 정통합니다.

---
━━━━━━━━━━━━━
【 📥 Input Data 】
━━━━━━━━━━━━━
[티커: {ticker}]
📌 [주가 + 기술적 지표 + 시그널 백테스트 요약]
{phist}
📌 [YFinance 펀더멘탈]
{fundamentals}

---
━━━━━━━━━━━━━
【 📄 Output Format (아래 양식을 반드시 지켜 작성) 】
━━━━━━━━━━━━━
# 🚦 {ticker} 심층 퀀트 리포트
[🔵/🔴/🟠] [{ticker}] 분석: [핵심 한 줄]

---
### 🚦 시장 국면 및 액션 판정
* 현재 시장 국면: [Bull/Bear/Sideways 중 택1 + 부연설명]
* 🔥 통합 Score: [점수]
* 🎯 최종 판정(Action): [Strong Buy/Buy/Sell 등]
> 해석: [위 판정이 나온 이유를 1~2문장 해석]

---
### 주가 및 거래량 분석
* 현재 상태: [과매수/과매도, ADX 기반 추세 강도]
* 거래량 해석: [스마트 머니 유입/이탈]  [긍정:🔵/부정:🔴/중간:🟠]
> 종합 해석: [🔵/🔴/🟠] [종합 판단]

---
### 장중 기술적 지표
[식별된 기술적 패턴 이름]
* 상태: [패턴 설명. ATR 기반 예상 변동]
* 역사적 유사패턴: [백테스트 기반 승률/수익률]

---
### 파생 심리 및 공매도 현황
* 공매도 및 숏스퀴즈 가능성: [Short % Float 분석]

---
### 🔮 트레이딩 전략 (ATR 기반)
* **공격적 매수/공매도 구간:** [가격대]
* **손절(Stop-loss):** [가격] (현재가 +- ATR*1.5)
* **목표가:** 1차 [가격], 2차 [가격]

### 주가 예측 (다음 거래일)
[🔵/🔴/🟠] 예상: [방향] · 근거: [...]
"""

# ──────────────────────────────────────────
# UI 렌더 및 앱 실행부
# ──────────────────────────────────────────
def render_price_header(m):
    # 이전 버전(V10) 데이터와 호환되도록 .get() 방식으로 안전하게 값을 가져옵니다.
    chg = m.get('price_change', 0)
    cp = m.get('price_change_pct', 0)
    cc = 'price-change-up' if chg >= 0 else 'price-change-down'
    ci = '▲' if chg >= 0 else '▼'
    
    tr = m.get('trend_regime', 'NEUTRAL')
    # action_label이 없으면 과거 데이터의 overall_bias를, 그것도 없으면 Neutral을 표기합니다.
    act = m.get('action_label', m.get('overall_bias', 'Neutral'))
    
    st.markdown(f"""<div class="price-header">
        <div style="display:flex;justify-content:space-between;align-items:center">
            <div><p class="price-label">🚦 {m.get('ticker', 'UNKNOWN')} · {m.get('last_date', '')} · <b>{tr}</b> · <span style="color:#00E5FF;font-weight:700">Action: {act}</span></p>
            <p class="price-big" style="color:#FAFAFA">${m.get('price', 0):.2f}
                <span class="{cc}" style="font-size:1rem;margin-left:8px">
                    {ci} {abs(chg):.2f} ({abs(cp):.2f}%)</span></p></div>
            <div style="text-align:right"><p class="price-label">Conf Score / ATR</p>
            <p style="color:#FFC107;font-size:1.1rem;font-weight:600;margin:0">
                ★ {m.get('confluence_score', 0):.1f} / ${m.get('atr', 0):.2f}</p></div></div>
        </div>""", unsafe_allow_html=True)

def render_signals(m):
    sigs = m['recent_signals']
    if not sigs:
        st.markdown("""<div class="signal-card signal-card-neutral"><p style="margin:0;color:#FFC107;font-weight:600">🟠 최근 15일 내 시그널 없음</p></div>""",unsafe_allow_html=True)
        return
    dg = OrderedDict()
    for icon,lbl,ds,side in sigs: dg.setdefault(ds,[]).append((icon,lbl,side))
    alls = m.get('all_signal_stats',{})
    for ds in reversed(dg):
        group = dg[ds]
        bc = sum(1 for _,_,s in group if s=='buy')
        sc_count = sum(1 for _,_,s in group if s=='sell')
        ct = 'signal-card-buy' if bc>sc_count else ('signal-card-sell' if sc_count>bc else 'signal-card-neutral')
        parts = []
        for i,l,s in group:
            cn = "ind-bullish" if s=="buy" else "ind-bearish"
            sh = ""
            for sn,sv in alls.items():
                if SIGNAL_REGISTRY.get(sn,{}).get('label')==l:
                    if sv.get('2d_winrate') is not None: sh = f" ({sv['2d_winrate']:.0f}%)"
                    break
            parts.append(f'<span class="indicator-mini {cn}">{i} {l}{sh}</span>')
        st.markdown(f"""<div class="signal-card {ct}">
            <div style="display:flex;justify-content:space-between;align-items:center">
                <span style="font-weight:700;font-size:.9rem;color:#FAFAFA">📅 {ds}</span>
                <span style="color:#888;font-size:.75rem">{len(group)}개</span></div>
            <div style="margin-top:6px;display:flex;gap:4px;flex-wrap:wrap">{" ".join(parts)}</div></div>""",unsafe_allow_html=True)

def render_stats(m):
    with st.expander("📊 2년 백테스트 (진입: 다음날 시가, 청산: 2일 후 종가)", expanded=True):
        alls=m.get('all_signal_stats',{})
        if not alls: st.caption("통계 없음"); return
        def _side(title, data, is_sell=False):
            st.markdown(f"##### {title}")
            for sn,sv in sorted(data.items(),key=lambda x:x[1]['count'],reverse=True):
                wr, av = sv.get('2d_winrate'), sv.get('2d_avg')
                if wr is None: continue
                kor_label = SIGNAL_REGISTRY.get(sn,{}).get('kor',sn)
                c = '#00E676' if wr>50 else ('#FFC107' if wr>40 else '#FF1744')
                lb = f"승률 <span style='color:{c}'>**{wr:.0f}%**</span>"
                av_c = '#00E676' if (av<0 if is_sell else av>0) else '#FF1744'
                av_text = f"<span style='color:{av_c}'>**{abs(av):.1f}% {'하락' if is_sell else '상승'}**</span>"
                ic = SIGNAL_REGISTRY.get(sn,{}).get('icon','')
                st.markdown(f"<span style='font-size:.85rem'>{ic} **{kor_label}** ({sv['count']}회) · {lb} · 평균 변동: {av_text}</span>",unsafe_allow_html=True)

        c1,c2=st.columns(2)
        with c1: _side("🟢 BUY 시그널",{k:v for k,v in alls.items() if v['direction']=='buy'}, False)
        with c2: _side("🔴 SELL 시그널",{k:v for k,v in alls.items() if v['direction']=='sell'}, True)

def analyze(ticker,chart_days=252,refresh=False):
    try:
        ts = int(time.time()) if refresh else None
        df = compute_and_cache(ticker,ts)
        if df is None or df.empty: return None,"주가 데이터 없음",None
        dv = df.dropna(subset=['WT1','WT2']); dc = dv.tail(chart_days).copy()
        if dc.empty: return None,"차트 데이터 부족",None
        meta = build_metadata(dc, dv, ticker)
        fig = build_chart(dc, ticker)
        return fig, build_prompt_text(dc,meta), meta
    except Exception as e: return None,f"로딩 실패:{e}",None

def render_analysis(msg):
    m,fig=msg.get('meta'),msg.get('fig')
    if m: render_price_header(m)
    if m or fig:
        t1,t2,t3,t4=st.tabs(["📊 정밀 차트 (Dynamic Markers)","🔔 발생 시그널","📈 백테스트 통계","🏢 기업 정보"])
        with t1:
            if fig: st.plotly_chart(fig,use_container_width=True,theme=None,config={'displaylogo':False})
        with t2:
            if m: render_signals(m)
        with t3:
            if m: render_stats(m)
        with t4:
            if m: render_company_details(m['ticker'])

with st.sidebar:
    st.markdown("## 🚦 CipherX")
    st.markdown("<p style='color:#888;font-size:.8rem'>시장 국면별 동적 스코어링 v11.0</p>",unsafe_allow_html=True)
    st.markdown("---")
    chart_period=st.radio("표시 기간",['3개월','6개월','1년','2년'],index=0,horizontal=True)
    chart_days={'3개월':63,'6개월':126,'1년':252,'2년':504}[chart_period]
    st.markdown("---")
    if st.button("🗑️ 대화 지우기",use_container_width=True,type="secondary"):
        for key in ['messages','pending_ai_ticker','pending_ai_prompt','last_ticker']:
            st.session_state[key]=[{"role":"assistant","type":"text","content":"안녕하세요! **CipherX v11.0** 입니다.\n\n분석할 티커명을 입력하세요."}] if key=='messages' else None
        st.rerun()

if 'messages' not in st.session_state:
    st.session_state.messages=[{"role":"assistant","type":"text","content":"안녕하세요! 🚦 **CipherX v11.0** 입니다.\n\n분석할 **티커명**을 입력하세요. 국면에 따라 Action 타점이 동적으로 변경됩니다."}]
for key in ['pending_ai_ticker','pending_ai_prompt','last_ticker']:
    if key not in st.session_state: st.session_state[key]=None
if 'enabled_signals' not in st.session_state:
    st.session_state['enabled_signals']=set(SIGNAL_REGISTRY.keys())

st.markdown("<h2 style='text-align:center;color:#fff;margin-bottom:20px'>🚦 CipherX V11</h2>",unsafe_allow_html=True)

if not st.session_state.last_ticker:
    cols=st.columns(4)
    quick_tickers=["NVDA","TSLA","AAPL","QQQ"]
    for idx,col in enumerate(cols):
        with col:
            if st.button(f"{quick_tickers[idx]}",use_container_width=True): st.session_state['quick_ticker']=quick_tickers[idx]

for i,msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"], avatar="✨" if msg["role"]=="assistant" else "🧑‍💻"):
        if msg.get("type")=="analysis":
            st.markdown(msg.get("content",""))
            render_analysis(msg)
            if msg.get("prompt"):
                with st.expander("📝 퀀트 프롬프트 원문 확인",expanded=False):
                    st.code(msg["prompt"],language="markdown")
                    st_copy_to_clipboard(msg["prompt"],before_copy_label="📋 복사",after_copy_label="✅ 복사됨!")
        elif msg.get("type")=="report":
            with st.expander(f"📊 {msg.get('ticker','')} AI 퀀트 리포트",expanded=True):
                st.markdown(msg["content"])
        else: st.markdown(msg.get("content",""))

def _run_ai():
    tp=st.session_state.pending_ai_ticker
    pp=st.session_state.pending_ai_prompt
    with st.chat_message("assistant",avatar="✨"):
        pb=st.progress(10,text="Gemini 모델 초기화 중...")
        try:
            model=genai.GenerativeModel('gemini-2.5-flash')
            collected_chunks=[]
            def gen():
                pb.progress(40,text="🚀 AI 리포트 생성 중...")
                for chunk in model.generate_content(pp,stream=True):
                    if chunk.text:
                        collected_chunks.append(chunk.text)
                        yield chunk.text
                pb.progress(100,text="✅ 퀀트 분석 완료!")
            with st.expander(f"📊 {tp.upper()} AI 퀀트 리포트",expanded=True): st.write_stream(gen())
            time.sleep(0.3); pb.empty()
            st.session_state.messages.append({"role":"assistant","type":"report","ticker":tp.upper(),"content":"".join(collected_chunks)})
            st.session_state.pending_ai_ticker=None; st.session_state.pending_ai_prompt=None
            st.rerun()
        except Exception as e: pb.empty(); st.error(f"AI 오류: {e}")

def process_ticker(tv,refresh=False):
    tv=tv.strip().upper()
    if not validate_ticker(tv):
        st.toast(f"⚠️ **{tv}** — 데이터를 찾을 수 없습니다.",icon="🔍"); return
    st.session_state.messages.append({"role":"user","type":"text","content":tv})
    st.session_state.last_ticker=tv
    with st.chat_message("assistant",avatar="✨"):
        with st.status(f"🌐 {tv} 퀀트 파이프라인 가동 중...",expanded=True) as status:
            fundamentals=fetch_fundamentals(tv)
            fig,phist,meta=analyze(tv,chart_days,refresh)
            if fig:
                prompt=build_ai_prompt(tv,phist,fundamentals)
                status.update(label=f"✅ {tv} 퀀트 분석 완료!",state="complete",expanded=False)
                st.session_state.messages.append({"role":"assistant","type":"analysis","ticker":tv,"content":f"✅ **{tv}** 분석이 완료되었습니다.","fig":fig,"meta":meta,"prompt":prompt})
                st.session_state.pending_ai_ticker=tv; st.session_state.pending_ai_prompt=prompt
            else: status.update(label=f"⚠️ {tv} 데이터 처리 실패",state="error",expanded=False)
        st.rerun()

if st.session_state.get('quick_ticker'):
    process_ticker(st.session_state.pop('quick_ticker'))
elif st.session_state.pending_ai_ticker and st.session_state.pending_ai_prompt:
    if st.button(f"🚀 {st.session_state.pending_ai_ticker.upper()} AI 퀀트 분석 시작", type="primary", use_container_width=True): _run_ai()

if ticker_input:=st.chat_input("미국 주식 티커를 입력하세요 (예: TSLA, AAPL)"): process_ticker(ticker_input)