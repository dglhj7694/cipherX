import json
import unittest

import pandas as pd

from ai_agent import build_ai_prompt, build_prompt_text, parse_ai_signal_assisted_response
from ai_report import (
    attach_ai_result_to_analysis_message,
    build_ai_report_message,
    format_ai_signal_report,
    format_ai_signal_report_html,
)
from services.ai_signal_service import generate_ai_signal_assisted, mask_secret, resolve_ai_key


def make_prompt_frame():
    index = pd.date_range("2026-01-01", periods=65, freq="D")
    rows = []
    for i, _ in enumerate(index):
        close = 100 + i * 0.4
        rows.append(
            {
                "Open": close - 0.3,
                "High": close + 1.1,
                "Low": close - 1.2,
                "Close": close,
                "Volume": 1_000_000 + i * 10_000,
                "HMA": close - 0.5,
                "RSI": 48 + i * 0.1,
                "MFI": 52 + i * 0.1,
                "WT1": -10 + i * 0.2,
                "WT2": -11 + i * 0.2,
                "MACD_Hist": -0.1 + i * 0.005,
                "ADX": 18 + i * 0.1,
                "ATR": 3.2,
                "Percent_B": 0.45 + i * 0.002,
                "ROC": 0.2,
                "Volume_Ratio_20": 1.25,
                "Volume_Ratio_50": 1.12,
                "Volume_Oscillator": 4.5,
                "Dollar_Volume_20": 125_000_000,
                "MACD_Line": 0.15,
                "MACD_Signal": 0.11,
                "MACD_Accel": 0.03,
                "SlowK": 32.0,
                "SlowD": 29.0,
                "Squeeze_On": i % 7 == 0,
                "Squeeze_Momentum": 0.45 + i * 0.01,
                "Squeeze_Mom_Rising": True,
                "CMF": 0.08,
                "Chaikin_Oscillator": 1.4,
                "OBV": 5_000_000 + i * 25_000,
                "OBV_Slope": 0.18,
                "AD_Line": 2_000_000 + i * 15_000,
                "Plus_DI": 28.0,
                "Minus_DI": 17.0,
                "VWAP": close - 0.8,
                "VWAP_Osc": 0.65,
                "Fixed_VWAP": close - 2.1,
                "Ichimoku_Tenkan": close - 1.0,
                "Ichimoku_Kijun": close - 2.0,
                "Mass_Index": 24.3,
                "RS_Ratio": 1.08,
                "Price_Slope_5": 0.024,
                "Composite_Accel": 1.7,
                "MA20_ATR_Gap": 0.9,
                "Channel_Position": 0.62,
                "UTBot_Dir": 1,
                "UTBot_Stop": close - 3.2,
                "VP_POC": close - 1.3,
                "VP_VAH": close + 2.8,
                "VP_VAL": close - 4.0,
                "VP_Long_RR": 2.2,
                "Fib_382": close - 2.0,
                "Fib_50": close - 3.4,
                "Fib_618": close - 4.8,
                "EMA12": close - 0.4,
                "EMA26": close - 1.1,
                "Trendline_Dist_ATR": 0.35,
                "Trendline_Slope_Pct": 0.42,
                "Objective_Buy_Score": 99,
                "Objective_Judgment": "STRONG_BUY",
            }
        )
    return pd.DataFrame(rows, index=index)


def make_meta():
    return {
        "ticker": "MU",
        "price": 128.4,
        "price_change_pct": 3.21,
        "judgment": "WATCH_BUY",
        "action_label": "매수 관심",
        "confidence": 72,
        "ensemble_score": 13.5,
        "buy_agree": 5,
        "sell_agree": 1,
        "context_label": "상승 전환",
        "judgment_reason": "전환 신호와 거래량이 동시에 개선되었습니다.",
        "leading_verdict": "선행 신호 우위",
        "lagging_verdict": "후행 확인 대기",
        "rsi": 54.2,
        "mfi": 57.1,
        "wt1": 3.5,
        "macd_hist": 0.04,
        "adx": 24.8,
        "atr_pct": 4.6,
        "volume_ratio_20": 1.82,
        "dollar_volume_20": 125_000_000,
        "cmf": 0.08,
        "recent_signals": [
            {"date": "04/20", "dir": "buy", "key": "UTBot_Buy", "label": "UTBot Buy"},
            {"date": "04/21", "dir": "buy", "key": "TK_Cross_Bull", "label": "TK Cross Bull"},
        ],
        "combined_scans": [
            {"kor": "CS Trend Buy", "dir": "buy", "tier": 1, "is_today": True, "score": 88},
        ],
        "strategy_summary": {
            "conflict_level": "LOW",
            "top_strategy": {
                "label": "Breakout Confirmation",
                "direction": "LONG",
                "score": 84,
                "status": "ACTIVE",
                "entry_price": 128.5,
                "stop_loss": 122.0,
                "target_1": 136.0,
            },
        },
        "veto_flags": "",
        "risk_flags": ["추격 주의"],
    }


class PromptTapeTests(unittest.TestCase):
    def test_prompt_tape_contains_current_analysis_context(self):
        prompt_tape = build_prompt_text(make_prompt_frame(), make_meta())

        self.assertIn("# PROMPT TAPE", prompt_tape)
        self.assertIn("ticker=MU", prompt_tape)
        self.assertIn("price=128.40", prompt_tape)
        self.assertIn("RSI=", prompt_tape)
        self.assertIn("MACD_Hist=", prompt_tape)
        self.assertIn("ADX=", prompt_tape)
        self.assertIn("Volume_Ratio_20=", prompt_tape)
        self.assertIn("Vol[", prompt_tape)
        self.assertIn("WaveTrend[", prompt_tape)
        self.assertIn("SqueezeMom[", prompt_tape)
        self.assertIn("VP/POC/RR[", prompt_tape)
        self.assertIn("Trendline/Pattern[", prompt_tape)
        self.assertIn("시장/상대강도", prompt_tape)
        self.assertIn("최근 60봉 보조지표 테이프", prompt_tape)

        self.assertNotIn("WATCH_BUY", prompt_tape)
        self.assertNotIn("매수 관심", prompt_tape)
        self.assertNotIn("ES=", prompt_tape)
        self.assertNotIn("buy:sell", prompt_tape)
        self.assertNotIn("UTBot Buy", prompt_tape)
        self.assertNotIn("TK Cross Bull", prompt_tape)
        self.assertNotIn("CS Trend Buy", prompt_tape)
        self.assertNotIn("Breakout Confirmation", prompt_tape)
        self.assertNotIn("추격 주의", prompt_tape)
        self.assertNotIn("Objective_Buy_Score", prompt_tape)
        self.assertNotIn("Objective_Judgment", prompt_tape)
        self.assertNotIn("STRONG_BUY", prompt_tape)

    def test_ai_prompt_declares_json_only_schema_and_allowed_styles(self):
        ai_prompt = build_ai_prompt("MU", "PROMPT TAPE BODY")

        self.assertIn("JSON 객체만 반환", ai_prompt)
        self.assertIn("검증된 보조지표", ai_prompt)
        self.assertIn("엔진의 판단, 점수, 전략 후보, 시그널 라벨", ai_prompt)
        self.assertIn("STRONG_BUY", ai_prompt)
        self.assertIn("WATCH_SELL", ai_prompt)
        self.assertIn("초단타", ai_prompt)
        self.assertIn("눌림목 되돌림", ai_prompt)
        self.assertIn("PROMPT TAPE BODY", ai_prompt)

    def test_parser_handles_plain_json_fenced_json_and_bad_json(self):
        payload = {
            "AI_Judgment": "BUY",
            "AI_Confidence": 78,
            "AI_Bullish_Score": 74,
            "AI_Bearish_Score": 22,
            "AI_Risk_Flags": ["당일 급등"],
            "AI_Key_Drivers": ["거래량 증가", "전환 신호"],
            "AI_Evidence_Details": [
                {
                    "category": "수급/거래량",
                    "observation": "Volume_Ratio_20=1.82로 20일 평균 대비 거래량이 증가",
                    "interpretation": "가격 상승이 거래량 확인을 동반합니다.",
                    "impact": "bullish",
                    "importance": 82,
                },
                {
                    "category": "모멘텀",
                    "observation": "MACD_Hist가 플러스권으로 전환",
                    "interpretation": "단기 모멘텀 개선 신호입니다.",
                    "impact": "bullish",
                    "importance": 70,
                },
            ],
            "AI_Counter_Evidence": ["ATR%가 높아 변동성 부담이 있습니다."],
            "AI_Data_Limits": ["뉴스와 실적 데이터는 포함되지 않았습니다."],
            "AI_Reason": "전환 신호가 누적됐습니다.",
            "AI_Trade_Strategy": "분할 진입이 적절합니다.",
            "AI_Entry_Plan": "128 돌파 후 유지",
            "AI_Invalidation": "122 이탈",
            "AI_Target_Plan": "136 부근 분할청산",
            "AI_Strategy_Playbook": [
                {
                    "style": "스윙",
                    "fit": 82,
                    "summary": "전환 확인 후 접근",
                    "entry": "128 돌파",
                    "invalidation": "122 이탈",
                    "target": "136",
                }
            ],
        }

        plain = parse_ai_signal_assisted_response(json.dumps(payload, ensure_ascii=False), engine_judgment="WATCH_BUY")
        fenced = parse_ai_signal_assisted_response(
            "```json\n" + json.dumps(payload, ensure_ascii=False) + "\n```",
            engine_judgment="WATCH_BUY",
        )
        bad = parse_ai_signal_assisted_response("not json", engine_judgment="WATCH_BUY")

        self.assertTrue(plain["available"])
        self.assertEqual(plain["AI_Judgment"], "BUY")
        self.assertEqual(plain["AI_Evidence_Details"][0]["category"], "수급/거래량")
        self.assertEqual(plain["AI_Evidence_Details"][0]["impact"], "bullish")
        self.assertEqual(plain["AI_Evidence_Details"][0]["importance"], 82)
        self.assertIn("ATR%", plain["AI_Counter_Evidence"][0])
        self.assertIn("뉴스", plain["AI_Data_Limits"][0])
        self.assertEqual(plain["AI_Strategy_Playbook"][0]["style"], "스윙")
        self.assertTrue(fenced["available"])
        self.assertFalse(bad["available"])
        self.assertIn("JSON", bad["AI_Reason"])


class AiSignalServiceTests(unittest.TestCase):
    def test_key_resolution_and_masking(self):
        self.assertEqual(mask_secret(""), "미설정")
        self.assertEqual(mask_secret("abcd1234efgh"), "abcd...efgh")
        self.assertEqual(resolve_ai_key("runtime", "configured", False).source, "세션 입력")
        self.assertEqual(resolve_ai_key("", "configured", True).source, "secret")
        self.assertEqual(resolve_ai_key("", "configured", False).source, "환경변수")

    def test_generate_without_key_returns_unavailable_result(self):
        result = generate_ai_signal_assisted(
            runtime_key="",
            configured_key="",
            configured_from_secrets=False,
            prompt="PROMPT",
            engine_judgment="BUY",
            parser=lambda raw, engine_judgment="": {"available": True},
        )

        self.assertFalse(result["available"])
        self.assertIn("Gemini API 키", result["AI_Reason"])

    def test_generate_uses_fake_client_and_parser(self):
        class FakeResponse:
            text = '{"AI_Judgment":"BUY"}'

        class FakeClient:
            def generate_content(self, prompt):
                self.prompt = prompt
                return FakeResponse()

        def parser(raw, engine_judgment=""):
            return {"available": True, "raw": raw, "engine": engine_judgment}

        result = generate_ai_signal_assisted(
            runtime_key="runtime-key",
            configured_key="",
            configured_from_secrets=False,
            prompt="PROMPT",
            engine_judgment="WATCH_BUY",
            parser=parser,
            client_factory=lambda key: FakeClient(),
        )

        self.assertTrue(result["available"])
        self.assertEqual(result["raw"], '{"AI_Judgment":"BUY"}')
        self.assertEqual(result["engine"], "WATCH_BUY")

    def test_generate_exception_returns_unavailable_result(self):
        result = generate_ai_signal_assisted(
            runtime_key="runtime-key",
            configured_key="",
            configured_from_secrets=False,
            prompt="PROMPT",
            engine_judgment="BUY",
            parser=lambda raw, engine_judgment="": {"available": True},
            client_factory=lambda key: (_ for _ in ()).throw(RuntimeError("boom")),
        )

        self.assertFalse(result["available"])
        self.assertIn("오류", result["AI_Reason"])


class AiReportTests(unittest.TestCase):
    def test_report_markdown_and_payload_contract(self):
        ai_result = {
            "available": True,
            "AI_Judgment": "BUY",
            "AI_Confidence": 78,
            "AI_Bullish_Score": 74,
            "AI_Bearish_Score": 22,
            "AI_Risk_Flags": ["당일 급등"],
            "AI_Key_Drivers": ["거래량 증가"],
            "AI_Evidence_Details": [
                {
                    "category": "수급/거래량",
                    "observation": "Volume_Ratio_20=1.82",
                    "interpretation": "거래량이 동반된 상승입니다.",
                    "impact": "bullish",
                    "importance": 82,
                }
            ],
            "AI_Counter_Evidence": ["ATR% 4.6으로 변동성이 있습니다."],
            "AI_Data_Limits": ["보조지표 기반 판단입니다."],
            "AI_Reason": "전환 신호가 누적됐습니다.",
            "AI_Trade_Strategy": "분할 진입이 적절합니다.",
            "AI_Entry_Plan": "128 돌파 후 유지",
            "AI_Invalidation": "122 이탈",
            "AI_Target_Plan": "136 부근",
            "AI_Agreement": "ALIGNED",
            "AI_Disagreement_Type": "TIMING",
            "AI_Strategy_Playbook": [
                {
                    "style": "스윙",
                    "fit": 82,
                    "summary": "전환 확인",
                    "entry": "128 돌파",
                    "invalidation": "122 이탈",
                    "target": "136",
                }
            ],
        }

        content = format_ai_signal_report("MU", ai_result, engine_judgment="WATCH_BUY", generated_at="2026-05-12T09:30:00")
        html_content = format_ai_signal_report_html(
            "MU",
            ai_result,
            engine_judgment="WATCH_BUY",
            generated_at="2026-05-12T09:30:00",
        )
        message = build_ai_report_message(
            ticker="MU",
            ai_result=ai_result,
            source_analysis_index=3,
            engine_judgment="WATCH_BUY",
            generated_at="2026-05-12T09:30:00",
        )

        self.assertIn("MU AI분석 리포트", content)
        self.assertIn("상세 근거", content)
        self.assertIn("Volume_Ratio_20=1.82", content)
        self.assertIn("반대 근거", content)
        self.assertIn("데이터 한계", content)
        self.assertIn("sigl-ai-report", html_content)
        self.assertIn("AI분석 리포트", html_content)
        self.assertIn("상세 근거", html_content)
        self.assertIn("Volume_Ratio_20=1.82", html_content)
        self.assertIn("반대 근거", html_content)
        self.assertIn("데이터 한계", html_content)
        self.assertIn("진입", html_content)
        self.assertIn("AI분석 리포트", message["content"])
        self.assertEqual(message["type"], "report")
        self.assertEqual(message["ticker"], "MU")
        self.assertEqual(message["source_analysis_index"], 3)
        self.assertEqual(message["engine_judgment"], "WATCH_BUY")
        self.assertEqual(message["ai_result"]["AI_Judgment"], "BUY")

    def test_attach_ai_result_updates_meta_without_mutating_original(self):
        original = {"type": "analysis", "ticker": "MU", "meta": {"judgment": "BUY"}}
        updated = attach_ai_result_to_analysis_message(original, {"available": True, "AI_Judgment": "BUY"})

        self.assertNotIn("ai_signal_assisted", original["meta"])
        self.assertEqual(updated["meta"]["ai_signal_assisted"]["AI_Judgment"], "BUY")


if __name__ == "__main__":
    unittest.main()
