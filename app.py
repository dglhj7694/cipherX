import streamlit as st
import google.generativeai as genai
import time, json, re, math
from datetime import datetime
from st_copy_to_clipboard import st_copy_to_clipboard
from concurrent.futures import ThreadPoolExecutor, as_completed
import yfinance as yf
import pandas as pd# Extracted modules
from config import *
from utils import validate_ticker, _valid_fmt, _sf, fetch_fundamentals, compute_and_cache, _compute_cached
from chart import build_chart, build_metadata
from ui import render_analysis
from ai_agent import build_prompt_text, build_ai_prompt
from sectors import SECTOR_GROUPS

if 'theme_set' not in st.session_state:
    st.set_page_config(page_title="CipherX", page_icon="💠", layout="wide", initial_sidebar_state="expanded")

# ━━━ CSS ━━━
st.markdown("""<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
html,body,[class*="css"]{font-family:'Pretendard',sans-serif!important}
.stApp{background-color:#0B0E14;background-image:radial-gradient(ellipse at top,#1A2035 0%,#0B0E14 60%);background-attachment:fixed;}
@keyframes fadeUp{from{opacity:0;transform:translateY(20px);}to{opacity:1;transform:translateY(0);}}
.fade-up{animation:fadeUp 0.6s cubic-bezier(0.16,1,0.3,1) forwards;}
p,li{color:#E8ECF1!important} h1,h2{color:#FFF!important;font-weight:800!important;letter-spacing:-0.5px;}
h3{color:#F0F4F8!important;font-weight:700!important;letter-spacing:-0.3px;}
h4{color:#CBD5E1!important;font-weight:600!important;font-size:1rem!important}
.block-container{padding-top:1rem!important;max-width:1400px}
div.stButton>button[kind="primary"]{background:linear-gradient(135deg,#6366F1,#8B5CF6)!important;color:#fff!important;border:none!important;border-radius:12px!important;font-weight:700!important;width:100%;transition:all .3s ease;box-shadow:0 4px 15px rgba(99,102,241,0.3)!important;}
div.stButton>button[kind="primary"]:hover{transform:translateY(-2px);box-shadow:0 6px 20px rgba(99,102,241,0.5)!important;}
div.stButton>button[kind="secondary"]{background:rgba(18,22,31,0.6)!important;backdrop-filter:blur(10px)!important;color:#C4CDD8!important;border:1px solid #2A3040!important;border-radius:12px!important;width:100%;transition:all .3s!important;}
div.stButton>button[kind="secondary"]:hover{background:rgba(42,48,64,0.6)!important;color:#fff!important;border-color:#6366F1!important;transform:translateY(-2px);}
.price-header{background:rgba(15,19,32,0.6);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);border:1px solid rgba(255,255,255,0.05);border-radius:16px;padding:20px 24px;margin-bottom:18px;box-shadow:0 8px 32px rgba(0,0,0,0.3);transition:all 0.3s ease;}
.price-header:hover{border-color:rgba(99,102,241,0.3);transform:translateY(-2px);box-shadow:0 12px 40px rgba(0,0,0,0.4);}
.price-big{font-size:2.2rem;font-weight:800;margin:0;letter-spacing:-1px;}
.price-change-up{color:#34D399!important} .price-change-down{color:#F87171!important}
.ind-mini{display:inline-block;padding:4px 10px;margin:2px;border-radius:8px;font-size:.76rem;font-weight:600;letter-spacing:0.5px;}
.ind-b{background:rgba(16,185,129,.12);color:#6EE7B7;border:1px solid rgba(16,185,129,0.2);}
.ind-s{background:rgba(239,68,68,.12);color:#FCA5A5;border:1px solid rgba(239,68,68,0.2);}
.ind-n{background:rgba(245,158,11,.10);color:#FCD34D;border:1px solid rgba(245,158,11,0.2);}
.layer-row{display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid rgba(255,255,255,.04);transition:all .2s;}
.layer-row:hover{background:rgba(255,255,255,0.02);}
.layer-bar{background:rgba(0,0,0,0.3);border-radius:4px;height:8px;flex:1;margin:0 8px;overflow:hidden;box-shadow:inset 0 1px 3px rgba(0,0,0,0.5);}
.layer-fill-b{height:8px;border-radius:4px;background:linear-gradient(90deg,#059669,#34D399);box-shadow:0 0 8px rgba(52,211,153,0.5);}
.layer-fill-s{height:8px;border-radius:4px;background:linear-gradient(90deg,#DC2626,#F87171);box-shadow:0 0 8px rgba(248,113,113,0.5);}
.score-card{border-radius:16px;padding:24px;text-align:center;position:relative;overflow:hidden;backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);box-shadow:0 8px 32px rgba(0,0,0,0.3);transition:all 0.4s cubic-bezier(0.16,1,0.3,1);}
.score-card:hover{transform:translateY(-4px);box-shadow:0 12px 40px rgba(0,0,0,0.5);}
.score-card-buy{background:linear-gradient(160deg,rgba(5,46,22,0.7),rgba(13,27,42,0.8));border:1px solid rgba(16,185,129,.3);}
.score-card-sell{background:linear-gradient(160deg,rgba(42,14,14,0.7),rgba(27,13,27,0.8));border:1px solid rgba(239,68,68,.3);}
.score-card-neutral{background:linear-gradient(160deg,rgba(26,22,8,0.7),rgba(27,26,13,0.8));border:1px solid rgba(245,158,11,.3);}
.cs-card{border-radius:12px;padding:12px 16px;margin:6px 0;border-left:4px solid;background:rgba(255,255,255,0.02);backdrop-filter:blur(8px);transition:all .3s;}
.cs-card:hover{background:rgba(255,255,255,0.05);transform:translateX(2px);}
.reason-card{background:rgba(0,0,0,.2);border:1px solid rgba(255,255,255,0.05);border-radius:12px;padding:14px 18px;margin-top:14px;text-align:left;backdrop-filter:blur(8px);}
div[data-baseweb="select"]>div{background-color:rgba(18,22,31,0.6)!important;backdrop-filter:blur(10px);border-color:#2A3040!important;color:#E8ECF1!important;border-radius:10px!important;transition:all .3s;}
div[data-baseweb="select"]>div:hover{border-color:#6366F1!important;}
div[data-baseweb="popover"] ul{background-color:rgba(18,22,31,0.9)!important;backdrop-filter:blur(16px)!important;border:1px solid #2A3040!important;border-radius:12px!important;box-shadow:0 8px 32px rgba(0,0,0,0.5)!important;}
div[data-baseweb="popover"] li{color:#CBD5E1!important;}
div[data-baseweb="popover"] li:hover{background-color:rgba(99,102,241,0.2)!important;color:#fff!important;}
div[data-testid="stRadio"] label p{color:#CBD5E1!important;font-weight:600;}
div[data-testid="stTextInput"] input{background-color:rgba(18,22,31,0.6)!important;backdrop-filter:blur(10px);border-color:#2A3040!important;color:#E8ECF1!important;border-radius:10px!important;transition:all .3s;}
div[data-testid="stTextInput"] input:focus{border-color:#6366F1!important;box-shadow:0 0 0 2px rgba(99,102,241,0.2)!important;}
div[data-testid="stTabs"] button{color:#64748B!important;font-weight:700!important;border-bottom:3px solid transparent!important;transition:all .3s ease;}
div[data-testid="stTabs"] button[aria-selected="true"]{color:#A5B4FC!important;border-bottom-color:#6366F1!important;}
div[data-testid="stTabs"] button:hover{color:#CBD5E1!important;}
section[data-testid="stSidebar"]{background:rgba(8,10,16,0.85);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);border-right:1px solid rgba(255,255,255,0.05);}
header{background-color:transparent!important;}
div[data-testid="stMetricValue"]{color:#F8FAFC!important;font-weight:800!important;letter-spacing:-0.5px;}
div[data-testid="stMetricDelta"]{font-weight:700!important;}
::-webkit-scrollbar{width:6px;height:6px;} ::-webkit-scrollbar-track{background:rgba(0,0,0,0.2);} ::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.1);border-radius:3px;} ::-webkit-scrollbar-thumb:hover{background:rgba(255,255,255,0.2);}
.glass-metric{background:rgba(15,19,32,.55);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);border:1px solid rgba(255,255,255,.06);border-radius:14px;padding:16px 18px;text-align:center;transition:all .35s cubic-bezier(.16,1,.3,1);position:relative;overflow:hidden;}
.glass-metric:hover{border-color:rgba(99,102,241,.25);transform:translateY(-3px);box-shadow:0 8px 28px rgba(0,0,0,.35);}
.glass-metric .gm-label{color:#64748B;font-size:.72rem;font-weight:700;letter-spacing:.8px;text-transform:uppercase;margin:0 0 6px;}
.glass-metric .gm-value{font-size:1.65rem;font-weight:800;margin:0;letter-spacing:-1px;line-height:1.2;}
.glass-metric .gm-sub{color:#94A3B8;font-size:.72rem;font-weight:600;margin:4px 0 0;}
.glass-metric .gm-bar{height:4px;background:rgba(255,255,255,.06);border-radius:3px;margin-top:10px;overflow:hidden;}
.glass-metric .gm-bar-fill{height:4px;border-radius:3px;transition:width .6s cubic-bezier(.16,1,.3,1);}
.conf-ring{position:relative;width:90px;height:90px;margin:0 auto;}
.conf-ring svg{transform:rotate(-90deg);width:90px;height:90px;}
.conf-ring .ring-bg{fill:none;stroke:rgba(255,255,255,.06);stroke-width:6;}
.conf-ring .ring-fg{fill:none;stroke-width:6;stroke-linecap:round;transition:stroke-dashoffset .8s cubic-bezier(.16,1,.3,1);}
.conf-ring .ring-text{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);font-weight:800;font-size:1.1rem;}
.cm-card{background:rgba(15,19,32,.5);backdrop-filter:blur(12px);border:1px solid rgba(255,255,255,.05);border-radius:12px;padding:14px;text-align:center;transition:all .3s;}
.cm-card:hover{border-color:rgba(99,102,241,.2);transform:translateY(-2px);}
.cm-card .cm-name{color:#94A3B8;font-size:.72rem;font-weight:700;letter-spacing:.5px;margin:0 0 6px;}
.cm-card .cm-score{font-size:1.35rem;font-weight:800;margin:0;letter-spacing:-.5px;}
.cm-card .cm-vote{display:inline-block;padding:2px 8px;border-radius:6px;font-size:.68rem;font-weight:700;margin-top:6px;}
.cm-card .cm-mini-bar{height:4px;background:rgba(255,255,255,.06);border-radius:2px;margin-top:8px;overflow:hidden}
.cm-card .cm-mini-fill{height:4px;border-radius:2px;}
.dual-layer{display:flex;align-items:center;padding:5px 0;border-bottom:1px solid rgba(255,255,255,.03);transition:all .2s;}
.dual-layer:hover{background:rgba(255,255,255,.02);}
.dual-layer .dl-name{color:#94A3B8;font-size:.76rem;width:72px;text-align:center;font-weight:600;flex-shrink:0;}
.dual-layer .dl-bar-wrap{flex:1;height:8px;background:rgba(0,0,0,.25);border-radius:4px;overflow:hidden;position:relative;box-shadow:inset 0 1px 3px rgba(0,0,0,.4);}
.dual-layer .dl-fill-b{position:absolute;right:50%;height:8px;background:linear-gradient(270deg,#059669,#34D399);border-radius:4px 0 0 4px;transition:width .5s;}
.dual-layer .dl-fill-s{position:absolute;left:50%;height:8px;background:linear-gradient(90deg,#DC2626,#F87171);border-radius:0 4px 4px 0;transition:width .5s;}
.dual-layer .dl-center{position:absolute;left:50%;top:0;width:1px;height:8px;background:rgba(255,255,255,.15);}
.dual-layer .dl-val{font-size:.72rem;font-weight:700;width:42px;text-align:center;flex-shrink:0;}
.stat-mini{background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.05);border-radius:10px;padding:10px 12px;text-align:center;transition:all .25s;}
.stat-mini:hover{border-color:rgba(99,102,241,.15);}
.stat-mini .sm-label{color:#64748B;font-size:.65rem;font-weight:700;margin:0;letter-spacing:.4px;}
.stat-mini .sm-value{font-size:1rem;font-weight:800;margin:2px 0 0;letter-spacing:-.3px;}
.tow-bar{height:10px;background:rgba(0,0,0,.3);border-radius:5px;position:relative;overflow:hidden;margin:6px 0;box-shadow:inset 0 1px 3px rgba(0,0,0,.5);}
.tow-bar .tow-buy{position:absolute;right:50%;height:10px;background:linear-gradient(270deg,#065F46,#34D399);border-radius:5px 0 0 5px;}
.tow-bar .tow-sell{position:absolute;left:50%;height:10px;background:linear-gradient(90deg,#7F1D1D,#F87171);border-radius:0 5px 5px 0;}
.tow-bar .tow-center{position:absolute;left:50%;top:-1px;width:2px;height:12px;background:#fff;border-radius:1px;transform:translateX(-1px);z-index:1;}
.vote-dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin:0 2px;box-shadow:0 0 6px rgba(0,0,0,.3);}
.vote-dot.buy{background:#34D399;box-shadow:0 0 8px rgba(52,211,153,.4);}
.vote-dot.sell{background:#F87171;box-shadow:0 0 8px rgba(248,113,113,.4);}
.vote-dot.neutral{background:#475569;}
.vote-dot.abstain{background:#1E293B;border:1px solid #334155;}
@media(max-width:768px){
  .block-container{padding-top:.5rem!important}
  .price-header{padding:14px 16px;border-radius:12px}
  .price-big{font-size:1.6rem!important}
  .ind-mini{padding:3px 7px;font-size:.68rem}
  .glass-metric{padding:12px 14px;border-radius:12px}
  .glass-metric .gm-value{font-size:1.3rem}
  .glass-metric .gm-label{font-size:.65rem}
  .cm-card{padding:10px}
  .cm-card .cm-score{font-size:1.1rem}
  .cm-card .cm-name{font-size:.65rem}
  .dual-layer .dl-name{width:56px;font-size:.68rem}
  .dual-layer .dl-val{width:34px;font-size:.65rem}
  .stat-mini{padding:8px 10px}
  .stat-mini .sm-value{font-size:.88rem}
  .score-card{padding:16px;border-radius:12px}
  .conf-ring{width:70px;height:70px}
  .conf-ring svg{width:70px;height:70px}
  .conf-ring .ring-text{font-size:.9rem}
  div[style*="grid-template-columns:repeat(4"]{grid-template-columns:repeat(2,1fr)!important}
  div[style*="grid-template-columns:repeat(5"]{grid-template-columns:repeat(2,1fr)!important}
  div[style*="grid-template-columns:repeat(6"]{grid-template-columns:repeat(3,1fr)!important}
  div[style*="grid-template-columns:1fr 1fr"]{grid-template-columns:1fr!important}
}
@media(max-width:480px){
  .price-big{font-size:1.3rem!important}
  .glass-metric .gm-value{font-size:1.1rem}
  .dual-layer .dl-name{width:48px;font-size:.62rem}
  .dual-layer .dl-val{width:30px;font-size:.6rem}
  .cm-card .cm-score{font-size:.95rem}
  .conf-ring{width:60px;height:60px}
  .conf-ring svg{width:60px;height:60px}
  .conf-ring .ring-text{font-size:.8rem}
  div[style*="grid-template-columns:repeat(4"]{grid-template-columns:1fr!important}
  div[style*="grid-template-columns:repeat(5"]{grid-template-columns:repeat(2,1fr)!important}
  div[style*="grid-template-columns:repeat(6"]{grid-template-columns:repeat(2,1fr)!important}
}
</style>""", unsafe_allow_html=True)

# ━━━ Constants ━━━

@st.cache_resource
def get_gemini_model():
    if GEMINI_API_KEY: genai.configure(api_key=GEMINI_API_KEY)
    return genai.GenerativeModel('gemini-2.5-flash')

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
    st.markdown("#### 📂 기능 / 섹터 선택"); sector_names=list(SECTOR_GROUPS.keys()); selected_sector=st.session_state.get('selected_sector',None)
    
    all_tickers = []
    for v in SECTOR_GROUPS.values(): all_tickers.extend(v)
    all_tickers = list(set(all_tickers))
    if st.button(f"🌐 전체 종목 ALL\n({len(all_tickers)})", use_container_width=True, type="primary" if selected_sector=="ALL" else "secondary"):
        st.session_state['selected_sector']="ALL"
        st.session_state['scan_tickers_override']=all_tickers
        st.rerun()

    for rs in range(0,len(sector_names),3):
        ri=sector_names[rs:rs+3];cols=st.columns(3)
        for i,sn in enumerate(ri):
            with cols[i]:
                if st.button(f"{sn}\n({len(SECTOR_GROUPS[sn])})",key=f"sec_{rs+i}",use_container_width=True,type="primary" if selected_sector==sn else "secondary"):st.session_state['selected_sector']=sn;st.session_state['scan_tickers_override']=SECTOR_GROUPS[sn];st.rerun()

    if selected_sector:
        tkrs = st.session_state.get('scan_tickers_override', [])
        slen = len(tkrs)
        preview = ", ".join(tkrs)
        st.markdown(f"<div style='background:rgba(99,102,241,.08);border:1px solid #6366F133;border-radius:10px;padding:12px 14px;margin:8px 0'><div style='margin-bottom:6px;'><span style='color:#A5B4FC;font-weight:700'>{selected_sector}</span><span style='color:#64748B;margin-left:8px'>{slen}종목</span></div><div style='color:#94A3B8;font-size:0.8rem;line-height:1.4;'>{preview}</div></div>",unsafe_allow_html=True)
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
        
        # 1. Bulk Download (가장 큰 병목인 네트워크를 한 번에 해결)
        with st.spinner(f"📡 {len(tickers)}개 종목 데이터 일괄 다운로드 중 (초고속)..."):
            # yfinance는 리스트 형식을 지원하고, 내부적으로 multithreading을 돌립니다.
            bulk_data = yf.download(tickers, period="2y", group_by='ticker', threads=True, progress=False)
            
        def _so_bulk(t):
            try:
                # 2. Extract specific ticker data from bulk
                if isinstance(bulk_data.columns, pd.MultiIndex):
                    if t not in bulk_data.columns.levels[0]: return None
                    df = bulk_data[t].copy()
                else: 
                    df = bulk_data.copy()
                
                df.dropna(how='all', inplace=True)
                if df.empty or len(df) < 50: return None
                
                # 3. 계산 (네트워크 통신 없이 순수 CPU 연산만)
                from engine import detect_all_signals
                from indicators import compute_indicators
                df_ = detect_all_signals(compute_indicators(df))
                if df_ is None or df_.empty: return None
                
                # ⚡ 최근 1주일(5 영업일)치 캔들만 스캔 출력
                dc_=df_.tail(5);acs=[];lsd=None
                
                scan_targets = {**COMBINED_SCAN_REGISTRY}
                scan_targets['System_Turn_Bull'] = {'icon':'🟢 ', 'kor':'전면매수전환', 'dir':'buy', 'tier':1}
                scan_targets['System_Turn_Bear'] = {'icon':'🔴 ', 'kor':'전면매도전환', 'dir':'sell', 'tier':1}
                
                for cn,ccfg in scan_targets.items():
                    if cn in dc_.columns and dc_[cn].any():
                        ld=dc_[cn][dc_[cn]].index[-1]
                        acs.append({'icon':ccfg['icon'],'kor':ccfg['kor'],'dir':ccfg['dir'],'tier':ccfg['tier'],'date':ld.strftime('%m/%d')})
                        lsd=ld if lsd is None or ld>lsd else lsd
                lt=dc_.iloc[-1];ch=_sf((lt['Close']-dc_.iloc[-2]['Close'])/dc_.iloc[-2]['Close']*100) if len(dc_)>=2 else 0
                return {'ticker':t,'price':_sf(lt['Close']),'chg':ch,'scans':sorted(acs,key=lambda x:x['tier']),'jg':str(lt.get('Trade_Judgment','N/A')),'cf':_sf(lt.get('Judgment_Confidence',0)),'es':_sf(lt.get('Ensemble_Score',0)),'ctx':CTX_KOR.get(int(_sf(lt.get('Market_Context',0))),'기본'),'ba':int(_sf(lt.get('Buy_Agree',0))),'sa':int(_sf(lt.get('Sell_Agree',0))),'latest_sig':lsd.strftime('%Y-%m-%d') if lsd else '9999-99-99','reason':str(lt.get('Judgment_Reason','')),'action':str(lt.get('Action_Label',''))}
            except Exception as e:
                # print(f"Bulk Err {t}: {e}")
                return None
                
        # 4. CPU 연산 분산 처리
        st_info = st.empty()
        with ThreadPoolExecutor(max_workers=min(32,len(tickers))) as ex:
            futs={ex.submit(_so_bulk,t):t for t in tickers}
            for idx_f,f in enumerate(as_completed(futs)):
                pb.progress((idx_f+1)/len(tickers))
                t_name = futs[f]
                st_info.markdown(f"<div style='color:#A5B4FC;font-size:0.9rem;text-align:center;margin-bottom:12px'>⏳ 스캔 중: <b>{t_name}</b> ({idx_f+1}/{len(tickers)})</div>", unsafe_allow_html=True)
                r=f.result()
                if r:results.append(r)
        pb.empty()
        st_info.empty()
        from datetime import datetime as dt_
        def _sk(x):
            has_macro_buy = any(s['kor'] == '전면매수전환' for s in x.get('scans', []))
            buy_count = sum(1 for s in x.get('scans', []) if s['dir'] == 'buy')
            jg_score = {'STRONG BUY':7, 'BUY':6, 'WATCH BUY':5, 'NEUTRAL':4, 'MIXED':3, 'WATCH SELL':2, 'SELL':1, 'STRONG SELL':0}.get(str(x.get('jg')).replace('_', ' ').upper(), -1)
            has_scans = 0 if x.get('scans') else 1
            latest_ts = -dt_.strptime(x['latest_sig'],'%Y-%m-%d').timestamp() if x.get('latest_sig')!='9999-99-99' else 0
            return (0 if has_macro_buy else 1, -buy_count, -jg_score, has_scans, latest_ts)
        results.sort(key=_sk)
        st.session_state['scan_results']=results;st.session_state['scan_source']=scan_source;st.session_state['scan_total']=len(tickers)
    results=st.session_state.get('scan_results',[])
    if results:
        if tickers and not scan_btn:
            f_set = set(tickers)
            results = [r for r in results if r['ticker'] in f_set]
            
        if not results:
            st.warning("선택한 섹터의 종목 중 최근 스캔 이력이 있는 데이터가 없습니다. 상단의 🚀스캔 버튼을 눌러 최신 데이터를 갱신해 주세요.")
        else:
            bt=[r for r in results if 'BUY' in r['jg']];st_=[r for r in results if 'SELL' in r['jg']]
            scan_total=len(tickers) if tickers else st.session_state.get('scan_total',0)
            st.markdown(f"<div style='display:flex;gap:12px;margin-bottom:12px'><div style='flex:1;background:rgba(0,230,118,.06);border:1px solid #10B98133;border-radius:10px;padding:10px;text-align:center'><span style='color:#34D399;font-weight:800;font-size:1.3rem'>{len(bt)}</span><span style='color:#64748B;font-size:.8rem'> 매수</span></div><div style='flex:1;background:rgba(255,23,68,.06);border:1px solid #EF444433;border-radius:10px;padding:10px;text-align:center'><span style='color:#F87171;font-weight:800;font-size:1.3rem'>{len(st_)}</span><span style='color:#64748B;font-size:.8rem'> 매도</span></div><div style='flex:1;background:rgba(99,102,241,.06);border:1px solid #6366F133;border-radius:10px;padding:10px;text-align:center'><span style='color:#A5B4FC;font-weight:800;font-size:1.3rem'>{len(results)}</span><span style='color:#64748B;font-size:.8rem'>/{scan_total}</span></div></div>",unsafe_allow_html=True)
            for r in results:
                chc='#34D399' if r['chg']>=0 else '#F87171';chi='▲' if r['chg']>=0 else '▼';jc='#34D399' if 'BUY' in r['jg'] else('#F87171' if 'SELL' in r['jg'] else '#FCD34D')
                sh="".join([f"<div style='display:flex;gap:6px;padding:2px 0'><span style='color:{'#34D399' if s['dir']=='buy' else '#F87171' if s['dir']=='sell' else '#FFC107'}'>{s.get('icon') or '■'}</span><span style='color:#E8ECF1;font-size:.82rem'>{s['kor']}</span><span style='color:#64748B;font-size:.7rem'>{s['date']}</span></div>" for s in r['scans']]) if r['scans'] else "<span style='color:#475569;font-size:.8rem'>—</span>"
                esc='#34D399' if r['es']>10 else('#F87171' if r['es']<-10 else '#FCD34D');bd='#1E293B' if r['scans'] else '#0F172A';op='1' if r['scans'] else '.6'
                rh=""
                if r.get('reason'):rc='#6EE7B7' if 'BUY' in r['jg'] else('#FCA5A5' if 'SELL' in r['jg'] else '#FCD34D');rh=f"<div style='padding:4px 0;border-top:1px solid rgba(255,255,255,.04);margin-top:4px'><span style='color:{rc};font-size:.78rem'>💬 {r['reason'][:80]}</span></div>"
                st.markdown(f"<div style='background:linear-gradient(160deg,#0F1320,#141926);border:1px solid {bd};border-radius:14px;padding:14px 18px;margin:6px 0;opacity:{op}'><div style='display:flex;justify-content:space-between;margin-bottom:8px'><span style='color:#A5B4FC;font-weight:800;font-size:1.15rem'>{r['ticker']}</span><div style='display:flex;align-items:center;gap:8px'><span style='color:{esc};font-size:.75rem;font-weight:700'>ES:{r['es']:+.0f}</span><span style='color:{jc};font-size:.8rem;font-weight:600'>{r['jg']}({r['cf']:.0f}%)</span><span style='color:{chc};font-size:.8rem'>{chi}{abs(r['chg']):.1f}%</span></div></div>{sh}{rh}</div>",unsafe_allow_html=True)
                if st.button(f"{r['ticker']} 분석",key=f"sc_{r['ticker']}",use_container_width=True):st.session_state['_mode']='분석';st.session_state['_auto']=r['ticker'];st.rerun()
else:
    st.markdown("<h2 style='text-align:center;color:#fff;margin-bottom:4px;letter-spacing:-0.5px;'>CipherX <span style='font-size:0.5em;color:#A5B4FC;background:rgba(165,180,252,0.1);border:1px solid rgba(165,180,252,0.3);padding:2px 8px;border-radius:12px;vertical-align:middle;'>V14.2</span></h2>",unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;color:#64748B;margin-bottom:16px'>5-Committee Ensemble + Prediction + Auto Reason</p>",unsafe_allow_html=True)
    if not st.session_state.last_ticker:
        cols=st.columns(4)
        for i,t in enumerate(["NVDA","TSLA","AAPL","QQQ"]):
            with cols[i]:
                if st.button(t,use_container_width=True):st.session_state['quick']=t
    for i,msg in enumerate(st.session_state.messages):
        av="assistant" if msg["role"]=="assistant" else "user"
        with st.chat_message(msg["role"],avatar=av):
            if msg.get("type")=="analysis":st.markdown(msg.get("content",""),unsafe_allow_html=True);render_analysis(msg)
            elif msg.get("type")=="report":
                with st.expander(f"{msg.get('ticker','')} AI Report",expanded=True):st.markdown(msg["content"])
                st.download_button("Download Report",key=f"dl_{i}",data=msg["content"].encode('utf-8'),file_name=f"{msg.get('ticker','')}_V142_{datetime.now().strftime('%Y%m%d')}.md",mime="text/markdown",use_container_width=True)
            else:st.markdown(msg.get("content",""))
            if msg.get("prompt") and msg.get("type")=="analysis":
                with st.expander("프롬프트"):st.code(msg["prompt"],language="markdown");st_copy_to_clipboard(msg["prompt"],before_copy_label="📋",after_copy_label="✅")
    def _run_ai():
        tp=st.session_state.pending_ai_ticker;pp=st.session_state.pending_ai_prompt
        with st.chat_message("assistant",avatar="assistant"):
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
                content=""
                st.session_state.messages.append({"role":"assistant","type":"analysis","ticker":tv,"content":content,"fig_json":fj,"meta":meta,"prompt":prompt})
                st.session_state.pending_ai_ticker=tv;st.session_state.pending_ai_prompt=prompt;st.rerun()
            else:st.session_state.messages.append({"role":"assistant","type":"text","content":f"⚠️ **{tv}** 실패:{phist}"});st.rerun()
    if st.session_state.get('_auto'):process_ticker(st.session_state.pop('_auto'))
    if st.session_state.get('quick'):process_ticker(st.session_state.pop('quick'))
    if st.session_state.pending_ai_ticker and st.session_state.pending_ai_prompt:
        if st.button(f"🚀 {st.session_state.pending_ai_ticker.upper()} AI분석",type="primary",use_container_width=True):_run_ai()
    if ti:=st.chat_input("티커 입력 (예: TSLA, AAPL, QQQ)"):process_ticker(ti)
