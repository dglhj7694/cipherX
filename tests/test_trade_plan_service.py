import copy
import json
import math
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.beginner_trade_guide import build_beginner_trade_guide
from services.trade_plan_service import (
    MAX_IMPORT_BYTES,
    MAX_SESSION_PLANS,
    add_trade_plan,
    assess_trade_plan,
    build_entry_trade_plan,
    build_holding_trade_plan,
    decode_trade_plan_bundle,
    delete_trade_plan,
    encode_trade_plan_bundle,
    merge_trade_plans,
    update_trade_plan_status,
    validate_trade_plan,
)


NOW = "2026-07-13T00:00:00Z"
PLAN_ID = "12345678-1234-4234-8234-123456789abc"


def _strategy(**overrides):
    value = {
        "id": "trend_pullback_long",
        "label": "추세 눌림 매수",
        "direction": "LONG",
        "status": "ACTIVE",
        "score": 80.0,
        "presentation_type": "strategy",
        "implementation_level": "implemented",
        "deterministic": True,
        "entry_reference_type": "ENTRY_PRICE",
        "entry_reference_text": "진입가 100.00",
        "entry_price": 100.0,
        "stop_loss": 95.0,
        "target_1": 110.0,
        "target_2": 115.0,
    }
    value.update(overrides)
    return value


def _meta(strategy=None, **overrides):
    strategy = dict(strategy or _strategy())
    value = {
        "ticker": "AAPL",
        "judgment": "BUY",
        "price": 100.0,
        "summary_price_available": True,
        "summary_date": "2026-07-10",
        "strategy_visible_results": [strategy],
        "strategy_summary": {
            "conflict_level": "LOW",
            "top_strategy": dict(strategy),
            "opposing_reasons": [],
        },
        "objective_alignment": "ALIGNED",
    }
    value.update(overrides)
    return value


def _guide(**meta_overrides):
    return build_beginner_trade_guide(_meta(**meta_overrides))


def _entry_plan(guide=None, *, plan_id=PLAN_ID, now=NOW, **overrides):
    values = {
        "entry_price": 100.0,
        "stop_price": 95.0,
        "target_1": 110.0,
        "target_2": 115.0,
        "risk_pct": 1.0,
        "max_allocation_pct": 20.0,
        "planned_quantity": 20,
        "include_quantity": False,
        "account_size": 10_000.0,
        "now": now,
        "plan_id": plan_id,
    }
    values.update(overrides)
    return build_entry_trade_plan(guide or _guide(), **values)


def _holding_plan(guide=None, *, plan_id=PLAN_ID, now=NOW, **overrides):
    values = {
        "average_entry": 100.0,
        "quantity": 10.5,
        "evaluation_price": 105.0,
        "evaluation_price_source": "USER_INPUT",
        "user_stop_price": 95.0,
        "now": now,
        "plan_id": plan_id,
    }
    values.update(overrides)
    return build_holding_trade_plan(guide or _guide(), **values)


class TradePlanCreationTests(unittest.TestCase):
    def test_entry_plan_uses_user_levels_recalculates_rr_and_omits_account_size(self):
        result = _entry_plan(
            entry_price=102,
            stop_price=96,
            target_1=114,
            target_2=120,
            risk_pct=0.7,
            max_allocation_pct=15,
        )

        self.assertTrue(result["valid"], result.get("reason"))
        self.assertEqual(result["calculation"]["rr"], 2.0)
        inputs = result["plan"]["user_inputs"]
        self.assertEqual(inputs["entry_price"], 102.0)
        self.assertEqual(inputs["stop_price"], 96.0)
        self.assertEqual(inputs["target_1"], 114.0)
        self.assertIsNone(inputs["planned_quantity"])
        self.assertFalse(inputs["quantity_included"])
        serialized = json.dumps(result["plan"], ensure_ascii=False)
        self.assertNotIn('"account_size":', serialized)
        self.assertFalse(result["plan"]["privacy"]["account_size_stored"])

    def test_entry_quantity_is_stored_only_after_explicit_opt_in(self):
        hidden = _entry_plan(planned_quantity=25, include_quantity=False)
        included = _entry_plan(
            plan_id="22345678-1234-4234-8234-123456789abc",
            planned_quantity=20,
            include_quantity=True,
        )

        self.assertIsNone(hidden["plan"]["user_inputs"]["planned_quantity"])
        self.assertEqual(hidden["plan"]["privacy"]["sensitive_fields"], [])
        self.assertEqual(included["plan"]["user_inputs"]["planned_quantity"], 20)
        self.assertEqual(included["plan"]["privacy"]["sensitive_fields"], ["planned_quantity"])

    def test_entry_quantity_requires_transient_account_recalculation_and_is_not_ready_after_reload(self):
        mismatch = _entry_plan(planned_quantity=999_999, include_quantity=True, account_size=10_000)
        missing_account = _entry_plan(planned_quantity=20, include_quantity=True, account_size=None)
        verified = _entry_plan(planned_quantity=20, include_quantity=True, account_size=10_000)

        self.assertFalse(mismatch["valid"])
        self.assertEqual(mismatch["errors"][0]["code"], "QUANTITY_MISMATCH")
        self.assertFalse(missing_account["valid"])
        self.assertTrue(verified["valid"], verified.get("reason"))
        assessed = assess_trade_plan(verified["plan"], _guide())
        self.assertEqual(assessed["freshness"], "MATCHED")
        self.assertEqual(assessed["readiness"], "REVIEW_REQUIRED")

    def test_entry_rejects_invalid_levels_low_rr_and_unsafe_guide(self):
        cases = [
            ({"stop_price": 101}, "손절가"),
            ({"target_1": 99}, "1차 목표"),
            ({"target_1": 101}, "1.00R"),
        ]
        for overrides, expected in cases:
            with self.subTest(overrides=overrides):
                result = _entry_plan(**overrides)
                self.assertFalse(result["valid"])
                self.assertIn(expected, result["reason"])

        conflicted = _guide(objective_alignment="CONFLICT")
        result = _entry_plan(conflicted)
        self.assertFalse(result["valid"])
        self.assertIn("안전 게이트", result["reason"])

    def test_entry_omits_reversed_optional_second_target_without_hiding_plan(self):
        result = _entry_plan(target_1=115, target_2=110)

        self.assertTrue(result["valid"])
        self.assertIsNone(result["plan"]["user_inputs"]["target_2"])
        self.assertTrue(any("2차 목표" in warning for warning in result["warnings"]))

    def test_entry_rejects_missing_analysis_date_and_non_finite_or_boolean_values(self):
        no_date = _guide(summary_date="")
        self.assertFalse(_entry_plan(no_date)["valid"])
        for field, value in (("entry_price", True), ("entry_price", math.nan), ("risk_pct", math.inf)):
            with self.subTest(field=field, value=value):
                result = _entry_plan(**{field: value})
                self.assertFalse(result["valid"])

    def test_creation_is_deep_copy_and_does_not_copy_raw_meta_secrets(self):
        meta = _meta(runtime_gemini_api_key="secret-sentinel", fig_json="chart", prompt="private")
        guide = build_beginner_trade_guide(meta)
        original = copy.deepcopy(guide)
        result = _entry_plan(guide)
        guide["risk_flags"].append("later mutation")

        self.assertEqual(original["risk_flags"], result["plan"]["analysis_snapshot"]["risk_flags"])
        serialized = json.dumps(result["plan"], ensure_ascii=False)
        self.assertNotIn("secret-sentinel", serialized)
        self.assertNotIn("fig_json", serialized)
        self.assertNotIn("prompt", serialized)

    def test_holding_plan_preserves_fractional_quantity_and_profitable_trailing_stop(self):
        result = _holding_plan(
            average_entry=100,
            quantity=0.75,
            evaluation_price=120,
            user_stop_price=110,
        )

        self.assertTrue(result["valid"], result.get("reason"))
        self.assertEqual(result["plan"]["user_inputs"]["quantity"], 0.75)
        self.assertEqual(result["calculation"]["pnl_at_stop"], 7.5)
        self.assertEqual(result["plan"]["status"], "MONITORING")

    def test_holding_requires_explicit_user_stop_and_never_substitutes_engine_level(self):
        result = _holding_plan(user_stop_price=None)

        self.assertFalse(result["valid"])
        self.assertIn("사용자 방어 기준", result["reason"])

    def test_holding_uses_engine_levels_only_from_snapshot_and_checks_snapshot_price_source(self):
        derived = _holding_plan(evaluation_price=94.5, evaluation_price_source="USER_INPUT", user_stop_price=90)
        mismatched_source = _holding_plan(
            evaluation_price=94.5,
            evaluation_price_source="ANALYSIS_SNAPSHOT",
            user_stop_price=90,
        )

        self.assertTrue(derived["valid"], derived.get("reason"))
        self.assertEqual(derived["calculation"]["scenario_code"], "DEFEND_REVIEW")
        inputs = derived["plan"]["user_inputs"]
        self.assertNotIn("engine_invalidation_price", inputs)
        self.assertNotIn("target_1", inputs)
        self.assertFalse(mismatched_source["valid"])
        self.assertEqual(mismatched_source["errors"][0]["code"], "SNAPSHOT_PRICE_MISMATCH")

    def test_sell_holding_is_saved_as_review_required(self):
        meta = {
            "ticker": "AAPL",
            "judgment": "SELL",
            "price": 90.0,
            "summary_price_available": True,
            "summary_date": "2026-07-10",
            "strategy_visible_results": [],
            "strategy_summary": {"conflict_level": "LOW", "top_strategy": None},
        }
        result = _holding_plan(build_beginner_trade_guide(meta), evaluation_price=90, user_stop_price=85)

        self.assertTrue(result["valid"])
        self.assertEqual(result["calculation"]["scenario_code"], "DEFEND_REVIEW")
        self.assertEqual(result["plan"]["status"], "REVIEW_REQUIRED")


class TradePlanValidationAndFreshnessTests(unittest.TestCase):
    def test_fingerprint_detects_nested_mutation(self):
        result = _entry_plan()
        tampered = copy.deepcopy(result["plan"])
        tampered["user_inputs"]["entry_price"] = 101.0

        checked = validate_trade_plan(tampered)

        self.assertFalse(checked["valid"])
        self.assertEqual(checked["errors"][0]["code"], "FINGERPRINT_MISMATCH")

    def test_validator_rejects_unknown_sensitive_fields_before_use(self):
        result = _entry_plan()
        tampered = copy.deepcopy(result["plan"])
        tampered["user_inputs"]["account_size"] = 10_000

        checked = validate_trade_plan(tampered)

        self.assertFalse(checked["valid"])
        self.assertEqual(checked["errors"][0]["code"], "SENSITIVE_FIELD")

    def test_assessment_distinguishes_matched_stale_context_and_unverified(self):
        plan = _entry_plan()["plan"]

        matched = assess_trade_plan(plan, _guide())
        changed = assess_trade_plan(plan, _guide(judgment="WATCH_BUY"))
        other = copy.deepcopy(_meta())
        other["ticker"] = "MSFT"
        other_guide = build_beginner_trade_guide(other)
        context = assess_trade_plan(plan, other_guide)
        unverified = assess_trade_plan(plan)

        self.assertEqual(matched["freshness"], "MATCHED")
        self.assertEqual(matched["readiness"], "READY")
        self.assertEqual(changed["freshness"], "STALE")
        self.assertEqual(context["freshness"], "CONTEXT_MISMATCH")
        self.assertEqual(unverified["freshness"], "UNVERIFIED")
        self.assertNotEqual(unverified["readiness"], "READY")

    def test_display_copy_changes_do_not_change_analysis_digest(self):
        plan = _entry_plan()["plan"]
        guide = _guide()
        guide["action_title"] = "다른 표시 문구"
        guide["action_summary"] = "표시 설명만 바뀜"

        assessed = assess_trade_plan(plan, guide)

        self.assertEqual(assessed["freshness"], "MATCHED")

    def test_new_risk_flag_marks_saved_plan_stale(self):
        plan = _entry_plan()["plan"]
        guide = _guide()
        guide["risk_flags"] = ["새로운 중대 경고"]

        assessed = assess_trade_plan(plan, guide)

        self.assertEqual(assessed["freshness"], "STALE")
        self.assertEqual(assessed["readiness"], "REVIEW_REQUIRED")

    def test_status_update_is_copy_on_write_and_increments_version(self):
        original = _entry_plan()["plan"]
        before = copy.deepcopy(original)

        result = update_trade_plan_status([original], original["plan_id"], "CANCELLED", now="2026-07-14T00:00:00Z")

        self.assertTrue(result["valid"])
        self.assertEqual(original, before)
        updated = result["plans"][0]
        self.assertEqual(updated["status"], "CANCELLED")
        self.assertEqual(updated["plan_version"], 2)
        self.assertEqual(updated["plan_id"], original["plan_id"])
        self.assertEqual(updated["analysis_snapshot"], original["analysis_snapshot"])
        self.assertTrue(validate_trade_plan(updated)["valid"])

    def test_status_update_never_moves_time_backwards_or_overflows_version(self):
        future = _entry_plan(now="2099-01-01T00:00:00Z")["plan"]
        updated = update_trade_plan_status([future], future["plan_id"], "CANCELLED", now=NOW)

        self.assertTrue(updated["valid"], updated.get("reason"))
        self.assertGreaterEqual(updated["plans"][0]["updated_at"], future["updated_at"])
        self.assertTrue(validate_trade_plan(updated["plans"][0])["valid"])

        capped = copy.deepcopy(future)
        capped["plan_version"] = 1_000_000
        blocked = update_trade_plan_status([capped], capped["plan_id"], "CANCELLED", now=NOW)
        self.assertFalse(blocked["valid"])
        self.assertEqual(blocked["errors"][0]["code"], "PLAN_VERSION_LIMIT")

    def test_delete_is_copy_on_write_and_fails_atomically_for_invalid_collection(self):
        original = _entry_plan()["plan"]
        before = copy.deepcopy(original)
        deleted = delete_trade_plan([original], original["plan_id"])
        self.assertTrue(deleted["valid"])
        self.assertEqual(deleted["plans"], [])
        self.assertEqual(original, before)

        invalid = copy.deepcopy(original)
        invalid["fingerprint"] = "sha256:" + "0" * 64
        failed = delete_trade_plan([invalid], original["plan_id"])
        self.assertFalse(failed["valid"])
        self.assertEqual(failed["plans"], [invalid])


class TradePlanCollectionAndJsonTests(unittest.TestCase):
    def test_add_deduplicates_by_fingerprint_and_never_mutates_existing(self):
        plan = _entry_plan()["plan"]
        existing = [copy.deepcopy(plan)]
        before = copy.deepcopy(existing)

        result = add_trade_plan(existing, plan)

        self.assertTrue(result["valid"])
        self.assertEqual(result["added"], 0)
        self.assertEqual(result["duplicates"], 1)
        self.assertEqual(existing, before)

    def test_session_limit_blocks_twenty_first_without_evicting_oldest(self):
        plans = []
        for index in range(MAX_SESSION_PLANS):
            plan_id = f"{index + 1:08x}-1234-4234-8234-{index + 1:012x}"
            built = _entry_plan(
                plan_id=plan_id,
                entry_price=100 + index,
                stop_price=95 + index,
                target_1=110 + index,
                target_2=115 + index,
            )
            self.assertTrue(built["valid"], built.get("reason"))
            added = add_trade_plan(plans, built["plan"])
            self.assertTrue(added["valid"])
            plans = added["plans"]
        original = copy.deepcopy(plans)
        extra = _entry_plan(
            plan_id="ffffffff-1234-4234-8234-ffffffffffff",
            entry_price=200,
            stop_price=190,
            target_1=220,
            target_2=230,
        )

        blocked = add_trade_plan(plans, extra["plan"])

        self.assertFalse(blocked["valid"])
        self.assertEqual(blocked["errors"][0]["code"], "PLAN_LIMIT")
        self.assertEqual(blocked["plans"], original)

    def test_json_round_trip_is_utf8_strict_and_import_requires_review(self):
        entry = _entry_plan(include_quantity=True, planned_quantity=20)["plan"]
        holding = _holding_plan(plan_id="22345678-1234-4234-8234-123456789abc")["plan"]

        encoded = encode_trade_plan_bundle([entry, holding], exported_at=NOW)
        decoded = decode_trade_plan_bundle(encoded["data"], imported_at="2026-07-14T00:00:00Z")

        self.assertTrue(encoded["valid"])
        self.assertTrue(decoded["valid"], decoded.get("reason"))
        self.assertEqual(decoded["count"], 2)
        self.assertTrue(all(plan["status"] == "REVIEW_REQUIRED" for plan in decoded["plans"]))
        text = encoded["data"].decode("utf-8")
        self.assertIn('"average_entry"', text)
        self.assertIn('"quantity"', text)
        self.assertNotIn('"account_size":', text)
        self.assertNotIn("runtime_gemini_api_key", text)

    def test_decoder_rejects_non_json_invalid_utf8_nan_duplicate_keys_and_depth(self):
        cases = [
            (b"not-json", "INVALID_JSON"),
            (b"\xff\xfe", "INVALID_UTF8"),
            (b'{"schema":NaN}', "NON_FINITE_JSON"),
            (b'{"schema":"a","schema":"b"}', "DUPLICATE_JSON_KEY"),
            (json.dumps({"x": [[[[[[[[[1]]]]]]]]]}).encode(), "JSON_TOO_DEEP"),
        ]
        for payload, code in cases:
            with self.subTest(code=code):
                result = decode_trade_plan_bundle(payload)
                self.assertFalse(result["valid"])
                self.assertEqual(result["errors"][0]["code"], code)
                self.assertEqual(result["plans"], [])

    def test_decoder_rejects_unpaired_unicode_surrogate_without_raising(self):
        escaped = b'{"schema":"\\ud800"}'
        direct = '{"schema":"\ud800"}'

        for payload in (escaped, direct):
            with self.subTest(payload_type=type(payload).__name__):
                result = decode_trade_plan_bundle(payload)
                self.assertFalse(result["valid"])
                self.assertIn(result["errors"][0]["code"], {"INVALID_UNICODE", "UNKNOWN_FIELD", "MISSING_FIELD"})

    def test_encoder_rejects_duplicate_plan_ids_that_decoder_cannot_restore(self):
        plan = _entry_plan()["plan"]

        encoded = encode_trade_plan_bundle([plan, copy.deepcopy(plan)], exported_at=NOW)

        self.assertFalse(encoded["valid"])
        self.assertEqual(encoded["errors"][0]["code"], "DUPLICATE_EXPORT_ID")

    def test_decoder_rejects_oversized_future_schema_and_unknown_fields(self):
        oversized = b"{" + b" " * MAX_IMPORT_BYTES + b"}"
        self.assertEqual(decode_trade_plan_bundle(oversized)["errors"][0]["code"], "IMPORT_TOO_LARGE")

        encoded = encode_trade_plan_bundle([_entry_plan()["plan"]], exported_at=NOW)
        root = json.loads(encoded["data"])
        root["schema_version"] = 2
        future = decode_trade_plan_bundle(json.dumps(root).encode())
        self.assertFalse(future["valid"])

        root = json.loads(encoded["data"])
        root["constructor"] = {}
        unknown = decode_trade_plan_bundle(json.dumps(root).encode())
        self.assertFalse(unknown["valid"])
        self.assertEqual(unknown["errors"][0]["code"], "UNKNOWN_FIELD")

    def test_decoder_converts_numeric_and_timestamp_overflow_to_structured_errors(self):
        encoded = encode_trade_plan_bundle([_entry_plan()["plan"]], exported_at=NOW)
        huge_number = json.loads(encoded["data"])
        huge_number["plans"][0]["user_inputs"]["entry_price"] = int("9" * 1000)
        bad_offset = json.loads(encoded["data"])
        bad_offset["exported_at"] = "9999-12-31T23:59:59-23:59"

        numeric_result = decode_trade_plan_bundle(json.dumps(huge_number).encode())
        timestamp_result = decode_trade_plan_bundle(json.dumps(bad_offset).encode())

        self.assertFalse(numeric_result["valid"])
        self.assertEqual(numeric_result["errors"][0]["code"], "NUMBER_RANGE")
        self.assertFalse(timestamp_result["valid"])
        self.assertEqual(timestamp_result["errors"][0]["code"], "INVALID_TIMESTAMP")

    def test_decoder_is_atomic_when_one_plan_is_tampered(self):
        first = _entry_plan()["plan"]
        second = _holding_plan(plan_id="22345678-1234-4234-8234-123456789abc")["plan"]
        encoded = encode_trade_plan_bundle([first, second], exported_at=NOW)
        root = json.loads(encoded["data"])
        root["plans"][1]["user_inputs"]["quantity"] = True

        decoded = decode_trade_plan_bundle(json.dumps(root).encode())

        self.assertFalse(decoded["valid"])
        self.assertEqual(decoded["plans"], [])

    def test_merge_rejects_same_id_different_plan_without_modifying_existing(self):
        existing = _entry_plan()["plan"]
        incoming = _entry_plan(entry_price=101, stop_price=96, target_1=111, target_2=116)["plan"]
        before = copy.deepcopy(existing)

        merged = merge_trade_plans([existing], [incoming])

        self.assertFalse(merged["valid"])
        self.assertEqual(merged["errors"][0]["code"], "PLAN_ID_CONFLICT")
        self.assertEqual(merged["plans"], [before])

    def test_import_bundle_duplicate_ids_is_atomic(self):
        plan = _entry_plan()["plan"]
        bundle = {
            "schema": "cipherx.trade-plans",
            "schema_version": 1,
            "exported_at": NOW,
            "plans": [plan, copy.deepcopy(plan)],
        }

        decoded = decode_trade_plan_bundle(json.dumps(bundle).encode())

        self.assertFalse(decoded["valid"])
        self.assertEqual(decoded["errors"][0]["code"], "DUPLICATE_IMPORT_ID")
        self.assertEqual(decoded["plans"], [])


if __name__ == "__main__":
    unittest.main()
