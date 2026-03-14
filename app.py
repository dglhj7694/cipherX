import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import google.generativeai as genai
import time
import random
import io
from datetime import datetime
from st_copy_to_clipboard import st_copy_to_clipboard
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from plotly.subplots import make_subplots

st.set_page_config(page_title="CipherX", page_icon="📈", layout="centered")

# ──────────────────────────────────────────
# 🎨 CSS
# ──────────────────────────────────────────
st.markdown("""
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
html, body, [class*="css"] { font-family: 'Pretendard', 'Noto Sans KR', sans-serif !important; }
.stApp { background-color: #0E1117; }
p, div[data-testid="stMarkdownContainer"] p,
div[data-testid="stChatMessageContent"] p,
h1, h2, h3, h4, h5, h6, li { color: #FAFAFA !important; }
div[data-testid="stCodeBlock"], pre, code {
    background-color: #1A1D24 !important; color: #FAFAFA !important;
}
div[data-testid="stCodeBlock"] span { text-shadow: none !important; }
div[data-testid="stCodeBlock"] span[style*="color: rgb(0, 0, 0)"],
div[data-testid="stCodeBlock"] span[style*="color: black"],
div[data-testid="stCodeBlock"] code > span:not([class]) { color: #FAFAFA !important; }
div[data-testid="stChatMessage"]:nth-child(even) {
    background-color: #161A22; border-radius: 12px; padding: 5px 15px;
}
header {visibility: hidden;}
.block-container { padding-top: 1rem !important; max-width: 900px; }
div.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    color: white !important; border: none !important; border-radius: 12px !important;
    padding: 0.6rem 1.5rem !important; font-weight: 600 !important;
    font-size: 1rem !important; transition: all 0.3s ease !important; width: 100%;
}
div.stButton > button[kind="primary"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 20px rgba(118, 75, 162, 0.4) !important;
}
div.stButton > button[kind="secondary"] {
    background-color: #1E2127 !important; color: #E2E8F0 !important;
    border: 1px solid #333842 !important; border-radius: 12px !important;
    font-weight: 500 !important; transition: all 0.2s ease !important; width: 100%;
}
div.stButton > button[kind="secondary"]:hover {
    border-color: #667eea !important; color: #667eea !important;
}
.streamlit-expanderHeader {
    background-color: #161A22 !important; border-radius: 10px !important; font-weight: 600 !important;
}
.streamlit-expanderHeader p { color: #414df2 !important; }
div[data-testid="stExpander"] {
    border: 1px solid #2D333B !important; border-radius: 10px !important; background-color: #161A22;
}
section[data-testid="stSidebar"] {
    background-color: #0A0D12; border-right: 1px solid #1E2127;
}
section[data-testid="stSidebar"] .stMarkdown p { color: #AAAAAA !important; }
.signal-card {
    border-radius: 12px; padding: 16px 20px; margin: 6px 0; border: 1px solid #2D333B;
}
.signal-card-buy {
    background: linear-gradient(135deg, rgba(0,230,118,0.08) 0%, rgba(0,191,255,0.05) 100%);
    border-left: 4px solid #00E676;
}
.signal-card-sell {
    background: linear-gradient(135deg, rgba(255,23,68,0.08) 0%, rgba(255,82,82,0.05) 100%);
    border-left: 4px solid #FF1744;
}
.signal-card-neutral {
    background: linear-gradient(135deg, rgba(255,193,7,0.08) 0%, rgba(255,152,0,0.05) 100%);
    border-left: 4px solid #FFC107;
}
.price-header {
    background: linear-gradient(135deg, #161A22 0%, #1A1F2E 100%);
    border: 1px solid #2D333B; border-radius: 14px;
    padding: 18px 24px; margin-bottom: 16px;
}
.price-big { font-size: 2rem; font-weight: 700; margin: 0; }
.price-change-up { color: #00E676 !important; }
.price-change-down { color: #FF1744 !important; }
.price-label { color: #666 !important; font-size: 0.8rem; margin: 0; }
.indicator-mini {
    display: inline-block; padding: 4px 10px; margin: 2px;
    border-radius: 6px; font-size: 0.78rem; font-weight: 500;
}
.ind-bullish { background: rgba(0,230,118,0.15); color: #00E676; }
.ind-bearish { background: rgba(255,23,68,0.15); color: #FF1744; }
.ind-neutral { background: rgba(255,193,7,0.15); color: #FFC107; }
.bias-gauge-track {
    height: 8px; border-radius: 4px; margin: 8px 0;
    background: linear-gradient(90deg, #FF1744 0%, #FF1744 20%, #FFC107 35%, #888 50%, #FFC107 65%, #00E676 80%, #00E676 100%);
    position: relative;
}
.bias-gauge-needle {
    width: 4px; height: 16px; background: white; border-radius: 2px;
    position: absolute; top: -4px; transform: translateX(-50%);
    box-shadow: 0 0 6px rgba(255,255,255,0.5);
}
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────
# 시그널 레지스트리
# ──────────────────────────────────────────
SIGNAL_REGISTRY = {
    'Gold_Dot':          {'w': 3.0, 'dir': 'buy',  'icon': '🏆', 'label': 'GOLD DOT',       'sym': 'circle',         'sz': 18, 'clr': '#FFD700', 'base': 'Low',  'atr_m': -3.0},
    'Green_Dot_T1':      {'w': 2.5, 'dir': 'buy',  'icon': '🟢', 'label': 'BUY T1',         'sym': 'circle',         'sz': 16, 'clr': '#00E676', 'base': 'Low',  'atr_m': -2.5},
    'Green_Dot_T2':      {'w': 2.0, 'dir': 'buy',  'icon': '🟩', 'label': 'BUY T2',         'sym': 'circle',         'sz': 13, 'clr': '#69F0AE', 'base': 'Low',  'atr_m': -2.2},
    'Blue_Diamond':      {'w': 2.0, 'dir': 'buy',  'icon': '🔹', 'label': 'BLUE DIA',       'sym': 'diamond',        'sz': 14, 'clr': '#00bfff', 'base': 'Low',  'atr_m': -1.8},
    'Green_Circle':      {'w': 1.5, 'dir': 'buy',  'icon': '✅', 'label': 'BUY Circle',     'sym': 'circle-open',    'sz': 11, 'clr': '#00E676', 'base': 'Low',  'atr_m': -1.2},
    'Bull_Divergence':   {'w': 2.0, 'dir': 'buy',  'icon': '📈', 'label': 'Bull Div',       'sym': 'triangle-up',    'sz': 12, 'clr': '#AA00FF', 'base': 'Low',  'atr_m': -2.0},
    'Squeeze_Fire_Buy':  {'w': 1.5, 'dir': 'buy',  'icon': '💥', 'label': 'Squeeze BUY',    'sym': 'star-diamond',   'sz': 14, 'clr': '#00FFFF', 'base': 'Low',  'atr_m': -1.5},
    'Hidden_Bull_Div':   {'w': 1.5, 'dir': 'buy',  'icon': '🔀', 'label': 'Hidden Bull',    'sym': 'triangle-up',    'sz': 10, 'clr': '#E040FB', 'base': 'Low',  'atr_m': -1.6},
    'Volume_Climax_Buy': {'w': 2.0, 'dir': 'buy',  'icon': '🌊', 'label': 'Vol Climax BUY', 'sym': 'hexagram',       'sz': 14, 'clr': '#00BCD4', 'base': 'Low',  'atr_m': -2.8},
    'OBV_Div_Buy':       {'w': 1.5, 'dir': 'buy',  'icon': '📊', 'label': 'OBV Div BUY',   'sym': 'triangle-up',    'sz': 10, 'clr': '#80DEEA', 'base': 'Low',  'atr_m': -1.4},
    'ADX_Momentum_Buy':  {'w': 1.5, 'dir': 'buy',  'icon': '🚀', 'label': 'ADX Ignition',   'sym': 'arrow-up',       'sz': 11, 'clr': '#76FF03', 'base': 'Low',  'atr_m': -1.4},
    'Fib_Bounce_Buy':    {'w': 1.0, 'dir': 'buy',  'icon': '📐', 'label': 'Fib Bounce',     'sym': 'diamond-open',   'sz': 10, 'clr': '#FFAB00', 'base': 'Low',  'atr_m': -1.0},
    'Bullish_Engulfing':  {'w': 1.5, 'dir': 'buy',  'icon': '☀️', 'label': 'Bull Engulf',   'sym': 'square',         'sz': 10, 'clr': '#00E676', 'base': 'Low',  'atr_m': -1.3},
    'Golden_Cross':      {'w': 1.5, 'dir': 'buy',  'icon': '✨', 'label': 'Golden Cross',   'sym': 'cross',          'sz': 12, 'clr': '#FFD700', 'base': 'Low',  'atr_m': -0.8},
    'Blood_Diamond':     {'w': 3.0, 'dir': 'sell', 'icon': '🩸', 'label': 'BLOOD DIA',      'sym': 'diamond',        'sz': 18, 'clr': '#DC143C', 'base': 'High', 'atr_m': 3.0},
    'Red_Dot_T1':        {'w': 2.5, 'dir': 'sell', 'icon': '🔴', 'label': 'SELL T1',        'sym': 'circle',         'sz': 16, 'clr': '#FF1744', 'base': 'High', 'atr_m': 2.5},
    'Red_Dot_T2':        {'w': 2.0, 'dir': 'sell', 'icon': '🟥', 'label': 'SELL T2',        'sym': 'circle',         'sz': 13, 'clr': '#FF5252', 'base': 'High', 'atr_m': 2.2},
    'Red_Diamond':       {'w': 2.0, 'dir': 'sell', 'icon': '🔸', 'label': 'RED DIA',        'sym': 'diamond',        'sz': 14, 'clr': '#ff3333', 'base': 'High', 'atr_m': 1.8},
    'Red_Circle':        {'w': 1.5, 'dir': 'sell', 'icon': '⛔', 'label': 'SELL Circle',    'sym': 'circle-open',    'sz': 11, 'clr': '#FF1744', 'base': 'High', 'atr_m': 1.2},
    'Bear_Divergence':   {'w': 2.0, 'dir': 'sell', 'icon': '📉', 'label': 'Bear Div',       'sym': 'triangle-down',  'sz': 12, 'clr': '#AA00FF', 'base': 'High', 'atr_m': 2.0},
    'Squeeze_Fire_Sell': {'w': 1.5, 'dir': 'sell', 'icon': '🧨', 'label': 'Squeeze SELL',   'sym': 'star-diamond',   'sz': 14, 'clr': '#FF6600', 'base': 'High', 'atr_m': 1.5},
    'Hidden_Bear_Div':   {'w': 1.5, 'dir': 'sell', 'icon': '🔁', 'label': 'Hidden Bear',    'sym': 'triangle-down',  'sz': 10, 'clr': '#E040FB', 'base': 'High', 'atr_m': 1.6},
    'Volume_Climax_Sell':{'w': 2.0, 'dir': 'sell', 'icon': '🌋', 'label': 'Vol Climax SELL','sym': 'hexagram',       'sz': 14, 'clr': '#FF5722', 'base': 'High', 'atr_m': 2.8},
    'OBV_Div_Sell':      {'w': 1.5, 'dir': 'sell', 'icon': '🔻', 'label': 'OBV Div SELL',  'sym': 'triangle-down',  'sz': 10, 'clr': '#FFAB91', 'base': 'High', 'atr_m': 1.4},
    'ADX_Momentum_Sell': {'w': 1.5, 'dir': 'sell', 'icon': '💨', 'label': 'ADX Down',       'sym': 'arrow-down',     'sz': 11, 'clr': '#FF3D00', 'base': 'High', 'atr_m': 1.4},
    'Fib_Resistance_Sell':{'w': 1.0, 'dir': 'sell','icon': '🚧', 'label': 'Fib Resist',     'sym': 'diamond-open',   'sz': 10, 'clr': '#FF8F00', 'base': 'High', 'atr_m': 1.0},
    'Bearish_Engulfing':  {'w': 1.5, 'dir': 'sell','icon': '🌑', 'label': 'Bear Engulf',    'sym': 'x',             'sz': 10, 'clr': '#D50000', 'base': 'High', 'atr_m': 1.3},
    'Death_Cross':       {'w': 1.5, 'dir': 'sell', 'icon': '☠️', 'label': 'Death Cross',    'sym': 'cross',          'sz': 12, 'clr': '#FF1744', 'base': 'High', 'atr_m': 0.8},
}

COMPOSITE_SIGNALS = {
    'Ultra_Buy':  {'w': 0, 'dir': 'buy',  'icon': '⚡', 'label': 'ULTRA BUY',  'sym': 'star', 'sz': 20, 'clr': '#FFD700', 'base': 'Low',  'atr_m': -3.5},
    'Strong_Buy': {'w': 0, 'dir': 'buy',  'icon': '🔱', 'label': 'STRONG BUY', 'sym': 'star', 'sz': 16, 'clr': '#00E676', 'base': 'Low',  'atr_m': -3.2},
    'Ultra_Sell': {'w': 0, 'dir': 'sell', 'icon': '🚨', 'label': 'ULTRA SELL', 'sym': 'star', 'sz': 20, 'clr': '#FF0000', 'base': 'High', 'atr_m': 3.5},
    'Strong_Sell':{'w': 0, 'dir': 'sell', 'icon': '⚠️', 'label': 'STRONG SELL','sym': 'star', 'sz': 16, 'clr': '#FF1744', 'base': 'High', 'atr_m': 3.2},
}

BUY_SIGNALS  = {k: v for k, v in SIGNAL_REGISTRY.items() if v['dir'] == 'buy'}
SELL_SIGNALS = {k: v for k, v in SIGNAL_REGISTRY.items() if v['dir'] == 'sell'}
ALL_CHART_SIGNALS = {**SIGNAL_REGISTRY, **COMPOSITE_SIGNALS}

# ──────────────────────────────────────────
# 신호 설명 사전 (사이드바용)
# ──────────────────────────────────────────
SIGNAL_DESCRIPTIONS = {
    'Ultra_Buy': {
        'chart_icon': '⚡', 'chart_label': 'ULTRA BUY',
        'kor': '울트라 매수',
        'desc': 'Confluence Score ≥ 6 또는 (≥5 + 동시 3개 이상 매수 신호). 모든 지표가 극단적 매수를 가리킴.',
    },
    'Strong_Buy': {
        'chart_icon': '🔱', 'chart_label': 'STRONG BUY',
        'kor': '스트롱 매수',
        'desc': 'Confluence Score 3.5~6. 다수의 매수 시그널이 수렴하여 높은 신뢰도의 매수 구간.',
    },
    'Gold_Dot': {
        'chart_icon': '🏆', 'chart_label': 'GOLD DOT',
        'kor': '최강 매수',
        'desc': '모든 매수 조건이 극단적으로 수렴. RSI<30 + MFI<30 + WT1<-60 + 상승 다이버전스. 추세 필터 무시.',
    },
    'Green_Dot_T1': {
        'chart_icon': '🟢', 'chart_label': 'BUY T1',
        'kor': '강한 매수',
        'desc': 'WT 과매도 교차 + RSI<30 + MFI<30 + MF<0. 극단적 하락장에서만 억제.',
    },
    'Green_Dot_T2': {
        'chart_icon': '🟩', 'chart_label': 'BUY T2',
        'kor': '매수',
        'desc': 'T1 완화 버전. WT 과매도 + RSI 또는 MFI < 32. 강한 하락장에서 억제.',
    },
    'Blue_Diamond': {
        'chart_icon': '🔹', 'chart_label': 'BLUE DIA',
        'kor': '추세 매수',
        'desc': 'WT2≤0 상승교차 + HTF 강세 + 하락추세 아님 + 자금유출 심하지 않을 때 발동.',
    },
    'Green_Circle': {
        'chart_icon': '✅', 'chart_label': 'BUY Circle',
        'kor': '과매도 반등',
        'desc': 'WT 과매도 교차. Green Dot 미달. 강한 하락장에서 억제.',
    },
    'Bull_Divergence': {
        'chart_icon': '📈', 'chart_label': 'Bull Div',
        'kor': '상승 다이버전스',
        'desc': '가격 저점↓ vs WT 저점↑. 하락장에서 억제됨 (추세 중 다이버전스 실패 방지).',
    },
    'Hidden_Bull_Div': {
        'chart_icon': '🔀', 'chart_label': 'Hidden Bull',
        'kor': '히든 상승 다이버전스',
        'desc': '가격 저점↑ vs 오실레이터 저점↓. 기존 상승 추세 재개 신호.',
    },
    'Squeeze_Fire_Buy': {
        'chart_icon': '💥', 'chart_label': 'Squeeze BUY',
        'kor': '스퀴즈 매수',
        'desc': 'TTM Squeeze 해소 + 모멘텀 상방. 강한 하락장에서 억제.',
    },
    'Volume_Climax_Buy': {
        'chart_icon': '🌊', 'chart_label': 'Vol Climax BUY',
        'kor': '거래량 클라이맥스 매수',
        'desc': '평균 3배 거래량 + 하락캔들 + WT과매도 + 반등. 투매 후 반전.',
    },
    'OBV_Div_Buy': {
        'chart_icon': '📊', 'chart_label': 'OBV Div BUY',
        'kor': 'OBV 다이버전스 매수',
        'desc': 'OBV-가격 상승 다이버전스. 극단 하락장에서 억제.',
    },
    'ADX_Momentum_Buy': {
        'chart_icon': '🚀', 'chart_label': 'ADX Ignition',
        'kor': 'ADX 점화',
        'desc': 'ADX > 20 돌파 + Plus DI > Minus DI. 새 상승추세 시작.',
    },
    'Fib_Bounce_Buy': {
        'chart_icon': '📐', 'chart_label': 'Fib Bounce',
        'kor': '피보나치 반등',
        'desc': '0.618~0.786 되돌림 지지 + WT 상승교차. 강한 하락장 억제.',
    },
    'Bullish_Engulfing': {
        'chart_icon': '☀️', 'chart_label': 'Bull Engulf',
        'kor': '상승 장악형',
        'desc': '전일 하락캔들을 감싸는 상승캔들 + WT 약세구간. 강한 하락장 억제.',
    },
    'Golden_Cross': {
        'chart_icon': '✨', 'chart_label': 'Golden Cross',
        'kor': '골든 크로스',
        'desc': '50일 MA > 200일 MA 상향돌파. 중장기 강세 전환.',
    },
    'Ultra_Sell': {
        'chart_icon': '🚨', 'chart_label': 'ULTRA SELL',
        'kor': '울트라 매도',
        'desc': 'Confluence Score ≤ -6 또는 (≤-5 + 동시 3개 이상 매도). 극단적 매도.',
    },
    'Strong_Sell': {
        'chart_icon': '⚠️', 'chart_label': 'STRONG SELL',
        'kor': '스트롱 매도',
        'desc': 'Confluence Score -6~-3.5. 다수 매도 시그널 수렴.',
    },
    'Blood_Diamond': {
        'chart_icon': '🩸', 'chart_label': 'BLOOD DIA',
        'kor': '최강 매도',
        'desc': 'RSI>70 + MFI>70 + WT1>60 + 하락 다이버전스. 추세 필터 무시.',
    },
    'Red_Dot_T1': {
        'chart_icon': '🔴', 'chart_label': 'SELL T1',
        'kor': '강한 매도',
        'desc': 'WT 과매수 하락교차 + RSI>70 + MFI>70 + MF>0. 극단적 상승장에서만 억제.',
    },
    'Red_Dot_T2': {
        'chart_icon': '🟥', 'chart_label': 'SELL T2',
        'kor': '매도',
        'desc': 'T1 완화 버전. WT 과매수 + RSI 또는 MFI > 68. 강한 상승장에서 억제.',
    },
    'Red_Diamond': {
        'chart_icon': '🔸', 'chart_label': 'RED DIA',
        'kor': '추세 매도',
        'desc': 'WT2≥0 하락교차 + HTF 약세 + 상승추세 아님 + 자금유입 약할 때 발동.',
    },
    'Red_Circle': {
        'chart_icon': '⛔', 'chart_label': 'SELL Circle',
        'kor': '과매수 하락',
        'desc': 'WT 과매수 하락교차. Red Dot 미달. 강한 상승장에서 억제.',
    },
    'Bear_Divergence': {
        'chart_icon': '📉', 'chart_label': 'Bear Div',
        'kor': '하락 다이버전스',
        'desc': '가격 고점↑ vs WT 고점↓. 상승장에서 억제됨 (추세 중 다이버전스 실패 방지).',
    },
    'Hidden_Bear_Div': {
        'chart_icon': '🔁', 'chart_label': 'Hidden Bear',
        'kor': '히든 하락 다이버전스',
        'desc': '가격 고점↓ vs 오실레이터 고점↑. 하락 추세 재개.',
    },
    'Squeeze_Fire_Sell': {
        'chart_icon': '🧨', 'chart_label': 'Squeeze SELL',
        'kor': '스퀴즈 매도',
        'desc': 'TTM Squeeze 해소 + 모멘텀 하방. 강한 상승장에서 억제.',
    },
    'Volume_Climax_Sell': {
        'chart_icon': '🌋', 'chart_label': 'Vol Climax SELL',
        'kor': '거래량 클라이맥스 매도',
        'desc': '평균 3배 거래량 + 상승캔들 + WT과매수 + 하락. 클라이맥스 탑.',
    },
    'OBV_Div_Sell': {
        'chart_icon': '🔻', 'chart_label': 'OBV Div SELL',
        'kor': 'OBV 다이버전스 매도',
        'desc': 'OBV-가격 하락 다이버전스. 극단 상승장에서 억제.',
    },
    'ADX_Momentum_Sell': {
        'chart_icon': '💨', 'chart_label': 'ADX Down',
        'kor': 'ADX 하락 점화',
        'desc': 'ADX > 20 돌파 + Minus DI > Plus DI. 새 하락추세 시작.',
    },
    'Fib_Resistance_Sell': {
        'chart_icon': '🚧', 'chart_label': 'Fib Resist',
        'kor': '피보나치 저항',
        'desc': '0.618~0.786 되돌림 저항 + WT 하락교차. 강한 상승장 억제.',
    },
    'Bearish_Engulfing': {
        'chart_icon': '🌑', 'chart_label': 'Bear Engulf',
        'kor': '하락 장악형',
        'desc': '전일 상승캔들을 감싸는 하락캔들 + WT 강세구간. 강한 상승장 억제.',
    },
    'Death_Cross': {
        'chart_icon': '☠️', 'chart_label': 'Death Cross',
        'kor': '데드 크로스',
        'desc': '50일 MA < 200일 MA 하향돌파. 중장기 약세 전환.',
    },
}

# ──────────────────────────────────────────
# ✅ Gemini API
# ──────────────────────────────────────────
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GEMINI_API_KEY)


# ──────────────────────────────────────────
# 캐싱 크롤링
# ──────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def get_stock_data(ticker):
    url = f"https://swingtradebot.com/equities/{ticker.upper()}"
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
    )
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        ),
        'Referer': 'https://www.google.com/',
    }
    try:
        time.sleep(random.uniform(1.0, 2.0))
        response = scraper.get(url, headers=headers, timeout=20)
        if response.status_code != 200:
            return None
        soup = BeautifulSoup(response.text, 'html.parser')
        extracted = []
        headline = soup.find('h2', {'itemprop': 'headline'})
        if headline:
            extracted.append(f"#### [HEADLINE]\n{headline.get_text(strip=True)}")
        recap = soup.find('div', class_='recap-body')
        if recap:
            extracted.append(f"#### [DAILY RECAP]\n{recap.get_text(separator=' ', strip=True)}")
        recap_tour = soup.find(id='recap-tour')
        if recap_tour:
            extracted.append(f"#### [RECAP TOUR]\n{recap_tour.get_text(separator=' ', strip=True)}")
        indicators_tour = soup.find(id='indicators-tour')
        if indicators_tour:
            extracted.append(f"#### [INDICATORS TOUR]\n{indicators_tour.get_text(separator=' | ', strip=True)}")
        for t_id, t_name in [('trend-table-tour', 'TREND ANALYSIS'), ('recent-signals-tour', 'RECENT SIGNALS')]:
            table = soup.find('table', id=t_id)
            if table:
                extracted.append(f"#### [{t_name}]\n{table.get_text(separator=' | ', strip=True)}")
        return "\n\n".join(extracted) if extracted else None
    except Exception:
        return None


@st.cache_data(ttl=300, show_spinner=False)
def get_yf_history(ticker):
    return yf.Ticker(ticker).history(period="2y")


# ──────────────────────────────────────────
# 공통 유틸
# ──────────────────────────────────────────
def _recent_true(series, lookback=3):
    """series가 최근 lookback 바 이내에 True였으면 True (인과적, 미래 참조 없음)"""
    return series.rolling(window=lookback + 1, min_periods=1).max().fillna(0).astype(bool)


# ──────────────────────────────────────────
# 지표 계산 엔진
# ──────────────────────────────────────────
def compute_heikin_ashi(df):
    ha = pd.DataFrame(index=df.index)
    ha['Close'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    ha_open = np.empty(len(df))
    ha_open[0] = (df['Open'].iloc[0] + df['Close'].iloc[0]) / 2
    hc = ha['Close'].values
    for i in range(1, len(df)):
        ha_open[i] = (ha_open[i - 1] + hc[i - 1]) / 2
    ha['Open'] = ha_open
    ha['High'] = np.maximum(np.maximum(ha['Open'].values, hc), df['High'].values)
    ha['Low'] = np.minimum(np.minimum(ha['Open'].values, hc), df['Low'].values)
    ha['Bullish'] = ha['Close'] > ha['Open']
    return ha


def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
    rs = avg_gain / (avg_loss + 1e-10)
    return 100 - (100 / (1 + rs))


def compute_mfi(high, low, close, volume, period=14):
    tp = (high + low + close) / 3
    raw_mf = tp * volume
    pos = pd.Series(0.0, index=tp.index)
    neg = pd.Series(0.0, index=tp.index)
    d = tp.diff()
    pos[d >= 0] = raw_mf[d >= 0]
    neg[d < 0] = raw_mf[d < 0]
    return 100 - (100 / (1 + pos.rolling(period).sum() / (neg.rolling(period).sum() + 1e-10)))


def compute_rsi_mfi(high, low, close, volume, period=60):
    rsi = compute_rsi(close, period)
    mfi = compute_mfi(high, low, close, volume, period)
    return ((rsi - 50) + (mfi - 50)) / 2


def compute_wavetrend(high, low, close, channel_len=9, avg_len=12, ma_len=3):
    ap = (high + low + close) / 3
    esa = ap.ewm(span=channel_len, adjust=False).mean()
    d = abs(ap - esa).ewm(span=channel_len, adjust=False).mean()
    ci = (ap - esa) / (0.015 * d + 1e-10)
    wt1 = ci.ewm(span=avg_len, adjust=False).mean()
    wt2 = wt1.rolling(window=ma_len).mean()
    cross_up = (wt1 > wt2) & (wt1.shift(1) <= wt2.shift(1))
    cross_down = (wt1 < wt2) & (wt1.shift(1) >= wt2.shift(1))
    return wt1, wt2, cross_up, cross_down


def compute_stoch_rsi(close, rsi_len=14, stoch_len=14, k_smooth=3, d_smooth=3):
    rsi = compute_rsi(close, rsi_len)
    stoch = ((rsi - rsi.rolling(stoch_len).min())
             / (rsi.rolling(stoch_len).max() - rsi.rolling(stoch_len).min() + 1e-10)) * 100
    k = stoch.rolling(k_smooth).mean()
    return k, k.rolling(d_smooth).mean()


def compute_vwap_oscillator(close, volume, period=20):
    cv = volume.rolling(period).sum()
    cvp = (close * volume).rolling(period).sum()
    vwap = cvp / (cv + 1e-10)
    return ((close - vwap) / (vwap + 1e-10)) * 100


def compute_adx(high, low, close, period=14):
    ph, pl, pc = high.shift(1), low.shift(1), close.shift(1)
    tr = pd.concat([high - low, (high - pc).abs(), (low - pc).abs()], axis=1).max(axis=1)
    plus_dm = pd.Series(np.where((high - ph) > (pl - low), np.maximum(high - ph, 0), 0),
                        index=high.index, dtype=float)
    minus_dm = pd.Series(np.where((pl - low) > (high - ph), np.maximum(pl - low, 0), 0),
                         index=high.index, dtype=float)
    atr = tr.ewm(alpha=1 / period, min_periods=period).mean()
    pdi = 100 * plus_dm.ewm(alpha=1 / period, min_periods=period).mean() / (atr + 1e-10)
    mdi = 100 * minus_dm.ewm(alpha=1 / period, min_periods=period).mean() / (atr + 1e-10)
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi + 1e-10)
    adx = dx.ewm(alpha=1 / period, min_periods=period).mean()
    return adx, pdi, mdi


def compute_obv(close, volume):
    return (volume * np.sign(close.diff()).fillna(0)).cumsum()


def detect_pivot_divergence_v2(price, oscillator, lookback=60, pivot_window=5,
                                osc_oversold=None, osc_overbought=None):
    n = len(price)
    pv, ov = price.values, oscillator.values
    half = pivot_window
    min_gap = pivot_window * 2
    pivot_lows, pivot_highs = [], []
    for i in range(2 * half, n):
        candidate = i - half
        window = pv[i - 2 * half: i + 1]
        if pv[candidate] == window.min():
            pivot_lows.append((i, candidate))
        if pv[candidate] == window.max():
            pivot_highs.append((i, candidate))
    bull_div = pd.Series(False, index=price.index)
    bear_div = pd.Series(False, index=price.index)
    hidden_bull = pd.Series(False, index=price.index)
    hidden_bear = pd.Series(False, index=price.index)
    for idx in range(1, len(pivot_lows)):
        confirm_i, pivot_i = pivot_lows[idx]
        confirm_j, pivot_j = pivot_lows[idx - 1]
        if (pivot_i - pivot_j) > lookback or (pivot_i - pivot_j) < min_gap:
            continue
        ok = (osc_oversold is None) or (ov[pivot_i] <= osc_oversold)
        if ok and pv[pivot_i] < pv[pivot_j] and ov[pivot_i] > ov[pivot_j]:
            bull_div.iloc[confirm_i] = True
        if pv[pivot_i] > pv[pivot_j] and ov[pivot_i] < ov[pivot_j]:
            hidden_bull.iloc[confirm_i] = True
    for idx in range(1, len(pivot_highs)):
        confirm_i, pivot_i = pivot_highs[idx]
        confirm_j, pivot_j = pivot_highs[idx - 1]
        if (pivot_i - pivot_j) > lookback or (pivot_i - pivot_j) < min_gap:
            continue
        ok = (osc_overbought is None) or (ov[pivot_i] >= osc_overbought)
        if ok and pv[pivot_i] > pv[pivot_j] and ov[pivot_i] < ov[pivot_j]:
            bear_div.iloc[confirm_i] = True
        if pv[pivot_i] < pv[pivot_j] and ov[pivot_i] > ov[pivot_j]:
            hidden_bear.iloc[confirm_i] = True
    return bull_div, bear_div, hidden_bull, hidden_bear


def compute_keltner_channel(high, low, close, ema_len=20, atr_len=10, atr_mult=1.5):
    mid = close.ewm(span=ema_len, adjust=False).mean()
    pc = close.shift(1)
    tr = pd.concat([high - low, (high - pc).abs(), (low - pc).abs()], axis=1).max(axis=1)
    atr = tr.rolling(atr_len).mean()
    return mid + atr * atr_mult, mid, mid - atr * atr_mult


def detect_ttm_squeeze(bb_up, bb_low, kc_up, kc_low, close, high, low, kc_mid):
    squeeze_on = (bb_up < kc_up) & (bb_low > kc_low)
    fire = (~squeeze_on) & squeeze_on.shift(1).fillna(False)
    donchian_mid = (high.rolling(20).max() + low.rolling(20).min()) / 2
    momentum = close - (donchian_mid + kc_mid) / 2
    return squeeze_on, fire & (momentum > 0), fire & (momentum < 0)


def detect_volume_climax(close, opn, volume, wt1, vol_mult=3.0, wt_buy=-40, wt_sell=40):
    avg = volume.rolling(20).mean()
    spike = volume > avg * vol_mult
    bear_c = close < opn
    bull_c = close > opn
    wt_turning_up  = (wt1 > wt1.shift(1)) | (wt1 < -60)
    wt_turning_down = (wt1 < wt1.shift(1)) | (wt1 > 60)
    buy  = spike & bear_c & (wt1 < wt_buy) & wt_turning_up
    sell = spike & bull_c & (wt1 > wt_sell) & wt_turning_down
    return buy, sell


def detect_obv_divergence(close, volume, wt1, lookback=60, pivot_window=5):
    obv = compute_obv(close, volume)
    bull_d, bear_d, _, _ = detect_pivot_divergence_v2(
        close, obv, lookback=lookback, pivot_window=pivot_window,
    )
    buy = bull_d & (wt1 < -20)
    sell = bear_d & (wt1 > 20)
    return obv, buy, sell


def detect_bearish_engulfing(close, opn, wt1, wt_thresh=20):
    pb = close.shift(1) > opn.shift(1)
    cb = close < opn
    eng = pb & cb & (opn >= close.shift(1)) & (close <= opn.shift(1))
    body = (close - opn).abs()
    avg_body = body.rolling(20).mean()
    eng = eng & (body > avg_body * 0.8)
    return eng & (wt1 > wt_thresh)


def detect_bullish_engulfing(close, opn, wt1, wt_thresh=-20):
    pb = close.shift(1) < opn.shift(1)
    cb = close > opn
    eng = pb & cb & (opn <= close.shift(1)) & (close >= opn.shift(1))
    body = (close - opn).abs()
    avg_body = body.rolling(20).mean()
    eng = eng & (body > avg_body * 0.8)
    return eng & (wt1 < wt_thresh)


def detect_fib_bounce_buy(high, low, wt1, wt2, swing_lb=60, confirm=5):
    sh = high.shift(confirm).rolling(swing_lb).max()
    sl = low.shift(confirm).rolling(swing_lb).min()
    f618 = sh - (sh - sl) * 0.618
    f786 = sh - (sh - sl) * 0.786
    near = (low <= f618 * 1.01) & (low >= f786 * 0.99)
    return near & (wt1 < -30) & (wt1 > wt2)


def detect_fib_resistance_sell(high, low, close, wt1, wt2, swing_lb=60, confirm=5):
    sh = high.shift(confirm).rolling(swing_lb).max()
    sl = low.shift(confirm).rolling(swing_lb).min()
    f618 = sl + (sh - sl) * 0.618
    f786 = sl + (sh - sl) * 0.786
    near = (high >= f618 * 0.99) & (high <= f786 * 1.01)
    return near & (wt1 > 30) & (wt1 < wt2)


def detect_ma_cross(ma_fast, ma_slow, wt1, wt2):
    golden = (ma_fast > ma_slow) & (ma_fast.shift(1) <= ma_slow.shift(1)) & (wt1 > wt2)
    death  = (ma_fast < ma_slow) & (ma_fast.shift(1) >= ma_slow.shift(1)) & (wt1 < wt2)
    return golden, death


def compute_confluence_score(df, decay_window=5, decay_factor=0.7):
    buy_map  = {k: v['w'] for k, v in SIGNAL_REGISTRY.items() if v['dir'] == 'buy'}
    sell_map = {k: v['w'] for k, v in SIGNAL_REGISTRY.items() if v['dir'] == 'sell'}
    decay_kernel = np.array([decay_factor ** i for i in range(decay_window + 1)])
    s = np.zeros(len(df))
    buy_count = np.zeros(len(df))
    sell_count = np.zeros(len(df))
    for col, w in buy_map.items():
        if col in df.columns:
            raw = df[col].astype(float).values * w
            decayed = np.convolve(raw, decay_kernel, mode='full')[:len(raw)]
            s += decayed
            cnt = np.convolve(df[col].astype(float).values, np.ones(decay_window + 1), mode='full')[:len(raw)]
            buy_count += cnt
    for col, w in sell_map.items():
        if col in df.columns:
            raw = df[col].astype(float).values * w
            decayed = np.convolve(raw, decay_kernel, mode='full')[:len(raw)]
            s -= decayed
            cnt = np.convolve(df[col].astype(float).values, np.ones(decay_window + 1), mode='full')[:len(raw)]
            sell_count += cnt
    wt1 = df['WT1'].values
    s += np.where(wt1 < -53, 1.0, 0.0)
    s += np.where(wt1 < -60, 0.5, 0.0)
    s -= np.where(wt1 > 53, 1.0, 0.0)
    s -= np.where(wt1 > 60, 0.5, 0.0)
    df['Confluence_Score'] = s
    df['Ultra_Buy']  = (s >= 6.0) | ((s >= 5.0) & (buy_count >= 3))
    df['Ultra_Sell'] = (s <= -6.0) | ((s <= -5.0) & (sell_count >= 3))
    df['Strong_Buy']  = (s >= 3.5) & (~df['Ultra_Buy'])
    df['Strong_Sell'] = (s <= -3.5) & (~df['Ultra_Sell'])
    return s


def compute_signal_proximity(wt1, wt2, rsi, mfi, rsi_mfi, stochk):
    buy_prox = pd.Series(0.0, index=wt1.index)
    sell_prox = pd.Series(0.0, index=wt1.index)
    wt_gap = (wt1 - wt2).abs()
    near_cross = wt_gap < 3.0
    buy_prox += np.where((wt1 < -40) & near_cross, 30, 0)
    buy_prox += np.where((wt1 < -53), 20, np.where(wt1 < -40, 10, 0))
    buy_prox += np.where(rsi < 35, 15, np.where(rsi < 45, 5, 0))
    buy_prox += np.where(mfi < 35, 15, np.where(mfi < 45, 5, 0))
    buy_prox += np.where(rsi_mfi < -5, 10, np.where(rsi_mfi < 0, 5, 0))
    buy_prox += np.where(stochk < 20, 10, np.where(stochk < 35, 5, 0))
    sell_prox += np.where((wt1 > 40) & near_cross, 30, 0)
    sell_prox += np.where((wt1 > 53), 20, np.where(wt1 > 40, 10, 0))
    sell_prox += np.where(rsi > 65, 15, np.where(rsi > 55, 5, 0))
    sell_prox += np.where(mfi > 65, 15, np.where(mfi > 55, 5, 0))
    sell_prox += np.where(rsi_mfi > 5, 10, np.where(rsi_mfi > 0, 5, 0))
    sell_prox += np.where(stochk > 80, 10, np.where(stochk > 65, 5, 0))
    buy_prox = buy_prox.clip(upper=100)
    sell_prox = sell_prox.clip(upper=100)
    net = buy_prox - sell_prox
    buy_prox_final  = np.where(net >= 0, buy_prox, buy_prox * 0.4)
    sell_prox_final = np.where(net <= 0, sell_prox, sell_prox * 0.4)
    return pd.Series(buy_prox_final, index=wt1.index), pd.Series(sell_prox_final, index=wt1.index)


def compute_bias_score(meta, htf1_bull, htf2_bull):
    sc = 0.0
    wt = meta['wt1']
    if wt <= -60:     sc += 3
    elif wt <= -53:   sc += 2
    elif wt < 0:      sc += 1
    elif wt < 53:     sc -= 1
    elif wt < 60:     sc -= 2
    else:             sc -= 3
    rsi = meta['rsi']
    if rsi < 30:      sc += 2
    elif rsi < 45:    sc += 1
    elif rsi > 70:    sc -= 2
    elif rsi > 55:    sc -= 1
    mfi = meta['mfi']
    if mfi < 30:      sc += 2
    elif mfi < 45:    sc += 1
    elif mfi > 70:    sc -= 2
    elif mfi > 55:    sc -= 1
    mf = meta['mf_area']
    if mf < -5:       sc += 2
    elif mf < 0:      sc += 1
    elif mf > 5:      sc -= 2
    elif mf > 0:      sc -= 1
    stk = meta.get('stochk', 50)
    if stk < 20:      sc += 1.5
    elif stk < 35:    sc += 0.5
    elif stk > 80:    sc -= 1.5
    elif stk > 65:    sc -= 0.5
    sc += 1 if htf1_bull else -1
    sc += 1.5 if htf2_bull else -1.5
    if sc >= 8:    return 'STRONG BUY', sc
    elif sc >= 3:  return 'BUY', sc
    elif sc >= -3: return 'NEUTRAL', sc
    elif sc >= -8: return 'SELL', sc
    else:          return 'STRONG SELL', sc


def compute_signal_stats(df, signal_col, price_col='Close', forward_days=None, min_samples=5):
    if forward_days is None:
        forward_days = [5, 10, 20]
    if signal_col not in df.columns:
        return None
    mask = df[signal_col].values.astype(bool)
    if not mask.any():
        return None
    count = int(mask.sum())
    if count < min_samples:
        return None
    close = df[price_col].values
    stats = {'count': count}
    for n in forward_days:
        if n >= len(close):
            stats[f'{n}d_avg'] = stats[f'{n}d_winrate'] = stats[f'{n}d_median'] = None
            continue
        fwd = np.full(len(close), np.nan)
        fwd[:len(close) - n] = (close[n:] - close[:len(close) - n]) / close[:len(close) - n] * 100
        valid = fwd[mask]
        valid = valid[~np.isnan(valid)]
        if len(valid) >= min_samples:
            stats[f'{n}d_avg'] = float(np.mean(valid))
            stats[f'{n}d_winrate'] = float(np.sum(valid > 0) / len(valid) * 100)
            stats[f'{n}d_median'] = float(np.median(valid))
        else:
            stats[f'{n}d_avg'] = stats[f'{n}d_winrate'] = stats[f'{n}d_median'] = None
    return stats


def compute_all_signal_stats(df_valid):
    targets = {k: v['dir'] for k, v in SIGNAL_REGISTRY.items()}
    targets.update({
        'Ultra_Buy': 'buy', 'Strong_Buy': 'buy',
        'Ultra_Sell': 'sell', 'Strong_Sell': 'sell',
    })
    results = {}
    for sig, direction in targets.items():
        sig_result = compute_signal_stats(df_valid, sig)
        if sig_result and sig_result['count'] > 0:
            results[sig] = {**sig_result, 'direction': direction}
    return results


# ──────────────────────────────────────────
# 차트 + 분석 데이터 엔진 (✅ v2.2 추세 필터 통합)
# ──────────────────────────────────────────
def get_yfinance_data_and_chart(ticker, chart_period_days=252):
    try:
        df = get_yf_history(ticker)
        if df.empty:
            return None, "최근 주가 데이터 없음", None

        mas = [5, 20, 50, 100, 125, 200]
        for ma in mas:
            df[f'MA{ma}'] = df['Close'].rolling(ma).mean()
        df['BB_Mid'] = df['MA20']
        std20 = df['Close'].rolling(20).std()
        df['BB_Up'] = df['BB_Mid'] + std20 * 2
        df['BB_Low'] = df['BB_Mid'] - std20 * 2
        pc = df['Close'].shift(1)
        tr = pd.concat([df['High'] - df['Low'], (df['High'] - pc).abs(), (df['Low'] - pc).abs()], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(14).mean()

        wt1, wt2, wt_up, wt_down = compute_wavetrend(df['High'], df['Low'], df['Close'])
        df['WT1'], df['WT2'] = wt1, wt2
        df['RSI'] = compute_rsi(df['Close'], 14)
        df['StochK'], df['StochD'] = compute_stoch_rsi(df['Close'])
        df['MFI'] = compute_mfi(df['High'], df['Low'], df['Close'], df['Volume'], 14)
        df['RSI_MFI'] = compute_rsi_mfi(df['High'], df['Low'], df['Close'], df['Volume'], 60)
        df['VWAP_Osc'] = compute_vwap_oscillator(df['Close'], df['Volume'])
        df['ADX'], df['Plus_DI'], df['Minus_DI'] = compute_adx(df['High'], df['Low'], df['Close'])

        df['OBV'], obv_db, obv_ds = detect_obv_divergence(df['Close'], df['Volume'], df['WT1'])
        df['OBV_Div_Buy'], df['OBV_Div_Sell'] = obv_db, obv_ds

        ha = compute_heikin_ashi(df)
        htf1_bull = ha['Close'].rolling(5).mean() > ha['Open'].rolling(5).mean()
        htf2_bull = ha['Close'].rolling(20).mean() > ha['Open'].rolling(20).mean()

        OB1, OB2, OS1, OS2 = 53, 60, -53, -60

        wt_up_recent = _recent_true(wt_up, lookback=3)
        wt_down_recent = _recent_true(wt_down, lookback=3)

        # ═══════════════════════════════════════════════════════
        # ✅ NEW: 추세 레짐 감지 (Trend Regime Detection)
        # ═══════════════════════════════════════════════════════
        above_ma50  = df['Close'] > df['MA50']
        above_ma200 = df['Close'] > df['MA200']
        below_ma50  = df['Close'] < df['MA50']
        below_ma200 = df['Close'] < df['MA200']
        ma50_rising  = df['MA50'] > df['MA50'].shift(5)   # MA50이 5일 전보다 상승 중
        ma50_falling = df['MA50'] < df['MA50'].shift(5)   # MA50이 5일 전보다 하락 중

        # 강한 추세: ADX가 추세 확인 + DI 방향 + 가격이 MA50 위/아래
        strong_bull = (df['ADX'] > 25) & (df['Plus_DI'] > df['Minus_DI']) & above_ma50
        strong_bear = (df['ADX'] > 25) & (df['Minus_DI'] > df['Plus_DI']) & below_ma50

        # 극단 추세: 강한 추세 + MA200 확인 + MA50 기울기 확인
        extreme_bull = strong_bull & above_ma200 & ma50_rising
        extreme_bear = strong_bear & below_ma200 & ma50_falling

        # 자금 흐름 방향 (Money Flow 확인용)
        mf_bullish = df['RSI_MFI'] > -10    # 자금 유출이 심하지 않음
        mf_bearish = df['RSI_MFI'] < 10     # 자금 유입이 강하지 않음
        # ═══════════════════════════════════════════════════════

        # ──────────────────────────────────────
        # ✅ IMPROVED: 티어별 시그널 정의
        # ──────────────────────────────────────

        # ── TIER 1: 절대 억제 금지 (Gold_Dot, Blood_Diamond) ──
        # 이 신호들은 이미 극단적 조건 수렴이므로 추세 필터 불필요

        # ── Green/Red Dot (TIER 2: 극단 역추세에서만 억제) ──
        df['Green_Dot_T1'] = (
            wt_up & (df['WT1'] <= OS1) &
            (df['RSI'] < 30) & (df['MFI'] < 30) & (df['RSI_MFI'] < 0) &
            (~extreme_bear)  # ✅ NEW: 극단 하락장에서만 억제
        )
        df['Green_Dot_T2'] = (
            wt_up & (df['WT1'] <= OS1) &
            ((df['RSI'] < 32) | (df['MFI'] < 32)) &
            ~df['Green_Dot_T1'] &
            (~strong_bear)   # ✅ NEW: 강한 하락장에서 억제
        )
        df['Green_Dot'] = df['Green_Dot_T1'] | df['Green_Dot_T2']

        df['Red_Dot_T1'] = (
            wt_down & (df['WT1'] >= OB1) &
            (df['RSI'] > 70) & (df['MFI'] > 70) & (df['RSI_MFI'] > 0) &
            (~extreme_bull)  # ✅ NEW: 극단 상승장에서만 억제
        )
        df['Red_Dot_T2'] = (
            wt_down & (df['WT1'] >= OB1) &
            ((df['RSI'] > 68) | (df['MFI'] > 68)) &
            ~df['Red_Dot_T1'] &
            (~strong_bull)   # ✅ NEW: 강한 상승장에서 억제
        )
        df['Red_Dot'] = df['Red_Dot_T1'] | df['Red_Dot_T2']

        # ── TIER 3: 강한 역추세에서 억제 ──
        df['Blue_Diamond'] = (
            (df['WT2'] <= 0) & wt_up & htf1_bull & htf2_bull &
            (~strong_bear) &  # ✅ NEW: 강한 하락장에서 억제
            mf_bullish        # ✅ NEW: 자금 유출이 심하면 무시
        )
        df['Red_Diamond'] = (
            (df['WT2'] >= 0) & wt_down & ~htf1_bull & ~htf2_bull &
            (~strong_bull) &  # ✅ NEW: 강한 상승장에서 억제
            mf_bearish        # ✅ NEW: 자금 유입이 강하면 무시
        )

        df['Green_Circle'] = (
            wt_up & (df['WT1'] <= OS1) & ~df['Green_Dot'] &
            (~strong_bear)    # ✅ NEW
        )
        df['Red_Circle'] = (
            wt_down & (df['WT1'] >= OB1) & ~df['Red_Dot'] &
            (~strong_bull)    # ✅ NEW
        )

        # ── 다이버전스 (TIER 2~3: 추세 중 다이버전스 실패 방지) ──
        bull_d, bear_d, hid_bull, hid_bear = detect_pivot_divergence_v2(
            df['Close'], df['WT1'], 60, 5, OS1, OB1)

        bull_d_recent = _recent_true(bull_d, lookback=3)
        bear_d_recent = _recent_true(bear_d, lookback=3)

        # TIER 1: Gold_Dot — 절대 억제 금지
        df['Gold_Dot'] = df['Green_Dot_T1'] & (df['WT1'] <= OS2) & bull_d_recent

        # TIER 2: 다이버전스 — 강한 역추세에서 억제
        df['Bull_Divergence'] = (
            bull_d & wt_up_recent &
            ~df['Green_Dot'] & ~df['Gold_Dot'] &
            (~strong_bear)    # ✅ NEW: 강한 하락장에서 다이버전스 실패 가능성 높음
        )
        df['Bear_Divergence'] = (
            bear_d & wt_down_recent &
            ~df['Red_Dot'] &
            (~strong_bull)    # ✅ NEW: 강한 상승장에서 다이버전스 실패 가능성 높음
        )

        df['Hidden_Bull_Div'] = hid_bull & (df['WT1'] < 0) & htf2_bull
        df['Hidden_Bear_Div'] = hid_bear & (df['WT1'] > 0) & ~htf2_bull

        # TIER 1: Blood_Diamond — 절대 억제 금지
        df['Blood_Diamond'] = df['Red_Dot_T1'] & (df['WT1'] >= OB2) & bear_d_recent

        # ── TTM Squeeze (TIER 3) ──
        kc_u, kc_mid, kc_l = compute_keltner_channel(df['High'], df['Low'], df['Close'])
        df['KC_Upper'], df['KC_Lower'] = kc_u, kc_l
        sq_on, sq_fb, sq_fs = detect_ttm_squeeze(
            df['BB_Up'], df['BB_Low'], kc_u, kc_l,
            df['Close'], df['High'], df['Low'], kc_mid
        )
        df['Squeeze_On'] = sq_on
        df['Squeeze_Fire_Buy']  = sq_fb & (~strong_bear)   # ✅ NEW
        df['Squeeze_Fire_Sell'] = sq_fs & (~strong_bull)    # ✅ NEW

        # ── Volume Climax (TIER 2: 이미 극단 조건이라 약하게 필터) ──
        vc_b, vc_s = detect_volume_climax(df['Close'], df['Open'], df['Volume'], df['WT1'])
        df['Volume_Climax_Buy']  = vc_b   # 투매는 하락장에서 발생하므로 필터링하면 안 됨
        df['Volume_Climax_Sell'] = vc_s   # 클라이맥스 탑도 상승장에서 발생하므로 유지

        # ── ADX Momentum (자체적으로 추세 방향 확인하므로 추가 필터 불필요) ──
        df['ADX_Momentum_Buy']  = (df['ADX'] > 20) & (df['ADX'].shift(1) <= 20) & (df['Plus_DI'] > df['Minus_DI']) & (wt1 > wt2)
        df['ADX_Momentum_Sell'] = (df['ADX'] > 20) & (df['ADX'].shift(1) <= 20) & (df['Minus_DI'] > df['Plus_DI']) & (wt1 < wt2)

        # ── Fibonacci (TIER 4: 일반 역추세에서도 억제) ──
        raw_fib_buy = detect_fib_bounce_buy(df['High'], df['Low'], df['WT1'], df['WT2'])
        raw_fib_sell = detect_fib_resistance_sell(df['High'], df['Low'], df['Close'], df['WT1'], df['WT2'])
        df['Fib_Bounce_Buy']     = raw_fib_buy & (~strong_bear)    # ✅ NEW
        df['Fib_Resistance_Sell'] = raw_fib_sell & (~strong_bull)   # ✅ NEW

        # ── Engulfing (TIER 3) ──
        raw_bull_eng = detect_bullish_engulfing(df['Close'], df['Open'], df['WT1'])
        raw_bear_eng = detect_bearish_engulfing(df['Close'], df['Open'], df['WT1'])
        df['Bullish_Engulfing'] = raw_bull_eng & (~strong_bear)    # ✅ NEW
        df['Bearish_Engulfing'] = raw_bear_eng & (~strong_bull)    # ✅ NEW

        # ── MA Cross (추세 전환 신호이므로 필터 불필요) ──
        gc, dc = detect_ma_cross(df['MA50'], df['MA200'], df['WT1'], df['WT2'])
        df['Golden_Cross'], df['Death_Cross'] = gc, dc

        # ── OBV Divergence (TIER 4) ──
        df['OBV_Div_Buy']  = obv_db & (~extreme_bear)    # ✅ NEW: 극단 하락장에서만 억제
        df['OBV_Div_Sell'] = obv_ds & (~extreme_bull)     # ✅ NEW: 극단 상승장에서만 억제

        # ── Small Dots (WT 교차만으로는 신호 불필요, 차트 표시용) ──
        df['Small_Green_Dot'] = wt_up & ~df['Green_Circle'] & ~df['Green_Dot'] & ~df['Gold_Dot'] & ~df['Blue_Diamond'] & ~df['Bull_Divergence']
        df['Small_Red_Dot']   = wt_down & ~df['Red_Circle'] & ~df['Red_Dot'] & ~df['Red_Diamond'] & ~df['Bear_Divergence']

        # ── Confluence Score (필터된 시그널 기반으로 계산) ──
        compute_confluence_score(df)

        buy_prox, sell_prox = compute_signal_proximity(
            df['WT1'], df['WT2'], df['RSI'], df['MFI'], df['RSI_MFI'], df['StochK'])
        df['Buy_Proximity'], df['Sell_Proximity'] = buy_prox, sell_prox

        # ✅ NEW: 추세 레짐 정보를 meta에 전달
        df['Strong_Bull'] = strong_bull
        df['Strong_Bear'] = strong_bear

        df_valid = df.dropna(subset=['WT1', 'WT2'])
        df_chart = df_valid.tail(chart_period_days).copy()
        if df_chart.empty:
            return None, "차트 데이터 부족", None

        latest = df_chart.iloc[-1]
        prev = df_chart.iloc[-2] if len(df_chart) >= 2 else latest
        p_chg = latest['Close'] - prev['Close']
        p_chg_pct = (p_chg / prev['Close']) * 100
        all_stats = compute_all_signal_stats(df_valid)

        sig_checks = [(k, v['icon'], v['label'], v['dir'])
                      for k, v in ALL_CHART_SIGNALS.items()]

        recent_signals = []
        for ir, row in df_chart.tail(30).iterrows():
            d_str = ir.strftime('%m/%d')
            for col, icon, lbl, side in sig_checks:
                if row.get(col, False):
                    recent_signals.append((icon, lbl, d_str, side))

        m4b = {'wt1': float(latest['WT1']), 'rsi': float(latest['RSI']),
               'mfi': float(latest['MFI']), 'mf_area': float(latest['RSI_MFI']),
               'stochk': float(latest['StochK'])}
        bias, bscore = compute_bias_score(m4b, bool(htf1_bull.iloc[-1]), bool(htf2_bull.iloc[-1]))
        conf_now = float(df_chart['Confluence_Score'].iloc[-1])

        # ✅ NEW: 추세 상태 문자열
        if latest.get('Strong_Bull', False):
            trend_regime = 'STRONG BULL 🟢'
        elif latest.get('Strong_Bear', False):
            trend_regime = 'STRONG BEAR 🔴'
        else:
            trend_regime = 'NEUTRAL ⚪'

        meta = {
            'ticker': ticker.upper(), 'price': latest['Close'],
            'price_change': p_chg, 'price_change_pct': p_chg_pct,
            'volume': latest['Volume'],
            'avg_volume': df_chart['Volume'].rolling(20).mean().iloc[-1],
            'wt1': float(latest['WT1']), 'wt2': float(latest['WT2']),
            'rsi': float(latest['RSI']), 'mfi': float(latest['MFI']),
            'stochk': float(latest['StochK']), 'stochd': float(latest['StochD']),
            'vwap_osc': float(latest['VWAP_Osc']), 'mf_area': float(latest['RSI_MFI']),
            'atr': float(latest['ATR']),
            'atr_pct': float(latest['ATR']) / float(latest['Close']) * 100,
            'adx': float(latest['ADX']),
            'plus_di': float(latest['Plus_DI']), 'minus_di': float(latest['Minus_DI']),
            'overall_bias': bias, 'bias_score': bscore, 'confluence_score': conf_now,
            'recent_signals': recent_signals, 'all_signal_stats': all_stats,
            'last_date': df_chart.index[-1].strftime('%Y-%m-%d'),
            'buy_proximity': float(latest['Buy_Proximity']),
            'sell_proximity': float(latest['Sell_Proximity']),
            'squeeze_on': bool(latest.get('Squeeze_On', False)),
            'trend_regime': trend_regime,   # ✅ NEW
        }

        # ── 차트 (5 패널) ──
        fig = make_subplots(
            rows=5, cols=1, shared_xaxes=True, vertical_spacing=0.02,
            row_heights=[0.40, 0.10, 0.22, 0.14, 0.14],
            subplot_titles=("", "", "WaveTrend Oscillator", "Money Flow", "Confluence Score"),
        )
        fig.add_trace(go.Candlestick(
            x=df_chart.index, open=df_chart['Open'], high=df_chart['High'],
            low=df_chart['Low'], close=df_chart['Close'], name="가격",
            increasing_line_color='#26a69a', decreasing_line_color='#ef5350',
        ), row=1, col=1)
        mac = {5: "#ff9900", 20: '#f1c40f', 50: '#e74c3c', 100: '#9b59b6', 125: '#3498db', 200: '#2ecc71'}
        for ma in mas:
            fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart[f'MA{ma}'],
                                     line=dict(color=mac[ma], width=1.2), name=f'{ma}일선'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['BB_Up'],
                                 line=dict(color='gray', width=1, dash='dot'), name='BB 상단'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['BB_Low'],
                                 line=dict(color='gray', width=1, dash='dot'), name='BB 하단',
                                 fill='tonexty', fillcolor='rgba(128,128,128,0.1)'), row=1, col=1)

        def _atr_at(sig_df):
            return df_chart.loc[sig_df.index, 'ATR'].fillna(df_chart['ATR'].median())

        for cn, cfg in ALL_CHART_SIGNALS.items():
            if cn not in df_chart.columns:
                continue
            if cn == 'Green_Dot_T1':
                sig = df_chart[df_chart[cn] & ~df_chart['Gold_Dot']]
            elif cn == 'Ultra_Buy':
                sig = df_chart[df_chart[cn] & ~df_chart['Gold_Dot']]
            elif cn == 'Ultra_Sell':
                sig = df_chart[df_chart[cn] & ~df_chart['Blood_Diamond']]
            else:
                sig = df_chart[df_chart[cn]]
            if sig.empty:
                continue
            yv = sig[cfg['base']] + _atr_at(sig) * cfg['atr_m']
            lw = 2 if cfg['sz'] >= 16 else (1.5 if cfg['sz'] >= 13 else 1)
            nm = f"{cfg['icon']} {cfg['label']}"
            fig.add_trace(go.Scatter(
                x=sig.index, y=yv, mode='markers',
                marker=dict(symbol=cfg['sym'], size=cfg['sz'], color=cfg['clr'],
                            line=dict(width=lw, color='white' if 'open' not in cfg['sym'] else cfg['clr'])),
                name=nm,
            ), row=1, col=1)

        br = df_chart['Close'] < df_chart['Open']
        fig.add_trace(go.Bar(x=df_chart.index, y=df_chart['Volume'],
                             marker_color=np.where(br, '#ef5350', '#26a69a').tolist(),
                             name="거래량", opacity=0.7), row=2, col=1)
        vcm = df_chart.get('Volume_Climax_Buy', pd.Series(False, index=df_chart.index)) | \
              df_chart.get('Volume_Climax_Sell', pd.Series(False, index=df_chart.index))
        vcd = df_chart[vcm]
        if not vcd.empty:
            fig.add_trace(go.Bar(x=vcd.index, y=vcd['Volume'],
                                 marker_color='#FFD700', name="Vol Climax", opacity=0.9), row=2, col=1)

        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['WT1'],
                                 line=dict(color='#00E676', width=2), name="WT1"), row=3, col=1)
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['WT2'],
                                 line=dict(color='#FF1744', width=1.5, dash='dot'), name="WT2"), row=3, col=1)
        wd = df_chart['WT1'] - df_chart['WT2']
        fig.add_trace(go.Bar(x=df_chart.index, y=wd,
                             marker_color=np.where(wd >= 0, '#00E676', '#FF1744').tolist(),
                             name="WT Hist", opacity=0.3), row=3, col=1)
        wb = df_chart[df_chart['Green_Circle'] | df_chart['Green_Dot'] | df_chart['Gold_Dot']]
        if not wb.empty:
            fig.add_trace(go.Scatter(x=wb.index, y=wb['WT1'], mode='markers',
                                     marker=dict(symbol='circle', size=10, color='#00E676',
                                                 line=dict(width=1, color='white')),
                                     showlegend=False), row=3, col=1)
        ws = df_chart[df_chart['Red_Circle'] | df_chart['Red_Dot']]
        if not ws.empty:
            fig.add_trace(go.Scatter(x=ws.index, y=ws['WT1'], mode='markers',
                                     marker=dict(symbol='circle', size=10, color='#FF1744',
                                                 line=dict(width=1, color='white')),
                                     showlegend=False), row=3, col=1)
        for lv, c, d in [(OB2, '#ff3333', 'dash'), (OB1, '#ff3333', 'solid'),
                          (0, 'gray', 'dot'), (OS1, '#00bfff', 'solid'), (OS2, '#00bfff', 'dash')]:
            fig.add_hline(y=lv, line_dash=d, line_color=c, line_width=1, row=3, col=1)
        wmx = max(float(df_chart['WT1'].max()), 100) + 10
        wmn = min(float(df_chart['WT1'].min()), -100) - 10
        fig.add_hrect(y0=OB1, y1=wmx, fillcolor="rgba(255,23,68,0.08)", line_width=0, row=3, col=1)
        fig.add_hrect(y0=wmn, y1=OS1, fillcolor="rgba(0,191,255,0.08)", line_width=0, row=3, col=1)
        if 'Squeeze_On' in df_chart.columns:
            sq = df_chart['Squeeze_On']
            sd = sq.astype(int).diff().fillna(0)
            ss_list = df_chart.index[sd == 1].tolist()
            se_list = df_chart.index[sd == -1].tolist()
            if sq.iloc[0]:
                ss_list.insert(0, df_chart.index[0])
            if sq.iloc[-1]:
                se_list.append(df_chart.index[-1])
            for s0, e0 in zip(ss_list, se_list):
                fig.add_vrect(x0=s0, x1=e0, fillcolor="rgba(255,255,0,0.05)", line_width=0, row=3, col=1)

        rmfi = df_chart['RSI_MFI']
        fig.add_trace(go.Bar(x=df_chart.index, y=rmfi,
                             marker_color=np.where(rmfi >= 0, '#3ee145', '#ff3d2e').tolist(),
                             name="Money Flow", opacity=0.7), row=4, col=1)
        fig.add_hline(y=0, line_dash="solid", line_color="gray", line_width=1, row=4, col=1)

        conf = df_chart['Confluence_Score']
        fig.add_trace(go.Bar(x=df_chart.index, y=conf,
                             marker_color=np.where(conf >= 3.5, '#00E676',
                                          np.where(conf <= -3.5, '#FF1744', '#FFC107')).tolist(),
                             name="Confluence", opacity=0.8), row=5, col=1)
        for lv, c, d in [(6, '#00E676', 'dash'), (-6, '#FF1744', 'dash'),
                          (3.5, '#00E676', 'dot'), (-3.5, '#FF1744', 'dot'), (0, 'gray', 'solid')]:
            fig.add_hline(y=lv, line_dash=d, line_color=c, line_width=1 if d == 'solid' else 0.8, row=5, col=1)

        fig.update_layout(
            title=dict(text=f"📊 {ticker.upper()} | 💎 Market Cipher B+ | {trend_regime}",
                       font=dict(size=14, color='#FAFAFA')),
            yaxis_title="USD", yaxis2_title="Vol", yaxis3_title="WT", yaxis4_title="MF", yaxis5_title="Conf",
            template="plotly_dark", margin=dict(l=0, r=0, t=50, b=0), height=1100, showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
                        font=dict(size=9, color='#AAAAAA'), bgcolor='rgba(0,0,0,0)'),
        )
        fig.update(layout_xaxis_rangeslider_visible=False)
        for ann in fig['layout']['annotations']:
            ann['font'] = dict(size=11, color='#888888')

        # ── 프롬프트 텍스트 ──
        rd = df_chart.tail(60)
        ps = ", ".join([f"'{d.strftime('%Y-%m-%d')}:{r['Close']:.2f}'" for d, r in rd.iterrows()])
        all_sig_cols = [(k, f"{v['icon']} {v['label']}") for k, v in ALL_CHART_SIGNALS.items()]
        sl = []
        for ir, row in df_chart.tail(30).iterrows():
            dd = ir.strftime('%Y-%m-%d')
            for c, l in all_sig_cols:
                if row.get(c, False):
                    sl.append(f"{l} {dd}")
        st_text = "\n".join(sl) if sl else "최근 30일 내 주요 시그널 없음"
        bp = float(latest['Buy_Proximity'])
        sp = float(latest['Sell_Proximity'])
        prox_text = f"Buy Proximity={bp:.0f}%, Sell Proximity={sp:.0f}%"
        if bp >= 60:
            prox_text += " ⚠️ 매수 시그널 임박!"
        if sp >= 60:
            prox_text += " ⚠️ 매도 시그널 임박!"
        sq_text = "Squeeze ON (변동성 응축 중 → 폭발 임박)" if latest.get('Squeeze_On', False) else "Squeeze OFF"

        inds = (
            f"WT1={latest['WT1']:.1f}, WT2={latest['WT2']:.1f}, "
            f"RSI={latest['RSI']:.1f}, MFI={latest['MFI']:.1f}, "
            f"StochK={latest['StochK']:.1f}, StochD={latest['StochD']:.1f}, "
            f"VWAP_Osc={latest['VWAP_Osc']:.2f}, MF_Area={latest['RSI_MFI']:.1f}, "
            f"ADX={latest['ADX']:.1f}, +DI={latest['Plus_DI']:.1f}, -DI={latest['Minus_DI']:.1f}, "
            f"Confluence={conf_now:.1f}, Bias={bias}({bscore:.1f}), "
            f"Trend={trend_regime}, "
            f"{prox_text}, {sq_text}"
        )
        enhanced = f"{ps}\n\n📌 [지표]\n{inds}\n\n📌 [시그널]\n{st_text}"
        return fig, enhanced, meta

    except Exception as e:
        return None, f"주가 데이터 로딩 실패: {e}", None


# ──────────────────────────────────────────
# UI 렌더 헬퍼 함수들
# ──────────────────────────────────────────
def _indicator_label(name, value):
    if name == 'wt1':
        if value < -53: return '극과매도'
        elif value < -20: return '과매도'
        elif value > 53: return '극과매수'
        elif value > 20: return '과매수'
        else: return '중립'
    elif name in ('rsi', 'mfi'):
        if value < 30: return '과매도'
        elif value < 45: return '약세'
        elif value > 70: return '과매수'
        elif value > 55: return '강세'
        else: return '중립'
    elif name == 'stochk':
        if value < 20: return '바닥'
        elif value > 80: return '천장'
        else: return ''
    return ''


def render_price_header(meta):
    chg = meta['price_change']
    chg_pct = meta['price_change_pct']
    chg_cls = 'price-change-up' if chg >= 0 else 'price-change-down'
    chg_ico = '▲' if chg >= 0 else '▼'
    vr = meta['volume'] / meta['avg_volume'] if meta['avg_volume'] else 0
    wt1_c = 'ind-bullish' if meta['wt1'] < -20 else ('ind-bearish' if meta['wt1'] > 20 else 'ind-neutral')
    rsi_c = 'ind-bullish' if meta['rsi'] < 40 else ('ind-bearish' if meta['rsi'] > 60 else 'ind-neutral')
    mfi_c = 'ind-bullish' if meta['mfi'] < 40 else ('ind-bearish' if meta['mfi'] > 60 else 'ind-neutral')
    mf_c  = 'ind-bullish' if meta['mf_area'] < 0 else ('ind-bearish' if meta['mf_area'] > 0 else 'ind-neutral')
    vol_c = 'ind-bullish' if vr > 1.5 else 'ind-neutral'
    adx_c = 'ind-bullish' if meta['adx'] > 25 else 'ind-neutral'
    cv = meta.get('confluence_score', 0)
    cf_c = 'ind-bullish' if cv >= 3.5 else ('ind-bearish' if cv <= -3.5 else 'ind-neutral')
    stk_c = 'ind-bullish' if meta['stochk'] < 30 else ('ind-bearish' if meta['stochk'] > 70 else 'ind-neutral')
    wt_lbl = _indicator_label('wt1', meta['wt1'])
    rsi_lbl = _indicator_label('rsi', meta['rsi'])
    mfi_lbl = _indicator_label('mfi', meta['mfi'])
    stk_lbl = _indicator_label('stochk', meta['stochk'])
    # ✅ NEW: 추세 레짐 표시
    trend = meta.get('trend_regime', 'NEUTRAL ⚪')

    st.markdown(f"""
    <div class="price-header">
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <div>
                <p class="price-label">💎 {meta['ticker']} · {meta['last_date']} · <b>{trend}</b></p>
                <p class="price-big" style="color:#FAFAFA;">${meta['price']:.2f}
                    <span class="{chg_cls}" style="font-size:1rem;margin-left:8px;">
                        {chg_ico} {abs(chg):.2f} ({abs(chg_pct):.2f}%)</span></p>
            </div>
            <div style="text-align:right;">
                <p class="price-label">ATR (변동성)</p>
                <p style="color:#FFC107;font-size:1.1rem;font-weight:600;margin:0;">
                    ${meta['atr']:.2f} ({meta['atr_pct']:.1f}%)</p>
            </div>
        </div>
        <div style="margin-top:10px;display:flex;gap:6px;flex-wrap:wrap;">
            <span class="indicator-mini {wt1_c}">WT: {meta['wt1']:.0f} {wt_lbl}</span>
            <span class="indicator-mini {rsi_c}">RSI: {meta['rsi']:.0f} {rsi_lbl}</span>
            <span class="indicator-mini {mfi_c}">MFI: {meta['mfi']:.0f} {mfi_lbl}</span>
            <span class="indicator-mini {mf_c}">MF: {meta['mf_area']:.1f}</span>
            <span class="indicator-mini {vol_c}">Vol: {vr:.1f}x</span>
            <span class="indicator-mini {adx_c}">ADX: {meta['adx']:.0f}</span>
            <span class="indicator-mini {stk_c}">StK: {meta['stochk']:.0f} {stk_lbl}</span>
            <span class="indicator-mini {cf_c}">Conf: {cv:.1f}</span>
        </div>
    </div>""", unsafe_allow_html=True)


def render_bias_badge(meta):
    bias = meta['overall_bias']; sc = meta.get('bias_score', 0); cv = meta.get('confluence_score', 0)
    if 'STRONG BUY' in bias:    bg, clr, ico = 'rgba(0,230,118,0.2)', '#00E676', '🟢🟢'
    elif 'BUY' in bias:         bg, clr, ico = 'rgba(0,230,118,0.12)', '#00E676', '🟢'
    elif 'STRONG SELL' in bias: bg, clr, ico = 'rgba(255,23,68,0.2)', '#FF1744', '🔴🔴'
    elif 'SELL' in bias:        bg, clr, ico = 'rgba(255,23,68,0.12)', '#FF1744', '🔴'
    else:                       bg, clr, ico = 'rgba(255,193,7,0.12)', '#FFC107', '🟠'
    cc = '#00E676' if cv >= 3.5 else ('#FF1744' if cv <= -3.5 else '#FFC107')
    max_score = 13.0
    gauge_pct = max(0, min(100, ((sc + max_score) / (2 * max_score)) * 100))

    st.markdown(f"""<div style="background:{bg};border-radius:10px;padding:12px 16px;text-align:center;margin:8px 0;">
        <span style="font-size:1.2rem;font-weight:700;color:{clr};">{ico} 종합 판정: {bias} ({sc:.1f})</span><br>
        <span style="font-size:0.9rem;color:{cc};font-weight:600;">📊 Confluence: {cv:.1f}</span>
        <div class="bias-gauge-track" style="margin:10px auto;max-width:300px;">
            <div class="bias-gauge-needle" style="left:{gauge_pct}%;"></div>
        </div>
        <div style="display:flex;justify-content:space-between;max-width:300px;margin:0 auto;">
            <span style="color:#FF1744;font-size:0.65rem;">STRONG SELL</span>
            <span style="color:#888;font-size:0.65rem;">NEUTRAL</span>
            <span style="color:#00E676;font-size:0.65rem;">STRONG BUY</span>
        </div>
    </div>""", unsafe_allow_html=True)


def render_proximity_alert(meta):
    bp = meta.get('buy_proximity', 0)
    sp = meta.get('sell_proximity', 0)
    sq = meta.get('squeeze_on', False)
    alerts = []
    if bp >= 70:
        alerts.append(('🟢⚡ 매수 시그널 매우 임박!', '#00E676', bp))
    elif bp >= 50:
        alerts.append(('🟢 매수 시그널 접근 중', '#69F0AE', bp))
    if sp >= 70:
        alerts.append(('🔴⚡ 매도 시그널 매우 임박!', '#FF1744', sp))
    elif sp >= 50:
        alerts.append(('🔴 매도 시그널 접근 중', '#FF5252', sp))
    if sq:
        alerts.append(('💥 Squeeze ON — 변동성 폭발 임박', '#FFFF00', 80))
    if not alerts:
        return
    for txt, clr, pct in alerts:
        w = min(pct, 100)
        st.markdown(f"""
        <div style="background:rgba(255,255,255,0.03);border:1px solid #2D333B;border-radius:8px;
                    padding:8px 14px;margin:4px 0;">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <span style="color:{clr};font-weight:600;font-size:0.9rem;">{txt}</span>
                <span style="color:{clr};font-weight:700;font-size:0.85rem;">{pct:.0f}%</span>
            </div>
            <div style="background:#1A1D24;border-radius:3px;height:6px;margin-top:6px;">
                <div style="background:{clr};width:{w}%;height:6px;border-radius:3px;"></div>
            </div>
        </div>""", unsafe_allow_html=True)


def render_signal_cards(meta):
    sigs = meta['recent_signals']
    if not sigs:
        st.markdown("""<div class="signal-card signal-card-neutral">
            <p style="margin:0;color:#FFC107;font-weight:600;">🟠 최근 30일 내 주요 시그널 없음</p>
            <p style="margin:4px 0 0 0;color:#888;font-size:0.85rem;">관망 구간입니다.</p></div>""",
                    unsafe_allow_html=True)
        return

    from collections import OrderedDict
    date_groups = OrderedDict()
    for icon, lbl, d_str, side in sigs:
        if d_str not in date_groups:
            date_groups[d_str] = []
        date_groups[d_str].append((icon, lbl, side))

    for d_str in reversed(date_groups):
        group = date_groups[d_str]
        buy_count = sum(1 for _, _, s in group if s == 'buy')
        sell_count = sum(1 for _, _, s in group if s == 'sell')
        if buy_count > sell_count:
            ct = 'signal-card-buy'
        elif sell_count > buy_count:
            ct = 'signal-card-sell'
        else:
            ct = 'signal-card-neutral'
        sig_html_parts = []
        for icon, lbl, side in group:
            badge_cls = 'ind-bullish' if side == 'buy' else 'ind-bearish'
            sig_html_parts.append(f'<span class="indicator-mini {badge_cls}">{icon} {lbl}</span>')
        sig_list_html = " ".join(sig_html_parts)
        count_text = f"{len(group)}개 신호" if len(group) > 1 else "1개 신호"
        st.markdown(f"""<div class="signal-card {ct}">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <span style="font-weight:700;font-size:0.9rem;color:#FAFAFA;">📅 {d_str}</span>
                <span style="color:#888;font-size:0.75rem;">{count_text}</span>
            </div>
            <div style="margin-top:6px;display:flex;gap:4px;flex-wrap:wrap;">{sig_list_html}</div>
        </div>""", unsafe_allow_html=True)


def render_signal_stats(meta):
    with st.expander("📊 시그널 백테스트 통계 (과거 2년, 최소 5회 이상)", expanded=True):
        alls = meta.get('all_signal_stats', {})
        if not alls:
            st.caption("통계 데이터 없음 (최소 발생 횟수 미달)"); return
        bs = {k: v for k, v in alls.items() if v['direction'] == 'buy'}
        ss_dict = {k: v for k, v in alls.items() if v['direction'] == 'sell'}
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### 🟢 BUY 시그널")
            for sn, sv in sorted(bs.items(), key=lambda x: x[1]['count'], reverse=True):
                wr = sv.get('10d_winrate'); av = sv.get('10d_avg')
                if wr is not None:
                    clr = '#00E676' if wr > 55 else ('#FFC107' if wr > 45 else '#FF1744')
                    icon = ALL_CHART_SIGNALS.get(sn, {}).get('icon', '')
                    st.markdown(f"<span style='font-size:0.82rem;'>{icon} **{sn}** ({sv['count']}회) · "
                                f"10일 상승 <span style='color:{clr}'>{wr:.0f}%</span> · 평균 {av:+.1f}%</span>",
                                unsafe_allow_html=True)
        with c2:
            st.markdown("##### 🔴 SELL 시그널")
            for sn, sv in sorted(ss_dict.items(), key=lambda x: x[1]['count'], reverse=True):
                wr = sv.get('10d_winrate'); av = sv.get('10d_avg')
                if wr is not None:
                    drop_rate = 100 - wr
                    clr = '#FF1744' if drop_rate > 55 else ('#FFC107' if drop_rate > 45 else '#00E676')
                    icon = ALL_CHART_SIGNALS.get(sn, {}).get('icon', '')
                    st.markdown(
                        f"<span style='font-size:0.82rem;'>{icon} **{sn}** ({sv['count']}회) · "
                        f"10일 후 하락 확률 <span style='color:{clr}'>{drop_rate:.0f}%</span> · "
                        f"평균 변동 {av:+.1f}%</span>",
                        unsafe_allow_html=True)


def render_inline_analysis(msg):
    meta = msg.get('meta')
    fig = msg.get('fig')
    if meta:
        render_price_header(meta)
        render_bias_badge(meta)
        render_proximity_alert(meta)
        render_signal_cards(meta)
    if fig:
        st.plotly_chart(fig, use_container_width=True, theme=None)
    if meta:
        render_signal_stats(meta)


# ──────────────────────────────────────────
# 사이드바
# ──────────────────────────────────────────
with st.sidebar:
    st.markdown("## 💎 CipherX")
    st.markdown("<p style='color:#888;font-size:0.8rem;'>AI 주가 분석 · Market Cipher B+ v2.2</p>", unsafe_allow_html=True)
    st.markdown("---")

    st.markdown("### 📅 차트 기간")
    chart_period = st.radio("표시 기간", ['3개월', '6개월', '1년', '2년'],
                            index=2, horizontal=True, key="chart_period_radio")
    chart_days = {'3개월': 63, '6개월': 126, '1년': 252, '2년': 504}[chart_period]
    st.markdown("---")

    if st.button("🗑️ 대화 초기화", use_container_width=True, type="secondary"):
        st.session_state.messages = [
            {"role": "assistant", "type": "text",
             "content": "안녕하세요! 💎 **CipherX** 입니다.\n\n분석할 **티커명**을 입력하세요."}
        ]
        st.session_state.pending_ai_ticker = None
        st.session_state.pending_ai_prompt = None
        st.rerun()
    st.markdown("---")

    st.markdown("### 📖 신호 가이드")

    BUY_GUIDE_ORDER = [
        'Ultra_Buy', 'Strong_Buy', 'Gold_Dot', 'Green_Dot_T1', 'Green_Dot_T2',
        'Blue_Diamond', 'Green_Circle', 'Bull_Divergence', 'Hidden_Bull_Div',
        'Squeeze_Fire_Buy', 'Volume_Climax_Buy', 'OBV_Div_Buy',
        'ADX_Momentum_Buy', 'Fib_Bounce_Buy', 'Bullish_Engulfing', 'Golden_Cross',
    ]
    SELL_GUIDE_ORDER = [
        'Ultra_Sell', 'Strong_Sell', 'Blood_Diamond', 'Red_Dot_T1', 'Red_Dot_T2',
        'Red_Diamond', 'Red_Circle', 'Bear_Divergence', 'Hidden_Bear_Div',
        'Squeeze_Fire_Sell', 'Volume_Climax_Sell', 'OBV_Div_Sell',
        'ADX_Momentum_Sell', 'Fib_Resistance_Sell', 'Bearish_Engulfing', 'Death_Cross',
    ]

    with st.expander("🟢 매수 신호 (BUY)", expanded=False):
        for k in BUY_GUIDE_ORDER:
            if k in SIGNAL_DESCRIPTIONS:
                info = SIGNAL_DESCRIPTIONS[k]
                chart_name = f"{info['chart_icon']} {info['chart_label']}"
                st.markdown(
                    f"**{chart_name}** · <span style='color:#888;font-size:0.82rem;'>{info['kor']}</span>",
                    unsafe_allow_html=True,
                )
                st.caption(info['desc'])
                st.markdown("<hr style='border:none;border-top:1px solid #222;margin:4px 0;'>", unsafe_allow_html=True)

    with st.expander("🔴 매도 신호 (SELL)", expanded=False):
        for k in SELL_GUIDE_ORDER:
            if k in SIGNAL_DESCRIPTIONS:
                info = SIGNAL_DESCRIPTIONS[k]
                chart_name = f"{info['chart_icon']} {info['chart_label']}"
                st.markdown(
                    f"**{chart_name}** · <span style='color:#888;font-size:0.82rem;'>{info['kor']}</span>",
                    unsafe_allow_html=True,
                )
                st.caption(info['desc'])
                st.markdown("<hr style='border:none;border-top:1px solid #222;margin:4px 0;'>", unsafe_allow_html=True)

    # ✅ NEW: 추세 필터 설명 추가
    with st.expander("🛡️ 추세 필터 시스템", expanded=False):
        st.markdown("""
**추세 레짐 감지**
- `STRONG BULL 🟢`: ADX>25 + Plus DI > Minus DI + Close > MA50
- `STRONG BEAR 🔴`: ADX>25 + Minus DI > Plus DI + Close < MA50
- `EXTREME`: Strong + MA200 확인 + MA50 기울기 확인

**티어별 필터링**
- **Tier 1** (Gold Dot, Blood Diamond): ❌ 절대 억제 안 함
- **Tier 2** (T1, Divergence): 극단 역추세에서만 억제
- **Tier 3** (T2, Diamond, Circle, Squeeze, Engulfing): 강한 역추세에서 억제
- **Tier 4** (Fib, OBV Div): 일반 역추세에서도 억제

**자금 흐름 필터**
- Blue Diamond: RSI_MFI > -10 (자금 대량 유출 중이면 억제)
- Red Diamond: RSI_MFI < 10 (자금 대량 유입 중이면 억제)
        """)

    with st.expander("📊 지표 해석 가이드", expanded=False):
        st.markdown("""
**WaveTrend (WT1/WT2)**
- WT1 < -53: 과매도 · WT1 > 53: 과매수
- WT1이 WT2를 상향돌파: 매수 교차
- WT1이 WT2를 하향돌파: 매도 교차

**RSI / MFI**
- < 30: 과매도 · > 70: 과매수

**Confluence Score**
- ≥ 6.0: Ultra Buy · 3.5~6.0: Strong Buy
- -3.5~3.5: Neutral
- -6.0~-3.5: Strong Sell · ≤ -6.0: Ultra Sell

**TTM Squeeze**
- ON: 변동성 응축 (폭발 대기)
- OFF: 정상 변동성
        """)

    st.markdown("---")
    st.markdown("<p style='color:#555;font-size:0.7rem;text-align:center;'>CipherX v2.2 · Trend-Filtered Engine</p>", unsafe_allow_html=True)


# ──────────────────────────────────────────
# 세션 초기화
# ──────────────────────────────────────────
if 'messages' not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "type": "text",
         "content": "안녕하세요! 💎 **CipherX** 입니다.\n\n분석할 **티커명**을 입력하세요. 채팅처럼 자유롭게 여러 종목을 이어서 분석할 수 있습니다."}
    ]
if 'pending_ai_ticker' not in st.session_state:
    st.session_state.pending_ai_ticker = None
if 'pending_ai_prompt' not in st.session_state:
    st.session_state.pending_ai_prompt = None


# ──────────────────────────────────────────
# 프롬프트 생성 함수
# ──────────────────────────────────────────
def build_analysis_prompt(ticker_value, phist, scraped):
    return f"""━━━━━━━━━━━━━ 
【 🎯 Role 】
━━━━━━━━━━━━━ 
당신은 월스트리트 20년+ 경력 베테랑 주식 애널리스트이자 펀드 매니저입니다.
기술적 분석과 시장 심리 파악에 탁월하며, Market Cipher B 지표 해석에 정통합니다.

---
━━━━━━━━━━━━━
【 🛠️ Task 】
━━━━━━━━━━━━━ 
아래 데이터로 심층 주가 분석 보고서를 작성하세요.

💎 시그널은 추세 필터가 적용되었습니다:
- Tier 1 (Gold Dot, Blood Diamond): 추세 무관 항상 유효
- Tier 2 (T1, Divergence): 극단 역추세에서만 억제됨
- Tier 3 (T2, Diamond, Circle 등): 강한 역추세에서 억제됨

🔥 Confluence Score (시간 감쇠 적용): ≥6 Ultra Buy | 3.5~6 Strong Buy | -3.5~3.5 Neutral | -6~-3.5 Strong Sell | ≤-6 Ultra Sell

⚠️ Trend Regime: 현재 추세 상태를 반드시 고려하세요.
⚠️ Signal Proximity: 매수/매도 시그널 임박 여부를 반드시 언급하세요.

주가변동이유/이벤트, 공매도, 콜/풋옵션 → DEEP SEARCH.

---
━━━━━━━━━━━━━ 
【 📥 Input Data 】
━━━━━━━━━━━━━ 
[티커: {ticker_value}]

📌 [주가 + 지표]
{phist}

📌 [SwingTradeBot]
{scraped}

---
━━━━━━━━━━━━━ 
【 ✍️ Guidelines 】
━━━━━━━━━━━━━ 
① 한국어, 전문적이면서 이해하기 쉽게
② 확신형 어조
③ 불릿/강조/이모티콘(🔵긍정 🔴부정 🟠중간)
④ Trend Regime과 시그널의 신뢰도를 연계하여 분석
⑤ 시나리오별 확률(%) + 근거
⑥ 기술적 vs 심리지표 충돌 판단
⑦ 섹터/지수 동조성, 베타
⑧ 지지/저항

━━━━━━━━━━━━━ 
【 📄 Output Format 】
━━━━━━━━━━━━━ 

[🔵/🔴/🟠] [{ticker_value}] 분석: [핵심 한 줄]
[날짜], 전일 대비 [변동률]% [방향]. 거래량 [배수]. 지지 [가격], 저항 [가격].

---
### 내용 요약
[🔵/🔴/🟠] [3~4문장]

---
### 🛡️ 추세 상태 & 시그널 신뢰도
* 현재 추세 레짐: [STRONG BULL/BEAR/NEUTRAL]
* 시그널 필터 상태: [어떤 시그널이 억제/통과되었는지]
* 신뢰도 종합: [높음/중간/낮음 + 근거]

---
### 💎 마켓 사이퍼 B+ 시그널 분석
* WaveTrend: [WT1/WT2, 상태]
* Money Flow: [방향]
* 🔥 Confluence Score: [점수, 판정]
* ⚠️ Signal Proximity: [매수/매도 임박 여부]
* 최근 시그널: [목록]
> 💎 해석:

---
### 주가 및 거래량 분석
* 거래량: 평균 대비 [배수]
* 거래량 해석: [스마트머니 유입/이탈]
> 해석: [🔵/🔴/🟠]

---
### 장중 기술적 지표
* 패턴: [식별된 패턴]
* ATR ±__%, ADX, TTM Squeeze, MA Cross
> 해석: [🔵/🔴/🟠]

---
### 지지선 및 저항선
* 지지선: [가격들]
* 저항선: [가격들]

---
### 콜/풋옵션 현황
* 시사점: [심리 분석]
> [🔵/🔴/🟠]

---
### 공매도현황
* 시사점: [숏스퀴즈 가능성]

---
### 주가변동이유 및 이벤트
- [🔵/🔴/🟠] [이유] — 단발성/추세형

---
### 종합해석 및 전망
* 🔵 Bullish: [조건] → [목표가]. 확률: __%
* 🟠 Base: [시나리오]. 확률: __%
* 🔴 Bearish: [조건] → [목표가]. 확률: __%

전략:
공격적 매수: [가격대]
보수적 진입: [가격대]
손절: [가격]
분할매도: 1차 [가격] __%, 2차 [가격] __%

---
### 결론
[🔵/🔴/🟠] [2~3문장]

### 주가 예측 (다음 거래일)
[🔵/🔴/🟠] 예상: [방향] · 근거: [...]
[GRADE/Score]: [이유]"""


# ──────────────────────────────────────────
# 메인 영역
# ──────────────────────────────────────────
st.markdown("<h2 style='text-align:center;color:#fff;margin-bottom:20px;'>💎 CipherX</h2>", unsafe_allow_html=True)

for i, msg in enumerate(st.session_state.messages):
    av = "✨" if msg["role"] == "assistant" else "🧑‍💻"
    with st.chat_message(msg["role"], avatar=av):
        if msg.get("type") == "analysis":
            st.markdown(msg.get("content", ""))
            render_inline_analysis(msg)
            if msg.get("prompt"):
                with st.expander("📝 생성된 프롬프트 확인", expanded=False):
                    st.code(msg["prompt"], language="markdown")
                    st_copy_to_clipboard(msg["prompt"],
                                         before_copy_label="📋 복사", after_copy_label="✅ 복사됨!")
        elif msg.get("type") == "report":
            with st.expander(f"📊 {msg.get('ticker', '')} AI 심층 분석 리포트", expanded=True):
                st.markdown(msg["content"])
            ns = datetime.now().strftime("%Y%m%d_%H%M")
            tn = msg.get("ticker", "report").upper()
            st.download_button("📥 다운로드 (.md)", key=f"dl_{i}",
                               data=msg["content"].encode('utf-8'),
                               file_name=f"{tn}_Report_{ns}.md", mime="text/markdown",
                               use_container_width=True)
        else:
            st.markdown(msg.get("content", ""))

if st.session_state.pending_ai_ticker and st.session_state.pending_ai_prompt:
    ticker_pending = st.session_state.pending_ai_ticker
    prompt_pending = st.session_state.pending_ai_prompt
    if st.button(f"🚀 {ticker_pending.upper()} AI 심층 분석 시작", type="primary", use_container_width=True):
        with st.chat_message("assistant", avatar="✨"):
            pb = st.progress(0, text="AI 분석 초기화 중...")
            try:
                pb.progress(10, text="Gemini 모델 로딩...")
                model = genai.GenerativeModel('gemini-flash-latest')
                pb.progress(20, text="시장 데이터 분석 중...")
                resp = model.generate_content(prompt_pending, stream=True)
                pb.progress(40, text="AI 리포트 생성 중...")
                rpt = ""; rph = st.empty(); cc = 0
                for chunk in resp:
                    rpt += chunk.text; rph.markdown(rpt + " ▌"); cc += 1
                    pb.progress(min(40 + cc * 2, 95), text="AI 리포트 작성 중...")
                pb.progress(100, text="✅ 분석 완료!"); time.sleep(0.5); pb.empty()
                rph.empty()
                st.session_state.messages.append({
                    "role": "assistant", "type": "report",
                    "ticker": ticker_pending.upper(), "content": rpt,
                })
                st.session_state.pending_ai_ticker = None
                st.session_state.pending_ai_prompt = None
                st.rerun()
            except Exception as e:
                pb.empty()
                st.error(f"AI 분석 중 오류 발생: {e}")


def process_ticker(ticker_value):
    ticker_value = ticker_value.strip().upper()
    st.session_state.messages.append({"role": "user", "type": "text", "content": ticker_value})
    with st.chat_message("assistant", avatar="✨"):
        pg = st.progress(0, text=f"🌐 {ticker_value} 데이터 수집 시작...")
        pg.progress(15, text="📡 SwingTradeBot 크롤링 중...")
        scraped = get_stock_data(ticker_value)
        pg.progress(40, text="📊 Yahoo Finance 주가 로딩 중...")
        cfig, phist, meta = get_yfinance_data_and_chart(ticker_value, chart_period_days=chart_days)
        pg.progress(70, text="💎 마켓 사이퍼 + 추세 필터 분석 중...")
        time.sleep(0.3)
        pg.progress(90, text="📝 프롬프트 생성 중...")
        if scraped or cfig:
            prompt = build_analysis_prompt(ticker_value, phist, scraped)
            analysis_msg = {
                "role": "assistant", "type": "analysis", "ticker": ticker_value,
                "content": f"✅ **{ticker_value}** 분석 완료! 아래에서 차트와 시그널을 확인하세요.",
                "fig": cfig, "meta": meta, "prompt": prompt,
            }
            st.session_state.messages.append(analysis_msg)
            st.session_state.pending_ai_ticker = ticker_value
            st.session_state.pending_ai_prompt = prompt
            pg.progress(100, text="✅ 완료!"); time.sleep(0.3); pg.empty()
            st.rerun()
        else:
            pg.empty()
            st.session_state.messages.append({
                "role": "assistant", "type": "text",
                "content": f"⚠️ **{ticker_value}** 데이터 로딩 실패. 티커명을 확인하세요.",
            })
            st.rerun()


if ticker_input := st.chat_input("분석할 티커를 입력하세요 (예: IREN, TSLA, AAPL)"):
    process_ticker(ticker_input)