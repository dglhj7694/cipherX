import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# ─────────────────────────────────────────
# 🛠️ 유틸리티 함수
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
    """최근 4~5년 재무 데이터를 바탕으로 연평균 성장률(CAGR) 계산"""
    try:
        if row_name in financials.index:
            data = financials.loc[row_name].dropna()
            if len(data) >= 2:
                start_val = data.iloc[-1] # 가장 오래된 데이터
                end_val = data.iloc[0]    # 가장 최신 데이터
                if start_val > 0 and end_val > 0:
                    cagr = (end_val / start_val) ** (1 / (len(data) - 1)) - 1
                    return cagr
    except: pass
    return None

def _get_growth_stage(info, cagr_rev):
    """SEC 재무제표 기반 8단계 기업 생애주기 모델"""
    rev_growth = info.get('revenueGrowth', 0) or 0
    net_margin = info.get('profitMargins', 0) or 0
    
    if rev_growth > 0.4 and net_margin < 0: return "2단계: 초기 고성장 (매출 폭발, 적자 지속) 🌱"
    elif rev_growth > 0.2 and net_margin > 0: return "3단계: 고성장 흑자 (매출 고성장, 이익 창출) 🚀"
    elif rev_growth > 0.1 and net_margin > 0.1: return "4단계: 성숙한 성장 (안정적 매출, 고수익성) 🌟"
    elif rev_growth > 0 and net_margin > 0.15: return "5단계: 캐시카우 (성장 둔화, 막대현 현금흐름) 💰"
    elif rev_growth > 0 and net_margin < 0: return "1단계: 스타트업/개발 (미미한 매출, 투자 단계) 🥚"
    elif rev_growth <= 0 and net_margin > 0: return "6단계: 정체기 (매출 감소, 이익 유지) 🍂"
    elif rev_growth <= -0.1 and net_margin < 0: return "8단계: 쇠퇴기 (역성장 및 적자 누적) ☠️"
    elif rev_growth <= 0 and net_margin <= 0: return "7단계: 구조조정 (매출/이익 동반 하락) ⚠️"
    return "평가 불가 (데이터 부족) ⚪"

def get_max_pain(tkr):
    """가장 가까운 만기일의 옵션 Max Pain 및 거래량 상위 분석"""
    try:
        exp_dates = tkr.options
        if not exp_dates: return None, None, None, None
        
        nearest_date = exp_dates[0]
        opt = tkr.option_chain(nearest_date)
        calls, puts = opt.calls, opt.puts
        
        strikes = sorted(list(set(calls['strike']).union(set(puts['strike']))))
        pain_values = {}
        for strike in strikes:
            call_pain = np.sum(calls['openInterest'] * np.maximum(0, strike - calls['strike']))
            put_pain = np.sum(puts['openInterest'] * np.maximum(0, puts['strike'] - strike))
            pain_values[strike] = call_pain + put_pain
            
        max_pain_strike = min(pain_values, key=pain_values.get)
        top_calls = calls.nlargest(3, 'volume')[['strike', 'volume']].to_dict('records')
        top_puts = puts.nlargest(3, 'volume')[['strike', 'volume']].to_dict('records')
        return nearest_date, max_pain_strike, top_calls, top_puts
    except: return None, None, None, None


# ─────────────────────────────────────────
# 🎨 메인 렌더링 함수
# ─────────────────────────────────────────
def render_company_details(ticker_str):
    st.markdown("""
    <style>
    .info-card { background-color: #161A22; border: 1px solid #2D333B; border-radius: 12px; padding: 20px; margin-bottom: 16px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
    .info-title { font-size: 1.1rem; font-weight: 700; color: #82aaff; margin-bottom: 15px; border-bottom: 1px solid #2D333B; padding-bottom: 8px; }
    .metric-row { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 0.95rem; }
    .metric-label { color: #888; }
    .metric-value { color: #FAFAFA; font-weight: 600; text-align: right; }
    .metric-highlight { color: #00E676; font-weight: 700; }
    .metric-warn { color: #FF1744; font-weight: 700; }
    </style>
    """, unsafe_allow_html=True)
    
    with st.spinner(f"📡 {ticker_str}의 SEC 공시 및 파생 데이터를 집계 중입니다..."):
        tkr = yf.Ticker(ticker_str)
        info = tkr.info
        if not info or 'shortName' not in info:
            st.error("해당 종목의 상세 데이터를 불러올 수 없습니다.")
            return
            
        fin = tkr.financials
        bs = tkr.balance_sheet

        # 5년 연평균 성장률(CAGR) 계산
        cagr_rev = _calc_cagr(fin, 'Total Revenue')
        cagr_ni = _calc_cagr(fin, 'Net Income')
        cagr_eps = _calc_cagr(fin, 'Basic EPS')

        sector = info.get('sector', 'N/A')
        industry = info.get('industry', 'N/A')

    st.markdown(f"### 🏢 {info.get('shortName', ticker_str)} ({sector} / {industry})")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 1. 성장 사이클 & 2. 수익성
        st.markdown(f"""
        <div class="info-card">
            <div class="info-title">1. 성장 단계 & 2. 수익성 (SEC 기준)</div>
            <div class="metric-row"><span class="metric-label">현재 성장 8단계:</span> <span class="metric-value metric-highlight">{_get_growth_stage(info, cagr_rev)}</span></div>
            <div class="metric-row"><span class="metric-label">시가총액:</span> <span class="metric-value">{_fmt_num(info.get('marketCap'))}</span></div>
            <div class="metric-row"><span class="metric-label">주당 순이익(EPS):</span> <span class="metric-value">${info.get('trailingEps', 'N/A')}</span></div>
            <div class="metric-row"><span class="metric-label">최근 12M 매출:</span> <span class="metric-value">{_fmt_num(info.get('totalRevenue'))}</span></div>
            <div class="metric-row"><span class="metric-label">매출 총이익률:</span> <span class="metric-value">{_fmt_pct(info.get('grossMargins'))}</span></div>
            <div class="metric-row"><span class="metric-label">순이익률:</span> <span class="metric-value">{_fmt_pct(info.get('profitMargins'))}</span></div>
            <hr style="border-color:#2D333B; margin: 10px 0;">
            <div class="metric-row"><span class="metric-label">5년 매출 성장률(CAGR):</span> <span class="metric-value">{_fmt_pct(cagr_rev)}</span></div>
            <div class="metric-row"><span class="metric-label">5년 순이익 성장률(CAGR):</span> <span class="metric-value">{_fmt_pct(cagr_ni)}</span></div>
            <div class="metric-row"><span class="metric-label">5년 EPS 성장률(CAGR):</span> <span class="metric-value">{_fmt_pct(cagr_eps)}</span></div>
        </div>
        """, unsafe_allow_html=True)

        # 3. 과거 성적 & 4. 성장 가능성
        payout_ratio = info.get('payoutRatio', 0)
        retention_ratio = 1 - payout_ratio if payout_ratio is not None else 1
        roe = info.get('returnOnEquity', 0)
        future_roe_est = (roe * retention_ratio) if roe else None
        
        st.markdown(f"""
        <div class="info-card">
            <div class="info-title">3. 최근 성적 & 4. 미래 성장 가능성</div>
            <div class="metric-row"><span class="metric-label">이익 성장 추이(YOY):</span> <span class="metric-value">{_fmt_pct(info.get('earningsGrowth'))}</span></div>
            <div class="metric-row"><span class="metric-label">매출 성장 가속화(YOY):</span> <span class="metric-value">{_fmt_pct(info.get('revenueGrowth'))}</span></div>
            <div class="metric-row"><span class="metric-label">자기자본이익률(ROE):</span> <span class="metric-value">{_fmt_pct(roe)}</span></div>
            <hr style="border-color:#2D333B; margin: 10px 0;">
            <div class="metric-row"><span class="metric-label">수익 대비 저축률(유보율):</span> <span class="metric-value">{_fmt_pct(retention_ratio)}</span></div>
            <div class="metric-row"><span class="metric-label">미래 성장 ROE 추정치:</span> <span class="metric-value">{_fmt_pct(future_roe_est)}</span></div>
        </div>
        """, unsafe_allow_html=True)

        # 5. 재무 건전성 (회사에 돈이 얼마나 있나요?)
        try:
            curr_debt = bs.loc['Current Debt'].iloc[0] if 'Current Debt' in bs.index else 0
            lt_debt = bs.loc['Long Term Debt'].iloc[0] if 'Long Term Debt' in bs.index else 0
            tot_assets = bs.loc['Total Assets'].iloc[0] if 'Total Assets' in bs.index else info.get('totalAssets', 0)
            tot_liab = bs.loc['Total Liabilities Net Minority Interest'].iloc[0] if 'Total Liabilities Net Minority Interest' in bs.index else 0
            net_assets = tot_assets - tot_liab
        except:
            curr_debt, lt_debt, tot_assets, tot_liab, net_assets = 0, 0, 0, 0, 0

        st.markdown(f"""
        <div class="info-card">
            <div class="info-title">5. 재무 건전성 (대차대조표 요약)</div>
            <div class="metric-row"><span class="metric-label">보유 현금:</span> <span class="metric-value">{_fmt_num(info.get('totalCash'))}</span></div>
            <div class="metric-row"><span class="metric-label">단기 부채:</span> <span class="metric-value">{_fmt_num(curr_debt)}</span></div>
            <div class="metric-row"><span class="metric-label">장기 부채:</span> <span class="metric-value">{_fmt_num(lt_debt)}</span></div>
            <div class="metric-row"><span class="metric-label">부채/자본 비율:</span> <span class="metric-value">{info.get('debtToEquity', 'N/A')}%</span></div>
            <hr style="border-color:#2D333B; margin: 10px 0;">
            <div class="metric-row"><span class="metric-label">총 자산:</span> <span class="metric-value">{_fmt_num(tot_assets)}</span></div>
            <div class="metric-row"><span class="metric-label">총 부채:</span> <span class="metric-value">{_fmt_num(tot_liab)}</span></div>
            <div class="metric-row"><span class="metric-label">순 자산 (Equity):</span> <span class="metric-value metric-highlight">{_fmt_num(net_assets)}</span></div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        # 6. 시장 수요 & 7. 변동성
        st.markdown(f"""
        <div class="info-card">
            <div class="info-title">6. 거래량 (수급) & 7. 변동성</div>
            <div class="metric-row"><span class="metric-label">현재 거래량:</span> <span class="metric-value">{_fmt_num(info.get('volume'), False)} 주</span></div>
            <div class="metric-row"><span class="metric-label">10일 평균 거래량:</span> <span class="metric-value">{_fmt_num(info.get('averageVolume10days'), False)} 주</span></div>
            <div class="metric-row"><span class="metric-label">3개월 평균 거래량:</span> <span class="metric-value">{_fmt_num(info.get('averageVolume'), False)} 주</span></div>
            <hr style="border-color:#2D333B; margin: 10px 0;">
            <div class="metric-row"><span class="metric-label">베타 (시장 대비 변동성):</span> <span class="metric-value">{info.get('beta', 'N/A')}</span></div>
            <div class="metric-row"><span class="metric-label">52주 가격 변화율:</span> <span class="metric-value">{_fmt_pct(info.get('52WeekChange'))}</span></div>
        </div>
        """, unsafe_allow_html=True)

        # 8. 가치평가 & 9. 애널리스트 의견
        st.markdown(f"""
        <div class="info-card">
            <div class="info-title">8. 밸류에이션 (비싼가?) & 9. 전문가 목표가</div>
            <div class="metric-row"><span class="metric-label">주가수익비율 (Trailing P/E):</span> <span class="metric-value">{info.get('trailingPE', 'N/A')}</span></div>
            <div class="metric-row"><span class="metric-label">미래수익비율 (Forward P/E):</span> <span class="metric-value">{info.get('forwardPE', 'N/A')}</span></div>
            <div class="metric-row"><span class="metric-label">주가매출비율 (P/S):</span> <span class="metric-value">{info.get('priceToSalesTrailing12Months', 'N/A')}</span></div>
            <hr style="border-color:#2D333B; margin: 10px 0;">
            <div class="metric-row"><span class="metric-label">전문가 종합 의견:</span> <span class="metric-value metric-highlight">{str(info.get('recommendationKey', 'N/A')).upper()}</span></div>
            <div class="metric-row"><span class="metric-label">의견 점수 (1=강력매수, 5=매도):</span> <span class="metric-value">{info.get('recommendationMean', 'N/A')} 점</span></div>
            <div class="metric-row"><span class="metric-label">목표가 (최저 / 중앙 / 최고):</span> <span class="metric-value">${info.get('targetLowPrice', 'N/A')} / ${info.get('targetMedianPrice', 'N/A')} / ${info.get('targetHighPrice', 'N/A')}</span></div>
            <div class="metric-row"><span class="metric-label">참여 애널리스트 수:</span> <span class="metric-value">{info.get('numberOfAnalystOpinions', 0)} 명</span></div>
        </div>
        """, unsafe_allow_html=True)

        # 10. 주주 구성 & 12. 공매도
        st.markdown(f"""
        <div class="info-card">
            <div class="info-title">10. 주주 지분구조 & 12. 공매도 현황</div>
            <div class="metric-row"><span class="metric-label">총 발행 주식수:</span> <span class="metric-value">{_fmt_num(info.get('sharesOutstanding'), False)} 주</span></div>
            <div class="metric-row"><span class="metric-label">기관 투자자 비중:</span> <span class="metric-value">{_fmt_pct(info.get('heldPercentInstitutions'))}</span></div>
            <div class="metric-row"><span class="metric-label">내부자 비중:</span> <span class="metric-value">{_fmt_pct(info.get('heldPercentInsiders'))}</span></div>
            <hr style="border-color:#2D333B; margin: 10px 0;">
            <div class="metric-row"><span class="metric-label">유통주식 대비 공매도 비율:</span> <span class="metric-value metric-warn">{_fmt_pct(info.get('shortPercentOfFloat'))}</span></div>
            <div class="metric-row"><span class="metric-label">공매도 잔고 (Shares Short):</span> <span class="metric-value">{_fmt_num(info.get('sharesShort'), False)} 주</span></div>
            <div class="metric-row"><span class="metric-label">숏 커버링 필요 일수 (Short Ratio):</span> <span class="metric-value">{info.get('shortRatio', 'N/A')} 일</span></div>
        </div>
        """, unsafe_allow_html=True)

    # 11. 옵션 시장 (Max Pain)
    date, pain, top_c, top_p = get_max_pain(tkr)
    pain_html = f"<div class='metric-row'><span class='metric-label'>만기일: {date}</span> <span class='metric-value metric-warn' style='font-size:1.2rem;'>Max Pain: ${pain}</span></div>" if pain else "옵션 데이터가 없습니다."
    
    c_html = "".join([f"<li>행사가 ${c['strike']} (수량: {c['volume']})</li>" for c in top_c]) if top_c else ""
    p_html = "".join([f"<li>행사가 ${p['strike']} (수량: {p['volume']})</li>" for p in top_p]) if top_p else ""

    st.markdown(f"""
    <div class="info-card">
        <div class="info-title">11. 옵션 파생 시장 심리 (세력의 목표가)</div>
        {pain_html}
        <div style="display:flex; justify-content: space-between; margin-top: 10px; font-size: 0.9rem; color: #AAA;">
            <div style="width:48%;"><b>🟢 상방 베팅 (Call Top 3)</b><br><ul style="margin-top:5px; padding-left:20px;">{c_html}</ul></div>
            <div style="width:48%;"><b>🔴 하방 베팅 (Put Top 3)</b><br><ul style="margin-top:5px; padding-left:20px;">{p_html}</ul></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 13. 관련 최신 뉴스
    st.markdown("""<div class="info-card"><div class="info-title">13. 관련 최신 뉴스</div>""", unsafe_allow_html=True)
    news = tkr.news
    if news:
        for n in news[:3]:
            pub_date = datetime.fromtimestamp(n['providerPublishTime']).strftime('%Y-%m-%d %H:%M')
            st.markdown(f"<div style='margin-bottom:8px; font-size:0.9rem;'><span style='color:#888'>[{pub_date}]</span> <a href='{n['link']}' style='color:#667eea; text-decoration:none;' target='_blank'><b>{n['title']}</b></a></div>", unsafe_allow_html=True)
    else:
        st.write("최신 뉴스를 불러올 수 없습니다.")
    st.markdown("</div>", unsafe_allow_html=True)