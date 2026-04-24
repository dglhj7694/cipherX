import unittest

import pandas as pd

from scripts.daily_scan_and_notify import (
    POST_CLOSE_LATEST_SESSION_FIELD_SPECS,
    _compute_post_close_row_metrics,
)


def _base_frame(rows: int = 30) -> pd.DataFrame:
    idx = pd.date_range("2026-01-01", periods=rows, freq="D")
    close = pd.Series([100.0 + i for i in range(rows)], index=idx, dtype=float)
    frame = pd.DataFrame(index=idx)
    frame["Open"] = close - 0.2
    frame["Close"] = close
    frame["High"] = close + 0.5
    frame["Low"] = close - 0.5
    frame["Volume"] = 1_000_000.0
    frame["MA20"] = close - 0.8
    frame["MA50"] = close - 1.2
    frame["MA120"] = close - 2.2
    frame["MA200"] = close - 3.2
    frame["EMA8"] = close - 0.4
    frame["EMA21"] = close - 0.7
    frame["EMA15"] = close - 0.6
    frame["EMA25"] = close - 0.9
    frame["EMA50"] = close - 1.3
    frame["EMA200"] = close - 3.4
    frame["HMA25"] = close - 0.3
    frame["HMA"] = close - 0.3
    frame["HMA60"] = close - 0.5
    frame["HMA200"] = close - 1.0
    frame["ATR"] = 2.0
    frame["Volume_Ratio_20"] = 1.2
    frame["OBV_Slope"] = 0.15
    frame["CMF"] = 0.08
    frame["ADX"] = 22.0
    frame["UTBot_Buy"] = False
    frame["Hull_Turn_Bull"] = False
    frame["Hull_Turn_Bear"] = False
    frame["System_Turn_Bull"] = False
    frame["Pocket_Pivot"] = False
    frame["HMA_EMA_Long_Aligned"] = False
    frame["HMA_EMA_Short_Aligned"] = False
    frame["HMA_EMA_Long_Entry"] = False
    frame["HMA_EMA_Short_Entry"] = False
    frame["HMA25_EMA25_Cross_Bull"] = False
    frame["HMA25_EMA25_Cross_Bear"] = False
    frame["HMA25_EMA15_Cross_Bear"] = False
    frame["HMA25_EMA15_Cross_Bull"] = False
    frame["HMA_EMA_Risk_To_EMA50_Pct"] = 2.5
    frame["HMA_EMA_EMA50_EMA200_Gap_Pct"] = 6.2
    return frame


class PostCloseHmaEmaMetricsTests(unittest.TestCase):
    def test_gap_field_name_and_ema200_fields_present(self):
        keys = {spec["key"] for spec in POST_CLOSE_LATEST_SESSION_FIELD_SPECS}
        self.assertIn("ema200", keys)
        self.assertIn("hma_ema_ema50_ema200_gap_pct", keys)
        self.assertNotIn("hma_ema_ema50_200_gap_pct", keys)

    def test_signal_state_priority_entry_over_aligned(self):
        frame = _base_frame()
        frame.loc[frame.index[-1], "HMA_EMA_Long_Aligned"] = True
        frame.loc[frame.index[-1], "HMA_EMA_Long_Entry"] = True
        metrics = _compute_post_close_row_metrics(frame)
        self.assertEqual(metrics["hma_ema_signal_state"], "LONG_ENTRY")

    def test_long_rr_invalid_when_close_below_or_equal_ema50(self):
        frame = _base_frame()
        frame.loc[frame.index[-1], "Close"] = 100.0
        frame.loc[frame.index[-1], "EMA50"] = 101.0
        metrics = _compute_post_close_row_metrics(frame)
        self.assertFalse(metrics["hma_ema_long_rr_valid"])
        self.assertIsNone(metrics["hma_ema_long_virtual_stop"])
        self.assertIsNone(metrics["hma_ema_long_target_2r"])

    def test_short_rr_invalid_when_close_above_or_equal_ema50(self):
        frame = _base_frame()
        frame.loc[frame.index[-1], "Close"] = 101.0
        frame.loc[frame.index[-1], "EMA50"] = 100.0
        metrics = _compute_post_close_row_metrics(frame)
        self.assertFalse(metrics["hma_ema_short_rr_valid"])
        self.assertIsNone(metrics["hma_ema_short_virtual_stop"])
        self.assertIsNone(metrics["hma_ema_short_target_2r"])


if __name__ == "__main__":
    unittest.main()

