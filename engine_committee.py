from __future__ import annotations

import numpy as np
import pandas as pd

from config import *
from utils import _sp, _vs


OBJECTIVE_BUY_LABELS = {"STRONG_BUY", "BUY", "WATCH_BUY"}
OBJECTIVE_SELL_LABELS = {"STRONG_SELL", "SELL", "WATCH_SELL"}


def detect_context_vectorized(df):
    n = len(df)
    idx = df.index
    N = lambda c, d=0: df.get(c, pd.Series(d, index=idx)).fillna(d)
    C = df["Close"]
    wt1 = N("WT1")
    rsi = N("RSI")
    adx = N("ADX")
    pdi = N("Plus_DI")
    mdi = N("Minus_DI")
    cmf = N("CMF")
    obv = N("OBV")
    history_bars = N("History_Bars", 0)
    a50 = (history_bars >= JT.MIN_HISTORY_MA50) & (C > N("MA50", np.nan))
    a200 = (history_bars >= JT.MIN_HISTORY_MA200) & (C > N("MA200", np.nan))
    b50 = (history_bars >= JT.MIN_HISTORY_MA50) & (C < N("MA50", np.nan))
    b200 = (history_bars >= JT.MIN_HISTORY_MA200) & (C < N("MA200", np.nan))
    atr = N("ATR")
    vol_avg = df["Volume"].rolling(50, min_periods=10).mean()
    vr = df["Volume"] / (vol_avg + 1e-10)
    obv_ma = obv.rolling(10, min_periods=5).mean()
    prp = (C.rolling(20).max() - C.rolling(20).min()) / (C.rolling(20).min() + 1e-10)
    flat = prp < 0.08
    ma50s = (N("MA50") - N("MA50").shift(10)) / (N("MA50").shift(10) + 1e-10) * 100
    ctx = np.full(n, CTX_DEFAULT, dtype=int)
    ctx = np.where((adx < 20) & flat, CTX_RANGING, ctx)
    ctx = np.where(flat & (cmf < -0.05) & (obv < obv_ma) & (vr >= 0.7), CTX_DISTRIBUTION, ctx)
    ctx = np.where(flat & (cmf > 0.05) & (obv > obv_ma) & (vr >= 0.7), CTX_ACCUMULATION, ctx)
    ctx = np.where((adx > 30) & (mdi > pdi) & b50 & b200, CTX_STRONG_DN, ctx)
    ctx = np.where((adx > 30) & (pdi > mdi) & a50 & a200, CTX_STRONG_UP, ctx)
    ctx = np.where((wt1 > 60) | (rsi > 75) | ((wt1 > 50) & (rsi > 70) & (N("MFI") > 75)), CTX_EXTREME_OB, ctx)
    ctx = np.where((wt1 < -60) | (rsi < 25) | ((wt1 < -50) & (rsi < 30) & (N("MFI") < 25)), CTX_EXTREME_OS, ctx)
    ctx = np.where((ma50s < 0) & (ma50s > ma50s.shift(5)) & flat & (cmf > 0), CTX_BOTTOMING, ctx)
    ctx = np.where((ma50s > 0) & (ma50s < ma50s.shift(5)) & flat & (cmf < 0), CTX_TOPPING, ctx)
    ctx = np.where((vr < 0.5) & (N("BB_Width") < N("BB_Width").rolling(60, min_periods=30).quantile(0.1)), CTX_VOL_DRY, ctx)
    wb = (df["High"] - df["Low"]) > atr * 2
    pe = wb.shift(1).fillna(False) | wb.shift(2).fillna(False)
    ctx = np.where(pe & ~wb, CTX_POST_EXPLOSION, ctx)
    return pd.Series(ctx, index=idx)


def stabilize_context_sequence(df, raw_ctx):
    idx = df.index
    N = lambda c, d=0: df.get(c, pd.Series(d, index=idx)).fillna(d)
    stable = raw_ctx.astype(int).values.copy()
    raw_vals = raw_ctx.astype(int).values
    if len(stable) <= 1:
        return pd.Series(stable, index=idx)
    C = df["Close"].values
    adx = N("ADX", 0).values
    pdi = N("Plus_DI", 0).values
    mdi = N("Minus_DI", 0).values
    cmf = N("CMF", 0).values
    wt1 = N("WT1", 0).values
    rsi = N("RSI", 50).values
    history_bars = N("History_Bars", 0).values
    ma50 = N("MA50", np.nan).values
    ma200 = N("MA200", np.nan).values
    obv = N("OBV", 0).values
    obv_ma = N("OBV", 0).rolling(10, min_periods=5).mean().values
    trend_inflect_bull = N("Trend_Inflection_Bull", False).values.astype(bool)
    trend_inflect_bear = N("Trend_Inflection_Bear", False).values.astype(bool)
    market_turn_bull = N("Market_Turn_Bull", False).values.astype(bool)
    market_turn_bear = N("Market_Turn_Bear", False).values.astype(bool)
    for i in range(1, len(stable)):
        prev = stable[i - 1]
        cur = raw_vals[i]
        if cur == prev:
            continue
        above50 = bool((history_bars[i] >= JT.MIN_HISTORY_MA50) and np.isfinite(ma50[i]) and C[i] > ma50[i])
        above200 = bool((history_bars[i] >= JT.MIN_HISTORY_MA200) and np.isfinite(ma200[i]) and C[i] > ma200[i])
        below50 = bool((history_bars[i] >= JT.MIN_HISTORY_MA50) and np.isfinite(ma50[i]) and C[i] < ma50[i])
        below200 = bool((history_bars[i] >= JT.MIN_HISTORY_MA200) and np.isfinite(ma200[i]) and C[i] < ma200[i])
        obv_support = bool(np.isfinite(obv_ma[i]) and obv[i] >= obv_ma[i])
        obv_pressure = bool(np.isfinite(obv_ma[i]) and obv[i] <= obv_ma[i])
        if prev == CTX_STRONG_UP and cur in (CTX_DEFAULT, CTX_RANGING, CTX_EXTREME_OB):
            trend_intact = (adx[i] >= JT.CONTEXT_HOLD_ADX) and (pdi[i] >= mdi[i]) and above50 and above200
            if trend_intact and (rsi[i] >= 52) and (wt1[i] >= -15) and not trend_inflect_bear[i] and not market_turn_bear[i]:
                stable[i] = prev
                continue
        if prev == CTX_STRONG_DN and cur in (CTX_DEFAULT, CTX_RANGING, CTX_EXTREME_OS):
            trend_intact = (adx[i] >= JT.CONTEXT_HOLD_ADX) and (mdi[i] >= pdi[i]) and below50 and below200
            if trend_intact and (rsi[i] <= 48) and (wt1[i] <= 15) and not trend_inflect_bull[i] and not market_turn_bull[i]:
                stable[i] = prev
                continue
        if prev == CTX_ACCUMULATION and cur == CTX_DEFAULT:
            if (cmf[i] >= 0.03) and obv_support and not trend_inflect_bear[i]:
                stable[i] = prev
                continue
        if prev == CTX_DISTRIBUTION and cur == CTX_DEFAULT:
            if (cmf[i] <= -0.03) and obv_pressure and not trend_inflect_bull[i]:
                stable[i] = prev
                continue
        if prev == CTX_BOTTOMING and cur == CTX_EXTREME_OS:
            if (cmf[i] >= -0.02) and (wt1[i] > wt1[i - 1]) and (rsi[i] >= rsi[i - 1]):
                stable[i] = prev
                continue
        if prev == CTX_TOPPING and cur == CTX_EXTREME_OB:
            if (cmf[i] <= 0.02) and (wt1[i] < wt1[i - 1]) and (rsi[i] <= rsi[i - 1]):
                stable[i] = prev
                continue
    return pd.Series(stable, index=idx)


def committee_trend(df, N):
    C = df["Close"]
    idx = df.index
    score = pd.Series(0.0, index=idx)
    history_bars = N("History_Bars", 0)
    a200 = (history_bars >= JT.MIN_HISTORY_MA200) & (C > N("MA200", np.nan))
    a50 = (history_bars >= JT.MIN_HISTORY_MA50) & (C > N("MA50", np.nan))
    a20 = C > N("MA20", np.nan)
    b200 = (history_bars >= JT.MIN_HISTORY_MA200) & (C < N("MA200", np.nan))
    b50 = (history_bars >= JT.MIN_HISTORY_MA50) & (C < N("MA50", np.nan))
    b20 = C < N("MA20", np.nan)
    score += a200.astype(float) * 10 + a50.astype(float) * 10 + a20.astype(float) * 10
    score -= b200.astype(float) * 10 + b50.astype(float) * 10 + b20.astype(float) * 10
    ma50s = (N("MA50") - N("MA50").shift(10)) / (N("MA50").shift(10) + 1e-10) * 100
    score += np.clip(ma50s * 3, -15, 15)
    adx_val = N("ADX")
    pdi = N("Plus_DI")
    mdi = N("Minus_DI")
    di_diff = pdi - mdi
    score += np.where(adx_val > 25, np.clip(di_diff * 0.5, -15, 15), np.clip(di_diff * 0.2, -5, 5))
    score += np.where(N("ST_Direction") == 1, 10, np.where(N("ST_Direction") == -1, -10, 0))
    senkou_a = N("Ichimoku_SenkouA", np.nan)
    senkou_b = N("Ichimoku_SenkouB", np.nan)
    kumo_ready = senkou_a.notna() & senkou_b.notna()
    kt = pd.concat([senkou_a, senkou_b], axis=1).max(axis=1)
    kb = pd.concat([senkou_a, senkou_b], axis=1).min(axis=1)
    score += np.where(kumo_ready & (C > kt), 10, np.where(kumo_ready & (C < kb), -10, 0))
    atr = N("ATR")
    d50 = (C - N("MA50")) / (atr + 1e-10)
    d200 = (C - N("MA200")) / (atr + 1e-10)
    d50_score = np.where(d50 >= 0, np.clip(np.minimum(d50, 2.5) * 2.0, 0, 5) - np.clip((d50 - 4.0) * 3.0, 0, 8), -np.clip(np.abs(d50) * 3.2, 0, 14))
    d200_score = np.where(d200 >= 0, np.clip(np.minimum(d200, 3.0) * 1.5, 0, 4.5) - np.clip((d200 - 5.0) * 2.0, 0, 6), -np.clip(np.abs(d200) * 2.8, 0, 12))
    score += d50_score
    score += d200_score
    wt1 = N("WT1")
    rsi = N("RSI")
    score += np.where((wt1 < -60) & (wt1 > wt1.shift(1)), 10, 0) + np.where((wt1 > 60) & (wt1 < wt1.shift(1)), -10, 0)
    score += np.where((rsi < 35) & (rsi > rsi.shift(1)), 6, 0) + np.where((rsi > 65) & (rsi < rsi.shift(1)), -6, 0)
    ma50a = ma50s - ma50s.shift(5)
    score += np.where((ma50s < 0) & (ma50a > 0.5), 8, 0) + np.where((ma50s > 0) & (ma50a < -0.5), -8, 0)
    score += np.clip((N("Trend_Inflection_Buy_Score", 0) * JT.TREND_INFLECTION_COMMITTEE_BUY_W) - (N("Trend_Inflection_Sell_Score", 0) * JT.BEAR_TURN_SCORE_SCALE * JT.TREND_INFLECTION_COMMITTEE_SELL_W), -24, 24)
    score += np.clip((N("Market_Turn_Bull_Score", 0) * 3) - (N("Market_Turn_Bear_Score", 0) * JT.MARKET_TURN_BEAR_SCALE * 3), -12, 12)
    ns = (score / JT.TREND_NORM * 100).clip(-100, 100)
    conv = np.clip(adx_val.values * 2, 5, 95)
    wt1v = wt1.values
    rsiv = rsi.values
    eos = np.clip((-50 - wt1v) / 30, 0, 1) * 0.7 + np.clip((30 - rsiv) / 20, 0, 1) * 0.3
    eob = np.clip((wt1v - 50) / 30, 0, 1) * 0.7 + np.clip((rsiv - 70) / 20, 0, 1) * 0.3
    conv = conv * (1 - np.maximum(eos, eob) * 0.8)
    conv = np.clip(conv, 5, 95)
    conv = np.clip(conv + np.maximum(N("Trend_Inflection_Buy_Score", 0).values, N("Trend_Inflection_Sell_Score", 0).values) * 4 + np.maximum(N("Market_Turn_Bull_Score", 0).values, N("Market_Turn_Bear_Score", 0).values) * 2, 5, 95)
    return ns, pd.Series(conv, index=idx)


def committee_momentum(df, N):
    idx = df.index
    score = pd.Series(0.0, index=idx)
    rsi = N("RSI")
    wt1 = N("WT1")
    wt2 = N("WT2")
    mh = N("MACD_Hist")
    stk = N("StochK")
    std = N("StochD")
    ca = N("Composite_Accel")
    score += (rsi - 50) * 0.6 + np.where(rsi > rsi.shift(1), 5, np.where(rsi < rsi.shift(1), -5, 0))
    score += wt1 * 0.3 + np.where(wt1 > wt2, 8, np.where(wt1 < wt2, -8, 0)) + np.where(wt1 > wt1.shift(1), 5, np.where(wt1 < wt1.shift(1), -5, 0))
    score += np.where(mh > mh.shift(1), 8, np.where(mh < mh.shift(1), -8, 0)) + np.where(mh > 0, 5, np.where(mh < 0, -5, 0))
    score += (stk - 50) * 0.2 + np.where((stk > std) & (stk < 30), 10, np.where((stk < std) & (stk > 70), -10, 0))
    score += np.clip(ca * JT.ACCEL_COMMITTEE_MOM, -12, 12)
    wv = wt1.values
    rv = rsi.values
    mv = N("MFI").values
    mhv = mh.values
    wtu = (wv < -30) & (wv > np.roll(wv, 1))
    wtd = (wv > 30) & (wv < np.roll(wv, 1))
    rtu = (rv < 40) & (rv > np.roll(rv, 1))
    rtd = (rv > 60) & (rv < np.roll(rv, 1))
    bp = wtu.astype(float) + rtu.astype(float) + (mv < 35).astype(float) + (mhv > np.roll(mhv, 1)).astype(float)
    brp = wtd.astype(float) + rtd.astype(float) + (mv > 65).astype(float) + (mhv < np.roll(mhv, 1)).astype(float)
    score += np.clip((bp - 1) * 8.5, 0, 30) - np.clip((brp - 1) * 8.5, 0, 30)
    score += np.where((wv < -70) & (wv > np.roll(wv, 1)), 20, 0) + np.where((wv > 70) & (wv < np.roll(wv, 1)), -20, 0)
    ns = (score / JT.MOMENTUM_NORM * 100).clip(-100, 100)
    ext = np.maximum(np.clip((-wt1.values - 30) / 40, 0, 1), np.clip((wt1.values - 30) / 40, 0, 1))
    tb = np.where(wtu | wtd, 20, 0)
    pb = np.where(bp >= 3, 15, np.where(brp >= 3, 15, 0))
    conv = np.clip(40 + ext * 50 + tb + pb, 15, 98)
    return ns, pd.Series(conv, index=idx)


def committee_money(df, N):
    idx = df.index
    C = df["Close"]
    score = pd.Series(0.0, index=idx)
    cmf = N("CMF")
    obv = N("OBV")
    obv_ma = obv.rolling(20, min_periods=10).mean()
    F = lambda c: df.get(c, pd.Series(False, index=idx)).fillna(False)
    score += np.clip(cmf * 100, -30, 30)
    obv_r = (obv - obv_ma) / (obv_ma.abs() + 1e-10) * 100
    score += np.clip(obv_r * 0.3, -20, 20)
    ou = _vs(obv > obv.shift(1))
    od = _vs(obv < obv.shift(1))
    score += np.where(ou >= 5, 10, np.where(od >= 5, -10, 0))
    score += (N("MFI") - 50) * 0.5 + np.clip(N("RSI_MFI") * 0.8, -15, 15)
    vol = df["Volume"]
    va = vol.rolling(50, min_periods=10).mean()
    vr = vol / (va + 1e-10)
    pd_ = np.where(C > C.shift(1), 1, np.where(C < C.shift(1), -1, 0))
    score += np.clip(vr * 7.5, 0, 20) * pd_
    score += np.clip(N("OBV_Slope") * 12, -15, 15)
    score += np.where(F("Smart_Money_Bullish_Div"), 12, 0) - np.where(F("Smart_Money_Bearish_Div"), 16, 0)
    score -= np.where((N("Price_Slope_5") > 0) & F("Low_Volume_Caution"), 8, 0)
    score -= np.where(F("Thin_Trade_Risk") & (N("Price_Slope_5") > 0), 10, 0)
    ns = (score / JT.MONEY_NORM * 100).clip(-100, 100)
    vc = np.clip(vr.values * 30, 10, 60)
    cc = np.clip(np.abs(cmf.values) * 100, 0, 30)
    divc = np.where(F("Smart_Money_Bullish_Div") | F("Smart_Money_Bearish_Div"), 10, 0)
    conv = np.clip(vc + cc + divc, 10, 95)
    return ns, pd.Series(conv, index=idx)


def committee_structure(df, N):
    idx = df.index
    C = df["Close"]
    O = df["Open"]
    score = pd.Series(0.0, index=idx)
    pb = N("Percent_B")
    score += np.clip((0.5 - pb) * 40, -25, 25)
    score += np.where((pb < 0.1) & (C > O), 10, 0) + np.where((pb > 0.9) & (C < O), -10, 0)
    poc = N("VP_POC")
    vah = N("VP_VAH")
    val_ = N("VP_VAL")
    dp = (C - poc) / (poc + 1e-10) * 100
    va_vol = df["Volume"].rolling(50, min_periods=10).mean()
    vr_str = df["Volume"] / (va_vol + 1e-10)
    vp_scalar = np.clip(vr_str.rolling(5).mean().fillna(1.0), 0.5, 2.0)
    score += np.clip((3 - dp.abs()) * 2, -5, 10) * vp_scalar
    score += np.where(((C - val_).abs() / (C + 1e-10) < 0.02) & (C > O), 10, 0) + np.where(((vah - C).abs() / (C + 1e-10) < 0.02) & (C < O), -10, 0)
    F = lambda c: df.get(c, pd.Series(False, index=idx)).fillna(False)
    cb = F("Morning_Star").astype(float) * 20 + F("Bullish_Engulfing").astype(float) * 15 + F("Hammer").astype(float) * 12 + F("Outside_Bullish").astype(float) * 10 + F("Doji_Bullish").astype(float) * 5 + F("Three_Bar_Reversal_Buy").astype(float) * 15
    cs = F("Evening_Star").astype(float) * 20 + F("Bearish_Engulfing").astype(float) * 15 + F("Shooting_Star").astype(float) * 12 + F("Outside_Bearish").astype(float) * 10 + F("Doji_Bearish").astype(float) * 5 + F("Three_Bar_Reversal_Sell").astype(float) * 15
    score += cb - cs + np.where(F("BB_Squeeze_End_Bull"), 15, np.where(F("BB_Squeeze_End_Bear"), -15, 0))
    score += np.where(F("Gap_Down_Closed") & (C > O), 10, 0) - np.where(F("Gap_Up_Closed") & (C < O), 10, 0)
    score += F("Multiple_Ten_Bull").astype(float) * 5 - F("Multiple_Ten_Bear").astype(float) * 5
    score += np.where(F("Three_Weeks_Tight") & (C > O) & (pb > 0.55), 8, 0) - np.where(F("Parabolic_Rise") & (C < O), 10, 0)
    score += _sp(df, "Diag_Support_Hold", 7) + _sp(df, "Diag_Breakout_Bull", 9) - _sp(df, "Diag_Resistance_Reject", 7) - _sp(df, "Diag_Breakdown_Bear", 9)
    score += _sp(df, "Box_Support_Hold", 7) + _sp(df, "Channel_Support_Hold", 8) + _sp(df, "Box_Breakout_Bull", 9) + _sp(df, "Channel_Breakout_Bull", 10) + _sp(df, "Triangle_Breakout_Bull", 11)
    score -= _sp(df, "Box_Resistance_Reject", 7) + _sp(df, "Channel_Resistance_Reject", 8) + _sp(df, "Box_Breakdown_Bear", 9) + _sp(df, "Channel_Breakdown_Bear", 10) + _sp(df, "Triangle_Breakdown_Bear", 11)
    score += _sp(df, "Fib_382_Support", 4) + _sp(df, "Fib_50_Support", 5) + _sp(df, "Fib_618_Support", 7) + _sp(df, "Fib_618_Reclaim", 8) + _sp(df, "Fib_Confluence_Buy", 9)
    score -= _sp(df, "Fib_382_Resistance", 4) + _sp(df, "Fib_50_Resistance", 5) + _sp(df, "Fib_618_Resistance", 7) + _sp(df, "Fib_618_Breakdown", 8) + _sp(df, "Fib_Confluence_Sell", 9)
    score += np.where(F("Asc_Triangle") & (C > O), 5, 0) - np.where(F("Desc_Triangle") & (C < O), 5, 0)
    score += np.where(F("Sym_Triangle") & (C > O), 2.5, np.where(F("Sym_Triangle") & (C < O), -2.5, 0))
    score += N("Upside_Space_Score")
    score += np.clip((N("VP_Long_RR") - JT.VP_RR_FLOOR) * 12, -18, 10)
    score -= np.clip((N("VP_Short_RR") - JT.VP_RR_FLOOR) * 12, 0, 12)
    ns = (score / JT.STRUCTURE_NORM * 100).clip(-100, 100)
    ne = (
        (pb < 0.2).astype(float)
        + (pb > 0.8).astype(float)
        + (cb > 0).astype(float)
        + (cs > 0).astype(float)
        + (((C - val_).abs() / (C + 1e-10) < 0.03) | ((vah - C).abs() / (C + 1e-10) < 0.03)).astype(float)
        + F("BB_Squeeze_End_Bull").astype(float)
        + F("BB_Squeeze_End_Bear").astype(float)
        + (N("VP_Long_RR") > JT.VP_RR_STRONG).astype(float)
        + (N("VP_Short_RR") > JT.VP_RR_STRONG).astype(float)
        + F("Gap_Down_Closed").astype(float)
        + F("Gap_Up_Closed").astype(float)
        + F("Three_Weeks_Tight").astype(float)
        + F("Box_Breakout_Bull").astype(float)
        + F("Box_Breakdown_Bear").astype(float)
        + F("Channel_Breakout_Bull").astype(float)
        + F("Channel_Breakdown_Bear").astype(float)
        + F("Triangle_Breakout_Bull").astype(float)
        + F("Triangle_Breakdown_Bear").astype(float)
        + F("Fib_618_Support").astype(float)
        + F("Fib_618_Breakdown").astype(float)
        + F("Fib_Confluence_Buy").astype(float)
        + F("Fib_Confluence_Sell").astype(float)
    )
    conv = np.clip(ne.values * 20 + 15, 10, 90)
    return ns, pd.Series(conv, index=idx)


def committee_leading(df, N):
    idx = df.index
    score = pd.Series(0.0, index=idx)
    ut = N("UTBot_Dir")
    hma = df.get("HMA_Rising", pd.Series(False, index=idx)).fillna(False)
    score += np.where(ut == 1, 20, np.where(ut == -1, -20, 0)) + np.where(hma, 15, -15)
    sq = N("Squeeze_Momentum")
    sr = df.get("Squeeze_Mom_Rising", pd.Series(False, index=idx)).fillna(False)
    score += np.where(sq > 0, 10, np.where(sq < 0, -10, 0)) + np.where((sq > 0) & sr, 5, np.where((sq < 0) & ~sr, -5, 0))
    ca = N("Composite_Accel")
    score += np.clip(ca * JT.ACCEL_COMMITTEE_LEAD, -16, 16)
    spb = N("Setup_Pressure_Buy")
    sps = N("Setup_Pressure_Sell")
    score += np.clip(spb * 2, 0, 20) - np.clip(sps * 2, 0, 20)
    F = lambda c: df.get(c, pd.Series(False, index=idx)).fillna(False)
    sq_pos = F("Squeeze_Mom_Positive")
    ut_stop_gap = (df["Close"] - N("UTBot_Stop", np.nan)) / (N("ATR") + 1e-10)
    ut_valid = ut_stop_gap.replace([np.inf, -np.inf], np.nan).notna()
    ut_support_buy = ut_valid & (ut_stop_gap >= 0) & (ut_stop_gap <= JT.UTBOT_SUPPORT_MAX_ATR) & (ut == 1)
    ut_support_sell = ut_valid & (ut_stop_gap <= 0) & ((-ut_stop_gap) <= JT.UTBOT_SUPPORT_MAX_ATR) & (ut == -1)
    ut_overheat_buy = ut_valid & (ut_stop_gap >= JT.UTBOT_OVERHEAT_ATR)
    ut_overheat_sell = ut_valid & ((-ut_stop_gap) >= JT.UTBOT_OVERHEAT_ATR)
    score += np.where(sq_pos & (sq > 0), 6, np.where((~sq_pos) & (sq < 0), -6, 0))
    score += np.where(F("Pocket_Pivot"), 10, 0) + np.where(F("Pocket_Pivot") & F("Three_Weeks_Tight"), 8, 0)
    score += np.where(F("Gap_Down_Closed") & (F("Pocket_Pivot") | sq_pos), 10, 0) - np.where(F("Gap_Up_Closed") & (F("Parabolic_Rise") | F("Volume_Surge")), 12, 0)
    score += F("Multiple_Ten_Bull").astype(float) * 4 - F("Multiple_Ten_Bear").astype(float) * 4
    score += np.where(F("Fib_50_Support"), 5, 0) + np.where(F("Fib_618_Support"), 7, 0) + np.where(F("Fib_618_Reclaim"), 8, 0)
    score -= np.where(F("Fib_50_Resistance"), 5, 0) + np.where(F("Fib_618_Resistance"), 7, 0) + np.where(F("Fib_618_Breakdown"), 8, 0)
    score += np.where(F("Fib_Confluence_Buy"), 8, 0) - np.where(F("Fib_Confluence_Sell"), 8, 0)
    score += np.where(F("Box_Support_Hold"), 6, 0) - np.where(F("Box_Resistance_Reject"), 6, 0)
    score += np.where(F("Channel_Support_Hold"), 7, 0) - np.where(F("Channel_Resistance_Reject"), 7, 0)
    score += np.where(F("Box_Breakout_Bull"), 8, 0) - np.where(F("Box_Breakdown_Bear"), 8, 0)
    score += np.where(F("Channel_Breakout_Bull"), 9, 0) - np.where(F("Channel_Breakdown_Bear"), 9, 0)
    score += np.where(F("Triangle_Breakout_Bull"), 10, 0) - np.where(F("Triangle_Breakdown_Bear"), 10, 0)
    score += np.where(F("Triangle_Breakout_Bull") & (F("Pocket_Pivot") | sq_pos), 6, 0) - np.where(F("Triangle_Breakdown_Bear") & (F("Parabolic_Rise") | F("Volume_Surge")), 6, 0)
    score += np.where(ut_support_buy, 8, 0) - np.where(ut_support_sell, 8, 0)
    score -= np.where(ut_overheat_buy, 10, 0)
    score += np.where(ut_overheat_sell, 10, 0)
    score += np.clip((N("Trend_Inflection_Buy_Score", 0) * JT.TREND_INFLECTION_COMMITTEE_BUY_W * 1.05) - (N("Trend_Inflection_Sell_Score", 0) * JT.BEAR_TURN_SCORE_SCALE * JT.TREND_INFLECTION_COMMITTEE_SELL_W), -28, 28)
    score += np.clip((N("Market_Turn_Bull_Score", 0) * 3.5) - (N("Market_Turn_Bear_Score", 0) * JT.MARKET_TURN_BEAR_SCALE * 3.5), -14, 14)
    ma_gap = N("MA20_ATR_Gap")
    score -= np.clip((ma_gap - 1.5) * 8, 0, 20)
    score += np.clip((-ma_gap - 1.5) * 8, 0, 20)
    for cn, cfg in COMBINED_SCAN_REGISTRY.items():
        if cn not in df.columns:
            continue
        pts = {1: 15, 2: 8, 3: 3}.get(cfg["tier"], 3)
        if cfg["dir"] == "buy":
            score += np.where(F(cn), pts, 0)
        elif cfg["dir"] == "sell":
            score -= np.where(F(cn), pts, 0)
    score += np.where(F("VuManChu_Bull"), 20, 0) - np.where(F("VuManChu_Bear"), 20, 0)
    score += np.where(F("Washout_Bottom_Hard"), 35, 0) - np.where(F("Blowoff_Top_Hard"), 45, 0)
    ns = (score / JT.LEADING_NORM * 100).clip(-100, 100)
    ag = (ut == 1).astype(float) + hma.astype(float) + (sq > 0).astype(float) + (ca > 0).astype(float) + ut_support_buy.astype(float) + F("Pocket_Pivot").astype(float) + F("Gap_Down_Closed").astype(float) + F("Box_Support_Hold").astype(float) + F("Channel_Support_Hold").astype(float) + F("Triangle_Breakout_Bull").astype(float) + F("Fib_618_Support").astype(float) + F("Fib_618_Reclaim").astype(float) + F("Fib_Confluence_Buy").astype(float)
    dg = (ut == -1).astype(float) + (~hma).astype(float) + (sq < 0).astype(float) + (ca < 0).astype(float) + ut_support_sell.astype(float) + F("Gap_Up_Closed").astype(float) + F("Parabolic_Rise").astype(float) + F("Box_Resistance_Reject").astype(float) + F("Channel_Resistance_Reject").astype(float) + F("Triangle_Breakdown_Bear").astype(float) + F("Fib_618_Resistance").astype(float) + F("Fib_618_Breakdown").astype(float) + F("Fib_Confluence_Sell").astype(float)
    conv = np.clip(np.maximum(ag.values, dg.values) * 20 + 10 + np.where(F("Blowoff_Top_Hard") | F("Washout_Bottom_Hard"), 12, 0), 10, 90)
    conv = np.clip(conv + np.maximum(N("Trend_Inflection_Buy_Score", 0).values, N("Trend_Inflection_Sell_Score", 0).values) * 4 + np.maximum(N("Market_Turn_Bull_Score", 0).values, N("Market_Turn_Bear_Score", 0).values) * 2, 10, 95)
    return ns, pd.Series(conv, index=idx)


def normalize_weight_rows(wa):
    wa = np.asarray(wa, dtype=float)
    rs = wa.sum(axis=1, keepdims=True)
    rs[rs <= 0] = 1.0
    return wa / rs


def apply_adx_weight_regime(wa, adx_values):
    wa = normalize_weight_rows(wa)
    range_mult = np.array([0.70, 0.95, 1.15, 1.25, 0.95], dtype=float)
    trend_mult = np.array([1.25, 1.20, 0.90, 0.80, 0.95], dtype=float)
    low = np.isfinite(adx_values) & (adx_values < JT.ADX_RANGE_MAX)
    high = np.isfinite(adx_values) & (adx_values > JT.ADX_TREND_MIN)
    if low.any():
        wa[low] *= range_mult
    if high.any():
        wa[high] *= trend_mult
    return normalize_weight_rows(wa)


def downgrade_buy(label, severe=False):
    if severe:
        return "NEUTRAL"
    return {"STRONG_BUY": "BUY", "BUY": "WATCH_BUY", "WATCH_BUY": "NEUTRAL"}.get(label, label)


def downgrade_sell(label, severe=False):
    if severe:
        return "NEUTRAL"
    return {"STRONG_SELL": "SELL", "SELL": "WATCH_SELL", "WATCH_SELL": "NEUTRAL"}.get(label, label)


def promote_buy(label):
    return {"WATCH_BUY": "BUY", "BUY": "STRONG_BUY"}.get(label, label)


def promote_sell(label):
    return {"WATCH_SELL": "SELL", "SELL": "STRONG_SELL"}.get(label, label)


def judgment_side(label):
    text = str(label or "").upper()
    if text in OBJECTIVE_BUY_LABELS:
        return 1
    if text in OBJECTIVE_SELL_LABELS:
        return -1
    return 0


def default_action_label(label):
    return {
        "STRONG_BUY": "강한 매수 / 정렬 최상",
        "BUY": "매수 우위 / 추세 지속",
        "WATCH_BUY": "매수 관찰 / 확인 대기",
        "NEUTRAL": "중립 / 방향성 대기",
        "MIXED": "혼조 / 근거 충돌",
        "WATCH_SELL": "매도 관찰 / 리스크 관리",
        "SELL": "매도 우위 / 하락 정렬",
        "STRONG_SELL": "강한 매도 / 하락 정렬 최상",
    }.get(str(label or "").upper(), "중립 / 방향성 대기")


def append_note(base, extra, sep=" | "):
    left = str(base or "").strip()
    right = str(extra or "").strip()
    if not right:
        return left
    if not left:
        return right
    if right in left:
        return left
    return f"{left}{sep}{right}"


def context_threshold_adjustments(ctx_code):
    buy_adj = 0.0
    sell_adj = 0.0
    if ctx_code == CTX_EXTREME_OS:
        buy_adj -= 10.0
        sell_adj -= 8.0
    elif ctx_code == CTX_EXTREME_OB:
        buy_adj += 8.0
        sell_adj += 10.0
    elif ctx_code == CTX_STRONG_UP:
        buy_adj -= 5.0
        sell_adj -= 5.0
    elif ctx_code == CTX_STRONG_DN:
        buy_adj += 8.0
        sell_adj += 5.0
    elif ctx_code == CTX_ACCUMULATION:
        buy_adj -= 4.0
        sell_adj -= 3.0
    elif ctx_code == CTX_DISTRIBUTION:
        buy_adj += 5.0
        sell_adj += 4.0
    elif ctx_code == CTX_BOTTOMING:
        buy_adj -= 6.0
        sell_adj -= 4.0
    elif ctx_code == CTX_TOPPING:
        buy_adj += 6.0
        sell_adj += 6.0
    return buy_adj, sell_adj


def market_filter_adjustments(
    spy_trend_score,
    breadth_score=0.0,
    risk_on=False,
    risk_off=False,
    breadth_risk_on=False,
    breadth_risk_off=False,
    narrow_leadership=False,
    vix_risk_on=False,
    vix_risk_off=False,
    vix_pressure_score=0.0,
    tnx_tailwind=False,
    tnx_headwind=False,
    tnx_pressure_score=0.0,
    dxy_tailwind=False,
    dxy_headwind=False,
    dxy_pressure_score=0.0,
    leader_stock_mode=False,
):
    buy_adj = 0.0
    sell_adj = 0.0
    bias = np.clip(spy_trend_score * JT.MARKET_ENSEMBLE_SCALE, -6.0, 6.0)
    if risk_off:
        buy_adj += 4.0
        sell_adj += 4.0
        bias -= JT.MARKET_RISK_OFF_PENALTY
    elif risk_on:
        buy_adj -= 4.0
        sell_adj -= 4.0
        bias += JT.MARKET_RISK_ON_BONUS
    elif spy_trend_score >= JT.MARKET_SCORE_TREND_ON:
        buy_adj -= 2.0
        sell_adj -= 2.0
    elif spy_trend_score <= JT.MARKET_SCORE_TREND_OFF:
        buy_adj += 3.0
        sell_adj += 2.0
    bias += np.clip(breadth_score * 0.75, -1.8, 1.8)
    buy_adj -= np.clip(max(breadth_score, 0), 0, 1.0) * 0.35
    buy_adj += np.clip(max(-breadth_score, 0), 0, 1.0) * 0.28
    if breadth_risk_off:
        buy_adj += 1.5
        sell_adj += 1.0
        bias -= 1.6
    elif breadth_risk_on:
        buy_adj -= 2.0
        sell_adj -= 1.0
        bias += 1.2
    if narrow_leadership:
        buy_adj += 0.5
        bias -= 0.8
    if vix_pressure_score:
        buy_adj += np.clip(max(vix_pressure_score, 0) * 0.55, 0, 2.0)
        sell_adj += np.clip(max(vix_pressure_score, 0) * 0.4, 0, 1.4)
        buy_adj -= np.clip(max(-vix_pressure_score, 0) * 0.45, 0, 1.4)
        bias -= np.clip(vix_pressure_score * 0.75, -2.2, 2.2)
    if vix_risk_off:
        buy_adj += 2.5
        sell_adj += 2.0
        bias -= 2.2
    elif vix_risk_on:
        buy_adj -= 2.0
        sell_adj -= 1.0
        bias += 1.5
    if tnx_pressure_score:
        buy_adj += np.clip(max(tnx_pressure_score, 0) * 0.3, 0, 1.1)
        buy_adj -= np.clip(max(-tnx_pressure_score, 0) * 0.25, 0, 0.9)
        bias -= np.clip(tnx_pressure_score * 0.5, -1.5, 1.5)
    if tnx_headwind:
        buy_adj += 1.25
        bias -= 1.1
    elif tnx_tailwind:
        buy_adj -= 1.0
        bias += 0.8
    if dxy_pressure_score:
        buy_adj += np.clip(max(dxy_pressure_score, 0) * 0.3, 0, 1.1)
        sell_adj += np.clip(max(dxy_pressure_score, 0) * 0.25, 0, 0.8)
        buy_adj -= np.clip(max(-dxy_pressure_score, 0) * 0.25, 0, 0.9)
        bias -= np.clip(dxy_pressure_score * 0.45, -1.5, 1.5)
    if dxy_headwind:
        buy_adj += 1.25
        sell_adj += 1.0
        bias -= 1.1
    elif dxy_tailwind:
        buy_adj -= 1.0
        bias += 0.8
    if leader_stock_mode:
        buy_adj -= JT.LEADER_BUY_SUPPORT
        sell_adj -= JT.LEADER_SELL_RELIEF
        if narrow_leadership or breadth_risk_on:
            sell_adj -= 1.0
            bias += 0.8
    return np.clip(buy_adj, -12.0, 12.0), np.clip(sell_adj, -12.0, 12.0), np.clip(bias, -12.0, 12.0)
