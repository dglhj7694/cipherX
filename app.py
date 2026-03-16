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

# ──────────────────────────────────────────
# 🔧 개선1: initial_sidebar_state="collapsed" → 모바일/데스크톱 모두 닫힌 상태 DEFAULT
# ──────────────────────────────────────────
st.set_page_config(
    page_title="CipherX V8.5",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="collapsed"  # ✅ 개선1 핵심
)

# ──────────────────────────────────────────
# 🎨 CSS (UX & 리포트 폰트 최적화 + 사이드바 토글 개선)
# ──────────────────────────────────────────
st.markdown("""<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
html,body,[class*="css"]{font-family:'Pretendard','Noto Sans KR',sans-serif!important}
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

/* 헤더 배경은 투명하게 처리하되 버튼은 살려둠 */
header {
    background-color: transparent !important;
}

/* 닫힌 사이드바를 여는 화살표 버튼 강제 노출 및 최상단 배치 */
div[data-testid="collapsedControl"] {
    display: flex !important;
    z-index: 999999 !important;
}
            
/* ✅ 개선1: 사이드바 토글 버튼 스타일 */
section[data-testid="stSidebar"]{background-color:#0A0D12;border-right:1px solid #1E2127}
section[data-testid="stSidebar"] .stMarkdown p{color:#AAA!important}
section[data-testid="stSidebar"] [data-testid="stSidebarCollapsedControl"]{
    background:rgba(14,17,23,0.9)!important;border:1px solid #2D333B!important;border-radius:8px!important}
/* 모바일: 사이드바 오버레이 */
@media (max-width: 768px) {
    section[data-testid="stSidebar"]{z-index:999!important}
    .sidebar-toggle-btn{position:fixed;top:10px;left:10px;z-index:1000;
        background:rgba(22,26,34,0.95);border:1px solid #2D333B;border-radius:8px;
        padding:6px 12px;cursor:pointer;color:#FAFAFA;font-size:1.2rem}
}

div[data-testid="stExpanderDetails"] h1 { font-size: 1.5rem !important; margin-bottom: 0.5rem !important; padding-bottom: 0.3rem !important; border-bottom: 1px solid #2D333B; }
div[data-testid="stExpanderDetails"] h2 { font-size: 1.3rem !important; margin-top: 1.2rem !important; margin-bottom: 0.5rem !important; }
div[data-testid="stExpanderDetails"] h3 { font-size: 1.15rem !important; margin-top: 1.2rem !important; margin-bottom: 0.4rem !important; color: #82aaff !important; }
div[data-testid="stExpanderDetails"] p, div[data-testid="stExpanderDetails"] li { font-size: 0.95rem !important; line-height: 1.6 !important; color: #D0D7DE !important; margin-bottom: 0.5rem !important; }
div[data-testid="stExpanderDetails"] blockquote { font-size: 0.95rem !important; border-left-color: #667eea !important; color: #A0B2C6 !important; }
div[data-testid="stExpanderDetails"] table { font-size: 0.85rem !important; width: 100% !important; }
div[data-testid="stExpanderDetails"] th, div[data-testid="stExpanderDetails"] td { padding: 0.4rem 0.6rem !important; }
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
.bias-gauge-track{height:8px;border-radius:4px;margin:8px 0;
background:linear-gradient(90deg,#FF1744 0%,#FF1744 20%,#FFC107 35%,#888 50%,#FFC107 65%,#00E676 80%,#00E676 100%);position:relative}
.bias-gauge-needle{width:4px;height:16px;background:white;border-radius:2px;position:absolute;top:-4px;
transform:translateX(-50%);box-shadow:0 0 6px rgba(255,255,255,.5)}
div[data-testid="stTabs"] button{color:#AAA!important;font-weight:600!important}
div[data-testid="stTabs"] button[aria-selected="true"]{color:#667eea!important;border-bottom-color:#667eea!important}
</style>""", unsafe_allow_html=True)

# ──────────────────────────────────────────
# 🔧 시그널 레지스트리
# ──────────────────────────────────────────
_B, _S = 'buy', 'sell'
def _sig(w,d,icon,label,sym,sz,clr,base,atr_m,kor,desc):
    return {'w':w,'dir':d,'icon':icon,'label':label,'sym':sym,'sz':sz,'clr':clr,
            'base':base,'atr_m':atr_m,'kor':kor,'desc':desc}

SIGNAL_REGISTRY = {
    'Gold_Dot':              _sig(3.0,_B,'🏆','GOLD DOT','circle',18,'#FFD700','Low',-3.0,'최강 매수','RSI<30+MFI<30+WT1<-60+상승 다이버전스'),
    'Green_Dot_T1':          _sig(2.5,_B,'🟢','BUY T1','circle',16,'#00E676','Low',-2.5,'강한 매수','WT과매도교차+RSI<30+MFI<30+MF<0'),
    'Green_Dot_T2':          _sig(2.0,_B,'🟩','BUY T2','circle',13,'#69F0AE','Low',-2.2,'매수','WT과매도+RSI또는MFI<32'),
    'Blue_Diamond':          _sig(2.0,_B,'🔹','BLUE DIA','diamond',14,'#00bfff','Low',-1.8,'추세 매수','WT2≤0 상승교차+HTF강세'),
    'Green_Circle':          _sig(0.8,_B,'✅','BUY Circle','circle-open',11,'#00E676','Low',-1.2,'과매도 반등','WT과매도교차+RSI<45'),
    'Bull_Divergence':       _sig(2.0,_B,'📈','Bull Div','triangle-up',12,'#AA00FF','Low',-2.0,'상승 다이버전스','가격 저점↓ vs WT 저점↑'),
    'RSI_Bull_Divergence':   _sig(1.5,_B,'📊','RSI Bull Div','triangle-up',11,'#CE93D8','Low',-1.8,'RSI 상승 다이버전스','가격↓ vs RSI↑'),
    'Squeeze_Fire_Buy':      _sig(1.5,_B,'💥','Squeeze BUY','star-diamond',14,'#00FFFF','Low',-1.5,'스퀴즈 매수','TTM Squeeze 해소+모멘텀↑'),
    'Hidden_Bull_Div':       _sig(1.5,_B,'🔀','Hidden Bull','triangle-up',10,'#E040FB','Low',-1.6,'히든 상승 다이버전스','가격 저점↑ vs WT↓+WT<-25+거래량'),
    'Volume_Climax_Buy':     _sig(2.0,_B,'🌊','Vol Climax BUY','hexagram',14,'#00BCD4','Low',-2.8,'거래량 클라이맥스','3배 거래량+하락장대봉+WT과매도→반등'),
    'OBV_Div_Buy':           _sig(0.8,_B,'📊','OBV Div BUY','triangle-up',10,'#80DEEA','Low',-1.4,'OBV 다이버전스','OBV-가격↑ 다이버전스+WT<-30'),
    'ADX_Momentum_Buy':      _sig(1.5,_B,'🚀','ADX Ignition','arrow-up',11,'#76FF03','Low',-1.4,'ADX 점화','ADX>20돌파++DI>-DI'),
    'Bullish_Engulfing':     _sig(1.5,_B,'☀️','Bull Engulf','square',10,'#00E676','Low',-1.3,'상승 장악형','하락캔들 감싸는 상승캔들+WT<-20'),
    'Golden_Cross':          _sig(1.5,_B,'✨','Golden Cross','cross',12,'#FFD700','Low',-0.8,'골든 크로스','50MA>200MA+ADX>15'),
    'EMA_Pullback_Buy':      _sig(2.0,_B,'🎯','EMA Pullback','triangle-up',13,'#00BFA5','Low',-1.8,'EMA 눌림목','상승추세 EMA조정후 WT반등'),
    'Momentum_Ignition_Buy': _sig(2.5,_B,'🔥','Mom. Ignition','star-diamond',15,'#FF6D00','Low',-2.5,'모멘텀 점화','장대양봉>ATR×1.5+거래량>2.5배'),
    'SuperTrend_Buy':        _sig(1.5,_B,'📈','ST Flip Bull','arrow-up',12,'#00E5FF','Low',-1.5,'슈퍼트렌드 강세','SuperTrend 위로 돌파'),
    'VWAP_Bounce_Buy':       _sig(1.5,_B,'🏦','VWAP Bounce','triangle-up',11,'#00E5FF','Low',-1.3,'VWAP 반등','VWAP 복귀+WT교차'),
    'Parabolic_Bottom_Buy':  _sig(3.0,_B,'🧊','Parabolic Bot','diamond',16,'#00FFFF','Low',-3.0,'포물선 바닥','WT1<-85 꺾임+양봉'),
    'MACD_Cross_Buy':        _sig(1.0,_B,'〽️','MACD Cross','triangle-up',9,'#4CAF50','Low',-1.0,'MACD 골든크로스','MACD>시그널(0선 하방)'),
    'StochRSI_Cross_Buy':    _sig(0.8,_B,'🔄','StRSI Cross','circle-open',8,'#81C784','Low',-0.8,'StochRSI 매수교차','StochK>StochD(과매도)'),

    'Blood_Diamond':         _sig(3.0,_S,'🩸','BLOOD DIA','diamond',18,'#DC143C','High',3.0,'최강 매도','RSI>70+MFI>70+WT1>60+하락 다이버전스'),
    'Red_Dot_T1':            _sig(2.5,_S,'🔴','SELL T1','circle',16,'#FF1744','High',2.5,'강한 매도','WT과매수하락교차+RSI>70+MFI>70'),
    'Red_Dot_T2':            _sig(2.0,_S,'🟥','SELL T2','circle',13,'#FF5252','High',2.2,'매도','WT과매수+RSI또는MFI>68'),
    'Red_Diamond':           _sig(2.0,_S,'🔸','RED DIA','diamond',14,'#ff3333','High',1.8,'추세 매도','WT2≥0 하락교차+HTF약세'),
    'Red_Circle':            _sig(0.8,_S,'⛔','SELL Circle','circle-open',11,'#FF1744','High',1.2,'과매수 하락','WT과매수하락교차+RSI>55'),
    'Bear_Divergence':       _sig(2.0,_S,'📉','Bear Div','triangle-down',12,'#AA00FF','High',2.0,'하락 다이버전스','가격 고점↑ vs WT↓'),
    'RSI_Bear_Divergence':   _sig(1.5,_S,'📉','RSI Bear Div','triangle-down',11,'#CE93D8','High',1.8,'RSI 하락 다이버전스','가격↑ vs RSI↓'),
    'Squeeze_Fire_Sell':     _sig(1.5,_S,'🧨','Squeeze SELL','star-diamond',14,'#FF6600','High',1.5,'스퀴즈 매도','TTM Squeeze 해소+모멘텀↓'),
    'Hidden_Bear_Div':       _sig(1.5,_S,'🔁','Hidden Bear','triangle-down',10,'#E040FB','High',1.6,'히든 하락 다이버전스','가격 고점↓ vs WT↑+WT>25+거래량'),
    'Volume_Climax_Sell':    _sig(2.0,_S,'🌋','Vol Climax SELL','hexagram',14,'#FF5722','High',2.8,'거래량 클라이맥스','3배 거래량+상승장대봉+WT과매수→하락'),
    'OBV_Div_Sell':          _sig(0.8,_S,'🔻','OBV Div SELL','triangle-down',10,'#FFAB91','High',1.4,'OBV 다이버전스','OBV-가격↓ 다이버전스+WT>30'),
    'ADX_Momentum_Sell':     _sig(1.5,_S,'💨','ADX Down','arrow-down',11,'#FF3D00','High',1.4,'ADX 하락 점화','ADX>20돌파+-DI>+DI'),
    'Bearish_Engulfing':     _sig(1.5,_S,'🌑','Bear Engulf','x',10,'#D50000','High',1.3,'하락 장악형','상승캔들 감싸는 하락캔들+WT>20'),
    'Death_Cross':           _sig(1.5,_S,'☠️','Death Cross','cross',12,'#FF1744','High',0.8,'데드 크로스','50MA<200MA+ADX>15'),
    'SuperTrend_Sell':       _sig(2.0,_S,'📉','ST Flip Bear','arrow-down',12,'#FF1744','High',1.5,'슈퍼트렌드 약세','SuperTrend 하단선 하향 돌파'),
    'Parabolic_Top_Sell':    _sig(3.0,_S,'🌡️','Parabolic Top','diamond',16,'#FF0000','High',3.0,'포물선 천장','WT1>85 꺾임+음봉'),
    'EMA_Pullback_Sell':     _sig(2.0,_S,'🎯','EMA PB Sell','triangle-down',13,'#FF6E40','High',1.8,'EMA 되돌림 매도','하락추세 EMA반등후 WT재하락'),
    'Momentum_Ignition_Sell':_sig(2.5,_S,'💣','Mom. Ign Sell','star-diamond',15,'#D50000','High',2.5,'모멘텀 점화 매도','장대음봉>ATR×1.5+거래량>2.5배'),
    'VWAP_Reject_Sell':      _sig(1.5,_S,'🏛️','VWAP Reject','triangle-down',11,'#FF6E40','High',1.3,'VWAP 저항','VWAP 실패+WT교차'),
    'MACD_Cross_Sell':       _sig(1.0,_S,'〽️','MACD Dead','triangle-down',9,'#E57373','High',1.0,'MACD 데드크로스','MACD<시그널(0선 상방)'),
    'StochRSI_Cross_Sell':   _sig(0.8,_S,'🔄','StRSI Dead','circle-open',8,'#EF9A9A','High',0.8,'StochRSI 매도교차','StochK<StochD(과매수)'),
}

COMPOSITE_SIGNALS = {
    'Ultra_Buy':  _sig(0,_B,'⚡','ULTRA BUY','star',20,'#FFD700','Low',-3.5,'울트라 매수','Confluence≥6 또는 ≥5+동시3개'),
    'Strong_Buy': _sig(0,_B,'🔱','STRONG BUY','star',16,'#00E676','Low',-3.2,'스트롱 매수','Confluence 3.5~6'),
    'Ultra_Sell': _sig(0,_S,'🚨','ULTRA SELL','star',20,'#FF0000','High',3.5,'울트라 매도','Confluence≤-6 또는 ≤-5+동시3개'),
    'Strong_Sell':_sig(0,_S,'⚠️','STRONG SELL','star',16,'#FF1744','High',3.2,'스트롱 매도','Confluence -6~-3.5'),
}
ALL_CHART_SIGNALS = {**SIGNAL_REGISTRY, **COMPOSITE_SIGNALS}

OB1, OB2, OS1, OS2 = 53, 60, -53, -60
ST_MIN_BAR = 12

GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GEMINI_API_KEY)

COOLDOWN_MAP = {
    'Squeeze_Fire_Buy':5,'Squeeze_Fire_Sell':5, 'Bullish_Engulfing':5,'Bearish_Engulfing':5,
    'ADX_Momentum_Buy':10,'ADX_Momentum_Sell':10, 'EMA_Pullback_Buy':7,'EMA_Pullback_Sell':7,
    'Momentum_Ignition_Buy':10,'Momentum_Ignition_Sell':10, 'Parabolic_Top_Sell':5,'Parabolic_Bottom_Buy':5,
    'VWAP_Bounce_Buy':7,'VWAP_Reject_Sell':7, 'MACD_Cross_Buy':12,'MACD_Cross_Sell':12,
    'StochRSI_Cross_Buy':7,'StochRSI_Cross_Sell':7, 'RSI_Bull_Divergence':10,'RSI_Bear_Divergence':10,
}

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
# 지표 계산 엔진
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
    return sq, fire&(momentum>0), fire&(momentum<0)

def detect_volume_climax(c,o,v,wt1,atr,vm=3.0):
    avg=v.rolling(20).mean(); big=(c-o).abs()>atr*0.5
    ps=(v.shift(1)>avg.shift(1)*vm)&big.shift(1)
    return (ps&(c.shift(1)<o.shift(1))&(wt1.shift(1)<-40)&(c>o),
            ps&(c.shift(1)>o.shift(1))&(wt1.shift(1)>40)&(c<o))

def _detect_engulfing_pair(c,o,wt1,wt_t=20):
    body=(c-o).abs(); big=body>body.rolling(20).mean()*0.8
    pb=c.shift(1)<o.shift(1); pp=c.shift(1)>o.shift(1)
    bull=pb&(c>o)&(o<=c.shift(1))&(c>=o.shift(1))&big&(wt1<-wt_t)
    bear=pp&(c<o)&(o>=c.shift(1))&(c<=o.shift(1))&big&(wt1>wt_t)
    return bull,bear

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

def _detect_ema_pullback_pair(c,h,l,v,e8,e21,atr,wt1,wt2):
    vok=_volf(v,0.5); ar=atr/c
    results={}
    for d in ['buy','sell']:
        slope=e21>e21.shift(5) if d=='buy' else e21<e21.shift(5)
        trend=((e8>e21) if d=='buy' else (e8<e21))&slope
        side=(c>e21) if d=='buy' else (c<e21)
        if d=='buy':
            t=(l<=e8*(1+ar*0.15))&(l>=e21*(1-ar*0.25))
            tr=_recent(t,2); b=(c>=e8)&(c>c.shift(1))
            wok=(wt1>wt1.shift(1))&(wt1>wt2)&(wt1<60)
        else:
            t=(h>=e8*(1-ar*0.15))&(h<=e21*(1+ar*0.25))
            tr=_recent(t,2); b=(c<=e8)&(c<c.shift(1))
            wok=(wt1<wt1.shift(1))&(wt1<wt2)&(wt1>-60)
        results[d]=trend&side&tr&b&wok&vok
    return results['buy'],results['sell']

def _detect_mom_ignition_pair(c,o,v,bbu,bbl,atr,e8,e21,wt1):
    body=(c-o).abs(); bb=body>atr*1.5; hv=v>v.rolling(20).mean()*2.5
    buy=(c>o)&bb&hv&(c>bbu)&(e8>e21)&(wt1<50)
    sell=(c<o)&bb&hv&(c<bbl)&(e8<e21)&(wt1>-50)
    return buy,sell

def _detect_vwap_pair(c,vosc,wt1,wt2,v,atr):
    vok=_volf(v,0.7); ap=(atr/c*100).clip(0.3,3.0); dt=(ap*0.3).clip(0.3,1.5)
    buy=(vosc>0)&(vosc.shift(1)<-dt)&(wt1>wt2)&(wt1<30)&vok
    sell=(vosc<0)&(vosc.shift(1)>dt)&(wt1<wt2)&(wt1>-30)&vok
    return buy,sell

def _detect_parabolic_pair(c,o,wt1,bbu,bbl,atr):
    bot=((wt1<-85)&(wt1>wt1.shift(1))&(c>o)&(c>c.shift(1)))|((c<bbl-atr*1.5)&(c>o))
    top=((wt1>85)&(wt1<wt1.shift(1))&(c<o)&(c<c.shift(1)))|((c>bbu+atr*1.5)&(c<o))
    return bot,top

def compute_confluence(df, dw=5, df_=0.7):
    bm={k:v['w'] for k,v in SIGNAL_REGISTRY.items() if v['dir']=='buy'}
    sm={k:v['w'] for k,v in SIGNAL_REGISTRY.items() if v['dir']=='sell'}
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
    s+=np.where(wt1<OS1,1,0)+np.where(wt1<OS2,0.5,0)-np.where(wt1>OB1,1,0)-np.where(wt1>OB2,0.5,0)
    adx=df['ADX'].values; pdi=df['Plus_DI'].values; mdi=df['Minus_DI'].values
    bull_trend=(adx>25)&(pdi>mdi); bear_trend=(adx>25)&(mdi>pdi)
    s+=np.where(bull_trend&(s>0), s*0.1, 0)
    s+=np.where(bear_trend&(s<0), s*0.1, 0)
    df['Confluence_Score']=s
    df['Ultra_Buy']=(s>=6)|((s>=5)&(bc>=3))
    df['Ultra_Sell']=(s<=-6)|((s<=-5)&(sc>=3))
    df['Strong_Buy']=(s>=3.5)&(~df['Ultra_Buy'])
    df['Strong_Sell']=(s<=-3.5)&(~df['Ultra_Sell'])
    return s

def compute_proximity(wt1,wt2,rsi,mfi,rmfi,stk,macd_h,bb_w,sb,sbe):
    bp=pd.Series(0.0,index=wt1.index); sp=pd.Series(0.0,index=wt1.index)
    gap=(wt1-wt2).abs(); nc=gap<3
    cu=(wt1-wt2)>(wt1.shift(1)-wt2.shift(1)); cd=(wt1-wt2)<(wt1.shift(1)-wt2.shift(1))
    for cond,pts in [((wt1<-40)&nc,30),((wt1<-40)&cu&(gap<8),15),(wt1<OS2,20),
        ((wt1>=OS2)&(wt1<-40),10),(rsi<35,15),((rsi>=35)&(rsi<45),5),
        (mfi<35,15),((mfi>=35)&(mfi<45),5),(rmfi<-5,10),((rmfi>=-5)&(rmfi<0),5),
        (stk<20,10),((stk>=20)&(stk<35),5),(macd_h<0,3),(macd_h<macd_h.shift(1),2)]:
        bp+=np.where(cond,pts,0)
    for cond,pts in [((wt1>40)&nc,30),((wt1>40)&cd&(gap<8),15),(wt1>OB1,20),
        ((wt1<=OB1)&(wt1>40),10),(rsi>65,15),((rsi<=65)&(rsi>55),5),
        (mfi>65,15),((mfi<=65)&(mfi>55),5),(rmfi>5,10),((rmfi<=5)&(rmfi>0),5),
        (stk>80,10),((stk<=80)&(stk>65),5),(macd_h>0,3),(macd_h>macd_h.shift(1),2)]:
        sp+=np.where(cond,pts,0)
    bb_narrow=bb_w<bb_w.rolling(50).quantile(0.2)
    bp+=np.where(bb_narrow,5,0); sp+=np.where(bb_narrow,5,0)
    bp,sp=bp.clip(upper=100),sp.clip(upper=100)
    net=bp-sp
    return (pd.Series(np.where(net>=0,bp,bp*np.where(sbe,.4,.55)),index=wt1.index),
            pd.Series(np.where(net<=0,sp,sp*np.where(sb,.4,.55)),index=wt1.index))

def compute_bias(meta,htf1,htf2):
    sc=0.0
    for val,thr in [(meta['wt1'],[(-60,3),(-53,2),(0,1),(53,-1),(60,-2),(999,-3)]),
                     (meta['rsi'],[(-1,0),(30,2),(45,1),(55,0),(70,-1),(999,-2)]),
                     (meta['mfi'],[(-1,0),(30,2),(45,1),(55,0),(70,-1),(999,-2)])]:
        for t,p in thr:
            if val<=t: sc+=p; break
    mf=meta['mf_area']
    sc+=2 if mf<-5 else (1 if mf<0 else (-2 if mf>5 else (-1 if mf>0 else 0)))
    stk=meta.get('stochk',50)
    sc+=1.5 if stk<20 else (.5 if stk<35 else (-1.5 if stk>80 else (-.5 if stk>65 else 0)))
    sc+=(1 if htf1 else -1)+(1.5 if htf2 else -1.5)
    if sc>=8: return 'STRONG BUY',sc
    elif sc>=3: return 'BUY',sc
    elif sc>=-3: return 'NEUTRAL',sc
    elif sc>=-8: return 'SELL',sc
    else: return 'STRONG SELL',sc

def compute_signal_stats(df, col, direction, fwd=(5, 10, 20), mn=5):
    if col not in df.columns: return None
    mask = df[col].fillna(False).values.astype(bool)
    if mask.sum() < mn: return None
    st_res = {'count': int(mask.sum())}
    entry_price = df['Open'].shift(-1)
    for n in fwd:
        exit_price = df['Close'].shift(-(n + 1))
        pct_change = (exit_price - entry_price) / entry_price * 100
        if direction == 'sell':
            pct_change = -pct_change
        valid_returns = pct_change[mask].dropna()
        if len(valid_returns) >= mn:
            st_res[f'{n}d_avg'] = float(valid_returns.mean())
            st_res[f'{n}d_winrate'] = float((valid_returns > 0).sum() / len(valid_returns) * 100)
            st_res[f'{n}d_median'] = float(valid_returns.median())
        else:
            st_res[f'{n}d_avg'] = st_res[f'{n}d_winrate'] = st_res[f'{n}d_median'] = None
    return st_res

def compute_all_stats(dv):
    tgt={k:v['dir'] for k,v in SIGNAL_REGISTRY.items()}
    tgt.update({'Ultra_Buy':'buy','Strong_Buy':'buy','Ultra_Sell':'sell','Strong_Sell':'sell'})
    return {s:{**r,'direction':d} for s,d in tgt.items() if (r:=compute_signal_stats(dv, s, d)) and r['count']>0}

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
    atr22 = compute_tr(h,l,c).rolling(22).mean()
    df['Chandelier_Long'] = h.rolling(22).max() - atr22 * 3.0
    df['Chandelier_Short'] = l.rolling(22).min() + atr22 * 3.0
    df['SuperTrend'],df['ST_Direction']=compute_supertrend(h,l,c)
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

def detect_all_signals(df):
    H,L,C,O,V=df['High'],df['Low'],df['Close'],df['Open'],df['Volume']
    e8,e21,m50,m200=df['EMA8'],df['EMA21'],df['MA50'],df['MA200']
    wt1,wt2,atr=df['WT1'],df['WT2'],df['ATR']

    htf1=(e8>e21)&(e21>e21.shift(5)); htf2=(C>m50)&(m50>m50.shift(10))
    wun=_recent(df['WT_Up'],2); wdn=_recent(df['WT_Down'],2)
    wur=_recent(df['WT_Up'],3); wdr=_recent(df['WT_Down'],3)
    vok=_volf(V,0.5)

    sb=(df['ADX']>25)&(df['Plus_DI']>df['Minus_DI'])&(C>m50)
    sbe=(df['ADX']>25)&(df['Minus_DI']>df['Plus_DI'])&(C<m50)
    xb=sb&(C>m200)&(m50>m50.shift(5)); xbe=sbe&(C<m200)&(m50<m50.shift(5))
    mfb=df['RSI_MFI']>-10; mfs=df['RSI_MFI']<10

    para_bot,para_top=_detect_parabolic_pair(C,O,wt1,df['BB_Up'],df['BB_Low'],atr)
    st_fb=(df['ST_Direction']==-1)&(df['ST_Direction'].shift(1)==1)
    st_fb.iloc[:ST_MIN_BAR]=False; st_bo=_recent(st_fb,3)
    st_fb2=(df['ST_Direction']==1)&(df['ST_Direction'].shift(1)==-1)
    st_fb2.iloc[:ST_MIN_BAR]=False; st_bu=_recent(st_fb2,3)

    ssb=sb&(~para_top)&(~st_bo); ssx=xb&(~para_top)&(~st_bo)
    bsb=sbe&(~para_bot)&(~st_bu); bsx=xbe&(~para_bot)&(~st_bu)

    df['Green_Dot_T1']=wun&(wt1<=OS1)&(df['RSI']<30)&(df['MFI']<30)&(df['RSI_MFI']<0)&(~bsx)&vok
    df['Green_Dot_T2']=wun&(wt1<=OS1)&((df['RSI']<32)|(df['MFI']<32))&~df['Green_Dot_T1']&(~bsb)&vok
    _gd=df['Green_Dot_T1']|df['Green_Dot_T2']
    df['Red_Dot_T1']=wdn&(wt1>=OB1)&(df['RSI']>70)&(df['MFI']>70)&(df['RSI_MFI']>0)&(~ssx)&vok
    df['Red_Dot_T2']=wdn&(wt1>=OB1)&((df['RSI']>68)|(df['MFI']>68))&~df['Red_Dot_T1']&(~ssb)&vok
    _rd=df['Red_Dot_T1']|df['Red_Dot_T2']

    df['Blue_Diamond']=(wt2<=0)&wun&htf1&htf2&(~bsb)&mfb&vok
    df['Red_Diamond']=(wt2>=0)&wdn&~htf1&~htf2&(~ssb)&mfs&vok
    df['Green_Circle']=wun&(wt1<=OS1)&~_gd&(~bsb)&vok&(df['RSI']<45)
    df['Red_Circle']=wdn&(wt1>=OB1)&~_rd&(~ssb)&vok&(df['RSI']>55)

    bd,brd,hb,hbr=detect_pivot_div(C,wt1,60,5,OS1,OB1)
    bdr=_recent(bd,3); brdr=_recent(brd,3)
    rbd,rbrd,_,_=detect_pivot_div(C,df['RSI'],60,5,35,65)
    obd,obrd,_,_=detect_pivot_div(C,df['OBV'],60,5)

    df['Gold_Dot']=df['Green_Dot_T1']&(wt1<=OS2)&bdr
    df['Blood_Diamond']=df['Red_Dot_T1']&(wt1>=OB2)&brdr
    df['Bull_Divergence']=bd&wur&~_gd&~df['Gold_Dot']&(~bsb)&vok
    df['Bear_Divergence']=brd&wdr&~_rd&(~ssb)&vok
    df['RSI_Bull_Divergence']=rbd&(wt1<-20)&(~bsb)&vok&~bd
    df['RSI_Bear_Divergence']=rbrd&(wt1>20)&(~ssb)&vok&~brd
    vol_ok_hidden=_volf(V,0.7)
    df['Hidden_Bull_Div']=hb&(wt1<-25)&htf2&(~bsx)&vol_ok_hidden
    df['Hidden_Bear_Div']=hbr&(wt1>25)&~htf2&(~ssx)&vol_ok_hidden
    df['OBV_Div_Buy']=obd&(wt1<-30)&(~bsx)
    df['OBV_Div_Sell']=obrd&(wt1>30)&(~ssx)

    sqo,sqb,sqs=detect_ttm_squeeze(df['BB_Up'],df['BB_Low'],df['KC_Upper'],df['KC_Lower'],C,H,L,df['KC_Mid'])
    df['Squeeze_On']=sqo
    df['Squeeze_Fire_Buy']=sqb&(~bsb)&vok
    df['Squeeze_Fire_Sell']=sqs&(~ssb)&vok

    df['Volume_Climax_Buy'],df['Volume_Climax_Sell']=detect_volume_climax(C,O,V,wt1,atr)

    ax=(df['ADX']>20)&(df['ADX'].shift(1)<=20)
    df['ADX_Momentum_Buy']=ax&(df['Plus_DI']>df['Minus_DI'])&(wt1>wt2)&vok
    df['ADX_Momentum_Sell']=ax&(df['Minus_DI']>df['Plus_DI'])&(wt1<wt2)&vok

    df['Bullish_Engulfing'],df['Bearish_Engulfing']=_detect_engulfing_pair(C,O,wt1)
    df['Bullish_Engulfing']&=(~bsb)&vok; df['Bearish_Engulfing']&=(~ssb)&vok

    gc=(m50>m200)&(m50.shift(1)<=m200.shift(1)); dc=(m50<m200)&(m50.shift(1)>=m200.shift(1))
    af=df['ADX']>15; vc=_volf(V,0.7)
    df['Golden_Cross']=gc&af&vc; df['Death_Cross']=dc&af&vc

    df['EMA_Pullback_Buy'],df['EMA_Pullback_Sell']=_detect_ema_pullback_pair(C,H,L,V,e8,e21,atr,wt1,wt2)
    df['Momentum_Ignition_Buy'],df['Momentum_Ignition_Sell']=_detect_mom_ignition_pair(C,O,V,df['BB_Up'],df['BB_Low'],atr,e8,e21,wt1)

    df['SuperTrend_Buy']=st_fb2; df['SuperTrend_Sell']=st_fb

    vp=_volf(V,1.0)
    df['Parabolic_Top_Sell']=para_top&((df['WT_Down']|wdr)|((C<O)&(C<C.shift(1))))&vp
    df['Parabolic_Bottom_Buy']=para_bot&((df['WT_Up']|wur)|((C>O)&(C>C.shift(1))))&vp

    df['VWAP_Bounce_Buy'],df['VWAP_Reject_Sell']=_detect_vwap_pair(C,df['VWAP_Osc'],wt1,wt2,V,atr)

    ml,ms=df['MACD_Line'],df['MACD_Signal']
    df['MACD_Cross_Buy']=(ml>ms)&(ml.shift(1)<=ms.shift(1))&(ml<0)&(~bsb)&vok
    df['MACD_Cross_Sell']=(ml<ms)&(ml.shift(1)>=ms.shift(1))&(ml>0)&(~ssb)&vok
    df['StochRSI_Cross_Buy']=(df['StochK']>df['StochD'])&(df['StochK'].shift(1)<=df['StochD'].shift(1))&(df['StochK']<25)&(~bsb)&vok
    df['StochRSI_Cross_Sell']=(df['StochK']<df['StochD'])&(df['StochK'].shift(1)>=df['StochD'].shift(1))&(df['StochK']>75)&(~ssb)&vok

    for s,cd in COOLDOWN_MAP.items():
        if s in df.columns: df[s]=_cooldown(df[s],cd)

    compute_confluence(df)
    df['Buy_Proximity'],df['Sell_Proximity']=compute_proximity(wt1,wt2,df['RSI'],df['MFI'],df['RSI_MFI'],df['StochK'],df['MACD_Hist'],df['BB_Width'],sb,sbe)

    df['Strong_Bull'],df['Strong_Bear']=sb,sbe
    df['Parabolic_Blowoff']=para_top; df['Parabolic_Bottom_Raw']=para_bot
    df['ST_Bear_Override']=st_bo
    df['Sell_Shield_Overridden']=para_top|st_bo
    df['Buy_Shield_Overridden']=para_bot|st_bu
    df['_HTF1_Bull'],df['_HTF2_Bull']=htf1,htf2
    return df

# ──────────────────────────────────────────
# ✅ 개선3: Speedometer(속도계) 게이지 차트 빌더
# ──────────────────────────────────────────
def build_speedometer_gauges(meta):
    """Confluence Score + Overall Bias 속도계 게이지 차트 생성"""
    from plotly.subplots import make_subplots

    conf_score = meta.get('confluence_score', 0)
    bias_score = meta.get('bias_score', 0)
    bias_label = meta.get('overall_bias', 'NEUTRAL')

    # Confluence Score 색상 결정
    if conf_score >= 6:
        conf_color = "#00E676"
    elif conf_score >= 3.5:
        conf_color = "#69F0AE"
    elif conf_score <= -6:
        conf_color = "#FF1744"
    elif conf_score <= -3.5:
        conf_color = "#FF5252"
    else:
        conf_color = "#FFC107"

    # Bias Score 색상 결정
    bias_colors = {
        'STRONG BUY': '#00E676', 'BUY': '#69F0AE',
        'STRONG SELL': '#FF1744', 'SELL': '#FF5252', 'NEUTRAL': '#FFC107'
    }
    bias_color = bias_colors.get(bias_label, '#FFC107')

    fig = make_subplots(
        rows=1, cols=2,
        specs=[[{"type": "indicator"}, {"type": "indicator"}]],
        horizontal_spacing=0.08
    )

    # ✅ 좌측: Confluence Score 게이지
    fig.add_trace(go.Indicator(
        mode="gauge+number+delta",
        value=conf_score,
        number=dict(font=dict(size=28, color="#FAFAFA"), suffix=""),
        title=dict(text="<b>🔥 Confluence Score</b>", font=dict(size=13, color="#AAA")),
        gauge=dict(
            axis=dict(range=[-10, 10], tickwidth=2, tickcolor="#555",
                      dtick=2.5, tickfont=dict(size=10, color="#888")),
            bar=dict(color=conf_color, thickness=0.3),
            bgcolor="rgba(30,33,39,0.8)",
            borderwidth=2, bordercolor="#2D333B",
            steps=[
                dict(range=[-10, -6], color="rgba(255,23,68,0.25)"),
                dict(range=[-6, -3.5], color="rgba(255,82,82,0.15)"),
                dict(range=[-3.5, 3.5], color="rgba(255,193,7,0.10)"),
                dict(range=[3.5, 6], color="rgba(105,240,174,0.15)"),
                dict(range=[6, 10], color="rgba(0,230,118,0.25)"),
            ],
            threshold=dict(
                line=dict(color="white", width=3),
                thickness=0.8, value=conf_score
            ),
        ),
    ), row=1, col=1)

    # ✅ 우측: Overall Bias 게이지
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=bias_score,
        number=dict(font=dict(size=28, color="#FAFAFA"),
                     suffix=f"  {bias_label}", valueformat=".1f"),
        title=dict(text="<b>🧭 Overall Bias</b>", font=dict(size=13, color="#AAA")),
        gauge=dict(
            axis=dict(range=[-13, 13], tickwidth=2, tickcolor="#555",
                      dtick=3.25, tickfont=dict(size=10, color="#888")),
            bar=dict(color=bias_color, thickness=0.3),
            bgcolor="rgba(30,33,39,0.8)",
            borderwidth=2, bordercolor="#2D333B",
            steps=[
                dict(range=[-13, -8], color="rgba(255,23,68,0.30)"),
                dict(range=[-8, -3], color="rgba(255,82,82,0.15)"),
                dict(range=[-3, 3], color="rgba(255,193,7,0.10)"),
                dict(range=[3, 8], color="rgba(105,240,174,0.15)"),
                dict(range=[8, 13], color="rgba(0,230,118,0.30)"),
            ],
            threshold=dict(
                line=dict(color="white", width=3),
                thickness=0.8, value=bias_score
            ),
        ),
    ), row=1, col=2)

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=230,
        margin=dict(l=20, r=20, t=50, b=10),
        font=dict(family="Pretendard"),
    )

    return fig

# ──────────────────────────────────────────
# 📊 정밀 차트 렌더링 (V8.5 - 개선2: 가독성 극대화)
# ──────────────────────────────────────────
def _hl(fig,mask,idx,fill,txt=None,row=1):
    d=mask.astype(int).diff().fillna(0)
    starts=idx[d==1].tolist(); ends=idx[d==-1].tolist()
    if len(mask)>0 and mask.iloc[0]: starts.insert(0,idx[0])
    if len(mask)>0 and mask.iloc[-1]: ends.append(idx[-1])
    for s,e in zip(starts,ends):
        kw=dict(x0=s,x1=e,fillcolor=fill,line_width=0,row=row,col=1)
        if txt: kw.update(annotation_text=txt,annotation_position="top left",
                          annotation_font_size=10,annotation_font_color="#FF5252")
        fig.add_vrect(**kw)

def build_chart(dc,ticker,regime,shield):
    mac={5:"#ff9900",10:"#ffb74d",20:'#f1c40f',50:'#e74c3c',100:'#9b59b6',125:'#3498db',200:'#2ecc71'}

    # ✅ 개선2: 서브플롯 간격 확대, row_heights 비율 조정, 서브플롯 제목 강조
    fig=make_subplots(rows=6,cols=1,shared_xaxes=True,vertical_spacing=0.035,
        row_heights=[.36,.07,.15,.12,.15,.15],
        subplot_titles=("","Volume","WaveTrend Oscillator","Money Flow","MACD (12, 26, 9)","Confluence Score"))

    enabled = st.session_state.get('enabled_signals', set(ALL_CHART_SIGNALS.keys()))

    active_masks = {}
    for cn, cfg in ALL_CHART_SIGNALS.items():
        if cn not in dc.columns or cn not in enabled: continue
        mask = dc[cn].copy()
        if cn == 'Green_Dot_T1': mask &= ~dc.get('Gold_Dot', pd.Series(False, index=dc.index))
        elif cn == 'Ultra_Buy': mask &= ~dc.get('Gold_Dot', pd.Series(False, index=dc.index))
        elif cn == 'Ultra_Sell': mask &= ~dc.get('Blood_Diamond', pd.Series(False, index=dc.index))
        active_masks[cn] = mask

    daily_sig_texts = []
    for i in range(len(dc)):
        day_sigs = []
        for cn, mask in active_masks.items():
            if mask.iloc[i]:
                cfg = ALL_CHART_SIGNALS[cn]
                day_sigs.append(f"<span style='color:{cfg['clr']}'><b>{cfg['icon']} {cfg['label']}</b></span> <span style='font-size:11px;color:#AAA'>({cfg.get('kor','')})</span>")
        if day_sigs:
            daily_sig_texts.append("<br><br><b>🎯 포착 시그널:</b><br>" + "<br>".join(day_sigs))
        else:
            daily_sig_texts.append("")

    fig.add_trace(go.Candlestick(x=dc.index,open=dc['Open'],high=dc['High'],low=dc['Low'],
        close=dc['Close'],name="Price",increasing_line_color='#26a69a',decreasing_line_color='#ef5350',
        increasing_fillcolor='#26a69a', decreasing_fillcolor='#ef5350',  # ✅ 개선2: 캔들 채우기 색상 명시
        customdata=daily_sig_texts,
        hovertemplate="O: %{open:.2f}<br>H: %{high:.2f}<br>L: %{low:.2f}<br>C: %{close:.2f}%{customdata}<extra></extra>"
    ),row=1,col=1)

    for ma in [5,10,20,50,100,125,200]:
        fig.add_trace(go.Scatter(x=dc.index,y=dc[f'MA{ma}'],line=dict(color=mac[ma],width=1.2),name=f'{ma} MA',hovertemplate="%{y:.2f}"),row=1,col=1)
    for nm,col,clr,dash in [('EMA 8','EMA8','#00FFFF','dot'),('EMA 21','EMA21','#FF69B4','dot')]:
        fig.add_trace(go.Scatter(x=dc.index,y=dc[col],line=dict(color=clr,width=1.5,dash=dash),name=nm,hovertemplate="%{y:.2f}"),row=1,col=1)
    for mc,clr,nm in [(dc['ST_Direction']==1,'#00E676','ST▲'),(dc['ST_Direction']==-1,'#FF1744','ST▼')]:
        fig.add_trace(go.Scatter(x=dc.index,y=dc['SuperTrend'].where(mc),line=dict(color=clr,width=2),name=nm,connectgaps=False,hovertemplate="%{y:.2f}"),row=1,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['BB_Up'],line=dict(color='gray',width=1,dash='dot'),name='BB↑',hovertemplate="%{y:.2f}"),row=1,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['BB_Low'],line=dict(color='gray',width=1,dash='dot'),name='BB↓',
        fill='tonexty',fillcolor='rgba(128,128,128,0.07)',hovertemplate="%{y:.2f}"),row=1,col=1)

    for col_name,clr,txt in [('Sell_Shield_Overridden','rgba(255,0,0,0.04)','🔓Sell OFF'),
                         ('Buy_Shield_Overridden','rgba(0,255,0,0.04)','🔓Buy OFF')]:
        om=dc.get(col_name,pd.Series(False,index=dc.index))
        if om.any(): _hl(fig,om,dc.index,clr,txt,1)

    def _at(s): return dc.loc[s.index,'ATR'].fillna(dc['ATR'].median())

    for cn, cfg in ALL_CHART_SIGNALS.items():
        if cn not in active_masks: continue
        sig = dc[active_masks[cn]]
        if sig.empty: continue
        yv = sig[cfg['base']] + _at(sig) * cfg['atr_m']
        lw = 2 if cfg['sz'] >= 16 else (1.5 if cfg['sz'] >= 13 else 1)
        fig.add_trace(go.Scatter(x=sig.index, y=yv, mode='markers',
            marker=dict(symbol=cfg['sym'], size=cfg['sz'], color=cfg['clr'],
                line=dict(width=lw, color='white' if 'open' not in cfg['sym'] else cfg['clr'])),
            name=f"{cfg['icon']} {cfg['label']}",
            hoverinfo='skip'), row=1, col=1)

    br=dc['Close']<dc['Open']
    fig.add_trace(go.Bar(x=dc.index,y=dc['Volume'],marker_color=np.where(br,'#ef5350','#26a69a').tolist(),
        name="Volume",opacity=0.7,hovertemplate="%{y:,.0f}"),row=2,col=1)
    vcm=dc.get('Volume_Climax_Buy',pd.Series(False))|dc.get('Volume_Climax_Sell',pd.Series(False))
    vcd=dc[vcm]
    if not vcd.empty:
        fig.add_trace(go.Bar(x=vcd.index,y=vcd['Volume'],marker_color='#FFD700',name="Vol Climax",opacity=0.9,hovertemplate="%{y:,.0f}"),row=2,col=1)

    fig.add_trace(go.Scatter(x=dc.index,y=dc['WT1'],line=dict(color='#00E676',width=2),name="WT1",hovertemplate="%{y:.1f}"),row=3,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['WT2'],line=dict(color='#FF1744',width=1.5,dash='dot'),name="WT2",hovertemplate="%{y:.1f}"),row=3,col=1)
    wd=dc['WT1']-dc['WT2']
    fig.add_trace(go.Bar(x=dc.index,y=wd,marker_color=np.where(wd>=0,'#00E676','#FF1744').tolist(),name="WT Hist",opacity=0.3,hovertemplate="%{y:.1f}"),row=3,col=1)

    for ml,clr in [(['Green_Circle','Green_Dot_T1','Green_Dot_T2','Gold_Dot'],'#00E676'),
                     (['Red_Circle','Red_Dot_T1','Red_Dot_T2','Blood_Diamond'],'#FF1744')]:
        comb=pd.Series(False,index=dc.index)
        for mc in ml: comb|=dc.get(mc,pd.Series(False,index=dc.index))
        pts=dc[comb]
        if not pts.empty:
            fig.add_trace(go.Scatter(x=pts.index,y=pts['WT1'],mode='markers',
                marker=dict(symbol='circle',size=10,color=clr,line=dict(width=1,color='white')),
                hoverinfo='skip',showlegend=False),row=3,col=1)

    for lv,c_color,d in [(OB2,'#ff3333','dash'),(OB1,'#ff3333','solid'),(0,'gray','dot'),(OS1,'#00bfff','solid'),(OS2,'#00bfff','dash')]:
        fig.add_hline(y=lv,line_dash=d,line_color=c_color,line_width=1,row=3,col=1)
    wmx=max(float(dc['WT1'].max()),100)+10; wmn=min(float(dc['WT1'].min()),-100)-10
    fig.add_hrect(y0=OB1,y1=wmx,fillcolor="rgba(255,23,68,0.08)",line_width=0,row=3,col=1)
    fig.add_hrect(y0=wmn,y1=OS1,fillcolor="rgba(0,191,255,0.08)",line_width=0,row=3,col=1)
    if 'Squeeze_On' in dc.columns: _hl(fig,dc['Squeeze_On'],dc.index,"rgba(255,255,0,0.05)",None,3)

    rmfi=dc['RSI_MFI']
    fig.add_trace(go.Bar(x=dc.index,y=rmfi,marker_color=np.where(rmfi>=0,'#3ee145','#ff3d2e').tolist(),
        name="Money Flow",opacity=0.7,hovertemplate="%{y:.1f}"),row=4,col=1)
    fig.add_hline(y=0,line_dash="solid",line_color="gray",line_width=1,row=4,col=1)

    fig.add_trace(go.Scatter(x=dc.index,y=dc['MACD_Line'],line=dict(color='#29B6F6',width=1.5),name="MACD",hovertemplate="%{y:.3f}"),row=5,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['MACD_Signal'],line=dict(color='#FFA726',width=1.5),name="Signal",hovertemplate="%{y:.3f}"),row=5,col=1)
    mh=dc['MACD_Hist']
    fig.add_trace(go.Bar(x=dc.index,y=mh,marker_color=np.where(mh>=0,'#26A69A','#EF5350').tolist(),name="Hist",opacity=0.7,hovertemplate="%{y:.3f}"),row=5,col=1)
    fig.add_hline(y=0,line_color="#444444",line_width=1,row=5,col=1)

    conf=dc['Confluence_Score']
    fig.add_trace(go.Bar(x=dc.index,y=conf,
        marker_color=np.where(conf>=3.5,'#00E676',np.where(conf<=-3.5,'#FF1744','#FFC107')).tolist(),
        name="Conf Score",opacity=0.8,hovertemplate="%{y:.1f}"),row=6,col=1)
    for lv,c_color,d in [(6,'#00E676','dash'),(-6,'#FF1744','dash'),(3.5,'#00E676','dot'),(-3.5,'#FF1744','dot'),(0,'gray','solid')]:
        fig.add_hline(y=lv,line_dash=d,line_color=c_color,line_width=1 if d=='solid' else .8,row=6,col=1)

    stxt=f" | {shield}" if shield else ""

    # ✅ 개선2: 차트 레이아웃 가독성 극대화
    fig.update_layout(
        title=dict(text=f"📊 {ticker.upper()} | 💎 MCB+ V8.5 | {regime}{stxt}",
                   font=dict(size=15, color='#FAFAFA', family='Pretendard')),
        yaxis_title="Price", yaxis2_title="Vol", yaxis3_title="WT",
        yaxis4_title="MF", yaxis5_title="MACD", yaxis6_title="Conf",
        template="plotly_dark",
        margin=dict(l=5, r=5, t=55, b=5),
        height=1400,  # ✅ 개선2: 높이 증가
        showlegend=True,
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="rgba(22,26,34,0.95)",
            font_size=12,
            font_family="Pretendard",
            bordercolor="#2D333B"
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
            font=dict(size=9.5, color='#CCC', family='Pretendard'),
            bgcolor='rgba(0,0,0,0)',
            itemsizing='constant'
        ),
    )

    # ✅ 개선2: 축 스타일 - 그리드라인 가독성 향상
    for i in range(1, 7):
        ya = f'yaxis{i}' if i > 1 else 'yaxis'
        fig.update_layout(**{
            ya: dict(
                gridcolor='rgba(60,63,70,0.5)',
                gridwidth=0.5,
                zerolinecolor='rgba(100,103,110,0.6)',
                zerolinewidth=0.8,
                title_font=dict(size=11, color='#888'),
                tickfont=dict(size=10, color='#999'),
            )
        })

    fig.update_xaxes(rangeslider_visible=False)
    has_weekends = dc.index.dayofweek.isin([5, 6]).any()
    rangebreaks_config = [dict(bounds=["sat", "mon"])] if not has_weekends else []

    # ✅ 개선2: 크로스헤어 스파이크 개선
    fig.update_xaxes(
        showspikes=True, spikecolor="#667eea", spikemode="across",
        spikethickness=1, spikedash="dot", rangebreaks=rangebreaks_config,
        gridcolor='rgba(60,63,70,0.3)', gridwidth=0.5,
        tickfont=dict(size=10, color='#999'),
    )
    fig.update_yaxes(
        showspikes=True, spikecolor="#667eea", spikemode="across",
        spikethickness=1, spikedash="dot",
    )

    # ✅ 개선2: 서브플롯 제목 스타일링 강화
    for ann in fig['layout']['annotations']:
        ann['font'] = dict(size=12, color='#AAA', family='Pretendard')

    return fig

# ──────────────────────────────────────────
# 메타데이터 + AI 프롬프트 생성
# ──────────────────────────────────────────
def build_metadata(dc,dv,ticker):
    lat,prev=dc.iloc[-1],dc.iloc[-2] if len(dc)>=2 else dc.iloc[-1]
    pc=lat['Close']-prev['Close']; pp=pc/prev['Close']*100
    m4={k:float(lat[c]) for k,c in [('wt1','WT1'),('rsi','RSI'),('mfi','MFI'),('mf_area','RSI_MFI'),('stochk','StochK')]}
    h1=bool(lat.get('_HTF1_Bull',False)); h2=bool(lat.get('_HTF2_Bull',False))
    bias,bsc=compute_bias(m4,h1,h2); cf=float(dc['Confluence_Score'].iloc[-1])
    regime='STRONG BULL 🟢' if lat.get('Strong_Bull',False) else ('STRONG BEAR 🔴' if lat.get('Strong_Bear',False) else 'NEUTRAL ⚪')
    sp=[]
    for cond,lab in [('Parabolic_Blowoff','🌡️PARA TOP'),('ST_Bear_Override','📉ST BEAR'),('Parabolic_Bottom_Raw','🧊PARA BOT')]:
        if lat.get(cond,False): sp.append(lab)
    if not sp:
        if lat.get('Buy_Shield_Overridden',False): sp.append('🔓BUY OFF')
        if lat.get('Sell_Shield_Overridden',False): sp.append('🔓SELL OFF')
    shield_str=' + '.join(sp)
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
        'overall_bias':bias,'bias_score':bsc,'confluence_score':cf,
        'recent_signals':recent,'all_signal_stats':compute_all_stats(dv),
        'last_date':dc.index[-1].strftime('%Y-%m-%d'),
        'buy_proximity':float(lat['Buy_Proximity']),'sell_proximity':float(lat['Sell_Proximity']),
        'squeeze_on':bool(lat.get('Squeeze_On',False)),
        'trend_regime':regime,'shield_status':shield_str,
        'supertrend_dir':int(lat.get('ST_Direction',0)),'supertrend_val':float(lat.get('SuperTrend',0)),
        'ema8':float(lat.get('EMA8',0)),'ema21':float(lat.get('EMA21',0)),
        'bb_up':float(lat.get('BB_Up',0)),'bb_low':float(lat.get('BB_Low',0)),
        'ma50':float(lat.get('MA50',0)),'ma200':float(lat.get('MA200',0)),
        'macd_line':float(lat.get('MACD_Line',0)),'macd_signal':float(lat.get('MACD_Signal',0)),
        'macd_hist':float(lat.get('MACD_Hist',0)),
    },regime,shield_str

def build_prompt_text(dc,meta):
    lat=dc.iloc[-1]; rd=dc.tail(60)
    ps=", ".join([f"'{d.strftime('%Y-%m-%d')}:{r['Close']:.2f}'" for d,r in rd.iterrows()])
    sl=[]
    for ir,row in dc.tail(30).iterrows():
        dd=ir.strftime('%Y-%m-%d')
        for k,v in ALL_CHART_SIGNALS.items():
            if row.get(k,False): sl.append(f"{v['icon']} {v['label']} {dd}")
    st_text="\n".join(sl) if sl else "최근 30일 내 시그널 없음"
    bp,sp=meta['buy_proximity'],meta['sell_proximity']
    prox=f"BuyProx={bp:.0f}%,SellProx={sp:.0f}%"
    if bp>=60: prox+=" ⚠️매수임박"
    if sp>=60: prox+=" ⚠️매도임박"
    sq="SqON" if meta['squeeze_on'] else "SqOFF"
    std=f"BULL▲({meta['supertrend_val']:.2f})" if meta['supertrend_dir']==1 else f"BEAR▼({meta['supertrend_val']:.2f})"
    shd=f"Shield:{meta['shield_status']}" if meta['shield_status'] else "Shield:NONE"
    inds=(f"WT1={lat['WT1']:.1f},WT2={lat['WT2']:.1f},RSI={lat['RSI']:.1f},MFI={lat['MFI']:.1f},"
        f"StK={lat['StochK']:.1f},StD={lat['StochD']:.1f},VWAP={lat['VWAP_Osc']:.2f},"
        f"MF={lat['RSI_MFI']:.1f},ADX={lat['ADX']:.1f},+DI={lat['Plus_DI']:.1f},-DI={lat['Minus_DI']:.1f},"
        f"E8={lat['EMA8']:.2f},E21={lat['EMA21']:.2f},ST={std},"
        f"BB=[{meta['bb_up']:.2f}/{meta['bb_low']:.2f}],%B={lat.get('Percent_B',0):.2f},M50={meta['ma50']:.2f},M200={meta['ma200']:.2f},"
        f"Chandelier=[L:{lat.get('Chandelier_Long',0):.2f}/S:{lat.get('Chandelier_Short',0):.2f}],"
        f"MACD={meta['macd_line']:.3f}/{meta['macd_signal']:.3f} H={meta['macd_hist']:.3f},"
        f"Conf={meta['confluence_score']:.1f},Bias={meta['overall_bias']}({meta['bias_score']:.1f}),"
        f"Trend={meta['trend_regime']},{shd},{prox},{sq}")
    stats=meta.get('all_signal_stats',{})
    st_txt=""
    if stats:
        lines=[]
        for sn,sv in sorted(stats.items(),key=lambda x:x[1]['count'],reverse=True)[:10]:
            wr=sv.get('10d_winrate'); avg=sv.get('10d_avg')
            if wr is not None: lines.append(f"  {sn}:{sv['count']}회,10일승률{wr:.0f}%,평균{avg:+.1f}%")
        if lines: st_txt="\n📌 [백테스트(2년,상위10)]\n"+"\n".join(lines)
    return f"{ps}\n\n📌 [지표 요약]\n{inds}\n\n📌 [최근 시그널]\n{st_text}{st_txt}"

def build_ai_prompt(ticker,phist,fundamentals):
    return f"""━━━━━━━━━━━━━
【 🎯 Role & Persona 】
━━━━━━━━━━━━━
당신은 월스트리트 20년+ 경력 베테랑 주식 애널리스트이자 펀드 매니저입니다.
기술적 분석과 시장 심리 파악에 탁월하며, Market Cipher B 지표 해석 및 ATR 변동성 기반의 철저한 리스크 관리에 정통합니다.

---
━━━━━━━━━━━━━
【 🛠️ Task & Rules 】
━━━━━━━━━━━━━
제공된 데이터를 바탕으로 심층 주가 분석 보고서를 작성하세요. 함의와 투자자 행동을 구체적으로 설명하세요.

1. 🚫 환각(Hallucination) 엄금: [YFinance 펀더멘탈]에 없는 데이터는 지어내지 마세요. 옵션이나 공매도 수치는 제공된 숏 비율과 거래량, 차트 흐름을 통해 유추한 수급 상태로 대체 설명하세요.
2. 🧮 기계적 리스크 관리 (ATR 활용): 손절가와 목표가는 반드시 주어진 **ATR** 데이터를 기반으로 산출하여 표(Table)로 작성하세요.
   - 스윙 롱 손절가 = 현재가 - (ATR * 1.5) / 1차 목표가 = 현재가 + (ATR * 2.0)
3. 🌊 추세 맞춤형 전략 (Trend Regime): STRONG BULL, STRONG BEAR, NEUTRAL 에 맞는 전략을 제시하세요.
4. 📈 데이터 활용: 백테스트 승률(Winrate), VWAP_Osc, ADX, Squeeze 상태 등 제공된 텍스트 데이터를 분석의 근거로 반드시 포함하세요. 지지/저항은 MA선, 볼린저밴드, 최근 고점/저점을 활용하세요.

---
━━━━━━━━━━━━━
【 📥 Input Data 】
━━━━━━━━━━━━━
[티커: {ticker}]

📌 [주가 + 기술적 지표 + 시그널 백테스트 요약]
{phist}

📌 [YFinance 펀더멘탈 및 숏(공매도) 데이터]
{fundamentals}

---
━━━━━━━━━━━━━
【 📄 Output Format (반드시 아래 양식을 그대로 출력할 것) 】
━━━━━━━━━━━━━
# 🚦 {{ticker}} 심층 퀀트 리포트
[🔵/🔴/🟠] [{{ticker}}] 분석: [핵심 한 줄]
[날짜], 전일 대비 [변동률]% [상승/하락]. 거래량 [평균대비 배수]. [핵심 패턴]. 지지 [가격], 저항 [가격].

---
### 내용 요약
[🔵/🔴/🟠] [현재 상황 및 방향성에 대한 3~4문장 요약]

---
### 🚦 마켓 사이퍼 B+ 시그널 분석
* WaveTrend: [WT1/WT2 값, 과매수/과매도 등 상태]
* Money Flow: [MF_Area 값, 자금 유입/유출 방향]
* 🔥 Confluence Score: [점수, 판정 (예: Strong Buy), 감쇠 상태]
* ⚠️ Signal Proximity: [매수/매도 임박 여부 퍼센트 및 코멘트]
* 최근 시그널: [최근 발생한 주요 시그널 목록 요약]
* 시그널 신뢰도: [높음/중간/낮음 + 제공된 백테스트 승률/평균수익 등 근거]
> 🚦 해석: [위 지표들이 뜻하는 바를 베테랑의 시선으로 1~2문장 해석]

---
### 주가 및 거래량 분석
* 거래량: 평균 대비 [배수] 수준. 거래량 지표(VWAP Oscillator): [값]
* 현재 상태: [과매수/과매도 여부, ADX 기반 추세 강도 분석]
> 해석: [거래량이 갖는 시장 심리 해석]  [긍정:🔵/부정 :🔴/중간:🟠]
* 거래량 해석: [스마트 머니 유입/이탈 징후 판단]  [긍정:🔵/부정 :🔴/중간:🟠]
> 종합 해석: [🔵/🔴/🟠] [종합 판단]

---
### 장중 기술적 지표
[식별된 기술적 패턴 이름 (예: Momentum Ignition, EMA Pullback 등)]
* 상태: [패턴에 대한 설명. ATR 기반 예상 변동 ±__%]
* 해석: [패턴이 향후 주가에 미칠 영향]  [긍정:🔵/부정 :🔴/중간:🟠]
* 역사적 유사패턴: [백테스트 데이터 기반: 동일 시그널 발생 시 10일 승률 __%, 평균 수익률 __%]  [긍정:🔵/부정 :🔴/중간:🟠]
* 지표 요약: ATR [값] (±__%), ADX [값], TTM Squeeze [ON/OFF], MACD [상태]

---
### 지지선 및 저항선
* 지지선: [가격1] (설명), [가격2], [가격3]
* 저항선: [가격1] (설명), [가격2], [가격3]
[이동평균선, 볼린저 밴드, 샹들리에 엑시트(Chandelier) 등을 기준으로 현재 주가 위치 설명]

---
### 파생 심리 및 공매도 현황
* 공매도 및 숏스퀴즈 가능성: [제공된 Short % of Float, Short Ratio 기반 하방 압력 및 숏커버링 가능성 분석. 숏커버링 압력 지수: High/Medium/Low]
* 옵션/파생 심리 추정: [현재 추세 및 변동성을 통한 파생 시장의 상방/하방 베팅 심리 유추]
> [긍정:🔵/부정 :🔴/중간:🟠] 해석: 수급상 주가를 끌어올릴(혹은 내릴) '에너지'가 얼마나 축적되었는가?

---
### 주가변동이유 및 이벤트
- [🔵/🔴/🟠] [이유 1] — 단발성/추세형 [현재 펀더멘탈/뉴스 모멘텀 평가]
- [🔵/🔴/🟠] [이유 2] (필요시)

---
### 🔮 종합해석 및 시나리오
* 🔵 **긍정적 시나리오 (Bullish):** [조건] 충족 시 [목표가]까지 상승 예상. 확률: __% (근거: )
* 🟠 **베이스 시나리오 (Base):** [가장 확률 높은 시나리오]. 확률: __%
* 🔴 **리스크 시나리오 (Bearish):** [조건] 이탈 시 [하락 목표가]까지 하락 예상. 확률: __% (근거: )

**실전 트레이딩 전략:**
* **리스크/리워드 비율:** 목표가 대비 손절가 간 비율 1:__ 확인
* **공격적 매수 구간:** [가격대] (ATR __% 이내 진입)
* **보수적 진입 시점:** [확인 매매 가격대]
* **손절(Stop-loss) 라인:** [필수 준수 가격] - 이 가격 붕괴 시 예측 시나리오 폐기, 즉시 대응
* **분할 매도 전략:** 1차 목표 [가격] 도달 시 __% 익절, 2차 목표 [가격] 도달 시 __% 추가 매도
* **트레일링 스탑:** [Chandelier Exit 값 등을 활용한 이익 보존 가이드]

---
### 결론
[🔵/🔴/🟠] [2~3문장 명확한 결론]

### 주가 예측 (다음 거래일)
[🔵/🔴/🟠] 예상: [방향] · 근거: [...]
[리스크/리워드 최적 진입] : [가격] 지지 확인 후 [가격] 공략, [비율] 리스크/리워드 최적 진입
[GRADE/Score]: [최종 등급 및 이유]
"""

# ──────────────────────────────────────────
# 통합 분석
# ──────────────────────────────────────────
def analyze(ticker,chart_days=252,refresh=False):
    try:
        ts=int(time.time()) if refresh else None
        df=compute_and_cache(ticker,ts)
        if df is None or df.empty: return None,"주가 데이터 없음",None
        dv=df.dropna(subset=['WT1','WT2']); dc=dv.tail(chart_days).copy()
        if dc.empty: return None,"차트 데이터 부족",None
        meta,regime,shield=build_metadata(dc,dv,ticker)
        fig=build_chart(dc,ticker,regime,shield)
        return fig,build_prompt_text(dc,meta),meta
    except Exception as e:
        return None,f"로딩 실패:{e}",None

# ──────────────────────────────────────────
# UI 렌더
# ──────────────────────────────────────────
_IT={'wt1':[(-53,'극과매도'),(-20,'과매도'),(20,'중립'),(53,'과매수'),(999,'극과매수')],
     'rsi':[(30,'과매도'),(45,'약세'),(55,'중립'),(70,'강세'),(999,'과매수')],
     'mfi':[(30,'과매도'),(45,'약세'),(55,'중립'),(70,'강세'),(999,'과매수')],
     'stochk':[(20,'바닥'),(80,''),(999,'천장')]}

def _il(n,v):
    for t,l in _IT.get(n,[]):
        if v<=t: return l
    return ''

def render_price_header(m):
    chg=m['price_change']; cp=m['price_change_pct']
    cc='price-change-up' if chg>=0 else 'price-change-down'
    ci='▲' if chg>=0 else '▼'
    vr=m['volume']/m['avg_volume'] if m['avg_volume'] else 0
    cv=m.get('confluence_score',0); sd=m.get('supertrend_dir',0)
    sh=m.get('shield_status',''); mh_val=m.get('macd_hist',0)
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
    if sh: ih+=f"<span class='indicator-mini ind-bearish' style='font-weight:700'>🔓 {sh}</span>"
    tr=m.get('trend_regime','NEUTRAL ⚪')
    st.markdown(f"""<div class="price-header">
        <div style="display:flex;justify-content:space-between;align-items:center">
            <div><p class="price-label">🚦 {m['ticker']} · {m['last_date']} · <b>{tr}</b></p>
            <p class="price-big" style="color:#FAFAFA">${m['price']:.2f}
                <span class="{cc}" style="font-size:1rem;margin-left:8px">
                    {ci} {abs(chg):.2f} ({abs(cp):.2f}%)</span></p></div>
            <div style="text-align:right"><p class="price-label">ATR</p>
            <p style="color:#FFC107;font-size:1.1rem;font-weight:600;margin:0">
                ${m['atr']:.2f} ({m['atr_pct']:.1f}%)</p></div></div>
        <div style="margin-top:10px;display:flex;gap:6px;flex-wrap:wrap">{ih}</div></div>""",unsafe_allow_html=True)

# ──────────────────────────────────────────
# ✅ 개선3: Speedometer 게이지 렌더링 함수 (render_bias 대체)
# ──────────────────────────────────────────
def render_speedometer(m):
    """속도계 형태의 게이지 차트 + 텍스트 판정을 통합 렌더링"""
    gauge_fig = build_speedometer_gauges(m)
    st.plotly_chart(gauge_fig, use_container_width=True, theme=None, config={'displayModeBar': False})

    # 게이지 아래에 간결한 판정 텍스트
    bias = m['overall_bias']; sc = m.get('bias_score', 0); cv = m.get('confluence_score', 0)
    styles = {
        'STRONG BUY': ('rgba(0,230,118,.15)', '#00E676', '🟢🟢'),
        'BUY': ('rgba(0,230,118,.10)', '#00E676', '🟢'),
        'STRONG SELL': ('rgba(255,23,68,.15)', '#FF1744', '🔴🔴'),
        'SELL': ('rgba(255,23,68,.10)', '#FF1744', '🔴')
    }
    bg, clr, ico = styles.get(bias, ('rgba(255,193,7,.10)', '#FFC107', '🟠'))

    bp = m.get('buy_proximity', 0)
    sp = m.get('sell_proximity', 0)
    prox_txt = ""
    if bp >= 50:
        prox_txt = f"<span style='color:#00E676'>매수 임박 {bp:.0f}%</span>"
    elif sp >= 50:
        prox_txt = f"<span style='color:#FF1744'>매도 임박 {sp:.0f}%</span>"

    sq_txt = " · <span style='color:#FFFF00;font-weight:600'>💥 Squeeze ON</span>" if m.get('squeeze_on') else ""

    st.markdown(f"""<div style="background:{bg};border-radius:10px;padding:10px 16px;text-align:center;margin:4px 0 12px 0">
        <span style="font-size:1.1rem;font-weight:700;color:{clr}">{ico} 종합 판정: {bias} ({sc:.1f})</span>
        {f' · {prox_txt}' if prox_txt else ''}{sq_txt}</div>""", unsafe_allow_html=True)


def render_alerts(m):
    alerts=[]
    bp,sp=m.get('buy_proximity',0),m.get('sell_proximity',0)
    if bp>=70: alerts.append(('🟢⚡ 매수 매우 임박!','#00E676',bp))
    elif bp>=50: alerts.append(('🟢 매수 접근 중','#69F0AE',bp))
    if sp>=70: alerts.append(('🔴⚡ 매도 매우 임박!','#FF1744',sp))
    elif sp>=50: alerts.append(('🔴 매도 접근 중','#FF5252',sp))
    if m.get('squeeze_on'): alerts.append(('💥 Squeeze ON','#FFFF00',80))
    for txt,clr,pct in alerts:
        w=min(pct,100)
        st.markdown(f"""<div style="background:rgba(255,255,255,.03);border:1px solid #2D333B;border-radius:8px;padding:8px 14px;margin:4px 0">
            <div style="display:flex;justify-content:space-between;align-items:center">
                <span style="color:{clr};font-weight:600;font-size:.9rem">{txt}</span>
                <span style="color:{clr};font-weight:700;font-size:.85rem">{pct:.0f}%</span></div>
            <div style="background:#1A1D24;border-radius:3px;height:6px;margin-top:6px">
                <div style="background:{clr};width:{w}%;height:6px;border-radius:3px"></div></div></div>""",unsafe_allow_html=True)

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
            cn="ind-bullish" if s=="buy" else "ind-bearish"
            sh=""
            for sn,sv in alls.items():
                if ALL_CHART_SIGNALS.get(sn,{}).get('label')==l:
                    wr=sv.get('10d_winrate')
                    if wr is not None: sh=f" ({wr:.0f}%)"
                    break
            parts.append(f'<span class="indicator-mini {cn}">{i} {l}{sh}</span>')
        st.markdown(f"""<div class="signal-card {ct}">
            <div style="display:flex;justify-content:space-between;align-items:center">
                <span style="font-weight:700;font-size:.9rem;color:#FAFAFA">📅 {ds}</span>
                <span style="color:#888;font-size:.75rem">{len(group)}개</span></div>
            <div style="margin-top:6px;display:flex;gap:4px;flex-wrap:wrap">{" ".join(parts)}</div></div>""",unsafe_allow_html=True)

def render_stats(m):
    with st.expander("📊 백테스트 (2년, 진입:다음날시가, 청산:종가)",expanded=True):
        alls=m.get('all_signal_stats',{})
        if not alls: st.caption("통계 없음"); return
        def _side(title,data):
            st.markdown(f"##### {title}")
            for sn,sv in sorted(data.items(),key=lambda x:x[1]['count'],reverse=True):
                wr=sv.get('10d_winrate'); av=sv.get('10d_avg')
                if wr is None: continue
                kor_label = ALL_CHART_SIGNALS.get(sn,{}).get('kor', sn)
                c='#00E676' if wr>50 else ('#FFC107' if wr>40 else '#FF1744')
                lb=f"승률 <span style='color:{c}'>**{wr:.0f}%**</span>"
                av_c='#00E676' if av>0 else '#FF1744'
                ic=ALL_CHART_SIGNALS.get(sn,{}).get('icon','')
                st.markdown(f"<span style='font-size:.85rem'>{ic} **{kor_label}** ({sv['count']}회) · {lb} · 평균 <span style='color:{av_c}'>**{av:+.1f}%**</span></span>",unsafe_allow_html=True)
        c1,c2=st.columns(2)
        with c1: _side("🟢 BUY 전략",{k:v for k,v in alls.items() if v['direction']=='buy'})
        with c2: _side("🔴 SELL (Short) 전략",{k:v for k,v in alls.items() if v['direction']=='sell'})

def render_analysis(msg):
    m,fig=msg.get('meta'),msg.get('fig')
    if m:
        render_price_header(m)
        render_speedometer(m)     # ✅ 개선3: 기존 render_bias → render_speedometer 교체
        render_alerts(m)
    if m or fig:
        t1,t2,t3=st.tabs(["📊 정밀 차트","🔔 발생 시그널","📈 백테스트 통계"])
        with t1:
            if fig: st.plotly_chart(fig,use_container_width=True,theme=None, config={'displayModeBar': False})
        with t2:
            if m: render_signals(m)
        with t3:
            if m: render_stats(m)

# ──────────────────────────────────────────
# ✅ 개선1: 사이드바 (토글 기능은 initial_sidebar_state="collapsed" + Streamlit 네이티브)
# ──────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🚦 CipherX")
    st.markdown("<p style='color:#888;font-size:.8rem'>AI 퀀트 주가 분석 · MCB+ v8.5</p>",unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("### 📅 차트 기간")
    chart_period=st.radio("표시 기간",['3개월','6개월','1년','2년'],index=2,horizontal=True,key="period")
    chart_days={'3개월':63,'6개월':126,'1년':252,'2년':504}[chart_period]
    st.markdown("---")
    with st.expander("🎛️ 시그널 활성화 필터",expanded=False):
        _sb=st.checkbox("🟢 매수 시그널",value=True,key="sb")
        _ss=st.checkbox("🔴 매도 시그널",value=True,key="ss")
        _sc=st.checkbox("⭐ 복합 시그널",value=True,key="sc")
        _mw=st.slider("최소 가중치 필터",0.0,3.0,0.0,0.5,key="mw")
        enabled=set()
        for k,v in ALL_CHART_SIGNALS.items():
            if v['dir']=='buy' and not _sb: continue
            if v['dir']=='sell' and not _ss: continue
            if k in COMPOSITE_SIGNALS and not _sc: continue
            if v['w']<_mw and k not in COMPOSITE_SIGNALS: continue
            enabled.add(k)
        st.session_state['enabled_signals']=enabled
        st.caption(f"현재 차트 표시: {len(enabled)}개")
    st.markdown("---")
    # ✅ 개선1: 사이드바 닫기 안내 (모바일 UX)
    st.markdown("<p style='color:#555;font-size:.7rem;text-align:center'>← 화살표를 눌러 사이드바를 닫을 수 있습니다</p>", unsafe_allow_html=True)
    if st.button("🗑️ 대화 내역 지우기",use_container_width=True,type="secondary"):
        for key in ['messages','pending_ai_ticker','pending_ai_prompt','last_ticker']:
            st.session_state[key]=[{"role":"assistant","type":"text",
                "content":"안녕하세요! 🚦 **CipherX** 입니다.\n\n분석할 **티커명**을 입력하세요."}] if key=='messages' else None
        st.rerun()

# ──────────────────────────────────────────
# 세션 관리
# ──────────────────────────────────────────
if 'messages' not in st.session_state:
    st.session_state.messages=[{"role":"assistant","type":"text",
        "content":"안녕하세요! 🚦 **CipherX** 입니다.\n\n분석할 **티커명**을 입력하세요. 채팅처럼 이어서 여러 종목을 검색할 수 있습니다."}]
for key in ['pending_ai_ticker','pending_ai_prompt','last_ticker']:
    if key not in st.session_state: st.session_state[key]=None
if 'enabled_signals' not in st.session_state:
    st.session_state['enabled_signals']=set(ALL_CHART_SIGNALS.keys())

# ──────────────────────────────────────────
# 챗 인터페이스 & AI 실행
# ──────────────────────────────────────────
st.markdown("<h2 style='text-align:center;color:#fff;margin-bottom:20px'>🚦 CipherX</h2>",unsafe_allow_html=True)

for i,msg in enumerate(st.session_state.messages):
    av="✨" if msg["role"]=="assistant" else "🧑‍💻"
    with st.chat_message(msg["role"],avatar=av):
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
            st.download_button("📥 마크다운 파일 다운로드",key=f"dl_{i}_{msg.get('ticker','RPT')}",
                data=msg["content"].encode('utf-8'),
                file_name=f"{msg.get('ticker','RPT').upper()}_Quant_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
                mime="text/markdown",use_container_width=True)
        else: st.markdown(msg.get("content",""))

# ──────────────────────────────────────────
# ✅ 개선4: st.write_stream 기반 리포트 스트리밍
# ──────────────────────────────────────────
def _run_ai():
    tp = st.session_state.pending_ai_ticker
    pp = st.session_state.pending_ai_prompt
    with st.chat_message("assistant", avatar="✨"):
        pb = st.progress(0, text="퀀트 엔진 로딩 중...")
        try:
            pb.progress(10, text="Gemini 모델 초기화 중...")
            model = genai.GenerativeModel('gemini-2.5-flash')
            pb.progress(20, text="시장 데이터 및 시그널 취합 중...")

            # ✅ 개선4 핵심: Gemini 스트림을 제너레이터로 변환 → st.write_stream 사용
            collected_chunks = []

            def gemini_stream_generator():
                """Gemini streaming response를 st.write_stream 호환 제너레이터로 변환"""
                pb.progress(40, text="🚀 AI 리포트 생성 중...")
                response = model.generate_content(pp, stream=True)
                chunk_count = 0
                for chunk in response:
                    text = chunk.text
                    if text:
                        collected_chunks.append(text)
                        chunk_count += 1
                        progress_val = min(40 + chunk_count * 2, 95)
                        pb.progress(progress_val, text="차트 타점 및 전략 산출 중...")
                        yield text
                pb.progress(100, text="✅ 퀀트 분석 완료!")

            # ✅ 개선4: st.write_stream으로 부드러운 스트리밍 렌더링 (깜빡임 없음)
            with st.expander(f"📊 {tp.upper()} AI 퀀트 리포트", expanded=True):
                st.write_stream(gemini_stream_generator())

            time.sleep(0.3)
            pb.empty()

            # 전체 텍스트 조립 후 세션에 저장
            full_report = "".join(collected_chunks)
            st.session_state.messages.append({
                "role": "assistant", "type": "report",
                "ticker": tp.upper(), "content": full_report
            })
            st.session_state.pending_ai_ticker = None
            st.session_state.pending_ai_prompt = None
            st.rerun()

        except Exception as e:
            pb.empty()
            st.error(f"AI 오류: {e}")


def process_ticker(tv,refresh=False):
    tv=tv.strip().upper()
    st.session_state.pending_ai_ticker=None; st.session_state.pending_ai_prompt=None
    if not _valid_fmt(tv):
        st.session_state.messages.append({"role":"user","type":"text","content":tv})
        st.session_state.messages.append({"role":"assistant","type":"text",
            "content":f"⚠️ **{tv}** — 올바른 형식이 아닙니다. (영문 1~5자)"})
        st.rerun(); return
    if not validate_ticker(tv):
        st.session_state.messages.append({"role":"user","type":"text","content":tv})
        st.session_state.messages.append({"role":"assistant","type":"text",
            "content":f"⚠️ **{tv}** — Yahoo Finance에서 데이터를 찾을 수 없습니다."})
        st.rerun(); return

    st.session_state.messages.append({"role":"user","type":"text","content":tv})
    st.session_state.last_ticker=tv
    with st.chat_message("assistant",avatar="✨"):
        pg=st.progress(0,text=f"🌐 {tv} 데이터 파이프라인 가동...")
        pg.progress(20,text="📡 YFinance 펀더멘탈 및 숏(공매도) 데이터 조회 중...")
        fundamentals = fetch_fundamentals(tv)
        pg.progress(50,text="📊 YFinance 기술적 데이터 및 지표 계산 중...")
        fig,phist,meta=analyze(tv,chart_days,refresh)
        pg.progress(85,text="🚦 마켓 사이퍼 시그널 엔진 교차 검증 중...")
        if fig:
            prompt=build_ai_prompt(tv,phist,fundamentals)
            st.session_state.messages.append({"role":"assistant","type":"analysis","ticker":tv,
                "content":f"✅ **{tv}** 분석 완료! 아래에서 정밀 차트를 확인하세요.","fig":fig,"meta":meta,"prompt":prompt})
            st.session_state.pending_ai_ticker=tv; st.session_state.pending_ai_prompt=prompt
            pg.progress(100,text="✅완료!"); time.sleep(.3); pg.empty()
            st.rerun()
        else:
            pg.empty()
            st.session_state.messages.append({"role":"assistant","type":"text",
                "content":f"⚠️ **{tv}** 차트 렌더링에 실패했습니다."})
            st.rerun()

# ──────────────────────────────────────────
# 액션 버튼 (챗 하단 고정)
# ──────────────────────────────────────────
if st.session_state.last_ticker:
    lt=st.session_state.last_ticker
    c1,c2=st.columns([3,1])
    with c1:
        if st.session_state.pending_ai_ticker and st.session_state.pending_ai_prompt:
            if st.button(f"🚀 {st.session_state.pending_ai_ticker.upper()} AI 심층 퀀트 분석 시작",
                         type="primary",use_container_width=True):
                _run_ai()
    with c2:
        if st.button(f"🔄 {lt} 새로고침",type="secondary",use_container_width=True,key="re"):
            process_ticker(lt,refresh=True)
elif st.session_state.pending_ai_ticker and st.session_state.pending_ai_prompt:
    if st.button(f"🚀 {st.session_state.pending_ai_ticker.upper()} AI 심층 퀀트 분석 시작",
                 type="primary",use_container_width=True):
        _run_ai()

if ticker_input:=st.chat_input("미국 주식 티커를 입력하세요 (예: TSLA, AAPL, QQQ)"):
    process_ticker(ticker_input)