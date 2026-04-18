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

