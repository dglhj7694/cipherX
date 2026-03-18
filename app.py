# ══════════════════════════════════════════════════════════════
#  CipherX V12.0 + Custom Scanner — FULL INTEGRATED CODE
#  PART 1/4: 임포트 + 상수 + 스캐너 콤보 정의 + 지표/패턴 엔진
# ══════════════════════════════════════════════════════════════

import streamlit as st
import google.generativeai as genai
import time, re
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

st.set_page_config(page_title="CipherX V12.0", page_icon="📈",
                    layout="centered", initial_sidebar_state="collapsed")

# ──────────────────────────────────────────
# CSS
# ──────────────────────────────────────────
def inject_css():
    st.markdown("""<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
html,body,[class*="css"]{font-family:'Pretendard','Noto Sans KR',sans-serif!important}
.stApp{background-color:#0B0E14}
p,div[data-testid="stMarkdownContainer"] p,div[data-testid="stChatMessageContent"] p,
li{color:#E8ECF1!important}
h1{color:#FFFFFF!important;font-weight:800!important}
h2{color:#FFFFFF!important;font-weight:700!important}
h3{color:#F0F4F8!important;font-weight:700!important}
h4{color:#CBD5E1!important;font-weight:600!important;font-size:1rem!important;
   margin-top:1.5rem!important;margin-bottom:0.8rem!important;
   padding-bottom:6px;border-bottom:1px solid rgba(255,255,255,0.06)}
div[data-testid="stCodeBlock"],pre,code{background-color:#151921!important;color:#E2E8F0!important;
    border:1px solid #1E2530!important;border-radius:10px!important}
div[data-testid="stChatMessage"]:nth-child(even){background-color:#10141C;border-radius:14px;
    padding:8px 18px;border:1px solid rgba(255,255,255,0.03)}
.block-container{padding-top:1rem!important;max-width:960px}
@media(max-width:768px){.block-container{padding-left:.5rem!important;padding-right:.5rem!important}
    .price-big{font-size:1.6rem!important}}
div.stButton>button[kind="primary"]{
    background:linear-gradient(135deg,#6366F1 0%,#8B5CF6 50%,#A78BFA 100%)!important;
    color:white!important;border:none!important;border-radius:12px!important;
    padding:.65rem 1.5rem!important;font-weight:700!important;font-size:1rem!important;
    width:100%;box-shadow:0 4px 14px rgba(99,102,241,.3)!important}
div.stButton>button[kind="primary"]:hover{transform:translateY(-2px);
    box-shadow:0 8px 25px rgba(139,92,246,.45)!important}
div.stButton>button[kind="secondary"]{
    background-color:#12161F!important;color:#C4CDD8!important;
    border:1px solid #2A3040!important;border-radius:12px!important;
    font-weight:600!important;width:100%}
div.stButton>button[kind="secondary"]:hover{border-color:#6366F1!important;color:#A5B4FC!important}
.streamlit-expanderHeader{background-color:#10141C!important;border-radius:12px!important;font-weight:700!important}
div[data-testid="stExpander"]{border:1px solid #1C2233!important;border-radius:12px!important;
    background-color:#0D1017;overflow:hidden}
div[data-testid="stExpanderDetails"] p,div[data-testid="stExpanderDetails"] li{
    font-size:.95rem!important;line-height:1.7!important;color:#B8C5D3!important}
header{background-color:transparent!important}
section[data-testid="stSidebar"]{background-color:#080A10;border-right:1px solid #151921}
.signal-card{border-radius:14px;padding:14px 18px;margin:8px 0;
    border:1px solid rgba(255,255,255,0.06)}
.signal-card-buy{background:linear-gradient(135deg,rgba(0,230,118,.06),rgba(16,185,129,.03));
    border-left:4px solid #10B981}
.signal-card-sell{background:linear-gradient(135deg,rgba(239,68,68,.06),rgba(220,38,38,.03));
    border-left:4px solid #EF4444}
.signal-card-neutral{background:linear-gradient(135deg,rgba(245,158,11,.06),rgba(217,119,6,.03));
    border-left:4px solid #F59E0B}
.price-header{background:linear-gradient(160deg,#0F1320,#141926,#111827);
    border:1px solid #1C2233;border-radius:16px;padding:20px 24px;margin-bottom:18px;
    box-shadow:0 4px 20px rgba(0,0,0,0.3)}
.price-big{font-size:2.2rem;font-weight:800;margin:0}
.price-change-up{color:#34D399!important}
.price-change-down{color:#F87171!important}
.price-label{color:#64748B!important;font-size:.8rem;margin:0;font-weight:500;
    text-transform:uppercase;letter-spacing:0.5px}
.indicator-mini{display:inline-block;padding:5px 11px;margin:3px;border-radius:8px;
    font-size:.78rem;font-weight:600;border:1px solid rgba(255,255,255,0.04)}
.ind-bullish{background:rgba(16,185,129,.12);color:#6EE7B7;border-color:rgba(16,185,129,.2)}
.ind-bearish{background:rgba(239,68,68,.12);color:#FCA5A5;border-color:rgba(239,68,68,.2)}
.ind-neutral{background:rgba(245,158,11,.10);color:#FCD34D;border-color:rgba(245,158,11,.15)}
div[data-testid="stTabs"] button{color:#64748B!important;font-weight:700!important;
    border-bottom:3px solid transparent!important}
div[data-testid="stTabs"] button[aria-selected="true"]{color:#A5B4FC!important;
    border-bottom-color:#6366F1!important}
.judgment-card{border-radius:16px;padding:24px 28px;margin-bottom:20px;text-align:center;
    position:relative;overflow:hidden}
.judgment-card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px}
.judgment-card-buy{background:linear-gradient(160deg,#052E16,#0D1B2A);
    border:1px solid rgba(16,185,129,.25)}
.judgment-card-buy::before{background:linear-gradient(90deg,#10B981,#34D399)}
.judgment-card-sell{background:linear-gradient(160deg,#2A0E0E,#1B0D1B);
    border:1px solid rgba(239,68,68,.25)}
.judgment-card-sell::before{background:linear-gradient(90deg,#EF4444,#F87171)}
.judgment-card-neutral{background:linear-gradient(160deg,#1A1608,#1B1A0D);
    border:1px solid rgba(245,158,11,.2)}
.judgment-card-neutral::before{background:linear-gradient(90deg,#F59E0B,#FCD34D)}
.combo-card{border-radius:12px;padding:12px 16px;margin:6px 0;display:flex;
    align-items:center;justify-content:space-between;border:1px solid rgba(255,255,255,0.06)}
.combo-buy{background:linear-gradient(135deg,rgba(16,185,129,.08),rgba(6,78,59,.05));
    border-left:3px solid #10B981}
.combo-sell{background:linear-gradient(135deg,rgba(239,68,68,.08),rgba(127,29,29,.05));
    border-left:3px solid #EF4444}
.layer-bar-wrap{padding:4px 0}
.layer-bar-bg{background:#151921;border-radius:6px;height:10px;overflow:hidden;
    border:1px solid rgba(255,255,255,0.03)}
.layer-bar-fill{height:10px;border-radius:6px}
.layer-bar-fill-buy{background:linear-gradient(90deg,#059669,#34D399)}
.layer-bar-fill-sell{background:linear-gradient(90deg,#DC2626,#F87171)}
.history-row{display:flex;align-items:center;padding:8px 14px;margin:4px 0;
    border-radius:10px;background:rgba(255,255,255,0.015);border:1px solid rgba(255,255,255,0.04)}
.alert-bar{border-radius:10px;padding:10px 16px;margin:5px 0;border:1px solid rgba(255,255,255,0.06)}
.alert-bar-progress{background:#151921;border-radius:4px;height:5px;margin-top:8px;overflow:hidden}
.alert-bar-fill{height:5px;border-radius:4px}
.scanner-card{border-radius:14px;padding:16px 20px;margin:8px 0;
    background:linear-gradient(160deg,#0F1320,#141926);border:1px solid #1C2233}
.scanner-card-highlight{border-color:#FFD700;box-shadow:0 0 15px rgba(255,215,0,0.15)}
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

class JudgmentThresholds:
    STRONG_BUY_SCORE = 18.0; BUY_SCORE = 12.0; WATCH_BUY_SCORE = 6.5
    STRONG_BUY_LAYERS = 5; BUY_LAYERS = 3; WATCH_LAYERS = 2
    STRONG_BUY_RATIO = 2.0; BUY_RATIO = 1.4
    STRONG_BUY_DIFF = 10.0; BUY_DIFF = 5.0; WATCH_DIFF = 2.0
    SELL_ASYMMETRY = 0.85; LOW_VOL_SCALE = 0.85
    MIXED_MIN = 9.0; MIXED_DIFF_MAX = 3.0
    TREND_CAP = 12.0; MOMENTUM_CAP = 10.0; CANDLE_CAP = 5.0; BB_CAP = 7.0
    VOLUME_CAP = 7.0; MF_CAP = 8.0; PATTERN_CAP = 10.0; ANTICIPATION_CAP = 8.0
    CROSS_SIGNAL_CAP = 6.0
    ACCEL_STRONG = 3.0; ACCEL_MODERATE = 1.5
    CONVERGENCE_FAST = 3.0; CONVERGENCE_SLOW = 1.5
    SETUP_MATURITY = 3
    COMBO_TIER1_BONUS = 4.0; COMBO_TIER2_BONUS = 2.5; COMBO_TIER3_BONUS = 1.5

JT = JudgmentThresholds
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GEMINI_API_KEY)

@st.cache_resource
def get_gemini_model():
    return genai.GenerativeModel('gemini-2.5-flash')

# ══════════════════════════════════════════
#  시그널 레지스트리 (V12.0 — Part 1에서와 동일)
# ══════════════════════════════════════════
_B, _S, _N = 'buy', 'sell', 'neutral'
def _sig(w, d, icon, label, sym, sz, clr, base, atr_m, kor, desc):
    return {'w':w,'dir':d,'icon':icon,'label':label,'sym':sym,'sz':sz,
            'clr':clr,'base':base,'atr_m':atr_m,'kor':kor,'desc':desc}

SIGNAL_REGISTRY = {
    'Gold_Dot':_sig(3,_B,'🏆','GOLD DOT','circle',18,'#FFD700','Low',-3,'최강 매수','RSI<30+MFI<30+WT<-60+다이버전스'),
    'Green_Dot_T1':_sig(2.5,_B,'🟢','BUY T1','circle',16,'#00E676','Low',-2.5,'강한 매수','WT과매도교차+RSI<30+MFI<30'),
    'Green_Dot_T2':_sig(2,_B,'🟩','BUY T2','circle',13,'#69F0AE','Low',-2.2,'매수','WT과매도+RSI/MFI<32'),
    'Blue_Diamond':_sig(2,_B,'🔹','BLUE DIA','diamond',14,'#00bfff','Low',-1.8,'추세 매수','WT2≤0 상승교차+HTF강세'),
    'Green_Circle':_sig(0.8,_B,'✅','BUY Circle','circle-open',11,'#00E676','Low',-1.2,'과매도 반등','WT과매도교차+RSI<45'),
    'Bull_Divergence':_sig(2,_B,'📈','Bull Div','triangle-up',12,'#AA00FF','Low',-2,'상승 다이버전스','가격↓ vs WT↑'),
    'RSI_Bull_Divergence':_sig(1.5,_B,'📊','RSI Bull Div','triangle-up',11,'#CE93D8','Low',-1.8,'RSI 상승 다이버전스','가격↓ vs RSI↑'),
    'Squeeze_Fire_Buy':_sig(1.5,_B,'💥','Squeeze BUY','star-diamond',14,'#00FFFF','Low',-1.5,'스퀴즈 매수','TTM Squeeze 해소+모멘텀↑'),
    'Hidden_Bull_Div':_sig(1.5,_B,'🔀','Hidden Bull','triangle-up',10,'#E040FB','Low',-1.6,'히든 상승 다이버전스','가격↑ vs WT↓'),
    'Volume_Climax_Buy':_sig(2,_B,'🌊','Vol Climax BUY','hexagram',14,'#00BCD4','Low',-2.8,'거래량 클라이맥스','3x거래량+하락장대봉→반등'),
    'OBV_Div_Buy':_sig(0.8,_B,'📊','OBV Div BUY','triangle-up',10,'#80DEEA','Low',-1.4,'OBV 다이버전스','OBV↑ vs 가격↓'),
    'ADX_Momentum_Buy':_sig(1.5,_B,'🚀','ADX Ignition','arrow-up',11,'#76FF03','Low',-1.4,'ADX 점화','ADX>20돌파+DI↑'),
    'Bullish_Engulfing':_sig(1.5,_B,'☀️','Bull Engulf','square',10,'#00E676','Low',-1.3,'상승 장악형','하락캔들 감싸는 상승캔들'),
    'Golden_Cross':_sig(1.5,_B,'✨','Golden Cross','cross',12,'#FFD700','Low',-0.8,'골든 크로스','50MA>200MA'),
    'EMA_Pullback_Buy':_sig(2,_B,'🎯','EMA Pullback','triangle-up',13,'#00BFA5','Low',-1.8,'EMA 눌림목','상승추세 EMA조정후 반등'),
    'Momentum_Ignition_Buy':_sig(2.5,_B,'🔥','Mom. Ignition','star-diamond',15,'#FF6D00','Low',-2.5,'모멘텀 점화','장대양봉>ATR×1.5'),
    'SuperTrend_Buy':_sig(1.5,_B,'📈','ST Flip Bull','arrow-up',12,'#00E5FF','Low',-1.5,'슈퍼트렌드 강세','ST 위로 돌파'),
    'VWAP_Bounce_Buy':_sig(1.5,_B,'🏦','VWAP Bounce','triangle-up',11,'#00E5FF','Low',-1.3,'VWAP 반등','VWAP복귀+WT교차'),
    'Parabolic_Bottom_Buy':_sig(3,_B,'🧊','Parabolic Bot','diamond',16,'#00FFFF','Low',-3,'포물선 바닥','WT<-80 꺾임+양봉'),
    'MACD_Cross_Buy':_sig(1,_B,'〽️','MACD Cross','triangle-up',9,'#4CAF50','Low',-1,'MACD 골든크로스','MACD>시그널(0선하방)'),
    'StochRSI_Cross_Buy':_sig(0.8,_B,'🔄','StRSI Cross','circle-open',8,'#81C784','Low',-0.8,'StochRSI 매수교차','StochK>StochD(과매도)'),
    'Blood_Diamond':_sig(3,_S,'🩸','BLOOD DIA','diamond',18,'#DC143C','High',3,'최강 매도','RSI>70+MFI>70+WT>60+다이버전스'),
    'Red_Dot_T1':_sig(2.5,_S,'🔴','SELL T1','circle',16,'#FF1744','High',2.5,'강한 매도','WT과매수하락교차+RSI>70'),
    'Red_Dot_T2':_sig(2,_S,'🟥','SELL T2','circle',13,'#FF5252','High',2.2,'매도','WT과매수+RSI/MFI>68'),
    'Red_Diamond':_sig(2,_S,'🔸','RED DIA','diamond',14,'#ff3333','High',1.8,'추세 매도','WT2≥0 하락교차+HTF약세'),
    'Red_Circle':_sig(0.8,_S,'⛔','SELL Circle','circle-open',11,'#FF1744','High',1.2,'과매수 하락','WT과매수하락교차'),
    'Bear_Divergence':_sig(2,_S,'📉','Bear Div','triangle-down',12,'#AA00FF','High',2,'하락 다이버전스','가격↑ vs WT↓'),
    'RSI_Bear_Divergence':_sig(1.5,_S,'📉','RSI Bear Div','triangle-down',11,'#CE93D8','High',1.8,'RSI 하락 다이버전스','가격↑ vs RSI↓'),
    'Squeeze_Fire_Sell':_sig(1.5,_S,'🧨','Squeeze SELL','star-diamond',14,'#FF6600','High',1.5,'스퀴즈 매도','TTM Squeeze 해소+모멘텀↓'),
    'Hidden_Bear_Div':_sig(1.5,_S,'🔁','Hidden Bear','triangle-down',10,'#E040FB','High',1.6,'히든 하락 다이버전스','가격↓ vs WT↑'),
    'Volume_Climax_Sell':_sig(2,_S,'🌋','Vol Climax SELL','hexagram',14,'#FF5722','High',2.8,'거래량 클라이맥스','3x거래량+상승장대봉→하락'),
    'OBV_Div_Sell':_sig(0.8,_S,'🔻','OBV Div SELL','triangle-down',10,'#FFAB91','High',1.4,'OBV 다이버전스','OBV↓ vs 가격↑'),
    'ADX_Momentum_Sell':_sig(1.5,_S,'💨','ADX Down','arrow-down',11,'#FF3D00','High',1.4,'ADX 하락 점화','ADX>20+-DI>+DI'),
    'Bearish_Engulfing':_sig(1.5,_S,'🌑','Bear Engulf','x',10,'#D50000','High',1.3,'하락 장악형','상승캔들 감싸는 하락캔들'),
    'Death_Cross':_sig(1.5,_S,'☠️','Death Cross','cross',12,'#FF1744','High',0.8,'데스 크로스','50MA<200MA'),
    'SuperTrend_Sell':_sig(2,_S,'📉','ST Flip Bear','arrow-down',12,'#FF1744','High',1.5,'슈퍼트렌드 약세','ST 하향 돌파'),
    'Parabolic_Top_Sell':_sig(3,_S,'🌡️','Parabolic Top','diamond',16,'#FF0000','High',3,'포물선 천장','WT>80 꺾임+음봉'),
    'EMA_Pullback_Sell':_sig(2,_S,'🎯','EMA PB Sell','triangle-down',13,'#FF6E40','High',1.8,'EMA 되돌림 매도','하락추세 EMA반등후 재하락'),
    'Momentum_Ignition_Sell':_sig(2.5,_S,'💣','Mom. Ign Sell','star-diamond',15,'#D50000','High',2.5,'모멘텀 점화 매도','장대음봉>ATR×1.5'),
    'VWAP_Reject_Sell':_sig(1.5,_S,'🏛️','VWAP Reject','triangle-down',11,'#FF6E40','High',1.3,'VWAP 저항','VWAP실패+WT교차'),
    'MACD_Cross_Sell':_sig(1,_S,'〽️','MACD Dead','triangle-down',9,'#E57373','High',1,'MACD 데드크로스','MACD<시그널'),
    'StochRSI_Cross_Sell':_sig(0.8,_S,'🔄','StRSI Dead','circle-open',8,'#EF9A9A','High',0.8,'StochRSI 매도교차','StochK<StochD(과매수)'),
    'Hammer':_sig(1.5,_B,'🔨','Hammer','triangle-up',11,'#00E676','Low',-1.5,'해머','긴하단꼬리+소형실체'),
    'Morning_Star':_sig(2,_B,'🌅','MornStar','star',13,'#00E676','Low',-2,'모닝스타','큰음봉→소형봉→양봉'),
    'Doji_Bullish':_sig(0.8,_B,'➕','Doji Bull','cross-thin',9,'#69F0AE','Low',-1,'강세 도지','시가≈종가+하락후 반등'),
    'Shooting_Star':_sig(1.5,_S,'🌠','ShootStar','triangle-down',11,'#FF1744','High',1.5,'슈팅스타','긴상단꼬리+소형실체'),
    'Evening_Star':_sig(2,_S,'🌆','EveStar','star',13,'#FF1744','High',2,'이브닝스타','큰양봉→소형봉→음봉'),
    'Doji_Bearish':_sig(0.8,_S,'➖','Doji Bear','cross-thin',9,'#FF5252','High',1,'약세 도지','시가≈종가+상승후 하락'),
    'Inside_Day':_sig(0.3,_N,'📦','InsideDay','square-open',7,'#FFC107','Low',-0.3,'인사이드데이','고가<전일고&저가>전일저'),
    'Outside_Bullish':_sig(1.5,_B,'💪','OutsideBull','square',11,'#00E676','Low',-1.5,'강세 아웃사이드','전일범위포함+양봉'),
    'Outside_Bearish':_sig(1.5,_S,'🥊','OutsideBear','square',11,'#FF1744','High',1.5,'약세 아웃사이드','전일범위포함+음봉'),
    'Cross_Above_20MA':_sig(0.8,_B,'📈','X▲20MA','triangle-up',9,'#69F0AE','Low',-0.8,'20MA상향돌파','종가>20MA'),
    'Cross_Above_50MA':_sig(1.2,_B,'📈','X▲50MA','triangle-up',10,'#00E676','Low',-1,'50MA상향돌파','종가>50MA'),
    'Cross_Above_200MA':_sig(1.5,_B,'📈','X▲200MA','triangle-up',11,'#00BFA5','Low',-1.2,'200MA상향돌파','종가>200MA'),
    'Fell_Below_20MA':_sig(0.8,_S,'📉','X▼20MA','triangle-down',9,'#FF5252','High',0.8,'20MA하향이탈','종가<20MA'),
    'Fell_Below_50MA':_sig(1.2,_S,'📉','X▼50MA','triangle-down',10,'#FF1744','High',1,'50MA하향이탈','종가<50MA'),
    'Fell_Below_200MA':_sig(1.5,_S,'📉','X▼200MA','triangle-down',11,'#D50000','High',1.2,'200MA하향이탈','종가<200MA'),
    'BB_Upper_Break':_sig(1,_B,'🔝','BB▲Break','diamond-open',10,'#00E5FF','High',1,'BB상단돌파','종가>상단BB'),
    'BB_Lower_Bounce':_sig(1.2,_B,'⤵️','BB▼Bounce','diamond-open',10,'#4FC3F7','Low',-1.2,'BB하단반등','종가<하단BB+양봉전환'),
    'BB_Lower_Break':_sig(1,_S,'💀','BB▼Break','diamond-open',10,'#FF6E40','Low',-1,'BB하단붕괴','종가<하단BB+약세지속'),
    'BB_Squeeze_End_Bull':_sig(1.5,_B,'💥','SqEnd▲','star-diamond',12,'#00FFFF','Low',-1.5,'BB스퀴즈해소↑','BB확장+상승'),
    'BB_Squeeze_End_Bear':_sig(1.5,_S,'💥','SqEnd▼','star-diamond',12,'#FF6600','High',1.5,'BB스퀴즈해소↓','BB확장+하락'),
    'MACD_Zero_Cross_Buy':_sig(1.2,_B,'⬆️','MACD 0▲','triangle-up',10,'#4CAF50','Low',-1,'MACD 0선돌파','MACD>0'),
    'MACD_Zero_Cross_Sell':_sig(1.2,_S,'⬇️','MACD 0▼','triangle-down',10,'#E57373','High',1,'MACD 0선이탈','MACD<0'),
    'Up_3_Days':_sig(0.5,_B,'📗','Up3D','triangle-up',8,'#69F0AE','High',0.5,'3일연속상승','3일연속양봉'),
    'Up_5_Days':_sig(0.8,_B,'📗','Up5D','triangle-up',9,'#00E676','High',0.8,'5일연속상승','5일연속양봉'),
    'Down_3_Days':_sig(0.5,_S,'📕','Dn3D','triangle-down',8,'#FF5252','Low',-0.5,'3일연속하락','3일연속음봉'),
    'Down_5_Days':_sig(0.8,_S,'📕','Dn5D','triangle-down',9,'#FF1744','Low',-0.8,'5일연속하락','5일연속음봉'),
    'Gap_Up':_sig(1,_B,'⏫','GapUp','arrow-up',10,'#00E676','Low',-1,'갭 상승','시가>전일고가'),
    'Gap_Down':_sig(1,_S,'⏬','GapDn','arrow-down',10,'#FF1744','High',1,'갭 하락','시가<전일저가'),
    'Gap_Up_Closed':_sig(0.8,_S,'🔄','GapUp Fill','circle-open',8,'#FFA726','High',0.8,'갭업메움','상승갭메워짐'),
    'Gap_Down_Closed':_sig(0.8,_B,'🔄','GapDn Fill','circle-open',8,'#4FC3F7','Low',-0.8,'갭다운메움','하락갭메워짐'),
    'NR7':_sig(0.3,_N,'🔲','NR7','square-open',7,'#B0BEC5','Low',-0.3,'NR7','7일중최소범위'),
    'NR7_2':_sig(0.8,_N,'🔳','NR7-2','square-open',8,'#90A4AE','Low',-0.5,'NR7-2','2일연속NR7'),
    'Calm_After_Storm':_sig(1,_N,'🌤️','CalmStorm','diamond-open',9,'#FFC107','Low',-0.8,'폭풍뒤고요','WideRange→NarrowRange'),
    'Wide_Range_Bar':_sig(0.5,_N,'📊','WideBar','square-open',7,'#FFAB40','Low',-0.4,'넓은범위봉','범위>ATR×2'),
    'New_52W_High':_sig(1.5,_B,'🏔️','52W▲','star-triangle-up',12,'#FFD700','High',1.5,'52주신고가','52주최고가갱신'),
    'New_52W_Low':_sig(1.5,_S,'🕳️','52W▼','star-triangle-down',12,'#B71C1C','Low',-1.5,'52주신저가','52주최저가갱신'),
    'Pullback_123_Bull':_sig(2,_B,'🎯','123PB▲','triangle-up',12,'#00E676','Low',-1.8,'1,2,3풀백매수','ADX>30+DI↑+3일저점↓'),
    'Pullback_123_Bear':_sig(2,_S,'🎯','123PB▼','triangle-down',12,'#FF1744','High',1.8,'1,2,3풀백매도','ADX>30+DI↓+3일고점↑'),
    'Setup_180_Bull':_sig(2,_B,'🔄','180▲','star-diamond',13,'#00E676','Low',-2,'180매수셋업','전일하위25%→당일상위25%'),
    'Setup_180_Bear':_sig(2,_S,'🔄','180▼','star-diamond',13,'#FF1744','High',2,'180매도셋업','전일상위25%→당일하위25%'),
    'Boomer_Buy':_sig(2,_B,'💣','Boomer▲','star',12,'#00E676','Low',-1.8,'부머매수','ADX>30+2일인사이드→돌파'),
    'Boomer_Sell':_sig(2,_S,'💣','Boomer▼','star',12,'#FF1744','High',1.8,'부머매도','ADX>30+2일인사이드→이탈'),
    'Expansion_BO':_sig(2.5,_B,'🚀','XBO','star-diamond',14,'#FFD700','Low',-2.5,'확장돌파','2개월신고가+9일최대범위'),
    'Expansion_BD':_sig(2.5,_S,'💨','XBD','star-diamond',14,'#FF0000','High',2.5,'확장붕괴','2개월신저가+9일최대범위'),
    'Gilligans_Buy':_sig(2,_B,'🏝️','Gilligan▲','hexagon',12,'#00BCD4','Low',-2,'길리건매수','갭다운신저가→반전'),
    'Gilligans_Sell':_sig(2,_S,'🏝️','Gilligan▼','hexagon',12,'#FF5722','High',2,'길리건매도','갭업신고가→반전'),
    'Lizard_Bull':_sig(1.5,_B,'🦎','Lizard▲','triangle-up',10,'#00E676','Low',-1.5,'리자드매수','시가종가상위25%+10일신저가'),
    'Lizard_Bear':_sig(1.5,_S,'🦎','Lizard▼','triangle-down',10,'#FF1744','High',1.5,'리자드매도','시가종가하위25%+10일신고가'),
    'NonADX_123_Bull':_sig(1.8,_B,'📐','nADX123▲','triangle-up',11,'#69F0AE','Low',-1.5,'비ADX풀백매수','주가>50MA+3일저점↓'),
    'NonADX_123_Bear':_sig(1.8,_S,'📐','nADX123▼','triangle-down',11,'#FF5252','High',1.5,'비ADX풀백매도','주가<50MA+3일고점↑'),
    'Pocket_Pivot':_sig(1.5,_B,'🧲','PocketPvt','triangle-up',11,'#7C4DFF','Low',-1.5,'포켓피봇','양봉+거래량>10일하락최대'),
    'MF_Cross_Bull':_sig(1.5,_B,'💰','MF 0▲','triangle-up',11,'#00E676','Low',-1.2,'MF 강세전환','자금흐름 음→양'),
    'MF_Cross_Bear':_sig(1.5,_S,'💸','MF 0▼','triangle-down',11,'#FF1744','High',1.2,'MF 약세전환','자금흐름 양→음'),
    'MF_Bull_Div':_sig(1.8,_B,'💹','MF Bull Div','triangle-up',11,'#7C4DFF','Low',-1.5,'MF 상승 다이버전스','가격↓ vs MF↑'),
    'MF_Bear_Div':_sig(1.8,_S,'💹','MF Bear Div','triangle-down',11,'#E040FB','High',1.5,'MF 하락 다이버전스','가격↑ vs MF↓'),
    'MF_Accel_Up':_sig(1,_B,'📈','MF Accel▲','arrow-up',9,'#69F0AE','Low',-0.8,'MF 가속상승','5일+ MF 연속상승'),
    'MF_Accel_Dn':_sig(1,_S,'📉','MF Accel▼','arrow-down',9,'#FF5252','High',0.8,'MF 가속하락','5일+ MF 연속하락'),
    'Kumo_Breakout_Bull':_sig(2,_B,'☁️','Kumo▲','triangle-up',13,'#00E676','Low',-2,'쿠모 상향돌파','종가>구름상단'),
    'Kumo_Breakout_Bear':_sig(2,_S,'☁️','Kumo▼','triangle-down',13,'#FF1744','High',2,'쿠모 하향돌파','종가<구름하단'),
    'TK_Cross_Bull':_sig(1.5,_B,'⛩️','TK Cross▲','triangle-up',10,'#69F0AE','Low',-1.2,'전환-기준 골든','전환선>기준선'),
    'TK_Cross_Bear':_sig(1.5,_S,'⛩️','TK Cross▼','triangle-down',10,'#FF5252','High',1.2,'전환-기준 데드','전환선<기준선'),
    'CMF_Bull':_sig(1.2,_B,'🌀','CMF Bull','triangle-up',10,'#00BCD4','Low',-1,'CMF 강세','CMF>0.1+상승추세'),
    'CMF_Bear':_sig(1.2,_S,'🌀','CMF Bear','triangle-down',10,'#FF5722','High',1,'CMF 약세','CMF<-0.1+하락추세'),
    'Setup_Squeeze_Bull':_sig(1,_B,'⏳','SqSetup▲','hourglass',10,'#80DEEA','Low',-0.8,'스퀴즈셋업▲','BB축소+모멘텀상승임박'),
    'Setup_Squeeze_Bear':_sig(1,_S,'⏳','SqSetup▼','hourglass',10,'#FFAB91','High',0.8,'스퀴즈셋업▼','BB축소+모멘텀하락임박'),
    'Momentum_Accel_Buy':_sig(1.5,_B,'⚡','Mom Accel▲','arrow-up',11,'#76FF03','Low',-1.2,'모멘텀가속▲','RSI+WT+MACD 동시가속'),
    'Momentum_Accel_Sell':_sig(1.5,_S,'⚡','Mom Accel▼','arrow-down',11,'#FF3D00','High',1.2,'모멘텀가속▼','RSI+WT+MACD 동시감속'),
    'Volume_Dry_Up':_sig(0.5,_N,'🏜️','VolDryUp','square-open',8,'#FFE082','Low',-0.3,'거래량고갈','5일연속평균이하'),
    'WT_Convergence_Bull':_sig(1.2,_B,'🔀','WT Conv▲','triangle-up',10,'#B2FF59','Low',-1,'WT수렴매수임박','WT1→WT2수렴+과매도'),
    'WT_Convergence_Bear':_sig(1.2,_S,'🔀','WT Conv▼','triangle-down',10,'#FF8A80','High',1,'WT수렴매도임박','WT1→WT2수렴+과매수'),
}

COMPOSITE_SIGNALS = {
    'Ultra_Buy':_sig(0,_B,'⚡','ULTRA BUY','star',20,'#FFD700','Low',-3.5,'울트라 매수','Confluence≥6.5'),
    'Strong_Buy':_sig(0,_B,'🔱','STRONG BUY','star',16,'#00E676','Low',-3.2,'스트롱 매수','Confluence 3.5~6.5'),
    'Ultra_Sell':_sig(0,_S,'🚨','ULTRA SELL','star',20,'#FF0000','High',3.5,'울트라 매도','Confluence≤-6.5'),
    'Strong_Sell':_sig(0,_S,'⚠️','STRONG SELL','star',16,'#FF1744','High',3.2,'스트롱 매도','Confluence -6.5~-3.5'),
}
ALL_CHART_SIGNALS = {**SIGNAL_REGISTRY, **COMPOSITE_SIGNALS}

# ══════════════════════════════════════════
#  🆕 스캐너 콤보 정의 (20종)
# ══════════════════════════════════════════
SCANNER_COMBOS = {
    'SC_Oversold_Bounce':{'name':'🟢 Oversold Bounce','kor':'과매도 반등','dir':'buy','tier':1,
        'icon':'🏓','color':'#00E676','desc':'StochK 과매도 + 강세 캔들 + 20MA 돌파','category':'반전'},
    'SC_Breakout_Momentum':{'name':'🟢 Breakout Momentum','kor':'돌파 모멘텀','dir':'buy','tier':1,
        'icon':'🚀','color':'#00E676','desc':'확장 돌파 + 거래량 급증 + 52주 신고가','category':'돌파'},
    'SC_Pullback_Buy_Zone':{'name':'🟢 Pullback Buy Zone','kor':'눌림목 매수','dir':'buy','tier':2,
        'icon':'🎯','color':'#69F0AE','desc':'상승추세 + 20MA 눌림 + 해머/반등','category':'추세지속'},
    'SC_Triple_Oversold':{'name':'🟢 Triple Oversold','kor':'삼중 과매도 반전','dir':'buy','tier':1,
        'icon':'💎','color':'#00E676','desc':'WT+RSI+캔들 동시 과매도 극단 반전','category':'반전'},
    'SC_Squeeze_Fire_Bull':{'name':'🟢 Squeeze Fire Bull','kor':'스퀴즈 돌파','dir':'buy','tier':2,
        'icon':'💥','color':'#00FFFF','desc':'BB 스퀴즈 해소 + 거래량 + MACD','category':'돌파'},
    'SC_Trend_Continuation':{'name':'🟢 Trend Continuation','kor':'추세 지속','dir':'buy','tier':2,
        'icon':'📐','color':'#69F0AE','desc':'ADX 강세 + 123 풀백 + 자금흐름↑','category':'추세지속'},
    'SC_Volume_Climax_Rev':{'name':'🟢 Vol Climax Reversal','kor':'거래량 클라이맥스','dir':'buy','tier':1,
        'icon':'🌊','color':'#00BCD4','desc':'거래량 폭발 + WT 과매도 + 다이버전스','category':'반전'},
    'SC_Ichimoku_Breakout':{'name':'🟢 Ichimoku Breakout','kor':'쿠모 돌파','dir':'buy','tier':2,
        'icon':'☁️','color':'#00E5FF','desc':'쿠모 상향돌파 + CMF 양호 + 거래량','category':'돌파'},
    'SC_Smart_Money_Accum':{'name':'🟢 Smart Money','kor':'스마트머니 매집','dir':'buy','tier':2,
        'icon':'🏦','color':'#7C4DFF','desc':'MF 전환 + CMF 양수 + BB 하단 반등','category':'매집'},
    'SC_Momentum_Ignition_Buy':{'name':'🟢 Mom. Ignition','kor':'모멘텀 점화','dir':'buy','tier':1,
        'icon':'🔥','color':'#FF6D00','desc':'모멘텀 점화 + ST 강세전환 + ADX↑','category':'돌파'},
    'SC_Overbought_Exhaust':{'name':'🔴 Overbought Exhaust','kor':'과매수 소진','dir':'sell','tier':1,
        'icon':'🌡️','color':'#FF1744','desc':'StochK 과매수 + 약세 캔들 + 20MA 이탈','category':'반전'},
    'SC_Breakdown_Momentum':{'name':'🔴 Breakdown Momentum','kor':'붕괴 모멘텀','dir':'sell','tier':1,
        'icon':'💨','color':'#FF1744','desc':'확장 붕괴 + 거래량 급증 + 52주 신저가','category':'붕괴'},
    'SC_Rally_Failure':{'name':'🔴 Rally Failure','kor':'반등 실패','dir':'sell','tier':2,
        'icon':'🎯','color':'#FF5252','desc':'하락추세 + 20MA 저항 + 슈팅스타','category':'추세지속'},
    'SC_Triple_Overbought':{'name':'🔴 Triple Overbought','kor':'삼중 과매수 반전','dir':'sell','tier':1,
        'icon':'💀','color':'#FF1744','desc':'WT+RSI+캔들 동시 과매수 극단 반전','category':'반전'},
    'SC_Squeeze_Fire_Bear':{'name':'🔴 Squeeze Fire Bear','kor':'스퀴즈 붕괴','dir':'sell','tier':2,
        'icon':'🧨','color':'#FF6600','desc':'BB 스퀴즈 해소 하방 + 거래량 + MACD','category':'붕괴'},
    'SC_Trend_Breakdown':{'name':'🔴 Trend Breakdown','kor':'추세 붕괴','dir':'sell','tier':2,
        'icon':'📐','color':'#FF5252','desc':'ADX 약세 + 123 풀백 매도 + 자금유출','category':'추세지속'},
    'SC_Volume_Climax_Sell':{'name':'🔴 Vol Climax Sell','kor':'거래량 클라이맥스 매도','dir':'sell','tier':1,
        'icon':'🌋','color':'#D50000','desc':'거래량 폭발 + WT 과매수 + 다이버전스','category':'반전'},
    'SC_Ichimoku_Breakdown':{'name':'🔴 Ichimoku Breakdown','kor':'쿠모 하향','dir':'sell','tier':2,
        'icon':'☁️','color':'#FF6E40','desc':'쿠모 하향돌파 + CMF 약세 + 거래량','category':'붕괴'},
    'SC_Distribution':{'name':'🔴 Distribution','kor':'분배 신호','dir':'sell','tier':2,
        'icon':'🏛️','color':'#E040FB','desc':'MF 전환 + CMF 음수 + WT 하락','category':'분배'},
    'SC_Parabolic_Exhaust':{'name':'🔴 Parabolic Exhaust','kor':'포물선 소진','dir':'sell','tier':1,
        'icon':'🌡️','color':'#FF0000','desc':'포물선 천장 + 거래량 폭발 + RSI 극과매수','category':'반전'},
}

# ══════════════════════════════════════════
#  나머지 상수 (쿨다운, 계층, 판단마커, 판단설정)
# ══════════════════════════════════════════
COOLDOWN_MAP = {
    'Squeeze_Fire_Buy':5,'Squeeze_Fire_Sell':5,'Bullish_Engulfing':5,'Bearish_Engulfing':5,
    'ADX_Momentum_Buy':10,'ADX_Momentum_Sell':10,'EMA_Pullback_Buy':7,'EMA_Pullback_Sell':7,
    'Momentum_Ignition_Buy':10,'Momentum_Ignition_Sell':10,
    'Parabolic_Top_Sell':5,'Parabolic_Bottom_Buy':5,
    'VWAP_Bounce_Buy':7,'VWAP_Reject_Sell':7,
    'MACD_Cross_Buy':12,'MACD_Cross_Sell':12,'StochRSI_Cross_Buy':7,'StochRSI_Cross_Sell':7,
    'RSI_Bull_Divergence':10,'RSI_Bear_Divergence':10,
    'Hammer':5,'Shooting_Star':5,'Morning_Star':7,'Evening_Star':7,
    'Doji_Bullish':5,'Doji_Bearish':5,'Outside_Bullish':7,'Outside_Bearish':7,
    'Cross_Above_20MA':5,'Fell_Below_20MA':5,'Cross_Above_50MA':10,'Fell_Below_50MA':10,
    'Cross_Above_200MA':15,'Fell_Below_200MA':15,
    'BB_Upper_Break':5,'BB_Lower_Bounce':5,'BB_Lower_Break':5,
    'BB_Squeeze_End_Bull':7,'BB_Squeeze_End_Bear':7,
    'MACD_Zero_Cross_Buy':12,'MACD_Zero_Cross_Sell':12,
    'Gap_Up':3,'Gap_Down':3,'Gap_Up_Closed':5,'Gap_Down_Closed':5,
    'New_52W_High':10,'New_52W_Low':10,'Calm_After_Storm':5,
    'Pullback_123_Bull':7,'Pullback_123_Bear':7,'Setup_180_Bull':7,'Setup_180_Bear':7,
    'Boomer_Buy':10,'Boomer_Sell':10,'Expansion_BO':10,'Expansion_BD':10,
    'Gilligans_Buy':10,'Gilligans_Sell':10,'Lizard_Bull':5,'Lizard_Bear':5,
    'NonADX_123_Bull':7,'NonADX_123_Bear':7,'Pocket_Pivot':10,
    'MF_Cross_Bull':10,'MF_Cross_Bear':10,'MF_Bull_Div':10,'MF_Bear_Div':10,
    'MF_Accel_Up':5,'MF_Accel_Dn':5,
    'Kumo_Breakout_Bull':10,'Kumo_Breakout_Bear':10,'TK_Cross_Bull':7,'TK_Cross_Bear':7,
    'CMF_Bull':10,'CMF_Bear':10,
    'Setup_Squeeze_Bull':3,'Setup_Squeeze_Bear':3,
    'Momentum_Accel_Buy':5,'Momentum_Accel_Sell':5,'Volume_Dry_Up':3,
    'WT_Convergence_Bull':5,'WT_Convergence_Bear':5,
}

SIGNAL_HIERARCHY = {
    'candle_bull':['Morning_Star','Bullish_Engulfing','Hammer','Doji_Bullish'],
    'candle_bear':['Evening_Star','Bearish_Engulfing','Shooting_Star','Doji_Bearish'],
    'ma_cross_bull':['Cross_Above_200MA','Cross_Above_50MA','Cross_Above_20MA'],
    'ma_cross_bear':['Fell_Below_200MA','Fell_Below_50MA','Fell_Below_20MA'],
    'cooper_bull':['Expansion_BO','Pullback_123_Bull','Setup_180_Bull','Boomer_Buy',
                   'Gilligans_Buy','Lizard_Bull','NonADX_123_Bull'],
    'cooper_bear':['Expansion_BD','Pullback_123_Bear','Setup_180_Bear','Boomer_Sell',
                   'Gilligans_Sell','Lizard_Bear','NonADX_123_Bear'],
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

COMBO_MAP = {
    'Combo_TrendPullback_Buy':('🎯 추세 눌림목 매수','buy',2),
    'Combo_VolSqueeze_Buy':('💥 변동성 수축 돌파','buy',2),
    'Combo_Reversal_Buy':('🔄 반전 매수','buy',1),
    'Combo_Momentum_Buy':('🚀 모멘텀 돌파','buy',1),
    'Combo_MAConfluence_Buy':('📊 MA 합류 매수','buy',2),
    'Combo_MF_Reversal_Buy':('💰 자금흐름 전환','buy',3),
    'Combo_Ichimoku_Buy':('☁️ 쿠모 돌파','buy',2),
    'Combo_Anticipation_Buy':('⏳ 매수 셋업 임박','buy',3),
    'Combo_TrendRejection_Sell':('🎯 추세 반등 실패','sell',2),
    'Combo_Exhaustion_Sell':('🌡️ 고점 소진','sell',1),
    'Combo_MABreakdown_Sell':('📉 MA 붕괴','sell',2),
    'Combo_VolSqueeze_Sell':('💨 변동성 수축 붕괴','sell',2),
    'Combo_GapFailure_Sell':('⏬ 갭 실패','sell',2),
    'Combo_MF_Reversal_Sell':('💸 자금흐름 전환 매도','sell',3),
    'Combo_Ichimoku_Sell':('☁️ 쿠모 하향','sell',2),
    'Combo_Anticipation_Sell':('⏳ 매도 셋업 임박','sell',3),
}

# 기본 워치리스트
DEFAULT_WATCHLIST = {
    '🔥 대형주':['NVDA','TSLA','AAPL','MSFT','AMZN','GOOG','META','AMD','NFLX','AVGO'],
    '📊 ETF':['QQQ','SPY','IWM','ARKK','SOXX','XLF','XLE','XLV','XLK','TQQQ'],
    '🚀 성장주':['PLTR','SNOW','CRWD','DDOG','NET','SHOP','SQ','COIN','MARA','RIOT'],
}

# ══════════════════════════════════════════
#  유틸리티 함수
# ══════════════════════════════════════════
def _recent(s, lb=3):
    return s.astype(float).rolling(lb+1, min_periods=1).max().fillna(0).astype(bool)

def _cooldown(sig, bars=5):
    v = sig.fillna(False).values.astype(bool)
    out = np.zeros(len(v), dtype=bool); last = -bars-1
    for i in range(len(v)):
        if v[i] and (i-last) > bars: out[i]=True; last=i
    return pd.Series(out, index=sig.index)

def _cooldown_directional(df, buy_sig, sell_sig, bars=5):
    bv = df.get(buy_sig, pd.Series(False, index=df.index)).fillna(False).values.astype(bool)
    sv = df.get(sell_sig, pd.Series(False, index=df.index)).fillna(False).values.astype(bool)
    b_out=np.zeros(len(bv),dtype=bool); s_out=np.zeros(len(sv),dtype=bool)
    last_b=-bars-1; last_s=-bars-1
    for i in range(len(df)):
        if sv[i]: last_b=-bars-1
        if bv[i]: last_s=-bars-1
        if bv[i] and (i-last_b)>bars: b_out[i]=True; last_b=i
        if sv[i] and (i-last_s)>bars: s_out[i]=True; last_s=i
    if buy_sig in df.columns: df[buy_sig]=pd.Series(b_out,index=df.index)
    if sell_sig in df.columns: df[sell_sig]=pd.Series(s_out,index=df.index)

def _volf(vol, ratio=0.5, period=20):
    return vol >= (vol.rolling(period, min_periods=5).mean() * ratio)

def _valid_fmt(t): return bool(re.match(r'^[A-Za-z]{1,5}([.\-][A-Za-z]{1,2})?$', t))
def _cls(val, lo, hi): return 'ind-bullish' if val<lo else ('ind-bearish' if val>hi else 'ind-neutral')

def _sig_pts(df, sig_name, points):
    if sig_name in df.columns: return np.where(df[sig_name].fillna(False), points, 0.0)
    return 0.0

def _vectorized_streak(condition):
    c = condition.astype(int); groups = (c==0).cumsum()
    return c.groupby(groups).cumsum()

# ══════════════════════════════════════════
#  데이터 캐싱
# ══════════════════════════════════════════
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_fundamentals(ticker):
    try:
        info = yf.Ticker(ticker).info
        def _get(key,fmt=None):
            val=info.get(key)
            if val is None: return "N/A"
            if fmt=='currency': return f"${val:,.2f}"
            if fmt=='large': return f"{val:,.0f}"
            if fmt=='percent': return f"{val*100:.2f}%"
            if fmt=='float': return f"{val:.2f}"
            return str(val)
        return "\n".join([f"Market Cap: {_get('marketCap','large')}",
            f"Short % of Float: {_get('shortPercentOfFloat','percent')}",
            f"Trailing EPS: {_get('trailingEps','currency')}",
            f"P/E Ratio: {_get('trailingPE','float')}",
            f"52W High: {_get('fiftyTwoWeekHigh','currency')}",
            f"52W Low: {_get('fiftyTwoWeekLow','currency')}",
            f"Avg Vol: {_get('averageVolume','large')}"])
    except: return "펀더멘탈 데이터를 불러올 수 없습니다."

@st.cache_data(ttl=300, max_entries=30, show_spinner=False)
def fetch_history(ticker, _ts=None):
    return yf.Ticker(ticker).history(period="2y")

@st.cache_data(ttl=600, show_spinner=False)
def validate_ticker(ticker):
    try: return not yf.Ticker(ticker).history(period="5d").empty
    except: return False

@st.cache_data(ttl=300, max_entries=30, show_spinner=False)
def compute_and_cache(ticker, _ts=None):
    df = fetch_history(ticker, _ts)
    if df.empty: return None
    return detect_all_signals(compute_indicators(df))

# ══════════════════════════════════════════════════════════════
#  CipherX V12.0 + Scanner — PART 2/4
#  지표 계산 + 패턴 탐지 + detect_all_signals + detect_scanner_combos
#  + 8-Layer 판단 엔진 + Confluence + Combo
# ══════════════════════════════════════════════════════════════

# ──────────────────────────────────────────
# 기술 지표 계산 함수
# ──────────────────────────────────────────
def compute_rsi(s, p=14):
    d=s.diff(); g,l=d.clip(lower=0),-d.clip(upper=0)
    return 100-(100/(1+g.ewm(alpha=1/p,min_periods=p).mean()/(l.ewm(alpha=1/p,min_periods=p).mean()+1e-10)))

def compute_mfi(h,l,c,v,p=14):
    tp=(h+l+c)/3; raw=tp*v; d=tp.diff()
    return 100-(100/(1+raw.where(d>=0,0).rolling(p).sum()/(raw.where(d<0,0).rolling(p).sum()+1e-10)))

def compute_rsi_mfi(h,l,c,v,p=60):
    rf,mf=compute_rsi(c,20),compute_mfi(h,l,c,v,20)
    rs,ms=compute_rsi(c,p),compute_mfi(h,l,c,v,p)
    return (((rf-50)+(mf-50))/2)*.6+(((rs-50)+(ms-50))/2)*.4

def compute_wavetrend(h,l,c,ch=9,avg=12,ma=3):
    ap=(h+l+c)/3; esa=ap.ewm(span=ch,adjust=False).mean()
    d=abs(ap-esa).ewm(span=ch,adjust=False).mean()
    ci=(ap-esa)/(0.015*d+1e-10); wt1=ci.ewm(span=avg,adjust=False).mean(); wt2=wt1.rolling(ma).mean()
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
    ml=c.ewm(span=f,adjust=False).mean()-c.ewm(span=s,adjust=False).mean()
    sl=ml.ewm(span=sig,adjust=False).mean(); return ml,sl,ml-sl

def compute_ichimoku(h,l,c,tp=9,kp=26,sbp=52,disp=26):
    tenkan=(h.rolling(tp).max()+l.rolling(tp).min())/2
    kijun=(h.rolling(kp).max()+l.rolling(kp).min())/2
    sa=((tenkan+kijun)/2).shift(disp)
    sb=((h.rolling(sbp).max()+l.rolling(sbp).min())/2).shift(disp)
    return tenkan,kijun,sa,sb,c.shift(-disp)

def compute_cmf(h,l,c,v,p=20):
    mfm=((c-l)-(h-c))/(h-l+1e-10); return (mfm*v).rolling(p).sum()/(v.rolling(p).sum()+1e-10)

def compute_keltner(h,l,c,el=20,al=10,m=1.5):
    mid=c.ewm(span=el,adjust=False).mean(); atr=compute_tr(h,l,c).rolling(al).mean()
    return mid+atr*m,mid,mid-atr*m

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

# ──────────────────────────────────────────
# 선행 지표 계산
# ──────────────────────────────────────────
def compute_momentum_acceleration(df):
    rsi_vel=df['RSI']-df['RSI'].shift(3); df['RSI_Accel']=rsi_vel-rsi_vel.shift(3)
    wt_vel=df['WT1']-df['WT1'].shift(3); df['WT_Accel']=wt_vel-wt_vel.shift(3)
    df['MACD_Accel']=df['MACD_Hist']-df['MACD_Hist'].shift(3)
    ra=df['RSI_Accel']/(df['RSI_Accel'].rolling(50,min_periods=10).std()+1e-10)
    wa=df['WT_Accel']/(df['WT_Accel'].rolling(50,min_periods=10).std()+1e-10)
    ma=df['MACD_Accel']/(df['MACD_Accel'].rolling(50,min_periods=10).std()+1e-10)
    df['Composite_Accel']=(ra+wa+ma)/3; return df

def compute_convergence_speed(df):
    gap=df['WT1']-df['WT2']; gap_abs=gap.abs()
    df['WT_Gap']=gap; df['WT_Gap_Abs']=gap_abs
    df['WT_Conv_Speed']=gap_abs.shift(3)-gap_abs
    df['WT_Conv_Bull']=(gap<0)&(df['WT_Conv_Speed']>JT.CONVERGENCE_SLOW)&(df['WT1']<20)
    df['WT_Conv_Bear']=(gap>0)&(df['WT_Conv_Speed']>JT.CONVERGENCE_SLOW)&(df['WT1']>-20)
    return df

def compute_setup_pressure(df):
    idx=df.index; bb_w=df.get('BB_Width',pd.Series(0,index=idx))
    bb_w_ma=bb_w.rolling(50,min_periods=10).mean()
    vol_ratio=df['Volume']/(df['Volume'].rolling(20,min_periods=5).mean()+1e-10)
    vol_dry_streak=_vectorized_streak(vol_ratio<0.7); rmfi=df['RSI_MFI']
    ca=df.get('Composite_Accel',pd.Series(0,index=idx))
    bp=pd.Series(0.0,index=idx)
    bp+=np.where(df['WT1']<-40,2,np.where(df['WT1']<-20,1,0))
    bp+=np.where(df['RSI']<35,1.5,np.where(df['RSI']<45,0.5,0))
    bp+=np.where(df['StochK']<25,1,0)
    bp+=np.where(ca>JT.ACCEL_MODERATE,2,np.where(ca>0.5,1,0))
    bp+=np.where(df.get('WT_Conv_Bull',pd.Series(False,index=idx)),1.5,0)
    bp+=np.where(bb_w<bb_w_ma*0.7,1.5,np.where(bb_w<bb_w_ma,0.5,0))
    bp+=np.where(vol_dry_streak>=3,1,0)
    bp+=np.where((rmfi<0)&(rmfi>rmfi.shift(3)),1,0)
    df['Setup_Pressure_Buy']=bp
    sp=pd.Series(0.0,index=idx)
    sp+=np.where(df['WT1']>40,2,np.where(df['WT1']>20,1,0))
    sp+=np.where(df['RSI']>65,1.5,np.where(df['RSI']>55,0.5,0))
    sp+=np.where(df['StochK']>75,1,0)
    sp+=np.where(ca<-JT.ACCEL_MODERATE,2,np.where(ca<-0.5,1,0))
    sp+=np.where(df.get('WT_Conv_Bear',pd.Series(False,index=idx)),1.5,0)
    sp+=np.where(bb_w<bb_w_ma*0.7,1.5,np.where(bb_w<bb_w_ma,0.5,0))
    sp+=np.where(vol_dry_streak>=3,1,0)
    sp+=np.where((rmfi>0)&(rmfi<rmfi.shift(3)),1,0)
    df['Setup_Pressure_Sell']=sp; return df

def detect_anticipation_signals(df):
    idx=df.index; bb_w=df.get('BB_Width',pd.Series(0,index=idx))
    bb_w_q10=bb_w.rolling(120,min_periods=20).quantile(0.1); squeeze_tight=bb_w<=bb_w_q10
    mh=df['MACD_Hist']
    mt_up=(mh<0)&(mh>mh.shift(1))&(mh.shift(1)>mh.shift(2))
    mt_dn=(mh>0)&(mh<mh.shift(1))&(mh.shift(1)<mh.shift(2))
    df['Setup_Squeeze_Bull']=squeeze_tight&mt_up&(df['WT1']<30)
    df['Setup_Squeeze_Bear']=squeeze_tight&mt_dn&(df['WT1']>-30)
    ca=df.get('Composite_Accel',pd.Series(0,index=idx))
    rau=df.get('RSI_Accel',pd.Series(0,index=idx))>0
    wau=df.get('WT_Accel',pd.Series(0,index=idx))>0
    mau=df.get('MACD_Accel',pd.Series(0,index=idx))>0
    df['Momentum_Accel_Buy']=rau&wau&mau&(ca>JT.ACCEL_MODERATE)&(df['WT1']<40)
    df['Momentum_Accel_Sell']=(~rau)&(~wau)&(~mau)&(ca<-JT.ACCEL_MODERATE)&(df['WT1']>-40)
    vr=df['Volume']/(df['Volume'].rolling(20,min_periods=5).mean()+1e-10)
    df['Volume_Dry_Up']=_vectorized_streak(vr<0.6)>=5
    cs=df.get('WT_Conv_Speed',pd.Series(0,index=idx))
    ga=df.get('WT_Gap_Abs',pd.Series(999,index=idx))
    df['WT_Convergence_Bull']=(cs>JT.CONVERGENCE_FAST)&(ga>2)&(ga<15)&(df['WT1']<df['WT2'])&(df['WT1']<20)
    df['WT_Convergence_Bear']=(cs>JT.CONVERGENCE_FAST)&(ga>2)&(ga<15)&(df['WT1']>df['WT2'])&(df['WT1']>-20)
    return df

# ──────────────────────────────────────────
# 지표 통합 계산
# ──────────────────────────────────────────
def compute_indicators(df):
    c,h,l,v=df['Close'],df['High'],df['Low'],df['Volume']
    for ma in [5,10,20,50,100,125,200]: df[f'MA{ma}']=c.rolling(ma).mean()
    df['EMA8']=c.ewm(span=8,adjust=False).mean(); df['EMA21']=c.ewm(span=21,adjust=False).mean()
    df['BB_Mid']=df['MA20']; s20=c.rolling(20).std()
    df['BB_Up'],df['BB_Low']=df['BB_Mid']+s20*2,df['BB_Mid']-s20*2
    df['BB_Width']=(df['BB_Up']-df['BB_Low'])/(df['BB_Mid']+1e-10)
    df['Percent_B']=(c-df['BB_Low'])/(df['BB_Up']-df['BB_Low']+1e-10)
    df['ATR']=compute_tr(h,l,c).rolling(14).mean()
    atr22=compute_tr(h,l,c).rolling(22).mean()
    df['Chandelier_Long']=h.rolling(22).max()-atr22*3; df['Chandelier_Short']=l.rolling(22).min()+atr22*3
    df['SuperTrend'],df['ST_Direction']=compute_supertrend(h,l,c)
    wt1,wt2,wu,wd=compute_wavetrend(h,l,c)
    df['WT1'],df['WT2'],df['WT_Up'],df['WT_Down']=wt1,wt2,wu,wd
    df['RSI']=compute_rsi(c,14); df['StochK'],df['StochD']=compute_stoch_rsi(c)
    df['MFI']=compute_mfi(h,l,c,v,14); df['RSI_MFI']=compute_rsi_mfi(h,l,c,v,60)
    vwap=(c*v).rolling(20).sum()/(v.rolling(20).sum()+1e-10)
    df['VWAP_Osc']=((c-vwap)/(vwap+1e-10))*100
    df['ADX'],df['Plus_DI'],df['Minus_DI']=compute_adx(h,l,c); df['OBV']=compute_obv(c,v)
    df['KC_Upper'],df['KC_Mid'],df['KC_Lower']=compute_keltner(h,l,c)
    df['MACD_Line'],df['MACD_Signal'],df['MACD_Hist']=compute_macd(c)
    t,k,sa,sb,ch=compute_ichimoku(h,l,c)
    df['Ichimoku_Tenkan'],df['Ichimoku_Kijun']=t,k
    df['Ichimoku_SenkouA'],df['Ichimoku_SenkouB'],df['Ichimoku_Chikou']=sa,sb,ch
    df['CMF']=compute_cmf(h,l,c,v,20)
    df=compute_momentum_acceleration(df)
    df=compute_convergence_speed(df)
    df=compute_setup_pressure(df)
    return df

# ──────────────────────────────────────────
# 패턴 탐지 함수들 (압축)
# ──────────────────────────────────────────
def detect_pivot_div(price,osc,lb=60,pw=5,os_lim=None,ob_lim=None):
    n=len(price); pv,ov=price.values,osc.values; half=pw; p_lo,p_hi=[],[]
    for i in range(2*half,n):
        c_=i-half; w=pv[i-2*half:i+1]
        if pv[c_]==w.min(): p_lo.append((i,c_))
        if pv[c_]==w.max(): p_hi.append((i,c_))
    bd=pd.Series(False,index=price.index); brd=pd.Series(False,index=price.index)
    hb=pd.Series(False,index=price.index); hbr=pd.Series(False,index=price.index)
    for ix in range(1,len(p_lo)):
        ci,pi=p_lo[ix]; cj,pj=p_lo[ix-1]
        if not (pw*2<=(pi-pj)<=lb): continue
        if (os_lim is None or ov[pi]<=os_lim) and pv[pi]<pv[pj] and ov[pi]>ov[pj]: bd.iloc[ci]=True
        if pv[pi]>pv[pj] and ov[pi]<ov[pj]: hb.iloc[ci]=True
    for ix in range(1,len(p_hi)):
        ci,pi=p_hi[ix]; cj,pj=p_hi[ix-1]
        if not (pw*2<=(pi-pj)<=lb): continue
        if (ob_lim is None or ov[pi]>=ob_lim) and pv[pi]>pv[pj] and ov[pi]<ov[pj]: brd.iloc[ci]=True
        if pv[pi]<pv[pj] and ov[pi]>ov[pj]: hbr.iloc[ci]=True
    return bd,brd,hb,hbr

def detect_ttm_squeeze(bbu,bbl,kcu,kcl,c,h,l,kcm):
    sq=(bbu<kcu)&(bbl>kcl); fire=(~sq)&sq.shift(1).fillna(False)
    mom=c-((h.rolling(20).max()+l.rolling(20).min())/2+kcm)/2
    return sq,fire&(mom>0)&(mom>mom.shift(1)),fire&(mom<0)&(mom<mom.shift(1))

def detect_volume_climax(c,o,v,wt1,atr,z=2.5):
    vm=v.rolling(20).mean(); vs=v.rolling(20).std(); vz=(v-vm)/(vs+1e-10)
    big=(c-o).abs()>atr*0.5; ps=(vz.shift(1)>z)&big.shift(1)
    return ps&(c.shift(1)<o.shift(1))&(wt1.shift(1)<-40)&(c>o), ps&(c.shift(1)>o.shift(1))&(wt1.shift(1)>40)&(c<o)

def _detect_engulfing_pair(c,o,wt1,wt_t=20):
    body=(c-o).abs(); bp=(c.shift(1)-o.shift(1)).abs(); ab=body.rolling(20).mean()
    big=(body>ab*0.8)&(body>bp)
    pbh=pd.concat([c.shift(1),o.shift(1)],axis=1).max(axis=1)
    pbl=pd.concat([c.shift(1),o.shift(1)],axis=1).min(axis=1)
    cbh=pd.concat([c,o],axis=1).max(axis=1); cbl=pd.concat([c,o],axis=1).min(axis=1)
    bull=(c.shift(1)<o.shift(1))&(c>o)&(cbl<=pbl)&(cbh>=pbh)&big&(wt1<-wt_t)
    bear=(c.shift(1)>o.shift(1))&(c<o)&(cbl<=pbl)&(cbh>=pbh)&big&(wt1>wt_t)
    return bull,bear

def _detect_parabolic_pair(c,o,wt1,bbu,bbl,atr):
    return (((wt1<-80)&(wt1>wt1.shift(1))&(c>o)&(c>c.shift(1)))|((c<bbl-atr*1.5)&(c>o)),
            ((wt1>80)&(wt1<wt1.shift(1))&(c<o)&(c<c.shift(1)))|((c>bbu+atr*1.5)&(c<o)))

def _detect_ema_pullback_pair(c,h,l,v,e8,e21,atr,wt1,wt2):
    vok=_volf(v,0.5); ar=atr/(c+1e-10); results={}
    for d in ['buy','sell']:
        slope=e21>e21.shift(5) if d=='buy' else e21<e21.shift(5)
        trend=((e8>e21) if d=='buy' else (e8<e21))&slope
        side=(c>e8) if d=='buy' else (c<e8)
        if d=='buy':
            t=(l<=e8*(1+ar*0.15))&(l>=e21*(1-ar*0.25)); tr=_recent(t,2)
            b=(c>=e8)&(c>h.shift(1)); wok=(wt1>wt1.shift(1))&(wt1>wt2)&(wt1<60)
        else:
            t=(h>=e8*(1-ar*0.15))&(h<=e21*(1+ar*0.25)); tr=_recent(t,2)
            b=(c<=e8)&(c<l.shift(1)); wok=(wt1<wt1.shift(1))&(wt1<wt2)&(wt1>-60)
        results[d]=trend&side&tr&b&wok&vok
    return results['buy'],results['sell']

def _detect_mom_ignition_pair(c,o,v,bbu,bbl,atr,e8,e21,wt1,bb_w):
    body=(c-o).abs(); bb=body>atr*1.5; hv=v>v.rolling(20).mean()*2
    comp=bb_w.shift(1)<bb_w.rolling(20).mean().shift(1)
    return (c>o)&bb&hv&(c>bbu)&(e8>e21)&(wt1<50)&comp,(c<o)&bb&hv&(c<bbl)&(e8<e21)&(wt1>-50)&comp

def _detect_vwap_pair(c,vosc,wt1,wt2,v,atr):
    vok=_volf(v,0.7); ap=(atr/(c+1e-10)*100).clip(0.3,3); dt=(ap*0.3).clip(0.3,1.5)
    return (vosc>0)&(vosc.shift(1)<-dt)&(wt1>wt2)&(wt1<30)&vok,(vosc<0)&(vosc.shift(1)>dt)&(wt1<wt2)&(wt1>-30)&vok

def detect_candlestick_patterns(c,o,h,l,wt1,atr):
    body=(c-o).abs(); us=h-pd.concat([c,o],axis=1).max(axis=1)
    ls=pd.concat([c,o],axis=1).min(axis=1)-l; fr=h-l+1e-10; ab=body.rolling(20).mean()
    ism=body<ab*0.6; mr=atr*0.5
    hammer=(ls>=body*2)&(us<=body*0.3)&ism&(wt1<-20)&(c>=o)&(fr>mr)
    shooting=(us>=body*2)&(ls<=body*0.3)&ism&(wt1>20)&(c<=o)&(fr>mr)
    doji=(body<=fr*0.05)&(fr>atr*0.3)
    doji_bull=doji&(wt1<-30)&(wt1>wt1.shift(1))&(c.shift(1)<c.shift(3))
    doji_bear=doji&(wt1>30)&(wt1<wt1.shift(1))&(c.shift(1)>c.shift(3))
    d1b=(c.shift(2)<o.shift(2))&(body.shift(2)>ab.shift(2)); d2s=body.shift(1)<ab.shift(1)*0.5
    d3bu=(c>o)&(c>(o.shift(2)+c.shift(2))/2)&(body>ab*0.8)
    morning=d1b&d2s&d3bu&(wt1<-15)
    d1bu=(c.shift(2)>o.shift(2))&(body.shift(2)>ab.shift(2))
    d3be=(c<o)&(c<(o.shift(2)+c.shift(2))/2)&(body>ab*0.8)
    evening=d1bu&d2s&d3be&(wt1>15)
    return hammer,shooting,doji_bull,doji_bear,morning,evening

def detect_inside_outside_day(h,l,c,o,wt1):
    inside=(h<h.shift(1))&(l>l.shift(1)); outside=(h>h.shift(1))&(l<l.shift(1))
    return inside,outside&(c>o)&(c>h.shift(1))&(wt1<30),outside&(c<o)&(c<l.shift(1))&(wt1>-30)

def detect_ma_crossovers(c,ma20,ma50,ma200):
    s={}
    for tag,ma in [('20MA',ma20),('50MA',ma50),('200MA',ma200)]:
        s[f'Cross_Above_{tag}']=(c>ma)&(c.shift(1)<=ma.shift(1))
        s[f'Fell_Below_{tag}']=(c<ma)&(c.shift(1)>=ma.shift(1))
    return s

def detect_bb_extra(c,o,bb_up,bb_low,bb_w,wt1):
    bwm=bb_w.rolling(20).mean(); wide=(bb_w>bb_w.shift(1))&(bb_w.shift(1)<bwm.shift(1))
    below=c<bb_low
    return (c>bb_up, below&(c>o)&(wt1>wt1.shift(1)), below&(c<o)&(wt1<wt1.shift(1)),
            wide&(c>c.shift(1))&(wt1>wt1.shift(1)), wide&(c<c.shift(1))&(wt1<wt1.shift(1)))

def detect_macd_centerline(ml):
    return (ml>0)&(ml.shift(1)<=0),(ml<0)&(ml.shift(1)>=0)

def detect_consecutive_days(c):
    up=c>c.shift(1); dn=c<c.shift(1)
    return {'Up_3_Days':_vectorized_streak(up)>=3,'Up_5_Days':_vectorized_streak(up)>=5,
            'Down_3_Days':_vectorized_streak(dn)>=3,'Down_5_Days':_vectorized_streak(dn)>=5}

def detect_gaps(c,o,h,l,atr):
    thr=atr*0.5; gu=(o>h.shift(1))&((o-h.shift(1))>thr); gd=(o<l.shift(1))&((l.shift(1)-o)>thr)
    return gu,gd,gu.shift(1).fillna(False)&(l<=h.shift(2)),gd.shift(1).fillna(False)&(h>=l.shift(2))

def detect_nr7(h,l):
    dr=h-l; mn7=dr.rolling(7).min(); nr=dr<=mn7; return nr,nr&nr.shift(1).fillna(False)

def detect_range_bars(h,l,atr):
    dr=h-l; wide=dr>atr*2; narrow=dr<atr*0.5
    rw=wide.rolling(5,min_periods=1).max().shift(1).fillna(False).astype(bool)
    return wide,rw&narrow

def detect_52w(c,h,l):
    h252=h.rolling(252,min_periods=200).max().shift(1); l252=l.rolling(252,min_periods=200).min().shift(1)
    return h>h252,l<l252

def detect_123_pullback(h,l,c,adx,pdi,mdi):
    sb=(adx>30)&(pdi>mdi); ss=(adx>30)&(mdi>pdi)
    ins=(h<h.shift(1))&(l>l.shift(1))
    ll1=l<l.shift(1);ll2=l.shift(1)<l.shift(2);ll3=l.shift(2)<l.shift(3)
    tll=ll1&ll2&ll3; tli=(ll1&ll2&ins.shift(2))|(ll1&ins.shift(1)&ll2.shift(1))|(ins&ll1&ll2)
    hh1=h>h.shift(1);hh2=h.shift(1)>h.shift(2);hh3=h.shift(2)>h.shift(3)
    thh=hh1&hh2&hh3; thi=(hh1&hh2&ins.shift(2))|(hh1&ins.shift(1)&hh2.shift(1))|(ins&hh1&hh2)
    return sb&(tll|tli),ss&(thh|thi)

def detect_180_setup(c,o,h,l,ma10,ma50):
    dr=h-l+1e-10; cp=(c-l)/dr; pp=(c.shift(1)-l.shift(1))/(h.shift(1)-l.shift(1)+1e-10)
    return (pp<=0.25)&(cp>=0.75)&(c>ma10)&(c>ma50),(pp>=0.75)&(cp<=0.25)&(c<ma10)&(c<ma50)

def detect_boomer(h,l,adx,pdi,mdi):
    ins=(h<h.shift(1))&(l>l.shift(1)); in2=ins&ins.shift(1)
    return in2.shift(1).fillna(False)&(adx>30)&(pdi>mdi),in2.shift(1).fillna(False)&(adx>30)&(mdi>pdi)

def detect_expansion(h,l,c):
    dr=h-l; mr9=dr.rolling(9).max(); h60=h.rolling(60,min_periods=40).max(); l60=l.rolling(60,min_periods=40).min()
    return (h>=h60)&(dr>=mr9),(l<=l60)&(dr>=mr9)

def detect_gilligans(o,c,h,l):
    dr=h-l+1e-10; cp=(c-l)/dr; l60=l.rolling(60,min_periods=40).min(); h60=h.rolling(60,min_periods=40).max()
    return (o<=l60)&(o<l.shift(1))&(cp>=0.5)&(c>=o),(o>=h60)&(o>h.shift(1))&(cp<=0.5)&(c<=o)

def detect_lizard(o,c,h,l):
    dr=h-l+1e-10; cp=(c-l)/dr; op=(o-l)/dr
    return (cp>=0.75)&(op>=0.75)&(l<=l.rolling(10).min()),(cp<=0.25)&(op<=0.25)&(h>=h.rolling(10).max())

def detect_non_adx_123(h,l,c,ma50):
    ins=(h<h.shift(1))&(l>l.shift(1))
    ll1=l<l.shift(1);ll2=l.shift(1)<l.shift(2)
    tll=ll1&ll2&(l.shift(2)<l.shift(3)); tli=(ll1&ll2&ins.shift(2))|(ll1&ins.shift(1)&ll2.shift(1))|(ins&ll1&ll2)
    hh1=h>h.shift(1);hh2=h.shift(1)>h.shift(2)
    thh=hh1&hh2&(h.shift(2)>h.shift(3)); thi=(hh1&hh2&ins.shift(2))|(hh1&ins.shift(1)&hh2.shift(1))|(ins&hh1&hh2)
    return (c>ma50)&(tll|tli),(c<ma50)&(thh|thi)

def detect_pocket_pivot(c,o,v,ma50,ma200):
    dv=v.where(c<c.shift(1),0); return (c>o)&(v>dv.rolling(10).max())&(c>ma50)&(c>c.shift(1))

def detect_ichimoku_signals(c,tenkan,kijun,sa,sb):
    kt=pd.concat([sa,sb],axis=1).max(axis=1); kb=pd.concat([sa,sb],axis=1).min(axis=1)
    return ((c>kt)&(c.shift(1)<=kt.shift(1))&(tenkan>kijun),
            (c<kb)&(c.shift(1)>=kb.shift(1))&(tenkan<kijun),
            (tenkan>kijun)&(tenkan.shift(1)<=kijun.shift(1))&(c>kt),
            (tenkan<kijun)&(tenkan.shift(1)>=kijun.shift(1))&(c<kb))

def detect_cmf_signals(cmf,c,ma50):
    return (cmf>0.1)&(cmf.shift(1)<=0.1)&(c>ma50),(cmf<-0.1)&(cmf.shift(1)>=-0.1)&(c<ma50)

def detect_mf_signals(c,rmfi):
    mcb=(rmfi>0)&(rmfi.shift(1)<=0); mcbe=(rmfi<0)&(rmfi.shift(1)>=0)
    mr=rmfi>rmfi.shift(1); mf=rmfi<rmfi.shift(1)
    mus=_vectorized_streak(mr); mds=_vectorized_streak(mf)
    ms5=rmfi-rmfi.shift(5); ms10=rmfi-rmfi.shift(10)
    pl=c<c.rolling(5).min().shift(1); mh=rmfi>rmfi.rolling(5).min().shift(1)
    mbd=pl&mh&(rmfi<0)
    ph=c>c.rolling(5).max().shift(1); ml=rmfi<rmfi.rolling(5).max().shift(1)
    mbrd=ph&ml&(rmfi>0)
    return {'MF_Cross_Bull':mcb,'MF_Cross_Bear':mcbe,'MF_Strong_Up':mus>=3,'MF_Strong_Dn':mds>=3,
            'MF_Accel_Up':mus>=5,'MF_Accel_Dn':mds>=5,'MF_Slope_5':ms5,'MF_Slope_10':ms10,
            'MF_Bull_Div':mbd,'MF_Bear_Div':mbrd,'MF_Rising':mr,'MF_Falling':mf,
            'MF_Up_Streak':mus,'MF_Dn_Streak':mds}

def _deduplicate(df):
    for _,sigs in SIGNAL_HIERARCHY.items():
        for i,s in enumerate(sigs):
            if s not in df.columns: continue
            for higher in sigs[:i]:
                if higher in df.columns: df[s]=df[s]&~df[higher]
    return df

# ──────────────────────────────────────────
# 통합 시그널 탐지 엔진
# ──────────────────────────────────────────
def detect_all_signals(df):
    H,L,C,O,V=df['High'],df['Low'],df['Close'],df['Open'],df['Volume']
    e8,e21=df['EMA8'],df['EMA21']; m10,m20,m50,m200=df['MA10'],df['MA20'],df['MA50'],df['MA200']
    wt1,wt2,atr=df['WT1'],df['WT2'],df['ATR']
    htf1=(e8>e21)&(e21>e21.shift(5)); htf2=(C>m50)&(m50>m50.shift(10))
    wun=_recent(df['WT_Up'],2); wdn=_recent(df['WT_Down'],2)
    wur=_recent(df['WT_Up'],3); wdr=_recent(df['WT_Down'],3)
    vol_ok=_volf(V,0.5)
    rb=(df['ADX']>25)&(df['Plus_DI']>df['Minus_DI'])&(C>m50)
    rbe=(df['ADX']>25)&(df['Minus_DI']>df['Plus_DI'])&(C<m50)
    rxb=rb&(C>m200)&(m50>m50.shift(5)); rxbe=rbe&(C<m200)&(m50<m50.shift(5))
    mfp=df['RSI_MFI']>-10; mfn=df['RSI_MFI']<10
    para_bot,para_top=_detect_parabolic_pair(C,O,wt1,df['BB_Up'],df['BB_Low'],atr)
    stfb=(df['ST_Direction']==-1)&(df['ST_Direction'].shift(1)==1); stfb.iloc[:ST_MIN_BAR]=False
    stbr=_recent(stfb,3)
    stfbu=(df['ST_Direction']==1)&(df['ST_Direction'].shift(1)==-1); stfbu.iloc[:ST_MIN_BAR]=False
    stbur=_recent(stfbu,3)
    ss=rb&(~para_top)&(~stbr); bs=rbe&(~para_bot)&(~stbur)
    ssx=rxb&(~para_top)&(~stbr); bsx=rxbe&(~para_bot)&(~stbur)
    # MF 시그널 (한 번만 계산)
    mfs=detect_mf_signals(C,df['RSI_MFI'])
    df['MF_Cross_Bull']=mfs['MF_Cross_Bull']&(~bs)&vol_ok
    df['MF_Cross_Bear']=mfs['MF_Cross_Bear']&(~ss)&vol_ok
    df['MF_Bull_Div']=mfs['MF_Bull_Div']&(~bs)&vol_ok
    df['MF_Bear_Div']=mfs['MF_Bear_Div']&(~ss)&vol_ok
    for k in ['MF_Accel_Up','MF_Accel_Dn','MF_Slope_5','MF_Slope_10','MF_Rising','MF_Falling',
              'MF_Strong_Up','MF_Strong_Dn','MF_Up_Streak','MF_Dn_Streak']:
        df[k]=mfs[k]
    # MCB+
    df['Green_Dot_T1']=wun&(wt1<=OS1)&(df['RSI']<30)&(df['MFI']<30)&(df['RSI_MFI']<0)&(~bsx)&vol_ok
    df['Green_Dot_T2']=wun&(wt1<=OS1)&((df['RSI']<32)|(df['MFI']<32))&~df['Green_Dot_T1']&(~bs)&vol_ok
    ag=df['Green_Dot_T1']|df['Green_Dot_T2']
    df['Red_Dot_T1']=wdn&(wt1>=OB1)&(df['RSI']>70)&(df['MFI']>70)&(df['RSI_MFI']>0)&(~ssx)&vol_ok
    df['Red_Dot_T2']=wdn&(wt1>=OB1)&((df['RSI']>68)|(df['MFI']>68))&~df['Red_Dot_T1']&(~ss)&vol_ok
    ar=df['Red_Dot_T1']|df['Red_Dot_T2']
    df['Blue_Diamond']=(wt2<=0)&wun&htf1&htf2&(~bs)&mfp&vol_ok
    df['Red_Diamond']=(wt2>=0)&wdn&~htf1&~htf2&(~ss)&mfn&vol_ok
    df['Green_Circle']=wun&(wt1<=OS1)&~ag&(~bs)&vol_ok&(df['RSI']<45)
    df['Red_Circle']=wdn&(wt1>=OB1)&~ar&(~ss)&vol_ok&(df['RSI']>55)
    bd,brd,hb,hbr=detect_pivot_div(C,wt1,60,5,OS1,OB1)
    bdr=_recent(bd,3); brdr=_recent(brd,3)
    rbd,rbrd,_,_=detect_pivot_div(C,df['RSI'],60,5,35,65)
    obd,obrd,_,_=detect_pivot_div(C,df['OBV'],60,5)
    df['Gold_Dot']=df['Green_Dot_T1']&(wt1<=OS2)&bdr
    df['Blood_Diamond']=df['Red_Dot_T1']&(wt1>=OB2)&brdr
    df['Bull_Divergence']=bd&wur&~ag&~df['Gold_Dot']&(~bs)&vol_ok
    df['Bear_Divergence']=brd&wdr&~ar&(~ss)&vol_ok
    df['RSI_Bull_Divergence']=rbd&(wt1<-20)&(~bs)&vol_ok&~bd
    df['RSI_Bear_Divergence']=rbrd&(wt1>20)&(~ss)&vol_ok&~brd
    vos=_volf(V,0.7)
    df['Hidden_Bull_Div']=hb&(wt1<-25)&htf2&(~bsx)&vos
    df['Hidden_Bear_Div']=hbr&(wt1>25)&~htf2&(~ssx)&vos
    df['OBV_Div_Buy']=obd&(wt1<-30)&(~bsx); df['OBV_Div_Sell']=obrd&(wt1>30)&(~ssx)
    sqo,sqb,sqs=detect_ttm_squeeze(df['BB_Up'],df['BB_Low'],df['KC_Upper'],df['KC_Lower'],C,H,L,df['KC_Mid'])
    df['Squeeze_On']=sqo; df['Squeeze_Fire_Buy']=sqb&(~bs)&vol_ok; df['Squeeze_Fire_Sell']=sqs&(~ss)&vol_ok
    df['Volume_Climax_Buy'],df['Volume_Climax_Sell']=detect_volume_climax(C,O,V,wt1,atr)
    ax=(df['ADX']>20)&(df['ADX'].shift(1)<=20)
    df['ADX_Momentum_Buy']=ax&(df['Plus_DI']>df['Minus_DI'])&(wt1>wt2)&vol_ok
    df['ADX_Momentum_Sell']=ax&(df['Minus_DI']>df['Plus_DI'])&(wt1<wt2)&vol_ok
    df['Bullish_Engulfing'],df['Bearish_Engulfing']=_detect_engulfing_pair(C,O,wt1)
    df['Bullish_Engulfing']&=(~bs)&vol_ok; df['Bearish_Engulfing']&=(~ss)&vol_ok
    gc=(m50>m200)&(m50.shift(1)<=m200.shift(1)); dc=(m50<m200)&(m50.shift(1)>=m200.shift(1))
    af=df['ADX']>15; vc=_volf(V,0.7)
    df['Golden_Cross']=gc&af&vc; df['Death_Cross']=dc&af&vc
    df['EMA_Pullback_Buy'],df['EMA_Pullback_Sell']=_detect_ema_pullback_pair(C,H,L,V,e8,e21,atr,wt1,wt2)
    df['Momentum_Ignition_Buy'],df['Momentum_Ignition_Sell']=_detect_mom_ignition_pair(C,O,V,df['BB_Up'],df['BB_Low'],atr,e8,e21,wt1,df['BB_Width'])
    df['SuperTrend_Buy']=stfbu; df['SuperTrend_Sell']=stfb
    vp=_volf(V,1.0)
    df['Parabolic_Top_Sell']=para_top&((df['WT_Down']|wdr)|((C<O)&(C<C.shift(1))))&vp
    df['Parabolic_Bottom_Buy']=para_bot&((df['WT_Up']|wur)|((C>O)&(C>C.shift(1))))&vp
    df['VWAP_Bounce_Buy'],df['VWAP_Reject_Sell']=_detect_vwap_pair(C,df['VWAP_Osc'],wt1,wt2,V,atr)
    ml,ms=df['MACD_Line'],df['MACD_Signal']
    df['MACD_Cross_Buy']=(ml>ms)&(ml.shift(1)<=ms.shift(1))&(ml<0)&(~bs)&vol_ok
    df['MACD_Cross_Sell']=(ml<ms)&(ml.shift(1)>=ms.shift(1))&(ml>0)&(~ss)&vol_ok
    df['StochRSI_Cross_Buy']=(df['StochK']>df['StochD'])&(df['StochK'].shift(1)<=df['StochD'].shift(1))&(df['StochK']<25)&(~bs)&vol_ok
    df['StochRSI_Cross_Sell']=(df['StochK']<df['StochD'])&(df['StochK'].shift(1)>=df['StochD'].shift(1))&(df['StochK']>75)&(~ss)&vol_ok
    (df['Hammer'],df['Shooting_Star'],df['Doji_Bullish'],df['Doji_Bearish'],
     df['Morning_Star'],df['Evening_Star'])=detect_candlestick_patterns(C,O,H,L,wt1,atr)
    for s in ['Hammer','Doji_Bullish','Morning_Star','Outside_Bullish']: 
        if s in df.columns: df[s]&=(~bs)&vol_ok
    for s in ['Shooting_Star','Doji_Bearish','Evening_Star','Outside_Bearish']:
        if s in df.columns: df[s]&=(~ss)&vol_ok
    df['Inside_Day'],df['Outside_Bullish'],df['Outside_Bearish']=detect_inside_outside_day(H,L,C,O,wt1)
    df['Outside_Bullish']&=(~bs)&vol_ok; df['Outside_Bearish']&=(~ss)&vol_ok
    for k,v in detect_ma_crossovers(C,m20,m50,m200).items(): df[k]=v
    (df['BB_Upper_Break'],df['BB_Lower_Bounce'],df['BB_Lower_Break'],
     df['BB_Squeeze_End_Bull'],df['BB_Squeeze_End_Bear'])=detect_bb_extra(C,O,df['BB_Up'],df['BB_Low'],df['BB_Width'],wt1)
    df['MACD_Zero_Cross_Buy'],df['MACD_Zero_Cross_Sell']=detect_macd_centerline(df['MACD_Line'])
    for k,v in detect_consecutive_days(C).items(): df[k]=v
    df['Gap_Up'],df['Gap_Down'],df['Gap_Up_Closed'],df['Gap_Down_Closed']=detect_gaps(C,O,H,L,atr)
    df['NR7'],df['NR7_2']=detect_nr7(H,L)
    df['Wide_Range_Bar'],df['Calm_After_Storm']=detect_range_bars(H,L,atr)
    df['New_52W_High'],df['New_52W_Low']=detect_52w(C,H,L)
    df['Pullback_123_Bull'],df['Pullback_123_Bear']=detect_123_pullback(H,L,C,df['ADX'],df['Plus_DI'],df['Minus_DI'])
    df['Setup_180_Bull'],df['Setup_180_Bear']=detect_180_setup(C,O,H,L,m10,m50)
    df['Boomer_Buy'],df['Boomer_Sell']=detect_boomer(H,L,df['ADX'],df['Plus_DI'],df['Minus_DI'])
    df['Expansion_BO'],df['Expansion_BD']=detect_expansion(H,L,C)
    df['Gilligans_Buy'],df['Gilligans_Sell']=detect_gilligans(O,C,H,L)
    df['Lizard_Bull'],df['Lizard_Bear']=detect_lizard(O,C,H,L)
    df['NonADX_123_Bull'],df['NonADX_123_Bear']=detect_non_adx_123(H,L,C,m50)
    df['Pocket_Pivot']=detect_pocket_pivot(C,O,V,m50,m200)
    (df['Kumo_Breakout_Bull'],df['Kumo_Breakout_Bear'],df['TK_Cross_Bull'],df['TK_Cross_Bear'])=detect_ichimoku_signals(C,df['Ichimoku_Tenkan'],df['Ichimoku_Kijun'],df['Ichimoku_SenkouA'],df['Ichimoku_SenkouB'])
    for s in ['Kumo_Breakout_Bull','Kumo_Breakout_Bear','TK_Cross_Bull','TK_Cross_Bear','CMF_Bull','CMF_Bear']:
        if s in df.columns: df[s]&=vol_ok
    df['CMF_Bull'],df['CMF_Bear']=detect_cmf_signals(df['CMF'],C,m50)
    df['CMF_Bull']&=vol_ok; df['CMF_Bear']&=vol_ok
    # 선행 시그널
    df=detect_anticipation_signals(df)
    abf=ag|df['Gold_Dot']|df['Squeeze_Fire_Buy']|df['Bullish_Engulfing']
    asf=ar|df['Blood_Diamond']|df['Squeeze_Fire_Sell']|df['Bearish_Engulfing']
    df['Setup_Squeeze_Bull']&=~abf; df['Setup_Squeeze_Bear']&=~asf
    df['Momentum_Accel_Buy']&=~abf; df['Momentum_Accel_Sell']&=~asf
    df['WT_Convergence_Bull']&=~df['WT_Up']; df['WT_Convergence_Bear']&=~df['WT_Down']
    # 쿨다운
    PAIRED={('MACD_Cross_Buy','MACD_Cross_Sell'):12,('StochRSI_Cross_Buy','StochRSI_Cross_Sell'):7,
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
        ('WT_Convergence_Bull','WT_Convergence_Bear'):5}
    ph=set()
    for (b,s),cd in PAIRED.items(): _cooldown_directional(df,b,s,cd); ph.add(b); ph.add(s)
    for s,cd in COOLDOWN_MAP.items():
        if s in df.columns and s not in ph: df[s]=_cooldown(df[s],cd)
    _deduplicate(df)
    compute_confluence(df)
    df['Buy_Proximity'],df['Sell_Proximity']=compute_proximity(df)
    df['Strong_Bull'],df['Strong_Bear']=rb,rbe
    df['Parabolic_Blowoff']=para_top; df['Parabolic_Bottom_Raw']=para_bot
    df['ST_Bear_Override']=stbr; df['Sell_Shield_Overridden']=para_top|stbr
    df['Buy_Shield_Overridden']=para_bot|stbur
    df['_HTF1_Bull'],df['_HTF2_Bull']=htf1,htf2
    # ★ 스캐너 콤보 탐지
    df=detect_scanner_combos(df)
    # ★ 판단 엔진
    compute_trade_judgment(df)
    return df

# ──────────────────────────────────────────
# ★ 스캐너 콤보 탐지 함수
# ──────────────────────────────────────────
def detect_scanner_combos(df):
    idx=df.index; C,O,H,L,V=df['Close'],df['Open'],df['High'],df['Low'],df['Volume']
    F=lambda col: df.get(col,pd.Series(False,index=idx)).fillna(False)
    def _rec(col,lb=3): return _recent(F(col),lb)
    vr=V/(V.rolling(50,min_periods=10).mean()+1e-10)
    v15=vr>=1.5; v2=vr>=2.0
    a50=C>df['MA50']; b50=C<df['MA50']
    m50r=df['MA50']>df['MA50'].shift(5); m50f=df['MA50']<df['MA50'].shift(5)
    cb=F('Bullish_Engulfing')|F('Hammer')|F('Morning_Star')|F('Doji_Bullish')
    cbe=F('Bearish_Engulfing')|F('Shooting_Star')|F('Evening_Star')|F('Doji_Bearish')
    cmf=df.get('CMF',pd.Series(0,index=idx)); rmfi=df['RSI_MFI']
    mfr=df.get('MF_Rising',pd.Series(False,index=idx)).fillna(False)
    mff=df.get('MF_Falling',pd.Series(False,index=idx)).fillna(False)
    # B1: Oversold Bounce
    so=(df['StochK']<20)&(df['StochD']<20)
    df['SC_Oversold_Bounce']=so&(cb|_rec('StochRSI_Cross_Buy'))&(_rec('Cross_Above_20MA')|(C>df['MA20']))&v15
    # B2: Breakout Momentum
    df['SC_Breakout_Momentum']=(F('Expansion_BO')|F('New_52W_High'))&v2&(df['ADX']>20)
    # B3: Pullback Buy Zone
    p20=(C<=df['MA20']*1.02)&(C>=df['MA20']*0.97)
    df['SC_Pullback_Buy_Zone']=a50&m50r&(p20|_rec('Fell_Below_20MA')|F('EMA_Pullback_Buy'))&(F('Hammer')|F('Doji_Bullish')|F('Outside_Bullish')|(C>O)&(df['WT1']>df['WT1'].shift(1)))
    # B4: Triple Oversold
    to=((df['WT1']<OS1).astype(int)+(df['RSI']<35).astype(int)+(df['MFI']<35).astype(int)+(df['StochK']<20).astype(int))>=3
    sbs=F('Gold_Dot')|F('Green_Dot_T1')|F('Morning_Star')|F('Bullish_Engulfing')|F('Bull_Divergence')|F('Parabolic_Bottom_Buy')
    df['SC_Triple_Oversold']=to&(sbs|cb)
    # B5: Squeeze Fire Bull
    df['SC_Squeeze_Fire_Bull']=(F('BB_Squeeze_End_Bull')|F('Squeeze_Fire_Buy'))&v15&(_rec('MACD_Cross_Buy')|_rec('MACD_Zero_Cross_Buy')|(df['MACD_Hist']>0)&(df['MACD_Hist']>df['MACD_Hist'].shift(1)))
    # B6: Trend Continuation
    df['SC_Trend_Continuation']=(df['ADX']>25)&(df['Plus_DI']>df['Minus_DI'])&(F('Pullback_123_Bull')|F('NonADX_123_Bull')|F('Boomer_Buy'))&(mfr|(rmfi>rmfi.shift(3)))
    # B7: Volume Climax Reversal
    df['SC_Volume_Climax_Rev']=F('Volume_Climax_Buy')&(df['WT1']<-30)&(_rec('Bull_Divergence')|_rec('RSI_Bull_Divergence')|_rec('OBV_Div_Buy')|_rec('MF_Bull_Div')|cb)
    # B8: Ichimoku Breakout
    kt=pd.concat([df.get('Ichimoku_SenkouA',pd.Series(0,index=idx)),df.get('Ichimoku_SenkouB',pd.Series(0,index=idx))],axis=1).max(axis=1)
    df['SC_Ichimoku_Breakout']=(F('Kumo_Breakout_Bull')|F('TK_Cross_Bull'))&(cmf>0.05)&v15&(C>kt)
    # B9: Smart Money
    df['SC_Smart_Money_Accum']=(F('MF_Cross_Bull')|_rec('MF_Bull_Div'))&(cmf>0)&(F('BB_Lower_Bounce')|(df['Percent_B']<0.2))&(df['WT1']>df['WT1'].shift(1))
    # B10: Momentum Ignition
    df['SC_Momentum_Ignition_Buy']=(F('Momentum_Ignition_Buy')|(F('Expansion_BO')&v2))&(F('SuperTrend_Buy')|(df['ST_Direction']==1))&(df['ADX']>20)
    # S1: Overbought Exhaustion
    sob=(df['StochK']>80)&(df['StochD']>80)
    df['SC_Overbought_Exhaust']=sob&(cbe|_rec('StochRSI_Cross_Sell'))&(_rec('Fell_Below_20MA')|(C<df['MA20']))&v15
    # S2: Breakdown Momentum
    df['SC_Breakdown_Momentum']=(F('Expansion_BD')|F('New_52W_Low'))&v2&(df['ADX']>20)
    # S3: Rally Failure
    r20=(C<=df['MA20']*1.02)&(C>=df['MA20']*0.97)
    df['SC_Rally_Failure']=b50&m50f&(r20|_rec('Fell_Below_20MA'))&(F('Shooting_Star')|F('Doji_Bearish')|F('Outside_Bearish')|F('EMA_Pullback_Sell'))
    # S4: Triple Overbought
    tob=((df['WT1']>OB1).astype(int)+(df['RSI']>65).astype(int)+(df['MFI']>65).astype(int)+(df['StochK']>80).astype(int))>=3
    sbe=F('Blood_Diamond')|F('Red_Dot_T1')|F('Evening_Star')|F('Bearish_Engulfing')|F('Bear_Divergence')|F('Parabolic_Top_Sell')
    df['SC_Triple_Overbought']=tob&(sbe|cbe)
    # S5: Squeeze Fire Bear
    df['SC_Squeeze_Fire_Bear']=(F('BB_Squeeze_End_Bear')|F('Squeeze_Fire_Sell'))&v15&(_rec('MACD_Cross_Sell')|_rec('MACD_Zero_Cross_Sell')|(df['MACD_Hist']<0)&(df['MACD_Hist']<df['MACD_Hist'].shift(1)))
    # S6: Trend Breakdown
    df['SC_Trend_Breakdown']=(df['ADX']>25)&(df['Minus_DI']>df['Plus_DI'])&(F('Pullback_123_Bear')|F('NonADX_123_Bear')|F('Boomer_Sell'))&(mff|(rmfi<rmfi.shift(3)))
    # S7: Volume Climax Sell
    df['SC_Volume_Climax_Sell']=F('Volume_Climax_Sell')&(df['WT1']>30)&(_rec('Bear_Divergence')|_rec('RSI_Bear_Divergence')|_rec('OBV_Div_Sell')|_rec('MF_Bear_Div')|cbe)
    # S8: Ichimoku Breakdown
    kb=pd.concat([df.get('Ichimoku_SenkouA',pd.Series(0,index=idx)),df.get('Ichimoku_SenkouB',pd.Series(0,index=idx))],axis=1).min(axis=1)
    df['SC_Ichimoku_Breakdown']=(F('Kumo_Breakout_Bear')|F('TK_Cross_Bear'))&(cmf<-0.05)&v15&(C<kb)
    # S9: Distribution
    df['SC_Distribution']=(F('MF_Cross_Bear')|_rec('MF_Bear_Div'))&(cmf<0)&(df['WT1']<df['WT1'].shift(1))&(df['WT1']>0)
    # S10: Parabolic Exhaustion
    df['SC_Parabolic_Exhaust']=(F('Parabolic_Top_Sell')|((df['WT1']>80)&(df['WT1']<df['WT1'].shift(1))))&v2&(df['RSI']>65)
    # 쿨다운
    for cn in SCANNER_COMBOS:
        if cn in df.columns: df[cn]=_cooldown(df[cn],bars=5)
    return df

# ──────────────────────────────────────────
# Confluence / Proximity
# ──────────────────────────────────────────
def compute_confluence(df,dw=5,df_=0.75):
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
    s+=np.where(wt1<OS1,1,0)+np.where(wt1<OS2,0.5,0)
    s-=np.where(wt1>OB1,1,0)+np.where(wt1>OB2,0.5,0)
    adx,pdi,mdi=df['ADX'].values,df['Plus_DI'].values,df['Minus_DI'].values
    af=np.clip((adx-20)/100,0,0.3)
    s+=np.where((pdi>mdi)&(s>0),s*af,0); s-=np.where((mdi>pdi)&(s<0),abs(s)*af,0)
    df['Confluence_Score']=s
    df['Ultra_Buy']=(s>=6.5)|((s>=5)&(bc>=3)); df['Ultra_Sell']=(s<=-6.5)|((s<=-5)&(sc>=3))
    df['Strong_Buy']=(s>=3.5)&(~df['Ultra_Buy']); df['Strong_Sell']=(s<=-3.5)&(~df['Ultra_Sell'])
    return s

def compute_proximity(df):
    wt1,wt2,rsi,mfi,rmfi=df['WT1'],df['WT2'],df['RSI'],df['MFI'],df['RSI_MFI']
    stk,mh,bb_w=df['StochK'],df['MACD_Hist'],df['BB_Width']
    rbull=df.get('Strong_Bull',pd.Series(False,index=df.index))
    rbear=df.get('Strong_Bear',pd.Series(False,index=df.index))
    bp=pd.Series(0.0,index=df.index); sp=pd.Series(0.0,index=df.index)
    gap=(wt1-wt2).abs(); nc=gap<3; cu=(wt1-wt2)>(wt1.shift(1)-wt2.shift(1)); cd=(wt1-wt2)<(wt1.shift(1)-wt2.shift(1))
    for cond,pts in [((wt1<-40)&nc,30),((wt1<-40)&cu&(gap<8),15),(wt1<OS2,20),
        ((wt1>=OS2)&(wt1<-40),10),(rsi<35,15),((rsi>=35)&(rsi<45),5),(mfi<35,15),
        (rmfi<-5,10),(rmfi>rmfi.shift(1),5),(stk<20,10),(mh>mh.shift(1),2)]:
        bp+=np.where(cond,pts,0)
    for cond,pts in [((wt1>40)&nc,30),((wt1>40)&cd&(gap<8),15),(wt1>OB1,20),
        ((wt1<=OB1)&(wt1>40),10),(rsi>65,15),((rsi<=65)&(rsi>55),5),(mfi>65,15),
        (rmfi>5,10),(rmfi<rmfi.shift(1),5),(stk>80,10),(mh<mh.shift(1),2)]:
        sp+=np.where(cond,pts,0)
    ca=df.get('Composite_Accel',pd.Series(0,index=df.index))
    bp+=np.where(ca>JT.ACCEL_STRONG,15,np.where(ca>JT.ACCEL_MODERATE,8,np.where(ca>0.5,3,0)))
    sp+=np.where(ca<-JT.ACCEL_STRONG,15,np.where(ca<-JT.ACCEL_MODERATE,8,np.where(ca<-0.5,3,0)))
    bp+=np.where(df.get('WT_Conv_Bull',pd.Series(False,index=df.index)),10,0)
    sp+=np.where(df.get('WT_Conv_Bear',pd.Series(False,index=df.index)),10,0)
    sbuy=df.get('Setup_Pressure_Buy',pd.Series(0,index=df.index))
    ssell=df.get('Setup_Pressure_Sell',pd.Series(0,index=df.index))
    bp+=np.where(sbuy>=8,10,np.where(sbuy>=5,5,0))
    sp+=np.where(ssell>=8,10,np.where(ssell>=5,5,0))
    bn=bb_w<bb_w.rolling(50,min_periods=10).quantile(0.2)
    bp+=np.where(bn,5,0); sp+=np.where(bn,5,0)
    bp,sp=bp.clip(upper=100),sp.clip(upper=100); net=bp-sp
    return (pd.Series(np.where(net>=0,bp,bp*np.where(rbear,.4,.55)),index=df.index),
            pd.Series(np.where(net<=0,sp,sp*np.where(rbull,.4,.55)),index=df.index))

# ──────────────────────────────────────────
# 콤보 감지
# ──────────────────────────────────────────
def detect_combos(df,vol_ratio):
    C,idx=df['Close'],df.index; F=lambda col:df.get(col,pd.Series(False,index=idx))
    tu=(C>df['MA200'])&(C>df['MA50'])&(df['MA50']>df['MA200'])
    td=(C<df['MA200'])&(C<df['MA50'])&(df['MA50']<df['MA200'])
    cb=F('Bullish_Engulfing')|F('Hammer')|F('Morning_Star')|F('Doji_Bullish')
    cbe=F('Bearish_Engulfing')|F('Shooting_Star')|F('Evening_Star')|F('Doji_Bearish')
    tb=(df['StochK']<20)|F('StochRSI_Cross_Buy')|F('MACD_Cross_Buy')|(df['WT1']<-30)
    tbe=(df['StochK']>80)|F('StochRSI_Cross_Sell')|F('MACD_Cross_Sell')|(df['WT1']>30)
    vc=vol_ratio>=1.5; sq=(F('NR7')|F('NR7_2')|F('Inside_Day')|F('Calm_After_Storm')|(df['BB_Width']<=df['BB_Width'].rolling(120,min_periods=20).quantile(0.1)))
    mb=(df['RSI_MFI']>df['RSI_MFI'].shift(1))|(df['RSI_MFI']>0)
    mbe=(df['RSI_MFI']<df['RSI_MFI'].shift(1))|(df['RSI_MFI']<0)
    cmf=df.get('CMF',pd.Series(0,index=idx))
    ms=((C-df['MA50']).abs()<=df['ATR']*1.5)|((C-df['MA20']).abs()<=df['ATR']*1)
    df['Combo_TrendPullback_Buy']=tu&(C<df['MA20'])&ms&(cb|tb)&mb
    df['Combo_VolSqueeze_Buy']=sq.shift(1).fillna(False)&(C>df['MA50'])&(F('BB_Squeeze_End_Bull')|(F('Wide_Range_Bar')&(C>df['Open'])))&vc&mb
    oe=(((df['StochK']<20)&(df['StochD']<20)).astype(int)+(df['RSI']<30).astype(int)+(df['WT1']<-53).astype(int))>=2
    df['Combo_Reversal_Buy']=oe&((C>df['MA200'])|(df['MA50']>df['MA200']))&(cb|F('Gold_Dot')|F('Green_Dot_T1')|F('Lizard_Bull')|F('Gilligans_Buy'))
    msb=F('MF_Strong_Up')|(df.get('MF_Slope_5',pd.Series(0,index=idx))>3)
    df['Combo_Momentum_Buy']=(F('New_52W_High')|F('Expansion_BO'))&(vc|F('Pocket_Pivot')|F('Momentum_Ignition_Buy'))&(df['ADX']>25)&(df['Plus_DI']>df['Minus_DI'])&msb
    df['Combo_MAConfluence_Buy']=(df['MA50']>df['MA200'])&(C>df['MA200'])&(F('Cross_Above_20MA')|F('Cross_Above_50MA'))&(F('MACD_Cross_Buy')|F('StochRSI_Cross_Buy')|F('NonADX_123_Bull'))&mb
    df['Combo_MF_Reversal_Buy']=F('MF_Cross_Bull')&(df['WT1']<20)&(C>df['MA50'])&(cb|tb|vc)
    df['Combo_Ichimoku_Buy']=F('Kumo_Breakout_Bull')&(cb|tb|vc)&(cmf>0.05)&(df['ADX']>20)
    ab=(df.get('Setup_Pressure_Buy',pd.Series(0,index=idx))>=5)
    df['Combo_Anticipation_Buy']=ab&sq&((cmf>0.05)|mb)&(F('WT_Convergence_Bull')|F('Momentum_Accel_Buy')|F('Setup_Squeeze_Bull'))
    df['Combo_TrendRejection_Sell']=td&(C>df['MA20'])&(cbe|tbe)&mbe
    ob=(((df['StochK']>80)&(df['StochD']>80)).astype(int)+(df['RSI']>70).astype(int)+(df['WT1']>53).astype(int))>=2
    df['Combo_Exhaustion_Sell']=ob&(cbe|F('Gilligans_Sell')|F('Blood_Diamond')|F('Red_Dot_T1')|F('Parabolic_Top_Sell'))
    mab=(F('Fell_Below_20MA').astype(int)+F('Fell_Below_50MA').astype(int)+F('Fell_Below_200MA').astype(int)+F('Death_Cross').astype(int))>=1
    df['Combo_MABreakdown_Sell']=mab&(vc|F('MACD_Zero_Cross_Sell')|(F('Wide_Range_Bar')&(C<df['Open'])))&mbe
    df['Combo_VolSqueeze_Sell']=sq.shift(1).fillna(False)&(C<df['MA50'])&(F('BB_Squeeze_End_Bear')|(F('Wide_Range_Bar')&(C<df['Open'])))&vc&mbe
    gf=F('Gap_Up').shift(1).fillna(False)&(C<df['Open'])&(cbe|F('Gilligans_Sell'))
    df['Combo_GapFailure_Sell']=gf|(F('Gap_Down')&vc&(F('Fell_Below_50MA')|F('Fell_Below_200MA')))
    df['Combo_MF_Reversal_Sell']=F('MF_Cross_Bear')&(df['WT1']>-20)&(C<df['MA50'])&(cbe|tbe|vc)
    df['Combo_Ichimoku_Sell']=F('Kumo_Breakout_Bear')&(cbe|tbe|vc)&(cmf<-0.05)&(df['ADX']>20)
    asell=(df.get('Setup_Pressure_Sell',pd.Series(0,index=idx))>=5)
    df['Combo_Anticipation_Sell']=asell&sq&((cmf<-0.05)|mbe)&(F('WT_Convergence_Bear')|F('Momentum_Accel_Sell')|F('Setup_Squeeze_Bear'))

# ──────────────────────────────────────────
# 8-Layer 판단 엔진 (V12.0 — 압축)
# ──────────────────────────────────────────
def compute_trade_judgment(df):
    C,O,H,L,idx=df['Close'],df['Open'],df['High'],df['Low'],df.index
    rmfi=df['RSI_MFI']; vr=df['Volume']/(df['Volume'].rolling(50,min_periods=10).mean()+1e-10); atr=df['ATR']
    a200=C>df['MA200'];a50=C>df['MA50'];a20=C>df['MA20']
    b200=C<df['MA200'];b50=C<df['MA50']
    m50r=df['MA50']>df['MA50'].shift(5);m50f=df['MA50']<df['MA50'].shift(5)
    mh=df['MACD_Hist'];mhr=mh>mh.shift(1);mhf=mh<mh.shift(1)
    mg=df['MACD_Line']-df['MACD_Signal'];ma=mg>mg.shift(1);md=mg<mg.shift(1)
    rr=df['RSI']>df['RSI'].shift(1);rf=df['RSI']<df['RSI'].shift(1)
    sr=df['StochK']>df['StochK'].shift(1)
    wr=df['WT1']>df['WT1'].shift(1);wf=df['WT1']<df['WT1'].shift(1)
    obv=df['OBV'];obm=obv.rolling(20,min_periods=10).mean()
    oba=obv>obm;obb=obv<obm
    bv=df['Volume'].where(C>O,0);bev=df['Volume'].where(C<O,0)
    abv=bv.rolling(10,min_periods=5).mean();abev=bev.rolling(10,min_periods=5).mean()
    vbr=abv/(abev+1e-10); vo=df['VWAP_Osc']
    body=(C-O).abs();bar=body/(atr+1e-10)
    idt=b50|(df['WT1']<-20)|(df['RSI']<45); iut=a50|(df['WT1']>20)|(df['RSI']>55)
    wcu=df.get('WT_Up',pd.Series(False,index=idx))
    wcd=df.get('WT_Down',pd.Series(False,index=idx))
    sqo=df.get('Squeeze_On',pd.Series(False,index=idx));pb=df['Percent_B']
    kt=pd.concat([df.get('Ichimoku_SenkouA',pd.Series(0,index=idx)),df.get('Ichimoku_SenkouB',pd.Series(0,index=idx))],axis=1).max(axis=1)
    kbt=pd.concat([df.get('Ichimoku_SenkouA',pd.Series(0,index=idx)),df.get('Ichimoku_SenkouB',pd.Series(0,index=idx))],axis=1).min(axis=1)
    ak=C>kt;bk=C<kbt;cmf=df.get('CMF',pd.Series(0,index=idx))
    tka=df.get('Ichimoku_Tenkan',pd.Series(0,index=idx))>df.get('Ichimoku_Kijun',pd.Series(0,index=idx))
    tkb=df.get('Ichimoku_Tenkan',pd.Series(0,index=idx))<df.get('Ichimoku_Kijun',pd.Series(0,index=idx))
    nr7v=_sig_pts(df,'NR7',1);nr72v=_sig_pts(df,'NR7_2',1.5);cv=_sig_pts(df,'Calm_After_Storm',1)
    # BUY Layers
    bt=pd.Series(0.0,index=idx)
    bt+=np.where(a200&a50&a20,5,np.where(a200&a50,4,np.where(a200,2.5,np.where(a50,1.5,0))))
    bt+=np.where(df['MA50']>df['MA200'],1.5,0)+np.where(df['Plus_DI']>df['Minus_DI'],1,0)
    bt+=np.where(df['ST_Direction']==1,1,0)+np.where(a50&m50r,0.5,0)
    bt+=_sig_pts(df,'Cross_Above_50MA',1)+_sig_pts(df,'Cross_Above_200MA',1.5)+_sig_pts(df,'Golden_Cross',1.5)
    bt+=np.where(ak,1.5,0)+np.where(ak&tka,0.5,0)+np.where(b200&b50,-2,0)+np.where(df['ST_Direction']==-1,-0.5,0)
    df['BJ_Trend']=bt.clip(-2,JT.TREND_CAP)
    bm=pd.Series(0.0,index=idx)
    bmc=pd.Series(0.0,index=idx)
    for s,p in [('MACD_Cross_Buy',2.5),('MACD_Zero_Cross_Buy',2),('StochRSI_Cross_Buy',2),('ADX_Momentum_Buy',2),('VWAP_Bounce_Buy',1.5)]:
        bmc+=_sig_pts(df,s,p)
    bm+=bmc.clip(upper=JT.CROSS_SIGNAL_CAP)
    bm+=np.select([(mh>0)&mhr,(mh>0)&mhf,(mh<0)&mhr],[2,0.5,1.5],0)+np.where((mh>0)&ma,0.5,0)
    bm+=np.select([vo>3,vo>1,vo>0],[1.5,1,0.5],0)
    bm+=np.select([(df['RSI']<30)&rr,df['RSI']<30,(df['RSI']<45)&rr,(df['RSI']>70)&rf,(df['RSI']>70)&rr],[3,1.5,1,-1.5,-0.5],0)
    bm+=np.select([(df['StochK']<20)&sr,df['StochK']<20,(df['StochK']>80)&~sr],[2.5,1,-1],0)
    bm+=np.select([(df['WT1']<OS1)&(wcu|wr),df['WT1']<OS1,(df['WT1']<-20)&wr,(df['WT1']>OB1)&wf],[3,1,1,-1.5],0)
    df['BJ_Momentum']=bm.clip(-2,JT.MOMENTUM_CAP)
    bcc=[]
    for sn,bp_,tp in [('Morning_Star',2.5,3.5),('Bullish_Engulfing',2,3),('Hammer',1.5,2.5),('Outside_Bullish',1.5,2.5),('Doji_Bullish',0.5,1)]:
        raw=df.get(sn,pd.Series(False,index=idx)).fillna(False)
        if sn=='Bullish_Engulfing': pts=np.where(raw&idt&(bar>1),3.5,np.where(raw&idt,tp,np.where(raw&(bar>1),2.5,np.where(raw,bp_,0))))
        else: pts=np.where(raw&idt,tp,np.where(raw,bp_,0))
        bcc.append(pts)
    df['BJ_Candle']=pd.Series(np.stack(bcc).max(axis=0),index=idx).clip(upper=JT.CANDLE_CAP) if bcc else pd.Series(0.0,index=idx)
    bb=pd.Series(0.0,index=idx)+_sig_pts(df,'BB_Squeeze_End_Bull',3)+nr7v+nr72v+cv
    bb+=np.where(sqo&a50,1,0)+np.select([pb<0.05,pb<0.2,(pb>=0.4)&(pb<=0.6)&a50,pb>0.95],[2.5,1.5,0.5,-1.5],0)
    bb+=_sig_pts(df,'BB_Lower_Bounce',2)+np.where(df.get('BB_Lower_Break',pd.Series(False,index=idx)).fillna(False),-1,0)
    df['BJ_BB']=bb.clip(-1,JT.BB_CAP)
    bvol=pd.Series(0.0,index=idx)+_sig_pts(df,'Volume_Climax_Buy',3)+_sig_pts(df,'Pocket_Pivot',2)+_sig_pts(df,'OBV_Div_Buy',1.5)
    bvol+=np.where((vr>=3)&(C>O),2.5,np.where((vr>=1.5)&(C>O),1,0))
    bvol+=np.where(oba&(obv>obv.shift(5)),1.5,np.where(oba,0.5,0))+np.where(obb&(obv<obv.shift(5)),-1,0)
    bvol+=np.select([vbr>2,vbr>1.3,vbr<0.5],[1.5,0.5,-1],0)
    df['BJ_Volume']=bvol.clip(-1,JT.VOLUME_CAP)
    bmf=pd.Series(0.0,index=idx)+np.select([rmfi<-10,rmfi<-5,rmfi>10],[2,1,-0.5],0)
    if 'MF_Slope_5' in df.columns: bmf+=np.select([df['MF_Slope_5']>5,df['MF_Slope_5']>2,df['MF_Slope_5']>0,df['MF_Slope_5']<-5],[2,1.5,0.5,-1],0)
    if 'MF_Up_Streak' in df.columns: bmf+=np.select([df['MF_Up_Streak']>=5,df['MF_Up_Streak']>=3],[2,1],0)
    bmf+=_sig_pts(df,'MF_Cross_Bull',2)+_sig_pts(df,'MF_Bull_Div',2)+_sig_pts(df,'MF_Accel_Up',1)
    bmf+=np.where(cmf>0.15,1.5,np.where(cmf>0.05,0.5,np.where(cmf<-0.15,-1,0)))+_sig_pts(df,'CMF_Bull',1.5)
    df['BJ_MF']=bmf.clip(-1,JT.MF_CAP)
    bpat=pd.Series(0.0,index=idx)
    gold=_sig_pts(df,'Gold_Dot',4); gt1=np.where(gold==0,_sig_pts(df,'Green_Dot_T1',2.5),0)
    gt2=np.where((gold==0)&(gt1==0),_sig_pts(df,'Green_Dot_T2',2),0)
    bpat+=gold+gt1+gt2+np.where(gold==0,_sig_pts(df,'Bull_Divergence',2),0)
    for s,p in [('Pullback_123_Bull',2.5),('Setup_180_Bull',2),('Boomer_Buy',2),('Expansion_BO',3),('Gilligans_Buy',2.5),('Lizard_Bull',2),('NonADX_123_Bull',1.5),('EMA_Pullback_Buy',2),('Momentum_Ignition_Buy',3),('SuperTrend_Buy',2),('Gap_Up',1),('Gap_Down_Closed',1),('New_52W_High',2),('Blue_Diamond',2),('Hidden_Bull_Div',1.5),('Squeeze_Fire_Buy',2),('Parabolic_Bottom_Buy',3),('Pocket_Pivot',2),('Kumo_Breakout_Bull',2.5),('TK_Cross_Bull',1.5)]:
        bpat+=_sig_pts(df,s,p)
    for s,dp in [('Gold_Dot',2),('Green_Dot_T1',1),('Expansion_BO',1.5),('Momentum_Ignition_Buy',1.5),('Parabolic_Bottom_Buy',1.5),('Kumo_Breakout_Bull',1)]:
        if s in df.columns: bpat+=np.where(df[s].shift(1).fillna(False)&~df[s],dp*0.5,0)
    df['BJ_Pattern']=bpat.clip(upper=JT.PATTERN_CAP)
    ba=pd.Series(0.0,index=idx); sbuy=df.get('Setup_Pressure_Buy',pd.Series(0,index=idx))
    ca_=df.get('Composite_Accel',pd.Series(0,index=idx))
    ba+=np.where(sbuy>=8,3,np.where(sbuy>=5,2,np.where(sbuy>=3,1,0)))
    ba+=np.where(ca_>JT.ACCEL_STRONG,2.5,np.where(ca_>JT.ACCEL_MODERATE,1.5,np.where(ca_>0.5,0.5,0)))
    ba+=np.where(ca_<-JT.ACCEL_MODERATE,-1,0)+np.where(df.get('WT_Conv_Bull',pd.Series(False,index=idx)),2,0)
    ba+=_sig_pts(df,'Setup_Squeeze_Bull',1.5)+_sig_pts(df,'Momentum_Accel_Buy',2)+_sig_pts(df,'WT_Convergence_Bull',1.5)+_sig_pts(df,'Volume_Dry_Up',0.5)
    df['BJ_Anticipation']=ba.clip(-1,JT.ANTICIPATION_CAP)
    df['Buy_Total']=df['BJ_Trend']+df['BJ_Momentum']+df['BJ_Candle']+df['BJ_BB']+df['BJ_Volume']+df['BJ_MF']+df['BJ_Pattern']+df['BJ_Anticipation']
    # SELL Layers (mirror)
    st_=pd.Series(0.0,index=idx)
    st_+=np.where(b200&b50&(C<df['MA20']),5,np.where(b200&b50,4,np.where(b200,2.5,np.where(b50,1.5,0))))
    st_+=np.where(df['MA50']<df['MA200'],1.5,0)+np.where(df['Minus_DI']>df['Plus_DI'],1,0)
    st_+=np.where(df['ST_Direction']==-1,1,0)+np.where(b50&m50f,0.5,0)
    st_+=_sig_pts(df,'Fell_Below_50MA',1)+_sig_pts(df,'Fell_Below_200MA',1.5)+_sig_pts(df,'Death_Cross',1.5)
    st_+=np.where(bk,1.5,0)+np.where(bk&tkb,0.5,0)+np.where(a200&a50,-2,0)+np.where(df['ST_Direction']==1,-0.5,0)
    df['SJ_Trend']=st_.clip(-2,JT.TREND_CAP)
    sm=pd.Series(0.0,index=idx); smc=pd.Series(0.0,index=idx)
    for s,p in [('MACD_Cross_Sell',2.5),('MACD_Zero_Cross_Sell',2),('StochRSI_Cross_Sell',2),('ADX_Momentum_Sell',2),('VWAP_Reject_Sell',1.5)]:
        smc+=_sig_pts(df,s,p)
    sm+=smc.clip(upper=JT.CROSS_SIGNAL_CAP)
    sm+=np.select([(mh<0)&mhf,(mh<0)&mhr,(mh>0)&mhf],[2,0.5,1.5],0)+np.where((mh<0)&md,0.5,0)
    sm+=np.select([vo<-3,vo<-1,vo<0],[1.5,1,0.5],0)
    sm+=np.select([(df['RSI']>70)&rf,df['RSI']>70,(df['RSI']>55)&rf,(df['RSI']<30)&rr,(df['RSI']<30)&~rr],[3,1.5,1,-1.5,-0.5],0)
    sm+=np.select([(df['StochK']>80)&~sr,df['StochK']>80,(df['StochK']<20)&sr],[2.5,1,-1],0)
    sm+=np.select([(df['WT1']>OB1)&(wcd|wf),df['WT1']>OB1,(df['WT1']>20)&wf,(df['WT1']<OS1)&wr],[3,1,1,-1.5],0)
    df['SJ_Momentum']=sm.clip(-2,JT.MOMENTUM_CAP)
    scc=[]
    for sn,bp_,tp in [('Evening_Star',2.5,3.5),('Bearish_Engulfing',2,3),('Shooting_Star',1.5,2.5),('Outside_Bearish',1.5,2.5),('Doji_Bearish',0.5,1)]:
        raw=df.get(sn,pd.Series(False,index=idx)).fillna(False)
        if sn=='Bearish_Engulfing': pts=np.where(raw&iut&(bar>1),3.5,np.where(raw&iut,tp,np.where(raw&(bar>1),2.5,np.where(raw,bp_,0))))
        else: pts=np.where(raw&iut,tp,np.where(raw,bp_,0))
        scc.append(pts)
    df['SJ_Candle']=pd.Series(np.stack(scc).max(axis=0),index=idx).clip(upper=JT.CANDLE_CAP) if scc else pd.Series(0.0,index=idx)
    sb_=pd.Series(0.0,index=idx)+_sig_pts(df,'BB_Squeeze_End_Bear',3)+nr7v+nr72v+cv
    sb_+=np.where(sqo&b50,1,0)+np.select([pb>0.95,pb>0.8,(pb>=0.4)&(pb<=0.6)&b50,pb<0.05],[2.5,1.5,0.5,-1.5],0)
    sb_+=_sig_pts(df,'BB_Lower_Break',1.5)+np.where(df.get('BB_Upper_Break',pd.Series(False,index=idx)).fillna(False)&a200,-0.5,0)
    df['SJ_BB']=sb_.clip(-1,JT.BB_CAP)
    svol=pd.Series(0.0,index=idx)+_sig_pts(df,'Volume_Climax_Sell',3)+_sig_pts(df,'OBV_Div_Sell',1.5)
    svol+=np.where((vr>=3)&(C<O),2.5,np.where((vr>=1.5)&(C<O),1,0))
    svol+=np.where(obb&(obv<obv.shift(5)),1.5,np.where(obb,0.5,0))+np.where(oba&(obv>obv.shift(5)),-1,0)
    svol+=np.select([vbr<0.5,vbr<0.7,vbr>2],[1.5,0.5,-1],0)
    df['SJ_Volume']=svol.clip(-1,JT.VOLUME_CAP)
    smf=pd.Series(0.0,index=idx)+np.select([rmfi>10,rmfi>5,rmfi<-10],[2,1,-0.5],0)
    if 'MF_Slope_5' in df.columns: smf+=np.select([df['MF_Slope_5']<-5,df['MF_Slope_5']<-2,df['MF_Slope_5']<0,df['MF_Slope_5']>5],[2,1.5,0.5,-1],0)
    if 'MF_Dn_Streak' in df.columns: smf+=np.select([df['MF_Dn_Streak']>=5,df['MF_Dn_Streak']>=3],[2,1],0)
    smf+=_sig_pts(df,'MF_Cross_Bear',2)+_sig_pts(df,'MF_Bear_Div',2)+_sig_pts(df,'MF_Accel_Dn',1)
    smf+=np.where(cmf<-0.15,1.5,np.where(cmf<-0.05,0.5,np.where(cmf>0.15,-1,0)))+_sig_pts(df,'CMF_Bear',1.5)
    df['SJ_MF']=smf.clip(-1,JT.MF_CAP)
    spat=pd.Series(0.0,index=idx)
    blood=_sig_pts(df,'Blood_Diamond',4); rt1=np.where(blood==0,_sig_pts(df,'Red_Dot_T1',2.5),0)
    rt2=np.where((blood==0)&(rt1==0),_sig_pts(df,'Red_Dot_T2',2),0)
    spat+=blood+rt1+rt2+np.where(blood==0,_sig_pts(df,'Bear_Divergence',2),0)
    for s,p in [('Pullback_123_Bear',2.5),('Setup_180_Bear',2),('Boomer_Sell',2),('Expansion_BD',3),('Gilligans_Sell',2.5),('Lizard_Bear',2),('NonADX_123_Bear',1.5),('EMA_Pullback_Sell',2),('Momentum_Ignition_Sell',3),('SuperTrend_Sell',2),('Gap_Down',1),('Gap_Up_Closed',1),('New_52W_Low',2),('Red_Diamond',2),('Hidden_Bear_Div',1.5),('Squeeze_Fire_Sell',2),('Parabolic_Top_Sell',3),('Kumo_Breakout_Bear',2.5),('TK_Cross_Bear',1.5)]:
        spat+=_sig_pts(df,s,p)
    for s,dp in [('Blood_Diamond',2),('Red_Dot_T1',1),('Expansion_BD',1.5),('Momentum_Ignition_Sell',1.5),('Parabolic_Top_Sell',1.5),('Kumo_Breakout_Bear',1)]:
        if s in df.columns: spat+=np.where(df[s].shift(1).fillna(False)&~df[s],dp*0.5,0)
    df['SJ_Pattern']=spat.clip(upper=JT.PATTERN_CAP)
    sa=pd.Series(0.0,index=idx); ssell=df.get('Setup_Pressure_Sell',pd.Series(0,index=idx))
    sa+=np.where(ssell>=8,3,np.where(ssell>=5,2,np.where(ssell>=3,1,0)))
    sa+=np.where(ca_<-JT.ACCEL_STRONG,2.5,np.where(ca_<-JT.ACCEL_MODERATE,1.5,np.where(ca_<-0.5,0.5,0)))
    sa+=np.where(ca_>JT.ACCEL_MODERATE,-1,0)+np.where(df.get('WT_Conv_Bear',pd.Series(False,index=idx)),2,0)
    sa+=_sig_pts(df,'Setup_Squeeze_Bear',1.5)+_sig_pts(df,'Momentum_Accel_Sell',2)+_sig_pts(df,'WT_Convergence_Bear',1.5)+_sig_pts(df,'Volume_Dry_Up',0.5)
    df['SJ_Anticipation']=sa.clip(-1,JT.ANTICIPATION_CAP)
    df['Sell_Total']=df['SJ_Trend']+df['SJ_Momentum']+df['SJ_Candle']+df['SJ_BB']+df['SJ_Volume']+df['SJ_MF']+df['SJ_Pattern']+df['SJ_Anticipation']
    # Combo bonus
    detect_combos(df,vr)
    bcb=pd.Series(0.0,index=idx); scb=pd.Series(0.0,index=idx)
    for col,(name,d,tier) in COMBO_MAP.items():
        if col not in df.columns: continue
        bonus={1:JT.COMBO_TIER1_BONUS,2:JT.COMBO_TIER2_BONUS,3:JT.COMBO_TIER3_BONUS}[tier]
        if d=='buy': bcb+=np.where(df[col],bonus,0)
        else: scb+=np.where(df[col],bonus,0)
    df['Buy_Total']+=bcb; df['Sell_Total']+=scb
    lnb=['BJ_Trend','BJ_Momentum','BJ_Candle','BJ_BB','BJ_Volume','BJ_MF','BJ_Pattern','BJ_Anticipation']
    lns=['SJ_Trend','SJ_Momentum','SJ_Candle','SJ_BB','SJ_Volume','SJ_MF','SJ_Pattern','SJ_Anticipation']
    df['Buy_Active_Layers']=sum((df[n]>0).astype(int) for n in lnb)
    df['Sell_Active_Layers']=sum((df[n]>0).astype(int) for n in lns)
    # Final judgment
    j=np.full(len(df),'NEUTRAL',dtype=object); conf=np.zeros(len(df))
    btv,stv=df['Buy_Total'].values,df['Sell_Total'].values
    bav,sav=df['Buy_Active_Layers'].values,df['Sell_Active_Layers'].values
    ap=(df['ATR']/(df['Close']+1e-10)*100).values
    for i in range(len(df)):
        b,s,bl,sl=btv[i],stv[i],bav[i],sav[i]; diff=b-s; rat=b/(s+0.01); srat=s/(b+0.01)
        sc=JT.LOW_VOL_SCALE if ap[i]<2 else 1; ssc=sc*JT.SELL_ASYMMETRY
        if b>=JT.STRONG_BUY_SCORE*sc and bl>=JT.STRONG_BUY_LAYERS and rat>=JT.STRONG_BUY_RATIO and diff>=JT.STRONG_BUY_DIFF*sc:
            j[i]='STRONG_BUY'; conf[i]=min(90+(diff-JT.STRONG_BUY_DIFF)*2,99)
        elif b>=JT.BUY_SCORE*sc and bl>=JT.BUY_LAYERS and rat>=JT.BUY_RATIO and diff>=JT.BUY_DIFF*sc:
            j[i]='BUY'; conf[i]=min(60+(diff-JT.BUY_DIFF)*3,89)
        elif b>=JT.WATCH_BUY_SCORE*sc and bl>=JT.WATCH_LAYERS and diff>=JT.WATCH_DIFF*sc:
            j[i]='WATCH_BUY'; conf[i]=min(30+diff*3,59)
        elif s>=JT.STRONG_BUY_SCORE*ssc and sl>=JT.STRONG_BUY_LAYERS and srat>=1.5 and (s-b)>=8*sc:
            j[i]='STRONG_SELL'; conf[i]=min(90+((s-b)-8)*2,99)
        elif s>=JT.BUY_SCORE*ssc and sl>=JT.BUY_LAYERS and srat>=1.2 and (s-b)>=4*sc:
            j[i]='SELL'; conf[i]=min(60+((s-b)-4)*3,89)
        elif s>=JT.WATCH_BUY_SCORE*ssc and sl>=JT.WATCH_LAYERS and (s-b)>=1.5*sc:
            j[i]='WATCH_SELL'; conf[i]=min(30+(s-b)*3,59)
        elif b>=JT.MIXED_MIN*sc and s>=JT.MIXED_MIN*sc and abs(diff)<JT.MIXED_DIFF_MAX*sc:
            j[i]='MIXED'; conf[i]=max(20,50-abs(diff)*5)
        else: conf[i]=max(10,50-max(b,s))
    df['Trade_Judgment']=j; df['Judgment_Confidence']=np.clip(conf,0,99)
    return df

# ──────────────────────────────────────────
# 판단 상세 / Bias
# ──────────────────────────────────────────
def get_judgment_detail(row):
    ln=['Trend','Momentum','Candle','BB','Volume','MF','Pattern','Anticipation']
    bl={n:float(row.get(f'BJ_{n}',0)) for n in ln}
    sl={n:float(row.get(f'SJ_{n}',0)) for n in ln}
    combos=[{'name':name,'dir':d,'tier':t} for col,(name,d,t) in COMBO_MAP.items() if row.get(col,False)]
    # 스캐너 콤보도 수집
    scanner_active=[{'name':sc['name'],'kor':sc['kor'],'dir':sc['dir'],'tier':sc['tier'],'icon':sc['icon']}
                    for cn,sc in SCANNER_COMBOS.items() if row.get(cn,False)]
    return {'judgment':str(row.get('Trade_Judgment','NEUTRAL')),'confidence':float(row.get('Judgment_Confidence',0)),
            'buy_total':float(row.get('Buy_Total',0)),'sell_total':float(row.get('Sell_Total',0)),
            'buy_layers':bl,'sell_layers':sl,'buy_active':int(row.get('Buy_Active_Layers',0)),
            'sell_active':int(row.get('Sell_Active_Layers',0)),'active_combos':combos,
            'net':float(row.get('Buy_Total',0))-float(row.get('Sell_Total',0)),
            'setup_pressure_buy':float(row.get('Setup_Pressure_Buy',0)),
            'setup_pressure_sell':float(row.get('Setup_Pressure_Sell',0)),
            'composite_accel':float(row.get('Composite_Accel',0)),
            'scanner_combos':scanner_active}  # ★ 스캐너 콤보

def compute_bias(meta,htf1,htf2):
    sc=0.0; wt1=meta.get('wt1',0)
    if wt1<=-60: sc+=3
    elif wt1<=-53: sc+=2
    elif wt1<=-20: sc+=1
    elif wt1>=60: sc-=3
    elif wt1>=53: sc-=2
    elif wt1>=20: sc-=1
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
    if mf<-5: sc+=2
    elif mf<0: sc+=1
    elif mf>5: sc-=2
    elif mf>0: sc-=1
    stk=meta.get('stochk',50)
    if stk<20: sc+=1.5
    elif stk<35: sc+=0.5
    elif stk>80: sc-=1.5
    elif stk>65: sc-=0.5
    mhv=meta.get('macd_hist',0)
    if mhv>0.1: sc+=1
    elif mhv>0: sc+=0.5
    elif mhv<-0.1: sc-=1
    elif mhv<0: sc-=0.5
    sc+=1.5 if htf1 else -1.5; sc+=2 if htf2 else -2
    accel=meta.get('composite_accel',0)
    if accel>1.5: sc+=1
    elif accel<-1.5: sc-=1
    if sc>=9: return 'STRONG BUY',sc
    elif sc>=3.5: return 'BUY',sc
    elif sc>-3.5: return 'NEUTRAL',sc
    elif sc>-9: return 'SELL',sc
    else: return 'STRONG SELL',sc

def _build_judgment_hover(row,signals_dict):
    j=str(row.get('Trade_Judgment','NEUTRAL')); bt,st_=float(row.get('Buy_Total',0)),float(row.get('Sell_Total',0))
    cf=float(row.get('Judgment_Confidence',0)); net=bt-st_
    ico='🟢' if 'BUY' in j else ('🔴' if 'SELL' in j else '🟠')
    lines=[f"<b style='font-size:13px'>{ico} {j} ({cf:.0f}%)</b>",
           f"<b>BUY</b> {bt:.1f} vs <b>SELL</b> {st_:.1f} (NET: {net:+.1f})","─"*26]
    ln=['Trend','Momentum','Candle','BB','Volume','MF','Pattern','Anticipation']
    li=['📈','🔥','🕯️','📊','📦','💰','⭐','⏳']
    bp=[f"{ic}{n}:{float(row.get(f'BJ_{n}',0)):.1f}" for ic,n in zip(li,ln) if float(row.get(f'BJ_{n}',0))>0]
    sp=[f"{ic}{n}:{float(row.get(f'SJ_{n}',0)):.1f}" for ic,n in zip(li,ln) if float(row.get(f'SJ_{n}',0))>0]
    if bp: lines.append(f"<span style='color:#34D399'><b>▲</b> {' · '.join(bp)}</span>")
    if sp: lines.append(f"<span style='color:#F87171'><b>▼</b> {' · '.join(sp)}</span>")
    # ★ 스캐너 콤보 표시
    sc_active=[f"{sc['icon']} {sc['kor']}" for cn,sc in SCANNER_COMBOS.items() if row.get(cn,False)]
    if sc_active:
        lines.append("─"*26)
        lines.append(f"<b>🔍 Scanner:</b> {' / '.join(sc_active[:4])}")
    combos=[name for col,(name,_,_) in COMBO_MAP.items() if row.get(col,False)]
    if combos: lines.append(f"<b>🔥 콤보:</b> {' / '.join(combos[:3])}")
    return "<br>".join(lines)

# ══════════════════════════════════════════
#  PART 2/4 끝 — 다음: PART 3/4 차트+메타+프롬프트+분석
# ══════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
#  CipherX V12.0 + Scanner — PART 3/4
#  차트 빌더 (★ 스캐너 마커 통합) + 메타데이터 + 프롬프트
#  + 스피도미터 + 분석 로직 + ★ 멀티 티커 스캐너
# ══════════════════════════════════════════════════════════════

# ──────────────────────────────────────────
# 차트 유틸리티
# ──────────────────────────────────────────
def _hl(fig, mask, idx, fill, txt=None, row=1):
    d=mask.astype(int).diff().fillna(0)
    starts=idx[d==1].tolist(); ends=idx[d==-1].tolist()
    if len(mask)>0 and mask.iloc[0]: starts.insert(0,idx[0])
    if len(mask)>0 and mask.iloc[-1]: ends.append(idx[-1])
    for sv,ev in zip(starts,ends):
        kw=dict(x0=sv,x1=ev,fillcolor=fill,line_width=0,row=row,col=1)
        if txt: kw.update(annotation_text=txt,annotation_position="top left",
                          annotation_font_size=10,annotation_font_color="#FF5252")
        fig.add_vrect(**kw)


# ──────────────────────────────────────────
# ★ 스캐너 콤보 차트 마커
# ──────────────────────────────────────────
def add_scanner_markers_to_chart(fig, dc, row=1):
    """차트에 스캐너 콤보 마커를 별도 레이어로 추가"""
    for cn, cfg in SCANNER_COMBOS.items():
        if cn not in dc.columns: continue
        mask = dc[cn].fillna(False)
        if not mask.any(): continue
        sr = dc[mask]
        is_buy = cfg['dir'] == 'buy'
        y_vals = sr['Low'] - sr['ATR'] * 0.8 if is_buy else sr['High'] + sr['ATR'] * 0.8
        tier = cfg.get('tier', 2)
        sym = 'star-diamond' if tier == 1 else 'diamond'
        sz = 15 if tier == 1 else 11
        lw = 2 if tier == 1 else 1.5
        hovers = [f"<b>{cfg['icon']} {cfg['name']}</b><br>"
                  f"<span style='color:#94A3B8'>{cfg['desc']}</span><br>"
                  f"<span style='color:#CBD5E1'>{iv.strftime('%Y-%m-%d')}</span>"
                  for iv in sr.index]
        fig.add_trace(go.Scatter(
            x=sr.index, y=y_vals, mode='markers',
            marker=dict(symbol=sym, size=sz, color=cfg['color'],
                        line=dict(width=lw, color='#FFFFFF'), opacity=0.9),
            name=f"SC: {cfg['kor']}", text=hovers,
            hovertemplate="%{text}<extra></extra>",
            hoverlabel=dict(bgcolor='rgba(14,17,23,0.97)', bordercolor=cfg['color'],
                            font=dict(size=11, family='Pretendard', color='#FAFAFA')),
            legendgroup='scanner', legendgrouptitle_text='🔍 Scanner',
        ), row=row, col=1)


# ──────────────────────────────────────────
# 차트 빌더 (7행 + ★ 스캐너 마커)
# ──────────────────────────────────────────
def build_chart(dc, ticker, regime, shield):
    mac={5:"#ff9900",10:"#ffb74d",20:'#f1c40f',50:'#e74c3c',100:'#9b59b6',125:'#3498db',200:'#2ecc71'}
    fig=make_subplots(rows=7,cols=1,shared_xaxes=True,vertical_spacing=0.03,
        row_heights=[.32,.06,.12,.10,.12,.14,.14],
        subplot_titles=("","Volume","WaveTrend","Money Flow","MACD","Judgment","Anticipation"))
    # Row 1: Candlestick
    fig.add_trace(go.Candlestick(x=dc.index,open=dc['Open'],high=dc['High'],low=dc['Low'],close=dc['Close'],
        name="Price",increasing_line_color='#00E676',decreasing_line_color='#FF1744',
        increasing_fillcolor='rgba(0,230,118,0.8)',decreasing_fillcolor='rgba(255,23,68,0.8)',
        hovertemplate="O:%{open:.2f} H:%{high:.2f}<br>L:%{low:.2f} C:%{close:.2f}<extra></extra>"),row=1,col=1)
    for ma in [5,10,20,50,100,125,200]:
        fig.add_trace(go.Scatter(x=dc.index,y=dc[f'MA{ma}'],line=dict(color=mac[ma],width=1.2),
            name=f'{ma}MA',hovertemplate="%{y:.2f}"),row=1,col=1)
    for nm,cn,clr,dash in [('EMA8','EMA8','#00FFFF','dot'),('EMA21','EMA21','#FF69B4','dot')]:
        fig.add_trace(go.Scatter(x=dc.index,y=dc[cn],line=dict(color=clr,width=1.5,dash=dash),
            name=nm,hovertemplate="%{y:.2f}"),row=1,col=1)
    for mc,clr,nm in [(dc['ST_Direction']==1,'#00E676','ST▲'),(dc['ST_Direction']==-1,'#FF1744','ST▼')]:
        fig.add_trace(go.Scatter(x=dc.index,y=dc['SuperTrend'].where(mc),line=dict(color=clr,width=2),
            name=nm,connectgaps=False,hovertemplate="%{y:.2f}"),row=1,col=1)
    if 'Ichimoku_SenkouA' in dc.columns:
        fig.add_trace(go.Scatter(x=dc.index,y=dc['Ichimoku_SenkouA'],line=dict(color='rgba(0,230,118,0.3)',width=0.5),
            name='SenkouA',showlegend=False,hoverinfo='skip'),row=1,col=1)
        fig.add_trace(go.Scatter(x=dc.index,y=dc['Ichimoku_SenkouB'],line=dict(color='rgba(255,23,68,0.3)',width=0.5),
            name='SenkouB',fill='tonexty',fillcolor='rgba(99,102,241,0.04)',showlegend=False,hoverinfo='skip'),row=1,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['BB_Up'],line=dict(color='gray',width=1,dash='dot'),
        name='BB↑',hovertemplate="%{y:.2f}"),row=1,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['BB_Low'],line=dict(color='gray',width=1,dash='dot'),
        name='BB↓',fill='tonexty',fillcolor='rgba(128,128,128,0.07)',hovertemplate="%{y:.2f}"),row=1,col=1)
    for cn,clr,txt in [('Sell_Shield_Overridden','rgba(255,0,0,0.04)','🔓Sell'),
                        ('Buy_Shield_Overridden','rgba(0,255,0,0.04)','🔓Buy')]:
        om=dc.get(cn,pd.Series(False,index=dc.index))
        if om.any(): _hl(fig,om,dc.index,clr,txt,1)
    # Judgment markers
    if 'Trade_Judgment' in dc.columns:
        ej=st.session_state.get('enabled_judgments',set(JUDGMENT_MARKERS.keys()))
        for jg,jc in JUDGMENT_MARKERS.items():
            if jg not in ej: continue
            mask=dc['Trade_Judgment']==jg
            if not mask.any(): continue
            sr=dc[mask]
            yv=sr['Low']+sr['ATR']*jc['atr_mult'] if jc['base']=='Low' else sr['High']+sr['ATR']*jc['atr_mult']
            ht=[_build_judgment_hover(dc.loc[iv],ALL_CHART_SIGNALS) for iv in sr.index]
            fig.add_trace(go.Scatter(x=sr.index,y=yv,mode='markers',
                marker=dict(symbol=jc['symbol'],size=jc['size'],color=jc['color'],
                    line=dict(width=jc['line_width'],color=jc['line_color']),opacity=0.95),
                name=jc['label'],text=ht,hovertemplate="%{text}<extra></extra>",
                hoverlabel=dict(bgcolor='rgba(14,17,23,0.97)',bordercolor=jc['color'],
                    font=dict(size=11,family='Pretendard',color='#FAFAFA'),align='left')),row=1,col=1)
        for jn,fc in [('STRONG_BUY','rgba(0,230,118,0.05)'),('BUY','rgba(0,230,118,0.025)'),
                       ('STRONG_SELL','rgba(255,23,68,0.05)'),('SELL','rgba(255,23,68,0.025)')]:
            jm=dc['Trade_Judgment']==jn
            if jm.any(): _hl(fig,jm,dc.index,fc,None,1)
    # ★ 스캐너 콤보 마커
    if st.session_state.get('show_scanner_combos',True):
        add_scanner_markers_to_chart(fig,dc,row=1)
    # Row 2: Volume
    br=dc['Close']<dc['Open']
    fig.add_trace(go.Bar(x=dc.index,y=dc['Volume'],
        marker_color=np.where(br,'rgba(255,23,68,0.6)','rgba(0,230,118,0.6)').tolist(),
        name="Volume",opacity=0.8,hovertemplate="%{y:,.0f}"),row=2,col=1)
    vcm=dc.get('Volume_Climax_Buy',pd.Series(False))|dc.get('Volume_Climax_Sell',pd.Series(False))
    vcd=dc[vcm]
    if not vcd.empty:
        fig.add_trace(go.Bar(x=vcd.index,y=vcd['Volume'],marker_color='#FFD700',
            name="Vol Climax",opacity=0.9),row=2,col=1)
    # Row 3: WaveTrend
    fig.add_trace(go.Scatter(x=dc.index,y=dc['WT1'],line=dict(color='#00E676',width=2),name="WT1"),row=3,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['WT2'],line=dict(color='#FF1744',width=1.5,dash='dot'),name="WT2"),row=3,col=1)
    wd=dc['WT1']-dc['WT2']
    fig.add_trace(go.Bar(x=dc.index,y=wd,marker_color=np.where(wd>=0,'#00E676','#FF1744').tolist(),
        name="WT Hist",opacity=0.3),row=3,col=1)
    for lv,cc,d in [(OB2,'#ff3333','dash'),(OB1,'#ff3333','solid'),(0,'gray','dot'),
                     (OS1,'#00bfff','solid'),(OS2,'#00bfff','dash')]:
        fig.add_hline(y=lv,line_dash=d,line_color=cc,line_width=1,row=3,col=1)
    if 'Squeeze_On' in dc.columns: _hl(fig,dc['Squeeze_On'],dc.index,"rgba(255,255,0,0.05)",None,3)
    # Row 4: Money Flow
    rmfi=dc['RSI_MFI']
    fig.add_trace(go.Bar(x=dc.index,y=rmfi,marker_color=np.where(rmfi>=0,'#3ee145','#ff3d2e').tolist(),
        name="Money Flow",opacity=0.7),row=4,col=1)
    fig.add_hline(y=0,line_color="gray",line_width=1,row=4,col=1)
    if 'CMF' in dc.columns:
        fig.add_trace(go.Scatter(x=dc.index,y=dc['CMF']*50,line=dict(color='#FFD700',width=1,dash='dot'),
            name="CMF×50",opacity=0.6,customdata=dc['CMF'].values,
            hovertemplate="CMF: %{customdata:.3f}"),row=4,col=1)
    # Row 5: MACD
    fig.add_trace(go.Scatter(x=dc.index,y=dc['MACD_Line'],line=dict(color='#29B6F6',width=1.5),name="MACD"),row=5,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['MACD_Signal'],line=dict(color='#FFA726',width=1.5),name="Signal"),row=5,col=1)
    mhv=dc['MACD_Hist']
    fig.add_trace(go.Bar(x=dc.index,y=mhv,marker_color=np.where(mhv>=0,'#26A69A','#EF5350').tolist(),
        name="Hist",opacity=0.7),row=5,col=1)
    fig.add_hline(y=0,line_color="#444444",line_width=1,row=5,col=1)
    # Row 6: Judgment
    if 'Buy_Total' in dc.columns:
        nj=dc['Buy_Total']-dc['Sell_Total']
        colors=np.where(nj>=10,'#00E676',np.where(nj>=5,'#69F0AE',np.where(nj<=-10,'#FF1744',np.where(nj<=-5,'#FF5252','#FFC107'))))
        cfv=dc.get('Judgment_Confidence',pd.Series(0,index=dc.index)).values
        fig.add_trace(go.Bar(x=dc.index,y=nj,marker_color=colors.tolist(),name="Judgment NET",opacity=0.8,
            customdata=np.stack([dc['Buy_Total'].values,dc['Sell_Total'].values,
                dc.get('Trade_Judgment',pd.Series('N/A',index=dc.index)).values,cfv],axis=-1),
            hovertemplate="<b>%{customdata[2]}</b> (%{customdata[3]:.0f}%)<br>BUY:%{customdata[0]:.1f} SELL:%{customdata[1]:.1f}<br>NET:%{y:.1f}<extra></extra>"),row=6,col=1)
        for lv,cc,d in [(15,'#00E676','dash'),(-15,'#FF1744','dash'),(10,'#00E676','dot'),(-10,'#FF1744','dot'),
                         (5,'#69F0AE','dot'),(-5,'#FF5252','dot'),(0,'gray','solid')]:
            fig.add_hline(y=lv,line_dash=d,line_color=cc,line_width=1 if d=='solid' else .8,row=6,col=1)
    # Row 7: Anticipation
    sbuy=dc.get('Setup_Pressure_Buy',pd.Series(0,index=dc.index))
    ssell=dc.get('Setup_Pressure_Sell',pd.Series(0,index=dc.index))
    an=sbuy-ssell
    ac=np.where(an>=5,'#00E676',np.where(an>=2,'#69F0AE',np.where(an<=-5,'#FF1744',np.where(an<=-2,'#FF5252','#FFC107'))))
    fig.add_trace(go.Bar(x=dc.index,y=an,marker_color=ac.tolist(),name="Setup NET",opacity=0.7,
        customdata=np.stack([sbuy.values,ssell.values,dc.get('Composite_Accel',pd.Series(0,index=dc.index)).values],axis=-1),
        hovertemplate="BUY Setup:%{customdata[0]:.1f}<br>SELL Setup:%{customdata[1]:.1f}<br>Accel:%{customdata[2]:.2f}<extra></extra>"),row=7,col=1)
    ca=dc.get('Composite_Accel',pd.Series(0,index=dc.index))
    fig.add_trace(go.Scatter(x=dc.index,y=ca*3,line=dict(color='#FFD700',width=1.5,dash='dot'),
        name="Accel×3",opacity=0.6),row=7,col=1)
    fig.add_hline(y=0,line_color="gray",line_width=1,row=7,col=1)
    # Layout
    fig.update_layout(yaxis_title="Price",yaxis2_title="Vol",yaxis3_title="WT",yaxis4_title="MF",
        yaxis5_title="MACD",yaxis6_title="BUY−SELL",yaxis7_title="Setup",
        template="plotly_dark",paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=2,r=2,t=40,b=2),height=1400,showlegend=True,hovermode="x unified",
        hoverlabel=dict(bgcolor="rgba(14,17,23,0.95)",font_size=12,font_family="Pretendard"),
        legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="center",x=0.5,
            font=dict(size=9.5,color='#CCC'),bgcolor='rgba(0,0,0,0)'))
    for i in range(1,8):
        ya=f'yaxis{i}' if i>1 else 'yaxis'
        fig.update_layout(**{ya:dict(gridcolor='rgba(45,51,59,0.5)',zerolinecolor='rgba(60,63,70,0.6)',
            title_font=dict(size=11,color='#777'),tickfont=dict(size=10,color='#888'))})
    fig.update_xaxes(rangeslider_visible=False)
    hw=dc.index.dayofweek.isin([5,6]).any()
    rb=[dict(bounds=["sat","mon"])] if not hw else []
    fig.update_xaxes(showspikes=True,spikecolor="#667eea",spikemode="across",spikethickness=1,
        spikedash="dot",rangebreaks=rb,gridcolor='rgba(45,51,59,0.5)',tickfont=dict(size=10,color='#888'))
    fig.update_yaxes(showspikes=True,spikecolor="#667eea",spikemode="across",spikethickness=1,spikedash="dot")
    for ann in fig['layout']['annotations']: ann['font']=dict(size=12,color='#AAA',family='Pretendard')
    return fig


# ──────────────────────────────────────────
# 메타데이터 빌드
# ──────────────────────────────────────────
def build_metadata(dc, dv, ticker):
    lat,prev=dc.iloc[-1],dc.iloc[-2] if len(dc)>=2 else dc.iloc[-1]
    pc=lat['Close']-prev['Close']; pp=pc/(prev['Close']+1e-10)*100
    m4={k:float(lat[c]) for k,c in [('wt1','WT1'),('rsi','RSI'),('mfi','MFI'),
        ('mf_area','RSI_MFI'),('stochk','StochK')]}
    m4['composite_accel']=float(lat.get('Composite_Accel',0))
    h1=bool(lat.get('_HTF1_Bull',False)); h2=bool(lat.get('_HTF2_Bull',False))
    bias,bsc=compute_bias(m4,h1,h2)
    cf=float(dc['Confluence_Score'].iloc[-1])
    regime='STRONG BULL 🟢' if lat.get('Strong_Bull',False) else ('STRONG BEAR 🔴' if lat.get('Strong_Bear',False) else 'NEUTRAL ⚪')
    sp_list=[]
    for cond,lab in [('Parabolic_Blowoff','🌡️PARA TOP'),('ST_Bear_Override','📉ST BEAR'),('Parabolic_Bottom_Raw','🧊PARA BOT')]:
        if lat.get(cond,False): sp_list.append(lab)
    if not sp_list:
        if lat.get('Buy_Shield_Overridden',False): sp_list.append('🔓BUY OFF')
        if lat.get('Sell_Shield_Overridden',False): sp_list.append('🔓SELL OFF')
    shield_str=' + '.join(sp_list)
    sig_checks=[(k,v['icon'],v['label'],v['dir']) for k,v in ALL_CHART_SIGNALS.items()]
    recent=[]
    for ir,row in dc.tail(15).iterrows():
        ds=ir.strftime('%m/%d')
        for col,icon,lbl,side in sig_checks:
            if row.get(col,False): recent.append((icon,lbl,ds,side))
    jd=get_judgment_detail(lat)
    jh=[]
    for ir,row in dc.tail(5).iterrows():
        jhi=get_judgment_detail(row)
        jh.append({'date':ir.strftime('%m/%d'),'judgment':jhi['judgment'],'confidence':jhi['confidence'],
                   'buy_total':jhi['buy_total'],'sell_total':jhi['sell_total'],'combos':jhi['active_combos'],
                   'scanner_combos':jhi.get('scanner_combos',[])})
    return {
        'ticker':ticker.upper(),'price':lat['Close'],'price_change':pc,'price_change_pct':pp,
        'volume':lat['Volume'],'avg_volume':dc['Volume'].rolling(20).mean().iloc[-1],
        'wt1':float(lat['WT1']),'wt2':float(lat['WT2']),'rsi':float(lat['RSI']),'mfi':float(lat['MFI']),
        'stochk':float(lat['StochK']),'stochd':float(lat['StochD']),
        'vwap_osc':float(lat['VWAP_Osc']),'mf_area':float(lat['RSI_MFI']),
        'atr':float(lat['ATR']),'atr_pct':float(lat['ATR'])/(float(lat['Close'])+1e-10)*100,
        'adx':float(lat['ADX']),'plus_di':float(lat['Plus_DI']),'minus_di':float(lat['Minus_DI']),
        'overall_bias':bias,'bias_score':bsc,'confluence_score':cf,
        'recent_signals':recent,'last_date':dc.index[-1].strftime('%Y-%m-%d'),
        'buy_proximity':float(lat['Buy_Proximity']),'sell_proximity':float(lat['Sell_Proximity']),
        'squeeze_on':bool(lat.get('Squeeze_On',False)),'trend_regime':regime,'shield_status':shield_str,
        'supertrend_dir':int(lat.get('ST_Direction',0)),'supertrend_val':float(lat.get('SuperTrend',0)),
        'ema8':float(lat.get('EMA8',0)),'ema21':float(lat.get('EMA21',0)),
        'bb_up':float(lat.get('BB_Up',0)),'bb_low':float(lat.get('BB_Low',0)),
        'ma50':float(lat.get('MA50',0)),'ma200':float(lat.get('MA200',0)),
        'macd_line':float(lat.get('MACD_Line',0)),'macd_signal':float(lat.get('MACD_Signal',0)),
        'macd_hist':float(lat.get('MACD_Hist',0)),'judgment_detail':jd,'judgment_history':jh,
        'cmf':float(lat.get('CMF',0)),'ichimoku_tenkan':float(lat.get('Ichimoku_Tenkan',0)),
        'ichimoku_kijun':float(lat.get('Ichimoku_Kijun',0)),
        'composite_accel':float(lat.get('Composite_Accel',0)),
        'setup_pressure_buy':float(lat.get('Setup_Pressure_Buy',0)),
        'setup_pressure_sell':float(lat.get('Setup_Pressure_Sell',0)),
        'wt_conv_speed':float(lat.get('WT_Conv_Speed',0)),'rsi_accel':float(lat.get('RSI_Accel',0)),
    },regime,shield_str


# ──────────────────────────────────────────
# 프롬프트 빌더
# ──────────────────────────────────────────
def build_prompt_text(dc, meta):
    lat=dc.iloc[-1]; rd=dc.tail(60)
    ps=", ".join([f"'{d.strftime('%Y-%m-%d')}:{r['Close']:.2f}'" for d,r in rd.iterrows()])
    sl=[]
    for ir,row in dc.tail(30).iterrows():
        dd=ir.strftime('%Y-%m-%d')
        for k,v in ALL_CHART_SIGNALS.items():
            if row.get(k,False): sl.append(f"{v['icon']} {v['label']} {dd}")
        # ★ 스캐너 콤보도 포함
        for cn,sc in SCANNER_COMBOS.items():
            if row.get(cn,False): sl.append(f"🔍 {sc['kor']} {dd}")
    st_text="\n".join(sl) if sl else "최근 30일 내 시그널 없음"
    bp,sp=meta['buy_proximity'],meta['sell_proximity']
    prox=f"BuyProx={bp:.0f}%,SellProx={sp:.0f}%"
    if bp>=60: prox+=" ⚠️매수임박"
    if sp>=60: prox+=" ⚠️매도임박"
    sq="SqON" if meta['squeeze_on'] else "SqOFF"
    std=f"BULL▲({meta['supertrend_val']:.2f})" if meta['supertrend_dir']==1 else f"BEAR▼({meta['supertrend_val']:.2f})"
    shd=f"Shield:{meta['shield_status']}" if meta['shield_status'] else "Shield:NONE"
    vol=meta.get('volume',0); avg_vol=meta.get('avg_volume',1)
    vol_ratio=vol/avg_vol if avg_vol else 0
    antic_str=f"MomAccel={meta.get('composite_accel',0):.2f},SetupBuy={meta.get('setup_pressure_buy',0):.1f},SetupSell={meta.get('setup_pressure_sell',0):.1f}"
    inds=(f"Vol={vol:,.0f}({vol_ratio:.1f}x),WT1={lat['WT1']:.1f},WT2={lat['WT2']:.1f},"
        f"RSI={lat['RSI']:.1f},MFI={lat['MFI']:.1f},StK={lat['StochK']:.1f},"
        f"VWAP={lat['VWAP_Osc']:.2f},MF={lat['RSI_MFI']:.1f},ADX={lat['ADX']:.1f},"
        f"+DI={lat['Plus_DI']:.1f},-DI={lat['Minus_DI']:.1f},ST={std},"
        f"BB=[{meta['bb_up']:.2f}/{meta['bb_low']:.2f}],%B={lat.get('Percent_B',0):.2f},"
        f"M50={meta['ma50']:.2f},M200={meta['ma200']:.2f},"
        f"MACD={meta['macd_line']:.3f}/{meta['macd_signal']:.3f} H={meta['macd_hist']:.3f},"
        f"Ichimoku=[T:{meta.get('ichimoku_tenkan',0):.2f}/K:{meta.get('ichimoku_kijun',0):.2f}],"
        f"CMF={meta.get('cmf',0):.3f},"
        f"Conf={meta['confluence_score']:.1f},Bias={meta['overall_bias']}({meta['bias_score']:.1f}),"
        f"Trend={meta['trend_regime']},{shd},{prox},{sq}")
    jd=meta.get('judgment_detail',{})
    j_txt=""
    if jd:
        j_txt=f"\n\n📌 [멀티 시그널 매매 판단]\n"
        j_txt+=f"  최종판단: {jd.get('judgment','NEUTRAL')} (확신도: {jd.get('confidence',0):.0f}%)\n"
        j_txt+=f"  BUY: {jd.get('buy_total',0):.1f} ({jd.get('buy_active',0)}/{NUM_LAYERS}층) / SELL: {jd.get('sell_total',0):.1f} ({jd.get('sell_active',0)}/{NUM_LAYERS}층)\n"
        combos=jd.get('active_combos',[])
        combo_str = ', '.join(c['name'] + '(T' + str(c.get('tier', 2)) + ')' for c in combos) if combos else '없음'
        j_txt += f"  콤보: {combo_str}\n"
        sc_combos=jd.get('scanner_combos',[])
        if sc_combos: j_txt+=f"  🔍 스캐너: {', '.join(c['kor'] for c in sc_combos)}\n"
        jh_list=meta.get('judgment_history',[])
        if jh_list:
            j_txt+="  5일: "+" → ".join(f"{d['date']}:{d['judgment']}({d.get('confidence',0):.0f}%)" for d in jh_list)+"\n"
    antic_txt=f"\n\n📌 [선행 지표]\n  {antic_str}\n"
    acv=meta.get('composite_accel',0)
    if acv>JT.ACCEL_STRONG: antic_txt+="  ⚡ 강한 상승 가속\n"
    elif acv>JT.ACCEL_MODERATE: antic_txt+="  📈 상승 가속\n"
    elif acv<-JT.ACCEL_STRONG: antic_txt+="  ⚡ 강한 하락 가속\n"
    elif acv<-JT.ACCEL_MODERATE: antic_txt+="  📉 하락 가속\n"
    return f"{ps}\n\n📌 [지표 요약]\n{inds}\n\n📌 [최근 시그널]\n{st_text}{j_txt}{antic_txt}"


def build_ai_prompt(ticker, phist, fundamentals):
    return f"""━━━━━━━━━━━━━
【 🎯 Role 】 월스트리트 20년+ 퀀트 펀드 매니저. 냉철한 기술 분석.
━━━━━━━━━━━━━
【 ✍️ Rules 】
1. 객관적·확신에 찬 어조 2. ATR 기반 손절/목표가 3. 시스템 크로스체크
4. 매물대 기반 지지/저항 5. 확률적 시나리오 6. 환각 금지 7. 선행 지표 활용
━━━━━━━━━━━━━
【 📥 Data 】 [{ticker}]
{phist}

📌 [펀더멘탈] {fundamentals}
━━━━━━━━━━━━━
【 📄 Output 】
# 🚦 {ticker} 심층 퀀트 리포트
[🔵/🔴/🟠] 핵심 요약 1줄

### 📊 시장 심리 (3~4문장)
### ⚖️ 시스템 스코어 검증 (판단+확신도+콤보+스캐너콤보)
### ⏳ 선행 지표 (가속도+셋업+WT수렴)
### 📈 기술적 심층 (RSI/MACD/ADX/CMF/Ichimoku)
### 📉 공매도 현황
### 주가변동이유 (뉴스/공시/매크로)
### 🔮 시나리오 (🔵긍정 __% / 🟠베이스 __% / 🔴리스크 __%)
**ATR 기반 전략:** R/R / 공격적·보수적 진입 / 손절 / 분할매도 / 트레일링
### 결론 + 익일 예측 + GRADE
"""


# ──────────────────────────────────────────
# 분석 통합 로직
# ──────────────────────────────────────────
def analyze(ticker, chart_days=252, refresh=False):
    try:
        ts=int(time.time()) if refresh else None
        df=compute_and_cache(ticker,ts)
        if df is None or df.empty: return None,"주가 데이터를 불러올 수 없습니다.",None
        if len(df)<50: return None,f"데이터 부족 ({len(df)}일, 최소 50일 필요)",None
        dv=df.dropna(subset=['WT1','WT2']); dc=dv.tail(chart_days).copy()
        if dc.empty: return None,"차트 데이터 부족",None
        meta,regime,shield=build_metadata(dc,dv,ticker)
        fig=build_chart(dc,ticker,regime,shield)
        return fig,build_prompt_text(dc,meta),meta
    except Exception as e:
        import traceback; print(f"[CipherX ERROR] {ticker}: {traceback.format_exc()}")
        return None,f"로딩 실패: {type(e).__name__}: {e}",None


# ──────────────────────────────────────────
# 스피도미터 게이지 (3열)
# ──────────────────────────────────────────
def build_speedometer_gauges(meta):
    cs=meta.get('confluence_score',0); bs=meta.get('bias_score',0); bl=meta.get('overall_bias','NEUTRAL')
    an=meta.get('setup_pressure_buy',0)-meta.get('setup_pressure_sell',0)
    cc='#34D399' if cs>=3.5 else ('#F87171' if cs<=-3.5 else '#FCD34D')
    bcm={'STRONG BUY':'#34D399','BUY':'#6EE7B7','STRONG SELL':'#F87171','SELL':'#FCA5A5','NEUTRAL':'#FCD34D'}
    bc=bcm.get(bl,'#FCD34D'); ac='#34D399' if an>3 else ('#F87171' if an<-3 else '#FCD34D')
    fig=make_subplots(rows=1,cols=3,specs=[[{"type":"indicator"}]*3],horizontal_spacing=0.06)
    for i,(val,title,color,rng) in enumerate([
        (cs,"🔥 Confluence",cc,[-10,10]),(bs,"🧭 Bias",bc,[-13,13]),(an,"⏳ Anticipation",ac,[-12,12])],1):
        fig.add_trace(go.Indicator(mode="gauge+number",value=val,
            number=dict(font=dict(size=24,color="#F8FAFC"),valueformat="+.1f" if i==3 else ".1f",
                        suffix=f" {bl}" if i==2 else ""),
            title=dict(text=f"<b>{title}</b>",font=dict(size=11,color="#94A3B8")),
            gauge=dict(axis=dict(range=rng,tickfont=dict(size=9,color="#64748B")),
                bar=dict(color=color,thickness=0.3),bgcolor="rgba(15,19,32,0.9)",
                borderwidth=1,bordercolor="#1E293B",
                threshold=dict(line=dict(color="#F8FAFC",width=3),thickness=0.8,value=val))),row=1,col=i)
    fig.update_layout(template="plotly_dark",paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",height=210,margin=dict(l=15,r=15,t=50,b=10),
        font=dict(family="Pretendard"))
    return fig


# ──────────────────────────────────────────
# ★ 멀티 티커 스캐너
# ──────────────────────────────────────────
@st.cache_data(ttl=600, show_spinner=False)
def scan_ticker(ticker, _ts=None):
    """단일 티커 스캔 → 활성 스캐너 콤보 반환"""
    try:
        df=compute_and_cache(ticker,_ts)
        if df is None or len(df)<50: return None
        lat=df.iloc[-1]
        active=[]
        for cn,cfg in SCANNER_COMBOS.items():
            if cn not in df.columns: continue
            rec=df[cn].tail(3)
            if rec.any():
                ld=rec[rec].index[-1]; da=(df.index[-1]-ld).days
                active.append({**cfg,'days_ago':da,'date':ld.strftime('%m/%d')})
        if not active: return None
        jd=get_judgment_detail(lat) if 'Trade_Judgment' in df.columns else {}
        prev=df.iloc[-2]['Close'] if len(df)>=2 else lat['Close']
        return {'ticker':ticker.upper(),'price':float(lat['Close']),
                'change_pct':float((lat['Close']-prev)/prev*100),
                'volume_ratio':float(lat['Volume']/(df['Volume'].rolling(50,min_periods=10).mean().iloc[-1]+1e-10)),
                'judgment':jd.get('judgment','N/A'),'confidence':jd.get('confidence',0),
                'active_combos':active,
                'buy_combos':[c for c in active if c['dir']=='buy'],
                'sell_combos':[c for c in active if c['dir']=='sell'],
                'wt1':float(lat.get('WT1',0)),'rsi':float(lat.get('RSI',50))}
    except: return None


def scan_multiple_tickers(tickers, progress_cb=None):
    results=[]
    for i,t in enumerate(tickers):
        if progress_cb: progress_cb(i/len(tickers),f"🔍 {t} 스캔 중... ({i+1}/{len(tickers)})")
        r=scan_ticker(t)
        if r: results.append(r)
    results.sort(key=lambda x:(-sum(1 for c in x['active_combos'] if c['tier']==1),-len(x['active_combos'])))
    return results


def render_scanner_page():
    """멀티 티커 스캐너 전용 페이지"""
    st.markdown("## 🔍 CipherX Custom Scanner")
    st.markdown("<p style='color:#94A3B8;font-size:.85rem'>고승률 시그널 콤보 20종 · 멀티 티커 실시간 스캔</p>",
                unsafe_allow_html=True)
    # 워치리스트 선택
    st.markdown("#### 📋 워치리스트")
    wl_tabs=st.tabs(list(DEFAULT_WATCHLIST.keys())+['✏️ 커스텀'])
    selected=[]
    for i,(wl_name,tickers) in enumerate(DEFAULT_WATCHLIST.items()):
        with wl_tabs[i]:
            cols=st.columns(5)
            for j,t in enumerate(tickers):
                with cols[j%5]:
                    if st.checkbox(t,value=True,key=f"wl_{wl_name}_{t}"):
                        if t not in selected: selected.append(t)
    with wl_tabs[-1]:
        ci=st.text_input("티커 입력 (쉼표 구분)",placeholder="NVDA, TSLA, ...",key="custom_wl")
        if ci:
            for t in ci.split(','):
                t=t.strip().upper()
                if t and t not in selected: selected.append(t)
    st.caption(f"선택: {len(selected)}개")
    fc1,fc2=st.columns(2)
    with fc1: dir_f=st.selectbox("방향",['전체','매수만','매도만'],key="sc_dir")
    with fc2: tier_f=st.selectbox("등급",['전체','Tier 1만','Tier 2만'],key="sc_tier")
    if st.button("🚀 스캔 시작",type="primary",use_container_width=True):
        if not selected: st.warning("종목을 선택해주세요."); return
        pb=st.progress(0,text="스캔 준비 중...")
        results=scan_multiple_tickers(selected,lambda p,t:pb.progress(p,text=t))
        pb.progress(1.0,text=f"✅ {len(results)}개 종목에서 콤보 발견!")
        time.sleep(0.3); pb.empty()
        # 필터
        if dir_f=='매수만': results=[r for r in results if r['buy_combos']]
        elif dir_f=='매도만': results=[r for r in results if r['sell_combos']]
        if tier_f=='Tier 1만': results=[r for r in results if any(c['tier']==1 for c in r['active_combos'])]
        elif tier_f=='Tier 2만': results=[r for r in results if any(c['tier']==2 for c in r['active_combos'])]
        if not results: st.info("🔍 조건에 맞는 콤보 없음"); return
        st.markdown(f"### 📊 스캔 결과: {len(results)}개 종목")
        for r in results:
            t=r['ticker']; chg=r['change_pct']; cc='#34D399' if chg>=0 else '#F87171'
            ci='▲' if chg>=0 else '▼'
            t1=any(c['tier']==1 for c in r['active_combos'])
            bc=f"border-color:#FFD700;box-shadow:0 0 15px rgba(255,215,0,0.15)" if t1 else ""
            ch=""
            for c in r['active_combos']:
                dc2='#34D399' if c['dir']=='buy' else '#F87171'
                ts2='⭐'*(4-c['tier'])
                ch+=f"<div style='display:flex;align-items:center;gap:8px;padding:3px 0;border-bottom:1px solid rgba(255,255,255,0.03)'>"
                ch+=f"<span style='color:{dc2}'>●</span><span style='color:#E8ECF1;font-weight:600;flex:1'>{c['icon']} {c['kor']}</span>"
                ch+=f"<span style='font-size:.7rem'>{ts2}</span><span style='color:#64748B;font-size:.7rem'>{c['date']}</span></div>"
            jl=r.get('judgment','N/A'); jcf=r.get('confidence',0)
            jcls='ind-bullish' if 'BUY' in jl else ('ind-bearish' if 'SELL' in jl else 'ind-neutral')
            st.markdown(f"""<div class="scanner-card" style="{bc}">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                    <div><span style="color:#A5B4FC;font-weight:800;font-size:1.2rem">{t}</span>
                        <span style="color:#64748B;font-size:.85rem;margin-left:10px">${r['price']:.2f}</span>
                        <span style="color:{cc};font-size:.85rem;margin-left:6px;font-weight:600">{ci}{abs(chg):.1f}%</span></div>
                    <div style="display:flex;gap:8px;align-items:center">
                        <span class="indicator-mini {jcls}" style="font-size:.75rem">{jl} {jcf:.0f}%</span>
                        <span style="color:#FCD34D;font-size:.8rem;font-weight:600">{len(r['buy_combos'])}B/{len(r['sell_combos'])}S</span></div>
                </div><div>{ch}</div></div>""",unsafe_allow_html=True)
            if st.button(f"📊 {t} 상세 분석",key=f"scan_{t}",use_container_width=True):
                st.session_state['quick_ticker']=t


# ──────────────────────────────────────────
# ★ 개별 종목 스캐너 탭
# ──────────────────────────────────────────
def render_scanner_tab(m):
    """개별 종목의 스캐너 콤보 결과 표시"""
    ticker=m['ticker']; jd=m.get('judgment_detail',{})
    sc_combos=jd.get('scanner_combos',[])
    st.markdown(f"### 🔍 {ticker} 스캐너 콤보")
    if not sc_combos:
        st.info("최근 활성 스캐너 콤보 없음")
        with st.expander("📋 사용 가능한 콤보 목록 (20종)",expanded=False):
            for cn,cfg in SCANNER_COMBOS.items():
                di='🟢' if cfg['dir']=='buy' else '🔴'
                ts='⭐'*(4-cfg['tier'])
                st.markdown(f"<div style='display:flex;align-items:center;gap:10px;padding:5px 0;"
                    f"border-bottom:1px solid rgba(255,255,255,0.03)'>"
                    f"<span>{di} {cfg['icon']}</span>"
                    f"<span style='color:#E8ECF1;font-weight:600;flex:1'>{cfg['kor']}</span>"
                    f"<span style='color:#94A3B8;font-size:.8rem;flex:2'>{cfg['desc']}</span>"
                    f"<span>{ts}</span></div>",unsafe_allow_html=True)
        return
    buy_sc=[c for c in sc_combos if c['dir']=='buy']
    sell_sc=[c for c in sc_combos if c['dir']=='sell']
    if buy_sc:
        st.markdown("#### 🟢 매수 콤보")
        for c in buy_sc:
            ts='⭐'*(4-c['tier'])
            st.markdown(f"""<div class="combo-card combo-buy">
                <div style="display:flex;align-items:center;gap:10px;flex:1">
                    <span style="font-size:1.2rem">{c['icon']}</span>
                    <span style="color:#E8ECF1;font-weight:700">{c['kor']}</span>
                </div><span>{ts}</span></div>""",unsafe_allow_html=True)
    if sell_sc:
        st.markdown("#### 🔴 매도 콤보")
        for c in sell_sc:
            ts='⭐'*(4-c['tier'])
            st.markdown(f"""<div class="combo-card combo-sell">
                <div style="display:flex;align-items:center;gap:10px;flex:1">
                    <span style="font-size:1.2rem">{c['icon']}</span>
                    <span style="color:#E8ECF1;font-weight:700">{c['kor']}</span>
                </div><span>{ts}</span></div>""",unsafe_allow_html=True)
    # 콤보 설명
    with st.expander("📋 전체 콤보 목록",expanded=False):
        for cn,cfg in SCANNER_COMBOS.items():
            di='🟢' if cfg['dir']=='buy' else '🔴'
            is_active=any(c['kor']==cfg['kor'] for c in sc_combos)
            bg='rgba(99,102,241,.08)' if is_active else 'transparent'
            badge='<span style="color:#A5B4FC;font-weight:700">✅</span>' if is_active else ''
            st.markdown(f"<div style='display:flex;align-items:center;gap:8px;padding:5px 8px;"
                f"border-radius:6px;background:{bg};margin:2px 0'>"
                f"<span>{di} {cfg['icon']}</span>"
                f"<span style='color:#E8ECF1;font-weight:600;flex:1'>{cfg['kor']}</span>"
                f"<span style='color:#64748B;font-size:.75rem;flex:2'>{cfg['desc']}</span>"
                f"{badge}</div>",unsafe_allow_html=True)


# ──────────────────────────────────────────
# Anticipation 탭
# ──────────────────────────────────────────
def render_anticipation_tab(m):
    jd=m.get('judgment_detail',{}); accel=m.get('composite_accel',0)
    sb_v=m.get('setup_pressure_buy',0); ss_v=m.get('setup_pressure_sell',0)
    wt_conv=m.get('wt_conv_speed',0); wt1=m.get('wt1',0); wt2=m.get('wt2',0); wt_gap=abs(wt1-wt2)
    st.markdown("### ⏳ 선행 지표 분석")
    # 가속도
    if accel>JT.ACCEL_STRONG: as_='🟢🟢 강한 상승 가속'; ab='rgba(16,185,129,.08)'
    elif accel>JT.ACCEL_MODERATE: as_='🟢 상승 가속'; ab='rgba(16,185,129,.05)'
    elif accel>-JT.ACCEL_MODERATE: as_='⚪ 중립'; ab='rgba(128,128,128,.03)'
    elif accel>-JT.ACCEL_STRONG: as_='🔴 하락 가속'; ab='rgba(239,68,68,.05)'
    else: as_='🔴🔴 강한 하락 가속'; ab='rgba(239,68,68,.08)'
    st.markdown(f"""<div style="background:{ab};border-radius:12px;padding:14px 18px;margin:8px 0;
        border:1px solid rgba(255,255,255,0.06)">
        <div style="display:flex;justify-content:space-between;align-items:center">
            <span style="color:#E8ECF1;font-weight:700">{as_}</span>
            <span style="color:#A5B4FC;font-weight:800;font-size:1.2rem">{accel:+.2f}</span></div>
    </div>""",unsafe_allow_html=True)
    ac1,ac2=st.columns(2)
    with ac1: st.metric("RSI 가속도",f"{m.get('rsi_accel',0):+.1f}")
    with ac2: st.metric("MACD Hist",f"{m.get('macd_hist',0):+.3f}")
    # 셋업
    st.markdown("#### 📊 셋업 축적")
    sc1,sc2=st.columns(2)
    with sc1:
        pct=min(sb_v/12*100,100)
        st.markdown(f"""<div style="background:rgba(16,185,129,.04);border-radius:10px;padding:14px;
            border:1px solid rgba(16,185,129,.15)">
            <p style="color:#34D399;font-weight:700;font-size:.85rem;margin:0">▲ BUY 셋업</p>
            <p style="color:#E8ECF1;font-weight:800;font-size:1.5rem;margin:4px 0">{sb_v:.1f}</p>
            <div style="height:8px;background:#151921;border-radius:4px;overflow:hidden">
                <div style="width:{pct}%;height:8px;background:#34D399;border-radius:4px"></div></div>
        </div>""",unsafe_allow_html=True)
    with sc2:
        pct=min(ss_v/12*100,100)
        st.markdown(f"""<div style="background:rgba(239,68,68,.04);border-radius:10px;padding:14px;
            border:1px solid rgba(239,68,68,.15)">
            <p style="color:#F87171;font-weight:700;font-size:.85rem;margin:0">▼ SELL 셋업</p>
            <p style="color:#E8ECF1;font-weight:800;font-size:1.5rem;margin:4px 0">{ss_v:.1f}</p>
            <div style="height:8px;background:#151921;border-radius:4px;overflow:hidden">
                <div style="width:{pct}%;height:8px;background:#F87171;border-radius:4px"></div></div>
        </div>""",unsafe_allow_html=True)
    # WT 수렴
    st.markdown("#### 🔀 WT 수렴")
    wc1,wc2,wc3=st.columns(3)
    with wc1: st.metric("WT 갭",f"{wt_gap:.1f}",delta=f"{'수렴' if wt_conv>0 else '발산'} {wt_conv:.1f}")
    with wc2:
        wd="아래→위(매수)" if wt1<wt2 else "위→아래(매도)"
        st.metric("방향",wd[:6])
    with wc3:
        ce=f"~{max(1,int(wt_gap/max(wt_conv,0.5)))}봉" if wt_conv>JT.CONVERGENCE_SLOW else "미정"
        st.metric("교차 예상",ce)


# ══════════════════════════════════════════
#  PART 3/4 끝 — 다음: PART 4/4 UI 렌더 + 사이드바 + 챗
# ══════════════════════════════════════════

# ══════════════════════════════════════════════════════════════
#  CipherX V12.0 + Scanner — PART 4/4
#  UI 렌더 + 사이드바 + 세션 관리 + 챗 인터페이스
#  ★ 스캐너 탭/페이지 통합, 6탭 구조
# ══════════════════════════════════════════════════════════════


# ──────────────────────────────────────────
# 매매 판단 UI (8-Layer + 확신도 + ★ 스캐너 콤보)
# ──────────────────────────────────────────
def render_judgment(meta):
    jd=meta.get('judgment_detail')
    if not jd: st.info("매매 판단 데이터가 없습니다."); return
    judgment=jd['judgment']; buy_t=jd['buy_total']; sell_t=jd['sell_total']
    net=buy_t-sell_t; confidence=jd.get('confidence',0)
    if 'BUY' in judgment: card_cls='judgment-card-buy'
    elif 'SELL' in judgment: card_cls='judgment-card-sell'
    else: card_cls='judgment-card-neutral'
    j_label,j_color,_=JUDGMENT_CONFIG.get(judgment,('⚪ NEUTRAL','#64748B',''))
    net_color='#34D399' if net>0 else ('#F87171' if net<0 else '#FCD34D')
    conf_bar_color=j_color if confidence>=60 else ('#FCD34D' if confidence>=30 else '#475569')
    st.markdown(f"""<div class="judgment-card {card_cls}">
        <p style="font-size:2rem;font-weight:800;color:{j_color};margin:0;
           text-shadow:0 0 30px {j_color}40">{j_label}</p>
        <div style="margin-top:8px">
            <p style="color:#64748B;font-size:.7rem;margin:0;text-transform:uppercase;letter-spacing:1px">CONFIDENCE</p>
            <div style="display:flex;align-items:center;gap:10px;justify-content:center;margin-top:4px">
                <div style="flex:0 0 200px;height:8px;background:#151921;border-radius:4px;overflow:hidden">
                    <div style="width:{min(confidence,100)}%;height:8px;background:{conf_bar_color};border-radius:4px"></div>
                </div>
                <span style="color:{conf_bar_color};font-weight:800;font-size:1.1rem">{confidence:.0f}%</span>
            </div>
        </div>
        <div style="display:flex;justify-content:center;gap:32px;margin-top:14px">
            <div><p style="color:#64748B;font-size:.7rem;margin:0;text-transform:uppercase">BUY Score</p>
                <p style="color:#34D399;font-size:1.4rem;font-weight:800;margin:2px 0 0 0">{buy_t:.1f}</p></div>
            <div style="border-left:1px solid rgba(255,255,255,0.08);padding-left:32px">
                <p style="color:#64748B;font-size:.7rem;margin:0;text-transform:uppercase">SELL Score</p>
                <p style="color:#F87171;font-size:1.4rem;font-weight:800;margin:2px 0 0 0">{sell_t:.1f}</p></div>
            <div style="border-left:1px solid rgba(255,255,255,0.08);padding-left:32px">
                <p style="color:#64748B;font-size:.7rem;margin:0;text-transform:uppercase">NET</p>
                <p style="color:{net_color};font-size:1.4rem;font-weight:800;margin:2px 0 0 0">{net:+.1f}</p></div>
        </div></div>""",unsafe_allow_html=True)

    # ★ 스캐너 콤보 활성 표시 (판단 카드 바로 아래)
    sc_combos=jd.get('scanner_combos',[])
    if sc_combos:
        st.markdown("#### 🔍 활성 스캐너 콤보")
        for c in sc_combos:
            cc='combo-buy' if c['dir']=='buy' else 'combo-sell'
            dc='#34D399' if c['dir']=='buy' else '#F87171'
            ts='⭐'*(4-c['tier'])
            st.markdown(f"""<div class="combo-card {cc}">
                <div style="display:flex;align-items:center;gap:10px">
                    <span style="font-size:1.2rem">{c['icon']}</span>
                    <span style="color:#E8ECF1;font-weight:700;font-size:.95rem">{c['kor']}</span>
                </div>
                <div style="display:flex;gap:8px;align-items:center">
                    <span style="font-size:.8rem">{ts}</span>
                    <span style="color:{dc};font-size:.75rem;font-weight:600;padding:3px 10px;
                        border-radius:6px;background:rgba(255,255,255,0.04)">
                        {'BUY' if c['dir']=='buy' else 'SELL'}</span>
                </div></div>""",unsafe_allow_html=True)

    # 선행 지표 요약
    sb_v=jd.get('setup_pressure_buy',0); ss_v=jd.get('setup_pressure_sell',0)
    accel=jd.get('composite_accel',0); antic_net=sb_v-ss_v
    if abs(antic_net)>2 or abs(accel)>JT.ACCEL_MODERATE:
        if antic_net>0: albl='⏳ 매수 셋업 축적 중'; abg='rgba(16,185,129,.06)'; abd='#10B981'
        elif antic_net<0: albl='⏳ 매도 셋업 축적 중'; abg='rgba(239,68,68,.06)'; abd='#EF4444'
        else: albl='⏳ 셋업 균형'; abg='rgba(245,158,11,.06)'; abd='#F59E0B'
        aico='🚀' if accel>JT.ACCEL_MODERATE else ('💨' if accel<-JT.ACCEL_MODERATE else '➡️')
        st.markdown(f"""<div style="border-radius:12px;padding:14px 18px;margin:8px 0;
            background:{abg};border:1px solid {abd}30;border-left:3px solid {abd}">
            <div style="display:flex;justify-content:space-between;align-items:center">
                <span style="color:#E8ECF1;font-weight:700;font-size:.9rem">{albl}</span>
                <span style="color:#94A3B8;font-size:.8rem">{aico} 가속도: {accel:+.2f}</span>
            </div>
            <div style="display:flex;gap:16px;margin-top:8px">
                <span style="color:#34D399;font-size:.8rem;font-weight:600">BUY: {sb_v:.1f}</span>
                <span style="color:#F87171;font-size:.8rem;font-weight:600">SELL: {ss_v:.1f}</span>
            </div></div>""",unsafe_allow_html=True)

    # 활성 콤보 (기존 판단 콤보)
    combos=jd.get('active_combos',[])
    st.markdown("#### 🔥 활성 매매 콤보")
    if combos:
        for cb in combos:
            cc='combo-buy' if cb['dir']=='buy' else 'combo-sell'
            dc='#34D399' if cb['dir']=='buy' else '#F87171'
            tier=cb.get('tier',2); tl=f"T{tier}"
            tc='#FFD700' if tier==1 else ('#C0C0C0' if tier==2 else '#CD7F32')
            st.markdown(f"""<div class="combo-card {cc}">
                <div style="display:flex;align-items:center;gap:10px">
                    <span style="color:{dc};font-size:1.2rem">●</span>
                    <span style="color:#E8ECF1;font-weight:700;font-size:.95rem">{cb['name']}</span></div>
                <div style="display:flex;gap:8px;align-items:center">
                    <span style="color:{tc};font-size:.7rem;font-weight:700;padding:2px 6px;border-radius:4px;
                        background:rgba(255,255,255,0.05)">{tl}</span>
                    <span style="color:{dc};font-size:.75rem;font-weight:600;padding:3px 10px;
                        border-radius:6px;background:rgba(255,255,255,0.04)">
                        {'BUY' if cb['dir']=='buy' else 'SELL'}</span></div>
            </div>""",unsafe_allow_html=True)
    else:
        st.markdown("""<div class="combo-card" style="background:rgba(245,158,11,.04);
            border:1px solid rgba(245,158,11,.15);border-left:3px solid #F59E0B;justify-content:center">
            <span style="color:#FCD34D;font-weight:600;font-size:.9rem">⏸️ 활성 콤보 없음 — 관망</span></div>""",
            unsafe_allow_html=True)
    st.markdown("<div style='height:12px'></div>",unsafe_allow_html=True)

    # 8-Layer
    st.markdown("#### 📊 8-Layer 스코어 분석")
    col_b,col_s=st.columns(2)
    with col_b:
        st.markdown("<p style='color:#34D399;font-weight:700;font-size:.85rem;margin-bottom:8px;"
                    "text-transform:uppercase;letter-spacing:1px'>▲ BUY LAYERS</p>",unsafe_allow_html=True)
        _render_layer_bars(jd['buy_layers'],'buy',jd['buy_active'])
    with col_s:
        st.markdown("<p style='color:#F87171;font-weight:700;font-size:.85rem;margin-bottom:8px;"
                    "text-transform:uppercase;letter-spacing:1px'>▼ SELL LAYERS</p>",unsafe_allow_html=True)
        _render_layer_bars(jd['sell_layers'],'sell',jd['sell_active'])
    st.markdown("<div style='height:12px'></div>",unsafe_allow_html=True)

    # 판단 기준
    with st.expander("📐 판단 기준 상세",expanded=False):
        criteria=[('STRONG_BUY','🟢🟢🟢 STRONG BUY',f'BUY≥{JT.STRONG_BUY_SCORE:.0f}+{JT.STRONG_BUY_LAYERS}층+ratio≥{JT.STRONG_BUY_RATIO}'),
            ('BUY','🟢🟢 BUY',f'BUY≥{JT.BUY_SCORE:.0f}+{JT.BUY_LAYERS}층+ratio≥{JT.BUY_RATIO}'),
            ('WATCH_BUY','🟡🟢 WATCH BUY',f'BUY≥{JT.WATCH_BUY_SCORE:.0f}+{JT.WATCH_LAYERS}층'),
            ('NEUTRAL','⚪ NEUTRAL','기준 미달'),('MIXED','🟠 MIXED',f'BUY≥{JT.MIXED_MIN:.0f}&SELL≥{JT.MIXED_MIN:.0f}'),
            ('WATCH_SELL','🟡🔴 WATCH SELL',f'SELL≥{JT.WATCH_BUY_SCORE*JT.SELL_ASYMMETRY:.0f}'),
            ('SELL','🔴🔴 SELL',f'SELL≥{JT.BUY_SCORE*JT.SELL_ASYMMETRY:.0f}'),
            ('STRONG_SELL','🔴🔴🔴 STRONG SELL',f'SELL≥{JT.STRONG_BUY_SCORE*JT.SELL_ASYMMETRY:.0f}')]
        rh=""
        for key,label,cond in criteria:
            ia=judgment==key; bg='rgba(99,102,241,.1)' if ia else 'transparent'
            badge='<span style="color:#A5B4FC;font-weight:700">✅</span>' if ia else ''
            rh+=f"""<div style="display:flex;align-items:center;padding:6px 12px;margin:2px 0;border-radius:8px;background:{bg}">
                <span style="color:#CBD5E1;font-weight:600;width:200px;font-size:.85rem">{label}</span>
                <span style="color:#64748B;font-size:.8rem;flex:1">{cond}</span>{badge}</div>"""
        st.markdown(rh,unsafe_allow_html=True)

    # 5일 이력
    jh=meta.get('judgment_history',[])
    if jh:
        st.markdown("#### 📅 최근 5일 판단 추이")
        for day in reversed(jh):
            jcd=JUDGMENT_CONFIG.get(day['judgment'],('⚪','#64748B',''))
            combo_str=', '.join([c['name'] for c in day['combos']]) if day['combos'] else '—'
            sc_str=' / '.join([c['kor'] for c in day.get('scanner_combos',[])]) if day.get('scanner_combos') else ''
            full_str=combo_str+(' · 🔍'+sc_str if sc_str else '')
            bp_=min(day['buy_total']/30*100,100); sp_=min(day['sell_total']/30*100,100)
            cfv=day.get('confidence',0); cfc=jcd[1] if cfv>=60 else '#FCD34D'
            st.markdown(f"""<div class="history-row">
                <span style="color:#64748B;font-size:.85rem;width:45px;font-weight:600">{day['date']}</span>
                <span style="color:{jcd[1]};font-weight:700;font-size:.75rem;width:120px">{jcd[0]}</span>
                <span style="color:{cfc};font-size:.7rem;font-weight:600;width:35px">{cfv:.0f}%</span>
                <div style="flex:1;display:flex;align-items:center;gap:6px"><div style="flex:1">
                    <div style="display:flex;gap:4px;align-items:center">
                        <div style="flex:1;height:4px;background:#151921;border-radius:2px;overflow:hidden">
                            <div style="width:{bp_}%;height:4px;background:#34D399;border-radius:2px"></div></div>
                        <span style="color:#34D399;font-size:.7rem;width:28px;text-align:right">{day['buy_total']:.0f}</span></div>
                    <div style="display:flex;gap:4px;align-items:center;margin-top:2px">
                        <div style="flex:1;height:4px;background:#151921;border-radius:2px;overflow:hidden">
                            <div style="width:{sp_}%;height:4px;background:#F87171;border-radius:2px"></div></div>
                        <span style="color:#F87171;font-size:.7rem;width:28px;text-align:right">{day['sell_total']:.0f}</span></div>
                </div></div>
                <span style="color:#475569;font-size:.65rem;width:130px;text-align:right;overflow:hidden;
                    text-overflow:ellipsis;white-space:nowrap">{full_str}</span>
            </div>""",unsafe_allow_html=True)


def _render_layer_bars(layers, side, active_count):
    icons={'Trend':'📈','Momentum':'🔥','Candle':'🕯️','BB':'📊','Volume':'📦','MF':'💰','Pattern':'⭐','Anticipation':'⏳'}
    mx=10.0; fc='layer-bar-fill-buy' if side=='buy' else 'layer-bar-fill-sell'
    sc='#34D399' if side=='buy' else '#F87171'; total=sum(max(0,v) for v in layers.values())
    for name,score in layers.items():
        icon=icons.get(name,'•'); pct=min(max(score,0)/mx*100,100)
        op='1' if score>0 else ('0.5' if score<0 else '0.2')
        dc2='#F87171' if score<0 and side=='buy' else ('#34D399' if score<0 and side=='sell' else sc)
        ind='⚠️' if score<0 else ('✓' if score>0 else '')
        st.markdown(f"""<div class="layer-bar-wrap">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px">
                <span style="color:#94A3B8;font-size:.8rem;font-weight:500;opacity:{op}">{icon} {name}</span>
                <span style="color:{sc if score>=0 else dc2};font-weight:700;font-size:.8rem;opacity:{op}">
                    {score:.1f} {ind}</span></div>
            <div class="layer-bar-bg"><div class="layer-bar-fill {fc}" style="width:{pct}%;opacity:{op}"></div></div>
        </div>""",unsafe_allow_html=True)
    st.markdown(f"""<div style="margin-top:12px;padding:10px 14px;border-radius:10px;background:rgba(255,255,255,0.02);
        border:1px solid rgba(255,255,255,0.04);text-align:center">
        <span style="color:{sc};font-weight:800;font-size:1.15rem">{total:.1f}</span>
        <span style="color:#475569;font-size:.8rem"> 점 · 활성 </span>
        <span style="color:#CBD5E1;font-weight:700;font-size:.85rem">{active_count}</span>
        <span style="color:#475569;font-size:.8rem">/{NUM_LAYERS}</span></div>""",unsafe_allow_html=True)


# ──────────────────────────────────────────
# 가격 헤더 + st.metric
# ──────────────────────────────────────────
_IT={'wt1':[(-53,'극과매도'),(-20,'과매도'),(20,'중립'),(53,'과매수'),(999,'극과매수')],
     'rsi':[(30,'과매도'),(45,'약세'),(55,'중립'),(70,'강세'),(999,'과매수')]}
def _il(n,v):
    for t,l in _IT.get(n,[]):
        if v<=t: return l
    return ''

def render_price_header(m):
    chg=m['price_change']; cp=m['price_change_pct']
    cc='price-change-up' if chg>=0 else 'price-change-down'; ci='▲' if chg>=0 else '▼'
    vr=m['volume']/m['avg_volume'] if m['avg_volume'] else 0
    cv=m.get('confluence_score',0); sd=m.get('supertrend_dir',0); sh=m.get('shield_status','')
    mhv=m.get('macd_hist',0); accel=m.get('composite_accel',0)
    jd=m.get('judgment_detail',{}); j_short=jd.get('judgment','NEUTRAL') if jd else 'N/A'
    confidence=jd.get('confidence',0) if jd else 0
    jcm={'STRONG_BUY':'ind-bullish','BUY':'ind-bullish','WATCH_BUY':'ind-neutral',
         'STRONG_SELL':'ind-bearish','SELL':'ind-bearish','WATCH_SELL':'ind-neutral',
         'MIXED':'ind-neutral','NEUTRAL':'ind-neutral'}
    jcls=jcm.get(j_short,'ind-neutral')
    # ★ 스캐너 콤보 수
    sc_combos=jd.get('scanner_combos',[])
    sc_count=len(sc_combos)
    specs=[(jcls,f"📍 {j_short} ({confidence:.0f}%)"),
        (_cls(m['wt1'],-20,20),f"WT {m['wt1']:.0f} {_il('wt1',m['wt1'])}"),
        (_cls(m['rsi'],40,60),f"RSI {m['rsi']:.0f}"),
        ('ind-bullish' if m['mf_area']<0 else ('ind-bearish' if m['mf_area']>0 else 'ind-neutral'),f"MF {m['mf_area']:.1f}"),
        ('ind-bullish' if vr>1.5 else 'ind-neutral',f"Vol {vr:.1f}x"),
        ('ind-bullish' if m['adx']>25 else 'ind-neutral',f"ADX {m['adx']:.0f}"),
        ('ind-bullish' if cv>=3.5 else ('ind-bearish' if cv<=-3.5 else 'ind-neutral'),f"Conf {cv:.1f}"),
        ('ind-bullish' if sd==1 else 'ind-bearish',f"ST {'▲' if sd==1 else '▼'}"),
        ('ind-bullish' if mhv>0 else ('ind-bearish' if mhv<0 else 'ind-neutral'),f"MACD {mhv:+.2f}"),
        ('ind-bullish' if m.get('cmf',0)>0.05 else ('ind-bearish' if m.get('cmf',0)<-0.05 else 'ind-neutral'),f"CMF {m.get('cmf',0):.2f}"),
        ('ind-bullish' if accel>JT.ACCEL_MODERATE else ('ind-bearish' if accel<-JT.ACCEL_MODERATE else 'ind-neutral'),f"Accel {accel:+.1f}")]
    if sc_count>0:
        sc_dir='buy' if any(c['dir']=='buy' for c in sc_combos) else 'sell'
        specs.append(('ind-bullish' if sc_dir=='buy' else 'ind-bearish',f"🔍 SC {sc_count}"))
    ih="".join([f"<span class='indicator-mini {c}'>{l}</span>" for c,l in specs])
    if sh: ih+=f"<span class='indicator-mini ind-bearish' style='font-weight:700'>🔓 {sh}</span>"
    tr=m.get('trend_regime','NEUTRAL ⚪')
    st.markdown(f"""<div class="price-header">
        <div style="display:flex;justify-content:space-between;align-items:flex-start">
            <div><p class="price-label">🚦 {m['ticker']} · {m['last_date']} · <b style="color:#A5B4FC">{tr}</b></p>
                <p class="price-big" style="color:#F8FAFC">${m['price']:.2f}
                    <span class="{cc}" style="font-size:1.1rem;margin-left:10px;font-weight:700">
                        {ci} {abs(chg):.2f} ({abs(cp):.2f}%)</span></p></div>
            <div style="text-align:right;padding-top:4px">
                <p class="price-label">ATR (14)</p>
                <p style="color:#FCD34D;font-size:1.2rem;font-weight:700;margin:2px 0 0 0">
                    ${m['atr']:.2f} <span style="font-size:.85rem;color:#D97706">({m['atr_pct']:.1f}%)</span></p></div>
        </div>
        <div style="margin-top:12px;display:flex;gap:5px;flex-wrap:wrap">{ih}</div>
    </div>""",unsafe_allow_html=True)
    mc1,mc2,mc3,mc4,mc5=st.columns(5)
    with mc1: st.metric("BUY Score",f"{jd.get('buy_total',0):.1f}",delta=f"{jd.get('buy_active',0)}/{NUM_LAYERS} layers",delta_color="normal")
    with mc2: st.metric("SELL Score",f"{jd.get('sell_total',0):.1f}",delta=f"{jd.get('sell_active',0)}/{NUM_LAYERS} layers",delta_color="inverse")
    with mc3:
        nv=jd.get('buy_total',0)-jd.get('sell_total',0)
        st.metric("NET Score",f"{nv:+.1f}",delta=j_short,delta_color="normal" if nv>0 else "inverse")
    with mc4: st.metric("Confidence",f"{confidence:.0f}%",delta=m.get('overall_bias','N/A'),delta_color="normal" if confidence>=60 else "off")
    with mc5:
        antic=m.get('setup_pressure_buy',0)-m.get('setup_pressure_sell',0)
        st.metric("⏳ Antic",f"{antic:+.1f}",delta=f"Accel {accel:+.1f}",delta_color="normal" if antic>0 else ("inverse" if antic<0 else "off"))


def render_speedometer(m):
    gf=build_speedometer_gauges(m)
    st.plotly_chart(gf,use_container_width=True,theme=None,config={'displayModeBar':False})
    bias=m['overall_bias']; sc=m.get('bias_score',0)
    sty={'STRONG BUY':('rgba(16,185,129,.1)','#34D399','🟢🟢'),'BUY':('rgba(16,185,129,.06)','#34D399','🟢'),
         'STRONG SELL':('rgba(239,68,68,.1)','#F87171','🔴🔴'),'SELL':('rgba(239,68,68,.06)','#F87171','🔴')}
    bg,clr,ico=sty.get(bias,('rgba(245,158,11,.06)','#FCD34D','🟠'))
    bp=m.get('buy_proximity',0); sp=m.get('sell_proximity',0)
    ptxt=""
    if bp>=50: ptxt=f"<span style='color:#34D399;font-weight:600'>매수 임박 {bp:.0f}%</span>"
    elif sp>=50: ptxt=f"<span style='color:#F87171;font-weight:600'>매도 임박 {sp:.0f}%</span>"
    sqt=" · <span style='color:#FCD34D;font-weight:700'>💥 Squeeze ON</span>" if m.get('squeeze_on') else ""
    st.markdown(f"""<div style="background:{bg};border-radius:12px;padding:12px 18px;text-align:center;
        margin:4px 0 14px 0;border:1px solid rgba(255,255,255,0.06)">
        <span style="font-size:1.05rem;font-weight:700;color:{clr}">{ico} 종합 판정: {bias} ({sc:.1f})</span>
        {f' · {ptxt}' if ptxt else ''}{sqt}</div>""",unsafe_allow_html=True)


def render_alerts(m):
    alerts=[]; bp=m.get('buy_proximity',0); sp=m.get('sell_proximity',0)
    if bp>=70: alerts.append(('🟢⚡ 매수 매우 임박!','#34D399','rgba(16,185,129,.08)',bp))
    elif bp>=50: alerts.append(('🟢 매수 접근 중','#6EE7B7','rgba(16,185,129,.05)',bp))
    if sp>=70: alerts.append(('🔴⚡ 매도 매우 임박!','#F87171','rgba(239,68,68,.08)',sp))
    elif sp>=50: alerts.append(('🔴 매도 접근 중','#FCA5A5','rgba(239,68,68,.05)',sp))
    if m.get('squeeze_on'): alerts.append(('💥 Squeeze ON','#FCD34D','rgba(245,158,11,.06)',80))
    accel=m.get('composite_accel',0)
    if accel>JT.ACCEL_STRONG: alerts.append(('⚡ 강한 상승 가속','#34D399','rgba(16,185,129,.06)',70))
    elif accel<-JT.ACCEL_STRONG: alerts.append(('⚡ 강한 하락 가속','#F87171','rgba(239,68,68,.06)',70))
    # ★ 스캐너 콤보 알림
    jd=m.get('judgment_detail',{}); sc_combos=jd.get('scanner_combos',[])
    for c in sc_combos:
        clr2='#34D399' if c['dir']=='buy' else '#F87171'
        bg2='rgba(16,185,129,.05)' if c['dir']=='buy' else 'rgba(239,68,68,.05)'
        alerts.append((f"🔍 {c['kor']}",clr2,bg2,70 if c['tier']==1 else 50))
    j=jd.get('judgment','NEUTRAL'); conf=jd.get('confidence',0)
    if j=='STRONG_BUY': alerts.insert(0,(f'🟢🟢🟢 STRONG BUY ({conf:.0f}%)','#34D399','rgba(16,185,129,.1)',95))
    elif j=='BUY': alerts.insert(0,(f'🟢🟢 BUY ({conf:.0f}%)','#34D399','rgba(16,185,129,.06)',75))
    elif j=='STRONG_SELL': alerts.insert(0,(f'🔴🔴🔴 STRONG SELL ({conf:.0f}%)','#F87171','rgba(239,68,68,.1)',95))
    elif j=='SELL': alerts.insert(0,(f'🔴🔴 SELL ({conf:.0f}%)','#F87171','rgba(239,68,68,.06)',75))
    for txt,clr,bg,pct in alerts:
        w=min(pct,100)
        st.markdown(f"""<div class="alert-bar" style="background:{bg}">
            <div style="display:flex;justify-content:space-between;align-items:center">
                <span style="color:{clr};font-weight:700;font-size:.9rem">{txt}</span>
                <span style="color:{clr};font-weight:800;font-size:.85rem">{pct:.0f}%</span></div>
            <div class="alert-bar-progress"><div class="alert-bar-fill" style="background:{clr};width:{w}%"></div></div>
        </div>""",unsafe_allow_html=True)


def render_signals(m):
    sigs=m['recent_signals']
    if not sigs:
        st.markdown("""<div class="signal-card signal-card-neutral" style="text-align:center">
            <p style="margin:0;color:#FCD34D;font-weight:600">⏸️ 최근 15일 내 시그널 없음</p></div>""",unsafe_allow_html=True)
        return
    dg=OrderedDict()
    for icon,lbl,ds,side in sigs: dg.setdefault(ds,[]).append((icon,lbl,side))
    for ds in reversed(dg):
        group=dg[ds]; bc=sum(1 for _,_,s in group if s=='buy'); sc2=sum(1 for _,_,s in group if s=='sell')
        ct='signal-card-buy' if bc>sc2 else ('signal-card-sell' if sc2>bc else 'signal-card-neutral')
        parts=[]
        for i,l,s in group:
            cn="ind-bullish" if s=="buy" else ("ind-bearish" if s=="sell" else "ind-neutral")
            parts.append(f'<span class="indicator-mini {cn}">{i} {l}</span>')
        dc2='#34D399' if bc>sc2 else ('#F87171' if sc2>bc else '#FCD34D')
        st.markdown(f"""<div class="signal-card {ct}">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
                <span style="font-weight:700;font-size:.9rem;color:#E8ECF1">📅 {ds}</span>
                <span style="color:{dc2};font-size:.75rem;font-weight:600;padding:2px 8px;border-radius:6px;
                    background:rgba(255,255,255,0.04)">{len(group)}개</span></div>
            <div style="display:flex;gap:5px;flex-wrap:wrap">{" ".join(parts)}</div></div>""",unsafe_allow_html=True)


# ──────────────────────────────────────────
# 메인 분석 렌더 (★ 6탭: 스캐너 콤보 탭 추가)
# ──────────────────────────────────────────
def render_analysis(msg):
    m,fig=msg.get('meta'),msg.get('fig')
    if m: render_price_header(m); render_speedometer(m); render_alerts(m)
    if m or fig:
        t0,t1,t2,t3,t4,t5=st.tabs(["🎯 매매 판단","📊 차트","⏳ 선행 지표","🔔 시그널 이력","🔍 스캐너 콤보","🏢 기업 상세"])
        with t0:
            if m: render_judgment(m)
        with t1:
            pcfg={'displaylogo':False,'modeBarButtonsToRemove':['lasso2d','select2d']}
            if fig: st.plotly_chart(fig,use_container_width=True,theme=None,config=pcfg)
        with t2:
            if m: render_anticipation_tab(m)
        with t3:
            if m: render_signals(m)
        with t4:
            if m: render_scanner_tab(m)  # ★
        with t5:
            if m: render_company_details(m['ticker'])


# ──────────────────────────────────────────
# 사이드바
# ──────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🚦 CipherX")
    st.markdown("<p style='color:#888;font-size:.8rem'>AI 퀀트 · Anticipatory v12.0 + Scanner</p>",unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("### 📅 차트 기간")
    chart_period=st.radio("표시 기간",['3개월','6개월','1년','2년'],index=0,horizontal=True,key="period")
    chart_days={'3개월':63,'6개월':126,'1년':252,'2년':504}[chart_period]
    st.markdown("---")
    with st.expander("🎛️ 차트 표시 설정",expanded=False):
        st.markdown("**판단 등급**")
        _show_strong=st.checkbox("🟢🔴 STRONG",value=True,key="j_strong")
        _show_normal=st.checkbox("🟢🔴 BUY/SELL",value=True,key="j_normal")
        _show_watch=st.checkbox("🟡 WATCH",value=False,key="j_watch")
        _show_mixed=st.checkbox("🟠 MIXED",value=False,key="j_mixed")
        ej=set()
        if _show_strong: ej|={'STRONG_BUY','STRONG_SELL'}
        if _show_normal: ej|={'BUY','SELL'}
        if _show_watch: ej|={'WATCH_BUY','WATCH_SELL'}
        if _show_mixed: ej.add('MIXED')
        st.session_state['enabled_judgments']=ej
        st.caption(f"표시: {len(ej)}개 등급")
        st.markdown("---")
        st.markdown("**🔍 스캐너 콤보**")
        _show_sc=st.checkbox("차트에 스캐너 콤보 마커 표시",value=True,key="show_sc")
        st.session_state['show_scanner_combos']=_show_sc
        st.session_state['enabled_signals']=set(ALL_CHART_SIGNALS.keys())
    st.markdown("---")
    # ★ 멀티 스캐너 버튼
    if st.button("🔍 멀티 티커 스캐너",use_container_width=True,type="secondary"):
        st.session_state['show_scanner_page']=True
        st.rerun()
    st.markdown("---")
    with st.expander("🔍 디버그",expanded=False):
        st.caption(f"시그널: {len(SIGNAL_REGISTRY)} + {len(COMPOSITE_SIGNALS)} composite")
        st.caption(f"스캐너 콤보: {len(SCANNER_COMBOS)}")
        st.caption(f"판단 콤보: {len(COMBO_MAP)}")
        st.caption(f"레이어: {NUM_LAYERS}")
        st.caption(f"STRONG BUY: ≥{JT.STRONG_BUY_SCORE}, {JT.STRONG_BUY_LAYERS}층+")
    if st.button("🗑️ 대화 내역 지우기",use_container_width=True,type="secondary"):
        for key in ['messages','pending_ai_ticker','pending_ai_prompt','last_ticker','show_scanner_page']:
            if key=='messages':
                st.session_state[key]=[{"role":"assistant","type":"text",
                    "content":"안녕하세요! 🚦 **CipherX v12.0** 입니다.\n\n분석할 **티커명**을 입력하세요."}]
            else: st.session_state[key]=None
        st.rerun()


# ──────────────────────────────────────────
# 세션 관리
# ──────────────────────────────────────────
if 'messages' not in st.session_state:
    st.session_state.messages=[{"role":"assistant","type":"text",
        "content":("안녕하세요! 🚦 **CipherX v12.0** 입니다.\n\n"
                   "분석할 **티커명**을 입력하세요.\n\n"
                   "🆕 **V12.0 기능:** ⏳ 선행 지표 · 📊 8-Layer · 🔍 스캐너 콤보 20종")}]
for key in ['pending_ai_ticker','pending_ai_prompt','last_ticker']:
    if key not in st.session_state: st.session_state[key]=None
if 'enabled_signals' not in st.session_state: st.session_state['enabled_signals']=set(ALL_CHART_SIGNALS.keys())
if 'enabled_judgments' not in st.session_state: st.session_state['enabled_judgments']={'STRONG_BUY','BUY','SELL','STRONG_SELL'}
if 'show_scanner_combos' not in st.session_state: st.session_state['show_scanner_combos']=True
if 'show_scanner_page' not in st.session_state: st.session_state['show_scanner_page']=False

def _check_query_params():
    try:
        qp=st.query_params; t=qp.get("ticker",None)
        if t and st.session_state.last_ticker!=t.upper(): return t.upper()
    except: pass
    return None
url_ticker=_check_query_params()


# ──────────────────────────────────────────
# ★ 메인 페이지 분기: 스캐너 or 채팅
# ──────────────────────────────────────────
st.markdown("<h2 style='text-align:center;color:#fff;margin-bottom:20px'>🚦 CipherX</h2>",unsafe_allow_html=True)

if st.session_state.get('show_scanner_page'):
    # ★ 스캐너 페이지 모드
    if st.button("← 분석 모드로 돌아가기",type="secondary"):
        st.session_state['show_scanner_page']=False; st.rerun()
    render_scanner_page()
else:
    # 일반 채팅 모드
    if not st.session_state.last_ticker:
        st.markdown("<p style='text-align:center;color:#888;font-size:0.9rem'>🔥 빠른 분석</p>",unsafe_allow_html=True)
        cols=st.columns(4)
        quick_tickers=["NVDA","TSLA","AAPL","QQQ"]
        for iq,col in enumerate(cols):
            with col:
                if st.button(f"{quick_tickers[iq]}",use_container_width=True):
                    st.session_state['quick_ticker']=quick_tickers[iq]
        st.markdown("<br>",unsafe_allow_html=True)

    for i,msg in enumerate(st.session_state.messages):
        av="✨" if msg["role"]=="assistant" else "🧑‍💻"
        with st.chat_message(msg["role"],avatar=av):
            if msg.get("type")=="analysis":
                st.markdown(msg.get("content",""))
                render_analysis(msg)
                if msg.get("prompt"):
                    with st.expander("📝 퀀트 프롬프트 원문",expanded=False):
                        st.code(msg["prompt"],language="markdown")
                        st_copy_to_clipboard(msg["prompt"],before_copy_label="📋 복사",after_copy_label="✅ 복사됨!")
            elif msg.get("type")=="report":
                with st.expander(f"📊 {msg.get('ticker','')} AI 퀀트 리포트",expanded=True):
                    st.markdown(msg["content"])
                st.download_button("📥 마크다운 다운로드",key=f"dl_{i}_{msg.get('ticker','RPT')}",
                    data=msg["content"].encode('utf-8'),
                    file_name=f"{msg.get('ticker','RPT').upper()}_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
                    mime="text/markdown",use_container_width=True)
            else:
                st.markdown(msg.get("content",""))


# ──────────────────────────────────────────
# AI 실행
# ──────────────────────────────────────────
def _run_ai():
    tp=st.session_state.pending_ai_ticker; pp=st.session_state.pending_ai_prompt
    with st.chat_message("assistant",avatar="✨"):
        pb=st.progress(0,text="퀀트 엔진 로딩...")
        try:
            pb.progress(10,text="Gemini 초기화..."); model=get_gemini_model()
            pb.progress(20,text="데이터 취합..."); chunks=[]
            def gen():
                pb.progress(40,text="🚀 AI 리포트 생성...")
                response=model.generate_content(pp,stream=True)
                for chunk in response:
                    text=chunk.text
                    if text: chunks.append(text); yield text
                pb.progress(100,text="✅ 완료!")
            with st.expander(f"📊 {tp.upper()} AI 퀀트 리포트",expanded=True):
                st.write_stream(gen())
            time.sleep(0.3); pb.empty()
            st.session_state.messages.append({"role":"assistant","type":"report","ticker":tp.upper(),"content":"".join(chunks)})
            st.session_state.pending_ai_ticker=None; st.session_state.pending_ai_prompt=None; st.rerun()
        except Exception as e: pb.empty(); st.error(f"AI 오류: {e}")


# ──────────────────────────────────────────
# 티커 처리
# ──────────────────────────────────────────
def process_ticker(tv, refresh=False):
    tv=tv.strip().upper()
    st.session_state.pending_ai_ticker=None; st.session_state.pending_ai_prompt=None
    st.session_state['show_scanner_page']=False
    if not _valid_fmt(tv): st.toast(f"⚠️ {tv} — 올바른 형식이 아닙니다.",icon="🚨"); return
    if not validate_ticker(tv): st.toast(f"⚠️ {tv} — 데이터를 찾을 수 없습니다.",icon="🔍"); return
    st.session_state.messages.append({"role":"user","type":"text","content":tv})
    st.session_state.last_ticker=tv
    try: st.query_params["ticker"]=tv
    except: pass
    with st.chat_message("assistant",avatar="✨"):
        with st.status(f"🌐 {tv} 퀀트 파이프라인 가동...",expanded=True) as status:
            st.write("📡 펀더멘탈 데이터 조회...")
            fundamentals=fetch_fundamentals(tv)
            st.write("📊 기술적 지표 + 8-Layer 판단 + 🔍 스캐너 콤보 계산...")
            fig,phist,meta=analyze(tv,chart_days,refresh)
            if fig:
                prompt=build_ai_prompt(tv,phist,fundamentals)
                status.update(label=f"✅ {tv} 분석 완료!",state="complete",expanded=False)
            else:
                prompt=None
                status.update(label=f"⚠️ {tv} 실패",state="error",expanded=False)
        if fig:
            st.session_state.messages.append({"role":"assistant","type":"analysis","ticker":tv,
                "content":f"✅ **{tv}** 분석 완료.","fig":fig,"meta":meta,"prompt":prompt})
            st.session_state.pending_ai_ticker=tv; st.session_state.pending_ai_prompt=prompt; st.rerun()
        else:
            st.session_state.messages.append({"role":"assistant","type":"text",
                "content":f"⚠️ **{tv}** 분석 실패: {phist}"}); st.rerun()


# ──────────────────────────────────────────
# 실행 트리거
# ──────────────────────────────────────────
if not st.session_state.get('show_scanner_page'):
    if url_ticker and 'url_loaded' not in st.session_state:
        st.session_state['url_loaded']=True; process_ticker(url_ticker)
    if st.session_state.get('quick_ticker'):
        qt=st.session_state.pop('quick_ticker'); process_ticker(qt)
    if st.session_state.last_ticker and st.session_state.pending_ai_ticker and st.session_state.pending_ai_prompt:
        if st.button(f"🚀 {st.session_state.pending_ai_ticker.upper()} AI 심층 퀀트 분석",type="primary",use_container_width=True):
            _run_ai()
    elif st.session_state.pending_ai_ticker and st.session_state.pending_ai_prompt:
        if st.button(f"🚀 {st.session_state.pending_ai_ticker.upper()} AI 심층 퀀트 분석",type="primary",use_container_width=True):
            _run_ai()
    if ticker_input:=st.chat_input("미국 주식 티커를 입력하세요 (예: TSLA, AAPL, QQQ)"):
        process_ticker(ticker_input)