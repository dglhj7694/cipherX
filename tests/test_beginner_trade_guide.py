import math
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.beginner_trade_guide import (
    build_beginner_trade_guide,
    calculate_execution_ticket,
    calculate_position_size,
    resolve_top_strategy,
)


def _strategy(**overrides):
    payload = {
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
        "rr": 99.0,
    }
    payload.update(overrides)
    return payload


def _meta(strategy=None, **overrides):
    strategy = dict(strategy or _strategy())
    payload = {
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
    payload.update(overrides)
    return payload


class BeginnerTradeGuideTests(unittest.TestCase):
    def test_sparse_top_strategy_is_merged_with_full_visible_result(self):
        full = _strategy(stop_loss=94.0, target_2=118.0)
        meta = _meta(full)
        meta["strategy_summary"]["top_strategy"] = {
            "id": full["id"],
            "label": full["label"],
            "score": 91.0,
        }

        selected = resolve_top_strategy(meta)

        self.assertEqual(selected["score"], 91.0)
        self.assertEqual(selected["stop_loss"], 94.0)
        self.assertEqual(selected["target_2"], 118.0)

    def test_sparse_standalone_top_without_provenance_fails_closed(self):
        meta = {
            "ticker": "AAPL",
            "judgment": "BUY",
            "strategy_summary": {
                "conflict_level": "LOW",
                "top_strategy": {
                    "id": "legacy_top",
                    "label": "출처 불명 전략",
                    "direction": "LONG",
                    "status": "ACTIVE",
                    "entry_price": 100,
                    "stop_loss": 95,
                    "target_1": 110,
                },
            },
        }

        guide = build_beginner_trade_guide(meta)

        self.assertEqual(guide["action_code"], "NO_SETUP")
        self.assertFalse(guide["sizing_available"])

    def test_opposite_proxy_top_is_not_used_as_beginner_buy_plan(self):
        proxy_short = _strategy(
            id="macro_short",
            label="거시 약세 맥락",
            direction="SHORT",
            score=99.0,
            presentation_type="context",
            implementation_level="proxy",
            stop_loss=105.0,
            target_1=90.0,
            target_2=85.0,
        )
        implemented_long = _strategy(score=72.0)
        meta = _meta(implemented_long)
        meta["strategy_visible_results"] = [proxy_short, implemented_long]
        meta["strategy_summary"]["top_strategy"] = proxy_short

        selected = resolve_top_strategy(meta)

        self.assertEqual(selected["id"], implemented_long["id"])
        self.assertEqual(selected["direction"], "LONG")

    def test_active_buy_plan_recalculates_rr_and_enables_sizing(self):
        audit = {
            "available": True,
            "reference_horizon": 5,
            "label_rows": [{"name": "BUY", "samples": 24, "hit_5": 0.625, "edge_5": 0.012}],
        }

        guide = build_beginner_trade_guide(_meta(), audit=audit)

        self.assertEqual(guide["action_code"], "PLAN_READY")
        self.assertTrue(guide["levels_visible"])
        self.assertFalse(guide["levels_conditional"])
        self.assertEqual(guide["stop_loss"], 95.0)
        self.assertEqual(guide["target_1"], 110.0)
        self.assertEqual(guide["target_2"], 115.0)
        self.assertEqual(guide["rr"], 2.0)
        self.assertTrue(guide["sizing_available"])
        self.assertTrue(guide["audit_snapshot"]["sufficient_samples"])
        self.assertEqual(guide["audit_snapshot"]["hit_rate"], 0.625)

    def test_reversed_second_target_is_hidden_without_blocking_valid_first_target(self):
        reversed_second = _strategy(target_1=115.0, target_2=110.0)

        guide = build_beginner_trade_guide(_meta(reversed_second))

        self.assertEqual(guide["target_1"], 115.0)
        self.assertIsNone(guide["target_2"])
        self.assertEqual(guide["rr"], 3.0)
        self.assertTrue(guide["sizing_available"])
        self.assertIn("2차 목표 순서 확인 필요", guide["risk_flags"])

    def test_waiting_strategy_hides_stale_execution_levels(self):
        waiting = _strategy(
            status="TRIGGER_WAIT",
            entry_reference_type="CONFIRMATION",
            entry_reference_text="확인선 105.00",
            entry_price=105.0,
            stop_loss=95.0,
            target_1=110.0,
            target_2=115.0,
        )

        guide = build_beginner_trade_guide(_meta(waiting))

        self.assertEqual(guide["action_code"], "WAIT_TRIGGER")
        self.assertEqual(guide["entry_reference"], "확인선 105.00")
        self.assertIsNone(guide["entry_price"])
        self.assertIsNone(guide["stop_loss"])
        self.assertIsNone(guide["target_1"])
        self.assertIsNone(guide["target_2"])
        self.assertIsNone(guide["rr"])
        self.assertFalse(guide["sizing_available"])
        self.assertIn("진입이 확인된 뒤", guide["checklist"][2]["text"])

    def test_confirming_strategy_shows_conditional_levels_but_no_sizing(self):
        confirming = _strategy(status="CONFIRMING", entry_reference_type="CONFIRMATION")

        guide = build_beginner_trade_guide(_meta(confirming))

        self.assertEqual(guide["action_code"], "CONFIRMING")
        self.assertTrue(guide["levels_visible"])
        self.assertTrue(guide["levels_conditional"])
        self.assertEqual(guide["stop_loss"], 95.0)
        self.assertFalse(guide["sizing_available"])

    def test_sell_judgment_is_defensive_and_never_opens_short_calculator(self):
        short = _strategy(
            id="breakdown_short",
            label="하락 추세",
            direction="SHORT",
            status="SHORT_ENTRY",
            entry_price=100.0,
            stop_loss=105.0,
            target_1=90.0,
            target_2=85.0,
        )
        meta = _meta(short, judgment="SELL")

        guide = build_beginner_trade_guide(meta)

        self.assertEqual(guide["action_code"], "DEFEND")
        self.assertEqual(guide["direction"], "SHORT")
        self.assertFalse(guide["levels_visible"])
        self.assertIsNone(guide["stop_loss"])
        self.assertIsNone(guide["target_1"])
        self.assertEqual(guide["entry_reference"], "매도 압력 완화와 지지 회복 확인")
        self.assertFalse(guide["sizing_available"])
        self.assertIn("신규 매수 보류", guide["action_title"])

    def test_high_or_objective_conflict_blocks_sizing(self):
        high_meta = _meta()
        high_meta["strategy_summary"]["conflict_level"] = "HIGH"
        objective_meta = _meta(objective_alignment="CONFLICT")

        high_guide = build_beginner_trade_guide(high_meta)
        objective_guide = build_beginner_trade_guide(objective_meta)

        self.assertEqual(high_guide["action_code"], "CONFLICT")
        self.assertFalse(high_guide["sizing_available"])
        self.assertEqual(objective_guide["action_code"], "CONFLICT")
        self.assertFalse(objective_guide["sizing_available"])
        self.assertTrue(any("객관 엔진" in flag for flag in objective_guide["risk_flags"]))

    def test_signal_conflict_or_thin_liquidity_blocks_beginner_entry(self):
        signal_conflict = build_beginner_trade_guide(_meta(signal_conflict_layers=3))
        thin_liquidity = build_beginner_trade_guide(_meta(thin_trade_risk=True))

        self.assertEqual(signal_conflict["action_code"], "CONFLICT")
        self.assertFalse(signal_conflict["sizing_available"])
        self.assertIn("3개 레이어", signal_conflict["checklist"][-1]["text"])
        self.assertEqual(thin_liquidity["action_code"], "LIQUIDITY_WAIT")
        self.assertFalse(thin_liquidity["sizing_available"])
        self.assertTrue(any("거래대금" in flag for flag in thin_liquidity["risk_flags"]))

    def test_proxy_only_or_missing_strategy_degrades_to_observation(self):
        proxy = _strategy(presentation_type="context", implementation_level="proxy")
        guide = build_beginner_trade_guide(_meta(proxy))
        empty = build_beginner_trade_guide({"ticker": "AAPL", "judgment": "BUY"})

        self.assertEqual(guide["action_code"], "NO_SETUP")
        self.assertEqual(guide["strategy_label"], "전략 없음")
        self.assertFalse(guide["sizing_available"])
        self.assertEqual(empty["action_code"], "NO_SETUP")

    def test_empty_visible_results_never_fall_back_to_invalid_strategy(self):
        invalid = _strategy(status="INVALID", label="무효 전략")
        meta = _meta(invalid)
        meta["strategy_visible_results"] = []
        meta["strategy_results"] = [invalid]

        guide = build_beginner_trade_guide(meta)

        self.assertEqual(guide["action_code"], "NO_SETUP")
        self.assertEqual(guide["strategy_label"], "전략 없음")
        self.assertEqual(guide["strategy_status"], "")

    def test_empty_visible_results_drop_stale_active_summary_top(self):
        meta = _meta()
        meta["strategy_visible_results"] = []

        guide = build_beginner_trade_guide(meta)

        self.assertEqual(guide["action_code"], "NO_SETUP")
        self.assertEqual(guide["strategy_label"], "전략 없음")
        self.assertFalse(guide["sizing_available"])

    def test_invalid_price_data_or_wrong_target_never_looks_executable(self):
        wrong_target = _strategy(target_1=90.0, target_2=float("nan"))
        unavailable = build_beginner_trade_guide(_meta(wrong_target, summary_price_available=False))
        available = build_beginner_trade_guide(_meta(wrong_target))

        self.assertFalse(unavailable["levels_visible"])
        self.assertFalse(unavailable["sizing_available"])
        self.assertIn("유효한 대표 가격 없음", unavailable["risk_flags"])
        self.assertIsNone(available["target_1"])
        self.assertIsNone(available["target_2"])
        self.assertIsNone(available["rr"])
        self.assertEqual(available["action_code"], "MISSING_REWARD")
        self.assertFalse(available["sizing_available"])
        self.assertIn("1차 목표", available["sizing_block_reason"])

    def test_low_reward_risk_never_opens_positive_plan_or_calculator(self):
        low_rr = _strategy(target_1=101.0, target_2=102.0)

        guide = build_beginner_trade_guide(_meta(low_rr))

        self.assertEqual(guide["rr"], 0.2)
        self.assertEqual(guide["action_code"], "LOW_REWARD_RISK")
        self.assertEqual(guide["action_tone"], "risk")
        self.assertFalse(guide["sizing_available"])
        self.assertIn("1R 미만", guide["sizing_block_reason"])

    def test_watch_buy_and_neutral_judgments_never_open_execution_calculator(self):
        watch = build_beginner_trade_guide(_meta(judgment="WATCH_BUY"))
        neutral = build_beginner_trade_guide(_meta(judgment="NEUTRAL"))

        self.assertEqual(watch["action_code"], "WAIT_TRIGGER")
        self.assertTrue(watch["levels_conditional"])
        self.assertFalse(watch["sizing_available"])
        self.assertIn("BUY 이상", watch["sizing_block_reason"])
        self.assertEqual(neutral["action_code"], "NO_SETUP")
        self.assertFalse(neutral["levels_visible"])
        self.assertFalse(neutral["sizing_available"])

    def test_structured_leading_noise_flags_never_render_boolean_text(self):
        guide = build_beginner_trade_guide(
            _meta(
                leading_noise_flags={
                    "summary": "약한 ADX",
                    "noise_block": True,
                    "buy_noise_block": False,
                }
            )
        )

        self.assertIn("약한 ADX", guide["risk_flags"])
        self.assertIn("선행 신호 노이즈 차단", guide["risk_flags"])
        self.assertNotIn("True", guide["risk_flags"])

    def test_audit_snapshot_marks_small_same_label_sample_as_insufficient(self):
        audit = {
            "available": True,
            "reference_horizon": 10,
            "label_rows": [{"name": "BUY", "samples": 7, "hit_10": 0.8, "edge_10": 0.03}],
        }

        guide = build_beginner_trade_guide(_meta(), audit=audit)

        self.assertTrue(guide["audit_snapshot"]["matched"])
        self.assertFalse(guide["audit_snapshot"]["sufficient_samples"])
        self.assertEqual(guide["audit_snapshot"]["samples"], 7)


class PositionSizeTests(unittest.TestCase):
    def test_execution_ticket_revalidates_target_rr_and_position_size_together(self):
        ticket = calculate_execution_ticket(
            entry_price=100,
            stop_price=95,
            target_price=110,
            account_size=10_000,
            risk_pct=1,
            max_allocation_pct=20,
        )

        self.assertTrue(ticket["valid"])
        self.assertEqual(ticket["rr"], 2.0)
        self.assertEqual(ticket["quantity"], 20)
        self.assertEqual(ticket["target_price"], 110)

    def test_execution_ticket_blocks_target_below_entry_and_low_rr(self):
        wrong_direction = calculate_execution_ticket(
            entry_price=120,
            stop_price=115,
            target_price=110,
            account_size=10_000,
            risk_pct=1,
            max_allocation_pct=20,
        )
        low_rr = calculate_execution_ticket(
            entry_price=100,
            stop_price=95,
            target_price=101,
            account_size=10_000,
            risk_pct=1,
            max_allocation_pct=20,
        )

        self.assertFalse(wrong_direction["valid"])
        self.assertIn("1차 목표", wrong_direction["reason"])
        self.assertFalse(low_rr["valid"])
        self.assertEqual(low_rr["rr"], 0.2)
        self.assertEqual(low_rr["quantity"], 0)

    def test_uses_smaller_of_risk_and_allocation_limits(self):
        risk_limited = calculate_position_size(
            entry_price=100,
            stop_price=95,
            account_size=10_000,
            risk_pct=1,
            max_allocation_pct=20,
        )
        allocation_limited = calculate_position_size(
            entry_price=100,
            stop_price=95,
            account_size=10_000,
            risk_pct=1,
            max_allocation_pct=10,
        )

        self.assertTrue(risk_limited["valid"])
        self.assertEqual(risk_limited["quantity"], 20)
        self.assertEqual(risk_limited["estimated_loss"], 100)
        self.assertEqual(risk_limited["position_value"], 2_000)
        self.assertEqual(risk_limited["limited_by"], "both")
        self.assertEqual(allocation_limited["quantity"], 10)
        self.assertEqual(allocation_limited["limited_by"], "allocation")

    def test_validates_long_and_short_stop_direction(self):
        invalid_long = calculate_position_size(
            entry_price=100,
            stop_price=101,
            account_size=10_000,
            risk_pct=1,
            max_allocation_pct=20,
            direction="LONG",
        )
        valid_short = calculate_position_size(
            entry_price=100,
            stop_price=105,
            account_size=10_000,
            risk_pct=1,
            max_allocation_pct=20,
            direction="SHORT",
        )

        self.assertFalse(invalid_long["valid"])
        self.assertIn("손절가", invalid_long["reason"])
        self.assertTrue(valid_short["valid"])
        self.assertEqual(valid_short["quantity"], 20)

    def test_rejects_non_finite_zero_and_sub_one_share_results(self):
        invalid_values = [
            {"entry_price": math.nan, "stop_price": 95, "account_size": 10_000, "risk_pct": 1, "max_allocation_pct": 20},
            {"entry_price": 100, "stop_price": 100, "account_size": 10_000, "risk_pct": 1, "max_allocation_pct": 20},
            {"entry_price": 100, "stop_price": 95, "account_size": 0, "risk_pct": 1, "max_allocation_pct": 20},
            {"entry_price": 100, "stop_price": 95, "account_size": 10_000, "risk_pct": 0, "max_allocation_pct": 20},
        ]
        for values in invalid_values:
            with self.subTest(values=values):
                self.assertFalse(calculate_position_size(**values)["valid"])

        too_small = calculate_position_size(
            entry_price=1_000,
            stop_price=900,
            account_size=100,
            risk_pct=1,
            max_allocation_pct=20,
        )
        self.assertFalse(too_small["valid"])
        self.assertEqual(too_small["quantity"], 0)

        overflow = calculate_position_size(
            entry_price=1e-10,
            stop_price=5e-11,
            account_size=1e308,
            risk_pct=100,
            max_allocation_pct=100,
        )
        self.assertFalse(overflow["valid"])
        self.assertEqual(overflow["quantity"], 0)


if __name__ == "__main__":
    unittest.main()
