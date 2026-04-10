# -*- coding: utf-8 -*-
from __future__ import annotations

import numpy as np
import pandas as pd

from config import *
from signal_catalog import COOPER_BUY_SIGNAL_KEYS, COOPER_SELL_SIGNAL_KEYS
from utils import _sp, _vs


OBJECTIVE_BUY_LABELS = {"STRONG_BUY", "BUY", "WATCH_BUY"}
OBJECTIVE_SELL_LABELS = {"STRONG_SELL", "SELL", "WATCH_SELL"}


def _finite_array(values, default=0.0):
    return np.nan_to_num(np.asarray(values, dtype=float), nan=default, posinf=default, neginf=default)


def _top_component_notes(components: pd.DataFrame, *, limit: int = 3, score_floor: float = 0.5) -> pd.Series:
    if components is None or components.empty:
        return pd.Series("", index=getattr(components, "index", None), dtype=object)
    labels = list(components.columns)
    values = components.fillna(0.0).to_numpy(dtype=float)
    notes: list[str] = []
    for row in values:
        ranked = sorted(
            ((float(row[idx]), labels[idx]) for idx in range(len(labels)) if float(row[idx]) >= score_floor),
            key=lambda item: item[0],
            reverse=True,
        )
        notes.append("; ".join(f"{label} {score:.0f}" for score, label in ranked[:limit]))
    return pd.Series(notes, index=components.index, dtype=object)


def _active_flag_notes(flags: pd.DataFrame, *, limit: int = 4) -> pd.Series:
    if flags is None or flags.empty:
        return pd.Series("", index=getattr(flags, "index", None), dtype=object)
    labels = list(flags.columns)
    values = flags.fillna(False).to_numpy(dtype=bool)
    notes: list[str] = []
    for row in values:
        active = [labels[idx] for idx, flag in enumerate(row) if bool(flag)]
        notes.append("; ".join(active[:limit]))
    return pd.Series(notes, index=flags.index, dtype=object)


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
    pe = wb.shift(1, fill_value=False) | wb.shift(2, fill_value=False)
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


def committee_trend(df, N, bias_profile=None):
    bias_profile = bias_profile or get_bias_profile()
    bear_turn_scale = float(bias_profile.get("bear_turn_score_scale", JT.BEAR_TURN_SCORE_SCALE))
    market_turn_bear_scale = float(bias_profile.get("market_turn_bear_scale", JT.MARKET_TURN_BEAR_SCALE))
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
    score += np.clip((N("Trend_Inflection_Buy_Score", 0) * JT.TREND_INFLECTION_COMMITTEE_BUY_W) - (N("Trend_Inflection_Sell_Score", 0) * bear_turn_scale * JT.TREND_INFLECTION_COMMITTEE_SELL_W), -24, 24)
    score += np.clip((N("Market_Turn_Bull_Score", 0) * 3) - (N("Market_Turn_Bear_Score", 0) * market_turn_bear_scale * 3), -12, 12)
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


def committee_leading(df, N, bias_profile=None):
    bias_profile = bias_profile or get_bias_profile()
    idx = df.index
    score = pd.Series(0.0, index=idx)
    F = lambda c: df.get(c, pd.Series(False, index=idx)).fillna(False).astype(bool)
    close = df["Close"]
    ut = N("UTBot_Dir")
    hma_available = "HMA_Rising" in df.columns
    hma = df.get("HMA_Rising", pd.Series(False, index=idx)).fillna(False).astype(bool)
    hma_down = (~hma) if hma_available else pd.Series(False, index=idx)
    sq = N("Squeeze_Momentum")
    sr = df.get("Squeeze_Mom_Rising", pd.Series(False, index=idx)).fillna(False).astype(bool)
    sq_pos = F("Squeeze_Mom_Positive")
    sq_neg = (sq < 0) & (~sq_pos)
    volume_ratio = N("Volume_Ratio_20", 1.0)
    adx = N("ADX", 0.0)
    rsi = N("RSI", 50.0)
    wt1 = N("WT1", 0.0)
    history_bars = N("History_Bars", 0)
    ma50 = N("MA50", np.nan)
    ma200 = N("MA200", np.nan)
    vwap = N("VWAP", np.nan)
    fixed_vwap = N("Fixed_VWAP", np.nan)
    prev_close = close.shift(1).fillna(close)
    vwap_prev = vwap.shift(1).fillna(vwap)
    fixed_vwap_prev = fixed_vwap.shift(1).fillna(fixed_vwap)
    above_vwap = (close >= vwap).fillna(False)
    below_vwap = (close <= vwap).fillna(False)
    above_fixed_vwap = (close >= fixed_vwap).fillna(False)
    below_fixed_vwap = (close <= fixed_vwap).fillna(False)
    vwap_reclaim_buy = F("VWAP_Bounce_Buy") | (above_vwap & (prev_close <= vwap_prev))
    vwap_reclaim_sell = F("VWAP_Reject_Sell") | (below_vwap & (prev_close >= vwap_prev))
    fixed_vwap_hold_buy = above_fixed_vwap & (fixed_vwap >= fixed_vwap_prev)
    fixed_vwap_hold_sell = below_fixed_vwap & (fixed_vwap <= fixed_vwap_prev)
    above_ma50 = (history_bars >= JT.MIN_HISTORY_MA50) & (close > ma50)
    above_ma200 = (history_bars >= JT.MIN_HISTORY_MA200) & (close > ma200)
    below_ma50 = (history_bars >= JT.MIN_HISTORY_MA50) & (close < ma50)
    below_ma200 = (history_bars >= JT.MIN_HISTORY_MA200) & (close < ma200)

    ut_stop_gap = (df["Close"] - N("UTBot_Stop", np.nan)) / (N("ATR") + 1e-10)
    ut_valid = ut_stop_gap.replace([np.inf, -np.inf], np.nan).notna()
    ut_support_buy = ut_valid & (ut_stop_gap >= 0) & (ut_stop_gap <= JT.UTBOT_SUPPORT_MAX_ATR) & (ut == 1)
    ut_support_sell = ut_valid & (ut_stop_gap <= 0) & ((-ut_stop_gap) <= JT.UTBOT_SUPPORT_MAX_ATR) & (ut == -1)
    ut_overheat_buy = ut_valid & (ut_stop_gap >= JT.UTBOT_OVERHEAT_ATR)
    ut_overheat_sell = ut_valid & ((-ut_stop_gap) >= JT.UTBOT_OVERHEAT_ATR)
    bullish_gap_reversal = F("Gap_Down_Closed") & (
        F("Pocket_Pivot")
        | F("Three_Weeks_Tight")
        | F("Box_Support_Hold")
        | F("Channel_Support_Hold")
        | F("Triangle_Breakout_Bull")
        | (sq > 0)
    )
    bearish_gap_failure = F("Gap_Up_Closed") & (
        F("Parabolic_Rise")
        | F("Volume_Surge")
        | F("Box_Breakdown_Bear")
        | F("Channel_Breakdown_Bear")
        | F("Triangle_Breakdown_Bear")
        | (sq < 0)
    )

    def _weighted_signal_score(weight_map: dict[str, float], cap: float) -> pd.Series:
        total = pd.Series(0.0, index=idx)
        for key, weight in weight_map.items():
            total += F(key).astype(float) * float(weight)
        return total.clip(lower=0.0, upper=float(cap))

    cooper_buy_score = _weighted_signal_score(
        {
            "Pullback_123_Bull": 4.0,
            "Setup_180_Bull": 4.0,
            "Boomer_Buy": 4.0,
            "Expansion_BO": 6.0,
            "Expansion_Pivot_Buy": 4.0,
            "Gilligans_Buy": 5.0,
            "Lizard_Bull": 3.0,
            "Slingshot_Bull": 5.0,
        },
        cap=18.0,
    )
    cooper_sell_score = _weighted_signal_score(
        {
            "Pullback_123_Bear": 4.0,
            "Setup_180_Bear": 4.0,
            "Boomer_Sell": 4.0,
            "Expansion_BD": 6.0,
            "Expansion_Pivot_Sell": 4.0,
            "Expansion_Double_Sticks": 5.0,
            "Gilligans_Sell": 5.0,
            "Lizard_Bear": 3.0,
            "Slingshot_Bear": 5.0,
        },
        cap=18.0,
    )

    buy_components = pd.DataFrame(
        {
            "UT Bot aligned": np.where(ut == 1, 22.0, 0.0) + np.where(ut_support_buy, 4.0, 0.0),
            "Hull slope up": hma.astype(float) * 18.0,
            "VuManChu bull": F("VuManChu_Bull").astype(float) * 28.0,
            "VWAP support": (
                above_vwap.astype(float) * 8.0
                + vwap_reclaim_buy.astype(float) * 6.0
                + fixed_vwap_hold_buy.astype(float) * 6.0
            ).clip(upper=20.0),
            "Cooper setups": cooper_buy_score,
            "Confirmation stack": (
                F("CS_Triple_Confirm_Buy").astype(float) * 8.0
                + F("CS_VuManChu_Squeeze_Buy").astype(float) * 8.0
                + F("CS_Cooper_Setup_Buy").astype(float) * 6.0
                + F("Pocket_Pivot").astype(float) * 4.0
                + F("Fib_Confluence_Buy").astype(float) * 4.0
                + bullish_gap_reversal.astype(float) * 5.0
                + np.clip(N("Trend_Inflection_Buy_Score", 0.0) * 2.0, 0, 8)
                + np.clip(N("Market_Turn_Bull_Score", 0.0) * 1.5, 0, 6)
                + np.where(sq_pos & (sq > 0) & sr, 3.0, 0.0)
                + F("Washout_Bottom_Hard").astype(float) * 10.0
            ).clip(upper=22.0),
        },
        index=idx,
    )
    sell_components = pd.DataFrame(
        {
            "UT Bot aligned": np.where(ut == -1, 22.0, 0.0) + np.where(ut_support_sell, 4.0, 0.0),
            "Hull slope down": hma_down.astype(float) * 18.0,
            "VuManChu bear": F("VuManChu_Bear").astype(float) * 28.0,
            "VWAP resistance": (
                below_vwap.astype(float) * 8.0
                + vwap_reclaim_sell.astype(float) * 6.0
                + fixed_vwap_hold_sell.astype(float) * 6.0
            ).clip(upper=20.0),
            "Cooper setups": cooper_sell_score,
            "Confirmation stack": (
                F("CS_Triple_Confirm_Sell").astype(float) * 8.0
                + F("CS_VuManChu_Squeeze_Sell").astype(float) * 8.0
                + F("CS_Cooper_Setup_Sell").astype(float) * 6.0
                + F("Parabolic_Rise").astype(float) * 4.0
                + F("Fib_Confluence_Sell").astype(float) * 4.0
                + bearish_gap_failure.astype(float) * 5.0
                + np.clip(N("Trend_Inflection_Sell_Score", 0.0) * 2.0, 0, 8)
                + np.clip(N("Market_Turn_Bear_Score", 0.0) * 1.5, 0, 6)
                + np.where(sq_neg & (~sr), 3.0, 0.0)
                + F("Blowoff_Top_Hard").astype(float) * 12.0
            ).clip(upper=22.0),
        },
        index=idx,
    )
    buy_raw = buy_components.sum(axis=1)
    sell_raw = sell_components.sum(axis=1)

    buy_penalties = pd.DataFrame(
        {
            "Opposing core conflict": (
                (ut == -1).astype(float) * 6.0
                + hma_down.astype(float) * 5.0
                + F("VuManChu_Bear").astype(float) * 8.0
                + below_vwap.astype(float) * 3.0
                + below_fixed_vwap.astype(float) * 2.0
            ).clip(upper=18.0),
            "Weak ADX / volume": (
                (adx < 18).astype(float) * 6.0
                + (volume_ratio < 0.85).astype(float) * 4.0
                + F("Thin_Trade_Risk").astype(float) * 6.0
            ).clip(upper=14.0),
            "Overheat risk": (
                ut_overheat_buy.astype(float) * 10.0
                + ((rsi >= 70) & (wt1 >= 55)).astype(float) * 6.0
                + F("Blowoff_Top_Hard").astype(float) * 18.0
            ).clip(upper=22.0),
            "Pattern headwind": (
                bearish_gap_failure.astype(float) * 8.0
                + F("Box_Breakdown_Bear").astype(float) * 5.0
                + F("Channel_Breakdown_Bear").astype(float) * 5.0
                + F("Triangle_Breakdown_Bear").astype(float) * 6.0
                + F("Fib_618_Breakdown").astype(float) * 5.0
                + F("Fib_Confluence_Sell").astype(float) * 6.0
            ).clip(upper=18.0),
        },
        index=idx,
    )
    sell_penalties = pd.DataFrame(
        {
            "Opposing core conflict": (
                (ut == 1).astype(float) * 6.0
                + hma.astype(float) * 5.0
                + F("VuManChu_Bull").astype(float) * 8.0
                + above_vwap.astype(float) * 3.0
                + above_fixed_vwap.astype(float) * 2.0
            ).clip(upper=18.0),
            "Weak ADX / volume": (
                (adx < 18).astype(float) * 6.0
                + (volume_ratio < 0.85).astype(float) * 4.0
                + F("Thin_Trade_Risk").astype(float) * 6.0
            ).clip(upper=14.0),
            "Washout risk": (
                ut_overheat_sell.astype(float) * 10.0
                + ((rsi <= 30) & (wt1 <= -55)).astype(float) * 6.0
                + F("Washout_Bottom_Hard").astype(float) * 18.0
            ).clip(upper=22.0),
            "Pattern headwind": (
                bullish_gap_reversal.astype(float) * 8.0
                + F("Box_Support_Hold").astype(float) * 5.0
                + F("Channel_Support_Hold").astype(float) * 5.0
                + F("Triangle_Breakout_Bull").astype(float) * 6.0
                + F("Fib_618_Reclaim").astype(float) * 5.0
                + F("Fib_Confluence_Buy").astype(float) * 6.0
            ).clip(upper=18.0),
        },
        index=idx,
    )

    buy_penalty = buy_penalties.sum(axis=1).clip(lower=0.0, upper=40.0)
    sell_penalty = sell_penalties.sum(axis=1).clip(lower=0.0, upper=40.0)
    buy_score = (buy_raw - buy_penalty).clip(lower=0.0, upper=100.0)
    sell_score = (sell_raw - sell_penalty).clip(lower=0.0, upper=100.0)
    spread = (buy_score - sell_score).clip(lower=-100.0, upper=100.0)

    buy_block = (
        (buy_penalty >= 24.0)
        | (((adx < 16) & (volume_ratio < 0.80)) & (buy_raw >= 40.0))
        | ((buy_penalties["Opposing core conflict"] >= 14.0) & (buy_raw < 75.0))
    )
    sell_block = (
        (sell_penalty >= 24.0)
        | (((adx < 16) & (volume_ratio < 0.80)) & (sell_raw >= 40.0))
        | ((sell_penalties["Opposing core conflict"] >= 14.0) & (sell_raw < 75.0))
    )
    dominant_buy = buy_score >= sell_score
    dominant_penalty = pd.Series(np.where(dominant_buy, buy_penalty, sell_penalty), index=idx)
    dominant_block = pd.Series(np.where(dominant_buy, buy_block, sell_block), index=idx).astype(bool)

    buy_reason_notes = _top_component_notes(buy_components, limit=3, score_floor=3.0)
    sell_reason_notes = _top_component_notes(sell_components, limit=3, score_floor=3.0)
    buy_noise_notes = _active_flag_notes(
        pd.DataFrame(
            {
                "Signal conflict": buy_penalties["Opposing core conflict"] >= 8.0,
                "Weak ADX": adx < 18,
                "Light volume": volume_ratio < 0.85,
                "UTBot overheat": ut_overheat_buy,
                "Pattern headwind": buy_penalties["Pattern headwind"] >= 6.0,
            },
            index=idx,
        )
    )
    sell_noise_notes = _active_flag_notes(
        pd.DataFrame(
            {
                "Signal conflict": sell_penalties["Opposing core conflict"] >= 8.0,
                "Weak ADX": adx < 18,
                "Light volume": volume_ratio < 0.85,
                "UTBot squeeze risk": ut_overheat_sell,
                "Pattern headwind": sell_penalties["Pattern headwind"] >= 6.0,
            },
            index=idx,
        )
    )
    dominant_reasons = pd.Series(np.where(dominant_buy, buy_reason_notes, sell_reason_notes), index=idx)
    dominant_noise_notes = pd.Series(np.where(dominant_buy, buy_noise_notes, sell_noise_notes), index=idx)

    score = spread
    align_buy = (
        (ut == 1).astype(float)
        + hma.astype(float)
        + F("VuManChu_Bull").astype(float)
        + above_vwap.astype(float)
        + above_fixed_vwap.astype(float)
        + (cooper_buy_score > 0).astype(float)
        + (buy_components["Confirmation stack"] >= 8.0).astype(float)
        + above_ma50.astype(float)
        + above_ma200.astype(float)
    )
    align_sell = (
        (ut == -1).astype(float)
        + hma_down.astype(float)
        + F("VuManChu_Bear").astype(float)
        + below_vwap.astype(float)
        + below_fixed_vwap.astype(float)
        + (cooper_sell_score > 0).astype(float)
        + (sell_components["Confirmation stack"] >= 8.0).astype(float)
        + below_ma50.astype(float)
        + below_ma200.astype(float)
    )
    conviction = (
        np.maximum(buy_score.values, sell_score.values) * 0.55
        + np.abs(spread.values) * 0.35
        + np.maximum(align_buy.values, align_sell.values) * 4.0
        - dominant_penalty.values * 0.25
        + np.where(F("Washout_Bottom_Hard") | F("Blowoff_Top_Hard"), 6.0, 0.0)
    )
    conviction = np.clip(conviction, 10.0, 95.0)

    details = {
        "Leading_Buy_Score": buy_score,
        "Leading_Sell_Score": sell_score,
        "Leading_Score_Spread": spread,
        "Leading_Noise_Penalty": dominant_penalty,
        "Leading_Noise_Block": dominant_block,
        "Leading_Buy_Noise_Block": buy_block.astype(bool),
        "Leading_Sell_Noise_Block": sell_block.astype(bool),
        "Leading_Buy_Reasons": buy_reason_notes,
        "Leading_Sell_Reasons": sell_reason_notes,
        "Leading_Core_Reasons": dominant_reasons,
        "Leading_Noise_Flags": dominant_noise_notes,
        "Leading_Cooper_Buy_Count": pd.Series(sum(F(key).astype(int) for key in COOPER_BUY_SIGNAL_KEYS), index=idx),
        "Leading_Cooper_Sell_Count": pd.Series(sum(F(key).astype(int) for key in COOPER_SELL_SIGNAL_KEYS), index=idx),
    }
    return score, pd.Series(conviction, index=idx), details


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
        "STRONG_BUY": "Strong buy bias",
        "BUY": "Buy bias",
        "WATCH_BUY": "Watch buy",
        "NEUTRAL": "Neutral",
        "MIXED": "Mixed signals",
        "WATCH_SELL": "Watch sell",
        "SELL": "Sell bias",
        "STRONG_SELL": "Strong sell bias",
    }.get(str(label or "").upper(), "Neutral")
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
    bias_profile=None,
):
    bias_profile = bias_profile or get_bias_profile()
    leader_buy_support = float(bias_profile.get("leader_buy_support", JT.LEADER_BUY_SUPPORT))
    leader_sell_relief = float(bias_profile.get("leader_sell_relief", JT.LEADER_SELL_RELIEF))
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
        buy_adj -= leader_buy_support
        sell_adj -= leader_sell_relief
        if narrow_leadership or breadth_risk_on:
            sell_adj -= 1.0
            bias += 0.8
    return np.clip(buy_adj, -12.0, 12.0), np.clip(sell_adj, -12.0, 12.0), np.clip(bias, -12.0, 12.0)

def _gen_reason(j,es,ctx,veto,syn,pred,ba,sa,wt1,rsi,mfi,cmf,obv_up,adx,vr,ma50a,ma200a,mh_up,stk,hma_r,ut_dir,sq_on,cms):
    side = str(j or "NEUTRAL").upper()
    ctx_label = CTX_KOR.get(ctx, "context")
    action = default_action_label(side)
    reason_map = {
        "STRONG_BUY": "Broad bullish alignment is confirmed.",
        "BUY": "Bullish evidence is leading overall.",
        "WATCH_BUY": "Bullish setup is forming but still needs confirmation.",
        "STRONG_SELL": "Broad bearish alignment is confirmed.",
        "SELL": "Bearish evidence is leading overall.",
        "WATCH_SELL": "Bearish setup is forming but still needs confirmation.",
        "MIXED": "Bullish and bearish evidence are conflicting.",
        "NEUTRAL": "Directional evidence is still limited.",
    }
    detail_parts = [
        f"context={ctx_label}",
        f"ensemble={es:+.1f}",
        f"agree=B{ba}:S{sa}",
        f"WT={wt1:.0f}",
        f"RSI={rsi:.0f}",
    ]
    if syn:
        detail_parts.append(f"synergy={syn:+.1f}")
    if pred:
        detail_parts.append(f"prediction={pred:+.1f}")
    if veto:
        detail_parts.append(f"veto={veto}")
    detail = " | ".join(detail_parts)
    return reason_map.get(side, "Directional evidence is still limited."), detail, action
def compute_committee_ensemble(df, vol_ratio, hma_r_v, bias_mode=DEFAULT_BIAS_MODE):
    bias_profile = get_bias_profile(bias_mode)
    bias_mode = str(bias_profile.get("name", DEFAULT_BIAS_MODE))
    strong_buy_th = float(bias_profile.get("strong_buy_th", JT.STRONG_BUY_TH))
    buy_th = float(bias_profile.get("buy_th", JT.BUY_TH))
    watch_buy_th = float(bias_profile.get("watch_buy_th", JT.WATCH_BUY_TH))
    strong_sell_th = float(bias_profile.get("strong_sell_th", JT.STRONG_SELL_TH))
    sell_th = float(bias_profile.get("sell_th", JT.SELL_TH))
    watch_sell_th = float(bias_profile.get("watch_sell_th", JT.WATCH_SELL_TH))
    bear_turn_scale = float(bias_profile.get("bear_turn_score_scale", JT.BEAR_TURN_SCORE_SCALE))
    market_turn_bear_scale = float(bias_profile.get("market_turn_bear_scale", JT.MARKET_TURN_BEAR_SCALE))
    idx=df.index;n=len(df);N=lambda c,d=0:df.get(c,pd.Series(d,index=idx)).fillna(d);F=lambda c:df.get(c,pd.Series(False,index=idx)).fillna(False)
    raw_ctx=detect_context_vectorized(df);ctx=stabilize_context_sequence(df,raw_ctx);df['Market_Context']=ctx
    scores={};convictions={}
    scores['Trend'],convictions['Trend']=committee_trend(df,N,bias_profile=bias_profile);scores['Momentum'],convictions['Momentum']=committee_momentum(df,N)
    scores['Money'],convictions['Money']=committee_money(df,N);scores['Structure'],convictions['Structure']=committee_structure(df,N)
    scores['Leading'],convictions['Leading'],leading_details=committee_leading(df,N,bias_profile=bias_profile)
    for column_name, column_values in leading_details.items():
        df[column_name] = column_values
    for cm in COMMITTEE_NAMES:
        scores[cm]=pd.Series(_finite_array(scores[cm].values),index=idx)
        convictions[cm]=pd.Series(_finite_array(convictions[cm].values),index=idx).clip(lower=0,upper=100)
    ctx_v=ctx.values;wa=np.zeros((n,NUM_COMMITTEES))
    for cc,cn in CTX_LABELS.items():
        m=(ctx_v==cc)
        if m.any():wa[m]=CONTEXT_WEIGHTS.get(cn,CONTEXT_WEIGHTS['default'])
    
    wa = pd.DataFrame(wa).ewm(span=3, adjust=False).mean().values
    wa = apply_adx_weight_regime(wa, N('ADX').values)
    wa = _finite_array(wa)
    wt1=N('WT1').values;rsi=N('RSI').values;cmf=N('CMF').values;obv=N('OBV').values;obv_ma=N('OBV').rolling(20,min_periods=10).mean().values;C=df['Close'].values;O=df['Open'].values
    hma_r_arr=np.asarray(pd.Series(hma_r_v,index=idx).fillna(False).astype(bool).values if isinstance(hma_r_v,pd.Series) else np.asarray(hma_r_v,dtype=bool),dtype=bool)
    vr_v=vol_ratio.values;obv_slope_v=N('OBV_Slope').values;price_slope_v=N('Price_Slope_5').values;long_rr_v=N('VP_Long_RR',1.).values;short_rr_v=N('VP_Short_RR',1.).values
    pv_bear_v=F('Smart_Money_Bearish_Div').values;pv_bull_v=F('Smart_Money_Bullish_Div').values;low_vol_v=F('Low_Volume_Caution').values;hard_blowoff_v=F('Blowoff_Top_Hard').values
    spy_trend_score_v=N('SPY_Trend_Score',0.).values;spy_risk_on_v=F('SPY_Risk_On').values;spy_risk_off_v=F('SPY_Risk_Off').values
    breadth_score_v=N('Market_Breadth_Score',0.).values;breadth_risk_on_v=F('Breadth_Risk_On').values;breadth_risk_off_v=F('Breadth_Risk_Off').values;narrow_leadership_v=F('Narrow_Leadership').values
    vix_risk_on_v=F('VIX_Risk_On').values;vix_risk_off_v=F('VIX_Risk_Off').values;vix_pressure_v=N('VIX_Pressure_Score',0.).values
    tnx_tailwind_v=F('TNX_Tailwind').values;tnx_headwind_v=F('TNX_Headwind').values;tnx_pressure_v=N('TNX_Pressure_Score',0.).values
    dxy_tailwind_v=F('DXY_Tailwind').values;dxy_headwind_v=F('DXY_Headwind').values;dxy_pressure_v=N('DXY_Pressure_Score',0.).values
    macro_pressure_v=N('Macro_Pressure_Score',0.).values;thin_trade_v=F('Thin_Trade_Risk').values
    rs_ratio_v=N('RS_Ratio',1.).values;qqq_rs20_v=N('QQQ_RS_20',0.).values;leader_stock_base_v=F('Leader_Stock_Mode').values;leader_stock_score_v=N('Leader_Stock_Score',0.).values
    trend_inflect_buy_score_v=N('Trend_Inflection_Buy_Score',0.).values;trend_inflect_sell_score_v=N('Trend_Inflection_Sell_Score',0.).values
    trend_inflect_bull_v=F('Trend_Inflection_Bull').values;trend_inflect_bear_v=F('Trend_Inflection_Bear').values
    market_turn_bull_score_v=N('Market_Turn_Bull_Score',0.).values;market_turn_bear_score_v=N('Market_Turn_Bear_Score',0.).values
    market_turn_bull_v=F('Market_Turn_Bull').values;market_turn_bear_v=F('Market_Turn_Bear').values
    pocket_pivot_v=F('Pocket_Pivot').values;three_weeks_tight_v=F('Three_Weeks_Tight').values
    gap_up_closed_v=F('Gap_Up_Closed').values;gap_down_closed_v=F('Gap_Down_Closed').values
    volume_surge_v=F('Volume_Surge').values;parabolic_rise_v=F('Parabolic_Rise').values
    multiple_ten_bull_v=F('Multiple_Ten_Bull').values;multiple_ten_bear_v=F('Multiple_Ten_Bear').values
    squeeze_positive_v=F('Squeeze_Mom_Positive').values;vwap_osc_v=N('VWAP_Osc').values
    diag_support_v=F('Diag_Support_Hold').values;diag_breakout_v=F('Diag_Breakout_Bull').values
    diag_reject_v=F('Diag_Resistance_Reject').values;diag_breakdown_v=F('Diag_Breakdown_Bear').values
    box_support_v=F('Box_Support_Hold').values;box_breakout_v=F('Box_Breakout_Bull').values
    box_reject_v=F('Box_Resistance_Reject').values;box_breakdown_v=F('Box_Breakdown_Bear').values
    channel_support_v=F('Channel_Support_Hold').values;channel_breakout_v=F('Channel_Breakout_Bull').values
    channel_reject_v=F('Channel_Resistance_Reject').values;channel_breakdown_v=F('Channel_Breakdown_Bear').values
    triangle_breakout_v=F('Triangle_Breakout_Bull').values;triangle_breakdown_v=F('Triangle_Breakdown_Bear').values
    asc_triangle_v=F('Asc_Triangle').values;desc_triangle_v=F('Desc_Triangle').values;sym_triangle_v=F('Sym_Triangle').values
    fib_382_support_v=F('Fib_382_Support').values;fib_50_support_v=F('Fib_50_Support').values;fib_618_support_v=F('Fib_618_Support').values
    fib_382_resistance_v=F('Fib_382_Resistance').values;fib_50_resistance_v=F('Fib_50_Resistance').values;fib_618_resistance_v=F('Fib_618_Resistance').values
    fib_618_breakdown_v=F('Fib_618_Breakdown').values;fib_618_reclaim_v=F('Fib_618_Reclaim').values
    fib_confluence_buy_v=F('Fib_Confluence_Buy').values;fib_confluence_sell_v=F('Fib_Confluence_Sell').values
    fib_ext_up_hit_v=F('Fib_Ext_1618_Up_Hit').values;fib_ext_down_hit_v=F('Fib_Ext_1618_Down_Hit').values
    ut_v=N('UTBot_Dir').values;ut_stop_gap_v=((C-N('UTBot_Stop',np.nan).values)/(N('ATR').values+1e-10))
    ut_stop_gap_v=np.where(np.isfinite(ut_stop_gap_v),ut_stop_gap_v,np.nan)
    ut_support_buy_v=np.isfinite(ut_stop_gap_v)&(ut_stop_gap_v>=0)&(ut_stop_gap_v<=JT.UTBOT_SUPPORT_MAX_ATR)&(ut_v==1)
    ut_support_sell_v=np.isfinite(ut_stop_gap_v)&(ut_stop_gap_v<=0)&((-ut_stop_gap_v)<=JT.UTBOT_SUPPORT_MAX_ATR)&(ut_v==-1)
    ut_overheat_buy_v=np.isfinite(ut_stop_gap_v)&(ut_stop_gap_v>=JT.UTBOT_OVERHEAT_ATR)
    ut_overheat_sell_v=np.isfinite(ut_stop_gap_v)&((-ut_stop_gap_v)>=JT.UTBOT_OVERHEAT_ATR)
    hull_turn_bull_v=F('Hull_Turn_Bull').values
    hull_turn_bear_v=F('Hull_Turn_Bear').values
    ut_buy_v=F('UTBot_Buy').values
    ut_sell_v=F('UTBot_Sell').values
    leading_buy_score_v=N('Leading_Buy_Score',0.).values
    leading_sell_score_v=N('Leading_Sell_Score',0.).values
    leading_spread_v=N('Leading_Score_Spread',0.).values
    leading_noise_penalty_v=N('Leading_Noise_Penalty',0.).values
    leading_noise_block_v=F('Leading_Noise_Block').values
    leading_buy_noise_block_v=F('Leading_Buy_Noise_Block').values
    leading_sell_noise_block_v=F('Leading_Sell_Noise_Block').values
    leading_reason_v=np.asarray(df.get('Leading_Core_Reasons',pd.Series('',index=idx)).fillna('').astype(str).values,dtype=object)
    leading_noise_flag_v=np.asarray(df.get('Leading_Noise_Flags',pd.Series('',index=idx)).fillna('').astype(str).values,dtype=object)
    continuation_buy_score_v=(
        pocket_pivot_v.astype(int)
        +(three_weeks_tight_v&squeeze_positive_v).astype(int)
        +(multiple_ten_bull_v&(vwap_osc_v>0)).astype(int)
        +(gap_down_closed_v&(pocket_pivot_v|squeeze_positive_v)).astype(int)
        +(diag_support_v|diag_breakout_v).astype(int)
        +(box_support_v|channel_support_v).astype(int)
        +(box_breakout_v|channel_breakout_v|triangle_breakout_v).astype(int)
        +(fib_382_support_v|fib_50_support_v).astype(int)
        +(fib_618_support_v|fib_618_reclaim_v|fib_confluence_buy_v).astype(int)
        +ut_support_buy_v.astype(int)
    )
    continuation_sell_score_v=(
        ((gap_up_closed_v&(volume_surge_v|parabolic_rise_v))|(multiple_ten_bear_v&(vwap_osc_v<0))).astype(int)
        +(gap_up_closed_v&(vwap_osc_v<0)).astype(int)
        +(diag_reject_v|diag_breakdown_v).astype(int)
        +(box_reject_v|channel_reject_v).astype(int)
        +(box_breakdown_v|channel_breakdown_v|triangle_breakdown_v).astype(int)
        +(fib_382_resistance_v|fib_50_resistance_v).astype(int)
        +(fib_618_resistance_v|fib_618_breakdown_v|fib_confluence_sell_v).astype(int)
        +ut_support_sell_v.astype(int)
        +ut_overheat_buy_v.astype(int)
    )
    bullish_gap_reversal_v=gap_down_closed_v&((pocket_pivot_v|three_weeks_tight_v|box_support_v|channel_support_v)&(squeeze_positive_v|(vwap_osc_v>0)|triangle_breakout_v))
    bearish_gap_failure_v=gap_up_closed_v&((volume_surge_v&parabolic_rise_v)|(vwap_osc_v<0)|multiple_ten_bear_v|box_breakdown_v|channel_breakdown_v|triangle_breakdown_v)
    turn_alignment_buy_v=(
        (hull_turn_bull_v&ut_buy_v)
        | (trend_inflect_bull_v&(hull_turn_bull_v|ut_buy_v))
        | (market_turn_bull_v&hull_turn_bull_v&(continuation_buy_score_v>=2))
    )
    turn_alignment_sell_v=(
        ((hull_turn_bear_v&ut_sell_v) | (trend_inflect_bear_v&(hull_turn_bear_v|ut_sell_v)))
        & ((continuation_sell_score_v>=2)|market_turn_bear_v)
    )
    leader_stock_mode_v=(
        leader_stock_base_v
        | (
            (rs_ratio_v>=JT.LEADER_RS_RATIO)
            & (qqq_rs20_v>=JT.LEADER_QQQ_RS_MIN)
            & ((continuation_buy_score_v>=2)|pocket_pivot_v|three_weeks_tight_v|bullish_gap_reversal_v)
            & (~thin_trade_v)
            & ((breadth_score_v>=-0.5)|breadth_risk_on_v|narrow_leadership_v)
        )
    )
    leader_stock_score_v=np.maximum(
        leader_stock_score_v,
        (
            (rs_ratio_v>=JT.LEADER_RS_RATIO).astype(int)
            +(qqq_rs20_v>=JT.LEADER_QQQ_RS_MIN).astype(int)
            +(continuation_buy_score_v>=2).astype(int)
            +(bullish_gap_reversal_v|pocket_pivot_v|three_weeks_tight_v).astype(int)
            +((breadth_score_v>=0)|breadth_risk_on_v|narrow_leadership_v).astype(int)
        )
    )
    df['UTBot_Stop_ATR_Gap']=ut_stop_gap_v
    df['Continuation_Buy_Score']=continuation_buy_score_v
    df['Continuation_Sell_Score']=continuation_sell_score_v
    df['Bullish_Gap_Reversal']=bullish_gap_reversal_v
    df['Bearish_Gap_Failure']=bearish_gap_failure_v
    df['Leader_Stock_Mode']=leader_stock_mode_v
    df['Leader_Stock_Score']=leader_stock_score_v
    df['Fib_Ext_1618_Up_Hit']=fib_ext_up_hit_v
    df['Fib_Ext_1618_Down_Hit']=fib_ext_down_hit_v
    df['Turn_Alignment_Buy']=turn_alignment_buy_v
    df['Turn_Alignment_Sell']=turn_alignment_sell_v
    wt_hook_up=(wt1>np.roll(wt1,1));wt_hook_dn=(wt1<np.roll(wt1,1))
    flat=((pd.Series(C).rolling(20).max()-pd.Series(C).rolling(20).min())/(pd.Series(C).rolling(20).min()+1e-10)<.08).values
    veto_masks={
        'ExOS':((wt1<-60)|(rsi<JT.VETO_EXTREME_RSI_LO))&wt_hook_up,
        'ExOB':((wt1>60)|(rsi>JT.VETO_EXTREME_RSI_HI))&wt_hook_dn,
        'Accum':flat&(cmf>JT.VETO_MONEY_CMF)&(obv>obv_ma),
        'Distrib':flat&(cmf<-JT.VETO_MONEY_CMF)&(obv<obv_ma),
        'Capitul':(((wt1<-60)|(rsi<JT.VETO_EXTREME_RSI_LO))&wt_hook_up)&(vr_v>=3)&(C>O),
        'Blowoff':(((wt1>60)|(rsi>JT.VETO_EXTREME_RSI_HI))&wt_hook_dn)&(vr_v>=3)&(C<O),
        'PVBearDiv':pv_bear_v,
        'PVBullDiv':pv_bull_v,
        'RRLong':(long_rr_v<JT.VP_RR_FLOOR)&(C>=N('VP_POC').values),
        'RRShort':(short_rr_v<JT.VP_RR_FLOOR)&(C<=N('VP_POC').values),
        'HardBlowoff':hard_blowoff_v,
    }
    veto_names=list(veto_masks.keys());vf=np.column_stack([veto_masks[nm] for nm in veto_names])
    df['Veto_Flags']=pd.Series([','.join([veto_names[j] for j in range(len(veto_names)) if vf[i,j]]) for i in range(n)],index=idx)
    sa=np.column_stack([scores[cm].values for cm in COMMITTEE_NAMES]);ca_=np.column_stack([convictions[cm].values for cm in COMMITTEE_NAMES])
    es=sa.copy();ec=ca_.copy();trend_i,mom_i,money_i,struct_i,lead_i=0,1,2,3,4
    om=veto_masks['ExOS'];tsm=np.abs(np.minimum(es[om,trend_i],0));es[om,trend_i]=np.clip(tsm*0.4,0,30);ec[om,trend_i]=np.minimum(ec[om,trend_i],25);ec[om,mom_i]*=1.4;ec[om,money_i]*=1.3;ec[om,lead_i]*=1.3
    obm=veto_masks['ExOB'];tbm=np.abs(np.maximum(es[obm,trend_i],0));es[obm,trend_i]=-np.clip(tbm*0.4,0,30);ec[obm,trend_i]=np.minimum(ec[obm,trend_i],25);ec[obm,mom_i]*=1.4;ec[obm,money_i]*=1.3;ec[obm,lead_i]*=1.3
    for nm in ('Accum','Distrib'):
        mm=veto_masks[nm];es[mm,trend_i]*=0.3;ec[mm,money_i]*=1.5
    cm_=veto_masks['Capitul']
    for ci in range(NUM_COMMITTEES):sm_=np.abs(np.minimum(es[cm_,ci],0));es[cm_,ci]=np.maximum(es[cm_,ci],0)+sm_*0.3
    ec[cm_,mom_i]=np.clip(ec[cm_,mom_i]*1.5,0,98)
    bom=veto_masks['Blowoff']
    for ci in range(NUM_COMMITTEES):bm_=np.abs(np.maximum(es[bom,ci],0));es[bom,ci]=np.minimum(es[bom,ci],0)-bm_*0.3
    ec[bom,mom_i]=np.clip(ec[bom,mom_i]*1.5,0,98)
    pvb=veto_masks['PVBearDiv']
    if pvb.any():
        es[pvb]=np.where(es[pvb]>0,es[pvb]*(1-JT.DIVERGENCE_PENALTY),es[pvb]);es[pvb,money_i]-=12;es[pvb,struct_i]-=6;ec[pvb,money_i]=np.clip(ec[pvb,money_i]*1.2,0,98)
    pvu=veto_masks['PVBullDiv']
    if pvu.any():
        es[pvu]=np.where(es[pvu]<0,es[pvu]*(1-JT.DIVERGENCE_PENALTY),es[pvu]);es[pvu,money_i]+=12;es[pvu,struct_i]+=6;ec[pvu,money_i]=np.clip(ec[pvu,money_i]*1.2,0,98)
    rrl=veto_masks['RRLong']
    if rrl.any():
        es[rrl]=np.where(es[rrl]>0,es[rrl]*0.85,es[rrl]);es[rrl,struct_i]-=16;ec[rrl,struct_i]=np.clip(ec[rrl,struct_i]*1.15,0,98)
    rrs=veto_masks['RRShort']
    if rrs.any():
        es[rrs]=np.where(es[rrs]<0,es[rrs]*0.85,es[rrs]);es[rrs,struct_i]+=16;ec[rrs,struct_i]=np.clip(ec[rrs,struct_i]*1.15,0,98)
    hbo=veto_masks['HardBlowoff']
    if hbo.any():
        es[hbo]=np.where(es[hbo]>0,es[hbo]*0.60,es[hbo]);es[hbo,trend_i]-=15;es[hbo,mom_i]-=20;es[hbo,lead_i]=np.minimum(es[hbo,lead_i],-55);ec[hbo,lead_i]=np.maximum(ec[hbo,lead_i],85)
    es=_finite_array(es)
    ec=np.clip(ec,0,100)
    ec=_finite_array(ec)
    # ?쒕꼫吏
    syn=np.zeros(n);ts_=es[:,0];ms_=es[:,1];mns_=es[:,2];ss_=es[:,3];ls_=es[:,4]
    bc=(ms_>20)&(ls_>10)&(ts_<10);bstr=np.clip((ms_+ls_)*0.15+np.abs(np.minimum(ts_,0))*0.1,0,25)
    syn+=np.where(bc,bstr,0)+np.where(bc&(mns_>5),8,0)+np.where(bc&(ss_>10),5,0)
    brc=(ms_<-20)&(ls_<-10)&(ts_>-10);brstr=np.clip((-ms_-ls_)*0.15+np.abs(np.maximum(ts_,0))*0.1,0,25)
    syn-=np.where(brc,brstr,0)+np.where(brc&(mns_<-5),8,0)+np.where(brc&(ss_<-10),5,0)
    syn=_finite_array(syn)
    df['Reversal_Synergy']=syn
    # ?덉륫
    cav=N('Composite_Accel');ab=np.clip(cav.values*JT.ACCEL_PREDICTION_SCALE,-12,12);mh=N('MACD_Hist');mu=_vs(mh>mh.shift(1));md=_vs(mh<mh.shift(1))
    mb=np.where(mu.values>=3,8,np.where(md.values>=3,-8,0));stk=N('StochK');sb=np.where((stk.values<20)&(stk.values>N('StochD').values),5,np.where((stk.values>80)&(stk.values<N('StochD').values),-5,0))
    pred=_finite_array(ab+mb+sb);df['Prediction_Boost']=pred
    contribs=es*(ec/100.)*wa;ens=contribs.sum(axis=1)+syn+pred
    buy_total_arr=N('Buy_Total').values;sell_total_arr=N('Sell_Total').values
    ba_layers=N('Buy_Active_Layers').values;sa_layers=N('Sell_Active_Layers').values
    layer_edge=buy_total_arr-sell_total_arr
    ens+=np.clip(layer_edge*0.55,-24,24)
    ens+=np.where((ba_layers>=7)&(sa_layers<=2),5,0)
    ens-=np.where((sa_layers>=7)&(ba_layers<=2),5,0)
    conflict_adj=np.clip(np.minimum(ba_layers,sa_layers)*1.3,0,8)
    ens-=np.where(np.abs(layer_edge)<6,conflict_adj,conflict_adj*0.4)
    ens=np.where(veto_masks['PVBearDiv']&(ens>0),ens*(1-JT.DIVERGENCE_PENALTY),ens)
    ens=np.where(veto_masks['PVBullDiv']&(ens<0),ens*(1-JT.DIVERGENCE_PENALTY),ens)
    ens=np.where(veto_masks['RRLong']&(ens>0),ens*0.82,ens)
    ens=np.where(veto_masks['RRShort']&(ens<0),ens*0.82,ens)
    ens=np.where(veto_masks['HardBlowoff']&(ens>0),ens-22,ens)
    ens+=np.where(trend_inflect_buy_score_v>=JT.TREND_INFLECTION_STRONG,np.clip((trend_inflect_buy_score_v-(JT.TREND_INFLECTION_STRONG-1))*JT.TREND_INFLECTION_SIGNAL_BONUS,0,12),0)
    ens-=np.where(trend_inflect_sell_score_v>=JT.TREND_INFLECTION_STRONG,np.clip((trend_inflect_sell_score_v-(JT.TREND_INFLECTION_STRONG-1))*JT.TREND_INFLECTION_SIGNAL_BONUS*bear_turn_scale,0,9),0)
    ens+=np.where(market_turn_bull_v,np.clip(market_turn_bull_score_v*JT.MARKET_TURN_SIGNAL_BONUS,0,10),0)
    ens-=np.where(market_turn_bear_v,np.clip(market_turn_bear_score_v*JT.MARKET_TURN_SIGNAL_BONUS*market_turn_bear_scale,0,8),0)
    ens+=np.where(turn_alignment_buy_v,JT.TURN_ALIGNMENT_BONUS_BUY,0)
    ens-=np.where(turn_alignment_sell_v,JT.TURN_ALIGNMENT_BONUS_SELL,0)
    ens+=np.where(continuation_buy_score_v>=2,np.clip((continuation_buy_score_v-1)*JT.CONTINUATION_SIGNAL_BONUS,0,12),0)
    ens-=np.where(continuation_sell_score_v>=2,np.clip((continuation_sell_score_v-1)*JT.CONTINUATION_SIGNAL_BONUS,0,12),0)
    ens=np.where(bearish_gap_failure_v&(ens>0),ens-JT.TRAP_SIGNAL_PENALTY,ens)
    ens=np.where(bullish_gap_reversal_v&(ens<0),ens+JT.TRAP_SIGNAL_PENALTY*0.85,ens)
    ens=np.where(ut_overheat_buy_v&(ens>0),ens-4.5,ens)
    ens=np.where(ut_overheat_sell_v&(ens<0),ens+4.5,ens)
    ens=np.where(fib_ext_up_hit_v&(ens>0),ens-2.5,ens)
    ens=np.where(fib_ext_down_hit_v&(ens<0),ens+2.0,ens)
    ensemble_fallback=np.clip(layer_edge*0.55,-100,100)
    ens=np.where(np.isfinite(ens),ens,ensemble_fallback)
    ens=_finite_array(ens)
    market_buy_adj=np.zeros(n);market_sell_adj=np.zeros(n);market_bias=np.zeros(n)
    for i in range(n):
        market_buy_adj[i],market_sell_adj[i],market_bias[i]=market_filter_adjustments(
            float(spy_trend_score_v[i]),
            float(breadth_score_v[i]),
            bool(spy_risk_on_v[i]),
            bool(spy_risk_off_v[i]),
            bool(breadth_risk_on_v[i]),
            bool(breadth_risk_off_v[i]),
            bool(narrow_leadership_v[i]),
            bool(vix_risk_on_v[i]),
            bool(vix_risk_off_v[i]),
            float(vix_pressure_v[i]),
            bool(tnx_tailwind_v[i]),
            bool(tnx_headwind_v[i]),
            float(tnx_pressure_v[i]),
            bool(dxy_tailwind_v[i]),
            bool(dxy_headwind_v[i]),
            float(dxy_pressure_v[i]),
            bool(leader_stock_mode_v[i]),
            bias_profile=bias_profile,
        )
    df['Bias_Mode']=bias_mode
    df['Market_Filter_Bias']=market_bias
    for ci,cm in enumerate(COMMITTEE_NAMES):
        s=es[:,ci];c=ec[:,ci];v=np.full(n,0,dtype=int);v=np.where((s>15)&(c>=25),1,v);v=np.where((s<-15)&(c>=25),-1,v);v=np.where(c<15,-99,v)
        df[f'CM_{cm}_Vote']=v;df[f'CM_{cm}_EffScore']=es[:,ci];df[f'CM_{cm}_EffConv']=ec[:,ci]
    df['Ensemble_Score']=ens
    # ?먮떒
    bag=np.zeros(n,dtype=int);sag=np.zeros(n,dtype=int)
    for ci in range(NUM_COMMITTEES):bag+=((es[:,ci]>15)&(ec[:,ci]>=25)).astype(int);sag+=((es[:,ci]<-15)&(ec[:,ci]>=25)).astype(int)
    bag+=((ba_layers>=6)&(buy_total_arr>=20)).astype(int)
    sag+=((sa_layers>=6)&(sell_total_arr>=20)).astype(int)
    j=np.full(n,'NEUTRAL',dtype=object);pre_veto_j=np.full(n,'NEUTRAL',dtype=object);conf=np.zeros(n,dtype=float)
    downgrade_count=np.zeros(n,dtype=int);macro_risk_off_count_arr=np.zeros(n,dtype=int);macro_risk_on_count_arr=np.zeros(n,dtype=int);flip_guard_triggered=np.zeros(n,dtype=bool)
    rs=[];rd=[];al=[];contrast_notes=[]
    obv_v=N('OBV').values;obv_mav=N('OBV').rolling(20,min_periods=10).mean().values;mhv=N('MACD_Hist').values;mhpv=np.roll(mhv,1)
    ma50_v=N('MA50').values;ma200_v=N('MA200').values;wt1_v=N('WT1').values;rsi_v=N('RSI').values;mfi_v=N('MFI').values
    adx_v=N('ADX').values;stoch_v=N('StochK').values;ut_v=N('UTBot_Dir').values;sq_v=df.get('Squeeze_On',pd.Series(False,index=idx)).values
    washout_bottom_v=F('Washout_Bottom_Hard').values
    atr_norm = (N('ATR').values / (C + 1e-10)) * 100
    atr_scale = np.clip(atr_norm / 2.5, 0.75, 1.25)
    buy_labels=('STRONG_BUY','BUY','WATCH_BUY');sell_labels=('STRONG_SELL','SELL','WATCH_SELL');money_eff=es[:,money_i]
    for i in range(n):
        e=ens[i];ba=bag[i];sl=sag[i];sy=syn[i];sr=1 if abs(sy)>=15 else 0
        asc = atr_scale[i]
        above_ma50=bool(C[i]>ma50_v[i]) if not np.isnan(ma50_v[i]) else False
        above_ma200=bool(C[i]>ma200_v[i]) if not np.isnan(ma200_v[i]) else False
        leader_mode=bool(leader_stock_mode_v[i])
        lead_buy=float(leading_buy_score_v[i])
        lead_sell=float(leading_sell_score_v[i])
        lead_spread=float(leading_spread_v[i])
        lead_penalty=float(leading_noise_penalty_v[i])
        lead_noise_block=bool(leading_noise_block_v[i])
        lead_buy_block=bool(leading_buy_noise_block_v[i])
        lead_sell_block=bool(leading_sell_noise_block_v[i])
        lead_reason=str(leading_reason_v[i] or "").strip()
        lead_noise_text=str(leading_noise_flag_v[i] or "").strip()
        macro_risk_off_count=int(bool(spy_risk_off_v[i]))+int(bool(breadth_risk_off_v[i]))+int(bool(vix_risk_off_v[i]))+int(bool(tnx_headwind_v[i]))+int(bool(dxy_headwind_v[i]))
        macro_risk_on_count=int(bool(spy_risk_on_v[i]))+int(bool(breadth_risk_on_v[i]))+int(bool(vix_risk_on_v[i]))+int(bool(tnx_tailwind_v[i]))+int(bool(dxy_tailwind_v[i]))
        buy_adj,sell_adj=context_threshold_adjustments(int(ctx_v[i]))
        buy_adj+=market_buy_adj[i];sell_adj+=market_sell_adj[i]
        early_bull_turn=((trend_inflect_buy_score_v[i]>=JT.TREND_INFLECTION_STRONG) and (market_turn_bull_v[i] or continuation_buy_score_v[i]>=2 or ctx_v[i] in (CTX_BOTTOMING,CTX_EXTREME_OS)))
        early_bear_turn=((trend_inflect_sell_score_v[i]>=JT.TREND_INFLECTION_STRONG+1) and ((market_turn_bear_v[i] and continuation_sell_score_v[i]>=2) or ctx_v[i] in (CTX_TOPPING,CTX_EXTREME_OB)))
        if early_bull_turn:
            buy_adj-=3.2
            sell_adj-=1.0
        if early_bear_turn:
            sell_adj+=0.9
        if leader_mode:
            buy_adj-=0.6
            sell_adj-=5.5
        sbt=(strong_buy_th * asc)+buy_adj;bt=(buy_th * asc)+buy_adj;wbt=(watch_buy_th * asc)+buy_adj*.5
        sst=(strong_sell_th * asc)+sell_adj;st=(sell_th * asc)+sell_adj;wst=(watch_sell_th * asc)+sell_adj*.5
        if continuation_buy_score_v[i]>=2 and not ut_overheat_buy_v[i]:
            bt-=0.8
            wbt-=2.4
        if ut_overheat_buy_v[i] or bearish_gap_failure_v[i]:
            sbt+=4.0
        buy_supportive_stack=(
            (continuation_buy_score_v[i]>=3)
            or bullish_gap_reversal_v[i]
            or diag_support_v[i]
            or diag_breakout_v[i]
            or box_breakout_v[i]
            or channel_breakout_v[i]
            or triangle_breakout_v[i]
        )
        buy_supportive_stack_light=(
            (continuation_buy_score_v[i]>=2)
            or bullish_gap_reversal_v[i]
            or diag_support_v[i]
            or box_support_v[i]
            or channel_support_v[i]
            or leader_mode
        )
        sell_supportive_stack=(
            (continuation_sell_score_v[i]>=3)
            or bearish_gap_failure_v[i]
            or diag_reject_v[i]
            or diag_breakdown_v[i]
            or box_breakdown_v[i]
            or channel_breakdown_v[i]
            or triangle_breakdown_v[i]
            or hard_blowoff_v[i]
        )
        buy_confirm_count=(
            int(continuation_buy_score_v[i]>=2)
            +int(bullish_gap_reversal_v[i])
            +int(diag_support_v[i] or diag_breakout_v[i] or box_support_v[i] or channel_support_v[i] or box_breakout_v[i] or channel_breakout_v[i] or triangle_breakout_v[i])
            +int(market_turn_bull_v[i])
            +int(trend_inflect_buy_score_v[i]>=JT.TREND_INFLECTION_STRONG)
            +int(vr_v[i]>=JT.STRONG_BUY_MIN_VOL_RATIO)
            +int(above_ma50)
            +int(above_ma200)
            +int(lead_buy>=52.0)
            +int(lead_spread>=8.0)
        )
        sell_confirm_count=(
            int(continuation_sell_score_v[i]>=2)
            +int(bearish_gap_failure_v[i])
            +int(diag_reject_v[i] or diag_breakdown_v[i] or box_reject_v[i] or channel_reject_v[i] or box_breakdown_v[i] or channel_breakdown_v[i] or triangle_breakdown_v[i])
            +int(market_turn_bear_v[i])
            +int(trend_inflect_sell_score_v[i]>=JT.TREND_INFLECTION_STRONG+1)
            +int(macro_risk_off_count>=3)
            +int(breadth_risk_off_v[i])
            +int(not above_ma50)
            +int(not above_ma200)
            +int(lead_sell>=52.0)
            +int(lead_spread<=-8.0)
        )
        strong_buy_ready=(
            (lead_buy>=62.0)
            and (lead_spread>=12.0)
            and (not lead_buy_block)
            and
            (continuation_buy_score_v[i]>=JT.STRONG_BUY_CONTINUATION_MIN)
            and (buy_confirm_count>=5)
            and (bullish_gap_reversal_v[i] or diag_breakout_v[i] or box_breakout_v[i] or channel_breakout_v[i] or triangle_breakout_v[i] or pocket_pivot_v[i] or three_weeks_tight_v[i] or fib_confluence_buy_v[i])
            and (not ut_overheat_buy_v[i])
            and (not bearish_gap_failure_v[i])
            and (not thin_trade_v[i])
            and (vr_v[i]>=JT.STRONG_BUY_MIN_VOL_RATIO)
            and (long_rr_v[i]>=0.95)
            and above_ma50
            and (above_ma200 or leader_mode or bullish_gap_reversal_v[i])
            and (macro_risk_off_count<4)
        )
        buy_ready=(
            (lead_buy>=48.0)
            and (lead_spread>=4.0)
            and (not lead_buy_block)
            and
            (buy_confirm_count>=3)
            and (
                (continuation_buy_score_v[i]>=2)
                or buy_supportive_stack_light
                or bullish_gap_reversal_v[i]
                or market_turn_bull_v[i]
                or trend_inflect_buy_score_v[i]>=JT.TREND_INFLECTION_STRONG
            )
        )
        watch_buy_ready=(
            (lead_buy>=38.0)
            and (lead_spread>=-4.0)
            and (not lead_buy_block)
            and (
                (continuation_buy_score_v[i]>=2)
                or bullish_gap_reversal_v[i]
                or buy_supportive_stack_light
                or early_bull_turn
                or ut_support_buy_v[i]
            )
        )
        sell_breakdown_stack=(
            bearish_gap_failure_v[i]
            or diag_breakdown_v[i]
            or box_breakdown_v[i]
            or channel_breakdown_v[i]
            or triangle_breakdown_v[i]
            or fib_618_breakdown_v[i]
            or fib_confluence_sell_v[i]
        )
        strong_sell_ready=(
            (lead_sell>=62.0)
            and (lead_spread<=-12.0)
            and (not lead_sell_block)
            and
            (sell_confirm_count>=JT.STRONG_SELL_CONFIRM_MIN)
            and (
                hard_blowoff_v[i]
                or (
                    sell_supportive_stack
                    and (continuation_sell_score_v[i]>=4)
                    and sell_breakdown_stack
                    and ((macro_risk_off_count>=3) or breadth_risk_off_v[i] or ctx_v[i] in (CTX_STRONG_DN,CTX_DISTRIBUTION,CTX_TOPPING,CTX_EXTREME_OB))
                    and (not above_ma50)
                    and (not above_ma200)
                )
            )
        )
        sell_ready=(
            (lead_sell>=48.0)
            and (lead_spread<=-4.0)
            and (not lead_sell_block)
            and
            (sell_confirm_count>=JT.SELL_CONFIRM_MIN)
            and (
                hard_blowoff_v[i]
                or (
                    (continuation_sell_score_v[i]>=3)
                    and (sell_breakdown_stack or diag_reject_v[i] or box_reject_v[i] or channel_reject_v[i])
                    and ((macro_risk_off_count>=2) or breadth_risk_off_v[i] or (not above_ma50) or (not above_ma200))
                )
            )
        )
        watch_sell_ready=(
            (lead_sell>=38.0)
            and (lead_spread<=4.0)
            and (not lead_sell_block)
            and (
                hard_blowoff_v[i]
                or (
                    (sell_confirm_count>=JT.WATCH_SELL_CONFIRM_MIN)
                    and (
                        continuation_sell_score_v[i]>=2
                        or bearish_gap_failure_v[i]
                        or diag_reject_v[i]
                        or box_reject_v[i]
                        or channel_reject_v[i]
                        or market_turn_bear_v[i]
                    )
                )
            )
        )
        if leader_mode:
            strong_sell_ready=strong_sell_ready and (
                hard_blowoff_v[i]
                or (
                    ((macro_risk_off_count>=3) or breadth_risk_off_v[i])
                    and bearish_gap_failure_v[i]
                    and (diag_breakdown_v[i] or box_breakdown_v[i] or channel_breakdown_v[i] or triangle_breakdown_v[i] or continuation_sell_score_v[i]>=4)
                    and (not above_ma50)
                    and (not above_ma200)
                )
            )
            sell_ready=sell_ready and (
                hard_blowoff_v[i]
                or (
                    ((macro_risk_off_count>=3) or breadth_risk_off_v[i])
                    and (bearish_gap_failure_v[i] or diag_breakdown_v[i] or box_breakdown_v[i] or channel_breakdown_v[i] or triangle_breakdown_v[i] or continuation_sell_score_v[i]>=4)
                )
            )
            if not (macro_risk_off_count>=2 or breadth_risk_off_v[i] or hard_blowoff_v[i] or bearish_gap_failure_v[i]):
                watch_sell_ready=False
        high_conflict=(
            (buy_total_arr[i]>=JT.HIGH_CONFLICT_TOTAL)
            and (sell_total_arr[i]>=JT.HIGH_CONFLICT_TOTAL)
            and (abs(layer_edge[i])<=JT.HIGH_CONFLICT_EDGE)
            and (abs(e)<=JT.HIGH_CONFLICT_ENSEMBLE)
            and (ba>=2)
            and (sl>=2)
        )
        if high_conflict:
            j[i]='MIXED'
        elif e>=sbt and ba>=(JT.STRONG_MIN_AGREE-sr) and strong_buy_ready:j[i]='STRONG_BUY'
        elif e>=bt and ba>=(JT.BUY_MIN_AGREE-sr):
            j[i]='BUY' if buy_ready else ('WATCH_BUY' if watch_buy_ready else 'NEUTRAL')
        elif e>=wbt and ba>=max(JT.WATCH_MIN_AGREE-sr,1) and watch_buy_ready:j[i]='WATCH_BUY'
        elif e<=sst and sl>=(JT.STRONG_MIN_AGREE-sr) and strong_sell_ready:j[i]='STRONG_SELL'
        elif e<=st and sl>=(JT.BUY_MIN_AGREE-sr):
            j[i]='SELL' if sell_ready else ('WATCH_SELL' if watch_sell_ready else 'NEUTRAL')
        elif e<=wst and sl>=max(JT.WATCH_MIN_AGREE-sr,1) and watch_sell_ready:j[i]='WATCH_SELL'
        elif (ctx_v[i] in (CTX_EXTREME_OS,CTX_BOTTOMING)) and ba>=2 and (sy>6 or pred[i]>5) and e>=(wbt-6):
            j[i]='BUY' if buy_ready else 'WATCH_BUY'
        elif (ctx_v[i] in (CTX_EXTREME_OB,CTX_TOPPING)) and sl>=2 and (sy<-6 or pred[i]<-5) and e<=(wst+6) and watch_sell_ready:
            j[i]='WATCH_SELL'
        elif ba>=3 and sl>=3:j[i]='MIXED'
        pre_veto_j[i]=j[i]
        notes=[];signal_notes=[]
        macro_risk_off_count_arr[i]=macro_risk_off_count;macro_risk_on_count_arr[i]=macro_risk_on_count
        if high_conflict:
            notes.append("Flip guard active")
        if lead_noise_block:
            notes.append("Leading noise block")
        elif lead_penalty>=18:
            notes.append("Leading noise elevated")
        if macro_risk_off_count>=3:
            notes.append("Flip guard active")
        elif macro_risk_on_count>=2 and j[i] in sell_labels:
            notes.append("Flip guard active")
        if market_turn_bull_v[i] or trend_inflect_bull_v[i]:
            signal_notes.append("Bullish turn evidence")
        if market_turn_bear_v[i] or trend_inflect_bear_v[i]:
            signal_notes.append("Bearish turn evidence")
        if bullish_gap_reversal_v[i]:
            signal_notes.append("Gap reversal")
        if bearish_gap_failure_v[i]:
            notes.append("Flip guard active")
        if continuation_buy_score_v[i]>=2:
            signal_notes.append("Continuation buy stack")
        if continuation_sell_score_v[i]>=2:
            notes.append("Flip guard active")
        if leader_mode:
            signal_notes.append("Leader mode")
        if hard_blowoff_v[i]:
            notes.append("Flip guard active")
        if thin_trade_v[i]:
            notes.append("Flip guard active")
        if ut_overheat_buy_v[i] and j[i] in buy_labels:
            notes.append("Flip guard active")
        severe_buy=(money_eff[i]<=JT.MONEY_VETO_NEUTRAL) or (cmf[i]<0 and obv_slope_v[i]<0 and long_rr_v[i]<0.9)
        severe_sell=(money_eff[i]>=abs(JT.MONEY_VETO_NEUTRAL)) or (cmf[i]>0 and obv_slope_v[i]>0 and short_rr_v[i]<0.9)
        countertrend_buy_risk=(
            ctx_v[i] in (CTX_STRONG_DN,CTX_DISTRIBUTION)
            and (not above_ma50)
            and (not above_ma200)
            and (money_eff[i]<0 or long_rr_v[i]<1.15)
            and not washout_bottom_v[i]
            and 'Capitul' not in df['Veto_Flags'].iloc[i]
        )
        countertrend_sell_risk=(
            ctx_v[i] in (CTX_STRONG_UP,CTX_ACCUMULATION)
            and above_ma50
            and above_ma200
            and (money_eff[i]>0 or short_rr_v[i]<1.15)
            and not hard_blowoff_v[i]
        )
        market_sell_headwind=((macro_risk_on_count>=2) or leader_mode) and not hard_blowoff_v[i] and ((money_eff[i]>-5) or (short_rr_v[i]<1.45) or (continuation_buy_score_v[i]>=2))
        market_buy_headwind=(
            (
                (macro_risk_off_count>=5)
                or ((macro_risk_off_count>=4) and (macro_pressure_v[i]>=4.4))
                or ((macro_risk_off_count>=3) and breadth_risk_off_v[i] and market_turn_bear_v[i] and (continuation_sell_score_v[i]>=3))
            )
            and not washout_bottom_v[i]
            and (not leader_mode)
            and ((money_eff[i]<0) or (long_rr_v[i]<0.95))
        )
        if hard_blowoff_v[i]:
            if j[i] in buy_labels or j[i] in ('NEUTRAL','MIXED'):
                new_label='STRONG_SELL' if (sl>=max(JT.WATCH_MIN_AGREE-sr,1) and e<=st) else 'SELL'
                if new_label!=j[i]:downgrade_count[i]+=1
                j[i]=new_label
        elif j[i] in buy_labels:
            if bearish_gap_failure_v[i] and (
                (j[i]=='STRONG_BUY')
                or ((j[i]=='BUY') and (not leader_mode) and (macro_risk_off_count>=3) and not buy_supportive_stack)
            ):
                prev_label=j[i]
                j[i]=downgrade_buy(j[i],severe=bool((parabolic_rise_v[i] and volume_surge_v[i]) and not leader_mode))
                downgrade_count[i]+=int(j[i]!=prev_label)
            if j[i]=='STRONG_BUY' and thin_trade_v[i] and (not buy_supportive_stack_light) and (long_rr_v[i]<1.0):
                prev_label=j[i]
                j[i]=downgrade_buy(j[i],severe=False)
                downgrade_count[i]+=int(j[i]!=prev_label)
            if j[i]=='STRONG_BUY' and ut_overheat_buy_v[i] and (continuation_buy_score_v[i]<JT.STRONG_BUY_CONTINUATION_MIN) and not bullish_gap_reversal_v[i]:
                prev_label=j[i]
                j[i]=downgrade_buy(j[i],severe=False)
                downgrade_count[i]+=int(j[i]!=prev_label)
            if countertrend_buy_risk and not buy_supportive_stack:
                if j[i]=='STRONG_BUY':
                    prev_label=j[i]
                    j[i]=downgrade_buy(j[i],severe=False)
                    downgrade_count[i]+=int(j[i]!=prev_label)
                if j[i] in buy_labels and (macro_risk_off_count>=4) and (severe_buy or long_rr_v[i]<0.85) and not buy_supportive_stack_light:
                    if not leader_mode:
                        prev_label=j[i]
                        j[i]=downgrade_buy(j[i],severe=True)
                        downgrade_count[i]+=int(j[i]!=prev_label)
            if j[i] in buy_labels and market_buy_headwind and not buy_supportive_stack:
                if j[i]=='STRONG_BUY':
                    prev_label=j[i]
                    j[i]=downgrade_buy(j[i],severe=(spy_trend_score_v[i]<=JT.MARKET_SCORE_TREND_OFF-1 and long_rr_v[i]<JT.VP_RR_FLOOR))
                    downgrade_count[i]+=int(j[i]!=prev_label)
            if pv_bear_v[i] and (j[i]=='STRONG_BUY' or (severe_buy and j[i]=='BUY' and not leader_mode and not buy_supportive_stack_light and macro_risk_off_count>=3)):
                prev_label=j[i]
                j[i]=downgrade_buy(j[i],severe=(j[i]=='STRONG_BUY' and severe_buy and not leader_mode))
                downgrade_count[i]+=int(j[i]!=prev_label)
            if long_rr_v[i]<JT.VP_RR_FLOOR:
                if (j[i]=='STRONG_BUY') or ((long_rr_v[i]<0.70) and not buy_supportive_stack_light and not leader_mode and macro_risk_off_count>=3):
                    prev_label=j[i]
                    j[i]=downgrade_buy(j[i],severe=(long_rr_v[i]<0.75 and money_eff[i]<0 and not leader_mode))
                    downgrade_count[i]+=int(j[i]!=prev_label)
        elif j[i] in sell_labels:
            if bullish_gap_reversal_v[i]:
                prev_label=j[i]
                j[i]=downgrade_sell(j[i],severe=bool((continuation_buy_score_v[i]>=2 and (diag_support_v[i] or macro_risk_on_count>=2)) or leader_mode))
                downgrade_count[i]+=int(j[i]!=prev_label)
            if j[i]=='STRONG_SELL' and thin_trade_v[i] and not sell_supportive_stack:
                prev_label=j[i]
                j[i]=downgrade_sell(j[i],severe=False)
                downgrade_count[i]+=int(j[i]!=prev_label)
            if j[i] in sell_labels and continuation_buy_score_v[i]>=2 and (macro_risk_on_count>=1 or breadth_risk_on_v[i] or diag_support_v[i]) and not bearish_gap_failure_v[i]:
                prev_label=j[i]
                j[i]=downgrade_sell(j[i],severe=bool(leader_mode or continuation_buy_score_v[i]>=3))
                downgrade_count[i]+=int(j[i]!=prev_label)
            if countertrend_sell_risk and not sell_supportive_stack:
                prev_label=j[i]
                j[i]=downgrade_sell(j[i],severe=bool(leader_mode or macro_risk_on_count>=3))
                downgrade_count[i]+=int(j[i]!=prev_label)
                if j[i] in sell_labels and (severe_sell or short_rr_v[i]<JT.VP_RR_FLOOR) and not sell_supportive_stack:
                    prev_label=j[i]
                    j[i]=downgrade_sell(j[i],severe=bool(leader_mode or continuation_buy_score_v[i]>=2))
                    downgrade_count[i]+=int(j[i]!=prev_label)
            if j[i] in sell_labels and market_sell_headwind and not sell_supportive_stack:
                prev_label=j[i]
                j[i]=downgrade_sell(j[i],severe=(leader_mode or (spy_trend_score_v[i]>=JT.MARKET_SCORE_TREND_ON+1 and short_rr_v[i]<JT.VP_RR_FLOOR)))
                downgrade_count[i]+=int(j[i]!=prev_label)
            if pv_bull_v[i]:
                prev_label=j[i]
                j[i]=downgrade_sell(j[i],severe=(leader_mode or (j[i]=='STRONG_SELL' and severe_sell)))
                downgrade_count[i]+=int(j[i]!=prev_label)
            if short_rr_v[i]<JT.VP_RR_FLOOR:
                prev_label=j[i]
                j[i]=downgrade_sell(j[i],severe=(leader_mode or (short_rr_v[i]<0.75 and money_eff[i]>0)))
                downgrade_count[i]+=int(j[i]!=prev_label)
        if j[i] in buy_labels and lead_buy_block:
            prev_label=j[i]
            j[i]=downgrade_buy(j[i],severe=bool((lead_sell>=lead_buy) or (lead_spread<=0) or (lead_buy<42.0) or (lead_penalty>=28.0)))
            downgrade_count[i]+=int(j[i]!=prev_label)
        elif j[i] in sell_labels and lead_sell_block:
            prev_label=j[i]
            j[i]=downgrade_sell(j[i],severe=bool((lead_buy>=lead_sell) or (lead_spread>=0) or (lead_sell<42.0) or (lead_penalty>=28.0)))
            downgrade_count[i]+=int(j[i]!=prev_label)
        if i>0:
            prev_final=j[i-1];prev_buy=prev_final in buy_labels;prev_sell=prev_final in sell_labels;cur_buy=j[i] in buy_labels;cur_sell=j[i] in sell_labels
            if prev_buy and cur_sell:
                strong_sell_flip=(
                    (e<=sst)
                    or (sl>=JT.STRONG_MIN_AGREE)
                    or (ctx_v[i] in (CTX_STRONG_DN,CTX_DISTRIBUTION,CTX_EXTREME_OB,CTX_TOPPING))
                    or (macro_risk_off_count>=JT.FLIP_GUARD_MACRO_CONFIRM)
                    or (market_turn_bear_v[i] and sell_supportive_stack)
                    or ((trend_inflect_sell_score_v[i]>=JT.TREND_INFLECTION_STRONG+1) and sell_supportive_stack)
                    or hard_blowoff_v[i]
                    or (sy<=-JT.FLIP_GUARD_SYNERGY)
                    or (pred[i]<=-JT.FLIP_GUARD_PREDICTION)
                )
                if leader_mode and not hard_blowoff_v[i] and not bearish_gap_failure_v[i] and continuation_sell_score_v[i]<3:
                    strong_sell_flip=False
                if not strong_sell_flip:
                    prev_label=j[i]
                    j[i]='MIXED'
                    flip_guard_triggered[i]=j[i]!=prev_label
                    downgrade_count[i]+=int(j[i]!=prev_label)
                    notes.append("Flip guard active")
            elif prev_sell and cur_buy:
                strong_buy_flip=(
                    (e>=sbt)
                    or (ba>=JT.STRONG_MIN_AGREE)
                    or (ctx_v[i] in (CTX_STRONG_UP,CTX_ACCUMULATION,CTX_EXTREME_OS,CTX_BOTTOMING))
                    or (macro_risk_on_count>=JT.FLIP_GUARD_MACRO_CONFIRM)
                    or market_turn_bull_v[i]
                    or (trend_inflect_buy_score_v[i]>=JT.TREND_INFLECTION_STRONG)
                    or washout_bottom_v[i]
                    or (sy>=JT.FLIP_GUARD_SYNERGY)
                    or (pred[i]>=JT.FLIP_GUARD_PREDICTION)
                )
                if not strong_buy_flip:
                    prev_label=j[i]
                    j[i]='MIXED'
                    flip_guard_triggered[i]=j[i]!=prev_label
                    downgrade_count[i]+=int(j[i]!=prev_label)
                    notes.append("Flip guard active")
        contrast_notes.append('; '.join(notes[:3]))
        signal_note_txt='; '.join(signal_notes[:2])
        ae=abs(e);dm=max(ba,sl);ap=dm/NUM_COMMITTEES*35;sp=min(ae/60*30,30);avp=np.mean(ec[i])/100*20;syp=min(abs(sy)/20*10,10);pp=min(abs(pred[i])/15*5,5)
        raw=ap+sp+avp+syp+pp
        layer_conf=0.
        if j[i] in buy_labels:
            layer_conf=min((ba_layers[i]*1.6)+(buy_total_arr[i]*0.22),14)
        elif j[i] in sell_labels:
            layer_conf=min((sa_layers[i]*1.6)+(sell_total_arr[i]*0.22),14)
        raw+=layer_conf
        if min(ba_layers[i],sa_layers[i])>=4:
            raw-=5
        if notes and not hard_blowoff_v[i]:
            raw-=min(6,2*len(notes))
        if hard_blowoff_v[i]:
            raw=min(99,raw+4)
        if j[i] in ('NEUTRAL','MIXED'):raw=max(15,min(55,raw))
        conf[i]=np.clip(raw,5,99)
        
        if i < n - 7:
            rs.append("");rd.append("");al.append("")
            continue

        cms={cm:es[i,ci] for ci,cm in enumerate(COMMITTEE_NAMES)}
        vstr=df['Veto_Flags'].iloc[i] if i<len(df) else ''
        obr=bool(obv_v[i]>obv_mav[i]) if not np.isnan(obv_mav[i]) else True
        ma50a=bool(C[i]>ma50_v[i]) if not np.isnan(ma50_v[i]) else False
        ma200a=bool(C[i]>ma200_v[i]) if not np.isnan(ma200_v[i]) else False
        mhu=bool(mhv[i]>mhpv[i]) if i>0 else False
        signal_note_txt='; '.join(signal_notes[:2])
        r,d,a=_gen_reason(j[i],e,int(ctx_v[i]),vstr,sy,pred[i],ba,sl,wt1_v[i],rsi_v[i],mfi_v[i],cmf[i],obr,adx_v[i],vr_v[i],ma50a,ma200a,mhu,stoch_v[i],bool(hma_r_arr[i]) if i<len(hma_r_arr) else False,int(ut_v[i]),bool(sq_v[i]),cms)
        note_txt=contrast_notes[-1]
        if note_txt:
            d=f"{d} | {note_txt}" if d else note_txt
        if signal_note_txt:
            d=f"{d} | {signal_note_txt}" if d else signal_note_txt
        if lead_reason:
            d=f"{d} | leading={lead_reason}" if d else f"leading={lead_reason}"
        if lead_noise_text:
            d=f"{d} | noise={lead_noise_text}" if d else f"noise={lead_noise_text}"
        if not a:
            a=default_action_label(j[i])
        rs.append(r);rd.append(d);al.append(a)
    df['Committee_PreVeto_Judgment']=pre_veto_j;df['Committee_Judgment']=j;df['Committee_Confidence']=conf;df['Committee_Buy_Agree']=bag;df['Committee_Sell_Agree']=sag
    df['Committee_Downgrade_Count']=downgrade_count;df['Committee_Macro_Risk_Off_Count']=macro_risk_off_count_arr;df['Committee_Macro_Risk_On_Count']=macro_risk_on_count_arr
    df['Committee_Flip_Guard_Triggered']=flip_guard_triggered
    df['Committee_Judgment_Reason']=rs;df['Committee_Judgment_Detail']=rd;df['Committee_Action_Label']=al;df['Committee_Contrast_Notes']=contrast_notes
    
    return df



