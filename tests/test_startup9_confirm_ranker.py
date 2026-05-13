from __future__ import annotations

import unittest
from datetime import date

from telegram_pipeline.startup9_confirm_ranker import (
    ABOVE_GOLD_ZONE_KEY,
    BLUE_DIAMOND_ENTRY_KEY,
    BULLISH_REVERSAL_KEY,
    MARKET_STRUCTURE_BULLISH_KEY,
    NO_PINK_DIAMOND_KEY,
    SMART_MONEY_FLOW_KEY,
    SUPPORT_HOLD_KEY,
    evaluate_startup9_confirm,
    annotate_rows_with_startup9_confirm,
    rank_startup9_confirm_candidates,
    select_startup9_confirm_rows,
)


TARGET_DATE = date(2026, 5, 12)


def _row(ticker: str = "S9A", **overrides):
    row = {
        "ticker": ticker,
        "price": 100.0,
        "ma20_dist_pct": 3.0,
        "percent_b": 0.62,
        "uptrend_persistent": True,
        "first_higher_low_pivot2": True,
        "pullback_reentry": True,
        "cmf": 0.12,
        "volume_ratio_20": 1.7,
        "adx": 26.0,
        "rs_rank_vs_index": 74.0,
        "dollar_volume_20": 100_000_000.0,
        "detected_signals": [
            {"key": "UTBot_Buy", "date": TARGET_DATE.isoformat()},
            {"key": "Pocket_Pivot", "date": TARGET_DATE.isoformat()},
            {"key": "Bull_Divergence", "date": TARGET_DATE.isoformat()},
            {"key": "Squeeze_Fire_Buy", "date": TARGET_DATE.isoformat()},
        ],
    }
    row.update(overrides)
    return row


def _six_axis_row(ticker: str = "S9B", **overrides):
    row = _row(
        ticker,
        first_higher_low_pivot2=False,
        pullback_reentry=False,
        detected_signals=[
            {"key": "UTBot_Buy", "date": TARGET_DATE.isoformat()},
            {"key": "Pocket_Pivot", "date": TARGET_DATE.isoformat()},
            {"key": "Squeeze_Fire_Buy", "date": TARGET_DATE.isoformat()},
        ],
    )
    row.update(overrides)
    return row


class Startup9ConfirmRankerTests(unittest.TestCase):
    def test_all_nine_axes_full_bull(self):
        result = evaluate_startup9_confirm(_row(), TARGET_DATE)

        self.assertEqual(result.confirm_count, 9)
        self.assertEqual(result.grade, "FULL_BULL")

    def test_same_axis_multiple_signals_count_once(self):
        row = _row(
            detected_signals=[
                {"key": "UTBot_Buy", "date": TARGET_DATE.isoformat()},
                {"key": "Hull_Turn_Bull", "date": TARGET_DATE.isoformat()},
                {"key": "CS_Triple_Confirm_Buy", "date": TARGET_DATE.isoformat()},
                {"key": "Pocket_Pivot", "date": TARGET_DATE.isoformat()},
                {"key": "CMF_Bull", "date": TARGET_DATE.isoformat()},
                {"key": "Bull_Divergence", "date": TARGET_DATE.isoformat()},
                {"key": "Squeeze_Fire_Buy", "date": TARGET_DATE.isoformat()},
            ]
        )

        result = evaluate_startup9_confirm(row, TARGET_DATE)

        self.assertEqual(result.confirm_count, 9)
        self.assertTrue(result.confirm_map[BLUE_DIAMOND_ENTRY_KEY])
        self.assertEqual(result.confirm_keys.count(BLUE_DIAMOND_ENTRY_KEY), 1)

    def test_six_axes_strong_bull_and_rank_included(self):
        row = _six_axis_row()

        result = evaluate_startup9_confirm(row, TARGET_DATE)
        ranked = rank_startup9_confirm_candidates([row], TARGET_DATE)

        self.assertEqual(result.confirm_count, 6)
        self.assertEqual(result.grade, "STRONG_BULL")
        self.assertEqual([item.ticker for item in ranked], ["S9B"])

    def test_four_axes_watch_bull_excluded_from_top20(self):
        row = _row(
            "S9C",
            detected_signals=[],
            first_higher_low_pivot2=False,
            pullback_reentry=False,
            cmf=0.0,
            volume_ratio_20=1.0,
            percent_b=None,
        )

        result = evaluate_startup9_confirm(row, TARGET_DATE)
        ranked = rank_startup9_confirm_candidates([row], TARGET_DATE)

        self.assertEqual(result.confirm_count, 4)
        self.assertEqual(result.grade, "WATCH_BULL")
        self.assertEqual(ranked, [])

    def test_bear_active_no_pink_missing_and_rank_excluded(self):
        row = _six_axis_row(
            "S9D",
            detected_signals=[
                {"key": "UTBot_Buy", "date": "2026-05-10"},
                {"key": "Pocket_Pivot", "date": TARGET_DATE.isoformat()},
                {"key": "Squeeze_Fire_Buy", "date": TARGET_DATE.isoformat()},
                {"key": "UTBot_Sell", "date": TARGET_DATE.isoformat()},
            ],
        )

        result = evaluate_startup9_confirm(row, TARGET_DATE)
        ranked = rank_startup9_confirm_candidates([row], TARGET_DATE)

        self.assertEqual(result.direction_state, "BEAR_ACTIVE")
        self.assertFalse(result.confirm_map[NO_PINK_DIAMOND_KEY])
        self.assertIn("No Pink Diamond", result.missing)
        self.assertIn("recent_sell_turn", result.hard_exclusions)
        self.assertEqual(ranked, [])

    def test_mixed_same_day_no_pink_missing_and_rank_excluded(self):
        row = _six_axis_row(
            "S9E",
            detected_signals=[
                {"key": "UTBot_Buy", "date": TARGET_DATE.isoformat()},
                {"key": "UTBot_Sell", "date": TARGET_DATE.isoformat()},
                {"key": "Pocket_Pivot", "date": TARGET_DATE.isoformat()},
                {"key": "Squeeze_Fire_Buy", "date": TARGET_DATE.isoformat()},
            ],
        )

        result = evaluate_startup9_confirm(row, TARGET_DATE)
        ranked = rank_startup9_confirm_candidates([row], TARGET_DATE)

        self.assertEqual(result.direction_state, "MIXED_SAME_DAY")
        self.assertFalse(result.confirm_map[NO_PINK_DIAMOND_KEY])
        self.assertIn("direction_conflict", result.hard_exclusions)
        self.assertEqual(ranked, [])

    def test_sell_then_newer_buy_is_reclaimed_and_rankable(self):
        row = _six_axis_row(
            "S9F",
            detected_signals=[
                {"key": "UTBot_Sell", "date": "2026-05-09"},
                {"key": "UTBot_Buy", "date": TARGET_DATE.isoformat()},
                {"key": "Pocket_Pivot", "date": TARGET_DATE.isoformat()},
                {"key": "Squeeze_Fire_Buy", "date": TARGET_DATE.isoformat()},
            ],
        )

        result = evaluate_startup9_confirm(row, TARGET_DATE)
        ranked = rank_startup9_confirm_candidates([row], TARGET_DATE)

        self.assertEqual(result.direction_state, "BULL_RECLAIMED")
        self.assertTrue(result.confirm_map[NO_PINK_DIAMOND_KEY])
        self.assertIn("sell_signal_recovered", result.soft_risk_flags)
        self.assertEqual([item.ticker for item in ranked], ["S9F"])

    def test_same_day_timestamp_resolves_latest_direction(self):
        row = _six_axis_row(
            "S9T",
            detected_signals=[
                {"key": "UTBot_Sell", "timestamp": "2026-05-12T10:15:00-04:00"},
                {"key": "UTBot_Buy", "timestamp": "2026-05-12T15:45:00-04:00"},
                {"key": "Pocket_Pivot", "date": TARGET_DATE.isoformat()},
                {"key": "Squeeze_Fire_Buy", "date": TARGET_DATE.isoformat()},
            ],
        )

        result = evaluate_startup9_confirm(row, TARGET_DATE)
        ranked = rank_startup9_confirm_candidates([row], TARGET_DATE)

        self.assertEqual(result.direction_state, "BULL_RECLAIMED")
        self.assertTrue(result.confirm_map[NO_PINK_DIAMOND_KEY])
        self.assertEqual([item.ticker for item in ranked], ["S9T"])

    def test_low_dollar_volume_is_visible_risk_and_top20_exclusion(self):
        row = _row("S9G", dollar_volume_20=1_000_000.0)

        result = evaluate_startup9_confirm(row, TARGET_DATE)
        ranked = rank_startup9_confirm_candidates([row], TARGET_DATE)

        self.assertIn("low_dollar_volume", result.risk_flags)
        self.assertIn("low_dollar_volume", result.hard_exclusions)
        self.assertEqual(ranked, [])

    def test_above_gold_zone_percent_b_missing_does_not_fail(self):
        row = _row("S9H", percent_b=None, bb_percent_b=None)

        result = evaluate_startup9_confirm(row, TARGET_DATE)

        self.assertTrue(result.confirm_map[ABOVE_GOLD_ZONE_KEY])

    def test_smart_money_requires_strong_or_two_weak(self):
        weak_one = _row(
            "S9I",
            cmf=0.05,
            obv_slope=0.0,
            volume_ratio_20=1.0,
            detected_signals=[{"key": "UTBot_Buy", "date": TARGET_DATE.isoformat()}],
        )
        weak_two = dict(weak_one, obv_slope=0.05)
        strong_one = dict(weak_one, cmf=0.11)

        self.assertFalse(evaluate_startup9_confirm(weak_one, TARGET_DATE).confirm_map[SMART_MONEY_FLOW_KEY])
        self.assertTrue(evaluate_startup9_confirm(weak_two, TARGET_DATE).confirm_map[SMART_MONEY_FLOW_KEY])
        self.assertTrue(evaluate_startup9_confirm(strong_one, TARGET_DATE).confirm_map[SMART_MONEY_FLOW_KEY])

    def test_annotation_adds_csv_and_json_helper_fields(self):
        annotated = annotate_rows_with_startup9_confirm([_row("S9J"), _six_axis_row("S9K")], TARGET_DATE)

        for row in annotated:
            for key in (
                "startup9_confirm_count",
                "startup9_confirm_grade",
                "startup9_confirm_hits",
                "startup9_confirm_missing",
                "startup9_confirm_reason",
                "startup9_risk_flags",
                "startup9_score",
                "startup9_confirm_map",
                "startup9_confirm_keys",
                "startup9_missing_keys",
                "startup9_profile",
                "startup9_direction_state",
                "startup9_hard_exclusions",
                "startup9_soft_risk_flags",
            ):
                self.assertIn(key, row)

    def test_select_rows_adds_rank_and_sorts_by_confirm_count(self):
        rows = [_six_axis_row("SIX"), _row("NINE")]

        selected = select_startup9_confirm_rows(rows, TARGET_DATE)

        self.assertEqual([row["ticker"] for row in selected[:2]], ["NINE", "SIX"])
        self.assertEqual(selected[0]["startup9_confirm_count"], 9)
        self.assertEqual(selected[0]["startup9_rank"], 1)
        self.assertEqual(selected[1]["startup9_rank"], 2)

    def test_market_structure_and_support_are_separate_axes(self):
        structure_only = _six_axis_row("S9L", first_higher_low_pivot2=True, pullback_reentry=False)
        support_only = _six_axis_row("S9M", first_higher_low_pivot2=False, pullback_reentry=True)

        structure_result = evaluate_startup9_confirm(structure_only, TARGET_DATE)
        support_result = evaluate_startup9_confirm(support_only, TARGET_DATE)

        self.assertTrue(structure_result.confirm_map[MARKET_STRUCTURE_BULLISH_KEY])
        self.assertFalse(structure_result.confirm_map[SUPPORT_HOLD_KEY])
        self.assertFalse(support_result.confirm_map[MARKET_STRUCTURE_BULLISH_KEY])
        self.assertTrue(support_result.confirm_map[SUPPORT_HOLD_KEY])
        self.assertFalse(support_result.confirm_map[BULLISH_REVERSAL_KEY])


if __name__ == "__main__":
    unittest.main()
