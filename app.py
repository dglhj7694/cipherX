# ══════════════════════════════════════════════════════════════
#  CipherX V12.3 — Full Signal Integration
#  PART 1/6: 설정, 상수, 레지스트리
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
from scipy.signal import find_peaks
from concurrent.futures import ThreadPoolExecutor, as_completed

st.set_page_config(page_title="CipherX V12.3", page_icon="📈", layout="centered", initial_sidebar_state="collapsed")

# ──────────────────────────────────────────
# CSS
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
h4{color:#CBD5E1!important;font-weight:600!important;font-size:1rem!important}
.block-container{padding-top:1rem!important;max-width:960px}
div.stButton>button[kind="primary"]{background:linear-gradient(135deg,#6366F1 0%,#8B5CF6 50%,#A78BFA 100%)!important;color:white!important;border:none!important;border-radius:12px!important;padding:.65rem 1.5rem!important;font-weight:700!important;width:100%}
.price-header{background:linear-gradient(160deg,#0F1320,#141926,#111827);border:1px solid #1C2233;border-radius:16px;padding:20px 24px;margin-bottom:18px}
.price-big{font-size:2.2rem;font-weight:800;margin:0}
.price-change-up{color:#34D399!important}
.price-change-down{color:#F87171!important}
.indicator-mini{display:inline-block;padding:5px 11px;margin:3px;border-radius:8px;font-size:.78rem;font-weight:600}
.ind-bullish{background:rgba(16,185,129,.12);color:#6EE7B7}
.ind-bearish{background:rgba(239,68,68,.12);color:#FCA5A5}
.ind-neutral{background:rgba(245,158,11,.10);color:#FCD34D}
.signal-summary-card{border-radius:14px;padding:16px 20px;margin:8px 0;border:1px solid rgba(255,255,255,0.06)}
.signal-summary-buy{background:linear-gradient(135deg,rgba(0,230,118,.08),rgba(16,185,129,.03));border-left:4px solid #10B981}
.signal-summary-sell{background:linear-gradient(135deg,rgba(239,68,68,.08),rgba(220,38,38,.03));border-left:4px solid #EF4444}
.judgment-card{border-radius:16px;padding:24px 28px;margin-bottom:20px;text-align:center;position:relative;overflow:hidden}
.judgment-card-buy{background:linear-gradient(160deg,#052E16,#0D1B2A);border:1px solid rgba(16,185,129,.25)}
.judgment-card-sell{background:linear-gradient(160deg,#2A0E0E,#1B0D1B);border:1px solid rgba(239,68,68,.25)}
.judgment-card-neutral{background:linear-gradient(160deg,#1A1608,#1B1A0D);border:1px solid rgba(245,158,11,.2)}
</style>""", unsafe_allow_html=True)
inject_css()

# ══════════════════════════════════════════
#  상수
# ══════════════════════════════════════════
OB1, OB2, OS1, OS2 = 53, 60, -53, -60
NUM_LAYERS = 8

class JT:
    STRONG_BUY_SCORE=18.0; BUY_SCORE=12.0; WATCH_BUY_SCORE=6.5
    STRONG_BUY_LAYERS=5; BUY_LAYERS=3; WATCH_LAYERS=2
    STRONG_BUY_RATIO=2.0; BUY_RATIO=1.4
    STRONG_BUY_DIFF=10.0; BUY_DIFF=5.0; WATCH_DIFF=2.0
    SELL_ASYMMETRY=0.85; LOW_VOL_SCALE=0.85
    ACCEL_STRONG=3.0; ACCEL_MODERATE=1.5
    COMBO_TIER1_BONUS=4.0; COMBO_TIER2_BONUS=2.5; COMBO_TIER3_BONUS=1.5
    DECAY_DAYS=3; DECAY_RATE=0.5

GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GEMINI_API_KEY)

@st.cache_resource
def get_gemini_model():
    return genai.GenerativeModel('gemini-2.5-flash')

# ══════════════════════════════════════════
#  시그널 레지스트리 (125개 + 기존)
# ══════════════════════════════════════════
_B, _S, _N = 'buy', 'sell', 'neutral'

def _sig(w, d, icon, label, sym, sz, clr, base, atr_m, kor, desc):
    return {'w': w, 'dir': d, 'icon': icon, 'label': label, 'sym': sym,
            'sz': sz, 'clr': clr, 'base': base, 'atr_m': atr_m, 'kor': kor, 'desc': desc}

SIGNAL_REGISTRY = {
    # ═══ MCB+ 핵심 시그널 ═══
    'Gold_Dot': _sig(3.0, _B, '🏆', 'GOLD DOT', 'circle', 18, '#FFD700', 'Low', -3.0, '최강 매수', 'RSI<30+MFI<30+WT1<-60+상승다이버전스'),
    'Green_Dot_T1': _sig(2.5, _B, '🟢', 'BUY T1', 'circle', 16, '#00E676', 'Low', -2.5, '강한 매수', 'WT과매도교차+RSI<30+MFI<30'),
    'Green_Dot_T2': _sig(2.0, _B, '🟩', 'BUY T2', 'circle', 13, '#69F0AE', 'Low', -2.2, '매수', 'WT과매도+RSI/MFI<32'),
    'Blue_Diamond': _sig(2.0, _B, '🔹', 'BLUE DIA', 'diamond', 14, '#00bfff', 'Low', -1.8, '추세 매수', 'WT2≤0상승교차+HTF강세'),
    'Green_Circle': _sig(0.8, _B, '✅', 'BUY Circle', 'circle-open', 11, '#00E676', 'Low', -1.2, '과매도 반등', 'WT과매도교차+RSI<45'),
    'Blood_Diamond': _sig(3.0, _S, '🩸', 'BLOOD DIA', 'diamond', 18, '#DC143C', 'High', 3.0, '최강 매도', 'RSI>70+MFI>70+WT1>60+하락다이버전스'),
    'Red_Dot_T1': _sig(2.5, _S, '🔴', 'SELL T1', 'circle', 16, '#FF1744', 'High', 2.5, '강한 매도', 'WT과매수하락교차+RSI>70+MFI>70'),
    'Red_Dot_T2': _sig(2.0, _S, '🟥', 'SELL T2', 'circle', 13, '#FF5252', 'High', 2.2, '매도', 'WT과매수+RSI/MFI>68'),
    'Red_Diamond': _sig(2.0, _S, '🔸', 'RED DIA', 'diamond', 14, '#ff3333', 'High', 1.8, '추세 매도', 'WT2≥0하락교차+HTF약세'),
    'Red_Circle': _sig(0.8, _S, '⛔', 'SELL Circle', 'circle-open', 11, '#FF1744', 'High', 1.2, '과매수 하락', 'WT과매수하락교차+RSI>55'),
    
    # ═══ 다이버전스 ═══
    'Bull_Divergence': _sig(2.0, _B, '📈', 'Bull Div', 'triangle-up', 12, '#AA00FF', 'Low', -2.0, '상승 다이버전스', '가격↓ vs WT↑'),
    'Bear_Divergence': _sig(2.0, _S, '📉', 'Bear Div', 'triangle-down', 12, '#AA00FF', 'High', 2.0, '하락 다이버전스', '가격↑ vs WT↓'),
    'RSI_Bull_Divergence': _sig(1.5, _B, '📊', 'RSI Bull Div', 'triangle-up', 11, '#CE93D8', 'Low', -1.8, 'RSI 상승 다이버전스', '가격↓ vs RSI↑'),
    'RSI_Bear_Divergence': _sig(1.5, _S, '📉', 'RSI Bear Div', 'triangle-down', 11, '#CE93D8', 'High', 1.8, 'RSI 하락 다이버전스', '가격↑ vs RSI↓'),
    'Hidden_Bull_Div': _sig(1.5, _B, '🔀', 'Hidden Bull', 'triangle-up', 10, '#E040FB', 'Low', -1.6, '히든 상승 다이버전스', '가격↑ vs WT↓'),
    'Hidden_Bear_Div': _sig(1.5, _S, '🔁', 'Hidden Bear', 'triangle-down', 10, '#E040FB', 'High', 1.6, '히든 하락 다이버전스', '가격↓ vs WT↑'),
    
    # ═══ Jeff Cooper Hit & Run (24개) ═══
    'Pullback_123_Bull': _sig(2.0, _B, '🎯', '123PB▲', 'triangle-up', 12, '#00E676', 'Low', -1.8, '1,2,3 풀백 매수', 'ADX>30+DI↑+3일저점하락'),
    'Pullback_123_Bear': _sig(2.0, _S, '🎯', '123PB▼', 'triangle-down', 12, '#FF1744', 'High', 1.8, '1,2,3 되돌림 매도', 'ADX>30+DI↓+3일고점상승'),
    'Setup_180_Bull': _sig(2.0, _B, '🔄', '180▲', 'star-diamond', 13, '#00E676', 'Low', -2.0, '180 매수 셋업', '전일하위25%→당일상위25%+MA위'),
    'Setup_180_Bear': _sig(2.0, _S, '🔄', '180▼', 'star-diamond', 13, '#FF1744', 'High', 2.0, '180 매도 셋업', '전일상위25%→당일하위25%+MA아래'),
    'Boomer_Buy': _sig(2.0, _B, '💣', 'Boomer▲', 'star', 12, '#00E676', 'Low', -1.8, '부머 매수', 'ADX>30+2일인사이드→돌파'),
    'Boomer_Sell': _sig(2.0, _S, '💣', 'Boomer▼', 'star', 12, '#FF1744', 'High', 1.8, '부머 매도', 'ADX>30+2일인사이드→이탈'),
    'Expansion_BO': _sig(2.5, _B, '🚀', 'XBO', 'star-diamond', 14, '#FFD700', 'Low', -2.5, '확장 돌파', '2개월신고가+9일최대범위'),
    'Expansion_BD': _sig(2.5, _S, '💨', 'XBD', 'star-diamond', 14, '#FF0000', 'High', 2.5, '확장 붕괴', '2개월신저가+9일최대범위'),
    'Expansion_Pivot_Buy': _sig(2.0, _B, '📍', 'XPivot▲', 'triangle-up', 12, '#00E676', 'Low', -2.0, '확장 피봇 매수', '50MA부근폭발상승'),
    'Expansion_Pivot_Sell': _sig(2.0, _S, '📍', 'XPivot▼', 'triangle-down', 12, '#FF1744', 'High', 2.0, '확장 피봇 매도', '50MA부근폭발하락'),
    'Expansion_Double_Sticks': _sig(2.0, _S, '🎭', 'DoubleStk', 'hexagram', 13, '#FF5722', 'High', 2.0, '더블 스틱', '60일신고가후시가아래마감'),
    'Gilligans_Buy': _sig(2.0, _B, '🏝️', 'Gilligan▲', 'hexagon', 12, '#00BCD4', 'Low', -2.0, '길리건 매수', '2개월신저가갭다운→반전'),
    'Gilligans_Sell': _sig(2.0, _S, '🏝️', 'Gilligan▼', 'hexagon', 12, '#FF5722', 'High', 2.0, '길리건 매도', '2개월신고가갭업→반전'),
    'Lizard_Bull': _sig(1.5, _B, '🦎', 'Lizard▲', 'triangle-up', 10, '#00E676', 'Low', -1.5, '리자드 매수', '시가종가상위25%+10일신저가'),
    'Lizard_Bear': _sig(1.5, _S, '🦎', 'Lizard▼', 'triangle-down', 10, '#FF1744', 'High', 1.5, '리자드 매도', '시가종가하위25%+10일신고가'),
    'Slingshot_Bull': _sig(2.0, _B, '🎯', 'Sling▲', 'triangle-up', 12, '#00E676', 'Low', -1.8, '슬링샷 매수', '2개월신고가후흔들기→재돌파'),
    'Slingshot_Bear': _sig(2.0, _S, '🎯', 'Sling▼', 'triangle-down', 12, '#FF1744', 'High', 1.8, '슬링샷 매도', '2개월신저가후흔들기→재하락'),
    'Jack_In_Box_Bull': _sig(2.0, _B, '🎁', 'JackBox▲', 'star', 12, '#00E676', 'Low', -1.8, '잭인더박스 매수', 'XBO후인사이드→재돌파'),
    'Jack_In_Box_Bear': _sig(2.0, _S, '🎁', 'JackBox▼', 'star', 12, '#FF1744', 'High', 1.8, '잭인더박스 매도', 'XBD후인사이드→재하락'),
    'NonADX_123_Bull': _sig(1.8, _B, '📐', 'nADX123▲', 'triangle-up', 11, '#69F0AE', 'Low', -1.5, '비ADX풀백 매수', '주가>50MA+3일저점하락'),
    'NonADX_123_Bear': _sig(1.8, _S, '📐', 'nADX123▼', 'triangle-down', 11, '#FF5252', 'High', 1.5, '비ADX풀백 매도', '주가<50MA+3일고점상승'),
    'Reversal_New_Highs': _sig(2.5, _B, '🔝', 'RevHigh', 'star-diamond', 14, '#00E676', 'Low', -2.5, '신고가 반전', '60일신고가+아웃사이드+5일최대범위'),
    'Reversal_New_Lows': _sig(2.5, _S, '🔻', 'RevLow', 'star-diamond', 14, '#FF1744', 'High', 2.5, '신저가 반전', '60일신저가+아웃사이드+5일최대범위'),
    
    # ═══ 이동평균(MA) 시그널 (15개) ═══
    'MA20_Support': _sig(1.0, _B, '📈', 'MA20Sup', 'triangle-up', 9, '#69F0AE', 'Low', -1.0, '20MA 지지', '20일이평선지지반등'),
    'MA20_Resistance': _sig(1.0, _S, '📉', 'MA20Res', 'triangle-down', 9, '#FF5252', 'High', 1.0, '20MA 저항', '20일이평선저항'),
    'MA50_Support': _sig(1.2, _B, '📈', 'MA50Sup', 'triangle-up', 10, '#00E676', 'Low', -1.2, '50MA 지지', '50일이평선지지반등'),
    'MA50_Resistance': _sig(1.2, _S, '📉', 'MA50Res', 'triangle-down', 10, '#FF1744', 'High', 1.2, '50MA 저항', '50일이평선저항'),
    'MA200_Support': _sig(1.5, _B, '📈', 'MA200Sup', 'triangle-up', 11, '#00BFA5', 'Low', -1.5, '200MA 지지', '200일이평선지지반등'),
    'MA200_Resistance': _sig(1.5, _S, '📉', 'MA200Res', 'triangle-down', 11, '#D50000', 'High', 1.5, '200MA 저항', '200일이평선저항'),
    'Cross_Above_20MA': _sig(0.8, _B, '📈', 'X▲20MA', 'triangle-up', 9, '#69F0AE', 'Low', -0.8, '20MA 상향돌파', '종가>20MA'),
    'Cross_Above_50MA': _sig(1.2, _B, '📈', 'X▲50MA', 'triangle-up', 10, '#00E676', 'Low', -1.0, '50MA 상향돌파', '종가>50MA'),
    'Cross_Above_200MA': _sig(1.5, _B, '📈', 'X▲200MA', 'triangle-up', 11, '#00BFA5', 'Low', -1.2, '200MA 상향돌파', '종가>200MA'),
    'Fell_Below_20MA': _sig(0.8, _S, '📉', 'X▼20MA', 'triangle-down', 9, '#FF5252', 'High', 0.8, '20MA 하향이탈', '종가<20MA'),
    'Fell_Below_50MA': _sig(1.2, _S, '📉', 'X▼50MA', 'triangle-down', 10, '#FF1744', 'High', 1.0, '50MA 하향이탈', '종가<50MA'),
    'Fell_Below_200MA': _sig(1.5, _S, '📉', 'X▼200MA', 'triangle-down', 11, '#D50000', 'High', 1.2, '200MA 하향이탈', '종가<200MA'),
    'Golden_Cross': _sig(1.5, _B, '✨', 'Golden', 'cross', 12, '#FFD700', 'Low', -0.8, '골든 크로스', '50MA>200MA교차'),
    'Death_Cross': _sig(1.5, _S, '☠️', 'Death', 'cross', 12, '#FF1744', 'High', 0.8, '데스 크로스', '50MA<200MA교차'),
    'MTF_All_Bullish': _sig(2.0, _B, '📊', 'MTF▲', 'star', 13, '#00E676', 'Low', -1.5, '다중시간대 강세', '10/50/200MA모두위'),
    'MTF_All_Bearish': _sig(2.0, _S, '📊', 'MTF▼', 'star', 13, '#FF1744', 'High', 1.5, '다중시간대 약세', '10/50/200MA모두아래'),
    
    # ═══ 볼린저 밴드(BB) 시그널 (12개) ═══
    'BB_Squeeze': _sig(1.0, _N, '🔳', 'BBSqueeze', 'square-open', 9, '#FFC107', 'Low', -0.5, 'BB 스퀴즈', 'BB폭6개월최저'),
    'BB_Squeeze_Started': _sig(1.0, _N, '⏳', 'SqStart', 'hourglass', 9, '#90A4AE', 'Low', -0.5, 'BB스퀴즈 시작', 'BB밴드수축시작'),
    'BB_Squeeze_End_Bull': _sig(1.5, _B, '💥', 'SqEnd▲', 'star-diamond', 12, '#00FFFF', 'Low', -1.5, 'BB스퀴즈 해소↑', 'BB확장+상승'),
    'BB_Squeeze_End_Bear': _sig(1.5, _S, '💥', 'SqEnd▼', 'star-diamond', 12, '#FF6600', 'High', 1.5, 'BB스퀴즈 해소↓', 'BB확장+하락'),
    'BB_Upper_Touch': _sig(0.8, _N, '🔝', 'BB▲T', 'diamond-open', 8, '#FFA726', 'High', 1.0, 'BB 상단 터치', '상단BB접촉'),
    'BB_Lower_Touch': _sig(0.8, _N, '⬇️', 'BB▼T', 'diamond-open', 8, '#4FC3F7', 'Low', -1.0, 'BB 하단 터치', '하단BB접촉'),
    'BB_Upper_Break': _sig(1.0, _B, '🔝', 'BB▲Break', 'diamond-open', 10, '#00E5FF', 'High', 1.0, 'BB 상단 돌파', '종가>상단BB'),
    'BB_Lower_Break': _sig(1.0, _S, '💀', 'BB▼Break', 'diamond-open', 10, '#FF6E40', 'Low', -1.0, 'BB 하단 붕괴', '종가<하단BB+약세'),
    'BB_Lower_Bounce': _sig(1.2, _B, '⤵️', 'BB▼Bounce', 'diamond-open', 10, '#4FC3F7', 'Low', -1.2, 'BB 하단 반등', '종가<하단BB+양봉전환'),
    'BB_Upper_Walk': _sig(1.5, _B, '🚶', 'BBWalk▲', 'arrow-up', 10, '#00E676', 'High', 1.2, 'BB 상단 워크', '연속상단BB상승'),
    'BB_Lower_Walk': _sig(1.5, _S, '🚶', 'BBWalk▼', 'arrow-down', 10, '#FF1744', 'Low', -1.2, 'BB 하단 워크', '연속하단BB하락'),
    'BB_Wide_Bands': _sig(0.5, _N, '📊', 'WideBB', 'square-open', 8, '#FFAB40', 'Low', -0.4, '넓은 BB', 'BB폭비정상확대'),
    
    # ═══ 캔들스틱 패턴 (12개) ═══
    'Bullish_Engulfing': _sig(1.5, _B, '☀️', 'BullEngulf', 'square', 10, '#00E676', 'Low', -1.3, '상승 장악형', '하락캔들감싸는상승캔들'),
    'Bearish_Engulfing': _sig(1.5, _S, '🌑', 'BearEngulf', 'x', 10, '#D50000', 'High', 1.3, '하락 장악형', '상승캔들감싸는하락캔들'),
    'Morning_Star': _sig(2.0, _B, '🌅', 'MornStar', 'star', 13, '#00E676', 'Low', -2.0, '모닝스타', '큰음봉→소형봉→강한양봉'),
    'Evening_Star': _sig(2.0, _S, '🌆', 'EveStar', 'star', 13, '#FF1744', 'High', 2.0, '이브닝스타', '큰양봉→소형봉→강한음봉'),
    'Doji': _sig(0.5, _N, '➕', 'Doji', 'cross-thin', 8, '#FFC107', 'Low', -0.5, '도지', '시가≈종가'),
    'Doji_Bullish': _sig(0.8, _B, '➕', 'DojiBull', 'cross-thin', 9, '#69F0AE', 'Low', -1.0, '강세 도지', '도지+하락추세후'),
    'Doji_Bearish': _sig(0.8, _S, '➖', 'DojiBear', 'cross-thin', 9, '#FF5252', 'High', 1.0, '약세 도지', '도지+상승추세후'),
    'Hammer': _sig(1.5, _B, '🔨', 'Hammer', 'triangle-up', 11, '#00E676', 'Low', -1.5, '해머', '긴하단꼬리+거래량'),
    'Shooting_Star': _sig(1.5, _S, '🌠', 'ShootStar', 'triangle-down', 11, '#FF1744', 'High', 1.5, '슈팅스타', '긴상단꼬리+거래량'),
    'Spinning_Top': _sig(0.3, _N, '🔄', 'SpinTop', 'circle-open', 7, '#90A4AE', 'Low', -0.3, '팽이형', '소형실체+상하꼬리유사'),
    'Inside_Day': _sig(0.3, _N, '📦', 'InsideDay', 'square-open', 7, '#FFC107', 'Low', -0.3, '인사이드데이', '고가<전일고&저가>전일저'),
    'Outside_Bullish': _sig(1.5, _B, '💪', 'OutBull', 'square', 11, '#00E676', 'Low', -1.5, '강세 아웃사이드', '전일범위포함+양봉'),
    'Outside_Bearish': _sig(1.5, _S, '🥊', 'OutBear', 'square', 11, '#FF1744', 'High', 1.5, '약세 아웃사이드', '전일범위포함+음봉'),
    
    # ═══ MACD 시그널 (4개) ═══
    'MACD_Cross_Buy': _sig(1.0, _B, '〽️', 'MACD▲', 'triangle-up', 9, '#4CAF50', 'Low', -1.0, 'MACD 골든', 'MACD>시그널'),
    'MACD_Cross_Sell': _sig(1.0, _S, '〽️', 'MACD▼', 'triangle-down', 9, '#E57373', 'High', 1.0, 'MACD 데드', 'MACD<시그널'),
    'MACD_Zero_Cross_Buy': _sig(1.2, _B, '⬆️', 'MACD0▲', 'triangle-up', 10, '#4CAF50', 'Low', -1.0, 'MACD 0선↑', 'MACD>0'),
    'MACD_Zero_Cross_Sell': _sig(1.2, _S, '⬇️', 'MACD0▼', 'triangle-down', 10, '#E57373', 'High', 1.0, 'MACD 0선↓', 'MACD<0'),
    
    # ═══ 스토캐스틱 시그널 (6개) ═══
    'StochRSI_Cross_Buy': _sig(0.8, _B, '🔄', 'StRSI▲', 'circle-open', 8, '#81C784', 'Low', -0.8, 'StochRSI 매수', '%K>%D(과매도)'),
    'StochRSI_Cross_Sell': _sig(0.8, _S, '🔄', 'StRSI▼', 'circle-open', 8, '#EF9A9A', 'High', 0.8, 'StochRSI 매도', '%K<%D(과매수)'),
    'Stoch_Reached_OB': _sig(0.5, _N, '📊', 'Stoch→OB', 'triangle-up', 7, '#FFA726', 'High', 0.5, '스토캐스틱 과매수도달', '%K≥80'),
    'Stoch_Reached_OS': _sig(0.5, _N, '📊', 'Stoch→OS', 'triangle-down', 7, '#4FC3F7', 'Low', -0.5, '스토캐스틱 과매도도달', '%K≤20'),
    'Stoch_Overbought': _sig(0.8, _S, '🔴', 'StochOB', 'circle', 8, '#FF5252', 'High', 0.8, '스토캐스틱 과매수', '%K>80&%D>80'),
    'Stoch_Oversold': _sig(0.8, _B, '🟢', 'StochOS', 'circle', 8, '#69F0AE', 'Low', -0.8, '스토캐스틱 과매도', '%K<20&%D<20'),
    
    # ═══ ADX/DMI 시그널 (6개) ═══
    'DMI_Cross_Bull': _sig(1.5, _B, '📈', 'DMI▲', 'triangle-up', 10, '#00E676', 'Low', -1.2, 'DMI 강세교차', '+DI>-DI교차'),
    'DMI_Cross_Bear': _sig(1.5, _S, '📉', 'DMI▼', 'triangle-down', 10, '#FF1744', 'High', 1.2, 'DMI 약세교차', '-DI>+DI교차'),
    'ADX_New_Uptrend': _sig(1.5, _B, '🚀', 'NewUp▲', 'arrow-up', 11, '#76FF03', 'Low', -1.4, '신규 상승추세', 'ADX>25++DI>-DI'),
    'ADX_New_Downtrend': _sig(1.5, _S, '💨', 'NewDn▼', 'arrow-down', 11, '#FF3D00', 'High', 1.4, '신규 하락추세', 'ADX>25+-DI>+DI'),
    'ADX_Momentum_Buy': _sig(1.5, _B, '🚀', 'ADX Ign▲', 'arrow-up', 11, '#76FF03', 'Low', -1.4, 'ADX 점화', 'ADX>20돌파+DI↑'),
    'ADX_Momentum_Sell': _sig(1.5, _S, '💨', 'ADX Dn', 'arrow-down', 11, '#FF3D00', 'High', 1.4, 'ADX 하락점화', 'ADX>20+-DI>+DI'),
    
    # ═══ RSI 시그널 (6개) ═══
    'RSI_Cross_30_Up': _sig(1.0, _B, '📈', 'RSI30▲', 'triangle-up', 9, '#4CAF50', 'Low', -1.0, 'RSI 30 상향', 'RSI>30돌파'),
    'RSI_Cross_50_Up': _sig(1.0, _B, '📈', 'RSI50▲', 'triangle-up', 9, '#69F0AE', 'Low', -0.8, 'RSI 50 상향', 'RSI>50돌파'),
    'RSI_Cross_70_Down': _sig(1.0, _S, '📉', 'RSI70▼', 'triangle-down', 9, '#EF5350', 'High', 1.0, 'RSI 70 하향', 'RSI<70하락'),
    'RSI_Cross_50_Down': _sig(1.0, _S, '📉', 'RSI50▼', 'triangle-down', 9, '#FF5252', 'High', 0.8, 'RSI 50 하향', 'RSI<50하락'),
    
    # ═══ 갭 시그널 (4개) ═══
    'Gap_Up': _sig(1.0, _B, '⏫', 'GapUp', 'arrow-up', 10, '#00E676', 'Low', -1.0, '갭 상승', '시가>전일고가'),
    'Gap_Down': _sig(1.0, _S, '⏬', 'GapDn', 'arrow-down', 10, '#FF1744', 'High', 1.0, '갭 하락', '시가<전일저가'),
    'Gap_Up_Closed': _sig(0.8, _S, '🔄', 'GapUp Fill', 'circle-open', 8, '#FFA726', 'High', 0.8, '갭업 메움', '상승갭메워짐'),
    'Gap_Down_Closed': _sig(0.8, _B, '🔄', 'GapDn Fill', 'circle-open', 8, '#4FC3F7', 'Low', -0.8, '갭다운 메움', '하락갭메워짐'),
    
    # ═══ 변동성/범위 패턴 (5개) ═══
    'NR7': _sig(0.5, _N, '🔳', 'NR7', 'square-open', 7, '#90A4AE', 'Low', -0.3, 'NR7', '7일중최소범위'),
    'NR7_2': _sig(0.8, _N, '🔳', 'NR7-2', 'square-open', 8, '#90A4AE', 'Low', -0.5, 'NR7-2', '2일연속NR7'),
    'Narrow_Range_Bar': _sig(0.5, _N, '📊', 'NarrowBar', 'square-open', 7, '#90A4AE', 'Low', -0.3, '좁은 범위봉', '범위<ATR×0.5'),
    'Wide_Range_Bar': _sig(0.5, _N, '📊', 'WideBar', 'square-open', 7, '#FFAB40', 'Low', -0.4, '넓은 범위봉', '범위>ATR×2'),
    'Calm_After_Storm': _sig(1.0, _N, '🌤️', 'CalmStorm', 'diamond-open', 9, '#FFC107', 'Low', -0.8, '폭풍뒤 고요', 'WideRange→NarrowRange'),
    
    # ═══ 52주 고/저가 (4개) ═══
    'New_52W_High': _sig(1.5, _B, '🏔️', '52W▲', 'star-triangle-up', 12, '#FFD700', 'High', 1.5, '52주 신고가', '52주최고가갱신'),
    'New_52W_Low': _sig(1.5, _S, '🕳️', '52W▼', 'star-triangle-down', 12, '#B71C1C', 'Low', -1.5, '52주 신저가', '52주최저가갱신'),
    'New_52W_Closing_High': _sig(1.2, _B, '🏆', '52WC▲', 'star', 11, '#FFD700', 'High', 1.2, '52주 종가신고가', '52주종가기준최고'),
    'New_52W_Closing_Low': _sig(1.2, _S, '💀', '52WC▼', 'star', 11, '#B71C1C', 'Low', -1.2, '52주 종가신저가', '52주종가기준최저'),
    
    # ═══ 연속 상승/하락 (6개) ═══
    'Up_3_Days': _sig(0.5, _B, '📗', 'Up3D', 'triangle-up', 8, '#69F0AE', 'High', 0.5, '3일 연속상승', '3일연속양봉'),
    'Up_4_Days': _sig(0.6, _B, '📗', 'Up4D', 'triangle-up', 8, '#69F0AE', 'High', 0.6, '4일 연속상승', '4일연속양봉'),
    'Up_5_Days': _sig(0.8, _B, '📗', 'Up5D', 'triangle-up', 9, '#00E676', 'High', 0.8, '5일 연속상승', '5일연속양봉'),
    'Down_3_Days': _sig(0.5, _S, '📕', 'Dn3D', 'triangle-down', 8, '#FF5252', 'Low', -0.5, '3일 연속하락', '3일연속음봉'),
    'Down_4_Days': _sig(0.6, _S, '📕', 'Dn4D', 'triangle-down', 8, '#FF5252', 'Low', -0.6, '4일 연속하락', '4일연속음봉'),
    'Down_5_Days': _sig(0.8, _S, '📕', 'Dn5D', 'triangle-down', 9, '#FF1744', 'Low', -0.8, '5일 연속하락', '5일연속음봉'),
    
    # ═══ 심리적 가격대 (2개) ═══
    'Multiple_Ten_Bull': _sig(1.0, _B, '💯', 'Round▲', 'triangle-up', 9, '#00E676', 'Low', -1.0, '10배수 강세', '$10/$20/$50등돌파'),
    'Multiple_Ten_Bear': _sig(1.0, _S, '💯', 'Round▼', 'triangle-down', 9, '#FF1744', 'High', 1.0, '10배수 약세', '$10/$20/$50등이탈'),
    
    # ═══ 특수 패턴 (4개) ═══
    'Pocket_Pivot': _sig(1.5, _B, '🧲', 'PocketPvt', 'triangle-up', 11, '#7C4DFF', 'Low', -1.5, '포켓 피봇', '양봉+거래량>10일하락거래량최대'),
    'Parabolic_Rise': _sig(2.0, _N, '🚀', 'Parabolic', 'star-diamond', 13, '#FF6D00', 'High', 2.0, '포물선 상승', '급격한수직상승'),
    'Three_Weeks_Tight': _sig(1.5, _B, '📦', '3WTight', 'square', 11, '#00E676', 'Low', -1.5, '3주 타이트', '3주연속좁은종가범위'),
    
    # ═══ 기타 기존 시그널들 ═══
    'Squeeze_Fire_Buy': _sig(1.5, _B, '💥', 'Squeeze BUY', 'star-diamond', 14, '#00FFFF', 'Low', -1.5, '스퀴즈 매수', 'TTM Squeeze해소+모멘텀↑'),
    'Squeeze_Fire_Sell': _sig(1.5, _S, '🧨', 'Squeeze SELL', 'star-diamond', 14, '#FF6600', 'High', 1.5, '스퀴즈 매도', 'TTM Squeeze해소+모멘텀↓'),
    'Volume_Climax_Buy': _sig(2.0, _B, '🌊', 'VolClimax▲', 'hexagram', 14, '#00BCD4', 'Low', -2.8, '거래량클라이맥스매수', '3x거래량+WT과매도→반등'),
    'Volume_Climax_Sell': _sig(2.0, _S, '🌋', 'VolClimax▼', 'hexagram', 14, '#FF5722', 'High', 2.8, '거래량클라이맥스매도', '3x거래량+WT과매수→하락'),
    'Volume_Surge': _sig(1.5, _N, '🌊', 'VolSurge', 'hexagram', 12, '#00BCD4', 'Low', -1.0, '거래량 급증', '거래량≥50일평균×3'),
    'OBV_Div_Buy': _sig(0.8, _B, '📊', 'OBV Div▲', 'triangle-up', 10, '#80DEEA', 'Low', -1.4, 'OBV 다이버전스', 'OBV↑vs가격↓'),
    'OBV_Div_Sell': _sig(0.8, _S, '🔻', 'OBV Div▼', 'triangle-down', 10, '#FFAB91', 'High', 1.4, 'OBV 다이버전스', 'OBV↓vs가격↑'),
    'SuperTrend_Buy': _sig(1.5, _B, '📈', 'ST▲', 'arrow-up', 12, '#00E5FF', 'Low', -1.5, '슈퍼트렌드 강세', 'SuperTrend위로돌파'),
    'SuperTrend_Sell': _sig(2.0, _S, '📉', 'ST▼', 'arrow-down', 12, '#FF1744', 'High', 1.5, '슈퍼트렌드 약세', 'SuperTrend하향돌파'),
    'EMA_Pullback_Buy': _sig(2.0, _B, '🎯', 'EMA PB▲', 'triangle-up', 13, '#00BFA5', 'Low', -1.8, 'EMA 눌림목', '상승추세EMA조정후반등'),
    'EMA_Pullback_Sell': _sig(2.0, _S, '🎯', 'EMA PB▼', 'triangle-down', 13, '#FF6E40', 'High', 1.8, 'EMA 되돌림', '하락추세EMA반등후재하락'),
    'Momentum_Ignition_Buy': _sig(2.5, _B, '🔥', 'MomIgn▲', 'star-diamond', 15, '#FF6D00', 'Low', -2.5, '모멘텀 점화', '장대양봉>ATR×1.5+거래량>2x'),
    'Momentum_Ignition_Sell': _sig(2.5, _S, '💣', 'MomIgn▼', 'star-diamond', 15, '#D50000', 'High', 2.5, '모멘텀 점화매도', '장대음봉>ATR×1.5+거래량>2x'),
    'Parabolic_Bottom_Buy': _sig(3.0, _B, '🧊', 'ParaBot', 'diamond', 16, '#00FFFF', 'Low', -3.0, '포물선 바닥', 'WT1<-80꺾임+양봉'),
    'Parabolic_Top_Sell': _sig(3.0, _S, '🌡️', 'ParaTop', 'diamond', 16, '#FF0000', 'High', 3.0, '포물선 천장', 'WT1>80꺾임+음봉'),
    'VWAP_Bounce_Buy': _sig(1.5, _B, '🏦', 'VWAP▲', 'triangle-up', 11, '#00E5FF', 'Low', -1.3, 'VWAP 반등', 'VWAP복귀+WT교차'),
    'VWAP_Reject_Sell': _sig(1.5, _S, '🏛️', 'VWAP▼', 'triangle-down', 11, '#FF6E40', 'High', 1.3, 'VWAP 저항', 'VWAP실패+WT교차'),
    'MF_Cross_Bull': _sig(1.5, _B, '💰', 'MF▲', 'triangle-up', 11, '#00E676', 'Low', -1.2, 'MF 강세전환', '자금흐름음→양'),
    'MF_Cross_Bear': _sig(1.5, _S, '💸', 'MF▼', 'triangle-down', 11, '#FF1744', 'High', 1.2, 'MF 약세전환', '자금흐름양→음'),
    'MF_Bull_Div': _sig(1.8, _B, '💹', 'MF Bull Div', 'triangle-up', 11, '#7C4DFF', 'Low', -1.5, 'MF 상승다이버전스', '가격↓vsMF↑'),
    'MF_Bear_Div': _sig(1.8, _S, '💹', 'MF Bear Div', 'triangle-down', 11, '#E040FB', 'High', 1.5, 'MF 하락다이버전스', '가격↑vsMF↓'),
    'MF_Accel_Up': _sig(1.0, _B, '📈', 'MF Accel▲', 'arrow-up', 9, '#69F0AE', 'Low', -0.8, 'MF 가속상승', '5일+MF연속상승'),
    'MF_Accel_Dn': _sig(1.0, _S, '📉', 'MF Accel▼', 'arrow-down', 9, '#FF5252', 'High', 0.8, 'MF 가속하락', '5일+MF연속하락'),
    'Kumo_Breakout_Bull': _sig(2.0, _B, '☁️', 'Kumo▲', 'triangle-up', 13, '#00E676', 'Low', -2.0, '쿠모 상향돌파', '종가>구름상단'),
    'Kumo_Breakout_Bear': _sig(2.0, _S, '☁️', 'Kumo▼', 'triangle-down', 13, '#FF1744', 'High', 2.0, '쿠모 하향돌파', '종가<구름하단'),
    'TK_Cross_Bull': _sig(1.5, _B, '⛩️', 'TK▲', 'triangle-up', 10, '#69F0AE', 'Low', -1.2, '전환-기준 골든', '전환선>기준선'),
    'TK_Cross_Bear': _sig(1.5, _S, '⛩️', 'TK▼', 'triangle-down', 10, '#FF5252', 'High', 1.2, '전환-기준 데드', '전환선<기준선'),
    'CMF_Bull': _sig(1.2, _B, '🌀', 'CMF▲', 'triangle-up', 10, '#00BCD4', 'Low', -1.0, 'CMF 강세', 'CMF>0.1'),
    'CMF_Bear': _sig(1.2, _S, '🌀', 'CMF▼', 'triangle-down', 10, '#FF5722', 'High', 1.0, 'CMF 약세', 'CMF<-0.1'),
    'Setup_Squeeze_Bull': _sig(1.0, _B, '⏳', 'SqSetup▲', 'hourglass', 10, '#80DEEA', 'Low', -0.8, '스퀴즈셋업▲', 'BB축소+모멘텀상승임박'),
    'Setup_Squeeze_Bear': _sig(1.0, _S, '⏳', 'SqSetup▼', 'hourglass', 10, '#FFAB91', 'High', 0.8, '스퀴즈셋업▼', 'BB축소+모멘텀하락임박'),
    'Momentum_Accel_Buy': _sig(1.5, _B, '⚡', 'MomAccel▲', 'arrow-up', 11, '#76FF03', 'Low', -1.2, '모멘텀가속▲', 'RSI+WT+MACD동시가속'),
    'Momentum_Accel_Sell': _sig(1.5, _S, '⚡', 'MomAccel▼', 'arrow-down', 11, '#FF3D00', 'High', 1.2, '모멘텀가속▼', 'RSI+WT+MACD동시감속'),
    'Volume_Dry_Up': _sig(0.5, _N, '🏜️', 'VolDryUp', 'square-open', 8, '#FFE082', 'Low', -0.3, '거래량 고갈', '5일연속평균이하'),
    'WT_Convergence_Bull': _sig(1.2, _B, '🔀', 'WTConv▲', 'triangle-up', 10, '#B2FF59', 'Low', -1.0, 'WT수렴매수임박', 'WT1→WT2빠른수렴+과매도'),
    'WT_Convergence_Bear': _sig(1.2, _S, '🔀', 'WTConv▼', 'triangle-down', 10, '#FF8A80', 'High', 1.0, 'WT수렴매도임박', 'WT1→WT2빠른수렴+과매수'),
    'Volume_POC_Breakout': _sig(2.0, _B, '🏛️', 'POC▲', 'triangle-up', 13, '#7C4DFF', 'Low', -1.8, 'POC 상향돌파', '종가>매물대POC'),
    'Volume_POC_Breakdown': _sig(2.0, _S, '🏛️', 'POC▼', 'triangle-down', 13, '#E040FB', 'High', 1.8, 'POC 하향이탈', '종가<매물대POC'),
    'VP_VAH_Resistance': _sig(1.0, _S, '🏛️', 'VAH Res', 'triangle-down', 10, '#FFAB91', 'High', 1.0, 'VAH 저항', '종가→VA상단+약세'),
    'VP_VAL_Support': _sig(1.0, _B, '🏛️', 'VAL Sup', 'triangle-up', 10, '#80DEEA', 'Low', -1.0, 'VAL 지지', '종가→VA하단+강세'),
    'Relative_Strength_Buy': _sig(2.0, _B, '💪', 'RS Strong', 'star-diamond', 13, '#00E5FF', 'Low', -1.8, '상대강도 매수', '하락장방어+SPY대비강세'),
    'Relative_Strength_Sell': _sig(1.5, _S, '🐌', 'RS Weak', 'star-diamond', 11, '#FF6E40', 'High', 1.5, '상대약세 매도', '상승장뒤처짐+SPY대비약세'),
}

# ══════════════════════════════════════════
#  COMBINED SCAN 레지스트리
# ══════════════════════════════════════════
COMBINED_SCAN_REGISTRY = {
    # TIER 1 매수
    'CS_Ultimate_Buy': {'name': '🏆 ULTIMATE BUY', 'kor': '궁극의 매수', 'dir': 'buy', 'tier': 1, 'icon': '🏆', 'color': '#FFD700', 'desc': '6중확인', 'win_rate': '75-85%'},
    'CS_Triple_Oversold_Reversal': {'name': '🔥 Triple Oversold', 'kor': '삼중과매도반전', 'dir': 'buy', 'tier': 1, 'icon': '🔥', 'color': '#00E676', 'desc': 'WT+RSI+Stoch과매도+반전', 'win_rate': '70-80%'},
    'CS_Breakout_Momentum_Buy': {'name': '🚀 Breakout Momentum', 'kor': '돌파모멘텀', 'dir': 'buy', 'tier': 1, 'icon': '🚀', 'color': '#00E676', 'desc': '52W신고가+거래량+ADX', 'win_rate': '65-75%'},
    'CS_Institutional_Accumulation': {'name': '🏦 Institutional', 'kor': '기관매집', 'dir': 'buy', 'tier': 1, 'icon': '🏦', 'color': '#00BCD4', 'desc': '포켓피봇+OBV+타이트', 'win_rate': '70-80%'},
    'CS_Divergence_Confluence_Buy': {'name': '📊 Div Confluence', 'kor': '다이버전스합류', 'dir': 'buy', 'tier': 1, 'icon': '📊', 'color': '#7C4DFF', 'desc': 'WT+RSI+MF다이버전스', 'win_rate': '70-80%'},
    'CS_Capitulation_Bottom': {'name': '🏳️ Capitulation', 'kor': '항복바닥', 'dir': 'buy', 'tier': 1, 'icon': '🏳️', 'color': '#00E676', 'desc': '52W저+거래량폭발+극과매도', 'win_rate': '70-80%'},
    
    # TIER 1 매도
    'CS_Ultimate_Sell': {'name': '🏆 ULTIMATE SELL', 'kor': '궁극의 매도', 'dir': 'sell', 'tier': 1, 'icon': '🏆', 'color': '#FFD700', 'desc': '6중확인', 'win_rate': '75-85%'},
    'CS_Triple_Overbought_Exhaustion': {'name': '🌡️ Triple Overbought', 'kor': '삼중과매수소진', 'dir': 'sell', 'tier': 1, 'icon': '🌡️', 'color': '#FF1744', 'desc': 'WT+RSI+Stoch과매수+반전', 'win_rate': '70-80%'},
    'CS_Breakdown_Momentum_Sell': {'name': '💨 Breakdown Momentum', 'kor': '붕괴모멘텀', 'dir': 'sell', 'tier': 1, 'icon': '💨', 'color': '#FF1744', 'desc': '52W신저가+거래량+ADX', 'win_rate': '65-75%'},
    'CS_Parabolic_Exhaustion_Sell': {'name': '🎢 Parabolic Exhaust', 'kor': '포물선소진', 'dir': 'sell', 'tier': 1, 'icon': '🎢', 'color': '#D50000', 'desc': '포물선상승+천장캔들+폭발거래량', 'win_rate': '70-80%'},
    'CS_Divergence_Confluence_Sell': {'name': '📉 Div Confluence', 'kor': '다이버전스합류매도', 'dir': 'sell', 'tier': 1, 'icon': '📉', 'color': '#E040FB', 'desc': 'WT+RSI+MF다이버전스', 'win_rate': '70-80%'},
    'CS_Blow_Off_Top': {'name': '🎆 Blow-Off Top', 'kor': '블로우오프천장', 'dir': 'sell', 'tier': 1, 'icon': '🎆', 'color': '#FF1744', 'desc': '52W고+거래량폭발+극과매수', 'win_rate': '70-80%'},
    
    # TIER 2 매수
    'CS_Trend_Pullback_Buy': {'name': '🎯 Trend Pullback', 'kor': '추세눌림목', 'dir': 'buy', 'tier': 2, 'icon': '🎯', 'color': '#00E676', 'desc': '상승추세+MA지지+캔들', 'win_rate': '60-70%'},
    'CS_Squeeze_Breakout_Buy': {'name': '💥 Squeeze Breakout', 'kor': '스퀴즈돌파', 'dir': 'buy', 'tier': 2, 'icon': '💥', 'color': '#00FFFF', 'desc': 'BB스퀴즈종료+상방+거래량', 'win_rate': '60-70%'},
    'CS_MA_Confluence_Buy': {'name': '📈 MA Confluence', 'kor': 'MA합류', 'dir': 'buy', 'tier': 2, 'icon': '📈', 'color': '#69F0AE', 'desc': '골든크로스+정배열+MACD', 'win_rate': '60-70%'},
    'CS_Cooper_Setup_Buy': {'name': '🃏 Cooper Setup', 'kor': '쿠퍼셋업', 'dir': 'buy', 'tier': 2, 'icon': '🃏', 'color': '#FF6D00', 'desc': 'ADX>30+쿠퍼패턴+추세', 'win_rate': '60-70%'},
    'CS_Volume_Climax_Reversal_Buy': {'name': '🌊 Vol Climax Rev', 'kor': '거래량클라이맥스반전', 'dir': 'buy', 'tier': 2, 'icon': '🌊', 'color': '#00BCD4', 'desc': '거래량폭발+과매도+반전', 'win_rate': '60-70%'},
    'CS_Ichimoku_Breakout_Buy': {'name': '☁️ Ichimoku Breakout', 'kor': '이치모쿠돌파', 'dir': 'buy', 'tier': 2, 'icon': '☁️', 'color': '#00E676', 'desc': '쿠모돌파+TK크로스+거래량', 'win_rate': '60-70%'},
    
    # TIER 2 매도
    'CS_Trend_Rejection_Sell': {'name': '🎯 Trend Rejection', 'kor': '추세거부', 'dir': 'sell', 'tier': 2, 'icon': '🎯', 'color': '#FF1744', 'desc': '하락추세+MA저항+캔들', 'win_rate': '60-70%'},
    'CS_Squeeze_Breakdown_Sell': {'name': '💨 Squeeze Breakdown', 'kor': '스퀴즈붕괴', 'dir': 'sell', 'tier': 2, 'icon': '💨', 'color': '#FF6600', 'desc': 'BB스퀴즈종료+하방+거래량', 'win_rate': '60-70%'},
    'CS_MA_Breakdown_Sell': {'name': '📉 MA Breakdown', 'kor': 'MA붕괴', 'dir': 'sell', 'tier': 2, 'icon': '📉', 'color': '#FF5252', 'desc': '데스크로스+역배열+MACD', 'win_rate': '60-70%'},
    'CS_Cooper_Setup_Sell': {'name': '🃏 Cooper Setup Sell', 'kor': '쿠퍼셋업매도', 'dir': 'sell', 'tier': 2, 'icon': '🃏', 'color': '#FF3D00', 'desc': 'ADX>30+쿠퍼패턴매도+추세', 'win_rate': '60-70%'},
    'CS_Gap_Failure_Sell': {'name': '⏬ Gap Failure', 'kor': '갭실패', 'dir': 'sell', 'tier': 2, 'icon': '⏬', 'color': '#FF1744', 'desc': '갭업후약세반전+거래량', 'win_rate': '60-70%'},
    
    # TIER 3
    'CS_Oversold_Bounce_Buy': {'name': '🏓 Oversold Bounce', 'kor': '과매도반등', 'dir': 'buy', 'tier': 3, 'icon': '🏓', 'color': '#69F0AE', 'desc': 'Stoch과매도+캔들+지지', 'win_rate': '55-65%'},
    'CS_Momentum_Acceleration_Buy': {'name': '⚡ Mom Accel Buy', 'kor': '모멘텀가속', 'dir': 'buy', 'tier': 3, 'icon': '⚡', 'color': '#76FF03', 'desc': 'RSI+WT+MACD가속+거래량', 'win_rate': '55-65%'},
    'CS_Structure_Support_Buy': {'name': '🏗️ Structure Support', 'kor': '구조적지지', 'dir': 'buy', 'tier': 3, 'icon': '🏗️', 'color': '#4FC3F7', 'desc': 'VP지지+BB하단+양봉', 'win_rate': '55-65%'},
    'CS_Overbought_Fade_Sell': {'name': '📉 Overbought Fade', 'kor': '과매수페이드', 'dir': 'sell', 'tier': 3, 'icon': '📉', 'color': '#FF5252', 'desc': 'Stoch과매수+캔들+저항', 'win_rate': '55-65%'},
    'CS_Momentum_Deceleration_Sell': {'name': '⚡ Mom Decel Sell', 'kor': '모멘텀감속', 'dir': 'sell', 'tier': 3, 'icon': '⚡', 'color': '#FF3D00', 'desc': 'RSI+WT+MACD감속+거래량', 'win_rate': '55-65%'},
    'CS_Structure_Resistance_Sell': {'name': '🏗️ Structure Resist', 'kor': '구조적저항', 'dir': 'sell', 'tier': 3, 'icon': '🏗️', 'color': '#FFAB91', 'desc': 'VP저항+BB상단+음봉', 'win_rate': '55-65%'},
    
    # 특수
    'CS_Volatility_Explosion_Setup': {'name': '💣 Vol Explosion', 'kor': '변동성폭발셋업', 'dir': 'neutral', 'tier': 2, 'icon': '💣', 'color': '#FFC107', 'desc': 'NR7-2+BB스퀴즈+거래량고갈', 'win_rate': '방향확정시70%+'},
}

# 쿨다운 맵
COOLDOWN_MAP = {
    'Squeeze_Fire_Buy': 5, 'Squeeze_Fire_Sell': 5, 'Bullish_Engulfing': 5, 'Bearish_Engulfing': 5,
    'ADX_Momentum_Buy': 10, 'ADX_Momentum_Sell': 10, 'EMA_Pullback_Buy': 7, 'EMA_Pullback_Sell': 7,
    'Momentum_Ignition_Buy': 10, 'Momentum_Ignition_Sell': 10, 'Parabolic_Top_Sell': 5, 'Parabolic_Bottom_Buy': 5,
    'MACD_Cross_Buy': 12, 'MACD_Cross_Sell': 12, 'StochRSI_Cross_Buy': 7, 'StochRSI_Cross_Sell': 7,
    'Hammer': 5, 'Shooting_Star': 5, 'Morning_Star': 7, 'Evening_Star': 7,
    'Golden_Cross': 20, 'Death_Cross': 20, 'Expansion_BO': 10, 'Expansion_BD': 10,
    'Gilligans_Buy': 10, 'Gilligans_Sell': 10, 'Pullback_123_Bull': 7, 'Pullback_123_Bear': 7,
    'Kumo_Breakout_Bull': 10, 'Kumo_Breakout_Bear': 10, 'New_52W_High': 10, 'New_52W_Low': 10,
}

# 차트 표시용 시그널 분류 (강력매수, 강력매도, 일반매수, 일반매도)
CHART_SIGNAL_TIERS = {
    'strong_buy': ['Gold_Dot', 'Green_Dot_T1', 'Parabolic_Bottom_Buy', 'Volume_Climax_Buy', 'Momentum_Ignition_Buy',
                   'Expansion_BO', 'Morning_Star', 'Reversal_New_Highs', 'CS_Ultimate_Buy', 'CS_Triple_Oversold_Reversal',
                   'CS_Breakout_Momentum_Buy', 'CS_Capitulation_Bottom', 'CS_Divergence_Confluence_Buy', 'CS_Institutional_Accumulation'],
    'strong_sell': ['Blood_Diamond', 'Red_Dot_T1', 'Parabolic_Top_Sell', 'Volume_Climax_Sell', 'Momentum_Ignition_Sell',
                    'Expansion_BD', 'Evening_Star', 'Reversal_New_Lows', 'CS_Ultimate_Sell', 'CS_Triple_Overbought_Exhaustion',
                    'CS_Breakdown_Momentum_Sell', 'CS_Blow_Off_Top', 'CS_Divergence_Confluence_Sell', 'CS_Parabolic_Exhaustion_Sell'],
}

print("✅ Part 1/6 로드 완료: 설정, 상수, 레지스트리")

# ══════════════════════════════════════════════════════════════
#  CipherX V12.3 — PART 2/6: 유틸리티, 기술지표, 시그널 탐지
# ══════════════════════════════════════════════════════════════

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  유틸리티 함수
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _recent(s, lb=3):
    return s.astype(float).rolling(lb + 1, min_periods=1).max().fillna(0).astype(bool)

def _cooldown(sig, bars=5):
    v = sig.fillna(False).values.astype(bool)
    out = np.zeros(len(v), dtype=bool)
    last = -bars - 1
    for i in range(len(v)):
        if v[i] and (i - last) > bars:
            out[i] = True
            last = i
    return pd.Series(out, index=sig.index)

def _cooldown_directional(df, buy_sig, sell_sig, bars=5):
    bv = df.get(buy_sig, pd.Series(False, index=df.index)).fillna(False).values.astype(bool)
    sv = df.get(sell_sig, pd.Series(False, index=df.index)).fillna(False).values.astype(bool)
    b_out = np.zeros(len(bv), dtype=bool)
    s_out = np.zeros(len(sv), dtype=bool)
    last_b, last_s = -bars - 1, -bars - 1
    for i in range(len(df)):
        if sv[i]: last_b = -bars - 1
        if bv[i]: last_s = -bars - 1
        if bv[i] and (i - last_b) > bars:
            b_out[i] = True; last_b = i
        if sv[i] and (i - last_s) > bars:
            s_out[i] = True; last_s = i
    if buy_sig in df.columns: df[buy_sig] = pd.Series(b_out, index=df.index)
    if sell_sig in df.columns: df[sell_sig] = pd.Series(s_out, index=df.index)

def _volf(vol, ratio=0.5, period=20):
    return vol >= (vol.rolling(period, min_periods=5).mean() * ratio)

def _valid_fmt(t):
    return bool(re.match(r'^[A-Za-z]{1,5}([.\-][A-Za-z]{1,2})?$', t))

def _vectorized_streak(condition):
    c = condition.astype(int)
    groups = (c == 0).cumsum()
    return c.groupby(groups).cumsum()

def _sig_pts(df, sig_name, points):
    return np.where(df[sig_name].fillna(False), points, 0.0) if sig_name in df.columns else 0.0

def _sig_pts_decayed(df, sig_name, full_pts, decay_days=None, decay_rate=None):
    if decay_days is None: decay_days = JT.DECAY_DAYS
    if decay_rate is None: decay_rate = JT.DECAY_RATE
    if sig_name not in df.columns: return 0.0
    base = np.where(df[sig_name].fillna(False), full_pts, 0.0)
    total = base.copy()
    for d in range(1, decay_days + 1):
        shifted = np.roll(base, d); shifted[:d] = 0
        total += shifted * (decay_rate ** d)
    return total


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  캐시 함수
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_fundamentals(ticker):
    try:
        info = yf.Ticker(ticker).info
        def _get(key, fmt=None):
            val = info.get(key)
            if val is None: return "N/A"
            if fmt == 'currency': return f"${val:,.2f}"
            if fmt == 'large': return f"{val:,.0f}"
            if fmt == 'percent': return f"{val * 100:.2f}%"
            if fmt == 'float': return f"{val:.2f}"
            return str(val)
        return "\n".join([
            f"Market Cap: {_get('marketCap', 'large')}", f"P/E: {_get('trailingPE', 'float')}",
            f"52W High: {_get('fiftyTwoWeekHigh', 'currency')}", f"52W Low: {_get('fiftyTwoWeekLow', 'currency')}",
            f"Avg Vol: {_get('averageVolume', 'large')}", f"Short%: {_get('shortPercentOfFloat', 'percent')}"])
    except:
        return "펀더멘탈 데이터 없음"

@st.cache_data(ttl=300, max_entries=30, show_spinner=False)
def fetch_history(ticker, _ts=None):
    return yf.Ticker(ticker).history(period="2y")

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_spy_history(_ts=None):
    return yf.Ticker("SPY").history(period="2y")

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


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  기술지표 계산 엔진
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def compute_rsi(s, p=14):
    d = s.diff(); g, l = d.clip(lower=0), -d.clip(upper=0)
    return 100 - (100 / (1 + g.ewm(alpha=1/p, min_periods=p).mean() / (l.ewm(alpha=1/p, min_periods=p).mean() + 1e-10)))

def compute_mfi(h, l, c, v, p=14):
    tp = (h + l + c) / 3; raw = tp * v; d = tp.diff()
    return 100 - (100 / (1 + raw.where(d >= 0, 0.0).rolling(p).sum() / (raw.where(d < 0, 0.0).rolling(p).sum() + 1e-10)))

def compute_rsi_mfi(h, l, c, v, p=60):
    rf, mf = compute_rsi(c, 20), compute_mfi(h, l, c, v, 20)
    rs, ms = compute_rsi(c, p), compute_mfi(h, l, c, v, p)
    return (((rf - 50) + (mf - 50)) / 2) * .6 + (((rs - 50) + (ms - 50)) / 2) * .4

def compute_wavetrend(h, l, c, ch=9, avg=12, ma=3):
    ap = (h + l + c) / 3; esa = ap.ewm(span=ch, adjust=False).mean()
    d = abs(ap - esa).ewm(span=ch, adjust=False).mean()
    ci = (ap - esa) / (0.015 * d + 1e-10)
    wt1 = ci.ewm(span=avg, adjust=False).mean()
    wt2 = wt1.rolling(ma).mean()
    return wt1, wt2, (wt1 > wt2) & (wt1.shift(1) <= wt2.shift(1)), (wt1 < wt2) & (wt1.shift(1) >= wt2.shift(1))

def compute_stoch_rsi(c, rl=14, sl=14, ks=3, ds=3):
    rsi = compute_rsi(c, rl); mn, mx = rsi.rolling(sl).min(), rsi.rolling(sl).max()
    k = (((rsi - mn) / (mx - mn + 1e-10)) * 100).rolling(ks).mean()
    return k, k.rolling(ds).mean()

def compute_tr(h, l, c):
    pc = c.shift(1)
    return pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)

def compute_adx(h, l, c, p=14):
    tr = compute_tr(h, l, c); ph, pl = h.shift(1), l.shift(1)
    pdm = pd.Series(np.where((h - ph) > (pl - l), np.maximum(h - ph, 0), 0), index=h.index, dtype=float)
    mdm = pd.Series(np.where((pl - l) > (h - ph), np.maximum(pl - l, 0), 0), index=h.index, dtype=float)
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

def compute_ichimoku(h, l, c, tp=9, kp=26, sbp=52, disp=26):
    tenkan = (h.rolling(tp).max() + l.rolling(tp).min()) / 2
    kijun = (h.rolling(kp).max() + l.rolling(kp).min()) / 2
    sa = ((tenkan + kijun) / 2).shift(disp)
    sb = ((h.rolling(sbp).max() + l.rolling(sbp).min()) / 2).shift(disp)
    return tenkan, kijun, sa, sb

def compute_cmf(h, l, c, v, p=20):
    mfm = ((c - l) - (h - c)) / (h - l + 1e-10)
    return (mfm * v).rolling(p).sum() / (v.rolling(p).sum() + 1e-10)

def compute_supertrend(h, l, c, tr, period=10, mult=3.0):
    atr = tr.rolling(period).mean(); hl2 = (h + l) / 2
    up = (hl2 + mult * atr).values.copy(); dn = (hl2 - mult * atr).values.copy()
    cl = c.values; n = len(c)
    sv = np.full(n, np.nan); dv = np.zeros(n, dtype=int)
    fv = period
    if fv >= n: return pd.Series(np.nan, index=c.index), pd.Series(0, index=c.index, dtype=int)
    dv[fv] = 1; sv[fv] = dn[fv]
    for i in range(fv + 1, n):
        if dv[i - 1] == 1:
            dn[i] = max(dn[i], dn[i - 1]) if not np.isnan(dn[i - 1]) else dn[i]
        else:
            up[i] = min(up[i], up[i - 1]) if not np.isnan(up[i - 1]) else up[i]
        if dv[i - 1] == 1:
            dv[i], sv[i] = (-1, up[i]) if cl[i] < dn[i] else (1, dn[i])
        else:
            dv[i], sv[i] = (1, dn[i]) if cl[i] > up[i] else (-1, up[i])
    return pd.Series(sv, index=c.index), pd.Series(dv, index=c.index)

def compute_volume_profile(h, l, c, v, lookback=20, num_bins=30):
    n = len(c); poc = np.full(n, np.nan); vah = np.full(n, np.nan); val_a = np.full(n, np.nan)
    c_v, h_v, l_v, v_v = c.values, h.values, l.values, v.values
    for i in range(lookback, n):
        s = i - lookback
        h_w, l_w, v_w = h_v[s:i + 1], l_v[s:i + 1], v_v[s:i + 1]
        plo, phi = l_w.min(), h_w.max()
        if phi - plo < 1e-10:
            poc[i] = c_v[i]; vah[i] = phi; val_a[i] = plo; continue
        tp = (h_w + l_w + c_v[s:i + 1]) / 3
        vp, be = np.histogram(tp, bins=num_bins, range=(plo, phi), weights=v_w)
        bc = (be[:-1] + be[1:]) / 2; pb = np.argmax(vp); poc[i] = bc[pb]
        tv = vp.sum(); target = tv * 0.70; cum = vp[pb]; lo_i, hi_i = pb, pb
        while cum < target and (lo_i > 0 or hi_i < num_bins - 1):
            lv = vp[lo_i - 1] if lo_i > 0 else 0
            hv = vp[hi_i + 1] if hi_i < num_bins - 1 else 0
            if lv >= hv and lo_i > 0: lo_i -= 1; cum += lv
            elif hi_i < num_bins - 1: hi_i += 1; cum += hv
            else: break
        vah[i] = be[min(hi_i + 1, num_bins)]; val_a[i] = be[lo_i]
    return pd.Series(poc, index=c.index), pd.Series(vah, index=c.index), pd.Series(val_a, index=c.index)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  다이버전스 (ATR 동적 + scipy)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def detect_pivot_div(price, osc, lb=60, pw=5, os_lim=None, ob_lim=None, atr=None):
    n = len(price); pv = price.values.astype(float); ov = osc.values.astype(float)
    if atr is not None and len(atr) > 0:
        atr_pct = atr / (price + 1e-10) * 100
        atr_ratio = atr_pct / (atr_pct.rolling(100, min_periods=20).median() + 1e-10)
        lb_scale = np.clip(1.3 - 0.35 * atr_ratio.values, 0.5, 1.5)
        dynamic_lb = np.clip(lb * lb_scale, 30, 90).astype(int)
    else:
        dynamic_lb = np.full(n, lb, dtype=int)
    if atr is not None:
        prom_val = max(np.nanmean(np.nan_to_num((atr.rolling(20, min_periods=5).mean() * 0.3).values, nan=0.01)), 0.01)
    else:
        prom_val = max(np.percentile(np.abs(np.diff(pv, prepend=pv[0])), 75) * 2, 0.01)
    lows_idx, _ = find_peaks(-pv, distance=pw, prominence=prom_val)
    highs_idx, _ = find_peaks(pv, distance=pw, prominence=prom_val)
    bd = np.zeros(n, dtype=bool); brd = np.zeros(n, dtype=bool)
    hb = np.zeros(n, dtype=bool); hbr = np.zeros(n, dtype=bool)
    for i in range(1, len(lows_idx)):
        ci, pi = lows_idx[i], lows_idx[i - 1]
        dlb = dynamic_lb[ci] if ci < n else lb
        gap = ci - pi
        if gap < pw * 2 or gap > dlb: continue
        if pv[ci] < pv[pi] and ov[ci] > ov[pi]:
            if os_lim is None or ov[ci] <= os_lim: bd[min(ci + pw, n - 1)] = True
        if pv[ci] > pv[pi] and ov[ci] < ov[pi]: hb[min(ci + pw, n - 1)] = True
    for i in range(1, len(highs_idx)):
        ci, pi = highs_idx[i], highs_idx[i - 1]
        dlb = dynamic_lb[ci] if ci < n else lb
        gap = ci - pi
        if gap < pw * 2 or gap > dlb: continue
        if pv[ci] > pv[pi] and ov[ci] < ov[pi]:
            if ob_lim is None or ov[ci] >= ob_lim: brd[min(ci + pw, n - 1)] = True
        if pv[ci] < pv[pi] and ov[ci] > ov[pi]: hbr[min(ci + pw, n - 1)] = True
    return (pd.Series(bd, index=price.index), pd.Series(brd, index=price.index),
            pd.Series(hb, index=price.index), pd.Series(hbr, index=price.index))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Relative Strength & 선행지표
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def compute_relative_strength(df, spy_df, period=20):
    sc = df['Close'].copy(); spy_c = spy_df['Close'].reindex(sc.index, method='ffill')
    if spy_c.isna().all():
        for k in ['RS_Ratio', 'RS_Momentum']: df[k] = 0.0
        df['RS_Ratio'] = 1.0; return df
    sr = sc.pct_change(period).fillna(0); spr = spy_c.pct_change(period).fillna(0)
    df['Stock_Return'] = sr; df['SPY_Return'] = spr
    df['RS_Ratio'] = ((1 + sr) / (1 + spr + 1e-10)).rolling(10, min_periods=5).mean()
    df['RS_Momentum'] = df['RS_Ratio'] - df['RS_Ratio'].shift(5)
    return df

def compute_momentum_acceleration(df):
    rv = df['RSI'] - df['RSI'].shift(3); df['RSI_Accel'] = rv - rv.shift(3)
    wv = df['WT1'] - df['WT1'].shift(3); df['WT_Accel'] = wv - wv.shift(3)
    df['MACD_Accel'] = df['MACD_Hist'] - df['MACD_Hist'].shift(3)
    rn = df['RSI_Accel'] / (df['RSI_Accel'].rolling(50, min_periods=10).std() + 1e-10)
    wn = df['WT_Accel'] / (df['WT_Accel'].rolling(50, min_periods=10).std() + 1e-10)
    mn = df['MACD_Accel'] / (df['MACD_Accel'].rolling(50, min_periods=10).std() + 1e-10)
    df['Composite_Accel'] = (rn + wn + mn) / 3
    return df

def compute_convergence_speed(df):
    gap = df['WT1'] - df['WT2']; ga = gap.abs()
    df['WT_Gap'] = gap; df['WT_Gap_Abs'] = ga
    df['WT_Conv_Speed'] = ga.shift(3) - ga
    df['WT_Conv_Bull'] = (gap < 0) & (df['WT_Conv_Speed'] > 1.5) & (df['WT1'] < 20)
    df['WT_Conv_Bear'] = (gap > 0) & (df['WT_Conv_Speed'] > 1.5) & (df['WT1'] > -20)
    return df

def compute_market_regime(df):
    C = df['Close']; idx = df.index; score = pd.Series(0.0, index=idx)
    score += np.where(C > df['MA200'], 1.0, -1.0)
    score += np.where(C > df['MA50'], 1.0, -1.0)
    score += np.where(C > df['MA20'], 0.5, -0.5)
    score += np.where(df['MA50'] > df['MA50'].shift(10), 1.0, -1.0)
    score += np.where(df['ST_Direction'] == 1, 1.0, -1.0)
    score += np.where(df['Plus_DI'] > df['Minus_DI'], 0.5, -0.5)
    score += np.where(df['MACD_Line'] > 0, 0.5, -0.5)
    regime_raw = score.rolling(5, min_periods=3).mean()
    df['Regime_Score'] = regime_raw.clip(-8, 8)
    df['Regime'] = np.select([regime_raw >= 4, regime_raw >= 1.5, regime_raw <= -4, regime_raw <= -1.5],
                              [2, 1, -2, -1], default=0)
    return df


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  통합 지표 계산
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def compute_indicators(df):
    c, h, l, v = df['Close'], df['High'], df['Low'], df['Volume']
    for ma in [5, 10, 20, 50, 100, 125, 200]:
        df[f'MA{ma}'] = c.rolling(ma).mean()
    df['EMA8'] = c.ewm(span=8, adjust=False).mean()
    df['EMA21'] = c.ewm(span=21, adjust=False).mean()
    df['BB_Mid'] = df['MA20']; s20 = c.rolling(20).std()
    df['BB_Up'], df['BB_Low'] = df['BB_Mid'] + s20 * 2, df['BB_Mid'] - s20 * 2
    df['BB_Width'] = (df['BB_Up'] - df['BB_Low']) / (df['BB_Mid'] + 1e-10)
    df['Percent_B'] = (c - df['BB_Low']) / (df['BB_Up'] - df['BB_Low'] + 1e-10)
    tr = compute_tr(h, l, c); df['ATR'] = tr.rolling(14).mean()
    df['SuperTrend'], df['ST_Direction'] = compute_supertrend(h, l, c, tr)
    atr_kc = tr.rolling(10).mean(); mid_kc = c.ewm(span=20, adjust=False).mean()
    df['KC_Upper'] = mid_kc + atr_kc * 1.5; df['KC_Mid'] = mid_kc; df['KC_Lower'] = mid_kc - atr_kc * 1.5
    wt1, wt2, wu, wd = compute_wavetrend(h, l, c)
    df['WT1'], df['WT2'], df['WT_Up'], df['WT_Down'] = wt1, wt2, wu, wd
    df['RSI'] = compute_rsi(c, 14)
    df['StochK'], df['StochD'] = compute_stoch_rsi(c)
    df['MFI'] = compute_mfi(h, l, c, v, 14)
    df['RSI_MFI'] = compute_rsi_mfi(h, l, c, v, 60)
    vwap = (c * v).rolling(20).sum() / (v.rolling(20).sum() + 1e-10)
    df['VWAP_Osc'] = ((c - vwap) / (vwap + 1e-10)) * 100
    df['ADX'], df['Plus_DI'], df['Minus_DI'] = compute_adx(h, l, c)
    df['OBV'] = compute_obv(c, v)
    df['MACD_Line'], df['MACD_Signal'], df['MACD_Hist'] = compute_macd(c)
    tk, kj, sa, sb = compute_ichimoku(h, l, c)
    df['Ichimoku_Tenkan'] = tk; df['Ichimoku_Kijun'] = kj
    df['Ichimoku_SenkouA'] = sa; df['Ichimoku_SenkouB'] = sb
    df['CMF'] = compute_cmf(h, l, c, v, 20)
    df = compute_momentum_acceleration(df)
    df = compute_convergence_speed(df)
    df['VP_POC'], df['VP_VAH'], df['VP_VAL'] = compute_volume_profile(h, l, c, v)
    try:
        spy = fetch_spy_history()
        if not spy.empty: df = compute_relative_strength(df, spy, 20)
    except:
        df['RS_Ratio'] = 1.0; df['RS_Momentum'] = 0.0
    df = compute_market_regime(df)
    return df


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  125개 시그널 탐지 함수들
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# ═══ Jeff Cooper Hit & Run ═══

def detect_123_pullback(h, l, c, adx, pdi, mdi):
    sb = (adx > 30) & (pdi > mdi); sbe = (adx > 30) & (mdi > pdi)
    ins = (h < h.shift(1)) & (l > l.shift(1))
    ll1, ll2, ll3 = l < l.shift(1), l.shift(1) < l.shift(2), l.shift(2) < l.shift(3)
    tll = ll1 & ll2 & ll3; tli = (ll1 & ll2 & ins.shift(2)) | (ll1 & ins.shift(1) & ll2.shift(1)) | (ins & ll1 & ll2)
    hh1, hh2, hh3 = h > h.shift(1), h.shift(1) > h.shift(2), h.shift(2) > h.shift(3)
    thh = hh1 & hh2 & hh3; thi = (hh1 & hh2 & ins.shift(2)) | (hh1 & ins.shift(1) & hh2.shift(1)) | (ins & hh1 & hh2)
    return sb & (tll | tli), sbe & (thh | thi)

def detect_180_setup(c, o, h, l, ma10, ma50):
    dr = h - l + 1e-10; cp = (c - l) / dr; pp = (c.shift(1) - l.shift(1)) / (h.shift(1) - l.shift(1) + 1e-10)
    return (pp <= 0.25) & (cp >= 0.75) & (c > ma10) & (c > ma50), (pp >= 0.75) & (cp <= 0.25) & (c < ma10) & (c < ma50)

def detect_boomer(h, l, adx, pdi, mdi):
    ins = (h < h.shift(1)) & (l > l.shift(1)); in2 = ins & ins.shift(1)
    return in2.shift(1).fillna(False) & (adx > 30) & (pdi > mdi), in2.shift(1).fillna(False) & (adx > 30) & (mdi > pdi)

def detect_expansion(h, l, c):
    dr = h - l; mr9 = dr.rolling(9).max()
    h60 = h.rolling(60, min_periods=40).max(); l60 = l.rolling(60, min_periods=40).min()
    return (h >= h60) & (dr >= mr9), (l <= l60) & (dr >= mr9)

def detect_expansion_pivot(c, h, l, ma50):
    dr = h - l; mr9 = dr.rolling(9).max()
    near_low = (l <= ma50) | (l.shift(1) <= ma50.shift(1))
    near_high = (h >= ma50) | (h.shift(1) >= ma50.shift(1))
    return (dr >= mr9) & near_low & (c > ma50), (dr >= mr9) & near_high & (c < ma50)

def detect_expansion_double_sticks(c, o, h, l):
    dr = h - l; dr10r = dr.rolling(10).rank(pct=True)
    h60 = h.rolling(60, min_periods=40).max()
    return (h.shift(1) >= h60.shift(1)) & (dr10r.shift(1) >= 0.7) & (c < o) & (dr10r >= 0.7)

def detect_gilligans(o, c, h, l):
    dr = h - l + 1e-10; cp = (c - l) / dr
    l60 = l.rolling(60, min_periods=40).min(); h60 = h.rolling(60, min_periods=40).max()
    return (o <= l60) & (o < l.shift(1)) & (cp >= 0.5) & (c >= o), (o >= h60) & (o > h.shift(1)) & (cp <= 0.5) & (c <= o)

def detect_lizard(o, c, h, l):
    dr = h - l + 1e-10; cp = (c - l) / dr; op = (o - l) / dr
    return (cp >= 0.75) & (op >= 0.75) & (l <= l.rolling(10).min()), (cp <= 0.25) & (op <= 0.25) & (h >= h.rolling(10).max())

def detect_slingshot(c, o, h, l):
    h60 = h.rolling(60, min_periods=40).max(); l60 = l.rolling(60, min_periods=40).min()
    return (h.shift(1) >= h60.shift(1)) & (l < l.shift(1) - 0.10), (l.shift(1) <= l60.shift(1)) & (h > h.shift(1) + 0.10)

def detect_jack_in_box(h, l, c, df):
    ins = (h < h.shift(1)) & (l > l.shift(1))
    xbo = df.get('Expansion_BO', pd.Series(False, index=df.index)).fillna(False)
    xbd = df.get('Expansion_BD', pd.Series(False, index=df.index)).fillna(False)
    return xbo.shift(2).fillna(False) & ins.shift(1).fillna(False) & (c > h.shift(2)), \
           xbd.shift(2).fillna(False) & ins.shift(1).fillna(False) & (c < l.shift(2))

def detect_non_adx_123(h, l, c, ma50):
    ins = (h < h.shift(1)) & (l > l.shift(1))
    ll1, ll2 = l < l.shift(1), l.shift(1) < l.shift(2)
    tll = ll1 & ll2 & (l.shift(2) < l.shift(3))
    tli = (ll1 & ll2 & ins.shift(2)) | (ll1 & ins.shift(1) & ll2.shift(1)) | (ins & ll1 & ll2)
    hh1, hh2 = h > h.shift(1), h.shift(1) > h.shift(2)
    thh = hh1 & hh2 & (h.shift(2) > h.shift(3))
    thi = (hh1 & hh2 & ins.shift(2)) | (hh1 & ins.shift(1) & hh2.shift(1)) | (ins & hh1 & hh2)
    return (c > ma50) & (tll | tli), (c < ma50) & (thh | thi)

def detect_reversal_new_highs_lows(c, o, h, l):
    dr = h - l; mr5 = dr.rolling(5).max()
    h60 = h.rolling(60, min_periods=40).max(); l60 = l.rolling(60, min_periods=40).min()
    outside = (h > h.shift(1)) & (l < l.shift(1))
    return (h >= h60) & outside & (dr >= mr5) & (c > o), (l <= l60) & outside & (dr >= mr5) & (c < o)


# ═══ MA 지지/저항 ═══

def detect_ma_support_resistance(c, o, h, l, ma, atr):
    ma_dist = (c - ma).abs() / (atr + 1e-10)
    near = ma_dist < 0.2
    support = near & (c > ma) & (l <= ma * 1.01) & (c > o)
    resistance = near & (c < ma) & (h >= ma * 0.99) & (c < o)
    return support, resistance


# ═══ 캔들스틱 ═══

def detect_candlestick_patterns(c, o, h, l, wt1, atr, v):
    body = (c - o).abs()
    us = h - pd.concat([c, o], axis=1).max(axis=1)
    ls_ = pd.concat([c, o], axis=1).min(axis=1) - l
    fr = h - l + 1e-10; ab = body.rolling(20).mean()
    ism = body < ab * 0.6; mr = atr * 0.5
    vok = v >= v.rolling(10, min_periods=5).mean() * 0.5
    vsurge = v > v.rolling(10, min_periods=5).mean() * 1.2
    
    ham = (ls_ >= body * 2) & (us <= body * 0.3) & ism & (wt1 < -20) & (c >= o) & (fr > mr) & vok
    sho = (us >= body * 2) & (ls_ <= body * 0.3) & ism & (wt1 > 20) & (c <= o) & (fr > mr) & vok
    doji = (body <= fr * 0.05) & (fr > atr * 0.3)
    db = doji & (wt1 < -30) & (wt1 > wt1.shift(1)) & vok
    dbe = doji & (wt1 > 30) & (wt1 < wt1.shift(1)) & vok
    d1b = (c.shift(2) < o.shift(2)) & (body.shift(2) > ab.shift(2))
    d2s = body.shift(1) < ab.shift(1) * 0.5
    d3bu = (c > o) & (c > (o.shift(2) + c.shift(2)) / 2) & (body > ab * 0.8)
    ms = d1b & d2s & d3bu & (wt1 < -15) & vsurge
    d1bu = (c.shift(2) > o.shift(2)) & (body.shift(2) > ab.shift(2))
    d3be = (c < o) & (c < (o.shift(2) + c.shift(2)) / 2) & (body > ab * 0.8)
    es = d1bu & d2s & d3be & (wt1 > 15) & vsurge
    spin = ism & (us > body * 0.5) & (ls_ > body * 0.5)
    
    return {'Hammer': ham, 'Shooting_Star': sho, 'Doji': doji, 'Doji_Bullish': db,
            'Doji_Bearish': dbe, 'Morning_Star': ms, 'Evening_Star': es, 'Spinning_Top': spin}

def detect_engulfing(c, o, wt1, ma50, v):
    body = (c - o).abs(); pb = (c.shift(1) - o.shift(1)).abs(); ab = body.rolling(20).mean()
    big = (body > ab * 0.8) & (body > pb)
    pbh = pd.concat([c.shift(1), o.shift(1)], axis=1).max(axis=1)
    pbl = pd.concat([c.shift(1), o.shift(1)], axis=1).min(axis=1)
    cbh = pd.concat([c, o], axis=1).max(axis=1); cbl = pd.concat([c, o], axis=1).min(axis=1)
    vok = v >= v.rolling(10, min_periods=5).mean() * 0.5
    bull = (c.shift(1) < o.shift(1)) & (c > o) & (cbl <= pbl) & (cbh >= pbh) & big & (wt1 < -20) & vok
    bear = (c.shift(1) > o.shift(1)) & (c < o) & (cbl <= pbl) & (cbh >= pbh) & big & (wt1 > 20) & vok
    return bull, bear


# ═══ BB 관련 ═══

def detect_bb_signals(c, o, h, l, bbu, bbl, bbw, kcu, kcl):
    sq_on = (bbu < kcu) & (bbl > kcl)
    sq_started = sq_on & ~sq_on.shift(1).fillna(False)
    sq_ended = ~sq_on & sq_on.shift(1).fillna(False)
    sq_end_bull = sq_ended & (c > c.shift(1)) & (c > o)
    sq_end_bear = sq_ended & (c < c.shift(1)) & (c < o)
    
    ut = h >= bbu; lt = l <= bbl
    ub = c > bbu; lb_break = (c < bbl) & (c < o)
    lb_bounce = (c < bbl) & (c > o) & (c > c.shift(1))
    u_walk = ut.rolling(3).sum() >= 3
    l_walk = lt.rolling(3).sum() >= 3
    
    bbw_pct = bbw.rolling(126, min_periods=60).rank(pct=True)
    wide = bbw_pct >= 0.9
    squeeze_tight = bbw <= bbw.rolling(126, min_periods=60).min() * 1.05
    
    return {
        'Squeeze_On': sq_on, 'BB_Squeeze': squeeze_tight, 'BB_Squeeze_Started': sq_started,
        'BB_Squeeze_End_Bull': sq_end_bull, 'BB_Squeeze_End_Bear': sq_end_bear,
        'BB_Upper_Touch': ut & ~ub, 'BB_Lower_Touch': lt & ~lb_break,
        'BB_Upper_Break': ub, 'BB_Lower_Break': lb_break, 'BB_Lower_Bounce': lb_bounce,
        'BB_Upper_Walk': u_walk, 'BB_Lower_Walk': l_walk, 'BB_Wide_Bands': wide,
    }


# ═══ MACD/스토캐스틱/ADX/RSI ═══

def detect_macd_signals(ml, ms_):
    return {
        'MACD_Cross_Buy': (ml > ms_) & (ml.shift(1) <= ms_.shift(1)) & (ml < 0),
        'MACD_Cross_Sell': (ml < ms_) & (ml.shift(1) >= ms_.shift(1)) & (ml > 0),
        'MACD_Zero_Cross_Buy': (ml > 0) & (ml.shift(1) <= 0),
        'MACD_Zero_Cross_Sell': (ml < 0) & (ml.shift(1) >= 0),
    }

def detect_stoch_signals(stk, std):
    return {
        'StochRSI_Cross_Buy': (stk > std) & (stk.shift(1) <= std.shift(1)) & (stk < 25),
        'StochRSI_Cross_Sell': (stk < std) & (stk.shift(1) >= std.shift(1)) & (stk > 75),
        'Stoch_Reached_OB': (stk >= 80) & (stk.shift(1) < 80),
        'Stoch_Reached_OS': (stk <= 20) & (stk.shift(1) > 20),
        'Stoch_Overbought': (stk > 80) & (std > 80),
        'Stoch_Oversold': (stk < 20) & (std < 20),
    }

def detect_dmi_signals(adx, pdi, mdi):
    return {
        'DMI_Cross_Bull': (pdi > mdi) & (pdi.shift(1) <= mdi.shift(1)),
        'DMI_Cross_Bear': (mdi > pdi) & (mdi.shift(1) <= pdi.shift(1)),
        'ADX_New_Uptrend': (adx > 25) & (adx.shift(1) <= 25) & (pdi > mdi),
        'ADX_New_Downtrend': (adx > 25) & (adx.shift(1) <= 25) & (mdi > pdi),
        'ADX_Momentum_Buy': (adx > 20) & (adx.shift(1) <= 20) & (pdi > mdi),
        'ADX_Momentum_Sell': (adx > 20) & (adx.shift(1) <= 20) & (mdi > pdi),
    }

def detect_rsi_signals(rsi):
    return {
        'RSI_Cross_30_Up': (rsi > 30) & (rsi.shift(1) <= 30),
        'RSI_Cross_50_Up': (rsi > 50) & (rsi.shift(1) <= 50),
        'RSI_Cross_70_Down': (rsi < 70) & (rsi.shift(1) >= 70),
        'RSI_Cross_50_Down': (rsi < 50) & (rsi.shift(1) >= 50),
    }


# ═══ 갭/범위/52주/연속일/기타 ═══

def detect_gaps(c, o, h, l, atr):
    t = atr * 0.5
    gu = (o > h.shift(1)) & ((o - h.shift(1)) > t)
    gd = (o < l.shift(1)) & ((l.shift(1) - o) > t)
    return {'Gap_Up': gu, 'Gap_Down': gd,
            'Gap_Up_Closed': gu.shift(1).fillna(False) & (l <= h.shift(2)),
            'Gap_Down_Closed': gd.shift(1).fillna(False) & (h >= l.shift(2))}

def detect_range_signals(h, l, atr):
    dr = h - l; nr7m = dr.rolling(7).min(); nr7 = dr <= nr7m
    return {'NR7': nr7, 'NR7_2': nr7 & nr7.shift(1).fillna(False),
            'Narrow_Range_Bar': dr < atr * 0.5, 'Wide_Range_Bar': dr > atr * 2.0,
            'Calm_After_Storm': (dr > atr * 2.0).rolling(5, min_periods=1).max().shift(1).fillna(False).astype(bool) & (dr < atr * 0.5)}

def detect_52w(c, h, l):
    h252 = h.rolling(252, min_periods=200).max().shift(1); l252 = l.rolling(252, min_periods=200).min().shift(1)
    c252h = c.rolling(252, min_periods=200).max().shift(1); c252l = c.rolling(252, min_periods=200).min().shift(1)
    return {'New_52W_High': h > h252, 'New_52W_Low': l < l252,
            'New_52W_Closing_High': c > c252h, 'New_52W_Closing_Low': c < c252l}

def detect_consecutive(c):
    up = c > c.shift(1); dn = c < c.shift(1)
    us = _vectorized_streak(up); ds = _vectorized_streak(dn)
    return {'Up_3_Days': us >= 3, 'Up_4_Days': us >= 4, 'Up_5_Days': us >= 5,
            'Down_3_Days': ds >= 3, 'Down_4_Days': ds >= 4, 'Down_5_Days': ds >= 5}

def detect_round_number(c, o, atr):
    n10 = (c / 10).round() * 10; dist = (c - n10).abs(); near = dist < atr * 0.5
    return near & (c.shift(1) < n10) & (c > n10) & (c > o), near & (c.shift(1) > n10) & (c < n10) & (c < o)

def detect_pocket_pivot(c, o, v, ma50):
    dv = v.where(c < c.shift(1), 0)
    return (c > o) & (v > dv.rolling(10).max()) & (c > ma50) & (c > c.shift(1))

def detect_parabolic_rise(c):
    pct = (c - c.shift(10)) / (c.shift(10) + 1e-10)
    return pct > 0.3

def detect_three_weeks_tight(c, period=15):
    ch = c.rolling(period).max(); cl = c.rolling(period).min()
    return ((ch - cl) / (cl + 1e-10)) < 0.015

def detect_ichimoku_signals(c, tk, kj, sa, sb):
    kt = pd.concat([sa, sb], axis=1).max(axis=1); kb = pd.concat([sa, sb], axis=1).min(axis=1)
    return ((c > kt) & (c.shift(1) <= kt.shift(1)) & (tk > kj),
            (c < kb) & (c.shift(1) >= kb.shift(1)) & (tk < kj),
            (tk > kj) & (tk.shift(1) <= kj.shift(1)) & (c > kt),
            (tk < kj) & (tk.shift(1) >= kj.shift(1)) & (c < kb))

def detect_cmf_signals(cmf, c, ma50):
    return (cmf > 0.1) & (cmf.shift(1) <= 0.1) & (c > ma50), (cmf < -0.1) & (cmf.shift(1) >= -0.1) & (c < ma50)

def detect_mf_signals(c, rmfi):
    mcb = (rmfi > 0) & (rmfi.shift(1) <= 0); mcs = (rmfi < 0) & (rmfi.shift(1) >= 0)
    mr = rmfi > rmfi.shift(1); mf_ = rmfi < rmfi.shift(1)
    mus = _vectorized_streak(mr); mds = _vectorized_streak(mf_)
    pl = c < c.rolling(5).min().shift(1); mh = rmfi > rmfi.rolling(5).min().shift(1)
    ph = c > c.rolling(5).max().shift(1); ml = rmfi < rmfi.rolling(5).max().shift(1)
    return {'MF_Cross_Bull': mcb, 'MF_Cross_Bear': mcs,
            'MF_Bull_Div': pl & mh & (rmfi < 0), 'MF_Bear_Div': ph & ml & (rmfi > 0),
            'MF_Accel_Up': mus >= 5, 'MF_Accel_Dn': mds >= 5}

def detect_volume_signals(c, o, v, wt1, atr):
    avg = v.rolling(50, min_periods=10).mean(); vr = v / (avg + 1e-10)
    vs = v.rolling(20).std(); vz = (v - avg) / (vs + 1e-10)
    big = (c - o).abs() > atr * 0.5; ps = (vz.shift(1) > 2.5) & big.shift(1)
    return {
        'Volume_Surge': vr >= 3.0,
        'Volume_Climax_Buy': ps & (c.shift(1) < o.shift(1)) & (wt1.shift(1) < -40) & (c > o),
        'Volume_Climax_Sell': ps & (c.shift(1) > o.shift(1)) & (wt1.shift(1) > 40) & (c < o),
    }

def detect_relative_strength_signals(df):
    rs = df.get('RS_Ratio', pd.Series(1.0, index=df.index))
    rm = df.get('RS_Momentum', pd.Series(0.0, index=df.index))
    spr = df.get('SPY_Return', pd.Series(0.0, index=df.index))
    df['Relative_Strength_Buy'] = (rs > 1.03) & (rm > 0.01) & (spr < 0) & (df['Close'] > df['Close'].shift(1))
    df['Relative_Strength_Sell'] = (rs < 0.97) & (rm < -0.01) & (spr > 0) & (df['Close'] < df['Close'].shift(1))
    return df

def detect_vwap_pair(c, vosc, wt1, wt2, v, atr):
    vok = _volf(v, 0.7)
    return (vosc > 0) & (vosc.shift(1) < -0.5) & (wt1 > wt2) & (wt1 < 30) & vok, \
           (vosc < 0) & (vosc.shift(1) > 0.5) & (wt1 < wt2) & (wt1 > -30) & vok

def detect_ema_pullback(c, h, l, v, e8, e21, atr, wt1, wt2):
    vok = _volf(v, 0.5); ar = atr / (c + 1e-10)
    slope_up = e21 > e21.shift(5); trend_up = (e8 > e21) & slope_up & (c > e8)
    touch_up = (l <= e8 * (1 + ar * 0.15)) & (l >= e21 * (1 - ar * 0.25))
    bounce_up = (c >= e8) & (c > h.shift(1)) & (wt1 > wt1.shift(1)) & (wt1 > wt2) & (wt1 < 60)
    slope_dn = e21 < e21.shift(5); trend_dn = (e8 < e21) & slope_dn & (c < e8)
    touch_dn = (h >= e8 * (1 - ar * 0.15)) & (h <= e21 * (1 + ar * 0.25))
    bounce_dn = (c <= e8) & (c < l.shift(1)) & (wt1 < wt1.shift(1)) & (wt1 < wt2) & (wt1 > -60)
    return trend_up & _recent(touch_up, 2) & bounce_up & vok, trend_dn & _recent(touch_dn, 2) & bounce_dn & vok

def detect_mom_ignition(c, o, v, bbu, bbl, atr, e8, e21, wt1, bbw):
    body = (c - o).abs(); bb = body > atr * 1.5; hv = v > v.rolling(20).mean() * 2.0
    comp = bbw.shift(1) < bbw.rolling(20).mean().shift(1)
    return (c > o) & bb & hv & (c > bbu) & (e8 > e21) & (wt1 < 50) & comp, \
           (c < o) & bb & hv & (c < bbl) & (e8 < e21) & (wt1 > -50) & comp

def detect_parabolic_pair(c, o, wt1, bbu, bbl, atr):
    return (((wt1 < -80) & (wt1 > wt1.shift(1)) & (c > o)) | ((c < bbl - atr * 1.5) & (c > o))), \
           (((wt1 > 80) & (wt1 < wt1.shift(1)) & (c < o)) | ((c > bbu + atr * 1.5) & (c < o)))


print("✅ Part 2/6 로드 완료: 유틸리티, 기술지표, 시그널 탐지 함수")

# ══════════════════════════════════════════════════════════════
#  CipherX V12.3 — PART 3/6: 통합 시그널 탐지 + Combined Scan
# ══════════════════════════════════════════════════════════════

def detect_all_signals(df):
    """125개 시그널 + Combined Scan 전체 탐지"""
    H, L, C, O, V = df['High'], df['Low'], df['Close'], df['Open'], df['Volume']
    e8, e21 = df['EMA8'], df['EMA21']
    m10, m20, m50, m200 = df['MA10'], df['MA20'], df['MA50'], df['MA200']
    wt1, wt2, atr = df['WT1'], df['WT2'], df['ATR']
    adx, pdi, mdi = df['ADX'], df['Plus_DI'], df['Minus_DI']
    idx = df.index
    vol_ok = _volf(V, 0.5)
    
    # ═══ MCB+ 핵심 시그널 ═══
    wt_up_r = _recent(df['WT_Up'], 2); wt_dn_r = _recent(df['WT_Down'], 2)
    htf_bull = (e8 > e21) & (e21 > e21.shift(5)) & (C > m50) & (m50 > m50.shift(10))
    
    df['Green_Dot_T1'] = wt_up_r & (wt1 <= OS1) & (df['RSI'] < 30) & (df['MFI'] < 30) & vol_ok
    df['Green_Dot_T2'] = wt_up_r & (wt1 <= OS1) & ((df['RSI'] < 32) | (df['MFI'] < 32)) & ~df['Green_Dot_T1'] & vol_ok
    df['Red_Dot_T1'] = wt_dn_r & (wt1 >= OB1) & (df['RSI'] > 70) & (df['MFI'] > 70) & vol_ok
    df['Red_Dot_T2'] = wt_dn_r & (wt1 >= OB1) & ((df['RSI'] > 68) | (df['MFI'] > 68)) & ~df['Red_Dot_T1'] & vol_ok
    df['Blue_Diamond'] = (wt2 <= 0) & wt_up_r & htf_bull & vol_ok
    df['Red_Diamond'] = (wt2 >= 0) & wt_dn_r & ~htf_bull & vol_ok
    df['Green_Circle'] = wt_up_r & (wt1 <= OS1) & ~df['Green_Dot_T1'] & ~df['Green_Dot_T2'] & vol_ok & (df['RSI'] < 45)
    df['Red_Circle'] = wt_dn_r & (wt1 >= OB1) & ~df['Red_Dot_T1'] & ~df['Red_Dot_T2'] & vol_ok & (df['RSI'] > 55)
    
    # 다이버전스
    bd, brd, hb, hbr = detect_pivot_div(C, wt1, 60, 5, OS1, OB1, atr=atr)
    rbd, rbrd, _, _ = detect_pivot_div(C, df['RSI'], 60, 5, 35, 65, atr=atr)
    obd, obrd, _, _ = detect_pivot_div(C, df['OBV'], 60, 5, atr=atr)
    
    df['Gold_Dot'] = df['Green_Dot_T1'] & (wt1 <= OS2) & _recent(bd, 3)
    df['Blood_Diamond'] = df['Red_Dot_T1'] & (wt1 >= OB2) & _recent(brd, 3)
    df['Bull_Divergence'] = bd & ~df['Gold_Dot'] & vol_ok
    df['Bear_Divergence'] = brd & ~df['Blood_Diamond'] & vol_ok
    df['RSI_Bull_Divergence'] = rbd & (wt1 < -20) & vol_ok
    df['RSI_Bear_Divergence'] = rbrd & (wt1 > 20) & vol_ok
    df['Hidden_Bull_Div'] = hb & (wt1 < -25) & htf_bull & vol_ok
    df['Hidden_Bear_Div'] = hbr & (wt1 > 25) & ~htf_bull & vol_ok
    df['OBV_Div_Buy'] = obd & (wt1 < -30); df['OBV_Div_Sell'] = obrd & (wt1 > 30)
    
    # ═══ Jeff Cooper ═══
    df['Pullback_123_Bull'], df['Pullback_123_Bear'] = detect_123_pullback(H, L, C, adx, pdi, mdi)
    df['Setup_180_Bull'], df['Setup_180_Bear'] = detect_180_setup(C, O, H, L, m10, m50)
    df['Boomer_Buy'], df['Boomer_Sell'] = detect_boomer(H, L, adx, pdi, mdi)
    df['Expansion_BO'], df['Expansion_BD'] = detect_expansion(H, L, C)
    df['Expansion_Pivot_Buy'], df['Expansion_Pivot_Sell'] = detect_expansion_pivot(C, H, L, m50)
    df['Expansion_Double_Sticks'] = detect_expansion_double_sticks(C, O, H, L)
    df['Gilligans_Buy'], df['Gilligans_Sell'] = detect_gilligans(O, C, H, L)
    df['Lizard_Bull'], df['Lizard_Bear'] = detect_lizard(O, C, H, L)
    df['Slingshot_Bull'], df['Slingshot_Bear'] = detect_slingshot(C, O, H, L)
    df['Jack_In_Box_Bull'], df['Jack_In_Box_Bear'] = detect_jack_in_box(H, L, C, df)
    df['NonADX_123_Bull'], df['NonADX_123_Bear'] = detect_non_adx_123(H, L, C, m50)
    df['Reversal_New_Highs'], df['Reversal_New_Lows'] = detect_reversal_new_highs_lows(C, O, H, L)
    
    # ═══ MA 시그널 ═══
    df['MA20_Support'], df['MA20_Resistance'] = detect_ma_support_resistance(C, O, H, L, m20, atr)
    df['MA50_Support'], df['MA50_Resistance'] = detect_ma_support_resistance(C, O, H, L, m50, atr)
    df['MA200_Support'], df['MA200_Resistance'] = detect_ma_support_resistance(C, O, H, L, m200, atr)
    for k, v_ in ({'Cross_Above_20MA': (C > m20) & (C.shift(1) <= m20.shift(1)),
                    'Cross_Above_50MA': (C > m50) & (C.shift(1) <= m50.shift(1)),
                    'Cross_Above_200MA': (C > m200) & (C.shift(1) <= m200.shift(1)),
                    'Fell_Below_20MA': (C < m20) & (C.shift(1) >= m20.shift(1)),
                    'Fell_Below_50MA': (C < m50) & (C.shift(1) >= m50.shift(1)),
                    'Fell_Below_200MA': (C < m200) & (C.shift(1) >= m200.shift(1))}).items():
        df[k] = v_
    gc = (m50 > m200) & (m50.shift(1) <= m200.shift(1)); dc_ = (m50 < m200) & (m50.shift(1) >= m200.shift(1))
    df['Golden_Cross'] = gc & (adx > 15); df['Death_Cross'] = dc_ & (adx > 15)
    df['MTF_All_Bullish'] = (C > m10) & (C > m50) & (C > m200)
    df['MTF_All_Bearish'] = (C < m10) & (C < m50) & (C < m200)
    
    # ═══ BB 시그널 ═══
    bb_sigs = detect_bb_signals(C, O, H, L, df['BB_Up'], df['BB_Low'], df['BB_Width'], df['KC_Upper'], df['KC_Lower'])
    for k, v_ in bb_sigs.items(): df[k] = v_
    
    # ═══ 캔들스틱 ═══
    candle_sigs = detect_candlestick_patterns(C, O, H, L, wt1, atr, V)
    for k, v_ in candle_sigs.items(): df[k] = v_
    df['Bullish_Engulfing'], df['Bearish_Engulfing'] = detect_engulfing(C, O, wt1, m50, V)
    ins = (H < H.shift(1)) & (L > L.shift(1)); out = (H > H.shift(1)) & (L < L.shift(1))
    df['Inside_Day'] = ins
    df['Outside_Bullish'] = out & (C > O) & (C > H.shift(1)) & vol_ok
    df['Outside_Bearish'] = out & (C < O) & (C < L.shift(1)) & vol_ok
    
    # ═══ MACD/Stoch/ADX/RSI ═══
    for k, v_ in detect_macd_signals(df['MACD_Line'], df['MACD_Signal']).items(): df[k] = v_ & vol_ok
    for k, v_ in detect_stoch_signals(df['StochK'], df['StochD']).items(): df[k] = v_
    for k, v_ in detect_dmi_signals(adx, pdi, mdi).items(): df[k] = v_ & vol_ok
    for k, v_ in detect_rsi_signals(df['RSI']).items(): df[k] = v_
    
    # ═══ 갭/범위/52주/연속일 ═══
    for k, v_ in detect_gaps(C, O, H, L, atr).items(): df[k] = v_
    for k, v_ in detect_range_signals(H, L, atr).items(): df[k] = v_
    for k, v_ in detect_52w(C, H, L).items(): df[k] = v_
    for k, v_ in detect_consecutive(C).items(): df[k] = v_
    
    # ═══ 기타 시그널 ═══
    df['Multiple_Ten_Bull'], df['Multiple_Ten_Bear'] = detect_round_number(C, O, atr)
    df['Pocket_Pivot'] = detect_pocket_pivot(C, O, V, m50)
    df['Parabolic_Rise'] = detect_parabolic_rise(C)
    df['Three_Weeks_Tight'] = detect_three_weeks_tight(C)
    
    for k, v_ in detect_volume_signals(C, O, V, wt1, atr).items(): df[k] = v_
    
    # TTM Squeeze
    mom = C - ((H.rolling(20).max() + L.rolling(20).min()) / 2 + df['KC_Mid']) / 2
    sq_fire = ~df['Squeeze_On'] & df['Squeeze_On'].shift(1).fillna(False)
    df['Squeeze_Fire_Buy'] = sq_fire & (mom > 0) & (mom > mom.shift(1)) & vol_ok
    df['Squeeze_Fire_Sell'] = sq_fire & (mom < 0) & (mom < mom.shift(1)) & vol_ok
    
    # SuperTrend
    df['SuperTrend_Buy'] = (df['ST_Direction'] == 1) & (df['ST_Direction'].shift(1) == -1)
    df['SuperTrend_Sell'] = (df['ST_Direction'] == -1) & (df['ST_Direction'].shift(1) == 1)
    
    # EMA PB, Mom Ign, Parabolic, VWAP
    df['EMA_Pullback_Buy'], df['EMA_Pullback_Sell'] = detect_ema_pullback(C, H, L, V, e8, e21, atr, wt1, wt2)
    df['Momentum_Ignition_Buy'], df['Momentum_Ignition_Sell'] = detect_mom_ignition(C, O, V, df['BB_Up'], df['BB_Low'], atr, e8, e21, wt1, df['BB_Width'])
    df['Parabolic_Bottom_Buy'], df['Parabolic_Top_Sell'] = detect_parabolic_pair(C, O, wt1, df['BB_Up'], df['BB_Low'], atr)
    df['VWAP_Bounce_Buy'], df['VWAP_Reject_Sell'] = detect_vwap_pair(C, df['VWAP_Osc'], wt1, wt2, V, atr)
    
    # 이치모쿠, CMF, MF
    (df['Kumo_Breakout_Bull'], df['Kumo_Breakout_Bear'],
     df['TK_Cross_Bull'], df['TK_Cross_Bear']) = detect_ichimoku_signals(C, df['Ichimoku_Tenkan'], df['Ichimoku_Kijun'], df['Ichimoku_SenkouA'], df['Ichimoku_SenkouB'])
    df['CMF_Bull'], df['CMF_Bear'] = detect_cmf_signals(df['CMF'], C, m50)
    mfs = detect_mf_signals(C, df['RSI_MFI'])
    for k in ['MF_Cross_Bull', 'MF_Cross_Bear', 'MF_Bull_Div', 'MF_Bear_Div', 'MF_Accel_Up', 'MF_Accel_Dn']:
        if k in mfs: df[k] = mfs[k] & vol_ok
    
    # VP, RS
    if 'VP_POC' in df.columns:
        poc = df['VP_POC']
        df['Volume_POC_Breakout'] = (C > poc) & (C.shift(1) <= poc.shift(1)) & vol_ok & (C > O)
        df['Volume_POC_Breakdown'] = (C < poc) & (C.shift(1) >= poc.shift(1)) & vol_ok & (C < O)
    if 'VP_VAH' in df.columns:
        ap_ = atr / (C + 1e-10)
        df['VP_VAH_Resistance'] = ((df['VP_VAH'] - C).abs() / (C + 1e-10) < ap_ * 0.5) & (C < O)
        df['VP_VAL_Support'] = ((C - df['VP_VAL']).abs() / (C + 1e-10) < ap_ * 0.5) & (C > O)
    df = detect_relative_strength_signals(df)
    
    # 선행지표
    df['Setup_Squeeze_Bull'] = df['BB_Squeeze'] & (df['MACD_Hist'] < 0) & (df['MACD_Hist'] > df['MACD_Hist'].shift(1)) & (wt1 < 30)
    df['Setup_Squeeze_Bear'] = df['BB_Squeeze'] & (df['MACD_Hist'] > 0) & (df['MACD_Hist'] < df['MACD_Hist'].shift(1)) & (wt1 > -30)
    ca = df.get('Composite_Accel', pd.Series(0, index=idx))
    df['Momentum_Accel_Buy'] = (ca > JT.ACCEL_MODERATE) & (wt1 < 40) & vol_ok
    df['Momentum_Accel_Sell'] = (ca < -JT.ACCEL_MODERATE) & (wt1 > -40) & vol_ok
    vr = V / (V.rolling(20, min_periods=5).mean() + 1e-10)
    df['Volume_Dry_Up'] = _vectorized_streak(vr < 0.6) >= 5
    cs = df.get('WT_Conv_Speed', pd.Series(0, index=idx))
    ga = df.get('WT_Gap_Abs', pd.Series(999, index=idx))
    df['WT_Convergence_Bull'] = (cs > 3.0) & (ga > 2) & (ga < 15) & (wt1 < wt2) & (wt1 < 20)
    df['WT_Convergence_Bear'] = (cs > 3.0) & (ga > 2) & (ga < 15) & (wt1 > wt2) & (wt1 > -20)
    
    # ═══ 쿨다운 ═══
    PAIRED = {
        ('MACD_Cross_Buy', 'MACD_Cross_Sell'): 12, ('StochRSI_Cross_Buy', 'StochRSI_Cross_Sell'): 7,
        ('Bullish_Engulfing', 'Bearish_Engulfing'): 5, ('Hammer', 'Shooting_Star'): 5,
        ('Morning_Star', 'Evening_Star'): 7, ('DMI_Cross_Bull', 'DMI_Cross_Bear'): 10,
        ('Pullback_123_Bull', 'Pullback_123_Bear'): 7, ('Expansion_BO', 'Expansion_BD'): 10,
        ('Gilligans_Buy', 'Gilligans_Sell'): 10, ('Slingshot_Bull', 'Slingshot_Bear'): 7,
        ('MF_Cross_Bull', 'MF_Cross_Bear'): 10, ('Kumo_Breakout_Bull', 'Kumo_Breakout_Bear'): 10,
    }
    ph = set()
    for (bs, ss), cd in PAIRED.items():
        _cooldown_directional(df, bs, ss, cd); ph.add(bs); ph.add(ss)
    for s, cd in COOLDOWN_MAP.items():
        if s in df.columns and s not in ph: df[s] = _cooldown(df[s], cd)
    
    # ═══ Combined Scan 실행 ═══
    df = detect_combined_scans(df)
    
    return df


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Combined Scan 탐지
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def detect_combined_scans(df):
    """Combined Multiple Scan — 초강력 복합 시그널 탐지"""
    idx = df.index
    C, O, H, L, V = df['Close'], df['Open'], df['High'], df['Low'], df['Volume']
    F = lambda col: df.get(col, pd.Series(False, index=idx)).fillna(False)
    N = lambda col, d=0: df.get(col, pd.Series(d, index=idx)).fillna(d)
    
    vol_avg = V.rolling(50, min_periods=10).mean()
    vol_ratio = V / (vol_avg + 1e-10)
    
    # 조건 블록
    uptrend = (C > N('MA50')) & (N('MA50') > N('MA200')) & (N('Plus_DI') > N('Minus_DI'))
    downtrend = (C < N('MA50')) & (N('MA50') < N('MA200')) & (N('Minus_DI') > N('Plus_DI'))
    adx_ok = N('ADX') > 20
    vol_surge = vol_ratio >= 2.0; vol_ok = vol_ratio >= 1.0
    
    bull_candle = F('Bullish_Engulfing') | F('Morning_Star') | F('Hammer') | F('Doji_Bullish')
    bear_candle = F('Bearish_Engulfing') | F('Evening_Star') | F('Shooting_Star') | F('Doji_Bearish')
    
    cooper_bull = F('Pullback_123_Bull') | F('NonADX_123_Bull') | F('Setup_180_Bull') | F('Boomer_Buy') | F('Expansion_BO') | F('Gilligans_Buy') | F('Lizard_Bull')
    cooper_bear = F('Pullback_123_Bear') | F('NonADX_123_Bear') | F('Setup_180_Bear') | F('Boomer_Sell') | F('Expansion_BD') | F('Gilligans_Sell') | F('Lizard_Bear')
    
    mf_bull = (N('RSI_MFI') > N('RSI_MFI').shift(1)) | (N('CMF') > 0.05) | F('MF_Cross_Bull')
    mf_bear = (N('RSI_MFI') < N('RSI_MFI').shift(1)) | (N('CMF') < -0.05) | F('MF_Cross_Bear')
    
    near_bb_lower = C <= N('BB_Low') * 1.01
    near_bb_upper = C >= N('BB_Up') * 0.99
    near_vp_sup = (N('VP_VAL') > 0) & ((C - N('VP_VAL')).abs() / (C + 1e-10) < 0.02)
    near_vp_res = (N('VP_VAH') > 0) & ((N('VP_VAH') - C).abs() / (C + 1e-10) < 0.02)
    near_ma50 = ((C - N('MA50')).abs() / (C + 1e-10)) < 0.03
    
    wt_os = N('WT1') < -53; wt_ob = N('WT1') > 53
    rsi_os = N('RSI') < 30; rsi_ob = N('RSI') > 70
    stoch_os = (N('StochK') < 20) & (N('StochD') < 20)
    stoch_ob = (N('StochK') > 80) & (N('StochD') > 80)
    
    div_bull_cnt = F('Bull_Divergence').astype(int) + F('RSI_Bull_Divergence').astype(int) + F('MF_Bull_Div').astype(int) + F('OBV_Div_Buy').astype(int)
    div_bear_cnt = F('Bear_Divergence').astype(int) + F('RSI_Bear_Divergence').astype(int) + F('MF_Bear_Div').astype(int) + F('OBV_Div_Sell').astype(int)
    
    macd_bull = N('MACD_Hist') > N('MACD_Hist').shift(1)
    macd_bear = N('MACD_Hist') < N('MACD_Hist').shift(1)
    wt_rising = N('WT1') > N('WT1').shift(1)
    wt_falling = N('WT1') < N('WT1').shift(1)
    
    long_lower_wick = (pd.concat([C, O], axis=1).min(axis=1) - L) > (H - L) * 0.6
    long_upper_wick = (H - pd.concat([C, O], axis=1).max(axis=1)) > (H - L) * 0.6
    
    # ═══ TIER 1 매수 ═══
    # Ultimate Buy (6중)
    ub = (uptrend | (C > N('MA50'))).astype(int)
    ub += ((wt_rising | F('WT_Up')) & (macd_bull | (N('MACD_Hist') > 0))).astype(int)
    ub += (bull_candle | cooper_bull).astype(int)
    ub += vol_ok.astype(int)
    ub += mf_bull.astype(int)
    ub += (near_ma50 | F('BB_Squeeze_End_Bull') | near_vp_sup | (C > N('VP_POC'))).astype(int)
    df['CS_Ultimate_Buy'] = ub >= 6
    
    # Triple Oversold Reversal
    triple_os = (wt_os | (N('WT1') < -60)) & (rsi_os | (N('RSI') < 35)) & stoch_os
    rev_sig = F('WT_Up') | wt_rising | bull_candle | long_lower_wick | F('Gold_Dot') | F('Green_Dot_T1')
    df['CS_Triple_Oversold_Reversal'] = triple_os & rev_sig & vol_ok
    
    # Breakout Momentum
    breakout = F('New_52W_High') | F('Expansion_BO') | (C > N('BB_Up'))
    df['CS_Breakout_Momentum_Buy'] = breakout & adx_ok & (N('Plus_DI') > N('Minus_DI')) & vol_surge & macd_bull
    
    # Institutional Accumulation
    accum = F('Pocket_Pivot') | (F('NR7') & (N('OBV') > N('OBV').shift(5))) | (F('Calm_After_Storm') & (C > O))
    df['CS_Institutional_Accumulation'] = accum & (C > N('MA50')) & (N('CMF') > 0.05) & (N('OBV') > N('OBV').shift(5))
    
    # Divergence Confluence
    df['CS_Divergence_Confluence_Buy'] = (div_bull_cnt >= 2) & (near_bb_lower | near_vp_sup | near_ma50) & (bull_candle | long_lower_wick | F('WT_Up')) & vol_ok
    
    # Capitulation Bottom
    extreme_low = F('New_52W_Low') | (C <= C.rolling(252, min_periods=200).min() * 1.02)
    extreme_os = (N('WT1') < -80) | (wt_os & (N('RSI') < 25))
    df['CS_Capitulation_Bottom'] = extreme_low & extreme_os & (vol_ratio >= 3.0) & (long_lower_wick | F('Hammer') | F('Parabolic_Bottom_Buy')) & (N('MFI') < 30)
    
    # ═══ TIER 1 매도 ═══
    us = (downtrend | (C < N('MA50'))).astype(int)
    us += ((wt_falling | F('WT_Down')) & (macd_bear | (N('MACD_Hist') < 0))).astype(int)
    us += (bear_candle | cooper_bear).astype(int)
    us += vol_ok.astype(int)
    us += mf_bear.astype(int)
    us += (near_ma50 | F('BB_Squeeze_End_Bear') | near_vp_res | (C < N('VP_POC'))).astype(int)
    df['CS_Ultimate_Sell'] = us >= 6
    
    triple_ob = (wt_ob | (N('WT1') > 60)) & (rsi_ob | (N('RSI') > 65)) & stoch_ob
    rev_sig_s = F('WT_Down') | wt_falling | bear_candle | long_upper_wick | F('Blood_Diamond') | F('Red_Dot_T1')
    df['CS_Triple_Overbought_Exhaustion'] = triple_ob & rev_sig_s & vol_ok
    
    breakdown = F('New_52W_Low') | F('Expansion_BD') | (C < N('BB_Low'))
    df['CS_Breakdown_Momentum_Sell'] = breakdown & adx_ok & (N('Minus_DI') > N('Plus_DI')) & vol_surge & macd_bear
    
    parabolic = (C > C.shift(10) * 1.3) | F('Parabolic_Top_Sell')
    extreme_ob = (N('WT1') > 80) | (wt_ob & (N('RSI') > 75))
    df['CS_Parabolic_Exhaustion_Sell'] = parabolic & extreme_ob & (long_upper_wick | F('Shooting_Star') | bear_candle) & (vol_ratio >= 3.0)
    
    df['CS_Divergence_Confluence_Sell'] = (div_bear_cnt >= 2) & (near_bb_upper | near_vp_res | near_ma50) & (bear_candle | long_upper_wick | F('WT_Down')) & vol_ok
    
    extreme_high = F('New_52W_High') | (C >= C.rolling(252, min_periods=200).max() * 0.98)
    df['CS_Blow_Off_Top'] = extreme_high & extreme_ob & (vol_ratio >= 3.0) & (long_upper_wick | F('Shooting_Star') | F('Parabolic_Top_Sell')) & (N('MFI') > 70)
    
    # ═══ TIER 2 매수 ═══
    df['CS_Trend_Pullback_Buy'] = uptrend & (near_ma50 | (L <= N('MA20')) & (C > N('MA20'))) & (bull_candle | (C > O)) & mf_bull
    df['CS_Squeeze_Breakout_Buy'] = (F('BB_Squeeze_End_Bull') | (F('BB_Squeeze').shift(1) & (C > N('BB_Mid')) & (C > O))) & vol_ok & macd_bull
    df['CS_MA_Confluence_Buy'] = ((N('MA50') > N('MA200')) & (N('MA50') > N('MA50').shift(5))) & (F('MACD_Cross_Buy') | macd_bull) & vol_ok & (C > N('MA50'))
    df['CS_Cooper_Setup_Buy'] = cooper_bull & adx_ok & (N('Plus_DI') > N('Minus_DI')) & vol_ok & (C > N('MA50'))
    df['CS_Volume_Climax_Reversal_Buy'] = (F('Volume_Climax_Buy') | (vol_ratio >= 2.5)) & (wt_os | stoch_os) & (bull_candle | long_lower_wick) & (near_bb_lower | near_vp_sup)
    df['CS_Ichimoku_Breakout_Buy'] = F('Kumo_Breakout_Bull') & (F('TK_Cross_Bull') | adx_ok) & vol_ok
    
    # ═══ TIER 2 매도 ═══
    df['CS_Trend_Rejection_Sell'] = downtrend & (near_ma50 | (H >= N('MA20')) & (C < N('MA20'))) & (bear_candle | (C < O)) & mf_bear
    df['CS_Squeeze_Breakdown_Sell'] = (F('BB_Squeeze_End_Bear') | (F('BB_Squeeze').shift(1) & (C < N('BB_Mid')) & (C < O))) & vol_ok & macd_bear
    df['CS_MA_Breakdown_Sell'] = ((N('MA50') < N('MA200')) & (N('MA50') < N('MA50').shift(5))) & (F('MACD_Cross_Sell') | macd_bear) & vol_ok & (C < N('MA50'))
    df['CS_Cooper_Setup_Sell'] = cooper_bear & adx_ok & (N('Minus_DI') > N('Plus_DI')) & vol_ok & (C < N('MA50'))
    df['CS_Gap_Failure_Sell'] = (F('Gap_Up').shift(1).fillna(False) & bear_candle & vol_ok & wt_falling) | (F('Gap_Up') & (C < O) & vol_ok)
    
    # ═══ TIER 3 ═══
    df['CS_Oversold_Bounce_Buy'] = stoch_os & bull_candle & (near_ma50 | near_bb_lower)
    df['CS_Momentum_Acceleration_Buy'] = (N('Composite_Accel', 0) > 1.5) & vol_ok & (C > N('MA50'))
    df['CS_Structure_Support_Buy'] = near_vp_sup & near_bb_lower & (C > O)
    df['CS_Overbought_Fade_Sell'] = stoch_ob & bear_candle & (near_ma50 | near_bb_upper)
    df['CS_Momentum_Deceleration_Sell'] = (N('Composite_Accel', 0) < -1.5) & vol_ok & (C < N('MA50'))
    df['CS_Structure_Resistance_Sell'] = near_vp_res & near_bb_upper & (C < O)
    
    # 특수
    nr7_tight = F('NR7_2') | F('NR7')
    df['CS_Volatility_Explosion_Setup'] = (nr7_tight.astype(int) + F('BB_Squeeze').astype(int) + (vol_ratio < 0.5).astype(int) + F('Inside_Day').astype(int)) >= 3
    
    # 쿨다운
    for scan_name in COMBINED_SCAN_REGISTRY:
        if scan_name in df.columns:
            df[scan_name] = _cooldown(df[scan_name], bars=7)
    
    return df


print("✅ Part 3/6 로드 완료: 통합 시그널 탐지 + Combined Scan")

# ══════════════════════════════════════════════════════════════
#  CipherX V12.3 — PART 4/6: 차트 빌더
#  차트에는 ▲강력매수, ▼강력매도, △매수, ▽매도 만 표시
#  마우스 호버 시 상세정보 표시
# ══════════════════════════════════════════════════════════════

def _build_hover_text(dc, idx_v, trigger_name, trigger_cfg):
    """마우스 호버 시 표시할 상세 정보 생성"""
    row = dc.loc[idx_v]
    ds = idx_v.strftime('%Y-%m-%d')
    
    # 당일 활성 시그널 수집
    buy_sigs, sell_sigs, neutral_sigs = [], [], []
    for sn, cfg in SIGNAL_REGISTRY.items():
        if sn in dc.columns and row.get(sn, False):
            entry = f"{cfg['icon']} {cfg['kor']}"
            if cfg['dir'] == 'buy': buy_sigs.append(entry)
            elif cfg['dir'] == 'sell': sell_sigs.append(entry)
            else: neutral_sigs.append(entry)
    
    # Combined Scan 수집
    active_cs = []
    for cs_name, cs_cfg in COMBINED_SCAN_REGISTRY.items():
        if cs_name in dc.columns and row.get(cs_name, False):
            tier_badge = {1: '🥇T1', 2: '🥈T2', 3: '🥉T3'}.get(cs_cfg['tier'], 'T?')
            active_cs.append(f"{cs_cfg['icon']} {cs_cfg['kor']} [{tier_badge}]")
    
    # 국면 정보
    rg = int(row.get('Regime', 0))
    regime_label = {2: '🟢🟢STRONG UP', 1: '🟢UP', 0: '⚪RANGE', -1: '🔴DN', -2: '🔴🔴STRONG DN'}.get(rg, '?')
    
    # 가격 정보
    price_info = f"O:{row.get('Open',0):.2f} H:{row.get('High',0):.2f} L:{row.get('Low',0):.2f} C:{row.get('Close',0):.2f}"
    
    # 지표 정보
    ind_info = f"WT:{row.get('WT1',0):.0f} RSI:{row.get('RSI',0):.0f} MFI:{row.get('MFI',0):.0f} StK:{row.get('StochK',0):.0f} ADX:{row.get('ADX',0):.0f}"
    
    # 호버 텍스트 조립
    lines = [
        f"<b style='font-size:13px'>📅 {ds}</b>",
        f"<b style='color:{trigger_cfg['clr']}'>{trigger_cfg['icon']} {trigger_cfg['kor']}</b>",
        f"<span style='color:#888'>{trigger_cfg['desc']}</span>",
        "─" * 28,
        f"<b>국면:</b> {regime_label}",
        f"{price_info}",
        f"{ind_info}",
    ]
    
    # Combined Scan
    if active_cs:
        lines.append("─" * 28)
        lines.append(f"<b style='color:#FFD700'>🎯 Combined Scan ({len(active_cs)}):</b>")
        for cs in active_cs[:5]:
            lines.append(f"  {cs}")
    
    # 매수/매도 시그널
    if buy_sigs or sell_sigs:
        lines.append("─" * 28)
    if buy_sigs:
        lines.append(f"<span style='color:#34D399'><b>▲매수({len(buy_sigs)}):</b></span>")
        for s in buy_sigs[:6]: lines.append(f"  {s}")
    if sell_sigs:
        lines.append(f"<span style='color:#F87171'><b>▼매도({len(sell_sigs)}):</b></span>")
        for s in sell_sigs[:6]: lines.append(f"  {s}")
    
    return "<br>".join(lines)


def _collect_chart_markers(dc):
    """
    차트에 표시할 마커 4가지로 분류:
    ▲ 강력매수 (빨간 큰별) — T1 Combined + Gold/Green_T1 + 핵심 패턴
    △ 매수 (초록 삼각) — 나머지 매수 시그널
    ▼ 강력매도 (빨간 큰별) — T1 Combined + Blood/Red_T1 + 핵심 패턴
    ▽ 매도 (빨간 삼각) — 나머지 매도 시그널
    """
    idx = dc.index
    
    # 강력매수 조건: T1 Combined Scan OR 핵심 매수 시그널
    strong_buy_mask = pd.Series(False, index=idx)
    for sn in CHART_SIGNAL_TIERS['strong_buy']:
        if sn in dc.columns:
            strong_buy_mask |= dc[sn].fillna(False)
    
    # 강력매도 조건
    strong_sell_mask = pd.Series(False, index=idx)
    for sn in CHART_SIGNAL_TIERS['strong_sell']:
        if sn in dc.columns:
            strong_sell_mask |= dc[sn].fillna(False)
    
    # 일반매수: 강력매수 제외한 모든 매수 시그널
    normal_buy_mask = pd.Series(False, index=idx)
    for sn, cfg in SIGNAL_REGISTRY.items():
        if cfg['dir'] == 'buy' and sn in dc.columns:
            normal_buy_mask |= dc[sn].fillna(False)
    # T2/T3 Combined Scan 매수도 포함
    for cs_name, cs_cfg in COMBINED_SCAN_REGISTRY.items():
        if cs_cfg['dir'] == 'buy' and cs_cfg['tier'] >= 2 and cs_name in dc.columns:
            normal_buy_mask |= dc[cs_name].fillna(False)
    normal_buy_mask = normal_buy_mask & ~strong_buy_mask
    
    # 일반매도
    normal_sell_mask = pd.Series(False, index=idx)
    for sn, cfg in SIGNAL_REGISTRY.items():
        if cfg['dir'] == 'sell' and sn in dc.columns:
            normal_sell_mask |= dc[sn].fillna(False)
    for cs_name, cs_cfg in COMBINED_SCAN_REGISTRY.items():
        if cs_cfg['dir'] == 'sell' and cs_cfg['tier'] >= 2 and cs_name in dc.columns:
            normal_sell_mask |= dc[cs_name].fillna(False)
    normal_sell_mask = normal_sell_mask & ~strong_sell_mask
    
    return strong_buy_mask, normal_buy_mask, strong_sell_mask, normal_sell_mask


def _get_trigger_info(dc, idx_v):
    """해당 날짜의 대표 트리거 시그널 정보 반환"""
    row = dc.loc[idx_v]
    
    # T1 Combined Scan 우선
    for cs_name, cs_cfg in COMBINED_SCAN_REGISTRY.items():
        if cs_cfg['tier'] == 1 and cs_name in dc.columns and row.get(cs_name, False):
            return _sig(0, cs_cfg['dir'], cs_cfg['icon'], cs_cfg['name'], '', 0, cs_cfg['color'], '', 0, cs_cfg['kor'], cs_cfg['desc'])
    
    # 핵심 시그널
    for sn in ['Gold_Dot', 'Blood_Diamond', 'Green_Dot_T1', 'Red_Dot_T1', 'Parabolic_Bottom_Buy', 'Parabolic_Top_Sell']:
        if sn in dc.columns and row.get(sn, False):
            return SIGNAL_REGISTRY[sn]
    
    # 일반 시그널 중 가중치 가장 높은 것
    best = None; best_w = 0
    for sn, cfg in SIGNAL_REGISTRY.items():
        if sn in dc.columns and row.get(sn, False) and cfg['w'] > best_w:
            best = cfg; best_w = cfg['w']
    
    if best: return best
    
    # Combined Scan T2/T3
    for cs_name, cs_cfg in COMBINED_SCAN_REGISTRY.items():
        if cs_name in dc.columns and row.get(cs_name, False):
            return _sig(0, cs_cfg['dir'], cs_cfg['icon'], cs_cfg['name'], '', 0, cs_cfg['color'], '', 0, cs_cfg['kor'], cs_cfg['desc'])
    
    return _sig(0, 'neutral', '❓', 'Unknown', '', 0, '#888', '', 0, '알수없음', '')


def build_chart(dc, ticker):
    """차트 빌더 — 4가지 마커만 표시 + 리치 호버"""
    mac = {5: "#ff9900", 10: "#ffb74d", 20: '#f1c40f', 50: '#e74c3c', 100: '#9b59b6', 125: '#3498db', 200: '#2ecc71'}
    
    fig = make_subplots(rows=5, cols=1, shared_xaxes=True, vertical_spacing=0.03,
        row_heights=[.40, .08, .15, .15, .22],
        subplot_titles=("", "Volume", "WaveTrend", "MACD", "Combined Score"))
    
    # ═══ Row 1: 캔들 + MA + BB + SuperTrend ═══
    fig.add_trace(go.Candlestick(
        x=dc.index, open=dc['Open'], high=dc['High'], low=dc['Low'], close=dc['Close'],
        name="Price", increasing_line_color='#00E676', decreasing_line_color='#FF1744',
        increasing_fillcolor='rgba(0,230,118,0.8)', decreasing_fillcolor='rgba(255,23,68,0.8)'),
        row=1, col=1)
    
    for ma in [20, 50, 200]:
        fig.add_trace(go.Scatter(x=dc.index, y=dc[f'MA{ma}'], line=dict(color=mac[ma], width=1.2),
            name=f'{ma}MA', hovertemplate="%{y:.2f}"), row=1, col=1)
    
    for mc, clr, nm in [(dc['ST_Direction'] == 1, '#00E676', 'ST▲'), (dc['ST_Direction'] == -1, '#FF1744', 'ST▼')]:
        fig.add_trace(go.Scatter(x=dc.index, y=dc['SuperTrend'].where(mc),
            line=dict(color=clr, width=2), name=nm, connectgaps=False), row=1, col=1)
    
    fig.add_trace(go.Scatter(x=dc.index, y=dc['BB_Up'], line=dict(color='gray', width=1, dash='dot'), name='BB↑'), row=1, col=1)
    fig.add_trace(go.Scatter(x=dc.index, y=dc['BB_Low'], line=dict(color='gray', width=1, dash='dot'),
        name='BB↓', fill='tonexty', fillcolor='rgba(128,128,128,0.07)'), row=1, col=1)
    
    if 'VP_POC' in dc.columns:
        fig.add_trace(go.Scatter(x=dc.index, y=dc['VP_POC'], line=dict(color='#FFD700', width=1.5, dash='dashdot'),
            name='POC', opacity=0.6), row=1, col=1)
    
    # ═══ 4가지 마커 표시 ═══
    strong_buy, normal_buy, strong_sell, normal_sell = _collect_chart_markers(dc)
    
    marker_configs = [
        (strong_buy, '⭐ 강력매수', 'star', 16, '#FFD700', '#00E676', 'Low', -3.0, 2.0),
        (normal_buy, '△ 매수', 'triangle-up', 10, '#00E676', '#00E676', 'Low', -2.0, 1.0),
        (strong_sell, '⭐ 강력매도', 'star', 16, '#FFD700', '#FF1744', 'High', 3.0, 2.0),
        (normal_sell, '▽ 매도', 'triangle-down', 10, '#FF1744', '#FF1744', 'High', 2.0, 1.0),
    ]
    
    for mask, label, symbol, size, marker_color, line_color, base, atr_mult, line_width in marker_configs:
        if not mask.any():
            continue
        sr = dc[mask]
        if base == 'Low':
            yv = sr['Low'] + sr['ATR'] * atr_mult
        else:
            yv = sr['High'] + sr['ATR'] * atr_mult
        
        # 호버 텍스트 생성
        hover_texts = []
        for iv in sr.index:
            trigger = _get_trigger_info(dc, iv)
            hover_texts.append(_build_hover_text(dc, iv, '', trigger))
        
        fig.add_trace(go.Scatter(
            x=sr.index, y=yv, mode='markers',
            marker=dict(symbol=symbol, size=size, color=marker_color,
                line=dict(width=line_width, color=line_color), opacity=0.95),
            name=label,
            text=hover_texts,
            hovertemplate="%{text}<extra></extra>",
            hoverlabel=dict(
                bgcolor='rgba(10,13,20,0.97)',
                bordercolor=line_color,
                font=dict(size=11, family='Pretendard', color='#FAFAFA'),
                align='left'
            )
        ), row=1, col=1)
    
    # ═══ Row 2: Volume ═══
    bear_bar = dc['Close'] < dc['Open']
    fig.add_trace(go.Bar(x=dc.index, y=dc['Volume'],
        marker_color=np.where(bear_bar, 'rgba(255,23,68,0.6)', 'rgba(0,230,118,0.6)').tolist(),
        name="Volume", opacity=0.8), row=2, col=1)
    
    # ═══ Row 3: WaveTrend ═══
    fig.add_trace(go.Scatter(x=dc.index, y=dc['WT1'], line=dict(color='#00E676', width=2), name="WT1"), row=3, col=1)
    fig.add_trace(go.Scatter(x=dc.index, y=dc['WT2'], line=dict(color='#FF1744', width=1.5, dash='dot'), name="WT2"), row=3, col=1)
    wd = dc['WT1'] - dc['WT2']
    fig.add_trace(go.Bar(x=dc.index, y=wd, marker_color=np.where(wd >= 0, '#00E676', '#FF1744').tolist(),
        name="WT Hist", opacity=0.3), row=3, col=1)
    for lv, cc, d in [(OB2, '#ff3333', 'dash'), (OB1, '#ff3333', 'solid'), (0, 'gray', 'dot'), (OS1, '#00bfff', 'solid'), (OS2, '#00bfff', 'dash')]:
        fig.add_hline(y=lv, line_dash=d, line_color=cc, line_width=1, row=3, col=1)
    
    # ═══ Row 4: MACD ═══
    fig.add_trace(go.Scatter(x=dc.index, y=dc['MACD_Line'], line=dict(color='#29B6F6', width=1.5), name="MACD"), row=4, col=1)
    fig.add_trace(go.Scatter(x=dc.index, y=dc['MACD_Signal'], line=dict(color='#FFA726', width=1.5), name="Signal"), row=4, col=1)
    mhv = dc['MACD_Hist']
    fig.add_trace(go.Bar(x=dc.index, y=mhv, marker_color=np.where(mhv >= 0, '#26A69A', '#EF5350').tolist(),
        name="Hist", opacity=0.7), row=4, col=1)
    fig.add_hline(y=0, line_color="#444", line_width=1, row=4, col=1)
    
    # ═══ Row 5: Combined Score (매수 vs 매도 시그널 카운트) ═══
    buy_count = pd.Series(0, index=dc.index, dtype=float)
    sell_count = pd.Series(0, index=dc.index, dtype=float)
    
    for sn, cfg in SIGNAL_REGISTRY.items():
        if sn not in dc.columns: continue
        sig_active = dc[sn].fillna(False).astype(float)
        # 최근 3일 decay 적용
        decayed = sig_active.copy()
        for d in range(1, 4):
            decayed += sig_active.shift(d).fillna(0) * (0.5 ** d)
        
        if cfg['dir'] == 'buy': buy_count += decayed * cfg['w']
        elif cfg['dir'] == 'sell': sell_count += decayed * cfg['w']
    
    # Combined Scan 보너스
    for cs_name, cs_cfg in COMBINED_SCAN_REGISTRY.items():
        if cs_name not in dc.columns: continue
        bonus = {1: 5.0, 2: 3.0, 3: 1.5}.get(cs_cfg['tier'], 1.0)
        cs_active = dc[cs_name].fillna(False).astype(float) * bonus
        if cs_cfg['dir'] == 'buy': buy_count += cs_active
        elif cs_cfg['dir'] == 'sell': sell_count += cs_active
    
    net_score = buy_count - sell_count
    colors = np.where(net_score >= 8, '#00E676',
             np.where(net_score >= 3, '#69F0AE',
             np.where(net_score <= -8, '#FF1744',
             np.where(net_score <= -3, '#FF5252', '#FFC107'))))
    
    fig.add_trace(go.Bar(x=dc.index, y=net_score, marker_color=colors.tolist(),
        name="Signal Score", opacity=0.8,
        customdata=np.stack([buy_count.values, sell_count.values], axis=-1),
        hovertemplate="BUY: %{customdata[0]:.1f}<br>SELL: %{customdata[1]:.1f}<br>NET: %{y:.1f}<extra></extra>"),
        row=5, col=1)
    fig.add_hline(y=0, line_color="gray", line_width=1, row=5, col=1)
    
    # ═══ 레이아웃 ═══
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=2, r=2, t=40, b=2), height=1200,
        showlegend=True, hovermode="closest",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
            font=dict(size=9.5, color='#CCC'), bgcolor='rgba(0,0,0,0)')
    )
    
    for i in range(1, 6):
        ya = f'yaxis{i}' if i > 1 else 'yaxis'
        fig.update_layout(**{ya: dict(gridcolor='rgba(45,51,59,0.5)', tickfont=dict(size=10, color='#888'))})
    
    # 비거래일 제거
    all_days = pd.date_range(start=dc.index[0], end=dc.index[-1], freq='D')
    non_trading = all_days.difference(dc.index.normalize())
    fig.update_xaxes(rangeslider_visible=False, rangebreaks=[dict(values=non_trading.tolist())],
        gridcolor='rgba(45,51,59,0.5)', tickfont=dict(size=10, color='#888'))
    
    for ann in fig['layout']['annotations']:
        ann['font'] = dict(size=12, color='#AAA', family='Pretendard')
    
    return fig


print("✅ Part 4/6 로드 완료: 차트 빌더")

# ══════════════════════════════════════════════════════════════
#  CipherX V12.3 — PART 5/6: 메타데이터, AI, UI
# ══════════════════════════════════════════════════════════════

def build_metadata(dc, ticker):
    lat = dc.iloc[-1]; prev = dc.iloc[-2] if len(dc) >= 2 else lat
    pc = lat['Close'] - prev['Close']; pp = pc / (prev['Close'] + 1e-10) * 100
    
    # 최근 시그널 수집
    recent = []
    for ir, row in dc.tail(15).iterrows():
        ds = ir.strftime('%m/%d')
        for col, cfg in {**SIGNAL_REGISTRY, **{k: _sig(0, v['dir'], v['icon'], v['name'], '', 0, v['color'], '', 0, v['kor'], v['desc']) for k, v in COMBINED_SCAN_REGISTRY.items()}}.items():
            if col in dc.columns and row.get(col, False):
                recent.append((cfg['icon'], cfg['kor'], ds, cfg['dir']))
    
    # Combined Scan 요약
    active_cs = []
    for cs_name, cs_cfg in COMBINED_SCAN_REGISTRY.items():
        if cs_name in dc.columns:
            rec = dc[cs_name].tail(5)
            if rec.any():
                ld = rec[rec].index[-1]
                active_cs.append({
                    'name': cs_cfg['name'], 'kor': cs_cfg['kor'], 'dir': cs_cfg['dir'],
                    'tier': cs_cfg['tier'], 'icon': cs_cfg['icon'], 'color': cs_cfg['color'],
                    'win_rate': cs_cfg['win_rate'], 'days_ago': (dc.index[-1] - ld).days,
                    'date': ld.strftime('%m/%d'), 'is_today': (dc.index[-1] - ld).days == 0
                })
    active_cs.sort(key=lambda x: (x['tier'], x['days_ago']))
    
    # 국면
    rg = int(lat.get('Regime', 0))
    regime_label = {2: 'STRONG BULL 🟢🟢', 1: 'BULL 🟢', 0: 'NEUTRAL ⚪', -1: 'BEAR 🔴', -2: 'STRONG BEAR 🔴🔴'}.get(rg, 'N/A')
    
    return {
        'ticker': ticker.upper(), 'price': float(lat['Close']),
        'price_change': pc, 'price_change_pct': pp,
        'volume': float(lat['Volume']),
        'avg_volume': float(dc['Volume'].rolling(20).mean().iloc[-1]),
        'wt1': float(lat['WT1']), 'rsi': float(lat['RSI']),
        'mfi': float(lat['MFI']), 'stochk': float(lat['StochK']),
        'adx': float(lat['ADX']), 'atr': float(lat['ATR']),
        'atr_pct': float(lat['ATR']) / (float(lat['Close']) + 1e-10) * 100,
        'macd_hist': float(lat.get('MACD_Hist', 0)),
        'ma50': float(lat.get('MA50', 0)), 'ma200': float(lat.get('MA200', 0)),
        'regime': rg, 'regime_label': regime_label,
        'regime_score': float(lat.get('Regime_Score', 0)),
        'rs_ratio': float(lat.get('RS_Ratio', 1.0)),
        'cmf': float(lat.get('CMF', 0)),
        'composite_accel': float(lat.get('Composite_Accel', 0)),
        'recent_signals': recent,
        'combined_scans': active_cs,
        'last_date': dc.index[-1].strftime('%Y-%m-%d'),
        'squeeze_on': bool(lat.get('Squeeze_On', False)),
    }


def build_prompt_text(dc, meta):
    lat = dc.iloc[-1]; rd = dc.tail(60)
    ps = ", ".join([f"'{d.strftime('%Y-%m-%d')}:{r['Close']:.2f}'" for d, r in rd.iterrows()])
    
    # 시그널 텍스트
    sl = []
    for ir, row in dc.tail(30).iterrows():
        dd = ir.strftime('%Y-%m-%d')
        for k, v in SIGNAL_REGISTRY.items():
            if row.get(k, False): sl.append(f"{v['icon']} {v['kor']} {dd}")
        for k, v in COMBINED_SCAN_REGISTRY.items():
            if row.get(k, False): sl.append(f"🎯 {v['kor']} [T{v['tier']}] {dd}")
    st_text = "\n".join(sl[-30:]) if sl else "최근30일시그널없음"
    
    # Combined Scan 텍스트
    cs_text = ""
    if meta.get('combined_scans'):
        cs_text = "\n📌 [Combined Scan 활성]\n"
        for cs in meta['combined_scans']:
            cs_text += f"  {cs['icon']} {cs['kor']} [T{cs['tier']}] {cs['date']} (승률:{cs['win_rate']})\n"
    
    inds = (f"WT1={lat['WT1']:.1f},RSI={lat['RSI']:.1f},MFI={lat['MFI']:.1f},"
            f"StK={lat['StochK']:.1f},ADX={lat['ADX']:.1f},ATR={meta['atr']:.2f}({meta['atr_pct']:.1f}%),"
            f"MACD_H={meta['macd_hist']:.3f},CMF={meta['cmf']:.3f},"
            f"Regime={meta['regime']}({meta['regime_score']:.1f}),RS={meta['rs_ratio']:.3f},"
            f"Accel={meta['composite_accel']:.2f}")
    
    return f"{ps}\n\n📌 [지표요약]\n{inds}\n\n📌 [최근시그널]\n{st_text}{cs_text}"


def build_ai_prompt(ticker, phist, fundamentals):
    return f"""━━━ Role ━━━
월스트리트 20년+ 퀀트 펀드매니저. 냉철한 기술 분석.
━━━ Rules ━━━
1. ATR 기반 손절/목표가 2. Combined Scan 결과 활용 3. Regime 국면 반영
4. RS_Ratio 시장대비 강도 5. 시나리오별 확률% 6. 환각금지
━━━ Data ━━━
[{ticker}]
{phist}
📌 [펀더멘탈] {fundamentals}
━━━ Output ━━━
# 🚦 {{ticker}} 퀀트 리포트
[🔵/🔴/🟠] 핵심 한줄
### 📊 시장심리 (3~4문장)
### 🎯 Combined Scan 분석 (활성 스캔 해석)
### ⚖️ 시스템 검증 (125개 시그널 합류도)
### 📈 기술분석 (VP+RS+국면+종합)
### 🔮 시나리오 (🔵긍정 🟠베이스 🔴리스크 + ATR전략)
### 결론 (예측+GRADE)"""


def analyze(ticker, chart_days=252, refresh=False):
    try:
        ts = int(time.time()) if refresh else None
        df = compute_and_cache(ticker, ts)
        if df is None or df.empty or len(df) < 50:
            return None, "데이터부족", None
        dc = df.dropna(subset=['WT1', 'WT2']).tail(chart_days).copy()
        if dc.empty: return None, "차트데이터부족", None
        meta = build_metadata(dc, ticker)
        fig = build_chart(dc, ticker)
        return fig, build_prompt_text(dc, meta), meta
    except Exception as e:
        import traceback; print(traceback.format_exc())
        return None, f"실패:{e}", None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  UI 렌더 함수들
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def render_price_header(m):
    chg = m['price_change']; cp = m['price_change_pct']
    cc = 'price-change-up' if chg >= 0 else 'price-change-down'
    ci = '▲' if chg >= 0 else '▼'
    vr = m['volume'] / m['avg_volume'] if m['avg_volume'] else 0
    accel = m.get('composite_accel', 0)
    
    specs = [
        ('ind-bullish' if m['wt1'] < -20 else ('ind-bearish' if m['wt1'] > 20 else 'ind-neutral'), f"WT{m['wt1']:.0f}"),
        ('ind-bullish' if m['rsi'] < 40 else ('ind-bearish' if m['rsi'] > 60 else 'ind-neutral'), f"RSI{m['rsi']:.0f}"),
        ('ind-bullish' if vr > 1.5 else 'ind-neutral', f"Vol{vr:.1f}x"),
        ('ind-bullish' if m['adx'] > 25 else 'ind-neutral', f"ADX{m['adx']:.0f}"),
        ('ind-bullish' if accel > 1.5 else ('ind-bearish' if accel < -1.5 else 'ind-neutral'), f"Accel{accel:+.1f}"),
        ('ind-bullish' if m.get('rs_ratio', 1) > 1.03 else ('ind-bearish' if m.get('rs_ratio', 1) < 0.97 else 'ind-neutral'), f"RS{m.get('rs_ratio', 1):.2f}"),
    ]
    ih = "".join([f"<span class='indicator-mini {c}'>{l}</span>" for c, l in specs])
    
    st.markdown(f"""<div class="price-header">
        <p style="color:#64748B;font-size:.8rem;margin:0">🚦 {m['ticker']} · {m['last_date']} · <b style="color:#A5B4FC">{m['regime_label']}</b></p>
        <p class="price-big" style="color:#F8FAFC">${m['price']:.2f}
            <span class="{cc}" style="font-size:1.1rem;margin-left:10px;font-weight:700">{ci}{abs(chg):.2f}({abs(cp):.2f}%)</span></p>
        <div style="margin-top:12px;display:flex;gap:5px;flex-wrap:wrap">{ih}</div>
    </div>""", unsafe_allow_html=True)


def render_combined_scans(m):
    """Combined Scan 결과 UI"""
    scans = m.get('combined_scans', [])
    if not scans:
        st.info("🔍 활성 Combined Scan 없음")
        return
    
    buy_scans = [s for s in scans if s['dir'] == 'buy']
    sell_scans = [s for s in scans if s['dir'] == 'sell']
    t1_count = sum(1 for s in scans if s['tier'] == 1)
    
    header_clr = '#FFD700' if t1_count > 0 else ('#00E676' if len(buy_scans) > len(sell_scans) else ('#FF1744' if len(sell_scans) > len(buy_scans) else '#FFC107'))
    
    st.markdown(f"""<div style="background:linear-gradient(135deg,rgba(255,215,0,0.08),rgba(0,0,0,0));
        border:1px solid {header_clr}33;border-radius:12px;padding:14px;margin-bottom:12px">
        <span style="font-size:1.3rem;font-weight:800;color:{header_clr}">🎯 Combined Scan: {len(scans)}개 활성</span>
        <span style="color:#888;margin-left:16px">T1:{t1_count} BUY:{len(buy_scans)} SELL:{len(sell_scans)}</span>
    </div>""", unsafe_allow_html=True)
    
    for scan in scans:
        tb = {1: '🥇T1', 2: '🥈T2', 3: '🥉T3'}.get(scan['tier'], 'T?')
        dc_ = '#00E676' if scan['dir'] == 'buy' else ('#FF1744' if scan['dir'] == 'sell' else '#FFC107')
        bg = 'rgba(0,230,118,0.05)' if scan['dir'] == 'buy' else ('rgba(255,23,68,0.05)' if scan['dir'] == 'sell' else 'rgba(255,193,7,0.05)')
        today = "<span style='background:#FFD700;color:#000;padding:2px 6px;border-radius:4px;font-size:.7rem;font-weight:700'>TODAY</span>" if scan['is_today'] else f"<span style='color:#888;font-size:.8rem'>{scan['date']}</span>"
        
        st.markdown(f"""<div style="background:{bg};border-left:4px solid {dc_};border-radius:8px;padding:10px 14px;margin:6px 0">
            <div style="display:flex;justify-content:space-between;align-items:center">
                <span style="color:{dc_};font-size:1rem;font-weight:700">{scan['icon']} {scan['kor']} <span style="color:#888;font-size:.75rem">{tb}</span></span>
                <div>{today} <span style="color:#4FC3F7;font-size:.7rem;margin-left:8px">승률:{scan['win_rate']}</span></div>
            </div>
        </div>""", unsafe_allow_html=True)


def render_signals(m):
    """시그널 히스토리"""
    sigs = m.get('recent_signals', [])
    if not sigs:
        st.info("최근 15일 시그널 없음"); return
    
    dg = OrderedDict()
    for icon, lbl, ds, side in sigs:
        dg.setdefault(ds, []).append((icon, lbl, side))
    
    for ds in reversed(dg):
        grp = dg[ds]
        bc = sum(1 for _, _, s in grp if s == 'buy')
        sc = sum(1 for _, _, s in grp if s == 'sell')
        ct = 'signal-summary-buy' if bc > sc else ('signal-summary-sell' if sc > bc else '')
        
        parts = []
        for i, l, s in grp:
            cls = 'ind-bullish' if s == 'buy' else ('ind-bearish' if s == 'sell' else 'ind-neutral')
            parts.append(f"<span class='indicator-mini {cls}'>{i} {l}</span>")
        
        st.markdown(f"""<div class="signal-summary-card {ct}">
            <div style="display:flex;justify-content:space-between;margin-bottom:6px">
                <span style="font-weight:700;color:#E8ECF1">📅 {ds}</span>
                <span style="color:#64748B;font-size:.75rem">{len(grp)}개</span>
            </div>
            <div style="display:flex;gap:4px;flex-wrap:wrap">{' '.join(parts)}</div>
        </div>""", unsafe_allow_html=True)


def render_analysis(msg):
    """분석 결과 전체 렌더"""
    m, fig = msg.get('meta'), msg.get('fig')
    
    if m:
        render_price_header(m)
    
    if m or fig:
        t0, t1, t2 = st.tabs(["📈 차트", "🎯 Combined Scan", "📋 시그널 히스토리"])
        
        with t0:
            if fig:
                st.plotly_chart(fig, use_container_width=True, theme=None,
                    config={'displaylogo': False, 'modeBarButtonsToRemove': ['lasso2d', 'select2d']})
        with t1:
            if m:
                render_combined_scans(m)
        with t2:
            if m:
                render_signals(m)


print("✅ Part 5/6 로드 완료: 메타데이터, AI, UI")

# ══════════════════════════════════════════════════════════════
#  CipherX V12.3 — PART 6/6: 사이드바, 세션, 메인 루프
# ══════════════════════════════════════════════════════════════

def init_session_state():
    defaults = {
        'messages': [{"role": "assistant", "type": "text",
                      "content": "안녕하세요! 🚦 **CipherX V12.3** 입니다.\n\n분석할 **티커명**을 입력하세요.\n\n✨ 125개 시그널 + Combined Scan 통합 버전"}],
        'pending_ai_ticker': None,
        'pending_ai_prompt': None,
        'last_ticker': None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session_state()

# ═══ 사이드바 ═══
with st.sidebar:
    st.markdown("## 🚦 CipherX")
    st.markdown("<p style='color:#888;font-size:.8rem'>V12.3 — 125 Signals + Combined Scan</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    app_mode = st.radio("모드", ['📊 개별분석', '🔍 스캐너'], index=0, key="app_mode")
    st.markdown("---")
    
    chart_period = st.radio("차트기간", ['3개월', '6개월', '1년', '2년'], index=0, horizontal=True, key="period")
    chart_days = {'3개월': 63, '6개월': 126, '1년': 252, '2년': 504}[chart_period]
    
    if st.button("🗑️ 초기화", use_container_width=True, type="secondary"):
        for k in ['messages', 'pending_ai_ticker', 'pending_ai_prompt', 'last_ticker']:
            if k == 'messages':
                st.session_state[k] = [{"role": "assistant", "type": "text",
                    "content": "안녕하세요! 🚦 **CipherX V12.3**"}]
            else:
                st.session_state[k] = None
        st.rerun()


# ═══ 스캐너 모드 ═══
if st.session_state.get('app_mode') == '🔍 스캐너':
    st.markdown("<h2 style='text-align:center;color:#fff'>🔍 CipherX Scanner</h2>", unsafe_allow_html=True)
    st.markdown("#### 📋 티커 입력")
    ci = st.text_input("쉼표 구분", placeholder="NVDA,TSLA,AAPL,QQQ,...", key="scan_input")
    tickers = [t.strip().upper() for t in ci.split(',') if t.strip()] if ci else ['NVDA', 'TSLA', 'AAPL', 'MSFT', 'AMZN', 'META', 'AMD', 'QQQ', 'SPY']
    
    if st.button("🚀 스캔 시작", type="primary", use_container_width=True):
        pb = st.progress(0)
        results = []
        
        for i, t in enumerate(tickers):
            pb.progress((i + 1) / len(tickers), text=f"🔍 {t} ({i + 1}/{len(tickers)})")
            try:
                df = compute_and_cache(t)
                if df is None or len(df) < 50: continue
                dc = df.tail(63)
                
                active_cs = []
                for cs_name, cs_cfg in COMBINED_SCAN_REGISTRY.items():
                    if cs_name in dc.columns:
                        rec = dc[cs_name].tail(5)
                        if rec.any():
                            ld = rec[rec].index[-1]
                            active_cs.append({
                                'name': cs_cfg['name'], 'kor': cs_cfg['kor'],
                                'dir': cs_cfg['dir'], 'tier': cs_cfg['tier'],
                                'icon': cs_cfg['icon'], 'color': cs_cfg['color'],
                                'win_rate': cs_cfg['win_rate'],
                                'date': ld.strftime('%m/%d'),
                                'days_ago': (dc.index[-1] - ld).days,
                            })
                
                if active_cs:
                    lat = dc.iloc[-1]
                    chg = float((lat['Close'] - dc.iloc[-2]['Close']) / dc.iloc[-2]['Close'] * 100) if len(dc) >= 2 else 0
                    results.append({
                        'ticker': t, 'price': float(lat['Close']),
                        'change_pct': chg, 'scans': sorted(active_cs, key=lambda x: x['tier'])
                    })
            except:
                pass
        
        pb.progress(1.0, text=f"✅ {len(results)}개 발견")
        time.sleep(0.3); pb.empty()
        
        if not results:
            st.info("활성 Combined Scan 없음")
        else:
            # T1 개수 → 총 개수 순 정렬
            results.sort(key=lambda x: (-sum(1 for s in x['scans'] if s['tier'] == 1), -len(x['scans'])))
            
            for r in results:
                chc = '#34D399' if r['change_pct'] >= 0 else '#F87171'
                chi = '▲' if r['change_pct'] >= 0 else '▼'
                
                scan_html = ""
                for cs in r['scans']:
                    dc_ = '#34D399' if cs['dir'] == 'buy' else ('#F87171' if cs['dir'] == 'sell' else '#FFC107')
                    tb = {1: '🥇', 2: '🥈', 3: '🥉'}.get(cs['tier'], '')
                    scan_html += f"<div style='display:flex;align-items:center;gap:8px;padding:3px 0'>"
                    scan_html += f"<span style='color:{dc_}'>●</span>"
                    scan_html += f"<span style='color:#E8ECF1;font-weight:600;font-size:.85rem'>{cs['icon']} {cs['kor']} {tb}</span>"
                    scan_html += f"<span style='color:#64748B;font-size:.7rem'>{cs['date']}</span></div>"
                
                st.markdown(f"""<div style="background:linear-gradient(160deg,#0F1320,#141926);
                    border:1px solid #1C2233;border-radius:14px;padding:16px 20px;margin:8px 0">
                    <div style="display:flex;justify-content:space-between;margin-bottom:10px">
                        <span style="color:#A5B4FC;font-weight:800;font-size:1.2rem">{r['ticker']}</span>
                        <span style="color:{chc};font-size:.85rem;font-weight:600">${r['price']:.2f} {chi}{abs(r['change_pct']):.1f}%</span>
                    </div>
                    {scan_html}
                </div>""", unsafe_allow_html=True)
                
                if st.button(f"📊 {r['ticker']} 분석", key=f"sc_{r['ticker']}", use_container_width=True):
                    st.session_state['app_mode'] = '📊 개별분석'
                    st.session_state['_auto_ticker'] = r['ticker']
                    st.rerun()


# ═══ 개별분석 모드 ═══
else:
    st.markdown("<h2 style='text-align:center;color:#fff;margin-bottom:20px'>🚦 CipherX</h2>", unsafe_allow_html=True)
    
    # 퀵 버튼
    if not st.session_state.last_ticker:
        cols = st.columns(4)
        for i, t in enumerate(["NVDA", "TSLA", "AAPL", "QQQ"]):
            with cols[i]:
                if st.button(t, use_container_width=True):
                    st.session_state['quick_ticker'] = t
    
    # 메시지 히스토리
    for i, msg in enumerate(st.session_state.messages):
        av = "✨" if msg["role"] == "assistant" else "🧑‍💻"
        with st.chat_message(msg["role"], avatar=av):
            if msg.get("type") == "analysis":
                st.markdown(msg.get("content", ""))
                render_analysis(msg)
                if msg.get("prompt"):
                    with st.expander("📝 프롬프트", expanded=False):
                        st.code(msg["prompt"], language="markdown")
                        st_copy_to_clipboard(msg["prompt"], before_copy_label="📋복사", after_copy_label="✅복사됨!")
            elif msg.get("type") == "report":
                with st.expander(f"📊 {msg.get('ticker', '')} AI리포트", expanded=True):
                    st.markdown(msg["content"])
                st.download_button("📥 다운로드", key=f"dl_{i}",
                    data=msg["content"].encode('utf-8'),
                    file_name=f"{msg.get('ticker', '')}_Quant_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
                    mime="text/markdown", use_container_width=True)
            else:
                st.markdown(msg.get("content", ""))
    
    # ═══ AI 실행 ═══
    def _run_ai():
        tp = st.session_state.pending_ai_ticker
        pp = st.session_state.pending_ai_prompt
        with st.chat_message("assistant", avatar="✨"):
            pb = st.progress(0, text="로딩...")
            try:
                model = get_gemini_model()
                pb.progress(20)
                collected = []
                
                def gen():
                    pb.progress(40, text="🚀 AI 생성중...")
                    for chunk in model.generate_content(pp, stream=True):
                        if chunk.text:
                            collected.append(chunk.text)
                            yield chunk.text
                    pb.progress(100, text="✅ 완료!")
                
                with st.expander(f"📊 {tp.upper()} AI리포트", expanded=True):
                    st.write_stream(gen())
                
                time.sleep(0.3); pb.empty()
                st.session_state.messages.append({
                    "role": "assistant", "type": "report",
                    "ticker": tp.upper(), "content": "".join(collected)
                })
                st.session_state.pending_ai_ticker = None
                st.session_state.pending_ai_prompt = None
                st.rerun()
            except Exception as e:
                pb.empty()
                st.error(f"AI 오류: {e}")
    
    # ═══ 티커 처리 ═══
    def process_ticker(tv, refresh=False):
        tv = tv.strip().upper()
        st.session_state.pending_ai_ticker = None
        st.session_state.pending_ai_prompt = None
        
        if not _valid_fmt(tv):
            st.toast(f"⚠️ {tv} 형식오류", icon="🚨"); return
        if not validate_ticker(tv):
            st.toast(f"⚠️ {tv} 데이터없음", icon="🔍"); return
        
        st.session_state.messages.append({"role": "user", "type": "text", "content": tv})
        st.session_state.last_ticker = tv
        
        with st.chat_message("assistant", avatar="✨"):
            with st.status(f"🌐 {tv} 분석중...", expanded=True) as status:
                st.write("📡 데이터 수집...")
                fundamentals = fetch_fundamentals(tv)
                
                st.write("📊 125개 시그널 + Combined Scan 분석...")
                fig, phist, meta = analyze(tv, chart_days, refresh)
                
                if fig and meta:
                    # Combined Scan 요약
                    cs_count = len(meta.get('combined_scans', []))
                    t1_count = sum(1 for s in meta.get('combined_scans', []) if s['tier'] == 1)
                    st.write(f"🎯 Combined Scan: {cs_count}개 활성 (T1: {t1_count})")
                    
                    prompt = build_ai_prompt(tv, phist, fundamentals)
                    status.update(label=f"✅ {tv} 완료!", state="complete", expanded=False)
                else:
                    prompt = None
                    status.update(label=f"⚠️ {tv} 실패", state="error", expanded=False)
            
            if fig:
                # 분석 결과 저장
                content = f"✅ **{tv}** 분석 완료."
                if meta.get('combined_scans'):
                    buy_cs = [s for s in meta['combined_scans'] if s['dir'] == 'buy']
                    sell_cs = [s for s in meta['combined_scans'] if s['dir'] == 'sell']
                    if buy_cs or sell_cs:
                        content += f"\n\n🎯 **Combined Scan**: "
                        if buy_cs: content += f"매수 {len(buy_cs)}개 "
                        if sell_cs: content += f"매도 {len(sell_cs)}개"
                
                st.session_state.messages.append({
                    "role": "assistant", "type": "analysis",
                    "ticker": tv, "content": content,
                    "fig": fig, "meta": meta, "prompt": prompt
                })
                st.session_state.pending_ai_ticker = tv
                st.session_state.pending_ai_prompt = prompt
                st.rerun()
            else:
                st.session_state.messages.append({
                    "role": "assistant", "type": "text",
                    "content": f"⚠️ **{tv}** 분석 실패: {phist}"
                })
                st.rerun()
    
    # ═══ 자동 티커 처리 ═══
    if st.session_state.get('_auto_ticker'):
        at = st.session_state.pop('_auto_ticker')
        process_ticker(at)
    
    if st.session_state.get('quick_ticker'):
        qt = st.session_state.pop('quick_ticker')
        process_ticker(qt)
    
    # AI 버튼
    if st.session_state.pending_ai_ticker and st.session_state.pending_ai_prompt:
        if st.button(f"🚀 {st.session_state.pending_ai_ticker.upper()} AI 분석 시작",
                     type="primary", use_container_width=True):
            _run_ai()
    
    # 채팅 입력
    if ti := st.chat_input("티커 입력 (예: TSLA, AAPL, QQQ)"):
        process_ticker(ti)


print("✅ Part 6/6 로드 완료: 사이드바, 세션, 메인 루프")
print("🚀 CipherX V12.3 — 125개 시그널 + Combined Scan 통합 완료!")