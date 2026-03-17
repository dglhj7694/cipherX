# ══════════════════════════════════════════════════════════════
#  CipherX V11.0 — Judgment-First Architecture
#  PART 1/3: 임포트 + 상수 + 지표 엔진 + 시그널 탐지 + 판단 엔진
# ══════════════════════════════════════════════════════════════

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
    page_title="CipherX V11.0",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ──────────────────────────────────────────
# 🎨 CSS
# ──────────────────────────────────────────
st.markdown("""<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
html,body,[class*="css"]{font-family:'Pretendard','Noto Sans KR',sans-serif!important}
span[class*="material-symbols"],span[class*="material-icons"],
i[class*="material-icons"],.stIcon,[data-testid="stIconMaterial"]{
    font-family:'Material Symbols Rounded','Material Icons',sans-serif!important}

/* ── 전역 배경 ── */
.stApp{background-color:#0B0E14}

/* ── 텍스트 ── */
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

/* ── 코드 블록 ── */
div[data-testid="stCodeBlock"],pre,code{background-color:#151921!important;color:#E2E8F0!important;
    border:1px solid #1E2530!important;border-radius:10px!important}
div[data-testid="stCodeBlock"] span{text-shadow:none!important}
div[data-testid="stCodeBlock"] span[style*="color: rgb(0, 0, 0)"],
div[data-testid="stCodeBlock"] span[style*="color: black"],
div[data-testid="stCodeBlock"] code>span:not([class]){color:#E2E8F0!important}

/* ── 채팅 메시지 ── */
div[data-testid="stChatMessage"]:nth-child(even){background-color:#10141C;border-radius:14px;
    padding:8px 18px;border:1px solid rgba(255,255,255,0.03)}

/* ── 컨테이너 ── */
.block-container{padding-top:1rem!important;max-width:960px}
@media(max-width:768px){
    .block-container{padding-left:.5rem!important;padding-right:.5rem!important}
    .price-big{font-size:1.6rem!important}
    div[data-testid="stPlotlyChart"]{margin-left:-10px!important;margin-right:-10px!important}
}

/* ── 버튼 ── */
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

/* ── Expander ── */
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

/* ── 헤더/사이드바 ── */
header{background-color:transparent!important}
div[data-testid="collapsedControl"]{display:flex!important;z-index:999999!important}
section[data-testid="stSidebar"]{background-color:#080A10;border-right:1px solid #151921}
section[data-testid="stSidebar"] .stMarkdown p{color:#8896A8!important}
section[data-testid="stSidebar"] [data-testid="stSidebarCollapsedControl"]{
    background:rgba(11,14,20,0.95)!important;border:1px solid #1C2233!important;border-radius:10px!important}

/* ── 시그널 카드 ── */
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

/* ── 가격 헤더 ── */
.price-header{
    background:linear-gradient(160deg,#0F1320 0%,#141926 50%,#111827 100%);
    border:1px solid #1C2233;border-radius:16px;padding:20px 24px;margin-bottom:18px;
    box-shadow:0 4px 20px rgba(0,0,0,0.3)}
.price-big{font-size:2.2rem;font-weight:800;margin:0;letter-spacing:-0.5px}
.price-change-up{color:#34D399!important}
.price-change-down{color:#F87171!important}
.price-label{color:#64748B!important;font-size:.8rem;margin:0;font-weight:500;
    text-transform:uppercase;letter-spacing:0.5px}

/* ── 미니 인디케이터 ── */
.indicator-mini{display:inline-block;padding:5px 11px;margin:3px;border-radius:8px;
    font-size:.78rem;font-weight:600;letter-spacing:0.2px;
    border:1px solid rgba(255,255,255,0.04)}
.ind-bullish{background:rgba(16,185,129,.12);color:#6EE7B7;border-color:rgba(16,185,129,.2)}
.ind-bearish{background:rgba(239,68,68,.12);color:#FCA5A5;border-color:rgba(239,68,68,.2)}
.ind-neutral{background:rgba(245,158,11,.10);color:#FCD34D;border-color:rgba(245,158,11,.15)}

/* ── 탭 ── */
div[data-testid="stTabs"] button{color:#64748B!important;font-weight:700!important;
    font-size:.9rem!important;padding:10px 16px!important;
    border-bottom:3px solid transparent!important;transition:all .2s ease}
div[data-testid="stTabs"] button:hover{color:#A5B4FC!important}
div[data-testid="stTabs"] button[aria-selected="true"]{
    color:#A5B4FC!important;border-bottom-color:#6366F1!important}

/* ── 판단 카드 (신규) ── */
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

/* ── 콤보 카드 (신규) ── */
.combo-card{border-radius:12px;padding:12px 16px;margin:6px 0;display:flex;
    align-items:center;justify-content:space-between;
    border:1px solid rgba(255,255,255,0.06);transition:transform .15s ease}
.combo-card:hover{transform:translateX(4px)}
.combo-buy{background:linear-gradient(135deg,rgba(16,185,129,.08),rgba(6,78,59,.05));
    border-left:3px solid #10B981}
.combo-sell{background:linear-gradient(135deg,rgba(239,68,68,.08),rgba(127,29,29,.05));
    border-left:3px solid #EF4444}

/* ── 레이어 바 (신규) ── */
.layer-bar-wrap{padding:4px 0}
.layer-bar-bg{background:#151921;border-radius:6px;height:10px;overflow:hidden;
    border:1px solid rgba(255,255,255,0.03)}
.layer-bar-fill{height:10px;border-radius:6px;transition:width .5s cubic-bezier(.4,0,.2,1)}
.layer-bar-fill-buy{background:linear-gradient(90deg,#059669,#34D399)}
.layer-bar-fill-sell{background:linear-gradient(90deg,#DC2626,#F87171)}

/* ── 판단 이력 행 (신규) ── */
.history-row{display:flex;align-items:center;padding:8px 14px;margin:4px 0;
    border-radius:10px;background:rgba(255,255,255,0.015);
    border:1px solid rgba(255,255,255,0.04);transition:background .15s ease}
.history-row:hover{background:rgba(255,255,255,0.03)}

/* ── 알림 바 (신규) ── */
.alert-bar{border-radius:10px;padding:10px 16px;margin:5px 0;
    border:1px solid rgba(255,255,255,0.06);backdrop-filter:blur(8px)}
.alert-bar-progress{background:#151921;border-radius:4px;height:5px;margin-top:8px;overflow:hidden}
.alert-bar-fill{height:5px;border-radius:4px;transition:width .4s ease}

/* ── 테이블 개선 ── */
table{border-collapse:collapse!important;border:none!important}
th{background:rgba(99,102,241,.08)!important;color:#C4CDD8!important;
    font-weight:700!important;border:1px solid rgba(255,255,255,0.06)!important}
td{border:1px solid rgba(255,255,255,0.04)!important;color:#94A3B8!important}
tr:hover td{background:rgba(255,255,255,0.02)!important}

/* ── 스크롤바 ── */
::-webkit-scrollbar{width:6px;height:6px}
::-webkit-scrollbar-track{background:#0B0E14}
::-webkit-scrollbar-thumb{background:#2A3040;border-radius:3px}
::-webkit-scrollbar-thumb:hover{background:#3D4A5F}
</style>""", unsafe_allow_html=True)

# ──────────────────────────────────────────
# 🔧 시그널 레지스트리
# ──────────────────────────────────────────
_B, _S = 'buy', 'sell'
def _sig(w, d, icon, label, sym, sz, clr, base, atr_m, kor, desc):
    return {'w': w, 'dir': d, 'icon': icon, 'label': label, 'sym': sym, 'sz': sz,
            'clr': clr, 'base': base, 'atr_m': atr_m, 'kor': kor, 'desc': desc}

SIGNAL_REGISTRY = {
    # MCB+ 매수 (21)
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
    # MCB+ 매도 (21)
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
    # 캔들스틱 (7)
    'Hammer':               _sig(1.5,_B,'🔨','Hammer','triangle-up',11,'#00E676','Low',-1.5,'해머','긴하단꼬리+소형실체+WT<-20'),
    'Morning_Star':         _sig(2.0,_B,'🌅','MornStar','star',13,'#00E676','Low',-2.0,'모닝스타','큰음봉→소형봉→강한양봉(3봉반전)'),
    'Doji_Bullish':         _sig(0.8,_B,'➕','Doji Bull','cross-thin',9,'#69F0AE','Low',-1.0,'강세 도지','시가≈종가+하락추세후 WT반등'),
    'Shooting_Star':        _sig(1.5,_S,'🌠','ShootStar','triangle-down',11,'#FF1744','High',1.5,'슈팅스타','긴상단꼬리+소형실체+WT>20'),
    'Evening_Star':         _sig(2.0,_S,'🌆','EveStar','star',13,'#FF1744','High',2.0,'이브닝스타','큰양봉→소형봉→강한음봉(3봉반전)'),
    'Doji_Bearish':         _sig(0.8,_S,'➖','Doji Bear','cross-thin',9,'#FF5252','High',1.0,'약세 도지','시가≈종가+상승추세후 WT하락'),
    # Inside/Outside (3)
    'Inside_Day':           _sig(0.3,_B,'📦','InsideDay','square-open',7,'#FFC107','Low',-0.3,'인사이드데이','고가<전일고&저가>전일저(돌파대기)'),
    'Outside_Bullish':      _sig(1.5,_B,'💪','OutsideBull','square',11,'#00E676','Low',-1.5,'강세 아웃사이드','전일범위포함+양봉마감+WT<30'),
    'Outside_Bearish':      _sig(1.5,_S,'🥊','OutsideBear','square',11,'#FF1744','High',1.5,'약세 아웃사이드','전일범위포함+음봉마감+WT>-30'),
    # MA 돌파/이탈 (6)
    'Cross_Above_20MA':     _sig(0.8,_B,'📈','X▲20MA','triangle-up',9,'#69F0AE','Low',-0.8,'20MA상향돌파','종가>20MA(전일≤)'),
    'Cross_Above_50MA':     _sig(1.2,_B,'📈','X▲50MA','triangle-up',10,'#00E676','Low',-1.0,'50MA상향돌파','종가>50MA(전일≤)'),
    'Cross_Above_200MA':    _sig(1.5,_B,'📈','X▲200MA','triangle-up',11,'#00BFA5','Low',-1.2,'200MA상향돌파','종가>200MA(전일≤)'),
    'Fell_Below_20MA':      _sig(0.8,_S,'📉','X▼20MA','triangle-down',9,'#FF5252','High',0.8,'20MA하향이탈','종가<20MA(전일≥)'),
    'Fell_Below_50MA':      _sig(1.2,_S,'📉','X▼50MA','triangle-down',10,'#FF1744','High',1.0,'50MA하향이탈','종가<50MA(전일≥)'),
    'Fell_Below_200MA':     _sig(1.5,_S,'📉','X▼200MA','triangle-down',11,'#D50000','High',1.2,'200MA하향이탈','종가<200MA(전일≥)'),
    # 볼린저 밴드 (4)
    'Above_Upper_BB':       _sig(1.0,_B,'🔝','BB▲Break','diamond-open',10,'#00E5FF','High',1.0,'BB상단돌파','종가>상단BB(강한모멘텀)'),
    'Below_Lower_BB':       _sig(1.0,_S,'⤵️','BB▼Break','diamond-open',10,'#FF6E40','Low',-1.0,'BB하단이탈','종가<하단BB(과매도/붕괴)'),
    'BB_Squeeze_End_Bull':  _sig(1.5,_B,'💥','SqEnd▲','star-diamond',12,'#00FFFF','Low',-1.5,'BB스퀴즈해소↑','BB확장+상승+WT↑'),
    'BB_Squeeze_End_Bear':  _sig(1.5,_S,'💥','SqEnd▼','star-diamond',12,'#FF6600','High',1.5,'BB스퀴즈해소↓','BB확장+하락+WT↓'),
    # MACD 센터라인 (2)
    'MACD_Zero_Cross_Buy':  _sig(1.2,_B,'⬆️','MACD 0▲','triangle-up',10,'#4CAF50','Low',-1.0,'MACD 0선돌파','MACD>0(전일≤0)'),
    'MACD_Zero_Cross_Sell': _sig(1.2,_S,'⬇️','MACD 0▼','triangle-down',10,'#E57373','High',1.0,'MACD 0선이탈','MACD<0(전일≥0)'),
    # 연속 (4)
    'Up_3_Days':            _sig(0.5,_B,'📗','Up3D','triangle-up',8,'#69F0AE','High',0.5,'3일연속상승','3거래일연속양봉'),
    'Up_5_Days':            _sig(0.8,_B,'📗','Up5D','triangle-up',9,'#00E676','High',0.8,'5일연속상승','5거래일연속양봉(과매수주의)'),
    'Down_3_Days':          _sig(0.5,_S,'📕','Dn3D','triangle-down',8,'#FF5252','Low',-0.5,'3일연속하락','3거래일연속음봉'),
    'Down_5_Days':          _sig(0.8,_S,'📕','Dn5D','triangle-down',9,'#FF1744','Low',-0.8,'5일연속하락','5거래일연속음봉(과매도주의)'),
    # 갭 (4)
    'Gap_Up':               _sig(1.0,_B,'⏫','GapUp','arrow-up',10,'#00E676','Low',-1.0,'갭 상승','시가>전일고가(ATR50%↑)'),
    'Gap_Down':             _sig(1.0,_S,'⏬','GapDn','arrow-down',10,'#FF1744','High',1.0,'갭 하락','시가<전일저가(ATR50%↑)'),
    'Gap_Up_Closed':        _sig(0.8,_S,'🔄','GapUp Fill','circle-open',8,'#FFA726','High',0.8,'갭업메움','상승갭메워짐(약세전환)'),
    'Gap_Down_Closed':      _sig(0.8,_B,'🔄','GapDn Fill','circle-open',8,'#4FC3F7','Low',-0.8,'갭다운메움','하락갭메워짐(강세전환)'),
    # 변동성 (4)
    'NR7':                  _sig(0.3,_B,'🔲','NR7','square-open',7,'#B0BEC5','Low',-0.3,'NR7','7일중최소범위(돌파임박)'),
    'NR7_2':                _sig(0.8,_B,'🔳','NR7-2','square-open',8,'#90A4AE','Low',-0.5,'NR7-2','2일연속NR7(강력돌파임박)'),
    'Calm_After_Storm':     _sig(1.0,_B,'🌤️','CalmStorm','diamond-open',9,'#FFC107','Low',-0.8,'폭풍뒤고요','WideRange후→NarrowRange(돌파임박)'),
    'Wide_Range_Bar':       _sig(0.5,_B,'📊','WideBar','square-open',7,'#FFAB40','Low',-0.4,'넓은범위봉','범위>ATR×2(변동성확장)'),
    # 52주 / Spinning Top (3)
    'New_52W_High':         _sig(1.5,_B,'🏔️','52W▲','star-triangle-up',12,'#FFD700','High',1.5,'52주신고가','52주최고가갱신(돌파)'),
    'New_52W_Low':          _sig(1.5,_S,'🕳️','52W▼','star-triangle-down',12,'#B71C1C','Low',-1.5,'52주신저가','52주최저가갱신(붕괴)'),
    'Spinning_Top':         _sig(0.3,_B,'🌀','SpinTop','circle-open',7,'#FFC107','Low',-0.3,'팽이형','소형실체+유사꼬리(우유부단)'),
    # Jeff Cooper (15)
    'Pullback_123_Bull':    _sig(2.0,_B,'🎯','123PB▲','triangle-up',12,'#00E676','Low',-1.8,'1,2,3풀백매수','ADX>30+DI↑+3일저점↓후 되돌림매수'),
    'Pullback_123_Bear':    _sig(2.0,_S,'🎯','123PB▼','triangle-down',12,'#FF1744','High',1.8,'1,2,3풀백매도','ADX>30+DI↓+3일고점↑후 되돌림매도'),
    'Setup_180_Bull':       _sig(2.0,_B,'🔄','180▲','star-diamond',13,'#00E676','Low',-2.0,'180매수셋업','전일하위25%→당일상위25%+MA위'),
    'Setup_180_Bear':       _sig(2.0,_S,'🔄','180▼','star-diamond',13,'#FF1744','High',2.0,'180매도셋업','전일상위25%→당일하위25%+MA아래'),
    'Boomer_Buy':           _sig(2.0,_B,'💣','Boomer▲','star',12,'#00E676','Low',-1.8,'부머매수','ADX>30+DI↑+2일인사이드→돌파매수'),
    'Boomer_Sell':          _sig(2.0,_S,'💣','Boomer▼','star',12,'#FF1744','High',1.8,'부머매도','ADX>30+DI↓+2일인사이드→하향이탈매도'),
    'Expansion_BO':         _sig(2.5,_B,'🚀','XBO','star-diamond',14,'#FFD700','Low',-2.5,'확장돌파','2개월신고가+9일최대범위→돌파매수'),
    'Expansion_BD':         _sig(2.5,_S,'💨','XBD','star-diamond',14,'#FF0000','High',2.5,'확장붕괴','2개월신저가+9일최대범위→공매도'),
    'Gilligans_Buy':        _sig(2.0,_B,'🏝️','Gilligan▲','hexagon',12,'#00BCD4','Low',-2.0,'길리건매수','갭다운2개월신저가→상위50%마감반전'),
    'Gilligans_Sell':       _sig(2.0,_S,'🏝️','Gilligan▼','hexagon',12,'#FF5722','High',2.0,'길리건매도','갭업2개월신고가→하위50%마감반전'),
    'Lizard_Bull':          _sig(1.5,_B,'🦎','Lizard▲','triangle-up',10,'#00E676','Low',-1.5,'리자드매수','시가종가상위25%+10일신저가'),
    'Lizard_Bear':          _sig(1.5,_S,'🦎','Lizard▼','triangle-down',10,'#FF1744','High',1.5,'리자드매도','시가종가하위25%+10일신고가'),
    'NonADX_123_Bull':      _sig(1.8,_B,'📐','nADX123▲','triangle-up',11,'#69F0AE','Low',-1.5,'비ADX풀백매수','주가>50MA+3일저점↓→매수'),
    'NonADX_123_Bear':      _sig(1.8,_S,'📐','nADX123▼','triangle-down',11,'#FF5252','High',1.5,'비ADX풀백매도','주가<50MA+3일고점↑→매도'),
    'Pocket_Pivot':         _sig(1.5,_B,'🧲','PocketPvt','triangle-up',11,'#7C4DFF','Low',-1.5,'포켓피봇','양봉+거래량>10일하락거래량최대+MA위'),
    # Money Flow 시그널 (6개)
    'MF_Cross_Bull':        _sig(1.5,_B,'💰','MF 0▲','triangle-up',11,'#00E676','Low',-1.2,'MF 강세전환','자금흐름 음→양 전환'),
    'MF_Cross_Bear':        _sig(1.5,_S,'💸','MF 0▼','triangle-down',11,'#FF1744','High',1.2,'MF 약세전환','자금흐름 양→음 전환'),
    'MF_Bull_Div':          _sig(1.8,_B,'💹','MF Bull Div','triangle-up',11,'#7C4DFF','Low',-1.5,'MF 상승 다이버전스','가격↓ vs MF↑'),
    'MF_Bear_Div':          _sig(1.8,_S,'💹','MF Bear Div','triangle-down',11,'#E040FB','High',1.5,'MF 하락 다이버전스','가격↑ vs MF↓'),
    'MF_Accel_Up':          _sig(1.0,_B,'📈','MF Accel▲','arrow-up',9,'#69F0AE','Low',-0.8,'MF 가속상승','5일+연속 MF 상승'),
    'MF_Accel_Dn':          _sig(1.0,_S,'📉','MF Accel▼','arrow-down',9,'#FF5252','High',0.8,'MF 가속하락','5일+연속 MF 하락'),
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
    'Above_Upper_BB':5,'Below_Lower_BB':5,
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
    'MF_Cross_Bull':10, 'MF_Cross_Bear':10,
    'MF_Bull_Div':10, 'MF_Bear_Div':10,
    'MF_Accel_Up':5, 'MF_Accel_Dn':5,
}

SIGNAL_HIERARCHY = {
    'candle_bull': ['Morning_Star','Bullish_Engulfing','Hammer','Doji_Bullish','Spinning_Top'],
    'candle_bear': ['Evening_Star','Bearish_Engulfing','Shooting_Star','Doji_Bearish','Spinning_Top'],
    'ma_cross_bull': ['Cross_Above_200MA','Cross_Above_50MA','Cross_Above_20MA'],
    'ma_cross_bear': ['Fell_Below_200MA','Fell_Below_50MA','Fell_Below_20MA'],
    'cooper_bull': ['Expansion_BO','Pullback_123_Bull','Setup_180_Bull','Boomer_Buy','Gilligans_Buy','Lizard_Bull','NonADX_123_Bull'],
    'cooper_bear': ['Expansion_BD','Pullback_123_Bear','Setup_180_Bear','Boomer_Sell','Gilligans_Sell','Lizard_Bear','NonADX_123_Bear'],
}

# ──────────────────────────────────────────
# 🆕 판단 마커 시각 설정
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

# ──────────────────────────────────────────
# 유틸리티
# ──────────────────────────────────────────
def _recent(s, lb=3): return s.astype(float).rolling(lb+1, min_periods=1).max().fillna(0).astype(bool)
def _cooldown(sig, bars=5):
    """단일 시그널 쿨다운 (Numpy 배열 최적화)"""
    v = sig.fillna(False).values
    out = np.zeros_like(v, dtype=bool)
    last = -bars - 1
    
    for i in range(len(v)):
        if v[i]:
            if (i - last) > bars:
                out[i] = True
                last = i
    return pd.Series(out, index=sig.index)

def _cooldown_directional(df, buy_sig, sell_sig, bars=5):
    """방향별 쿨다운 (Numpy 배열 최적화)"""
    bv = df.get(buy_sig, pd.Series(False, index=df.index)).fillna(False).values
    sv = df.get(sell_sig, pd.Series(False, index=df.index)).fillna(False).values
    b_out = np.zeros_like(bv, dtype=bool)
    s_out = np.zeros_like(sv, dtype=bool)
    last_b, last_s = -bars - 1, -bars - 1
    
    for i in range(len(df)):
        if bv[i] and (i - last_b) > bars:
            b_out[i] = True
            last_b = i
        if sv[i] and (i - last_s) > bars:
            s_out[i] = True
            last_s = i
            
    if buy_sig in df.columns: df[buy_sig] = pd.Series(b_out, index=df.index)
    if sell_sig in df.columns: df[sell_sig] = pd.Series(s_out, index=df.index)
def _volf(vol, ratio=0.5, period=20): return vol >= (vol.rolling(period, min_periods=5).mean() * ratio)
def _valid_fmt(t): return bool(re.match(r'^[A-Za-z]{1,5}([.\-][A-Za-z]{1,2})?$', t))
def _cls(val, lo, hi): return 'ind-bullish' if val<lo else ('ind-bearish' if val>hi else 'ind-neutral')

# ──────────────────────────────────────────
# 데이터 캐싱
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
        return "\n".join([
            f"Market Cap: {_get('marketCap','large')}",f"Shares Outstanding: {_get('sharesOutstanding','large')}",
            f"Float: {_get('floatShares','large')}",f"Short % of Float: {_get('shortPercentOfFloat','percent')}",
            f"Days to Cover: {_get('shortRatio','float')}",f"Trailing EPS: {_get('trailingEps','currency')}",
            f"P/E Ratio: {_get('trailingPE','float')}",f"P/S: {_get('priceToSalesTrailing12Months','float')}",
            f"P/B: {_get('priceToBook','float')}",f"PEG: {_get('pegRatio','float')}",
            f"52W High: {_get('fiftyTwoWeekHigh','currency')}",f"52W Low: {_get('fiftyTwoWeekLow','currency')}",
            f"Avg Vol: {_get('averageVolume','large')}"])
    except: return "펀더멘탈 데이터를 불러올 수 없습니다."

@st.cache_data(ttl=300, show_spinner=False)
def fetch_history(ticker, _ts=None): return yf.Ticker(ticker).history(period="2y")

@st.cache_data(ttl=600, show_spinner=False)
def validate_ticker(ticker):
    try:
        # 불안정한 info() 대신 최근 5일치 history 데이터 존재 여부로 확실하게 검증
        hist = yf.Ticker(ticker).history(period="5d")
        return not hist.empty
    except Exception as e:
        import logging
        logging.warning(f"Ticker validation failed for {ticker}: {e}")
        return False

@st.cache_data(ttl=300, show_spinner=False)
def compute_and_cache(ticker, _ts=None):
    df = fetch_history(ticker, _ts)
    if df.empty: return None
    return detect_all_signals(compute_indicators(df))

# ──────────────────────────────────────────
# 기술 지표 계산 엔진 (변경 없음)
# ──────────────────────────────────────────
def compute_rsi(s,p=14):
    d=s.diff();g,l=d.clip(lower=0),-d.clip(upper=0)
    return 100-(100/(1+g.ewm(alpha=1/p,min_periods=p).mean()/(l.ewm(alpha=1/p,min_periods=p).mean()+1e-10)))
def compute_mfi(h,l,c,v,p=14):
    tp=(h+l+c)/3;raw=tp*v;d=tp.diff()
    return 100-(100/(1+raw.where(d>=0,0.0).rolling(p).sum()/(raw.where(d<0,0.0).rolling(p).sum()+1e-10)))
def compute_rsi_mfi(h,l,c,v,p=60):
    rf,mf=compute_rsi(c,20),compute_mfi(h,l,c,v,20);rs,ms=compute_rsi(c,p),compute_mfi(h,l,c,v,p)
    return (((rf-50)+(mf-50))/2)*.6+(((rs-50)+(ms-50))/2)*.4
def compute_wavetrend(h,l,c,ch=9,avg=12,ma=3):
    ap=(h+l+c)/3;esa=ap.ewm(span=ch,adjust=False).mean();d=abs(ap-esa).ewm(span=ch,adjust=False).mean()
    ci=(ap-esa)/(0.015*d+1e-10);wt1=ci.ewm(span=avg,adjust=False).mean();wt2=wt1.rolling(ma).mean()
    return wt1,wt2,(wt1>wt2)&(wt1.shift(1)<=wt2.shift(1)),(wt1<wt2)&(wt1.shift(1)>=wt2.shift(1))
def compute_stoch_rsi(c,rl=14,sl=14,ks=3,ds=3):
    rsi=compute_rsi(c,rl);mn,mx=rsi.rolling(sl).min(),rsi.rolling(sl).max()
    k=(((rsi-mn)/(mx-mn+1e-10))*100).rolling(ks).mean();return k,k.rolling(ds).mean()
def compute_tr(h,l,c):
    pc=c.shift(1);return pd.concat([h-l,(h-pc).abs(),(l-pc).abs()],axis=1).max(axis=1)
def compute_adx(h,l,c,p=14):
    tr=compute_tr(h,l,c);ph,pl=h.shift(1),l.shift(1)
    pdm=pd.Series(np.where((h-ph)>(pl-l),np.maximum(h-ph,0),0),index=h.index,dtype=float)
    mdm=pd.Series(np.where((pl-l)>(h-ph),np.maximum(pl-l,0),0),index=h.index,dtype=float)
    atr=tr.ewm(alpha=1/p,min_periods=p).mean()
    pdi=100*pdm.ewm(alpha=1/p,min_periods=p).mean()/(atr+1e-10)
    mdi=100*mdm.ewm(alpha=1/p,min_periods=p).mean()/(atr+1e-10)
    dx=100*(pdi-mdi).abs()/(pdi+mdi+1e-10);return dx.ewm(alpha=1/p,min_periods=p).mean(),pdi,mdi
def compute_obv(c,v): return (v*np.sign(c.diff()).fillna(0)).cumsum()
def compute_macd(c,f=12,s=26,sig=9):
    ml=c.ewm(span=f,adjust=False).mean()-c.ewm(span=s,adjust=False).mean();sl=ml.ewm(span=sig,adjust=False).mean();return ml,sl,ml-sl
def detect_pivot_div(price,osc,lb=60,pw=5,os_lim=None,ob_lim=None):
    n=len(price);pv,ov=price.values,osc.values;half=pw;p_lo,p_hi=[],[]
    for i in range(2*half,n):
        c_=i-half;w=pv[i-2*half:i+1]
        if pv[c_]==w.min():p_lo.append((i,c_))
        if pv[c_]==w.max():p_hi.append((i,c_))
    bd=pd.Series(False,index=price.index);brd=pd.Series(False,index=price.index)
    hb=pd.Series(False,index=price.index);hbr=pd.Series(False,index=price.index)
    for idx in range(1,len(p_lo)):
        ci,pi=p_lo[idx];cj,pj=p_lo[idx-1]
        if not(pw*2<=(pi-pj)<=lb):continue
        if(os_lim is None or ov[pi]<=os_lim)and pv[pi]<pv[pj]and ov[pi]>ov[pj]:bd.iloc[ci]=True
        if pv[pi]>pv[pj]and ov[pi]<ov[pj]:hb.iloc[ci]=True
    for idx in range(1,len(p_hi)):
        ci,pi=p_hi[idx];cj,pj=p_hi[idx-1]
        if not(pw*2<=(pi-pj)<=lb):continue
        if(ob_lim is None or ov[pi]>=ob_lim)and pv[pi]>pv[pj]and ov[pi]<ov[pj]:brd.iloc[ci]=True
        if pv[pi]<pv[pj]and ov[pi]>ov[pj]:hbr.iloc[ci]=True
    return bd,brd,hb,hbr
def compute_keltner(h,l,c,el=20,al=10,m=1.5):
    mid=c.ewm(span=el,adjust=False).mean();atr=compute_tr(h,l,c).rolling(al).mean();return mid+atr*m,mid,mid-atr*m
def detect_ttm_squeeze(bbu,bbl,kcu,kcl,c,h,l,kcm):
    sq=(bbu<kcu)&(bbl>kcl);fire=(~sq)&sq.shift(1).fillna(False)
    momentum=c-((h.rolling(20).max()+l.rolling(20).min())/2+kcm)/2;mu=momentum>momentum.shift(1);md=momentum<momentum.shift(1)
    return sq,fire&(momentum>0)&mu,fire&(momentum<0)&md
def detect_volume_climax(c,o,v,wt1,atr,z_thresh=2.5):
    vm=v.rolling(20).mean();vs=v.rolling(20).std();vz=(v-vm)/(vs+1e-10);big=(c-o).abs()>atr*0.5
    ps=(vz.shift(1)>z_thresh)&big.shift(1)
    return ps&(c.shift(1)<o.shift(1))&(wt1.shift(1)<-40)&(c>o),ps&(c.shift(1)>o.shift(1))&(wt1.shift(1)>40)&(c<o)
def _detect_engulfing_pair(c, o, wt1, wt_t=20):
    """정확한 Engulfing: 당일 실체가 전일 실체를 완전히 감싸야 함"""
    body = (c - o).abs()
    body_prev = (c.shift(1) - o.shift(1)).abs()
    avg_body = body.rolling(20).mean()
    
    # 당일 실체가 평균 이상 & 전일 실체보다 커야 함
    big = (body > avg_body * 0.8) & (body > body_prev)
    
    # 전일 실체 범위
    prev_body_high = pd.concat([c.shift(1), o.shift(1)], axis=1).max(axis=1)
    prev_body_low = pd.concat([c.shift(1), o.shift(1)], axis=1).min(axis=1)
    
    # 당일 실체 범위
    curr_body_high = pd.concat([c, o], axis=1).max(axis=1)
    curr_body_low = pd.concat([c, o], axis=1).min(axis=1)
    
    prev_bearish = c.shift(1) < o.shift(1)
    prev_bullish = c.shift(1) > o.shift(1)
    
    # Bullish: 전일 음봉 + 당일 양봉 + 당일 실체가 전일 실체를 감쌈
    bull = (prev_bearish & (c > o) & 
            (curr_body_low <= prev_body_low) & 
            (curr_body_high >= prev_body_high) & 
            big & (wt1 < -wt_t))
    
    # Bearish: 전일 양봉 + 당일 음봉 + 당일 실체가 전일 실체를 감쌈
    bear = (prev_bullish & (c < o) & 
            (curr_body_low <= prev_body_low) & 
            (curr_body_high >= prev_body_high) & 
            big & (wt1 > wt_t))
    
    return bull, bear
def compute_supertrend(h,l,c,period=10,mult=3.0):
    atr=compute_tr(h,l,c).rolling(period).mean();hl2=(h+l)/2
    up=(hl2+mult*atr).values.copy();dn=(hl2-mult*atr).values.copy();cl=c.values;n=len(c)
    sv=np.full(n,np.nan);dv=np.zeros(n,dtype=int);fv=period
    if fv>=n:return pd.Series(np.nan,index=c.index),pd.Series(0,index=c.index,dtype=int)
    dv[fv]=1;sv[fv]=dn[fv]
    for i in range(fv+1,n):
        if dv[i-1]==1:dn[i]=max(dn[i],dn[i-1])if not np.isnan(dn[i-1])else dn[i]
        else:up[i]=min(up[i],up[i-1])if not np.isnan(up[i-1])else up[i]
        if dv[i-1]==1:dv[i],sv[i]=(-1,up[i])if cl[i]<dn[i]else(1,dn[i])
        else:dv[i],sv[i]=(1,dn[i])if cl[i]>up[i]else(-1,up[i])
    return pd.Series(sv,index=c.index),pd.Series(dv,index=c.index)
def _detect_ema_pullback_pair(c,h,l,v,e8,e21,atr,wt1,wt2):
    vok=_volf(v,0.5);ar=atr/c;results={}
    for d in['buy','sell']:
        slope=e21>e21.shift(5)if d=='buy'else e21<e21.shift(5);trend=((e8>e21)if d=='buy'else(e8<e21))&slope
        side=(c>e8)if d=='buy'else(c<e8)
        if d=='buy':t=(l<=e8*(1+ar*0.15))&(l>=e21*(1-ar*0.25));tr=_recent(t,2);b=(c>=e8)&(c>h.shift(1));wok=(wt1>wt1.shift(1))&(wt1>wt2)&(wt1<60)
        else:t=(h>=e8*(1-ar*0.15))&(h<=e21*(1+ar*0.25));tr=_recent(t,2);b=(c<=e8)&(c<l.shift(1));wok=(wt1<wt1.shift(1))&(wt1<wt2)&(wt1>-60)
        results[d]=trend&side&tr&b&wok&vok
    return results['buy'],results['sell']
def _detect_mom_ignition_pair(c,o,v,bbu,bbl,atr,e8,e21,wt1,bb_w):
    body=(c-o).abs();bb=body>atr*1.5;hv=v>v.rolling(20).mean()*2.0;compressed=bb_w.shift(1)<bb_w.rolling(20).mean().shift(1)
    return(c>o)&bb&hv&(c>bbu)&(e8>e21)&(wt1<50)&compressed,(c<o)&bb&hv&(c<bbl)&(e8<e21)&(wt1>-50)&compressed
def _detect_vwap_pair(c,vosc,wt1,wt2,v,atr):
    vok=_volf(v,0.7);ap=(atr/c*100).clip(0.3,3.0);dt=(ap*0.3).clip(0.3,1.5)
    return(vosc>0)&(vosc.shift(1)<-dt)&(wt1>wt2)&(wt1<30)&vok,(vosc<0)&(vosc.shift(1)>dt)&(wt1<wt2)&(wt1>-30)&vok
def _detect_parabolic_pair(c,o,wt1,bbu,bbl,atr):
    return((wt1<-85)&(wt1>wt1.shift(1))&(c>o)&(c>c.shift(1)))|((c<bbl-atr*1.5)&(c>o)),((wt1>85)&(wt1<wt1.shift(1))&(c<o)&(c<c.shift(1)))|((c>bbu+atr*1.5)&(c<o))

# ── 신규 시그널 탐지 ──
def detect_candlestick_patterns(c, o, h, l, wt1, atr):
    body = (c - o).abs()
    upper_shadow = h - pd.concat([c, o], axis=1).max(axis=1)
    lower_shadow = pd.concat([c, o], axis=1).min(axis=1) - l
    full_range = h - l + 1e-10
    avg_body = body.rolling(20).mean()
    is_small = body < avg_body * 0.6  # 🔧 0.8→0.6 (더 엄격)

    # Hammer: 하단꼬리 ≥ 실체×2 + 상단꼬리 짧음 + 범위가 ATR의 50% 이상 (너무 작은 봉 제외)
    min_range = atr * 0.5
    hammer = ((lower_shadow >= body * 2) & (upper_shadow <= body * 0.3) &  # 🔧 0.5→0.3
              is_small & (wt1 < -20) & (c >= o) & (full_range > min_range))
    
    # Shooting Star: 상단꼬리 ≥ 실체×2 + 하단꼬리 짧음
    shooting = ((upper_shadow >= body * 2) & (lower_shadow <= body * 0.3) &  # 🔧
                is_small & (wt1 > 20) & (c <= o) & (full_range > min_range))
    
    # Doji: 실체 ≤ 범위의 5% + 범위가 ATR 30% 이상 (작은 범위 도지 제외)
    doji = (body <= full_range * 0.05) & (full_range > atr * 0.3)
    # 🔧 방향 판단 강화: 3일→5일 추세 확인
    doji_bull = doji & (wt1 < -30) & (wt1 > wt1.shift(1)) & (c.shift(1) < c.shift(3))
    doji_bear = doji & (wt1 > 30) & (wt1 < wt1.shift(1)) & (c.shift(1) > c.shift(3))
    
    # Morning Star: Day1 큰 음봉 + Day2 소형봉(갭다운) + Day3 큰 양봉
    d1_bearish = (c.shift(2) < o.shift(2)) & (body.shift(2) > avg_body.shift(2))
    d2_small = body.shift(1) < avg_body.shift(1) * 0.5
    d2_gap = pd.concat([c.shift(1), o.shift(1)], axis=1).max(axis=1) < o.shift(2)  # 🆕 갭 확인
    d3_bullish = (c > o) & (c > (o.shift(2) + c.shift(2)) / 2) & (body > avg_body * 0.8)  # 🔧 Day3도 큰 봉
    morning = d1_bearish & d2_small & d3_bullish & (wt1 < -15)
    
    # Evening Star
    d1_bullish = (c.shift(2) > o.shift(2)) & (body.shift(2) > avg_body.shift(2))
    d3_bearish = (c < o) & (c < (o.shift(2) + c.shift(2)) / 2) & (body > avg_body * 0.8)  # 🔧
    evening = d1_bullish & d2_small & d3_bearish & (wt1 > 15)
    
    # Spinning Top: 소형 실체 + 양쪽 꼬리 비슷한 길이
    spin_ratio = (upper_shadow / (lower_shadow + 1e-10))
    spin = (is_small & 
            (upper_shadow > body * 0.5) & (lower_shadow > body * 0.5) &
            (spin_ratio > 0.5) & (spin_ratio < 2.0) &  # 🆕 꼬리 균형
            ~doji)
    
    return hammer, shooting, doji_bull, doji_bear, morning, evening, spin
def detect_inside_outside_day(h,l,c,o,wt1):
    inside=(h<h.shift(1))&(l>l.shift(1));outside=(h>h.shift(1))&(l<l.shift(1))
    return inside,outside&(c>o)&(c>h.shift(1))&(wt1<30),outside&(c<o)&(c<l.shift(1))&(wt1>-30)
def detect_ma_crossovers(c,ma20,ma50,ma200):
    sigs={}
    for tag,ma in[('20MA',ma20),('50MA',ma50),('200MA',ma200)]:
        sigs[f'Cross_Above_{tag}']=(c>ma)&(c.shift(1)<=ma.shift(1));sigs[f'Fell_Below_{tag}']=(c<ma)&(c.shift(1)>=ma.shift(1))
    return sigs
def detect_bb_extra(c,bb_up,bb_low,bb_w,wt1):
    bwm=bb_w.rolling(20).mean();widening=(bb_w>bb_w.shift(1))&(bb_w.shift(1)<bwm.shift(1))
    return c>bb_up,c<bb_low,widening&(c>c.shift(1))&(wt1>wt1.shift(1)),widening&(c<c.shift(1))&(wt1<wt1.shift(1))
def detect_macd_centerline(ml): return(ml>0)&(ml.shift(1)<=0),(ml<0)&(ml.shift(1)>=0)
def detect_consecutive_days(c):
    """연속 상승/하락일 계산 (완전 벡터화)"""
    up = (c > c.shift(1)).astype(int)
    dn = (c < c.shift(1)).astype(int)
    
    # up/dn이 0인 지점을 기준으로 그룹화하여 누적합 계산 (연속 발생 횟수 측정)
    us = up.groupby((up == 0).cumsum()).cumsum()
    ds = dn.groupby((dn == 0).cumsum()).cumsum()
    
    return {
        'Up_3_Days': us >= 3, 
        'Up_5_Days': us >= 5, 
        'Down_3_Days': ds >= 3, 
        'Down_5_Days': ds >= 5
    }
def detect_gaps(c,o,h,l,atr):
    thr=atr*0.5;gu=(o>h.shift(1))&((o-h.shift(1))>thr);gd=(o<l.shift(1))&((l.shift(1)-o)>thr)
    return gu,gd,gu.shift(1).fillna(False)&(l<=h.shift(2)),gd.shift(1).fillna(False)&(h>=l.shift(2))
def detect_nr7(h,l):
    dr=h-l;mn7=dr.rolling(7).min();nr=dr<=mn7;return nr,nr&nr.shift(1).fillna(False)
def detect_range_bars(h, l, atr):
    """Wide Range Bar + Calm After Storm (최근 5일 내 wide 존재 + 오늘 narrow)"""
    dr = h - l
    wide = dr > atr * 2.0
    narrow = dr < atr * 0.5
    # 최근 5일 내 wide가 1개 이상 있었고, 오늘 narrow
    recent_wide = wide.rolling(5, min_periods=1).max().shift(1).fillna(False).astype(bool)
    calm = recent_wide & narrow
    return wide, calm
def detect_52w(c, h, l):
    """52주 신고가/신저가 — 전일까지의 범위와 비교해야 정확"""
    h252_prev = h.rolling(252, min_periods=200).max().shift(1)  # 어제까지의 52주 고가
    l252_prev = l.rolling(252, min_periods=200).min().shift(1)  # 어제까지의 52주 저가
    return h > h252_prev, l < l252_prev
def detect_123_pullback(h,l,c,adx,pdi,mdi):
    sb=(adx>30)&(pdi>mdi);ss=(adx>30)&(mdi>pdi);inside=(h<h.shift(1))&(l>l.shift(1))
    ll1=l<l.shift(1);ll2=l.shift(1)<l.shift(2);ll3=l.shift(2)<l.shift(3);tll=ll1&ll2&ll3
    tli=(ll1&ll2&inside.shift(2))|(ll1&inside.shift(1)&ll2.shift(1))|(inside&ll1&ll2)
    hh1=h>h.shift(1);hh2=h.shift(1)>h.shift(2);hh3=h.shift(2)>h.shift(3);thh=hh1&hh2&hh3
    thi=(hh1&hh2&inside.shift(2))|(hh1&inside.shift(1)&hh2.shift(1))|(inside&hh1&hh2)
    return sb&(tll|tli),ss&(thh|thi)
def detect_180_setup(c,o,h,l,ma10,ma50):
    dr=h-l+1e-10;cp=(c-l)/dr;pp=(c.shift(1)-l.shift(1))/(h.shift(1)-l.shift(1)+1e-10)
    return(pp<=0.25)&(cp>=0.75)&(c>ma10)&(c>ma50),(pp>=0.75)&(cp<=0.25)&(c<ma10)&(c<ma50)
def detect_boomer(h,l,adx,pdi,mdi):
    inside=(h<h.shift(1))&(l>l.shift(1));in2=inside&inside.shift(1)
    return in2.shift(1).fillna(False)&(adx>30)&(pdi>mdi),in2.shift(1).fillna(False)&(adx>30)&(mdi>pdi)
def detect_expansion(h,l,c):
    dr=h-l;mr9=dr.rolling(9).max();h60=h.rolling(60,min_periods=40).max();l60=l.rolling(60,min_periods=40).min()
    return(h>=h60)&(dr>=mr9),(l<=l60)&(dr>=mr9)
def detect_gilligans(o,c,h,l):
    dr=h-l+1e-10;cp=(c-l)/dr;l60=l.rolling(60,min_periods=40).min();h60=h.rolling(60,min_periods=40).max()
    return(o<=l60)&(o<l.shift(1))&(cp>=0.5)&(c>=o),(o>=h60)&(o>h.shift(1))&(cp<=0.5)&(c<=o)
def detect_lizard(o,c,h,l):
    dr=h-l+1e-10;cp=(c-l)/dr;op=(o-l)/dr
    return(cp>=0.75)&(op>=0.75)&(l<=l.rolling(10).min()),(cp<=0.25)&(op<=0.25)&(h>=h.rolling(10).max())
def detect_non_adx_123(h,l,c,ma50):
    inside=(h<h.shift(1))&(l>l.shift(1))
    ll1=l<l.shift(1);ll2=l.shift(1)<l.shift(2);tll=ll1&ll2&(l.shift(2)<l.shift(3))
    tli=(ll1&ll2&inside.shift(2))|(ll1&inside.shift(1)&ll2.shift(1))|(inside&ll1&ll2)
    hh1=h>h.shift(1);hh2=h.shift(1)>h.shift(2);thh=hh1&hh2&(h.shift(2)>h.shift(3))
    thi=(hh1&hh2&inside.shift(2))|(hh1&inside.shift(1)&hh2.shift(1))|(inside&hh1&hh2)
    return(c>ma50)&(tll|tli),(c<ma50)&(thh|thi)
def detect_pocket_pivot(c,o,v,ma50,ma200):
    dv=v.where(c<c.shift(1),0);return(c>o)&(v>dv.rolling(10).max())&(c>ma50)&(c>c.shift(1))

# ──────────────────────────────────────────
# 지표 통합 계산
# ──────────────────────────────────────────
def compute_indicators(df):
    c,h,l,v=df['Close'],df['High'],df['Low'],df['Volume']
    for ma in[5,10,20,50,100,125,200]:df[f'MA{ma}']=c.rolling(ma).mean()
    df['EMA8']=c.ewm(span=8,adjust=False).mean();df['EMA21']=c.ewm(span=21,adjust=False).mean()
    df['BB_Mid']=df['MA20'];s20=c.rolling(20).std()
    df['BB_Up'],df['BB_Low']=df['BB_Mid']+s20*2,df['BB_Mid']-s20*2
    df['BB_Width']=(df['BB_Up']-df['BB_Low'])/df['BB_Mid'];df['Percent_B']=(c-df['BB_Low'])/(df['BB_Up']-df['BB_Low']+1e-10)
    df['ATR']=compute_tr(h,l,c).rolling(14).mean()
    atr22=compute_tr(h,l,c).rolling(22).mean()
    df['Chandelier_Long']=h.rolling(22).max()-atr22*3.0;df['Chandelier_Short']=l.rolling(22).min()+atr22*3.0
    df['SuperTrend'],df['ST_Direction']=compute_supertrend(h,l,c)
    wt1,wt2,wu,wd=compute_wavetrend(h,l,c);df['WT1'],df['WT2'],df['WT_Up'],df['WT_Down']=wt1,wt2,wu,wd
    df['RSI']=compute_rsi(c,14);df['StochK'],df['StochD']=compute_stoch_rsi(c)
    df['MFI']=compute_mfi(h,l,c,v,14);df['RSI_MFI']=compute_rsi_mfi(h,l,c,v,60)
    vwap=(c*v).rolling(20).sum()/(v.rolling(20).sum()+1e-10);df['VWAP_Osc']=((c-vwap)/(vwap+1e-10))*100
    df['ADX'],df['Plus_DI'],df['Minus_DI']=compute_adx(h,l,c);df['OBV']=compute_obv(c,v)
    df['KC_Upper'],df['KC_Mid'],df['KC_Lower']=compute_keltner(h,l,c)
    df['MACD_Line'],df['MACD_Signal'],df['MACD_Hist']=compute_macd(c)
    return df

def _deduplicate(df):
    for _cat,sigs in SIGNAL_HIERARCHY.items():
        for i,s in enumerate(sigs):
            if s not in df.columns:continue
            for higher in sigs[:i]:
                if higher in df.columns:df[s]=df[s]&~df[higher]
    return df

# ──────────────────────────────────────────
# 🆕 7-Layer 판단 엔진
# ──────────────────────────────────────────
def _sig_pts(df, sig_name, points):
    if sig_name in df.columns: return np.where(df[sig_name].fillna(False), points, 0.0)
    return 0.0

def compute_trade_judgment(df):
    """
    7-Layer 스코어링 → 최종 BUY/SELL 판단
    v3: Momentum/Candle/BB/Volume/Pattern 전면 개선
    """
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

    # MACD 히스토그램 방향
    macd_h = df['MACD_Hist']
    macd_h_rising = macd_h > macd_h.shift(1)     # 히스토그램 증가
    macd_h_falling = macd_h < macd_h.shift(1)    # 히스토그램 감소

    # MACD 갭(Line - Signal) 변화 = 모멘텀 가속/감속
    macd_gap = df['MACD_Line'] - df['MACD_Signal']
    macd_accel = macd_gap > macd_gap.shift(1)    # 갭 벌어짐 = 가속
    macd_decel = macd_gap < macd_gap.shift(1)    # 갭 좁아짐 = 감속

    # RSI/StochK/WT 방향
    rsi_rising = df['RSI'] > df['RSI'].shift(1)
    rsi_falling = df['RSI'] < df['RSI'].shift(1)
    stk_rising = df['StochK'] > df['StochK'].shift(1)
    wt_rising = df['WT1'] > df['WT1'].shift(1)
    wt_falling = df['WT1'] < df['WT1'].shift(1)

    # OBV 추세
    obv = df['OBV']
    obv_ma20 = obv.rolling(20, min_periods=10).mean()
    obv_above = obv > obv_ma20    # 축적
    obv_below = obv < obv_ma20    # 분배

    # 양봉/음봉 거래량 비율
    bull_vol = df['Volume'].where(C > O, 0)
    bear_vol = df['Volume'].where(C < O, 0)
    avg_bull_vol = bull_vol.rolling(10, min_periods=5).mean()
    avg_bear_vol = bear_vol.rolling(10, min_periods=5).mean()
    vol_bull_ratio = avg_bull_vol / (avg_bear_vol + 1e-10)   # > 1 = 매수 우세

    # ══════════════ BUY ══════════════

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
    # 🆕 MA 돌파 보너스 (Pattern에서 이동)
    bt += _sig_pts(df, 'Cross_Above_50MA', 1.0)
    bt += _sig_pts(df, 'Cross_Above_200MA', 1.5)
    bt += _sig_pts(df, 'Golden_Cross', 1.5)
    df['BJ_Trend'] = bt

    # ── Layer 2: 모멘텀 (대폭 개선) ──
    bm = pd.Series(0.0, index=idx)

    # 시그널
    for s, p in [('MACD_Cross_Buy',2.5), ('MACD_Zero_Cross_Buy',2.0),
                  ('StochRSI_Cross_Buy',2.0), ('ADX_Momentum_Buy',2.0),
                  ('VWAP_Bounce_Buy',1.5)]:
        bm += _sig_pts(df, s, p)

    # 🔧 MACD 히스토그램: 레벨 + 방향 결합
    bm += np.where((macd_h > 0) & macd_h_rising, 2.0,        # 양수 + 증가 = 강세 가속
          np.where((macd_h > 0) & macd_h_falling, 0.5,        # 양수 + 감소 = 약화 중
          np.where((macd_h < 0) & macd_h_rising, 1.5, 0)))    # 음수 + 증가 = 반등 시작

    # 🔧 MACD 가속/감속
    bm += np.where((macd_h > 0) & macd_accel, 0.5, 0)

    # 🆕 VWAP: 크기 반영
    vwap_osc = df['VWAP_Osc']
    bm += np.where(vwap_osc > 3.0, 1.5,
          np.where(vwap_osc > 1.0, 1.0,
          np.where(vwap_osc > 0, 0.5, 0)))

    # 🔧 RSI: 레벨 + 방향 결합
    bm += np.where((df['RSI'] < 30) & rsi_rising, 3.0,        # 과매도 + 반등 시작 = 최강
          np.where(df['RSI'] < 30, 1.5,                         # 과매도 (아직 반등 없음)
          np.where((df['RSI'] < 45) & rsi_rising, 1.0,          # 약세 + 회복 중
          np.where((df['RSI'] > 70) & rsi_falling, -1.5,        # 🆕 과매수 + 하락 시작 = 감점
          np.where((df['RSI'] > 70) & rsi_rising, -0.5, 0)))))  # 과매수 + 아직 상승 = 약한 감점

    # 🔧 StochK: 레벨 + 방향
    bm += np.where((df['StochK'] < 20) & stk_rising, 2.5,
          np.where(df['StochK'] < 20, 1.0,
          np.where((df['StochK'] > 80) & ~stk_rising, -1.0, 0)))

    # 🔧 WT: 레벨 + 교차 결합
    wt_cross_up = df.get('WT_Up', pd.Series(False, index=idx))
    bm += np.where((df['WT1'] < -53) & (wt_cross_up | wt_rising), 3.0,    # 과매도 + 교차/반등
          np.where(df['WT1'] < -53, 1.0,                                     # 과매도 (교차 없음)
          np.where((df['WT1'] < -20) & wt_rising, 1.0,                       # 약세 + 상승 중
          np.where((df['WT1'] > 53) & wt_falling, -1.5, 0))))               # 과매수 + 하락

# ── Layer 2: 모멘텀 (BUY) 리팩토링 ──
    bm = pd.Series(0.0, index=idx)

    for s, p in [('MACD_Cross_Buy',2.5), ('MACD_Zero_Cross_Buy',2.0),
                 ('StochRSI_Cross_Buy',2.0), ('ADX_Momentum_Buy',2.0),
                 ('VWAP_Bounce_Buy',1.5)]:
        bm += _sig_pts(df, s, p)

    # MACD 히스토그램: np.select 적용
    macd_cond = [
        (macd_h > 0) & macd_h_rising,
        (macd_h > 0) & macd_h_falling,
        (macd_h < 0) & macd_h_rising
    ]
    macd_choice = [2.0, 0.5, 1.5]
    bm += np.select(macd_cond, macd_choice, default=0.0)
    bm += np.where((macd_h > 0) & macd_accel, 0.5, 0)
    
    # VWAP 크기 반영
    vwap_cond = [vwap_osc > 3.0, vwap_osc > 1.0, vwap_osc > 0]
    vwap_choice = [1.5, 1.0, 0.5]
    bm += np.select(vwap_cond, vwap_choice, default=0.0)

    # 추격매수 방지 및 상승 모멘텀: np.select 적용
    rsi_cond = [df['RSI'] > 80, df['RSI'] >= 60, df['RSI'] >= 50]
    rsi_choice = [-1.0, 2.0, 1.0]
    bm += np.select(rsi_cond, rsi_choice, default=0.0)

    stoch_cond = [df['StochK'] > 85, df['StochK'] >= 60, df['StochK'] >= 50]
    stoch_choice = [-1.0, 2.0, 1.0]
    bm += np.select(stoch_cond, stoch_choice, default=0.0)

    wt1_cond = [df['WT1'] > 60, df['WT1'] >= 20, df['WT1'] >= 0]
    wt1_choice = [-1.0, 2.0, 1.0]
    bm += np.select(wt1_cond, wt1_choice, default=0.0)

    df['BJ_Momentum'] = bm.clip(lower=0)

    # ── Layer 3: 캔들 (대폭 개선) ──
    bc = pd.Series(0.0, index=idx)

    # 🔧 추세 맥락 가중: 하락 추세에서 강세 캔들 = 높은 점수
    in_downtrend = below_50 | (df['WT1'] < -20) | (df['RSI'] < 45)
    in_uptrend = above_50 | (df['WT1'] > 20) | (df['RSI'] > 55)

    # 🔧 실체 크기 대비 가중
    body = (C - O).abs()
    body_atr_ratio = body / (atr + 1e-10)

    # Morning Star (3봉 패턴 = 가장 신뢰)
    ms_pts = np.where(df.get('Morning_Star', pd.Series(False, index=idx)).fillna(False) & in_downtrend, 3.5,
             np.where(df.get('Morning_Star', pd.Series(False, index=idx)).fillna(False), 2.5, 0))

    # Bullish Engulfing (크기 가중)
    be_raw = df.get('Bullish_Engulfing', pd.Series(False, index=idx)).fillna(False)
    be_pts = np.where(be_raw & in_downtrend & (body_atr_ratio > 1.0), 3.5,    # 큰 Engulfing + 하락추세
             np.where(be_raw & in_downtrend, 3.0,                                # 보통 Engulfing + 하락추세
             np.where(be_raw & (body_atr_ratio > 1.0), 2.5,                      # 큰 Engulfing
             np.where(be_raw, 2.0, 0))))

    # Hammer
    hm_raw = df.get('Hammer', pd.Series(False, index=idx)).fillna(False)
    hm_pts = np.where(hm_raw & in_downtrend, 2.5,
             np.where(hm_raw, 1.5, 0))

    # Outside Bullish
    ob_raw = df.get('Outside_Bullish', pd.Series(False, index=idx)).fillna(False)
    ob_pts = np.where(ob_raw & in_downtrend, 2.5,
             np.where(ob_raw, 1.5, 0))

    # Doji — 확인 캔들 필요하므로 낮은 점수
    dj_pts = np.where(df.get('Doji_Bullish', pd.Series(False, index=idx)).fillna(False) & in_downtrend, 1.0,
             np.where(df.get('Doji_Bullish', pd.Series(False, index=idx)).fillna(False), 0.5, 0))

    # 🔧 당일 최고 1개 캔들만 (중복 방지)
    all_candle_pts = np.stack([ms_pts, be_pts, hm_pts, ob_pts, dj_pts])
    bc = pd.Series(all_candle_pts.max(axis=0), index=idx)

    df['BJ_Candle'] = bc.clip(upper=5.0)

    # ── Layer 4: BB (개선) ──
    bb = pd.Series(0.0, index=idx)

    # 🔧 Squeeze End: 실제 상방 돌파 시에만 높은 점수
    bb += _sig_pts(df, 'BB_Squeeze_End_Bull', 3.0)

    # NR7/Calm: 아직 돌파 전이면 "예비" 점수만
    squeeze_on = df.get('Squeeze_On', pd.Series(False, index=idx))
    nr7_val = _sig_pts(df, 'NR7', 1.0)
    nr72_val = _sig_pts(df, 'NR7_2', 1.5)
    calm_val = _sig_pts(df, 'Calm_After_Storm', 1.0)

    # 🔧 스퀴즈 상태 + 상방 필터 = 가점 / 스퀴즈 없으면 낮은 점수
    squeeze_bonus = np.where(squeeze_on & above_50, 1.0, 0)
    bb += nr7_val + nr72_val + calm_val + squeeze_bonus

    # 🔧 %B 구간 세분화
    pct_b = df['Percent_B']
    bb += np.where(pct_b < 0.05, 2.5,                          # 극단 과매도
          np.where(pct_b < 0.2, 1.5,                             # 과매도
          np.where((pct_b >= 0.4) & (pct_b <= 0.6) & above_50, 0.5,  # 🆕 건강한 중간대
          np.where(pct_b > 0.95, -1.5, 0))))                     # 과매수 감점

    # 🔧 Below_Lower_BB: 추세 맥락 반영
    blb = df.get('Below_Lower_BB', pd.Series(False, index=idx)).fillna(False)
    bb += np.where(blb & above_200, 2.0,     # 장기 상승 + BB 하단 = 매수 기회
          np.where(blb & below_200, -0.5,     # 장기 하락 + BB 하단 = 추가 하락 위험
          np.where(blb, 1.0, 0)))             # 중립

    df['BJ_BB'] = bb.clip(lower=0, upper=7.0)

    # ── Layer 5: Volume (대폭 개선) ──
    bv = pd.Series(0.0, index=idx)

    # 기존 시그널
    bv += _sig_pts(df, 'Volume_Climax_Buy', 3.0)
    bv += _sig_pts(df, 'Pocket_Pivot', 2.0)
    bv += _sig_pts(df, 'OBV_Div_Buy', 1.5)

    # 거래량 급증 + 양봉
    bv += np.where((vol_ratio >= 3.0) & (C > O), 2.5,
          np.where((vol_ratio >= 1.5) & (C > O), 1.0, 0))

    # 🆕 OBV 추세: 축적 중이면 가점
    bv += np.where(obv_above & (obv > obv.shift(5)), 1.5,   # OBV 상승 추세
          np.where(obv_above, 0.5, 0))
    bv += np.where(obv_below & (obv < obv.shift(5)), -1.0, 0)  # OBV 하락 = 감점

    # 🆕 양봉/음봉 거래량 비율
    bv += np.where(vol_bull_ratio > 2.0, 1.5,    # 양봉 거래량 2배 이상
          np.where(vol_bull_ratio > 1.3, 0.5,
          np.where(vol_bull_ratio < 0.5, -1.0, 0)))  # 음봉 거래량이 압도

    # 🆕 거래량 건조 (돌파 전 축적 신호)
    vol_dry = vol_ratio < 0.5
    vol_dry_streak = vol_dry.astype(int)
    for i in range(1, len(vol_dry_streak)):
        if vol_dry.iloc[i]:
            vol_dry_streak.iloc[i] = vol_dry_streak.iloc[i-1] + 1
    bv += np.where((vol_dry_streak >= 3) & above_50 & squeeze_on, 1.0, 0)

    df['BJ_Volume'] = bv.clip(lower=0, upper=7.0)

    # ── Layer 6: 자금흐름 (이전 수정 유지) ──
    bmf = pd.Series(0.0, index=idx)
    bmf += np.where(rmfi < -10, 2.0,
           np.where(rmfi < -5, 1.0,
           np.where(rmfi > 10, -0.5, 0)))
    if 'MF_Slope_5' in df.columns:
        mf_slope = df['MF_Slope_5']
        bmf += np.where(mf_slope > 5, 2.0,
               np.where(mf_slope > 2, 1.5,
               np.where(mf_slope > 0, 0.5,
               np.where(mf_slope < -5, -1.0, 0))))
    if 'MF_Up_Streak' in df.columns:
        bmf += np.where(df['MF_Up_Streak'] >= 5, 2.0,
               np.where(df['MF_Up_Streak'] >= 3, 1.0, 0))
    bmf += _sig_pts(df, 'MF_Cross_Bull', 2.0)
    bmf += _sig_pts(df, 'MF_Bull_Div', 2.0)
    bmf += _sig_pts(df, 'MF_Accel_Up', 1.0)
    df['BJ_MF'] = bmf.clip(lower=0, upper=8.0)

    # ── Layer 7: Pattern (개선) ──
    bp = pd.Series(0.0, index=idx)

    # 🔧 이중 카운팅 방지: Gold_Dot는 Green_Dot + Div를 포함하므로 단독 계산
    gold = _sig_pts(df, 'Gold_Dot', 4.0)
    gdt1 = np.where(gold == 0, _sig_pts(df, 'Green_Dot_T1', 2.5), 0)
    gdt2 = np.where((gold == 0) & (gdt1 == 0), _sig_pts(df, 'Green_Dot_T2', 2.0), 0)
    bp += gold + gdt1 + gdt2

    blood = _sig_pts(df, 'Blood_Diamond', 0)  # SELL 전용, BUY에서 제외
    # Bull_Divergence: Gold_Dot과 중복 방지
    bd_pts = np.where(gold == 0, _sig_pts(df, 'Bull_Divergence', 2.0), 0)
    bp += bd_pts

    # 나머지 패턴 (MA 교차는 Trend로 이동했으므로 제외)
    for s, p in [('Pullback_123_Bull',2.5), ('Setup_180_Bull',2.0), ('Boomer_Buy',2.0),
                  ('Expansion_BO',3.0), ('Gilligans_Buy',2.5), ('Lizard_Bull',2.0),
                  ('NonADX_123_Bull',1.5), ('EMA_Pullback_Buy',2.0),
                  ('Momentum_Ignition_Buy',3.0), ('SuperTrend_Buy',2.0),
                  ('Gap_Up',1.0), ('Gap_Down_Closed',1.0),
                  ('New_52W_High',2.0), ('Blue_Diamond',2.0),
                  ('Hidden_Bull_Div',1.5), ('Squeeze_Fire_Buy',2.0),
                  ('Parabolic_Bottom_Buy',3.0), ('Pocket_Pivot',2.0)]:
        bp += _sig_pts(df, s, p)

    # 🆕 패턴 신선도: 어제 발생한 강한 패턴도 감쇠 반영
    for s, decay_pts in [('Gold_Dot',2.0), ('Green_Dot_T1',1.0), ('Expansion_BO',1.5),
                          ('Momentum_Ignition_Buy',1.5), ('Parabolic_Bottom_Buy',1.5)]:
        if s in df.columns:
            yesterday = df[s].shift(1).fillna(False)
            bp += np.where(yesterday & ~df[s], decay_pts * 0.5, 0)  # 어제 발생, 오늘 아님 = 절반 점수

    df['BJ_Pattern'] = bp.clip(upper=10.0)  # 🔧 8→10 (차별화 확대)

    df['Buy_Total'] = (df['BJ_Trend'] + df['BJ_Momentum'] + df['BJ_Candle'] +
                       df['BJ_BB'] + df['BJ_Volume'] + df['BJ_MF'] + df['BJ_Pattern'])

    # ══════════════ SELL ══════════════

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
    df['SJ_Trend'] = st_

    # ── Layer 2: 모멘텀 ──
# ── Layer 2: 모멘텀 (SELL) 리팩토링 ──
    sm = pd.Series(0.0, index=idx)
    
    for s, p in [('MACD_Cross_Sell',2.5), ('MACD_Zero_Cross_Sell',2.0),
                 ('StochRSI_Cross_Sell',2.0), ('ADX_Momentum_Sell',2.0),
                 ('VWAP_Reject_Sell',1.5)]:
        sm += _sig_pts(df, s, p)

    # SELL MACD
    macd_s_cond = [
        (macd_h < 0) & macd_h_falling,
        (macd_h < 0) & macd_h_rising,
        (macd_h > 0) & macd_h_falling
    ]
    macd_s_choice = [2.0, 0.5, 1.5]
    sm += np.select(macd_s_cond, macd_s_choice, default=0.0)
    sm += np.where((macd_h < 0) & macd_decel, 0.5, 0)

    # SELL VWAP
    vwap_s_cond = [vwap_osc < -3.0, vwap_osc < -1.0, vwap_osc < 0]
    vwap_s_choice = [1.5, 1.0, 0.5]
    sm += np.select(vwap_s_cond, vwap_s_choice, default=0.0)

    # 바닥 추격매도 방지 및 하락 모멘텀
    rsi_s_cond = [df['RSI'] < 20, df['RSI'] <= 40, df['RSI'] <= 50]
    rsi_s_choice = [-1.0, 2.0, 1.0]
    sm += np.select(rsi_s_cond, rsi_s_choice, default=0.0)

    stoch_s_cond = [df['StochK'] < 15, df['StochK'] <= 40, df['StochK'] <= 50]
    stoch_s_choice = [-1.0, 2.0, 1.0]
    sm += np.select(stoch_s_cond, stoch_s_choice, default=0.0)

    wt1_s_cond = [df['WT1'] < -60, df['WT1'] <= -20, df['WT1'] <= 0]
    wt1_s_choice = [-1.0, 2.0, 1.0]
    sm += np.select(wt1_s_cond, wt1_s_choice, default=0.0)

    df['SJ_Momentum'] = sm.clip(lower=0)

    # ── Layer 3: 캔들 ──
    sc = pd.Series(0.0, index=idx)
    es_raw = df.get('Evening_Star', pd.Series(False, index=idx)).fillna(False)
    es_pts = np.where(es_raw & in_uptrend, 3.5, np.where(es_raw, 2.5, 0))
    be2_raw = df.get('Bearish_Engulfing', pd.Series(False, index=idx)).fillna(False)
    be2_pts = np.where(be2_raw & in_uptrend & (body_atr_ratio > 1.0), 3.5,
              np.where(be2_raw & in_uptrend, 3.0,
              np.where(be2_raw & (body_atr_ratio > 1.0), 2.5,
              np.where(be2_raw, 2.0, 0))))
    ss_raw = df.get('Shooting_Star', pd.Series(False, index=idx)).fillna(False)
    ss_pts = np.where(ss_raw & in_uptrend, 2.5, np.where(ss_raw, 1.5, 0))
    ob2_raw = df.get('Outside_Bearish', pd.Series(False, index=idx)).fillna(False)
    ob2_pts = np.where(ob2_raw & in_uptrend, 2.5, np.where(ob2_raw, 1.5, 0))
    dj2_pts = np.where(df.get('Doji_Bearish', pd.Series(False, index=idx)).fillna(False) & in_uptrend, 1.0,
              np.where(df.get('Doji_Bearish', pd.Series(False, index=idx)).fillna(False), 0.5, 0))
    all_sell_candle = np.stack([es_pts, be2_pts, ss_pts, ob2_pts, dj2_pts])
    sc = pd.Series(all_sell_candle.max(axis=0), index=idx)
    df['SJ_Candle'] = sc.clip(upper=5.0)

    # ── Layer 4: BB ──
    sb_ = pd.Series(0.0, index=idx)
    sb_ += _sig_pts(df, 'BB_Squeeze_End_Bear', 3.0)
    sb_ += nr7_val + nr72_val + calm_val
    sb_ += np.where(squeeze_on & below_50, 1.0, 0)
    sb_ += np.where(pct_b > 0.95, 2.5,
           np.where(pct_b > 0.8, 1.5,
           np.where((pct_b >= 0.4) & (pct_b <= 0.6) & below_50, 0.5,
           np.where(pct_b < 0.05, -1.5, 0))))
    aub = df.get('Above_Upper_BB', pd.Series(False, index=idx)).fillna(False)
    sb_ += np.where(aub & below_200, 2.0,
           np.where(aub & above_200, -0.5,
           np.where(aub, 1.0, 0)))
    df['SJ_BB'] = sb_.clip(lower=0, upper=7.0)

    # ── Layer 5: Volume ──
    sv = pd.Series(0.0, index=idx)
    sv += _sig_pts(df, 'Volume_Climax_Sell', 3.0)
    sv += _sig_pts(df, 'OBV_Div_Sell', 1.5)
    sv += np.where((vol_ratio >= 3.0) & (C < O), 2.5,
          np.where((vol_ratio >= 1.5) & (C < O), 1.0, 0))
    sv += np.where(obv_below & (obv < obv.shift(5)), 1.5,
          np.where(obv_below, 0.5, 0))
    sv += np.where(obv_above & (obv > obv.shift(5)), -1.0, 0)
    sv += np.where(vol_bull_ratio < 0.5, 1.5,
          np.where(vol_bull_ratio < 0.7, 0.5,
          np.where(vol_bull_ratio > 2.0, -1.0, 0)))
    df['SJ_Volume'] = sv.clip(lower=0, upper=7.0)

    # ── Layer 6: 자금흐름 (이전 수정 유지) ──
    smf = pd.Series(0.0, index=idx)
    smf += np.where(rmfi > 10, 2.0,
           np.where(rmfi > 5, 1.0,
           np.where(rmfi < -10, -0.5, 0)))
    if 'MF_Slope_5' in df.columns:
        mf_slope = df['MF_Slope_5']
        smf += np.where(mf_slope < -5, 2.0,
               np.where(mf_slope < -2, 1.5,
               np.where(mf_slope < 0, 0.5,
               np.where(mf_slope > 5, -1.0, 0))))
    if 'MF_Dn_Streak' in df.columns:
        smf += np.where(df['MF_Dn_Streak'] >= 5, 2.0,
               np.where(df['MF_Dn_Streak'] >= 3, 1.0, 0))
    smf += _sig_pts(df, 'MF_Cross_Bear', 2.0)
    smf += _sig_pts(df, 'MF_Bear_Div', 2.0)
    smf += _sig_pts(df, 'MF_Accel_Dn', 1.0)
    df['SJ_MF'] = smf.clip(lower=0, upper=8.0)

    # ── Layer 7: Pattern ──
    sp = pd.Series(0.0, index=idx)
    blood = _sig_pts(df, 'Blood_Diamond', 4.0)
    rdt1 = np.where(blood == 0, _sig_pts(df, 'Red_Dot_T1', 2.5), 0)
    rdt2 = np.where((blood == 0) & (rdt1 == 0), _sig_pts(df, 'Red_Dot_T2', 2.0), 0)
    sp += blood + rdt1 + rdt2
    brd_pts = np.where(blood == 0, _sig_pts(df, 'Bear_Divergence', 2.0), 0)
    sp += brd_pts
    for s, p in [('Pullback_123_Bear',2.5), ('Setup_180_Bear',2.0), ('Boomer_Sell',2.0),
                  ('Expansion_BD',3.0), ('Gilligans_Sell',2.5), ('Lizard_Bear',2.0),
                  ('NonADX_123_Bear',1.5), ('EMA_Pullback_Sell',2.0),
                  ('Momentum_Ignition_Sell',3.0), ('SuperTrend_Sell',2.0),
                  ('Gap_Down',1.0), ('Gap_Up_Closed',1.0),
                  ('New_52W_Low',2.0), ('Red_Diamond',2.0),
                  ('Hidden_Bear_Div',1.5), ('Squeeze_Fire_Sell',2.0),
                  ('Parabolic_Top_Sell',3.0)]:
        sp += _sig_pts(df, s, p)
    for s, decay_pts in [('Blood_Diamond',2.0), ('Red_Dot_T1',1.0), ('Expansion_BD',1.5),
                          ('Momentum_Ignition_Sell',1.5), ('Parabolic_Top_Sell',1.5)]:
        if s in df.columns:
            yesterday = df[s].shift(1).fillna(False)
            sp += np.where(yesterday & ~df[s], decay_pts * 0.5, 0)
    df['SJ_Pattern'] = sp.clip(upper=10.0)

    df['Sell_Total'] = (df['SJ_Trend'] + df['SJ_Momentum'] + df['SJ_Candle'] +
                        df['SJ_BB'] + df['SJ_Volume'] + df['SJ_MF'] + df['SJ_Pattern'])

    # ── 활성 레이어 + 판단 ──
    df['Buy_Active_Layers'] = sum((df[f'BJ_{n}'] > 0).astype(int) for n in ['Trend','Momentum','Candle','BB','Volume','MF','Pattern'])
    df['Sell_Active_Layers'] = sum((df[f'SJ_{n}'] > 0).astype(int) for n in ['Trend','Momentum','Candle','BB','Volume','MF','Pattern'])

    j = np.full(len(df), 'NEUTRAL', dtype=object)
    bt_v, st_v = df['Buy_Total'].values, df['Sell_Total'].values
    ba, sa = df['Buy_Active_Layers'].values, df['Sell_Active_Layers'].values
    for i in range(len(df)):
        b, s, bal, sal = bt_v[i], st_v[i], ba[i], sa[i]
        diff = b - s
        ratio = b / (s + 0.01)
        s_ratio = s / (b + 0.01)
        if b >= 17 and bal >= 4 and ratio >= 2.0 and diff >= 10:     j[i] = 'STRONG_BUY'
        elif b >= 11 and bal >= 3 and ratio >= 1.4 and diff >= 5:    j[i] = 'BUY'
        elif b >= 6 and bal >= 2 and diff >= 2:                       j[i] = 'WATCH_BUY'
        elif s >= 17 and sal >= 4 and s_ratio >= 2.0 and (s-b) >= 10:j[i] = 'STRONG_SELL'
        elif s >= 11 and sal >= 3 and s_ratio >= 1.4 and (s-b) >= 5: j[i] = 'SELL'
        elif s >= 6 and sal >= 2 and (s-b) >= 2:                     j[i] = 'WATCH_SELL'
        elif b >= 9 and s >= 9 and abs(diff) < 3:                    j[i] = 'MIXED'
    df['Trade_Judgment'] = j

    detect_combos(df, vol_ratio)
    return df

def detect_combos(df, vol_ratio):
    C, idx = df['Close'], df.index
    F = lambda col: df.get(col, pd.Series(False, index=idx))

    trend_up = (C > df['MA200']) & (C > df['MA50']) & (df['MA50'] > df['MA200'])
    trend_dn = (C < df['MA200']) & (C < df['MA50']) & (df['MA50'] < df['MA200'])
    candle_bull = F('Bullish_Engulfing') | F('Hammer') | F('Morning_Star') | F('Doji_Bullish')
    candle_bear = F('Bearish_Engulfing') | F('Shooting_Star') | F('Evening_Star') | F('Doji_Bearish')
    timing_bull = (df['StochK'] < 20) | F('StochRSI_Cross_Buy') | F('MACD_Cross_Buy') | (df['WT1'] < -30)
    timing_bear = (df['StochK'] > 80) | F('StochRSI_Cross_Sell') | F('MACD_Cross_Sell') | (df['WT1'] > 30)
    vol_confirm = vol_ratio >= 1.5
    squeeze_state = F('NR7') | F('NR7_2') | F('Inside_Day') | F('Calm_After_Storm') | (df['BB_Width'] <= df['BB_Width'].rolling(120, min_periods=20).quantile(0.1))

    # 🆕 MF 조건
    mf_bull = (df['RSI_MFI'] > df['RSI_MFI'].shift(1)) | (df['RSI_MFI'] > 0)   # MF 상승 중이거나 양수
    mf_bear = (df['RSI_MFI'] < df['RSI_MFI'].shift(1)) | (df['RSI_MFI'] < 0)   # MF 하락 중이거나 음수
    mf_strong_bull = F('MF_Strong_Up') | (df.get('MF_Slope_5', pd.Series(0, index=idx)) > 3)
    mf_strong_bear = F('MF_Strong_Dn') | (df.get('MF_Slope_5', pd.Series(0, index=idx)) < -3)

    # ═══ BUY 콤보 (MF 조건 추가) ═══
    ma_support = ((C - df['MA50']).abs() <= df['ATR'] * 1.5) | ((C - df['MA20']).abs() <= df['ATR'] * 1.0)
    df['Combo_TrendPullback_Buy'] = (
        trend_up & (C < df['MA20']) & ma_support &
        (candle_bull | timing_bull) &
        mf_bull &                                    # 🆕 MF도 상승/양수
        (df['BJ_Trend'] >= 5))

    df['Combo_VolSqueeze_Buy'] = (
        squeeze_state.shift(1).fillna(False) &
        (C > df['MA50']) &
        (F('BB_Squeeze_End_Bull') | (F('Wide_Range_Bar') & (C > df['Open']))) &
        vol_confirm &
        mf_bull)                                     # 🆕

    oversold_ext = (((df['StochK'] < 20) & (df['StochD'] < 20)).astype(int) + (df['RSI'] < 30).astype(int) + (df['WT1'] < -53).astype(int)) >= 2
    df['Combo_Reversal_Buy'] = (
        oversold_ext &
        ((C > df['MA200']) | (df['MA50'] > df['MA200'])) &
        (candle_bull | F('Gold_Dot') | F('Green_Dot_T1') | F('Lizard_Bull') | F('Gilligans_Buy')))
        # 반전은 MF 제외 (과매도에서 MF가 아직 음수일 수 있음)

    df['Combo_Momentum_Buy'] = (
        (F('New_52W_High') | F('Expansion_BO')) &
        (vol_confirm | F('Pocket_Pivot') | F('Momentum_Ignition_Buy')) &
        (df['ADX'] > 25) & (df['Plus_DI'] > df['Minus_DI']) &
        mf_strong_bull)                               # 🆕 MF 강한 상승

    df['Combo_MAConfluence_Buy'] = (
        (df['MA50'] > df['MA200']) & (C > df['MA200']) &
        (F('Cross_Above_20MA') | F('Cross_Above_50MA')) &
        (F('MACD_Cross_Buy') | F('StochRSI_Cross_Buy') | F('NonADX_123_Bull')) &
        mf_bull)                                      # 🆕

    # 🆕 새 콤보: MF 추세 전환 매수
    df['Combo_MF_Reversal_Buy'] = (
        F('MF_Cross_Bull') &                          # MF 0선 돌파
        (df['WT1'] < 20) &                            # 아직 과매수 아님
        (C > df['MA50']) &                            # 중기 추세 상승
        (candle_bull | timing_bull | vol_confirm))

    # ═══ SELL 콤보 (MF 조건 추가) ═══
    df['Combo_TrendRejection_Sell'] = (
        trend_dn & (C > df['MA20']) &
        (candle_bear | timing_bear) &
        mf_bear &                                     # 🆕
        (df['SJ_Trend'] >= 5))

    overbought_ext = (((df['StochK'] > 80) & (df['StochD'] > 80)).astype(int) + (df['RSI'] > 70).astype(int) + (df['WT1'] > 53).astype(int)) >= 2
    df['Combo_Exhaustion_Sell'] = (
        overbought_ext &
        (candle_bear | F('Gilligans_Sell') | F('Blood_Diamond') | F('Red_Dot_T1') | F('Parabolic_Top_Sell')))

    ma_break = (F('Fell_Below_20MA').astype(int) + F('Fell_Below_50MA').astype(int) + F('Fell_Below_200MA').astype(int) + F('Death_Cross').astype(int)) >= 1
    df['Combo_MABreakdown_Sell'] = (
        ma_break &
        (vol_confirm | F('MACD_Zero_Cross_Sell') | (F('Wide_Range_Bar') & (C < df['Open']))) &
        mf_bear &                                     # 🆕
        (df['SJ_Trend'] >= 3))

    df['Combo_VolSqueeze_Sell'] = (
        squeeze_state.shift(1).fillna(False) &
        (C < df['MA50']) &
        (F('BB_Squeeze_End_Bear') | (F('Wide_Range_Bar') & (C < df['Open']))) &
        vol_confirm & mf_bear)                        # 🆕

    gap_up_fail = F('Gap_Up').shift(1).fillna(False) & (C < df['Open']) & (candle_bear | F('Gilligans_Sell'))
    df['Combo_GapFailure_Sell'] = gap_up_fail | (F('Gap_Down') & vol_confirm & (F('Fell_Below_50MA') | F('Fell_Below_200MA')))

    # 🆕 새 콤보: MF 추세 전환 매도
    df['Combo_MF_Reversal_Sell'] = (
        F('MF_Cross_Bear') &
        (df['WT1'] > -20) &
        (C < df['MA50']) &
        (candle_bear | timing_bear | vol_confirm))
    
COMBO_MAP = {
    'Combo_TrendPullback_Buy':  ('🎯 추세 눌림목 매수', 'buy'),
    'Combo_VolSqueeze_Buy':     ('💥 변동성 수축 돌파', 'buy'),
    'Combo_Reversal_Buy':       ('🔄 반전 매수', 'buy'),
    'Combo_Momentum_Buy':       ('🚀 모멘텀 돌파', 'buy'),
    'Combo_MAConfluence_Buy':   ('📊 MA 합류 매수', 'buy'),
    'Combo_MF_Reversal_Buy':    ('💰 자금흐름 전환 매수', 'buy'),      # 🆕
    'Combo_TrendRejection_Sell':('🎯 추세 반등 실패', 'sell'),
    'Combo_Exhaustion_Sell':    ('🌡️ 고점 소진', 'sell'),
    'Combo_MABreakdown_Sell':   ('📉 MA 붕괴', 'sell'),
    'Combo_VolSqueeze_Sell':    ('💨 변동성 수축 붕괴', 'sell'),
    'Combo_GapFailure_Sell':    ('⏬ 갭 실패', 'sell'),
    'Combo_MF_Reversal_Sell':   ('💸 자금흐름 전환 매도', 'sell'),      # 🆕
}


def get_judgment_detail(row):
    # 7개 레이어로 변경
    bl = {n: float(row.get(f'BJ_{n}', 0)) for n in ['Trend','Momentum','Candle','BB','Volume','MF','Pattern']}
    sl = {n: float(row.get(f'SJ_{n}', 0)) for n in ['Trend','Momentum','Candle','BB','Volume','MF','Pattern']}
    combos = [{'name': name, 'dir': d} for col, (name, d) in COMBO_MAP.items() if row.get(col, False)]
    return {
        'judgment': str(row.get('Trade_Judgment', 'NEUTRAL')),
        'buy_total': float(row.get('Buy_Total', 0)),
        'sell_total': float(row.get('Sell_Total', 0)),
        'buy_layers': bl, 'sell_layers': sl,
        'buy_active': int(row.get('Buy_Active_Layers', 0)),
        'sell_active': int(row.get('Sell_Active_Layers', 0)),
        'active_combos': combos,
        'net': float(row.get('Buy_Total', 0)) - float(row.get('Sell_Total', 0)),
    }
# ──────────────────────────────────────────
# 🆕 Money Flow 확장 시그널
# ──────────────────────────────────────────

def detect_mf_signals(c, rmfi):
    """
    Money Flow 기반 시그널 탐지
    - MF 0선 교차
    - MF 추세 (5일 연속 상승/하락)
    - MF 가속 (기울기 증가)
    - MF-가격 다이버전스
    """
    # ── MF 0선 교차 ──
    mf_cross_bull = (rmfi > 0) & (rmfi.shift(1) <= 0)   # 음→양
    mf_cross_bear = (rmfi < 0) & (rmfi.shift(1) >= 0)   # 양→음

    # ── MF 추세 (방향) ──
    mf_rising = rmfi > rmfi.shift(1)   # 오늘 > 어제
    mf_falling = rmfi < rmfi.shift(1)

    # 연속 상승/하락 카운트
    mf_up_streak = pd.Series(0, index=c.index, dtype=int)
    mf_dn_streak = pd.Series(0, index=c.index, dtype=int)
    for i in range(1, len(c)):
        if mf_rising.iloc[i]:
            mf_up_streak.iloc[i] = mf_up_streak.iloc[i-1] + 1
        else:
            mf_up_streak.iloc[i] = 0
        if mf_falling.iloc[i]:
            mf_dn_streak.iloc[i] = mf_dn_streak.iloc[i-1] + 1
        else:
            mf_dn_streak.iloc[i] = 0

    mf_strong_up = mf_up_streak >= 3       # 3일+ 연속 MF 상승
    mf_strong_dn = mf_dn_streak >= 3       # 3일+ 연속 MF 하락
    mf_accel_up = mf_up_streak >= 5        # 5일+ 연속 = 가속
    mf_accel_dn = mf_dn_streak >= 5

    # ── MF 기울기 (5일 변화량) ──
    mf_slope_5 = rmfi - rmfi.shift(5)      # 5일간 변화
    mf_slope_10 = rmfi - rmfi.shift(10)    # 10일간 변화

    # ── MF-가격 다이버전스 (간소화 버전) ──
    # 가격은 5일 저점 갱신인데 MF는 5일 전보다 높음 = 강세 다이버전스
    price_lower = c < c.rolling(5).min().shift(1)
    mf_higher = rmfi > rmfi.rolling(5).min().shift(1)
    mf_bull_div = price_lower & mf_higher & (rmfi < 0)

    price_higher = c > c.rolling(5).max().shift(1)
    mf_lower = rmfi < rmfi.rolling(5).max().shift(1)
    mf_bear_div = price_higher & mf_lower & (rmfi > 0)

    return {
        'MF_Cross_Bull': mf_cross_bull,
        'MF_Cross_Bear': mf_cross_bear,
        'MF_Strong_Up': mf_strong_up,
        'MF_Strong_Dn': mf_strong_dn,
        'MF_Accel_Up': mf_accel_up,
        'MF_Accel_Dn': mf_accel_dn,
        'MF_Slope_5': mf_slope_5,
        'MF_Slope_10': mf_slope_10,
        'MF_Bull_Div': mf_bull_div,
        'MF_Bear_Div': mf_bear_div,
        'MF_Rising': mf_rising,
        'MF_Falling': mf_falling,
        'MF_Up_Streak': mf_up_streak,
        'MF_Dn_Streak': mf_dn_streak,
    }


# ──────────────────────────────────────────
# 호버 텍스트 빌더
# ──────────────────────────────────────────
def _build_judgment_hover(row, signals_dict):
    judgment = str(row.get('Trade_Judgment', 'NEUTRAL'))
    bt, st_ = float(row.get('Buy_Total', 0)), float(row.get('Sell_Total', 0))
    net = bt - st_
    ico = '🟢' if 'BUY' in judgment else ('🔴' if 'SELL' in judgment else '🟠')
    lines = [f"<b style='font-size:13px'>{ico} {judgment}</b>",
             f"<b>BUY</b> {bt:.1f} vs <b>SELL</b> {st_:.1f} (NET: {net:+.1f})", "─" * 26]

    lnames = ['Trend','Momentum','Candle','BB','Volume','MF','Pattern']
    licons = ['📈','🔥','🕯️','📊','📦','💰','⭐']

    bparts = [f"{ic}{n}:{float(row.get(f'BJ_{n}',0)):.1f}" for ic, n in zip(licons, lnames) if float(row.get(f'BJ_{n}',0)) > 0]
    sparts = [f"{ic}{n}:{float(row.get(f'SJ_{n}',0)):.1f}" for ic, n in zip(licons, lnames) if float(row.get(f'SJ_{n}',0)) > 0]
    if bparts: lines.append(f"<span style='color:#34D399'><b>▲</b> {' · '.join(bparts)}</span>")
    if sparts: lines.append(f"<span style='color:#F87171'><b>▼</b> {' · '.join(sparts)}</span>")
    lines.append("─" * 26)

    combos = [name for col, (name, _) in COMBO_MAP.items() if row.get(col, False)]
    lines.append(f"<b>🔥 콤보:</b> {' / '.join(combos)}" if combos else "<span style='color:#64748B'>콤보 없음</span>")
    lines.append("─" * 26)

    bsigs, ssigs = [], []
    for sn, cfg in signals_dict.items():
        if sn.startswith('Combo_') or sn in ('Ultra_Buy','Strong_Buy','Ultra_Sell','Strong_Sell'): continue
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
    if not bsigs and not ssigs: lines.append("<span style='color:#64748B'>지표 점수 기반 판단</span>")
    return "<br>".join(lines)

# ══════════════════════════════════════════════════════════════
#  CipherX V11.0 — PART 2/3
#  detect_all_signals + confluence + chart + metadata + prompt
# ══════════════════════════════════════════════════════════════

# ──────────────────────────────────────────
# 통합 시그널 탐지 엔진
# ──────────────────────────────────────────
def detect_all_signals(df):
    H, L, C, O, V = df['High'], df['Low'], df['Close'], df['Open'], df['Volume']
    e8, e21, m10, m20, m50, m200 = df['EMA8'], df['EMA21'], df['MA10'], df['MA20'], df['MA50'], df['MA200']
    wt1, wt2, atr = df['WT1'], df['WT2'], df['ATR']

    htf1 = (e8 > e21) & (e21 > e21.shift(5))
    htf2 = (C > m50) & (m50 > m50.shift(10))
    wun = _recent(df['WT_Up'], 2); wdn = _recent(df['WT_Down'], 2)
    wur = _recent(df['WT_Up'], 3); wdr = _recent(df['WT_Down'], 3)
    vok = _volf(V, 0.5)

    sb = (df['ADX'] > 25) & (df['Plus_DI'] > df['Minus_DI']) & (C > m50)
    sbe = (df['ADX'] > 25) & (df['Minus_DI'] > df['Plus_DI']) & (C < m50)
    xb = sb & (C > m200) & (m50 > m50.shift(5))
    xbe = sbe & (C < m200) & (m50 < m50.shift(5))
    mfb = df['RSI_MFI'] > -10; mfs = df['RSI_MFI'] < 10

    para_bot, para_top = _detect_parabolic_pair(C, O, wt1, df['BB_Up'], df['BB_Low'], atr)
    st_fb = (df['ST_Direction'] == -1) & (df['ST_Direction'].shift(1) == 1)
    st_fb.iloc[:ST_MIN_BAR] = False; st_bo = _recent(st_fb, 3)
    st_fb2 = (df['ST_Direction'] == 1) & (df['ST_Direction'].shift(1) == -1)
    st_fb2.iloc[:ST_MIN_BAR] = False; st_bu = _recent(st_fb2, 3)

    ssb = sb & (~para_top) & (~st_bo); ssx = xb & (~para_top) & (~st_bo)
    bsb = sbe & (~para_bot) & (~st_bu); bsx = xbe & (~para_bot) & (~st_bu)

    # ═══ MCB+ 시그널 ═══
    df['Green_Dot_T1'] = wun & (wt1 <= OS1) & (df['RSI'] < 30) & (df['MFI'] < 30) & (df['RSI_MFI'] < 0) & (~bsx) & vok
    df['Green_Dot_T2'] = wun & (wt1 <= OS1) & ((df['RSI'] < 32) | (df['MFI'] < 32)) & ~df['Green_Dot_T1'] & (~bsb) & vok
    _gd = df['Green_Dot_T1'] | df['Green_Dot_T2']
    df['Red_Dot_T1'] = wdn & (wt1 >= OB1) & (df['RSI'] > 70) & (df['MFI'] > 70) & (df['RSI_MFI'] > 0) & (~ssx) & vok
    df['Red_Dot_T2'] = wdn & (wt1 >= OB1) & ((df['RSI'] > 68) | (df['MFI'] > 68)) & ~df['Red_Dot_T1'] & (~ssb) & vok
    _rd = df['Red_Dot_T1'] | df['Red_Dot_T2']

    df['Blue_Diamond'] = (wt2 <= 0) & wun & htf1 & htf2 & (~bsb) & mfb & vok
    df['Red_Diamond'] = (wt2 >= 0) & wdn & ~htf1 & ~htf2 & (~ssb) & mfs & vok
    df['Green_Circle'] = wun & (wt1 <= OS1) & ~_gd & (~bsb) & vok & (df['RSI'] < 45)
    df['Red_Circle'] = wdn & (wt1 >= OB1) & ~_rd & (~ssb) & vok & (df['RSI'] > 55)

    bd, brd, hb, hbr = detect_pivot_div(C, wt1, 60, 5, OS1, OB1)
    bdr = _recent(bd, 3); brdr = _recent(brd, 3)
    rbd, rbrd, _, _ = detect_pivot_div(C, df['RSI'], 60, 5, 35, 65)
    obd, obrd, _, _ = detect_pivot_div(C, df['OBV'], 60, 5)

    df['Gold_Dot'] = df['Green_Dot_T1'] & (wt1 <= OS2) & bdr
    df['Blood_Diamond'] = df['Red_Dot_T1'] & (wt1 >= OB2) & brdr
    df['Bull_Divergence'] = bd & wur & ~_gd & ~df['Gold_Dot'] & (~bsb) & vok
    df['Bear_Divergence'] = brd & wdr & ~_rd & (~ssb) & vok
    df['RSI_Bull_Divergence'] = rbd & (wt1 < -20) & (~bsb) & vok & ~bd
    df['RSI_Bear_Divergence'] = rbrd & (wt1 > 20) & (~ssb) & vok & ~brd
    vol_ok_hidden = _volf(V, 0.7)
    df['Hidden_Bull_Div'] = hb & (wt1 < -25) & htf2 & (~bsx) & vol_ok_hidden
    df['Hidden_Bear_Div'] = hbr & (wt1 > 25) & ~htf2 & (~ssx) & vol_ok_hidden
    df['OBV_Div_Buy'] = obd & (wt1 < -30) & (~bsx)
    df['OBV_Div_Sell'] = obrd & (wt1 > 30) & (~ssx)

    sqo, sqb, sqs = detect_ttm_squeeze(df['BB_Up'], df['BB_Low'], df['KC_Upper'], df['KC_Lower'], C, H, L, df['KC_Mid'])
    df['Squeeze_On'] = sqo
    df['Squeeze_Fire_Buy'] = sqb & (~bsb) & vok
    df['Squeeze_Fire_Sell'] = sqs & (~ssb) & vok

    df['Volume_Climax_Buy'], df['Volume_Climax_Sell'] = detect_volume_climax(C, O, V, wt1, atr)

    ax = (df['ADX'] > 20) & (df['ADX'].shift(1) <= 20)
    df['ADX_Momentum_Buy'] = ax & (df['Plus_DI'] > df['Minus_DI']) & (wt1 > wt2) & vok
    df['ADX_Momentum_Sell'] = ax & (df['Minus_DI'] > df['Plus_DI']) & (wt1 < wt2) & vok

    df['Bullish_Engulfing'], df['Bearish_Engulfing'] = _detect_engulfing_pair(C, O, wt1)
    df['Bullish_Engulfing'] &= (~bsb) & vok; df['Bearish_Engulfing'] &= (~ssb) & vok

    gc = (m50 > m200) & (m50.shift(1) <= m200.shift(1))
    dc = (m50 < m200) & (m50.shift(1) >= m200.shift(1))
    af = df['ADX'] > 15; vc = _volf(V, 0.7)
    df['Golden_Cross'] = gc & af & vc; df['Death_Cross'] = dc & af & vc

    df['EMA_Pullback_Buy'], df['EMA_Pullback_Sell'] = _detect_ema_pullback_pair(C, H, L, V, e8, e21, atr, wt1, wt2)
    df['Momentum_Ignition_Buy'], df['Momentum_Ignition_Sell'] = _detect_mom_ignition_pair(C, O, V, df['BB_Up'], df['BB_Low'], atr, e8, e21, wt1, df['BB_Width'])
    df['SuperTrend_Buy'] = st_fb2; df['SuperTrend_Sell'] = st_fb

    vp = _volf(V, 1.0)
    df['Parabolic_Top_Sell'] = para_top & ((df['WT_Down'] | wdr) | ((C < O) & (C < C.shift(1)))) & vp
    df['Parabolic_Bottom_Buy'] = para_bot & ((df['WT_Up'] | wur) | ((C > O) & (C > C.shift(1)))) & vp
    df['VWAP_Bounce_Buy'], df['VWAP_Reject_Sell'] = _detect_vwap_pair(C, df['VWAP_Osc'], wt1, wt2, V, atr)

    ml, ms = df['MACD_Line'], df['MACD_Signal']
    df['MACD_Cross_Buy'] = (ml > ms) & (ml.shift(1) <= ms.shift(1)) & (ml < 0) & (~bsb) & vok
    df['MACD_Cross_Sell'] = (ml < ms) & (ml.shift(1) >= ms.shift(1)) & (ml > 0) & (~ssb) & vok
    df['StochRSI_Cross_Buy'] = (df['StochK'] > df['StochD']) & (df['StochK'].shift(1) <= df['StochD'].shift(1)) & (df['StochK'] < 25) & (~bsb) & vok
    df['StochRSI_Cross_Sell'] = (df['StochK'] < df['StochD']) & (df['StochK'].shift(1) >= df['StochD'].shift(1)) & (df['StochK'] > 75) & (~ssb) & vok

    # ═══ 캔들스틱 ═══
    (df['Hammer'], df['Shooting_Star'], df['Doji_Bullish'], df['Doji_Bearish'],
     df['Morning_Star'], df['Evening_Star'], df['Spinning_Top']) = detect_candlestick_patterns(C, O, H, L, wt1, atr)
    df['Hammer'] &= (~bsb) & vok; df['Shooting_Star'] &= (~ssb) & vok
    df['Doji_Bullish'] &= (~bsb) & vok; df['Doji_Bearish'] &= (~ssb) & vok
    df['Morning_Star'] &= (~bsb) & vok; df['Evening_Star'] &= (~ssb) & vok

    # ═══ Inside/Outside ═══
    df['Inside_Day'], df['Outside_Bullish'], df['Outside_Bearish'] = detect_inside_outside_day(H, L, C, O, wt1)
    df['Outside_Bullish'] &= (~bsb) & vok; df['Outside_Bearish'] &= (~ssb) & vok

    # ═══ MA 돌파/이탈 ═══
    for k, v in detect_ma_crossovers(C, m20, m50, m200).items(): df[k] = v

    # ═══ 볼린저 밴드 ═══
    (df['Above_Upper_BB'], df['Below_Lower_BB'],
     df['BB_Squeeze_End_Bull'], df['BB_Squeeze_End_Bear']) = detect_bb_extra(C, df['BB_Up'], df['BB_Low'], df['BB_Width'], wt1)

    # ═══ MACD 센터라인 ═══
    df['MACD_Zero_Cross_Buy'], df['MACD_Zero_Cross_Sell'] = detect_macd_centerline(df['MACD_Line'])

    # ═══ 연속 상승/하락 ═══
    for k, v in detect_consecutive_days(C).items(): df[k] = v

    # ═══ 갭 ═══
    df['Gap_Up'], df['Gap_Down'], df['Gap_Up_Closed'], df['Gap_Down_Closed'] = detect_gaps(C, O, H, L, atr)

    # ═══ 변동성 패턴 ═══
    df['NR7'], df['NR7_2'] = detect_nr7(H, L)
    df['Wide_Range_Bar'], df['Calm_After_Storm'] = detect_range_bars(H, L, atr)

    # ═══ 52주 ═══
    df['New_52W_High'], df['New_52W_Low'] = detect_52w(C, H, L)

    # ═══ Jeff Cooper ═══
    df['Pullback_123_Bull'], df['Pullback_123_Bear'] = detect_123_pullback(H, L, C, df['ADX'], df['Plus_DI'], df['Minus_DI'])
    df['Setup_180_Bull'], df['Setup_180_Bear'] = detect_180_setup(C, O, H, L, m10, m50)
    df['Boomer_Buy'], df['Boomer_Sell'] = detect_boomer(H, L, df['ADX'], df['Plus_DI'], df['Minus_DI'])
    df['Expansion_BO'], df['Expansion_BD'] = detect_expansion(H, L, C)
    df['Gilligans_Buy'], df['Gilligans_Sell'] = detect_gilligans(O, C, H, L)
    df['Lizard_Bull'], df['Lizard_Bear'] = detect_lizard(O, C, H, L)
    df['NonADX_123_Bull'], df['NonADX_123_Bear'] = detect_non_adx_123(H, L, C, m50)
    df['Pocket_Pivot'] = detect_pocket_pivot(C, O, V, m50, m200)

    # ═══ 쿨다운 (방향별 + 일반) ═══
    # 🆕 페어 시그널: BUY 쿨다운 중에도 SELL은 허용 (반대도 마찬가지)
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
    }
    
    # 페어 시그널은 방향별 쿨다운 적용
    paired_handled = set()
    for (buy_sig, sell_sig), cd in PAIRED_COOLDOWNS.items():
        _cooldown_directional(df, buy_sig, sell_sig, cd)
        paired_handled.add(buy_sig)
        paired_handled.add(sell_sig)
    
    # 나머지 시그널은 일반 쿨다운
    for s, cd in COOLDOWN_MAP.items():
        if s in df.columns and s not in paired_handled:
            df[s] = _cooldown(df[s], cd)

    _deduplicate(df)

    # ═══ Confluence (내부 참고용) ═══
    compute_confluence(df)

    # ═══ Proximity ═══
    df['Buy_Proximity'], df['Sell_Proximity'] = compute_proximity(
        wt1, wt2, df['RSI'], df['MFI'], df['RSI_MFI'],
        df['StochK'], df['MACD_Hist'], df['BB_Width'], sb, sbe)

    # ═══ 메타 ═══
    df['Strong_Bull'], df['Strong_Bear'] = sb, sbe
    df['Parabolic_Blowoff'] = para_top
    df['Parabolic_Bottom_Raw'] = para_bot
    df['ST_Bear_Override'] = st_bo
    df['Sell_Shield_Overridden'] = para_top | st_bo
    df['Buy_Shield_Overridden'] = para_bot | st_bu
    df['_HTF1_Bull'], df['_HTF2_Bull'] = htf1, htf2

    # ═══ 🆕 Money Flow 확장 시그널 ═══
    mf_sigs = detect_mf_signals(C, df['RSI_MFI'])
    df['MF_Cross_Bull'] = mf_sigs['MF_Cross_Bull'] & (~bsb) & vok
    df['MF_Cross_Bear'] = mf_sigs['MF_Cross_Bear'] & (~ssb) & vok
    df['MF_Bull_Div'] = mf_sigs['MF_Bull_Div'] & (~bsb) & vok
    df['MF_Bear_Div'] = mf_sigs['MF_Bear_Div'] & (~ssb) & vok
    df['MF_Accel_Up'] = mf_sigs['MF_Accel_Up']
    df['MF_Accel_Dn'] = mf_sigs['MF_Accel_Dn']

    # MF 내부 데이터 저장 (판단 엔진용)
    df['MF_Slope_5'] = mf_sigs['MF_Slope_5']
    df['MF_Slope_10'] = mf_sigs['MF_Slope_10']
    df['MF_Rising'] = mf_sigs['MF_Rising']
    df['MF_Falling'] = mf_sigs['MF_Falling']
    df['MF_Strong_Up'] = mf_sigs['MF_Strong_Up']
    df['MF_Strong_Dn'] = mf_sigs['MF_Strong_Dn']
    df['MF_Up_Streak'] = mf_sigs['MF_Up_Streak']
    df['MF_Dn_Streak'] = mf_sigs['MF_Dn_Streak']

    # ═══ 🆕 7-Layer 판단 엔진 ═══
    compute_trade_judgment(df)

    return df


# ──────────────────────────────────────────
# Confluence / Proximity / Bias
# ──────────────────────────────────────────
def compute_confluence(df, dw=5, df_=0.75):
    bm = {k: v['w'] for k, v in SIGNAL_REGISTRY.items() if v['dir'] == 'buy'}
    sm = {k: v['w'] for k, v in SIGNAL_REGISTRY.items() if v['dir'] == 'sell'}
    dk = np.array([df_**i for i in range(dw+1)]); ones = np.ones(dw+1)
    s = np.zeros(len(df)); bc = np.zeros(len(df)); sc = np.zeros(len(df))
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
    s += np.where(wt1 < OS1, 1.0, 0) + np.where(wt1 < OS2, 0.5, 0) - np.where(wt1 > OB1, 1.0, 0) - np.where(wt1 > OB2, 0.5, 0)
    adx = df['ADX'].values; pdi = df['Plus_DI'].values; mdi = df['Minus_DI'].values
    bt = pdi > mdi; brt = mdi > pdi; af = np.clip((adx-20)/100, 0.0, 0.3)
    s += np.where(bt & (s > 0), s*af, 0); s -= np.where(brt & (s < 0), abs(s)*af, 0)
    df['Confluence_Score'] = s
    df['Ultra_Buy'] = (s >= 6.5) | ((s >= 5) & (bc >= 3))
    df['Ultra_Sell'] = (s <= -6.5) | ((s <= -5) & (sc >= 3))
    df['Strong_Buy'] = (s >= 3.5) & (~df['Ultra_Buy'])
    df['Strong_Sell'] = (s <= -3.5) & (~df['Ultra_Sell'])
    return s


def compute_proximity(wt1, wt2, rsi, mfi, rmfi, stk, macd_h, bb_w, sb, sbe):
    bp = pd.Series(0.0, index=wt1.index); sp = pd.Series(0.0, index=wt1.index)
    gap = (wt1 - wt2).abs(); nc = gap < 3
    cu = (wt1 - wt2) > (wt1.shift(1) - wt2.shift(1))
    cd = (wt1 - wt2) < (wt1.shift(1) - wt2.shift(1))

    for cond, pts in [
        ((wt1 < -40) & nc, 30), ((wt1 < -40) & cu & (gap < 8), 15),
        (wt1 < OS2, 20), ((wt1 >= OS2) & (wt1 < -40), 10),
        (rsi < 35, 15), ((rsi >= 35) & (rsi < 45), 5),
        (mfi < 35, 15), ((mfi >= 35) & (mfi < 45), 5),
        (rmfi < -5, 10), ((rmfi >= -5) & (rmfi < 0), 5),
        # 🆕 MF 방향 가점
        (rmfi > rmfi.shift(1), 5),  # MF 상승 중
        (rmfi > rmfi.shift(3), 3),  # 3일 전보다 높음
        (stk < 20, 10), ((stk >= 20) & (stk < 35), 5),
        (macd_h < 0, 3), (macd_h < macd_h.shift(1), 2),
    ]:
        bp += np.where(cond, pts, 0)

    for cond, pts in [
        ((wt1 > 40) & nc, 30), ((wt1 > 40) & cd & (gap < 8), 15),
        (wt1 > OB1, 20), ((wt1 <= OB1) & (wt1 > 40), 10),
        (rsi > 65, 15), ((rsi <= 65) & (rsi > 55), 5),
        (mfi > 65, 15), ((mfi <= 65) & (mfi > 55), 5),
        (rmfi > 5, 10), ((rmfi <= 5) & (rmfi > 0), 5),
        # 🆕 MF 방향 가점
        (rmfi < rmfi.shift(1), 5),
        (rmfi < rmfi.shift(3), 3),
        (stk > 80, 10), ((stk <= 80) & (stk > 65), 5),
        (macd_h > 0, 3), (macd_h > macd_h.shift(1), 2),
    ]:
        sp += np.where(cond, pts, 0)

    bb_narrow = bb_w < bb_w.rolling(50).quantile(0.2)
    bp += np.where(bb_narrow, 5, 0); sp += np.where(bb_narrow, 5, 0)
    bp, sp = bp.clip(upper=100), sp.clip(upper=100)
    net = bp - sp

    return (pd.Series(np.where(net >= 0, bp, bp * np.where(sbe, .4, .55)), index=wt1.index),
            pd.Series(np.where(net <= 0, sp, sp * np.where(sb, .4, .55)), index=wt1.index))

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
    if sc >= 9.0: return 'STRONG BUY', sc
    elif sc >= 3.5: return 'BUY', sc
    elif sc > -3.5: return 'NEUTRAL', sc
    elif sc > -9.0: return 'SELL', sc
    else: return 'STRONG SELL', sc


def compute_signal_stats(df, col, direction, fwd=(2, 3, 5), mn=5):
    if col not in df.columns: return None
    mask = df[col].fillna(False).values.astype(bool)
    if mask.sum() < mn: return None
    st_res = {'count': int(mask.sum())}
    entry_price = df['Open'].shift(-1)
    for n in fwd:
        exit_price = df['Close'].shift(-(n+1))
        pct = (exit_price - entry_price) / entry_price * 100
        vr = pct[mask].dropna()
        if len(vr) >= mn:
            st_res[f'{n}d_avg'] = float(vr.mean())
            st_res[f'{n}d_winrate'] = float((vr < 0).sum() / len(vr) * 100) if direction == 'sell' else float((vr > 0).sum() / len(vr) * 100)
            st_res[f'{n}d_median'] = float(vr.median())
        else: st_res[f'{n}d_avg'] = st_res[f'{n}d_winrate'] = st_res[f'{n}d_median'] = None
    return st_res


def compute_all_stats(dv):
    tgt = {k: v['dir'] for k, v in SIGNAL_REGISTRY.items()}
    tgt.update({'Ultra_Buy':'buy','Strong_Buy':'buy','Ultra_Sell':'sell','Strong_Sell':'sell'})
    return {s: {**r, 'direction': d} for s, d in tgt.items() if (r := compute_signal_stats(dv, s, d)) and r['count'] > 0}


# ──────────────────────────────────────────
# 차트 유틸리티
# ──────────────────────────────────────────
def _hl(fig, mask, idx, fill, txt=None, row=1):
    d = mask.astype(int).diff().fillna(0)
    starts = idx[d == 1].tolist(); ends = idx[d == -1].tolist()
    if len(mask) > 0 and mask.iloc[0]: starts.insert(0, idx[0])
    if len(mask) > 0 and mask.iloc[-1]: ends.append(idx[-1])
    for s, e in zip(starts, ends):
        kw = dict(x0=s, x1=e, fillcolor=fill, line_width=0, row=row, col=1)
        if txt: kw.update(annotation_text=txt, annotation_position="top left",
                          annotation_font_size=10, annotation_font_color="#FF5252")
        fig.add_vrect(**kw)


# ──────────────────────────────────────────
# 🆕 차트 빌더 — 판단 마커 Only
# ──────────────────────────────────────────
def build_chart(dc, ticker, regime, shield):
    mac = {5:"#ff9900", 10:"#ffb74d", 20:'#f1c40f', 50:'#e74c3c',
           100:'#9b59b6', 125:'#3498db', 200:'#2ecc71'}

    fig = make_subplots(
        rows=6, cols=1, shared_xaxes=True, vertical_spacing=0.035,
        row_heights=[.36, .07, .15, .12, .15, .15],
        subplot_titles=("", "Volume", "WaveTrend Oscillator",
                        "Money Flow", "MACD (12, 26, 9)", "BUY / SELL Judgment"))

    # ═══ Row 1: 캔들스틱 ═══
    fig.add_trace(go.Candlestick(
        x=dc.index, open=dc['Open'], high=dc['High'], low=dc['Low'], close=dc['Close'],
        name="Price", increasing_line_color='#00E676', decreasing_line_color='#FF1744',
        increasing_fillcolor='rgba(0,230,118,0.8)', decreasing_fillcolor='rgba(255,23,68,0.8)',
        hovertemplate="O:%{open:.2f} H:%{high:.2f}<br>L:%{low:.2f} C:%{close:.2f}<extra></extra>"),
        row=1, col=1)

    # ── 이동평균 ──
    for ma in [5, 10, 20, 50, 100, 125, 200]:
        fig.add_trace(go.Scatter(x=dc.index, y=dc[f'MA{ma}'],
            line=dict(color=mac[ma], width=1.2), name=f'{ma}MA',
            hovertemplate="%{y:.2f}"), row=1, col=1)

    # ── EMA ──
    for nm, col_n, clr, dash in [('EMA8','EMA8','#00FFFF','dot'),('EMA21','EMA21','#FF69B4','dot')]:
        fig.add_trace(go.Scatter(x=dc.index, y=dc[col_n],
            line=dict(color=clr, width=1.5, dash=dash), name=nm,
            hovertemplate="%{y:.2f}"), row=1, col=1)

    # ── 슈퍼트렌드 ──
    for mc, clr, nm in [(dc['ST_Direction']==1,'#00E676','ST▲'),(dc['ST_Direction']==-1,'#FF1744','ST▼')]:
        fig.add_trace(go.Scatter(x=dc.index, y=dc['SuperTrend'].where(mc),
            line=dict(color=clr, width=2), name=nm, connectgaps=False,
            hovertemplate="%{y:.2f}"), row=1, col=1)

    # ── 볼린저 밴드 ──
    fig.add_trace(go.Scatter(x=dc.index, y=dc['BB_Up'], line=dict(color='gray', width=1, dash='dot'),
        name='BB↑', hovertemplate="%{y:.2f}"), row=1, col=1)
    fig.add_trace(go.Scatter(x=dc.index, y=dc['BB_Low'], line=dict(color='gray', width=1, dash='dot'),
        name='BB↓', fill='tonexty', fillcolor='rgba(128,128,128,0.07)',
        hovertemplate="%{y:.2f}"), row=1, col=1)

    # ── Shield 배경 ──
    for col_name, clr, txt in [('Sell_Shield_Overridden','rgba(255,0,0,0.04)','🔓Sell OFF'),
                                 ('Buy_Shield_Overridden','rgba(0,255,0,0.04)','🔓Buy OFF')]:
        om = dc.get(col_name, pd.Series(False, index=dc.index))
        if om.any(): _hl(fig, om, dc.index, clr, txt, 1)

    # ═══ 🆕 BUY/SELL 판단 마커 (핵심) ═══
    if 'Trade_Judgment' in dc.columns:
        enabled_j = st.session_state.get('enabled_judgments', set(JUDGMENT_MARKERS.keys()))

        for j_grade, j_cfg in JUDGMENT_MARKERS.items():
            if j_grade not in enabled_j: continue
            mask = dc['Trade_Judgment'] == j_grade
            if not mask.any(): continue

            sig_rows = dc[mask]
            if j_cfg['base'] == 'Low':
                y_vals = sig_rows['Low'] + sig_rows['ATR'] * j_cfg['atr_mult']
            else:
                y_vals = sig_rows['High'] + sig_rows['ATR'] * j_cfg['atr_mult']

            hover_texts = [_build_judgment_hover(dc.loc[idx_v], ALL_CHART_SIGNALS) for idx_v in sig_rows.index]

            fig.add_trace(go.Scatter(
                x=sig_rows.index, y=y_vals, mode='markers',
                marker=dict(symbol=j_cfg['symbol'], size=j_cfg['size'], color=j_cfg['color'],
                    line=dict(width=j_cfg['line_width'], color=j_cfg['line_color']), opacity=0.95),
                name=j_cfg['label'], text=hover_texts,
                hovertemplate="%{text}<extra></extra>",
                hoverlabel=dict(bgcolor='rgba(14,17,23,0.97)', bordercolor=j_cfg['color'],
                    font=dict(size=11, family='Pretendard', color='#FAFAFA'), align='left'),
            ), row=1, col=1)

        # 판단 배경
        for j_name, fill_clr in [('STRONG_BUY','rgba(0,230,118,0.05)'),('BUY','rgba(0,230,118,0.025)'),
                                   ('STRONG_SELL','rgba(255,23,68,0.05)'),('SELL','rgba(255,23,68,0.025)')]:
            jm = dc['Trade_Judgment'] == j_name
            if jm.any(): _hl(fig, jm, dc.index, fill_clr, None, 1)

    # ═══ Row 2: 거래량 ═══
    br = dc['Close'] < dc['Open']
    fig.add_trace(go.Bar(x=dc.index, y=dc['Volume'],
        marker_color=np.where(br,'rgba(255,23,68,0.6)','rgba(0,230,118,0.6)').tolist(),
        name="Volume", opacity=0.8, hovertemplate="%{y:,.0f}"), row=2, col=1)
    vcm = dc.get('Volume_Climax_Buy', pd.Series(False)) | dc.get('Volume_Climax_Sell', pd.Series(False))
    vcd = dc[vcm]
    if not vcd.empty:
        fig.add_trace(go.Bar(x=vcd.index, y=vcd['Volume'], marker_color='#FFD700',
            name="Vol Climax", opacity=0.9, hovertemplate="%{y:,.0f}"), row=2, col=1)

    # ═══ Row 3: WaveTrend ═══
    fig.add_trace(go.Scatter(x=dc.index, y=dc['WT1'], line=dict(color='#00E676', width=2),
        name="WT1", hovertemplate="%{y:.1f}"), row=3, col=1)
    fig.add_trace(go.Scatter(x=dc.index, y=dc['WT2'], line=dict(color='#FF1744', width=1.5, dash='dot'),
        name="WT2", hovertemplate="%{y:.1f}"), row=3, col=1)
    wd = dc['WT1'] - dc['WT2']
    fig.add_trace(go.Bar(x=dc.index, y=wd,
        marker_color=np.where(wd >= 0, '#00E676', '#FF1744').tolist(),
        name="WT Hist", opacity=0.3, hovertemplate="%{y:.1f}"), row=3, col=1)
    for lv, cc, d in [(OB2,'#ff3333','dash'),(OB1,'#ff3333','solid'),(0,'gray','dot'),(OS1,'#00bfff','solid'),(OS2,'#00bfff','dash')]:
        fig.add_hline(y=lv, line_dash=d, line_color=cc, line_width=1, row=3, col=1)
    wmx = max(float(dc['WT1'].max()), 100)+10; wmn = min(float(dc['WT1'].min()), -100)-10
    fig.add_hrect(y0=OB1, y1=wmx, fillcolor="rgba(255,23,68,0.08)", line_width=0, row=3, col=1)
    fig.add_hrect(y0=wmn, y1=OS1, fillcolor="rgba(0,191,255,0.08)", line_width=0, row=3, col=1)
    if 'Squeeze_On' in dc.columns: _hl(fig, dc['Squeeze_On'], dc.index, "rgba(255,255,0,0.05)", None, 3)

    # ═══ Row 4: Money Flow ═══
    rmfi = dc['RSI_MFI']
    fig.add_trace(go.Bar(x=dc.index, y=rmfi,
        marker_color=np.where(rmfi >= 0, '#3ee145', '#ff3d2e').tolist(),
        name="Money Flow", opacity=0.7, hovertemplate="%{y:.1f}"), row=4, col=1)
    fig.add_hline(y=0, line_dash="solid", line_color="gray", line_width=1, row=4, col=1)

    # ═══ Row 5: MACD ═══
    fig.add_trace(go.Scatter(x=dc.index, y=dc['MACD_Line'], line=dict(color='#29B6F6', width=1.5),
        name="MACD", hovertemplate="%{y:.3f}"), row=5, col=1)
    fig.add_trace(go.Scatter(x=dc.index, y=dc['MACD_Signal'], line=dict(color='#FFA726', width=1.5),
        name="Signal", hovertemplate="%{y:.3f}"), row=5, col=1)
    mh = dc['MACD_Hist']
    fig.add_trace(go.Bar(x=dc.index, y=mh,
        marker_color=np.where(mh >= 0, '#26A69A', '#EF5350').tolist(),
        name="Hist", opacity=0.7, hovertemplate="%{y:.3f}"), row=5, col=1)
    fig.add_hline(y=0, line_color="#444444", line_width=1, row=5, col=1)

    # ═══ Row 6: 🆕 BUY/SELL Judgment Score ═══
    if 'Buy_Total' in dc.columns and 'Sell_Total' in dc.columns:
        net_j = dc['Buy_Total'] - dc['Sell_Total']
        colors = np.where(net_j >= 10, '#00E676',
                  np.where(net_j >= 5, '#69F0AE',
                  np.where(net_j <= -10, '#FF1744',
                  np.where(net_j <= -5, '#FF5252', '#FFC107'))))
        fig.add_trace(go.Bar(x=dc.index, y=net_j,
            marker_color=colors.tolist(), name="Judgment NET", opacity=0.8,
            customdata=np.stack([dc['Buy_Total'].values, dc['Sell_Total'].values,
                dc.get('Trade_Judgment', pd.Series('N/A', index=dc.index)).values], axis=-1),
            hovertemplate="<b>%{customdata[2]}</b><br>BUY: %{customdata[0]:.1f}<br>SELL: %{customdata[1]:.1f}<br>NET: %{y:.1f}<extra></extra>"),
            row=6, col=1)
        for lv, cc, d in [(15,'#00E676','dash'),(-15,'#FF1744','dash'),(10,'#00E676','dot'),
                           (-10,'#FF1744','dot'),(5,'#69F0AE','dot'),(-5,'#FF5252','dot'),(0,'gray','solid')]:
            fig.add_hline(y=lv, line_dash=d, line_color=cc, line_width=1 if d == 'solid' else .8, row=6, col=1)
    else:
        conf = dc['Confluence_Score']
        fig.add_trace(go.Bar(x=dc.index, y=conf,
            marker_color=np.where(conf >= 3.5, '#00E676', np.where(conf <= -3.5, '#FF1744', '#FFC107')).tolist(),
            name="Conf Score", opacity=0.8, hovertemplate="%{y:.1f}"), row=6, col=1)

    # ═══ 레이아웃 ═══
    fig.update_layout(
        yaxis_title="Price", yaxis2_title="Vol", yaxis3_title="WT",
        yaxis4_title="MF", yaxis5_title="MACD", yaxis6_title="BUY−SELL",
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=2, r=2, t=40, b=2), height=1200, showlegend=True, hovermode="x unified",
        hoverlabel=dict(bgcolor="rgba(14,17,23,0.95)", font_size=12, font_family="Pretendard", bordercolor="#2D333B"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
            font=dict(size=9.5, color='#CCC', family='Pretendard'), bgcolor='rgba(0,0,0,0)', itemsizing='constant'))
    for i in range(1, 7):
        ya = f'yaxis{i}' if i > 1 else 'yaxis'
        fig.update_layout(**{ya: dict(gridcolor='rgba(45,51,59,0.5)', gridwidth=1,
            zerolinecolor='rgba(60,63,70,0.6)', zerolinewidth=1,
            title_font=dict(size=11, color='#777'), tickfont=dict(size=10, color='#888'))})
    fig.update_xaxes(rangeslider_visible=False)
    has_weekends = dc.index.dayofweek.isin([5, 6]).any()
    rb = [dict(bounds=["sat","mon"])] if not has_weekends else []
    fig.update_xaxes(showspikes=True, spikecolor="#667eea", spikemode="across", spikethickness=1, spikedash="dot",
        rangebreaks=rb, gridcolor='rgba(45,51,59,0.5)', gridwidth=1, tickfont=dict(size=10, color='#888'))
    fig.update_yaxes(showspikes=True, spikecolor="#667eea", spikemode="across", spikethickness=1, spikedash="dot")
    for ann in fig['layout']['annotations']: ann['font'] = dict(size=12, color='#AAA', family='Pretendard')
    return fig


# ──────────────────────────────────────────
# 메타데이터 빌드
# ──────────────────────────────────────────
def build_metadata(dc, dv, ticker):
    lat, prev = dc.iloc[-1], dc.iloc[-2] if len(dc) >= 2 else dc.iloc[-1]
    pc = lat['Close'] - prev['Close']; pp = pc / prev['Close'] * 100
    m4 = {k: float(lat[c]) for k, c in [('wt1','WT1'),('rsi','RSI'),('mfi','MFI'),('mf_area','RSI_MFI'),('stochk','StochK')]}
    h1 = bool(lat.get('_HTF1_Bull', False)); h2 = bool(lat.get('_HTF2_Bull', False))
    bias, bsc = compute_bias(m4, h1, h2); cf = float(dc['Confluence_Score'].iloc[-1])
    regime = 'STRONG BULL 🟢' if lat.get('Strong_Bull', False) else ('STRONG BEAR 🔴' if lat.get('Strong_Bear', False) else 'NEUTRAL ⚪')
    sp_list = []
    for cond, lab in [('Parabolic_Blowoff','🌡️PARA TOP'),('ST_Bear_Override','📉ST BEAR'),('Parabolic_Bottom_Raw','🧊PARA BOT')]:
        if lat.get(cond, False): sp_list.append(lab)
    if not sp_list:
        if lat.get('Buy_Shield_Overridden', False): sp_list.append('🔓BUY OFF')
        if lat.get('Sell_Shield_Overridden', False): sp_list.append('🔓SELL OFF')
    shield_str = ' + '.join(sp_list)

    # 최근 시그널 수집
    sig_checks = [(k, v['icon'], v['label'], v['dir']) for k, v in ALL_CHART_SIGNALS.items()]
    recent = []
    for ir, row in dc.tail(15).iterrows():
        ds = ir.strftime('%m/%d')
        for col, icon, lbl, side in sig_checks:
            if row.get(col, False): recent.append((icon, lbl, ds, side))

    # 🆕 판단 데이터
    jd = get_judgment_detail(lat)
    judgment_history = []
    for ir, row in dc.tail(5).iterrows():
        jh = get_judgment_detail(row)
        judgment_history.append({
            'date': ir.strftime('%m/%d'), 'judgment': jh['judgment'],
            'buy_total': jh['buy_total'], 'sell_total': jh['sell_total'],
            'combos': jh['active_combos'],
        })

    return {
        'ticker': ticker.upper(), 'price': lat['Close'], 'price_change': pc, 'price_change_pct': pp,
        'volume': lat['Volume'], 'avg_volume': dc['Volume'].rolling(20).mean().iloc[-1],
        'wt1': float(lat['WT1']), 'wt2': float(lat['WT2']), 'rsi': float(lat['RSI']), 'mfi': float(lat['MFI']),
        'stochk': float(lat['StochK']), 'stochd': float(lat['StochD']),
        'vwap_osc': float(lat['VWAP_Osc']), 'mf_area': float(lat['RSI_MFI']),
        'atr': float(lat['ATR']), 'atr_pct': float(lat['ATR'])/float(lat['Close'])*100,
        'adx': float(lat['ADX']), 'plus_di': float(lat['Plus_DI']), 'minus_di': float(lat['Minus_DI']),
        'overall_bias': bias, 'bias_score': bsc, 'confluence_score': cf,
        'recent_signals': recent, 'all_signal_stats': compute_all_stats(dv),
        'last_date': dc.index[-1].strftime('%Y-%m-%d'),
        'buy_proximity': float(lat['Buy_Proximity']), 'sell_proximity': float(lat['Sell_Proximity']),
        'squeeze_on': bool(lat.get('Squeeze_On', False)),
        'trend_regime': regime, 'shield_status': shield_str,
        'supertrend_dir': int(lat.get('ST_Direction', 0)), 'supertrend_val': float(lat.get('SuperTrend', 0)),
        'ema8': float(lat.get('EMA8', 0)), 'ema21': float(lat.get('EMA21', 0)),
        'bb_up': float(lat.get('BB_Up', 0)), 'bb_low': float(lat.get('BB_Low', 0)),
        'ma50': float(lat.get('MA50', 0)), 'ma200': float(lat.get('MA200', 0)),
        'macd_line': float(lat.get('MACD_Line', 0)), 'macd_signal': float(lat.get('MACD_Signal', 0)),
        'macd_hist': float(lat.get('MACD_Hist', 0)),
        'judgment_detail': jd, 'judgment_history': judgment_history,
    }, regime, shield_str


# ──────────────────────────────────────────
# 프롬프트 빌더
# ──────────────────────────────────────────
def build_prompt_text(dc, meta):
    lat = dc.iloc[-1]; rd = dc.tail(60)
    ps = ", ".join([f"'{d.strftime('%Y-%m-%d')}:{r['Close']:.2f}'" for d, r in rd.iterrows()])

    sl = []
    for ir, row in dc.tail(30).iterrows():
        dd = ir.strftime('%Y-%m-%d')
        for k, v in ALL_CHART_SIGNALS.items():
            if row.get(k, False): sl.append(f"{v['icon']} {v['label']} {dd}")
    st_text = "\n".join(sl) if sl else "최근 30일 내 시그널 없음"

    bp, sp = meta['buy_proximity'], meta['sell_proximity']
    prox = f"BuyProx={bp:.0f}%,SellProx={sp:.0f}%"
    if bp >= 60: prox += " ⚠️매수임박"
    if sp >= 60: prox += " ⚠️매도임박"
    sq = "SqON" if meta['squeeze_on'] else "SqOFF"
    std = f"BULL▲({meta['supertrend_val']:.2f})" if meta['supertrend_dir'] == 1 else f"BEAR▼({meta['supertrend_val']:.2f})"
    shd = f"Shield:{meta['shield_status']}" if meta['shield_status'] else "Shield:NONE"

    inds = (f"WT1={lat['WT1']:.1f},WT2={lat['WT2']:.1f},RSI={lat['RSI']:.1f},MFI={lat['MFI']:.1f},"
        f"StK={lat['StochK']:.1f},StD={lat['StochD']:.1f},VWAP={lat['VWAP_Osc']:.2f},"
        f"MF={lat['RSI_MFI']:.1f},ADX={lat['ADX']:.1f},+DI={lat['Plus_DI']:.1f},-DI={lat['Minus_DI']:.1f},"
        f"E8={lat['EMA8']:.2f},E21={lat['EMA21']:.2f},ST={std},"
        f"BB=[{meta['bb_up']:.2f}/{meta['bb_low']:.2f}],%B={lat.get('Percent_B',0):.2f},M50={meta['ma50']:.2f},M200={meta['ma200']:.2f},"
        f"Chandelier=[L:{lat.get('Chandelier_Long',0):.2f}/S:{lat.get('Chandelier_Short',0):.2f}],"
        f"MACD={meta['macd_line']:.3f}/{meta['macd_signal']:.3f} H={meta['macd_hist']:.3f},"
        f"Conf={meta['confluence_score']:.1f},Bias={meta['overall_bias']}({meta['bias_score']:.1f}),"
        f"Trend={meta['trend_regime']},{shd},{prox},{sq}")

    stats = meta.get('all_signal_stats', {})
    st_txt = ""
    if stats:
        lines = []
        for sn, sv in sorted(stats.items(), key=lambda x: x[1]['count'], reverse=True)[:15]:
            wr = sv.get('2d_winrate'); avg = sv.get('2d_avg')
            if wr is not None: lines.append(f"  {sn}:{sv['count']}회,2일승률{wr:.0f}%,평균{avg:+.1f}%")
        if lines: st_txt = "\n📌 [백테스트(2년,상위15)]\n" + "\n".join(lines)

    # 🆕 판단 데이터
    jd = meta.get('judgment_detail', {})
    j_txt = ""
    if jd:
        j_txt = f"\n\n📌 [멀티 시그널 매매 판단]\n"
        j_txt += f"  최종판단: {jd.get('judgment','NEUTRAL')}\n"
        j_txt += f"  BUY점수: {jd.get('buy_total',0):.1f} (활성 {jd.get('buy_active',0)}/6 레이어)\n"
        j_txt += f"  SELL점수: {jd.get('sell_total',0):.1f} (활성 {jd.get('sell_active',0)}/6 레이어)\n"
        bl = jd.get('buy_layers', {}); sla = jd.get('sell_layers', {})
        j_txt += f"  BUY레이어: {', '.join(f'{k}={v:.1f}' for k,v in bl.items())}\n"
        j_txt += f"  SELL레이어: {', '.join(f'{k}={v:.1f}' for k,v in sla.items())}\n"
        combos = jd.get('active_combos', [])
        j_txt += f"  🔥활성콤보: {', '.join(c['name'] for c in combos)}\n" if combos else "  활성콤보: 없음\n"
        jh = meta.get('judgment_history', [])
        if jh:
            j_txt += "  최근5일: " + " → ".join(
                f"{d['date']}:{d['judgment']}(B{d['buy_total']:.0f}/S{d['sell_total']:.0f})"
                for d in jh) + "\n"

    return f"{ps}\n\n📌 [지표 요약]\n{inds}\n\n📌 [최근 시그널]\n{st_text}{st_txt}{j_txt}"


def build_ai_prompt(ticker, phist, fundamentals):
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

1. 🚫 환각(Hallucination) 엄금: [YFinance 펀더멘탈]에 없는 데이터는 지어내지 마세요.
2. 🧮 기계적 리스크 관리 (ATR 활용): 손절가와 목표가는 반드시 **ATR** 데이터를 기반으로 산출하세요.
   - 스윙 롱 손절가 = 현재가 - (ATR * 1.5) / 1차 목표가 = 현재가 + (ATR * 2.0)
3. 🌊 추세 맞춤형 전략 (Trend Regime): STRONG BULL, STRONG BEAR, NEUTRAL 에 맞는 전략을 제시하세요.
4. 📈 데이터 활용: 백테스트 승률(Winrate), VWAP_Osc, ADX, Squeeze 상태 등을 분석의 근거로 포함하세요.
5. 🎯 멀티 시그널 판단: [멀티 시그널 매매 판단] 섹션의 7-Layer 점수, 콤보, 최종 판단을 핵심 근거로 활용하세요.

---
━━━━━━━━━━━━━
【 📥 Input Data 】
━━━━━━━━━━━━━
[티커: {ticker}]

📌 [주가 + 기술적 지표 + 시그널 + 매매 판단]
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
### 🎯 멀티 시그널 매매 판단
* 최종 판단: [STRONG BUY / BUY / WATCH / NEUTRAL / SELL / STRONG SELL]
* BUY 점수: [점수] (활성 [N]/6 레이어) — SELL 점수: [점수] (활성 [N]/6 레이어)
* 7-Layer 분해: [추세/모멘텀/캔들/볼린저/거래량/패턴 각 점수]
* 활성 콤보: [콤보명]
* 최근 5일 판단 추이: [이력]
> 🚦 판단 해석: [이 판단이 의미하는 바를 구체적으로 2~3문장]

---
### 🚦 마켓 사이퍼 B+ 시그널 분석
* WaveTrend: [WT1/WT2 값, 상태]
* Money Flow: [MF_Area 값, 방향]
* 🔥 Confluence Score: [점수, 판정]
* ⚠️ Signal Proximity: [매수/매도 임박 여부]
* 최근 시그널: [주요 시그널 요약]
> 🚦 해석: [1~2문장]

---
### 주가 및 거래량 분석
* 거래량: 평균 대비 [배수]. VWAP Oscillator: [값]
* 현재 상태: [과매수/과매도, ADX 추세 강도]
> 종합 해석: [🔵/🔴/🟠] [판단]

---
### 장중 기술적 지표
[패턴 이름]
* 상태: [설명. ATR 기반 변동]
* 지표 요약: ATR [값], ADX [값], TTM Squeeze [ON/OFF], MACD [상태]

---
### 지지선 및 저항선
* 지지선: [가격1], [가격2], [가격3]
* 저항선: [가격1], [가격2], [가격3]

---
### 파생 심리 및 공매도 현황
* 공매도 및 숏스퀴즈 가능성: [분석]
> [긍정:🔵/부정:🔴/중간:🟠] 해석

---
### 🔮 종합해석 및 시나리오
* 🔵 **긍정적 시나리오:** [조건] → [목표가]. 확률: __%
* 🟠 **베이스 시나리오:** [시나리오]. 확률: __%
* 🔴 **리스크 시나리오:** [조건] → [하락 목표가]. 확률: __%

**실전 트레이딩 전략:**
* **리스크/리워드 비율:** 1:__
* **공격적 매수 구간:** [가격대]
* **보수적 진입 시점:** [확인 매매 가격대]
* **손절(Stop-loss):** [가격]
* **분할 매도:** 1차 [가격] __%, 2차 [가격] __%
* **트레일링 스탑:** [Chandelier Exit 활용]

---
### 결론
[🔵/🔴/🟠] [2~3문장 결론]

### 주가 예측 (다음 거래일)
[🔵/🔴/🟠] 예상: [방향] · 근거: [...]
[GRADE/Score]: [최종 등급]
"""


# ──────────────────────────────────────────
# 분석 통합 로직
# ──────────────────────────────────────────
def analyze(ticker, chart_days=252, refresh=False):
    try:
        ts = int(time.time()) if refresh else None
        df = compute_and_cache(ticker, ts)
        if df is None or df.empty:
            return None, "주가 데이터 없음", None
        dv = df.dropna(subset=['WT1','WT2'])
        dc = dv.tail(chart_days).copy()
        if dc.empty:
            return None, "차트 데이터 부족", None
        meta, regime, shield = build_metadata(dc, dv, ticker)
        fig = build_chart(dc, ticker, regime, shield)
        return fig, build_prompt_text(dc, meta), meta
    except Exception as e:
        import traceback
        err_detail = traceback.format_exc()
        print(f"[CipherX ERROR] {ticker}: {err_detail}")
        return None, f"로딩 실패: {type(e).__name__}: {e}", None

# ──────────────────────────────────────────
# 스피도미터 게이지
# ──────────────────────────────────────────
def build_speedometer_gauges(meta):
    conf_score = meta.get('confluence_score', 0); bias_score = meta.get('bias_score', 0)
    bias_label = meta.get('overall_bias', 'NEUTRAL')
    if conf_score >= 6.5: cc = "#34D399"
    elif conf_score >= 3.5: cc = "#6EE7B7"
    elif conf_score <= -6.5: cc = "#F87171"
    elif conf_score <= -3.5: cc = "#FCA5A5"
    else: cc = "#FCD34D"
    bc_map = {'STRONG BUY':'#34D399','BUY':'#6EE7B7','STRONG SELL':'#F87171','SELL':'#FCA5A5','NEUTRAL':'#FCD34D'}
    bc = bc_map.get(bias_label, '#FCD34D')

    fig = make_subplots(rows=1, cols=2, specs=[[{"type":"indicator"},{"type":"indicator"}]], horizontal_spacing=0.08)
    fig.add_trace(go.Indicator(mode="gauge+number", value=conf_score,
        number=dict(font=dict(size=30, color="#F8FAFC", family="Pretendard"), suffix=""),
        title=dict(text="<b>🔥 Confluence Score</b>", font=dict(size=13, color="#94A3B8")),
        gauge=dict(axis=dict(range=[-10,10], tickwidth=2, tickcolor="#334155", dtick=2.5,
                   tickfont=dict(size=10, color="#64748B")),
            bar=dict(color=cc, thickness=0.3), bgcolor="rgba(15,19,32,0.9)",
            borderwidth=1, bordercolor="#1E293B",
            steps=[dict(range=[-10,-6.5],color="rgba(239,68,68,0.15)"),
                dict(range=[-6.5,-3.5],color="rgba(239,68,68,0.08)"),
                dict(range=[-3.5,3.5],color="rgba(245,158,11,0.06)"),
                dict(range=[3.5,6.5],color="rgba(16,185,129,0.08)"),
                dict(range=[6.5,10],color="rgba(16,185,129,0.15)")],
            threshold=dict(line=dict(color="#F8FAFC", width=3), thickness=0.8, value=conf_score))), row=1, col=1)
    fig.add_trace(go.Indicator(mode="gauge+number", value=bias_score,
        number=dict(font=dict(size=30, color="#F8FAFC", family="Pretendard"),
                    suffix=f"  {bias_label}", valueformat=".1f"),
        title=dict(text="<b>🧭 Overall Bias</b>", font=dict(size=13, color="#94A3B8")),
        gauge=dict(axis=dict(range=[-13,13], tickwidth=2, tickcolor="#334155", dtick=3.25,
                   tickfont=dict(size=10, color="#64748B")),
            bar=dict(color=bc, thickness=0.3), bgcolor="rgba(15,19,32,0.9)",
            borderwidth=1, bordercolor="#1E293B",
            steps=[dict(range=[-13,-9],color="rgba(239,68,68,0.18)"),
                dict(range=[-9,-3.5],color="rgba(239,68,68,0.08)"),
                dict(range=[-3.5,3.5],color="rgba(245,158,11,0.06)"),
                dict(range=[3.5,9],color="rgba(16,185,129,0.08)"),
                dict(range=[9,13],color="rgba(16,185,129,0.18)")],
            threshold=dict(line=dict(color="#F8FAFC", width=3), thickness=0.8, value=bias_score))), row=1, col=2)
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=230, margin=dict(l=20, r=20, t=50, b=10), font=dict(family="Pretendard"))
    return fig
# ══════════════════════════════════════════════════════════════
#  CipherX V11.0 — PART 3/3
#  UI 렌더 함수 + 사이드바 + 챗 인터페이스
# ══════════════════════════════════════════════════════════════

# ──────────────────────────────────────────
# 🆕 매매 판단 UI
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

    # 카드 스타일 결정
    if 'BUY' in judgment: card_cls = 'judgment-card-buy'
    elif 'SELL' in judgment: card_cls = 'judgment-card-sell'
    else: card_cls = 'judgment-card-neutral'

    j_label, j_color, _ = JUDGMENT_CONFIG.get(judgment, ('⚪ NEUTRAL','#64748B',''))
    net_color = '#34D399' if net > 0 else ('#F87171' if net < 0 else '#FCD34D')

    st.markdown(f"""
    <div class="judgment-card {card_cls}">
        <p style="font-size:2rem;font-weight:800;color:{j_color};margin:0;
           text-shadow:0 0 30px {j_color}40">{j_label}</p>
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

    # ── 활성 콤보 ──
    combos = jd.get('active_combos', [])
    st.markdown("#### 🔥 활성 매매 콤보")
    if combos:
        for cb in combos:
            cc = 'combo-buy' if cb['dir'] == 'buy' else 'combo-sell'
            dot_c = '#34D399' if cb['dir'] == 'buy' else '#F87171'
            side_label = 'BUY' if cb['dir'] == 'buy' else 'SELL'
            st.markdown(f"""<div class="combo-card {cc}">
                <div style="display:flex;align-items:center;gap:10px">
                    <span style="color:{dot_c};font-size:1.2rem">●</span>
                    <span style="color:#E8ECF1;font-weight:700;font-size:.95rem">{cb['name']}</span>
                </div>
                <span style="color:{dot_c};font-size:.75rem;font-weight:600;padding:3px 10px;
                    border-radius:6px;background:rgba(255,255,255,0.04)">{side_label}</span>
            </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""<div class="combo-card" style="background:rgba(245,158,11,.04);
            border:1px solid rgba(245,158,11,.15);border-left:3px solid #F59E0B;justify-content:center">
            <span style="color:#FCD34D;font-weight:600;font-size:.9rem">
                ⏸️ 활성 콤보 없음 — 관망 구간</span></div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── 7-Layer 점수 ──
    st.markdown("#### 📊 7-Layer 스코어 분석")
    col_b, col_s = st.columns(2)
    with col_b:
        st.markdown("<p style='color:#34D399;font-weight:700;font-size:.85rem;margin-bottom:8px;"
                    "text-transform:uppercase;letter-spacing:1px'>▲ BUY LAYERS</p>", unsafe_allow_html=True)
        _render_layer_bars(jd['buy_layers'], 'buy', jd['buy_active'])
    with col_s:
        st.markdown("<p style='color:#F87171;font-weight:700;font-size:.85rem;margin-bottom:8px;"
                    "text-transform:uppercase;letter-spacing:1px'>▼ SELL LAYERS</p>", unsafe_allow_html=True)
        _render_layer_bars(jd['sell_layers'], 'sell', jd['sell_active'])

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── 판단 기준 ──
    with st.expander("📐 판단 기준 상세", expanded=False):
        rows_html = ""
        criteria = [
            ('STRONG_BUY','🟢🟢🟢 STRONG BUY','BUY ≥ 17 + 4층↑ + BUY > SELL×1.5'),
            ('BUY','🟢🟢 BUY','BUY ≥ 11 + 3층↑ + BUY > SELL'),
            ('WATCH_BUY','🟡🟢 WATCH BUY','BUY ≥ 6 + 2층↑'),
            ('NEUTRAL','⚪ NEUTRAL','기준 미달'),
            ('MIXED','🟠 MIXED','BUY ≥ 9 & SELL ≥ 9'),
            ('WATCH_SELL','🟡🔴 WATCH SELL','SELL ≥ 6 + 2층↑'),
            ('SELL','🔴🔴 SELL','SELL ≥ 11 + 3층↑ + SELL > BUY'),
            ('STRONG_SELL','🔴🔴🔴 STRONG SELL','SELL ≥ 17 + 4층↑ + SELL > BUY×1.5'),
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

    # ── 최근 5일 이력 ──
    jh = meta.get('judgment_history', [])
    if jh:
        st.markdown("#### 📅 최근 5일 판단 추이")
        for day in reversed(jh):
            j_cfg_d = JUDGMENT_CONFIG.get(day['judgment'], ('⚪','#64748B',''))
            combo_str = ', '.join([c['name'] for c in day['combos']]) if day['combos'] else '—'
            # 미니 바
            b_pct = min(day['buy_total'] / 25 * 100, 100)
            s_pct = min(day['sell_total'] / 25 * 100, 100)
            st.markdown(f"""<div class="history-row">
                <span style="color:#64748B;font-size:.85rem;width:45px;font-weight:600">{day['date']}</span>
                <span style="color:{j_cfg_d[1]};font-weight:700;font-size:.8rem;width:150px">{j_cfg_d[0]}</span>
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
                <span style="color:#475569;font-size:.7rem;width:140px;text-align:right;overflow:hidden;
                    text-overflow:ellipsis;white-space:nowrap">{combo_str}</span>
            </div>""", unsafe_allow_html=True)


def _render_layer_bars(layers, side, active_count):
    icons = {'Trend':'📈','Momentum':'🔥','Candle':'🕯️','BB':'📊',
             'Volume':'📦','MF':'💰','Pattern':'⭐'}  
    max_per = 9.0
    fill_cls = 'layer-bar-fill-buy' if side == 'buy' else 'layer-bar-fill-sell'
    score_color = '#34D399' if side == 'buy' else '#F87171'
    total = sum(layers.values())

    for name, score in layers.items():
        icon = icons.get(name, '•')
        pct = min(score / max_per * 100, 100)
        opacity = '1' if score > 0 else '0.2'
        st.markdown(f"""<div class="layer-bar-wrap">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px">
                <span style="color:#94A3B8;font-size:.8rem;font-weight:500;opacity:{opacity}">{icon} {name}</span>
                <span style="color:{score_color};font-weight:700;font-size:.8rem;opacity:{opacity}">
                    {score:.1f}{'  ✓' if score > 0 else ''}</span>
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
        <span style="color:#475569;font-size:.8rem">/6</span>
    </div>""", unsafe_allow_html=True)


# ──────────────────────────────────────────
# 기존 UI 렌더 함수들
# ──────────────────────────────────────────
_IT = {'wt1': [(-53,'극과매도'),(-20,'과매도'),(20,'중립'),(53,'과매수'),(999,'극과매수')],
       'rsi': [(30,'과매도'),(45,'약세'),(55,'중립'),(70,'강세'),(999,'과매수')],
       'mfi': [(30,'과매도'),(45,'약세'),(55,'중립'),(70,'강세'),(999,'과매수')],
       'stochk': [(20,'바닥'),(80,''),(999,'천장')]}

def _il(n, v):
    for t, l in _IT.get(n, []):
        if v <= t: return l
    return ''


def render_price_header(m):
    chg = m['price_change']; cp = m['price_change_pct']
    cc = 'price-change-up' if chg >= 0 else 'price-change-down'
    ci = '▲' if chg >= 0 else '▼'
    vr = m['volume'] / m['avg_volume'] if m['avg_volume'] else 0
    cv = m.get('confluence_score', 0); sd = m.get('supertrend_dir', 0)
    sh = m.get('shield_status', ''); mh_val = m.get('macd_hist', 0)

    jd = m.get('judgment_detail', {})
    j_short = jd.get('judgment', 'NEUTRAL') if jd else 'N/A'
    j_color_map = {'STRONG_BUY':'ind-bullish','BUY':'ind-bullish','WATCH_BUY':'ind-neutral',
                   'STRONG_SELL':'ind-bearish','SELL':'ind-bearish','WATCH_SELL':'ind-neutral',
                   'MIXED':'ind-neutral','NEUTRAL':'ind-neutral'}
    j_cls = j_color_map.get(j_short, 'ind-neutral')

    specs = [
        (j_cls, f"📍 {j_short}"),
        (_cls(m['wt1'],-20,20), f"WT {m['wt1']:.0f} {_il('wt1',m['wt1'])}"),
        (_cls(m['rsi'],40,60), f"RSI {m['rsi']:.0f}"),
        (_cls(m['mfi'],40,60), f"MFI {m['mfi']:.0f}"),
        ('ind-bullish' if m['mf_area']<0 else ('ind-bearish' if m['mf_area']>0 else 'ind-neutral'), f"MF {m['mf_area']:.1f}"),
        ('ind-bullish' if vr>1.5 else 'ind-neutral', f"Vol {vr:.1f}x"),
        ('ind-bullish' if m['adx']>25 else 'ind-neutral', f"ADX {m['adx']:.0f}"),
        (_cls(m['stochk'],30,70), f"StK {m['stochk']:.0f}"),
        ('ind-bullish' if cv>=3.5 else ('ind-bearish' if cv<=-3.5 else 'ind-neutral'), f"Conf {cv:.1f}"),
        ('ind-bullish' if sd==1 else 'ind-bearish', f"ST {'▲' if sd==1 else '▼'}"),
        ('ind-bullish' if mh_val>0 else ('ind-bearish' if mh_val<0 else 'ind-neutral'), f"MACD {mh_val:+.2f}"),
    ]
    ih = "".join([f"<span class='indicator-mini {c}'>{l}</span>" for c, l in specs])
    if sh: ih += f"<span class='indicator-mini ind-bearish' style='font-weight:700'>🔓 {sh}</span>"
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

def render_speedometer(m):
    gauge_fig = build_speedometer_gauges(m)
    st.plotly_chart(gauge_fig, use_container_width=True, theme=None, config={'displayModeBar': False})
    bias = m['overall_bias']; sc = m.get('bias_score', 0)
    styles = {'STRONG BUY':('rgba(16,185,129,.1)','#34D399','🟢🟢'),
        'BUY':('rgba(16,185,129,.06)','#34D399','🟢'),
        'STRONG SELL':('rgba(239,68,68,.1)','#F87171','🔴🔴'),
        'SELL':('rgba(239,68,68,.06)','#F87171','🔴')}
    bg, clr, ico = styles.get(bias, ('rgba(245,158,11,.06)','#FCD34D','🟠'))
    bp = m.get('buy_proximity', 0); sp = m.get('sell_proximity', 0)
    prox_txt = ""
    if bp >= 50: prox_txt = f"<span style='color:#34D399;font-weight:600'>매수 임박 {bp:.0f}%</span>"
    elif sp >= 50: prox_txt = f"<span style='color:#F87171;font-weight:600'>매도 임박 {sp:.0f}%</span>"
    sq_txt = " · <span style='color:#FCD34D;font-weight:700'>💥 Squeeze ON</span>" if m.get('squeeze_on') else ""
    st.markdown(f"""<div style="background:{bg};border-radius:12px;padding:12px 18px;
        text-align:center;margin:4px 0 14px 0;border:1px solid rgba(255,255,255,0.06)">
        <span style="font-size:1.05rem;font-weight:700;color:{clr}">{ico} 종합 판정: {bias} ({sc:.1f})</span>
        {f' · {prox_txt}' if prox_txt else ''}{sq_txt}</div>""", unsafe_allow_html=True)

def render_alerts(m):
    alerts = []
    bp, sp = m.get('buy_proximity', 0), m.get('sell_proximity', 0)
    if bp >= 70: alerts.append(('🟢⚡ 매수 매우 임박!','#34D399','rgba(16,185,129,.08)',bp))
    elif bp >= 50: alerts.append(('🟢 매수 접근 중','#6EE7B7','rgba(16,185,129,.05)',bp))
    if sp >= 70: alerts.append(('🔴⚡ 매도 매우 임박!','#F87171','rgba(239,68,68,.08)',sp))
    elif sp >= 50: alerts.append(('🔴 매도 접근 중','#FCA5A5','rgba(239,68,68,.05)',sp))
    if m.get('squeeze_on'): alerts.append(('💥 TTM Squeeze ON — 돌파 임박','#FCD34D','rgba(245,158,11,.06)',80))

    jd = m.get('judgment_detail', {})
    j = jd.get('judgment', 'NEUTRAL')
    if j == 'STRONG_BUY': alerts.insert(0, ('🟢🟢🟢 STRONG BUY 판단 활성!','#34D399','rgba(16,185,129,.1)',95))
    elif j == 'BUY': alerts.insert(0, ('🟢🟢 BUY 판단 활성','#34D399','rgba(16,185,129,.06)',75))
    elif j == 'STRONG_SELL': alerts.insert(0, ('🔴🔴🔴 STRONG SELL 판단 활성!','#F87171','rgba(239,68,68,.1)',95))
    elif j == 'SELL': alerts.insert(0, ('🔴🔴 SELL 판단 활성','#F87171','rgba(239,68,68,.06)',75))

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
            <p style="margin:0;color:#FCD34D;font-weight:600">⏸️ 최근 15일 내 포착된 시그널 없음</p></div>""", unsafe_allow_html=True)
        return
    dg = OrderedDict()
    for icon, lbl, ds, side in sigs: dg.setdefault(ds, []).append((icon, lbl, side))
    alls = m.get('all_signal_stats', {})
    for ds in reversed(dg):
        group = dg[ds]
        bc_cnt = sum(1 for _, _, s in group if s == 'buy')
        sc_cnt = sum(1 for _, _, s in group if s == 'sell')
        ct = 'signal-card-buy' if bc_cnt > sc_cnt else ('signal-card-sell' if sc_cnt > bc_cnt else 'signal-card-neutral')
        parts = []
        for i, l, s in group:
            cn = "ind-bullish" if s == "buy" else "ind-bearish"
            sh = ""
            for sn, sv in alls.items():
                if ALL_CHART_SIGNALS.get(sn, {}).get('label') == l:
                    wr = sv.get('2d_winrate')
                    if wr is not None: sh = f" {wr:.0f}%"
                    break
            parts.append(f'<span class="indicator-mini {cn}">{i} {l}{sh}</span>')
        date_color = '#34D399' if bc_cnt > sc_cnt else ('#F87171' if sc_cnt > bc_cnt else '#FCD34D')
        st.markdown(f"""<div class="signal-card {ct}">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                <span style="font-weight:700;font-size:.9rem;color:#E8ECF1">📅 {ds}</span>
                <span style="color:{date_color};font-size:.75rem;font-weight:600;
                    padding:2px 8px;border-radius:6px;background:rgba(255,255,255,0.04)">{len(group)}개 시그널</span></div>
            <div style="display:flex;gap:5px;flex-wrap:wrap">{" ".join(parts)}</div></div>""", unsafe_allow_html=True)

def render_stats(m):
    with st.expander("📊 시그널 백테스트 (2년 데이터 기반)", expanded=True):
        alls = m.get('all_signal_stats', {})
        if not alls: st.caption("충분한 통계 데이터가 없습니다."); return
        st.markdown("<p style='color:#64748B;font-size:.8rem;margin-bottom:16px'>진입: 시그널 다음날 시가 · 청산: 2일 후 종가</p>", unsafe_allow_html=True)

        def _side(title, data, is_sell=False):
            st.markdown(f"<p style='color:{'#F87171' if is_sell else '#34D399'};font-weight:700;font-size:.85rem;"
                        f"text-transform:uppercase;letter-spacing:1px;margin-bottom:10px'>{title}</p>", unsafe_allow_html=True)
            for sn, sv in sorted(data.items(), key=lambda x: x[1]['count'], reverse=True):
                wr = sv.get('2d_winrate'); av = sv.get('2d_avg')
                if wr is None: continue
                kor_label = ALL_CHART_SIGNALS.get(sn, {}).get('kor', sn)
                ic = ALL_CHART_SIGNALS.get(sn, {}).get('icon', '')

                # 승률 색상
                if wr >= 60: wr_c = '#34D399'
                elif wr >= 50: wr_c = '#6EE7B7'
                elif wr >= 40: wr_c = '#FCD34D'
                else: wr_c = '#F87171'

                # 수익률 색상
                if is_sell: av_c = '#34D399' if av < 0 else '#F87171'
                else: av_c = '#34D399' if av > 0 else '#F87171'

                wr_bar = min(wr, 100)
                st.markdown(f"""<div style="padding:8px 12px;margin:4px 0;border-radius:8px;
                    background:rgba(255,255,255,0.015);border:1px solid rgba(255,255,255,0.03)">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
                        <span style="color:#CBD5E1;font-weight:600;font-size:.85rem">{ic} {kor_label}
                            <span style="color:#475569;font-size:.75rem;font-weight:400">({sv['count']}회)</span></span>
                        <span style="color:{av_c};font-weight:700;font-size:.85rem">{av:+.1f}%</span>
                    </div>
                    <div style="display:flex;align-items:center;gap:8px">
                        <div style="flex:1;height:4px;background:#151921;border-radius:2px;overflow:hidden">
                            <div style="width:{wr_bar}%;height:4px;background:{wr_c};border-radius:2px"></div></div>
                        <span style="color:{wr_c};font-size:.75rem;font-weight:700;width:38px;text-align:right">{wr:.0f}%</span>
                    </div>
                </div>""", unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1: _side("▲ BUY 전략 (롱)", {k: v for k, v in alls.items() if v['direction'] == 'buy'}, is_sell=False)
        with c2: _side("▼ SELL 전략 (숏)", {k: v for k, v in alls.items() if v['direction'] == 'sell'}, is_sell=True)


# ──────────────────────────────────────────
# 메인 분석 렌더
# ──────────────────────────────────────────
def render_analysis(msg):
    m, fig = msg.get('meta'), msg.get('fig')
    if m:
        render_price_header(m)
        render_speedometer(m)
        render_alerts(m)
    if m or fig:
        t0, t1, t2, t3, t4 = st.tabs([
            "🎯 매매 판단",
            "📊 차트",
            "📈 백테스트",
            "🔔 시그널 이력",
            "🏢 기업 상세"
        ])
        with t0:
            if m: render_judgment(m)
        with t1:
            plotly_config = {'displaylogo': False,
                'modeBarButtonsToRemove': ['lasso2d','select2d','hoverCompareCartesian','hoverClosestCartesian']}
            if fig: st.plotly_chart(fig, use_container_width=True, theme=None, config=plotly_config)
        with t2:
            if m: render_stats(m)
        with t3:
            if m: render_signals(m)
        with t4:
            if m: render_company_details(m['ticker'])


# ──────────────────────────────────────────
# 사이드바
# ──────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🚦 CipherX")
    st.markdown("<p style='color:#888;font-size:.8rem'>AI 퀀트 주가 분석 · Judgment-First v11.0</p>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("### 📅 차트 기간")
    chart_period = st.radio("표시 기간", ['3개월','6개월','1년','2년'], index=0, horizontal=True, key="period")
    chart_days = {'3개월':63, '6개월':126, '1년':252, '2년':504}[chart_period]
    st.markdown("---")

    with st.expander("🎛️ 차트 표시 설정", expanded=False):
        st.markdown("**표시할 판단 등급**")
        _show_strong = st.checkbox("🟢🔴 STRONG (강력 매수/매도)", value=True, key="j_strong")
        _show_normal = st.checkbox("🟢🔴 BUY / SELL (일반)", value=True, key="j_normal")
        _show_watch = st.checkbox("🟡 WATCH (관망)", value=False, key="j_watch")
        _show_mixed = st.checkbox("🟠 MIXED (혼조)", value=False, key="j_mixed")

        enabled_judgments = set()
        if _show_strong: enabled_judgments |= {'STRONG_BUY', 'STRONG_SELL'}
        if _show_normal: enabled_judgments |= {'BUY', 'SELL'}
        if _show_watch: enabled_judgments |= {'WATCH_BUY', 'WATCH_SELL'}
        if _show_mixed: enabled_judgments.add('MIXED')
        st.session_state['enabled_judgments'] = enabled_judgments
        st.caption(f"차트 표시: {len(enabled_judgments)}개 등급")

        # 시그널은 백그라운드 전체 활성
        st.session_state['enabled_signals'] = set(ALL_CHART_SIGNALS.keys())

    st.markdown("---")
    if st.button("🗑️ 대화 내역 지우기", use_container_width=True, type="secondary"):
        for key in ['messages','pending_ai_ticker','pending_ai_prompt','last_ticker']:
            st.session_state[key] = [{"role":"assistant","type":"text",
                "content":"안녕하세요! 🚦 **CipherX v11** 입니다.\n\n분석할 **티커명**을 입력하세요."}] if key == 'messages' else None
        st.rerun()


# ──────────────────────────────────────────
# 세션 관리
# ──────────────────────────────────────────
if 'messages' not in st.session_state:
    st.session_state.messages = [{"role":"assistant","type":"text",
        "content":"안녕하세요! 🚦 **CipherX v11** 입니다.\n\n분석할 **티커명**을 입력하세요. 채팅처럼 이어서 여러 종목을 검색할 수 있습니다."}]
for key in ['pending_ai_ticker','pending_ai_prompt','last_ticker']:
    if key not in st.session_state: st.session_state[key] = None
if 'enabled_signals' not in st.session_state:
    st.session_state['enabled_signals'] = set(ALL_CHART_SIGNALS.keys())
if 'enabled_judgments' not in st.session_state:
    st.session_state['enabled_judgments'] = {'STRONG_BUY','BUY','SELL','STRONG_SELL'}


# ──────────────────────────────────────────
# 챗 인터페이스
# ──────────────────────────────────────────
st.markdown("<h2 style='text-align:center;color:#fff;margin-bottom:20px'>🚦 CipherX</h2>", unsafe_allow_html=True)

if not st.session_state.last_ticker:
    st.markdown("<p style='text-align:center;color:#888;font-size:0.9rem;'>🔥 추천 주식 빠르게 분석해보기</p>", unsafe_allow_html=True)
    cols = st.columns(4)
    quick_tickers = ["NVDA","TSLA","AAPL","QQQ"]
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
                    st_copy_to_clipboard(msg["prompt"], before_copy_label="📋 복사", after_copy_label="✅ 복사됨!")
        elif msg.get("type") == "report":
            with st.expander(f"📊 {msg.get('ticker','')} AI 퀀트 리포트", expanded=True):
                st.markdown(msg["content"])
            st.download_button("📥 마크다운 파일 다운로드", key=f"dl_{i}_{msg.get('ticker','RPT')}",
                data=msg["content"].encode('utf-8'),
                file_name=f"{msg.get('ticker','RPT').upper()}_Quant_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
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
            model = genai.GenerativeModel('gemini-2.5-flash')
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
                "role":"assistant","type":"report",
                "ticker":tp.upper(),"content":full_report})
            st.session_state.pending_ai_ticker = None
            st.session_state.pending_ai_prompt = None
            st.rerun()
        except Exception as e:
            pb.empty()
            st.error(f"AI 오류: {e}")


# ──────────────────────────────────────────
# 티커 처리
# ──────────────────────────────────────────
def process_ticker(tv, refresh=False):
    tv = tv.strip().upper()
    st.session_state.pending_ai_ticker = None
    st.session_state.pending_ai_prompt = None

    if not _valid_fmt(tv):
        st.toast(f"⚠️ **{tv}** — 올바른 티커 형식이 아닙니다.", icon="🚨")
        return
    if not validate_ticker(tv):
        st.toast(f"⚠️ **{tv}** — Yahoo Finance에서 데이터를 찾을 수 없습니다.", icon="🔍")
        return

    st.session_state.messages.append({"role":"user","type":"text","content":tv})
    st.session_state.last_ticker = tv

    with st.chat_message("assistant", avatar="✨"):
        with st.status(f"🌐 {tv} 퀀트 파이프라인 가동 중...", expanded=True) as status:
            st.write("📡 YFinance 펀더멘탈 및 숏(공매도) 데이터 조회 중...")
            fundamentals = fetch_fundamentals(tv)

            st.write("📊 기술적 데이터 계산 및 시그널 엔진 검증 중...")
            st.write("🎯 7-Layer 매매 판단 엔진 가동 중...")
            fig, phist, meta = analyze(tv, chart_days, refresh)

            if fig:
                prompt = build_ai_prompt(tv, phist, fundamentals)
                status.update(label=f"✅ {tv} 퀀트 분석 완료!", state="complete", expanded=False)
            else:
                status.update(label=f"⚠️ {tv} 데이터 처리 실패", state="error", expanded=False)

        if fig:
            st.session_state.messages.append({"role":"assistant","type":"analysis","ticker":tv,
                "content":f"✅ **{tv}** 분석이 완료되었습니다.", "fig":fig,"meta":meta,"prompt":prompt})
            st.session_state.pending_ai_ticker = tv
            st.session_state.pending_ai_prompt = prompt
            st.rerun()
        else:
            # phist에 실제 에러 메시지가 들어있음
            err_msg = phist if phist else "데이터 부족"
            st.session_state.messages.append({"role":"assistant","type":"text",
                "content":f"⚠️ **{tv}** 분석 실패: {err_msg}"})
            st.rerun()


# ──────────────────────────────────────────
# 퀵 티커 / 버튼 / 입력
# ──────────────────────────────────────────
if st.session_state.get('quick_ticker'):
    qt = st.session_state.pop('quick_ticker')
    process_ticker(qt)

if st.session_state.last_ticker:
    lt = st.session_state.last_ticker
    c1, c2 = st.columns([3, 1])
    with c1:
        if st.session_state.pending_ai_ticker and st.session_state.pending_ai_prompt:
            if st.button(f"🚀 {st.session_state.pending_ai_ticker.upper()} AI 심층 퀀트 분석 시작",
                         type="primary", use_container_width=True):
                _run_ai()
    with c2:
        if st.button(f"🔄 {lt} 새로고침", type="secondary", use_container_width=True, key="re"):
            process_ticker(lt, refresh=True)
elif st.session_state.pending_ai_ticker and st.session_state.pending_ai_prompt:
    if st.button(f"🚀 {st.session_state.pending_ai_ticker.upper()} AI 심층 퀀트 분석 시작",
                 type="primary", use_container_width=True):
        _run_ai()

if ticker_input := st.chat_input("미국 주식 티커를 입력하세요 (예: TSLA, AAPL, QQQ)"):
    process_ticker(ticker_input)