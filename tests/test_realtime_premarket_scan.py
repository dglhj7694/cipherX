import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pandas as pd

from scripts import realtime_premarket_scan as pm


def _base_hist(rows: int = 60) -> pd.DataFrame:
    idx = pd.date_range("2026-01-01", periods=rows, freq="D", tz="America/New_York")
    price = [100.0 + i * 0.1 for i in range(rows)]
    return pd.DataFrame(
        {
            "Open": price,
            "High": [p + 1.0 for p in price],
            "Low": [p - 1.0 for p in price],
            "Close": price,
            "Volume": [1_000.0 for _ in price],
        },
        index=idx,
    )


def _signal_frame(turn_col: str | None = None) -> pd.DataFrame:
    frame = _base_hist().copy()
    frame["MA20"] = frame["Close"] - 0.5
    frame["Hull_Trend"] = "bullish"
    frame["New_52W_High"] = False
    frame["Ensemble_Score"] = 3.0
    frame["Judgment_Confidence"] = 5.0
    frame["UTBot_Buy"] = False
    frame["UTBot_Sell"] = False
    frame["Hull_Turn_Bull"] = False
    frame["Hull_Turn_Bear"] = False
    if turn_col:
        frame.loc[frame.index[-2], turn_col] = True
    return frame


class RealtimePremarketScanTests(unittest.TestCase):
    def test_tv_fallback_applies_effective_volume_and_aliases(self):
        hist = _base_hist()
        signal = _signal_frame("UTBot_Buy")
        metrics = {
            "pm_open": 100.0,
            "pm_high": 102.0,
            "pm_low": 99.5,
            "pm_close": 101.0,
            "pm_vwap": 101.0,
            "prev_close": 100.0,
            "prev_high": 105.0,
            "gap_pct": 1.0,
            "change_pct": 1.0,
            "market_cap": 1_000_000_000.0,
            "pm_volume_yf": 0.0,
            "pm_volume_tv": 0.0,
            "pm_volume_effective": 0.0,
            "pm_volume_source": "none",
        }
        with patch.object(pm, "fetch_and_synthesize_daily", return_value=(hist, dict(metrics))), patch.object(
            pm, "compute_indicators", return_value=hist
        ), patch.object(pm, "detect_all_signals", return_value=signal), patch.object(
            pm, "_ensure_runtime_combo_registry", return_value=None
        ):
            payload = pm._build_pm_scanner_row(
                "AAPL",
                "default",
                min_dollar_volume=1_000.0,
                min_turnover_pct=0.001,
                tv_volume=500.0,
            )

        self.assertTrue(payload.get("ok"))
        row = payload["row"]
        self.assertEqual(row["pm_volume_source"], "tradingview")
        self.assertEqual(row["pm_volume_effective"], 500.0)
        self.assertEqual(row["pm_volume"], row["pm_volume_effective"])
        self.assertEqual(row["dollar_volume"], row["effective_dollar_volume"])
        self.assertEqual(row["mcap_ratio"], row["mcap_turnover_pct"])
        self.assertEqual(row["group"], "G2_BUY_TURN")

    def test_zero_dollar_volume_cannot_pass_buy_or_pullback_groups(self):
        hist = _base_hist()
        metrics = {
            "pm_open": 100.0,
            "pm_high": 101.0,
            "pm_low": 99.0,
            "pm_close": 100.5,
            "pm_vwap": 100.5,
            "prev_close": 100.0,
            "prev_high": 101.0,
            "gap_pct": 0.5,
            "change_pct": 0.5,
            "market_cap": 5_000_000_000.0,
            "pm_volume_yf": 0.0,
            "pm_volume_tv": 0.0,
            "pm_volume_effective": 0.0,
            "pm_volume_source": "none",
        }
        with patch.object(pm, "fetch_and_synthesize_daily", return_value=(hist, dict(metrics))):
            payload = pm._build_pm_scanner_row(
                "MSFT",
                "default",
                min_dollar_volume=1_000.0,
                min_turnover_pct=0.001,
                tv_volume=0.0,
            )
        self.assertFalse(payload.get("ok"))
        self.assertIn("low_effective_dollar_volume", str(payload.get("skip_reason")))

    def test_time_based_min_dollar_floor(self):
        et = ZoneInfo("America/New_York")
        kst = ZoneInfo("Asia/Seoul")

        run_early = datetime(2026, 4, 20, 5, 0, 0, tzinfo=et).astimezone(kst)
        run_mid = datetime(2026, 4, 20, 7, 0, 0, tzinfo=et).astimezone(kst)
        run_late = datetime(2026, 4, 20, 8, 0, 0, tzinfo=et).astimezone(kst)

        self.assertEqual(
            pm._premarket_min_dollar_floor(
                run_early,
                dollar_floor_early=20_000.0,
                dollar_floor_mid=40_000.0,
                dollar_floor_late=80_000.0,
            ),
            20_000.0,
        )
        self.assertEqual(
            pm._premarket_min_dollar_floor(
                run_mid,
                dollar_floor_early=20_000.0,
                dollar_floor_mid=40_000.0,
                dollar_floor_late=80_000.0,
            ),
            40_000.0,
        )
        self.assertEqual(
            pm._premarket_min_dollar_floor(
                run_late,
                dollar_floor_early=20_000.0,
                dollar_floor_mid=40_000.0,
                dollar_floor_late=80_000.0,
            ),
            80_000.0,
        )

    def test_group_sort_key_prioritizes_dollar_then_turnover_then_abs_gap(self):
        rows = [
            {"ticker": "AAA", "effective_dollar_volume": 100_000.0, "mcap_turnover_pct": 0.002, "gap_pct": 1.0},
            {"ticker": "BBB", "effective_dollar_volume": 150_000.0, "mcap_turnover_pct": 0.001, "gap_pct": 0.4},
            {"ticker": "CCC", "effective_dollar_volume": 100_000.0, "mcap_turnover_pct": 0.003, "gap_pct": 0.2},
        ]
        ranked = sorted(rows, key=pm._group_sort_key)
        self.assertEqual([row["ticker"] for row in ranked], ["BBB", "CCC", "AAA"])

    def test_pre_market_workflow_uses_realtime_script_without_prev_scan_dependency(self):
        workflow_path = Path(".github/workflows/pre_market_scan.yml")
        text = workflow_path.read_text(encoding="utf-8")
        self.assertIn("python -m scripts.realtime_premarket_scan", text)
        self.assertNotIn("--prev-scan-dir", text)
        self.assertNotIn("daily-scan-final-*", text)


if __name__ == "__main__":
    unittest.main()
