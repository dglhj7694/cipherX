import json
import re
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from scripts.daily_scan_and_notify import (
    RUSSELL2000_UNIVERSE_ITEMS,
    build_scan_universe,
    build_transition_summary,
    filter_turn_rows_for_telegram,
    merge_shard_scan_rows,
    select_pullback_reentry_rows_for_telegram,
    select_us_session_52w_high_rows,
    select_us_session_hull_bear_rows,
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
