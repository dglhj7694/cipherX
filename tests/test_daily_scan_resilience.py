import argparse
import json
import re
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from scripts.daily_scan_and_notify import (
    KST,
    _run_early_session,
    _run_post_close,
    _run_pre_market,
    merge_shard_scan_rows,
    split_tickers_for_shard,
)


class DailyScanResilienceTests(unittest.TestCase):
    @staticmethod
    def _base_args(**overrides):
        data = {
            "out_dir": "artifacts/tmp",
            "max_workers": 2,
            "summary_limit": 0,
            "bias_mode": "default",
            "skip_telegram": True,
            "dry_run": False,
            "shard_count": 2,
            "shard_index": 0,
            "merge_dir": "",
            "run_stamp": "",
            "universe_profile": "default",
            "scan_mode": "post_close",
            "prev_scan_dir": "",
        }
        data.update(overrides)
        return argparse.Namespace(**data)

    def test_merge_shard_scan_rows_reports_missing_indices_and_priority_modes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "scan_rows_20260420_010101_shard0of8.json").write_text(
                json.dumps([{"ticker": "AAA", "scan_score": 2.0}]),
                encoding="utf-8",
            )
            (root / "scan_rows_20260420_010101_shard2of8.json").write_text(
                json.dumps([{"ticker": "BBB", "scan_score": 1.0}]),
                encoding="utf-8",
            )
            (root / "run_meta_20260420_010101_shard0of8.json").write_text(
                json.dumps(
                    {
                        "mode": "scan",
                        "shard_count": 8,
                        "shard_index": 0,
                        "result_count": 1,
                        "performance": {"skip_count": 0},
                        "priority_mode": "from_prev_scan",
                    }
                ),
                encoding="utf-8",
            )
            (root / "run_meta_20260420_010101_shard2of8.json").write_text(
                json.dumps(
                    {
                        "mode": "scan",
                        "shard_count": 8,
                        "shard_index": 2,
                        "result_count": 1,
                        "performance": {"skip_count": 1},
                        "priority_mode": "empty_fallback",
                    }
                ),
                encoding="utf-8",
            )

            merged = merge_shard_scan_rows(root)

        self.assertEqual(merged["expected_shard_count"], 8)
        self.assertEqual(merged["found_shard_count"], 2)
        self.assertEqual(merged["found_shard_indices"], [0, 2])
        self.assertEqual(merged["missing_shard_indices"], [1, 3, 4, 5, 6, 7])
        self.assertFalse(merged["merge_ready"])
        self.assertEqual(merged["merge_block_reason"], "incomplete_shards")
        self.assertEqual(set(merged["priority_modes"]), {"from_prev_scan", "empty_fallback"})

    def test_run_post_close_merge_blocks_incomplete_shards(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            merge_dir = root / "merge_inputs"
            out_dir = root / "final"
            merge_dir.mkdir(parents=True, exist_ok=True)
            run_stamp = "batch-42"

            rows_a = [{"ticker": "AAA", "scan_score": 3.0, "es": 1.0, "volume_ratio_20": 1.2}]
            rows_b = [{"ticker": "BBB", "scan_score": 2.0, "es": 0.5, "volume_ratio_20": 1.3}]
            (merge_dir / f"scan_rows_{run_stamp}_shard0of3.json").write_text(json.dumps(rows_a), encoding="utf-8")
            (merge_dir / f"scan_rows_{run_stamp}_shard2of3.json").write_text(json.dumps(rows_b), encoding="utf-8")
            (merge_dir / f"run_meta_{run_stamp}_shard0of3.json").write_text(
                json.dumps({"mode": "scan", "shard_count": 3, "shard_index": 0, "result_count": 1, "performance": {"skip_count": 0}}),
                encoding="utf-8",
            )
            (merge_dir / f"run_meta_{run_stamp}_shard2of3.json").write_text(
                json.dumps({"mode": "scan", "shard_count": 3, "shard_index": 2, "result_count": 1, "performance": {"skip_count": 0}}),
                encoding="utf-8",
            )

            args = self._base_args(merge_dir=str(merge_dir), shard_count=3, shard_index=0, run_stamp=run_stamp)
            with patch("scripts.daily_scan_and_notify._send_telegram_if_enabled") as mock_send:
                result = _run_post_close(
                    args,
                    run_at_kst=datetime(2026, 4, 20, 5, 0, 0, tzinfo=KST),
                    out_dir=out_dir,
                )

            self.assertEqual(result, 1)
            mock_send.assert_not_called()
            summary_file = next(out_dir.glob(f"trend_turn_summary_{run_stamp}_merged.txt"))
            self.assertTrue(summary_file.exists())
            meta_file = next(out_dir.glob(f"run_meta_{run_stamp}_merged.json"))
            meta = json.loads(meta_file.read_text(encoding="utf-8")); self.assertEqual(meta["run_stamp"], run_stamp); self.assertFalse(meta["merge_ready"]); self.assertEqual(meta["merge_block_reason"], "incomplete_shards"); self.assertEqual(meta["found_shard_count"], 2); self.assertEqual(meta["expected_shard_count"], 3); self.assertEqual(meta["missing_shard_indices"], [1]); self.assertEqual(meta["telegram_skipped_reason"], "incomplete_shards")

    def test_run_early_session_merge_blocks_incomplete_shards(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            merge_dir = root / "merge_inputs"
            out_dir = root / "final"
            merge_dir.mkdir(parents=True, exist_ok=True)
            run_stamp = "batch-es-7"

            rows_a = [{"ticker": "AAA", "scan_score": 3.0, "es": 1.0, "volume_ratio_20": 0.8}]
            rows_b = [{"ticker": "BBB", "scan_score": 2.0, "es": 0.5, "volume_ratio_20": 0.9}]
            (merge_dir / f"scan_rows_{run_stamp}_early_session_shard0of3.json").write_text(json.dumps(rows_a), encoding="utf-8")
            (merge_dir / f"scan_rows_{run_stamp}_early_session_shard2of3.json").write_text(json.dumps(rows_b), encoding="utf-8")
            (merge_dir / f"run_meta_{run_stamp}_early_session_shard0of3.json").write_text(
                json.dumps({"mode": "scan", "scan_mode": "early_session", "shard_count": 3, "shard_index": 0, "result_count": 1, "performance": {"skip_count": 0}}),
                encoding="utf-8",
            )
            (merge_dir / f"run_meta_{run_stamp}_early_session_shard2of3.json").write_text(
                json.dumps({"mode": "scan", "scan_mode": "early_session", "shard_count": 3, "shard_index": 2, "result_count": 1, "performance": {"skip_count": 0}}),
                encoding="utf-8",
            )

            args = self._base_args(scan_mode="early_session", merge_dir=str(merge_dir), shard_count=3, shard_index=0, run_stamp=run_stamp)
            with patch("scripts.daily_scan_and_notify._send_telegram_if_enabled") as mock_send, patch(
                "scripts.daily_scan_and_notify._fetch_tv_market_caps",
                return_value={},
            ):
                result = _run_early_session(
                    args,
                    run_at_kst=datetime(2026, 4, 20, 23, 10, 0, tzinfo=KST),
                    out_dir=out_dir,
                )

            self.assertEqual(result, 1)
            mock_send.assert_not_called()
            summary_file = next(out_dir.glob(f"trend_turn_summary_{run_stamp}_early_session_merged.txt"))
            self.assertTrue(summary_file.exists())
            meta_file = next(out_dir.glob(f"run_meta_{run_stamp}_early_session_merged.json"))
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            self.assertEqual(meta["run_stamp"], run_stamp)
            self.assertFalse(meta["merge_ready"])
            self.assertEqual(meta["merge_block_reason"], "incomplete_shards")
            self.assertEqual(meta["found_shard_count"], 2)
            self.assertEqual(meta["expected_shard_count"], 3)
            self.assertEqual(meta["missing_shard_indices"], [1])
            self.assertEqual(meta["telegram_skipped_reason"], "incomplete_shards")

    def test_run_pre_market_fallback_without_previous_artifacts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            out_dir = root / "out"
            prev_dir = root / "prev"
            prev_dir.mkdir(parents=True, exist_ok=True)

            universe_tickers = ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF", "GGG", "HHH"]
            shard0 = split_tickers_for_shard(universe_tickers, 2, 0)
            shard1 = split_tickers_for_shard(universe_tickers, 2, 1)
            shard_index = 0 if len(shard0) >= len(shard1) else 1
            expected_tickers = shard0 if shard_index == 0 else shard1

            args = self._base_args(
                scan_mode="pre_market",
                prev_scan_dir=str(prev_dir),
                shard_count=2,
                shard_index=shard_index,
            )
            fake_universe = {
                "tickers": universe_tickers,
                "universe_profile": "default",
            }
            gap_ticker = expected_tickers[0]
            fake_gaps = {gap_ticker: {"premarket_price": 11.0, "prev_close": 10.0, "gap_pct": 10.0}}

            with patch("scripts.daily_scan_and_notify.build_scan_universe", return_value=fake_universe), patch(
                "scripts.daily_scan_and_notify._fetch_premarket_gaps",
                return_value=fake_gaps,
            ):
                result = _run_pre_market(
                    args,
                    run_at_kst=datetime(2026, 4, 20, 21, 0, 0, tzinfo=KST),
                    out_dir=out_dir,
                )

            self.assertEqual(result, 0)
            meta_file = next(out_dir.glob(f"run_meta_*_pre_market_shard{shard_index}of2.json"))
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            self.assertEqual(meta["priority_mode"], "empty_fallback")
            self.assertFalse(meta["prev_scan_found"])
            self.assertEqual(meta["fallback_reason"], "missing_prev_scan_artifact")

            rows_file = next(out_dir.glob(f"scan_rows_*_pre_market_shard{shard_index}of2.json"))
            rows = json.loads(rows_file.read_text(encoding="utf-8"))
            self.assertEqual(sorted(row["ticker"] for row in rows), sorted(expected_tickers))
            self.assertTrue(all(row.get("scan_source") == "pre_market_fallback" for row in rows))

    def test_run_pre_market_uses_prev_scan_priority_mode(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            out_dir = root / "out"
            prev_dir = root / "prev"
            prev_dir.mkdir(parents=True, exist_ok=True)
            prev_rows = [
                {"ticker": "AAA", "price": 10.0, "scan_score": 1.2},
                {"ticker": "BBB", "price": 20.0, "scan_score": 0.9},
                {"ticker": "CCC", "price": 30.0, "scan_score": 0.5},
            ]
            (prev_dir / "scan_rows_20260420_pre_market_merged.json").write_text(json.dumps(prev_rows), encoding="utf-8")

            args = self._base_args(
                scan_mode="pre_market",
                prev_scan_dir=str(prev_dir),
                shard_count=2,
                shard_index=0,
            )
            with patch("scripts.daily_scan_and_notify._fetch_premarket_gaps", return_value={}):
                result = _run_pre_market(
                    args,
                    run_at_kst=datetime(2026, 4, 20, 21, 0, 0, tzinfo=KST),
                    out_dir=out_dir,
                )

            self.assertEqual(result, 0)
            meta_file = next(out_dir.glob("run_meta_*_pre_market_shard0of2.json"))
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            self.assertEqual(meta["priority_mode"], "from_prev_scan")
            self.assertTrue(meta["prev_scan_found"])
            self.assertEqual(meta["fallback_reason"], "")

    def test_daily_scan_workflow_schedule_guard_and_shards(self):
        workflow_text = Path(".github/workflows/daily_scan_notify.yml").read_text(encoding="utf-8")
        self.assertNotIn('cron: "5 20,21 * * 1-5"', workflow_text)
        self.assertGreaterEqual(workflow_text.count("shard_index: [0, 1, 2, 3, 4, 5, 6, 7]"), 2)
        self.assertGreaterEqual(workflow_text.count("--shard-count 8"), 2)
        self.assertGreaterEqual(workflow_text.count('--run-stamp "$RUN_STAMP"'), 4)
        self.assertGreaterEqual(workflow_text.count("RUN_STAMP: ${{ github.run_id }}-${{ github.run_attempt }}"), 4)

        self.assertRegex(
            workflow_text,
            r"merge_and_notify:\s+name:\s+merge-and-notify[\s\S]*?needs:\s+[\s\S]*?-\s+scan_shard\s+if:\s+\$\{\{\s*always\(\)\s*&&",
        )
        self.assertRegex(
            workflow_text,
            r"extended_merge_and_notify:\s+name:\s+extended-merge-and-notify[\s\S]*?needs:\s+[\s\S]*?-\s+extended_scan_shard\s+if:\s+\$\{\{\s*always\(\)\s*&&",
        )

    def test_daily_scan_workflow_uses_schedule_event_for_dst_guard(self):
        workflow_text = Path(".github/workflows/daily_scan_notify.yml").read_text(encoding="utf-8")
        self.assertIn('- cron: "5 20 * 3-11 1-5"', workflow_text)
        self.assertIn('- cron: "5 21 * 1-3,11-12 1-5"', workflow_text)
        self.assertIn("EVENT_SCHEDULE: ${{ github.event.schedule }}", workflow_text)
        self.assertIn(
            'expected_schedule = "5 20 * 3-11 1-5" if is_dst else "5 21 * 1-3,11-12 1-5"',
            workflow_text,
        )
        self.assertNotIn("now.hour == 16", workflow_text)

    def test_early_session_workflow_uses_shared_run_stamp(self):
        workflow_text = Path(".github/workflows/early_session_scan.yml").read_text(encoding="utf-8")
        self.assertGreaterEqual(workflow_text.count('--run-stamp "$RUN_STAMP"'), 2)
        self.assertGreaterEqual(workflow_text.count("RUN_STAMP: ${{ github.run_id }}-${{ github.run_attempt }}"), 2)

    def test_kst_scheduled_workflows_use_single_utc_cron_without_guard(self):
        workflows = {
            ".github/workflows/pre_market_1800_scan.yml": "0 9 * * 1-5",
            ".github/workflows/pre_market_scan.yml": "0 12 * * 1-5",
            ".github/workflows/early_session_scan.yml": "0 14 * * 1-5",
        }
        for path, cron in workflows.items():
            with self.subTest(path=path):
                workflow_text = Path(path).read_text(encoding="utf-8")
                self.assertIn(f'- cron: "{cron}"', workflow_text)
                self.assertNotIn("schedule_guard:", workflow_text)
                self.assertNotIn("needs.schedule_guard", workflow_text)


if __name__ == "__main__":
    unittest.main()
