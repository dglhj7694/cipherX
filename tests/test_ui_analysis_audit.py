import sys
import unittest
from pathlib import Path
from unittest.mock import call, patch


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import ui_localized


class _TabContext:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False


class AnalysisAuditTabTests(unittest.TestCase):
    def test_render_analysis_adds_audit_tab_and_renders_payload(self):
        audit = {"available": True, "ticker": "AAPL", "summary": {}}
        tabs = [_TabContext() for _ in range(8)]
        message = {"meta": {"ticker": "AAPL"}, "fig_json": None, "audit": audit}

        with (
            patch.object(ui_localized.st, "tabs", return_value=tabs) as tabs_mock,
            patch.object(ui_localized, "render_price_header"),
            patch.object(ui_localized, "render_beginner_trade_guide") as beginner_mock,
            patch.object(ui_localized, "render_judgment_card"),
            patch.object(ui_localized.st, "markdown"),
            patch.object(ui_localized, "render_committee_panel_clean"),
            patch.object(ui_localized, "render_leading_lagging"),
            patch.object(ui_localized, "render_indicator_help"),
            patch.object(ui_localized, "render_10layer_bars_clean"),
            patch.object(ui_localized, "render_combined_scans"),
            patch.object(ui_localized, "_render_startup9_confirm_tab"),
            patch.object(ui_localized, "render_audit_panel") as audit_mock,
            patch.object(ui_localized, "render_company_details"),
        ):
            ui_localized.render_analysis(message, key_prefix="analysis_test", allow_plan_save=True)

        tab_labels = tabs_mock.call_args.args[0]
        self.assertEqual(len(tab_labels), 8)
        self.assertEqual(tab_labels[0], "초보자 가이드")
        self.assertIn("성과/검증", tab_labels)
        beginner_mock.assert_called_once_with(
            message["meta"],
            audit=audit,
            key_prefix="analysis_test_beginner",
            allow_plan_save=True,
        )
        audit_mock.assert_called_once_with(audit)

    def test_render_analysis_passes_empty_audit_to_safe_panel(self):
        tabs = [_TabContext() for _ in range(8)]
        message = {"meta": {"ticker": "AAPL"}, "fig_json": None, "audit": None}

        with (
            patch.object(ui_localized.st, "tabs", return_value=tabs),
            patch.object(ui_localized, "render_price_header"),
            patch.object(ui_localized, "render_beginner_trade_guide") as beginner_mock,
            patch.object(ui_localized, "render_judgment_card"),
            patch.object(ui_localized.st, "markdown"),
            patch.object(ui_localized, "render_committee_panel_clean"),
            patch.object(ui_localized, "render_leading_lagging"),
            patch.object(ui_localized, "render_indicator_help"),
            patch.object(ui_localized, "render_10layer_bars_clean"),
            patch.object(ui_localized, "render_combined_scans"),
            patch.object(ui_localized, "_render_startup9_confirm_tab"),
            patch.object(ui_localized, "render_audit_panel") as audit_mock,
            patch.object(ui_localized, "render_company_details"),
        ):
            ui_localized.render_analysis(message, key_prefix="analysis_test")

        beginner_mock.assert_called_once_with(
            message["meta"],
            audit=None,
            key_prefix="analysis_test_beginner",
            allow_plan_save=False,
        )
        audit_mock.assert_called_once_with(None)

    def test_render_audit_panel_handles_missing_and_unavailable_payloads(self):
        with patch.object(ui_localized.st, "info") as info_mock:
            ui_localized.render_audit_panel(None)
            ui_localized.render_audit_panel({})
            ui_localized.render_audit_panel({"available": False, "reason": "표본 부족"})

        self.assertEqual(info_mock.call_count, 3)
        self.assertIn("백테스트/감사 표본이 아직 부족합니다.", info_mock.call_args_list[0].args)
        self.assertIn("백테스트/감사 표본이 아직 부족합니다.", info_mock.call_args_list[1].args)
        self.assertEqual(info_mock.call_args_list[2], call("표본 부족"))


if __name__ == "__main__":
    unittest.main()
