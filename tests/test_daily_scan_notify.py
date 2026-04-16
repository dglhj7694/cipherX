import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from scripts.daily_scan_and_notify import (
    build_scan_universe,
    build_transition_summary,
    filter_turn_rows_for_telegram,
    merge_shard_scan_rows,
    select_us_session_turn_rows,
    split_telegram_message_text,
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

    def test_select_us_session_turn_rows_filters_by_previous_us_session(self):
        rows = [
            {"ticker": "AAA", "scan_score": 3.2, "utbot_buy_last_date": "2026-04-15", "hull_turn_bull_last_date": "없음"},
            {"ticker": "BBB", "scan_score": 9.0, "utbot_buy_last_date": "2026-04-14", "hull_turn_bull_last_date": "없음"},
            {"ticker": "CCC", "scan_score": 7.1, "utbot_buy_last_date": "없음", "hull_turn_bull_last_date": "2026-04-15"},
        ]
        selected = select_us_session_turn_rows(rows, run_at_kst=datetime(2026, 4, 16, 6, 15, 0))
        self.assertEqual([row["ticker"] for row in selected], ["CCC", "AAA"])
        self.assertEqual(selected[0]["transition_signals"], ["HULL 매수"])
        self.assertEqual(selected[1]["transition_signals"], ["UTBot 매수"])

    def test_filter_turn_rows_for_telegram_uses_volume_ratio_gt_one(self):
        rows = [
            {"ticker": "AAA", "scan_score": 5.0, "volume_ratio_20": 1.0},
            {"ticker": "BBB", "scan_score": 8.0, "volume_ratio_20": 1.01},
            {"ticker": "CCC", "scan_score": 4.0, "volume_ratio_20": 2.5},
        ]
        filtered = filter_turn_rows_for_telegram(rows, min_volume_ratio_20_exclusive=1.0)
        self.assertEqual([row["ticker"] for row in filtered], ["BBB", "CCC"])

    def test_build_transition_summary_contains_new_header_and_row_format(self):
        summary = build_transition_summary(
            [
                {
                    "ticker": "NVDA",
                    "chg_value": 4.25,
                    "chg": 2.4,
                    "volume_ratio_20": 1.8,
                    "jg_key": "BUY",
                    "transition_signals": ["HULL 매수"],
                },
                {
                    "ticker": "AAPL",
                    "chg_value": -1.12,
                    "chg": -0.7,
                    "volume_ratio_20": 1.4,
                    "jg_key": "WATCH_BUY",
                    "transition_signals": ["UTBot 매수"],
                },
            ],
            run_at_kst=datetime(2026, 4, 16, 6, 15, 0),
            universe_count=1200,
            result_count=980,
            skip_count=220,
            detected_turn_count=4,
            summary_limit=10,
        )
        self.assertIn("필터 기준: 전일 미국장(US/Eastern)에서 UTBot/HULL 매수 신호 발생", summary)
        self.assertIn("추가 필터: 20일 평균대비 거래량 > 1.0x", summary)
        self.assertIn("전환 감지 4개 -> 필터 통과 2개", summary)
        self.assertIn("1. NVDA | (+4.25, +2.40%) | 거래량 1.80x | BUY | HULL 매수", summary)
        self.assertNotIn("매수전환", summary)
        self.assertNotIn("| 판단", summary)
        self.assertNotIn("| 전환", summary)

    def test_build_transition_summary_does_not_truncate_when_summary_limit_is_zero(self):
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
        )
        self.assertIn("45. T044", summary)
        self.assertNotIn("... 외", summary)

    def test_split_telegram_message_text_chunks_long_message(self):
        text = "\n".join([f"line-{idx:03d}-abcdefghijklmnopqrstuvwxyz" for idx in range(120)])
        chunks = split_telegram_message_text(text, chunk_size=220)
        self.assertGreater(len(chunks), 1)
        self.assertEqual("\n".join(chunks), text)
        self.assertTrue(all(len(chunk) <= 220 for chunk in chunks))

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

    def test_split_tickers_for_shard_is_stable(self):
        tickers = [self._alpha_symbol(i) for i in range(80)]
        first = split_tickers_for_shard(tickers, shard_count=4, shard_index=0)
        second = split_tickers_for_shard(tickers, shard_count=4, shard_index=0)
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
