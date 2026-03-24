# ══════════════════════════════════════════════════════════════
#  CipherX V14.2 — PART 1/4
#  설정, 레지스트리, 유틸리티, 기술지표
# ══════════════════════════════════════════════════════════════

import streamlit as st, google.generativeai as genai
import time, re, math, json
from datetime import datetime
from st_copy_to_clipboard import st_copy_to_clipboard
import yfinance as yf, plotly.graph_objects as go
import pandas as pd, numpy as np
from plotly.subplots import make_subplots
from scipy.signal import find_peaks
from concurrent.futures import ThreadPoolExecutor, as_completed
from company_details import render_company_details
from sectors import SECTOR_GROUPS
from indicators import compute_indicators as modular_compute_indicators
from engine import detect_all_signals as modular_detect_all_signals

st.set_page_config(page_title="CipherX V14.2", page_icon="📈", layout="wide", initial_sidebar_state="collapsed")

# ━━━ CSS ━━━
st.markdown("""<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
html,body,[class*="css"]{font-family:'Pretendard',sans-serif!important}
.stApp{background-color:#0B0E14}
p,li{color:#E8ECF1!important} h1,h2{color:#FFF!important;font-weight:800!important}
h3{color:#F0F4F8!important;font-weight:700!important}
h4{color:#CBD5E1!important;font-weight:600!important;font-size:1rem!important}
.block-container{padding-top:1rem!important;max-width:1400px}
div.stButton>button[kind="primary"]{background:linear-gradient(135deg,#6366F1,#8B5CF6)!important;color:#fff!important;border:none!important;border-radius:12px!important;font-weight:700!important;width:100%}
div.stButton>button[kind="secondary"]{background-color:#12161F!important;color:#C4CDD8!important;border:1px solid #2A3040!important;border-radius:12px!important;width:100%}
.price-header{background:linear-gradient(160deg,#0F1320,#141926);border:1px solid #1C2233;border-radius:16px;padding:20px 24px;margin-bottom:18px}
.price-big{font-size:2.2rem;font-weight:800;margin:0}
.price-change-up{color:#34D399!important} .price-change-down{color:#F87171!important}
.ind-mini{display:inline-block;padding:4px 10px;margin:2px;border-radius:8px;font-size:.76rem;font-weight:600}
.ind-b{background:rgba(16,185,129,.12);color:#6EE7B7}
.ind-s{background:rgba(239,68,68,.12);color:#FCA5A5}
.ind-n{background:rgba(245,158,11,.10);color:#FCD34D}
.layer-row{display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid rgba(255,255,255,.04)}
.layer-bar{background:#151921;border-radius:4px;height:8px;flex:1;margin:0 8px;overflow:hidden}
.layer-fill-b{height:8px;border-radius:4px;background:linear-gradient(90deg,#059669,#34D399)}
.layer-fill-s{height:8px;border-radius:4px;background:linear-gradient(90deg,#DC2626,#F87171)}
.score-card{border-radius:14px;padding:20px;text-align:center;position:relative;overflow:hidden}
.score-card-buy{background:linear-gradient(160deg,#052E16,#0D1B2A);border:1px solid rgba(16,185,129,.25)}
.score-card-sell{background:linear-gradient(160deg,#2A0E0E,#1B0D1B);border:1px solid rgba(239,68,68,.25)}
.score-card-neutral{background:linear-gradient(160deg,#1A1608,#1B1A0D);border:1px solid rgba(245,158,11,.2)}
.cs-card{border-radius:10px;padding:10px 14px;margin:5px 0;border-left:4px solid}
.reason-card{background:rgba(255,255,255,.04);border-radius:10px;padding:12px 16px;margin-top:12px;text-align:left}
div[data-baseweb="select"]>div{background-color:#12161F!important;border-color:#2A3040!important;color:#E8ECF1!important}
div[data-baseweb="popover"] ul{background-color:#FFFFFF!important;border-radius:10px!important}
div[data-baseweb="popover"] li{color:#1E293B!important}
div[data-testid="stRadio"] label p{color:#CBD5E1!important}
div[data-testid="stTextInput"] input{background-color:#12161F!important;border-color:#2A3040!important;color:#E8ECF1!important}
div[data-testid="stTabs"] button{color:#64748B!important;font-weight:700!important;border-bottom:3px solid transparent!important}
div[data-testid="stTabs"] button[aria-selected="true"]{color:#A5B4FC!important;border-bottom-color:#6366F1!important}
section[data-testid="stSidebar"]{background-color:#080A10;border-right:1px solid #151921}
header{background-color:transparent!important}
div[data-testid="stMetricValue"]{color:#F8FAFC!important}
::-webkit-scrollbar{width:6px} ::-webkit-scrollbar-track{background:#0B0E14} ::-webkit-scrollbar-thumb{background:#2A3040;border-radius:3px}
</style>""", unsafe_allow_html=True)

# ━━━ Constants ━━━
OB1,OB2,OS1,OS2=53,60,-53,-60
NUM_COMMITTEES=5;NUM_LAYERS=10

class JT:
    TREND_CAP=12;MOMENTUM_CAP=12;CANDLE_CAP=6;BB_CAP=8;VOLUME_CAP=8;MF_CAP=8
    PATTERN_CAP=12;COMBINED_CAP=15;LEADING_CAP=10;LAGGING_CAP=10;REVERSAL_CAP=12
    COMBO_T1=5.;COMBO_T2=3.;COMBO_T3=1.5;ACCEL_STRONG=3.;ACCEL_MOD=1.5;DECAY_DAYS=3;DECAY_RATE=.5
    TREND_NORM=18.;MOMENTUM_NORM=10.;MONEY_NORM=12.;STRUCTURE_NORM=10.;LEADING_NORM=25.
    STRONG_BUY_TH=40;BUY_TH=20;WATCH_BUY_TH=8
    STRONG_SELL_TH=-40;SELL_TH=-20;WATCH_SELL_TH=-8
    STRONG_MIN_AGREE=4;BUY_MIN_AGREE=3;WATCH_MIN_AGREE=2
    VETO_EXTREME_WT=65;VETO_EXTREME_RSI_LO=25;VETO_EXTREME_RSI_HI=75
    VETO_MONEY_CMF=0.12;VETO_MONEY_OBV_BARS=10

# ── Context (11종) ──
CTX_DEFAULT=0;CTX_EXTREME_OS=1;CTX_EXTREME_OB=2;CTX_STRONG_UP=3;CTX_STRONG_DN=4
CTX_ACCUMULATION=5;CTX_DISTRIBUTION=6;CTX_RANGING=7;CTX_BOTTOMING=8;CTX_TOPPING=9
CTX_VOL_DRY=10;CTX_POST_EXPLOSION=11
CTX_LABELS={0:'default',1:'extreme_oversold',2:'extreme_overbought',3:'strong_trend_up',
    4:'strong_trend_down',5:'accumulation',6:'distribution',7:'ranging',
    8:'bottoming',9:'topping',10:'vol_dry',11:'post_explosion'}
CTX_KOR={0:'기본',1:'극과매도',2:'극과매수',3:'강한상승추세',4:'강한하락추세',
    5:'매집구간',6:'분배구간',7:'횡보구간',8:'바닥다지기',9:'천장형성',
    10:'거래량고갈',11:'폭발직후'}
CONTEXT_WEIGHTS={
    'extreme_oversold':[.05,.30,.20,.15,.30],'extreme_overbought':[.05,.30,.20,.15,.30],
    'strong_trend_up':[.30,.25,.15,.10,.20],'strong_trend_down':[.30,.25,.15,.10,.20],
    'accumulation':[.08,.15,.35,.22,.20],'distribution':[.08,.15,.35,.22,.20],
    'ranging':[.10,.20,.25,.25,.20],'default':[.20,.25,.20,.15,.20],
    'bottoming':[.08,.25,.30,.17,.20],'topping':[.08,.25,.30,.17,.20],
    'vol_dry':[.10,.15,.15,.30,.30],'post_explosion':[.15,.30,.20,.15,.20],
}
COMMITTEE_NAMES=['Trend','Momentum','Money','Structure','Leading']
COMMITTEE_ICONS={'Trend':'📈','Momentum':'🔥','Money':'💰','Structure':'🏗️','Leading':'⏳'}

GEMINI_API_KEY=st.secrets["GEMINI_API_KEY"];genai.configure(api_key=GEMINI_API_KEY)
@st.cache_resource
def get_gemini_model():return genai.GenerativeModel('gemini-2.5-flash')

_B,_S,_N='buy','sell','neutral'
def _sig(w,d,icon,label,sym,sz,clr,base,atr_m,kor,desc):
    return {'w':w,'dir':d,'icon':icon,'label':label,'sym':sym,'sz':sz,'clr':clr,'base':base,'atr_m':atr_m,'kor':kor,'desc':desc}

SIGNAL_REGISTRY={
    'Gold_Dot':_sig(3,_B,'🏆','GOLD','circle',18,'#FFD700','Low',-3,'최강매수','RSI<30+MFI<30+WT<-60+Div'),
    'Green_Dot_T1':_sig(2.5,_B,'🟢','BUY T1','circle',16,'#00E676','Low',-2.5,'강한매수','WT과매도+RSI<30+MFI<30'),
    'Green_Dot_T2':_sig(2,_B,'🟩','BUY T2','circle',13,'#69F0AE','Low',-2.2,'매수','WT과매도+RSI/MFI<32'),
    'Blue_Diamond':_sig(2,_B,'🔹','BLUE','diamond',14,'#00bfff','Low',-1.8,'추세매수','WT2≤0+HTF강세'),
    'Green_Circle':_sig(.8,_B,'✅','BUYCir','circle-open',11,'#00E676','Low',-1.2,'과매도반등','WT과매도+RSI<45'),
    'Blood_Diamond':_sig(3,_S,'🩸','BLOOD','diamond',18,'#DC143C','High',3,'최강매도','RSI>70+MFI>70+WT>60+Div'),
    'Red_Dot_T1':_sig(2.5,_S,'🔴','SELL T1','circle',16,'#FF1744','High',2.5,'강한매도','WT과매수+RSI>70+MFI>70'),
    'Red_Dot_T2':_sig(2,_S,'🟥','SELL T2','circle',13,'#FF5252','High',2.2,'매도','WT과매수+RSI/MFI>68'),
    'Red_Diamond':_sig(2,_S,'🔸','RED','diamond',14,'#ff3333','High',1.8,'추세매도','WT2≥0+HTF약세'),
    'Red_Circle':_sig(.8,_S,'⛔','SELLCir','circle-open',11,'#FF1744','High',1.2,'과매수하락','WT과매수+RSI>55'),
    'Bull_Divergence':_sig(2,_B,'📈','BullDiv','triangle-up',12,'#AA00FF','Low',-2,'상승다이버','가격↓vsWT↑'),
    'Bear_Divergence':_sig(2,_S,'📉','BearDiv','triangle-down',12,'#AA00FF','High',2,'하락다이버','가격↑vsWT↓'),
    'RSI_Bull_Divergence':_sig(1.5,_B,'📊','RSIBDiv','triangle-up',11,'#CE93D8','Low',-1.8,'RSI상승다이버','가격↓vsRSI↑'),
    'RSI_Bear_Divergence':_sig(1.5,_S,'📉','RSIBrDiv','triangle-down',11,'#CE93D8','High',1.8,'RSI하락다이버','가격↑vsRSI↓'),
    'Hidden_Bull_Div':_sig(1.5,_B,'🔀','HidBull','triangle-up',10,'#E040FB','Low',-1.6,'히든강세','가격↑vsWT↓'),
    'Hidden_Bear_Div':_sig(1.5,_S,'🔁','HidBear','triangle-down',10,'#E040FB','High',1.6,'히든약세','가격↓vsWT↑'),
    'Pullback_123_Bull':_sig(2,_B,'🎯','123PB▲','triangle-up',12,'#00E676','Low',-1.8,'123풀백매수','ADX>30+3일저점↓'),
    'Pullback_123_Bear':_sig(2,_S,'🎯','123PB▼','triangle-down',12,'#FF1744','High',1.8,'123되돌림매도','ADX>30+3일고점↑'),
    'Setup_180_Bull':_sig(2,_B,'🔄','180▲','star-diamond',13,'#00E676','Low',-2,'180매수','전일하위25%→당일상위25%'),
    'Setup_180_Bear':_sig(2,_S,'🔄','180▼','star-diamond',13,'#FF1744','High',2,'180매도','전일상위25%→당일하위25%'),
    'Boomer_Buy':_sig(2,_B,'💣','Boom▲','star',12,'#00E676','Low',-1.8,'부머매수','ADX>30+2일인사이드'),
    'Boomer_Sell':_sig(2,_S,'💣','Boom▼','star',12,'#FF1744','High',1.8,'부머매도','ADX>30+2일인사이드'),
    'Expansion_BO':_sig(2.5,_B,'🚀','XBO','star-diamond',14,'#FFD700','Low',-2.5,'확장돌파','2개월신고가+9일최대범위'),
    'Expansion_BD':_sig(2.5,_S,'💨','XBD','star-diamond',14,'#FF0000','High',2.5,'확장붕괴','2개월신저가+9일최대범위'),
    'Expansion_Pivot_Buy':_sig(2,_B,'📍','XPvt▲','triangle-up',12,'#00E676','Low',-2,'확장피봇매수','50MA부근폭발상승'),
    'Expansion_Pivot_Sell':_sig(2,_S,'📍','XPvt▼','triangle-down',12,'#FF1744','High',2,'확장피봇매도','50MA부근폭발하락'),
    'Expansion_Double_Sticks':_sig(2,_S,'🎭','DblStk','hexagram',13,'#FF5722','High',2,'더블스틱','60일신고가후시가아래마감'),
    'Gilligans_Buy':_sig(2,_B,'🏝️','Gill▲','hexagon',12,'#00BCD4','Low',-2,'길리건매수','2개월신저가갭다운→반전'),
    'Gilligans_Sell':_sig(2,_S,'🏝️','Gill▼','hexagon',12,'#FF5722','High',2,'길리건매도','2개월신고가갭업→반전'),
    'Lizard_Bull':_sig(1.5,_B,'🦎','Liz▲','triangle-up',10,'#00E676','Low',-1.5,'리자드매수','시가종가상위25%+10일신저가'),
    'Lizard_Bear':_sig(1.5,_S,'🦎','Liz▼','triangle-down',10,'#FF1744','High',1.5,'리자드매도','시가종가하위25%+10일신고가'),
    'Slingshot_Bull':_sig(2,_B,'🎯','Sling▲','triangle-up',12,'#00E676','Low',-1.8,'슬링샷매수','신고가후흔들기→재돌파'),
    'Slingshot_Bear':_sig(2,_S,'🎯','Sling▼','triangle-down',12,'#FF1744','High',1.8,'슬링샷매도','신저가후흔들기→재하락'),
    'Jack_In_Box_Bull':_sig(2,_B,'🎁','Jack▲','star',12,'#00E676','Low',-1.8,'잭인더박스매수','XBO후인사이드→재돌파'),
    'Jack_In_Box_Bear':_sig(2,_S,'🎁','Jack▼','star',12,'#FF1744','High',1.8,'잭인더박스매도','XBD후인사이드→재하락'),
    'NonADX_123_Bull':_sig(1.8,_B,'📐','nADX▲','triangle-up',11,'#69F0AE','Low',-1.5,'비ADX풀백매수','주가>50MA+3일저점↓'),
    'NonADX_123_Bear':_sig(1.8,_S,'📐','nADX▼','triangle-down',11,'#FF5252','High',1.5,'비ADX풀백매도','주가<50MA+3일고점↑'),
    'Reversal_New_Highs':_sig(2.5,_B,'🔝','RevHi','star-diamond',14,'#00E676','Low',-2.5,'신고가반전','60일신고가+아웃사이드'),
    'Reversal_New_Lows':_sig(2.5,_S,'🔻','RevLo','star-diamond',14,'#FF1744','High',2.5,'신저가반전','60일신저가+아웃사이드'),
    'MA20_Support':_sig(1,_B,'📈','MA20S','triangle-up',9,'#69F0AE','Low',-1,'20MA지지','20MA부근반등'),
    'MA20_Resistance':_sig(1,_S,'📉','MA20R','triangle-down',9,'#FF5252','High',1,'20MA저항','20MA부근저항'),
    'MA50_Support':_sig(1.2,_B,'📈','MA50S','triangle-up',10,'#00E676','Low',-1.2,'50MA지지','50MA부근반등'),
    'MA50_Resistance':_sig(1.2,_S,'📉','MA50R','triangle-down',10,'#FF1744','High',1.2,'50MA저항','50MA부근저항'),
    'MA200_Support':_sig(1.5,_B,'📈','MA200S','triangle-up',11,'#00BFA5','Low',-1.5,'200MA지지','200MA부근반등'),
    'MA200_Resistance':_sig(1.5,_S,'📉','MA200R','triangle-down',11,'#D50000','High',1.5,'200MA저항','200MA부근저항'),
    'Cross_Above_20MA':_sig(.8,_B,'📈','X▲20','triangle-up',9,'#69F0AE','Low',-.8,'20MA상향','종가>20MA'),
    'Cross_Above_50MA':_sig(1.2,_B,'📈','X▲50','triangle-up',10,'#00E676','Low',-1,'50MA상향','종가>50MA'),
    'Cross_Above_200MA':_sig(1.5,_B,'📈','X▲200','triangle-up',11,'#00BFA5','Low',-1.2,'200MA상향','종가>200MA'),
    'Fell_Below_20MA':_sig(.8,_S,'📉','X▼20','triangle-down',9,'#FF5252','High',.8,'20MA하향','종가<20MA'),
    'Fell_Below_50MA':_sig(1.2,_S,'📉','X▼50','triangle-down',10,'#FF1744','High',1,'50MA하향','종가<50MA'),
    'Fell_Below_200MA':_sig(1.5,_S,'📉','X▼200','triangle-down',11,'#D50000','High',1.2,'200MA하향','종가<200MA'),
    'Golden_Cross':_sig(1.5,_B,'✨','GoldenX','cross',12,'#FFD700','Low',-.8,'골든크로스','50MA>200MA'),
    'Death_Cross':_sig(1.5,_S,'☠️','DeathX','cross',12,'#FF1744','High',.8,'데스크로스','50MA<200MA'),
    'MTF_All_Bullish':_sig(2,_B,'📊','MTF▲','star',13,'#00E676','Low',-1.5,'다중시간대강세','10/50/200MA위'),
    'MTF_All_Bearish':_sig(2,_S,'📊','MTF▼','star',13,'#FF1744','High',1.5,'다중시간대약세','10/50/200MA아래'),
    'BB_Squeeze':_sig(1,_N,'🔳','BBSq','square-open',9,'#FFC107','Low',-.5,'BB스퀴즈','BB폭6개월최저'),
    'BB_Squeeze_Started':_sig(1,_N,'⏳','SqSt','hourglass',9,'#90A4AE','Low',-.5,'스퀴즈시작','BB수축시작'),
    'BB_Squeeze_End_Bull':_sig(1.5,_B,'💥','SqE▲','star-diamond',12,'#00FFFF','Low',-1.5,'스퀴즈해소↑','BB확장+상승'),
    'BB_Squeeze_End_Bear':_sig(1.5,_S,'💥','SqE▼','star-diamond',12,'#FF6600','High',1.5,'스퀴즈해소↓','BB확장+하락'),
    'BB_Upper_Touch':_sig(.8,_N,'🔝','BB▲T','diamond-open',8,'#FFA726','High',1,'BB상단터치','상단BB접촉'),
    'BB_Lower_Touch':_sig(.8,_N,'⬇️','BB▼T','diamond-open',8,'#4FC3F7','Low',-1,'BB하단터치','하단BB접촉'),
    'BB_Upper_Break':_sig(1,_B,'🔝','BB▲Br','diamond-open',10,'#00E5FF','High',1,'BB상단돌파','종가>상단BB'),
    'BB_Lower_Break':_sig(1,_S,'💀','BB▼Br','diamond-open',10,'#FF6E40','Low',-1,'BB하단붕괴','종가<하단BB'),
    'BB_Lower_Bounce':_sig(1.2,_B,'⤵️','BB▼Bo','diamond-open',10,'#4FC3F7','Low',-1.2,'BB하단반등','하단BB+양봉전환'),
    'BB_Upper_Walk':_sig(1.5,_B,'🚶','BBW▲','arrow-up',10,'#00E676','High',1.2,'BB상단워크','연속상단BB'),
    'BB_Lower_Walk':_sig(1.5,_S,'🚶','BBW▼','arrow-down',10,'#FF1744','Low',-1.2,'BB하단워크','연속하단BB'),
    'BB_Wide_Bands':_sig(.5,_N,'📊','WdBB','square-open',8,'#FFAB40','Low',-.4,'넓은BB','BB폭확대'),
    'Bullish_Engulfing':_sig(1.5,_B,'☀️','BullEng','square',10,'#00E676','Low',-1.3,'상승장악형','하락캔들감싸는양봉'),
    'Bearish_Engulfing':_sig(1.5,_S,'🌑','BearEng','x',10,'#D50000','High',1.3,'하락장악형','상승캔들감싸는음봉'),
    'Morning_Star':_sig(2,_B,'🌅','MornSt','star',13,'#00E676','Low',-2,'모닝스타','큰음봉→소형→강한양봉'),
    'Evening_Star':_sig(2,_S,'🌆','EveSt','star',13,'#FF1744','High',2,'이브닝스타','큰양봉→소형→강한음봉'),
    'Doji':_sig(.5,_N,'➕','Doji','cross-thin',8,'#FFC107','Low',-.5,'도지','시가≈종가'),
    'Doji_Bullish':_sig(.8,_B,'➕','DjBull','cross-thin',9,'#69F0AE','Low',-1,'강세도지','도지+하락추세후'),
    'Doji_Bearish':_sig(.8,_S,'➖','DjBear','cross-thin',9,'#FF5252','High',1,'약세도지','도지+상승추세후'),
    'Hammer':_sig(1.5,_B,'🔨','Hammer','triangle-up',11,'#00E676','Low',-1.5,'해머','긴하단꼬리'),
    'Shooting_Star':_sig(1.5,_S,'🌠','ShStar','triangle-down',11,'#FF1744','High',1.5,'슈팅스타','긴상단꼬리'),
    'Spinning_Top':_sig(.3,_N,'🔄','SpinT','circle-open',7,'#90A4AE','Low',-.3,'팽이형','소형실체'),
    'Inside_Day':_sig(.3,_N,'📦','InDay','square-open',7,'#FFC107','Low',-.3,'인사이드데이','전일범위안'),
    'Outside_Bullish':_sig(1.5,_B,'💪','OutB','square',11,'#00E676','Low',-1.5,'강세아웃사이드','범위포함+양봉'),
    'Outside_Bearish':_sig(1.5,_S,'🥊','OutBr','square',11,'#FF1744','High',1.5,'약세아웃사이드','범위포함+음봉'),
    'MACD_Cross_Buy':_sig(1,_B,'〽️','MCD▲','triangle-up',9,'#4CAF50','Low',-1,'MACD골든','MACD>시그널'),
    'MACD_Cross_Sell':_sig(1,_S,'〽️','MCD▼','triangle-down',9,'#E57373','High',1,'MACD데드','MACD<시그널'),
    'MACD_Zero_Cross_Buy':_sig(1.2,_B,'⬆️','MC0▲','triangle-up',10,'#4CAF50','Low',-1,'MACD0↑','MACD>0'),
    'MACD_Zero_Cross_Sell':_sig(1.2,_S,'⬇️','MC0▼','triangle-down',10,'#E57373','High',1,'MACD0↓','MACD<0'),
    'StochRSI_Cross_Buy':_sig(.8,_B,'🔄','StR▲','circle-open',8,'#81C784','Low',-.8,'StRSI매수','%K>%D과매도'),
    'StochRSI_Cross_Sell':_sig(.8,_S,'🔄','StR▼','circle-open',8,'#EF9A9A','High',.8,'StRSI매도','%K<%D과매수'),
    'Stoch_Reached_OB':_sig(.5,_N,'📊','St→OB','triangle-up',7,'#FFA726','High',.5,'Stoch과매수도달','%K≥80'),
    'Stoch_Reached_OS':_sig(.5,_N,'📊','St→OS','triangle-down',7,'#4FC3F7','Low',-.5,'Stoch과매도도달','%K≤20'),
    'Stoch_Overbought':_sig(.8,_S,'🔴','StOB','circle',8,'#FF5252','High',.8,'Stoch과매수','%K>80&%D>80'),
    'Stoch_Oversold':_sig(.8,_B,'🟢','StOS','circle',8,'#69F0AE','Low',-.8,'Stoch과매도','%K<20&%D<20'),
    'DMI_Cross_Bull':_sig(1.5,_B,'📈','DMI▲','triangle-up',10,'#00E676','Low',-1.2,'DMI강세교차','+DI>-DI'),
    'DMI_Cross_Bear':_sig(1.5,_S,'📉','DMI▼','triangle-down',10,'#FF1744','High',1.2,'DMI약세교차','-DI>+DI'),
    'ADX_New_Uptrend':_sig(1.5,_B,'🚀','ADX▲','arrow-up',11,'#76FF03','Low',-1.4,'신규상승추세','ADX>25+DI↑'),
    'ADX_New_Downtrend':_sig(1.5,_S,'💨','ADX▼','arrow-down',11,'#FF3D00','High',1.4,'신규하락추세','ADX>25+DI↓'),
    'ADX_Momentum_Buy':_sig(1.5,_B,'🚀','ADXIg','arrow-up',11,'#76FF03','Low',-1.4,'ADX점화','ADX>20+DI↑'),
    'ADX_Momentum_Sell':_sig(1.5,_S,'💨','ADXDn','arrow-down',11,'#FF3D00','High',1.4,'ADX하락점화','ADX>20+DI↓'),
    'RSI_Cross_30_Up':_sig(1,_B,'📈','RSI30▲','triangle-up',9,'#4CAF50','Low',-1,'RSI30↑','RSI>30'),
    'RSI_Cross_50_Up':_sig(1,_B,'📈','RSI50▲','triangle-up',9,'#69F0AE','Low',-.8,'RSI50↑','RSI>50'),
    'RSI_Cross_70_Down':_sig(1,_S,'📉','RSI70▼','triangle-down',9,'#EF5350','High',1,'RSI70↓','RSI<70'),
    'RSI_Cross_50_Down':_sig(1,_S,'📉','RSI50▼','triangle-down',9,'#FF5252','High',.8,'RSI50↓','RSI<50'),
    'Gap_Up':_sig(1,_B,'⏫','Gap▲','arrow-up',10,'#00E676','Low',-1,'갭상승','시가>전일고'),
    'Gap_Down':_sig(1,_S,'⏬','Gap▼','arrow-down',10,'#FF1744','High',1,'갭하락','시가<전일저'),
    'Gap_Up_Closed':_sig(.8,_S,'🔄','GpUF','circle-open',8,'#FFA726','High',.8,'갭업메움','갭메움'),
    'Gap_Down_Closed':_sig(.8,_B,'🔄','GpDF','circle-open',8,'#4FC3F7','Low',-.8,'갭다운메움','갭메움'),
    'NR7':_sig(.5,_N,'🔳','NR7','square-open',7,'#90A4AE','Low',-.3,'NR7','7일최소범위'),
    'NR7_2':_sig(.8,_N,'🔳','NR72','square-open',8,'#90A4AE','Low',-.5,'NR7-2','2일연속NR7'),
    'Narrow_Range_Bar':_sig(.5,_N,'📊','NrBar','square-open',7,'#90A4AE','Low',-.3,'좁은범위봉','범위<ATR×.5'),
    'Wide_Range_Bar':_sig(.5,_N,'📊','WdBar','square-open',7,'#FFAB40','Low',-.4,'넓은범위봉','범위>ATR×2'),
    'Calm_After_Storm':_sig(1,_N,'🌤️','Calm','diamond-open',9,'#FFC107','Low',-.8,'폭풍뒤고요','WR→NR'),
    'New_52W_High':_sig(1.5,_B,'🏔️','52H','star-triangle-up',12,'#FFD700','High',1.5,'52주신고가','52주고가갱신'),
    'New_52W_Low':_sig(1.5,_S,'🕳️','52L','star-triangle-down',12,'#B71C1C','Low',-1.5,'52주신저가','52주저가갱신'),
    'New_52W_Closing_High':_sig(1.2,_B,'🏆','52CH','star',11,'#FFD700','High',1.2,'52주종가신고','종가최고'),
    'New_52W_Closing_Low':_sig(1.2,_S,'💀','52CL','star',11,'#B71C1C','Low',-1.2,'52주종가신저','종가최저'),
    'Up_3_Days':_sig(.5,_B,'📗','Up3','triangle-up',8,'#69F0AE','High',.5,'3일연속↑','3일양봉'),
    'Up_4_Days':_sig(.6,_B,'📗','Up4','triangle-up',8,'#69F0AE','High',.6,'4일연속↑','4일양봉'),
    'Up_5_Days':_sig(.8,_B,'📗','Up5','triangle-up',9,'#00E676','High',.8,'5일연속↑','5일양봉'),
    'Down_3_Days':_sig(.5,_S,'📕','Dn3','triangle-down',8,'#FF5252','Low',-.5,'3일연속↓','3일음봉'),
    'Down_4_Days':_sig(.6,_S,'📕','Dn4','triangle-down',8,'#FF5252','Low',-.6,'4일연속↓','4일음봉'),
    'Down_5_Days':_sig(.8,_S,'📕','Dn5','triangle-down',9,'#FF1744','Low',-.8,'5일연속↓','5일음봉'),
    'Multiple_Ten_Bull':_sig(1,_B,'💯','Rnd▲','triangle-up',9,'#00E676','Low',-1,'10배수강세','라운드넘버돌파'),
    'Multiple_Ten_Bear':_sig(1,_S,'💯','Rnd▼','triangle-down',9,'#FF1744','High',1,'10배수약세','라운드넘버이탈'),
    'Pocket_Pivot':_sig(1.5,_B,'🧲','PkPvt','triangle-up',11,'#7C4DFF','Low',-1.5,'포켓피봇','양봉+거래량>10일하락최대'),
    'Parabolic_Rise':_sig(2,_N,'🚀','Para','star-diamond',13,'#FF6D00','High',2,'포물선상승','급격한수직상승'),
    'Three_Weeks_Tight':_sig(1.5,_B,'📦','3WT','square',11,'#00E676','Low',-1.5,'3주타이트','3주좁은종가'),
    'Squeeze_Fire_Buy':_sig(1.5,_B,'💥','SqF▲','star-diamond',14,'#00FFFF','Low',-1.5,'스퀴즈매수','TTM해소+모멘텀↑'),
    'Squeeze_Fire_Sell':_sig(1.5,_S,'🧨','SqF▼','star-diamond',14,'#FF6600','High',1.5,'스퀴즈매도','TTM해소+모멘텀↓'),
    'Volume_Climax_Buy':_sig(2,_B,'🌊','VCl▲','hexagram',14,'#00BCD4','Low',-2.8,'거래량클라이맥스','3x거래량+WT과매도+반전'),
    'Volume_Climax_Sell':_sig(2,_S,'🌋','VCl▼','hexagram',14,'#FF5722','High',2.8,'거래량클라이맥스','3x거래량+WT과매수+반전'),
    'Volume_Surge':_sig(1.5,_N,'🌊','VSrg','hexagram',12,'#00BCD4','Low',-1,'거래량급증','거래량≥50일평균×3'),
    'OBV_Div_Buy':_sig(.8,_B,'📊','OBV▲','triangle-up',10,'#80DEEA','Low',-1.4,'OBV다이버','OBV↑vs가격↓'),
    'OBV_Div_Sell':_sig(.8,_S,'🔻','OBV▼','triangle-down',10,'#FFAB91','High',1.4,'OBV다이버','OBV↓vs가격↑'),
    'SuperTrend_Buy':_sig(1.5,_B,'📈','ST▲','arrow-up',12,'#00E5FF','Low',-1.5,'ST강세','ST위로돌파'),
    'SuperTrend_Sell':_sig(2,_S,'📉','ST▼','arrow-down',12,'#FF1744','High',1.5,'ST약세','ST하향돌파'),
    'EMA_Pullback_Buy':_sig(2,_B,'🎯','EPB▲','triangle-up',13,'#00BFA5','Low',-1.8,'EMA눌림목','상승추세EMA조정'),
    'EMA_Pullback_Sell':_sig(2,_S,'🎯','EPB▼','triangle-down',13,'#FF6E40','High',1.8,'EMA되돌림','하락추세EMA반등'),
    'Momentum_Ignition_Buy':_sig(2.5,_B,'🔥','MIg▲','star-diamond',15,'#FF6D00','Low',-2.5,'모멘텀점화','장대양봉+거래량'),
    'Momentum_Ignition_Sell':_sig(2.5,_S,'💣','MIg▼','star-diamond',15,'#D50000','High',2.5,'모멘텀점화매도','장대음봉+거래량'),
    'Parabolic_Bottom_Buy':_sig(3,_B,'🧊','PBot','diamond',16,'#00FFFF','Low',-3,'포물선바닥','WT<-70꺾임+양봉'),
    'Parabolic_Top_Sell':_sig(3,_S,'🌡️','PTop','diamond',16,'#FF0000','High',3,'포물선천장','WT>70꺾임+음봉'),
    'VWAP_Bounce_Buy':_sig(1.5,_B,'🏦','VW▲','triangle-up',11,'#00E5FF','Low',-1.3,'VWAP반등','VWAP복귀+WT교차'),
    'VWAP_Reject_Sell':_sig(1.5,_S,'🏛️','VW▼','triangle-down',11,'#FF6E40','High',1.3,'VWAP저항','VWAP실패'),
    'MF_Cross_Bull':_sig(1.5,_B,'💰','MF▲','triangle-up',11,'#00E676','Low',-1.2,'MF강세','자금흐름양전환'),
    'MF_Cross_Bear':_sig(1.5,_S,'💸','MF▼','triangle-down',11,'#FF1744','High',1.2,'MF약세','자금흐름음전환'),
    'MF_Bull_Div':_sig(1.8,_B,'💹','MFBd','triangle-up',11,'#7C4DFF','Low',-1.5,'MF상승다이버','가격↓vsMF↑'),
    'MF_Bear_Div':_sig(1.8,_S,'💹','MFBrd','triangle-down',11,'#E040FB','High',1.5,'MF하락다이버','가격↑vsMF↓'),
    'MF_Accel_Up':_sig(1,_B,'📈','MFA▲','arrow-up',9,'#69F0AE','Low',-.8,'MF가속↑','5일MF연속↑'),
    'MF_Accel_Dn':_sig(1,_S,'📉','MFA▼','arrow-down',9,'#FF5252','High',.8,'MF가속↓','5일MF연속↓'),
    'Kumo_Breakout_Bull':_sig(2,_B,'☁️','Kumo▲','triangle-up',13,'#00E676','Low',-2,'쿠모상향돌파','종가>구름상단'),
    'Kumo_Breakout_Bear':_sig(2,_S,'☁️','Kumo▼','triangle-down',13,'#FF1744','High',2,'쿠모하향돌파','종가<구름하단'),
    'TK_Cross_Bull':_sig(1.5,_B,'⛩️','TK▲','triangle-up',10,'#69F0AE','Low',-1.2,'TK골든','전환>기준'),
    'TK_Cross_Bear':_sig(1.5,_S,'⛩️','TK▼','triangle-down',10,'#FF5252','High',1.2,'TK데드','전환<기준'),
    'CMF_Bull':_sig(1.2,_B,'🌀','CMF▲','triangle-up',10,'#00BCD4','Low',-1,'CMF강세','CMF>0.1'),
    'CMF_Bear':_sig(1.2,_S,'🌀','CMF▼','triangle-down',10,'#FF5722','High',1,'CMF약세','CMF<-0.1'),
    'Setup_Squeeze_Bull':_sig(1,_B,'⏳','SqS▲','hourglass',10,'#80DEEA','Low',-.8,'스퀴즈셋업▲','BB축소+모멘텀↑임박'),
    'Setup_Squeeze_Bear':_sig(1,_S,'⏳','SqS▼','hourglass',10,'#FFAB91','High',.8,'스퀴즈셋업▼','BB축소+모멘텀↓임박'),
    'Momentum_Accel_Buy':_sig(1.5,_B,'⚡','MoA▲','arrow-up',11,'#76FF03','Low',-1.2,'모멘텀가속▲','RSI+WT+MACD가속'),
    'Momentum_Accel_Sell':_sig(1.5,_S,'⚡','MoA▼','arrow-down',11,'#FF3D00','High',1.2,'모멘텀가속▼','RSI+WT+MACD감속'),
    'Volume_Dry_Up':_sig(.5,_N,'🏜️','VDry','square-open',8,'#FFE082','Low',-.3,'거래량고갈','5일연속평균이하'),
    'WT_Convergence_Bull':_sig(1.2,_B,'🔀','WTC▲','triangle-up',10,'#B2FF59','Low',-1,'WT수렴매수','빠른수렴+과매도'),
    'WT_Convergence_Bear':_sig(1.2,_S,'🔀','WTC▼','triangle-down',10,'#FF8A80','High',1,'WT수렴매도','빠른수렴+과매수'),
    'Volume_POC_Breakout':_sig(2,_B,'🏛️','POC▲','triangle-up',13,'#7C4DFF','Low',-1.8,'POC상향','종가>POC'),
    'Volume_POC_Breakdown':_sig(2,_S,'🏛️','POC▼','triangle-down',13,'#E040FB','High',1.8,'POC하향','종가<POC'),
    'VP_VAH_Resistance':_sig(1,_S,'🏛️','VAH','triangle-down',10,'#FFAB91','High',1,'VAH저항','VA상단접근'),
    'VP_VAL_Support':_sig(1,_B,'🏛️','VAL','triangle-up',10,'#80DEEA','Low',-1,'VAL지지','VA하단접근'),
    'Relative_Strength_Buy':_sig(2,_B,'💪','RS▲','star-diamond',13,'#00E5FF','Low',-1.8,'상대강도매수','SPY대비강세'),
    'Relative_Strength_Sell':_sig(1.5,_S,'🐌','RS▼','star-diamond',11,'#FF6E40','High',1.5,'상대약세매도','SPY대비약세'),
    'UTBot_Buy':_sig(2,_B,'🤖','UTBot▲','triangle-up',15,'#00E676','Low',-2,'UT봇매수','ATR트레일링전환'),
    'UTBot_Sell':_sig(2,_S,'🤖','UTBot▼','triangle-down',15,'#FF1744','High',2,'UT봇매도','ATR트레일링전환'),
    'Hull_Turn_Bull':_sig(1.8,_B,'🟢','Hull▲','circle',15,'#00E676','Low',-1.5,'Hull강세전환','HMA빨강→초록'),
    'Hull_Turn_Bear':_sig(1.8,_S,'🔴','Hull▼','circle',15,'#FF1744','High',1.5,'Hull약세전환','HMA초록→빨강'),
    'StochSlow_Cross_Buy':_sig(1,_B,'🔄','StSl▲','circle-open',9,'#81C784','Low',-1,'StochSlow매수','SlowK>SlowD바닥권'),
    'StochSlow_Cross_Sell':_sig(1,_S,'🔄','StSl▼','circle-open',9,'#EF9A9A','High',1,'StochSlow매도','SlowK<SlowD천장권'),
    'Squeeze_Mom_Cross_Up':_sig(1.5,_B,'💥','SqMom▲','diamond',11,'#00FFFF','Low',-1.2,'스퀴즈모멘텀0↑','모멘텀음→양'),
    'Squeeze_Mom_Cross_Down':_sig(1.5,_S,'💥','SqMom▼','diamond',11,'#FF6600','High',1.2,'스퀴즈모멘텀0↓','모멘텀양→음'),
    'VuManChu_Bull':_sig(2.5,_B,'💎','VuMC▲','star',14,'#00E676','Low',-2.5,'VuManChu강세','WT과매도+Hull강세+반전'),
    'VuManChu_Bear':_sig(2.5,_S,'💎','VuMC▼','star',14,'#FF1744','High',2.5,'VuManChu약세','WT과매수+Hull약세+반전'),
    'Volume_Dry_Breakout_Buy':_sig(2,_B,'🏜️','VDB▲','triangle-up',12,'#00E676','Low',-2,'건조돌파매수','5일건조후거래량폭발'),
    'Volume_Dry_Breakout_Sell':_sig(2,_S,'🏜️','VDB▼','triangle-down',12,'#FF1744','High',2,'건조돌파매도','5일건조후거래량폭발'),
    'Doji_Breakout_Buy':_sig(1.5,_B,'➕','DjBO▲','triangle-up',10,'#00E676','Low',-1.5,'도지돌파매수','연속도지후방향결정'),
    'Doji_Breakout_Sell':_sig(1.5,_S,'➕','DjBO▼','triangle-down',10,'#FF1744','High',1.5,'도지돌파매도','연속도지후방향결정'),
    'Three_Bar_Reversal_Buy':_sig(2,_B,'🔃','3BR▲','triangle-up',12,'#00BFA5','Low',-2,'3바반전매수','3연하후강한양봉'),
    'Three_Bar_Reversal_Sell':_sig(2,_S,'🔃','3BR▼','triangle-down',12,'#D50000','High',2,'3바반전매도','3연상후강한음봉'),
    'System_Turn_Bull':_sig(3.5,_B,'','SysUp','star-diamond',16,'#00FF00','Low',-4,'System Buy Turn','Engine-wide buy judgment flip'),
    'System_Turn_Bear':_sig(3.5,_S,'','SysDn','star-diamond',16,'#FF0000','High',4,'System Sell Turn','Engine-wide sell judgment flip'),
}

COMBINED_SCAN_REGISTRY={
    'CS_Ultimate_Buy':{'name':'🏆 ULTIMATE BUY','kor':'궁극의매수','dir':'buy','tier':1,'icon':'🏆','color':'#FFD700','desc':'6중확인','win':'75-85%'},
    'CS_Triple_Oversold_Reversal':{'name':'🔥 Triple OS','kor':'삼중과매도반전','dir':'buy','tier':1,'icon':'🔥','color':'#00E676','desc':'WT+RSI+Stoch+반전','win':'70-80%'},
    'CS_Breakout_Momentum_Buy':{'name':'🚀 Breakout','kor':'돌파모멘텀','dir':'buy','tier':1,'icon':'🚀','color':'#00E676','desc':'52W+거래량+ADX','win':'65-75%'},
    'CS_Institutional_Accumulation':{'name':'🏦 Instit','kor':'기관매집','dir':'buy','tier':1,'icon':'🏦','color':'#00BCD4','desc':'포켓피봇+OBV','win':'70-80%'},
    'CS_Divergence_Confluence_Buy':{'name':'📊 DivConf','kor':'다이버합류매수','dir':'buy','tier':1,'icon':'📊','color':'#7C4DFF','desc':'다중다이버전스','win':'70-80%'},
    'CS_Capitulation_Bottom':{'name':'🏳️ Capitul','kor':'항복바닥','dir':'buy','tier':1,'icon':'🏳️','color':'#00E676','desc':'52W저+극과매도','win':'70-80%'},
    'CS_Triple_Confirm_Buy':{'name':'🤖 TriConf▲','kor':'삼중확인매수','dir':'buy','tier':1,'icon':'🤖','color':'#00E676','desc':'UTBot+Hull+WT동시','win':'75-85%'},
    'CS_VuManChu_Squeeze_Buy':{'name':'💎 VuMC+Sq▲','kor':'VuManChu스퀴즈매수','dir':'buy','tier':1,'icon':'💎','color':'#00E676','desc':'VuManChu+스퀴즈해소','win':'80-90%'},
    'CS_Ultimate_Sell':{'name':'🏆 ULTIMATE SELL','kor':'궁극의매도','dir':'sell','tier':1,'icon':'🏆','color':'#FFD700','desc':'6중확인','win':'75-85%'},
    'CS_Triple_Overbought_Exhaustion':{'name':'🌡️ Triple OB','kor':'삼중과매수소진','dir':'sell','tier':1,'icon':'🌡️','color':'#FF1744','desc':'WT+RSI+Stoch+반전','win':'70-80%'},
    'CS_Breakdown_Momentum_Sell':{'name':'💨 Breakdown','kor':'붕괴모멘텀','dir':'sell','tier':1,'icon':'💨','color':'#FF1744','desc':'52W+거래량+ADX','win':'65-75%'},
    'CS_Parabolic_Exhaustion_Sell':{'name':'🎢 ParaExh','kor':'포물선소진','dir':'sell','tier':1,'icon':'🎢','color':'#D50000','desc':'포물선+천장캔들','win':'70-80%'},
    'CS_Divergence_Confluence_Sell':{'name':'📉 DivConf','kor':'다이버합류매도','dir':'sell','tier':1,'icon':'📉','color':'#E040FB','desc':'다중다이버전스','win':'70-80%'},
    'CS_Blow_Off_Top':{'name':'🎆 BlowOff','kor':'블로우오프천장','dir':'sell','tier':1,'icon':'🎆','color':'#FF1744','desc':'52W고+극과매수','win':'70-80%'},
    'CS_Triple_Confirm_Sell':{'name':'🤖 TriConf▼','kor':'삼중확인매도','dir':'sell','tier':1,'icon':'🤖','color':'#FF1744','desc':'UTBot+Hull+WT동시','win':'75-85%'},
    'CS_VuManChu_Squeeze_Sell':{'name':'💎 VuMC+Sq▼','kor':'VuManChu스퀴즈매도','dir':'sell','tier':1,'icon':'💎','color':'#FF1744','desc':'VuManChu+스퀴즈해소','win':'80-90%'},
    'CS_Trend_Pullback_Buy':{'name':'🎯 TrendPB','kor':'추세눌림목','dir':'buy','tier':2,'icon':'🎯','color':'#00E676','desc':'상승추세+MA지지','win':'60-70%'},
    'CS_Squeeze_Breakout_Buy':{'name':'💥 SqBreak','kor':'스퀴즈돌파','dir':'buy','tier':2,'icon':'💥','color':'#00FFFF','desc':'BB해소+상방','win':'60-70%'},
    'CS_MA_Confluence_Buy':{'name':'📈 MAConf','kor':'MA합류','dir':'buy','tier':2,'icon':'📈','color':'#69F0AE','desc':'골든+정배열','win':'60-70%'},
    'CS_Cooper_Setup_Buy':{'name':'🃏 Cooper','kor':'쿠퍼셋업','dir':'buy','tier':2,'icon':'🃏','color':'#FF6D00','desc':'ADX+쿠퍼패턴','win':'60-70%'},
    'CS_Volume_Climax_Rev_Buy':{'name':'🌊 VolRev','kor':'거래량반전','dir':'buy','tier':2,'icon':'🌊','color':'#00BCD4','desc':'거래량폭발+과매도','win':'60-70%'},
    'CS_Ichimoku_Breakout_Buy':{'name':'☁️ IchiBreak','kor':'이치모쿠돌파','dir':'buy','tier':2,'icon':'☁️','color':'#00E676','desc':'쿠모+TK','win':'60-70%'},
    'CS_Trend_Rejection_Sell':{'name':'🎯 TrendRej','kor':'추세거부','dir':'sell','tier':2,'icon':'🎯','color':'#FF1744','desc':'하락추세+MA저항','win':'60-70%'},
    'CS_Squeeze_Breakdown_Sell':{'name':'💨 SqBrkDn','kor':'스퀴즈붕괴','dir':'sell','tier':2,'icon':'💨','color':'#FF6600','desc':'BB해소+하방','win':'60-70%'},
    'CS_MA_Breakdown_Sell':{'name':'📉 MABreak','kor':'MA붕괴','dir':'sell','tier':2,'icon':'📉','color':'#FF5252','desc':'데스+역배열','win':'60-70%'},
    'CS_Cooper_Setup_Sell':{'name':'🃏 CooperSell','kor':'쿠퍼매도','dir':'sell','tier':2,'icon':'🃏','color':'#FF3D00','desc':'ADX+쿠퍼매도','win':'60-70%'},
    'CS_Gap_Failure_Sell':{'name':'⏬ GapFail','kor':'갭실패','dir':'sell','tier':2,'icon':'⏬','color':'#FF1744','desc':'갭업후약세반전','win':'60-70%'},
    'CS_Bottom_Fishing_Buy':{'name':'BottomFish','kor':'Bottom Fishing Reversal','dir':'buy','tier':2,'icon':'','color':'#00E676','desc':'deep oversold + reversal confirmation','win':'62-74%'},
    'CS_Top_Fishing_Sell':{'name':'TopFish','kor':'Top Fishing Reversal','dir':'sell','tier':2,'icon':'','color':'#FF5252','desc':'deep overbought + reversal confirmation','win':'62-74%'},
    'CS_Oversold_Bounce_Buy':{'name':'🏓 OSBounce','kor':'과매도반등','dir':'buy','tier':3,'icon':'🏓','color':'#69F0AE','desc':'Stoch과매도+캔들','win':'55-65%'},
    'CS_Momentum_Accel_Buy':{'name':'⚡ MomAcc','kor':'모멘텀가속','dir':'buy','tier':3,'icon':'⚡','color':'#76FF03','desc':'RSI+WT+MACD가속','win':'55-65%'},
    'CS_Structure_Support_Buy':{'name':'🏗️ Support','kor':'구조적지지','dir':'buy','tier':3,'icon':'🏗️','color':'#4FC3F7','desc':'VP+BB지지','win':'55-65%'},
    'CS_Overbought_Fade_Sell':{'name':'📉 OBFade','kor':'과매수페이드','dir':'sell','tier':3,'icon':'📉','color':'#FF5252','desc':'Stoch과매수+캔들','win':'55-65%'},
    'CS_Volatility_Explosion':{'name':'💣 VolExpl','kor':'변동성폭발셋업','dir':'neutral','tier':2,'icon':'💣','color':'#FFC107','desc':'NR7+BB스퀴즈','win':'방향70%+'},
}

STRONG_BUY_SIGS={'System_Turn_Bull','Gold_Dot','Green_Dot_T1','Parabolic_Bottom_Buy','Volume_Climax_Buy','Momentum_Ignition_Buy','Expansion_BO','Morning_Star','Reversal_New_Highs','CS_Ultimate_Buy','CS_Triple_Oversold_Reversal','CS_Breakout_Momentum_Buy','CS_Capitulation_Bottom','CS_Triple_Confirm_Buy','CS_VuManChu_Squeeze_Buy','VuManChu_Bull'}
STRONG_SELL_SIGS={'System_Turn_Bear','Blood_Diamond','Red_Dot_T1','Parabolic_Top_Sell','Volume_Climax_Sell','Momentum_Ignition_Sell','Expansion_BD','Evening_Star','Reversal_New_Lows','CS_Ultimate_Sell','CS_Triple_Overbought_Exhaustion','CS_Breakdown_Momentum_Sell','CS_Blow_Off_Top','CS_Parabolic_Exhaustion_Sell','CS_Triple_Confirm_Sell','CS_VuManChu_Squeeze_Sell','VuManChu_Bear'}

COOLDOWN_MAP={'Squeeze_Fire_Buy':5,'Squeeze_Fire_Sell':5,'Bullish_Engulfing':5,'Bearish_Engulfing':5,'Hammer':5,'Shooting_Star':5,'Morning_Star':7,'Evening_Star':7,'Golden_Cross':20,'Death_Cross':20,'Expansion_BO':10,'Expansion_BD':10,'Gilligans_Buy':10,'Gilligans_Sell':10,'MACD_Cross_Buy':12,'MACD_Cross_Sell':12,'Kumo_Breakout_Bull':10,'Kumo_Breakout_Bear':10,'New_52W_High':10,'New_52W_Low':10,'StochRSI_Cross_Buy':7,'StochRSI_Cross_Sell':7,'ADX_Momentum_Buy':10,'ADX_Momentum_Sell':10,'EMA_Pullback_Buy':7,'EMA_Pullback_Sell':7,'SuperTrend_Buy':10,'SuperTrend_Sell':10,'Parabolic_Bottom_Buy':5,'Parabolic_Top_Sell':5,'DMI_Cross_Bull':10,'DMI_Cross_Bear':10,'Boomer_Buy':10,'Boomer_Sell':10,'Setup_180_Bull':7,'Setup_180_Bear':7,'VWAP_Bounce_Buy':7,'VWAP_Reject_Sell':7,'Momentum_Ignition_Buy':10,'Momentum_Ignition_Sell':10,'Slingshot_Bull':7,'Slingshot_Bear':7,'MF_Cross_Bull':10,'MF_Cross_Bear':10,'Pullback_123_Bull':7,'Pullback_123_Bear':7,'UTBot_Buy':10,'UTBot_Sell':10,'Hull_Turn_Bull':7,'Hull_Turn_Bear':7,'StochSlow_Cross_Buy':7,'StochSlow_Cross_Sell':7,'Squeeze_Mom_Cross_Up':5,'Squeeze_Mom_Cross_Down':5,'VuManChu_Bull':10,'VuManChu_Bear':10,'Volume_Dry_Breakout_Buy':7,'Volume_Dry_Breakout_Sell':7,'Doji_Breakout_Buy':5,'Doji_Breakout_Sell':5,'Three_Bar_Reversal_Buy':5,'Three_Bar_Reversal_Sell':5}

# ━━━ 유틸리티 ━━━
def _recent(s,lb=3):return s.astype(float).rolling(lb+1,min_periods=1).max().fillna(0).astype(bool)
def _cooldown(sig,bars=5):
    v=sig.fillna(False).values.astype(bool);out=np.zeros(len(v),dtype=bool);last=-bars-1
    for i in range(len(v)):
        if v[i] and (i-last)>bars:out[i]=True;last=i
    return pd.Series(out,index=sig.index)
def _cd_dir(df,bs,ss,bars=5):
    bv=df.get(bs,pd.Series(False,index=df.index)).fillna(False).values.astype(bool)
    sv=df.get(ss,pd.Series(False,index=df.index)).fillna(False).values.astype(bool)
    bo=np.zeros(len(bv),dtype=bool);so=np.zeros(len(sv),dtype=bool);lb_=-bars-1;ls_=-bars-1
    for i in range(len(df)):
        if sv[i]:lb_=-bars-1
        if bv[i]:ls_=-bars-1
        if bv[i] and (i-lb_)>bars:bo[i]=True;lb_=i
        if sv[i] and (i-ls_)>bars:so[i]=True;ls_=i
    if bs in df.columns:df[bs]=pd.Series(bo,index=df.index)
    if ss in df.columns:df[ss]=pd.Series(so,index=df.index)
def _volf(vol,r=.5,p=20):return vol>=(vol.rolling(p,min_periods=5).mean()*r)
def _valid_fmt(t):return bool(re.match(r'^[A-Za-z]{1,5}([.\-][A-Za-z]{1,2})?$',t))
def _vs(cond):c=cond.fillna(False).astype(int);g=(c==0).cumsum();return c.groupby(g).cumsum()
def _sp(df,sn,pts):
    if sn not in df.columns:return pd.Series(0.,index=df.index)
    return pd.Series(np.where(df[sn].fillna(False),pts,0.),index=df.index)
def _spd(df,sn,fp,dd=3,dr=.5):
    if sn not in df.columns:return np.zeros(len(df),dtype=float)
    b=np.where(df[sn].fillna(False),fp,0.);t=b.copy()
    for d in range(1,dd+1):s=np.roll(b,d);s[:d]=0;t+=s*(dr**d)
    return t
def _cs_str(cs_list):return ', '.join(f"{c['icon']}{c['kor']}[T{c['tier']}]" for c in cs_list)
def _sf(val,default=0.):
    try:r=float(val);return r if r==r else default
    except:return default

# ━━━ 캐시 ━━━
@st.cache_data(ttl=3600,show_spinner=False)
def fetch_fundamentals(t):
    try:
        info=yf.Ticker(t).info
        def g(key,fmt=None):
            val=info.get(key)
            if val is None:return "N/A"
            try:
                if fmt=='$':return f"${val:,.2f}"
                if fmt=='n':return f"{val:,.0f}"
                return str(val)
            except:return "N/A"
        return f"MCap:{g('marketCap','n')} PE:{g('trailingPE')} 52H:{g('fiftyTwoWeekHigh','$')} 52L:{g('fiftyTwoWeekLow','$')} AvgVol:{g('averageVolume','n')}"
    except:return "N/A"
@st.cache_data(ttl=300,max_entries=30,show_spinner=False)
def fetch_history(t,_ts=None):
    try:return yf.Ticker(t).history(period="2y")
    except:return pd.DataFrame()
@st.cache_data(ttl=3600,show_spinner=False)
def fetch_spy(_ts=None):return yf.Ticker("SPY").history(period="2y")
@st.cache_data(ttl=3600,show_spinner=False)
def validate_ticker(t):
    try:return not yf.Ticker(t).history(period="5d").empty
    except:return False
@st.cache_data(ttl=300,max_entries=50,show_spinner=False)
def _compute_cached(t,k):
    try:
        df=fetch_history(t)
        if df.empty:return None
        try:return modular_detect_all_signals(modular_compute_indicators(df.copy()))
        except Exception as me:
            print(f"[WARN] modular pipeline failed for {t}: {me}; fallback to in-file pipeline")
            return detect_all_signals(compute_indicators(df))
    except Exception as e:print(f"[ERR]{t}:{e}");return None
def compute_and_cache(t,ts=None):
    ck=f"{t}_{ts}" if ts else f"{t}_{math.floor(time.time()/300)}";return _compute_cached(t,ck)

# ━━━ 기술지표 (V14.1과 동일) ━━━
def compute_rsi(s,p=14):d=s.diff();g,l_=d.clip(lower=0),-d.clip(upper=0);return 100-(100/(1+g.ewm(alpha=1/p,min_periods=p).mean()/(l_.ewm(alpha=1/p,min_periods=p).mean()+1e-10)))
def compute_mfi(h,l,c,v,p=14):tp=(h+l+c)/3;r=tp*v;d=tp.diff();return 100-(100/(1+r.where(d>=0,0.).rolling(p).sum()/(r.where(d<0,0.).rolling(p).sum()+1e-10)))
def compute_rsi_mfi(h,l,c,v,p=60):rf,mf=compute_rsi(c,20),compute_mfi(h,l,c,v,20);rs,ms=compute_rsi(c,p),compute_mfi(h,l,c,v,p);return (((rf-50)+(mf-50))/2)*.6+(((rs-50)+(ms-50))/2)*.4
def compute_wavetrend(h,l,c,ch=9,avg=12,ma=3):ap=(h+l+c)/3;esa=ap.ewm(span=ch,adjust=False).mean();d=abs(ap-esa).ewm(span=ch,adjust=False).mean();ci=(ap-esa)/(0.015*d+1e-10);w1=ci.ewm(span=avg,adjust=False).mean();w2=w1.rolling(ma).mean();return w1,w2,(w1>w2)&(w1.shift(1)<=w2.shift(1)),(w1<w2)&(w1.shift(1)>=w2.shift(1))
def compute_stoch_rsi(c,rl=14,sl=14,ks=3,ds=3):r=compute_rsi(c,rl);mn,mx=r.rolling(sl).min(),r.rolling(sl).max();k=(((r-mn)/(mx-mn+1e-10))*100).rolling(ks).mean();return k,k.rolling(ds).mean()
def compute_tr(h,l,c):pc=c.shift(1);return pd.concat([h-l,(h-pc).abs(),(l-pc).abs()],axis=1).max(axis=1)
def compute_adx(h,l,c,p=14):tr=compute_tr(h,l,c);ph,pl=h.shift(1),l.shift(1);plus_dm=pd.Series(np.where((h-ph)>(pl-l),np.maximum(h-ph,0),0),index=h.index,dtype=float);minus_dm=pd.Series(np.where((pl-l)>(h-ph),np.maximum(pl-l,0),0),index=h.index,dtype=float);a=tr.ewm(alpha=1/p,min_periods=p).mean();pdi=100*plus_dm.ewm(alpha=1/p,min_periods=p).mean()/(a+1e-10);mdi=100*minus_dm.ewm(alpha=1/p,min_periods=p).mean()/(a+1e-10);dx=100*(pdi-mdi).abs()/(pdi+mdi+1e-10);return dx.ewm(alpha=1/p,min_periods=p).mean(),pdi,mdi
def compute_obv(c,v):return (v*np.sign(c.diff()).fillna(0)).cumsum()
def compute_macd(c,f=12,s=26,sig=9):ml=c.ewm(span=f,adjust=False).mean()-c.ewm(span=s,adjust=False).mean();sl=ml.ewm(span=sig,adjust=False).mean();return ml,sl,ml-sl
def compute_ichimoku(h,l,c,tp=9,kp=26,sp=52,d=26):tk=(h.rolling(tp).max()+l.rolling(tp).min())/2;kj=(h.rolling(kp).max()+l.rolling(kp).min())/2;sa=((tk+kj)/2).shift(d);sb=((h.rolling(sp).max()+l.rolling(sp).min())/2).shift(d);return tk,kj,sa,sb
def compute_cmf(h,l,c,v,p=20):m=((c-l)-(h-c))/(h-l+1e-10);return (m*v).rolling(p).sum()/(v.rolling(p).sum()+1e-10)
def compute_supertrend(h,l,c,tr,per=10,mult=3.):
    a=tr.rolling(per).mean();hl=(h+l)/2;up=(hl+mult*a).values.copy();dn=(hl-mult*a).values.copy();cl=c.values;n=len(c);sv=np.full(n,np.nan);dv=np.zeros(n,dtype=int);fv=per
    if fv>=n:return pd.Series(np.nan,index=c.index),pd.Series(0,index=c.index,dtype=int)
    dv[fv]=1;sv[fv]=dn[fv]
    for i in range(fv+1,n):
        if dv[i-1]==1:dn[i]=max(dn[i],dn[i-1]) if not np.isnan(dn[i-1]) else dn[i]
        else:up[i]=min(up[i],up[i-1]) if not np.isnan(up[i-1]) else up[i]
        if dv[i-1]==1:dv[i],sv[i]=(-1,up[i]) if cl[i]<dn[i] else (1,dn[i])
        else:dv[i],sv[i]=(1,dn[i]) if cl[i]>up[i] else (-1,up[i])
    return pd.Series(sv,index=c.index),pd.Series(dv,index=c.index)
def compute_vp(h,l,c,v,lb=20,nb=30,step=1):
    n=len(c);poc=np.full(n,np.nan);vah=np.full(n,np.nan);val_=np.full(n,np.nan);cv,hv,lv,vv=c.values,h.values,l.values,v.values;pp,pv_,pvl=np.nan,np.nan,np.nan
    for i in range(lb,n):
        if i>lb and abs(cv[i]-cv[i-1])/(cv[i-1]+1e-10)<0.001:poc[i]=pp;vah[i]=pv_;val_[i]=pvl;continue
        s=i-lb;hw,lw,vw=hv[s:i+1],lv[s:i+1],vv[s:i+1];plo,phi=lw.min(),hw.max()
        if phi-plo<1e-10:poc[i]=cv[i];vah[i]=phi;val_[i]=plo;pp=poc[i];pv_=vah[i];pvl=val_[i];continue
        tp_=(hw+lw+cv[s:i+1])/3;vp_,be=np.histogram(tp_,bins=nb,range=(plo,phi),weights=vw);bc=(be[:-1]+be[1:])/2;pb_=np.argmax(vp_);poc[i]=bc[pb_]
        tv=vp_.sum();tgt=tv*.7;cm=vp_[pb_];lo_i,hi_i=pb_,pb_
        while cm<tgt and (lo_i>0 or hi_i<nb-1):
            lv2=vp_[lo_i-1] if lo_i>0 else 0;hv2=vp_[hi_i+1] if hi_i<nb-1 else 0
            if lv2>=hv2 and lo_i>0:lo_i-=1;cm+=lv2
            elif hi_i<nb-1:hi_i+=1;cm+=hv2
            else:break
        vah[i]=be[min(hi_i+1,nb)];val_[i]=be[lo_i];pp=poc[i];pv_=vah[i];pvl=val_[i]
    return pd.Series(poc,index=c.index).ffill(),pd.Series(vah,index=c.index).ffill(),pd.Series(val_,index=c.index).ffill()
def detect_pivot_div(price,osc,lb=60,pw=5,os_lim=None,ob_lim=None,atr=None):
    n=len(price);pv=price.values.astype(float);ov=osc.values.astype(float);dl=np.full(n,lb,dtype=int)
    if atr is not None and len(atr)>0:ap=atr/(price+1e-10)*100;ar=ap/(ap.rolling(100,min_periods=20).median()+1e-10);ls__=np.clip(1.3-.35*ar.values,.5,1.5);dl=np.clip(lb*ls__,30,90).astype(int)
    pm=max(np.nanmean(np.nan_to_num((atr.rolling(20,min_periods=5).mean()*.3).values,nan=.01)),.01) if atr is not None else .01
    li,_=find_peaks(-pv,distance=pw,prominence=pm);hi,_=find_peaks(pv,distance=pw,prominence=pm)
    bd=np.zeros(n,dtype=bool);brd=np.zeros(n,dtype=bool);hb=np.zeros(n,dtype=bool);hbr=np.zeros(n,dtype=bool)
    for i in range(1,len(li)):
        ci,pi=li[i],li[i-1];gap=ci-pi
        if gap<pw*2 or gap>dl[ci]:continue
        if pv[ci]<pv[pi] and ov[ci]>ov[pi]:
            if os_lim is None or ov[ci]<=os_lim:bd[min(ci+pw,n-1)]=True
        if pv[ci]>pv[pi] and ov[ci]<ov[pi]:hb[min(ci+pw,n-1)]=True
    for i in range(1,len(hi)):
        ci,pi=hi[i],hi[i-1];gap=ci-pi
        if gap<pw*2 or gap>dl[ci]:continue
        if pv[ci]>pv[pi] and ov[ci]<ov[pi]:
            if ob_lim is None or ov[ci]>=ob_lim:brd[min(ci+pw,n-1)]=True
        if pv[ci]<pv[pi] and ov[ci]>ov[pi]:hbr[min(ci+pw,n-1)]=True
    return pd.Series(bd,index=price.index),pd.Series(brd,index=price.index),pd.Series(hb,index=price.index),pd.Series(hbr,index=price.index)
def compute_hull_ma(c,period=20):
    half_p=max(int(period/2),1);sqrt_p=max(int(np.sqrt(period)),1)
    def _wma(s,p):weights=np.arange(1,p+1,dtype=float);return s.rolling(p).apply(lambda x:np.dot(x,weights[-len(x):])/weights[-len(x):].sum(),raw=True)
    hma=_wma(2*_wma(c,half_p)-_wma(c,period),sqrt_p);rising=hma>hma.shift(1);return hma,rising,rising&~rising.shift(1).fillna(False),~rising&rising.shift(1).fillna(False)
def compute_ut_bot(c,h,l,atr,key_value=1):
    n=len(c);xatr=(atr*key_value).values;cv=c.values;ts_=np.zeros(n);dir_=np.zeros(n,dtype=int);ts_[0]=cv[0];dir_[0]=1
    for i in range(1,n):
        if np.isnan(xatr[i]) or np.isnan(cv[i]):ts_[i]=ts_[i-1];dir_[i]=dir_[i-1];continue
        if dir_[i-1]==1:ns=cv[i]-xatr[i];ts_[i]=max(ns,ts_[i-1]);dir_[i],ts_[i]=((-1,cv[i]+xatr[i]) if cv[i]<ts_[i] else (1,ts_[i]))
        else:ns=cv[i]+xatr[i];ts_[i]=min(ns,ts_[i-1]);dir_[i],ts_[i]=((1,cv[i]-xatr[i]) if cv[i]>ts_[i] else (-1,ts_[i]))
    ts_s=pd.Series(ts_,index=c.index);dir_s=pd.Series(dir_,index=c.index);return ts_s,dir_s,(dir_s==1)&(dir_s.shift(1)==-1),(dir_s==-1)&(dir_s.shift(1)==1)
def compute_stochastic_slow(h,l,c,k_period=14,smooth_k=3,d_period=3):ll=l.rolling(k_period).min();hh=h.rolling(k_period).max();fast_k=((c-ll)/(hh-ll+1e-10))*100;slow_k=fast_k.rolling(smooth_k).mean();return slow_k,slow_k.rolling(d_period).mean()
def compute_squeeze_mom_enh(c,h,l,bbu,bbl,kcu,kcl,kc_mid,period=20):sq=(bbu<kcu)&(bbl>kcl);mid_hl=(h.rolling(period).max()+l.rolling(period).min())/2;mom=c-(mid_hl+kc_mid)/2;ms_=mom.ewm(span=period,adjust=False).mean();return {'squeeze_on':sq,'momentum':ms_,'mom_rising':ms_>ms_.shift(1),'mom_positive':ms_>0,'mom_cross_up':(ms_>0)&(ms_.shift(1)<=0),'mom_cross_down':(ms_<0)&(ms_.shift(1)>=0)}

def compute_indicators(df):
    c,h,l,v=df['Close'],df['High'],df['Low'],df['Volume']
    for ma in [5,10,20,50,200]:df[f'MA{ma}']=c.rolling(ma).mean()
    df['EMA8']=c.ewm(span=8,adjust=False).mean();df['EMA21']=c.ewm(span=21,adjust=False).mean()
    df['BB_Mid']=df['MA20'];s20=c.rolling(20).std();df['BB_Up'],df['BB_Low']=df['BB_Mid']+s20*2,df['BB_Mid']-s20*2
    df['BB_Width']=(df['BB_Up']-df['BB_Low'])/(df['BB_Mid']+1e-10);df['Percent_B']=(c-df['BB_Low'])/(df['BB_Up']-df['BB_Low']+1e-10)
    tr=compute_tr(h,l,c);df['ATR']=tr.rolling(14).mean();df['SuperTrend'],df['ST_Direction']=compute_supertrend(h,l,c,tr)
    ak=tr.rolling(10).mean();mk=c.ewm(span=20,adjust=False).mean();df['KC_Upper']=mk+ak*1.5;df['KC_Mid']=mk;df['KC_Lower']=mk-ak*1.5
    w1,w2,wu,wd=compute_wavetrend(h,l,c);df['WT1'],df['WT2'],df['WT_Up'],df['WT_Down']=w1,w2,wu,wd
    df['RSI']=compute_rsi(c,14);df['StochK'],df['StochD']=compute_stoch_rsi(c);df['MFI']=compute_mfi(h,l,c,v,14).fillna(50)
    df['RSI_MFI']=compute_rsi_mfi(h,l,c,v,60);vw=(c*v).rolling(20).sum()/(v.rolling(20).sum()+1e-10);df['VWAP_Osc']=((c-vw)/(vw+1e-10))*100
    df['ADX'],df['Plus_DI'],df['Minus_DI']=compute_adx(h,l,c);df['OBV']=compute_obv(c,v)
    df['MACD_Line'],df['MACD_Signal'],df['MACD_Hist']=compute_macd(c)
    tk,kj,sa,sb=compute_ichimoku(h,l,c);df['Ichimoku_Tenkan']=tk;df['Ichimoku_Kijun']=kj;df['Ichimoku_SenkouA']=sa;df['Ichimoku_SenkouB']=sb
    df['CMF']=compute_cmf(h,l,c,v,20)
    rv=df['RSI']-df['RSI'].shift(3);df['RSI_Accel']=rv-rv.shift(3);wv=df['WT1']-df['WT1'].shift(3);df['WT_Accel']=wv-wv.shift(3);df['MACD_Accel']=df['MACD_Hist']-df['MACD_Hist'].shift(3)
    rn=df['RSI_Accel']/(df['RSI_Accel'].rolling(50,min_periods=10).std()+1e-10);wn=df['WT_Accel']/(df['WT_Accel'].rolling(50,min_periods=10).std()+1e-10);mn=df['MACD_Accel']/(df['MACD_Accel'].rolling(50,min_periods=10).std()+1e-10)
    df['Composite_Accel']=(rn+wn+mn)/3;wg=df['WT1']-df['WT2'];df['WT_Gap']=wg;df['WT_Gap_Abs']=wg.abs();df['WT_Conv_Speed']=df['WT_Gap_Abs'].shift(3)-df['WT_Gap_Abs']
    df['VP_POC'],df['VP_VAH'],df['VP_VAL']=compute_vp(h,l,c,v)
    try:
        spy=fetch_spy()
        if not spy.empty:sc_=c.copy();spc=spy['Close'].reindex(sc_.index,method='ffill');sr=sc_.pct_change(20).fillna(0);spr=spc.pct_change(20).fillna(0);df['Stock_Return']=sr;df['SPY_Return']=spr;df['RS_Ratio']=((1+sr)/(1+spr+1e-10)).rolling(10,min_periods=5).mean()
    except:df['RS_Ratio']=1.;df['SPY_Return']=0.;df['Stock_Return']=0.
    rsc=pd.Series(0.,index=df.index);rsc+=np.where(c>df['MA200'],1,-1);rsc+=np.where(c>df['MA50'],1,-1);rsc+=np.where(c>df['MA20'],.5,-.5)
    rsc+=np.where(df['MA50']>df['MA50'].shift(10),1,-1);rsc+=np.where(df['ST_Direction']==1,1,-1);rsc+=np.where(df['Plus_DI']>df['Minus_DI'],.5,-.5);rsc+=np.where(df['MACD_Line']>0,.5,-.5)
    rr_=rsc.rolling(5,min_periods=3).mean();df['Regime_Score']=rr_.clip(-8,8);df['Regime']=np.select([rr_>=4,rr_>=1.5,rr_<=-4,rr_<=-1.5],[2,1,-2,-1],default=0)
    df['HMA'],df['HMA_Rising'],df['Hull_Turn_Bull_Raw'],df['Hull_Turn_Bear_Raw']=compute_hull_ma(c,20)
    df['UTBot_Stop'],df['UTBot_Dir'],df['UTBot_Buy_Raw'],df['UTBot_Sell_Raw']=compute_ut_bot(c,h,l,df['ATR'],1)
    df['SlowK'],df['SlowD']=compute_stochastic_slow(h,l,c)
    sqe=compute_squeeze_mom_enh(c,h,l,df['BB_Up'],df['BB_Low'],df['KC_Upper'],df['KC_Lower'],df['KC_Mid'])
    df['Squeeze_On']=sqe['squeeze_on'];df['Squeeze_Momentum']=sqe['momentum'];df['Squeeze_Mom_Rising']=sqe['mom_rising'];df['Squeeze_Mom_Positive']=sqe['mom_positive']
    df['Squeeze_Mom_Cross_Up_Raw']=sqe['mom_cross_up'];df['Squeeze_Mom_Cross_Down_Raw']=sqe['mom_cross_down']
    return df

print("✅ Part 1/4 완료")

# ══════════════════════════════════════════════════════════════
#  CipherX V14.2 — PART 2/4
#  시그널 탐지 + Combined Scan + 5-Committee + 판단이유 생성
# ══════════════════════════════════════════════════════════════

# ━━━ 시그널 탐지 함수 ━━━
def det_123pb(h,l,c,adx,pdi,mdi):
    sb=(adx>30)&(pdi>mdi);sbe=(adx>30)&(mdi>pdi);ins=(h<h.shift(1))&(l>l.shift(1))
    l1,l2,l3=l<l.shift(1),l.shift(1)<l.shift(2),l.shift(2)<l.shift(3);tl=l1&l2&l3;tli=(l1&l2&ins.shift(2))|(l1&ins.shift(1)&l2.shift(1))|(ins&l1&l2)
    h1,h2,h3=h>h.shift(1),h.shift(1)>h.shift(2),h.shift(2)>h.shift(3);th=h1&h2&h3;thi=(h1&h2&ins.shift(2))|(h1&ins.shift(1)&h2.shift(1))|(ins&h1&h2)
    return sb&(tl|tli),sbe&(th|thi)
def det_180(c,o,h,l,m10,m50):dr=h-l+1e-10;cp=(c-l)/dr;pp=(c.shift(1)-l.shift(1))/(h.shift(1)-l.shift(1)+1e-10);return (pp<=.25)&(cp>=.75)&(c>m10)&(c>m50),(pp>=.75)&(cp<=.25)&(c<m10)&(c<m50)
def det_boomer(h,l,adx,pdi,mdi):ins=(h<h.shift(1))&(l>l.shift(1));in2=ins&ins.shift(1);return in2.shift(1).fillna(False)&(adx>30)&(pdi>mdi),in2.shift(1).fillna(False)&(adx>30)&(mdi>pdi)
def det_expansion(h,l,c):dr=h-l;mr=dr.rolling(9).max();h60=h.rolling(60,min_periods=40).max();l60=l.rolling(60,min_periods=40).min();return (h>=h60)&(dr>=mr),(l<=l60)&(dr>=mr)
def det_exp_pivot(c,o,h,l,m50,atr):dr=h-l;mr=dr.rolling(9).max();bn=((c.shift(1)-m50.shift(1)).abs()<atr.shift(1))|((l<=m50)&(c>m50));sn=((c.shift(1)-m50.shift(1)).abs()<atr.shift(1))|((h>=m50)&(c<m50));return (dr>=mr)&bn&(c>m50)&(c>o),(dr>=mr)&sn&(c<m50)&(c<o)
def det_exp_dbl(c,o,h,l):dr=h-l;r=dr.rolling(10).rank(pct=True);h60=h.rolling(60,min_periods=40).max();return (h.shift(1)>=h60.shift(1))&(r.shift(1)>=.7)&(c<o)&(r>=.7)
def det_gilligans(o,c,h,l):dr=h-l+1e-10;cp=(c-l)/dr;l60=l.rolling(60,min_periods=40).min();h60=h.rolling(60,min_periods=40).max();return (o<=l60)&(o<l.shift(1))&(cp>=.5)&(c>=o),(o>=h60)&(o>h.shift(1))&(cp<=.5)&(c<=o)
def det_lizard(o,c,h,l):dr=h-l+1e-10;cp=(c-l)/dr;op=(o-l)/dr;return (cp>=.75)&(op>=.75)&(l<=l.rolling(10).min()),(cp<=.25)&(op<=.25)&(h>=h.rolling(10).max())
def det_slingshot(c,o,h,l,atr):t=atr*.3;h60=h.rolling(60,min_periods=40).max();l60=l.rolling(60,min_periods=40).min();return (h.shift(1)>=h60.shift(1))&(l<l.shift(1)-t),(l.shift(1)<=l60.shift(1))&(h>h.shift(1)+t)
def det_jack(h,l,c,df):ins=(h<h.shift(1))&(l>l.shift(1));xb=df.get('Expansion_BO',pd.Series(False,index=df.index)).fillna(False);xd=df.get('Expansion_BD',pd.Series(False,index=df.index)).fillna(False);return xb.shift(2).fillna(False)&ins.shift(1).fillna(False)&(c>h.shift(2)),xd.shift(2).fillna(False)&ins.shift(1).fillna(False)&(c<l.shift(2))
def det_nonadx(h,l,c,m50):ins=(h<h.shift(1))&(l>l.shift(1));l1,l2=l<l.shift(1),l.shift(1)<l.shift(2);tl=l1&l2&(l.shift(2)<l.shift(3));tli=(l1&l2&ins.shift(2))|(l1&ins.shift(1)&l2.shift(1))|(ins&l1&l2);h1,h2=h>h.shift(1),h.shift(1)>h.shift(2);th=h1&h2&(h.shift(2)>h.shift(3));thi=(h1&h2&ins.shift(2))|(h1&ins.shift(1)&h2.shift(1))|(ins&h1&h2);return (c>m50)&(tl|tli),(c<m50)&(th|thi)
def det_rev_hl(c,o,h,l):dr=h-l;mr=dr.rolling(5).max();h60=h.rolling(60,min_periods=40).max();l60=l.rolling(60,min_periods=40).min();out=(h>h.shift(1))&(l<l.shift(1));return (h>=h60)&out&(dr>=mr)&(c>o),(l<=l60)&out&(dr>=mr)&(c<o)
def det_ma_sr(c,o,h,l,ma,atr):md=(c-ma).abs()/(atr+1e-10);nr=md<.2;return nr&(c>ma)&(l<=ma*1.01)&(c>o),nr&(c<ma)&(h>=ma*.99)&(c<o)
def det_candles(c,o,h,l,wt1,atr,v):
    body=(c-o).abs();us=h-pd.concat([c,o],axis=1).max(axis=1);ls_=pd.concat([c,o],axis=1).min(axis=1)-l;fr=h-l+1e-10;ab=body.rolling(20).mean();sm=body<ab*.6;mr=atr*.5;vk=v>=v.rolling(10,min_periods=5).mean()*.5;vs_=v>v.rolling(10,min_periods=5).mean()*1.2
    ham=(ls_>=body*2)&(us<=body*.3)&sm&(wt1<-20)&(c>=o)&(fr>mr)&vk;sho=(us>=body*2)&(ls_<=body*.3)&sm&(wt1>20)&(c<=o)&(fr>mr)&vk
    doji=(body<=fr*.05)&(fr>atr*.3);db=doji&(wt1<-30)&(wt1>wt1.shift(1))&vk;dbe=doji&(wt1>30)&(wt1<wt1.shift(1))&vk
    d1b=(c.shift(2)<o.shift(2))&(body.shift(2)>ab.shift(2));d2s=body.shift(1)<ab.shift(1)*.5;d3u=(c>o)&(c>(o.shift(2)+c.shift(2))/2)&(body>ab*.8);ms_=d1b&d2s&d3u&(wt1<-15)&vs_
    d1u=(c.shift(2)>o.shift(2))&(body.shift(2)>ab.shift(2));d3d=(c<o)&(c<(o.shift(2)+c.shift(2))/2)&(body>ab*.8);es_=d1u&d2s&d3d&(wt1>15)&vs_
    return {'Hammer':ham,'Shooting_Star':sho,'Doji':doji,'Doji_Bullish':db,'Doji_Bearish':dbe,'Morning_Star':ms_,'Evening_Star':es_,'Spinning_Top':sm&(us>body*.5)&(ls_>body*.5)}
def det_engulf(c,o,wt1,m50,v):
    body=(c-o).abs();pb=(c.shift(1)-o.shift(1)).abs();ab=body.rolling(20).mean();big=(body>ab*.8)&(body>pb)
    ph=pd.concat([c.shift(1),o.shift(1)],axis=1).max(axis=1);pl=pd.concat([c.shift(1),o.shift(1)],axis=1).min(axis=1)
    ch=pd.concat([c,o],axis=1).max(axis=1);cl_=pd.concat([c,o],axis=1).min(axis=1)
    vi=v>v.shift(1)*1.1;vk=v>=v.rolling(10,min_periods=5).mean()*.5;vo=vi|vk
    return (c.shift(1)<o.shift(1))&(c>o)&(cl_<=pl)&(ch>=ph)&big&(wt1<-10)&vo,(c.shift(1)>o.shift(1))&(c<o)&(cl_<=pl)&(ch>=ph)&big&(wt1>10)&vo
def det_bb(c,o,h,l,bbu,bbl,bbw,kcu,kcl):
    ss_bb=(bbu<kcu)&(bbl>kcl);se=~ss_bb&ss_bb.shift(1).fillna(False);seb=se&(c>c.shift(1))&(c>o);ses=se&(c<c.shift(1))&(c<o)
    ut=h>=bbu;lt=l<=bbl;ub=c>bbu;lb_=(c<bbl)&(c<o);lbo=(c<bbl)&(c>o)&(c>c.shift(1));uw=ut.rolling(3).sum()>=3;lw=lt.rolling(3).sum()>=3
    wd=bbw.rolling(126,min_periods=60).rank(pct=True)>=.9;tight=bbw<=bbw.rolling(126,min_periods=60).min()*1.05
    return {'BB_Squeeze':tight,'BB_Squeeze_Started':ss_bb&~ss_bb.shift(1).fillna(False),'BB_Squeeze_End_Bull':seb,'BB_Squeeze_End_Bear':ses,'BB_Upper_Touch':ut&~ub,'BB_Lower_Touch':lt&~lb_,'BB_Upper_Break':ub,'BB_Lower_Break':lb_,'BB_Lower_Bounce':lbo,'BB_Upper_Walk':uw,'BB_Lower_Walk':lw,'BB_Wide_Bands':wd}

# ━━━ detect_all_signals ━━━
def detect_all_signals(df):
    H,L,C,O,V=df['High'],df['Low'],df['Close'],df['Open'],df['Volume']
    e8,e21=df['EMA8'],df['EMA21'];m10,m20,m50,m200=df['MA10'],df['MA20'],df['MA50'],df['MA200']
    wt1,wt2,atr=df['WT1'],df['WT2'],df['ATR'];adx,pdi,mdi=df['ADX'],df['Plus_DI'],df['Minus_DI']
    idx=df.index;vok=_volf(V,.5);avg_vol=V.rolling(50,min_periods=10).mean();vol_ratio=V/(avg_vol+1e-10)
    wur=_recent(df['WT_Up'],2);wdr=_recent(df['WT_Down'],2);htf=(e8>e21)&(e21>e21.shift(5))&(C>m50)&(m50>m50.shift(10))
    # MCB+
    df['Green_Dot_T1']=wur&(wt1<=OS1)&(df['RSI']<30)&(df['MFI']<30)&vok;df['Green_Dot_T2']=wur&(wt1<=OS1)&((df['RSI']<32)|(df['MFI']<32))&~df['Green_Dot_T1']&vok
    df['Red_Dot_T1']=wdr&(wt1>=OB1)&(df['RSI']>70)&(df['MFI']>70)&vok;df['Red_Dot_T2']=wdr&(wt1>=OB1)&((df['RSI']>68)|(df['MFI']>68))&~df['Red_Dot_T1']&vok
    df['Blue_Diamond']=(wt2<=0)&wur&htf&vok;df['Red_Diamond']=(wt2>=0)&wdr&~htf&vok
    df['Green_Circle']=wur&(wt1<=OS1)&~df['Green_Dot_T1']&~df['Green_Dot_T2']&vok&(df['RSI']<45)
    df['Red_Circle']=wdr&(wt1>=OB1)&~df['Red_Dot_T1']&~df['Red_Dot_T2']&vok&(df['RSI']>55)
    bd,brd,hb,hbr=detect_pivot_div(C,wt1,60,5,OS1,OB1,atr=atr);rbd,rbrd,_,_=detect_pivot_div(C,df['RSI'],60,5,35,65,atr=atr);obd,obrd,_,_=detect_pivot_div(C,df['OBV'],60,5,atr=atr)
    df['Gold_Dot']=df['Green_Dot_T1']&(wt1<=OS2)&_recent(bd,3);df['Blood_Diamond']=df['Red_Dot_T1']&(wt1>=OB2)&_recent(brd,3)
    df['Bull_Divergence']=bd&~df['Gold_Dot']&vok;df['Bear_Divergence']=brd&~df['Blood_Diamond']&vok
    df['RSI_Bull_Divergence']=rbd&(wt1<-20)&vok;df['RSI_Bear_Divergence']=rbrd&(wt1>20)&vok
    df['Hidden_Bull_Div']=hb&(wt1<-25)&htf&vok;df['Hidden_Bear_Div']=hbr&(wt1>25)&~htf&vok
    df['OBV_Div_Buy']=obd&(wt1<-30);df['OBV_Div_Sell']=obrd&(wt1>30)
    # Cooper
    df['Pullback_123_Bull'],df['Pullback_123_Bear']=det_123pb(H,L,C,adx,pdi,mdi);df['Setup_180_Bull'],df['Setup_180_Bear']=det_180(C,O,H,L,m10,m50)
    df['Boomer_Buy'],df['Boomer_Sell']=det_boomer(H,L,adx,pdi,mdi);df['Expansion_BO'],df['Expansion_BD']=det_expansion(H,L,C)
    df['Expansion_Pivot_Buy'],df['Expansion_Pivot_Sell']=det_exp_pivot(C,O,H,L,m50,atr);df['Expansion_Double_Sticks']=det_exp_dbl(C,O,H,L)
    df['Gilligans_Buy'],df['Gilligans_Sell']=det_gilligans(O,C,H,L);df['Lizard_Bull'],df['Lizard_Bear']=det_lizard(O,C,H,L)
    df['Slingshot_Bull'],df['Slingshot_Bear']=det_slingshot(C,O,H,L,atr);df['Jack_In_Box_Bull'],df['Jack_In_Box_Bear']=det_jack(H,L,C,df)
    df['NonADX_123_Bull'],df['NonADX_123_Bear']=det_nonadx(H,L,C,m50);df['Reversal_New_Highs'],df['Reversal_New_Lows']=det_rev_hl(C,O,H,L)
    # MA
    df['MA20_Support'],df['MA20_Resistance']=det_ma_sr(C,O,H,L,m20,atr);df['MA50_Support'],df['MA50_Resistance']=det_ma_sr(C,O,H,L,m50,atr);df['MA200_Support'],df['MA200_Resistance']=det_ma_sr(C,O,H,L,m200,atr)
    for tag,ma in [('20MA',m20),('50MA',m50),('200MA',m200)]:df[f'Cross_Above_{tag}']=(C>ma)&(C.shift(1)<=ma.shift(1));df[f'Fell_Below_{tag}']=(C<ma)&(C.shift(1)>=ma.shift(1))
    gc=(m50>m200)&(m50.shift(1)<=m200.shift(1));df['Golden_Cross']=gc&(adx>15);dc_=(m50<m200)&(m50.shift(1)>=m200.shift(1));df['Death_Cross']=dc_&(adx>15)
    df['MTF_All_Bullish']=(C>m10)&(C>m50)&(C>m200);df['MTF_All_Bearish']=(C<m10)&(C<m50)&(C<m200)
    # BB+캔들
    for k,v_ in det_bb(C,O,H,L,df['BB_Up'],df['BB_Low'],df['BB_Width'],df['KC_Upper'],df['KC_Lower']).items():df[k]=v_
    for k,v_ in det_candles(C,O,H,L,wt1,atr,V).items():df[k]=v_
    df['Bullish_Engulfing'],df['Bearish_Engulfing']=det_engulf(C,O,wt1,m50,V)
    ins=(H<H.shift(1))&(L>L.shift(1));out=(H>H.shift(1))&(L<L.shift(1))
    df['Inside_Day']=ins;df['Outside_Bullish']=out&(C>O)&(C>H.shift(1))&vok;df['Outside_Bearish']=out&(C<O)&(C<L.shift(1))&vok
    # MACD/Stoch/ADX/RSI
    ml,ms_=df['MACD_Line'],df['MACD_Signal'];df['MACD_Cross_Buy']=((ml>ms_)&(ml.shift(1)<=ms_.shift(1))&(ml<0))&vok;df['MACD_Cross_Sell']=((ml<ms_)&(ml.shift(1)>=ms_.shift(1))&(ml>0))&vok
    df['MACD_Zero_Cross_Buy']=(ml>0)&(ml.shift(1)<=0);df['MACD_Zero_Cross_Sell']=(ml<0)&(ml.shift(1)>=0)
    stk,std_=df['StochK'],df['StochD'];df['StochRSI_Cross_Buy']=(stk>std_)&(stk.shift(1)<=std_.shift(1))&(stk<25);df['StochRSI_Cross_Sell']=(stk<std_)&(stk.shift(1)>=std_.shift(1))&(stk>75)
    df['Stoch_Reached_OB']=(stk>=80)&(stk.shift(1)<80);df['Stoch_Reached_OS']=(stk<=20)&(stk.shift(1)>20);df['Stoch_Overbought']=(stk>80)&(std_>80);df['Stoch_Oversold']=(stk<20)&(std_<20)
    df['DMI_Cross_Bull']=((pdi>mdi)&(pdi.shift(1)<=mdi.shift(1)))&vok;df['DMI_Cross_Bear']=((mdi>pdi)&(mdi.shift(1)<=pdi.shift(1)))&vok
    df['ADX_New_Uptrend']=(adx>25)&(adx.shift(1)<=25)&(pdi>mdi)&vok;df['ADX_New_Downtrend']=(adx>25)&(adx.shift(1)<=25)&(mdi>pdi)&vok
    df['ADX_Momentum_Buy']=(adx>20)&(adx.shift(1)<=20)&(pdi>mdi)&vok;df['ADX_Momentum_Sell']=(adx>20)&(adx.shift(1)<=20)&(mdi>pdi)&vok
    rsi=df['RSI'];df['RSI_Cross_30_Up']=(rsi>30)&(rsi.shift(1)<=30);df['RSI_Cross_50_Up']=(rsi>50)&(rsi.shift(1)<=50);df['RSI_Cross_70_Down']=(rsi<70)&(rsi.shift(1)>=70);df['RSI_Cross_50_Down']=(rsi<50)&(rsi.shift(1)>=50)
    # 갭/범위/52주/연속
    t=atr*.5;gu=(O>H.shift(1))&((O-H.shift(1))>t);gd=(O<L.shift(1))&((L.shift(1)-O)>t);df['Gap_Up']=gu;df['Gap_Down']=gd;df['Gap_Up_Closed']=gu.shift(1).fillna(False)&(L<=H.shift(2));df['Gap_Down_Closed']=gd.shift(1).fillna(False)&(H>=L.shift(2))
    dr=H-L;nr7m=dr.rolling(7).min();nr7=dr<=nr7m;df['NR7']=nr7;df['NR7_2']=nr7&nr7.shift(1).fillna(False);df['Narrow_Range_Bar']=dr<atr*.5;df['Wide_Range_Bar']=dr>atr*2
    df['Calm_After_Storm']=(dr>atr*2).rolling(5,min_periods=1).max().shift(1).fillna(False).astype(bool)&(dr<atr*.5)
    h252=H.rolling(252,min_periods=200).max().shift(1);l252=L.rolling(252,min_periods=200).min().shift(1);df['New_52W_High']=H>h252;df['New_52W_Low']=L<l252
    c252h=C.rolling(252,min_periods=200).max().shift(1);c252l=C.rolling(252,min_periods=200).min().shift(1);df['New_52W_Closing_High']=C>c252h;df['New_52W_Closing_Low']=C<c252l
    up_=C>C.shift(1);dn_=C<C.shift(1);us__=_vs(up_);ds__=_vs(dn_);df['Up_3_Days']=us__>=3;df['Up_4_Days']=us__>=4;df['Up_5_Days']=us__>=5;df['Down_3_Days']=ds__>=3;df['Down_4_Days']=ds__>=4;df['Down_5_Days']=ds__>=5
    # 기타
    n10=(C/10).round()*10;dist=(C-n10).abs();nrd=dist<atr*.5;df['Multiple_Ten_Bull']=nrd&(C.shift(1)<n10)&(C>n10)&(C>O);df['Multiple_Ten_Bear']=nrd&(C.shift(1)>n10)&(C<n10)&(C<O)
    dv_=V.where(C<C.shift(1),0);df['Pocket_Pivot']=(C>O)&(V>dv_.rolling(10).max())&(C>m50)&(C>C.shift(1));df['Parabolic_Rise']=(C-C.shift(10))/(C.shift(10)+1e-10)>.3
    df['Three_Weeks_Tight']=((C.rolling(15).max()-C.rolling(15).min())/(C.rolling(15).min()+1e-10))<.015
    vz=(V-avg_vol)/(V.rolling(20).std()+1e-10);df['Volume_Surge']=vol_ratio>=3;big=(C-O).abs()>atr*.5;ps=(vz.shift(1)>2.5)&big.shift(1)
    df['Volume_Climax_Buy']=ps&(C.shift(1)<O.shift(1))&(wt1.shift(1)<-40)&(C>O)&(C>(O+C.shift(1))/2);df['Volume_Climax_Sell']=ps&(C.shift(1)>O.shift(1))&(wt1.shift(1)>40)&(C<O)&(C<(O+C.shift(1))/2)
    mom=C-((H.rolling(20).max()+L.rolling(20).min())/2+df['KC_Mid'])/2;sf=~df['Squeeze_On']&df['Squeeze_On'].shift(1).fillna(False)
    df['Squeeze_Fire_Buy']=sf&(mom>0)&(mom>mom.shift(1))&vok;df['Squeeze_Fire_Sell']=sf&(mom<0)&(mom<mom.shift(1))&vok
    df['SuperTrend_Buy']=(df['ST_Direction']==1)&(df['ST_Direction'].shift(1)==-1);df['SuperTrend_Sell']=(df['ST_Direction']==-1)&(df['ST_Direction'].shift(1)==1)
    ar_=atr/(C+1e-10);vk2=_volf(V,.5);su_=e21>e21.shift(5);tu_=(e8>e21)&su_&(C>e8);tcu_=(L<=e8*(1+ar_*.15))&(L>=e21*(1-ar_*.25));bcu_=(C>=e8)&(C>H.shift(1))&(wt1>wt1.shift(1))&(wt1>wt2)&(wt1<60)
    df['EMA_Pullback_Buy']=tu_&_recent(tcu_,2)&bcu_&vk2
    sd__=e21<e21.shift(5);td_=(e8<e21)&sd__&(C<e8);tcd_=(H>=e8*(1-ar_*.15))&(H<=e21*(1+ar_*.25));bcd_=(C<=e8)&(C<L.shift(1))&(wt1<wt1.shift(1))&(wt1<wt2)&(wt1>-60)
    df['EMA_Pullback_Sell']=td_&_recent(tcd_,2)&bcd_&vk2
    body__=(C-O).abs();bb__=body__>atr*1.5;hv__=V>V.rolling(20).mean()*2;comp_=df['BB_Width'].shift(1)<df['BB_Width'].rolling(20).mean().shift(1)
    df['Momentum_Ignition_Buy']=(C>O)&bb__&hv__&(C>df['BB_Up'])&(e8>e21)&(wt1<50)&comp_;df['Momentum_Ignition_Sell']=(C<O)&bb__&hv__&(C<df['BB_Low'])&(e8<e21)&(wt1>-50)&comp_
    df['Parabolic_Bottom_Buy']=(((wt1<-80)&(wt1>wt1.shift(1))&(C>O))|((wt1<-70)&(wt1>wt1.shift(1))&(wt1>wt1.shift(2))&(C>O)&(C>C.shift(1)))|((C<df['BB_Low']-atr*1.5)&(C>O)))
    df['Parabolic_Top_Sell']=(((wt1>80)&(wt1<wt1.shift(1))&(C<O))|((wt1>70)&(wt1<wt1.shift(1))&(wt1<wt1.shift(2))&(C<O)&(C<C.shift(1)))|((C>df['BB_Up']+atr*1.5)&(C<O)))
    vk3=_volf(V,.7);df['VWAP_Bounce_Buy']=(df['VWAP_Osc']>0)&(df['VWAP_Osc'].shift(1)<-.5)&(wt1>wt2)&(wt1<30)&vk3;df['VWAP_Reject_Sell']=(df['VWAP_Osc']<0)&(df['VWAP_Osc'].shift(1)>.5)&(wt1<wt2)&(wt1>-30)&vk3
    tk_,kj_=df['Ichimoku_Tenkan'],df['Ichimoku_Kijun'];sa_,sb_=df['Ichimoku_SenkouA'],df['Ichimoku_SenkouB'];kt_=pd.concat([sa_,sb_],axis=1).max(axis=1);kb_=pd.concat([sa_,sb_],axis=1).min(axis=1)
    df['Kumo_Breakout_Bull']=(C>kt_)&(C.shift(1)<=kt_.shift(1))&(tk_>kj_)&vok;df['Kumo_Breakout_Bear']=(C<kb_)&(C.shift(1)>=kb_.shift(1))&(tk_<kj_)&vok
    df['TK_Cross_Bull']=(tk_>kj_)&(tk_.shift(1)<=kj_.shift(1))&(C>kt_)&vok;df['TK_Cross_Bear']=(tk_<kj_)&(tk_.shift(1)>=kj_.shift(1))&(C<kb_)&vok
    df['CMF_Bull']=(df['CMF']>.1)&(df['CMF'].shift(1)<=.1)&(C>m50)&vok;df['CMF_Bear']=(df['CMF']<-.1)&(df['CMF'].shift(1)>=-.1)&(C<m50)&vok
    rmfi=df['RSI_MFI'];mr__=rmfi>rmfi.shift(1);mf__=rmfi<rmfi.shift(1);df['MF_Cross_Bull']=((rmfi>0)&(rmfi.shift(1)<=0))&vok;df['MF_Cross_Bear']=((rmfi<0)&(rmfi.shift(1)>=0))&vok
    mus_=_vs(mr__);mds_=_vs(mf__);df['MF_Accel_Up']=(mus_>=5)&vok;df['MF_Accel_Dn']=(mds_>=5)&vok
    df['MF_Bull_Div']=(C<C.rolling(5).min().shift(1))&(rmfi>rmfi.rolling(5).min().shift(1))&(rmfi<0)&vok;df['MF_Bear_Div']=(C>C.rolling(5).max().shift(1))&(rmfi<rmfi.rolling(5).max().shift(1))&(rmfi>0)&vok
    if 'VP_POC' in df.columns:poc_=df['VP_POC'];df['Volume_POC_Breakout']=(C>poc_)&(C.shift(1)<=poc_.shift(1))&vok&(C>O);df['Volume_POC_Breakdown']=(C<poc_)&(C.shift(1)>=poc_.shift(1))&vok&(C<O)
    if 'VP_VAH' in df.columns:ap___=atr/(C+1e-10);df['VP_VAH_Resistance']=((df['VP_VAH']-C).abs()/(C+1e-10)<ap___*.5)&(C<O);df['VP_VAL_Support']=((C-df['VP_VAL']).abs()/(C+1e-10)<ap___*.5)&(C>O)
    rs_=df.get('RS_Ratio',pd.Series(1.,index=idx));rm_=rs_-rs_.shift(5);df['Relative_Strength_Buy']=(rs_>1.03)&(rm_>0.01)&(C>C.shift(1))&vok;df['Relative_Strength_Sell']=(rs_<.97)&(rm_<-0.01)&(C<C.shift(1))&vok
    df['Setup_Squeeze_Bull']=df.get('BB_Squeeze',pd.Series(False,index=idx)).fillna(False)&(df['MACD_Hist']<0)&(df['MACD_Hist']>df['MACD_Hist'].shift(1))&(wt1<30)
    df['Setup_Squeeze_Bear']=df.get('BB_Squeeze',pd.Series(False,index=idx)).fillna(False)&(df['MACD_Hist']>0)&(df['MACD_Hist']<df['MACD_Hist'].shift(1))&(wt1>-30)
    ca_=df.get('Composite_Accel',pd.Series(0,index=idx));df['Momentum_Accel_Buy']=(ca_>JT.ACCEL_MOD)&(wt1<40)&vok;df['Momentum_Accel_Sell']=(ca_<-JT.ACCEL_MOD)&(wt1>-40)&vok
    df['Volume_Dry_Up']=_vs(vol_ratio<.6)>=5
    cs__=df.get('WT_Conv_Speed',pd.Series(0,index=idx));ga__=df.get('WT_Gap_Abs',pd.Series(0,index=idx))
    df['WT_Convergence_Bull']=(cs__>3)&(ga__>2)&(ga__<15)&(wt1<wt2)&(wt1<20);df['WT_Convergence_Bear']=(cs__>3)&(ga__>2)&(ga__<15)&(wt1>wt2)&(wt1>-20)
    # ★ 신규 6종
    vds=_vs(vol_ratio<0.6);vd5=vds>=5;df['Volume_Dry_Breakout_Buy']=vd5.shift(1).fillna(False)&(C>O)&(vol_ratio>=2)&(C>H.shift(1));df['Volume_Dry_Breakout_Sell']=vd5.shift(1).fillna(False)&(C<O)&(vol_ratio>=2)&(C<L.shift(1))
    br_=(C-O).abs();rr_=H-L+1e-10;idj=br_<rr_*0.1;djs=_vs(idj);df['Doji_Breakout_Buy']=(djs.shift(1)>=2)&(C>O)&(br_>atr*0.5)&(C>H.shift(1));df['Doji_Breakout_Sell']=(djs.shift(1)>=2)&(C<O)&(br_>atr*0.5)&(C<L.shift(1))
    tdn=(C.shift(1)<C.shift(2))&(C.shift(2)<C.shift(3));df['Three_Bar_Reversal_Buy']=tdn&(C>O)&(br_>atr*0.8)&(vol_ratio>=1.5)&(wt1<-20)
    tup=(C.shift(1)>C.shift(2))&(C.shift(2)>C.shift(3));df['Three_Bar_Reversal_Sell']=tup&(C<O)&(br_>atr*0.8)&(vol_ratio>=1.5)&(wt1>20)

    # ═══ 쿨다운 ═══
    PAIRED={('MACD_Cross_Buy','MACD_Cross_Sell'):12,('Bullish_Engulfing','Bearish_Engulfing'):5,('Hammer','Shooting_Star'):5,('Morning_Star','Evening_Star'):7,('DMI_Cross_Bull','DMI_Cross_Bear'):10,('Pullback_123_Bull','Pullback_123_Bear'):7,('Expansion_BO','Expansion_BD'):10,('Gilligans_Buy','Gilligans_Sell'):10,('Slingshot_Bull','Slingshot_Bear'):7,('MF_Cross_Bull','MF_Cross_Bear'):10,('Kumo_Breakout_Bull','Kumo_Breakout_Bear'):10,('StochRSI_Cross_Buy','StochRSI_Cross_Sell'):7,('ADX_Momentum_Buy','ADX_Momentum_Sell'):10,('EMA_Pullback_Buy','EMA_Pullback_Sell'):7,('SuperTrend_Buy','SuperTrend_Sell'):10,('Boomer_Buy','Boomer_Sell'):10,('Setup_180_Bull','Setup_180_Bear'):7,('VWAP_Bounce_Buy','VWAP_Reject_Sell'):7,('Momentum_Ignition_Buy','Momentum_Ignition_Sell'):10,('Volume_Dry_Breakout_Buy','Volume_Dry_Breakout_Sell'):7,('Doji_Breakout_Buy','Doji_Breakout_Sell'):5,('Three_Bar_Reversal_Buy','Three_Bar_Reversal_Sell'):5}
    ph__=set()
    for (bs,ss),cd in PAIRED.items():_cd_dir(df,bs,ss,cd);ph__.add(bs);ph__.add(ss)
    for s,cd in COOLDOWN_MAP.items():
        if s in df.columns and s not in ph__:df[s]=_cooldown(df[s],cd)
    # 보조지표
    df['UTBot_Buy']=df.get('UTBot_Buy_Raw',pd.Series(False,index=idx)).fillna(False)&vok;df['UTBot_Sell']=df.get('UTBot_Sell_Raw',pd.Series(False,index=idx)).fillna(False)&vok
    hma_r=df.get('HMA_Rising',pd.Series(False,index=idx)).fillna(False);hma_r_v=hma_r.values
    df['Hull_Turn_Bull']=df.get('Hull_Turn_Bull_Raw',pd.Series(False,index=idx)).fillna(False)&(wt1>wt1.shift(1))&vok;df['Hull_Turn_Bear']=df.get('Hull_Turn_Bear_Raw',pd.Series(False,index=idx)).fillna(False)&(wt1<wt1.shift(1))&vok
    slk,sld=df.get('SlowK',pd.Series(50,index=idx)),df.get('SlowD',pd.Series(50,index=idx));df['StochSlow_Cross_Buy']=(slk>sld)&(slk.shift(1)<=sld.shift(1))&(slk<20);df['StochSlow_Cross_Sell']=(slk<sld)&(slk.shift(1)>=sld.shift(1))&(slk>80)
    df['Squeeze_Mom_Cross_Up']=df.get('Squeeze_Mom_Cross_Up_Raw',pd.Series(False,index=idx)).fillna(False)&vok;df['Squeeze_Mom_Cross_Down']=df.get('Squeeze_Mom_Cross_Down_Raw',pd.Series(False,index=idx)).fillna(False)&vok
    hrb=_recent(df.get('Hull_Turn_Bull_Raw',pd.Series(False,index=idx)).fillna(False),3);hrbe=_recent(df.get('Hull_Turn_Bear_Raw',pd.Series(False,index=idx)).fillna(False),3)
    df['VuManChu_Bull']=((wt1<-30)&(hrb|hma_r)&(df['Bull_Divergence'].fillna(False)|df['RSI_Bull_Divergence'].fillna(False)|df['Bullish_Engulfing'].fillna(False)|df['Hammer'].fillna(False)|df['Morning_Star'].fillna(False)))&vok
    df['VuManChu_Bear']=((wt1>30)&(hrbe|~hma_r)&(df['Bear_Divergence'].fillna(False)|df['RSI_Bear_Divergence'].fillna(False)|df['Bearish_Engulfing'].fillna(False)|df['Shooting_Star'].fillna(False)|df['Evening_Star'].fillna(False)))&vok
    for (bs,ss),cd in {('UTBot_Buy','UTBot_Sell'):10,('Hull_Turn_Bull','Hull_Turn_Bear'):7,('StochSlow_Cross_Buy','StochSlow_Cross_Sell'):7,('Squeeze_Mom_Cross_Up','Squeeze_Mom_Cross_Down'):5,('VuManChu_Bull','VuManChu_Bear'):10}.items():_cd_dir(df,bs,ss,cd)
    df=detect_combined_scans(df,vol_ratio,hma_r);df=compute_10layer_scores(df,vol_ratio,hma_r_v);df=compute_committee_ensemble(df,vol_ratio,hma_r_v)
    return df

# ━━━ Combined Scan (동일) ━━━
def detect_combined_scans(df,vol_ratio,hma_rising):
    idx=df.index;C,O,H,L,V=df['Close'],df['Open'],df['High'],df['Low'],df['Volume']
    F=lambda c:df.get(c,pd.Series(False,index=idx)).fillna(False);N=lambda c,d=0:df.get(c,pd.Series(d,index=idx)).fillna(d)
    vr=vol_ratio;up_=(C>N('MA50'))&(N('MA50')>N('MA200'))&(N('Plus_DI')>N('Minus_DI'));dn_=(C<N('MA50'))&(N('MA50')<N('MA200'))&(N('Minus_DI')>N('Plus_DI'))
    adx_ok=N('ADX')>20;vs_=vr>=2;vok_=vr>=1
    bc_=F('Bullish_Engulfing')|F('Morning_Star')|F('Hammer')|F('Doji_Bullish');sc__=F('Bearish_Engulfing')|F('Evening_Star')|F('Shooting_Star')|F('Doji_Bearish')
    cb_=F('Pullback_123_Bull')|F('NonADX_123_Bull')|F('Setup_180_Bull')|F('Boomer_Buy')|F('Expansion_BO')|F('Gilligans_Buy')|F('Lizard_Bull')
    cs___=F('Pullback_123_Bear')|F('NonADX_123_Bear')|F('Setup_180_Bear')|F('Boomer_Sell')|F('Expansion_BD')|F('Gilligans_Sell')|F('Lizard_Bear')
    mfb_=(N('RSI_MFI')>N('RSI_MFI').shift(1))|(N('CMF')>.05)|F('MF_Cross_Bull');mfs_=(N('RSI_MFI')<N('RSI_MFI').shift(1))|(N('CMF')<-.05)|F('MF_Cross_Bear')
    n_bl=C<=N('BB_Low')*1.01;n_bu=C>=N('BB_Up')*.99;n_vp=((C-N('VP_VAL')).abs()/(C+1e-10)<.02)&(N('VP_VAL')>0);n_vr=((N('VP_VAH')-C).abs()/(C+1e-10)<.02)&(N('VP_VAH')>0)
    n50=((C-N('MA50')).abs()/(C+1e-10))<.03;wos_=N('WT1')<-53;wob_=N('WT1')>53;sos_=(N('StochK')<20)&(N('StochD')<20);sob_=(N('StochK')>80)&(N('StochD')>80)
    dbc_=F('Bull_Divergence').astype(int)+F('RSI_Bull_Divergence').astype(int)+F('MF_Bull_Div').astype(int)+F('OBV_Div_Buy').astype(int)
    dsc_=F('Bear_Divergence').astype(int)+F('RSI_Bear_Divergence').astype(int)+F('MF_Bear_Div').astype(int)+F('OBV_Div_Sell').astype(int)
    mr_=N('MACD_Hist')>N('MACD_Hist').shift(1);mf_=N('MACD_Hist')<N('MACD_Hist').shift(1);wr_=N('WT1')>N('WT1').shift(1);wf_=N('WT1')<N('WT1').shift(1)
    llw_=(pd.concat([C,O],axis=1).min(axis=1)-L)>(H-L)*.6;luw_=(H-pd.concat([C,O],axis=1).max(axis=1))>(H-L)*.6
    ub_=(up_|(C>N('MA50'))).astype(int)+((wr_|F('WT_Up'))&(mr_|(N('MACD_Hist')>0))).astype(int)+(bc_|cb_).astype(int)+vok_.astype(int)+mfb_.astype(int)+(n50|F('BB_Squeeze_End_Bull')|n_vp).astype(int);df['CS_Ultimate_Buy']=ub_>=6
    tos_=(wos_|(N('WT1')<-60))&((N('RSI')<30)|(N('RSI')<35))&sos_;df['CS_Triple_Oversold_Reversal']=tos_&(F('WT_Up')|wr_|bc_|llw_|F('Gold_Dot')|F('Green_Dot_T1'))&vok_
    df['CS_Breakout_Momentum_Buy']=(F('New_52W_High')|F('Expansion_BO')|(C>N('BB_Up')))&adx_ok&(N('Plus_DI')>N('Minus_DI'))&vs_&mr_
    df['CS_Institutional_Accumulation']=(F('Pocket_Pivot')|(F('NR7')&(N('OBV')>N('OBV').shift(5)))|(F('Calm_After_Storm')&(C>O)))&(C>N('MA50'))&(N('CMF')>.05)&(N('OBV')>N('OBV').shift(5))
    df['CS_Divergence_Confluence_Buy']=(dbc_>=2)&(n_bl|n_vp|n50)&(bc_|llw_|F('WT_Up'))&vok_
    el_=F('New_52W_Low')|(C<=C.rolling(252,min_periods=200).min()*1.02);eos_=(N('WT1')<-80)|(wos_&(N('RSI')<25));df['CS_Capitulation_Bottom']=el_&eos_&(vr>=3)&(llw_|F('Hammer')|F('Parabolic_Bottom_Buy'))&(N('MFI')<30)
    df['CS_Triple_Confirm_Buy']=F('UTBot_Buy')&hma_rising&(N('WT1')>N('WT2'))&vok_;df['CS_VuManChu_Squeeze_Buy']=F('VuManChu_Bull')&(F('Squeeze_Fire_Buy')|F('Squeeze_Mom_Cross_Up'))
    us__=(dn_|(C<N('MA50'))).astype(int)+((wf_|F('WT_Down'))&(mf_|(N('MACD_Hist')<0))).astype(int)+(sc__|cs___).astype(int)+vok_.astype(int)+mfs_.astype(int)+(n50|F('BB_Squeeze_End_Bear')|n_vr).astype(int);df['CS_Ultimate_Sell']=us__>=6
    tob_=(wob_|(N('WT1')>60))&((N('RSI')>70)|(N('RSI')>65))&sob_;df['CS_Triple_Overbought_Exhaustion']=tob_&(F('WT_Down')|wf_|sc__|luw_|F('Blood_Diamond')|F('Red_Dot_T1'))&vok_
    df['CS_Breakdown_Momentum_Sell']=(F('New_52W_Low')|F('Expansion_BD')|(C<N('BB_Low')))&adx_ok&(N('Minus_DI')>N('Plus_DI'))&vs_&mf_
    para_=(C>C.shift(10)*1.3)|F('Parabolic_Top_Sell');eob_=(N('WT1')>80)|(wob_&(N('RSI')>75));df['CS_Parabolic_Exhaustion_Sell']=para_&eob_&(luw_|F('Shooting_Star')|sc__)&(vr>=3)
    df['CS_Divergence_Confluence_Sell']=(dsc_>=2)&(n_bu|n_vr|n50)&(sc__|luw_|F('WT_Down'))&vok_
    eh_=F('New_52W_High')|(C>=C.rolling(252,min_periods=200).max()*.98);df['CS_Blow_Off_Top']=eh_&eob_&(vr>=3)&(luw_|F('Shooting_Star')|F('Parabolic_Top_Sell'))&(N('MFI')>70)
    df['CS_Triple_Confirm_Sell']=F('UTBot_Sell')&~hma_rising&(N('WT1')<N('WT2'))&vok_;df['CS_VuManChu_Squeeze_Sell']=F('VuManChu_Bear')&(F('Squeeze_Fire_Sell')|F('Squeeze_Mom_Cross_Down'))
    df['CS_Trend_Pullback_Buy']=up_&(n50|(L<=N('MA20'))&(C>N('MA20')))&(bc_|(C>O))&mfb_;df['CS_Squeeze_Breakout_Buy']=(F('BB_Squeeze_End_Bull')|(F('BB_Squeeze').shift(1)&(C>N('BB_Mid'))&(C>O)))&vok_&mr_
    df['CS_MA_Confluence_Buy']=((N('MA50')>N('MA200'))&(N('MA50')>N('MA50').shift(5)))&(F('MACD_Cross_Buy')|mr_)&vok_&(C>N('MA50'));df['CS_Cooper_Setup_Buy']=cb_&adx_ok&(N('Plus_DI')>N('Minus_DI'))&vok_&(C>N('MA50'))
    df['CS_Volume_Climax_Rev_Buy']=(F('Volume_Climax_Buy')|(vr>=2.5))&(wos_|sos_)&(bc_|llw_)&(n_bl|n_vp);df['CS_Ichimoku_Breakout_Buy']=F('Kumo_Breakout_Bull')&(F('TK_Cross_Bull')|adx_ok)&vok_
    df['CS_Trend_Rejection_Sell']=dn_&(n50|(H>=N('MA20'))&(C<N('MA20')))&(sc__|(C<O))&mfs_;df['CS_Squeeze_Breakdown_Sell']=(F('BB_Squeeze_End_Bear')|(F('BB_Squeeze').shift(1)&(C<N('BB_Mid'))&(C<O)))&vok_&mf_
    df['CS_MA_Breakdown_Sell']=((N('MA50')<N('MA200'))&(N('MA50')<N('MA50').shift(5)))&(F('MACD_Cross_Sell')|mf_)&vok_&(C<N('MA50'));df['CS_Cooper_Setup_Sell']=cs___&adx_ok&(N('Minus_DI')>N('Plus_DI'))&vok_&(C<N('MA50'))
    df['CS_Gap_Failure_Sell']=(F('Gap_Up').shift(1).fillna(False)&sc__&vok_&wf_)|(F('Gap_Up')&(C<O)&vok_)
    df['CS_Oversold_Bounce_Buy']=sos_&bc_&(n50|n_bl);df['CS_Momentum_Accel_Buy']=(N('Composite_Accel',0)>1.5)&vok_&(C>N('MA50'));df['CS_Structure_Support_Buy']=n_vp&n_bl&(C>O)
    df['CS_Overbought_Fade_Sell']=sob_&sc__&(n50|n_bu);df['CS_Volatility_Explosion']=(F('NR7_2').astype(int)+F('BB_Squeeze').astype(int)+(vr<.5).astype(int)+F('Inside_Day').astype(int))>=3
    for sn,cfg in COMBINED_SCAN_REGISTRY.items():
        if sn in df.columns:df[sn]=_cooldown(df[sn],bars={1:5,2:7,3:10}.get(cfg.get('tier',2),7))
    return df

# ━━━ 10-Layer Scores (시각화용, 코드 생략 — V14.1과 100% 동일) ━━━
# compute_10layer_scores 는 V14.1 Part 2/4와 완전히 동일하므로 그대로 사용
# 여기서는 지면 절약을 위해 함수 시그니처만 표시

def compute_10layer_scores(df, vol_ratio, hma_r_v):
    """10-Layer — V14.1과 동일 (시각화 참고용)"""
    C,O,H,L=df['Close'],df['Open'],df['High'],df['Low'];idx=df.index
    N=lambda c,d=0:df.get(c,pd.Series(d,index=idx)).fillna(d);vr=vol_ratio
    a200=C>N('MA200');a50=C>N('MA50');a20=C>N('MA20');b200=C<N('MA200');b50=C<N('MA50')
    mhr=N('MACD_Hist')>N('MACD_Hist').shift(1);mhf=N('MACD_Hist')<N('MACD_Hist').shift(1)
    rr_=N('RSI')>N('RSI').shift(1);rf_=N('RSI')<N('RSI').shift(1);wr_=N('WT1')>N('WT1').shift(1);wf_=N('WT1')<N('WT1').shift(1)
    obv=N('OBV');obvm=obv.rolling(20,min_periods=10).mean();regime=N('Regime');ca=N('Composite_Accel');pb=N('Percent_B');rmfi=N('RSI_MFI');cmf=N('CMF')
    kumo_top=pd.concat([N('Ichimoku_SenkouA'),N('Ichimoku_SenkouB')],axis=1).max(axis=1);kumo_bot=pd.concat([N('Ichimoku_SenkouA'),N('Ichimoku_SenkouB')],axis=1).min(axis=1);utbot_dir=N('UTBot_Dir')
    # BUY
    bt=pd.Series(0.,index=idx);bt+=np.where(a200&a50&a20,5,np.where(a200&a50,4,np.where(a200,2.5,np.where(a50,1.5,0))));bt+=np.where(N('MA50')>N('MA200'),1.5,0)+np.where(N('Plus_DI')>N('Minus_DI'),1,0)+np.where(N('ST_Direction')==1,1,0);bt+=_sp(df,'Cross_Above_50MA',1)+_sp(df,'Golden_Cross',1.5)+np.where(b200&b50,-2.,0);df['BL_Trend']=bt.clip(-2,JT.TREND_CAP)
    bm=pd.Series(0.,index=idx)
    for s,p in [('MACD_Cross_Buy',2.5),('MACD_Zero_Cross_Buy',2),('StochRSI_Cross_Buy',2),('ADX_Momentum_Buy',2),('VWAP_Bounce_Buy',1.5)]:bm+=_sp(df,s,p)
    bm=bm.clip(upper=6);bm+=np.select([(N('MACD_Hist')>0)&mhr,(N('MACD_Hist')>0)&mhf,(N('MACD_Hist')<0)&mhr],[2,.5,1.5],default=0.);bm+=np.select([(N('RSI')<30)&rr_,N('RSI')<30,(N('RSI')<45)&rr_],[3,1.5,1],default=0.)
    bm+=np.select([(N('StochK')<20)&(N('StochK')>N('StochD')),N('StochK')<20],[2.5,1],default=0.);bm+=np.select([(N('WT1')<OS1)&wr_,N('WT1')<OS1,(N('WT1')<-20)&wr_],[3,1,1],default=0.)
    bm+=_sp(df,'UTBot_Buy',2.5)+_sp(df,'StochSlow_Cross_Buy',1.5)+_sp(df,'Squeeze_Mom_Cross_Up',1.5)+np.where(hma_r_v&wr_.values,1,0);df['BL_Momentum']=bm.clip(-2,JT.MOMENTUM_CAP)
    bcc=pd.Series(0.,index=idx)
    for s,p in [('Morning_Star',3.5),('Bullish_Engulfing',3),('Hammer',2.5),('Outside_Bullish',2.5),('Doji_Bullish',1),('Three_Bar_Reversal_Buy',2.5)]:bcc=np.maximum(bcc,_sp(df,s,p))
    df['BL_Candle']=pd.Series(bcc,index=idx).clip(upper=JT.CANDLE_CAP)
    bb_=pd.Series(0.,index=idx);bb_+=_sp(df,'BB_Squeeze_End_Bull',3)+_sp(df,'NR7_2',1.5)+_sp(df,'Calm_After_Storm',1);bb_+=np.select([pb<.05,pb<.2,(pb>=.4)&(pb<=.6)&a50,pb>.95],[2.5,1.5,.5,-1.5],default=0.)+_sp(df,'BB_Lower_Bounce',2);df['BL_BB']=bb_.clip(-1,JT.BB_CAP)
    bv=pd.Series(0.,index=idx);bv+=_sp(df,'Volume_Climax_Buy',3)+_sp(df,'Pocket_Pivot',2)+_sp(df,'OBV_Div_Buy',1.5)+_sp(df,'Volume_POC_Breakout',2.5)+_sp(df,'Volume_Dry_Breakout_Buy',2);bv+=np.where((vr>=3)&(C>O),2.5,np.where((vr>=1.5)&(C>O),1,0))+np.where(obv>obvm,1,np.where(obv<obvm,-1,0));df['BL_Volume']=bv.clip(-1,JT.VOLUME_CAP)
    bmf=pd.Series(0.,index=idx);bmf+=np.select([rmfi<-10,rmfi<-5,rmfi>10],[2,1,-.5],default=0.);bmf+=_sp(df,'MF_Cross_Bull',2)+_sp(df,'MF_Bull_Div',2)+_sp(df,'MF_Accel_Up',1)+_sp(df,'CMF_Bull',1.5);bmf+=np.where(cmf>.15,1.5,np.where(cmf>.05,.5,np.where(cmf<-.15,-1,0)));df['BL_MF']=bmf.clip(-1,JT.MF_CAP)
    bp=pd.Series(0.,index=idx);bp+=_spd(df,'Gold_Dot',4);bp+=np.where(bp==0,_spd(df,'Green_Dot_T1',2.5),0)
    for s,p in [('Bull_Divergence',2),('Pullback_123_Bull',2.5),('Setup_180_Bull',2),('Boomer_Buy',2),('Expansion_BO',3),('Gilligans_Buy',2.5),('Lizard_Bull',2),('NonADX_123_Bull',1.5),('EMA_Pullback_Buy',2),('Momentum_Ignition_Buy',3),('SuperTrend_Buy',2),('Parabolic_Bottom_Buy',3),('Kumo_Breakout_Bull',2.5),('Reversal_New_Highs',2.5),('Slingshot_Bull',2),('Jack_In_Box_Bull',2),('Relative_Strength_Buy',2.5),('VP_VAL_Support',1.5),('VuManChu_Bull',3),('Hull_Turn_Bull',2),('Doji_Breakout_Buy',1.5),('Three_Bar_Reversal_Buy',2)]:bp+=_sp(df,s,p)
    df['BL_Pattern']=bp.clip(upper=JT.PATTERN_CAP)
    bcs=pd.Series(0.,index=idx)
    for cn,cfg in COMBINED_SCAN_REGISTRY.items():
        if cfg['dir']!='buy' or cn not in df.columns:continue
        bcs+=np.where(df[cn].fillna(False),{1:JT.COMBO_T1,2:JT.COMBO_T2,3:JT.COMBO_T3}.get(cfg['tier'],1),0.)
    df['BL_Combined']=bcs.clip(upper=JT.COMBINED_CAP)
    bl_=pd.Series(0.,index=idx);bl_+=np.where(ca>JT.ACCEL_STRONG,3,np.where(ca>JT.ACCEL_MOD,1.5,np.where(ca>.5,.5,np.where(ca<-JT.ACCEL_MOD,-1,0))));bl_+=_sp(df,'Setup_Squeeze_Bull',1.5)+_sp(df,'Momentum_Accel_Buy',2)+_sp(df,'WT_Convergence_Bull',1.5)+_sp(df,'Volume_Dry_Up',.5)
    bl_+=np.where(utbot_dir==1,1,np.where(utbot_dir==-1,-.5,0))+np.where(hma_r_v,.5,-.5)
    sp_buy=pd.Series(0.,index=idx);sp_buy+=np.where(N('WT1')<-40,2,np.where(N('WT1')<-20,1,0));sp_buy+=np.where(N('RSI')<35,1.5,np.where(N('RSI')<45,.5,0))+np.where(N('StochK')<25,1,0)+np.where(ca>JT.ACCEL_MOD,2,np.where(ca>.5,1,0))
    df['Setup_Pressure_Buy']=sp_buy;bl_+=np.where(sp_buy>=8,3,np.where(sp_buy>=5,2,np.where(sp_buy>=3,1,0)));df['BL_Leading']=bl_.clip(-1,JT.LEADING_CAP)
    blag=pd.Series(0.,index=idx);blag+=np.where(a200&a50&(N('MA50')>N('MA200')),3,np.where(a50&(N('MA50')>N('MA200')),2,np.where(a200,1,0)));blag+=np.where(regime.values<=-1,-1.5,0)+np.where(regime.values>=2,3,np.where(regime.values>=1,1.5,0))
    blag+=np.where(C>kumo_top,1.5,np.where(C<kumo_top,-1,0));blag+=np.where(N('RS_Ratio',1)>1.05,2,np.where(N('RS_Ratio',1)>1.02,1,np.where(N('RS_Ratio',1)<.95,-1.5,0)));df['BL_Lagging']=blag.clip(-2,JT.LAGGING_CAP)
    # SELL
    st_=pd.Series(0.,index=idx);st_+=np.where(b200&b50&(C<N('MA20')),5,np.where(b200&b50,4,np.where(b200,2.5,np.where(b50,1.5,0))));st_+=np.where(N('MA50')<N('MA200'),1.5,0)+np.where(N('Minus_DI')>N('Plus_DI'),1,0)+np.where(N('ST_Direction')==-1,1,0);st_+=_sp(df,'Fell_Below_50MA',1)+_sp(df,'Death_Cross',1.5)+np.where(a200&a50,-2.,0);df['SL_Trend']=st_.clip(-2,JT.TREND_CAP)
    sm_=pd.Series(0.,index=idx)
    for s,p in [('MACD_Cross_Sell',2.5),('MACD_Zero_Cross_Sell',2),('StochRSI_Cross_Sell',2),('ADX_Momentum_Sell',2),('VWAP_Reject_Sell',1.5)]:sm_+=_sp(df,s,p)
    sm_=sm_.clip(upper=6);sm_+=np.select([(N('MACD_Hist')<0)&mhf,(N('MACD_Hist')<0)&mhr,(N('MACD_Hist')>0)&mhf],[2,.5,1.5],default=0.);sm_+=np.select([(N('RSI')>70)&rf_,N('RSI')>70,(N('RSI')>55)&rf_],[3,1.5,1],default=0.)
    sm_+=np.select([(N('StochK')>80)&(N('StochK')<N('StochD')),N('StochK')>80],[2.5,1],default=0.);sm_+=np.select([(N('WT1')>OB1)&wf_,N('WT1')>OB1,(N('WT1')>20)&wf_],[3,1,1],default=0.)
    sm_+=_sp(df,'UTBot_Sell',2.5)+_sp(df,'StochSlow_Cross_Sell',1.5)+_sp(df,'Squeeze_Mom_Cross_Down',1.5)+np.where(~hma_r_v&wf_.values,1,0);df['SL_Momentum']=sm_.clip(-2,JT.MOMENTUM_CAP)
    scc_=pd.Series(0.,index=idx)
    for s,p in [('Evening_Star',3.5),('Bearish_Engulfing',3),('Shooting_Star',2.5),('Outside_Bearish',2.5),('Doji_Bearish',1),('Three_Bar_Reversal_Sell',2.5)]:scc_=np.maximum(scc_,_sp(df,s,p))
    df['SL_Candle']=pd.Series(scc_,index=idx).clip(upper=JT.CANDLE_CAP)
    sbb_=pd.Series(0.,index=idx);sbb_+=_sp(df,'BB_Squeeze_End_Bear',3)+_sp(df,'NR7_2',1.5)+_sp(df,'Calm_After_Storm',1);sbb_+=np.select([pb>.95,pb>.8,(pb>=.4)&(pb<=.6)&b50,pb<.05],[2.5,1.5,.5,-1.5],default=0.)+_sp(df,'BB_Lower_Break',1.5);df['SL_BB']=sbb_.clip(-1,JT.BB_CAP)
    sv_=pd.Series(0.,index=idx);sv_+=_sp(df,'Volume_Climax_Sell',3)+_sp(df,'OBV_Div_Sell',1.5)+_sp(df,'Volume_POC_Breakdown',2.5)+_sp(df,'Volume_Dry_Breakout_Sell',2);sv_+=np.where((vr>=3)&(C<O),2.5,np.where((vr>=1.5)&(C<O),1,0))+np.where(obv<obvm,1,np.where(obv>obvm,-1,0));df['SL_Volume']=sv_.clip(-1,JT.VOLUME_CAP)
    smf_=pd.Series(0.,index=idx);smf_+=np.select([rmfi>10,rmfi>5,rmfi<-10],[2,1,-.5],default=0.);smf_+=_sp(df,'MF_Cross_Bear',2)+_sp(df,'MF_Bear_Div',2)+_sp(df,'MF_Accel_Dn',1)+_sp(df,'CMF_Bear',1.5);smf_+=np.where(cmf<-.15,1.5,np.where(cmf<-.05,.5,np.where(cmf>.15,-1,0)));df['SL_MF']=smf_.clip(-1,JT.MF_CAP)
    spp_=pd.Series(0.,index=idx);spp_+=_spd(df,'Blood_Diamond',4);spp_+=np.where(spp_==0,_spd(df,'Red_Dot_T1',2.5),0)
    for s,p in [('Bear_Divergence',2),('Pullback_123_Bear',2.5),('Setup_180_Bear',2),('Boomer_Sell',2),('Expansion_BD',3),('Gilligans_Sell',2.5),('Lizard_Bear',2),('NonADX_123_Bear',1.5),('EMA_Pullback_Sell',2),('Momentum_Ignition_Sell',3),('SuperTrend_Sell',2),('Parabolic_Top_Sell',3),('Kumo_Breakout_Bear',2.5),('Reversal_New_Lows',2.5),('Slingshot_Bear',2),('Jack_In_Box_Bear',2),('Relative_Strength_Sell',2),('VP_VAH_Resistance',1.5),('VuManChu_Bear',3),('Hull_Turn_Bear',2),('Doji_Breakout_Sell',1.5),('Three_Bar_Reversal_Sell',2)]:spp_+=_sp(df,s,p)
    df['SL_Pattern']=spp_.clip(upper=JT.PATTERN_CAP)
    scs_=pd.Series(0.,index=idx)
    for cn,cfg in COMBINED_SCAN_REGISTRY.items():
        if cfg['dir']!='sell' or cn not in df.columns:continue
        scs_+=np.where(df[cn].fillna(False),{1:JT.COMBO_T1,2:JT.COMBO_T2,3:JT.COMBO_T3}.get(cfg['tier'],1),0.)
    df['SL_Combined']=scs_.clip(upper=JT.COMBINED_CAP)
    sl__=pd.Series(0.,index=idx);sl__+=np.where(ca<-JT.ACCEL_STRONG,3,np.where(ca<-JT.ACCEL_MOD,1.5,np.where(ca<-.5,.5,np.where(ca>JT.ACCEL_MOD,-1,0))));sl__+=_sp(df,'Setup_Squeeze_Bear',1.5)+_sp(df,'Momentum_Accel_Sell',2)+_sp(df,'WT_Convergence_Bear',1.5)
    sl__+=np.where(utbot_dir==-1,1,np.where(utbot_dir==1,-.5,0))+np.where(~hma_r_v,.5,-.5)
    sp_sell=pd.Series(0.,index=idx);sp_sell+=np.where(N('WT1')>40,2,np.where(N('WT1')>20,1,0));sp_sell+=np.where(N('RSI')>65,1.5,np.where(N('RSI')>55,.5,0))+np.where(N('StochK')>75,1,0)+np.where(ca<-JT.ACCEL_MOD,2,np.where(ca<-.5,1,0))
    df['Setup_Pressure_Sell']=sp_sell;sl__+=np.where(sp_sell>=8,3,np.where(sp_sell>=5,2,np.where(sp_sell>=3,1,0)));df['SL_Leading']=sl__.clip(-1,JT.LEADING_CAP)
    slag_=pd.Series(0.,index=idx);slag_+=np.where(b200&b50&(N('MA50')<N('MA200')),3,np.where(b50&(N('MA50')<N('MA200')),2,np.where(b200,1,0)));slag_+=np.where(regime.values>=1,-1.5,0)+np.where(regime.values<=-2,3,np.where(regime.values<=-1,1.5,0))
    slag_+=np.where(C<kumo_bot,1.5,np.where(C>kumo_top,-1,0));slag_+=np.where(N('RS_Ratio',1)<.95,2,np.where(N('RS_Ratio',1)<.98,1,np.where(N('RS_Ratio',1)>1.05,-1.5,0)));df['SL_Lagging']=slag_.clip(-2,JT.LAGGING_CAP)
    LN=['Trend','Momentum','Candle','BB','Volume','MF','Pattern','Combined','Leading','Lagging']
    df['Buy_Total']=sum(df[f'BL_{n}'].clip(lower=0) for n in LN);df['Sell_Total']=sum(df[f'SL_{n}'].clip(lower=0) for n in LN)
    df['Buy_Active_Layers']=sum((df[f'BL_{n}']>0).astype(int) for n in LN);df['Sell_Active_Layers']=sum((df[f'SL_{n}']>0).astype(int) for n in LN)
    ls_=df['BL_Leading']-df['SL_Leading'];lgs=df['BL_Lagging']-df['SL_Lagging']
    df['Leading_Verdict']=np.select([ls_>3,ls_>1,ls_<-3,ls_<-1],['강한 상승 가속','상승 임박','강한 하락 가속','하락 임박'],default='중립')
    df['Lagging_Verdict']=np.select([lgs>3,lgs>1,lgs<-3,lgs<-1],['강한 상승 추세','상승 추세','강한 하락 추세','하락 추세'],default='비추세/횡보')
    return df

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  🏷️ 판단 이유 자동 생성
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _gen_reason(j,es,ctx,veto,syn,pred,ba,sa,wt1,rsi,mfi,cmf,obv_up,adx,vr,ma50a,ma200a,mh_up,stk,hma_r,ut_dir,sq_on,cms):
    ts,ms,mns,ss,ls=cms.get('Trend',0),cms.get('Momentum',0),cms.get('Money',0),cms.get('Structure',0),cms.get('Leading',0)
    cl=CTX_KOR.get(ctx,'기본')
    if j=='STRONG_BUY':
        if 'Capitul' in veto:return "투매 항복 바닥 확인 — 극과매도+거래량 폭발+강한 반전 캔들",f"WT={wt1:.0f} RSI={rsi:.0f} + Vol {vr:.1f}x 폭발 + 양봉 전환","강력매수 🟢🟢🟢"
        if ctx==CTX_EXTREME_OS and syn>10:return "V자 급반등 가능성 고조 — 투매 종료+모멘텀 전환 확인",f"WT={wt1:.0f} 방향전환 + {ba}개 위원회 매수 + 시너지 {syn:+.1f}","강력매수 🟢🟢🟢"
        if ba>=4:
            f=[];
            if ms>30:f.append(f"모멘텀↑{ms:+.0f}");
            if mns>15:f.append(f"자금유입{mns:+.0f}");
            if ls>20:f.append(f"선행↑{ls:+.0f}")
            return "다중 확인 강세 — 4개 이상 위원회 매수 합의",' + '.join(f) or '전위원회 강세',"강력매수 🟢🟢🟢"
        return "복합 강세 시그널 다중 확인",f"ES={es:+.1f}, {ba}개 위원회 동의, {cl}","강력매수 🟢🟢🟢"
    if j=='STRONG_SELL':
        if 'Blowoff' in veto:return "블로우오프 천장 — 극과매수+거래량 폭발+강한 하락 전환",f"WT={wt1:.0f} RSI={rsi:.0f} + Vol {vr:.1f}x + 음봉","강력매도 🔴🔴🔴"
        if ctx==CTX_EXTREME_OB and syn<-10:return "오버슈팅 한계 도달 — 단기 급락+추세 반전 위험",f"WT={wt1:.0f} 꺾임 + {sa}개 위원회 매도 + 시너지 {syn:+.1f}","강력매도 🔴🔴🔴"
        if sa>=4:
            f=[];
            if ms<-30:f.append(f"모멘텀↓{ms:+.0f}");
            if mns<-15:f.append(f"자금이탈{mns:+.0f}")
            return "전면적 약세 — 다중 하락 확인",' + '.join(f) or '전위원회 약세',"강력매도 🔴🔴🔴"
        return "복합 약세 시그널 다중 확인",f"ES={es:+.1f}, {sa}개 위원회 매도","강력매도 🔴🔴🔴"
    if j=='BUY':
        if ctx in (CTX_ACCUMULATION,CTX_BOTTOMING):return "바닥권 매집 완료 — 박스권 상단 돌파 예상",f"CMF={cmf:.3f} 자금유입 + OBV {'↑' if obv_up else '↓'} + 에너지 축적","매수 🟢🟢"
        if ma50a and ma200a and ms>15:return "상승추세 내 눌림목 — 모멘텀 재가속 확인",f"정배열 + 모멘텀{ms:+.0f} + {'MACD개선' if mh_up else ''}","매수 🟢🟢"
        if sq_on or (ss>15 and ls>10):return "에너지 축적 후 상방 돌파",f"스퀴즈{'해소' if sq_on else ''} + 구조{ss:+.0f} + 선행{ls:+.0f}","매수 🟢🟢"
        if syn>5:return "모멘텀 전환 확인 — 선행지표 주도 추세 전환",f"교차시너지 {syn:+.1f}","매수 🟢🟢"
        return "상승 모멘텀 우위 — 매수 조건 충족",f"ES={es:+.1f}, B{ba}:S{sa}, {cl}","매수 🟢🟢"
    if j=='SELL':
        if ctx in (CTX_DISTRIBUTION,CTX_TOPPING):return "고점 매물 출회+세력 이탈 — 하락 전환 예상",f"CMF={cmf:.3f} 이탈 + OBV {'↓' if not obv_up else '↑'}","매도 🔴🔴"
        if not ma50a and not ma200a and ms<-15:return "하락추세 가속 — 역배열+모멘텀 악화",f"역배열 + 모멘텀{ms:+.0f}","매도 🔴🔴"
        if syn<-5:return "천장 전환 신호 — 모멘텀+선행 하락 경고",f"시너지 {syn:+.1f}","매도 🔴🔴"
        return "하락 모멘텀 우위 — 리스크 관리 필요",f"ES={es:+.1f}","매도 🔴🔴"
    if j=='WATCH_BUY':
        if ctx==CTX_EXTREME_OS:return "과매도 접근 — 반등 준비, 확인 후 진입",f"WT={wt1:.0f} RSI={rsi:.0f}","단기매수 관찰 🟡🟢"
        if pred>5:return "상승 모멘텀 형성 중 — 가속도 개선",f"예측+{pred:+.1f}","단기매수 관찰 🟡🟢"
        if hma_r and ut_dir==1:return "선행지표 강세 전환 — Hull+UTBot 매수",f"Hull↑ + UTBot 매수","단기매수 관찰 🟡🟢"
        return "상승 우위이나 확인 부족",f"ES={es:+.1f}","단기매수 관찰 🟡🟢"
    if j=='WATCH_SELL':
        if ctx==CTX_EXTREME_OB:return "과매수 접근 — 조정 준비, 확인 후 매도",f"WT={wt1:.0f} RSI={rsi:.0f}","단기매도 관찰 🟡🔴"
        if pred<-5:return "하락 모멘텀 형성 중 — 가속도 악화",f"예측{pred:+.1f}","단기매도 관찰 🟡🔴"
        if not hma_r and ut_dir==-1:return "선행지표 약세 전환",f"Hull↓ + UTBot 매도","단기매도 관찰 🟡🔴"
        return "하락 우위이나 확인 부족",f"ES={es:+.1f}","단기매도 관찰 🟡🔴"
    if j=='MIXED':
        if sq_on or ctx==CTX_VOL_DRY:return "에너지 응축 — 변동성 폭발(Squeeze) 직전",f"스퀴즈{'ON' if sq_on else 'OFF'} + 거래량 고갈","관망/대기 🟠"
        if ba>=2 and sa>=2:return "매수·매도 팽팽 — 방향 결정 이벤트 대기",f"B{ba}:S{sa} 균형","관망/대기 🟠"
        return "상반된 시그널 혼재",f"ES={es:+.1f}","관망/대기 🟠"
    # NEUTRAL
    if ctx==CTX_RANGING:return "방향성 부재 — 지지/저항선 이탈 확인 필요",f"ADX={adx:.0f} + 횡보","중립/관망 ⚪"
    if ctx==CTX_VOL_DRY:return "거래량 고갈 — 폭풍 전 고요, 방향성 돌파 대기","거래량↓ + BB수축","중립/관망 ⚪"
    if ctx==CTX_POST_EXPLOSION:return "변동성 폭발 직후 — 방향 확인 단계","대형캔들 후 정착 관찰","중립/관망 ⚪"
    if abs(es)<5:return "시그널 부족 — 명확한 근거 없음",f"ES={es:+.1f}","중립/관망 ⚪"
    return "혼조세 — 추가 확인 대기",f"ES={es:+.1f}, {cl}","중립/관망 ⚪"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  🏛️ 5-Committee Ensemble + 컨텍스트 + Veto + 시너지 + 예측 + 이유
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _detect_context_vectorized(df):
    n=len(df);idx=df.index;N=lambda c,d=0:df.get(c,pd.Series(d,index=idx)).fillna(d)
    C=df['Close'];wt1=N('WT1');rsi=N('RSI');adx=N('ADX');pdi=N('Plus_DI');mdi=N('Minus_DI');cmf=N('CMF');obv=N('OBV')
    a50=C>N('MA50');a200=C>N('MA200');b50=C<N('MA50');b200=C<N('MA200');atr=N('ATR')
    vol_avg=df['Volume'].rolling(50,min_periods=10).mean();vr=df['Volume']/(vol_avg+1e-10);obv_ma=obv.rolling(10,min_periods=5).mean()
    prp=(C.rolling(20).max()-C.rolling(20).min())/(C.rolling(20).min()+1e-10);flat=prp<.08
    ma50s=(N('MA50')-N('MA50').shift(10))/(N('MA50').shift(10)+1e-10)*100
    ctx=np.full(n,CTX_DEFAULT,dtype=int)
    ctx=np.where((adx<20)&flat,CTX_RANGING,ctx);ctx=np.where(flat&(cmf<-.05)&(obv<obv_ma)&(vr>=.7),CTX_DISTRIBUTION,ctx)
    ctx=np.where(flat&(cmf>.05)&(obv>obv_ma)&(vr>=.7),CTX_ACCUMULATION,ctx);ctx=np.where((adx>30)&(mdi>pdi)&b50&b200,CTX_STRONG_DN,ctx)
    ctx=np.where((adx>30)&(pdi>mdi)&a50&a200,CTX_STRONG_UP,ctx)
    ctx=np.where((wt1>60)|(rsi>75)|((wt1>50)&(rsi>70)&(N('MFI')>75)),CTX_EXTREME_OB,ctx)
    ctx=np.where((wt1<-60)|(rsi<25)|((wt1<-50)&(rsi<30)&(N('MFI')<25)),CTX_EXTREME_OS,ctx)
    ctx=np.where((ma50s<0)&(ma50s>ma50s.shift(5))&flat&(cmf>0),CTX_BOTTOMING,ctx)
    ctx=np.where((ma50s>0)&(ma50s<ma50s.shift(5))&flat&(cmf<0),CTX_TOPPING,ctx)
    ctx=np.where((vr<0.5)&(N('BB_Width')<N('BB_Width').rolling(60,min_periods=30).quantile(0.1)),CTX_VOL_DRY,ctx)
    wb=(df['High']-df['Low'])>atr*2;pe=wb.shift(1).fillna(False)|wb.shift(2).fillna(False);ctx=np.where(pe&~wb,CTX_POST_EXPLOSION,ctx)
    return pd.Series(ctx,index=idx)

def _committee_trend(df,N):
    C=df['Close'];idx=df.index;score=pd.Series(0.,index=idx)
    a200=C>N('MA200');a50=C>N('MA50');a20=C>N('MA20');b200=C<N('MA200');b50=C<N('MA50');b20=C<N('MA20')
    score+=np.where(a200&a50&a20,30,np.where(a200&a50,20,np.where(a50,10,0)));score+=np.where(b200&b50&b20,-30,np.where(b200&b50,-20,np.where(b50,-10,0)))
    ma50s=(N('MA50')-N('MA50').shift(10))/(N('MA50').shift(10)+1e-10)*100;score+=np.clip(ma50s*3,-15,15)
    adx_val=N('ADX');pdi=N('Plus_DI');mdi=N('Minus_DI');di_diff=pdi-mdi;score+=np.where(adx_val>25,np.clip(di_diff*.5,-15,15),np.clip(di_diff*.2,-5,5))
    score+=np.where(N('ST_Direction')==1,10,np.where(N('ST_Direction')==-1,-10,0))
    kt=pd.concat([N('Ichimoku_SenkouA'),N('Ichimoku_SenkouB')],axis=1).max(axis=1);kb=pd.concat([N('Ichimoku_SenkouA'),N('Ichimoku_SenkouB')],axis=1).min(axis=1)
    score+=np.where(C>kt,10,np.where(C<kb,-10,0))
    atr=N('ATR');d50=(C-N('MA50'))/(atr+1e-10);d200=(C-N('MA200'))/(atr+1e-10)
    score+=np.where(d50<-3,20,np.where(d50<-2,12,np.where(d50>3,-20,np.where(d50>2,-12,0))))
    score+=np.where(d200<-4,15,np.where(d200<-2.5,8,np.where(d200>4,-15,np.where(d200>2.5,-8,0))))
    ma50a=ma50s-ma50s.shift(5);score+=np.where((ma50s<0)&(ma50a>0.5),8,0)+np.where((ma50s>0)&(ma50a<-0.5),-8,0)
    ns=(score/JT.TREND_NORM*100).clip(-100,100);conv=np.clip(adx_val.values*2,5,95)
    wt1=N('WT1').values;rsi=N('RSI').values;eos=np.clip((-50-wt1)/30,0,1)*.7+np.clip((30-rsi)/20,0,1)*.3;eob=np.clip((wt1-50)/30,0,1)*.7+np.clip((rsi-70)/20,0,1)*.3
    conv=conv*(1-np.maximum(eos,eob)*0.8);conv=np.clip(conv,5,95)
    return ns,pd.Series(conv,index=idx)

def _committee_momentum(df,N):
    idx=df.index;score=pd.Series(0.,index=idx);rsi=N('RSI');wt1=N('WT1');wt2=N('WT2');mh=N('MACD_Hist');stk=N('StochK');std=N('StochD');ca=N('Composite_Accel')
    score+=(rsi-50)*.6+np.where(rsi>rsi.shift(1),5,np.where(rsi<rsi.shift(1),-5,0))
    score+=wt1*.3+np.where(wt1>wt2,8,np.where(wt1<wt2,-8,0))+np.where(wt1>wt1.shift(1),5,np.where(wt1<wt1.shift(1),-5,0))
    score+=np.where(mh>mh.shift(1),8,np.where(mh<mh.shift(1),-8,0))+np.where(mh>0,5,np.where(mh<0,-5,0))
    score+=(stk-50)*.2+np.where((stk>std)&(stk<30),10,np.where((stk<std)&(stk>70),-10,0));score+=np.clip(ca*5,-15,15)
    wv=wt1.values;rv=rsi.values;mv=N('MFI').values;mhv=mh.values
    wtu=(wv<-30)&(wv>np.roll(wv,1));wtd=(wv>30)&(wv<np.roll(wv,1));rtu=(rv<40)&(rv>np.roll(rv,1));rtd=(rv>60)&(rv<np.roll(rv,1))
    bp=wtu.astype(float)+rtu.astype(float)+(mv<35).astype(float)+(mhv>np.roll(mhv,1)).astype(float)
    brp=wtd.astype(float)+rtd.astype(float)+(mv>65).astype(float)+(mhv<np.roll(mhv,1)).astype(float)
    score+=np.where(bp>=4,25,np.where(bp>=3,15,np.where(bp>=2,5,0)))+np.where(brp>=4,-25,np.where(brp>=3,-15,np.where(brp>=2,-5,0)))
    score+=np.where((wv<-70)&(wv>np.roll(wv,1)),20,0)+np.where((wv>70)&(wv<np.roll(wv,1)),-20,0)
    ns=(score/JT.MOMENTUM_NORM*100).clip(-100,100)
    ext=np.maximum(np.clip((-wt1.values-30)/40,0,1),np.clip((wt1.values-30)/40,0,1))
    tb=np.where(wtu|wtd,20,0);pb=np.where(bp>=3,15,np.where(brp>=3,15,0));conv=np.clip(40+ext*50+tb+pb,15,98)
    return ns,pd.Series(conv,index=idx)

def _committee_money(df,N):
    idx=df.index;C=df['Close'];score=pd.Series(0.,index=idx);cmf=N('CMF');obv=N('OBV');obv_ma=obv.rolling(20,min_periods=10).mean()
    score+=np.clip(cmf*100,-30,30);obv_r=(obv-obv_ma)/(obv_ma.abs()+1e-10)*100;score+=np.clip(obv_r*.3,-20,20)
    ou=_vs(obv>obv.shift(1));od=_vs(obv<obv.shift(1));score+=np.where(ou>=5,10,np.where(od>=5,-10,0))
    score+=(N('MFI')-50)*.5+np.clip(N('RSI_MFI')*.8,-15,15)
    vol=df['Volume'];va=vol.rolling(50,min_periods=10).mean();vr=vol/(va+1e-10);pd_=np.where(C>C.shift(1),1,np.where(C<C.shift(1),-1,0))
    score+=np.where(vr>=2,pd_*15,np.where(vr>=1.5,pd_*8,0))
    ns=(score/JT.MONEY_NORM*100).clip(-100,100);vc=np.clip(vr.values*30,10,60);cc=np.clip(np.abs(cmf.values)*100,0,30);conv=np.clip(vc+cc,10,95)
    return ns,pd.Series(conv,index=idx)

def _committee_structure(df,N):
    idx=df.index;C=df['Close'];O=df['Open'];score=pd.Series(0.,index=idx);pb=N('Percent_B')
    score+=np.select([pb<.05,pb<.15,pb<.3,pb>.95,pb>.85,pb>.7,(pb>=.4)&(pb<=.6)],[20,12,5,-20,-12,-5,0],default=0.)
    score+=np.where((pb<.1)&(C>O),10,0)+np.where((pb>.9)&(C<O),-10,0)
    poc=N('VP_POC');vah=N('VP_VAH');val_=N('VP_VAL');dp=(C-poc)/(poc+1e-10)*100
    score+=np.where(dp.abs()<1,5,np.where(dp>3,-3,np.where(dp<-3,3,0)))
    score+=np.where(((C-val_).abs()/(C+1e-10)<.02)&(C>O),10,0)+np.where(((vah-C).abs()/(C+1e-10)<.02)&(C<O),-10,0)
    F=lambda c:df.get(c,pd.Series(False,index=idx)).fillna(False)
    cb=F('Morning_Star').astype(float)*20+F('Bullish_Engulfing').astype(float)*15+F('Hammer').astype(float)*12+F('Outside_Bullish').astype(float)*10+F('Doji_Bullish').astype(float)*5+F('Three_Bar_Reversal_Buy').astype(float)*15
    cs=F('Evening_Star').astype(float)*20+F('Bearish_Engulfing').astype(float)*15+F('Shooting_Star').astype(float)*12+F('Outside_Bearish').astype(float)*10+F('Doji_Bearish').astype(float)*5+F('Three_Bar_Reversal_Sell').astype(float)*15
    score+=cb-cs+np.where(F('BB_Squeeze_End_Bull'),15,np.where(F('BB_Squeeze_End_Bear'),-15,0))
    ns=(score/JT.STRUCTURE_NORM*100).clip(-100,100)
    ne=(pb<.2).astype(float)+(pb>.8).astype(float)+(cb>0).astype(float)+(cs>0).astype(float)+(((C-val_).abs()/(C+1e-10)<.03)|((vah-C).abs()/(C+1e-10)<.03)).astype(float)+F('BB_Squeeze_End_Bull').astype(float)+F('BB_Squeeze_End_Bear').astype(float)
    conv=np.clip(ne.values*20+15,10,90)
    return ns,pd.Series(conv,index=idx)

def _committee_leading(df,N):
    idx=df.index;score=pd.Series(0.,index=idx);ut=N('UTBot_Dir');hma=df.get('HMA_Rising',pd.Series(False,index=idx)).fillna(False)
    score+=np.where(ut==1,20,np.where(ut==-1,-20,0))+np.where(hma,15,-15)
    sq=N('Squeeze_Momentum');sr=df.get('Squeeze_Mom_Rising',pd.Series(False,index=idx)).fillna(False)
    score+=np.where(sq>0,10,np.where(sq<0,-10,0))+np.where((sq>0)&sr,5,np.where((sq<0)&~sr,-5,0))
    ca=N('Composite_Accel');score+=np.clip(ca*8,-20,20)
    spb=N('Setup_Pressure_Buy');sps=N('Setup_Pressure_Sell')
    score+=np.where(spb>=8,15,np.where(spb>=5,8,np.where(spb>=3,3,0)))-np.where(sps>=8,15,np.where(sps>=5,8,np.where(sps>=3,3,0)))
    F=lambda c:df.get(c,pd.Series(False,index=idx)).fillna(False)
    for cn,cfg in COMBINED_SCAN_REGISTRY.items():
        if cn not in df.columns:continue
        pts={1:15,2:8,3:3}.get(cfg['tier'],3)
        if cfg['dir']=='buy':score+=np.where(F(cn),pts,0)
        elif cfg['dir']=='sell':score-=np.where(F(cn),pts,0)
    score+=np.where(F('VuManChu_Bull'),20,0)-np.where(F('VuManChu_Bear'),20,0)
    ns=(score/JT.LEADING_NORM*100).clip(-100,100)
    ag=(ut==1).astype(float)+hma.astype(float)+(sq>0).astype(float)+(ca>0).astype(float);dg=(ut==-1).astype(float)+(~hma).astype(float)+(sq<0).astype(float)+(ca<0).astype(float)
    conv=np.clip(np.maximum(ag.values,dg.values)*20+10,10,90)
    return ns,pd.Series(conv,index=idx)


def compute_committee_ensemble(df,vol_ratio,hma_r_v):
    idx=df.index;n=len(df);N=lambda c,d=0:df.get(c,pd.Series(d,index=idx)).fillna(d)
    ctx=_detect_context_vectorized(df);df['Market_Context']=ctx
    scores={};convictions={}
    scores['Trend'],convictions['Trend']=_committee_trend(df,N);scores['Momentum'],convictions['Momentum']=_committee_momentum(df,N)
    scores['Money'],convictions['Money']=_committee_money(df,N);scores['Structure'],convictions['Structure']=_committee_structure(df,N)
    scores['Leading'],convictions['Leading']=_committee_leading(df,N)
    for cm in COMMITTEE_NAMES:df[f'CM_{cm}_Score']=scores[cm];df[f'CM_{cm}_Conv']=convictions[cm]
    ctx_v=ctx.values;wa=np.zeros((n,NUM_COMMITTEES))
    for cc,cn in CTX_LABELS.items():
        m=(ctx_v==cc)
        if m.any():wa[m]=CONTEXT_WEIGHTS.get(cn,CONTEXT_WEIGHTS['default'])
    # Veto
    wt1=N('WT1').values;rsi=N('RSI').values;cmf=N('CMF').values;obv=N('OBV').values;obv_ma=N('OBV').rolling(20,min_periods=10).mean().values;C=df['Close'].values;O=df['Open'].values
    vf=np.zeros((n,6),dtype=bool);vf[:,0]=(wt1<-60)|(rsi<JT.VETO_EXTREME_RSI_LO);vf[:,1]=(wt1>60)|(rsi>JT.VETO_EXTREME_RSI_HI)
    flat=((pd.Series(C).rolling(20).max()-pd.Series(C).rolling(20).min())/(pd.Series(C).rolling(20).min()+1e-10)<.08).values
    vf[:,2]=flat&(cmf>JT.VETO_MONEY_CMF)&(obv>obv_ma);vf[:,3]=flat&(cmf<-JT.VETO_MONEY_CMF)&(obv<obv_ma)
    vr_v=vol_ratio.values;vf[:,4]=vf[:,0]&(vr_v>=3)&(C>O);vf[:,5]=vf[:,1]&(vr_v>=3)&(C<O)
    df['Veto_Flags']=pd.Series([','.join([['ExOS','ExOB','Accum','Distrib','Capitul','Blowoff'][j] for j in range(6) if vf[i,j]]) for i in range(n)],index=idx)
    # Active Flip
    sa=np.column_stack([scores[cm].values for cm in COMMITTEE_NAMES]);ca_=np.column_stack([convictions[cm].values for cm in COMMITTEE_NAMES])
    es=sa.copy();ec=ca_.copy()
    om=vf[:,0];tsm=np.abs(np.minimum(es[om,0],0));es[om,0]=np.clip(tsm*0.4,0,30);ec[om,0]=np.minimum(ec[om,0],25);ec[om,1]*=1.4;ec[om,2]*=1.3;ec[om,4]*=1.3
    obm=vf[:,1];tbm=np.abs(np.maximum(es[obm,0],0));es[obm,0]=-np.clip(tbm*0.4,0,30);ec[obm,0]=np.minimum(ec[obm,0],25);ec[obm,1]*=1.4;ec[obm,2]*=1.3;ec[obm,4]*=1.3
    for mi,bi in [(2,2),(3,2)]:mm=vf[:,mi];es[mm,0]*=0.3;ec[mm,bi]*=1.5
    cm_=vf[:,4]
    for ci in range(NUM_COMMITTEES):sm_=np.abs(np.minimum(es[cm_,ci],0));es[cm_,ci]=np.maximum(es[cm_,ci],0)+sm_*0.3
    ec[cm_,1]=np.clip(ec[cm_,1]*1.5,0,98)
    bom=vf[:,5]
    for ci in range(NUM_COMMITTEES):bm_=np.abs(np.maximum(es[bom,ci],0));es[bom,ci]=np.minimum(es[bom,ci],0)-bm_*0.3
    ec[bom,1]=np.clip(ec[bom,1]*1.5,0,98);ec=np.clip(ec,0,100)
    # 시너지
    syn=np.zeros(n);ts_=es[:,0];ms_=es[:,1];mns_=es[:,2];ss_=es[:,3];ls_=es[:,4]
    bc=(ms_>20)&(ls_>10)&(ts_<10);bstr=np.clip((ms_+ls_)*0.15+np.abs(np.minimum(ts_,0))*0.1,0,25)
    syn+=np.where(bc,bstr,0)+np.where(bc&(mns_>5),8,0)+np.where(bc&(ss_>10),5,0)
    brc=(ms_<-20)&(ls_<-10)&(ts_>-10);brstr=np.clip((-ms_-ls_)*0.15+np.abs(np.maximum(ts_,0))*0.1,0,25)
    syn-=np.where(brc,brstr,0)+np.where(brc&(mns_<-5),8,0)+np.where(brc&(ss_<-10),5,0)
    df['Reversal_Synergy']=syn
    # 예측
    cav=N('Composite_Accel');ab=np.clip(cav.values*3,-15,15);mh=N('MACD_Hist');mu=_vs(mh>mh.shift(1));md=_vs(mh<mh.shift(1))
    mb=np.where(mu.values>=3,8,np.where(md.values>=3,-8,0));stk=N('StochK');sb=np.where((stk.values<20)&(stk.values>N('StochD').values),5,np.where((stk.values>80)&(stk.values<N('StochD').values),-5,0))
    pred=ab+mb+sb;df['Prediction_Boost']=pred
    contribs=es*(ec/100.)*wa;ens=contribs.sum(axis=1)+syn+pred
    for ci,cm in enumerate(COMMITTEE_NAMES):
        s=es[:,ci];c=ec[:,ci];v=np.full(n,0,dtype=int);v=np.where((s>15)&(c>=25),1,v);v=np.where((s<-15)&(c>=25),-1,v);v=np.where(c<15,-99,v)
        df[f'CM_{cm}_Vote']=v;df[f'CM_{cm}_EffScore']=es[:,ci];df[f'CM_{cm}_EffConv']=ec[:,ci]
    df['Ensemble_Score']=ens
    # 판단
    bag=np.zeros(n,dtype=int);sag=np.zeros(n,dtype=int)
    for ci in range(NUM_COMMITTEES):bag+=((es[:,ci]>15)&(ec[:,ci]>=25)).astype(int);sag+=((es[:,ci]<-15)&(ec[:,ci]>=25)).astype(int)
    cth=np.zeros(n);cth=np.where(ctx_v==CTX_EXTREME_OS,-10,cth);cth=np.where(ctx_v==CTX_EXTREME_OB,10,cth);cth=np.where(ctx_v==CTX_STRONG_UP,5,cth);cth=np.where(ctx_v==CTX_STRONG_DN,-5,cth);cth=np.where(ctx_v==CTX_BOTTOMING,-8,cth);cth=np.where(ctx_v==CTX_TOPPING,8,cth)
    j=np.full(n,'NEUTRAL',dtype=object);conf=np.zeros(n,dtype=float)
    rs=[];rd=[];al=[]
    obv_v=N('OBV').values;obv_mav=N('OBV').rolling(20,min_periods=10).mean().values;mhv=N('MACD_Hist').values;mhpv=np.roll(mhv,1)
    for i in range(n):
        e=ens[i];ba=bag[i];sl=sag[i];sy=syn[i];adj=cth[i];sr=1 if abs(sy)>=15 else 0
        sbt=JT.STRONG_BUY_TH+adj;bt=JT.BUY_TH+adj;wbt=JT.WATCH_BUY_TH+adj*.5;sst=JT.STRONG_SELL_TH-adj;st=JT.SELL_TH-adj;wst=JT.WATCH_SELL_TH-adj*.5
        if e>=sbt and ba>=(JT.STRONG_MIN_AGREE-sr):j[i]='STRONG_BUY'
        elif e>=bt and ba>=(JT.BUY_MIN_AGREE-sr):j[i]='BUY'
        elif e>=wbt and ba>=max(JT.WATCH_MIN_AGREE-sr,1):j[i]='WATCH_BUY'
        elif e<=sst and sl>=(JT.STRONG_MIN_AGREE-sr):j[i]='STRONG_SELL'
        elif e<=st and sl>=(JT.BUY_MIN_AGREE-sr):j[i]='SELL'
        elif e<=wst and sl>=max(JT.WATCH_MIN_AGREE-sr,1):j[i]='WATCH_SELL'
        elif ba>=3 and sl>=3:j[i]='MIXED'
        ae=abs(e);dm=max(ba,sl);ap=dm/NUM_COMMITTEES*35;sp=min(ae/60*30,30);avp=np.mean(ec[i])/100*20;syp=min(abs(sy)/20*10,10);pp=min(abs(pred[i])/15*5,5)
        raw=ap+sp+avp+syp+pp
        if j[i] in ('NEUTRAL','MIXED'):raw=max(15,min(55,raw))
        conf[i]=np.clip(raw,5,99)
        cms={cm:es[i,ci] for ci,cm in enumerate(COMMITTEE_NAMES)}
        vstr=df['Veto_Flags'].iloc[i] if i<len(df) else ''
        obr=bool(obv_v[i]>obv_mav[i]) if not np.isnan(obv_mav[i]) else True
        ma50a=bool(C[i]>N('MA50').values[i]) if not np.isnan(N('MA50').values[i]) else False
        ma200a=bool(C[i]>N('MA200').values[i]) if not np.isnan(N('MA200').values[i]) else False
        mhu=bool(mhv[i]>mhpv[i]) if i>0 else False
        r,d,a=_gen_reason(j[i],e,int(ctx_v[i]),vstr,sy,pred[i],ba,sl,N('WT1').values[i],N('RSI').values[i],N('MFI').values[i],N('CMF').values[i],obr,N('ADX').values[i],vol_ratio.values[i],ma50a,ma200a,mhu,N('StochK').values[i],bool(hma_r_v[i]) if i<len(hma_r_v) else False,int(N('UTBot_Dir').values[i]),bool(df.get('Squeeze_On',pd.Series(False,index=idx)).iloc[i]),cms)
        rs.append(r);rd.append(d);al.append(a)
    df['Trade_Judgment']=j;df['Judgment_Confidence']=conf;df['Buy_Agree']=bag;df['Sell_Agree']=sag
    df['Judgment_Reason']=rs;df['Judgment_Detail']=rd;df['Action_Label']=al
    return df

print("✅ Part 2/4 완료")

# ══════════════════════════════════════════════════════════════
#  CipherX V14.2 — PART 3/4
#  차트, 호버(전체시그널+이유), 위원회 시각화, UI
# ══════════════════════════════════════════════════════════════

def _build_candle_hover(dc):
    n=len(dc)
    bar_buy=[[] for _ in range(n)];bar_sell=[[] for _ in range(n)];bar_neutral=[[] for _ in range(n)]
    bar_cs=[[] for _ in range(n)];bar_sb=[[] for _ in range(n)];bar_ss=[[] for _ in range(n)]
    for sn,cfg in SIGNAL_REGISTRY.items():
        if sn not in dc.columns:continue
        vals=dc[sn].fillna(False).values
        if not vals.any():continue
        ix=np.flatnonzero(vals);lbl=f"{cfg['icon']}{cfg['kor']}";desc=cfg['desc'];isb=sn in STRONG_BUY_SIGS;iss=sn in STRONG_SELL_SIGS
        if cfg['dir']=='buy':
            for i in ix:bar_buy[i].append((lbl,desc));
            if isb:
                for i in ix:bar_sb[i].append((lbl,desc))
        elif cfg['dir']=='sell':
            for i in ix:bar_sell[i].append((lbl,desc));
            if iss:
                for i in ix:bar_ss[i].append((lbl,desc))
        else:
            for i in ix:bar_neutral[i].append((lbl,desc))
    for cn,ccfg in COMBINED_SCAN_REGISTRY.items():
        if cn not in dc.columns:continue
        vals=dc[cn].fillna(False).values
        if not vals.any():continue
        ix=np.flatnonzero(vals);lbl=f"{ccfg['icon']}{ccfg['kor']}";desc=ccfg['desc']
        for i in ix:
            bar_cs[i].append((lbl,desc,ccfg['dir']))
            if cn in STRONG_BUY_SIGS:bar_sb[i].append((lbl,desc))
            if cn in STRONG_SELL_SIGS:bar_ss[i].append((lbl,desc))
    dates=dc.index.strftime('%Y-%m-%d').values
    def _g(c,d=0):return dc[c].values if c in dc.columns else np.full(n,d)
    def _gs(c,d=''):return dc[c].values if c in dc.columns else np.full(n,d,dtype=object)
    ov=_g('Open');hv=_g('High');lv=_g('Low');cv=_g('Close');vol=_g('Volume');atr=_g('ATR')
    wt=_g('WT1');rs=_g('RSI',50);mf=_g('MFI',50);jg=_gs('Trade_Judgment','');cf=_g('Judgment_Confidence')
    esv=_g('Ensemble_Score');ctxv=_g('Market_Context');ut=_g('UTBot_Dir')
    hma=dc.get('HMA_Rising',pd.Series(False,index=dc.index)).fillna(False).values
    veto=_gs('Veto_Flags','');pred=_g('Prediction_Boost');reason=_gs('Judgment_Reason','');action=_gs('Action_Label','')
    lv_v=_gs('Leading_Verdict','');lgv=_gs('Lagging_Verdict','')
    cms={cm:_g(f'CM_{cm}_EffScore') for cm in COMMITTEE_NAMES};cmv={cm:_g(f'CM_{cm}_Vote') for cm in COMMITTEE_NAMES}
    texts=[]
    for i in range(n):
        p=[]
        p.append(f"<b>{dates[i]}</b> O:{ov[i]:.2f} H:{hv[i]:.2f} L:{lv[i]:.2f} C:{cv[i]:.2f}")
        p.append(f"Vol:{vol[i]:,.0f} ATR:{atr[i]:.2f}")
        p.append("─"*28)
        cl=CTX_KOR.get(int(ctxv[i]),'기본');act=str(action[i]) if action[i] else ''
        p.append(f"<b>📍{act}</b> ({cf[i]:.0f}%) ES:{esv[i]:+.1f} [{cl}]")
        rsn=str(reason[i])
        if rsn:
            rc='#6EE7B7' if 'BUY' in str(jg[i]) or '매수' in act else('#FCA5A5' if 'SELL' in str(jg[i]) or '매도' in act else '#FCD34D')
            p.append(f"<span style='color:{rc};font-size:11px'>💬 {rsn}</span>")
        p.append(f"WT:{wt[i]:.0f} RSI:{rs[i]:.0f} MFI:{mf[i]:.0f} UT:{'B' if ut[i]==1 else 'S' if ut[i]==-1 else '-'} Hull:{'🟢' if hma[i] else '🔴'}")
        if abs(pred[i])>3:p.append(f"<span style='color:{'#6EE7B7' if pred[i]>0 else '#FCA5A5'}'>🔮예측:{pred[i]:+.1f}</span>")
        vp=[]
        for cm in COMMITTEE_NAMES:
            v=cmv[cm][i];s=cms[cm][i];ic=COMMITTEE_ICONS.get(cm,'•')
            if v==1:vp.append(f"<span style='color:#6EE7B7'>{ic}B{s:+.0f}</span>")
            elif v==-1:vp.append(f"<span style='color:#FCA5A5'>{ic}S{s:+.0f}</span>")
            elif v==-99:vp.append(f"<span style='color:#475569'>{ic}—</span>")
            else:vp.append(f"<span style='color:#FCD34D'>{ic}N{s:+.0f}</span>")
        p.append(' '.join(vp))
        vs=str(veto[i]) if veto[i] else ''
        if vs:p.append(f"<span style='color:#FCA5A5'>🚫{vs}</span>")
        if lv_v[i]!='중립' or lgv[i]!='비추세/횡보':p.append(f"⏳{lv_v[i]}|📊{lgv[i]}")
        if bar_sb[i] or bar_ss[i]:
            p.append("─"*28)
            for l,d in bar_sb[i]:p.append(f"<span style='color:#6EE7B7'>⭐{l}: {d}</span>")
            for l,d in bar_ss[i]:p.append(f"<span style='color:#FCA5A5'>⭐{l}: {d}</span>")
        if bar_cs[i]:
            p.append("─"*28)
            for l,d,dr in bar_cs[i]:
                c='#6EE7B7' if dr=='buy' else('#FCA5A5' if dr=='sell' else '#FCD34D')
                p.append(f"<span style='color:{c}'>🎯{l}: {d}</span>")
        bs=bar_buy[i];ss=bar_sell[i];ns=bar_neutral[i]
        if bs or ss or ns:p.append("─"*28)
        if bs:
            p.append(f"<span style='color:#6EE7B7'><b>▲매수({len(bs)})</b></span>")
            for l,d in bs:p.append(f"<span style='color:#6EE7B7'> {l} <span style='color:#94A3B8;font-size:10px'>({d})</span></span>")
        if ss:
            p.append(f"<span style='color:#FCA5A5'><b>▼매도({len(ss)})</b></span>")
            for l,d in ss:p.append(f"<span style='color:#FCA5A5'> {l} <span style='color:#94A3B8;font-size:10px'>({d})</span></span>")
        if ns:
            p.append(f"<span style='color:#FCD34D'><b>◆중립({len(ns)})</b></span>")
            for l,d in ns:p.append(f"<span style='color:#FCD34D'> {l} <span style='color:#94A3B8;font-size:10px'>({d})</span></span>")
        texts.append("<br>".join(p))
    return texts

def _collect_strong_markers(dc):
    idx=dc.index;sb=pd.Series(False,index=idx);ss=pd.Series(False,index=idx)
    for sn in STRONG_BUY_SIGS:
        if sn in dc.columns:sb|=dc[sn].fillna(False)
    for sn in STRONG_SELL_SIGS:
        if sn in dc.columns:ss|=dc[sn].fillna(False)
    return sb,ss

def _sig_marker(fig,dc,sn,row,y,clr,sym,sz,lbl):
    reg=SIGNAL_REGISTRY.get(sn) or COMBINED_SCAN_REGISTRY.get(sn,{})
    if sn not in dc.columns:return
    mask=dc[sn].fillna(False)
    if not mask.any():return
    sr=dc[mask];yv=y[mask] if isinstance(y,pd.Series) else pd.Series(y,index=dc.index)[mask]
    valid=yv.notna()
    if not valid.any():return
    sr=sr[valid];yv=yv[valid];kor=reg.get('kor','');desc=reg.get('desc','')
    ht=f"<b>{lbl}</b> ({kor})<br><span style='color:#94A3B8'>{desc}</span><br>%{{x|%Y-%m-%d}}<extra></extra>" if kor else f"<b>{lbl}</b><br>%{{x|%Y-%m-%d}}<extra></extra>"
    fig.add_trace(go.Scatter(x=sr.index,y=yv,mode='markers',marker=dict(symbol=sym,size=sz,color=clr,line=dict(width=1.5,color='#FFF'),opacity=.95),name=lbl,showlegend=False,hovertemplate=ht),row=row,col=1)

def build_chart(dc,ticker):
    mac={20:'#f1c40f',50:'#e74c3c',200:'#2ecc71'}
    fig=make_subplots(rows=8,cols=1,shared_xaxes=True,vertical_spacing=0.02,row_heights=[.32,.04,.09,.09,.09,.09,.09,.19],subplot_titles=(ticker,"Vol","WaveTrend","MACD","Money Flow","Stoch Slow","Squeeze Mom","5-Committee Ensemble"))
    hover=_build_candle_hover(dc)
    fig.add_trace(go.Candlestick(x=dc.index,open=dc['Open'],high=dc['High'],low=dc['Low'],close=dc['Close'],name="Price",increasing_line_color='#00E676',decreasing_line_color='#FF1744',increasing_fillcolor='rgba(0,230,118,.8)',decreasing_fillcolor='rgba(255,23,68,.8)',text=hover,hoverinfo='text',hoverlabel=dict(bgcolor='rgba(11,14,20,.97)',bordercolor='#334155',font=dict(size=11,family='Pretendard',color='#F1F5F9'),align='left')),row=1,col=1)
    for mp in [20,50,200]:fig.add_trace(go.Scatter(x=dc.index,y=dc[f'MA{mp}'],line=dict(color=mac[mp],width=1.2),name=f'{mp}MA',hoverinfo='skip',showlegend=(mp==200)),row=1,col=1)
    for mc,clr,nm in [(dc['ST_Direction']==1,'#00E676','ST▲'),(dc['ST_Direction']==-1,'#FF1744','ST▼')]:fig.add_trace(go.Scatter(x=dc.index,y=dc['SuperTrend'].where(mc),line=dict(color=clr,width=2),name=nm,connectgaps=False,hoverinfo='skip',showlegend=False),row=1,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['BB_Up'],line=dict(color='#475569',width=1,dash='dot'),name='BB',hoverinfo='skip',showlegend=False),row=1,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['BB_Low'],line=dict(color='#475569',width=1,dash='dot'),fill='tonexty',fillcolor='rgba(71,85,105,.06)',hoverinfo='skip',showlegend=False),row=1,col=1)
    if 'HMA' in dc.columns:
        hup=dc.get('HMA_Rising',pd.Series(False,index=dc.index)).fillna(False)
        fig.add_trace(go.Scatter(x=dc.index,y=dc['HMA'].where(hup),line=dict(color='#00E676',width=2.5),name='HMA▲',connectgaps=False,hoverinfo='skip'),row=1,col=1)
        fig.add_trace(go.Scatter(x=dc.index,y=dc['HMA'].where(~hup),line=dict(color='#FF1744',width=2.5),name='HMA▼',connectgaps=False,hoverinfo='skip',showlegend=False),row=1,col=1)
    if 'UTBot_Stop' in dc.columns:
        ub=dc['UTBot_Dir']==1;us=dc['UTBot_Dir']==-1
        fig.add_trace(go.Scatter(x=dc.index,y=dc['UTBot_Stop'].where(ub),line=dict(color='rgba(0,230,118,.5)',width=2,dash='dot'),name='UTBot▲',connectgaps=False,hoverinfo='skip'),row=1,col=1)
        fig.add_trace(go.Scatter(x=dc.index,y=dc['UTBot_Stop'].where(us),line=dict(color='rgba(255,23,68,.5)',width=2,dash='dot'),name='UTBot▼',connectgaps=False,hoverinfo='skip',showlegend=False),row=1,col=1)
    for sn,clr,sym,sz,lbl in [('Hull_Turn_Bull','#00E676','circle',8,'🟢Hull▲'),('Hull_Turn_Bear','#FF1744','circle',8,'🔴Hull▼'),('UTBot_Buy','#00E676','triangle-up',12,'🤖UTBot▲'),('UTBot_Sell','#FF1744','triangle-down',12,'🤖UTBot▼'),('VuManChu_Bull','#00E676','diamond',12,'💎VuMC▲'),('VuManChu_Bear','#FF1744','diamond',12,'💎VuMC▼')]:
        yoff=dc['Low']-dc['ATR']*(0.8 if 'Hull' in sn else 1.2 if 'UTBot' in sn else 1.8) if 'Bull' in sn or 'Buy' in sn else dc['High']+dc['ATR']*(0.8 if 'Hull' in sn else 1.2 if 'UTBot' in sn else 1.8)
        _sig_marker(fig,dc,sn,1,yoff,clr,sym,sz,lbl)
    sb,ss=_collect_strong_markers(dc)
    if sb.any():
        sr=dc[sb];yv=sr['Low']-sr['ATR']*2;ht=[]
        for bi in sr.index:
            br=[SIGNAL_REGISTRY.get(s,COMBINED_SCAN_REGISTRY.get(s,{})).get('kor',s) for s in STRONG_BUY_SIGS if s in dc.columns and dc.loc[bi,s]]
            ht.append(f"<b>⭐강력매수</b><br><span style='color:#94A3B8'>{', '.join(br[:5]) or '다중강세'}</span><br>{bi.strftime('%Y-%m-%d')}")
        fig.add_trace(go.Scatter(x=sr.index,y=yv,mode='markers',marker=dict(symbol='star',size=8,color='#FFD700',line=dict(width=2,color='#00E676'),opacity=.95),name='⭐강력매수',hovertemplate="%{text}<extra></extra>",text=ht),row=1,col=1)
    if ss.any():
        sr=dc[ss];yv=sr['High']+sr['ATR']*2;ht=[]
        for bi in sr.index:
            br=[SIGNAL_REGISTRY.get(s,COMBINED_SCAN_REGISTRY.get(s,{})).get('kor',s) for s in STRONG_SELL_SIGS if s in dc.columns and dc.loc[bi,s]]
            ht.append(f"<b>⭐강력매도</b><br><span style='color:#94A3B8'>{', '.join(br[:5]) or '다중약세'}</span><br>{bi.strftime('%Y-%m-%d')}")
        fig.add_trace(go.Scatter(x=sr.index,y=yv,mode='markers',marker=dict(symbol='star',size=8,color='#FFD700',line=dict(width=2,color='#FF1744'),opacity=.95),name='⭐강력매도',hovertemplate="%{text}<extra></extra>",text=ht),row=1,col=1)
    # R2 Vol
    bb=dc['Close']<dc['Open'];fig.add_trace(go.Bar(x=dc.index,y=dc['Volume'],marker_color=np.where(bb,'rgba(255,23,68,.5)','rgba(0,230,118,.5)').tolist(),name="Vol",opacity=.8,hoverinfo='skip',showlegend=False),row=2,col=1)
    # R3 WT
    fig.add_trace(go.Scatter(x=dc.index,y=dc['WT1'],line=dict(color='#00E676',width=2),name="WT1",hovertemplate="WT1:%{y:.1f}<extra></extra>"),row=3,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['WT2'],line=dict(color='#FF1744',width=1.5,dash='dot'),hoverinfo='skip',showlegend=False),row=3,col=1)
    wd=dc['WT1']-dc['WT2'];fig.add_trace(go.Bar(x=dc.index,y=wd,marker_color=np.where(wd>=0,'rgba(0,230,118,.25)','rgba(255,23,68,.25)').tolist(),hoverinfo='skip',showlegend=False),row=3,col=1)
    for y_,c_,d_ in [(OB1,'#FF5252','solid'),(0,'#475569','dot'),(OS1,'#4FC3F7','solid')]:fig.add_hline(y=y_,line_dash=d_,line_color=c_,line_width=1,row=3,col=1)
    for sn,clr,sym,sz,lbl in [('Gold_Dot','#FFD700','star',14,'🏆Gold'),('Green_Dot_T1','#00E676','circle',10,'🟢T1'),('Green_Dot_T2','#69F0AE','circle',8,'🟩T2'),('Blood_Diamond','#DC143C','star',14,'🩸Blood'),('Red_Dot_T1','#FF1744','circle',10,'🔴T1'),('Red_Dot_T2','#FF5252','circle',8,'🟥T2'),('Bull_Divergence','#AA00FF','triangle-up',10,'📈BullDiv'),('Bear_Divergence','#AA00FF','triangle-down',10,'📉BearDiv'),('RSI_Bull_Divergence','#CE93D8','triangle-up',8,'📊RSIDiv▲'),('RSI_Bear_Divergence','#CE93D8','triangle-down',8,'📊RSIDiv▼')]:_sig_marker(fig,dc,sn,3,dc['WT1'],clr,sym,sz,lbl)
    # R4 MACD
    fig.add_trace(go.Scatter(x=dc.index,y=dc['MACD_Line'],line=dict(color='#29B6F6',width=1.5),name="MACD",hovertemplate="MACD:%{y:.3f}<extra></extra>"),row=4,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['MACD_Signal'],line=dict(color='#FFA726',width=1.5),hoverinfo='skip',showlegend=False),row=4,col=1)
    mh_=dc['MACD_Hist'];fig.add_trace(go.Bar(x=dc.index,y=mh_,marker_color=np.where(mh_>=0,'#26A69A','#EF5350').tolist(),opacity=.7,hoverinfo='skip',showlegend=False),row=4,col=1)
    fig.add_hline(y=0,line_color="#475569",line_width=1,row=4,col=1)
    for sn,clr,sym,sz,lbl in [('MACD_Cross_Buy','#00E676','triangle-up',10,'〽️MCD▲'),('MACD_Cross_Sell','#FF1744','triangle-down',10,'〽️MCD▼'),('MACD_Zero_Cross_Buy','#4CAF50','diamond',8,'⬆️MC0▲'),('MACD_Zero_Cross_Sell','#E57373','diamond',8,'⬇️MC0▼')]:_sig_marker(fig,dc,sn,4,dc['MACD_Line'],clr,sym,sz,lbl)
    # R5 MFI
    mfr=dc.get('MFI',pd.Series(50,index=dc.index));mfc=mfr-50;rmfi=dc.get('RSI_MFI',pd.Series(0,index=dc.index))
    fig.add_trace(go.Bar(x=dc.index,y=rmfi,marker_color=np.where(rmfi>=0,'rgba(0,230,118,.35)','rgba(255,23,68,.35)').tolist(),opacity=.7,hoverinfo='skip',showlegend=False),row=5,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=mfc,line=dict(color='#AB47BC',width=2.5),name="MFI",hovertemplate="MFI:%{customdata:.1f}<extra></extra>",customdata=mfr.values),row=5,col=1)
    fig.add_hrect(y0=30,y1=50,fillcolor="rgba(239,68,68,.08)",line_width=0,row=5,col=1);fig.add_hrect(y0=-50,y1=-30,fillcolor="rgba(16,185,129,.08)",line_width=0,row=5,col=1)
    for y_,c_,d_ in [(30,'#FF5252','dash'),(-30,'#4FC3F7','dash'),(0,'#475569','solid')]:fig.add_hline(y=y_,line_dash=d_,line_color=c_,line_width=1,row=5,col=1)
    for sn,clr,sym,sz,lbl in [('MF_Cross_Bull','#00E676','triangle-up',10,'💰MF▲'),('MF_Cross_Bear','#FF1744','triangle-down',10,'💸MF▼'),('MF_Bull_Div','#7C4DFF','diamond',10,'💹MFDiv▲'),('MF_Bear_Div','#E040FB','diamond',10,'💹MFDiv▼'),('CMF_Bull','#00BCD4','circle',8,'🌀CMF▲'),('CMF_Bear','#FF5722','circle',8,'🌀CMF▼')]:_sig_marker(fig,dc,sn,5,mfc,clr,sym,sz,lbl)
    # R6 Stoch
    slk=dc.get('SlowK',pd.Series(50,index=dc.index));sld=dc.get('SlowD',pd.Series(50,index=dc.index))
    fig.add_trace(go.Scatter(x=dc.index,y=slk,line=dict(color='#00BCD4',width=2),name="SlowK",hovertemplate="SlK:%{y:.1f}<extra></extra>"),row=6,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=sld,line=dict(color='#FF9800',width=1.5,dash='dot'),hoverinfo='skip',showlegend=False),row=6,col=1)
    fig.add_hrect(y0=80,y1=100,fillcolor="rgba(239,68,68,.08)",line_width=0,row=6,col=1);fig.add_hrect(y0=0,y1=20,fillcolor="rgba(16,185,129,.08)",line_width=0,row=6,col=1)
    for y_,c_,d_ in [(80,'#FF5252','dash'),(20,'#4FC3F7','dash'),(50,'#475569','dot')]:fig.add_hline(y=y_,line_dash=d_,line_color=c_,line_width=1,row=6,col=1)
    for sn,clr,sym,sz,lbl in [('StochSlow_Cross_Buy','#00E676','triangle-up',12,'🔄StSl▲'),('StochSlow_Cross_Sell','#FF1744','triangle-down',12,'🔄StSl▼'),('Stoch_Oversold','#69F0AE','square',6,'🟢StOS'),('Stoch_Overbought','#FF5252','square',6,'🔴StOB')]:_sig_marker(fig,dc,sn,6,slk,clr,sym,sz,lbl)
    # R7 SqMom
    sqm=dc.get('Squeeze_Momentum',pd.Series(0,index=dc.index));sqr=dc.get('Squeeze_Mom_Rising',pd.Series(False,index=dc.index)).fillna(False);sqp=dc.get('Squeeze_Mom_Positive',pd.Series(False,index=dc.index)).fillna(False);sqo=dc.get('Squeeze_On',pd.Series(False,index=dc.index)).fillna(False)
    sqc=np.where(sqp&sqr,'#00E676',np.where(sqp&~sqr,'#69F0AE',np.where(~sqp&sqr,'#FF8A80','#FF1744')))
    fig.add_trace(go.Bar(x=dc.index,y=sqm,marker_color=sqc.tolist(),name="SqMom",opacity=.85,hovertemplate="SqMom:%{y:.3f}<extra></extra>"),row=7,col=1)
    fig.add_hline(y=0,line_color="#475569",line_width=1,row=7,col=1)
    if sqo.any():
        smn=float(sqm.min()) if len(sqm)>0 else -0.1;dy=smn*1.1 if smn<0 else -0.05
        fig.add_trace(go.Scatter(x=dc.index[sqo],y=[dy]*int(sqo.sum()),mode='markers',marker=dict(symbol='circle',size=5,color='#000',line=dict(width=1,color='#FFC107'),opacity=.9),name='⚫SqON',hovertemplate="⚡Squeeze ON<br>%{x|%Y-%m-%d}<extra></extra>"),row=7,col=1)
    for sn,clr,sym,sz,lbl in [('Squeeze_Fire_Buy','#00FFFF','star-diamond',14,'💥SqFire▲'),('Squeeze_Fire_Sell','#FF6600','star-diamond',14,'🧨SqFire▼'),('Squeeze_Mom_Cross_Up','#00E676','diamond',10,'💥SqMom▲'),('Squeeze_Mom_Cross_Down','#FF1744','diamond',10,'💥SqMom▼')]:_sig_marker(fig,dc,sn,7,sqm,clr,sym,sz,lbl)
    # R8 Ensemble
    if 'Ensemble_Score' in dc.columns:
        es=dc['Ensemble_Score'];colors=np.where(es>=30,'#00E676',np.where(es>=10,'#69F0AE',np.where(es<=-30,'#FF1744',np.where(es<=-10,'#FF5252','#FFC107'))))
        cmd=[dc.get(f'CM_{cm}_EffScore',pd.Series(0,index=dc.index)).values for cm in COMMITTEE_NAMES];cma=np.column_stack(cmd) if cmd else np.zeros((len(dc),5))
        jgv=dc.get('Trade_Judgment',pd.Series('N/A',index=dc.index)).values;cfv=dc.get('Judgment_Confidence',pd.Series(0,index=dc.index)).values
        ctxv=dc.get('Market_Context',pd.Series(0,index=dc.index)).values;bav=dc.get('Buy_Agree',pd.Series(0,index=dc.index)).values;sav=dc.get('Sell_Agree',pd.Series(0,index=dc.index)).values
        fig.add_trace(go.Bar(x=dc.index,y=es,marker_color=colors.tolist(),name="Ensemble",opacity=.85,
            customdata=np.column_stack([jgv,cfv,bav,sav,cma[:,0],cma[:,1],cma[:,2],cma[:,3],cma[:,4],[CTX_KOR.get(int(c),'-') for c in ctxv]]),
            hovertemplate="<b>%{customdata[0]}</b> (%{customdata[1]:.0f}%) ES:%{y:+.1f}<br>B%{customdata[2]}:S%{customdata[3]} [%{customdata[9]}]<br>📈%{customdata[4]:+.0f} 🔥%{customdata[5]:+.0f} 💰%{customdata[6]:+.0f}<br>🏗️%{customdata[7]:+.0f} ⏳%{customdata[8]:+.0f}<extra></extra>"),row=8,col=1)
        fig.add_hline(y=0,line_color="#475569",line_width=1,row=8,col=1);fig.add_hline(y=JT.STRONG_BUY_TH,line_dash='dot',line_color='rgba(0,230,118,.3)',line_width=1,row=8,col=1);fig.add_hline(y=JT.STRONG_SELL_TH,line_dash='dot',line_color='rgba(255,23,68,.3)',line_width=1,row=8,col=1)
        ctx_colors={CTX_EXTREME_OS:'rgba(0,230,118,.06)',CTX_EXTREME_OB:'rgba(255,23,68,.06)',CTX_ACCUMULATION:'rgba(0,188,212,.06)',CTX_DISTRIBUTION:'rgba(255,87,34,.06)',CTX_STRONG_UP:'rgba(0,230,118,.03)',CTX_STRONG_DN:'rgba(255,23,68,.03)',CTX_BOTTOMING:'rgba(0,188,212,.04)',CTX_TOPPING:'rgba(255,152,0,.04)'}
        pc=-1;ss_=0;cvs=dc.get('Market_Context',pd.Series(0,index=dc.index)).values
        for ci in range(len(dc)):
            cur=int(cvs[ci])
            if cur!=pc:
                if pc in ctx_colors and ci>ss_:fig.add_vrect(x0=dc.index[ss_],x1=dc.index[ci-1],fillcolor=ctx_colors[pc],line_width=0,row=8,col=1)
                ss_=ci;pc=cur
        if pc in ctx_colors:fig.add_vrect(x0=dc.index[ss_],x1=dc.index[-1],fillcolor=ctx_colors[pc],line_width=0,row=8,col=1)
    fig.update_layout(template="plotly_dark",paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",margin=dict(l=2,r=2,t=40,b=2),height=1600,showlegend=True,hovermode="closest",legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="center",x=.5,font=dict(size=8,color='#94A3B8'),bgcolor='rgba(0,0,0,0)'))
    for i in range(1,9):fig.update_layout(**{(f'yaxis{i}' if i>1 else 'yaxis'):dict(gridcolor='rgba(51,65,85,.3)',tickfont=dict(size=9,color='#64748B'))})
    fig.update_yaxes(range=[-50,50],row=5,col=1);fig.update_yaxes(range=[0,100],row=6,col=1)
    ad=pd.date_range(start=dc.index[0],end=dc.index[-1],freq='D');nt=ad.difference(dc.index.normalize())
    fig.update_xaxes(rangeslider_visible=False,rangebreaks=[dict(values=nt.tolist())],gridcolor='rgba(51,65,85,.3)',tickfont=dict(size=9,color='#64748B'))
    for ann in fig['layout']['annotations']:ann['font']=dict(size=11,color='#94A3B8',family='Pretendard')
    return fig

def build_metadata(dc,ticker):
    lat=dc.iloc[-1];prev=dc.iloc[-2] if len(dc)>=2 else lat;pc=lat['Close']-prev['Close'];pp=pc/(prev['Close']+1e-10)*100
    LN=['Trend','Momentum','Candle','BB','Volume','MF','Pattern','Combined','Leading','Lagging']
    bl={n:_sf(lat.get(f'BL_{n}',0)) for n in LN};sl={n:_sf(lat.get(f'SL_{n}',0)) for n in LN}
    acs=[]
    for cn,ccfg in COMBINED_SCAN_REGISTRY.items():
        if cn in dc.columns and dc[cn].tail(5).any():
            ld=dc[cn].tail(5)[dc[cn].tail(5)].index[-1];acs.append({'name':ccfg['name'],'kor':ccfg['kor'],'dir':ccfg['dir'],'tier':ccfg['tier'],'icon':ccfg['icon'],'color':ccfg['color'],'win':ccfg['win'],'date':ld.strftime('%m/%d'),'is_today':(dc.index[-1]-ld).days==0,'days_ago':(dc.index[-1]-ld).days})
    acs.sort(key=lambda x:(x['tier'],x['days_ago']))
    recent=[]
    for ir,row in dc.tail(15).iterrows():
        ds=ir.strftime('%m/%d')
        for col,cfg in SIGNAL_REGISTRY.items():
            if col in dc.columns and row.get(col,False):recent.append((cfg['icon'],cfg['kor'],ds,cfg['dir'],False))
        for col,cfg in COMBINED_SCAN_REGISTRY.items():
            if col in dc.columns and row.get(col,False):recent.append((cfg['icon'],cfg['kor'],ds,cfg['dir'],True))
    rg=int(lat.get('Regime',0));rl={2:'STRONG BULL 🟢🟢',1:'BULL 🟢',0:'NEUTRAL ⚪',-1:'BEAR 🔴',-2:'STRONG BEAR 🔴🔴'}.get(rg,'N/A')
    committee={}
    for cm in COMMITTEE_NAMES:vv=int(_sf(lat.get(f'CM_{cm}_Vote',0)));committee[cm]={'score':_sf(lat.get(f'CM_{cm}_EffScore',0)),'conviction':_sf(lat.get(f'CM_{cm}_EffConv',0)),'vote':'BUY' if vv==1 else('SELL' if vv==-1 else('ABSTAIN' if vv==-99 else 'NEUTRAL')),'vote_int':vv}
    ctx_code=int(_sf(lat.get('Market_Context',0)))
    return {'ticker':ticker.upper(),'price':_sf(lat['Close']),'price_change':pc,'price_change_pct':pp,'volume':_sf(lat['Volume']),'avg_volume':_sf(dc['Volume'].rolling(20).mean().iloc[-1]),
        'wt1':_sf(lat.get('WT1')),'rsi':_sf(lat.get('RSI'),50),'mfi':_sf(lat.get('MFI'),50),'stochk':_sf(lat.get('StochK'),50),'adx':_sf(lat.get('ADX')),'atr':_sf(lat.get('ATR')),'atr_pct':_sf(lat.get('ATR'))/(max(_sf(lat['Close']),0.01))*100,
        'macd_hist':_sf(lat.get('MACD_Hist')),'cmf':_sf(lat.get('CMF')),'composite_accel':_sf(lat.get('Composite_Accel')),'rs_ratio':_sf(lat.get('RS_Ratio'),1),
        'regime':rg,'regime_label':rl,'regime_score':_sf(lat.get('Regime_Score')),'last_date':dc.index[-1].strftime('%Y-%m-%d'),'squeeze_on':bool(lat.get('Squeeze_On',False)),
        'buy_total':_sf(lat.get('Buy_Total')),'sell_total':_sf(lat.get('Sell_Total')),'buy_active':int(_sf(lat.get('Buy_Active_Layers'))),'sell_active':int(_sf(lat.get('Sell_Active_Layers'))),
        'buy_layers':bl,'sell_layers':sl,'judgment':str(lat.get('Trade_Judgment','NEUTRAL')),'confidence':_sf(lat.get('Judgment_Confidence')),
        'ensemble_score':_sf(lat.get('Ensemble_Score')),'prediction_boost':_sf(lat.get('Prediction_Boost')),
        'leading_verdict':str(lat.get('Leading_Verdict','중립')),'lagging_verdict':str(lat.get('Lagging_Verdict','비추세/횡보')),
        'setup_pressure_buy':_sf(lat.get('Setup_Pressure_Buy')),'setup_pressure_sell':_sf(lat.get('Setup_Pressure_Sell')),
        'utbot_dir':int(_sf(lat.get('UTBot_Dir'))),'hma_rising':bool(lat.get('HMA_Rising',False)),'slowk':_sf(lat.get('SlowK'),50),'squeeze_mom':_sf(lat.get('Squeeze_Momentum')),
        'context':ctx_code,'context_label':CTX_KOR.get(ctx_code,'기본'),'committee':committee,
        'buy_agree':int(_sf(lat.get('Buy_Agree'))),'sell_agree':int(_sf(lat.get('Sell_Agree'))),'veto_flags':str(lat.get('Veto_Flags','')),'reversal_synergy':_sf(lat.get('Reversal_Synergy')),
        'judgment_reason':str(lat.get('Judgment_Reason','')),'judgment_detail':str(lat.get('Judgment_Detail','')),'action_label':str(lat.get('Action_Label','')),
        'ma50':_sf(lat.get('MA50')),'ma200':_sf(lat.get('MA200')),'vp_poc':_sf(lat.get('VP_POC')),'vp_vah':_sf(lat.get('VP_VAH')),'vp_val':_sf(lat.get('VP_VAL')),
        'percent_b':_sf(lat.get('Percent_B'),0.5),'rsi_mfi':_sf(lat.get('RSI_MFI')),'bb_up':_sf(lat.get('BB_Up')),'bb_low':_sf(lat.get('BB_Low')),
        'ema8':_sf(lat.get('EMA8')),'ema21':_sf(lat.get('EMA21')),'obv_trend':'rising' if _sf(lat.get('OBV'))>_sf(dc['OBV'].rolling(20).mean().iloc[-1]) else 'falling',
        'combined_scans':acs,'recent_signals':recent}

# ━━━ UI ━━━
def render_price_header(m):
    chg=m['price_change'];cp=m['price_change_pct'];cc='price-change-up' if chg>=0 else 'price-change-down';ci='▲' if chg>=0 else '▼'
    vr_=m['volume']/max(m['avg_volume'],1);jg=m['judgment'];cf=m['confidence'];es=m.get('ensemble_score',0)
    jc='#34D399' if 'BUY' in jg else('#F87171' if 'SELL' in jg else '#FCD34D')
    act=m.get('action_label','');rsn=m.get('judgment_reason','')
    specs=[(jc,f"📍{act}({cf:.0f}%)"),('ind-b' if m['wt1']<-20 else('ind-s' if m['wt1']>20 else 'ind-n'),f"WT{m['wt1']:.0f}"),('ind-b' if m['rsi']<40 else('ind-s' if m['rsi']>60 else 'ind-n'),f"RSI{m['rsi']:.0f}"),('ind-b' if vr_>1.5 else 'ind-n',f"Vol{vr_:.1f}x"),('ind-b' if m['adx']>25 else 'ind-n',f"ADX{m['adx']:.0f}"),('ind-b' if m.get('utbot_dir',0)==1 else('ind-s' if m.get('utbot_dir',0)==-1 else 'ind-n'),'🤖B' if m.get('utbot_dir',0)==1 else('🤖S' if m.get('utbot_dir',0)==-1 else '🤖—')),('ind-b' if m.get('hma_rising') else 'ind-s','🟢H' if m.get('hma_rising') else '🔴H')]
    ih="".join([f"<span class='ind-mini {c}'>{l}</span>" for c,l in specs])
    rsn_html=f"<p style='color:#94A3B8;font-size:.82rem;margin:6px 0 0'>💬 {rsn}</p>" if rsn else ""
    st.markdown(f"""<div class="price-header"><p style="color:#64748B;font-size:.8rem;margin:0">🚦 {m['ticker']} · {m['last_date']} · <b style="color:#A5B4FC">{m['regime_label']}</b> · <span style='color:#A5B4FC'>🌐{m.get('context_label','기본')}</span></p>
        <p class="price-big" style="color:#F8FAFC">${m['price']:.2f}<span class="{cc}" style="font-size:1.1rem;margin-left:10px;font-weight:700">{ci}{abs(chg):.2f}({abs(cp):.2f}%)</span></p>{rsn_html}
        <div style="margin-top:10px;display:flex;gap:4px;flex-wrap:wrap">{ih}</div></div>""",unsafe_allow_html=True)
    c1,c2,c3,c4=st.columns(4)
    with c1:st.metric("Ensemble",f"{es:+.1f}",delta=f"B{m.get('buy_agree',0)}:S{m.get('sell_agree',0)}")
    with c2:st.metric("BUY(10L)",f"{m['buy_total']:.1f}",delta=f"{m['buy_active']}/{NUM_LAYERS}")
    with c3:st.metric("SELL(10L)",f"{m['sell_total']:.1f}",delta=f"{m['sell_active']}/{NUM_LAYERS}",delta_color="inverse")
    with c4:st.metric("Conf",f"{m['confidence']:.0f}%",delta=f"⏳{m['leading_verdict']}")

def render_judgment_card(m):
    jg=m['judgment'];es=m.get('ensemble_score',0);cf=m['confidence']
    cc='score-card-buy' if 'BUY' in jg else('score-card-sell' if 'SELL' in jg else 'score-card-neutral')
    jc='#34D399' if 'BUY' in jg else('#F87171' if 'SELL' in jg else '#FCD34D')
    labels={'STRONG_BUY':'🟢🟢🟢 STRONG BUY','BUY':'🟢🟢 BUY','WATCH_BUY':'🟡🟢 WATCH BUY','NEUTRAL':'⚪ NEUTRAL','MIXED':'🟠 MIXED','WATCH_SELL':'🟡🔴 WATCH SELL','SELL':'🔴🔴 SELL','STRONG_SELL':'🔴🔴🔴 STRONG SELL'}
    ba=m.get('buy_agree',0);sa=m.get('sell_agree',0);veto=m.get('veto_flags','');syn=m.get('reversal_synergy',0);pred=m.get('prediction_boost',0)
    reason=m.get('judgment_reason','');detail=m.get('judgment_detail','');action=m.get('action_label','')
    reason_html=""
    if reason:reason_html=f"<div class='reason-card'><p style='color:{jc};font-weight:800;font-size:.95rem;margin:0 0 4px'>🏷️ {action}</p><p style='color:#E8ECF1;font-size:.88rem;margin:0 0 4px'>💬 {reason}</p><p style='color:#94A3B8;font-size:.78rem;margin:0'>📋 {detail}</p></div>"
    veto_html=f"<div style='margin-top:6px'><span style='background:rgba(239,68,68,.15);color:#FCA5A5;padding:3px 8px;border-radius:6px;font-size:.7rem;font-weight:700'>🚫 {veto}</span></div>" if veto else ""
    extra=""
    if abs(syn)>5:extra+=f"<span style='color:{'#34D399' if syn>0 else '#F87171'};font-size:.8rem;margin:0 4px'>🔄시너지:{syn:+.1f}</span>"
    if abs(pred)>3:extra+=f"<span style='color:{'#34D399' if pred>0 else '#F87171'};font-size:.8rem;margin:0 4px'>🔮예측:{pred:+.1f}</span>"
    st.markdown(f"""<div class="score-card {cc}"><p style="font-size:2rem;font-weight:800;color:{jc};margin:0">{labels.get(jg,jg)}</p>
        <div style="display:flex;align-items:center;gap:10px;justify-content:center;margin-top:8px"><div style="flex:0 0 200px;height:8px;background:#1E293B;border-radius:4px;overflow:hidden"><div style="width:{min(cf,100)}%;height:8px;background:{jc};border-radius:4px"></div></div><span style="color:{jc};font-weight:800;font-size:1.1rem">{cf:.0f}%</span></div>
        {reason_html}
        <div style="display:flex;justify-content:center;gap:32px;margin-top:14px"><div><p style="color:#64748B;font-size:.7rem;margin:0">Ensemble</p><p style="color:{'#34D399' if es>0 else '#F87171' if es<0 else '#FCD34D'};font-size:1.4rem;font-weight:800;margin:2px 0">{es:+.1f}</p></div>
        <div style="border-left:1px solid rgba(255,255,255,.08);padding-left:32px"><p style="color:#64748B;font-size:.7rem;margin:0">찬성</p><p style="color:#F8FAFC;font-size:1.4rem;font-weight:800;margin:2px 0">B{ba}:S{sa}</p></div>
        <div style="border-left:1px solid rgba(255,255,255,.08);padding-left:32px"><p style="color:#64748B;font-size:.7rem;margin:0">컨텍스트</p><p style="color:#A5B4FC;font-size:1rem;font-weight:700;margin:2px 0">🌐{m.get('context_label','기본')}</p></div></div>
        <div style='margin-top:8px'>{extra}</div>{veto_html}</div>""",unsafe_allow_html=True)

def render_committee_panel(m):
    committee=m.get('committee',{})
    if not committee:return
    ctx_code=m.get('context',0);ctx_name=CTX_LABELS.get(ctx_code,'default');weights=CONTEXT_WEIGHTS.get(ctx_name,CONTEXT_WEIGHTS['default'])
    st.markdown(f"#### 🌐 컨텍스트: {m.get('context_label','기본')}")
    cols=st.columns(5)
    for ci,cm in enumerate(COMMITTEE_NAMES):
        data=committee.get(cm,{});score=data.get('score',0);conv=data.get('conviction',0);vote=data.get('vote','NEUTRAL');weight=weights[ci] if ci<len(weights) else 0.2
        with cols[ci]:st.metric(label=f"{COMMITTEE_ICONS.get(cm,'•')} {cm} ×{weight:.0%}",value=f"{score:+.0f}",delta=f"{vote} ({conv:.0f}%)",delta_color="normal" if score>0 else "inverse" if score<0 else "off")
    veto=m.get('veto_flags','')
    if veto:st.warning(f"🚫 **거부권:** {veto}")
    syn=m.get('reversal_synergy',0)
    if abs(syn)>5:st.info(f"🔄 **교차시너지:** {syn:+.1f}")

def render_10layer_bars(m):
    LN=['Trend','Momentum','Candle','BB','Volume','MF','Pattern','Combined','Leading','Lagging'];icons={'Trend':'📈','Momentum':'🔥','Candle':'🕯️','BB':'📊','Volume':'📦','MF':'💰','Pattern':'⭐','Combined':'🎯','Leading':'⏳','Lagging':'📊'}
    c1,c2=st.columns(2)
    for col_st,side,data,color,fcls in [(c1,'BUY',m['buy_layers'],'#34D399','layer-fill-b'),(c2,'SELL',m['sell_layers'],'#F87171','layer-fill-s')]:
        with col_st:
            st.markdown(f"<p style='color:{color};font-weight:700;font-size:.85rem'>{'▲' if side=='BUY' else '▼'} {side}</p>",unsafe_allow_html=True)
            for n in LN:v_=data.get(n,0);pct=min(max(v_,0)/12*100,100);op='1' if v_>0 else '.3';st.markdown(f"<div class='layer-row'><span style='color:#94A3B8;font-size:.78rem;opacity:{op};width:80px'>{icons.get(n,'•')} {n}</span><div class='layer-bar'><div class='{fcls}' style='width:{pct}%;opacity:{op}'></div></div><span style='color:{color};font-weight:700;font-size:.78rem;width:35px;text-align:right;opacity:{op}'>{v_:.1f}</span></div>",unsafe_allow_html=True)

def render_leading_lagging(m):
    lv=m['leading_verdict'];lgv=m['lagging_verdict'];ac=m['composite_accel']
    lc='#34D399' if '상승' in lv else('#F87171' if '하락' in lv else '#FCD34D');lgc='#34D399' if '상승' in lgv else('#F87171' if '하락' in lgv else '#FCD34D')
    st.markdown(f"""<div style="background:rgba(255,255,255,.03);border:1px solid #1E293B;border-radius:12px;padding:14px;margin-bottom:10px"><p style="font-weight:700;color:#A5B4FC;margin:0 0 8px">⏳ 선행지표</p><p style="color:{lc};font-weight:800;font-size:1.1rem;margin:0">{lv}</p>
        <div style="display:flex;gap:10px;margin-top:8px;flex-wrap:wrap"><span style="color:#94A3B8;font-size:.8rem">가속도:<b style="color:{'#34D399' if ac>0 else '#F87171'}">{ac:+.2f}</b></span><span style="color:#94A3B8;font-size:.8rem">UT:{'🤖매수' if m.get('utbot_dir',0)==1 else('🤖매도' if m.get('utbot_dir',0)==-1 else '🤖중립')}</span><span style="color:#94A3B8;font-size:.8rem">Hull:{'🟢상승' if m.get('hma_rising') else '🔴하락'}</span></div></div>""",unsafe_allow_html=True)
    st.markdown(f"""<div style="background:rgba(255,255,255,.03);border:1px solid #1E293B;border-radius:12px;padding:14px"><p style="font-weight:700;color:#A5B4FC;margin:0 0 8px">📊 후행지표</p><p style="color:{lgc};font-weight:800;font-size:1.1rem;margin:0">{lgv}</p>
        <div style="display:flex;gap:16px;margin-top:8px"><span style="color:#94A3B8;font-size:.8rem">국면:<b>{m['regime_label']}</b></span><span style="color:#94A3B8;font-size:.8rem">RS:<b style="color:{'#34D399' if m['rs_ratio']>1.03 else('#F87171' if m['rs_ratio']<.97 else '#FCD34D')}">{m['rs_ratio']:.3f}</b></span></div></div>""",unsafe_allow_html=True)

def render_combined_scans(m):
    scans=m.get('combined_scans',[])
    if not scans:st.info("🔍 활성 CS 없음");return
    bn=sum(1 for s in scans if s['dir']=='buy');sn_=sum(1 for s in scans if s['dir']=='sell');t1=sum(1 for s in scans if s['tier']==1)
    hc='#FFD700' if t1>0 else('#00E676' if bn>sn_ else('#FF1744' if sn_>bn else '#FFC107'))
    st.markdown(f"<div style='background:rgba(255,215,0,.06);border:1px solid {hc}33;border-radius:12px;padding:12px;margin-bottom:10px'><span style='font-size:1.2rem;font-weight:800;color:{hc}'>🎯 CS:{len(scans)}개</span> <span style='color:#94A3B8;margin-left:12px'>T1:{t1} B:{bn} S:{sn_}</span></div>",unsafe_allow_html=True)
    for s in scans:
        tb={1:'🥇T1',2:'🥈T2',3:'🥉T3'}.get(s['tier'],'T?');dc_='#34D399' if s['dir']=='buy' else('#F87171' if s['dir']=='sell' else '#FFC107')
        bg='rgba(0,230,118,.04)' if s['dir']=='buy' else('rgba(255,23,68,.04)' if s['dir']=='sell' else 'rgba(255,193,7,.04)')
        td="<span style='background:#FFD700;color:#000;padding:2px 6px;border-radius:4px;font-size:.65rem;font-weight:700'>TODAY</span>" if s['is_today'] else f"<span style='color:#64748B;font-size:.75rem'>{s['date']}</span>"
        st.markdown(f"<div class='cs-card' style='background:{bg};border-color:{dc_}'><div style='display:flex;justify-content:space-between;align-items:center'><span style='color:{dc_};font-weight:700'>{s['icon']} {s['kor']} <span style='color:#64748B;font-size:.7rem'>{tb}</span></span><div>{td} <span style='color:#4FC3F7;font-size:.65rem;margin-left:6px'>승률:{s['win']}</span></div></div></div>",unsafe_allow_html=True)

def render_analysis(msg):
    m,fj=msg.get('meta'),msg.get('fig_json')
    if m:render_price_header(m)
    if m or fj:
        t0,t1,t2,t3,t4,t5=st.tabs(["차트","위원회","매매판단","Combined Scan","선행/후행","기업 상세"])
        with t0:
            if fj:fig=go.Figure(json.loads(fj));st.plotly_chart(fig,use_container_width=True,theme=None,config={'displaylogo':False,'modeBarButtonsToRemove':['lasso2d','select2d']});st.caption("💡 캔들 호버 → 판단이유 + 모든 시그널 + 위원회 투표")
        with t1:
            if m:render_judgment_card(m);st.markdown("#### 🏛️ 5-Committee");render_committee_panel(m)
        with t2:
            if m:st.markdown("#### 📊 10-Layer (참고)");render_10layer_bars(m)
        with t3:
            if m:render_combined_scans(m)
        with t4:
            if m:render_leading_lagging(m)
        with t5:
            if m:render_company_details(m['ticker'])

print("✅ Part 3/4 완료")

# ══════════════════════════════════════════════════════════════
#  CipherX V14.2 — PART 4/4
#  AI프롬프트(이유+시너지), 스캐너(이유표시), 메인루프
# ══════════════════════════════════════════════════════════════

def build_prompt_text(dc,meta):
    m=meta;rd=dc.tail(60);prices=", ".join([f"'{d.strftime('%m/%d')}:{r['Close']:.2f}'" for d,r in rd.iterrows()])
    vr=m['volume']/max(m['avg_volume'],1)
    ba=f"📌 [A. 가격]\n{prices}\n\n현재가:${m['price']:.2f} ({m['price_change_pct']:+.2f}%)\n거래량:{m['volume']:,.0f} ({vr:.1f}x)\nATR:${m['atr']:.2f} ({m['atr_pct']:.1f}%)\n"
    mas=f"MA50=${m['ma50']:.2f}, MA200=${m['ma200']:.2f}" if m['ma50']>0 else "MA=데이터부족"
    vps=f"POC=${m['vp_poc']:.2f}, VAH=${m['vp_vah']:.2f}, VAL=${m['vp_val']:.2f}" if m['vp_poc']>0 else "VP=데이터부족"
    bbs=f"BB상단=${m.get('bb_up',0):.2f}, BB하단=${m.get('bb_low',0):.2f}" if m.get('bb_up',0)>0 else ""
    bb=f"📌 [B. 지표]\n모멘텀:RSI={m['rsi']:.1f},MFI={m['mfi']:.1f},WT={m['wt1']:.1f},StK={m['stochk']:.1f},SlK={m.get('slowk',50):.1f}\n추세:ADX={m['adx']:.1f},MACD_H={m['macd_hist']:.4f}\n자금:CMF={m['cmf']:.3f},RSI_MFI={m.get('rsi_mfi',0):.1f},OBV={m.get('obv_trend','N/A')}\n구조:BB%B={m.get('percent_b',.5):.2f},{bbs}\n  {vps}\n  {mas}\n보조:UTBot={'매수' if m.get('utbot_dir',0)==1 else '매도' if m.get('utbot_dir',0)==-1 else '미정'},Hull={'상승' if m.get('hma_rising') else '하락'},SqMom={m.get('squeeze_mom',0):.3f}\nRS={m['rs_ratio']:.3f}\n"
    sls=[]
    for ir,row in dc.tail(20).iterrows():
        dd=ir.strftime('%m/%d');ds=[]
        for k,v in SIGNAL_REGISTRY.items():
            if row.get(k,False):ds.append(f"{'▲' if v['dir']=='buy' else '▼' if v['dir']=='sell' else '•'}{v['kor']}")
        for k,v in COMBINED_SCAN_REGISTRY.items():
            if row.get(k,False):ds.append(f"{'▲' if v['dir']=='buy' else '▼' if v['dir']=='sell' else '•'}{v['kor']}[T{v['tier']}]")
        if ds:sls.append(f"  {dd}: {', '.join(ds)}")
    bc=f"📌 [C. 시그널]\n"+("\n".join(sls[-15:]) if sls else "  (없음)")
    cm=m.get('committee',{});cmls=[]
    for name in COMMITTEE_NAMES:d=cm.get(name,{});cmls.append(f"    {COMMITTEE_ICONS.get(name,'•')}{name}:투표={d.get('vote','?')} 점수={d.get('score',0):+.0f} 확신도={d.get('conviction',0):.0f}%")
    bls=', '.join(f"{k}:{v:.1f}" for k,v in m['buy_layers'].items() if v>0);sls_=', '.join(f"{k}:{v:.1f}" for k,v in m['sell_layers'].items() if v>0)
    syn=m.get('reversal_synergy',0);pred=m.get('prediction_boost',0)
    bd=f"\n📌 [D. 시스템판단 — 검증대상]\n  🌐 컨텍스트:{m.get('context_label','기본')}\n  🏛️ 위원회:\n"+"\n".join(cmls)+f"\n  📊 ES:{m.get('ensemble_score',0):+.1f} (B{m.get('buy_agree',0)}:S{m.get('sell_agree',0)})\n  🔄 시너지:{syn:+.1f} | 🔮 예측:{pred:+.1f}\n  🚫 Veto:{m.get('veto_flags','없음') or '없음'}\n  🏷️ 판단:{m['judgment']}({m['confidence']:.0f}%)\n  💬 이유:{m.get('judgment_reason','')}\n  📋 근거:{m.get('judgment_detail','')}\n  [10L] BUY:{m['buy_total']:.1f}({m['buy_active']}/10)[{bls}] SELL:{m['sell_total']:.1f}({m['sell_active']}/10)[{sls_}]\n  선행:{m['leading_verdict']}|후행:{m['lagging_verdict']}\n"
    if m['combined_scans']:bd+=f"  CS:{_cs_str(m['combined_scans'])}\n"
    return f"{ba}\n{bb}\n{bc}\n{bd}"

def build_ai_prompt(ticker,phist,fund):
    return f"""━━━ Role ━━━
월스트리트 20년 경력 독립 애널리스트. CipherX V14.2(5-Committee Ensemble)의 Devil's Advocate.

━━━ V14.2 이해 ━━━
5개 위원회(Trend,Momentum,Money,Structure,Leading) 독립 투표 + 11종 컨텍스트 + Active Flip Veto + 교차시너지 + 예측부스트 + 자동 이유 생성.
Block D의 "판단 이유"를 반드시 검증하세요.

━━━ Rules ━━━
1. Block A~C 먼저 독자 분석 → Block D 대조
2. 시스템 BUY→SELL근거 탐색, SELL→BUY근거 탐색
3. 소수 의견 위원 검증 + 교차시너지 진위 + Veto 타당성
4. 확률적 시나리오 + 구체적 가격(VP/MA/ATR)
5. CMF/OBV/Vol로 스마트머니 추적
6. 환각 금지

━━━ Data ━━━
[{ticker}]
{phist}
[펀더멘탈] {fund}

━━━ Output ━━━

# 🚦 {ticker} 독립 검증 리포트

[🔵/🔴/🟠] **핵심 한줄**

---

### 1. 시장 심리
* 가격동향/거래량수급/모멘텀

### 2. 위원회 교차 검증
* 컨텍스트/다수의견/소수의견/시너지/Veto/시스템맹점
* ★ 시스템 "판단이유"에 동의하는가? 반박한다면 이유는?

### 3. 핵심 시그널
* WT/VuManChu/UTBot/Hull/자금흐름

### 4. 지지/저항
| 레벨 | 가격 | 근거 | 시나리오 |

### 5. 주가변동이유

### 6. 확률 시나리오
* 🔵강세 __%  🟠베이스 __%  🔴약세 __%

### 7. 실전 전략
* 진입/손절/익절/R:R

### 결론
[🔵/🔴/🟠] 2~3문장 + GRADE(A~F)"""

def analyze(ticker,chart_days=252,refresh=False):
    try:
        ts=int(time.time()) if refresh else None;df=compute_and_cache(ticker,ts)
        if df is None or df.empty or len(df)<50:return None,"데이터부족",None
        dc=df.dropna(subset=['WT1','WT2']).tail(chart_days).copy()
        if dc.empty:return None,"차트데이터부족",None
        return build_chart(dc,ticker).to_json(),build_prompt_text(dc,build_metadata(dc,ticker)),build_metadata(dc,ticker)
    except Exception as e:import traceback;print(f"[ERR]{ticker}:\n{traceback.format_exc()}");return None,f"실패:{e}",None

# ━━━ Session + Main ━━━
def init_session():
    defs={'messages':[{"role":"assistant","type":"text","content":"🚦 **CipherX V14.2**\n**티커명**을 입력하세요."}],'pending_ai_ticker':None,'pending_ai_prompt':None,'last_ticker':None,'scan_results':[],'scan_source':'','scan_total':0}
    for k,v in defs.items():
        if k not in st.session_state:st.session_state[k]=v
init_session()

with st.sidebar:
    st.markdown("## 🚦 CipherX V14.2");st.markdown("---")
    _mi=0 if st.session_state.get('_mode','분석')=='분석' else 1;app_mode=st.radio("모드",['분석','스캐너'],index=_mi);st.session_state['_mode']=app_mode
    chart_period=st.radio("기간",['3개월','6개월','1년'],index=0,horizontal=True,key="period");chart_days={'3개월':63,'6개월':126,'1년':252}[chart_period]
    if st.button("🗑️ 초기화",use_container_width=True,type="secondary"):
        for k in ['messages','pending_ai_ticker','pending_ai_prompt','last_ticker']:st.session_state[k]=[{"role":"assistant","type":"text","content":"🚦 **CipherX V14.2**"}] if k=='messages' else None
        st.rerun()

current_mode=st.session_state.get('_mode','분석')
if current_mode=='스캐너':
    st.markdown("<h2 style='text-align:center;color:#fff'>🔍 Scanner</h2>",unsafe_allow_html=True)
    st.markdown("#### 📂 섹터 선택");sector_names=list(SECTOR_GROUPS.keys());selected_sector=st.session_state.get('selected_sector',None)
    for rs in range(0,len(sector_names),3):
        ri=sector_names[rs:rs+3];cols=st.columns(3)
        for i,sn in enumerate(ri):
            with cols[i]:
                if st.button(f"{sn}\n({len(SECTOR_GROUPS[sn])})",key=f"sec_{rs+i}",use_container_width=True,type="primary" if selected_sector==sn else "secondary"):st.session_state['selected_sector']=sn;st.session_state['scan_tickers_override']=SECTOR_GROUPS[sn];st.rerun()
    if selected_sector:st.markdown(f"<div style='background:rgba(99,102,241,.08);border:1px solid #6366F133;border-radius:10px;padding:10px 14px;margin:8px 0'><span style='color:#A5B4FC;font-weight:700'>{selected_sector}</span><span style='color:#64748B;margin-left:8px'>{len(SECTOR_GROUPS.get(selected_sector,[]))}종목</span></div>",unsafe_allow_html=True)
    st.markdown("#### ✏️ 직접 입력");ci=st.text_input("티커",placeholder="NVDA,TSLA...",key="scan_in")
    if ci and ci.strip():tickers=[t.strip().upper() for t in ci.split(',') if t.strip()];scan_source="직접"
    elif st.session_state.get('scan_tickers_override'):tickers=st.session_state['scan_tickers_override'];scan_source=selected_sector or "섹터"
    else:tickers=[];scan_source="직접"
    cb1,cb2=st.columns([3,1])
    with cb1:scan_btn=st.button(f"🚀 스캔({len(tickers)})",type="primary",use_container_width=True)
    with cb2:
        if st.button("🗑️",use_container_width=True,key="sr"):st.session_state.pop('selected_sector',None);st.session_state.pop('scan_tickers_override',None);st.session_state['scan_results']=[];st.rerun()
    if scan_btn and tickers:
        pb=st.progress(0);results=[];sts=math.floor(time.time()/300)
        def _so(t):
            try:
                time.sleep(np.random.uniform(0.1, 0.5)) # API Rate Limit 회피용 지터링 추가
                df_=_compute_cached(t,f"{t}_{sts}")
                if df_ is None or len(df_)<50:return None
                dc_=df_.tail(63);acs=[];lsd=None
                for cn,ccfg in COMBINED_SCAN_REGISTRY.items():
                    if cn in dc_.columns and dc_[cn].tail(5).any():ld=dc_[cn].tail(5)[dc_[cn].tail(5)].index[-1];acs.append({'icon':ccfg['icon'],'kor':ccfg['kor'],'dir':ccfg['dir'],'tier':ccfg['tier'],'date':ld.strftime('%m/%d')});lsd=ld if lsd is None or ld>lsd else lsd
                lt=dc_.iloc[-1];ch=_sf((lt['Close']-dc_.iloc[-2]['Close'])/dc_.iloc[-2]['Close']*100) if len(dc_)>=2 else 0
                return {'ticker':t,'price':_sf(lt['Close']),'chg':ch,'scans':sorted(acs,key=lambda x:x['tier']),'jg':str(lt.get('Trade_Judgment','N/A')),'cf':_sf(lt.get('Judgment_Confidence',0)),'es':_sf(lt.get('Ensemble_Score',0)),'ctx':CTX_KOR.get(int(_sf(lt.get('Market_Context',0))),'기본'),'ba':int(_sf(lt.get('Buy_Agree',0))),'sa':int(_sf(lt.get('Sell_Agree',0))),'latest_sig':lsd.strftime('%Y-%m-%d') if lsd else '9999-99-99','reason':str(lt.get('Judgment_Reason','')),'action':str(lt.get('Action_Label',''))}
            except:return None
        with ThreadPoolExecutor(max_workers=min(8,len(tickers))) as ex:
            futs={ex.submit(_so,t):t for t in tickers}
            for idx_f,f in enumerate(as_completed(futs)):
                pb.progress((idx_f+1)/len(tickers))
                r=f.result()
                if r:results.append(r)
        pb.empty()
        from datetime import datetime as dt_
        results.sort(key=lambda x:(0 if x['scans'] else 1,-dt_.strptime(x['latest_sig'],'%Y-%m-%d').timestamp() if x['latest_sig']!='9999-99-99' else 0,-sum(1 for s in x['scans'] if s['tier']==1)))
        st.session_state['scan_results']=results;st.session_state['scan_source']=scan_source;st.session_state['scan_total']=len(tickers)
    results=st.session_state.get('scan_results',[])
    if results:
        bt=[r for r in results if 'BUY' in r['jg']];st_=[r for r in results if 'SELL' in r['jg']]
        scan_total=st.session_state.get('scan_total',0)  # ★ 미리 추출
        st.markdown(f"<div style='display:flex;gap:12px;margin-bottom:12px'><div style='flex:1;background:rgba(0,230,118,.06);border:1px solid #10B98133;border-radius:10px;padding:10px;text-align:center'><span style='color:#34D399;font-weight:800;font-size:1.3rem'>{len(bt)}</span><span style='color:#64748B;font-size:.8rem'> 매수</span></div><div style='flex:1;background:rgba(255,23,68,.06);border:1px solid #EF444433;border-radius:10px;padding:10px;text-align:center'><span style='color:#F87171;font-weight:800;font-size:1.3rem'>{len(st_)}</span><span style='color:#64748B;font-size:.8rem'> 매도</span></div><div style='flex:1;background:rgba(99,102,241,.06);border:1px solid #6366F133;border-radius:10px;padding:10px;text-align:center'><span style='color:#A5B4FC;font-weight:800;font-size:1.3rem'>{len(results)}</span><span style='color:#64748B;font-size:.8rem'>/{scan_total}</span></div></div>",unsafe_allow_html=True)
        for r in results:
            chc='#34D399' if r['chg']>=0 else '#F87171';chi='▲' if r['chg']>=0 else '▼';jc='#34D399' if 'BUY' in r['jg'] else('#F87171' if 'SELL' in r['jg'] else '#FCD34D')
            sh="".join([f"<div style='display:flex;gap:6px;padding:2px 0'><span style='color:{'#34D399' if s['dir']=='buy' else '#F87171' if s['dir']=='sell' else '#FFC107'}'>●</span><span style='color:#E8ECF1;font-size:.82rem'>{s['icon']}{s['kor']}</span><span style='color:#64748B;font-size:.7rem'>{s['date']}</span></div>" for s in r['scans']]) if r['scans'] else "<span style='color:#475569;font-size:.8rem'>—</span>"
            esc='#34D399' if r['es']>10 else('#F87171' if r['es']<-10 else '#FCD34D');bd='#1E293B' if r['scans'] else '#0F172A';op='1' if r['scans'] else '.6'
            rh=""
            if r.get('reason'):rc='#6EE7B7' if 'BUY' in r['jg'] else('#FCA5A5' if 'SELL' in r['jg'] else '#FCD34D');rh=f"<div style='padding:4px 0;border-top:1px solid rgba(255,255,255,.04);margin-top:4px'><span style='color:{rc};font-size:.78rem'>💬 {r['reason'][:80]}</span></div>"
            st.markdown(f"<div style='background:linear-gradient(160deg,#0F1320,#141926);border:1px solid {bd};border-radius:14px;padding:14px 18px;margin:6px 0;opacity:{op}'><div style='display:flex;justify-content:space-between;margin-bottom:8px'><span style='color:#A5B4FC;font-weight:800;font-size:1.15rem'>{r['ticker']}</span><div style='display:flex;align-items:center;gap:8px'><span style='color:{esc};font-size:.75rem;font-weight:700'>ES:{r['es']:+.0f}</span><span style='color:{jc};font-size:.8rem;font-weight:600'>{r['jg']}({r['cf']:.0f}%)</span><span style='color:{chc};font-size:.8rem'>{chi}{abs(r['chg']):.1f}%</span></div></div>{sh}{rh}</div>",unsafe_allow_html=True)
            if st.button(f"{r['ticker']} 분석",key=f"sc_{r['ticker']}",use_container_width=True):st.session_state['_mode']='분석';st.session_state['_auto']=r['ticker'];st.rerun()
else:
    st.markdown("<h2 style='text-align:center;color:#fff;margin-bottom:4px'>🚦 CipherX V14.2</h2>",unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;color:#64748B;margin-bottom:16px'>5-Committee Ensemble + Prediction + Auto Reason</p>",unsafe_allow_html=True)
    if not st.session_state.last_ticker:
        cols=st.columns(4)
        for i,t in enumerate(["NVDA","TSLA","AAPL","QQQ"]):
            with cols[i]:
                if st.button(t,use_container_width=True):st.session_state['quick']=t
    for i,msg in enumerate(st.session_state.messages):
        av="✨" if msg["role"]=="assistant" else "🧑‍💻"
        with st.chat_message(msg["role"],avatar=av):
            if msg.get("type")=="analysis":st.markdown(msg.get("content",""));render_analysis(msg)
            elif msg.get("type")=="report":
                with st.expander(f"{msg.get('ticker','')} AI리포트",expanded=True):st.markdown(msg["content"])
                st.download_button("📥",key=f"dl_{i}",data=msg["content"].encode('utf-8'),file_name=f"{msg.get('ticker','')}_V142_{datetime.now().strftime('%Y%m%d')}.md",mime="text/markdown",use_container_width=True)
            else:st.markdown(msg.get("content",""))
            if msg.get("prompt") and msg.get("type")=="analysis":
                with st.expander("프롬프트"):st.code(msg["prompt"],language="markdown");st_copy_to_clipboard(msg["prompt"],before_copy_label="📋",after_copy_label="✅")
    def _run_ai():
        tp=st.session_state.pending_ai_ticker;pp=st.session_state.pending_ai_prompt
        with st.chat_message("assistant",avatar="✨"):
            pb=st.progress(0);
            try:
                model=get_gemini_model();pb.progress(20);col_=[]
                def gen():
                    pb.progress(40,text="🚀 AI생성중...")
                    for ch in model.generate_content(pp,stream=True):
                        if ch.text:col_.append(ch.text);yield ch.text
                    pb.progress(100)
                with st.expander(f"{tp.upper()} AI리포트",expanded=True):st.write_stream(gen())
                time.sleep(.3);pb.empty();st.session_state.messages.append({"role":"assistant","type":"report","ticker":tp.upper(),"content":"".join(col_)});st.session_state.pending_ai_ticker=None;st.session_state.pending_ai_prompt=None;st.rerun()
            except Exception as e:pb.empty();st.error(f"AI오류:{e}")
    def process_ticker(tv,refresh=False):
        tv=tv.strip().upper();st.session_state.pending_ai_ticker=None;st.session_state.pending_ai_prompt=None
        if not _valid_fmt(tv):st.toast(f"⚠️ {tv} 형식오류",icon="🚨");return
        if not validate_ticker(tv):st.toast(f"⚠️ {tv} 없음",icon="🔍");return
        st.session_state.messages.append({"role":"user","type":"text","content":tv});st.session_state.last_ticker=tv
        with st.chat_message("assistant",avatar="✨"):
            with st.status(f"🔍 {tv} 분석중...",expanded=True) as status:
                st.write("📊 데이터+지표+시그널+위원회...");fund=fetch_fundamentals(tv)
                fj,phist,meta=analyze(tv,chart_days,refresh)
                if fj and meta:
                    jg=meta['judgment'];act=meta.get('action_label','');rsn=meta.get('judgment_reason','')
                    es=meta.get('ensemble_score',0);syn=meta.get('reversal_synergy',0)
                    st.write(f"📍 {act} | ES:{es:+.1f}")
                    if 'STRONG' in jg:st.toast(f"{'🟢🟢🟢' if 'BUY' in jg else '🔴🔴🔴'} {tv} {jg}!",icon="🚀" if 'BUY' in jg else "⚠️")
                    veto=meta.get('veto_flags','')
                    if veto:st.toast(f"🚫 Veto:{veto}",icon="🚫")
                    for cs in [s for s in meta.get('combined_scans',[]) if s['tier']==1 and s['is_today']]:st.toast(f"🎯 T1 {cs['kor']}!",icon=cs['icon'])
                    prompt=build_ai_prompt(tv,phist,fund);status.update(label=f"✅ {tv} — {act}",state="complete",expanded=False)
                else:prompt=None;status.update(label=f"⚠️ {tv} 실패",state="error")
            if fj:
                content=f"**{tv}** — **{meta.get('action_label','')}**\n💬 {meta.get('judgment_reason','')}"
                es=meta.get('ensemble_score',0);syn=meta.get('reversal_synergy',0);pred=meta.get('prediction_boost',0)
                content+=f"\n🏛️ ES:{es:+.1f} | B{meta.get('buy_agree',0)}:S{meta.get('sell_agree',0)} | 🌐{meta.get('context_label','')}"
                if abs(syn)>5:content+=f" | 🔄{syn:+.1f}"
                if abs(pred)>3:content+=f" | 🔮{pred:+.1f}"
                if meta.get('combined_scans'):content+=f"\n🎯 CS:매수{sum(1 for s in meta['combined_scans'] if s['dir']=='buy')} 매도{sum(1 for s in meta['combined_scans'] if s['dir']=='sell')}"
                content+=f"\n⏳{meta['leading_verdict']} | 📊{meta['lagging_verdict']}"
                veto=meta.get('veto_flags','')
                if veto:content+=f"\n🚫 {veto}"
                st.session_state.messages.append({"role":"assistant","type":"analysis","ticker":tv,"content":content,"fig_json":fj,"meta":meta,"prompt":prompt})
                st.session_state.pending_ai_ticker=tv;st.session_state.pending_ai_prompt=prompt;st.rerun()
            else:st.session_state.messages.append({"role":"assistant","type":"text","content":f"⚠️ **{tv}** 실패:{phist}"});st.rerun()
    if st.session_state.get('_auto'):process_ticker(st.session_state.pop('_auto'))
    if st.session_state.get('quick'):process_ticker(st.session_state.pop('quick'))
    if st.session_state.pending_ai_ticker and st.session_state.pending_ai_prompt:
        if st.button(f"🚀 {st.session_state.pending_ai_ticker.upper()} AI분석",type="primary",use_container_width=True):_run_ai()
    if ti:=st.chat_input("티커 입력 (예: TSLA, AAPL, QQQ)"):process_ticker(ti)

print("✅ CipherX V14.2 전체 완료!")
