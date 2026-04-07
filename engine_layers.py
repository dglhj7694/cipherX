from __future__ import annotations

import numpy as np
import pandas as pd

from config import JT
from utils import _sp, _spd


def apply_layer_totals(df, layer_names, combo_registry):
    buy_raw = sum(df[f"BL_{name}"].clip(lower=0) for name in layer_names)
    sell_raw = sum(df[f"SL_{name}"].clip(lower=0) for name in layer_names)
    df["Buy_Active_Layers"] = sum((df[f"BL_{name}"] > 0).astype(int) for name in layer_names)
    df["Sell_Active_Layers"] = sum((df[f"SL_{name}"] > 0).astype(int) for name in layer_names)

    conflict_layers = sum(((df[f"BL_{name}"] > 0) & (df[f"SL_{name}"] > 0)).astype(int) for name in layer_names)
    buy_core = (df["BL_Trend"] + df["BL_Momentum"] + df["BL_Leading"]).clip(lower=0)
    sell_core = (df["SL_Trend"] + df["SL_Momentum"] + df["SL_Leading"]).clip(lower=0)
    buy_quality = (1.0 + ((buy_core - sell_core) / 36.0).clip(-0.20, 0.35)).astype(float)
    sell_quality = (1.0 + ((sell_core - buy_core) / 36.0).clip(-0.20, 0.35)).astype(float)
    conflict_penalty = (conflict_layers * 0.7).clip(0, 6).astype(float)

    idx = df.index
    t1_buy_cols = [cn for cn, cfg in combo_registry.items() if cfg.get("dir") == "buy" and cfg.get("tier") == 1 and cn in df.columns]
    t1_sell_cols = [cn for cn, cfg in combo_registry.items() if cfg.get("dir") == "sell" and cfg.get("tier") == 1 and cn in df.columns]
    t1_buy_boost = sum(df[col].fillna(False).astype(float) for col in t1_buy_cols) if t1_buy_cols else pd.Series(0.0, index=idx)
    t1_sell_boost = sum(df[col].fillna(False).astype(float) for col in t1_sell_cols) if t1_sell_cols else pd.Series(0.0, index=idx)

    df["Signal_Conflict_Layers"] = conflict_layers
    df["Buy_Quality_Factor"] = buy_quality
    df["Sell_Quality_Factor"] = sell_quality
    df["Buy_Total"] = ((buy_raw * buy_quality) + (t1_buy_boost * 0.8) - conflict_penalty).clip(lower=0)
    df["Sell_Total"] = ((sell_raw * sell_quality) + (t1_sell_boost * 0.8) - conflict_penalty).clip(lower=0)

    ls_ = df["BL_Leading"] - df["SL_Leading"]
    lgs = df["BL_Lagging"] - df["SL_Lagging"]
    df["Leading_Verdict"] = pd.Series(
        np.select(
            [ls_ > 3, ls_ > 1, ls_ < -3, ls_ < -1],
            ["Strong leading buy", "Leading buy", "Strong leading sell", "Leading sell"],
            default="Neutral",
        ),
        index=idx,
    )
    df["Lagging_Verdict"] = pd.Series(
        np.select(
            [lgs > 3, lgs > 1, lgs < -3, lgs < -1],
            ["Strong lagging buy", "Lagging buy", "Strong lagging sell", "Lagging sell"],
            default="Neutral follow-through",
        ),
        index=idx,
    )
    return df


def compute_10layer_scores(df, vol_ratio, hma_r_v, combo_registry):
    C, O = df["Close"], df["Open"]
    idx = df.index
    N = lambda c, d=0: df.get(c, pd.Series(d, index=idx)).fillna(d)
    vr = vol_ratio
    history_bars = N("History_Bars", 0)
    ma50_ready = history_bars >= JT.MIN_HISTORY_MA50
    ma200_ready = history_bars >= JT.MIN_HISTORY_MA200
    a200 = ma200_ready & (C > N("MA200", np.nan))
    a50 = ma50_ready & (C > N("MA50", np.nan))
    a20 = C > N("MA20", np.nan)
    b200 = ma200_ready & (C < N("MA200", np.nan))
    b50 = ma50_ready & (C < N("MA50", np.nan))
    b20 = C < N("MA20", np.nan)
    mhr = N("MACD_Hist") > N("MACD_Hist").shift(1)
    mhf = N("MACD_Hist") < N("MACD_Hist").shift(1)
    rr_ = N("RSI") > N("RSI").shift(1)
    rf_ = N("RSI") < N("RSI").shift(1)
    wr_ = N("WT1") > N("WT1").shift(1)
    wf_ = N("WT1") < N("WT1").shift(1)
    obv = N("OBV")
    obvm = obv.rolling(20, min_periods=10).mean()
    regime = N("Regime")
    ca = N("Composite_Accel")
    pb = N("Percent_B")
    rmfi = N("RSI_MFI")
    cmf = N("CMF")
    kumo_a = N("Ichimoku_SenkouA", np.nan)
    kumo_b = N("Ichimoku_SenkouB", np.nan)
    kumo_ready = kumo_a.notna() & kumo_b.notna()
    kumo_top = pd.concat([kumo_a, kumo_b], axis=1).max(axis=1)
    kumo_bot = pd.concat([kumo_a, kumo_b], axis=1).min(axis=1)
    utbot_dir = N("UTBot_Dir")
    wt1 = N("WT1")
    rsi = N("RSI")
    stochk = N("StochK")
    mfi = N("MFI")
    vwap = N("VWAP", np.nan)
    fixed_vwap = N("Fixed_VWAP", np.nan)
    psar_dir = N("PSAR_Direction", 0)
    supertrend = N("SuperTrend", np.nan)
    tenkan = N("Ichimoku_Tenkan", np.nan)
    kijun = N("Ichimoku_Kijun", np.nan)
    willr = N("Williams_R", -50)
    cci = N("CCI", 0)
    roc = N("ROC", 0)
    rmi = N("RMI", 50)
    trix = N("TRIX", 0)
    price_osc = N("Price_Oscillator", 0)
    vol_osc = N("Volume_Oscillator", 0)
    intensity_idx = N("Intraday_Intensity_Index", 0)
    chaikin = N("Chaikin_Oscillator", 0)
    env_pct = N("Envelope_Percent", 0.5)
    ma20_gap = N("MA20_ATR_Gap", 0)
    channel_up = N("Price_Channel_Up", np.nan)
    channel_low = N("Price_Channel_Low", np.nan)
    channel_pos = ((((C - channel_low) / ((channel_up - channel_low) + 1e-10)) - 0.5) * 2).clip(-2, 2)
    ad_line = N("AD_Line", 0)
    ad_roll = ad_line.rolling(60, min_periods=20)
    ad_z = ((ad_line - ad_roll.mean()) / (ad_roll.std() + 1e-10)).fillna(0)
    dv20 = N("Dollar_Volume_20", 0)
    dv_log = np.log10(dv20.clip(lower=1))
    dv_roll = dv_log.rolling(60, min_periods=20)
    dv_z = ((dv_log - dv_roll.mean()) / (dv_roll.std() + 1e-10)).fillna(0)
    price_above_vwap = vwap.notna() & (C > vwap)
    price_above_fixed = fixed_vwap.notna() & (C > fixed_vwap)
    price_below_vwap = vwap.notna() & (C < vwap)
    price_below_fixed = fixed_vwap.notna() & (C < fixed_vwap)
    price_above_super = supertrend.notna() & (C > supertrend)
    price_below_super = supertrend.notna() & (C < supertrend)
    price_above_tk = tenkan.notna() & kijun.notna() & (C > tenkan) & (C > kijun)
    price_below_tk = tenkan.notna() & kijun.notna() & (C < tenkan) & (C < kijun)
    cloud_bull = kumo_ready & (C > kumo_top)
    cloud_bear = kumo_ready & (C < kumo_bot)
    wr_rebound = (willr <= -80) & (willr > willr.shift(1))
    wr_fade = (willr >= -20) & (willr < willr.shift(1))
    cci_rebound = (cci <= -100) & (cci > cci.shift(1))
    cci_fade = (cci >= 100) & (cci < cci.shift(1))
    F = lambda c: df.get(c, pd.Series(False, index=idx)).fillna(False)
    os_base = ((wt1 < -60) | (rsi < 32) | (stochk < 20)) & (wr_ | (wt1 > wt1.shift(1)))
    ob_base = ((wt1 > 60) | (rsi > 68) | (stochk > 80)) & (wf_ | (wt1 < wt1.shift(1)))
    os_turn = (
        F("UTBot_Buy").rolling(3, min_periods=1).max().astype(bool)
        | F("Hull_Turn_Bull").rolling(3, min_periods=1).max().astype(bool)
        | F("MACD_Cross_Buy")
        | F("StochRSI_Cross_Buy")
        | F("WT_Up")
    )
    ob_turn = (
        F("UTBot_Sell").rolling(3, min_periods=1).max().astype(bool)
        | F("Hull_Turn_Bear").rolling(3, min_periods=1).max().astype(bool)
        | F("MACD_Cross_Sell")
        | F("StochRSI_Cross_Sell")
        | F("WT_Down")
    )
    os_rev = os_base & (os_turn | F("Bull_Divergence") | F("RSI_Bull_Divergence") | F("CS_Bottom_Fishing_Buy"))
    ob_rev = ob_base & (ob_turn | F("Bear_Divergence") | F("RSI_Bear_Divergence") | F("CS_Top_Fishing_Sell"))

    bt = pd.Series(0.0, index=idx)
    bt += a200.astype(float) * 2.5 + a50.astype(float) * 1.5 + a20.astype(float) * 1
    bt += np.where(N("MA50") > N("MA200"), 1.5, 0) + np.where(N("Plus_DI") > N("Minus_DI"), 1, 0) + np.where(N("ST_Direction") == 1, 1, 0)
    bt += _sp(df, "Cross_Above_50MA", 1) + _sp(df, "Golden_Cross", 1.5) + np.where(b200 & b50, -2.0, 0)
    bt += np.where((b50 | b200) & os_rev, 1.8, 0) - np.where((a50 | a200) & ob_rev, 1.2, 0)
    bt += price_above_vwap.astype(float) * 0.45 + price_above_fixed.astype(float) * 0.45 + np.where(psar_dir > 0, 0.6, np.where(psar_dir < 0, -0.45, 0))
    bt += price_above_super.astype(float) * 0.7 + price_above_tk.astype(float) * 0.55 + cloud_bull.astype(float) * 0.8
    df["BL_Trend"] = bt.clip(-2, JT.TREND_CAP)

    bm = pd.Series(0.0, index=idx)
    for s, p in [("MACD_Cross_Buy", 2.5), ("MACD_Zero_Cross_Buy", 2), ("StochRSI_Cross_Buy", 2), ("ADX_Momentum_Buy", 2), ("VWAP_Bounce_Buy", 1.5)]:
        bm += _sp(df, s, p)
    bm = bm.clip(upper=6)
    bm += np.select([(N("MACD_Hist") > 0) & mhr, (N("MACD_Hist") > 0) & mhf, (N("MACD_Hist") < 0) & mhr], [2, 0.5, 1.5], default=0.0)
    bm += np.clip((40 - N("RSI")) * 0.15, 0, 3) + rr_.astype(float) + np.clip((25 - N("StochK")) * 0.15, 0, 2.5) + np.clip((-10 - N("WT1")) * 0.05, 0, 3) + wr_.astype(float)
    bm += _sp(df, "UTBot_Buy", 2.5) + _sp(df, "Hull_Turn_Bull", 1.6) + _sp(df, "StochSlow_Cross_Buy", 1.5) + _sp(df, "Squeeze_Mom_Cross_Up", 1.5) + np.where(hma_r_v & wr_.values, 1.2, 0)
    bm += np.where(os_rev, 1.5, 0) - np.where(ob_rev, 1.0, 0) + np.where(wr_rebound, 0.8, 0) + np.where(cci_rebound, 0.7, 0)
    bm += np.where(rmi >= 55, 0.7, np.where(rmi <= 45, -0.4, 0)) + np.where(trix > 0, 0.5, np.where(trix < 0, -0.3, 0))
    bm += np.where(roc > 0, 0.6, np.where(roc < 0, -0.4, 0)) + np.where(price_osc > 0, 0.55, np.where(price_osc < 0, -0.35, 0))
    df["BL_Momentum"] = bm.clip(-2, JT.MOMENTUM_CAP)

    bcc = pd.Series(0.0, index=idx)
    for s, p in [("Morning_Star", 3.5), ("Bullish_Engulfing", 3), ("Hammer", 2.5), ("Outside_Bullish", 2.5), ("Doji_Bullish", 1), ("Three_Bar_Reversal_Buy", 2.5)]:
        bcc = np.maximum(bcc, _sp(df, s, p))
    df["BL_Candle"] = pd.Series(bcc, index=idx).clip(upper=JT.CANDLE_CAP)

    bb_ = pd.Series(0.0, index=idx)
    bb_ += _sp(df, "BB_Squeeze_End_Bull", 3) + _sp(df, "NR7_2", 1.5) + _sp(df, "Calm_After_Storm", 1)
    bb_ += np.clip((0.5 - pb) * 6, -2, 3) + _sp(df, "BB_Lower_Bounce", 2) + np.where((env_pct <= 0.20) & (C > O), 1.0, 0) - np.where((env_pct >= 0.80) & (C < O), 0.7, 0)
    df["BL_BB"] = bb_.clip(-1, JT.BB_CAP)

    bv = pd.Series(0.0, index=idx)
    bv += _sp(df, "Volume_Climax_Buy", 3) + _sp(df, "Pocket_Pivot", 2) + _sp(df, "OBV_Div_Buy", 1.5) + _sp(df, "Volume_POC_Breakout", 2.5) + _sp(df, "Volume_Dry_Breakout_Buy", 2)
    bv += np.clip((vr - 1) * 1.5, 0, 3) * (C > O).astype(float) + np.where(obv > obvm, 1, np.where(obv < obvm, -1, 0))
    bv += np.where((vol_osc > 0) & (C > O), 0.9, np.where((vol_osc < 0) & (C < O), -0.7, 0)) + np.where(dv_z > 0.35, 0.6, np.where(dv_z < -0.35, -0.5, 0))
    bv -= np.where(F("Thin_Trade_Risk"), 1.4, 0)
    df["BL_Volume"] = bv.clip(-1, JT.VOLUME_CAP)

    bmf = pd.Series(0.0, index=idx)
    bmf += np.clip(-rmfi * 0.2, -0.5, 2) + _sp(df, "MF_Cross_Bull", 2) + _sp(df, "MF_Bull_Div", 2) + _sp(df, "MF_Accel_Up", 1) + _sp(df, "CMF_Bull", 1.5)
    bmf += np.clip(cmf * 8, -1, 2) + np.where(intensity_idx > 10, 0.9, np.where(intensity_idx < -10, -0.7, 0))
    bmf += np.where(chaikin > 0, 0.8, np.where(chaikin < 0, -0.8, 0)) + np.where(ad_z > 0.4, 0.7, np.where(ad_z < -0.4, -0.7, 0))
    df["BL_MF"] = bmf.clip(-1, JT.MF_CAP)

    bp = pd.Series(0.0, index=idx)
    bp += _spd(df, "Gold_Dot", 4)
    bp += np.where(bp == 0, _spd(df, "Green_Dot_T1", 2.5), 0)
    for s, p in [
        ("Bull_Divergence", 2),
        ("Pullback_123_Bull", 2.5),
        ("Setup_180_Bull", 2),
        ("Boomer_Buy", 2),
        ("Expansion_BO", 3),
        ("Gilligans_Buy", 2.5),
        ("Lizard_Bull", 2),
        ("NonADX_123_Bull", 1.5),
        ("EMA_Pullback_Buy", 2),
        ("Momentum_Ignition_Buy", 3),
        ("SuperTrend_Buy", 2),
        ("Parabolic_Bottom_Buy", 3),
        ("Kumo_Breakout_Bull", 2.5),
        ("Reversal_New_Highs", 2.5),
        ("Slingshot_Bull", 2),
        ("Jack_In_Box_Bull", 2),
        ("Relative_Strength_Buy", 2.5),
        ("VP_VAL_Support", 1.5),
        ("VuManChu_Bull", 3),
        ("Hull_Turn_Bull", JT.TURN_SIGNAL_PATTERN_BUY),
        ("Doji_Breakout_Buy", 1.5),
        ("Three_Bar_Reversal_Buy", 2),
        ("CS_Bottom_Fishing_Buy", 3),
        ("CS_Oversold_Bounce_Buy", 1.5),
    ]:
        bp += _sp(df, s, p)
    bp += _sp(df, "Diag_Support_Hold", 1.8) + _sp(df, "Diag_Breakout_Bull", 2.2)
    bp += _sp(df, "Box_Support_Hold", 1.8) + _sp(df, "Channel_Support_Hold", 2.0)
    bp += _sp(df, "Box_Breakout_Bull", 2.4) + _sp(df, "Channel_Breakout_Bull", 2.5) + _sp(df, "Triangle_Breakout_Bull", 2.8)
    bp += _sp(df, "Fib_382_Support", 1.2) + _sp(df, "Fib_50_Support", 1.5) + _sp(df, "Fib_618_Support", 2.0)
    bp += _sp(df, "Fib_618_Reclaim", 2.2) + _sp(df, "Fib_Confluence_Buy", 2.5)
    df["BL_Pattern"] = bp.clip(upper=JT.PATTERN_CAP)

    bcs = pd.Series(0.0, index=idx)
    for cn, cfg in combo_registry.items():
        if cfg["dir"] != "buy" or cn not in df.columns:
            continue
        bcs += np.where(df[cn].fillna(False), {1: JT.COMBO_T1, 2: JT.COMBO_T2, 3: JT.COMBO_T3}.get(cfg["tier"], 1), 0.0)
    df["BL_Combined"] = bcs.clip(upper=JT.COMBINED_CAP)

    bl_ = pd.Series(0.0, index=idx)
    bl_ += np.clip(ca * 2.5, -1, 3.5) + _sp(df, "Setup_Squeeze_Bull", 1.5) + _sp(df, "Momentum_Accel_Buy", 2) + _sp(df, "WT_Convergence_Bull", 1.5) + _sp(df, "Volume_Dry_Up", 0.5) + np.where(os_rev, 1.2, 0) + _sp(df, "CS_Bottom_Fishing_Buy", 2)
    bl_ += np.where(utbot_dir == 1, 1, np.where(utbot_dir == -1, -0.5, 0)) + np.where(hma_r_v, 0.5, -0.5)
    sp_buy = pd.Series(0.0, index=idx)
    sp_buy += np.clip((10 - N("WT1")) * 0.05, 0, 2) + np.clip((45 - N("RSI")) * 0.1, 0, 2) + np.clip((35 - N("StochK")) * 0.1, 0, 1) + np.clip((35 - mfi) * 0.08, 0, 1.5) + np.clip(ca * 1.5, 0, 2)
    sp_buy += np.where(os_rev, 1.0, 0)
    bl_ += np.where((ma20_gap <= -1.6) & (C > O), 1.0, 0) - np.where(ma20_gap >= 2.4, 1.2, 0)
    bl_ += np.where((channel_pos <= -0.6) & (C > O), 0.7, 0) + np.where(price_above_vwap & (channel_pos < 0.15), 0.45, 0)
    bl_ -= np.where(F("Fib_Ext_1618_Up_Hit"), 1.1, 0)
    df["Setup_Pressure_Buy"] = sp_buy
    bl_ += np.clip(sp_buy * 0.4, 0, 3)
    df["BL_Leading"] = bl_.clip(-1, JT.LEADING_CAP)

    blag = pd.Series(0.0, index=idx)
    blag += a200.astype(float) * 1.0 + a50.astype(float) * 1.0 + ((ma50_ready & ma200_ready) & (N("MA50", np.nan) > N("MA200", np.nan))).astype(float) * 1.0
    blag += np.clip(regime.values * 1.0, -1.5, 3) + np.where(kumo_ready & (C > kumo_top), 1.5, np.where(kumo_ready & (C < kumo_top), -1, 0)) + np.clip((N("RS_Ratio", 1) - 1.0) * 30, -1.5, 2)
    blag += np.where(price_above_tk, 0.6, 0) + np.where(price_above_super, 0.5, 0) + np.where(price_above_fixed, 0.35, 0)
    df["BL_Lagging"] = blag.clip(-2, JT.LAGGING_CAP)

    st_ = pd.Series(0.0, index=idx)
    st_ += b200.astype(float) * 2.5 + b50.astype(float) * 1.5 + b20.astype(float) * 1
    st_ += np.where(N("MA50") < N("MA200"), 1.5, 0) + np.where(N("Minus_DI") > N("Plus_DI"), 1, 0) + np.where(N("ST_Direction") == -1, 1, 0)
    st_ += _sp(df, "Fell_Below_50MA", 1) + _sp(df, "Death_Cross", 1.5) + np.where(a200 & a50, -2.0, 0)
    st_ += np.where((a50 | a200) & ob_rev, 1.8, 0) - np.where((b50 | b200) & os_rev, 1.2, 0)
    st_ += price_below_vwap.astype(float) * 0.45 + price_below_fixed.astype(float) * 0.45 + np.where(psar_dir < 0, 0.6, np.where(psar_dir > 0, -0.45, 0))
    st_ += price_below_super.astype(float) * 0.7 + price_below_tk.astype(float) * 0.55 + cloud_bear.astype(float) * 0.8
    df["SL_Trend"] = st_.clip(-2, JT.TREND_CAP)

    sm_ = pd.Series(0.0, index=idx)
    for s, p in [("MACD_Cross_Sell", 2.5), ("MACD_Zero_Cross_Sell", 2), ("StochRSI_Cross_Sell", 2), ("ADX_Momentum_Sell", 2), ("VWAP_Reject_Sell", 1.5)]:
        sm_ += _sp(df, s, p)
    sm_ = sm_.clip(upper=6)
    sm_ += np.select([(N("MACD_Hist") < 0) & mhf, (N("MACD_Hist") < 0) & mhr, (N("MACD_Hist") > 0) & mhf], [2, 0.5, 1.5], default=0.0)
    sm_ += np.clip((N("RSI") - 60) * 0.15, 0, 3) + rf_.astype(float) + np.clip((N("StochK") - 75) * 0.15, 0, 2.5) + np.clip((N("WT1") - 10) * 0.05, 0, 3) + wf_.astype(float)
    sm_ += _sp(df, "UTBot_Sell", 2.1) + _sp(df, "Hull_Turn_Bear", 0.9) + _sp(df, "StochSlow_Cross_Sell", 1.5) + _sp(df, "Squeeze_Mom_Cross_Down", 1.5) + np.where(~hma_r_v & wf_.values, 0.8, 0)
    sm_ += np.where(ob_rev, 1.5, 0) - np.where(os_rev, 1.0, 0) + np.where(wr_fade, 0.8, 0) + np.where(cci_fade, 0.7, 0)
    sm_ += np.where(rmi <= 45, 0.7, np.where(rmi >= 55, -0.4, 0)) + np.where(trix < 0, 0.5, np.where(trix > 0, -0.3, 0))
    sm_ += np.where(roc < 0, 0.6, np.where(roc > 0, -0.4, 0)) + np.where(price_osc < 0, 0.55, np.where(price_osc > 0, -0.35, 0))
    df["SL_Momentum"] = sm_.clip(-2, JT.MOMENTUM_CAP)

    scc_ = pd.Series(0.0, index=idx)
    for s, p in [("Evening_Star", 3.5), ("Bearish_Engulfing", 3), ("Shooting_Star", 2.5), ("Outside_Bearish", 2.5), ("Doji_Bearish", 1), ("Three_Bar_Reversal_Sell", 2.5)]:
        scc_ = np.maximum(scc_, _sp(df, s, p))
    df["SL_Candle"] = pd.Series(scc_, index=idx).clip(upper=JT.CANDLE_CAP)

    sbb_ = pd.Series(0.0, index=idx)
    sbb_ += _sp(df, "BB_Squeeze_End_Bear", 3) + _sp(df, "NR7_2", 1.5) + _sp(df, "Calm_After_Storm", 1)
    sbb_ += np.clip((pb - 0.5) * 6, -2, 3) + _sp(df, "BB_Lower_Break", 1.5) + np.where((env_pct >= 0.80) & (C < O), 1.0, 0) - np.where((env_pct <= 0.20) & (C > O), 0.7, 0)
    df["SL_BB"] = sbb_.clip(-1, JT.BB_CAP)

    sv_ = pd.Series(0.0, index=idx)
    sv_ += _sp(df, "Volume_Climax_Sell", 3) + _sp(df, "OBV_Div_Sell", 1.5) + _sp(df, "Volume_POC_Breakdown", 2.5) + _sp(df, "Volume_Dry_Breakout_Sell", 2)
    sv_ += np.clip((vr - 1) * 1.5, 0, 3) * (C < O).astype(float) + np.where(obv < obvm, 1, np.where(obv > obvm, -1, 0))
    sv_ += np.where((vol_osc < 0) & (C < O), 0.9, np.where((vol_osc > 0) & (C > O), -0.7, 0)) + np.where(dv_z > 0.35, 0.25, np.where(dv_z < -0.35, 0.55, 0))
    sv_ -= np.where(F("Thin_Trade_Risk"), 1.2, 0)
    df["SL_Volume"] = sv_.clip(-1, JT.VOLUME_CAP)

    smf_ = pd.Series(0.0, index=idx)
    smf_ += np.clip(rmfi * 0.2, -0.5, 2) + _sp(df, "MF_Cross_Bear", 2) + _sp(df, "MF_Bear_Div", 2) + _sp(df, "MF_Accel_Dn", 1) + _sp(df, "CMF_Bear", 1.5)
    smf_ += np.clip(-cmf * 8, -1, 2) + np.where(intensity_idx < -10, 0.9, np.where(intensity_idx > 10, -0.7, 0))
    smf_ += np.where(chaikin < 0, 0.8, np.where(chaikin > 0, -0.8, 0)) + np.where(ad_z < -0.4, 0.7, np.where(ad_z > 0.4, -0.7, 0))
    df["SL_MF"] = smf_.clip(-1, JT.MF_CAP)

    spp_ = pd.Series(0.0, index=idx)
    spp_ += _spd(df, "Blood_Diamond", 4)
    spp_ += np.where(spp_ == 0, _spd(df, "Red_Dot_T1", 2.5), 0)
    for s, p in [
        ("Bear_Divergence", 2),
        ("Pullback_123_Bear", 2.5),
        ("Setup_180_Bear", 2),
        ("Boomer_Sell", 2),
        ("Expansion_BD", 3),
        ("Gilligans_Sell", 2.5),
        ("Lizard_Bear", 2),
        ("NonADX_123_Bear", 1.5),
        ("EMA_Pullback_Sell", 2),
        ("Momentum_Ignition_Sell", 3),
        ("SuperTrend_Sell", 2),
        ("Parabolic_Top_Sell", 3),
        ("Kumo_Breakout_Bear", 2.5),
        ("Reversal_New_Lows", 2.5),
        ("Slingshot_Bear", 2),
        ("Jack_In_Box_Bear", 2),
        ("Relative_Strength_Sell", 2),
        ("VP_VAH_Resistance", 1.5),
        ("VuManChu_Bear", 3),
        ("Hull_Turn_Bear", JT.TURN_SIGNAL_PATTERN_SELL),
        ("Doji_Breakout_Sell", 1.5),
        ("Three_Bar_Reversal_Sell", 2),
        ("CS_Top_Fishing_Sell", 3),
        ("CS_Overbought_Fade_Sell", 1.5),
    ]:
        spp_ += _sp(df, s, p)
    spp_ += _sp(df, "Diag_Resistance_Reject", 1.8) + _sp(df, "Diag_Breakdown_Bear", 2.2)
    spp_ += _sp(df, "Box_Resistance_Reject", 1.8) + _sp(df, "Channel_Resistance_Reject", 2.0)
    spp_ += _sp(df, "Box_Breakdown_Bear", 2.4) + _sp(df, "Channel_Breakdown_Bear", 2.5) + _sp(df, "Triangle_Breakdown_Bear", 2.8)
    spp_ += _sp(df, "Fib_382_Resistance", 1.2) + _sp(df, "Fib_50_Resistance", 1.5) + _sp(df, "Fib_618_Resistance", 2.0)
    spp_ += _sp(df, "Fib_618_Breakdown", 2.2) + _sp(df, "Fib_Confluence_Sell", 2.5)
    df["SL_Pattern"] = spp_.clip(upper=JT.PATTERN_CAP)

    scs_ = pd.Series(0.0, index=idx)
    for cn, cfg in combo_registry.items():
        if cfg["dir"] != "sell" or cn not in df.columns:
            continue
        scs_ += np.where(df[cn].fillna(False), {1: JT.COMBO_T1, 2: JT.COMBO_T2, 3: JT.COMBO_T3}.get(cfg["tier"], 1), 0.0)
    df["SL_Combined"] = scs_.clip(upper=JT.COMBINED_CAP)

    sl__ = pd.Series(0.0, index=idx)
    sl__ += np.clip(-ca * 2.5, -1, 3.5) + _sp(df, "Setup_Squeeze_Bear", 1.5) + _sp(df, "Momentum_Accel_Sell", 2) + _sp(df, "WT_Convergence_Bear", 1.5) + np.where(ob_rev, 1.2, 0) + _sp(df, "CS_Top_Fishing_Sell", 2)
    sl__ += np.where(utbot_dir == -1, 1, np.where(utbot_dir == 1, -0.5, 0)) + np.where(~hma_r_v, 0.5, -0.5)
    sp_sell = pd.Series(0.0, index=idx)
    sp_sell += np.clip((N("WT1") + 10) * 0.05, 0, 2) + np.clip((N("RSI") - 55) * 0.1, 0, 2) + np.clip((N("StochK") - 65) * 0.1, 0, 1) + np.clip((mfi - 65) * 0.08, 0, 1.5) + np.clip(-ca * 1.5, 0, 2)
    sp_sell += np.where(ob_rev, 1.0, 0)
    sl__ += np.where((ma20_gap >= 1.6) & (C < O), 1.0, 0) - np.where(ma20_gap <= -2.4, 1.2, 0)
    sl__ += np.where((channel_pos >= 0.6) & (C < O), 0.7, 0) + np.where(price_below_vwap & (channel_pos > -0.15), 0.45, 0)
    sl__ -= np.where(F("Fib_Ext_1618_Down_Hit"), 1.0, 0)
    df["Setup_Pressure_Sell"] = sp_sell
    sl__ += np.clip(sp_sell * 0.4, 0, 3)
    df["SL_Leading"] = sl__.clip(-1, JT.LEADING_CAP)

    slag_ = pd.Series(0.0, index=idx)
    slag_ += b200.astype(float) * 1.0 + b50.astype(float) * 1.0 + ((ma50_ready & ma200_ready) & (N("MA50", np.nan) < N("MA200", np.nan))).astype(float) * 1.0
    slag_ += np.clip(-regime.values * 1.0, -1.5, 3) + np.where(kumo_ready & (C < kumo_bot), 1.5, np.where(kumo_ready & (C > kumo_top), -1, 0)) + np.clip((1.0 - N("RS_Ratio", 1)) * 30, -1.5, 2)
    slag_ += np.where(price_below_tk, 0.6, 0) + np.where(price_below_super, 0.5, 0) + np.where(price_below_fixed, 0.35, 0)
    df["SL_Lagging"] = slag_.clip(-2, JT.LAGGING_CAP)

    layer_names = ["Trend", "Momentum", "Candle", "BB", "Volume", "MF", "Pattern", "Combined", "Leading", "Lagging"]
    return apply_layer_totals(df, layer_names, combo_registry)
