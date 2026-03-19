# ══════════════════════════════════════════════════════════════
#  CipherX V13.0 — Institutional Quant Judgment Architecture
#  PART 1/4: 설정, 레지스트리, 유틸리티, 기술지표
# ══════════════════════════════════════════════════════════════

import streamlit as st, google.generativeai as genai
import time, re, math
from datetime import datetime
from st_copy_to_clipboard import st_copy_to_clipboard
import yfinance as yf, plotly.graph_objects as go
import pandas as pd, numpy as np
from plotly.subplots import make_subplots
from collections import OrderedDict
from scipy.signal import find_peaks
from concurrent.futures import ThreadPoolExecutor, as_completed

st.set_page_config(page_title="CipherX V13", page_icon="📈", layout="centered", initial_sidebar_state="collapsed")

def inject_css():
    st.markdown("""<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
html,body,[class*="css"]{font-family:'Pretendard',sans-serif!important}
.stApp{background-color:#0B0E14}
p,li{color:#E8ECF1!important} h1,h2{color:#FFF!important;font-weight:800!important}
h3{color:#F0F4F8!important;font-weight:700!important}
.block-container{padding-top:1rem!important;max-width:960px}
div.stButton>button[kind="primary"]{background:linear-gradient(135deg,#6366F1,#8B5CF6)!important;color:#fff!important;border:none!important;border-radius:12px!important;font-weight:700!important;width:100%}
.price-header{background:linear-gradient(160deg,#0F1320,#141926);border:1px solid #1C2233;border-radius:16px;padding:20px 24px;margin-bottom:18px}
.price-big{font-size:2.2rem;font-weight:800;margin:0}
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
</style>""", unsafe_allow_html=True)
inject_css()

# ══════════════════════════════════════════
#  상수 & 임계값
# ══════════════════════════════════════════
OB1, OB2, OS1, OS2 = 53, 60, -53, -60
NUM_LAYERS = 10  # 10-Layer 시스템

class JT:
    # 판단 임계값
    STRONG_BUY=20; BUY=13; WATCH_BUY=7; STRONG_SELL=20; SELL=13; WATCH_SELL=7
    # 레이어 캡
    TREND_CAP=12; MOMENTUM_CAP=12; CANDLE_CAP=6; BB_CAP=8; VOLUME_CAP=8
    MF_CAP=8; PATTERN_CAP=12; ANTICIPATION_CAP=8; LEADING_CAP=10; LAGGING_CAP=10
    # 보정
    COMBO_T1=5.0; COMBO_T2=3.0; COMBO_T3=1.5
    ACCEL_STRONG=3.0; ACCEL_MOD=1.5
    DECAY_DAYS=3; DECAY_RATE=0.5

GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GEMINI_API_KEY)

@st.cache_resource
def get_gemini_model(): return genai.GenerativeModel('gemini-2.5-flash')

# ══════════════════════════════════════════
#  시그널 레지스트리 (125개)
# ══════════════════════════════════════════
_B, _S, _N = 'buy', 'sell', 'neutral'
def _sig(w,d,icon,label,sym,sz,clr,base,atr_m,kor,desc):
    return {'w':w,'dir':d,'icon':icon,'label':label,'sym':sym,'sz':sz,'clr':clr,'base':base,'atr_m':atr_m,'kor':kor,'desc':desc}

SIGNAL_REGISTRY = {
    # MCB+ 핵심
    'Gold_Dot':_sig(3,_B,'🏆','GOLD','circle',18,'#FFD700','Low',-3,'최강매수','RSI<30+MFI<30+WT<-60+다이버'),
    'Green_Dot_T1':_sig(2.5,_B,'🟢','BUY T1','circle',16,'#00E676','Low',-2.5,'강한매수','WT과매도+RSI<30+MFI<30'),
    'Green_Dot_T2':_sig(2,_B,'🟩','BUY T2','circle',13,'#69F0AE','Low',-2.2,'매수','WT과매도+RSI/MFI<32'),
    'Blue_Diamond':_sig(2,_B,'🔹','BLUE DIA','diamond',14,'#00bfff','Low',-1.8,'추세매수','WT2≤0+HTF강세'),
    'Green_Circle':_sig(.8,_B,'✅','BUY Cir','circle-open',11,'#00E676','Low',-1.2,'과매도반등','WT과매도+RSI<45'),
    'Blood_Diamond':_sig(3,_S,'🩸','BLOOD','diamond',18,'#DC143C','High',3,'최강매도','RSI>70+MFI>70+WT>60+다이버'),
    'Red_Dot_T1':_sig(2.5,_S,'🔴','SELL T1','circle',16,'#FF1744','High',2.5,'강한매도','WT과매수+RSI>70+MFI>70'),
    'Red_Dot_T2':_sig(2,_S,'🟥','SELL T2','circle',13,'#FF5252','High',2.2,'매도','WT과매수+RSI/MFI>68'),
    'Red_Diamond':_sig(2,_S,'🔸','RED DIA','diamond',14,'#ff3333','High',1.8,'추세매도','WT2≥0+HTF약세'),
    'Red_Circle':_sig(.8,_S,'⛔','SELL Cir','circle-open',11,'#FF1744','High',1.2,'과매수하락','WT과매수+RSI>55'),
    # 다이버전스
    'Bull_Divergence':_sig(2,_B,'📈','BullDiv','triangle-up',12,'#AA00FF','Low',-2,'상승다이버전스','가격↓vsWT↑'),
    'Bear_Divergence':_sig(2,_S,'📉','BearDiv','triangle-down',12,'#AA00FF','High',2,'하락다이버전스','가격↑vsWT↓'),
    'RSI_Bull_Divergence':_sig(1.5,_B,'📊','RSIBullDiv','triangle-up',11,'#CE93D8','Low',-1.8,'RSI상승다이버','가격↓vsRSI↑'),
    'RSI_Bear_Divergence':_sig(1.5,_S,'📉','RSIBearDiv','triangle-down',11,'#CE93D8','High',1.8,'RSI하락다이버','가격↑vsRSI↓'),
    'Hidden_Bull_Div':_sig(1.5,_B,'🔀','HidBull','triangle-up',10,'#E040FB','Low',-1.6,'히든강세다이버','가격↑vsWT↓'),
    'Hidden_Bear_Div':_sig(1.5,_S,'🔁','HidBear','triangle-down',10,'#E040FB','High',1.6,'히든약세다이버','가격↓vsWT↑'),
    # Cooper Hit&Run (24개)
    'Pullback_123_Bull':_sig(2,_B,'🎯','123PB▲','triangle-up',12,'#00E676','Low',-1.8,'1,2,3풀백매수','ADX>30+3일저점↓'),
    'Pullback_123_Bear':_sig(2,_S,'🎯','123PB▼','triangle-down',12,'#FF1744','High',1.8,'1,2,3되돌림매도','ADX>30+3일고점↑'),
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
    'Slingshot_Bull':_sig(2,_B,'🎯','Sling▲','triangle-up',12,'#00E676','Low',-1.8,'슬링샷매수','2개월신고가후흔들기→재돌파'),
    'Slingshot_Bear':_sig(2,_S,'🎯','Sling▼','triangle-down',12,'#FF1744','High',1.8,'슬링샷매도','2개월신저가후흔들기→재하락'),
    'Jack_In_Box_Bull':_sig(2,_B,'🎁','Jack▲','star',12,'#00E676','Low',-1.8,'잭인더박스매수','XBO후인사이드→재돌파'),
    'Jack_In_Box_Bear':_sig(2,_S,'🎁','Jack▼','star',12,'#FF1744','High',1.8,'잭인더박스매도','XBD후인사이드→재하락'),
    'NonADX_123_Bull':_sig(1.8,_B,'📐','nADX▲','triangle-up',11,'#69F0AE','Low',-1.5,'비ADX풀백매수','주가>50MA+3일저점↓'),
    'NonADX_123_Bear':_sig(1.8,_S,'📐','nADX▼','triangle-down',11,'#FF5252','High',1.5,'비ADX풀백매도','주가<50MA+3일고점↑'),
    'Reversal_New_Highs':_sig(2.5,_B,'🔝','RevHi','star-diamond',14,'#00E676','Low',-2.5,'신고가반전','60일신고가+아웃사이드'),
    'Reversal_New_Lows':_sig(2.5,_S,'🔻','RevLo','star-diamond',14,'#FF1744','High',2.5,'신저가반전','60일신저가+아웃사이드'),
    # MA (15개)
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
    # BB (12개)
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
    # 캔들 (12개)
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
    # MACD (4개)
    'MACD_Cross_Buy':_sig(1,_B,'〽️','MCD▲','triangle-up',9,'#4CAF50','Low',-1,'MACD골든','MACD>시그널'),
    'MACD_Cross_Sell':_sig(1,_S,'〽️','MCD▼','triangle-down',9,'#E57373','High',1,'MACD데드','MACD<시그널'),
    'MACD_Zero_Cross_Buy':_sig(1.2,_B,'⬆️','MC0▲','triangle-up',10,'#4CAF50','Low',-1,'MACD0↑','MACD>0'),
    'MACD_Zero_Cross_Sell':_sig(1.2,_S,'⬇️','MC0▼','triangle-down',10,'#E57373','High',1,'MACD0↓','MACD<0'),
    # 스토캐스틱 (6개)
    'StochRSI_Cross_Buy':_sig(.8,_B,'🔄','StR▲','circle-open',8,'#81C784','Low',-.8,'StRSI매수','%K>%D과매도'),
    'StochRSI_Cross_Sell':_sig(.8,_S,'🔄','StR▼','circle-open',8,'#EF9A9A','High',.8,'StRSI매도','%K<%D과매수'),
    'Stoch_Reached_OB':_sig(.5,_N,'📊','St→OB','triangle-up',7,'#FFA726','High',.5,'Stoch과매수도달','%K≥80'),
    'Stoch_Reached_OS':_sig(.5,_N,'📊','St→OS','triangle-down',7,'#4FC3F7','Low',-.5,'Stoch과매도도달','%K≤20'),
    'Stoch_Overbought':_sig(.8,_S,'🔴','StOB','circle',8,'#FF5252','High',.8,'Stoch과매수','%K>80&%D>80'),
    'Stoch_Oversold':_sig(.8,_B,'🟢','StOS','circle',8,'#69F0AE','Low',-.8,'Stoch과매도','%K<20&%D<20'),
    # ADX/DMI (6개)
    'DMI_Cross_Bull':_sig(1.5,_B,'📈','DMI▲','triangle-up',10,'#00E676','Low',-1.2,'DMI강세교차','+DI>-DI'),
    'DMI_Cross_Bear':_sig(1.5,_S,'📉','DMI▼','triangle-down',10,'#FF1744','High',1.2,'DMI약세교차','-DI>+DI'),
    'ADX_New_Uptrend':_sig(1.5,_B,'🚀','ADX▲','arrow-up',11,'#76FF03','Low',-1.4,'신규상승추세','ADX>25+DI↑'),
    'ADX_New_Downtrend':_sig(1.5,_S,'💨','ADX▼','arrow-down',11,'#FF3D00','High',1.4,'신규하락추세','ADX>25+DI↓'),
    'ADX_Momentum_Buy':_sig(1.5,_B,'🚀','ADXIg','arrow-up',11,'#76FF03','Low',-1.4,'ADX점화','ADX>20+DI↑'),
    'ADX_Momentum_Sell':_sig(1.5,_S,'💨','ADXDn','arrow-down',11,'#FF3D00','High',1.4,'ADX하락점화','ADX>20+DI↓'),
    # RSI (4개)
    'RSI_Cross_30_Up':_sig(1,_B,'📈','RSI30▲','triangle-up',9,'#4CAF50','Low',-1,'RSI30↑','RSI>30돌파'),
    'RSI_Cross_50_Up':_sig(1,_B,'📈','RSI50▲','triangle-up',9,'#69F0AE','Low',-.8,'RSI50↑','RSI>50돌파'),
    'RSI_Cross_70_Down':_sig(1,_S,'📉','RSI70▼','triangle-down',9,'#EF5350','High',1,'RSI70↓','RSI<70'),
    'RSI_Cross_50_Down':_sig(1,_S,'📉','RSI50▼','triangle-down',9,'#FF5252','High',.8,'RSI50↓','RSI<50'),
    # 갭 (4개)
    'Gap_Up':_sig(1,_B,'⏫','Gap▲','arrow-up',10,'#00E676','Low',-1,'갭상승','시가>전일고'),
    'Gap_Down':_sig(1,_S,'⏬','Gap▼','arrow-down',10,'#FF1744','High',1,'갭하락','시가<전일저'),
    'Gap_Up_Closed':_sig(.8,_S,'🔄','GpUF','circle-open',8,'#FFA726','High',.8,'갭업메움','갭메움'),
    'Gap_Down_Closed':_sig(.8,_B,'🔄','GpDF','circle-open',8,'#4FC3F7','Low',-.8,'갭다운메움','갭메움'),
    # 범위 (5개)
    'NR7':_sig(.5,_N,'🔳','NR7','square-open',7,'#90A4AE','Low',-.3,'NR7','7일최소범위'),
    'NR7_2':_sig(.8,_N,'🔳','NR72','square-open',8,'#90A4AE','Low',-.5,'NR7-2','2일연속NR7'),
    'Narrow_Range_Bar':_sig(.5,_N,'📊','NrBar','square-open',7,'#90A4AE','Low',-.3,'좁은범위봉','범위<ATR×.5'),
    'Wide_Range_Bar':_sig(.5,_N,'📊','WdBar','square-open',7,'#FFAB40','Low',-.4,'넓은범위봉','범위>ATR×2'),
    'Calm_After_Storm':_sig(1,_N,'🌤️','Calm','diamond-open',9,'#FFC107','Low',-.8,'폭풍뒤고요','WR→NR'),
    # 52주 (4개)
    'New_52W_High':_sig(1.5,_B,'🏔️','52H','star-triangle-up',12,'#FFD700','High',1.5,'52주신고가','52주고가갱신'),
    'New_52W_Low':_sig(1.5,_S,'🕳️','52L','star-triangle-down',12,'#B71C1C','Low',-1.5,'52주신저가','52주저가갱신'),
    'New_52W_Closing_High':_sig(1.2,_B,'🏆','52CH','star',11,'#FFD700','High',1.2,'52주종가신고','종가최고'),
    'New_52W_Closing_Low':_sig(1.2,_S,'💀','52CL','star',11,'#B71C1C','Low',-1.2,'52주종가신저','종가최저'),
    # 연속 (6개)
    'Up_3_Days':_sig(.5,_B,'📗','Up3','triangle-up',8,'#69F0AE','High',.5,'3일연속↑','3일양봉'),
    'Up_4_Days':_sig(.6,_B,'📗','Up4','triangle-up',8,'#69F0AE','High',.6,'4일연속↑','4일양봉'),
    'Up_5_Days':_sig(.8,_B,'📗','Up5','triangle-up',9,'#00E676','High',.8,'5일연속↑','5일양봉'),
    'Down_3_Days':_sig(.5,_S,'📕','Dn3','triangle-down',8,'#FF5252','Low',-.5,'3일연속↓','3일음봉'),
    'Down_4_Days':_sig(.6,_S,'📕','Dn4','triangle-down',8,'#FF5252','Low',-.6,'4일연속↓','4일음봉'),
    'Down_5_Days':_sig(.8,_S,'📕','Dn5','triangle-down',9,'#FF1744','Low',-.8,'5일연속↓','5일음봉'),
    # 기타
    'Multiple_Ten_Bull':_sig(1,_B,'💯','Rnd▲','triangle-up',9,'#00E676','Low',-1,'10배수강세','라운드넘버돌파'),
    'Multiple_Ten_Bear':_sig(1,_S,'💯','Rnd▼','triangle-down',9,'#FF1744','High',1,'10배수약세','라운드넘버이탈'),
    'Pocket_Pivot':_sig(1.5,_B,'🧲','PkPvt','triangle-up',11,'#7C4DFF','Low',-1.5,'포켓피봇','양봉+거래량>10일하락최대'),
    'Parabolic_Rise':_sig(2,_N,'🚀','Para','star-diamond',13,'#FF6D00','High',2,'포물선상승','급격한수직상승'),
    'Three_Weeks_Tight':_sig(1.5,_B,'📦','3WT','square',11,'#00E676','Low',-1.5,'3주타이트','3주좁은종가'),
    # 기존 핵심
    'Squeeze_Fire_Buy':_sig(1.5,_B,'💥','SqF▲','star-diamond',14,'#00FFFF','Low',-1.5,'스퀴즈매수','TTM해소+모멘텀↑'),
    'Squeeze_Fire_Sell':_sig(1.5,_S,'🧨','SqF▼','star-diamond',14,'#FF6600','High',1.5,'스퀴즈매도','TTM해소+모멘텀↓'),
    'Volume_Climax_Buy':_sig(2,_B,'🌊','VCl▲','hexagram',14,'#00BCD4','Low',-2.8,'거래량클라이맥스','3x거래량+WT과매도'),
    'Volume_Climax_Sell':_sig(2,_S,'🌋','VCl▼','hexagram',14,'#FF5722','High',2.8,'거래량클라이맥스','3x거래량+WT과매수'),
    'Volume_Surge':_sig(1.5,_N,'🌊','VSrg','hexagram',12,'#00BCD4','Low',-1,'거래량급증','거래량≥50일평균×3'),
    'OBV_Div_Buy':_sig(.8,_B,'📊','OBV▲','triangle-up',10,'#80DEEA','Low',-1.4,'OBV다이버','OBV↑vs가격↓'),
    'OBV_Div_Sell':_sig(.8,_S,'🔻','OBV▼','triangle-down',10,'#FFAB91','High',1.4,'OBV다이버','OBV↓vs가격↑'),
    'SuperTrend_Buy':_sig(1.5,_B,'📈','ST▲','arrow-up',12,'#00E5FF','Low',-1.5,'ST강세','ST위로돌파'),
    'SuperTrend_Sell':_sig(2,_S,'📉','ST▼','arrow-down',12,'#FF1744','High',1.5,'ST약세','ST하향돌파'),
    'EMA_Pullback_Buy':_sig(2,_B,'🎯','EPB▲','triangle-up',13,'#00BFA5','Low',-1.8,'EMA눌림목','상승추세EMA조정'),
    'EMA_Pullback_Sell':_sig(2,_S,'🎯','EPB▼','triangle-down',13,'#FF6E40','High',1.8,'EMA되돌림','하락추세EMA반등'),
    'Momentum_Ignition_Buy':_sig(2.5,_B,'🔥','MIg▲','star-diamond',15,'#FF6D00','Low',-2.5,'모멘텀점화','장대양봉+거래량'),
    'Momentum_Ignition_Sell':_sig(2.5,_S,'💣','MIg▼','star-diamond',15,'#D50000','High',2.5,'모멘텀점화매도','장대음봉+거래량'),
    'Parabolic_Bottom_Buy':_sig(3,_B,'🧊','PBot','diamond',16,'#00FFFF','Low',-3,'포물선바닥','WT<-80꺾임+양봉'),
    'Parabolic_Top_Sell':_sig(3,_S,'🌡️','PTop','diamond',16,'#FF0000','High',3,'포물선천장','WT>80꺾임+음봉'),
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
}

# Combined Scan 레지스트리 (28개)
COMBINED_SCAN_REGISTRY = {
    'CS_Ultimate_Buy':{'name':'🏆 ULTIMATE BUY','kor':'궁극의매수','dir':'buy','tier':1,'icon':'🏆','color':'#FFD700','desc':'6중확인','win':'75-85%'},
    'CS_Triple_Oversold_Reversal':{'name':'🔥 Triple OS Rev','kor':'삼중과매도반전','dir':'buy','tier':1,'icon':'🔥','color':'#00E676','desc':'WT+RSI+Stoch+반전','win':'70-80%'},
    'CS_Breakout_Momentum_Buy':{'name':'🚀 Breakout Mom','kor':'돌파모멘텀','dir':'buy','tier':1,'icon':'🚀','color':'#00E676','desc':'52W+거래량+ADX','win':'65-75%'},
    'CS_Institutional_Accumulation':{'name':'🏦 Institutional','kor':'기관매집','dir':'buy','tier':1,'icon':'🏦','color':'#00BCD4','desc':'포켓피봇+OBV','win':'70-80%'},
    'CS_Divergence_Confluence_Buy':{'name':'📊 Div Conf','kor':'다이버합류매수','dir':'buy','tier':1,'icon':'📊','color':'#7C4DFF','desc':'다중다이버전스','win':'70-80%'},
    'CS_Capitulation_Bottom':{'name':'🏳️ Capitulation','kor':'항복바닥','dir':'buy','tier':1,'icon':'🏳️','color':'#00E676','desc':'52W저+극과매도','win':'70-80%'},
    'CS_Ultimate_Sell':{'name':'🏆 ULTIMATE SELL','kor':'궁극의매도','dir':'sell','tier':1,'icon':'🏆','color':'#FFD700','desc':'6중확인','win':'75-85%'},
    'CS_Triple_Overbought_Exhaustion':{'name':'🌡️ Triple OB','kor':'삼중과매수소진','dir':'sell','tier':1,'icon':'🌡️','color':'#FF1744','desc':'WT+RSI+Stoch+반전','win':'70-80%'},
    'CS_Breakdown_Momentum_Sell':{'name':'💨 Breakdown','kor':'붕괴모멘텀','dir':'sell','tier':1,'icon':'💨','color':'#FF1744','desc':'52W+거래량+ADX','win':'65-75%'},
    'CS_Parabolic_Exhaustion_Sell':{'name':'🎢 Para Exhaust','kor':'포물선소진','dir':'sell','tier':1,'icon':'🎢','color':'#D50000','desc':'포물선+천장캔들','win':'70-80%'},
    'CS_Divergence_Confluence_Sell':{'name':'📉 Div Conf Sell','kor':'다이버합류매도','dir':'sell','tier':1,'icon':'📉','color':'#E040FB','desc':'다중다이버전스','win':'70-80%'},
    'CS_Blow_Off_Top':{'name':'🎆 Blow-Off','kor':'블로우오프천장','dir':'sell','tier':1,'icon':'🎆','color':'#FF1744','desc':'52W고+극과매수','win':'70-80%'},
    'CS_Trend_Pullback_Buy':{'name':'🎯 Trend PB','kor':'추세눌림목','dir':'buy','tier':2,'icon':'🎯','color':'#00E676','desc':'상승추세+MA지지','win':'60-70%'},
    'CS_Squeeze_Breakout_Buy':{'name':'💥 Sq Break','kor':'스퀴즈돌파','dir':'buy','tier':2,'icon':'💥','color':'#00FFFF','desc':'BB해소+상방','win':'60-70%'},
    'CS_MA_Confluence_Buy':{'name':'📈 MA Conf','kor':'MA합류','dir':'buy','tier':2,'icon':'📈','color':'#69F0AE','desc':'골든+정배열','win':'60-70%'},
    'CS_Cooper_Setup_Buy':{'name':'🃏 Cooper','kor':'쿠퍼셋업','dir':'buy','tier':2,'icon':'🃏','color':'#FF6D00','desc':'ADX+쿠퍼패턴','win':'60-70%'},
    'CS_Volume_Climax_Rev_Buy':{'name':'🌊 Vol Rev','kor':'거래량반전','dir':'buy','tier':2,'icon':'🌊','color':'#00BCD4','desc':'거래량폭발+과매도','win':'60-70%'},
    'CS_Ichimoku_Breakout_Buy':{'name':'☁️ Ichi Break','kor':'이치모쿠돌파','dir':'buy','tier':2,'icon':'☁️','color':'#00E676','desc':'쿠모+TK','win':'60-70%'},
    'CS_Trend_Rejection_Sell':{'name':'🎯 Trend Rej','kor':'추세거부','dir':'sell','tier':2,'icon':'🎯','color':'#FF1744','desc':'하락추세+MA저항','win':'60-70%'},
    'CS_Squeeze_Breakdown_Sell':{'name':'💨 Sq Break Dn','kor':'스퀴즈붕괴','dir':'sell','tier':2,'icon':'💨','color':'#FF6600','desc':'BB해소+하방','win':'60-70%'},
    'CS_MA_Breakdown_Sell':{'name':'📉 MA Break','kor':'MA붕괴','dir':'sell','tier':2,'icon':'📉','color':'#FF5252','desc':'데스+역배열','win':'60-70%'},
    'CS_Cooper_Setup_Sell':{'name':'🃏 Cooper Sell','kor':'쿠퍼매도','dir':'sell','tier':2,'icon':'🃏','color':'#FF3D00','desc':'ADX+쿠퍼매도','win':'60-70%'},
    'CS_Gap_Failure_Sell':{'name':'⏬ Gap Fail','kor':'갭실패','dir':'sell','tier':2,'icon':'⏬','color':'#FF1744','desc':'갭업후약세반전','win':'60-70%'},
    'CS_Oversold_Bounce_Buy':{'name':'🏓 OS Bounce','kor':'과매도반등','dir':'buy','tier':3,'icon':'🏓','color':'#69F0AE','desc':'Stoch과매도+캔들','win':'55-65%'},
    'CS_Momentum_Accel_Buy':{'name':'⚡ Mom Acc','kor':'모멘텀가속','dir':'buy','tier':3,'icon':'⚡','color':'#76FF03','desc':'RSI+WT+MACD가속','win':'55-65%'},
    'CS_Structure_Support_Buy':{'name':'🏗️ Support','kor':'구조적지지','dir':'buy','tier':3,'icon':'🏗️','color':'#4FC3F7','desc':'VP+BB지지','win':'55-65%'},
    'CS_Overbought_Fade_Sell':{'name':'📉 OB Fade','kor':'과매수페이드','dir':'sell','tier':3,'icon':'📉','color':'#FF5252','desc':'Stoch과매수+캔들','win':'55-65%'},
    'CS_Volatility_Explosion':{'name':'💣 Vol Explosion','kor':'변동성폭발셋업','dir':'neutral','tier':2,'icon':'💣','color':'#FFC107','desc':'NR7+BB스퀴즈','win':'방향70%+'},
}

# 강력매수/매도 차트 분류
STRONG_BUY_SIGS = {'Gold_Dot','Green_Dot_T1','Parabolic_Bottom_Buy','Volume_Climax_Buy','Momentum_Ignition_Buy',
    'Expansion_BO','Morning_Star','Reversal_New_Highs','CS_Ultimate_Buy','CS_Triple_Oversold_Reversal',
    'CS_Breakout_Momentum_Buy','CS_Capitulation_Bottom','CS_Divergence_Confluence_Buy','CS_Institutional_Accumulation'}
STRONG_SELL_SIGS = {'Blood_Diamond','Red_Dot_T1','Parabolic_Top_Sell','Volume_Climax_Sell','Momentum_Ignition_Sell',
    'Expansion_BD','Evening_Star','Reversal_New_Lows','CS_Ultimate_Sell','CS_Triple_Overbought_Exhaustion',
    'CS_Breakdown_Momentum_Sell','CS_Blow_Off_Top','CS_Divergence_Confluence_Sell','CS_Parabolic_Exhaustion_Sell'}

COOLDOWN_MAP = {
    'Squeeze_Fire_Buy':5,'Squeeze_Fire_Sell':5,'Bullish_Engulfing':5,'Bearish_Engulfing':5,
    'Hammer':5,'Shooting_Star':5,'Morning_Star':7,'Evening_Star':7,
    'Golden_Cross':20,'Death_Cross':20,'Expansion_BO':10,'Expansion_BD':10,
    'Gilligans_Buy':10,'Gilligans_Sell':10,'MACD_Cross_Buy':12,'MACD_Cross_Sell':12,
    'Kumo_Breakout_Bull':10,'Kumo_Breakout_Bear':10,'New_52W_High':10,'New_52W_Low':10,
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  유틸리티
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _recent(s,lb=3): return s.astype(float).rolling(lb+1,min_periods=1).max().fillna(0).astype(bool)
def _cooldown(sig,bars=5):
    v=sig.fillna(False).values.astype(bool);out=np.zeros(len(v),dtype=bool);last=-bars-1
    for i in range(len(v)):
        if v[i] and (i-last)>bars: out[i]=True;last=i
    return pd.Series(out,index=sig.index)
def _cd_dir(df,bs,ss,bars=5):
    bv=df.get(bs,pd.Series(False,index=df.index)).fillna(False).values.astype(bool)
    sv=df.get(ss,pd.Series(False,index=df.index)).fillna(False).values.astype(bool)
    bo=np.zeros(len(bv),dtype=bool);so=np.zeros(len(sv),dtype=bool);lb=-bars-1;ls_=-bars-1
    for i in range(len(df)):
        if sv[i]:lb=-bars-1
        if bv[i]:ls_=-bars-1
        if bv[i] and (i-lb)>bars:bo[i]=True;lb=i
        if sv[i] and (i-ls_)>bars:so[i]=True;ls_=i
    if bs in df.columns:df[bs]=pd.Series(bo,index=df.index)
    if ss in df.columns:df[ss]=pd.Series(so,index=df.index)
def _volf(vol,r=.5,p=20): return vol>=(vol.rolling(p,min_periods=5).mean()*r)
def _valid_fmt(t): return bool(re.match(r'^[A-Za-z]{1,5}([.\-][A-Za-z]{1,2})?$',t))
def _vs(cond):
    c=cond.astype(int);g=(c==0).cumsum();return c.groupby(g).cumsum()
def _sp(df,sn,pts): return np.where(df[sn].fillna(False),pts,0.) if sn in df.columns else 0.
def _spd(df,sn,fp,dd=3,dr=.5):
    if sn not in df.columns:return 0.
    b=np.where(df[sn].fillna(False),fp,0.);t=b.copy()
    for d in range(1,dd+1):s=np.roll(b,d);s[:d]=0;t+=s*(dr**d)
    return t

# 캐시
@st.cache_data(ttl=3600,show_spinner=False)
def fetch_fundamentals(t):
    try:
        i=yf.Ticker(t).info
        g=lambda k,f=None:f"${i[k]:,.2f}" if f=='$' and i.get(k) else (f"{i[k]:,.0f}" if f=='n' and i.get(k) else (f"{i[k]*100:.1f}%" if f=='%' and i.get(k) else str(i.get(k,'N/A'))))
        return f"MCap:{g('marketCap','n')} PE:{g('trailingPE')} 52H:{g('fiftyTwoWeekHigh','$')} 52L:{g('fiftyTwoWeekLow','$')} AvgVol:{g('averageVolume','n')}"
    except:return "N/A"
@st.cache_data(ttl=300,max_entries=30,show_spinner=False)
def fetch_history(t,_ts=None): return yf.Ticker(t).history(period="2y")
@st.cache_data(ttl=3600,show_spinner=False)
def fetch_spy(_ts=None): return yf.Ticker("SPY").history(period="2y")
@st.cache_data(ttl=600,show_spinner=False)
def validate_ticker(t):
    try:return not yf.Ticker(t).history(period="5d").empty
    except:return False
@st.cache_data(ttl=300,max_entries=50,show_spinner=False)
def _compute_cached(t,k):
    df=fetch_history(t);return detect_all_signals(compute_indicators(df)) if not df.empty else None
def compute_and_cache(t,ts=None):
    ck=f"{t}_{ts}" if ts else f"{t}_{math.floor(time.time()/300)}";return _compute_cached(t,ck)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  기술지표
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def compute_rsi(s,p=14):
    d=s.diff();g,l=d.clip(lower=0),-d.clip(upper=0)
    return 100-(100/(1+g.ewm(alpha=1/p,min_periods=p).mean()/(l.ewm(alpha=1/p,min_periods=p).mean()+1e-10)))
def compute_mfi(h,l,c,v,p=14):
    tp=(h+l+c)/3;r=tp*v;d=tp.diff()
    return 100-(100/(1+r.where(d>=0,0.).rolling(p).sum()/(r.where(d<0,0.).rolling(p).sum()+1e-10)))
def compute_rsi_mfi(h,l,c,v,p=60):
    rf,mf=compute_rsi(c,20),compute_mfi(h,l,c,v,20);rs,ms=compute_rsi(c,p),compute_mfi(h,l,c,v,p)
    return (((rf-50)+(mf-50))/2)*.6+(((rs-50)+(ms-50))/2)*.4
def compute_wavetrend(h,l,c,ch=9,avg=12,ma=3):
    ap=(h+l+c)/3;esa=ap.ewm(span=ch,adjust=False).mean()
    d=abs(ap-esa).ewm(span=ch,adjust=False).mean();ci=(ap-esa)/(0.015*d+1e-10)
    w1=ci.ewm(span=avg,adjust=False).mean();w2=w1.rolling(ma).mean()
    return w1,w2,(w1>w2)&(w1.shift(1)<=w2.shift(1)),(w1<w2)&(w1.shift(1)>=w2.shift(1))
def compute_stoch_rsi(c,rl=14,sl=14,ks=3,ds=3):
    r=compute_rsi(c,rl);mn,mx=r.rolling(sl).min(),r.rolling(sl).max()
    k=(((r-mn)/(mx-mn+1e-10))*100).rolling(ks).mean();return k,k.rolling(ds).mean()
def compute_tr(h,l,c):
    pc=c.shift(1);return pd.concat([h-l,(h-pc).abs(),(l-pc).abs()],axis=1).max(axis=1)
def compute_adx(h,l,c,p=14):
    tr=compute_tr(h,l,c);ph,pl=h.shift(1),l.shift(1)
    pd_=pd.Series(np.where((h-ph)>(pl-l),np.maximum(h-ph,0),0),index=h.index,dtype=float)
    md=pd.Series(np.where((pl-l)>(h-ph),np.maximum(pl-l,0),0),index=h.index,dtype=float)
    a=tr.ewm(alpha=1/p,min_periods=p).mean()
    pi_=100*pd_.ewm(alpha=1/p,min_periods=p).mean()/(a+1e-10)
    mi_=100*md.ewm(alpha=1/p,min_periods=p).mean()/(a+1e-10)
    dx=100*(pi_-mi_).abs()/(pi_+mi_+1e-10);return dx.ewm(alpha=1/p,min_periods=p).mean(),pi_,mi_
def compute_obv(c,v): return (v*np.sign(c.diff()).fillna(0)).cumsum()
def compute_macd(c,f=12,s=26,sig=9):
    ml=c.ewm(span=f,adjust=False).mean()-c.ewm(span=s,adjust=False).mean()
    sl=ml.ewm(span=sig,adjust=False).mean();return ml,sl,ml-sl
def compute_ichimoku(h,l,c,tp=9,kp=26,sp=52,d=26):
    tk=(h.rolling(tp).max()+l.rolling(tp).min())/2;kj=(h.rolling(kp).max()+l.rolling(kp).min())/2
    sa=((tk+kj)/2).shift(d);sb=((h.rolling(sp).max()+l.rolling(sp).min())/2).shift(d)
    return tk,kj,sa,sb
def compute_cmf(h,l,c,v,p=20):
    m=((c-l)-(h-c))/(h-l+1e-10);return (m*v).rolling(p).sum()/(v.rolling(p).sum()+1e-10)
def compute_supertrend(h,l,c,tr,per=10,mult=3.):
    a=tr.rolling(per).mean();hl=(h+l)/2;up=(hl+mult*a).values.copy();dn=(hl-mult*a).values.copy()
    cl=c.values;n=len(c);sv=np.full(n,np.nan);dv=np.zeros(n,dtype=int);fv=per
    if fv>=n:return pd.Series(np.nan,index=c.index),pd.Series(0,index=c.index,dtype=int)
    dv[fv]=1;sv[fv]=dn[fv]
    for i in range(fv+1,n):
        if dv[i-1]==1:dn[i]=max(dn[i],dn[i-1]) if not np.isnan(dn[i-1]) else dn[i]
        else:up[i]=min(up[i],up[i-1]) if not np.isnan(up[i-1]) else up[i]
        if dv[i-1]==1:dv[i],sv[i]=(-1,up[i]) if cl[i]<dn[i] else (1,dn[i])
        else:dv[i],sv[i]=(1,dn[i]) if cl[i]>up[i] else (-1,up[i])
    return pd.Series(sv,index=c.index),pd.Series(dv,index=c.index)
def compute_vp(h,l,c,v,lb=20,nb=30):
    n=len(c);poc=np.full(n,np.nan);vah=np.full(n,np.nan);val_=np.full(n,np.nan)
    cv,hv,lv,vv=c.values,h.values,l.values,v.values
    for i in range(lb,n):
        s=i-lb;hw,lw,vw=hv[s:i+1],lv[s:i+1],vv[s:i+1];pl,ph=lw.min(),hw.max()
        if ph-pl<1e-10:poc[i]=cv[i];vah[i]=ph;val_[i]=pl;continue
        tp_=(hw+lw+cv[s:i+1])/3;vp_,be=np.histogram(tp_,bins=nb,range=(pl,ph),weights=vw)
        bc=(be[:-1]+be[1:])/2;pb_=np.argmax(vp_);poc[i]=bc[pb_]
        tv=vp_.sum();tgt=tv*.7;cm=vp_[pb_];lo,hi=pb_,pb_
        while cm<tgt and (lo>0 or hi<nb-1):
            lv_=vp_[lo-1] if lo>0 else 0;hv_=vp_[hi+1] if hi<nb-1 else 0
            if lv_>=hv_ and lo>0:lo-=1;cm+=lv_
            elif hi<nb-1:hi+=1;cm+=hv_
            else:break
        vah[i]=be[min(hi+1,nb)];val_[i]=be[lo]
    return pd.Series(poc,index=c.index),pd.Series(vah,index=c.index),pd.Series(val_,index=c.index)

def detect_pivot_div(price,osc,lb=60,pw=5,os_lim=None,ob_lim=None,atr=None):
    n=len(price);pv=price.values.astype(float);ov=osc.values.astype(float)
    dl=np.full(n,lb,dtype=int)
    if atr is not None and len(atr)>0:
        ap=atr/(price+1e-10)*100;ar=ap/(ap.rolling(100,min_periods=20).median()+1e-10)
        ls_=np.clip(1.3-.35*ar.values,.5,1.5);dl=np.clip(lb*ls_,30,90).astype(int)
    pm=max(np.nanmean(np.nan_to_num((atr.rolling(20,min_periods=5).mean()*.3).values,nan=.01)),.01) if atr is not None else max(np.percentile(np.abs(np.diff(pv,prepend=pv[0])),75)*2,.01)
    li,_=find_peaks(-pv,distance=pw,prominence=pm);hi,_=find_peaks(pv,distance=pw,prominence=pm)
    bd=np.zeros(n,dtype=bool);brd=np.zeros(n,dtype=bool);hb=np.zeros(n,dtype=bool);hbr=np.zeros(n,dtype=bool)
    for i in range(1,len(li)):
        ci,pi=li[i],li[i-1];g=ci-pi
        if g<pw*2 or g>dl[ci]:continue
        if pv[ci]<pv[pi] and ov[ci]>ov[pi]:
            if os_lim is None or ov[ci]<=os_lim:bd[min(ci+pw,n-1)]=True
        if pv[ci]>pv[pi] and ov[ci]<ov[pi]:hb[min(ci+pw,n-1)]=True
    for i in range(1,len(hi)):
        ci,pi=hi[i],hi[i-1];g=ci-pi
        if g<pw*2 or g>dl[ci]:continue
        if pv[ci]>pv[pi] and ov[ci]<ov[pi]:
            if ob_lim is None or ov[ci]>=ob_lim:brd[min(ci+pw,n-1)]=True
        if pv[ci]<pv[pi] and ov[ci]>ov[pi]:hbr[min(ci+pw,n-1)]=True
    return (pd.Series(bd,index=price.index),pd.Series(brd,index=price.index),
            pd.Series(hb,index=price.index),pd.Series(hbr,index=price.index))

def compute_indicators(df):
    c,h,l,v=df['Close'],df['High'],df['Low'],df['Volume']
    for ma in [5,10,20,50,100,125,200]:df[f'MA{ma}']=c.rolling(ma).mean()
    df['EMA8']=c.ewm(span=8,adjust=False).mean();df['EMA21']=c.ewm(span=21,adjust=False).mean()
    df['BB_Mid']=df['MA20'];s20=c.rolling(20).std()
    df['BB_Up'],df['BB_Low']=df['BB_Mid']+s20*2,df['BB_Mid']-s20*2
    df['BB_Width']=(df['BB_Up']-df['BB_Low'])/(df['BB_Mid']+1e-10)
    df['Percent_B']=(c-df['BB_Low'])/(df['BB_Up']-df['BB_Low']+1e-10)
    tr=compute_tr(h,l,c);df['ATR']=tr.rolling(14).mean()
    df['SuperTrend'],df['ST_Direction']=compute_supertrend(h,l,c,tr)
    ak=tr.rolling(10).mean();mk=c.ewm(span=20,adjust=False).mean()
    df['KC_Upper']=mk+ak*1.5;df['KC_Mid']=mk;df['KC_Lower']=mk-ak*1.5
    w1,w2,wu,wd=compute_wavetrend(h,l,c)
    df['WT1'],df['WT2'],df['WT_Up'],df['WT_Down']=w1,w2,wu,wd
    df['RSI']=compute_rsi(c,14);df['StochK'],df['StochD']=compute_stoch_rsi(c)
    df['MFI']=compute_mfi(h,l,c,v,14);df['RSI_MFI']=compute_rsi_mfi(h,l,c,v,60)
    vw=(c*v).rolling(20).sum()/(v.rolling(20).sum()+1e-10);df['VWAP_Osc']=((c-vw)/(vw+1e-10))*100
    df['ADX'],df['Plus_DI'],df['Minus_DI']=compute_adx(h,l,c)
    df['OBV']=compute_obv(c,v)
    df['MACD_Line'],df['MACD_Signal'],df['MACD_Hist']=compute_macd(c)
    tk,kj,sa,sb=compute_ichimoku(h,l,c)
    df['Ichimoku_Tenkan']=tk;df['Ichimoku_Kijun']=kj;df['Ichimoku_SenkouA']=sa;df['Ichimoku_SenkouB']=sb
    df['CMF']=compute_cmf(h,l,c,v,20)
    # 가속도
    rv=df['RSI']-df['RSI'].shift(3);df['RSI_Accel']=rv-rv.shift(3)
    wv=df['WT1']-df['WT1'].shift(3);df['WT_Accel']=wv-wv.shift(3)
    df['MACD_Accel']=df['MACD_Hist']-df['MACD_Hist'].shift(3)
    rn=df['RSI_Accel']/(df['RSI_Accel'].rolling(50,min_periods=10).std()+1e-10)
    wn=df['WT_Accel']/(df['WT_Accel'].rolling(50,min_periods=10).std()+1e-10)
    mn=df['MACD_Accel']/(df['MACD_Accel'].rolling(50,min_periods=10).std()+1e-10)
    df['Composite_Accel']=(rn+wn+mn)/3
    # WT 수렴
    gap=df['WT1']-df['WT2'];ga=gap.abs();df['WT_Conv_Speed']=ga.shift(3)-ga
    # VP
    df['VP_POC'],df['VP_VAH'],df['VP_VAL']=compute_vp(h,l,c,v)
    # RS
    try:
        spy=fetch_spy()
        if not spy.empty:
            sc_=df['Close'].copy();spc=spy['Close'].reindex(sc_.index,method='ffill')
            sr=sc_.pct_change(20).fillna(0);spr=spc.pct_change(20).fillna(0)
            df['RS_Ratio']=((1+sr)/(1+spr+1e-10)).rolling(10,min_periods=5).mean()
    except:df['RS_Ratio']=1.0
    # Regime
    sc_=pd.Series(0.,index=df.index)
    sc_+=np.where(c>df['MA200'],1,-1);sc_+=np.where(c>df['MA50'],1,-1);sc_+=np.where(c>df['MA20'],.5,-.5)
    sc_+=np.where(df['MA50']>df['MA50'].shift(10),1,-1);sc_+=np.where(df['ST_Direction']==1,1,-1)
    sc_+=np.where(df['Plus_DI']>df['Minus_DI'],.5,-.5);sc_+=np.where(df['MACD_Line']>0,.5,-.5)
    rr=sc_.rolling(5,min_periods=3).mean();df['Regime_Score']=rr.clip(-8,8)
    df['Regime']=np.select([rr>=4,rr>=1.5,rr<=-4,rr<=-1.5],[2,1,-2,-1],default=0)
    return df

print("✅ Part 1/4 완료")

# ══════════════════════════════════════════════════════════════
#  CipherX V13.0 — PART 2/4
#  125개 시그널 탐지 + Combined Scan + 10-Layer Judgment Engine
# ══════════════════════════════════════════════════════════════

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  개별 시그널 탐지 함수들
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def det_123pb(h,l,c,adx,pdi,mdi):
    sb=(adx>30)&(pdi>mdi);sbe=(adx>30)&(mdi>pdi)
    ins=(h<h.shift(1))&(l>l.shift(1))
    l1,l2,l3=l<l.shift(1),l.shift(1)<l.shift(2),l.shift(2)<l.shift(3)
    tl=l1&l2&l3;tli=(l1&l2&ins.shift(2))|(l1&ins.shift(1)&l2.shift(1))|(ins&l1&l2)
    h1,h2,h3=h>h.shift(1),h.shift(1)>h.shift(2),h.shift(2)>h.shift(3)
    th=h1&h2&h3;thi=(h1&h2&ins.shift(2))|(h1&ins.shift(1)&h2.shift(1))|(ins&h1&h2)
    return sb&(tl|tli),sbe&(th|thi)

def det_180(c,o,h,l,m10,m50):
    dr=h-l+1e-10;cp=(c-l)/dr;pp=(c.shift(1)-l.shift(1))/(h.shift(1)-l.shift(1)+1e-10)
    return (pp<=.25)&(cp>=.75)&(c>m10)&(c>m50),(pp>=.75)&(cp<=.25)&(c<m10)&(c<m50)

def det_boomer(h,l,adx,pdi,mdi):
    ins=(h<h.shift(1))&(l>l.shift(1));in2=ins&ins.shift(1)
    return in2.shift(1).fillna(False)&(adx>30)&(pdi>mdi),in2.shift(1).fillna(False)&(adx>30)&(mdi>pdi)

def det_expansion(h,l,c):
    dr=h-l;mr=dr.rolling(9).max();h60=h.rolling(60,min_periods=40).max();l60=l.rolling(60,min_periods=40).min()
    return (h>=h60)&(dr>=mr),(l<=l60)&(dr>=mr)

def det_exp_pivot(c,h,l,m50):
    dr=h-l;mr=dr.rolling(9).max()
    return (dr>=mr)&((l<=m50)|(l.shift(1)<=m50.shift(1)))&(c>m50),(dr>=mr)&((h>=m50)|(h.shift(1)>=m50.shift(1)))&(c<m50)

def det_exp_dbl(c,o,h,l):
    dr=h-l;r=dr.rolling(10).rank(pct=True);h60=h.rolling(60,min_periods=40).max()
    return (h.shift(1)>=h60.shift(1))&(r.shift(1)>=.7)&(c<o)&(r>=.7)

def det_gilligans(o,c,h,l):
    dr=h-l+1e-10;cp=(c-l)/dr;l60=l.rolling(60,min_periods=40).min();h60=h.rolling(60,min_periods=40).max()
    return (o<=l60)&(o<l.shift(1))&(cp>=.5)&(c>=o),(o>=h60)&(o>h.shift(1))&(cp<=.5)&(c<=o)

def det_lizard(o,c,h,l):
    dr=h-l+1e-10;cp=(c-l)/dr;op=(o-l)/dr
    return (cp>=.75)&(op>=.75)&(l<=l.rolling(10).min()),(cp<=.25)&(op<=.25)&(h>=h.rolling(10).max())

def det_slingshot(c,o,h,l):
    h60=h.rolling(60,min_periods=40).max();l60=l.rolling(60,min_periods=40).min()
    return (h.shift(1)>=h60.shift(1))&(l<l.shift(1)-.10),(l.shift(1)<=l60.shift(1))&(h>h.shift(1)+.10)

def det_jack(h,l,c,df):
    ins=(h<h.shift(1))&(l>l.shift(1))
    xb=df.get('Expansion_BO',pd.Series(False,index=df.index)).fillna(False)
    xd=df.get('Expansion_BD',pd.Series(False,index=df.index)).fillna(False)
    return xb.shift(2).fillna(False)&ins.shift(1).fillna(False)&(c>h.shift(2)),xd.shift(2).fillna(False)&ins.shift(1).fillna(False)&(c<l.shift(2))

def det_nonadx(h,l,c,m50):
    ins=(h<h.shift(1))&(l>l.shift(1))
    l1,l2=l<l.shift(1),l.shift(1)<l.shift(2)
    tl=l1&l2&(l.shift(2)<l.shift(3));tli=(l1&l2&ins.shift(2))|(l1&ins.shift(1)&l2.shift(1))|(ins&l1&l2)
    h1,h2=h>h.shift(1),h.shift(1)>h.shift(2)
    th=h1&h2&(h.shift(2)>h.shift(3));thi=(h1&h2&ins.shift(2))|(h1&ins.shift(1)&h2.shift(1))|(ins&h1&h2)
    return (c>m50)&(tl|tli),(c<m50)&(th|thi)

def det_rev_hl(c,o,h,l):
    dr=h-l;mr=dr.rolling(5).max();h60=h.rolling(60,min_periods=40).max();l60=l.rolling(60,min_periods=40).min()
    out=(h>h.shift(1))&(l<l.shift(1))
    return (h>=h60)&out&(dr>=mr)&(c>o),(l<=l60)&out&(dr>=mr)&(c<o)

def det_ma_sr(c,o,h,l,ma,atr):
    md=(c-ma).abs()/(atr+1e-10);nr=md<.2
    return nr&(c>ma)&(l<=ma*1.01)&(c>o),nr&(c<ma)&(h>=ma*.99)&(c<o)

def det_candles(c,o,h,l,wt1,atr,v):
    body=(c-o).abs();us=h-pd.concat([c,o],axis=1).max(axis=1)
    ls_=pd.concat([c,o],axis=1).min(axis=1)-l;fr=h-l+1e-10;ab=body.rolling(20).mean()
    sm=body<ab*.6;mr=atr*.5;vk=v>=v.rolling(10,min_periods=5).mean()*.5;vs=v>v.rolling(10,min_periods=5).mean()*1.2
    ham=(ls_>=body*2)&(us<=body*.3)&sm&(wt1<-20)&(c>=o)&(fr>mr)&vk
    sho=(us>=body*2)&(ls_<=body*.3)&sm&(wt1>20)&(c<=o)&(fr>mr)&vk
    doji=(body<=fr*.05)&(fr>atr*.3)
    db=doji&(wt1<-30)&(wt1>wt1.shift(1))&vk;dbe=doji&(wt1>30)&(wt1<wt1.shift(1))&vk
    d1b=(c.shift(2)<o.shift(2))&(body.shift(2)>ab.shift(2));d2s=body.shift(1)<ab.shift(1)*.5
    d3u=(c>o)&(c>(o.shift(2)+c.shift(2))/2)&(body>ab*.8);ms=d1b&d2s&d3u&(wt1<-15)&vs
    d1u=(c.shift(2)>o.shift(2))&(body.shift(2)>ab.shift(2))
    d3d=(c<o)&(c<(o.shift(2)+c.shift(2))/2)&(body>ab*.8);es=d1u&d2s&d3d&(wt1>15)&vs
    sp=sm&(us>body*.5)&(ls_>body*.5)
    return {'Hammer':ham,'Shooting_Star':sho,'Doji':doji,'Doji_Bullish':db,'Doji_Bearish':dbe,
            'Morning_Star':ms,'Evening_Star':es,'Spinning_Top':sp}

def det_engulf(c,o,wt1,m50,v):
    body=(c-o).abs();pb=(c.shift(1)-o.shift(1)).abs();ab=body.rolling(20).mean()
    big=(body>ab*.8)&(body>pb)
    ph=pd.concat([c.shift(1),o.shift(1)],axis=1).max(axis=1)
    pl=pd.concat([c.shift(1),o.shift(1)],axis=1).min(axis=1)
    ch=pd.concat([c,o],axis=1).max(axis=1);cl_=pd.concat([c,o],axis=1).min(axis=1)
    vk=v>=v.rolling(10,min_periods=5).mean()*.5
    bu=(c.shift(1)<o.shift(1))&(c>o)&(cl_<=pl)&(ch>=ph)&big&(wt1<-20)&vk
    be=(c.shift(1)>o.shift(1))&(c<o)&(cl_<=pl)&(ch>=ph)&big&(wt1>20)&vk
    return bu,be

def det_bb(c,o,h,l,bbu,bbl,bbw,kcu,kcl):
    sq=(bbu<kcu)&(bbl>kcl);ss=sq&~sq.shift(1).fillna(False);se=~sq&sq.shift(1).fillna(False)
    seb=se&(c>c.shift(1))&(c>o);ses=se&(c<c.shift(1))&(c<o)
    ut=h>=bbu;lt=l<=bbl;ub=c>bbu;lb=(c<bbl)&(c<o);lbo=(c<bbl)&(c>o)&(c>c.shift(1))
    uw=ut.rolling(3).sum()>=3;lw=lt.rolling(3).sum()>=3
    wd=bbw.rolling(126,min_periods=60).rank(pct=True)>=.9
    tight=bbw<=bbw.rolling(126,min_periods=60).min()*1.05
    return {'Squeeze_On':sq,'BB_Squeeze':tight,'BB_Squeeze_Started':ss,'BB_Squeeze_End_Bull':seb,
            'BB_Squeeze_End_Bear':ses,'BB_Upper_Touch':ut&~ub,'BB_Lower_Touch':lt&~lb,
            'BB_Upper_Break':ub,'BB_Lower_Break':lb,'BB_Lower_Bounce':lbo,
            'BB_Upper_Walk':uw,'BB_Lower_Walk':lw,'BB_Wide_Bands':wd}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  detect_all_signals — 125개 시그널 통합 탐지
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def detect_all_signals(df):
    H,L,C,O,V=df['High'],df['Low'],df['Close'],df['Open'],df['Volume']
    e8,e21=df['EMA8'],df['EMA21'];m10,m20,m50,m200=df['MA10'],df['MA20'],df['MA50'],df['MA200']
    wt1,wt2,atr=df['WT1'],df['WT2'],df['ATR'];adx,pdi,mdi=df['ADX'],df['Plus_DI'],df['Minus_DI']
    idx=df.index;vok=_volf(V,.5)
    wur=_recent(df['WT_Up'],2);wdr=_recent(df['WT_Down'],2)
    htf=(e8>e21)&(e21>e21.shift(5))&(C>m50)&(m50>m50.shift(10))

    # MCB+
    df['Green_Dot_T1']=wur&(wt1<=OS1)&(df['RSI']<30)&(df['MFI']<30)&vok
    df['Green_Dot_T2']=wur&(wt1<=OS1)&((df['RSI']<32)|(df['MFI']<32))&~df['Green_Dot_T1']&vok
    df['Red_Dot_T1']=wdr&(wt1>=OB1)&(df['RSI']>70)&(df['MFI']>70)&vok
    df['Red_Dot_T2']=wdr&(wt1>=OB1)&((df['RSI']>68)|(df['MFI']>68))&~df['Red_Dot_T1']&vok
    df['Blue_Diamond']=(wt2<=0)&wur&htf&vok
    df['Red_Diamond']=(wt2>=0)&wdr&~htf&vok
    df['Green_Circle']=wur&(wt1<=OS1)&~df['Green_Dot_T1']&~df['Green_Dot_T2']&vok&(df['RSI']<45)
    df['Red_Circle']=wdr&(wt1>=OB1)&~df['Red_Dot_T1']&~df['Red_Dot_T2']&vok&(df['RSI']>55)

    # 다이버전스
    bd,brd,hb,hbr=detect_pivot_div(C,wt1,60,5,OS1,OB1,atr=atr)
    rbd,rbrd,_,_=detect_pivot_div(C,df['RSI'],60,5,35,65,atr=atr)
    obd,obrd,_,_=detect_pivot_div(C,df['OBV'],60,5,atr=atr)
    df['Gold_Dot']=df['Green_Dot_T1']&(wt1<=OS2)&_recent(bd,3)
    df['Blood_Diamond']=df['Red_Dot_T1']&(wt1>=OB2)&_recent(brd,3)
    df['Bull_Divergence']=bd&~df['Gold_Dot']&vok;df['Bear_Divergence']=brd&~df['Blood_Diamond']&vok
    df['RSI_Bull_Divergence']=rbd&(wt1<-20)&vok;df['RSI_Bear_Divergence']=rbrd&(wt1>20)&vok
    df['Hidden_Bull_Div']=hb&(wt1<-25)&htf&vok;df['Hidden_Bear_Div']=hbr&(wt1>25)&~htf&vok
    df['OBV_Div_Buy']=obd&(wt1<-30);df['OBV_Div_Sell']=obrd&(wt1>30)

    # Cooper
    df['Pullback_123_Bull'],df['Pullback_123_Bear']=det_123pb(H,L,C,adx,pdi,mdi)
    df['Setup_180_Bull'],df['Setup_180_Bear']=det_180(C,O,H,L,m10,m50)
    df['Boomer_Buy'],df['Boomer_Sell']=det_boomer(H,L,adx,pdi,mdi)
    df['Expansion_BO'],df['Expansion_BD']=det_expansion(H,L,C)
    df['Expansion_Pivot_Buy'],df['Expansion_Pivot_Sell']=det_exp_pivot(C,H,L,m50)
    df['Expansion_Double_Sticks']=det_exp_dbl(C,O,H,L)
    df['Gilligans_Buy'],df['Gilligans_Sell']=det_gilligans(O,C,H,L)
    df['Lizard_Bull'],df['Lizard_Bear']=det_lizard(O,C,H,L)
    df['Slingshot_Bull'],df['Slingshot_Bear']=det_slingshot(C,O,H,L)
    df['Jack_In_Box_Bull'],df['Jack_In_Box_Bear']=det_jack(H,L,C,df)
    df['NonADX_123_Bull'],df['NonADX_123_Bear']=det_nonadx(H,L,C,m50)
    df['Reversal_New_Highs'],df['Reversal_New_Lows']=det_rev_hl(C,O,H,L)

    # MA
    df['MA20_Support'],df['MA20_Resistance']=det_ma_sr(C,O,H,L,m20,atr)
    df['MA50_Support'],df['MA50_Resistance']=det_ma_sr(C,O,H,L,m50,atr)
    df['MA200_Support'],df['MA200_Resistance']=det_ma_sr(C,O,H,L,m200,atr)
    for tag,ma in [('20MA',m20),('50MA',m50),('200MA',m200)]:
        df[f'Cross_Above_{tag}']=(C>ma)&(C.shift(1)<=ma.shift(1))
        df[f'Fell_Below_{tag}']=(C<ma)&(C.shift(1)>=ma.shift(1))
    gc=(m50>m200)&(m50.shift(1)<=m200.shift(1));dc_=(m50<m200)&(m50.shift(1)>=m200.shift(1))
    df['Golden_Cross']=gc&(adx>15);df['Death_Cross']=dc_&(adx>15)
    df['MTF_All_Bullish']=(C>m10)&(C>m50)&(C>m200);df['MTF_All_Bearish']=(C<m10)&(C<m50)&(C<m200)

    # BB
    for k,v_ in det_bb(C,O,H,L,df['BB_Up'],df['BB_Low'],df['BB_Width'],df['KC_Upper'],df['KC_Lower']).items():df[k]=v_

    # 캔들
    for k,v_ in det_candles(C,O,H,L,wt1,atr,V).items():df[k]=v_
    df['Bullish_Engulfing'],df['Bearish_Engulfing']=det_engulf(C,O,wt1,m50,V)
    ins=(H<H.shift(1))&(L>L.shift(1));out=(H>H.shift(1))&(L<L.shift(1))
    df['Inside_Day']=ins;df['Outside_Bullish']=out&(C>O)&(C>H.shift(1))&vok;df['Outside_Bearish']=out&(C<O)&(C<L.shift(1))&vok

    # MACD
    ml,ms_=df['MACD_Line'],df['MACD_Signal']
    df['MACD_Cross_Buy']=((ml>ms_)&(ml.shift(1)<=ms_.shift(1))&(ml<0))&vok
    df['MACD_Cross_Sell']=((ml<ms_)&(ml.shift(1)>=ms_.shift(1))&(ml>0))&vok
    df['MACD_Zero_Cross_Buy']=(ml>0)&(ml.shift(1)<=0);df['MACD_Zero_Cross_Sell']=(ml<0)&(ml.shift(1)>=0)

    # Stoch
    stk,std_=df['StochK'],df['StochD']
    df['StochRSI_Cross_Buy']=(stk>std_)&(stk.shift(1)<=std_.shift(1))&(stk<25)
    df['StochRSI_Cross_Sell']=(stk<std_)&(stk.shift(1)>=std_.shift(1))&(stk>75)
    df['Stoch_Reached_OB']=(stk>=80)&(stk.shift(1)<80);df['Stoch_Reached_OS']=(stk<=20)&(stk.shift(1)>20)
    df['Stoch_Overbought']=(stk>80)&(std_>80);df['Stoch_Oversold']=(stk<20)&(std_<20)

    # ADX/DMI
    df['DMI_Cross_Bull']=((pdi>mdi)&(pdi.shift(1)<=mdi.shift(1)))&vok
    df['DMI_Cross_Bear']=((mdi>pdi)&(mdi.shift(1)<=pdi.shift(1)))&vok
    df['ADX_New_Uptrend']=(adx>25)&(adx.shift(1)<=25)&(pdi>mdi)&vok
    df['ADX_New_Downtrend']=(adx>25)&(adx.shift(1)<=25)&(mdi>pdi)&vok
    df['ADX_Momentum_Buy']=(adx>20)&(adx.shift(1)<=20)&(pdi>mdi)&vok
    df['ADX_Momentum_Sell']=(adx>20)&(adx.shift(1)<=20)&(mdi>pdi)&vok

    # RSI
    rsi=df['RSI']
    df['RSI_Cross_30_Up']=(rsi>30)&(rsi.shift(1)<=30);df['RSI_Cross_50_Up']=(rsi>50)&(rsi.shift(1)<=50)
    df['RSI_Cross_70_Down']=(rsi<70)&(rsi.shift(1)>=70);df['RSI_Cross_50_Down']=(rsi<50)&(rsi.shift(1)>=50)

    # 갭
    t=atr*.5;gu=(O>H.shift(1))&((O-H.shift(1))>t);gd=(O<L.shift(1))&((L.shift(1)-O)>t)
    df['Gap_Up']=gu;df['Gap_Down']=gd
    df['Gap_Up_Closed']=gu.shift(1).fillna(False)&(L<=H.shift(2));df['Gap_Down_Closed']=gd.shift(1).fillna(False)&(H>=L.shift(2))

    # 범위
    dr=H-L;nr7m=dr.rolling(7).min();nr7=dr<=nr7m
    df['NR7']=nr7;df['NR7_2']=nr7&nr7.shift(1).fillna(False)
    df['Narrow_Range_Bar']=dr<atr*.5;df['Wide_Range_Bar']=dr>atr*2
    df['Calm_After_Storm']=(dr>atr*2).rolling(5,min_periods=1).max().shift(1).fillna(False).astype(bool)&(dr<atr*.5)

    # 52주
    h252=H.rolling(252,min_periods=200).max().shift(1);l252=L.rolling(252,min_periods=200).min().shift(1)
    df['New_52W_High']=H>h252;df['New_52W_Low']=L<l252
    c252h=C.rolling(252,min_periods=200).max().shift(1);c252l=C.rolling(252,min_periods=200).min().shift(1)
    df['New_52W_Closing_High']=C>c252h;df['New_52W_Closing_Low']=C<c252l

    # 연속
    up=C>C.shift(1);dn=C<C.shift(1);us=_vs(up);ds=_vs(dn)
    df['Up_3_Days']=us>=3;df['Up_4_Days']=us>=4;df['Up_5_Days']=us>=5
    df['Down_3_Days']=ds>=3;df['Down_4_Days']=ds>=4;df['Down_5_Days']=ds>=5

    # 기타
    n10=(C/10).round()*10;dist=(C-n10).abs();nrd=dist<atr*.5
    df['Multiple_Ten_Bull']=nrd&(C.shift(1)<n10)&(C>n10)&(C>O);df['Multiple_Ten_Bear']=nrd&(C.shift(1)>n10)&(C<n10)&(C<O)
    dv=V.where(C<C.shift(1),0);df['Pocket_Pivot']=(C>O)&(V>dv.rolling(10).max())&(C>m50)&(C>C.shift(1))
    df['Parabolic_Rise']=(C-C.shift(10))/(C.shift(10)+1e-10)>.3
    df['Three_Weeks_Tight']=((C.rolling(15).max()-C.rolling(15).min())/(C.rolling(15).min()+1e-10))<.015
    avg_v=V.rolling(50,min_periods=10).mean();vr=V/(avg_v+1e-10);vz=(V-avg_v)/(V.rolling(20).std()+1e-10)
    df['Volume_Surge']=vr>=3
    big=(C-O).abs()>atr*.5;ps=(vz.shift(1)>2.5)&big.shift(1)
    df['Volume_Climax_Buy']=ps&(C.shift(1)<O.shift(1))&(wt1.shift(1)<-40)&(C>O)
    df['Volume_Climax_Sell']=ps&(C.shift(1)>O.shift(1))&(wt1.shift(1)>40)&(C<O)

    # TTM Squeeze
    mom=C-((H.rolling(20).max()+L.rolling(20).min())/2+df['KC_Mid'])/2
    sf=~df['Squeeze_On']&df['Squeeze_On'].shift(1).fillna(False)
    df['Squeeze_Fire_Buy']=sf&(mom>0)&(mom>mom.shift(1))&vok;df['Squeeze_Fire_Sell']=sf&(mom<0)&(mom<mom.shift(1))&vok

    # SuperTrend
    df['SuperTrend_Buy']=(df['ST_Direction']==1)&(df['ST_Direction'].shift(1)==-1)
    df['SuperTrend_Sell']=(df['ST_Direction']==-1)&(df['ST_Direction'].shift(1)==1)

    # EMA PB
    ar_=atr/(C+1e-10);vk2=_volf(V,.5)
    su=e21>e21.shift(5);tu=(e8>e21)&su&(C>e8)
    tcu=(L<=e8*(1+ar_*.15))&(L>=e21*(1-ar_*.25));bcu=(C>=e8)&(C>H.shift(1))&(wt1>wt1.shift(1))&(wt1>wt2)&(wt1<60)
    df['EMA_Pullback_Buy']=tu&_recent(tcu,2)&bcu&vk2
    sd_=e21<e21.shift(5);td=(e8<e21)&sd_&(C<e8)
    tcd=(H>=e8*(1-ar_*.15))&(H<=e21*(1+ar_*.25));bcd=(C<=e8)&(C<L.shift(1))&(wt1<wt1.shift(1))&(wt1<wt2)&(wt1>-60)
    df['EMA_Pullback_Sell']=td&_recent(tcd,2)&bcd&vk2

    # Mom Ignition
    body_=(C-O).abs();bb_=body_>atr*1.5;hv_=V>V.rolling(20).mean()*2;comp=df['BB_Width'].shift(1)<df['BB_Width'].rolling(20).mean().shift(1)
    df['Momentum_Ignition_Buy']=(C>O)&bb_&hv_&(C>df['BB_Up'])&(e8>e21)&(wt1<50)&comp
    df['Momentum_Ignition_Sell']=(C<O)&bb_&hv_&(C<df['BB_Low'])&(e8<e21)&(wt1>-50)&comp

    # Parabolic
    df['Parabolic_Bottom_Buy']=((wt1<-80)&(wt1>wt1.shift(1))&(C>O))|((C<df['BB_Low']-atr*1.5)&(C>O))
    df['Parabolic_Top_Sell']=((wt1>80)&(wt1<wt1.shift(1))&(C<O))|((C>df['BB_Up']+atr*1.5)&(C<O))

    # VWAP
    vk3=_volf(V,.7)
    df['VWAP_Bounce_Buy']=(df['VWAP_Osc']>0)&(df['VWAP_Osc'].shift(1)<-.5)&(wt1>wt2)&(wt1<30)&vk3
    df['VWAP_Reject_Sell']=(df['VWAP_Osc']<0)&(df['VWAP_Osc'].shift(1)>.5)&(wt1<wt2)&(wt1>-30)&vk3

    # 이치모쿠
    tk,kj=df['Ichimoku_Tenkan'],df['Ichimoku_Kijun'];sa,sb=df['Ichimoku_SenkouA'],df['Ichimoku_SenkouB']
    kt=pd.concat([sa,sb],axis=1).max(axis=1);kb=pd.concat([sa,sb],axis=1).min(axis=1)
    df['Kumo_Breakout_Bull']=(C>kt)&(C.shift(1)<=kt.shift(1))&(tk>kj)&vok
    df['Kumo_Breakout_Bear']=(C<kb)&(C.shift(1)>=kb.shift(1))&(tk<kj)&vok
    df['TK_Cross_Bull']=(tk>kj)&(tk.shift(1)<=kj.shift(1))&(C>kt)&vok
    df['TK_Cross_Bear']=(tk<kj)&(tk.shift(1)>=kj.shift(1))&(C<kb)&vok

    # CMF/MF
    df['CMF_Bull']=(df['CMF']>.1)&(df['CMF'].shift(1)<=.1)&(C>m50)&vok
    df['CMF_Bear']=(df['CMF']<-.1)&(df['CMF'].shift(1)>=-.1)&(C<m50)&vok
    rmfi=df['RSI_MFI'];mr_=rmfi>rmfi.shift(1);mf__=rmfi<rmfi.shift(1)
    df['MF_Cross_Bull']=((rmfi>0)&(rmfi.shift(1)<=0))&vok;df['MF_Cross_Bear']=((rmfi<0)&(rmfi.shift(1)>=0))&vok
    mus=_vs(mr_);mds=_vs(mf__)
    df['MF_Accel_Up']=(mus>=5)&vok;df['MF_Accel_Dn']=(mds>=5)&vok
    pl_=C<C.rolling(5).min().shift(1);mh_=rmfi>rmfi.rolling(5).min().shift(1)
    ph_=C>C.rolling(5).max().shift(1);ml_=rmfi<rmfi.rolling(5).max().shift(1)
    df['MF_Bull_Div']=(pl_&mh_&(rmfi<0))&vok;df['MF_Bear_Div']=(ph_&ml_&(rmfi>0))&vok

    # VP
    if 'VP_POC' in df.columns:
        poc=df['VP_POC']
        df['Volume_POC_Breakout']=(C>poc)&(C.shift(1)<=poc.shift(1))&vok&(C>O)
        df['Volume_POC_Breakdown']=(C<poc)&(C.shift(1)>=poc.shift(1))&vok&(C<O)
    if 'VP_VAH' in df.columns:
        ap__=atr/(C+1e-10)
        df['VP_VAH_Resistance']=((df['VP_VAH']-C).abs()/(C+1e-10)<ap__*.5)&(C<O)
        df['VP_VAL_Support']=((C-df['VP_VAL']).abs()/(C+1e-10)<ap__*.5)&(C>O)

    # RS
    rs=df.get('RS_Ratio',pd.Series(1.,index=idx));rm=rs-rs.shift(5)
    spr=df.get('SPY_Return',pd.Series(0.,index=idx)) if 'SPY_Return' in df else pd.Series(0.,index=idx)
    df['Relative_Strength_Buy']=(rs>1.03)&(rm>0.01)&(C>C.shift(1))&vok
    df['Relative_Strength_Sell']=(rs<.97)&(rm<-0.01)&(C<C.shift(1))&vok

    # 선행지표
    df['Setup_Squeeze_Bull']=df['BB_Squeeze']&(df['MACD_Hist']<0)&(df['MACD_Hist']>df['MACD_Hist'].shift(1))&(wt1<30)
    df['Setup_Squeeze_Bear']=df['BB_Squeeze']&(df['MACD_Hist']>0)&(df['MACD_Hist']<df['MACD_Hist'].shift(1))&(wt1>-30)
    ca=df.get('Composite_Accel',pd.Series(0,index=idx))
    df['Momentum_Accel_Buy']=(ca>JT.ACCEL_MOD)&(wt1<40)&vok
    df['Momentum_Accel_Sell']=(ca<-JT.ACCEL_MOD)&(wt1>-40)&vok
    df['Volume_Dry_Up']=_vs(vr<.6)>=5
    cs_=df.get('WT_Conv_Speed',pd.Series(0,index=idx))
    ga_=df.get('WT_Gap_Abs',pd.Series(0,index=idx)) if 'WT_Gap_Abs' in df else (wt1-wt2).abs()
    df['WT_Convergence_Bull']=(cs_>3)&(ga_>2)&(ga_<15)&(wt1<wt2)&(wt1<20)
    df['WT_Convergence_Bear']=(cs_>3)&(ga_>2)&(ga_<15)&(wt1>wt2)&(wt1>-20)

    # 쿨다운
    PAIRED={('MACD_Cross_Buy','MACD_Cross_Sell'):12,('Bullish_Engulfing','Bearish_Engulfing'):5,
        ('Hammer','Shooting_Star'):5,('Morning_Star','Evening_Star'):7,('DMI_Cross_Bull','DMI_Cross_Bear'):10,
        ('Pullback_123_Bull','Pullback_123_Bear'):7,('Expansion_BO','Expansion_BD'):10,
        ('Gilligans_Buy','Gilligans_Sell'):10,('Slingshot_Bull','Slingshot_Bear'):7,
        ('MF_Cross_Bull','MF_Cross_Bear'):10,('Kumo_Breakout_Bull','Kumo_Breakout_Bear'):10}
    ph_=set()
    for (bs,ss),cd in PAIRED.items():_cd_dir(df,bs,ss,cd);ph_.add(bs);ph_.add(ss)
    for s,cd in COOLDOWN_MAP.items():
        if s in df.columns and s not in ph_:df[s]=_cooldown(df[s],cd)

    # Combined Scan + 10-Layer Judgment
    df = detect_combined_scans(df)
    df = compute_10layer_judgment(df)
    return df


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Combined Scan 탐지 (28개)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def detect_combined_scans(df):
    idx=df.index;C,O,H,L,V=df['Close'],df['Open'],df['High'],df['Low'],df['Volume']
    F=lambda c:df.get(c,pd.Series(False,index=idx)).fillna(False)
    N=lambda c,d=0:df.get(c,pd.Series(d,index=idx)).fillna(d)
    va=V.rolling(50,min_periods=10).mean();vr=V/(va+1e-10)
    up=(C>N('MA50'))&(N('MA50')>N('MA200'))&(N('Plus_DI')>N('Minus_DI'))
    dn=(C<N('MA50'))&(N('MA50')<N('MA200'))&(N('Minus_DI')>N('Plus_DI'))
    adx_ok=N('ADX')>20;vs_=vr>=2;vok=vr>=1
    bc=F('Bullish_Engulfing')|F('Morning_Star')|F('Hammer')|F('Doji_Bullish')
    sc_=F('Bearish_Engulfing')|F('Evening_Star')|F('Shooting_Star')|F('Doji_Bearish')
    cb=F('Pullback_123_Bull')|F('NonADX_123_Bull')|F('Setup_180_Bull')|F('Boomer_Buy')|F('Expansion_BO')|F('Gilligans_Buy')|F('Lizard_Bull')
    cs_=F('Pullback_123_Bear')|F('NonADX_123_Bear')|F('Setup_180_Bear')|F('Boomer_Sell')|F('Expansion_BD')|F('Gilligans_Sell')|F('Lizard_Bear')
    mfb=(N('RSI_MFI')>N('RSI_MFI').shift(1))|(N('CMF')>.05)|F('MF_Cross_Bull')
    mfs=(N('RSI_MFI')<N('RSI_MFI').shift(1))|(N('CMF')<-.05)|F('MF_Cross_Bear')
    n_bl=C<=N('BB_Low')*1.01;n_bu=C>=N('BB_Up')*.99
    n_vp=((C-N('VP_VAL')).abs()/(C+1e-10)<.02)&(N('VP_VAL')>0)
    n_vr=((N('VP_VAH')-C).abs()/(C+1e-10)<.02)&(N('VP_VAH')>0)
    n50=((C-N('MA50')).abs()/(C+1e-10))<.03
    wos=N('WT1')<-53;wob=N('WT1')>53;ros=N('RSI')<30;rob=N('RSI')>70
    sos=(N('StochK')<20)&(N('StochD')<20);sob=(N('StochK')>80)&(N('StochD')>80)
    dbc=F('Bull_Divergence').astype(int)+F('RSI_Bull_Divergence').astype(int)+F('MF_Bull_Div').astype(int)+F('OBV_Div_Buy').astype(int)
    dsc=F('Bear_Divergence').astype(int)+F('RSI_Bear_Divergence').astype(int)+F('MF_Bear_Div').astype(int)+F('OBV_Div_Sell').astype(int)
    mr=N('MACD_Hist')>N('MACD_Hist').shift(1);mf=N('MACD_Hist')<N('MACD_Hist').shift(1)
    wr=N('WT1')>N('WT1').shift(1);wf=N('WT1')<N('WT1').shift(1)
    llw=(pd.concat([C,O],axis=1).min(axis=1)-L)>(H-L)*.6
    luw=(H-pd.concat([C,O],axis=1).max(axis=1))>(H-L)*.6

    # T1 매수
    ub=(up|(C>N('MA50'))).astype(int)+((wr|F('WT_Up'))&(mr|(N('MACD_Hist')>0))).astype(int)+(bc|cb).astype(int)+vok.astype(int)+mfb.astype(int)+(n50|F('BB_Squeeze_End_Bull')|n_vp).astype(int)
    df['CS_Ultimate_Buy']=ub>=6
    tos=(wos|(N('WT1')<-60))&(ros|(N('RSI')<35))&sos
    df['CS_Triple_Oversold_Reversal']=tos&(F('WT_Up')|wr|bc|llw|F('Gold_Dot')|F('Green_Dot_T1'))&vok
    bo=F('New_52W_High')|F('Expansion_BO')|(C>N('BB_Up'))
    df['CS_Breakout_Momentum_Buy']=bo&adx_ok&(N('Plus_DI')>N('Minus_DI'))&vs_&mr
    acc=F('Pocket_Pivot')|(F('NR7')&(N('OBV')>N('OBV').shift(5)))|(F('Calm_After_Storm')&(C>O))
    df['CS_Institutional_Accumulation']=acc&(C>N('MA50'))&(N('CMF')>.05)&(N('OBV')>N('OBV').shift(5))
    df['CS_Divergence_Confluence_Buy']=(dbc>=2)&(n_bl|n_vp|n50)&(bc|llw|F('WT_Up'))&vok
    el=F('New_52W_Low')|(C<=C.rolling(252,min_periods=200).min()*1.02)
    eos=(N('WT1')<-80)|(wos&(N('RSI')<25))
    df['CS_Capitulation_Bottom']=el&eos&(vr>=3)&(llw|F('Hammer')|F('Parabolic_Bottom_Buy'))&(N('MFI')<30)

    # T1 매도
    us_=(dn|(C<N('MA50'))).astype(int)+((wf|F('WT_Down'))&(mf|(N('MACD_Hist')<0))).astype(int)+(sc_|cs_).astype(int)+vok.astype(int)+mfs.astype(int)+(n50|F('BB_Squeeze_End_Bear')|n_vr).astype(int)
    df['CS_Ultimate_Sell']=us_>=6
    tob=(wob|(N('WT1')>60))&(rob|(N('RSI')>65))&sob
    df['CS_Triple_Overbought_Exhaustion']=tob&(F('WT_Down')|wf|sc_|luw|F('Blood_Diamond')|F('Red_Dot_T1'))&vok
    bd_=F('New_52W_Low')|F('Expansion_BD')|(C<N('BB_Low'))
    df['CS_Breakdown_Momentum_Sell']=bd_&adx_ok&(N('Minus_DI')>N('Plus_DI'))&vs_&mf
    para=(C>C.shift(10)*1.3)|F('Parabolic_Top_Sell')
    eob=(N('WT1')>80)|(wob&(N('RSI')>75))
    df['CS_Parabolic_Exhaustion_Sell']=para&eob&(luw|F('Shooting_Star')|sc_)&(vr>=3)
    df['CS_Divergence_Confluence_Sell']=(dsc>=2)&(n_bu|n_vr|n50)&(sc_|luw|F('WT_Down'))&vok
    eh=F('New_52W_High')|(C>=C.rolling(252,min_periods=200).max()*.98)
    df['CS_Blow_Off_Top']=eh&eob&(vr>=3)&(luw|F('Shooting_Star')|F('Parabolic_Top_Sell'))&(N('MFI')>70)

    # T2 매수
    df['CS_Trend_Pullback_Buy']=up&(n50|(L<=N('MA20'))&(C>N('MA20')))&(bc|(C>O))&mfb
    df['CS_Squeeze_Breakout_Buy']=(F('BB_Squeeze_End_Bull')|(F('BB_Squeeze').shift(1)&(C>N('BB_Mid'))&(C>O)))&vok&mr
    df['CS_MA_Confluence_Buy']=((N('MA50')>N('MA200'))&(N('MA50')>N('MA50').shift(5)))&(F('MACD_Cross_Buy')|mr)&vok&(C>N('MA50'))
    df['CS_Cooper_Setup_Buy']=cb&adx_ok&(N('Plus_DI')>N('Minus_DI'))&vok&(C>N('MA50'))
    df['CS_Volume_Climax_Rev_Buy']=(F('Volume_Climax_Buy')|(vr>=2.5))&(wos|sos)&(bc|llw)&(n_bl|n_vp)
    df['CS_Ichimoku_Breakout_Buy']=F('Kumo_Breakout_Bull')&(F('TK_Cross_Bull')|adx_ok)&vok

    # T2 매도
    df['CS_Trend_Rejection_Sell']=dn&(n50|(H>=N('MA20'))&(C<N('MA20')))&(sc_|(C<O))&mfs
    df['CS_Squeeze_Breakdown_Sell']=(F('BB_Squeeze_End_Bear')|(F('BB_Squeeze').shift(1)&(C<N('BB_Mid'))&(C<O)))&vok&mf
    df['CS_MA_Breakdown_Sell']=((N('MA50')<N('MA200'))&(N('MA50')<N('MA50').shift(5)))&(F('MACD_Cross_Sell')|mf)&vok&(C<N('MA50'))
    df['CS_Cooper_Setup_Sell']=cs_&adx_ok&(N('Minus_DI')>N('Plus_DI'))&vok&(C<N('MA50'))
    df['CS_Gap_Failure_Sell']=(F('Gap_Up').shift(1).fillna(False)&sc_&vok&wf)|(F('Gap_Up')&(C<O)&vok)

    # T3
    df['CS_Oversold_Bounce_Buy']=sos&bc&(n50|n_bl)
    df['CS_Momentum_Accel_Buy']=(N('Composite_Accel',0)>1.5)&vok&(C>N('MA50'))
    df['CS_Structure_Support_Buy']=n_vp&n_bl&(C>O)
    df['CS_Overbought_Fade_Sell']=sob&sc_&(n50|n_bu)
    df['CS_Volatility_Explosion']=(F('NR7_2').astype(int)+F('BB_Squeeze').astype(int)+(vr<.5).astype(int)+F('Inside_Day').astype(int))>=3

    for sn in COMBINED_SCAN_REGISTRY:
        if sn in df.columns:df[sn]=_cooldown(df[sn],bars=7)
    return df


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  🏛️ 10-Layer Institutional Judgment Engine
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def compute_10layer_judgment(df):
    """
    10-Layer 다차원 매매판단 시스템
    L1: Trend (추세)          — MA, ST, ADX 방향
    L2: Momentum (모멘텀)      — RSI, WT, MACD, Stoch 교차
    L3: Candle (캔들패턴)      — 반전/지속 캔들
    L4: Bollinger (BB)        — 스퀴즈, %B, 워크
    L5: Volume (거래량)        — OBV, 클라이맥스, 포켓피봇
    L6: Money Flow (자금흐름)  — RSI_MFI, CMF, 다이버전스
    L7: Pattern (Cooper+패턴)  — 쿠퍼 + 구조 패턴
    L8: Combined Scan (합류)   — 28개 Combined Scan 보너스
    L9: Leading (선행지표)     — 가속도, 수렴속도, 셋업 압력
    L10: Lagging (후행지표)    — MA정배열, 이치모쿠, RS, 국면
    """
    C,O,H,L=df['Close'],df['Open'],df['High'],df['Low']
    idx=df.index;N=lambda c,d=0:df.get(c,pd.Series(d,index=idx)).fillna(d)

    a200=C>N('MA200');a50=C>N('MA50');a20=C>N('MA20')
    b200=C<N('MA200');b50=C<N('MA50')
    m50r=N('MA50')>N('MA50').shift(5);m50f=N('MA50')<N('MA50').shift(5)
    mhr=N('MACD_Hist')>N('MACD_Hist').shift(1);mhf=N('MACD_Hist')<N('MACD_Hist').shift(1)
    rr=N('RSI')>N('RSI').shift(1);rf=N('RSI')<N('RSI').shift(1)
    wr=N('WT1')>N('WT1').shift(1);wf=N('WT1')<N('WT1').shift(1)
    vr=df['Volume']/(df['Volume'].rolling(50,min_periods=10).mean()+1e-10)
    obv=N('OBV');obvm=obv.rolling(20,min_periods=10).mean()
    regime=N('Regime')

    # ═══ BUY 10 Layers ═══
    # L1 Trend
    bt=pd.Series(0.,index=idx)
    bt+=np.where(a200&a50&a20,5,np.where(a200&a50,4,np.where(a200,2.5,np.where(a50,1.5,0))))
    bt+=np.where(N('MA50')>N('MA200'),1.5,0)+np.where(N('Plus_DI')>N('Minus_DI'),1,0)
    bt+=np.where(N('ST_Direction')==1,1,0)+_sp(df,'Cross_Above_50MA',1)+_sp(df,'Golden_Cross',1.5)
    bt+=np.where(b200&b50,-2,0)
    df['BL_Trend']=bt.clip(-2,JT.TREND_CAP)

    # L2 Momentum
    bm=pd.Series(0.,index=idx)
    for s,p in [('MACD_Cross_Buy',2.5),('MACD_Zero_Cross_Buy',2),('StochRSI_Cross_Buy',2),('ADX_Momentum_Buy',2),('VWAP_Bounce_Buy',1.5)]:
        bm+=_sp(df,s,p)
    bm=bm.clip(upper=6)  # cross signal cap
    bm+=np.select([(N('MACD_Hist')>0)&mhr,(N('MACD_Hist')>0)&mhf,(N('MACD_Hist')<0)&mhr],[2,.5,1.5],default=0.)
    bm+=np.select([(N('RSI')<30)&rr,N('RSI')<30,(N('RSI')<45)&rr],[3,1.5,1],default=0.)
    bm+=np.select([(N('StochK')<20)&(N('StochK')>N('StochD')),N('StochK')<20],[2.5,1],default=0.)
    bm+=np.select([(N('WT1')<OS1)&wr,N('WT1')<OS1,(N('WT1')<-20)&wr],[3,1,1],default=0.)
    df['BL_Momentum']=bm.clip(-2,JT.MOMENTUM_CAP)

    # L3 Candle
    bcc=pd.Series(0.,index=idx)
    for s,p in [('Morning_Star',3.5),('Bullish_Engulfing',3),('Hammer',2.5),('Outside_Bullish',2.5),('Doji_Bullish',1)]:
        bcc=np.maximum(bcc,_sp(df,s,p))
    df['BL_Candle']=pd.Series(bcc,index=idx).clip(upper=JT.CANDLE_CAP)

    # L4 BB
    bb=pd.Series(0.,index=idx)
    bb+=_sp(df,'BB_Squeeze_End_Bull',3)+_sp(df,'NR7_2',1.5)+_sp(df,'Calm_After_Storm',1)
    pb=N('Percent_B')
    bb+=np.select([pb<.05,pb<.2,(pb>=.4)&(pb<=.6)&a50,pb>.95],[2.5,1.5,.5,-1.5],default=0.)
    bb+=_sp(df,'BB_Lower_Bounce',2)
    df['BL_BB']=bb.clip(-1,JT.BB_CAP)

    # L5 Volume
    bv=pd.Series(0.,index=idx)
    bv+=_sp(df,'Volume_Climax_Buy',3)+_sp(df,'Pocket_Pivot',2)+_sp(df,'OBV_Div_Buy',1.5)+_sp(df,'Volume_POC_Breakout',2.5)
    bv+=np.where((vr>=3)&(C>O),2.5,np.where((vr>=1.5)&(C>O),1,0))
    bv+=np.where(obv>obvm,1,np.where(obv<obvm,-1,0))
    df['BL_Volume']=bv.clip(-1,JT.VOLUME_CAP)

    # L6 Money Flow
    bmf=pd.Series(0.,index=idx)
    rmfi=N('RSI_MFI')
    bmf+=np.select([rmfi<-10,rmfi<-5,rmfi>10],[2,1,-.5],default=0.)
    bmf+=_sp(df,'MF_Cross_Bull',2)+_sp(df,'MF_Bull_Div',2)+_sp(df,'MF_Accel_Up',1)+_sp(df,'CMF_Bull',1.5)
    cmf=N('CMF');bmf+=np.where(cmf>.15,1.5,np.where(cmf>.05,.5,np.where(cmf<-.15,-1,0)))
    df['BL_MF']=bmf.clip(-1,JT.MF_CAP)

    # L7 Pattern (Cooper + 구조)
    bp=pd.Series(0.,index=idx)
    bp+=_spd(df,'Gold_Dot',4);bp+=np.where(bp==0,_spd(df,'Green_Dot_T1',2.5),0)
    for s,p in [('Bull_Divergence',2),('Pullback_123_Bull',2.5),('Setup_180_Bull',2),('Boomer_Buy',2),
        ('Expansion_BO',3),('Gilligans_Buy',2.5),('Lizard_Bull',2),('NonADX_123_Bull',1.5),
        ('EMA_Pullback_Buy',2),('Momentum_Ignition_Buy',3),('SuperTrend_Buy',2),('Parabolic_Bottom_Buy',3),
        ('Kumo_Breakout_Bull',2.5),('Reversal_New_Highs',2.5),('Slingshot_Bull',2),('Jack_In_Box_Bull',2),
        ('Relative_Strength_Buy',2.5),('VP_VAL_Support',1.5)]:
        bp+=_sp(df,s,p)
    df['BL_Pattern']=bp.clip(upper=JT.PATTERN_CAP)

    # L8 Combined Scan
    bcs=pd.Series(0.,index=idx)
    for cs,cfg in COMBINED_SCAN_REGISTRY.items():
        if cfg['dir']!='buy' or cs not in df.columns:continue
        bonus={1:JT.COMBO_T1,2:JT.COMBO_T2,3:JT.COMBO_T3}.get(cfg['tier'],1)
        bcs+=np.where(df[cs].fillna(False),bonus,0.)
    df['BL_Combined']=bcs.clip(upper=15)

    # L9 Leading (선행지표)
    bl=pd.Series(0.,index=idx)
    ca=N('Composite_Accel')
    bl+=np.where(ca>JT.ACCEL_STRONG,3,np.where(ca>JT.ACCEL_MOD,1.5,np.where(ca>.5,.5,np.where(ca<-JT.ACCEL_MOD,-1,0))))
    bl+=_sp(df,'Setup_Squeeze_Bull',1.5)+_sp(df,'Momentum_Accel_Buy',2)+_sp(df,'WT_Convergence_Bull',1.5)+_sp(df,'Volume_Dry_Up',.5)
    # 셋업 압력
    sp_buy=pd.Series(0.,index=idx)
    sp_buy+=np.where(N('WT1')<-40,2,np.where(N('WT1')<-20,1,0))
    sp_buy+=np.where(N('RSI')<35,1.5,np.where(N('RSI')<45,.5,0))
    sp_buy+=np.where(N('StochK')<25,1,0)
    sp_buy+=np.where(ca>JT.ACCEL_MOD,2,np.where(ca>.5,1,0))
    df['Setup_Pressure_Buy']=sp_buy
    bl+=np.where(sp_buy>=8,3,np.where(sp_buy>=5,2,np.where(sp_buy>=3,1,0)))
    df['BL_Leading']=bl.clip(-1,JT.LEADING_CAP)

    # L10 Lagging (후행지표)
    blag=pd.Series(0.,index=idx)
    blag+=np.where(a200&a50&(N('MA50')>N('MA200')),3,np.where(a50&(N('MA50')>N('MA200')),2,np.where(a200,1,0)))
    blag+=np.where(regime>=2,3,np.where(regime>=1,1.5,np.where(regime<=-1,-1.5,0)))
    # 이치모쿠 후행
    kt=pd.concat([N('Ichimoku_SenkouA'),N('Ichimoku_SenkouB')],axis=1).max(axis=1)
    blag+=np.where(C>kt,1.5,np.where(C<kt,-1,0))
    blag+=np.where(N('RS_Ratio',1)>1.05,2,np.where(N('RS_Ratio',1)>1.02,1,np.where(N('RS_Ratio',1)<.95,-1.5,0)))
    df['BL_Lagging']=blag.clip(-2,JT.LAGGING_CAP)

    # ═══ SELL 10 Layers (대칭 구조) ═══
    st_=pd.Series(0.,index=idx)
    st_+=np.where(b200&b50&(C<N('MA20')),5,np.where(b200&b50,4,np.where(b200,2.5,np.where(b50,1.5,0))))
    st_+=np.where(N('MA50')<N('MA200'),1.5,0)+np.where(N('Minus_DI')>N('Plus_DI'),1,0)
    st_+=np.where(N('ST_Direction')==-1,1,0)+_sp(df,'Fell_Below_50MA',1)+_sp(df,'Death_Cross',1.5)
    st_+=np.where(a200&a50,-2,0)
    df['SL_Trend']=st_.clip(-2,JT.TREND_CAP)

    sm=pd.Series(0.,index=idx)
    for s,p in [('MACD_Cross_Sell',2.5),('MACD_Zero_Cross_Sell',2),('StochRSI_Cross_Sell',2),('ADX_Momentum_Sell',2),('VWAP_Reject_Sell',1.5)]:
        sm+=_sp(df,s,p)
    sm=sm.clip(upper=6)
    sm+=np.select([(N('MACD_Hist')<0)&mhf,(N('MACD_Hist')<0)&mhr,(N('MACD_Hist')>0)&mhf],[2,.5,1.5],default=0.)
    sm+=np.select([(N('RSI')>70)&rf,N('RSI')>70,(N('RSI')>55)&rf],[3,1.5,1],default=0.)
    sm+=np.select([(N('StochK')>80)&(N('StochK')<N('StochD')),N('StochK')>80],[2.5,1],default=0.)
    sm+=np.select([(N('WT1')>OB1)&wf,N('WT1')>OB1,(N('WT1')>20)&wf],[3,1,1],default=0.)
    df['SL_Momentum']=sm.clip(-2,JT.MOMENTUM_CAP)

    scc=pd.Series(0.,index=idx)
    for s,p in [('Evening_Star',3.5),('Bearish_Engulfing',3),('Shooting_Star',2.5),('Outside_Bearish',2.5),('Doji_Bearish',1)]:
        scc=np.maximum(scc,_sp(df,s,p))
    df['SL_Candle']=pd.Series(scc,index=idx).clip(upper=JT.CANDLE_CAP)

    sbb=pd.Series(0.,index=idx)
    sbb+=_sp(df,'BB_Squeeze_End_Bear',3)+_sp(df,'NR7_2',1.5)+_sp(df,'Calm_After_Storm',1)
    sbb+=np.select([pb>.95,pb>.8,(pb>=.4)&(pb<=.6)&b50,pb<.05],[2.5,1.5,.5,-1.5],default=0.)
    sbb+=_sp(df,'BB_Lower_Break',1.5)
    df['SL_BB']=sbb.clip(-1,JT.BB_CAP)

    sv=pd.Series(0.,index=idx)
    sv+=_sp(df,'Volume_Climax_Sell',3)+_sp(df,'OBV_Div_Sell',1.5)+_sp(df,'Volume_POC_Breakdown',2.5)
    sv+=np.where((vr>=3)&(C<O),2.5,np.where((vr>=1.5)&(C<O),1,0))
    sv+=np.where(obv<obvm,1,np.where(obv>obvm,-1,0))
    df['SL_Volume']=sv.clip(-1,JT.VOLUME_CAP)

    smf=pd.Series(0.,index=idx)
    smf+=np.select([rmfi>10,rmfi>5,rmfi<-10],[2,1,-.5],default=0.)
    smf+=_sp(df,'MF_Cross_Bear',2)+_sp(df,'MF_Bear_Div',2)+_sp(df,'MF_Accel_Dn',1)+_sp(df,'CMF_Bear',1.5)
    smf+=np.where(cmf<-.15,1.5,np.where(cmf<-.05,.5,np.where(cmf>.15,-1,0)))
    df['SL_MF']=smf.clip(-1,JT.MF_CAP)

    spp=pd.Series(0.,index=idx)
    spp+=_spd(df,'Blood_Diamond',4);spp+=np.where(spp==0,_spd(df,'Red_Dot_T1',2.5),0)
    for s,p in [('Bear_Divergence',2),('Pullback_123_Bear',2.5),('Setup_180_Bear',2),('Boomer_Sell',2),
        ('Expansion_BD',3),('Gilligans_Sell',2.5),('Lizard_Bear',2),('NonADX_123_Bear',1.5),
        ('EMA_Pullback_Sell',2),('Momentum_Ignition_Sell',3),('SuperTrend_Sell',2),('Parabolic_Top_Sell',3),
        ('Kumo_Breakout_Bear',2.5),('Reversal_New_Lows',2.5),('Slingshot_Bear',2),('Jack_In_Box_Bear',2),
        ('Relative_Strength_Sell',2),('VP_VAH_Resistance',1.5)]:
        spp+=_sp(df,s,p)
    df['SL_Pattern']=spp.clip(upper=JT.PATTERN_CAP)

    scs=pd.Series(0.,index=idx)
    for cs,cfg in COMBINED_SCAN_REGISTRY.items():
        if cfg['dir']!='sell' or cs not in df.columns:continue
        bonus={1:JT.COMBO_T1,2:JT.COMBO_T2,3:JT.COMBO_T3}.get(cfg['tier'],1)
        scs+=np.where(df[cs].fillna(False),bonus,0.)
    df['SL_Combined']=scs.clip(upper=15)

    sl_=pd.Series(0.,index=idx)
    sl_+=np.where(ca<-JT.ACCEL_STRONG,3,np.where(ca<-JT.ACCEL_MOD,1.5,np.where(ca<-.5,.5,np.where(ca>JT.ACCEL_MOD,-1,0))))
    sl_+=_sp(df,'Setup_Squeeze_Bear',1.5)+_sp(df,'Momentum_Accel_Sell',2)+_sp(df,'WT_Convergence_Bear',1.5)
    sp_sell=pd.Series(0.,index=idx)
    sp_sell+=np.where(N('WT1')>40,2,np.where(N('WT1')>20,1,0))
    sp_sell+=np.where(N('RSI')>65,1.5,np.where(N('RSI')>55,.5,0))
    sp_sell+=np.where(N('StochK')>75,1,0)
    sp_sell+=np.where(ca<-JT.ACCEL_MOD,2,np.where(ca<-.5,1,0))
    df['Setup_Pressure_Sell']=sp_sell
    sl_+=np.where(sp_sell>=8,3,np.where(sp_sell>=5,2,np.where(sp_sell>=3,1,0)))
    df['SL_Leading']=sl_.clip(-1,JT.LEADING_CAP)

    slag=pd.Series(0.,index=idx)
    slag+=np.where(b200&b50&(N('MA50')<N('MA200')),3,np.where(b50&(N('MA50')<N('MA200')),2,np.where(b200,1,0)))
    slag+=np.where(regime<=-2,3,np.where(regime<=-1,1.5,np.where(regime>=1,-1.5,0)))
    kb=pd.concat([N('Ichimoku_SenkouA'),N('Ichimoku_SenkouB')],axis=1).min(axis=1)
    slag+=np.where(C<kb,1.5,np.where(C>kt,-1,0))
    slag+=np.where(N('RS_Ratio',1)<.95,2,np.where(N('RS_Ratio',1)<.98,1,np.where(N('RS_Ratio',1)>1.05,-1.5,0)))
    df['SL_Lagging']=slag.clip(-2,JT.LAGGING_CAP)

    # ═══ 합산 ═══
    layer_names=['Trend','Momentum','Candle','BB','Volume','MF','Pattern','Combined','Leading','Lagging']
    df['Buy_Total']=sum(df[f'BL_{n}'] for n in layer_names).clip(lower=0)
    df['Sell_Total']=sum(df[f'SL_{n}'] for n in layer_names).clip(lower=0)
    df['Buy_Active_Layers']=sum((df[f'BL_{n}']>0).astype(int) for n in layer_names)
    df['Sell_Active_Layers']=sum((df[f'SL_{n}']>0).astype(int) for n in layer_names)

    # ═══ 최종 판단 + Confidence ═══
    btv,stv=df['Buy_Total'].values,df['Sell_Total'].values
    bav,sav=df['Buy_Active_Layers'].values,df['Sell_Active_Layers'].values
    j=np.full(len(df),'NEUTRAL',dtype=object);conf=np.zeros(len(df),dtype=float)

    for i in range(len(df)):
        b,s=btv[i],stv[i];bal,sal=bav[i],sav[i]
        diff=b-s;ratio=b/(s+.01);sr=s/(b+.01)

        if b>=JT.STRONG_BUY and bal>=6 and ratio>=2 and diff>=10: j[i]='STRONG_BUY'
        elif b>=JT.BUY and bal>=4 and ratio>=1.4 and diff>=5: j[i]='BUY'
        elif b>=JT.WATCH_BUY and bal>=3 and diff>=2: j[i]='WATCH_BUY'
        elif s>=JT.STRONG_SELL and sal>=6 and sr>=1.5 and (s-b)>=8: j[i]='STRONG_SELL'
        elif s>=JT.SELL and sal>=4 and sr>=1.2 and (s-b)>=4: j[i]='SELL'
        elif s>=JT.WATCH_SELL and sal>=3 and (s-b)>=1.5: j[i]='WATCH_SELL'
        elif b>s+2 and bal>=2: j[i]='WATCH_BUY'
        elif s>b+2 and sal>=2: j[i]='WATCH_SELL'
        elif b>=9 and s>=9 and abs(diff)<3: j[i]='MIXED'

        # Confidence 계산 (다차원)
        dom=max(b,s);act=bal if 'BUY' in j[i] else (sal if 'SELL' in j[i] else max(bal,sal))
        margin_sc=min((dom-13)/13*30,30) if 'STRONG' in j[i] else (min((dom-10)/10*25,25) if j[i] in ('BUY','SELL') else 0)
        consensus_sc=(act/NUM_LAYERS)*30
        ratio_sc=min(max((ratio-1)*10,0),20) if 'BUY' in j[i] else (min(max((sr-1)*10,0),20) if 'SELL' in j[i] else 0)
        raw=margin_sc+consensus_sc+ratio_sc
        if j[i] in ('NEUTRAL','MIXED'): raw=max(10,50-abs(diff)*5)
        conf[i]=np.clip(raw,5,99)

    df['Trade_Judgment']=j;df['Judgment_Confidence']=conf

    # ═══ 선행/후행 판단 (사용자 정보용) ═══
    leading_score=df['BL_Leading']-df['SL_Leading']
    lagging_score=df['BL_Lagging']-df['SL_Lagging']
    df['Leading_Verdict']=np.select([leading_score>3,leading_score>1,leading_score<-3,leading_score<-1],
        ['강한 상승 가속','상승 임박','강한 하락 가속','하락 임박'],default='중립')
    df['Lagging_Verdict']=np.select([lagging_score>3,lagging_score>1,lagging_score<-3,lagging_score<-1],
        ['강한 상승 추세','상승 추세','강한 하락 추세','하락 추세'],default='비추세/횡보')

    return df


print("✅ Part 2/4 완료: 시그널 탐지 + Combined Scan + 10-Layer 판단 엔진")

# ══════════════════════════════════════════════════════════════
#  CipherX V13.0 — PART 3/4: 차트 빌더 + UI 렌더링
# ══════════════════════════════════════════════════════════════

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  호버 텍스트 생성
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _hover(dc, iv, tier_label):
    """마우스 호버 시 상세 정보"""
    row = dc.loc[iv]; ds = iv.strftime('%Y-%m-%d')
    bs, ss, cs_list = [], [], []
    for sn, cfg in SIGNAL_REGISTRY.items():
        if sn in dc.columns and row.get(sn, False):
            e = f"{cfg['icon']} {cfg['kor']}"
            if cfg['dir'] == 'buy': bs.append(e)
            elif cfg['dir'] == 'sell': ss.append(e)
    for cn, ccfg in COMBINED_SCAN_REGISTRY.items():
        if cn in dc.columns and row.get(cn, False):
            tb = {1:'🥇T1',2:'🥈T2',3:'🥉T3'}.get(ccfg['tier'],'T?')
            cs_list.append(f"{ccfg['icon']} {ccfg['kor']} [{tb}]")
    rg = int(row.get('Regime', 0))
    rl = {2:'🟢🟢UP',1:'🟢UP',0:'⚪RNG',-1:'🔴DN',-2:'🔴🔴DN'}.get(rg,'?')
    jg = str(row.get('Trade_Judgment',''))
    cf = float(row.get('Judgment_Confidence',0))
    bt = float(row.get('Buy_Total',0)); st_ = float(row.get('Sell_Total',0))
    lines = [
        f"<b style='font-size:13px'>📅 {ds}</b>",
        f"<b style='color:#A5B4FC'>{tier_label}</b>",
        f"─"*26,
        f"<b>국면:</b> {rl} | <b>판단:</b> {jg} ({cf:.0f}%)",
        f"<b>BUY:</b>{bt:.1f} vs <b>SELL:</b>{st_:.1f} (NET:{bt-st_:+.1f})",
        f"WT:{row.get('WT1',0):.0f} RSI:{row.get('RSI',0):.0f} ADX:{row.get('ADX',0):.0f}",
    ]
    if cs_list:
        lines.append(f"─"*26)
        lines.append(f"<b style='color:#FFD700'>🎯 Combined({len(cs_list)}):</b>")
        for c in cs_list[:4]: lines.append(f"  {c}")
    if bs:
        lines.append(f"<span style='color:#34D399'><b>▲매수({len(bs)}):</b> {', '.join(bs[:5])}</span>")
    if ss:
        lines.append(f"<span style='color:#F87171'><b>▼매도({len(ss)}):</b> {', '.join(ss[:5])}</span>")
    # 선행/후행
    lv = str(row.get('Leading_Verdict',''))
    lgv = str(row.get('Lagging_Verdict',''))
    if lv != '중립' or lgv != '비추세/횡보':
        lines.append(f"─"*26)
        lines.append(f"⏳선행: {lv} | 📊후행: {lgv}")
    return "<br>".join(lines)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  4마커 수집
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _collect_markers(dc):
    idx = dc.index
    sb = pd.Series(False, index=idx)
    for sn in STRONG_BUY_SIGS:
        if sn in dc.columns: sb |= dc[sn].fillna(False)
    ss = pd.Series(False, index=idx)
    for sn in STRONG_SELL_SIGS:
        if sn in dc.columns: ss |= dc[sn].fillna(False)
    nb = pd.Series(False, index=idx)
    for sn, cfg in SIGNAL_REGISTRY.items():
        if cfg['dir'] == 'buy' and sn in dc.columns: nb |= dc[sn].fillna(False)
    for cn, ccfg in COMBINED_SCAN_REGISTRY.items():
        if ccfg['dir'] == 'buy' and ccfg['tier'] >= 2 and cn in dc.columns: nb |= dc[cn].fillna(False)
    nb = nb & ~sb
    ns = pd.Series(False, index=idx)
    for sn, cfg in SIGNAL_REGISTRY.items():
        if cfg['dir'] == 'sell' and sn in dc.columns: ns |= dc[sn].fillna(False)
    for cn, ccfg in COMBINED_SCAN_REGISTRY.items():
        if ccfg['dir'] == 'sell' and ccfg['tier'] >= 2 and cn in dc.columns: ns |= dc[cn].fillna(False)
    ns = ns & ~ss
    return sb, nb, ss, ns


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  차트 빌더
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def build_chart(dc, ticker):
    mac = {20:'#f1c40f',50:'#e74c3c',200:'#2ecc71'}
    fig = make_subplots(rows=5, cols=1, shared_xaxes=True, vertical_spacing=0.03,
        row_heights=[.40,.07,.14,.14,.25],
        subplot_titles=("","Volume","WaveTrend","MACD","10-Layer Score"))

    # 캔들
    fig.add_trace(go.Candlestick(x=dc.index,open=dc['Open'],high=dc['High'],low=dc['Low'],close=dc['Close'],
        name="Price",increasing_line_color='#00E676',decreasing_line_color='#FF1744',
        increasing_fillcolor='rgba(0,230,118,.8)',decreasing_fillcolor='rgba(255,23,68,.8)'),row=1,col=1)
    for ma in [20,50,200]:
        fig.add_trace(go.Scatter(x=dc.index,y=dc[f'MA{ma}'],line=dict(color=mac[ma],width=1.2),name=f'{ma}MA'),row=1,col=1)
    for mc,clr,nm in [(dc['ST_Direction']==1,'#00E676','ST▲'),(dc['ST_Direction']==-1,'#FF1744','ST▼')]:
        fig.add_trace(go.Scatter(x=dc.index,y=dc['SuperTrend'].where(mc),line=dict(color=clr,width=2),name=nm,connectgaps=False),row=1,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['BB_Up'],line=dict(color='gray',width=1,dash='dot'),name='BB↑'),row=1,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['BB_Low'],line=dict(color='gray',width=1,dash='dot'),name='BB↓',fill='tonexty',fillcolor='rgba(128,128,128,.07)'),row=1,col=1)

    # 4마커
    sb,nb,ss,ns = _collect_markers(dc)
    markers = [
        (sb,'⭐ 강력매수','star',16,'#FFD700','#00E676','Low',-3,2),
        (nb,'△ 매수','triangle-up',10,'#00E676','#00E676','Low',-2,1),
        (ss,'⭐ 강력매도','star',16,'#FFD700','#FF1744','High',3,2),
        (ns,'▽ 매도','triangle-down',10,'#FF1744','#FF1744','High',2,1),
    ]
    for mask,label,sym,sz,mc,lc,base,am,lw in markers:
        if not mask.any(): continue
        sr = dc[mask]
        yv = sr['Low']+sr['ATR']*am if base=='Low' else sr['High']+sr['ATR']*am
        ht = [_hover(dc,iv,label) for iv in sr.index]
        fig.add_trace(go.Scatter(x=sr.index,y=yv,mode='markers',
            marker=dict(symbol=sym,size=sz,color=mc,line=dict(width=lw,color=lc),opacity=.95),
            name=label,text=ht,hovertemplate="%{text}<extra></extra>",
            hoverlabel=dict(bgcolor='rgba(10,13,20,.97)',bordercolor=lc,
                font=dict(size=11,family='Pretendard',color='#FAFAFA'),align='left')),row=1,col=1)

    # 거래량
    br = dc['Close']<dc['Open']
    fig.add_trace(go.Bar(x=dc.index,y=dc['Volume'],
        marker_color=np.where(br,'rgba(255,23,68,.6)','rgba(0,230,118,.6)').tolist(),name="Vol",opacity=.8),row=2,col=1)

    # WT
    fig.add_trace(go.Scatter(x=dc.index,y=dc['WT1'],line=dict(color='#00E676',width=2),name="WT1"),row=3,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['WT2'],line=dict(color='#FF1744',width=1.5,dash='dot'),name="WT2"),row=3,col=1)
    wd=dc['WT1']-dc['WT2']
    fig.add_trace(go.Bar(x=dc.index,y=wd,marker_color=np.where(wd>=0,'#00E676','#FF1744').tolist(),name="WTH",opacity=.3),row=3,col=1)
    for lv,cc,d in [(OB1,'#ff3333','solid'),(0,'gray','dot'),(OS1,'#00bfff','solid')]:
        fig.add_hline(y=lv,line_dash=d,line_color=cc,line_width=1,row=3,col=1)

    # MACD
    fig.add_trace(go.Scatter(x=dc.index,y=dc['MACD_Line'],line=dict(color='#29B6F6',width=1.5),name="MACD"),row=4,col=1)
    fig.add_trace(go.Scatter(x=dc.index,y=dc['MACD_Signal'],line=dict(color='#FFA726',width=1.5),name="Sig"),row=4,col=1)
    mh=dc['MACD_Hist']
    fig.add_trace(go.Bar(x=dc.index,y=mh,marker_color=np.where(mh>=0,'#26A69A','#EF5350').tolist(),name="Hist",opacity=.7),row=4,col=1)
    fig.add_hline(y=0,line_color="#444",line_width=1,row=4,col=1)

    # 10-Layer NET 스코어
    if 'Buy_Total' in dc.columns:
        net=dc['Buy_Total']-dc['Sell_Total']
        colors=np.where(net>=10,'#00E676',np.where(net>=5,'#69F0AE',np.where(net<=-10,'#FF1744',np.where(net<=-5,'#FF5252','#FFC107'))))
        fig.add_trace(go.Bar(x=dc.index,y=net,marker_color=colors.tolist(),name="10L NET",opacity=.8,
            customdata=np.stack([dc['Buy_Total'].values,dc['Sell_Total'].values,
                dc.get('Trade_Judgment',pd.Series('N/A',index=dc.index)).values,
                dc.get('Judgment_Confidence',pd.Series(0,index=dc.index)).values],axis=-1),
            hovertemplate="<b>%{customdata[2]}</b> (%{customdata[3]:.0f}%)<br>B:%{customdata[0]:.1f} S:%{customdata[1]:.1f}<br>NET:%{y:.1f}<extra></extra>"),row=5,col=1)
        fig.add_hline(y=0,line_color="gray",line_width=1,row=5,col=1)

    # 레이아웃
    fig.update_layout(template="plotly_dark",paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=2,r=2,t=40,b=2),height=1200,showlegend=True,hovermode="closest",
        legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="center",x=.5,
            font=dict(size=9,color='#CCC'),bgcolor='rgba(0,0,0,0)'))
    for i in range(1,6):
        ya=f'yaxis{i}' if i>1 else 'yaxis'
        fig.update_layout(**{ya:dict(gridcolor='rgba(45,51,59,.5)',tickfont=dict(size=10,color='#888'))})
    all_d=pd.date_range(start=dc.index[0],end=dc.index[-1],freq='D')
    nt=all_d.difference(dc.index.normalize())
    fig.update_xaxes(rangeslider_visible=False,rangebreaks=[dict(values=nt.tolist())],gridcolor='rgba(45,51,59,.5)',tickfont=dict(size=10,color='#888'))
    for a in fig['layout']['annotations']: a['font']=dict(size=12,color='#AAA',family='Pretendard')
    return fig


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  메타데이터 빌더
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def build_metadata(dc, ticker):
    lat=dc.iloc[-1]; prev=dc.iloc[-2] if len(dc)>=2 else lat
    pc=lat['Close']-prev['Close']; pp=pc/(prev['Close']+1e-10)*100

    # 10-Layer 상세
    LN = ['Trend','Momentum','Candle','BB','Volume','MF','Pattern','Combined','Leading','Lagging']
    buy_layers = {n: float(lat.get(f'BL_{n}',0)) for n in LN}
    sell_layers = {n: float(lat.get(f'SL_{n}',0)) for n in LN}

    # Combined Scan 수집
    active_cs = []
    for cn, ccfg in COMBINED_SCAN_REGISTRY.items():
        if cn in dc.columns and dc[cn].tail(5).any():
            ld = dc[cn].tail(5)[dc[cn].tail(5)].index[-1]
            active_cs.append({'name':ccfg['name'],'kor':ccfg['kor'],'dir':ccfg['dir'],
                'tier':ccfg['tier'],'icon':ccfg['icon'],'color':ccfg['color'],
                'win':ccfg['win'],'date':ld.strftime('%m/%d'),
                'is_today':(dc.index[-1]-ld).days==0,'days_ago':(dc.index[-1]-ld).days})
    active_cs.sort(key=lambda x:(x['tier'],x['days_ago']))

    # 최근 시그널
    recent = []
    for ir, row in dc.tail(15).iterrows():
        ds = ir.strftime('%m/%d')
        for col, cfg in SIGNAL_REGISTRY.items():
            if col in dc.columns and row.get(col,False):
                recent.append((cfg['icon'],cfg['kor'],ds,cfg['dir']))
        for col, cfg in COMBINED_SCAN_REGISTRY.items():
            if col in dc.columns and row.get(col,False):
                recent.append((cfg['icon'],cfg['kor'],ds,cfg['dir']))

    rg=int(lat.get('Regime',0))
    rl={2:'STRONG BULL 🟢🟢',1:'BULL 🟢',0:'NEUTRAL ⚪',-1:'BEAR 🔴',-2:'STRONG BEAR 🔴🔴'}.get(rg,'N/A')

    return {
        'ticker':ticker.upper(),'price':float(lat['Close']),
        'price_change':pc,'price_change_pct':pp,
        'volume':float(lat['Volume']),'avg_volume':float(dc['Volume'].rolling(20).mean().iloc[-1]),
        'wt1':float(lat['WT1']),'rsi':float(lat['RSI']),'mfi':float(lat['MFI']),
        'stochk':float(lat['StochK']),'adx':float(lat['ADX']),
        'atr':float(lat['ATR']),'atr_pct':float(lat['ATR'])/(float(lat['Close'])+1e-10)*100,
        'macd_hist':float(lat.get('MACD_Hist',0)),
        'cmf':float(lat.get('CMF',0)),'composite_accel':float(lat.get('Composite_Accel',0)),
        'rs_ratio':float(lat.get('RS_Ratio',1)),
        'regime':rg,'regime_label':rl,'regime_score':float(lat.get('Regime_Score',0)),
        'last_date':dc.index[-1].strftime('%Y-%m-%d'),
        'squeeze_on':bool(lat.get('Squeeze_On',False)),
        # 10-Layer
        'buy_total':float(lat.get('Buy_Total',0)),'sell_total':float(lat.get('Sell_Total',0)),
        'buy_active':int(lat.get('Buy_Active_Layers',0)),'sell_active':int(lat.get('Sell_Active_Layers',0)),
        'buy_layers':buy_layers,'sell_layers':sell_layers,
        'judgment':str(lat.get('Trade_Judgment','NEUTRAL')),
        'confidence':float(lat.get('Judgment_Confidence',0)),
        # 선행/후행
        'leading_verdict':str(lat.get('Leading_Verdict','중립')),
        'lagging_verdict':str(lat.get('Lagging_Verdict','비추세/횡보')),
        'setup_pressure_buy':float(lat.get('Setup_Pressure_Buy',0)),
        'setup_pressure_sell':float(lat.get('Setup_Pressure_Sell',0)),
        # 리스트
        'combined_scans':active_cs,'recent_signals':recent,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  UI 렌더 함수들
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def render_price_header(m):
    chg=m['price_change'];cp=m['price_change_pct']
    cc='price-change-up' if chg>=0 else 'price-change-down'
    ci='▲' if chg>=0 else '▼'
    vr=m['volume']/m['avg_volume'] if m['avg_volume'] else 0
    ac=m.get('composite_accel',0)
    jg=m['judgment'];cf=m['confidence']
    jc='#34D399' if 'BUY' in jg else ('#F87171' if 'SELL' in jg else '#FCD34D')
    specs=[
        (jc,f"📍{jg}({cf:.0f}%)"),
        ('ind-b' if m['wt1']<-20 else ('ind-s' if m['wt1']>20 else 'ind-n'),f"WT{m['wt1']:.0f}"),
        ('ind-b' if m['rsi']<40 else ('ind-s' if m['rsi']>60 else 'ind-n'),f"RSI{m['rsi']:.0f}"),
        ('ind-b' if vr>1.5 else 'ind-n',f"Vol{vr:.1f}x"),
        ('ind-b' if m['adx']>25 else 'ind-n',f"ADX{m['adx']:.0f}"),
        ('ind-b' if ac>1.5 else ('ind-s' if ac<-1.5 else 'ind-n'),f"Acc{ac:+.1f}"),
        ('ind-b' if m['rs_ratio']>1.03 else ('ind-s' if m['rs_ratio']<.97 else 'ind-n'),f"RS{m['rs_ratio']:.2f}"),
    ]
    ih="".join([f"<span class='ind-mini {c}'>{l}</span>" for c,l in specs])
    st.markdown(f"""<div class="price-header">
        <p style="color:#64748B;font-size:.8rem;margin:0">🚦 {m['ticker']} · {m['last_date']} · <b style="color:#A5B4FC">{m['regime_label']}</b></p>
        <p class="price-big" style="color:#F8FAFC">${m['price']:.2f}
            <span class="{cc}" style="font-size:1.1rem;margin-left:10px;font-weight:700">{ci}{abs(chg):.2f}({abs(cp):.2f}%)</span></p>
        <div style="margin-top:10px;display:flex;gap:4px;flex-wrap:wrap">{ih}</div>
    </div>""",unsafe_allow_html=True)
    # 요약 metrics
    c1,c2,c3,c4=st.columns(4)
    with c1:st.metric("BUY Score",f"{m['buy_total']:.1f}",delta=f"{m['buy_active']}/{NUM_LAYERS}")
    with c2:st.metric("SELL Score",f"{m['sell_total']:.1f}",delta=f"{m['sell_active']}/{NUM_LAYERS}",delta_color="inverse")
    net=m['buy_total']-m['sell_total']
    with c3:st.metric("NET",f"{net:+.1f}",delta=m['judgment'],delta_color="normal" if net>0 else "inverse")
    with c4:st.metric("Confidence",f"{m['confidence']:.0f}%",delta=f"⏳{m['leading_verdict']}")


def render_judgment_card(m):
    """10-Layer 판단 카드"""
    jg=m['judgment'];bt=m['buy_total'];st_=m['sell_total'];net=bt-st_;cf=m['confidence']
    cc='score-card-buy' if 'BUY' in jg else ('score-card-sell' if 'SELL' in jg else 'score-card-neutral')
    jc='#34D399' if 'BUY' in jg else ('#F87171' if 'SELL' in jg else '#FCD34D')
    nc='#34D399' if net>0 else ('#F87171' if net<0 else '#FCD34D')

    labels={'STRONG_BUY':'🟢🟢🟢 STRONG BUY','BUY':'🟢🟢 BUY','WATCH_BUY':'🟡🟢 WATCH BUY',
            'NEUTRAL':'⚪ NEUTRAL','MIXED':'🟠 MIXED','WATCH_SELL':'🟡🔴 WATCH SELL',
            'SELL':'🔴🔴 SELL','STRONG_SELL':'🔴🔴🔴 STRONG SELL'}

    st.markdown(f"""<div class="score-card {cc}">
        <p style="font-size:2rem;font-weight:800;color:{jc};margin:0">{labels.get(jg,jg)}</p>
        <div style="display:flex;align-items:center;gap:10px;justify-content:center;margin-top:8px">
            <div style="flex:0 0 200px;height:8px;background:#151921;border-radius:4px;overflow:hidden">
                <div style="width:{min(cf,100)}%;height:8px;background:{jc};border-radius:4px"></div></div>
            <span style="color:{jc};font-weight:800;font-size:1.1rem">{cf:.0f}%</span></div>
        <div style="display:flex;justify-content:center;gap:32px;margin-top:14px">
            <div><p style="color:#64748B;font-size:.7rem;margin:0">BUY</p><p style="color:#34D399;font-size:1.4rem;font-weight:800;margin:2px 0">{bt:.1f}</p></div>
            <div style="border-left:1px solid rgba(255,255,255,.08);padding-left:32px"><p style="color:#64748B;font-size:.7rem;margin:0">SELL</p><p style="color:#F87171;font-size:1.4rem;font-weight:800;margin:2px 0">{st_:.1f}</p></div>
            <div style="border-left:1px solid rgba(255,255,255,.08);padding-left:32px"><p style="color:#64748B;font-size:.7rem;margin:0">NET</p><p style="color:{nc};font-size:1.4rem;font-weight:800;margin:2px 0">{net:+.1f}</p></div></div>
    </div>""",unsafe_allow_html=True)


def render_10layer_bars(m):
    """10-Layer 바 차트"""
    LN=['Trend','Momentum','Candle','BB','Volume','MF','Pattern','Combined','Leading','Lagging']
    icons={'Trend':'📈','Momentum':'🔥','Candle':'🕯️','BB':'📊','Volume':'📦','MF':'💰','Pattern':'⭐','Combined':'🎯','Leading':'⏳','Lagging':'📊'}

    c1,c2=st.columns(2)
    with c1:
        st.markdown("<p style='color:#34D399;font-weight:700;font-size:.85rem'>▲ BUY Layers</p>",unsafe_allow_html=True)
        for n in LN:
            v=m['buy_layers'].get(n,0);pct=min(max(v,0)/12*100,100)
            op='1' if v>0 else '.3';dc_='#34D399' if v>=0 else '#F87171'
            st.markdown(f"""<div class="layer-row">
                <span style="color:#94A3B8;font-size:.78rem;opacity:{op};width:80px">{icons.get(n,'•')} {n}</span>
                <div class="layer-bar"><div class="layer-fill-b" style="width:{pct}%;opacity:{op}"></div></div>
                <span style="color:{dc_};font-weight:700;font-size:.78rem;width:35px;text-align:right">{v:.1f}</span>
            </div>""",unsafe_allow_html=True)
        total_b=sum(max(0,v) for v in m['buy_layers'].values())
        st.markdown(f"<div style='text-align:center;margin-top:8px'><span style='color:#34D399;font-weight:800;font-size:1.1rem'>{total_b:.1f}</span> <span style='color:#475569;font-size:.8rem'>점 · {m['buy_active']}/{NUM_LAYERS}</span></div>",unsafe_allow_html=True)

    with c2:
        st.markdown("<p style='color:#F87171;font-weight:700;font-size:.85rem'>▼ SELL Layers</p>",unsafe_allow_html=True)
        for n in LN:
            v=m['sell_layers'].get(n,0);pct=min(max(v,0)/12*100,100)
            op='1' if v>0 else '.3';dc_='#F87171' if v>=0 else '#34D399'
            st.markdown(f"""<div class="layer-row">
                <span style="color:#94A3B8;font-size:.78rem;opacity:{op};width:80px">{icons.get(n,'•')} {n}</span>
                <div class="layer-bar"><div class="layer-fill-s" style="width:{pct}%;opacity:{op}"></div></div>
                <span style="color:{dc_};font-weight:700;font-size:.78rem;width:35px;text-align:right">{v:.1f}</span>
            </div>""",unsafe_allow_html=True)
        total_s=sum(max(0,v) for v in m['sell_layers'].values())
        st.markdown(f"<div style='text-align:center;margin-top:8px'><span style='color:#F87171;font-weight:800;font-size:1.1rem'>{total_s:.1f}</span> <span style='color:#475569;font-size:.8rem'>점 · {m['sell_active']}/{NUM_LAYERS}</span></div>",unsafe_allow_html=True)


def render_leading_lagging(m):
    """선행/후행 지표 판단 UI"""
    lv=m['leading_verdict'];lgv=m['lagging_verdict']
    ac=m['composite_accel'];spb=m['setup_pressure_buy'];sps=m['setup_pressure_sell']

    # 선행 지표
    lc='#34D399' if '상승' in lv else ('#F87171' if '하락' in lv else '#FCD34D')
    st.markdown(f"""<div style="background:rgba(255,255,255,.02);border-radius:12px;padding:14px;margin-bottom:10px">
        <p style="font-weight:700;color:#A5B4FC;margin:0 0 8px">⏳ 선행지표 판단</p>
        <p style="color:{lc};font-weight:800;font-size:1.1rem;margin:0">{lv}</p>
        <div style="display:flex;gap:16px;margin-top:8px">
            <span style="color:#888;font-size:.8rem">가속도: <b style="color:{'#34D399' if ac>0 else '#F87171'}">{ac:+.2f}</b></span>
            <span style="color:#888;font-size:.8rem">매수셋업: <b>{spb:.1f}</b></span>
            <span style="color:#888;font-size:.8rem">매도셋업: <b>{sps:.1f}</b></span>
        </div>
    </div>""",unsafe_allow_html=True)

    # 후행 지표
    lgc='#34D399' if '상승' in lgv else ('#F87171' if '하락' in lgv else '#FCD34D')
    rg=m['regime_label'];rs=m['rs_ratio']
    st.markdown(f"""<div style="background:rgba(255,255,255,.02);border-radius:12px;padding:14px">
        <p style="font-weight:700;color:#A5B4FC;margin:0 0 8px">📊 후행지표 판단</p>
        <p style="color:{lgc};font-weight:800;font-size:1.1rem;margin:0">{lgv}</p>
        <div style="display:flex;gap:16px;margin-top:8px">
            <span style="color:#888;font-size:.8rem">국면: <b>{rg}</b></span>
            <span style="color:#888;font-size:.8rem">RS: <b style="color:{'#34D399' if rs>1.03 else ('#F87171' if rs<.97 else '#FCD34D')}">{rs:.3f}</b></span>
        </div>
    </div>""",unsafe_allow_html=True)


def render_combined_scans(m):
    """Combined Scan UI"""
    scans=m.get('combined_scans',[])
    if not scans: st.info("🔍 활성 Combined Scan 없음"); return
    buy_n=sum(1 for s in scans if s['dir']=='buy')
    sell_n=sum(1 for s in scans if s['dir']=='sell')
    t1=sum(1 for s in scans if s['tier']==1)
    hc='#FFD700' if t1>0 else ('#00E676' if buy_n>sell_n else ('#FF1744' if sell_n>buy_n else '#FFC107'))
    st.markdown(f"<div style='background:rgba(255,215,0,.06);border:1px solid {hc}33;border-radius:12px;padding:12px;margin-bottom:10px'><span style='font-size:1.2rem;font-weight:800;color:{hc}'>🎯 Combined Scan: {len(scans)}개</span> <span style='color:#888;margin-left:12px'>T1:{t1} BUY:{buy_n} SELL:{sell_n}</span></div>",unsafe_allow_html=True)
    for s in scans:
        tb={1:'🥇T1',2:'🥈T2',3:'🥉T3'}.get(s['tier'],'T?')
        dc_='#34D399' if s['dir']=='buy' else ('#F87171' if s['dir']=='sell' else '#FFC107')
        bg='rgba(0,230,118,.05)' if s['dir']=='buy' else ('rgba(255,23,68,.05)' if s['dir']=='sell' else 'rgba(255,193,7,.05)')
        td="<span style='background:#FFD700;color:#000;padding:2px 6px;border-radius:4px;font-size:.65rem;font-weight:700'>TODAY</span>" if s['is_today'] else f"<span style='color:#888;font-size:.75rem'>{s['date']}</span>"
        st.markdown(f"<div class='cs-card' style='background:{bg};border-color:{dc_}'><div style='display:flex;justify-content:space-between;align-items:center'><span style='color:{dc_};font-weight:700'>{s['icon']} {s['kor']} <span style='color:#888;font-size:.7rem'>{tb}</span></span><div>{td} <span style='color:#4FC3F7;font-size:.65rem;margin-left:6px'>승률:{s['win']}</span></div></div></div>",unsafe_allow_html=True)


def render_signals(m):
    sigs=m.get('recent_signals',[])
    if not sigs: st.info("최근 15일 시그널 없음"); return
    dg=OrderedDict()
    for icon,lbl,ds,side in sigs: dg.setdefault(ds,[]).append((icon,lbl,side))
    for ds in list(reversed(dg))[:10]:
        grp=dg[ds];bc=sum(1 for _,_,s in grp if s=='buy');sc=sum(1 for _,_,s in grp if s=='sell')
        bl='rgba(0,230,118,.06)' if bc>sc else ('rgba(255,23,68,.06)' if sc>bc else 'rgba(255,193,7,.04)')
        parts=" ".join([f"<span class='ind-mini {'ind-b' if s=='buy' else ('ind-s' if s=='sell' else 'ind-n')}'>{i} {l}</span>" for i,l,s in grp])
        st.markdown(f"<div style='background:{bl};border-radius:10px;padding:10px 14px;margin:5px 0'><div style='display:flex;justify-content:space-between;margin-bottom:4px'><span style='font-weight:700;color:#E8ECF1'>📅 {ds}</span><span style='color:#64748B;font-size:.7rem'>{len(grp)}개</span></div><div style='display:flex;gap:3px;flex-wrap:wrap'>{parts}</div></div>",unsafe_allow_html=True)

def run_backtest_evaluation(df, forward_periods=[3, 5, 10, 20]):
    """실제 과거 데이터를 기반으로 10-Layer 판단과 콤보의 승률/수익률을 검증합니다."""
    # 1. N일 후의 미래 수익률(Forward Returns) 및 승리 여부 계산
    for p in forward_periods:
        df[f'Fwd_Ret_{p}d'] = df['Close'].shift(-p) / df['Close'] - 1
        df[f'Win_{p}d'] = (df[f'Fwd_Ret_{p}d'] > 0).astype(float) # 수익이 나면 1, 아니면 0

    # 2. Trade_Judgment (판단 등급별) 성과 분석
    judgment_results = []
    judgments_to_track = ['STRONG_BUY', 'BUY', 'WATCH_BUY', 'WATCH_SELL', 'SELL', 'STRONG_SELL']
    
    for judgment in judgments_to_track:
        mask = df['Trade_Judgment'] == judgment
        count = mask.sum()
        if count == 0: continue
        
        row = {'판단 등급': judgment, '발생 횟수': count}
        for p in forward_periods:
            row[f'{p}일 후 승률(%)'] = df.loc[mask, f'Win_{p}d'].mean() * 100
            row[f'{p}일 후 평균수익률(%)'] = df.loc[mask, f'Fwd_Ret_{p}d'].mean() * 100
        judgment_results.append(row)
        
    # 3. Combined Scan (주요 콤보별) 성과 분석
    combo_results = []
    for combo_name, cfg in COMBINED_SCAN_REGISTRY.items():
        if combo_name not in df.columns: continue
        mask = df[combo_name] == True
        count = mask.sum()
        if count == 0: continue
        
        row = {'콤보 이름': f"{cfg['icon']} {cfg['kor']} (T{cfg['tier']})", '방향': cfg['dir'], '발생 횟수': count}
        for p in forward_periods:
            # 매도 시그널은 하락해야 승리이므로 부호를 반대로 계산
            multiplier = 1 if cfg['dir'] == 'buy' else -1
            win_rate = ((df.loc[mask, f'Fwd_Ret_{p}d'] * multiplier) > 0).mean() * 100
            avg_ret = df.loc[mask, f'Fwd_Ret_{p}d'].mean() * 100
            
            row[f'{p}일 후 승률(%)'] = win_rate
            row[f'{p}일 후 평균수익률(%)'] = avg_ret
        combo_results.append(row)

    return pd.DataFrame(judgment_results), pd.DataFrame(combo_results)

def render_backtest_tab(df, ticker):
    st.markdown(f"### 🧪 {ticker} 실제 데이터 백테스트 검증 (최근 2년)")
    st.write("각 시그널 발생 후 3일, 5일, 10일, 20일 뒤의 **실제 주가 등락**을 추적한 결과입니다.")
    
    # 평가 함수 실행 (최근 N일의 데이터는 미래 수익률을 알 수 없으므로 dropna 처리)
    df_eval = df.copy()
    j_df, c_df = run_backtest_evaluation(df_eval)
    
    if not j_df.empty:
        st.markdown("#### ⚖️ 10-Layer 판단 등급별 성과")
        st.dataframe(j_df.style.format(precision=2).background_gradient(cmap='RdYlGn', subset=[col for col in j_df.columns if '%' in col]), use_container_width=True)
        
    if not c_df.empty:
        st.markdown("#### 🎯 Combined Scan (콤보) 패턴별 성과")
        # 매수/매도 분리해서 표시
        buy_c_df = c_df[c_df['방향'] == 'buy'].drop(columns=['방향'])
        sell_c_df = c_df[c_df['방향'] == 'sell'].drop(columns=['방향'])
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("<p style='color:#34D399;font-weight:bold'>▲ 매수 콤보 검증</p>", unsafe_allow_html=True)
            if not buy_c_df.empty:
                st.dataframe(buy_c_df.style.format(precision=2).background_gradient(cmap='Greens', subset=[col for col in buy_c_df.columns if '%' in col]), use_container_width=True)
        with c2:
            st.markdown("<p style='color:#F87171;font-weight:bold'>▼ 매도 콤보 검증 (승률: 하락 시 승리)</p>", unsafe_allow_html=True)
            if not sell_c_df.empty:
                st.dataframe(sell_c_df.style.format(precision=2).background_gradient(cmap='Reds', subset=[col for col in sell_c_df.columns if '승률' in col]), use_container_width=True)


def render_analysis(msg):
    m, fig, raw_df = msg.get('meta'), msg.get('fig'), msg.get('raw_df') # raw_df를 넘겨받도록 수정 필요
    if m: render_price_header(m)
    if m or fig:
        t0, t1, t2, t3, t4, t5 = st.tabs(["📈차트", "⚖️매매판단", "🎯CombinedScan", "⏳선행/후행", "📋시그널", "🧪백테스트 검증"])
        with t0:
            if fig: st.plotly_chart(fig,use_container_width=True,theme=None,config={'displaylogo':False,'modeBarButtonsToRemove':['lasso2d','select2d']})
        with t1:
            if m: render_judgment_card(m); st.markdown("#### 📊 10-Layer 스코어"); render_10layer_bars(m)
        with t2:
            if m: render_combined_scans(m)
        with t3:
            if m: render_leading_lagging(m)
        with t4:
            if m: render_signals(m)
        with t5:
            if raw_df is not None:
                render_backtest_tab(raw_df, m['ticker'])


print("✅ Part 3/4 완료: 차트 빌더 + UI")

# ══════════════════════════════════════════════════════════════
#  CipherX V13.0 — PART 4/4: AI, 사이드바, 메인 루프
# ══════════════════════════════════════════════════════════════

def build_prompt_text(dc, meta):
    lat=dc.iloc[-1]; rd=dc.tail(60)
    ps=", ".join([f"'{d.strftime('%Y-%m-%d')}:{r['Close']:.2f}'" for d,r in rd.iterrows()])
    sl=[]
    for ir,row in dc.tail(30).iterrows():
        dd=ir.strftime('%Y-%m-%d')
        for k,v in SIGNAL_REGISTRY.items():
            if row.get(k,False): sl.append(f"{v['icon']}{v['kor']} {dd}")
        for k,v in COMBINED_SCAN_REGISTRY.items():
            if row.get(k,False): sl.append(f"🎯{v['kor']}[T{v['tier']}] {dd}")
    st_text="\n".join(sl[-25:]) if sl else "시그널없음"

    m=meta
    inds=f"WT={m['wt1']:.1f},RSI={m['rsi']:.1f},MFI={m['mfi']:.1f},StK={m['stochk']:.1f},ADX={m['adx']:.1f},ATR={m['atr']:.2f}({m['atr_pct']:.1f}%),MACD_H={m['macd_hist']:.3f},CMF={m['cmf']:.3f},Regime={m['regime']}({m['regime_score']:.1f}),RS={m['rs_ratio']:.3f},Accel={m['composite_accel']:.2f}"

    jtext=f"\n📌[매매판단]\n  최종:{m['judgment']}({m['confidence']:.0f}%)\n  BUY:{m['buy_total']:.1f}({m['buy_active']}/{NUM_LAYERS}) SELL:{m['sell_total']:.1f}({m['sell_active']}/{NUM_LAYERS})\n"
    jtext+=f"  BUY층:{', '.join(f'{k}={v:.1f}' for k,v in m['buy_layers'].items() if v!=0)}\n"
    jtext+=f"  SELL층:{', '.join(f'{k}={v:.1f}' for k,v in m['sell_layers'].items() if v!=0)}\n"
    jtext+=f"  ⏳선행:{m['leading_verdict']} | 📊후행:{m['lagging_verdict']}\n"
    if m['combined_scans']:
        jtext+=f"  🎯Combined:{', '.join(f'{c['icon']}{c['kor']}[T{c['tier']}]' for c in m['combined_scans'])}\n"

    return f"{ps}\n\n📌[지표]{inds}\n\n📌[시그널]\n{st_text}{jtext}"


def build_ai_prompt(ticker, phist, fund):
    return f"""━━━ Role ━━━
월스트리트 20년+ 퀀트 펀드매니저. 10-Layer 판단 시스템 기반 냉철한 분석.
━━━ Rules ━━━
1. ATR기반 손절/목표가 2. 10-Layer 스코어 크로스체크 3. Combined Scan 결과 활용
4. 선행지표(가속도,셋업압력)로 향후 1~3일 예측 5. 후행지표(국면,RS)로 대세 확인
6. 시나리오별 확률% 7. 환각금지 8. Regime 국면 반영
━━━ Data ━━━
[{ticker}]
{phist}
📌[펀더멘탈] {fund}
━━━ Output ━━━
# 🚦 {{ticker}} 퀀트 리포트
[🔵/🔴/🟠] 핵심 한줄
### 📊 시장심리 (3~4문장)
### ⚖️ 10-Layer 판단 검증 (매수/매도 스코어 해석 + 핵심 레이어)
### 🎯 Combined Scan 분석 (활성 스캔 의미)
### ⏳ 선행지표 예측 (가속도+셋업압력+1~3일 전망)
### 📊 후행지표 확인 (국면+RS+추세 상태)
### 📈 종합 기술분석 (VP+BB+모멘텀)
### 🔮 시나리오 (🔵긍정 🟠베이스 🔴리스크 + ATR전략)
### 📋 결론 (종합의견+예측+GRADE)"""


def analyze(ticker, chart_days=252, refresh=False):
    try:
        ts=int(time.time()) if refresh else None
        df=compute_and_cache(ticker,ts)
        if df is None or df.empty or len(df)<50: return None,"데이터부족",None
        dc=df.dropna(subset=['WT1','WT2']).tail(chart_days).copy()
        if dc.empty: return None,"차트데이터부족",None
        meta=build_metadata(dc,ticker)
        fig=build_chart(dc,ticker)
        return fig,build_prompt_text(dc,meta),meta
    except Exception as e:
        import traceback;print(traceback.format_exc())
        return None,f"실패:{e}",None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  세션 & 사이드바 & 메인
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def init_session():
    defs={'messages':[{"role":"assistant","type":"text","content":"🚦 **CipherX V13.0** — 10-Layer Quant Judgment\n\n125개 시그널 + 28개 Combined Scan + 선행/후행 판단\n\n**티커명**을 입력하세요."}],
        'pending_ai_ticker':None,'pending_ai_prompt':None,'last_ticker':None}
    for k,v in defs.items():
        if k not in st.session_state:st.session_state[k]=v
init_session()

with st.sidebar:
    st.markdown("## 🚦 CipherX V13")
    st.markdown("<p style='color:#888;font-size:.75rem'>10-Layer Quant Judgment</p>",unsafe_allow_html=True)
    st.markdown("---")
    app_mode=st.radio("모드",['📊 분석','🔍 스캐너'],index=0,key="app_mode")
    chart_period=st.radio("기간",['3개월','6개월','1년'],index=0,horizontal=True,key="period")
    chart_days={'3개월':63,'6개월':126,'1년':252}[chart_period]
    if st.button("🗑️ 초기화",use_container_width=True,type="secondary"):
        for k in ['messages','pending_ai_ticker','pending_ai_prompt','last_ticker']:
            st.session_state[k]=[{"role":"assistant","type":"text","content":"🚦 **CipherX V13.0**"}] if k=='messages' else None
        st.rerun()

# ═══ 스캐너 ═══
if st.session_state.get('app_mode')=='🔍 스캐너':
    st.markdown("<h2 style='text-align:center;color:#fff'>🔍 Scanner</h2>",unsafe_allow_html=True)
    ci=st.text_input("티커 (쉼표구분)",placeholder="NVDA,TSLA,AAPL...",key="scan_in")
    tickers=[t.strip().upper() for t in ci.split(',') if t.strip()] if ci else ['NVDA','TSLA','AAPL','MSFT','AMZN','META','AMD','QQQ','SPY']
    if st.button("🚀 스캔",type="primary",use_container_width=True):
        pb=st.progress(0);results=[]
        for i,t in enumerate(tickers):
            pb.progress((i+1)/len(tickers),text=f"🔍{t}")
            try:
                df=compute_and_cache(t)
                if df is None or len(df)<50:continue
                dc=df.tail(63);acs=[]
                for cn,ccfg in COMBINED_SCAN_REGISTRY.items():
                    if cn in dc.columns and dc[cn].tail(5).any():
                        ld=dc[cn].tail(5)[dc[cn].tail(5)].index[-1]
                        acs.append({'icon':ccfg['icon'],'kor':ccfg['kor'],'dir':ccfg['dir'],'tier':ccfg['tier'],'date':ld.strftime('%m/%d')})
                if acs:
                    lat=dc.iloc[-1];chg=float((lat['Close']-dc.iloc[-2]['Close'])/dc.iloc[-2]['Close']*100) if len(dc)>=2 else 0
                    results.append({'ticker':t,'price':float(lat['Close']),'chg':chg,'scans':sorted(acs,key=lambda x:x['tier']),'jg':str(lat.get('Trade_Judgment','N/A')),'cf':float(lat.get('Judgment_Confidence',0))})
            except:pass
        pb.progress(1.0,text=f"✅{len(results)}개");time.sleep(.3);pb.empty()
        if not results:st.info("없음")
        else:
            results.sort(key=lambda x:(-sum(1 for s in x['scans'] if s['tier']==1),-len(x['scans'])))
            for r in results:
                chc='#34D399' if r['chg']>=0 else '#F87171';chi='▲' if r['chg']>=0 else '▼'
                jc='#34D399' if 'BUY' in r['jg'] else ('#F87171' if 'SELL' in r['jg'] else '#FCD34D')
                sh="".join([f"<div style='display:flex;gap:6px;padding:2px 0'><span style='color:{'#34D399' if s['dir']=='buy' else ('#F87171' if s['dir']=='sell' else '#FFC107')}'>●</span><span style='color:#E8ECF1;font-size:.82rem'>{s['icon']}{s['kor']}</span><span style='color:#64748B;font-size:.7rem'>{s['date']}</span></div>" for s in r['scans']])
                st.markdown(f"<div style='background:linear-gradient(160deg,#0F1320,#141926);border:1px solid #1C2233;border-radius:14px;padding:14px 18px;margin:6px 0'><div style='display:flex;justify-content:space-between;margin-bottom:8px'><span style='color:#A5B4FC;font-weight:800;font-size:1.15rem'>{r['ticker']}</span><div><span style='color:{jc};font-size:.8rem;font-weight:600'>{r['jg']}({r['cf']:.0f}%)</span> <span style='color:{chc};font-size:.8rem;margin-left:8px'>{chi}{abs(r['chg']):.1f}%</span></div></div>{sh}</div>",unsafe_allow_html=True)
                if st.button(f"📊{r['ticker']}",key=f"sc_{r['ticker']}",use_container_width=True):
                    st.session_state['app_mode']='📊 분석';st.session_state['_auto']=r['ticker'];st.rerun()

# ═══ 분석 ═══
else:
    st.markdown("<h2 style='text-align:center;color:#fff;margin-bottom:16px'>🚦 CipherX</h2>",unsafe_allow_html=True)
    if not st.session_state.last_ticker:
        cols=st.columns(4)
        for i,t in enumerate(["NVDA","TSLA","AAPL","QQQ"]):
            with cols[i]:
                if st.button(t,use_container_width=True):st.session_state['quick']=t
    for i,msg in enumerate(st.session_state.messages):
        av="✨" if msg["role"]=="assistant" else "🧑‍💻"
        with st.chat_message(msg["role"],avatar=av):
            if msg.get("type")=="analysis":
                st.markdown(msg.get("content",""));render_analysis(msg)
                if msg.get("prompt"):
                    with st.expander("📝 프롬프트",expanded=False):st.code(msg["prompt"],language="markdown");st_copy_to_clipboard(msg["prompt"],before_copy_label="📋복사",after_copy_label="✅됨!")
            elif msg.get("type")=="report":
                with st.expander(f"📊{msg.get('ticker','')} AI리포트",expanded=True):st.markdown(msg["content"])
                st.download_button("📥",key=f"dl_{i}",data=msg["content"].encode('utf-8'),file_name=f"{msg.get('ticker','')}_V13_{datetime.now().strftime('%Y%m%d')}.md",mime="text/markdown",use_container_width=True)
            else:st.markdown(msg.get("content",""))

    def _run_ai():
        tp=st.session_state.pending_ai_ticker;pp=st.session_state.pending_ai_prompt
        with st.chat_message("assistant",avatar="✨"):
            pb=st.progress(0,text="로딩...")
            try:
                model=get_gemini_model();pb.progress(20);col=[]
                def gen():
                    pb.progress(40,text="🚀AI생성중...")
                    for ch in model.generate_content(pp,stream=True):
                        if ch.text:col.append(ch.text);yield ch.text
                    pb.progress(100,text="✅완료!")
                with st.expander(f"📊{tp.upper()} AI리포트",expanded=True):st.write_stream(gen())
                time.sleep(.3);pb.empty()
                st.session_state.messages.append({"role":"assistant","type":"report","ticker":tp.upper(),"content":"".join(col)})
                st.session_state.pending_ai_ticker=None;st.session_state.pending_ai_prompt=None;st.rerun()
            except Exception as e:pb.empty();st.error(f"AI오류:{e}")

    def process_ticker(tv,refresh=False):
        tv=tv.strip().upper();st.session_state.pending_ai_ticker=None;st.session_state.pending_ai_prompt=None
        if not _valid_fmt(tv):st.toast(f"⚠️{tv}형식오류",icon="🚨");return
        if not validate_ticker(tv):st.toast(f"⚠️{tv}없음",icon="🔍");return
        st.session_state.messages.append({"role":"user","type":"text","content":tv});st.session_state.last_ticker=tv
        with st.chat_message("assistant",avatar="✨"):
            with st.status(f"🌐{tv}분석중...",expanded=True) as status:
                st.write("📡데이터수집...");fund=fetch_fundamentals(tv)
                st.write("📊125시그널+CombinedScan+10Layer분석...")
                fig,phist,meta=analyze(tv,chart_days,refresh)
                if fig and meta:
                    cs_n=len(meta.get('combined_scans',[]));t1_n=sum(1 for s in meta.get('combined_scans',[]) if s['tier']==1)
                    st.write(f"🎯판단:{meta['judgment']}({meta['confidence']:.0f}%) CS:{cs_n}개(T1:{t1_n})")
                    prompt=build_ai_prompt(tv,phist,fund);status.update(label=f"✅{tv}완료!",state="complete",expanded=False)
                else:prompt=None;status.update(label=f"⚠️{tv}실패",state="error",expanded=False)
            if fig:
                content=f"✅ **{tv}** 분석완료 — **{meta['judgment']}** ({meta['confidence']:.0f}%)"
                if meta.get('combined_scans'):
                    bn=sum(1 for s in meta['combined_scans'] if s['dir']=='buy')
                    sn=sum(1 for s in meta['combined_scans'] if s['dir']=='sell')
                    content+=f"\n🎯 CS: 매수{bn} 매도{sn}"
                content+=f"\n⏳ 선행: {meta['leading_verdict']} | 📊 후행: {meta['lagging_verdict']}"
                st.session_state.messages.append({"role":"assistant","type":"analysis","ticker":tv,"content":content,"fig":fig,"meta":meta,"prompt":prompt})
                st.session_state.pending_ai_ticker=tv;st.session_state.pending_ai_prompt=prompt;st.rerun()
            else:
                st.session_state.messages.append({"role":"assistant","type":"text","content":f"⚠️**{tv}**실패:{phist}"});st.rerun()

    if st.session_state.get('_auto'):process_ticker(st.session_state.pop('_auto'))
    if st.session_state.get('quick'):process_ticker(st.session_state.pop('quick'))
    if st.session_state.pending_ai_ticker and st.session_state.pending_ai_prompt:
        if st.button(f"🚀{st.session_state.pending_ai_ticker.upper()} AI분석",type="primary",use_container_width=True):_run_ai()
    if ti:=st.chat_input("티커 입력 (예: TSLA, AAPL, QQQ)"):process_ticker(ti)

print("✅ Part 4/4 완료: AI, 사이드바, 메인 루프")
print("🚀 CipherX V13.0 — 전체 코드 로드 완료!")