import unittest
from unittest.mock import patch

import pandas as pd

import ui


class _StopAfterDownloadCalls(Exception):
    pass


class MarketDailyMoverUniverseTests(unittest.TestCase):
    def setUp(self):
        if hasattr(ui._download_market_history, "clear"):
            ui._download_market_history.clear()
        if hasattr(ui.build_us_market_daily_payload, "clear"):
            ui.build_us_market_daily_payload.clear()

    def test_market_mover_universe_is_union_without_96_cap(self):
        fake_sectors = {
            "A": [f"S{i:03d}" for i in range(120)],
        }
        fake_payload = {
            "items": [],
            "tickers": [f"E{i:03d}" for i in range(80)] + ["S005", "S010"],
            "note": "",
            "errors": [],
        }
        with patch.object(ui, "SECTOR_GROUPS", fake_sectors):
            universe = ui._market_mover_universe(fake_payload)

        self.assertEqual(len(universe), 200)
        self.assertGreater(len(universe), 96)
        self.assertIn("S005", universe)
        self.assertIn("E079", universe)

    def test_resolver_payload_uses_spy_and_eusa(self):
        captured = {}

        def _fake_resolve(items):
            captured["items"] = list(items)
            return {"items": [], "tickers": ["AAA"], "note": "", "errors": []}

        with patch.object(ui, "resolve_etf_universe", side_effect=_fake_resolve):
            payload = ui._resolve_market_mover_etf_payload()

        self.assertEqual(payload.get("tickers"), ["AAA"])
        self.assertEqual(
            captured["items"],
            [
                {"requested": "S&P500", "resolved": "SPY"},
                {"requested": "MSCI(USA)", "resolved": "EUSA"},
            ],
        )

    def test_build_payload_splits_period_between_benchmark_and_movers(self):
        calls = []

        def _fake_download(tickers, period=ui._US_MARKET_HISTORY_PERIOD):
            calls.append((tuple(tickers), period))
            if len(calls) >= 2:
                raise _StopAfterDownloadCalls()
            return pd.DataFrame()

        with patch.object(
            ui,
            "_resolve_market_mover_etf_payload",
            return_value={"items": [], "tickers": ["AAA", "BBB"], "note": "", "errors": []},
        ), patch.object(ui, "_market_mover_universe", return_value=("AAA", "BBB")), patch.object(
            ui,
            "_download_market_history",
            side_effect=_fake_download,
        ):
            with self.assertRaises(_StopAfterDownloadCalls):
                ui.build_us_market_daily_payload()

        self.assertEqual(calls[0][1], ui._US_MARKET_HISTORY_PERIOD)
        self.assertEqual(calls[1][1], ui._US_MARKET_MOVER_HISTORY_PERIOD)
        self.assertEqual(calls[1][0], ("AAA", "BBB"))

    def test_download_market_history_chunks_and_merges_symbols(self):
        calls = []
        idx = pd.date_range("2026-04-10", periods=3, freq="D")

        def _fake_download(tickers, period, interval, group_by, auto_adjust, progress, threads):
            symbols = [str(item) for item in tickers]
            calls.append(tuple(symbols))
            if len(symbols) == 1:
                return pd.DataFrame(
                    {
                        "Close": [1.0, 1.2, 1.3],
                        "Volume": [100, 110, 120],
                    },
                    index=idx,
                )

            data = {}
            for symbol in symbols:
                data[(symbol, "Close")] = [1.0, 1.1, 1.2]
                data[(symbol, "Volume")] = [100, 101, 102]
            return pd.DataFrame(data, index=idx)

        with patch.object(ui, "_US_MARKET_DOWNLOAD_CHUNK_SIZE", 2), patch.object(
            ui,
            "yf",
        ) as yf_mock:
            yf_mock.download.side_effect = _fake_download
            history = ui._download_market_history(("AAA", "BBB", "CCC"), period="3mo")

        self.assertEqual(calls, [("AAA", "BBB"), ("CCC",)])
        self.assertIsInstance(history.columns, pd.MultiIndex)
        self.assertIn("AAA", set(history.columns.get_level_values(0)))
        self.assertIn("BBB", set(history.columns.get_level_values(0)))
        self.assertIn("CCC", set(history.columns.get_level_values(0)))

    def test_top_mover_card_count_stays_limited_to_9_each_side(self):
        mover_universe = tuple(f"M{i:02d}" for i in range(30))

        def _fake_extract_symbol_frame(_history, symbol):
            idx = pd.date_range("2026-03-01", periods=30, freq="D")
            if str(symbol).startswith("M"):
                rank = int(str(symbol)[1:])
                if rank < 15:
                    delta = 15 - rank
                else:
                    delta = -(rank - 14)
            else:
                delta = 0.2
            close = [100.0] * 29 + [100.0 * (1.0 + (delta / 100.0))]
            volume = [1_000_000] * 30
            return pd.DataFrame({"Close": close, "Volume": volume}, index=idx)

        with patch.object(
            ui,
            "_resolve_market_mover_etf_payload",
            return_value={"items": [], "tickers": [], "note": "", "errors": []},
        ), patch.object(ui, "_market_mover_universe", return_value=mover_universe), patch.object(
            ui,
            "_download_market_history",
            return_value=pd.DataFrame(),
        ), patch.object(
            ui,
            "_extract_symbol_frame",
            side_effect=_fake_extract_symbol_frame,
        ), patch.object(
            ui,
            "_collect_market_news",
            return_value={"items": [], "ranked_items": [], "rate_limited": False},
        ), patch.object(
            ui,
            "_generate_us_market_ai_copy",
            return_value={},
        ):
            payload = ui.build_us_market_daily_payload()

        cards = list(payload.get("cards") or [])
        top_mover_card = next(card for card in cards if card.get("id") == "top_movers")
        expected_count = ui._US_MARKET_TOP_MOVER_CARD_COUNT * 2
        self.assertEqual(len(top_mover_card.get("metrics") or []), expected_count)
        self.assertEqual(len(top_mover_card.get("bullets") or []), expected_count)

        gainers_detail = list(payload.get("gainers_detail") or [])
        losers_detail = list(payload.get("losers_detail") or [])
        self.assertEqual(payload.get("mover_detail_limit"), ui._US_MARKET_TOP_MOVER_DETAIL_COUNT)
        self.assertEqual(payload.get("mover_universe_count"), len(mover_universe))
        self.assertEqual(len(gainers_detail), ui._US_MARKET_TOP_MOVER_DETAIL_COUNT)
        self.assertEqual(len(losers_detail), ui._US_MARKET_TOP_MOVER_DETAIL_COUNT)

        required_keys = {
            "symbol",
            "price",
            "prev_close",
            "change_value",
            "change_pct",
            "price_summary",
            "volume_ratio",
            "five_day_change",
            "month_change",
            "reason",
        }
        self.assertTrue(required_keys.issubset(set(gainers_detail[0].keys())))
        self.assertTrue(required_keys.issubset(set(losers_detail[0].keys())))
        self.assertIn("$", str(gainers_detail[0].get("price_summary", "")))
        self.assertIn("(", str(gainers_detail[0].get("price_summary", "")))
        self.assertIn("%", str(gainers_detail[0].get("price_summary", "")))

        gainers_changes = [float(row["change_pct"]) for row in gainers_detail if row.get("change_pct") is not None]
        losers_changes = [float(row["change_pct"]) for row in losers_detail if row.get("change_pct") is not None]
        self.assertEqual(gainers_changes, sorted(gainers_changes, reverse=True))
        self.assertEqual(losers_changes, sorted(losers_changes))


if __name__ == "__main__":
    unittest.main()
