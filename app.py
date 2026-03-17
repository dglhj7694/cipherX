import streamlit as st
import google.generativeai as genai
import time
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

st.set_page_config(page_title="CipherX V10.1",page_icon="📈",layout="centered",initial_sidebar_state="collapsed")

st.markdown("""<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
html,body,[class*="css"]{font-family:'Pretendard','Noto Sans KR',sans-serif!important}
span[class*="material-symbols"],span[class*="material-icons"],i[class*="material-icons"],.stIcon,[data-testid="stIconMaterial"]{font-family:'Material Symbols Rounded','Material Icons',sans-serif!important}
.stApp{background-color:#0E1117}
p,div[data-testid="stMarkdownContainer"] p,div[data-testid="stChatMessageContent"] p,h1,h2,h3,h4,h5,h6,li{color:#FAFAFA!important}
div[data-testid="stCodeBlock"],pre,code{background-color:#1A1D24!important;color:#FAFAFA!important}
div[data-testid="stCodeBlock"] span{text-shadow:none!important}
div[data-testid="stCodeBlock"] span[style*="color: rgb(0, 0, 0)"],div[data-testid="stCodeBlock"] span[style*="color: black"],div[data-testid="stCodeBlock"] code>span:not([class]){color:#FAFAFA!important}
div[data-testid="stChatMessage"]:nth-child(even){background-color:#161A22;border-radius:12px;padding:5px 15px}
.block-container{padding-top:1rem!important;max-width:950px}
@media(max-width:768px){.block-container{padding-left:.5rem!important;padding-right:.5rem!important}.price-big{font-size:1.6rem!important}div[data-testid="stPlotlyChart"]{margin-left:-10px!important;margin-right:-10px!important}}
div.stButton>button[kind="primary"]{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%)!important;color:white!important;border:none!important;border-radius:12px!important;padding:.6rem 1.5rem!important;font-weight:600!important;font-size:1rem!important;transition:all .3s ease!important;width:100%}
div.stButton>button[kind="primary"]:hover{transform:translateY(-2px);box-shadow:0 8px 20px rgba(118,75,162,.4)!important}
div.stButton>button[kind="secondary"]{background-color:#1E2127!important;color:#E2E8F0!important;border:1px solid #333842!important;border-radius:12px!important;font-weight:500!important;transition:all .2s ease!important;width:100%}
div.stButton>button[kind="secondary"]:hover{border-color:#667eea!important;color:#667eea!important}
.streamlit-expanderHeader{background-color:#161A22!important;border-radius:10px!important;font-weight:600!important}
.streamlit-expanderHeader p{color:#414df2!important}
div[data-testid="stExpander"]{border:1px solid #2D333B!important;border-radius:10px!important;background-color:#161A22}
header{background-color:transparent!important}
div[data-testid="collapsedControl"]{display:flex!important;z-index:999999!important}
section[data-testid="stSidebar"]{background-color:#0A0D12;border-right:1px solid #1E2127}
section[data-testid="stSidebar"] .stMarkdown p{color:#AAA!important}
div[data-testid="stExpanderDetails"] h1{font-size:1.5rem!important;margin-bottom:.5rem!important;padding-bottom:.3rem!important;border-bottom:1px solid #2D333B}
div[data-testid="stExpanderDetails"] h2{font-size:1.3rem!important;margin-top:1.2rem!important;margin-bottom:.5rem!important}
div[data-testid="stExpanderDetails"] h3{font-size:1.15rem!important;margin-top:1.2rem!important;margin-bottom:.4rem!important;color:#82aaff!important}
div[data-testid="stExpanderDetails"] p,div[data-testid="stExpanderDetails"] li{font-size:.95rem!important;line-height:1.6!important;color:#D0D7DE!important;margin-bottom:.5rem!important}
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
# 🔧 시그널 레지스트리 v10.1 — 61 signals (확실한 BUY/SELL만)
# ──────────────────────────────────────────
_B, _S = 'buy', 'sell'
def _sig(w,d,icon,label,sym,sz,clr,base,atr_m,kor,desc):
    return {'w':w,'dir':d,'icon':icon,'label':label,'sym':sym,'sz':sz,'clr':clr,
            'base':base,'atr_m':atr_m,'kor':kor,'desc':desc}

SIGNAL_REGISTRY = {
    # ═══ MCB+ 매수 (16개) ═══
    'Gold_Dot':              _sig(3.0,_B,'🏆','GOLD DOT','circle',18,'#FFD700','Low',-3.0,'최강 매수','RSI<30+MFI<30+WT1<-60+상승다이버전스'),
    'Green_Dot_T1':          _sig(2.5,_B,'🟢','BUY T1','circle',16,'#00E676','Low',-2.5,'강한 매수','WT과매도교차+RSI<30+MFI<30+MF<0'),
    'Green_Dot_T2':          _sig(2.0,_B,'🟩','BUY T2','circle',13,'#69F0AE','Low',-2.2,'매수','WT과매도+RSI또는MFI<32'),
    'Blue_Diamond':          _sig(2.0,_B,'🔹','BLUE DIA','diamond',14,'#00bfff','Low',-1.8,'추세 매수','WT2≤0 상승교차+HTF강세'),
    'Bull_Divergence':       _sig(2.0,_B,'📈','Bull Div','triangle-up',12,'#AA00FF','Low',-2.0,'상승 다이버전스','가격↓ vs WT↑'),
    'RSI_Bull_Divergence':   _sig(1.5,_B,'📊','RSI Bull Div','triangle-up',11,'#CE93D8','Low',-1.8,'RSI 상승 다이버전스','가격↓ vs RSI↑'),
    'Squeeze_Fire_Buy':      _sig(1.5,_B,'💥','Squeeze BUY','star-diamond',14,'#00FFFF','Low',-1.5,'스퀴즈 매수','TTM Squeeze 해소+모멘텀↑'),
    'Hidden_Bull_Div':       _sig(1.5,_B,'🔀','Hidden Bull','triangle-up',10,'#E040FB','Low',-1.6,'히든 상승 다이버전스','가격↑ vs WT↓'),
    'Volume_Climax_Buy':     _sig(2.0,_B,'🌊','Vol Climax BUY','hexagram',14,'#00BCD4','Low',-2.8,'거래량 클라이맥스','3배거래량+하락봉+WT과매도→반등'),
    'ADX_Momentum_Buy':      _sig(1.5,_B,'🚀','ADX Ignition','arrow-up',11,'#76FF03','Low',-1.4,'ADX 점화','ADX>20돌파++DI>-DI'),
    'Bullish_Engulfing':     _sig(1.5,_B,'☀️','Bull Engulf','square',10,'#00E676','Low',-1.3,'상승 장악형','하락캔들감싸는 상승캔들+WT<-20'),
    'Golden_Cross':          _sig(1.5,_B,'✨','Golden Cross','cross',12,'#FFD700','Low',-0.8,'골든 크로스','50MA>200MA+ADX>15'),
    'EMA_Pullback_Buy':      _sig(2.0,_B,'🎯','EMA Pullback','triangle-up',13,'#00BFA5','Low',-1.8,'EMA 눌림목','상승추세 EMA조정후 WT반등'),
    'Momentum_Ignition_Buy': _sig(2.5,_B,'🔥','Mom. Ignition','star-diamond',15,'#FF6D00','Low',-2.5,'모멘텀 점화','장대양봉>ATR×1.5+거래량>2.5배'),
    'SuperTrend_Buy':        _sig(2.0,_B,'📈','ST Flip Bull','arrow-up',12,'#00E5FF','Low',-1.5,'슈퍼트렌드 강세','SuperTrend 위로 돌파'),
    'VWAP_Bounce_Buy':       _sig(1.5,_B,'🏦','VWAP Bounce','triangle-up',11,'#00E5FF','Low',-1.3,'VWAP 반등','VWAP 복귀+WT교차'),
    'Parabolic_Bottom_Buy':  _sig(3.0,_B,'🧊','Parabolic Bot','diamond',16,'#00FFFF','Low',-3.0,'포물선 바닥','WT1<-85 꺾임+양봉'),
    # ═══ MCB+ 매도 (16개) ═══
    'Blood_Diamond':         _sig(3.0,_S,'🩸','BLOOD DIA','diamond',18,'#DC143C','High',3.0,'최강 매도','RSI>70+MFI>70+WT1>60+하락다이버전스'),
    'Red_Dot_T1':            _sig(2.5,_S,'🔴','SELL T1','circle',16,'#FF1744','High',2.5,'강한 매도','WT과매수하락교차+RSI>70+MFI>70'),
    'Red_Dot_T2':            _sig(2.0,_S,'🟥','SELL T2','circle',13,'#FF5252','High',2.2,'매도','WT과매수+RSI또는MFI>68'),
    'Red_Diamond':           _sig(2.0,_S,'🔸','RED DIA','diamond',14,'#ff3333','High',1.8,'추세 매도','WT2≥0 하락교차+HTF약세'),
    'Bear_Divergence':       _sig(2.0,_S,'📉','Bear Div','triangle-down',12,'#AA00FF','High',2.0,'하락 다이버전스','가격↑ vs WT↓'),
    'RSI_Bear_Divergence':   _sig(1.5,_S,'📉','RSI Bear Div','triangle-down',11,'#CE93D8','High',1.8,'RSI 하락 다이버전스','가격↑ vs RSI↓'),
    'Squeeze_Fire_Sell':     _sig(1.5,_S,'🧨','Squeeze SELL','star-diamond',14,'#FF6600','High',1.5,'스퀴즈 매도','TTM Squeeze 해소+모멘텀↓'),
    'Hidden_Bear_Div':       _sig(1.5,_S,'🔁','Hidden Bear','triangle-down',10,'#E040FB','High',1.6,'히든 하락 다이버전스','가격↓ vs WT↑'),
    'Volume_Climax_Sell':    _sig(2.0,_S,'🌋','Vol Climax SELL','hexagram',14,'#FF5722','High',2.8,'거래량 클라이맥스','3배거래량+상승봉+WT과매수→하락'),
    'ADX_Momentum_Sell':     _sig(1.5,_S,'💨','ADX Down','arrow-down',11,'#FF3D00','High',1.4,'ADX 하락 점화','ADX>20돌파+-DI>+DI'),
    'Bearish_Engulfing':     _sig(1.5,_S,'🌑','Bear Engulf','x',10,'#D50000','High',1.3,'하락 장악형','상승캔들감싸는 하락캔들+WT>20'),
    'Death_Cross':           _sig(1.5,_S,'☠️','Death Cross','cross',12,'#FF1744','High',0.8,'데드 크로스','50MA<200MA+ADX>15'),
    'SuperTrend_Sell':       _sig(2.0,_S,'📉','ST Flip Bear','arrow-down',12,'#FF1744','High',1.5,'슈퍼트렌드 약세','SuperTrend 아래로 돌파'),
    'Parabolic_Top_Sell':    _sig(3.0,_S,'🌡️','Parabolic Top','diamond',16,'#FF0000','High',3.0,'포물선 천장','WT1>85 꺾임+음봉'),
    'EMA_Pullback_Sell':     _sig(2.0,_S,'🎯','EMA PB Sell','triangle-down',13,'#FF6E40','High',1.8,'EMA 되돌림 매도','하락추세 EMA반등후 WT재하락'),
    'Momentum_Ignition_Sell':_sig(2.5,_S,'💣','Mom. Ign Sell','star-diamond',15,'#D50000','High',2.5,'모멘텀 점화 매도','장대음봉>ATR×1.5+거래량>2.5배'),
    'VWAP_Reject_Sell':      _sig(1.5,_S,'🏛️','VWAP Reject','triangle-down',11,'#FF6E40','High',1.3,'VWAP 저항','VWAP 실패+WT교차'),
    # ═══ 캔들스틱 (4개) ═══
    'Hammer':               _sig(1.5,_B,'🔨','Hammer','triangle-up',11,'#00E676','Low',-1.5,'해머','긴하단꼬리+소형실체+WT<-20'),
    'Morning_Star':         _sig(2.0,_B,'🌅','MornStar','star',13,'#00E676','Low',-2.0,'모닝스타','큰음봉→소형봉→강한양봉'),
    'Shooting_Star':        _sig(1.5,_S,'🌠','ShootStar','triangle-down',11,'#FF1744','High',1.5,'슈팅스타','긴상단꼬리+소형실체+WT>20'),
    'Evening_Star':         _sig(2.0,_S,'🌆','EveStar','star',13,'#FF1744','High',2.0,'이브닝스타','큰양봉→소형봉→강한음봉'),
    # ═══ Outside Day (2개) ═══
    'Outside_Bullish':      _sig(1.5,_B,'💪','OutsideBull','square',11,'#00E676','Low',-1.5,'강세 아웃사이드','전일범위포함+양봉+WT<30'),
    'Outside_Bearish':      _sig(1.5,_S,'🥊','OutsideBear','square',11,'#FF1744','High',1.5,'약세 아웃사이드','전일범위포함+음봉+WT>-30'),
    # ═══ 200MA (2개) ═══
    'Cross_Above_200MA':    _sig(1.5,_B,'📈','X▲200MA','triangle-up',11,'#00BFA5','Low',-1.2,'200MA상향돌파','종가>200MA(전일≤)'),
    'Fell_Below_200MA':     _sig(1.5,_S,'📉','X▼200MA','triangle-down',11,'#D50000','High',1.2,'200MA하향이탈','종가<200MA(전일≥)'),
    # ═══ BB Squeeze End (2개) ═══
    'BB_Squeeze_End_Bull':  _sig(1.5,_B,'💥','SqEnd▲','star-diamond',12,'#00FFFF','Low',-1.5,'BB스퀴즈해소↑','BB확장+상승+WT↑'),
    'BB_Squeeze_End_Bear':  _sig(1.5,_S,'💥','SqEnd▼','star-diamond',12,'#FF6600','High',1.5,'BB스퀴즈해소↓','BB확장+하락+WT↓'),
    # ═══ 52주 (2개) ═══
    'New_52W_High':         _sig(1.5,_B,'🏔️','52W▲','star-triangle-up',12,'#FFD700','High',1.5,'52주신고가','52주최고가갱신'),
    'New_52W_Low':          _sig(1.5,_S,'🕳️','52W▼','star-triangle-down',12,'#B71C1C','Low',-1.5,'52주신저가','52주최저가갱신'),
    # ═══ Jeff Cooper (15개) ═══
    'Pullback_123_Bull':    _sig(2.0,_B,'🎯','123PB▲','triangle-up',12,'#00E676','Low',-1.8,'1,2,3풀백매수','ADX>30+DI↑+3일저점↓'),
    'Pullback_123_Bear':    _sig(2.0,_S,'🎯','123PB▼','triangle-down',12,'#FF1744','High',1.8,'1,2,3풀백매도','ADX>30+DI↓+3일고점↑'),
    'Setup_180_Bull':       _sig(2.0,_B,'🔄','180▲','star-diamond',13,'#00E676','Low',-2.0,'180매수셋업','전일하위25%→당일상위25%+MA위'),
    'Setup_180_Bear':       _sig(2.0,_S,'🔄','180▼','star-diamond',13,'#FF1744','High',2.0,'180매도셋업','전일상위25%→당일하위25%+MA아래'),
    'Boomer_Buy':           _sig(2.0,_B,'💣','Boomer▲','star',12,'#00E676','Low',-1.8,'부머매수','ADX>30+DI↑+2일인사이드→돌파'),
    'Boomer_Sell':          _sig(2.0,_S,'💣','Boomer▼','star',12,'#FF1744','High',1.8,'부머매도','ADX>30+DI↓+2일인사이드→이탈'),
    'Expansion_BO':         _sig(2.5,_B,'🚀','XBO','star-diamond',14,'#FFD700','Low',-2.5,'확장돌파','2개월신고가+9일최대범위'),
    'Expansion_BD':         _sig(2.5,_S,'💨','XBD','star-diamond',14,'#FF0000','High',2.5,'확장붕괴','2개월신저가+9일최대범위'),
    'Gilligans_Buy':        _sig(2.0,_B,'🏝️','Gilligan▲','hexagon',12,'#00BCD4','Low',-2.0,'길리건매수','갭다운2개월신저가→상위50%마감'),
    'Gilligans_Sell':       _sig(2.0,_S,'🏝️','Gilligan▼','hexagon',12,'#FF5722','High',2.0,'길리건매도','갭업2개월신고가→하위50%마감'),
    'Lizard_Bull':          _sig(1.5,_B,'🦎','Lizard▲','triangle-up',10,'#00E676','Low',-1.5,'리자드매수','시가종가상위25%+10일신저가'),
    'Lizard_Bear':          _sig(1.5,_S,'🦎','Lizard▼','triangle-down',10,'#FF1744','High',1.5,'리자드매도','시가종가하위25%+10일신고가'),
    'NonADX_123_Bull':      _sig(1.8,_B,'📐','nADX123▲','triangle-up',11,'#69F0AE','Low',-1.5,'비ADX풀백매수','주가>50MA+3일저점↓'),
    'NonADX_123_Bear':      _sig(1.8,_S,'📐','nADX123▼','triangle-down',11,'#FF5252','High',1.5,'비ADX풀백매도','주가<50MA+3일고점↑'),
    'Pocket_Pivot':         _sig(1.5,_B,'🧲','PocketPvt','triangle-up',11,'#7C4DFF','Low',-1.5,'포켓피봇','양봉+거래량>10일하락거래량최대+MA위'),
}

COMPOSITE_SIGNALS = {
    'Ultra_Buy':  _sig(0,_B,'⚡','ULTRA BUY','star',20,'#FFD700','Low',-3.5,'울트라 매수','Confluence≥6.5'),
    'Strong_Buy': _sig(0,_B,'🔱','STRONG BUY','star',16,'#00E676','Low',-3.2,'스트롱 매수','Confluence 3.5~6.5'),
    'Ultra_Sell': _sig(0,_S,'🚨','ULTRA SELL','star',20,'#FF0000','High',3.5,'울트라 매도','Confluence≤-6.5'),
    'Strong_Sell':_sig(0,_S,'⚠️','STRONG SELL','star',16,'#FF1744','High',3.2,'스트롱 매도','Confluence -6.5~-3.5'),
}
ALL_CHART_SIGNALS = {**SIGNAL_REGISTRY, **COMPOSITE_SIGNALS}
NEUTRAL_SIGNALS = set()
OB1, OB2, OS1, OS2 = 53, 60, -53, -60
ST_MIN_BAR = 12
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GEMINI_API_KEY)

COOLDOWN_MAP = {
    'Squeeze_Fire_Buy':5,'Squeeze_Fire_Sell':5,'Bullish_Engulfing':5,'Bearish_Engulfing':5,
    'ADX_Momentum_Buy':10,'ADX_Momentum_Sell':10,'EMA_Pullback_Buy':7,'EMA_Pullback_Sell':7,
    'Momentum_Ignition_Buy':10,'Momentum_Ignition_Sell':10,'Parabolic_Top_Sell':5,'Parabolic_Bottom_Buy':5,
    'VWAP_Bounce_Buy':7,'VWAP_Reject_Sell':7,'RSI_Bull_Divergence':10,'RSI_Bear_Divergence':10,
    'Hammer':5,'Shooting_Star':5,'Morning_Star':7,'Evening_Star':7,
    'Outside_Bullish':7,'Outside_Bearish':7,
    'Cross_Above_200MA':15,'Fell_Below_200MA':15,
    'BB_Squeeze_End_Bull':7,'BB_Squeeze_End_Bear':7,
    'New_52W_High':10,'New_52W_Low':10,
    'Pullback_123_Bull':7,'Pullback_123_Bear':7,'Setup_180_Bull':7,'Setup_180_Bear':7,
    'Boomer_Buy':10,'Boomer_Sell':10,'Expansion_BO':10,'Expansion_BD':10,
    'Gilligans_Buy':10,'Gilligans_Sell':10,'Lizard_Bull':5,'Lizard_Bear':5,
    'NonADX_123_Bull':7,'NonADX_123_Bear':7,'Pocket_Pivot':10,
}

SIGNAL_HIERARCHY = {
    'candle_bull': ['Morning_Star','Bullish_Engulfing','Hammer'],
    'candle_bear': ['Evening_Star','Bearish_Engulfing','Shooting_Star'],
    'cooper_bull': ['Expansion_BO','Pullback_123_Bull','Setup_180_Bull','Boomer_Buy','Gilligans_Buy','Lizard_Bull','NonADX_123_Bull'],
    'cooper_bear': ['Expansion_BD','Pullback_123_Bear','Setup_180_Bear','Boomer_Sell','Gilligans_Sell','Lizard_Bear','NonADX_123_Bear'],
}

TREND_IMMUNE_W = 2.0

# ── 유틸리티 ──
def _recent(s, lb=3): return s.astype(float).rolling(lb+1, min_periods=1).max().fillna(0).astype(bool)
def _cooldown(sig, bars=5):
    v=sig.astype(bool).values.copy(); last=-bars-1
    for i in range(len(v)):
        if v[i]:
            if (i-last)<=bars: v[i]=False
            else: last=i
    return pd.Series(v, index=sig.index)
def _volf(vol, ratio=0.5, period=20): return vol >= (vol.rolling(period, min_periods=5).mean() * ratio)
def _valid_fmt(t): return bool(re.match(r'^[A-Za-z]{1,5}([.\-][A-Za-z]{1,2})?$', t))
def _cls(val, lo, hi): return 'ind-bullish' if val<lo else ('ind-bearish' if val>hi else 'ind-neutral')

# ── 캐싱 ──
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_fundamentals(ticker):
    try:
        info=yf.Ticker(ticker).info
        def _get(key,fmt=None):
            val=info.get(key)
            if val is None: return "N/A"
            if fmt=='currency': return f"${val:,.2f}"
            if fmt=='large': return f"{val:,.0f}"
            if fmt=='percent': return f"{val*100:.2f}%"
            if fmt=='float': return f"{val:.2f}"
            return str(val)
        return "\n".join([f"Market Cap: {_get('marketCap','large')}",f"Shares Outstanding: {_get('sharesOutstanding','large')}",
            f"Float: {_get('floatShares','large')}",f"Short % of Float: {_get('shortPercentOfFloat','percent')}",
            f"Days to Cover: {_get('shortRatio','float')}",f"Trailing EPS: {_get('trailingEps','currency')}",
            f"P/E Ratio: {_get('trailingPE','float')}",f"P/S: {_get('priceToSalesTrailing12Months','float')}",
            f"P/B: {_get('priceToBook','float')}",f"PEG: {_get('pegRatio','float')}",
            f"52W High: {_get('fiftyTwoWeekHigh','currency')}",f"52W Low: {_get('fiftyTwoWeekLow','currency')}",
            f"Avg Volume: {_get('averageVolume','large')}"])
    except: return "펀더멘탈 데이터를 불러올 수 없습니다."

@st.cache_data(ttl=300, show_spinner=False)
def fetch_history(ticker, _ts=None): return yf.Ticker(ticker).history(period="2y")

@st.cache_data(ttl=600, show_spinner=False)
def validate_ticker(ticker):
    try:
        info=yf.Ticker(ticker).info
        return info.get('regularMarketPrice') is not None or info.get('currentPrice') is not None
    except: return False

@st.cache_data(ttl=300, show_spinner=False)
def compute_and_cache(ticker, _ts=None):
    df=fetch_history(ticker,_ts)
    if df.empty: return None
    return detect_all_signals(compute_indicators(df))

# ── 지표 계산 엔진 ──
def compute_rsi(s,p=14):
    d=s.diff(); g,l=d.clip(lower=0),-d.clip(upper=0)
    return 100-(100/(1+g.ewm(alpha=1/p,min_periods=p).mean()/(l.ewm(alpha=1/p,min_periods=p).mean()+1e-10)))
def compute_mfi(h,l,c,v,p=14):
    tp=(h+l+c)/3; raw=tp*v; d=tp.diff()
    return 100-(100/(1+raw.where(d>=0,0.0).rolling(p).sum()/(raw.where(d<0,0.0).rolling(p).sum()+1e-10)))
def compute_rsi_mfi(h,l,c,v,p=60):
    rf,mf=compute_rsi(c,20),compute_mfi(h,l,c,v,20); rs,ms=compute_rsi(c,p),compute_mfi(h,l,c,v,p)
    return (((rf-50)+(mf-50))/2)*.6+(((rs-50)+(ms-50))/2)*.4
def compute_wavetrend(h,l,c,ch=9,avg=12,ma=3):
    ap=(h+l+c)/3; esa=ap.ewm(span=ch,adjust=False).mean()
    d=abs(ap-esa).ewm(span=ch,adjust=False).mean(); ci=(ap-esa)/(0.015*d+1e-10)
    wt1=ci.ewm(span=avg,adjust=False).mean(); wt2=wt1.rolling(ma).mean()
    return wt1,wt2,(wt1>wt2)&(wt1.shift(1)<=wt2.shift(1)),(wt1<wt2)&(wt1.shift(1)>=wt2.shift(1))
def compute_stoch_rsi(c,rl=14,sl=14,ks=3,ds=3):
    rsi=compute_rsi(c,rl); mn,mx=rsi.rolling(sl).min(),rsi.rolling(sl).max()
    k=(((rsi-mn)/(mx-mn+1e-10))*100).rolling(ks).mean(); return k,k.rolling(ds).mean()
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
def compute_macd(c,f=12,s=26,sig=9):
    ml=c.ewm(span=f,adjust=False).mean()-c.ewm(span=s,adjust=False).mean(); sl=ml.ewm(span=sig,adjust=False).mean()
    return ml,sl,ml-sl
def detect_pivot_div(price,osc,lb=60,pw=5,os_lim=None,ob_lim=None):
    n=len(price); pv,ov=price.values,osc.values; half=pw; p_lo,p_hi=[],[]
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
    momentum=c-((h.rolling(20).max()+l.rolling(20).min())/2+kcm)/2
    return sq,fire&(momentum>0)&(momentum>momentum.shift(1)),fire&(momentum<0)&(momentum<momentum.shift(1))
def detect_volume_climax(c,o,v,wt1,atr,z_thresh=2.5):
    vm=v.rolling(20).mean(); vz=(v-vm)/(v.rolling(20).std()+1e-10)
    big=(c-o).abs()>atr*0.5; ps=(vz.shift(1)>z_thresh)&big.shift(1)
    return ps&(c.shift(1)<o.shift(1))&(wt1.shift(1)<-40)&(c>o),ps&(c.shift(1)>o.shift(1))&(wt1.shift(1)>40)&(c<o)
def _detect_engulfing_pair(c,o,wt1,wt_t=20):
    body=(c-o).abs(); big=body>body.rolling(20).mean()*0.8
    pb=c.shift(1)<o.shift(1); pp=c.shift(1)>o.shift(1)
    return pb&(c>o)&(o<=c.shift(1))&(c>=o.shift(1))&big&(wt1<-wt_t),pp&(c<o)&(o>=c.shift(1))&(c<=o.shift(1))&big&(wt1>wt_t)
def compute_supertrend(h,l,c,period=10,mult=3.0):
    atr=compute_tr(h,l,c).rolling(period).mean(); hl2=(h+l)/2
    up=(hl2+mult*atr).values.copy(); dn=(hl2-mult*atr).values.copy(); cl=c.values; n=len(c)
    sv=np.full(n,np.nan); dv=np.zeros(n,dtype=int); fv=period
    if fv>=n: return pd.Series(np.nan,index=c.index),pd.Series(0,index=c.index,dtype=int)
    dv[fv]=1; sv[fv]=dn[fv]
    for i in range(fv+1,n):
        if dv[i-1]==1: dn[i]=max(dn[i],dn[i-1]) if not np.isnan(dn[i-1]) else dn[i]
        else: up[i]=min(up[i],up[i-1]) if not np.isnan(up[i-1]) else up[i]
        if dv[i-1]==1: dv[i],sv[i]=(-1,up[i]) if cl[i]<dn[i] else (1,dn[i])
        else: dv[i],sv[i]=(1,dn[i]) if cl[i]>up[i] else (-1,up[i])
    return pd.Series(sv,index=c.index),pd.Series(dv,index=c.index)
def _detect_ema_pullback_pair(c,h,l,v,e8,e21,atr,wt1,wt2):
    vok=_volf(v,0.5); ar=atr/c; results={}
    for d in ['buy','sell']:
        slope=e21>e21.shift(5) if d=='buy' else e21<e21.shift(5)
        trend=((e8>e21) if d=='buy' else (e8<e21))&slope; side=(c>e8) if d=='buy' else (c<e8)
        if d=='buy':
            t=(l<=e8*(1+ar*0.15))&(l>=e21*(1-ar*0.25)); tr=_recent(t,2); b=(c>=e8)&(c>h.shift(1)); wok=(wt1>wt1.shift(1))&(wt1>wt2)&(wt1<60)
        else:
            t=(h>=e8*(1-ar*0.15))&(h<=e21*(1+ar*0.25)); tr=_recent(t,2); b=(c<=e8)&(c<l.shift(1)); wok=(wt1<wt1.shift(1))&(wt1<wt2)&(wt1>-60)
        results[d]=trend&side&tr&b&wok&vok
    return results['buy'],results['sell']
def _detect_mom_ignition_pair(c,o,v,bbu,bbl,atr,e8,e21,wt1,bb_w):
    body=(c-o).abs(); bb=body>atr*1.5; hv=v>v.rolling(20).mean()*2.0
    compressed=bb_w.shift(1)<bb_w.rolling(20).mean().shift(1)
    return (c>o)&bb&hv&(c>bbu)&(e8>e21)&(wt1<50)&compressed,(c<o)&bb&hv&(c<bbl)&(e8<e21)&(wt1>-50)&compressed
def _detect_vwap_pair(c,vosc,wt1,wt2,v,atr):
    vok=_volf(v,0.7); ap=(atr/c*100).clip(0.3,3.0); dt=(ap*0.3).clip(0.3,1.5)
    return (vosc>0)&(vosc.shift(1)<-dt)&(wt1>wt2)&(wt1<30)&vok,(vosc<0)&(vosc.shift(1)>dt)&(wt1<wt2)&(wt1>-30)&vok
def _detect_parabolic_pair(c,o,wt1,bbu,bbl,atr):
    return ((wt1<-85)&(wt1>wt1.shift(1))&(c>o)&(c>c.shift(1)))|((c<bbl-atr*1.5)&(c>o)),((wt1>85)&(wt1<wt1.shift(1))&(c<o)&(c<c.shift(1)))|((c>bbu+atr*1.5)&(c<o))

# ── 신규 탐지 함수들 ──
def detect_candlestick_patterns(c,o,h,l,wt1,atr):
    body=(c-o).abs(); us=h-pd.concat([c,o],axis=1).max(axis=1); ls=pd.concat([c,o],axis=1).min(axis=1)-l
    fr=h-l+1e-10; ab=body.rolling(20).mean(); sm=body<ab*0.8
    hammer=(ls>=body*2)&(us<=body*0.5)&sm&(wt1<-20)&(c>=o)
    shooting=(us>=body*2)&(ls<=body*0.5)&sm&(wt1>20)&(c<=o)
    d1b=(c.shift(2)<o.shift(2))&(body.shift(2)>ab.shift(2)); d2s=body.shift(1)<ab.shift(1)*0.5
    d3b=(c>o)&(c>(o.shift(2)+c.shift(2))/2); morning=d1b&d2s&d3b&(wt1<-15)
    d1u=(c.shift(2)>o.shift(2))&(body.shift(2)>ab.shift(2)); d3s=(c<o)&(c<(o.shift(2)+c.shift(2))/2)
    evening=d1u&d2s&d3s&(wt1>15)
    return hammer,shooting,morning,evening

def detect_inside_outside_day(h,l,c,o,wt1):
    inside=(h<h.shift(1))&(l>l.shift(1)); outside=(h>h.shift(1))&(l<l.shift(1))
    return inside,outside&(c>o)&(c>h.shift(1))&(wt1<30),outside&(c<o)&(c<l.shift(1))&(wt1>-30)

def detect_ma_crossovers(c,ma200):
    return (c>ma200)&(c.shift(1)<=ma200.shift(1)),(c<ma200)&(c.shift(1)>=ma200.shift(1))

def detect_bb_extra(c,bb_up,bb_low,bb_w,wt1):
    bwm=bb_w.rolling(20).mean(); widening=(bb_w>bb_w.shift(1))&(bb_w.shift(1)<bwm.shift(1))
    return widening&(c>c.shift(1))&(wt1>wt1.shift(1)),widening&(c<c.shift(1))&(wt1<wt1.shift(1))

def detect_52w(c,h,l):
    h252=h.rolling(252,min_periods=200).max(); l252=l.rolling(252,min_periods=200).min()
    return h>=h252,l<=l252

def detect_123_pullback(h,l,c,adx,pdi,mdi):
    sb=(adx>30)&(pdi>mdi); ss=(adx>30)&(mdi>pdi); inside=(h<h.shift(1))&(l>l.shift(1))
    ll1=l<l.shift(1); ll2=l.shift(1)<l.shift(2); ll3=l.shift(2)<l.shift(3)
    pb=ll1&ll2&ll3|(ll1&ll2&inside.shift(2))|(ll1&inside.shift(1)&ll3)|(inside&ll2&ll3)
    hh1=h>h.shift(1); hh2=h.shift(1)>h.shift(2); hh3=h.shift(2)>h.shift(3)
    ps=hh1&hh2&hh3|(hh1&hh2&inside.shift(2))|(hh1&inside.shift(1)&hh3)|(inside&hh2&hh3)
    return sb&pb,ss&ps

def detect_180_setup(c,o,h,l,ma10,ma50):
    dr=h-l+1e-10; cp=(c-l)/dr; pp=(c.shift(1)-l.shift(1))/(h.shift(1)-l.shift(1)+1e-10)
    return (pp<=0.25)&(cp>=0.75)&(c>ma10)&(c>ma50),(pp>=0.75)&(cp<=0.25)&(c<ma10)&(c<ma50)

def detect_boomer(h,l,adx,pdi,mdi):
    inside=(h<h.shift(1))&(l>l.shift(1)); in2=inside&inside.shift(1)
    return in2.shift(1).fillna(False)&(adx>30)&(pdi>mdi),in2.shift(1).fillna(False)&(adx>30)&(mdi>pdi)

def detect_expansion(h,l,c):
    dr=h-l; mr9=dr.rolling(9).max()
    h60=h.shift(1).rolling(60,min_periods=40).max(); l60=l.shift(1).rolling(60,min_periods=40).min()
    return (h>h60)&(dr>=mr9),(l<l60)&(dr>=mr9)

def detect_gilligans(o,c,h,l):
    dr=h-l+1e-10; cp=(c-l)/dr
    l60=l.shift(1).rolling(60,min_periods=40).min(); h60=h.shift(1).rolling(60,min_periods=40).max()
    return (o<=l60)&(o<l.shift(1))&(cp>=0.5)&(c>=o),(o>=h60)&(o>h.shift(1))&(cp<=0.5)&(c<=o)

def detect_lizard(o,c,h,l):
    dr=h-l+1e-10; cp=(c-l)/dr; op=(o-l)/dr
    return (cp>=0.75)&(op>=0.75)&(l<=l.rolling(10).min()),(cp<=0.25)&(op<=0.25)&(h>=h.rolling(10).max())

def detect_non_adx_123(h,l,c,ma50):
    inside=(h<h.shift(1))&(l>l.shift(1))
    ll1=l<l.shift(1); ll2=l.shift(1)<l.shift(2); ll3=l.shift(2)<l.shift(3)
    pb=ll1&ll2&ll3|(ll1&ll2&inside.shift(2))|(ll1&inside.shift(1)&ll3)|(inside&ll2&ll3)
    hh1=h>h.shift(1); hh2=h.shift(1)>h.shift(2); hh3=h.shift(2)>h.shift(3)
    ps=hh1&hh2&hh3|(hh1&hh2&inside.shift(2))|(hh1&inside.shift(1)&hh3)|(inside&hh2&hh3)
    return (c>ma50)&pb,(c<ma50)&ps

def detect_pocket_pivot(c,o,v,ma50,ma200):
    dv=v.where(c<c.shift(1),0); mdv10=dv.rolling(10,min_periods=5).max()
    has_down=(dv>0).rolling(10,min_periods=1).sum()>=2
    return (c>o)&(v>mdv10)&(c>ma50)&(c>c.shift(1))&has_down

# ── 추세 필터 ──
def _apply_trend_filter(df):
    C=df['Close']; tc=pd.Series(0.0,index=df.index)
    m50v=df['MA50'].notna(); m200v=df['MA200'].notna()
    tc+=np.where(m50v,np.where(C>df['MA50'],1.0,-1.0),0.0)
    tc+=np.where(m200v,np.where(C>df['MA200'],1.0,-1.0),0.0)
    tc+=np.where(df['EMA8']>df['EMA21'],0.5,-0.5)
    tc+=np.where(df['ST_Direction']==1,0.5,-0.5)
    df['_Trend_Context']=tc
    bull=tc>=1.5; bear=tc<=-1.5
    buy_sigs={k for k,v in SIGNAL_REGISTRY.items() if v['dir']=='buy'}
    sell_sigs={k for k,v in SIGNAL_REGISTRY.items() if v['dir']=='sell'}
    for s in sell_sigs:
        if s not in df.columns: continue
        if SIGNAL_REGISTRY[s]['w']<TREND_IMMUNE_W: df[s]=df[s]&~bull
    for s in buy_sigs:
        if s not in df.columns: continue
        if SIGNAL_REGISTRY[s]['w']<TREND_IMMUNE_W: df[s]=df[s]&~bear
    dbw=pd.Series(0.0,index=df.index); dsw=pd.Series(0.0,index=df.index)
    for s in buy_sigs:
        if s in df.columns: dbw+=df[s].fillna(False).astype(float)*SIGNAL_REGISTRY[s]['w']
    for s in sell_sigs:
        if s in df.columns: dsw+=df[s].fillna(False).astype(float)*SIGNAL_REGISTRY[s]['w']
    conflict=(dbw>0)&(dsw>0); net=dbw-dsw
    bl=conflict&(net<0); sl=conflict&(net>0); tie=conflict&(net==0)
    for s in buy_sigs:
        if s not in df.columns: continue
        if SIGNAL_REGISTRY[s]['w']<TREND_IMMUNE_W: df[s]=df[s]&~bl&~tie
    for s in sell_sigs:
        if s not in df.columns: continue
        if SIGNAL_REGISTRY[s]['w']<TREND_IMMUNE_W: df[s]=df[s]&~sl&~tie
    return df

# ── 지표 통합 계산 ──
def compute_indicators(df):
    c,h,l,v=df['Close'],df['High'],df['Low'],df['Volume']
    for ma in [5,10,20,50,100,125,200]: df[f'MA{ma}']=c.rolling(ma).mean()
    df['EMA8']=c.ewm(span=8,adjust=False).mean(); df['EMA21']=c.ewm(span=21,adjust=False).mean()
    df['BB_Mid']=df['MA20']; s20=c.rolling(20).std()
    df['BB_Up'],df['BB_Low']=df['BB_Mid']+s20*2,df['BB_Mid']-s20*2
    df['BB_Width']=(df['BB_Up']-df['BB_Low'])/df['BB_Mid']
    df['Percent_B']=(c-df['BB_Low'])/(df['BB_Up']-df['BB_Low']+1e-10)
    df['ATR']=compute_tr(h,l,c).rolling(14).mean()
    atr22=compute_tr(h,l,c).rolling(22).mean()
    df['Chandelier_Long']=h.rolling(22).max()-atr22*3.0; df['Chandelier_Short']=l.rolling(22).min()+atr22*3.0
    df['SuperTrend'],df['ST_Direction']=compute_supertrend(h,l,c)
    wt1,wt2,wu,wd=compute_wavetrend(h,l,c); df['WT1'],df['WT2'],df['WT_Up'],df['WT_Down']=wt1,wt2,wu,wd
    df['RSI']=compute_rsi(c,14); df['StochK'],df['StochD']=compute_stoch_rsi(c)
    df['MFI']=compute_mfi(h,l,c,v,14); df['RSI_MFI']=compute_rsi_mfi(h,l,c,v,60)
    vwap=(c*v).rolling(20).sum()/(v.rolling(20).sum()+1e-10); df['VWAP_Osc']=((c-vwap)/(vwap+1e-10))*100
    df['ADX'],df['Plus_DI'],df['Minus_DI']=compute_adx(h,l,c); df['OBV']=compute_obv(c,v)
    df['KC_Upper'],df['KC_Mid'],df['KC_Lower']=compute_keltner(h,l,c)
    df['MACD_Line'],df['MACD_Signal'],df['MACD_Hist']=compute_macd(c)
    return df

def _deduplicate(df):
    for _cat,sigs in SIGNAL_HIERARCHY.items():
        for i,s in enumerate(sigs):
            if s not in df.columns: continue
            for higher in sigs[:i]:
                if higher in df.columns: df[s]=df[s]&~df[higher]
    return df

# ── 통합 시그널 탐지 엔진 ──
def detect_all_signals(df):
    H,L,C,O,V=df['High'],df['Low'],df['Close'],df['Open'],df['Volume']
    e8,e21,m10,m50,m200=df['EMA8'],df['EMA21'],df['MA10'],df['MA50'],df['MA200']
    wt1,wt2,atr=df['WT1'],df['WT2'],df['ATR']
    htf1=(e8>e21)&(e21>e21.shift(5)); htf2=(C>m50)&(m50>m50.shift(10))
    wun=_recent(df['WT_Up'],2); wdn=_recent(df['WT_Down'],2)
    wur=_recent(df['WT_Up'],3); wdr=_recent(df['WT_Down'],3); vok=_volf(V,0.5)
    sb=(df['ADX']>25)&(df['Plus_DI']>df['Minus_DI'])&(C>m50)
    sbe=(df['ADX']>25)&(df['Minus_DI']>df['Plus_DI'])&(C<m50)
    xb=sb&(C>m200)&(m50>m50.shift(5)); xbe=sbe&(C<m200)&(m50<m50.shift(5))
    mfb=df['RSI_MFI']>-10; mfs=df['RSI_MFI']<10
    para_bot,para_top=_detect_parabolic_pair(C,O,wt1,df['BB_Up'],df['BB_Low'],atr)
    st_fb=(df['ST_Direction']==-1)&(df['ST_Direction'].shift(1)==1); st_fb.iloc[:ST_MIN_BAR]=False; st_bo=_recent(st_fb,3)
    st_fb2=(df['ST_Direction']==1)&(df['ST_Direction'].shift(1)==-1); st_fb2.iloc[:ST_MIN_BAR]=False; st_bu=_recent(st_fb2,3)
    ssb=sb&(~para_top)&(~st_bo); ssx=xb&(~para_top)&(~st_bo)
    bsb=sbe&(~para_bot)&(~st_bu); bsx=xbe&(~para_bot)&(~st_bu)

    # MCB+ core
    df['Green_Dot_T1']=wun&(wt1<=OS1)&(df['RSI']<30)&(df['MFI']<30)&(df['RSI_MFI']<0)&(~bsx)&vok
    df['Green_Dot_T2']=wun&(wt1<=OS1)&((df['RSI']<32)|(df['MFI']<32))&~df['Green_Dot_T1']&(~bsb)&vok
    _gd=df['Green_Dot_T1']|df['Green_Dot_T2']
    df['Red_Dot_T1']=wdn&(wt1>=OB1)&(df['RSI']>70)&(df['MFI']>70)&(df['RSI_MFI']>0)&(~ssx)&vok
    df['Red_Dot_T2']=wdn&(wt1>=OB1)&((df['RSI']>68)|(df['MFI']>68))&~df['Red_Dot_T1']&(~ssb)&vok
    _rd=df['Red_Dot_T1']|df['Red_Dot_T2']
    df['Blue_Diamond']=(wt2<=0)&wun&htf1&htf2&(~bsb)&mfb&vok
    df['Red_Diamond']=(wt2>=0)&wdn&~htf1&~htf2&(~ssb)&mfs&vok
    bd,brd,hb,hbr=detect_pivot_div(C,wt1,60,5,OS1,OB1); bdr=_recent(bd,3); brdr=_recent(brd,3)
    rbd,rbrd,_,_=detect_pivot_div(C,df['RSI'],60,5,35,65)
    obd,obrd,_,_=detect_pivot_div(C,df['OBV'],60,5)
    df['Gold_Dot']=df['Green_Dot_T1']&(wt1<=OS2)&bdr
    df['Blood_Diamond']=df['Red_Dot_T1']&(wt1>=OB2)&brdr
    df['Bull_Divergence']=bd&wur&~_gd&~df['Gold_Dot']&(~bsb)&vok
    df['Bear_Divergence']=brd&wdr&~_rd&(~ssb)&vok
    df['RSI_Bull_Divergence']=rbd&(wt1<-20)&(~bsb)&vok&~bd
    df['RSI_Bear_Divergence']=rbrd&(wt1>20)&(~ssb)&vok&~brd
    voh=_volf(V,0.7)
    df['Hidden_Bull_Div']=hb&(wt1<-25)&htf2&(~bsx)&voh
    df['Hidden_Bear_Div']=hbr&(wt1>25)&~htf2&(~ssx)&voh
    sqo,sqb,sqs=detect_ttm_squeeze(df['BB_Up'],df['BB_Low'],df['KC_Upper'],df['KC_Lower'],C,H,L,df['KC_Mid'])
    df['Squeeze_On']=sqo; df['Squeeze_Fire_Buy']=sqb&(~bsb)&vok; df['Squeeze_Fire_Sell']=sqs&(~ssb)&vok
    df['Volume_Climax_Buy'],df['Volume_Climax_Sell']=detect_volume_climax(C,O,V,wt1,atr)
    ax=(df['ADX']>20)&(df['ADX'].shift(1)<=20)
    df['ADX_Momentum_Buy']=ax&(df['Plus_DI']>df['Minus_DI'])&(wt1>wt2)&vok
    df['ADX_Momentum_Sell']=ax&(df['Minus_DI']>df['Plus_DI'])&(wt1<wt2)&vok
    df['Bullish_Engulfing'],df['Bearish_Engulfing']=_detect_engulfing_pair(C,O,wt1)
    df['Bullish_Engulfing']&=(~bsb)&vok; df['Bearish_Engulfing']&=(~ssb)&vok
    gc=(m50>m200)&(m50.shift(1)<=m200.shift(1)); dc=(m50<m200)&(m50.shift(1)>=m200.shift(1))
    af=df['ADX']>15; vc=_volf(V,0.7); df['Golden_Cross']=gc&af&vc; df['Death_Cross']=dc&af&vc
    df['EMA_Pullback_Buy'],df['EMA_Pullback_Sell']=_detect_ema_pullback_pair(C,H,L,V,e8,e21,atr,wt1,wt2)
    df['Momentum_Ignition_Buy'],df['Momentum_Ignition_Sell']=_detect_mom_ignition_pair(C,O,V,df['BB_Up'],df['BB_Low'],atr,e8,e21,wt1,df['BB_Width'])
    df['SuperTrend_Buy']=st_fb2; df['SuperTrend_Sell']=st_fb
    vp=_volf(V,1.0)
    df['Parabolic_Top_Sell']=para_top&((df['WT_Down']|wdr)|((C<O)&(C<C.shift(1))))&vp
    df['Parabolic_Bottom_Buy']=para_bot&((df['WT_Up']|wur)|((C>O)&(C>C.shift(1))))&vp
    df['VWAP_Bounce_Buy'],df['VWAP_Reject_Sell']=_detect_vwap_pair(C,df['VWAP_Osc'],wt1,wt2,V,atr)

    # 캔들스틱
    df['Hammer'],df['Shooting_Star'],df['Morning_Star'],df['Evening_Star']=detect_candlestick_patterns(C,O,H,L,wt1,atr)
    df['Hammer']&=(~bsb)&vok; df['Shooting_Star']&=(~ssb)&vok; df['Morning_Star']&=(~bsb)&vok; df['Evening_Star']&=(~ssb)&vok
    # Outside Day
    _,df['Outside_Bullish'],df['Outside_Bearish']=detect_inside_outside_day(H,L,C,O,wt1)
    df['Outside_Bullish']&=(~bsb)&vok; df['Outside_Bearish']&=(~ssb)&vok
    # 200MA
    df['Cross_Above_200MA'],df['Fell_Below_200MA']=detect_ma_crossovers(C,m200)
    # BB Squeeze End
    df['BB_Squeeze_End_Bull'],df['BB_Squeeze_End_Bear']=detect_bb_extra(C,df['BB_Up'],df['BB_Low'],df['BB_Width'],wt1)
    # 52W
    df['New_52W_High'],df['New_52W_Low']=detect_52w(C,H,L)
    # Cooper
    df['Pullback_123_Bull'],df['Pullback_123_Bear']=detect_123_pullback(H,L,C,df['ADX'],df['Plus_DI'],df['Minus_DI'])
    df['Setup_180_Bull'],df['Setup_180_Bear']=detect_180_setup(C,O,H,L,m10,m50)
    df['Boomer_Buy'],df['Boomer_Sell']=detect_boomer(H,L,df['ADX'],df['Plus_DI'],df['Minus_DI'])
    df['Expansion_BO'],df['Expansion_BD']=detect_expansion(H,L,C)
    df['Gilligans_Buy'],df['Gilligans_Sell']=detect_gilligans(O,C,H,L)
    df['Lizard_Bull'],df['Lizard_Bear']=detect_lizard(O,C,H,L)
    df['NonADX_123_Bull'],df['NonADX_123_Bear']=detect_non_adx_123(H,L,C,m50)
    df['Pocket_Pivot']=detect_pocket_pivot(C,O,V,m50,m200)

    _deduplicate(df)
    _apply_trend_filter(df)
    for s,cd in COOLDOWN_MAP.items():
        if s in df.columns: df[s]=_cooldown(df[s],cd)
    compute_confluence(df)
    df['Buy_Proximity'],df['Sell_Proximity']=compute_proximity(wt1,wt2,df['RSI'],df['MFI'],df['RSI_MFI'],df['StochK'],df['MACD_Hist'],df['BB_Width'],sb,sbe)
    df['Strong_Bull'],df['Strong_Bear']=sb,sbe
    df['Parabolic_Blowoff']=para_top; df['Parabolic_Bottom_Raw']=para_bot; df['ST_Bear_Override']=st_bo
    df['Sell_Shield_Overridden']=para_top|st_bo; df['Buy_Shield_Overridden']=para_bot|st_bu
    df['_HTF1_Bull'],df['_HTF2_Bull']=htf1,htf2
    return df

# ──────────────────────────────────────────
# Confluence / Proximity / Bias
# ──────────────────────────────────────────
def compute_confluence(df, dw=5, df_=0.75):
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
    s+=np.where(wt1<OS1,1.0,0)+np.where(wt1<OS2,0.5,0)-np.where(wt1>OB1,1.0,0)-np.where(wt1>OB2,0.5,0)
    adx=df['ADX'].values; pdi=df['Plus_DI'].values; mdi=df['Minus_DI'].values
    bull_trend=pdi>mdi; bear_trend=mdi>pdi; adx_factor=np.clip((adx-20)/100,0.0,0.3)
    s+=np.where(bull_trend&(s>0),s*adx_factor,0); s-=np.where(bear_trend&(s<0),abs(s)*adx_factor,0)
    df['Confluence_Score']=s
    df['Ultra_Buy']=(s>=6.5)|((s>=5)&(bc>=3)); df['Ultra_Sell']=(s<=-6.5)|((s<=-5)&(sc>=3))
    df['Strong_Buy']=(s>=3.5)&(~df['Ultra_Buy']); df['Strong_Sell']=(s<=-3.5)&(~df['Ultra_Sell'])
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
    bp,sp=bp.clip(upper=100),sp.clip(upper=100); net=bp-sp
    return (pd.Series(np.where(net>=0,bp,bp*np.where(sbe,.4,.55)),index=wt1.index),
            pd.Series(np.where(net<=0,sp,sp*np.where(sb,.4,.55)),index=wt1.index))

def compute_bias(meta, htf1, htf2):
    sc=0.0; wt1=meta.get('wt1',0)
    if wt1<=-60: sc+=3.0
    elif wt1<=-53: sc+=2.0
    elif wt1<=-20: sc+=1.0
    elif wt1>=60: sc-=3.0
    elif wt1>=53: sc-=2.0
    elif wt1>=20: sc-=1.0
    rsi=meta.get('rsi',50)
    if rsi<=30: sc+=1.5
    elif rsi<=45: sc+=0.5
    elif rsi>=70: sc-=1.5
    elif rsi>=55: sc-=0.5
    mfi=meta.get('mfi',50)
    if mfi<=30: sc+=1.5
    elif mfi<=45: sc+=0.5
    elif mfi>=70: sc-=1.5
    elif mfi>=55: sc-=0.5
    mf=meta.get('mf_area',0)
    if mf<-5: sc+=2.0
    elif mf<0: sc+=1.0
    elif mf>5: sc-=2.0
    elif mf>0: sc-=1.0
    stk=meta.get('stochk',50)
    if stk<20: sc+=1.5
    elif stk<35: sc+=0.5
    elif stk>80: sc-=1.5
    elif stk>65: sc-=0.5
    mh=meta.get('macd_hist',0)
    if mh>0.1: sc+=1.0
    elif mh>0: sc+=0.5
    elif mh<-0.1: sc-=1.0
    elif mh<0: sc-=0.5
    sc+=1.5 if htf1 else -1.5; sc+=2.0 if htf2 else -2.0
    if sc>=9.0: return 'STRONG BUY',sc
    elif sc>=3.5: return 'BUY',sc
    elif sc>-3.5: return 'NEUTRAL',sc
    elif sc>-9.0: return 'SELL',sc
    else: return 'STRONG SELL',sc

def compute_signal_stats(df,col,direction,fwd=(2,3,5),mn=5):
    if col not in df.columns: return None
    mask=df[col].fillna(False).values.astype(bool)
    if mask.sum()<mn: return None
    st_res={'count':int(mask.sum())}; entry_price=df['Open'].shift(-1)
    for n in fwd:
        exit_price=df['Close'].shift(-(n+1)); pct=(exit_price-entry_price)/entry_price*100
        vr=pct[mask].dropna()
        if len(vr)>=mn:
            st_res[f'{n}d_avg']=float(vr.mean())
            st_res[f'{n}d_winrate']=float((vr<0).sum()/len(vr)*100) if direction=='sell' else float((vr>0).sum()/len(vr)*100)
            st_res[f'{n}d_median']=float(vr.median())
        else: st_res[f'{n}d_avg']=st_res[f'{n}d_winrate']=st_res[f'{n}d_median']=None
    return st_res

def compute_all_stats(dv):
    tgt={k:v['dir'] for k,v in SIGNAL_REGISTRY.items()}
    tgt.update({'Ultra_Buy':'buy','Strong_Buy':'buy','Ultra_Sell':'sell','Strong_Sell':'sell'})
    return {s:{**r,'direction':d} for s,d in tgt.items() if (r:=compute_signal_stats(dv,s,d)) and r['count']>0}

# ──────────────────────────────────────────
# 분석 파이프라인
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
    except Exception as e: return None,f"로딩 실패:{e}",None

def build_speedometer_gauges(meta):
    cs=meta.get('confluence_score',0); bs=meta.get('bias_score',0); bl=meta.get('overall_bias','NEUTRAL')
    cc='#00E676' if cs>=6.5 else ('#69F0AE' if cs>=3.5 else ('#FF1744' if cs<=-6.5 else ('#FF5252' if cs<=-3.5 else '#FFC107')))
    bcm={'STRONG BUY':'#00E676','BUY':'#69F0AE','STRONG SELL':'#FF1744','SELL':'#FF5252','NEUTRAL':'#FFC107'}; bc=bcm.get(bl,'#FFC107')
    fig=make_subplots(rows=1,cols=2,specs=[[{"type":"indicator"},{"type":"indicator"}]],horizontal_spacing=0.08)
    fig.add_trace(go.Indicator(mode="gauge+number+delta",value=cs,
        number=dict(font=dict(size=28,color="#FAFAFA")),title=dict(text="<b>🔥 Confluence Score</b>",font=dict(size=13,color="#AAA")),
        gauge=dict(axis=dict(range=[-10,10],tickwidth=2,tickcolor="#555",dtick=2.5,tickfont=dict(size=10,color="#888")),
            bar=dict(color=cc,thickness=0.3),bgcolor="rgba(30,33,39,0.8)",borderwidth=2,bordercolor="#2D333B",
            steps=[dict(range=[-10,-6.5],color="rgba(255,23,68,0.25)"),dict(range=[-6.5,-3.5],color="rgba(255,82,82,0.15)"),
                dict(range=[-3.5,3.5],color="rgba(255,193,7,0.10)"),dict(range=[3.5,6.5],color="rgba(105,240,174,0.15)"),
                dict(range=[6.5,10],color="rgba(0,230,118,0.25)")],
            threshold=dict(line=dict(color="white",width=3),thickness=0.8,value=cs))),row=1,col=1)
    fig.add_trace(go.Indicator(mode="gauge+number",value=bs,
        number=dict(font=dict(size=28,color="#FAFAFA"),suffix=f"  {bl}",valueformat=".1f"),
        title=dict(text="<b>🧭 Overall Bias</b>",font=dict(size=13,color="#AAA")),
        gauge=dict(axis=dict(range=[-13,13],tickwidth=2,tickcolor="#555",dtick=3.25,tickfont=dict(size=10,color="#888")),
            bar=dict(color=bc,thickness=0.3),bgcolor="rgba(30,33,39,0.8)",borderwidth=2,bordercolor="#2D333B",
            steps=[dict(range=[-13,-9],color="rgba(255,23,68,0.30)"),dict(range=[-9,-3.5],color="rgba(255,82,82,0.15)"),
                dict(range=[-3.5,3.5],color="rgba(255,193,7,0.10)"),dict(range=[3.5,9],color="rgba(105,240,174,0.15)"),
                dict(range=[9,13],color="rgba(0,230,118,0.30)")],
            threshold=dict(line=dict(color="white",width=3),thickness=0.8,value=bs))),row=1,col=2)
    fig.update_layout(template="plotly_dark",paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
        height=230,margin=dict(l=20,r=20,t=50,b=10),font=dict(family="Pretendard"))
    return fig

def _hl(fig,mask,idx,fill,txt=None,row=1):
    d=mask.astype(int).diff().fillna(0); starts=idx[d==1].tolist(); ends=idx[d==-1].tolist()
    if len(mask)>0 and mask.iloc[0]: starts.insert(0,idx[0])
    if len(mask)>0 and mask.iloc[-1]: ends.append(idx[-1])
    for s,e in zip(starts,ends):
        kw=dict(x0=s,x1=e,fillcolor=fill,line_width=0,row=row,col=1)
        if txt: kw.update(annotation_text=txt,annotation_position="top left",annotation_font_size=10,annotation_font_color="#FF5252")
        fig.add_vrect(**kw)

# ──────────────────────────────────────────
# 차트 빌더
# ──────────────────────────────────────────
def build_chart(dc,ticker,regime,shield):
    mac={5:"#ff9900",10:"#ffb74d",20:'#f1c40f',50:'#e74c3c',100:'#9b59b6',125:'#3498db',200:'#2ecc71'}
    fig=make_subplots(rows=6,cols=1,shared_xaxes=True,vertical_spacing=0.035,
        row_heights=[.36,.07,.15,.12,.15,.15],
        subplot_titles=("","Volume","WaveTrend Oscillator","Money Flow","MACD (12,26,9)","Confluence Score"))
    enabled=st.session_state.get('enabled_signals',set(ALL_CHART_SIGNALS.keys()))
    active_masks={}
    for cn,cfg in ALL_CHART_SIGNALS.items():
        if cn not in dc.columns or cn not in enabled: continue
        mask=dc[cn].copy()
        if cn=='Green_Dot_T1': mask&=~dc.get('Gold_Dot',pd.Series(False,index=dc.index))
        elif cn=='Ultra_Buy': mask&=~dc.get('Gold_Dot',pd.Series(False,index=dc.index))
        elif cn=='Ultra_Sell': mask&=~dc.get('Blood_Diamond',pd.Series(False,index=dc.index))
        active_masks[cn]=mask
    daily_sig_texts=[]
    for i in range(len(dc)):
        day_sigs=[]
        for cn,mask in active_masks.items():
            if mask.iloc[i]:
                cfg=ALL_CHART_SIGNALS[cn]
                day_sigs.append(f"<span style='color:{cfg['clr']}'><b>{cfg['icon']} {cfg['label']}</b></span> <span style='font-size:11px;color:#AAA'>({cfg.get('kor','')})</span>")
        daily_sig_texts.append("<br><br><b>🎯 시그널:</b><br>"+"<br>".join(day_sigs) if day_sigs else "")
    fig.add_trace(go.Candlestick(x=dc.index,open=dc['Open'],high=dc['High'],low=dc['Low'],close=dc['Close'],name="Price",
        increasing_line_color='#00E676',decreasing_line_color='#FF1744',
        increasing_fillcolor='rgba(0,230,118,0.8)',decreasing_fillcolor='rgba(255,23,68,0.8)',
        customdata=daily_sig_texts,hovertemplate="O:%{open:.2f}<br>H:%{high:.2f}<br>L:%{low:.2f}<br>C:%{close:.2f}%{customdata}<extra></extra>"),row=1,col=1)
    for ma in [5,10,20,50,100,125,200]:
        fig.add_trace(go.Scatter(x=dc.index,y=dc[f'MA{ma}'],line=dict(color=mac[ma],width=1.2),name=f'{ma}MA',hovertemplate="%{y:.2f}"),row=1,col=1)
    for nm,col,clr,dash in [('EMA8','EMA8','#00FFFF','dot'),('EMA21','EMA21','#FF69B4','dot')]:
        fig.add_trace(go.Scatter(x=dc.index,y=dc[col],line=dict(color=clr,width=1.5,dash=dash),name=nm,hovertemplate="%{y:.2f}"),row=1,col=1)
    for mc,clr,nm in [(dc['ST_Direction']==1,'#00E676','ST▲'),(dc['ST_Direction']==-1,'#FF1744','ST▼')]:
        fig.add_trace(go.Scatter(x=dc.index,y=dc['SuperTrend'].where(mc),line=dict(color=clr,width=2),name=nm,connectgaps=False,hovertemplate="%{y:.2f}"),row=1,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['BB_Up'],line=dict(color='gray',width=1,dash='dot'),name='BB↑',hovertemplate="%{y:.2f}"),row=1,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['BB_Low'],line=dict(color='gray',width=1,dash='dot'),name='BB↓',fill='tonexty',fillcolor='rgba(128,128,128,0.07)',hovertemplate="%{y:.2f}"),row=1,col=1)
    for cn2,clr2,txt2 in [('Sell_Shield_Overridden','rgba(255,0,0,0.04)','🔓Sell OFF'),('Buy_Shield_Overridden','rgba(0,255,0,0.04)','🔓Buy OFF')]:
        om=dc.get(cn2,pd.Series(False,index=dc.index))
        if om.any(): _hl(fig,om,dc.index,clr2,txt2,1)
    def _at(s): return dc.loc[s.index,'ATR'].fillna(dc['ATR'].median())
    for cn,cfg in ALL_CHART_SIGNALS.items():
        if cn not in active_masks: continue
        sig=dc[active_masks[cn]]
        if sig.empty: continue
        yv=sig[cfg['base']]+_at(sig)*cfg['atr_m']; lw=2 if cfg['sz']>=16 else (1.5 if cfg['sz']>=13 else 1)
        fig.add_trace(go.Scatter(x=sig.index,y=yv,mode='markers',
            marker=dict(symbol=cfg['sym'],size=cfg['sz'],color=cfg['clr'],line=dict(width=lw,color='white' if 'open' not in cfg['sym'] else cfg['clr'])),
            name=f"{cfg['icon']} {cfg['label']}",hoverinfo='skip'),row=1,col=1)
    br=dc['Close']<dc['Open']
    fig.add_trace(go.Bar(x=dc.index,y=dc['Volume'],marker_color=np.where(br,'rgba(255,23,68,0.6)','rgba(0,230,118,0.6)').tolist(),name="Volume",opacity=0.8,hovertemplate="%{y:,.0f}"),row=2,col=1)
    vcm=dc.get('Volume_Climax_Buy',pd.Series(False))|dc.get('Volume_Climax_Sell',pd.Series(False)); vcd=dc[vcm]
    if not vcd.empty: fig.add_trace(go.Bar(x=vcd.index,y=vcd['Volume'],marker_color='#FFD700',name="Vol Climax",opacity=0.9,hovertemplate="%{y:,.0f}"),row=2,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['WT1'],line=dict(color='#00E676',width=2),name="WT1",hovertemplate="%{y:.1f}"),row=3,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['WT2'],line=dict(color='#FF1744',width=1.5,dash='dot'),name="WT2",hovertemplate="%{y:.1f}"),row=3,col=1)
    wd=dc['WT1']-dc['WT2']
    fig.add_trace(go.Bar(x=dc.index,y=wd,marker_color=np.where(wd>=0,'#00E676','#FF1744').tolist(),name="WT Hist",opacity=0.3,hovertemplate="%{y:.1f}"),row=3,col=1)
    for ml2,clr2 in [(['Green_Dot_T1','Green_Dot_T2','Gold_Dot'],'#00E676'),(['Red_Dot_T1','Red_Dot_T2','Blood_Diamond'],'#FF1744')]:
        comb=pd.Series(False,index=dc.index)
        for mc2 in ml2: comb|=dc.get(mc2,pd.Series(False,index=dc.index))
        pts=dc[comb]
        if not pts.empty: fig.add_trace(go.Scatter(x=pts.index,y=pts['WT1'],mode='markers',marker=dict(symbol='circle',size=10,color=clr2,line=dict(width=1,color='white')),hoverinfo='skip',showlegend=False),row=3,col=1)
    for lv,cc2,d in [(OB2,'#ff3333','dash'),(OB1,'#ff3333','solid'),(0,'gray','dot'),(OS1,'#00bfff','solid'),(OS2,'#00bfff','dash')]:
        fig.add_hline(y=lv,line_dash=d,line_color=cc2,line_width=1,row=3,col=1)
    wmx=max(float(dc['WT1'].max()),100)+10; wmn=min(float(dc['WT1'].min()),-100)-10
    fig.add_hrect(y0=OB1,y1=wmx,fillcolor="rgba(255,23,68,0.08)",line_width=0,row=3,col=1)
    fig.add_hrect(y0=wmn,y1=OS1,fillcolor="rgba(0,191,255,0.08)",line_width=0,row=3,col=1)
    if 'Squeeze_On' in dc.columns: _hl(fig,dc['Squeeze_On'],dc.index,"rgba(255,255,0,0.05)",None,3)
    rmfi=dc['RSI_MFI']
    fig.add_trace(go.Bar(x=dc.index,y=rmfi,marker_color=np.where(rmfi>=0,'#3ee145','#ff3d2e').tolist(),name="Money Flow",opacity=0.7,hovertemplate="%{y:.1f}"),row=4,col=1)
    fig.add_hline(y=0,line_dash="solid",line_color="gray",line_width=1,row=4,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['MACD_Line'],line=dict(color='#29B6F6',width=1.5),name="MACD",hovertemplate="%{y:.3f}"),row=5,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['MACD_Signal'],line=dict(color='#FFA726',width=1.5),name="Signal",hovertemplate="%{y:.3f}"),row=5,col=1)
    mhist=dc['MACD_Hist']
    fig.add_trace(go.Bar(x=dc.index,y=mhist,marker_color=np.where(mhist>=0,'#26A69A','#EF5350').tolist(),name="Hist",opacity=0.7,hovertemplate="%{y:.3f}"),row=5,col=1)
    fig.add_hline(y=0,line_color="#444444",line_width=1,row=5,col=1)
    conf=dc['Confluence_Score']
    fig.add_trace(go.Bar(x=dc.index,y=conf,marker_color=np.where(conf>=3.5,'#00E676',np.where(conf<=-3.5,'#FF1744','#FFC107')).tolist(),name="Conf Score",opacity=0.8,hovertemplate="%{y:.1f}"),row=6,col=1)
    for lv,cc2,d in [(6.5,'#00E676','dash'),(-6.5,'#FF1744','dash'),(3.5,'#00E676','dot'),(-3.5,'#FF1744','dot'),(0,'gray','solid')]:
        fig.add_hline(y=lv,line_dash=d,line_color=cc2,line_width=1 if d=='solid' else .8,row=6,col=1)
    fig.update_layout(yaxis_title="Price",yaxis2_title="Vol",yaxis3_title="WT",yaxis4_title="MF",yaxis5_title="MACD",yaxis6_title="Conf",
        template="plotly_dark",paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=2,r=2,t=40,b=2),height=1200,showlegend=True,hovermode="x unified",
        hoverlabel=dict(bgcolor="rgba(14,17,23,0.95)",font_size=12,font_family="Pretendard",bordercolor="#2D333B"),
        legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="center",x=0.5,font=dict(size=9.5,color='#CCC',family='Pretendard'),bgcolor='rgba(0,0,0,0)',itemsizing='constant'))
    for i in range(1,7):
        ya=f'yaxis{i}' if i>1 else 'yaxis'
        fig.update_layout(**{ya:dict(gridcolor='rgba(45,51,59,0.5)',gridwidth=1,zerolinecolor='rgba(60,63,70,0.6)',zerolinewidth=1,title_font=dict(size=11,color='#777'),tickfont=dict(size=10,color='#888'))})
    fig.update_xaxes(rangeslider_visible=False)
    has_weekends=dc.index.dayofweek.isin([5,6]).any()
    rb=[dict(bounds=["sat","mon"])] if not has_weekends else []
    fig.update_xaxes(showspikes=True,spikecolor="#667eea",spikemode="across",spikethickness=1,spikedash="dot",rangebreaks=rb,gridcolor='rgba(45,51,59,0.5)',gridwidth=1,tickfont=dict(size=10,color='#888'))
    fig.update_yaxes(showspikes=True,spikecolor="#667eea",spikemode="across",spikethickness=1,spikedash="dot")
    for ann in fig['layout']['annotations']: ann['font']=dict(size=12,color='#AAA',family='Pretendard')
    return fig

# ──────────────────────────────────────────
# 메타데이터 + AI 프롬프트
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
    bp,sp2=meta['buy_proximity'],meta['sell_proximity']
    prox=f"BuyProx={bp:.0f}%,SellProx={sp2:.0f}%"
    if bp>=60: prox+=" ⚠️매수임박"
    if sp2>=60: prox+=" ⚠️매도임박"
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
        for sn,sv in sorted(stats.items(),key=lambda x:x[1]['count'],reverse=True)[:15]:
            wr=sv.get('2d_winrate'); avg=sv.get('2d_avg')
            if wr is not None: lines.append(f"  {sn}:{sv['count']}회,2일승률{wr:.0f}%,평균{avg:+.1f}%")
        if lines: st_txt="\n📌 [백테스트(2년,상위15)]\n"+"\n".join(lines)
    return f"{ps}\n\n📌 [지표 요약]\n{inds}\n\n📌 [최근 시그널]\n{st_text}{st_txt}"

def build_ai_prompt(ticker,phist,fundamentals):
    return f"""━━━━━━━━━━━━━
【 🎯 Role & Persona 】
━━━━━━━━━━━━━
당신은 월스트리트 20년+ 경력 베테랑 주식 애널리스트이자 펀드 매니저입니다.
기술적 분석과 시장 심리 파악에 탁월하며, Market Cipher B 지표 해석 및 ATR 변동성 기반의 철저한 리스크 관리에 정통합니다.

---
【 🛠️ Task & Rules 】
1. 🚫 환각(Hallucination) 엄금: [YFinance 펀더멘탈]에 없는 데이터는 지어내지 마세요.
2. 🧮 기계적 리스크 관리: 손절가/목표가는 ATR 기반으로 산출.
3. 🌊 추세 맞춤형 전략: STRONG BULL, STRONG BEAR, NEUTRAL 에 맞는 전략 제시.
4. 📈 백테스트 승률, VWAP_Osc, ADX, Squeeze 등을 근거로 포함.

---
【 📥 Input Data 】
[티커: {ticker}]

📌 [주가 + 기술적 지표 + 시그널 백테스트]
{phist}

📌 [YFinance 펀더멘탈 및 숏 데이터]
{fundamentals}

---
【 📄 Output Format 】
# 🚦 {ticker} 심층 퀀트 리포트
[🔵/🔴/🟠] [{ticker}] 분석: [핵심 한 줄]

---
### 내용 요약
[🔵/🔴/🟠] [3~4문장 요약]

---
### 🚦 시그널 분석
* WaveTrend / Money Flow / Confluence Score / Signal Proximity
* 최근 시그널 목록 + 신뢰도 + 백테스트 근거
> 🚦 해석: [1~2문장]

---
### 주가 및 거래량 분석
* 거래량, VWAP, ADX, 과매수/과매도 상태
> 종합 해석: [🔵/🔴/🟠]

---
### 기술적 지표 및 패턴
* ATR, ADX, TTM Squeeze, MACD 상태
* 백테스트 승률/수익률

---
### 지지선 및 저항선
* 지지선: [가격1], [가격2], [가격3]
* 저항선: [가격1], [가격2], [가격3]

---
### 공매도 현황
* Short % Float, Short Ratio 기반 분석

---
### 🔮 종합해석 및 시나리오
* 🔵 긍정적 / 🟠 베이스 / 🔴 리스크 시나리오

**실전 트레이딩 전략:**
* 리스크/리워드, 공격적/보수적 진입, 손절, 분할매도, 트레일링 스탑

---
### 결론
[🔵/🔴/🟠] [2~3문장]

### 주가 예측 (다음 거래일)
[🔵/🔴/🟠] 예상: [방향] · 근거
[GRADE/Score]: [최종 등급]
"""

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
    cc='price-change-up' if chg>=0 else 'price-change-down'; ci='▲' if chg>=0 else '▼'
    vr=m['volume']/m['avg_volume'] if m['avg_volume'] else 0
    cv=m.get('confluence_score',0); sd=m.get('supertrend_dir',0); sh=m.get('shield_status',''); mhv=m.get('macd_hist',0)
    specs=[(_cls(m['wt1'],-20,20),f"WT:{m['wt1']:.0f} {_il('wt1',m['wt1'])}"),
        (_cls(m['rsi'],40,60),f"RSI:{m['rsi']:.0f} {_il('rsi',m['rsi'])}"),
        (_cls(m['mfi'],40,60),f"MFI:{m['mfi']:.0f} {_il('mfi',m['mfi'])}"),
        ('ind-bullish' if m['mf_area']<0 else ('ind-bearish' if m['mf_area']>0 else 'ind-neutral'),f"MF:{m['mf_area']:.1f}"),
        ('ind-bullish' if vr>1.5 else 'ind-neutral',f"Vol:{vr:.1f}x"),
        ('ind-bullish' if m['adx']>25 else 'ind-neutral',f"ADX:{m['adx']:.0f}"),
        (_cls(m['stochk'],30,70),f"StK:{m['stochk']:.0f} {_il('stochk',m['stochk'])}"),
        ('ind-bullish' if cv>=3.5 else ('ind-bearish' if cv<=-3.5 else 'ind-neutral'),f"Conf:{cv:.1f}"),
        ('ind-bullish' if sd==1 else 'ind-bearish',f"ST:{'▲' if sd==1 else '▼'}"),
        ('ind-bullish' if mhv>0 else ('ind-bearish' if mhv<0 else 'ind-neutral'),f"MACD:{mhv:+.2f}")]
    ih="".join([f"<span class='indicator-mini {c}'>{l}</span>" for c,l in specs])
    if sh: ih+=f"<span class='indicator-mini ind-bearish' style='font-weight:700'>🔓 {sh}</span>"
    tr=m.get('trend_regime','NEUTRAL ⚪')
    st.markdown(f"""<div class="price-header"><div style="display:flex;justify-content:space-between;align-items:center">
        <div><p class="price-label">🚦 {m['ticker']} · {m['last_date']} · <b>{tr}</b></p>
        <p class="price-big" style="color:#FAFAFA">${m['price']:.2f}<span class="{cc}" style="font-size:1rem;margin-left:8px">{ci} {abs(chg):.2f} ({abs(cp):.2f}%)</span></p></div>
        <div style="text-align:right"><p class="price-label">ATR</p><p style="color:#FFC107;font-size:1.1rem;font-weight:600;margin:0">${m['atr']:.2f} ({m['atr_pct']:.1f}%)</p></div></div>
        <div style="margin-top:10px;display:flex;gap:6px;flex-wrap:wrap">{ih}</div></div>""",unsafe_allow_html=True)

def render_speedometer(m):
    st.plotly_chart(build_speedometer_gauges(m),use_container_width=True,theme=None,config={'displayModeBar':False})
    bias=m['overall_bias']; sc=m.get('bias_score',0)
    styles={'STRONG BUY':('rgba(0,230,118,.15)','#00E676','🟢🟢'),'BUY':('rgba(0,230,118,.10)','#00E676','🟢'),
        'STRONG SELL':('rgba(255,23,68,.15)','#FF1744','🔴🔴'),'SELL':('rgba(255,23,68,.10)','#FF1744','🔴')}
    bg,clr,ico=styles.get(bias,('rgba(255,193,7,.10)','#FFC107','🟠'))
    bp=m.get('buy_proximity',0); sp2=m.get('sell_proximity',0)
    prox=""
    if bp>=50: prox=f"<span style='color:#00E676'>매수 임박 {bp:.0f}%</span>"
    elif sp2>=50: prox=f"<span style='color:#FF1744'>매도 임박 {sp2:.0f}%</span>"
    sq=" · <span style='color:#FFFF00;font-weight:600'>💥 Squeeze ON</span>" if m.get('squeeze_on') else ""
    st.markdown(f"""<div style="background:{bg};border-radius:10px;padding:10px 16px;text-align:center;margin:4px 0 12px 0">
        <span style="font-size:1.1rem;font-weight:700;color:{clr}">{ico} 종합 판정: {bias} ({sc:.1f})</span>
        {f' · {prox}' if prox else ''}{sq}</div>""",unsafe_allow_html=True)

def render_alerts(m):
    alerts=[]
    bp=m.get('buy_proximity',0); sp2=m.get('sell_proximity',0)
    if bp>=70: alerts.append(('🟢⚡ 매수 매우 임박!','#00E676',bp))
    elif bp>=50: alerts.append(('🟢 매수 접근 중','#69F0AE',bp))
    if sp2>=70: alerts.append(('🔴⚡ 매도 매우 임박!','#FF1744',sp2))
    elif sp2>=50: alerts.append(('🔴 매도 접근 중','#FF5252',sp2))
    if m.get('squeeze_on'): alerts.append(('💥 Squeeze ON','#FFFF00',80))
    for txt,clr,pct in alerts:
        w=min(pct,100)
        st.markdown(f"""<div style="background:rgba(255,255,255,.03);border:1px solid #2D333B;border-radius:8px;padding:8px 14px;margin:4px 0">
            <div style="display:flex;justify-content:space-between;align-items:center"><span style="color:{clr};font-weight:600;font-size:.9rem">{txt}</span>
            <span style="color:{clr};font-weight:700;font-size:.85rem">{pct:.0f}%</span></div>
            <div style="background:#1A1D24;border-radius:3px;height:6px;margin-top:6px"><div style="background:{clr};width:{w}%;height:6px;border-radius:3px"></div></div></div>""",unsafe_allow_html=True)

def render_signals(m):
    sigs=m['recent_signals']
    if not sigs:
        st.markdown('<div class="signal-card signal-card-neutral"><p style="margin:0;color:#FFC107;font-weight:600">🟠 최근 15일 내 시그널 없음</p></div>',unsafe_allow_html=True); return
    dg=OrderedDict()
    for icon,lbl,ds,side in sigs: dg.setdefault(ds,[]).append((icon,lbl,side))
    alls=m.get('all_signal_stats',{})
    for ds in reversed(dg):
        group=dg[ds]; bc=sum(1 for _,_,s in group if s=='buy'); sc2=sum(1 for _,_,s in group if s=='sell')
        ct='signal-card-buy' if bc>sc2 else ('signal-card-sell' if sc2>bc else 'signal-card-neutral')
        parts=[]
        for i,l,s in group:
            cn="ind-bullish" if s=="buy" else "ind-bearish"; sh=""
            for sn,sv in alls.items():
                if ALL_CHART_SIGNALS.get(sn,{}).get('label')==l:
                    wr=sv.get('2d_winrate')
                    if wr is not None: sh=f" ({wr:.0f}%)"
                    break
            parts.append(f'<span class="indicator-mini {cn}">{i} {l}{sh}</span>')
        st.markdown(f"""<div class="signal-card {ct}"><div style="display:flex;justify-content:space-between;align-items:center">
            <span style="font-weight:700;font-size:.9rem;color:#FAFAFA">📅 {ds}</span>
            <span style="color:#888;font-size:.75rem">{len(group)}개</span></div>
            <div style="margin-top:6px;display:flex;gap:4px;flex-wrap:wrap">{" ".join(parts)}</div></div>""",unsafe_allow_html=True)

def render_stats(m):
    with st.expander("📊 백테스트 (2년, 진입: 시그널 다음날 시가, 청산: 2일 후 종가)",expanded=True):
        alls=m.get('all_signal_stats',{})
        if not alls: st.caption("통계 없음"); return
        def _side(title,data,is_sell=False):
            st.markdown(f"##### {title}")
            for sn,sv in sorted(data.items(),key=lambda x:x[1]['count'],reverse=True):
                wr=sv.get('2d_winrate'); av=sv.get('2d_avg')
                if wr is None: continue
                kor=ALL_CHART_SIGNALS.get(sn,{}).get('kor',sn); c2='#00E676' if wr>50 else ('#FFC107' if wr>40 else '#FF1744')
                lb=f"승률 <span style='color:{c2}'>**{wr:.0f}%**</span>"
                if is_sell:
                    ac='#00E676' if av<0 else '#FF1744'
                    at2=f"<span style='color:{ac}'>**{abs(av):.1f}% 하락**</span>" if av<0 else f"<span style='color:{ac}'>**{av:+.1f}%(실패)**</span>"
                else:
                    ac='#00E676' if av>0 else '#FF1744'
                    at2=f"<span style='color:{ac}'>**{av:+.1f}% 상승**</span>" if av>0 else f"<span style='color:{ac}'>**{abs(av):.1f}%(실패)**</span>"
                ic=ALL_CHART_SIGNALS.get(sn,{}).get('icon','')
                st.markdown(f"<span style='font-size:.85rem'>{ic} **{kor}** ({sv['count']}회) · {lb} · 평균: {at2}</span>",unsafe_allow_html=True)
        c1,c2=st.columns(2)
        with c1: _side("🟢 BUY (롱)",{k:v for k,v in alls.items() if v['direction']=='buy'},False)
        with c2: _side("🔴 SELL (숏)",{k:v for k,v in alls.items() if v['direction']=='sell'},True)

def render_analysis(msg):
    m,fig=msg.get('meta'),msg.get('fig')
    if m: render_price_header(m); render_speedometer(m); render_alerts(m)
    if m or fig:
        t1,t2,t3,t4=st.tabs(["📊 정밀 차트","🔔 발생 시그널","📈 백테스트 통계","🏢 기업 펀더멘탈 상세"])
        with t1:
            if fig: st.plotly_chart(fig,use_container_width=True,theme=None,config={'displaylogo':False,'modeBarButtonsToRemove':['lasso2d','select2d','hoverCompareCartesian','hoverClosestCartesian']})
        with t2:
            if m: render_signals(m)
        with t3:
            if m: render_stats(m)
        with t4:
            if m: render_company_details(m['ticker'])

# ──────────────────────────────────────────
# 사이드바
# ──────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🚦 CipherX")
    st.markdown("<p style='color:#888;font-size:.8rem'>AI 퀀트 주가 분석 · v10.1</p>",unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("### 📅 차트 기간")
    chart_period=st.radio("표시 기간",['3개월','6개월','1년','2년'],index=0,horizontal=True,key="period")
    chart_days={'3개월':63,'6개월':126,'1년':252,'2년':504}[chart_period]
    st.markdown("---")
    with st.expander("🎛️ 시그널 필터",expanded=False):
        _sb=st.checkbox("🟢 매수 시그널",value=True,key="sb")
        _ss=st.checkbox("🔴 매도 시그널",value=True,key="ss")
        _sc=st.checkbox("⭐ 복합 시그널",value=True,key="sc")
        _mw=st.slider("최소 가중치",0.0,3.0,0.0,0.5,key="mw")
        enabled=set()
        for k,v in ALL_CHART_SIGNALS.items():
            if v['dir']=='buy' and not _sb: continue
            if v['dir']=='sell' and not _ss: continue
            if k in COMPOSITE_SIGNALS and not _sc: continue
            if v['w']<_mw and k not in COMPOSITE_SIGNALS: continue
            enabled.add(k)
        st.session_state['enabled_signals']=enabled
        st.caption(f"표시: {len(enabled)}개")
    st.markdown("---")
    if st.button("🗑️ 대화 내역 지우기",use_container_width=True,type="secondary"):
        for key in ['messages','pending_ai_ticker','pending_ai_prompt','last_ticker']:
            st.session_state[key]=[{"role":"assistant","type":"text","content":"안녕하세요! 🚦 **CipherX v10.1** 입니다.\n\n분석할 **티커명**을 입력하세요."}] if key=='messages' else None
        st.rerun()

# ──────────────────────────────────────────
# 세션 관리
# ──────────────────────────────────────────
if 'messages' not in st.session_state:
    st.session_state.messages=[{"role":"assistant","type":"text","content":"안녕하세요! 🚦 **CipherX v10.1** 입니다.\n\n분석할 **티커명**을 입력하세요."}]
for key in ['pending_ai_ticker','pending_ai_prompt','last_ticker']:
    if key not in st.session_state: st.session_state[key]=None
if 'enabled_signals' not in st.session_state:
    st.session_state['enabled_signals']=set(ALL_CHART_SIGNALS.keys())

# ──────────────────────────────────────────
# 챗 인터페이스
# ──────────────────────────────────────────
st.markdown("<h2 style='text-align:center;color:#fff;margin-bottom:20px'>🚦 CipherX</h2>",unsafe_allow_html=True)

if not st.session_state.last_ticker:
    st.markdown("<p style='text-align:center;color:#888;font-size:0.9rem;'>🔥 추천 주식 빠르게 분석해보기</p>",unsafe_allow_html=True)
    cols=st.columns(4); quick_tickers=["NVDA","TSLA","AAPL","QQQ"]
    for idx,col in enumerate(cols):
        with col:
            if st.button(quick_tickers[idx],use_container_width=True): st.session_state['quick_ticker']=quick_tickers[idx]
    st.markdown("<br>",unsafe_allow_html=True)

for i,msg in enumerate(st.session_state.messages):
    av="✨" if msg["role"]=="assistant" else "🧑‍💻"
    with st.chat_message(msg["role"],avatar=av):
        if msg.get("type")=="analysis":
            st.markdown(msg.get("content","")); render_analysis(msg)
            if msg.get("prompt"):
                with st.expander("📝 퀀트 프롬프트 원문",expanded=False):
                    st.code(msg["prompt"],language="markdown"); st_copy_to_clipboard(msg["prompt"],before_copy_label="📋 복사",after_copy_label="✅ 복사됨!")
        elif msg.get("type")=="report":
            with st.expander(f"📊 {msg.get('ticker','')} AI 퀀트 리포트",expanded=True): st.markdown(msg["content"])
            st.download_button("📥 마크다운 다운로드",key=f"dl_{i}_{msg.get('ticker','RPT')}",data=msg["content"].encode('utf-8'),
                file_name=f"{msg.get('ticker','RPT').upper()}_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.md",mime="text/markdown",use_container_width=True)
        else: st.markdown(msg.get("content",""))

def _run_ai():
    tp=st.session_state.pending_ai_ticker; pp=st.session_state.pending_ai_prompt
    with st.chat_message("assistant",avatar="✨"):
        pb=st.progress(0,text="퀀트 엔진 로딩 중...")
        try:
            pb.progress(10,text="Gemini 모델 초기화 중..."); model=genai.GenerativeModel('gemini-2.5-flash')
            pb.progress(20,text="시장 데이터 취합 중..."); collected=[]
            def gen():
                pb.progress(40,text="🚀 AI 리포트 생성 중...")
                response=model.generate_content(pp,stream=True); cnt=0
                for chunk in response:
                    t=chunk.text
                    if t: collected.append(t); cnt+=1; pb.progress(min(40+cnt*2,95),text="전략 산출 중..."); yield t
                pb.progress(100,text="✅ 완료!")
            with st.expander(f"📊 {tp.upper()} AI 퀀트 리포트",expanded=True): st.write_stream(gen())
            time.sleep(0.3); pb.empty()
            st.session_state.messages.append({"role":"assistant","type":"report","ticker":tp.upper(),"content":"".join(collected)})
            st.session_state.pending_ai_ticker=None; st.session_state.pending_ai_prompt=None; st.rerun()
        except Exception as e: pb.empty(); st.error(f"AI 오류: {e}")

def process_ticker(tv,refresh=False):
    tv=tv.strip().upper(); st.session_state.pending_ai_ticker=None; st.session_state.pending_ai_prompt=None
    if not _valid_fmt(tv): st.toast(f"⚠️ **{tv}** — 올바른 티커 형식이 아닙니다.",icon="🚨"); return
    if not validate_ticker(tv): st.toast(f"⚠️ **{tv}** — Yahoo Finance에서 찾을 수 없습니다.",icon="🔍"); return
    st.session_state.messages.append({"role":"user","type":"text","content":tv}); st.session_state.last_ticker=tv
    with st.chat_message("assistant",avatar="✨"):
        with st.status(f"🌐 {tv} 퀀트 파이프라인 가동 중...",expanded=True) as status:
            st.write("📡 데이터 조회 중..."); fundamentals=fetch_fundamentals(tv)
            st.write("📊 시그널 엔진 검증 중..."); fig,phist,meta=analyze(tv,chart_days,refresh)
            if fig: prompt=build_ai_prompt(tv,phist,fundamentals); status.update(label=f"✅ {tv} 분석 완료!",state="complete",expanded=False)
            else: status.update(label=f"⚠️ {tv} 실패",state="error",expanded=False)
        if fig:
            st.session_state.messages.append({"role":"assistant","type":"analysis","ticker":tv,
                "content":f"✅ **{tv}** 분석이 완료되었습니다.","fig":fig,"meta":meta,"prompt":prompt})
            st.session_state.pending_ai_ticker=tv; st.session_state.pending_ai_prompt=prompt; st.rerun()
        else:
            st.session_state.messages.append({"role":"assistant","type":"text","content":f"⚠️ **{tv}** 데이터 부족"}); st.rerun()

if st.session_state.get('quick_ticker'): process_ticker(st.session_state.pop('quick_ticker'))

if st.session_state.last_ticker:
    lt=st.session_state.last_ticker; c1,c2=st.columns([3,1])
    with c1:
        if st.session_state.pending_ai_ticker and st.session_state.pending_ai_prompt:
            if st.button(f"🚀 {st.session_state.pending_ai_ticker.upper()} AI 심층 분석",type="primary",use_container_width=True): _run_ai()
    with c2:
        if st.button(f"🔄 {lt}",type="secondary",use_container_width=True,key="re"): process_ticker(lt,refresh=True)
elif st.session_state.pending_ai_ticker and st.session_state.pending_ai_prompt:
    if st.button(f"🚀 {st.session_state.pending_ai_ticker.upper()} AI 심층 분석",type="primary",use_container_width=True): _run_ai()

if ticker_input:=st.chat_input("미국 주식 티커 입력 (예: TSLA, AAPL, QQQ)"): process_ticker(ticker_input)