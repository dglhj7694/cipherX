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
데이터(Block A~D)의 "판단 이유"와 컨텍스트를 반드시 검증하고 반영하세요.

━━━ Rules ━━━
1. 제공된 데이터 독자 분석 → 시스템 판단 대조
2. 가격변동(A), 거래량 수급 변화, 심리적 지지/저항(B), 시스템 시그널(C, D)를 융합하여 분석
3. 스마트 머니(OBV, CMF, Volume 등) 흐름 파악 및 해석 추가
4. 확률적인 예상 시나리오와 주요 가격 레벨(VP/MA/ATR 등 활용) 제시
5. 옵션/공매도 등 데이터가 불충분할 경우 기술적 흐름을 통해 추론
6. 불필요한 서론 금지, 투자 피드백 위주의 실전형 출력

━━━ Data ━━━
[{ticker}]
{phist}
[펀더멘탈] {fund}

━━━ Output ━━━

### **1. 내용 요약 및 시장 심리**
[이날의 시장 상황과 주가 흐름을 3~4문장으로 요약. 심리적 저항선/지지선 테스트 여부 포함]

---

### **2. 위원회 교차 검증 및 판단**
* **시스템 검증**: 컨텍스트 / 소수의견 / 시너지 / Veto / 시스템 맹점 분석
* ★ **판단 이유 검증**: 시스템의 "판단이유"에 동의하는가? 반박한다면 근거는?

---

### **3. 주가/거래량 및 핵심 시그널**
* **거래량 (스마트 머니)**: 평균 대비 **[0.0배]** 수준. (단순 증량뿐 아니라 스마트머니 유입/이탈 여부 분석)
* **주요 시그널 상태**: WT/VuManChu/UTBot/Hull 기반 과매수/과매도 및 추세 강도 해석
* **추가 지표**: [식별된 기술적 패턴 이름 (예: NR7 등)] 상태 및 향후 영향

---

### **4. 지지선 및 저항선**
* **저항선**: **[가격1]** (설명), **[가격2]**
* **지지선**: **[가격1]** (설명), **[가격2]**
[현재 주가가 어느 위치에 있는지, 단기적으로 어느 선을 뚫어야 하는지 설명]

---

### **5. 수급 현황 (콜/풋옵션 및 공매도)**
* **콜/풋옵션 현황**: [감마(Gamma) 및 포지션 비중을 통해 주가를 변동시킬 에너지가 얼마나 축적되었는가?]
* **공매도 현황**: [숏 커버링 확률, 혹은 하방 공격 압력 분석]
*(데이터가 부족할 경우 기술적 흐름을 바탕으로 시장의 베팅 방향 추론)*

---

### **6. 주가변동이유 및 이벤트**
1. [이유 1: 매크로, 뉴스, 섹터 이슈 등]
2. [이유 2]

---

### **7. 종합해석 및 전망 (확률 시나리오)**
**현재 상황 평가**: [주가 위치와 모멘텀에 대한 냉철한 평가]

**전망 (시나리오)**
* 🔵 **긍정적(Bullish) 시나리오 (__%)**: [조건] 충족 시 [목표가]까지 상승 예상
* 🟠 **베이스 시나리오 (__%)**: [가장 확률 높은 전개]
* 🔴 **리스크(Bearish) 시나리오 (__%)**: [조건] 이탈 시 [목표가]까지 하락 예상

**핵심 전략 포인트** (*[구체적 조건] 제시 포함*)
* **진입(Entry)**: 공격적 매수 [가격대] / 보수적 진입 [확인 매매 가격대]
* **손절(Stop-loss)**: [필수 준수 가격] (이 가격 붕괴 시 예측 시나리오 폐기)

---

### **결론**
[전체 분석을 2문장으로 요약하며 무조건 GRADE(A~F) 표시]

### **앞으로의 주가 예측 (다음 거래일)**
**예상**: **[상승/하락/보합]**
* **근거**: [기술적/심리적 근거를 바탕으로 다음 거래일의 구체적 움직임 예측]

**[결론]**: 한 줄로 요약하는 이번 주 투자 핵심 가이드.
"""
