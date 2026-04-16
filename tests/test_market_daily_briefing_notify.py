import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from scripts.market_daily_briefing_notify import (
    build_market_daily_briefing_failure_text,
    build_market_daily_briefing_text,
    send_telegram_message,
    split_telegram_message_text,
)


class MarketDailyBriefingNotifyTests(unittest.TestCase):
    def _build_report_payload(self) -> dict:
        gainers = []
        losers = []
        for idx in range(35):
            gainers.append(
                {
                    "symbol": f"G{idx:03d}",
                    "price": 100 + idx,
                    "change_value": 1.5 + idx * 0.1,
                    "change_pct": 2.0 + idx * 0.05,
                    "volume_ratio": 1.2 + idx * 0.01,
                    "reason": "up momentum",
                }
            )
            losers.append(
                {
                    "symbol": f"L{idx:03d}",
                    "price": 80 + idx,
                    "change_value": -(1.0 + idx * 0.1),
                    "change_pct": -(1.5 + idx * 0.05),
                    "volume_ratio": 1.1 + idx * 0.02,
                    "reason": "down pressure",
                }
            )
        return {
            "briefing_report": {
                "market_date_label": "2026-04-15 (US)",
                "headline": "US equities closed higher led by tech",
                "executive_summary": {
                    "risk_state_display": "RISK_ON",
                    "fear_greed_score": 72,
                    "fear_greed_label": "탐욕",
                    "short_view": "leaders remained strong into close",
                },
                "benchmarks": {
                    "NASDAQ100": {"symbol": "QQQ", "price": 490.0, "change_value": 6.4, "change_pct": 1.32},
                    "S&P500": {"symbol": "SPY", "price": 530.0, "change_value": 3.2, "change_pct": 0.61},
                    "DOW": {"symbol": "DIA", "price": 405.0, "change_value": 1.1, "change_pct": 0.27},
                    "RUSSELL2000": {"symbol": "IWM", "price": 205.0, "change_value": 0.7, "change_pct": 0.34},
                    "VIX": {"symbol": "VIX", "price": 15.8, "change_value": -0.4, "change_pct": -2.5},
                },
                "macro": {
                    "10Y": {"symbol": "10Y", "price": 43.1, "change_value": -0.4, "change_pct": -0.92},
                    "DXY": {"symbol": "DXY", "price": 103.2, "change_value": 0.2, "change_pct": 0.19},
                    "USD/KRW": {"symbol": "USD/KRW", "price": 1360.1, "change_value": 4.2, "change_pct": 0.31},
                    "Gold": {"symbol": "Gold", "price": 2380.0, "change_value": 11.4, "change_pct": 0.48},
                    "WTI": {"symbol": "WTI", "price": 81.2, "change_value": 0.9, "change_pct": 1.12},
                    "BTC": {"symbol": "BTC", "price": 69500.0, "change_value": 560.0, "change_pct": 0.81},
                },
                "relative_strength": {"QQQ_SPY": 0.71, "IWM_SPY": -0.22},
                "sentiment": {"risk_state_display": "RISK_ON", "fear_greed_score": 72, "fear_greed_label": "탐욕"},
                "sector_rank": [
                    {"rank": 1, "symbol": "XLK", "label": "Technology", "change_pct": 2.1},
                    {"rank": 2, "symbol": "XLF", "label": "Financials", "change_pct": 0.8},
                    {"rank": 3, "symbol": "XLU", "label": "Utilities", "change_pct": -1.2},
                ],
                "movers": {"gainers": gainers, "losers": losers},
                "action_points": {
                    "insight_bullets": ["follow leaders", "watch volume confirmation"],
                    "analysis_actions": [{"symbol": "NVDA"}, {"symbol": "AAPL"}, {"symbol": "MSFT"}],
                    "watchlist": ["QQQ hold", "VIX fade"],
                },
            },
            "market_date_label": "2026-04-15 (US)",
            "headline": "US equities closed higher led by tech",
            "cards": [],
            "gainers_detail": gainers,
            "losers_detail": losers,
        }

    def test_report_text_contains_sections_and_requested_metric_labels(self):
        payload = self._build_report_payload()
        text = build_market_daily_briefing_text(payload, run_at_kst=datetime(2026, 4, 16, 6, 15, 0), detail_limit=30)
        self.assertIn("1) Executive Summary", text)
        self.assertIn("2) Index Snapshot", text)
        self.assertIn("3) Macro Snapshot", text)
        self.assertIn("4) Relative Strength", text)
        self.assertIn("5) Sector Strength (강->약)", text)
        self.assertIn("6) Top Movers +30 / -30", text)
        self.assertIn("7) Action Checklist", text)
        self.assertIn("NASDAQ100", text)
        self.assertIn("S&P500", text)
        self.assertIn("DOW", text)
        self.assertIn("RUSSELL2000", text)
        self.assertIn("VIX", text)
        self.assertIn("10Y", text)
        self.assertIn("DXY", text)
        self.assertIn("USD/KRW", text)
        self.assertIn("Gold", text)
        self.assertIn("WTI", text)
        self.assertIn("BTC", text)

    def test_report_text_contains_fear_greed_and_relative_strength(self):
        payload = self._build_report_payload()
        text = build_market_daily_briefing_text(payload, run_at_kst=datetime(2026, 4, 16, 6, 15, 0), detail_limit=30)
        self.assertIn("공탐지수(Fear/Greed): 72/100 (탐욕)", text)
        self.assertIn("QQQ-SPY: +0.71%p", text)
        self.assertIn("IWM-SPY: -0.22%p", text)

    def test_report_text_limits_gainers_and_losers_to_30(self):
        payload = self._build_report_payload()
        text = build_market_daily_briefing_text(payload, run_at_kst=datetime(2026, 4, 16, 6, 15, 0), detail_limit=30)
        self.assertIn("30. G029", text)
        self.assertNotIn("31. G030", text)
        self.assertIn("30. L029", text)
        self.assertNotIn("31. L030", text)

    def test_fallback_without_briefing_report_uses_legacy_format(self):
        payload = {
            "market_date_label": "2026-04-15 (US)",
            "headline": "legacy headline",
            "cards": [
                {"id": "daily_insight", "subtitle": "legacy insight", "bullets": [{"text": "legacy bullet"}]},
                {"id": "sector_pressure", "metrics": [{"label": "XLK", "delta": "+2.10%", "note": "Tech"}]},
            ],
            "gainers_detail": [{"symbol": "AAA", "price": 100, "change_value": 1, "change_pct": 1, "volume_ratio": 1.2, "reason": "legacy"}],
            "losers_detail": [{"symbol": "BBB", "price": 90, "change_value": -1, "change_pct": -1, "volume_ratio": 1.1, "reason": "legacy"}],
        }
        text = build_market_daily_briefing_text(payload, run_at_kst=datetime(2026, 4, 16, 6, 15, 0), detail_limit=30)
        self.assertIn("핵심 인사이트:", text)
        self.assertIn("섹터 강약도 (강->약):", text)
        self.assertIn("주요 등락주 상승 1개", text)

    def test_split_telegram_message_text_chunks_long_text(self):
        raw = "\n".join([f"line-{idx:03d}-abcdefghijklmnopqrstuvwxyz" for idx in range(100)])
        chunks = split_telegram_message_text(raw, chunk_size=180)
        self.assertGreater(len(chunks), 1)
        self.assertEqual("\n".join(chunks), raw)
        self.assertTrue(all(len(chunk) <= 180 for chunk in chunks))

    @patch("scripts.market_daily_briefing_notify.requests.post")
    def test_send_telegram_message_sends_all_chunks_in_order(self, mock_post: MagicMock):
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"ok": True}
        mock_post.return_value = response

        text = "\n".join([f"row-{idx:03d}-abcdefghijklmno" for idx in range(70)])
        expected_chunks = split_telegram_message_text(text, chunk_size=140)
        send_telegram_message("token", "chat", text, chunk_size=140)

        self.assertEqual(mock_post.call_count, len(expected_chunks))
        sent_chunks = [call.kwargs["json"]["text"] for call in mock_post.call_args_list]
        self.assertEqual(sent_chunks, expected_chunks)

    def test_failure_text_contains_notice(self):
        text = build_market_daily_briefing_failure_text(
            run_at_kst=datetime(2026, 4, 16, 6, 15, 0),
            reason="payload_build_error",
        )
        self.assertIn("브리핑 생성 실패", text)
        self.assertIn("스캐너 전환 알림과 전체 CSV 전송은 계속 진행됩니다.", text)


if __name__ == "__main__":
    unittest.main()
