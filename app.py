# ══════════════════════════════════════════════════════════════
#  CipherX V12.2 — Regime-Aware Judgment Architecture
#  FULL INTEGRATED CODE
#
#  V12.1→V12.2 변경사항:
#    [핵심] 5단계 시장 국면 인식 (Regime Detector)
#    [핵심] 매수/매도 분리 Adaptive Weighting
#    [핵심] Momentum 레이어 국면별 해석
#    [핵심] Proximity 국면별 할인
#    [핵심] Bias 추세 맥락 반영
#    [차트] Tier A/B/C 시그널 필터링 + 리치 호버
#    [시그널] 캔들 거래량 필터, Engulfing 추세 맥락
#    [시그널] VP VAH/VAL, 7일 연속, NR7/3일 제거
#    [엔진] TR 1회 계산, Time Decay, MTF 보정
#    [엔진] 다차원 Confidence
# ══════════════════════════════════════════════════════════════

import streamlit as st
import google.generativeai as genai
import time, re, math
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
from scipy.signal import find_peaks
from concurrent.futures import ThreadPoolExecutor, as_completed

st.set_page_config(page_title="CipherX V12.2", page_icon="📈", layout="centered", initial_sidebar_state="collapsed")

# ──────────────────────────────────────────
# CSS (드롭다운 수정 포함)
# ──────────────────────────────────────────
def inject_css():
    st.markdown("""<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
html,body,[class*="css"]{font-family:'Pretendard','Noto Sans KR',sans-serif!important}
.stApp{background-color:#0B0E14}
p,div[data-testid="stMarkdownContainer"] p,div[data-testid="stChatMessageContent"] p,li{color:#E8ECF1!important}
h1{color:#FFFFFF!important;font-weight:800!important}
h2{color:#FFFFFF!important;font-weight:700!important}
h3{color:#F0F4F8!important;font-weight:700!important}
h4{color:#CBD5E1!important;font-weight:600!important;font-size:1rem!important;margin-top:1.5rem!important;margin-bottom:0.8rem!important;padding-bottom:6px;border-bottom:1px solid rgba(255,255,255,0.06)}
div[data-testid="stCodeBlock"],pre,code{background-color:#151921!important;color:#E2E8F0!important;border:1px solid #1E2530!important;border-radius:10px!important}
div[data-testid="stChatMessage"]:nth-child(even){background-color:#10141C;border-radius:14px;padding:8px 18px;border:1px solid rgba(255,255,255,0.03)}
.block-container{padding-top:1rem!important;max-width:960px}
@media(max-width:768px){.block-container{padding-left:.5rem!important;padding-right:.5rem!important}.price-big{font-size:1.6rem!important}}
div.stButton>button[kind="primary"]{background:linear-gradient(135deg,#6366F1 0%,#8B5CF6 50%,#A78BFA 100%)!important;color:white!important;border:none!important;border-radius:12px!important;padding:.65rem 1.5rem!important;font-weight:700!important;font-size:1rem!important;width:100%;box-shadow:0 4px 14px rgba(99,102,241,.3)!important}
div.stButton>button[kind="secondary"]{background-color:#12161F!important;color:#C4CDD8!important;border:1px solid #2A3040!important;border-radius:12px!important;font-weight:600!important;width:100%}
.streamlit-expanderHeader{background-color:#10141C!important;border-radius:12px!important;font-weight:700!important;padding:12px 16px!important}
div[data-testid="stExpander"]{border:1px solid #1C2233!important;border-radius:12px!important;background-color:#0D1017;overflow:hidden}
header{background-color:transparent!important}
section[data-testid="stSidebar"]{background-color:#080A10;border-right:1px solid #151921}
.signal-card{border-radius:14px;padding:14px 18px;margin:8px 0;border:1px solid rgba(255,255,255,0.06)}
.signal-card-buy{background:linear-gradient(135deg,rgba(0,230,118,.06),rgba(16,185,129,.03));border-left:4px solid #10B981}
.signal-card-sell{background:linear-gradient(135deg,rgba(239,68,68,.06),rgba(220,38,38,.03));border-left:4px solid #EF4444}
.signal-card-neutral{background:linear-gradient(135deg,rgba(245,158,11,.06),rgba(217,119,6,.03));border-left:4px solid #F59E0B}
.price-header{background:linear-gradient(160deg,#0F1320,#141926,#111827);border:1px solid #1C2233;border-radius:16px;padding:20px 24px;margin-bottom:18px;box-shadow:0 4px 20px rgba(0,0,0,0.3)}
.price-big{font-size:2.2rem;font-weight:800;margin:0}
.price-change-up{color:#34D399!important}
.price-change-down{color:#F87171!important}
.price-label{color:#64748B!important;font-size:.8rem;margin:0;font-weight:500;text-transform:uppercase;letter-spacing:0.5px}
.indicator-mini{display:inline-block;padding:5px 11px;margin:3px;border-radius:8px;font-size:.78rem;font-weight:600;border:1px solid rgba(255,255,255,0.04)}
.ind-bullish{background:rgba(16,185,129,.12);color:#6EE7B7;border-color:rgba(16,185,129,.2)}
.ind-bearish{background:rgba(239,68,68,.12);color:#FCA5A5;border-color:rgba(239,68,68,.2)}
.ind-neutral{background:rgba(245,158,11,.10);color:#FCD34D;border-color:rgba(245,158,11,.15)}
div[data-testid="stTabs"] button{color:#64748B!important;font-weight:700!important;font-size:.9rem!important;border-bottom:3px solid transparent!important}
div[data-testid="stTabs"] button[aria-selected="true"]{color:#A5B4FC!important;border-bottom-color:#6366F1!important}
.judgment-card{border-radius:16px;padding:24px 28px;margin-bottom:20px;text-align:center;position:relative;overflow:hidden}
.judgment-card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px}
.judgment-card-buy{background:linear-gradient(160deg,#052E16,#0D1B2A);border:1px solid rgba(16,185,129,.25)}
.judgment-card-buy::before{background:linear-gradient(90deg,#10B981,#34D399)}
.judgment-card-sell{background:linear-gradient(160deg,#2A0E0E,#1B0D1B);border:1px solid rgba(239,68,68,.25)}
.judgment-card-sell::before{background:linear-gradient(90deg,#EF4444,#F87171)}
.judgment-card-neutral{background:linear-gradient(160deg,#1A1608,#1B1A0D);border:1px solid rgba(245,158,11,.2)}
.judgment-card-neutral::before{background:linear-gradient(90deg,#F59E0B,#FCD34D)}
.combo-card{border-radius:12px;padding:12px 16px;margin:6px 0;display:flex;align-items:center;justify-content:space-between;border:1px solid rgba(255,255,255,0.06)}
.combo-buy{background:linear-gradient(135deg,rgba(16,185,129,.08),rgba(6,78,59,.05));border-left:3px solid #10B981}
.combo-sell{background:linear-gradient(135deg,rgba(239,68,68,.08),rgba(127,29,29,.05));border-left:3px solid #EF4444}
.layer-bar-wrap{padding:4px 0}
.layer-bar-bg{background:#151921;border-radius:6px;height:10px;overflow:hidden;border:1px solid rgba(255,255,255,0.03)}
.layer-bar-fill{height:10px;border-radius:6px}
.layer-bar-fill-buy{background:linear-gradient(90deg,#059669,#34D399)}
.layer-bar-fill-sell{background:linear-gradient(90deg,#DC2626,#F87171)}
.alert-bar{border-radius:10px;padding:10px 16px;margin:5px 0;border:1px solid rgba(255,255,255,0.06)}
.alert-bar-progress{background:#151921;border-radius:4px;height:5px;margin-top:8px;overflow:hidden}
.alert-bar-fill{height:5px;border-radius:4px}
div[data-baseweb="select"] ul li{color:#1E293B!important;background-color:#FFFFFF!important}
div[data-baseweb="select"] ul li:hover{background-color:#EEF2FF!important}
div[data-baseweb="select"]>div{background-color:#12161F!important;border-color:#2A3040!important;color:#E8ECF1!important}
div[data-baseweb="select"] input{color:#E8ECF1!important}
div[data-baseweb="select"] svg{fill:#94A3B8!important}
div[data-baseweb="popover"] ul{background-color:#FFFFFF!important;border:1px solid #E2E8F0!important;border-radius:10px!important}
div[data-baseweb="popover"] li{color:#1E293B!important}
div[data-baseweb="popover"] li:hover{background-color:#EEF2FF!important}
div[data-testid="stRadio"] label p{color:#CBD5E1!important}
div[data-testid="stCheckbox"] label p{color:#CBD5E1!important}
div[data-testid="stTextInput"] input{background-color:#12161F!important;border-color:#2A3040!important;color:#E8ECF1!important}
::-webkit-scrollbar{width:6px;height:6px}
::-webkit-scrollbar-track{background:#0B0E14}
::-webkit-scrollbar-thumb{background:#2A3040;border-radius:3px}
</style>""", unsafe_allow_html=True)
inject_css()

# ══════════════════════════════════════════
#  상수
# ══════════════════════════════════════════
OB1, OB2, OS1, OS2 = 53, 60, -53, -60
ST_MIN_BAR = 12
NUM_LAYERS = 8

class JT:  # JudgmentThresholds
    STRONG_BUY_SCORE=18.0; BUY_SCORE=12.0; WATCH_BUY_SCORE=6.5
    STRONG_BUY_LAYERS=5; BUY_LAYERS=3; WATCH_LAYERS=2
    STRONG_BUY_RATIO=2.0; BUY_RATIO=1.4
    STRONG_BUY_DIFF=10.0; BUY_DIFF=5.0; WATCH_DIFF=2.0
    SELL_ASYMMETRY=0.85; LOW_VOL_SCALE=0.85
    MIXED_MIN=9.0; MIXED_DIFF_MAX=3.0
    TREND_CAP=12.0; MOMENTUM_CAP=10.0; CANDLE_CAP=5.0; BB_CAP=7.0
    VOLUME_CAP=7.0; MF_CAP=8.0; PATTERN_CAP=10.0; ANTICIPATION_CAP=8.0
    CROSS_SIGNAL_CAP=6.0
    ACCEL_STRONG=3.0; ACCEL_MODERATE=1.5
    CONVERGENCE_FAST=3.0; CONVERGENCE_SLOW=1.5
    COMBO_TIER1_BONUS=4.0; COMBO_TIER2_BONUS=2.5; COMBO_TIER3_BONUS=1.5
    VOL_FILTER_MIN=0.5; VOL_FILTER_STRONG=0.7; VOL_SURGE_RATIO=1.2
    WEEKLY_BULL_THRESH=3; WEEKLY_BEAR_THRESH=-3; MTF_BONUS=3.0; MTF_PENALTY=-2.0
    DECAY_DAYS=3; DECAY_RATE=0.5
    ATR_SPIKE_THRESH=2.0; ATR_SPIKE_MILD=1.5; SHOCK_SEVERE_STREAK=3

GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GEMINI_API_KEY)

@st.cache_resource
def get_gemini_model():
    return genai.GenerativeModel('gemini-2.5-flash')

# ══════════════════════════════════════════
#  시그널 레지스트리
# ══════════════════════════════════════════
_B, _S, _N = 'buy', 'sell', 'neutral'
def _sig(w,d,icon,label,sym,sz,clr,base,atr_m,kor,desc):
    return {'w':w,'dir':d,'icon':icon,'label':label,'sym':sym,'sz':sz,'clr':clr,'base':base,'atr_m':atr_m,'kor':kor,'desc':desc}

SIGNAL_REGISTRY = {
    'Gold_Dot':_sig(3.0,_B,'🏆','GOLD DOT','circle',18,'#FFD700','Low',-3.0,'최강 매수','RSI<30+MFI<30+WT1<-60+상승다이버전스'),
    'Green_Dot_T1':_sig(2.5,_B,'🟢','BUY T1','circle',16,'#00E676','Low',-2.5,'강한 매수','WT과매도교차+RSI<30+MFI<30'),
    'Green_Dot_T2':_sig(2.0,_B,'🟩','BUY T2','circle',13,'#69F0AE','Low',-2.2,'매수','WT과매도+RSI또는MFI<32'),
    'Blue_Diamond':_sig(2.0,_B,'🔹','BLUE DIA','diamond',14,'#00bfff','Low',-1.8,'추세 매수','WT2≤0 상승교차+HTF강세'),
    'Green_Circle':_sig(0.8,_B,'✅','BUY Circle','circle-open',11,'#00E676','Low',-1.2,'과매도 반등','WT과매도교차+RSI<45'),
    'Bull_Divergence':_sig(2.0,_B,'📈','Bull Div','triangle-up',12,'#AA00FF','Low',-2.0,'상승 다이버전스','가격↓ vs WT↑'),
    'RSI_Bull_Divergence':_sig(1.5,_B,'📊','RSI Bull Div','triangle-up',11,'#CE93D8','Low',-1.8,'RSI 상승 다이버전스','가격↓ vs RSI↑'),
    'Squeeze_Fire_Buy':_sig(1.5,_B,'💥','Squeeze BUY','star-diamond',14,'#00FFFF','Low',-1.5,'스퀴즈 매수','TTM Squeeze 해소+모멘텀↑'),
    'Hidden_Bull_Div':_sig(1.5,_B,'🔀','Hidden Bull','triangle-up',10,'#E040FB','Low',-1.6,'히든 상승 다이버전스','가격↑ vs WT↓'),
    'Volume_Climax_Buy':_sig(2.0,_B,'🌊','Vol Climax BUY','hexagram',14,'#00BCD4','Low',-2.8,'거래량 클라이맥스','3x거래량+WT과매도→반등'),
    'OBV_Div_Buy':_sig(0.8,_B,'📊','OBV Div BUY','triangle-up',10,'#80DEEA','Low',-1.4,'OBV 다이버전스','OBV↑ vs 가격↓'),
    'ADX_Momentum_Buy':_sig(1.5,_B,'🚀','ADX Ignition','arrow-up',11,'#76FF03','Low',-1.4,'ADX 점화','ADX>20돌파+DI↑'),
    'Bullish_Engulfing':_sig(1.5,_B,'☀️','Bull Engulf','square',10,'#00E676','Low',-1.3,'상승 장악형','하락캔들감싸는상승캔들+하락맥락'),
    'Golden_Cross':_sig(1.5,_B,'✨','Golden Cross','cross',12,'#FFD700','Low',-0.8,'골든 크로스','50MA>200MA'),
    'EMA_Pullback_Buy':_sig(2.0,_B,'🎯','EMA Pullback','triangle-up',13,'#00BFA5','Low',-1.8,'EMA 눌림목','상승추세EMA조정후반등'),
    'Momentum_Ignition_Buy':_sig(2.5,_B,'🔥','Mom. Ignition','star-diamond',15,'#FF6D00','Low',-2.5,'모멘텀 점화','장대양봉>ATR×1.5+거래량>2x'),
    'SuperTrend_Buy':_sig(1.5,_B,'📈','ST Flip Bull','arrow-up',12,'#00E5FF','Low',-1.5,'슈퍼트렌드 강세','SuperTrend위로돌파'),
    'VWAP_Bounce_Buy':_sig(1.5,_B,'🏦','VWAP Bounce','triangle-up',11,'#00E5FF','Low',-1.3,'VWAP 반등','VWAP복귀+WT교차'),
    'Parabolic_Bottom_Buy':_sig(3.0,_B,'🧊','Parabolic Bot','diamond',16,'#00FFFF','Low',-3.0,'포물선 바닥','WT1<-80꺾임+양봉'),
    'MACD_Cross_Buy':_sig(1.0,_B,'〽️','MACD Cross','triangle-up',9,'#4CAF50','Low',-1.0,'MACD 골든크로스','MACD>시그널'),
    'StochRSI_Cross_Buy':_sig(0.8,_B,'🔄','StRSI Cross','circle-open',8,'#81C784','Low',-0.8,'StochRSI 매수교차','StochK>StochD(과매도)'),
    'Blood_Diamond':_sig(3.0,_S,'🩸','BLOOD DIA','diamond',18,'#DC143C','High',3.0,'최강 매도','RSI>70+MFI>70+WT1>60+하락다이버전스'),
    'Red_Dot_T1':_sig(2.5,_S,'🔴','SELL T1','circle',16,'#FF1744','High',2.5,'강한 매도','WT과매수하락교차+RSI>70+MFI>70'),
    'Red_Dot_T2':_sig(2.0,_S,'🟥','SELL T2','circle',13,'#FF5252','High',2.2,'매도','WT과매수+RSI또는MFI>68'),
    'Red_Diamond':_sig(2.0,_S,'🔸','RED DIA','diamond',14,'#ff3333','High',1.8,'추세 매도','WT2≥0하락교차+HTF약세'),
    'Red_Circle':_sig(0.8,_S,'⛔','SELL Circle','circle-open',11,'#FF1744','High',1.2,'과매수 하락','WT과매수하락교차+RSI>55'),
    'Bear_Divergence':_sig(2.0,_S,'📉','Bear Div','triangle-down',12,'#AA00FF','High',2.0,'하락 다이버전스','가격↑ vs WT↓'),
    'RSI_Bear_Divergence':_sig(1.5,_S,'📉','RSI Bear Div','triangle-down',11,'#CE93D8','High',1.8,'RSI 하락 다이버전스','가격↑ vs RSI↓'),
    'Squeeze_Fire_Sell':_sig(1.5,_S,'🧨','Squeeze SELL','star-diamond',14,'#FF6600','High',1.5,'스퀴즈 매도','TTM Squeeze해소+모멘텀↓'),
    'Hidden_Bear_Div':_sig(1.5,_S,'🔁','Hidden Bear','triangle-down',10,'#E040FB','High',1.6,'히든 하락 다이버전스','가격↓ vs WT↑'),
    'Volume_Climax_Sell':_sig(2.0,_S,'🌋','Vol Climax SELL','hexagram',14,'#FF5722','High',2.8,'거래량 클라이맥스','3x거래량+WT과매수→하락'),
    'OBV_Div_Sell':_sig(0.8,_S,'🔻','OBV Div SELL','triangle-down',10,'#FFAB91','High',1.4,'OBV 다이버전스','OBV↓ vs 가격↑'),
    'ADX_Momentum_Sell':_sig(1.5,_S,'💨','ADX Down','arrow-down',11,'#FF3D00','High',1.4,'ADX 하락 점화','ADX>20+-DI>+DI'),
    'Bearish_Engulfing':_sig(1.5,_S,'🌑','Bear Engulf','x',10,'#D50000','High',1.3,'하락 장악형','상승캔들감싸는하락캔들+상승맥락'),
    'Death_Cross':_sig(1.5,_S,'☠️','Death Cross','cross',12,'#FF1744','High',0.8,'데드 크로스','50MA<200MA'),
    'SuperTrend_Sell':_sig(2.0,_S,'📉','ST Flip Bear','arrow-down',12,'#FF1744','High',1.5,'슈퍼트렌드 약세','SuperTrend하향돌파'),
    'Parabolic_Top_Sell':_sig(3.0,_S,'🌡️','Parabolic Top','diamond',16,'#FF0000','High',3.0,'포물선 천장','WT1>80꺾임+음봉'),
    'EMA_Pullback_Sell':_sig(2.0,_S,'🎯','EMA PB Sell','triangle-down',13,'#FF6E40','High',1.8,'EMA 되돌림 매도','하락추세EMA반등후WT재하락'),
    'Momentum_Ignition_Sell':_sig(2.5,_S,'💣','Mom. Ign Sell','star-diamond',15,'#D50000','High',2.5,'모멘텀 점화 매도','장대음봉>ATR×1.5+거래량>2x'),
    'VWAP_Reject_Sell':_sig(1.5,_S,'🏛️','VWAP Reject','triangle-down',11,'#FF6E40','High',1.3,'VWAP 저항','VWAP실패+WT교차'),
    'MACD_Cross_Sell':_sig(1.0,_S,'〽️','MACD Dead','triangle-down',9,'#E57373','High',1.0,'MACD 데드크로스','MACD<시그널'),
    'StochRSI_Cross_Sell':_sig(0.8,_S,'🔄','StRSI Dead','circle-open',8,'#EF9A9A','High',0.8,'StochRSI 매도교차','StochK<StochD(과매수)'),
    'Hammer':_sig(1.5,_B,'🔨','Hammer','triangle-up',11,'#00E676','Low',-1.5,'해머','긴하단꼬리+거래량확인'),
    'Morning_Star':_sig(2.0,_B,'🌅','MornStar','star',13,'#00E676','Low',-2.0,'모닝스타','큰음봉→소형봉→강한양봉+거래량급증'),
    'Doji_Bullish':_sig(0.8,_B,'➕','Doji Bull','cross-thin',9,'#69F0AE','Low',-1.0,'강세 도지','시가≈종가+하락추세후'),
    'Shooting_Star':_sig(1.5,_S,'🌠','ShootStar','triangle-down',11,'#FF1744','High',1.5,'슈팅스타','긴상단꼬리+거래량확인'),
    'Evening_Star':_sig(2.0,_S,'🌆','EveStar','star',13,'#FF1744','High',2.0,'이브닝스타','큰양봉→소형봉→강한음봉+거래량급증'),
    'Doji_Bearish':_sig(0.8,_S,'➖','Doji Bear','cross-thin',9,'#FF5252','High',1.0,'약세 도지','시가≈종가+상승추세후'),
    'Inside_Day':_sig(0.3,_N,'📦','InsideDay','square-open',7,'#FFC107','Low',-0.3,'인사이드데이','고가<전일고&저가>전일저'),
    'Outside_Bullish':_sig(1.5,_B,'💪','OutsideBull','square',11,'#00E676','Low',-1.5,'강세 아웃사이드','전일범위포함+양봉'),
    'Outside_Bearish':_sig(1.5,_S,'🥊','OutsideBear','square',11,'#FF1744','High',1.5,'약세 아웃사이드','전일범위포함+음봉'),
    'Cross_Above_20MA':_sig(0.8,_B,'📈','X▲20MA','triangle-up',9,'#69F0AE','Low',-0.8,'20MA상향돌파','종가>20MA'),
    'Cross_Above_50MA':_sig(1.2,_B,'📈','X▲50MA','triangle-up',10,'#00E676','Low',-1.0,'50MA상향돌파','종가>50MA'),
    'Cross_Above_200MA':_sig(1.5,_B,'📈','X▲200MA','triangle-up',11,'#00BFA5','Low',-1.2,'200MA상향돌파','종가>200MA'),
    'Fell_Below_20MA':_sig(0.8,_S,'📉','X▼20MA','triangle-down',9,'#FF5252','High',0.8,'20MA하향이탈','종가<20MA'),
    'Fell_Below_50MA':_sig(1.2,_S,'📉','X▼50MA','triangle-down',10,'#FF1744','High',1.0,'50MA하향이탈','종가<50MA'),
    'Fell_Below_200MA':_sig(1.5,_S,'📉','X▼200MA','triangle-down',11,'#D50000','High',1.2,'200MA하향이탈','종가<200MA'),
    'BB_Upper_Break':_sig(1.0,_B,'🔝','BB▲Break','diamond-open',10,'#00E5FF','High',1.0,'BB상단돌파','종가>상단BB'),
    'BB_Lower_Bounce':_sig(1.2,_B,'⤵️','BB▼Bounce','diamond-open',10,'#4FC3F7','Low',-1.2,'BB하단반등','종가<하단BB+양봉전환'),
    'BB_Lower_Break':_sig(1.0,_S,'💀','BB▼Break','diamond-open',10,'#FF6E40','Low',-1.0,'BB하단붕괴','종가<하단BB+약세지속'),
    'BB_Squeeze_End_Bull':_sig(1.5,_B,'💥','SqEnd▲','star-diamond',12,'#00FFFF','Low',-1.5,'BB스퀴즈해소↑','BB확장+상승'),
    'BB_Squeeze_End_Bear':_sig(1.5,_S,'💥','SqEnd▼','star-diamond',12,'#FF6600','High',1.5,'BB스퀴즈해소↓','BB확장+하락'),
    'MACD_Zero_Cross_Buy':_sig(1.2,_B,'⬆️','MACD 0▲','triangle-up',10,'#4CAF50','Low',-1.0,'MACD 0선돌파','MACD>0'),
    'MACD_Zero_Cross_Sell':_sig(1.2,_S,'⬇️','MACD 0▼','triangle-down',10,'#E57373','High',1.0,'MACD 0선이탈','MACD<0'),
    'Up_5_Days':_sig(0.8,_B,'📗','Up5D','triangle-up',9,'#00E676','High',0.8,'5일연속상승','5일연속양봉'),
    'Down_5_Days':_sig(0.8,_S,'📕','Dn5D','triangle-down',9,'#FF1744','Low',-0.8,'5일연속하락','5일연속음봉'),
    'Up_7_Days':_sig(1.2,_B,'📗','Up7D','triangle-up',10,'#00E676','High',1.0,'7일연속상승','7일연속양봉'),
    'Down_7_Days':_sig(1.2,_S,'📕','Dn7D','triangle-down',10,'#FF1744','Low',-1.0,'7일연속하락','7일연속음봉'),
    'Gap_Up':_sig(1.0,_B,'⏫','GapUp','arrow-up',10,'#00E676','Low',-1.0,'갭 상승','시가>전일고가'),
    'Gap_Down':_sig(1.0,_S,'⏬','GapDn','arrow-down',10,'#FF1744','High',1.0,'갭 하락','시가<전일저가'),
    'Gap_Up_Closed':_sig(0.8,_S,'🔄','GapUp Fill','circle-open',8,'#FFA726','High',0.8,'갭업메움','상승갭메워짐'),
    'Gap_Down_Closed':_sig(0.8,_B,'🔄','GapDn Fill','circle-open',8,'#4FC3F7','Low',-0.8,'갭다운메움','하락갭메워짐'),
    'NR7_2':_sig(0.8,_N,'🔳','NR7-2','square-open',8,'#90A4AE','Low',-0.5,'NR7-2','2일연속NR7'),
    'Calm_After_Storm':_sig(1.0,_N,'🌤️','CalmStorm','diamond-open',9,'#FFC107','Low',-0.8,'폭풍뒤고요','WideRange→NarrowRange'),
    'Wide_Range_Bar':_sig(0.5,_N,'📊','WideBar','square-open',7,'#FFAB40','Low',-0.4,'넓은범위봉','범위>ATR×2'),
    'New_52W_High':_sig(1.5,_B,'🏔️','52W▲','star-triangle-up',12,'#FFD700','High',1.5,'52주신고가','52주최고가갱신'),
    'New_52W_Low':_sig(1.5,_S,'🕳️','52W▼','star-triangle-down',12,'#B71C1C','Low',-1.5,'52주신저가','52주최저가갱신'),
    'Pullback_123_Bull':_sig(2.0,_B,'🎯','123PB▲','triangle-up',12,'#00E676','Low',-1.8,'1,2,3풀백매수','ADX>30+DI↑+3일저점↓'),
    'Pullback_123_Bear':_sig(2.0,_S,'🎯','123PB▼','triangle-down',12,'#FF1744','High',1.8,'1,2,3풀백매도','ADX>30+DI↓+3일고점↑'),
    'Setup_180_Bull':_sig(2.0,_B,'🔄','180▲','star-diamond',13,'#00E676','Low',-2.0,'180매수셋업','전일하위25%→당일상위25%'),
    'Setup_180_Bear':_sig(2.0,_S,'🔄','180▼','star-diamond',13,'#FF1744','High',2.0,'180매도셋업','전일상위25%→당일하위25%'),
    'Boomer_Buy':_sig(2.0,_B,'💣','Boomer▲','star',12,'#00E676','Low',-1.8,'부머매수','ADX>30+2일인사이드→돌파'),
    'Boomer_Sell':_sig(2.0,_S,'💣','Boomer▼','star',12,'#FF1744','High',1.8,'부머매도','ADX>30+2일인사이드→이탈'),
    'Expansion_BO':_sig(2.5,_B,'🚀','XBO','star-diamond',14,'#FFD700','Low',-2.5,'확장돌파','2개월신고가+9일최대범위'),
    'Expansion_BD':_sig(2.5,_S,'💨','XBD','star-diamond',14,'#FF0000','High',2.5,'확장붕괴','2개월신저가+9일최대범위'),
    'Gilligans_Buy':_sig(2.0,_B,'🏝️','Gilligan▲','hexagon',12,'#00BCD4','Low',-2.0,'길리건매수','갭다운2개월신저가→반전'),
    'Gilligans_Sell':_sig(2.0,_S,'🏝️','Gilligan▼','hexagon',12,'#FF5722','High',2.0,'길리건매도','갭업2개월신고가→반전'),
    'Lizard_Bull':_sig(1.5,_B,'🦎','Lizard▲','triangle-up',10,'#00E676','Low',-1.5,'리자드매수','시가종가상위25%+10일신저가'),
    'Lizard_Bear':_sig(1.5,_S,'🦎','Lizard▼','triangle-down',10,'#FF1744','High',1.5,'리자드매도','시가종가하위25%+10일신고가'),
    'NonADX_123_Bull':_sig(1.8,_B,'📐','nADX123▲','triangle-up',11,'#69F0AE','Low',-1.5,'비ADX풀백매수','주가>50MA+3일저점↓'),
    'NonADX_123_Bear':_sig(1.8,_S,'📐','nADX123▼','triangle-down',11,'#FF5252','High',1.5,'비ADX풀백매도','주가<50MA+3일고점↑'),
    'Pocket_Pivot':_sig(1.5,_B,'🧲','PocketPvt','triangle-up',11,'#7C4DFF','Low',-1.5,'포켓피봇','양봉+거래량>10일하락거래량최대'),
    'MF_Cross_Bull':_sig(1.5,_B,'💰','MF 0▲','triangle-up',11,'#00E676','Low',-1.2,'MF 강세전환','자금흐름음→양'),
    'MF_Cross_Bear':_sig(1.5,_S,'💸','MF 0▼','triangle-down',11,'#FF1744','High',1.2,'MF 약세전환','자금흐름양→음'),
    'MF_Bull_Div':_sig(1.8,_B,'💹','MF Bull Div','triangle-up',11,'#7C4DFF','Low',-1.5,'MF 상승 다이버전스','가격↓ vs MF↑'),
    'MF_Bear_Div':_sig(1.8,_S,'💹','MF Bear Div','triangle-down',11,'#E040FB','High',1.5,'MF 하락 다이버전스','가격↑ vs MF↓'),
    'MF_Accel_Up':_sig(1.0,_B,'📈','MF Accel▲','arrow-up',9,'#69F0AE','Low',-0.8,'MF 가속상승','5일+MF연속상승'),
    'MF_Accel_Dn':_sig(1.0,_S,'📉','MF Accel▼','arrow-down',9,'#FF5252','High',0.8,'MF 가속하락','5일+MF연속하락'),
    'Kumo_Breakout_Bull':_sig(2.0,_B,'☁️','Kumo▲','triangle-up',13,'#00E676','Low',-2.0,'쿠모 상향돌파','종가>구름상단'),
    'Kumo_Breakout_Bear':_sig(2.0,_S,'☁️','Kumo▼','triangle-down',13,'#FF1744','High',2.0,'쿠모 하향돌파','종가<구름하단'),
    'TK_Cross_Bull':_sig(1.5,_B,'⛩️','TK Cross▲','triangle-up',10,'#69F0AE','Low',-1.2,'전환-기준 골든','전환선>기준선'),
    'TK_Cross_Bear':_sig(1.5,_S,'⛩️','TK Cross▼','triangle-down',10,'#FF5252','High',1.2,'전환-기준 데드','전환선<기준선'),
    'CMF_Bull':_sig(1.2,_B,'🌀','CMF Bull','triangle-up',10,'#00BCD4','Low',-1.0,'CMF 강세','CMF>0.1'),
    'CMF_Bear':_sig(1.2,_S,'🌀','CMF Bear','triangle-down',10,'#FF5722','High',1.0,'CMF 약세','CMF<-0.1'),
    'Setup_Squeeze_Bull':_sig(1.0,_B,'⏳','SqSetup▲','hourglass',10,'#80DEEA','Low',-0.8,'스퀴즈셋업▲','BB축소+모멘텀상승전환임박'),
    'Setup_Squeeze_Bear':_sig(1.0,_S,'⏳','SqSetup▼','hourglass',10,'#FFAB91','High',0.8,'스퀴즈셋업▼','BB축소+모멘텀하락전환임박'),
    'Momentum_Accel_Buy':_sig(1.5,_B,'⚡','Mom Accel▲','arrow-up',11,'#76FF03','Low',-1.2,'모멘텀가속▲','RSI+WT+MACD동시가속상승'),
    'Momentum_Accel_Sell':_sig(1.5,_S,'⚡','Mom Accel▼','arrow-down',11,'#FF3D00','High',1.2,'모멘텀가속▼','RSI+WT+MACD동시가속하락'),
    'Volume_Dry_Up':_sig(0.5,_N,'🏜️','VolDryUp','square-open',8,'#FFE082','Low',-0.3,'거래량고갈','5일연속평균이하'),
    'WT_Convergence_Bull':_sig(1.2,_B,'🔀','WT Conv▲','triangle-up',10,'#B2FF59','Low',-1.0,'WT수렴매수임박','WT1→WT2빠른수렴+과매도'),
    'WT_Convergence_Bear':_sig(1.2,_S,'🔀','WT Conv▼','triangle-down',10,'#FF8A80','High',1.0,'WT수렴매도임박','WT1→WT2빠른수렴+과매수'),
    'Volume_POC_Breakout':_sig(2.0,_B,'🏛️','POC Break▲','triangle-up',13,'#7C4DFF','Low',-1.8,'POC 상향돌파','종가>매물대POC'),
    'Volume_POC_Breakdown':_sig(2.0,_S,'🏛️','POC Break▼','triangle-down',13,'#E040FB','High',1.8,'POC 하향이탈','종가<매물대POC'),
    'VP_VAH_Resistance':_sig(1.0,_S,'🏛️','VAH Resist','triangle-down',10,'#FFAB91','High',1.0,'VAH 저항 접근','종가→VA상단+약세반응'),
    'VP_VAL_Support':_sig(1.0,_B,'🏛️','VAL Support','triangle-up',10,'#80DEEA','Low',-1.0,'VAL 지지 접근','종가→VA하단+강세반응'),
    'Relative_Strength_Buy':_sig(2.0,_B,'💪','RS Strong','star-diamond',13,'#00E5FF','Low',-1.8,'상대강도 매수','하락장방어+SPY대비강세'),
    'Relative_Strength_Sell':_sig(1.5,_S,'🐌','RS Weak','star-diamond',11,'#FF6E40','High',1.5,'상대약세 매도','상승장뒤처짐+SPY대비약세'),
}

COMPOSITE_SIGNALS = {
    'Ultra_Buy':_sig(0,_B,'⚡','ULTRA BUY','star',20,'#FFD700','Low',-3.5,'울트라 매수','Confluence≥6.5'),
    'Strong_Buy':_sig(0,_B,'🔱','STRONG BUY','star',16,'#00E676','Low',-3.2,'스트롱 매수','Confluence 3.5~6.5'),
    'Ultra_Sell':_sig(0,_S,'🚨','ULTRA SELL','star',20,'#FF0000','High',3.5,'울트라 매도','Confluence≤-6.5'),
    'Strong_Sell':_sig(0,_S,'⚠️','STRONG SELL','star',16,'#FF1744','High',3.2,'스트롱 매도','Confluence -6.5~-3.5'),
}
ALL_CHART_SIGNALS = {**SIGNAL_REGISTRY, **COMPOSITE_SIGNALS}

# 차트 표시 등급
SIGNAL_CHART_TIERS = {
    'A': ['Gold_Dot','Blood_Diamond','Green_Dot_T1','Red_Dot_T1','Parabolic_Bottom_Buy','Parabolic_Top_Sell',
          'Volume_Climax_Buy','Volume_Climax_Sell','Momentum_Ignition_Buy','Momentum_Ignition_Sell',
          'Expansion_BO','Expansion_BD'],
    'B': ['Green_Dot_T2','Red_Dot_T2','Blue_Diamond','Red_Diamond','Bull_Divergence','Bear_Divergence',
          'Squeeze_Fire_Buy','Squeeze_Fire_Sell','EMA_Pullback_Buy','EMA_Pullback_Sell',
          'SuperTrend_Buy','SuperTrend_Sell','Kumo_Breakout_Bull','Kumo_Breakout_Bear',
          'Morning_Star','Evening_Star','Bullish_Engulfing','Bearish_Engulfing',
          'Golden_Cross','Death_Cross','Volume_POC_Breakout','Volume_POC_Breakdown',
          'Relative_Strength_Buy','Relative_Strength_Sell'],
}

COOLDOWN_MAP = {
    'Squeeze_Fire_Buy':5,'Squeeze_Fire_Sell':5,'Bullish_Engulfing':5,'Bearish_Engulfing':5,
    'ADX_Momentum_Buy':10,'ADX_Momentum_Sell':10,'EMA_Pullback_Buy':7,'EMA_Pullback_Sell':7,
    'Momentum_Ignition_Buy':10,'Momentum_Ignition_Sell':10,'Parabolic_Top_Sell':5,'Parabolic_Bottom_Buy':5,
    'VWAP_Bounce_Buy':7,'VWAP_Reject_Sell':7,'MACD_Cross_Buy':12,'MACD_Cross_Sell':12,
    'StochRSI_Cross_Buy':7,'StochRSI_Cross_Sell':7,'RSI_Bull_Divergence':10,'RSI_Bear_Divergence':10,
    'Hammer':5,'Shooting_Star':5,'Morning_Star':7,'Evening_Star':7,'Doji_Bullish':5,'Doji_Bearish':5,
    'Outside_Bullish':7,'Outside_Bearish':7,'Cross_Above_20MA':5,'Fell_Below_20MA':5,
    'Cross_Above_50MA':10,'Fell_Below_50MA':10,'Cross_Above_200MA':15,'Fell_Below_200MA':15,
    'BB_Upper_Break':5,'BB_Lower_Bounce':5,'BB_Lower_Break':5,
    'BB_Squeeze_End_Bull':7,'BB_Squeeze_End_Bear':7,'MACD_Zero_Cross_Buy':12,'MACD_Zero_Cross_Sell':12,
    'Gap_Up':3,'Gap_Down':3,'Gap_Up_Closed':5,'Gap_Down_Closed':5,
    'New_52W_High':10,'New_52W_Low':10,'Calm_After_Storm':5,
    'Pullback_123_Bull':7,'Pullback_123_Bear':7,'Setup_180_Bull':7,'Setup_180_Bear':7,
    'Boomer_Buy':10,'Boomer_Sell':10,'Expansion_BO':10,'Expansion_BD':10,
    'Gilligans_Buy':10,'Gilligans_Sell':10,'Lizard_Bull':5,'Lizard_Bear':5,
    'NonADX_123_Bull':7,'NonADX_123_Bear':7,'Pocket_Pivot':10,
    'MF_Cross_Bull':10,'MF_Cross_Bear':10,'MF_Bull_Div':10,'MF_Bear_Div':10,
    'MF_Accel_Up':5,'MF_Accel_Dn':5,'Kumo_Breakout_Bull':10,'Kumo_Breakout_Bear':10,
    'TK_Cross_Bull':7,'TK_Cross_Bear':7,'CMF_Bull':10,'CMF_Bear':10,
    'Setup_Squeeze_Bull':3,'Setup_Squeeze_Bear':3,'Momentum_Accel_Buy':5,'Momentum_Accel_Sell':5,
    'Volume_Dry_Up':3,'WT_Convergence_Bull':5,'WT_Convergence_Bear':5,
    'Volume_POC_Breakout':7,'Volume_POC_Breakdown':7,'VP_VAH_Resistance':5,'VP_VAL_Support':5,
    'Relative_Strength_Buy':10,'Relative_Strength_Sell':10,'Up_7_Days':10,'Down_7_Days':10,
}

SIGNAL_HIERARCHY = {
    'candle_bull':['Morning_Star','Bullish_Engulfing','Hammer','Doji_Bullish'],
    'candle_bear':['Evening_Star','Bearish_Engulfing','Shooting_Star','Doji_Bearish'],
    'ma_cross_bull':['Cross_Above_200MA','Cross_Above_50MA','Cross_Above_20MA'],
    'ma_cross_bear':['Fell_Below_200MA','Fell_Below_50MA','Fell_Below_20MA'],
    'cooper_bull':['Expansion_BO','Pullback_123_Bull','Setup_180_Bull','Boomer_Buy','Gilligans_Buy','Lizard_Bull','NonADX_123_Bull'],
    'cooper_bear':['Expansion_BD','Pullback_123_Bear','Setup_180_Bear','Boomer_Sell','Gilligans_Sell','Lizard_Bear','NonADX_123_Bear'],
    'ichimoku_bull':['Kumo_Breakout_Bull','TK_Cross_Bull'],
    'ichimoku_bear':['Kumo_Breakout_Bear','TK_Cross_Bear'],
    'anticipation_bull':['Momentum_Accel_Buy','WT_Convergence_Bull','Setup_Squeeze_Bull'],
    'anticipation_bear':['Momentum_Accel_Sell','WT_Convergence_Bear','Setup_Squeeze_Bear'],
}

JUDGMENT_MARKERS = {
    'STRONG_BUY':{'symbol':'star','size':18,'color':'#00E676','label':'🟢🟢🟢 STRONG BUY','short':'S.BUY','line_color':'#FFFFFF','line_width':2,'base':'Low','atr_mult':-3.5},
    'BUY':{'symbol':'triangle-up','size':14,'color':'#00E676','label':'🟢🟢 BUY','short':'BUY','line_color':'#FFFFFF','line_width':1.5,'base':'Low','atr_mult':-2.5},
    'WATCH_BUY':{'symbol':'circle','size':9,'color':'#69F0AE','label':'🟡🟢 WATCH BUY','short':'W.BUY','line_color':'#69F0AE','line_width':1,'base':'Low','atr_mult':-2.0},
    'STRONG_SELL':{'symbol':'star','size':18,'color':'#FF1744','label':'🔴🔴🔴 STRONG SELL','short':'S.SELL','line_color':'#FFFFFF','line_width':2,'base':'High','atr_mult':3.5},
    'SELL':{'symbol':'triangle-down','size':14,'color':'#FF1744','label':'🔴🔴 SELL','short':'SELL','line_color':'#FFFFFF','line_width':1.5,'base':'High','atr_mult':2.5},
    'WATCH_SELL':{'symbol':'circle','size':9,'color':'#FF5252','label':'🟡🔴 WATCH SELL','short':'W.SELL','line_color':'#FF5252','line_width':1,'base':'High','atr_mult':2.0},
    'MIXED':{'symbol':'diamond','size':11,'color':'#FF9800','label':'🟠 MIXED','short':'MIXED','line_color':'#FF9800','line_width':1,'base':'High','atr_mult':2.0},
}
JUDGMENT_CONFIG = {
    'STRONG_BUY':('🟢🟢🟢 STRONG BUY','#00E676','rgba(0,230,118,.12)'),
    'BUY':('🟢🟢 BUY','#00E676','rgba(0,230,118,.08)'),
    'WATCH_BUY':('🟡🟢 WATCH BUY','#FFC107','rgba(255,193,7,.08)'),
    'NEUTRAL':('⚪ NEUTRAL','#888888','rgba(128,128,128,.05)'),
    'MIXED':('🟠 MIXED','#FF9800','rgba(255,152,0,.08)'),
    'WATCH_SELL':('🟡🔴 WATCH SELL','#FFC107','rgba(255,193,7,.08)'),
    'SELL':('🔴🔴 SELL','#FF1744','rgba(255,23,68,.08)'),
    'STRONG_SELL':('🔴🔴🔴 STRONG SELL','#FF1744','rgba(255,23,68,.12)'),
}


# ══════════════════════════════════════════
#  유틸리티
# ══════════════════════════════════════════
def _recent(s, lb=3):
    return s.astype(float).rolling(lb+1, min_periods=1).max().fillna(0).astype(bool)

def _cooldown(sig, bars=5):
    v = sig.fillna(False).values.astype(bool); out = np.zeros(len(v), dtype=bool); last = -bars-1
    for i in range(len(v)):
        if v[i] and (i-last) > bars: out[i] = True; last = i
    return pd.Series(out, index=sig.index)

def _cooldown_directional(df, buy_sig, sell_sig, bars=5):
    bv = df.get(buy_sig, pd.Series(False, index=df.index)).fillna(False).values.astype(bool)
    sv = df.get(sell_sig, pd.Series(False, index=df.index)).fillna(False).values.astype(bool)
    b_out = np.zeros(len(bv), dtype=bool); s_out = np.zeros(len(sv), dtype=bool)
    last_b, last_s = -bars-1, -bars-1
    for i in range(len(df)):
        if sv[i]: last_b = -bars-1
        if bv[i]: last_s = -bars-1
        if bv[i] and (i-last_b) > bars: b_out[i] = True; last_b = i
        if sv[i] and (i-last_s) > bars: s_out[i] = True; last_s = i
    if buy_sig in df.columns: df[buy_sig] = pd.Series(b_out, index=df.index)
    if sell_sig in df.columns: df[sell_sig] = pd.Series(s_out, index=df.index)

def _volf(vol, ratio=0.5, period=20):
    return vol >= (vol.rolling(period, min_periods=5).mean() * ratio)

def _valid_fmt(t): return bool(re.match(r'^[A-Za-z]{1,5}([.\-][A-Za-z]{1,2})?$', t))
def _cls(val, lo, hi): return 'ind-bullish' if val < lo else ('ind-bearish' if val > hi else 'ind-neutral')
def _sig_pts(df, sig_name, points):
    return np.where(df[sig_name].fillna(False), points, 0.0) if sig_name in df.columns else 0.0
def _sig_pts_decayed(df, sig_name, full_pts, decay_days=None, decay_rate=None):
    if decay_days is None: decay_days = JT.DECAY_DAYS
    if decay_rate is None: decay_rate = JT.DECAY_RATE
    if sig_name not in df.columns: return 0.0
    base = np.where(df[sig_name].fillna(False), full_pts, 0.0)
    total = base.copy()
    for d in range(1, decay_days+1):
        shifted = np.roll(base, d); shifted[:d] = 0
        total += shifted * (decay_rate ** d)
    return total
def _vectorized_streak(condition):
    c = condition.astype(int); groups = (c == 0).cumsum()
    return c.groupby(groups).cumsum()


# ══════════════════════════════════════════
#  캐시
# ══════════════════════════════════════════
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
        return "\n".join([f"Market Cap: {_get('marketCap','large')}",f"Float: {_get('floatShares','large')}",
            f"Short % of Float: {_get('shortPercentOfFloat','percent')}",f"Days to Cover: {_get('shortRatio','float')}",
            f"P/E: {_get('trailingPE','float')}",f"P/S: {_get('priceToSalesTrailing12Months','float')}",
            f"52W High: {_get('fiftyTwoWeekHigh','currency')}",f"52W Low: {_get('fiftyTwoWeekLow','currency')}",
            f"Avg Vol: {_get('averageVolume','large')}"])
    except: return "펀더멘탈 데이터 없음"

@st.cache_data(ttl=300, max_entries=30, show_spinner=False)
def fetch_history(ticker, _ts=None): return yf.Ticker(ticker).history(period="2y")

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_spy_history(_ts=None): return yf.Ticker("SPY").history(period="2y")

@st.cache_data(ttl=600, show_spinner=False)
def validate_ticker(ticker):
    try: return not yf.Ticker(ticker).history(period="5d").empty
    except: return False

@st.cache_data(ttl=300, max_entries=50, show_spinner=False)
def _compute_cached(ticker, _cache_key):
    df = fetch_history(ticker)
    if df.empty: return None
    return detect_all_signals(compute_indicators(df))

def compute_and_cache(ticker, _ts=None):
    cache_window = math.floor(time.time() / 300)
    cache_key = f"{ticker}_{_ts}" if _ts else f"{ticker}_{cache_window}"
    return _compute_cached(ticker, cache_key)

# ══════════════════════════════════════════
#  기술 지표 계산 엔진
# ══════════════════════════════════════════
def compute_rsi(s, p=14):
    d = s.diff(); g, l = d.clip(lower=0), -d.clip(upper=0)
    return 100 - (100 / (1 + g.ewm(alpha=1/p, min_periods=p).mean() / (l.ewm(alpha=1/p, min_periods=p).mean() + 1e-10)))

def compute_mfi(h, l, c, v, p=14):
    tp = (h+l+c)/3; raw = tp*v; d = tp.diff()
    return 100 - (100 / (1 + raw.where(d>=0,0.0).rolling(p).sum() / (raw.where(d<0,0.0).rolling(p).sum()+1e-10)))

def compute_rsi_mfi(h, l, c, v, p=60):
    rf, mf = compute_rsi(c,20), compute_mfi(h,l,c,v,20)
    rs, ms = compute_rsi(c,p), compute_mfi(h,l,c,v,p)
    return (((rf-50)+(mf-50))/2)*.6 + (((rs-50)+(ms-50))/2)*.4

def compute_wavetrend(h, l, c, ch=9, avg=12, ma=3):
    ap = (h+l+c)/3; esa = ap.ewm(span=ch, adjust=False).mean()
    d = abs(ap-esa).ewm(span=ch, adjust=False).mean()
    ci = (ap-esa)/(0.015*d+1e-10); wt1 = ci.ewm(span=avg, adjust=False).mean()
    wt2 = wt1.rolling(ma).mean()
    return wt1, wt2, (wt1>wt2)&(wt1.shift(1)<=wt2.shift(1)), (wt1<wt2)&(wt1.shift(1)>=wt2.shift(1))

def compute_stoch_rsi(c, rl=14, sl=14, ks=3, ds=3):
    rsi = compute_rsi(c, rl); mn, mx = rsi.rolling(sl).min(), rsi.rolling(sl).max()
    k = (((rsi-mn)/(mx-mn+1e-10))*100).rolling(ks).mean(); return k, k.rolling(ds).mean()

def compute_tr(h, l, c):
    pc = c.shift(1); return pd.concat([h-l, (h-pc).abs(), (l-pc).abs()], axis=1).max(axis=1)

def compute_adx(h, l, c, p=14):
    tr = compute_tr(h,l,c); ph, pl = h.shift(1), l.shift(1)
    pdm = pd.Series(np.where((h-ph)>(pl-l), np.maximum(h-ph,0), 0), index=h.index, dtype=float)
    mdm = pd.Series(np.where((pl-l)>(h-ph), np.maximum(pl-l,0), 0), index=h.index, dtype=float)
    atr = tr.ewm(alpha=1/p, min_periods=p).mean()
    pdi = 100*pdm.ewm(alpha=1/p, min_periods=p).mean()/(atr+1e-10)
    mdi = 100*mdm.ewm(alpha=1/p, min_periods=p).mean()/(atr+1e-10)
    dx = 100*(pdi-mdi).abs()/(pdi+mdi+1e-10)
    return dx.ewm(alpha=1/p, min_periods=p).mean(), pdi, mdi

def compute_obv(c, v): return (v*np.sign(c.diff()).fillna(0)).cumsum()

def compute_macd(c, f=12, s=26, sig=9):
    ml = c.ewm(span=f, adjust=False).mean()-c.ewm(span=s, adjust=False).mean()
    sl = ml.ewm(span=sig, adjust=False).mean(); return ml, sl, ml-sl

def compute_ichimoku(h, l, c, tp=9, kp=26, sbp=52, disp=26):
    tenkan = (h.rolling(tp).max()+l.rolling(tp).min())/2
    kijun = (h.rolling(kp).max()+l.rolling(kp).min())/2
    sa = ((tenkan+kijun)/2).shift(disp)
    sb = ((h.rolling(sbp).max()+l.rolling(sbp).min())/2).shift(disp)
    return tenkan, kijun, sa, sb, c.shift(-disp)

def compute_cmf(h, l, c, v, p=20):
    mfm = ((c-l)-(h-c))/(h-l+1e-10); return (mfm*v).rolling(p).sum()/(v.rolling(p).sum()+1e-10)

def compute_supertrend(h, l, c, tr, period=10, mult=3.0):
    atr = tr.rolling(period).mean(); hl2 = (h+l)/2
    up = (hl2+mult*atr).values.copy(); dn = (hl2-mult*atr).values.copy()
    cl = c.values; n = len(c); sv = np.full(n, np.nan); dv = np.zeros(n, dtype=int)
    fv = period
    if fv >= n: return pd.Series(np.nan, index=c.index), pd.Series(0, index=c.index, dtype=int)
    dv[fv] = 1; sv[fv] = dn[fv]
    for i in range(fv+1, n):
        if dv[i-1]==1: dn[i] = max(dn[i], dn[i-1]) if not np.isnan(dn[i-1]) else dn[i]
        else: up[i] = min(up[i], up[i-1]) if not np.isnan(up[i-1]) else up[i]
        if dv[i-1]==1: dv[i], sv[i] = (-1, up[i]) if cl[i]<dn[i] else (1, dn[i])
        else: dv[i], sv[i] = (1, dn[i]) if cl[i]>up[i] else (-1, up[i])
    return pd.Series(sv, index=c.index), pd.Series(dv, index=c.index)


# ══════════════════════════════════════════
#  다이버전스 (ATR 동적 + scipy)
# ══════════════════════════════════════════
def detect_pivot_div(price, osc, lb=60, pw=5, os_lim=None, ob_lim=None, atr=None):
    n = len(price); pv = price.values.astype(float); ov = osc.values.astype(float)
    if atr is not None and len(atr) > 0:
        atr_pct = atr/(price+1e-10)*100
        atr_ratio = atr_pct/(atr_pct.rolling(100, min_periods=20).median()+1e-10)
        lb_scale = np.clip(1.3-0.35*atr_ratio.values, 0.5, 1.5)
        dynamic_lb = np.clip(lb*lb_scale, 30, 90).astype(int)
    else: dynamic_lb = np.full(n, lb, dtype=int)
    if atr is not None:
        prom_val = max(np.nanmean(np.nan_to_num((atr.rolling(20, min_periods=5).mean()*0.3).values, nan=0.01)), 0.01)
    else: prom_val = max(np.percentile(np.abs(np.diff(pv, prepend=pv[0])), 75)*2, 0.01)
    lows_idx, _ = find_peaks(-pv, distance=pw, prominence=prom_val)
    highs_idx, _ = find_peaks(pv, distance=pw, prominence=prom_val)
    bd = np.zeros(n, dtype=bool); brd = np.zeros(n, dtype=bool)
    hb = np.zeros(n, dtype=bool); hbr = np.zeros(n, dtype=bool)
    for i in range(1, len(lows_idx)):
        ci, pi = lows_idx[i], lows_idx[i-1]
        dlb = dynamic_lb[ci] if ci < n else lb
        gap = ci-pi
        if gap < pw*2 or gap > dlb: continue
        if pv[ci] < pv[pi] and ov[ci] > ov[pi]:
            if os_lim is None or ov[ci] <= os_lim: bd[min(ci+pw, n-1)] = True
        if pv[ci] > pv[pi] and ov[ci] < ov[pi]: hb[min(ci+pw, n-1)] = True
    for i in range(1, len(highs_idx)):
        ci, pi = highs_idx[i], highs_idx[i-1]
        dlb = dynamic_lb[ci] if ci < n else lb
        gap = ci-pi
        if gap < pw*2 or gap > dlb: continue
        if pv[ci] > pv[pi] and ov[ci] < ov[pi]:
            if ob_lim is None or ov[ci] >= ob_lim: brd[min(ci+pw, n-1)] = True
        if pv[ci] < pv[pi] and ov[ci] > ov[pi]: hbr[min(ci+pw, n-1)] = True
    return (pd.Series(bd, index=price.index), pd.Series(brd, index=price.index),
            pd.Series(hb, index=price.index), pd.Series(hbr, index=price.index))


# ══════════════════════════════════════════
#  Volume Profile + Relative Strength
# ══════════════════════════════════════════
def compute_volume_profile(h, l, c, v, lookback=20, num_bins=30):
    n = len(c); poc = np.full(n, np.nan); vah = np.full(n, np.nan); val_a = np.full(n, np.nan)
    c_v, h_v, l_v, v_v = c.values, h.values, l.values, v.values
    for i in range(lookback, n):
        s = i-lookback; h_w, l_w, v_w = h_v[s:i+1], l_v[s:i+1], v_v[s:i+1]
        plo, phi = l_w.min(), h_w.max()
        if phi-plo < 1e-10: poc[i] = c_v[i]; vah[i] = phi; val_a[i] = plo; continue
        tp = (h_w+l_w+c_v[s:i+1])/3
        vp, be = np.histogram(tp, bins=num_bins, range=(plo, phi), weights=v_w)
        bc = (be[:-1]+be[1:])/2; pb = np.argmax(vp); poc[i] = bc[pb]
        tv = vp.sum(); target = tv*0.70; cum = vp[pb]; lo_i, hi_i = pb, pb
        while cum < target and (lo_i > 0 or hi_i < num_bins-1):
            lv = vp[lo_i-1] if lo_i > 0 else 0; hv = vp[hi_i+1] if hi_i < num_bins-1 else 0
            if lv >= hv and lo_i > 0: lo_i -= 1; cum += lv
            elif hi_i < num_bins-1: hi_i += 1; cum += hv
            else: break
        vah[i] = be[min(hi_i+1, num_bins)]; val_a[i] = be[lo_i]
    return pd.Series(poc, index=c.index), pd.Series(vah, index=c.index), pd.Series(val_a, index=c.index)

def compute_relative_strength(df, spy_df, period=20):
    sc = df['Close'].copy(); spy_c = spy_df['Close'].reindex(sc.index, method='ffill')
    if spy_c.isna().all():
        for k in ['RS_Ratio','RS_Momentum','RS_Defense','SPY_Return','Stock_Return']: df[k] = 0.0
        df['RS_Ratio'] = 1.0; return df
    sr = sc.pct_change(period).fillna(0); spr = spy_c.pct_change(period).fillna(0)
    df['Stock_Return'] = sr; df['SPY_Return'] = spr
    df['RS_Ratio'] = ((1+sr)/(1+spr+1e-10)).rolling(10, min_periods=5).mean()
    df['RS_Momentum'] = df['RS_Ratio'] - df['RS_Ratio'].shift(5)
    df['RS_Defense'] = ((spr < -0.02) & (sr > spr)).astype(float).rolling(10, min_periods=3).mean()
    return df

def detect_relative_strength_signals(df):
    rs = df.get('RS_Ratio', pd.Series(1.0, index=df.index))
    rm = df.get('RS_Momentum', pd.Series(0.0, index=df.index))
    rd = df.get('RS_Defense', pd.Series(0.0, index=df.index))
    spr = df.get('SPY_Return', pd.Series(0.0, index=df.index))
    df['Relative_Strength_Buy'] = (rs>1.03)&(rm>0.01)&(rd>0.3)&(spr<0)&(df['Close']>df['Close'].shift(1))
    df['Relative_Strength_Sell'] = (rs<0.97)&(rm<-0.01)&(spr>0)&(df['Close']<df['Close'].shift(1))
    return df


# ══════════════════════════════════════════
#  선행 지표
# ══════════════════════════════════════════
def compute_momentum_acceleration(df):
    rv = df['RSI']-df['RSI'].shift(3); df['RSI_Accel'] = rv-rv.shift(3)
    wv = df['WT1']-df['WT1'].shift(3); df['WT_Accel'] = wv-wv.shift(3)
    df['MACD_Accel'] = df['MACD_Hist']-df['MACD_Hist'].shift(3)
    rn = df['RSI_Accel']/(df['RSI_Accel'].rolling(50, min_periods=10).std()+1e-10)
    wn = df['WT_Accel']/(df['WT_Accel'].rolling(50, min_periods=10).std()+1e-10)
    mn = df['MACD_Accel']/(df['MACD_Accel'].rolling(50, min_periods=10).std()+1e-10)
    df['Composite_Accel'] = (rn+wn+mn)/3; return df

def compute_convergence_speed(df):
    gap = df['WT1']-df['WT2']; ga = gap.abs()
    df['WT_Gap'] = gap; df['WT_Gap_Abs'] = ga; df['WT_Conv_Speed'] = ga.shift(3)-ga
    df['WT_Conv_Bull'] = (gap<0)&(df['WT_Conv_Speed']>JT.CONVERGENCE_SLOW)&(df['WT1']<20)
    df['WT_Conv_Bear'] = (gap>0)&(df['WT_Conv_Speed']>JT.CONVERGENCE_SLOW)&(df['WT1']>-20)
    return df

def compute_setup_pressure(df):
    idx = df.index; bb_w = df.get('BB_Width', pd.Series(0, index=idx))
    bb_wm = bb_w.rolling(50, min_periods=10).mean()
    vr = df['Volume']/(df['Volume'].rolling(20, min_periods=5).mean()+1e-10)
    vds = _vectorized_streak(vr < 0.7); rmfi = df['RSI_MFI']
    ca = df.get('Composite_Accel', pd.Series(0, index=idx))

    bp = pd.Series(0.0, index=idx)
    bp += np.where(df['WT1']<-40, 2.0, np.where(df['WT1']<-20, 1.0, 0))
    bp += np.where(df['RSI']<35, 1.5, np.where(df['RSI']<45, 0.5, 0))
    bp += np.where(df['StochK']<25, 1.0, 0)
    bp += np.where(ca>JT.ACCEL_MODERATE, 2.0, np.where(ca>0.5, 1.0, 0))
    bp += np.where(df.get('WT_Conv_Bull', pd.Series(False, index=idx)), 1.5, 0)
    bp += np.where(bb_w<bb_wm*0.7, 1.5, np.where(bb_w<bb_wm, 0.5, 0))
    bp += np.where(vds>=3, 1.0, 0)
    bp += np.where((rmfi<0)&(rmfi>rmfi.shift(3)), 1.0, 0)
    df['Setup_Pressure_Buy'] = bp

    sp = pd.Series(0.0, index=idx)
    sp += np.where(df['WT1']>40, 2.0, np.where(df['WT1']>20, 1.0, 0))
    sp += np.where(df['RSI']>65, 1.5, np.where(df['RSI']>55, 0.5, 0))
    sp += np.where(df['StochK']>75, 1.0, 0)
    sp += np.where(ca<-JT.ACCEL_MODERATE, 2.0, np.where(ca<-0.5, 1.0, 0))
    sp += np.where(df.get('WT_Conv_Bear', pd.Series(False, index=idx)), 1.5, 0)
    sp += np.where(bb_w<bb_wm*0.7, 1.5, np.where(bb_w<bb_wm, 0.5, 0))
    sp += np.where(vds>=3, 1.0, 0)
    sp += np.where((rmfi>0)&(rmfi<rmfi.shift(3)), 1.0, 0)
    df['Setup_Pressure_Sell'] = sp
    return df

def detect_anticipation_signals(df):
    idx = df.index; bb_w = df.get('BB_Width', pd.Series(0, index=idx))
    sq_tight = bb_w <= bb_w.rolling(120, min_periods=20).quantile(0.1)
    mh = df['MACD_Hist']
    mtu = (mh<0)&(mh>mh.shift(1))&(mh.shift(1)>mh.shift(2))
    mtd = (mh>0)&(mh<mh.shift(1))&(mh.shift(1)<mh.shift(2))
    df['Setup_Squeeze_Bull'] = sq_tight&mtu&(df['WT1']<30)
    df['Setup_Squeeze_Bear'] = sq_tight&mtd&(df['WT1']>-30)
    ca = df.get('Composite_Accel', pd.Series(0, index=idx))
    rau = df.get('RSI_Accel', pd.Series(0, index=idx))>0
    wau = df.get('WT_Accel', pd.Series(0, index=idx))>0
    mau = df.get('MACD_Accel', pd.Series(0, index=idx))>0
    df['Momentum_Accel_Buy'] = rau&wau&mau&(ca>JT.ACCEL_MODERATE)&(df['WT1']<40)
    df['Momentum_Accel_Sell'] = (~rau)&(~wau)&(~mau)&(ca<-JT.ACCEL_MODERATE)&(df['WT1']>-40)
    vr = df['Volume']/(df['Volume'].rolling(20, min_periods=5).mean()+1e-10)
    df['Volume_Dry_Up'] = _vectorized_streak(vr<0.6) >= 5
    cs = df.get('WT_Conv_Speed', pd.Series(0, index=idx))
    ga = df.get('WT_Gap_Abs', pd.Series(999, index=idx))
    df['WT_Convergence_Bull'] = (cs>JT.CONVERGENCE_FAST)&(ga>2)&(ga<15)&(df['WT1']<df['WT2'])&(df['WT1']<20)
    df['WT_Convergence_Bear'] = (cs>JT.CONVERGENCE_FAST)&(ga>2)&(ga<15)&(df['WT1']>df['WT2'])&(df['WT1']>-20)
    return df


# ══════════════════════════════════════════
#  시장 국면 인식 (5단계 Regime Detector)
# ══════════════════════════════════════════
def compute_market_regime(df):
    C = df['Close']; idx = df.index
    score = pd.Series(0.0, index=idx)
    score += np.where(C>df['MA200'], 1.0, -1.0)
    score += np.where(C>df['MA50'], 1.0, -1.0)
    score += np.where(C>df['MA20'], 0.5, -0.5)
    score += np.where(df['MA50']>df['MA50'].shift(10), 1.0, -1.0)
    score += np.where(df['ST_Direction']==1, 1.0, -1.0)
    score += np.where(df['Plus_DI']>df['Minus_DI'], 0.5, -0.5)
    score += np.where(df['ADX']>25, 0.5*np.sign(df['Plus_DI']-df['Minus_DI']), 0)
    score += np.where(df['MACD_Line']>0, 0.5, -0.5)
    score += np.where(df['MACD_Hist']>df['MACD_Hist'].shift(1), 0.3, -0.3)
    ret_20 = (C-C.shift(20))/(C.shift(20)+1e-10)
    score += np.where(ret_20>0.15, 1.5, np.where(ret_20>0.05, 0.5, np.where(ret_20<-0.15, -1.5, np.where(ret_20<-0.05, -0.5, 0))))
    regime_raw = score.rolling(5, min_periods=3).mean()
    df['Regime_Score'] = regime_raw.clip(-8, 8)
    df['Regime'] = np.select([regime_raw>=4, regime_raw>=1.5, regime_raw<=-4, regime_raw<=-1.5], [2,1,-2,-1], default=0)
    df['Strong_Bull'] = df['Regime']>=2; df['Strong_Bear'] = df['Regime']<=-2
    df['In_Uptrend'] = df['Regime']>=1; df['In_Downtrend'] = df['Regime']<=-1
    rs = df['Regime']-df['Regime'].shift(5)
    df['Breakout_Up'] = (rs>=2)&(df['Regime']>=1)
    df['Breakout_Down'] = (rs<=-2)&(df['Regime']<=-1)
    df['Slow_Bleed'] = (ret_20<-0.05)&(df['ADX']<20)&(C<df['MA50'])
    return df


# ══════════════════════════════════════════
#  주봉 추세 스코어
# ══════════════════════════════════════════
def compute_weekly_trend_score(df):
    c = df['Close']
    wd = np.sign(c-c.shift(5)); md = np.sign(c-c.shift(20)); qd = np.sign(c-c.shift(60))
    am = (c>df['MA100']).astype(int)
    df['Weekly_Trend_Score'] = wd+md+qd+am
    df['Weekly_Bullish'] = df['Weekly_Trend_Score']>=JT.WEEKLY_BULL_THRESH
    df['Weekly_Bearish'] = df['Weekly_Trend_Score']<=JT.WEEKLY_BEAR_THRESH
    return df


# ══════════════════════════════════════════
#  지표 통합 계산
# ══════════════════════════════════════════
def compute_indicators(df):
    c, h, l, v = df['Close'], df['High'], df['Low'], df['Volume']
    for ma in [5,10,20,50,100,125,200]: df[f'MA{ma}'] = c.rolling(ma).mean()
    df['EMA8'] = c.ewm(span=8, adjust=False).mean(); df['EMA21'] = c.ewm(span=21, adjust=False).mean()
    df['BB_Mid'] = df['MA20']; s20 = c.rolling(20).std()
    df['BB_Up'], df['BB_Low'] = df['BB_Mid']+s20*2, df['BB_Mid']-s20*2
    df['BB_Width'] = (df['BB_Up']-df['BB_Low'])/(df['BB_Mid']+1e-10)
    df['Percent_B'] = (c-df['BB_Low'])/(df['BB_Up']-df['BB_Low']+1e-10)
    tr = compute_tr(h, l, c)
    df['ATR'] = tr.rolling(14).mean()
    atr22 = tr.rolling(22).mean()
    df['Chandelier_Long'] = h.rolling(22).max()-atr22*3.0
    df['Chandelier_Short'] = l.rolling(22).min()+atr22*3.0
    df['SuperTrend'], df['ST_Direction'] = compute_supertrend(h, l, c, tr)
    atr_kc = tr.rolling(10).mean(); mid_kc = c.ewm(span=20, adjust=False).mean()
    df['KC_Upper'] = mid_kc+atr_kc*1.5; df['KC_Mid'] = mid_kc; df['KC_Lower'] = mid_kc-atr_kc*1.5
    wt1, wt2, wu, wd = compute_wavetrend(h, l, c)
    df['WT1'], df['WT2'], df['WT_Up'], df['WT_Down'] = wt1, wt2, wu, wd
    df['RSI'] = compute_rsi(c, 14); df['StochK'], df['StochD'] = compute_stoch_rsi(c)
    df['MFI'] = compute_mfi(h,l,c,v,14); df['RSI_MFI'] = compute_rsi_mfi(h,l,c,v,60)
    vwap = (c*v).rolling(20).sum()/(v.rolling(20).sum()+1e-10)
    df['VWAP_Osc'] = ((c-vwap)/(vwap+1e-10))*100
    df['ADX'], df['Plus_DI'], df['Minus_DI'] = compute_adx(h, l, c)
    df['OBV'] = compute_obv(c, v)
    df['MACD_Line'], df['MACD_Signal'], df['MACD_Hist'] = compute_macd(c)
    tk, kj, sa, sb, ch = compute_ichimoku(h, l, c)
    df['Ichimoku_Tenkan']=tk; df['Ichimoku_Kijun']=kj; df['Ichimoku_SenkouA']=sa; df['Ichimoku_SenkouB']=sb
    df['CMF'] = compute_cmf(h,l,c,v,20)
    df = compute_momentum_acceleration(df); df = compute_convergence_speed(df); df = compute_setup_pressure(df)
    df['VP_POC'], df['VP_VAH'], df['VP_VAL'] = compute_volume_profile(h,l,c,v,lookback=20,num_bins=30)
    try:
        spy = fetch_spy_history()
        if not spy.empty: df = compute_relative_strength(df, spy, 20)
    except:
        for k in ['RS_Ratio','RS_Momentum','RS_Defense','SPY_Return','Stock_Return']: df[k] = 0.0
        df['RS_Ratio'] = 1.0
    df = compute_weekly_trend_score(df)
    df = compute_market_regime(df)
    return df


# ══════════════════════════════════════════
#  패턴 탐지 함수
# ══════════════════════════════════════════
def detect_ttm_squeeze(bbu, bbl, kcu, kcl, c, h, l, kcm):
    sq = (bbu<kcu)&(bbl>kcl); fire = (~sq)&sq.shift(1).fillna(False)
    mom = c-((h.rolling(20).max()+l.rolling(20).min())/2+kcm)/2
    return sq, fire&(mom>0)&(mom>mom.shift(1)), fire&(mom<0)&(mom<mom.shift(1))

def detect_volume_climax(c, o, v, wt1, atr, z=2.5):
    vm = v.rolling(20).mean(); vs = v.rolling(20).std(); vz = (v-vm)/(vs+1e-10)
    big = (c-o).abs()>atr*0.5; ps = (vz.shift(1)>z)&big.shift(1)
    return ps&(c.shift(1)<o.shift(1))&(wt1.shift(1)<-40)&(c>o), ps&(c.shift(1)>o.shift(1))&(wt1.shift(1)>40)&(c<o)

def _detect_engulfing_pair(c, o, wt1, ma50, wt_t=20):
    body = (c-o).abs(); bp = (c.shift(1)-o.shift(1)).abs(); ab = body.rolling(20).mean()
    big = (body>ab*0.8)&(body>bp)
    pbh = pd.concat([c.shift(1),o.shift(1)],axis=1).max(axis=1)
    pbl = pd.concat([c.shift(1),o.shift(1)],axis=1).min(axis=1)
    cbh = pd.concat([c,o],axis=1).max(axis=1); cbl = pd.concat([c,o],axis=1).min(axis=1)
    below_ma = c<ma50; above_ma = c>ma50
    bull = ((c.shift(1)<o.shift(1))&(c>o)&(cbl<=pbl)&(cbh>=pbh)&big&(wt1<-wt_t)&(below_ma|(wt1<-40)))
    bear = ((c.shift(1)>o.shift(1))&(c<o)&(cbl<=pbl)&(cbh>=pbh)&big&(wt1>wt_t)&(above_ma|(wt1>40)))
    return bull, bear

def _detect_parabolic_pair(c, o, wt1, bbu, bbl, atr):
    return (((wt1<-80)&(wt1>wt1.shift(1))&(c>o)&(c>c.shift(1)))|((c<bbl-atr*1.5)&(c>o)),
            ((wt1>80)&(wt1<wt1.shift(1))&(c<o)&(c<c.shift(1)))|((c>bbu+atr*1.5)&(c<o)))

def _detect_ema_pullback_pair(c, h, l, v, e8, e21, atr, wt1, wt2):
    vok = _volf(v, 0.5); ar = atr/(c+1e-10); results = {}
    for d in ['buy','sell']:
        slope = e21>e21.shift(5) if d=='buy' else e21<e21.shift(5)
        trend = ((e8>e21) if d=='buy' else (e8<e21))&slope
        side = (c>e8) if d=='buy' else (c<e8)
        if d=='buy':
            t = (l<=e8*(1+ar*0.15))&(l>=e21*(1-ar*0.25)); tr_ = _recent(t,2)
            b = (c>=e8)&(c>h.shift(1)); wok = (wt1>wt1.shift(1))&(wt1>wt2)&(wt1<60)
        else:
            t = (h>=e8*(1-ar*0.15))&(h<=e21*(1+ar*0.25)); tr_ = _recent(t,2)
            b = (c<=e8)&(c<l.shift(1)); wok = (wt1<wt1.shift(1))&(wt1<wt2)&(wt1>-60)
        results[d] = trend&side&tr_&b&wok&vok
    return results['buy'], results['sell']

def _detect_mom_ignition_pair(c, o, v, bbu, bbl, atr, e8, e21, wt1, bb_w):
    body = (c-o).abs(); bb = body>atr*1.5; hv = v>v.rolling(20).mean()*2.0
    comp = bb_w.shift(1)<bb_w.rolling(20).mean().shift(1)
    return (c>o)&bb&hv&(c>bbu)&(e8>e21)&(wt1<50)&comp, (c<o)&bb&hv&(c<bbl)&(e8<e21)&(wt1>-50)&comp

def _detect_vwap_pair(c, vosc, wt1, wt2, v, atr):
    vok = _volf(v,0.7); ap = (atr/(c+1e-10)*100).clip(0.3,3.0); dt = (ap*0.3).clip(0.3,1.5)
    return (vosc>0)&(vosc.shift(1)<-dt)&(wt1>wt2)&(wt1<30)&vok, (vosc<0)&(vosc.shift(1)>dt)&(wt1<wt2)&(wt1>-30)&vok

def detect_candlestick_patterns(c, o, h, l, wt1, atr, v):
    body = (c-o).abs(); us = h-pd.concat([c,o],axis=1).max(axis=1)
    ls_ = pd.concat([c,o],axis=1).min(axis=1)-l; fr = h-l+1e-10
    ab = body.rolling(20).mean(); ism = body<ab*0.6; mr = atr*0.5
    vok = v>=v.rolling(10, min_periods=5).mean()*JT.VOL_FILTER_MIN
    vsurge = v>v.rolling(10, min_periods=5).mean()*JT.VOL_SURGE_RATIO
    ham = (ls_>=body*2)&(us<=body*0.3)&ism&(wt1<-20)&(c>=o)&(fr>mr)&vok
    sho = (us>=body*2)&(ls_<=body*0.3)&ism&(wt1>20)&(c<=o)&(fr>mr)&vok
    doji = (body<=fr*0.05)&(fr>atr*0.3)
    db = doji&(wt1<-30)&(wt1>wt1.shift(1))&(c.shift(1)<c.shift(3))&vok
    dbe = doji&(wt1>30)&(wt1<wt1.shift(1))&(c.shift(1)>c.shift(3))&vok
    d1b = (c.shift(2)<o.shift(2))&(body.shift(2)>ab.shift(2)); d2s = body.shift(1)<ab.shift(1)*0.5
    d3bu = (c>o)&(c>(o.shift(2)+c.shift(2))/2)&(body>ab*0.8)
    ms = d1b&d2s&d3bu&(wt1<-15)&vsurge
    d1bu = (c.shift(2)>o.shift(2))&(body.shift(2)>ab.shift(2))
    d3be = (c<o)&(c<(o.shift(2)+c.shift(2))/2)&(body>ab*0.8)
    es = d1bu&d2s&d3be&(wt1>15)&vsurge
    return ham, sho, db, dbe, ms, es

def detect_inside_outside_day(h, l, c, o, wt1):
    ins = (h<h.shift(1))&(l>l.shift(1)); out = (h>h.shift(1))&(l<l.shift(1))
    return ins, out&(c>o)&(c>h.shift(1))&(wt1<30), out&(c<o)&(c<l.shift(1))&(wt1>-30)

def detect_ma_crossovers(c, ma20, ma50, ma200):
    s = {}
    for tag, ma in [('20MA',ma20),('50MA',ma50),('200MA',ma200)]:
        s[f'Cross_Above_{tag}'] = (c>ma)&(c.shift(1)<=ma.shift(1))
        s[f'Fell_Below_{tag}'] = (c<ma)&(c.shift(1)>=ma.shift(1))
    return s

def detect_bb_extra(c, o, bbu, bbl, bbw, wt1):
    bwm = bbw.rolling(20).mean(); wid = (bbw>bbw.shift(1))&(bbw.shift(1)<bwm.shift(1))
    below = c<bbl
    return (c>bbu, below&(c>o)&(wt1>wt1.shift(1)), below&(c<o)&(wt1<wt1.shift(1)),
            wid&(c>c.shift(1))&(wt1>wt1.shift(1)), wid&(c<c.shift(1))&(wt1<wt1.shift(1)))

def detect_macd_centerline(ml):
    return (ml>0)&(ml.shift(1)<=0), (ml<0)&(ml.shift(1)>=0)

def detect_consecutive_days(c):
    up = c>c.shift(1); dn = c<c.shift(1)
    us = _vectorized_streak(up); ds = _vectorized_streak(dn)
    return {'Up_5_Days':us>=5,'Up_7_Days':us>=7,'Down_5_Days':ds>=5,'Down_7_Days':ds>=7}

def detect_gaps(c, o, h, l, atr):
    t = atr*0.5; gu = (o>h.shift(1))&((o-h.shift(1))>t); gd = (o<l.shift(1))&((l.shift(1)-o)>t)
    return gu, gd, gu.shift(1).fillna(False)&(l<=h.shift(2)), gd.shift(1).fillna(False)&(h>=l.shift(2))

def detect_nr7(h, l):
    dr = h-l; mn7 = dr.rolling(7).min(); nr = dr<=mn7; return nr, nr&nr.shift(1).fillna(False)

def detect_range_bars(h, l, atr):
    dr = h-l; wide = dr>atr*2.0; narrow = dr<atr*0.5
    rw = wide.rolling(5, min_periods=1).max().shift(1).fillna(False).astype(bool)
    return wide, rw&narrow

def detect_52w(c, h, l):
    hp = h.rolling(252, min_periods=200).max().shift(1)
    lp = l.rolling(252, min_periods=200).min().shift(1)
    return h>hp, l<lp

def detect_123_pullback(h, l, c, adx, pdi, mdi):
    sb = (adx>30)&(pdi>mdi); sbe = (adx>30)&(mdi>pdi)
    ins = (h<h.shift(1))&(l>l.shift(1))
    ll1=l<l.shift(1); ll2=l.shift(1)<l.shift(2); ll3=l.shift(2)<l.shift(3)
    tll=ll1&ll2&ll3; tli=(ll1&ll2&ins.shift(2))|(ll1&ins.shift(1)&ll2.shift(1))|(ins&ll1&ll2)
    hh1=h>h.shift(1); hh2=h.shift(1)>h.shift(2); hh3=h.shift(2)>h.shift(3)
    thh=hh1&hh2&hh3; thi=(hh1&hh2&ins.shift(2))|(hh1&ins.shift(1)&hh2.shift(1))|(ins&hh1&hh2)
    return sb&(tll|tli), sbe&(thh|thi)

def detect_180_setup(c, o, h, l, ma10, ma50):
    dr=h-l+1e-10; cp=(c-l)/dr; pp=(c.shift(1)-l.shift(1))/(h.shift(1)-l.shift(1)+1e-10)
    return (pp<=0.25)&(cp>=0.75)&(c>ma10)&(c>ma50), (pp>=0.75)&(cp<=0.25)&(c<ma10)&(c<ma50)

def detect_boomer(h, l, adx, pdi, mdi):
    ins=(h<h.shift(1))&(l>l.shift(1)); in2=ins&ins.shift(1)
    return in2.shift(1).fillna(False)&(adx>30)&(pdi>mdi), in2.shift(1).fillna(False)&(adx>30)&(mdi>pdi)

def detect_expansion(h, l, c):
    dr=h-l; mr9=dr.rolling(9).max(); h60=h.rolling(60,min_periods=40).max(); l60=l.rolling(60,min_periods=40).min()
    return (h>=h60)&(dr>=mr9), (l<=l60)&(dr>=mr9)

def detect_gilligans(o, c, h, l):
    dr=h-l+1e-10; cp=(c-l)/dr; l60=l.rolling(60,min_periods=40).min(); h60=h.rolling(60,min_periods=40).max()
    return (o<=l60)&(o<l.shift(1))&(cp>=0.5)&(c>=o), (o>=h60)&(o>h.shift(1))&(cp<=0.5)&(c<=o)

def detect_lizard(o, c, h, l):
    dr=h-l+1e-10; cp=(c-l)/dr; op=(o-l)/dr
    return (cp>=0.75)&(op>=0.75)&(l<=l.rolling(10).min()), (cp<=0.25)&(op<=0.25)&(h>=h.rolling(10).max())

def detect_non_adx_123(h, l, c, ma50):
    ins=(h<h.shift(1))&(l>l.shift(1))
    ll1=l<l.shift(1); ll2=l.shift(1)<l.shift(2)
    tll=ll1&ll2&(l.shift(2)<l.shift(3)); tli=(ll1&ll2&ins.shift(2))|(ll1&ins.shift(1)&ll2.shift(1))|(ins&ll1&ll2)
    hh1=h>h.shift(1); hh2=h.shift(1)>h.shift(2)
    thh=hh1&hh2&(h.shift(2)>h.shift(3)); thi=(hh1&hh2&ins.shift(2))|(hh1&ins.shift(1)&hh2.shift(1))|(ins&hh1&hh2)
    return (c>ma50)&(tll|tli), (c<ma50)&(thh|thi)

def detect_pocket_pivot(c, o, v, ma50, ma200):
    dv = v.where(c<c.shift(1), 0)
    return (c>o)&(v>dv.rolling(10).max())&(c>ma50)&(c>c.shift(1))

def detect_ichimoku_signals(c, tk, kj, sa, sb):
    kt = pd.concat([sa,sb],axis=1).max(axis=1); kb = pd.concat([sa,sb],axis=1).min(axis=1)
    return ((c>kt)&(c.shift(1)<=kt.shift(1))&(tk>kj), (c<kb)&(c.shift(1)>=kb.shift(1))&(tk<kj),
            (tk>kj)&(tk.shift(1)<=kj.shift(1))&(c>kt), (tk<kj)&(tk.shift(1)>=kj.shift(1))&(c<kb))

def detect_cmf_signals(cmf, c, ma50):
    return (cmf>0.1)&(cmf.shift(1)<=0.1)&(c>ma50), (cmf<-0.1)&(cmf.shift(1)>=-0.1)&(c<ma50)

def detect_mf_signals(c, rmfi):
    mcb=(rmfi>0)&(rmfi.shift(1)<=0); mcs=(rmfi<0)&(rmfi.shift(1)>=0)
    mr=rmfi>rmfi.shift(1); mf_=rmfi<rmfi.shift(1)
    mus=_vectorized_streak(mr); mds=_vectorized_streak(mf_)
    ms5=rmfi-rmfi.shift(5); ms10=rmfi-rmfi.shift(10)
    pl=c<c.rolling(5).min().shift(1); mh=rmfi>rmfi.rolling(5).min().shift(1)
    mbd=pl&mh&(rmfi<0)
    ph=c>c.rolling(5).max().shift(1); ml=rmfi<rmfi.rolling(5).max().shift(1)
    mbrd=ph&ml&(rmfi>0)
    return {'MF_Cross_Bull':mcb,'MF_Cross_Bear':mcs,'MF_Strong_Up':mus>=3,'MF_Strong_Dn':mds>=3,
            'MF_Accel_Up':mus>=5,'MF_Accel_Dn':mds>=5,'MF_Slope_5':ms5,'MF_Slope_10':ms10,
            'MF_Bull_Div':mbd,'MF_Bear_Div':mbrd,'MF_Rising':mr,'MF_Falling':mf_,
            'MF_Up_Streak':mus,'MF_Dn_Streak':mds}

def _deduplicate(df):
    for _, sigs in SIGNAL_HIERARCHY.items():
        for i, s in enumerate(sigs):
            if s not in df.columns: continue
            for higher in sigs[:i]:
                if higher in df.columns: df[s] = df[s]&~df[higher]
    return df


# ══════════════════════════════════════════
#  통합 시그널 탐지
# ══════════════════════════════════════════
def detect_all_signals(df):
    H,L,C,O,V = df['High'],df['Low'],df['Close'],df['Open'],df['Volume']
    e8,e21 = df['EMA8'],df['EMA21']
    m10,m20,m50,m200 = df['MA10'],df['MA20'],df['MA50'],df['MA200']
    wt1,wt2,atr = df['WT1'],df['WT2'],df['ATR']
    idx = df.index

    htf_ema_bull = (e8>e21)&(e21>e21.shift(5)); htf_ma_bull = (C>m50)&(m50>m50.shift(10))
    wt_up_r = _recent(df['WT_Up'],2); wt_dn_r = _recent(df['WT_Down'],2)
    wt_up_w = _recent(df['WT_Up'],3); wt_dn_w = _recent(df['WT_Down'],3)
    vol_ok = _volf(V, JT.VOL_FILTER_MIN)

    regime_bull = (df['ADX']>25)&(df['Plus_DI']>df['Minus_DI'])&(C>m50)
    regime_bear = (df['ADX']>25)&(df['Minus_DI']>df['Plus_DI'])&(C<m50)
    regime_ext_bull = regime_bull&(C>m200)&(m50>m50.shift(5))
    regime_ext_bear = regime_bear&(C<m200)&(m50<m50.shift(5))
    mf_pos = df['RSI_MFI']>-10; mf_neg = df['RSI_MFI']<10

    para_bot, para_top = _detect_parabolic_pair(C,O,wt1,df['BB_Up'],df['BB_Low'],atr)
    st_fb = (df['ST_Direction']==-1)&(df['ST_Direction'].shift(1)==1)
    st_fb.iloc[:ST_MIN_BAR] = False; st_br = _recent(st_fb,3)
    st_fu = (df['ST_Direction']==1)&(df['ST_Direction'].shift(1)==-1)
    st_fu.iloc[:ST_MIN_BAR] = False; st_ur = _recent(st_fu,3)

    sell_sh = regime_bull&(~para_top)&(~st_br); buy_sh = regime_bear&(~para_bot)&(~st_ur)
    sell_sh_ext = regime_ext_bull&(~para_top)&(~st_br); buy_sh_ext = regime_ext_bear&(~para_bot)&(~st_ur)

    # MF
    mfs = detect_mf_signals(C, df['RSI_MFI'])
    df['MF_Cross_Bull'] = mfs['MF_Cross_Bull']&(~buy_sh)&vol_ok
    df['MF_Cross_Bear'] = mfs['MF_Cross_Bear']&(~sell_sh)&vol_ok
    df['MF_Bull_Div'] = mfs['MF_Bull_Div']&(~buy_sh)&vol_ok
    df['MF_Bear_Div'] = mfs['MF_Bear_Div']&(~sell_sh)&vol_ok
    for k in ['MF_Accel_Up','MF_Accel_Dn','MF_Slope_5','MF_Slope_10','MF_Rising',
              'MF_Falling','MF_Strong_Up','MF_Strong_Dn','MF_Up_Streak','MF_Dn_Streak']:
        df[k] = mfs[k]

    # MCB+
    df['Green_Dot_T1'] = wt_up_r&(wt1<=OS1)&(df['RSI']<30)&(df['MFI']<30)&(df['RSI_MFI']<0)&(~buy_sh_ext)&vol_ok
    df['Green_Dot_T2'] = wt_up_r&(wt1<=OS1)&((df['RSI']<32)|(df['MFI']<32))&~df['Green_Dot_T1']&(~buy_sh)&vol_ok
    any_g = df['Green_Dot_T1']|df['Green_Dot_T2']
    df['Red_Dot_T1'] = wt_dn_r&(wt1>=OB1)&(df['RSI']>70)&(df['MFI']>70)&(df['RSI_MFI']>0)&(~sell_sh_ext)&vol_ok
    df['Red_Dot_T2'] = wt_dn_r&(wt1>=OB1)&((df['RSI']>68)|(df['MFI']>68))&~df['Red_Dot_T1']&(~sell_sh)&vol_ok
    any_r = df['Red_Dot_T1']|df['Red_Dot_T2']
    df['Blue_Diamond'] = (wt2<=0)&wt_up_r&htf_ema_bull&htf_ma_bull&(~buy_sh)&mf_pos&vol_ok
    df['Red_Diamond'] = (wt2>=0)&wt_dn_r&~htf_ema_bull&~htf_ma_bull&(~sell_sh)&mf_neg&vol_ok
    df['Green_Circle'] = wt_up_r&(wt1<=OS1)&~any_g&(~buy_sh)&vol_ok&(df['RSI']<45)
    df['Red_Circle'] = wt_dn_r&(wt1>=OB1)&~any_r&(~sell_sh)&vol_ok&(df['RSI']>55)

    # 다이버전스
    bd,brd,hb,hbr = detect_pivot_div(C,wt1,60,5,OS1,OB1,atr=atr)
    bd_r = _recent(bd,3); brd_r = _recent(brd,3)
    rbd,rbrd,_,_ = detect_pivot_div(C,df['RSI'],60,5,35,65,atr=atr)
    obd,obrd,_,_ = detect_pivot_div(C,df['OBV'],60,5,atr=atr)
    df['Gold_Dot'] = df['Green_Dot_T1']&(wt1<=OS2)&bd_r
    df['Blood_Diamond'] = df['Red_Dot_T1']&(wt1>=OB2)&brd_r
    df['Bull_Divergence'] = bd&wt_up_w&~any_g&~df['Gold_Dot']&(~buy_sh)&vol_ok
    df['Bear_Divergence'] = brd&wt_dn_w&~any_r&(~sell_sh)&vol_ok
    df['RSI_Bull_Divergence'] = rbd&(wt1<-20)&(~buy_sh)&vol_ok&~bd
    df['RSI_Bear_Divergence'] = rbrd&(wt1>20)&(~sell_sh)&vol_ok&~brd
    vol_s = _volf(V, JT.VOL_FILTER_STRONG)
    df['Hidden_Bull_Div'] = hb&(wt1<-25)&htf_ma_bull&(~buy_sh_ext)&vol_s
    df['Hidden_Bear_Div'] = hbr&(wt1>25)&~htf_ma_bull&(~sell_sh_ext)&vol_s
    df['OBV_Div_Buy'] = obd&(wt1<-30)&(~buy_sh_ext)
    df['OBV_Div_Sell'] = obrd&(wt1>30)&(~sell_sh_ext)

    # TTM, VolClimax, ADX
    sqo,sqb,sqs = detect_ttm_squeeze(df['BB_Up'],df['BB_Low'],df['KC_Upper'],df['KC_Lower'],C,H,L,df['KC_Mid'])
    df['Squeeze_On'] = sqo
    df['Squeeze_Fire_Buy'] = sqb&(~buy_sh)&vol_ok; df['Squeeze_Fire_Sell'] = sqs&(~sell_sh)&vol_ok
    df['Volume_Climax_Buy'],df['Volume_Climax_Sell'] = detect_volume_climax(C,O,V,wt1,atr)
    adx_x = (df['ADX']>20)&(df['ADX'].shift(1)<=20)
    df['ADX_Momentum_Buy'] = adx_x&(df['Plus_DI']>df['Minus_DI'])&(wt1>wt2)&vol_ok
    df['ADX_Momentum_Sell'] = adx_x&(df['Minus_DI']>df['Plus_DI'])&(wt1<wt2)&vol_ok

    # Engulfing
    df['Bullish_Engulfing'],df['Bearish_Engulfing'] = _detect_engulfing_pair(C,O,wt1,m50)
    df['Bullish_Engulfing'] &= (~buy_sh)&vol_ok; df['Bearish_Engulfing'] &= (~sell_sh)&vol_ok

    # Golden/Death, EMA PB, Mom Ign, ST, Parabolic, VWAP, MACD, StochRSI
    gc = (m50>m200)&(m50.shift(1)<=m200.shift(1)); dc_ = (m50<m200)&(m50.shift(1)>=m200.shift(1))
    af = df['ADX']>15; vc = _volf(V, JT.VOL_FILTER_STRONG)
    df['Golden_Cross'] = gc&af&vc; df['Death_Cross'] = dc_&af&vc
    df['EMA_Pullback_Buy'],df['EMA_Pullback_Sell'] = _detect_ema_pullback_pair(C,H,L,V,e8,e21,atr,wt1,wt2)
    df['Momentum_Ignition_Buy'],df['Momentum_Ignition_Sell'] = _detect_mom_ignition_pair(C,O,V,df['BB_Up'],df['BB_Low'],atr,e8,e21,wt1,df['BB_Width'])
    df['SuperTrend_Buy'] = st_fu; df['SuperTrend_Sell'] = st_fb
    vp_ = _volf(V,1.0)
    df['Parabolic_Top_Sell'] = para_top&((df['WT_Down']|wt_dn_w)|((C<O)&(C<C.shift(1))))&vp_
    df['Parabolic_Bottom_Buy'] = para_bot&((df['WT_Up']|wt_up_w)|((C>O)&(C>C.shift(1))))&vp_
    df['VWAP_Bounce_Buy'],df['VWAP_Reject_Sell'] = _detect_vwap_pair(C,df['VWAP_Osc'],wt1,wt2,V,atr)
    ml,ms = df['MACD_Line'],df['MACD_Signal']
    df['MACD_Cross_Buy'] = (ml>ms)&(ml.shift(1)<=ms.shift(1))&(ml<0)&(~buy_sh)&vol_ok
    df['MACD_Cross_Sell'] = (ml<ms)&(ml.shift(1)>=ms.shift(1))&(ml>0)&(~sell_sh)&vol_ok
    df['StochRSI_Cross_Buy'] = (df['StochK']>df['StochD'])&(df['StochK'].shift(1)<=df['StochD'].shift(1))&(df['StochK']<25)&(~buy_sh)&vol_ok
    df['StochRSI_Cross_Sell'] = (df['StochK']<df['StochD'])&(df['StochK'].shift(1)>=df['StochD'].shift(1))&(df['StochK']>75)&(~sell_sh)&vol_ok

    # 캔들스틱 (V 전달)
    (df['Hammer'],df['Shooting_Star'],df['Doji_Bullish'],df['Doji_Bearish'],
     df['Morning_Star'],df['Evening_Star']) = detect_candlestick_patterns(C,O,H,L,wt1,atr,V)
    for s in ['Hammer','Doji_Bullish','Morning_Star']: df[s] &= (~buy_sh)
    for s in ['Shooting_Star','Doji_Bearish','Evening_Star']: df[s] &= (~sell_sh)

    # 나머지 패턴
    df['Inside_Day'],df['Outside_Bullish'],df['Outside_Bearish'] = detect_inside_outside_day(H,L,C,O,wt1)
    df['Outside_Bullish'] &= (~buy_sh)&vol_ok; df['Outside_Bearish'] &= (~sell_sh)&vol_ok
    for k,v_ in detect_ma_crossovers(C,m20,m50,m200).items(): df[k] = v_
    (df['BB_Upper_Break'],df['BB_Lower_Bounce'],df['BB_Lower_Break'],
     df['BB_Squeeze_End_Bull'],df['BB_Squeeze_End_Bear']) = detect_bb_extra(C,O,df['BB_Up'],df['BB_Low'],df['BB_Width'],wt1)
    df['MACD_Zero_Cross_Buy'],df['MACD_Zero_Cross_Sell'] = detect_macd_centerline(df['MACD_Line'])
    for k,v_ in detect_consecutive_days(C).items(): df[k] = v_
    df['Gap_Up'],df['Gap_Down'],df['Gap_Up_Closed'],df['Gap_Down_Closed'] = detect_gaps(C,O,H,L,atr)
    df['NR7_2'] = detect_nr7(H,L)[1]
    df['Wide_Range_Bar'],df['Calm_After_Storm'] = detect_range_bars(H,L,atr)
    df['New_52W_High'],df['New_52W_Low'] = detect_52w(C,H,L)
    df['Pullback_123_Bull'],df['Pullback_123_Bear'] = detect_123_pullback(H,L,C,df['ADX'],df['Plus_DI'],df['Minus_DI'])
    df['Setup_180_Bull'],df['Setup_180_Bear'] = detect_180_setup(C,O,H,L,m10,m50)
    df['Boomer_Buy'],df['Boomer_Sell'] = detect_boomer(H,L,df['ADX'],df['Plus_DI'],df['Minus_DI'])
    df['Expansion_BO'],df['Expansion_BD'] = detect_expansion(H,L,C)
    df['Gilligans_Buy'],df['Gilligans_Sell'] = detect_gilligans(O,C,H,L)
    df['Lizard_Bull'],df['Lizard_Bear'] = detect_lizard(O,C,H,L)
    df['NonADX_123_Bull'],df['NonADX_123_Bear'] = detect_non_adx_123(H,L,C,m50)
    df['Pocket_Pivot'] = detect_pocket_pivot(C,O,V,m50,m200)
    (df['Kumo_Breakout_Bull'],df['Kumo_Breakout_Bear'],
     df['TK_Cross_Bull'],df['TK_Cross_Bear']) = detect_ichimoku_signals(
        C,df['Ichimoku_Tenkan'],df['Ichimoku_Kijun'],df['Ichimoku_SenkouA'],df['Ichimoku_SenkouB'])
    for s in ['Kumo_Breakout_Bull','TK_Cross_Bull','Kumo_Breakout_Bear','TK_Cross_Bear']: df[s] &= vol_ok
    df['CMF_Bull'],df['CMF_Bear'] = detect_cmf_signals(df['CMF'],C,m50)
    df['CMF_Bull'] &= vol_ok; df['CMF_Bear'] &= vol_ok

    # 선행 시그널
    df = detect_anticipation_signals(df)
    ab = any_g|df['Gold_Dot']|df['Squeeze_Fire_Buy']|df['Bullish_Engulfing']
    asf = any_r|df['Blood_Diamond']|df['Squeeze_Fire_Sell']|df['Bearish_Engulfing']
    df['Setup_Squeeze_Bull'] &= ~ab; df['Setup_Squeeze_Bear'] &= ~asf
    df['Momentum_Accel_Buy'] &= ~ab; df['Momentum_Accel_Sell'] &= ~asf
    df['WT_Convergence_Bull'] &= ~df['WT_Up']; df['WT_Convergence_Bear'] &= ~df['WT_Down']

    # VP 시그널
    if 'VP_POC' in df.columns:
        poc = df['VP_POC']; pp = poc.shift(1)
        df['Volume_POC_Breakout'] = (C>poc)&(C.shift(1)<=pp)&vol_s&(C>O)&(~buy_sh)&(wt1<50)
        df['Volume_POC_Breakdown'] = (C<poc)&(C.shift(1)>=pp)&vol_s&(C<O)&(~sell_sh)&(wt1>-50)
    if 'VP_VAH' in df.columns:
        vah_=df['VP_VAH']; val_=df['VP_VAL']; ap_=atr/(C+1e-10)
        nv = ((vah_-C).abs()/(C+1e-10))<ap_*0.5
        df['VP_VAH_Resistance'] = nv&(C<O)&(wt1>0)&(~sell_sh)&vol_ok
        nl = ((C-val_).abs()/(C+1e-10))<ap_*0.5
        df['VP_VAL_Support'] = nl&(C>O)&(wt1<0)&(~buy_sh)&vol_ok

    # RS
    df = detect_relative_strength_signals(df)
    df['Relative_Strength_Buy'] &= vol_ok&(~buy_sh)
    df['Relative_Strength_Sell'] &= vol_ok&(~sell_sh)

    # 쿨다운
    PAIRED = {
        ('MACD_Cross_Buy','MACD_Cross_Sell'):12,('StochRSI_Cross_Buy','StochRSI_Cross_Sell'):7,
        ('EMA_Pullback_Buy','EMA_Pullback_Sell'):7,('Momentum_Ignition_Buy','Momentum_Ignition_Sell'):10,
        ('VWAP_Bounce_Buy','VWAP_Reject_Sell'):7,('ADX_Momentum_Buy','ADX_Momentum_Sell'):10,
        ('Squeeze_Fire_Buy','Squeeze_Fire_Sell'):5,('Bullish_Engulfing','Bearish_Engulfing'):5,
        ('Hammer','Shooting_Star'):5,('Morning_Star','Evening_Star'):7,
        ('Doji_Bullish','Doji_Bearish'):5,('Outside_Bullish','Outside_Bearish'):7,
        ('BB_Squeeze_End_Bull','BB_Squeeze_End_Bear'):7,('MACD_Zero_Cross_Buy','MACD_Zero_Cross_Sell'):12,
        ('Pullback_123_Bull','Pullback_123_Bear'):7,('Setup_180_Bull','Setup_180_Bear'):7,
        ('Boomer_Buy','Boomer_Sell'):10,('Expansion_BO','Expansion_BD'):10,
        ('Gilligans_Buy','Gilligans_Sell'):10,('Lizard_Bull','Lizard_Bear'):5,
        ('NonADX_123_Bull','NonADX_123_Bear'):7,('MF_Cross_Bull','MF_Cross_Bear'):10,
        ('MF_Bull_Div','MF_Bear_Div'):10,('Kumo_Breakout_Bull','Kumo_Breakout_Bear'):10,
        ('TK_Cross_Bull','TK_Cross_Bear'):7,('CMF_Bull','CMF_Bear'):10,
        ('Setup_Squeeze_Bull','Setup_Squeeze_Bear'):3,('Momentum_Accel_Buy','Momentum_Accel_Sell'):5,
        ('WT_Convergence_Bull','WT_Convergence_Bear'):5,
        ('Volume_POC_Breakout','Volume_POC_Breakdown'):7,('VP_VAL_Support','VP_VAH_Resistance'):5,
        ('Relative_Strength_Buy','Relative_Strength_Sell'):10,
    }
    ph = set()
    for (bs,ss),cd in PAIRED.items():
        _cooldown_directional(df,bs,ss,cd); ph.add(bs); ph.add(ss)
    for s,cd in COOLDOWN_MAP.items():
        if s in df.columns and s not in ph: df[s] = _cooldown(df[s],cd)
    _deduplicate(df)

    compute_confluence(df)
    df['Buy_Proximity'],df['Sell_Proximity'] = compute_proximity(df)
    df['Parabolic_Blowoff'] = para_top; df['Parabolic_Bottom_Raw'] = para_bot
    df['ST_Bear_Override'] = st_br
    df['Sell_Shield_Overridden'] = para_top|st_br; df['Buy_Shield_Overridden'] = para_bot|st_ur
    df['_HTF1_Bull'] = htf_ema_bull; df['_HTF2_Bull'] = htf_ma_bull
    compute_trade_judgment(df)
    return df


# ══════════════════════════════════════════
#  Confluence
# ══════════════════════════════════════════
def compute_confluence(df, dw=5, df_=0.75):
    bm = {k:v['w'] for k,v in SIGNAL_REGISTRY.items() if v['dir']=='buy'}
    sm = {k:v['w'] for k,v in SIGNAL_REGISTRY.items() if v['dir']=='sell'}
    dk = np.array([df_**i for i in range(dw+1)]); ones = np.ones(dw+1)
    s = np.zeros(len(df)); bc = np.zeros(len(df)); sc = np.zeros(len(df))
    for col,w in bm.items():
        if col in df.columns:
            r = df[col].fillna(False).astype(float).values
            s += np.convolve(r*w, dk, mode='full')[:len(r)]
            bc += np.convolve(r, ones, mode='full')[:len(r)]
    for col,w in sm.items():
        if col in df.columns:
            r = df[col].fillna(False).astype(float).values
            s -= np.convolve(r*w, dk, mode='full')[:len(r)]
            sc += np.convolve(r, ones, mode='full')[:len(r)]
    wt1 = df['WT1'].values
    s += np.where(wt1<OS1,1.0,0)+np.where(wt1<OS2,0.5,0)
    s -= np.where(wt1>OB1,1.0,0)+np.where(wt1>OB2,0.5,0)
    adx=df['ADX'].values; pdi=df['Plus_DI'].values; mdi=df['Minus_DI'].values
    af = np.clip((adx-20)/100, 0.0, 0.3)
    s += np.where((pdi>mdi)&(s>0), s*af, 0); s -= np.where((mdi>pdi)&(s<0), abs(s)*af, 0)
    df['Confluence_Score'] = s
    df['Ultra_Buy'] = (s>=6.5)|((s>=5)&(bc>=3)); df['Ultra_Sell'] = (s<=-6.5)|((s<=-5)&(sc>=3))
    df['Strong_Buy'] = (s>=3.5)&(~df['Ultra_Buy']); df['Strong_Sell'] = (s<=-3.5)&(~df['Ultra_Sell'])
    return s


# ══════════════════════════════════════════
#  Proximity (국면 인식)
# ══════════════════════════════════════════
def compute_proximity(df):
    wt1,wt2,rsi,mfi = df['WT1'],df['WT2'],df['RSI'],df['MFI']
    rmfi,stk,mh = df['RSI_MFI'],df['StochK'],df['MACD_Hist']
    bb_w = df['BB_Width']
    regime = df.get('Regime', pd.Series(0, index=df.index))
    in_up = regime>=1; breakout_up = df.get('Breakout_Up', pd.Series(False, index=df.index))
    in_dn = regime<=-1; breakout_dn = df.get('Breakout_Down', pd.Series(False, index=df.index))

    bp = pd.Series(0.0, index=df.index); sp = pd.Series(0.0, index=df.index)
    gap = (wt1-wt2).abs(); nc = gap<3
    cu = (wt1-wt2)>(wt1.shift(1)-wt2.shift(1)); cd = (wt1-wt2)<(wt1.shift(1)-wt2.shift(1))

    for cond, pts in [((wt1<-40)&nc,30),((wt1<-40)&cu&(gap<8),15),(wt1<OS2,20),
        ((wt1>=OS2)&(wt1<-40),10),(rsi<35,15),((rsi>=35)&(rsi<45),5),(mfi<35,15),
        ((mfi>=35)&(mfi<45),5),(rmfi<-5,10),((rmfi>=-5)&(rmfi<0),5),(rmfi>rmfi.shift(1),5),
        (stk<20,10),((stk>=20)&(stk<35),5),(mh<0,3),(mh>mh.shift(1),2)]:
        bp += np.where(cond, pts, 0)

    # 매도 근접도 — 상승추세에서 과매수 할인
    sd = np.where(breakout_up|(in_up&(regime>=2)), 0.3, np.where(in_up, 0.6, 1.0))
    for cond, pts in [((wt1>40)&nc,30),((wt1>40)&cd&(gap<8),15),(wt1>OB1,20),
        ((wt1<=OB1)&(wt1>40),10),(rsi>65,15),((rsi<=65)&(rsi>55),5),(mfi>65,15),
        ((mfi<=65)&(mfi>55),5),(stk>80,10),((stk<=80)&(stk>65),5)]:
        sp += np.where(cond, pts*sd, 0)
    for cond, pts in [(rmfi>5,10),((rmfi<=5)&(rmfi>0),5),(rmfi<rmfi.shift(1),5),
        (mh>0,3),(mh<mh.shift(1),2)]:
        sp += np.where(cond, pts, 0)

    # 매수 근접도 — 하락추세에서 과매도 할인 (데드캣 방지)
    bd = np.where(breakout_dn|(in_dn&(regime<=-2)), 0.3, np.where(in_dn, 0.6, 1.0))
    reduction = pd.Series(0.0, index=df.index)
    for cond, pts in [(wt1<OS2,20),((wt1>=OS2)&(wt1<-40),10),(rsi<35,15),(mfi<35,15),(stk<20,10)]:
        orig = np.where(cond, pts, 0); reduction += orig - orig*bd
    bp -= reduction

    # 선행 지표
    ca = df.get('Composite_Accel', pd.Series(0, index=df.index))
    sb = df.get('Setup_Pressure_Buy', pd.Series(0, index=df.index))
    ss = df.get('Setup_Pressure_Sell', pd.Series(0, index=df.index))
    bp += np.where(ca>JT.ACCEL_STRONG,15,np.where(ca>JT.ACCEL_MODERATE,8,np.where(ca>0.5,3,0)))
    sp += np.where(ca<-JT.ACCEL_STRONG,15,np.where(ca<-JT.ACCEL_MODERATE,8,np.where(ca<-0.5,3,0)))
    bp += np.where(df.get('WT_Conv_Bull',pd.Series(False,index=df.index)),10,0)
    sp += np.where(df.get('WT_Conv_Bear',pd.Series(False,index=df.index)),10,0)
    bp += np.where(sb>=8,10,np.where(sb>=5,5,0)); sp += np.where(ss>=8,10,np.where(ss>=5,5,0))
    bbn = bb_w<bb_w.rolling(50,min_periods=10).quantile(0.2)
    bp += np.where(bbn,5,0); sp += np.where(bbn,5,0)
    return bp.clip(0,100), sp.clip(0,100)


# ══════════════════════════════════════════
#  콤보 감지
# ══════════════════════════════════════════
def detect_combos(df, vol_ratio):
    C,idx = df['Close'],df.index
    F = lambda col: df.get(col, pd.Series(False, index=idx))
    tu = (C>df['MA200'])&(C>df['MA50'])&(df['MA50']>df['MA200'])
    td = (C<df['MA200'])&(C<df['MA50'])&(df['MA50']<df['MA200'])
    cb = F('Bullish_Engulfing')|F('Hammer')|F('Morning_Star')|F('Doji_Bullish')
    cbe = F('Bearish_Engulfing')|F('Shooting_Star')|F('Evening_Star')|F('Doji_Bearish')
    tb = (df['StochK']<20)|F('StochRSI_Cross_Buy')|F('MACD_Cross_Buy')|(df['WT1']<-30)
    tbe = (df['StochK']>80)|F('StochRSI_Cross_Sell')|F('MACD_Cross_Sell')|(df['WT1']>30)
    vc = vol_ratio>=1.5; mfb = (df['RSI_MFI']>df['RSI_MFI'].shift(1))|(df['RSI_MFI']>0)
    mfbe = (df['RSI_MFI']<df['RSI_MFI'].shift(1))|(df['RSI_MFI']<0)
    sq = F('NR7_2')|F('Inside_Day')|F('Calm_After_Storm')|(df['BB_Width']<=df['BB_Width'].rolling(120,min_periods=20).quantile(0.1))
    cmf=df.get('CMF',pd.Series(0,index=idx)); cmfb=cmf>0.05; cmfbe=cmf<-0.05
    mas = ((C-df['MA50']).abs()<=df['ATR']*1.5)|((C-df['MA20']).abs()<=df['ATR']*1.0)
    ab = df.get('Setup_Pressure_Buy',pd.Series(0,index=idx))>=5
    abe = df.get('Setup_Pressure_Sell',pd.Series(0,index=idx))>=5

    df['Combo_TrendPullback_Buy'] = tu&(C<df['MA20'])&mas&(cb|tb)&mfb
    df['Combo_VolSqueeze_Buy'] = sq.shift(1).fillna(False)&(C>df['MA50'])&(F('BB_Squeeze_End_Bull')|(F('Wide_Range_Bar')&(C>df['Open'])))&vc&mfb
    oe = (((df['StochK']<20)&(df['StochD']<20)).astype(int)+(df['RSI']<30).astype(int)+(df['WT1']<-53).astype(int))>=2
    df['Combo_Reversal_Buy'] = oe&((C>df['MA200'])|(df['MA50']>df['MA200']))&(cb|F('Gold_Dot')|F('Green_Dot_T1')|F('Lizard_Bull')|F('Gilligans_Buy'))
    mfsb = F('MF_Strong_Up')|(df.get('MF_Slope_5',pd.Series(0,index=idx))>3)
    df['Combo_Momentum_Buy'] = (F('New_52W_High')|F('Expansion_BO'))&(vc|F('Pocket_Pivot')|F('Momentum_Ignition_Buy'))&(df['ADX']>25)&(df['Plus_DI']>df['Minus_DI'])&mfsb
    df['Combo_MAConfluence_Buy'] = (df['MA50']>df['MA200'])&(C>df['MA200'])&(F('Cross_Above_20MA')|F('Cross_Above_50MA'))&(F('MACD_Cross_Buy')|F('StochRSI_Cross_Buy')|F('NonADX_123_Bull'))&mfb
    df['Combo_MF_Reversal_Buy'] = F('MF_Cross_Bull')&(df['WT1']<20)&(C>df['MA50'])&(cb|tb|vc)
    df['Combo_Ichimoku_Buy'] = F('Kumo_Breakout_Bull')&(cb|tb|vc)&cmfb&(df['ADX']>20)
    df['Combo_Anticipation_Buy'] = ab&sq&(cmfb|mfb)&(F('WT_Convergence_Bull')|F('Momentum_Accel_Buy')|F('Setup_Squeeze_Bull'))
    df['Combo_TrendRejection_Sell'] = td&(C>df['MA20'])&(cbe|tbe)&mfbe
    ob = (((df['StochK']>80)&(df['StochD']>80)).astype(int)+(df['RSI']>70).astype(int)+(df['WT1']>53).astype(int))>=2
    df['Combo_Exhaustion_Sell'] = ob&(cbe|F('Gilligans_Sell')|F('Blood_Diamond')|F('Red_Dot_T1')|F('Parabolic_Top_Sell'))
    mab = (F('Fell_Below_20MA').astype(int)+F('Fell_Below_50MA').astype(int)+F('Fell_Below_200MA').astype(int)+F('Death_Cross').astype(int))>=1
    df['Combo_MABreakdown_Sell'] = mab&(vc|F('MACD_Zero_Cross_Sell')|(F('Wide_Range_Bar')&(C<df['Open'])))&mfbe
    df['Combo_VolSqueeze_Sell'] = sq.shift(1).fillna(False)&(C<df['MA50'])&(F('BB_Squeeze_End_Bear')|(F('Wide_Range_Bar')&(C<df['Open'])))&vc&mfbe
    guf = F('Gap_Up').shift(1).fillna(False)&(C<df['Open'])&(cbe|F('Gilligans_Sell'))
    df['Combo_GapFailure_Sell'] = guf|(F('Gap_Down')&vc&(F('Fell_Below_50MA')|F('Fell_Below_200MA')))
    df['Combo_MF_Reversal_Sell'] = F('MF_Cross_Bear')&(df['WT1']>-20)&(C<df['MA50'])&(cbe|tbe|vc)
    df['Combo_Ichimoku_Sell'] = F('Kumo_Breakout_Bear')&(cbe|tbe|vc)&cmfbe&(df['ADX']>20)
    df['Combo_Anticipation_Sell'] = abe&sq&(cmfbe|mfbe)&(F('WT_Convergence_Bear')|F('Momentum_Accel_Sell')|F('Setup_Squeeze_Bear'))

COMBO_MAP = {
    'Combo_TrendPullback_Buy':('🎯 추세 눌림목 매수','buy',2),
    'Combo_VolSqueeze_Buy':('💥 변동성 수축 돌파','buy',2),
    'Combo_Reversal_Buy':('🔄 반전 매수','buy',1),
    'Combo_Momentum_Buy':('🚀 모멘텀 돌파','buy',1),
    'Combo_MAConfluence_Buy':('📊 MA 합류 매수','buy',2),
    'Combo_MF_Reversal_Buy':('💰 자금흐름 전환 매수','buy',3),
    'Combo_Ichimoku_Buy':('☁️ 쿠모 돌파 매수','buy',2),
    'Combo_Anticipation_Buy':('⏳ 매수 셋업 임박','buy',3),
    'Combo_TrendRejection_Sell':('🎯 추세 반등 실패','sell',2),
    'Combo_Exhaustion_Sell':('🌡️ 고점 소진','sell',1),
    'Combo_MABreakdown_Sell':('📉 MA 붕괴','sell',2),
    'Combo_VolSqueeze_Sell':('💨 변동성 수축 붕괴','sell',2),
    'Combo_GapFailure_Sell':('⏬ 갭 실패','sell',2),
    'Combo_MF_Reversal_Sell':('💸 자금흐름 전환 매도','sell',3),
    'Combo_Ichimoku_Sell':('☁️ 쿠모 하향 매도','sell',2),
    'Combo_Anticipation_Sell':('⏳ 매도 셋업 임박','sell',3),
}


# ══════════════════════════════════════════
#  Adaptive Weighting (매수/매도 분리)
# ══════════════════════════════════════════
def _compute_regime_weights(df):
    idx = df.index; n = len(df)
    regime = df['Regime_Score'].values
    sq = df.get('Squeeze_On', pd.Series(False, index=idx)).fillna(False).values.astype(bool)
    names = ['Trend','Momentum','Candle','BB','Volume','MF','Pattern','Anticipation']
    wb = {nm: np.ones(n) for nm in names}; ws = {nm: np.ones(n) for nm in names}

    su = regime>=4; up = (regime>=1.5)&(regime<4); sd = regime<=-4; dn = (regime<=-1.5)&(regime>-4)
    rng = (regime>-1.5)&(regime<1.5)

    wb['Trend'][su]=1.4; wb['Pattern'][su]=1.3; wb['BB'][su]=0.6
    ws['Momentum'][su]=0.4; ws['Trend'][su]=0.5; ws['BB'][su]=0.5; ws['Pattern'][su]=0.7

    wb['Trend'][up]=1.2; wb['Pattern'][up]=1.1; ws['Momentum'][up]=0.65; ws['Trend'][up]=0.7

    ws['Trend'][sd]=1.4; ws['Pattern'][sd]=1.3; ws['BB'][sd]=0.6
    wb['Momentum'][sd]=0.4; wb['Trend'][sd]=0.5; wb['BB'][sd]=0.5; wb['Pattern'][sd]=0.7

    ws['Trend'][dn]=1.2; ws['Pattern'][dn]=1.1; wb['Momentum'][dn]=0.65; wb['Trend'][dn]=0.7

    for w in [wb, ws]:
        w['Trend'][rng]=0.5; w['Momentum'][rng]=1.4; w['BB'][rng]=1.5
        w['MF'][rng]=1.2; w['Anticipation'][rng]=1.3
        w['BB'][sq]=np.maximum(w['BB'][sq],1.6); w['Anticipation'][sq]=np.maximum(w['Anticipation'][sq],1.5)

    return ({nm: pd.Series(v, index=idx) for nm,v in wb.items()},
            {nm: pd.Series(v, index=idx) for nm,v in ws.items()})


# ══════════════════════════════════════════
#  다차원 Confidence
# ══════════════════════════════════════════
def _compute_confidence(b, s, bal, sal, judgment, atr_pct):
    diff = abs(b-s); dom = max(b, s)
    if 'STRONG' in judgment: margin = min((dom-JT.STRONG_BUY_SCORE)/JT.STRONG_BUY_SCORE*35, 35)
    elif judgment in ('BUY','SELL'): margin = min((dom-JT.BUY_SCORE)/JT.BUY_SCORE*30, 30)
    elif 'WATCH' in judgment: margin = min((dom-JT.WATCH_BUY_SCORE)/JT.WATCH_BUY_SCORE*20, 20)
    else: margin = 0
    active = bal if 'BUY' in judgment else (sal if 'SELL' in judgment else max(bal, sal))
    consensus = (active/NUM_LAYERS)*30
    ratio = b/(s+0.01) if 'BUY' in judgment else (s/(b+0.01) if 'SELL' in judgment else 1.0)
    ratio_sc = min(max((ratio-1.0)*10, 0), 20)
    vp = -15 if atr_pct>5.0 else (-8 if atr_pct>3.0 else (-3 if atr_pct>2.0 else 0))
    raw = margin+consensus+ratio_sc+vp
    if judgment in ('NEUTRAL','MIXED'): raw = max(10, 50-diff*5)
    return np.clip(raw, 5, 99)


# ══════════════════════════════════════════
#  8-Layer 판단 엔진
# ══════════════════════════════════════════
def compute_trade_judgment(df):
    C,O,H,L,idx = df['Close'],df['Open'],df['High'],df['Low'],df.index
    rmfi = df['RSI_MFI']; atr = df['ATR']
    vol_ratio = df['Volume']/(df['Volume'].rolling(50,min_periods=10).mean()+1e-10)

    above_200=C>df['MA200']; above_50=C>df['MA50']; above_20=C>df['MA20']
    below_200=C<df['MA200']; below_50=C<df['MA50']
    ma50r=df['MA50']>df['MA50'].shift(5); ma50f=df['MA50']<df['MA50'].shift(5)
    mh=df['MACD_Hist']; mhr=mh>mh.shift(1); mhf=mh<mh.shift(1)
    mg=df['MACD_Line']-df['MACD_Signal']; mac=mg>mg.shift(1); mdc=mg<mg.shift(1)
    rr=df['RSI']>df['RSI'].shift(1); rf=df['RSI']<df['RSI'].shift(1)
    sr=df['StochK']>df['StochK'].shift(1)
    wr=df['WT1']>df['WT1'].shift(1); wf=df['WT1']<df['WT1'].shift(1)
    obv=df['OBV']; obvm=obv.rolling(20,min_periods=10).mean()
    obva=obv>obvm; obvb=obv<obvm
    bvol=df['Volume'].where(C>O,0); bevol=df['Volume'].where(C<O,0)
    abv=bvol.rolling(10,min_periods=5).mean(); abev=bevol.rolling(10,min_periods=5).mean()
    vbr=abv/(abev+1e-10); vosc=df['VWAP_Osc']
    body=(C-O).abs(); bar=body/(atr+1e-10)
    wcu=df.get('WT_Up',pd.Series(False,index=idx))
    wcd=df.get('WT_Down',pd.Series(False,index=idx))
    sqo=df.get('Squeeze_On',pd.Series(False,index=idx)); pb=df['Percent_B']
    kt=pd.concat([df.get('Ichimoku_SenkouA',pd.Series(0,index=idx)),df.get('Ichimoku_SenkouB',pd.Series(0,index=idx))],axis=1).max(axis=1)
    kb=pd.concat([df.get('Ichimoku_SenkouA',pd.Series(0,index=idx)),df.get('Ichimoku_SenkouB',pd.Series(0,index=idx))],axis=1).min(axis=1)
    ak=C>kt; bk=C<kb; cmf=df.get('CMF',pd.Series(0,index=idx))
    tka=df.get('Ichimoku_Tenkan',pd.Series(0,index=idx))>df.get('Ichimoku_Kijun',pd.Series(0,index=idx))
    tkb=df.get('Ichimoku_Tenkan',pd.Series(0,index=idx))<df.get('Ichimoku_Kijun',pd.Series(0,index=idx))
    nr72v=_sig_pts(df,'NR7_2',1.5); calm=_sig_pts(df,'Calm_After_Storm',1.0)
    ca=df.get('Composite_Accel',pd.Series(0,index=idx))
    rs=df.get('RS_Ratio',pd.Series(1.0,index=idx))
    regime_v=df.get('Regime',pd.Series(0,index=idx))
    in_up=regime_v>=1; in_dn=regime_v<=-1

    # BUY
    # L1 Trend
    bt=pd.Series(0.0,index=idx)
    bt+=np.where(above_200&above_50&above_20,5.0,np.where(above_200&above_50,4.0,np.where(above_200,2.5,np.where(above_50,1.5,0))))
    bt+=np.where(df['MA50']>df['MA200'],1.5,0)+np.where(df['Plus_DI']>df['Minus_DI'],1.0,0)
    bt+=np.where(df['ST_Direction']==1,1.0,0)+np.where(above_50&ma50r,0.5,0)
    bt+=_sig_pts(df,'Cross_Above_50MA',1.0)+_sig_pts(df,'Cross_Above_200MA',1.5)+_sig_pts(df,'Golden_Cross',1.5)
    bt+=np.where(ak,1.5,0)+np.where(ak&tka,0.5,0)
    bt+=np.where(below_200&below_50,-2.0,0)+np.where(df['ST_Direction']==-1,-0.5,0)
    bt+=np.where(rs>1.05,1.5,np.where(rs>1.02,0.5,0))+np.where(rs<0.95,-1.0,0)
    df['BJ_Trend']=bt.clip(-2,JT.TREND_CAP)

    # L2 Momentum (국면 인식)
    bm=pd.Series(0.0,index=idx)
    bmc=pd.Series(0.0,index=idx)
    for s,p in [('MACD_Cross_Buy',2.5),('MACD_Zero_Cross_Buy',2.0),('StochRSI_Cross_Buy',2.0),('ADX_Momentum_Buy',2.0),('VWAP_Bounce_Buy',1.5)]:
        bmc+=_sig_pts(df,s,p)
    bm+=bmc.clip(upper=JT.CROSS_SIGNAL_CAP)
    bm+=np.select([(mh>0)&mhr,(mh>0)&mhf,(mh<0)&mhr],[2.0,0.5,1.5],default=0.0)
    bm+=np.where((mh>0)&mac,0.5,0)
    bm+=np.select([vosc>3.0,vosc>1.0,vosc>0],[1.5,1.0,0.5],default=0.0)
    bm+=np.select([(df['RSI']<30)&rr,df['RSI']<30,(df['RSI']<45)&rr,
        in_up&(df['RSI']>=50)&(df['RSI']<=70)&rr,
        (df['RSI']>70)&rf&~in_up,(df['RSI']>70)&rf&in_up],
        [3.0,1.5,1.0,1.5,-1.5,-0.3],default=0.0)
    bm+=np.select([(df['StochK']<20)&sr,df['StochK']<20,
        in_up&(df['StochK']>80)&sr,(df['StochK']>80)&~sr&~in_up],
        [2.5,1.0,0.5,-1.0],default=0.0)
    bm+=np.select([(df['WT1']<OS1)&(wcu|wr),df['WT1']<OS1,(df['WT1']<-20)&wr,
        in_up&(df['WT1']>20)&(df['WT1']<OB1)&wr,(df['WT1']>OB1)&wf&~in_up],
        [3.0,1.0,1.0,0.5,-1.5],default=0.0)
    df['BJ_Momentum']=bm.clip(-2,JT.MOMENTUM_CAP)

    # L3 Candle
    bcc=[]
    idt=below_50|(df['WT1']<-20)|(df['RSI']<45)
    for sn,bp_,tp in [('Morning_Star',2.5,3.5),('Bullish_Engulfing',2.0,3.0),('Hammer',1.5,2.5),('Outside_Bullish',1.5,2.5),('Doji_Bullish',0.5,1.0)]:
        r=df.get(sn,pd.Series(False,index=idx)).fillna(False)
        if sn=='Bullish_Engulfing': pts=np.where(r&idt&(bar>1.0),3.5,np.where(r&idt,tp,np.where(r&(bar>1.0),2.5,np.where(r,bp_,0))))
        else: pts=np.where(r&idt,tp,np.where(r,bp_,0))
        bcc.append(pts)
    df['BJ_Candle']=pd.Series(np.stack(bcc).max(axis=0),index=idx).clip(upper=JT.CANDLE_CAP) if bcc else pd.Series(0.0,index=idx)

    # L4 BB
    bb=pd.Series(0.0,index=idx)
    bb+=_sig_pts(df,'BB_Squeeze_End_Bull',3.0)+nr72v+calm
    bb+=np.where(sqo&above_50,1.0,0)
    bb+=np.select([pb<0.05,pb<0.2,(pb>=0.4)&(pb<=0.6)&above_50,pb>0.95],[2.5,1.5,0.5,-1.5],default=0.0)
    bb+=_sig_pts(df,'BB_Lower_Bounce',2.0)+np.where(df.get('BB_Lower_Break',pd.Series(False,index=idx)).fillna(False),-1.0,0)
    df['BJ_BB']=bb.clip(-1,JT.BB_CAP)

    # L5 Volume
    bv=pd.Series(0.0,index=idx)
    bv+=_sig_pts(df,'Volume_Climax_Buy',3.0)+_sig_pts(df,'Pocket_Pivot',2.0)+_sig_pts(df,'OBV_Div_Buy',1.5)
    bv+=_sig_pts(df,'Volume_POC_Breakout',2.5)
    bv+=np.where((vol_ratio>=3.0)&(C>O),2.5,np.where((vol_ratio>=1.5)&(C>O),1.0,0))
    bv+=np.where(obva&(obv>obv.shift(5)),1.5,np.where(obva,0.5,0))
    bv+=np.where(obvb&(obv<obv.shift(5)),-1.0,0)
    bv+=np.select([vbr>2.0,vbr>1.3,vbr<0.5],[1.5,0.5,-1.0],default=0.0)
    df['BJ_Volume']=bv.clip(-1,JT.VOLUME_CAP)

    # L6 MF
    bmf=pd.Series(0.0,index=idx)
    bmf+=np.select([rmfi<-10,rmfi<-5,rmfi>10],[2.0,1.0,-0.5],default=0.0)
    if 'MF_Slope_5' in df.columns: bmf+=np.select([df['MF_Slope_5']>5,df['MF_Slope_5']>2,df['MF_Slope_5']>0,df['MF_Slope_5']<-5],[2.0,1.5,0.5,-1.0],default=0.0)
    if 'MF_Up_Streak' in df.columns: bmf+=np.select([df['MF_Up_Streak']>=5,df['MF_Up_Streak']>=3],[2.0,1.0],default=0.0)
    bmf+=_sig_pts(df,'MF_Cross_Bull',2.0)+_sig_pts(df,'MF_Bull_Div',2.0)+_sig_pts(df,'MF_Accel_Up',1.0)
    bmf+=np.where(cmf>0.15,1.5,np.where(cmf>0.05,0.5,np.where(cmf<-0.15,-1.0,0)))
    bmf+=_sig_pts(df,'CMF_Bull',1.5)
    df['BJ_MF']=bmf.clip(-1,JT.MF_CAP)

    # L7 Pattern (Time Decay)
    bpp=pd.Series(0.0,index=idx)
    gold=_sig_pts_decayed(df,'Gold_Dot',4.0)
    gt1=np.where(gold==0,_sig_pts_decayed(df,'Green_Dot_T1',2.5),0)
    gt2=np.where((gold==0)&(gt1==0),_sig_pts(df,'Green_Dot_T2',2.0),0)
    bpp+=gold+gt1+gt2+np.where(gold==0,_sig_pts(df,'Bull_Divergence',2.0),0)
    for s,p in [('Pullback_123_Bull',2.5),('Setup_180_Bull',2.0),('Boomer_Buy',2.0),('Expansion_BO',3.0),
        ('Gilligans_Buy',2.5),('Lizard_Bull',2.0),('NonADX_123_Bull',1.5),('EMA_Pullback_Buy',2.0),
        ('Momentum_Ignition_Buy',3.0),('SuperTrend_Buy',2.0),('Gap_Up',1.0),('Gap_Down_Closed',1.0),
        ('New_52W_High',2.0),('Blue_Diamond',2.0),('Hidden_Bull_Div',1.5),('Squeeze_Fire_Buy',2.0),
        ('Parabolic_Bottom_Buy',3.0),('Pocket_Pivot',2.0),('Kumo_Breakout_Bull',2.5),('TK_Cross_Bull',1.5),
        ('Volume_POC_Breakout',2.5),('Relative_Strength_Buy',2.5),('VP_VAL_Support',1.5)]:
        bpp+=_sig_pts(df,s,p)
    for s,p in [('Expansion_BO',3.0),('Momentum_Ignition_Buy',3.0),('Parabolic_Bottom_Buy',3.0),('Kumo_Breakout_Bull',2.5)]:
        if s in df.columns:
            bpp+=np.where(df[s].shift(1).fillna(False)&~df[s],p*JT.DECAY_RATE,0)
            bpp+=np.where(df[s].shift(2).fillna(False)&~df[s]&~df[s].shift(1).fillna(False),p*JT.DECAY_RATE**2,0)
    df['BJ_Pattern']=bpp.clip(upper=JT.PATTERN_CAP)

    # L8 Anticipation
    ba=pd.Series(0.0,index=idx)
    spb=df.get('Setup_Pressure_Buy',pd.Series(0,index=idx))
    ba+=np.where(spb>=8,3.0,np.where(spb>=5,2.0,np.where(spb>=3,1.0,0)))
    ba+=np.where(ca>JT.ACCEL_STRONG,2.5,np.where(ca>JT.ACCEL_MODERATE,1.5,np.where(ca>0.5,0.5,0)))
    ba+=np.where(ca<-JT.ACCEL_MODERATE,-1.0,0)
    ba+=np.where(df.get('WT_Conv_Bull',pd.Series(False,index=idx)),2.0,0)
    ba+=_sig_pts(df,'Setup_Squeeze_Bull',1.5)+_sig_pts(df,'Momentum_Accel_Buy',2.0)+_sig_pts(df,'WT_Convergence_Bull',1.5)+_sig_pts(df,'Volume_Dry_Up',0.5)
    df['BJ_Anticipation']=ba.clip(-1,JT.ANTICIPATION_CAP)

    # SELL
    st_=pd.Series(0.0,index=idx)
    st_+=np.where(below_200&below_50&(C<df['MA20']),5.0,np.where(below_200&below_50,4.0,np.where(below_200,2.5,np.where(below_50,1.5,0))))
    st_+=np.where(df['MA50']<df['MA200'],1.5,0)+np.where(df['Minus_DI']>df['Plus_DI'],1.0,0)
    st_+=np.where(df['ST_Direction']==-1,1.0,0)+np.where(below_50&ma50f,0.5,0)
    st_+=_sig_pts(df,'Fell_Below_50MA',1.0)+_sig_pts(df,'Fell_Below_200MA',1.5)+_sig_pts(df,'Death_Cross',1.5)
    st_+=np.where(bk,1.5,0)+np.where(bk&tkb,0.5,0)
    st_+=np.where(above_200&above_50,-2.0,0)+np.where(df['ST_Direction']==1,-0.5,0)
    st_+=np.where(rs<0.95,1.5,np.where(rs<0.98,0.5,0))+np.where(rs>1.05,-1.0,0)
    df['SJ_Trend']=st_.clip(-2,JT.TREND_CAP)

    sm=pd.Series(0.0,index=idx)
    smc=pd.Series(0.0,index=idx)
    for s,p in [('MACD_Cross_Sell',2.5),('MACD_Zero_Cross_Sell',2.0),('StochRSI_Cross_Sell',2.0),('ADX_Momentum_Sell',2.0),('VWAP_Reject_Sell',1.5)]:
        smc+=_sig_pts(df,s,p)
    sm+=smc.clip(upper=JT.CROSS_SIGNAL_CAP)
    sm+=np.select([(mh<0)&mhf,(mh<0)&mhr,(mh>0)&mhf],[2.0,0.5,1.5],default=0.0)
    sm+=np.where((mh<0)&mdc,0.5,0)
    sm+=np.select([vosc<-3.0,vosc<-1.0,vosc<0],[1.5,1.0,0.5],default=0.0)
    iut=above_50|(df['WT1']>20)|(df['RSI']>55)
    sm+=np.select([(df['RSI']>70)&rf&~in_up,(df['RSI']>70)&rf&in_up,df['RSI']>70,
        (df['RSI']>55)&rf&~in_up,(df['RSI']<30)&rr&~in_dn],[3.0,1.0,1.5,1.0,-1.5],default=0.0)
    sm+=np.select([(df['StochK']>80)&~sr&~in_up,(df['StochK']>80)&~sr&in_up,df['StochK']>80,
        (df['StochK']<20)&sr&~in_dn],[2.5,0.5,1.0,-1.0],default=0.0)
    sm+=np.select([(df['WT1']>OB1)&(wcd|wf)&~in_up,(df['WT1']>OB1)&wf&in_up,df['WT1']>OB1,
        (df['WT1']>20)&wf&~in_up,(df['WT1']<OS1)&wr&~in_dn],[3.0,1.0,1.0,1.0,-1.5],default=0.0)
    df['SJ_Momentum']=sm.clip(-2,JT.MOMENTUM_CAP)

    scc=[]
    for sn,bp_,tp in [('Evening_Star',2.5,3.5),('Bearish_Engulfing',2.0,3.0),('Shooting_Star',1.5,2.5),('Outside_Bearish',1.5,2.5),('Doji_Bearish',0.5,1.0)]:
        r=df.get(sn,pd.Series(False,index=idx)).fillna(False)
        if sn=='Bearish_Engulfing': pts=np.where(r&iut&(bar>1.0),3.5,np.where(r&iut,tp,np.where(r&(bar>1.0),2.5,np.where(r,bp_,0))))
        else: pts=np.where(r&iut,tp,np.where(r,bp_,0))
        scc.append(pts)
    df['SJ_Candle']=pd.Series(np.stack(scc).max(axis=0),index=idx).clip(upper=JT.CANDLE_CAP) if scc else pd.Series(0.0,index=idx)

    sb_=pd.Series(0.0,index=idx)
    sb_+=_sig_pts(df,'BB_Squeeze_End_Bear',3.0)+nr72v+calm
    sb_+=np.where(sqo&below_50,1.0,0)
    sb_+=np.select([pb>0.95,pb>0.8,(pb>=0.4)&(pb<=0.6)&below_50,pb<0.05],[2.5,1.5,0.5,-1.5],default=0.0)
    sb_+=_sig_pts(df,'BB_Lower_Break',1.5)+np.where(df.get('BB_Upper_Break',pd.Series(False,index=idx)).fillna(False)&above_200,-0.5,0)
    df['SJ_BB']=sb_.clip(-1,JT.BB_CAP)

    sv=pd.Series(0.0,index=idx)
    sv+=_sig_pts(df,'Volume_Climax_Sell',3.0)+_sig_pts(df,'OBV_Div_Sell',1.5)+_sig_pts(df,'Volume_POC_Breakdown',2.5)
    sv+=np.where((vol_ratio>=3.0)&(C<O),2.5,np.where((vol_ratio>=1.5)&(C<O),1.0,0))
    sv+=np.where(obvb&(obv<obv.shift(5)),1.5,np.where(obvb,0.5,0))+np.where(obva&(obv>obv.shift(5)),-1.0,0)
    sv+=np.select([vbr<0.5,vbr<0.7,vbr>2.0],[1.5,0.5,-1.0],default=0.0)
    df['SJ_Volume']=sv.clip(-1,JT.VOLUME_CAP)

    smf=pd.Series(0.0,index=idx)
    smf+=np.select([rmfi>10,rmfi>5,rmfi<-10],[2.0,1.0,-0.5],default=0.0)
    if 'MF_Slope_5' in df.columns: smf+=np.select([df['MF_Slope_5']<-5,df['MF_Slope_5']<-2,df['MF_Slope_5']<0,df['MF_Slope_5']>5],[2.0,1.5,0.5,-1.0],default=0.0)
    if 'MF_Dn_Streak' in df.columns: smf+=np.select([df['MF_Dn_Streak']>=5,df['MF_Dn_Streak']>=3],[2.0,1.0],default=0.0)
    smf+=_sig_pts(df,'MF_Cross_Bear',2.0)+_sig_pts(df,'MF_Bear_Div',2.0)+_sig_pts(df,'MF_Accel_Dn',1.0)
    smf+=np.where(cmf<-0.15,1.5,np.where(cmf<-0.05,0.5,np.where(cmf>0.15,-1.0,0)))
    smf+=_sig_pts(df,'CMF_Bear',1.5)
    df['SJ_MF']=smf.clip(-1,JT.MF_CAP)

    spp=pd.Series(0.0,index=idx)
    blood=_sig_pts_decayed(df,'Blood_Diamond',4.0)
    rt1=np.where(blood==0,_sig_pts_decayed(df,'Red_Dot_T1',2.5),0)
    rt2=np.where((blood==0)&(rt1==0),_sig_pts(df,'Red_Dot_T2',2.0),0)
    spp+=blood+rt1+rt2+np.where(blood==0,_sig_pts(df,'Bear_Divergence',2.0),0)
    for s,p in [('Pullback_123_Bear',2.5),('Setup_180_Bear',2.0),('Boomer_Sell',2.0),('Expansion_BD',3.0),
        ('Gilligans_Sell',2.5),('Lizard_Bear',2.0),('NonADX_123_Bear',1.5),('EMA_Pullback_Sell',2.0),
        ('Momentum_Ignition_Sell',3.0),('SuperTrend_Sell',2.0),('Gap_Down',1.0),('Gap_Up_Closed',1.0),
        ('New_52W_Low',2.0),('Red_Diamond',2.0),('Hidden_Bear_Div',1.5),('Squeeze_Fire_Sell',2.0),
        ('Parabolic_Top_Sell',3.0),('Kumo_Breakout_Bear',2.5),('TK_Cross_Bear',1.5),
        ('Volume_POC_Breakdown',2.5),('Relative_Strength_Sell',2.0),('VP_VAH_Resistance',1.5)]:
        spp+=_sig_pts(df,s,p)
    for s,p in [('Expansion_BD',3.0),('Momentum_Ignition_Sell',3.0),('Parabolic_Top_Sell',3.0),('Kumo_Breakout_Bear',2.5)]:
        if s in df.columns:
            spp+=np.where(df[s].shift(1).fillna(False)&~df[s],p*JT.DECAY_RATE,0)
            spp+=np.where(df[s].shift(2).fillna(False)&~df[s]&~df[s].shift(1).fillna(False),p*JT.DECAY_RATE**2,0)
    df['SJ_Pattern']=spp.clip(upper=JT.PATTERN_CAP)

    sa=pd.Series(0.0,index=idx)
    sps=df.get('Setup_Pressure_Sell',pd.Series(0,index=idx))
    sa+=np.where(sps>=8,3.0,np.where(sps>=5,2.0,np.where(sps>=3,1.0,0)))
    sa+=np.where(ca<-JT.ACCEL_STRONG,2.5,np.where(ca<-JT.ACCEL_MODERATE,1.5,np.where(ca<-0.5,0.5,0)))
    sa+=np.where(ca>JT.ACCEL_MODERATE,-1.0,0)
    sa+=np.where(df.get('WT_Conv_Bear',pd.Series(False,index=idx)),2.0,0)
    sa+=_sig_pts(df,'Setup_Squeeze_Bear',1.5)+_sig_pts(df,'Momentum_Accel_Sell',2.0)+_sig_pts(df,'WT_Convergence_Bear',1.5)+_sig_pts(df,'Volume_Dry_Up',0.5)
    df['SJ_Anticipation']=sa.clip(-1,JT.ANTICIPATION_CAP)

    # ═══ Adaptive Weighting (매수/매도 분리) ═══
    bw, sw = _compute_regime_weights(df)
    names = ['Trend','Momentum','Candle','BB','Volume','MF','Pattern','Anticipation']

    # 1. 개별 레이어에 가중치를 먼저 적용하여 덮어쓰기
    for n in names:
        df[f'BJ_{n}'] = df[f'BJ_{n}'] * bw[n]
        df[f'SJ_{n}'] = df[f'SJ_{n}'] * sw[n]

    # 2. 이미 가중치가 적용된 컬럼들을 단순 합산
    df['Buy_Total'] = sum(df[f'BJ_{n}'] for n in names)
    df['Sell_Total'] = sum(df[f'SJ_{n}'] for n in names)

    # 콤보 보너스
    detect_combos(df, vol_ratio)
    bcb=pd.Series(0.0,index=idx); scb=pd.Series(0.0,index=idx)
    for col,(nm,d,t) in COMBO_MAP.items():
        if col not in df.columns: continue
        bonus={1:JT.COMBO_TIER1_BONUS,2:JT.COMBO_TIER2_BONUS,3:JT.COMBO_TIER3_BONUS}.get(t,JT.COMBO_TIER3_BONUS)
        if d=='buy': bcb+=np.where(df[col],bonus,0.0)
        else: scb+=np.where(df[col],bonus,0.0)
    df['Buy_Total']+=bcb; df['Sell_Total']+=scb

    # MTF 보정
    wts=df.get('Weekly_Trend_Score',pd.Series(0,index=idx))
    wbu=wts>=JT.WEEKLY_BULL_THRESH; wbe=wts<=JT.WEEKLY_BEAR_THRESH
    df['Buy_Total']+=np.where(wbu,JT.MTF_BONUS,np.where(wbe,JT.MTF_PENALTY,0))
    df['Sell_Total']+=np.where(wbe,JT.MTF_BONUS,np.where(wbu,JT.MTF_PENALTY,0))

    # Vol Shock
    am5=atr.rolling(5,min_periods=3).mean(); asp=atr/(am5+1e-10)
    vsd=(asp>=JT.ATR_SPIKE_THRESH)&(C<C.shift(1))&(C<O)
    vsu=(asp>=JT.ATR_SPIKE_THRESH)&(C>C.shift(1))&(C>O)
    ssk=_vectorized_streak(asp>=JT.ATR_SPIKE_MILD); severe=ssk>=JT.SHOCK_SEVERE_STREAK
    bpen=np.where(vsd&severe,-8.0,np.where(vsd,-5.0,np.where((asp>=JT.ATR_SPIKE_MILD)&(C<O),-2.0,0)))
    spen=np.where(vsu&severe,-5.0,np.where(vsu,-3.0,0))
    df['Buy_Total']+=bpen; df['Sell_Total']+=spen
    df['Buy_Total']=df['Buy_Total'].clip(lower=0); df['Sell_Total']=df['Sell_Total'].clip(lower=0)
    df['ATR_Spike']=asp; df['Vol_Shock_Active']=vsd|vsu

    # 활성 레이어
    bln=['BJ_Trend','BJ_Momentum','BJ_Candle','BJ_BB','BJ_Volume','BJ_MF','BJ_Pattern','BJ_Anticipation']
    sln=['SJ_Trend','SJ_Momentum','SJ_Candle','SJ_BB','SJ_Volume','SJ_MF','SJ_Pattern','SJ_Anticipation']
    df['Buy_Active_Layers']=sum((df[n]>0).astype(int) for n in bln)
    df['Sell_Active_Layers']=sum((df[n]>0).astype(int) for n in sln)

    # 최종 판단
    j=np.full(len(df),'NEUTRAL',dtype=object); conf=np.zeros(len(df),dtype=float)
    btv,stv=df['Buy_Total'].values,df['Sell_Total'].values
    bav,sav=df['Buy_Active_Layers'].values,df['Sell_Active_Layers'].values
    apct=(df['ATR']/(df['Close']+1e-10)*100).values
    for i in range(len(df)):
        b,s=btv[i],stv[i]; bal,sal=bav[i],sav[i]
        diff=b-s; ratio=b/(s+0.01); sr_=s/(b+0.01); vol=apct[i]
        sc=JT.LOW_VOL_SCALE if vol<2.0 else 1.0; ssc=sc*JT.SELL_ASYMMETRY
        if b>=JT.STRONG_BUY_SCORE*sc and bal>=JT.STRONG_BUY_LAYERS and ratio>=JT.STRONG_BUY_RATIO and diff>=JT.STRONG_BUY_DIFF*sc: j[i]='STRONG_BUY'
        elif b>=JT.BUY_SCORE*sc and bal>=JT.BUY_LAYERS and ratio>=JT.BUY_RATIO and diff>=JT.BUY_DIFF*sc: j[i]='BUY'
        elif b>=JT.WATCH_BUY_SCORE*sc and bal>=JT.WATCH_LAYERS and diff>=JT.WATCH_DIFF*sc: j[i]='WATCH_BUY'
        elif s>=JT.STRONG_BUY_SCORE*ssc and sal>=JT.STRONG_BUY_LAYERS and sr_>=1.5 and (s-b)>=8*sc: j[i]='STRONG_SELL'
        elif s>=JT.BUY_SCORE*ssc and sal>=JT.BUY_LAYERS and sr_>=1.2 and (s-b)>=4*sc: j[i]='SELL'
        elif s>=JT.WATCH_BUY_SCORE*ssc and sal>=JT.WATCH_LAYERS and (s-b)>=1.5*sc: j[i]='WATCH_SELL'
        elif b>s+2.0 and bal>=2: j[i]='WATCH_BUY'
        elif s>b+2.0 and sal>=2: j[i]='WATCH_SELL'
        elif b>=JT.MIXED_MIN*sc and s>=JT.MIXED_MIN*sc and abs(diff)<JT.MIXED_DIFF_MAX*sc: j[i]='MIXED'
        conf[i]=_compute_confidence(b,s,bal,sal,j[i],vol)
    df['Trade_Judgment']=j; df['Judgment_Confidence']=np.clip(conf,0,99)
    return df


# ══════════════════════════════════════════
#  판단 상세 + Bias
# ══════════════════════════════════════════
def get_judgment_detail(row):
    ln=['Trend','Momentum','Candle','BB','Volume','MF','Pattern','Anticipation']
    bl={n:float(row.get(f'BJ_{n}',0)) for n in ln}; sl={n:float(row.get(f'SJ_{n}',0)) for n in ln}
    combos=[{'name':nm,'dir':d,'tier':t} for col,(nm,d,t) in COMBO_MAP.items() if row.get(col,False)]
    return {'judgment':str(row.get('Trade_Judgment','NEUTRAL')),'confidence':float(row.get('Judgment_Confidence',0)),
        'buy_total':float(row.get('Buy_Total',0)),'sell_total':float(row.get('Sell_Total',0)),
        'buy_layers':bl,'sell_layers':sl,'buy_active':int(row.get('Buy_Active_Layers',0)),
        'sell_active':int(row.get('Sell_Active_Layers',0)),'active_combos':combos,
        'net':float(row.get('Buy_Total',0))-float(row.get('Sell_Total',0)),
        'setup_pressure_buy':float(row.get('Setup_Pressure_Buy',0)),
        'setup_pressure_sell':float(row.get('Setup_Pressure_Sell',0)),
        'composite_accel':float(row.get('Composite_Accel',0))}

def compute_bias(meta, htf1, htf2):
    sc=0.0; wt1=meta.get('wt1',0); rsi=meta.get('rsi',50); mfi=meta.get('mfi',50)
    stk=meta.get('stochk',50); mf=meta.get('mf_area',0); mhv=meta.get('macd_hist',0)
    accel=meta.get('composite_accel',0)
    st_dir=meta.get('supertrend_dir',0); pdi=meta.get('plus_di',0); mdi=meta.get('minus_di',0)
    sup=htf1 and htf2 and (st_dir==1) and (pdi>mdi)
    sdn=(not htf1) and (not htf2) and (st_dir==-1) and (mdi>pdi)

    if wt1<=-60: sc+=3.0
    elif wt1<=-53: sc+=2.0
    elif wt1<=-20: sc+=1.0
    elif wt1>=60: sc-=3.0
    elif wt1>=53: sc-=2.0
    elif wt1>=20: sc-=0.0 if sup else 1.0

    if rsi<=30: sc+=1.5
    elif rsi<=45: sc+=0.5
    elif rsi>=70: sc-=0.3 if sup else 1.5
    elif rsi>=55: sc-=0.0 if sup else 0.5

    if mfi<=30: sc+=1.5
    elif mfi<=45: sc+=0.5
    elif mfi>=70: sc-=0.0 if sup else 1.5
    elif mfi>=55: sc-=0.0 if sup else 0.5

    if stk<20: sc+=1.5
    elif stk<35: sc+=0.5
    elif stk>80: sc-=0.0 if sup else 1.5
    elif stk>65: sc-=0.0 if sup else 0.5

    if mf<-5: sc+=2.0
    elif mf<0: sc+=1.0
    elif mf>5: sc-=2.0
    elif mf>0: sc-=1.0
    if mhv>0.1: sc+=1.0
    elif mhv>0: sc+=0.5
    elif mhv<-0.1: sc-=1.0
    elif mhv<0: sc-=0.5
    sc+=1.5 if htf1 else -1.5; sc+=2.0 if htf2 else -2.0
    if accel>1.5: sc+=1.0
    elif accel<-1.5: sc-=1.0
    if sup: sc+=2.0
    elif sdn: sc-=2.0

    if sc>=9.0: return 'STRONG BUY',sc
    elif sc>=3.5: return 'BUY',sc
    elif sc>-3.5: return 'NEUTRAL',sc
    elif sc>-9.0: return 'SELL',sc
    else: return 'STRONG SELL',sc


# ══════════════════════════════════════════
#  스캐너 콤보
# ══════════════════════════════════════════
SCANNER_COMBOS = {
    'SC_Oversold_Bounce':{'name':'🟢 Oversold Bounce','kor':'과매도 반등','dir':'buy','tier':1,'icon':'🏓','color':'#00E676','desc':'StochRSI 과매도+강세캔들+20MA돌파','category':'반전'},
    'SC_Breakout_Momentum':{'name':'🟢 Breakout Momentum','kor':'돌파 모멘텀','dir':'buy','tier':1,'icon':'🚀','color':'#00E676','desc':'확장돌파+거래량급증+52주신고가','category':'돌파'},
    'SC_Triple_Oversold':{'name':'🟢 Triple Oversold','kor':'삼중과매도반전','dir':'buy','tier':1,'icon':'💎','color':'#00E676','desc':'WT+RSI+캔들동시과매도극단반전','category':'반전'},
    'SC_Volume_Climax_Rev':{'name':'🟢 Vol Climax Rev','kor':'거래량클라이맥스반전','dir':'buy','tier':1,'icon':'🌊','color':'#00BCD4','desc':'거래량폭발+WT과매도+다이버전스','category':'반전'},
    'SC_Momentum_Ignition_Buy':{'name':'🟢 Mom Ignition','kor':'모멘텀점화매수','dir':'buy','tier':1,'icon':'🔥','color':'#FF6D00','desc':'모멘텀점화+ST강세+ADX상승','category':'돌파'},
    'SC_Overbought_Exhaust':{'name':'🔴 Overbought Exhaust','kor':'과매수소진','dir':'sell','tier':1,'icon':'🌡️','color':'#FF1744','desc':'StochRSI과매수+약세캔들+20MA이탈','category':'반전'},
    'SC_Breakdown_Momentum':{'name':'🔴 Breakdown Mom','kor':'붕괴모멘텀','dir':'sell','tier':1,'icon':'💨','color':'#FF1744','desc':'확장붕괴+거래량급증+52주신저가','category':'붕괴'},
    'SC_Triple_Overbought':{'name':'🔴 Triple Overbought','kor':'삼중과매수반전','dir':'sell','tier':1,'icon':'💀','color':'#FF1744','desc':'WT+RSI+캔들동시과매수극단반전','category':'반전'},
    'SC_Volume_Climax_Sell':{'name':'🔴 Vol Climax Sell','kor':'거래량클라이맥스매도','dir':'sell','tier':1,'icon':'🌋','color':'#D50000','desc':'거래량폭발매도+WT과매수+다이버전스','category':'반전'},
    'SC_Parabolic_Exhaust':{'name':'🔴 Parabolic Exhaust','kor':'포물선소진','dir':'sell','tier':1,'icon':'🌡️','color':'#FF0000','desc':'포물선천장+거래량폭발+RSI극과매수','category':'반전'},
}

def detect_scanner_combos(df):
    idx=df.index; C,O,H,L,V=df['Close'],df['Open'],df['High'],df['Low'],df['Volume']
    F=lambda col: df.get(col,pd.Series(False,index=idx)).fillna(False)
    vr=V/(V.rolling(50,min_periods=10).mean()+1e-10); v15=vr>=1.5; v2=vr>=2.0
    cb=F('Bullish_Engulfing')|F('Hammer')|F('Morning_Star')|F('Doji_Bullish')
    cbe=F('Bearish_Engulfing')|F('Shooting_Star')|F('Evening_Star')|F('Doji_Bearish')
    def _rec(col,lb=3): s=F(col); return s.astype(float).rolling(lb+1,min_periods=1).max().fillna(0).astype(bool)

    so=(df['StochK']<20)&(df['StochD']<20)
    df['SC_Oversold_Bounce']=so&(cb|_rec('StochRSI_Cross_Buy'))&(_rec('Cross_Above_20MA')|(C>df['MA20']))&v15
    df['SC_Breakout_Momentum']=(F('Expansion_BO')|F('New_52W_High'))&v2&(df['ADX']>20)
    to=(((df['WT1']<OS1).astype(int)+(df['RSI']<35).astype(int)+(df['MFI']<35).astype(int)+(df['StochK']<20).astype(int))>=3)
    sbs=F('Gold_Dot')|F('Green_Dot_T1')|F('Morning_Star')|F('Bullish_Engulfing')|F('Bull_Divergence')|F('Parabolic_Bottom_Buy')
    df['SC_Triple_Oversold']=to&(sbs|cb)
    df['SC_Volume_Climax_Rev']=F('Volume_Climax_Buy')&(df['WT1']<-30)&(_rec('Bull_Divergence')|_rec('RSI_Bull_Divergence')|cb)
    df['SC_Momentum_Ignition_Buy']=(F('Momentum_Ignition_Buy')|(F('Expansion_BO')&v2))&(F('SuperTrend_Buy')|(df['ST_Direction']==1))&(df['ADX']>20)

    sob=(df['StochK']>80)&(df['StochD']>80)
    df['SC_Overbought_Exhaust']=sob&(cbe|_rec('StochRSI_Cross_Sell'))&(_rec('Fell_Below_20MA')|(C<df['MA20']))&v15
    df['SC_Breakdown_Momentum']=(F('Expansion_BD')|F('New_52W_Low'))&v2&(df['ADX']>20)
    tob=(((df['WT1']>OB1).astype(int)+(df['RSI']>65).astype(int)+(df['MFI']>65).astype(int)+(df['StochK']>80).astype(int))>=3)
    sbse=F('Blood_Diamond')|F('Red_Dot_T1')|F('Evening_Star')|F('Bearish_Engulfing')|F('Bear_Divergence')|F('Parabolic_Top_Sell')
    df['SC_Triple_Overbought']=tob&(sbse|cbe)
    df['SC_Volume_Climax_Sell']=F('Volume_Climax_Sell')&(df['WT1']>30)&(_rec('Bear_Divergence')|_rec('RSI_Bear_Divergence')|cbe)
    df['SC_Parabolic_Exhaust']=(F('Parabolic_Top_Sell')|((df['WT1']>80)&(df['WT1']<df['WT1'].shift(1))))&v2&(df['RSI']>65)

    for cn in SCANNER_COMBOS:
        if cn in df.columns: df[cn]=_cooldown(df[cn],bars=5)
    return df


# ══════════════════════════════════════════
#  병렬 스캐너
# ══════════════════════════════════════════
@st.cache_data(ttl=600, show_spinner=False)
def scan_ticker(ticker, _ts=None):
    try:
        df=compute_and_cache(ticker,_ts)
        if df is None or len(df)<50: return None
        df=detect_scanner_combos(df); lat=df.iloc[-1]; ac=[]
        for cn,cfg in SCANNER_COMBOS.items():
            if cn not in df.columns: continue
            rec=df[cn].tail(5)
            if rec.any():
                ld=rec[rec].index[-1]
                ac.append({'name':cfg['name'],'kor':cfg['kor'],'dir':cfg['dir'],'tier':cfg['tier'],
                    'icon':cfg['icon'],'color':cfg['color'],'desc':cfg['desc'],'category':cfg['category'],
                    'days_ago':(df.index[-1]-ld).days,'date':ld.strftime('%m/%d')})
        if not ac: return None
        jd=get_judgment_detail(lat) if 'Trade_Judgment' in df.columns else {}
        return {'ticker':ticker.upper(),'price':float(lat['Close']),
            'change_pct':float((lat['Close']-df.iloc[-2]['Close'])/df.iloc[-2]['Close']*100) if len(df)>=2 else 0,
            'judgment':jd.get('judgment','N/A'),'confidence':jd.get('confidence',0),
            'active_combos':ac,'buy_combos':[c for c in ac if c['dir']=='buy'],
            'sell_combos':[c for c in ac if c['dir']=='sell']}
    except: return None

def scan_multiple_tickers(tickers, progress_callback=None, max_workers=8):
    results=[]; total=len(tickers); done=0
    def _safe(t):
        try: return scan_ticker(t)
        except: return None
    with ThreadPoolExecutor(max_workers=min(max_workers,total)) as ex:
        futs={ex.submit(_safe,t):t for t in tickers}
        for f in as_completed(futs):
            done+=1
            if progress_callback: progress_callback(done/total, f"🔍 {futs[f]} ({done}/{total})")
            try:
                r=f.result(timeout=30)
                if r: results.append(r)
            except: pass
    results.sort(key=lambda x:(-sum(1 for c in x['active_combos'] if c['tier']==1),-len(x['active_combos'])))
    return results


# ══════════════════════════════════════════
#  차트 빌더 (Tier A/B + 리치 호버)
# ══════════════════════════════════════════
def _hl(fig,mask,idx,fill,txt=None,row=1):
    d=mask.astype(int).diff().fillna(0)
    starts=idx[d==1].tolist(); ends=idx[d==-1].tolist()
    if len(mask)>0 and mask.iloc[0]: starts.insert(0,idx[0])
    if len(mask)>0 and mask.iloc[-1]: ends.append(idx[-1])
    for sv,ev in zip(starts,ends):
        kw=dict(x0=sv,x1=ev,fillcolor=fill,line_width=0,row=row,col=1)
        if txt: kw.update(annotation_text=txt,annotation_position="top left",annotation_font_size=10,annotation_font_color="#FF5252")
        fig.add_vrect(**kw)

def _build_signal_hover(dc, idx_v, trigger_cfg):
    row=dc.loc[idx_v]; ds=idx_v.strftime('%Y-%m-%d')
    ab,asb,an=[],[],[]
    for sn,cfg in SIGNAL_REGISTRY.items():
        if sn in dc.columns and row.get(sn,False):
            e=f"{cfg['icon']} {cfg['kor']}"
            if cfg['dir']=='buy': ab.append(e)
            elif cfg['dir']=='sell': asb.append(e)
            else: an.append(e)
    lb,ls=[],[]
    for n in ['Trend','Momentum','Candle','BB','Volume','MF','Pattern','Anticipation']:
        bv=float(row.get(f'BJ_{n}',0)); sv=float(row.get(f'SJ_{n}',0))
        if bv>0: lb.append(f"{n}:{bv:.1f}")
        if sv>0: ls.append(f"{n}:{sv:.1f}")
    j=str(row.get('Trade_Judgment',''));cf=float(row.get('Judgment_Confidence',0))
    bt=float(row.get('Buy_Total',0));st=float(row.get('Sell_Total',0))
    rg=int(row.get('Regime',0))
    rl={2:'🟢🟢UP',1:'🟢UP',0:'⚪RANGE',-1:'🔴DN',-2:'🔴🔴DN'}.get(rg,'?')
    combos=[nm for col,(nm,_,_) in COMBO_MAP.items() if row.get(col,False)]
    lines=[f"<b style='font-size:13px'>📅 {ds}</b>",
           f"<b style='color:#A5B4FC'>{trigger_cfg['icon']} {trigger_cfg['kor']}</b>",
           f"─"*28, f"<b>국면:</b> {rl}", f"<b>판단:</b> {j} ({cf:.0f}%) · B{bt:.1f} vs S{st:.1f}"]
    if combos: lines.append(f"<b>🔥콤보:</b> {', '.join(combos)}")
    lines.append(f"─"*28)
    if ab: lines.append(f"<span style='color:#34D399'><b>▲매수({len(ab)}):</b></span>"); lines.extend(f"  {s}" for s in ab[:5])
    if asb: lines.append(f"<span style='color:#F87171'><b>▼매도({len(asb)}):</b></span>"); lines.extend(f"  {s}" for s in asb[:5])
    lines.append(f"─"*28)
    if lb: lines.append(f"<span style='color:#34D399'><b>BUY층:</b> {' · '.join(lb)}</span>")
    if ls: lines.append(f"<span style='color:#F87171'><b>SELL층:</b> {' · '.join(ls)}</span>")
    lines.append(f"WT:{row.get('WT1',0):.0f} RSI:{row.get('RSI',0):.0f} MFI:{row.get('MFI',0):.0f} StK:{row.get('StochK',0):.0f} ADX:{row.get('ADX',0):.0f}")
    return "<br>".join(lines)

def build_chart(dc, ticker, regime, shield):
    mac={5:"#ff9900",10:"#ffb74d",20:'#f1c40f',50:'#e74c3c',100:'#9b59b6',125:'#3498db',200:'#2ecc71'}
    fig=make_subplots(rows=7,cols=1,shared_xaxes=True,vertical_spacing=0.03,
        row_heights=[.32,.06,.12,.10,.12,.14,.14],
        subplot_titles=("","Volume","WaveTrend","Money Flow","MACD","Judgment","Anticipation"))

    # 캔들 + 국면 정보 호버
    rl=dc.get('Regime',pd.Series(0,index=dc.index)).map({2:'🟢🟢UP',1:'🟢UP',0:'⚪RNG',-1:'🔴DN',-2:'🔴🔴DN'}).fillna('?')
    ch=[f"O:{o:.2f} H:{h:.2f} L:{lo:.2f} C:{cl:.2f}<br>Vol:{vol:,.0f} ATR:{at:.2f}<br>WT:{wt:.0f} RSI:{rs:.0f} {rg}"
        for o,h,lo,cl,vol,at,wt,rs,rg in zip(dc['Open'],dc['High'],dc['Low'],dc['Close'],dc['Volume'],dc['ATR'],dc['WT1'],dc['RSI'],rl)]
    fig.add_trace(go.Candlestick(x=dc.index,open=dc['Open'],high=dc['High'],low=dc['Low'],close=dc['Close'],
        name="Price",increasing_line_color='#00E676',decreasing_line_color='#FF1744',
        increasing_fillcolor='rgba(0,230,118,0.8)',decreasing_fillcolor='rgba(255,23,68,0.8)',
        text=ch,hoverinfo='text'),row=1,col=1)

    for ma in [5,10,20,50,100,125,200]:
        fig.add_trace(go.Scatter(x=dc.index,y=dc[f'MA{ma}'],line=dict(color=mac[ma],width=1.2),name=f'{ma}MA',hovertemplate="%{y:.2f}"),row=1,col=1)
    for nm,cn,clr,dash in [('EMA8','EMA8','#00FFFF','dot'),('EMA21','EMA21','#FF69B4','dot')]:
        fig.add_trace(go.Scatter(x=dc.index,y=dc[cn],line=dict(color=clr,width=1.5,dash=dash),name=nm),row=1,col=1)
    for mc,clr,nm in [(dc['ST_Direction']==1,'#00E676','ST▲'),(dc['ST_Direction']==-1,'#FF1744','ST▼')]:
        fig.add_trace(go.Scatter(x=dc.index,y=dc['SuperTrend'].where(mc),line=dict(color=clr,width=2),name=nm,connectgaps=False),row=1,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['BB_Up'],line=dict(color='gray',width=1,dash='dot'),name='BB↑'),row=1,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['BB_Low'],line=dict(color='gray',width=1,dash='dot'),name='BB↓',fill='tonexty',fillcolor='rgba(128,128,128,0.07)'),row=1,col=1)
    if 'VP_POC' in dc.columns:
        fig.add_trace(go.Scatter(x=dc.index,y=dc['VP_POC'],line=dict(color='#FFD700',width=1.5,dash='dashdot'),name='POC',opacity=0.6),row=1,col=1)

    # 판단 마커
    if 'Trade_Judgment' in dc.columns:
        ej=st.session_state.get('enabled_judgments',set(JUDGMENT_MARKERS.keys()))
        for jg,jc in JUDGMENT_MARKERS.items():
            if jg not in ej: continue
            mask=dc['Trade_Judgment']==jg
            if not mask.any(): continue
            sr=dc[mask]
            yv=sr['Low']+sr['ATR']*jc['atr_mult'] if jc['base']=='Low' else sr['High']+sr['ATR']*jc['atr_mult']
            ht=[_build_signal_hover(dc,iv,{'icon':'🎯','kor':jg}) for iv in sr.index]
            fig.add_trace(go.Scatter(x=sr.index,y=yv,mode='markers',
                marker=dict(symbol=jc['symbol'],size=jc['size'],color=jc['color'],
                    line=dict(width=jc['line_width'],color=jc['line_color']),opacity=0.95),
                name=jc['label'],text=ht,hovertemplate="%{text}<extra></extra>",
                hoverlabel=dict(bgcolor='rgba(10,13,20,0.97)',bordercolor=jc['color'],
                    font=dict(size=11,family='Pretendard',color='#FAFAFA'),align='left')),row=1,col=1)

    # 시그널 마커 (Tier A + 조건부 Tier B)
    tier_a=set(SIGNAL_CHART_TIERS['A']); tier_b=set(SIGNAL_CHART_TIERS['B'])
    sig_cnt=pd.Series(0,index=dc.index)
    for sn in SIGNAL_REGISTRY:
        if sn in dc.columns: sig_cnt+=dc[sn].fillna(False).astype(int)
    conf=dc.get('Confluence_Score',pd.Series(0,index=dc.index))
    show_b=(sig_cnt>=2)|(conf.abs()>=3.5)
    dl=st.session_state.get('sig_display_level','⭐ 핵심만 (Tier A)')

    for sn,sc in SIGNAL_REGISTRY.items():
        if sn not in dc.columns: continue
        raw=dc[sn].fillna(False)
        if not raw.any(): continue
        if sn in tier_a: mask=raw
        elif sn in tier_b:
            if '핵심만' in dl: continue
            mask=raw&show_b
        else:
            if '전체' not in dl: continue
            mask=raw
        if not mask.any(): continue
        sr=dc[mask]
        yv=sr['Low']+sr['ATR']*sc['atr_m'] if sc['base']=='Low' else sr['High']+sr['ATR']*sc['atr_m']
        ht=[_build_signal_hover(dc,iv,sc) for iv in sr.index]
        sz=sc['sz'] if sn in tier_a else max(sc['sz']-3,6)
        op=0.95 if sn in tier_a else 0.75
        lw=1.5 if sn in tier_a else 1
        tier_prefix = "⭐" if sn in tier_a else "📊"
        fig.add_trace(go.Scatter(x=sr.index,y=yv,mode='markers',
            marker=dict(symbol=sc['sym'],size=sz,color=sc['clr'],line=dict(width=lw,color='#FFF' if sn in tier_a else sc['clr']),opacity=op),
            name=f"{tier_prefix} {sc['icon']} {sc['kor']}",text=ht,hovertemplate="%{text}<extra></extra>",
            hoverlabel=dict(bgcolor='rgba(10,13,20,0.97)',bordercolor=sc['clr'],font=dict(size=11,family='Pretendard',color='#FAFAFA'),align='left')),row=1,col=1)

    # Row 2-7
    br=dc['Close']<dc['Open']
    fig.add_trace(go.Bar(x=dc.index,y=dc['Volume'],marker_color=np.where(br,'rgba(255,23,68,0.6)','rgba(0,230,118,0.6)').tolist(),name="Volume",opacity=0.8),row=2,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['WT1'],line=dict(color='#00E676',width=2),name="WT1"),row=3,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['WT2'],line=dict(color='#FF1744',width=1.5,dash='dot'),name="WT2"),row=3,col=1)
    wd=dc['WT1']-dc['WT2']
    fig.add_trace(go.Bar(x=dc.index,y=wd,marker_color=np.where(wd>=0,'#00E676','#FF1744').tolist(),name="WT Hist",opacity=0.3),row=3,col=1)
    for lv,cc,d in [(OB2,'#ff3333','dash'),(OB1,'#ff3333','solid'),(0,'gray','dot'),(OS1,'#00bfff','solid'),(OS2,'#00bfff','dash')]:
        fig.add_hline(y=lv,line_dash=d,line_color=cc,line_width=1,row=3,col=1)
    rmfi=dc['RSI_MFI']
    fig.add_trace(go.Bar(x=dc.index,y=rmfi,marker_color=np.where(rmfi>=0,'#3ee145','#ff3d2e').tolist(),name="MF",opacity=0.7),row=4,col=1)
    fig.add_hline(y=0,line_color="gray",line_width=1,row=4,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['MACD_Line'],line=dict(color='#29B6F6',width=1.5),name="MACD"),row=5,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['MACD_Signal'],line=dict(color='#FFA726',width=1.5),name="Signal"),row=5,col=1)
    mhv=dc['MACD_Hist']
    fig.add_trace(go.Bar(x=dc.index,y=mhv,marker_color=np.where(mhv>=0,'#26A69A','#EF5350').tolist(),name="Hist",opacity=0.7),row=5,col=1)
    fig.add_hline(y=0,line_color="#444",line_width=1,row=5,col=1)
    if 'Buy_Total' in dc.columns:
        nj=dc['Buy_Total']-dc['Sell_Total']
        colors=np.where(nj>=10,'#00E676',np.where(nj>=5,'#69F0AE',np.where(nj<=-10,'#FF1744',np.where(nj<=-5,'#FF5252','#FFC107'))))
        fig.add_trace(go.Bar(x=dc.index,y=nj,marker_color=colors.tolist(),name="J NET",opacity=0.8,
            customdata=np.stack([dc['Buy_Total'].values,dc['Sell_Total'].values,dc.get('Trade_Judgment',pd.Series('N/A',index=dc.index)).values,dc.get('Judgment_Confidence',pd.Series(0,index=dc.index)).values],axis=-1),
            hovertemplate="<b>%{customdata[2]}</b> (%{customdata[3]:.0f}%)<br>B:%{customdata[0]:.1f} S:%{customdata[1]:.1f}<br>NET:%{y:.1f}<extra></extra>"),row=6,col=1)
    sb=dc.get('Setup_Pressure_Buy',pd.Series(0,index=dc.index))
    ss=dc.get('Setup_Pressure_Sell',pd.Series(0,index=dc.index))
    an=sb-ss; ac_=np.where(an>=5,'#00E676',np.where(an>=2,'#69F0AE',np.where(an<=-5,'#FF1744',np.where(an<=-2,'#FF5252','#FFC107'))))
    fig.add_trace(go.Bar(x=dc.index,y=an,marker_color=ac_.tolist(),name="Setup NET",opacity=0.7),row=7,col=1)
    ca=dc.get('Composite_Accel',pd.Series(0,index=dc.index))
    fig.add_trace(go.Scatter(x=dc.index,y=ca*3,line=dict(color='#FFD700',width=1.5,dash='dot'),name="Accel×3",opacity=0.6),row=7,col=1)
    fig.add_hline(y=0,line_color="gray",line_width=1,row=7,col=1)

    # ═══ 레이아웃 ═══
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=2, r=2, t=40, b=2),
        height=1400,
        showlegend=True,
        hovermode="closest",
        hoverlabel=dict(
            bgcolor="rgba(14,17,23,0.95)",
            font_size=12,
            font_family="Pretendard"
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="center", x=0.5,
            font=dict(size=9.5, color='#CCC'),
            bgcolor='rgba(0,0,0,0)'
        )
    )

    for i in range(1, 8):
        ya = f'yaxis{i}' if i > 1 else 'yaxis'
        fig.update_layout(**{ya: dict(
            gridcolor='rgba(45,51,59,0.5)',
            zerolinecolor='rgba(60,63,70,0.6)',
            tickfont=dict(size=10, color='#888')
        )})

    # 거래일이 아닌 날짜를 모두 제외 (주말 + 공휴일 + 휴장일)
    all_calendar_days = pd.date_range(
        start=dc.index[0], end=dc.index[-1], freq='D')
    trading_days = dc.index.normalize()
    non_trading_days = all_calendar_days.difference(trading_days)

    fig.update_xaxes(
        rangeslider_visible=False,
        showspikes=True,
        spikecolor="#667eea",
        spikemode="across",
        spikethickness=1,
        spikedash="dot",
        rangebreaks=[dict(values=non_trading_days.tolist())],
        gridcolor='rgba(45,51,59,0.5)',
        gridwidth=1,
        tickfont=dict(size=10, color='#888')
    )
    fig.update_yaxes(
        showspikes=True,
        spikecolor="#667eea",
        spikemode="across",
        spikethickness=1,
        spikedash="dot"
    )

    for ann in fig['layout']['annotations']:
        ann['font'] = dict(size=12, color='#AAA', family='Pretendard')

    return fig

# ══════════════════════════════════════════
#  메타데이터 + 프롬프트 + 분석
# ══════════════════════════════════════════
def build_metadata(dc, dv, ticker):
    lat,prev=dc.iloc[-1],dc.iloc[-2] if len(dc)>=2 else dc.iloc[-1]
    pc=lat['Close']-prev['Close']; pp=pc/(prev['Close']+1e-10)*100
    m4={k:float(lat[c]) for k,c in [('wt1','WT1'),('rsi','RSI'),('mfi','MFI'),('mf_area','RSI_MFI'),('stochk','StochK')]}
    m4['composite_accel']=float(lat.get('Composite_Accel',0))
    m4['supertrend_dir']=int(lat.get('ST_Direction',0))
    m4['plus_di']=float(lat.get('Plus_DI',0)); m4['minus_di']=float(lat.get('Minus_DI',0))
    h1=bool(lat.get('_HTF1_Bull',False)); h2=bool(lat.get('_HTF2_Bull',False))
    bias,bsc=compute_bias(m4,h1,h2)
    regime='STRONG BULL 🟢' if lat.get('Strong_Bull',False) else ('STRONG BEAR 🔴' if lat.get('Strong_Bear',False) else 'NEUTRAL ⚪')
    spl=[]
    for cond,lab in [('Parabolic_Blowoff','🌡️PARA TOP'),('ST_Bear_Override','📉ST BEAR'),('Parabolic_Bottom_Raw','🧊PARA BOT')]:
        if lat.get(cond,False): spl.append(lab)
    shield_str=' + '.join(spl)
    sig_checks=[(k,v['icon'],v['label'],v['dir']) for k,v in ALL_CHART_SIGNALS.items()]
    recent=[]
    for ir,row in dc.tail(15).iterrows():
        ds=ir.strftime('%m/%d')
        for col,icon,lbl,side in sig_checks:
            if row.get(col,False): recent.append((icon,lbl,ds,side))
    jd=get_judgment_detail(lat)
    jh=[]
    for ir,row in dc.tail(5).iterrows():
        jh_=get_judgment_detail(row)
        jh.append({'date':ir.strftime('%m/%d'),'judgment':jh_['judgment'],'confidence':jh_['confidence'],'buy_total':jh_['buy_total'],'sell_total':jh_['sell_total'],'combos':jh_['active_combos']})
    return {
        'ticker':ticker.upper(),'price':lat['Close'],'price_change':pc,'price_change_pct':pp,
        'volume':lat['Volume'],'avg_volume':dc['Volume'].rolling(20).mean().iloc[-1],
        'wt1':float(lat['WT1']),'wt2':float(lat['WT2']),'rsi':float(lat['RSI']),'mfi':float(lat['MFI']),
        'stochk':float(lat['StochK']),'stochd':float(lat['StochD']),'vwap_osc':float(lat['VWAP_Osc']),
        'mf_area':float(lat['RSI_MFI']),'atr':float(lat['ATR']),'atr_pct':float(lat['ATR'])/(float(lat['Close'])+1e-10)*100,
        'adx':float(lat['ADX']),'plus_di':float(lat['Plus_DI']),'minus_di':float(lat['Minus_DI']),
        'overall_bias':bias,'bias_score':bsc,'confluence_score':float(dc['Confluence_Score'].iloc[-1]),
        'recent_signals':recent,'last_date':dc.index[-1].strftime('%Y-%m-%d'),
        'buy_proximity':float(lat['Buy_Proximity']),'sell_proximity':float(lat['Sell_Proximity']),
        'squeeze_on':bool(lat.get('Squeeze_On',False)),'trend_regime':regime,'shield_status':shield_str,
        'supertrend_dir':int(lat.get('ST_Direction',0)),'supertrend_val':float(lat.get('SuperTrend',0)),
        'ema8':float(lat.get('EMA8',0)),'ema21':float(lat.get('EMA21',0)),
        'bb_up':float(lat.get('BB_Up',0)),'bb_low':float(lat.get('BB_Low',0)),
        'ma50':float(lat.get('MA50',0)),'ma200':float(lat.get('MA200',0)),
        'macd_line':float(lat.get('MACD_Line',0)),'macd_signal':float(lat.get('MACD_Signal',0)),
        'macd_hist':float(lat.get('MACD_Hist',0)),'judgment_detail':jd,'judgment_history':jh,
        'cmf':float(lat.get('CMF',0)),'composite_accel':float(lat.get('Composite_Accel',0)),
        'setup_pressure_buy':float(lat.get('Setup_Pressure_Buy',0)),'setup_pressure_sell':float(lat.get('Setup_Pressure_Sell',0)),
        'wt_conv_speed':float(lat.get('WT_Conv_Speed',0)),'rsi_accel':float(lat.get('RSI_Accel',0)),
        'atr_spike':float(lat.get('ATR_Spike',1.0)),'rs_ratio':float(lat.get('RS_Ratio',1.0)),
        'rs_momentum':float(lat.get('RS_Momentum',0)),
        'vp_poc':float(lat.get('VP_POC',0)),'vp_vah':float(lat.get('VP_VAH',0)),'vp_val':float(lat.get('VP_VAL',0)),
        'regime_score':float(lat.get('Regime_Score',0)),'regime':int(lat.get('Regime',0)),
    },regime,shield_str

def build_prompt_text(dc, meta):
    lat=dc.iloc[-1]; rd=dc.tail(60)
    ps=", ".join([f"'{d.strftime('%Y-%m-%d')}:{r['Close']:.2f}'" for d,r in rd.iterrows()])
    sl=[]
    for ir,row in dc.tail(30).iterrows():
        dd=ir.strftime('%Y-%m-%d')
        for k,v in ALL_CHART_SIGNALS.items():
            if row.get(k,False): sl.append(f"{v['icon']} {v['label']} {dd}")
    st_text="\n".join(sl) if sl else "최근30일시그널없음"
    bp,sp=meta['buy_proximity'],meta['sell_proximity']
    prox=f"BuyProx={bp:.0f}%,SellProx={sp:.0f}%"
    std=f"BULL▲({meta['supertrend_val']:.2f})" if meta['supertrend_dir']==1 else f"BEAR▼({meta['supertrend_val']:.2f})"
    shd=f"Shield:{meta['shield_status']}" if meta['shield_status'] else "Shield:NONE"
    vol=meta.get('volume',0); avg_vol=meta.get('avg_volume',1)
    inds=(f"Vol={vol:,.0f}({vol/avg_vol if avg_vol else 0:.1f}x),"
        f"WT1={lat['WT1']:.1f},WT2={lat['WT2']:.1f},RSI={lat['RSI']:.1f},MFI={lat['MFI']:.1f},"
        f"StK={lat['StochK']:.1f},VWAP={lat['VWAP_Osc']:.2f},MF={lat['RSI_MFI']:.1f},"
        f"ADX={lat['ADX']:.1f},+DI={lat['Plus_DI']:.1f},-DI={lat['Minus_DI']:.1f},"
        f"ATR={meta['atr']:.2f}({meta['atr_pct']:.1f}%),E8={lat['EMA8']:.2f},E21={lat['EMA21']:.2f},ST={std},"
        f"BB=[{meta['bb_up']:.2f}/{meta['bb_low']:.2f}],%B={lat.get('Percent_B',0):.2f},"
        f"M50={meta['ma50']:.2f},M200={meta['ma200']:.2f},"
        f"MACD={meta['macd_line']:.3f}/{meta['macd_signal']:.3f} H={meta['macd_hist']:.3f},"
        f"CMF={meta.get('cmf',0):.3f},Conf={meta['confluence_score']:.1f},"
        f"Bias={meta['overall_bias']}({meta['bias_score']:.1f}),Trend={meta['trend_regime']},{shd},{prox},"
        f"VP_POC={meta.get('vp_poc',0):.2f},VP_VAH={meta.get('vp_vah',0):.2f},VP_VAL={meta.get('vp_val',0):.2f},"
        f"RS={meta.get('rs_ratio',1.0):.3f},ATR_Spike={meta.get('atr_spike',1.0):.1f}x,"
        f"Regime={meta.get('regime',0)}({meta.get('regime_score',0):.1f})")
    jd=meta.get('judgment_detail',{}); j_txt=""
    if jd:
        j_txt=f"\n\n📌 [매매판단]\n  최종: {jd.get('judgment','NEUTRAL')} ({jd.get('confidence',0):.0f}%)\n"
        j_txt+=f"  BUY:{jd.get('buy_total',0):.1f}({jd.get('buy_active',0)}/{NUM_LAYERS}) SELL:{jd.get('sell_total',0):.1f}({jd.get('sell_active',0)}/{NUM_LAYERS})\n"
        bl=jd.get('buy_layers',{}); sla=jd.get('sell_layers',{})
        j_txt+=f"  BUY층: {', '.join(f'{k}={v:.1f}' for k,v in bl.items() if v!=0)}\n"
        j_txt+=f"  SELL층: {', '.join(f'{k}={v:.1f}' for k,v in sla.items() if v!=0)}\n"
        combos=jd.get('active_combos',[])
        if combos: j_txt+=f"  🔥콤보: {', '.join(c['name'] for c in combos)}\n"
        if sp>=80: j_txt+=f"  ⚠️ SellProx={sp:.0f}%\n"
        if bp>=80: j_txt+=f"  ⚠️ BuyProx={bp:.0f}%\n"
        j_txt+=f"  Bias: {meta.get('overall_bias','N/A')} ({meta.get('bias_score',0):.1f})\n"
    antic=f"\n\n📌 [선행지표]\n  MomAccel={meta.get('composite_accel',0):.2f},SetupBuy={meta.get('setup_pressure_buy',0):.1f},SetupSell={meta.get('setup_pressure_sell',0):.1f}\n"
    return f"{ps}\n\n📌 [지표요약]\n{inds}\n\n📌 [최근시그널]\n{st_text}{j_txt}{antic}"

def build_ai_prompt(ticker, phist, fundamentals):
    return f"""━━━ 🎯 Role ━━━
월스트리트 20년+ 퀀트 펀드매니저. 기술적 지표 기반 냉철 분석.
━━━ ✍️ Rules ━━━
1. ATR 기반 손절/목표가 산출 2. 시스템 판단 크로스체크 3. VP POC/VAH/VAL 활용
4. RS_Ratio로 시장대비 강도 판단 5. 시나리오별 확률% 6. 환각금지
7. Regime 스코어로 국면 판단 (양수=상승추세, 음수=하락추세)
8. 상승추세에서 과매수는 정상운행 — 추세 국면에서 RSI 60~80은 건강한 모멘텀
9. ATR_Spike≥2.0이면 변동성 쇼크 경고 10. 시스템 판단과 GRADE 일관성 유지
━━━ 📥 Data ━━━
[{ticker}]
{phist}
📌 [펀더멘탈] {fundamentals}
━━━ 📄 Output ━━━
# 🚦 {{ticker}} 퀀트 리포트
[🔵/🔴/🟠] 핵심 한줄
### 📊 시장심리 (3~4문장)
### ⚖️ 시스템 검증 (판단+확신도+콤보+검증)
### ⏳ 선행지표 (가속도+셋업+수렴+1~3일전망)
### 📈 기술분석 (VP+RS+VolShock+종합)
### 📉 공매도+수급
### 🔮 시나리오 (🔵긍정 🟠베이스 🔴리스크 + ATR전략)
### 결론 (예측+GRADE)"""

def analyze(ticker, chart_days=252, refresh=False):
    try:
        ts=int(time.time()) if refresh else None
        df=compute_and_cache(ticker,ts)
        if df is None or df.empty: return None,"데이터없음",None
        if len(df)<50: return None,f"데이터부족({len(df)}일)",None
        dv=df.dropna(subset=['WT1','WT2']); dc=dv.tail(chart_days).copy()
        if dc.empty: return None,"차트데이터부족",None
        dc=detect_scanner_combos(dc)
        meta,regime,shield=build_metadata(dc,dv,ticker)
        fig=build_chart(dc,ticker,regime,shield)
        return fig,build_prompt_text(dc,meta),meta
    except Exception as e:
        import traceback; print(f"[ERR]{ticker}:{traceback.format_exc()}")
        return None,f"실패:{e}",None

def build_speedometer_gauges(meta):
    cs=meta.get('confluence_score',0); bs=meta.get('bias_score',0); bl=meta.get('overall_bias','NEUTRAL')
    an=meta.get('setup_pressure_buy',0)-meta.get('setup_pressure_sell',0)
    cc='#34D399' if cs>=3.5 else ('#F87171' if cs<=-3.5 else '#FCD34D')
    bcm={'STRONG BUY':'#34D399','BUY':'#6EE7B7','STRONG SELL':'#F87171','SELL':'#FCA5A5','NEUTRAL':'#FCD34D'}
    bc=bcm.get(bl,'#FCD34D'); ac='#34D399' if an>3 else ('#F87171' if an<-3 else '#FCD34D')
    fig=make_subplots(rows=1,cols=3,specs=[[{"type":"indicator"}]*3],horizontal_spacing=0.06)
    for i,(val,title,clr,rng) in enumerate([(cs,"🔥 Confluence",cc,[-10,10]),(bs,f"🧭 {bl}",bc,[-13,13]),(an,"⏳ Anticipation",ac,[-12,12])],1):
        fig.add_trace(go.Indicator(mode="gauge+number",value=val,
            number=dict(font=dict(size=26,color="#F8FAFC")),
            title=dict(text=f"<b>{title}</b>",font=dict(size=12,color="#94A3B8")),
            gauge=dict(axis=dict(range=rng),bar=dict(color=clr,thickness=0.3),
                bgcolor="rgba(15,19,32,0.9)",borderwidth=1,bordercolor="#1E293B",
                threshold=dict(line=dict(color="#F8FAFC",width=3),thickness=0.8,value=val))),row=1,col=i)
    fig.update_layout(template="plotly_dark",paper_bgcolor="rgba(0,0,0,0)",height=220,margin=dict(l=15,r=15,t=50,b=10))
    return fig


# ══════════════════════════════════════════
#  UI 렌더
# ══════════════════════════════════════════
def render_judgment(meta):
    jd=meta.get('judgment_detail')
    if not jd: return
    j=jd['judgment']; bt=jd['buy_total']; st_=jd['sell_total']; net=bt-st_; cf=jd.get('confidence',0)
    cc='judgment-card-buy' if 'BUY' in j else ('judgment-card-sell' if 'SELL' in j else 'judgment-card-neutral')
    jl,jc,_=JUDGMENT_CONFIG.get(j,('⚪ NEUTRAL','#64748B',''))
    nc='#34D399' if net>0 else ('#F87171' if net<0 else '#FCD34D')
    cbc=jc if cf>=60 else ('#FCD34D' if cf>=30 else '#475569')
    st.markdown(f"""<div class="judgment-card {cc}">
        <p style="font-size:2rem;font-weight:800;color:{jc};margin:0">{jl}</p>
        <div style="display:flex;align-items:center;gap:10px;justify-content:center;margin-top:8px">
            <div style="flex:0 0 200px;height:8px;background:#151921;border-radius:4px;overflow:hidden">
                <div style="width:{min(cf,100)}%;height:8px;background:{cbc};border-radius:4px"></div></div>
            <span style="color:{cbc};font-weight:800;font-size:1.1rem">{cf:.0f}%</span></div>
        <div style="display:flex;justify-content:center;gap:32px;margin-top:14px">
            <div><p style="color:#64748B;font-size:.7rem;margin:0">BUY</p><p style="color:#34D399;font-size:1.4rem;font-weight:800;margin:2px 0">{bt:.1f}</p></div>
            <div style="border-left:1px solid rgba(255,255,255,0.08);padding-left:32px"><p style="color:#64748B;font-size:.7rem;margin:0">SELL</p><p style="color:#F87171;font-size:1.4rem;font-weight:800;margin:2px 0">{st_:.1f}</p></div>
            <div style="border-left:1px solid rgba(255,255,255,0.08);padding-left:32px"><p style="color:#64748B;font-size:.7rem;margin:0">NET</p><p style="color:{nc};font-size:1.4rem;font-weight:800;margin:2px 0">{net:+.1f}</p></div></div></div>""",unsafe_allow_html=True)
    # 국면 표시
    rg=meta.get('regime',0); rgs=meta.get('regime_score',0)
    rgl={2:'🟢🟢 STRONG UPTREND',1:'🟢 UPTREND',0:'⚪ RANGING',-1:'🔴 DOWNTREND',-2:'🔴🔴 STRONG DOWNTREND'}.get(rg,'?')
    rgc='#34D399' if rg>=1 else ('#F87171' if rg<=-1 else '#FCD34D')
    st.markdown(f"<div style='text-align:center;padding:8px;border-radius:8px;background:rgba(255,255,255,0.02);margin:6px 0'><span style='color:{rgc};font-weight:700'>국면: {rgl} ({rgs:+.1f})</span></div>",unsafe_allow_html=True)
    combos=jd.get('active_combos',[])
    st.markdown("#### 🔥 활성 콤보")
    if combos:
        for cb in combos:
            ccc='combo-buy' if cb['dir']=='buy' else 'combo-sell'; dc_='#34D399' if cb['dir']=='buy' else '#F87171'
            tc='#FFD700' if cb.get('tier',2)==1 else '#C0C0C0'
            st.markdown(f"<div class='combo-card {ccc}'><span style='color:{dc_};font-size:1.2rem'>●</span><span style='color:#E8ECF1;font-weight:700'> {cb['name']}</span><span style='color:{tc};font-size:.7rem;padding:2px 6px;border-radius:4px;background:rgba(255,255,255,0.05)'>T{cb.get('tier',2)}</span></div>",unsafe_allow_html=True)
    else:
        st.markdown("<div class='combo-card' style='background:rgba(245,158,11,.04);border:1px solid rgba(245,158,11,.15);border-left:3px solid #F59E0B;justify-content:center'><span style='color:#FCD34D;font-weight:600'>⏸️ 활성 콤보 없음</span></div>",unsafe_allow_html=True)
    st.markdown("#### 📊 8-Layer 스코어")
    c1,c2=st.columns(2)
    with c1:
        st.markdown("<p style='color:#34D399;font-weight:700;font-size:.85rem'>▲ BUY</p>",unsafe_allow_html=True)
        _render_layer_bars(jd['buy_layers'],'buy',jd['buy_active'])
    with c2:
        st.markdown("<p style='color:#F87171;font-weight:700;font-size:.85rem'>▼ SELL</p>",unsafe_allow_html=True)
        _render_layer_bars(jd['sell_layers'],'sell',jd['sell_active'])

def _render_layer_bars(layers, side, active):
    icons={'Trend':'📈','Momentum':'🔥','Candle':'🕯️','BB':'📊','Volume':'📦','MF':'💰','Pattern':'⭐','Anticipation':'⏳'}
    fc='layer-bar-fill-buy' if side=='buy' else 'layer-bar-fill-sell'
    sc_='#34D399' if side=='buy' else '#F87171'; total=sum(max(0,v) for v in layers.values())
    for nm,s in layers.items():
        ic=icons.get(nm,'•'); pct=min(max(s,0)/10*100,100); op='1' if s>0 else '0.3'
        dc_=sc_ if s>=0 else ('#F87171' if side=='buy' else '#34D399')
        st.markdown(f"<div class='layer-bar-wrap'><div style='display:flex;justify-content:space-between;margin-bottom:3px'><span style='color:#94A3B8;font-size:.8rem;opacity:{op}'>{ic} {nm}</span><span style='color:{dc_};font-weight:700;font-size:.8rem;opacity:{op}'>{s:.1f}</span></div><div class='layer-bar-bg'><div class='layer-bar-fill {fc}' style='width:{pct}%;opacity:{op}'></div></div></div>",unsafe_allow_html=True)
    st.markdown(f"<div style='margin-top:12px;padding:10px;border-radius:10px;background:rgba(255,255,255,0.02);text-align:center'><span style='color:{sc_};font-weight:800;font-size:1.15rem'>{total:.1f}</span> <span style='color:#475569;font-size:.8rem'>점 · 활성 </span><span style='color:#CBD5E1;font-weight:700'>{active}</span><span style='color:#475569;font-size:.8rem'>/{NUM_LAYERS}</span></div>",unsafe_allow_html=True)

def render_price_header(m):
    chg=m['price_change']; cp=m['price_change_pct']; cc='price-change-up' if chg>=0 else 'price-change-down'
    ci='▲' if chg>=0 else '▼'; vr=m['volume']/m['avg_volume'] if m['avg_volume'] else 0
    jd=m.get('judgment_detail',{}); js=jd.get('judgment','N/A'); cf=jd.get('confidence',0)
    accel=m.get('composite_accel',0)
    jcm={'STRONG_BUY':'ind-bullish','BUY':'ind-bullish','WATCH_BUY':'ind-neutral','STRONG_SELL':'ind-bearish','SELL':'ind-bearish','WATCH_SELL':'ind-neutral','MIXED':'ind-neutral','NEUTRAL':'ind-neutral'}
    specs=[(jcm.get(js,'ind-neutral'),f"📍{js}({cf:.0f}%)"),(_cls(m['wt1'],-20,20),f"WT{m['wt1']:.0f}"),
        (_cls(m['rsi'],40,60),f"RSI{m['rsi']:.0f}"),('ind-bullish' if vr>1.5 else 'ind-neutral',f"Vol{vr:.1f}x"),
        ('ind-bullish' if m['adx']>25 else 'ind-neutral',f"ADX{m['adx']:.0f}"),
        ('ind-bullish' if accel>JT.ACCEL_MODERATE else ('ind-bearish' if accel<-JT.ACCEL_MODERATE else 'ind-neutral'),f"Accel{accel:+.1f}"),
        ('ind-bullish' if m.get('rs_ratio',1)>1.03 else ('ind-bearish' if m.get('rs_ratio',1)<0.97 else 'ind-neutral'),f"RS{m.get('rs_ratio',1):.2f}")]
    ih="".join([f"<span class='indicator-mini {c}'>{l}</span>" for c,l in specs])
    tr=m.get('trend_regime','NEUTRAL ⚪')
    st.markdown(f"""<div class="price-header"><div style="display:flex;justify-content:space-between"><div>
        <p class="price-label">🚦 {m['ticker']} · {m['last_date']} · <b style="color:#A5B4FC">{tr}</b></p>
        <p class="price-big" style="color:#F8FAFC">${m['price']:.2f}<span class="{cc}" style="font-size:1.1rem;margin-left:10px;font-weight:700">{ci}{abs(chg):.2f}({abs(cp):.2f}%)</span></p></div>
        <div style="text-align:right"><p class="price-label">ATR(14)</p><p style="color:#FCD34D;font-size:1.2rem;font-weight:700;margin:2px 0">${m['atr']:.2f}({m['atr_pct']:.1f}%)</p></div></div>
        <div style="margin-top:12px;display:flex;gap:5px;flex-wrap:wrap">{ih}</div></div>""",unsafe_allow_html=True)
    c1,c2,c3,c4,c5=st.columns(5)
    with c1: st.metric("BUY",f"{jd.get('buy_total',0):.1f}",delta=f"{jd.get('buy_active',0)}/{NUM_LAYERS}")
    with c2: st.metric("SELL",f"{jd.get('sell_total',0):.1f}",delta=f"{jd.get('sell_active',0)}/{NUM_LAYERS}",delta_color="inverse")
    with c3: nv=jd.get('buy_total',0)-jd.get('sell_total',0); st.metric("NET",f"{nv:+.1f}",delta=js,delta_color="normal" if nv>0 else "inverse")
    with c4: st.metric("Conf",f"{cf:.0f}%",delta=m.get('overall_bias','N/A'),delta_color="normal" if cf>=60 else "off")
    with c5: ant=m.get('setup_pressure_buy',0)-m.get('setup_pressure_sell',0); st.metric("⏳Antic",f"{ant:+.1f}",delta=f"Accel{accel:+.1f}",delta_color="normal" if ant>0 else ("inverse" if ant<0 else "off"))

def render_alerts(m):
    alerts=[]; bp,sp=m.get('buy_proximity',0),m.get('sell_proximity',0)
    if bp>=70: alerts.append(('🟢⚡ 매수임박!','#34D399','rgba(16,185,129,.08)',bp))
    if sp>=70: alerts.append(('🔴⚡ 매도임박!','#F87171','rgba(239,68,68,.08)',sp))
    if m.get('squeeze_on'): alerts.append(('💥 Squeeze ON','#FCD34D','rgba(245,158,11,.06)',80))
    accel=m.get('composite_accel',0)
    if accel>JT.ACCEL_STRONG: alerts.append(('⚡ 강한상승가속','#34D399','rgba(16,185,129,.06)',70))
    elif accel<-JT.ACCEL_STRONG: alerts.append(('⚡ 강한하락가속','#F87171','rgba(239,68,68,.06)',70))
    asp=m.get('atr_spike',1.0)
    if asp>=2.0: alerts.insert(0,(f'🔥 VOL SHOCK (ATR{asp:.1f}x)','#FF6600','rgba(255,102,0,.08)',90))
    jd=m.get('judgment_detail',{}); j=jd.get('judgment','NEUTRAL'); cf=jd.get('confidence',0)
    if j=='STRONG_BUY': alerts.insert(0,(f'🟢🟢🟢 STRONG BUY({cf:.0f}%)','#34D399','rgba(16,185,129,.1)',95))
    elif j=='STRONG_SELL': alerts.insert(0,(f'🔴🔴🔴 STRONG SELL({cf:.0f}%)','#F87171','rgba(239,68,68,.1)',95))
    for txt,clr,bg,pct in alerts:
        st.markdown(f"<div class='alert-bar' style='background:{bg}'><div style='display:flex;justify-content:space-between'><span style='color:{clr};font-weight:700;font-size:.9rem'>{txt}</span><span style='color:{clr};font-weight:800'>{pct:.0f}%</span></div><div class='alert-bar-progress'><div class='alert-bar-fill' style='background:{clr};width:{min(pct,100)}%'></div></div></div>",unsafe_allow_html=True)

def render_signals(m):
    sigs=m['recent_signals']
    if not sigs: st.info("최근 15일 시그널 없음"); return
    dg=OrderedDict()
    for icon,lbl,ds,side in sigs: dg.setdefault(ds,[]).append((icon,lbl,side))
    for ds in reversed(dg):
        grp=dg[ds]; bc=sum(1 for _,_,s in grp if s=='buy'); sc=sum(1 for _,_,s in grp if s=='sell')
        ct='signal-card-buy' if bc>sc else ('signal-card-sell' if sc>bc else 'signal-card-neutral')
        parts=[f"<span class='indicator-mini {'ind-bullish' if s=='buy' else ('ind-bearish' if s=='sell' else 'ind-neutral')}'>{i} {l}</span>" for i,l,s in grp]
        st.markdown(f"<div class='signal-card {ct}'><div style='display:flex;justify-content:space-between;margin-bottom:8px'><span style='font-weight:700;color:#E8ECF1'>📅 {ds}</span><span style='color:#64748B;font-size:.75rem'>{len(grp)}개</span></div><div style='display:flex;gap:5px;flex-wrap:wrap'>{' '.join(parts)}</div></div>",unsafe_allow_html=True)

def render_analysis(msg):
    m,fig=msg.get('meta'),msg.get('fig')
    if m: render_price_header(m); st.plotly_chart(build_speedometer_gauges(m),use_container_width=True,theme=None,config={'displayModeBar':False}); render_alerts(m)
    if m or fig:
        t0,t1,t2,t3,t4=st.tabs(["차트","매매판단","시그널","선행지표","기업상세"])
        with t0:
            if fig: st.plotly_chart(fig,use_container_width=True,theme=None,config={'displaylogo':False,'modeBarButtonsToRemove':['lasso2d','select2d']})
        with t1:
            if m: render_judgment(m)
        with t2:
            if m: render_signals(m)
        with t3:
            if m:
                accel=m.get('composite_accel',0); sbv=m.get('setup_pressure_buy',0); ssv=m.get('setup_pressure_sell',0)
                if accel>JT.ACCEL_STRONG: st.success(f"🟢🟢 강한상승가속 ({accel:+.2f})")
                elif accel>JT.ACCEL_MODERATE: st.info(f"🟢 상승가속 ({accel:+.2f})")
                elif accel<-JT.ACCEL_STRONG: st.error(f"🔴🔴 강한하락가속 ({accel:+.2f})")
                elif accel<-JT.ACCEL_MODERATE: st.warning(f"🔴 하락가속 ({accel:+.2f})")
                c1,c2=st.columns(2)
                with c1: st.metric("BUY 셋업",f"{sbv:.1f}",delta="축적중" if sbv>=5 else "부족",delta_color="normal" if sbv>=5 else "off")
                with c2: st.metric("SELL 셋업",f"{ssv:.1f}",delta="축적중" if ssv>=5 else "부족",delta_color="inverse" if ssv>=5 else "off")
        with t4:
            if m: render_company_details(m['ticker'])


# ══════════════════════════════════════════
#  사이드바 + 세션 + 챗
# ══════════════════════════════════════════
def init_session_state():
    defaults={'messages':[{"role":"assistant","type":"text","content":"안녕하세요! 🚦 **CipherX v12.2** 입니다.\n\n분석할 **티커명**을 입력하세요."}],
        'pending_ai_ticker':None,'pending_ai_prompt':None,'last_ticker':None,
        'enabled_signals':set(ALL_CHART_SIGNALS.keys()),
        'enabled_judgments':{'STRONG_BUY','BUY','SELL','STRONG_SELL'},
        'show_scanner_combos':True,'sig_display_level':'⭐ 핵심만 (Tier A)'}
    for k,v in defaults.items():
        if k not in st.session_state: st.session_state[k]=v
init_session_state()

with st.sidebar:
    st.markdown("## 🚦 CipherX"); st.markdown("<p style='color:#888;font-size:.8rem'>v12.2 Regime-Aware</p>",unsafe_allow_html=True); st.markdown("---")
    app_mode=st.radio("모드",['📊 개별분석','🔍 스캐너'],index=0,key="app_mode"); st.markdown("---")
    chart_period=st.radio("차트기간",['3개월','6개월','1년','2년'],index=0,horizontal=True,key="period")
    chart_days={'3개월':63,'6개월':126,'1년':252,'2년':504}[chart_period]; st.markdown("---")
    with st.expander("🎛️ 설정",expanded=False):
        _ss=st.checkbox("🟢🔴 STRONG",value=False,key="j_s"); _sn=st.checkbox("🟢🔴 BUY/SELL",value=False,key="j_n")
        _sw=st.checkbox("🟡 WATCH",value=False,key="j_w"); _sm=st.checkbox("🟠 MIXED",value=False,key="j_m")
        ej=set()
        if _ss: ej|={'STRONG_BUY','STRONG_SELL'}
        if _sn: ej|={'BUY','SELL'}
        if _sw: ej|={'WATCH_BUY','WATCH_SELL'}
        if _sm: ej.add('MIXED')
        st.session_state['enabled_judgments']=ej
        st.session_state['sig_display_level']=st.radio("시그널표시",['⭐ 핵심만 (Tier A)','📊 핵심+보조 (A+B)','🔍 전체'],index=1,key="sig_disp")
    if st.button("🗑️ 초기화",use_container_width=True,type="secondary"):
        for k in ['messages','pending_ai_ticker','pending_ai_prompt','last_ticker']:
            st.session_state[k]=[{"role":"assistant","type":"text","content":"안녕하세요! 🚦 **CipherX v12.2**"}] if k=='messages' else None
        st.rerun()

def _check_qp():
    try:
        t=st.query_params.get("ticker",None)
        if t and st.session_state.last_ticker!=t.upper(): return t.upper()
    except: pass
    return None
url_ticker=_check_qp()

if st.session_state.get('app_mode')=='🔍 스캐너':
    st.markdown("<h2 style='text-align:center;color:#fff'>🔍 CipherX Scanner</h2>",unsafe_allow_html=True)
    st.markdown("#### 📋 티커 입력")
    ci=st.text_input("쉼표구분",placeholder="NVDA,TSLA,AAPL,QQQ,...",key="scan_input")
    tickers=[t.strip().upper() for t in ci.split(',') if t.strip()] if ci else ['NVDA','TSLA','AAPL','MSFT','AMZN','META','AMD','NFLX','QQQ','SPY']
    if st.button("🚀 스캔",type="primary",use_container_width=True):
        pb=st.progress(0); results=scan_multiple_tickers(tickers,lambda p,t:pb.progress(p,text=t))
        pb.progress(1.0,text=f"✅ {len(results)}개 발견"); time.sleep(0.5); pb.empty()
        if not results: st.info("콤보없음")
        else:
            for r in results:
                chg=r['change_pct']; chc='#34D399' if chg>=0 else '#F87171'; chi='▲' if chg>=0 else '▼'
                chtml="".join([f"<div style='display:flex;align-items:center;gap:8px;padding:4px 0'><span style='color:{'#34D399' if c['dir']=='buy' else '#F87171'}'>●</span><span style='color:#E8ECF1;font-weight:600;font-size:.85rem'>{c['icon']} {c['kor']}</span><span style='color:#64748B;font-size:.7rem'>{c['date']}</span></div>" for c in r['active_combos']])
                st.markdown(f"<div style='background:linear-gradient(160deg,#0F1320,#141926);border:1px solid #1C2233;border-radius:14px;padding:16px 20px;margin:8px 0'><div style='display:flex;justify-content:space-between;margin-bottom:10px'><span style='color:#A5B4FC;font-weight:800;font-size:1.2rem'>{r['ticker']}</span><span style='color:{chc};font-size:.85rem;font-weight:600'>{chi}{abs(chg):.1f}%</span></div>{chtml}</div>",unsafe_allow_html=True)
                if st.button(f"📊 {r['ticker']} 분석",key=f"sc_{r['ticker']}",use_container_width=True):
                    st.session_state['app_mode']='📊 개별분석'; st.session_state['_auto_ticker']=r['ticker']; st.rerun()
else:
    st.markdown("<h2 style='text-align:center;color:#fff;margin-bottom:20px'>🚦 CipherX</h2>",unsafe_allow_html=True)
    if not st.session_state.last_ticker:
        cols=st.columns(4)
        for i,t in enumerate(["NVDA","TSLA","AAPL","QQQ"]):
            with cols[i]:
                if st.button(t,use_container_width=True): st.session_state['quick_ticker']=t
    for i,msg in enumerate(st.session_state.messages):
        av="✨" if msg["role"]=="assistant" else "🧑‍💻"
        with st.chat_message(msg["role"],avatar=av):
            if msg.get("type")=="analysis":
                st.markdown(msg.get("content","")); render_analysis(msg)
                if msg.get("prompt"):
                    with st.expander("📝 프롬프트",expanded=False): st.code(msg["prompt"],language="markdown"); st_copy_to_clipboard(msg["prompt"],before_copy_label="📋복사",after_copy_label="✅복사됨!")
            elif msg.get("type")=="report":
                with st.expander(f"📊 {msg.get('ticker','')} AI리포트",expanded=True): st.markdown(msg["content"])
                st.download_button("📥 다운로드",key=f"dl_{i}",data=msg["content"].encode('utf-8'),file_name=f"{msg.get('ticker','')}_Quant_{datetime.now().strftime('%Y%m%d_%H%M')}.md",mime="text/markdown",use_container_width=True)
            else: st.markdown(msg.get("content",""))

    def _run_ai():
        tp=st.session_state.pending_ai_ticker; pp=st.session_state.pending_ai_prompt
        with st.chat_message("assistant",avatar="✨"):
            pb=st.progress(0,text="로딩...")
            try:
                model=get_gemini_model(); pb.progress(20); collected=[]
                def gen():
                    pb.progress(40,text="🚀 AI생성중...")
                    for chunk in model.generate_content(pp,stream=True):
                        if chunk.text: collected.append(chunk.text); yield chunk.text
                    pb.progress(100,text="✅ 완료!")
                with st.expander(f"📊 {tp.upper()} AI리포트",expanded=True): st.write_stream(gen())
                time.sleep(0.3); pb.empty()
                st.session_state.messages.append({"role":"assistant","type":"report","ticker":tp.upper(),"content":"".join(collected)})
                st.session_state.pending_ai_ticker=None; st.session_state.pending_ai_prompt=None; st.rerun()
            except Exception as e: pb.empty(); st.error(f"AI오류:{e}")

    def process_ticker(tv,refresh=False):
        tv=tv.strip().upper(); st.session_state.pending_ai_ticker=None; st.session_state.pending_ai_prompt=None
        if not _valid_fmt(tv): st.toast(f"⚠️ {tv} 형식오류",icon="🚨"); return
        if not validate_ticker(tv): st.toast(f"⚠️ {tv} 데이터없음",icon="🔍"); return
        st.session_state.messages.append({"role":"user","type":"text","content":tv}); st.session_state.last_ticker=tv
        try: st.query_params["ticker"]=tv
        except: pass
        with st.chat_message("assistant",avatar="✨"):
            with st.status(f"🌐 {tv} 분석중...",expanded=True) as status:
                st.write("📡 데이터수집..."); fundamentals=fetch_fundamentals(tv)
                st.write("📊 지표+시그널+8-Layer+국면분석...")
                fig,phist,meta=analyze(tv,chart_days,refresh)
                if fig:
                    jd=meta.get('judgment_detail',{}); j=jd.get('judgment','N/A'); cf=jd.get('confidence',0)
                    st.write(f"🏷️ 판단: **{j}** ({cf:.0f}%)")
                    prompt=build_ai_prompt(tv,phist,fundamentals)
                    status.update(label=f"✅ {tv} 완료!",state="complete",expanded=False)
                else: prompt=None; status.update(label=f"⚠️ {tv} 실패",state="error",expanded=False)
            if fig:
                st.session_state.messages.append({"role":"assistant","type":"analysis","ticker":tv,"content":f"✅ **{tv}** 분석완료.","fig":fig,"meta":meta,"prompt":prompt})
                st.session_state.pending_ai_ticker=tv; st.session_state.pending_ai_prompt=prompt; st.rerun()
            else:
                st.session_state.messages.append({"role":"assistant","type":"text","content":f"⚠️ **{tv}** 실패: {phist}"}); st.rerun()

    if url_ticker and 'url_loaded' not in st.session_state: st.session_state['url_loaded']=True; process_ticker(url_ticker)
    if st.session_state.get('_auto_ticker'): at=st.session_state.pop('_auto_ticker'); process_ticker(at)
    if st.session_state.get('quick_ticker'): qt=st.session_state.pop('quick_ticker'); process_ticker(qt)
    if st.session_state.pending_ai_ticker and st.session_state.pending_ai_prompt:
        if st.button(f"🚀 {st.session_state.pending_ai_ticker.upper()} AI분석",type="primary",use_container_width=True): _run_ai()
    if ti:=st.chat_input("티커 입력 (예: TSLA, AAPL, QQQ)"): process_ticker(ti)