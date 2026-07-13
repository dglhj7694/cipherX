import copy
import sys
import unittest
from pathlib import Path

import streamlit as st
from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.test_trade_plan_service import _entry_plan, _holding_plan, _meta


def _render_workspace_app(plans, current_meta=None):
    import copy
    import streamlit as st

    from app_ui.components.trade_plan_workspace import render_trade_plan_workspace

    if "_trade_plans_v1" not in st.session_state:
        st.session_state["_trade_plans_v1"] = copy.deepcopy(plans)
    if "_trade_plan_pending_delete_id" not in st.session_state:
        st.session_state["_trade_plan_pending_delete_id"] = None
    render_trade_plan_workspace(current_meta=current_meta, key_prefix="trade_plan_ui_test")


def _render_combined_plan_app(current_meta):
    import streamlit as st

    from app_ui.components.beginner_trade_guide import render_beginner_trade_guide
    from app_ui.components.trade_plan_workspace import render_trade_plan_workspace

    if "_trade_plans_v1" not in st.session_state:
        st.session_state["_trade_plans_v1"] = []
    if "_trade_plan_pending_delete_id" not in st.session_state:
        st.session_state["_trade_plan_pending_delete_id"] = None
    render_trade_plan_workspace(current_meta=current_meta, key_prefix="trade_plan_ui_combined")
    render_beginner_trade_guide(
        current_meta,
        key_prefix="combined_guide",
        allow_plan_save=True,
    )


class TradePlanWorkspaceAppTests(unittest.TestCase):
    def test_entry_save_reruns_workspace_with_current_count_and_flash(self):
        app = AppTest.from_function(_render_combined_plan_app, kwargs={"current_meta": _meta()}).run()

        next(item for item in app.button if item.key == "trade_plan_ui_save_entry__combined_guide").click()
        app.run()

        self.assertEqual(list(app.exception), [])
        self.assertEqual(len(app.session_state["_trade_plans_v1"]), 1)
        self.assertTrue(any("내 매매계획 · 1/20" in item.label for item in app.expander))
        self.assertFalse(any("아직 저장된 계획" in item.value for item in app.info))
        self.assertTrue(any("신규 진입 계획" in item.value for item in app.success))

    def test_save_flash_surfaces_second_target_adjustment(self):
        app = AppTest.from_function(_render_combined_plan_app, kwargs={"current_meta": _meta()}).run()
        next(
            item for item in app.number_input
            if item.key == "trade_plan_sensitive_combined_guide_target_price"
        ).set_value(120.0)
        app.run()
        next(item for item in app.button if item.key == "trade_plan_ui_save_entry__combined_guide").click()
        app.run()

        self.assertEqual(list(app.exception), [])
        self.assertIsNone(app.session_state["_trade_plans_v1"][0]["user_inputs"]["target_2"])
        self.assertTrue(any("2차 목표" in item.value for item in app.warning))

    def test_workspace_renders_one_copy_with_download_import_and_matched_plan(self):
        plan = _entry_plan()["plan"]
        app = AppTest.from_function(
            _render_workspace_app,
            kwargs={"plans": [plan], "current_meta": _meta()},
        ).run()

        self.assertEqual(list(app.exception), [])
        self.assertEqual(len(app.get("file_uploader")), 1)
        self.assertEqual(len(app.get("download_button")), 1)
        self.assertTrue(any("내 매매계획 · 1/20" in item.label for item in app.expander))
        self.assertTrue(any("현재 분석 일치" in item.value for item in app.success))
        metric_values = [item.value for item in app.metric]
        self.assertIn("100.00", metric_values)
        self.assertIn("2.00R", metric_values)
        self.assertTrue(any("가정 2차 목표 115.00" in item.value for item in app.caption))

    def test_holding_review_warning_is_visible_even_if_manual_status_is_monitoring(self):
        from services.trade_plan_service import update_trade_plan_status

        risky = _holding_plan(evaluation_price=90.0, user_stop_price=95.0)["plan"]
        monitoring = update_trade_plan_status(
            [risky],
            risky["plan_id"],
            "MONITORING",
            now="2026-07-14T00:00:00Z",
        )["plans"][0]
        app = AppTest.from_function(
            _render_workspace_app,
            kwargs={"plans": [monitoring], "current_meta": _meta()},
        ).run()

        self.assertEqual(list(app.exception), [])
        self.assertTrue(any("보유 방어계획은 재검토" in item.value for item in app.warning))
        self.assertTrue(any("방어선 도달" in item.value for item in app.warning))

    def test_manual_status_update_preserves_plan_and_increments_version(self):
        plan = _entry_plan()["plan"]
        app = AppTest.from_function(
            _render_workspace_app,
            kwargs={"plans": [plan], "current_meta": _meta()},
        ).run()
        plan_id = plan["plan_id"]
        next(item for item in app.selectbox if item.key == f"trade_plan_ui_test_status_{plan_id}").set_value(
            "CANCELLED"
        )
        next(item for item in app.button if item.key == f"trade_plan_ui_test_status_save_{plan_id}").click()
        app.run()

        saved = app.session_state["_trade_plans_v1"][0]
        self.assertEqual(saved["status"], "CANCELLED")
        self.assertEqual(saved["plan_version"], 2)
        self.assertEqual(saved["analysis_snapshot"], plan["analysis_snapshot"])

    def test_delete_requires_confirmation_and_cancel_keeps_plan(self):
        plan = _entry_plan()["plan"]
        plan_id = plan["plan_id"]
        app = AppTest.from_function(
            _render_workspace_app,
            kwargs={"plans": [plan], "current_meta": _meta()},
        ).run()

        next(item for item in app.button if item.key == f"trade_plan_ui_test_delete_request_{plan_id}").click()
        app.run()
        self.assertEqual(len(app.session_state["_trade_plans_v1"]), 1)
        self.assertTrue(any("삭제할까요" in item.value for item in app.warning))
        next(item for item in app.button if item.key == f"trade_plan_ui_test_delete_cancel_{plan_id}").click()
        app.run()
        self.assertEqual(len(app.session_state["_trade_plans_v1"]), 1)

        next(item for item in app.button if item.key == f"trade_plan_ui_test_delete_request_{plan_id}").click()
        app.run()
        next(item for item in app.button if item.key == f"trade_plan_ui_test_delete_confirm_{plan_id}").click()
        app.run()
        self.assertEqual(app.session_state["_trade_plans_v1"], [])

    def test_separate_workspace_sessions_are_isolated(self):
        plan = _entry_plan()["plan"]
        first = AppTest.from_function(
            _render_workspace_app,
            kwargs={"plans": [plan], "current_meta": _meta()},
        ).run()
        second = AppTest.from_function(
            _render_workspace_app,
            kwargs={"plans": [], "current_meta": _meta()},
        ).run()

        self.assertEqual(len(first.session_state["_trade_plans_v1"]), 1)
        self.assertEqual(second.session_state["_trade_plans_v1"], [])
        self.assertTrue(any("아직 저장된 계획" in item.value for item in second.info))


if __name__ == "__main__":
    unittest.main()
