import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

def _format_large_num(num):
    if pd.isna(num) or num is None: return "N/A"
    if num >= 1e12: return f"${num/1e12:.2f}T (조)"
    elif num >= 1e9: return f"${num/1e9:.2f}B (십억)"
    elif num >= 1e6: return f"${num/1e6:.2f}M (백만)"
    return f"${num:,.0f}"

def _format_pct(num):
    if pd.isna(num) or num is None: return "N/A"
    return f"{num * 100:.2f}%"

def _get_growth_stage(info, financials):
    """SEC 재무제표 기반 8단계 기업 생애주기 추정"""
    try:
        rev_growth = info.get('revenueGrowth', 0)
        net_margin = info.get('profitMargins', 0)
        
        if rev_growth > 0.4 and net_margin < 0: return "2단계: 초기 고성장기 🌱 (매출 급증, 적자)"
        elif rev_growth > 0.2 and net_margin > 0: return "3단계: 고성장기 🚀 (매출 고성장, 흑자 전환)"
        elif rev_growth > 0.05 and net_margin > 0.1: return "4~5단계: 성숙한 성장/캐시카우 🌳 (안정적 매출, 높은 이익률)"
        elif rev_growth > 0 and net_margin < 0: return "1단계: 스타트업/개발기 🥚 (미미한 매출, 적자)"
        elif rev_growth <= 0 and net_margin > 0: return "6단계: 정체기 🍂 (매출 감소, 이익 유지)"
        elif rev_growth <= 0 and net_margin < 0: return "7~8단계: 쇠퇴/구조조정기 ⚠️ (역성장 및 적자 누적)"
        return "평가 대기 (데이터 부족)"
    except:
        return "평가 불가"

def get_max_pain(tkr):
    """가장 가까운 만기일의 옵션 Max Pain 계산"""
    try:
        exp_dates = tkr.options
        if not exp_dates: return "옵션 데이터 없음", None, None
        
        nearest_date = exp_dates[0]
        opt = tkr.option_chain(nearest_date)
        calls, puts = opt.calls, opt.puts
        
        # Max Pain 계산: 각 행사가(Strike)마다 콜/풋 매수자의 내재가치 손실 합산
        strikes = sorted(list(set(calls['strike']).union(set(puts['strike']))))
        pain_values = {}
        for strike in strikes:
            call_pain = np.sum(calls['openInterest'] * np.maximum(0, strike - calls['strike']))
            put_pain = np.sum(puts['openInterest'] * np.maximum(0, puts['strike'] - strike))
            pain_values[strike] = call_pain + put_pain
            
        max_pain_strike = min(pain_values, key=pain_values.get)
        
        # 거래량 상위 3개 추출
        top_calls = calls.nlargest(3, 'volume')[['strike', 'volume']].to_dict('records')
        top_puts = puts.nlargest(3, 'volume')[['strike', 'volume']].to_dict('records')
        
        return nearest_date, max_pain_strike, top_calls, top_puts
    except Exception as e:
        return "오류 발생", None, None

def render_company_details(ticker_str):
    st.markdown("### 🏢 기업 펀더멘탈 및 시장 심리 심층 분석 (SEC / YF 기반)")
    
    with st.spinner(f"{ticker_str}의 공시 및 재무 데이터를 집계 중입니다..."):
        tkr = yf.Ticker(ticker_str)
        info = tkr.info
        financials = tkr.financials
        bs = tkr.balance_sheet
        
        if not info or 'shortName' not in info:
            st.error("해당 종목의 상세 데이터를 불러올 수 없습니다.")
            return

    # ─────────────────────────────────────────
    # 파트 1: SEC 재무 기반 기업 분석
    # ─────────────────────────────────────────
    st.markdown("#### 📁 Part 1. SEC 재무제표 기반 분석")
    col1, col2 = st.columns(2)
    
    with col1:
        with st.container(border=True):
            st.markdown("##### 1. 기업 성장 사이클")
            stage = _get_growth_stage(info, financials)
            st.markdown(f"<p style='color:#00E676; font-size:1.1rem; font-weight:bold;'>{stage}</p>", unsafe_allow_html=True)
            st.caption("최근 매출 성장률 및 순이익률을 바탕으로 한 추정치입니다.")
            
        with st.container(border=True):
            st.markdown("##### 3. 과거 성적 및 수익성 추이")
            roe = info.get('returnOnEquity', None)
            st.write(f"- **자기자본이익률(ROE):** {_format_pct(roe)}")
            st.write(f"- **수익 안정성:** {'흑자 유지' if info.get('profitMargins', 0) > 0 else '적자 상태'}")
            st.write("- **5년 매출 성장률:** N/A (분기별 별도 검증 필요)")
            
    with col2:
        with st.container(border=True):
            st.markdown("##### 2. 돈을 잘 버는 회사인가요?")
            st.write(f"- **시가총액:** {_format_large_num(info.get('marketCap'))}")
            st.write(f"- **주당순이익(TTM EPS):** ${info.get('trailingEps', 'N/A')}")
            st.write(f"- **최근 12개월 매출(TTM):** {_format_large_num(info.get('totalRevenue'))}")
            st.write(f"- **매출 총이익률(Gross Margin):** {_format_pct(info.get('grossMargins'))}")
            st.write(f"- **순이익률(Net Margin):** {_format_pct(info.get('profitMargins'))}")

        with st.container(border=True):
            st.markdown("##### 4. 성장 가능성 (Growth Potential)")
            st.write(f"- **매출 성장률(YOY):** {_format_pct(info.get('revenueGrowth'))}")
            st.write(f"- **이익 성장률(YOY):** {_format_pct(info.get('earningsGrowth'))}")
            st.write(f"- **PEG Ratio (성장대비 가치):** {info.get('pegRatio', 'N/A')} (1 이하면 저평가)")

    # ─────────────────────────────────────────
    # 파트 2: 재무 건전성 및 가치 평가
    # ─────────────────────────────────────────
    st.markdown("#### 🏦 Part 2. 자금력 및 가치 평가 (Valuation)")
    col3, col4 = st.columns(2)
    
    with col3:
        with st.container(border=True):
            st.markdown("##### 5. 회사에 돈이 얼마나 있나요? (건전성)")
            st.write(f"- **총 현금:** {_format_large_num(info.get('totalCash'))}")
            st.write(f"- **총 부채:** {_format_large_num(info.get('totalDebt'))}")
            st.write(f"- **부채/자본 비율(Debt to Equity):** {info.get('debtToEquity', 'N/A')}%")
            st.write(f"- **유동 비율(Current Ratio):** {info.get('currentRatio', 'N/A')}")
            
        with st.container(border=True):
            st.markdown("##### 8. 이 종목, 비싼가요? (Valuation)")
            trailing_pe = info.get('trailingPE', 'N/A')
            forward_pe = info.get('forwardPE', 'N/A')
            ps_ratio = info.get('priceToSalesTrailing12Months', 'N/A')
            st.write(f"- **현재 P/E (PER):** {trailing_pe}")
            st.write(f"- **선행 P/E (Forward PER):** {forward_pe}")
            st.write(f"- **P/S (매출 대비 주가):** {ps_ratio}")
            st.write(f"- **P/B (자산 대비 주가):** {info.get('priceToBook', 'N/A')}")

    with col4:
        with st.container(border=True):
            st.markdown("##### 10. 이 회사는 누가 들고 있나요? (지분구조)")
            st.write(f"- **기관 투자자 비중:** {_format_pct(info.get('heldPercentInstitutions'))}")
            st.write(f"- **내부자(임원 등) 비중:** {_format_pct(info.get('heldPercentInsiders'))}")
            st.write(f"- **유통 주식수(Float):** {_format_large_num(info.get('floatShares'))}")
            st.write(f"- **총 발행 주식수:** {_format_large_num(info.get('sharesOutstanding'))}")

        with st.container(border=True):
            st.markdown("##### 9. 월가 전문가들의 의견은? (Consensus)")
            st.write(f"- **종합 의견:** **{info.get('recommendationKey', 'N/A').upper()}**")
            st.write(f"- **참여 애널리스트 수:** {info.get('numberOfAnalystOpinions', 'N/A')}명")
            st.write(f"- **목표가 (최저 / 평균 / 최고):** ${info.get('targetLowPrice', 'N/A')} / **${info.get('targetMeanPrice', 'N/A')}** / ${info.get('targetHighPrice', 'N/A')}")

    # ─────────────────────────────────────────
    # 파트 3: 시장 심리 및 파생/공매도 현황
    # ─────────────────────────────────────────
    st.markdown("#### 🌊 Part 3. 수급, 파생 심리 및 공매도")
    col5, col6 = st.columns(2)
    
    with col5:
        with st.container(border=True):
            st.markdown("##### 6 & 7. 거래량 및 변동성")
            st.write(f"- **현재 거래량:** {_format_large_num(info.get('volume'))}")
            st.write(f"- **10일 평균 거래량:** {_format_large_num(info.get('averageVolume10days'))}")
            st.write(f"- **베타(Beta, 시장대비 변동성):** {info.get('beta', 'N/A')}")
            st.write(f"- **52주 가격 변동폭:** {_format_pct(info.get('52WeekChange'))}")

        with st.container(border=True):
            st.markdown("##### 12. 공매도 비율 (Short Interest)")
            st.write(f"- **유통주식 대비 공매도 비율:** {_format_pct(info.get('shortPercentOfFloat'))}")
            st.write(f"- **공매도 잔고(Shares Short):** {_format_large_num(info.get('sharesShort'))}")
            st.write(f"- **Days to Cover (숏커버링 소요일):** {info.get('shortRatio', 'N/A')}일")

    with col6:
        with st.container(border=True):
            st.markdown("##### 11. 옵션 시장은 얼마를 보고 있나요? (Max Pain)")
            date, pain, top_c, top_p = get_max_pain(tkr)
            if pain:
                st.write(f"- **가장 가까운 만기일:** {date}")
                st.markdown(f"- **🎯 Max Pain (최대 고통 가격):** <span style='color:#FF1744; font-size:1.2rem; font-weight:bold;'>${pain}</span>", unsafe_allow_html=True)
                st.caption("주가가 이 가격에 머물 때 콜/풋 매수자들의 손실이 가장 극대화됩니다. (기관의 타겟 가격)")
                
                st.write("**🔥 Call (상방 베팅) 거래량 Top 3:**")
                for c in top_c: st.write(f"  행사가 ${c['strike']} (거래량: {c['volume']})")
                st.write("**🧊 Put (하방 베팅) 거래량 Top 3:**")
                for p in top_p: st.write(f"  행사가 ${p['strike']} (거래량: {p['volume']})")
            else:
                st.write("옵션 데이터가 제공되지 않는 종목입니다.")

    # ─────────────────────────────────────────
    # 파트 4: 최신 뉴스
    # ─────────────────────────────────────────
    st.markdown("#### 📰 13. 최신 뉴스 (Top 3)")
    news = tkr.news
    if news:
        for n in news[:3]:
            pub_date = datetime.fromtimestamp(n['providerPublishTime']).strftime('%Y-%m-%d %H:%M')
            st.write(f"- [{pub_date}] [{n['title']}]({n['link']})")
    else:
        st.write("최신 뉴스가 없습니다.")