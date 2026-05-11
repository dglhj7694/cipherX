import unittest

from services.quant_prediction_service import build_quant_prediction_payload


class QuantPredictionServiceTests(unittest.TestCase):
    def test_scanner_rows_drive_prediction_without_program_scores(self):
        payload = build_quant_prediction_payload(
            scanner_rows=[
                {
                    "ticker": "WEAK",
                    "scan_score": 999,
                    "final_entry_score": 100,
                    "qbs_score": 99,
                    "chg": -5.0,
                    "chg_5d": -8.0,
                    "ret20_pct": -12.0,
                    "volume_ratio_20": 0.5,
                    "atr_pct": 1.0,
                    "rs_rank_vs_index": 30.0,
                    "adx": 8.0,
                    "dist_sma20_pct": -12.0,
                    "drawdown_from_52w_high_pct": -40.0,
                    "risk_flags": ["sell", "bearish_gap_failure"],
                },
                {
                    "ticker": "STRG",
                    "scan_score": 0,
                    "final_entry_score": 0,
                    "qbs_score": 0,
                    "chg": 2.0,
                    "chg_5d": 10.0,
                    "ret20_pct": 20.0,
                    "ret20_percentile": 95.0,
                    "volume_ratio_20": 1.8,
                    "atr_pct": 5.0,
                    "rs_rank_vs_index": 90.0,
                    "adx": 30.0,
                    "dist_sma20_pct": 5.0,
                    "drawdown_from_52w_high_pct": -3.0,
                    "signal_count": 3,
                    "risk_flags": [],
                },
            ],
            telegram_payload={},
            market_payload={},
        )

        rows_by_ticker = {row["ticker"]: row for row in payload["rows"]}

        self.assertEqual(payload["source"], "scanner")
        self.assertEqual(rows_by_ticker["STRG"]["prediction_label"], "UP")
        self.assertGreaterEqual(rows_by_ticker["STRG"]["up_probability"], 80.0)
        self.assertEqual(rows_by_ticker["WEAK"]["prediction_label"], "DOWN")
        self.assertLessEqual(rows_by_ticker["WEAK"]["up_probability"], 25.0)
        self.assertEqual(payload["rows"][0]["ticker"], "STRG")

    def test_korean_parenthesized_headers_are_supported(self):
        payload = build_quant_prediction_payload(
            scanner_rows=[
                {
                    "티커(ticker)": "NVDA",
                    "등락률(chg)": "3.2",
                    "5일등락(chg_5d)": "8.5",
                    "거래량비(volume_ratio_20)": "1.6",
                    "ATR%(atr_pct)": "4.5",
                    "상대강도(rs_rank_vs_index)": "88",
                    "ADX(adx)": "27",
                    "MA20거리(dist_sma20_pct)": "4.0",
                    "52주고점거리(drawdown_from_52w_high_pct)": "-4.0",
                }
            ],
            telegram_payload={},
            market_payload={},
        )

        row = payload["rows"][0]

        self.assertEqual(row["ticker"], "NVDA")
        self.assertEqual(row["prediction_label"], "UP")
        self.assertEqual(row["source"], "scanner")

    def test_telegram_fallback_merges_source_flags_and_deduplicates(self):
        payload = build_quant_prediction_payload(
            scanner_rows=[],
            telegram_payload={
                "sections": [
                    {
                        "key": "part2",
                        "items": [
                            {
                                "ticker": "SNDK",
                                "chg_pct": 5.0,
                                "chg_5d": 12.0,
                                "volume_ratio_20": 1.5,
                                "risk_flags": ["extended_5d"],
                                "source_flags": {
                                    "ret20_pct": 24.0,
                                    "atr_pct": 6.0,
                                    "rs_rank_vs_index": 92.0,
                                    "adx": 36.0,
                                    "dist_sma20_pct": 8.0,
                                    "drawdown_from_52w_high_pct": -2.0,
                                },
                            },
                            {"ticker": "SNDK", "chg_pct": 1.0},
                        ],
                    }
                ]
            },
            market_payload={},
        )

        self.assertEqual(payload["source"], "telegram")
        self.assertEqual([row["ticker"] for row in payload["rows"]], ["SNDK"])
        self.assertEqual(payload["rows"][0]["prediction_label"], "UP")
        self.assertEqual(payload["rows"][0]["source"], "telegram:part2")

    def test_market_fallback_and_empty_payload(self):
        market_payload = {
            "briefing_report": {
                "movers": {
                    "gainers": [
                        {
                            "ticker": "AAPL",
                            "chg": 1.2,
                            "volume_ratio_20": 1.1,
                            "atr_pct": 2.5,
                            "rs_rank_vs_index": 65.0,
                            "adx": 20.0,
                        }
                    ]
                }
            }
        }

        market_result = build_quant_prediction_payload([], {}, market_payload)
        empty_result = build_quant_prediction_payload([], {}, {})

        self.assertEqual(market_result["source"], "market")
        self.assertEqual(market_result["rows"][0]["ticker"], "AAPL")
        self.assertIn(market_result["rows"][0]["prediction_label"], {"UP", "NEUTRAL", "DOWN"})
        self.assertEqual(empty_result["source"], "empty")
        self.assertEqual(empty_result["rows"], [])


if __name__ == "__main__":
    unittest.main()
