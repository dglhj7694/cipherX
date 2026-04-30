import csv
import io
import unittest

import pandas as pd

from scanner_csv import (
    CORE_SIGNAL_GROUP,
    build_detected_signal_payload,
    scanner_csv_dictionary_to_csv_bytes,
    scanner_csv_field_specs,
    scanner_rows_to_csv_bytes,
    summarize_detected_signal_items,
)


class ScannerCsvExportTests(unittest.TestCase):
    def _localize_combo(self, key, kor, desc):
        return str(kor or key), str(desc or "")

    def _localize_signal(self, key, _kor, _desc):
        labels = {
            "System_Turn_Bull": "시스템 매수 전환",
            "Trend_Inflection_Bull": "추세 전환 강세",
            "UTBot_Buy": "UTBot 매수",
            "UTBot_Sell": "UTBot 매도",
            "Hull_Turn_Bull": "Hull 상승 전환",
            "Hull_Turn_Bear": "Hull 하락 전환",
            "EMA_Pullback_Buy": "EMA 눌림목 매수",
            "EMA_Pullback_Sell": "EMA 눌림목 매도",
            "Volume_Surge": "거래량 급증",
            "Volume_Climax_Buy": "거래량 클라이맥스 매수",
            "Volume_Climax_Sell": "거래량 클라이맥스 매도",
        }
        return labels.get(str(key), str(key)), ""

    def test_detected_signal_payload_groups_last_5_bars(self):
        idx = pd.date_range("2026-04-10", periods=8, freq="D")
        frame = pd.DataFrame(index=idx)

        for column in (
            "CS_Trend_Pullback_Buy",
            "CS_Triple_Confirm_Buy",
            "UTBot_Buy",
            "UTBot_Sell",
            "Hull_Turn_Bull",
            "Hull_Turn_Bear",
            "System_Turn_Bull",
            "Trend_Inflection_Bull",
            "EMA_Pullback_Buy",
            "EMA_Pullback_Sell",
            "Volume_Surge",
            "Volume_Climax_Buy",
            "Volume_Climax_Sell",
        ):
            frame[column] = False

        # Recent 5-bar window is idx[-5:] == 2026-04-13 .. 2026-04-17
        frame.loc[idx[-1], "CS_Trend_Pullback_Buy"] = True
        frame.loc[idx[-3], "CS_Triple_Confirm_Buy"] = True
        frame.loc[idx[-1], "UTBot_Buy"] = True
        frame.loc[idx[-2], "Hull_Turn_Bear"] = True
        frame.loc[idx[-4], "System_Turn_Bull"] = True
        frame.loc[idx[-2], "EMA_Pullback_Buy"] = True
        frame.loc[idx[-1], "Volume_Surge"] = True
        frame.loc[idx[1], "Trend_Inflection_Bull"] = True  # out of window

        combo_registry = {
            "CS_Trend_Pullback_Buy": {"kor": "트렌드 눌림목", "desc": "", "dir": "buy", "tier": 2, "icon": "◆"},
            "CS_Triple_Confirm_Buy": {"kor": "삼중 확인 매수", "desc": "", "dir": "buy", "tier": 1, "icon": "★"},
        }
        transition_cfg = {
            "UTBot_Buy": {"label": "UTBot 전환↑", "icon": "▲", "dir": "buy"},
            "UTBot_Sell": {"label": "UTBot 전환↓", "icon": "▼", "dir": "sell"},
            "Hull_Turn_Bull": {"label": "Hull 전환↑", "icon": "▲", "dir": "buy"},
            "Hull_Turn_Bear": {"label": "Hull 전환↓", "icon": "▼", "dir": "sell"},
        }

        payload = build_detected_signal_payload(
            frame=frame,
            recent_window=5,
            combo_registry=combo_registry,
            transition_cfg=transition_cfg,
            core_signal_cfg=CORE_SIGNAL_GROUP,
            localize_combo_fn=self._localize_combo,
            localize_signal_fn=self._localize_signal,
            summary_limit=8,
        )

        self.assertEqual(payload["detected_combo_count"], 2)
        self.assertEqual(payload["detected_transition_count"], 2)
        self.assertEqual(payload["detected_core_count"], 5)
        self.assertEqual(payload["detected_signal_total_count"], 7)
        self.assertEqual(payload["detected_buy_signal_latest_date"], "2026-04-17")
        self.assertEqual(payload["detected_signal_latest_date"], "2026-04-17")
        self.assertTrue(payload["utbot_buy_recent"])
        self.assertEqual(payload["utbot_buy_last_date"], "2026-04-17")
        self.assertTrue(payload["hull_turn_bear_recent"])
        self.assertEqual(payload["hull_turn_bear_last_date"], "2026-04-16")

        self.assertIn("UTBot 전환↑(2026-04-17)", payload["detected_transition_summary"])
        self.assertIn(" | ", payload["detected_core_summary"])

    def test_summary_format_and_overflow_suffix(self):
        items = [
            {"label": "A", "date": "2026-04-14"},
            {"label": "B", "date": "2026-04-13"},
            {"label": "C", "date": "2026-04-12"},
        ]
        summary = summarize_detected_signal_items(items, limit=2)
        self.assertEqual(summary, "A(2026-04-14) | B(2026-04-13) | +1개")

    def test_csv_headers_and_bool_normalization(self):
        row = {
            "ticker": "AAPL",
            "price": 182.34,
            "chg": 1.25,
            "scan_score": 18.6,
            "strength": 22.1,
            "jg": "매수",
            "jg_key": "BUY",
            "action": "매수",
            "es": 6.0,
            "cf": 74,
            "ctx": "중립",
            "latest_sig": "2026-04-17",
            "strategy_active_count": 2,
            "multi_buy": 3,
            "multi_sell": 1,
            "volume_ratio_20": 1.4,
            "volume_ratio_50": 1.2,
            "volume_oscillator": 3.2,
            "dollar_volume_20": 120000000,
            "volume_surge": True,
            "volume_abnormal": True,
            "volume_bullish": True,
            "thin_trade_risk": False,
            "bull_turn_recent": True,
            "uptrend_or_pullback": True,
            "pullback_ready": False,
            "bull_strength_recent": True,
            "uptrend_persistent": True,
            "strong_trend_persistent": True,
            "pullback_reentry": False,
            "low_conflict_bullish": True,
            "utbot_buy_recent": True,
            "utbot_buy_last_date": "2026-04-17",
            "utbot_sell_recent": False,
            "utbot_sell_last_date": "없음",
            "hull_turn_bull_recent": False,
            "hull_turn_bull_last_date": "없음",
            "hull_turn_bear_recent": True,
            "hull_turn_bear_last_date": "2026-04-16",
            "detected_combo_count": 2,
            "detected_combo_summary": "트렌드 눌림목(2026-04-17)",
            "detected_transition_count": 2,
            "detected_transition_summary": "UTBot 전환↑(2026-04-17) | Hull 전환↓(2026-04-16)",
            "detected_core_count": 5,
            "detected_core_summary": "시스템 매수 전환(2026-04-14)",
            "detected_signal_total_count": 7,
            "detected_buy_signal_latest_date": "2026-04-17",
            "detected_signal_latest_date": "2026-04-17",
            "gap_risk_2pct": True,
            "gap_risk_atr": False,
            "bearish_gap_failure": True,
            "first_higher_high_pivot2": False,
            "system_turn_bull_last_date": "2026-04-15",
        }

        blob = scanner_rows_to_csv_bytes([row]).decode("utf-8-sig")
        parsed = list(csv.reader(io.StringIO(blob)))
        self.assertGreaterEqual(len(parsed), 2)

        header = parsed[0]
        self.assertIn("티커(ticker)", header)
        self.assertIn("탐지전환요약(detected_transition_summary)", header)
        self.assertIn("매수탐지최근일(detected_buy_signal_latest_date)", header)
        self.assertIn("UTBot매수전환(utbot_buy_recent)", header)
        self.assertIn("우상향지속(uptrend_persistent)", header)
        self.assertIn("강한추세지속(strong_trend_persistent)", header)
        self.assertIn("약세갭실패(bearish_gap_failure)", header)
        self.assertIn("EntryJudgment(entry_judgment)", header)
        self.assertIn("EntryChaseRisk(entry_chase_risk)", header)
        self.assertIn("InvalidationLevel(invalidation_level)", header)
        self.assertIn("RR(rr)", header)

        data = parsed[1]
        h_index = {name: idx for idx, name in enumerate(header)}
        self.assertEqual(data[h_index["UTBot매수전환(utbot_buy_recent)"]], "Y")
        self.assertEqual(data[h_index["유동성주의(thin_trade_risk)"]], "N")
        self.assertEqual(data[h_index["강한추세지속(strong_trend_persistent)"]], "Y")
        self.assertEqual(data[h_index["눌림목재진입(pullback_reentry)"]], "N")
        self.assertEqual(data[h_index["약세갭실패(bearish_gap_failure)"]], "Y")

    def test_entry_v2_missing_trade_plan_prices_export_empty_strings(self):
        blob = scanner_rows_to_csv_bytes(
            [
                {
                    "ticker": "AAPL",
                    "entry_judgment": "WAIT_PULLBACK",
                    "risk_judgment": "MEDIUM",
                    "position_action": "WATCHLIST",
                }
            ]
        ).decode("utf-8-sig")
        parsed = list(csv.reader(io.StringIO(blob)))
        header = parsed[0]
        data = parsed[1]
        h_index = {name: idx for idx, name in enumerate(header)}

        for column in (
            "EntryZoneLow(entry_zone_low)",
            "EntryZoneHigh(entry_zone_high)",
            "InvalidationLevel(invalidation_level)",
            "Target1(target_1)",
            "Target2(target_2)",
            "RR(rr)",
        ):
            self.assertEqual(data[h_index[column]], "")

    def test_bool_and_date_normalization_for_extra_fields(self):
        row = {
            "ticker": "AAPL",
            "gap_risk_2pct": True,
            "gap_risk_atr": False,
            "first_higher_high_pivot2": False,
            "system_turn_bull_last_date": "",
        }
        extra_specs = (
            {"group": "risk", "key": "gap_risk_2pct", "label": "GapRisk2Pct", "type": "bool", "description": "", "rule": "", "example": "Y"},
            {"group": "risk", "key": "gap_risk_atr", "label": "GapRiskATR", "type": "bool", "description": "", "rule": "", "example": "N"},
            {"group": "turn", "key": "first_higher_high_pivot2", "label": "FirstHigherHighPivot2", "type": "bool", "description": "", "rule": "", "example": "N"},
            {"group": "turn", "key": "system_turn_bull_last_date", "label": "SystemTurnBullLastDate", "type": "date", "description": "", "rule": "", "example": "없음"},
        )
        blob = scanner_rows_to_csv_bytes([row], field_specs=extra_specs).decode("utf-8-sig")
        parsed = list(csv.reader(io.StringIO(blob)))
        header = parsed[0]
        data = parsed[1]
        h_index = {name: idx for idx, name in enumerate(header)}

        self.assertEqual(data[h_index["GapRisk2Pct(gap_risk_2pct)"]], "Y")
        self.assertEqual(data[h_index["GapRiskATR(gap_risk_atr)"]], "N")
        self.assertEqual(data[h_index["FirstHigherHighPivot2(first_higher_high_pivot2)"]], "N")
        self.assertEqual(data[h_index["SystemTurnBullLastDate(system_turn_bull_last_date)"]], "없음")

    def test_default_scanner_rows_to_csv_bytes_matches_explicit_default_field_specs(self):
        row = {
            "ticker": "AAPL",
            "utbot_buy_recent": True,
            "latest_session_utbot_buy_turn": True,
            "latest_session_hull_buy_turn": False,
        }
        implicit = scanner_rows_to_csv_bytes([row]).decode("utf-8-sig")
        explicit = scanner_rows_to_csv_bytes([row], field_specs=scanner_csv_field_specs()).decode("utf-8-sig")
        self.assertEqual(implicit, explicit)

        header = list(csv.reader(io.StringIO(implicit)))[0]
        self.assertNotIn("최근일자UTBot매수전환(latest_session_utbot_buy_turn)", header)
        self.assertNotIn("최근일자HULL매수전환(latest_session_hull_buy_turn)", header)

    def test_dictionary_csv_is_synced_with_field_specs(self):
        specs = scanner_csv_field_specs()
        expected_keys = {str(spec["key"]) for spec in specs}

        blob = scanner_csv_dictionary_to_csv_bytes().decode("utf-8-sig")
        rows = list(csv.DictReader(io.StringIO(blob)))
        dict_keys = {str(row.get("내부키", "")) for row in rows}

        self.assertEqual(dict_keys, expected_keys)

        focus_row = next(row for row in rows if row.get("내부키") == "detected_core_summary")
        self.assertIn("라벨(YYYY-MM-DD)", str(focus_row.get("계산/판정기준", "")))


if __name__ == "__main__":
    unittest.main()
