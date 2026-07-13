import sys
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _render_guide_app(meta, audit=None, key_prefix="guide_test", allow_plan_save=False):
    from app_ui.components.beginner_trade_guide import render_beginner_trade_guide

    render_beginner_trade_guide(
        meta,
        audit=audit,
        key_prefix=key_prefix,
        allow_plan_save=allow_plan_save,
    )


def _active_meta(status="ACTIVE"):
    strategy = {
        "id": "trend_pullback_long",
        "label": "추세 눌림 매수",
        "direction": "LONG",
        "status": status,
        "score": 82,
        "presentation_type": "strategy",
        "implementation_level": "implemented",
        "deterministic": True,
        "entry_reference_type": "ENTRY_PRICE" if status == "ACTIVE" else "CONFIRMATION",
        "entry_reference_text": "진입가 100.00" if status == "ACTIVE" else "확인선 100.00",
        "entry_price": 100.0,
        "stop_loss": 95.0,
        "target_1": 110.0,
        "target_2": 115.0,
    }
    return {
        "ticker": "AAPL",
        "judgment": "BUY",
        "price": 100.0,
        "summary_price_available": True,
        "summary_date": "2026-07-10",
        "strategy_visible_results": [strategy],
        "strategy_summary": {"conflict_level": "LOW", "top_strategy": strategy},
        "objective_alignment": "ALIGNED",
    }


class BeginnerTradeGuideAppTests(unittest.TestCase):
    def test_active_plan_renders_calculator_without_streamlit_exception(self):
        audit = {
            "available": True,
            "reference_horizon": 5,
            "label_rows": [{"name": "BUY", "samples": 30, "hit_5": 0.6, "edge_5": 0.01}],
        }

        app = AppTest.from_function(
            _render_guide_app,
            kwargs={"meta": _active_meta(), "audit": audit, "key_prefix": "active_guide"},
        ).run()

        self.assertEqual(list(app.exception), [])
        self.assertEqual(len(app.number_input), 6)
        self.assertTrue(any("조건 확인 후 분할 접근 검토" in item.value for item in app.success))
        metric_values = [item.value for item in app.metric]
        self.assertIn("20주", metric_values)
        self.assertIn("2.00R", " ".join(item.value for item in app.caption))
        self.assertTrue(any("what-if" in item.value for item in app.caption))
        self.assertFalse(app.metric[0].delta)
        self.assertFalse(any(item.key == "trade_plan_ui_save_entry__active_guide" for item in app.button))

        next(
            item for item in app.number_input if item.key == "trade_plan_sensitive_active_guide_entry_price"
        ).set_value(120.0)
        app.run()
        self.assertEqual(list(app.exception), [])
        self.assertTrue(any("1차 목표" in item.value for item in app.warning))

    def test_waiting_plan_does_not_render_position_inputs(self):
        waiting = _active_meta(status="TRIGGER_WAIT")

        app = AppTest.from_function(
            _render_guide_app,
            kwargs={"meta": waiting, "key_prefix": "waiting_guide"},
        ).run()

        self.assertEqual(list(app.exception), [])
        self.assertEqual(len(app.number_input), 0)
        self.assertTrue(any("확인 조건 대기" in item.value for item in app.info))
        self.assertTrue(any("진입 후 재계산" in item.value for item in app.metric))

    def test_holding_toggle_calculates_existing_long_position_separately(self):
        app = AppTest.from_function(
            _render_guide_app,
            kwargs={"meta": _active_meta(), "key_prefix": "holding_guide"},
        ).run()

        next(
            item for item in app.toggle if item.key == "trade_plan_sensitive_holding_guide_holding_enabled"
        ).set_value(True)
        app.run()
        next(
            item for item in app.number_input
            if item.key == "trade_plan_sensitive_holding_guide_holding_average_entry"
        ).set_value(100.0)
        next(
            item for item in app.number_input if item.key == "trade_plan_sensitive_holding_guide_holding_quantity"
        ).set_value(10.0)
        next(
            item for item in app.number_input
            if item.key == "trade_plan_sensitive_holding_guide_holding_current_price"
        ).set_value(105.0)
        next(
            item for item in app.number_input if item.key == "trade_plan_sensitive_holding_guide_holding_user_stop"
        ).set_value(95.0)
        next(
            item for item in app.number_input
            if item.key == "trade_plan_sensitive_holding_guide_holding_account_size"
        ).set_value(10_000.0)
        app.run()

        self.assertEqual(list(app.exception), [])
        metric_values = [item.value for item in app.metric]
        self.assertIn("+50.00", metric_values)
        self.assertIn("+5.00%", metric_values)
        self.assertIn("100.00", metric_values)
        self.assertTrue(any("보유 계획 범위 점검" in item.value for item in app.success))
        self.assertTrue(any("입력칸에 자동 반영하지 않습니다" in item.value for item in app.caption))
        self.assertTrue(any("계좌 대비 비율: -0.50%" in item.value for item in app.caption))

    def test_sell_judgment_still_allows_opt_in_holding_defense_review(self):
        meta = {
            "ticker": "AAPL",
            "judgment": "SELL",
            "price": 90.0,
            "summary_price_available": True,
            "summary_date": "2026-07-10",
            "strategy_visible_results": [],
            "strategy_summary": {"conflict_level": "LOW", "top_strategy": None},
        }
        app = AppTest.from_function(
            _render_guide_app,
            kwargs={"meta": meta, "key_prefix": "defend_guide"},
        ).run()

        next(
            item for item in app.toggle if item.key == "trade_plan_sensitive_defend_guide_holding_enabled"
        ).set_value(True)
        app.run()
        next(
            item for item in app.number_input
            if item.key == "trade_plan_sensitive_defend_guide_holding_average_entry"
        ).set_value(100.0)
        next(
            item for item in app.number_input if item.key == "trade_plan_sensitive_defend_guide_holding_quantity"
        ).set_value(10.0)
        next(
            item for item in app.number_input if item.key == "trade_plan_sensitive_defend_guide_holding_user_stop"
        ).set_value(85.0)
        app.run()

        self.assertEqual(list(app.exception), [])
        self.assertTrue(any("보유분 방어 재검토" in item.value for item in app.warning))
        self.assertTrue(any("자동 매도 지시" in item.value for item in app.warning))

    def test_valid_entry_ticket_saves_once_without_account_size_or_quantity_by_default(self):
        app = AppTest.from_function(
            _render_guide_app,
            kwargs={
                "meta": _active_meta(),
                "key_prefix": "save_guide",
                "allow_plan_save": True,
            },
        ).run()

        save = next(item for item in app.button if item.key == "trade_plan_ui_save_entry__save_guide")
        save.click()
        app.run()

        self.assertEqual(list(app.exception), [])
        plans = app.session_state["_trade_plans_v1"]
        self.assertEqual(len(plans), 1)
        self.assertEqual(plans[0]["plan_type"], "ENTRY_LONG")
        self.assertIsNone(plans[0]["user_inputs"]["planned_quantity"])
        self.assertNotIn("account_size", plans[0]["user_inputs"])
        next(item for item in app.button if item.key == "trade_plan_ui_save_entry__save_guide").click()
        app.run()
        self.assertEqual(len(app.session_state["_trade_plans_v1"]), 1)
        self.assertTrue(any("이미 저장" in item.value for item in app.info))

    def test_invalid_edited_entry_does_not_render_save_action(self):
        app = AppTest.from_function(
            _render_guide_app,
            kwargs={
                "meta": _active_meta(),
                "key_prefix": "invalid_save_guide",
                "allow_plan_save": True,
            },
        ).run()
        next(
            item for item in app.number_input
            if item.key == "trade_plan_sensitive_invalid_save_guide_entry_price"
        ).set_value(120.0)
        app.run()

        self.assertTrue(any("1차 목표" in item.value for item in app.warning))
        self.assertFalse(
            any(item.key == "trade_plan_ui_save_entry__invalid_save_guide" for item in app.button)
        )

    def test_holding_plan_requires_user_stop_and_saves_fractional_sensitive_inputs(self):
        app = AppTest.from_function(
            _render_guide_app,
            kwargs={
                "meta": _active_meta(),
                "key_prefix": "holding_save",
                "allow_plan_save": True,
            },
        ).run()
        next(
            item for item in app.toggle if item.key == "trade_plan_sensitive_holding_save_holding_enabled"
        ).set_value(True)
        app.run()
        next(
            item for item in app.number_input
            if item.key == "trade_plan_sensitive_holding_save_holding_average_entry"
        ).set_value(100.0)
        next(
            item for item in app.number_input if item.key == "trade_plan_sensitive_holding_save_holding_quantity"
        ).set_value(0.75)
        next(
            item for item in app.number_input
            if item.key == "trade_plan_sensitive_holding_save_holding_current_price"
        ).set_value(105.0)
        app.run()
        self.assertFalse(
            any(item.key == "trade_plan_ui_save_holding__holding_save_holding" for item in app.button)
        )

        next(
            item for item in app.number_input if item.key == "trade_plan_sensitive_holding_save_holding_user_stop"
        ).set_value(95.0)
        app.run()
        next(
            item for item in app.button if item.key == "trade_plan_ui_save_holding__holding_save_holding"
        ).click()
        app.run()

        plans = app.session_state["_trade_plans_v1"]
        self.assertEqual(len(plans), 1)
        self.assertEqual(plans[0]["plan_type"], "HOLDING_LONG")
        self.assertEqual(plans[0]["user_inputs"]["quantity"], 0.75)
        self.assertEqual(plans[0]["privacy"]["sensitive_fields"], ["average_entry", "quantity"])
        self.assertNotIn("account_size", plans[0]["user_inputs"])

    def test_separate_app_sessions_do_not_share_saved_plans(self):
        first = AppTest.from_function(
            _render_guide_app,
            kwargs={"meta": _active_meta(), "key_prefix": "isolated", "allow_plan_save": True},
        ).run()
        next(item for item in first.button if item.key == "trade_plan_ui_save_entry__isolated").click()
        first.run()

        second = AppTest.from_function(
            _render_guide_app,
            kwargs={"meta": _active_meta(), "key_prefix": "isolated", "allow_plan_save": True},
        ).run()

        self.assertEqual(len(first.session_state["_trade_plans_v1"]), 1)
        self.assertNotIn("_trade_plans_v1", second.session_state)


if __name__ == "__main__":
    unittest.main()
