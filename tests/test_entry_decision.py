import unittest

import pandas as pd

from engine_runtime.entry_decision import (
    apply_adjusted_decision_fields,
    apply_entry_decision_fields,
    compute_entry_decision_row,
)


class EntryDecisionTests(unittest.TestCase):
    def _buy_row(self, **overrides):
        row = {
            "Trade_Judgment": "BUY",
            "price": 100.0,
            "rr": 1.8,
            "chg": 1.2,
            "chg_5d": 4.0,
            "volume_ratio_20": 1.45,
            "strategy_conflict_level": "LOW",
            "low_conflict_bullish": True,
            "thin_trade_risk": False,
            "bearish_gap_failure": False,
            "multi_sell": 0,
            "hma_ema_long_entry": True,
            "latest_session_utbot_buy_turn": True,
        }
        row.update(overrides)
        return row

    def test_buy_plus_sharp_extension_is_chase_risk(self):
        result = compute_entry_decision_row(self._buy_row(chg=13.0, chg_5d=21.0))

        self.assertEqual(result["direction_judgment"], "BUY")
        self.assertEqual(result["entry_judgment"], "CHASE_RISK")
        self.assertEqual(result["position_action"], "WATCHLIST")
        self.assertTrue(result["entry_chase_risk"])

    def test_buy_low_conflict_volume_and_rr_enters_now_with_low_risk(self):
        result = compute_entry_decision_row(self._buy_row())

        self.assertEqual(result["entry_judgment"], "ENTER_NOW")
        self.assertEqual(result["risk_judgment"], "LOW")
        self.assertEqual(result["position_action"], "BUY_NOW")

    def test_sell_turn_exits_or_avoids_with_high_risk(self):
        result = compute_entry_decision_row(
            {
                "Trade_Judgment": "SELL",
                "price": 100.0,
                "rr": 0.8,
                "chg": -2.0,
                "volume_ratio_20": 1.1,
                "same_session_sell_turn": True,
                "strategy_conflict_level": "HIGH",
                "multi_sell": 2,
            }
        )

        self.assertEqual(result["direction_judgment"], "SELL")
        self.assertEqual(result["entry_judgment"], "EXIT_OR_AVOID")
        self.assertEqual(result["risk_judgment"], "HIGH")
        self.assertEqual(result["position_action"], "SELL_OR_EXIT")

    def test_adjusted_fields_do_not_mutate_original_contract_fields(self):
        df = pd.DataFrame(
            [
                {
                    **self._buy_row(chg=13.0),
                    "Final_Decision_Score": 42.0,
                    "Judgment_Confidence": 76.0,
                    "Downgrade_Count": 1,
                }
            ]
        )

        apply_entry_decision_fields(df)
        apply_adjusted_decision_fields(df)

        self.assertEqual(float(df.loc[0, "Final_Decision_Score"]), 42.0)
        self.assertEqual(float(df.loc[0, "Judgment_Confidence"]), 76.0)
        self.assertIn("final_adjusted_score", df.columns)
        self.assertIn("final_adjusted_confidence", df.columns)
        self.assertLess(float(df.loc[0, "final_adjusted_score"]), 42.0)


if __name__ == "__main__":
    unittest.main()
