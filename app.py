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
def load_css():
    st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    html, body, [class*="css"] { font-family: 'Pretendard', 'Noto Sans KR', sans-serif !important; }
    .stApp { background-color: #0E1117; }
    p, div[data-testid="stMarkdownContainer"] p, div[data-testid="stChatMessageContent"] p,
    h1, h2, h3, h4, h5, h6, li { color: #FAFAFA !important; }
    div[data-testid="stCodeBlock"], pre, code { background-color: #1A1D24 !important; color: #FAFAFA !important; }
    div[data-testid="stCodeBlock"] span { text-shadow: none !important; }
    div[data-testid="stCodeBlock"] span[style*="color: rgb(0, 0, 0)"],
    div[data-testid="stCodeBlock"] span[style*="color: black"],
    div[data-testid="stCodeBlock"] code > span:not([class]) { color: #FAFAFA !important; }
    div[data-testid="stChatMessage"]:nth-child(even) { background-color: #161A22; border-radius: 12px; padding: 5px 15px; }
    header {visibility: hidden;}
    .block-container { padding-top: 1rem !important; max-width: 900px; }
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important; border: none !important; border-radius: 12px !important;
        padding: 0.6rem 1.5rem !important; font-weight: 600 !important;
        font-size: 1rem !important; transition: all 0.3s ease !important; width: 100%;
    }
    div.stButton > button[kind="primary"]:hover { transform: translateY(-2px); box-shadow: 0 8px 20px rgba(118, 75, 162, 0.4) !important; }
    div.stButton > button[kind="secondary"] {
        background-color: #1E2127 !important; color: #E2E8F0 !important;
        border: 1px solid #333842 !important; border-radius: 12px !important;
        font-weight: 500 !important; transition: all 0.2s ease !important; width: 100%;
    }
    div.stButton > button[kind="secondary"]:hover { border-color: #667eea !important; color: #667eea !important; }
    .streamlit-expanderHeader { background-color: #161A22 !important; border-radius: 10px !important; font-weight: 600 !important; }
    .streamlit-expanderHeader p { color: #414df2 !important; }
    div[data-testid="stExpander"] { border: 1px solid #2D333B !important; border-radius: 10px !important; background-color: #161A22; }
    section[data-testid="stSidebar"] { background-color: #0A0D12; border-right: 1px solid #1E2127; }
    section[data-testid="stSidebar"] .stMarkdown p { color: #AAAAAA !important; }
    .signal-card { border-radius: 12px; padding: 16px 20px; margin: 6px 0; border: 1px solid #2D333B; }
    .signal-card-buy { background: linear-gradient(135deg, rgba(0,230,118,0.08) 0%, rgba(0,191,255,0.05) 100%); border-left: 4px solid #00E676; }
    .signal-card-sell { background: linear-gradient(135deg, rgba(255,23,68,0.08) 0%, rgba(255,82,82,0.05) 100%); border-left: 4px solid #FF1744; }
    .signal-card-neutral { background: linear-gradient(135deg, rgba(255,193,7,0.08) 0%, rgba(255,152,0,0.05) 100%); border-left: 4px solid #FFC107; }
    .price-header { background: linear-gradient(135deg, #161A22 0%, #1A1F2E 100%); border: 1px solid #2D333B; border-radius: 14px; padding: 18px 24px; margin-bottom: 16px; }
    .price-big { font-size: 2rem; font-weight: 700; margin: 0; }
    .price-change-up { color: #00E676 !important; }
    .price-change-down { color: #FF1744 !important; }
    .price-label { color: #666 !important; font-size: 0.8rem; margin: 0; }
    .indicator-mini { display: inline-block; padding: 4px 10px; margin: 2px; border-radius: 6px; font-size: 0.78rem; font-weight: 500; }
    .ind-bullish { background: rgba(0,230,118,0.15); color: #00E676; }
    .ind-bearish { background: rgba(255,23,68,0.15); color: #FF1744; }
    .ind-neutral { background: rgba(255,193,7,0.15); color: #FFC107; }
    .bias-gauge-track { height: 8px; border-radius: 4px; margin: 8px 0; background: linear-gradient(90deg, #FF1744 0%, #FF1744 20%, #FFC107 35%, #888 50%, #FFC107 65%, #00E676 80%, #00E676 100%); position: relative; }
    .bias-gauge-needle { width: 4px; height: 16px; background: white; border-radius: 2px; position: absolute; top: -4px; transform: translateX(-50%); box-shadow: 0 0 6px rgba(255,255,255,0.5); }
    .quick-btn { display: inline-block; margin: 2px; }
    </style>
    """, unsafe_allow_html=True)

load_css()

# ──────────────────────────────────────────
# 🔧 통합 시그널 레지스트리 (V2.8)
# ──────────────────────────────────────────
SIGNAL_REGISTRY = {
    'Gold_Dot':         {'w': 3.0, 'dir': 'buy',  'icon': '🏆', 'label': 'GOLD DOT',       'sym': 'circle',       'sz': 18, 'clr': '#FFD700', 'base': 'Low',  'atr_m': -3.0, 'kor': '최강 매수', 'desc': '모든 매수 조건 극단 수렴. RSI<30 + MFI<30 + WT1<-60 + 상승 다이버전스.'},
    'Green_Dot_T1':     {'w': 2.5, 'dir': 'buy',  'icon': '🟢', 'label': 'BUY T1',         'sym': 'circle',       'sz': 16, 'clr': '#00E676', 'base': 'Low',  'atr_m': -2.5, 'kor': '강한 매수', 'desc': 'WT 과매도 교차(2봉) + RSI<30 + MFI<30 + MF<0.'},
    'Green_Dot_T2':     {'w': 2.0, 'dir': 'buy',  'icon': '🟩', 'label': 'BUY T2',         'sym': 'circle',       'sz': 13, 'clr': '#69F0AE', 'base': 'Low',  'atr_m': -2.2, 'kor': '매수', 'desc': 'T1 완화 버전. WT 과매도 + RSI 또는 MFI < 32.'},
    'Blue_Diamond':     {'w': 2.0, 'dir': 'buy',  'icon': '🔹', 'label': 'BLUE DIA',       'sym': 'diamond',      'sz': 14, 'clr': '#00bfff', 'base': 'Low',  'atr_m': -1.8, 'kor': '추세 매수', 'desc': 'WT2≤0 상승교차(2봉) + HTF 강세 + 하락추세 아님.'},
    'Green_Circle':     {'w': 1.5, 'dir': 'buy',  'icon': '✅', 'label': 'BUY Circle',     'sym': 'circle-open',  'sz': 11, 'clr': '#00E676', 'base': 'Low',  'atr_m': -1.2, 'kor': '과매도 반등', 'desc': 'WT 과매도 교차(2봉). Green Dot 미달.'},
    'Bull_Divergence':  {'w': 2.0, 'dir': 'buy',  'icon': '📈', 'label': 'Bull Div',       'sym': 'triangle-up',  'sz': 12, 'clr': '#AA00FF', 'base': 'Low',  'atr_m': -2.0, 'kor': '상승 다이버전스', 'desc': '가격 저점↓ vs WT 저점↑.'},
    'Squeeze_Fire_Buy': {'w': 1.5, 'dir': 'buy',  'icon': '💥', 'label': 'Squeeze BUY',    'sym': 'star-diamond', 'sz': 14, 'clr': '#00FFFF', 'base': 'Low',  'atr_m': -1.5, 'kor': '스퀴즈 매수', 'desc': 'TTM Squeeze 해소 + 모멘텀 상방.'},
    'Hidden_Bull_Div':  {'w': 1.5, 'dir': 'buy',  'icon': '🔀', 'label': 'Hidden Bull',    'sym': 'triangle-up',  'sz': 10, 'clr': '#E040FB', 'base': 'Low',  'atr_m': -1.6, 'kor': '히든 상승 다이버전스', 'desc': '가격 저점↑ vs 오실레이터 저점↓.'},
    'Volume_Climax_Buy':{'w': 2.0, 'dir': 'buy',  'icon': '🌊', 'label': 'Vol Climax BUY', 'sym': 'hexagram',     'sz': 14, 'clr': '#00BCD4', 'base': 'Low',  'atr_m': -2.8, 'kor': '거래량 클라이맥스 매수', 'desc': '평균 3배 거래량 + 하락 장대봉 + WT과매도 → 다음봉 반등 확인.'},
    'OBV_Div_Buy':      {'w': 1.0, 'dir': 'buy',  'icon': '📊', 'label': 'OBV Div BUY',   'sym': 'triangle-up',  'sz': 10, 'clr': '#80DEEA', 'base': 'Low',  'atr_m': -1.4, 'kor': 'OBV 다이버전스 매수', 'desc': 'OBV-가격 상승 다이버전스.'},
    'ADX_Momentum_Buy': {'w': 1.5, 'dir': 'buy',  'icon': '🚀', 'label': 'ADX Ignition',   'sym': 'arrow-up',     'sz': 11, 'clr': '#76FF03', 'base': 'Low',  'atr_m': -1.4, 'kor': 'ADX 점화', 'desc': 'ADX > 20 돌파 + Plus DI > Minus DI.'},
    'Fib_Bounce_Buy':   {'w': 0.8, 'dir': 'buy',  'icon': '📐', 'label': 'Fib Bounce',     'sym': 'diamond-open', 'sz': 10, 'clr': '#FFAB00', 'base': 'Low',  'atr_m': -1.0, 'kor': '피보나치 반등', 'desc': '0.618~0.786 되돌림 지지 + WT 상승교차.'},
    'Bullish_Engulfing': {'w': 1.5, 'dir': 'buy', 'icon': '☀️', 'label': 'Bull Engulf',    'sym': 'square',       'sz': 10, 'clr': '#00E676', 'base': 'Low',  'atr_m': -1.3, 'kor': '상승 장악형', 'desc': '전일 하락캔들을 감싸는 상승캔들 + WT 약세구간.'},
    'Golden_Cross':     {'w': 1.5, 'dir': 'buy',  'icon': '✨', 'label': 'Golden Cross',   'sym': 'cross',        'sz': 12, 'clr': '#FFD700', 'base': 'Low',  'atr_m': -0.8, 'kor': '골든 크로스', 'desc': '50일 MA > 200일 MA 상향돌파.'},
    'EMA_Pullback_Buy': {'w': 2.0, 'dir': 'buy',  'icon': '🎯', 'label': 'EMA Pullback',   'sym': 'triangle-up',  'sz': 13, 'clr': '#00BFA5', 'base': 'Low',  'atr_m': -1.8, 'kor': 'EMA 눌림목 매수', 'desc': '상승추세 중 EMA 부근 조정 후 WT 반등 + 거래량 확인.'},
    'Momentum_Ignition_Buy': {'w': 2.5, 'dir': 'buy', 'icon': '🔥', 'label': 'Mom. Ignition', 'sym': 'star-diamond', 'sz': 15, 'clr': '#FF6D00', 'base': 'Low', 'atr_m': -2.5, 'kor': '모멘텀 점화 매수', 'desc': '장대양봉>ATR×1.5 + 거래량>20MA×2.5 + BB돌파 + 상승추세 + WT미과매수.'},
    'SuperTrend_Buy':   {'w': 1.5, 'dir': 'buy',  'icon': '📈', 'label': 'ST Flip Bull',   'sym': 'arrow-up',     'sz': 12, 'clr': '#00E5FF', 'base': 'Low',  'atr_m': -1.5, 'kor': '슈퍼트렌드 강세 전환', 'desc': 'SuperTrend 하단선 위로 돌파.'},
    'VWAP_Bounce_Buy':  {'w': 1.5, 'dir': 'buy',  'icon': '🏦', 'label': 'VWAP Bounce',    'sym': 'triangle-up',  'sz': 11, 'clr': '#00E5FF', 'base': 'Low',  'atr_m': -1.3, 'kor': 'VWAP 반등 매수', 'desc': 'VWAP 하방이탈 후 복귀 + WT 상승교차 + 거래량 확인.'},
    'Parabolic_Bottom_Buy': {'w': 3.0, 'dir': 'buy', 'icon': '🧊', 'label': 'Parabolic Bot', 'sym': 'diamond', 'sz': 16, 'clr': '#00FFFF', 'base': 'Low', 'atr_m': -3.0, 'kor': '포물선 바닥 매수', 'desc': 'WT1<-85 꺾임+양봉 또는 Close<BB-ATR×1.5 극단이격+양봉.'},

    'Blood_Diamond':    {'w': 3.0, 'dir': 'sell', 'icon': '🩸', 'label': 'BLOOD DIA',      'sym': 'diamond',       'sz': 18, 'clr': '#DC143C', 'base': 'High', 'atr_m': 3.0, 'kor': '최강 매도', 'desc': 'RSI>70 + MFI>70 + WT1>60 + 하락 다이버전스.'},
    'Red_Dot_T1':       {'w': 2.5, 'dir': 'sell', 'icon': '🔴', 'label': 'SELL T1',        'sym': 'circle',        'sz': 16, 'clr': '#FF1744', 'base': 'High', 'atr_m': 2.5, 'kor': '강한 매도', 'desc': 'WT 과매수 하락교차(2봉) + RSI>70 + MFI>70 + MF>0.'},
    'Red_Dot_T2':       {'w': 2.0, 'dir': 'sell', 'icon': '🟥', 'label': 'SELL T2',        'sym': 'circle',        'sz': 13, 'clr': '#FF5252', 'base': 'High', 'atr_m': 2.2, 'kor': '매도', 'desc': 'T1 완화 버전. WT 과매수 + RSI 또는 MFI > 68.'},
    'Red_Diamond':      {'w': 2.0, 'dir': 'sell', 'icon': '🔸', 'label': 'RED DIA',        'sym': 'diamond',       'sz': 14, 'clr': '#ff3333', 'base': 'High', 'atr_m': 1.8, 'kor': '추세 매도', 'desc': 'WT2≥0 하락교차(2봉) + HTF 약세 + 상승추세 아님.'},
    'Red_Circle':       {'w': 1.5, 'dir': 'sell', 'icon': '⛔', 'label': 'SELL Circle',    'sym': 'circle-open',   'sz': 11, 'clr': '#FF1744', 'base': 'High', 'atr_m': 1.2, 'kor': '과매수 하락', 'desc': 'WT 과매수 하락교차(2봉). Red Dot 미달.'},
    'Bear_Divergence':  {'w': 2.0, 'dir': 'sell', 'icon': '📉', 'label': 'Bear Div',       'sym': 'triangle-down', 'sz': 12, 'clr': '#AA00FF', 'base': 'High', 'atr_m': 2.0, 'kor': '하락 다이버전스', 'desc': '가격 고점↑ vs WT 고점↓.'},
    'Squeeze_Fire_Sell':{'w': 1.5, 'dir': 'sell', 'icon': '🧨', 'label': 'Squeeze SELL',   'sym': 'star-diamond',  'sz': 14, 'clr': '#FF6600', 'base': 'High', 'atr_m': 1.5, 'kor': '스퀴즈 매도', 'desc': 'TTM Squeeze 해소 + 모멘텀 하방.'},
    'Hidden_Bear_Div':  {'w': 1.5, 'dir': 'sell', 'icon': '🔁', 'label': 'Hidden Bear',    'sym': 'triangle-down', 'sz': 10, 'clr': '#E040FB', 'base': 'High', 'atr_m': 1.6, 'kor': '히든 하락 다이버전스', 'desc': '가격 고점↓ vs 오실레이터 고점↑.'},
    'Volume_Climax_Sell':{'w': 2.0, 'dir': 'sell','icon': '🌋', 'label': 'Vol Climax SELL', 'sym': 'hexagram',     'sz': 14, 'clr': '#FF5722', 'base': 'High', 'atr_m': 2.8, 'kor': '거래량 클라이맥스 매도', 'desc': '평균 3배 거래량 + 상승 장대봉 + WT과매수 → 다음봉 하락 확인.'},
    'OBV_Div_Sell':     {'w': 1.0, 'dir': 'sell', 'icon': '🔻', 'label': 'OBV Div SELL',   'sym': 'triangle-down', 'sz': 10, 'clr': '#FFAB91', 'base': 'High', 'atr_m': 1.4, 'kor': 'OBV 다이버전스 매도', 'desc': 'OBV-가격 하락 다이버전스.'},
    'ADX_Momentum_Sell':{'w': 1.5, 'dir': 'sell', 'icon': '💨', 'label': 'ADX Down',       'sym': 'arrow-down',    'sz': 11, 'clr': '#FF3D00', 'base': 'High', 'atr_m': 1.4, 'kor': 'ADX 하락 점화', 'desc': 'ADX > 20 돌파 + Minus DI > Plus DI.'},
    'Fib_Resistance_Sell':{'w': 0.8, 'dir': 'sell','icon': '🚧', 'label': 'Fib Resist',    'sym': 'diamond-open',  'sz': 10, 'clr': '#FF8F00', 'base': 'High', 'atr_m': 1.0, 'kor': '피보나치 저항', 'desc': '0.618~0.786 되돌림 저항 + WT 하락교차.'},
    'Bearish_Engulfing': {'w': 1.5, 'dir': 'sell','icon': '🌑', 'label': 'Bear Engulf',    'sym': 'x',             'sz': 10, 'clr': '#D50000', 'base': 'High', 'atr_m': 1.3, 'kor': '하락 장악형', 'desc': '전일 상승캔들을 감싸는 하락캔들 + WT 강세구간.'},
    'Death_Cross':      {'w': 1.5, 'dir': 'sell', 'icon': '☠️', 'label': 'Death Cross',    'sym': 'cross',         'sz': 12, 'clr': '#FF1744', 'base': 'High', 'atr_m': 0.8, 'kor': '데드 크로스', 'desc': '50일 MA < 200일 MA 하향돌파.'},
    'SuperTrend_Sell':  {'w': 2.0, 'dir': 'sell', 'icon': '📉', 'label': 'ST Flip Bear',   'sym': 'arrow-down',    'sz': 12, 'clr': '#FF1744', 'base': 'High', 'atr_m': 1.5, 'kor': '슈퍼트렌드 약세 전환', 'desc': 'SuperTrend 상단선 아래로 돌파.'},
    'Parabolic_Top_Sell':{'w': 3.0, 'dir': 'sell','icon': '🌡️', 'label': 'Parabolic Top',  'sym': 'diamond',       'sz': 16, 'clr': '#FF0000', 'base': 'High', 'atr_m': 3.0, 'kor': '포물선 천장 매도', 'desc': 'WT1>85 꺾임+음봉 또는 Close>BB+ATR×1.5 극단이격+음봉.'},
    'EMA_Pullback_Sell':{'w': 2.0, 'dir': 'sell', 'icon': '🎯', 'label': 'EMA PB Sell',    'sym': 'triangle-down', 'sz': 13, 'clr': '#FF6E40', 'base': 'High', 'atr_m': 1.8, 'kor': 'EMA 되돌림 매도', 'desc': '하락추세 중 EMA 부근 반등 후 WT 재하락 + 거래량 확인.'},
    'Momentum_Ignition_Sell':{'w': 2.5, 'dir': 'sell','icon': '💣', 'label': 'Mom. Ign Sell','sym': 'star-diamond', 'sz': 15, 'clr': '#D50000', 'base': 'High', 'atr_m': 2.5, 'kor': '모멘텀 점화 매도', 'desc': '장대음봉>ATR×1.5 + 거래량>20MA×2.5 + BB하단돌파 + 하락추세 + WT미과매도.'},
    'VWAP_Reject_Sell': {'w': 1.5, 'dir': 'sell', 'icon': '🏛️', 'label': 'VWAP Reject',   'sym': 'triangle-down', 'sz': 11, 'clr': '#FF6E40', 'base': 'High', 'atr_m': 1.3, 'kor': 'VWAP 저항 매도', 'desc': 'VWAP 상방돌파 실패 후 하락 + WT 하락교차 + 거래량 확인.'},
}

COMPOSITE_SIGNALS = {
    'Ultra_Buy':  {'w': 0, 'dir': 'buy',  'icon': '⚡', 'label': 'ULTRA BUY',  'sym': 'star', 'sz': 20, 'clr': '#FFD700', 'base': 'Low',  'atr_m': -3.5, 'kor': '울트라 매수', 'desc': 'Confluence ≥6 또는 (≥5 + 동시 3개 이상 매수).'},
    'Strong_Buy': {'w': 0, 'dir': 'buy',  'icon': '🔱', 'label': 'STRONG BUY', 'sym': 'star', 'sz': 16, 'clr': '#00E676', 'base': 'Low',  'atr_m': -3.2, 'kor': '스트롱 매수', 'desc': 'Confluence 3.5~6.'},
    'Ultra_Sell': {'w': 0, 'dir': 'sell', 'icon': '🚨', 'label': 'ULTRA SELL', 'sym': 'star', 'sz': 20, 'clr': '#FF0000', 'base': 'High', 'atr_m': 3.5, 'kor': '울트라 매도', 'desc': 'Confluence ≤-6 또는 (≤-5 + 동시 3개 이상 매도).'},
    'Strong_Sell':{'w': 0, 'dir': 'sell', 'icon': '⚠️', 'label': 'STRONG SELL','sym': 'star', 'sz': 16, 'clr': '#FF1744', 'base': 'High', 'atr_m': 3.2, 'kor': '스트롱 매도', 'desc': 'Confluence -6~-3.5.'},
}

ALL_CHART_SIGNALS = {**SIGNAL_REGISTRY, **COMPOSITE_SIGNALS}

OB1, OB2, OS1, OS2 = 53, 60, -53, -60
ST_MIN_BAR = 12
QUICK_TICKERS = ['AAPL', 'TSLA', 'NVDA', 'MSFT', 'AMZN', 'META', 'GOOG', 'AMD']
_UA_LIST = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0',
]

# ──────────────────────────────────────────
# ✅ Gemini API
# ──────────────────────────────────────────
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GEMINI_API_KEY)


# ──────────────────────────────────────────
# 캐싱 함수 — 재시도 로직 추가 (v2.8)
# ──────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def get_stock_data(ticker):
    """SwingTradeBot 크롤링 — 3회 재시도 + UA 로테이션"""
    url = f"https://swingtradebot.com/equities/{ticker.upper()}"
    for attempt in range(3):
        headers = {
            'User-Agent': random.choice(_UA_LIST),
            'Referer': 'https://www.google.com/',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        try:
            time.sleep(random.uniform(1.0, 2.0) * (attempt + 1))
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 403 and attempt < 2:
                continue
            if response.status_code != 200:
                if attempt < 2:
                    continue
                return None
            soup = BeautifulSoup(response.text, 'html.parser')
            extracted = []

            for sel, tag, label, sep in [
                (('h2', {'itemprop': 'headline'}), 'find', 'HEADLINE', ' '),
                (('div', {'class_': 'recap-body'}), 'find', 'DAILY RECAP', ' '),
                (('', {'id': 'recap-tour'}), 'find_id', 'RECAP TOUR', ' '),
                (('', {'id': 'indicators-tour'}), 'find_id', 'INDICATORS TOUR', ' | '),
                (('table', {'id': 'trend-table-tour'}), 'find', 'TREND ANALYSIS', ' | '),
                (('table', {'id': 'recent-signals-tour'}), 'find', 'RECENT SIGNALS', ' | '),
            ]:
                if tag == 'find_id':
                    elem = soup.find(id=sel[1]['id'])
                else:
                    elem = soup.find(sel[0], sel[1]) if sel[0] else None
                if elem:
                    extracted.append(f"#### [{label}]\n{elem.get_text(separator=sep, strip=True)}")

            sm_tables = soup.find_all('table', class_='table-sm')
            for i, t in enumerate(sm_tables):
                if t.get('id') not in ['trend-table-tour', 'recent-signals-tour']:
                    extracted.append(f"#### [EXTRA {i}]\n{t.get_text(separator=' | ', strip=True)}")

            return "\n\n".join(extracted) if extracted else None
        except requests.exceptions.Timeout:
            if attempt < 2:
                continue
            return None
        except Exception:
            return None
    return None


@st.cache_data(ttl=300, show_spinner=False)
def get_yf_history(ticker):
    return yf.Ticker(ticker).history(period="2y")


@st.cache_data(ttl=600, show_spinner=False)
def validate_ticker(ticker):
    try:
        info = yf.Ticker(ticker).info
        return info.get('regularMarketPrice') is not None or info.get('currentPrice') is not None
    except Exception:
        return False


@st.cache_data(ttl=300, show_spinner=False)
def compute_and_cache(ticker):
    df = get_yf_history(ticker)
    if df.empty:
        return None
    df = compute_indicators(df)
    df = detect_all_signals(df)
    return df


# ──────────────────────────────────────────
# 공통 유틸
# ──────────────────────────────────────────
def _recent_true(series, lookback=3):
    return series.astype(float).rolling(window=lookback + 1, min_periods=1).max().fillna(0).astype(bool)


def _apply_cooldown(signal_series, cooldown_bars=5):
    result = signal_series.copy().astype(bool)
    vals = result.values.copy()
    last_fire = -cooldown_bars - 1
    for i in range(len(vals)):
        if vals[i]:
            if (i - last_fire) <= cooldown_bars:
                vals[i] = False
            else:
                last_fire = i
    return pd.Series(vals, index=signal_series.index)


def _vol_filter(volume, min_ratio=0.5, period=20):
    return volume >= (volume.rolling(period, min_periods=5).mean() * min_ratio)


def _is_valid_ticker_format(ticker):
    return bool(re.match(r'^[A-Za-z]{1,5}([.\-][A-Za-z]{1,2})?$', ticker))


# ──────────────────────────────────────────
# 지표 계산 엔진
# ──────────────────────────────────────────
def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
    return 100 - (100 / (1 + avg_gain / (avg_loss + 1e-10)))


def compute_mfi(high, low, close, volume, period=14):
    tp = (high + low + close) / 3
    raw_mf = tp * volume
    d = tp.diff()
    pos = raw_mf.where(d >= 0, 0.0)
    neg = raw_mf.where(d < 0, 0.0)
    return 100 - (100 / (1 + pos.rolling(period).sum() / (neg.rolling(period).sum() + 1e-10)))


def compute_rsi_mfi(high, low, close, volume, period=60):
    rsi_f, mfi_f = compute_rsi(close, 20), compute_mfi(high, low, close, volume, 20)
    rsi_s, mfi_s = compute_rsi(close, period), compute_mfi(high, low, close, volume, period)
    return (((rsi_f - 50) + (mfi_f - 50)) / 2) * 0.6 + (((rsi_s - 50) + (mfi_s - 50)) / 2) * 0.4


def compute_wavetrend(high, low, close, channel_len=9, avg_len=12, ma_len=3):
    ap = (high + low + close) / 3
    esa = ap.ewm(span=channel_len, adjust=False).mean()
    d = abs(ap - esa).ewm(span=channel_len, adjust=False).mean()
    ci = (ap - esa) / (0.015 * d + 1e-10)
    wt1 = ci.ewm(span=avg_len, adjust=False).mean()
    wt2 = wt1.rolling(window=ma_len).mean()
    return wt1, wt2, (wt1 > wt2) & (wt1.shift(1) <= wt2.shift(1)), (wt1 < wt2) & (wt1.shift(1) >= wt2.shift(1))


def compute_stoch_rsi(close, rsi_len=14, stoch_len=14, k_smooth=3, d_smooth=3):
    rsi = compute_rsi(close, rsi_len)
    stoch = ((rsi - rsi.rolling(stoch_len).min())
             / (rsi.rolling(stoch_len).max() - rsi.rolling(stoch_len).min() + 1e-10)) * 100
    k = stoch.rolling(k_smooth).mean()
    return k, k.rolling(d_smooth).mean()


def compute_vwap_oscillator(close, volume, period=20):
    cv = volume.rolling(period).sum()
    vwap = (close * volume).rolling(period).sum() / (cv + 1e-10)
    return ((close - vwap) / (vwap + 1e-10)) * 100


def compute_true_range(high, low, close):
    pc = close.shift(1)
    return pd.concat([high - low, (high - pc).abs(), (low - pc).abs()], axis=1).max(axis=1)


def compute_adx(high, low, close, period=14):
    tr = compute_true_range(high, low, close)
    ph, pl = high.shift(1), low.shift(1)
    plus_dm = pd.Series(np.where((high - ph) > (pl - low), np.maximum(high - ph, 0), 0),
                        index=high.index, dtype=float)
    minus_dm = pd.Series(np.where((pl - low) > (high - ph), np.maximum(pl - low, 0), 0),
                         index=high.index, dtype=float)
    atr = tr.ewm(alpha=1 / period, min_periods=period).mean()
    pdi = 100 * plus_dm.ewm(alpha=1 / period, min_periods=period).mean() / (atr + 1e-10)
    mdi = 100 * minus_dm.ewm(alpha=1 / period, min_periods=period).mean() / (atr + 1e-10)
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi + 1e-10)
    return dx.ewm(alpha=1 / period, min_periods=period).mean(), pdi, mdi


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
        ci, pi = pivot_lows[idx]
        cj, pj = pivot_lows[idx - 1]
        if not (min_gap <= (pi - pj) <= lookback):
            continue
        if (osc_oversold is None or ov[pi] <= osc_oversold) and pv[pi] < pv[pj] and ov[pi] > ov[pj]:
            bull_div.iloc[ci] = True
        if pv[pi] > pv[pj] and ov[pi] < ov[pj]:
            hidden_bull.iloc[ci] = True
    for idx in range(1, len(pivot_highs)):
        ci, pi = pivot_highs[idx]
        cj, pj = pivot_highs[idx - 1]
        if not (min_gap <= (pi - pj) <= lookback):
            continue
        if (osc_overbought is None or ov[pi] >= osc_overbought) and pv[pi] > pv[pj] and ov[pi] < ov[pj]:
            bear_div.iloc[ci] = True
        if pv[pi] < pv[pj] and ov[pi] > ov[pj]:
            hidden_bear.iloc[ci] = True
    return bull_div, bear_div, hidden_bull, hidden_bear


def compute_keltner_channel(high, low, close, ema_len=20, atr_len=10, atr_mult=1.5):
    mid = close.ewm(span=ema_len, adjust=False).mean()
    atr = compute_true_range(high, low, close).rolling(atr_len).mean()
    return mid + atr * atr_mult, mid, mid - atr * atr_mult


def detect_ttm_squeeze(bb_up, bb_low, kc_up, kc_low, close, high, low, kc_mid):
    squeeze_on = (bb_up < kc_up) & (bb_low > kc_low)
    fire = (~squeeze_on) & squeeze_on.shift(1).fillna(False)
    donchian_mid = (high.rolling(20).max() + low.rolling(20).min()) / 2
    momentum = close - (donchian_mid + kc_mid) / 2
    return squeeze_on, fire & (momentum > 0), fire & (momentum < 0)


def detect_volume_climax(close, opn, volume, wt1, atr, vol_mult=3.0, wt_buy=-40, wt_sell=40):
    """v2.8: ATR 기반 캔들 크기 필터 추가"""
    avg = volume.rolling(20).mean()
    body = (close - opn).abs()
    big_body = body > atr * 0.5  # 최소 ATR 50% 이상 실체
    prev_spike = (volume.shift(1) > avg.shift(1) * vol_mult) & big_body.shift(1)
    prev_bear = (close.shift(1) < opn.shift(1))
    prev_bull = (close.shift(1) > opn.shift(1))
    return (prev_spike & prev_bear & (wt1.shift(1) < wt_buy) & (close > opn),
            prev_spike & prev_bull & (wt1.shift(1) > wt_sell) & (close < opn))


def detect_obv_divergence(close, volume, wt1, lookback=60, pivot_window=5):
    obv = compute_obv(close, volume)
    bull_d, bear_d, _, _ = detect_pivot_divergence_v2(close, obv, lookback, pivot_window)
    return obv, bull_d & (wt1 < -20), bear_d & (wt1 > 20)


def detect_engulfing(close, opn, wt1, direction='bull', wt_thresh=20):
    body = (close - opn).abs()
    big_enough = body > body.rolling(20).mean() * 0.8
    if direction == 'bull':
        prev_bear = close.shift(1) < opn.shift(1)
        eng = prev_bear & (close > opn) & (opn <= close.shift(1)) & (close >= opn.shift(1))
        return eng & big_enough & (wt1 < -wt_thresh)
    else:
        prev_bull = close.shift(1) > opn.shift(1)
        eng = prev_bull & (close < opn) & (opn >= close.shift(1)) & (close <= opn.shift(1))
        return eng & big_enough & (wt1 > wt_thresh)


def detect_fib_levels(high, low, close, wt1, wt2, atr, direction='buy', swing_lb=60, confirm=5):
    """v2.8: ATR 기반 동적 허용범위"""
    sh = high.shift(confirm).rolling(swing_lb).max()
    sl = low.shift(confirm).rolling(swing_lb).min()
    fib_range = sh - sl
    tol = (atr / (fib_range + 1e-10)).clip(upper=0.05)  # ATR 비례, 최대 5%
    if direction == 'buy':
        f618 = sh - fib_range * 0.618
        f786 = sh - fib_range * 0.786
        near = (low <= f618 * (1 + tol)) & (low >= f786 * (1 - tol))
        return near & (wt1 < -30) & (wt1 > wt2)
    else:
        f618 = sl + fib_range * 0.618
        f786 = sl + fib_range * 0.786
        near = (high >= f618 * (1 - tol)) & (high <= f786 * (1 + tol))
        return near & (wt1 > 30) & (wt1 < wt2)


def detect_ma_cross(ma_fast, ma_slow):
    return ((ma_fast > ma_slow) & (ma_fast.shift(1) <= ma_slow.shift(1)),
            (ma_fast < ma_slow) & (ma_fast.shift(1) >= ma_slow.shift(1)))


def compute_supertrend(high, low, close, period=10, multiplier=3.0):
    tr = compute_true_range(high, low, close)
    atr = tr.rolling(period).mean()
    hl2 = (high + low) / 2
    up_vals = (hl2 + multiplier * atr).values.copy()
    dn_vals = (hl2 - multiplier * atr).values.copy()
    cl = close.values
    st_vals = np.full(len(close), np.nan)
    dir_vals = np.zeros(len(close), dtype=int)
    first_valid = period
    if first_valid >= len(close):
        return pd.Series(np.nan, index=close.index), pd.Series(0, index=close.index, dtype=int)
    dir_vals[first_valid] = 1
    st_vals[first_valid] = dn_vals[first_valid]
    for i in range(first_valid + 1, len(close)):
        if dir_vals[i - 1] == 1:
            dn_vals[i] = max(dn_vals[i], dn_vals[i - 1]) if not np.isnan(dn_vals[i - 1]) else dn_vals[i]
        else:
            up_vals[i] = min(up_vals[i], up_vals[i - 1]) if not np.isnan(up_vals[i - 1]) else up_vals[i]
        if dir_vals[i - 1] == 1:
            dir_vals[i], st_vals[i] = (-1, up_vals[i]) if cl[i] < dn_vals[i] else (1, dn_vals[i])
        else:
            dir_vals[i], st_vals[i] = (1, dn_vals[i]) if cl[i] > up_vals[i] else (-1, up_vals[i])
    return pd.Series(st_vals, index=close.index), pd.Series(dir_vals, index=close.index)


def detect_ema_pullback(close, high, low, volume, ema8, ema21, atr, wt1, wt2, direction='buy'):
    slope_ok = ema21 > ema21.shift(5) if direction == 'buy' else ema21 < ema21.shift(5)
    trend = ((ema8 > ema21) if direction == 'buy' else (ema8 < ema21)) & slope_ok
    side_ok = (close > ema21) if direction == 'buy' else (close < ema21)
    vol_ok = _vol_filter(volume, min_ratio=0.5)
    atr_r = atr / close

    if direction == 'buy':
        touched = (low <= ema8 * (1 + atr_r * 0.15)) & (low >= ema21 * (1 - atr_r * 0.25))
        bounced = close >= ema8
        wt_ok = (wt1 > wt1.shift(1)) & (wt1 > wt2) & (wt1 < 60)
    else:
        touched = (high >= ema8 * (1 - atr_r * 0.15)) & (high <= ema21 * (1 + atr_r * 0.25))
        bounced = close <= ema8
        wt_ok = (wt1 < wt1.shift(1)) & (wt1 < wt2) & (wt1 > -60)

    return trend & side_ok & touched & bounced & wt_ok & vol_ok


def detect_momentum_ignition(close, opn, volume, bb_band, atr, ema8, ema21, wt1,
                              direction='buy', body_atr_mult=1.5, vol_mult=2.5):
    """v2.8: WT 필터 추가 — 이미 과매수/과매도 극단에서 발화 방지"""
    body = (close - opn).abs()
    big_body = body > (atr * body_atr_mult)
    avg_vol = volume.rolling(20).mean()
    huge_vol = volume > (avg_vol * vol_mult)
    if direction == 'buy':
        wt_ok = wt1 < 50  # 과매수 구간에서 매수 점화 방지
        return (close > opn) & big_body & huge_vol & (close > bb_band) & (ema8 > ema21) & wt_ok
    else:
        wt_ok = wt1 > -50  # 과매도 구간에서 매도 점화 방지
        return (close < opn) & big_body & huge_vol & (close < bb_band) & (ema8 < ema21) & wt_ok


def detect_vwap_bounce(close, vwap_osc, wt1, wt2, volume, atr, direction='buy'):
    """v2.8: ATR 비례 동적 임계값"""
    vol_ok = _vol_filter(volume, min_ratio=0.7)
    atr_pct = (atr / close * 100).clip(lower=0.3, upper=3.0)
    dyn_thresh = (atr_pct * 0.3).clip(lower=0.3, upper=1.5)
    if direction == 'buy':
        crossed_up = (vwap_osc > 0) & (vwap_osc.shift(1) < -dyn_thresh)
        return crossed_up & (wt1 > wt2) & (wt1 < 30) & vol_ok
    else:
        crossed_dn = (vwap_osc < 0) & (vwap_osc.shift(1) > dyn_thresh)
        return crossed_dn & (wt1 < wt2) & (wt1 > -30) & vol_ok


def detect_parabolic_bottom(close, opn, wt1, bb_low, atr, wt_down):
    """v2.8 신규: Parabolic Top Sell의 대칭"""
    return (
        ((wt1 < -85) & (wt1 > wt1.shift(1)) &
         (close > opn) & (close > close.shift(1))) |
        ((close < bb_low - atr * 1.5) & (close > opn))
    )


def compute_htf_trend(close, ema8, ema21, ma50):
    return ((ema8 > ema21) & (ema21 > ema21.shift(5)),
            (close > ma50) & (ma50 > ma50.shift(10)))


# ──────────────────────────────────────────
# Scoring 함수들
# ──────────────────────────────────────────
def compute_confluence_score(df, decay_window=5, decay_factor=0.7):
    buy_map = {k: v['w'] for k, v in SIGNAL_REGISTRY.items() if v['dir'] == 'buy'}
    sell_map = {k: v['w'] for k, v in SIGNAL_REGISTRY.items() if v['dir'] == 'sell'}
    decay_kernel = np.array([decay_factor ** i for i in range(decay_window + 1)])
    s = np.zeros(len(df))
    buy_count = np.zeros(len(df))
    sell_count = np.zeros(len(df))

    for col, w in buy_map.items():
        if col in df.columns:
            raw = df[col].fillna(False).astype(float).values * w
            s += np.convolve(raw, decay_kernel, mode='full')[:len(raw)]
            buy_count += np.convolve(df[col].fillna(False).astype(float).values,
                                     np.ones(decay_window + 1), mode='full')[:len(raw)]
    for col, w in sell_map.items():
        if col in df.columns:
            raw = df[col].fillna(False).astype(float).values * w
            s -= np.convolve(raw, decay_kernel, mode='full')[:len(raw)]
            sell_count += np.convolve(df[col].fillna(False).astype(float).values,
                                      np.ones(decay_window + 1), mode='full')[:len(raw)]

    wt1 = df['WT1'].values
    s += np.where(wt1 < OS1, 1.0, 0.0) + np.where(wt1 < OS2, 0.5, 0.0)
    s -= np.where(wt1 > OB1, 1.0, 0.0) + np.where(wt1 > OB2, 0.5, 0.0)

    df['Confluence_Score'] = s
    df['Ultra_Buy'] = (s >= 6.0) | ((s >= 5.0) & (buy_count >= 3))
    df['Ultra_Sell'] = (s <= -6.0) | ((s <= -5.0) & (sell_count >= 3))
    df['Strong_Buy'] = (s >= 3.5) & (~df['Ultra_Buy'])
    df['Strong_Sell'] = (s <= -3.5) & (~df['Ultra_Sell'])
    return s


def compute_signal_proximity(wt1, wt2, rsi, mfi, rsi_mfi, stochk, strong_bull, strong_bear):
    buy_prox = pd.Series(0.0, index=wt1.index)
    sell_prox = pd.Series(0.0, index=wt1.index)
    wt_gap = (wt1 - wt2).abs()
    near_cross = wt_gap < 3.0
    wt_conv_up = (wt1 - wt2) > (wt1.shift(1) - wt2.shift(1))
    wt_conv_dn = (wt1 - wt2) < (wt1.shift(1) - wt2.shift(1))

    for prox, conds in [
        (buy_prox, [
            ((wt1 < -40) & near_cross, 30), ((wt1 < -40) & wt_conv_up & (wt_gap < 8), 15),
            (wt1 < OS2, 20), ((wt1 >= OS2) & (wt1 < -40), 10),
            (rsi < 35, 15), ((rsi >= 35) & (rsi < 45), 5),
            (mfi < 35, 15), ((mfi >= 35) & (mfi < 45), 5),
            (rsi_mfi < -5, 10), ((rsi_mfi >= -5) & (rsi_mfi < 0), 5),
            (stochk < 20, 10), ((stochk >= 20) & (stochk < 35), 5),
        ]),
        (sell_prox, [
            ((wt1 > 40) & near_cross, 30), ((wt1 > 40) & wt_conv_dn & (wt_gap < 8), 15),
            (wt1 > OB1, 20), ((wt1 <= OB1) & (wt1 > 40), 10),
            (rsi > 65, 15), ((rsi <= 65) & (rsi > 55), 5),
            (mfi > 65, 15), ((mfi <= 65) & (mfi > 55), 5),
            (rsi_mfi > 5, 10), ((rsi_mfi <= 5) & (rsi_mfi > 0), 5),
            (stochk > 80, 10), ((stochk <= 80) & (stochk > 65), 5),
        ]),
    ]:
        for cond, pts in conds:
            prox += np.where(cond, pts, 0)

    buy_prox = buy_prox.clip(upper=100)
    sell_prox = sell_prox.clip(upper=100)
    net = buy_prox - sell_prox

    buy_damp = np.where(strong_bear, 0.4, 0.55)
    sell_damp = np.where(strong_bull, 0.4, 0.55)
    return (pd.Series(np.where(net >= 0, buy_prox, buy_prox * buy_damp), index=wt1.index),
            pd.Series(np.where(net <= 0, sell_prox, sell_prox * sell_damp), index=wt1.index))


def compute_bias_score(meta, htf1_bull, htf2_bull):
    sc = 0.0
    for val, thresholds in [
        (meta['wt1'], [(-60, 3), (-53, 2), (0, 1), (53, -1), (60, -2), (999, -3)]),
        (meta['rsi'], [(-1, 0), (30, 2), (45, 1), (55, 0), (70, -1), (999, -2)]),
        (meta['mfi'], [(-1, 0), (30, 2), (45, 1), (55, 0), (70, -1), (999, -2)]),
    ]:
        for thresh, points in thresholds:
            if val <= thresh:
                sc += points; break
    mf = meta['mf_area']
    sc += 2 if mf < -5 else (1 if mf < 0 else (-2 if mf > 5 else (-1 if mf > 0 else 0)))
    stk = meta.get('stochk', 50)
    sc += 1.5 if stk < 20 else (0.5 if stk < 35 else (-1.5 if stk > 80 else (-0.5 if stk > 65 else 0)))
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
    mask = df[signal_col].fillna(False).values.astype(bool)
    if mask.sum() < min_samples:
        return None
    close = df[price_col].values
    stats = {'count': int(mask.sum())}
    for n in forward_days:
        if n >= len(close):
            stats[f'{n}d_avg'] = stats[f'{n}d_winrate'] = stats[f'{n}d_median'] = None
            continue
        fwd = np.full(len(close), np.nan)
        fwd[:len(close) - n] = (close[n:] - close[:len(close) - n]) / close[:len(close) - n] * 100
        valid = fwd[mask]; valid = valid[~np.isnan(valid)]
        if len(valid) >= min_samples:
            stats[f'{n}d_avg'] = float(np.mean(valid))
            stats[f'{n}d_winrate'] = float(np.sum(valid > 0) / len(valid) * 100)
            stats[f'{n}d_median'] = float(np.median(valid))
        else:
            stats[f'{n}d_avg'] = stats[f'{n}d_winrate'] = stats[f'{n}d_median'] = None
    return stats


def compute_all_signal_stats(df_valid):
    targets = {k: v['dir'] for k, v in SIGNAL_REGISTRY.items()}
    targets.update({'Ultra_Buy': 'buy', 'Strong_Buy': 'buy', 'Ultra_Sell': 'sell', 'Strong_Sell': 'sell'})
    return {sig: {**r, 'direction': d}
            for sig, d in targets.items()
            if (r := compute_signal_stats(df_valid, sig)) and r['count'] > 0}


# ──────────────────────────────────────────
# 지표 + 시그널 계산
# ──────────────────────────────────────────
def compute_indicators(df):
    for ma in [5, 20, 50, 100, 125, 200]:
        df[f'MA{ma}'] = df['Close'].rolling(ma).mean()
    df['EMA8'] = df['Close'].ewm(span=8, adjust=False).mean()
    df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()
    df['BB_Mid'] = df['MA20']
    std20 = df['Close'].rolling(20).std()
    df['BB_Up'] = df['BB_Mid'] + std20 * 2
    df['BB_Low'] = df['BB_Mid'] - std20 * 2
    df['ATR'] = compute_true_range(df['High'], df['Low'], df['Close']).rolling(14).mean()
    df['SuperTrend'], df['ST_Direction'] = compute_supertrend(df['High'], df['Low'], df['Close'])
    wt1, wt2, wt_up, wt_down = compute_wavetrend(df['High'], df['Low'], df['Close'])
    df['WT1'], df['WT2'], df['WT_Up'], df['WT_Down'] = wt1, wt2, wt_up, wt_down
    df['RSI'] = compute_rsi(df['Close'], 14)
    df['StochK'], df['StochD'] = compute_stoch_rsi(df['Close'])
    df['MFI'] = compute_mfi(df['High'], df['Low'], df['Close'], df['Volume'], 14)
    df['RSI_MFI'] = compute_rsi_mfi(df['High'], df['Low'], df['Close'], df['Volume'], 60)
    df['VWAP_Osc'] = compute_vwap_oscillator(df['Close'], df['Volume'])
    df['ADX'], df['Plus_DI'], df['Minus_DI'] = compute_adx(df['High'], df['Low'], df['Close'])
    df['OBV'], df['_OBV_Div_Buy_raw'], df['_OBV_Div_Sell_raw'] = detect_obv_divergence(
        df['Close'], df['Volume'], df['WT1'])
    df['KC_Upper'], df['KC_Mid'], df['KC_Lower'] = compute_keltner_channel(df['High'], df['Low'], df['Close'])
    return df


def detect_all_signals(df):
    H, L, C, O, V = df['High'], df['Low'], df['Close'], df['Open'], df['Volume']
    htf1_bull, htf2_bull = compute_htf_trend(C, df['EMA8'], df['EMA21'], df['MA50'])

    wt_up_near = _recent_true(df['WT_Up'], 2)
    wt_down_near = _recent_true(df['WT_Down'], 2)
    wt_up_recent = _recent_true(df['WT_Up'], 3)
    wt_down_recent = _recent_true(df['WT_Down'], 3)
    vol_ok = _vol_filter(V, 0.5)

    above_ma50 = C > df['MA50']
    below_ma50 = C < df['MA50']
    above_ma200 = C > df['MA200']
    below_ma200 = C < df['MA200']
    ma50_rising = df['MA50'] > df['MA50'].shift(5)
    ma50_falling = df['MA50'] < df['MA50'].shift(5)

    strong_bull = (df['ADX'] > 25) & (df['Plus_DI'] > df['Minus_DI']) & above_ma50
    strong_bear = (df['ADX'] > 25) & (df['Minus_DI'] > df['Plus_DI']) & below_ma50
    extreme_bull = strong_bull & above_ma200 & ma50_rising
    extreme_bear = strong_bear & below_ma200 & ma50_falling

    mf_bullish = df['RSI_MFI'] > -10
    mf_bearish = df['RSI_MFI'] < 10

    parabolic_blowoff = (
        ((df['WT1'] > 85) & (df['WT1'] < df['WT1'].shift(1)) & (C < O) & (C < C.shift(1))) |
        ((C > df['BB_Up'] + df['ATR'] * 1.5) & (C < O))
    )
    parabolic_bottom = detect_parabolic_bottom(C, O, df['WT1'], df['BB_Low'], df['ATR'], df['WT_Down'])

    st_flip_bear_raw = (df['ST_Direction'] == -1) & (df['ST_Direction'].shift(1) == 1)
    st_flip_bear_raw.iloc[:ST_MIN_BAR] = False
    st_bear_override = _recent_true(st_flip_bear_raw, 3)

    st_flip_bull_raw = (df['ST_Direction'] == 1) & (df['ST_Direction'].shift(1) == -1)
    st_flip_bull_raw.iloc[:ST_MIN_BAR] = False
    st_bull_override = _recent_true(st_flip_bull_raw, 3)

    sell_shield_bull = strong_bull & (~parabolic_blowoff) & (~st_bear_override)
    sell_shield_extreme = extreme_bull & (~parabolic_blowoff) & (~st_bear_override)
    buy_shield_bear = strong_bear & (~parabolic_bottom) & (~st_bull_override)
    buy_shield_extreme = extreme_bear & (~parabolic_bottom) & (~st_bull_override)

    # ── Core WT Signals ──
    df['Green_Dot_T1'] = (
        wt_up_near & (df['WT1'] <= OS1) &
        (df['RSI'] < 30) & (df['MFI'] < 30) & (df['RSI_MFI'] < 0) &
        (~buy_shield_extreme) & vol_ok
    )
    df['Green_Dot_T2'] = (
        wt_up_near & (df['WT1'] <= OS1) &
        ((df['RSI'] < 32) | (df['MFI'] < 32)) &
        ~df['Green_Dot_T1'] & (~buy_shield_bear) & vol_ok
    )
    _green_dot = df['Green_Dot_T1'] | df['Green_Dot_T2']

    df['Red_Dot_T1'] = (
        wt_down_near & (df['WT1'] >= OB1) &
        (df['RSI'] > 70) & (df['MFI'] > 70) & (df['RSI_MFI'] > 0) &
        (~sell_shield_extreme) & vol_ok
    )
    df['Red_Dot_T2'] = (
        wt_down_near & (df['WT1'] >= OB1) &
        ((df['RSI'] > 68) | (df['MFI'] > 68)) &
        ~df['Red_Dot_T1'] & (~sell_shield_bull) & vol_ok
    )
    _red_dot = df['Red_Dot_T1'] | df['Red_Dot_T2']

    df['Blue_Diamond'] = (
        (df['WT2'] <= 0) & wt_up_near & htf1_bull & htf2_bull &
        (~buy_shield_bear) & mf_bullish & vol_ok
    )
    df['Red_Diamond'] = (
        (df['WT2'] >= 0) & wt_down_near & ~htf1_bull & ~htf2_bull &
        (~sell_shield_bull) & mf_bearish & vol_ok
    )
    df['Green_Circle'] = wt_up_near & (df['WT1'] <= OS1) & ~_green_dot & (~buy_shield_bear) & vol_ok
    df['Red_Circle'] = wt_down_near & (df['WT1'] >= OB1) & ~_red_dot & (~sell_shield_bull) & vol_ok

    # ── Divergences ──
    bull_d, bear_d, hid_bull, hid_bear = detect_pivot_divergence_v2(C, df['WT1'], 60, 5, OS1, OB1)
    bull_d_recent = _recent_true(bull_d, 3)
    bear_d_recent = _recent_true(bear_d, 3)

    df['Gold_Dot'] = df['Green_Dot_T1'] & (df['WT1'] <= OS2) & bull_d_recent
    df['Blood_Diamond'] = df['Red_Dot_T1'] & (df['WT1'] >= OB2) & bear_d_recent
    df['Bull_Divergence'] = bull_d & wt_up_recent & ~_green_dot & ~df['Gold_Dot'] & (~buy_shield_bear) & vol_ok
    df['Bear_Divergence'] = bear_d & wt_down_recent & ~_red_dot & (~sell_shield_bull) & vol_ok
    df['Hidden_Bull_Div'] = hid_bull & (df['WT1'] < 0) & htf2_bull & (~buy_shield_extreme)
    df['Hidden_Bear_Div'] = hid_bear & (df['WT1'] > 0) & ~htf2_bull & (~sell_shield_extreme)

    # ── TTM Squeeze ──
    sq_on, sq_fb, sq_fs = detect_ttm_squeeze(
        df['BB_Up'], df['BB_Low'], df['KC_Upper'], df['KC_Lower'], C, H, L, df['KC_Mid'])
    df['Squeeze_On'] = sq_on
    df['Squeeze_Fire_Buy'] = sq_fb & (~buy_shield_bear) & vol_ok
    df['Squeeze_Fire_Sell'] = sq_fs & (~sell_shield_bull) & vol_ok

    # ── Volume Climax (v2.8: ATR body filter) ──
    df['Volume_Climax_Buy'], df['Volume_Climax_Sell'] = detect_volume_climax(
        C, O, V, df['WT1'], df['ATR'])

    # ── ADX Momentum ──
    adx_cross = (df['ADX'] > 20) & (df['ADX'].shift(1) <= 20)
    df['ADX_Momentum_Buy'] = adx_cross & (df['Plus_DI'] > df['Minus_DI']) & (df['WT1'] > df['WT2']) & vol_ok
    df['ADX_Momentum_Sell'] = adx_cross & (df['Minus_DI'] > df['Plus_DI']) & (df['WT1'] < df['WT2']) & vol_ok

    # ── Fib (v2.8: ATR dynamic tolerance) ──
    df['Fib_Bounce_Buy'] = detect_fib_levels(H, L, C, df['WT1'], df['WT2'], df['ATR'], 'buy') & (~buy_shield_bear) & vol_ok
    df['Fib_Resistance_Sell'] = detect_fib_levels(H, L, C, df['WT1'], df['WT2'], df['ATR'], 'sell') & (~sell_shield_bull) & vol_ok

    # ── Engulfing ──
    df['Bullish_Engulfing'] = detect_engulfing(C, O, df['WT1'], 'bull') & (~buy_shield_bear) & vol_ok
    df['Bearish_Engulfing'] = detect_engulfing(C, O, df['WT1'], 'bear') & (~sell_shield_bull) & vol_ok

    # ── MA Cross ──
    df['Golden_Cross'], df['Death_Cross'] = detect_ma_cross(df['MA50'], df['MA200'])

    # ── OBV Div ──
    df['OBV_Div_Buy'] = df['_OBV_Div_Buy_raw'] & (~buy_shield_extreme)
    df['OBV_Div_Sell'] = df['_OBV_Div_Sell_raw'] & (~sell_shield_extreme)

    # ── EMA Pullback ──
    for d in ['buy', 'sell']:
        col = f"EMA_Pullback_{'Buy' if d == 'buy' else 'Sell'}"
        df[col] = _apply_cooldown(detect_ema_pullback(
            C, H, L, V, df['EMA8'], df['EMA21'], df['ATR'], df['WT1'], df['WT2'], d), 7)

    # ── Momentum Ignition (v2.8: WT filter) ──
    df['Momentum_Ignition_Buy'] = _apply_cooldown(detect_momentum_ignition(
        C, O, V, df['BB_Up'], df['ATR'], df['EMA8'], df['EMA21'], df['WT1'], 'buy'), 10)
    df['Momentum_Ignition_Sell'] = _apply_cooldown(detect_momentum_ignition(
        C, O, V, df['BB_Low'], df['ATR'], df['EMA8'], df['EMA21'], df['WT1'], 'sell'), 10)

    # ── SuperTrend ──
    df['SuperTrend_Buy'] = st_flip_bull_raw
    df['SuperTrend_Sell'] = st_flip_bear_raw

    # ── Parabolic (v2.8: Buy 추가) ──
    raw_parabolic_sell = parabolic_blowoff & (
        (df['WT_Down'] | wt_down_recent) | ((C < O) & (C < C.shift(1))))
    df['Parabolic_Top_Sell'] = _apply_cooldown(raw_parabolic_sell, 5)
    df['Parabolic_Bottom_Buy'] = _apply_cooldown(
        parabolic_bottom & ((df['WT_Up'] | wt_up_recent) | ((C > O) & (C > C.shift(1)))), 5)

    # ── VWAP (v2.8: ATR dynamic threshold) ──
    df['VWAP_Bounce_Buy'] = _apply_cooldown(detect_vwap_bounce(
        C, df['VWAP_Osc'], df['WT1'], df['WT2'], V, df['ATR'], 'buy'), 7)
    df['VWAP_Reject_Sell'] = _apply_cooldown(detect_vwap_bounce(
        C, df['VWAP_Osc'], df['WT1'], df['WT2'], V, df['ATR'], 'sell'), 7)

    # ── Cooldowns ──
    for sig_col, cd in {'Squeeze_Fire_Buy': 5, 'Squeeze_Fire_Sell': 5,
                        'Bullish_Engulfing': 5, 'Bearish_Engulfing': 5,
                        'Fib_Bounce_Buy': 7, 'Fib_Resistance_Sell': 7,
                        'ADX_Momentum_Buy': 10, 'ADX_Momentum_Sell': 10}.items():
        if sig_col in df.columns:
            df[sig_col] = _apply_cooldown(df[sig_col], cd)

    compute_confluence_score(df)
    df['Buy_Proximity'], df['Sell_Proximity'] = compute_signal_proximity(
        df['WT1'], df['WT2'], df['RSI'], df['MFI'], df['RSI_MFI'], df['StochK'],
        strong_bull, strong_bear)

    df['Strong_Bull'], df['Strong_Bear'] = strong_bull, strong_bear
    df['Parabolic_Blowoff'] = parabolic_blowoff
    df['Parabolic_Bottom_Raw'] = parabolic_bottom
    df['ST_Bear_Override'] = st_bear_override
    df['Sell_Shield_Overridden'] = parabolic_blowoff | st_bear_override
    df['Buy_Shield_Overridden'] = parabolic_bottom | st_bull_override
    df['_HTF1_Bull'], df['_HTF2_Bull'] = htf1_bull, htf2_bull

    return df


# ──────────────────────────────────────────
# 차트 생성
# ──────────────────────────────────────────
def _add_highlight_zones(fig, mask_series, index, fillcolor, annotation_text=None, row=1):
    d = mask_series.astype(int).diff().fillna(0)
    starts = index[d == 1].tolist()
    ends = index[d == -1].tolist()
    if len(mask_series) > 0 and mask_series.iloc[0]:
        starts.insert(0, index[0])
    if len(mask_series) > 0 and mask_series.iloc[-1]:
        ends.append(index[-1])
    for s0, e0 in zip(starts, ends):
        kwargs = dict(x0=s0, x1=e0, fillcolor=fillcolor, line_width=0, row=row, col=1)
        if annotation_text:
            kwargs.update(annotation_text=annotation_text, annotation_position="top left",
                          annotation_font_size=8, annotation_font_color="#FF4444")
        fig.add_vrect(**kwargs)


def build_chart(df_chart, ticker, trend_regime, shield_status):
    mac = {5: "#ff9900", 20: '#f1c40f', 50: '#e74c3c', 100: '#9b59b6', 125: '#3498db', 200: '#2ecc71'}

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

    for ma in [5, 20, 50, 100, 125, 200]:
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart[f'MA{ma}'],
                                 line=dict(color=mac[ma], width=1.2), name=f'{ma}일선'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['EMA8'],
                             line=dict(color='#00FFFF', width=1.5, dash='dot'), name='EMA 8'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['EMA21'],
                             line=dict(color='#FF69B4', width=1.5, dash='dot'), name='EMA 21'), row=1, col=1)

    for mask_cond, color, name in [
        (df_chart['ST_Direction'] == 1, '#00E676', 'SuperTrend ▲'),
        (df_chart['ST_Direction'] == -1, '#FF1744', 'SuperTrend ▼'),
    ]:
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['SuperTrend'].where(mask_cond),
                                 line=dict(color=color, width=2), name=name, connectgaps=False), row=1, col=1)

    fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['BB_Up'],
                             line=dict(color='gray', width=1, dash='dot'), name='BB 상단'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['BB_Low'],
                             line=dict(color='gray', width=1, dash='dot'), name='BB 하단',
                             fill='tonexty', fillcolor='rgba(128,128,128,0.1)'), row=1, col=1)

    # Shield override zones
    for col, clr, txt in [
        ('Sell_Shield_Overridden', 'rgba(255,0,0,0.04)', '🔓Sell Shield OFF'),
        ('Buy_Shield_Overridden', 'rgba(0,255,0,0.04)', '🔓Buy Shield OFF'),
    ]:
        override_mask = df_chart.get(col, pd.Series(False, index=df_chart.index))
        if override_mask.any():
            _add_highlight_zones(fig, override_mask, df_chart.index, clr, txt, row=1)

    # Plot signals
    def _atr_at(sig_df):
        return df_chart.loc[sig_df.index, 'ATR'].fillna(df_chart['ATR'].median())

    for cn, cfg in ALL_CHART_SIGNALS.items():
        if cn not in df_chart.columns:
            continue
        if cn == 'Green_Dot_T1':
            sig = df_chart[df_chart[cn] & ~df_chart.get('Gold_Dot', False)]
        elif cn == 'Ultra_Buy':
            sig = df_chart[df_chart[cn] & ~df_chart.get('Gold_Dot', False)]
        elif cn == 'Ultra_Sell':
            sig = df_chart[df_chart[cn] & ~df_chart.get('Blood_Diamond', False)]
        else:
            sig = df_chart[df_chart[cn]]
        if sig.empty:
            continue
        yv = sig[cfg['base']] + _atr_at(sig) * cfg['atr_m']
        lw = 2 if cfg['sz'] >= 16 else (1.5 if cfg['sz'] >= 13 else 1)
        fig.add_trace(go.Scatter(
            x=sig.index, y=yv, mode='markers',
            marker=dict(symbol=cfg['sym'], size=cfg['sz'], color=cfg['clr'],
                        line=dict(width=lw, color='white' if 'open' not in cfg['sym'] else cfg['clr'])),
            name=f"{cfg['icon']} {cfg['label']}",
        ), row=1, col=1)

    # Volume
    br = df_chart['Close'] < df_chart['Open']
    fig.add_trace(go.Bar(x=df_chart.index, y=df_chart['Volume'],
                         marker_color=np.where(br, '#ef5350', '#26a69a').tolist(),
                         name="거래량", opacity=0.7), row=2, col=1)
    vcm = df_chart.get('Volume_Climax_Buy', pd.Series(False)) | df_chart.get('Volume_Climax_Sell', pd.Series(False))
    vcd = df_chart[vcm]
    if not vcd.empty:
        fig.add_trace(go.Bar(x=vcd.index, y=vcd['Volume'],
                             marker_color='#FFD700', name="Vol Climax", opacity=0.9), row=2, col=1)

    # WaveTrend
    fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['WT1'],
                             line=dict(color='#00E676', width=2), name="WT1"), row=3, col=1)
    fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['WT2'],
                             line=dict(color='#FF1744', width=1.5, dash='dot'), name="WT2"), row=3, col=1)
    wd = df_chart['WT1'] - df_chart['WT2']
    fig.add_trace(go.Bar(x=df_chart.index, y=wd,
                         marker_color=np.where(wd >= 0, '#00E676', '#FF1744').tolist(),
                         name="WT Hist", opacity=0.3), row=3, col=1)

    # WT signal dots
    for mask_col_list, clr in [
        (['Green_Circle', 'Green_Dot_T1', 'Green_Dot_T2', 'Gold_Dot'], '#00E676'),
        (['Red_Circle', 'Red_Dot_T1', 'Red_Dot_T2', 'Blood_Diamond'], '#FF1744'),
    ]:
        combined = pd.Series(False, index=df_chart.index)
        for mc in mask_col_list:
            combined |= df_chart.get(mc, pd.Series(False, index=df_chart.index))
        pts = df_chart[combined]
        if not pts.empty:
            fig.add_trace(go.Scatter(x=pts.index, y=pts['WT1'], mode='markers',
                                     marker=dict(symbol='circle', size=10, color=clr,
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
        _add_highlight_zones(fig, df_chart['Squeeze_On'], df_chart.index, "rgba(255,255,0,0.05)", None, row=3)

    # Money Flow
    rmfi = df_chart['RSI_MFI']
    fig.add_trace(go.Bar(x=df_chart.index, y=rmfi,
                         marker_color=np.where(rmfi >= 0, '#3ee145', '#ff3d2e').tolist(),
                         name="Money Flow", opacity=0.7), row=4, col=1)
    fig.add_hline(y=0, line_dash="solid", line_color="gray", line_width=1, row=4, col=1)

    # Confluence
    conf = df_chart['Confluence_Score']
    fig.add_trace(go.Bar(x=df_chart.index, y=conf,
                         marker_color=np.where(conf >= 3.5, '#00E676',
                                      np.where(conf <= -3.5, '#FF1744', '#FFC107')).tolist(),
                         name="Confluence", opacity=0.8), row=5, col=1)
    for lv, c, d in [(6, '#00E676', 'dash'), (-6, '#FF1744', 'dash'),
                      (3.5, '#00E676', 'dot'), (-3.5, '#FF1744', 'dot'), (0, 'gray', 'solid')]:
        fig.add_hline(y=lv, line_dash=d, line_color=c, line_width=1 if d == 'solid' else 0.8, row=5, col=1)

    shield_title = f" | {shield_status}" if shield_status else ""
    fig.update_layout(
        title=dict(text=f"📊 {ticker.upper()} | 💎 Market Cipher B+ V2.8 | {trend_regime}{shield_title}",
                   font=dict(size=14, color='#FAFAFA')),
        yaxis_title="USD", yaxis2_title="Vol", yaxis3_title="WT", yaxis4_title="MF", yaxis5_title="Conf",
        template="plotly_dark", margin=dict(l=0, r=0, t=50, b=0), height=1100, showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
                    font=dict(size=9, color='#AAAAAA'), bgcolor='rgba(0,0,0,0)'),
    )
    fig.update(layout_xaxis_rangeslider_visible=False)
    for ann in fig['layout']['annotations']:
        ann['font'] = dict(size=11, color='#888888')

    return fig


# ──────────────────────────────────────────
# 메타데이터 + 프롬프트 텍스트 생성
# ──────────────────────────────────────────
def build_metadata(df_chart, df_valid, ticker):
    latest = df_chart.iloc[-1]
    prev = df_chart.iloc[-2] if len(df_chart) >= 2 else latest
    p_chg = latest['Close'] - prev['Close']
    p_chg_pct = (p_chg / prev['Close']) * 100

    m4b = {k: float(latest[col]) for k, col in [
        ('wt1', 'WT1'), ('rsi', 'RSI'), ('mfi', 'MFI'),
        ('mf_area', 'RSI_MFI'), ('stochk', 'StochK')]}
    htf1_b = bool(latest.get('_HTF1_Bull', False))
    htf2_b = bool(latest.get('_HTF2_Bull', False))
    bias, bscore = compute_bias_score(m4b, htf1_b, htf2_b)
    conf_now = float(df_chart['Confluence_Score'].iloc[-1])

    if latest.get('Strong_Bull', False):
        trend_regime = 'STRONG BULL 🟢'
    elif latest.get('Strong_Bear', False):
        trend_regime = 'STRONG BEAR 🔴'
    else:
        trend_regime = 'NEUTRAL ⚪'

    shield_parts = []
    if latest.get('Parabolic_Blowoff', False):
        shield_parts.append('🌡️ PARABOLIC TOP')
    if latest.get('ST_Bear_Override', False):
        shield_parts.append('📉 ST BEAR')
    if latest.get('Parabolic_Bottom_Raw', False):
        shield_parts.append('🧊 PARABOLIC BOT')
    if latest.get('Buy_Shield_Overridden', False) and not shield_parts:
        shield_parts.append('🔓 BUY SHIELD OFF')
    if latest.get('Sell_Shield_Overridden', False) and '🌡️' not in str(shield_parts) and '📉' not in str(shield_parts):
        shield_parts.append('🔓 SELL SHIELD OFF')
    shield_status = ' + '.join(shield_parts)

    sig_checks = [(k, v['icon'], v['label'], v['dir']) for k, v in ALL_CHART_SIGNALS.items()]
    recent_signals = []
    for ir, row in df_chart.tail(30).iterrows():
        d_str = ir.strftime('%m/%d')
        for col, icon, lbl, side in sig_checks:
            if row.get(col, False):
                recent_signals.append((icon, lbl, d_str, side))

    all_stats = compute_all_signal_stats(df_valid)

    return {
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
        'trend_regime': trend_regime, 'shield_status': shield_status,
        'supertrend_dir': int(latest.get('ST_Direction', 0)),
        'supertrend_val': float(latest.get('SuperTrend', 0)),
        'ema8': float(latest.get('EMA8', 0)), 'ema21': float(latest.get('EMA21', 0)),
        'bb_up': float(latest.get('BB_Up', 0)), 'bb_low': float(latest.get('BB_Low', 0)),
        'ma50': float(latest.get('MA50', 0)), 'ma200': float(latest.get('MA200', 0)),
    }, trend_regime, shield_status


def build_prompt_text(df_chart, meta):
    latest = df_chart.iloc[-1]
    rd = df_chart.tail(60)
    ps = ", ".join([f"'{d.strftime('%Y-%m-%d')}:{r['Close']:.2f}'" for d, r in rd.iterrows()])

    sig_checks = [(k, f"{v['icon']} {v['label']}") for k, v in ALL_CHART_SIGNALS.items()]
    sl = []
    for ir, row in df_chart.tail(30).iterrows():
        dd = ir.strftime('%Y-%m-%d')
        for c, l in sig_checks:
            if row.get(c, False):
                sl.append(f"{l} {dd}")
    st_text = "\n".join(sl) if sl else "최근 30일 내 주요 시그널 없음"

    bp, sp = meta['buy_proximity'], meta['sell_proximity']
    prox_text = f"Buy Proximity={bp:.0f}%, Sell Proximity={sp:.0f}%"
    if bp >= 60: prox_text += " ⚠️ 매수 시그널 임박!"
    if sp >= 60: prox_text += " ⚠️ 매도 시그널 임박!"
    sq_text = "Squeeze ON (변동성 응축→폭발 임박)" if meta['squeeze_on'] else "Squeeze OFF"
    st_dir_text = f"BULL ▲ ({meta['supertrend_val']:.2f})" if meta['supertrend_dir'] == 1 else f"BEAR ▼ ({meta['supertrend_val']:.2f})"
    shield_text = f"Shield Override: {meta['shield_status']}" if meta['shield_status'] else "Shield Override: NONE"

    inds = (
        f"WT1={latest['WT1']:.1f}, WT2={latest['WT2']:.1f}, RSI={latest['RSI']:.1f}, MFI={latest['MFI']:.1f}, "
        f"StochK={latest['StochK']:.1f}, StochD={latest['StochD']:.1f}, "
        f"VWAP_Osc={latest['VWAP_Osc']:.2f}, MF_Area={latest['RSI_MFI']:.1f}, "
        f"ADX={latest['ADX']:.1f}, +DI={latest['Plus_DI']:.1f}, -DI={latest['Minus_DI']:.1f}, "
        f"EMA8={latest['EMA8']:.2f}, EMA21={latest['EMA21']:.2f}, "
        f"SuperTrend={st_dir_text}, BB=[{meta['bb_up']:.2f}/{meta['bb_low']:.2f}], "
        f"MA50={meta['ma50']:.2f}, MA200={meta['ma200']:.2f}, "
        f"Confluence={meta['confluence_score']:.1f}, Bias={meta['overall_bias']}({meta['bias_score']:.1f}), "
        f"Trend={meta['trend_regime']}, {shield_text}, {prox_text}, {sq_text}"
    )

    # v2.8: 백테스트 통계 프롬프트 포함
    stats = meta.get('all_signal_stats', {})
    stats_text = ""
    if stats:
        lines = []
        for sn, sv in sorted(stats.items(), key=lambda x: x[1]['count'], reverse=True)[:10]:
            wr = sv.get('10d_winrate')
            avg = sv.get('10d_avg')
            if wr is not None:
                lines.append(f"  {sn}: {sv['count']}회, 10일 승률 {wr:.0f}%, 평균 {avg:+.1f}%")
        if lines:
            stats_text = "\n📌 [백테스트 통계 (2년, 상위 10)]\n" + "\n".join(lines)

    return f"{ps}\n\n📌 [지표]\n{inds}\n\n📌 [시그널]\n{st_text}{stats_text}"


# ──────────────────────────────────────────
# 통합 분석 함수
# ──────────────────────────────────────────
def get_yfinance_data_and_chart(ticker, chart_period_days=252):
    try:
        df = compute_and_cache(ticker)
        if df is None or df.empty:
            return None, "최근 주가 데이터 없음", None

        df_valid = df.dropna(subset=['WT1', 'WT2'])
        df_chart = df_valid.tail(chart_period_days).copy()
        if df_chart.empty:
            return None, "차트 데이터 부족", None

        meta, trend_regime, shield_status = build_metadata(df_chart, df_valid, ticker)
        fig = build_chart(df_chart, ticker, trend_regime, shield_status)
        enhanced = build_prompt_text(df_chart, meta)

        return fig, enhanced, meta
    except Exception as e:
        return None, f"주가 데이터 로딩 실패: {e}", None


# ──────────────────────────────────────────
# UI 렌더 헬퍼
# ──────────────────────────────────────────
_IND_THRESHOLDS = {
    'wt1': [(-53, '극과매도'), (-20, '과매도'), (20, '중립'), (53, '과매수'), (999, '극과매수')],
    'rsi': [(30, '과매도'), (45, '약세'), (55, '중립'), (70, '강세'), (999, '과매수')],
    'mfi': [(30, '과매도'), (45, '약세'), (55, '중립'), (70, '강세'), (999, '과매수')],
    'stochk': [(20, '바닥'), (80, ''), (999, '천장')],
}

def _indicator_label(name, value):
    for thresh, label in _IND_THRESHOLDS.get(name, []):
        if value <= thresh:
            return label
    return ''


def _cls(val, lo, hi):
    return 'ind-bullish' if val < lo else ('ind-bearish' if val > hi else 'ind-neutral')


def render_price_header(meta):
    chg = meta['price_change']
    chg_pct = meta['price_change_pct']
    chg_cls = 'price-change-up' if chg >= 0 else 'price-change-down'
    chg_ico = '▲' if chg >= 0 else '▼'
    vr = meta['volume'] / meta['avg_volume'] if meta['avg_volume'] else 0
    cv = meta.get('confluence_score', 0)
    st_dir = meta.get('supertrend_dir', 0)
    shield = meta.get('shield_status', '')

    ind_specs = [
        (_cls(meta['wt1'], -20, 20), f"WT: {meta['wt1']:.0f} {_indicator_label('wt1', meta['wt1'])}"),
        (_cls(meta['rsi'], 40, 60), f"RSI: {meta['rsi']:.0f} {_indicator_label('rsi', meta['rsi'])}"),
        (_cls(meta['mfi'], 40, 60), f"MFI: {meta['mfi']:.0f} {_indicator_label('mfi', meta['mfi'])}"),
        ('ind-bullish' if meta['mf_area'] < 0 else ('ind-bearish' if meta['mf_area'] > 0 else 'ind-neutral'), f"MF: {meta['mf_area']:.1f}"),
        ('ind-bullish' if vr > 1.5 else 'ind-neutral', f"Vol: {vr:.1f}x"),
        ('ind-bullish' if meta['adx'] > 25 else 'ind-neutral', f"ADX: {meta['adx']:.0f}"),
        (_cls(meta['stochk'], 30, 70), f"StK: {meta['stochk']:.0f} {_indicator_label('stochk', meta['stochk'])}"),
        ('ind-bullish' if cv >= 3.5 else ('ind-bearish' if cv <= -3.5 else 'ind-neutral'), f"Conf: {cv:.1f}"),
        ('ind-bullish' if st_dir == 1 else 'ind-bearish', f"ST: {'▲' if st_dir == 1 else '▼'}"),
    ]

    indicators_html = "".join([f"<span class='indicator-mini {c}'>{lbl}</span>" for c, lbl in ind_specs])
    if shield:
        indicators_html += f"<span class='indicator-mini ind-bearish' style='font-weight:700;'>🔓 {shield}</span>"

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
        <div style="margin-top:10px;display:flex;gap:6px;flex-wrap:wrap;">{indicators_html}</div>
    </div>""", unsafe_allow_html=True)


def render_bias_badge(meta):
    bias = meta['overall_bias']; sc = meta.get('bias_score', 0); cv = meta.get('confluence_score', 0)
    bias_styles = {
        'STRONG BUY': ('rgba(0,230,118,0.2)', '#00E676', '🟢🟢'),
        'BUY': ('rgba(0,230,118,0.12)', '#00E676', '🟢'),
        'STRONG SELL': ('rgba(255,23,68,0.2)', '#FF1744', '🔴🔴'),
        'SELL': ('rgba(255,23,68,0.12)', '#FF1744', '🔴'),
    }
    bg, clr, ico = bias_styles.get(bias, ('rgba(255,193,7,0.12)', '#FFC107', '🟠'))
    cc = '#00E676' if cv >= 3.5 else ('#FF1744' if cv <= -3.5 else '#FFC107')
    gauge_pct = max(0, min(100, ((sc + 13.0) / 26.0) * 100))

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
    alerts = []
    bp, sp = meta.get('buy_proximity', 0), meta.get('sell_proximity', 0)
    if bp >= 70: alerts.append(('🟢⚡ 매수 시그널 매우 임박!', '#00E676', bp))
    elif bp >= 50: alerts.append(('🟢 매수 시그널 접근 중', '#69F0AE', bp))
    if sp >= 70: alerts.append(('🔴⚡ 매도 시그널 매우 임박!', '#FF1744', sp))
    elif sp >= 50: alerts.append(('🔴 매도 시그널 접근 중', '#FF5252', sp))
    if meta.get('squeeze_on', False):
        alerts.append(('💥 Squeeze ON — 변동성 폭발 임박', '#FFFF00', 80))
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

    # v2.8: 백테스트 승률 인라인 표시
    all_stats = meta.get('all_signal_stats', {})

    for d_str in reversed(date_groups):
        group = date_groups[d_str]
        buy_c = sum(1 for _, _, s in group if s == 'buy')
        sell_c = sum(1 for _, _, s in group if s == 'sell')
        ct = 'signal-card-buy' if buy_c > sell_c else ('signal-card-sell' if sell_c > buy_c else 'signal-card-neutral')
        sig_parts = []
        for i, l, s in group:
            cls_name = "ind-bullish" if s == "buy" else "ind-bearish"
            # Find matching stat by label
            stat_hint = ""
            for sn, sv in all_stats.items():
                cfg = ALL_CHART_SIGNALS.get(sn, {})
                if cfg.get('label') == l:
                    wr = sv.get('10d_winrate')
                    if wr is not None:
                        stat_hint = f" ({wr:.0f}%)"
                    break
            sig_parts.append(f'<span class="indicator-mini {cls_name}">{i} {l}{stat_hint}</span>')
        sig_html = " ".join(sig_parts)
        st.markdown(f"""<div class="signal-card {ct}">
            <div style="display:flex;justify-content:space-between;align-items:center;">
                <span style="font-weight:700;font-size:0.9rem;color:#FAFAFA;">📅 {d_str}</span>
                <span style="color:#888;font-size:0.75rem;">{len(group)}개 신호</span>
            </div>
            <div style="margin-top:6px;display:flex;gap:4px;flex-wrap:wrap;">{sig_html}</div>
        </div>""", unsafe_allow_html=True)


def render_signal_stats(meta):
    with st.expander("📊 시그널 백테스트 통계 (과거 2년, 최소 5회 이상)", expanded=True):
        alls = meta.get('all_signal_stats', {})
        if not alls:
            st.caption("통계 데이터 없음 (최소 발생 횟수 미달)"); return

        def _render_side(title, data, is_sell=False):
            st.markdown(f"##### {title}")
            for sn, sv in sorted(data.items(), key=lambda x: x[1]['count'], reverse=True):
                wr = sv.get('10d_winrate'); av = sv.get('10d_avg')
                if wr is None: continue
                if is_sell:
                    rate = 100 - wr
                    clr = '#FF1744' if rate > 55 else ('#FFC107' if rate > 45 else '#00E676')
                    label = f"10일 후 하락 확률 <span style='color:{clr}'>{rate:.0f}%</span>"
                else:
                    clr = '#00E676' if wr > 55 else ('#FFC107' if wr > 45 else '#FF1744')
                    label = f"10일 상승 <span style='color:{clr}'>{wr:.0f}%</span>"
                icon = ALL_CHART_SIGNALS.get(sn, {}).get('icon', '')
                st.markdown(f"<span style='font-size:0.82rem;'>{icon} **{sn}** ({sv['count']}회) · "
                            f"{label} · 평균 {av:+.1f}%</span>", unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            _render_side("🟢 BUY 시그널", {k: v for k, v in alls.items() if v['direction'] == 'buy'})
        with c2:
            _render_side("🔴 SELL 시그널", {k: v for k, v in alls.items() if v['direction'] == 'sell'}, True)


def render_inline_analysis(msg):
    meta, fig = msg.get('meta'), msg.get('fig')
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
    st.markdown("<p style='color:#888;font-size:0.8rem;'>AI 주가 분석 · Market Cipher B+ v2.8</p>", unsafe_allow_html=True)
    st.markdown("---")

    st.markdown("### 📅 차트 기간")
    chart_period = st.radio("표시 기간", ['3개월', '6개월', '1년', '2년'],
                            index=2, horizontal=True, key="chart_period_radio")
    chart_days = {'3개월': 63, '6개월': 126, '1년': 252, '2년': 504}[chart_period]

    # v2.8: 기간 변경 시 자동 재분석
    if 'prev_chart_period' not in st.session_state:
        st.session_state.prev_chart_period = chart_period
    if chart_period != st.session_state.prev_chart_period:
        st.session_state.prev_chart_period = chart_period
        if st.session_state.get('last_ticker'):
            st.session_state._auto_reanalyze = True
            st.rerun()

    st.markdown("---")

    # v2.8: 퀵 티커 버튼
    st.markdown("### ⚡ 빠른 분석")
    quick_cols = st.columns(4)
    for idx, t in enumerate(QUICK_TICKERS):
        with quick_cols[idx % 4]:
            if st.button(t, key=f"quick_{t}", type="secondary", use_container_width=True):
                st.session_state._quick_ticker = t
                st.rerun()

    st.markdown("---")

    if st.button("🗑️ 대화 초기화", use_container_width=True, type="secondary"):
        for key in ['messages', 'pending_ai_ticker', 'pending_ai_prompt', 'last_ticker']:
            st.session_state[key] = [{"role": "assistant", "type": "text",
                                       "content": "안녕하세요! 💎 **CipherX** 입니다.\n\n분석할 **티커명**을 입력하세요."}] if key == 'messages' else None
        st.rerun()
    st.markdown("---")

    st.markdown("### 📖 신호 가이드")
    for expander_title, sig_list in [
        ("🟢 매수 신호 (BUY)", [k for k, v in ALL_CHART_SIGNALS.items() if v['dir'] == 'buy']),
        ("🔴 매도 신호 (SELL)", [k for k, v in ALL_CHART_SIGNALS.items() if v['dir'] == 'sell']),
    ]:
        with st.expander(expander_title, expanded=False):
            for k in sig_list:
                info = ALL_CHART_SIGNALS[k]
                st.markdown(f"**{info['icon']} {info['label']}** · <span style='color:#888;font-size:0.82rem;'>{info.get('kor', '')}</span>",
                            unsafe_allow_html=True)
                st.caption(info.get('desc', ''))
                st.markdown("<hr style='border:none;border-top:1px solid #222;margin:4px 0;'>", unsafe_allow_html=True)

    with st.expander("🛡️ 추세 필터 시스템", expanded=False):
        st.markdown("""
**추세 레짐**: STRONG BULL 🟢 / STRONG BEAR 🔴 / NEUTRAL ⚪

**🔓 쉴드 오버라이드**:
- Parabolic Top/Bottom → 매도/매수 쉴드 강제 해제
- SuperTrend Flip → 해당 방향 쉴드 해제

**V2.8**: Parabolic Bottom 추가 · WT필터 Momentum Ignition · ATR동적 Fib/VWAP · Volume Climax 캔들크기 검증 · 백테스트 통계 AI전달
        """)

    with st.expander("📊 지표 해석 가이드", expanded=False):
        st.markdown("""
**WaveTrend**: WT1 < -53 과매도 · WT1 > 53 과매수 · 교차 = 시그널
**RSI/MFI**: < 30 과매도 · > 70 과매수
**Confluence**: ≥6 Ultra Buy · ≤-6 Ultra Sell
**Squeeze**: ON = 변동성 응축 → 폭발 대기
**VWAP**: 0 위 = 강세, 0 아래 = 약세 (기관 기준)
**SuperTrend**: ▲ = 강세지지 · ▼ = 약세저항
        """)

    st.markdown("---")
    st.markdown("<p style='color:#555;font-size:0.7rem;text-align:center;'>CipherX v2.8 · Enhanced Signal Engine</p>", unsafe_allow_html=True)


# ──────────────────────────────────────────
# 세션 초기화
# ──────────────────────────────────────────
if 'messages' not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "type": "text",
         "content": "안녕하세요! 💎 **CipherX** 입니다.\n\n분석할 **티커명**을 입력하세요. 채팅처럼 자유롭게 여러 종목을 이어서 분석할 수 있습니다."}
    ]
for key in ['pending_ai_ticker', 'pending_ai_prompt', 'last_ticker']:
    if key not in st.session_state:
        st.session_state[key] = None


# ──────────────────────────────────────────
# 프롬프트
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
아래 **제공된 데이터만으로** 심층 주가 분석 보고서를 작성하세요.
데이터에 없는 정보(옵션, 공매도 등)는 추측하지 말고 "데이터 미제공"으로 표기하세요.

💎 **시그널 신뢰도 계층 구조** (추세 필터 + 쿨다운 적용됨):
- **Tier 0** (Parabolic Top/Bottom, SuperTrend Flip): 추세 무관 + 쉴드 강제 해제. 즉시 경고.
- **Tier 1** (Gold Dot, Blood Diamond): 추세 무관, 항상 유효. 극단적 수렴.
- **Tier 2** (T1, Divergence, Momentum Ignition): 극단 역추세에서만 억제됨. 높은 신뢰도.
- **Tier 3** (T2, Diamond, Circle, EMA Pullback 등): 강한 역추세에서 억제됨.
→ ⚠️ **쿨다운이 적용되어 남은 시그널은 이미 높은 신뢰도**입니다.

🔥 **Confluence Score** (시간 감쇠 적용):
- ≥6: Ultra Buy (극단적 매수 수렴) | 3.5~6: Strong Buy | 0~3.5: 약한 매수 편향
- ≤-6: Ultra Sell | -6~-3.5: Strong Sell | -3.5~0: 약한 매도 편향

📡 **Proximity Alert** 해석:
- ≥70%: 시그널 발동 매우 임박 | 50~70%: 접근 중 | <50%: 아직 거리 있음

🛡️ **Shield Override** 해석:
- NONE: 추세 필터가 정상 작동 중
- PARABOLIC TOP: 극단적 과열 감지 → 매도 쉴드 해제 (강한 경고)
- PARABOLIC BOT: 극단적 과매도 → 매수 쉴드 해제 (반등 가능성)
- ST BEAR/BULL: 슈퍼트렌드 전환 → 해당 방향 쉴드 해제

📊 **백테스트 통계**: 과거 2년간 각 시그널의 실제 10일 후 승률/평균수익률이 포함되어 있습니다.
→ 승률 60% 이상 시그널은 높은 신뢰도, 50% 미만은 주의 필요로 해석하세요.

---
━━━━━━━━━━━━━
【 📥 Input Data 】
━━━━━━━━━━━━━
[티커: {ticker_value}]

📌 [주가 + 지표 + 시그널 + 통계]
{phist}

📌 [SwingTradeBot]
{scraped if scraped else '데이터 미제공'}

---
━━━━━━━━━━━━━
【 ✍️ Guidelines 】
━━━━━━━━━━━━━
① 한국어, 전문적이면서 이해하기 쉽게
② 확신형 어조, 이모티콘(🔵긍정 🔴부정 🟠중간)
③ Trend Regime + 시그널 Tier + 백테스트 통계를 연계 분석
④ 시나리오별 신뢰도(높음/중간/낮음) + 근거 (추측 확률% 금지)
⑤ 지지/저항 수준은 MA, BB, SuperTrend, Fib 레벨에서 도출
⑥ Proximity Alert와 Squeeze 상태를 시나리오에 반영
⑦ Shield Override 상태의 의미를 분석에 반영

━━━━━━━━━━━━━
【 📄 Output Format 】
━━━━━━━━━━━━━

[🔵/🔴/🟠] [{ticker_value}] 분석: [핵심 한 줄]
[날짜], 전일 대비 [변동률]% [방향].

---
### 내용 요약
[3~4문장]

---
### 🛡️ 추세 상태 & 시그널 신뢰도
* 현재 추세 레짐 · 시그널 필터 상태 · 신뢰도 종합 · Shield 상태

---
### 💎 마켓 사이퍼 B+ 시그널 분석
* WaveTrend / Money Flow / Confluence / Proximity / 최근 시그널 + 백테스트 신뢰도

---
### 주가 및 거래량 분석
* 거래량 배수 · 스마트머니 해석

---
### 장중 기술적 지표
* 패턴, ATR, ADX, TTM Squeeze, MA Cross, SuperTrend, VWAP

---
### 지지선 및 저항선
* 지지선: [가격들 + 근거] · 저항선: [가격들 + 근거]

---
### 주가변동이유 및 이벤트
- (SwingTradeBot 데이터 기반, 없으면 "데이터 미제공")

---
### 종합해석 및 전망
* 🔵 Bullish: [조건] → [목표가]. 신뢰도: 높음/중간/낮음
* 🟠 Base: [시나리오]. 신뢰도: 높음/중간/낮음
* 🔴 Bearish: [조건] → [목표가]. 신뢰도: 높음/중간/낮음

전략: 진입가 / 손절 / 분할매도 1차·2차

---
### 결론
[🔵/🔴/🟠] [2~3문장]

### 다음 거래일 전망
[🔵/🔴/🟠] 예상 방향 · 근거 · 종합 등급"""


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
            tn = msg.get("ticker", "report").upper()
            st.download_button("📥 다운로드 (.md)", key=f"dl_{i}",
                               data=msg["content"].encode('utf-8'),
                               file_name=f"{tn}_Report_{ns}.md", mime="text/markdown",
                               use_container_width=True)
        else:
            st.markdown(msg.get("content", ""))


# ──────────────────────────────────────────
# 재분석 바 + AI 분석 버튼
# ──────────────────────────────────────────
def _run_ai_analysis():
    ticker_pending = st.session_state.pending_ai_ticker
    prompt_pending = st.session_state.pending_ai_prompt
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

    if not _is_valid_ticker_format(ticker_value):
        st.session_state.messages.append({"role": "user", "type": "text", "content": ticker_value})
        st.session_state.messages.append({
            "role": "assistant", "type": "text",
            "content": f"⚠️ **{ticker_value}** — 올바른 티커 형식이 아닙니다.\n\n"
                       f"영문 1~5자를 입력하세요 (예: AAPL, TSLA, BRK.B)"
        })
        st.rerun()
        return

    if not validate_ticker(ticker_value):
        st.session_state.messages.append({"role": "user", "type": "text", "content": ticker_value})
        st.session_state.messages.append({
            "role": "assistant", "type": "text",
            "content": f"⚠️ **{ticker_value}** — 유효하지 않은 티커입니다.\n\n"
                       f"Yahoo Finance에서 해당 종목을 찾을 수 없습니다. 티커명을 확인해주세요."
        })
        st.rerun()
        return

    st.session_state.messages.append({"role": "user", "type": "text", "content": ticker_value})
    st.session_state.last_ticker = ticker_value

    with st.chat_message("assistant", avatar="✨"):
        pg = st.progress(0, text=f"🌐 {ticker_value} 데이터 수집 시작...")
        pg.progress(15, text="📡 SwingTradeBot 크롤링 중...")
        scraped = get_stock_data(ticker_value)
        pg.progress(40, text="📊 Yahoo Finance 주가 로딩 중...")
        cfig, phist, meta = get_yfinance_data_and_chart(ticker_value, chart_period_days=chart_days)
        pg.progress(70, text="💎 마켓 사이퍼 + 시그널 분석 중...")
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
                "content": f"⚠️ **{ticker_value}** 데이터 로딩 실패.\n\n"
                           f"가능한 원인: 상장폐지, 데이터 미제공, 네트워크 오류.\n"
                           f"다른 티커를 입력해보세요.",
            })
            st.rerun()


if st.session_state.last_ticker:
    lt = st.session_state.last_ticker
    c1, c2 = st.columns([3, 1])
    with c1:
        if st.session_state.pending_ai_ticker and st.session_state.pending_ai_prompt:
            if st.button(f"🚀 {st.session_state.pending_ai_ticker.upper()} AI 심층 분석 시작",
                         type="primary", use_container_width=True):
                _run_ai_analysis()
    with c2:
        if st.button(f"🔄 {lt} 재분석", type="secondary", use_container_width=True, key="reanalyze"):
            process_ticker(lt)
elif st.session_state.pending_ai_ticker and st.session_state.pending_ai_prompt:
    if st.button(f"🚀 {st.session_state.pending_ai_ticker.upper()} AI 심층 분석 시작",
                 type="primary", use_container_width=True):
        _run_ai_analysis()


if ticker_input := st.chat_input("분석할 티커를 입력하세요 (예: IREN, TSLA, AAPL, BRK.B)"):
    process_ticker(ticker_input)