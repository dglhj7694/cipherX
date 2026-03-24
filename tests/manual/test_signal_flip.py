import sys
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine import detect_all_signals
from indicators import compute_indicators
import warnings

warnings.filterwarnings('ignore')

tickers = ['AAPL', 'NVDA', 'TSLA', 'AMZN']
bulk_data = yf.download(tickers, period="6mo", group_by='ticker', threads=True, progress=False)

def is_buy(j): return j in ['STRONG_BUY', 'BUY', 'WATCH_BUY']
def is_sell(j): return j in ['STRONG_SELL', 'SELL', 'WATCH_SELL']

for t in tickers:
    if isinstance(bulk_data.columns, pd.MultiIndex):
        df = bulk_data[t].copy()
    else: 
        df = bulk_data.copy()
        
    df.dropna(how='all', inplace=True)
    if len(df) < 50: continue
    
    try:
        df_ind = compute_indicators(df)
        df_sig = detect_all_signals(df_ind)
        
        print(f"\n=== [ {t} ] 매수/매도 시스템 전면부 전환(Flip) 테스트 (최근 6개월) ===")
        
        j_col = df_sig['Trade_Judgment']
        es_col = df_sig['Ensemble_Score']
        c_col = df_sig['Close']
        rs_col = df_sig['Judgment_Reason']
        
        flips = []
        for i in range(1, len(df_sig)):
            prev = j_col.iloc[i-1]
            curr = j_col.iloc[i]
            
            # 매도/관망 -> 매수 전환
            if not is_buy(prev) and is_buy(curr):
                date_str = df_sig.index[i].strftime('%Y-%m-%d')
                flips.append(f"🟢 [매수 스위칭] {date_str} | {prev:12s} -> {curr:12s} | 가격: ${c_col.iloc[i]:.2f} | 점수: {es_col.iloc[i]:+.1f} | 이유: {rs_col.iloc[i]}")
            
            # 매수/관망 -> 매도 전환
            elif not is_sell(prev) and is_sell(curr):
                date_str = df_sig.index[i].strftime('%Y-%m-%d')
                flips.append(f"🔴 [매도 스위칭] {date_str} | {prev:12s} -> {curr:12s} | 가격: ${c_col.iloc[i]:.2f} | 점수: {es_col.iloc[i]:+.1f} | 이유: {rs_col.iloc[i]}")
                
        # 최근 6개 결과만 출력
        if not flips:
            print("  최근 6개월 내 전환 시그널 없음.")
        for f in flips[-6:]:
            print(f)
            
    except Exception as e:
        print(f"Error on {t}: {e}")
