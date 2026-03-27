import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import math, time, re

_ANALYSIS_US_TICKER_PATTERN = re.compile(r"^[A-Z]{1,6}(?:[.\-][A-Z0-9]{1,4})?$")
_ANALYSIS_KR_CODE_PATTERN = re.compile(r"^\d{6}$")
_ANALYSIS_KR_TICKER_PATTERN = re.compile(r"^\d{6}\.(?:KS|KQ)$")
_CURRENCY_SYMBOLS = {
    "USD": "$",
    "KRW": "KRW ",
    "JPY": "JPY ",
    "EUR": "EUR ",
    "GBP": "GBP ",
    "CNY": "CNY ",
    "HKD": "HK$",
}

def _recent(s,lb=3):return s.astype(float).rolling(lb+1,min_periods=1).max().fillna(0).astype(bool)
def _cooldown(sig,bars=5):
    v=sig.fillna(False).values.astype(bool);out=np.zeros(len(v),dtype=bool);last=-bars-1
    for i in range(len(v)):
        if v[i] and (i-last)>bars:out[i]=True;last=i
    return pd.Series(out,index=sig.index)
def _cd_dir(df,bs,ss,bars=5):
    bv=df.get(bs,pd.Series(False,index=df.index)).fillna(False).values.astype(bool)
    sv=df.get(ss,pd.Series(False,index=df.index)).fillna(False).values.astype(bool)
    bo=np.zeros(len(bv),dtype=bool);so=np.zeros(len(sv),dtype=bool);lb_=-bars-1;ls_=-bars-1
    for i in range(len(df)):
        if sv[i]:lb_=-bars-1
        if bv[i]:ls_=-bars-1
        if bv[i] and (i-lb_)>bars:bo[i]=True;lb_=i
        if sv[i] and (i-ls_)>bars:so[i]=True;ls_=i
    if bs in df.columns:df[bs]=pd.Series(bo,index=df.index)
    if ss in df.columns:df[ss]=pd.Series(so,index=df.index)
def _volf(vol,r=.5,p=20):return vol>=(vol.rolling(p,min_periods=5).mean()*r)
def _valid_fmt(t):
    text = str(t or "").strip().upper()
    return bool(
        _ANALYSIS_US_TICKER_PATTERN.fullmatch(text)
        or _ANALYSIS_KR_CODE_PATTERN.fullmatch(text)
        or _ANALYSIS_KR_TICKER_PATTERN.fullmatch(text)
    )
def _vs(cond):c=cond.fillna(False).astype(int);g=(c==0).cumsum();return c.groupby(g).cumsum()
def _sp(df,sn,pts):
    if sn not in df.columns:return pd.Series(0.,index=df.index)
    return pd.Series(np.where(df[sn].fillna(False),pts,0.),index=df.index)
def _spd(df,sn,fp,dd=3,dr=.5):
    if sn not in df.columns:return np.zeros(len(df),dtype=float)
    b=np.where(df[sn].fillna(False),fp,0.);t=b.copy()
    for d in range(1,dd+1):s=np.roll(b,d);s[:d]=0;t+=s*(dr**d)
    return t
def _cs_str(cs_list):return ', '.join(f"{c['icon']}{c['kor']}[T{c['tier']}]" for c in cs_list)
def _sf(val,default=0.):
    try:r=float(val);return r if r==r else default
    except:return default

def _display_currency(info):
    code = str((info or {}).get('currency') or (info or {}).get('financialCurrency') or 'USD').upper()
    symbol = _CURRENCY_SYMBOLS.get(code, f"{code} ")
    return code, symbol

def _format_quote_value(val, currency_code='USD', currency_symbol='$'):
    if val is None:
        return "N/A"
    try:
        numeric = float(val)
    except Exception:
        return "N/A"
    decimals = 0 if currency_code in {"KRW", "JPY"} else 2
    return f"{currency_symbol}{numeric:,.{decimals}f}"

def _analysis_ticker_candidates(t):
    raw = str(t or "").strip().upper()
    if _ANALYSIS_KR_CODE_PATTERN.fullmatch(raw):
        return [f"{raw}.KS", f"{raw}.KQ"]
    if _ANALYSIS_KR_TICKER_PATTERN.fullmatch(raw) or _ANALYSIS_US_TICKER_PATTERN.fullmatch(raw):
        return [raw]
    return []

# ━━━ 캐시 ━━━
@st.cache_data(ttl=3600,show_spinner=False)
def fetch_fundamentals(t):
    try:
        info=yf.Ticker(t).info
        currency_code, currency_symbol = _display_currency(info)
        def g(key,fmt=None):
            val=info.get(key)
            if val is None:return "N/A"
            try:
                if fmt=='$':return _format_quote_value(val, currency_code, currency_symbol)
                if fmt=='n':return f"{val:,.0f}"
                return str(val)
            except:return "N/A"
        return f"MCap:{g('marketCap','n')} PE:{g('trailingPE')} 52H:{g('fiftyTwoWeekHigh','$')} 52L:{g('fiftyTwoWeekLow','$')} AvgVol:{g('averageVolume','n')}"
    except:return "N/A"
@st.cache_data(ttl=300,max_entries=30,show_spinner=False)
def fetch_history(t,_ts=None):
    try:return yf.Ticker(t).history(period="2y")
    except:return pd.DataFrame()
@st.cache_data(ttl=3600,show_spinner=False)
def fetch_spy(_ts=None):return yf.Ticker("SPY").history(period="2y")
@st.cache_data(ttl=3600,show_spinner=False)
def validate_ticker(t):
    try:return not yf.Ticker(t).history(period="5d").empty
    except:return False
@st.cache_data(ttl=3600,show_spinner=False)
def resolve_analysis_ticker(t):
    raw = str(t or "").strip().upper()
    if not _valid_fmt(raw):
        return {"input": raw, "resolved": None, "valid": False, "reason": "format", "candidates": []}
    candidates = _analysis_ticker_candidates(raw)
    for candidate in candidates:
        if validate_ticker(candidate):
            return {
                "input": raw,
                "resolved": candidate,
                "valid": True,
                "reason": "ok",
                "candidates": candidates,
                "auto_resolved": candidate != raw,
            }
    return {"input": raw, "resolved": None, "valid": False, "reason": "not_found", "candidates": candidates}
@st.cache_data(ttl=300,max_entries=50,show_spinner=False)
def _compute_cached(t,k):
    from engine import detect_all_signals
    from indicators import compute_indicators
    try:df=fetch_history(t);return detect_all_signals(compute_indicators(df)) if not df.empty else None
    except Exception as e:print(f"[ERR]{t}:{e}");return None
def compute_and_cache(t,ts=None):
    ck=f"{t}_{ts}" if ts else f"{t}_{math.floor(time.time()/300)}";return _compute_cached(t,ck)
