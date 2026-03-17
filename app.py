# ══════════════════════════════════════════════════════════════
#  CipherX V12.0 — Optimized Judgment-First Architecture
#  PART 1/4: 설정 + 상수 + 시그널 정의 + 유틸리티
# ══════════════════════════════════════════════════════════════

from __future__ import annotations
import streamlit as st
import google.generativeai as genai
import time
import re
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Literal
from enum import Enum
from functools import lru_cache

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
# 상수 중앙화
# ──────────────────────────────────────────
class Config:
    """전역 설정"""
    # WaveTrend 임계값
    WT_OB1, WT_OB2 = 53, 60
    WT_OS1, WT_OS2 = -53, -60
    
    # RSI/MFI 임계값
    RSI_OB, RSI_OS = 70, 30
    MFI_OB, MFI_OS = 70, 30
    STOCH_OB, STOCH_OS = 80, 20
    
    # 판단 임계값
    STRONG_THRESHOLD = 15.0
    NORMAL_THRESHOLD = 10.0
    WATCH_THRESHOLD = 5.0
    
    # 판단 비율 요구사항
    STRONG_RATIO = 1.8
    NORMAL_RATIO = 1.3
    
    # 민감도 (1.0 = 기본, <1.0 = 더 예민, >1.0 = 덜 예민)
    BUY_SENSITIVITY = 1.0      # 🆕 추가
    SELL_SENSITIVITY = 0.9     # 매도는 약간 더 예민
    
    # 레이어 최대 점수
    LAYER_MAX = {
        'Trend': 8, 'Momentum': 8, 'Candle': 6,
        'BB': 5, 'Volume': 5, 'MF': 5, 'Pattern': 8
    }
    
    ST_MIN_BAR = 12
    DEFAULT_COOLDOWN = 5


class Colors:
    """UI 색상"""
    BUY = '#00E676'
    BUY_LIGHT = '#69F0AE'
    SELL = '#FF1744'
    SELL_LIGHT = '#FF5252'
    NEUTRAL = '#FFC107'
    NEUTRAL_LIGHT = '#FCD34D'
    BG_DARK = '#0B0E14'
    TEXT = '#E8ECF1'
    TEXT_MUTED = '#64748B'


# ──────────────────────────────────────────
# 시그널 방향 열거형
# ──────────────────────────────────────────
class Direction(str, Enum):
    BUY = 'buy'
    SELL = 'sell'


# ──────────────────────────────────────────
# 시그널 데이터 클래스
# ──────────────────────────────────────────
@dataclass(frozen=True)
class Signal:
    """시그널 정의"""
    weight: float
    direction: Direction
    icon: str
    label: str
    symbol: str
    size: int
    color: str
    base: Literal['Low', 'High']
    atr_mult: float
    kor: str
    desc: str
    cooldown: int = Config.DEFAULT_COOLDOWN
    
    @property
    def is_buy(self) -> bool:
        return self.direction == Direction.BUY


def _sig(w, d, icon, label, sym, sz, clr, base, atr_m, kor, desc, cd=5):
    """시그널 생성 헬퍼"""
    return Signal(w, Direction(d), icon, label, sym, sz, clr, base, atr_m, kor, desc, cd)


# ──────────────────────────────────────────
# 시그널 레지스트리 (통합 + 정리)
# ──────────────────────────────────────────
SIGNAL_REGISTRY: Dict[str, Signal] = {
    # ═══ MCB+ 매수 (핵심) ═══
    'Gold_Dot':              _sig(3.0,'buy','🏆','GOLD DOT','circle',18,'#FFD700','Low',-3.0,'최강 매수','RSI<30+MFI<30+WT1<-60+다이버전스',10),
    'Green_Dot_T1':          _sig(2.5,'buy','🟢','BUY T1','circle',16,'#00E676','Low',-2.5,'강한 매수','WT과매도교차+RSI<30+MFI<30',8),
    'Green_Dot_T2':          _sig(2.0,'buy','🟩','BUY T2','circle',13,'#69F0AE','Low',-2.2,'매수','WT과매도+RSI|MFI<32',5),
    'Blue_Diamond':          _sig(2.0,'buy','🔹','BLUE DIA','diamond',14,'#00bfff','Low',-1.8,'추세 매수','WT2≤0 상승교차+HTF강세',7),
    'Bull_Divergence':       _sig(2.0,'buy','📈','Bull Div','triangle-up',12,'#AA00FF','Low',-2.0,'상승 다이버전스','가격↓ vs WT↑',10),
    
    # ═══ MCB+ 매도 (핵심) ═══
    'Blood_Diamond':         _sig(3.0,'sell','🩸','BLOOD DIA','diamond',18,'#DC143C','High',3.0,'최강 매도','RSI>70+MFI>70+WT1>60+다이버전스',10),
    'Red_Dot_T1':            _sig(2.5,'sell','🔴','SELL T1','circle',16,'#FF1744','High',2.5,'강한 매도','WT과매수하락교차+RSI>70+MFI>70',8),
    'Red_Dot_T2':            _sig(2.0,'sell','🟥','SELL T2','circle',13,'#FF5252','High',2.2,'매도','WT과매수+RSI|MFI>68',5),
    'Red_Diamond':           _sig(2.0,'sell','🔸','RED DIA','diamond',14,'#ff3333','High',1.8,'추세 매도','WT2≥0 하락교차+HTF약세',7),
    'Bear_Divergence':       _sig(2.0,'sell','📉','Bear Div','triangle-down',12,'#AA00FF','High',2.0,'하락 다이버전스','가격↑ vs WT↓',10),
    
    # ═══ 서브 시그널 (매수) ═══
    'Green_Circle':          _sig(0.8,'buy','✅','BUY Circle','circle-open',11,'#00E676','Low',-1.2,'과매도 반등','WT과매도교차+RSI<45',5),
    'RSI_Bull_Divergence':   _sig(1.5,'buy','📊','RSI Bull Div','triangle-up',11,'#CE93D8','Low',-1.8,'RSI 상승 다이버전스','가격↓ vs RSI↑',10),
    'Squeeze_Fire_Buy':      _sig(1.5,'buy','💥','Squeeze BUY','star-diamond',14,'#00FFFF','Low',-1.5,'스퀴즈 매수','TTM Squeeze 해소+모멘텀↑',5),
    'Hidden_Bull_Div':       _sig(1.2,'buy','🔀','Hidden Bull','triangle-up',10,'#E040FB','Low',-1.6,'히든 상승 다이버전스','가격↑ vs WT↓(강세지속)',10),
    'Volume_Climax_Buy':     _sig(2.0,'buy','🌊','Vol Climax BUY','hexagram',14,'#00BCD4','Low',-2.8,'거래량 클라이맥스','3배 거래량+하락→반등',7),
    'ADX_Momentum_Buy':      _sig(1.5,'buy','🚀','ADX Ignition','arrow-up',11,'#76FF03','Low',-1.4,'ADX 점화','ADX>20돌파++DI>-DI',10),
    'Golden_Cross':          _sig(1.5,'buy','✨','Golden Cross','cross',12,'#FFD700','Low',-0.8,'골든 크로스','50MA>200MA+ADX>15',20),
    'EMA_Pullback_Buy':      _sig(2.0,'buy','🎯','EMA Pullback','triangle-up',13,'#00BFA5','Low',-1.8,'EMA 눌림목','상승추세 EMA조정후 반등',7),
    'Momentum_Ignition_Buy': _sig(2.5,'buy','🔥','Mom. Ignition','star-diamond',15,'#FF6D00','Low',-2.5,'모멘텀 점화','장대양봉>ATR×1.5+거래량>2.5배',10),
    'SuperTrend_Buy':        _sig(1.5,'buy','📈','ST Flip Bull','arrow-up',12,'#00E5FF','Low',-1.5,'슈퍼트렌드 강세','SuperTrend 상향 돌파',7),
    'VWAP_Bounce_Buy':       _sig(1.5,'buy','🏦','VWAP Bounce','triangle-up',11,'#00E5FF','Low',-1.3,'VWAP 반등','VWAP 복귀+WT교차',7),
    'Parabolic_Bottom_Buy':  _sig(3.0,'buy','🧊','Parabolic Bot','diamond',16,'#00FFFF','Low',-3.0,'포물선 바닥','WT1<-85 꺾임+양봉',5),
    'MACD_Cross_Buy':        _sig(1.0,'buy','〽️','MACD Cross','triangle-up',9,'#4CAF50','Low',-1.0,'MACD 골든크로스','MACD>시그널(0선 하방)',12),
    'StochRSI_Cross_Buy':    _sig(0.8,'buy','🔄','StRSI Cross','circle-open',8,'#81C784','Low',-0.8,'StochRSI 매수교차','StochK>StochD(과매도)',7),
    'OBV_Div_Buy':           _sig(0.8,'buy','📊','OBV Div BUY','triangle-up',10,'#80DEEA','Low',-1.4,'OBV 다이버전스','OBV↑ 가격↓',7),
    
    # ═══ 서브 시그널 (매도) ═══
    'Red_Circle':            _sig(0.8,'sell','⛔','SELL Circle','circle-open',11,'#FF1744','High',1.2,'과매수 하락','WT과매수하락교차+RSI>55',5),
    'RSI_Bear_Divergence':   _sig(1.5,'sell','📉','RSI Bear Div','triangle-down',11,'#CE93D8','High',1.8,'RSI 하락 다이버전스','가격↑ vs RSI↓',10),
    'Squeeze_Fire_Sell':     _sig(1.5,'sell','🧨','Squeeze SELL','star-diamond',14,'#FF6600','High',1.5,'스퀴즈 매도','TTM Squeeze 해소+모멘텀↓',5),
    'Hidden_Bear_Div':       _sig(1.2,'sell','🔁','Hidden Bear','triangle-down',10,'#E040FB','High',1.6,'히든 하락 다이버전스','가격↓ vs WT↑(약세지속)',10),
    'Volume_Climax_Sell':    _sig(2.0,'sell','🌋','Vol Climax SELL','hexagram',14,'#FF5722','High',2.8,'거래량 클라이맥스','3배 거래량+상승→하락',7),
    'ADX_Momentum_Sell':     _sig(1.5,'sell','💨','ADX Down','arrow-down',11,'#FF3D00','High',1.4,'ADX 하락 점화','ADX>20돌파+-DI>+DI',10),
    'Death_Cross':           _sig(1.5,'sell','☠️','Death Cross','cross',12,'#FF1744','High',0.8,'데드 크로스','50MA<200MA+ADX>15',20),
    'SuperTrend_Sell':       _sig(1.5,'sell','📉','ST Flip Bear','arrow-down',12,'#FF1744','High',1.5,'슈퍼트렌드 약세','SuperTrend 하향 이탈',7),
    'EMA_Pullback_Sell':     _sig(2.0,'sell','🎯','EMA PB Sell','triangle-down',13,'#FF6E40','High',1.8,'EMA 되돌림 매도','하락추세 EMA반등후 재하락',7),
    'Momentum_Ignition_Sell':_sig(2.5,'sell','💣','Mom. Ign Sell','star-diamond',15,'#D50000','High',2.5,'모멘텀 점화 매도','장대음봉>ATR×1.5+거래량>2.5배',10),
    'VWAP_Reject_Sell':      _sig(1.5,'sell','🏛️','VWAP Reject','triangle-down',11,'#FF6E40','High',1.3,'VWAP 저항','VWAP 실패+WT교차',7),
    'Parabolic_Top_Sell':    _sig(3.0,'sell','🌡️','Parabolic Top','diamond',16,'#FF0000','High',3.0,'포물선 천장','WT1>85 꺾임+음봉',5),
    'MACD_Cross_Sell':       _sig(1.0,'sell','〽️','MACD Dead','triangle-down',9,'#E57373','High',1.0,'MACD 데드크로스','MACD<시그널(0선 상방)',12),
    'StochRSI_Cross_Sell':   _sig(0.8,'sell','🔄','StRSI Dead','circle-open',8,'#EF9A9A','High',0.8,'StochRSI 매도교차','StochK<StochD(과매수)',7),
    'OBV_Div_Sell':          _sig(0.8,'sell','🔻','OBV Div SELL','triangle-down',10,'#FFAB91','High',1.4,'OBV 다이버전스','OBV↓ 가격↑',7),
    
    # ═══ 캔들스틱 ═══
    'Hammer':               _sig(1.5,'buy','🔨','Hammer','triangle-up',11,'#00E676','Low',-1.5,'해머','긴하단꼬리+소형실체+WT<-20',5),
    'Morning_Star':         _sig(2.0,'buy','🌅','MornStar','star',13,'#00E676','Low',-2.0,'모닝스타','3봉 반전 패턴',7),
    'Doji_Bullish':         _sig(0.6,'buy','➕','Doji Bull','cross-thin',9,'#69F0AE','Low',-1.0,'강세 도지','시가≈종가+하락추세후',5),
    'Bullish_Engulfing':    _sig(1.8,'buy','☀️','Bull Engulf','square',10,'#00E676','Low',-1.3,'상승 장악형','전일실체 완전 감싸기',5),
    'Shooting_Star':        _sig(1.5,'sell','🌠','ShootStar','triangle-down',11,'#FF1744','High',1.5,'슈팅스타','긴상단꼬리+소형실체+WT>20',5),
    'Evening_Star':         _sig(2.0,'sell','🌆','EveStar','star',13,'#FF1744','High',2.0,'이브닝스타','3봉 반전 패턴',7),
    'Doji_Bearish':         _sig(0.6,'sell','➖','Doji Bear','cross-thin',9,'#FF5252','High',1.0,'약세 도지','시가≈종가+상승추세후',5),
    'Bearish_Engulfing':    _sig(1.8,'sell','🌑','Bear Engulf','x',10,'#D50000','High',1.3,'하락 장악형','전일실체 완전 감싸기',5),
    
    # ═══ Inside/Outside ═══
    'Inside_Day':           _sig(0.3,'buy','📦','InsideDay','square-open',7,'#FFC107','Low',-0.3,'인사이드데이','변동성 수축',3),
    'Outside_Bullish':      _sig(1.5,'buy','💪','OutsideBull','square',11,'#00E676','Low',-1.5,'강세 아웃사이드','전일범위포함+양봉',7),
    'Outside_Bearish':      _sig(1.5,'sell','🥊','OutsideBear','square',11,'#FF1744','High',1.5,'약세 아웃사이드','전일범위포함+음봉',7),
    
    # ═══ MA 돌파 ═══
    'Cross_Above_20MA':     _sig(0.6,'buy','📈','X▲20MA','triangle-up',9,'#69F0AE','Low',-0.8,'20MA상향돌파','단기 강세전환',5),
    'Cross_Above_50MA':     _sig(1.0,'buy','📈','X▲50MA','triangle-up',10,'#00E676','Low',-1.0,'50MA상향돌파','중기 강세전환',10),
    'Cross_Above_200MA':    _sig(1.5,'buy','📈','X▲200MA','triangle-up',11,'#00BFA5','Low',-1.2,'200MA상향돌파','장기 강세전환',15),
    'Fell_Below_20MA':      _sig(0.6,'sell','📉','X▼20MA','triangle-down',9,'#FF5252','High',0.8,'20MA하향이탈','단기 약세전환',5),
    'Fell_Below_50MA':      _sig(1.0,'sell','📉','X▼50MA','triangle-down',10,'#FF1744','High',1.0,'50MA하향이탈','중기 약세전환',10),
    'Fell_Below_200MA':     _sig(1.5,'sell','📉','X▼200MA','triangle-down',11,'#D50000','High',1.2,'200MA하향이탈','장기 약세전환',15),
    
    # ═══ 볼린저 밴드 ═══
    'Above_Upper_BB':       _sig(0.8,'buy','🔝','BB▲Break','diamond-open',10,'#00E5FF','High',1.0,'BB상단돌파','강한모멘텀',5),
    'Below_Lower_BB':       _sig(0.8,'sell','⤵️','BB▼Break','diamond-open',10,'#FF6E40','Low',-1.0,'BB하단이탈','과매도/붕괴',5),
    'BB_Squeeze_End_Bull':  _sig(1.5,'buy','💥','SqEnd▲','star-diamond',12,'#00FFFF','Low',-1.5,'BB스퀴즈해소↑','상방 돌파',7),
    'BB_Squeeze_End_Bear':  _sig(1.5,'sell','💥','SqEnd▼','star-diamond',12,'#FF6600','High',1.5,'BB스퀴즈해소↓','하방 붕괴',7),
    
    # ═══ MACD 센터라인 ═══
    'MACD_Zero_Cross_Buy':  _sig(1.0,'buy','⬆️','MACD 0▲','triangle-up',10,'#4CAF50','Low',-1.0,'MACD 0선돌파','강세 전환',12),
    'MACD_Zero_Cross_Sell': _sig(1.0,'sell','⬇️','MACD 0▼','triangle-down',10,'#E57373','High',1.0,'MACD 0선이탈','약세 전환',12),
    
    # ═══ 연속 상승/하락 ═══
    'Up_3_Days':            _sig(0.4,'buy','📗','Up3D','triangle-up',8,'#69F0AE','High',0.5,'3일연속상승','단기 모멘텀',3),
    'Up_5_Days':            _sig(0.6,'buy','📗','Up5D','triangle-up',9,'#00E676','High',0.8,'5일연속상승','강한 모멘텀(과열주의)',5),
    'Down_3_Days':          _sig(0.4,'sell','📕','Dn3D','triangle-down',8,'#FF5252','Low',-0.5,'3일연속하락','단기 약세',3),
    'Down_5_Days':          _sig(0.6,'sell','📕','Dn5D','triangle-down',9,'#FF1744','Low',-0.8,'5일연속하락','강한 약세(반등주의)',5),
    
    # ═══ 갭 ═══
    'Gap_Up':               _sig(0.8,'buy','⏫','GapUp','arrow-up',10,'#00E676','Low',-1.0,'갭 상승','강한 매수세',3),
    'Gap_Down':             _sig(0.8,'sell','⏬','GapDn','arrow-down',10,'#FF1744','High',1.0,'갭 하락','강한 매도세',3),
    'Gap_Up_Closed':        _sig(0.6,'sell','🔄','GapUp Fill','circle-open',8,'#FFA726','High',0.8,'갭업메움','약세전환',5),
    'Gap_Down_Closed':      _sig(0.6,'buy','🔄','GapDn Fill','circle-open',8,'#4FC3F7','Low',-0.8,'갭다운메움','강세전환',5),
    
    # ═══ 변동성 패턴 ═══
    'NR7':                  _sig(0.3,'buy','🔲','NR7','square-open',7,'#B0BEC5','Low',-0.3,'NR7','7일중최소범위(돌파임박)',3),
    'NR7_2':                _sig(0.6,'buy','🔳','NR7-2','square-open',8,'#90A4AE','Low',-0.5,'NR7-2','2일연속NR7',5),
    'Calm_After_Storm':     _sig(0.8,'buy','🌤️','CalmStorm','diamond-open',9,'#FFC107','Low',-0.8,'폭풍뒤고요','대폭변동후수축',5),
    'Wide_Range_Bar':       _sig(0.4,'buy','📊','WideBar','square-open',7,'#FFAB40','Low',-0.4,'넓은범위봉','변동성확장',3),
    
    # ═══ 52주 ═══
    'New_52W_High':         _sig(1.5,'buy','🏔️','52W▲','star-triangle-up',12,'#FFD700','High',1.5,'52주신고가','돌파',10),
    'New_52W_Low':          _sig(1.5,'sell','🕳️','52W▼','star-triangle-down',12,'#B71C1C','Low',-1.5,'52주신저가','붕괴',10),
    'Spinning_Top':         _sig(0.2,'buy','🌀','SpinTop','circle-open',7,'#FFC107','Low',-0.3,'팽이형','우유부단',3),
    
    # ═══ Jeff Cooper ═══
    'Pullback_123_Bull':    _sig(2.0,'buy','🎯','123PB▲','triangle-up',12,'#00E676','Low',-1.8,'1,2,3풀백매수','ADX>30+3일저점↓후',7),
    'Pullback_123_Bear':    _sig(2.0,'sell','🎯','123PB▼','triangle-down',12,'#FF1744','High',1.8,'1,2,3풀백매도','ADX>30+3일고점↑후',7),
    'Setup_180_Bull':       _sig(2.0,'buy','🔄','180▲','star-diamond',13,'#00E676','Low',-2.0,'180매수셋업','하위25%→상위25%',7),
    'Setup_180_Bear':       _sig(2.0,'sell','🔄','180▼','star-diamond',13,'#FF1744','High',2.0,'180매도셋업','상위25%→하위25%',7),
    'Boomer_Buy':           _sig(2.0,'buy','💣','Boomer▲','star',12,'#00E676','Low',-1.8,'부머매수','ADX>30+2일인사이드→돌파',10),
    'Boomer_Sell':          _sig(2.0,'sell','💣','Boomer▼','star',12,'#FF1744','High',1.8,'부머매도','ADX>30+2일인사이드→이탈',10),
    'Expansion_BO':         _sig(2.5,'buy','🚀','XBO','star-diamond',14,'#FFD700','Low',-2.5,'확장돌파','2개월신고가+9일최대범위',10),
    'Expansion_BD':         _sig(2.5,'sell','💨','XBD','star-diamond',14,'#FF0000','High',2.5,'확장붕괴','2개월신저가+9일최대범위',10),
    'Gilligans_Buy':        _sig(2.0,'buy','🏝️','Gilligan▲','hexagon',12,'#00BCD4','Low',-2.0,'길리건매수','갭다운신저가→상위50%마감',10),
    'Gilligans_Sell':       _sig(2.0,'sell','🏝️','Gilligan▼','hexagon',12,'#FF5722','High',2.0,'길리건매도','갭업신고가→하위50%마감',10),
    'Lizard_Bull':          _sig(1.5,'buy','🦎','Lizard▲','triangle-up',10,'#00E676','Low',-1.5,'리자드매수','시가종가상위25%+10일신저가',5),
    'Lizard_Bear':          _sig(1.5,'sell','🦎','Lizard▼','triangle-down',10,'#FF1744','High',1.5,'리자드매도','시가종가하위25%+10일신고가',5),
    'NonADX_123_Bull':      _sig(1.5,'buy','📐','nADX123▲','triangle-up',11,'#69F0AE','Low',-1.5,'비ADX풀백매수','주가>50MA+3일저점↓',7),
    'NonADX_123_Bear':      _sig(1.5,'sell','📐','nADX123▼','triangle-down',11,'#FF5252','High',1.5,'비ADX풀백매도','주가<50MA+3일고점↑',7),
    'Pocket_Pivot':         _sig(1.5,'buy','🧲','PocketPvt','triangle-up',11,'#7C4DFF','Low',-1.5,'포켓피봇','양봉+거래량>10일하락거래량최대',10),
    
    # ═══ Money Flow ═══
    'MF_Cross_Bull':        _sig(1.2,'buy','💰','MF 0▲','triangle-up',11,'#00E676','Low',-1.2,'MF 강세전환','자금흐름 음→양',10),
    'MF_Cross_Bear':        _sig(1.2,'sell','💸','MF 0▼','triangle-down',11,'#FF1744','High',1.2,'MF 약세전환','자금흐름 양→음',10),
    'MF_Bull_Div':          _sig(1.5,'buy','💹','MF Bull Div','triangle-up',11,'#7C4DFF','Low',-1.5,'MF 상승 다이버전스','가격↓ vs MF↑',10),
    'MF_Bear_Div':          _sig(1.5,'sell','💹','MF Bear Div','triangle-down',11,'#E040FB','High',1.5,'MF 하락 다이버전스','가격↑ vs MF↓',10),
    'MF_Accel_Up':          _sig(0.8,'buy','📈','MF Accel▲','arrow-up',9,'#69F0AE','Low',-0.8,'MF 가속상승','5일+ 연속 상승',5),
    'MF_Accel_Dn':          _sig(0.8,'sell','📉','MF Accel▼','arrow-down',9,'#FF5252','High',0.8,'MF 가속하락','5일+ 연속 하락',5),
}

# 복합 시그널 (Confluence 기반)
COMPOSITE_SIGNALS: Dict[str, Signal] = {
    'Ultra_Buy':  _sig(0,'buy','⚡','ULTRA BUY','star',20,'#FFD700','Low',-3.5,'울트라 매수','Confluence≥6.5',0),
    'Strong_Buy': _sig(0,'buy','🔱','STRONG BUY','star',16,'#00E676','Low',-3.2,'스트롱 매수','Confluence 3.5~6.5',0),
    'Ultra_Sell': _sig(0,'sell','🚨','ULTRA SELL','star',20,'#FF0000','High',3.5,'울트라 매도','Confluence≤-6.5',0),
    'Strong_Sell':_sig(0,'sell','⚠️','STRONG SELL','star',16,'#FF1744','High',3.2,'스트롱 매도','Confluence -6.5~-3.5',0),
}

ALL_SIGNALS = {**SIGNAL_REGISTRY, **COMPOSITE_SIGNALS}


# ──────────────────────────────────────────
# 판단 설정
# ──────────────────────────────────────────
JUDGMENT_CONFIG = {
    'STRONG_BUY':  ('🟢🟢🟢 STRONG BUY', Colors.BUY, 'rgba(0,230,118,.12)'),
    'BUY':         ('🟢🟢 BUY', Colors.BUY, 'rgba(0,230,118,.08)'),
    'WATCH_BUY':   ('🟡🟢 WATCH BUY', Colors.NEUTRAL, 'rgba(255,193,7,.08)'),
    'NEUTRAL':     ('⚪ NEUTRAL', '#888888', 'rgba(128,128,128,.05)'),
    'MIXED':       ('🟠 MIXED', '#FF9800', 'rgba(255,152,0,.08)'),
    'WATCH_SELL':  ('🟡🔴 WATCH SELL', Colors.NEUTRAL, 'rgba(255,193,7,.08)'),
    'SELL':        ('🔴🔴 SELL', Colors.SELL, 'rgba(255,23,68,.08)'),
    'STRONG_SELL': ('🔴🔴🔴 STRONG SELL', Colors.SELL, 'rgba(255,23,68,.12)'),
}

JUDGMENT_MARKERS = {
    'STRONG_BUY':  {'symbol':'star','size':18,'color':Colors.BUY,'base':'Low','atr_mult':-3.5},
    'BUY':         {'symbol':'triangle-up','size':14,'color':Colors.BUY,'base':'Low','atr_mult':-2.5},
    'WATCH_BUY':   {'symbol':'circle','size':9,'color':Colors.BUY_LIGHT,'base':'Low','atr_mult':-2.0},
    'STRONG_SELL': {'symbol':'star','size':18,'color':Colors.SELL,'base':'High','atr_mult':3.5},
    'SELL':        {'symbol':'triangle-down','size':14,'color':Colors.SELL,'base':'High','atr_mult':2.5},
    'WATCH_SELL':  {'symbol':'circle','size':9,'color':Colors.SELL_LIGHT,'base':'High','atr_mult':2.0},
    'MIXED':       {'symbol':'diamond','size':11,'color':'#FF9800','base':'High','atr_mult':2.0},
}


# ──────────────────────────────────────────
# 콤보 정의 (차등 보너스)
# ──────────────────────────────────────────
COMBO_CONFIG = {
    # BUY 콤보
    'Combo_TrendPullback_Buy':  ('🎯 추세 눌림목', 'buy', 4.0),
    'Combo_VolSqueeze_Buy':     ('💥 변동성 수축 돌파', 'buy', 3.5),
    'Combo_Reversal_Buy':       ('🔄 반전 매수', 'buy', 3.5),
    'Combo_Momentum_Buy':       ('🚀 모멘텀 돌파', 'buy', 3.0),
    'Combo_MAConfluence_Buy':   ('📊 MA 합류', 'buy', 2.5),
    'Combo_MF_Reversal_Buy':    ('💰 자금흐름 전환', 'buy', 3.0),
    # SELL 콤보
    'Combo_TrendRejection_Sell':('🎯 추세 반등 실패', 'sell', 4.0),
    'Combo_Exhaustion_Sell':    ('🌡️ 고점 소진', 'sell', 3.5),
    'Combo_MABreakdown_Sell':   ('📉 MA 붕괴', 'sell', 3.0),
    'Combo_VolSqueeze_Sell':    ('💨 변동성 수축 붕괴', 'sell', 3.5),
    'Combo_GapFailure_Sell':    ('⏬ 갭 실패', 'sell', 2.5),
    'Combo_MF_Reversal_Sell':   ('💸 자금흐름 전환', 'sell', 3.0),
}


# ──────────────────────────────────────────
# 시그널 계층 (중복 제거용)
# ──────────────────────────────────────────
SIGNAL_HIERARCHY = {
    'candle_bull': ['Morning_Star','Bullish_Engulfing','Hammer','Doji_Bullish','Spinning_Top'],
    'candle_bear': ['Evening_Star','Bearish_Engulfing','Shooting_Star','Doji_Bearish','Spinning_Top'],
    'ma_cross_bull': ['Cross_Above_200MA','Cross_Above_50MA','Cross_Above_20MA'],
    'ma_cross_bear': ['Fell_Below_200MA','Fell_Below_50MA','Fell_Below_20MA'],
    'mcb_buy': ['Gold_Dot','Green_Dot_T1','Green_Dot_T2','Green_Circle'],
    'mcb_sell': ['Blood_Diamond','Red_Dot_T1','Red_Dot_T2','Red_Circle'],
    'div_buy': ['Gold_Dot','Bull_Divergence','RSI_Bull_Divergence','Hidden_Bull_Div'],
    'div_sell': ['Blood_Diamond','Bear_Divergence','RSI_Bear_Divergence','Hidden_Bear_Div'],
}


# ──────────────────────────────────────────
# 유틸리티 함수
# ──────────────────────────────────────────
def _valid_ticker(t: str) -> bool:
    """티커 형식 검증"""
    return bool(re.match(r'^[A-Za-z]{1,5}([.\-][A-Za-z]{1,2})?$', t))


def _cooldown_vectorized(sig: pd.Series, bars: int) -> pd.Series:
    """벡터화된 쿨다운 (최적화)"""
    if not sig.any():
        return sig
    
    mask = sig.fillna(False).values
    indices = np.where(mask)[0]
    
    if len(indices) == 0:
        return pd.Series(False, index=sig.index)
    
    # 유효한 시그널만 선택
    valid = [indices[0]]
    for idx in indices[1:]:
        if idx - valid[-1] > bars:
            valid.append(idx)
    
    result = np.zeros(len(sig), dtype=bool)
    result[valid] = True
    return pd.Series(result, index=sig.index)


def _cooldown_paired(df: pd.DataFrame, buy_col: str, sell_col: str, bars: int) -> None:
    """방향별 독립 쿨다운 (in-place)"""
    if buy_col in df.columns:
        df[buy_col] = _cooldown_vectorized(df[buy_col], bars)
    if sell_col in df.columns:
        df[sell_col] = _cooldown_vectorized(df[sell_col], bars)


def _recent(s: pd.Series, lookback: int = 3) -> pd.Series:
    """최근 N일 내 발생 여부"""
    return s.astype(float).rolling(lookback + 1, min_periods=1).max().fillna(0).astype(bool)


def _volume_filter(vol: pd.Series, ratio: float = 0.5, period: int = 20) -> pd.Series:
    """거래량 필터"""
    avg = vol.rolling(period, min_periods=5).mean()
    return vol >= (avg * ratio)


def _cls(val: float, low: float, high: float) -> str:
    """값에 따른 CSS 클래스 반환"""
    if val < low:
        return 'ind-bullish'
    elif val > high:
        return 'ind-bearish'
    return 'ind-neutral'


# ──────────────────────────────────────────
# API 키 설정
# ──────────────────────────────────────────
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GEMINI_API_KEY)

# ══════════════════════════════════════════════════════════════
#  CipherX V12.0 — PART 2/4: 기술 지표 + 시그널 탐지 엔진
# ══════════════════════════════════════════════════════════════

# ──────────────────────────────────────────
# 기술 지표 계산 (최적화)
# ──────────────────────────────────────────
class Indicators:
    """기술 지표 계산 클래스"""
    
    @staticmethod
    def rsi(close: pd.Series, period: int = 14) -> pd.Series:
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
        avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
        return 100 - (100 / (1 + avg_gain / (avg_loss + 1e-10)))
    
    @staticmethod
    def mfi(high: pd.Series, low: pd.Series, close: pd.Series, 
            volume: pd.Series, period: int = 14) -> pd.Series:
        tp = (high + low + close) / 3
        raw_mf = tp * volume
        delta = tp.diff()
        pos_mf = raw_mf.where(delta >= 0, 0.0).rolling(period).sum()
        neg_mf = raw_mf.where(delta < 0, 0.0).rolling(period).sum()
        return 100 - (100 / (1 + pos_mf / (neg_mf + 1e-10)))
    
    @staticmethod
    def rsi_mfi_combined(high: pd.Series, low: pd.Series, close: pd.Series,
                         volume: pd.Series, period: int = 60) -> pd.Series:
        """RSI + MFI 복합 지표"""
        rsi_fast = Indicators.rsi(close, 20)
        mfi_fast = Indicators.mfi(high, low, close, volume, 20)
        rsi_slow = Indicators.rsi(close, period)
        mfi_slow = Indicators.mfi(high, low, close, volume, period)
        
        fast = ((rsi_fast - 50) + (mfi_fast - 50)) / 2
        slow = ((rsi_slow - 50) + (mfi_slow - 50)) / 2
        return fast * 0.6 + slow * 0.4
    
    @staticmethod
    def wavetrend(high: pd.Series, low: pd.Series, close: pd.Series,
                  ch_period: int = 9, avg_period: int = 12, 
                  ma_period: int = 3) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
        """WaveTrend 오실레이터"""
        ap = (high + low + close) / 3
        esa = ap.ewm(span=ch_period, adjust=False).mean()
        d = (ap - esa).abs().ewm(span=ch_period, adjust=False).mean()
        ci = (ap - esa) / (0.015 * d + 1e-10)
        wt1 = ci.ewm(span=avg_period, adjust=False).mean()
        wt2 = wt1.rolling(ma_period).mean()
        
        cross_up = (wt1 > wt2) & (wt1.shift(1) <= wt2.shift(1))
        cross_down = (wt1 < wt2) & (wt1.shift(1) >= wt2.shift(1))
        
        return wt1, wt2, cross_up, cross_down
    
    @staticmethod
    def stoch_rsi(close: pd.Series, rsi_period: int = 14, stoch_period: int = 14,
                  k_smooth: int = 3, d_smooth: int = 3) -> Tuple[pd.Series, pd.Series]:
        """Stochastic RSI"""
        rsi = Indicators.rsi(close, rsi_period)
        rsi_min = rsi.rolling(stoch_period).min()
        rsi_max = rsi.rolling(stoch_period).max()
        stoch_rsi = (rsi - rsi_min) / (rsi_max - rsi_min + 1e-10) * 100
        k = stoch_rsi.rolling(k_smooth).mean()
        d = k.rolling(d_smooth).mean()
        return k, d
    
    @staticmethod
    def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
        prev_close = close.shift(1)
        return pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs()
        ], axis=1).max(axis=1)
    
    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, 
            period: int = 14) -> pd.Series:
        tr = Indicators.true_range(high, low, close)
        return tr.rolling(period).mean()
    
    @staticmethod
    def adx(high: pd.Series, low: pd.Series, close: pd.Series,
            period: int = 14) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """ADX, +DI, -DI"""
        tr = Indicators.true_range(high, low, close)
        prev_high, prev_low = high.shift(1), low.shift(1)
        
        plus_dm = np.where((high - prev_high) > (prev_low - low),
                           np.maximum(high - prev_high, 0), 0)
        minus_dm = np.where((prev_low - low) > (high - prev_high),
                            np.maximum(prev_low - low, 0), 0)
        
        plus_dm = pd.Series(plus_dm, index=high.index, dtype=float)
        minus_dm = pd.Series(minus_dm, index=high.index, dtype=float)
        
        atr_smooth = tr.ewm(alpha=1/period, min_periods=period).mean()
        plus_di = 100 * plus_dm.ewm(alpha=1/period, min_periods=period).mean() / (atr_smooth + 1e-10)
        minus_di = 100 * minus_dm.ewm(alpha=1/period, min_periods=period).mean() / (atr_smooth + 1e-10)
        
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-10)
        adx = dx.ewm(alpha=1/period, min_periods=period).mean()
        
        return adx, plus_di, minus_di
    
    @staticmethod
    def macd(close: pd.Series, fast: int = 12, slow: int = 26, 
             signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        ema_fast = close.ewm(span=fast, adjust=False).mean()
        ema_slow = close.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram
    
    @staticmethod
    def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
        return (volume * np.sign(close.diff()).fillna(0)).cumsum()
    
    @staticmethod
    def keltner(high: pd.Series, low: pd.Series, close: pd.Series,
                ema_period: int = 20, atr_period: int = 10, 
                mult: float = 1.5) -> Tuple[pd.Series, pd.Series, pd.Series]:
        mid = close.ewm(span=ema_period, adjust=False).mean()
        atr = Indicators.true_range(high, low, close).rolling(atr_period).mean()
        return mid + atr * mult, mid, mid - atr * mult
    
    @staticmethod
    def supertrend(high: pd.Series, low: pd.Series, close: pd.Series,
                   period: int = 10, mult: float = 3.0) -> Tuple[pd.Series, pd.Series]:
        """SuperTrend 계산"""
        atr = Indicators.true_range(high, low, close).rolling(period).mean()
        hl2 = (high + low) / 2
        
        upper = (hl2 + mult * atr).values.copy()
        lower = (hl2 - mult * atr).values.copy()
        cl = close.values
        n = len(close)
        
        st_val = np.full(n, np.nan)
        direction = np.zeros(n, dtype=int)
        
        first_valid = period
        if first_valid >= n:
            return pd.Series(np.nan, index=close.index), pd.Series(0, index=close.index, dtype=int)
        
        direction[first_valid] = 1
        st_val[first_valid] = lower[first_valid]
        
        for i in range(first_valid + 1, n):
            if direction[i-1] == 1:
                lower[i] = max(lower[i], lower[i-1]) if not np.isnan(lower[i-1]) else lower[i]
            else:
                upper[i] = min(upper[i], upper[i-1]) if not np.isnan(upper[i-1]) else upper[i]
            
            if direction[i-1] == 1:
                if cl[i] < lower[i]:
                    direction[i], st_val[i] = -1, upper[i]
                else:
                    direction[i], st_val[i] = 1, lower[i]
            else:
                if cl[i] > upper[i]:
                    direction[i], st_val[i] = 1, lower[i]
                else:
                    direction[i], st_val[i] = -1, upper[i]
        
        return pd.Series(st_val, index=close.index), pd.Series(direction, index=close.index)


def compute_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """모든 기술 지표 계산"""
    C, H, L, V = df['Close'], df['High'], df['Low'], df['Volume']
    
    # 이동평균
    for ma in [5, 10, 20, 50, 100, 125, 200]:
        df[f'MA{ma}'] = C.rolling(ma).mean()
    
    # EMA
    df['EMA8'] = C.ewm(span=8, adjust=False).mean()
    df['EMA21'] = C.ewm(span=21, adjust=False).mean()
    
    # 볼린저 밴드
    df['BB_Mid'] = df['MA20']
    std20 = C.rolling(20).std()
    df['BB_Up'] = df['BB_Mid'] + std20 * 2
    df['BB_Low'] = df['BB_Mid'] - std20 * 2
    df['BB_Width'] = (df['BB_Up'] - df['BB_Low']) / df['BB_Mid']
    df['Percent_B'] = (C - df['BB_Low']) / (df['BB_Up'] - df['BB_Low'] + 1e-10)
    
    # ATR
    df['ATR'] = Indicators.atr(H, L, C, 14)
    
    # Chandelier Exit
    atr22 = Indicators.true_range(H, L, C).rolling(22).mean()
    df['Chandelier_Long'] = H.rolling(22).max() - atr22 * 3.0
    df['Chandelier_Short'] = L.rolling(22).min() + atr22 * 3.0
    
    # SuperTrend
    df['SuperTrend'], df['ST_Direction'] = Indicators.supertrend(H, L, C)
    
    # WaveTrend
    wt1, wt2, wt_up, wt_down = Indicators.wavetrend(H, L, C)
    df['WT1'], df['WT2'], df['WT_Up'], df['WT_Down'] = wt1, wt2, wt_up, wt_down
    
    # RSI & MFI
    df['RSI'] = Indicators.rsi(C, 14)
    df['MFI'] = Indicators.mfi(H, L, C, V, 14)
    df['RSI_MFI'] = Indicators.rsi_mfi_combined(H, L, C, V, 60)
    
    # Stochastic RSI
    df['StochK'], df['StochD'] = Indicators.stoch_rsi(C)
    
    # VWAP Oscillator
    vwap = (C * V).rolling(20).sum() / (V.rolling(20).sum() + 1e-10)
    df['VWAP_Osc'] = ((C - vwap) / (vwap + 1e-10)) * 100
    
    # ADX
    df['ADX'], df['Plus_DI'], df['Minus_DI'] = Indicators.adx(H, L, C)
    
    # OBV
    df['OBV'] = Indicators.obv(C, V)
    
    # Keltner Channels
    df['KC_Upper'], df['KC_Mid'], df['KC_Lower'] = Indicators.keltner(H, L, C)
    
    # MACD
    df['MACD_Line'], df['MACD_Signal'], df['MACD_Hist'] = Indicators.macd(C)
    
    return df


# ──────────────────────────────────────────
# 시그널 탐지 함수들
# ──────────────────────────────────────────
class SignalDetector:
    """시그널 탐지 클래스"""
    
    @staticmethod
    def pivot_divergence(price: pd.Series, osc: pd.Series, lookback: int = 60,
                         pivot_width: int = 5, os_limit: float = None,
                         ob_limit: float = None) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
        """피봇 기반 다이버전스 탐지 (최적화)"""
        n = len(price)
        pv, ov = price.values, osc.values
        half = pivot_width
        
        # 피봇 저점/고점 찾기
        pivot_lows, pivot_highs = [], []
        for i in range(2 * half, n):
            center = i - half
            window = pv[i - 2*half:i + 1]
            if pv[center] == window.min():
                pivot_lows.append((i, center))
            if pv[center] == window.max():
                pivot_highs.append((i, center))
        
        bull_div = pd.Series(False, index=price.index)
        bear_div = pd.Series(False, index=price.index)
        hidden_bull = pd.Series(False, index=price.index)
        hidden_bear = pd.Series(False, index=price.index)
        
        # 상승 다이버전스 (가격↓, 오실레이터↑)
        for idx in range(1, len(pivot_lows)):
            curr_i, curr_p = pivot_lows[idx]
            prev_i, prev_p = pivot_lows[idx - 1]
            
            if not (pivot_width * 2 <= (curr_p - prev_p) <= lookback):
                continue
            
            if (os_limit is None or ov[curr_p] <= os_limit):
                if pv[curr_p] < pv[prev_p] and ov[curr_p] > ov[prev_p]:
                    bull_div.iloc[curr_i] = True
            
            # 히든 상승 다이버전스
            if pv[curr_p] > pv[prev_p] and ov[curr_p] < ov[prev_p]:
                hidden_bull.iloc[curr_i] = True
        
        # 하락 다이버전스 (가격↑, 오실레이터↓)
        for idx in range(1, len(pivot_highs)):
            curr_i, curr_p = pivot_highs[idx]
            prev_i, prev_p = pivot_highs[idx - 1]
            
            if not (pivot_width * 2 <= (curr_p - prev_p) <= lookback):
                continue
            
            if (ob_limit is None or ov[curr_p] >= ob_limit):
                if pv[curr_p] > pv[prev_p] and ov[curr_p] < ov[prev_p]:
                    bear_div.iloc[curr_i] = True
            
            # 히든 하락 다이버전스
            if pv[curr_p] < pv[prev_p] and ov[curr_p] > ov[prev_p]:
                hidden_bear.iloc[curr_i] = True
        
        return bull_div, bear_div, hidden_bull, hidden_bear
    
    @staticmethod
    def ttm_squeeze(bb_up: pd.Series, bb_low: pd.Series, kc_up: pd.Series,
                    kc_low: pd.Series, close: pd.Series, high: pd.Series,
                    low: pd.Series, kc_mid: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """TTM Squeeze 탐지"""
        squeeze_on = (bb_up < kc_up) & (bb_low > kc_low)
        fire = (~squeeze_on) & squeeze_on.shift(1).fillna(False)
        
        momentum = close - ((high.rolling(20).max() + low.rolling(20).min()) / 2 + kc_mid) / 2
        mom_up = momentum > momentum.shift(1)
        mom_down = momentum < momentum.shift(1)
        
        return squeeze_on, fire & (momentum > 0) & mom_up, fire & (momentum < 0) & mom_down
    
    @staticmethod
    def volume_climax(close: pd.Series, open_: pd.Series, volume: pd.Series,
                      wt1: pd.Series, atr: pd.Series, 
                      z_thresh: float = 2.5) -> Tuple[pd.Series, pd.Series]:
        """거래량 클라이맥스 탐지"""
        vol_mean = volume.rolling(20).mean()
        vol_std = volume.rolling(20).std()
        vol_z = (volume - vol_mean) / (vol_std + 1e-10)
        
        big_body = (close - open_).abs() > atr * 0.5
        prev_spike = (vol_z.shift(1) > z_thresh) & big_body.shift(1)
        
        buy = prev_spike & (close.shift(1) < open_.shift(1)) & (wt1.shift(1) < -40) & (close > open_)
        sell = prev_spike & (close.shift(1) > open_.shift(1)) & (wt1.shift(1) > 40) & (close < open_)
        
        return buy, sell
    
    @staticmethod
    def engulfing(close: pd.Series, open_: pd.Series, wt1: pd.Series,
                  atr: pd.Series, wt_threshold: float = 20) -> Tuple[pd.Series, pd.Series]:
        """정확한 Engulfing 패턴"""
        body = (close - open_).abs()
        body_prev = (close.shift(1) - open_.shift(1)).abs()
        avg_body = body.rolling(20).mean()
        
        # 당일 실체가 전일보다 크고, 평균 이상
        big = (body > avg_body * 0.8) & (body > body_prev)
        
        # 전일/당일 실체 범위
        prev_high = pd.concat([close.shift(1), open_.shift(1)], axis=1).max(axis=1)
        prev_low = pd.concat([close.shift(1), open_.shift(1)], axis=1).min(axis=1)
        curr_high = pd.concat([close, open_], axis=1).max(axis=1)
        curr_low = pd.concat([close, open_], axis=1).min(axis=1)
        
        # 완전 감싸기 조건
        wrap = (curr_low <= prev_low) & (curr_high >= prev_high)
        
        bull = (close.shift(1) < open_.shift(1)) & (close > open_) & wrap & big & (wt1 < -wt_threshold)
        bear = (close.shift(1) > open_.shift(1)) & (close < open_) & wrap & big & (wt1 > wt_threshold)
        
        return bull, bear
    
    @staticmethod
    def candlestick_patterns(close: pd.Series, open_: pd.Series, high: pd.Series,
                             low: pd.Series, wt1: pd.Series, 
                             atr: pd.Series) -> Dict[str, pd.Series]:
        """캔들스틱 패턴 탐지"""
        body = (close - open_).abs()
        upper_shadow = high - pd.concat([close, open_], axis=1).max(axis=1)
        lower_shadow = pd.concat([close, open_], axis=1).min(axis=1) - low
        full_range = high - low + 1e-10
        avg_body = body.rolling(20).mean()
        
        is_small = body < avg_body * 0.5
        min_range = atr * 0.5
        
        patterns = {}
        
        # Hammer
        patterns['Hammer'] = (
            (lower_shadow >= body * 2) & 
            (upper_shadow <= body * 0.3) & 
            is_small & (wt1 < -20) & (close >= open_) & 
            (full_range > min_range)
        )
        
        # Shooting Star
        patterns['Shooting_Star'] = (
            (upper_shadow >= body * 2) & 
            (lower_shadow <= body * 0.3) & 
            is_small & (wt1 > 20) & (close <= open_) & 
            (full_range > min_range)
        )
        
        # Doji
        doji = (body <= full_range * 0.05) & (full_range > atr * 0.3)
        patterns['Doji_Bullish'] = doji & (wt1 < -30) & (wt1 > wt1.shift(1)) & (close.shift(1) < close.shift(3))
        patterns['Doji_Bearish'] = doji & (wt1 > 30) & (wt1 < wt1.shift(1)) & (close.shift(1) > close.shift(3))
        
        # Morning Star
        d1_bear = (close.shift(2) < open_.shift(2)) & (body.shift(2) > avg_body.shift(2))
        d2_small = body.shift(1) < avg_body.shift(1) * 0.5
        d3_bull = (close > open_) & (close > (open_.shift(2) + close.shift(2)) / 2) & (body > avg_body * 0.8)
        patterns['Morning_Star'] = d1_bear & d2_small & d3_bull & (wt1 < -15)
        
        # Evening Star
        d1_bull = (close.shift(2) > open_.shift(2)) & (body.shift(2) > avg_body.shift(2))
        d3_bear = (close < open_) & (close < (open_.shift(2) + close.shift(2)) / 2) & (body > avg_body * 0.8)
        patterns['Evening_Star'] = d1_bull & d2_small & d3_bear & (wt1 > 15)
        
        # Spinning Top
        spin_ratio = upper_shadow / (lower_shadow + 1e-10)
        patterns['Spinning_Top'] = (
            is_small & 
            (upper_shadow > body * 0.5) & 
            (lower_shadow > body * 0.5) & 
            (spin_ratio > 0.5) & (spin_ratio < 2.0) & 
            ~doji
        )
        
        return patterns
    
    @staticmethod
    def ma_crossovers(close: pd.Series, ma20: pd.Series, ma50: pd.Series,
                      ma200: pd.Series) -> Dict[str, pd.Series]:
        """이동평균 돌파/이탈"""
        return {
            'Cross_Above_20MA': (close > ma20) & (close.shift(1) <= ma20.shift(1)),
            'Fell_Below_20MA': (close < ma20) & (close.shift(1) >= ma20.shift(1)),
            'Cross_Above_50MA': (close > ma50) & (close.shift(1) <= ma50.shift(1)),
            'Fell_Below_50MA': (close < ma50) & (close.shift(1) >= ma50.shift(1)),
            'Cross_Above_200MA': (close > ma200) & (close.shift(1) <= ma200.shift(1)),
            'Fell_Below_200MA': (close < ma200) & (close.shift(1) >= ma200.shift(1)),
        }
    
    @staticmethod
    def consecutive_days(close: pd.Series) -> Dict[str, pd.Series]:
        """연속 상승/하락일 (벡터화)"""
        up = (close > close.shift(1)).astype(int)
        dn = (close < close.shift(1)).astype(int)
        
        up_streak = up.groupby((up == 0).cumsum()).cumsum()
        dn_streak = dn.groupby((dn == 0).cumsum()).cumsum()
        
        return {
            'Up_3_Days': up_streak >= 3,
            'Up_5_Days': up_streak >= 5,
            'Down_3_Days': dn_streak >= 3,
            'Down_5_Days': dn_streak >= 5,
        }
    
    @staticmethod
    def gaps(close: pd.Series, open_: pd.Series, high: pd.Series,
             low: pd.Series, atr: pd.Series) -> Dict[str, pd.Series]:
        """갭 탐지"""
        threshold = atr * 0.5
        gap_up = (open_ > high.shift(1)) & ((open_ - high.shift(1)) > threshold)
        gap_down = (open_ < low.shift(1)) & ((low.shift(1) - open_) > threshold)
        
        return {
            'Gap_Up': gap_up,
            'Gap_Down': gap_down,
            'Gap_Up_Closed': gap_up.shift(1).fillna(False) & (low <= high.shift(2)),
            'Gap_Down_Closed': gap_down.shift(1).fillna(False) & (high >= low.shift(2)),
        }
    
    @staticmethod
    def nr7_patterns(high: pd.Series, low: pd.Series, atr: pd.Series) -> Dict[str, pd.Series]:
        """NR7 및 변동성 패턴"""
        daily_range = high - low
        min_range_7 = daily_range.rolling(7).min()
        
        nr7 = daily_range <= min_range_7
        wide = daily_range > atr * 2.0
        narrow = daily_range < atr * 0.5
        
        recent_wide = wide.rolling(5, min_periods=1).max().shift(1).fillna(False).astype(bool)
        
        return {
            'NR7': nr7,
            'NR7_2': nr7 & nr7.shift(1).fillna(False),
            'Wide_Range_Bar': wide,
            'Calm_After_Storm': recent_wide & narrow,
        }
    
    @staticmethod
    def week_52_extremes(close: pd.Series, high: pd.Series, 
                         low: pd.Series) -> Tuple[pd.Series, pd.Series]:
        """52주 신고가/신저가 (look-ahead bias 제거)"""
        h252_prev = high.rolling(252, min_periods=200).max().shift(1)
        l252_prev = low.rolling(252, min_periods=200).min().shift(1)
        return high > h252_prev, low < l252_prev
    
    @staticmethod
    def money_flow_signals(close: pd.Series, rmfi: pd.Series) -> Dict[str, pd.Series]:
        """Money Flow 시그널"""
        # 0선 교차
        cross_bull = (rmfi > 0) & (rmfi.shift(1) <= 0)
        cross_bear = (rmfi < 0) & (rmfi.shift(1) >= 0)
        
        # 연속 상승/하락 (벡터화)
        mf_rising = rmfi > rmfi.shift(1)
        mf_falling = rmfi < rmfi.shift(1)
        
        up_streak = mf_rising.astype(int).groupby((~mf_rising).cumsum()).cumsum()
        dn_streak = mf_falling.astype(int).groupby((~mf_falling).cumsum()).cumsum()
        
        # 다이버전스
        price_lower = close < close.rolling(5).min().shift(1)
        mf_higher = rmfi > rmfi.rolling(5).min().shift(1)
        
        price_higher = close > close.rolling(5).max().shift(1)
        mf_lower = rmfi < rmfi.rolling(5).max().shift(1)
        
        return {
            'MF_Cross_Bull': cross_bull,
            'MF_Cross_Bear': cross_bear,
            'MF_Bull_Div': price_lower & mf_higher & (rmfi < 0),
            'MF_Bear_Div': price_higher & mf_lower & (rmfi > 0),
            'MF_Accel_Up': up_streak >= 5,
            'MF_Accel_Dn': dn_streak >= 5,
            'MF_Slope_5': rmfi - rmfi.shift(5),
            'MF_Up_Streak': up_streak,
            'MF_Dn_Streak': dn_streak,
        }
    
    @staticmethod
    def inside_outside_day(high: pd.Series, low: pd.Series, close: pd.Series,
                           open_: pd.Series, wt1: pd.Series) -> Dict[str, pd.Series]:
        """Inside/Outside Day"""
        inside = (high < high.shift(1)) & (low > low.shift(1))
        outside = (high > high.shift(1)) & (low < low.shift(1))
        
        return {
            'Inside_Day': inside,
            'Outside_Bullish': outside & (close > open_) & (close > high.shift(1)) & (wt1 < 30),
            'Outside_Bearish': outside & (close < open_) & (close < low.shift(1)) & (wt1 > -30),
        }
    
    @staticmethod
    def bollinger_signals(close: pd.Series, bb_up: pd.Series, bb_low: pd.Series,
                          bb_width: pd.Series, wt1: pd.Series) -> Dict[str, pd.Series]:
        """볼린저 밴드 시그널"""
        width_avg = bb_width.rolling(20).mean()
        widening = (bb_width > bb_width.shift(1)) & (bb_width.shift(1) < width_avg.shift(1))
        
        return {
            'Above_Upper_BB': close > bb_up,
            'Below_Lower_BB': close < bb_low,
            'BB_Squeeze_End_Bull': widening & (close > close.shift(1)) & (wt1 > wt1.shift(1)),
            'BB_Squeeze_End_Bear': widening & (close < close.shift(1)) & (wt1 < wt1.shift(1)),
        }
    
    @staticmethod
    def macd_signals(macd_line: pd.Series, macd_signal: pd.Series) -> Dict[str, pd.Series]:
        """MACD 시그널"""
        return {
            'MACD_Zero_Cross_Buy': (macd_line > 0) & (macd_line.shift(1) <= 0),
            'MACD_Zero_Cross_Sell': (macd_line < 0) & (macd_line.shift(1) >= 0),
        }


# ──────────────────────────────────────────
# Jeff Cooper 패턴
# ──────────────────────────────────────────
class CooperPatterns:
    """Jeff Cooper 트레이딩 패턴"""
    
    @staticmethod
    def pullback_123(high: pd.Series, low: pd.Series, close: pd.Series,
                     adx: pd.Series, plus_di: pd.Series, 
                     minus_di: pd.Series) -> Tuple[pd.Series, pd.Series]:
        strong_bull = (adx > 30) & (plus_di > minus_di)
        strong_bear = (adx > 30) & (minus_di > plus_di)
        
        inside = (high < high.shift(1)) & (low > low.shift(1))
        
        # 3일 연속 저점 하락
        ll = (low < low.shift(1)) & (low.shift(1) < low.shift(2)) & (low.shift(2) < low.shift(3))
        ll_inside = ((low < low.shift(1)) & (low.shift(1) < low.shift(2)) & inside.shift(2)) | \
                    ((low < low.shift(1)) & inside.shift(1) & (low.shift(1) < low.shift(2).shift(1))) | \
                    (inside & (low < low.shift(1)) & (low.shift(1) < low.shift(2)))
        
        # 3일 연속 고점 상승
        hh = (high > high.shift(1)) & (high.shift(1) > high.shift(2)) & (high.shift(2) > high.shift(3))
        hh_inside = ((high > high.shift(1)) & (high.shift(1) > high.shift(2)) & inside.shift(2)) | \
                    ((high > high.shift(1)) & inside.shift(1) & (high.shift(1) > high.shift(2).shift(1))) | \
                    (inside & (high > high.shift(1)) & (high.shift(1) > high.shift(2)))
        
        return strong_bull & (ll | ll_inside), strong_bear & (hh | hh_inside)
    
    @staticmethod
    def setup_180(close: pd.Series, open_: pd.Series, high: pd.Series,
                  low: pd.Series, ma10: pd.Series, ma50: pd.Series) -> Tuple[pd.Series, pd.Series]:
        daily_range = high - low + 1e-10
        close_pos = (close - low) / daily_range
        prev_pos = (close.shift(1) - low.shift(1)) / (high.shift(1) - low.shift(1) + 1e-10)
        
        bull = (prev_pos <= 0.25) & (close_pos >= 0.75) & (close > ma10) & (close > ma50)
        bear = (prev_pos >= 0.75) & (close_pos <= 0.25) & (close < ma10) & (close < ma50)
        
        return bull, bear
    
    @staticmethod
    def boomer(high: pd.Series, low: pd.Series, adx: pd.Series,
               plus_di: pd.Series, minus_di: pd.Series) -> Tuple[pd.Series, pd.Series]:
        inside = (high < high.shift(1)) & (low > low.shift(1))
        two_inside = inside & inside.shift(1)
        
        bull = two_inside.shift(1).fillna(False) & (adx > 30) & (plus_di > minus_di)
        bear = two_inside.shift(1).fillna(False) & (adx > 30) & (minus_di > plus_di)
        
        return bull, bear
    
    @staticmethod
    def expansion(high: pd.Series, low: pd.Series, close: pd.Series) -> Tuple[pd.Series, pd.Series]:
        daily_range = high - low
        max_range_9 = daily_range.rolling(9).max()
        high_60 = high.rolling(60, min_periods=40).max()
        low_60 = low.rolling(60, min_periods=40).min()
        
        breakout = (high >= high_60) & (daily_range >= max_range_9)
        breakdown = (low <= low_60) & (daily_range >= max_range_9)
        
        return breakout, breakdown
    
    @staticmethod
    def gilligans(open_: pd.Series, close: pd.Series, high: pd.Series,
                  low: pd.Series) -> Tuple[pd.Series, pd.Series]:
        daily_range = high - low + 1e-10
        close_pos = (close - low) / daily_range
        
        low_60 = low.rolling(60, min_periods=40).min()
        high_60 = high.rolling(60, min_periods=40).max()
        
        buy = (open_ <= low_60) & (open_ < low.shift(1)) & (close_pos >= 0.5) & (close >= open_)
        sell = (open_ >= high_60) & (open_ > high.shift(1)) & (close_pos <= 0.5) & (close <= open_)
        
        return buy, sell
    
    @staticmethod
    def lizard(open_: pd.Series, close: pd.Series, high: pd.Series,
               low: pd.Series) -> Tuple[pd.Series, pd.Series]:
        daily_range = high - low + 1e-10
        close_pos = (close - low) / daily_range
        open_pos = (open_ - low) / daily_range
        
        low_10 = low.rolling(10).min()
        high_10 = high.rolling(10).max()
        
        bull = (close_pos >= 0.75) & (open_pos >= 0.75) & (low <= low_10)
        bear = (close_pos <= 0.25) & (open_pos <= 0.25) & (high >= high_10)
        
        return bull, bear
    
    @staticmethod
    def non_adx_123(high: pd.Series, low: pd.Series, close: pd.Series,
                    ma50: pd.Series) -> Tuple[pd.Series, pd.Series]:
        inside = (high < high.shift(1)) & (low > low.shift(1))
        
        ll = (low < low.shift(1)) & (low.shift(1) < low.shift(2)) & (low.shift(2) < low.shift(3))
        ll_inside = ((low < low.shift(1)) & (low.shift(1) < low.shift(2)) & inside.shift(2)) | \
                    ((low < low.shift(1)) & inside.shift(1) & (low.shift(1) < low.shift(2).shift(1))) | \
                    (inside & (low < low.shift(1)) & (low.shift(1) < low.shift(2)))
        
        hh = (high > high.shift(1)) & (high.shift(1) > high.shift(2)) & (high.shift(2) > high.shift(3))
        hh_inside = ((high > high.shift(1)) & (high.shift(1) > high.shift(2)) & inside.shift(2)) | \
                    ((high > high.shift(1)) & inside.shift(1) & (high.shift(1) > high.shift(2).shift(1))) | \
                    (inside & (high > high.shift(1)) & (high.shift(1) > high.shift(2)))
        
        return (close > ma50) & (ll | ll_inside), (close < ma50) & (hh | hh_inside)
    
    @staticmethod
    def pocket_pivot(close: pd.Series, open_: pd.Series, volume: pd.Series,
                     ma50: pd.Series, ma200: pd.Series) -> pd.Series:
        down_vol = volume.where(close < close.shift(1), 0)
        max_down_vol_10 = down_vol.rolling(10).max()
        
        return (close > open_) & (volume > max_down_vol_10) & (close > ma50) & (close > close.shift(1))
    
# ══════════════════════════════════════════════════════════════
#  CipherX V12.0 — PART 3/4: 판단 엔진 + 콤보 + 통합 탐지
# ══════════════════════════════════════════════════════════════

# ──────────────────────────────────────────
# 통합 시그널 탐지 엔진
# ──────────────────────────────────────────
def detect_all_signals(df: pd.DataFrame) -> pd.DataFrame:
    """모든 시그널 통합 탐지"""
    H, L, C, O, V = df['High'], df['Low'], df['Close'], df['Open'], df['Volume']
    e8, e21 = df['EMA8'], df['EMA21']
    m10, m20, m50, m200 = df['MA10'], df['MA20'], df['MA50'], df['MA200']
    wt1, wt2, atr = df['WT1'], df['WT2'], df['ATR']
    
    # 기본 필터
    vok = _volume_filter(V, 0.5)
    vok_strong = _volume_filter(V, 0.7)
    
    # HTF 추세 확인
    htf1 = (e8 > e21) & (e21 > e21.shift(5))
    htf2 = (C > m50) & (m50 > m50.shift(10))
    
    # 최근 WT 교차
    wt_up_recent = _recent(df['WT_Up'], 2)
    wt_down_recent = _recent(df['WT_Down'], 2)
    
    # 강세/약세 추세 환경
    strong_bull = (df['ADX'] > 25) & (df['Plus_DI'] > df['Minus_DI']) & (C > m50)
    strong_bear = (df['ADX'] > 25) & (df['Minus_DI'] > df['Plus_DI']) & (C < m50)
    extended_bull = strong_bull & (C > m200) & (m50 > m50.shift(5))
    extended_bear = strong_bear & (C < m200) & (m50 < m50.shift(5))
    
    # MF 기본 필터
    mf_bullish = df['RSI_MFI'] > -10
    mf_bearish = df['RSI_MFI'] < 10
    
    # ═══ 극단 조건 탐지 ═══
    para_bot = ((wt1 < -85) & (wt1 > wt1.shift(1)) & (C > O)) | ((C < df['BB_Low'] - atr * 1.5) & (C > O))
    para_top = ((wt1 > 85) & (wt1 < wt1.shift(1)) & (C < O)) | ((C > df['BB_Up'] + atr * 1.5) & (C < O))
    
    # SuperTrend 전환
    st_flip_bear = (df['ST_Direction'] == -1) & (df['ST_Direction'].shift(1) == 1)
    st_flip_bull = (df['ST_Direction'] == 1) & (df['ST_Direction'].shift(1) == -1)
    st_flip_bear.iloc[:Config.ST_MIN_BAR] = False
    st_flip_bull.iloc[:Config.ST_MIN_BAR] = False
    
    # 실드 오버라이드 조건
    sell_shield_off = para_top | _recent(st_flip_bear, 3)
    buy_shield_off = para_bot | _recent(st_flip_bull, 3)
    
    # 시그널 억제 조건 (방향 반대일 때만)
    suppress_buy = extended_bear & (~para_bot) & (~_recent(st_flip_bull, 3))
    suppress_sell = extended_bull & (~para_top) & (~_recent(st_flip_bear, 3))
    
    # ═══ MCB+ 핵심 시그널 ═══
    # Green Dots
    df['Green_Dot_T1'] = (
        wt_up_recent & (wt1 <= Config.WT_OS1) & 
        (df['RSI'] < 30) & (df['MFI'] < 30) & (df['RSI_MFI'] < 0) & 
        (~suppress_buy) & vok
    )
    df['Green_Dot_T2'] = (
        wt_up_recent & (wt1 <= Config.WT_OS1) & 
        ((df['RSI'] < 32) | (df['MFI'] < 32)) & 
        ~df['Green_Dot_T1'] & (~suppress_buy) & vok
    )
    _any_green = df['Green_Dot_T1'] | df['Green_Dot_T2']
    
    # Red Dots
    df['Red_Dot_T1'] = (
        wt_down_recent & (wt1 >= Config.WT_OB1) & 
        (df['RSI'] > 70) & (df['MFI'] > 70) & (df['RSI_MFI'] > 0) & 
        (~suppress_sell) & vok
    )
    df['Red_Dot_T2'] = (
        wt_down_recent & (wt1 >= Config.WT_OB1) & 
        ((df['RSI'] > 68) | (df['MFI'] > 68)) & 
        ~df['Red_Dot_T1'] & (~suppress_sell) & vok
    )
    _any_red = df['Red_Dot_T1'] | df['Red_Dot_T2']
    
    # Diamonds
    df['Blue_Diamond'] = (wt2 <= 0) & wt_up_recent & htf1 & htf2 & (~suppress_buy) & mf_bullish & vok
    df['Red_Diamond'] = (wt2 >= 0) & wt_down_recent & ~htf1 & ~htf2 & (~suppress_sell) & mf_bearish & vok
    
    # Circles
    df['Green_Circle'] = wt_up_recent & (wt1 <= Config.WT_OS1) & ~_any_green & (~suppress_buy) & vok & (df['RSI'] < 45)
    df['Red_Circle'] = wt_down_recent & (wt1 >= Config.WT_OB1) & ~_any_red & (~suppress_sell) & vok & (df['RSI'] > 55)
    
    # ═══ 다이버전스 ═══
    bull_div, bear_div, hidden_bull, hidden_bear = SignalDetector.pivot_divergence(
        C, wt1, 60, 5, Config.WT_OS1, Config.WT_OB1
    )
    rsi_bull_div, rsi_bear_div, _, _ = SignalDetector.pivot_divergence(C, df['RSI'], 60, 5, 35, 65)
    obv_bull_div, obv_bear_div, _, _ = SignalDetector.pivot_divergence(C, df['OBV'], 60, 5)
    
    bull_div_recent = _recent(bull_div, 3)
    bear_div_recent = _recent(bear_div, 3)
    
    # Gold/Blood Dots (최강 시그널)
    df['Gold_Dot'] = df['Green_Dot_T1'] & (wt1 <= Config.WT_OS2) & bull_div_recent
    df['Blood_Diamond'] = df['Red_Dot_T1'] & (wt1 >= Config.WT_OB2) & bear_div_recent
    
    # 일반 다이버전스 (Gold/Blood와 중복 제거)
    df['Bull_Divergence'] = bull_div & wt_up_recent & ~_any_green & ~df['Gold_Dot'] & (~suppress_buy) & vok
    df['Bear_Divergence'] = bear_div & wt_down_recent & ~_any_red & (~suppress_sell) & vok
    df['RSI_Bull_Divergence'] = rsi_bull_div & (wt1 < -20) & (~suppress_buy) & vok & ~bull_div
    df['RSI_Bear_Divergence'] = rsi_bear_div & (wt1 > 20) & (~suppress_sell) & vok & ~bear_div
    df['Hidden_Bull_Div'] = hidden_bull & (wt1 < -25) & htf2 & (~suppress_buy) & vok_strong
    df['Hidden_Bear_Div'] = hidden_bear & (wt1 > 25) & ~htf2 & (~suppress_sell) & vok_strong
    df['OBV_Div_Buy'] = obv_bull_div & (wt1 < -30) & (~suppress_buy)
    df['OBV_Div_Sell'] = obv_bear_div & (wt1 > 30) & (~suppress_sell)
    
    # ═══ Squeeze ═══
    sq_on, sq_buy, sq_sell = SignalDetector.ttm_squeeze(
        df['BB_Up'], df['BB_Low'], df['KC_Upper'], df['KC_Lower'], C, H, L, df['KC_Mid']
    )
    df['Squeeze_On'] = sq_on
    df['Squeeze_Fire_Buy'] = sq_buy & (~suppress_buy) & vok
    df['Squeeze_Fire_Sell'] = sq_sell & (~suppress_sell) & vok
    
    # ═══ Volume Climax ═══
    df['Volume_Climax_Buy'], df['Volume_Climax_Sell'] = SignalDetector.volume_climax(C, O, V, wt1, atr)
    
    # ═══ ADX Momentum ═══
    adx_break = (df['ADX'] > 20) & (df['ADX'].shift(1) <= 20)
    df['ADX_Momentum_Buy'] = adx_break & (df['Plus_DI'] > df['Minus_DI']) & (wt1 > wt2) & vok
    df['ADX_Momentum_Sell'] = adx_break & (df['Minus_DI'] > df['Plus_DI']) & (wt1 < wt2) & vok
    
    # ═══ Engulfing ═══
    df['Bullish_Engulfing'], df['Bearish_Engulfing'] = SignalDetector.engulfing(C, O, wt1, atr)
    df['Bullish_Engulfing'] &= (~suppress_buy) & vok
    df['Bearish_Engulfing'] &= (~suppress_sell) & vok
    
    # ═══ Golden/Death Cross ═══
    gc = (m50 > m200) & (m50.shift(1) <= m200.shift(1))
    dc = (m50 < m200) & (m50.shift(1) >= m200.shift(1))
    adx_filter = df['ADX'] > 15
    df['Golden_Cross'] = gc & adx_filter & vok_strong
    df['Death_Cross'] = dc & adx_filter & vok_strong
    
    # ═══ EMA Pullback ═══
    df['EMA_Pullback_Buy'], df['EMA_Pullback_Sell'] = _detect_ema_pullback(
        C, H, L, V, e8, e21, atr, wt1, wt2
    )
    
    # ═══ Momentum Ignition ═══
    df['Momentum_Ignition_Buy'], df['Momentum_Ignition_Sell'] = _detect_momentum_ignition(
        C, O, V, df['BB_Up'], df['BB_Low'], atr, e8, e21, wt1, df['BB_Width']
    )
    
    # ═══ SuperTrend ═══
    df['SuperTrend_Buy'] = st_flip_bull
    df['SuperTrend_Sell'] = st_flip_bear
    
    # ═══ Parabolic ═══
    vp = _volume_filter(V, 1.0)
    df['Parabolic_Top_Sell'] = para_top & ((df['WT_Down'] | wt_down_recent) | ((C < O) & (C < C.shift(1)))) & vp
    df['Parabolic_Bottom_Buy'] = para_bot & ((df['WT_Up'] | wt_up_recent) | ((C > O) & (C > C.shift(1)))) & vp
    
    # ═══ VWAP ═══
    df['VWAP_Bounce_Buy'], df['VWAP_Reject_Sell'] = _detect_vwap(C, df['VWAP_Osc'], wt1, wt2, V, atr)
    
    # ═══ MACD Cross ═══
    ml, ms = df['MACD_Line'], df['MACD_Signal']
    df['MACD_Cross_Buy'] = (ml > ms) & (ml.shift(1) <= ms.shift(1)) & (ml < 0) & (~suppress_buy) & vok
    df['MACD_Cross_Sell'] = (ml < ms) & (ml.shift(1) >= ms.shift(1)) & (ml > 0) & (~suppress_sell) & vok
    
    # ═══ StochRSI Cross ═══
    df['StochRSI_Cross_Buy'] = (
        (df['StochK'] > df['StochD']) & (df['StochK'].shift(1) <= df['StochD'].shift(1)) & 
        (df['StochK'] < 25) & (~suppress_buy) & vok
    )
    df['StochRSI_Cross_Sell'] = (
        (df['StochK'] < df['StochD']) & (df['StochK'].shift(1) >= df['StochD'].shift(1)) & 
        (df['StochK'] > 75) & (~suppress_sell) & vok
    )
    
    # ═══ 캔들스틱 패턴 ═══
    candle_patterns = SignalDetector.candlestick_patterns(C, O, H, L, wt1, atr)
    for name, pattern in candle_patterns.items():
        is_buy = name in ['Hammer', 'Morning_Star', 'Doji_Bullish']
        suppress = suppress_buy if is_buy else suppress_sell
        df[name] = pattern & (~suppress) & vok
    
    # ═══ Inside/Outside Day ═══
    io_patterns = SignalDetector.inside_outside_day(H, L, C, O, wt1)
    for name, pattern in io_patterns.items():
        df[name] = pattern
    df['Outside_Bullish'] &= (~suppress_buy) & vok
    df['Outside_Bearish'] &= (~suppress_sell) & vok
    
    # ═══ MA Crossovers ═══
    ma_patterns = SignalDetector.ma_crossovers(C, m20, m50, m200)
    for name, pattern in ma_patterns.items():
        df[name] = pattern
    
    # ═══ Bollinger Signals ═══
    bb_patterns = SignalDetector.bollinger_signals(C, df['BB_Up'], df['BB_Low'], df['BB_Width'], wt1)
    for name, pattern in bb_patterns.items():
        df[name] = pattern
    
    # ═══ MACD Centerline ═══
    macd_patterns = SignalDetector.macd_signals(df['MACD_Line'], df['MACD_Signal'])
    for name, pattern in macd_patterns.items():
        df[name] = pattern
    
    # ═══ Consecutive Days ═══
    consec_patterns = SignalDetector.consecutive_days(C)
    for name, pattern in consec_patterns.items():
        df[name] = pattern
    
    # ═══ Gaps ═══
    gap_patterns = SignalDetector.gaps(C, O, H, L, atr)
    for name, pattern in gap_patterns.items():
        df[name] = pattern
    
    # ═══ NR7 / Volatility ═══
    nr7_patterns = SignalDetector.nr7_patterns(H, L, atr)
    for name, pattern in nr7_patterns.items():
        df[name] = pattern
    
    # ═══ 52 Week ═══
    df['New_52W_High'], df['New_52W_Low'] = SignalDetector.week_52_extremes(C, H, L)
    
    # ═══ Jeff Cooper Patterns ═══
    df['Pullback_123_Bull'], df['Pullback_123_Bear'] = CooperPatterns.pullback_123(H, L, C, df['ADX'], df['Plus_DI'], df['Minus_DI'])
    df['Setup_180_Bull'], df['Setup_180_Bear'] = CooperPatterns.setup_180(C, O, H, L, m10, m50)
    df['Boomer_Buy'], df['Boomer_Sell'] = CooperPatterns.boomer(H, L, df['ADX'], df['Plus_DI'], df['Minus_DI'])
    df['Expansion_BO'], df['Expansion_BD'] = CooperPatterns.expansion(H, L, C)
    df['Gilligans_Buy'], df['Gilligans_Sell'] = CooperPatterns.gilligans(O, C, H, L)
    df['Lizard_Bull'], df['Lizard_Bear'] = CooperPatterns.lizard(O, C, H, L)
    df['NonADX_123_Bull'], df['NonADX_123_Bear'] = CooperPatterns.non_adx_123(H, L, C, m50)
    df['Pocket_Pivot'] = CooperPatterns.pocket_pivot(C, O, V, m50, m200)
    
    # ═══ Money Flow Signals ═══
    mf_patterns = SignalDetector.money_flow_signals(C, df['RSI_MFI'])
    for name, pattern in mf_patterns.items():
        if isinstance(pattern, pd.Series) and pattern.dtype == bool:
            is_buy = 'Bull' in name or 'Up' in name
            suppress = suppress_buy if is_buy else suppress_sell
            df[name] = pattern & (~suppress) & vok if name in ['MF_Cross_Bull', 'MF_Cross_Bear', 'MF_Bull_Div', 'MF_Bear_Div'] else pattern
        else:
            df[name] = pattern
    
    # ═══ 쿨다운 적용 ═══
    _apply_cooldowns(df)
    
    # ═══ 중복 제거 ═══
    _deduplicate_signals(df)
    
    # ═══ Confluence 계산 ═══
    compute_confluence(df)
    
    # ═══ Proximity 계산 ═══
    df['Buy_Proximity'], df['Sell_Proximity'] = compute_proximity(df)
    
    # ═══ 메타 정보 ═══
    df['Strong_Bull'] = strong_bull
    df['Strong_Bear'] = strong_bear
    df['Sell_Shield_Overridden'] = sell_shield_off
    df['Buy_Shield_Overridden'] = buy_shield_off
    df['_HTF1_Bull'] = htf1
    df['_HTF2_Bull'] = htf2
    
    # ═══ 7-Layer 판단 ═══
    compute_trade_judgment(df)
    
    return df


def _detect_ema_pullback(C, H, L, V, e8, e21, atr, wt1, wt2):
    """EMA Pullback 탐지"""
    vok = _volume_filter(V, 0.5)
    ar = atr / C
    
    # 매수
    slope_up = e21 > e21.shift(5)
    trend_up = (e8 > e21) & slope_up
    touch_up = (L <= e8 * (1 + ar * 0.15)) & (L >= e21 * (1 - ar * 0.25))
    touch_recent_up = _recent(touch_up, 2)
    breakout_up = (C >= e8) & (C > H.shift(1))
    wt_ok_up = (wt1 > wt1.shift(1)) & (wt1 > wt2) & (wt1 < 60)
    buy = trend_up & (C > e8) & touch_recent_up & breakout_up & wt_ok_up & vok
    
    # 매도
    slope_dn = e21 < e21.shift(5)
    trend_dn = (e8 < e21) & slope_dn
    touch_dn = (H >= e8 * (1 - ar * 0.15)) & (H <= e21 * (1 + ar * 0.25))
    touch_recent_dn = _recent(touch_dn, 2)
    breakout_dn = (C <= e8) & (C < L.shift(1))
    wt_ok_dn = (wt1 < wt1.shift(1)) & (wt1 < wt2) & (wt1 > -60)
    sell = trend_dn & (C < e8) & touch_recent_dn & breakout_dn & wt_ok_dn & vok
    
    return buy, sell


def _detect_momentum_ignition(C, O, V, bb_up, bb_low, atr, e8, e21, wt1, bb_w):
    """Momentum Ignition 탐지"""
    body = (C - O).abs()
    big_body = body > atr * 1.5
    high_vol = V > V.rolling(20).mean() * 2.0
    compressed = bb_w.shift(1) < bb_w.rolling(20).mean().shift(1)
    
    buy = (C > O) & big_body & high_vol & (C > bb_up) & (e8 > e21) & (wt1 < 50) & compressed
    sell = (C < O) & big_body & high_vol & (C < bb_low) & (e8 < e21) & (wt1 > -50) & compressed
    
    return buy, sell


def _detect_vwap(C, vwap_osc, wt1, wt2, V, atr):
    """VWAP 시그널 탐지"""
    vok = _volume_filter(V, 0.7)
    ap = (atr / C * 100).clip(0.3, 3.0)
    dt = (ap * 0.3).clip(0.3, 1.5)
    
    buy = (vwap_osc > 0) & (vwap_osc.shift(1) < -dt) & (wt1 > wt2) & (wt1 < 30) & vok
    sell = (vwap_osc < 0) & (vwap_osc.shift(1) > dt) & (wt1 < wt2) & (wt1 > -30) & vok
    
    return buy, sell


def _apply_cooldowns(df: pd.DataFrame) -> None:
    """쿨다운 적용 (벡터화)"""
    # 페어 시그널 (방향별 독립 쿨다운)
    paired_signals = [
        ('MACD_Cross_Buy', 'MACD_Cross_Sell', 12),
        ('StochRSI_Cross_Buy', 'StochRSI_Cross_Sell', 7),
        ('EMA_Pullback_Buy', 'EMA_Pullback_Sell', 7),
        ('Momentum_Ignition_Buy', 'Momentum_Ignition_Sell', 10),
        ('VWAP_Bounce_Buy', 'VWAP_Reject_Sell', 7),
        ('ADX_Momentum_Buy', 'ADX_Momentum_Sell', 10),
        ('Squeeze_Fire_Buy', 'Squeeze_Fire_Sell', 5),
        ('Bullish_Engulfing', 'Bearish_Engulfing', 5),
        ('Hammer', 'Shooting_Star', 5),
        ('Morning_Star', 'Evening_Star', 7),
        ('Doji_Bullish', 'Doji_Bearish', 5),
        ('Outside_Bullish', 'Outside_Bearish', 7),
        ('BB_Squeeze_End_Bull', 'BB_Squeeze_End_Bear', 7),
        ('MACD_Zero_Cross_Buy', 'MACD_Zero_Cross_Sell', 12),
        ('Pullback_123_Bull', 'Pullback_123_Bear', 7),
        ('Setup_180_Bull', 'Setup_180_Bear', 7),
        ('Boomer_Buy', 'Boomer_Sell', 10),
        ('Expansion_BO', 'Expansion_BD', 10),
        ('Gilligans_Buy', 'Gilligans_Sell', 10),
        ('Lizard_Bull', 'Lizard_Bear', 5),
        ('NonADX_123_Bull', 'NonADX_123_Bear', 7),
        ('MF_Cross_Bull', 'MF_Cross_Bear', 10),
        ('MF_Bull_Div', 'MF_Bear_Div', 10),
    ]
    
    handled = set()
    for buy_sig, sell_sig, cd in paired_signals:
        _cooldown_paired(df, buy_sig, sell_sig, cd)
        handled.add(buy_sig)
        handled.add(sell_sig)
    
    # 나머지 시그널
    single_cooldowns = {
        'Gold_Dot': 10, 'Blood_Diamond': 10,
        'Green_Dot_T1': 8, 'Red_Dot_T1': 8,
        'Green_Dot_T2': 5, 'Red_Dot_T2': 5,
        'Bull_Divergence': 10, 'Bear_Divergence': 10,
        'RSI_Bull_Divergence': 10, 'RSI_Bear_Divergence': 10,
        'Hidden_Bull_Div': 10, 'Hidden_Bear_Div': 10,
        'Golden_Cross': 20, 'Death_Cross': 20,
        'SuperTrend_Buy': 7, 'SuperTrend_Sell': 7,
        'Parabolic_Bottom_Buy': 5, 'Parabolic_Top_Sell': 5,
        'Volume_Climax_Buy': 7, 'Volume_Climax_Sell': 7,
        'Pocket_Pivot': 10,
        'New_52W_High': 10, 'New_52W_Low': 10,
        'Gap_Up': 3, 'Gap_Down': 3,
        'Gap_Up_Closed': 5, 'Gap_Down_Closed': 5,
        'Blue_Diamond': 7, 'Red_Diamond': 7,
    }
    
    for sig, cd in single_cooldowns.items():
        if sig in df.columns and sig not in handled:
            df[sig] = _cooldown_vectorized(df[sig], cd)


def _deduplicate_signals(df: pd.DataFrame) -> None:
    """계층적 시그널 중복 제거"""
    for _category, signals in SIGNAL_HIERARCHY.items():
        for i, sig in enumerate(signals):
            if sig not in df.columns:
                continue
            # 상위 시그널이 있으면 하위 시그널 제거
            for higher in signals[:i]:
                if higher in df.columns:
                    df[sig] = df[sig] & ~df[higher]


# ──────────────────────────────────────────
# 7-Layer 판단 엔진 (최적화)
# ──────────────────────────────────────────
def compute_trade_judgment(df: pd.DataFrame) -> None:
    """7-Layer 스코어링 → BUY/SELL 판단"""
    C, O, H, L = df['Close'], df['Open'], df['High'], df['Low']
    idx = df.index
    n = len(df)
    
    # 공통 계산
    above_200 = C > df['MA200']
    above_50 = C > df['MA50']
    above_20 = C > df['MA20']
    below_200 = C < df['MA200']
    below_50 = C < df['MA50']
    
    ma50_rising = df['MA50'] > df['MA50'].shift(5)
    ma50_falling = df['MA50'] < df['MA50'].shift(5)
    
    vol_ratio = df['Volume'] / (df['Volume'].rolling(50, min_periods=10).mean() + 1e-10)
    
    # MACD 방향
    macd_h = df['MACD_Hist']
    macd_rising = macd_h > macd_h.shift(1)
    macd_falling = macd_h < macd_h.shift(1)
    
    # OBV 추세
    obv = df['OBV']
    obv_ma20 = obv.rolling(20, min_periods=10).mean()
    obv_above = obv > obv_ma20
    
    # 추세 맥락
    in_downtrend = below_50 | (df['WT1'] < -20) | (df['RSI'] < 45)
    in_uptrend = above_50 | (df['WT1'] > 20) | (df['RSI'] > 55)
    
    # ══════════════ BUY 레이어 ══════════════
    
    # Layer 1: Trend (max 8)
    buy_trend = pd.Series(0.0, index=idx)
    buy_trend += np.where(above_200 & above_50 & above_20, 4.0,
                 np.where(above_200 & above_50, 3.0,
                 np.where(above_200, 2.0,
                 np.where(above_50, 1.0, 0))))
    buy_trend += np.where(df['MA50'] > df['MA200'], 1.5, 0)
    buy_trend += np.where(df['Plus_DI'] > df['Minus_DI'], 1.0, 0)
    buy_trend += np.where(df['ST_Direction'] == 1, 1.0, 0)
    buy_trend += np.where(ma50_rising & above_50, 0.5, 0)
    df['BJ_Trend'] = buy_trend.clip(upper=Config.LAYER_MAX['Trend'])
    
    # Layer 2: Momentum (max 8) - 크로스오버 캡 적용
    buy_mom = pd.Series(0.0, index=idx)
    
    # 크로스오버 시그널 (캡 4점)
    cross_pts = pd.Series(0.0, index=idx)
    for sig, pts in [('MACD_Cross_Buy', 2.0), ('MACD_Zero_Cross_Buy', 1.5),
                     ('StochRSI_Cross_Buy', 1.5), ('ADX_Momentum_Buy', 1.5)]:
        cross_pts += np.where(df.get(sig, pd.Series(False, index=idx)).fillna(False), pts, 0)
    buy_mom += cross_pts.clip(upper=4.0)
    
    # MACD 히스토그램 상태
    buy_mom += np.where((macd_h > 0) & macd_rising, 1.5,
               np.where((macd_h < 0) & macd_rising, 1.0, 0))
    
    # 오실레이터 상태 (방향 + 레벨)
    buy_mom += np.where((df['RSI'] < 30) & (df['RSI'] > df['RSI'].shift(1)), 1.5,
               np.where(df['RSI'] < 35, 0.5, 0))
    buy_mom += np.where((df['StochK'] < 20) & (df['StochK'] > df['StochK'].shift(1)), 1.0,
               np.where(df['StochK'] < 25, 0.5, 0))
    
    df['BJ_Momentum'] = buy_mom.clip(upper=Config.LAYER_MAX['Momentum'])
    
    # Layer 3: Candle (max 6) - 최고 1개만
    candle_scores = []
    for sig, base, ctx_bonus in [
        ('Morning_Star', 2.5, 1.0),
        ('Bullish_Engulfing', 2.0, 1.0),
        ('Hammer', 1.5, 0.5),
        ('Outside_Bullish', 1.5, 0.5),
        ('Doji_Bullish', 0.8, 0.2),
    ]:
        raw = df.get(sig, pd.Series(False, index=idx)).fillna(False)
        pts = np.where(raw & in_downtrend, base + ctx_bonus, np.where(raw, base, 0))
        candle_scores.append(pts)
    
    df['BJ_Candle'] = pd.Series(np.max(candle_scores, axis=0), index=idx).clip(upper=Config.LAYER_MAX['Candle'])
    
    # Layer 4: BB (max 5)
    buy_bb = pd.Series(0.0, index=idx)
    buy_bb += np.where(df.get('BB_Squeeze_End_Bull', pd.Series(False, index=idx)).fillna(False), 2.5, 0)
    buy_bb += np.where(df.get('NR7', pd.Series(False, index=idx)).fillna(False), 0.5, 0)
    buy_bb += np.where(df.get('Calm_After_Storm', pd.Series(False, index=idx)).fillna(False), 0.5, 0)
    
    pct_b = df['Percent_B']
    buy_bb += np.where(pct_b < 0.1, 2.0, np.where(pct_b < 0.2, 1.0, 0))
    
    df['BJ_BB'] = buy_bb.clip(upper=Config.LAYER_MAX['BB'])
    
    # Layer 5: Volume (max 5)
    buy_vol = pd.Series(0.0, index=idx)
    buy_vol += np.where(df.get('Volume_Climax_Buy', pd.Series(False, index=idx)).fillna(False), 2.5, 0)
    buy_vol += np.where(df.get('Pocket_Pivot', pd.Series(False, index=idx)).fillna(False), 1.5, 0)
    buy_vol += np.where((vol_ratio >= 2.0) & (C > O), 1.5, np.where((vol_ratio >= 1.5) & (C > O), 0.8, 0))
    buy_vol += np.where(obv_above & (obv > obv.shift(5)), 1.0, 0)
    
    df['BJ_Volume'] = buy_vol.clip(upper=Config.LAYER_MAX['Volume'])
    
    # Layer 6: Money Flow (max 5)
    buy_mf = pd.Series(0.0, index=idx)
    rmfi = df['RSI_MFI']
    buy_mf += np.where(rmfi < -10, 1.5, np.where(rmfi < -5, 0.8, 0))
    
    mf_slope = df.get('MF_Slope_5', pd.Series(0, index=idx))
    buy_mf += np.where(mf_slope > 5, 1.5, np.where(mf_slope > 2, 0.8, 0))
    
    buy_mf += np.where(df.get('MF_Cross_Bull', pd.Series(False, index=idx)).fillna(False), 1.5, 0)
    buy_mf += np.where(df.get('MF_Bull_Div', pd.Series(False, index=idx)).fillna(False), 1.5, 0)
    
    df['BJ_MF'] = buy_mf.clip(upper=Config.LAYER_MAX['MF'])
    
    # Layer 7: Pattern (max 8) - 시그널만 (지표 중복 제거)
    buy_pat = pd.Series(0.0, index=idx)
    
    # MCB+ 계층적 (Gold > T1 > T2)
    gold = np.where(df.get('Gold_Dot', pd.Series(False, index=idx)).fillna(False), 3.5, 0)
    t1 = np.where((gold == 0) & df.get('Green_Dot_T1', pd.Series(False, index=idx)).fillna(False), 2.5, 0)
    t2 = np.where((gold == 0) & (t1 == 0) & df.get('Green_Dot_T2', pd.Series(False, index=idx)).fillna(False), 1.5, 0)
    buy_pat += gold + t1 + t2
    
    # 다이버전스 (Gold와 중복 방지)
    div_pts = np.where((gold == 0) & df.get('Bull_Divergence', pd.Series(False, index=idx)).fillna(False), 2.0, 0)
    buy_pat += div_pts
    
    # 기타 패턴
    for sig, pts in [
        ('Blue_Diamond', 1.5), ('Expansion_BO', 2.5), ('Pullback_123_Bull', 2.0),
        ('Setup_180_Bull', 1.5), ('EMA_Pullback_Buy', 1.5), ('Momentum_Ignition_Buy', 2.5),
        ('SuperTrend_Buy', 1.5), ('Parabolic_Bottom_Buy', 2.5), ('Gilligans_Buy', 2.0),
        ('Cross_Above_50MA', 1.0), ('Cross_Above_200MA', 1.5), ('Golden_Cross', 1.5),
    ]:
        buy_pat += np.where(df.get(sig, pd.Series(False, index=idx)).fillna(False), pts, 0)
    
    df['BJ_Pattern'] = buy_pat.clip(upper=Config.LAYER_MAX['Pattern'])
    
    # BUY 합계
    df['Buy_Total'] = (df['BJ_Trend'] + df['BJ_Momentum'] + df['BJ_Candle'] + 
                       df['BJ_BB'] + df['BJ_Volume'] + df['BJ_MF'] + df['BJ_Pattern'])
    
    # ══════════════ SELL 레이어 (대칭 구조) ══════════════
    
    # Layer 1: Trend
    sell_trend = pd.Series(0.0, index=idx)
    sell_trend += np.where(below_200 & below_50 & (C < df['MA20']), 4.0,
                  np.where(below_200 & below_50, 3.0,
                  np.where(below_200, 2.0,
                  np.where(below_50, 1.0, 0))))
    sell_trend += np.where(df['MA50'] < df['MA200'], 1.5, 0)
    sell_trend += np.where(df['Minus_DI'] > df['Plus_DI'], 1.0, 0)
    sell_trend += np.where(df['ST_Direction'] == -1, 1.0, 0)
    sell_trend += np.where(ma50_falling & below_50, 0.5, 0)
    df['SJ_Trend'] = sell_trend.clip(upper=Config.LAYER_MAX['Trend'])
    
    # Layer 2: Momentum
    sell_mom = pd.Series(0.0, index=idx)
    cross_pts_s = pd.Series(0.0, index=idx)
    for sig, pts in [('MACD_Cross_Sell', 2.0), ('MACD_Zero_Cross_Sell', 1.5),
                     ('StochRSI_Cross_Sell', 1.5), ('ADX_Momentum_Sell', 1.5)]:
        cross_pts_s += np.where(df.get(sig, pd.Series(False, index=idx)).fillna(False), pts, 0)
    sell_mom += cross_pts_s.clip(upper=4.0)
    
    sell_mom += np.where((macd_h < 0) & macd_falling, 1.5,
                np.where((macd_h > 0) & macd_falling, 1.0, 0))
    sell_mom += np.where((df['RSI'] > 70) & (df['RSI'] < df['RSI'].shift(1)), 1.5,
                np.where(df['RSI'] > 65, 0.5, 0))
    sell_mom += np.where((df['StochK'] > 80) & (df['StochK'] < df['StochK'].shift(1)), 1.0,
                np.where(df['StochK'] > 75, 0.5, 0))
    
    df['SJ_Momentum'] = sell_mom.clip(upper=Config.LAYER_MAX['Momentum'])
    
    # Layer 3: Candle
    candle_scores_s = []
    for sig, base, ctx_bonus in [
        ('Evening_Star', 2.5, 1.0),
        ('Bearish_Engulfing', 2.0, 1.0),
        ('Shooting_Star', 1.5, 0.5),
        ('Outside_Bearish', 1.5, 0.5),
        ('Doji_Bearish', 0.8, 0.2),
    ]:
        raw = df.get(sig, pd.Series(False, index=idx)).fillna(False)
        pts = np.where(raw & in_uptrend, base + ctx_bonus, np.where(raw, base, 0))
        candle_scores_s.append(pts)
    
    df['SJ_Candle'] = pd.Series(np.max(candle_scores_s, axis=0), index=idx).clip(upper=Config.LAYER_MAX['Candle'])
    
    # Layer 4: BB
    sell_bb = pd.Series(0.0, index=idx)
    sell_bb += np.where(df.get('BB_Squeeze_End_Bear', pd.Series(False, index=idx)).fillna(False), 2.5, 0)
    sell_bb += np.where(df.get('NR7', pd.Series(False, index=idx)).fillna(False), 0.5, 0)
    sell_bb += np.where(pct_b > 0.9, 2.0, np.where(pct_b > 0.8, 1.0, 0))
    df['SJ_BB'] = sell_bb.clip(upper=Config.LAYER_MAX['BB'])
    
    # Layer 5: Volume
    sell_vol = pd.Series(0.0, index=idx)
    sell_vol += np.where(df.get('Volume_Climax_Sell', pd.Series(False, index=idx)).fillna(False), 2.5, 0)
    sell_vol += np.where((vol_ratio >= 2.0) & (C < O), 1.5, np.where((vol_ratio >= 1.5) & (C < O), 0.8, 0))
    sell_vol += np.where(~obv_above & (obv < obv.shift(5)), 1.0, 0)
    df['SJ_Volume'] = sell_vol.clip(upper=Config.LAYER_MAX['Volume'])
    
    # Layer 6: Money Flow
    sell_mf = pd.Series(0.0, index=idx)
    sell_mf += np.where(rmfi > 10, 1.5, np.where(rmfi > 5, 0.8, 0))
    sell_mf += np.where(mf_slope < -5, 1.5, np.where(mf_slope < -2, 0.8, 0))
    sell_mf += np.where(df.get('MF_Cross_Bear', pd.Series(False, index=idx)).fillna(False), 1.5, 0)
    sell_mf += np.where(df.get('MF_Bear_Div', pd.Series(False, index=idx)).fillna(False), 1.5, 0)
    df['SJ_MF'] = sell_mf.clip(upper=Config.LAYER_MAX['MF'])
    
    # Layer 7: Pattern
    sell_pat = pd.Series(0.0, index=idx)
    blood = np.where(df.get('Blood_Diamond', pd.Series(False, index=idx)).fillna(False), 3.5, 0)
    rt1 = np.where((blood == 0) & df.get('Red_Dot_T1', pd.Series(False, index=idx)).fillna(False), 2.5, 0)
    rt2 = np.where((blood == 0) & (rt1 == 0) & df.get('Red_Dot_T2', pd.Series(False, index=idx)).fillna(False), 1.5, 0)
    sell_pat += blood + rt1 + rt2
    
    div_pts_s = np.where((blood == 0) & df.get('Bear_Divergence', pd.Series(False, index=idx)).fillna(False), 2.0, 0)
    sell_pat += div_pts_s
    
    for sig, pts in [
        ('Red_Diamond', 1.5), ('Expansion_BD', 2.5), ('Pullback_123_Bear', 2.0),
        ('Setup_180_Bear', 1.5), ('EMA_Pullback_Sell', 1.5), ('Momentum_Ignition_Sell', 2.5),
        ('SuperTrend_Sell', 1.5), ('Parabolic_Top_Sell', 2.5), ('Gilligans_Sell', 2.0),
        ('Fell_Below_50MA', 1.0), ('Fell_Below_200MA', 1.5), ('Death_Cross', 1.5),
    ]:
        sell_pat += np.where(df.get(sig, pd.Series(False, index=idx)).fillna(False), pts, 0)
    
    df['SJ_Pattern'] = sell_pat.clip(upper=Config.LAYER_MAX['Pattern'])
    
    # SELL 합계
    df['Sell_Total'] = (df['SJ_Trend'] + df['SJ_Momentum'] + df['SJ_Candle'] + 
                        df['SJ_BB'] + df['SJ_Volume'] + df['SJ_MF'] + df['SJ_Pattern'])
    
    # ══════════════ 콤보 보너스 ══════════════
    detect_combos(df, vol_ratio)
    
    buy_combo_bonus = pd.Series(0.0, index=idx)
    sell_combo_bonus = pd.Series(0.0, index=idx)
    
    for col, (name, direction, bonus) in COMBO_CONFIG.items():
        if col in df.columns:
            if direction == 'buy':
                buy_combo_bonus += np.where(df[col], bonus, 0)
            else:
                sell_combo_bonus += np.where(df[col], bonus, 0)
    
    df['Buy_Total'] += buy_combo_bonus.clip(upper=6.0)  # 콤보 보너스 최대 6점
    df['Sell_Total'] += sell_combo_bonus.clip(upper=6.0)
    
    # 활성 레이어 수
    df['Buy_Active_Layers'] = sum((df[f'BJ_{n}'] > 0).astype(int) for n in ['Trend','Momentum','Candle','BB','Volume','MF','Pattern'])
    df['Sell_Active_Layers'] = sum((df[f'SJ_{n}'] > 0).astype(int) for n in ['Trend','Momentum','Candle','BB','Volume','MF','Pattern'])
    
    # ══════════════ 최종 판단 ══════════════
    _compute_final_judgment(df)


def _compute_final_judgment(df: pd.DataFrame) -> None:
    """최종 판단 계산 (단순화된 임계값)"""
    n = len(df)
    j = np.full(n, 'NEUTRAL', dtype=object)
    
    bt = df['Buy_Total'].values
    st = df['Sell_Total'].values
    ba = df['Buy_Active_Layers'].values
    sa = df['Sell_Active_Layers'].values
    
    # 변동성 기반 동적 스케일링
    atr_pct = (df['ATR'] / df['Close'] * 100).values
    
    # 민감도 상수 (루프 밖에서 한 번만 조회)
    b_sens = Config.BUY_SENSITIVITY
    s_sens = Config.SELL_SENSITIVITY
    
    for i in range(n):
        b, s = bt[i], st[i]
        b_layers, s_layers = ba[i], sa[i]
        diff = b - s
        vol = atr_pct[i]
        
        # 저변동성 종목 (ETF, 우량주) 스케일 조정
        scale = 0.85 if vol < 2.0 else 1.0
        
        # 임계값 계산
        strong_t = Config.STRONG_THRESHOLD * scale
        normal_t = Config.NORMAL_THRESHOLD * scale
        watch_t = Config.WATCH_THRESHOLD * scale
        
        # 비율 계산
        buy_ratio = b / (s + 0.1)
        sell_ratio = s / (b + 0.1)
        
        # ══════════════ 판단 로직 (연속된 if-elif 체인) ══════════════
        
        # STRONG_BUY
        if (b >= strong_t * b_sens and 
            b_layers >= 4 and 
            buy_ratio >= Config.STRONG_RATIO and 
            diff >= 8 * scale):
            j[i] = 'STRONG_BUY'
        
        # BUY
        elif (b >= normal_t * b_sens and 
              b_layers >= 3 and 
              buy_ratio >= Config.NORMAL_RATIO and 
              diff >= 4 * scale):
            j[i] = 'BUY'
        
        # WATCH_BUY
        elif (b >= watch_t * b_sens and 
              b_layers >= 2 and 
              diff >= 2 * scale):
            j[i] = 'WATCH_BUY'
        
        # STRONG_SELL
        elif (s >= strong_t * s_sens and 
              s_layers >= 4 and 
              sell_ratio >= Config.STRONG_RATIO * 0.9 and 
              (s - b) >= 7 * scale):
            j[i] = 'STRONG_SELL'
        
        # SELL
        elif (s >= normal_t * s_sens and 
              s_layers >= 3 and 
              sell_ratio >= Config.NORMAL_RATIO * 0.9 and 
              (s - b) >= 3 * scale):
            j[i] = 'SELL'
        
        # WATCH_SELL
        elif (s >= watch_t * s_sens and 
              s_layers >= 2 and 
              (s - b) >= 1 * scale):
            j[i] = 'WATCH_SELL'
        
        # MIXED (BUY와 SELL 점수가 둘 다 높고 비슷할 때)
        elif (b >= 8 * scale and 
              s >= 8 * scale and 
              abs(diff) < 3 * scale):
            j[i] = 'MIXED'
        
        # else: NEUTRAL (기본값이므로 명시 불필요)
    
    df['Trade_Judgment'] = j



# ──────────────────────────────────────────
# 콤보 탐지
# ──────────────────────────────────────────
def detect_combos(df: pd.DataFrame, vol_ratio: pd.Series) -> None:
    """매매 콤보 탐지"""
    C, idx = df['Close'], df.index
    F = lambda col: df.get(col, pd.Series(False, index=idx))
    
    # 기본 조건
    trend_up = (C > df['MA200']) & (C > df['MA50']) & (df['MA50'] > df['MA200'])
    trend_dn = (C < df['MA200']) & (C < df['MA50']) & (df['MA50'] < df['MA200'])
    
    candle_bull = F('Bullish_Engulfing') | F('Hammer') | F('Morning_Star') | F('Doji_Bullish')
    candle_bear = F('Bearish_Engulfing') | F('Shooting_Star') | F('Evening_Star') | F('Doji_Bearish')
    
    timing_bull = (df['StochK'] < 20) | F('StochRSI_Cross_Buy') | F('MACD_Cross_Buy') | (df['WT1'] < -30)
    timing_bear = (df['StochK'] > 80) | F('StochRSI_Cross_Sell') | F('MACD_Cross_Sell') | (df['WT1'] > 30)
    
    vol_confirm = vol_ratio >= 1.5
    squeeze_state = F('NR7') | F('Inside_Day') | F('Calm_After_Storm') | (df['BB_Width'] <= df['BB_Width'].rolling(120, min_periods=20).quantile(0.1))
    
    mf_bull = (df['RSI_MFI'] > df['RSI_MFI'].shift(1)) | (df['RSI_MFI'] > 0)
    mf_bear = (df['RSI_MFI'] < df['RSI_MFI'].shift(1)) | (df['RSI_MFI'] < 0)
    
    # ═══ BUY 콤보 ═══
    ma_support = ((C - df['MA50']).abs() <= df['ATR'] * 1.5) | ((C - df['MA20']).abs() <= df['ATR'] * 1.0)
    
    df['Combo_TrendPullback_Buy'] = (
        trend_up & (C < df['MA20']) & ma_support &
        (candle_bull | timing_bull) & mf_bull & (df['BJ_Trend'] >= 4)
    )
    
    df['Combo_VolSqueeze_Buy'] = (
        squeeze_state.shift(1).fillna(False) & (C > df['MA50']) &
        (F('BB_Squeeze_End_Bull') | (F('Wide_Range_Bar') & (C > df['Open']))) &
        vol_confirm & mf_bull
    )
    
    oversold = (((df['StochK'] < 20) & (df['StochD'] < 20)).astype(int) + 
                (df['RSI'] < 30).astype(int) + (df['WT1'] < -53).astype(int)) >= 2
    df['Combo_Reversal_Buy'] = (
        oversold & ((C > df['MA200']) | (df['MA50'] > df['MA200'])) &
        (candle_bull | F('Gold_Dot') | F('Green_Dot_T1') | F('Lizard_Bull') | F('Gilligans_Buy'))
    )
    
    df['Combo_Momentum_Buy'] = (
        (F('New_52W_High') | F('Expansion_BO')) &
        (vol_confirm | F('Pocket_Pivot') | F('Momentum_Ignition_Buy')) &
        (df['ADX'] > 25) & (df['Plus_DI'] > df['Minus_DI']) & mf_bull
    )
    
    df['Combo_MAConfluence_Buy'] = (
        (df['MA50'] > df['MA200']) & (C > df['MA200']) &
        (F('Cross_Above_20MA') | F('Cross_Above_50MA')) &
        (F('MACD_Cross_Buy') | F('StochRSI_Cross_Buy') | F('NonADX_123_Bull')) & mf_bull
    )
    
    df['Combo_MF_Reversal_Buy'] = (
        F('MF_Cross_Bull') & (df['WT1'] < 20) & (C > df['MA50']) &
        (candle_bull | timing_bull | vol_confirm)
    )
    
    # ═══ SELL 콤보 ═══
    df['Combo_TrendRejection_Sell'] = (
        trend_dn & (C > df['MA20']) &
        (candle_bear | timing_bear) & mf_bear & (df['SJ_Trend'] >= 4)
    )
    
    overbought = (((df['StochK'] > 80) & (df['StochD'] > 80)).astype(int) + 
                  (df['RSI'] > 70).astype(int) + (df['WT1'] > 53).astype(int)) >= 2
    df['Combo_Exhaustion_Sell'] = (
        overbought & (candle_bear | F('Gilligans_Sell') | F('Blood_Diamond') | F('Red_Dot_T1') | F('Parabolic_Top_Sell'))
    )
    
    ma_break = (F('Fell_Below_20MA').astype(int) + F('Fell_Below_50MA').astype(int) + 
                F('Fell_Below_200MA').astype(int) + F('Death_Cross').astype(int)) >= 1
    df['Combo_MABreakdown_Sell'] = (
        ma_break & (vol_confirm | F('MACD_Zero_Cross_Sell') | (F('Wide_Range_Bar') & (C < df['Open']))) &
        mf_bear & (df['SJ_Trend'] >= 3)
    )
    
    df['Combo_VolSqueeze_Sell'] = (
        squeeze_state.shift(1).fillna(False) & (C < df['MA50']) &
        (F('BB_Squeeze_End_Bear') | (F('Wide_Range_Bar') & (C < df['Open']))) &
        vol_confirm & mf_bear
    )
    
    gap_up_fail = F('Gap_Up').shift(1).fillna(False) & (C < df['Open']) & (candle_bear | F('Gilligans_Sell'))
    df['Combo_GapFailure_Sell'] = gap_up_fail | (F('Gap_Down') & vol_confirm & (F('Fell_Below_50MA') | F('Fell_Below_200MA')))
    
    df['Combo_MF_Reversal_Sell'] = (
        F('MF_Cross_Bear') & (df['WT1'] > -20) & (C < df['MA50']) &
        (candle_bear | timing_bear | vol_confirm)
    )


# ──────────────────────────────────────────
# Confluence / Proximity
# ──────────────────────────────────────────
def compute_confluence(df: pd.DataFrame, decay_window: int = 5, decay_factor: float = 0.75) -> None:
    """Confluence Score 계산"""
    buy_weights = {k: v.weight for k, v in SIGNAL_REGISTRY.items() if v.is_buy}
    sell_weights = {k: v.weight for k, v in SIGNAL_REGISTRY.items() if not v.is_buy}
    
    decay_kernel = np.array([decay_factor ** i for i in range(decay_window + 1)])
    ones = np.ones(decay_window + 1)
    
    score = np.zeros(len(df))
    buy_count = np.zeros(len(df))
    sell_count = np.zeros(len(df))
    
    for col, weight in buy_weights.items():
        if col in df.columns:
            raw = df[col].fillna(False).astype(float).values
            score += np.convolve(raw * weight, decay_kernel, mode='full')[:len(raw)]
            buy_count += np.convolve(raw, ones, mode='full')[:len(raw)]
    
    for col, weight in sell_weights.items():
        if col in df.columns:
            raw = df[col].fillna(False).astype(float).values
            score -= np.convolve(raw * weight, decay_kernel, mode='full')[:len(raw)]
            sell_count += np.convolve(raw, ones, mode='full')[:len(raw)]
    
    # WT 보정
    wt1 = df['WT1'].values
    score += np.where(wt1 < Config.WT_OS1, 1.0, 0) + np.where(wt1 < Config.WT_OS2, 0.5, 0)
    score -= np.where(wt1 > Config.WT_OB1, 1.0, 0) - np.where(wt1 > Config.WT_OB2, 0.5, 0)
    
    # ADX 가중
    adx = df['ADX'].values
    plus_di, minus_di = df['Plus_DI'].values, df['Minus_DI'].values
    bull_trend = plus_di > minus_di
    bear_trend = minus_di > plus_di
    adx_factor = np.clip((adx - 20) / 100, 0.0, 0.3)
    
    score += np.where(bull_trend & (score > 0), score * adx_factor, 0)
    score -= np.where(bear_trend & (score < 0), abs(score) * adx_factor, 0)
    
    df['Confluence_Score'] = score
    df['Ultra_Buy'] = (score >= 6.5) | ((score >= 5) & (buy_count >= 3))
    df['Ultra_Sell'] = (score <= -6.5) | ((score <= -5) & (sell_count >= 3))
    df['Strong_Buy'] = (score >= 3.5) & (~df['Ultra_Buy'])
    df['Strong_Sell'] = (score <= -3.5) & (~df['Ultra_Sell'])


def compute_proximity(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
    """시그널 근접도 계산"""
    wt1, wt2 = df['WT1'], df['WT2']
    rsi, mfi = df['RSI'], df['MFI']
    rmfi = df['RSI_MFI']
    stk = df['StochK']
    macd_h = df['MACD_Hist']
    bb_w = df['BB_Width']
    
    gap = (wt1 - wt2).abs()
    near_cross = gap < 3
    crossing_up = (wt1 - wt2) > (wt1.shift(1) - wt2.shift(1))
    crossing_dn = (wt1 - wt2) < (wt1.shift(1) - wt2.shift(1))
    
    # Buy Proximity
    bp = pd.Series(0.0, index=df.index)
    bp += np.where((wt1 < -40) & near_cross, 25, 0)
    bp += np.where((wt1 < -40) & crossing_up & (gap < 8), 15, 0)
    bp += np.where(wt1 < Config.WT_OS2, 20, np.where(wt1 < -40, 10, 0))
    bp += np.where(rsi < 35, 15, np.where(rsi < 45, 5, 0))
    bp += np.where(mfi < 35, 15, np.where(mfi < 45, 5, 0))
    bp += np.where(rmfi < -5, 10, np.where(rmfi < 0, 5, 0))
    bp += np.where(rmfi > rmfi.shift(1), 5, 0)
    bp += np.where(stk < 20, 10, np.where(stk < 35, 5, 0))
    
    # Sell Proximity
    sp = pd.Series(0.0, index=df.index)
    sp += np.where((wt1 > 40) & near_cross, 25, 0)
    sp += np.where((wt1 > 40) & crossing_dn & (gap < 8), 15, 0)
    sp += np.where(wt1 > Config.WT_OB2, 20, np.where(wt1 > 40, 10, 0))
    sp += np.where(rsi > 65, 15, np.where(rsi > 55, 5, 0))
    sp += np.where(mfi > 65, 15, np.where(mfi > 55, 5, 0))
    sp += np.where(rmfi > 5, 10, np.where(rmfi > 0, 5, 0))
    sp += np.where(rmfi < rmfi.shift(1), 5, 0)
    sp += np.where(stk > 80, 10, np.where(stk > 65, 5, 0))
    
    # BB 수축
    bb_narrow = bb_w < bb_w.rolling(50).quantile(0.2)
    bp += np.where(bb_narrow, 5, 0)
    sp += np.where(bb_narrow, 5, 0)
    
    # 추세 필터
    sb = df.get('Strong_Bull', pd.Series(False, index=df.index))
    sbe = df.get('Strong_Bear', pd.Series(False, index=df.index))
    net = bp - sp
    
    bp_adj = np.where(net >= 0, bp, bp * np.where(sbe, 0.4, 0.55))
    sp_adj = np.where(net <= 0, sp, sp * np.where(sb, 0.4, 0.55))
    
    return pd.Series(bp_adj, index=df.index).clip(upper=100), pd.Series(sp_adj, index=df.index).clip(upper=100)


# ──────────────────────────────────────────
# 판단 상세 추출
# ──────────────────────────────────────────
def get_judgment_detail(row: pd.Series) -> Dict:
    """행에서 판단 상세 추출"""
    layer_names = ['Trend', 'Momentum', 'Candle', 'BB', 'Volume', 'MF', 'Pattern']
    
    buy_layers = {n: float(row.get(f'BJ_{n}', 0)) for n in layer_names}
    sell_layers = {n: float(row.get(f'SJ_{n}', 0)) for n in layer_names}
    
    active_combos = []
    for col, (name, direction, _) in COMBO_CONFIG.items():
        if row.get(col, False):
            active_combos.append({'name': name, 'dir': direction})
    
    return {
        'judgment': str(row.get('Trade_Judgment', 'NEUTRAL')),
        'buy_total': float(row.get('Buy_Total', 0)),
        'sell_total': float(row.get('Sell_Total', 0)),
        'buy_layers': buy_layers,
        'sell_layers': sell_layers,
        'buy_active': int(row.get('Buy_Active_Layers', 0)),
        'sell_active': int(row.get('Sell_Active_Layers', 0)),
        'active_combos': active_combos,
        'net': float(row.get('Buy_Total', 0)) - float(row.get('Sell_Total', 0)),
    }


# ══════════════════════════════════════════════════════════════
#  CipherX V12.0 — PART 4/4: 차트 + UI + 메인 로직
# ══════════════════════════════════════════════════════════════

# ──────────────────────────────────────────
# CSS (간소화)
# ──────────────────────────────────────────
st.markdown("""<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
html,body,[class*="css"]{font-family:'Pretendard','Noto Sans KR',sans-serif!important}
.stApp{background-color:#0B0E14}
p,li{color:#E8ECF1!important}
h1,h2{color:#FFFFFF!important;font-weight:700!important}
h3,h4{color:#CBD5E1!important;font-weight:600!important}
div[data-testid="stCodeBlock"],pre,code{background-color:#151921!important;border-radius:10px!important}
.block-container{padding-top:1rem!important;max-width:960px}
div.stButton>button[kind="primary"]{
    background:linear-gradient(135deg,#6366F1 0%,#8B5CF6 50%,#A78BFA 100%)!important;
    color:white!important;border:none!important;border-radius:12px!important;
    padding:.65rem 1.5rem!important;font-weight:700!important;width:100%}
div.stButton>button[kind="secondary"]{
    background-color:#12161F!important;color:#C4CDD8!important;
    border:1px solid #2A3040!important;border-radius:12px!important;width:100%}
.indicator-mini{display:inline-block;padding:5px 11px;margin:3px;border-radius:8px;
    font-size:.78rem;font-weight:600;border:1px solid rgba(255,255,255,0.04)}
.ind-bullish{background:rgba(16,185,129,.12);color:#6EE7B7}
.ind-bearish{background:rgba(239,68,68,.12);color:#FCA5A5}
.ind-neutral{background:rgba(245,158,11,.10);color:#FCD34D}
.signal-card{border-radius:14px;padding:14px 18px;margin:8px 0;border:1px solid rgba(255,255,255,0.06)}
.signal-card-buy{background:linear-gradient(135deg,rgba(0,230,118,.06) 0%,rgba(16,185,129,.03) 100%);border-left:4px solid #10B981}
.signal-card-sell{background:linear-gradient(135deg,rgba(239,68,68,.06) 0%,rgba(220,38,38,.03) 100%);border-left:4px solid #EF4444}
.signal-card-neutral{background:linear-gradient(135deg,rgba(245,158,11,.06) 0%,rgba(217,119,6,.03) 100%);border-left:4px solid #F59E0B}
.price-header{background:linear-gradient(160deg,#0F1320 0%,#141926 50%,#111827 100%);
    border:1px solid #1C2233;border-radius:16px;padding:20px 24px;margin-bottom:18px}
.judgment-card{border-radius:16px;padding:24px 28px;margin-bottom:20px;text-align:center;position:relative;overflow:hidden}
.judgment-card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px}
.judgment-card-buy{background:linear-gradient(160deg,#052E16 0%,#0D1B2A 100%);border:1px solid rgba(16,185,129,.25)}
.judgment-card-buy::before{background:linear-gradient(90deg,#10B981,#34D399)}
.judgment-card-sell{background:linear-gradient(160deg,#2A0E0E 0%,#1B0D1B 100%);border:1px solid rgba(239,68,68,.25)}
.judgment-card-sell::before{background:linear-gradient(90deg,#EF4444,#F87171)}
.judgment-card-neutral{background:linear-gradient(160deg,#1A1608 0%,#1B1A0D 100%);border:1px solid rgba(245,158,11,.2)}
.judgment-card-neutral::before{background:linear-gradient(90deg,#F59E0B,#FCD34D)}
.combo-card{border-radius:12px;padding:12px 16px;margin:6px 0;display:flex;align-items:center;
    justify-content:space-between;border:1px solid rgba(255,255,255,0.06)}
.combo-buy{background:linear-gradient(135deg,rgba(16,185,129,.08),rgba(6,78,59,.05));border-left:3px solid #10B981}
.combo-sell{background:linear-gradient(135deg,rgba(239,68,68,.08),rgba(127,29,29,.05));border-left:3px solid #EF4444}
.layer-bar-bg{background:#151921;border-radius:6px;height:10px;overflow:hidden}
.layer-bar-fill{height:10px;border-radius:6px;transition:width .5s}
.layer-bar-fill-buy{background:linear-gradient(90deg,#059669,#34D399)}
.layer-bar-fill-sell{background:linear-gradient(90deg,#DC2626,#F87171)}
</style>""", unsafe_allow_html=True)


# ──────────────────────────────────────────
# 데이터 캐싱
# ──────────────────────────────────────────
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
            f"Market Cap: {_get('marketCap','large')}", f"Float: {_get('floatShares','large')}",
            f"Short % of Float: {_get('shortPercentOfFloat','percent')}", f"P/E Ratio: {_get('trailingPE','float')}",
            f"52W High: {_get('fiftyTwoWeekHigh','currency')}", f"52W Low: {_get('fiftyTwoWeekLow','currency')}",
        ])
    except:
        return "펀더멘탈 데이터를 불러올 수 없습니다."


@st.cache_data(ttl=300, show_spinner=False)
def fetch_history(ticker: str, _ts=None) -> pd.DataFrame:
    return yf.Ticker(ticker).history(period="2y")


@st.cache_data(ttl=600, show_spinner=False)
def validate_ticker(ticker: str) -> bool:
    try:
        hist = yf.Ticker(ticker).history(period="5d")
        return not hist.empty
    except:
        return False


@st.cache_data(ttl=300, show_spinner=False)
def compute_and_cache(ticker: str, _ts=None) -> Optional[pd.DataFrame]:
    df = fetch_history(ticker, _ts)
    if df.empty:
        return None
    df = compute_all_indicators(df)
    return detect_all_signals(df)


# ──────────────────────────────────────────
# 차트 빌더
# ──────────────────────────────────────────
def build_chart(dc: pd.DataFrame, ticker: str) -> go.Figure:
    """6행 차트 빌드"""
    ma_colors = {5:"#ff9900", 10:"#ffb74d", 20:'#f1c40f', 50:'#e74c3c', 100:'#9b59b6', 125:'#3498db', 200:'#2ecc71'}
    
    fig = make_subplots(
        rows=6, cols=1, shared_xaxes=True, vertical_spacing=0.035,
        row_heights=[.36, .07, .15, .12, .15, .15],
        subplot_titles=("", "Volume", "WaveTrend", "Money Flow", "MACD", "BUY/SELL Score")
    )
    
    # Row 1: 캔들스틱
    fig.add_trace(go.Candlestick(
        x=dc.index, open=dc['Open'], high=dc['High'], low=dc['Low'], close=dc['Close'],
        name="Price", increasing_line_color='#00E676', decreasing_line_color='#FF1744',
        increasing_fillcolor='rgba(0,230,118,0.8)', decreasing_fillcolor='rgba(255,23,68,0.8)'
    ), row=1, col=1)
    
    # 이동평균
    for ma, color in ma_colors.items():
        if f'MA{ma}' in dc.columns:
            fig.add_trace(go.Scatter(x=dc.index, y=dc[f'MA{ma}'], line=dict(color=color, width=1.2), name=f'{ma}MA'), row=1, col=1)
    
    # 볼린저 밴드
    fig.add_trace(go.Scatter(x=dc.index, y=dc['BB_Up'], line=dict(color='gray', width=1, dash='dot'), name='BB↑'), row=1, col=1)
    fig.add_trace(go.Scatter(x=dc.index, y=dc['BB_Low'], line=dict(color='gray', width=1, dash='dot'), name='BB↓', fill='tonexty', fillcolor='rgba(128,128,128,0.07)'), row=1, col=1)
    
    # SuperTrend
    for mask, color, name in [(dc['ST_Direction']==1, '#00E676', 'ST▲'), (dc['ST_Direction']==-1, '#FF1744', 'ST▼')]:
        fig.add_trace(go.Scatter(x=dc.index, y=dc['SuperTrend'].where(mask), line=dict(color=color, width=2), name=name, connectgaps=False), row=1, col=1)
    
    # 판단 마커
    if 'Trade_Judgment' in dc.columns:
        enabled = st.session_state.get('enabled_judgments', set(JUDGMENT_MARKERS.keys()))
        for j_grade, j_cfg in JUDGMENT_MARKERS.items():
            if j_grade not in enabled:
                continue
            mask = dc['Trade_Judgment'] == j_grade
            if not mask.any():
                continue
            
            sig_rows = dc[mask]
            base_col = 'Low' if j_cfg['base'] == 'Low' else 'High'
            y_vals = sig_rows[base_col] + sig_rows['ATR'] * j_cfg['atr_mult']
            
            hover_texts = [_build_judgment_hover(dc.loc[idx], ALL_SIGNALS) for idx in sig_rows.index]
            
            fig.add_trace(go.Scatter(
                x=sig_rows.index, y=y_vals, mode='markers',
                marker=dict(symbol=j_cfg['symbol'], size=j_cfg['size'], color=j_cfg['color'], line=dict(width=1.5, color='#FFFFFF')),
                name=JUDGMENT_CONFIG[j_grade][0], text=hover_texts, hovertemplate="%{text}<extra></extra>"
            ), row=1, col=1)
    
    # Row 2: Volume
    bearish = dc['Close'] < dc['Open']
    fig.add_trace(go.Bar(x=dc.index, y=dc['Volume'], marker_color=np.where(bearish, 'rgba(255,23,68,0.6)', 'rgba(0,230,118,0.6)').tolist(), name="Volume"), row=2, col=1)
    
    # Row 3: WaveTrend
    fig.add_trace(go.Scatter(x=dc.index, y=dc['WT1'], line=dict(color='#00E676', width=2), name="WT1"), row=3, col=1)
    fig.add_trace(go.Scatter(x=dc.index, y=dc['WT2'], line=dict(color='#FF1744', width=1.5, dash='dot'), name="WT2"), row=3, col=1)
    wt_diff = dc['WT1'] - dc['WT2']
    fig.add_trace(go.Bar(x=dc.index, y=wt_diff, marker_color=np.where(wt_diff >= 0, '#00E676', '#FF1744').tolist(), name="WT Hist", opacity=0.3), row=3, col=1)
    
    for lv, color, dash in [(Config.WT_OB1, '#ff3333', 'solid'), (Config.WT_OS1, '#00bfff', 'solid'), (0, 'gray', 'dot')]:
        fig.add_hline(y=lv, line_dash=dash, line_color=color, line_width=1, row=3, col=1)
    
    # Row 4: Money Flow
    rmfi = dc['RSI_MFI']
    fig.add_trace(go.Bar(x=dc.index, y=rmfi, marker_color=np.where(rmfi >= 0, '#3ee145', '#ff3d2e').tolist(), name="Money Flow", opacity=0.7), row=4, col=1)
    fig.add_hline(y=0, line_color="gray", line_width=1, row=4, col=1)
    
    # Row 5: MACD
    fig.add_trace(go.Scatter(x=dc.index, y=dc['MACD_Line'], line=dict(color='#29B6F6', width=1.5), name="MACD"), row=5, col=1)
    fig.add_trace(go.Scatter(x=dc.index, y=dc['MACD_Signal'], line=dict(color='#FFA726', width=1.5), name="Signal"), row=5, col=1)
    mh = dc['MACD_Hist']
    fig.add_trace(go.Bar(x=dc.index, y=mh, marker_color=np.where(mh >= 0, '#26A69A', '#EF5350').tolist(), name="Hist", opacity=0.7), row=5, col=1)
    
    # Row 6: Judgment Score
    if 'Buy_Total' in dc.columns and 'Sell_Total' in dc.columns:
        net = dc['Buy_Total'] - dc['Sell_Total']
        colors = np.where(net >= 10, '#00E676', np.where(net >= 5, '#69F0AE', np.where(net <= -10, '#FF1744', np.where(net <= -5, '#FF5252', '#FFC107'))))
        fig.add_trace(go.Bar(x=dc.index, y=net, marker_color=colors.tolist(), name="NET Score", opacity=0.8), row=6, col=1)
        for lv, color in [(10, '#00E676'), (-10, '#FF1744'), (0, 'gray')]:
            fig.add_hline(y=lv, line_dash='dot' if lv != 0 else 'solid', line_color=color, line_width=0.8, row=6, col=1)
    
    # 레이아웃
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=2, r=2, t=40, b=2), height=1200, showlegend=True, hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=9.5))
    )
    fig.update_xaxes(rangeslider_visible=False, rangebreaks=[dict(bounds=["sat","mon"])])
    
    return fig


def _build_judgment_hover(row: pd.Series, signals_dict: Dict) -> str:
    """판단 마커 호버 텍스트"""
    judgment = str(row.get('Trade_Judgment', 'NEUTRAL'))
    bt, st = float(row.get('Buy_Total', 0)), float(row.get('Sell_Total', 0))
    
    lines = [f"<b>{JUDGMENT_CONFIG.get(judgment, ('NEUTRAL',))[0]}</b>",
             f"BUY {bt:.1f} vs SELL {st:.1f} (NET: {bt-st:+.1f})"]
    
    # 활성 콤보
    combos = [name for col, (name, _, _) in COMBO_CONFIG.items() if row.get(col, False)]
    if combos:
        lines.append(f"<b>콤보:</b> {', '.join(combos[:3])}")
    
    # 활성 시그널
    buy_sigs = [cfg.icon for name, cfg in signals_dict.items() if row.get(name, False) and cfg.is_buy][:5]
    sell_sigs = [cfg.icon for name, cfg in signals_dict.items() if row.get(name, False) and not cfg.is_buy][:5]
    
    if buy_sigs:
        lines.append(f"<span style='color:#34D399'>▲ {''.join(buy_sigs)}</span>")
    if sell_sigs:
        lines.append(f"<span style='color:#F87171'>▼ {''.join(sell_sigs)}</span>")
    
    return "<br>".join(lines)


# ──────────────────────────────────────────
# 메타데이터 빌드
# ──────────────────────────────────────────
def build_metadata(dc: pd.DataFrame, ticker: str) -> Tuple[Dict, str, str]:
    """메타데이터 구축"""
    lat = dc.iloc[-1]
    prev = dc.iloc[-2] if len(dc) >= 2 else lat
    
    pc = lat['Close'] - prev['Close']
    pp = pc / prev['Close'] * 100
    
    # 추세 레짐
    regime = 'STRONG BULL 🟢' if lat.get('Strong_Bull', False) else ('STRONG BEAR 🔴' if lat.get('Strong_Bear', False) else 'NEUTRAL ⚪')
    
    # 실드 상태
    shield_parts = []
    if lat.get('Sell_Shield_Overridden', False):
        shield_parts.append('🔓SELL OFF')
    if lat.get('Buy_Shield_Overridden', False):
        shield_parts.append('🔓BUY OFF')
    shield_str = ' + '.join(shield_parts)
    
    # 최근 시그널
    recent = []
    for ir, row in dc.tail(15).iterrows():
        ds = ir.strftime('%m/%d')
        for name, cfg in ALL_SIGNALS.items():
            if row.get(name, False):
                recent.append((cfg.icon, cfg.label, ds, 'buy' if cfg.is_buy else 'sell'))
    
    # 판단 히스토리
    judgment_history = []
    for ir, row in dc.tail(5).iterrows():
        jd = get_judgment_detail(row)
        judgment_history.append({
            'date': ir.strftime('%m/%d'),
            'judgment': jd['judgment'],
            'buy_total': jd['buy_total'],
            'sell_total': jd['sell_total'],
            'combos': jd['active_combos'],
        })
    
    meta = {
        'ticker': ticker.upper(),
        'price': float(lat['Close']),
        'price_change': pc,
        'price_change_pct': pp,
        'volume': float(lat['Volume']),
        'avg_volume': float(dc['Volume'].rolling(20).mean().iloc[-1]),
        'wt1': float(lat['WT1']),
        'wt2': float(lat['WT2']),
        'rsi': float(lat['RSI']),
        'mfi': float(lat['MFI']),
        'stochk': float(lat['StochK']),
        'mf_area': float(lat['RSI_MFI']),
        'atr': float(lat['ATR']),
        'atr_pct': float(lat['ATR']) / float(lat['Close']) * 100,
        'adx': float(lat['ADX']),
        'plus_di': float(lat['Plus_DI']),
        'minus_di': float(lat['Minus_DI']),
        'confluence_score': float(lat.get('Confluence_Score', 0)),
        'buy_proximity': float(lat.get('Buy_Proximity', 0)),
        'sell_proximity': float(lat.get('Sell_Proximity', 0)),
        'squeeze_on': bool(lat.get('Squeeze_On', False)),
        'supertrend_dir': int(lat.get('ST_Direction', 0)),
        'last_date': dc.index[-1].strftime('%Y-%m-%d'),
        'recent_signals': recent,
        'trend_regime': regime,
        'shield_status': shield_str,
        'judgment_detail': get_judgment_detail(lat),
        'judgment_history': judgment_history,
    }
    
    return meta, regime, shield_str


# ──────────────────────────────────────────
# UI 렌더 함수들
# ──────────────────────────────────────────
def render_price_header(m: Dict) -> None:
    """가격 헤더 렌더"""
    chg = m['price_change']
    cc = 'price-change-up' if chg >= 0 else 'price-change-down'
    ci = '▲' if chg >= 0 else '▼'
    vr = m['volume'] / m['avg_volume'] if m['avg_volume'] else 0
    
    jd = m.get('judgment_detail', {})
    j_short = jd.get('judgment', 'NEUTRAL')
    j_cls = 'ind-bullish' if 'BUY' in j_short else ('ind-bearish' if 'SELL' in j_short else 'ind-neutral')
    
    specs = [
        (j_cls, f"📍 {j_short}"),
        (_cls(m['wt1'], -20, 20), f"WT {m['wt1']:.0f}"),
        (_cls(m['rsi'], 40, 60), f"RSI {m['rsi']:.0f}"),
        (_cls(m['mfi'], 40, 60), f"MFI {m['mfi']:.0f}"),
        ('ind-bullish' if m['mf_area'] < 0 else ('ind-bearish' if m['mf_area'] > 0 else 'ind-neutral'), f"MF {m['mf_area']:.1f}"),
        ('ind-bullish' if vr > 1.5 else 'ind-neutral', f"Vol {vr:.1f}x"),
        ('ind-bullish' if m['adx'] > 25 else 'ind-neutral', f"ADX {m['adx']:.0f}"),
        ('ind-bullish' if m['supertrend_dir'] == 1 else 'ind-bearish', f"ST {'▲' if m['supertrend_dir']==1 else '▼'}"),
    ]
    
    indicators_html = "".join([f"<span class='indicator-mini {c}'>{l}</span>" for c, l in specs])
    
    st.markdown(f"""<div class="price-header">
        <div style="display:flex;justify-content:space-between;align-items:flex-start">
            <div>
                <p style="color:#64748B;font-size:.8rem;margin:0">🚦 {m['ticker']} · {m['last_date']} · <b style="color:#A5B4FC">{m['trend_regime']}</b></p>
                <p style="font-size:2.2rem;font-weight:800;color:#F8FAFC;margin:0">${m['price']:.2f}
                    <span class="{cc}" style="font-size:1.1rem;margin-left:10px;font-weight:700;color:{'#34D399' if chg>=0 else '#F87171'}">
                        {ci} {abs(chg):.2f} ({abs(m['price_change_pct']):.2f}%)</span></p>
            </div>
            <div style="text-align:right">
                <p style="color:#64748B;font-size:.8rem;margin:0">ATR (14)</p>
                <p style="color:#FCD34D;font-size:1.2rem;font-weight:700;margin:0">${m['atr']:.2f} ({m['atr_pct']:.1f}%)</p>
            </div>
        </div>
        <div style="margin-top:12px;display:flex;gap:5px;flex-wrap:wrap">{indicators_html}</div>
    </div>""", unsafe_allow_html=True)


def render_judgment(m: Dict) -> None:
    """매매 판단 UI"""
    jd = m.get('judgment_detail')
    if not jd:
        st.info("매매 판단 데이터가 없습니다.")
        return
    
    judgment = jd['judgment']
    buy_t, sell_t = jd['buy_total'], jd['sell_total']
    net = buy_t - sell_t
    
    card_cls = 'judgment-card-buy' if 'BUY' in judgment else ('judgment-card-sell' if 'SELL' in judgment else 'judgment-card-neutral')
    j_label, j_color, _ = JUDGMENT_CONFIG.get(judgment, ('⚪ NEUTRAL', '#64748B', ''))
    net_color = '#34D399' if net > 0 else ('#F87171' if net < 0 else '#FCD34D')
    
    st.markdown(f"""<div class="judgment-card {card_cls}">
        <p style="font-size:2rem;font-weight:800;color:{j_color};margin:0">{j_label}</p>
        <div style="display:flex;justify-content:center;gap:32px;margin-top:14px">
            <div><p style="color:#64748B;font-size:.7rem;margin:0">BUY Score</p>
                <p style="color:#34D399;font-size:1.4rem;font-weight:800;margin:0">{buy_t:.1f}</p></div>
            <div style="border-left:1px solid rgba(255,255,255,0.08);padding-left:32px">
                <p style="color:#64748B;font-size:.7rem;margin:0">SELL Score</p>
                <p style="color:#F87171;font-size:1.4rem;font-weight:800;margin:0">{sell_t:.1f}</p></div>
            <div style="border-left:1px solid rgba(255,255,255,0.08);padding-left:32px">
                <p style="color:#64748B;font-size:.7rem;margin:0">NET</p>
                <p style="color:{net_color};font-size:1.4rem;font-weight:800;margin:0">{net:+.1f}</p></div>
        </div>
    </div>""", unsafe_allow_html=True)
    
    # 콤보
    combos = jd.get('active_combos', [])
    st.markdown("#### 🔥 활성 콤보")
    if combos:
        for cb in combos:
            cc = 'combo-buy' if cb['dir'] == 'buy' else 'combo-sell'
            dot_c = '#34D399' if cb['dir'] == 'buy' else '#F87171'
            st.markdown(f"""<div class="combo-card {cc}">
                <span style="color:{dot_c};font-weight:700">● {cb['name']}</span>
                <span style="color:{dot_c};font-size:.75rem;font-weight:600">{cb['dir'].upper()}</span>
            </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""<div class="combo-card" style="background:rgba(245,158,11,.04);border-left:3px solid #F59E0B;justify-content:center">
            <span style="color:#FCD34D;font-weight:600">⏸️ 활성 콤보 없음</span></div>""", unsafe_allow_html=True)
    
    # 7-Layer 바
    st.markdown("#### 📊 7-Layer 스코어")
    col_b, col_s = st.columns(2)
    with col_b:
        st.markdown("<p style='color:#34D399;font-weight:700;font-size:.85rem'>▲ BUY LAYERS</p>", unsafe_allow_html=True)
        _render_layer_bars(jd['buy_layers'], 'buy')
    with col_s:
        st.markdown("<p style='color:#F87171;font-weight:700;font-size:.85rem'>▼ SELL LAYERS</p>", unsafe_allow_html=True)
        _render_layer_bars(jd['sell_layers'], 'sell')


def _render_layer_bars(layers: Dict, side: str) -> None:
    """레이어 바 렌더"""
    icons = {'Trend':'📈','Momentum':'🔥','Candle':'🕯️','BB':'📊','Volume':'📦','MF':'💰','Pattern':'⭐'}
    fill_cls = 'layer-bar-fill-buy' if side == 'buy' else 'layer-bar-fill-sell'
    score_color = '#34D399' if side == 'buy' else '#F87171'
    
    max_scores = Config.LAYER_MAX
    total = sum(layers.values())
    
    for name, score in layers.items():
        icon = icons.get(name, '•')
        max_s = max_scores.get(name, 8)
        pct = min(score / max_s * 100, 100)
        opacity = '1' if score > 0 else '0.3'
        
        st.markdown(f"""<div style="margin:4px 0">
            <div style="display:flex;justify-content:space-between;margin-bottom:2px">
                <span style="color:#94A3B8;font-size:.8rem;opacity:{opacity}">{icon} {name}</span>
                <span style="color:{score_color};font-weight:700;font-size:.8rem;opacity:{opacity}">{score:.1f}</span>
            </div>
            <div class="layer-bar-bg"><div class="layer-bar-fill {fill_cls}" style="width:{pct}%;opacity:{opacity}"></div></div>
        </div>""", unsafe_allow_html=True)
    
    st.markdown(f"""<div style="margin-top:12px;padding:10px;border-radius:10px;background:rgba(255,255,255,0.02);text-align:center">
        <span style="color:{score_color};font-weight:800;font-size:1.15rem">{total:.1f}</span>
        <span style="color:#475569;font-size:.8rem"> 점</span>
    </div>""", unsafe_allow_html=True)


def render_signals(m: Dict) -> None:
    """시그널 이력 렌더"""
    sigs = m.get('recent_signals', [])
    if not sigs:
        st.markdown("""<div class="signal-card signal-card-neutral" style="text-align:center">
            <p style="margin:0;color:#FCD34D;font-weight:600">⏸️ 최근 15일 내 시그널 없음</p></div>""", unsafe_allow_html=True)
        return
    
    # 날짜별 그룹화
    from collections import defaultdict
    grouped = defaultdict(list)
    for icon, label, date, side in sigs:
        grouped[date].append((icon, label, side))
    
    for date in reversed(list(grouped.keys())[:7]):
        group = grouped[date]
        buy_cnt = sum(1 for _, _, s in group if s == 'buy')
        sell_cnt = sum(1 for _, _, s in group if s == 'sell')
        card_cls = 'signal-card-buy' if buy_cnt > sell_cnt else ('signal-card-sell' if sell_cnt > buy_cnt else 'signal-card-neutral')
        
        parts = [f"<span class='indicator-mini {'ind-bullish' if s=='buy' else 'ind-bearish'}'>{i} {l}</span>" for i, l, s in group]
        
        st.markdown(f"""<div class="signal-card {card_cls}">
            <div style="display:flex;justify-content:space-between;margin-bottom:8px">
                <span style="font-weight:700;color:#E8ECF1">📅 {date}</span>
                <span style="color:#64748B;font-size:.75rem">{len(group)}개</span></div>
            <div style="display:flex;gap:5px;flex-wrap:wrap">{" ".join(parts)}</div>
        </div>""", unsafe_allow_html=True)


def render_analysis(msg: Dict) -> None:
    """분석 결과 렌더"""
    m, fig = msg.get('meta'), msg.get('fig')
    
    if m:
        render_price_header(m)
    
    if m or fig:
        tabs = st.tabs(["🎯 매매 판단", "📊 차트", "🔔 시그널 이력", "🏢 기업 상세"])
        
        with tabs[0]:
            if m:
                render_judgment(m)
        
        with tabs[1]:
            if fig:
                st.plotly_chart(fig, use_container_width=True, theme=None, config={'displaylogo': False})
        
        with tabs[2]:
            if m:
                render_signals(m)
        
        with tabs[3]:
            if m:
                render_company_details(m['ticker'])


# ──────────────────────────────────────────
# 프롬프트 빌더
# ──────────────────────────────────────────
def build_prompt_text(dc: pd.DataFrame, meta: Dict) -> str:
    """AI 프롬프트 텍스트 생성"""
    lat = dc.iloc[-1]
    prices = ", ".join([f"'{d.strftime('%Y-%m-%d')}:{r['Close']:.2f}'" for d, r in dc.tail(60).iterrows()])
    
    # 시그널 목록
    sig_list = []
    for ir, row in dc.tail(30).iterrows():
        date_str = ir.strftime('%Y-%m-%d')
        for name, cfg in ALL_SIGNALS.items():
            if row.get(name, False):
                sig_list.append(f"{cfg.icon} {cfg.label} {date_str}")
    
    signals_text = "\n".join(sig_list) if sig_list else "최근 30일 내 시그널 없음"
    
    # 판단 정보
    jd = meta.get('judgment_detail', {})
    judgment_text = f"""
📌 [멀티 시그널 매매 판단]
  최종판단: {jd.get('judgment', 'NEUTRAL')}
  BUY점수: {jd.get('buy_total', 0):.1f} (활성 {jd.get('buy_active', 0)}/7 레이어)
  SELL점수: {jd.get('sell_total', 0):.1f} (활성 {jd.get('sell_active', 0)}/7 레이어)
  활성콤보: {', '.join(c['name'] for c in jd.get('active_combos', [])) or '없음'}
"""
    
    indicators = f"""WT1={lat['WT1']:.1f}, RSI={lat['RSI']:.1f}, MFI={lat['MFI']:.1f}, StK={lat['StochK']:.1f},
MF={lat['RSI_MFI']:.1f}, ADX={lat['ADX']:.1f}, +DI={lat['Plus_DI']:.1f}, -DI={lat['Minus_DI']:.1f},
Trend={meta['trend_regime']}, ATR={meta['atr']:.2f}({meta['atr_pct']:.1f}%)"""
    
    return f"{prices}\n\n📌 [지표 요약]\n{indicators}\n\n📌 [최근 시그널]\n{signals_text}\n{judgment_text}"


def build_ai_prompt(ticker: str, prompt_hist: str, fundamentals: str) -> str:
    """AI 프롬프트 전체 생성"""
    return f"""당신은 월스트리트 20년+ 경력 퀀트 애널리스트입니다.

[티커: {ticker}]

📌 [기술적 데이터 + 시그널 + 판단]
{prompt_hist}

📌 [펀더멘탈]
{fundamentals}

위 데이터를 바탕으로 심층 분석 리포트를 작성하세요:
1. 현재 상황 요약 (2-3문장)
2. 멀티 시그널 판단 해석
3. 지지선/저항선
4. 시나리오별 전략 (긍정/중립/부정)
5. ATR 기반 손절/목표가
6. 최종 결론
"""


# ──────────────────────────────────────────
# 분석 실행
# ──────────────────────────────────────────
def analyze(ticker: str, chart_days: int = 252, refresh: bool = False):
    """메인 분석 함수"""
    try:
        ts = int(time.time()) if refresh else None
        df = compute_and_cache(ticker, ts)
        
        if df is None or df.empty:
            return None, "주가 데이터 없음", None
        
        dv = df.dropna(subset=['WT1', 'WT2'])
        dc = dv.tail(chart_days).copy()
        
        if dc.empty:
            return None, "차트 데이터 부족", None
        
        meta, regime, shield = build_metadata(dc, ticker)
        fig = build_chart(dc, ticker)
        prompt = build_prompt_text(dc, meta)
        
        return fig, prompt, meta
    
    except Exception as e:
        import traceback
        print(f"[CipherX ERROR] {ticker}: {traceback.format_exc()}")
        return None, f"분석 실패: {e}", None


# ──────────────────────────────────────────
# 사이드바
# ──────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🚦 CipherX V12")
    st.markdown("<p style='color:#888;font-size:.8rem'>AI 퀀트 주가 분석</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    chart_period = st.radio("차트 기간", ['3개월','6개월','1년','2년'], index=0, horizontal=True)
    chart_days = {'3개월':63, '6개월':126, '1년':252, '2년':504}[chart_period]
    
    st.markdown("---")
    
    with st.expander("🎛️ 표시 설정"):
        show_strong = st.checkbox("STRONG 판단", value=True)
        show_normal = st.checkbox("BUY/SELL 판단", value=True)
        show_watch = st.checkbox("WATCH 판단", value=False)
        show_mixed = st.checkbox("MIXED 판단", value=False)
        
        enabled = set()
        if show_strong:
            enabled |= {'STRONG_BUY', 'STRONG_SELL'}
        if show_normal:
            enabled |= {'BUY', 'SELL'}
        if show_watch:
            enabled |= {'WATCH_BUY', 'WATCH_SELL'}
        if show_mixed:
            enabled.add('MIXED')
        
        st.session_state['enabled_judgments'] = enabled
    
    st.markdown("---")
    
    if st.button("🗑️ 대화 초기화", use_container_width=True):
        st.session_state.messages = [{"role": "assistant", "type": "text", "content": "안녕하세요! 🚦 **CipherX V12** 입니다.\n\n분석할 **티커명**을 입력하세요."}]
        st.session_state.last_ticker = None
        st.session_state.pending_ai_ticker = None
        st.session_state.pending_ai_prompt = None
        st.rerun()


# ──────────────────────────────────────────
# 세션 초기화
# ──────────────────────────────────────────
if 'messages' not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "type": "text", "content": "안녕하세요! 🚦 **CipherX V12** 입니다.\n\n분석할 **티커명**을 입력하세요."}]

for key in ['pending_ai_ticker', 'pending_ai_prompt', 'last_ticker']:
    if key not in st.session_state:
        st.session_state[key] = None

if 'enabled_judgments' not in st.session_state:
    st.session_state['enabled_judgments'] = {'STRONG_BUY', 'BUY', 'SELL', 'STRONG_SELL'}


# ──────────────────────────────────────────
# 메인 UI
# ──────────────────────────────────────────
st.markdown("<h2 style='text-align:center;color:#fff'>🚦 CipherX</h2>", unsafe_allow_html=True)

# 퀵 버튼
if not st.session_state.last_ticker:
    st.markdown("<p style='text-align:center;color:#888;font-size:0.9rem'>🔥 빠른 분석</p>", unsafe_allow_html=True)
    cols = st.columns(4)
    for i, ticker in enumerate(["NVDA", "TSLA", "AAPL", "QQQ"]):
        with cols[i]:
            if st.button(ticker, use_container_width=True):
                st.session_state['quick_ticker'] = ticker

# 메시지 표시
for i, msg in enumerate(st.session_state.messages):
    avatar = "✨" if msg["role"] == "assistant" else "🧑‍💻"
    with st.chat_message(msg["role"], avatar=avatar):
        if msg.get("type") == "analysis":
            st.markdown(msg.get("content", ""))
            render_analysis(msg)
            if msg.get("prompt"):
                with st.expander("📝 프롬프트 원문"):
                    st.code(msg["prompt"], language="markdown")
                    st_copy_to_clipboard(msg["prompt"], before_copy_label="📋 복사")
        elif msg.get("type") == "report":
            with st.expander(f"📊 {msg.get('ticker','')} AI 리포트", expanded=True):
                st.markdown(msg["content"])
        else:
            st.markdown(msg.get("content", ""))


# ──────────────────────────────────────────
# 티커 처리
# ──────────────────────────────────────────
def process_ticker(tv: str, refresh: bool = False):
    tv = tv.strip().upper()
    st.session_state.pending_ai_ticker = None
    st.session_state.pending_ai_prompt = None
    
    if not _valid_ticker(tv):
        st.toast(f"⚠️ **{tv}** — 올바른 티커 형식이 아닙니다.", icon="🚨")
        return
    
    if not validate_ticker(tv):
        st.toast(f"⚠️ **{tv}** — 데이터를 찾을 수 없습니다.", icon="🔍")
        return
    
    st.session_state.messages.append({"role": "user", "type": "text", "content": tv})
    st.session_state.last_ticker = tv
    
    with st.chat_message("assistant", avatar="✨"):
        with st.status(f"🌐 {tv} 분석 중...", expanded=True) as status:
            st.write("📡 데이터 조회 중...")
            fundamentals = fetch_fundamentals(tv)
            
            st.write("📊 기술 지표 계산 중...")
            st.write("🎯 7-Layer 판단 엔진 가동 중...")
            fig, prompt_hist, meta = analyze(tv, chart_days, refresh)
            
            if fig:
                prompt = build_ai_prompt(tv, prompt_hist, fundamentals)
                status.update(label=f"✅ {tv} 분석 완료!", state="complete", expanded=False)
            else:
                status.update(label=f"⚠️ {tv} 분석 실패", state="error", expanded=False)
        
        if fig:
            st.session_state.messages.append({
                "role": "assistant", "type": "analysis", "ticker": tv,
                "content": f"✅ **{tv}** 분석이 완료되었습니다.",
                "fig": fig, "meta": meta, "prompt": prompt
            })
            st.session_state.pending_ai_ticker = tv
            st.session_state.pending_ai_prompt = prompt
            st.rerun()
        else:
            st.session_state.messages.append({
                "role": "assistant", "type": "text",
                "content": f"⚠️ **{tv}** 분석 실패: {prompt_hist}"
            })
            st.rerun()


def run_ai():
    """AI 리포트 실행"""
    tp = st.session_state.pending_ai_ticker
    pp = st.session_state.pending_ai_prompt
    
    with st.chat_message("assistant", avatar="✨"):
        pb = st.progress(0, text="AI 분석 준비 중...")
        try:
            pb.progress(10, text="Gemini 초기화...")
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            pb.progress(20, text="리포트 생성 중...")
            collected = []
            
            def stream_gen():
                pb.progress(40, text="🚀 AI 분석 진행 중...")
                response = model.generate_content(pp, stream=True)
                for chunk in response:
                    if chunk.text:
                        collected.append(chunk.text)
                        yield chunk.text
                pb.progress(100, text="✅ 완료!")
            
            with st.expander(f"📊 {tp.upper()} AI 리포트", expanded=True):
                st.write_stream(stream_gen())
            
            time.sleep(0.3)
            pb.empty()
            
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


# 퀵 티커 처리
if st.session_state.get('quick_ticker'):
    qt = st.session_state.pop('quick_ticker')
    process_ticker(qt)

# 버튼
if st.session_state.last_ticker:
    lt = st.session_state.last_ticker
    c1, c2 = st.columns([3, 1])
    with c1:
        if st.session_state.pending_ai_ticker:
            if st.button(f"🚀 {st.session_state.pending_ai_ticker} AI 분석", type="primary", use_container_width=True):
                run_ai()
    with c2:
        if st.button(f"🔄 {lt}", type="secondary", use_container_width=True):
            process_ticker(lt, refresh=True)
elif st.session_state.pending_ai_ticker:
    if st.button(f"🚀 {st.session_state.pending_ai_ticker} AI 분석", type="primary", use_container_width=True):
        run_ai()

# 입력
if ticker_input := st.chat_input("티커 입력 (예: TSLA, AAPL)"):
    process_ticker(ticker_input)