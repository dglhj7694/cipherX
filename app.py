# ══════════════════════════════════════════════════════════════
#  CipherX V14.2 — PART 1/4
#  설정, 레지스트리, 유틸리티, 기술지표
# ══════════════════════════════════════════════════════════════

import streamlit as st, google.generativeai as genai
import time, re, math, json
from datetime import datetime
from st_copy_to_clipboard import st_copy_to_clipboard
from concurrent.futures import ThreadPoolExecutor, as_completed
from sectors import SECTOR_GROUPS
from config import GEMINI_API_KEY, COMBINED_SCAN_REGISTRY, CTX_KOR
from utils import _valid_fmt, _sf, fetch_fundamentals, validate_ticker, compute_and_cache, _compute_cached
from chart import build_chart, build_metadata
from ui import render_analysis
from ai_agent import build_prompt_text, build_ai_prompt
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
.fade-up{animation:fadeUp .35s ease both}
@keyframes fadeUp{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
.conf-ring{position:relative;width:80px;height:80px;display:inline-block}
.conf-ring svg{width:80px;height:80px;transform:rotate(-90deg)}
.ring-bg{fill:none;stroke:rgba(148,163,184,.2);stroke-width:8}
.ring-fg{fill:none;stroke-width:8;stroke-linecap:round}
.ring-text{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:.92rem;font-weight:800}
.vote-dot{width:8px;height:8px;border-radius:999px;display:inline-block}
.vote-dot.buy{background:#34D399;box-shadow:0 0 7px rgba(52,211,153,.65)}
.vote-dot.sell{background:#F87171;box-shadow:0 0 7px rgba(248,113,113,.65)}
.vote-dot.neutral{background:#FF9800;box-shadow:0 0 7px rgba(255,152,0,.55)}
.vote-dot.abstain{background:#64748B}
.cm-card{background:rgba(255,255,255,.03);border:1px solid rgba(148,163,184,.12);border-radius:10px;padding:10px}
.cm-name{color:#94A3B8;font-size:.7rem;font-weight:700;margin:0 0 4px}
.cm-score{font-size:1.15rem;font-weight:800;margin:0 0 6px}
.cm-vote{display:inline-block;padding:2px 8px;border-radius:999px;font-size:.65rem;font-weight:700}
.cm-mini-bar{height:4px;background:rgba(148,163,184,.18);border-radius:999px;overflow:hidden;margin-top:6px}
.cm-mini-fill{height:100%;border-radius:999px}
.tow-bar{position:relative;height:14px;border-radius:999px;background:rgba(148,163,184,.15);overflow:hidden}
.tow-buy{position:absolute;right:50%;top:0;bottom:0;background:linear-gradient(90deg,#065F46,#34D399)}
.tow-sell{position:absolute;left:50%;top:0;bottom:0;background:linear-gradient(90deg,#F87171,#7F1D1D)}
.tow-center{position:absolute;left:50%;top:0;bottom:0;width:1px;background:rgba(226,232,240,.55)}
.stat-mini{background:rgba(255,255,255,.03);border:1px solid #1E293B;border-radius:10px;padding:10px 8px;text-align:center}
.sm-label{color:#64748B;font-size:.66rem;font-weight:700;margin:0 0 4px}
.sm-value{color:#E2E8F0;font-size:1rem;font-weight:800;margin:0}
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
@st.cache_resource
def get_gemini_model():
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
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
    all_universe=sorted({str(t).strip().upper() for ts in SECTOR_GROUPS.values() for t in ts if str(t).strip()})
    st.markdown("#### 📂 섹터 선택");sector_names=list(SECTOR_GROUPS.keys());selected_sector=st.session_state.get('selected_sector',None)
    for rs in range(0,len(sector_names),3):
        ri=sector_names[rs:rs+3];cols=st.columns(3)
        for i,sn in enumerate(ri):
            with cols[i]:
                if st.button(f"{sn}\n({len(SECTOR_GROUPS[sn])})",key=f"sec_{rs+i}",use_container_width=True,type="primary" if selected_sector==sn else "secondary"):st.session_state['selected_sector']=sn;st.session_state['scan_tickers_override']=SECTOR_GROUPS[sn];st.rerun()
    if st.button(f"🌐 전체종목\n({len(all_universe)})",key="sec_all",use_container_width=True,type="primary" if selected_sector=='🌐 전체' else "secondary"):st.session_state['selected_sector']='🌐 전체';st.session_state['scan_tickers_override']=all_universe;st.rerun()
    if selected_sector:
        sel_list=st.session_state.get('scan_tickers_override',[]) if selected_sector=='🌐 전체' else SECTOR_GROUPS.get(selected_sector,[])
        sel_list=list(dict.fromkeys([str(t).strip().upper() for t in sel_list if str(t).strip()]))
        sel_cnt=len(sel_list)
        st.markdown(f"<div style='background:rgba(99,102,241,.08);border:1px solid #6366F133;border-radius:10px;padding:10px 14px;margin:8px 0'><span style='color:#A5B4FC;font-weight:700'>{selected_sector}</span><span style='color:#64748B;margin-left:8px'>{sel_cnt}종목</span><span style='color:#64748B;margin-left:8px'>· 점수 높은 순 정렬</span></div>",unsafe_allow_html=True)
        if sel_list:
            chips="".join([f"<span style='display:inline-block;margin:3px 4px 0 0;padding:3px 8px;border-radius:999px;background:rgba(30,41,59,.8);border:1px solid #334155;color:#CBD5E1;font-size:.76rem;font-weight:600'>{t}</span>" for t in sel_list])
            st.markdown(f"<div style='background:rgba(15,23,42,.55);border:1px solid #1E293B;border-radius:10px;padding:10px 12px;margin:6px 0 10px'><p style='margin:0 0 6px;color:#94A3B8;font-size:.74rem;font-weight:700'>선택 종목 목록</p><div style='max-height:110px;overflow:auto'>{chips}</div></div>",unsafe_allow_html=True)
    st.markdown("#### ✏️ 직접 입력");ci=st.text_input("티커",placeholder="NVDA,TSLA...",key="scan_in")
    if ci and ci.strip():tickers=[t.strip().upper() for t in ci.split(',') if t.strip()];scan_source="직접"
    elif st.session_state.get('scan_tickers_override'):tickers=st.session_state['scan_tickers_override'];scan_source=selected_sector or "섹터"
    else:tickers=[];scan_source="직접"
    tickers=list(dict.fromkeys([t for t in tickers if t]))
    cb1,cb2=st.columns([3,1])
    with cb1:scan_btn=st.button(f"🚀 스캔({len(tickers)})",type="primary",use_container_width=True)
    with cb2:
        if st.button("🗑️",use_container_width=True,key="sr"):st.session_state.pop('selected_sector',None);st.session_state.pop('scan_tickers_override',None);st.session_state['scan_results']=[];st.rerun()
    if scan_btn and tickers:
        pb=st.progress(0);results=[];sts=math.floor(time.time()/300)
        try:
            from engine import _ensure_runtime_combo_registry
            _ensure_runtime_combo_registry()
        except Exception:
            pass
        trans_cfg={
            'UTBot_Buy':{'label':'UTBot 전환▲','icon':'🟢','dir':'buy'},
            'UTBot_Sell':{'label':'UTBot 전환▼','icon':'🔴','dir':'sell'},
            'Hull_Turn_Bull':{'label':'HULL 전환▲','icon':'🟢','dir':'buy'},
            'Hull_Turn_Bear':{'label':'HULL 전환▼','icon':'🔴','dir':'sell'},
        }
        multi_cols=['UTBot_Buy','UTBot_Sell','Hull_Turn_Bull','Hull_Turn_Bear','MACD_Cross_Buy','MACD_Cross_Sell','StochRSI_Cross_Buy','StochRSI_Cross_Sell','Squeeze_Mom_Cross_Up','Squeeze_Mom_Cross_Down']
        def _so(t):
            try:
                df_=_compute_cached(t,f"{t}_{sts}")
                if df_ is None or len(df_)<50:return None
                dc_=df_.tail(63);acs=[];lsd=None;trs=[]
                for cn,ccfg in COMBINED_SCAN_REGISTRY.items():
                    if cn in dc_.columns and dc_[cn].tail(5).any():ld=dc_[cn].tail(5)[dc_[cn].tail(5)].index[-1];acs.append({'icon':ccfg['icon'],'kor':ccfg['kor'],'dir':ccfg['dir'],'tier':ccfg['tier'],'date':ld.strftime('%m/%d')});lsd=ld if lsd is None or ld>lsd else lsd
                for sn,cfg in trans_cfg.items():
                    if sn in dc_.columns and dc_[sn].tail(5).any():td=dc_[sn].tail(5)[dc_[sn].tail(5)].index[-1];trs.append({'icon':cfg['icon'],'label':cfg['label'],'dir':cfg['dir'],'date':td.strftime('%m/%d')})
                lt=dc_.iloc[-1];ch=_sf((lt['Close']-dc_.iloc[-2]['Close'])/dc_.iloc[-2]['Close']*100) if len(dc_)>=2 else 0
                bt=_sf(lt.get('Buy_Total',0));stt=_sf(lt.get('Sell_Total',0));ba=int(_sf(lt.get('Buy_Agree',0)));sa=int(_sf(lt.get('Sell_Agree',0)))
                t1b=sum(1 for s in acs if s['tier']==1 and s['dir']=='buy');t1s=sum(1 for s in acs if s['tier']==1 and s['dir']=='sell')
                t2b=sum(1 for s in acs if s['tier']==2 and s['dir']=='buy');t2s=sum(1 for s in acs if s['tier']==2 and s['dir']=='sell')
                es=_sf(lt.get('Ensemble_Score',0));cf=_sf(lt.get('Judgment_Confidence',0))
                scan_score=es+((bt-stt)*0.55)+((ba-sa)*2.5)+(t1b*4.0)-(t1s*4.0)+(t2b*1.6)-(t2s*1.6)+(cf*0.04)
                strength=abs(es)+((bt+stt)*0.35)+(abs(ba-sa)*1.8)+((t1b+t1s)*3.0)+(cf*0.02)
                mcnt=sum(1 for c in multi_cols if c in dc_.columns and dc_[c].tail(3).any());mflag=(mcnt>=3) or ((t1b+t1s)>=1 and mcnt>=2)
                return {'ticker':t,'price':_sf(lt['Close']),'chg':ch,'scans':sorted(acs,key=lambda x:x['tier']),'transitions':trs,'multi_sig':bool(mflag),'multi_cnt':int(mcnt),'jg':str(lt.get('Trade_Judgment','N/A')),'cf':cf,'es':es,'ctx':CTX_KOR.get(int(_sf(lt.get('Market_Context',0))),'기본'),'ba':ba,'sa':sa,'buy_total':bt,'sell_total':stt,'scan_score':_sf(scan_score),'strength':_sf(strength),'latest_sig':lsd.strftime('%Y-%m-%d') if lsd else '9999-99-99','latest_sig_ts':lsd.timestamp() if lsd else 0.0,'reason':str(lt.get('Judgment_Reason','')),'action':str(lt.get('Action_Label',''))}
            except:return None
        with ThreadPoolExecutor(max_workers=min(16,max(4,len(tickers)//8),len(tickers))) as ex:
            futs={ex.submit(_so,t):t for t in tickers}
            for idx_f,f in enumerate(as_completed(futs)):
                pb.progress((idx_f+1)/len(tickers))
                r=f.result()
                if r:results.append(r)
        pb.empty()
        results.sort(key=lambda x:(-x['scan_score'],-x['strength'],-x['latest_sig_ts'],x['ticker']))
        st.session_state['scan_results']=results;st.session_state['scan_source']=scan_source;st.session_state['scan_total']=len(tickers)
    results=st.session_state.get('scan_results',[])
    if results:
        bt=[r for r in results if 'BUY' in r['jg']];st_=[r for r in results if 'SELL' in r['jg']]
        scan_total=st.session_state.get('scan_total',0)  # ★ 미리 추출
        st.markdown(f"<div style='display:flex;gap:12px;margin-bottom:12px'><div style='flex:1;background:rgba(0,230,118,.06);border:1px solid #10B98133;border-radius:10px;padding:10px;text-align:center'><span style='color:#34D399;font-weight:800;font-size:1.3rem'>{len(bt)}</span><span style='color:#64748B;font-size:.8rem'> 매수</span></div><div style='flex:1;background:rgba(255,23,68,.06);border:1px solid #EF444433;border-radius:10px;padding:10px;text-align:center'><span style='color:#F87171;font-weight:800;font-size:1.3rem'>{len(st_)}</span><span style='color:#64748B;font-size:.8rem'> 매도</span></div><div style='flex:1;background:rgba(99,102,241,.06);border:1px solid #6366F133;border-radius:10px;padding:10px;text-align:center'><span style='color:#A5B4FC;font-weight:800;font-size:1.3rem'>{len(results)}</span><span style='color:#64748B;font-size:.8rem'>/{scan_total}</span></div></div>",unsafe_allow_html=True)
        for rk,r in enumerate(results,start=1):
            chc='#34D399' if r['chg']>=0 else '#F87171';chi='▲' if r['chg']>=0 else '▼';jc='#34D399' if 'BUY' in r['jg'] else('#F87171' if 'SELL' in r['jg'] else '#FCD34D')
            sh="".join([f"<div style='display:flex;gap:6px;padding:2px 0'><span style='color:{'#34D399' if s['dir']=='buy' else '#F87171' if s['dir']=='sell' else '#FFC107'}'>●</span><span style='color:#E8ECF1;font-size:.82rem'>{s['icon']}{s['kor']}</span><span style='color:#64748B;font-size:.7rem'>{s['date']}</span></div>" for s in r['scans']]) if r['scans'] else "<span style='color:#475569;font-size:.8rem'>—</span>"
            th="".join([f"<span style='display:inline-flex;align-items:center;gap:4px;padding:2px 8px;border-radius:999px;background:rgba({ '52,211,153' if t['dir']=='buy' else '248,113,113' },.12);color:{'#34D399' if t['dir']=='buy' else '#F87171'};font-size:.72rem;font-weight:700;margin-right:6px'>{t['icon']} {t['label']} {t['date']}</span>" for t in r.get('transitions',[])]) if r.get('transitions') else "<span style='color:#475569;font-size:.78rem'>UT/HULL 전환 없음</span>"
            mh=f"<div style='margin:6px 0 2px'><span style='display:inline-block;padding:2px 8px;border-radius:999px;background:rgba({ '52,211,153' if r.get('multi_sig') else '148,163,184' },.16);color:{'#34D399' if r.get('multi_sig') else '#94A3B8'};font-size:.72rem;font-weight:700'>MULTI-SIGNAL {'ON' if r.get('multi_sig') else 'OFF'} ({r.get('multi_cnt',0)})</span></div>"
            esc='#34D399' if r['es']>10 else('#F87171' if r['es']<-10 else '#FCD34D');bd='#1E293B' if r['scans'] else '#0F172A';op='1' if r['scans'] else '.6';sc='#34D399' if r['scan_score']>0 else('#F87171' if r['scan_score']<0 else '#FCD34D')
            rh=""
            if r.get('reason'):rc='#6EE7B7' if 'BUY' in r['jg'] else('#FCA5A5' if 'SELL' in r['jg'] else '#FCD34D');rh=f"<div style='padding:4px 0;border-top:1px solid rgba(255,255,255,.04);margin-top:4px'><span style='color:{rc};font-size:.78rem'>💬 {r['reason'][:80]}</span></div>"
            st.markdown(f"<div style='background:linear-gradient(160deg,#0F1320,#141926);border:1px solid {bd};border-radius:14px;padding:14px 18px;margin:6px 0;opacity:{op}'><div style='display:flex;justify-content:space-between;margin-bottom:8px'><span style='color:#A5B4FC;font-weight:800;font-size:1.15rem'>#{rk} {r['ticker']}</span><div style='display:flex;align-items:center;gap:8px'><span style='color:{sc};font-size:.75rem;font-weight:700'>SCAN:{r['scan_score']:+.1f}</span><span style='color:{esc};font-size:.75rem;font-weight:700'>ES:{r['es']:+.0f}</span><span style='color:{jc};font-size:.8rem;font-weight:600'>{r['jg']}({r['cf']:.0f}%)</span><span style='color:{chc};font-size:.8rem'>{chi}{abs(r['chg']):.1f}%</span></div></div><div style='margin:4px 0 8px'>{th}</div>{mh}{sh}{rh}</div>",unsafe_allow_html=True)
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
            if msg.get("type")=="analysis":render_analysis(msg)
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
