import pandas as pd
import numpy as np
import streamlit as st

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
    ADX_RANGE_MAX=20;ADX_TREND_MIN=30
    LOW_VOLUME_RATIO=0.7;DIVERGENCE_PENALTY=0.30
    MONEY_VETO_SCORE=-8;MONEY_VETO_NEUTRAL=-18
    VP_RR_FLOOR=1.0;VP_RR_STRONG=1.35
    MA20_BLOWOFF_ATR=3.;CLIMAX_VOL_RATIO=2.
    MIN_HISTORY_MA50=60;MIN_HISTORY_MA200=220;MIN_HISTORY_LONG=220
    HIGH_CONFLICT_TOTAL=18.;HIGH_CONFLICT_EDGE=6.;HIGH_CONFLICT_ENSEMBLE=28.
    MARKET_SCORE_TREND_ON=3.;MARKET_SCORE_TREND_OFF=-3.
    MARKET_ENSEMBLE_SCALE=1.2;MARKET_RISK_ON_BONUS=3.;MARKET_RISK_OFF_PENALTY=3.6
    VIX_RISK_OFF_RATIO=1.08;VIX_RISK_ON_RATIO=0.95
    VIX_RISK_OFF_PCT10=0.15;VIX_RISK_ON_PCT10=-0.08
    TNX_HEADWIND_DELTA20=2.5;TNX_TAILWIND_DELTA20=-2.5
    DXY_HEADWIND_PCT20=0.02;DXY_TAILWIND_PCT20=-0.015
    BREADTH_RS_POS=0.005
    BREADTH_RS_NEG=-0.005
    NARROW_LEADERSHIP_GAP=0.02
    CONTEXT_HOLD_ADX=25.
    FLIP_GUARD_MACRO_CONFIRM=2
    FLIP_GUARD_SYNERGY=15.
    FLIP_GUARD_PREDICTION=12.
    ACCEL_COMMITTEE_MOM=3.5
    ACCEL_COMMITTEE_LEAD=5.0
    ACCEL_PREDICTION_SCALE=2.0
    CONTINUATION_SIGNAL_BONUS=3.5
    TRAP_SIGNAL_PENALTY=7.0
    TREND_INFLECTION_STRONG=3
    MARKET_TURN_STRONG=3
    TREND_INFLECTION_SIGNAL_BONUS=3.8
    MARKET_TURN_SIGNAL_BONUS=2.8
    UTBOT_SUPPORT_MAX_ATR=1.25
    UTBOT_OVERHEAT_ATR=3.75
    MIN_DOLLAR_VOLUME_20=5000000.
    TRENDLINE_WINDOW=20
    TRENDLINE_MIN_SLOPE_PCT=0.6
    TRENDLINE_TOUCH_ATR=0.6
    TRENDLINE_BREAK_ATR=0.8

# ── Context (11종) ──
CTX_DEFAULT=0;CTX_EXTREME_OS=1;CTX_EXTREME_OB=2;CTX_STRONG_UP=3;CTX_STRONG_DN=4
CTX_ACCUMULATION=5;CTX_DISTRIBUTION=6;CTX_RANGING=7;CTX_BOTTOMING=8;CTX_TOPPING=9
CTX_VOL_DRY=10;CTX_POST_EXPLOSION=11
CTX_LABELS={0:'default',1:'extreme_oversold',2:'extreme_overbought',3:'strong_trend_up',
    4:'strong_trend_down',5:'accumulation',6:'distribution',7:'ranging',
    8:'bottoming',9:'topping',10:'vol_dry',11:'post_explosion'}
CTX_KOR={0:'기본',1:'극과매도',2:'극과매수',3:'강한 상승 추세',4:'강한 하락 추세',
    5:'매집 구간',6:'분산 구간',7:'횡보 구간',8:'바닥 다지기',9:'천장 형성',
    10:'거래량 감소',11:'급등락 직후'}

CONTEXT_WEIGHTS={
    'extreme_oversold':[.05,.30,.20,.15,.30],'extreme_overbought':[.05,.30,.20,.15,.30],
    'strong_trend_up':[.30,.25,.15,.10,.20],'strong_trend_down':[.30,.25,.15,.10,.20],
    'accumulation':[.08,.15,.35,.22,.20],'distribution':[.08,.15,.35,.22,.20],
    'ranging':[.10,.20,.25,.25,.20],'default':[.20,.25,.20,.15,.20],
    'bottoming':[.08,.25,.30,.17,.20],'topping':[.08,.25,.30,.17,.20],
    'vol_dry':[.10,.15,.15,.30,.30],'post_explosion':[.15,.30,.20,.15,.20],
}
COMMITTEE_NAMES=['Trend','Momentum','Money','Structure','Leading']
COMMITTEE_ICONS = {}

try:
    GEMINI_API_KEY=st.secrets.get("GEMINI_API_KEY", "")
except Exception:
    GEMINI_API_KEY=""


_B,_S,_N='buy','sell','neutral'
def _sig(w,d,icon,label,sym,sz,clr,base,atr_m,kor,desc):
    return {'w':w,'dir':d,'icon':icon,'label':label,'sym':sym,'sz':sz,'clr':clr,'base':base,'atr_m':atr_m,'kor':kor,'desc':desc}

SIGNAL_REGISTRY={
    'Gold_Dot':_sig(3,_B,'','GOLD','circle',18,'#FFD700','Low',-3,'최강매수','RSI<30+MFI<30+WT<-60+Div'),
    'Green_Dot_T1':_sig(2.5,_B,'','BUY T1','circle',16,'#00E676','Low',-2.5,'강한매수','WT과매도+RSI<30+MFI<30'),
    'Green_Dot_T2':_sig(2,_B,'','BUY T2','circle',13,'#69F0AE','Low',-2.2,'매수','WT과매도+RSI/MFI<32'),
    'Blue_Diamond':_sig(2,_B,'','BLUE','diamond',14,'#00bfff','Low',-1.8,'추세매수','WT2≤0+HTF강세'),
    'Green_Circle':_sig(.8,_B,'','BUYCir','circle-open',11,'#00E676','Low',-1.2,'과매도반등','WT과매도+RSI<45'),
    'Blood_Diamond':_sig(3,_S,'','BLOOD','diamond',18,'#DC143C','High',3,'최강매도','RSI>70+MFI>70+WT>60+Div'),
    'Red_Dot_T1':_sig(2.5,_S,'','SELL T1','circle',16,'#FF1744','High',2.5,'강한매도','WT과매수+RSI>70+MFI>70'),
    'Red_Dot_T2':_sig(2,_S,'','SELL T2','circle',13,'#FF5252','High',2.2,'매도','WT과매수+RSI/MFI>68'),
    'Red_Diamond':_sig(2,_S,'','RED','diamond',14,'#ff3333','High',1.8,'추세매도','WT2≥0+HTF약세'),
    'Red_Circle':_sig(.8,_S,'','SELLCir','circle-open',11,'#FF1744','High',1.2,'과매수하락','WT과매수+RSI>55'),
    'Bull_Divergence':_sig(2,_B,'','BullDiv','triangle-up',12,'#AA00FF','Low',-2,'상승다이버','가격↓vsWT↑'),
    'Bear_Divergence':_sig(2,_S,'','BearDiv','triangle-down',12,'#AA00FF','High',2,'하락다이버','가격↑vsWT↓'),
    'RSI_Bull_Divergence':_sig(1.5,_B,'','RSIBDiv','triangle-up',11,'#CE93D8','Low',-1.8,'RSI상승다이버','가격↓vsRSI↑'),
    'RSI_Bear_Divergence':_sig(1.5,_S,'','RSIBrDiv','triangle-down',11,'#CE93D8','High',1.8,'RSI하락다이버','가격↑vsRSI↓'),
    'Hidden_Bull_Div':_sig(1.5,_B,'','HidBull','triangle-up',10,'#E040FB','Low',-1.6,'히든강세','가격↑vsWT↓'),
    'Hidden_Bear_Div':_sig(1.5,_S,'','HidBear','triangle-down',10,'#E040FB','High',1.6,'히든약세','가격↓vsWT↑'),
    'Pullback_123_Bull':_sig(2,_B,'','123PB▲','triangle-up',12,'#00E676','Low',-1.8,'123풀백매수','ADX>30+3일저점↓'),
    'Pullback_123_Bear':_sig(2,_S,'','123PB▼','triangle-down',12,'#FF1744','High',1.8,'123되돌림매도','ADX>30+3일고점↑'),
    'Setup_180_Bull':_sig(2,_B,'','180▲','star-diamond',13,'#00E676','Low',-2,'180매수','전일하위25%→당일상위25%'),
    'Setup_180_Bear':_sig(2,_S,'','180▼','star-diamond',13,'#FF1744','High',2,'180매도','전일상위25%→당일하위25%'),
    'Boomer_Buy':_sig(2,_B,'','Boom▲','star',12,'#00E676','Low',-1.8,'부머매수','ADX>30+2일인사이드'),
    'Boomer_Sell':_sig(2,_S,'','Boom▼','star',12,'#FF1744','High',1.8,'부머매도','ADX>30+2일인사이드'),
    'Expansion_BO':_sig(2.5,_B,'','XBO','star-diamond',14,'#FFD700','Low',-2.5,'확장돌파','2개월신고가+9일최대범위'),
    'Expansion_BD':_sig(2.5,_S,'','XBD','star-diamond',14,'#FF0000','High',2.5,'확장붕괴','2개월신저가+9일최대범위'),
    'Expansion_Pivot_Buy':_sig(2,_B,'','XPvt▲','triangle-up',12,'#00E676','Low',-2,'확장피봇매수','50MA부근폭발상승'),
    'Expansion_Pivot_Sell':_sig(2,_S,'','XPvt▼','triangle-down',12,'#FF1744','High',2,'확장피봇매도','50MA부근폭발하락'),
    'Expansion_Double_Sticks':_sig(2,_S,'','DblStk','hexagram',13,'#FF5722','High',2,'더블스틱','60일신고가후시가아래마감'),
    'Gilligans_Buy':_sig(2,_B,'','Gill▲','hexagon',12,'#00BCD4','Low',-2,'길리건매수','2개월신저가갭다운→반전'),
    'Gilligans_Sell':_sig(2,_S,'','Gill▼','hexagon',12,'#FF5722','High',2,'길리건매도','2개월신고가갭업→반전'),
    'Lizard_Bull':_sig(1.5,_B,'','Liz▲','triangle-up',10,'#00E676','Low',-1.5,'리자드매수','시가종가상위25%+10일신저가'),
    'Lizard_Bear':_sig(1.5,_S,'','Liz▼','triangle-down',10,'#FF1744','High',1.5,'리자드매도','시가종가하위25%+10일신고가'),
    'Slingshot_Bull':_sig(2,_B,'','Sling▲','triangle-up',12,'#00E676','Low',-1.8,'슬링샷매수','신고가후흔들기→재돌파'),
    'Slingshot_Bear':_sig(2,_S,'','Sling▼','triangle-down',12,'#FF1744','High',1.8,'슬링샷매도','신저가후흔들기→재하락'),
    'Jack_In_Box_Bull':_sig(2,_B,'','Jack▲','star',12,'#00E676','Low',-1.8,'잭인더박스매수','XBO후인사이드→재돌파'),
    'Jack_In_Box_Bear':_sig(2,_S,'','Jack▼','star',12,'#FF1744','High',1.8,'잭인더박스매도','XBD후인사이드→재하락'),
    'NonADX_123_Bull':_sig(1.8,_B,'','nADX▲','triangle-up',11,'#69F0AE','Low',-1.5,'비ADX풀백매수','주가>50MA+3일저점↓'),
    'NonADX_123_Bear':_sig(1.8,_S,'','nADX▼','triangle-down',11,'#FF5252','High',1.5,'비ADX풀백매도','주가<50MA+3일고점↑'),
    'Reversal_New_Highs':_sig(2.5,_B,'','RevHi','star-diamond',14,'#00E676','Low',-2.5,'신고가반전','60일신고가+아웃사이드'),
    'Reversal_New_Lows':_sig(2.5,_S,'','RevLo','star-diamond',14,'#FF1744','High',2.5,'신저가반전','60일신저가+아웃사이드'),
    'MA20_Support':_sig(1,_B,'','MA20S','triangle-up',9,'#69F0AE','Low',-1,'20MA지지','20MA부근반등'),
    'MA20_Resistance':_sig(1,_S,'','MA20R','triangle-down',9,'#FF5252','High',1,'20MA저항','20MA부근저항'),
    'MA50_Support':_sig(1.2,_B,'','MA50S','triangle-up',10,'#00E676','Low',-1.2,'50MA지지','50MA부근반등'),
    'MA50_Resistance':_sig(1.2,_S,'','MA50R','triangle-down',10,'#FF1744','High',1.2,'50MA저항','50MA부근저항'),
    'MA200_Support':_sig(1.5,_B,'','MA200S','triangle-up',11,'#00BFA5','Low',-1.5,'200MA지지','200MA부근반등'),
    'MA200_Resistance':_sig(1.5,_S,'','MA200R','triangle-down',11,'#D50000','High',1.5,'200MA저항','200MA부근저항'),
    'Cross_Above_20MA':_sig(.8,_B,'','X▲20','triangle-up',9,'#69F0AE','Low',-.8,'20MA상향','종가>20MA'),
    'Cross_Above_50MA':_sig(1.2,_B,'','X▲50','triangle-up',10,'#00E676','Low',-1,'50MA상향','종가>50MA'),
    'Cross_Above_200MA':_sig(1.5,_B,'','X▲200','triangle-up',11,'#00BFA5','Low',-1.2,'200MA상향','종가>200MA'),
    'Fell_Below_20MA':_sig(.8,_S,'','X▼20','triangle-down',9,'#FF5252','High',.8,'20MA하향','종가<20MA'),
    'Fell_Below_50MA':_sig(1.2,_S,'','X▼50','triangle-down',10,'#FF1744','High',1,'50MA하향','종가<50MA'),
    'Fell_Below_200MA':_sig(1.5,_S,'','X▼200','triangle-down',11,'#D50000','High',1.2,'200MA하향','종가<200MA'),
    'Golden_Cross':_sig(1.5,_B,'','GoldenX','cross',12,'#FFD700','Low',-.8,'골든크로스','50MA>200MA'),
    'Death_Cross':_sig(1.5,_S,'','DeathX','cross',12,'#FF1744','High',.8,'데스크로스','50MA<200MA'),
    'MTF_All_Bullish':_sig(2,_B,'','MTF▲','star',13,'#00E676','Low',-1.5,'다중시간대강세','10/50/200MA위'),
    'MTF_All_Bearish':_sig(2,_S,'','MTF▼','star',13,'#FF1744','High',1.5,'다중시간대약세','10/50/200MA아래'),
    'BB_Squeeze':_sig(1,_N,'','BBSq','square-open',9,'#FFC107','Low',-.5,'BB스퀴즈','BB폭6개월최저'),
    'BB_Squeeze_Started':_sig(1,_N,'','SqSt','hourglass',9,'#90A4AE','Low',-.5,'스퀴즈시작','BB수축시작'),
    'BB_Squeeze_End_Bull':_sig(1.5,_B,'','SqE▲','star-diamond',12,'#00FFFF','Low',-1.5,'스퀴즈해소↑','BB확장+상승'),
    'BB_Squeeze_End_Bear':_sig(1.5,_S,'','SqE▼','star-diamond',12,'#FF6600','High',1.5,'스퀴즈해소↓','BB확장+하락'),
    'BB_Upper_Touch':_sig(.8,_N,'','BB▲T','diamond-open',8,'#FFA726','High',1,'BB상단터치','상단BB접촉'),
    'BB_Lower_Touch':_sig(.8,_N,'','BB▼T','diamond-open',8,'#4FC3F7','Low',-1,'BB하단터치','하단BB접촉'),
    'BB_Upper_Break':_sig(1,_B,'','BB▲Br','diamond-open',10,'#00E5FF','High',1,'BB상단돌파','종가>상단BB'),
    'BB_Lower_Break':_sig(1,_S,'','BB▼Br','diamond-open',10,'#FF6E40','Low',-1,'BB하단붕괴','종가<하단BB'),
    'BB_Lower_Bounce':_sig(1.2,_B,'','BB▼Bo','diamond-open',10,'#4FC3F7','Low',-1.2,'BB하단반등','하단BB+양봉전환'),
    'BB_Upper_Walk':_sig(1.5,_B,'','BBW▲','arrow-up',10,'#00E676','High',1.2,'BB상단워크','연속상단BB'),
    'BB_Lower_Walk':_sig(1.5,_S,'','BBW▼','arrow-down',10,'#FF1744','Low',-1.2,'BB하단워크','연속하단BB'),
    'BB_Wide_Bands':_sig(.5,_N,'','WdBB','square-open',8,'#FFAB40','Low',-.4,'넓은BB','BB폭확대'),
    'Bullish_Engulfing':_sig(1.5,_B,'','BullEng','square',10,'#00E676','Low',-1.3,'상승장악형','하락캔들감싸는양봉'),
    'Bearish_Engulfing':_sig(1.5,_S,'','BearEng','x',10,'#D50000','High',1.3,'하락장악형','상승캔들감싸는음봉'),
    'Morning_Star':_sig(2,_B,'','MornSt','star',13,'#00E676','Low',-2,'모닝스타','큰음봉→소형→강한양봉'),
    'Evening_Star':_sig(2,_S,'','EveSt','star',13,'#FF1744','High',2,'이브닝스타','큰양봉→소형→강한음봉'),
    'Doji':_sig(.5,_N,'','Doji','cross-thin',8,'#FFC107','Low',-.5,'도지','시가≈종가'),
    'Doji_Bullish':_sig(.8,_B,'','DjBull','cross-thin',9,'#69F0AE','Low',-1,'강세도지','도지+하락추세후'),
    'Doji_Bearish':_sig(.8,_S,'','DjBear','cross-thin',9,'#FF5252','High',1,'약세도지','도지+상승추세후'),
    'Hammer':_sig(1.5,_B,'','Hammer','triangle-up',11,'#00E676','Low',-1.5,'해머','긴하단꼬리'),
    'Shooting_Star':_sig(1.5,_S,'','ShStar','triangle-down',11,'#FF1744','High',1.5,'슈팅스타','긴상단꼬리'),
    'Spinning_Top':_sig(.3,_N,'','SpinT','circle-open',7,'#90A4AE','Low',-.3,'팽이형','소형실체'),
    'Inside_Day':_sig(.3,_N,'','InDay','square-open',7,'#FFC107','Low',-.3,'인사이드데이','전일범위안'),
    'Outside_Bullish':_sig(1.5,_B,'','OutB','square',11,'#00E676','Low',-1.5,'강세아웃사이드','범위포함+양봉'),
    'Outside_Bearish':_sig(1.5,_S,'','OutBr','square',11,'#FF1744','High',1.5,'약세아웃사이드','범위포함+음봉'),
    'MACD_Cross_Buy':_sig(1,_B,'','MCD▲','triangle-up',9,'#4CAF50','Low',-1,'MACD골든','MACD>시그널'),
    'MACD_Cross_Sell':_sig(1,_S,'','MCD▼','triangle-down',9,'#E57373','High',1,'MACD데드','MACD<시그널'),
    'MACD_Zero_Cross_Buy':_sig(1.2,_B,'','MC0▲','triangle-up',10,'#4CAF50','Low',-1,'MACD0↑','MACD>0'),
    'MACD_Zero_Cross_Sell':_sig(1.2,_S,'','MC0▼','triangle-down',10,'#E57373','High',1,'MACD0↓','MACD<0'),
    'StochRSI_Cross_Buy':_sig(.8,_B,'','StR▲','circle-open',8,'#81C784','Low',-.8,'StRSI매수','%K>%D과매도'),
    'StochRSI_Cross_Sell':_sig(.8,_S,'','StR▼','circle-open',8,'#EF9A9A','High',.8,'StRSI매도','%K<%D과매수'),
    'Stoch_Reached_OB':_sig(.5,_N,'','St→OB','triangle-up',7,'#FFA726','High',.5,'Stoch과매수도달','%K≥80'),
    'Stoch_Reached_OS':_sig(.5,_N,'','St→OS','triangle-down',7,'#4FC3F7','Low',-.5,'Stoch과매도도달','%K≤20'),
    'Stoch_Overbought':_sig(.8,_S,'','StOB','circle',8,'#FF5252','High',.8,'Stoch과매수','%K>80&%D>80'),
    'Stoch_Oversold':_sig(.8,_B,'','StOS','circle',8,'#69F0AE','Low',-.8,'Stoch과매도','%K<20&%D<20'),
    'DMI_Cross_Bull':_sig(1.5,_B,'','DMI▲','triangle-up',10,'#00E676','Low',-1.2,'DMI강세교차','+DI>-DI'),
    'DMI_Cross_Bear':_sig(1.5,_S,'','DMI▼','triangle-down',10,'#FF1744','High',1.2,'DMI약세교차','-DI>+DI'),
    'ADX_New_Uptrend':_sig(1.5,_B,'','ADX▲','arrow-up',11,'#76FF03','Low',-1.4,'신규상승추세','ADX>25+DI↑'),
    'ADX_New_Downtrend':_sig(1.5,_S,'','ADX▼','arrow-down',11,'#FF3D00','High',1.4,'신규하락추세','ADX>25+DI↓'),
    'ADX_Momentum_Buy':_sig(1.5,_B,'','ADXIg','arrow-up',11,'#76FF03','Low',-1.4,'ADX점화','ADX>20+DI↑'),
    'ADX_Momentum_Sell':_sig(1.5,_S,'','ADXDn','arrow-down',11,'#FF3D00','High',1.4,'ADX하락점화','ADX>20+DI↓'),
    'RSI_Cross_30_Up':_sig(1,_B,'','RSI30▲','triangle-up',9,'#4CAF50','Low',-1,'RSI30↑','RSI>30'),
    'RSI_Cross_50_Up':_sig(1,_B,'','RSI50▲','triangle-up',9,'#69F0AE','Low',-.8,'RSI50↑','RSI>50'),
    'RSI_Cross_70_Down':_sig(1,_S,'','RSI70▼','triangle-down',9,'#EF5350','High',1,'RSI70↓','RSI<70'),
    'RSI_Cross_50_Down':_sig(1,_S,'','RSI50▼','triangle-down',9,'#FF5252','High',.8,'RSI50↓','RSI<50'),
    'Gap_Up':_sig(1,_B,'','Gap▲','arrow-up',10,'#00E676','Low',-1,'갭상승','시가>전일고'),
    'Gap_Down':_sig(1,_S,'','Gap▼','arrow-down',10,'#FF1744','High',1,'갭하락','시가<전일저'),
    'Gap_Up_Closed':_sig(.8,_S,'','GpUF','circle-open',8,'#FFA726','High',.8,'갭업메움','갭메움'),
    'Gap_Down_Closed':_sig(.8,_B,'','GpDF','circle-open',8,'#4FC3F7','Low',-.8,'갭다운메움','갭메움'),
    'NR7':_sig(.5,_N,'','NR7','square-open',7,'#90A4AE','Low',-.3,'NR7','7일최소범위'),
    'NR7_2':_sig(.8,_N,'','NR72','square-open',8,'#90A4AE','Low',-.5,'NR7-2','2일연속NR7'),
    'Narrow_Range_Bar':_sig(.5,_N,'','NrBar','square-open',7,'#90A4AE','Low',-.3,'좁은범위봉','범위<ATR×.5'),
    'Wide_Range_Bar':_sig(.5,_N,'','WdBar','square-open',7,'#FFAB40','Low',-.4,'넓은범위봉','범위>ATR×2'),
    'Calm_After_Storm':_sig(1,_N,'','Calm','diamond-open',9,'#FFC107','Low',-.8,'폭풍뒤고요','WR→NR'),
    'New_52W_High':_sig(1.5,_B,'','52H','star-triangle-up',12,'#FFD700','High',1.5,'52주신고가','52주고가갱신'),
    'New_52W_Low':_sig(1.5,_S,'','52L','star-triangle-down',12,'#B71C1C','Low',-1.5,'52주신저가','52주저가갱신'),
    'New_52W_Closing_High':_sig(1.2,_B,'','52CH','star',11,'#FFD700','High',1.2,'52주종가신고','종가최고'),
    'New_52W_Closing_Low':_sig(1.2,_S,'','52CL','star',11,'#B71C1C','Low',-1.2,'52주종가신저','종가최저'),
    'Up_3_Days':_sig(.5,_B,'','Up3','triangle-up',8,'#69F0AE','High',.5,'3일연속↑','3일양봉'),
    'Up_4_Days':_sig(.6,_B,'','Up4','triangle-up',8,'#69F0AE','High',.6,'4일연속↑','4일양봉'),
    'Up_5_Days':_sig(.8,_B,'','Up5','triangle-up',9,'#00E676','High',.8,'5일연속↑','5일양봉'),
    'Down_3_Days':_sig(.5,_S,'','Dn3','triangle-down',8,'#FF5252','Low',-.5,'3일연속↓','3일음봉'),
    'Down_4_Days':_sig(.6,_S,'','Dn4','triangle-down',8,'#FF5252','Low',-.6,'4일연속↓','4일음봉'),
    'Down_5_Days':_sig(.8,_S,'','Dn5','triangle-down',9,'#FF1744','Low',-.8,'5일연속↓','5일음봉'),
    'Multiple_Ten_Bull':_sig(1,_B,'','Rnd▲','triangle-up',9,'#00E676','Low',-1,'10배수강세','라운드넘버돌파'),
    'Multiple_Ten_Bear':_sig(1,_S,'','Rnd▼','triangle-down',9,'#FF1744','High',1,'10배수약세','라운드넘버이탈'),
    'Pocket_Pivot':_sig(1.5,_B,'','PkPvt','triangle-up',11,'#7C4DFF','Low',-1.5,'포켓피봇','양봉+거래량>10일하락최대'),
    'Parabolic_Rise':_sig(2,_N,'','Para','star-diamond',13,'#FF6D00','High',2,'포물선상승','급격한수직상승'),
    'Three_Weeks_Tight':_sig(1.5,_B,'','3WT','square',11,'#00E676','Low',-1.5,'3주타이트','3주좁은종가'),
    'Squeeze_Fire_Buy':_sig(1.5,_B,'','SqF▲','star-diamond',14,'#00FFFF','Low',-1.5,'스퀴즈매수','TTM해소+모멘텀↑'),
    'Squeeze_Fire_Sell':_sig(1.5,_S,'','SqF▼','star-diamond',14,'#FF6600','High',1.5,'스퀴즈매도','TTM해소+모멘텀↓'),
    'Volume_Climax_Buy':_sig(2,_B,'','VCl▲','hexagram',14,'#00BCD4','Low',-2.8,'거래량클라이맥스','3x거래량+WT과매도+반전'),
    'Volume_Climax_Sell':_sig(2,_S,'','VCl▼','hexagram',14,'#FF5722','High',2.8,'거래량클라이맥스','3x거래량+WT과매수+반전'),
    'Volume_Surge':_sig(1.5,_N,'','VSrg','hexagram',12,'#00BCD4','Low',-1,'거래량급증','거래량≥50일평균×3'),
    'OBV_Div_Buy':_sig(.8,_B,'','OBV▲','triangle-up',10,'#80DEEA','Low',-1.4,'OBV다이버','OBV↑vs가격↓'),
    'OBV_Div_Sell':_sig(.8,_S,'','OBV▼','triangle-down',10,'#FFAB91','High',1.4,'OBV다이버','OBV↓vs가격↑'),
    'SuperTrend_Buy':_sig(1.5,_B,'','ST▲','arrow-up',12,'#00E5FF','Low',-1.5,'ST강세','ST위로돌파'),
    'SuperTrend_Sell':_sig(2,_S,'','ST▼','arrow-down',12,'#FF1744','High',1.5,'ST약세','ST하향돌파'),
    'EMA_Pullback_Buy':_sig(2,_B,'','EPB▲','triangle-up',13,'#00BFA5','Low',-1.8,'EMA눌림목','상승추세EMA조정'),
    'EMA_Pullback_Sell':_sig(2,_S,'','EPB▼','triangle-down',13,'#FF6E40','High',1.8,'EMA되돌림','하락추세EMA반등'),
    'Momentum_Ignition_Buy':_sig(2.5,_B,'','MIg▲','star-diamond',15,'#FF6D00','Low',-2.5,'모멘텀점화','장대양봉+거래량'),
    'Momentum_Ignition_Sell':_sig(2.5,_S,'','MIg▼','star-diamond',15,'#D50000','High',2.5,'모멘텀점화매도','장대음봉+거래량'),
    'Parabolic_Bottom_Buy':_sig(3,_B,'','PBot','diamond',16,'#00FFFF','Low',-3,'포물선바닥','WT<-70꺾임+양봉'),
    'Parabolic_Top_Sell':_sig(3,_S,'','PTop','diamond',16,'#FF0000','High',3,'포물선천장','WT>70꺾임+음봉'),
    'VWAP_Bounce_Buy':_sig(1.5,_B,'','VW▲','triangle-up',11,'#00E5FF','Low',-1.3,'VWAP반등','VWAP복귀+WT교차'),
    'VWAP_Reject_Sell':_sig(1.5,_S,'','VW▼','triangle-down',11,'#FF6E40','High',1.3,'VWAP저항','VWAP실패'),
    'MF_Cross_Bull':_sig(1.5,_B,'','MF▲','triangle-up',11,'#00E676','Low',-1.2,'MF강세','자금흐름양전환'),
    'MF_Cross_Bear':_sig(1.5,_S,'','MF▼','triangle-down',11,'#FF1744','High',1.2,'MF약세','자금흐름음전환'),
    'MF_Bull_Div':_sig(1.8,_B,'','MFBd','triangle-up',11,'#7C4DFF','Low',-1.5,'MF상승다이버','가격↓vsMF↑'),
    'MF_Bear_Div':_sig(1.8,_S,'','MFBrd','triangle-down',11,'#E040FB','High',1.5,'MF하락다이버','가격↑vsMF↓'),
    'MF_Accel_Up':_sig(1,_B,'','MFA▲','arrow-up',9,'#69F0AE','Low',-.8,'MF가속↑','5일MF연속↑'),
    'MF_Accel_Dn':_sig(1,_S,'','MFA▼','arrow-down',9,'#FF5252','High',.8,'MF가속↓','5일MF연속↓'),
    'Kumo_Breakout_Bull':_sig(2,_B,'','Kumo▲','triangle-up',13,'#00E676','Low',-2,'쿠모상향돌파','종가>구름상단'),
    'Kumo_Breakout_Bear':_sig(2,_S,'','Kumo▼','triangle-down',13,'#FF1744','High',2,'쿠모하향돌파','종가<구름하단'),
    'TK_Cross_Bull':_sig(1.5,_B,'','TK▲','triangle-up',10,'#69F0AE','Low',-1.2,'TK골든','전환>기준'),
    'TK_Cross_Bear':_sig(1.5,_S,'','TK▼','triangle-down',10,'#FF5252','High',1.2,'TK데드','전환<기준'),
    'CMF_Bull':_sig(1.2,_B,'','CMF▲','triangle-up',10,'#00BCD4','Low',-1,'CMF강세','CMF>0.1'),
    'CMF_Bear':_sig(1.2,_S,'','CMF▼','triangle-down',10,'#FF5722','High',1,'CMF약세','CMF<-0.1'),
    'Setup_Squeeze_Bull':_sig(1,_B,'','SqS▲','hourglass',10,'#80DEEA','Low',-.8,'스퀴즈셋업▲','BB축소+모멘텀↑임박'),
    'Setup_Squeeze_Bear':_sig(1,_S,'','SqS▼','hourglass',10,'#FFAB91','High',.8,'스퀴즈셋업▼','BB축소+모멘텀↓임박'),
    'Momentum_Accel_Buy':_sig(1.5,_B,'','MoA▲','arrow-up',11,'#76FF03','Low',-1.2,'모멘텀가속▲','RSI+WT+MACD가속'),
    'Momentum_Accel_Sell':_sig(1.5,_S,'','MoA▼','arrow-down',11,'#FF3D00','High',1.2,'모멘텀가속▼','RSI+WT+MACD감속'),
    'Volume_Dry_Up':_sig(.5,_N,'','VDry','square-open',8,'#FFE082','Low',-.3,'거래량고갈','5일연속평균이하'),
    'WT_Convergence_Bull':_sig(1.2,_B,'','WTC▲','triangle-up',10,'#B2FF59','Low',-1,'WT수렴매수','빠른수렴+과매도'),
    'WT_Convergence_Bear':_sig(1.2,_S,'','WTC▼','triangle-down',10,'#FF8A80','High',1,'WT수렴매도','빠른수렴+과매수'),
    'Volume_POC_Breakout':_sig(2,_B,'','POC▲','triangle-up',13,'#7C4DFF','Low',-1.8,'POC상향','종가>POC'),
    'Volume_POC_Breakdown':_sig(2,_S,'','POC▼','triangle-down',13,'#E040FB','High',1.8,'POC하향','종가<POC'),
    'VP_VAH_Resistance':_sig(1,_S,'','VAH','triangle-down',10,'#FFAB91','High',1,'VAH저항','VA상단접근'),
    'VP_VAL_Support':_sig(1,_B,'','VAL','triangle-up',10,'#80DEEA','Low',-1,'VAL지지','VA하단접근'),
    'Relative_Strength_Buy':_sig(2,_B,'','RS▲','star-diamond',13,'#00E5FF','Low',-1.8,'상대강도매수','SPY대비강세'),
    'Relative_Strength_Sell':_sig(1.5,_S,'','RS▼','star-diamond',11,'#FF6E40','High',1.5,'상대약세매도','SPY대비약세'),
    'UTBot_Buy':_sig(2,_B,'','UTBot▲','triangle-up',15,'#00E676','Low',-2,'UT봇매수','ATR트레일링전환'),
    'UTBot_Sell':_sig(2,_S,'','UTBot▼','triangle-down',15,'#FF1744','High',2,'UT봇매도','ATR트레일링전환'),
    'Hull_Turn_Bull':_sig(1.8,_B,'','Hull▲','circle',15,'#00E676','Low',-1.5,'Hull강세전환','HMA빨강→초록'),
    'Hull_Turn_Bear':_sig(1.8,_S,'','Hull▼','circle',15,'#FF1744','High',1.5,'Hull약세전환','HMA초록→빨강'),
    'StochSlow_Cross_Buy':_sig(1,_B,'','StSl▲','circle-open',9,'#81C784','Low',-1,'StochSlow매수','SlowK>SlowD바닥권'),
    'StochSlow_Cross_Sell':_sig(1,_S,'','StSl▼','circle-open',9,'#EF9A9A','High',1,'StochSlow매도','SlowK<SlowD천장권'),
    'Squeeze_Mom_Cross_Up':_sig(1.5,_B,'','SqMom▲','diamond',11,'#00FFFF','Low',-1.2,'스퀴즈모멘텀0↑','모멘텀음→양'),
    'Squeeze_Mom_Cross_Down':_sig(1.5,_S,'','SqMom▼','diamond',11,'#FF6600','High',1.2,'스퀴즈모멘텀0↓','모멘텀양→음'),
    'VuManChu_Bull':_sig(2.5,_B,'','VuMC▲','star',14,'#00E676','Low',-2.5,'VuManChu강세','WT과매도+Hull강세+반전'),
    'VuManChu_Bear':_sig(2.5,_S,'','VuMC▼','star',14,'#FF1744','High',2.5,'VuManChu약세','WT과매수+Hull약세+반전'),
    'Volume_Dry_Breakout_Buy':_sig(2,_B,'','VDB▲','triangle-up',12,'#00E676','Low',-2,'건조돌파매수','5일건조후거래량폭발'),
    'Volume_Dry_Breakout_Sell':_sig(2,_S,'','VDB▼','triangle-down',12,'#FF1744','High',2,'건조돌파매도','5일건조후거래량폭발'),
    'Doji_Breakout_Buy':_sig(1.5,_B,'','DjBO▲','triangle-up',10,'#00E676','Low',-1.5,'도지돌파매수','연속도지후방향결정'),
    'Doji_Breakout_Sell':_sig(1.5,_S,'','DjBO▼','triangle-down',10,'#FF1744','High',1.5,'도지돌파매도','연속도지후방향결정'),
    'Three_Bar_Reversal_Buy':_sig(2,_B,'','3BR▲','triangle-up',12,'#00BFA5','Low',-2,'3바반전매수','3연하후강한양봉'),
    'Three_Bar_Reversal_Sell':_sig(2,_S,'','3BR▼','triangle-down',12,'#D50000','High',2,'3바반전매도','3연상후강한음봉'),
    'System_Turn_Bull':_sig(3.5,_B,'','Sys▲','star-diamond',16,'#00FF00','Low',-4,'전면매수전환','엔진종합판단매수전환'),
    'System_Turn_Bear':_sig(3.5,_S,'','Sys▼','star-diamond',16,'#FF0000','High',4,'전면매도전환','엔진종합판단매도전환'),
}

COMBINED_SCAN_REGISTRY={
    'CS_Ultimate_Buy':{'name':'🏆 ULTIMATE BUY','kor':'궁극의매수','dir':'buy','tier':1,'icon':'','color':'#FFD700','desc':'6중확인','win':'75-85%'},
    'CS_Triple_Oversold_Reversal':{'name':'🔥 Triple OS','kor':'삼중과매도반전','dir':'buy','tier':1,'icon':'','color':'#00E676','desc':'WT+RSI+Stoch+반전','win':'70-80%'},
    'CS_Breakout_Momentum_Buy':{'name':'🚀 Breakout','kor':'돌파모멘텀','dir':'buy','tier':1,'icon':'','color':'#00E676','desc':'52W+거래량+ADX','win':'65-75%'},
    'CS_Institutional_Accumulation':{'name':'🏦 Instit','kor':'기관매집','dir':'buy','tier':1,'icon':'','color':'#00BCD4','desc':'포켓피봇+OBV','win':'70-80%'},
    'CS_Divergence_Confluence_Buy':{'name':'📊 DivConf','kor':'다이버합류매수','dir':'buy','tier':1,'icon':'','color':'#7C4DFF','desc':'다중다이버전스','win':'70-80%'},
    'CS_Capitulation_Bottom':{'name':'🏳️ Capitul','kor':'항복바닥','dir':'buy','tier':1,'icon':'','color':'#00E676','desc':'52W저+극과매도','win':'70-80%'},
    'CS_Triple_Confirm_Buy':{'name':'🤖 TriConf▲','kor':'삼중확인매수','dir':'buy','tier':1,'icon':'','color':'#00E676','desc':'UTBot+Hull+WT동시','win':'75-85%'},
    'CS_VuManChu_Squeeze_Buy':{'name':'💎 VuMC+Sq▲','kor':'VuManChu스퀴즈매수','dir':'buy','tier':1,'icon':'','color':'#00E676','desc':'VuManChu+스퀴즈해소','win':'80-90%'},
    'CS_Ultimate_Sell':{'name':'🏆 ULTIMATE SELL','kor':'궁극의매도','dir':'sell','tier':1,'icon':'','color':'#FFD700','desc':'6중확인','win':'75-85%'},
    'CS_Triple_Overbought_Exhaustion':{'name':'🌡️ Triple OB','kor':'삼중과매수소진','dir':'sell','tier':1,'icon':'','color':'#FF1744','desc':'WT+RSI+Stoch+반전','win':'70-80%'},
    'CS_Breakdown_Momentum_Sell':{'name':'💨 Breakdown','kor':'붕괴모멘텀','dir':'sell','tier':1,'icon':'','color':'#FF1744','desc':'52W+거래량+ADX','win':'65-75%'},
    'CS_Parabolic_Exhaustion_Sell':{'name':'🎢 ParaExh','kor':'포물선소진','dir':'sell','tier':1,'icon':'','color':'#D50000','desc':'포물선+천장캔들','win':'70-80%'},
    'CS_Divergence_Confluence_Sell':{'name':'📉 DivConf','kor':'다이버합류매도','dir':'sell','tier':1,'icon':'','color':'#E040FB','desc':'다중다이버전스','win':'70-80%'},
    'CS_Blow_Off_Top':{'name':'🎆 BlowOff','kor':'블로우오프천장','dir':'sell','tier':1,'icon':'','color':'#FF1744','desc':'52W고+극과매수','win':'70-80%'},
    'CS_Triple_Confirm_Sell':{'name':'🤖 TriConf▼','kor':'삼중확인매도','dir':'sell','tier':1,'icon':'','color':'#FF1744','desc':'UTBot+Hull+WT동시','win':'75-85%'},
    'CS_VuManChu_Squeeze_Sell':{'name':'💎 VuMC+Sq▼','kor':'VuManChu스퀴즈매도','dir':'sell','tier':1,'icon':'','color':'#FF1744','desc':'VuManChu+스퀴즈해소','win':'80-90%'},
    'CS_Trend_Pullback_Buy':{'name':'🎯 TrendPB','kor':'추세눌림목','dir':'buy','tier':2,'icon':'','color':'#00E676','desc':'상승추세+MA지지','win':'60-70%'},
    'CS_Squeeze_Breakout_Buy':{'name':'💥 SqBreak','kor':'스퀴즈돌파','dir':'buy','tier':2,'icon':'','color':'#00FFFF','desc':'BB해소+상방','win':'60-70%'},
    'CS_MA_Confluence_Buy':{'name':'📈 MAConf','kor':'MA합류','dir':'buy','tier':2,'icon':'','color':'#69F0AE','desc':'골든+정배열','win':'60-70%'},
    'CS_Cooper_Setup_Buy':{'name':'🃏 Cooper','kor':'쿠퍼셋업','dir':'buy','tier':2,'icon':'','color':'#FF6D00','desc':'ADX+쿠퍼패턴','win':'60-70%'},
    'CS_Volume_Climax_Rev_Buy':{'name':'🌊 VolRev','kor':'거래량반전','dir':'buy','tier':2,'icon':'','color':'#00BCD4','desc':'거래량폭발+과매도','win':'60-70%'},
    'CS_Ichimoku_Breakout_Buy':{'name':'☁️ IchiBreak','kor':'이치모쿠돌파','dir':'buy','tier':2,'icon':'','color':'#00E676','desc':'쿠모+TK','win':'60-70%'},
    'CS_Trend_Rejection_Sell':{'name':'🎯 TrendRej','kor':'추세거부','dir':'sell','tier':2,'icon':'','color':'#FF1744','desc':'하락추세+MA저항','win':'60-70%'},
    'CS_Squeeze_Breakdown_Sell':{'name':'💨 SqBrkDn','kor':'스퀴즈붕괴','dir':'sell','tier':2,'icon':'','color':'#FF6600','desc':'BB해소+하방','win':'60-70%'},
    'CS_MA_Breakdown_Sell':{'name':'📉 MABreak','kor':'MA붕괴','dir':'sell','tier':2,'icon':'','color':'#FF5252','desc':'데스+역배열','win':'60-70%'},
    'CS_Cooper_Setup_Sell':{'name':'🃏 CooperSell','kor':'쿠퍼매도','dir':'sell','tier':2,'icon':'','color':'#FF3D00','desc':'ADX+쿠퍼매도','win':'60-70%'},
    'CS_Gap_Failure_Sell':{'name':'⏬ GapFail','kor':'갭실패','dir':'sell','tier':2,'icon':'','color':'#FF1744','desc':'갭업후약세반전','win':'60-70%'},
    'CS_Bottom_Fishing_Buy':{'name':'🪝 BottomFish','kor':'바닥낚시반전','dir':'buy','tier':2,'icon':'','color':'#00E676','desc':'심과매도+반전확인','win':'62-74%'},
    'CS_Top_Fishing_Sell':{'name':'🎣 TopFish','kor':'천장낚시반전','dir':'sell','tier':2,'icon':'','color':'#FF5252','desc':'심과매수+반전확인','win':'62-74%'},
    'CS_Oversold_Bounce_Buy':{'name':'🏓 OSBounce','kor':'과매도반등','dir':'buy','tier':3,'icon':'','color':'#69F0AE','desc':'Stoch과매도+캔들','win':'55-65%'},
    'CS_Momentum_Accel_Buy':{'name':'⚡ MomAcc','kor':'모멘텀가속','dir':'buy','tier':3,'icon':'','color':'#76FF03','desc':'RSI+WT+MACD가속','win':'55-65%'},
    'CS_Structure_Support_Buy':{'name':'🏗️ Support','kor':'구조적지지','dir':'buy','tier':3,'icon':'','color':'#4FC3F7','desc':'VP+BB지지','win':'55-65%'},
    'CS_Overbought_Fade_Sell':{'name':'📉 OBFade','kor':'과매수페이드','dir':'sell','tier':3,'icon':'','color':'#FF5252','desc':'Stoch과매수+캔들','win':'55-65%'},
    'CS_Volatility_Explosion':{'name':'💣 VolExpl','kor':'변동성폭발셋업','dir':'neutral','tier':2,'icon':'','color':'#FFC107','desc':'NR7+BB스퀴즈','win':'방향70%+'},
}

STRONG_BUY_SIGS={'System_Turn_Bull','Gold_Dot','Green_Dot_T1','Parabolic_Bottom_Buy','Volume_Climax_Buy','Momentum_Ignition_Buy','Expansion_BO','Morning_Star','Reversal_New_Highs','CS_Ultimate_Buy','CS_Triple_Oversold_Reversal','CS_Breakout_Momentum_Buy','CS_Capitulation_Bottom','CS_Triple_Confirm_Buy','CS_VuManChu_Squeeze_Buy','VuManChu_Bull'}
STRONG_SELL_SIGS={'System_Turn_Bear','Blood_Diamond','Red_Dot_T1','Parabolic_Top_Sell','Volume_Climax_Sell','Momentum_Ignition_Sell','Expansion_BD','Evening_Star','Reversal_New_Lows','CS_Ultimate_Sell','CS_Triple_Overbought_Exhaustion','CS_Breakdown_Momentum_Sell','CS_Blow_Off_Top','CS_Parabolic_Exhaustion_Sell','CS_Triple_Confirm_Sell','CS_VuManChu_Squeeze_Sell','VuManChu_Bear'}

COOLDOWN_MAP={'Squeeze_Fire_Buy':5,'Squeeze_Fire_Sell':5,'Bullish_Engulfing':5,'Bearish_Engulfing':5,'Hammer':5,'Shooting_Star':5,'Morning_Star':7,'Evening_Star':7,'Golden_Cross':20,'Death_Cross':20,'Expansion_BO':10,'Expansion_BD':10,'Gilligans_Buy':10,'Gilligans_Sell':10,'MACD_Cross_Buy':12,'MACD_Cross_Sell':12,'Kumo_Breakout_Bull':10,'Kumo_Breakout_Bear':10,'New_52W_High':10,'New_52W_Low':10,'StochRSI_Cross_Buy':7,'StochRSI_Cross_Sell':7,'ADX_Momentum_Buy':10,'ADX_Momentum_Sell':10,'EMA_Pullback_Buy':7,'EMA_Pullback_Sell':7,'SuperTrend_Buy':10,'SuperTrend_Sell':10,'Parabolic_Bottom_Buy':5,'Parabolic_Top_Sell':5,'DMI_Cross_Bull':10,'DMI_Cross_Bear':10,'Boomer_Buy':10,'Boomer_Sell':10,'Setup_180_Bull':7,'Setup_180_Bear':7,'VWAP_Bounce_Buy':7,'VWAP_Reject_Sell':7,'Momentum_Ignition_Buy':10,'Momentum_Ignition_Sell':10,'Slingshot_Bull':7,'Slingshot_Bear':7,'MF_Cross_Bull':10,'MF_Cross_Bear':10,'Pullback_123_Bull':7,'Pullback_123_Bear':7,'UTBot_Buy':10,'UTBot_Sell':10,'Hull_Turn_Bull':7,'Hull_Turn_Bear':7,'StochSlow_Cross_Buy':7,'StochSlow_Cross_Sell':7,'Squeeze_Mom_Cross_Up':5,'Squeeze_Mom_Cross_Down':5,'VuManChu_Bull':10,'VuManChu_Bear':10,'Volume_Dry_Breakout_Buy':7,'Volume_Dry_Breakout_Sell':7,'Doji_Breakout_Buy':5,'Doji_Breakout_Sell':5,'Three_Bar_Reversal_Buy':5,'Three_Bar_Reversal_Sell':5}

# ━━━ 유틸리티 ━━━
