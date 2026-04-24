import unittest

import numpy as np
import pandas as pd

from strategy import build_strategy_payload


def _hma_base_frame(rows: int = 40) -> pd.DataFrame:
    idx = pd.date_range("2026-01-01", periods=rows, freq="D")
    close = pd.Series(np.linspace(100.0, 120.0, rows), index=idx)
    frame = pd.DataFrame(index=idx)
    frame["Open"] = close - 0.2
    frame["High"] = close + 0.4
    frame["Low"] = close - 0.4
    frame["Close"] = close
    frame["Volume"] = 1_000_000.0
    frame["ATR"] = 2.0
    frame["EMA8"] = close - 0.5
    frame["EMA15"] = close - 0.6
    frame["EMA21"] = close - 0.7
    frame["EMA25"] = close - 0.8
    frame["EMA50"] = close - 1.4
    frame["EMA200"] = close - 4.0
    frame["MA20"] = close - 0.9
    frame["MA50"] = close - 1.5
    frame["MA200"] = close - 4.2
    frame["VWAP"] = close - 0.4
    frame["Fixed_VWAP"] = close - 0.4
    frame["SuperTrend"] = close - 0.9
    frame["Parabolic_SAR"] = close - 0.8
    frame["Price_Channel_Up"] = close + 3.5
    frame["Price_Channel_Low"] = close - 3.5
    frame["Price_Channel_Mid"] = close
    frame["BB_Up"] = close + 2.5
    frame["BB_Low"] = close - 2.5
    frame["KC_Upper"] = close + 2.0
    frame["KC_Mid"] = close - 0.8
    frame["KC_Lower"] = close - 2.0
    frame["Volume_Ratio_20"] = 1.3
    frame["Volume_Ratio_50"] = 1.2
    frame["MACD_Hist"] = np.linspace(0.1, 0.7, rows)
    frame["WT1"] = np.linspace(10.0, 25.0, rows)
    frame["OBV"] = np.linspace(1000.0, 1500.0, rows)
    frame["OBV_Slope"] = 0.9
    frame["Chaikin_Oscillator"] = np.linspace(0.1, 0.4, rows)
    frame["CMF"] = 0.15
    frame["Composite_Accel"] = 0.5
    frame["RSI"] = 58.0
    frame["StochK"] = 62.0
    frame["MFI"] = 57.0
    frame["BB_Width"] = 4.0
    frame["ST_Direction"] = 1.0
    frame["PSAR_Direction"] = 1.0
    frame["ADX"] = 24.0
    frame["Plus_DI"] = 27.0
    frame["Minus_DI"] = 12.0
    frame["HMA25"] = close - 0.3
    frame["HMA"] = close - 0.3
    frame["HMA60"] = close - 0.6
    frame["HMA200"] = close - 1.2
    frame["HMA_EMA_Long_Aligned"] = True
    frame["HMA_EMA_Short_Aligned"] = False
    frame["HMA_EMA_Long_Entry"] = False
    frame["HMA_EMA_Short_Entry"] = False
    frame["HMA25_EMA25_Cross_Bull"] = False
    frame["HMA25_EMA25_Cross_Bear"] = False
    frame["HMA25_EMA15_Cross_Bear"] = False
    frame["HMA25_EMA15_Cross_Bull"] = False
    frame["HMA_EMA_Risk_To_EMA50_Pct"] = 2.5
    frame["HMA_EMA_EMA50_EMA200_Gap_Pct"] = 4.5

    bool_cols = [
        "Hammer",
        "Bullish_Engulfing",
        "Morning_Star",
        "Outside_Bullish",
        "Doji_Bullish",
        "Three_Bar_Reversal_Buy",
        "Shooting_Star",
        "Bearish_Engulfing",
        "Evening_Star",
        "Outside_Bearish",
        "Doji_Bearish",
        "Three_Bar_Reversal_Sell",
        "New_52W_High",
        "New_52W_Low",
        "Squeeze_On",
        "BB_Squeeze",
        "Squeeze_Fire_Buy",
        "Squeeze_Fire_Sell",
        "MF_Cross_Bull",
        "MF_Cross_Bear",
        "Volume_Dry_Up",
        "Bull_Divergence",
        "RSI_Bull_Divergence",
        "MF_Bull_Div",
        "OBV_Div_Buy",
        "Smart_Money_Bullish_Div",
        "Bear_Divergence",
        "RSI_Bear_Divergence",
        "MF_Bear_Div",
        "OBV_Div_Sell",
        "Smart_Money_Bearish_Div",
        "Volume_Climax_Buy",
        "Volume_Climax_Sell",
        "Parabolic_Bottom_Buy",
        "Parabolic_Top_Sell",
        "EMA_Pullback_Buy",
        "EMA_Pullback_Sell",
        "VWAP_Bounce_Buy",
        "VWAP_Reject_Sell",
        "SuperTrend_Buy",
        "SuperTrend_Sell",
        "UTBot_Buy",
        "UTBot_Sell",
        "Hull_Turn_Bull",
        "Hull_Turn_Bear",
        "Squeeze_Mom_Cross_Up",
        "Squeeze_Mom_Cross_Down",
        "BB_Squeeze_End_Bull",
        "BB_Squeeze_End_Bear",
        "Expansion_BO",
        "Expansion_BD",
        "Kumo_Breakout_Bull",
        "Kumo_Breakout_Bear",
        "TK_Cross_Bull",
        "TK_Cross_Bear",
        "BB_Upper_Break",
        "BB_Lower_Break",
        "CMF_Bull",
        "CMF_Bear",
        "Pocket_Pivot",
        "Volume_POC_Breakout",
        "Volume_POC_Breakdown",
        "VP_VAH_Resistance",
        "VP_VAL_Support",
        "Fib_50_Support",
        "Fib_50_Resistance",
        "Fib_618_Support",
        "Fib_618_Resistance",
        "Fib_618_Reclaim",
        "Fib_618_Breakdown",
        "Fib_Confluence_Buy",
        "Fib_Confluence_Sell",
        "Box_Breakout_Bull",
        "Box_Breakdown_Bear",
        "Channel_Breakout_Bull",
        "Channel_Breakdown_Bear",
        "Triangle_Breakout_Bull",
        "Triangle_Breakdown_Bear",
        "CS_Trend_Continuation_Buy",
        "CS_Trend_Continuation_Sell",
        "CS_Breakout_Confirm_Buy",
        "CS_Breakout_Confirm_Sell",
        "CS_Squeeze_Breakout_Buy",
        "CS_Squeeze_Breakdown_Sell",
        "CS_Reversal_Cluster_Buy",
        "CS_Reversal_Cluster_Sell",
        "CS_Divergence_Confluence_Buy",
        "CS_Divergence_Confluence_Sell",
        "CS_Triple_Confirm_Buy",
        "CS_Triple_Confirm_Sell",
        "CS_Institutional_Accumulation",
        "CS_Ichimoku_Breakout_Buy",
        "CS_Ichimoku_Breakout_Sell",
        "CS_Conflict_Warning",
        "Fractal_High",
        "Fractal_Low",
    ]
    for col in bool_cols:
        frame[col] = False

    return frame


def _result_by_id(payload: dict, strategy_id: str) -> dict:
    for item in payload["results"]:
        if item["id"] == strategy_id:
            return item
    raise KeyError(strategy_id)


class StrategyHmaEmaTests(unittest.TestCase):
    def test_hma_ema_long_entry_strategy(self):
        frame = _hma_base_frame()
        frame.loc[frame.index[-1], "HMA_EMA_Long_Entry"] = True
        frame.loc[frame.index[-1], "HMA25_EMA25_Cross_Bull"] = True
        payload = build_strategy_payload(frame)
        result = _result_by_id(payload, "hma_ema_trend_long")
        self.assertEqual(result["status"], "LONG_ENTRY")
        self.assertEqual(result["phase"], "LONG_ENTRY")
        self.assertTrue(result["stop_loss"] is not None)
        self.assertTrue(result["target_1"] is not None)
        self.assertTrue(result["target_2"] is not None)

    def test_hma_ema_short_entry_strategy(self):
        frame = _hma_base_frame()
        frame["Close"] = np.linspace(120.0, 100.0, len(frame))
        frame["EMA50"] = frame["Close"] + 1.0
        frame["EMA200"] = frame["Close"] + 3.0
        frame["HMA25"] = frame["Close"] + 0.2
        frame["HMA"] = frame["Close"] + 0.2
        frame["HMA_EMA_Long_Aligned"] = False
        frame["HMA_EMA_Short_Aligned"] = True
        frame["HMA_EMA_Long_Entry"] = False
        frame["HMA_EMA_Short_Entry"] = True
        frame["HMA25_EMA25_Cross_Bull"] = False
        frame["HMA25_EMA25_Cross_Bear"] = True
        frame["ST_Direction"] = -1.0
        frame["PSAR_Direction"] = -1.0
        payload = build_strategy_payload(frame)
        result = _result_by_id(payload, "hma_ema_trend_short")
        self.assertEqual(result["status"], "SHORT_ENTRY")
        self.assertEqual(result["phase"], "SHORT_ENTRY")
        self.assertTrue(result["stop_loss"] is not None)
        self.assertTrue(result["target_1"] is not None)
        self.assertTrue(result["target_2"] is not None)

    def test_hma_ema_exit_warning_state(self):
        frame = _hma_base_frame()
        frame.loc[frame.index[-1], "HMA_EMA_Long_Aligned"] = True
        frame.loc[frame.index[-1], "HMA_EMA_Long_Entry"] = False
        frame.loc[frame.index[-1], "HMA25_EMA15_Cross_Bear"] = True
        payload = build_strategy_payload(frame)
        result = _result_by_id(payload, "hma_ema_trend_long")
        self.assertEqual(result["status"], "EXIT_WARNING")
        self.assertIn("EMA50", result["invalidation_text"])

    def test_hma_ema_rr_invalid_when_close_not_above_ema50_for_long(self):
        frame = _hma_base_frame()
        frame.loc[frame.index[-1], "Close"] = 100.0
        frame.loc[frame.index[-1], "EMA50"] = 101.0
        frame.loc[frame.index[-1], "HMA_EMA_Long_Aligned"] = True
        payload = build_strategy_payload(frame)
        result = _result_by_id(payload, "hma_ema_trend_long")
        self.assertIsNone(result["stop_loss"])
        self.assertIsNone(result["target_1"])
        self.assertIsNone(result["target_2"])


if __name__ == "__main__":
    unittest.main()

