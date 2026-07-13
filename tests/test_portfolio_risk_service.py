import copy
import math
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.portfolio_risk_service import calculate_portfolio_risk_summary, inspect_portfolio_risk_plans
from services.trade_plan_service import encode_trade_plan_bundle, update_trade_plan_status
from tests.test_trade_plan_service import _entry_plan, _guide, _holding_plan


ENTRY_ID_2 = "22345678-1234-4234-8234-123456789abc"
HOLDING_ID = "32345678-1234-4234-8234-123456789abc"
HOLDING_ID_2 = "42345678-1234-4234-8234-123456789abc"


def _holding_confirmation(**overrides):
    values = {
        "confirmed": True,
        "average_entry": 40.0,
        "quantity": 20.0,
        "current_price": 50.0,
        "user_stop_price": 45.0,
    }
    values.update(overrides)
    return values


def _calculate(plans, **overrides):
    values = {
        "source_currency_hint": "계좌 통화",
        "currency_code": "USD",
        "currency_confirmed": True,
        "account_size": 10_000.0,
        "selected_entry_ids": [],
        "holding_confirmations": {},
        "multiple_entry_tickers_confirmed": [],
        "include_combined_scenario": False,
        "completeness_confirmed": True,
        "max_total_risk_pct": 3.0,
        "max_total_exposure_pct": 100.0,
        "max_single_ticker_exposure_pct": 50.0,
    }
    values.update(overrides)
    return calculate_portfolio_risk_summary(plans, **values)


class PortfolioRiskInspectionTests(unittest.TestCase):
    def test_inspection_separates_currency_status_and_plan_type_without_mutation(self):
        entry = _entry_plan()["plan"]
        holding = _holding_plan(plan_id=HOLDING_ID)["plan"]
        before = copy.deepcopy([entry, holding])

        result = inspect_portfolio_risk_plans([entry, holding])

        self.assertTrue(result["valid"], result.get("reason"))
        self.assertEqual(result["inspection"]["currencies"], ["계좌 통화"])
        self.assertEqual([row["plan_type"] for row in result["inspection"]["candidates"]], ["ENTRY_LONG", "HOLDING_LONG"])
        self.assertTrue(all(row["selectable"] for row in result["inspection"]["candidates"]))
        self.assertEqual([entry, holding], before)

    def test_inspection_rejects_invalid_or_duplicate_ids_atomically(self):
        plan = _entry_plan()["plan"]
        invalid = copy.deepcopy(plan)
        invalid["fingerprint"] = "sha256:" + "0" * 64

        bad = inspect_portfolio_risk_plans([plan, invalid])
        duplicate = inspect_portfolio_risk_plans([plan, copy.deepcopy(plan)])

        self.assertFalse(bad["valid"])
        self.assertEqual(bad["errors"][0]["code"], "INVALID_TRADE_PLAN")
        self.assertFalse(duplicate["valid"])
        self.assertEqual(duplicate["errors"][0]["code"], "DUPLICATE_PLAN_ID")


class PortfolioRiskCalculationTests(unittest.TestCase):
    def test_holding_and_entry_are_separate_and_combined_only_after_explicit_confirmation(self):
        entry = _entry_plan()["plan"]
        holding = _holding_plan(plan_id=HOLDING_ID)["plan"]
        plans = [entry, holding]

        separate = _calculate(
            plans,
            selected_entry_ids=[entry["plan_id"]],
            holding_confirmations={holding["plan_id"]: _holding_confirmation()},
        )
        combined = _calculate(
            plans,
            selected_entry_ids=[entry["plan_id"]],
            holding_confirmations={holding["plan_id"]: _holding_confirmation()},
            include_combined_scenario=True,
        )

        self.assertTrue(separate["valid"], separate.get("reason"))
        self.assertEqual(separate["summary"]["holding"]["exposure"], 1_000.0)
        self.assertEqual(separate["summary"]["holding"]["giveback_to_stop"], 100.0)
        self.assertEqual(separate["summary"]["pending_entry"]["exposure"], 2_000.0)
        self.assertEqual(separate["summary"]["pending_entry"]["risk_at_stop"], 100.0)
        self.assertIsNone(separate["summary"]["combined_scenario"])
        self.assertEqual(separate["summary"]["decision_code"], "COMBINED_SCENARIO_NOT_CONFIRMED")
        self.assertEqual(
            {row["scope"] for row in separate["summary"]["ticker_rows"]},
            {"HOLDING", "PENDING_ENTRY"},
        )

        self.assertEqual(combined["summary"]["combined_scenario"]["exposure"], 3_000.0)
        self.assertEqual(combined["summary"]["combined_scenario"]["risk_at_stop"], 200.0)
        self.assertEqual(combined["summary"]["combined_scenario"]["exposure_pct_of_account"], 30.0)
        self.assertEqual(combined["summary"]["combined_scenario"]["risk_pct_of_account"], 2.0)
        self.assertEqual(combined["summary"]["decision_code"], "WITHIN_USER_LIMITS")
        self.assertEqual(combined["summary"]["ticker_rows"][0]["exposure_pct_of_account"], 30.0)

    def test_combined_risk_over_user_limit_is_flagged(self):
        entry = _entry_plan()["plan"]
        holding = _holding_plan(plan_id=HOLDING_ID)["plan"]

        result = _calculate(
            [entry, holding],
            selected_entry_ids=[entry["plan_id"]],
            holding_confirmations={holding["plan_id"]: _holding_confirmation()},
            include_combined_scenario=True,
            max_total_risk_pct=1.5,
        )

        self.assertTrue(result["valid"])
        self.assertEqual(result["summary"]["decision_code"], "OVER_USER_LIMIT")
        self.assertEqual(result["summary"]["limits"]["risk_budget"], 150.0)
        self.assertEqual(result["summary"]["limits"]["remaining_risk_budget"], -50.0)
        self.assertTrue(any(item["code"] == "TOTAL_RISK" for item in result["summary"]["limit_breaches"]))

    def test_entry_quantity_is_recalculated_from_current_account_and_saved_quantity_is_not_trusted(self):
        entry = _entry_plan(include_quantity=True, planned_quantity=20, account_size=10_000)["plan"]

        result = _calculate(
            [entry],
            account_size=5_000,
            selected_entry_ids=[entry["plan_id"]],
        )

        self.assertTrue(result["valid"], result.get("reason"))
        row = result["summary"]["entry_rows"][0]
        self.assertEqual(row["stored_quantity_ignored"], 20)
        self.assertEqual(row["quantity"], 10)
        self.assertEqual(row["exposure"], 1_000.0)
        self.assertEqual(row["risk_at_stop"], 50.0)

    def test_entry_recalculation_requires_account_and_at_least_one_current_share(self):
        entry = _entry_plan(include_quantity=True, planned_quantity=20, account_size=10_000)["plan"]

        no_account = _calculate(
            [entry],
            account_size=None,
            selected_entry_ids=[entry["plan_id"]],
        )
        under_one_share = _calculate(
            [entry],
            account_size=99,
            selected_entry_ids=[entry["plan_id"]],
        )

        self.assertFalse(no_account["valid"])
        self.assertEqual(no_account["errors"][0]["code"], "ACCOUNT_REQUIRED")
        self.assertFalse(under_one_share["valid"])
        self.assertEqual(under_one_share["errors"][0]["code"], "ENTRY_RECALCULATION_FAILED")

    def test_holding_uses_current_confirmed_values_and_separates_locked_profit(self):
        holding = _holding_plan(plan_id=HOLDING_ID)["plan"]

        result = _calculate(
            [holding],
            holding_confirmations={
                holding["plan_id"]: _holding_confirmation(
                    average_entry=100,
                    quantity=10,
                    current_price=120,
                    user_stop_price=110,
                )
            },
        )

        self.assertTrue(result["valid"], result.get("reason"))
        row = result["summary"]["holding_rows"][0]
        self.assertEqual(row["exposure"], 1_200.0)
        self.assertEqual(row["giveback_to_stop"], 100.0)
        self.assertEqual(row["capital_loss_at_stop"], 0.0)
        self.assertEqual(row["locked_profit_at_stop"], 100.0)

    def test_stop_reached_is_urgent_and_can_never_report_within_limit(self):
        holding = _holding_plan(plan_id=HOLDING_ID)["plan"]

        result = _calculate(
            [holding],
            holding_confirmations={
                holding["plan_id"]: _holding_confirmation(current_price=44, user_stop_price=45)
            },
        )

        self.assertTrue(result["valid"], result.get("reason"))
        self.assertEqual(result["summary"]["decision_code"], "STOP_REVIEW_REQUIRED")
        self.assertEqual(result["summary"]["holding"]["urgent_count"], 1)
        self.assertEqual(result["summary"]["holding"]["quantified_count"], 0)
        self.assertEqual(result["summary"]["holding"]["exposure"], 880.0)
        self.assertIsNone(result["summary"]["holding"]["giveback_to_stop"])
        self.assertFalse(result["summary"]["holding"]["risk_complete"])
        self.assertEqual(result["summary"]["ticker_rows"][0]["exposure"], 880.0)
        self.assertIsNone(result["summary"]["ticker_rows"][0]["risk_at_stop"])
        self.assertIsNone(result["summary"]["limits"]["remaining_risk_budget"])

    def test_ticker_concentration_is_separate_until_combined_scenario_is_confirmed(self):
        entry = _entry_plan()["plan"]
        holding = _holding_plan(plan_id=HOLDING_ID)["plan"]
        values = {
            "selected_entry_ids": [entry["plan_id"]],
            "holding_confirmations": {holding["plan_id"]: _holding_confirmation()},
            "max_single_ticker_exposure_pct": 25.0,
        }

        separate = _calculate([entry, holding], **values)
        combined = _calculate([entry, holding], include_combined_scenario=True, **values)

        self.assertEqual(separate["summary"]["decision_code"], "COMBINED_SCENARIO_NOT_CONFIRMED")
        self.assertFalse(
            any(item["code"] == "TICKER_EXPOSURE" for item in separate["summary"]["limit_breaches"])
        )
        self.assertEqual(combined["summary"]["decision_code"], "OVER_USER_LIMIT")
        breach = next(
            item for item in combined["summary"]["limit_breaches"] if item["code"] == "TICKER_EXPOSURE"
        )
        self.assertEqual(breach["scope"], "COMBINED")
        self.assertEqual(breach["actual_pct"], 30.0)

    def test_each_separate_scenario_is_checked_even_without_combined_confirmation(self):
        entry = _entry_plan()["plan"]
        holding = _holding_plan(plan_id=HOLDING_ID)["plan"]

        result = _calculate(
            [entry, holding],
            selected_entry_ids=[entry["plan_id"]],
            holding_confirmations={holding["plan_id"]: _holding_confirmation()},
            max_total_risk_pct=0.5,
        )

        self.assertEqual(result["summary"]["decision_code"], "OVER_USER_LIMIT")
        scopes = {
            item["scope"]
            for item in result["summary"]["limit_breaches"]
            if item["code"] == "TOTAL_RISK"
        }
        self.assertEqual(scopes, {"HOLDING", "PENDING_ENTRY"})

    def test_combined_request_requires_both_holding_and_entry(self):
        entry = _entry_plan()["plan"]

        result = _calculate(
            [entry],
            selected_entry_ids=[entry["plan_id"]],
            include_combined_scenario=True,
        )

        self.assertFalse(result["valid"])
        self.assertEqual(result["errors"][0]["code"], "COMBINED_SCENARIO_UNAVAILABLE")

    def test_duplicate_holding_is_blocked_and_duplicate_entry_requires_explicit_simultaneous_confirmation(self):
        holding_1 = _holding_plan(plan_id=HOLDING_ID)["plan"]
        holding_2 = _holding_plan(plan_id=HOLDING_ID_2, evaluation_price=106)["plan"]
        duplicate_holdings = _calculate(
            [holding_1, holding_2],
            holding_confirmations={
                holding_1["plan_id"]: _holding_confirmation(),
                holding_2["plan_id"]: _holding_confirmation(quantity=5),
            },
        )

        entry_1 = _entry_plan()["plan"]
        entry_2 = _entry_plan(
            plan_id=ENTRY_ID_2,
            entry_price=101,
            stop_price=96,
            target_1=111,
            target_2=116,
        )["plan"]
        blocked_entries = _calculate(
            [entry_1, entry_2],
            selected_entry_ids=[entry_1["plan_id"], entry_2["plan_id"]],
        )
        allowed_entries = _calculate(
            [entry_1, entry_2],
            selected_entry_ids=[entry_1["plan_id"], entry_2["plan_id"]],
            multiple_entry_tickers_confirmed=["AAPL"],
        )

        self.assertFalse(duplicate_holdings["valid"])
        self.assertEqual(duplicate_holdings["errors"][0]["code"], "AMBIGUOUS_HOLDING_SELECTION")
        self.assertFalse(blocked_entries["valid"])
        self.assertEqual(blocked_entries["errors"][0]["code"], "AMBIGUOUS_ENTRY_SELECTION")
        self.assertTrue(allowed_entries["valid"], allowed_entries.get("reason"))
        self.assertEqual(allowed_entries["summary"]["pending_entry"]["selected_count"], 2)

    def test_holding_confirmation_schema_boolean_and_positive_values_fail_closed(self):
        holding = _holding_plan(plan_id=HOLDING_ID)["plan"]
        invalid_values = [
            (_holding_confirmation(confirmed=False), "HOLDING_NOT_CONFIRMED"),
            (_holding_confirmation(confirmed=1), "INVALID_BOOLEAN"),
            (_holding_confirmation(quantity=0), "NUMBER_RANGE"),
            (
                {
                    key: value
                    for key, value in _holding_confirmation().items()
                    if key != "user_stop_price"
                },
                "INVALID_HOLDING_INPUTS",
            ),
        ]

        for confirmation, expected_code in invalid_values:
            with self.subTest(expected_code=expected_code):
                result = _calculate(
                    [holding],
                    holding_confirmations={holding["plan_id"]: confirmation},
                )
                self.assertFalse(result["valid"])
                self.assertEqual(result["errors"][0]["code"], expected_code)

    def test_mixed_currency_and_review_entry_are_rejected(self):
        us_entry = _entry_plan()["plan"]
        kr_guide = _guide(ticker="005930")
        kr_entry = _entry_plan(kr_guide, plan_id=ENTRY_ID_2)["plan"]
        mixed = _calculate(
            [us_entry, kr_entry],
            selected_entry_ids=[us_entry["plan_id"], kr_entry["plan_id"]],
        )

        reviewed = update_trade_plan_status([us_entry], us_entry["plan_id"], "REVIEW_REQUIRED")["plans"][0]
        blocked_review = _calculate([reviewed], selected_entry_ids=[reviewed["plan_id"]])

        self.assertFalse(mixed["valid"])
        self.assertEqual(mixed["errors"][0]["code"], "MIXED_CURRENCY")
        self.assertFalse(blocked_review["valid"])
        self.assertEqual(blocked_review["errors"][0]["code"], "ENTRY_NOT_SELECTABLE")

    def test_known_plan_currency_must_match_confirmed_account_currency(self):
        upper_guide = _guide(ticker="005930")
        lower_guide = copy.deepcopy(upper_guide)
        lower_guide["currency_hint"] = "krw"

        for guide, source_hint in ((upper_guide, "KRW"), (lower_guide, "krw")):
            with self.subTest(source_hint=source_hint):
                kr_entry = _entry_plan(guide, plan_id=ENTRY_ID_2)["plan"]
                result = _calculate(
                    [kr_entry],
                    source_currency_hint=source_hint,
                    currency_code="USD",
                    selected_entry_ids=[kr_entry["plan_id"]],
                )

                self.assertFalse(result["valid"])
                self.assertEqual(result["errors"][0]["code"], "CURRENCY_MISMATCH")

    def test_urgent_combined_scenario_reports_known_minimum_risk_breach(self):
        entry = _entry_plan()["plan"]
        holding = _holding_plan(plan_id=HOLDING_ID)["plan"]

        result = _calculate(
            [entry, holding],
            selected_entry_ids=[entry["plan_id"]],
            holding_confirmations={
                holding["plan_id"]: _holding_confirmation(current_price=44, user_stop_price=45)
            },
            include_combined_scenario=True,
            max_total_risk_pct=0.5,
        )

        self.assertEqual(result["summary"]["decision_code"], "STOP_REVIEW_REQUIRED")
        self.assertEqual(result["summary"]["combined_scenario"]["exposure"], 2_880.0)
        self.assertIsNone(result["summary"]["combined_scenario"]["risk_at_stop"])
        breach = next(
            item for item in result["summary"]["limit_breaches"] if item["code"] == "TOTAL_RISK"
        )
        self.assertEqual(breach["scope"], "COMBINED")
        self.assertTrue(breach["partial"])
        self.assertEqual(breach["actual_pct"], 1.0)

    def test_ticker_limit_uses_unrounded_percentage(self):
        holding = _holding_plan(plan_id=HOLDING_ID)["plan"]

        result = _calculate(
            [holding],
            holding_confirmations={
                holding["plan_id"]: _holding_confirmation(
                    average_entry=90,
                    quantity=10,
                    current_price=100.0004,
                    user_stop_price=90,
                )
            },
            max_single_ticker_exposure_pct=10.0,
        )

        self.assertEqual(result["summary"]["ticker_rows"][0]["exposure_pct_of_account"], 10.0)
        self.assertEqual(result["summary"]["decision_code"], "OVER_USER_LIMIT")
        breach = next(
            item for item in result["summary"]["limit_breaches"] if item["code"] == "TICKER_EXPOSURE"
        )
        self.assertGreater(breach["actual_pct"], 10.0)

    def test_total_exposure_limit_and_empty_selection_decisions_fail_closed(self):
        holding = _holding_plan(plan_id=HOLDING_ID)["plan"]
        over_exposure = _calculate(
            [holding],
            holding_confirmations={holding["plan_id"]: _holding_confirmation()},
            max_total_exposure_pct=9.0,
        )
        empty = _calculate([holding])

        self.assertEqual(over_exposure["summary"]["decision_code"], "OVER_USER_LIMIT")
        breach = next(
            item for item in over_exposure["summary"]["limit_breaches"] if item["code"] == "TOTAL_EXPOSURE"
        )
        self.assertEqual(breach["scope"], "HOLDING")
        self.assertEqual(breach["actual_pct"], 10.0)
        self.assertEqual(empty["summary"]["decision_code"], "NO_SELECTION")

    def test_price_equal_to_stop_is_urgent_with_unknown_risk(self):
        holding = _holding_plan(plan_id=HOLDING_ID)["plan"]

        result = _calculate(
            [holding],
            holding_confirmations={
                holding["plan_id"]: _holding_confirmation(current_price=45, user_stop_price=45)
            },
        )

        self.assertEqual(result["summary"]["decision_code"], "STOP_REVIEW_REQUIRED")
        self.assertEqual(result["summary"]["holding"]["urgent_count"], 1)
        self.assertIsNone(result["summary"]["holding"]["giveback_to_stop"])

    def test_review_status_holding_can_be_counted_only_after_current_position_confirmation(self):
        holding = _holding_plan(plan_id=HOLDING_ID)["plan"]
        cancelled = update_trade_plan_status([holding], holding["plan_id"], "CANCELLED")["plans"][0]

        result = _calculate(
            [cancelled],
            holding_confirmations={cancelled["plan_id"]: _holding_confirmation()},
        )

        self.assertTrue(result["valid"], result.get("reason"))
        self.assertEqual(result["summary"]["decision_code"], "REVIEW_REQUIRED")
        self.assertTrue(result["summary"]["holding_rows"][0]["review_required"])

    def test_confirmations_and_account_are_required_for_a_positive_decision(self):
        holding = _holding_plan(plan_id=HOLDING_ID)["plan"]
        base = {
            "holding_confirmations": {holding["plan_id"]: _holding_confirmation()},
        }
        incomplete = _calculate([holding], completeness_confirmed=False, **base)
        currency_unchecked = _calculate([holding], currency_confirmed=False, **base)
        no_account = _calculate([holding], account_size=None, **base)
        no_limit = _calculate([holding], max_total_risk_pct=None, **base)

        self.assertEqual(incomplete["summary"]["decision_code"], "INCOMPLETE_CONFIRMATION")
        self.assertEqual(currency_unchecked["summary"]["decision_code"], "INCOMPLETE_CONFIRMATION")
        self.assertEqual(no_account["summary"]["decision_code"], "ACCOUNT_REQUIRED_FOR_DECISION")
        self.assertIsNone(no_account["summary"]["holding"]["risk_pct_of_account"])
        self.assertEqual(no_limit["summary"]["decision_code"], "RISK_LIMIT_NOT_SET")

    def test_invalid_numbers_fail_closed_and_inputs_are_not_mutated_or_serialized(self):
        entry = _entry_plan()["plan"]
        original = copy.deepcopy(entry)
        cases = [
            {"account_size": True},
            {"account_size": math.nan},
            {"max_total_risk_pct": math.inf},
            {"currency_code": "US"},
            {"currency_confirmed": 1},
        ]
        for values in cases:
            with self.subTest(values=values):
                result = _calculate([entry], selected_entry_ids=[entry["plan_id"]], **values)
                self.assertFalse(result["valid"])

        self.assertEqual(entry, original)
        encoded = encode_trade_plan_bundle([entry])
        self.assertTrue(encoded["valid"])
        self.assertNotIn('"account_size":', encoded["data"].decode("utf-8"))

    def test_falsey_non_mapping_holding_inputs_are_rejected(self):
        entry = _entry_plan()["plan"]

        for invalid in ([], "", 0, False):
            with self.subTest(invalid=invalid):
                result = _calculate(
                    [entry],
                    selected_entry_ids=[entry["plan_id"]],
                    holding_confirmations=invalid,
                )
                self.assertFalse(result["valid"])
                self.assertEqual(result["errors"][0]["code"], "INVALID_HOLDING_INPUTS")


if __name__ == "__main__":
    unittest.main()
