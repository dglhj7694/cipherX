import google.generativeai as genai
import streamlit as st
from config import *
from utils import _cs_str

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
