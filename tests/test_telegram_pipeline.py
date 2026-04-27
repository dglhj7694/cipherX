import json
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app_ui.pages.home_page import extract_section_candidates, load_latest_telegram_digest
from scripts.daily_scan_and_notify import _build_post_close_digest_bundle, _send_telegram_if_enabled
from telegram_pipeline import (
    FINAL_TOP_LIMIT,
    FIVE_DAY_TOP_LIMIT,
    HMA_EMA_TOP_LIMIT,
    TelegramCandidate,
    annotate_rows_with_qbs,
    build_post_close_digest,
    build_post_close_message_texts,
    split_telegram_message_text,
    write_local_digest_artifacts,
)


class TelegramPipelineTests(unittest.TestCase):
    def setUp(self):
        self.market_date = date(2026, 4, 23)
        self.generated_at = datetime(2026, 4, 24, 5, 0, 0)

    def _row(self, ticker: str, **overrides):
        row = {
            "ticker": ticker,
            "price": 101.25,
            "chg_value": 1.75,
            "chg": 2.35,
            "chg_5d": 12.0,
            "volume_ratio_20": 1.45,
            "dollar_volume_20": 125_000_000,
            "final_entry_eligible": True,
            "final_entry_selected": True,
            "final_entry_score": 90.0,
            "b_score": 3,
            "c_score": 2,
            "scan_score": 140.0,
            "es": 7.0,
            "low_conflict_bullish": True,
            "strategy_conflict_level": "LOW",
            "multi_buy": 2,
            "multi_sell": 0,
            "thin_trade_risk": False,
            "bearish_gap_failure": False,
            "utbot_buy_recent": True,
            "hull_turn_bull_recent": False,
            "bull_turn_recent": True,
            "latest_session_utbot_buy_turn": True,
            "latest_session_hull_buy_turn": False,
            "utbot_buy_last_date": self.market_date.isoformat(),
            "hull_turn_bull_last_date": "N/A",
            "days_since_utbot_buy": 0,
            "days_since_hull_turn_bull": 99,
            "cmf": 0.18,
            "obv_slope": 1.2,
            "uptrend_persistent": True,
            "hma20_slope_pct": 1.8,
            "hma60_slope_pct": 2.2,
            "pullback_from_swing_high_pct": -4.5,
            "drawdown_from_20d_high_pct": -4.0,
            "pullback_atr_multiple": 1.8,
            "pullback_ready": True,
            "pullback_reentry": True,
            "volume_dry_up_score": 12.0,
            "bull_strength_recent": True,
            "volume_bullish": True,
            "adx": 24.0,
            "rs_rank_vs_index": 83.0,
            "dist_sma20_pct": 9.0,
            "zscore20": 1.9,
            "utbot_sell_recent": False,
            "hull_turn_bear_recent": False,
            "utbot_sell_last_date": "N/A",
            "hull_turn_bear_last_date": "N/A",
            "gap_setup_candidate": True,
            "gap_setup_score": 9,
            "gap_setup_gate_count": 4,
            "gap_setup_hits": ["band squeeze", "relative strength"],
            "gap_setup_quality_hits": ["volume dry-up"],
            "pocket_pivot_candidate": True,
            "pocket_pivot_score": 10,
            "pocket_pivot_gate_count": 4,
            "pocket_pivot_hits": ["PocketPivot", "volume recovery"],
            "pocket_pivot_quality_hits": ["institutional flow"],
            "new_52w_high": True,
            "new_52w_closing_high": True,
            "latest_bar_date": self.market_date.isoformat(),
            "ema50": 98.0,
            "hma_ema_long_entry": True,
            "hma_ema_long_aligned": True,
            "hma25_ema25_cross_bull": True,
            "hma_ema_risk_to_ema50_pct": 2.0,
        }
        row.update(overrides)
        return row

    def test_build_post_close_digest_keeps_overlap_and_has_hma_section(self):
        digest = build_post_close_digest(
            [self._row("ALPHA")],
            run_stamp="20260424_050000",
            generated_at=self.generated_at,
            market_date=self.market_date,
            scan_label="post-close default",
            universe_count=1,
            result_count=1,
            skip_count=0,
        )
        section_map = digest.section_map()

        self.assertEqual(
            digest.section_order,
            [
                "qbs_buy_now",
                "qbs_chase_watch",
                "qbs_pullback_wait",
                "final_top",
                "buy_turn",
                "pullback_reentry",
                "trend_continuation",
                "hma_ema_trend",
                "sell_turn",
                "gap_setup",
                "pocket_pivot",
                "five_day_top",
                "new_52w_high",
            ],
        )
        self.assertEqual([item.ticker for item in section_map["final_top"].items], ["ALPHA"])
        self.assertEqual([item.ticker for item in section_map["buy_turn"].items], ["ALPHA"])
        self.assertEqual([item.ticker for item in section_map["hma_ema_trend"].items], ["ALPHA"])
        self.assertEqual([item.ticker for item in section_map["gap_setup"].items], ["ALPHA"])
        self.assertEqual([item.ticker for item in section_map["pocket_pivot"].items], ["ALPHA"])
        self.assertEqual([item.ticker for item in section_map["five_day_top"].items], ["ALPHA"])
        self.assertEqual([item.ticker for item in section_map["new_52w_high"].items], ["ALPHA"])
        self.assertTrue(section_map["final_top"].items[0].source_flags["hma_ema_long_aligned"])
        self.assertTrue(section_map["final_top"].items[0].source_flags["hma_ema_long_entry"])

    def test_qbs_scores_confluence_above_single_buy_turn(self):
        confluence = self._row("ALPHA")
        single_buy = self._row(
            "BETA",
            final_entry_eligible=False,
            final_entry_selected=False,
            chg_5d=0.0,
            uptrend_persistent=False,
            pullback_ready=False,
            pullback_reentry=False,
            bull_strength_recent=False,
            gap_setup_candidate=False,
            pocket_pivot_candidate=False,
            new_52w_high=False,
            latest_bar_date=self.market_date.isoformat(),
            hma_ema_long_entry=False,
            hma_ema_long_aligned=False,
            hma25_ema25_cross_bull=False,
        )

        annotated = annotate_rows_with_qbs([confluence, single_buy], target_date=self.market_date)
        by_ticker = {row["ticker"]: row for row in annotated}

        self.assertGreater(float(by_ticker["ALPHA"]["qbs_score"]), float(by_ticker["BETA"]["qbs_score"]))
        self.assertEqual(by_ticker["ALPHA"]["qbs_bucket"], "BUY_NOW")

    def test_qbs_hard_risk_and_chase_buckets(self):
        sell_conflict = self._row(
            "SELLX",
            utbot_sell_last_date=self.market_date.isoformat(),
        )
        chase = self._row("CHASE", chg=13.0)
        extreme = self._row("EXTREME", chg=21.0)

        annotated = annotate_rows_with_qbs([sell_conflict, chase, extreme], target_date=self.market_date)
        by_ticker = {row["ticker"]: row for row in annotated}

        self.assertEqual(by_ticker["SELLX"]["qbs_bucket"], "EXCLUDE")
        self.assertIn("sell_turn", by_ticker["SELLX"]["qbs_risk_flags"])
        self.assertEqual(by_ticker["CHASE"]["qbs_bucket"], "CHASE_WATCH")
        self.assertIn("chase_risk", by_ticker["CHASE"]["qbs_risk_flags"])
        self.assertEqual(by_ticker["EXTREME"]["qbs_bucket"], "CHASE_WATCH")
        self.assertIn("extreme_chase", by_ticker["EXTREME"]["qbs_risk_flags"])

    def test_qbs_high_conflict_extreme_strength_stays_chase_watch(self):
        row = self._row(
            "POET",
            chg=28.84,
            chg_5d=107.99,
            strategy_conflict_level="HIGH",
            low_conflict_bullish=False,
            final_entry_eligible=False,
            final_entry_selected=False,
            gap_setup_candidate=False,
            new_52w_high=False,
            hma_ema_long_entry=False,
            hma_ema_long_aligned=False,
        )

        annotated = annotate_rows_with_qbs([row], target_date=self.market_date)

        self.assertEqual(annotated[0]["qbs_bucket"], "CHASE_WATCH")
        self.assertIn("high_conflict", annotated[0]["qbs_risk_flags"])
        self.assertIn("extreme_chase", annotated[0]["qbs_risk_flags"])

    def test_qbs_hma_negative_not_buy_now_and_pullback_wait(self):
        hma_negative = self._row(
            "HMANEG",
            final_entry_eligible=False,
            final_entry_selected=False,
            latest_session_utbot_buy_turn=False,
            latest_session_hull_buy_turn=False,
            utbot_buy_last_date="N/A",
            hull_turn_bull_last_date="N/A",
            chg=-0.5,
            chg_5d=0.0,
            uptrend_persistent=False,
            pullback_ready=False,
            pullback_reentry=False,
            bull_strength_recent=False,
            gap_setup_candidate=False,
            pocket_pivot_candidate=False,
            new_52w_high=False,
            hma_ema_long_entry=True,
            hma_ema_long_aligned=True,
            hma25_ema25_cross_bull=True,
        )
        pullback = self._row(
            "PULL",
            final_entry_eligible=False,
            final_entry_selected=False,
            latest_session_utbot_buy_turn=False,
            latest_session_hull_buy_turn=False,
            utbot_buy_last_date="N/A",
            hull_turn_bull_last_date="N/A",
            chg=0.4,
            chg_5d=0.0,
            gap_setup_candidate=False,
            pocket_pivot_candidate=False,
            new_52w_high=False,
            hma_ema_long_entry=False,
            hma_ema_long_aligned=False,
            hma25_ema25_cross_bull=False,
        )

        annotated = annotate_rows_with_qbs([hma_negative, pullback], target_date=self.market_date)
        by_ticker = {row["ticker"]: row for row in annotated}

        self.assertNotEqual(by_ticker["HMANEG"]["qbs_bucket"], "BUY_NOW")
        self.assertEqual(by_ticker["PULL"]["qbs_bucket"], "PULLBACK_WAIT")

    def test_qbs_candidate_mutable_fields_are_isolated(self):
        first = TelegramCandidate("AAA", None, None, None, None, "qbs_buy_now", 1, "", "")
        second = TelegramCandidate("BBB", None, None, None, None, "qbs_buy_now", 2, "", "")

        first.tags.append("final")
        first.risk_flags.append("chase_risk")

        self.assertEqual(second.tags, [])
        self.assertEqual(second.risk_flags, [])

    def test_turn_sections_use_same_day_only(self):
        same_day_buy = self._row("BUYDAY")
        recent_buy_only = self._row(
            "BUYRECENT",
            latest_session_utbot_buy_turn=False,
            latest_session_hull_buy_turn=False,
            utbot_buy_last_date="2026-04-22",
            days_since_utbot_buy=1,
            hma_ema_long_entry=False,
            hma_ema_long_aligned=False,
        )
        same_day_sell = self._row(
            "SELLDAY",
            final_entry_eligible=False,
            final_entry_selected=False,
            latest_session_utbot_buy_turn=False,
            utbot_buy_last_date="N/A",
            utbot_sell_last_date=self.market_date.isoformat(),
            hull_turn_bear_last_date="N/A",
            hma_ema_long_entry=False,
            hma_ema_long_aligned=False,
        )
        risk_only = self._row(
            "RISKONLY",
            final_entry_eligible=False,
            final_entry_selected=False,
            latest_session_utbot_buy_turn=False,
            utbot_buy_last_date="N/A",
            thin_trade_risk=True,
            bearish_gap_failure=True,
            utbot_sell_last_date="N/A",
            hull_turn_bear_last_date="N/A",
            hma_ema_long_entry=False,
            hma_ema_long_aligned=False,
        )

        digest = build_post_close_digest(
            [same_day_buy, recent_buy_only, same_day_sell, risk_only],
            run_stamp="20260424_050000",
            generated_at=self.generated_at,
            market_date=self.market_date,
            scan_label="post-close default",
            universe_count=4,
            result_count=4,
            skip_count=0,
        )
        section_map = digest.section_map()

        self.assertEqual([item.ticker for item in section_map["buy_turn"].items], ["BUYDAY"])
        self.assertEqual([item.ticker for item in section_map["sell_turn"].items], ["SELLDAY"])
        self.assertEqual(section_map["buy_turn"].items[0].source_flags.get("turn_engine"), "UTBot")
        self.assertEqual(section_map["sell_turn"].items[0].source_flags.get("turn_engine"), "UTBot")

    def test_only_final_five_hma_have_top20_limits(self):
        rows = [
            self._row(
                f"T{i:02d}",
                final_entry_score=500 - i,
                chg_5d=50 - i,
                scan_score=300 - i,
                hma_ema_risk_to_ema50_pct=1.0 + i * 0.05,
            )
            for i in range(25)
        ]
        digest = build_post_close_digest(
            rows,
            run_stamp="20260424_050000",
            generated_at=self.generated_at,
            market_date=self.market_date,
            scan_label="post-close default",
            universe_count=25,
            result_count=25,
            skip_count=0,
        )
        section_map = digest.section_map()

        self.assertEqual(section_map["final_top"].item_count, FINAL_TOP_LIMIT)
        self.assertEqual(section_map["five_day_top"].item_count, FIVE_DAY_TOP_LIMIT)
        self.assertEqual(section_map["hma_ema_trend"].item_count, HMA_EMA_TOP_LIMIT)
        self.assertEqual(section_map["buy_turn"].item_count, 25)
        self.assertEqual(section_map["gap_setup"].item_count, 25)
        self.assertEqual(section_map["pocket_pivot"].item_count, 25)

    def test_hma_selector_applies_price_over_ema50_gate(self):
        ok = self._row("OK", price=101.0, ema50=100.0)
        blocked = self._row("BLOCKED", price=99.0, ema50=100.0)
        digest = build_post_close_digest(
            [ok, blocked],
            run_stamp="20260424_050000",
            generated_at=self.generated_at,
            market_date=self.market_date,
            scan_label="post-close default",
            universe_count=2,
            result_count=2,
            skip_count=0,
        )
        hma_items = digest.section_map()["hma_ema_trend"].items
        self.assertEqual([item.ticker for item in hma_items], ["OK"])

    def test_message_contract_is_single_main_message(self):
        digest = build_post_close_digest(
            [self._row("ALPHA"), self._row("BETA", final_entry_score=80.0, chg_5d=9.5)],
            run_stamp="20260424_050000",
            generated_at=self.generated_at,
            market_date=self.market_date,
            scan_label="post-close default",
            universe_count=2,
            result_count=2,
            skip_count=0,
        )
        messages = build_post_close_message_texts(digest)
        self.assertEqual(len(messages), 1)
        self.assertIn("## 1.", messages[0])
        self.assertIn("## 2.", messages[0])

    def test_qbs_blocks_render_above_existing_sections_with_special_numbering(self):
        digest = build_post_close_digest(
            [self._row("ALPHA")],
            run_stamp="20260424_050000",
            generated_at=self.generated_at,
            market_date=self.market_date,
            scan_label="post-close default",
            universe_count=1,
            result_count=1,
            skip_count=0,
        )
        message = build_post_close_message_texts(digest)[0]

        qbs_0 = message.index("## 0. ")
        qbs_01 = message.index("## 0-1. ")
        qbs_02 = message.index("## 0-2. ")
        normal_1 = message.index("## 1. ")
        self.assertTrue(qbs_0 < qbs_01 < qbs_02 < normal_1)
        self.assertIn("QBS", message)

    def test_empty_qbs_blocks_are_always_rendered(self):
        digest = build_post_close_digest(
            [],
            run_stamp="20260424_050000",
            generated_at=self.generated_at,
            market_date=self.market_date,
            scan_label="post-close default",
            universe_count=0,
            result_count=0,
            skip_count=0,
        )
        message = build_post_close_message_texts(digest)[0]

        self.assertIn("## 0. ", message)
        self.assertIn("## 0-1. ", message)
        self.assertIn("## 0-2. ", message)
        self.assertGreaterEqual(message.count("- 해당 없음"), 3)

    def test_chunk_split_keeps_qbs_before_existing_sections(self):
        rows = [self._row(f"T{i:02d}", final_entry_score=100.0 - i, chg_5d=15.0 - (i / 10.0)) for i in range(12)]
        digest = build_post_close_digest(
            rows,
            run_stamp="20260424_050000",
            generated_at=self.generated_at,
            market_date=self.market_date,
            scan_label="post-close default",
            universe_count=12,
            result_count=12,
            skip_count=0,
        )
        chunks = split_telegram_message_text(build_post_close_message_texts(digest)[0], chunk_size=350)
        joined = "\n".join(chunks)

        self.assertGreater(len(chunks), 1)
        self.assertTrue(joined.index("## 0. ") < joined.index("## 0-1. ") < joined.index("## 0-2. ") < joined.index("## 1. "))

    def test_message_lines_show_core_fields_and_turn_engine_only_for_turn_sections(self):
        buy_hull_only = self._row(
            "BUYHULL",
            latest_session_utbot_buy_turn=False,
            latest_session_hull_buy_turn=True,
            utbot_buy_last_date="N/A",
            hull_turn_bull_last_date=self.market_date.isoformat(),
        )
        sell_both = self._row(
            "SELLBOTH",
            final_entry_eligible=False,
            final_entry_selected=False,
            latest_session_utbot_buy_turn=False,
            latest_session_hull_buy_turn=False,
            utbot_buy_last_date="N/A",
            hull_turn_bull_last_date="N/A",
            utbot_sell_last_date=self.market_date.isoformat(),
            hull_turn_bear_last_date=self.market_date.isoformat(),
            hma_ema_long_entry=False,
            hma_ema_long_aligned=False,
        )
        digest = build_post_close_digest(
            [buy_hull_only, sell_both],
            run_stamp="20260424_050000",
            generated_at=self.generated_at,
            market_date=self.market_date,
            scan_label="post-close default",
            universe_count=2,
            result_count=2,
            skip_count=0,
        )
        message = build_post_close_message_texts(digest)[0]

        self.assertIn("BUYHULL | (+1.75, +2.35%) | x1.45 | HULL", message)
        self.assertIn("SELLBOTH | (+1.75, +2.35%) | x1.45 | UTBot+HULL", message)

    def test_split_telegram_message_text_prefers_section_boundaries(self):
        text = "\n\n".join(
            [
                "[오늘 종목판]\n- 시장일: 2026-04-23 (US)",
                "## 1. 오늘 최우선 후보 (Top 2)\n1. AAA | (+1.00, +2.00%) | x1.20",
                "## 2. 오늘 매수전환 (1 items)\n1. BBB | (+0.50, +1.00%) | x1.10 | UTBot",
                "## 3. 눌림목 재진입 (1 items)\n1. CCC | (+0.30, +0.80%) | x0.95",
            ]
        )
        chunks = split_telegram_message_text(text, chunk_size=120)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(any(chunk.startswith("## 2.") for chunk in chunks))
        self.assertTrue(any("## 3." in chunk for chunk in chunks))

    def test_write_local_digest_artifacts_writes_latest_and_versioned_json(self):
        digest = build_post_close_digest(
            [self._row("AAPL")],
            run_stamp="20260424_050000",
            generated_at=self.generated_at,
            market_date=self.market_date,
            scan_label="post-close default",
            universe_count=1,
            result_count=1,
            skip_count=0,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            paths = write_local_digest_artifacts(digest, out_dir=Path(temp_dir))
            latest_payload = json.loads(paths["latest_path"].read_text(encoding="utf-8"))
            versioned_payload = json.loads(paths["versioned_path"].read_text(encoding="utf-8"))

        self.assertEqual(latest_payload["version"], "2.0")
        self.assertEqual(versioned_payload["run_stamp"], "20260424_050000")
        self.assertIn("items", latest_payload["sections"][0])

    def test_build_post_close_digest_bundle_keeps_publish_failure_non_blocking(self):
        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "scripts.daily_scan_and_notify.publish_digest_if_configured",
            side_effect=RuntimeError("publish unavailable"),
        ):
            bundle = _build_post_close_digest_bundle(
                rows=[self._row("AAPL")],
                out_dir=Path(temp_dir),
                run_stamp="20260424_050000",
                run_label="20260424_050000",
                run_at_kst=self.generated_at,
                market_date=self.market_date,
                scan_label="post-close default",
                universe_count=1,
                result_count=1,
                skip_count=0,
                publish_enabled=True,
            )
            self.assertTrue(Path(bundle["summary_path"]).exists())
            self.assertEqual(len(bundle["message_texts"]), 1)
            self.assertEqual(bundle["publish_status"]["reason"], "publish_error")
            self.assertIn("publish unavailable", bundle["publish_status"]["detail"])

    def test_send_telegram_if_enabled_uses_digest_message_sequence_when_present(self):
        args = SimpleNamespace(dry_run=False, skip_telegram=False)
        with patch.dict(
            "os.environ",
            {"TELEGRAM_BOT_TOKEN": "token", "TELEGRAM_CHAT_ID": "chat"},
            clear=False,
        ), patch("scripts.daily_scan_and_notify.send_digest_telegram_messages") as mock_digest_send, patch(
            "scripts.daily_scan_and_notify.send_telegram_message"
        ) as mock_single_send, patch("scripts.daily_scan_and_notify.send_telegram_document") as mock_document:
            _send_telegram_if_enabled(
                args,
                summary_text="legacy summary",
                csv_path=Path("C:/tmp/scan.csv"),
                scan_label="post-close default",
                run_at_kst=self.generated_at,
                message_texts=["main board"],
            )

        mock_digest_send.assert_called_once_with("token", "chat", ["main board"])
        mock_single_send.assert_not_called()
        mock_document.assert_called_once()


class HomeDigestLoaderTests(unittest.TestCase):
    def test_extract_section_candidates_reads_items_contract(self):
        payload = {
            "sections": [
                {"key": "final_top", "items": [{"ticker": "AAPL"}, {"ticker": "MSFT"}]},
            ]
        }
        self.assertEqual([item["ticker"] for item in extract_section_candidates(payload, "final_top", limit=1)], ["AAPL"])

    def test_load_latest_telegram_digest_uses_remote_then_cache_fallback(self):
        payload = {
            "market_date": "2026-04-23",
            "sections": [
                {"key": "final_top", "items": [{"ticker": "AAPL"}, {"ticker": "MSFT"}]},
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "digest.json"
            with patch(
                "app_ui.pages.home_page.resolve_github_digest_config",
                return_value={"repo": "owner/repo", "branch": "telegram-digest", "path": "post_close/latest.json", "token": ""},
            ), patch("app_ui.pages.home_page._fetch_digest_cached", return_value=payload):
                first = load_latest_telegram_digest(cache_path=cache_path)

            self.assertEqual(first["source"], "remote")
            self.assertEqual(first["payload"]["market_date"], "2026-04-23")
            self.assertEqual([item["ticker"] for item in extract_section_candidates(first["payload"], "final_top", limit=1)], ["AAPL"])

            with patch(
                "app_ui.pages.home_page.resolve_github_digest_config",
                return_value={"repo": "owner/repo", "branch": "telegram-digest", "path": "post_close/latest.json", "token": ""},
            ), patch("app_ui.pages.home_page._fetch_digest_cached", side_effect=RuntimeError("network down")):
                second = load_latest_telegram_digest(cache_path=cache_path)

            self.assertEqual(second["source"], "cache")
            self.assertEqual(second["payload"]["market_date"], "2026-04-23")
            self.assertIn("network down", second["error"])


if __name__ == "__main__":
    unittest.main()
