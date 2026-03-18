# ══════════════════════════════════════════════════════════════
#  CipherX V12.0 — Anticipatory Judgment Architecture
#  PART 1/4: 임포트 + 상수 + 지표 엔진 + 🆕 선행 지표
#  V11.1→V12.0 주요변경:
#    🆕 ANTIC  선행/예측 지표 추가
#    🔧 FIX    MF 이중계산 버그, 시그널 정리
#    ⚡ PERF   벡터화, 캐싱 강화
#    🧹 CLEAN  함수 분할, 네이밍 개선
# ══════════════════════════════════════════════════════════════

import streamlit as st
import google.generativeai as genai
import time
import re
from datetime import datetime
from typing import Dict, Tuple, Optional, Any, List
from st_copy_to_clipboard import st_copy_to_clipboard
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from plotly.subplots import make_subplots
from collections import OrderedDict
from company_details import render_company_details

# ──────────────────────────────────────────
# 페이지 설정
# ──────────────────────────────────────────
st.set_page_config(
    page_title="CipherX V12.0",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ──────────────────────────────────────────
# CSS (별도 함수로 분리 — 🧹 CLEAN)
# ──────────────────────────────────────────
def inject_css():
    st.markdown("""<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
html,body,[class*="css"]{font-family:'Pretendard','Noto Sans KR',sans-serif!important}
span[class*="material-symbols"],span[class*="material-icons"],
i[class*="material-icons"],.stIcon,[data-testid="stIconMaterial"]{
    font-family:'Material Symbols Rounded','Material Icons',sans-serif!important}
.stApp{background-color:#0B0E14}
p,div[data-testid="stMarkdownContainer"] p,div[data-testid="stChatMessageContent"] p,
li{color:#E8ECF1!important}
h1{color:#FFFFFF!important;font-weight:800!important;letter-spacing:-0.5px}
h2{color:#FFFFFF!important;font-weight:700!important}
h3{color:#F0F4F8!important;font-weight:700!important}
h4{color:#CBD5E1!important;font-weight:600!important;font-size:1rem!important;
   margin-top:1.5rem!important;margin-bottom:0.8rem!important;
   padding-bottom:6px;border-bottom:1px solid rgba(255,255,255,0.06)}
h5{color:#94A3B8!important;font-weight:600!important;font-size:.9rem!important;
   text-transform:uppercase;letter-spacing:1px}
div[data-testid="stCodeBlock"],pre,code{background-color:#151921!important;color:#E2E8F0!important;
    border:1px solid #1E2530!important;border-radius:10px!important}
div[data-testid="stCodeBlock"] span{text-shadow:none!important}
div[data-testid="stCodeBlock"] span[style*="color: rgb(0, 0, 0)"],
div[data-testid="stCodeBlock"] span[style*="color: black"],
div[data-testid="stCodeBlock"] code>span:not([class]){color:#E2E8F0!important}
div[data-testid="stChatMessage"]:nth-child(even){background-color:#10141C;border-radius:14px;
    padding:8px 18px;border:1px solid rgba(255,255,255,0.03)}
.block-container{padding-top:1rem!important;max-width:960px}
@media(max-width:768px){
    .block-container{padding-left:.5rem!important;padding-right:.5rem!important}
    .price-big{font-size:1.6rem!important}
    div[data-testid="stPlotlyChart"]{margin-left:-10px!important;margin-right:-10px!important}
}
div.stButton>button[kind="primary"]{
    background:linear-gradient(135deg,#6366F1 0%,#8B5CF6 50%,#A78BFA 100%)!important;
    color:white!important;border:none!important;border-radius:12px!important;
    padding:.65rem 1.5rem!important;font-weight:700!important;font-size:1rem!important;
    transition:all .3s cubic-bezier(.4,0,.2,1)!important;width:100%;
    box-shadow:0 4px 14px rgba(99,102,241,.3)!important}
div.stButton>button[kind="primary"]:hover{
    transform:translateY(-2px);box-shadow:0 8px 25px rgba(139,92,246,.45)!important;
    filter:brightness(1.08)}
div.stButton>button[kind="secondary"]{
    background-color:#12161F!important;color:#C4CDD8!important;
    border:1px solid #2A3040!important;border-radius:12px!important;
    font-weight:600!important;transition:all .2s ease!important;width:100%}
div.stButton>button[kind="secondary"]:hover{
    border-color:#6366F1!important;color:#A5B4FC!important;background-color:#161B27!important}
.streamlit-expanderHeader{background-color:#10141C!important;border-radius:12px!important;
    font-weight:700!important;padding:12px 16px!important}
.streamlit-expanderHeader p{color:#A5B4FC!important}
div[data-testid="stExpander"]{border:1px solid #1C2233!important;border-radius:12px!important;
    background-color:#0D1017;overflow:hidden}
div[data-testid="stExpanderDetails"]{padding:12px 16px!important}
div[data-testid="stExpanderDetails"] h1{font-size:1.5rem!important;margin-bottom:.5rem!important;
    padding-bottom:.3rem!important;border-bottom:1px solid #1C2233}
div[data-testid="stExpanderDetails"] h2{font-size:1.3rem!important;margin-top:1.2rem!important}
div[data-testid="stExpanderDetails"] h3{font-size:1.15rem!important;color:#93C5FD!important}
div[data-testid="stExpanderDetails"] p,div[data-testid="stExpanderDetails"] li{
    font-size:.95rem!important;line-height:1.7!important;color:#B8C5D3!important}
div[data-testid="stExpanderDetails"] blockquote{border-left-color:#6366F1!important;color:#94A3B8!important}
div[data-testid="stExpanderDetails"] table{font-size:.85rem!important;width:100%!important}
div[data-testid="stExpanderDetails"] th{color:#CBD5E1!important;background:rgba(255,255,255,0.03)!important;
    padding:.5rem .7rem!important;font-weight:600}
div[data-testid="stExpanderDetails"] td{padding:.45rem .7rem!important;color:#94A3B8!important;
    border-color:rgba(255,255,255,0.04)!important}
header{background-color:transparent!important}
div[data-testid="collapsedControl"]{display:flex!important;z-index:999999!important}
section[data-testid="stSidebar"]{background-color:#080A10;border-right:1px solid #151921}
section[data-testid="stSidebar"] .stMarkdown p{color:#8896A8!important}
section[data-testid="stSidebar"] [data-testid="stSidebarCollapsedControl"]{
    background:rgba(11,14,20,0.95)!important;border:1px solid #1C2233!important;border-radius:10px!important}
.signal-card{border-radius:14px;padding:14px 18px;margin:8px 0;
    border:1px solid rgba(255,255,255,0.06);backdrop-filter:blur(10px)}
.signal-card-buy{
    background:linear-gradient(135deg,rgba(0,230,118,.06) 0%,rgba(16,185,129,.03) 100%);
    border-left:4px solid #10B981}
.signal-card-sell{
    background:linear-gradient(135deg,rgba(239,68,68,.06) 0%,rgba(220,38,38,.03) 100%);
    border-left:4px solid #EF4444}
.signal-card-neutral{
    background:linear-gradient(135deg,rgba(245,158,11,.06) 0%,rgba(217,119,6,.03) 100%);
    border-left:4px solid #F59E0B}
.price-header{
    background:linear-gradient(160deg,#0F1320 0%,#141926 50%,#111827 100%);
    border:1px solid #1C2233;border-radius:16px;padding:20px 24px;margin-bottom:18px;
    box-shadow:0 4px 20px rgba(0,0,0,0.3)}
.price-big{font-size:2.2rem;font-weight:800;margin:0;letter-spacing:-0.5px}
.price-change-up{color:#34D399!important}
.price-change-down{color:#F87171!important}
.price-label{color:#64748B!important;font-size:.8rem;margin:0;font-weight:500;
    text-transform:uppercase;letter-spacing:0.5px}
.indicator-mini{display:inline-block;padding:5px 11px;margin:3px;border-radius:8px;
    font-size:.78rem;font-weight:600;letter-spacing:0.2px;
    border:1px solid rgba(255,255,255,0.04)}
.ind-bullish{background:rgba(16,185,129,.12);color:#6EE7B7;border-color:rgba(16,185,129,.2)}
.ind-bearish{background:rgba(239,68,68,.12);color:#FCA5A5;border-color:rgba(239,68,68,.2)}
.ind-neutral{background:rgba(245,158,11,.10);color:#FCD34D;border-color:rgba(245,158,11,.15)}
div[data-testid="stTabs"] button{color:#64748B!important;font-weight:700!important;
    font-size:.9rem!important;padding:10px 16px!important;
    border-bottom:3px solid transparent!important;transition:all .2s ease}
div[data-testid="stTabs"] button:hover{color:#A5B4FC!important}
div[data-testid="stTabs"] button[aria-selected="true"]{
    color:#A5B4FC!important;border-bottom-color:#6366F1!important}
.judgment-card{border-radius:16px;padding:24px 28px;margin-bottom:20px;text-align:center;
    position:relative;overflow:hidden}
.judgment-card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px}
.judgment-card-buy{background:linear-gradient(160deg,#052E16 0%,#0D1B2A 100%);
    border:1px solid rgba(16,185,129,.25)}
.judgment-card-buy::before{background:linear-gradient(90deg,#10B981,#34D399)}
.judgment-card-sell{background:linear-gradient(160deg,#2A0E0E 0%,#1B0D1B 100%);
    border:1px solid rgba(239,68,68,.25)}
.judgment-card-sell::before{background:linear-gradient(90deg,#EF4444,#F87171)}
.judgment-card-neutral{background:linear-gradient(160deg,#1A1608 0%,#1B1A0D 100%);
    border:1px solid rgba(245,158,11,.2)}
.judgment-card-neutral::before{background:linear-gradient(90deg,#F59E0B,#FCD34D)}
.combo-card{border-radius:12px;padding:12px 16px;margin:6px 0;display:flex;
    align-items:center;justify-content:space-between;
    border:1px solid rgba(255,255,255,0.06);transition:transform .15s ease}
.combo-card:hover{transform:translateX(4px)}
.combo-buy{background:linear-gradient(135deg,rgba(16,185,129,.08),rgba(6,78,59,.05));
    border-left:3px solid #10B981}
.combo-sell{background:linear-gradient(135deg,rgba(239,68,68,.08),rgba(127,29,29,.05));
    border-left:3px solid #EF4444}
.layer-bar-wrap{padding:4px 0}
.layer-bar-bg{background:#151921;border-radius:6px;height:10px;overflow:hidden;
    border:1px solid rgba(255,255,255,0.03)}
.layer-bar-fill{height:10px;border-radius:6px;transition:width .5s cubic-bezier(.4,0,.2,1)}
.layer-bar-fill-buy{background:linear-gradient(90deg,#059669,#34D399)}
.layer-bar-fill-sell{background:linear-gradient(90deg,#DC2626,#F87171)}
.history-row{display:flex;align-items:center;padding:8px 14px;margin:4px 0;
    border-radius:10px;background:rgba(255,255,255,0.015);
    border:1px solid rgba(255,255,255,0.04);transition:background .15s ease}
.history-row:hover{background:rgba(255,255,255,0.03)}
.alert-bar{border-radius:10px;padding:10px 16px;margin:5px 0;
    border:1px solid rgba(255,255,255,0.06);backdrop-filter:blur(8px)}
.alert-bar-progress{background:#151921;border-radius:4px;height:5px;margin-top:8px;overflow:hidden}
.alert-bar-fill{height:5px;border-radius:4px;transition:width .4s ease}
table{border-collapse:collapse!important;border:none!important}
th{background:rgba(99,102,241,.08)!important;color:#C4CDD8!important;
    font-weight:700!important;border:1px solid rgba(255,255,255,0.06)!important}
td{border:1px solid rgba(255,255,255,0.04)!important;color:#94A3B8!important}
tr:hover td{background:rgba(255,255,255,0.02)!important}
::-webkit-scrollbar{width:6px;height:6px}
::-webkit-scrollbar-track{background:#0B0E14}
::-webkit-scrollbar-thumb{background:#2A3040;border-radius:3px}
::-webkit-scrollbar-thumb:hover{background:#3D4A5F}
</style>""", unsafe_allow_html=True)

inject_css()


# ══════════════════════════════════════════
#  상수 (🔧 FIX + 🆕 선행지표 임계값 추가)
# ══════════════════════════════════════════
OB1, OB2, OS1, OS2 = 53, 60, -53, -60
ST_MIN_BAR = 12
NUM_LAYERS = 8  # 🆕 7→8 (Anticipation 레이어 추가)


class JudgmentThresholds:
    """판단 엔진 임계값 — 한곳에서 관리"""
    # ── 매수 임계값 ──
    STRONG_BUY_SCORE = 18.0   # 🔧 17→18 (레이어 추가 반영)
    BUY_SCORE = 12.0          # 🔧 11→12
    WATCH_BUY_SCORE = 6.5     # 🔧 6→6.5
    STRONG_BUY_LAYERS = 5     # 🔧 4→5
    BUY_LAYERS = 3
    WATCH_LAYERS = 2
    STRONG_BUY_RATIO = 2.0
    BUY_RATIO = 1.4
    STRONG_BUY_DIFF = 10.0
    BUY_DIFF = 5.0
    WATCH_DIFF = 2.0
    SELL_ASYMMETRY = 0.85
    LOW_VOL_SCALE = 0.85
    MIXED_MIN = 9.0
    MIXED_DIFF_MAX = 3.0
    # ── 레이어별 점수 캡 ──
    TREND_CAP = 12.0       # 🆕 명시
    MOMENTUM_CAP = 10.0
    CANDLE_CAP = 5.0
    BB_CAP = 7.0
    VOLUME_CAP = 7.0
    MF_CAP = 8.0
    PATTERN_CAP = 10.0
    ANTICIPATION_CAP = 8.0  # 🆕 선행지표 레이어 캡
    CROSS_SIGNAL_CAP = 6.0  # 🔧 4→6 (정보 손실 방지)
    # ── 🆕 선행지표 임계값 ──
    ACCEL_STRONG = 3.0       # 강한 가속 감지 임계
    ACCEL_MODERATE = 1.5     # 중간 가속 감지 임계
    CONVERGENCE_FAST = 3.0   # 빠른 수렴 (봉당 gap 감소)
    CONVERGENCE_SLOW = 1.5   # 느린 수렴
    SETUP_MATURITY = 3       # 셋업 조건 최소 축적 일수
    # ── 🆕 콤보 등급별 보너스 ──
    COMBO_TIER1_BONUS = 4.0  # 3개+ 독립 확인
    COMBO_TIER2_BONUS = 2.5  # 2개 독립 확인
    COMBO_TIER3_BONUS = 1.5  # 기본 콤보


JT = JudgmentThresholds

GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GEMINI_API_KEY)


@st.cache_resource
def get_gemini_model():
    return genai.GenerativeModel('gemini-2.5-flash')


# ══════════════════════════════════════════
#  시그널 레지스트리 (🧹 정리 + 🔧 수정)
#  변경: Spinning_Top → neutral, Below_Lower_BB → 방향 분리
#        중복 시그널 가중치 조정
# ══════════════════════════════════════════
_B, _S, _N = 'buy', 'sell', 'neutral'

def _sig(w, d, icon, label, sym, sz, clr, base, atr_m, kor, desc):
    return {'w': w, 'dir': d, 'icon': icon, 'label': label, 'sym': sym, 'sz': sz,
            'clr': clr, 'base': base, 'atr_m': atr_m, 'kor': kor, 'desc': desc}

SIGNAL_REGISTRY = {
    # ═══ MCB+ 매수 (21) ═══
    'Gold_Dot':              _sig(3.0,_B,'🏆','GOLD DOT','circle',18,'#FFD700','Low',-3.0,'최강 매수','RSI<30+MFI<30+WT1<-60+상승다이버전스'),
    'Green_Dot_T1':          _sig(2.5,_B,'🟢','BUY T1','circle',16,'#00E676','Low',-2.5,'강한 매수','WT과매도교차+RSI<30+MFI<30+MF<0'),
    'Green_Dot_T2':          _sig(2.0,_B,'🟩','BUY T2','circle',13,'#69F0AE','Low',-2.2,'매수','WT과매도+RSI또는MFI<32'),
    'Blue_Diamond':          _sig(2.0,_B,'🔹','BLUE DIA','diamond',14,'#00bfff','Low',-1.8,'추세 매수','WT2≤0 상승교차+HTF강세'),
    'Green_Circle':          _sig(0.8,_B,'✅','BUY Circle','circle-open',11,'#00E676','Low',-1.2,'과매도 반등','WT과매도교차+RSI<45'),
    'Bull_Divergence':       _sig(2.0,_B,'📈','Bull Div','triangle-up',12,'#AA00FF','Low',-2.0,'상승 다이버전스','가격↓ vs WT↑'),
    'RSI_Bull_Divergence':   _sig(1.5,_B,'📊','RSI Bull Div','triangle-up',11,'#CE93D8','Low',-1.8,'RSI 상승 다이버전스','가격↓ vs RSI↑'),
    'Squeeze_Fire_Buy':      _sig(1.5,_B,'💥','Squeeze BUY','star-diamond',14,'#00FFFF','Low',-1.5,'스퀴즈 매수','TTM Squeeze 해소+모멘텀↑'),
    'Hidden_Bull_Div':       _sig(1.5,_B,'🔀','Hidden Bull','triangle-up',10,'#E040FB','Low',-1.6,'히든 상승 다이버전스','가격↑ vs WT↓+거래량'),
    'Volume_Climax_Buy':     _sig(2.0,_B,'🌊','Vol Climax BUY','hexagram',14,'#00BCD4','Low',-2.8,'거래량 클라이맥스','3x거래량+하락장대봉+WT과매도→반등'),
    'OBV_Div_Buy':           _sig(0.8,_B,'📊','OBV Div BUY','triangle-up',10,'#80DEEA','Low',-1.4,'OBV 다이버전스','OBV↑ vs 가격↓'),
    'ADX_Momentum_Buy':      _sig(1.5,_B,'🚀','ADX Ignition','arrow-up',11,'#76FF03','Low',-1.4,'ADX 점화','ADX>20돌파+DI↑'),
    'Bullish_Engulfing':     _sig(1.5,_B,'☀️','Bull Engulf','square',10,'#00E676','Low',-1.3,'상승 장악형','하락캔들 감싸는 상승캔들+WT<-20'),
    'Golden_Cross':          _sig(1.5,_B,'✨','Golden Cross','cross',12,'#FFD700','Low',-0.8,'골든 크로스','50MA>200MA+ADX>15'),
    'EMA_Pullback_Buy':      _sig(2.0,_B,'🎯','EMA Pullback','triangle-up',13,'#00BFA5','Low',-1.8,'EMA 눌림목','상승추세 EMA조정후 WT반등'),
    'Momentum_Ignition_Buy': _sig(2.5,_B,'🔥','Mom. Ignition','star-diamond',15,'#FF6D00','Low',-2.5,'모멘텀 점화','장대양봉>ATR×1.5+거래량>2x'),
    'SuperTrend_Buy':        _sig(1.5,_B,'📈','ST Flip Bull','arrow-up',12,'#00E5FF','Low',-1.5,'슈퍼트렌드 강세','SuperTrend 위로 돌파'),
    'VWAP_Bounce_Buy':       _sig(1.5,_B,'🏦','VWAP Bounce','triangle-up',11,'#00E5FF','Low',-1.3,'VWAP 반등','VWAP 복귀+WT교차'),
    'Parabolic_Bottom_Buy':  _sig(3.0,_B,'🧊','Parabolic Bot','diamond',16,'#00FFFF','Low',-3.0,'포물선 바닥','WT1<-80 꺾임+양봉'),  # 🔧 -85→-80
    'MACD_Cross_Buy':        _sig(1.0,_B,'〽️','MACD Cross','triangle-up',9,'#4CAF50','Low',-1.0,'MACD 골든크로스','MACD>시그널(0선하방)'),
    'StochRSI_Cross_Buy':    _sig(0.8,_B,'🔄','StRSI Cross','circle-open',8,'#81C784','Low',-0.8,'StochRSI 매수교차','StochK>StochD(과매도)'),

    # ═══ MCB+ 매도 (21) ═══
    'Blood_Diamond':         _sig(3.0,_S,'🩸','BLOOD DIA','diamond',18,'#DC143C','High',3.0,'최강 매도','RSI>70+MFI>70+WT1>60+하락다이버전스'),
    'Red_Dot_T1':            _sig(2.5,_S,'🔴','SELL T1','circle',16,'#FF1744','High',2.5,'강한 매도','WT과매수하락교차+RSI>70+MFI>70'),
    'Red_Dot_T2':            _sig(2.0,_S,'🟥','SELL T2','circle',13,'#FF5252','High',2.2,'매도','WT과매수+RSI또는MFI>68'),
    'Red_Diamond':           _sig(2.0,_S,'🔸','RED DIA','diamond',14,'#ff3333','High',1.8,'추세 매도','WT2≥0 하락교차+HTF약세'),
    'Red_Circle':            _sig(0.8,_S,'⛔','SELL Circle','circle-open',11,'#FF1744','High',1.2,'과매수 하락','WT과매수하락교차+RSI>55'),
    'Bear_Divergence':       _sig(2.0,_S,'📉','Bear Div','triangle-down',12,'#AA00FF','High',2.0,'하락 다이버전스','가격↑ vs WT↓'),
    'RSI_Bear_Divergence':   _sig(1.5,_S,'📉','RSI Bear Div','triangle-down',11,'#CE93D8','High',1.8,'RSI 하락 다이버전스','가격↑ vs RSI↓'),
    'Squeeze_Fire_Sell':     _sig(1.5,_S,'🧨','Squeeze SELL','star-diamond',14,'#FF6600','High',1.5,'스퀴즈 매도','TTM Squeeze 해소+모멘텀↓'),
    'Hidden_Bear_Div':       _sig(1.5,_S,'🔁','Hidden Bear','triangle-down',10,'#E040FB','High',1.6,'히든 하락 다이버전스','가격↓ vs WT↑+거래량'),
    'Volume_Climax_Sell':    _sig(2.0,_S,'🌋','Vol Climax SELL','hexagram',14,'#FF5722','High',2.8,'거래량 클라이맥스','3x거래량+상승장대봉+WT과매수→하락'),
    'OBV_Div_Sell':          _sig(0.8,_S,'🔻','OBV Div SELL','triangle-down',10,'#FFAB91','High',1.4,'OBV 다이버전스','OBV↓ vs 가격↑'),
    'ADX_Momentum_Sell':     _sig(1.5,_S,'💨','ADX Down','arrow-down',11,'#FF3D00','High',1.4,'ADX 하락 점화','ADX>20돌파+-DI>+DI'),
    'Bearish_Engulfing':     _sig(1.5,_S,'🌑','Bear Engulf','x',10,'#D50000','High',1.3,'하락 장악형','상승캔들 감싸는 하락캔들+WT>20'),
    'Death_Cross':           _sig(1.5,_S,'☠️','Death Cross','cross',12,'#FF1744','High',0.8,'데드 크로스','50MA<200MA+ADX>15'),
    'SuperTrend_Sell':       _sig(2.0,_S,'📉','ST Flip Bear','arrow-down',12,'#FF1744','High',1.5,'슈퍼트렌드 약세','SuperTrend 하향 돌파'),
    'Parabolic_Top_Sell':    _sig(3.0,_S,'🌡️','Parabolic Top','diamond',16,'#FF0000','High',3.0,'포물선 천장','WT1>80 꺾임+음봉'),  # 🔧 85→80
    'EMA_Pullback_Sell':     _sig(2.0,_S,'🎯','EMA PB Sell','triangle-down',13,'#FF6E40','High',1.8,'EMA 되돌림 매도','하락추세 EMA반등후 WT재하락'),
    'Momentum_Ignition_Sell':_sig(2.5,_S,'💣','Mom. Ign Sell','star-diamond',15,'#D50000','High',2.5,'모멘텀 점화 매도','장대음봉>ATR×1.5+거래량>2x'),
    'VWAP_Reject_Sell':      _sig(1.5,_S,'🏛️','VWAP Reject','triangle-down',11,'#FF6E40','High',1.3,'VWAP 저항','VWAP 실패+WT교차'),
    'MACD_Cross_Sell':       _sig(1.0,_S,'〽️','MACD Dead','triangle-down',9,'#E57373','High',1.0,'MACD 데드크로스','MACD<시그널(0선상방)'),
    'StochRSI_Cross_Sell':   _sig(0.8,_S,'🔄','StRSI Dead','circle-open',8,'#EF9A9A','High',0.8,'StochRSI 매도교차','StochK<StochD(과매수)'),

    # ═══ 캔들스틱 (6) — 🧹 Spinning_Top 제거 ═══
    'Hammer':               _sig(1.5,_B,'🔨','Hammer','triangle-up',11,'#00E676','Low',-1.5,'해머','긴하단꼬리+소형실체+WT<-20'),
    'Morning_Star':         _sig(2.0,_B,'🌅','MornStar','star',13,'#00E676','Low',-2.0,'모닝스타','큰음봉→소형봉→강한양봉'),
    'Doji_Bullish':         _sig(0.8,_B,'➕','Doji Bull','cross-thin',9,'#69F0AE','Low',-1.0,'강세 도지','시가≈종가+하락추세후 WT반등'),
    'Shooting_Star':        _sig(1.5,_S,'🌠','ShootStar','triangle-down',11,'#FF1744','High',1.5,'슈팅스타','긴상단꼬리+소형실체+WT>20'),
    'Evening_Star':         _sig(2.0,_S,'🌆','EveStar','star',13,'#FF1744','High',2.0,'이브닝스타','큰양봉→소형봉→강한음봉'),
    'Doji_Bearish':         _sig(0.8,_S,'➖','Doji Bear','cross-thin',9,'#FF5252','High',1.0,'약세 도지','시가≈종가+상승추세후 WT하락'),

    # ═══ Inside/Outside (3) ═══
    'Inside_Day':           _sig(0.3,_N,'📦','InsideDay','square-open',7,'#FFC107','Low',-0.3,'인사이드데이','고가<전일고&저가>전일저'),  # 🔧 방향→neutral
    'Outside_Bullish':      _sig(1.5,_B,'💪','OutsideBull','square',11,'#00E676','Low',-1.5,'강세 아웃사이드','전일범위포함+양봉+WT<30'),
    'Outside_Bearish':      _sig(1.5,_S,'🥊','OutsideBear','square',11,'#FF1744','High',1.5,'약세 아웃사이드','전일범위포함+음봉+WT>-30'),

    # ═══ MA 돌파/이탈 (6) ═══
    'Cross_Above_20MA':     _sig(0.8,_B,'📈','X▲20MA','triangle-up',9,'#69F0AE','Low',-0.8,'20MA상향돌파','종가>20MA'),
    'Cross_Above_50MA':     _sig(1.2,_B,'📈','X▲50MA','triangle-up',10,'#00E676','Low',-1.0,'50MA상향돌파','종가>50MA'),
    'Cross_Above_200MA':    _sig(1.5,_B,'📈','X▲200MA','triangle-up',11,'#00BFA5','Low',-1.2,'200MA상향돌파','종가>200MA'),
    'Fell_Below_20MA':      _sig(0.8,_S,'📉','X▼20MA','triangle-down',9,'#FF5252','High',0.8,'20MA하향이탈','종가<20MA'),
    'Fell_Below_50MA':      _sig(1.2,_S,'📉','X▼50MA','triangle-down',10,'#FF1744','High',1.0,'50MA하향이탈','종가<50MA'),
    'Fell_Below_200MA':     _sig(1.5,_S,'📉','X▼200MA','triangle-down',11,'#D50000','High',1.2,'200MA하향이탈','종가<200MA'),

    # ═══ 볼린저 밴드 (4) — 🔧 BB하단=매수기회로 분리 ═══
    'BB_Upper_Break':       _sig(1.0,_B,'🔝','BB▲Break','diamond-open',10,'#00E5FF','High',1.0,'BB상단돌파','종가>상단BB(강한모멘텀)'),
    'BB_Lower_Bounce':      _sig(1.2,_B,'⤵️','BB▼Bounce','diamond-open',10,'#4FC3F7','Low',-1.2,'BB하단반등','종가<하단BB+양봉전환(반등)'),  # 🔧 매도→매수
    'BB_Lower_Break':       _sig(1.0,_S,'💀','BB▼Break','diamond-open',10,'#FF6E40','Low',-1.0,'BB하단붕괴','종가<하단BB+약세지속'),  # 🆕 분리
    'BB_Squeeze_End_Bull':  _sig(1.5,_B,'💥','SqEnd▲','star-diamond',12,'#00FFFF','Low',-1.5,'BB스퀴즈해소↑','BB확장+상승+WT↑'),
    'BB_Squeeze_End_Bear':  _sig(1.5,_S,'💥','SqEnd▼','star-diamond',12,'#FF6600','High',1.5,'BB스퀴즈해소↓','BB확장+하락+WT↓'),

    # ═══ MACD 센터라인 (2) ═══
    'MACD_Zero_Cross_Buy':  _sig(1.2,_B,'⬆️','MACD 0▲','triangle-up',10,'#4CAF50','Low',-1.0,'MACD 0선돌파','MACD>0'),
    'MACD_Zero_Cross_Sell': _sig(1.2,_S,'⬇️','MACD 0▼','triangle-down',10,'#E57373','High',1.0,'MACD 0선이탈','MACD<0'),

    # ═══ 연속 (4) ═══
    'Up_3_Days':            _sig(0.5,_B,'📗','Up3D','triangle-up',8,'#69F0AE','High',0.5,'3일연속상승','3일연속양봉'),
    'Up_5_Days':            _sig(0.8,_B,'📗','Up5D','triangle-up',9,'#00E676','High',0.8,'5일연속상승','5일연속양봉'),
    'Down_3_Days':          _sig(0.5,_S,'📕','Dn3D','triangle-down',8,'#FF5252','Low',-0.5,'3일연속하락','3일연속음봉'),
    'Down_5_Days':          _sig(0.8,_S,'📕','Dn5D','triangle-down',9,'#FF1744','Low',-0.8,'5일연속하락','5일연속음봉'),

    # ═══ 갭 (4) ═══
    'Gap_Up':               _sig(1.0,_B,'⏫','GapUp','arrow-up',10,'#00E676','Low',-1.0,'갭 상승','시가>전일고가'),
    'Gap_Down':             _sig(1.0,_S,'⏬','GapDn','arrow-down',10,'#FF1744','High',1.0,'갭 하락','시가<전일저가'),
    'Gap_Up_Closed':        _sig(0.8,_S,'🔄','GapUp Fill','circle-open',8,'#FFA726','High',0.8,'갭업메움','상승갭메워짐'),
    'Gap_Down_Closed':      _sig(0.8,_B,'🔄','GapDn Fill','circle-open',8,'#4FC3F7','Low',-0.8,'갭다운메움','하락갭메워짐'),

    # ═══ 변동성 (4) ═══
    'NR7':                  _sig(0.3,_N,'🔲','NR7','square-open',7,'#B0BEC5','Low',-0.3,'NR7','7일중최소범위'),  # 🔧 방향→neutral
    'NR7_2':                _sig(0.8,_N,'🔳','NR7-2','square-open',8,'#90A4AE','Low',-0.5,'NR7-2','2일연속NR7'),  # 🔧 방향→neutral
    'Calm_After_Storm':     _sig(1.0,_N,'🌤️','CalmStorm','diamond-open',9,'#FFC107','Low',-0.8,'폭풍뒤고요','WideRange→NarrowRange'),  # 🔧 방향→neutral
    'Wide_Range_Bar':       _sig(0.5,_N,'📊','WideBar','square-open',7,'#FFAB40','Low',-0.4,'넓은범위봉','범위>ATR×2'),  # 🔧 방향→neutral

    # ═══ 52주 (2) ═══
    'New_52W_High':         _sig(1.5,_B,'🏔️','52W▲','star-triangle-up',12,'#FFD700','High',1.5,'52주신고가','52주최고가갱신'),
    'New_52W_Low':          _sig(1.5,_S,'🕳️','52W▼','star-triangle-down',12,'#B71C1C','Low',-1.5,'52주신저가','52주최저가갱신'),

    # ═══ Jeff Cooper (15) ═══
    'Pullback_123_Bull':    _sig(2.0,_B,'🎯','123PB▲','triangle-up',12,'#00E676','Low',-1.8,'1,2,3풀백매수','ADX>30+DI↑+3일저점↓'),
    'Pullback_123_Bear':    _sig(2.0,_S,'🎯','123PB▼','triangle-down',12,'#FF1744','High',1.8,'1,2,3풀백매도','ADX>30+DI↓+3일고점↑'),
    'Setup_180_Bull':       _sig(2.0,_B,'🔄','180▲','star-diamond',13,'#00E676','Low',-2.0,'180매수셋업','전일하위25%→당일상위25%+MA위'),
    'Setup_180_Bear':       _sig(2.0,_S,'🔄','180▼','star-diamond',13,'#FF1744','High',2.0,'180매도셋업','전일상위25%→당일하위25%+MA아래'),
    'Boomer_Buy':           _sig(2.0,_B,'💣','Boomer▲','star',12,'#00E676','Low',-1.8,'부머매수','ADX>30+DI↑+2일인사이드→돌파'),
    'Boomer_Sell':          _sig(2.0,_S,'💣','Boomer▼','star',12,'#FF1744','High',1.8,'부머매도','ADX>30+DI↓+2일인사이드→이탈'),
    'Expansion_BO':         _sig(2.5,_B,'🚀','XBO','star-diamond',14,'#FFD700','Low',-2.5,'확장돌파','2개월신고가+9일최대범위'),
    'Expansion_BD':         _sig(2.5,_S,'💨','XBD','star-diamond',14,'#FF0000','High',2.5,'확장붕괴','2개월신저가+9일최대범위'),
    'Gilligans_Buy':        _sig(2.0,_B,'🏝️','Gilligan▲','hexagon',12,'#00BCD4','Low',-2.0,'길리건매수','갭다운2개월신저가→반전'),
    'Gilligans_Sell':       _sig(2.0,_S,'🏝️','Gilligan▼','hexagon',12,'#FF5722','High',2.0,'길리건매도','갭업2개월신고가→반전'),
    'Lizard_Bull':          _sig(1.5,_B,'🦎','Lizard▲','triangle-up',10,'#00E676','Low',-1.5,'리자드매수','시가종가상위25%+10일신저가'),
    'Lizard_Bear':          _sig(1.5,_S,'🦎','Lizard▼','triangle-down',10,'#FF1744','High',1.5,'리자드매도','시가종가하위25%+10일신고가'),
    'NonADX_123_Bull':      _sig(1.8,_B,'📐','nADX123▲','triangle-up',11,'#69F0AE','Low',-1.5,'비ADX풀백매수','주가>50MA+3일저점↓'),
    'NonADX_123_Bear':      _sig(1.8,_S,'📐','nADX123▼','triangle-down',11,'#FF5252','High',1.5,'비ADX풀백매도','주가<50MA+3일고점↑'),
    'Pocket_Pivot':         _sig(1.5,_B,'🧲','PocketPvt','triangle-up',11,'#7C4DFF','Low',-1.5,'포켓피봇','양봉+거래량>10일하락거래량최대'),

    # ═══ Money Flow (6) ═══
    'MF_Cross_Bull':        _sig(1.5,_B,'💰','MF 0▲','triangle-up',11,'#00E676','Low',-1.2,'MF 강세전환','자금흐름 음→양'),
    'MF_Cross_Bear':        _sig(1.5,_S,'💸','MF 0▼','triangle-down',11,'#FF1744','High',1.2,'MF 약세전환','자금흐름 양→음'),
    'MF_Bull_Div':          _sig(1.8,_B,'💹','MF Bull Div','triangle-up',11,'#7C4DFF','Low',-1.5,'MF 상승 다이버전스','가격↓ vs MF↑'),
    'MF_Bear_Div':          _sig(1.8,_S,'💹','MF Bear Div','triangle-down',11,'#E040FB','High',1.5,'MF 하락 다이버전스','가격↑ vs MF↓'),
    'MF_Accel_Up':          _sig(1.0,_B,'📈','MF Accel▲','arrow-up',9,'#69F0AE','Low',-0.8,'MF 가속상승','5일+ MF 연속상승'),
    'MF_Accel_Dn':          _sig(1.0,_S,'📉','MF Accel▼','arrow-down',9,'#FF5252','High',0.8,'MF 가속하락','5일+ MF 연속하락'),

    # ═══ Ichimoku Cloud (4) ═══
    'Kumo_Breakout_Bull':   _sig(2.0,_B,'☁️','Kumo▲','triangle-up',13,'#00E676','Low',-2.0,'쿠모 상향돌파','종가>구름상단+전환>기준'),
    'Kumo_Breakout_Bear':   _sig(2.0,_S,'☁️','Kumo▼','triangle-down',13,'#FF1744','High',2.0,'쿠모 하향돌파','종가<구름하단+전환<기준'),
    'TK_Cross_Bull':        _sig(1.5,_B,'⛩️','TK Cross▲','triangle-up',10,'#69F0AE','Low',-1.2,'전환-기준 골든','전환선>기준선(구름위)'),
    'TK_Cross_Bear':        _sig(1.5,_S,'⛩️','TK Cross▼','triangle-down',10,'#FF5252','High',1.2,'전환-기준 데드','전환선<기준선(구름아래)'),

    # ═══ CMF (2) ═══
    'CMF_Bull':             _sig(1.2,_B,'🌀','CMF Bull','triangle-up',10,'#00BCD4','Low',-1.0,'CMF 강세','CMF>0.1+상승추세'),
    'CMF_Bear':             _sig(1.2,_S,'🌀','CMF Bear','triangle-down',10,'#FF5722','High',1.0,'CMF 약세','CMF<-0.1+하락추세'),

    # ═══ 🆕 선행(Anticipation) 시그널 (6) ═══
    'Setup_Squeeze_Bull':   _sig(1.0,_B,'⏳','SqSetup▲','hourglass',10,'#80DEEA','Low',-0.8,'스퀴즈셋업▲','BB축소+모멘텀상승전환임박'),
    'Setup_Squeeze_Bear':   _sig(1.0,_S,'⏳','SqSetup▼','hourglass',10,'#FFAB91','High',0.8,'스퀴즈셋업▼','BB축소+모멘텀하락전환임박'),
    'Momentum_Accel_Buy':   _sig(1.5,_B,'⚡','Mom Accel▲','arrow-up',11,'#76FF03','Low',-1.2,'모멘텀가속▲','RSI+WT+MACD 동시가속상승'),
    'Momentum_Accel_Sell':  _sig(1.5,_S,'⚡','Mom Accel▼','arrow-down',11,'#FF3D00','High',1.2,'모멘텀가속▼','RSI+WT+MACD 동시가속하락'),
    'Volume_Dry_Up':        _sig(0.5,_N,'🏜️','VolDryUp','square-open',8,'#FFE082','Low',-0.3,'거래량고갈','5일연속평균이하→돌파임박'),
    'WT_Convergence_Bull':  _sig(1.2,_B,'🔀','WT Conv▲','triangle-up',10,'#B2FF59','Low',-1.0,'WT수렴매수임박','WT1→WT2빠른수렴+과매도'),
    'WT_Convergence_Bear':  _sig(1.2,_S,'🔀','WT Conv▼','triangle-down',10,'#FF8A80','High',1.0,'WT수렴매도임박','WT1→WT2빠른수렴+과매수'),
}

COMPOSITE_SIGNALS = {
    'Ultra_Buy':  _sig(0,_B,'⚡','ULTRA BUY','star',20,'#FFD700','Low',-3.5,'울트라 매수','Confluence≥6.5'),
    'Strong_Buy': _sig(0,_B,'🔱','STRONG BUY','star',16,'#00E676','Low',-3.2,'스트롱 매수','Confluence 3.5~6.5'),
    'Ultra_Sell': _sig(0,_S,'🚨','ULTRA SELL','star',20,'#FF0000','High',3.5,'울트라 매도','Confluence≤-6.5'),
    'Strong_Sell':_sig(0,_S,'⚠️','STRONG SELL','star',16,'#FF1744','High',3.2,'스트롱 매도','Confluence -6.5~-3.5'),
}
ALL_CHART_SIGNALS = {**SIGNAL_REGISTRY, **COMPOSITE_SIGNALS}


# ──────────────────────────────────────────
# 쿨다운 맵 (🧹 선행 시그널 + BB 분리 반영)
# ──────────────────────────────────────────
COOLDOWN_MAP = {
    'Squeeze_Fire_Buy':5,'Squeeze_Fire_Sell':5,
    'Bullish_Engulfing':5,'Bearish_Engulfing':5,
    'ADX_Momentum_Buy':10,'ADX_Momentum_Sell':10,
    'EMA_Pullback_Buy':7,'EMA_Pullback_Sell':7,
    'Momentum_Ignition_Buy':10,'Momentum_Ignition_Sell':10,
    'Parabolic_Top_Sell':5,'Parabolic_Bottom_Buy':5,
    'VWAP_Bounce_Buy':7,'VWAP_Reject_Sell':7,
    'MACD_Cross_Buy':12,'MACD_Cross_Sell':12,
    'StochRSI_Cross_Buy':7,'StochRSI_Cross_Sell':7,
    'RSI_Bull_Divergence':10,'RSI_Bear_Divergence':10,
    'Hammer':5,'Shooting_Star':5,'Morning_Star':7,'Evening_Star':7,
    'Doji_Bullish':5,'Doji_Bearish':5,
    'Outside_Bullish':7,'Outside_Bearish':7,
    'Cross_Above_20MA':5,'Fell_Below_20MA':5,
    'Cross_Above_50MA':10,'Fell_Below_50MA':10,
    'Cross_Above_200MA':15,'Fell_Below_200MA':15,
    'BB_Upper_Break':5,'BB_Lower_Bounce':5,'BB_Lower_Break':5,   # 🔧 분리 반영
    'BB_Squeeze_End_Bull':7,'BB_Squeeze_End_Bear':7,
    'MACD_Zero_Cross_Buy':12,'MACD_Zero_Cross_Sell':12,
    'Gap_Up':3,'Gap_Down':3,'Gap_Up_Closed':5,'Gap_Down_Closed':5,
    'New_52W_High':10,'New_52W_Low':10,
    'Calm_After_Storm':5,
    'Pullback_123_Bull':7,'Pullback_123_Bear':7,
    'Setup_180_Bull':7,'Setup_180_Bear':7,
    'Boomer_Buy':10,'Boomer_Sell':10,
    'Expansion_BO':10,'Expansion_BD':10,
    'Gilligans_Buy':10,'Gilligans_Sell':10,
    'Lizard_Bull':5,'Lizard_Bear':5,
    'NonADX_123_Bull':7,'NonADX_123_Bear':7,
    'Pocket_Pivot':10,
    'MF_Cross_Bull':10,'MF_Cross_Bear':10,
    'MF_Bull_Div':10,'MF_Bear_Div':10,
    'MF_Accel_Up':5,'MF_Accel_Dn':5,
    'Kumo_Breakout_Bull':10,'Kumo_Breakout_Bear':10,
    'TK_Cross_Bull':7,'TK_Cross_Bear':7,
    'CMF_Bull':10,'CMF_Bear':10,
    # 🆕 선행 시그널 쿨다운
    'Setup_Squeeze_Bull':3,'Setup_Squeeze_Bear':3,  # 짧은 쿨다운 (셋업은 반복 허용)
    'Momentum_Accel_Buy':5,'Momentum_Accel_Sell':5,
    'Volume_Dry_Up':3,
    'WT_Convergence_Bull':5,'WT_Convergence_Bear':5,
}


# ──────────────────────────────────────────
# 시그널 계층 (🧹 선행 시그널 추가)
# ──────────────────────────────────────────
SIGNAL_HIERARCHY = {
    'candle_bull': ['Morning_Star','Bullish_Engulfing','Hammer','Doji_Bullish'],
    'candle_bear': ['Evening_Star','Bearish_Engulfing','Shooting_Star','Doji_Bearish'],
    'ma_cross_bull': ['Cross_Above_200MA','Cross_Above_50MA','Cross_Above_20MA'],
    'ma_cross_bear': ['Fell_Below_200MA','Fell_Below_50MA','Fell_Below_20MA'],
    'cooper_bull': ['Expansion_BO','Pullback_123_Bull','Setup_180_Bull','Boomer_Buy',
                    'Gilligans_Buy','Lizard_Bull','NonADX_123_Bull'],
    'cooper_bear': ['Expansion_BD','Pullback_123_Bear','Setup_180_Bear','Boomer_Sell',
                    'Gilligans_Sell','Lizard_Bear','NonADX_123_Bear'],
    'ichimoku_bull': ['Kumo_Breakout_Bull','TK_Cross_Bull'],
    'ichimoku_bear': ['Kumo_Breakout_Bear','TK_Cross_Bear'],
    # 🆕 선행 시그널 계층: 실제 시그널이 발생하면 셋업은 자동 비활성화
    'anticipation_bull': ['Momentum_Accel_Buy','WT_Convergence_Bull','Setup_Squeeze_Bull'],
    'anticipation_bear': ['Momentum_Accel_Sell','WT_Convergence_Bear','Setup_Squeeze_Bear'],
}


# ──────────────────────────────────────────
# 판단 마커 / 설정 (변경 없음)
# ──────────────────────────────────────────
JUDGMENT_MARKERS = {
    'STRONG_BUY': {'symbol':'star','size':18,'color':'#00E676','label':'🟢🟢🟢 STRONG BUY','short':'S.BUY','line_color':'#FFFFFF','line_width':2,'base':'Low','atr_mult':-3.5},
    'BUY':        {'symbol':'triangle-up','size':14,'color':'#00E676','label':'🟢🟢 BUY','short':'BUY','line_color':'#FFFFFF','line_width':1.5,'base':'Low','atr_mult':-2.5},
    'WATCH_BUY':  {'symbol':'circle','size':9,'color':'#69F0AE','label':'🟡🟢 WATCH BUY','short':'W.BUY','line_color':'#69F0AE','line_width':1,'base':'Low','atr_mult':-2.0},
    'STRONG_SELL':{'symbol':'star','size':18,'color':'#FF1744','label':'🔴🔴🔴 STRONG SELL','short':'S.SELL','line_color':'#FFFFFF','line_width':2,'base':'High','atr_mult':3.5},
    'SELL':       {'symbol':'triangle-down','size':14,'color':'#FF1744','label':'🔴🔴 SELL','short':'SELL','line_color':'#FFFFFF','line_width':1.5,'base':'High','atr_mult':2.5},
    'WATCH_SELL': {'symbol':'circle','size':9,'color':'#FF5252','label':'🟡🔴 WATCH SELL','short':'W.SELL','line_color':'#FF5252','line_width':1,'base':'High','atr_mult':2.0},
    'MIXED':      {'symbol':'diamond','size':11,'color':'#FF9800','label':'🟠 MIXED','short':'MIXED','line_color':'#FF9800','line_width':1,'base':'High','atr_mult':2.0},
}
JUDGMENT_CONFIG = {
    'STRONG_BUY':  ('🟢🟢🟢 STRONG BUY','#00E676','rgba(0,230,118,.12)'),
    'BUY':         ('🟢🟢 BUY','#00E676','rgba(0,230,118,.08)'),
    'WATCH_BUY':   ('🟡🟢 WATCH BUY','#FFC107','rgba(255,193,7,.08)'),
    'NEUTRAL':     ('⚪ NEUTRAL','#888888','rgba(128,128,128,.05)'),
    'MIXED':       ('🟠 MIXED','#FF9800','rgba(255,152,0,.08)'),
    'WATCH_SELL':  ('🟡🔴 WATCH SELL','#FFC107','rgba(255,193,7,.08)'),
    'SELL':        ('🔴🔴 SELL','#FF1744','rgba(255,23,68,.08)'),
    'STRONG_SELL': ('🔴🔴🔴 STRONG SELL','#FF1744','rgba(255,23,68,.12)'),
}


# ══════════════════════════════════════════════════════════════
#  CipherX V12.0 — Custom Scanner Module
#  승률 높은 시그널 콤보 20종 + 차트 마킹 + 멀티 티커 스캐너
# ══════════════════════════════════════════════════════════════


# ──────────────────────────────────────────
# 📋 스캐너 콤보 정의
# ──────────────────────────────────────────
SCANNER_COMBOS = {
    # ═══════════ BUY 콤보 10종 ═══════════
    'SC_Oversold_Bounce': {
        'name': '🟢 Oversold Bounce',
        'kor': '과매도 반등',
        'dir': 'buy',
        'tier': 1,
        'icon': '🏓',
        'color': '#00E676',
        'desc': 'StochRSI 과매도 + 강세 캔들 + 20MA 돌파',
        'category': '반전',
    },
    'SC_Breakout_Momentum': {
        'name': '🟢 Breakout Momentum',
        'kor': '돌파 모멘텀',
        'dir': 'buy',
        'tier': 1,
        'icon': '🚀',
        'color': '#00E676',
        'desc': '확장 돌파 + 거래량 급증 + 52주 신고가',
        'category': '돌파',
    },
    'SC_Pullback_Buy_Zone': {
        'name': '🟢 Pullback Buy Zone',
        'kor': '눌림목 매수',
        'dir': 'buy',
        'tier': 2,
        'icon': '🎯',
        'color': '#69F0AE',
        'desc': '상승추세 + 20MA 눌림 + 해머/반등 캔들',
        'category': '추세 지속',
    },
    'SC_Triple_Oversold': {
        'name': '🟢 Triple Oversold Reversal',
        'kor': '삼중 과매도 반전',
        'dir': 'buy',
        'tier': 1,
        'icon': '💎',
        'color': '#00E676',
        'desc': 'WT+RSI+캔들 동시 과매도 극단에서 반전',
        'category': '반전',
    },
    'SC_Squeeze_Fire_Bull': {
        'name': '🟢 Squeeze Fire Bull',
        'kor': '스퀴즈 돌파 매수',
        'dir': 'buy',
        'tier': 2,
        'icon': '💥',
        'color': '#00FFFF',
        'desc': 'BB 스퀴즈 해소 + 거래량 + MACD 교차',
        'category': '돌파',
    },
    'SC_Trend_Continuation': {
        'name': '🟢 Trend Continuation',
        'kor': '추세 지속 매수',
        'dir': 'buy',
        'tier': 2,
        'icon': '📐',
        'color': '#69F0AE',
        'desc': 'ADX 강세 + 123 풀백 + 자금흐름 양호',
        'category': '추세 지속',
    },
    'SC_Volume_Climax_Rev': {
        'name': '🟢 Volume Climax Reversal',
        'kor': '거래량 클라이맥스 반전',
        'dir': 'buy',
        'tier': 1,
        'icon': '🌊',
        'color': '#00BCD4',
        'desc': '거래량 폭발 + WT 과매도 + 다이버전스',
        'category': '반전',
    },
    'SC_Ichimoku_Breakout': {
        'name': '🟢 Ichimoku Breakout',
        'kor': '쿠모 돌파 매수',
        'dir': 'buy',
        'tier': 2,
        'icon': '☁️',
        'color': '#00E5FF',
        'desc': '쿠모 상향돌파 + CMF 양호 + 거래량',
        'category': '돌파',
    },
    'SC_Smart_Money_Accum': {
        'name': '🟢 Smart Money Accumulation',
        'kor': '스마트머니 매집',
        'dir': 'buy',
        'tier': 2,
        'icon': '🏦',
        'color': '#7C4DFF',
        'desc': 'MF 전환 + CMF 양수 + BB 하단 반등',
        'category': '매집',
    },
    'SC_Momentum_Ignition_Buy': {
        'name': '🟢 Momentum Ignition',
        'kor': '모멘텀 점화 매수',
        'dir': 'buy',
        'tier': 1,
        'icon': '🔥',
        'color': '#FF6D00',
        'desc': '모멘텀 점화 + ST 강세전환 + ADX 상승',
        'category': '돌파',
    },

    # ═══════════ SELL 콤보 10종 ═══════════
    'SC_Overbought_Exhaust': {
        'name': '🔴 Overbought Exhaustion',
        'kor': '과매수 소진',
        'dir': 'sell',
        'tier': 1,
        'icon': '🌡️',
        'color': '#FF1744',
        'desc': 'StochRSI 과매수 + 약세 캔들 + 20MA 이탈',
        'category': '반전',
    },
    'SC_Breakdown_Momentum': {
        'name': '🔴 Breakdown Momentum',
        'kor': '붕괴 모멘텀',
        'dir': 'sell',
        'tier': 1,
        'icon': '💨',
        'color': '#FF1744',
        'desc': '확장 붕괴 + 거래량 급증 + 52주 신저가',
        'category': '붕괴',
    },
    'SC_Rally_Failure': {
        'name': '🔴 Rally Failure',
        'kor': '반등 실패',
        'dir': 'sell',
        'tier': 2,
        'icon': '🎯',
        'color': '#FF5252',
        'desc': '하락추세 + 20MA 저항 + 슈팅스타',
        'category': '추세 지속',
    },
    'SC_Triple_Overbought': {
        'name': '🔴 Triple Overbought Reversal',
        'kor': '삼중 과매수 반전',
        'dir': 'sell',
        'tier': 1,
        'icon': '💀',
        'color': '#FF1744',
        'desc': 'WT+RSI+캔들 동시 과매수 극단에서 반전',
        'category': '반전',
    },
    'SC_Squeeze_Fire_Bear': {
        'name': '🔴 Squeeze Fire Bear',
        'kor': '스퀴즈 돌파 매도',
        'dir': 'sell',
        'tier': 2,
        'icon': '🧨',
        'color': '#FF6600',
        'desc': 'BB 스퀴즈 해소 하방 + 거래량 + MACD 교차',
        'category': '붕괴',
    },
    'SC_Trend_Breakdown': {
        'name': '🔴 Trend Breakdown',
        'kor': '추세 붕괴 매도',
        'dir': 'sell',
        'tier': 2,
        'icon': '📐',
        'color': '#FF5252',
        'desc': 'ADX 약세 + 123 풀백 매도 + 자금유출',
        'category': '추세 지속',
    },
    'SC_Volume_Climax_Sell': {
        'name': '🔴 Volume Climax Sell',
        'kor': '거래량 클라이맥스 매도',
        'dir': 'sell',
        'tier': 1,
        'icon': '🌋',
        'color': '#D50000',
        'desc': '거래량 폭발 매도 + WT 과매수 + 다이버전스',
        'category': '반전',
    },
    'SC_Ichimoku_Breakdown': {
        'name': '🔴 Ichimoku Breakdown',
        'kor': '쿠모 하향 매도',
        'dir': 'sell',
        'tier': 2,
        'icon': '☁️',
        'color': '#FF6E40',
        'desc': '쿠모 하향돌파 + CMF 약세 + 거래량',
        'category': '붕괴',
    },
    'SC_Distribution': {
        'name': '🔴 Distribution Signal',
        'kor': '분배(투매) 신호',
        'dir': 'sell',
        'tier': 2,
        'icon': '🏛️',
        'color': '#E040FB',
        'desc': 'MF 전환 + CMF 음수 + WT 하락',
        'category': '분배',
    },
    'SC_Parabolic_Exhaust': {
        'name': '🔴 Parabolic Exhaustion',
        'kor': '포물선 소진',
        'dir': 'sell',
        'tier': 1,
        'icon': '🌡️',
        'color': '#FF0000',
        'desc': '포물선 천장 + 거래량 폭발 + RSI 극과매수',
        'category': '반전',
    },
}


# ──────────────────────────────────────────
# 📋 스캐너 콤보 탐지 함수
# ──────────────────────────────────────────
def detect_scanner_combos(df: pd.DataFrame) -> pd.DataFrame:
    """
    고승률 시그널 콤보 20종 탐지
    기존 시그널 컬럼이 이미 계산된 df를 입력받음
    """
    idx = df.index
    C, O, H, L, V = df['Close'], df['Open'], df['High'], df['Low'], df['Volume']
    F = lambda col: df.get(col, pd.Series(False, index=idx)).fillna(False)

    # ── 공통 조건 ──
    vol_ratio = V / (V.rolling(50, min_periods=10).mean() + 1e-10)
    vol_15x = vol_ratio >= 1.5
    vol_2x = vol_ratio >= 2.0
    vol_3x = vol_ratio >= 3.0

    above_50ma = C > df['MA50']
    below_50ma = C < df['MA50']
    ma50_rising = df['MA50'] > df['MA50'].shift(5)
    ma50_falling = df['MA50'] < df['MA50'].shift(5)

    candle_bull = F('Bullish_Engulfing') | F('Hammer') | F('Morning_Star') | F('Doji_Bullish')
    candle_bear = F('Bearish_Engulfing') | F('Shooting_Star') | F('Evening_Star') | F('Doji_Bearish')

    mf_rising = df.get('MF_Rising', pd.Series(False, index=idx)).fillna(False)
    mf_falling = df.get('MF_Falling', pd.Series(False, index=idx)).fillna(False)
    cmf = df.get('CMF', pd.Series(0, index=idx))
    rmfi = df['RSI_MFI']

    # ── 최근 발생 체크 (3봉 이내) ──
    def _rec(col, lb=3):
        s = F(col)
        return s.astype(float).rolling(lb + 1, min_periods=1).max().fillna(0).astype(bool)

    # ═══════════ BUY 콤보 ═══════════

    # B1: Oversold Bounce — StochK<20 + 강세캔들 + 20MA 돌파
    stoch_oversold = (df['StochK'] < 20) & (df['StochD'] < 20)
    df['SC_Oversold_Bounce'] = (
        stoch_oversold &
        (candle_bull | _rec('StochRSI_Cross_Buy')) &
        (_rec('Cross_Above_20MA') | (C > df['MA20'])) &
        vol_15x
    )

    # B2: Breakout Momentum — 확장 돌파 + 거래량 + 52주 신고가
    df['SC_Breakout_Momentum'] = (
        (F('Expansion_BO') | F('New_52W_High')) &
        vol_2x &
        (F('New_52W_High') | (H >= H.rolling(60, min_periods=40).max())) &
        (df['ADX'] > 20)
    )

    # B3: Pullback Buy Zone — 상승추세 + 20MA 눌림 + 해머
    pullback_to_20 = (C <= df['MA20'] * 1.02) & (C >= df['MA20'] * 0.97)
    df['SC_Pullback_Buy_Zone'] = (
        above_50ma & ma50_rising &
        (pullback_to_20 | _rec('Fell_Below_20MA') | F('EMA_Pullback_Buy')) &
        (F('Hammer') | F('Doji_Bullish') | F('Outside_Bullish') |
         (C > O) & (df['WT1'] > df['WT1'].shift(1)))
    )

    # B4: Triple Oversold Reversal — WT+RSI+캔들 동시 극단
    triple_oversold = (
        ((df['WT1'] < OS1).astype(int) +
         (df['RSI'] < 35).astype(int) +
         (df['MFI'] < 35).astype(int) +
         (df['StochK'] < 20).astype(int)) >= 3
    )
    strong_bull_signal = (
        F('Gold_Dot') | F('Green_Dot_T1') | F('Morning_Star') |
        F('Bullish_Engulfing') | F('Bull_Divergence') |
        F('Parabolic_Bottom_Buy')
    )
    df['SC_Triple_Oversold'] = triple_oversold & (strong_bull_signal | candle_bull)

    # B5: Squeeze Fire Bull — BB 스퀴즈 해소 + 거래량 + MACD
    df['SC_Squeeze_Fire_Bull'] = (
        (F('BB_Squeeze_End_Bull') | F('Squeeze_Fire_Buy')) &
        vol_15x &
        (_rec('MACD_Cross_Buy') | _rec('MACD_Zero_Cross_Buy') |
         (df['MACD_Hist'] > 0) & (df['MACD_Hist'] > df['MACD_Hist'].shift(1)))
    )

    # B6: Trend Continuation — ADX 강세 + 123 풀백
    df['SC_Trend_Continuation'] = (
        (df['ADX'] > 25) & (df['Plus_DI'] > df['Minus_DI']) &
        (F('Pullback_123_Bull') | F('NonADX_123_Bull') | F('Boomer_Buy')) &
        (mf_rising | (rmfi > rmfi.shift(3)))
    )

    # B7: Volume Climax Reversal — 거래량 폭발 + WT 과매도 + 다이버전스
    df['SC_Volume_Climax_Rev'] = (
        F('Volume_Climax_Buy') &
        (df['WT1'] < -30) &
        (_rec('Bull_Divergence') | _rec('RSI_Bull_Divergence') |
         _rec('OBV_Div_Buy') | _rec('MF_Bull_Div') | candle_bull)
    )

    # B8: Ichimoku Breakout — 쿠모 돌파 + CMF + 거래량
    kumo_top = pd.concat([df.get('Ichimoku_SenkouA', pd.Series(0, index=idx)),
                           df.get('Ichimoku_SenkouB', pd.Series(0, index=idx))], axis=1).max(axis=1)
    df['SC_Ichimoku_Breakout'] = (
        (F('Kumo_Breakout_Bull') | F('TK_Cross_Bull')) &
        (cmf > 0.05) &
        vol_15x &
        (C > kumo_top)
    )

    # B9: Smart Money Accumulation — MF전환 + CMF + BB하단반등
    df['SC_Smart_Money_Accum'] = (
        (F('MF_Cross_Bull') | (_rec('MF_Bull_Div'))) &
        (cmf > 0) &
        (F('BB_Lower_Bounce') | (df['Percent_B'] < 0.2)) &
        (df['WT1'] > df['WT1'].shift(1))  # WT 반등 중
    )

    # B10: Momentum Ignition Buy — 모멘텀 점화 + ST + ADX
    df['SC_Momentum_Ignition_Buy'] = (
        (F('Momentum_Ignition_Buy') | (F('Expansion_BO') & vol_2x)) &
        (F('SuperTrend_Buy') | (df['ST_Direction'] == 1)) &
        (df['ADX'] > 20)
    )

    # ═══════════ SELL 콤보 ═══════════

    # S1: Overbought Exhaustion — StochK>80 + 약세캔들 + 20MA 이탈
    stoch_overbought = (df['StochK'] > 80) & (df['StochD'] > 80)
    df['SC_Overbought_Exhaust'] = (
        stoch_overbought &
        (candle_bear | _rec('StochRSI_Cross_Sell')) &
        (_rec('Fell_Below_20MA') | (C < df['MA20'])) &
        vol_15x
    )

    # S2: Breakdown Momentum — 확장 붕괴 + 거래량 + 52주 신저가
    df['SC_Breakdown_Momentum'] = (
        (F('Expansion_BD') | F('New_52W_Low')) &
        vol_2x &
        (F('New_52W_Low') | (L <= L.rolling(60, min_periods=40).min())) &
        (df['ADX'] > 20)
    )

    # S3: Rally Failure — 하락추세 + 20MA 저항 + 슈팅스타
    resistance_at_20 = (C <= df['MA20'] * 1.02) & (C >= df['MA20'] * 0.97)
    df['SC_Rally_Failure'] = (
        below_50ma & ma50_falling &
        (resistance_at_20 | _rec('Fell_Below_20MA')) &
        (F('Shooting_Star') | F('Doji_Bearish') | F('Outside_Bearish') |
         F('EMA_Pullback_Sell'))
    )

    # S4: Triple Overbought Reversal
    triple_overbought = (
        ((df['WT1'] > OB1).astype(int) +
         (df['RSI'] > 65).astype(int) +
         (df['MFI'] > 65).astype(int) +
         (df['StochK'] > 80).astype(int)) >= 3
    )
    strong_bear_signal = (
        F('Blood_Diamond') | F('Red_Dot_T1') | F('Evening_Star') |
        F('Bearish_Engulfing') | F('Bear_Divergence') |
        F('Parabolic_Top_Sell')
    )
    df['SC_Triple_Overbought'] = triple_overbought & (strong_bear_signal | candle_bear)

    # S5: Squeeze Fire Bear
    df['SC_Squeeze_Fire_Bear'] = (
        (F('BB_Squeeze_End_Bear') | F('Squeeze_Fire_Sell')) &
        vol_15x &
        (_rec('MACD_Cross_Sell') | _rec('MACD_Zero_Cross_Sell') |
         (df['MACD_Hist'] < 0) & (df['MACD_Hist'] < df['MACD_Hist'].shift(1)))
    )

    # S6: Trend Breakdown
    df['SC_Trend_Breakdown'] = (
        (df['ADX'] > 25) & (df['Minus_DI'] > df['Plus_DI']) &
        (F('Pullback_123_Bear') | F('NonADX_123_Bear') | F('Boomer_Sell')) &
        (mf_falling | (rmfi < rmfi.shift(3)))
    )

    # S7: Volume Climax Sell
    df['SC_Volume_Climax_Sell'] = (
        F('Volume_Climax_Sell') &
        (df['WT1'] > 30) &
        (_rec('Bear_Divergence') | _rec('RSI_Bear_Divergence') |
         _rec('OBV_Div_Sell') | _rec('MF_Bear_Div') | candle_bear)
    )

    # S8: Ichimoku Breakdown
    kumo_bot = pd.concat([df.get('Ichimoku_SenkouA', pd.Series(0, index=idx)),
                           df.get('Ichimoku_SenkouB', pd.Series(0, index=idx))], axis=1).min(axis=1)
    df['SC_Ichimoku_Breakdown'] = (
        (F('Kumo_Breakout_Bear') | F('TK_Cross_Bear')) &
        (cmf < -0.05) &
        vol_15x &
        (C < kumo_bot)
    )

    # S9: Distribution Signal
    df['SC_Distribution'] = (
        (F('MF_Cross_Bear') | _rec('MF_Bear_Div')) &
        (cmf < 0) &
        (df['WT1'] < df['WT1'].shift(1)) &
        (df['WT1'] > 0)  # 아직 양수 영역 (하락 시작)
    )

    # S10: Parabolic Exhaustion
    df['SC_Parabolic_Exhaust'] = (
        (F('Parabolic_Top_Sell') | ((df['WT1'] > 80) & (df['WT1'] < df['WT1'].shift(1)))) &
        vol_2x &
        (df['RSI'] > 65)
    )

    # ── 쿨다운 적용 ──
    for combo_name in SCANNER_COMBOS:
        if combo_name in df.columns:
            df[combo_name] = _cooldown(df[combo_name], bars=5)

    return df


# ──────────────────────────────────────────
# 📊 차트에 스캐너 콤보 마킹
# ──────────────────────────────────────────
def add_scanner_markers_to_chart(fig, dc, row=1):
    """
    기존 차트에 스캐너 콤보 마커를 추가합니다.
    판단 마커와는 별도로, 특별한 모양과 색상으로 표시됩니다.
    """
    for combo_name, combo_cfg in SCANNER_COMBOS.items():
        if combo_name not in dc.columns:
            continue
        mask = dc[combo_name].fillna(False)
        if not mask.any():
            continue

        sig_rows = dc[mask]
        is_buy = combo_cfg['dir'] == 'buy'

        # 매수: 캔들 아래, 매도: 캔들 위
        if is_buy:
            y_vals = sig_rows['Low'] - sig_rows['ATR'] * 0.5
        else:
            y_vals = sig_rows['High'] + sig_rows['ATR'] * 0.5

        # 마커 스타일: Tier 1 = 크고 별 모양, Tier 2 = 중간 다이아몬드
        tier = combo_cfg.get('tier', 2)
        if tier == 1:
            symbol = 'star-diamond'
            size = 14
            line_width = 2
        else:
            symbol = 'diamond'
            size = 11
            line_width = 1.5

        # 호버 텍스트
        hover_texts = []
        for idx_v in sig_rows.index:
            date_str = idx_v.strftime('%Y-%m-%d')
            hover_texts.append(
                f"<b>{combo_cfg['icon']} {combo_cfg['name']}</b><br>"
                f"<span style='color:#94A3B8'>{combo_cfg['desc']}</span><br>"
                f"<span style='color:#CBD5E1'>{date_str}</span><br>"
                f"<span style='color:#A5B4FC'>카테고리: {combo_cfg['category']}</span>"
            )

        fig.add_trace(go.Scatter(
            x=sig_rows.index,
            y=y_vals,
            mode='markers',
            marker=dict(
                symbol=symbol,
                size=size,
                color=combo_cfg['color'],
                line=dict(width=line_width, color='#FFFFFF'),
                opacity=0.9,
            ),
            name=f"SC: {combo_cfg['kor']}",
            text=hover_texts,
            hovertemplate="%{text}<extra></extra>",
            hoverlabel=dict(
                bgcolor='rgba(14,17,23,0.97)',
                bordercolor=combo_cfg['color'],
                font=dict(size=11, family='Pretendard', color='#FAFAFA'),
                align='left',
            ),
            legendgroup='scanner',
            legendgrouptitle_text='🔍 Scanner Combos',
        ), row=row, col=1)


# ──────────────────────────────────────────
# 🔍 멀티 티커 스캐너
# ──────────────────────────────────────────
@st.cache_data(ttl=600, show_spinner=False)
def scan_ticker(ticker: str, _ts=None) -> Optional[Dict]:
    """단일 티커 스캔 결과 반환"""
    try:
        df = compute_and_cache(ticker, _ts)
        if df is None or len(df) < 50:
            return None

        df = detect_scanner_combos(df)
        lat = df.iloc[-1]

        # 최근 5일 내 활성 콤보 수집
        active_combos = []
        for combo_name, combo_cfg in SCANNER_COMBOS.items():
            if combo_name not in df.columns:
                continue
            # 최근 53봉 체크
            recent = df[combo_name].tail(5)
            if recent.any():
                # 가장 최근 발생일
                last_date = recent[recent].index[-1]
                days_ago = (df.index[-1] - last_date).days
                active_combos.append({
                    'name': combo_cfg['name'],
                    'kor': combo_cfg['kor'],
                    'dir': combo_cfg['dir'],
                    'tier': combo_cfg['tier'],
                    'icon': combo_cfg['icon'],
                    'color': combo_cfg['color'],
                    'desc': combo_cfg['desc'],
                    'category': combo_cfg['category'],
                    'days_ago': days_ago,
                    'date': last_date.strftime('%m/%d'),
                })

        if not active_combos:
            return None

        # 기본 메타 수집
        jd = get_judgment_detail(lat) if 'Trade_Judgment' in df.columns else {}

        return {
            'ticker': ticker.upper(),
            'price': float(lat['Close']),
            'change_pct': float((lat['Close'] - df.iloc[-2]['Close']) / df.iloc[-2]['Close'] * 100) if len(df) >= 2 else 0,
            'volume_ratio': float(lat['Volume'] / (df['Volume'].rolling(50, min_periods=10).mean().iloc[-1] + 1e-10)),
            'judgment': jd.get('judgment', 'N/A'),
            'confidence': jd.get('confidence', 0),
            'buy_score': jd.get('buy_total', 0),
            'sell_score': jd.get('sell_total', 0),
            'active_combos': active_combos,
            'buy_combos': [c for c in active_combos if c['dir'] == 'buy'],
            'sell_combos': [c for c in active_combos if c['dir'] == 'sell'],
            'wt1': float(lat.get('WT1', 0)),
            'rsi': float(lat.get('RSI', 50)),
            'adx': float(lat.get('ADX', 0)),
        }
    except Exception:
        return None


def scan_multiple_tickers(tickers: List[str], progress_callback=None) -> List[Dict]:
    """여러 티커를 스캔하여 활성 콤보가 있는 결과만 반환"""
    results = []
    total = len(tickers)
    for i, ticker in enumerate(tickers):
        if progress_callback:
            progress_callback(i / total, f"🔍 {ticker} 스캔 중... ({i+1}/{total})")
        result = scan_ticker(ticker)
        if result:
            results.append(result)

    # 콤보 수 + Tier 1 우선으로 정렬
    results.sort(key=lambda x: (
        -sum(1 for c in x['active_combos'] if c['tier'] == 1),
        -len(x['active_combos']),
    ))
    return results


# ──────────────────────────────────────────
# 🖥️ 스캐너 UI
# ──────────────────────────────────────────
# 기본 워치리스트 (인기 종목)
DEFAULT_WATCHLIST = {
    '🔥 인기 대형주': ['NVDA', 'TSLA', 'AAPL', 'MSFT', 'AMZN', 'GOOG', 'META', 'AMD', 'NFLX', 'AVGO'],
    '📊 ETF': ['QQQ', 'SPY', 'IWM', 'ARKK', 'SOXX', 'XLF', 'XLE', 'XLV', 'XLK', 'TQQQ'],
    '🚀 성장주': ['PLTR', 'SNOW', 'CRWD', 'DDOG', 'NET', 'SHOP', 'SQ', 'COIN', 'MARA', 'RIOT'],
    '💊 바이오/헬스': ['MRNA', 'BNTX', 'ISRG', 'DXCM', 'VEEV', 'ZTS', 'REGN', 'VRTX', 'ILMN', 'BIIB'],
}


def render_scanner_page():
    """스캐너 전용 페이지/탭 렌더"""
    st.markdown("## 🔍 CipherX Custom Scanner")
    st.markdown("""<p style='color:#94A3B8;font-size:.9rem'>
        검증된 고승률 시그널 콤보 20종을 멀티 티커에 실시간 적용합니다.
        <b>Tier 1</b>(⭐⭐⭐⭐⭐) 콤보가 최우선으로 표시됩니다.</p>""",
        unsafe_allow_html=True)

    # ── 워치리스트 선택 ──
    st.markdown("#### 📋 워치리스트 선택")
    wl_tabs = st.tabs(list(DEFAULT_WATCHLIST.keys()) + ['✏️ 커스텀'])

    selected_tickers = []
    for i, (wl_name, tickers) in enumerate(DEFAULT_WATCHLIST.items()):
        with wl_tabs[i]:
            cols = st.columns(5)
            for j, t in enumerate(tickers):
                with cols[j % 5]:
                    if st.checkbox(t, value=True, key=f"wl_{wl_name}_{t}"):
                        if t not in selected_tickers:
                            selected_tickers.append(t)

    with wl_tabs[-1]:
        custom_input = st.text_input(
            "티커 입력 (쉼표 구분)",
            placeholder="NVDA, TSLA, AAPL, ...",
            key="custom_wl"
        )
        if custom_input:
            for t in custom_input.split(','):
                t = t.strip().upper()
                if t and t not in selected_tickers:
                    selected_tickers.append(t)

    st.markdown(f"**선택된 종목: {len(selected_tickers)}개**")

    # ── 필터 옵션 ──
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    with filter_col1:
        dir_filter = st.selectbox("방향 필터", ['전체', '매수만', '매도만'], key="sc_dir")
    with filter_col2:
        tier_filter = st.selectbox("등급 필터", ['전체', 'Tier 1만', 'Tier 2만'], key="sc_tier")
    with filter_col3:
        cat_filter = st.selectbox("카테고리", ['전체', '반전', '돌파', '추세 지속', '매집/분배'], key="sc_cat")

    # ── 스캔 실행 ──
    if st.button("🚀 스캔 시작", type="primary", use_container_width=True):
        if not selected_tickers:
            st.warning("종목을 선택해주세요.")
            return

        pb = st.progress(0, text="스캔 준비 중...")
        results = scan_multiple_tickers(
            selected_tickers,
            progress_callback=lambda p, t: pb.progress(p, text=t)
        )
        pb.progress(1.0, text=f"✅ {len(results)}개 종목에서 콤보 발견!")
        time.sleep(0.5)
        pb.empty()

        # 필터 적용
        filtered = results
        if dir_filter == '매수만':
            filtered = [r for r in filtered if r['buy_combos']]
        elif dir_filter == '매도만':
            filtered = [r for r in filtered if r['sell_combos']]

        if not filtered:
            st.info("🔍 조건에 맞는 콤보가 발견되지 않았습니다.")
            return

        # ── 결과 카드 표시 ──
        st.markdown(f"### 📊 스캔 결과: {len(filtered)}개 종목")

        for result in filtered:
            ticker = result['ticker']
            chg = result['change_pct']
            chg_color = '#34D399' if chg >= 0 else '#F87171'
            chg_icon = '▲' if chg >= 0 else '▼'
            j_label = result.get('judgment', 'N/A')
            conf = result.get('confidence', 0)

            # 콤보 카드
            buy_combos = result['buy_combos']
            sell_combos = result['sell_combos']

            # Tier 1 콤보 강조
            tier1_buy = [c for c in buy_combos if c['tier'] == 1]
            tier1_sell = [c for c in sell_combos if c['tier'] == 1]
            has_tier1 = bool(tier1_buy or tier1_sell)

            border_color = '#FFD700' if has_tier1 else '#1C2233'
            glow = 'box-shadow:0 0 15px rgba(255,215,0,0.15);' if has_tier1 else ''

            # 콤보 HTML
            combo_html = ""
            for c in (buy_combos + sell_combos):
                dot_color = '#34D399' if c['dir'] == 'buy' else '#F87171'
                tier_badge = '⭐' * (3 - c['tier'] + 1)  # Tier1=⭐⭐⭐, Tier2=⭐⭐
                combo_html += f"""<div style="display:flex;align-items:center;gap:8px;
                    padding:4px 0;border-bottom:1px solid rgba(255,255,255,0.03)">
                    <span style="color:{dot_color};font-size:.9rem">●</span>
                    <span style="color:#E8ECF1;font-weight:600;font-size:.85rem;flex:1">
                        {c['icon']} {c['kor']}</span>
                    <span style="font-size:.7rem">{tier_badge}</span>
                    <span style="color:#64748B;font-size:.7rem">{c['date']}</span>
                </div>"""

            st.markdown(f"""<div style="background:linear-gradient(160deg,#0F1320,#141926);
                border:1px solid {border_color};border-radius:14px;padding:16px 20px;
                margin:8px 0;{glow}">
                <div style="display:flex;justify-content:space-between;align-items:center;
                    margin-bottom:10px">
                    <div>
                        <span style="color:#A5B4FC;font-weight:800;font-size:1.2rem">{ticker}</span>
                        <span style="color:#64748B;font-size:.85rem;margin-left:10px">
                            ${result['price']:.2f}</span>
                        <span style="color:{chg_color};font-size:.85rem;margin-left:6px;font-weight:600">
                            {chg_icon}{abs(chg):.1f}%</span>
                    </div>
                    <div style="display:flex;gap:8px;align-items:center">
                        <span class="indicator-mini {'ind-bullish' if 'BUY' in j_label else ('ind-bearish' if 'SELL' in j_label else 'ind-neutral')}"
                            style="font-size:.75rem">{j_label} {conf:.0f}%</span>
                        <span style="color:#FCD34D;font-size:.8rem;font-weight:600">
                            {len(buy_combos)}B / {len(sell_combos)}S</span>
                    </div>
                </div>
                <div style="margin-top:6px">{combo_html}</div>
            </div>""", unsafe_allow_html=True)

            # 빠른 분석 버튼
            if st.button(f"📊 {ticker} 상세 분석", key=f"scan_{ticker}", use_container_width=True):
                st.session_state['quick_ticker'] = ticker



# ══════════════════════════════════════════
#  유틸리티 함수 (⚡ 최적화)
# ══════════════════════════════════════════
def _recent(s: pd.Series, lb: int = 3) -> pd.Series:
    """최근 lb 봉 내에 True가 있으면 True"""
    return s.astype(float).rolling(lb + 1, min_periods=1).max().fillna(0).astype(bool)


def _cooldown(sig: pd.Series, bars: int = 5) -> pd.Series:
    """⚡ numpy 벡터화 쿨다운"""
    v = sig.fillna(False).values.astype(bool)
    out = np.zeros(len(v), dtype=bool)
    last = -bars - 1
    for i in range(len(v)):
        if v[i] and (i - last) > bars:
            out[i] = True
            last = i
    return pd.Series(out, index=sig.index)


def _cooldown_directional(df: pd.DataFrame, buy_sig: str, sell_sig: str, bars: int = 5):
    """⚡ 방향별 쿨다운 — 반대 방향 시그널 발생 시 즉시 리셋"""
    bv = df.get(buy_sig, pd.Series(False, index=df.index)).fillna(False).values.astype(bool)
    sv = df.get(sell_sig, pd.Series(False, index=df.index)).fillna(False).values.astype(bool)
    b_out = np.zeros(len(bv), dtype=bool)
    s_out = np.zeros(len(sv), dtype=bool)
    last_b, last_s = -bars - 1, -bars - 1
    for i in range(len(df)):
        # 🔧 반대 방향 시그널 발생 시 쿨다운 리셋
        if sv[i]:
            last_b = -bars - 1  # 매도 발생 → 매수 쿨다운 초기화
        if bv[i]:
            last_s = -bars - 1  # 매수 발생 → 매도 쿨다운 초기화

        if bv[i] and (i - last_b) > bars:
            b_out[i] = True
            last_b = i
        if sv[i] and (i - last_s) > bars:
            s_out[i] = True
            last_s = i
    if buy_sig in df.columns:
        df[buy_sig] = pd.Series(b_out, index=df.index)
    if sell_sig in df.columns:
        df[sell_sig] = pd.Series(s_out, index=df.index)


def _volf(vol: pd.Series, ratio: float = 0.5, period: int = 20) -> pd.Series:
    """거래량 필터: 이동평균 대비 ratio 이상"""
    return vol >= (vol.rolling(period, min_periods=5).mean() * ratio)


def _valid_fmt(t: str) -> bool:
    return bool(re.match(r'^[A-Za-z]{1,5}([.\-][A-Za-z]{1,2})?$', t))


def _cls(val: float, lo: float, hi: float) -> str:
    return 'ind-bullish' if val < lo else ('ind-bearish' if val > hi else 'ind-neutral')


def _sig_pts(df: pd.DataFrame, sig_name: str, points: float) -> np.ndarray:
    """시그널 존재 시 점수, 없으면 0"""
    if sig_name in df.columns:
        return np.where(df[sig_name].fillna(False), points, 0.0)
    return 0.0


def _vectorized_streak(condition: pd.Series) -> pd.Series:
    """⚡ 루프 없는 연속 카운트 (groupby+cumsum)"""
    c = condition.astype(int)
    groups = (c == 0).cumsum()
    return c.groupby(groups).cumsum()


# ══════════════════════════════════════════
#  데이터 캐싱 (⚡ 세분화)
# ══════════════════════════════════════════
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_fundamentals(ticker: str) -> str:
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
        return "\n".join([
            f"Market Cap: {_get('marketCap','large')}",
            f"Shares Outstanding: {_get('sharesOutstanding','large')}",
            f"Float: {_get('floatShares','large')}",
            f"Short % of Float: {_get('shortPercentOfFloat','percent')}",
            f"Days to Cover: {_get('shortRatio','float')}",
            f"Trailing EPS: {_get('trailingEps','currency')}",
            f"P/E Ratio: {_get('trailingPE','float')}",
            f"P/S: {_get('priceToSalesTrailing12Months','float')}",
            f"P/B: {_get('priceToBook','float')}",
            f"PEG: {_get('pegRatio','float')}",
            f"52W High: {_get('fiftyTwoWeekHigh','currency')}",
            f"52W Low: {_get('fiftyTwoWeekLow','currency')}",
            f"Avg Vol: {_get('averageVolume','large')}",
        ])
    except Exception:
        return "펀더멘탈 데이터를 불러올 수 없습니다."


@st.cache_data(ttl=300, max_entries=30, show_spinner=False)
def fetch_history(ticker: str, _ts=None) -> pd.DataFrame:
    return yf.Ticker(ticker).history(period="2y")


@st.cache_data(ttl=600, show_spinner=False)
def validate_ticker(ticker: str) -> bool:
    try:
        hist = yf.Ticker(ticker).history(period="5d")
        return not hist.empty
    except Exception:
        return False


@st.cache_data(ttl=300, max_entries=30, show_spinner=False)
def compute_and_cache(ticker: str, _ts=None):
    df = fetch_history(ticker, _ts)
    if df.empty:
        return None
    return detect_all_signals(compute_indicators(df))


# ══════════════════════════════════════════
#  기술 지표 계산 엔진
#  🆕 모멘텀 가속도 + 수렴속도 + 셋업 지표 추가
# ══════════════════════════════════════════
def compute_rsi(s: pd.Series, p: int = 14) -> pd.Series:
    d = s.diff()
    g, l = d.clip(lower=0), -d.clip(upper=0)
    return 100 - (100 / (1 + g.ewm(alpha=1/p, min_periods=p).mean() /
                         (l.ewm(alpha=1/p, min_periods=p).mean() + 1e-10)))


def compute_mfi(h, l, c, v, p=14):
    tp = (h + l + c) / 3
    raw = tp * v
    d = tp.diff()
    return 100 - (100 / (1 + raw.where(d >= 0, 0.0).rolling(p).sum() /
                         (raw.where(d < 0, 0.0).rolling(p).sum() + 1e-10)))


def compute_rsi_mfi(h, l, c, v, p=60):
    rf, mf = compute_rsi(c, 20), compute_mfi(h, l, c, v, 20)
    rs, ms = compute_rsi(c, p), compute_mfi(h, l, c, v, p)
    return (((rf - 50) + (mf - 50)) / 2) * .6 + (((rs - 50) + (ms - 50)) / 2) * .4


def compute_wavetrend(h, l, c, ch=9, avg=12, ma=3):
    ap = (h + l + c) / 3
    esa = ap.ewm(span=ch, adjust=False).mean()
    d = abs(ap - esa).ewm(span=ch, adjust=False).mean()
    ci = (ap - esa) / (0.015 * d + 1e-10)
    wt1 = ci.ewm(span=avg, adjust=False).mean()
    wt2 = wt1.rolling(ma).mean()
    return (wt1, wt2,
            (wt1 > wt2) & (wt1.shift(1) <= wt2.shift(1)),   # WT_Up
            (wt1 < wt2) & (wt1.shift(1) >= wt2.shift(1)))   # WT_Down


def compute_stoch_rsi(c, rl=14, sl=14, ks=3, ds=3):
    rsi = compute_rsi(c, rl)
    mn, mx = rsi.rolling(sl).min(), rsi.rolling(sl).max()
    k = (((rsi - mn) / (mx - mn + 1e-10)) * 100).rolling(ks).mean()
    return k, k.rolling(ds).mean()


def compute_tr(h, l, c):
    pc = c.shift(1)
    return pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)


def compute_adx(h, l, c, p=14):
    tr = compute_tr(h, l, c)
    ph, pl = h.shift(1), l.shift(1)
    pdm = pd.Series(np.where((h - ph) > (pl - l), np.maximum(h - ph, 0), 0),
                     index=h.index, dtype=float)
    mdm = pd.Series(np.where((pl - l) > (h - ph), np.maximum(pl - l, 0), 0),
                     index=h.index, dtype=float)
    atr = tr.ewm(alpha=1/p, min_periods=p).mean()
    pdi = 100 * pdm.ewm(alpha=1/p, min_periods=p).mean() / (atr + 1e-10)
    mdi = 100 * mdm.ewm(alpha=1/p, min_periods=p).mean() / (atr + 1e-10)
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi + 1e-10)
    return dx.ewm(alpha=1/p, min_periods=p).mean(), pdi, mdi


def compute_obv(c, v):
    return (v * np.sign(c.diff()).fillna(0)).cumsum()


def compute_macd(c, f=12, s=26, sig=9):
    ml = c.ewm(span=f, adjust=False).mean() - c.ewm(span=s, adjust=False).mean()
    sl = ml.ewm(span=sig, adjust=False).mean()
    return ml, sl, ml - sl


def compute_ichimoku(h, l, c, tenkan_p=9, kijun_p=26, senkou_b_p=52, displacement=26):
    tenkan = (h.rolling(tenkan_p).max() + l.rolling(tenkan_p).min()) / 2
    kijun = (h.rolling(kijun_p).max() + l.rolling(kijun_p).min()) / 2
    senkou_a = ((tenkan + kijun) / 2).shift(displacement)
    senkou_b = ((h.rolling(senkou_b_p).max() + l.rolling(senkou_b_p).min()) / 2).shift(displacement)
    chikou = c.shift(-displacement)
    return tenkan, kijun, senkou_a, senkou_b, chikou


def compute_cmf(h, l, c, v, p=20):
    mfm = ((c - l) - (h - c)) / (h - l + 1e-10)
    mfv = mfm * v
    return mfv.rolling(p).sum() / (v.rolling(p).sum() + 1e-10)


def compute_keltner(h, l, c, el=20, al=10, m=1.5):
    mid = c.ewm(span=el, adjust=False).mean()
    atr = compute_tr(h, l, c).rolling(al).mean()
    return mid + atr * m, mid, mid - atr * m


def compute_supertrend(h, l, c, period=10, mult=3.0):
    atr = compute_tr(h, l, c).rolling(period).mean()
    hl2 = (h + l) / 2
    up = (hl2 + mult * atr).values.copy()
    dn = (hl2 - mult * atr).values.copy()
    cl = c.values
    n = len(c)
    sv = np.full(n, np.nan)
    dv = np.zeros(n, dtype=int)
    fv = period
    if fv >= n:
        return pd.Series(np.nan, index=c.index), pd.Series(0, index=c.index, dtype=int)
    dv[fv] = 1
    sv[fv] = dn[fv]
    for i in range(fv + 1, n):
        if dv[i-1] == 1:
            dn[i] = max(dn[i], dn[i-1]) if not np.isnan(dn[i-1]) else dn[i]
        else:
            up[i] = min(up[i], up[i-1]) if not np.isnan(up[i-1]) else up[i]
        if dv[i-1] == 1:
            dv[i], sv[i] = (-1, up[i]) if cl[i] < dn[i] else (1, dn[i])
        else:
            dv[i], sv[i] = (1, dn[i]) if cl[i] > up[i] else (-1, up[i])
    return pd.Series(sv, index=c.index), pd.Series(dv, index=c.index)


# ══════════════════════════════════════════
#  🆕 선행 지표 계산 (Anticipation Engine)
#  핵심: "이미 일어난 것"이 아닌 "곧 일어날 것"을 감지
# ══════════════════════════════════════════

def compute_momentum_acceleration(df: pd.DataFrame) -> pd.DataFrame:
    """
    🆕 모멘텀 가속도 (2차 미분)
    - 1차 미분: 오실레이터의 변화량 (이미 계산됨)
    - 2차 미분: 변화량의 변화량 = 가속/감속
    가속이 양수면 모멘텀이 빨라지는 중, 음수면 느려지는 중
    → 꺾임 직전을 감지할 수 있음
    """
    # RSI 가속도 (3봉 변화율의 변화율)
    rsi_vel = df['RSI'] - df['RSI'].shift(3)       # 속도
    df['RSI_Accel'] = rsi_vel - rsi_vel.shift(3)    # 가속도

    # WT1 가속도
    wt_vel = df['WT1'] - df['WT1'].shift(3)
    df['WT_Accel'] = wt_vel - wt_vel.shift(3)

    # MACD 히스토그램 가속도
    df['MACD_Accel'] = df['MACD_Hist'] - df['MACD_Hist'].shift(3)

    # 🆕 복합 모멘텀 가속 스코어: 3개 오실레이터의 가속도를 정규화 후 합산
    rsi_a_norm = df['RSI_Accel'] / (df['RSI_Accel'].rolling(50, min_periods=10).std() + 1e-10)
    wt_a_norm = df['WT_Accel'] / (df['WT_Accel'].rolling(50, min_periods=10).std() + 1e-10)
    macd_a_norm = df['MACD_Accel'] / (df['MACD_Accel'].rolling(50, min_periods=10).std() + 1e-10)
    df['Composite_Accel'] = (rsi_a_norm + wt_a_norm + macd_a_norm) / 3

    return df


def compute_convergence_speed(df: pd.DataFrame) -> pd.DataFrame:
    """
    🆕 WT1-WT2 수렴 속도 계산
    교차 직전에 갭이 빠르게 줄어드는 것을 감지
    → 실제 교차(WT_Up/WT_Down) 1~3봉 전에 알림
    """
    gap = df['WT1'] - df['WT2']
    gap_abs = gap.abs()
    # 수렴 속도 = 갭 변화율 (음수 = 갭이 줄고 있음)
    df['WT_Gap'] = gap
    df['WT_Gap_Abs'] = gap_abs
    df['WT_Conv_Speed'] = gap_abs.shift(3) - gap_abs  # 양수 = 수렴 중

    # 수렴 방향: WT1이 아래에서 위로 올라가는지, 위에서 아래로 내려가는지
    df['WT_Conv_Bull'] = (gap < 0) & (df['WT_Conv_Speed'] > JT.CONVERGENCE_SLOW) & (df['WT1'] < 20)
    df['WT_Conv_Bear'] = (gap > 0) & (df['WT_Conv_Speed'] > JT.CONVERGENCE_SLOW) & (df['WT1'] > -20)

    return df


def compute_setup_pressure(df: pd.DataFrame) -> pd.DataFrame:
    """
    🆕 셋업 축적 점수 (Setup Pressure Score)
    여러 조건이 동시에 축적되는 것을 감지
    → "조건이 무르익고 있다"는 것을 수치화

    원리: 과매도 영역 + 변동성 축소 + 거래량 고갈 + 양의 가속도
          = 폭발적 상승의 전조
    """
    idx = df.index

    # ─── 매수 셋업 점수 ───
    bp = pd.Series(0.0, index=idx)
    # 과매도 접근
    bp += np.where(df['WT1'] < -40, 2.0, np.where(df['WT1'] < -20, 1.0, 0))
    bp += np.where(df['RSI'] < 35, 1.5, np.where(df['RSI'] < 45, 0.5, 0))
    bp += np.where(df['StochK'] < 25, 1.0, 0)
    # 모멘텀 방향 전환 징후
    bp += np.where(df.get('Composite_Accel', pd.Series(0, index=idx)) > JT.ACCEL_MODERATE, 2.0,
          np.where(df.get('Composite_Accel', pd.Series(0, index=idx)) > 0.5, 1.0, 0))
    # WT 수렴 중
    bp += np.where(df.get('WT_Conv_Bull', pd.Series(False, index=idx)), 1.5, 0)
    # 변동성 축소 (스퀴즈 축적)
    bb_w = df.get('BB_Width', pd.Series(0, index=idx))
    bb_w_ma = bb_w.rolling(50, min_periods=10).mean()
    bp += np.where(bb_w < bb_w_ma * 0.7, 1.5, np.where(bb_w < bb_w_ma, 0.5, 0))
    # 거래량 고갈 (반전 전조)
    vol_ratio = df['Volume'] / (df['Volume'].rolling(20, min_periods=5).mean() + 1e-10)
    vol_dry_streak = _vectorized_streak(vol_ratio < 0.7)
    bp += np.where(vol_dry_streak >= 3, 1.0, 0)
    # 자금흐름 개선 조짐
    rmfi = df['RSI_MFI']
    bp += np.where((rmfi < 0) & (rmfi > rmfi.shift(3)), 1.0, 0)  # 음수이지만 개선 중

    df['Setup_Pressure_Buy'] = bp

    # ─── 매도 셋업 점수 ───
    sp = pd.Series(0.0, index=idx)
    sp += np.where(df['WT1'] > 40, 2.0, np.where(df['WT1'] > 20, 1.0, 0))
    sp += np.where(df['RSI'] > 65, 1.5, np.where(df['RSI'] > 55, 0.5, 0))
    sp += np.where(df['StochK'] > 75, 1.0, 0)
    sp += np.where(df.get('Composite_Accel', pd.Series(0, index=idx)) < -JT.ACCEL_MODERATE, 2.0,
          np.where(df.get('Composite_Accel', pd.Series(0, index=idx)) < -0.5, 1.0, 0))
    sp += np.where(df.get('WT_Conv_Bear', pd.Series(False, index=idx)), 1.5, 0)
    sp += np.where(bb_w < bb_w_ma * 0.7, 1.5, np.where(bb_w < bb_w_ma, 0.5, 0))
    sp += np.where(vol_dry_streak >= 3, 1.0, 0)
    sp += np.where((rmfi > 0) & (rmfi < rmfi.shift(3)), 1.0, 0)

    df['Setup_Pressure_Sell'] = sp

    return df


def detect_anticipation_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    🆕 선행 시그널 감지
    완성된 패턴이 아닌 "임박한 움직임"을 포착
    """
    idx = df.index
    bb_w = df.get('BB_Width', pd.Series(0, index=idx))
    bb_w_q10 = bb_w.rolling(120, min_periods=20).quantile(0.1)
    squeeze_tight = bb_w <= bb_w_q10

    # ─── 스퀴즈 셋업 (방향 힌트 포함) ───
    # 조건: BB 극도 축소 + 방향 힌트
    macd_h = df['MACD_Hist']
    macd_turning_up = (macd_h < 0) & (macd_h > macd_h.shift(1)) & (macd_h.shift(1) > macd_h.shift(2))
    macd_turning_dn = (macd_h > 0) & (macd_h < macd_h.shift(1)) & (macd_h.shift(1) < macd_h.shift(2))

    df['Setup_Squeeze_Bull'] = squeeze_tight & macd_turning_up & (df['WT1'] < 30)
    df['Setup_Squeeze_Bear'] = squeeze_tight & macd_turning_dn & (df['WT1'] > -30)

    # ─── 모멘텀 가속 시그널 ───
    comp_accel = df.get('Composite_Accel', pd.Series(0, index=idx))
    # 3개 오실레이터가 동시에 가속 상승: 모멘텀 폭발 임박
    rsi_accel_up = df.get('RSI_Accel', pd.Series(0, index=idx)) > 0
    wt_accel_up = df.get('WT_Accel', pd.Series(0, index=idx)) > 0
    macd_accel_up = df.get('MACD_Accel', pd.Series(0, index=idx)) > 0
    all_accel_up = rsi_accel_up & wt_accel_up & macd_accel_up
    all_accel_dn = (~rsi_accel_up) & (~wt_accel_up) & (~macd_accel_up)

    df['Momentum_Accel_Buy'] = all_accel_up & (comp_accel > JT.ACCEL_MODERATE) & (df['WT1'] < 40)
    df['Momentum_Accel_Sell'] = all_accel_dn & (comp_accel < -JT.ACCEL_MODERATE) & (df['WT1'] > -40)

    # ─── 거래량 고갈 (돌파 전조) ───
    vol_ratio = df['Volume'] / (df['Volume'].rolling(20, min_periods=5).mean() + 1e-10)
    vol_dry = _vectorized_streak(vol_ratio < 0.6)
    df['Volume_Dry_Up'] = vol_dry >= 5  # 5일 연속 거래량 60% 미만

    # ─── WT 수렴 시그널 (교차 1~3봉 전) ───
    conv_speed = df.get('WT_Conv_Speed', pd.Series(0, index=idx))
    gap_abs = df.get('WT_Gap_Abs', pd.Series(999, index=idx))
    # 빠른 수렴 + 갭이 아직 남아있음(아직 교차 안됨) + 방향 힌트
    df['WT_Convergence_Bull'] = (
        (conv_speed > JT.CONVERGENCE_FAST) & (gap_abs > 2) & (gap_abs < 15) &
        (df['WT1'] < df['WT2']) &  # 아직 아래에 있음 (교차 전)
        (df['WT1'] < 20))          # 과매수가 아닌 곳에서
    df['WT_Convergence_Bear'] = (
        (conv_speed > JT.CONVERGENCE_FAST) & (gap_abs > 2) & (gap_abs < 15) &
        (df['WT1'] > df['WT2']) &
        (df['WT1'] > -20))

    return df


# ══════════════════════════════════════════
#  지표 통합 계산 (🆕 가속도 + 수렴 + 셋업 포함)
# ══════════════════════════════════════════
def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    c, h, l, v = df['Close'], df['High'], df['Low'], df['Volume']

    # ── 이동평균 ──
    for ma in [5, 10, 20, 50, 100, 125, 200]:
        df[f'MA{ma}'] = c.rolling(ma).mean()
    df['EMA8'] = c.ewm(span=8, adjust=False).mean()
    df['EMA21'] = c.ewm(span=21, adjust=False).mean()

    # ── 볼린저 밴드 ──
    df['BB_Mid'] = df['MA20']
    s20 = c.rolling(20).std()
    df['BB_Up'], df['BB_Low'] = df['BB_Mid'] + s20 * 2, df['BB_Mid'] - s20 * 2
    df['BB_Width'] = (df['BB_Up'] - df['BB_Low']) / (df['BB_Mid'] + 1e-10)
    df['Percent_B'] = (c - df['BB_Low']) / (df['BB_Up'] - df['BB_Low'] + 1e-10)

    # ── ATR + Chandelier ──
    df['ATR'] = compute_tr(h, l, c).rolling(14).mean()
    atr22 = compute_tr(h, l, c).rolling(22).mean()
    df['Chandelier_Long'] = h.rolling(22).max() - atr22 * 3.0
    df['Chandelier_Short'] = l.rolling(22).min() + atr22 * 3.0

    # ── SuperTrend ──
    df['SuperTrend'], df['ST_Direction'] = compute_supertrend(h, l, c)

    # ── WaveTrend ──
    wt1, wt2, wu, wd = compute_wavetrend(h, l, c)
    df['WT1'], df['WT2'], df['WT_Up'], df['WT_Down'] = wt1, wt2, wu, wd

    # ── 오실레이터 ──
    df['RSI'] = compute_rsi(c, 14)
    df['StochK'], df['StochD'] = compute_stoch_rsi(c)
    df['MFI'] = compute_mfi(h, l, c, v, 14)
    df['RSI_MFI'] = compute_rsi_mfi(h, l, c, v, 60)

    # ── VWAP Oscillator ──
    vwap = (c * v).rolling(20).sum() / (v.rolling(20).sum() + 1e-10)
    df['VWAP_Osc'] = ((c - vwap) / (vwap + 1e-10)) * 100

    # ── ADX + OBV ──
    df['ADX'], df['Plus_DI'], df['Minus_DI'] = compute_adx(h, l, c)
    df['OBV'] = compute_obv(c, v)

    # ── Keltner Channel + MACD ──
    df['KC_Upper'], df['KC_Mid'], df['KC_Lower'] = compute_keltner(h, l, c)
    df['MACD_Line'], df['MACD_Signal'], df['MACD_Hist'] = compute_macd(c)

    # ── Ichimoku Cloud ──
    tenkan, kijun, senkou_a, senkou_b, chikou = compute_ichimoku(h, l, c)
    df['Ichimoku_Tenkan'] = tenkan
    df['Ichimoku_Kijun'] = kijun
    df['Ichimoku_SenkouA'] = senkou_a
    df['Ichimoku_SenkouB'] = senkou_b
    df['Ichimoku_Chikou'] = chikou

    # ── CMF ──
    df['CMF'] = compute_cmf(h, l, c, v, 20)

    # ═══ 🆕 선행 지표 계산 ═══
    df = compute_momentum_acceleration(df)
    df = compute_convergence_speed(df)
    df = compute_setup_pressure(df)

    return df


# ══════════════════════════════════════════
#  패턴 탐지 함수들
#  🔧 Parabolic 임계값 완화, BB 시그널 분리
# ══════════════════════════════════════════

def detect_pivot_div(price, osc, lb=60, pw=5, os_lim=None, ob_lim=None):
    """⚡ 피봇 다이버전스 감지 (기존과 동일 — 향후 벡터화 예정)"""
    n = len(price)
    pv, ov = price.values, osc.values
    half = pw
    p_lo, p_hi = [], []
    for i in range(2 * half, n):
        c_ = i - half
        w = pv[i - 2*half:i + 1]
        if pv[c_] == w.min(): p_lo.append((i, c_))
        if pv[c_] == w.max(): p_hi.append((i, c_))
    bd = pd.Series(False, index=price.index)
    brd = pd.Series(False, index=price.index)
    hb = pd.Series(False, index=price.index)
    hbr = pd.Series(False, index=price.index)
    for i_idx in range(1, len(p_lo)):
        ci, pi = p_lo[i_idx]; cj, pj = p_lo[i_idx-1]
        if not (pw*2 <= (pi - pj) <= lb): continue
        if (os_lim is None or ov[pi] <= os_lim) and pv[pi] < pv[pj] and ov[pi] > ov[pj]:
            bd.iloc[ci] = True
        if pv[pi] > pv[pj] and ov[pi] < ov[pj]:
            hb.iloc[ci] = True
    for i_idx in range(1, len(p_hi)):
        ci, pi = p_hi[i_idx]; cj, pj = p_hi[i_idx-1]
        if not (pw*2 <= (pi - pj) <= lb): continue
        if (ob_lim is None or ov[pi] >= ob_lim) and pv[pi] > pv[pj] and ov[pi] < ov[pj]:
            brd.iloc[ci] = True
        if pv[pi] < pv[pj] and ov[pi] > ov[pj]:
            hbr.iloc[ci] = True
    return bd, brd, hb, hbr


def detect_ttm_squeeze(bbu, bbl, kcu, kcl, c, h, l, kcm):
    sq = (bbu < kcu) & (bbl > kcl)
    fire = (~sq) & sq.shift(1).fillna(False)
    momentum = c - ((h.rolling(20).max() + l.rolling(20).min()) / 2 + kcm) / 2
    mu = momentum > momentum.shift(1)
    md = momentum < momentum.shift(1)
    return sq, fire & (momentum > 0) & mu, fire & (momentum < 0) & md


def detect_volume_climax(c, o, v, wt1, atr, z_thresh=2.5):
    vm = v.rolling(20).mean()
    vs = v.rolling(20).std()
    vz = (v - vm) / (vs + 1e-10)
    big = (c - o).abs() > atr * 0.5
    ps = (vz.shift(1) > z_thresh) & big.shift(1)
    return (ps & (c.shift(1) < o.shift(1)) & (wt1.shift(1) < -40) & (c > o),
            ps & (c.shift(1) > o.shift(1)) & (wt1.shift(1) > 40) & (c < o))


def _detect_engulfing_pair(c, o, wt1, wt_t=20):
    body = (c - o).abs()
    body_prev = (c.shift(1) - o.shift(1)).abs()
    avg_body = body.rolling(20).mean()
    big = (body > avg_body * 0.8) & (body > body_prev)
    prev_body_high = pd.concat([c.shift(1), o.shift(1)], axis=1).max(axis=1)
    prev_body_low = pd.concat([c.shift(1), o.shift(1)], axis=1).min(axis=1)
    curr_body_high = pd.concat([c, o], axis=1).max(axis=1)
    curr_body_low = pd.concat([c, o], axis=1).min(axis=1)
    prev_bearish = c.shift(1) < o.shift(1)
    prev_bullish = c.shift(1) > o.shift(1)
    bull = (prev_bearish & (c > o) &
            (curr_body_low <= prev_body_low) & (curr_body_high >= prev_body_high) &
            big & (wt1 < -wt_t))
    bear = (prev_bullish & (c < o) &
            (curr_body_low <= prev_body_low) & (curr_body_high >= prev_body_high) &
            big & (wt1 > wt_t))
    return bull, bear


def _detect_parabolic_pair(c, o, wt1, bbu, bbl, atr):
    """🔧 FIX: -85→-80, 85→80 (발생 빈도 현실화)"""
    return (((wt1 < -80) & (wt1 > wt1.shift(1)) & (c > o) & (c > c.shift(1))) |
            ((c < bbl - atr * 1.5) & (c > o)),
            ((wt1 > 80) & (wt1 < wt1.shift(1)) & (c < o) & (c < c.shift(1))) |
            ((c > bbu + atr * 1.5) & (c < o)))


def _detect_ema_pullback_pair(c, h, l, v, e8, e21, atr, wt1, wt2):
    vok = _volf(v, 0.5)
    ar = atr / (c + 1e-10)
    results = {}
    for d in ['buy', 'sell']:
        slope = e21 > e21.shift(5) if d == 'buy' else e21 < e21.shift(5)
        trend = ((e8 > e21) if d == 'buy' else (e8 < e21)) & slope
        side = (c > e8) if d == 'buy' else (c < e8)
        if d == 'buy':
            t = (l <= e8 * (1 + ar * 0.15)) & (l >= e21 * (1 - ar * 0.25))
            tr = _recent(t, 2)
            b = (c >= e8) & (c > h.shift(1))
            wok = (wt1 > wt1.shift(1)) & (wt1 > wt2) & (wt1 < 60)
        else:
            t = (h >= e8 * (1 - ar * 0.15)) & (h <= e21 * (1 + ar * 0.25))
            tr = _recent(t, 2)
            b = (c <= e8) & (c < l.shift(1))
            wok = (wt1 < wt1.shift(1)) & (wt1 < wt2) & (wt1 > -60)
        results[d] = trend & side & tr & b & wok & vok
    return results['buy'], results['sell']


def _detect_mom_ignition_pair(c, o, v, bbu, bbl, atr, e8, e21, wt1, bb_w):
    body = (c - o).abs()
    bb = body > atr * 1.5
    hv = v > v.rolling(20).mean() * 2.0
    compressed = bb_w.shift(1) < bb_w.rolling(20).mean().shift(1)
    return ((c > o) & bb & hv & (c > bbu) & (e8 > e21) & (wt1 < 50) & compressed,
            (c < o) & bb & hv & (c < bbl) & (e8 < e21) & (wt1 > -50) & compressed)


def _detect_vwap_pair(c, vosc, wt1, wt2, v, atr):
    vok = _volf(v, 0.7)
    ap = (atr / (c + 1e-10) * 100).clip(0.3, 3.0)
    dt = (ap * 0.3).clip(0.3, 1.5)
    return ((vosc > 0) & (vosc.shift(1) < -dt) & (wt1 > wt2) & (wt1 < 30) & vok,
            (vosc < 0) & (vosc.shift(1) > dt) & (wt1 < wt2) & (wt1 > -30) & vok)


# ── 캔들스틱 패턴 (🧹 Spinning_Top 제거) ──
def detect_candlestick_patterns(c, o, h, l, wt1, atr):
    body = (c - o).abs()
    upper_shadow = h - pd.concat([c, o], axis=1).max(axis=1)
    lower_shadow = pd.concat([c, o], axis=1).min(axis=1) - l
    full_range = h - l + 1e-10
    avg_body = body.rolling(20).mean()
    is_small = body < avg_body * 0.6
    min_range = atr * 0.5

    hammer = ((lower_shadow >= body * 2) & (upper_shadow <= body * 0.3) &
              is_small & (wt1 < -20) & (c >= o) & (full_range > min_range))
    shooting = ((upper_shadow >= body * 2) & (lower_shadow <= body * 0.3) &
                is_small & (wt1 > 20) & (c <= o) & (full_range > min_range))
    doji = (body <= full_range * 0.05) & (full_range > atr * 0.3)
    doji_bull = doji & (wt1 < -30) & (wt1 > wt1.shift(1)) & (c.shift(1) < c.shift(3))
    doji_bear = doji & (wt1 > 30) & (wt1 < wt1.shift(1)) & (c.shift(1) > c.shift(3))

    d1_bearish = (c.shift(2) < o.shift(2)) & (body.shift(2) > avg_body.shift(2))
    d2_small = body.shift(1) < avg_body.shift(1) * 0.5
    d3_bullish = (c > o) & (c > (o.shift(2) + c.shift(2)) / 2) & (body > avg_body * 0.8)
    morning = d1_bearish & d2_small & d3_bullish & (wt1 < -15)

    d1_bullish = (c.shift(2) > o.shift(2)) & (body.shift(2) > avg_body.shift(2))
    d3_bearish = (c < o) & (c < (o.shift(2) + c.shift(2)) / 2) & (body > avg_body * 0.8)
    evening = d1_bullish & d2_small & d3_bearish & (wt1 > 15)

    return hammer, shooting, doji_bull, doji_bear, morning, evening


def detect_inside_outside_day(h, l, c, o, wt1):
    inside = (h < h.shift(1)) & (l > l.shift(1))
    outside = (h > h.shift(1)) & (l < l.shift(1))
    return (inside,
            outside & (c > o) & (c > h.shift(1)) & (wt1 < 30),
            outside & (c < o) & (c < l.shift(1)) & (wt1 > -30))


def detect_ma_crossovers(c, ma20, ma50, ma200):
    sigs = {}
    for tag, ma in [('20MA', ma20), ('50MA', ma50), ('200MA', ma200)]:
        sigs[f'Cross_Above_{tag}'] = (c > ma) & (c.shift(1) <= ma.shift(1))
        sigs[f'Fell_Below_{tag}'] = (c < ma) & (c.shift(1) >= ma.shift(1))
    return sigs


def detect_bb_extra(c, o, bb_up, bb_low, bb_w, wt1):
    """🔧 BB 하단을 반등(매수) vs 붕괴(매도)로 분리"""
    bwm = bb_w.rolling(20).mean()
    widening = (bb_w > bb_w.shift(1)) & (bb_w.shift(1) < bwm.shift(1))

    bb_upper_break = c > bb_up
    # 🔧 BB 하단: 반등(양봉=매수기회) vs 붕괴(음봉=위험)
    below_lower = c < bb_low
    bb_lower_bounce = below_lower & (c > o) & (wt1 > wt1.shift(1))  # 양봉 + WT 반등
    bb_lower_break = below_lower & (c < o) & (wt1 < wt1.shift(1))   # 음봉 + WT 하락

    return (bb_upper_break, bb_lower_bounce, bb_lower_break,
            widening & (c > c.shift(1)) & (wt1 > wt1.shift(1)),
            widening & (c < c.shift(1)) & (wt1 < wt1.shift(1)))


def detect_macd_centerline(ml):
    return (ml > 0) & (ml.shift(1) <= 0), (ml < 0) & (ml.shift(1) >= 0)


def detect_consecutive_days(c):
    up = c > c.shift(1)
    dn = c < c.shift(1)
    us = _vectorized_streak(up)
    ds = _vectorized_streak(dn)
    return {'Up_3_Days': us >= 3, 'Up_5_Days': us >= 5,
            'Down_3_Days': ds >= 3, 'Down_5_Days': ds >= 5}


def detect_gaps(c, o, h, l, atr):
    thr = atr * 0.5
    gu = (o > h.shift(1)) & ((o - h.shift(1)) > thr)
    gd = (o < l.shift(1)) & ((l.shift(1) - o) > thr)
    return (gu, gd,
            gu.shift(1).fillna(False) & (l <= h.shift(2)),
            gd.shift(1).fillna(False) & (h >= l.shift(2)))


def detect_nr7(h, l):
    dr = h - l
    mn7 = dr.rolling(7).min()
    nr = dr <= mn7
    return nr, nr & nr.shift(1).fillna(False)


def detect_range_bars(h, l, atr):
    dr = h - l
    wide = dr > atr * 2.0
    narrow = dr < atr * 0.5
    recent_wide = wide.rolling(5, min_periods=1).max().shift(1).fillna(False).astype(bool)
    calm = recent_wide & narrow
    return wide, calm


def detect_52w(c, h, l):
    h252_prev = h.rolling(252, min_periods=200).max().shift(1)
    l252_prev = l.rolling(252, min_periods=200).min().shift(1)
    return h > h252_prev, l < l252_prev


# ── Jeff Cooper 패턴들 (변경 없음) ──
def detect_123_pullback(h, l, c, adx, pdi, mdi):
    strong_bull = (adx > 30) & (pdi > mdi)
    strong_bear = (adx > 30) & (mdi > pdi)
    inside = (h < h.shift(1)) & (l > l.shift(1))
    ll1 = l < l.shift(1); ll2 = l.shift(1) < l.shift(2); ll3 = l.shift(2) < l.shift(3)
    tll = ll1 & ll2 & ll3
    tli = (ll1 & ll2 & inside.shift(2)) | (ll1 & inside.shift(1) & ll2.shift(1)) | (inside & ll1 & ll2)
    hh1 = h > h.shift(1); hh2 = h.shift(1) > h.shift(2); hh3 = h.shift(2) > h.shift(3)
    thh = hh1 & hh2 & hh3
    thi = (hh1 & hh2 & inside.shift(2)) | (hh1 & inside.shift(1) & hh2.shift(1)) | (inside & hh1 & hh2)
    return strong_bull & (tll | tli), strong_bear & (thh | thi)


def detect_180_setup(c, o, h, l, ma10, ma50):
    dr = h - l + 1e-10
    cp = (c - l) / dr
    pp = (c.shift(1) - l.shift(1)) / (h.shift(1) - l.shift(1) + 1e-10)
    return ((pp <= 0.25) & (cp >= 0.75) & (c > ma10) & (c > ma50),
            (pp >= 0.75) & (cp <= 0.25) & (c < ma10) & (c < ma50))


def detect_boomer(h, l, adx, pdi, mdi):
    inside = (h < h.shift(1)) & (l > l.shift(1))
    in2 = inside & inside.shift(1)
    return (in2.shift(1).fillna(False) & (adx > 30) & (pdi > mdi),
            in2.shift(1).fillna(False) & (adx > 30) & (mdi > pdi))


def detect_expansion(h, l, c):
    dr = h - l
    mr9 = dr.rolling(9).max()
    h60 = h.rolling(60, min_periods=40).max()
    l60 = l.rolling(60, min_periods=40).min()
    return (h >= h60) & (dr >= mr9), (l <= l60) & (dr >= mr9)


def detect_gilligans(o, c, h, l):
    dr = h - l + 1e-10
    cp = (c - l) / dr
    l60 = l.rolling(60, min_periods=40).min()
    h60 = h.rolling(60, min_periods=40).max()
    return ((o <= l60) & (o < l.shift(1)) & (cp >= 0.5) & (c >= o),
            (o >= h60) & (o > h.shift(1)) & (cp <= 0.5) & (c <= o))


def detect_lizard(o, c, h, l):
    dr = h - l + 1e-10
    cp = (c - l) / dr
    op = (o - l) / dr
    return ((cp >= 0.75) & (op >= 0.75) & (l <= l.rolling(10).min()),
            (cp <= 0.25) & (op <= 0.25) & (h >= h.rolling(10).max()))


def detect_non_adx_123(h, l, c, ma50):
    inside = (h < h.shift(1)) & (l > l.shift(1))
    ll1 = l < l.shift(1); ll2 = l.shift(1) < l.shift(2)
    tll = ll1 & ll2 & (l.shift(2) < l.shift(3))
    tli = ((ll1 & ll2 & inside.shift(2)) | (ll1 & inside.shift(1) & ll2.shift(1)) |
           (inside & ll1 & ll2))
    hh1 = h > h.shift(1); hh2 = h.shift(1) > h.shift(2)
    thh = hh1 & hh2 & (h.shift(2) > h.shift(3))
    thi = ((hh1 & hh2 & inside.shift(2)) | (hh1 & inside.shift(1) & hh2.shift(1)) |
           (inside & hh1 & hh2))
    return (c > ma50) & (tll | tli), (c < ma50) & (thh | thi)


def detect_pocket_pivot(c, o, v, ma50, ma200):
    dv = v.where(c < c.shift(1), 0)
    return (c > o) & (v > dv.rolling(10).max()) & (c > ma50) & (c > c.shift(1))


def detect_ichimoku_signals(c, tenkan, kijun, senkou_a, senkou_b):
    kumo_top = pd.concat([senkou_a, senkou_b], axis=1).max(axis=1)
    kumo_bot = pd.concat([senkou_a, senkou_b], axis=1).min(axis=1)
    kumo_bull = ((c > kumo_top) & (c.shift(1) <= kumo_top.shift(1)) & (tenkan > kijun))
    kumo_bear = ((c < kumo_bot) & (c.shift(1) >= kumo_bot.shift(1)) & (tenkan < kijun))
    tk_bull = ((tenkan > kijun) & (tenkan.shift(1) <= kijun.shift(1)) & (c > kumo_top))
    tk_bear = ((tenkan < kijun) & (tenkan.shift(1) >= kijun.shift(1)) & (c < kumo_bot))
    return kumo_bull, kumo_bear, tk_bull, tk_bear


def detect_cmf_signals(cmf, c, ma50):
    cmf_bull = (cmf > 0.1) & (cmf.shift(1) <= 0.1) & (c > ma50)
    cmf_bear = (cmf < -0.1) & (cmf.shift(1) >= -0.1) & (c < ma50)
    return cmf_bull, cmf_bear


# ── Money Flow 시그널 (🔧 FIX: 한 번만 계산) ──
def detect_mf_signals(c, rmfi):
    """Money Flow 시그널 — ⚡ 벡터화"""
    mf_cross_bull = (rmfi > 0) & (rmfi.shift(1) <= 0)
    mf_cross_bear = (rmfi < 0) & (rmfi.shift(1) >= 0)
    mf_rising = rmfi > rmfi.shift(1)
    mf_falling = rmfi < rmfi.shift(1)
    mf_up_streak = _vectorized_streak(mf_rising)
    mf_dn_streak = _vectorized_streak(mf_falling)
    mf_slope_5 = rmfi - rmfi.shift(5)
    mf_slope_10 = rmfi - rmfi.shift(10)

    price_lower = c < c.rolling(5).min().shift(1)
    mf_higher = rmfi > rmfi.rolling(5).min().shift(1)
    mf_bull_div = price_lower & mf_higher & (rmfi < 0)

    price_higher = c > c.rolling(5).max().shift(1)
    mf_lower = rmfi < rmfi.rolling(5).max().shift(1)
    mf_bear_div = price_higher & mf_lower & (rmfi > 0)

    return {
        'MF_Cross_Bull': mf_cross_bull, 'MF_Cross_Bear': mf_cross_bear,
        'MF_Strong_Up': mf_up_streak >= 3, 'MF_Strong_Dn': mf_dn_streak >= 3,
        'MF_Accel_Up': mf_up_streak >= 5, 'MF_Accel_Dn': mf_dn_streak >= 5,
        'MF_Slope_5': mf_slope_5, 'MF_Slope_10': mf_slope_10,
        'MF_Bull_Div': mf_bull_div, 'MF_Bear_Div': mf_bear_div,
        'MF_Rising': mf_rising, 'MF_Falling': mf_falling,
        'MF_Up_Streak': mf_up_streak, 'MF_Dn_Streak': mf_dn_streak,
    }


def _deduplicate(df):
    for _cat, sigs in SIGNAL_HIERARCHY.items():
        for i, s in enumerate(sigs):
            if s not in df.columns: continue
            for higher in sigs[:i]:
                if higher in df.columns:
                    df[s] = df[s] & ~df[higher]
    return df

# ══════════════════════════════════════════
#  PART 1/4 끝
#  다음: PART 2/4 — 통합 시그널 탐지 + 8-Layer 판단 엔진
# ══════════════════════════════════════════
# ══════════════════════════════════════════════════════════════
#  CipherX V12.0 — PART 2/4
#  통합 시그널 탐지 (🔧 MF 이중계산 버그 수정)
#  + 8-Layer 판단 엔진 (🆕 Anticipation Layer)
#  + Confluence + Combo (🔧 등급별 보너스)
# ══════════════════════════════════════════════════════════════


# ──────────────────────────────────────────
# 통합 시그널 탐지 엔진
# 🔧 FIX: MF 시그널 한 번만 계산 (이중 덮어씌기 제거)
# 🆕 선행 시그널 통합
# ──────────────────────────────────────────
def detect_all_signals(df: pd.DataFrame) -> pd.DataFrame:
    H, L, C, O, V = df['High'], df['Low'], df['Close'], df['Open'], df['Volume']
    e8, e21 = df['EMA8'], df['EMA21']
    m10, m20, m50, m200 = df['MA10'], df['MA20'], df['MA50'], df['MA200']
    wt1, wt2, atr = df['WT1'], df['WT2'], df['ATR']

    # ── 공통 조건 ──
    htf_ema_bull = (e8 > e21) & (e21 > e21.shift(5))
    htf_ma_bull = (C > m50) & (m50 > m50.shift(10))
    wt_up_recent = _recent(df['WT_Up'], 2)
    wt_dn_recent = _recent(df['WT_Down'], 2)
    wt_up_wide = _recent(df['WT_Up'], 3)
    wt_dn_wide = _recent(df['WT_Down'], 3)
    vol_ok = _volf(V, 0.5)

    # 강세/약세 체제
    regime_bull = (df['ADX'] > 25) & (df['Plus_DI'] > df['Minus_DI']) & (C > m50)
    regime_bear = (df['ADX'] > 25) & (df['Minus_DI'] > df['Plus_DI']) & (C < m50)
    regime_ext_bull = regime_bull & (C > m200) & (m50 > m50.shift(5))
    regime_ext_bear = regime_bear & (C < m200) & (m50 < m50.shift(5))
    mf_positive = df['RSI_MFI'] > -10
    mf_negative = df['RSI_MFI'] < 10

    # 파라볼릭/슈퍼트렌드 오버라이드
    para_bot, para_top = _detect_parabolic_pair(C, O, wt1, df['BB_Up'], df['BB_Low'], atr)

    st_flip_bear = (df['ST_Direction'] == -1) & (df['ST_Direction'].shift(1) == 1)
    st_flip_bear.iloc[:ST_MIN_BAR] = False
    st_bear_recent = _recent(st_flip_bear, 3)

    st_flip_bull = (df['ST_Direction'] == 1) & (df['ST_Direction'].shift(1) == -1)
    st_flip_bull.iloc[:ST_MIN_BAR] = False
    st_bull_recent = _recent(st_flip_bull, 3)

    # 쉴드: 강세 체제에서 매도 억제, 약세 체제에서 매수 억제 (오버라이드 제외)
    sell_shield = regime_bull & (~para_top) & (~st_bear_recent)
    buy_shield = regime_bear & (~para_bot) & (~st_bull_recent)
    sell_shield_ext = regime_ext_bull & (~para_top) & (~st_bear_recent)
    buy_shield_ext = regime_ext_bear & (~para_bot) & (~st_bull_recent)

    # ═══════════════════════════════════
    # 🔧 FIX: MF 시그널을 여기서 한 번만 계산
    # ═══════════════════════════════════
    mf_sigs = detect_mf_signals(C, df['RSI_MFI'])
    df['MF_Cross_Bull'] = mf_sigs['MF_Cross_Bull'] & (~buy_shield) & vol_ok
    df['MF_Cross_Bear'] = mf_sigs['MF_Cross_Bear'] & (~sell_shield) & vol_ok
    df['MF_Bull_Div'] = mf_sigs['MF_Bull_Div'] & (~buy_shield) & vol_ok
    df['MF_Bear_Div'] = mf_sigs['MF_Bear_Div'] & (~sell_shield) & vol_ok
    df['MF_Accel_Up'] = mf_sigs['MF_Accel_Up']
    df['MF_Accel_Dn'] = mf_sigs['MF_Accel_Dn']
    df['MF_Slope_5'] = mf_sigs['MF_Slope_5']
    df['MF_Slope_10'] = mf_sigs['MF_Slope_10']
    df['MF_Rising'] = mf_sigs['MF_Rising']
    df['MF_Falling'] = mf_sigs['MF_Falling']
    df['MF_Strong_Up'] = mf_sigs['MF_Strong_Up']
    df['MF_Strong_Dn'] = mf_sigs['MF_Strong_Dn']
    df['MF_Up_Streak'] = mf_sigs['MF_Up_Streak']
    df['MF_Dn_Streak'] = mf_sigs['MF_Dn_Streak']

    # ═══ MCB+ 시그널 ═══
    df['Green_Dot_T1'] = (wt_up_recent & (wt1 <= OS1) & (df['RSI'] < 30) &
                          (df['MFI'] < 30) & (df['RSI_MFI'] < 0) & (~buy_shield_ext) & vol_ok)
    df['Green_Dot_T2'] = (wt_up_recent & (wt1 <= OS1) &
                          ((df['RSI'] < 32) | (df['MFI'] < 32)) &
                          ~df['Green_Dot_T1'] & (~buy_shield) & vol_ok)
    any_green = df['Green_Dot_T1'] | df['Green_Dot_T2']

    df['Red_Dot_T1'] = (wt_dn_recent & (wt1 >= OB1) & (df['RSI'] > 70) &
                        (df['MFI'] > 70) & (df['RSI_MFI'] > 0) & (~sell_shield_ext) & vol_ok)
    df['Red_Dot_T2'] = (wt_dn_recent & (wt1 >= OB1) &
                        ((df['RSI'] > 68) | (df['MFI'] > 68)) &
                        ~df['Red_Dot_T1'] & (~sell_shield) & vol_ok)
    any_red = df['Red_Dot_T1'] | df['Red_Dot_T2']

    df['Blue_Diamond'] = ((wt2 <= 0) & wt_up_recent & htf_ema_bull &
                          htf_ma_bull & (~buy_shield) & mf_positive & vol_ok)
    df['Red_Diamond'] = ((wt2 >= 0) & wt_dn_recent & ~htf_ema_bull &
                         ~htf_ma_bull & (~sell_shield) & mf_negative & vol_ok)
    df['Green_Circle'] = (wt_up_recent & (wt1 <= OS1) & ~any_green &
                          (~buy_shield) & vol_ok & (df['RSI'] < 45))
    df['Red_Circle'] = (wt_dn_recent & (wt1 >= OB1) & ~any_red &
                        (~sell_shield) & vol_ok & (df['RSI'] > 55))

    # ═══ 다이버전스 ═══
    bd, brd, hb, hbr = detect_pivot_div(C, wt1, 60, 5, OS1, OB1)
    bd_recent = _recent(bd, 3)
    brd_recent = _recent(brd, 3)
    rsi_bd, rsi_brd, _, _ = detect_pivot_div(C, df['RSI'], 60, 5, 35, 65)
    obv_bd, obv_brd, _, _ = detect_pivot_div(C, df['OBV'], 60, 5)

    df['Gold_Dot'] = df['Green_Dot_T1'] & (wt1 <= OS2) & bd_recent
    df['Blood_Diamond'] = df['Red_Dot_T1'] & (wt1 >= OB2) & brd_recent
    df['Bull_Divergence'] = bd & wt_up_wide & ~any_green & ~df['Gold_Dot'] & (~buy_shield) & vol_ok
    df['Bear_Divergence'] = brd & wt_dn_wide & ~any_red & (~sell_shield) & vol_ok
    df['RSI_Bull_Divergence'] = rsi_bd & (wt1 < -20) & (~buy_shield) & vol_ok & ~bd
    df['RSI_Bear_Divergence'] = rsi_brd & (wt1 > 20) & (~sell_shield) & vol_ok & ~brd

    vol_ok_strong = _volf(V, 0.7)
    df['Hidden_Bull_Div'] = hb & (wt1 < -25) & htf_ma_bull & (~buy_shield_ext) & vol_ok_strong
    df['Hidden_Bear_Div'] = hbr & (wt1 > 25) & ~htf_ma_bull & (~sell_shield_ext) & vol_ok_strong
    df['OBV_Div_Buy'] = obv_bd & (wt1 < -30) & (~buy_shield_ext)
    df['OBV_Div_Sell'] = obv_brd & (wt1 > 30) & (~sell_shield_ext)

    # ═══ TTM Squeeze ═══
    sqo, sqb, sqs = detect_ttm_squeeze(
        df['BB_Up'], df['BB_Low'], df['KC_Upper'], df['KC_Lower'], C, H, L, df['KC_Mid'])
    df['Squeeze_On'] = sqo
    df['Squeeze_Fire_Buy'] = sqb & (~buy_shield) & vol_ok
    df['Squeeze_Fire_Sell'] = sqs & (~sell_shield) & vol_ok

    # ═══ Volume Climax ═══
    df['Volume_Climax_Buy'], df['Volume_Climax_Sell'] = detect_volume_climax(C, O, V, wt1, atr)

    # ═══ ADX ═══
    adx_cross = (df['ADX'] > 20) & (df['ADX'].shift(1) <= 20)
    df['ADX_Momentum_Buy'] = adx_cross & (df['Plus_DI'] > df['Minus_DI']) & (wt1 > wt2) & vol_ok
    df['ADX_Momentum_Sell'] = adx_cross & (df['Minus_DI'] > df['Plus_DI']) & (wt1 < wt2) & vol_ok

    # ═══ Engulfing ═══
    df['Bullish_Engulfing'], df['Bearish_Engulfing'] = _detect_engulfing_pair(C, O, wt1)
    df['Bullish_Engulfing'] &= (~buy_shield) & vol_ok
    df['Bearish_Engulfing'] &= (~sell_shield) & vol_ok

    # ═══ Golden/Death Cross ═══
    gc = (m50 > m200) & (m50.shift(1) <= m200.shift(1))
    dc = (m50 < m200) & (m50.shift(1) >= m200.shift(1))
    adx_filter = df['ADX'] > 15
    vol_confirm = _volf(V, 0.7)
    df['Golden_Cross'] = gc & adx_filter & vol_confirm
    df['Death_Cross'] = dc & adx_filter & vol_confirm

    # ═══ EMA Pullback ═══
    df['EMA_Pullback_Buy'], df['EMA_Pullback_Sell'] = _detect_ema_pullback_pair(
        C, H, L, V, e8, e21, atr, wt1, wt2)

    # ═══ Momentum Ignition ═══
    df['Momentum_Ignition_Buy'], df['Momentum_Ignition_Sell'] = _detect_mom_ignition_pair(
        C, O, V, df['BB_Up'], df['BB_Low'], atr, e8, e21, wt1, df['BB_Width'])

    # ═══ SuperTrend ═══
    df['SuperTrend_Buy'] = st_flip_bull
    df['SuperTrend_Sell'] = st_flip_bear

    # ═══ Parabolic ═══
    vol_para = _volf(V, 1.0)
    df['Parabolic_Top_Sell'] = (para_top &
        ((df['WT_Down'] | wt_dn_wide) | ((C < O) & (C < C.shift(1)))) & vol_para)
    df['Parabolic_Bottom_Buy'] = (para_bot &
        ((df['WT_Up'] | wt_up_wide) | ((C > O) & (C > C.shift(1)))) & vol_para)

    # ═══ VWAP ═══
    df['VWAP_Bounce_Buy'], df['VWAP_Reject_Sell'] = _detect_vwap_pair(
        C, df['VWAP_Osc'], wt1, wt2, V, atr)

    # ═══ MACD / StochRSI Cross ═══
    ml, ms = df['MACD_Line'], df['MACD_Signal']
    df['MACD_Cross_Buy'] = ((ml > ms) & (ml.shift(1) <= ms.shift(1)) &
                            (ml < 0) & (~buy_shield) & vol_ok)
    df['MACD_Cross_Sell'] = ((ml < ms) & (ml.shift(1) >= ms.shift(1)) &
                             (ml > 0) & (~sell_shield) & vol_ok)
    df['StochRSI_Cross_Buy'] = ((df['StochK'] > df['StochD']) &
        (df['StochK'].shift(1) <= df['StochD'].shift(1)) &
        (df['StochK'] < 25) & (~buy_shield) & vol_ok)
    df['StochRSI_Cross_Sell'] = ((df['StochK'] < df['StochD']) &
        (df['StochK'].shift(1) >= df['StochD'].shift(1)) &
        (df['StochK'] > 75) & (~sell_shield) & vol_ok)

    # ═══ 캔들스틱 (🧹 Spinning_Top 제거됨) ═══
    (df['Hammer'], df['Shooting_Star'], df['Doji_Bullish'], df['Doji_Bearish'],
     df['Morning_Star'], df['Evening_Star']) = detect_candlestick_patterns(C, O, H, L, wt1, atr)
    df['Hammer'] &= (~buy_shield) & vol_ok
    df['Shooting_Star'] &= (~sell_shield) & vol_ok
    df['Doji_Bullish'] &= (~buy_shield) & vol_ok
    df['Doji_Bearish'] &= (~sell_shield) & vol_ok
    df['Morning_Star'] &= (~buy_shield) & vol_ok
    df['Evening_Star'] &= (~sell_shield) & vol_ok

    # ═══ Inside/Outside ═══
    df['Inside_Day'], df['Outside_Bullish'], df['Outside_Bearish'] = detect_inside_outside_day(
        H, L, C, O, wt1)
    df['Outside_Bullish'] &= (~buy_shield) & vol_ok
    df['Outside_Bearish'] &= (~sell_shield) & vol_ok

    # ═══ MA 돌파/이탈 ═══
    for k, v_sig in detect_ma_crossovers(C, m20, m50, m200).items():
        df[k] = v_sig

    # ═══ 볼린저 밴드 (🔧 반등/붕괴 분리) ═══
    (df['BB_Upper_Break'], df['BB_Lower_Bounce'], df['BB_Lower_Break'],
     df['BB_Squeeze_End_Bull'], df['BB_Squeeze_End_Bear']) = detect_bb_extra(
        C, O, df['BB_Up'], df['BB_Low'], df['BB_Width'], wt1)

    # ═══ MACD 센터라인 ═══
    df['MACD_Zero_Cross_Buy'], df['MACD_Zero_Cross_Sell'] = detect_macd_centerline(df['MACD_Line'])

    # ═══ 연속 상승/하락 ═══
    for k, v_sig in detect_consecutive_days(C).items():
        df[k] = v_sig

    # ═══ 갭 ═══
    df['Gap_Up'], df['Gap_Down'], df['Gap_Up_Closed'], df['Gap_Down_Closed'] = detect_gaps(
        C, O, H, L, atr)

    # ═══ 변동성 패턴 ═══
    df['NR7'], df['NR7_2'] = detect_nr7(H, L)
    df['Wide_Range_Bar'], df['Calm_After_Storm'] = detect_range_bars(H, L, atr)

    # ═══ 52주 ═══
    df['New_52W_High'], df['New_52W_Low'] = detect_52w(C, H, L)

    # ═══ Jeff Cooper ═══
    df['Pullback_123_Bull'], df['Pullback_123_Bear'] = detect_123_pullback(
        H, L, C, df['ADX'], df['Plus_DI'], df['Minus_DI'])
    df['Setup_180_Bull'], df['Setup_180_Bear'] = detect_180_setup(C, O, H, L, m10, m50)
    df['Boomer_Buy'], df['Boomer_Sell'] = detect_boomer(
        H, L, df['ADX'], df['Plus_DI'], df['Minus_DI'])
    df['Expansion_BO'], df['Expansion_BD'] = detect_expansion(H, L, C)
    df['Gilligans_Buy'], df['Gilligans_Sell'] = detect_gilligans(O, C, H, L)
    df['Lizard_Bull'], df['Lizard_Bear'] = detect_lizard(O, C, H, L)
    df['NonADX_123_Bull'], df['NonADX_123_Bear'] = detect_non_adx_123(H, L, C, m50)
    df['Pocket_Pivot'] = detect_pocket_pivot(C, O, V, m50, m200)

    # ═══ Ichimoku ═══
    (df['Kumo_Breakout_Bull'], df['Kumo_Breakout_Bear'],
     df['TK_Cross_Bull'], df['TK_Cross_Bear']) = detect_ichimoku_signals(
        C, df['Ichimoku_Tenkan'], df['Ichimoku_Kijun'],
        df['Ichimoku_SenkouA'], df['Ichimoku_SenkouB'])
    df['Kumo_Breakout_Bull'] &= vol_ok
    df['Kumo_Breakout_Bear'] &= vol_ok
    df['TK_Cross_Bull'] &= vol_ok
    df['TK_Cross_Bear'] &= vol_ok

    # ═══ CMF ═══
    df['CMF_Bull'], df['CMF_Bear'] = detect_cmf_signals(df['CMF'], C, m50)
    df['CMF_Bull'] &= vol_ok
    df['CMF_Bear'] &= vol_ok

    # ═══ 🆕 선행 시그널 ═══
    df = detect_anticipation_signals(df)
    # 실제 매수/매도 시그널 발생 시 셋업 시그널 비활성화
    actual_buy_fired = any_green | df['Gold_Dot'] | df['Squeeze_Fire_Buy'] | df['Bullish_Engulfing']
    actual_sell_fired = any_red | df['Blood_Diamond'] | df['Squeeze_Fire_Sell'] | df['Bearish_Engulfing']
    df['Setup_Squeeze_Bull'] &= ~actual_buy_fired
    df['Setup_Squeeze_Bear'] &= ~actual_sell_fired
    df['Momentum_Accel_Buy'] &= ~actual_buy_fired
    df['Momentum_Accel_Sell'] &= ~actual_sell_fired
    df['WT_Convergence_Bull'] &= ~df['WT_Up']   # 이미 교차 완료되면 비활성화
    df['WT_Convergence_Bear'] &= ~df['WT_Down']

    # ═══ 쿨다운 (🔧 MF 시그널은 이미 위에서 계산 → 쿨다운만 적용) ═══
    PAIRED_COOLDOWNS = {
        ('MACD_Cross_Buy', 'MACD_Cross_Sell'): 12,
        ('StochRSI_Cross_Buy', 'StochRSI_Cross_Sell'): 7,
        ('EMA_Pullback_Buy', 'EMA_Pullback_Sell'): 7,
        ('Momentum_Ignition_Buy', 'Momentum_Ignition_Sell'): 10,
        ('VWAP_Bounce_Buy', 'VWAP_Reject_Sell'): 7,
        ('ADX_Momentum_Buy', 'ADX_Momentum_Sell'): 10,
        ('Squeeze_Fire_Buy', 'Squeeze_Fire_Sell'): 5,
        ('Bullish_Engulfing', 'Bearish_Engulfing'): 5,
        ('Hammer', 'Shooting_Star'): 5,
        ('Morning_Star', 'Evening_Star'): 7,
        ('Doji_Bullish', 'Doji_Bearish'): 5,
        ('Outside_Bullish', 'Outside_Bearish'): 7,
        ('BB_Squeeze_End_Bull', 'BB_Squeeze_End_Bear'): 7,
        ('MACD_Zero_Cross_Buy', 'MACD_Zero_Cross_Sell'): 12,
        ('Pullback_123_Bull', 'Pullback_123_Bear'): 7,
        ('Setup_180_Bull', 'Setup_180_Bear'): 7,
        ('Boomer_Buy', 'Boomer_Sell'): 10,
        ('Expansion_BO', 'Expansion_BD'): 10,
        ('Gilligans_Buy', 'Gilligans_Sell'): 10,
        ('Lizard_Bull', 'Lizard_Bear'): 5,
        ('NonADX_123_Bull', 'NonADX_123_Bear'): 7,
        ('MF_Cross_Bull', 'MF_Cross_Bear'): 10,
        ('MF_Bull_Div', 'MF_Bear_Div'): 10,
        ('Kumo_Breakout_Bull', 'Kumo_Breakout_Bear'): 10,
        ('TK_Cross_Bull', 'TK_Cross_Bear'): 7,
        ('CMF_Bull', 'CMF_Bear'): 10,
        # 🆕 선행 시그널
        ('Setup_Squeeze_Bull', 'Setup_Squeeze_Bear'): 3,
        ('Momentum_Accel_Buy', 'Momentum_Accel_Sell'): 5,
        ('WT_Convergence_Bull', 'WT_Convergence_Bear'): 5,
    }

    paired_handled = set()
    for (buy_sig, sell_sig), cd in PAIRED_COOLDOWNS.items():
        _cooldown_directional(df, buy_sig, sell_sig, cd)
        paired_handled.add(buy_sig)
        paired_handled.add(sell_sig)

    for s, cd in COOLDOWN_MAP.items():
        if s in df.columns and s not in paired_handled:
            df[s] = _cooldown(df[s], cd)

    _deduplicate(df)

    # ═══ Confluence ═══
    compute_confluence(df)

    # ═══ Proximity (🔧 가속도 + 수렴 반영) ═══
    df['Buy_Proximity'], df['Sell_Proximity'] = compute_proximity(df)

    # ═══ 메타 컬럼 ═══
    df['Strong_Bull'] = regime_bull
    df['Strong_Bear'] = regime_bear
    df['Parabolic_Blowoff'] = para_top
    df['Parabolic_Bottom_Raw'] = para_bot
    df['ST_Bear_Override'] = st_bear_recent
    df['Sell_Shield_Overridden'] = para_top | st_bear_recent
    df['Buy_Shield_Overridden'] = para_bot | st_bull_recent
    df['_HTF1_Bull'] = htf_ema_bull
    df['_HTF2_Bull'] = htf_ma_bull

    df = detect_scanner_combos(df)

    # ═══ 8-Layer 판단 엔진 ═══
    compute_trade_judgment(df)

    return df


# ──────────────────────────────────────────
# Confluence (변경 없음 — 선행 시그널 자동 포함)
# ──────────────────────────────────────────
def compute_confluence(df, dw=5, df_=0.75):
    bm = {k: v['w'] for k, v in SIGNAL_REGISTRY.items() if v['dir'] == 'buy'}
    sm = {k: v['w'] for k, v in SIGNAL_REGISTRY.items() if v['dir'] == 'sell'}
    dk = np.array([df_**i for i in range(dw + 1)])
    ones = np.ones(dw + 1)
    s = np.zeros(len(df))
    bc = np.zeros(len(df))
    sc = np.zeros(len(df))
    for col, w in bm.items():
        if col in df.columns:
            raw = df[col].fillna(False).astype(float).values
            s += np.convolve(raw * w, dk, mode='full')[:len(raw)]
            bc += np.convolve(raw, ones, mode='full')[:len(raw)]
    for col, w in sm.items():
        if col in df.columns:
            raw = df[col].fillna(False).astype(float).values
            s -= np.convolve(raw * w, dk, mode='full')[:len(raw)]
            sc += np.convolve(raw, ones, mode='full')[:len(raw)]
    wt1 = df['WT1'].values
    s += np.where(wt1 < OS1, 1.0, 0) + np.where(wt1 < OS2, 0.5, 0)
    s -= np.where(wt1 > OB1, 1.0, 0) + np.where(wt1 > OB2, 0.5, 0)
    adx = df['ADX'].values
    pdi = df['Plus_DI'].values
    mdi = df['Minus_DI'].values
    af = np.clip((adx - 20) / 100, 0.0, 0.3)
    s += np.where((pdi > mdi) & (s > 0), s * af, 0)
    s -= np.where((mdi > pdi) & (s < 0), abs(s) * af, 0)
    df['Confluence_Score'] = s
    df['Ultra_Buy'] = (s >= 6.5) | ((s >= 5) & (bc >= 3))
    df['Ultra_Sell'] = (s <= -6.5) | ((s <= -5) & (sc >= 3))
    df['Strong_Buy'] = (s >= 3.5) & (~df['Ultra_Buy'])
    df['Strong_Sell'] = (s <= -3.5) & (~df['Ultra_Sell'])
    return s


# ──────────────────────────────────────────
# Proximity (🔧 가속도 + 수렴 속도 반영)
# ──────────────────────────────────────────
def compute_proximity(df: pd.DataFrame):
    """🔧 선행 지표를 반영하여 예측력 향상"""
    wt1 = df['WT1']
    wt2 = df['WT2']
    rsi = df['RSI']
    mfi = df['MFI']
    rmfi = df['RSI_MFI']
    stk = df['StochK']
    macd_h = df['MACD_Hist']
    bb_w = df['BB_Width']
    regime_bull = df.get('Strong_Bull', pd.Series(False, index=df.index))
    regime_bear = df.get('Strong_Bear', pd.Series(False, index=df.index))

    bp = pd.Series(0.0, index=df.index)
    sp = pd.Series(0.0, index=df.index)

    gap = (wt1 - wt2).abs()
    near_cross = gap < 3
    converging_up = (wt1 - wt2) > (wt1.shift(1) - wt2.shift(1))
    converging_dn = (wt1 - wt2) < (wt1.shift(1) - wt2.shift(1))

    # ── 매수 근접도 ──
    for cond, pts in [
        ((wt1 < -40) & near_cross, 30), ((wt1 < -40) & converging_up & (gap < 8), 15),
        (wt1 < OS2, 20), ((wt1 >= OS2) & (wt1 < -40), 10),
        (rsi < 35, 15), ((rsi >= 35) & (rsi < 45), 5),
        (mfi < 35, 15), ((mfi >= 35) & (mfi < 45), 5),
        (rmfi < -5, 10), ((rmfi >= -5) & (rmfi < 0), 5),
        (rmfi > rmfi.shift(1), 5), (rmfi > rmfi.shift(3), 3),
        (stk < 20, 10), ((stk >= 20) & (stk < 35), 5),
        (macd_h < 0, 3), (macd_h > macd_h.shift(1), 2),
    ]:
        bp += np.where(cond, pts, 0)

    # ── 매도 근접도 ──
    for cond, pts in [
        ((wt1 > 40) & near_cross, 30), ((wt1 > 40) & converging_dn & (gap < 8), 15),
        (wt1 > OB1, 20), ((wt1 <= OB1) & (wt1 > 40), 10),
        (rsi > 65, 15), ((rsi <= 65) & (rsi > 55), 5),
        (mfi > 65, 15), ((mfi <= 65) & (mfi > 55), 5),
        (rmfi > 5, 10), ((rmfi <= 5) & (rmfi > 0), 5),
        (rmfi < rmfi.shift(1), 5), (rmfi < rmfi.shift(3), 3),
        (stk > 80, 10), ((stk <= 80) & (stk > 65), 5),
        (macd_h > 0, 3), (macd_h < macd_h.shift(1), 2),
    ]:
        sp += np.where(cond, pts, 0)

    # 🆕 선행 지표 보너스
    comp_accel = df.get('Composite_Accel', pd.Series(0, index=df.index))
    conv_speed = df.get('WT_Conv_Speed', pd.Series(0, index=df.index))
    setup_buy = df.get('Setup_Pressure_Buy', pd.Series(0, index=df.index))
    setup_sell = df.get('Setup_Pressure_Sell', pd.Series(0, index=df.index))

    # 모멘텀 가속도 (양의 가속 = 매수 임박, 음의 가속 = 매도 임박)
    bp += np.where(comp_accel > JT.ACCEL_STRONG, 15,
          np.where(comp_accel > JT.ACCEL_MODERATE, 8,
          np.where(comp_accel > 0.5, 3, 0)))
    sp += np.where(comp_accel < -JT.ACCEL_STRONG, 15,
          np.where(comp_accel < -JT.ACCEL_MODERATE, 8,
          np.where(comp_accel < -0.5, 3, 0)))

    # WT 수렴 속도
    bp += np.where(df.get('WT_Conv_Bull', pd.Series(False, index=df.index)), 10, 0)
    sp += np.where(df.get('WT_Conv_Bear', pd.Series(False, index=df.index)), 10, 0)

    # 셋업 축적 점수
    bp += np.where(setup_buy >= 8, 10, np.where(setup_buy >= 5, 5, 0))
    sp += np.where(setup_sell >= 8, 10, np.where(setup_sell >= 5, 5, 0))

    # BB 스퀴즈
    bb_narrow = bb_w < bb_w.rolling(50, min_periods=10).quantile(0.2)
    bp += np.where(bb_narrow, 5, 0)
    sp += np.where(bb_narrow, 5, 0)

    bp, sp = bp.clip(upper=100), sp.clip(upper=100)
    net = bp - sp

    return (pd.Series(np.where(net >= 0, bp, bp * np.where(regime_bear, .4, .55)), index=df.index),
            pd.Series(np.where(net <= 0, sp, sp * np.where(regime_bull, .4, .55)), index=df.index))


# ──────────────────────────────────────────
# 콤보 감지 (🔧 등급별 보너스 차등화)
# ──────────────────────────────────────────
def detect_combos(df: pd.DataFrame, vol_ratio: pd.Series):
    C, idx = df['Close'], df.index
    F = lambda col: df.get(col, pd.Series(False, index=idx))

    trend_up = (C > df['MA200']) & (C > df['MA50']) & (df['MA50'] > df['MA200'])
    trend_dn = (C < df['MA200']) & (C < df['MA50']) & (df['MA50'] < df['MA200'])
    candle_bull = F('Bullish_Engulfing') | F('Hammer') | F('Morning_Star') | F('Doji_Bullish')
    candle_bear = F('Bearish_Engulfing') | F('Shooting_Star') | F('Evening_Star') | F('Doji_Bearish')
    timing_bull = ((df['StochK'] < 20) | F('StochRSI_Cross_Buy') |
                   F('MACD_Cross_Buy') | (df['WT1'] < -30))
    timing_bear = ((df['StochK'] > 80) | F('StochRSI_Cross_Sell') |
                   F('MACD_Cross_Sell') | (df['WT1'] > 30))
    vol_confirm = vol_ratio >= 1.5
    squeeze_state = (F('NR7') | F('NR7_2') | F('Inside_Day') | F('Calm_After_Storm') |
                     (df['BB_Width'] <= df['BB_Width'].rolling(120, min_periods=20).quantile(0.1)))

    mf_bull = (df['RSI_MFI'] > df['RSI_MFI'].shift(1)) | (df['RSI_MFI'] > 0)
    mf_bear = (df['RSI_MFI'] < df['RSI_MFI'].shift(1)) | (df['RSI_MFI'] < 0)
    mf_strong_bull = F('MF_Strong_Up') | (df.get('MF_Slope_5', pd.Series(0, index=idx)) > 3)
    mf_strong_bear = F('MF_Strong_Dn') | (df.get('MF_Slope_5', pd.Series(0, index=idx)) < -3)

    cmf = df.get('CMF', pd.Series(0, index=idx))
    cmf_bull_cond = cmf > 0.05
    cmf_bear_cond = cmf < -0.05

    ma_support = ((C - df['MA50']).abs() <= df['ATR'] * 1.5) | ((C - df['MA20']).abs() <= df['ATR'] * 1.0)

    # 🆕 선행 조건
    antic_bull = (df.get('Setup_Pressure_Buy', pd.Series(0, index=idx)) >= 5)
    antic_bear = (df.get('Setup_Pressure_Sell', pd.Series(0, index=idx)) >= 5)

    # ═══ BUY 콤보 (🔧 등급 부여: Tier1/2/3) ═══
    # Tier 1: 3+ 독립 확인 (추세+캔들+거래량+자금흐름)
    df['Combo_TrendPullback_Buy'] = (
        trend_up & (C < df['MA20']) & ma_support &
        (candle_bull | timing_bull) & mf_bull & (df['BJ_Trend'] >= 5)
        if 'BJ_Trend' in df.columns else
        trend_up & (C < df['MA20']) & ma_support & (candle_bull | timing_bull) & mf_bull)
    df['Combo_Tier_TrendPullback_Buy'] = 2  # 기본 Tier 2

    df['Combo_VolSqueeze_Buy'] = (
        squeeze_state.shift(1).fillna(False) & (C > df['MA50']) &
        (F('BB_Squeeze_End_Bull') | (F('Wide_Range_Bar') & (C > df['Open']))) &
        vol_confirm & mf_bull)
    df['Combo_Tier_VolSqueeze_Buy'] = 2

    oversold_ext = (((df['StochK'] < 20) & (df['StochD'] < 20)).astype(int) +
                    (df['RSI'] < 30).astype(int) + (df['WT1'] < -53).astype(int)) >= 2
    df['Combo_Reversal_Buy'] = (
        oversold_ext & ((C > df['MA200']) | (df['MA50'] > df['MA200'])) &
        (candle_bull | F('Gold_Dot') | F('Green_Dot_T1') | F('Lizard_Bull') | F('Gilligans_Buy')))
    df['Combo_Tier_Reversal_Buy'] = 1  # Tier 1: 극단적 과매도 + 캔들 확인

    df['Combo_Momentum_Buy'] = (
        (F('New_52W_High') | F('Expansion_BO')) &
        (vol_confirm | F('Pocket_Pivot') | F('Momentum_Ignition_Buy')) &
        (df['ADX'] > 25) & (df['Plus_DI'] > df['Minus_DI']) & mf_strong_bull)
    df['Combo_Tier_Momentum_Buy'] = 1

    df['Combo_MAConfluence_Buy'] = (
        (df['MA50'] > df['MA200']) & (C > df['MA200']) &
        (F('Cross_Above_20MA') | F('Cross_Above_50MA')) &
        (F('MACD_Cross_Buy') | F('StochRSI_Cross_Buy') | F('NonADX_123_Bull')) & mf_bull)
    df['Combo_Tier_MAConfluence_Buy'] = 2

    df['Combo_MF_Reversal_Buy'] = (
        F('MF_Cross_Bull') & (df['WT1'] < 20) & (C > df['MA50']) &
        (candle_bull | timing_bull | vol_confirm))
    df['Combo_Tier_MF_Reversal_Buy'] = 3

    df['Combo_Ichimoku_Buy'] = (
        F('Kumo_Breakout_Bull') & (candle_bull | timing_bull | vol_confirm) &
        cmf_bull_cond & (df['ADX'] > 20))
    df['Combo_Tier_Ichimoku_Buy'] = 2

    # 🆕 선행 콤보: 셋업 축적 + 방향 힌트
    df['Combo_Anticipation_Buy'] = (
        antic_bull & squeeze_state & (cmf_bull_cond | mf_bull) &
        (F('WT_Convergence_Bull') | F('Momentum_Accel_Buy') | F('Setup_Squeeze_Bull')))
    df['Combo_Tier_Anticipation_Buy'] = 3

    # ═══ SELL 콤보 ═══
    df['Combo_TrendRejection_Sell'] = (
        trend_dn & (C > df['MA20']) &
        (candle_bear | timing_bear) & mf_bear)
    df['Combo_Tier_TrendRejection_Sell'] = 2

    overbought_ext = (((df['StochK'] > 80) & (df['StochD'] > 80)).astype(int) +
                      (df['RSI'] > 70).astype(int) + (df['WT1'] > 53).astype(int)) >= 2
    df['Combo_Exhaustion_Sell'] = (
        overbought_ext &
        (candle_bear | F('Gilligans_Sell') | F('Blood_Diamond') |
         F('Red_Dot_T1') | F('Parabolic_Top_Sell')))
    df['Combo_Tier_Exhaustion_Sell'] = 1

    ma_break = (F('Fell_Below_20MA').astype(int) + F('Fell_Below_50MA').astype(int) +
                F('Fell_Below_200MA').astype(int) + F('Death_Cross').astype(int)) >= 1
    df['Combo_MABreakdown_Sell'] = (
        ma_break & (vol_confirm | F('MACD_Zero_Cross_Sell') |
                     (F('Wide_Range_Bar') & (C < df['Open']))) & mf_bear)
    df['Combo_Tier_MABreakdown_Sell'] = 2

    df['Combo_VolSqueeze_Sell'] = (
        squeeze_state.shift(1).fillna(False) & (C < df['MA50']) &
        (F('BB_Squeeze_End_Bear') | (F('Wide_Range_Bar') & (C < df['Open']))) &
        vol_confirm & mf_bear)
    df['Combo_Tier_VolSqueeze_Sell'] = 2

    gap_up_fail = F('Gap_Up').shift(1).fillna(False) & (C < df['Open']) & (candle_bear | F('Gilligans_Sell'))
    df['Combo_GapFailure_Sell'] = (
        gap_up_fail | (F('Gap_Down') & vol_confirm & (F('Fell_Below_50MA') | F('Fell_Below_200MA'))))
    df['Combo_Tier_GapFailure_Sell'] = 2

    df['Combo_MF_Reversal_Sell'] = (
        F('MF_Cross_Bear') & (df['WT1'] > -20) & (C < df['MA50']) &
        (candle_bear | timing_bear | vol_confirm))
    df['Combo_Tier_MF_Reversal_Sell'] = 3

    df['Combo_Ichimoku_Sell'] = (
        F('Kumo_Breakout_Bear') & (candle_bear | timing_bear | vol_confirm) &
        cmf_bear_cond & (df['ADX'] > 20))
    df['Combo_Tier_Ichimoku_Sell'] = 2

    # 🆕 선행 매도 콤보
    df['Combo_Anticipation_Sell'] = (
        antic_bear & squeeze_state & (cmf_bear_cond | mf_bear) &
        (F('WT_Convergence_Bear') | F('Momentum_Accel_Sell') | F('Setup_Squeeze_Bear')))
    df['Combo_Tier_Anticipation_Sell'] = 3


COMBO_MAP = {
    'Combo_TrendPullback_Buy':   ('🎯 추세 눌림목 매수', 'buy', 2),
    'Combo_VolSqueeze_Buy':      ('💥 변동성 수축 돌파', 'buy', 2),
    'Combo_Reversal_Buy':        ('🔄 반전 매수', 'buy', 1),
    'Combo_Momentum_Buy':        ('🚀 모멘텀 돌파', 'buy', 1),
    'Combo_MAConfluence_Buy':    ('📊 MA 합류 매수', 'buy', 2),
    'Combo_MF_Reversal_Buy':     ('💰 자금흐름 전환 매수', 'buy', 3),
    'Combo_Ichimoku_Buy':        ('☁️ 쿠모 돌파 매수', 'buy', 2),
    'Combo_Anticipation_Buy':    ('⏳ 매수 셋업 임박', 'buy', 3),       # 🆕
    'Combo_TrendRejection_Sell': ('🎯 추세 반등 실패', 'sell', 2),
    'Combo_Exhaustion_Sell':     ('🌡️ 고점 소진', 'sell', 1),
    'Combo_MABreakdown_Sell':    ('📉 MA 붕괴', 'sell', 2),
    'Combo_VolSqueeze_Sell':     ('💨 변동성 수축 붕괴', 'sell', 2),
    'Combo_GapFailure_Sell':     ('⏬ 갭 실패', 'sell', 2),
    'Combo_MF_Reversal_Sell':    ('💸 자금흐름 전환 매도', 'sell', 3),
    'Combo_Ichimoku_Sell':       ('☁️ 쿠모 하향 매도', 'sell', 2),
    'Combo_Anticipation_Sell':   ('⏳ 매도 셋업 임박', 'sell', 3),       # 🆕
}


# ──────────────────────────────────────────
# 🔧 8-Layer 판단 엔진
# 🆕 Layer 8: Anticipation (선행 지표)
# 🔧 FIX: 음수 정보 보존 (contra_penalty)
# 🔧 FIX: 콤보 등급별 차등 보너스
# ──────────────────────────────────────────
def compute_trade_judgment(df: pd.DataFrame) -> pd.DataFrame:
    C, O, H, L, idx = df['Close'], df['Open'], df['High'], df['Low'], df.index
    rmfi = df['RSI_MFI']
    vol_ratio = df['Volume'] / (df['Volume'].rolling(50, min_periods=10).mean() + 1e-10)
    atr = df['ATR']

    # ═══ 공통 계산 ═══
    above_200 = C > df['MA200']
    above_50 = C > df['MA50']
    above_20 = C > df['MA20']
    below_200 = C < df['MA200']
    below_50 = C < df['MA50']
    ma50_rising = df['MA50'] > df['MA50'].shift(5)
    ma50_falling = df['MA50'] < df['MA50'].shift(5)

    macd_h = df['MACD_Hist']
    macd_h_rising = macd_h > macd_h.shift(1)
    macd_h_falling = macd_h < macd_h.shift(1)
    macd_gap = df['MACD_Line'] - df['MACD_Signal']
    macd_accel = macd_gap > macd_gap.shift(1)
    macd_decel = macd_gap < macd_gap.shift(1)

    rsi_rising = df['RSI'] > df['RSI'].shift(1)
    rsi_falling = df['RSI'] < df['RSI'].shift(1)
    stk_rising = df['StochK'] > df['StochK'].shift(1)
    wt_rising = df['WT1'] > df['WT1'].shift(1)
    wt_falling = df['WT1'] < df['WT1'].shift(1)

    obv = df['OBV']
    obv_ma20 = obv.rolling(20, min_periods=10).mean()
    obv_above = obv > obv_ma20
    obv_below = obv < obv_ma20

    bull_vol = df['Volume'].where(C > O, 0)
    bear_vol = df['Volume'].where(C < O, 0)
    avg_bull_vol = bull_vol.rolling(10, min_periods=5).mean()
    avg_bear_vol = bear_vol.rolling(10, min_periods=5).mean()
    vol_bull_ratio = avg_bull_vol / (avg_bear_vol + 1e-10)

    vwap_osc = df['VWAP_Osc']
    body = (C - O).abs()
    body_atr_ratio = body / (atr + 1e-10)

    in_downtrend = below_50 | (df['WT1'] < -20) | (df['RSI'] < 45)
    in_uptrend = above_50 | (df['WT1'] > 20) | (df['RSI'] > 55)

    wt_cross_up = df.get('WT_Up', pd.Series(False, index=idx))
    wt_cross_dn = df.get('WT_Down', pd.Series(False, index=idx))
    squeeze_on = df.get('Squeeze_On', pd.Series(False, index=idx))
    pct_b = df['Percent_B']

    kumo_top = pd.concat([df.get('Ichimoku_SenkouA', pd.Series(0, index=idx)),
                           df.get('Ichimoku_SenkouB', pd.Series(0, index=idx))], axis=1).max(axis=1)
    kumo_bot = pd.concat([df.get('Ichimoku_SenkouA', pd.Series(0, index=idx)),
                           df.get('Ichimoku_SenkouB', pd.Series(0, index=idx))], axis=1).min(axis=1)
    above_kumo = C > kumo_top
    below_kumo = C < kumo_bot
    cmf = df.get('CMF', pd.Series(0, index=idx))
    tk_above = df.get('Ichimoku_Tenkan', pd.Series(0, index=idx)) > df.get('Ichimoku_Kijun', pd.Series(0, index=idx))
    tk_below = df.get('Ichimoku_Tenkan', pd.Series(0, index=idx)) < df.get('Ichimoku_Kijun', pd.Series(0, index=idx))

    # NR7 공통
    nr7_val = _sig_pts(df, 'NR7', 1.0)
    nr72_val = _sig_pts(df, 'NR7_2', 1.5)
    calm_val = _sig_pts(df, 'Calm_After_Storm', 1.0)

    # ══════════════════ BUY ══════════════════

    # ── Layer 1: 추세 ──
    bt = pd.Series(0.0, index=idx)
    bt += np.where(above_200 & above_50 & above_20, 5.0,
          np.where(above_200 & above_50, 4.0,
          np.where(above_200, 2.5,
          np.where(above_50, 1.5, 0))))
    bt += np.where(df['MA50'] > df['MA200'], 1.5, 0)
    bt += np.where(df['Plus_DI'] > df['Minus_DI'], 1.0, 0)
    bt += np.where(df['ST_Direction'] == 1, 1.0, 0)
    bt += np.where(above_50 & ma50_rising, 0.5, 0)
    bt += _sig_pts(df, 'Cross_Above_50MA', 1.0)
    bt += _sig_pts(df, 'Cross_Above_200MA', 1.5)
    bt += _sig_pts(df, 'Golden_Cross', 1.5)
    bt += np.where(above_kumo, 1.5, 0)
    bt += np.where(above_kumo & tk_above, 0.5, 0)
    # 🔧 역방향 페널티 (음수 보존)
    bt += np.where(below_200 & below_50, -2.0, 0)
    bt += np.where(df['ST_Direction'] == -1, -0.5, 0)
    df['BJ_Trend'] = bt.clip(lower=-2, upper=JT.TREND_CAP)

    # ── Layer 2: 모멘텀 ──
    bm = pd.Series(0.0, index=idx)

    # Part A: 크로스오버 (캡 적용)
    bm_cross = pd.Series(0.0, index=idx)
    for s, p in [('MACD_Cross_Buy', 2.5), ('MACD_Zero_Cross_Buy', 2.0),
                  ('StochRSI_Cross_Buy', 2.0), ('ADX_Momentum_Buy', 2.0),
                  ('VWAP_Bounce_Buy', 1.5)]:
        bm_cross += _sig_pts(df, s, p)
    bm += bm_cross.clip(upper=JT.CROSS_SIGNAL_CAP)

    # Part B: MACD 히스토그램
    bm += np.select([(macd_h > 0) & macd_h_rising, (macd_h > 0) & macd_h_falling,
                      (macd_h < 0) & macd_h_rising],
                     [2.0, 0.5, 1.5], default=0.0)
    bm += np.where((macd_h > 0) & macd_accel, 0.5, 0)

    # Part C: VWAP
    bm += np.select([vwap_osc > 3.0, vwap_osc > 1.0, vwap_osc > 0],
                     [1.5, 1.0, 0.5], default=0.0)

    # Part D: RSI
    bm += np.select([
        (df['RSI'] < 30) & rsi_rising, df['RSI'] < 30,
        (df['RSI'] < 45) & rsi_rising,
        (df['RSI'] > 70) & rsi_falling, (df['RSI'] > 70) & rsi_rising,
    ], [3.0, 1.5, 1.0, -1.5, -0.5], default=0.0)

    # Part E: StochK
    bm += np.select([
        (df['StochK'] < 20) & stk_rising, df['StochK'] < 20,
        (df['StochK'] > 80) & ~stk_rising,
    ], [2.5, 1.0, -1.0], default=0.0)

    # Part F: WaveTrend
    bm += np.select([
        (df['WT1'] < OS1) & (wt_cross_up | wt_rising), df['WT1'] < OS1,
        (df['WT1'] < -20) & wt_rising, (df['WT1'] > OB1) & wt_falling,
    ], [3.0, 1.0, 1.0, -1.5], default=0.0)

    df['BJ_Momentum'] = bm.clip(lower=-2, upper=JT.MOMENTUM_CAP)  # 🔧 음수 하한

    # ── Layer 3: 캔들 ──
    bc_candidates = []
    for sig_name, base_pts, trend_pts in [
        ('Morning_Star', 2.5, 3.5), ('Bullish_Engulfing', 2.0, 3.0),
        ('Hammer', 1.5, 2.5), ('Outside_Bullish', 1.5, 2.5), ('Doji_Bullish', 0.5, 1.0),
    ]:
        raw = df.get(sig_name, pd.Series(False, index=idx)).fillna(False)
        if sig_name == 'Bullish_Engulfing':
            pts = np.where(raw & in_downtrend & (body_atr_ratio > 1.0), 3.5,
                  np.where(raw & in_downtrend, trend_pts,
                  np.where(raw & (body_atr_ratio > 1.0), 2.5,
                  np.where(raw, base_pts, 0))))
        else:
            pts = np.where(raw & in_downtrend, trend_pts, np.where(raw, base_pts, 0))
        bc_candidates.append(pts)
    bc = pd.Series(np.stack(bc_candidates).max(axis=0), index=idx) if bc_candidates else pd.Series(0.0, index=idx)
    df['BJ_Candle'] = bc.clip(upper=JT.CANDLE_CAP)

    # ── Layer 4: BB ──
    bb = pd.Series(0.0, index=idx)
    bb += _sig_pts(df, 'BB_Squeeze_End_Bull', 3.0)
    bb += nr7_val + nr72_val + calm_val
    bb += np.where(squeeze_on & above_50, 1.0, 0)
    bb += np.select([pct_b < 0.05, pct_b < 0.2,
                      (pct_b >= 0.4) & (pct_b <= 0.6) & above_50, pct_b > 0.95],
                     [2.5, 1.5, 0.5, -1.5], default=0.0)
    # 🔧 BB 하단 반등 = 매수 기회
    bb += _sig_pts(df, 'BB_Lower_Bounce', 2.0)
    bb += np.where(df.get('BB_Lower_Break', pd.Series(False, index=idx)).fillna(False), -1.0, 0)
    df['BJ_BB'] = bb.clip(lower=-1, upper=JT.BB_CAP)

    # ── Layer 5: Volume ──
    bv = pd.Series(0.0, index=idx)
    bv += _sig_pts(df, 'Volume_Climax_Buy', 3.0)
    bv += _sig_pts(df, 'Pocket_Pivot', 2.0)
    bv += _sig_pts(df, 'OBV_Div_Buy', 1.5)
    bv += np.where((vol_ratio >= 3.0) & (C > O), 2.5,
          np.where((vol_ratio >= 1.5) & (C > O), 1.0, 0))
    bv += np.where(obv_above & (obv > obv.shift(5)), 1.5,
          np.where(obv_above, 0.5, 0))
    bv += np.where(obv_below & (obv < obv.shift(5)), -1.0, 0)
    bv += np.select([vol_bull_ratio > 2.0, vol_bull_ratio > 1.3, vol_bull_ratio < 0.5],
                     [1.5, 0.5, -1.0], default=0.0)
    vol_dry = vol_ratio < 0.5
    vol_dry_streak = _vectorized_streak(vol_dry)
    bv += np.where((vol_dry_streak >= 3) & above_50 & squeeze_on, 1.0, 0)
    df['BJ_Volume'] = bv.clip(lower=-1, upper=JT.VOLUME_CAP)

    # ── Layer 6: 자금흐름 ──
    bmf = pd.Series(0.0, index=idx)
    bmf += np.select([rmfi < -10, rmfi < -5, rmfi > 10],
                      [2.0, 1.0, -0.5], default=0.0)
    if 'MF_Slope_5' in df.columns:
        mf_slope = df['MF_Slope_5']
        bmf += np.select([mf_slope > 5, mf_slope > 2, mf_slope > 0, mf_slope < -5],
                          [2.0, 1.5, 0.5, -1.0], default=0.0)
    if 'MF_Up_Streak' in df.columns:
        bmf += np.select([df['MF_Up_Streak'] >= 5, df['MF_Up_Streak'] >= 3],
                          [2.0, 1.0], default=0.0)
    bmf += _sig_pts(df, 'MF_Cross_Bull', 2.0)
    bmf += _sig_pts(df, 'MF_Bull_Div', 2.0)
    bmf += _sig_pts(df, 'MF_Accel_Up', 1.0)
    bmf += np.where(cmf > 0.15, 1.5, np.where(cmf > 0.05, 0.5, np.where(cmf < -0.15, -1.0, 0)))
    bmf += _sig_pts(df, 'CMF_Bull', 1.5)
    df['BJ_MF'] = bmf.clip(lower=-1, upper=JT.MF_CAP)

    # ── Layer 7: Pattern ──
    bp = pd.Series(0.0, index=idx)
    gold = _sig_pts(df, 'Gold_Dot', 4.0)
    gdt1 = np.where(gold == 0, _sig_pts(df, 'Green_Dot_T1', 2.5), 0)
    gdt2 = np.where((gold == 0) & (gdt1 == 0), _sig_pts(df, 'Green_Dot_T2', 2.0), 0)
    bp += gold + gdt1 + gdt2

    bd_pts = np.where(gold == 0, _sig_pts(df, 'Bull_Divergence', 2.0), 0)
    bp += bd_pts

    for s, p in [('Pullback_123_Bull', 2.5), ('Setup_180_Bull', 2.0), ('Boomer_Buy', 2.0),
                  ('Expansion_BO', 3.0), ('Gilligans_Buy', 2.5), ('Lizard_Bull', 2.0),
                  ('NonADX_123_Bull', 1.5), ('EMA_Pullback_Buy', 2.0),
                  ('Momentum_Ignition_Buy', 3.0), ('SuperTrend_Buy', 2.0),
                  ('Gap_Up', 1.0), ('Gap_Down_Closed', 1.0),
                  ('New_52W_High', 2.0), ('Blue_Diamond', 2.0),
                  ('Hidden_Bull_Div', 1.5), ('Squeeze_Fire_Buy', 2.0),
                  ('Parabolic_Bottom_Buy', 3.0), ('Pocket_Pivot', 2.0),
                  ('Kumo_Breakout_Bull', 2.5), ('TK_Cross_Bull', 1.5)]:
        bp += _sig_pts(df, s, p)

    # 패턴 감쇠
    for s, decay_pts in [('Gold_Dot', 2.0), ('Green_Dot_T1', 1.0), ('Expansion_BO', 1.5),
                          ('Momentum_Ignition_Buy', 1.5), ('Parabolic_Bottom_Buy', 1.5),
                          ('Kumo_Breakout_Bull', 1.0)]:
        if s in df.columns:
            yesterday = df[s].shift(1).fillna(False)
            bp += np.where(yesterday & ~df[s], decay_pts * 0.5, 0)

    df['BJ_Pattern'] = bp.clip(upper=JT.PATTERN_CAP)

    # ── 🆕 Layer 8: Anticipation (선행 지표) ──
    ba = pd.Series(0.0, index=idx)
    setup_buy = df.get('Setup_Pressure_Buy', pd.Series(0, index=idx))
    comp_accel = df.get('Composite_Accel', pd.Series(0, index=idx))

    # 셋업 축적 점수
    ba += np.where(setup_buy >= 8, 3.0,
          np.where(setup_buy >= 5, 2.0,
          np.where(setup_buy >= 3, 1.0, 0)))

    # 모멘텀 가속도
    ba += np.where(comp_accel > JT.ACCEL_STRONG, 2.5,
          np.where(comp_accel > JT.ACCEL_MODERATE, 1.5,
          np.where(comp_accel > 0.5, 0.5, 0)))
    # 역방향 감속: 매도 모멘텀 감속 = 매수에 유리
    ba += np.where(comp_accel < -JT.ACCEL_MODERATE, -1.0, 0)

    # WT 수렴
    ba += np.where(df.get('WT_Conv_Bull', pd.Series(False, index=idx)), 2.0, 0)

    # 선행 시그널
    ba += _sig_pts(df, 'Setup_Squeeze_Bull', 1.5)
    ba += _sig_pts(df, 'Momentum_Accel_Buy', 2.0)
    ba += _sig_pts(df, 'WT_Convergence_Bull', 1.5)
    ba += _sig_pts(df, 'Volume_Dry_Up', 0.5)

    df['BJ_Anticipation'] = ba.clip(lower=-1, upper=JT.ANTICIPATION_CAP)

    # ── BUY 합산 ──
    df['Buy_Total'] = (df['BJ_Trend'] + df['BJ_Momentum'] + df['BJ_Candle'] +
                       df['BJ_BB'] + df['BJ_Volume'] + df['BJ_MF'] +
                       df['BJ_Pattern'] + df['BJ_Anticipation'])

    # ══════════════════ SELL ══════════════════

    # ── Layer 1: 추세 ──
    st_ = pd.Series(0.0, index=idx)
    st_ += np.where(below_200 & below_50 & (C < df['MA20']), 5.0,
           np.where(below_200 & below_50, 4.0,
           np.where(below_200, 2.5,
           np.where(below_50, 1.5, 0))))
    st_ += np.where(df['MA50'] < df['MA200'], 1.5, 0)
    st_ += np.where(df['Minus_DI'] > df['Plus_DI'], 1.0, 0)
    st_ += np.where(df['ST_Direction'] == -1, 1.0, 0)
    st_ += np.where(below_50 & ma50_falling, 0.5, 0)
    st_ += _sig_pts(df, 'Fell_Below_50MA', 1.0)
    st_ += _sig_pts(df, 'Fell_Below_200MA', 1.5)
    st_ += _sig_pts(df, 'Death_Cross', 1.5)
    st_ += np.where(below_kumo, 1.5, 0)
    st_ += np.where(below_kumo & tk_below, 0.5, 0)
    st_ += np.where(above_200 & above_50, -2.0, 0)
    st_ += np.where(df['ST_Direction'] == 1, -0.5, 0)
    df['SJ_Trend'] = st_.clip(lower=-2, upper=JT.TREND_CAP)

    # ── Layer 2: 모멘텀 ──
    sm = pd.Series(0.0, index=idx)
    sm_cross = pd.Series(0.0, index=idx)
    for s, p in [('MACD_Cross_Sell', 2.5), ('MACD_Zero_Cross_Sell', 2.0),
                  ('StochRSI_Cross_Sell', 2.0), ('ADX_Momentum_Sell', 2.0),
                  ('VWAP_Reject_Sell', 1.5)]:
        sm_cross += _sig_pts(df, s, p)
    sm += sm_cross.clip(upper=JT.CROSS_SIGNAL_CAP)

    sm += np.select([(macd_h < 0) & macd_h_falling, (macd_h < 0) & macd_h_rising,
                      (macd_h > 0) & macd_h_falling],
                     [2.0, 0.5, 1.5], default=0.0)
    sm += np.where((macd_h < 0) & macd_decel, 0.5, 0)
    sm += np.select([vwap_osc < -3.0, vwap_osc < -1.0, vwap_osc < 0],
                     [1.5, 1.0, 0.5], default=0.0)
    sm += np.select([
        (df['RSI'] > 70) & rsi_falling, df['RSI'] > 70,
        (df['RSI'] > 55) & rsi_falling,
        (df['RSI'] < 30) & rsi_rising, (df['RSI'] < 30) & ~rsi_rising,
    ], [3.0, 1.5, 1.0, -1.5, -0.5], default=0.0)
    sm += np.select([
        (df['StochK'] > 80) & ~stk_rising, df['StochK'] > 80,
        (df['StochK'] < 20) & stk_rising,
    ], [2.5, 1.0, -1.0], default=0.0)
    sm += np.select([
        (df['WT1'] > OB1) & (wt_cross_dn | wt_falling), df['WT1'] > OB1,
        (df['WT1'] > 20) & wt_falling, (df['WT1'] < OS1) & wt_rising,
    ], [3.0, 1.0, 1.0, -1.5], default=0.0)
    df['SJ_Momentum'] = sm.clip(lower=-2, upper=JT.MOMENTUM_CAP)

    # ── Layer 3: 캔들 ──
    sc_candidates = []
    for sig_name, base_pts, trend_pts in [
        ('Evening_Star', 2.5, 3.5), ('Bearish_Engulfing', 2.0, 3.0),
        ('Shooting_Star', 1.5, 2.5), ('Outside_Bearish', 1.5, 2.5), ('Doji_Bearish', 0.5, 1.0),
    ]:
        raw = df.get(sig_name, pd.Series(False, index=idx)).fillna(False)
        if sig_name == 'Bearish_Engulfing':
            pts = np.where(raw & in_uptrend & (body_atr_ratio > 1.0), 3.5,
                  np.where(raw & in_uptrend, trend_pts,
                  np.where(raw & (body_atr_ratio > 1.0), 2.5,
                  np.where(raw, base_pts, 0))))
        else:
            pts = np.where(raw & in_uptrend, trend_pts, np.where(raw, base_pts, 0))
        sc_candidates.append(pts)
    sc = pd.Series(np.stack(sc_candidates).max(axis=0), index=idx) if sc_candidates else pd.Series(0.0, index=idx)
    df['SJ_Candle'] = sc.clip(upper=JT.CANDLE_CAP)

    # ── Layer 4: BB ──
    sb_ = pd.Series(0.0, index=idx)
    sb_ += _sig_pts(df, 'BB_Squeeze_End_Bear', 3.0)
    sb_ += nr7_val + nr72_val + calm_val
    sb_ += np.where(squeeze_on & below_50, 1.0, 0)
    sb_ += np.select([pct_b > 0.95, pct_b > 0.8,
                       (pct_b >= 0.4) & (pct_b <= 0.6) & below_50, pct_b < 0.05],
                      [2.5, 1.5, 0.5, -1.5], default=0.0)
    sb_ += _sig_pts(df, 'BB_Lower_Break', 1.5)  # 🔧 BB 하단 붕괴 = 매도
    sb_ += np.where(df.get('BB_Upper_Break', pd.Series(False, index=idx)).fillna(False) & above_200, -0.5, 0)
    df['SJ_BB'] = sb_.clip(lower=-1, upper=JT.BB_CAP)

    # ── Layer 5: Volume ──
    sv = pd.Series(0.0, index=idx)
    sv += _sig_pts(df, 'Volume_Climax_Sell', 3.0)
    sv += _sig_pts(df, 'OBV_Div_Sell', 1.5)
    sv += np.where((vol_ratio >= 3.0) & (C < O), 2.5,
          np.where((vol_ratio >= 1.5) & (C < O), 1.0, 0))
    sv += np.where(obv_below & (obv < obv.shift(5)), 1.5,
          np.where(obv_below, 0.5, 0))
    sv += np.where(obv_above & (obv > obv.shift(5)), -1.0, 0)
    sv += np.select([vol_bull_ratio < 0.5, vol_bull_ratio < 0.7, vol_bull_ratio > 2.0],
                     [1.5, 0.5, -1.0], default=0.0)
    df['SJ_Volume'] = sv.clip(lower=-1, upper=JT.VOLUME_CAP)

    # ── Layer 6: 자금흐름 ──
    smf = pd.Series(0.0, index=idx)
    smf += np.select([rmfi > 10, rmfi > 5, rmfi < -10],
                      [2.0, 1.0, -0.5], default=0.0)
    if 'MF_Slope_5' in df.columns:
        mf_slope = df['MF_Slope_5']
        smf += np.select([mf_slope < -5, mf_slope < -2, mf_slope < 0, mf_slope > 5],
                          [2.0, 1.5, 0.5, -1.0], default=0.0)
    if 'MF_Dn_Streak' in df.columns:
        smf += np.select([df['MF_Dn_Streak'] >= 5, df['MF_Dn_Streak'] >= 3],
                          [2.0, 1.0], default=0.0)
    smf += _sig_pts(df, 'MF_Cross_Bear', 2.0)
    smf += _sig_pts(df, 'MF_Bear_Div', 2.0)
    smf += _sig_pts(df, 'MF_Accel_Dn', 1.0)
    smf += np.where(cmf < -0.15, 1.5, np.where(cmf < -0.05, 0.5, np.where(cmf > 0.15, -1.0, 0)))
    smf += _sig_pts(df, 'CMF_Bear', 1.5)
    df['SJ_MF'] = smf.clip(lower=-1, upper=JT.MF_CAP)

    # ── Layer 7: Pattern ──
    sp = pd.Series(0.0, index=idx)
    blood = _sig_pts(df, 'Blood_Diamond', 4.0)
    rdt1 = np.where(blood == 0, _sig_pts(df, 'Red_Dot_T1', 2.5), 0)
    rdt2 = np.where((blood == 0) & (rdt1 == 0), _sig_pts(df, 'Red_Dot_T2', 2.0), 0)
    sp += blood + rdt1 + rdt2
    brd_pts = np.where(blood == 0, _sig_pts(df, 'Bear_Divergence', 2.0), 0)
    sp += brd_pts
    for s, p in [('Pullback_123_Bear', 2.5), ('Setup_180_Bear', 2.0), ('Boomer_Sell', 2.0),
                  ('Expansion_BD', 3.0), ('Gilligans_Sell', 2.5), ('Lizard_Bear', 2.0),
                  ('NonADX_123_Bear', 1.5), ('EMA_Pullback_Sell', 2.0),
                  ('Momentum_Ignition_Sell', 3.0), ('SuperTrend_Sell', 2.0),
                  ('Gap_Down', 1.0), ('Gap_Up_Closed', 1.0),
                  ('New_52W_Low', 2.0), ('Red_Diamond', 2.0),
                  ('Hidden_Bear_Div', 1.5), ('Squeeze_Fire_Sell', 2.0),
                  ('Parabolic_Top_Sell', 3.0),
                  ('Kumo_Breakout_Bear', 2.5), ('TK_Cross_Bear', 1.5)]:
        sp += _sig_pts(df, s, p)
    for s, decay_pts in [('Blood_Diamond', 2.0), ('Red_Dot_T1', 1.0), ('Expansion_BD', 1.5),
                          ('Momentum_Ignition_Sell', 1.5), ('Parabolic_Top_Sell', 1.5),
                          ('Kumo_Breakout_Bear', 1.0)]:
        if s in df.columns:
            yesterday = df[s].shift(1).fillna(False)
            sp += np.where(yesterday & ~df[s], decay_pts * 0.5, 0)
    df['SJ_Pattern'] = sp.clip(upper=JT.PATTERN_CAP)

    # ── 🆕 Layer 8: Anticipation (매도) ──
    sa = pd.Series(0.0, index=idx)
    setup_sell = df.get('Setup_Pressure_Sell', pd.Series(0, index=idx))
    sa += np.where(setup_sell >= 8, 3.0,
          np.where(setup_sell >= 5, 2.0,
          np.where(setup_sell >= 3, 1.0, 0)))
    sa += np.where(comp_accel < -JT.ACCEL_STRONG, 2.5,
          np.where(comp_accel < -JT.ACCEL_MODERATE, 1.5,
          np.where(comp_accel < -0.5, 0.5, 0)))
    sa += np.where(comp_accel > JT.ACCEL_MODERATE, -1.0, 0)
    sa += np.where(df.get('WT_Conv_Bear', pd.Series(False, index=idx)), 2.0, 0)
    sa += _sig_pts(df, 'Setup_Squeeze_Bear', 1.5)
    sa += _sig_pts(df, 'Momentum_Accel_Sell', 2.0)
    sa += _sig_pts(df, 'WT_Convergence_Bear', 1.5)
    sa += _sig_pts(df, 'Volume_Dry_Up', 0.5)
    df['SJ_Anticipation'] = sa.clip(lower=-1, upper=JT.ANTICIPATION_CAP)

    # ── SELL 합산 ──
    df['Sell_Total'] = (df['SJ_Trend'] + df['SJ_Momentum'] + df['SJ_Candle'] +
                        df['SJ_BB'] + df['SJ_Volume'] + df['SJ_MF'] +
                        df['SJ_Pattern'] + df['SJ_Anticipation'])

    # ═══ 콤보 보너스 (🔧 등급별 차등) ═══
    detect_combos(df, vol_ratio)
    buy_combo_bonus = pd.Series(0.0, index=idx)
    sell_combo_bonus = pd.Series(0.0, index=idx)
    for col, (name, d, tier) in COMBO_MAP.items():
        if col not in df.columns:
            continue
        if tier == 1:
            bonus = JT.COMBO_TIER1_BONUS
        elif tier == 2:
            bonus = JT.COMBO_TIER2_BONUS
        else:
            bonus = JT.COMBO_TIER3_BONUS

        if d == 'buy':
            buy_combo_bonus += np.where(df[col], bonus, 0.0)
        else:
            sell_combo_bonus += np.where(df[col], bonus, 0.0)

    df['Buy_Total'] += buy_combo_bonus
    df['Sell_Total'] += sell_combo_bonus

    # ── 활성 레이어 (🔧 8개) ──
    layer_names_buy = ['BJ_Trend', 'BJ_Momentum', 'BJ_Candle', 'BJ_BB',
                       'BJ_Volume', 'BJ_MF', 'BJ_Pattern', 'BJ_Anticipation']
    layer_names_sell = ['SJ_Trend', 'SJ_Momentum', 'SJ_Candle', 'SJ_BB',
                        'SJ_Volume', 'SJ_MF', 'SJ_Pattern', 'SJ_Anticipation']
    df['Buy_Active_Layers'] = sum((df[n] > 0).astype(int) for n in layer_names_buy)
    df['Sell_Active_Layers'] = sum((df[n] > 0).astype(int) for n in layer_names_sell)

    # ═══ 🔧 최종 판단 (확신도 포함) ═══
    j = np.full(len(df), 'NEUTRAL', dtype=object)
    conf = np.zeros(len(df), dtype=float)  # 🆕 확신도 (0~100)
    bt_v, st_v = df['Buy_Total'].values, df['Sell_Total'].values
    ba_v, sa_v = df['Buy_Active_Layers'].values, df['Sell_Active_Layers'].values
    atr_pct = (df['ATR'] / (df['Close'] + 1e-10) * 100).values

    for i in range(len(df)):
        b, s = bt_v[i], st_v[i]
        bal, sal = ba_v[i], sa_v[i]
        diff = b - s
        ratio = b / (s + 0.01)
        s_ratio = s / (b + 0.01)
        vol = atr_pct[i]

        scale = JT.LOW_VOL_SCALE if vol < 2.0 else 1.0
        sell_scale = scale * JT.SELL_ASYMMETRY

        # BUY 판단
        if (b >= JT.STRONG_BUY_SCORE * scale and bal >= JT.STRONG_BUY_LAYERS and
                ratio >= JT.STRONG_BUY_RATIO and diff >= JT.STRONG_BUY_DIFF * scale):
            j[i] = 'STRONG_BUY'
            conf[i] = min(90 + (diff - JT.STRONG_BUY_DIFF) * 2, 99)
        elif (b >= JT.BUY_SCORE * scale and bal >= JT.BUY_LAYERS and
                ratio >= JT.BUY_RATIO and diff >= JT.BUY_DIFF * scale):
            j[i] = 'BUY'
            conf[i] = min(60 + (diff - JT.BUY_DIFF) * 3, 89)
        elif b >= JT.WATCH_BUY_SCORE * scale and bal >= JT.WATCH_LAYERS and diff >= JT.WATCH_DIFF * scale:
            j[i] = 'WATCH_BUY'
            conf[i] = min(30 + diff * 3, 59)
        # SELL 판단
        elif (s >= JT.STRONG_BUY_SCORE * sell_scale and sal >= JT.STRONG_BUY_LAYERS and
                s_ratio >= 1.5 and (s - b) >= 8 * scale):
            j[i] = 'STRONG_SELL'
            conf[i] = min(90 + ((s - b) - 8) * 2, 99)
        elif (s >= JT.BUY_SCORE * sell_scale and sal >= JT.BUY_LAYERS and
                s_ratio >= 1.2 and (s - b) >= 4 * scale):
            j[i] = 'SELL'
            conf[i] = min(60 + ((s - b) - 4) * 3, 89)
        elif s >= JT.WATCH_BUY_SCORE * sell_scale and sal >= JT.WATCH_LAYERS and (s - b) >= 1.5 * scale:
            j[i] = 'WATCH_SELL'
            conf[i] = min(30 + (s - b) * 3, 59)
        elif (b >= JT.MIXED_MIN * scale and s >= JT.MIXED_MIN * scale and
                abs(diff) < JT.MIXED_DIFF_MAX * scale):
            j[i] = 'MIXED'
            conf[i] = max(20, 50 - abs(diff) * 5)
        else:
            conf[i] = max(10, 50 - max(b, s))

    df['Trade_Judgment'] = j
    df['Judgment_Confidence'] = np.clip(conf, 0, 99)  # 🆕

    return df


# ──────────────────────────────────────────
# 판단 상세 + Bias (🆕 확신도 + 선행 레이어)
# ──────────────────────────────────────────
def get_judgment_detail(row) -> Dict[str, Any]:
    layer_names = ['Trend', 'Momentum', 'Candle', 'BB', 'Volume', 'MF', 'Pattern', 'Anticipation']
    bl = {n: float(row.get(f'BJ_{n}', 0)) for n in layer_names}
    sl = {n: float(row.get(f'SJ_{n}', 0)) for n in layer_names}
    combos = [{'name': name, 'dir': d, 'tier': t}
              for col, (name, d, t) in COMBO_MAP.items()
              if row.get(col, False)]
    return {
        'judgment': str(row.get('Trade_Judgment', 'NEUTRAL')),
        'confidence': float(row.get('Judgment_Confidence', 0)),  # 🆕
        'buy_total': float(row.get('Buy_Total', 0)),
        'sell_total': float(row.get('Sell_Total', 0)),
        'buy_layers': bl, 'sell_layers': sl,
        'buy_active': int(row.get('Buy_Active_Layers', 0)),
        'sell_active': int(row.get('Sell_Active_Layers', 0)),
        'active_combos': combos,
        'net': float(row.get('Buy_Total', 0)) - float(row.get('Sell_Total', 0)),
        # 🆕 선행 지표 요약
        'setup_pressure_buy': float(row.get('Setup_Pressure_Buy', 0)),
        'setup_pressure_sell': float(row.get('Setup_Pressure_Sell', 0)),
        'composite_accel': float(row.get('Composite_Accel', 0)),
    }


def compute_bias(meta, htf1, htf2):
    sc = 0.0
    wt1 = meta.get('wt1', 0)
    if wt1 <= -60: sc += 3.0
    elif wt1 <= -53: sc += 2.0
    elif wt1 <= -20: sc += 1.0
    elif wt1 >= 60: sc -= 3.0
    elif wt1 >= 53: sc -= 2.0
    elif wt1 >= 20: sc -= 1.0
    rsi = meta.get('rsi', 50)
    if rsi <= 30: sc += 1.5
    elif rsi <= 45: sc += 0.5
    elif rsi >= 70: sc -= 1.5
    elif rsi >= 55: sc -= 0.5
    mfi = meta.get('mfi', 50)
    if mfi <= 30: sc += 1.5
    elif mfi <= 45: sc += 0.5
    elif mfi >= 70: sc -= 1.5
    elif mfi >= 55: sc -= 0.5
    mf = meta.get('mf_area', 0)
    if mf < -5: sc += 2.0
    elif mf < 0: sc += 1.0
    elif mf > 5: sc -= 2.0
    elif mf > 0: sc -= 1.0
    stk = meta.get('stochk', 50)
    if stk < 20: sc += 1.5
    elif stk < 35: sc += 0.5
    elif stk > 80: sc -= 1.5
    elif stk > 65: sc -= 0.5
    mh = meta.get('macd_hist', 0)
    if mh > 0.1: sc += 1.0
    elif mh > 0: sc += 0.5
    elif mh < -0.1: sc -= 1.0
    elif mh < 0: sc -= 0.5
    sc += 1.5 if htf1 else -1.5
    sc += 2.0 if htf2 else -2.0
    # 🆕 가속도 반영
    accel = meta.get('composite_accel', 0)
    if accel > 1.5: sc += 1.0
    elif accel < -1.5: sc -= 1.0

    if sc >= 9.0: return 'STRONG BUY', sc
    elif sc >= 3.5: return 'BUY', sc
    elif sc > -3.5: return 'NEUTRAL', sc
    elif sc > -9.0: return 'SELL', sc
    else: return 'STRONG SELL', sc


# ──────────────────────────────────────────
# 호버 텍스트 빌더 (🆕 확신도 표시)
# ──────────────────────────────────────────
def _build_judgment_hover(row, signals_dict):
    judgment = str(row.get('Trade_Judgment', 'NEUTRAL'))
    bt, st_ = float(row.get('Buy_Total', 0)), float(row.get('Sell_Total', 0))
    confidence = float(row.get('Judgment_Confidence', 0))
    net = bt - st_
    ico = '🟢' if 'BUY' in judgment else ('🔴' if 'SELL' in judgment else '🟠')
    lines = [f"<b style='font-size:13px'>{ico} {judgment} ({confidence:.0f}%)</b>",
             f"<b>BUY</b> {bt:.1f} vs <b>SELL</b> {st_:.1f} (NET: {net:+.1f})", "─" * 26]

    lnames = ['Trend', 'Momentum', 'Candle', 'BB', 'Volume', 'MF', 'Pattern', 'Anticipation']
    licons = ['📈', '🔥', '🕯️', '📊', '📦', '💰', '⭐', '⏳']

    bparts = [f"{ic}{n}:{float(row.get(f'BJ_{n}', 0)):.1f}"
              for ic, n in zip(licons, lnames) if float(row.get(f'BJ_{n}', 0)) > 0]
    sparts = [f"{ic}{n}:{float(row.get(f'SJ_{n}', 0)):.1f}"
              for ic, n in zip(licons, lnames) if float(row.get(f'SJ_{n}', 0)) > 0]
    if bparts:
        lines.append(f"<span style='color:#34D399'><b>▲</b> {' · '.join(bparts)}</span>")
    if sparts:
        lines.append(f"<span style='color:#F87171'><b>▼</b> {' · '.join(sparts)}</span>")
    lines.append("─" * 26)

    combos = [name for col, (name, _, _) in COMBO_MAP.items() if row.get(col, False)]
    lines.append(f"<b>🔥 콤보:</b> {' / '.join(combos)}" if combos
                 else "<span style='color:#64748B'>콤보 없음</span>")
    lines.append("─" * 26)

    bsigs, ssigs = [], []
    for sn, cfg in signals_dict.items():
        if sn.startswith('Combo_') or sn in ('Ultra_Buy', 'Strong_Buy', 'Ultra_Sell', 'Strong_Sell'):
            continue
        if row.get(sn, False):
            entry = f"{cfg['icon']} {cfg.get('kor', cfg['label'])}"
            (bsigs if cfg['dir'] == 'buy' else ssigs).append(entry)
    if bsigs:
        lines.append(f"<span style='color:#34D399'><b>▲ 매수({len(bsigs)}):</b></span>")
        lines.extend(f"  {s}" for s in bsigs[:8])
        if len(bsigs) > 8: lines.append(f"  ...외 {len(bsigs)-8}개")
    if ssigs:
        lines.append(f"<span style='color:#F87171'><b>▼ 매도({len(ssigs)}):</b></span>")
        lines.extend(f"  {s}" for s in ssigs[:8])
        if len(ssigs) > 8: lines.append(f"  ...외 {len(ssigs)-8}개")
    if not bsigs and not ssigs:
        lines.append("<span style='color:#64748B'>지표 점수 기반 판단</span>")
    return "<br>".join(lines)


# ══════════════════════════════════════════
#  PART 2/4 끝
#  다음: PART 3/4 — 차트 + 메타데이터 + 프롬프트 + 분석 로직
# ══════════════════════════════════════════
# ══════════════════════════════════════════════════════════════
#  CipherX V12.0 — PART 3/4
#  차트 빌더 + 메타데이터 + 프롬프트 + 분석 로직
#  🆕 확신도 표시, 선행 지표 차트 행, 가속도 게이지
#  🔧 BB 분리 반영, 8-Layer 반영
# ══════════════════════════════════════════════════════════════


# ──────────────────────────────────────────
# 차트 유틸리티
# ──────────────────────────────────────────
def _hl(fig, mask, idx, fill, txt=None, row=1):
    """하이라이트 영역 추가"""
    d = mask.astype(int).diff().fillna(0)
    starts = idx[d == 1].tolist()
    ends = idx[d == -1].tolist()
    if len(mask) > 0 and mask.iloc[0]: starts.insert(0, idx[0])
    if len(mask) > 0 and mask.iloc[-1]: ends.append(idx[-1])
    for s_v, e_v in zip(starts, ends):
        kw = dict(x0=s_v, x1=e_v, fillcolor=fill, line_width=0, row=row, col=1)
        if txt:
            kw.update(annotation_text=txt, annotation_position="top left",
                      annotation_font_size=10, annotation_font_color="#FF5252")
        fig.add_vrect(**kw)


# ──────────────────────────────────────────
# 차트 빌더 (🆕 Row 7: Anticipation 게이지)
# ──────────────────────────────────────────
def build_chart(dc, ticker, regime, shield):
    mac = {5: "#ff9900", 10: "#ffb74d", 20: '#f1c40f', 50: '#e74c3c',
           100: '#9b59b6', 125: '#3498db', 200: '#2ecc71'}

    fig = make_subplots(
        rows=7, cols=1, shared_xaxes=True, vertical_spacing=0.03,
        row_heights=[.32, .06, .12, .10, .12, .14, .14],
        subplot_titles=("", "Volume", "WaveTrend Oscillator",
                        "Money Flow", "MACD (12, 26, 9)",
                        "BUY / SELL Judgment",
                        "🆕 Anticipation (선행 지표)"))

    # ═══ Row 1: 캔들스틱 ═══
    fig.add_trace(go.Candlestick(
        x=dc.index, open=dc['Open'], high=dc['High'], low=dc['Low'], close=dc['Close'],
        name="Price", increasing_line_color='#00E676', decreasing_line_color='#FF1744',
        increasing_fillcolor='rgba(0,230,118,0.8)', decreasing_fillcolor='rgba(255,23,68,0.8)',
        hovertemplate="O:%{open:.2f} H:%{high:.2f}<br>L:%{low:.2f} C:%{close:.2f}<extra></extra>"),
        row=1, col=1)

    for ma in [5, 10, 20, 50, 100, 125, 200]:
        fig.add_trace(go.Scatter(x=dc.index, y=dc[f'MA{ma}'],
            line=dict(color=mac[ma], width=1.2), name=f'{ma}MA',
            hovertemplate="%{y:.2f}"), row=1, col=1)

    for nm, col_n, clr, dash in [('EMA8', 'EMA8', '#00FFFF', 'dot'),
                                   ('EMA21', 'EMA21', '#FF69B4', 'dot')]:
        fig.add_trace(go.Scatter(x=dc.index, y=dc[col_n],
            line=dict(color=clr, width=1.5, dash=dash), name=nm,
            hovertemplate="%{y:.2f}"), row=1, col=1)

    for mc, clr, nm in [(dc['ST_Direction'] == 1, '#00E676', 'ST▲'),
                          (dc['ST_Direction'] == -1, '#FF1744', 'ST▼')]:
        fig.add_trace(go.Scatter(x=dc.index, y=dc['SuperTrend'].where(mc),
            line=dict(color=clr, width=2), name=nm, connectgaps=False,
            hovertemplate="%{y:.2f}"), row=1, col=1)

    # Ichimoku Cloud
    if 'Ichimoku_SenkouA' in dc.columns:
        sa = dc['Ichimoku_SenkouA']
        sb_ichi = dc['Ichimoku_SenkouB']
        fig.add_trace(go.Scatter(x=dc.index, y=sa,
            line=dict(color='rgba(0,230,118,0.3)', width=0.5),
            name='Senkou A', showlegend=False, hoverinfo='skip'), row=1, col=1)
        fig.add_trace(go.Scatter(x=dc.index, y=sb_ichi,
            line=dict(color='rgba(255,23,68,0.3)', width=0.5),
            name='Senkou B', fill='tonexty', fillcolor='rgba(99,102,241,0.04)',
            showlegend=False, hoverinfo='skip'), row=1, col=1)

    fig.add_trace(go.Scatter(x=dc.index, y=dc['BB_Up'],
        line=dict(color='gray', width=1, dash='dot'),
        name='BB↑', hovertemplate="%{y:.2f}"), row=1, col=1)
    fig.add_trace(go.Scatter(x=dc.index, y=dc['BB_Low'],
        line=dict(color='gray', width=1, dash='dot'),
        name='BB↓', fill='tonexty', fillcolor='rgba(128,128,128,0.07)',
        hovertemplate="%{y:.2f}"), row=1, col=1)

    for col_name, clr, txt in [('Sell_Shield_Overridden', 'rgba(255,0,0,0.04)', '🔓Sell OFF'),
                                 ('Buy_Shield_Overridden', 'rgba(0,255,0,0.04)', '🔓Buy OFF')]:
        om = dc.get(col_name, pd.Series(False, index=dc.index))
        if om.any():
            _hl(fig, om, dc.index, clr, txt, 1)

    # ═══ 판단 마커 ═══
    if 'Trade_Judgment' in dc.columns:
        enabled_j = st.session_state.get('enabled_judgments', set(JUDGMENT_MARKERS.keys()))
        for j_grade, j_cfg in JUDGMENT_MARKERS.items():
            if j_grade not in enabled_j:
                continue
            mask = dc['Trade_Judgment'] == j_grade
            if not mask.any():
                continue
            sig_rows = dc[mask]
            if j_cfg['base'] == 'Low':
                y_vals = sig_rows['Low'] + sig_rows['ATR'] * j_cfg['atr_mult']
            else:
                y_vals = sig_rows['High'] + sig_rows['ATR'] * j_cfg['atr_mult']
            hover_texts = [_build_judgment_hover(dc.loc[idx_v], ALL_CHART_SIGNALS)
                           for idx_v in sig_rows.index]
            fig.add_trace(go.Scatter(
                x=sig_rows.index, y=y_vals, mode='markers',
                marker=dict(symbol=j_cfg['symbol'], size=j_cfg['size'], color=j_cfg['color'],
                    line=dict(width=j_cfg['line_width'], color=j_cfg['line_color']), opacity=0.95),
                name=j_cfg['label'], text=hover_texts,
                hovertemplate="%{text}<extra></extra>",
                hoverlabel=dict(bgcolor='rgba(14,17,23,0.97)', bordercolor=j_cfg['color'],
                    font=dict(size=11, family='Pretendard', color='#FAFAFA'), align='left'),
            ), row=1, col=1)

        for j_name, fill_clr in [('STRONG_BUY', 'rgba(0,230,118,0.05)'),
                                   ('BUY', 'rgba(0,230,118,0.025)'),
                                   ('STRONG_SELL', 'rgba(255,23,68,0.05)'),
                                   ('SELL', 'rgba(255,23,68,0.025)')]:
            jm = dc['Trade_Judgment'] == j_name
            if jm.any():
                _hl(fig, jm, dc.index, fill_clr, None, 1)

    # ═══ 🆕 스캐너 콤보 마커 ═══
    if st.session_state.get('show_scanner_combos', True):
        add_scanner_markers_to_chart(fig, dc, row=1)

    # ═══ Row 2: 거래량 ═══
    br = dc['Close'] < dc['Open']
    fig.add_trace(go.Bar(x=dc.index, y=dc['Volume'],
        marker_color=np.where(br, 'rgba(255,23,68,0.6)', 'rgba(0,230,118,0.6)').tolist(),
        name="Volume", opacity=0.8, hovertemplate="%{y:,.0f}"), row=2, col=1)
    vcm = dc.get('Volume_Climax_Buy', pd.Series(False)) | dc.get('Volume_Climax_Sell', pd.Series(False))
    vcd = dc[vcm]
    if not vcd.empty:
        fig.add_trace(go.Bar(x=vcd.index, y=vcd['Volume'], marker_color='#FFD700',
            name="Vol Climax", opacity=0.9, hovertemplate="%{y:,.0f}"), row=2, col=1)

    # ═══ Row 3: WaveTrend ═══
    fig.add_trace(go.Scatter(x=dc.index, y=dc['WT1'],
        line=dict(color='#00E676', width=2),
        name="WT1", hovertemplate="%{y:.1f}"), row=3, col=1)
    fig.add_trace(go.Scatter(x=dc.index, y=dc['WT2'],
        line=dict(color='#FF1744', width=1.5, dash='dot'),
        name="WT2", hovertemplate="%{y:.1f}"), row=3, col=1)
    wd = dc['WT1'] - dc['WT2']
    fig.add_trace(go.Bar(x=dc.index, y=wd,
        marker_color=np.where(wd >= 0, '#00E676', '#FF1744').tolist(),
        name="WT Hist", opacity=0.3, hovertemplate="%{y:.1f}"), row=3, col=1)
    for lv, cc, d in [(OB2, '#ff3333', 'dash'), (OB1, '#ff3333', 'solid'),
                       (0, 'gray', 'dot'), (OS1, '#00bfff', 'solid'), (OS2, '#00bfff', 'dash')]:
        fig.add_hline(y=lv, line_dash=d, line_color=cc, line_width=1, row=3, col=1)
    wmx = max(float(dc['WT1'].max()), 100) + 10
    wmn = min(float(dc['WT1'].min()), -100) - 10
    fig.add_hrect(y0=OB1, y1=wmx, fillcolor="rgba(255,23,68,0.08)", line_width=0, row=3, col=1)
    fig.add_hrect(y0=wmn, y1=OS1, fillcolor="rgba(0,191,255,0.08)", line_width=0, row=3, col=1)
    if 'Squeeze_On' in dc.columns:
        _hl(fig, dc['Squeeze_On'], dc.index, "rgba(255,255,0,0.05)", None, 3)

    # ═══ Row 4: Money Flow ═══
    rmfi = dc['RSI_MFI']
    fig.add_trace(go.Bar(x=dc.index, y=rmfi,
        marker_color=np.where(rmfi >= 0, '#3ee145', '#ff3d2e').tolist(),
        name="Money Flow", opacity=0.7, hovertemplate="%{y:.1f}"), row=4, col=1)
    fig.add_hline(y=0, line_dash="solid", line_color="gray", line_width=1, row=4, col=1)
    if 'CMF' in dc.columns:
        cmf_scaled = dc['CMF'] * 50
        fig.add_trace(go.Scatter(x=dc.index, y=cmf_scaled,
            line=dict(color='#FFD700', width=1, dash='dot'),
            name="CMF×50", opacity=0.6, hovertemplate="CMF: %{customdata:.3f}",
            customdata=dc['CMF'].values), row=4, col=1)

    # ═══ Row 5: MACD ═══
    fig.add_trace(go.Scatter(x=dc.index, y=dc['MACD_Line'],
        line=dict(color='#29B6F6', width=1.5),
        name="MACD", hovertemplate="%{y:.3f}"), row=5, col=1)
    fig.add_trace(go.Scatter(x=dc.index, y=dc['MACD_Signal'],
        line=dict(color='#FFA726', width=1.5),
        name="Signal", hovertemplate="%{y:.3f}"), row=5, col=1)
    mh = dc['MACD_Hist']
    fig.add_trace(go.Bar(x=dc.index, y=mh,
        marker_color=np.where(mh >= 0, '#26A69A', '#EF5350').tolist(),
        name="Hist", opacity=0.7, hovertemplate="%{y:.3f}"), row=5, col=1)
    fig.add_hline(y=0, line_color="#444444", line_width=1, row=5, col=1)

    # ═══ Row 6: Judgment Score ═══
    if 'Buy_Total' in dc.columns and 'Sell_Total' in dc.columns:
        net_j = dc['Buy_Total'] - dc['Sell_Total']
        colors = np.where(net_j >= 10, '#00E676',
                  np.where(net_j >= 5, '#69F0AE',
                  np.where(net_j <= -10, '#FF1744',
                  np.where(net_j <= -5, '#FF5252', '#FFC107'))))
        confidence_vals = dc.get('Judgment_Confidence', pd.Series(0, index=dc.index)).values
        fig.add_trace(go.Bar(x=dc.index, y=net_j,
            marker_color=colors.tolist(), name="Judgment NET", opacity=0.8,
            customdata=np.stack([dc['Buy_Total'].values, dc['Sell_Total'].values,
                dc.get('Trade_Judgment', pd.Series('N/A', index=dc.index)).values,
                confidence_vals], axis=-1),
            hovertemplate=("<b>%{customdata[2]}</b> (%{customdata[3]:.0f}%)<br>"
                           "BUY: %{customdata[0]:.1f}<br>"
                           "SELL: %{customdata[1]:.1f}<br>"
                           "NET: %{y:.1f}<extra></extra>")),
            row=6, col=1)
        for lv, cc, d in [(15, '#00E676', 'dash'), (-15, '#FF1744', 'dash'),
                           (10, '#00E676', 'dot'), (-10, '#FF1744', 'dot'),
                           (5, '#69F0AE', 'dot'), (-5, '#FF5252', 'dot'),
                           (0, 'gray', 'solid')]:
            fig.add_hline(y=lv, line_dash=d, line_color=cc,
                         line_width=1 if d == 'solid' else .8, row=6, col=1)
    else:
        conf = dc['Confluence_Score']
        fig.add_trace(go.Bar(x=dc.index, y=conf,
            marker_color=np.where(conf >= 3.5, '#00E676',
                         np.where(conf <= -3.5, '#FF1744', '#FFC107')).tolist(),
            name="Conf Score", opacity=0.8, hovertemplate="%{y:.1f}"), row=6, col=1)

    # ═══ 🆕 Row 7: Anticipation (선행 지표) ═══
    setup_buy = dc.get('Setup_Pressure_Buy', pd.Series(0, index=dc.index))
    setup_sell = dc.get('Setup_Pressure_Sell', pd.Series(0, index=dc.index))
    antic_net = setup_buy - setup_sell
    antic_colors = np.where(antic_net >= 5, '#00E676',
                   np.where(antic_net >= 2, '#69F0AE',
                   np.where(antic_net <= -5, '#FF1744',
                   np.where(antic_net <= -2, '#FF5252', '#FFC107'))))
    fig.add_trace(go.Bar(x=dc.index, y=antic_net,
        marker_color=antic_colors.tolist(), name="Setup NET", opacity=0.7,
        customdata=np.stack([setup_buy.values, setup_sell.values,
            dc.get('Composite_Accel', pd.Series(0, index=dc.index)).values], axis=-1),
        hovertemplate=("<b>Anticipation</b><br>"
                       "BUY Setup: %{customdata[0]:.1f}<br>"
                       "SELL Setup: %{customdata[1]:.1f}<br>"
                       "Accel: %{customdata[2]:.2f}<br>"
                       "NET: %{y:.1f}<extra></extra>")),
        row=7, col=1)

    # 가속도 오버레이
    comp_accel = dc.get('Composite_Accel', pd.Series(0, index=dc.index))
    fig.add_trace(go.Scatter(x=dc.index, y=comp_accel * 3,
        line=dict(color='#FFD700', width=1.5, dash='dot'),
        name="Accel×3", opacity=0.6, hovertemplate="Accel: %{customdata:.2f}",
        customdata=comp_accel.values), row=7, col=1)
    fig.add_hline(y=0, line_color="gray", line_width=1, row=7, col=1)
    for lv, cc in [(5, '#00E676'), (-5, '#FF1744'), (3, '#69F0AE'), (-3, '#FF5252')]:
        fig.add_hline(y=lv, line_dash='dot', line_color=cc, line_width=0.7, row=7, col=1)

    # ═══ 레이아웃 ═══
    fig.update_layout(
        yaxis_title="Price", yaxis2_title="Vol", yaxis3_title="WT",
        yaxis4_title="MF", yaxis5_title="MACD", yaxis6_title="BUY−SELL",
        yaxis7_title="Setup",
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=2, r=2, t=40, b=2), height=1400, showlegend=True, hovermode="x unified",
        hoverlabel=dict(bgcolor="rgba(14,17,23,0.95)", font_size=12,
                        font_family="Pretendard", bordercolor="#2D333B"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
            font=dict(size=9.5, color='#CCC', family='Pretendard'),
            bgcolor='rgba(0,0,0,0)', itemsizing='constant'))
    for i in range(1, 8):
        ya = f'yaxis{i}' if i > 1 else 'yaxis'
        fig.update_layout(**{ya: dict(gridcolor='rgba(45,51,59,0.5)', gridwidth=1,
            zerolinecolor='rgba(60,63,70,0.6)', zerolinewidth=1,
            title_font=dict(size=11, color='#777'), tickfont=dict(size=10, color='#888'))})
    fig.update_xaxes(rangeslider_visible=False)
    has_weekends = dc.index.dayofweek.isin([5, 6]).any()
    rb = [dict(bounds=["sat", "mon"])] if not has_weekends else []
    fig.update_xaxes(showspikes=True, spikecolor="#667eea", spikemode="across",
        spikethickness=1, spikedash="dot", rangebreaks=rb,
        gridcolor='rgba(45,51,59,0.5)', gridwidth=1, tickfont=dict(size=10, color='#888'))
    fig.update_yaxes(showspikes=True, spikecolor="#667eea", spikemode="across",
        spikethickness=1, spikedash="dot")
    for ann in fig['layout']['annotations']:
        ann['font'] = dict(size=12, color='#AAA', family='Pretendard')
    return fig


# ──────────────────────────────────────────
# 메타데이터 빌드 (🆕 확신도 + 선행 지표 포함)
# ──────────────────────────────────────────
def build_metadata(dc, dv, ticker):
    lat, prev = dc.iloc[-1], dc.iloc[-2] if len(dc) >= 2 else dc.iloc[-1]
    pc = lat['Close'] - prev['Close']
    pp = pc / (prev['Close'] + 1e-10) * 100
    m4 = {k: float(lat[c]) for k, c in
          [('wt1', 'WT1'), ('rsi', 'RSI'), ('mfi', 'MFI'),
           ('mf_area', 'RSI_MFI'), ('stochk', 'StochK')]}
    m4['composite_accel'] = float(lat.get('Composite_Accel', 0))
    h1 = bool(lat.get('_HTF1_Bull', False))
    h2 = bool(lat.get('_HTF2_Bull', False))
    bias, bsc = compute_bias(m4, h1, h2)
    cf = float(dc['Confluence_Score'].iloc[-1])
    regime = ('STRONG BULL 🟢' if lat.get('Strong_Bull', False)
              else ('STRONG BEAR 🔴' if lat.get('Strong_Bear', False) else 'NEUTRAL ⚪'))

    sp_list = []
    for cond, lab in [('Parabolic_Blowoff', '🌡️PARA TOP'),
                       ('ST_Bear_Override', '📉ST BEAR'),
                       ('Parabolic_Bottom_Raw', '🧊PARA BOT')]:
        if lat.get(cond, False):
            sp_list.append(lab)
    if not sp_list:
        if lat.get('Buy_Shield_Overridden', False):
            sp_list.append('🔓BUY OFF')
        if lat.get('Sell_Shield_Overridden', False):
            sp_list.append('🔓SELL OFF')
    shield_str = ' + '.join(sp_list)

    sig_checks = [(k, v['icon'], v['label'], v['dir']) for k, v in ALL_CHART_SIGNALS.items()]
    recent = []
    for ir, row in dc.tail(15).iterrows():
        ds = ir.strftime('%m/%d')
        for col, icon, lbl, side in sig_checks:
            if row.get(col, False):
                recent.append((icon, lbl, ds, side))

    jd = get_judgment_detail(lat)
    judgment_history = []
    for ir, row in dc.tail(5).iterrows():
        jh = get_judgment_detail(row)
        judgment_history.append({
            'date': ir.strftime('%m/%d'),
            'judgment': jh['judgment'],
            'confidence': jh['confidence'],
            'buy_total': jh['buy_total'],
            'sell_total': jh['sell_total'],
            'combos': jh['active_combos'],
        })

    return {
        'ticker': ticker.upper(),
        'price': lat['Close'],
        'price_change': pc,
        'price_change_pct': pp,
        'volume': lat['Volume'],
        'avg_volume': dc['Volume'].rolling(20).mean().iloc[-1],
        'wt1': float(lat['WT1']), 'wt2': float(lat['WT2']),
        'rsi': float(lat['RSI']), 'mfi': float(lat['MFI']),
        'stochk': float(lat['StochK']), 'stochd': float(lat['StochD']),
        'vwap_osc': float(lat['VWAP_Osc']),
        'mf_area': float(lat['RSI_MFI']),
        'atr': float(lat['ATR']),
        'atr_pct': float(lat['ATR']) / (float(lat['Close']) + 1e-10) * 100,
        'adx': float(lat['ADX']),
        'plus_di': float(lat['Plus_DI']),
        'minus_di': float(lat['Minus_DI']),
        'overall_bias': bias, 'bias_score': bsc,
        'confluence_score': cf,
        'recent_signals': recent,
        'last_date': dc.index[-1].strftime('%Y-%m-%d'),
        'buy_proximity': float(lat['Buy_Proximity']),
        'sell_proximity': float(lat['Sell_Proximity']),
        'squeeze_on': bool(lat.get('Squeeze_On', False)),
        'trend_regime': regime,
        'shield_status': shield_str,
        'supertrend_dir': int(lat.get('ST_Direction', 0)),
        'supertrend_val': float(lat.get('SuperTrend', 0)),
        'ema8': float(lat.get('EMA8', 0)),
        'ema21': float(lat.get('EMA21', 0)),
        'bb_up': float(lat.get('BB_Up', 0)),
        'bb_low': float(lat.get('BB_Low', 0)),
        'ma50': float(lat.get('MA50', 0)),
        'ma200': float(lat.get('MA200', 0)),
        'macd_line': float(lat.get('MACD_Line', 0)),
        'macd_signal': float(lat.get('MACD_Signal', 0)),
        'macd_hist': float(lat.get('MACD_Hist', 0)),
        'judgment_detail': jd,
        'judgment_history': judgment_history,
        'cmf': float(lat.get('CMF', 0)),
        'ichimoku_tenkan': float(lat.get('Ichimoku_Tenkan', 0)),
        'ichimoku_kijun': float(lat.get('Ichimoku_Kijun', 0)),
        # 🆕 선행 지표
        'composite_accel': float(lat.get('Composite_Accel', 0)),
        'setup_pressure_buy': float(lat.get('Setup_Pressure_Buy', 0)),
        'setup_pressure_sell': float(lat.get('Setup_Pressure_Sell', 0)),
        'wt_conv_speed': float(lat.get('WT_Conv_Speed', 0)),
        'rsi_accel': float(lat.get('RSI_Accel', 0)),
    }, regime, shield_str


# ──────────────────────────────────────────
# 프롬프트 빌더 (🆕 선행 지표 + 확신도 포함)
# ──────────────────────────────────────────
def build_prompt_text(dc, meta):
    lat = dc.iloc[-1]
    rd = dc.tail(60)
    ps = ", ".join([f"'{d.strftime('%Y-%m-%d')}:{r['Close']:.2f}'" for d, r in rd.iterrows()])

    sl = []
    for ir, row in dc.tail(30).iterrows():
        dd = ir.strftime('%Y-%m-%d')
        for k, v in ALL_CHART_SIGNALS.items():
            if row.get(k, False):
                sl.append(f"{v['icon']} {v['label']} {dd}")
    st_text = "\n".join(sl) if sl else "최근 30일 내 시그널 없음"

    bp, sp = meta['buy_proximity'], meta['sell_proximity']
    prox = f"BuyProx={bp:.0f}%,SellProx={sp:.0f}%"
    if bp >= 60: prox += " ⚠️매수임박"
    if sp >= 60: prox += " ⚠️매도임박"
    sq = "SqON" if meta['squeeze_on'] else "SqOFF"
    std = (f"BULL▲({meta['supertrend_val']:.2f})" if meta['supertrend_dir'] == 1
           else f"BEAR▼({meta['supertrend_val']:.2f})")
    shd = f"Shield:{meta['shield_status']}" if meta['shield_status'] else "Shield:NONE"

    ichi_str = (f"Ichimoku=[Tenkan:{meta.get('ichimoku_tenkan',0):.2f}/"
                f"Kijun:{meta.get('ichimoku_kijun',0):.2f}]")
    cmf_str = f"CMF={meta.get('cmf',0):.3f}"

    vol = meta.get('volume', 0)
    avg_vol = meta.get('avg_volume', 1)
    vol_ratio = vol / avg_vol if avg_vol else 0
    vol_str = f"Vol={vol:,.0f}(평균대비 {vol_ratio:.1f}x)"

    # 🆕 선행 지표 문자열
    antic_str = (f"MomAccel={meta.get('composite_accel',0):.2f},"
                 f"SetupBuy={meta.get('setup_pressure_buy',0):.1f},"
                 f"SetupSell={meta.get('setup_pressure_sell',0):.1f},"
                 f"WTConvSpd={meta.get('wt_conv_speed',0):.1f},"
                 f"RSIAccel={meta.get('rsi_accel',0):.1f}")

    inds = (f"{vol_str}, WT1={lat['WT1']:.1f},WT2={lat['WT2']:.1f},"
        f"RSI={lat['RSI']:.1f},MFI={lat['MFI']:.1f},"
        f"StK={lat['StochK']:.1f},StD={lat['StochD']:.1f},"
        f"VWAP={lat['VWAP_Osc']:.2f},"
        f"MF={lat['RSI_MFI']:.1f},ADX={lat['ADX']:.1f},"
        f"+DI={lat['Plus_DI']:.1f},-DI={lat['Minus_DI']:.1f},"
        f"E8={lat['EMA8']:.2f},E21={lat['EMA21']:.2f},ST={std},"
        f"BB=[{meta['bb_up']:.2f}/{meta['bb_low']:.2f}],"
        f"%B={lat.get('Percent_B',0):.2f},"
        f"M50={meta['ma50']:.2f},M200={meta['ma200']:.2f},"
        f"Chandelier=[L:{lat.get('Chandelier_Long',0):.2f}/"
        f"S:{lat.get('Chandelier_Short',0):.2f}],"
        f"MACD={meta['macd_line']:.3f}/{meta['macd_signal']:.3f} "
        f"H={meta['macd_hist']:.3f},"
        f"{ichi_str},{cmf_str},"
        f"Conf={meta['confluence_score']:.1f},"
        f"Bias={meta['overall_bias']}({meta['bias_score']:.1f}),"
        f"Trend={meta['trend_regime']},{shd},{prox},{sq}")

    jd = meta.get('judgment_detail', {})
    j_txt = ""
    if jd:
        j_txt = f"\n\n📌 [멀티 시그널 매매 판단]\n"
        j_txt += f"  최종판단: {jd.get('judgment','NEUTRAL')} (확신도: {jd.get('confidence',0):.0f}%)\n"
        j_txt += f"  BUY점수: {jd.get('buy_total',0):.1f} (활성 {jd.get('buy_active',0)}/{NUM_LAYERS} 레이어)\n"
        j_txt += f"  SELL점수: {jd.get('sell_total',0):.1f} (활성 {jd.get('sell_active',0)}/{NUM_LAYERS} 레이어)\n"
        bl = jd.get('buy_layers', {})
        sla = jd.get('sell_layers', {})
        j_txt += f"  BUY레이어: {', '.join(f'{k}={v:.1f}' for k,v in bl.items())}\n"
        j_txt += f"  SELL레이어: {', '.join(f'{k}={v:.1f}' for k,v in sla.items())}\n"
        combos = jd.get('active_combos', [])
        if combos:
            combo_strs = [f"{c['name']}(T{c.get('tier', 2)})" for c in combos]
            j_txt += f"  🔥활성콤보: {', '.join(combo_strs)}\n"
        else:
            j_txt += "  활성콤보: 없음\n"
        jh = meta.get('judgment_history', [])
        if jh:
            j_txt += "  최근5일: " + " → ".join(
                f"{d['date']}:{d['judgment']}({d.get('confidence',0):.0f}%,"
                f"B{d['buy_total']:.0f}/S{d['sell_total']:.0f})"
                for d in jh) + "\n"

    # 🆕 선행 지표 블록
    antic_txt = f"\n\n📌 [선행 지표 (Anticipation)]\n  {antic_str}\n"
    accel_v = meta.get('composite_accel', 0)
    if accel_v > JT.ACCEL_STRONG:
        antic_txt += "  ⚡ 모멘텀 강한 상승 가속 중\n"
    elif accel_v > JT.ACCEL_MODERATE:
        antic_txt += "  📈 모멘텀 상승 가속 감지\n"
    elif accel_v < -JT.ACCEL_STRONG:
        antic_txt += "  ⚡ 모멘텀 강한 하락 가속 중\n"
    elif accel_v < -JT.ACCEL_MODERATE:
        antic_txt += "  📉 모멘텀 하락 가속 감지\n"
    sb_v = meta.get('setup_pressure_buy', 0)
    ss_v = meta.get('setup_pressure_sell', 0)
    if sb_v >= 8:
        antic_txt += f"  🟢 매수 셋업 고도 축적 ({sb_v:.1f}점)\n"
    elif sb_v >= 5:
        antic_txt += f"  🟡 매수 셋업 축적 중 ({sb_v:.1f}점)\n"
    if ss_v >= 8:
        antic_txt += f"  🔴 매도 셋업 고도 축적 ({ss_v:.1f}점)\n"
    elif ss_v >= 5:
        antic_txt += f"  🟡 매도 셋업 축적 중 ({ss_v:.1f}점)\n"

    return f"{ps}\n\n📌 [지표 요약]\n{inds}\n\n📌 [최근 시그널]\n{st_text}{j_txt}{antic_txt}"


def build_ai_prompt(ticker, phist, fundamentals):
    return f"""━━━━━━━━━━━━━
【 🎯 Role & Persona 】
━━━━━━━━━━━━━
당신은 월스트리트 20년+ 경력의 베테랑 퀀트(Quant) 펀드 매니저이자 기술적 분석의 대가입니다.
감정이나 선입견을 철저히 배제하고 오직 제공된 기술적 지표(수치), 거래량, 펀더멘탈 팩트를 기반으로 냉철하게 시장을 분석합니다.
특히 Market Cipher B 지표와 ATR 기반의 변동성 리스크 관리에 정통하며, 개인 투자자에게 명확하고 실질적인 매매 전략을 조언합니다.

---
━━━━━━━━━━━━━
【 ✍️ Writing Guidelines & Rules 】
━━━━━━━━━━━━━
1. 톤앤매너: 객관적, 분석적이면서도 확신에 찬 어조. ("~일 것으로 보입니다" ❌ → "~할 가능성이 높습니다" ⭕)
2. 🧮 기계적 리스크 관리 (ATR 활용): 손절가와 목표가는 반드시 ATR 기반으로 산출.
   - 스윙 롱 손절가 = 현재가 - (ATR * 1.5) / 1차 목표가 = 현재가 + (ATR * 2.0)
3. ⚖️ 시스템 데이터 크로스체크: BUY/SELL 스코어와 콤보를 맹신하지 말고, 실제 WT1, RSI, MACD, CMF 수치와 일치하는지 검증.
4. 📊 지지/저항 고도화: Volume Profile(POC, VAH, VAL) 개념 적용하여 매물대 기반 지지/저항 설정.
5. 🎲 확률적 사고: Bullish / Base / Bearish 시나리오별 예상 확률(%) 부여.
6. 🚫 환각 엄금: Input Data에 없는 재무 정보를 지어내지 마세요.
7. ⏳ 선행 지표 활용: 제공된 Anticipation(셋업 축적, 모멘텀 가속도, WT 수렴 속도) 데이터를 적극 반영하여 "앞으로 일어날 움직임"을 예측하세요.

---
━━━━━━━━━━━━━
【 📥 Input Data 】
━━━━━━━━━━━━━
[티커: {ticker}]

📌 [주가 + 기술적 지표 + 시그널 + 시스템 스코어 + 선행 지표]
{phist}

📌 [YFinance 펀더멘탈 및 숏(공매도) 데이터]
{fundamentals}

---
━━━━━━━━━━━━━
【 📄 Output Format (반드시 아래 양식을 그대로 출력) 】
━━━━━━━━━━━━━
# 🚦 {{ticker}} 심층 퀀트 데이터 리포트
[🔵/🔴/🟠] [{{ticker}}] 분석: [핵심 한 줄 요약]
[날짜], 전일 대비 [변동률]% [상승/하락]. 거래량 평균 대비 [배수]. 지지 [가격], 저항 [가격].

---
### 📊 내용 요약 및 시장 심리
[🔵/🔴/🟠] [기술적 상태 + 스마트 머니 동향 3~4문장 요약]

---
### ⚖️ 시스템 스코어 및 마켓 사이퍼 검증
* 최종 판정: [판단] (확신도: [__]%) — BUY: [점수] / SELL: [점수]
* WaveTrend & MF: [상태]
* 발생 시그널 및 콤보: [내역]
> 💡 퀀트 매니저의 검증: [시스템과 실제 지표 일치 여부]

---
### ⏳ 선행 지표 분석 (Anticipation)
* 모멘텀 가속도: [수치 및 해석 — 상승/하락 가속 또는 감속 여부]
* 셋업 축적 점수: BUY [점수] / SELL [점수] — [해석]
* WT 수렴 속도: [교차 임박 여부 판단]
> [선행 지표가 가리키는 향후 1~3일 전망]

---
### 📈 기술적 지표 심층 분석
* 모멘텀 및 추세 강도: [RSI, MACD, ADX 기반]
* 자금 흐름: [CMF, VWAP 기반 매집/투매 징후]
* Ichimoku: [구름대 위치, 전환-기준 관계]
> [🔵/🔴/🟠] 종합 해석

---
### 📉 공매도 현황 및 수급 추론
* 숏 비중 및 데이터: [분석]
* 시사점: [숏커버링 압력 또는 하방 베팅]
> [🔵/🔴/🟠] 수급 해석

---
### 주가변동이유 및 이벤트
1. [🔵/🔴/🟠] [이유 1]
2. [이유 2]
3. [이유 3]

---
### 🔮 종합 해석 및 실전 트레이딩 시나리오
* 🔵 **긍정적 시나리오:** [조건] → [목표가]. (확률: __%)
* 🟠 **베이스 시나리오:** [횡보/조정]. (확률: __%)
* 🔴 **리스크 시나리오:** [이탈 시] → [하락 목표가]. (확률: __%)

**기계적 트레이딩 전략 (ATR 기반):**
* **R/R 비율:** 1:__
* **공격적 매수 구간:** [가격대]
* **보수적 진입 (확인 매매):** [가격대]
* **손절 라인:** [가격] — ATR 반영, 붕괴 시 즉시 대응
* **분할 매도:** 1차 [가격] __% / 2차 [가격] __%
* **트레일링 스탑:** ATR 기준 적용

---
### 결론 및 익일 주가 예측
[🔵/🔴/🟠] 예상: [상승/하락/보합]
* 근거: [1~2문장]
[결론]: [핵심 가이드 한 줄]
[리스크/리워드 최적 진입]: [가격] 지지 확인 후 [가격] 공략
[GRADE/Score]: [최종 등급]
"""


# ──────────────────────────────────────────
# 분석 통합 로직 (🔧 에러 핸들링 강화)
# ──────────────────────────────────────────
def analyze(ticker: str, chart_days: int = 252, refresh: bool = False):
    try:
        ts = int(time.time()) if refresh else None
        df = compute_and_cache(ticker, ts)

        if df is None or df.empty:
            return None, "주가 데이터를 불러올 수 없습니다.", None

        if len(df) < 50:
            return None, (f"데이터 부족: 상장/거래 기간이 짧아 퀀트 분석이 불가합니다. "
                          f"(현재 {len(df)}일, 최소 50일 필요)"), None

        dv = df.dropna(subset=['WT1', 'WT2'])
        dc = dv.tail(chart_days).copy()

        if dc.empty:
            return None, "차트 데이터 부족 (지표 계산 후 남은 데이터 없음)", None

        meta, regime, shield = build_metadata(dc, dv, ticker)
        fig = build_chart(dc, ticker, regime, shield)

        return fig, build_prompt_text(dc, meta), meta

    except Exception as e:
        import traceback
        err_detail = traceback.format_exc()
        print(f"[CipherX ERROR] {ticker}: {err_detail}")
        return None, f"로딩 실패: {type(e).__name__}: {e}", None


# ──────────────────────────────────────────
# 스피도미터 게이지 (🆕 3개: Confluence + Bias + Anticipation)
# ──────────────────────────────────────────
def build_speedometer_gauges(meta):
    conf_score = meta.get('confluence_score', 0)
    bias_score = meta.get('bias_score', 0)
    bias_label = meta.get('overall_bias', 'NEUTRAL')

    # 🆕 선행 지표 넷 스코어
    antic_net = meta.get('setup_pressure_buy', 0) - meta.get('setup_pressure_sell', 0)

    if conf_score >= 6.5: cc = "#34D399"
    elif conf_score >= 3.5: cc = "#6EE7B7"
    elif conf_score <= -6.5: cc = "#F87171"
    elif conf_score <= -3.5: cc = "#FCA5A5"
    else: cc = "#FCD34D"

    bc_map = {'STRONG BUY': '#34D399', 'BUY': '#6EE7B7',
              'STRONG SELL': '#F87171', 'SELL': '#FCA5A5', 'NEUTRAL': '#FCD34D'}
    bc = bc_map.get(bias_label, '#FCD34D')

    ac = '#34D399' if antic_net > 3 else ('#F87171' if antic_net < -3 else '#FCD34D')

    fig = make_subplots(rows=1, cols=3,
        specs=[[{"type": "indicator"}, {"type": "indicator"}, {"type": "indicator"}]],
        horizontal_spacing=0.06)

    fig.add_trace(go.Indicator(mode="gauge+number", value=conf_score,
        number=dict(font=dict(size=26, color="#F8FAFC", family="Pretendard")),
        title=dict(text="<b>🔥 Confluence</b>", font=dict(size=12, color="#94A3B8")),
        gauge=dict(axis=dict(range=[-10, 10], dtick=2.5,
                   tickfont=dict(size=9, color="#64748B")),
            bar=dict(color=cc, thickness=0.3), bgcolor="rgba(15,19,32,0.9)",
            borderwidth=1, bordercolor="#1E293B",
            steps=[dict(range=[-10, -3.5], color="rgba(239,68,68,0.1)"),
                dict(range=[-3.5, 3.5], color="rgba(245,158,11,0.06)"),
                dict(range=[3.5, 10], color="rgba(16,185,129,0.1)")],
            threshold=dict(line=dict(color="#F8FAFC", width=3),
                          thickness=0.8, value=conf_score))), row=1, col=1)

    fig.add_trace(go.Indicator(mode="gauge+number", value=bias_score,
        number=dict(font=dict(size=26, color="#F8FAFC", family="Pretendard"),
                    suffix=f" {bias_label}", valueformat=".1f"),
        title=dict(text="<b>🧭 Bias</b>", font=dict(size=12, color="#94A3B8")),
        gauge=dict(axis=dict(range=[-13, 13], dtick=3.25,
                   tickfont=dict(size=9, color="#64748B")),
            bar=dict(color=bc, thickness=0.3), bgcolor="rgba(15,19,32,0.9)",
            borderwidth=1, bordercolor="#1E293B",
            steps=[dict(range=[-13, -3.5], color="rgba(239,68,68,0.1)"),
                dict(range=[-3.5, 3.5], color="rgba(245,158,11,0.06)"),
                dict(range=[3.5, 13], color="rgba(16,185,129,0.1)")],
            threshold=dict(line=dict(color="#F8FAFC", width=3),
                          thickness=0.8, value=bias_score))), row=1, col=2)

    # 🆕 Anticipation 게이지
    fig.add_trace(go.Indicator(mode="gauge+number", value=antic_net,
        number=dict(font=dict(size=26, color="#F8FAFC", family="Pretendard"),
                    valueformat="+.1f"),
        title=dict(text="<b>⏳ Anticipation</b>", font=dict(size=12, color="#94A3B8")),
        gauge=dict(axis=dict(range=[-12, 12], dtick=3,
                   tickfont=dict(size=9, color="#64748B")),
            bar=dict(color=ac, thickness=0.3), bgcolor="rgba(15,19,32,0.9)",
            borderwidth=1, bordercolor="#1E293B",
            steps=[dict(range=[-12, -3], color="rgba(239,68,68,0.1)"),
                dict(range=[-3, 3], color="rgba(245,158,11,0.06)"),
                dict(range=[3, 12], color="rgba(16,185,129,0.1)")],
            threshold=dict(line=dict(color="#F8FAFC", width=3),
                          thickness=0.8, value=antic_net))), row=1, col=3)

    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", height=220, margin=dict(l=15, r=15, t=50, b=10),
        font=dict(family="Pretendard"))
    return fig


# ══════════════════════════════════════════
#  PART 3/4 끝
#  다음: PART 4/4 — UI 렌더 + 사이드바 + 챗 인터페이스
# ══════════════════════════════════════════
# ══════════════════════════════════════════════════════════════
#  CipherX V12.0 — PART 4/4
#  UI 렌더 함수 + 사이드바 + 챗 인터페이스
#  🆕 확신도 표시, 8-Layer, 선행 지표 UI
#  🔧 st.fragment, st.metric, st.query_params 활용
# ══════════════════════════════════════════════════════════════


# ──────────────────────────────────────────
# 매매 판단 UI (🆕 확신도 + 8-Layer + Anticipation)
# ──────────────────────────────────────────
def render_judgment(meta):
    jd = meta.get('judgment_detail')
    if not jd:
        st.info("매매 판단 데이터가 없습니다.")
        return

    judgment = jd['judgment']
    buy_t = jd['buy_total']
    sell_t = jd['sell_total']
    net = buy_t - sell_t
    confidence = jd.get('confidence', 0)

    if 'BUY' in judgment:
        card_cls = 'judgment-card-buy'
    elif 'SELL' in judgment:
        card_cls = 'judgment-card-sell'
    else:
        card_cls = 'judgment-card-neutral'

    j_label, j_color, _ = JUDGMENT_CONFIG.get(judgment, ('⚪ NEUTRAL', '#64748B', ''))
    net_color = '#34D399' if net > 0 else ('#F87171' if net < 0 else '#FCD34D')

    # 🆕 확신도 바 색상
    conf_bar_color = j_color if confidence >= 60 else ('#FCD34D' if confidence >= 30 else '#475569')

    st.markdown(f"""
    <div class="judgment-card {card_cls}">
        <p style="font-size:2rem;font-weight:800;color:{j_color};margin:0;
           text-shadow:0 0 30px {j_color}40">{j_label}</p>
        <div style="margin-top:8px">
            <p style="color:#64748B;font-size:.7rem;margin:0;text-transform:uppercase;
               letter-spacing:1px">CONFIDENCE</p>
            <div style="display:flex;align-items:center;gap:10px;justify-content:center;margin-top:4px">
                <div style="flex:0 0 200px;height:8px;background:#151921;border-radius:4px;overflow:hidden">
                    <div style="width:{min(confidence, 100)}%;height:8px;background:{conf_bar_color};
                         border-radius:4px;transition:width .5s ease"></div>
                </div>
                <span style="color:{conf_bar_color};font-weight:800;font-size:1.1rem">{confidence:.0f}%</span>
            </div>
        </div>
        <div style="display:flex;justify-content:center;gap:32px;margin-top:14px">
            <div>
                <p style="color:#64748B;font-size:.7rem;margin:0;text-transform:uppercase;letter-spacing:1px">BUY Score</p>
                <p style="color:#34D399;font-size:1.4rem;font-weight:800;margin:2px 0 0 0">{buy_t:.1f}</p>
            </div>
            <div style="border-left:1px solid rgba(255,255,255,0.08);padding-left:32px">
                <p style="color:#64748B;font-size:.7rem;margin:0;text-transform:uppercase;letter-spacing:1px">SELL Score</p>
                <p style="color:#F87171;font-size:1.4rem;font-weight:800;margin:2px 0 0 0">{sell_t:.1f}</p>
            </div>
            <div style="border-left:1px solid rgba(255,255,255,0.08);padding-left:32px">
                <p style="color:#64748B;font-size:.7rem;margin:0;text-transform:uppercase;letter-spacing:1px">NET</p>
                <p style="color:{net_color};font-size:1.4rem;font-weight:800;margin:2px 0 0 0">{net:+.1f}</p>
            </div>
        </div>
    </div>""", unsafe_allow_html=True)

    # ── 🆕 선행 지표 요약 카드 ──
    sb_v = jd.get('setup_pressure_buy', 0)
    ss_v = jd.get('setup_pressure_sell', 0)
    accel = jd.get('composite_accel', 0)
    antic_net = sb_v - ss_v

    if abs(antic_net) > 2 or abs(accel) > JT.ACCEL_MODERATE:
        if antic_net > 0:
            antic_cls, antic_border = 'rgba(16,185,129,.06)', '#10B981'
            antic_label = '⏳ 매수 셋업 축적 중'
        elif antic_net < 0:
            antic_cls, antic_border = 'rgba(239,68,68,.06)', '#EF4444'
            antic_label = '⏳ 매도 셋업 축적 중'
        else:
            antic_cls, antic_border = 'rgba(245,158,11,.06)', '#F59E0B'
            antic_label = '⏳ 셋업 균형'

        accel_icon = '🚀' if accel > JT.ACCEL_MODERATE else ('💨' if accel < -JT.ACCEL_MODERATE else '➡️')
        accel_text = f"가속도: {accel:+.2f}"

        st.markdown(f"""<div style="border-radius:12px;padding:14px 18px;margin:8px 0;
            background:{antic_cls};border:1px solid {antic_border}30;border-left:3px solid {antic_border}">
            <div style="display:flex;justify-content:space-between;align-items:center">
                <span style="color:#E8ECF1;font-weight:700;font-size:.9rem">{antic_label}</span>
                <span style="color:#94A3B8;font-size:.8rem">{accel_icon} {accel_text}</span>
            </div>
            <div style="display:flex;gap:16px;margin-top:8px">
                <span style="color:#34D399;font-size:.8rem;font-weight:600">
                    BUY Setup: {sb_v:.1f}</span>
                <span style="color:#F87171;font-size:.8rem;font-weight:600">
                    SELL Setup: {ss_v:.1f}</span>
            </div>
        </div>""", unsafe_allow_html=True)

    # ── 활성 콤보 ──
    combos = jd.get('active_combos', [])
    st.markdown("#### 🔥 활성 매매 콤보")
    if combos:
        for cb in combos:
            cc = 'combo-buy' if cb['dir'] == 'buy' else 'combo-sell'
            dot_c = '#34D399' if cb['dir'] == 'buy' else '#F87171'
            side_label = 'BUY' if cb['dir'] == 'buy' else 'SELL'
            tier = cb.get('tier', 2)
            tier_label = f"T{tier}"
            tier_color = '#FFD700' if tier == 1 else ('#C0C0C0' if tier == 2 else '#CD7F32')
            st.markdown(f"""<div class="combo-card {cc}">
                <div style="display:flex;align-items:center;gap:10px">
                    <span style="color:{dot_c};font-size:1.2rem">●</span>
                    <span style="color:#E8ECF1;font-weight:700;font-size:.95rem">{cb['name']}</span>
                </div>
                <div style="display:flex;gap:8px;align-items:center">
                    <span style="color:{tier_color};font-size:.7rem;font-weight:700;
                        padding:2px 6px;border-radius:4px;background:rgba(255,255,255,0.05)">{tier_label}</span>
                    <span style="color:{dot_c};font-size:.75rem;font-weight:600;padding:3px 10px;
                        border-radius:6px;background:rgba(255,255,255,0.04)">{side_label}</span>
                </div>
            </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""<div class="combo-card" style="background:rgba(245,158,11,.04);
            border:1px solid rgba(245,158,11,.15);border-left:3px solid #F59E0B;justify-content:center">
            <span style="color:#FCD34D;font-weight:600;font-size:.9rem">
                ⏸️ 활성 콤보 없음 — 관망 구간</span></div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── 8-Layer 점수 ──
    st.markdown("#### 📊 8-Layer 스코어 분석")
    col_b, col_s = st.columns(2)
    with col_b:
        st.markdown("<p style='color:#34D399;font-weight:700;font-size:.85rem;margin-bottom:8px;"
                    "text-transform:uppercase;letter-spacing:1px'>▲ BUY LAYERS</p>",
                    unsafe_allow_html=True)
        _render_layer_bars(jd['buy_layers'], 'buy', jd['buy_active'])
    with col_s:
        st.markdown("<p style='color:#F87171;font-weight:700;font-size:.85rem;margin-bottom:8px;"
                    "text-transform:uppercase;letter-spacing:1px'>▼ SELL LAYERS</p>",
                    unsafe_allow_html=True)
        _render_layer_bars(jd['sell_layers'], 'sell', jd['sell_active'])

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── 판단 기준 ──
    with st.expander("📐 판단 기준 상세", expanded=False):
        rows_html = ""
        criteria = [
            ('STRONG_BUY', '🟢🟢🟢 STRONG BUY',
             f'BUY ≥ {JT.STRONG_BUY_SCORE:.0f} + {JT.STRONG_BUY_LAYERS}층↑ + ratio≥{JT.STRONG_BUY_RATIO}'),
            ('BUY', '🟢🟢 BUY',
             f'BUY ≥ {JT.BUY_SCORE:.0f} + {JT.BUY_LAYERS}층↑ + ratio≥{JT.BUY_RATIO}'),
            ('WATCH_BUY', '🟡🟢 WATCH BUY',
             f'BUY ≥ {JT.WATCH_BUY_SCORE:.0f} + {JT.WATCH_LAYERS}층↑'),
            ('NEUTRAL', '⚪ NEUTRAL', '기준 미달'),
            ('MIXED', '🟠 MIXED',
             f'BUY ≥ {JT.MIXED_MIN:.0f} & SELL ≥ {JT.MIXED_MIN:.0f}'),
            ('WATCH_SELL', '🟡🔴 WATCH SELL',
             f'SELL ≥ {JT.WATCH_BUY_SCORE*JT.SELL_ASYMMETRY:.0f} + {JT.WATCH_LAYERS}층↑'),
            ('SELL', '🔴🔴 SELL',
             f'SELL ≥ {JT.BUY_SCORE*JT.SELL_ASYMMETRY:.0f} + {JT.BUY_LAYERS}층↑'),
            ('STRONG_SELL', '🔴🔴🔴 STRONG SELL',
             f'SELL ≥ {JT.STRONG_BUY_SCORE*JT.SELL_ASYMMETRY:.0f} + {JT.STRONG_BUY_LAYERS}층↑'),
        ]
        for key, label, cond in criteria:
            is_active = judgment == key
            bg = 'rgba(99,102,241,.1)' if is_active else 'transparent'
            badge = '<span style="color:#A5B4FC;font-weight:700">✅ 현재</span>' if is_active else ''
            rows_html += f"""<div style="display:flex;align-items:center;padding:6px 12px;
                margin:2px 0;border-radius:8px;background:{bg}">
                <span style="color:#CBD5E1;font-weight:600;width:200px;font-size:.85rem">{label}</span>
                <span style="color:#64748B;font-size:.8rem;flex:1">{cond}</span>
                {badge}</div>"""
        st.markdown(rows_html, unsafe_allow_html=True)

    # ── 최근 5일 이력 (🆕 확신도 포함) ──
    jh = meta.get('judgment_history', [])
    if jh:
        st.markdown("#### 📅 최근 5일 판단 추이")
        for day in reversed(jh):
            j_cfg_d = JUDGMENT_CONFIG.get(day['judgment'], ('⚪', '#64748B', ''))
            combo_str = ', '.join([c['name'] for c in day['combos']]) if day['combos'] else '—'
            b_pct = min(day['buy_total'] / 30 * 100, 100)
            s_pct = min(day['sell_total'] / 30 * 100, 100)
            conf_v = day.get('confidence', 0)
            conf_color = j_cfg_d[1] if conf_v >= 60 else '#FCD34D'
            st.markdown(f"""<div class="history-row">
                <span style="color:#64748B;font-size:.85rem;width:45px;font-weight:600">{day['date']}</span>
                <span style="color:{j_cfg_d[1]};font-weight:700;font-size:.75rem;width:130px">{j_cfg_d[0]}</span>
                <span style="color:{conf_color};font-size:.7rem;font-weight:600;width:35px">{conf_v:.0f}%</span>
                <div style="flex:1;display:flex;align-items:center;gap:6px">
                    <div style="flex:1">
                        <div style="display:flex;gap:4px;align-items:center">
                            <div style="flex:1;height:4px;background:#151921;border-radius:2px;overflow:hidden">
                                <div style="width:{b_pct}%;height:4px;background:#34D399;border-radius:2px"></div></div>
                            <span style="color:#34D399;font-size:.7rem;width:28px;text-align:right">{day['buy_total']:.0f}</span>
                        </div>
                        <div style="display:flex;gap:4px;align-items:center;margin-top:2px">
                            <div style="flex:1;height:4px;background:#151921;border-radius:2px;overflow:hidden">
                                <div style="width:{s_pct}%;height:4px;background:#F87171;border-radius:2px"></div></div>
                            <span style="color:#F87171;font-size:.7rem;width:28px;text-align:right">{day['sell_total']:.0f}</span>
                        </div>
                    </div>
                </div>
                <span style="color:#475569;font-size:.7rem;width:120px;text-align:right;overflow:hidden;
                    text-overflow:ellipsis;white-space:nowrap">{combo_str}</span>
            </div>""", unsafe_allow_html=True)


def _render_layer_bars(layers, side, active_count):
    """8-Layer 바 렌더 (🆕 Anticipation 포함)"""
    icons = {'Trend': '📈', 'Momentum': '🔥', 'Candle': '🕯️', 'BB': '📊',
             'Volume': '📦', 'MF': '💰', 'Pattern': '⭐', 'Anticipation': '⏳'}
    max_per = 10.0
    fill_cls = 'layer-bar-fill-buy' if side == 'buy' else 'layer-bar-fill-sell'
    score_color = '#34D399' if side == 'buy' else '#F87171'
    total = sum(max(0, v) for v in layers.values())  # 양수만 합산

    for name, score in layers.items():
        icon = icons.get(name, '•')
        pct = min(max(score, 0) / max_per * 100, 100)
        opacity = '1' if score > 0 else ('0.5' if score < 0 else '0.2')
        # 🔧 음수 점수 표시: 빨간색으로 역방향 표시
        if score < 0:
            display_color = '#F87171' if side == 'buy' else '#34D399'
            indicator = f'<span style="color:{display_color};font-size:.7rem">⚠️</span>'
        elif score > 0:
            indicator = '✓'
        else:
            indicator = ''

        st.markdown(f"""<div class="layer-bar-wrap">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px">
                <span style="color:#94A3B8;font-size:.8rem;font-weight:500;opacity:{opacity}">{icon} {name}</span>
                <span style="color:{score_color if score >= 0 else display_color if score < 0 else '#475569'};
                    font-weight:700;font-size:.8rem;opacity:{opacity}">
                    {score:.1f} {indicator}</span>
            </div>
            <div class="layer-bar-bg">
                <div class="layer-bar-fill {fill_cls}" style="width:{pct}%;opacity:{opacity}"></div>
            </div>
        </div>""", unsafe_allow_html=True)

    st.markdown(f"""<div style="margin-top:12px;padding:10px 14px;border-radius:10px;
        background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.04);text-align:center">
        <span style="color:{score_color};font-weight:800;font-size:1.15rem">{total:.1f}</span>
        <span style="color:#475569;font-size:.8rem;font-weight:500"> 점 · 활성 </span>
        <span style="color:#CBD5E1;font-weight:700;font-size:.85rem">{active_count}</span>
        <span style="color:#475569;font-size:.8rem">/{NUM_LAYERS}</span>
    </div>""", unsafe_allow_html=True)


# ──────────────────────────────────────────
# 가격 헤더 (🆕 확신도 + Anticipation metric)
# ──────────────────────────────────────────
_IT = {'wt1': [(-53, '극과매도'), (-20, '과매도'), (20, '중립'), (53, '과매수'), (999, '극과매수')],
       'rsi': [(30, '과매도'), (45, '약세'), (55, '중립'), (70, '강세'), (999, '과매수')],
       'mfi': [(30, '과매도'), (45, '약세'), (55, '중립'), (70, '강세'), (999, '과매수')],
       'stochk': [(20, '바닥'), (80, ''), (999, '천장')]}

def _il(n, v):
    for t, l in _IT.get(n, []):
        if v <= t:
            return l
    return ''


def render_price_header(m):
    chg = m['price_change']
    cp = m['price_change_pct']
    cc = 'price-change-up' if chg >= 0 else 'price-change-down'
    ci = '▲' if chg >= 0 else '▼'
    vr = m['volume'] / m['avg_volume'] if m['avg_volume'] else 0
    cv = m.get('confluence_score', 0)
    sd = m.get('supertrend_dir', 0)
    sh = m.get('shield_status', '')
    mh_val = m.get('macd_hist', 0)
    accel = m.get('composite_accel', 0)

    jd = m.get('judgment_detail', {})
    j_short = jd.get('judgment', 'NEUTRAL') if jd else 'N/A'
    confidence = jd.get('confidence', 0) if jd else 0
    j_color_map = {
        'STRONG_BUY': 'ind-bullish', 'BUY': 'ind-bullish', 'WATCH_BUY': 'ind-neutral',
        'STRONG_SELL': 'ind-bearish', 'SELL': 'ind-bearish', 'WATCH_SELL': 'ind-neutral',
        'MIXED': 'ind-neutral', 'NEUTRAL': 'ind-neutral',
    }
    j_cls = j_color_map.get(j_short, 'ind-neutral')

    specs = [
        (j_cls, f"📍 {j_short} ({confidence:.0f}%)"),
        (_cls(m['wt1'], -20, 20), f"WT {m['wt1']:.0f} {_il('wt1', m['wt1'])}"),
        (_cls(m['rsi'], 40, 60), f"RSI {m['rsi']:.0f}"),
        (_cls(m['mfi'], 40, 60), f"MFI {m['mfi']:.0f}"),
        ('ind-bullish' if m['mf_area'] < 0 else ('ind-bearish' if m['mf_area'] > 0 else 'ind-neutral'),
         f"MF {m['mf_area']:.1f}"),
        ('ind-bullish' if vr > 1.5 else 'ind-neutral', f"Vol {vr:.1f}x"),
        ('ind-bullish' if m['adx'] > 25 else 'ind-neutral', f"ADX {m['adx']:.0f}"),
        (_cls(m['stochk'], 30, 70), f"StK {m['stochk']:.0f}"),
        ('ind-bullish' if cv >= 3.5 else ('ind-bearish' if cv <= -3.5 else 'ind-neutral'),
         f"Conf {cv:.1f}"),
        ('ind-bullish' if sd == 1 else 'ind-bearish', f"ST {'▲' if sd == 1 else '▼'}"),
        ('ind-bullish' if mh_val > 0 else ('ind-bearish' if mh_val < 0 else 'ind-neutral'),
         f"MACD {mh_val:+.2f}"),
        ('ind-bullish' if m.get('cmf', 0) > 0.05 else
         ('ind-bearish' if m.get('cmf', 0) < -0.05 else 'ind-neutral'),
         f"CMF {m.get('cmf', 0):.2f}"),
        # 🆕 가속도 미니 인디케이터
        ('ind-bullish' if accel > JT.ACCEL_MODERATE else
         ('ind-bearish' if accel < -JT.ACCEL_MODERATE else 'ind-neutral'),
         f"Accel {accel:+.1f}"),
    ]
    ih = "".join([f"<span class='indicator-mini {c}'>{l}</span>" for c, l in specs])
    if sh:
        ih += f"<span class='indicator-mini ind-bearish' style='font-weight:700'>🔓 {sh}</span>"
    tr = m.get('trend_regime', 'NEUTRAL ⚪')

    st.markdown(f"""<div class="price-header">
        <div style="display:flex;justify-content:space-between;align-items:flex-start">
            <div>
                <p class="price-label">🚦 {m['ticker']} · {m['last_date']} · <b style="color:#A5B4FC">{tr}</b></p>
                <p class="price-big" style="color:#F8FAFC">${m['price']:.2f}
                    <span class="{cc}" style="font-size:1.1rem;margin-left:10px;font-weight:700">
                        {ci} {abs(chg):.2f} ({abs(cp):.2f}%)</span></p>
            </div>
            <div style="text-align:right;padding-top:4px">
                <p class="price-label">ATR (14)</p>
                <p style="color:#FCD34D;font-size:1.2rem;font-weight:700;margin:2px 0 0 0">
                    ${m['atr']:.2f} <span style="font-size:.85rem;color:#D97706">({m['atr_pct']:.1f}%)</span></p>
            </div>
        </div>
        <div style="margin-top:12px;display:flex;gap:5px;flex-wrap:wrap">{ih}</div>
    </div>""", unsafe_allow_html=True)

    # st.metric 활용 (🆕 5개: BUY/SELL/NET/Confidence/Anticipation)
    mc1, mc2, mc3, mc4, mc5 = st.columns(5)
    with mc1:
        st.metric("BUY Score",
                   f"{jd.get('buy_total', 0):.1f}",
                   delta=f"{jd.get('buy_active', 0)}/{NUM_LAYERS} layers",
                   delta_color="normal")
    with mc2:
        st.metric("SELL Score",
                   f"{jd.get('sell_total', 0):.1f}",
                   delta=f"{jd.get('sell_active', 0)}/{NUM_LAYERS} layers",
                   delta_color="inverse")
    with mc3:
        net_val = jd.get('buy_total', 0) - jd.get('sell_total', 0)
        st.metric("NET Score", f"{net_val:+.1f}",
                   delta=j_short,
                   delta_color="normal" if net_val > 0 else "inverse")
    with mc4:
        st.metric("Confidence", f"{confidence:.0f}%",
                   delta=m.get('overall_bias', 'N/A'),
                   delta_color="normal" if confidence >= 60 else "off")
    with mc5:
        antic = m.get('setup_pressure_buy', 0) - m.get('setup_pressure_sell', 0)
        accel_delta = f"Accel {accel:+.1f}"
        st.metric("⏳ Anticipation", f"{antic:+.1f}",
                   delta=accel_delta,
                   delta_color="normal" if antic > 0 else ("inverse" if antic < 0 else "off"))


def render_speedometer(m):
    gauge_fig = build_speedometer_gauges(m)
    st.plotly_chart(gauge_fig, use_container_width=True, theme=None,
                    config={'displayModeBar': False})
    bias = m['overall_bias']
    sc = m.get('bias_score', 0)
    styles = {
        'STRONG BUY': ('rgba(16,185,129,.1)', '#34D399', '🟢🟢'),
        'BUY': ('rgba(16,185,129,.06)', '#34D399', '🟢'),
        'STRONG SELL': ('rgba(239,68,68,.1)', '#F87171', '🔴🔴'),
        'SELL': ('rgba(239,68,68,.06)', '#F87171', '🔴'),
    }
    bg, clr, ico = styles.get(bias, ('rgba(245,158,11,.06)', '#FCD34D', '🟠'))
    bp = m.get('buy_proximity', 0)
    sp = m.get('sell_proximity', 0)
    prox_txt = ""
    if bp >= 50:
        prox_txt = f"<span style='color:#34D399;font-weight:600'>매수 임박 {bp:.0f}%</span>"
    elif sp >= 50:
        prox_txt = f"<span style='color:#F87171;font-weight:600'>매도 임박 {sp:.0f}%</span>"
    sq_txt = (" · <span style='color:#FCD34D;font-weight:700'>💥 Squeeze ON</span>"
              if m.get('squeeze_on') else "")
    st.markdown(f"""<div style="background:{bg};border-radius:12px;padding:12px 18px;
        text-align:center;margin:4px 0 14px 0;border:1px solid rgba(255,255,255,0.06)">
        <span style="font-size:1.05rem;font-weight:700;color:{clr}">{ico} 종합 판정: {bias} ({sc:.1f})</span>
        {f' · {prox_txt}' if prox_txt else ''}{sq_txt}</div>""", unsafe_allow_html=True)


def render_alerts(m):
    alerts = []
    bp, sp = m.get('buy_proximity', 0), m.get('sell_proximity', 0)
    if bp >= 70:
        alerts.append(('🟢⚡ 매수 매우 임박!', '#34D399', 'rgba(16,185,129,.08)', bp))
    elif bp >= 50:
        alerts.append(('🟢 매수 접근 중', '#6EE7B7', 'rgba(16,185,129,.05)', bp))
    if sp >= 70:
        alerts.append(('🔴⚡ 매도 매우 임박!', '#F87171', 'rgba(239,68,68,.08)', sp))
    elif sp >= 50:
        alerts.append(('🔴 매도 접근 중', '#FCA5A5', 'rgba(239,68,68,.05)', sp))
    if m.get('squeeze_on'):
        alerts.append(('💥 TTM Squeeze ON — 돌파 임박', '#FCD34D', 'rgba(245,158,11,.06)', 80))

    # 🆕 선행 지표 알림
    accel = m.get('composite_accel', 0)
    if accel > JT.ACCEL_STRONG:
        alerts.append(('⚡ 모멘텀 강한 상승 가속!', '#34D399', 'rgba(16,185,129,.06)', 70))
    elif accel < -JT.ACCEL_STRONG:
        alerts.append(('⚡ 모멘텀 강한 하락 가속!', '#F87171', 'rgba(239,68,68,.06)', 70))
    sb_v = m.get('setup_pressure_buy', 0)
    ss_v = m.get('setup_pressure_sell', 0)
    if sb_v >= 8:
        alerts.append(('⏳ 매수 셋업 고도 축적', '#6EE7B7', 'rgba(16,185,129,.05)', 60))
    if ss_v >= 8:
        alerts.append(('⏳ 매도 셋업 고도 축적', '#FCA5A5', 'rgba(239,68,68,.05)', 60))

    jd = m.get('judgment_detail', {})
    j = jd.get('judgment', 'NEUTRAL')
    conf = jd.get('confidence', 0)
    if j == 'STRONG_BUY':
        alerts.insert(0, (f'🟢🟢🟢 STRONG BUY ({conf:.0f}%)', '#34D399', 'rgba(16,185,129,.1)', 95))
    elif j == 'BUY':
        alerts.insert(0, (f'🟢🟢 BUY ({conf:.0f}%)', '#34D399', 'rgba(16,185,129,.06)', 75))
    elif j == 'STRONG_SELL':
        alerts.insert(0, (f'🔴🔴🔴 STRONG SELL ({conf:.0f}%)', '#F87171', 'rgba(239,68,68,.1)', 95))
    elif j == 'SELL':
        alerts.insert(0, (f'🔴🔴 SELL ({conf:.0f}%)', '#F87171', 'rgba(239,68,68,.06)', 75))

    for txt, clr, bg, pct in alerts:
        w = min(pct, 100)
        st.markdown(f"""<div class="alert-bar" style="background:{bg}">
            <div style="display:flex;justify-content:space-between;align-items:center">
                <span style="color:{clr};font-weight:700;font-size:.9rem">{txt}</span>
                <span style="color:{clr};font-weight:800;font-size:.85rem">{pct:.0f}%</span></div>
            <div class="alert-bar-progress">
                <div class="alert-bar-fill" style="background:{clr};width:{w}%"></div></div>
        </div>""", unsafe_allow_html=True)


def render_signals(m):
    sigs = m['recent_signals']
    if not sigs:
        st.markdown("""<div class="signal-card signal-card-neutral" style="text-align:center">
            <p style="margin:0;color:#FCD34D;font-weight:600">⏸️ 최근 15일 내 포착된 시그널 없음</p></div>""",
                    unsafe_allow_html=True)
        return
    dg = OrderedDict()
    for icon, lbl, ds, side in sigs:
        dg.setdefault(ds, []).append((icon, lbl, side))

    for ds in reversed(dg):
        group = dg[ds]
        bc_cnt = sum(1 for _, _, s in group if s == 'buy')
        sc_cnt = sum(1 for _, _, s in group if s == 'sell')
        ct = ('signal-card-buy' if bc_cnt > sc_cnt
              else ('signal-card-sell' if sc_cnt > bc_cnt else 'signal-card-neutral'))
        parts = []
        for i, l, s in group:
            cn = ("ind-bullish" if s == "buy" else
                  ("ind-bearish" if s == "sell" else "ind-neutral"))
            parts.append(f'<span class="indicator-mini {cn}">{i} {l}</span>')

        date_color = '#34D399' if bc_cnt > sc_cnt else ('#F87171' if sc_cnt > bc_cnt else '#FCD34D')
        st.markdown(f"""<div class="signal-card {ct}">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                <span style="font-weight:700;font-size:.9rem;color:#E8ECF1">📅 {ds}</span>
                <span style="color:{date_color};font-size:.75rem;font-weight:600;
                    padding:2px 8px;border-radius:6px;background:rgba(255,255,255,0.04)">{len(group)}개 시그널</span></div>
            <div style="display:flex;gap:5px;flex-wrap:wrap">{" ".join(parts)}</div></div>""",
                    unsafe_allow_html=True)


def render_scanner_tab(m):
    """개별 종목의 스캐너 콤보 결과 표시"""
    ticker = m['ticker']
    st.markdown(f"### 🔍 {ticker} 스캐너 콤보")
    
    # scan_ticker 결과 가져오기
    result = scan_ticker(ticker)
    
    if not result or not result['active_combos']:
        st.info("최근 5일 내 활성 스캐너 콤보가 없습니다.")
        
        # 콤보 설명 표시
        with st.expander("📋 사용 가능한 콤보 목록 (20종)", expanded=False):
            for combo_name, combo_cfg in SCANNER_COMBOS.items():
                dir_icon = '🟢' if combo_cfg['dir'] == 'buy' else '🔴'
                tier_stars = '⭐' * (3 - combo_cfg['tier'] + 1)
                st.markdown(f"""<div style="display:flex;align-items:center;gap:10px;
                    padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.03)">
                    <span>{dir_icon} {combo_cfg['icon']}</span>
                    <span style="color:#E8ECF1;font-weight:600;flex:1">{combo_cfg['kor']}</span>
                    <span style="color:#94A3B8;font-size:.8rem;flex:2">{combo_cfg['desc']}</span>
                    <span>{tier_stars}</span>
                </div>""", unsafe_allow_html=True)
        return
    
    # 활성 콤보 표시
    buy_combos = result['buy_combos']
    sell_combos = result['sell_combos']
    
    if buy_combos:
        st.markdown("#### 🟢 매수 콤보")
        for c in buy_combos:
            tier_stars = '⭐' * (3 - c['tier'] + 1)
            st.markdown(f"""<div class="combo-card combo-buy">
                <div style="display:flex;align-items:center;gap:10px;flex:1">
                    <span style="font-size:1.2rem">{c['icon']}</span>
                    <div>
                        <span style="color:#E8ECF1;font-weight:700">{c['kor']}</span><br>
                        <span style="color:#94A3B8;font-size:.8rem">{c['desc']}</span>
                    </div>
                </div>
                <div style="text-align:right">
                    <span style="font-size:.85rem">{tier_stars}</span><br>
                    <span style="color:#64748B;font-size:.75rem">{c['date']}</span>
                </div>
            </div>""", unsafe_allow_html=True)
    
    if sell_combos:
        st.markdown("#### 🔴 매도 콤보")
        for c in sell_combos:
            tier_stars = '⭐' * (3 - c['tier'] + 1)
            st.markdown(f"""<div class="combo-card combo-sell">
                <div style="display:flex;align-items:center;gap:10px;flex:1">
                    <span style="font-size:1.2rem">{c['icon']}</span>
                    <div>
                        <span style="color:#E8ECF1;font-weight:700">{c['kor']}</span><br>
                        <span style="color:#94A3B8;font-size:.8rem">{c['desc']}</span>
                    </div>
                </div>
                <div style="text-align:right">
                    <span style="font-size:.85rem">{tier_stars}</span><br>
                    <span style="color:#64748B;font-size:.75rem">{c['date']}</span>
                </div>
            </div>""", unsafe_allow_html=True)

# ──────────────────────────────────────────
# 메인 분석 렌더 (🆕 5탭: 선행 지표 탭 추가)
# ──────────────────────────────────────────
def render_analysis(msg):
    m, fig = msg.get('meta'), msg.get('fig')
    if m:
        render_price_header(m)
        render_speedometer(m)
        render_alerts(m)
    if m or fig:
        t0, t1, t2, t3, t4, t5 = st.tabs([
            "🎯 매매 판단",
            "📊 차트",
            "⏳ 선행 지표",
            "🔔 시그널 이력",
            "🔍 스캐너 콤보",   # 🆕
            "🏢 기업 상세",
        ])
        with t0:
            if m:
                render_judgment(m)
        with t1:
            plotly_config = {
                'displaylogo': False,
                'modeBarButtonsToRemove': ['lasso2d', 'select2d',
                    'hoverCompareCartesian', 'hoverClosestCartesian'],
            }
            if fig:
                st.plotly_chart(fig, use_container_width=True, theme=None,
                                config=plotly_config)
        with t2:
            if m:
                render_anticipation_tab(m)
        with t3:
            if m:
                render_signals(m)
        with t4:
            if m:
                render_scanner_tab(m)
        with t5:
            if m:
                render_company_details(m['ticker'])


# ──────────────────────────────────────────
# 🆕 선행 지표 전용 탭
# ──────────────────────────────────────────
def render_anticipation_tab(m):
    """선행 지표를 상세하게 보여주는 전용 탭"""
    jd = m.get('judgment_detail', {})
    accel = m.get('composite_accel', 0)
    rsi_accel = m.get('rsi_accel', 0)
    sb_v = m.get('setup_pressure_buy', 0)
    ss_v = m.get('setup_pressure_sell', 0)
    wt_conv = m.get('wt_conv_speed', 0)
    wt1 = m.get('wt1', 0)
    wt2 = m.get('wt2', 0)
    wt_gap = abs(wt1 - wt2)

    st.markdown("### ⏳ 선행 지표 분석 (Anticipation)")
    st.markdown("""<p style='color:#94A3B8;font-size:.85rem;line-height:1.6'>
        선행 지표는 <b>아직 발생하지 않은 시그널</b>의 가능성을 미리 감지합니다.
        모멘텀 가속도, 셋업 축적, WT 수렴 속도를 종합하여
        <b>향후 1~3일 내 움직임</b>을 예측합니다.</p>""", unsafe_allow_html=True)

    # ── 모멘텀 가속도 ──
    st.markdown("#### 🚀 모멘텀 가속도 (Composite Acceleration)")
    if accel > JT.ACCEL_STRONG:
        accel_status = "🟢🟢 강한 상승 가속"
        accel_bg = 'rgba(16,185,129,.08)'
    elif accel > JT.ACCEL_MODERATE:
        accel_status = "🟢 상승 가속"
        accel_bg = 'rgba(16,185,129,.05)'
    elif accel > 0.5:
        accel_status = "🟡 약한 상승 모멘텀"
        accel_bg = 'rgba(245,158,11,.05)'
    elif accel > -0.5:
        accel_status = "⚪ 중립"
        accel_bg = 'rgba(128,128,128,.03)'
    elif accel > -JT.ACCEL_MODERATE:
        accel_status = "🟡 약한 하락 모멘텀"
        accel_bg = 'rgba(245,158,11,.05)'
    elif accel > -JT.ACCEL_STRONG:
        accel_status = "🔴 하락 가속"
        accel_bg = 'rgba(239,68,68,.05)'
    else:
        accel_status = "🔴🔴 강한 하락 가속"
        accel_bg = 'rgba(239,68,68,.08)'

    st.markdown(f"""<div style="background:{accel_bg};border-radius:12px;padding:16px 20px;
        margin:8px 0;border:1px solid rgba(255,255,255,0.06)">
        <div style="display:flex;justify-content:space-between;align-items:center">
            <span style="color:#E8ECF1;font-weight:700;font-size:1rem">{accel_status}</span>
            <span style="color:#A5B4FC;font-weight:800;font-size:1.2rem">{accel:+.2f}</span>
        </div>
        <p style="color:#64748B;font-size:.8rem;margin-top:6px">
            RSI, WT, MACD 3개 오실레이터의 가속도(2차 미분)를 정규화 후 평균.
            양수 = 상승 모멘텀 가속, 음수 = 하락 모멘텀 가속.</p>
    </div>""", unsafe_allow_html=True)

    ac1, ac2 = st.columns(2)
    with ac1:
        st.metric("RSI 가속도", f"{rsi_accel:+.1f}",
                   delta="상승 가속" if rsi_accel > 2 else ("하락 가속" if rsi_accel < -2 else "중립"),
                   delta_color="normal" if rsi_accel > 0 else ("inverse" if rsi_accel < 0 else "off"))
    with ac2:
        macd_accel = m.get('macd_hist', 0) - 0  # 단순 표시
        st.metric("MACD Hist", f"{m.get('macd_hist', 0):+.3f}",
                   delta="상승" if m.get('macd_hist', 0) > 0 else "하락",
                   delta_color="normal" if m.get('macd_hist', 0) > 0 else "inverse")

    # ── 셋업 축적 ──
    st.markdown("#### 📊 셋업 축적 점수 (Setup Pressure)")
    sc1, sc2 = st.columns(2)
    with sc1:
        sb_pct = min(sb_v / 12 * 100, 100)
        sb_color = '#34D399' if sb_v >= 5 else '#64748B'
        st.markdown(f"""<div style="background:rgba(16,185,129,.04);border-radius:10px;
            padding:14px;border:1px solid rgba(16,185,129,.15)">
            <p style="color:#34D399;font-weight:700;font-size:.85rem;margin:0">▲ BUY 셋업</p>
            <p style="color:#E8ECF1;font-weight:800;font-size:1.5rem;margin:4px 0">{sb_v:.1f}</p>
            <div style="height:8px;background:#151921;border-radius:4px;overflow:hidden;margin-top:6px">
                <div style="width:{sb_pct}%;height:8px;background:#34D399;border-radius:4px"></div>
            </div>
            <p style="color:#64748B;font-size:.75rem;margin-top:4px">
                {'🟢 매수 조건 축적 중' if sb_v >= 5 else '축적 부족'}</p>
        </div>""", unsafe_allow_html=True)
    with sc2:
        ss_pct = min(ss_v / 12 * 100, 100)
        st.markdown(f"""<div style="background:rgba(239,68,68,.04);border-radius:10px;
            padding:14px;border:1px solid rgba(239,68,68,.15)">
            <p style="color:#F87171;font-weight:700;font-size:.85rem;margin:0">▼ SELL 셋업</p>
            <p style="color:#E8ECF1;font-weight:800;font-size:1.5rem;margin:4px 0">{ss_v:.1f}</p>
            <div style="height:8px;background:#151921;border-radius:4px;overflow:hidden;margin-top:6px">
                <div style="width:{ss_pct}%;height:8px;background:#F87171;border-radius:4px"></div>
            </div>
            <p style="color:#64748B;font-size:.75rem;margin-top:4px">
                {'🔴 매도 조건 축적 중' if ss_v >= 5 else '축적 부족'}</p>
        </div>""", unsafe_allow_html=True)

    # ── WT 수렴 속도 ──
    st.markdown("#### 🔀 WaveTrend 수렴 분석")
    wt_direction = "아래 → 위 (매수 교차 임박)" if wt1 < wt2 else "위 → 아래 (매도 교차 임박)"
    conv_status = "빠르게 수렴 중" if wt_conv > JT.CONVERGENCE_FAST else (
        "수렴 중" if wt_conv > JT.CONVERGENCE_SLOW else "수렴 없음")

    wc1, wc2, wc3 = st.columns(3)
    with wc1:
        st.metric("WT1 - WT2 갭", f"{wt_gap:.1f}",
                   delta=f"{'수렴' if wt_conv > 0 else '발산'} {wt_conv:.1f}",
                   delta_color="normal" if wt_conv > 0 else "inverse")
    with wc2:
        st.metric("수렴 방향", wt_direction[:6],
                   delta=f"WT1={wt1:.0f}",
                   delta_color="off")
    with wc3:
        cross_est = f"~{max(1, int(wt_gap / max(wt_conv, 0.5)))}봉 후" if wt_conv > JT.CONVERGENCE_SLOW else "미정"
        st.metric("교차 예상", cross_est,
                   delta=conv_status,
                   delta_color="normal" if wt_conv > JT.CONVERGENCE_FAST else "off")

    # ── 종합 해석 ──
    st.markdown("#### 💡 선행 지표 종합 해석")
    interpretation = []
    if accel > JT.ACCEL_STRONG and sb_v >= 5:
        interpretation.append("🟢🟢 **강한 매수 신호 임박** — 모멘텀 가속 + 셋업 축적 충분")
    elif accel > JT.ACCEL_MODERATE:
        interpretation.append("🟢 **상승 모멘텀 강화 중** — 가속도가 양수로 전환")
    elif accel < -JT.ACCEL_STRONG and ss_v >= 5:
        interpretation.append("🔴🔴 **강한 매도 신호 임박** — 모멘텀 하락 가속 + 셋업 축적")
    elif accel < -JT.ACCEL_MODERATE:
        interpretation.append("🔴 **하락 모멘텀 강화 중** — 가속도가 음수로 전환")
    else:
        interpretation.append("🟠 **방향성 불명확** — 모멘텀 가속/감속 없음")

    if wt_conv > JT.CONVERGENCE_FAST and wt_gap < 10:
        cross_dir = "매수" if wt1 < wt2 else "매도"
        interpretation.append(f"⚡ WT 교차 임박 — **{cross_dir} 시그널** 1~3봉 내 예상")
    if sb_v >= 8:
        interpretation.append("⏳ 매수 셋업 **고도 축적** — 돌파 시 강한 상승 예상")
    if ss_v >= 8:
        interpretation.append("⏳ 매도 셋업 **고도 축적** — 이탈 시 강한 하락 예상")

    for line in interpretation:
        st.markdown(line)


# ──────────────────────────────────────────
# 사이드바 (🆕 선행 지표 토글)
# ──────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🚦 CipherX")
    st.markdown("<p style='color:#888;font-size:.8rem'>AI 퀀트 주가 분석 · Anticipatory v12.0</p>",
                unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("### 📅 차트 기간")
    chart_period = st.radio("표시 기간", ['3개월', '6개월', '1년', '2년'],
                            index=0, horizontal=True, key="period")
    chart_days = {'3개월': 63, '6개월': 126, '1년': 252, '2년': 504}[chart_period]
    st.markdown("---")

    with st.expander("🎛️ 차트 표시 설정", expanded=False):
        st.markdown("**표시할 판단 등급**")
        _show_strong = st.checkbox("🟢🔴 STRONG (강력 매수/매도)", value=True, key="j_strong")
        _show_normal = st.checkbox("🟢🔴 BUY / SELL (일반)", value=True, key="j_normal")
        _show_watch = st.checkbox("🟡 WATCH (관망)", value=False, key="j_watch")
        _show_mixed = st.checkbox("🟠 MIXED (혼조)", value=False, key="j_mixed")

        enabled_judgments = set()
        if _show_strong:
            enabled_judgments |= {'STRONG_BUY', 'STRONG_SELL'}
        if _show_normal:
            enabled_judgments |= {'BUY', 'SELL'}
        if _show_watch:
            enabled_judgments |= {'WATCH_BUY', 'WATCH_SELL'}
        if _show_mixed:
            enabled_judgments.add('MIXED')
        st.session_state['enabled_judgments'] = enabled_judgments
        st.caption(f"차트 표시: {len(enabled_judgments)}개 등급")
        st.session_state['enabled_signals'] = set(ALL_CHART_SIGNALS.keys())

        st.markdown("---")
        st.markdown("**🔍 스캐너 콤보**")
        _show_scanner = st.checkbox(
            "차트에 스캐너 콤보 마커 표시",
            value=True, key="show_sc")
        st.session_state['show_scanner_combos'] = _show_scanner

    if st.button("🗑️ 대화 내역 지우기", use_container_width=True, type="secondary"):
        for key in ['messages', 'pending_ai_ticker', 'pending_ai_prompt', 'last_ticker']:
            if key == 'messages':
                st.session_state[key] = [{
                    "role": "assistant", "type": "text",
                    "content": "안녕하세요! 🚦 **CipherX v12.0** 입니다.\n\n분석할 **티커명**을 입력하세요."
                }]
            else:
                st.session_state[key] = None
        st.rerun()


# ──────────────────────────────────────────
# 세션 관리
# ──────────────────────────────────────────
if 'messages' not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant", "type": "text",
        "content": ("안녕하세요! 🚦 **CipherX v12.0** 입니다.\n\n"
                    "분석할 **티커명**을 입력하세요. 채팅처럼 이어서 여러 종목을 검색할 수 있습니다.\n\n")
    }]
for key in ['pending_ai_ticker', 'pending_ai_prompt', 'last_ticker']:
    if key not in st.session_state:
        st.session_state[key] = None
if 'enabled_signals' not in st.session_state:
    st.session_state['enabled_signals'] = set(ALL_CHART_SIGNALS.keys())
if 'enabled_judgments' not in st.session_state:
    st.session_state['enabled_judgments'] = {'STRONG_BUY', 'BUY', 'SELL', 'STRONG_SELL'}


def _check_query_params():
    try:
        qp = st.query_params
        ticker_from_url = qp.get("ticker", None)
        if ticker_from_url and st.session_state.last_ticker != ticker_from_url.upper():
            return ticker_from_url.upper()
    except Exception:
        pass
    return None

url_ticker = _check_query_params()


# ──────────────────────────────────────────
# 챗 인터페이스
# ──────────────────────────────────────────
st.markdown("<h2 style='text-align:center;color:#fff;margin-bottom:20px'>🚦 CipherX</h2>",
            unsafe_allow_html=True)

if not st.session_state.last_ticker:
    st.markdown("<p style='text-align:center;color:#888;font-size:0.9rem;'>"
                "🔥 추천 주식 빠르게 분석해보기</p>", unsafe_allow_html=True)
    cols = st.columns(4)
    quick_tickers = ["NVDA", "TSLA", "AAPL", "QQQ"]
    for idx_q, col in enumerate(cols):
        with col:
            if st.button(f"{quick_tickers[idx_q]}", use_container_width=True):
                st.session_state['quick_ticker'] = quick_tickers[idx_q]
    st.markdown("<br>", unsafe_allow_html=True)

for i, msg in enumerate(st.session_state.messages):
    av = "✨" if msg["role"] == "assistant" else "🧑‍💻"
    with st.chat_message(msg["role"], avatar=av):
        if msg.get("type") == "analysis":
            st.markdown(msg.get("content", ""))
            render_analysis(msg)
            if msg.get("prompt"):
                with st.expander("📝 퀀트 프롬프트 원문 확인", expanded=False):
                    st.code(msg["prompt"], language="markdown")
                    st_copy_to_clipboard(msg["prompt"],
                                        before_copy_label="📋 복사",
                                        after_copy_label="✅ 복사됨!")
        elif msg.get("type") == "report":
            with st.expander(f"📊 {msg.get('ticker', '')} AI 퀀트 리포트", expanded=True):
                st.markdown(msg["content"])
            st.download_button(
                "📥 마크다운 파일 다운로드",
                key=f"dl_{i}_{msg.get('ticker', 'RPT')}",
                data=msg["content"].encode('utf-8'),
                file_name=(f"{msg.get('ticker', 'RPT').upper()}_Quant_Report_"
                           f"{datetime.now().strftime('%Y%m%d_%H%M')}.md"),
                mime="text/markdown", use_container_width=True)
        else:
            st.markdown(msg.get("content", ""))


# ──────────────────────────────────────────
# AI 실행
# ──────────────────────────────────────────
def _run_ai():
    tp = st.session_state.pending_ai_ticker
    pp = st.session_state.pending_ai_prompt
    with st.chat_message("assistant", avatar="✨"):
        pb = st.progress(0, text="퀀트 엔진 로딩 중...")
        try:
            pb.progress(10, text="Gemini 모델 초기화 중...")
            model = get_gemini_model()
            pb.progress(20, text="시장 데이터 및 시그널 취합 중...")
            collected_chunks = []

            def gemini_stream_generator():
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

            with st.expander(f"📊 {tp.upper()} AI 퀀트 리포트", expanded=True):
                st.write_stream(gemini_stream_generator())
            time.sleep(0.3)
            pb.empty()

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


# ──────────────────────────────────────────
# 티커 처리
# ──────────────────────────────────────────
def process_ticker(tv: str, refresh: bool = False):
    tv = tv.strip().upper()
    st.session_state.pending_ai_ticker = None
    st.session_state.pending_ai_prompt = None

    if not _valid_fmt(tv):
        st.toast(f"⚠️ **{tv}** — 올바른 티커 형식이 아닙니다.", icon="🚨")
        return
    if not validate_ticker(tv):
        st.toast(f"⚠️ **{tv}** — Yahoo Finance에서 데이터를 찾을 수 없습니다.", icon="🔍")
        return

    st.session_state.messages.append({"role": "user", "type": "text", "content": tv})
    st.session_state.last_ticker = tv

    try:
        st.query_params["ticker"] = tv
    except Exception:
        pass

    with st.chat_message("assistant", avatar="✨"):
        with st.status(f"🌐 {tv} 퀀트 파이프라인 가동 중...", expanded=True) as status:
            st.write("📡 YFinance 펀더멘탈 및 숏(공매도) 데이터 조회 중...")
            fundamentals = fetch_fundamentals(tv)

            st.write("📊 기술적 데이터 계산 및 시그널 엔진 검증 중...")
            st.write("🎯 8-Layer 매매 판단 엔진 가동 중...")
            st.write("⏳ 선행 지표(가속도/수렴/셋업) 계산 중...")
            fig, phist, meta = analyze(tv, chart_days, refresh)

            if fig:
                prompt = build_ai_prompt(tv, phist, fundamentals)
                status.update(label=f"✅ {tv} 퀀트 분석 완료!", state="complete", expanded=False)
            else:
                prompt = None
                status.update(label=f"⚠️ {tv} 데이터 처리 실패", state="error", expanded=False)

        if fig:
            st.session_state.messages.append({
                "role": "assistant", "type": "analysis", "ticker": tv,
                "content": f"✅ **{tv}** 분석이 완료되었습니다.",
                "fig": fig, "meta": meta, "prompt": prompt,
            })
            st.session_state.pending_ai_ticker = tv
            st.session_state.pending_ai_prompt = prompt
            st.rerun()
        else:
            err_msg = phist if phist else "데이터 부족"
            st.session_state.messages.append({
                "role": "assistant", "type": "text",
                "content": f"⚠️ **{tv}** 분석 실패: {err_msg}"
            })
            st.rerun()


# ──────────────────────────────────────────
# 실행 트리거
# ──────────────────────────────────────────
if url_ticker and 'url_loaded' not in st.session_state:
    st.session_state['url_loaded'] = True
    process_ticker(url_ticker)

if st.session_state.get('quick_ticker'):
    qt = st.session_state.pop('quick_ticker')
    process_ticker(qt)

if st.session_state.last_ticker:
    if st.session_state.pending_ai_ticker and st.session_state.pending_ai_prompt:
        if st.button(
            f"🚀 {st.session_state.pending_ai_ticker.upper()} AI 심층 퀀트 분석 시작",
            type="primary", use_container_width=True
        ):
            _run_ai()

elif st.session_state.pending_ai_ticker and st.session_state.pending_ai_prompt:
    if st.button(
        f"🚀 {st.session_state.pending_ai_ticker.upper()} AI 심층 퀀트 분석 시작",
        type="primary", use_container_width=True
    ):
        _run_ai()

if ticker_input := st.chat_input("미국 주식 티커를 입력하세요 (예: TSLA, AAPL, QQQ)"):
    process_ticker(ticker_input)