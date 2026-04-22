import csv
import io
import json
import re
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

from scripts.daily_scan_and_notify import (
    POST_CLOSE_FINAL_ENTRY_FIELD_SPECS,
    POST_CLOSE_LATEST_SESSION_FIELD_SPECS,
    RUSSELL2000_UNIVERSE_ITEMS,
    ScanRunResult,
    _compute_post_close_row_metrics,
    _with_post_close_final_top20_scores,
    _with_post_close_cross_section_metrics,
    _with_post_close_setup_scores,
    _last_us_market_session_date,
    _run_post_close,
    _with_latest_session_buy_turn_flags,
    build_post_close_transition_summary,
    build_scan_universe,
    build_transition_summary,
    filter_turn_rows_for_telegram,
    merge_shard_scan_rows,
    select_post_close_buy_turn_rows_for_telegram,
    select_post_close_chase_rows_for_telegram,
    select_post_close_final_top_rows_for_telegram,
    select_post_close_gap_setup_rows_for_telegram,
    select_post_close_pocket_pivot_rows_for_telegram,
    select_post_close_pullback_rows_for_telegram,
    select_post_close_top_5d_rows_for_telegram,
    select_pullback_reentry_rows_for_telegram,
    select_us_session_52w_high_rows,
    select_us_session_hull_bear_rows,
    select_us_session_turn_rows,
    split_telegram_message_text,
    split_tickers_for_shard,
    write_scan_csv,
)


class DailyScanNotifyTests(unittest.TestCase):
    @staticmethod
    def _alpha_symbol(index: int) -> str:
        value = int(index)
        letters = []
        for _ in range(3):
            letters.append(chr(ord("A") + (value % 26)))
            value //= 26
        return "T" + "".join(reversed(letters))

    def test_build_scan_universe_combines_sector_and_etf_with_dedupe(self):
        fake_sectors = {"A": ["AAA", "BBB", "CCC"], "B": ["CCC", "DDD"]}
        fake_resolved = {
            "items": [{"requested": "S&P500", "resolved": "SPY"}],
            "tickers": ["EEE", "AAA", "FFF"],
            "note": "ok",
            "errors": [],
        }
        with patch("scripts.daily_scan_and_notify.SECTOR_GROUPS", fake_sectors), patch(
            "scripts.daily_scan_and_notify.resolve_etf_universe",
            return_value=fake_resolved,
        ):
            payload = build_scan_universe()

        self.assertEqual(payload["sector_count"], 4)
        self.assertEqual(payload["etf_count"], 3)
        self.assertEqual(payload["tickers"], ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF"])

    def test_build_scan_universe_russell2000_profile_uses_iwm_items(self):
        fake_sectors = {"A": ["AAA"]}
        captured = {}

        def _fake_resolve(items):
            captured["items"] = list(items)
            return {"items": [], "tickers": ["IWMA", "IWMB"], "note": "ok", "errors": []}

        with patch("scripts.daily_scan_and_notify.SECTOR_GROUPS", fake_sectors), patch(
            "scripts.daily_scan_and_notify.resolve_etf_universe",
            side_effect=_fake_resolve,
        ):
            payload = build_scan_universe(universe_profile="russell2000")

        self.assertEqual(payload["universe_profile"], "russell2000")
        self.assertEqual(captured["items"], list(RUSSELL2000_UNIVERSE_ITEMS))
        self.assertEqual(payload["tickers"], ["AAA", "IWMA", "IWMB"])

    def test_select_us_session_turn_rows_filters_previous_us_session(self):
        rows = [
            {"ticker": "AAA", "scan_score": 3.2, "utbot_buy_last_date": "2026-04-15", "hull_turn_bull_last_date": "없음"},
            {"ticker": "BBB", "scan_score": 9.0, "utbot_buy_last_date": "2026-04-14", "hull_turn_bull_last_date": "없음"},
            {"ticker": "CCC", "scan_score": 7.1, "utbot_buy_last_date": "없음", "hull_turn_bull_last_date": "2026-04-15"},
        ]
        selected = select_us_session_turn_rows(rows, run_at_kst=datetime(2026, 4, 16, 6, 15, 0))
        self.assertEqual([row["ticker"] for row in selected], ["CCC", "AAA"])
        self.assertEqual(selected[0]["transition_signals"], ["HULL 매수"])
        self.assertEqual(selected[1]["transition_signals"], ["UTBot 매수"])

    def test_with_latest_session_buy_turn_flags_uses_previous_us_session_for_5am_post_close(self):
        run_at_kst = datetime(2026, 4, 21, 5, 0, 0)
        target_date = _last_us_market_session_date(run_at_kst)
        self.assertEqual(target_date.isoformat(), "2026-04-20")

        rows = [
            {"ticker": "AAA", "utbot_buy_last_date": "2026-04-20", "hull_turn_bull_last_date": "2026-04-18"},
            {"ticker": "BBB", "utbot_buy_last_date": "2026-04-19", "hull_turn_bull_last_date": "2026-04-20"},
            {"ticker": "CCC", "utbot_buy_last_date": "N/A", "hull_turn_bull_last_date": "N/A"},
        ]
        flagged = _with_latest_session_buy_turn_flags(rows, target_date=target_date)

        self.assertTrue(flagged[0]["latest_session_utbot_buy_turn"])
        self.assertFalse(flagged[0]["latest_session_hull_buy_turn"])
        self.assertFalse(flagged[1]["latest_session_utbot_buy_turn"])
        self.assertTrue(flagged[1]["latest_session_hull_buy_turn"])
        self.assertFalse(flagged[2]["latest_session_utbot_buy_turn"])
        self.assertFalse(flagged[2]["latest_session_hull_buy_turn"])

    def test_write_scan_csv_post_close_extra_columns_and_default_headers(self):
        row = {
            "ticker": "AAPL",
            "latest_session_utbot_buy_turn": True,
            "latest_session_hull_buy_turn": False,
            "chg_5d": 3.42,
            "gap_risk_2pct": True,
            "atr_contracting": True,
            "weekly_trend_context": "STRONG_UPTREND",
            "gap_setup_score": 8,
            "gap_setup_gate_count": 4,
            "gap_setup_candidate": True,
            "pocket_pivot_score": 9,
            "pocket_pivot_gate_count": 4,
            "pocket_pivot_candidate": False,
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir)
            with_extra = write_scan_csv(
                [row],
                out_dir=out_dir,
                run_label="post_close_extra",
                extra_field_specs=POST_CLOSE_LATEST_SESSION_FIELD_SPECS,
            )
            without_extra = write_scan_csv([row], out_dir=out_dir, run_label="default_no_extra")

            extra_rows = list(csv.reader(io.StringIO(with_extra.read_text(encoding="utf-8-sig"))))
            base_rows = list(csv.reader(io.StringIO(without_extra.read_text(encoding="utf-8-sig"))))

        extra_header = extra_rows[0]
        extra_data = extra_rows[1]
        base_header = base_rows[0]

        utbot_idx = next(i for i, name in enumerate(extra_header) if str(name).endswith("(latest_session_utbot_buy_turn)"))
        hull_idx = next(i for i, name in enumerate(extra_header) if str(name).endswith("(latest_session_hull_buy_turn)"))
        chg_5d_idx = next(i for i, name in enumerate(extra_header) if str(name).endswith("(chg_5d)"))
        gap_risk_idx = next(i for i, name in enumerate(extra_header) if str(name).endswith("(gap_risk_2pct)"))
        atr_contracting_idx = next(i for i, name in enumerate(extra_header) if str(name).endswith("(atr_contracting)"))
        weekly_trend_idx = next(i for i, name in enumerate(extra_header) if str(name).endswith("(weekly_trend_context)"))
        gap_setup_score_idx = next(i for i, name in enumerate(extra_header) if str(name).endswith("(gap_setup_score)"))
        gap_setup_candidate_idx = next(i for i, name in enumerate(extra_header) if str(name).endswith("(gap_setup_candidate)"))
        pocket_pivot_candidate_idx = next(i for i, name in enumerate(extra_header) if str(name).endswith("(pocket_pivot_candidate)"))
        self.assertEqual(extra_data[utbot_idx], "Y")
        self.assertEqual(extra_data[hull_idx], "N")
        self.assertEqual(extra_data[chg_5d_idx], "3.42")
        self.assertEqual(extra_data[gap_risk_idx], "Y")
        self.assertEqual(extra_data[atr_contracting_idx], "Y")
        self.assertEqual(extra_data[weekly_trend_idx], "STRONG_UPTREND")
        self.assertEqual(extra_data[gap_setup_score_idx], "8")
        self.assertEqual(extra_data[gap_setup_candidate_idx], "Y")
        self.assertEqual(extra_data[pocket_pivot_candidate_idx], "N")

        self.assertFalse(any(str(name).endswith("(latest_session_utbot_buy_turn)") for name in base_header))
        self.assertFalse(any(str(name).endswith("(latest_session_hull_buy_turn)") for name in base_header))
        self.assertFalse(any(str(name).endswith("(chg_5d)") for name in base_header))
        self.assertFalse(any(str(name).endswith("(gap_risk_2pct)") for name in base_header))

    def test_write_scan_csv_post_close_final_entry_columns(self):
        row = {
            "ticker": "MSFT",
            "a_score": 4,
            "b_score": 3,
            "c_score": 2,
            "final_entry_score": 98.12,
            "final_entry_rank": 1,
            "final_entry_selected": True,
            "final_entry_reason": "A4/B3/C2 | PASS",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir)
            csv_path = write_scan_csv(
                [row],
                out_dir=out_dir,
                run_label="post_close_final_entry",
                extra_field_specs=[*POST_CLOSE_LATEST_SESSION_FIELD_SPECS, *POST_CLOSE_FINAL_ENTRY_FIELD_SPECS],
            )
            csv_rows = list(csv.reader(io.StringIO(csv_path.read_text(encoding="utf-8-sig"))))

        header = csv_rows[0]
        data = csv_rows[1]
        a_idx = next(i for i, name in enumerate(header) if str(name).endswith("(a_score)"))
        b_idx = next(i for i, name in enumerate(header) if str(name).endswith("(b_score)"))
        c_idx = next(i for i, name in enumerate(header) if str(name).endswith("(c_score)"))
        score_idx = next(i for i, name in enumerate(header) if str(name).endswith("(final_entry_score)"))
        rank_idx = next(i for i, name in enumerate(header) if str(name).endswith("(final_entry_rank)"))
        selected_idx = next(i for i, name in enumerate(header) if str(name).endswith("(final_entry_selected)"))
        reason_idx = next(i for i, name in enumerate(header) if str(name).endswith("(final_entry_reason)"))
        self.assertEqual(data[a_idx], "4")
        self.assertEqual(data[b_idx], "3")
        self.assertEqual(data[c_idx], "2")
        self.assertEqual(data[score_idx], "98.12")
        self.assertEqual(data[rank_idx], "1")
        self.assertIn(data[selected_idx], {"Y", "True"})
        self.assertEqual(data[reason_idx], "A4/B3/C2 | PASS")

    def test_filter_turn_rows_for_telegram_uses_volume_ratio_gt_one(self):
        rows = [
            {"ticker": "AAA", "scan_score": 5.0, "volume_ratio_20": 1.0},
            {"ticker": "BBB", "scan_score": 8.0, "volume_ratio_20": 1.01},
            {"ticker": "CCC", "scan_score": 4.0, "volume_ratio_20": 2.5},
        ]
        filtered = filter_turn_rows_for_telegram(rows, min_volume_ratio_20_exclusive=1.0)
        self.assertEqual([row["ticker"] for row in filtered], ["BBB", "CCC"])

    def test_select_pullback_reentry_rows_for_telegram(self):
        rows = [
            {"ticker": "AAA", "scan_score": 7.0, "pullback_reentry": True, "volume_ratio_20": 1.01},
            {"ticker": "BBB", "scan_score": 8.0, "pullback_reentry": False, "volume_ratio_20": 2.0},
            {"ticker": "CCC", "scan_score": 9.0, "pullback_reentry": True, "volume_ratio_20": 1.0},
        ]
        selected = select_pullback_reentry_rows_for_telegram(rows, min_volume_ratio_20_exclusive=1.0)
        self.assertEqual([row["ticker"] for row in selected], ["AAA"])

    def test_select_post_close_pullback_rows_for_telegram(self):
        rows = [
            {
                "ticker": "AAA",
                "scan_score": 15.0,
                "es": 7.0,
                "uptrend_persistent": True,
                "hma60_slope_pct": 0.5,
                "pullback_from_swing_high_pct": -3.0,
                "drawdown_from_20d_high_pct": -1.8,
                "pullback_atr_multiple": 2.2,
                "pullback_ready": True,
                "pullback_reentry": False,
                "volume_dry_up_score": 10.0,
                "utbot_sell_recent": False,
                "hull_turn_bear_recent": False,
            },
            {
                "ticker": "BBB",
                "scan_score": 20.0,
                "es": 8.0,
                "uptrend_persistent": True,
                "hma60_slope_pct": 0.4,
                "pullback_from_swing_high_pct": -2.5,
                "drawdown_from_20d_high_pct": -1.2,
                "pullback_atr_multiple": 2.0,
                "pullback_ready": True,
                "pullback_reentry": False,
                "volume_dry_up_score": 11.0,
                "utbot_sell_recent": True,
                "hull_turn_bear_recent": False,
            },
        ]
        selected = select_post_close_pullback_rows_for_telegram(rows)
        self.assertEqual([row["ticker"] for row in selected], ["AAA"])

    def test_select_post_close_chase_rows_for_telegram(self):
        rows = [
            {
                "ticker": "AAA",
                "scan_score": 130.0,
                "es": 6.0,
                "bull_strength_recent": True,
                "uptrend_persistent": True,
                "hma20_slope_pct": 0.3,
                "hma60_slope_pct": 0.2,
                "volume_bullish": True,
                "adx": 22.0,
                "rs_rank_vs_index": 72.0,
                "multi_buy": 3,
                "dist_sma20_pct": 8.0,
                "zscore20": 1.5,
                "utbot_sell_recent": False,
                "hull_turn_bear_recent": False,
            },
            {
                "ticker": "BBB",
                "scan_score": 119.9,
                "es": 7.0,
                "bull_strength_recent": True,
                "uptrend_persistent": True,
                "hma20_slope_pct": 0.4,
                "hma60_slope_pct": 0.3,
                "volume_bullish": True,
                "adx": 25.0,
                "rs_rank_vs_index": 80.0,
                "multi_buy": 3,
                "dist_sma20_pct": 5.0,
                "zscore20": 1.2,
                "utbot_sell_recent": False,
                "hull_turn_bear_recent": False,
            },
        ]
        selected = select_post_close_chase_rows_for_telegram(rows)
        self.assertEqual([row["ticker"] for row in selected], ["AAA"])

    def test_select_post_close_buy_turn_rows_for_telegram(self):
        run_at_kst = datetime(2026, 4, 17, 6, 15, 0)
        rows = [
            {
                "ticker": "AAA",
                "scan_score": 30.0,
                "es": 8.0,
                "latest_session_utbot_buy_turn": True,
                "latest_session_hull_buy_turn": False,
                "days_since_utbot_buy": 0,
                "days_since_hull_turn_bull": 9,
                "utbot_buy_last_date": "2026-04-16",
                "hull_turn_bull_last_date": "2026-04-12",
                "utbot_buy_recent": True,
                "hull_turn_bull_recent": False,
                "bull_turn_recent": True,
                "cmf": 0.01,
                "obv_slope": 0.20,
                "volume_ratio_20": 1.1,
                "utbot_sell_last_date": "2026-04-10",
                "hull_turn_bear_last_date": "2026-04-11",
            },
            {
                "ticker": "BBB",
                "scan_score": 25.0,
                "es": 7.0,
                "latest_session_utbot_buy_turn": False,
                "latest_session_hull_buy_turn": False,
                "days_since_utbot_buy": 1,
                "days_since_hull_turn_bull": 6,
                "utbot_buy_last_date": "2026-04-15",
                "hull_turn_bull_last_date": "2026-04-10",
                "utbot_buy_recent": True,
                "hull_turn_bull_recent": False,
                "bull_turn_recent": True,
                "cmf": 0.04,
                "obv_slope": 0.11,
                "volume_ratio_20": 1.0,
                "utbot_sell_last_date": "2026-04-14",
                "hull_turn_bear_last_date": "2026-04-14",
            },
            {
                "ticker": "CCC",
                "scan_score": 40.0,
                "es": 9.0,
                "latest_session_utbot_buy_turn": True,
                "latest_session_hull_buy_turn": False,
                "days_since_utbot_buy": 0,
                "days_since_hull_turn_bull": 2,
                "utbot_buy_last_date": "2026-04-16",
                "hull_turn_bull_last_date": "2026-04-14",
                "utbot_buy_recent": True,
                "hull_turn_bull_recent": True,
                "bull_turn_recent": True,
                "cmf": 0.02,
                "obv_slope": 0.10,
                "volume_ratio_20": 1.2,
                "utbot_sell_last_date": "2026-04-16",
                "hull_turn_bear_last_date": "2026-04-10",
            },
            {
                "ticker": "DDD",
                "scan_score": 50.0,
                "es": 9.0,
                "latest_session_utbot_buy_turn": True,
                "latest_session_hull_buy_turn": False,
                "days_since_utbot_buy": 0,
                "days_since_hull_turn_bull": 2,
                "utbot_buy_last_date": "2026-04-16",
                "hull_turn_bull_last_date": "2026-04-14",
                "utbot_buy_recent": True,
                "hull_turn_bull_recent": True,
                "bull_turn_recent": True,
                "cmf": 0.02,
                "obv_slope": 0.10,
                "volume_ratio_20": 0.9,
                "utbot_sell_last_date": "2026-04-15",
                "hull_turn_bear_last_date": "2026-04-10",
            },
        ]
        selected = select_post_close_buy_turn_rows_for_telegram(rows, run_at_kst=run_at_kst, scan_mode="post_close")
        self.assertEqual([row["ticker"] for row in selected], ["AAA", "BBB"])
        self.assertEqual(selected[0]["buy_turn_filter_tag"], "Tier1 D0")
        self.assertEqual(selected[1]["buy_turn_filter_tag"], "Tier2 D1-2")

    def test_select_post_close_buy_turn_rows_for_telegram_accepts_custom_volume_threshold(self):
        run_at_kst = datetime(2026, 4, 17, 21, 3, 0)
        rows = [
            {
                "ticker": "LOWVOL",
                "scan_score": 20.0,
                "es": 6.0,
                "latest_session_utbot_buy_turn": True,
                "latest_session_hull_buy_turn": False,
                "days_since_utbot_buy": 0,
                "days_since_hull_turn_bull": 9,
                "utbot_buy_last_date": "2026-04-16",
                "hull_turn_bull_last_date": "2026-04-12",
                "utbot_buy_recent": True,
                "hull_turn_bull_recent": False,
                "bull_turn_recent": True,
                "cmf": 0.05,
                "obv_slope": 0.15,
                "volume_ratio_20": 0.06,
                "utbot_sell_last_date": "2026-04-10",
                "hull_turn_bear_last_date": "2026-04-11",
            }
        ]
        strict_selected = select_post_close_buy_turn_rows_for_telegram(rows, run_at_kst=run_at_kst, scan_mode="post_close")
        relaxed_selected = select_post_close_buy_turn_rows_for_telegram(
            rows,
            run_at_kst=run_at_kst,
            scan_mode="post_close",
            min_volume_ratio_20_exclusive=0.05,
        )
        self.assertEqual(strict_selected, [])
        self.assertEqual([row["ticker"] for row in relaxed_selected], ["LOWVOL"])

    def test_actionable_post_close_sections_exclude_thin_trade_risk(self):
        run_at_kst = datetime(2026, 4, 17, 6, 15, 0)

        pullback_row = {
            "ticker": "PULL",
            "thin_trade_risk": True,
            "uptrend_persistent": True,
            "hma60_slope_pct": 0.2,
            "pullback_from_swing_high_pct": -5.0,
            "drawdown_from_20d_high_pct": -3.0,
            "pullback_atr_multiple": 2.0,
            "pullback_ready": True,
            "pullback_reentry": False,
            "volume_dry_up_score": 10.0,
            "utbot_sell_recent": False,
            "hull_turn_bear_recent": False,
        }
        chase_row = {
            "ticker": "CHASE",
            "thin_trade_risk": True,
            "bull_strength_recent": True,
            "uptrend_persistent": True,
            "hma20_slope_pct": 0.5,
            "hma60_slope_pct": 0.4,
            "volume_bullish": True,
            "adx": 20.0,
            "rs_rank_vs_index": 70.0,
            "multi_buy": 3.0,
            "dist_sma20_pct": 5.0,
            "zscore20": 1.0,
            "scan_score": 130.0,
            "utbot_sell_recent": False,
            "hull_turn_bear_recent": False,
        }
        buy_turn_row = {
            "ticker": "TURN",
            "thin_trade_risk": True,
            "latest_session_utbot_buy_turn": True,
            "latest_session_hull_buy_turn": False,
            "days_since_utbot_buy": 0,
            "days_since_hull_turn_bull": 3,
            "utbot_buy_last_date": "2026-04-16",
            "hull_turn_bull_last_date": "2026-04-10",
            "utbot_buy_recent": True,
            "hull_turn_bull_recent": False,
            "bull_turn_recent": True,
            "utbot_sell_last_date": "2026-04-10",
            "hull_turn_bear_last_date": "2026-04-11",
            "cmf": 0.01,
            "obv_slope": 0.20,
            "volume_ratio_20": 1.1,
        }
        gap_row = {
            "ticker": "GAP",
            "thin_trade_risk": True,
            "gap_setup_candidate": True,
            "gap_setup_score": 8,
            "gap_setup_gate_count": 4,
            "gap_setup_hits": ["DryUp"],
            "gap_setup_quality_hits": ["WUp"],
        }
        pocket_row = {
            "ticker": "POCKET",
            "thin_trade_risk": True,
            "pocket_pivot_candidate": True,
            "pocket_pivot_score": 9,
            "pocket_pivot_gate_count": 4,
            "pocket_pivot_hits": ["VolExp"],
            "pocket_pivot_quality_hits": ["WUp"],
        }

        self.assertEqual(select_post_close_pullback_rows_for_telegram([pullback_row]), [])
        self.assertEqual(select_post_close_chase_rows_for_telegram([chase_row]), [])
        self.assertEqual(select_post_close_buy_turn_rows_for_telegram([buy_turn_row], run_at_kst=run_at_kst, scan_mode="post_close"), [])
        self.assertEqual(select_post_close_gap_setup_rows_for_telegram([gap_row]), [])
        self.assertEqual(select_post_close_pocket_pivot_rows_for_telegram([pocket_row]), [])

    def test_legacy_post_close_sections_keep_thin_trade_risk_rows(self):
        turn_rows = filter_turn_rows_for_telegram(
            [{"ticker": "AAA", "scan_score": 20.0, "es": 5.0, "volume_ratio_20": 1.2, "thin_trade_risk": True}]
        )
        pullback_rows = select_pullback_reentry_rows_for_telegram(
            [{"ticker": "BBB", "scan_score": 20.0, "es": 5.0, "volume_ratio_20": 1.2, "thin_trade_risk": True, "pullback_reentry": True}]
        )

        self.assertEqual([row["ticker"] for row in turn_rows], ["AAA"])
        self.assertEqual([row["ticker"] for row in pullback_rows], ["BBB"])

    def test_with_post_close_setup_scores_populates_gap_and_pocket_candidates(self):
        rows = [
            {
                "ticker": "AAA",
                "volume_ratio_20": 0.7,
                "drawdown_from_20d_high_pct": -2.0,
                "bb_percent_b": 0.70,
                "atr_contracting": True,
                "rs_rank_vs_index": 81.0,
                "ret20_percentile": 92.0,
                "hma20_slope_pct": 0.7,
                "adx": 30.0,
                "volume_dry_up_score": 60.0,
                "cmf": 0.10,
                "ichimoku_above_cloud": True,
                "volume_expansion_score": 70.0,
                "days_since_utbot_buy": 1,
                "utbot_buy_recent": True,
                "pullback_from_swing_high_pct": -5.0,
                "pullback_ready": True,
                "obv_slope": 0.60,
                "multi_buy": 5,
                "low_conflict_bullish": True,
                "nr7_flag": True,
                "inside_day_flag": False,
                "three_weeks_tight": True,
                "tight_close_near_high_3d": True,
                "near_52w_high_2pct": True,
                "weekly_trend_context": "STRONG_UPTREND",
                "pocket_pivot_recent": True,
                "days_since_pocket_pivot": 2,
            },
            {
                "ticker": "BBB",
                "volume_ratio_20": 2.0,
                "drawdown_from_20d_high_pct": -4.0,
                "bb_percent_b": 0.65,
                "atr_contracting": True,
                "rs_rank_vs_index": 70.0,
                "ret20_percentile": 80.0,
                "hma20_slope_pct": 0.6,
                "adx": 28.0,
                "volume_dry_up_score": 0.0,
                "cmf": 0.10,
                "ichimoku_above_cloud": True,
                "volume_expansion_score": 70.0,
                "days_since_utbot_buy": 1,
                "utbot_buy_recent": True,
                "pullback_from_swing_high_pct": -5.0,
                "pullback_ready": True,
                "obv_slope": 0.60,
                "multi_buy": 5,
                "low_conflict_bullish": True,
                "nr7_flag": True,
                "inside_day_flag": False,
                "three_weeks_tight": True,
                "tight_close_near_high_3d": True,
                "near_52w_high_2pct": True,
                "weekly_trend_context": "STRONG_UPTREND",
                "pocket_pivot_recent": True,
                "days_since_pocket_pivot": 2,
            },
            {
                "ticker": "CCC",
                "volume_ratio_20": 1.1,
                "drawdown_from_20d_high_pct": -7.0,
                "bb_percent_b": 0.20,
                "atr_contracting": False,
                "rs_rank_vs_index": 30.0,
                "ret20_percentile": 40.0,
                "hma20_slope_pct": 0.1,
                "adx": 18.0,
                "volume_dry_up_score": 10.0,
                "cmf": -0.05,
                "ichimoku_above_cloud": False,
                "volume_expansion_score": 20.0,
                "days_since_utbot_buy": 8,
                "utbot_buy_recent": False,
                "pullback_from_swing_high_pct": -12.0,
                "pullback_ready": False,
                "obv_slope": -0.10,
                "multi_buy": 1,
                "low_conflict_bullish": False,
            },
        ]

        scored = _with_post_close_setup_scores(rows)

        self.assertEqual(scored[0]["gap_setup_score"], 11)
        self.assertEqual(scored[0]["gap_setup_gate_count"], 5)
        self.assertTrue(scored[0]["gap_setup_candidate"])
        self.assertEqual(scored[1]["pocket_pivot_score"], 12)
        self.assertEqual(scored[1]["pocket_pivot_gate_count"], 5)
        self.assertTrue(scored[1]["pocket_pivot_candidate"])
        self.assertFalse(scored[2]["gap_setup_candidate"])
        self.assertFalse(scored[2]["pocket_pivot_candidate"])

    def test_select_post_close_gap_setup_rows_for_telegram_uses_gate_and_top30(self):
        rows = []
        for idx in range(35):
            rows.append(
                {
                    "ticker": f"G{idx:03d}",
                    "scan_score": float(idx),
                    "es": 5.0,
                    "volume_ratio_20": 0.7,
                    "drawdown_from_20d_high_pct": -2.0,
                    "bb_percent_b": 0.70,
                    "atr_contracting": True,
                    "rs_rank_vs_index": 82.0,
                    "ret20_percentile": 90.0,
                    "hma20_slope_pct": 0.7,
                    "adx": 30.0,
                    "volume_dry_up_score": 60.0,
                    "cmf": 0.12,
                    "ichimoku_above_cloud": True,
                    "nr7_flag": idx % 2 == 0,
                    "inside_day_flag": False,
                    "three_weeks_tight": False,
                    "tight_close_near_high_3d": True,
                    "near_52w_high_2pct": True,
                    "weekly_trend_context": "STRONG_UPTREND",
                }
            )
        rows.append(
            {
                "ticker": "BAD",
                "scan_score": 999.0,
                "es": 9.0,
                "volume_ratio_20": 1.0,
                "drawdown_from_20d_high_pct": -9.0,
                "bb_percent_b": 0.10,
                "atr_contracting": False,
                "rs_rank_vs_index": 20.0,
                "ret20_percentile": 20.0,
                "hma20_slope_pct": 0.1,
                "adx": 10.0,
                "volume_dry_up_score": 5.0,
                "cmf": -0.1,
                "ichimoku_above_cloud": False,
            }
        )

        selected = select_post_close_gap_setup_rows_for_telegram(_with_post_close_setup_scores(rows))
        self.assertEqual(len(selected), 30)
        self.assertEqual(selected[0]["ticker"], "G034")
        self.assertEqual(selected[-1]["ticker"], "G005")
        self.assertNotIn("BAD", [row["ticker"] for row in selected])
        self.assertEqual(
            selected[0]["gap_setup_tag"],
            "GAP 11/11 | G5/5 | 거래량건조, 20일고점근접, 상대강도, 밴드압축, 추세강도, HMA상승",
        )

    def test_select_post_close_pocket_pivot_rows_for_telegram_uses_gate_and_top30(self):
        rows = []
        for idx in range(35):
            rows.append(
                {
                    "ticker": f"P{idx:03d}",
                    "scan_score": float(idx),
                    "es": 6.0,
                    "volume_expansion_score": 70.0,
                    "volume_ratio_20": 2.0,
                    "days_since_utbot_buy": 1,
                    "utbot_buy_recent": True,
                    "pullback_from_swing_high_pct": -5.0,
                    "pullback_ready": True,
                    "cmf": 0.10,
                    "obv_slope": 0.60,
                    "multi_buy": 5,
                    "low_conflict_bullish": True,
                    "ichimoku_above_cloud": True,
                    "nr7_flag": True,
                    "inside_day_flag": idx % 2 == 0,
                    "up_close_streak": 3,
                    "weekly_trend_context": "STRONG_UPTREND",
                    "pocket_pivot_recent": True,
                    "days_since_pocket_pivot": 2,
                }
            )
        rows.append(
            {
                "ticker": "BAD",
                "scan_score": 999.0,
                "es": 9.0,
                "volume_expansion_score": 10.0,
                "volume_ratio_20": 1.0,
                "days_since_utbot_buy": 8,
                "utbot_buy_recent": False,
                "pullback_from_swing_high_pct": -12.0,
                "pullback_ready": False,
                "cmf": -0.10,
                "obv_slope": -0.20,
                "multi_buy": 1,
                "low_conflict_bullish": False,
                "ichimoku_above_cloud": False,
            }
        )

        selected = select_post_close_pocket_pivot_rows_for_telegram(_with_post_close_setup_scores(rows))
        self.assertEqual(len(selected), 30)
        self.assertEqual(selected[0]["ticker"], "P034")
        self.assertEqual(selected[-1]["ticker"], "P005")
        self.assertNotIn("BAD", [row["ticker"] for row in selected])
        self.assertEqual(
            selected[0]["pocket_pivot_tag"],
            "PP 12/12 | G5/5 | 거래량팽창, 20일대비1.5배, UT최근3일, 멀티매수4+, 눌림8%이내, OBV상승",
        )

    def test_select_post_close_top_5d_rows_for_telegram_uses_positive_only_and_top30(self):
        rows = []
        for idx in range(35):
            rows.append(
                {
                    "ticker": f"F{idx:03d}",
                    "chg_5d": float(idx + 1),
                    "scan_score": float(100 - idx),
                    "es": 5.0,
                }
            )
        rows.extend(
            [
                {"ticker": "ZERO", "chg_5d": 0.0, "scan_score": 999.0, "es": 9.0},
                {"ticker": "NEG", "chg_5d": -4.0, "scan_score": 999.0, "es": 9.0},
            ]
        )

        selected = select_post_close_top_5d_rows_for_telegram(rows)

        self.assertEqual(len(selected), 30)
        self.assertEqual(selected[0]["ticker"], "F034")
        self.assertEqual(selected[-1]["ticker"], "F005")
        self.assertNotIn("ZERO", [row["ticker"] for row in selected])
        self.assertNotIn("NEG", [row["ticker"] for row in selected])
        self.assertEqual(selected[0]["five_day_top_tag"], "5일 +35.00%")

    def test_with_post_close_final_top20_scores_applies_abc_gates_and_top20(self):
        run_at_kst = datetime(2026, 4, 22, 6, 15, 0)

        def _base_row(ticker: str, *, scan_score: float, es: float) -> dict[str, object]:
            return {
                "ticker": ticker,
                "scan_score": scan_score,
                "es": es,
                "jg_key": "BUY",
                "chg_value": 1.0,
                "chg": 1.0,
                "volume_ratio_20": 1.2,
                "thin_trade_risk": False,
                "weekly_trend_context": "STRONG_UPTREND",
                "ichimoku_above_cloud": True,
                "drawdown_from_52w_high_pct": -10.0,
                "adx": 25.0,
                "hma60_slope_pct": 0.2,
                "pullback_reentry": True,
                "pocket_pivot_candidate": False,
                "gap_setup_candidate": True,
                "pullback_atr_multiple": 1.0,
                "detected_buy_signal_latest_date": "2026-04-21",
                "detected_signal_latest_date": "2026-04-21",
                "latest_session_utbot_buy_turn": True,
                "latest_session_hull_buy_turn": False,
                "cmf": 0.10,
                "obv_slope": 0.20,
                "volume_bullish": True,
                "volume_abnormal": False,
            }

        rows: list[dict[str, object]] = []
        for idx in range(35):
            rows.append(_base_row(f"P{idx:03d}", scan_score=180.0 - idx, es=70.0 - float(idx % 5)))

        rows[5]["pullback_reentry"] = False
        rows[5]["pocket_pivot_candidate"] = True  # B dimension OR gate

        rows.append(
            _base_row("BOUND_PASS", scan_score=400.0, es=80.0)
            | {"detected_buy_signal_latest_date": "2026-04-19", "detected_signal_latest_date": "2026-04-19"}
        )
        rows.append(
            _base_row("BOUND_FAIL", scan_score=399.0, es=80.0)
            | {"detected_buy_signal_latest_date": "2026-04-18", "detected_signal_latest_date": "2026-04-18"}
        )
        rows.append(
            _base_row("FAIL_A", scan_score=398.0, es=80.0)
            | {"ichimoku_above_cloud": False, "drawdown_from_52w_high_pct": -25.0, "adx": 10.0, "hma60_slope_pct": -0.1}
        )
        rows.append(
            _base_row("FAIL_C", scan_score=397.0, es=80.0)
            | {"cmf": 0.01, "obv_slope": 0.05, "volume_bullish": False, "volume_abnormal": True}
        )
        rows.append(_base_row("HARD_FAIL", scan_score=396.0, es=80.0) | {"thin_trade_risk": True})

        scored = _with_post_close_final_top20_scores(rows, run_at_kst=run_at_kst, scan_mode="post_close", top_n=30)
        selected = select_post_close_final_top_rows_for_telegram(scored, top_n=30)
        by_ticker = {str(row.get("ticker")): row for row in scored}

        self.assertEqual(len(selected), 30)
        self.assertEqual([int(row["final_entry_rank"]) for row in selected], list(range(1, 31)))
        self.assertTrue(bool(by_ticker["P005"]["final_entry_selected"]))
        self.assertGreaterEqual(int(by_ticker["BOUND_PASS"]["b_score"]), 3)
        self.assertFalse(bool(by_ticker["BOUND_FAIL"]["final_entry_selected"]))
        self.assertFalse(bool(by_ticker["FAIL_A"]["final_entry_selected"]))
        self.assertFalse(bool(by_ticker["FAIL_C"]["final_entry_selected"]))
        self.assertFalse(bool(by_ticker["HARD_FAIL"]["final_entry_selected"]))
        self.assertIn("HARD_FAIL:thin_trade_risk", str(by_ticker["HARD_FAIL"]["final_entry_reason"]))
        self.assertRegex(str(by_ticker["P000"]["final_entry_reason"]), r"A\d+/B\d+/C\d+")

    def test_with_post_close_final_top20_scores_uses_buy_direction_freshness(self):
        run_at_kst = datetime(2026, 4, 22, 6, 15, 0)

        base = {
            "ticker": "BASE",
            "scan_score": 190.0,
            "es": 70.0,
            "jg_key": "BUY",
            "chg_value": 1.0,
            "chg": 1.0,
            "volume_ratio_20": 1.2,
            "thin_trade_risk": False,
            "weekly_trend_context": "STRONG_UPTREND",
            "ichimoku_above_cloud": True,
            "drawdown_from_52w_high_pct": -10.0,
            "adx": 25.0,
            "hma60_slope_pct": 0.2,
            "pullback_reentry": True,
            "pocket_pivot_candidate": False,
            "gap_setup_candidate": False,
            "pullback_atr_multiple": 1.0,
            "latest_session_utbot_buy_turn": False,
            "latest_session_hull_buy_turn": False,
            "cmf": 0.10,
            "obv_slope": 0.20,
            "volume_bullish": True,
            "volume_abnormal": False,
        }
        sell_only_recent = dict(base)
        sell_only_recent["ticker"] = "SELL_ONLY"
        sell_only_recent["detected_signal_latest_date"] = "2026-04-21"
        sell_only_recent["detected_buy_signal_latest_date"] = "2026-04-18"

        buy_recent = dict(base)
        buy_recent["ticker"] = "BUY_RECENT"
        buy_recent["detected_signal_latest_date"] = "2026-04-21"
        buy_recent["detected_buy_signal_latest_date"] = "2026-04-21"

        scored = _with_post_close_final_top20_scores(
            [sell_only_recent, buy_recent],
            run_at_kst=run_at_kst,
            scan_mode="post_close",
            top_n=30,
        )
        by_ticker = {str(row.get("ticker")): row for row in scored}

        self.assertEqual(int(by_ticker["SELL_ONLY"]["b_score"]), 2)
        self.assertFalse(bool(by_ticker["SELL_ONLY"]["final_entry_selected"]))
        self.assertEqual(int(by_ticker["BUY_RECENT"]["b_score"]), 3)
        self.assertTrue(bool(by_ticker["BUY_RECENT"]["final_entry_selected"]))

    def test_select_post_close_final_top_rows_for_telegram_uses_tie_breaker_order(self):
        rows = [
            {"ticker": "AAA", "final_entry_selected": True, "final_entry_score": 90.0, "b_score": 4, "c_score": 2, "scan_score": 120.0, "es": 50.0},
            {"ticker": "BBB", "final_entry_selected": True, "final_entry_score": 90.0, "b_score": 5, "c_score": 1, "scan_score": 90.0, "es": 50.0},
            {"ticker": "CCC", "final_entry_selected": True, "final_entry_score": 90.0, "b_score": 4, "c_score": 3, "scan_score": 80.0, "es": 50.0},
            {"ticker": "DDD", "final_entry_selected": True, "final_entry_score": 90.0, "b_score": 4, "c_score": 2, "scan_score": 130.0, "es": 40.0},
            {"ticker": "EEE", "final_entry_selected": True, "final_entry_score": 90.0, "b_score": 4, "c_score": 2, "scan_score": 130.0, "es": 60.0},
        ]
        selected = select_post_close_final_top_rows_for_telegram(rows, top_n=30)
        self.assertEqual([row["ticker"] for row in selected], ["BBB", "CCC", "EEE", "DDD", "AAA"])

    def test_select_us_session_hull_bear_rows(self):
        rows = [
            {"ticker": "AAA", "scan_score": 6.0, "hull_turn_bear_last_date": "2026-04-16"},
            {"ticker": "BBB", "scan_score": 8.0, "hull_turn_bear_last_date": "2026-04-15"},
        ]
        selected = select_us_session_hull_bear_rows(rows, run_at_kst=datetime(2026, 4, 17, 6, 15, 0))
        self.assertEqual([row["ticker"] for row in selected], ["AAA"])

    def test_select_us_session_52w_high_rows(self):
        rows = [
            {"ticker": "AAA", "scan_score": 6.0, "new_52w_high": True, "latest_bar_date": "2026-04-16"},
            {"ticker": "BBB", "scan_score": 8.0, "new_52w_high": False, "latest_bar_date": "2026-04-16"},
            {"ticker": "CCC", "scan_score": 9.0, "new_52w_high": True, "latest_bar_date": "2026-04-15"},
        ]
        selected = select_us_session_52w_high_rows(rows, run_at_kst=datetime(2026, 4, 17, 6, 15, 0))
        self.assertEqual([row["ticker"] for row in selected], ["AAA"])

    def test_build_transition_summary_uses_four_ordered_sections_with_headers(self):
        summary = build_transition_summary(
            [
                {
                    "ticker": "NVDA",
                    "chg_value": 4.25,
                    "chg": 2.40,
                    "volume_ratio_20": 1.80,
                    "jg_key": "BUY",
                    "transition_signals": ["HULL 매수"],
                }
            ],
            run_at_kst=datetime(2026, 4, 17, 6, 15, 0),
            universe_count=1200,
            result_count=980,
            skip_count=220,
            detected_turn_count=4,
            summary_limit=10,
            pullback_rows=[
                {
                    "ticker": "AAPL",
                    "chg_value": 1.2,
                    "chg": 0.9,
                    "volume_ratio_20": 1.4,
                    "jg_key": "WATCH_BUY",
                }
            ],
            hull_bear_rows=[
                {
                    "ticker": "TSLA",
                    "chg_value": -3.2,
                    "chg": -1.8,
                    "volume_ratio_20": 1.3,
                    "jg_key": "SELL",
                }
            ],
            high_52w_rows=[
                {
                    "ticker": "MSFT",
                    "chg_value": 2.1,
                    "chg": 1.1,
                    "volume_ratio_20": 1.2,
                    "jg_key": "BUY",
                }
            ],
        )

        self.assertIn("요약 인덱스: 매수전환 1 | 눌림목 1 | HULL매도 1 | 52W 신고가 1", summary)
        p1 = summary.index("=== [1/4] 매수전환 ===")
        p2 = summary.index("=== [2/4] 눌림목 재진입 ===")
        p3 = summary.index("=== [3/4] 당일 HULL 매도 ===")
        p4 = summary.index("=== [4/4] 52주 신고가 갱신 ===")
        self.assertTrue(p1 < p2 < p3 < p4)
        self.assertIn("기준:", summary)
        self.assertIn("건수:", summary)

    def test_build_transition_summary_empty_section_has_placeholder(self):
        summary = build_transition_summary(
            [],
            run_at_kst=datetime(2026, 4, 17, 6, 15, 0),
            universe_count=1200,
            result_count=980,
            skip_count=220,
            detected_turn_count=0,
            summary_limit=10,
            pullback_rows=[],
            hull_bear_rows=[],
            high_52w_rows=[],
        )
        self.assertGreaterEqual(summary.count("- 해당 없음"), 4)

    def test_build_transition_summary_numbering_resets_per_section(self):
        summary = build_transition_summary(
            [
                {
                    "ticker": "AAA",
                    "chg_value": 1.0,
                    "chg": 1.0,
                    "volume_ratio_20": 1.2,
                    "jg_key": "BUY",
                    "transition_signals": ["UTBot 매수"],
                }
            ],
            run_at_kst=datetime(2026, 4, 17, 6, 15, 0),
            universe_count=100,
            result_count=80,
            skip_count=20,
            detected_turn_count=1,
            summary_limit=10,
            pullback_rows=[
                {
                    "ticker": "BBB",
                    "chg_value": 0.5,
                    "chg": 0.7,
                    "volume_ratio_20": 1.3,
                    "jg_key": "WATCH_BUY",
                }
            ],
            hull_bear_rows=[],
            high_52w_rows=[],
        )
        self.assertRegex(summary, r"=== \[1/4\] 매수전환 ===[\s\S]*\n1\. AAA")
        self.assertRegex(summary, r"=== \[2/4\] 눌림목 재진입 ===[\s\S]*\n1\. BBB")

    def test_build_transition_summary_does_not_truncate_when_summary_limit_zero(self):
        rows = [
            {
                "ticker": f"T{i:03d}",
                "chg_value": 1.0,
                "chg": 1.0,
                "volume_ratio_20": 1.5,
                "jg_key": "BUY",
                "transition_signals": ["HULL 매수"],
            }
            for i in range(45)
        ]
        summary = build_transition_summary(
            rows,
            run_at_kst=datetime(2026, 4, 16, 6, 15, 0),
            universe_count=1200,
            result_count=980,
            skip_count=220,
            detected_turn_count=45,
            summary_limit=0,
            pullback_rows=[],
            hull_bear_rows=[],
            high_52w_rows=[],
        )
        self.assertIn("45. T044", summary)
        self.assertNotIn("... 외", summary)

    def test_split_telegram_message_text_preserves_section_boundaries(self):
        base_row = {
            "ticker": "AAA",
            "chg_value": 1.0,
            "chg": 1.0,
            "volume_ratio_20": 1.5,
            "jg_key": "BUY",
            "transition_signals": ["HULL 매수"],
        }
        rows = []
        for i in range(40):
            row = dict(base_row)
            row["ticker"] = f"T{i:03d}"
            rows.append(row)

        summary = build_transition_summary(
            rows,
            run_at_kst=datetime(2026, 4, 16, 6, 15, 0),
            universe_count=1200,
            result_count=980,
            skip_count=220,
            detected_turn_count=40,
            summary_limit=0,
            pullback_rows=rows,
            hull_bear_rows=rows,
            high_52w_rows=rows,
        )
        chunks = split_telegram_message_text(summary, chunk_size=450)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 450 for chunk in chunks))

        joined = "\n".join(chunks)
        p1 = joined.index("=== [1/4] 매수전환 ===")
        p2 = joined.index("=== [2/4] 눌림목 재진입 ===")
        p3 = joined.index("=== [3/4] 당일 HULL 매도 ===")
        p4 = joined.index("=== [4/4] 52주 신고가 갱신 ===")
        self.assertTrue(p1 < p2 < p3 < p4)

    def test_build_post_close_transition_summary_uses_ten_ordered_sections(self):
        base_row = {
            "ticker": "AAA",
            "chg_value": 1.0,
            "chg": 1.0,
            "volume_ratio_20": 1.2,
            "jg_key": "BUY",
            "transition_signals": ["UTBot Buy"],
            "latest_session_utbot_buy_turn": True,
            "latest_session_hull_buy_turn": False,
            "utbot_buy_recent": True,
            "hull_turn_bull_recent": False,
        }
        gap_row = dict(base_row)
        gap_row["gap_setup_tag"] = "GAP 8/11 | G4/5 | 거래량건조, 상대강도, 밴드압축"
        pocket_row = dict(base_row)
        pocket_row["pocket_pivot_tag"] = "PP 9/12 | G4/5 | 거래량팽창, UT최근3일"
        five_day_row = dict(base_row)
        five_day_row["five_day_top_tag"] = "5일 +12.34%"
        five_day_row["chg_5d"] = 12.34
        buy_turn_filter_row = dict(base_row)
        buy_turn_filter_row["transition_signals"] = []
        buy_turn_filter_row["latest_session_utbot_buy_turn"] = False
        buy_turn_filter_row["latest_session_hull_buy_turn"] = False
        buy_turn_filter_row["utbot_buy_recent"] = True
        buy_turn_filter_row["hull_turn_bull_recent"] = True
        summary = build_post_close_transition_summary(
            [dict(base_row)],
            run_at_kst=datetime(2026, 4, 17, 6, 15, 0),
            universe_count=1200,
            result_count=980,
            skip_count=220,
            detected_turn_count=1,
            summary_limit=10,
            pullback_rows=[dict(base_row)],
            hull_bear_rows=[dict(base_row)],
            high_52w_rows=[dict(base_row)],
            pullback_filter_rows=[dict(base_row)],
            chase_filter_rows=[dict(base_row)],
            buy_turn_filter_rows=[buy_turn_filter_row],
            gap_setup_rows=[gap_row],
            pocket_pivot_rows=[pocket_row],
            five_day_top_rows=[five_day_row],
        )
        self.assertIn("대상 미국 세션일:", summary)
        self.assertIn("유니버스: 1200", summary)
        self.assertIn("스캔 결과: 980 | 제외: 220", summary)
        self.assertIn(
            "요약 인덱스: 매수전환(이전버전) 1 | 눌림 재진입(이전버전) 1 | HULL 매도전환(이전버전) 1 | 52주 신고가(이전버전) 1 | 눌림목 필터 1 | 추세추종 필터 1 | 매수전환 필터 1 | 에너지 압축 → 돌파 임박 1 | 기관 매집 포착 1 | 5일 변동률 상위종목 1",
            summary,
        )
        self.assertRegex(summary, r"1\. AAA \| \(\+1\.00, \+1\.00%\) \| [^\n]*1\.20x \| UTBOT"); self.assertRegex(summary, r"1\. AAA \| \(\+1\.00, \+1\.00%\) \| [^\n]*1\.20x \| UTBOT\+HULL"); self.assertRegex(summary, r"1\. AAA \| \(\+1\.00, \+1\.00%\) \| [^\n]*1\.20x(?:\n|$)"); self.assertNotIn(" | BUY | ", summary); self.assertNotIn("GAP 8/11", summary); self.assertNotIn("PP 9/12", summary); self.assertNotIn("12.34%", summary); p1 = summary.index("=== [1/10]")
        p2 = summary.index("=== [2/10] 눌림 재진입 (이전버전) ===")
        p3 = summary.index("=== [3/10] HULL 매도전환 (이전버전) ===")
        p4 = summary.index("=== [4/10] 52주 신고가 (이전버전) ===")
        p5 = summary.index("=== [5/10] 눌림목 필터 ===")
        p6 = summary.index("=== [6/10] 추세추종 필터 ===")
        p7 = summary.index("=== [7/10] 매수전환 필터 ===")
        p8 = summary.index("=== [8/10] 에너지 압축 → 돌파 임박 ===")
        p9 = summary.index("=== [9/10] 기관 매집 포착 ===")
        p10 = summary.index("=== [10/10] 5일 변동률 상위종목 ===")
        self.assertTrue(p1 < p2 < p3 < p4 < p5 < p6 < p7 < p8 < p9 < p10)

    def test_build_post_close_transition_summary_includes_final_top20_section_when_provided(self):
        base_row = {
            "ticker": "AAA",
            "chg_value": 1.0,
            "chg": 1.0,
            "volume_ratio_20": 1.2,
            "jg_key": "BUY",
        }
        final_row = dict(base_row)
        final_row["final_entry_reason"] = "A4/B3/C2 | PASS"
        final_row["final_entry_score"] = 97.5

        summary = build_post_close_transition_summary(
            [dict(base_row)],
            run_at_kst=datetime(2026, 4, 17, 6, 15, 0),
            universe_count=1200,
            result_count=980,
            skip_count=220,
            detected_turn_count=1,
            summary_limit=10,
            pullback_rows=[],
            hull_bear_rows=[],
            high_52w_rows=[],
            pullback_filter_rows=[],
            chase_filter_rows=[],
            buy_turn_filter_rows=[],
            gap_setup_rows=[],
            pocket_pivot_rows=[],
            five_day_top_rows=[],
            final_top_rows=[final_row],
        )

        self.assertIn("요약 인덱스:", summary)
        self.assertIn("오늘 진입 후보 Top30 1", summary)
        self.assertIn("=== [11/11] 오늘 진입 후보 Top30 (A/B/C 통과만) ===", summary)
        self.assertRegex(summary, r"1\. AAA \| \(\+1\.00, \+1\.00%\) \| [^\n]*1\.20x(?:\n|$)")
        self.assertNotIn("A4/B3/C2 | PASS", summary)
        self.assertNotIn("97.50", summary)

    def test_split_telegram_message_text_preserves_section_boundaries_for_ten_sections(self):
        base_row = {
            "ticker": "AAA",
            "chg_value": 1.0,
            "chg": 1.0,
            "volume_ratio_20": 1.5,
            "jg_key": "BUY",
            "transition_signals": ["UTBot Buy"],
        }
        rows = []
        for i in range(20):
            row = dict(base_row)
            row["ticker"] = f"S{i:03d}"
            rows.append(row)
        gap_rows = []
        pocket_rows = []
        for i, row in enumerate(rows):
            gap_row = dict(row)
            gap_row["gap_setup_tag"] = f"GAP 8/11 | G4/5 | 거래량건조{i}"
            gap_rows.append(gap_row)
            pocket_row = dict(row)
            pocket_row["pocket_pivot_tag"] = f"PP 9/12 | G4/5 | 기관매집{i}"
            pocket_rows.append(pocket_row)
        five_day_rows = []
        for i, row in enumerate(rows):
            five_day_row = dict(row)
            five_day_row["five_day_top_tag"] = f"5일 +{20.0 - (i / 10.0):.2f}%"
            five_day_row["chg_5d"] = 20.0 - (i / 10.0)
            five_day_rows.append(five_day_row)

        summary = build_post_close_transition_summary(
            rows,
            run_at_kst=datetime(2026, 4, 17, 6, 15, 0),
            universe_count=1200,
            result_count=980,
            skip_count=220,
            detected_turn_count=20,
            summary_limit=0,
            pullback_rows=rows,
            hull_bear_rows=rows,
            high_52w_rows=rows,
            pullback_filter_rows=rows,
            chase_filter_rows=rows,
            buy_turn_filter_rows=rows,
            gap_setup_rows=gap_rows,
            pocket_pivot_rows=pocket_rows,
            five_day_top_rows=five_day_rows,
        )
        chunks = split_telegram_message_text(summary, chunk_size=500)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 500 for chunk in chunks))

        joined = "\n".join(chunks)
        p1 = joined.index("=== [1/10] 매수전환 (이전버전) ===")
        p2 = joined.index("=== [2/10] 눌림 재진입 (이전버전) ===")
        p3 = joined.index("=== [3/10] HULL 매도전환 (이전버전) ===")
        p4 = joined.index("=== [4/10] 52주 신고가 (이전버전) ===")
        p5 = joined.index("=== [5/10] 눌림목 필터 ===")
        p6 = joined.index("=== [6/10] 추세추종 필터 ===")
        p7 = joined.index("=== [7/10] 매수전환 필터 ===")
        p8 = joined.index("=== [8/10] 에너지 압축 → 돌파 임박 ===")
        p9 = joined.index("=== [9/10] 기관 매집 포착 ===")
        p10 = joined.index("=== [10/10] 5일 변동률 상위종목 ===")
        self.assertTrue(p1 < p2 < p3 < p4 < p5 < p6 < p7 < p8 < p9 < p10)

    def test_split_tickers_for_shard_union_and_no_overlap(self):
        tickers = [self._alpha_symbol(i) for i in range(300)]
        shard0 = split_tickers_for_shard(tickers, shard_count=4, shard_index=0)
        shard1 = split_tickers_for_shard(tickers, shard_count=4, shard_index=1)
        shard2 = split_tickers_for_shard(tickers, shard_count=4, shard_index=2)
        shard3 = split_tickers_for_shard(tickers, shard_count=4, shard_index=3)
        self.assertEqual(set(shard0).intersection(set(shard1)), set())
        self.assertEqual(set(shard0).intersection(set(shard2)), set())
        self.assertEqual(set(shard0).intersection(set(shard3)), set())
        self.assertEqual(set(shard1).intersection(set(shard2)), set())
        self.assertEqual(set(shard1).intersection(set(shard3)), set())
        self.assertEqual(set(shard2).intersection(set(shard3)), set())
        self.assertEqual(set(shard0).union(set(shard1)).union(set(shard2)).union(set(shard3)), set(tickers))

    def test_split_tickers_for_shard_union_and_no_overlap_for_six_shards(self):
        tickers = [self._alpha_symbol(i) for i in range(420)]
        shards = [set(split_tickers_for_shard(tickers, shard_count=6, shard_index=idx)) for idx in range(6)]
        for idx in range(6):
            for jdx in range(idx + 1, 6):
                self.assertEqual(shards[idx].intersection(shards[jdx]), set())
        merged = set()
        for shard in shards:
            merged = merged.union(shard)
        self.assertEqual(merged, set(tickers))

    def test_split_tickers_for_shard_is_stable_for_six_shards(self):
        tickers = [self._alpha_symbol(i) for i in range(120)]
        first = split_tickers_for_shard(tickers, shard_count=6, shard_index=2)
        second = split_tickers_for_shard(tickers, shard_count=6, shard_index=2)
        self.assertEqual(first, second)

    def test_split_tickers_for_shard_is_stable(self):
        tickers = [self._alpha_symbol(i) for i in range(80)]
        first = split_tickers_for_shard(tickers, shard_count=4, shard_index=0)
        second = split_tickers_for_shard(tickers, shard_count=4, shard_index=0)
        self.assertEqual(first, second)

    def test_merge_shard_scan_rows_dedupes_and_sorts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            stamp = "20260422_060000"
            rows_a = [
                {"ticker": "AAA", "scan_score": 8.0, "strength": 3.0, "latest_sig_ts": 10.0, "bull_turn_recent": True},
                {"ticker": "BBB", "scan_score": 4.0, "strength": 2.0, "latest_sig_ts": 9.0, "bull_turn_recent": False},
            ]
            rows_b = [
                {"ticker": "AAA", "scan_score": 10.0, "strength": 2.0, "latest_sig_ts": 8.0, "bull_turn_recent": True},
                {"ticker": "CCC", "scan_score": 7.0, "strength": 5.0, "latest_sig_ts": 11.0, "bull_turn_recent": True},
            ]

            (root / f"scan_rows_{stamp}_shard0of2.json").write_text(json.dumps(rows_a), encoding="utf-8")
            (root / f"scan_rows_{stamp}_shard1of2.json").write_text(json.dumps(rows_b), encoding="utf-8")
            (root / f"run_meta_{stamp}_shard0of2.json").write_text(
                json.dumps(
                    {
                        "full_universe_count": 500,
                        "shard_ticker_count": 250,
                        "shard_count": 2,
                        "shard_index": 0,
                        "result_count": 2,
                        "performance": {"skip_count": 3},
                    }
                ),
                encoding="utf-8",
            )
            (root / f"run_meta_{stamp}_shard1of2.json").write_text(
                json.dumps(
                    {
                        "full_universe_count": 500,
                        "shard_ticker_count": 250,
                        "shard_count": 2,
                        "shard_index": 1,
                        "result_count": 2,
                        "performance": {"skip_count": 4},
                    }
                ),
                encoding="utf-8",
            )

            merged = merge_shard_scan_rows(root)

        merged_rows = merged["rows"]
        self.assertEqual([row["ticker"] for row in merged_rows], ["AAA", "CCC", "BBB"])
        self.assertEqual(float(merged_rows[0]["scan_score"]), 10.0)
        self.assertEqual(merged["source_row_count"], 4)
        self.assertEqual(merged["merged_row_count"], 3)
        self.assertEqual(merged["source_result_count_sum"], 4)
        self.assertEqual(merged["skip_count_sum"], 7)
        self.assertEqual(merged["universe_count"], 500)
        self.assertEqual(merged["run_stamp"], "20260422_060000")
        self.assertTrue(merged["merge_ready"])
        self.assertEqual(merged["merge_block_reason"], "")

    def test_merge_shard_scan_rows_uses_latest_stamp_and_excludes_merged_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            old_stamp = "20260421_060000"
            new_stamp = "20260422_060000"

            (root / f"scan_rows_{old_stamp}_shard0of2.json").write_text(
                json.dumps([{"ticker": "AAA", "scan_score": 999.0, "strength": 9.0, "latest_sig_ts": 20.0}]),
                encoding="utf-8",
            )
            (root / f"scan_rows_{old_stamp}_shard1of2.json").write_text(
                json.dumps([{"ticker": "OLD", "scan_score": 50.0, "strength": 5.0, "latest_sig_ts": 10.0}]),
                encoding="utf-8",
            )
            (root / f"scan_rows_{old_stamp}_merged.json").write_text(
                json.dumps([{"ticker": "MERGED", "scan_score": 1000.0, "strength": 10.0, "latest_sig_ts": 30.0}]),
                encoding="utf-8",
            )
            (root / f"scan_rows_{new_stamp}_shard0of2.json").write_text(
                json.dumps([{"ticker": "AAA", "scan_score": 10.0, "strength": 3.0, "latest_sig_ts": 5.0}]),
                encoding="utf-8",
            )
            (root / f"scan_rows_{new_stamp}_shard1of2.json").write_text(
                json.dumps([{"ticker": "BBB", "scan_score": 8.0, "strength": 2.0, "latest_sig_ts": 4.0}]),
                encoding="utf-8",
            )

            (root / f"run_meta_{old_stamp}_shard0of2.json").write_text(
                json.dumps({"shard_count": 2, "shard_index": 0, "full_universe_count": 400, "result_count": 1, "performance": {"skip_count": 8}}),
                encoding="utf-8",
            )
            (root / f"run_meta_{old_stamp}_shard1of2.json").write_text(
                json.dumps({"shard_count": 2, "shard_index": 1, "full_universe_count": 400, "result_count": 1, "performance": {"skip_count": 9}}),
                encoding="utf-8",
            )
            (root / f"run_meta_{old_stamp}_merged.json").write_text(
                json.dumps({"full_universe_count": 999, "result_count": 999, "performance": {"skip_count": 999}}),
                encoding="utf-8",
            )
            (root / f"run_meta_{new_stamp}_shard0of2.json").write_text(
                json.dumps({"shard_count": 2, "shard_index": 0, "full_universe_count": 500, "result_count": 1, "performance": {"skip_count": 2}}),
                encoding="utf-8",
            )
            (root / f"run_meta_{new_stamp}_shard1of2.json").write_text(
                json.dumps({"shard_count": 2, "shard_index": 1, "full_universe_count": 500, "result_count": 1, "performance": {"skip_count": 3}}),
                encoding="utf-8",
            )

            merged = merge_shard_scan_rows(root)

        self.assertEqual(merged["run_stamp"], new_stamp)
        self.assertEqual([row["ticker"] for row in merged["rows"]], ["AAA", "BBB"])
        self.assertEqual(float(merged["rows"][0]["scan_score"]), 10.0)
        self.assertEqual(merged["source_row_count"], 2)
        self.assertEqual(merged["source_result_count_sum"], 2)
        self.assertEqual(merged["skip_count_sum"], 5)
        self.assertEqual(merged["universe_count"], 500)
        self.assertTrue(all("_merged" not in str(path) for path in merged["row_files"]))
        self.assertTrue(all(new_stamp in str(path) for path in merged["row_files"]))
        self.assertTrue(merged["merge_ready"])
        self.assertEqual(merged["merge_block_reason"], "")

    def test_merge_shard_scan_rows_uses_required_run_stamp_for_custom_batch_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            old_stamp = "20260422_060000"
            requested_run_stamp = "123456789-2"

            (root / f"scan_rows_{old_stamp}_shard0of2.json").write_text(
                json.dumps([{"ticker": "OLD", "scan_score": 99.0, "strength": 9.0, "latest_sig_ts": 10.0}]),
                encoding="utf-8",
            )
            (root / f"run_meta_{old_stamp}_shard0of2.json").write_text(
                json.dumps({"shard_count": 2, "shard_index": 0, "full_universe_count": 100, "result_count": 1, "performance": {"skip_count": 9}}),
                encoding="utf-8",
            )
            (root / f"scan_rows_{requested_run_stamp}_shard0of2.json").write_text(
                json.dumps([{"ticker": "AAA", "scan_score": 10.0, "strength": 3.0, "latest_sig_ts": 5.0}]),
                encoding="utf-8",
            )
            (root / f"scan_rows_{requested_run_stamp}_shard1of2.json").write_text(
                json.dumps([{"ticker": "BBB", "scan_score": 8.0, "strength": 2.0, "latest_sig_ts": 4.0}]),
                encoding="utf-8",
            )
            (root / f"run_meta_{requested_run_stamp}_shard0of2.json").write_text(
                json.dumps({"shard_count": 2, "shard_index": 0, "full_universe_count": 500, "result_count": 1, "performance": {"skip_count": 2}}),
                encoding="utf-8",
            )
            (root / f"run_meta_{requested_run_stamp}_shard1of2.json").write_text(
                json.dumps({"shard_count": 2, "shard_index": 1, "full_universe_count": 500, "result_count": 1, "performance": {"skip_count": 3}}),
                encoding="utf-8",
            )

            merged = merge_shard_scan_rows(root, required_run_stamp=requested_run_stamp)

        self.assertEqual(merged["run_stamp"], requested_run_stamp)
        self.assertEqual([row["ticker"] for row in merged["rows"]], ["AAA", "BBB"])
        self.assertTrue(merged["merge_ready"])
        self.assertEqual(merged["merge_block_reason"], "")
        self.assertTrue(all(requested_run_stamp in str(path) for path in merged["row_files"]))

    def test_run_post_close_sharded_scan_skips_telegram_until_merge(self):
        args = SimpleNamespace(
            shard_count=2,
            shard_index=0,
            merge_dir="",
            universe_profile="default",
            summary_limit=0,
            max_workers=1,
            bias_mode="default",
            dry_run=False,
            skip_telegram=False,
        )
        run_at_kst = datetime(2026, 4, 22, 6, 15, 0)
        row = {
            "ticker": "AAA",
            "price": 100.0,
            "chg_value": 1.0,
            "chg": 1.0,
            "scan_score": 180.0,
            "strength": 20.0,
            "latest_sig_ts": 1.0,
            "es": 70.0,
            "volume_ratio_20": 1.2,
            "thin_trade_risk": False,
            "weekly_trend_context": "STRONG_UPTREND",
            "ichimoku_above_cloud": True,
            "drawdown_from_52w_high_pct": -10.0,
            "drawdown_from_20d_high_pct": -3.0,
            "pullback_from_swing_high_pct": -5.0,
            "pullback_atr_multiple": 1.0,
            "adx": 25.0,
            "hma20_slope_pct": 0.6,
            "hma60_slope_pct": 0.2,
            "cmf": 0.10,
            "obv_slope": 0.20,
            "volume_bullish": True,
            "volume_abnormal": False,
            "pullback_reentry": True,
            "pocket_pivot_candidate": False,
            "gap_setup_candidate": True,
            "utbot_buy_last_date": "2026-04-21",
            "hull_turn_bull_last_date": "없음",
            "utbot_sell_last_date": "없음",
            "hull_turn_bear_last_date": "없음",
            "utbot_buy_recent": True,
            "hull_turn_bull_recent": False,
            "bull_turn_recent": True,
            "detected_buy_signal_latest_date": "2026-04-21",
            "detected_signal_latest_date": "2026-04-21",
            "latest_bar_date": "2026-04-21",
            "new_52w_high": False,
        }

        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "scripts.daily_scan_and_notify.build_scan_universe",
            return_value={"tickers": ["AAA"], "sector_count": 1, "etf_count": 0, "etf_errors": []},
        ), patch(
            "scripts.daily_scan_and_notify.split_tickers_for_shard",
            return_value=["AAA"],
        ), patch(
            "scripts.daily_scan_and_notify.scan_universe",
            return_value=ScanRunResult(rows=[row], skips=[], perf={"total_seconds": 0.0}),
        ), patch("scripts.daily_scan_and_notify._send_telegram_if_enabled") as mock_send:
            out_dir = Path(temp_dir)
            result = _run_post_close(args, run_at_kst=run_at_kst, out_dir=out_dir)

            self.assertEqual(result, 0)
            mock_send.assert_not_called()

            meta_path = next(out_dir.glob("run_meta_*.json"))
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            self.assertEqual(meta["telegram_skipped_reason"], "requires_merge_for_ranked_post_close_summary")
            self.assertTrue(Path(meta["summary_path"]).exists())

    def test_compute_post_close_row_metrics_core_values(self):
        idx = pd.date_range("2026-01-01", periods=130, freq="D")
        close = pd.Series(range(1, 131), index=idx, dtype=float)
        frame = pd.DataFrame(index=idx)
        frame["Open"] = close - 0.5
        frame.loc[idx[-1], "Open"] = 133.0
        frame["Close"] = close
        frame["High"] = close + 1.0
        frame["Low"] = close - 1.0
        frame["MA20"] = close - 1.0
        frame["MA50"] = close - 2.0
        frame["MA120"] = close - 3.0
        frame["MA200"] = close - 4.0
        frame["EMA8"] = close - 0.8
        frame["EMA21"] = close - 1.1
        frame["EMA50"] = close - 1.7
        frame["HMA"] = close - 0.4
        frame["HMA60"] = close - 0.6
        frame["HMA200"] = close - 0.9
        frame["ADX"] = 25.0
        frame["Ichimoku_SenkouA"] = close - 2.0
        frame["Ichimoku_SenkouB"] = close - 3.0
        frame["Fib_Swing_High"] = close + 10.0
        frame["Percent_B"] = 0.7
        frame["ATR"] = 2.0
        frame["Volume_Ratio_20"] = 1.4
        frame["OBV_Slope"] = 0.12
        frame["CMF"] = 0.08
        frame["Volume_Climax_Buy"] = False
        frame["Volume_Climax_Sell"] = False
        frame.loc[idx[-1], "Volume_Climax_Sell"] = True
        frame["VWAP"] = close - 1.0
        frame["BB_Mid"] = close - 1.2
        frame["BB_Up"] = close + 2.0
        frame["Price_Channel_Up"] = close + 1.5
        frame["RS_Ratio"] = 1.05
        frame["UTBot_Buy"] = False
        frame["Hull_Turn_Bull"] = False
        frame["Hull_Turn_Bear"] = False
        frame["System_Turn_Bull"] = False
        frame.loc[idx[-4], "UTBot_Buy"] = True
        frame.loc[idx[-6], "Hull_Turn_Bull"] = True
        frame.loc[idx[-9], "Hull_Turn_Bear"] = True
        frame.loc[idx[-5], "System_Turn_Bull"] = True

        metrics = _compute_post_close_row_metrics(frame)

        expected_dist_sma120 = ((130.0 - 127.0) / 127.0) * 100.0
        self.assertAlmostEqual(metrics["dist_sma120_pct"], expected_dist_sma120, places=6)
        self.assertAlmostEqual(metrics["atr_pct"], (2.0 / 130.0) * 100.0, places=6)
        self.assertAlmostEqual(metrics["zscore20"], 1.647508942095828, places=5)
        self.assertTrue(metrics["gap_risk_2pct"])
        self.assertTrue(metrics["gap_risk_atr"])
        self.assertEqual(metrics["days_since_utbot_buy"], 3)
        self.assertEqual(metrics["days_since_hull_turn_bull"], 5)
        self.assertEqual(metrics["days_since_hull_turn_bear"], 8)
        self.assertEqual(metrics["system_turn_bull_last_date"], idx[-5].date().isoformat())
        self.assertTrue(metrics["volume_climax_flag"])

    def test_compute_post_close_row_metrics_accuracy_boosters(self):
        idx = pd.date_range("2026-01-01", periods=40, freq="D")
        close = pd.Series([100.0 + i * 0.5 for i in range(40)], index=idx, dtype=float)
        frame = pd.DataFrame(index=idx)
        frame["Open"] = close - 0.2
        frame["Close"] = close
        frame["High"] = close + 0.3
        frame["Low"] = close - 1.0
        frame.loc[idx[-3:], "High"] = frame.loc[idx[-3:], "Close"] + 0.1
        frame["Volume"] = [1000.0] * 30 + [400.0] * 10
        frame["MA20"] = close - 0.8
        frame["ATR"] = 2.0
        frame.loc[idx[-2], "ATR"] = 2.2
        frame.loc[idx[-1], "ATR"] = 1.8
        frame["Volume_Ratio_20"] = 0.7
        frame["OBV_Slope"] = 0.4
        frame["CMF"] = 0.09
        frame["NR7"] = False
        frame["Inside_Day"] = False
        frame["Three_Weeks_Tight"] = False
        frame["Pocket_Pivot"] = False
        frame.loc[idx[-1], ["NR7", "Inside_Day", "Three_Weeks_Tight"]] = True
        frame.loc[idx[-4], "Pocket_Pivot"] = True

        metrics = _compute_post_close_row_metrics(frame)

        self.assertTrue(metrics["atr_contracting"])
        self.assertTrue(metrics["nr7_flag"])
        self.assertTrue(metrics["inside_day_flag"])
        self.assertTrue(metrics["three_weeks_tight"])
        self.assertTrue(metrics["tight_close_near_high_3d"])
        self.assertGreater(metrics["pin_bar_ratio"], 0.0)
        self.assertTrue(metrics["near_52w_high_2pct"])
        self.assertIn(metrics["weekly_trend_context"], {"UPTREND", "STRONG_UPTREND"})
        self.assertGreater(metrics["volume_dry_up_score_10"], 0.0)
        self.assertEqual(metrics["days_since_pocket_pivot"], 3)
        self.assertTrue(metrics["pocket_pivot_recent"])

    def test_compute_post_close_row_metrics_first_close_above_ma20_after_5bars(self):
        idx = pd.date_range("2026-04-01", periods=8, freq="D")
        frame = pd.DataFrame(index=idx)
        frame["Open"] = [10, 10, 10, 10, 10, 10, 10, 12]
        frame["Close"] = [9, 9, 9, 9, 9, 9, 9, 11]
        frame["High"] = [10, 10, 10, 10, 10, 10, 10, 12]
        frame["Low"] = [8, 8, 8, 8, 8, 8, 8, 10]
        frame["MA20"] = [10] * 8
        frame["ATR"] = [1.5] * 8
        frame["Volume_Ratio_20"] = [1.0] * 8

        metrics = _compute_post_close_row_metrics(frame)
        self.assertTrue(metrics["first_close_above_ma20_after_5bars"])

    def test_compute_post_close_row_metrics_pivot2_flags(self):
        idx = pd.date_range("2026-05-01", periods=9, freq="D")
        frame_hl = pd.DataFrame(index=idx)
        frame_hl["Open"] = [10] * 9
        frame_hl["Close"] = [10] * 9
        frame_hl["High"] = [11, 12, 13, 12, 12, 12, 12, 12, 12]
        frame_hl["Low"] = [10, 9, 8, 5, 7, 8, 6, 8, 9]
        frame_hl["MA20"] = [10] * 9
        frame_hl["ATR"] = [1.0] * 9
        frame_hl["Volume_Ratio_20"] = [1.0] * 9

        frame_hh = pd.DataFrame(index=idx)
        frame_hh["Open"] = [10] * 9
        frame_hh["Close"] = [10] * 9
        frame_hh["High"] = [10, 11, 12, 9, 10, 11, 13, 12, 11]
        frame_hh["Low"] = [9, 9, 9, 9, 9, 9, 9, 9, 9]
        frame_hh["MA20"] = [10] * 9
        frame_hh["ATR"] = [1.0] * 9
        frame_hh["Volume_Ratio_20"] = [1.0] * 9

        hl_metrics = _compute_post_close_row_metrics(frame_hl)
        hh_metrics = _compute_post_close_row_metrics(frame_hh)
        self.assertTrue(hl_metrics["first_higher_low_pivot2"])
        self.assertTrue(hh_metrics["first_higher_high_pivot2"])

    def test_with_post_close_cross_section_metrics_enable_and_disable(self):
        rows = [
            {"ticker": "AAA", "rs_ratio": 0.90, "ret20_pct": 2.0, "ret60_pct": 4.0, "ret120_pct": 8.0},
            {"ticker": "BBB", "rs_ratio": 1.10, "ret20_pct": 8.0, "ret60_pct": 10.0, "ret120_pct": 15.0},
            {"ticker": "CCC", "rs_ratio": 1.00, "ret20_pct": 5.0, "ret60_pct": 6.0, "ret120_pct": 11.0},
        ]
        ranked = _with_post_close_cross_section_metrics(rows, enabled=True)
        self.assertGreater(ranked[1]["rs_rank_vs_index"], ranked[2]["rs_rank_vs_index"])
        self.assertGreater(ranked[2]["rs_rank_vs_index"], ranked[0]["rs_rank_vs_index"])
        self.assertGreater(ranked[1]["ret20_percentile"], ranked[2]["ret20_percentile"])

        disabled = _with_post_close_cross_section_metrics(rows, enabled=False)
        self.assertEqual(disabled[0]["rs_rank_vs_index"], "")
        self.assertEqual(disabled[1]["ret20_percentile"], "")


from scripts.daily_scan_and_notify import (
    _current_us_session_date,
    _resolve_target_session_date,
    _time_adjusted_volume_threshold,
    _enrich_rows_with_gap,
    _scan_label_for_mode,
    _history_period_for_mode,
    KST,
)
from datetime import date, timezone, timedelta
from zoneinfo import ZoneInfo


class ScanModeExpansionTests(unittest.TestCase):
    """21시/23시 스캔 모드 확장 테스트."""

    # --- _current_us_session_date ---

    def test_current_us_session_date_weekday(self):
        """평일 KST 23시 = ET 10시 → 오늘(ET) 반환."""
        # 2026-04-17 금요일 KST 23시 → ET 2026-04-17 10시
        kst_time = datetime(2026, 4, 17, 23, 0, 0, tzinfo=KST)
        result = _current_us_session_date(kst_time)
        self.assertEqual(result, date(2026, 4, 17))

    def test_current_us_session_date_saturday_returns_friday(self):
        """토요일 → 직전 금요일 반환."""
        kst_time = datetime(2026, 4, 18, 21, 0, 0, tzinfo=KST)  # KST 토요일 21시
        result = _current_us_session_date(kst_time)
        self.assertEqual(result.weekday(), 4)  # Friday

    def test_current_us_session_date_sunday_returns_friday(self):
        """일요일 → 직전 금요일 반환."""
        kst_time = datetime(2026, 4, 19, 21, 0, 0, tzinfo=KST)  # KST 일요일 21시
        result = _current_us_session_date(kst_time)
        self.assertEqual(result.weekday(), 4)  # Friday

    # --- _resolve_target_session_date ---

    def test_resolve_target_date_post_close_uses_last_session(self):
        kst_time = datetime(2026, 4, 17, 5, 0, 0, tzinfo=KST)
        from scripts.daily_scan_and_notify import _last_us_market_session_date
        expected = _last_us_market_session_date(kst_time)
        result = _resolve_target_session_date(kst_time, "post_close")
        self.assertEqual(result, expected)

    def test_resolve_target_date_pre_market_uses_last_session(self):
        kst_time = datetime(2026, 4, 17, 21, 0, 0, tzinfo=KST)
        from scripts.daily_scan_and_notify import _last_us_market_session_date
        expected = _last_us_market_session_date(kst_time)
        result = _resolve_target_session_date(kst_time, "pre_market")
        self.assertEqual(result, expected)

    def test_resolve_target_date_early_session_uses_current_session(self):
        kst_time = datetime(2026, 4, 17, 23, 0, 0, tzinfo=KST)
        expected = _current_us_session_date(kst_time)
        result = _resolve_target_session_date(kst_time, "early_session")
        self.assertEqual(result, expected)

    # --- _time_adjusted_volume_threshold ---

    def test_volume_threshold_before_market_open(self):
        """장 개시 전 → 0.05 (사실상 비활성화)."""
        kst_time = datetime(2026, 4, 17, 21, 0, 0, tzinfo=KST)  # ET ~08:00
        result = _time_adjusted_volume_threshold(kst_time)
        self.assertAlmostEqual(result, 0.05, places=2)

    def test_volume_threshold_30min_after_open(self):
        """장 개시 30분 후 → ~0.25."""
        kst_time = datetime(2026, 4, 17, 23, 0, 0, tzinfo=KST)  # ET ~10:00
        result = _time_adjusted_volume_threshold(kst_time)
        self.assertGreater(result, 0.10)
        self.assertLess(result, 0.60)

    def test_volume_threshold_after_close(self):
        """장 마감 후 → 1.0 (기존과 동일)."""
        kst_time = datetime(2026, 4, 18, 6, 0, 0, tzinfo=KST)  # ET ~17:00
        result = _time_adjusted_volume_threshold(kst_time)
        self.assertEqual(result, 1.0)

    def test_volume_threshold_returns_positive(self):
        """어떤 시간이든 양수 반환."""
        for hour in range(0, 24):
            kst_time = datetime(2026, 4, 17, hour, 0, 0, tzinfo=KST)
            result = _time_adjusted_volume_threshold(kst_time)
            self.assertGreater(result, 0)

    # --- _scan_label_for_mode ---

    def test_scan_label_post_close(self):
        self.assertIn("자동 스캔", _scan_label_for_mode("post_close", "default"))

    def test_scan_label_pre_market(self):
        self.assertIn("프리마켓", _scan_label_for_mode("pre_market", "default"))

    def test_scan_label_early_session(self):
        label = _scan_label_for_mode("early_session", "default")
        self.assertIn("얼리세션", label)
        self.assertIn("장중", label)

    def test_scan_label_russell2000_suffix(self):
        label = _scan_label_for_mode("early_session", "russell2000")
        self.assertIn("RUSSELL2000", label)

    # --- _history_period_for_mode ---

    def test_history_period_post_close(self):
        self.assertEqual(_history_period_for_mode("post_close"), "2y")

    def test_history_period_pre_market(self):
        self.assertEqual(_history_period_for_mode("pre_market"), "5d")

    def test_history_period_early_session(self):
        self.assertEqual(_history_period_for_mode("early_session"), "1y")

    # --- _enrich_rows_with_gap ---

    def test_enrich_rows_with_gap_injects_data(self):
        rows = [{"ticker": "AAPL", "price": 150.0}, {"ticker": "MSFT", "price": 300.0}]
        gap_data = {
            "AAPL": {"premarket_price": 155.0, "prev_close": 150.0, "gap_pct": 3.33},
        }
        enriched = _enrich_rows_with_gap(rows, gap_data)
        self.assertEqual(len(enriched), 2)
        # AAPL has gap data
        aapl = enriched[0]
        self.assertEqual(aapl["premarket_price"], 155.0)
        self.assertEqual(aapl["gap_pct"], 3.33)
        # MSFT has no gap data → defaults
        msft = enriched[1]
        self.assertEqual(msft["gap_pct"], 0.0)

    def test_enrich_rows_preserves_existing_fields(self):
        rows = [{"ticker": "TSLA", "price": 200.0, "scan_score": 5.0}]
        enriched = _enrich_rows_with_gap(rows, {})
        self.assertEqual(enriched[0]["scan_score"], 5.0)
        self.assertEqual(enriched[0]["gap_pct"], 0.0)

    # --- build_transition_summary mode headers ---

    def test_summary_header_post_close_default(self):
        kst_time = datetime(2026, 4, 17, 5, 0, 0, tzinfo=KST)
        summary = build_transition_summary(
            [], run_at_kst=kst_time, universe_count=100, result_count=50,
            skip_count=5, scan_label="자동 스캔", scan_mode="post_close",
        )
        self.assertIn("자동 스캔", summary)
        self.assertIn("전일 미국장 기준일", summary)

    def test_summary_header_pre_market(self):
        kst_time = datetime(2026, 4, 17, 21, 0, 0, tzinfo=KST)
        summary = build_transition_summary(
            [], run_at_kst=kst_time, universe_count=100, result_count=50,
            skip_count=5, scan_label="프리마켓 스캔", scan_mode="pre_market",
        )
        self.assertIn("프리마켓", summary)
        self.assertIn("오늘 본장에서 주목할 종목", summary)

    def test_summary_header_early_session(self):
        kst_time = datetime(2026, 4, 17, 23, 0, 0, tzinfo=KST)
        summary = build_transition_summary(
            [], run_at_kst=kst_time, universe_count=100, result_count=50,
            skip_count=5, scan_label="얼리세션 스캔", scan_mode="early_session",
            volume_threshold=0.25,
        )
        self.assertIn("미확정", summary)
        self.assertIn("장중 스냅샷", summary)
        self.assertIn("0.25x", summary)

    def test_summary_early_session_volume_criteria(self):
        """얼리세션 요약에 시간비례 거래량 기준이 포함되는지 확인."""
        kst_time = datetime(2026, 4, 17, 23, 0, 0, tzinfo=KST)
        summary = build_transition_summary(
            [], run_at_kst=kst_time, universe_count=100, result_count=50,
            skip_count=5, scan_mode="early_session", volume_threshold=0.30,
        )
        self.assertIn("시간비례 보정", summary)


if __name__ == "__main__":
    unittest.main()

