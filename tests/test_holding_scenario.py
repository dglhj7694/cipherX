import math
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.holding_scenario import calculate_long_holding_scenario


def _scenario(**overrides):
    values = {
        "current_price": 110.0,
        "average_entry": 100.0,
        "quantity": 10.0,
        "user_stop_price": 95.0,
        "account_size": 10_000.0,
        "engine_invalidation_price": 96.0,
        "target_1": 120.0,
        "target_2": 130.0,
        "judgment": "BUY",
        "hard_conflict": False,
        "liquidity_risk": False,
        "price_available": True,
        "as_of": "2026-07-10",
    }
    values.update(overrides)
    return calculate_long_holding_scenario(**values)


class HoldingScenarioCalculationTests(unittest.TestCase):
    def test_profitable_holding_calculates_position_pnl_stop_and_targets(self):
        result = _scenario()

        self.assertTrue(result["valid"])
        self.assertEqual(result["scenario_code"], "HOLD_REVIEW")
        self.assertEqual(result["scenario_tone"], "positive")
        self.assertEqual(result["as_of"], "2026-07-10")
        self.assertEqual(result["cost_value"], 1_000.0)
        self.assertEqual(result["position_value"], 1_100.0)
        self.assertEqual(result["unrealized_pnl"], 100.0)
        self.assertEqual(result["unrealized_pnl_pct"], 10.0)
        self.assertEqual(result["position_pct"], 11.0)
        self.assertEqual(result["signed_distance_to_stop"], 15.0)
        self.assertEqual(result["distance_to_stop_pct"], 13.636)
        self.assertEqual(result["giveback_to_stop"], 150.0)
        self.assertEqual(result["pnl_at_stop"], -50.0)
        self.assertEqual(result["pnl_at_stop_pct"], -5.0)
        self.assertEqual(result["pnl_at_stop_pct_of_account"], -0.5)
        self.assertFalse(result["stop_triggered"])
        self.assertFalse(result["engine_invalidation_breached"])
        self.assertEqual(result["target_1_pnl"], 200.0)
        self.assertEqual(result["target_2_pnl"], 300.0)
        self.assertFalse(result["target_1_reached"])
        self.assertFalse(result["target_2_reached"])
        self.assertEqual(result["warnings"], [])

    def test_losing_holding_keeps_hold_review_but_uses_wait_tone(self):
        result = _scenario(
            current_price=90,
            user_stop_price=85,
            engine_invalidation_price=None,
            target_1=None,
            target_2=None,
        )

        self.assertTrue(result["valid"])
        self.assertEqual(result["scenario_code"], "HOLD_REVIEW")
        self.assertEqual(result["scenario_tone"], "wait")
        self.assertEqual(result["position_value"], 900.0)
        self.assertEqual(result["unrealized_pnl"], -100.0)
        self.assertEqual(result["unrealized_pnl_pct"], -10.0)
        self.assertEqual(result["giveback_to_stop"], 50.0)
        self.assertEqual(result["pnl_at_stop"], -150.0)
        self.assertEqual(result["pnl_at_stop_pct"], -15.0)
        self.assertIsNone(result["target_1_pnl"])
        self.assertIsNone(result["target_2_pnl"])

    def test_profitable_trailing_stop_above_average_entry_is_valid(self):
        result = _scenario(
            current_price=120,
            average_entry=100,
            quantity=10,
            user_stop_price=110,
            engine_invalidation_price=None,
            target_1=None,
            target_2=None,
        )

        self.assertTrue(result["valid"])
        self.assertEqual(result["scenario_code"], "HOLD_REVIEW")
        self.assertFalse(result["stop_triggered"])
        self.assertEqual(result["giveback_to_stop"], 100.0)
        self.assertEqual(result["pnl_at_stop"], 100.0)
        self.assertEqual(result["pnl_at_stop_pct"], 10.0)

    def test_stop_at_current_price_has_highest_priority(self):
        result = _scenario(
            current_price=95,
            user_stop_price=95,
            engine_invalidation_price=100,
            judgment="SELL",
            hard_conflict=True,
            liquidity_risk=True,
        )

        self.assertTrue(result["valid"])
        self.assertEqual(result["scenario_code"], "STOP_REACHED")
        self.assertEqual(result["scenario_reasons"], ["사용자 방어 기준 도달"])
        self.assertTrue(result["stop_triggered"])
        self.assertEqual(result["signed_distance_to_stop"], 0.0)
        self.assertEqual(result["distance_to_stop_pct"], 0.0)
        self.assertEqual(result["giveback_to_stop"], 0.0)
        self.assertTrue(result["engine_invalidation_breached"])

    def test_price_below_stop_reports_signed_breach_without_negative_giveback(self):
        result = _scenario(
            current_price=94,
            user_stop_price=95,
            engine_invalidation_price=None,
            target_1=None,
            target_2=None,
        )

        self.assertTrue(result["valid"])
        self.assertEqual(result["scenario_code"], "STOP_REACHED")
        self.assertEqual(result["signed_distance_to_stop"], -1.0)
        self.assertEqual(result["distance_to_stop_pct"], -1.064)
        self.assertEqual(result["giveback_to_stop"], 0.0)

    def test_defensive_reasons_are_aggregated_without_overwriting_user_stop(self):
        result = _scenario(
            current_price=100,
            user_stop_price=90,
            engine_invalidation_price=105,
            judgment=" watch_sell ",
            hard_conflict=True,
            liquidity_risk=True,
            target_1=None,
            target_2=None,
        )

        self.assertTrue(result["valid"])
        self.assertEqual(result["scenario_code"], "DEFEND_REVIEW")
        self.assertEqual(
            result["scenario_reasons"],
            [
                "현재 엔진 판단 WATCH_SELL",
                "분석 엔진 무효화 기준 이탈",
                "매수·매도 신호 충돌",
                "얇은 거래대금",
            ],
        )
        self.assertEqual(result["user_stop_price"], 90.0)
        self.assertEqual(result["engine_invalidation_price"], 105.0)
        self.assertFalse(result["stop_triggered"])
        self.assertTrue(result["engine_invalidation_breached"])

    def test_sell_judgment_takes_priority_over_missing_stop(self):
        result = _scenario(
            user_stop_price=None,
            engine_invalidation_price=None,
            judgment="SELL",
            target_1=None,
            target_2=None,
        )

        self.assertTrue(result["valid"])
        self.assertEqual(result["scenario_code"], "DEFEND_REVIEW")
        self.assertIn("현재 엔진 판단 SELL", result["scenario_reasons"])
        self.assertIsNone(result["user_stop_price"])

    def test_missing_user_stop_still_calculates_pnl_but_hides_stop_metrics(self):
        result = _scenario(
            user_stop_price=None,
            engine_invalidation_price=None,
            target_1=None,
            target_2=None,
        )

        self.assertTrue(result["valid"])
        self.assertEqual(result["scenario_code"], "NO_STOP_SET")
        self.assertEqual(result["scenario_reasons"], ["사용자 방어 기준 미설정"])
        self.assertEqual(result["unrealized_pnl"], 100.0)
        for key in (
            "user_stop_price",
            "signed_distance_to_stop",
            "distance_to_stop_pct",
            "giveback_to_stop",
            "pnl_at_stop",
            "pnl_at_stop_pct",
            "pnl_at_stop_pct_of_account",
        ):
            self.assertIsNone(result[key], key)
        self.assertFalse(result["stop_triggered"])

    def test_optional_account_omits_portfolio_percentages(self):
        result = _scenario(account_size=None)

        self.assertTrue(result["valid"])
        self.assertIsNone(result["position_pct"])
        self.assertIsNone(result["pnl_at_stop_pct_of_account"])
        self.assertEqual(result["position_value"], 1_100.0)
        self.assertEqual(result["unrealized_pnl"], 100.0)

    def test_fractional_quantity_is_preserved_without_rounding_to_whole_shares(self):
        result = _scenario(
            current_price=12,
            average_entry=10,
            quantity=0.5,
            user_stop_price=9,
            account_size=None,
            engine_invalidation_price=None,
            target_1=None,
            target_2=None,
        )

        self.assertTrue(result["valid"])
        self.assertEqual(result["quantity"], 0.5)
        self.assertEqual(result["cost_value"], 5.0)
        self.assertEqual(result["position_value"], 6.0)
        self.assertEqual(result["unrealized_pnl"], 1.0)
        self.assertEqual(result["giveback_to_stop"], 1.5)
        self.assertEqual(result["pnl_at_stop"], -0.5)

    def test_target_progress_and_target_pnl_are_reported_independently(self):
        result = _scenario(
            current_price=125,
            average_entry=100,
            quantity=4,
            user_stop_price=90,
            engine_invalidation_price=None,
            target_1=120,
            target_2=130,
        )

        self.assertTrue(result["valid"])
        self.assertTrue(result["target_1_reached"])
        self.assertFalse(result["target_2_reached"])
        self.assertEqual(result["target_1_pnl"], 80.0)
        self.assertEqual(result["target_2_pnl"], 120.0)
        self.assertTrue(any("1차 목표 이상" in warning for warning in result["warnings"]))
        self.assertFalse(any("2차 목표 이상" in warning for warning in result["warnings"]))

    def test_position_over_account_and_missing_as_of_add_warnings(self):
        result = _scenario(
            current_price=100,
            average_entry=90,
            quantity=20,
            user_stop_price=80,
            account_size=1_000,
            engine_invalidation_price=None,
            target_1=None,
            target_2=None,
            as_of="",
        )

        self.assertTrue(result["valid"])
        self.assertEqual(result["position_pct"], 200.0)
        self.assertIn("입력 계좌금액보다 현재 포지션 평가금액이 큽니다.", result["warnings"])
        self.assertIn("분석 가격 기준일을 확인할 수 없습니다.", result["warnings"])

    def test_price_unavailable_fails_closed_and_preserves_as_of(self):
        result = _scenario(price_available=False, as_of="2026-07-09")

        self.assertFalse(result["valid"])
        self.assertEqual(result["scenario_code"], "PRICE_UNAVAILABLE")
        self.assertEqual(result["scenario_title"], "가격 확인 후 재점검")
        self.assertEqual(result["as_of"], "2026-07-09")
        self.assertIn("유효하지 않아", result["reason"])

    def test_required_values_reject_zero_negative_non_numeric_and_non_finite(self):
        cases = [
            ("current_price", 0, "현재가"),
            ("current_price", -1, "현재가"),
            ("current_price", "not-a-price", "현재가"),
            ("average_entry", math.nan, "평균단가"),
            ("average_entry", math.inf, "평균단가"),
            ("quantity", 0, "보유 수량"),
            ("quantity", -0.5, "보유 수량"),
        ]
        for field, value, label in cases:
            with self.subTest(field=field, value=value):
                result = _scenario(**{field: value})
                self.assertFalse(result["valid"])
                self.assertEqual(result["scenario_code"], "INVALID_INPUT")
                self.assertIn(label, result["reason"])

    def test_optional_values_reject_invalid_values_when_supplied(self):
        cases = [
            ("user_stop_price", 0, "사용자 방어 기준"),
            ("account_size", -1, "계좌 평가금액"),
            ("engine_invalidation_price", math.nan, "엔진 무효화 기준"),
            ("target_1", math.inf, "1차 목표"),
            ("target_2", "bad", "2차 목표"),
        ]
        for field, value, label in cases:
            with self.subTest(field=field, value=value):
                result = _scenario(**{field: value})
                self.assertFalse(result["valid"])
                self.assertEqual(result["scenario_code"], "INVALID_INPUT")
                self.assertIn(label, result["reason"])

    def test_second_target_below_first_is_omitted_without_hiding_holding_pnl(self):
        result = _scenario(target_1=130, target_2=120)

        self.assertTrue(result["valid"])
        self.assertEqual(result["unrealized_pnl"], 100.0)
        self.assertEqual(result["target_1"], 130.0)
        self.assertIsNone(result["target_2"])
        self.assertTrue(any("2차 목표 시나리오는 제외" in warning for warning in result["warnings"]))

    def test_blank_optional_values_are_treated_as_missing(self):
        result = _scenario(
            user_stop_price=" ",
            account_size="",
            engine_invalidation_price=" ",
            target_1="",
            target_2=" ",
        )

        self.assertTrue(result["valid"])
        self.assertEqual(result["scenario_code"], "NO_STOP_SET")
        self.assertIsNone(result["position_pct"])
        self.assertIsNone(result["engine_invalidation_price"])
        self.assertIsNone(result["target_1"])
        self.assertIsNone(result["target_2"])

    def test_required_arithmetic_overflow_fails_closed(self):
        result = _scenario(
            current_price=1e308,
            average_entry=1e308,
            quantity=1e308,
            user_stop_price=None,
            account_size=None,
            engine_invalidation_price=None,
            target_1=None,
            target_2=None,
        )

        self.assertFalse(result["valid"])
        self.assertEqual(result["scenario_code"], "INVALID_INPUT")
        self.assertIn("범위가 너무 커", result["reason"])

    def test_optional_scenario_arithmetic_overflow_fails_closed(self):
        result = _scenario(
            current_price=1,
            average_entry=1,
            quantity=1e200,
            user_stop_price=None,
            account_size=None,
            engine_invalidation_price=None,
            target_1=1e200,
            target_2=None,
        )

        self.assertFalse(result["valid"])
        self.assertEqual(result["scenario_code"], "INVALID_INPUT")
        self.assertIn("방어 시나리오", result["reason"])


if __name__ == "__main__":
    unittest.main()
