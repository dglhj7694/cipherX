import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from scripts.market_daily_briefing_notify import (
    build_market_daily_briefing_failure_text,
    build_market_daily_briefing_messages,
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
                    "reason": "AI trend extension",
                }
            )
            losers.append(
                {
                    "symbol": f"L{idx:03d}",
                    "price": 80 + idx,
                    "change_value": -(1.0 + idx * 0.1),
                    "change_pct": -(1.5 + idx * 0.05),
                    "volume_ratio": 1.1 + idx * 0.02,
                    "reason": "profit taking",
                }
            )

        return {
            "briefing_report": {
                "market_date_label": "2026-04-15 (US)",
                "headline": "US equities closed higher led by tech",
                "one_liner": "지수는 반등했지만 확산은 약해 메가캡 중심 흐름이었습니다.",
                "breadth_summary": "상승 섹터 4/11, 확산 약함",
                "session_flow": {
                    "premarket": "장전에는 금리 부담 완화 기대가 우위를 만들었습니다.",
                    "regular": "정규장에서는 메가캡 중심 쏠림이 이어졌습니다.",
                    "close": "마감에서는 확산 약세가 유지돼 선별 대응이 유효했습니다.",
                },
                "market_structure": {
                    "label": "Narrow Risk-On",
                    "note": "지수 상승 대비 확산이 약한 구조",
                    "breadth_summary": "상승 섹터 4/11, 확산 약함",
                    "leadership_summary": "QQQ 우위 / IWM 열세",
                },
                "market_structure_text": "리더십은 QQQ 우위였지만 IWM 열세와 breadth 약세가 겹쳐 선별 장세 해석이 유효했습니다.",
                "sector_summary": {
                    "strong": ["XLK", "XLY", "XLF"],
                    "weak": ["XLU", "XLB", "XLI"],
                    "interpretation": "반등은 있었지만 광범위 확산형 강세는 아니었습니다.",
                },
                "theme_clusters": [
                    {"theme": "AI", "count": 9, "sample_symbols": ["G000", "G001", "G002"]},
                    {"theme": "반도체", "count": 6, "sample_symbols": ["G003", "G004", "G005"]},
                ],
                "response_guidance": {
                    "favorable_actions": ["리더주 눌림 대응 우선", "거래량 동반 강세만 선별"],
                    "avoid_actions": ["확산 약한 날 지수 추격 매수", "거래량 부족 급등주 후행 추격"],
                    "checkpoints": ["10Y·DXY·WTI 동조 방향 점검", "IWM 상대강도 변화 점검"],
                    "favorable": ["리더주 눌림 대응 우선", "거래량 동반 강세만 선별"],
                    "avoid": ["확산 약한 날 지수 추격 자제", "거래량 부족 급등주 후행 추격 자제"],
                },
                "checkpoints": [
                    "10Y·DXY·WTI 동조 방향 확인",
                    "IWM 상대강도 회복 여부 확인",
                    "VIX 재상승 여부 확인",
                ],
                "quick_targets": [
                    {"symbol": "G000", "reason": "AI 리더"},
                    {"symbol": "G001", "reason": "거래량 강세"},
                    {"symbol": "G002", "reason": "추세 연장"},
                ],
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
                    {"rank": 1, "symbol": "XLY", "label": "Consumer Discretionary", "change_pct": 2.1},
                    {"rank": 2, "symbol": "XLI", "label": "Industrials", "change_pct": 0.8},
                    {"rank": 3, "symbol": "XLK", "label": "Technology", "change_pct": 0.6},
                    {"rank": 4, "symbol": "XLC", "label": "Communication Services", "change_pct": -0.2},
                    {"rank": 5, "symbol": "XLU", "label": "Utilities", "change_pct": -0.9},
                    {"rank": 6, "symbol": "XLE", "label": "Energy", "change_pct": -1.2},
                ],
                "movers": {"gainers": gainers, "losers": losers},
                "core_movers": {"gainers": gainers[:10], "losers": losers[:10]},
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

    def test_report_messages_split_into_core_and_detail(self):
        payload = self._build_report_payload()
        messages = build_market_daily_briefing_messages(
            payload,
            run_at_kst=datetime(2026, 4, 16, 6, 15, 0),
            detail_limit=30,
            core_mover_limit=10,
            quick_target_limit=8,
        )

        self.assertEqual(len(messages), 2)
        core, detail = messages

        self.assertIn("[오늘 미국장 핵심 브리핑]", core)
        self.assertIn("1) 한줄 결론", core)
        self.assertIn("3) Session Flow", core)
        self.assertIn("6) Market Structure", core)
        self.assertIn("Breadth: 상승 섹터 4/11, 확산 약함", core)
        self.assertIn("해석: 리더십은 QQQ 우위였지만 IWM 열세와 breadth 약세가 겹쳐 선별 장세 해석이 유효했습니다.", core)
        self.assertIn("- 10Y: 4.31% (-4.0bp)", core)
        self.assertIn("강한 섹터: XLY (경기소비재), XLI (산업재), XLK (기술)", core)
        self.assertIn("약한 섹터: XLE (에너지), XLU (유틸리티), XLC (커뮤니케이션)", core)
        self.assertIn("8) Top Movers +10 / -10", core)
        self.assertIn("10. G009", core)
        self.assertNotIn("11. G010", core)
        self.assertNotIn("9) 오늘 유리한 대응", core)
        self.assertNotIn("10) 오늘 피해야 할 대응", core)
        self.assertNotIn("11) 체크포인트", core)
        self.assertIn("9) 빠른 분석 대상", core)

        self.assertIn("[오늘 미국장 상세 브리핑]", detail)
        self.assertIn("breadth 요약: 상승 섹터 4/11, 확산 약함", detail)
        self.assertIn("3) Top Movers +30 / -30", detail)
        self.assertIn("30. G029", detail)
        self.assertNotIn("31. G030", detail)

    def test_detail_section_order_is_sector_theme_then_movers_only(self):
        payload = self._build_report_payload()
        detail = build_market_daily_briefing_messages(
            payload,
            run_at_kst=datetime(2026, 4, 16, 6, 15, 0),
            detail_limit=30,
            core_mover_limit=10,
            quick_target_limit=8,
        )[1]

        p1 = detail.index("1) 전체 섹터 순위")
        p2 = detail.index("2) 테마 묶음 요약")
        p3 = detail.index("3) Top Movers +30 / -30")
        self.assertTrue(p1 < p2 < p3)
        self.assertNotIn("4) 추가 인사이트", detail)
        self.assertNotIn("5) 다음 세션 트리거", detail)

    def test_core_10y_snapshot_uses_direct_percent_scale_when_raw_price_is_under_20(self):
        payload = self._build_report_payload()
        report = dict(payload["briefing_report"])
        report["macro"] = dict(report["macro"])
        report["macro"]["10Y"] = {"symbol": "10Y", "price": 4.2, "change_value": -0.06, "change_pct": -1.41}
        payload["briefing_report"] = report

        core = build_market_daily_briefing_messages(
            payload,
            run_at_kst=datetime(2026, 4, 16, 6, 15, 0),
            detail_limit=30,
            core_mover_limit=10,
            quick_target_limit=8,
        )[0]

        self.assertIn("- 10Y: 4.20% (-6.0bp)", core)
        self.assertIn("해석: 10Y -6.0bp -> 금리 부담 완화", core)

    def test_core_fear_greed_source_is_appended_when_present(self):
        payload = self._build_report_payload()
        report = dict(payload["briefing_report"])
        report["executive_summary"] = dict(report.get("executive_summary") or {})
        report["sentiment"] = dict(report.get("sentiment") or {})
        report["executive_summary"]["fear_greed_source"] = "proxy"
        report["sentiment"]["fear_greed_source"] = "proxy"
        payload["briefing_report"] = report

        core = build_market_daily_briefing_messages(
            payload,
            run_at_kst=datetime(2026, 4, 16, 6, 15, 0),
            detail_limit=30,
            core_mover_limit=10,
            quick_target_limit=8,
        )[0]

        self.assertIn("- 공포탐욕: 72/100 (탐욕, Proxy)", core)

    def test_core_avoids_duplicate_close_sentence(self):
        payload = self._build_report_payload()
        report = dict(payload["briefing_report"])
        report["session_flow"] = dict(report["session_flow"])
        report["session_flow"]["close"] = report["one_liner"]
        payload["briefing_report"] = report
        core = build_market_daily_briefing_messages(
            payload,
            run_at_kst=datetime(2026, 4, 16, 6, 15, 0),
            detail_limit=30,
            core_mover_limit=10,
            quick_target_limit=8,
        )[0]
        self.assertNotIn(f"- 마감: {report['one_liner']}", core)

    def test_detail_theme_section_shows_haedang_eopsum_when_empty(self):
        payload = self._build_report_payload()
        report = dict(payload["briefing_report"])
        report["theme_clusters"] = []
        payload["briefing_report"] = report
        detail = build_market_daily_briefing_messages(
            payload,
            run_at_kst=datetime(2026, 4, 16, 6, 15, 0),
            detail_limit=30,
            core_mover_limit=10,
            quick_target_limit=8,
        )[1]
        self.assertIn("2) 테마 묶음 요약", detail)
        self.assertIn("- 해당 없음", detail)

    def test_build_market_daily_briefing_text_keeps_single_string_contract(self):
        payload = self._build_report_payload()
        text = build_market_daily_briefing_text(
            payload,
            run_at_kst=datetime(2026, 4, 16, 6, 15, 0),
            detail_limit=30,
        )
        self.assertIn("[오늘 미국장 핵심 브리핑]", text)
        self.assertIn("[오늘 미국장 상세 브리핑]", text)

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
        messages = build_market_daily_briefing_messages(
            payload,
            run_at_kst=datetime(2026, 4, 16, 6, 15, 0),
            detail_limit=30,
            core_mover_limit=10,
            quick_target_limit=8,
        )
        self.assertEqual(len(messages), 1)
        self.assertIn("핵심 인사이트", messages[0])
        self.assertIn("섹터 강약도", messages[0])

    def test_split_telegram_message_text_chunks_long_text(self):
        raw = "\n".join([f"line-{idx:03d}-abcdefghijklmnopqrstuvwxyz" for idx in range(100)])
        chunks = split_telegram_message_text(raw, chunk_size=180)
        self.assertGreater(len(chunks), 1)
        self.assertEqual("\n".join(chunks), raw)
        self.assertTrue(all(len(chunk) <= 180 for chunk in chunks))

    def test_split_telegram_message_text_prefers_section_boundaries(self):
        raw = "\n".join(
            [
                "1) Section One",
                "A" * 50,
                "",
                "2) Section Two",
                "B" * 50,
                "",
                "3) Section Three",
                "C" * 50,
            ]
        )
        chunks = split_telegram_message_text(raw, chunk_size=95)
        self.assertGreaterEqual(len(chunks), 3)
        self.assertTrue(chunks[0].startswith("1) Section One"))
        self.assertTrue(any(chunk.startswith("2) Section Two") for chunk in chunks))
        self.assertTrue(any(chunk.startswith("3) Section Three") for chunk in chunks))
        self.assertEqual("\n".join(chunks), raw)

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
        self.assertIn("전체 CSV 전송은 계속 진행", text)


if __name__ == "__main__":
    unittest.main()
