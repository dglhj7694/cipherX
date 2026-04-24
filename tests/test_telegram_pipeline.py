import json
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app_ui.pages.home_page import extract_section_candidates, load_latest_telegram_digest
from scripts.daily_scan_and_notify import _build_post_close_digest_bundle, _send_telegram_if_enabled
from telegram_pipeline import build_post_close_digest, build_post_close_message_texts, write_local_digest_artifacts


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
            "hull_turn_bull_last_date": "없음",
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
            "utbot_sell_last_date": "없음",
            "hull_turn_bear_last_date": "없음",
        }
        row.update(overrides)
        return row

    def test_build_post_close_digest_keeps_final_top_duplicate_and_dedupes_core_sections(self):
        rows = [
            self._row("ALPHA", final_entry_score=99.0),
            self._row(
                "CLASH",
                final_entry_eligible=False,
                final_entry_selected=False,
                utbot_sell_recent=True,
                utbot_sell_last_date="2026-04-22",
                multi_sell=1,
                drawdown_from_20d_high_pct=-8.0,
            ),
        ]

        digest = build_post_close_digest(
            rows,
            run_stamp="20260424_050000",
            generated_at=self.generated_at,
            market_date=self.market_date,
            scan_label="post-close default",
            universe_count=2,
            result_count=2,
            skip_count=0,
        )
        section_map = digest.section_map()

        self.assertEqual([item.ticker for item in section_map["final_top"].detail_items], ["ALPHA"])
        self.assertEqual([item.ticker for item in section_map["buy_turn"].detail_items], ["ALPHA"])
        self.assertEqual([item.ticker for item in section_map["sell_turn"].detail_items], ["CLASH"])
        self.assertEqual(section_map["buy_turn"].dedupe_applied, True)

    def test_buy_turn_sort_uses_es_after_scan_score_tie(self):
        rows = [
            self._row("LOWES", es=5.0),
            self._row("HIGHES", es=9.0),
        ]

        digest = build_post_close_digest(
            rows,
            run_stamp="20260424_050000",
            generated_at=self.generated_at,
            market_date=self.market_date,
            scan_label="post-close default",
            universe_count=2,
            result_count=2,
            skip_count=0,
        )
        buy_tickers = [item.ticker for item in digest.section_map()["buy_turn"].detail_items]
        self.assertEqual(buy_tickers[:2], ["HIGHES", "LOWES"])

    def test_summary_and_detail_messages_follow_top5_and_tier_structure(self):
        rows = [self._row(f"T{i:02d}", final_entry_score=200 - i, scan_score=300 - i) for i in range(12)]
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

        messages = build_post_close_message_texts(digest)
        section_map = digest.section_map()
        summary_text = messages[0]
        final_detail_text = messages[1]

        self.assertEqual(len(messages), 6)
        self.assertEqual(section_map["final_top"].sent_count, 12)
        self.assertEqual([item.ticker for item in section_map["final_top"].summary_items], ["T00", "T01", "T02", "T03", "T04"])
        self.assertEqual(section_map["final_top"].detail_items[0].tier, "A")
        self.assertEqual(section_map["final_top"].detail_items[5].tier, "B")
        self.assertEqual(section_map["final_top"].detail_items[10].tier, "C")
        for ticker in ("T00", "T01", "T02", "T03", "T04"):
            self.assertIn(ticker, summary_text)
        for ticker in ("T00", "T05", "T10"):
            self.assertIn(ticker, final_detail_text)

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
            latest_path = paths["latest_path"]
            versioned_path = paths["versioned_path"]

            self.assertTrue(latest_path.exists())
            self.assertTrue(versioned_path.exists())
            latest_payload = json.loads(latest_path.read_text(encoding="utf-8"))
            versioned_payload = json.loads(versioned_path.read_text(encoding="utf-8"))
            self.assertEqual(latest_payload["run_stamp"], "20260424_050000")
            self.assertEqual(versioned_payload["run_stamp"], "20260424_050000")

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
            self.assertTrue(bundle["local_paths"]["latest_path"].exists())
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
                message_texts=["summary", "detail"],
            )

        mock_digest_send.assert_called_once_with("token", "chat", ["summary", "detail"])
        mock_single_send.assert_not_called()
        mock_document.assert_called_once()


class HomeDigestLoaderTests(unittest.TestCase):
    def test_load_latest_telegram_digest_uses_remote_then_cache_fallback(self):
        payload = {
            "market_date": "2026-04-23",
            "sections": [
                {"key": "final_top", "detail_items": [{"ticker": "AAPL"}, {"ticker": "MSFT"}]},
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
