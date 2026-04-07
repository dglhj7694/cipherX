import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import COMBINED_SCAN_REGISTRY
from domain import AnalysisRequest, AnalysisViewModel, ScannerRequest, ScannerResultRow
import engine as root_engine
from engine_combo_registry import ensure_runtime_combo_registry
from engine_combo_scans import detect_combined_scans as detect_combined_scans_impl
from engine_objective import OBJECTIVE_COMBO_BASE
from engine_runtime.final_decision import compute_final_decision
from engine_runtime.pipeline import build_engine_result
from infrastructure.etf import FunctionHoldingsProvider, HoldingsProviderRegistry
from services.analysis_service import AnalysisArtifacts
from strategy import build_strategy_payload
from ui_localized import build_strategy_tab_view_model
from workflows import AnalysisWorkflow, ScannerWorkflow


BOOLEAN_COLUMNS = [
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
    "BB_Upper_Break",
    "BB_Lower_Break",
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
    "CS_Ichimoku_Breakout_Buy",
    "CS_Ichimoku_Breakout_Sell",
    "CS_Conflict_Warning",
]


NUMERIC_COLUMNS = {
    "Open": 100.0,
    "High": 100.3,
    "Low": 99.7,
    "Close": 100.0,
    "Volume": 1_000_000.0,
    "ATR": 1.0,
    "EMA8": 99.5,
    "EMA21": 99.0,
    "MA20": 99.0,
    "MA50": 97.0,
    "MA200": 94.0,
    "VWAP": 99.2,
    "SuperTrend": 98.8,
    "Parabolic_SAR": 98.9,
    "Price_Channel_Up": 106.0,
    "Price_Channel_Low": 94.0,
    "Price_Channel_Mid": 100.0,
    "BB_Up": 106.0,
    "BB_Low": 94.0,
    "KC_Mid": 99.0,
    "VP_VAH": np.nan,
    "VP_VAL": np.nan,
    "VP_POC": np.nan,
    "Fib_Ext_1618_Up": np.nan,
    "Fib_Ext_1618_Down": np.nan,
    "Volume_Ratio_20": 1.1,
    "Volume_Ratio_50": 1.1,
    "MACD_Hist": 0.2,
    "WT1": 20.0,
    "OBV": 1000.0,
    "OBV_Slope": 1.0,
    "Chaikin_Oscillator": 0.2,
    "CMF": 0.2,
    "Composite_Accel": 0.4,
    "RSI": 60.0,
    "StochK": 60.0,
    "MFI": 60.0,
    "BB_Width": 4.0,
    "ST_Direction": 1.0,
    "PSAR_Direction": 1.0,
    "ADX": 24.0,
    "Plus_DI": 28.0,
    "Minus_DI": 12.0,
}


def make_blank_frame(rows=30):
    index = pd.date_range("2025-01-01", periods=rows, freq="D")
    data = {column: [value] * rows for column, value in NUMERIC_COLUMNS.items()}
    frame = pd.DataFrame(data, index=index)
    for column in BOOLEAN_COLUMNS:
        frame[column] = False
    return frame


def apply_close_series(frame, closes):
    frame["Close"] = closes
    previous = closes[0]
    opens = []
    highs = []
    lows = []
    for close in closes:
        delta = close - previous
        open_price = close - 0.15 if delta >= 0 else close + 0.15
        high_price = max(open_price, close) + 0.25
        low_price = min(open_price, close) - 0.25
        opens.append(open_price)
        highs.append(high_price)
        lows.append(low_price)
        previous = close
    frame["Open"] = opens
    frame["High"] = highs
    frame["Low"] = lows
    frame["Price_Channel_Mid"] = (frame["Price_Channel_Up"] + frame["Price_Channel_Low"]) / 2.0
    return frame


def result_by_id(payload, strategy_id):
    for item in payload["results"]:
        if item["id"] == strategy_id:
            return item
    raise KeyError(strategy_id)


def make_trend_pullback_long_df():
    frame = make_blank_frame()
    closes = [100.0 + (0.35 * i) for i in range(len(frame))]
    apply_close_series(frame, closes)
    frame["ATR"] = 1.0
    frame["EMA8"] = frame["Close"] - 0.4
    frame["EMA21"] = frame["Close"] - 0.8
    frame["MA20"] = frame["Close"] - 0.9
    frame["MA50"] = frame["Close"] - 3.0
    frame["MA200"] = frame["Close"] - 6.0
    frame["VWAP"] = frame["Close"] - 0.7
    frame["SuperTrend"] = frame["Close"] - 1.1
    frame["Parabolic_SAR"] = frame["Close"] - 1.0
    frame["Price_Channel_Up"] = frame["Close"] + 5.0
    frame["Price_Channel_Low"] = frame["Close"] - 5.0
    frame["BB_Up"] = frame["Close"] + 4.5
    frame["BB_Low"] = frame["Close"] - 4.5
    frame["KC_Mid"] = frame["EMA21"]
    frame["Volume_Ratio_20"] = 1.5
    frame["Volume_Ratio_50"] = 1.4
    frame["MACD_Hist"] = np.linspace(0.05, 0.8, len(frame))
    frame["WT1"] = np.linspace(10.0, 45.0, len(frame))
    frame["OBV"] = np.linspace(1000.0, 1600.0, len(frame))
    frame["OBV_Slope"] = 1.0
    frame["Composite_Accel"] = 0.8
    frame["ST_Direction"] = 1.0
    frame["PSAR_Direction"] = 1.0
    frame["ADX"] = 26.0
    frame["Plus_DI"] = 30.0
    frame["Minus_DI"] = 11.0
    frame.loc[frame.index[:-1], "High"] = frame.loc[frame.index[:-1], "Close"] + 6.0
    frame.loc[frame.index[-1], "High"] = frame["Close"].iloc[-1] + 0.3
    frame.loc[frame.index[-1], "Low"] = frame["EMA21"].iloc[-1] - 0.1
    frame.loc[frame.index[-1], ["EMA_Pullback_Buy", "UTBot_Buy", "CS_Trend_Continuation_Buy", "New_52W_High"]] = True
    return frame


def make_trend_pullback_short_df():
    frame = make_blank_frame()
    closes = [130.0 - (0.45 * i) for i in range(len(frame))]
    apply_close_series(frame, closes)
    frame["ATR"] = 1.0
    frame["EMA8"] = frame["Close"] + 0.4
    frame["EMA21"] = frame["Close"] + 0.8
    frame["MA20"] = frame["Close"] + 0.9
    frame["MA50"] = frame["Close"] + 3.0
    frame["MA200"] = frame["Close"] + 6.0
    frame["VWAP"] = frame["Close"] + 0.7
    frame["SuperTrend"] = frame["Close"] + 1.1
    frame["Parabolic_SAR"] = frame["Close"] + 1.0
    frame["Price_Channel_Up"] = frame["Close"] + 5.0
    frame["Price_Channel_Low"] = frame["Close"] - 5.0
    frame["BB_Up"] = frame["Close"] + 4.5
    frame["BB_Low"] = frame["Close"] - 4.5
    frame["KC_Mid"] = frame["EMA21"]
    frame["Volume_Ratio_20"] = 1.5
    frame["Volume_Ratio_50"] = 1.4
    frame["MACD_Hist"] = np.linspace(0.3, -0.8, len(frame))
    frame["WT1"] = np.linspace(25.0, -45.0, len(frame))
    frame["OBV"] = np.linspace(1400.0, 900.0, len(frame))
    frame["OBV_Slope"] = -1.0
    frame["Composite_Accel"] = -0.8
    frame["ST_Direction"] = -1.0
    frame["PSAR_Direction"] = -1.0
    frame["ADX"] = 27.0
    frame["Plus_DI"] = 11.0
    frame["Minus_DI"] = 30.0
    frame.loc[frame.index[:-1], "Low"] = frame.loc[frame.index[:-1], "Close"] - 6.0
    frame.loc[frame.index[-1], "Low"] = frame["Close"].iloc[-1] - 0.3
    frame.loc[frame.index[-1], "High"] = frame["EMA21"].iloc[-1] + 0.1
    frame.loc[frame.index[-1], ["EMA_Pullback_Sell", "UTBot_Sell", "CS_Trend_Continuation_Sell", "New_52W_Low"]] = True
    return frame


def make_breakout_long_df():
    frame = make_trend_pullback_long_df()
    frame["Volume_Ratio_20"] = 1.8
    frame["Volume_Ratio_50"] = 1.6
    frame["ADX"] = 28.0
    frame["MACD_Hist"] = np.linspace(0.1, 1.0, len(frame))
    frame.loc[frame.index[-1], ["Expansion_BO", "Channel_Breakout_Bull", "CS_Breakout_Confirm_Buy"]] = True
    frame.loc[frame.index[-1], "Close"] = frame["High"].iloc[-2] + 0.5
    frame.loc[frame.index[-1], "Open"] = frame["Close"].iloc[-1] - 0.2
    frame.loc[frame.index[-1], "High"] = frame["Close"].iloc[-1] + 0.3
    frame.loc[frame.index[-1], "Low"] = frame["Close"].iloc[-1] - 0.4
    frame.loc[frame.index[-1], "Price_Channel_Up"] = frame["Close"].iloc[-1] + 5.0
    frame.loc[frame.index[-1], "BB_Up"] = frame["Close"].iloc[-1] + 4.0
    return frame


def make_squeeze_long_df():
    frame = make_blank_frame()
    closes = [100.0 + (0.03 * i) for i in range(len(frame) - 3)] + [102.0, 102.7, 103.0]
    apply_close_series(frame, closes)
    frame["ATR"] = 1.0
    frame["EMA8"] = frame["Close"] - 0.2
    frame["EMA21"] = frame["Close"] - 0.5
    frame["MA20"] = frame["Close"] - 0.6
    frame["MA50"] = frame["Close"] - 1.5
    frame["MA200"] = frame["Close"] - 3.0
    frame["VWAP"] = frame["Close"] - 0.3
    frame["Price_Channel_Up"] = frame["Close"] + 5.0
    frame["Price_Channel_Low"] = frame["Close"] - 5.0
    frame["BB_Up"] = frame["Close"] + 4.5
    frame["BB_Low"] = frame["Close"] - 4.5
    frame["BB_Width"] = np.linspace(6.0, 3.0, len(frame))
    frame["MACD_Hist"] = np.linspace(0.05, 0.8, len(frame))
    frame["WT1"] = np.linspace(5.0, 35.0, len(frame))
    frame["Volume_Ratio_20"] = 0.8
    frame["Volume_Ratio_50"] = 0.9
    frame["ST_Direction"] = 1.0
    frame["PSAR_Direction"] = 1.0
    frame.loc[frame.index[-3:], "Squeeze_On"] = True
    frame.loc[frame.index[-1], ["Squeeze_Fire_Buy", "Squeeze_Mom_Cross_Up", "CS_Squeeze_Breakout_Buy", "Volume_Dry_Up"]] = True
    frame.loc[frame.index[-1], "Volume_Ratio_20"] = 1.7
    frame.loc[frame.index[-1], "Volume_Ratio_50"] = 1.4
    frame.loc[frame.index[-1], "Low"] = 102.7
    return frame


def make_reversal_long_df():
    frame = make_blank_frame()
    closes = [110.0, 109.2, 108.4, 107.6, 106.8, 106.0, 105.2, 104.4, 103.6, 102.8, 102.0, 101.2, 100.8, 100.6, 100.4, 100.2, 100.0, 99.9, 99.8, 99.7, 99.6, 99.5, 99.4, 99.3, 108.0, 106.0, 104.0, 102.0, 100.8, 100.5]
    apply_close_series(frame, closes)
    frame["ATR"] = 1.0
    frame["EMA8"] = frame["Close"] - 0.2
    frame["EMA21"] = frame["Close"] + 2.2
    frame["MA20"] = frame["Close"] + 2.5
    frame["MA50"] = frame["Close"] + 0.6
    frame["MA200"] = frame["Close"] + 4.5
    frame["VWAP"] = frame["Close"] - 1.5
    frame["Price_Channel_Up"] = frame["Close"] + 6.0
    frame["Price_Channel_Low"] = frame["Close"] - 3.0
    frame["BB_Up"] = frame["Close"] + 5.5
    frame["BB_Low"] = frame["Close"] + 0.8
    frame["MACD_Hist"] = np.linspace(-1.2, 0.1, len(frame))
    frame["WT1"] = np.linspace(-80.0, -10.0, len(frame))
    frame["RSI"] = 28.0
    frame["StochK"] = 14.0
    frame["MFI"] = 25.0
    frame["CMF"] = 0.25
    frame["Chaikin_Oscillator"] = 0.3
    frame["Composite_Accel"] = 0.6
    frame["ST_Direction"] = -1.0
    frame["PSAR_Direction"] = -1.0
    frame.loc[frame.index[-1], ["Bull_Divergence", "Hammer", "VWAP_Bounce_Buy", "UTBot_Buy"]] = True
    return frame


def make_supertrend_psar_long_df():
    frame = make_trend_pullback_long_df()
    frame["SuperTrend"] = frame["Close"] - 1.3
    frame["ST_Direction"] = 1.0
    frame["PSAR_Direction"] = 1.0
    frame["ADX"] = 30.0
    frame["Plus_DI"] = 34.0
    frame["Minus_DI"] = 10.0
    frame["MACD_Hist"] = np.linspace(0.1, 0.9, len(frame))
    frame["WT1"] = np.linspace(8.0, 38.0, len(frame))
    frame.loc[frame.index[-1], ["SuperTrend_Buy", "UTBot_Buy", "CS_Triple_Confirm_Buy"]] = True
    return frame


def make_obv_divergence_long_df():
    frame = make_blank_frame()
    closes = [112.0, 111.0, 110.0, 109.0, 108.0, 107.0, 106.0, 105.0, 104.0, 103.0, 102.0, 101.0, 100.5, 100.2, 100.0, 99.8, 99.6, 99.4, 99.2, 99.0, 98.8, 98.6, 98.4, 98.2, 110.0, 108.0, 105.0, 102.0, 100.5, 100.0]
    apply_close_series(frame, closes)
    frame["ATR"] = 1.0
    frame["EMA8"] = frame["Close"] - 0.2
    frame["EMA21"] = frame["Close"] + 2.4
    frame["MA20"] = frame["Close"] + 2.6
    frame["MA50"] = frame["Close"] + 1.0
    frame["MA200"] = frame["Close"] + 4.0
    frame["VWAP"] = frame["Close"] - 1.0
    frame["Price_Channel_Up"] = frame["Close"] + 6.0
    frame["Price_Channel_Low"] = frame["Close"] - 3.0
    frame["BB_Up"] = frame["Close"] + 5.0
    frame["BB_Low"] = frame["Close"] + 0.5
    frame["MACD_Hist"] = np.linspace(-1.0, 0.2, len(frame))
    frame["WT1"] = np.linspace(-70.0, -5.0, len(frame))
    frame["RSI"] = 29.0
    frame["StochK"] = 18.0
    frame["MFI"] = 30.0
    frame["CMF"] = 0.2
    frame["Chaikin_Oscillator"] = 0.25
    frame["Composite_Accel"] = 0.4
    frame["OBV"] = np.linspace(900.0, 1300.0, len(frame))
    frame["OBV_Slope"] = 1.0
    frame.loc[frame.index[-1], ["OBV_Div_Buy", "Hammer", "VWAP_Bounce_Buy", "UTBot_Buy"]] = True
    return frame


def make_vwap_reclaim_long_df():
    frame = make_trend_pullback_long_df()
    frame = frame.copy()
    frame["Fixed_VWAP"] = frame["Close"] - 0.5
    frame["VWAP"] = frame["Close"] - 0.8
    frame.loc[frame.index[-2], "Close"] = frame["VWAP"].iloc[-2] - 0.4
    frame.loc[frame.index[-1], "Close"] = frame["VWAP"].iloc[-1] + 0.9
    frame.loc[frame.index[-1], "Open"] = frame["VWAP"].iloc[-1] + 0.2
    frame.loc[frame.index[-1], "Low"] = frame["Fixed_VWAP"].iloc[-1] - 0.1
    frame.loc[frame.index[-1], "High"] = frame["Close"].iloc[-1] + 0.4
    frame.loc[frame.index[-1], ["VWAP_Bounce_Buy", "UTBot_Buy"]] = True
    frame.loc[frame.index[-1], "Volume_Ratio_20"] = 1.8
    frame.loc[frame.index[-1], "Volume_Ratio_50"] = 1.5
    return frame


def make_morning_star_fib_long_df():
    frame = make_reversal_long_df()
    frame = frame.copy()
    frame["Fixed_VWAP"] = frame["Close"] - 0.6
    frame.loc[frame.index[-1], ["Morning_Star", "Fib_50_Support", "Fib_618_Support", "Fib_618_Reclaim", "Fib_Confluence_Buy", "VWAP_Bounce_Buy", "UTBot_Buy"]] = True
    frame.loc[frame.index[-1], "Close"] = frame["Close"].iloc[-1] + 1.0
    frame.loc[frame.index[-1], "Open"] = frame["Close"].iloc[-1] - 0.5
    frame.loc[frame.index[-1], "High"] = frame["Close"].iloc[-1] + 0.4
    frame.loc[frame.index[-1], "Low"] = frame["Close"].iloc[-1] - 0.8
    frame["MACD_Hist"] = np.linspace(-1.1, 0.4, len(frame))
    return frame


def make_accumulation_long_df():
    frame = make_blank_frame()
    closes = [100.0, 100.2, 100.1, 100.3, 100.2, 100.4, 100.3, 100.5, 100.4, 100.6, 100.5, 100.7, 100.6, 100.8, 100.7, 100.9, 100.8, 101.0, 100.9, 101.1, 101.0, 101.2, 101.1, 101.3, 101.2, 101.5, 101.4, 101.7, 101.6, 102.0]
    apply_close_series(frame, closes)
    frame["MA50"] = frame["Close"] - 1.5
    frame["MA200"] = frame["Close"] - 4.0
    frame["EMA21"] = frame["Close"] - 0.4
    frame["MA20"] = frame["Close"] - 0.5
    frame["EMA8"] = frame["Close"] - 0.2
    frame["VWAP"] = frame["Close"] - 0.3
    frame["Fixed_VWAP"] = frame["Close"] - 0.5
    frame["VP_POC"] = frame["Close"] - 0.4
    frame["VP_VAL"] = frame["Close"] - 1.0
    frame["VP_VAH"] = frame["Close"] + 1.2
    frame["CMF"] = 0.25
    frame["Chaikin_Oscillator"] = np.linspace(-0.1, 0.5, len(frame))
    frame["OBV"] = np.linspace(900.0, 1800.0, len(frame))
    frame["OBV_Slope"] = 1.2
    frame["MACD_Hist"] = np.linspace(0.0, 0.7, len(frame))
    frame["Volume_Ratio_20"] = 1.4
    frame["Volume_Ratio_50"] = 1.3
    frame.loc[frame.index[-1], ["Pocket_Pivot", "Volume_POC_Breakout", "CS_Institutional_Accumulation"]] = True
    return frame


def make_poc_rotation_long_df():
    frame = make_blank_frame()
    closes = [100.0 + (0.12 * i) for i in range(len(frame))]
    apply_close_series(frame, closes)
    frame["EMA21"] = frame["Close"] - 0.3
    frame["MA20"] = frame["Close"] - 0.4
    frame["MA50"] = frame["Close"] - 1.2
    frame["MA200"] = frame["Close"] - 3.5
    frame["VWAP"] = frame["Close"] - 0.2
    frame["VP_POC"] = frame["Close"] - 0.15
    frame["VP_VAL"] = frame["Close"] - 0.8
    frame["VP_VAH"] = frame["Close"] + 0.9
    frame["MACD_Hist"] = np.linspace(0.05, 0.6, len(frame))
    frame["Volume_Ratio_20"] = 1.7
    frame["Volume_Ratio_50"] = 1.5
    frame["CMF"] = 0.2
    frame["Chaikin_Oscillator"] = 0.3
    frame.loc[frame.index[-1], ["VP_VAL_Support", "Volume_POC_Breakout"]] = True
    frame.loc[frame.index[-1], "Low"] = frame["VP_VAL"].iloc[-1] - 0.05
    return frame


def make_ichimoku_breakout_long_df():
    frame = make_breakout_long_df()
    frame = frame.copy()
    frame["Ichimoku_Tenkan"] = frame["Close"] - 0.2
    frame["Ichimoku_Kijun"] = frame["Close"] - 0.6
    frame["Ichimoku_SenkouA"] = frame["Close"] - 1.0
    frame["Ichimoku_SenkouB"] = frame["Close"] - 1.3
    frame["Volume_Ratio_20"] = 1.8
    frame["Volume_Ratio_50"] = 1.6
    frame["ADX"] = 28.0
    frame.loc[frame.index[-1], ["Kumo_Breakout_Bull", "TK_Cross_Bull", "CS_Ichimoku_Breakout_Buy"]] = True
    return frame


def make_ichimoku_breakout_short_df():
    frame = make_trend_pullback_short_df()
    frame = frame.copy()
    frame["Ichimoku_Tenkan"] = frame["Close"] + 0.2
    frame["Ichimoku_Kijun"] = frame["Close"] + 0.6
    frame["Ichimoku_SenkouA"] = frame["Close"] + 1.0
    frame["Ichimoku_SenkouB"] = frame["Close"] + 1.4
    frame["Volume_Ratio_20"] = 1.8
    frame["Volume_Ratio_50"] = 1.6
    frame["ADX"] = 28.0
    frame.loc[frame.index[-1], ["Kumo_Breakout_Bear", "TK_Cross_Bear", "CS_Ichimoku_Breakout_Sell"]] = True
    return frame


class EngineComboModuleTests(unittest.TestCase):
    def test_runtime_combo_registry_adds_ichimoku_sell_combo(self):
        registry = ensure_runtime_combo_registry({})
        self.assertIn("CS_Ichimoku_Breakout_Sell", registry)
        self.assertEqual(registry["CS_Ichimoku_Breakout_Sell"]["dir"], "sell")

    def test_detect_combined_scans_marks_ichimoku_sell_combo(self):
        frame = make_blank_frame()
        apply_close_series(frame, [110.0 - (0.3 * i) for i in range(len(frame))])
        frame["MA50"] = frame["Close"] + 1.0
        frame["MA200"] = frame["Close"] + 3.0
        frame["Plus_DI"] = 12.0
        frame["Minus_DI"] = 28.0
        frame["ADX"] = 26.0
        frame["Volume_Ratio_20"] = 1.3
        frame["Volume_Ratio_50"] = 1.2
        frame.loc[frame.index[-1], ["Kumo_Breakout_Bear", "TK_Cross_Bear"]] = True
        registry = ensure_runtime_combo_registry(dict(COMBINED_SCAN_REGISTRY))
        result = detect_combined_scans_impl(frame.copy(), frame["Volume_Ratio_20"], pd.Series(False, index=frame.index), registry=registry)
        self.assertTrue(bool(result["CS_Ichimoku_Breakout_Sell"].iloc[-1]))


class EngineCoreSplitSmokeTests(unittest.TestCase):
    def test_objective_combo_weights_are_confirmation_only(self):
        self.assertLess(OBJECTIVE_COMBO_BASE[1], 3.0)
        self.assertLess(OBJECTIVE_COMBO_BASE[2], 2.0)

    def test_root_engine_layers_committee_objective_pipeline_runs(self):
        frame = make_blank_frame()
        apply_close_series(frame, [100.0 + (0.1 * i) for i in range(len(frame))])
        hma_rising = pd.Series(False, index=frame.index)
        layered = root_engine.compute_10layer_scores(frame.copy(), frame["Volume_Ratio_20"], hma_rising)
        self.assertIn("Buy_Total", layered.columns)
        self.assertIn("Sell_Total", layered.columns)
        committee = root_engine.compute_committee_ensemble(layered.copy(), layered["Volume_Ratio_20"], hma_rising)
        self.assertIn("Ensemble_Score", committee.columns)
        self.assertIn("Committee_Judgment", committee.columns)
        self.assertNotIn("Trade_Judgment", committee.columns)
        objective = root_engine._compute_objective_judgment(committee.copy(), committee["Volume_Ratio_20"])
        self.assertIn("Objective_Buy_Score", objective.columns)
        self.assertIn("Objective_Judgment", objective.columns)
        self.assertNotIn("Trade_Judgment", objective.columns)


class FinalDecisionOwnershipTests(unittest.TestCase):
    def _build_objective_frame(self):
        frame = make_blank_frame()
        apply_close_series(frame, [100.0 + (0.1 * i) for i in range(len(frame))])
        hma_rising = pd.Series(False, index=frame.index)
        layered = root_engine.compute_10layer_scores(frame.copy(), frame["Volume_Ratio_20"], hma_rising)
        committee = root_engine.compute_committee_ensemble(layered.copy(), layered["Volume_Ratio_20"], hma_rising)
        return root_engine._compute_objective_judgment(committee.copy(), committee["Volume_Ratio_20"])

    def test_final_decision_module_owns_trade_judgment_columns(self):
        objective = self._build_objective_frame()
        self.assertNotIn("Trade_Judgment", objective.columns)
        self.assertNotIn("Action_Label", objective.columns)
        self.assertNotIn("Judgment_Confidence", objective.columns)

        finalised = compute_final_decision(objective.copy())
        self.assertIn("Trade_Judgment", finalised.columns)
        self.assertIn("Action_Label", finalised.columns)
        self.assertIn("Judgment_Confidence", finalised.columns)
        self.assertIn("Final_Decision_Score", finalised.columns)

    def test_build_engine_result_returns_typed_contract(self):
        objective = self._build_objective_frame()
        finalised = compute_final_decision(objective.copy())
        result = build_engine_result(finalised)
        self.assertEqual(result.decision.label, str(finalised["Trade_Judgment"].iloc[-1]))
        self.assertEqual(result.committee.label, str(finalised["Committee_Judgment"].iloc[-1]))
        self.assertEqual(result.objective.advisory_label, str(finalised["Objective_Judgment"].iloc[-1]))
        self.assertAlmostEqual(result.evidence.ensemble_score, float(finalised["Ensemble_Score"].iloc[-1]), places=6)


class WorkflowContractTests(unittest.TestCase):
    def test_analysis_workflow_returns_response_contract(self):
        class FakeAnalysisService:
            def analyze(self, request, prompt_builder):
                self.request = request
                self.prompt_builder = prompt_builder
                meta = AnalysisViewModel.from_payload(
                    {
                        "ticker": request.ticker,
                        "price": 101.25,
                        "price_change_pct": 1.5,
                        "judgment": "BUY",
                        "action_label": "매수 우세",
                        "confidence": 82,
                        "ensemble_score": 14.5,
                        "context_label": "추세",
                        "leading_verdict": "리드 양호",
                        "lagging_verdict": "후행 확인",
                        "combined_scans": [],
                        "top_strategy": {"label": "추세 지속 눌림목", "score": 81},
                        "strategy_summary": {"conflict_level": "LOW"},
                    }
                )
                return AnalysisArtifacts(
                    data_frame=None,
                    display_frame=None,
                    meta=meta,
                    prompt_text="PROMPT",
                    chart_json="{}",
                    audit={"ok": True},
                )

        workflow = AnalysisWorkflow(FakeAnalysisService())
        response = workflow.run(AnalysisRequest(ticker="AAPL", chart_days=126), prompt_builder=lambda *_: "PROMPT")
        self.assertEqual(response.chart_json, "{}")
        self.assertEqual(response.prompt_text, "PROMPT")
        self.assertEqual(response.meta.ticker, "AAPL")
        self.assertEqual(response.meta.top_strategy["label"], "추세 지속 눌림목")

    def test_scanner_workflow_uses_analysis_service_boundary(self):
        class FakeAnalysisService:
            def __init__(self):
                self.calls = []

            def analyze(self, request, prompt_builder):
                self.calls.append(request.ticker)
                meta = AnalysisViewModel.from_payload(
                    {
                        "ticker": request.ticker,
                        "price": 100.0,
                        "price_change_pct": 0.5,
                        "judgment": "WATCH_BUY",
                        "action_label": "관심",
                        "confidence": 61,
                        "ensemble_score": 6.5,
                        "context_label": "중립",
                        "leading_verdict": "관찰",
                        "lagging_verdict": "보류",
                        "combined_scans": [],
                        "top_strategy": {"label": "돌파 확인형", "score": 67, "direction": "LONG"},
                        "strategy_summary": {"conflict_level": "LOW"},
                    }
                )
                return AnalysisArtifacts(
                    data_frame=None,
                    display_frame=None,
                    meta=meta,
                    prompt_text="PROMPT",
                    chart_json=None,
                    audit=None,
                )

        workflow = ScannerWorkflow(FakeAnalysisService())
        request = ScannerRequest(tickers=["AAPL", "MSFT"], chart_days=126, max_workers=2)
        results = workflow.run(
            request,
            row_builder={
                "prompt_builder": lambda *_: "PROMPT",
                "build_row": lambda ticker, artifacts: ScannerResultRow(
                    ticker=ticker,
                    decision=artifacts.meta.decision_label,
                    confidence=artifacts.meta.confidence,
                    ensemble_score=artifacts.meta.ensemble_score,
                    scan_score=artifacts.meta.ensemble_score,
                    top_strategy=artifacts.meta.top_strategy,
                ),
            },
        )
        self.assertEqual(len(results), 2)
        self.assertEqual({row["ticker"] for row in results}, {"AAPL", "MSFT"})
        self.assertTrue(all("top_strategy" in row for row in results))


class EtfProviderContractTests(unittest.TestCase):
    def test_registry_uses_supported_provider_before_fallback(self):
        registry = HoldingsProviderRegistry(
            providers=[
                FunctionHoldingsProvider(
                    supported_symbols={"QQQ"},
                    fetcher=lambda symbol: {
                        "symbol": symbol,
                        "tickers": ["AAPL", "MSFT"],
                        "note": "primary",
                        "error": "",
                        "as_of": "2026-04-07",
                    },
                )
            ],
            fallback=FunctionHoldingsProvider(
                fetcher=lambda symbol: {
                    "symbol": symbol,
                    "tickers": ["SPY"],
                    "note": "fallback",
                    "error": "",
                    "as_of": "",
                }
            ),
        )
        payload = registry.fetch("QQQ")
        self.assertEqual(payload.symbol, "QQQ")
        self.assertEqual(payload.tickers, ["AAPL", "MSFT"])
        self.assertEqual(payload.note, "primary")

    def test_registry_returns_fallback_when_primary_is_empty(self):
        registry = HoldingsProviderRegistry(
            providers=[
                FunctionHoldingsProvider(
                    supported_symbols={"IGV"},
                    fetcher=lambda symbol: {
                        "symbol": symbol,
                        "tickers": [],
                        "note": "",
                        "error": "not found",
                        "as_of": "",
                    },
                )
            ],
            fallback=FunctionHoldingsProvider(
                fetcher=lambda symbol: {
                    "symbol": symbol,
                    "tickers": ["MSFT", "NOW"],
                    "note": "fallback",
                    "error": "",
                    "as_of": "",
                }
            ),
        )
        payload = registry.fetch("IGV")
        self.assertEqual(payload.tickers, ["MSFT", "NOW"])
        self.assertEqual(payload.note, "fallback")


class StrategyEngineMvpTests(unittest.TestCase):
    def test_empty_payload_is_safe(self):
        payload = build_strategy_payload(pd.DataFrame())
        self.assertEqual(payload["results"], [])
        self.assertEqual(payload["visible_results"], [])
        self.assertIsNone(payload["summary"]["top_strategy"])
        self.assertEqual(payload["summary"]["conflict_level"], "LOW")

    def test_trend_pullback_long_becomes_active(self):
        frame = make_trend_pullback_long_df()
        payload = build_strategy_payload(frame)
        result = result_by_id(payload, "trend_pullback_long")
        self.assertEqual(result["status"], "ACTIVE")
        self.assertEqual(result["phase"], "TRIGGERED")
        self.assertGreaterEqual(result["rr"], 1.3)
        self.assertAlmostEqual(result["entry_price"], float(frame["Close"].iloc[-1]), places=4)

    def test_breakout_confirmation_long_becomes_active(self):
        payload = build_strategy_payload(make_breakout_long_df())
        result = result_by_id(payload, "breakout_confirmation_long")
        self.assertEqual(result["status"], "ACTIVE")
        self.assertEqual(result["phase"], "BREAKOUT_CONFIRMED")
        self.assertTrue(result["entry_hint"])

    def test_squeeze_expansion_long_becomes_active(self):
        payload = build_strategy_payload(make_squeeze_long_df())
        result = result_by_id(payload, "squeeze_expansion_long")
        self.assertEqual(result["status"], "ACTIVE")
        self.assertEqual(result["phase"], "TRIGGERED")

    def test_reversal_cluster_long_becomes_active(self):
        payload = build_strategy_payload(make_reversal_long_df())
        result = result_by_id(payload, "reversal_cluster_long")
        self.assertEqual(result["status"], "ACTIVE")
        self.assertEqual(result["phase"], "TRIGGERED")
        self.assertGreaterEqual(result["setup_score"], 35)

    def test_supertrend_psar_long_becomes_active(self):
        payload = build_strategy_payload(make_supertrend_psar_long_df())
        result = result_by_id(payload, "supertrend_psar_long")
        self.assertEqual(result["status"], "ACTIVE")
        self.assertEqual(result["phase"], "DOUBLE_CONFIRMED")

    def test_obv_divergence_long_becomes_active(self):
        payload = build_strategy_payload(make_obv_divergence_long_df())
        result = result_by_id(payload, "obv_divergence_long")
        self.assertEqual(result["status"], "ACTIVE")
        self.assertEqual(result["phase"], "DIVERGENCE_CONFIRMED")

    def test_long_short_symmetry_prefers_matching_side(self):
        bullish_payload = build_strategy_payload(make_trend_pullback_long_df())
        bearish_payload = build_strategy_payload(make_trend_pullback_short_df())
        bullish_long = result_by_id(bullish_payload, "trend_pullback_long")
        bullish_short = result_by_id(bullish_payload, "trend_pullback_short")
        bearish_short = result_by_id(bearish_payload, "trend_pullback_short")
        bearish_long = result_by_id(bearish_payload, "trend_pullback_long")
        self.assertEqual(bullish_long["status"], "ACTIVE")
        self.assertEqual(bearish_short["status"], "ACTIVE")
        self.assertGreater(bullish_long["score"], bullish_short["score"])
        self.assertGreater(bearish_short["score"], bearish_long["score"])

    def test_conflict_summary_detects_mixed_regime(self):
        frame = make_blank_frame()
        apply_close_series(frame, [100.0] * len(frame))
        payload = build_strategy_payload(frame)
        self.assertGreaterEqual(payload["summary"]["bullish_count"], 1)
        self.assertGreaterEqual(payload["summary"]["bearish_count"], 1)
        self.assertIn(payload["summary"]["conflict_level"], {"MEDIUM", "HIGH"})

    def test_payload_summary_matches_visible_sort_order(self):
        payload = build_strategy_payload(make_breakout_long_df())
        visible = payload["visible_results"]
        self.assertGreater(len(visible), 0)
        scores = [item["score"] for item in visible]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertEqual(payload["summary"]["top_strategy"]["id"], visible[0]["id"])
        self.assertEqual(payload["summary"]["top_strategy"]["entry_price"], visible[0]["entry_price"])
        self.assertTrue(str(visible[0]["entry_reference_text"]).strip())

    def test_keltner_pullback_long_expands_strategy_set(self):
        payload = build_strategy_payload(make_trend_pullback_long_df())
        result = result_by_id(payload, "keltner_pullback_long")
        self.assertEqual(result["status"], "ACTIVE")
        self.assertEqual(result["phase"], "TRIGGERED")

    def test_keltner_breakout_long_expands_strategy_set(self):
        payload = build_strategy_payload(make_breakout_long_df())
        result = result_by_id(payload, "keltner_breakout_long")
        self.assertEqual(result["status"], "ACTIVE")
        self.assertEqual(result["phase"], "KELTNER_BREAKOUT_CONFIRMED")

    def test_keltner_mean_reversion_long_expands_strategy_set(self):
        payload = build_strategy_payload(make_reversal_long_df())
        result = result_by_id(payload, "keltner_mean_reversion_long")
        self.assertEqual(result["status"], "ACTIVE")
        self.assertEqual(result["phase"], "TRIGGERED")

    def test_vwap_reclaim_long_reaches_confirmed_phase(self):
        payload = build_strategy_payload(make_vwap_reclaim_long_df())
        result = result_by_id(payload, "vwap_reclaim_long")
        self.assertIn(result["status"], {"ACTIVE", "CONFIRMING", "TRIGGER_WAIT"})
        self.assertEqual(result["phase"], "VWAP_RECLAIM_CONFIRMED")

    def test_morning_star_fib_long_reaches_confirmed_phase(self):
        payload = build_strategy_payload(make_morning_star_fib_long_df())
        result = result_by_id(payload, "morning_star_fib_long")
        self.assertIn(result["status"], {"ACTIVE", "CONFIRMING", "TRIGGER_WAIT"})
        self.assertEqual(result["phase"], "FIB_CONFIRM")

    def test_fractal_breakout_long_is_visible(self):
        payload = build_strategy_payload(make_breakout_long_df())
        result = result_by_id(payload, "fractal_breakout_long")
        self.assertIn(result["status"], {"ACTIVE", "CONFIRMING", "TRIGGER_WAIT", "READY", "INTEREST"})
        self.assertIn(result["phase"], {"FRACTAL_BREAKOUT_CONFIRMED", "FRACTAL_BREAKOUT_PENDING"})

    def test_anchored_vwap_long_is_active(self):
        payload = build_strategy_payload(make_trend_pullback_long_df())
        result = result_by_id(payload, "anchored_vwap_long")
        self.assertEqual(result["status"], "ACTIVE")
        self.assertEqual(result["phase"], "AVWAP_CONFIRMED")
        self.assertEqual(result["label"], "Fixed VWAP 기반 롱 컨텍스트")
        self.assertEqual(result["canonical_label"], "Anchored VWAP")
        self.assertEqual(result["presentation_type"], "context")

    def test_institutional_accumulation_long_is_visible(self):
        payload = build_strategy_payload(make_accumulation_long_df())
        result = result_by_id(payload, "institutional_accumulation_long")
        self.assertIn(result["status"], {"ACTIVE", "CONFIRMING", "TRIGGER_WAIT", "READY"})
        self.assertEqual(result["phase"], "ACCUMULATION_CONFIRMED")

    def test_poc_rotation_long_reaches_confirmed_phase(self):
        payload = build_strategy_payload(make_poc_rotation_long_df())
        result = result_by_id(payload, "poc_rotation_long")
        self.assertIn(result["status"], {"ACTIVE", "CONFIRMING", "TRIGGER_WAIT"})
        self.assertEqual(result["phase"], "POC_RECLAIM_CONFIRMED")

    def test_ichimoku_breakout_long_expands_strategy_set(self):
        payload = build_strategy_payload(make_ichimoku_breakout_long_df())
        result = result_by_id(payload, "ichimoku_breakout_long")
        self.assertIn(result["status"], {"ACTIVE", "CONFIRMING", "TRIGGER_WAIT"})
        self.assertEqual(result["phase"], "ICHI_BREAKOUT_CONFIRMED")

    def test_ichimoku_breakout_short_uses_bearish_wording(self):
        payload = build_strategy_payload(make_ichimoku_breakout_short_df())
        result = result_by_id(payload, "ichimoku_breakout_short")
        self.assertIn(result["status"], {"ACTIVE", "CONFIRMING", "TRIGGER_WAIT"})
        self.assertEqual(result["label"], "Ichimoku 하향 이탈형")
        self.assertIn("하단", result["explanation"])
        self.assertNotIn("상단 돌파", result["explanation"])

    def test_fractal_alligator_long_is_active(self):
        payload = build_strategy_payload(make_trend_pullback_long_df())
        result = result_by_id(payload, "fractal_alligator_long")
        self.assertEqual(result["status"], "ACTIVE")
        self.assertEqual(result["phase"], "FRACTAL_BREAKOUT_CONFIRMED")

    def test_chaikin_flow_long_is_active(self):
        payload = build_strategy_payload(make_reversal_long_df())
        result = result_by_id(payload, "chaikin_flow_long")
        self.assertEqual(result["status"], "ACTIVE")
        self.assertEqual(result["phase"], "CHAIKIN_CONFIRMED")


class StrategyUiViewModelTests(unittest.TestCase):
    def test_ui_view_model_handles_no_strategy(self):
        model = build_strategy_tab_view_model({})
        self.assertEqual(model["top_label"], "-")
        self.assertEqual(model["visible_count"], 0)
        self.assertEqual(model["table_rows"], [])
        self.assertEqual(model["option_labels"], [])

    def test_ui_view_model_handles_single_dominant_strategy(self):
        meta = {
            "strategy_summary": {
                "active_count": 1,
                "visible_count": 1,
                "bullish_count": 1,
                "bearish_count": 0,
                "long_short_bias": "LONG",
                "conflict_level": "LOW",
                "top_strategy": {"label": "돌파 확인형", "score": 84.0, "direction": "LONG"},
                "secondary_strategies": [],
                "dominant_reasons": ["거래량 증가", "돌파 종가 유지"],
                "opposing_reasons": [],
            },
            "strategy_visible_results": [
                {
                    "label": "돌파 확인형",
                    "direction": "LONG",
                    "score": 84.0,
                    "status": "ACTIVE",
                    "phase": "BREAKOUT_CONFIRMED",
                    "entry_hint": "현재가 추격 가능",
                    "stop_loss": 100.0,
                    "target_1": 106.0,
                    "note": "돌파 확정",
                }
            ],
        }
        model = build_strategy_tab_view_model(meta)
        self.assertEqual(model["top_label"], "돌파 확인형")
        self.assertEqual(model["bias_text"], "Long 우세")
        self.assertEqual(model["table_rows"][0]["방향"], "LONG")
        self.assertIn("돌파 확정", model["option_labels"][0])

    def test_ui_view_model_handles_conflict_scenario(self):
        meta = {
            "strategy_summary": {
                "active_count": 2,
                "visible_count": 2,
                "bullish_count": 1,
                "bearish_count": 1,
                "long_short_bias": "BALANCED",
                "conflict_level": "HIGH",
                "top_strategy": {"label": "스퀴즈 발사형", "score": 82.0, "direction": "LONG"},
                "secondary_strategies": [{"label": "OBV 다이버전스", "score": 79.0, "direction": "SHORT"}],
                "dominant_reasons": ["Squeeze Off", "거래량 증가"],
                "opposing_reasons": ["장기 저항 인접", "OBV 약세"],
            },
            "strategy_visible_results": [
                {
                    "label": "스퀴즈 발사형",
                    "direction": "LONG",
                    "score": 82.0,
                    "status": "ACTIVE",
                    "phase": "TRIGGERED",
                    "entry_hint": "현재가 추격 가능",
                    "stop_loss": 98.0,
                    "target_1": 105.0,
                    "note": "확장 지속 확인",
                },
                {
                    "label": "OBV 다이버전스",
                    "direction": "SHORT",
                    "score": 79.0,
                    "status": "TRIGGER_WAIT",
                    "phase": "DIVERGENCE_READY",
                    "entry_hint": "확인 캔들 필요",
                    "stop_loss": 103.0,
                    "target_1": 97.5,
                    "note": "반대 근거 존재",
                },
            ],
        }
        model = build_strategy_tab_view_model(meta)
        self.assertEqual(model["conflict_level"], "HIGH")
        self.assertEqual(model["conflict_tone"], "negative")
        self.assertEqual(model["visible_count"], 2)
        self.assertEqual(model["table_rows"][1]["방향"], "SHORT")


    def test_ui_view_model_exposes_entry_price_column(self):
        meta = {
            "strategy_summary": {
                "active_count": 1,
                "visible_count": 1,
                "bullish_count": 1,
                "bearish_count": 0,
                "long_short_bias": "LONG",
                "conflict_level": "LOW",
                "top_strategy": {
                    "label": "Trend Pullback",
                    "score": 81.0,
                    "direction": "LONG",
                    "entry_price": 104.25,
                },
                "secondary_strategies": [],
                "dominant_reasons": ["EMA21 support", "Volume recovery"],
                "opposing_reasons": [],
            },
            "strategy_visible_results": [
                {
                    "label": "Trend Pullback",
                    "direction": "LONG",
                    "score": 81.0,
                    "status": "ACTIVE",
                    "phase": "TRIGGERED",
                    "entry_hint": "현재가 추격 가능",
                    "entry_price": 104.25,
                    "stop_loss": 101.8,
                    "target_1": 108.4,
                    "note": "추세 유지",
                },
            ],
        }
        model = build_strategy_tab_view_model(meta)
        self.assertEqual(model["top_entry_price_text"], "104.25")
        self.assertEqual(model["top_entry_reference_text"], "진입가 104.25")
        self.assertEqual(model["table_rows"][0]["진입 기준"], "진입가 104.25")

    def test_ui_view_model_maps_new_status_labels(self):
        meta = {
            "strategy_visible_results": [
                {
                    "label": "Breakout Confirmation",
                    "direction": "LONG",
                    "score": 67.0,
                    "status": "TRIGGER_WAIT",
                    "phase": "BREAKOUT_PENDING",
                    "entry_hint": "돌파 확인 대기",
                    "entry_price": 101.2,
                    "stop_loss": 99.4,
                    "target_1": 104.6,
                }
            ]
        }
        model = build_strategy_tab_view_model(meta)
        self.assertEqual(model["table_rows"][0]["상태"], "트리거 대기")
        self.assertEqual(model["table_rows"][0]["진입 기준"], "확인선 101.20")


if __name__ == "__main__":
    unittest.main()
