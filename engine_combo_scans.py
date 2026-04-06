from __future__ import annotations

import pandas as pd

from config import COMBINED_SCAN_REGISTRY, JT
from utils import _cooldown


def detect_combined_scans(df, vol_ratio, hma_rising, registry=None):
    active_registry = registry or COMBINED_SCAN_REGISTRY
    idx = df.index
    C, O, H, L, V = df["Close"], df["Open"], df["High"], df["Low"], df["Volume"]
    F = lambda c: df.get(c, pd.Series(False, index=idx)).fillna(False)
    N = lambda c, d=0: df.get(c, pd.Series(d, index=idx)).fillna(d)
    vr = vol_ratio
    up_ = (C > N("MA50")) & (N("MA50") > N("MA200")) & (N("Plus_DI") > N("Minus_DI"))
    dn_ = (C < N("MA50")) & (N("MA50") < N("MA200")) & (N("Minus_DI") > N("Plus_DI"))
    adx_ok = N("ADX") > 20
    vs_ = vr >= 2
    vok_ = vr >= 1
    bc_ = F("Bullish_Engulfing") | F("Morning_Star") | F("Hammer") | F("Doji_Bullish")
    sc__ = F("Bearish_Engulfing") | F("Evening_Star") | F("Shooting_Star") | F("Doji_Bearish")
    cb_ = F("Pullback_123_Bull") | F("NonADX_123_Bull") | F("Setup_180_Bull") | F("Boomer_Buy") | F("Expansion_BO") | F("Gilligans_Buy") | F("Lizard_Bull")
    cs___ = F("Pullback_123_Bear") | F("NonADX_123_Bear") | F("Setup_180_Bear") | F("Boomer_Sell") | F("Expansion_BD") | F("Gilligans_Sell") | F("Lizard_Bear")
    mfb_ = (N("RSI_MFI") > N("RSI_MFI").shift(1)) | (N("CMF") > 0.05) | F("MF_Cross_Bull")
    mfs_ = (N("RSI_MFI") < N("RSI_MFI").shift(1)) | (N("CMF") < -0.05) | F("MF_Cross_Bear")
    n_bl = C <= N("BB_Low") * 1.01
    n_bu = C >= N("BB_Up") * 0.99
    n_vp = ((C - N("VP_VAL")).abs() / (C + 1e-10) < 0.02) & (N("VP_VAL") > 0)
    n_vr = ((N("VP_VAH") - C).abs() / (C + 1e-10) < 0.02) & (N("VP_VAH") > 0)
    n50 = ((C - N("MA50")).abs() / (C + 1e-10)) < 0.03
    wos_ = N("WT1") < -53
    wob_ = N("WT1") > 53
    sos_ = (N("StochK") < 20) & (N("StochD") < 20)
    sob_ = (N("StochK") > 80) & (N("StochD") > 80)
    dbc_ = F("Bull_Divergence").astype(int) + F("RSI_Bull_Divergence").astype(int) + F("MF_Bull_Div").astype(int) + F("OBV_Div_Buy").astype(int)
    dsc_ = F("Bear_Divergence").astype(int) + F("RSI_Bear_Divergence").astype(int) + F("MF_Bear_Div").astype(int) + F("OBV_Div_Sell").astype(int)
    mr_ = N("MACD_Hist") > N("MACD_Hist").shift(1)
    mf_ = N("MACD_Hist") < N("MACD_Hist").shift(1)
    wr_ = N("WT1") > N("WT1").shift(1)
    wf_ = N("WT1") < N("WT1").shift(1)
    llw_ = (pd.concat([C, O], axis=1).min(axis=1) - L) > (H - L) * 0.6
    luw_ = (H - pd.concat([C, O], axis=1).max(axis=1)) > (H - L) * 0.6
    ma20 = N("MA20")
    ma50 = N("MA50")
    d20 = (C - ma20) / (ma20 + 1e-10)
    d50 = (C - ma50) / (ma50 + 1e-10)
    deep_os = (N("WT1") < -65) | (N("RSI") < 30) | (N("StochK") < 15)
    deep_ob = (N("WT1") > 65) | (N("RSI") > 70) | (N("StochK") > 85)
    down_stretch = (d20 < -0.06) | (d50 < -0.1) | (C <= N("BB_Low") * 0.985)
    up_stretch = (d20 > 0.06) | (d50 > 0.1) | (C >= N("BB_Up") * 1.015)
    bull_turn = (C > O) & (C > C.shift(1)) & (F("WT_Up") | F("MACD_Cross_Buy") | F("StochRSI_Cross_Buy") | F("UTBot_Buy") | F("Hull_Turn_Bull"))
    bear_turn = (C < O) & (C < C.shift(1)) & (F("WT_Down") | F("MACD_Cross_Sell") | F("StochRSI_Cross_Sell") | F("UTBot_Sell") | F("Hull_Turn_Bear"))

    ub_ = (
        (up_ | (C > N("MA50"))).astype(int)
        + ((wr_ | F("WT_Up")) & (mr_ | (N("MACD_Hist") > 0))).astype(int)
        + (bc_ | cb_).astype(int)
        + vok_.astype(int)
        + mfb_.astype(int)
        + (n50 | F("BB_Squeeze_End_Bull") | n_vp).astype(int)
    )
    df["CS_Ultimate_Buy"] = ub_ >= 6
    tos_ = (wos_ | (N("WT1") < -60)) & ((N("RSI") < 30) | (N("RSI") < 35)) & sos_
    df["CS_Triple_Oversold_Reversal"] = tos_ & (F("WT_Up") | wr_ | bc_ | llw_ | F("Gold_Dot") | F("Green_Dot_T1")) & vok_
    df["CS_Breakout_Momentum_Buy"] = (F("New_52W_High") | F("Expansion_BO") | (C > N("BB_Up"))) & adx_ok & (N("Plus_DI") > N("Minus_DI")) & vs_ & mr_
    df["CS_Institutional_Accumulation"] = (F("Pocket_Pivot") | (F("NR7") & (N("OBV") > N("OBV").shift(5))) | (F("Calm_After_Storm") & (C > O))) & (C > N("MA50")) & (N("CMF") > 0.05) & (N("OBV") > N("OBV").shift(5))
    df["CS_Divergence_Confluence_Buy"] = (dbc_ >= 2) & (n_bl | n_vp | n50) & (bc_ | llw_ | F("WT_Up")) & vok_
    el_ = F("New_52W_Low") | (C <= C.rolling(252, min_periods=200).min() * 1.02)
    eos_ = (N("WT1") < -80) | (wos_ & (N("RSI") < 25))
    df["CS_Capitulation_Bottom"] = el_ & eos_ & (vr >= 3) & (llw_ | F("Hammer") | F("Parabolic_Bottom_Buy")) & (N("MFI") < 30)
    df["CS_Triple_Confirm_Buy"] = F("UTBot_Buy") & hma_rising & (N("WT1") > N("WT2")) & vok_
    df["CS_VuManChu_Squeeze_Buy"] = F("VuManChu_Bull") & (F("Squeeze_Fire_Buy") | F("Squeeze_Mom_Cross_Up"))

    us__ = (
        (dn_ | (C < N("MA50"))).astype(int)
        + ((wf_ | F("WT_Down")) & (mf_ | (N("MACD_Hist") < 0))).astype(int)
        + (sc__ | cs___).astype(int)
        + vok_.astype(int)
        + mfs_.astype(int)
        + (n50 | F("BB_Squeeze_End_Bear") | n_vr).astype(int)
    )
    df["CS_Ultimate_Sell"] = us__ >= 6
    tob_ = (wob_ | (N("WT1") > 60)) & ((N("RSI") > 70) | (N("RSI") > 65)) & sob_
    df["CS_Triple_Overbought_Exhaustion"] = tob_ & (F("WT_Down") | wf_ | sc__ | luw_ | F("Blood_Diamond") | F("Red_Dot_T1")) & vok_
    df["CS_Breakdown_Momentum_Sell"] = (F("New_52W_Low") | F("Expansion_BD") | (C < N("BB_Low"))) & adx_ok & (N("Minus_DI") > N("Plus_DI")) & vs_ & mf_
    para_ = (C > C.shift(10) * 1.3) | F("Parabolic_Top_Sell")
    eob_ = (N("WT1") > 80) | (wob_ & (N("RSI") > 75))
    df["CS_Parabolic_Exhaustion_Sell"] = para_ & eob_ & (luw_ | F("Shooting_Star") | sc__) & (vr >= 3)
    df["CS_Divergence_Confluence_Sell"] = (dsc_ >= 2) & (n_bu | n_vr | n50) & (sc__ | luw_ | F("WT_Down")) & vok_
    eh_ = F("New_52W_High") | (C >= C.rolling(252, min_periods=200).max() * 0.98)
    df["CS_Blow_Off_Top"] = eh_ & eob_ & (vr >= 3) & (luw_ | F("Shooting_Star") | F("Parabolic_Top_Sell")) & (N("MFI") > 70)
    df["CS_Triple_Confirm_Sell"] = F("UTBot_Sell") & ~hma_rising & (N("WT1") < N("WT2")) & vok_
    df["CS_VuManChu_Squeeze_Sell"] = F("VuManChu_Bear") & (F("Squeeze_Fire_Sell") | F("Squeeze_Mom_Cross_Down"))

    df["CS_Trend_Pullback_Buy"] = up_ & (n50 | ((L <= N("MA20")) & (C > N("MA20")))) & (bc_ | (C > O)) & mfb_
    df["CS_Squeeze_Breakout_Buy"] = (F("BB_Squeeze_End_Bull") | (F("BB_Squeeze").shift(1) & (C > N("BB_Mid")) & (C > O))) & vok_ & mr_
    df["CS_MA_Confluence_Buy"] = ((N("MA50") > N("MA200")) & (N("MA50") > N("MA50").shift(5))) & (F("MACD_Cross_Buy") | mr_) & vok_ & (C > N("MA50"))
    df["CS_Cooper_Setup_Buy"] = cb_ & adx_ok & (N("Plus_DI") > N("Minus_DI")) & vok_ & (C > N("MA50"))
    df["CS_Volume_Climax_Rev_Buy"] = (F("Volume_Climax_Buy") | (vr >= 2.5)) & (wos_ | sos_) & (bc_ | llw_) & (n_bl | n_vp)
    df["CS_Ichimoku_Breakout_Buy"] = F("Kumo_Breakout_Bull") & (F("TK_Cross_Bull") | adx_ok) & vok_

    df["CS_Trend_Rejection_Sell"] = dn_ & (n50 | ((H >= N("MA20")) & (C < N("MA20")))) & (sc__ | (C < O)) & mfs_
    df["CS_Squeeze_Breakdown_Sell"] = (F("BB_Squeeze_End_Bear") | (F("BB_Squeeze").shift(1) & (C < N("BB_Mid")) & (C < O))) & vok_ & mf_
    df["CS_MA_Breakdown_Sell"] = ((N("MA50") < N("MA200")) & (N("MA50") < N("MA50").shift(5))) & (F("MACD_Cross_Sell") | mf_) & vok_ & (C < N("MA50"))
    df["CS_Cooper_Setup_Sell"] = cs___ & adx_ok & (N("Minus_DI") > N("Plus_DI")) & vok_ & (C < N("MA50"))
    df["CS_Gap_Failure_Sell"] = (F("Gap_Up").shift(1).fillna(False) & sc__ & vok_ & wf_) | (F("Gap_Up") & (C < O) & vok_)
    df["CS_Ichimoku_Breakout_Sell"] = F("Kumo_Breakout_Bear") & (F("TK_Cross_Bear") | adx_ok) & vok_

    os_ctx = (N("WT1") < -55) | (N("RSI") < 35) | (N("StochK") < 25)
    ob_ctx = (N("WT1") > 55) | (N("RSI") > 65) | (N("StochK") > 75)
    trend_favor_buy = (N("Plus_DI") >= N("Minus_DI")) | (N("ADX") < 25)
    trend_favor_sell = (N("Minus_DI") >= N("Plus_DI")) | (N("ADX") < 25)

    df["CS_Oversold_Bounce_Buy"] = sos_ & bc_ & (n50 | n_bl) & (wr_ | mr_ | mfb_) & trend_favor_buy
    df["CS_Overbought_Fade_Sell"] = sob_ & sc__ & (n50 | n_bu) & (wf_ | mf_ | mfs_) & trend_favor_sell

    df["CS_Trend_Continuation_Buy"] = up_ & (C > N("MA20")) & (F("EMA_Pullback_Buy") | F("MA20_Support") | F("MA50_Support") | F("Diag_Support_Hold") | F("Diag_Breakout_Bull") | F("Box_Support_Hold") | F("Channel_Support_Hold") | F("Box_Breakout_Bull") | F("Channel_Breakout_Bull") | F("Triangle_Breakout_Bull")) & (wr_ | mr_) & (vr >= 1.0) & (N("ADX") >= 18)
    df["CS_Trend_Continuation_Sell"] = dn_ & (C < N("MA20")) & (F("EMA_Pullback_Sell") | F("MA20_Resistance") | F("MA50_Resistance") | F("Diag_Resistance_Reject") | F("Diag_Breakdown_Bear") | F("Box_Resistance_Reject") | F("Channel_Resistance_Reject") | F("Box_Breakdown_Bear") | F("Channel_Breakdown_Bear") | F("Triangle_Breakdown_Bear")) & (wf_ | mf_) & (vr >= 1.0) & (N("ADX") >= 18)
    df["CS_Trend_Continuation_Buy"] = df["CS_Trend_Continuation_Buy"] | (up_ & (wr_ | mr_) & (vr >= 0.9) & (N("ADX") >= 16) & (F("Fib_50_Support") | F("Fib_618_Support") | F("Fib_618_Reclaim") | F("Fib_Confluence_Buy")))
    df["CS_Trend_Continuation_Sell"] = df["CS_Trend_Continuation_Sell"] | (dn_ & (wf_ | mf_) & (vr >= 0.9) & (N("ADX") >= 16) & (F("Fib_50_Resistance") | F("Fib_618_Resistance") | F("Fib_618_Breakdown") | F("Fib_Confluence_Sell")))
    df["CS_Reversal_Cluster_Buy"] = (dbc_ >= 2) & os_ctx & (bc_ | llw_ | F("Parabolic_Bottom_Buy") | F("Volume_Climax_Buy")) & (wr_ | F("UTBot_Buy") | F("Hull_Turn_Bull")) & vok_
    df["CS_Reversal_Cluster_Sell"] = (dsc_ >= 2) & ob_ctx & (sc__ | luw_ | F("Parabolic_Top_Sell") | F("Volume_Climax_Sell")) & (wf_ | F("UTBot_Sell") | F("Hull_Turn_Bear")) & vok_
    df["CS_Breakout_Confirm_Buy"] = (F("Expansion_BO") | F("Kumo_Breakout_Bull") | F("BB_Upper_Break") | F("New_52W_High") | F("Box_Breakout_Bull") | F("Channel_Breakout_Bull") | F("Triangle_Breakout_Bull")) & (vr >= 1.4) & (N("ADX") >= 20) & (N("MACD_Hist") > N("MACD_Hist").shift(1))
    df["CS_Breakout_Confirm_Sell"] = (F("Expansion_BD") | F("Kumo_Breakout_Bear") | F("BB_Lower_Break") | F("New_52W_Low") | F("Box_Breakdown_Bear") | F("Channel_Breakdown_Bear") | F("Triangle_Breakdown_Bear")) & (vr >= 1.4) & (N("ADX") >= 20) & (N("MACD_Hist") < N("MACD_Hist").shift(1))
    df["CS_Breakout_Confirm_Buy"] = df["CS_Breakout_Confirm_Buy"] | ((F("Fib_618_Reclaim") | F("Fib_Confluence_Buy")) & (vr >= 1.0) & (N("ADX") >= 18) & (N("MACD_Hist") >= N("MACD_Hist").shift(1)))
    df["CS_Breakout_Confirm_Sell"] = df["CS_Breakout_Confirm_Sell"] | ((F("Fib_618_Breakdown") | F("Fib_Confluence_Sell")) & (vr >= 1.0) & (N("ADX") >= 18) & (N("MACD_Hist") <= N("MACD_Hist").shift(1)))

    df["CS_Momentum_Accel_Buy"] = (N("Composite_Accel", 0) > JT.ACCEL_STRONG) & vok_ & (C > N("MA50"))
    df["CS_Structure_Support_Buy"] = n_vp & n_bl & (C > O)
    df["CS_Volatility_Explosion"] = (F("NR7_2").astype(int) + F("BB_Squeeze").astype(int) + (vr < 0.5).astype(int) + F("Inside_Day").astype(int)) >= 3
    df["CS_Bottom_Fishing_Buy"] = deep_os & down_stretch & bull_turn & (dbc_ >= 1) & (llw_ | bc_ | cb_) & vok_
    df["CS_Top_Fishing_Sell"] = deep_ob & up_stretch & bear_turn & (dsc_ >= 1) & (luw_ | sc__ | cs___) & vok_

    buy_cluster = df["CS_Reversal_Cluster_Buy"] | df["CS_Trend_Continuation_Buy"] | df["CS_Breakout_Confirm_Buy"]
    sell_cluster = df["CS_Reversal_Cluster_Sell"] | df["CS_Trend_Continuation_Sell"] | df["CS_Breakout_Confirm_Sell"]
    df["CS_Conflict_Warning"] = buy_cluster & sell_cluster

    for scan_name, cfg in active_registry.items():
        if scan_name in df.columns:
            df[scan_name] = _cooldown(df[scan_name], bars={1: 5, 2: 7, 3: 10}.get(cfg.get("tier", 2), 7))

    buy_cols = [scan_name for scan_name, cfg in active_registry.items() if scan_name in df.columns and cfg.get("dir") == "buy"]
    sell_cols = [scan_name for scan_name, cfg in active_registry.items() if scan_name in df.columns and cfg.get("dir") == "sell"]
    neutral_cols = [scan_name for scan_name, cfg in active_registry.items() if scan_name in df.columns and cfg.get("dir") == "neutral"]
    t1_cols = [scan_name for scan_name, cfg in active_registry.items() if scan_name in df.columns and cfg.get("tier") == 1]
    t2_cols = [scan_name for scan_name, cfg in active_registry.items() if scan_name in df.columns and cfg.get("tier") == 2]
    t3_cols = [scan_name for scan_name, cfg in active_registry.items() if scan_name in df.columns and cfg.get("tier") == 3]

    bcnt = sum(df[c].fillna(False).astype(int) for c in buy_cols) if buy_cols else pd.Series(0, index=idx, dtype=int)
    scnt = sum(df[c].fillna(False).astype(int) for c in sell_cols) if sell_cols else pd.Series(0, index=idx, dtype=int)
    ncnt = sum(df[c].fillna(False).astype(int) for c in neutral_cols) if neutral_cols else pd.Series(0, index=idx, dtype=int)
    t1cnt = sum(df[c].fillna(False).astype(int) for c in t1_cols) if t1_cols else pd.Series(0, index=idx, dtype=int)
    t2cnt = sum(df[c].fillna(False).astype(int) for c in t2_cols) if t2_cols else pd.Series(0, index=idx, dtype=int)
    t3cnt = sum(df[c].fillna(False).astype(int) for c in t3_cols) if t3_cols else pd.Series(0, index=idx, dtype=int)
    mcnt = bcnt + scnt + ncnt
    df["CS_Buy_Count"] = bcnt
    df["CS_Sell_Count"] = scnt
    df["CS_Neutral_Count"] = ncnt
    df["CS_T1_Count"] = t1cnt
    df["CS_T2_Count"] = t2cnt
    df["CS_T3_Count"] = t3cnt
    df["CS_Multi_Count"] = mcnt
    df["CS_Multi_Imbalance"] = bcnt - scnt
    df["CS_Multi_Signal_On"] = (mcnt >= 3) | ((t1cnt >= 1) & (mcnt >= 2))
    return df
