import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from scripts.daily_scan_and_notify import (
    build_scan_universe,
    build_transition_summary,
    merge_shard_scan_rows,
    select_recent_trend_turn_rows,
    split_tickers_for_shard,
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
        self.assertIn("1200", summary)
        self.assertIn("2", summary)
        self.assertIn("1. NVDA", summary)
        self.assertIn("2. AAPL", summary)

    def test_split_tickers_for_shard_union_and_no_overlap(self):
        tickers = [self._alpha_symbol(i) for i in range(300)]
        shard0 = split_tickers_for_shard(tickers, shard_count=3, shard_index=0)
        shard1 = split_tickers_for_shard(tickers, shard_count=3, shard_index=1)
        shard2 = split_tickers_for_shard(tickers, shard_count=3, shard_index=2)
        self.assertEqual(set(shard0).intersection(set(shard1)), set())
        self.assertEqual(set(shard0).intersection(set(shard2)), set())
        self.assertEqual(set(shard1).intersection(set(shard2)), set())
        self.assertEqual(set(shard0).union(set(shard1)).union(set(shard2)), set(tickers))

    def test_split_tickers_for_shard_is_stable(self):
        tickers = [self._alpha_symbol(i) for i in range(80)]
        first = split_tickers_for_shard(tickers, shard_count=3, shard_index=0)
        second = split_tickers_for_shard(tickers, shard_count=3, shard_index=0)
        self.assertEqual(first, second)

    def test_merge_shard_scan_rows_dedupes_and_sorts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            rows_a = [
                {"ticker": "AAA", "scan_score": 8.0, "strength": 3.0, "latest_sig_ts": 10.0, "bull_turn_recent": True},
                {"ticker": "BBB", "scan_score": 4.0, "strength": 2.0, "latest_sig_ts": 9.0, "bull_turn_recent": False},
            ]
            rows_b = [
                {"ticker": "AAA", "scan_score": 10.0, "strength": 2.0, "latest_sig_ts": 8.0, "bull_turn_recent": True},
                {"ticker": "CCC", "scan_score": 7.0, "strength": 5.0, "latest_sig_ts": 11.0, "bull_turn_recent": True},
            ]

            (root / "scan_rows_1.json").write_text(json.dumps(rows_a), encoding="utf-8")
            (root / "scan_rows_2.json").write_text(json.dumps(rows_b), encoding="utf-8")
            (root / "run_meta_1.json").write_text(
                json.dumps(
                    {
                        "full_universe_count": 500,
                        "shard_ticker_count": 250,
                        "result_count": 2,
                        "performance": {"skip_count": 3},
                    }
                ),
                encoding="utf-8",
            )
            (root / "run_meta_2.json").write_text(
                json.dumps(
                    {
                        "full_universe_count": 500,
                        "shard_ticker_count": 250,
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


if __name__ == "__main__":
    unittest.main()
