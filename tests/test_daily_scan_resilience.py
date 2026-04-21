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
        self.assertEqual(set(merged["priority_modes"]), {"from_prev_scan", "empty_fallback"})

    def test_run_post_close_merge_prepends_partial_result_warning(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            merge_dir = root / "merge_inputs"
            out_dir = root / "final"
            merge_dir.mkdir(parents=True, exist_ok=True)

            rows_a = [{"ticker": "AAA", "scan_score": 3.0, "es": 1.0, "volume_ratio_20": 1.2}]
            rows_b = [{"ticker": "BBB", "scan_score": 2.0, "es": 0.5, "volume_ratio_20": 1.3}]
            (merge_dir / "scan_rows_20260420_010101_shard0of3.json").write_text(json.dumps(rows_a), encoding="utf-8")
            (merge_dir / "scan_rows_20260420_010101_shard2of3.json").write_text(json.dumps(rows_b), encoding="utf-8")
            (merge_dir / "run_meta_20260420_010101_shard0of3.json").write_text(
                json.dumps({"mode": "scan", "shard_count": 3, "shard_index": 0, "result_count": 1, "performance": {"skip_count": 0}}),
                encoding="utf-8",
            )
            (merge_dir / "run_meta_20260420_010101_shard2of3.json").write_text(
                json.dumps({"mode": "scan", "shard_count": 3, "shard_index": 2, "result_count": 1, "performance": {"skip_count": 0}}),
                encoding="utf-8",
            )

            args = self._base_args(merge_dir=str(merge_dir), shard_count=3, shard_index=0)
            result = _run_post_close(
                args,
                run_at_kst=datetime(2026, 4, 20, 5, 0, 0, tzinfo=KST),
                out_dir=out_dir,
            )

            self.assertEqual(result, 0)
            summary_file = next(out_dir.glob("trend_turn_summary_*_merged.txt"))
            summary_text = summary_file.read_text(encoding="utf-8")
            self.assertIn("부분 결과", summary_text)
            self.assertIn("누락 index=[1]", summary_text)
            self.assertIn("=== [7/7] Buy Turn Filter ===", summary_text)

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

    def test_daily_scan_workflow_uses_eight_shards(self):
        workflow_text = Path(".github/workflows/daily_scan_notify.yml").read_text(encoding="utf-8")
        self.assertGreaterEqual(workflow_text.count("shard_index: [0, 1, 2, 3, 4, 5, 6, 7]"), 2)
        self.assertGreaterEqual(workflow_text.count("--shard-count 8"), 2)

        self.assertRegex(
            workflow_text,
            r"merge_and_notify:\s+name:\s+merge-and-notify[\s\S]*?needs:\s+scan_shard\s+if:\s+\$\{\{\s*always\(\)\s*\}\}",
        )
        self.assertRegex(
            workflow_text,
            r"extended_merge_and_notify:\s+name:\s+extended-merge-and-notify[\s\S]*?needs:\s+extended_scan_shard\s+if:\s+\$\{\{\s*always\(\)\s*\}\}",
        )


if __name__ == "__main__":
    unittest.main()
