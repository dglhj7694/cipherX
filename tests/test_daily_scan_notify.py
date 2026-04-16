import unittest
from datetime import datetime
from unittest.mock import patch

from scripts.daily_scan_and_notify import (
    build_scan_universe,
    build_transition_summary,
    select_recent_trend_turn_rows,
)


class DailyScanNotifyTests(unittest.TestCase):
    def test_build_scan_universe_combines_sector_and_etf_with_dedupe(self):
        fake_sectors = {
            "A": ["AAA", "BBB", "CCC"],
            "B": ["CCC", "DDD"],
        }
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
        self.assertEqual(payload["etf_note"], "ok")

    def test_select_recent_trend_turn_rows_filters_and_sorts_by_score(self):
        rows = [
            {"ticker": "AAA", "bull_turn_recent": True, "scan_score": 3.2},
            {"ticker": "BBB", "bull_turn_recent": False, "scan_score": 9.0},
            {"ticker": "CCC", "bull_turn_recent": True, "scan_score": 7.1},
        ]
        selected = select_recent_trend_turn_rows(rows)
        self.assertEqual([row["ticker"] for row in selected], ["CCC", "AAA"])

    def test_build_transition_summary_contains_counts_and_rows(self):
        summary = build_transition_summary(
            [
                {"ticker": "NVDA", "jg_key": "BUY", "es": 10.0, "scan_score": 22.5, "latest_sig": "2026-04-16"},
                {"ticker": "AAPL", "jg_key": "WATCH_BUY", "es": 6.5, "scan_score": 15.1, "latest_sig": "2026-04-16"},
            ],
            run_at_kst=datetime(2026, 4, 16, 6, 15, 0),
            universe_count=1200,
            result_count=980,
            skip_count=220,
            summary_limit=10,
        )
        self.assertIn("유니버스: 1200개", summary)
        self.assertIn("최근 추세전환: 2개", summary)
        self.assertIn("1. NVDA", summary)
        self.assertIn("2. AAPL", summary)


if __name__ == "__main__":
    unittest.main()

