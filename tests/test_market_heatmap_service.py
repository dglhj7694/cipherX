import unittest

from services.market_heatmap_service import build_market_heatmap_payload, normalize_heatmap_row_keys


class MarketHeatmapServiceTests(unittest.TestCase):
    def test_korean_parenthesized_scanner_headers_are_normalized(self):
        row = {
            "티커(ticker)": "NVDA",
            "현재가(price)": 920.5,
            "등락률(%)(chg)": 3.2,
            "Change5D(%)(chg_5d)": 9.8,
            "거래량비율20(volume_ratio_20)": 1.7,
            "20일평균거래대금(dollar_volume_20)": 1_500_000_000,
            "ATR(%)(atr_pct)": 4.2,
            "RSRankVsIndex(rs_rank_vs_index)": 94,
            "ADX(adx)": 31,
            "탐지시그널총수(detected_signal_total_count)": 7,
            "QBSRiskFlags(qbs_risk_flags)": "chase_risk+hot_zscore",
        }

        normalized = normalize_heatmap_row_keys(row)
        payload = build_market_heatmap_payload([row], {"sections": []}, {}, max_rows=10)
        heatmap_row = payload["rows"][0]

        self.assertEqual(normalized["ticker"], "NVDA")
        self.assertEqual(normalized["chg"], 3.2)
        self.assertEqual(payload["source"], "scanner")
        self.assertEqual(heatmap_row["ticker"], "NVDA")
        self.assertNotEqual(heatmap_row["sector"], "Unclassified")
        self.assertEqual(heatmap_row["price"], 920.5)
        self.assertEqual(heatmap_row["chg_5d"], 9.8)
        self.assertEqual(heatmap_row["volume_ratio_20"], 1.7)
        self.assertEqual(heatmap_row["atr_pct"], 4.2)
        self.assertEqual(heatmap_row["rs_rank_vs_index"], 94)
        self.assertEqual(heatmap_row["adx"], 31)
        self.assertEqual(heatmap_row["signal_count"], 7)
        self.assertEqual(heatmap_row["size"], 1_500_000_000)
        self.assertEqual(heatmap_row["risk_flags"], ["chase_risk", "hot_zscore"])

    def test_scanner_rows_take_priority_over_telegram_and_market(self):
        payload = build_market_heatmap_payload(
            [{"ticker": "SCAN", "chg": 1.0}],
            {"sections": [{"key": "qbs_buy_now", "items": [{"ticker": "TG", "chg_pct": 9.0}]}]},
            {"gainers_detail": [{"symbol": "MKT", "change_pct": 5.0}]},
        )

        self.assertEqual(payload["source"], "scanner")
        self.assertEqual([row["ticker"] for row in payload["rows"]], ["SCAN"])

    def test_telegram_digest_fallback_builds_unique_rows_from_source_flags(self):
        telegram_payload = {
            "sections": [
                {
                    "key": "qbs_buy_now",
                    "items": [
                        {
                            "ticker": "AAPL",
                            "price": 200.0,
                            "chg_pct": 1.2,
                            "volume_ratio_20": 1.4,
                            "risk_flags": ["watch"],
                            "source_flags": {
                                "chg_5d": 4.5,
                                "atr_pct": 2.1,
                                "rs_rank_vs_index": 72,
                                "adx": 19,
                                "qbs_membership_count": 3,
                            },
                        }
                    ],
                },
                {
                    "key": "aggressive_strong_trend",
                    "items": [{"ticker": "AAPL", "chg_pct": 8.0}],
                },
            ]
        }

        payload = build_market_heatmap_payload([], telegram_payload, {}, max_rows=10)
        row = payload["rows"][0]

        self.assertEqual(payload["source"], "telegram")
        self.assertEqual(len(payload["rows"]), 1)
        self.assertEqual(row["ticker"], "AAPL")
        self.assertEqual(row["chg"], 1.2)
        self.assertEqual(row["chg_5d"], 4.5)
        self.assertEqual(row["volume_ratio_20"], 1.4)
        self.assertEqual(row["atr_pct"], 2.1)
        self.assertEqual(row["rs_rank_vs_index"], 72)
        self.assertEqual(row["adx"], 19)
        self.assertEqual(row["risk_flags"], ["watch"])

    def test_market_payload_fallback_uses_movers_and_sector_rank(self):
        market_payload = {
            "gainers_detail": [{"symbol": "MSFT", "change_pct": 2.5, "volume_ratio": 1.2, "five_day_change": 3.4}],
            "briefing_report": {
                "sector_rank": [
                    {"symbol": "XLK", "label": "Technology", "change_pct": 1.1},
                ]
            },
        }

        payload = build_market_heatmap_payload([], {}, market_payload, max_rows=10)

        self.assertEqual(payload["source"], "market")
        self.assertEqual([row["ticker"] for row in payload["rows"]], ["MSFT", "XLK"])
        self.assertEqual(payload["rows"][0]["chg"], 2.5)
        self.assertEqual(payload["rows"][0]["volume_ratio_20"], 1.2)
        self.assertEqual(payload["rows"][1]["sector"], "Technology")

    def test_empty_payload_returns_empty_source_and_size_fallback_is_stable(self):
        unknown_payload = build_market_heatmap_payload([{"ticker": "ZZZZ", "volume_ratio_20": 0}], {}, {}, max_rows=10)
        empty_payload = build_market_heatmap_payload([], {}, {}, max_rows=10)

        self.assertEqual(unknown_payload["rows"][0]["sector"], "Unclassified")
        self.assertEqual(unknown_payload["rows"][0]["size"], 1.0)
        self.assertEqual(empty_payload["source"], "empty")
        self.assertEqual(empty_payload["rows"], [])
        self.assertEqual(empty_payload["summary"]["ticker_count"], 0)


if __name__ == "__main__":
    unittest.main()
