import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.test_trade_plan_service import _entry_plan, _guide, _holding_plan, _meta
from tests.test_trade_plan_workspace_app import _render_workspace_app
from services.trade_plan_service import encode_trade_plan_bundle


HOLDING_ID = "32345678-1234-4234-8234-123456789abc"
SECOND_ENTRY_ID = "22345678-1234-4234-8234-123456789abc"
TOKEN = hashlib.sha256("계좌 통화".encode("utf-8")).hexdigest()[:10]
PREFIX = "trade_plan_sensitive_portfolio"


def _render_risk_app(plans):
    import copy

    from app_ui.components.portfolio_risk_workspace import render_portfolio_risk_workspace

    render_portfolio_risk_workspace(copy.deepcopy(plans))


def _input(app, key):
    return next(item for item in app.number_input if item.key == key)


def _check(app, key):
    return next(item for item in app.checkbox if item.key == key)


def _check_label(app, text):
    return next(item for item in app.checkbox if text in item.label)


class PortfolioRiskWorkspaceAppTests(unittest.TestCase):
    def test_combined_scenario_recalculates_and_surfaces_user_limit_breach(self):
        entry = _entry_plan()["plan"]
        holding = _holding_plan(plan_id=HOLDING_ID)["plan"]
        original = copy.deepcopy([entry, holding])
        app = AppTest.from_function(_render_risk_app, kwargs={"plans": [entry, holding]}).run()

        _check_label(app, "통화임을 확인").set_value(True)
        _input(app, f"{PREFIX}_{TOKEN}_account_size").set_value(10_000.0)
        _input(app, f"{PREFIX}_{TOKEN}_risk_limit").set_value(1.5)
        _input(app, f"{PREFIX}_{TOKEN}_exposure_limit").set_value(100.0)
        _input(app, f"{PREFIX}_{TOKEN}_ticker_limit").set_value(50.0)
        _check(app, f"{PREFIX}_entry_{entry['plan_id']}").set_value(True)
        _check(app, f"{PREFIX}_holding_{holding['plan_id']}").set_value(True)
        app.run()

        _input(app, f"{PREFIX}_holding_average_{holding['plan_id']}").set_value(40.0)
        _input(app, f"{PREFIX}_holding_quantity_{holding['plan_id']}").set_value(20.0)
        _input(app, f"{PREFIX}_holding_price_{holding['plan_id']}").set_value(50.0)
        _input(app, f"{PREFIX}_holding_stop_{holding['plan_id']}").set_value(45.0)
        app.run()

        _check_label(app, "증권사 최신값과 대조").set_value(True)
        _check_label(app, "이번 점검에 반영할 실제 보유").set_value(True)
        app.run()
        _check_label(app, "모두 계획가에 체결된 동시 가정").set_value(True)
        app.run()

        self.assertEqual(list(app.exception), [])
        self.assertTrue(any("위험예산 또는 노출 한도" in item.value for item in app.error))
        metric_values = [item.value for item in app.metric]
        self.assertIn("3,000.00 (30.00%)", metric_values)
        self.assertIn("200.00 (2.00%)", metric_values)
        self.assertTrue(app.dataframe)
        self.assertEqual([entry, holding], original)
        self.assertNotIn('"account_size"', json.dumps(original))

        _input(app, f"{PREFIX}_holding_price_{holding['plan_id']}").set_value(51.0)
        app.run()
        self.assertFalse(_check_label(app, "증권사 최신값과 대조").value)
        self.assertFalse(_check_label(app, "모두 계획가에 체결된 동시 가정").value)
        self.assertFalse(any("위험예산 기준 이내" in item.value for item in app.success))

    def test_stop_reached_is_rendered_as_urgent_not_safe(self):
        holding = _holding_plan(plan_id=HOLDING_ID)["plan"]
        app = AppTest.from_function(_render_risk_app, kwargs={"plans": [holding]}).run()

        _check_label(app, "통화임을 확인").set_value(True)
        _input(app, f"{PREFIX}_{TOKEN}_account_size").set_value(10_000.0)
        _input(app, f"{PREFIX}_{TOKEN}_risk_limit").set_value(3.0)
        _check(app, f"{PREFIX}_holding_{holding['plan_id']}").set_value(True)
        app.run()
        _input(app, f"{PREFIX}_holding_price_{holding['plan_id']}").set_value(94.0)
        _input(app, f"{PREFIX}_holding_stop_{holding['plan_id']}").set_value(95.0)
        app.run()

        _check_label(app, "증권사 최신값과 대조").set_value(True)
        _check_label(app, "이번 점검에 반영할 실제 보유").set_value(True)
        app.run()

        self.assertEqual(list(app.exception), [])
        self.assertTrue(any("사용자 방어선 이하" in item.value for item in app.error))
        self.assertFalse(any("위험예산 기준 이내" in item.value for item in app.success))
        self.assertIn("987.00 (9.87%)", [item.value for item in app.metric])
        self.assertIn("긴급 미산정", [item.value for item in app.metric])

    def test_workspace_renders_portfolio_check_once_and_keeps_backup_available(self):
        entry = _entry_plan()["plan"]
        app = AppTest.from_function(
            _render_workspace_app,
            kwargs={"plans": [entry], "current_meta": _meta()},
        ).run()

        next(
            item for item in app.toggle if item.key == "trade_plan_ui_test_portfolio_risk_enabled"
        ).set_value(True)
        app.run()

        self.assertEqual(list(app.exception), [])
        self.assertEqual(sum("계좌 위험예산 점검" in item.value for item in app.markdown), 1)
        self.assertTrue(any(item.key == f"{PREFIX}_{TOKEN}_account_size" for item in app.number_input))
        self.assertEqual(len(app.get("download_button")), 1)

        _input(app, f"{PREFIX}_{TOKEN}_account_size").set_value(88_888.0)
        app.run()
        encoded = encode_trade_plan_bundle(list(app.session_state["_trade_plans_v1"]))
        self.assertTrue(encoded["valid"])
        self.assertNotIn('"account_size":', encoded["data"].decode("utf-8"))

    def test_separate_app_sessions_do_not_share_account_input(self):
        entry = _entry_plan()["plan"]
        first = AppTest.from_function(_render_risk_app, kwargs={"plans": [entry]}).run()
        _input(first, f"{PREFIX}_{TOKEN}_account_size").set_value(77_777.0)
        first.run()
        second = AppTest.from_function(_render_risk_app, kwargs={"plans": [entry]}).run()

        self.assertEqual(_input(first, f"{PREFIX}_{TOKEN}_account_size").value, 77_777.0)
        self.assertEqual(_input(second, f"{PREFIX}_{TOKEN}_account_size").value, 0.0)

    def test_confirmations_reset_when_currency_scope_or_holding_values_change(self):
        first_entry = _entry_plan()["plan"]
        second_entry = _entry_plan(_guide(ticker="MSFT"), plan_id=SECOND_ENTRY_ID)["plan"]
        app = AppTest.from_function(
            _render_risk_app,
            kwargs={"plans": [first_entry, second_entry]},
        ).run()

        _check_label(app, "통화임을 확인").set_value(True)
        _input(app, f"{PREFIX}_{TOKEN}_account_size").set_value(10_000.0)
        _input(app, f"{PREFIX}_{TOKEN}_risk_limit").set_value(3.0)
        _check(app, f"{PREFIX}_entry_{first_entry['plan_id']}").set_value(True)
        _check(app, f"{PREFIX}_entry_{second_entry['plan_id']}").set_value(True)
        app.run()
        _check_label(app, "이번 점검에 반영할 실제 보유").set_value(True)
        app.run()
        self.assertTrue(any("위험예산 기준 이내" in item.value for item in app.success))

        _check(app, f"{PREFIX}_entry_{second_entry['plan_id']}").set_value(False)
        app.run()
        self.assertFalse(_check_label(app, "이번 점검에 반영할 실제 보유").value)
        self.assertFalse(any("위험예산 기준 이내" in item.value for item in app.success))

        next(item for item in app.text_input if item.key == f"{PREFIX}_{TOKEN}_currency_code").set_value("KRW")
        app.run()
        self.assertFalse(_check_label(app, "통화임을 확인").value)

    def test_saved_holding_defaults_require_fresh_confirmation_and_edits_reset_it(self):
        holding = _holding_plan(plan_id=HOLDING_ID)["plan"]
        app = AppTest.from_function(_render_risk_app, kwargs={"plans": [holding]}).run()

        _check_label(app, "통화임을 확인").set_value(True)
        _input(app, f"{PREFIX}_{TOKEN}_account_size").set_value(10_000.0)
        _input(app, f"{PREFIX}_{TOKEN}_risk_limit").set_value(3.0)
        _check(app, f"{PREFIX}_holding_{holding['plan_id']}").set_value(True)
        app.run()
        _check_label(app, "이번 점검에 반영할 실제 보유").set_value(True)
        app.run()

        self.assertFalse(any("위험예산 기준 이내" in item.value for item in app.success))
        self.assertTrue(any("최신값 대조 확인 전" in item.value for item in app.warning))

        _check_label(app, "증권사 최신값과 대조").set_value(True)
        app.run()
        self.assertTrue(any("위험예산 기준 이내" in item.value for item in app.success))

        _input(app, f"{PREFIX}_holding_price_{holding['plan_id']}").set_value(106.0)
        app.run()
        self.assertFalse(_check_label(app, "증권사 최신값과 대조").value)
        self.assertFalse(any("위험예산 기준 이내" in item.value for item in app.success))

    def test_plan_deletion_clears_portfolio_sensitive_widget_state(self):
        entry = _entry_plan()["plan"]
        app = AppTest.from_function(
            _render_workspace_app,
            kwargs={"plans": [entry], "current_meta": _meta()},
        ).run()
        next(
            item for item in app.toggle if item.key == "trade_plan_ui_test_portfolio_risk_enabled"
        ).set_value(True)
        app.run()
        _input(app, f"{PREFIX}_{TOKEN}_account_size").set_value(77_777.0)
        app.run()
        self.assertTrue(
            any(str(key).startswith(PREFIX) for key in app.session_state.filtered_state)
        )

        next(
            item
            for item in app.button
            if item.key == f"trade_plan_ui_test_delete_request_{entry['plan_id']}"
        ).click()
        app.run()
        next(
            item
            for item in app.button
            if item.key == f"trade_plan_ui_test_delete_confirm_{entry['plan_id']}"
        ).click()
        app.run()

        self.assertEqual(app.session_state["_trade_plans_v1"], [])
        self.assertFalse(
            any(str(key).startswith(PREFIX) for key in app.session_state.filtered_state)
        )


if __name__ == "__main__":
    unittest.main()
