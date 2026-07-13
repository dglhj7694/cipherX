import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bootstrap.session_defaults import build_default_session_state, clear_session_namespace


class SessionDefaultsTests(unittest.TestCase):
    def test_trade_plan_defaults_are_isolated_between_sessions(self):
        first = build_default_session_state([], "홈")
        second = build_default_session_state([], "홈")

        self.assertEqual(first["_trade_plans_v1"], [])
        self.assertIsNone(first["_trade_plan_pending_delete_id"])
        self.assertIsNot(first["_trade_plans_v1"], second["_trade_plans_v1"])
        first["_trade_plans_v1"].append({"plan_id": "one"})
        self.assertEqual(second["_trade_plans_v1"], [])

    def test_clear_session_namespace_only_removes_trade_plan_widgets(self):
        state = {
            "trade_plan_ui_status_one": "PLANNED",
            "trade_plan_ui_upload": b"data",
            "runtime_gemini_api_key": "keep",
            "messages": [1],
        }

        removed = clear_session_namespace("trade_plan_ui_", state)

        self.assertEqual(removed, 2)
        self.assertEqual(state, {"runtime_gemini_api_key": "keep", "messages": [1]})

    def test_sensitive_trade_inputs_have_a_separate_reset_namespace(self):
        state = {
            "trade_plan_sensitive_analysis_account_size": 999_999.0,
            "trade_plan_sensitive_analysis_holding_average_entry": 123.45,
            "trade_plan_ui_status_one": "PLANNED",
            "messages": [1],
        }

        removed = clear_session_namespace("trade_plan_sensitive_", state)

        self.assertEqual(removed, 2)
        self.assertEqual(state, {"trade_plan_ui_status_one": "PLANNED", "messages": [1]})


if __name__ == "__main__":
    unittest.main()
