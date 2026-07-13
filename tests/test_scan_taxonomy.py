import unittest
from datetime import date

from telegram_pipeline.scan_taxonomy import (
    SCAN_TAXONOMY_KEYS,
    SCAN_TAXONOMY_TABS,
    annotate_rows_with_scan_taxonomy,
)


class ScanTaxonomyTests(unittest.TestCase):
    def setUp(self):
        self.target_date = date(2026, 4, 23)

    def _row(self, ticker="TST", **overrides):
        row = {
            "ticker": ticker,
            "scan_status": "ok",
            "price": 100.0,
            "chg": 1.2,
            "chg_5d": 4.0,
            "volume_ratio_20": 1.1,
            "dollar_volume_20": 50_000_000,
            "multi_buy": 1,
            "multi_sell": 0,
            "thin_trade_risk": False,
            "bearish_gap_failure": False,
            "strategy_conflict_level": "LOW",
            "detected_signals": [],
        }
        row.update(overrides)
        return row

    def _annotated(self, row):
        return annotate_rows_with_scan_taxonomy([row], target_date=self.target_date)[0]

    def test_representative_rows_match_all_13_tabs(self):
        cases = {
            "buy_turn": self._row(volume_ratio_20=1.6, utbot_buy_last_date=self.target_date.isoformat()),
            "rise_ready": self._row(uptrend_persistent=True, nr7_flag=True, atr_contracting=True),
            "trend_continue": self._row(strong_trend_persistent=True, adx=26, rs_rank_vs_index=82),
            "buy_now": self._row(
                uptrend_persistent=True,
                pullback_ready=True,
                volume_ratio_20=1.7,
                detected_signals=[{"key": "Hammer", "dir": "buy"}],
                utbot_buy_last_date=self.target_date.isoformat(),
            ),
            "pullback": self._row(uptrend_persistent=True, pullback_ready=True, drawdown_from_20d_high_pct=-4.0),
            "pre_breakout": self._row(
                uptrend_persistent=True,
                gap_setup_candidate=True,
                near_52w_high_2pct=True,
                volume_dry_up_score=35,
            ),
            "breakout_confirm": self._row(new_52w_high=True, volume_ratio_20=1.7),
            "accumulation": self._row(
                uptrend_persistent=True,
                pocket_pivot_candidate=True,
                volume_ratio_20=1.5,
                cmf=0.12,
                obv_slope=0.4,
            ),
            "rebreakout": self._row(
                volume_ratio_20=1.6,
                utbot_buy_last_date=self.target_date.isoformat(),
                utbot_sell_recent=True,
            ),
            "gap_and_go": self._row(session_gap_pct=2.8, chg=3.4, volume_ratio_20=1.9),
            "speculative_satellite": self._row(chg_5d=22.0, volume_ratio_20=1.8, atr_pct=7.0),
            "wait": self._row(volume_ratio_20=0.7),
            "avoid": self._row(thin_trade_risk=True),
        }

        for tab_key, row in cases.items():
            with self.subTest(tab=tab_key):
                annotated = self._annotated(row)
                self.assertEqual(annotated[f"scan_tab_{tab_key}"], "Y")

        self.assertEqual(sorted(SCAN_TAXONOMY_KEYS), sorted(tab.key for tab in SCAN_TAXONOMY_TABS))

    def test_single_row_can_match_multiple_tabs(self):
        row = self._annotated(
            self._row(
                uptrend_persistent=True,
                pullback_ready=True,
                pocket_pivot_candidate=True,
                cmf=0.16,
                obv_slope=0.5,
                volume_ratio_20=1.8,
                utbot_buy_last_date=self.target_date.isoformat(),
                detected_signals=[{"key": "Hammer", "dir": "buy"}, {"key": "MA20_Support", "dir": "buy"}],
            )
        )

        self.assertEqual(row["scan_action_label"], "STRONG_BUY_NOW")
        self.assertEqual(row["scan_tab_buy_now"], "Y")
        self.assertEqual(row["scan_tab_pullback"], "Y")
        self.assertEqual(row["scan_tab_accumulation"], "Y")
        self.assertIn("buy_now", row["scan_taxonomy_matches"])

    def test_avoid_overrides_primary_label(self):
        row = self._annotated(
            self._row(new_52w_high=True, volume_ratio_20=2.0, thin_trade_risk=True)
        )

        self.assertEqual(row["scan_action_label"], "AVOID")
        self.assertEqual(row["scan_taxonomy_primary"], "avoid")
        self.assertEqual(row["scan_tab_avoid"], "Y")
        self.assertEqual(row["scan_tab_breakout_confirm"], "N")

    def test_skipped_rows_are_not_classified(self):
        row = self._annotated(self._row(scan_status="skipped", scan_skip_reason="missing_frame"))

        self.assertEqual(row["scan_action_label"], "")
        self.assertEqual(row["scan_taxonomy_matches"], "")
        for tab in SCAN_TAXONOMY_TABS:
            self.assertEqual(row[tab.csv_key], "N")


if __name__ == "__main__":
    unittest.main()
