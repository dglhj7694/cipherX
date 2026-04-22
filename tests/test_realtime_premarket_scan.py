import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
import sys
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
    frame["MA50"] = frame["Close"] - 1.0
    frame["MA120"] = frame["Close"] - 2.0
    frame["MA200"] = frame["Close"] - 3.0
    frame["EMA8"] = frame["Close"] - 0.2
    frame["EMA21"] = frame["Close"] - 0.4
    frame["EMA50"] = frame["Close"] - 0.8
    frame["HMA"] = frame["Close"] - 0.1
    frame["HMA60"] = frame["Close"] - 0.3
    frame["HMA200"] = frame["Close"] - 0.6
    frame["Hull_Trend"] = "bullish"
    frame["New_52W_High"] = False
    frame["New_52W_Closing_High"] = False
    frame["Ensemble_Score"] = 3.0
    frame["Judgment_Confidence"] = 5.0
    frame["Judgment_Reason"] = "test"
    frame["Trade_Judgment"] = "WATCH_BUY"
    frame["Action_Label"] = "WATCH"
    frame["Market_Context"] = 2.0
    frame["Buy_Total"] = 3.0
    frame["Sell_Total"] = 1.0
    frame["Buy_Agree"] = 2.0
    frame["Sell_Agree"] = 0.0
    frame["ADX"] = 28.0
    frame["Ichimoku_SenkouA"] = frame["Close"] - 2.0
    frame["Ichimoku_SenkouB"] = frame["Close"] - 2.5
    frame["Fib_Swing_High"] = frame["Close"] + 2.0
    frame["Percent_B"] = 0.72
    frame["ATR"] = 1.4
    frame.iloc[-2, frame.columns.get_loc("ATR")] = 1.8
    frame["Volume_Ratio_20"] = 1.6
    frame["Volume_Ratio_50"] = 1.2
    frame["Volume_Oscillator"] = 0.8
    frame["Dollar_Volume_20"] = 1_500_000.0
    frame["Volume_Surge"] = True
    frame["Volume_Climax_Buy"] = False
    frame["Volume_Climax_Sell"] = False
    frame["OBV_Slope"] = 0.4
    frame["CMF"] = 0.12
    frame["VWAP"] = frame["Close"] - 0.4
    frame["BB_Mid"] = frame["Close"] - 0.8
    frame["BB_Up"] = frame["Close"] + 1.2
    frame["Price_Channel_Up"] = frame["Close"] + 0.8
    frame["RS_Ratio"] = 1.8
    frame["NR7"] = False
    frame["Inside_Day"] = False
    frame["Three_Weeks_Tight"] = False
    frame["Pocket_Pivot"] = False
    frame["System_Turn_Bull"] = False
    frame["Trend_Inflection_Bull"] = False
    frame["EMA_Pullback_Buy"] = False
    frame["UTBot_Buy"] = False
    frame["UTBot_Sell"] = False
    frame["Hull_Turn_Bull"] = False
    frame["Hull_Turn_Bear"] = False
    if turn_col:
        frame.loc[frame.index[-2], turn_col] = True
    return frame


def _mock_strategy_payload() -> dict[str, object]:
    return {
        "summary": {
            "conflict_level": "LOW",
            "long_short_bias": "LONG",
            "active_count": 1,
            "top_strategy": None,
        },
        "visible_results": [{"id": "TREND_PULLBACK", "direction": "LONG"}],
        "results": [{"id": "TREND_PULLBACK", "direction": "LONG"}],
    }


def _summary_row(run_at_kst: datetime, ticker: str, **overrides: object) -> dict[str, object]:
    target_date = pm._last_us_market_session_date(run_at_kst).isoformat()
    row: dict[str, object] = {
        "ticker": ticker,
        "price": 10.5,
        "chg_value": 0.5,
        "chg": 5.0,
        "gap_pct": 1.2,
        "chg_5d": 6.0,
        "scan_score": 180.0,
        "es": 6.0,
        "jg_key": "WATCH_BUY",
        "volume_ratio_20": 0.7,
        "volume_ratio_50": 1.1,
        "volume_oscillator": 0.5,
        "dollar_volume_20": 1_000_000.0,
        "volume_bullish": True,
        "volume_dry_up_score": 60.0,
        "volume_expansion_score": 70.0,
        "drawdown_from_20d_high_pct": -1.5,
        "pullback_from_swing_high_pct": -4.0,
        "pullback_ready": True,
        "pullback_reentry": True,
        "pullback_atr_multiple": 2.0,
        "uptrend_persistent": True,
        "bull_strength_recent": True,
        "low_conflict_bullish": True,
        "multi_buy": 4,
        "bb_percent_b": 0.7,
        "atr_contracting": True,
        "adx": 28.0,
        "hma20_slope_pct": 0.8,
        "hma60_slope_pct": 0.4,
        "cmf": 0.12,
        "obv_slope": 0.45,
        "weekly_trend_context": "UPTREND",
        "ichimoku_above_cloud": True,
        "utbot_buy_recent": True,
        "utbot_buy_last_date": target_date,
        "days_since_utbot_buy": 1,
        "hull_turn_bull_recent": False,
        "hull_turn_bull_last_date": "없음",
        "hull_turn_bear_recent": False,
        "hull_turn_bear_last_date": "없음",
        "utbot_sell_recent": False,
        "bull_turn_recent": True,
        "latest_bar_date": target_date,
        "new_52w_high": True,
        "pm_close": 10.6,
        "pm_vwap": 10.1,
        "change_pct": 1.5,
        "detected_buy_signal_latest_date": target_date,
        "detected_signal_latest_date": target_date,
        "effective_dollar_volume": 300_000.0,
        "mcap_turnover_pct": 0.015,
        "pm_volume_source": "tradingview",
        "ret20_pct": 22.0,
        "ret60_pct": 30.0,
        "ret120_pct": 40.0,
        "rs_ratio": 1.9,
    }
    row.update(overrides)
    return row


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
        ), patch.object(
            pm, "build_strategy_payload", return_value=_mock_strategy_payload()
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

    def test_tv_fallback_updates_synthetic_bar_volume_before_indicator_compute(self):
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
        captured: dict[str, object] = {}

        def _capture_indicator_input(frame: pd.DataFrame) -> pd.DataFrame:
            captured["latest_volume"] = float(frame.iloc[-1]["Volume"])
            return frame

        with patch.object(pm, "fetch_and_synthesize_daily", return_value=(hist, dict(metrics))), patch.object(
            pm, "compute_indicators", side_effect=_capture_indicator_input
        ), patch.object(pm, "detect_all_signals", return_value=signal), patch.object(
            pm, "_ensure_runtime_combo_registry", return_value=None
        ), patch.object(
            pm, "build_strategy_payload", return_value=_mock_strategy_payload()
        ):
            payload = pm._build_pm_scanner_row(
                "AAPL",
                "default",
                min_dollar_volume=1_000.0,
                min_turnover_pct=0.001,
                tv_volume=500.0,
            )

        self.assertTrue(payload.get("ok"))
        self.assertEqual(captured.get("latest_volume"), 500.0)

    def test_build_pm_scanner_row_populates_post_close_compatible_fields_and_pm_flags(self):
        hist = _base_hist()
        signal = _signal_frame("UTBot_Buy")
        metrics = {
            "pm_open": 100.0,
            "pm_high": 103.0,
            "pm_low": 99.5,
            "pm_close": 102.0,
            "pm_vwap": 101.2,
            "prev_close": 100.0,
            "prev_high": 101.0,
            "gap_pct": 2.0,
            "change_pct": 2.0,
            "market_cap": 2_000_000_000.0,
            "pm_volume_yf": 10_000.0,
            "pm_volume_tv": 0.0,
            "pm_volume_effective": 10_000.0,
            "pm_volume_source": "yfinance",
        }
        with patch.object(pm, "fetch_and_synthesize_daily", return_value=(hist, dict(metrics))), patch.object(
            pm, "compute_indicators", return_value=hist
        ), patch.object(pm, "detect_all_signals", return_value=signal), patch.object(
            pm, "_ensure_runtime_combo_registry", return_value=None
        ), patch.object(
            pm, "build_strategy_payload", return_value=_mock_strategy_payload()
        ):
            payload = pm._build_pm_scanner_row(
                "NVDA",
                "default",
                min_dollar_volume=1_000.0,
                min_turnover_pct=0.001,
                tv_volume=0.0,
            )

        self.assertTrue(payload.get("ok"))
        row = payload["row"]
        self.assertIn("scan_score", row)
        self.assertIn("chg_5d", row)
        self.assertIn("latest_bar_date", row)
        self.assertIn("pullback_reentry", row)
        self.assertIn("multi_buy", row)
        self.assertIn("volume_ratio_20", row)
        self.assertIn("cmf", row)
        self.assertIn("obv_slope", row)
        self.assertTrue(row["pm_supports_bullish"])
        self.assertFalse(row["pm_supports_bearish"])
        self.assertIn("PM +2.00%", row["pm_tag"])

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

    def test_build_premarket_summary_sections_filters_bullish_rows_when_pm_contradicts(self):
        run_at_kst = datetime(2026, 4, 21, 21, 0, 0, tzinfo=ZoneInfo("Asia/Seoul"))
        rows = [
            _summary_row(run_at_kst, "GOOD", chg_5d=12.0, rs_ratio=2.0, ret20_pct=25.0),
            _summary_row(
                run_at_kst,
                "BAD",
                chg_5d=11.0,
                rs_ratio=1.9,
                ret20_pct=24.0,
                pm_close=9.6,
                pm_vwap=10.1,
                change_pct=-2.5,
            ),
            _summary_row(
                run_at_kst,
                "WEAK",
                chg_5d=1.0,
                rs_ratio=0.5,
                ret20_pct=1.0,
                volume_ratio_20=1.4,
                volume_dry_up_score=0.0,
                drawdown_from_20d_high_pct=-12.0,
                bb_percent_b=0.2,
                atr_contracting=False,
                adx=10.0,
                hma20_slope_pct=0.0,
                cmf=0.0,
                ichimoku_above_cloud=False,
            ),
        ]

        section_rows = pm._build_premarket_summary_sections(rows, run_at_kst=run_at_kst)

        self.assertEqual([row["ticker"] for row in section_rows["gap_setup_rows"]], ["GOOD"])
        self.assertEqual([row["ticker"] for row in section_rows["five_day_top_rows"]], ["GOOD", "WEAK"])

    def test_build_premarket_summary_sections_keeps_only_bearish_support_in_hull_bear(self):
        run_at_kst = datetime(2026, 4, 21, 21, 0, 0, tzinfo=ZoneInfo("Asia/Seoul"))
        target_date = pm._last_us_market_session_date(run_at_kst).isoformat()
        rows = [
            _summary_row(
                run_at_kst,
                "BEAR",
                hull_turn_bear_last_date=target_date,
                pm_close=9.7,
                pm_vwap=10.0,
                change_pct=-0.8,
            ),
            _summary_row(
                run_at_kst,
                "BULL",
                hull_turn_bear_last_date=target_date,
                pm_close=10.8,
                pm_vwap=10.0,
                change_pct=1.1,
            ),
        ]

        section_rows = pm._build_premarket_summary_sections(rows, run_at_kst=run_at_kst)

        self.assertEqual([row["ticker"] for row in section_rows["legacy_hull_bear_rows"]], ["BEAR"])

    def test_format_telegram_summary_uses_thirteen_sections_with_core_briefing_rows(self):
        run_at_kst = datetime(2026, 4, 21, 21, 0, 0, tzinfo=ZoneInfo("Asia/Seoul"))
        target_date = pm._last_us_market_session_date(run_at_kst).isoformat()
        rows = [
            _summary_row(run_at_kst, "ALFA", utbot_buy_last_date=target_date, chg_5d=13.5, rs_ratio=2.1, ret20_pct=26.0),
            _summary_row(
                run_at_kst,
                "BETA",
                hull_turn_bear_last_date=target_date,
                pm_close=9.6,
                pm_vwap=10.1,
                change_pct=-1.4,
                chg_5d=-2.0,
                new_52w_high=False,
                bull_strength_recent=False,
                uptrend_persistent=False,
            ),
        ]

        summary = pm.format_telegram_summary(
            rows,
            run_at_kst,
            universe_count=50,
            skip_count=7,
            scan_label="프리마켓 21시 실시간 스캔",
            summary_limit=30,
        )

        self.assertIn(f"[1/13] {pm.PREMARKET_GAP_MOMENTUM_SECTION_NAME}", summary)
        self.assertIn(f"[2/13] {pm.PREMARKET_INFLOW_SECTION_NAME}", summary)
        self.assertIn(f"[3/13] {pm.PREMARKET_OPTIMAL_ENTRY_SECTION_NAME}", summary)
        self.assertIn("[4/13] 매수전환 (이전버전)", summary)
        self.assertIn("[11/13] 에너지 압축 → 돌파 임박", summary)
        self.assertIn("[13/13] 5일 변동률 상위종목", summary)
        self.assertIn("요약 인덱스:", summary)
        self.assertIn("GAP+1.20%", summary)
        self.assertIn("PM+1.50%", summary)
        self.assertIn("$300,000", summary)
        self.assertIn("5일 +13.50%", summary)

    def test_build_premarket_summary_sections_adds_core_sections_and_intersection(self):
        run_at_kst = datetime(2026, 4, 21, 21, 0, 0, tzinfo=ZoneInfo("Asia/Seoul"))
        rows = [
            _summary_row(run_at_kst, "AAA", gap_pct=3.0, change_pct=2.5, effective_dollar_volume=700_000.0, mcap_turnover_pct=0.030),
            _summary_row(run_at_kst, "BBB", gap_pct=2.1, change_pct=1.2, effective_dollar_volume=450_000.0, mcap_turnover_pct=0.0),
            _summary_row(run_at_kst, "CCC", gap_pct=-0.4, change_pct=0.8, effective_dollar_volume=900_000.0, mcap_turnover_pct=0.040),
        ]

        section_rows = pm._build_premarket_summary_sections(rows, run_at_kst=run_at_kst)

        gap_tickers = [row["ticker"] for row in section_rows["gap_momentum_rows"]]
        inflow_tickers = [row["ticker"] for row in section_rows["inflow_top_rows"]]
        self.assertEqual(gap_tickers, ["AAA", "BBB"])
        self.assertEqual(inflow_tickers, ["CCC", "AAA"])

        gap_intersection = {row["ticker"] for row in section_rows["gap_momentum_rows"] if row.get("pm_core_intersect")}
        inflow_intersection = {row["ticker"] for row in section_rows["inflow_top_rows"] if row.get("pm_core_intersect")}
        self.assertEqual(gap_intersection, {"AAA"})
        self.assertEqual(inflow_intersection, {"AAA"})

    def test_build_premarket_summary_sections_uses_time_adjusted_volume_thresholds(self):
        run_at_kst = datetime(2026, 4, 21, 21, 3, 0, tzinfo=ZoneInfo("Asia/Seoul"))
        target_date = pm._last_us_market_session_date(run_at_kst).isoformat()
        rows = [
            _summary_row(
                run_at_kst,
                "SOFTVOL",
                volume_ratio_20=0.06,
                latest_session_utbot_buy_turn=True,
                utbot_buy_last_date=target_date,
                detected_buy_signal_latest_date=target_date,
                cmf=0.2,
                obv_slope=0.3,
            )
        ]

        section_rows = pm._build_premarket_summary_sections(rows, run_at_kst=run_at_kst)

        self.assertEqual([row["ticker"] for row in section_rows["legacy_turn_rows"]], ["SOFTVOL"])
        self.assertEqual([row["ticker"] for row in section_rows["legacy_pullback_rows"]], ["SOFTVOL"])
        self.assertEqual([row["ticker"] for row in section_rows["buy_turn_filter_rows"]], ["SOFTVOL"])

    def test_optimal_entry_uses_buy_signal_freshness_and_priority_sort(self):
        run_at_kst = datetime(2026, 4, 21, 21, 0, 0, tzinfo=ZoneInfo("Asia/Seoul"))
        target_date = pm._last_us_market_session_date(run_at_kst)
        old_buy_date = (target_date - timedelta(days=4)).isoformat()
        rows = [
            _summary_row(
                run_at_kst,
                "AFAST",
                gap_pct=3.2,
                change_pct=2.1,
                mcap_turnover_pct=0.035,
                effective_dollar_volume=900_000.0,
                pullback_reentry=True,
                latest_session_utbot_buy_turn=True,
                detected_buy_signal_latest_date=target_date.isoformat(),
            ),
            _summary_row(
                run_at_kst,
                "BMED",
                gap_pct=2.0,
                change_pct=1.4,
                mcap_turnover_pct=0.020,
                effective_dollar_volume=500_000.0,
                pullback_reentry=True,
                latest_session_hull_buy_turn=True,
                detected_buy_signal_latest_date=target_date.isoformat(),
            ),
            _summary_row(
                run_at_kst,
                "CSTALE",
                gap_pct=2.8,
                change_pct=1.9,
                mcap_turnover_pct=0.030,
                effective_dollar_volume=750_000.0,
                pullback_reentry=True,
                latest_session_utbot_buy_turn=True,
                detected_buy_signal_latest_date=old_buy_date,
                detected_signal_latest_date=target_date.isoformat(),
            ),
        ]

        section_rows = pm._build_premarket_summary_sections(rows, run_at_kst=run_at_kst)
        optimal_tickers = [row["ticker"] for row in section_rows["optimal_entry_rows"]]

        self.assertEqual(optimal_tickers[:2], ["AFAST", "BMED"])
        self.assertNotIn("CSTALE", optimal_tickers)
        selected_map = {row["ticker"]: row for row in section_rows["optimal_entry_rows"]}
        self.assertEqual(selected_map["AFAST"]["pm_entry_reason"], "A4/B5/C4 | PASS")
        self.assertEqual(selected_map["BMED"]["pm_entry_reason"], "A4/B5/C4 | PASS")

    def test_core_row_format_includes_intersect_and_buy_labels_conditionally(self):
        run_at_kst = datetime(2026, 4, 21, 21, 0, 0, tzinfo=ZoneInfo("Asia/Seoul"))
        target_date = pm._last_us_market_session_date(run_at_kst).isoformat()
        rows = [
            _summary_row(
                run_at_kst,
                "DUAL",
                gap_pct=2.4,
                change_pct=1.8,
                effective_dollar_volume=800_000.0,
                mcap_turnover_pct=0.033,
                utbot_buy_recent=True,
                hull_turn_bull_recent=True,
                utbot_buy_last_date=target_date,
                hull_turn_bull_last_date=target_date,
                latest_session_utbot_buy_turn=True,
                latest_session_hull_buy_turn=True,
                detected_buy_signal_latest_date=target_date,
                pullback_reentry=True,
            )
        ]

        summary = pm.format_telegram_summary(
            rows,
            run_at_kst,
            universe_count=1,
            skip_count=0,
            scan_label="프리마켓 21시 실시간 스캔",
            summary_limit=30,
        )

        self.assertIn("1. DUAL | GAP+2.40% | PM+1.80% | $800,000 | 회전율0.033% | INTERSECT", summary)
        self.assertIn("1. DUAL | GAP+2.40% | PM+1.80% | $800,000 | 회전율0.033% | UTBOT+HULL", summary)

    def test_parse_args_summary_limit_defaults_to_30(self):
        with patch.object(sys, "argv", ["realtime_premarket_scan"]):
            args = pm.parse_args()
        self.assertEqual(args.summary_limit, 30)

    def test_summary_limit_truncates_section_rows(self):
        run_at_kst = datetime(2026, 4, 21, 21, 0, 0, tzinfo=ZoneInfo("Asia/Seoul"))
        rows = [
            _summary_row(
                run_at_kst,
                f"T{index:02d}",
                chg_5d=50.0 - index,
                volume_ratio_20=1.2,
                volume_dry_up_score=0.0,
                volume_expansion_score=0.0,
                drawdown_from_20d_high_pct=-12.0,
                bb_percent_b=0.2,
                atr_contracting=False,
                adx=10.0,
                hma20_slope_pct=0.0,
                cmf=0.0,
                obv_slope=0.0,
                ichimoku_above_cloud=False,
                utbot_buy_recent=False,
                utbot_buy_last_date="없음",
                days_since_utbot_buy=99,
                pullback_from_swing_high_pct=-20.0,
                pullback_ready=False,
                low_conflict_bullish=False,
                multi_buy=0,
                uptrend_persistent=False,
                bull_strength_recent=False,
                volume_bullish=False,
                new_52w_high=False,
                rs_ratio=0.1 + (index * 0.001),
                ret20_pct=1.0 + (index * 0.01),
            )
            for index in range(35)
        ]

        summary = pm.format_telegram_summary(
            rows,
            run_at_kst,
            universe_count=35,
            skip_count=0,
            scan_label="프리마켓 21시 실시간 스캔",
            summary_limit=30,
        )

        self.assertIn("건수: 30개", summary)
        self.assertIn("T00", summary)
        self.assertIn("T29", summary)
        self.assertNotIn("T30", summary)

    def test_merge_run_stats_collects_skip_reason_counts_from_skip_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "run_meta_shard0.json").write_text(
                json.dumps(
                    {
                        "universe_count": 10,
                        "shard_ticker_count": 10,
                        "performance": {"skip_count": 3},
                    }
                ),
                encoding="utf-8",
            )
            (root / "scan_skips_shard0.json").write_text(
                json.dumps(
                    [
                        {"ticker": "AAA", "reason": "no_group_matched"},
                        {"ticker": "BBB", "reason": "no_group_matched"},
                        {"ticker": "CCC", "reason": "engine_error"},
                    ]
                ),
                encoding="utf-8",
            )
            stats = pm._merge_run_stats(root)
        self.assertEqual(stats["skip_reason_counts"], {"no_group_matched": 2, "engine_error": 1})

    def test_pre_market_workflow_uses_realtime_script_without_prev_scan_dependency(self):
        workflow_path = Path(".github/workflows/pre_market_scan.yml")
        text = workflow_path.read_text(encoding="utf-8")
        self.assertIn("python -m scripts.realtime_premarket_scan", text)
        self.assertNotIn("--prev-scan-dir", text)
        self.assertNotIn("daily-scan-final-*", text)


if __name__ == "__main__":
    unittest.main()
