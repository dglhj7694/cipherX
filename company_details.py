import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# ─────────────────────────────────────────
# 🛠️ 유틸리티 및 계산 함수
# ─────────────────────────────────────────
def _fmt_num(num, is_currency=True):
    if pd.isna(num) or num is None: return "N/A"
    prefix = "$" if is_currency else ""
    if num >= 1e12: return f"{prefix}{num/1e12:.2f}T (조)"
    elif num >= 1e9: return f"{prefix}{num/1e9:.2f}B (십억)"
    elif num >= 1e6: return f"{prefix}{num/1e6:.2f}M (백만)"
    return f"{prefix}{num:,.0f}"

def _fmt_pct(num):
    if pd.isna(num) or num is None: return "N/A"
    return f"{num * 100:.2f}%"

def _calc_cagr(financials, row_name):
    """최근 재무 데이터를 바탕으로 연평균 성장률(CAGR) 계산"""
    try:
        if row_name in financials.index:
            data = financials.loc[row_name].dropna()
            if len(data) >= 2:
                start_val, end_val = data.iloc[-1], data.iloc[0]
                if start_val > 0 and end_val > 0:
                    return (end_val / start_val) ** (1 / (len(data) - 1)) - 1
    except: pass
    return None

def _get_yoy_change(df, row_name):
    """전년 대비 증감 여부 계산 (부채 감소 추세 등 확인용)"""
    try:
        if row_name in df.index:
            data = df.loc[row_name].dropna()
            if len(data) >= 2:
                return (data.iloc[0] - data.iloc[1]) / data.iloc[1]
    except: pass
    return 0

def _get_growth_stage(rev_growth, net_margin):
    """SEC 재무제표 기반 8단계 기업 생애주기 모델"""
    r, m = rev_growth or 0, net_margin or 0
    if r > 0.4 and m < 0: return "2단계: 초기 고성장 🌱 (매출 폭발/적자)", "warn"
    elif r > 0.2 and m > 0: return "3단계: 고성장 흑자 🚀 (매출/이익 동반성장)", "good"
    elif r > 0.05 and m > 0.1: return "4단계: 성숙한 성장 🌟 (안정적 매출/고수익)", "good"
    elif r > 0 and m > 0.15: return "5단계: 캐시카우 💰 (성장 둔화/막대한 현금)", "good"
    elif r > 0 and m < 0: return "1단계: 벤처/스타트업 🥚 (매출 미미/적자)", "warn"
    elif r <= 0 and m > 0: return "6단계: 정체기 🍂 (매출 감소/이익 유지)", "neutral"
    elif r <= -0.1 and m < 0: return "8단계: 쇠퇴기 ☠️ (역성장/적자 누적)", "bad"
    elif r <= 0 and m <= 0: return "7단계: 구조조정 ⚠️ (매출/이익 하락)", "bad"
    return "평가 불가 (데이터 부족)", "neutral"

def get_max_pain(tkr):
    """옵션 Max Pain 및 거래량 상위 분석"""
    try:
        exp_dates = tkr.options
        if not exp_dates: return None, None, None, None
        nearest_date = exp_dates[0]
        opt = tkr.option_chain(nearest_date)
        calls, puts = opt.calls, opt.puts
        
        strikes = sorted(list(set(calls['strike']).union(set(puts['strike']))))
        pain_values = {}
        for strike in strikes:
            c_pain = np.sum(calls['openInterest'] * np.maximum(0, strike - calls['strike']))
            p_pain = np.sum(puts['openInterest'] * np.maximum(0, puts['strike'] - strike))
            pain_values[strike] = c_pain + p_pain
            
        max_pain_strike = min(pain_values, key=pain_values.get)
        top_c = calls.nlargest(3, 'volume')[['strike', 'volume']].to_dict('records')
        top_p = puts.nlargest(3, 'volume')[['strike', 'volume']].to_dict('records')
        return nearest_date, max_pain_strike, top_c, top_p
    except: return None, None, None, None

# ─────────────────────────────────────────
# 🎨 상태 뱃지 생성기
# ─────────────────────────────────────────
def _badge(status_type, text):
    colors = {
        "good": ("#00E676", "rgba(0,230,118,0.15)"),
        "bad": ("#FF1744", "rgba(255,23,68,0.15)"),
        "warn": ("#FFC107", "rgba(255,193,7,0.15)"),
        "neutral": ("#82aaff", "rgba(130,170,255,0.15)")
    }
    color, bg = colors.get(status_type, colors["neutral"])
    return f"<span style='background-color:{bg}; color:{color}; padding:3px 8px; border-radius:6px; font-size:0.85rem; font-weight:700; margin-left:10px;'>{text}</span>"


# ─────────────────────────────────────────
# 🚀 메인 렌더링 함수
# ─────────────────────────────────────────
def render_company_details(ticker_str):
    st.markdown("""
    <style>
    .info-card { background-color: #161A22; border: 1px solid #2D333B; border-radius: 12px; padding: 22px; margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); }
    .info-title { font-size: 1.1rem; font-weight: 700; color: #FAFAFA; margin-bottom: 18px; border-bottom: 1px solid #2D333B; padding-bottom: 10px; display: flex; align-items: center; flex-wrap: wrap; }
    .metric-row { display: flex; justify-content: space-between; margin-bottom: 10px; font-size: 0.95rem; align-items: center; }
    .metric-label { color: #8b949e; font-weight: 500; }
    .metric-value { color: #c9d1d9; font-weight: 600; text-align: right; }
    .metric-good { color: #00E676; font-weight: 700; }
    .metric-bad { color: #FF1744; font-weight: 700; }
    .divider { border-top: 1px dashed #2D333B; margin: 15px 0; }
    </style>
    """, unsafe_allow_html=True)
    
    with st.spinner(f"📡 {ticker_str}의 12단계 심층 데이터를 파싱 중입니다..."):
        tkr = yf.Ticker(ticker_str)
        info = tkr.info
        if not info or 'shortName' not in info:
            st.error("해당 종목의 상세 데이터를 불러올 수 없습니다.")
            return
            
        fin = tkr.financials
        bs = tkr.balance_sheet
        current_price = info.get('currentPrice') or info.get('regularMarketPrice', 0)

        # CAGR 계산
        cagr_rev = _calc_cagr(fin, 'Total Revenue')
        cagr_ni = _calc_cagr(fin, 'Net Income')
        cagr_eps = _calc_cagr(fin, 'Basic EPS')

    st.markdown(f"### 🏢 {info.get('shortName', ticker_str)} <span style='font-size:1.1rem; color:#888;'>| {info.get('sector', 'N/A')}</span>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    
    with col1:
        # 📌 1. 성장 사이클
        stage_txt, stage_type = _get_growth_stage(info.get('revenueGrowth'), info.get('profitMargins'))
        st.markdown(f"""
        <div class="info-card">
            <div class="info-title">1. 이 회사, 지금 어느 단계인가요? {_badge(stage_type, stage_txt)}</div>
            <div class="metric-row"><span class="metric-label">SEC 기반 8단계 성장주기:</span> <span class="metric-value">{stage_txt}</span></div>
        </div>
        """, unsafe_allow_html=True)

        # 📌 2. 돈을 잘 버는 회사인가요?
        pm = info.get('profitMargins', 0)
        prof_stat = "good" if pm > 0.15 else ("warn" if pm > 0 else "bad")
        prof_txt = "🟢 탁월한 수익성" if pm > 0.15 else ("🟠 흑자 유지" if pm > 0 else "🔴 적자 상태")
        st.markdown(f"""
        <div class="info-card">
            <div class="info-title">2. 돈을 잘 버는 회사인가요? {_badge(prof_stat, prof_txt)}</div>
            <div class="metric-row"><span class="metric-label">시가총액:</span> <span class="metric-value">{_fmt_num(info.get('marketCap'))}</span></div>
            <div class="metric-row"><span class="metric-label">주당 순이익 (EPS):</span> <span class="metric-value">${info.get('trailingEps', 'N/A')}</span></div>
            <div class="metric-row"><span class="metric-label">최근 12개월 매출 (TTM):</span> <span class="metric-value">{_fmt_num(info.get('totalRevenue'))}</span></div>
            <div class="divider"></div>
            <div class="metric-row"><span class="metric-label">매출 총이익률:</span> <span class="metric-value">{_fmt_pct(info.get('grossMargins'))}</span></div>
            <div class="metric-row"><span class="metric-label">순이익률 (TTM):</span> <span class="metric-value metric-good">{_fmt_pct(pm)}</span></div>
            <div class="divider"></div>
            <div class="metric-row"><span class="metric-label">5년 매출 연평균 성장률:</span> <span class="metric-value">{_fmt_pct(cagr_rev)}</span></div>
            <div class="metric-row"><span class="metric-label">5년 순이익 연평균 성장률:</span> <span class="metric-value">{_fmt_pct(cagr_ni)}</span></div>
            <div class="metric-row"><span class="metric-label">5년 EPS 연평균 성장률:</span> <span class="metric-value">{_fmt_pct(cagr_eps)}</span></div>
        </div>
        """, unsafe_allow_html=True)

        # 📌 3. 지금까지 성적
        roe = info.get('returnOnEquity', 0)
        perf_stat = "good" if roe > 0.15 and (info.get('earningsGrowth') or 0) > 0 else "neutral"
        st.markdown(f"""
        <div class="info-card">
            <div class="info-title">3. 지금까지 성적 {_badge(perf_stat, '우상향 랠리' if perf_stat=='good' else '시장 수준')}</div>
            <div class="metric-row"><span class="metric-label">안정적인 수익 (흑자여부):</span> <span class="metric-value">{"안정적" if pm > 0 else "불안정"}</span></div>
            <div class="metric-row"><span class="metric-label">이익 마진 증가 (YOY):</span> <span class="metric-value">{_fmt_pct(info.get('earningsGrowth'))}</span></div>
            <div class="metric-row"><span class="metric-label">성장 가속화 (매출 YOY):</span> <span class="metric-value">{_fmt_pct(info.get('revenueGrowth'))}</span></div>
            <div class="metric-row"><span class="metric-label">자기자본이익률 (ROE):</span> <span class="metric-value metric-good">{_fmt_pct(roe)}</span></div>
        </div>
        """, unsafe_allow_html=True)

        # 📌 4. 성장 가능성
        retention = 1 - (info.get('payoutRatio') or 0)
        future_roe = roe * retention if roe else 0
        pot_stat = "good" if future_roe > 0.15 else "warn"
        st.markdown(f"""
        <div class="info-card">
            <div class="info-title">4. 미래 성장 가능성 {_badge(pot_stat, '고성장 기대' if pot_stat=='good' else '보통')}</div>
            <div class="metric-row"><span class="metric-label">수익 대비 저축률 (유보율):</span> <span class="metric-value">{_fmt_pct(retention)}</span></div>
            <div class="metric-row"><span class="metric-label">미래 성장 ROE 예상치:</span> <span class="metric-value">{_fmt_pct(future_roe)}</span></div>
        </div>
        """, unsafe_allow_html=True)

        # 📌 5. 회사에 돈이 얼마나 있나요?
        try:
            curr_debt = bs.loc['Current Debt'].iloc[0] if 'Current Debt' in bs.index else 0
            lt_debt = bs.loc['Long Term Debt'].iloc[0] if 'Long Term Debt' in bs.index else 0
            tot_assets = bs.loc['Total Assets'].iloc[0] if 'Total Assets' in bs.index else info.get('totalAssets', 0)
            tot_liab = bs.loc['Total Liabilities Net Minority Interest'].iloc[0] if 'Total Liabilities Net Minority Interest' in bs.index else 0
            int_exp = abs(fin.loc['Interest Expense'].iloc[0]) if 'Interest Expense' in fin.index else 0
            debt_yoy = _get_yoy_change(bs, 'Total Debt')
        except:
            curr_debt, lt_debt, tot_assets, tot_liab, int_exp, debt_yoy = 0,0,0,0,0,0

        dte = info.get('debtToEquity', 0)
        fin_stat = "good" if dte < 100 else ("bad" if dte > 200 else "warn")
        st.markdown(f"""
        <div class="info-card">
            <div class="info-title">5. 재무 건전성 (회사 돈) {_badge(fin_stat, '튼튼함' if fin_stat=='good' else '부채 주의')}</div>
            <div class="metric-row"><span class="metric-label">단기 부채:</span> <span class="metric-value">{_fmt_num(curr_debt)}</span></div>
            <div class="metric-row"><span class="metric-label">장기 부채:</span> <span class="metric-value">{_fmt_num(lt_debt)}</span></div>
            <div class="metric-row"><span class="metric-label">부채 감소 추세 (YOY):</span> <span class="metric-value">{_fmt_pct(debt_yoy)}</span></div>
            <div class="metric-row"><span class="metric-label">이자 부담 (연간):</span> <span class="metric-value">{_fmt_num(int_exp)}</span></div>
            <div class="metric-row"><span class="metric-label">부채/자본 비율:</span> <span class="metric-value">{dte}%</span></div>
            <div class="divider"></div>
            <div class="metric-row"><span class="metric-label">보유 현금:</span> <span class="metric-value">{_fmt_num(info.get('totalCash'))}</span></div>
            <div class="metric-row"><span class="metric-label">총 자산:</span> <span class="metric-value">{_fmt_num(tot_assets)}</span></div>
            <div class="metric-row"><span class="metric-label">총 부채:</span> <span class="metric-value">{_fmt_num(tot_liab)}</span></div>
            <div class="metric-row"><span class="metric-label">순 자산 (자본):</span> <span class="metric-value metric-good">{_fmt_num(tot_assets - tot_liab)}</span></div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        # 📌 6. 현재 사람들이 많이 사고 있나요?
        vol, avg_vol = info.get('volume', 0), info.get('averageVolume10days', 0)
        vol_stat = "good" if vol > avg_vol else "neutral"
        st.markdown(f"""
        <div class="info-card">
            <div class="info-title">6. 시장 수급 (많이 사나?) {_badge(vol_stat, '매수세 유입' if vol_stat=='good' else '관망/평균수준')}</div>
            <div class="metric-row"><span class="metric-label">현재 거래량:</span> <span class="metric-value">{_fmt_num(vol, False)} 주</span></div>
            <div class="metric-row"><span class="metric-label">10일 평균 거래량:</span> <span class="metric-value">{_fmt_num(avg_vol, False)} 주</span></div>
            <div class="metric-row"><span class="metric-label">3개월 평균 거래량:</span> <span class="metric-value">{_fmt_num(info.get('averageVolume'), False)} 주</span></div>
            <div class="metric-row"><span class="metric-label">거래량 변동 추이:</span> <span class="metric-value">{"평균 상회 🟢" if vol > avg_vol else "평균 하회 ⚪"}</span></div>
        </div>
        """, unsafe_allow_html=True)

        # 📌 7. 변동성이 큰가요?
        beta = info.get('beta', 1)
        beta_stat = "bad" if beta > 1.5 else ("good" if beta < 0.8 else "neutral")
        beta_txt = "초고위험" if beta > 1.5 else ("안전/방어주" if beta < 0.8 else "시장 수준")
        st.markdown(f"""
        <div class="info-card">
            <div class="info-title">7. 변동성 (리스크) {_badge(beta_stat, beta_txt)}</div>
            <div class="metric-row"><span class="metric-label">베타 (시장대비 민감도):</span> <span class="metric-value">{beta}</span></div>
            <div class="metric-row"><span class="metric-label">52주 가격 변화율:</span> <span class="metric-value">{_fmt_pct(info.get('52WeekChange'))}</span></div>
        </div>
        """, unsafe_allow_html=True)

        # 📌 8. 이 종목 비싼가요?
        pe = info.get('trailingPE', 0)
        val_stat = "good" if pe > 0 and pe < 15 else ("bad" if pe > 30 else "neutral")
        val_txt = "저평가 🟢" if val_stat == "good" else ("고평가 🔴" if val_stat == "bad" else "적정 수준")
        st.markdown(f"""
        <div class="info-card">
            <div class="info-title">8. 밸류에이션 (비싼가?) {_badge(val_stat, val_txt)}</div>
            <div class="metric-row"><span class="metric-label">주가 수익 비율 (P/E):</span> <span class="metric-value">{info.get('trailingPE', 'N/A')}</span></div>
            <div class="metric-row"><span class="metric-label">주가 매출 비율 (P/S):</span> <span class="metric-value">{info.get('priceToSalesTrailing12Months', 'N/A')}</span></div>
            <div class="metric-row"><span class="metric-label">섹터 / 산업:</span> <span class="metric-value">{info.get('sector', 'N/A')}</span></div>
        </div>
        """, unsafe_allow_html=True)

        # 📌 9. 전문가 의견
        score = info.get('recommendationMean', 3)
        exp_stat = "good" if score < 2.5 else ("bad" if score > 3.5 else "neutral")
        st.markdown(f"""
        <div class="info-card">
            <div class="info-title">9. 월가 전문가 컨센서스 {_badge(exp_stat, str(info.get('recommendationKey', 'N/A')).upper())}</div>
            <div class="metric-row"><span class="metric-label">목표가 (최저 / 중앙 / 최고):</span> <span class="metric-value">${info.get('targetLowPrice', 'N/A')} / ${info.get('targetMedianPrice', 'N/A')} / ${info.get('targetHighPrice', 'N/A')}</span></div>
            <div class="metric-row"><span class="metric-label">평균 목표가:</span> <span class="metric-value">${info.get('targetMeanPrice', 'N/A')}</span></div>
            <div class="metric-row"><span class="metric-label">의견 점수 (1=강력매수~5=매도):</span> <span class="metric-value">{score}</span></div>
            <div class="metric-row"><span class="metric-label">참여 애널리스트 수:</span> <span class="metric-value">{info.get('numberOfAnalystOpinions', 0)} 명</span></div>
        </div>
        """, unsafe_allow_html=True)

        # 📌 10. 지분 구조
        inst = info.get('heldPercentInstitutions', 0)
        insider = info.get('heldPercentInsiders', 0)
        public = 1 - inst - insider if inst else 0
        own_stat = "good" if inst > 0.6 else "neutral"
        st.markdown(f"""
        <div class="info-card">
            <div class="info-title">10. 지분 구조 (누가 들고있나?) {_badge(own_stat, '스마트머니 주도' if own_stat=='good' else '일반/개인 위주')}</div>
            <div class="metric-row"><span class="metric-label">총 발행 주식수:</span> <span class="metric-value">{_fmt_num(info.get('sharesOutstanding'), False)} 주</span></div>
            <div class="metric-row"><span class="metric-label">기관 투자자 비중:</span> <span class="metric-value">{_fmt_pct(inst)}</span></div>
            <div class="metric-row"><span class="metric-label">내부자(임원) 비중:</span> <span class="metric-value">{_fmt_pct(insider)}</span></div>
            <div class="metric-row"><span class="metric-label">정부/공공/일반(개인):</span> <span class="metric-value">{_fmt_pct(public)}</span></div>
        </div>
        """, unsafe_allow_html=True)

        # 📌 11. 시장은 어떤 가격을 보고 있나 (Max Pain)
        date, pain, top_c, top_p = get_max_pain(tkr)
        if pain and current_price:
            pain_stat = "good" if pain > current_price else "bad"
            pain_txt = "상방 베팅 우위 📈" if pain > current_price else "하방 압력 우위 📉"
        else:
            pain_stat, pain_txt = "neutral", "데이터 없음"
            
        c_html = "".join([f"<li style='margin-bottom:3px;'>행사가 ${c['strike']} (수량: {c['volume']})</li>" for c in top_c]) if top_c else "<li>없음</li>"
        p_html = "".join([f"<li style='margin-bottom:3px;'>행사가 ${p['strike']} (수량: {p['volume']})</li>" for p in top_p]) if top_p else "<li>없음</li>"

        st.markdown(f"""
        <div class="info-card">
            <div class="info-title">11. 시장이 보는 가격 (옵션) {_badge(pain_stat, pain_txt)}</div>
            <div class="metric-row"><span class="metric-label">가장 가까운 만기일:</span> <span class="metric-value">{date or 'N/A'}</span></div>
            <div class="metric-row"><span class="metric-label">Max Pain (최대 고통 가격):</span> <span class="metric-value" style="font-size:1.1rem; color:#FFC107;">${pain if pain else 'N/A'}</span></div>
            <div style="display:flex; justify-content: space-between; margin-top: 15px; font-size: 0.85rem; color:#CCC;">
                <div style="width:48%; background:rgba(0,230,118,0.1); padding:10px; border-radius:8px;"><b>🟢 Call (상승) Top 3</b><ul style="padding-left:15px; margin-top:5px;">{c_html}</ul></div>
                <div style="width:48%; background:rgba(255,23,68,0.1); padding:10px; border-radius:8px;"><b>🔴 Put (하락) Top 3</b><ul style="padding-left:15px; margin-top:5px;">{p_html}</ul></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 📌 12. 공매도 비율
        short_pct = info.get('shortPercentOfFloat', 0)
        short_stat = "bad" if short_pct > 0.1 else ("warn" if short_pct > 0.05 else "good")
        short_txt = "🚨 숏스퀴즈 위험" if short_pct > 0.1 else ("안전" if short_stat=='good' else "주의")
        st.markdown(f"""
        <div class="info-card">
            <div class="info-title">12. 공매도 현황 (Short) {_badge(short_stat, short_txt)}</div>
            <div class="metric-row"><span class="metric-label">전체 유통 주식 대비 공매도 비율:</span> <span class="metric-value metric-bad">{_fmt_pct(short_pct)}</span></div>
            <div class="metric-row"><span class="metric-label">현재 공매도 주식수:</span> <span class="metric-value">{_fmt_num(info.get('sharesShort'), False)} 주</span></div>
            <div class="metric-row"><span class="metric-label">총 발행 주식수:</span> <span class="metric-value">{_fmt_num(info.get('sharesOutstanding'), False)} 주</span></div>
        </div>
        """, unsafe_allow_html=True)