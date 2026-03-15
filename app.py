import streamlit as st
import requests
from bs4 import BeautifulSoup
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

st.set_page_config(page_title="CipherX", page_icon="📈", layout="centered")

# ──────────────────────────────────────────
# 🎨 CSS
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
header{visibility:hidden}
.block-container{padding-top:1rem!important;max-width:900px}
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
section[data-testid="stSidebar"]{background-color:#0A0D12;border-right:1px solid #1E2127}
section[data-testid="stSidebar"] .stMarkdown p{color:#AAA!important}
.signal-card{border-radius:12px;padding:16px 20px;margin:6px 0;border:1px solid #2D333B}
.signal-card-buy{background:linear-gradient(135deg,rgba(0,230,118,.08) 0%,rgba(0,191,255,.05) 100%);border-left:4px solid #00E676}
.signal-card-sell{background:linear-gradient(135deg,rgba(255,23,68,.08) 0%,rgba(255,82,82,.05) 100%);border-left:4px solid #FF1744}
.signal-card-neutral{background:linear-gradient(135deg,rgba(255,193,7,.08) 0%,rgba(255,152,0,.05) 100%);border-left:4px solid #FFC107}
.price-header{background:linear-gradient(135deg,#161A22 0%,#1A1F2E 100%);border:1px solid #2D333B;
border-radius:14px;padding:18px 24px;margin-bottom:16px}
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
# 🔧 시그널 레지스트리 (V5.0)
# ──────────────────────────────────────────
_B, _S = 'buy', 'sell'

def _sig(w, d, icon, label, sym, sz, clr, base, atr_m, kor, desc):
    return {'w':w,'dir':d,'icon':icon,'label':label,'sym':sym,'sz':sz,'clr':clr,
            'base':base,'atr_m':atr_m,'kor':kor,'desc':desc}

SIGNAL_REGISTRY = {
    # ── BUY ──
    'Gold_Dot':              _sig(3.0,_B,'🏆','GOLD DOT','circle',18,'#FFD700','Low',-3.0,'최강 매수','RSI<30+MFI<30+WT1<-60+상승 다이버전스'),
    'Green_Dot_T1':          _sig(2.5,_B,'🟢','BUY T1','circle',16,'#00E676','Low',-2.5,'강한 매수','WT과매도 교차+RSI<30+MFI<30+MF<0'),
    'Green_Dot_T2':          _sig(2.0,_B,'🟩','BUY T2','circle',13,'#69F0AE','Low',-2.2,'매수','WT과매도+RSI또는MFI<32'),
    'Blue_Diamond':          _sig(2.0,_B,'🔹','BLUE DIA','diamond',14,'#00bfff','Low',-1.8,'추세 매수','WT2≤0 상승교차+HTF강세'),
    'Green_Circle':          _sig(1.0,_B,'✅','BUY Circle','circle-open',11,'#00E676','Low',-1.2,'과매도 반등','WT과매도 교차+RSI<45'),
    'Bull_Divergence':       _sig(2.0,_B,'📈','Bull Div','triangle-up',12,'#AA00FF','Low',-2.0,'상승 다이버전스','가격 저점↓ vs WT 저점↑'),
    'RSI_Bull_Divergence':   _sig(1.5,_B,'📊','RSI Bull Div','triangle-up',11,'#CE93D8','Low',-1.8,'RSI 상승 다이버전스','가격 저점↓ vs RSI 저점↑'),
    'Squeeze_Fire_Buy':      _sig(1.5,_B,'💥','Squeeze BUY','star-diamond',14,'#00FFFF','Low',-1.5,'스퀴즈 매수','TTM Squeeze 해소+모멘텀 상방'),
    'Hidden_Bull_Div':       _sig(1.5,_B,'🔀','Hidden Bull','triangle-up',10,'#E040FB','Low',-1.6,'히든 상승 다이버전스','가격 저점↑ vs 오실레이터 저점↓+WT<-25'),
    'Volume_Climax_Buy':     _sig(2.0,_B,'🌊','Vol Climax BUY','hexagram',14,'#00BCD4','Low',-2.8,'거래량 클라이맥스 매수','평균3배 거래량+하락장대봉+WT과매도→반등'),
    'OBV_Div_Buy':           _sig(1.0,_B,'📊','OBV Div BUY','triangle-up',10,'#80DEEA','Low',-1.4,'OBV 다이버전스 매수','OBV-가격 상승 다이버전스+WT<-30'),
    'ADX_Momentum_Buy':      _sig(1.5,_B,'🚀','ADX Ignition','arrow-up',11,'#76FF03','Low',-1.4,'ADX 점화','ADX>20 돌파++DI>-DI'),
    'Bullish_Engulfing':     _sig(1.5,_B,'☀️','Bull Engulf','square',10,'#00E676','Low',-1.3,'상승 장악형','전일 하락캔들 감싸는 상승캔들+WT<-20'),
    'Hammer_Buy':            _sig(1.5,_B,'🔨','Hammer','triangle-up',11,'#4CAF50','Low',-1.3,'해머','하락추세 긴 아래꼬리+작은 몸통+WT<-20'),
    'Golden_Cross':          _sig(1.5,_B,'✨','Golden Cross','cross',12,'#FFD700','Low',-0.8,'골든 크로스','50MA>200MA+ADX>15+거래량'),
    'EMA_Pullback_Buy':      _sig(2.0,_B,'🎯','EMA Pullback','triangle-up',13,'#00BFA5','Low',-1.8,'EMA 눌림목','상승추세 EMA부근 조정 후 WT반등'),
    'Momentum_Ignition_Buy': _sig(2.5,_B,'🔥','Mom. Ignition','star-diamond',15,'#FF6D00','Low',-2.5,'모멘텀 점화','장대양봉>ATR×1.5+거래량>2.5배+BB돌파'),
    'SuperTrend_Buy':        _sig(1.5,_B,'📈','ST Flip Bull','arrow-up',12,'#00E5FF','Low',-1.5,'슈퍼트렌드 강세','SuperTrend 위로 돌파'),
    'VWAP_Bounce_Buy':       _sig(1.5,_B,'🏦','VWAP Bounce','triangle-up',11,'#00E5FF','Low',-1.3,'VWAP 반등','VWAP 복귀+WT교차+거래량'),
    'Parabolic_Bottom_Buy':  _sig(3.0,_B,'🧊','Parabolic Bot','diamond',16,'#00FFFF','Low',-3.0,'포물선 바닥','WT1<-85 꺾임+양봉 또는 BB극단이격'),
    'MACD_Cross_Buy':        _sig(1.0,_B,'〽️','MACD Cross','triangle-up',9,'#4CAF50','Low',-1.0,'MACD 골든크로스','MACD>시그널 상향교차(0선 하방)'),
    'StochRSI_Cross_Buy':    _sig(0.8,_B,'🔄','StRSI Cross','circle-open',8,'#81C784','Low',-0.8,'StochRSI 매수교차','StochK>StochD(과매도 존)'),
    'Three_Candle_Strike_Buy':_sig(1.8,_B,'🎰','3-Strike BUY','star',12,'#00E676','Low',-1.6,'3연속 반전','3연속 하락 후 감싸는 상승캔들'),
    # ── SELL ──
    'Blood_Diamond':         _sig(3.0,_S,'🩸','BLOOD DIA','diamond',18,'#DC143C','High',3.0,'최강 매도','RSI>70+MFI>70+WT1>60+하락 다이버전스'),
    'Red_Dot_T1':            _sig(2.5,_S,'🔴','SELL T1','circle',16,'#FF1744','High',2.5,'강한 매도','WT과매수 하락교차+RSI>70+MFI>70+MF>0'),
    'Red_Dot_T2':            _sig(2.0,_S,'🟥','SELL T2','circle',13,'#FF5252','High',2.2,'매도','WT과매수+RSI또는MFI>68'),
    'Red_Diamond':           _sig(2.0,_S,'🔸','RED DIA','diamond',14,'#ff3333','High',1.8,'추세 매도','WT2≥0 하락교차+HTF약세'),
    'Red_Circle':            _sig(1.0,_S,'⛔','SELL Circle','circle-open',11,'#FF1744','High',1.2,'과매수 하락','WT과매수 하락교차+RSI>55'),
    'Bear_Divergence':       _sig(2.0,_S,'📉','Bear Div','triangle-down',12,'#AA00FF','High',2.0,'하락 다이버전스','가격 고점↑ vs WT 고점↓'),
    'RSI_Bear_Divergence':   _sig(1.5,_S,'📉','RSI Bear Div','triangle-down',11,'#CE93D8','High',1.8,'RSI 하락 다이버전스','가격 고점↑ vs RSI 고점↓'),
    'Squeeze_Fire_Sell':     _sig(1.5,_S,'🧨','Squeeze SELL','star-diamond',14,'#FF6600','High',1.5,'스퀴즈 매도','TTM Squeeze 해소+모멘텀 하방'),
    'Hidden_Bear_Div':       _sig(1.5,_S,'🔁','Hidden Bear','triangle-down',10,'#E040FB','High',1.6,'히든 하락 다이버전스','가격 고점↓ vs 오실레이터 고점↑+WT>25'),
    'Volume_Climax_Sell':    _sig(2.0,_S,'🌋','Vol Climax SELL','hexagram',14,'#FF5722','High',2.8,'거래량 클라이맥스 매도','평균3배 거래량+상승장대봉+WT과매수→하락'),
    'OBV_Div_Sell':          _sig(1.0,_S,'🔻','OBV Div SELL','triangle-down',10,'#FFAB91','High',1.4,'OBV 다이버전스 매도','OBV-가격 하락 다이버전스+WT>30'),
    'ADX_Momentum_Sell':     _sig(1.5,_S,'💨','ADX Down','arrow-down',11,'#FF3D00','High',1.4,'ADX 하락 점화','ADX>20 돌파+-DI>+DI'),
    'Bearish_Engulfing':     _sig(1.5,_S,'🌑','Bear Engulf','x',10,'#D50000','High',1.3,'하락 장악형','전일 상승캔들 감싸는 하락캔들+WT>20'),
    'ShootingStar_Sell':     _sig(1.5,_S,'⭐','Shooting Star','triangle-down',11,'#FF5252','High',1.3,'슈팅스타','상승추세 긴 위꼬리+작은 몸통+WT>20'),
    'Death_Cross':           _sig(1.5,_S,'☠️','Death Cross','cross',12,'#FF1744','High',0.8,'데드 크로스','50MA<200MA+ADX>15+거래량'),
    'SuperTrend_Sell':       _sig(2.0,_S,'📉','ST Flip Bear','arrow-down',12,'#FF1744','High',1.5,'슈퍼트렌드 약세','SuperTrend 아래로 돌파'),
    'Parabolic_Top_Sell':    _sig(3.0,_S,'🌡️','Parabolic Top','diamond',16,'#FF0000','High',3.0,'포물선 천장','WT1>85 꺾임+음봉 또는 BB극단이격'),
    'EMA_Pullback_Sell':     _sig(2.0,_S,'🎯','EMA PB Sell','triangle-down',13,'#FF6E40','High',1.8,'EMA 되돌림 매도','하락추세 EMA부근 반등 후 WT재하락'),
    'Momentum_Ignition_Sell':_sig(2.5,_S,'💣','Mom. Ign Sell','star-diamond',15,'#D50000','High',2.5,'모멘텀 점화 매도','장대음봉>ATR×1.5+거래량>2.5배+BB돌파'),
    'VWAP_Reject_Sell':      _sig(1.5,_S,'🏛️','VWAP Reject','triangle-down',11,'#FF6E40','High',1.3,'VWAP 저항','VWAP 실패 후 하락+WT교차+거래량'),
    'MACD_Cross_Sell':       _sig(1.0,_S,'〽️','MACD Dead','triangle-down',9,'#E57373','High',1.0,'MACD 데드크로스','MACD<시그널 하향교차(0선 상방)'),
    'StochRSI_Cross_Sell':   _sig(0.8,_S,'🔄','StRSI Dead','circle-open',8,'#EF9A9A','High',0.8,'StochRSI 매도교차','StochK<StochD(과매수 존)'),
    'Three_Candle_Strike_Sell':_sig(1.8,_S,'🎰','3-Strike SELL','star',12,'#FF1744','High',1.6,'3연속 반전','3연속 상승 후 감싸는 하락캔들'),
}

COMPOSITE_SIGNALS = {
    'Ultra_Buy':  _sig(0,_B,'⚡','ULTRA BUY','star',20,'#FFD700','Low',-3.5,'울트라 매수','Confluence ≥6 또는 (≥5+동시 3개)'),
    'Strong_Buy': _sig(0,_B,'🔱','STRONG BUY','star',16,'#00E676','Low',-3.2,'스트롱 매수','Confluence 3.5~6'),
    'Ultra_Sell': _sig(0,_S,'🚨','ULTRA SELL','star',20,'#FF0000','High',3.5,'울트라 매도','Confluence ≤-6 또는 (≤-5+동시 3개)'),
    'Strong_Sell':_sig(0,_S,'⚠️','STRONG SELL','star',16,'#FF1744','High',3.2,'스트롱 매도','Confluence -6~-3.5'),
}

ALL_CHART_SIGNALS = {**SIGNAL_REGISTRY, **COMPOSITE_SIGNALS}

OB1, OB2, OS1, OS2 = 53, 60, -53, -60
ST_MIN_BAR = 12
_UA_LIST = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 Version/17.4 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36',
]

GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GEMINI_API_KEY)

COOLDOWN_MAP = {
    'Squeeze_Fire_Buy':5,'Squeeze_Fire_Sell':5,
    'Bullish_Engulfing':5,'Bearish_Engulfing':5,
    'Hammer_Buy':5,'ShootingStar_Sell':5,
    'Three_Candle_Strike_Buy':7,'Three_Candle_Strike_Sell':7,
    'ADX_Momentum_Buy':10,'ADX_Momentum_Sell':10,
    'EMA_Pullback_Buy':7,'EMA_Pullback_Sell':7,
    'Momentum_Ignition_Buy':10,'Momentum_Ignition_Sell':10,
    'Parabolic_Top_Sell':5,'Parabolic_Bottom_Buy':5,
    'VWAP_Bounce_Buy':7,'VWAP_Reject_Sell':7,
    'MACD_Cross_Buy':10,'MACD_Cross_Sell':10,
    'StochRSI_Cross_Buy':5,'StochRSI_Cross_Sell':5,
    'RSI_Bull_Divergence':10,'RSI_Bear_Divergence':10,
}

# ──────────────────────────────────────────
# 공통 유틸
# ──────────────────────────────────────────
def _recent(series, lb=3):
    return series.astype(float).rolling(lb+1, min_periods=1).max().fillna(0).astype(bool)

def _cooldown(sig, bars=5):
    vals = sig.astype(bool).values.copy()
    last = -bars - 1
    for i in range(len(vals)):
        if vals[i]:
            if (i - last) <= bars: vals[i] = False
            else: last = i
    return pd.Series(vals, index=sig.index)

def _volf(volume, ratio=0.5, period=20):
    return volume >= (volume.rolling(period, min_periods=5).mean() * ratio)

def _valid_fmt(ticker):
    return bool(re.match(r'^[A-Za-z]{1,5}([.\-][A-Za-z]{1,2})?$', ticker))

def _cls(val, lo, hi):
    return 'ind-bullish' if val < lo else ('ind-bearish' if val > hi else 'ind-neutral')

# ──────────────────────────────────────────
# 캐싱 함수 (V5.0: 티커별 캐시 무효화)
# ──────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def get_stock_data(ticker):
    url = f"https://swingtradebot.com/equities/{ticker.upper()}"
    for attempt in range(3):
        headers = {'User-Agent': random.choice(_UA_LIST), 'Referer': 'https://www.google.com/',
                   'Accept': 'text/html,application/xhtml+xml', 'Accept-Language': 'en-US,en;q=0.9'}
        try:
            time.sleep(random.uniform(1.0, 2.0) * (attempt + 1))
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code != 200:
                if attempt < 2: continue
                return None
            soup = BeautifulSoup(resp.text, 'html.parser')
            parts = []
            for tag, attrs, label, sep in [
                ('h2',{'itemprop':'headline'},'HEADLINE',' '),
                ('div',{'class_':'recap-body'},'DAILY RECAP',' '),
                (None,{'id':'recap-tour'},'RECAP TOUR',' '),
                (None,{'id':'indicators-tour'},'INDICATORS TOUR',' | '),
                ('table',{'id':'trend-table-tour'},'TREND ANALYSIS',' | '),
                ('table',{'id':'recent-signals-tour'},'RECENT SIGNALS',' | ')]:
                elem = soup.find(id=attrs['id']) if 'id' in attrs and not tag else soup.find(tag, attrs) if tag else None
                if elem: parts.append(f"#### [{label}]\n{elem.get_text(separator=sep, strip=True)}")
            for i, t in enumerate(soup.find_all('table', class_='table-sm')):
                if t.get('id') not in ['trend-table-tour','recent-signals-tour']:
                    parts.append(f"#### [EXTRA {i}]\n{t.get_text(separator=' | ', strip=True)}")
            return "\n\n".join(parts) if parts else None
        except Exception:
            if attempt < 2: continue
            return None
    return None

@st.cache_data(ttl=300, show_spinner=False)
def fetch_history(ticker, _ts=None):
    """_ts 파라미터로 캐시 무효화 제어"""
    return yf.Ticker(ticker).history(period="2y")

@st.cache_data(ttl=600, show_spinner=False)
def validate_ticker(ticker):
    try:
        info = yf.Ticker(ticker).info
        return info.get('regularMarketPrice') is not None or info.get('currentPrice') is not None
    except Exception:
        return False

@st.cache_data(ttl=300, show_spinner=False)
def compute_and_cache(ticker, _ts=None):
    df = fetch_history(ticker, _ts)
    if df.empty: return None
    return detect_all_signals(compute_indicators(df))

# ──────────────────────────────────────────
# 지표 계산 엔진 (통합)
# ──────────────────────────────────────────
def compute_rsi(series, period=14):
    d = series.diff(); g, l = d.clip(lower=0), -d.clip(upper=0)
    ag = g.ewm(alpha=1/period, min_periods=period).mean()
    al = l.ewm(alpha=1/period, min_periods=period).mean()
    return 100 - (100 / (1 + ag / (al + 1e-10)))

def compute_mfi(h, l, c, v, period=14):
    tp = (h+l+c)/3; raw = tp*v; d = tp.diff()
    pos = raw.where(d>=0,0.0); neg = raw.where(d<0,0.0)
    return 100 - (100 / (1 + pos.rolling(period).sum() / (neg.rolling(period).sum()+1e-10)))

def compute_rsi_mfi(h, l, c, v, period=60):
    rf, mf = compute_rsi(c,20), compute_mfi(h,l,c,v,20)
    rs, ms = compute_rsi(c,period), compute_mfi(h,l,c,v,period)
    return (((rf-50)+(mf-50))/2)*0.6 + (((rs-50)+(ms-50))/2)*0.4

def compute_wavetrend(h, l, c, ch=9, avg=12, ma=3):
    ap = (h+l+c)/3
    esa = ap.ewm(span=ch, adjust=False).mean()
    d = abs(ap-esa).ewm(span=ch, adjust=False).mean()
    ci = (ap-esa)/(0.015*d+1e-10)
    wt1 = ci.ewm(span=avg, adjust=False).mean()
    wt2 = wt1.rolling(ma).mean()
    return wt1, wt2, (wt1>wt2)&(wt1.shift(1)<=wt2.shift(1)), (wt1<wt2)&(wt1.shift(1)>=wt2.shift(1))

def compute_stoch_rsi(c, rsi_l=14, st_l=14, ks=3, ds=3):
    rsi = compute_rsi(c, rsi_l)
    mn, mx = rsi.rolling(st_l).min(), rsi.rolling(st_l).max()
    k = (((rsi-mn)/(mx-mn+1e-10))*100).rolling(ks).mean()
    return k, k.rolling(ds).mean()

def compute_tr(h, l, c):
    pc = c.shift(1)
    return pd.concat([h-l, (h-pc).abs(), (l-pc).abs()], axis=1).max(axis=1)

def compute_adx(h, l, c, period=14):
    tr = compute_tr(h,l,c); ph, pl = h.shift(1), l.shift(1)
    pdm = pd.Series(np.where((h-ph)>(pl-l), np.maximum(h-ph,0), 0), index=h.index, dtype=float)
    mdm = pd.Series(np.where((pl-l)>(h-ph), np.maximum(pl-l,0), 0), index=h.index, dtype=float)
    atr = tr.ewm(alpha=1/period, min_periods=period).mean()
    pdi = 100*pdm.ewm(alpha=1/period, min_periods=period).mean()/(atr+1e-10)
    mdi = 100*mdm.ewm(alpha=1/period, min_periods=period).mean()/(atr+1e-10)
    dx = 100*(pdi-mdi).abs()/(pdi+mdi+1e-10)
    return dx.ewm(alpha=1/period, min_periods=period).mean(), pdi, mdi

def compute_obv(c, v):
    return (v * np.sign(c.diff()).fillna(0)).cumsum()

def compute_macd(c, fast=12, slow=26, sig=9):
    ml = c.ewm(span=fast, adjust=False).mean() - c.ewm(span=slow, adjust=False).mean()
    sl = ml.ewm(span=sig, adjust=False).mean()
    return ml, sl, ml - sl

def detect_pivot_divergence(price, osc, lb=60, pw=5, os_lim=None, ob_lim=None):
    n = len(price); pv, ov = price.values, osc.values; half = pw
    p_lo, p_hi = [], []
    for i in range(2*half, n):
        c = i - half; w = pv[i-2*half:i+1]
        if pv[c] == w.min(): p_lo.append((i, c))
        if pv[c] == w.max(): p_hi.append((i, c))
    bull_d = pd.Series(False, index=price.index)
    bear_d = pd.Series(False, index=price.index)
    hid_bull = pd.Series(False, index=price.index)
    hid_bear = pd.Series(False, index=price.index)
    for idx in range(1, len(p_lo)):
        ci, pi = p_lo[idx]; cj, pj = p_lo[idx-1]
        if not (pw*2 <= (pi-pj) <= lb): continue
        if (os_lim is None or ov[pi]<=os_lim) and pv[pi]<pv[pj] and ov[pi]>ov[pj]: bull_d.iloc[ci] = True
        if pv[pi]>pv[pj] and ov[pi]<ov[pj]: hid_bull.iloc[ci] = True
    for idx in range(1, len(p_hi)):
        ci, pi = p_hi[idx]; cj, pj = p_hi[idx-1]
        if not (pw*2 <= (pi-pj) <= lb): continue
        if (ob_lim is None or ov[pi]>=ob_lim) and pv[pi]>pv[pj] and ov[pi]<ov[pj]: bear_d.iloc[ci] = True
        if pv[pi]<pv[pj] and ov[pi]>ov[pj]: hid_bear.iloc[ci] = True
    return bull_d, bear_d, hid_bull, hid_bear

def compute_keltner(h, l, c, ema_l=20, atr_l=10, mult=1.5):
    mid = c.ewm(span=ema_l, adjust=False).mean()
    atr = compute_tr(h,l,c).rolling(atr_l).mean()
    return mid+atr*mult, mid, mid-atr*mult

def detect_ttm_squeeze(bb_u, bb_l, kc_u, kc_l, c, h, l, kc_m):
    sq = (bb_u<kc_u)&(bb_l>kc_l)
    fire = (~sq)&sq.shift(1).fillna(False)
    dm = (h.rolling(20).max()+l.rolling(20).min())/2
    mom = c - (dm+kc_m)/2
    return sq, fire&(mom>0), fire&(mom<0)

def detect_volume_climax(c, o, v, wt1, atr, vm=3.0):
    avg = v.rolling(20).mean()
    big = (c-o).abs() > atr*0.5
    ps = (v.shift(1)>avg.shift(1)*vm) & big.shift(1)
    return (ps&(c.shift(1)<o.shift(1))&(wt1.shift(1)<-40)&(c>o),
            ps&(c.shift(1)>o.shift(1))&(wt1.shift(1)>40)&(c<o))

def detect_engulfing(c, o, wt1, d='bull', wt_t=20):
    body = (c-o).abs(); big = body > body.rolling(20).mean()*0.8
    if d == 'bull':
        pb = c.shift(1)<o.shift(1)
        return pb&(c>o)&(o<=c.shift(1))&(c>=o.shift(1))&big&(wt1<-wt_t)
    else:
        pb = c.shift(1)>o.shift(1)
        return pb&(c<o)&(o>=c.shift(1))&(c<=o.shift(1))&big&(wt1>wt_t)

def detect_hammer_star(h, l, c, o, atr, wt1, d='hammer'):
    body = (c-o).abs(); total = h-l
    us = h - pd.concat([c,o],axis=1).max(axis=1)
    ls = pd.concat([c,o],axis=1).min(axis=1) - l
    sb = body < total*0.35; sig = total > atr*0.5
    if d == 'hammer':
        return sb&(ls>body*2)&(us<body*0.5)&sig&(c<c.shift(5))&(wt1<-20)
    else:
        return sb&(us>body*2)&(ls<body*0.5)&sig&(c>c.shift(5))&(wt1>20)

def detect_three_strike(c, o, wt1, d='buy'):
    if d == 'buy':
        td = (c.shift(3)<o.shift(3))&(c.shift(2)<o.shift(2))&(c.shift(1)<o.shift(1))
        return td&(c>o)&(c>=o.shift(3))&(o<=c.shift(1))&(wt1<0)
    else:
        tu = (c.shift(3)>o.shift(3))&(c.shift(2)>o.shift(2))&(c.shift(1)>o.shift(1))
        return tu&(c<o)&(c<=o.shift(3))&(o>=c.shift(1))&(wt1>0)

def compute_supertrend(h, l, c, period=10, mult=3.0):
    atr = compute_tr(h,l,c).rolling(period).mean()
    hl2 = (h+l)/2
    up_v = (hl2+mult*atr).values.copy(); dn_v = (hl2-mult*atr).values.copy()
    cl = c.values; n = len(c)
    st_v = np.full(n, np.nan); dir_v = np.zeros(n, dtype=int)
    fv = period
    if fv >= n: return pd.Series(np.nan, index=c.index), pd.Series(0, index=c.index, dtype=int)
    dir_v[fv] = 1; st_v[fv] = dn_v[fv]
    for i in range(fv+1, n):
        if dir_v[i-1]==1: dn_v[i] = max(dn_v[i], dn_v[i-1]) if not np.isnan(dn_v[i-1]) else dn_v[i]
        else: up_v[i] = min(up_v[i], up_v[i-1]) if not np.isnan(up_v[i-1]) else up_v[i]
        if dir_v[i-1]==1: dir_v[i], st_v[i] = (-1, up_v[i]) if cl[i]<dn_v[i] else (1, dn_v[i])
        else: dir_v[i], st_v[i] = (1, dn_v[i]) if cl[i]>up_v[i] else (-1, up_v[i])
    return pd.Series(st_v, index=c.index), pd.Series(dir_v, index=c.index)

def detect_ema_pullback(c, h, l, v, e8, e21, atr, wt1, wt2, d='buy'):
    slope = e21>e21.shift(5) if d=='buy' else e21<e21.shift(5)
    trend = ((e8>e21) if d=='buy' else (e8<e21)) & slope
    side = (c>e21) if d=='buy' else (c<e21)
    vok = _volf(v, 0.5); ar = atr/c
    if d == 'buy':
        t = (l<=e8*(1+ar*0.15))&(l>=e21*(1-ar*0.25))
        tr = _recent(t, 2)
        b = (c>=e8)&(c>c.shift(1))
        wok = (wt1>wt1.shift(1))&(wt1>wt2)&(wt1<60)
        return trend&side&tr&b&wok&vok
    else:
        t = (h>=e8*(1-ar*0.15))&(h<=e21*(1+ar*0.25))
        tr = _recent(t, 2)
        b = (c<=e8)&(c<c.shift(1))
        wok = (wt1<wt1.shift(1))&(wt1<wt2)&(wt1>-60)
        return trend&side&tr&b&wok&vok

def detect_momentum_ignition(c, o, v, bb, atr, e8, e21, wt1, d='buy'):
    body = (c-o).abs(); bb_ok = body > atr*1.5
    hv = v > v.rolling(20).mean()*2.5
    if d=='buy': return (c>o)&bb_ok&hv&(c>bb)&(e8>e21)&(wt1<50)
    else: return (c<o)&bb_ok&hv&(c<bb)&(e8<e21)&(wt1>-50)

def detect_vwap_bounce(c, vosc, wt1, wt2, v, atr, d='buy'):
    vok = _volf(v, 0.7)
    ap = (atr/c*100).clip(0.3, 3.0); dt = (ap*0.3).clip(0.3, 1.5)
    if d=='buy':
        return (vosc>0)&(vosc.shift(1)<-dt)&(wt1>wt2)&(wt1<30)&vok
    else:
        return (vosc<0)&(vosc.shift(1)>dt)&(wt1<wt2)&(wt1>-30)&vok

def detect_parabolic(c, o, wt1, bb, atr, d='bottom'):
    if d=='bottom':
        return (((wt1<-85)&(wt1>wt1.shift(1))&(c>o)&(c>c.shift(1)))|((c<bb-atr*1.5)&(c>o)))
    else:
        return (((wt1>85)&(wt1<wt1.shift(1))&(c<o)&(c<c.shift(1)))|((c>bb+atr*1.5)&(c<o)))

# ──────────────────────────────────────────
# Scoring
# ──────────────────────────────────────────
def compute_confluence(df, dw=5, df_factor=0.7):
    bm = {k:v['w'] for k,v in SIGNAL_REGISTRY.items() if v['dir']=='buy'}
    sm = {k:v['w'] for k,v in SIGNAL_REGISTRY.items() if v['dir']=='sell'}
    dk = np.array([df_factor**i for i in range(dw+1)])
    s = np.zeros(len(df)); bc = np.zeros(len(df)); sc = np.zeros(len(df))
    ones = np.ones(dw+1)
    for col, w in bm.items():
        if col in df.columns:
            raw = df[col].fillna(False).astype(float).values
            s += np.convolve(raw*w, dk, mode='full')[:len(raw)]
            bc += np.convolve(raw, ones, mode='full')[:len(raw)]
    for col, w in sm.items():
        if col in df.columns:
            raw = df[col].fillna(False).astype(float).values
            s -= np.convolve(raw*w, dk, mode='full')[:len(raw)]
            sc += np.convolve(raw, ones, mode='full')[:len(raw)]
    wt1 = df['WT1'].values
    s += np.where(wt1<OS1,1,0)+np.where(wt1<OS2,0.5,0)-np.where(wt1>OB1,1,0)-np.where(wt1>OB2,0.5,0)
    df['Confluence_Score'] = s
    df['Ultra_Buy'] = (s>=6)|(s>=5)&(bc>=3)
    df['Ultra_Sell'] = (s<=-6)|(s<=-5)&(sc>=3)
    df['Strong_Buy'] = (s>=3.5)&(~df['Ultra_Buy'])
    df['Strong_Sell'] = (s<=-3.5)&(~df['Ultra_Sell'])
    return s

def compute_proximity(wt1, wt2, rsi, mfi, rmfi, stk, sb, sbe):
    bp = pd.Series(0.0, index=wt1.index); sp = pd.Series(0.0, index=wt1.index)
    gap = (wt1-wt2).abs(); nc = gap<3
    cu = (wt1-wt2)>(wt1.shift(1)-wt2.shift(1)); cd = (wt1-wt2)<(wt1.shift(1)-wt2.shift(1))
    for cond, pts in [((wt1<-40)&nc,30),((wt1<-40)&cu&(gap<8),15),(wt1<OS2,20),
        ((wt1>=OS2)&(wt1<-40),10),(rsi<35,15),((rsi>=35)&(rsi<45),5),
        (mfi<35,15),((mfi>=35)&(mfi<45),5),(rmfi<-5,10),((rmfi>=-5)&(rmfi<0),5),
        (stk<20,10),((stk>=20)&(stk<35),5)]:
        bp += np.where(cond,pts,0)
    for cond, pts in [((wt1>40)&nc,30),((wt1>40)&cd&(gap<8),15),(wt1>OB1,20),
        ((wt1<=OB1)&(wt1>40),10),(rsi>65,15),((rsi<=65)&(rsi>55),5),
        (mfi>65,15),((mfi<=65)&(mfi>55),5),(rmfi>5,10),((rmfi<=5)&(rmfi>0),5),
        (stk>80,10),((stk<=80)&(stk>65),5)]:
        sp += np.where(cond,pts,0)
    bp, sp = bp.clip(upper=100), sp.clip(upper=100)
    net = bp - sp
    return (pd.Series(np.where(net>=0,bp,bp*np.where(sbe,.4,.55)), index=wt1.index),
            pd.Series(np.where(net<=0,sp,sp*np.where(sb,.4,.55)), index=wt1.index))

def compute_bias(meta, htf1, htf2):
    sc = 0.0
    for val, thr in [(meta['wt1'],[(-60,3),(-53,2),(0,1),(53,-1),(60,-2),(999,-3)]),
                     (meta['rsi'],[(-1,0),(30,2),(45,1),(55,0),(70,-1),(999,-2)]),
                     (meta['mfi'],[(-1,0),(30,2),(45,1),(55,0),(70,-1),(999,-2)])]:
        for t,p in thr:
            if val<=t: sc+=p; break
    mf = meta['mf_area']
    sc += 2 if mf<-5 else (1 if mf<0 else (-2 if mf>5 else (-1 if mf>0 else 0)))
    stk = meta.get('stochk',50)
    sc += 1.5 if stk<20 else (0.5 if stk<35 else (-1.5 if stk>80 else (-0.5 if stk>65 else 0)))
    sc += (1 if htf1 else -1) + (1.5 if htf2 else -1.5)
    if sc>=8: return 'STRONG BUY', sc
    elif sc>=3: return 'BUY', sc
    elif sc>=-3: return 'NEUTRAL', sc
    elif sc>=-8: return 'SELL', sc
    else: return 'STRONG SELL', sc

def compute_signal_stats(df, col, fwd_days=(5,10,20), min_n=5):
    if col not in df.columns: return None
    mask = df[col].fillna(False).values.astype(bool)
    if mask.sum()<min_n: return None
    c = df['Close'].values; stats = {'count': int(mask.sum())}
    for n in fwd_days:
        if n>=len(c): stats[f'{n}d_avg']=stats[f'{n}d_winrate']=stats[f'{n}d_median']=None; continue
        fwd = np.full(len(c), np.nan)
        fwd[:len(c)-n] = (c[n:]-c[:len(c)-n])/c[:len(c)-n]*100
        v = fwd[mask]; v = v[~np.isnan(v)]
        if len(v)>=min_n:
            stats[f'{n}d_avg']=float(np.mean(v)); stats[f'{n}d_winrate']=float(np.sum(v>0)/len(v)*100)
            stats[f'{n}d_median']=float(np.median(v))
        else: stats[f'{n}d_avg']=stats[f'{n}d_winrate']=stats[f'{n}d_median']=None
    return stats

def compute_all_stats(df_v):
    tgt = {k:v['dir'] for k,v in SIGNAL_REGISTRY.items()}
    tgt.update({'Ultra_Buy':'buy','Strong_Buy':'buy','Ultra_Sell':'sell','Strong_Sell':'sell'})
    return {s:{**r,'direction':d} for s,d in tgt.items() if (r:=compute_signal_stats(df_v,s)) and r['count']>0}

# ──────────────────────────────────────────
# 지표 + 시그널 파이프라인
# ──────────────────────────────────────────
def compute_indicators(df):
    c, h, l, v = df['Close'], df['High'], df['Low'], df['Volume']
    for ma in [5,20,50,100,125,200]: df[f'MA{ma}'] = c.rolling(ma).mean()
    df['EMA8'] = c.ewm(span=8, adjust=False).mean()
    df['EMA21'] = c.ewm(span=21, adjust=False).mean()
    df['BB_Mid'] = df['MA20']
    s20 = c.rolling(20).std()
    df['BB_Up'], df['BB_Low'] = df['BB_Mid']+s20*2, df['BB_Mid']-s20*2
    df['ATR'] = compute_tr(h,l,c).rolling(14).mean()
    df['SuperTrend'], df['ST_Direction'] = compute_supertrend(h,l,c)
    wt1, wt2, wu, wd = compute_wavetrend(h,l,c)
    df['WT1'], df['WT2'], df['WT_Up'], df['WT_Down'] = wt1, wt2, wu, wd
    df['RSI'] = compute_rsi(c, 14)
    df['StochK'], df['StochD'] = compute_stoch_rsi(c)
    df['MFI'] = compute_mfi(h,l,c,v,14)
    df['RSI_MFI'] = compute_rsi_mfi(h,l,c,v,60)
    df['VWAP_Osc'] = ((c*v).rolling(20).sum()/(v.rolling(20).sum()+1e-10))
    df['VWAP_Osc'] = ((c - df['VWAP_Osc'])/(df['VWAP_Osc']+1e-10))*100
    df['ADX'], df['Plus_DI'], df['Minus_DI'] = compute_adx(h,l,c)
    df['OBV'] = compute_obv(c, v)
    df['KC_Upper'], df['KC_Mid'], df['KC_Lower'] = compute_keltner(h,l,c)
    df['MACD_Line'], df['MACD_Signal'], df['MACD_Hist'] = compute_macd(c)
    return df

def detect_all_signals(df):
    H,L,C,O,V = df['High'],df['Low'],df['Close'],df['Open'],df['Volume']
    e8, e21, m50, m200 = df['EMA8'], df['EMA21'], df['MA50'], df['MA200']
    wt1, wt2 = df['WT1'], df['WT2']
    atr = df['ATR']

    # HTF Trend
    htf1 = (e8>e21)&(e21>e21.shift(5))
    htf2 = (C>m50)&(m50>m50.shift(10))

    wun = _recent(df['WT_Up'],2); wdn = _recent(df['WT_Down'],2)
    wur = _recent(df['WT_Up'],3); wdr = _recent(df['WT_Down'],3)
    vok = _volf(V, 0.5)

    # Regime
    sb = (df['ADX']>25)&(df['Plus_DI']>df['Minus_DI'])&(C>m50)
    sbe = (df['ADX']>25)&(df['Minus_DI']>df['Plus_DI'])&(C<m50)
    xb = sb&(C>m200)&(m50>m50.shift(5))
    xbe = sbe&(C<m200)&(m50<m50.shift(5))

    mf_b = df['RSI_MFI']>-10; mf_s = df['RSI_MFI']<10

    para_top = detect_parabolic(C,O,wt1,df['BB_Up'],atr,'top')
    para_bot = detect_parabolic(C,O,wt1,df['BB_Low'],atr,'bottom')

    st_fb = (df['ST_Direction']==-1)&(df['ST_Direction'].shift(1)==1)
    st_fb.iloc[:ST_MIN_BAR] = False
    st_bo = _recent(st_fb, 3)

    st_fb2 = (df['ST_Direction']==1)&(df['ST_Direction'].shift(1)==-1)
    st_fb2.iloc[:ST_MIN_BAR] = False
    st_bu = _recent(st_fb2, 3)

    # Shields
    ss_b = sb&(~para_top)&(~st_bo)
    ss_x = xb&(~para_top)&(~st_bo)
    bs_b = sbe&(~para_bot)&(~st_bu)
    bs_x = xbe&(~para_bot)&(~st_bu)

    # ── Core WT ──
    df['Green_Dot_T1'] = wun&(wt1<=OS1)&(df['RSI']<30)&(df['MFI']<30)&(df['RSI_MFI']<0)&(~bs_x)&vok
    df['Green_Dot_T2'] = wun&(wt1<=OS1)&((df['RSI']<32)|(df['MFI']<32))&~df['Green_Dot_T1']&(~bs_b)&vok
    _gd = df['Green_Dot_T1']|df['Green_Dot_T2']

    df['Red_Dot_T1'] = wdn&(wt1>=OB1)&(df['RSI']>70)&(df['MFI']>70)&(df['RSI_MFI']>0)&(~ss_x)&vok
    df['Red_Dot_T2'] = wdn&(wt1>=OB1)&((df['RSI']>68)|(df['MFI']>68))&~df['Red_Dot_T1']&(~ss_b)&vok
    _rd = df['Red_Dot_T1']|df['Red_Dot_T2']

    df['Blue_Diamond'] = (wt2<=0)&wun&htf1&htf2&(~bs_b)&mf_b&vok
    df['Red_Diamond'] = (wt2>=0)&wdn&~htf1&~htf2&(~ss_b)&mf_s&vok
    df['Green_Circle'] = wun&(wt1<=OS1)&~_gd&(~bs_b)&vok&(df['RSI']<45)
    df['Red_Circle'] = wdn&(wt1>=OB1)&~_rd&(~ss_b)&vok&(df['RSI']>55)

    # ── Divergences (WT + RSI + Hidden) ──
    bd, brd, hb, hbr = detect_pivot_divergence(C, wt1, 60, 5, OS1, OB1)
    bdr = _recent(bd,3); brdr = _recent(brd,3)
    rbd, rbrd, _, _ = detect_pivot_divergence(C, df['RSI'], 60, 5, 35, 65)

    # OBV div
    obd, obrd, _, _ = detect_pivot_divergence(C, df['OBV'], 60, 5)

    df['Gold_Dot'] = df['Green_Dot_T1']&(wt1<=OS2)&bdr
    df['Blood_Diamond'] = df['Red_Dot_T1']&(wt1>=OB2)&brdr
    df['Bull_Divergence'] = bd&wur&~_gd&~df['Gold_Dot']&(~bs_b)&vok
    df['Bear_Divergence'] = brd&wdr&~_rd&(~ss_b)&vok
    df['RSI_Bull_Divergence'] = rbd&(wt1<-20)&(~bs_b)&vok&~bd
    df['RSI_Bear_Divergence'] = rbrd&(wt1>20)&(~ss_b)&vok&~brd
    df['Hidden_Bull_Div'] = hb&(wt1<-25)&htf2&(~bs_x)
    df['Hidden_Bear_Div'] = hbr&(wt1>25)&~htf2&(~ss_x)
    df['OBV_Div_Buy'] = obd&(wt1<-30)&(~bs_x)
    df['OBV_Div_Sell'] = obrd&(wt1>30)&(~ss_x)

    # ── TTM Squeeze ──
    sq_on, sq_fb, sq_fs = detect_ttm_squeeze(df['BB_Up'],df['BB_Low'],df['KC_Upper'],df['KC_Lower'],C,H,L,df['KC_Mid'])
    df['Squeeze_On'] = sq_on
    df['Squeeze_Fire_Buy'] = sq_fb&(~bs_b)&vok
    df['Squeeze_Fire_Sell'] = sq_fs&(~ss_b)&vok

    # ── Volume Climax ──
    df['Volume_Climax_Buy'], df['Volume_Climax_Sell'] = detect_volume_climax(C,O,V,wt1,atr)

    # ── ADX ──
    ax = (df['ADX']>20)&(df['ADX'].shift(1)<=20)
    df['ADX_Momentum_Buy'] = ax&(df['Plus_DI']>df['Minus_DI'])&(wt1>wt2)&vok
    df['ADX_Momentum_Sell'] = ax&(df['Minus_DI']>df['Plus_DI'])&(wt1<wt2)&vok

    # ── Candle Patterns ──
    df['Bullish_Engulfing'] = detect_engulfing(C,O,wt1,'bull')&(~bs_b)&vok
    df['Bearish_Engulfing'] = detect_engulfing(C,O,wt1,'bear')&(~ss_b)&vok
    df['Hammer_Buy'] = detect_hammer_star(H,L,C,O,atr,wt1,'hammer')&(~bs_b)&vok
    df['ShootingStar_Sell'] = detect_hammer_star(H,L,C,O,atr,wt1,'star')&(~ss_b)&vok
    df['Three_Candle_Strike_Buy'] = detect_three_strike(C,O,wt1,'buy')&(~bs_b)&vok
    df['Three_Candle_Strike_Sell'] = detect_three_strike(C,O,wt1,'sell')&(~ss_b)&vok

    # ── MA Cross ──
    gc = (m50>m200)&(m50.shift(1)<=m200.shift(1)); dc = (m50<m200)&(m50.shift(1)>=m200.shift(1))
    af = df['ADX']>15; vc = _volf(V, 0.7)
    df['Golden_Cross'] = gc&af&vc; df['Death_Cross'] = dc&af&vc

    # ── EMA Pullback ──
    df['EMA_Pullback_Buy'] = detect_ema_pullback(C,H,L,V,e8,e21,atr,wt1,wt2,'buy')
    df['EMA_Pullback_Sell'] = detect_ema_pullback(C,H,L,V,e8,e21,atr,wt1,wt2,'sell')

    # ── Momentum Ignition ──
    df['Momentum_Ignition_Buy'] = detect_momentum_ignition(C,O,V,df['BB_Up'],atr,e8,e21,wt1,'buy')
    df['Momentum_Ignition_Sell'] = detect_momentum_ignition(C,O,V,df['BB_Low'],atr,e8,e21,wt1,'sell')

    # ── SuperTrend ──
    df['SuperTrend_Buy'] = st_fb2; df['SuperTrend_Sell'] = st_fb

    # ── Parabolic ──
    vp = _volf(V, 1.0)
    df['Parabolic_Top_Sell'] = para_top&((df['WT_Down']|wdr)|((C<O)&(C<C.shift(1))))&vp
    df['Parabolic_Bottom_Buy'] = para_bot&((df['WT_Up']|wur)|((C>O)&(C>C.shift(1))))&vp

    # ── VWAP ──
    df['VWAP_Bounce_Buy'] = detect_vwap_bounce(C,df['VWAP_Osc'],wt1,wt2,V,atr,'buy')
    df['VWAP_Reject_Sell'] = detect_vwap_bounce(C,df['VWAP_Osc'],wt1,wt2,V,atr,'sell')

    # ── MACD Cross ──
    ml, ms = df['MACD_Line'], df['MACD_Signal']
    df['MACD_Cross_Buy'] = (ml>ms)&(ml.shift(1)<=ms.shift(1))&(ml<0)&(~bs_b)&vok
    df['MACD_Cross_Sell'] = (ml<ms)&(ml.shift(1)>=ms.shift(1))&(ml>0)&(~ss_b)&vok

    # ── StochRSI Cross ──
    sk, sd = df['StochK'], df['StochD']
    df['StochRSI_Cross_Buy'] = (sk>sd)&(sk.shift(1)<=sd.shift(1))&(sk<25)&(~bs_b)&vok
    df['StochRSI_Cross_Sell'] = (sk<sd)&(sk.shift(1)>=sd.shift(1))&(sk>75)&(~ss_b)&vok

    # ── Cooldown ──
    for sc, cd in COOLDOWN_MAP.items():
        if sc in df.columns: df[sc] = _cooldown(df[sc], cd)

    compute_confluence(df)
    df['Buy_Proximity'], df['Sell_Proximity'] = compute_proximity(wt1,wt2,df['RSI'],df['MFI'],df['RSI_MFI'],df['StochK'],sb,sbe)

    # State columns
    df['Strong_Bull'], df['Strong_Bear'] = sb, sbe
    df['Parabolic_Blowoff'] = para_top
    df['Parabolic_Bottom_Raw'] = para_bot
    df['ST_Bear_Override'] = st_bo
    df['Sell_Shield_Overridden'] = para_top | st_bo
    df['Buy_Shield_Overridden'] = para_bot | st_bu
    df['_HTF1_Bull'], df['_HTF2_Bull'] = htf1, htf2
    return df

# ──────────────────────────────────────────
# 차트 생성
# ──────────────────────────────────────────
def _highlight(fig, mask, idx, fill, txt=None, row=1):
    d = mask.astype(int).diff().fillna(0)
    starts = idx[d==1].tolist(); ends = idx[d==-1].tolist()
    if len(mask)>0 and mask.iloc[0]: starts.insert(0, idx[0])
    if len(mask)>0 and mask.iloc[-1]: ends.append(idx[-1])
    for s,e in zip(starts, ends):
        kw = dict(x0=s,x1=e,fillcolor=fill,line_width=0,row=row,col=1)
        if txt: kw.update(annotation_text=txt,annotation_position="top left",
                          annotation_font_size=8,annotation_font_color="#FF4444")
        fig.add_vrect(**kw)

def build_chart(dc, ticker, regime, shield):
    mac = {5:"#ff9900",20:'#f1c40f',50:'#e74c3c',100:'#9b59b6',125:'#3498db',200:'#2ecc71'}
    fig = make_subplots(rows=5, cols=1, shared_xaxes=True, vertical_spacing=0.02,
        row_heights=[.40,.10,.22,.14,.14],
        subplot_titles=("","","WaveTrend Oscillator","Money Flow","Confluence Score"))

    fig.add_trace(go.Candlestick(x=dc.index,open=dc['Open'],high=dc['High'],low=dc['Low'],
        close=dc['Close'],name="가격",increasing_line_color='#26a69a',decreasing_line_color='#ef5350'),row=1,col=1)

    for ma in [5,20,50,100,125,200]:
        fig.add_trace(go.Scatter(x=dc.index,y=dc[f'MA{ma}'],line=dict(color=mac[ma],width=1.2),name=f'{ma}일선'),row=1,col=1)
    for nm,col,clr,dash in [('EMA 8','EMA8','#00FFFF','dot'),('EMA 21','EMA21','#FF69B4','dot')]:
        fig.add_trace(go.Scatter(x=dc.index,y=dc[col],line=dict(color=clr,width=1.5,dash=dash),name=nm),row=1,col=1)

    for mc,clr,nm in [(dc['ST_Direction']==1,'#00E676','ST ▲'),(dc['ST_Direction']==-1,'#FF1744','ST ▼')]:
        fig.add_trace(go.Scatter(x=dc.index,y=dc['SuperTrend'].where(mc),line=dict(color=clr,width=2),name=nm,connectgaps=False),row=1,col=1)

    fig.add_trace(go.Scatter(x=dc.index,y=dc['BB_Up'],line=dict(color='gray',width=1,dash='dot'),name='BB 상단'),row=1,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['BB_Low'],line=dict(color='gray',width=1,dash='dot'),name='BB 하단',
        fill='tonexty',fillcolor='rgba(128,128,128,0.1)'),row=1,col=1)

    for col,clr,txt in [('Sell_Shield_Overridden','rgba(255,0,0,0.04)','🔓Sell OFF'),
                         ('Buy_Shield_Overridden','rgba(0,255,0,0.04)','🔓Buy OFF')]:
        om = dc.get(col, pd.Series(False, index=dc.index))
        if om.any(): _highlight(fig, om, dc.index, clr, txt, 1)

    enabled = st.session_state.get('enabled_signals', set(ALL_CHART_SIGNALS.keys()))
    def _atr(s): return dc.loc[s.index,'ATR'].fillna(dc['ATR'].median())

    for cn, cfg in ALL_CHART_SIGNALS.items():
        if cn not in dc.columns or cn not in enabled: continue
        if cn=='Green_Dot_T1': sig=dc[dc[cn]&~dc.get('Gold_Dot',False)]
        elif cn=='Ultra_Buy': sig=dc[dc[cn]&~dc.get('Gold_Dot',False)]
        elif cn=='Ultra_Sell': sig=dc[dc[cn]&~dc.get('Blood_Diamond',False)]
        else: sig=dc[dc[cn]]
        if sig.empty: continue
        yv = sig[cfg['base']] + _atr(sig)*cfg['atr_m']
        lw = 2 if cfg['sz']>=16 else (1.5 if cfg['sz']>=13 else 1)
        fig.add_trace(go.Scatter(x=sig.index,y=yv,mode='markers',
            marker=dict(symbol=cfg['sym'],size=cfg['sz'],color=cfg['clr'],
                line=dict(width=lw,color='white' if 'open' not in cfg['sym'] else cfg['clr'])),
            name=f"{cfg['icon']} {cfg['label']}"),row=1,col=1)

    # Volume
    br = dc['Close']<dc['Open']
    fig.add_trace(go.Bar(x=dc.index,y=dc['Volume'],marker_color=np.where(br,'#ef5350','#26a69a').tolist(),
        name="거래량",opacity=0.7),row=2,col=1)
    vcm = dc.get('Volume_Climax_Buy',pd.Series(False))|dc.get('Volume_Climax_Sell',pd.Series(False))
    vcd = dc[vcm]
    if not vcd.empty:
        fig.add_trace(go.Bar(x=vcd.index,y=vcd['Volume'],marker_color='#FFD700',name="Vol Climax",opacity=0.9),row=2,col=1)

    # WT
    fig.add_trace(go.Scatter(x=dc.index,y=dc['WT1'],line=dict(color='#00E676',width=2),name="WT1"),row=3,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['WT2'],line=dict(color='#FF1744',width=1.5,dash='dot'),name="WT2"),row=3,col=1)
    wd = dc['WT1']-dc['WT2']
    fig.add_trace(go.Bar(x=dc.index,y=wd,marker_color=np.where(wd>=0,'#00E676','#FF1744').tolist(),name="WT Hist",opacity=0.3),row=3,col=1)

    for ml, clr in [(['Green_Circle','Green_Dot_T1','Green_Dot_T2','Gold_Dot'],'#00E676'),
                     (['Red_Circle','Red_Dot_T1','Red_Dot_T2','Blood_Diamond'],'#FF1744')]:
        comb = pd.Series(False, index=dc.index)
        for mc in ml: comb |= dc.get(mc, pd.Series(False, index=dc.index))
        pts = dc[comb]
        if not pts.empty:
            fig.add_trace(go.Scatter(x=pts.index,y=pts['WT1'],mode='markers',
                marker=dict(symbol='circle',size=10,color=clr,line=dict(width=1,color='white')),
                showlegend=False),row=3,col=1)

    for lv,c,d in [(OB2,'#ff3333','dash'),(OB1,'#ff3333','solid'),(0,'gray','dot'),(OS1,'#00bfff','solid'),(OS2,'#00bfff','dash')]:
        fig.add_hline(y=lv,line_dash=d,line_color=c,line_width=1,row=3,col=1)
    wmx = max(float(dc['WT1'].max()),100)+10; wmn = min(float(dc['WT1'].min()),-100)-10
    fig.add_hrect(y0=OB1,y1=wmx,fillcolor="rgba(255,23,68,0.08)",line_width=0,row=3,col=1)
    fig.add_hrect(y0=wmn,y1=OS1,fillcolor="rgba(0,191,255,0.08)",line_width=0,row=3,col=1)
    if 'Squeeze_On' in dc.columns:
        _highlight(fig, dc['Squeeze_On'], dc.index, "rgba(255,255,0,0.05)", None, 3)

    rmfi = dc['RSI_MFI']
    fig.add_trace(go.Bar(x=dc.index,y=rmfi,marker_color=np.where(rmfi>=0,'#3ee145','#ff3d2e').tolist(),
        name="Money Flow",opacity=0.7),row=4,col=1)
    fig.add_hline(y=0,line_dash="solid",line_color="gray",line_width=1,row=4,col=1)

    conf = dc['Confluence_Score']
    fig.add_trace(go.Bar(x=dc.index,y=conf,
        marker_color=np.where(conf>=3.5,'#00E676',np.where(conf<=-3.5,'#FF1744','#FFC107')).tolist(),
        name="Confluence",opacity=0.8),row=5,col=1)
    for lv,c,d in [(6,'#00E676','dash'),(-6,'#FF1744','dash'),(3.5,'#00E676','dot'),(-3.5,'#FF1744','dot'),(0,'gray','solid')]:
        fig.add_hline(y=lv,line_dash=d,line_color=c,line_width=1 if d=='solid' else .8,row=5,col=1)

    stxt = f" | {shield}" if shield else ""
    fig.update_layout(
        title=dict(text=f"📊 {ticker.upper()} | 💎 Market Cipher B+ V5.0 | {regime}{stxt}",font=dict(size=14,color='#FAFAFA')),
        yaxis_title="USD",yaxis2_title="Vol",yaxis3_title="WT",yaxis4_title="MF",yaxis5_title="Conf",
        template="plotly_dark",margin=dict(l=0,r=0,t=50,b=0),height=1100,showlegend=True,
        legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="center",x=0.5,
                    font=dict(size=9,color='#AAAAAA'),bgcolor='rgba(0,0,0,0)'))
    fig.update(layout_xaxis_rangeslider_visible=False)
    for ann in fig['layout']['annotations']: ann['font']=dict(size=11,color='#888888')
    return fig

# ──────────────────────────────────────────
# 메타데이터 + 프롬프트
# ──────────────────────────────────────────
def build_metadata(dc, dv, ticker):
    lat, prev = dc.iloc[-1], dc.iloc[-2] if len(dc)>=2 else dc.iloc[-1]
    pc, pp = lat['Close']-prev['Close'], (lat['Close']-prev['Close'])/prev['Close']*100

    m4 = {k:float(lat[c]) for k,c in [('wt1','WT1'),('rsi','RSI'),('mfi','MFI'),('mf_area','RSI_MFI'),('stochk','StochK')]}
    h1 = bool(lat.get('_HTF1_Bull',False)); h2 = bool(lat.get('_HTF2_Bull',False))
    bias, bsc = compute_bias(m4, h1, h2)
    cf = float(dc['Confluence_Score'].iloc[-1])

    regime = 'STRONG BULL 🟢' if lat.get('Strong_Bull',False) else ('STRONG BEAR 🔴' if lat.get('Strong_Bear',False) else 'NEUTRAL ⚪')

    sp = []
    for cond, lab in [('Parabolic_Blowoff','🌡️ PARABOLIC TOP'),('ST_Bear_Override','📉 ST BEAR'),('Parabolic_Bottom_Raw','🧊 PARABOLIC BOT')]:
        if lat.get(cond, False): sp.append(lab)
    if not sp:
        if lat.get('Buy_Shield_Overridden',False): sp.append('🔓 BUY SHIELD OFF')
        if lat.get('Sell_Shield_Overridden',False): sp.append('🔓 SELL SHIELD OFF')
    shield = ' + '.join(sp)

    sig_checks = [(k,v['icon'],v['label'],v['dir']) for k,v in ALL_CHART_SIGNALS.items()]
    recent = []
    for ir, row in dc.tail(15).iterrows():
        ds = ir.strftime('%m/%d')
        for col, icon, lbl, side in sig_checks:
            if row.get(col, False): recent.append((icon, lbl, ds, side))

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
        'trend_regime':regime,'shield_status':shield,
        'supertrend_dir':int(lat.get('ST_Direction',0)),'supertrend_val':float(lat.get('SuperTrend',0)),
        'ema8':float(lat.get('EMA8',0)),'ema21':float(lat.get('EMA21',0)),
        'bb_up':float(lat.get('BB_Up',0)),'bb_low':float(lat.get('BB_Low',0)),
        'ma50':float(lat.get('MA50',0)),'ma200':float(lat.get('MA200',0)),
        'macd_line':float(lat.get('MACD_Line',0)),'macd_signal':float(lat.get('MACD_Signal',0)),
        'macd_hist':float(lat.get('MACD_Hist',0)),
    }, regime, shield

def build_prompt_text(dc, meta):
    lat = dc.iloc[-1]; rd = dc.tail(60)
    ps = ", ".join([f"'{d.strftime('%Y-%m-%d')}:{r['Close']:.2f}'" for d,r in rd.iterrows()])

    sl = []
    for ir, row in dc.tail(30).iterrows():
        dd = ir.strftime('%Y-%m-%d')
        for k, v in ALL_CHART_SIGNALS.items():
            if row.get(k, False): sl.append(f"{v['icon']} {v['label']} {dd}")
    st_text = "\n".join(sl) if sl else "최근 30일 내 주요 시그널 없음"

    bp, sp = meta['buy_proximity'], meta['sell_proximity']
    prox = f"Buy Prox={bp:.0f}%, Sell Prox={sp:.0f}%"
    if bp>=60: prox += " ⚠️매수임박!"
    if sp>=60: prox += " ⚠️매도임박!"
    sq = "Squeeze ON" if meta['squeeze_on'] else "Squeeze OFF"
    std = f"BULL▲({meta['supertrend_val']:.2f})" if meta['supertrend_dir']==1 else f"BEAR▼({meta['supertrend_val']:.2f})"
    shd = f"Shield: {meta['shield_status']}" if meta['shield_status'] else "Shield: NONE"

    inds = (f"WT1={lat['WT1']:.1f},WT2={lat['WT2']:.1f},RSI={lat['RSI']:.1f},MFI={lat['MFI']:.1f},"
        f"StochK={lat['StochK']:.1f},StochD={lat['StochD']:.1f},VWAP_Osc={lat['VWAP_Osc']:.2f},"
        f"MF={lat['RSI_MFI']:.1f},ADX={lat['ADX']:.1f},+DI={lat['Plus_DI']:.1f},-DI={lat['Minus_DI']:.1f},"
        f"EMA8={lat['EMA8']:.2f},EMA21={lat['EMA21']:.2f},ST={std},"
        f"BB=[{meta['bb_up']:.2f}/{meta['bb_low']:.2f}],MA50={meta['ma50']:.2f},MA200={meta['ma200']:.2f},"
        f"MACD={meta['macd_line']:.3f}/{meta['macd_signal']:.3f} H={meta['macd_hist']:.3f},"
        f"Conf={meta['confluence_score']:.1f},Bias={meta['overall_bias']}({meta['bias_score']:.1f}),"
        f"Trend={meta['trend_regime']},{shd},{prox},{sq}")

    stats = meta.get('all_signal_stats',{})
    st_txt = ""
    if stats:
        lines = []
        for sn,sv in sorted(stats.items(), key=lambda x:x[1]['count'], reverse=True)[:10]:
            wr=sv.get('10d_winrate'); avg=sv.get('10d_avg')
            if wr is not None: lines.append(f"  {sn}: {sv['count']}회, 10일 승률{wr:.0f}%, 평균{avg:+.1f}%")
        if lines: st_txt = "\n📌 [백테스트 (2년, 상위10)]\n" + "\n".join(lines)

    return f"{ps}\n\n📌 [지표]\n{inds}\n\n📌 [시그널]\n{st_text}{st_txt}"

# ──────────────────────────────────────────
# 통합 분석
# ──────────────────────────────────────────
def analyze(ticker, chart_days=252, refresh=False):
    try:
        ts = int(time.time()) if refresh else None
        df = compute_and_cache(ticker, ts)
        if df is None or df.empty: return None, "주가 데이터 없음", None
        dv = df.dropna(subset=['WT1','WT2'])
        dc = dv.tail(chart_days).copy()
        if dc.empty: return None, "차트 데이터 부족", None
        meta, regime, shield = build_metadata(dc, dv, ticker)
        fig = build_chart(dc, ticker, regime, shield)
        return fig, build_prompt_text(dc, meta), meta
    except Exception as e:
        return None, f"데이터 로딩 실패: {e}", None

# ──────────────────────────────────────────
# UI 렌더
# ──────────────────────────────────────────
_IND_T = {
    'wt1':[(-53,'극과매도'),(-20,'과매도'),(20,'중립'),(53,'과매수'),(999,'극과매수')],
    'rsi':[(30,'과매도'),(45,'약세'),(55,'중립'),(70,'강세'),(999,'과매수')],
    'mfi':[(30,'과매도'),(45,'약세'),(55,'중립'),(70,'강세'),(999,'과매수')],
    'stochk':[(20,'바닥'),(80,''),(999,'천장')],
}

def _ilbl(name, val):
    for t, l in _IND_T.get(name,[]):
        if val<=t: return l
    return ''

def render_price_header(meta):
    chg=meta['price_change']; cp=meta['price_change_pct']
    cc='price-change-up' if chg>=0 else 'price-change-down'
    ci='▲' if chg>=0 else '▼'
    vr=meta['volume']/meta['avg_volume'] if meta['avg_volume'] else 0
    cv=meta.get('confluence_score',0)
    sd=meta.get('supertrend_dir',0)
    sh=meta.get('shield_status','')
    mh=meta.get('macd_hist',0)

    specs=[
        (_cls(meta['wt1'],-20,20),f"WT:{meta['wt1']:.0f} {_ilbl('wt1',meta['wt1'])}"),
        (_cls(meta['rsi'],40,60),f"RSI:{meta['rsi']:.0f} {_ilbl('rsi',meta['rsi'])}"),
        (_cls(meta['mfi'],40,60),f"MFI:{meta['mfi']:.0f} {_ilbl('mfi',meta['mfi'])}"),
        ('ind-bullish' if meta['mf_area']<0 else ('ind-bearish' if meta['mf_area']>0 else 'ind-neutral'),f"MF:{meta['mf_area']:.1f}"),
        ('ind-bullish' if vr>1.5 else 'ind-neutral',f"Vol:{vr:.1f}x"),
        ('ind-bullish' if meta['adx']>25 else 'ind-neutral',f"ADX:{meta['adx']:.0f}"),
        (_cls(meta['stochk'],30,70),f"StK:{meta['stochk']:.0f} {_ilbl('stochk',meta['stochk'])}"),
        ('ind-bullish' if cv>=3.5 else ('ind-bearish' if cv<=-3.5 else 'ind-neutral'),f"Conf:{cv:.1f}"),
        ('ind-bullish' if sd==1 else 'ind-bearish',f"ST:{'▲' if sd==1 else '▼'}"),
        ('ind-bullish' if mh>0 else ('ind-bearish' if mh<0 else 'ind-neutral'),f"MACD:{mh:+.2f}"),
    ]
    ih="".join([f"<span class='indicator-mini {c}'>{l}</span>" for c,l in specs])
    if sh: ih+=f"<span class='indicator-mini ind-bearish' style='font-weight:700'>🔓 {sh}</span>"
    tr=meta.get('trend_regime','NEUTRAL ⚪')
    st.markdown(f"""<div class="price-header">
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <div><p class="price-label">💎 {meta['ticker']} · {meta['last_date']} · <b>{tr}</b></p>
            <p class="price-big" style="color:#FAFAFA">${meta['price']:.2f}
                <span class="{cc}" style="font-size:1rem;margin-left:8px">
                    {ci} {abs(chg):.2f} ({abs(cp):.2f}%)</span></p></div>
            <div style="text-align:right"><p class="price-label">ATR (변동성)</p>
            <p style="color:#FFC107;font-size:1.1rem;font-weight:600;margin:0">
                ${meta['atr']:.2f} ({meta['atr_pct']:.1f}%)</p></div></div>
        <div style="margin-top:10px;display:flex;gap:6px;flex-wrap:wrap">{ih}</div></div>""",
        unsafe_allow_html=True)

def render_bias(meta):
    bias=meta['overall_bias']; sc=meta.get('bias_score',0); cv=meta.get('confluence_score',0)
    styles={'STRONG BUY':('rgba(0,230,118,0.2)','#00E676','🟢🟢'),'BUY':('rgba(0,230,118,0.12)','#00E676','🟢'),
        'STRONG SELL':('rgba(255,23,68,0.2)','#FF1744','🔴🔴'),'SELL':('rgba(255,23,68,0.12)','#FF1744','🔴')}
    bg,clr,ico=styles.get(bias,('rgba(255,193,7,0.12)','#FFC107','🟠'))
    cc='#00E676' if cv>=3.5 else ('#FF1744' if cv<=-3.5 else '#FFC107')
    gp=max(0,min(100,((sc+13)/26)*100))
    st.markdown(f"""<div style="background:{bg};border-radius:10px;padding:12px 16px;text-align:center;margin:8px 0">
        <span style="font-size:1.2rem;font-weight:700;color:{clr}">{ico} 종합 판정: {bias} ({sc:.1f})</span><br>
        <span style="font-size:0.9rem;color:{cc};font-weight:600">📊 Confluence: {cv:.1f}</span>
        <div class="bias-gauge-track" style="margin:10px auto;max-width:300px">
            <div class="bias-gauge-needle" style="left:{gp}%"></div></div>
        <div style="display:flex;justify-content:space-between;max-width:300px;margin:0 auto">
            <span style="color:#FF1744;font-size:.65rem">STRONG SELL</span>
            <span style="color:#888;font-size:.65rem">NEUTRAL</span>
            <span style="color:#00E676;font-size:.65rem">STRONG BUY</span></div></div>""",
        unsafe_allow_html=True)

def render_alerts(meta):
    alerts=[]
    bp,sp=meta.get('buy_proximity',0),meta.get('sell_proximity',0)
    if bp>=70: alerts.append(('🟢⚡ 매수 시그널 매우 임박!','#00E676',bp))
    elif bp>=50: alerts.append(('🟢 매수 시그널 접근 중','#69F0AE',bp))
    if sp>=70: alerts.append(('🔴⚡ 매도 시그널 매우 임박!','#FF1744',sp))
    elif sp>=50: alerts.append(('🔴 매도 시그널 접근 중','#FF5252',sp))
    if meta.get('squeeze_on'): alerts.append(('💥 Squeeze ON — 변동성 폭발 임박','#FFFF00',80))
    for txt,clr,pct in alerts:
        w=min(pct,100)
        st.markdown(f"""<div style="background:rgba(255,255,255,0.03);border:1px solid #2D333B;border-radius:8px;padding:8px 14px;margin:4px 0">
            <div style="display:flex;justify-content:space-between;align-items:center">
                <span style="color:{clr};font-weight:600;font-size:.9rem">{txt}</span>
                <span style="color:{clr};font-weight:700;font-size:.85rem">{pct:.0f}%</span></div>
            <div style="background:#1A1D24;border-radius:3px;height:6px;margin-top:6px">
                <div style="background:{clr};width:{w}%;height:6px;border-radius:3px"></div></div></div>""",
            unsafe_allow_html=True)

def render_signals(meta):
    sigs=meta['recent_signals']
    if not sigs:
        st.markdown("""<div class="signal-card signal-card-neutral">
            <p style="margin:0;color:#FFC107;font-weight:600">🟠 최근 15일 내 주요 시그널 없음</p>
            <p style="margin:4px 0 0;color:#888;font-size:.85rem">관망 구간입니다.</p></div>""",unsafe_allow_html=True)
        return
    dg=OrderedDict()
    for icon,lbl,ds,side in sigs: dg.setdefault(ds,[]).append((icon,lbl,side))
    alls=meta.get('all_signal_stats',{})
    for ds in reversed(dg):
        group=dg[ds]; bc=sum(1 for _,_,s in group if s=='buy'); sc=sum(1 for _,_,s in group if s=='sell')
        ct='signal-card-buy' if bc>sc else ('signal-card-sell' if sc>bc else 'signal-card-neutral')
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
            <div style="margin-top:6px;display:flex;gap:4px;flex-wrap:wrap">{" ".join(parts)}</div></div>""",
            unsafe_allow_html=True)

def render_stats(meta):
    with st.expander("📊 백테스트 통계 (2년, 최소 5회)", expanded=True):
        alls=meta.get('all_signal_stats',{})
        if not alls: st.caption("통계 없음"); return
        def _side(title, data, is_sell=False):
            st.markdown(f"##### {title}")
            for sn,sv in sorted(data.items(), key=lambda x:x[1]['count'], reverse=True):
                wr=sv.get('10d_winrate'); av=sv.get('10d_avg')
                if wr is None: continue
                if is_sell:
                    r=100-wr; c='#FF1744' if r>55 else ('#FFC107' if r>45 else '#00E676')
                    lb=f"10일 하락 <span style='color:{c}'>{r:.0f}%</span>"
                else:
                    c='#00E676' if wr>55 else ('#FFC107' if wr>45 else '#FF1744')
                    lb=f"10일 상승 <span style='color:{c}'>{wr:.0f}%</span>"
                ic=ALL_CHART_SIGNALS.get(sn,{}).get('icon','')
                st.markdown(f"<span style='font-size:.82rem'>{ic} **{sn}** ({sv['count']}회) · {lb} · 평균{av:+.1f}%</span>",unsafe_allow_html=True)
        c1,c2=st.columns(2)
        with c1: _side("🟢 BUY",{k:v for k,v in alls.items() if v['direction']=='buy'})
        with c2: _side("🔴 SELL",{k:v for k,v in alls.items() if v['direction']=='sell'},True)

def render_analysis(msg):
    """V5.0: 탭 기반 레이아웃"""
    meta, fig = msg.get('meta'), msg.get('fig')
    if meta:
        render_price_header(meta)
        render_bias(meta)
        render_alerts(meta)

    if meta or fig:
        tab1, tab2, tab3 = st.tabs(["📊 차트", "🔔 시그널", "📈 통계"])
        with tab1:
            if fig: st.plotly_chart(fig, use_container_width=True, theme=None)
        with tab2:
            if meta: render_signals(meta)
        with tab3:
            if meta: render_stats(meta)

# ──────────────────────────────────────────
# 사이드바
# ──────────────────────────────────────────
with st.sidebar:
    st.markdown("## 💎 CipherX")
    st.markdown("<p style='color:#888;font-size:.8rem'>AI 주가 분석 · Market Cipher B+ v5.0</p>",unsafe_allow_html=True)
    st.markdown("---")

    st.markdown("### 📅 차트 기간")
    chart_period = st.radio("표시 기간",['3개월','6개월','1년','2년'],index=2,horizontal=True,key="period")
    chart_days = {'3개월':63,'6개월':126,'1년':252,'2년':504}[chart_period]

    st.markdown("---")

    with st.expander("🎛️ 시그널 필터",expanded=False):
        sb = st.checkbox("🟢 매수",value=True,key="sb")
        ss = st.checkbox("🔴 매도",value=True,key="ss")
        sc = st.checkbox("⭐ 복합",value=True,key="sc")
        mw = st.slider("최소 가중치",0.0,3.0,0.0,0.5,key="mw")
        enabled=set()
        for k,v in ALL_CHART_SIGNALS.items():
            if v['dir']=='buy' and not sb: continue
            if v['dir']=='sell' and not ss: continue
            if k in COMPOSITE_SIGNALS and not sc: continue
            if v['w']<mw and k not in COMPOSITE_SIGNALS: continue
            enabled.add(k)
        st.session_state['enabled_signals']=enabled
        st.caption(f"활성: {len(enabled)}개")

    if st.button("🗑️ 대화 초기화",use_container_width=True,type="secondary"):
        for key in ['messages','pending_ai_ticker','pending_ai_prompt','last_ticker','_refresh_ts']:
            st.session_state[key] = [{"role":"assistant","type":"text",
                "content":"안녕하세요! 💎 **CipherX** 입니다.\n\n분석할 **티커명**을 입력하세요."}] if key=='messages' else None
        st.rerun()

    st.markdown("---")
    st.markdown("### 📖 가이드")
    for et, sl in [("🟢 매수 신호",[k for k,v in ALL_CHART_SIGNALS.items() if v['dir']=='buy']),
                    ("🔴 매도 신호",[k for k,v in ALL_CHART_SIGNALS.items() if v['dir']=='sell'])]:
        with st.expander(et,expanded=False):
            for k in sl:
                info=ALL_CHART_SIGNALS[k]
                st.markdown(f"**{info['icon']} {info['label']}** (w={info['w']}) · "
                    f"<span style='color:#888;font-size:.82rem'>{info.get('kor','')}</span>",unsafe_allow_html=True)
                st.caption(info.get('desc',''))

    with st.expander("🛡️ 추세 필터",expanded=False):
        st.markdown("""
**레짐**: STRONG BULL 🟢 / STRONG BEAR 🔴 / NEUTRAL ⚪

**🔓 쉴드 오버라이드**:
- Parabolic Top/Bottom → 쉴드 강제 해제
- SuperTrend Flip → 해당 방향 쉴드 해제

**V5.0**: RSI Div · Hammer/ShootingStar · 3-Strike · 탭 UI · 캐시 개선
        """)

    st.markdown("<p style='color:#555;font-size:.7rem;text-align:center'>CipherX v5.0</p>",unsafe_allow_html=True)

# ──────────────────────────────────────────
# 세션 초기화
# ──────────────────────────────────────────
if 'messages' not in st.session_state:
    st.session_state.messages = [
        {"role":"assistant","type":"text",
         "content":"안녕하세요! 💎 **CipherX** 입니다.\n\n분석할 **티커명**을 입력하세요."}]
for key in ['pending_ai_ticker','pending_ai_prompt','last_ticker','_refresh_ts']:
    if key not in st.session_state: st.session_state[key] = None
if 'enabled_signals' not in st.session_state:
    st.session_state['enabled_signals'] = set(ALL_CHART_SIGNALS.keys())

# ──────────────────────────────────────────
# AI 프롬프트
# ──────────────────────────────────────────
def build_ai_prompt(ticker, phist, scraped):
    return f"""━━━━━━━━━━━━━
【 🎯 Role 】
━━━━━━━━━━━━━
당신은 월스트리트 20년+ 경력 베테랑 주식 애널리스트이자 펀드 매니저입니다.
기술적 분석과 시장 심리 파악에 탁월하며, Market Cipher B 지표 해석에 정통합니다.

---
━━━━━━━━━━━━━
【 🛠️ Task 】
━━━━━━━━━━━━━
아래 **제공된 데이터만으로** 심층 주가 분석 보고서를 작성하세요.
데이터에 없는 정보는 "데이터 미제공"으로 표기하세요.

💎 **시그널 신뢰도 계층**:
- **Tier 0** (Parabolic, SuperTrend Flip): 추세 무관, 쉴드 강제 해제
- **Tier 1** (Gold Dot, Blood Diamond): 극단적 수렴, 항상 유효
- **Tier 2** (T1, Divergence, Mom Ignition): 극단 역추세에서만 억제
- **Tier 3** (T2, Diamond, Circle, EMA PB 등): 강한 역추세에서 억제
→ 쿨다운 적용된 시그널 = 높은 신뢰도

🔥 **Confluence**: ≥6 Ultra Buy | 3.5~6 Strong Buy | ≤-6 Ultra Sell | -6~-3.5 Strong Sell
📡 **Proximity**: ≥70% 임박 | 50~70% 접근 | <50% 거리 있음
📊 **백테스트**: 승률 60%+ = 높은 신뢰도 | 50% 미만 = 주의

---
━━━━━━━━━━━━━
【 📥 Data 】
━━━━━━━━━━━━━
[티커: {ticker}]

📌 [주가+지표+시그널+통계]
{phist}

📌 [SwingTradeBot]
{scraped if scraped else '데이터 미제공'}

---
━━━━━━━━━━━━━
【 ✍️ Guidelines 】
━━━━━━━━━━━━━
① 한국어, 전문적+이해하기 쉽게 ② 확신형, 이모티콘(🔵🔴🟠)
③ Trend+시그널Tier+백테스트 연계 ④ 시나리오별 신뢰도(높음/중간/낮음)
⑤ MA/BB/SuperTrend 기반 지지/저항 ⑥ Proximity+Squeeze 반영

━━━━━━━━━━━━━
【 📄 Output 】
━━━━━━━━━━━━━

[🔵/🔴/🟠] [{ticker}] 분석: [핵심 한 줄]
[날짜], 전일 대비 [변동률]% [방향].

---
### 내용 요약
### 🛡️ 추세 상태 & 시그널 신뢰도
### 💎 마켓 사이퍼 B+ 시그널 분석
### 주가 및 거래량 분석
### 장중 기술적 지표
### 지지선 및 저항선
### 주가변동이유 및 이벤트
### 종합해석 및 전망
* 🔵 Bullish → 목표가. 신뢰도
* 🟠 Base. 신뢰도
* 🔴 Bearish → 목표가. 신뢰도
전략: 진입가 / 손절 / 분할매도 1차·2차
### 결론
### 다음 거래일 전망"""

# ──────────────────────────────────────────
# 메인
# ──────────────────────────────────────────
st.markdown("<h2 style='text-align:center;color:#fff;margin-bottom:20px'>💎 CipherX</h2>",unsafe_allow_html=True)

for i, msg in enumerate(st.session_state.messages):
    av = "✨" if msg["role"]=="assistant" else "🧑‍💻"
    with st.chat_message(msg["role"], avatar=av):
        if msg.get("type")=="analysis":
            st.markdown(msg.get("content",""))
            render_analysis(msg)
            if msg.get("prompt"):
                with st.expander("📝 프롬프트 확인",expanded=False):
                    st.code(msg["prompt"],language="markdown")
                    st_copy_to_clipboard(msg["prompt"],before_copy_label="📋 복사",after_copy_label="✅ 복사됨!")
        elif msg.get("type")=="report":
            with st.expander(f"📊 {msg.get('ticker','')} AI 분석 리포트",expanded=True):
                st.markdown(msg["content"])
            st.download_button("📥 다운로드",key=f"dl_{i}",
                data=msg["content"].encode('utf-8'),
                file_name=f"{msg.get('ticker','RPT').upper()}_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
                mime="text/markdown",use_container_width=True)
        else:
            st.markdown(msg.get("content",""))

# ──────────────────────────────────────────
# 처리 함수
# ──────────────────────────────────────────
def _run_ai():
    tp = st.session_state.pending_ai_ticker
    pp = st.session_state.pending_ai_prompt
    with st.chat_message("assistant",avatar="✨"):
        pb = st.progress(0,text="AI 분석 초기화...")
        try:
            pb.progress(10,text="Gemini 로딩...")
            model = genai.GenerativeModel('gemini-2.0-flash')
            pb.progress(20,text="분석 중...")
            resp = model.generate_content(pp, stream=True)
            pb.progress(40,text="리포트 생성 중...")
            rpt=""; rph=st.empty(); cc=0
            for chunk in resp:
                rpt+=chunk.text; rph.markdown(rpt+" ▌"); cc+=1
                pb.progress(min(40+cc*2,95),text="작성 중...")
            pb.progress(100,text="✅ 완료!"); time.sleep(0.5); pb.empty(); rph.empty()
            st.session_state.messages.append({"role":"assistant","type":"report","ticker":tp.upper(),"content":rpt})
            st.session_state.pending_ai_ticker = None
            st.session_state.pending_ai_prompt = None
            st.rerun()
        except Exception as e:
            pb.empty(); st.error(f"AI 오류: {e}")

def process_ticker(ticker_value, refresh=False):
    ticker_value = ticker_value.strip().upper()
    # V5.0: pending 상태 즉시 초기화 (충돌 방지)
    st.session_state.pending_ai_ticker = None
    st.session_state.pending_ai_prompt = None

    if not _valid_fmt(ticker_value):
        st.session_state.messages.append({"role":"user","type":"text","content":ticker_value})
        st.session_state.messages.append({"role":"assistant","type":"text",
            "content":f"⚠️ **{ticker_value}** — 올바른 티커 형식이 아닙니다. (영문 1~5자)"})
        st.rerun(); return

    if not validate_ticker(ticker_value):
        st.session_state.messages.append({"role":"user","type":"text","content":ticker_value})
        st.session_state.messages.append({"role":"assistant","type":"text",
            "content":f"⚠️ **{ticker_value}** — Yahoo Finance에서 찾을 수 없습니다."})
        st.rerun(); return

    st.session_state.messages.append({"role":"user","type":"text","content":ticker_value})
    st.session_state.last_ticker = ticker_value

    with st.chat_message("assistant",avatar="✨"):
        pg=st.progress(0,text=f"🌐 {ticker_value} 수집 시작...")
        pg.progress(15,text="📡 SwingTradeBot...")
        scraped = get_stock_data(ticker_value)
        pg.progress(40,text="📊 Yahoo Finance...")
        fig, phist, meta = analyze(ticker_value, chart_days, refresh)
        pg.progress(80,text="📝 프롬프트 생성...")
        if scraped or fig:
            prompt = build_ai_prompt(ticker_value, phist, scraped)
            st.session_state.messages.append({
                "role":"assistant","type":"analysis","ticker":ticker_value,
                "content":f"✅ **{ticker_value}** 분석 완료!",
                "fig":fig,"meta":meta,"prompt":prompt})
            st.session_state.pending_ai_ticker = ticker_value
            st.session_state.pending_ai_prompt = prompt
            pg.progress(100,text="✅ 완료!"); time.sleep(0.3); pg.empty()
            st.rerun()
        else:
            pg.empty()
            st.session_state.messages.append({"role":"assistant","type":"text",
                "content":f"⚠️ **{ticker_value}** 데이터 로딩 실패. 다른 티커를 시도하세요."})
            st.rerun()

# Action buttons
if st.session_state.last_ticker:
    lt = st.session_state.last_ticker
    c1, c2 = st.columns([3,1])
    with c1:
        if st.session_state.pending_ai_ticker and st.session_state.pending_ai_prompt:
            if st.button(f"🚀 {st.session_state.pending_ai_ticker.upper()} AI 심층 분석",
                         type="primary",use_container_width=True):
                _run_ai()
    with c2:
        if st.button(f"🔄 {lt}",type="secondary",use_container_width=True,key="re"):
            process_ticker(lt, refresh=True)
elif st.session_state.pending_ai_ticker and st.session_state.pending_ai_prompt:
    if st.button(f"🚀 {st.session_state.pending_ai_ticker.upper()} AI 심층 분석",
                 type="primary",use_container_width=True):
        _run_ai()

if ticker_input := st.chat_input("분석할 티커를 입력하세요 (예: IREN, TSLA, AAPL)"):
    process_ticker(ticker_input)