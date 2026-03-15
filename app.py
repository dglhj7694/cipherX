import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
import google.generativeai as genai
import time
import random
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
# 🎨 CSS (축약)
# ──────────────────────────────────────────
st.markdown("""
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
html, body, [class*="css"] { font-family: 'Pretendard', 'Noto Sans KR', sans-serif !important; }
:root {
    --bg-main: #0E1117; --bg-card: #161A22; --bg-code: #1A1D24;
    --clr-green: #00E676; --clr-red: #FF1744; --clr-yellow: #FFC107;
    --clr-text: #FAFAFA; --clr-muted: #888; --border: #2D333B;
}
.stApp { background-color: var(--bg-main); }
p, div[data-testid="stMarkdownContainer"] p,
div[data-testid="stChatMessageContent"] p,
h1, h2, h3, h4, h5, h6, li { color: var(--clr-text) !important; }
div[data-testid="stCodeBlock"], pre, code {
    background-color: var(--bg-code) !important; color: var(--clr-text) !important;
}
div[data-testid="stCodeBlock"] span { text-shadow: none !important; }
div[data-testid="stCodeBlock"] span[style*="color: rgb(0, 0, 0)"],
div[data-testid="stCodeBlock"] span[style*="color: black"],
div[data-testid="stCodeBlock"] code > span:not([class]) { color: var(--clr-text) !important; }
div[data-testid="stChatMessage"]:nth-child(even) {
    background-color: var(--bg-card); border-radius: 12px; padding: 5px 15px;
}
header {visibility: hidden;}
.block-container { padding-top: 1rem !important; max-width: 900px; }
div.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #667eea, #764ba2) !important;
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
    background-color: var(--bg-card) !important; border-radius: 10px !important; font-weight: 600 !important;
}
.streamlit-expanderHeader p { color: #414df2 !important; }
div[data-testid="stExpander"] {
    border: 1px solid var(--border) !important; border-radius: 10px !important; background-color: var(--bg-card);
}
section[data-testid="stSidebar"] {
    background-color: #0A0D12; border-right: 1px solid #1E2127;
}
section[data-testid="stSidebar"] .stMarkdown p { color: #AAAAAA !important; }
.signal-card {
    border-radius: 12px; padding: 16px 20px; margin: 6px 0; border: 1px solid var(--border);
}
.signal-card-buy {
    background: linear-gradient(135deg, rgba(0,230,118,0.08), rgba(0,191,255,0.05));
    border-left: 4px solid var(--clr-green);
}
.signal-card-sell {
    background: linear-gradient(135deg, rgba(255,23,68,0.08), rgba(255,82,82,0.05));
    border-left: 4px solid var(--clr-red);
}
.signal-card-neutral {
    background: linear-gradient(135deg, rgba(255,193,7,0.08), rgba(255,152,0,0.05));
    border-left: 4px solid var(--clr-yellow);
}
.price-header {
    background: linear-gradient(135deg, var(--bg-card), #1A1F2E);
    border: 1px solid var(--border); border-radius: 14px;
    padding: 18px 24px; margin-bottom: 16px;
}
.price-big { font-size: 2rem; font-weight: 700; margin: 0; }
.price-change-up { color: var(--clr-green) !important; }
.price-change-down { color: var(--clr-red) !important; }
.price-label { color: #666 !important; font-size: 0.8rem; margin: 0; }
.indicator-mini {
    display: inline-block; padding: 4px 10px; margin: 2px;
    border-radius: 6px; font-size: 0.78rem; font-weight: 500;
}
.ind-bullish { background: rgba(0,230,118,0.15); color: var(--clr-green); }
.ind-bearish { background: rgba(255,23,68,0.15); color: var(--clr-red); }
.ind-neutral { background: rgba(255,193,7,0.15); color: var(--clr-yellow); }
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
.sr-level {
    display: inline-block; padding: 3px 8px; margin: 2px;
    border-radius: 5px; font-size: 0.75rem; font-weight: 600;
}
.sr-support { background: rgba(0,230,118,0.12); color: var(--clr-green); border: 1px solid rgba(0,230,118,0.3); }
.sr-resist { background: rgba(255,23,68,0.12); color: var(--clr-red); border: 1px solid rgba(255,23,68,0.3); }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────
# 시그널 레지스트리 (V3.1 — 매수/매도 대칭 생성)
# ──────────────────────────────────────────
def _make_signal(w, d, icon, label, sym, sz, clr, base, atr_m):
    return {'w': w, 'dir': d, 'icon': icon, 'label': label, 'sym': sym,
            'sz': sz, 'clr': clr, 'base': base, 'atr_m': atr_m}

SIGNAL_REGISTRY = {
    # ═══ 매수 시그널 ═══
    'Gold_Dot':              _make_signal(3.0, 'buy',  '🏆', 'GOLD DOT',       'circle',         18, '#FFD700', 'Low',  -3.0),
    'Green_Dot_T1':          _make_signal(2.5, 'buy',  '🟢', 'BUY T1',         'circle',         16, '#00E676', 'Low',  -2.5),
    'Green_Dot_T2':          _make_signal(2.0, 'buy',  '🟩', 'BUY T2',         'circle',         13, '#69F0AE', 'Low',  -2.2),
    'Blue_Diamond':          _make_signal(2.0, 'buy',  '🔹', 'BLUE DIA',       'diamond',        14, '#00bfff', 'Low',  -1.8),
    'Green_Circle':          _make_signal(1.5, 'buy',  '✅', 'BUY Circle',     'circle-open',    11, '#00E676', 'Low',  -1.2),
    'Bull_Divergence':       _make_signal(2.0, 'buy',  '📈', 'Bull Div',       'triangle-up',    12, '#AA00FF', 'Low',  -2.0),
    'Squeeze_Fire_Buy':      _make_signal(1.5, 'buy',  '💥', 'Squeeze BUY',    'star-diamond',   14, '#00FFFF', 'Low',  -1.5),
    'Hidden_Bull_Div':       _make_signal(1.5, 'buy',  '🔀', 'Hidden Bull',    'triangle-up',    10, '#E040FB', 'Low',  -1.6),
    'Volume_Climax_Buy':     _make_signal(2.0, 'buy',  '🌊', 'Vol Climax BUY', 'hexagram',       14, '#00BCD4', 'Low',  -2.8),
    'OBV_Div_Buy':           _make_signal(1.5, 'buy',  '📊', 'OBV Div BUY',   'triangle-up',    10, '#80DEEA', 'Low',  -1.4),
    'ADX_Momentum_Buy':      _make_signal(1.5, 'buy',  '🚀', 'ADX Ignition',   'arrow-up',       11, '#76FF03', 'Low',  -1.4),
    'Fib_Bounce_Buy':        _make_signal(1.0, 'buy',  '📐', 'Fib Bounce',     'diamond-open',   10, '#FFAB00', 'Low',  -1.0),
    'Bullish_Engulfing':     _make_signal(1.5, 'buy',  '☀️', 'Bull Engulf',    'square',         10, '#00E676', 'Low',  -1.3),
    'Golden_Cross':          _make_signal(1.5, 'buy',  '✨', 'Golden Cross',   'cross',          12, '#FFD700', 'Low',  -0.8),
    'EMA_Pullback_Buy':      _make_signal(2.0, 'buy',  '🎯', 'EMA Pullback',   'triangle-up',    13, '#00BFA5', 'Low',  -1.8),
    'Momentum_Ignition_Buy': _make_signal(2.5, 'buy',  '🔥', 'Mom. Ignition',  'star-diamond',   15, '#FF6D00', 'Low',  -2.5),
    'SuperTrend_Buy':        _make_signal(1.5, 'buy',  '📈', 'ST Flip Bull',   'arrow-up',       12, '#00E5FF', 'Low',  -1.5),
    'MACD_Cross_Buy':        _make_signal(1.5, 'buy',  '〽️', 'MACD Cross',    'triangle-up',    11, '#00E676', 'Low',  -1.3),
    'RSI_Divergence_Buy':    _make_signal(1.5, 'buy',  '📉', 'RSI Bull Div',   'triangle-up',    10, '#64FFDA', 'Low',  -1.5),
    # ═══ 매도 시그널 ═══
    'Blood_Diamond':          _make_signal(3.0, 'sell', '🩸', 'BLOOD DIA',      'diamond',        18, '#DC143C', 'High', 3.0),
    'Red_Dot_T1':             _make_signal(2.5, 'sell', '🔴', 'SELL T1',        'circle',         16, '#FF1744', 'High', 2.5),
    'Red_Dot_T2':             _make_signal(2.0, 'sell', '🟥', 'SELL T2',        'circle',         13, '#FF5252', 'High', 2.2),
    'Red_Diamond':            _make_signal(2.0, 'sell', '🔸', 'RED DIA',        'diamond',        14, '#ff3333', 'High', 1.8),
    'Red_Circle':             _make_signal(1.5, 'sell', '⛔', 'SELL Circle',    'circle-open',    11, '#FF1744', 'High', 1.2),
    'Bear_Divergence':        _make_signal(2.0, 'sell', '📉', 'Bear Div',       'triangle-down',  12, '#AA00FF', 'High', 2.0),
    'Squeeze_Fire_Sell':      _make_signal(1.5, 'sell', '🧨', 'Squeeze SELL',   'star-diamond',   14, '#FF6600', 'High', 1.5),
    'Hidden_Bear_Div':        _make_signal(1.5, 'sell', '🔁', 'Hidden Bear',    'triangle-down',  10, '#E040FB', 'High', 1.6),
    'Volume_Climax_Sell':     _make_signal(2.0, 'sell', '🌋', 'Vol Climax SELL','hexagram',       14, '#FF5722', 'High', 2.8),
    'OBV_Div_Sell':           _make_signal(1.5, 'sell', '🔻', 'OBV Div SELL',  'triangle-down',  10, '#FFAB91', 'High', 1.4),
    'ADX_Momentum_Sell':      _make_signal(1.5, 'sell', '💨', 'ADX Down',       'arrow-down',     11, '#FF3D00', 'High', 1.4),
    'Fib_Resistance_Sell':    _make_signal(1.0, 'sell', '🚧', 'Fib Resist',     'diamond-open',   10, '#FF8F00', 'High', 1.0),
    'Bearish_Engulfing':      _make_signal(1.5, 'sell', '🌑', 'Bear Engulf',    'x',              10, '#D50000', 'High', 1.3),
    'Death_Cross':            _make_signal(1.5, 'sell', '☠️', 'Death Cross',    'cross',          12, '#FF1744', 'High', 0.8),
    'SuperTrend_Sell':        _make_signal(2.0, 'sell', '📉', 'ST Flip Bear',   'arrow-down',     12, '#FF1744', 'High', 1.5),
    'Parabolic_Top_Sell':     _make_signal(3.0, 'sell', '🌡️', 'Parabolic Top', 'diamond',        16, '#FF0000', 'High', 3.0),
    'EMA_Pullback_Sell':      _make_signal(2.0, 'sell', '🎯', 'EMA PB Sell',    'triangle-down',  13, '#FF6E40', 'High', 1.8),
    'Momentum_Ignition_Sell': _make_signal(2.5, 'sell', '💣', 'Mom. Ign Sell',  'star-diamond',   15, '#D50000', 'High', 2.5),
    'MACD_Cross_Sell':        _make_signal(1.5, 'sell', '〽️', 'MACD Cross',    'triangle-down',  11, '#FF1744', 'High', 1.3),
    'RSI_Divergence_Sell':    _make_signal(1.5, 'sell', '📈', 'RSI Bear Div',   'triangle-down',  10, '#FF8A80', 'High', 1.5),
}

COMPOSITE_SIGNALS = {
    'Ultra_Buy':  _make_signal(0, 'buy',  '⚡', 'ULTRA BUY',  'star', 20, '#FFD700', 'Low',  -3.5),
    'Strong_Buy': _make_signal(0, 'buy',  '🔱', 'STRONG BUY', 'star', 16, '#00E676', 'Low',  -3.2),
    'Ultra_Sell': _make_signal(0, 'sell', '🚨', 'ULTRA SELL', 'star', 20, '#FF0000', 'High', 3.5),
    'Strong_Sell':_make_signal(0, 'sell', '⚠️', 'STRONG SELL','star', 16, '#FF1744', 'High', 3.2),
}

BUY_SIGNALS  = {k: v for k, v in SIGNAL_REGISTRY.items() if v['dir'] == 'buy'}
SELL_SIGNALS = {k: v for k, v in SIGNAL_REGISTRY.items() if v['dir'] == 'sell'}
ALL_CHART_SIGNALS = {**SIGNAL_REGISTRY, **COMPOSITE_SIGNALS}

# ──────────────────────────────────────────
# 신호 설명 사전 (V3.1 — RSI Div 추가)
# ──────────────────────────────────────────
SIGNAL_DESCRIPTIONS = {
    'Ultra_Buy':              {'icon': '⚡', 'lbl': 'ULTRA BUY',      'kor': '울트라 매수',        'desc': 'Confluence ≥6 또는 (≥5 + 동시 3개). 모든 지표가 극단 매수.'},
    'Strong_Buy':             {'icon': '🔱', 'lbl': 'STRONG BUY',     'kor': '스트롱 매수',        'desc': 'Confluence 3.5~6. 다수 매수 시그널 수렴.'},
    'Gold_Dot':               {'icon': '🏆', 'lbl': 'GOLD DOT',       'kor': '최강 매수',         'desc': 'RSI<30 + MFI<30 + WT1<-60 + 상승 다이버전스. 추세 무관.'},
    'Green_Dot_T1':           {'icon': '🟢', 'lbl': 'BUY T1',         'kor': '강한 매수',         'desc': 'WT 과매도 교차 + RSI<30 + MFI<30 + MF<0.'},
    'Green_Dot_T2':           {'icon': '🟩', 'lbl': 'BUY T2',         'kor': '매수',             'desc': 'T1 완화. WT 과매도 + RSI 또는 MFI < 32.'},
    'Blue_Diamond':           {'icon': '🔹', 'lbl': 'BLUE DIA',       'kor': '추세 매수',         'desc': 'WT2≤0 상승교차 + HTF 강세 + 하락추세 아님.'},
    'Green_Circle':           {'icon': '✅', 'lbl': 'BUY Circle',     'kor': '과매도 반등',       'desc': 'WT 과매도 교차. Green Dot 미달.'},
    'Bull_Divergence':        {'icon': '📈', 'lbl': 'Bull Div',       'kor': '상승 다이버전스',    'desc': '가격 저점↓ vs WT 저점↑.'},
    'Hidden_Bull_Div':        {'icon': '🔀', 'lbl': 'Hidden Bull',    'kor': '히든 상승 다이버전스','desc': '가격 저점↑ vs 오실레이터 저점↓.'},
    'Squeeze_Fire_Buy':       {'icon': '💥', 'lbl': 'Squeeze BUY',    'kor': '스퀴즈 매수',       'desc': 'TTM Squeeze 해소 + 모멘텀 상방.'},
    'Volume_Climax_Buy':      {'icon': '🌊', 'lbl': 'Vol Climax BUY', 'kor': '거래량 클라이맥스 매수', 'desc': '3배 거래량 + 하락캔들 + WT과매도 → 반등 확인.'},
    'OBV_Div_Buy':            {'icon': '📊', 'lbl': 'OBV Div BUY',   'kor': 'OBV 다이버전스 매수', 'desc': 'OBV-가격 상승 다이버전스.'},
    'ADX_Momentum_Buy':       {'icon': '🚀', 'lbl': 'ADX Ignition',   'kor': 'ADX 점화',         'desc': 'ADX>20 돌파 + Plus DI > Minus DI.'},
    'Fib_Bounce_Buy':         {'icon': '📐', 'lbl': 'Fib Bounce',     'kor': '피보나치 반등',      'desc': '0.618~0.786 지지 + WT 상승교차.'},
    'Bullish_Engulfing':      {'icon': '☀️', 'lbl': 'Bull Engulf',    'kor': '상승 장악형',       'desc': '전일 하락을 감싸는 상승캔들 + WT 약세구간.'},
    'Golden_Cross':           {'icon': '✨', 'lbl': 'Golden Cross',   'kor': '골든 크로스',       'desc': '50MA > 200MA 상향돌파.'},
    'EMA_Pullback_Buy':       {'icon': '🎯', 'lbl': 'EMA Pullback',   'kor': 'EMA 눌림목 매수',   'desc': '상승추세 중 EMA 조정 후 WT 반등 + 거래량.'},
    'Momentum_Ignition_Buy':  {'icon': '🔥', 'lbl': 'Mom. Ignition',  'kor': '모멘텀 점화 매수',   'desc': '장대양봉>ATR×1.5 + 거래량>2.5x + BB 돌파.'},
    'SuperTrend_Buy':         {'icon': '📈', 'lbl': 'ST Flip Bull',   'kor': '슈퍼트렌드 강세 전환','desc': 'SuperTrend 하단선 위로 돌파.'},
    'MACD_Cross_Buy':         {'icon': '〽️', 'lbl': 'MACD Cross',    'kor': 'MACD 골든크로스',    'desc': 'MACD 시그널선 상향돌파 + 0선 하회 구간.'},
    'RSI_Divergence_Buy':     {'icon': '📉', 'lbl': 'RSI Bull Div',   'kor': 'RSI 상승 다이버전스', 'desc': '가격 저점↓ vs RSI 저점↑. WT 다이버전스와 독립 확인.'},
    'Ultra_Sell':             {'icon': '🚨', 'lbl': 'ULTRA SELL',     'kor': '울트라 매도',       'desc': 'Confluence ≤-6 또는 (≤-5 + 동시 3개).'},
    'Strong_Sell':            {'icon': '⚠️', 'lbl': 'STRONG SELL',    'kor': '스트롱 매도',       'desc': 'Confluence -6~-3.5. 다수 매도 수렴.'},
    'Blood_Diamond':          {'icon': '🩸', 'lbl': 'BLOOD DIA',      'kor': '최강 매도',         'desc': 'RSI>70 + MFI>70 + WT1>60 + 하락 다이버전스.'},
    'Red_Dot_T1':             {'icon': '🔴', 'lbl': 'SELL T1',        'kor': '강한 매도',         'desc': 'WT 과매수 하락교차 + RSI>70 + MFI>70 + MF>0.'},
    'Red_Dot_T2':             {'icon': '🟥', 'lbl': 'SELL T2',        'kor': '매도',             'desc': 'T1 완화. WT 과매수 + RSI 또는 MFI > 68.'},
    'Red_Diamond':            {'icon': '🔸', 'lbl': 'RED DIA',        'kor': '추세 매도',         'desc': 'WT2≥0 하락교차 + HTF 약세 + 상승추세 아님.'},
    'Red_Circle':             {'icon': '⛔', 'lbl': 'SELL Circle',    'kor': '과매수 하락',       'desc': 'WT 과매수 하락교차. Red Dot 미달.'},
    'Bear_Divergence':        {'icon': '📉', 'lbl': 'Bear Div',       'kor': '하락 다이버전스',    'desc': '가격 고점↑ vs WT 고점↓.'},
    'Hidden_Bear_Div':        {'icon': '🔁', 'lbl': 'Hidden Bear',    'kor': '히든 하락 다이버전스','desc': '가격 고점↓ vs 오실레이터 고점↑.'},
    'Squeeze_Fire_Sell':      {'icon': '🧨', 'lbl': 'Squeeze SELL',   'kor': '스퀴즈 매도',       'desc': 'TTM Squeeze 해소 + 모멘텀 하방.'},
    'Volume_Climax_Sell':     {'icon': '🌋', 'lbl': 'Vol Climax SELL','kor': '거래량 클라이맥스 매도','desc': '3배 거래량 + 상승캔들 + WT과매수 → 하락 확인.'},
    'OBV_Div_Sell':           {'icon': '🔻', 'lbl': 'OBV Div SELL',  'kor': 'OBV 다이버전스 매도', 'desc': 'OBV-가격 하락 다이버전스.'},
    'ADX_Momentum_Sell':      {'icon': '💨', 'lbl': 'ADX Down',       'kor': 'ADX 하락 점화',     'desc': 'ADX>20 돌파 + Minus DI > Plus DI.'},
    'Fib_Resistance_Sell':    {'icon': '🚧', 'lbl': 'Fib Resist',     'kor': '피보나치 저항',      'desc': '0.618~0.786 저항 + WT 하락교차.'},
    'Bearish_Engulfing':      {'icon': '🌑', 'lbl': 'Bear Engulf',    'kor': '하락 장악형',       'desc': '전일 상승을 감싸는 하락캔들 + WT 강세구간.'},
    'Death_Cross':            {'icon': '☠️', 'lbl': 'Death Cross',    'kor': '데드 크로스',       'desc': '50MA < 200MA 하향돌파.'},
    'SuperTrend_Sell':        {'icon': '📉', 'lbl': 'ST Flip Bear',   'kor': '슈퍼트렌드 약세 전환','desc': 'SuperTrend 상단선 아래로 하향 돌파. 쉴드 해제.'},
    'Parabolic_Top_Sell':     {'icon': '🌡️', 'lbl': 'Parabolic Top', 'kor': '포물선 천장 매도',   'desc': 'WT1>85 꺾임 + 음봉. 또는 BB+ATR×1.5 극단이격 + 음봉.'},
    'EMA_Pullback_Sell':      {'icon': '🎯', 'lbl': 'EMA PB Sell',    'kor': 'EMA 되돌림 매도',   'desc': '하락추세 중 EMA 반등 후 WT 재하락 + 거래량.'},
    'Momentum_Ignition_Sell': {'icon': '💣', 'lbl': 'Mom. Ign Sell',  'kor': '모멘텀 점화 매도',   'desc': '장대음봉>ATR×1.5 + 거래량>2.5x + BB 하단 돌파.'},
    'MACD_Cross_Sell':        {'icon': '〽️', 'lbl': 'MACD Cross',    'kor': 'MACD 데드크로스',    'desc': 'MACD 시그널선 하향돌파 + 0선 상회 구간.'},
    'RSI_Divergence_Sell':    {'icon': '📈', 'lbl': 'RSI Bear Div',   'kor': 'RSI 하락 다이버전스', 'desc': '가격 고점↑ vs RSI 고점↓. WT와 독립적 확인.'},
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
    try:
        return yf.Ticker(ticker).history(period="2y")
    except Exception:
        return pd.DataFrame()


# ──────────────────────────────────────────
# 공통 유틸
# ──────────────────────────────────────────
def _recent(series, lb=3):
    """최근 lb 봉 내 True가 있으면 True"""
    return series.rolling(window=lb + 1, min_periods=1).max().fillna(0).astype(bool)


def _cooldown(sig, bars=5):
    """동일 시그널 bars 이내 재발화 억제"""
    vals = sig.copy().astype(bool).values.copy()
    last = -bars - 1
    for i in range(len(vals)):
        if vals[i]:
            if (i - last) <= bars:
                vals[i] = False
            else:
                last = i
    return pd.Series(vals, index=sig.index)


def _vol_ok(volume, ratio=0.5, period=20):
    return volume >= volume.rolling(period, min_periods=5).mean() * ratio


# ──────────────────────────────────────────
# 지표 계산 엔진 (통합)
# ──────────────────────────────────────────
def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, min_periods=period).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, min_periods=period).mean()
    return 100 - (100 / (1 + gain / (loss + 1e-10)))


def compute_mfi(high, low, close, volume, period=14):
    tp = (high + low + close) / 3
    raw_mf = tp * volume
    d = tp.diff()
    pos = pd.Series(0.0, index=tp.index); neg = pos.copy()
    pos[d >= 0] = raw_mf[d >= 0]; neg[d < 0] = raw_mf[d < 0]
    return 100 - (100 / (1 + pos.rolling(period).sum() / (neg.rolling(period).sum() + 1e-10)))


def compute_rsi_mfi(high, low, close, volume, period=60):
    rf = compute_rsi(close, 20); mf = compute_mfi(high, low, close, volume, 20)
    rs = compute_rsi(close, period); ms = compute_mfi(high, low, close, volume, period)
    return ((rf - 50 + mf - 50) / 2) * 0.6 + ((rs - 50 + ms - 50) / 2) * 0.4


def compute_wavetrend(high, low, close, ch=9, avg=12, ma=3):
    ap = (high + low + close) / 3
    esa = ap.ewm(span=ch, adjust=False).mean()
    d = abs(ap - esa).ewm(span=ch, adjust=False).mean()
    ci = (ap - esa) / (0.015 * d + 1e-10)
    wt1 = ci.ewm(span=avg, adjust=False).mean()
    wt2 = wt1.rolling(window=ma).mean()
    up = (wt1 > wt2) & (wt1.shift(1) <= wt2.shift(1))
    dn = (wt1 < wt2) & (wt1.shift(1) >= wt2.shift(1))
    return wt1, wt2, up, dn


def compute_macd(close, fast=12, slow=26, sig=9):
    ml = close.ewm(span=fast, adjust=False).mean() - close.ewm(span=slow, adjust=False).mean()
    sl = ml.ewm(span=sig, adjust=False).mean()
    return ml, sl, ml - sl


def compute_stoch_rsi(close, rsi_len=14, stoch_len=14, k_sm=3, d_sm=3):
    rsi = compute_rsi(close, rsi_len)
    stoch = (rsi - rsi.rolling(stoch_len).min()) / (rsi.rolling(stoch_len).max() - rsi.rolling(stoch_len).min() + 1e-10) * 100
    k = stoch.rolling(k_sm).mean()
    return k, k.rolling(d_sm).mean()


def compute_vwap_osc(close, volume, period=20):
    vwap = (close * volume).rolling(period).sum() / (volume.rolling(period).sum() + 1e-10)
    return (close - vwap) / (vwap + 1e-10) * 100


def compute_adx(high, low, close, period=14):
    ph, pl, pc = high.shift(1), low.shift(1), close.shift(1)
    tr = pd.concat([high - low, (high - pc).abs(), (low - pc).abs()], axis=1).max(axis=1)
    pdm = pd.Series(np.where((high - ph) > (pl - low), np.maximum(high - ph, 0), 0), index=high.index, dtype=float)
    mdm = pd.Series(np.where((pl - low) > (high - ph), np.maximum(pl - low, 0), 0), index=high.index, dtype=float)
    atr = tr.ewm(alpha=1/period, min_periods=period).mean()
    pdi = 100 * pdm.ewm(alpha=1/period, min_periods=period).mean() / (atr + 1e-10)
    mdi = 100 * mdm.ewm(alpha=1/period, min_periods=period).mean() / (atr + 1e-10)
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi + 1e-10)
    return dx.ewm(alpha=1/period, min_periods=period).mean(), pdi, mdi


def compute_obv(close, volume):
    return (volume * np.sign(close.diff()).fillna(0)).cumsum()


def compute_atr(high, low, close, period=14):
    pc = close.shift(1)
    tr = pd.concat([high - low, (high - pc).abs(), (low - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def compute_supertrend(high, low, close, period=10, mult=3.0):
    atr = compute_atr(high, low, close, period)
    hl2 = (high + low) / 2
    up_b = (hl2 + mult * atr).values.copy()
    dn_b = (hl2 - mult * atr).values.copy()
    cl = close.values
    n = len(close)
    st_v = np.full(n, np.nan)
    dr = np.zeros(n, dtype=int)
    first = period
    if first >= n:
        return pd.Series(st_v, index=close.index), pd.Series(dr, index=close.index)
    dr[first] = 1; st_v[first] = dn_b[first]
    for i in range(first + 1, n):
        if dr[i-1] == 1:
            dn_b[i] = max(dn_b[i], dn_b[i-1]) if not np.isnan(dn_b[i-1]) else dn_b[i]
        else:
            up_b[i] = min(up_b[i], up_b[i-1]) if not np.isnan(up_b[i-1]) else up_b[i]
        if dr[i-1] == 1:
            dr[i], st_v[i] = (-1, up_b[i]) if cl[i] < dn_b[i] else (1, dn_b[i])
        else:
            dr[i], st_v[i] = (1, dn_b[i]) if cl[i] > up_b[i] else (-1, up_b[i])
    return pd.Series(st_v, index=close.index), pd.Series(dr, index=close.index)


# ──────────────────────────────────────────
# 다이버전스 탐지 (WT + RSI 통합)
# ──────────────────────────────────────────
def _find_pivots(price, half=5):
    pv = price.values; n = len(pv)
    lows, highs = [], []
    for i in range(2*half, n):
        c = i - half
        w = pv[i - 2*half: i + 1]
        if pv[c] == w.min(): lows.append((i, c))
        if pv[c] == w.max(): highs.append((i, c))
    return lows, highs


def detect_divergences(price, oscillator, lookback=60, pivot_window=5,
                        osc_oversold=None, osc_overbought=None):
    """통합 다이버전스 감지 — Regular + Hidden"""
    n = len(price)
    pv, ov = price.values, oscillator.values
    lows, highs = _find_pivots(price, pivot_window)
    min_gap = pivot_window * 2
    bull = pd.Series(False, index=price.index)
    bear = pd.Series(False, index=price.index)
    hid_bull = pd.Series(False, index=price.index)
    hid_bear = pd.Series(False, index=price.index)

    for idx in range(1, len(lows)):
        ci, pi = lows[idx]; cj, pj = lows[idx-1]
        if not (min_gap <= (pi - pj) <= lookback): continue
        if (osc_oversold is None or ov[pi] <= osc_oversold):
            if pv[pi] < pv[pj] and ov[pi] > ov[pj]:
                bull.iloc[ci] = True
        if pv[pi] > pv[pj] and ov[pi] < ov[pj]:
            hid_bull.iloc[ci] = True

    for idx in range(1, len(highs)):
        ci, pi = highs[idx]; cj, pj = highs[idx-1]
        if not (min_gap <= (pi - pj) <= lookback): continue
        if (osc_overbought is None or ov[pi] >= osc_overbought):
            if pv[pi] > pv[pj] and ov[pi] < ov[pj]:
                bear.iloc[ci] = True
        if pv[pi] < pv[pj] and ov[pi] > ov[pj]:
            hid_bear.iloc[ci] = True

    return bull, bear, hid_bull, hid_bear


# ──────────────────────────────────────────
# 패턴 / 특수 시그널 탐지 (통합)
# ──────────────────────────────────────────
def detect_keltner_channel(high, low, close, ema_len=20, atr_len=10, atr_mult=1.5):
    mid = close.ewm(span=ema_len, adjust=False).mean()
    atr = compute_atr(high, low, close, atr_len)
    return mid + atr * atr_mult, mid, mid - atr * atr_mult


def detect_ttm_squeeze(bb_up, bb_low, kc_up, kc_low, close, high, low, kc_mid):
    sq_on = (bb_up < kc_up) & (bb_low > kc_low)
    fire = (~sq_on) & sq_on.shift(1).fillna(False)
    dc_mid = (high.rolling(20).max() + low.rolling(20).min()) / 2
    mom = close - (dc_mid + kc_mid) / 2
    return sq_on, fire & (mom > 0), fire & (mom < 0)


def detect_volume_climax(close, opn, volume, wt1, vol_mult=3.0, wt_buy=-35, wt_sell=35):
    avg = volume.rolling(20).mean()
    spike = (volume > avg * vol_mult).shift(1).fillna(False)
    buy = spike & (close.shift(1) < opn.shift(1)) & (wt1.shift(1) < wt_buy) & (close > opn)
    sell = spike & (close.shift(1) > opn.shift(1)) & (wt1.shift(1) > wt_sell) & (close < opn)
    return buy, sell


def detect_engulfing(close, opn, wt1, direction='buy', wt_thresh=20):
    """매수/매도 장악형 통합"""
    body = (close - opn).abs()
    avg_body = body.rolling(20).mean()
    big = body > avg_body * 0.8
    if direction == 'buy':
        prev_bear = close.shift(1) < opn.shift(1)
        curr_bull = close > opn
        eng = prev_bear & curr_bull & (opn <= close.shift(1)) & (close >= opn.shift(1))
        return eng & big & (wt1 < -wt_thresh)
    else:
        prev_bull = close.shift(1) > opn.shift(1)
        curr_bear = close < opn
        eng = prev_bull & curr_bear & (opn >= close.shift(1)) & (close <= opn.shift(1))
        return eng & big & (wt1 > wt_thresh)


def detect_fib_level(high, low, close, wt1, wt2, direction='buy', swing_lb=60, confirm=5):
    """피보나치 반등/저항 통합"""
    sh = high.shift(confirm).rolling(swing_lb).max()
    sl = low.shift(confirm).rolling(swing_lb).min()
    if direction == 'buy':
        f618 = sh - (sh - sl) * 0.618; f786 = sh - (sh - sl) * 0.786
        near = (low <= f618 * 1.02) & (low >= f786 * 0.98)
        return near & (wt1 < -30) & (wt1 > wt2)
    else:
        f618 = sl + (sh - sl) * 0.618; f786 = sl + (sh - sl) * 0.786
        near = (high >= f618 * 0.98) & (high <= f786 * 1.02)
        return near & (wt1 > 30) & (wt1 < wt2)


def detect_ema_pullback(close, high, low, volume, ema8, ema21, atr, wt1, wt2, direction='buy'):
    """EMA 풀백 매수/매도 통합"""
    vol = _vol_ok(volume, ratio=0.5)
    if direction == 'buy':
        trend = (ema8 > ema21) & (ema21 > ema21.shift(5))
        zone_u = ema8 * (1 + atr / close * 0.15)
        zone_l = ema21 * (1 - atr / close * 0.25)
        touched = (low <= zone_u) & (low >= zone_l)
        return trend & (close > ema21) & touched & (close >= ema8) & (wt1 < 60) & (wt1 > wt1.shift(1)) & (wt1 > wt2) & vol
    else:
        trend = (ema8 < ema21) & (ema21 < ema21.shift(5))
        zone_l = ema8 * (1 - atr / close * 0.15)
        zone_u = ema21 * (1 + atr / close * 0.25)
        touched = (high >= zone_l) & (high <= zone_u)
        return trend & (close < ema21) & touched & (close <= ema8) & (wt1 > -60) & (wt1 < wt1.shift(1)) & (wt1 < wt2) & vol


def detect_momentum_ignition(close, opn, volume, bb_band, atr, ema8, ema21,
                              direction='buy', body_mult=1.5, vol_mult=2.5):
    """모멘텀 점화 매수/매도 통합"""
    body = (close - opn).abs()
    big = body > (atr * body_mult)
    huge_vol = volume > volume.rolling(20).mean() * vol_mult
    if direction == 'buy':
        return (close > opn) & big & huge_vol & (close > bb_band) & (ema8 > ema21)
    else:
        return (close < opn) & big & huge_vol & (close < bb_band) & (ema8 < ema21)


# ──────────────────────────────────────────
# Confluence / Bias / Proximity (통합)
# ──────────────────────────────────────────
def compute_confluence_score(df, decay_window=5, decay_factor=0.7):
    buy_map = {k: v['w'] for k, v in SIGNAL_REGISTRY.items() if v['dir'] == 'buy'}
    sell_map = {k: v['w'] for k, v in SIGNAL_REGISTRY.items() if v['dir'] == 'sell'}
    dk = np.array([decay_factor ** i for i in range(decay_window + 1)])
    ones = np.ones(decay_window + 1)
    s = np.zeros(len(df))
    bc = np.zeros(len(df)); sc = np.zeros(len(df))

    for smap, sign, cnt_arr in [(buy_map, 1, bc), (sell_map, -1, sc)]:
        for col, w in smap.items():
            if col not in df.columns: continue
            raw = df[col].fillna(False).astype(float).values
            s += sign * np.convolve(raw * w, dk, mode='full')[:len(raw)]
            cnt_arr += np.convolve(raw, ones, mode='full')[:len(raw)]

    wt1 = df['WT1'].values
    s += np.where(wt1 < -53, 1.0, 0) + np.where(wt1 < -60, 0.5, 0)
    s -= np.where(wt1 > 53, 1.0, 0) - np.where(wt1 > 60, -0.5, 0)

    df['Confluence_Score'] = s
    df['Ultra_Buy']  = (s >= 6.0) | ((s >= 5.0) & (bc >= 3))
    df['Ultra_Sell'] = (s <= -6.0) | ((s <= -5.0) & (sc >= 3))
    df['Strong_Buy']  = (s >= 3.5) & ~df['Ultra_Buy']
    df['Strong_Sell'] = (s <= -3.5) & ~df['Ultra_Sell']
    return s


def compute_signal_proximity(wt1, wt2, rsi, mfi, rsi_mfi, stochk, macd_hist):
    bp = pd.Series(0.0, index=wt1.index)
    sp = bp.copy()
    gap = (wt1 - wt2).abs()
    near = gap < 3.0
    conv_up = (wt1 - wt2) > (wt1.shift(1) - wt2.shift(1))
    conv_dn = (wt1 - wt2) < (wt1.shift(1) - wt2.shift(1))

    # 매수 근접도
    bp += np.where((wt1 < -40) & near, 30, 0)
    bp += np.where((wt1 < -40) & conv_up & (gap < 8), 15, 0)
    bp += np.where(wt1 < -53, 20, np.where(wt1 < -40, 10, 0))
    bp += np.where(rsi < 35, 15, np.where(rsi < 45, 5, 0))
    bp += np.where(mfi < 35, 15, np.where(mfi < 45, 5, 0))
    bp += np.where(rsi_mfi < -5, 10, np.where(rsi_mfi < 0, 5, 0))
    bp += np.where(stochk < 20, 10, np.where(stochk < 35, 5, 0))
    bp += np.where((macd_hist < 0) & (macd_hist > macd_hist.shift(1)), 5, 0)

    # 매도 근접도
    sp += np.where((wt1 > 40) & near, 30, 0)
    sp += np.where((wt1 > 40) & conv_dn & (gap < 8), 15, 0)
    sp += np.where(wt1 > 53, 20, np.where(wt1 > 40, 10, 0))
    sp += np.where(rsi > 65, 15, np.where(rsi > 55, 5, 0))
    sp += np.where(mfi > 65, 15, np.where(mfi > 55, 5, 0))
    sp += np.where(rsi_mfi > 5, 10, np.where(rsi_mfi > 0, 5, 0))
    sp += np.where(stochk > 80, 10, np.where(stochk > 65, 5, 0))
    sp += np.where((macd_hist > 0) & (macd_hist < macd_hist.shift(1)), 5, 0)

    bp = bp.clip(upper=100); sp = sp.clip(upper=100)
    net = bp - sp
    return (
        pd.Series(np.where(net >= 0, bp, bp * 0.4), index=wt1.index),
        pd.Series(np.where(net <= 0, sp, sp * 0.4), index=wt1.index),
    )


def compute_bias_score(meta, htf1_bull, htf2_bull):
    sc = 0.0
    # WT
    wt = meta['wt1']
    for thresh, val in [(-60, 3), (-53, 2), (0, 1)]:
        if wt <= thresh: sc += val; break
    else:
        for thresh, val in [(60, -3), (53, -2), (0, -1)]:
            if wt >= thresh: sc += val; break
    # RSI, MFI
    for v in [meta['rsi'], meta['mfi']]:
        if v < 30: sc += 2
        elif v < 45: sc += 1
        elif v > 70: sc -= 2
        elif v > 55: sc -= 1
    # Money Flow
    mf = meta['mf_area']
    if mf < -5: sc += 2
    elif mf < 0: sc += 1
    elif mf > 5: sc -= 2
    elif mf > 0: sc -= 1
    # StochK
    stk = meta.get('stochk', 50)
    if stk < 20: sc += 1.5
    elif stk < 35: sc += 0.5
    elif stk > 80: sc -= 1.5
    elif stk > 65: sc -= 0.5
    # MACD
    mh = meta.get('macd_hist', 0)
    sc += (-0.5 if mh > 0 else 0.5)
    # HTF
    sc += (1 if htf1_bull else -1) + (1.5 if htf2_bull else -1.5)

    if sc >= 8:    return 'STRONG BUY', sc
    elif sc >= 3:  return 'BUY', sc
    elif sc >= -3: return 'NEUTRAL', sc
    elif sc >= -8: return 'SELL', sc
    else:          return 'STRONG SELL', sc


def compute_signal_stats(df, sig_col, fwd_days=(5, 10, 20), min_n=5):
    if sig_col not in df.columns: return None
    mask = df[sig_col].fillna(False).values.astype(bool)
    count = int(mask.sum())
    if count < min_n: return None
    cl = df['Close'].values
    stats = {'count': count}
    for n in fwd_days:
        if n >= len(cl):
            stats[f'{n}d_avg'] = stats[f'{n}d_winrate'] = stats[f'{n}d_median'] = None; continue
        fwd = np.full(len(cl), np.nan)
        fwd[:len(cl)-n] = (cl[n:] - cl[:len(cl)-n]) / cl[:len(cl)-n] * 100
        valid = fwd[mask]; valid = valid[~np.isnan(valid)]
        if len(valid) >= min_n:
            stats[f'{n}d_avg'] = float(np.mean(valid))
            stats[f'{n}d_winrate'] = float(np.sum(valid > 0) / len(valid) * 100)
            stats[f'{n}d_median'] = float(np.median(valid))
        else:
            stats[f'{n}d_avg'] = stats[f'{n}d_winrate'] = stats[f'{n}d_median'] = None
    return stats


def compute_all_signal_stats(df):
    targets = {k: v['dir'] for k, v in SIGNAL_REGISTRY.items()}
    targets.update({'Ultra_Buy': 'buy', 'Strong_Buy': 'buy', 'Ultra_Sell': 'sell', 'Strong_Sell': 'sell'})
    results = {}
    for sig, d in targets.items():
        r = compute_signal_stats(df, sig)
        if r and r['count'] > 0:
            results[sig] = {**r, 'direction': d}
    return results


# ──────────────────────────────────────────
# S/R 레벨
# ──────────────────────────────────────────
def compute_support_resistance(df, lookback=60):
    recent = df.tail(lookback)
    price_now = df['Close'].iloc[-1]
    levels = []

    for name in ['MA20', 'MA50', 'MA100', 'MA200']:
        if name in df.columns:
            v = df[name].iloc[-1]
            if pd.notna(v) and v > 0:
                levels.append({'price': v, 'type': 'MA', 'name': name})
    for name in ['EMA8', 'EMA21']:
        if name in df.columns:
            v = df[name].iloc[-1]
            if pd.notna(v) and v > 0:
                levels.append({'price': v, 'type': 'EMA', 'name': name})
    if 'BB_Up' in df.columns:
        levels += [{'price': df['BB_Up'].iloc[-1], 'type': 'BB', 'name': 'BB Upper'},
                   {'price': df['BB_Low'].iloc[-1], 'type': 'BB', 'name': 'BB Lower'}]
    if 'SuperTrend' in df.columns:
        v = df['SuperTrend'].iloc[-1]
        if pd.notna(v):
            levels.append({'price': v, 'type': 'ST', 'name': 'SuperTrend'})

    sh = recent['High'].max(); sl = recent['Low'].min(); rng = sh - sl
    if rng > 0:
        for fib, nm in [(0.236, '23.6%'), (0.382, '38.2%'), (0.5, '50%'), (0.618, '61.8%'), (0.786, '78.6%')]:
            levels.append({'price': sh - rng * fib, 'type': 'FIB', 'name': f'Fib {nm}'})

    # 피봇 클러스터
    buckets = {}
    for _, r in recent.iterrows():
        for p in [r['High'], r['Low']]:
            b = round(p, 2)
            buckets[b] = buckets.get(b, 0) + 1
    for p, c in sorted(buckets.items(), key=lambda x: x[1], reverse=True)[:5]:
        if c >= 2:
            levels.append({'price': p, 'type': 'PIVOT', 'name': f'Pivot ({c}x)'})

    supports = sorted([l for l in levels if l['price'] < price_now * 0.999], key=lambda x: x['price'], reverse=True)[:5]
    resists = sorted([l for l in levels if l['price'] > price_now * 1.001], key=lambda x: x['price'])[:5]
    return supports, resists


# ──────────────────────────────────────────
# 🎯 메인 분석 엔진 (V3.1)
# ──────────────────────────────────────────
def analyze_ticker(ticker, chart_period_days=252):
    try:
        df = get_yf_history(ticker)
        if df.empty:
            return None, "최근 주가 데이터 없음", None

        # ── 이동평균 ──
        for ma in [5, 20, 50, 100, 125, 200]:
            df[f'MA{ma}'] = df['Close'].rolling(ma).mean()
        df['EMA8'] = df['Close'].ewm(span=8, adjust=False).mean()
        df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()
        df['BB_Mid'] = df['MA20']
        std20 = df['Close'].rolling(20).std()
        df['BB_Up'] = df['BB_Mid'] + std20 * 2
        df['BB_Low'] = df['BB_Mid'] - std20 * 2
        df['ATR'] = compute_atr(df['High'], df['Low'], df['Close'])

        # ── 오실레이터 ──
        wt1, wt2, wt_up, wt_dn = compute_wavetrend(df['High'], df['Low'], df['Close'])
        df['WT1'], df['WT2'] = wt1, wt2
        df['RSI'] = compute_rsi(df['Close'], 14)
        df['StochK'], df['StochD'] = compute_stoch_rsi(df['Close'])
        df['MFI'] = compute_mfi(df['High'], df['Low'], df['Close'], df['Volume'], 14)
        df['RSI_MFI'] = compute_rsi_mfi(df['High'], df['Low'], df['Close'], df['Volume'], 60)
        df['VWAP_Osc'] = compute_vwap_osc(df['Close'], df['Volume'])
        df['ADX'], df['Plus_DI'], df['Minus_DI'] = compute_adx(df['High'], df['Low'], df['Close'])
        df['MACD'], df['MACD_Signal'], df['MACD_Hist'] = compute_macd(df['Close'])
        df['OBV'] = compute_obv(df['Close'], df['Volume'])
        df['SuperTrend'], df['ST_Direction'] = compute_supertrend(df['High'], df['Low'], df['Close'])

        # ── 추세 & 쉴드 ──
        OB1, OB2, OS1, OS2 = 53, 60, -53, -60
        htf1_bull = (df['EMA8'] > df['EMA21']) & (df['EMA21'] > df['EMA21'].shift(5))
        htf2_bull = (df['Close'] > df['MA50']) & (df['MA50'] > df['MA50'].shift(10))
        above_ma50 = df['Close'] > df['MA50']; below_ma50 = ~above_ma50
        above_ma200 = df['Close'] > df['MA200']; below_ma200 = ~above_ma200

        strong_bull = (df['ADX'] > 25) & (df['Plus_DI'] > df['Minus_DI']) & above_ma50
        strong_bear = (df['ADX'] > 25) & (df['Minus_DI'] > df['Plus_DI']) & below_ma50
        extreme_bull = strong_bull & above_ma200 & (df['MA50'] > df['MA50'].shift(5))
        extreme_bear = strong_bear & below_ma200 & (df['MA50'] < df['MA50'].shift(5))

        parabolic = (
            ((wt1 > 85) & (wt1 < wt1.shift(1)) & (df['Close'] < df['Open']) & (df['Close'] < df['Close'].shift(1)))
            | ((df['Close'] > df['BB_Up'] + df['ATR'] * 1.5) & (df['Close'] < df['Open']))
        )
        st_min_bar = 12
        st_flip_bear = (df['ST_Direction'] == -1) & (df['ST_Direction'].shift(1) == 1)
        st_flip_bear.iloc[:st_min_bar] = False
        st_bear_override = _recent(st_flip_bear, lb=3)

        sell_shield = strong_bull & ~parabolic & ~st_bear_override
        sell_shield_ext = extreme_bull & ~parabolic & ~st_bear_override

        # ── 기본 변수 ──
        wt_up2 = _recent(wt_up, lb=2); wt_dn2 = _recent(wt_dn, lb=2)
        wt_up3 = _recent(wt_up, lb=3); wt_dn3 = _recent(wt_dn, lb=3)
        vol = _vol_ok(df['Volume'])
        mf_bull = df['RSI_MFI'] > -10; mf_bear = df['RSI_MFI'] < 10

        # ══════════ 시그널 생성 ══════════

        # Green / Red Dots
        df['Green_Dot_T1'] = wt_up2 & (wt1 <= OS1) & (df['RSI'] < 30) & (df['MFI'] < 30) & (df['RSI_MFI'] < 0) & ~extreme_bear & vol
        df['Green_Dot_T2'] = wt_up2 & (wt1 <= OS1) & ((df['RSI'] < 32) | (df['MFI'] < 32)) & ~df['Green_Dot_T1'] & ~strong_bear & vol
        df['Green_Dot'] = df['Green_Dot_T1'] | df['Green_Dot_T2']

        df['Red_Dot_T1'] = wt_dn2 & (wt1 >= OB1) & (df['RSI'] > 70) & (df['MFI'] > 70) & (df['RSI_MFI'] > 0) & ~sell_shield_ext & vol
        df['Red_Dot_T2'] = wt_dn2 & (wt1 >= OB1) & ((df['RSI'] > 68) | (df['MFI'] > 68)) & ~df['Red_Dot_T1'] & ~sell_shield & vol
        df['Red_Dot'] = df['Red_Dot_T1'] | df['Red_Dot_T2']

        # Diamond / Circle
        df['Blue_Diamond'] = (wt2 <= 0) & wt_up2 & (htf1_bull | htf2_bull) & ~strong_bear & mf_bull & vol
        df['Red_Diamond'] = (wt2 >= 0) & wt_dn2 & (~htf1_bull | ~htf2_bull) & ~sell_shield & mf_bear & vol
        df['Green_Circle'] = wt_up2 & (wt1 <= OS1) & ~df['Green_Dot'] & ~strong_bear & vol
        df['Red_Circle'] = wt_dn2 & (wt1 >= OB1) & ~df['Red_Dot'] & ~sell_shield & vol

        # WT 다이버전스
        bull_d, bear_d, hid_bull, hid_bear = detect_divergences(df['Close'], wt1, 60, 5, OS1, OB1)
        bull_d3 = _recent(bull_d, lb=3); bear_d3 = _recent(bear_d, lb=3)

        # ★ V3.1 NEW: RSI 다이버전스
        rsi_bull_d, rsi_bear_d, _, _ = detect_divergences(df['Close'], df['RSI'], 60, 5, 35, 65)
        df['RSI_Divergence_Buy'] = _cooldown(rsi_bull_d & (wt1 < -10) & ~strong_bear & vol, bars=10)
        df['RSI_Divergence_Sell'] = _cooldown(rsi_bear_d & (wt1 > 10) & ~sell_shield & vol, bars=10)

        # Gold / Blood (FIX: T2도 Gold_Dot 제외)
        df['Gold_Dot'] = df['Green_Dot_T1'] & (wt1 <= OS2) & bull_d3
        df['Green_Dot_T2'] = df['Green_Dot_T2'] & ~df['Gold_Dot']  # ★ FIX

        df['Bull_Divergence'] = bull_d & wt_up3 & ~df['Green_Dot'] & ~df['Gold_Dot'] & ~strong_bear & vol
        df['Bear_Divergence'] = bear_d & wt_dn3 & ~df['Red_Dot'] & ~sell_shield & vol
        df['Hidden_Bull_Div'] = hid_bull & (wt1 < 0) & htf2_bull & ~extreme_bear
        df['Hidden_Bear_Div'] = hid_bear & (wt1 > 0) & ~htf2_bull & ~sell_shield_ext

        df['Blood_Diamond'] = df['Red_Dot_T1'] & (wt1 >= OB2) & bear_d3

        # TTM Squeeze
        kc_u, kc_mid, kc_l = detect_keltner_channel(df['High'], df['Low'], df['Close'])
        sq_on, sq_fb, sq_fs = detect_ttm_squeeze(df['BB_Up'], df['BB_Low'], kc_u, kc_l, df['Close'], df['High'], df['Low'], kc_mid)
        df['Squeeze_On'] = sq_on
        df['Squeeze_Fire_Buy'] = sq_fb & ~strong_bear & vol
        df['Squeeze_Fire_Sell'] = sq_fs & ~sell_shield & vol

        # Volume Climax
        df['Volume_Climax_Buy'], df['Volume_Climax_Sell'] = detect_volume_climax(df['Close'], df['Open'], df['Volume'], wt1)

        # OBV Divergence
        obv_bull, obv_bear, _, _ = detect_divergences(df['Close'], df['OBV'], 60, 5)
        df['OBV_Div_Buy'] = obv_bull & (wt1 < -20) & ~extreme_bear
        df['OBV_Div_Sell'] = obv_bear & (wt1 > 20) & ~sell_shield_ext

        # ADX Momentum (2봉 윈도우)
        adx_cross = _recent((df['ADX'] > 20) & (df['ADX'].shift(1) <= 20), lb=2)
        df['ADX_Momentum_Buy'] = adx_cross & (df['Plus_DI'] > df['Minus_DI']) & (wt1 > wt2) & vol
        df['ADX_Momentum_Sell'] = adx_cross & (df['Minus_DI'] > df['Plus_DI']) & (wt1 < wt2) & vol

        # Fibonacci
        df['Fib_Bounce_Buy'] = detect_fib_level(df['High'], df['Low'], df['Close'], wt1, wt2, 'buy') & ~strong_bear & vol
        df['Fib_Resistance_Sell'] = detect_fib_level(df['High'], df['Low'], df['Close'], wt1, wt2, 'sell') & ~sell_shield & vol

        # Engulfing (통합 함수)
        df['Bullish_Engulfing'] = detect_engulfing(df['Close'], df['Open'], wt1, 'buy') & ~strong_bear & vol
        df['Bearish_Engulfing'] = detect_engulfing(df['Close'], df['Open'], wt1, 'sell') & ~sell_shield & vol

        # MA Cross
        gc = (df['MA50'] > df['MA200']) & (df['MA50'].shift(1) <= df['MA200'].shift(1))
        dc = (df['MA50'] < df['MA200']) & (df['MA50'].shift(1) >= df['MA200'].shift(1))
        df['Golden_Cross'], df['Death_Cross'] = gc, dc

        # MACD Cross (★ FIX: 히스토그램 방향 확인 추가)
        macd_buy = (df['MACD'] > df['MACD_Signal']) & (df['MACD'].shift(1) <= df['MACD_Signal'].shift(1)) & (df['MACD'] < 0)
        macd_sell = (df['MACD'] < df['MACD_Signal']) & (df['MACD'].shift(1) >= df['MACD_Signal'].shift(1)) & (df['MACD'] > 0)
        # ★ 추가 필터: 히스토그램 연속 3봉 방향 전환 확인
        hist_rising = (df['MACD_Hist'] > df['MACD_Hist'].shift(1)) & (df['MACD_Hist'].shift(1) > df['MACD_Hist'].shift(2))
        hist_falling = (df['MACD_Hist'] < df['MACD_Hist'].shift(1)) & (df['MACD_Hist'].shift(1) < df['MACD_Hist'].shift(2))
        df['MACD_Cross_Buy'] = _cooldown(macd_buy & _recent(hist_rising, lb=2) & ~strong_bear & vol, bars=7)
        df['MACD_Cross_Sell'] = _cooldown(macd_sell & _recent(hist_falling, lb=2) & ~sell_shield & vol, bars=7)

        # EMA Pullback (통합)
        df['EMA_Pullback_Buy'] = _cooldown(detect_ema_pullback(df['Close'], df['High'], df['Low'], df['Volume'],
                                                                 df['EMA8'], df['EMA21'], df['ATR'], wt1, wt2, 'buy'), bars=7)
        df['EMA_Pullback_Sell'] = _cooldown(detect_ema_pullback(df['Close'], df['High'], df['Low'], df['Volume'],
                                                                  df['EMA8'], df['EMA21'], df['ATR'], wt1, wt2, 'sell'), bars=7)

        # Momentum Ignition (통합)
        df['Momentum_Ignition_Buy'] = _cooldown(detect_momentum_ignition(
            df['Close'], df['Open'], df['Volume'], df['BB_Up'], df['ATR'], df['EMA8'], df['EMA21'], 'buy'), bars=10)
        df['Momentum_Ignition_Sell'] = _cooldown(detect_momentum_ignition(
            df['Close'], df['Open'], df['Volume'], df['BB_Low'], df['ATR'], df['EMA8'], df['EMA21'], 'sell'), bars=10)

        # SuperTrend 전환
        st_flip_bull = (df['ST_Direction'] == 1) & (df['ST_Direction'].shift(1) == -1)
        st_flip_bull.iloc[:st_min_bar] = False
        df['SuperTrend_Buy'] = st_flip_bull
        df['SuperTrend_Sell'] = st_flip_bear

        # Parabolic Top (★ FIX: 중복 계산 제거 — parabolic 변수 재사용)
        df['Parabolic_Top_Sell'] = _cooldown(
            parabolic & ((wt_dn | wt_dn3) | ((df['Close'] < df['Open']) & (df['Close'] < df['Close'].shift(1)))),
            bars=5
        )

        # ── 쿨다운 일괄 ──
        for sig, cd in [('Squeeze_Fire_Buy', 5), ('Squeeze_Fire_Sell', 5),
                         ('Bullish_Engulfing', 5), ('Bearish_Engulfing', 5),
                         ('Fib_Bounce_Buy', 7), ('Fib_Resistance_Sell', 7),
                         ('ADX_Momentum_Buy', 10), ('ADX_Momentum_Sell', 10)]:
            if sig in df.columns:
                df[sig] = _cooldown(df[sig], bars=cd)

        # ── Confluence ──
        compute_confluence_score(df)
        bp, sp = compute_signal_proximity(wt1, wt2, df['RSI'], df['MFI'], df['RSI_MFI'], df['StochK'], df['MACD_Hist'])
        df['Buy_Proximity'], df['Sell_Proximity'] = bp, sp
        df['Strong_Bull'] = strong_bull; df['Strong_Bear'] = strong_bear
        df['Sell_Shield_Overridden'] = parabolic | st_bear_override

        # ══════════ 차트 구성 ══════════
        df_valid = df.dropna(subset=['WT1', 'WT2'])
        dc = df_valid.tail(chart_period_days).copy()
        if dc.empty:
            return None, "차트 데이터 부족", None

        latest = dc.iloc[-1]
        prev = dc.iloc[-2] if len(dc) >= 2 else latest
        p_chg = latest['Close'] - prev['Close']
        p_pct = (p_chg / prev['Close']) * 100

        # Stats, S/R, Signals
        all_stats = compute_all_signal_stats(df_valid)
        supports, resists = compute_support_resistance(dc)

        sig_checks = [(k, v['icon'], v['label'], v['dir']) for k, v in ALL_CHART_SIGNALS.items()]
        recent_sigs = []
        for ir, row in dc.tail(30).iterrows():
            ds = ir.strftime('%m/%d')
            for col, icon, lbl, side in sig_checks:
                if row.get(col, False):
                    recent_sigs.append((icon, lbl, ds, side))

        m4b = {'wt1': float(latest['WT1']), 'rsi': float(latest['RSI']),
               'mfi': float(latest['MFI']), 'mf_area': float(latest['RSI_MFI']),
               'stochk': float(latest['StochK']), 'macd_hist': float(latest['MACD_Hist'])}
        bias, bscore = compute_bias_score(m4b, bool(htf1_bull.iloc[-1]), bool(htf2_bull.iloc[-1]))
        conf_now = float(dc['Confluence_Score'].iloc[-1])

        if latest.get('Strong_Bull', False):   trend_regime = 'STRONG BULL 🟢'
        elif latest.get('Strong_Bear', False):  trend_regime = 'STRONG BEAR 🔴'
        else:                                    trend_regime = 'NEUTRAL ⚪'

        shield_status = ''
        if parabolic.iloc[-1]:               shield_status = '🌡️ PARABOLIC OVERRIDE'
        elif st_bear_override.iloc[-1]:      shield_status = '📉 ST BEAR OVERRIDE'

        meta = {
            'ticker': ticker.upper(), 'price': latest['Close'],
            'price_change': p_chg, 'price_change_pct': p_pct,
            'volume': latest['Volume'],
            'avg_volume': dc['Volume'].rolling(20).mean().iloc[-1],
            'wt1': float(latest['WT1']), 'wt2': float(latest['WT2']),
            'rsi': float(latest['RSI']), 'mfi': float(latest['MFI']),
            'stochk': float(latest['StochK']), 'stochd': float(latest['StochD']),
            'vwap_osc': float(latest['VWAP_Osc']), 'mf_area': float(latest['RSI_MFI']),
            'atr': float(latest['ATR']),
            'atr_pct': float(latest['ATR']) / float(latest['Close']) * 100,
            'adx': float(latest['ADX']),
            'plus_di': float(latest['Plus_DI']), 'minus_di': float(latest['Minus_DI']),
            'macd': float(latest['MACD']), 'macd_signal': float(latest['MACD_Signal']),
            'macd_hist': float(latest['MACD_Hist']),
            'overall_bias': bias, 'bias_score': bscore, 'confluence_score': conf_now,
            'recent_signals': recent_sigs, 'all_signal_stats': all_stats,
            'last_date': dc.index[-1].strftime('%Y-%m-%d'),
            'buy_proximity': float(latest['Buy_Proximity']),
            'sell_proximity': float(latest['Sell_Proximity']),
            'squeeze_on': bool(latest.get('Squeeze_On', False)),
            'trend_regime': trend_regime, 'shield_status': shield_status,
            'supertrend_dir': int(latest.get('ST_Direction', 0)),
            'ema8': float(latest.get('EMA8', 0)), 'ema21': float(latest.get('EMA21', 0)),
            'supports': supports, 'resistances': resists,
        }

        # ═══ 차트 생성 ═══
        fig = make_subplots(
            rows=5, cols=1, shared_xaxes=True, vertical_spacing=0.02,
            row_heights=[0.40, 0.10, 0.22, 0.14, 0.14],
            subplot_titles=("", "", "WaveTrend Oscillator", "MACD / Money Flow", "Confluence Score"),
        )

        # Row 1: 캔들 + MA + BB + SuperTrend + S/R + 시그널
        fig.add_trace(go.Candlestick(
            x=dc.index, open=dc['Open'], high=dc['High'], low=dc['Low'], close=dc['Close'],
            name="가격", increasing_line_color='#26a69a', decreasing_line_color='#ef5350',
        ), row=1, col=1)

        ma_colors = {5: "#ff9900", 20: '#f1c40f', 50: '#e74c3c', 100: '#9b59b6', 125: '#3498db', 200: '#2ecc71'}
        for m, c in ma_colors.items():
            fig.add_trace(go.Scatter(x=dc.index, y=dc[f'MA{m}'], line=dict(color=c, width=1.2), name=f'{m}일선'), row=1, col=1)

        fig.add_trace(go.Scatter(x=dc.index, y=dc['EMA8'], line=dict(color='#00FFFF', width=1.5, dash='dot'), name='EMA 8'), row=1, col=1)
        fig.add_trace(go.Scatter(x=dc.index, y=dc['EMA21'], line=dict(color='#FF69B4', width=1.5, dash='dot'), name='EMA 21'), row=1, col=1)

        for mask_cond, color, name in [
            (dc['ST_Direction'] == 1, '#00E676', 'SuperTrend ▲'),
            (dc['ST_Direction'] == -1, '#FF1744', 'SuperTrend ▼'),
        ]:
            fig.add_trace(go.Scatter(x=dc.index, y=dc['SuperTrend'].where(mask_cond),
                line=dict(color=color, width=2), name=name, connectgaps=False), row=1, col=1)

        fig.add_trace(go.Scatter(x=dc.index, y=dc['BB_Up'], line=dict(color='gray', width=1, dash='dot'), name='BB 상단'), row=1, col=1)
        fig.add_trace(go.Scatter(x=dc.index, y=dc['BB_Low'], line=dict(color='gray', width=1, dash='dot'), name='BB 하단',
                                 fill='tonexty', fillcolor='rgba(128,128,128,0.1)'), row=1, col=1)

        # S/R 수평선
        for s in supports[:3]:
            fig.add_hline(y=s['price'], line_dash='dash', line_color='#00E676', line_width=0.8,
                          annotation_text=f"S: ${s['price']:.2f}", annotation_font_size=8,
                          annotation_font_color='#00E676', annotation_position='bottom left', row=1, col=1)
        for r in resists[:3]:
            fig.add_hline(y=r['price'], line_dash='dash', line_color='#FF1744', line_width=0.8,
                          annotation_text=f"R: ${r['price']:.2f}", annotation_font_size=8,
                          annotation_font_color='#FF1744', annotation_position='top left', row=1, col=1)

        # 쉴드 오버라이드 구간
        ov = dc.get('Sell_Shield_Overridden', pd.Series(False, index=dc.index))
        od = ov.astype(int).diff().fillna(0)
        os_list = dc.index[od == 1].tolist()
        oe_list = dc.index[od == -1].tolist()
        if len(ov) > 0 and ov.iloc[0]: os_list.insert(0, dc.index[0])
        if len(ov) > 0 and ov.iloc[-1]: oe_list.append(dc.index[-1])
        for s0, e0 in zip(os_list, oe_list):
            fig.add_vrect(x0=s0, x1=e0, fillcolor="rgba(255,0,0,0.04)", line_width=0, row=1, col=1,
                          annotation_text="🔓Shield OFF", annotation_position="top left",
                          annotation_font_size=8, annotation_font_color="#FF4444")

        # 시그널 마커
        def _atr_at(sig_df):
            return dc.loc[sig_df.index, 'ATR'].fillna(dc['ATR'].median())

        # ★ FIX: 상위 시그널 제외 로직 통합
        exclusion_map = {
            'Green_Dot_T1': ['Gold_Dot'],
            'Green_Dot_T2': ['Gold_Dot', 'Green_Dot_T1'],
            'Ultra_Buy': ['Gold_Dot'],
            'Ultra_Sell': ['Blood_Diamond'],
            'Green_Circle': ['Green_Dot', 'Gold_Dot'],
            'Red_Circle': ['Red_Dot', 'Blood_Diamond'],
        }

        for cn, cfg in ALL_CHART_SIGNALS.items():
            if cn not in dc.columns: continue
            mask = dc[cn].copy()
            for excl in exclusion_map.get(cn, []):
                if excl in dc.columns:
                    mask = mask & ~dc[excl]
            sig = dc[mask]
            if sig.empty: continue
            yv = sig[cfg['base']] + _atr_at(sig) * cfg['atr_m']
            lw = 2 if cfg['sz'] >= 16 else (1.5 if cfg['sz'] >= 13 else 1)
            fig.add_trace(go.Scatter(
                x=sig.index, y=yv, mode='markers',
                marker=dict(symbol=cfg['sym'], size=cfg['sz'], color=cfg['clr'],
                            line=dict(width=lw, color='white' if 'open' not in cfg['sym'] else cfg['clr'])),
                name=f"{cfg['icon']} {cfg['label']}",
            ), row=1, col=1)

        # Row 2: Volume
        br = dc['Close'] < dc['Open']
        fig.add_trace(go.Bar(x=dc.index, y=dc['Volume'],
                             marker_color=np.where(br, '#ef5350', '#26a69a').tolist(),
                             name="거래량", opacity=0.7), row=2, col=1)
        vcm = dc.get('Volume_Climax_Buy', pd.Series(False, index=dc.index)) | dc.get('Volume_Climax_Sell', pd.Series(False, index=dc.index))
        vcd = dc[vcm]
        if not vcd.empty:
            fig.add_trace(go.Bar(x=vcd.index, y=vcd['Volume'], marker_color='#FFD700', name="Vol Climax", opacity=0.9), row=2, col=1)

        # Row 3: WaveTrend
        fig.add_trace(go.Scatter(x=dc.index, y=dc['WT1'], line=dict(color='#00E676', width=2), name="WT1"), row=3, col=1)
        fig.add_trace(go.Scatter(x=dc.index, y=dc['WT2'], line=dict(color='#FF1744', width=1.5, dash='dot'), name="WT2"), row=3, col=1)
        wd = dc['WT1'] - dc['WT2']
        fig.add_trace(go.Bar(x=dc.index, y=wd, marker_color=np.where(wd >= 0, '#00E676', '#FF1744').tolist(),
                             name="WT Hist", opacity=0.3), row=3, col=1)

        # WT 시그널 마커
        for mask_col, clr in [
            (dc['Green_Circle'] | dc['Green_Dot'] | dc['Gold_Dot'], '#00E676'),
            (dc['Red_Circle'] | dc['Red_Dot'], '#FF1744'),
        ]:
            pts = dc[mask_col]
            if not pts.empty:
                fig.add_trace(go.Scatter(x=pts.index, y=pts['WT1'], mode='markers',
                    marker=dict(symbol='circle', size=10, color=clr, line=dict(width=1, color='white')),
                    showlegend=False), row=3, col=1)

        for lv, c, d in [(OB2, '#ff3333', 'dash'), (OB1, '#ff3333', 'solid'),
                          (0, 'gray', 'dot'), (OS1, '#00bfff', 'solid'), (OS2, '#00bfff', 'dash')]:
            fig.add_hline(y=lv, line_dash=d, line_color=c, line_width=1, row=3, col=1)

        wmx = max(float(dc['WT1'].max()), 100) + 10
        wmn = min(float(dc['WT1'].min()), -100) - 10
        fig.add_hrect(y0=OB1, y1=wmx, fillcolor="rgba(255,23,68,0.08)", line_width=0, row=3, col=1)
        fig.add_hrect(y0=wmn, y1=OS1, fillcolor="rgba(0,191,255,0.08)", line_width=0, row=3, col=1)

        if 'Squeeze_On' in dc.columns:
            sq = dc['Squeeze_On']
            sd = sq.astype(int).diff().fillna(0)
            ss = dc.index[sd == 1].tolist(); se = dc.index[sd == -1].tolist()
            if sq.iloc[0]: ss.insert(0, dc.index[0])
            if sq.iloc[-1]: se.append(dc.index[-1])
            for s0, e0 in zip(ss, se):
                fig.add_vrect(x0=s0, x1=e0, fillcolor="rgba(255,255,0,0.05)", line_width=0, row=3, col=1)

        # Row 4: MACD
        mh = dc['MACD_Hist']
        fig.add_trace(go.Bar(x=dc.index, y=mh, marker_color=np.where(mh >= 0, '#26a69a', '#ef5350').tolist(),
                             name="MACD Hist", opacity=0.5), row=4, col=1)
        fig.add_trace(go.Scatter(x=dc.index, y=dc['MACD'], line=dict(color='#2196F3', width=1.5), name="MACD"), row=4, col=1)
        fig.add_trace(go.Scatter(x=dc.index, y=dc['MACD_Signal'], line=dict(color='#FF9800', width=1, dash='dot'), name="Signal"), row=4, col=1)
        fig.add_hline(y=0, line_dash="solid", line_color="gray", line_width=1, row=4, col=1)

        # Row 5: Confluence
        conf = dc['Confluence_Score']
        fig.add_trace(go.Bar(x=dc.index, y=conf,
                             marker_color=np.where(conf >= 3.5, '#00E676', np.where(conf <= -3.5, '#FF1744', '#FFC107')).tolist(),
                             name="Confluence", opacity=0.8), row=5, col=1)
        for lv, c, d in [(6, '#00E676', 'dash'), (-6, '#FF1744', 'dash'),
                          (3.5, '#00E676', 'dot'), (-3.5, '#FF1744', 'dot'), (0, 'gray', 'solid')]:
            fig.add_hline(y=lv, line_dash=d, line_color=c, line_width=1 if d == 'solid' else 0.8, row=5, col=1)

        shield_title = f" | {shield_status}" if shield_status else ""
        fig.update_layout(
            title=dict(text=f"📊 {ticker.upper()} | 💎 Market Cipher B+ V3.1 | {trend_regime}{shield_title}",
                       font=dict(size=14, color='#FAFAFA')),
            yaxis_title="USD", yaxis2_title="Vol", yaxis3_title="WT", yaxis4_title="MACD", yaxis5_title="Conf",
            template="plotly_dark", margin=dict(l=0, r=0, t=50, b=0), height=1000, showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
                        font=dict(size=9, color='#AAAAAA'), bgcolor='rgba(0,0,0,0)'),
        )
        fig.update(layout_xaxis_rangeslider_visible=False)
        for ann in fig['layout']['annotations']:
            ann['font'] = dict(size=11, color='#888888')

        # ═══ 프롬프트 텍스트 (V3.1) ═══
        rd10 = dc.tail(10)
        ohlcv = "\n".join([f"{d.strftime('%Y-%m-%d')}: O={r['Open']:.2f} H={r['High']:.2f} L={r['Low']:.2f} C={r['Close']:.2f} V={r['Volume']:.0f}"
                           for d, r in rd10.iterrows()])
        rd60 = dc.tail(60)
        prices60 = ", ".join([f"'{d.strftime('%Y-%m-%d')}:{r['Close']:.2f}'" for d, r in rd60.iterrows()])

        all_sig_cols = [(k, f"{v['icon']} {v['label']}") for k, v in ALL_CHART_SIGNALS.items()]
        sl = []
        for ir, row in dc.tail(30).iterrows():
            dd = ir.strftime('%Y-%m-%d')
            for c, l in all_sig_cols:
                if row.get(c, False): sl.append(f"{l} {dd}")
        sig_text = "\n".join(sl) if sl else "최근 30일 내 주요 시그널 없음"

        bp_v = float(latest['Buy_Proximity']); sp_v = float(latest['Sell_Proximity'])
        prox_text = f"Buy Proximity={bp_v:.0f}%, Sell Proximity={sp_v:.0f}%"
        if bp_v >= 60: prox_text += " ⚠️ 매수 시그널 임박!"
        if sp_v >= 60: prox_text += " ⚠️ 매도 시그널 임박!"
        sq_text = "Squeeze ON (변동성 응축 → 폭발 임박)" if latest.get('Squeeze_On', False) else "Squeeze OFF"
        st_dir_text = "BULL ▲" if latest.get('ST_Direction', 0) == 1 else "BEAR ▼"

        sr_parts = []
        if supports: sr_parts.append("지지선: " + ", ".join([f"${s['price']:.2f}({s['name']})" for s in supports[:4]]))
        if resists: sr_parts.append("저항선: " + ", ".join([f"${r['price']:.2f}({r['name']})" for r in resists[:4]]))
        sr_text = "\n".join(sr_parts) if sr_parts else "S/R 없음"

        stats_parts = []
        for sn, sv in sorted(all_stats.items(), key=lambda x: x[1]['count'], reverse=True)[:10]:
            wr = sv.get('10d_winrate'); av = sv.get('10d_avg')
            if wr is not None:
                stats_parts.append(f"{sn}: {sv['count']}회, 10일WR={wr:.0f}%, 평균={av:+.1f}%")
        stats_summary = "\n".join(stats_parts) if stats_parts else "통계 부족"

        inds = (
            f"WT1={latest['WT1']:.1f}, WT2={latest['WT2']:.1f}, RSI={latest['RSI']:.1f}, MFI={latest['MFI']:.1f}, "
            f"StochK={latest['StochK']:.1f}, StochD={latest['StochD']:.1f}, VWAP_Osc={latest['VWAP_Osc']:.2f}, "
            f"MF_Area={latest['RSI_MFI']:.1f}, ADX={latest['ADX']:.1f}, +DI={latest['Plus_DI']:.1f}, -DI={latest['Minus_DI']:.1f}, "
            f"EMA8={latest['EMA8']:.2f}, EMA21={latest['EMA21']:.2f}, "
            f"MACD={latest['MACD']:.3f}, Signal={latest['MACD_Signal']:.3f}, Hist={latest['MACD_Hist']:.3f}, "
            f"SuperTrend={st_dir_text} ({latest['SuperTrend']:.2f}), "
            f"Confluence={conf_now:.1f}, Bias={bias}({bscore:.1f}), "
            f"Trend={trend_regime}, {prox_text}, {sq_text}"
        )
        enhanced = (
            f"📌 [최근 10일 OHLCV]\n{ohlcv}\n\n"
            f"📌 [60일 종가]\n{prices60}\n\n"
            f"📌 [지표]\n{inds}\n\n"
            f"📌 [지지/저항]\n{sr_text}\n\n"
            f"📌 [시그널]\n{sig_text}\n\n"
            f"📌 [백테스트 통계 (2년)]\n{stats_summary}"
        )
        return fig, enhanced, meta

    except Exception as e:
        return None, f"주가 데이터 로딩 실패: {e}", None


# ──────────────────────────────────────────
# UI 렌더 (통합)
# ──────────────────────────────────────────
def _ind_label(name, val):
    thresholds = {
        'wt1': [(-53, '극과매도'), (-20, '과매도'), (20, '중립'), (53, '과매수'), (999, '극과매수')],
        'rsi': [(30, '과매도'), (45, '약세'), (55, '중립'), (70, '강세'), (999, '과매수')],
        'mfi': [(30, '과매도'), (45, '약세'), (55, '중립'), (70, '강세'), (999, '과매수')],
        'stochk': [(20, '바닥'), (80, ''), (999, '천장')],
    }
    for thresh, lbl in thresholds.get(name, []):
        if val < thresh: return lbl
    return ''


def _ind_cls(val, bull_thresh, bear_thresh):
    if val < bull_thresh: return 'ind-bullish'
    if val > bear_thresh: return 'ind-bearish'
    return 'ind-neutral'


def render_price_header(meta):
    chg = meta['price_change']; pct = meta['price_change_pct']
    cls = 'price-change-up' if chg >= 0 else 'price-change-down'
    ico = '▲' if chg >= 0 else '▼'
    vr = meta['volume'] / meta['avg_volume'] if meta['avg_volume'] else 0
    cv = meta.get('confluence_score', 0)
    mh = meta.get('macd_hist', 0)
    st_dir = meta.get('supertrend_dir', 0)
    shield = meta.get('shield_status', '')

    indicators = [
        ('WT', meta['wt1'], _ind_cls(meta['wt1'], -20, 20), _ind_label('wt1', meta['wt1'])),
        ('RSI', meta['rsi'], _ind_cls(meta['rsi'], 40, 60), _ind_label('rsi', meta['rsi'])),
        ('MFI', meta['mfi'], _ind_cls(meta['mfi'], 40, 60), _ind_label('mfi', meta['mfi'])),
        ('MF', meta['mf_area'], _ind_cls(meta['mf_area'], 0, 0), ''),
        ('Vol', vr, 'ind-bullish' if vr > 1.5 else 'ind-neutral', 'x'),
        ('ADX', meta['adx'], 'ind-bullish' if meta['adx'] > 25 else 'ind-neutral', ''),
        ('StK', meta['stochk'], _ind_cls(meta['stochk'], 30, 70), _ind_label('stochk', meta['stochk'])),
        ('MACD', mh, 'ind-bullish' if mh > 0 else ('ind-bearish' if mh < 0 else 'ind-neutral'), ''),
        ('Conf', cv, 'ind-bullish' if cv >= 3.5 else ('ind-bearish' if cv <= -3.5 else 'ind-neutral'), ''),
        ('ST', '▲' if st_dir == 1 else '▼', 'ind-bullish' if st_dir == 1 else 'ind-bearish', ''),
    ]

    ind_html = ""
    for name, val, css, lbl in indicators:
        if name == 'Vol':
            ind_html += f"<span class='indicator-mini {css}'>{name}: {val:.1f}{lbl}</span>"
        elif name == 'ST':
            ind_html += f"<span class='indicator-mini {css}'>{name}: {val}</span>"
        elif name == 'MACD':
            ind_html += f"<span class='indicator-mini {css}'>{name}: {val:+.2f}</span>"
        elif name == 'Conf':
            ind_html += f"<span class='indicator-mini {css}'>{name}: {val:.1f}</span>"
        elif name == 'MF':
            ind_html += f"<span class='indicator-mini {css}'>{name}: {val:.1f}</span>"
        else:
            ind_html += f"<span class='indicator-mini {css}'>{name}: {val:.0f} {lbl}</span>"

    if shield:
        ind_html += f"<span class='indicator-mini ind-bearish' style='font-weight:700;'>🔓 {shield}</span>"

    st.markdown(f"""
    <div class="price-header">
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <div>
                <p class="price-label">💎 {meta['ticker']} · {meta['last_date']} · <b>{meta.get('trend_regime', '')}</b></p>
                <p class="price-big" style="color:#FAFAFA;">${meta['price']:.2f}
                    <span class="{cls}" style="font-size:1rem;margin-left:8px;">
                        {ico} {abs(chg):.2f} ({abs(pct):.2f}%)</span></p>
            </div>
            <div style="text-align:right;">
                <p class="price-label">ATR (변동성)</p>
                <p style="color:#FFC107;font-size:1.1rem;font-weight:600;margin:0;">
                    ${meta['atr']:.2f} ({meta['atr_pct']:.1f}%)</p>
            </div>
        </div>
        <div style="margin-top:10px;display:flex;gap:6px;flex-wrap:wrap;">{ind_html}</div>
    </div>""", unsafe_allow_html=True)


def render_sr_levels(meta):
    supports = meta.get('supports', []); resists = meta.get('resistances', [])
    if not supports and not resists: return
    html = '<div style="margin:8px 0;">'
    if resists:
        html += '<div style="margin-bottom:4px;"><span style="color:#888;font-size:0.75rem;">저항:</span> '
        html += "".join(f"<span class='sr-level sr-resist'>${r['price']:.2f} <small>{r['name']}</small></span>" for r in resists[:4])
        html += '</div>'
    if supports:
        html += '<div><span style="color:#888;font-size:0.75rem;">지지:</span> '
        html += "".join(f"<span class='sr-level sr-support'>${s['price']:.2f} <small>{s['name']}</small></span>" for s in supports[:4])
        html += '</div>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


def render_bias_badge(meta):
    bias = meta['overall_bias']; sc = meta.get('bias_score', 0); cv = meta.get('confluence_score', 0)
    styles = {
        'STRONG BUY':  ('rgba(0,230,118,0.2)',  '#00E676', '🟢🟢'),
        'BUY':         ('rgba(0,230,118,0.12)', '#00E676', '🟢'),
        'STRONG SELL': ('rgba(255,23,68,0.2)',  '#FF1744', '🔴🔴'),
        'SELL':        ('rgba(255,23,68,0.12)', '#FF1744', '🔴'),
        'NEUTRAL':     ('rgba(255,193,7,0.12)', '#FFC107', '🟠'),
    }
    bg, clr, ico = styles.get(bias, styles['NEUTRAL'])
    cc = '#00E676' if cv >= 3.5 else ('#FF1744' if cv <= -3.5 else '#FFC107')
    pct = max(0, min(100, ((sc + 14) / 28) * 100))

    st.markdown(f"""<div style="background:{bg};border-radius:10px;padding:12px 16px;text-align:center;margin:8px 0;">
        <span style="font-size:1.2rem;font-weight:700;color:{clr};">{ico} 종합 판정: {bias} ({sc:.1f})</span><br>
        <span style="font-size:0.9rem;color:{cc};font-weight:600;">📊 Confluence: {cv:.1f}</span>
        <div class="bias-gauge-track" style="margin:10px auto;max-width:300px;">
            <div class="bias-gauge-needle" style="left:{pct}%;"></div>
        </div>
        <div style="display:flex;justify-content:space-between;max-width:300px;margin:0 auto;">
            <span style="color:#FF1744;font-size:0.65rem;">STRONG SELL</span>
            <span style="color:#888;font-size:0.65rem;">NEUTRAL</span>
            <span style="color:#00E676;font-size:0.65rem;">STRONG BUY</span>
        </div>
    </div>""", unsafe_allow_html=True)


def render_proximity_alert(meta):
    alerts = []
    bp = meta.get('buy_proximity', 0); sp = meta.get('sell_proximity', 0)
    if bp >= 70: alerts.append(('🟢⚡ 매수 시그널 매우 임박!', '#00E676', bp))
    elif bp >= 50: alerts.append(('🟢 매수 시그널 접근 중', '#69F0AE', bp))
    if sp >= 70: alerts.append(('🔴⚡ 매도 시그널 매우 임박!', '#FF1744', sp))
    elif sp >= 50: alerts.append(('🔴 매도 시그널 접근 중', '#FF5252', sp))
    if meta.get('squeeze_on'): alerts.append(('💥 Squeeze ON — 변동성 폭발 임박', '#FFFF00', 80))
    for txt, clr, pct in alerts:
        w = min(pct, 100)
        st.markdown(f"""
        <div style="background:rgba(255,255,255,0.03);border:1px solid #2D333B;border-radius:8px;padding:8px 14px;margin:4px 0;">
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
    date_groups = OrderedDict()
    for icon, lbl, d_str, side in sigs:
        date_groups.setdefault(d_str, []).append((icon, lbl, side))
    for d_str in reversed(date_groups):
        grp = date_groups[d_str]
        bc = sum(1 for _, _, s in grp if s == 'buy')
        sc = sum(1 for _, _, s in grp if s == 'sell')
        ct = 'signal-card-buy' if bc > sc else ('signal-card-sell' if sc > bc else 'signal-card-neutral')
        badges = " ".join(f'<span class="indicator-mini {"ind-bullish" if s == "buy" else "ind-bearish"}">{i} {l}</span>'
                          for i, l, s in grp)
        st.markdown(f"""<div class="signal-card {ct}">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <span style="font-weight:700;font-size:0.9rem;color:#FAFAFA;">📅 {d_str}</span>
                <span style="color:#888;font-size:0.75rem;">{len(grp)}개 신호</span>
            </div>
            <div style="margin-top:6px;display:flex;gap:4px;flex-wrap:wrap;">{badges}</div>
        </div>""", unsafe_allow_html=True)


def render_signal_stats(meta):
    with st.expander("📊 시그널 백테스트 통계 (과거 2년, 최소 5회 이상)", expanded=False):
        alls = meta.get('all_signal_stats', {})
        if not alls: st.caption("통계 데이터 없음"); return
        c1, c2 = st.columns(2)
        for col, title, direction in [(c1, "🟢 BUY", 'buy'), (c2, "🔴 SELL", 'sell')]:
            with col:
                st.markdown(f"##### {title} 시그널")
                filtered = {k: v for k, v in alls.items() if v['direction'] == direction}
                for sn, sv in sorted(filtered.items(), key=lambda x: x[1]['count'], reverse=True):
                    wr = sv.get('10d_winrate'); av = sv.get('10d_avg')
                    if wr is None: continue
                    if direction == 'sell':
                        rate = 100 - wr
                        clr = '#FF1744' if rate > 55 else ('#FFC107' if rate > 45 else '#00E676')
                        label = f"10일 후 하락 <span style='color:{clr}'>{rate:.0f}%</span>"
                    else:
                        clr = '#00E676' if wr > 55 else ('#FFC107' if wr > 45 else '#FF1744')
                        label = f"10일 상승 <span style='color:{clr}'>{wr:.0f}%</span>"
                    icon = ALL_CHART_SIGNALS.get(sn, {}).get('icon', '')
                    st.markdown(f"<span style='font-size:0.82rem;'>{icon} **{sn}** ({sv['count']}회) · "
                                f"{label} · 평균 {av:+.1f}%</span>", unsafe_allow_html=True)


def render_inline_analysis(msg):
    meta = msg.get('meta'); fig = msg.get('fig')
    if meta:
        render_price_header(meta); render_sr_levels(meta)
        render_bias_badge(meta); render_proximity_alert(meta)
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
    st.markdown("<p style='color:#888;font-size:0.8rem;'>AI 주가 분석 · Market Cipher B+ v3.1</p>", unsafe_allow_html=True)
    st.markdown("---")

    st.markdown("### 📅 차트 기간")
    chart_period = st.radio("표시 기간", ['3개월', '6개월', '1년', '2년'],
                            index=2, horizontal=True, key="chart_period_radio")
    chart_days = {'3개월': 63, '6개월': 126, '1년': 252, '2년': 504}[chart_period]

    st.markdown("### ⚙️ AI 분석")
    auto_ai = st.toggle("자동 AI 분석", value=True, key="auto_ai_toggle",
                         help="티커 입력 후 자동으로 AI 심층 분석을 시작합니다.")
    st.markdown("---")

    if st.button("🗑️ 대화 초기화", use_container_width=True, type="secondary"):
        st.session_state.messages = [
            {"role": "assistant", "type": "text",
             "content": "안녕하세요! 💎 **CipherX** 입니다.\n\n분석할 **티커명**을 입력하세요."}
        ]
        st.session_state.pending_ai_ticker = None
        st.session_state.pending_ai_prompt = None
        st.session_state.auto_run = False
        st.rerun()
    st.markdown("---")

    st.markdown("### 📖 신호 가이드")
    BUY_ORDER = [k for k in SIGNAL_DESCRIPTIONS if SIGNAL_DESCRIPTIONS[k].get('icon') and
                 SIGNAL_REGISTRY.get(k, COMPOSITE_SIGNALS.get(k, {})).get('dir') == 'buy']
    SELL_ORDER = [k for k in SIGNAL_DESCRIPTIONS if SIGNAL_DESCRIPTIONS[k].get('icon') and
                  SIGNAL_REGISTRY.get(k, COMPOSITE_SIGNALS.get(k, {})).get('dir') == 'sell']

    for title, order in [("🟢 매수 신호 (BUY)", BUY_ORDER), ("🔴 매도 신호 (SELL)", SELL_ORDER)]:
        with st.expander(title, expanded=False):
            for k in order:
                info = SIGNAL_DESCRIPTIONS[k]
                st.markdown(f"**{info['icon']} {info['lbl']}** · <span style='color:#888;font-size:0.82rem;'>{info['kor']}</span>",
                            unsafe_allow_html=True)
                st.caption(info['desc'])
                st.markdown("<hr style='border:none;border-top:1px solid #222;margin:4px 0;'>", unsafe_allow_html=True)

    with st.expander("🛡️ 시스템 가이드", expanded=False):
        st.markdown("""
**추세 레짐**: STRONG BULL/BEAR/NEUTRAL (ADX+DI+MA50/200)
**티어별 필터링**: Tier0(Parabolic/ST)→무조건 | Tier1(Gold/Blood)→추세무관 | Tier2/3→역추세 억제
**V3.1 변경**: RSI 다이버전스 추가, MACD 히스토그램 방향 확인 필터, 시그널 중복 제거, 코드 30% 축소
        """)

    st.markdown("---")
    st.markdown("<p style='color:#555;font-size:0.7rem;text-align:center;'>CipherX v3.1</p>", unsafe_allow_html=True)


# ──────────────────────────────────────────
# 세션 초기화
# ──────────────────────────────────────────
for key, default in [
    ('messages', [{"role": "assistant", "type": "text",
                   "content": "안녕하세요! 💎 **CipherX** 입니다.\n\n분석할 **티커명**을 입력하세요."}]),
    ('pending_ai_ticker', None), ('pending_ai_prompt', None), ('auto_run', False),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ──────────────────────────────────────────
# 프롬프트 생성 함수 (V3.1 — 원본 복원 + 개선 반영)
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

💎 시그널은 추세 필터 + 쿨다운이 적용되었습니다 (V3.1):
- Tier 0 (Parabolic Top, SuperTrend Sell): 추세 무관 + 매도 쉴드 해제
- Tier 1 (Gold Dot, Blood Diamond): 추세 무관 항상 유효
- Tier 2 (T1, Divergence): 극단 역추세에서만 억제됨
- Tier 3 (T2, Diamond, Circle 등): 강한 역추세에서 억제됨
- 쿨다운 적용 완료 → 남은 시그널은 높은 신뢰도

🔥 Confluence Score (시간 감쇠 적용): ≥6 Ultra Buy | 3.5~6 Strong Buy | -3.5~3.5 Neutral | -6~-3.5 Strong Sell | ≤-6 Ultra Sell

⚠️ 반드시 확인:
1. Trend Regime — 현재 추세와 시그널 방향 일치 여부
2. Signal Proximity — 매수/매도 시그널 임박 여부
3. 지지/저항 레벨 — 제공된 S/R 데이터 활용
4. 백테스트 통계 — 과거 해당 종목에서의 시그널 적중률
5. MACD — 모멘텀 방향 확인
6. RSI 다이버전스 — WT 다이버전스와 독립 교차 검증

주가변동이유/이벤트, 공매도, 콜/풋옵션 → DEEP SEARCH.

---
━━━━━━━━━━━━━
【 📥 Input Data 】
━━━━━━━━━━━━━
[티커: {ticker_value}]

📌 [주가 + 지표]
{phist}

📌 [SwingTradeBot]
{scraped if scraped else "크롤링 데이터 없음"}

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
⑧ 지지/저항 (제공된 S/R 데이터 참조)
⑨ 백테스트 통계를 근거로 신뢰도 판단

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
* 백테스트 기반 신뢰도: [높음/중간/낮음 + 적중률 근거]

---
### 💎 마켓 사이퍼 B+ 시그널 분석
* WaveTrend: [WT1/WT2, 상태]
* MACD: [방향, 히스토그램 추세]
* Money Flow: [방향]
* 🔥 Confluence Score: [점수, 판정]
* ⚠️ Signal Proximity: [매수/매도 임박 여부]
* RSI 다이버전스: [감지 여부 + WT 다이버전스와 교차 검증]
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
* ATR ±__%, ADX, TTM Squeeze, MA Cross, SuperTrend
> 해석: [🔵/🔴/🟠]

---
### 지지선 및 저항선
* 지지선: [제공된 S/R 데이터 기반]
* 저항선: [제공된 S/R 데이터 기반]
* 핵심 레벨 해석

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
                    st_copy_to_clipboard(msg["prompt"], before_copy_label="📋 복사", after_copy_label="✅ 복사됨!")
        elif msg.get("type") == "report":
            with st.expander(f"📊 {msg.get('ticker', '')} AI 심층 분석 리포트", expanded=True):
                st.markdown(msg["content"])
            ns = datetime.now().strftime("%Y%m%d_%H%M")
            st.download_button("📥 다운로드 (.md)", key=f"dl_{i}",
                               data=msg["content"].encode('utf-8'),
                               file_name=f"{msg.get('ticker', 'report').upper()}_Report_{ns}.md",
                               mime="text/markdown", use_container_width=True)
        else:
            st.markdown(msg.get("content", ""))


# ── AI 실행 함수 ──
def run_ai_analysis(ticker_pending, prompt_pending):
    with st.chat_message("assistant", avatar="✨"):
        pb = st.progress(0, text="AI 분석 초기화 중...")
        try:
            pb.progress(10, text="Gemini 모델 로딩...")
            model = genai.GenerativeModel('gemini-2.0-flash')
            pb.progress(20, text="시장 데이터 분석 중...")
            resp = model.generate_content(prompt_pending, stream=True)
            pb.progress(40, text="AI 리포트 생성 중...")
            rpt = ""; rph = st.empty(); cc = 0
            for chunk in resp:
                rpt += chunk.text; rph.markdown(rpt + " ▌"); cc += 1
                pb.progress(min(40 + cc * 2, 95), text="AI 리포트 작성 중...")
            pb.progress(100, text="✅ 분석 완료!"); time.sleep(0.5); pb.empty(); rph.empty()
            st.session_state.messages.append({
                "role": "assistant", "type": "report",
                "ticker": ticker_pending.upper(), "content": rpt,
            })
            st.session_state.pending_ai_ticker = None
            st.session_state.pending_ai_prompt = None
            st.session_state.auto_run = False
            st.rerun()
        except Exception as e:
            pb.empty()
            st.error(f"AI 분석 중 오류 발생: {e}")


# ── 자동 AI 분석 (★ FIX: auto_ai 토글 작동) ──
if st.session_state.pending_ai_ticker and st.session_state.pending_ai_prompt:
    ticker_p = st.session_state.pending_ai_ticker
    prompt_p = st.session_state.pending_ai_prompt

    if auto_ai and st.session_state.get('auto_run', False):
        # 자동 실행
        run_ai_analysis(ticker_p, prompt_p)
    else:
        # 수동 버튼
        if st.button(f"🚀 {ticker_p.upper()} AI 심층 분석 시작", type="primary", use_container_width=True):
            run_ai_analysis(ticker_p, prompt_p)


def process_ticker(ticker_value):
    ticker_value = ticker_value.strip().upper()
    if not ticker_value:
        return
    st.session_state.messages.append({"role": "user", "type": "text", "content": ticker_value})

    with st.chat_message("assistant", avatar="✨"):
        pg = st.progress(0, text=f"🌐 {ticker_value} 데이터 수집 시작...")
        pg.progress(15, text="📡 SwingTradeBot 크롤링 중...")
        scraped = get_stock_data(ticker_value)
        pg.progress(40, text="📊 Yahoo Finance 주가 로딩 중...")
        cfig, phist, meta = analyze_ticker(ticker_value, chart_period_days=chart_days)
        pg.progress(70, text="💎 마켓 사이퍼 + 시그널 분석 중...")
        time.sleep(0.3)
        pg.progress(90, text="📝 프롬프트 생성 중...")

        if scraped or cfig:
            prompt = build_analysis_prompt(ticker_value, phist, scraped)
            st.session_state.messages.append({
                "role": "assistant", "type": "analysis", "ticker": ticker_value,
                "content": f"✅ **{ticker_value}** 분석 완료! 아래에서 차트와 시그널을 확인하세요.",
                "fig": cfig, "meta": meta, "prompt": prompt,
            })
            st.session_state.pending_ai_ticker = ticker_value
            st.session_state.pending_ai_prompt = prompt
            st.session_state.auto_run = auto_ai  # ★ 자동 실행 플래그
            pg.progress(100, text="✅ 완료!"); time.sleep(0.3); pg.empty()
            st.rerun()
        else:
            pg.empty()
            st.session_state.messages.append({
                "role": "assistant", "type": "text",
                "content": f"⚠️ **{ticker_value}** 데이터를 찾을 수 없습니다.\n\n"
                           f"• 올바른 티커인지 확인하세요 (예: AAPL, TSLA, MSFT)\n"
                           f"• 한국 종목은 지원하지 않습니다\n"
                           f"• 네트워크 연결을 확인하세요",
            })
            st.rerun()


if ticker_input := st.chat_input("분석할 티커를 입력하세요 (예: IREN, TSLA, AAPL)"):
    process_ticker(ticker_input)