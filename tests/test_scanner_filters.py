import unittest
from datetime import date

from scanner_filters import (
    SCAN_FILTER_LOW_CONFLICT_BULLISH,
    SCAN_FILTER_PRESETS,
    SCAN_FILTER_PULLBACK_REENTRY,
    SCAN_FILTER_RECENT_TREND_TURN,
    SCAN_FILTER_STRONG_TREND_PERSISTENT,
    SCAN_FILTER_TODAY_UTBOT,
    SCAN_FILTER_UPTREND_PERSISTENT,
    apply_scan_filter,
    compute_scanner_profile_flags,
)


class ScannerFilterTests(unittest.TestCase):
    def _base_profile_kwargs(self):
        return {
            "current_close": 105.0,
            "ma20": 100.0,
            "ma50": 95.0,
            "ma20_prev": 99.5,
            "ma50_prev": 94.8,
            "watch_buy_plus": True,
            "strategy_bias": "LONG",
            "recent_utbot_sell": False,
            "recent_hull_bear": False,
            "adx": 24.0,
            "es": 9.5,
            "cf": 71.0,
            "volume_bullish": True,
            "strategy_conflict_level": "LOW",
            "pullback_ready": True,
            "pullback_combo_present": False,
            "long_pullback_strategy_visible": True,
            "multi_sell": 1,
            "thin_trade_risk": False,
            "flip_guard_triggered": False,
        }

    def test_new_presets_are_prioritized_after_all(self):
        self.assertEqual(
            SCAN_FILTER_PRESETS[:5],
            (
                "전체",
                "우상향 지속",
                "강한 추세 지속",
                "눌림목 재진입",
                "저충돌 강세",
            ),
        )

    def test_uptrend_persistent_positive_and_bear_turn_block(self):
        kwargs = self._base_profile_kwargs()
        flags = compute_scanner_profile_flags(**kwargs)
        self.assertTrue(flags["uptrend_persistent"])

        kwargs["recent_utbot_sell"] = True
        blocked = compute_scanner_profile_flags(**kwargs)
        self.assertFalse(blocked["uptrend_persistent"])

    def test_strong_trend_is_subset_of_uptrend(self):
        flags = compute_scanner_profile_flags(**self._base_profile_kwargs())
        self.assertTrue(flags["strong_trend_persistent"])
        self.assertTrue(flags["uptrend_persistent"])

    def test_pullback_reentry_requires_pullback_and_long_strategy(self):
        kwargs = self._base_profile_kwargs()
        kwargs["pullback_ready"] = False
        kwargs["pullback_combo_present"] = True
        kwargs["long_pullback_strategy_visible"] = True
        flags = compute_scanner_profile_flags(**kwargs)
        self.assertTrue(flags["pullback_reentry"])

        kwargs["long_pullback_strategy_visible"] = False
        blocked = compute_scanner_profile_flags(**kwargs)
        self.assertFalse(blocked["pullback_reentry"])

    def test_low_conflict_bullish_blocks_flip_guard(self):
        kwargs = self._base_profile_kwargs()
        flags = compute_scanner_profile_flags(**kwargs)
        self.assertTrue(flags["low_conflict_bullish"])

        kwargs["flip_guard_triggered"] = True
        blocked = compute_scanner_profile_flags(**kwargs)
        self.assertFalse(blocked["low_conflict_bullish"])

    def test_apply_filter_for_new_presets(self):
        rows = [
            {
                "ticker": "AAA",
                "uptrend_persistent": True,
                "strong_trend_persistent": True,
                "pullback_reentry": False,
                "low_conflict_bullish": True,
            },
            {
                "ticker": "BBB",
                "uptrend_persistent": True,
                "strong_trend_persistent": False,
                "pullback_reentry": True,
                "low_conflict_bullish": False,
            },
        ]

        self.assertEqual(
            [row["ticker"] for row in apply_scan_filter(rows, SCAN_FILTER_UPTREND_PERSISTENT)],
            ["AAA", "BBB"],
        )
        self.assertEqual(
            [row["ticker"] for row in apply_scan_filter(rows, SCAN_FILTER_STRONG_TREND_PERSISTENT)],
            ["AAA"],
        )
        self.assertEqual(
            [row["ticker"] for row in apply_scan_filter(rows, SCAN_FILTER_PULLBACK_REENTRY)],
            ["BBB"],
        )
        self.assertEqual(
            [row["ticker"] for row in apply_scan_filter(rows, SCAN_FILTER_LOW_CONFLICT_BULLISH)],
            ["AAA"],
        )

    def test_existing_transition_and_recent_turn_filters_still_work(self):
        rows = [
            {
                "ticker": "AAA",
                "bull_turn_recent": True,
                "utbot_buy_last_date": "2026-04-15",
                "utbot_sell_last_date": "없음",
                "transitions": [],
            },
            {
                "ticker": "BBB",
                "bull_turn_recent": False,
                "utbot_buy_last_date": "없음",
                "utbot_sell_last_date": "없음",
                "transitions": [],
            },
        ]

        recent_turn = apply_scan_filter(rows, SCAN_FILTER_RECENT_TREND_TURN)
        self.assertEqual([row["ticker"] for row in recent_turn], ["AAA"])

        today_transition = apply_scan_filter(rows, SCAN_FILTER_TODAY_UTBOT, today=date(2026, 4, 15))
        self.assertEqual([row["ticker"] for row in today_transition], ["AAA"])


if __name__ == "__main__":
    unittest.main()
