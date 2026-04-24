from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd


def build_market_state(dc: pd.DataFrame) -> dict:
    frame = dc.copy()
    latest = frame.iloc[-1]
    previous = frame.iloc[-2] if len(frame) > 1 else latest
    close = scalar(latest.get("Close"))
    atr = max(scalar(latest.get("ATR")), close * 0.01, 0.01)
    prev_window = frame.iloc[:-1] if len(frame) > 1 else frame
    recent5 = frame.tail(5)
    recent20 = frame.tail(20)
    breakout_level = series_max(prev_window, "High", default=close)
    breakdown_level = series_min(prev_window, "Low", default=close)
    swing_high_5 = series_max(recent5, "High", default=close)
    swing_low_5 = series_min(recent5, "Low", default=close)
    swing_high_20 = series_max(recent20, "High", default=close)
    swing_low_20 = series_min(recent20, "Low", default=close)
    ema8 = scalar(latest.get("EMA8"), close)
    ema15 = scalar(latest.get("EMA15"), close)
    ema21 = scalar(latest.get("EMA21"), close)
    ema25 = scalar(latest.get("EMA25"), close)
    ema50 = scalar(latest.get("EMA50"), scalar(latest.get("MA50"), close))
    ema200 = scalar(latest.get("EMA200"), scalar(latest.get("MA200"), close))
    hma25 = scalar(latest.get("HMA25"), scalar(latest.get("HMA"), close))
    ma20 = scalar(latest.get("MA20"), close)
    ma50 = scalar(latest.get("MA50"), close)
    ma200 = scalar(latest.get("MA200"), close)
    vwap = scalar(latest.get("VWAP"), close)
    fixed_vwap = scalar(latest.get("Fixed_VWAP"), vwap)
    supertrend = scalar(latest.get("SuperTrend"), close)
    price_channel_up = scalar(latest.get("Price_Channel_Up"), breakout_level)
    price_channel_low = scalar(latest.get("Price_Channel_Low"), breakdown_level)
    price_channel_mid = scalar(latest.get("Price_Channel_Mid"), (price_channel_up + price_channel_low) / 2.0)
    bb_up = scalar(latest.get("BB_Up"), swing_high_20)
    bb_low = scalar(latest.get("BB_Low"), swing_low_20)
    kc_upper = scalar(latest.get("KC_Upper"), bb_up)
    kc_mid = scalar(latest.get("KC_Mid"), ma20)
    kc_lower = scalar(latest.get("KC_Lower"), bb_low)
    vp_vah = scalar(latest.get("VP_VAH"), np.nan)
    vp_val = scalar(latest.get("VP_VAL"), np.nan)
    vp_poc = scalar(latest.get("VP_POC"), np.nan)
    fib_382 = scalar(latest.get("Fib_382"), np.nan)
    fib_50 = scalar(latest.get("Fib_50"), np.nan)
    fib_618 = scalar(latest.get("Fib_618"), np.nan)
    fib_ext_up = scalar(latest.get("Fib_Ext_1618_Up"), np.nan)
    fib_ext_down = scalar(latest.get("Fib_Ext_1618_Down"), np.nan)
    tenkan = scalar(latest.get("Ichimoku_Tenkan"), np.nan)
    kijun = scalar(latest.get("Ichimoku_Kijun"), np.nan)
    senkou_a = scalar(latest.get("Ichimoku_SenkouA"), np.nan)
    senkou_b = scalar(latest.get("Ichimoku_SenkouB"), np.nan)
    cloud_top = finite_max([senkou_a, senkou_b], np.nan)
    cloud_bottom = finite_min([senkou_a, senkou_b], np.nan)
    volume_ratio = max(scalar(latest.get("Volume_Ratio_20"), 1.0), 0.0)
    volume_ratio_50 = max(scalar(latest.get("Volume_Ratio_50"), volume_ratio), 0.0)
    macd_hist = scalar(latest.get("MACD_Hist"))
    macd_hist_prev = scalar(previous.get("MACD_Hist"))
    wt1 = scalar(latest.get("WT1"))
    wt1_prev = scalar(previous.get("WT1"))
    obv_slope = scalar(latest.get("OBV_Slope"))
    chaikin = scalar(latest.get("Chaikin_Oscillator"))
    cmf = scalar(latest.get("CMF"))
    composite_accel = scalar(latest.get("Composite_Accel"))
    rsi = scalar(latest.get("RSI"), 50.0)
    stochk = scalar(latest.get("StochK"), 50.0)
    mfi = scalar(latest.get("MFI"), 50.0)
    price_change_5 = pct_change(close, scalar(recent5.iloc[0].get("Close"), close))
    ema15_prev = scalar(previous.get("EMA15"), ema15)
    ema21_prev = scalar(previous.get("EMA21"), ema21)
    ema25_prev = scalar(previous.get("EMA25"), ema25)
    ema50_prev = scalar(previous.get("EMA50"), ema50)
    ema200_prev = scalar(previous.get("EMA200"), ema200)
    hma25_prev = scalar(previous.get("HMA25"), scalar(previous.get("HMA"), hma25))
    ma50_prev = scalar(previous.get("MA50"), ma50)
    vwap_prev = scalar(previous.get("VWAP"), vwap)
    fixed_vwap_prev = scalar(previous.get("Fixed_VWAP"), fixed_vwap)
    chaikin_prev = scalar(previous.get("Chaikin_Oscillator"), chaikin)
    bb_width = scalar(latest.get("BB_Width"))
    bb_width_prev = scalar(previous.get("BB_Width"), bb_width)
    recent_fractal_high = recent_flagged_level(frame, "Fractal_High", "High", default=swing_high_20)
    recent_fractal_low = recent_flagged_level(frame, "Fractal_Low", "Low", default=swing_low_20)

    ema15_slope_up = bool(latest.get("EMA15_Slope_Up")) if "EMA15_Slope_Up" in frame.columns else ema15 >= ema15_prev
    ema25_slope_up = bool(latest.get("EMA25_Slope_Up")) if "EMA25_Slope_Up" in frame.columns else ema25 >= ema25_prev
    ema50_slope_up = bool(latest.get("EMA50_Slope_Up")) if "EMA50_Slope_Up" in frame.columns else ema50 >= ema50_prev
    hma25_slope_up = bool(latest.get("HMA25_Slope_Up")) if "HMA25_Slope_Up" in frame.columns else hma25 >= hma25_prev
    ema15_slope_down = bool(latest.get("EMA15_Slope_Down")) if "EMA15_Slope_Down" in frame.columns else ema15 <= ema15_prev
    ema25_slope_down = bool(latest.get("EMA25_Slope_Down")) if "EMA25_Slope_Down" in frame.columns else ema25 <= ema25_prev
    ema50_slope_down = bool(latest.get("EMA50_Slope_Down")) if "EMA50_Slope_Down" in frame.columns else ema50 <= ema50_prev
    hma25_slope_down = bool(latest.get("HMA25_Slope_Down")) if "HMA25_Slope_Down" in frame.columns else hma25 <= hma25_prev

    hma25_ema25_cross_bull = bool(latest.get("HMA25_EMA25_Cross_Bull")) if "HMA25_EMA25_Cross_Bull" in frame.columns else (hma25 >= ema25 and hma25_prev <= ema25_prev)
    hma25_ema25_cross_bear = bool(latest.get("HMA25_EMA25_Cross_Bear")) if "HMA25_EMA25_Cross_Bear" in frame.columns else (hma25 <= ema25 and hma25_prev >= ema25_prev)
    hma25_ema15_cross_bear = bool(latest.get("HMA25_EMA15_Cross_Bear")) if "HMA25_EMA15_Cross_Bear" in frame.columns else (hma25 <= ema15 and hma25_prev >= ema15_prev)
    hma25_ema15_cross_bull = bool(latest.get("HMA25_EMA15_Cross_Bull")) if "HMA25_EMA15_Cross_Bull" in frame.columns else (hma25 >= ema15 and hma25_prev <= ema15_prev)

    hma_ema_long_aligned = bool(latest.get("HMA_EMA_Long_Aligned")) if "HMA_EMA_Long_Aligned" in frame.columns else (
        close > ema200
        and hma25 > ema25
        and hma25 > ema15
        and ema15_slope_up
        and ema25_slope_up
        and ema50_slope_up
        and hma25_slope_up
    )
    hma_ema_short_aligned = bool(latest.get("HMA_EMA_Short_Aligned")) if "HMA_EMA_Short_Aligned" in frame.columns else (
        close < ema200
        and hma25 < ema25
        and hma25 < ema15
        and ema15_slope_down
        and ema25_slope_down
        and ema50_slope_down
        and hma25_slope_down
    )
    hma_ema_long_entry = bool(latest.get("HMA_EMA_Long_Entry")) if "HMA_EMA_Long_Entry" in frame.columns else (hma25_ema25_cross_bull and hma_ema_long_aligned)
    hma_ema_short_entry = bool(latest.get("HMA_EMA_Short_Entry")) if "HMA_EMA_Short_Entry" in frame.columns else (hma25_ema25_cross_bear and hma_ema_short_aligned)

    hma_ema_risk_to_ema50_pct = scalar(
        latest.get("HMA_EMA_Risk_To_EMA50_Pct"),
        (abs(close - ema50) / max(abs(close), 1e-9)) * 100.0,
    )
    hma_ema_ema50_ema200_gap_pct = scalar(
        latest.get("HMA_EMA_EMA50_EMA200_Gap_Pct"),
        (abs(ema50 - ema200) / max(abs(close), 1e-9)) * 100.0,
    )

    long_risk = close - ema50
    short_risk = ema50 - close
    hma_ema_long_rr_valid = close > ema50 and long_risk > 0.0
    hma_ema_short_rr_valid = close < ema50 and short_risk > 0.0

    hma_ema_long_virtual_stop = ema50 if hma_ema_long_rr_valid else None
    hma_ema_short_virtual_stop = ema50 if hma_ema_short_rr_valid else None
    hma_ema_long_target_2r = (close + (2.0 * long_risk)) if hma_ema_long_rr_valid else None
    hma_ema_short_target_2r = (close - (2.0 * short_risk)) if hma_ema_short_rr_valid else None
    hma_ema_long_target_3r = (close + (3.0 * long_risk)) if hma_ema_long_rr_valid else None
    hma_ema_short_target_3r = (close - (3.0 * short_risk)) if hma_ema_short_rr_valid else None

    if hma_ema_long_entry:
        hma_ema_signal_state = "LONG_ENTRY"
    elif hma_ema_long_aligned:
        hma_ema_signal_state = "LONG_ALIGNED"
    elif hma_ema_short_entry:
        hma_ema_signal_state = "SHORT_ENTRY"
    elif hma_ema_short_aligned:
        hma_ema_signal_state = "SHORT_ALIGNED"
    else:
        hma_ema_signal_state = "NEUTRAL"

    bullish_reversal_candle = any(
        bool_latest(frame, column)
        for column in ("Hammer", "Bullish_Engulfing", "Morning_Star", "Outside_Bullish", "Doji_Bullish", "Three_Bar_Reversal_Buy")
    )
    bearish_reversal_candle = any(
        bool_latest(frame, column)
        for column in ("Shooting_Star", "Bearish_Engulfing", "Evening_Star", "Outside_Bearish", "Doji_Bearish", "Three_Bar_Reversal_Sell")
    )

    return {
        "frame": frame,
        "price": {
            "close": close,
            "open": scalar(latest.get("Open"), close),
            "high": scalar(latest.get("High"), close),
            "low": scalar(latest.get("Low"), close),
            "previous_close": scalar(previous.get("Close"), close),
            "atr": atr,
            "entry": close,
            "ema8": ema8,
            "ema15": ema15,
            "ema21": ema21,
            "ema25": ema25,
            "ema50": ema50,
            "ema200": ema200,
            "hma25": hma25,
            "ma20": ma20,
            "ma50": ma50,
            "ma200": ma200,
            "vwap": vwap,
            "fixed_vwap": fixed_vwap,
            "supertrend": supertrend,
            "psar": scalar(latest.get("Parabolic_SAR"), close),
            "bb_up": bb_up,
            "bb_low": bb_low,
            "kc_upper": kc_upper,
            "kc_mid": kc_mid,
            "kc_lower": kc_lower,
            "price_channel_up": price_channel_up,
            "price_channel_low": price_channel_low,
            "price_channel_mid": price_channel_mid,
        },
        "trend": {
            "ema21_above_ma50": ema21 >= ma50,
            "ema21_below_ma50": ema21 <= ma50,
            "ema21_rising": ema21 >= ema21_prev,
            "ema21_falling": ema21 <= ema21_prev,
            "ma50_rising": ma50 >= ma50_prev,
            "ma50_falling": ma50 <= ma50_prev,
            "close_above_ema21": close >= ema21,
            "close_below_ema21": close <= ema21,
            "close_above_ma20": close >= ma20,
            "close_below_ma20": close <= ma20,
            "close_above_ma50": close >= ma50,
            "close_below_ma50": close <= ma50,
            "close_above_vwap": close >= vwap,
            "close_below_vwap": close <= vwap,
            "close_above_fixed_vwap": close >= fixed_vwap,
            "close_below_fixed_vwap": close <= fixed_vwap,
            "close_above_supertrend": close >= supertrend,
            "close_below_supertrend": close <= supertrend,
            "vwap_reclaimed_long": close >= vwap and scalar(previous.get("Close"), close) <= vwap_prev,
            "vwap_reclaimed_short": close <= vwap and scalar(previous.get("Close"), close) >= vwap_prev,
            "fixed_vwap_holding_long": close >= fixed_vwap and fixed_vwap >= fixed_vwap_prev,
            "fixed_vwap_holding_short": close <= fixed_vwap and fixed_vwap <= fixed_vwap_prev,
            "supertrend_bullish": scalar(latest.get("ST_Direction")) >= 1,
            "supertrend_bearish": scalar(latest.get("ST_Direction")) <= -1,
            "psar_bullish": scalar(latest.get("PSAR_Direction")) >= 0,
            "psar_bearish": scalar(latest.get("PSAR_Direction")) < 0,
            "adx_strong": scalar(latest.get("ADX")) >= 18,
            "adx_expanding": scalar(latest.get("ADX")) >= scalar(previous.get("ADX")),
            "plus_di_dominant": scalar(latest.get("Plus_DI")) >= scalar(latest.get("Minus_DI")),
            "minus_di_dominant": scalar(latest.get("Minus_DI")) >= scalar(latest.get("Plus_DI")),
            "higher_high_recent": close >= breakout_level or bool_recent(frame, "New_52W_High", 10),
            "lower_low_recent": close <= breakdown_level or bool_recent(frame, "New_52W_Low", 10),
            "bullish_trend_stack": close >= ma50 and ma50 >= ma200,
            "bearish_trend_stack": close <= ma50 and ma50 <= ma200,
        },
        "momentum": {
            "macd_hist_positive": macd_hist >= 0,
            "macd_hist_negative": macd_hist <= 0,
            "macd_hist_rising": macd_hist >= macd_hist_prev,
            "macd_hist_falling": macd_hist <= macd_hist_prev,
            "wt_rising": wt1 >= wt1_prev,
            "wt_falling": wt1 <= wt1_prev,
            "rsi": rsi,
            "stochk": stochk,
            "mfi": mfi,
            "oversold": (rsi <= 35) or (stochk <= 25) or (wt1 <= -50),
            "overbought": (rsi >= 65) or (stochk >= 75) or (wt1 >= 50),
            "deep_oversold": (rsi <= 30) or (stochk <= 15) or (wt1 <= -65),
            "deep_overbought": (rsi >= 70) or (stochk >= 85) or (wt1 >= 65),
            "composite_accel": composite_accel,
            "momentum_up": composite_accel >= 0,
            "momentum_down": composite_accel <= 0,
            "squeeze_on": bool_latest(frame, "Squeeze_On") or bool_latest(frame, "BB_Squeeze"),
            "squeeze_recent": bool_recent(frame, "Squeeze_On", 5) or bool_recent(frame, "BB_Squeeze", 5),
            "squeeze_off": bool_latest(frame, "Squeeze_Fire_Buy") or bool_latest(frame, "Squeeze_Fire_Sell"),
            "bb_width_contracting": bb_width <= bb_width_prev,
            "chaikin_rising": chaikin >= chaikin_prev,
            "chaikin_falling": chaikin <= chaikin_prev,
        },
        "volatility": {
            "bb_width": bb_width,
            "bb_width_prev": bb_width_prev,
            "atr_pct": pct_of(atr, close),
            "channel_span_pct": pct_of(price_channel_up - price_channel_low, close),
        },
        "volume_flow": {
            "volume_ratio": volume_ratio,
            "volume_ratio_50": volume_ratio_50,
            "volume_support": volume_ratio >= 1.0 or volume_ratio_50 >= 1.0,
            "volume_burst": volume_ratio >= 1.4,
            "volume_dry_up": bool_recent(frame, "Volume_Dry_Up", 2),
            "obv_rising": scalar(latest.get("OBV")) >= series_mean(recent20, "OBV", default=scalar(latest.get("OBV"))),
            "obv_slope_positive": obv_slope >= 0,
            "obv_slope_negative": obv_slope <= 0,
            "cmf_positive": cmf >= 0,
            "cmf_negative": cmf <= 0,
            "chaikin_positive": chaikin >= 0,
            "chaikin_negative": chaikin <= 0,
            "chaikin_cross_up": chaikin >= 0 and chaikin_prev <= 0,
            "chaikin_cross_down": chaikin <= 0 and chaikin_prev >= 0,
            "money_flow_improving": (cmf >= 0) or (chaikin >= 0) or bool_latest(frame, "MF_Cross_Bull"),
            "money_flow_weakening": (cmf <= 0) or (chaikin <= 0) or bool_latest(frame, "MF_Cross_Bear"),
        },
        "structure": {
            "breakout_level": breakout_level,
            "breakdown_level": breakdown_level,
            "swing_high_5": swing_high_5,
            "swing_low_5": swing_low_5,
            "swing_high_20": swing_high_20,
            "swing_low_20": swing_low_20,
            "pullback_near_ma20_long": near_zone(scalar(latest.get("Low"), close), ma20, atr, 0.6) and close >= ma20 * 0.99,
            "pullback_near_ma20_short": near_zone(scalar(latest.get("High"), close), ma20, atr, 0.6) and close <= ma20 * 1.01,
            "pullback_near_ema21_long": near_zone(scalar(latest.get("Low"), close), ema21, atr, 0.6) and close >= ema21 * 0.99,
            "pullback_near_ema21_short": near_zone(scalar(latest.get("High"), close), ema21, atr, 0.6) and close <= ema21 * 1.01,
            "pullback_near_kc_mid_long": near_zone(scalar(latest.get("Low"), close), kc_mid, atr, 0.6),
            "pullback_near_kc_mid_short": near_zone(scalar(latest.get("High"), close), kc_mid, atr, 0.6),
            "pullback_near_fixed_vwap_long": near_zone(scalar(latest.get("Low"), close), fixed_vwap, atr, 0.8),
            "pullback_near_fixed_vwap_short": near_zone(scalar(latest.get("High"), close), fixed_vwap, atr, 0.8),
            "near_breakout_long": near_zone(close, breakout_level, atr, 1.5) or near_zone(close, price_channel_up, atr, 1.5),
            "near_breakout_short": near_zone(close, breakdown_level, atr, 1.5) or near_zone(close, price_channel_low, atr, 1.5),
            "lower_zone": close <= min(bb_low, ma20, vwap) or near_zone(close, swing_low_20, atr, 1.0),
            "upper_zone": close >= max(bb_up, ma20, vwap) or near_zone(close, swing_high_20, atr, 1.0),
            "outside_keltner_lower": scalar(latest.get("Low"), close) <= kc_lower,
            "outside_keltner_upper": scalar(latest.get("High"), close) >= kc_upper,
            "inside_value_area": np.isfinite(vp_val) and np.isfinite(vp_vah) and vp_val <= close <= vp_vah,
            "near_vp_poc": near_zone(close, vp_poc, atr, 0.8),
            "near_vp_val": near_zone(close, vp_val, atr, 0.8),
            "near_vp_vah": near_zone(close, vp_vah, atr, 0.8),
            "recent_fractal_high": recent_fractal_high,
            "recent_fractal_low": recent_fractal_low,
            "fractal_breakout_long": close >= recent_fractal_high if np.isfinite(recent_fractal_high) else False,
            "fractal_breakout_short": close <= recent_fractal_low if np.isfinite(recent_fractal_low) else False,
            "price_change_5": price_change_5,
            "price_above_breakout": close >= breakout_level,
            "price_below_breakdown": close <= breakdown_level,
        },
        "levels": {
            "vwap": vwap,
            "fixed_vwap": fixed_vwap,
            "ema21": ema21,
            "ma50": ma50,
            "kc_upper": kc_upper,
            "kc_mid": kc_mid,
            "kc_lower": kc_lower,
            "vp_poc": vp_poc,
            "vp_vah": vp_vah,
            "vp_val": vp_val,
            "fib_382": fib_382,
            "fib_50": fib_50,
            "fib_618": fib_618,
            "fib_ext_up": fib_ext_up,
            "fib_ext_down": fib_ext_down,
            "tenkan": tenkan,
            "kijun": kijun,
            "cloud_top": cloud_top,
            "cloud_bottom": cloud_bottom,
            "nearest_resistance": nearest_resistance(close, [breakout_level, swing_high_20, bb_up, price_channel_up, vp_vah, fib_ext_up]),
            "nearest_support": nearest_support(close, [breakdown_level, swing_low_20, bb_low, price_channel_low, vp_val, vp_poc]),
        },
        "patterns": {
            "bullish_reversal_candle": bullish_reversal_candle,
            "bearish_reversal_candle": bearish_reversal_candle,
            "morning_star": bool_latest(frame, "Morning_Star"),
            "evening_star": bool_latest(frame, "Evening_Star"),
            "fractal_high": bool_latest(frame, "Fractal_High"),
            "fractal_low": bool_latest(frame, "Fractal_Low"),
            "pocket_pivot": bool_latest(frame, "Pocket_Pivot"),
            "bullish_divergence": any(
                bool_latest(frame, column)
                for column in ("Bull_Divergence", "RSI_Bull_Divergence", "MF_Bull_Div", "OBV_Div_Buy", "Smart_Money_Bullish_Div")
            ),
            "bearish_divergence": any(
                bool_latest(frame, column)
                for column in ("Bear_Divergence", "RSI_Bear_Divergence", "MF_Bear_Div", "OBV_Div_Sell", "Smart_Money_Bearish_Div")
            ),
            "volume_climax_buy": bool_latest(frame, "Volume_Climax_Buy"),
            "volume_climax_sell": bool_latest(frame, "Volume_Climax_Sell"),
            "parabolic_bottom": bool_latest(frame, "Parabolic_Bottom_Buy"),
            "parabolic_top": bool_latest(frame, "Parabolic_Top_Sell"),
            "obv_div_buy": bool_latest(frame, "OBV_Div_Buy") or bool_latest(frame, "Smart_Money_Bullish_Div"),
            "obv_div_sell": bool_latest(frame, "OBV_Div_Sell") or bool_latest(frame, "Smart_Money_Bearish_Div"),
        },
        "signals": {
            key: bool_latest(frame, key)
            for key in (
                "EMA_Pullback_Buy", "EMA_Pullback_Sell", "VWAP_Bounce_Buy", "VWAP_Reject_Sell",
                "SuperTrend_Buy", "SuperTrend_Sell", "UTBot_Buy", "UTBot_Sell",
                "Hull_Turn_Bull", "Hull_Turn_Bear", "Squeeze_Fire_Buy", "Squeeze_Fire_Sell",
                "Squeeze_Mom_Cross_Up", "Squeeze_Mom_Cross_Down", "BB_Squeeze_End_Bull", "BB_Squeeze_End_Bear",
                "Expansion_BO", "Expansion_BD", "Kumo_Breakout_Bull", "Kumo_Breakout_Bear",
                "TK_Cross_Bull", "TK_Cross_Bear", "BB_Upper_Break", "BB_Lower_Break",
                "CMF_Bull", "CMF_Bear", "Pocket_Pivot", "Volume_POC_Breakout", "Volume_POC_Breakdown",
                "VP_VAH_Resistance", "VP_VAL_Support", "Fib_50_Support", "Fib_50_Resistance",
                "Fib_618_Support", "Fib_618_Resistance", "Fib_618_Reclaim", "Fib_618_Breakdown",
                "Fib_Confluence_Buy", "Fib_Confluence_Sell", "Box_Breakout_Bull", "Box_Breakdown_Bear",
                "Channel_Breakout_Bull", "Channel_Breakdown_Bear", "Triangle_Breakout_Bull", "Triangle_Breakdown_Bear",
                "CS_Trend_Continuation_Buy", "CS_Trend_Continuation_Sell", "CS_Breakout_Confirm_Buy", "CS_Breakout_Confirm_Sell",
                "CS_Squeeze_Breakout_Buy", "CS_Squeeze_Breakdown_Sell", "CS_Reversal_Cluster_Buy", "CS_Reversal_Cluster_Sell",
                "CS_Divergence_Confluence_Buy", "CS_Divergence_Confluence_Sell", "CS_Triple_Confirm_Buy", "CS_Triple_Confirm_Sell",
                "CS_Institutional_Accumulation", "CS_Ichimoku_Breakout_Buy", "CS_Ichimoku_Breakout_Sell", "CS_Conflict_Warning",
            )
        },
        "hma_ema": {
            "ema15": ema15,
            "ema25": ema25,
            "ema50": ema50,
            "ema200": ema200,
            "hma25": hma25,
            "ema15_slope_up": ema15_slope_up,
            "ema25_slope_up": ema25_slope_up,
            "ema50_slope_up": ema50_slope_up,
            "hma25_slope_up": hma25_slope_up,
            "ema15_slope_down": ema15_slope_down,
            "ema25_slope_down": ema25_slope_down,
            "ema50_slope_down": ema50_slope_down,
            "hma25_slope_down": hma25_slope_down,
            "hma25_ema25_cross_bull": hma25_ema25_cross_bull,
            "hma25_ema25_cross_bear": hma25_ema25_cross_bear,
            "hma25_ema15_cross_bear": hma25_ema15_cross_bear,
            "hma25_ema15_cross_bull": hma25_ema15_cross_bull,
            "long_aligned": hma_ema_long_aligned,
            "short_aligned": hma_ema_short_aligned,
            "long_entry": hma_ema_long_entry,
            "short_entry": hma_ema_short_entry,
            "signal_state": hma_ema_signal_state,
            "risk_to_ema50_pct": hma_ema_risk_to_ema50_pct,
            "ema50_ema200_gap_pct": hma_ema_ema50_ema200_gap_pct,
            "long_rr_valid": hma_ema_long_rr_valid,
            "short_rr_valid": hma_ema_short_rr_valid,
            "long_virtual_stop": hma_ema_long_virtual_stop,
            "short_virtual_stop": hma_ema_short_virtual_stop,
            "long_target_2r": hma_ema_long_target_2r,
            "short_target_2r": hma_ema_short_target_2r,
            "long_target_3r": hma_ema_long_target_3r,
            "short_target_3r": hma_ema_short_target_3r,
        },
    }


def nearest_resistance(close: float, levels: Iterable[float]) -> float:
    candidates = [float(level) for level in levels if np.isfinite(level) and level >= close]
    return min(candidates) if candidates else float("inf")


def nearest_support(close: float, levels: Iterable[float]) -> float:
    candidates = [float(level) for level in levels if np.isfinite(level) and level <= close]
    return max(candidates) if candidates else float("-inf")


def near_zone(price: float, level: float, atr: float, atr_multiple: float) -> bool:
    if not np.isfinite(level):
        return False
    return abs(price - level) <= (atr * atr_multiple)


def bool_latest(df: pd.DataFrame, column: str) -> bool:
    if column not in df.columns or df.empty:
        return False
    value = df[column].iloc[-1]
    if pd.isna(value):
        return False
    return bool(value)


def bool_recent(df: pd.DataFrame, column: str, bars: int) -> bool:
    if column not in df.columns or df.empty:
        return False
    for value in df[column].tail(max(bars, 1)):
        if pd.isna(value):
            continue
        if bool(value):
            return True
    return False


def series_max(df: pd.DataFrame, column: str, default: float) -> float:
    if column not in df.columns or df.empty:
        return default
    return scalar(df[column].max(), default)


def series_min(df: pd.DataFrame, column: str, default: float) -> float:
    if column not in df.columns or df.empty:
        return default
    return scalar(df[column].min(), default)


def series_mean(df: pd.DataFrame, column: str, default: float) -> float:
    if column not in df.columns or df.empty:
        return default
    return scalar(df[column].mean(), default)


def scalar(value, default: float = 0.0) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return default
    if np.isnan(numeric):
        return default
    return numeric


def pct_change(current: float, previous: float) -> float:
    if abs(previous) <= 1e-9:
        return 0.0
    return ((current - previous) / previous) * 100.0


def pct_of(value: float, base: float) -> float:
    if abs(base) <= 1e-9:
        return 0.0
    return (value / base) * 100.0


def ordered_unique(items: Iterable[str]) -> list[str]:
    seen = set()
    ordered: list[str] = []
    for item in items:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        ordered.append(text)
    return ordered


def finite_max(values: Iterable[float], default: float) -> float:
    candidates = [float(value) for value in values if np.isfinite(value)]
    return max(candidates) if candidates else default


def finite_min(values: Iterable[float], default: float) -> float:
    candidates = [float(value) for value in values if np.isfinite(value)]
    return min(candidates) if candidates else default


def recent_flagged_level(df: pd.DataFrame, flag_column: str, price_column: str, default: float) -> float:
    if flag_column not in df.columns or price_column not in df.columns or df.empty:
        return default
    flagged = df[df[flag_column].fillna(False)]
    if flagged.empty:
        return default
    return scalar(flagged[price_column].iloc[-1], default)
