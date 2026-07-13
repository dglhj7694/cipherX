import json
import os
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app_ui.pages import home_page
from app_ui.pages.home_page import extract_section_candidates, load_latest_telegram_digest
from scripts.daily_scan_and_notify import _build_post_close_digest_bundle, _send_telegram_if_enabled
from telegram_pipeline import (
    AGGRESSIVE_NEXT_DAY_LIMIT,
    AGGRESSIVE_NEXT_DAY_SECTION_KEYS,
    BOARD_SECTION_LIMIT,
    EARLY_REVERSAL_KEY,
    HULL_BUY_TURN_KEY,
    SCAN_TAXONOMY_SECTION_ORDER,
    STEADY_WINNER_SECTION_KEY,
    STARTUP9_CONFIRM_KEY,
    TECHNICAL_BUY_CLUSTER_KEY,
    TelegramCandidate,
    annotate_rows_with_qbs,
    annotate_rows_with_technical_buy,
    build_post_close_digest,
    build_post_close_message_texts,
    select_aggressive_next_day_sections,
    select_post_close_sections,
    split_telegram_message_text,
    write_local_digest_artifacts,
)


class TelegramPipelineTests(unittest.TestCase):
    def setUp(self):
        self.market_date = date(2026, 4, 23)
        self.generated_at = datetime(2026, 4, 24, 5, 0, 0)

    def _row(self, ticker: str, **overrides):
        row = {
            "ticker": ticker,
            "price": 101.25,
            "chg_value": 1.75,
            "chg": 2.35,
            "chg_5d": 12.0,
            "rsi": 68.2,
            "volume_ratio_20": 1.45,
            "dollar_volume_20": 125_000_000,
            "final_entry_eligible": True,
            "final_entry_selected": True,
            "final_entry_score": 90.0,
            "b_score": 3,
            "c_score": 2,
            "scan_score": 140.0,
            "es": 7.0,
            "low_conflict_bullish": True,
            "strategy_conflict_level": "LOW",
            "multi_buy": 2,
            "multi_sell": 0,
            "thin_trade_risk": False,
            "entry_chase_risk": False,
            "bearish_gap_failure": False,
            "utbot_buy_recent": True,
            "hull_turn_bull_recent": False,
            "bull_turn_recent": True,
            "latest_session_utbot_buy_turn": True,
            "latest_session_hull_buy_turn": False,
            "utbot_buy_last_date": self.market_date.isoformat(),
            "hull_turn_bull_last_date": "N/A",
            "days_since_utbot_buy": 0,
            "days_since_hull_turn_bull": 99,
            "cmf": 0.18,
            "obv_slope": 1.2,
            "uptrend_persistent": True,
            "hma20_slope_pct": 1.8,
            "hma60_slope_pct": 2.2,
            "pullback_from_swing_high_pct": -4.5,
            "drawdown_from_52w_high_pct": -6.0,
            "drawdown_from_20d_high_pct": -4.0,
            "pullback_atr_multiple": 1.8,
            "pullback_ready": True,
            "pullback_reentry": True,
            "volume_dry_up_score": 12.0,
            "bull_strength_recent": True,
            "volume_bullish": True,
            "adx": 24.0,
            "rs_rank_vs_index": 83.0,
            "ret20_pct": 8.5,
            "ret60_pct": 18.0,
            "ret120_pct": 32.0,
            "ret252_pct": 64.0,
            "dist_sma20_pct": 9.0,
            "zscore20": 1.9,
            "utbot_sell_recent": False,
            "hull_turn_bear_recent": False,
            "utbot_sell_last_date": "N/A",
            "hull_turn_bear_last_date": "N/A",
            "gap_setup_candidate": True,
            "gap_setup_score": 9,
            "gap_setup_gate_count": 4,
            "gap_setup_hits": ["band squeeze", "relative strength"],
            "gap_setup_quality_hits": ["volume dry-up"],
            "pocket_pivot_candidate": True,
            "pocket_pivot_score": 10,
            "pocket_pivot_gate_count": 4,
            "pocket_pivot_hits": ["PocketPivot", "volume recovery"],
            "pocket_pivot_quality_hits": ["institutional flow"],
            "new_52w_high": True,
            "new_52w_closing_high": True,
            "latest_bar_date": self.market_date.isoformat(),
            "ema50": 98.0,
            "hma_ema_long_entry": True,
            "hma_ema_long_aligned": True,
            "hma25_ema25_cross_bull": True,
            "hma_ema_risk_to_ema50_pct": 2.0,
        }
        row.update(overrides)
        return row

    def _early_reversal_row(self, ticker: str, **overrides):
        row = self._row(
            ticker,
            final_entry_eligible=False,
            final_entry_selected=False,
            final_entry_score=0.0,
            scan_score=120.0,
            chg=2.1,
            chg_value=2.0,
            chg_5d=4.8,
            ret20_pct=-4.0,
            ret60_pct=-12.0,
            dist_sma50_pct=-3.0,
            drawdown_from_52w_high_pct=-22.0,
            drawdown_from_20d_high_pct=-3.0,
            atr_contracting=True,
            nr7_flag=True,
            inside_day_flag=True,
            three_weeks_tight=False,
            volume_dry_up_score=14.0,
            bb_percent_b=0.68,
            first_higher_low_pivot2=True,
            first_higher_high_pivot2=False,
            tight_close_near_high_3d=True,
            latest_session_utbot_buy_turn=False,
            latest_session_hull_buy_turn=True,
            days_since_utbot_buy=99,
            days_since_hull_turn_bull=0,
            first_close_above_ma20_after_5bars=True,
            volume_ratio_20=1.42,
            volume_expansion_score=30.0,
            obv_slope=0.4,
            cmf=0.12,
            volume_bullish=True,
            dist_sma20_pct=3.2,
            ma20_dist_pct=3.2,
            zscore20=1.1,
            breakout_dist_20d_high_pct=-1.8,
            thin_trade_risk=False,
            bearish_gap_failure=False,
            multi_sell=0,
            strategy_conflict_level="LOW",
            low_conflict_bullish=True,
            utbot_sell_last_date="N/A",
            hull_turn_bear_last_date="N/A",
            hma_ema_short_entry=False,
            hma_ema_short_aligned=False,
            new_52w_high=False,
            new_52w_closing_high=False,
        )
        row.update(overrides)
        return row

    def _hull_buy_turn_row(self, ticker: str, **overrides):
        row = self._row(
            ticker,
            latest_session_hull_buy_turn=True,
            hull_turn_bull_last_date=self.market_date.isoformat(),
            days_since_hull_turn_bull=0,
            latest_session_utbot_buy_turn=False,
            utbot_buy_last_date="N/A",
            days_since_utbot_buy=99,
            first_close_above_ma20_after_5bars=True,
            volume_ratio_20=1.3,
            cmf=0.12,
            obv_slope=0.8,
            rs_rank_vs_index=76.0,
            dist_sma20_pct=3.1,
            ma20_dist_pct=3.1,
            chg=2.1,
            chg_5d=4.8,
            zscore20=1.1,
        )
        row.update(overrides)
        return row

    def _technical_signal(self, key: str, *, label: str | None = None, direction: str = "buy", days_ago: int = 0):
        return {
            "group": "core",
            "key": key,
            "label": label or key,
            "dir": direction,
            "date": self.market_date.isoformat(),
            "days_ago": days_ago,
        }

    def _technical_base_row(self, ticker: str, *, signals: list[dict] | None = None, **overrides):
        row = self._row(
            ticker,
            final_entry_eligible=False,
            final_entry_selected=False,
            final_entry_score=0.0,
            scan_score=0.0,
            es=0.0,
            chg=1.2,
            chg_value=1.0,
            chg_5d=3.0,
            rsi=55.0,
            volume_ratio_20=1.0,
            dollar_volume_20=150_000_000,
            latest_session_utbot_buy_turn=False,
            latest_session_hull_buy_turn=False,
            utbot_buy_recent=False,
            hull_turn_bull_recent=False,
            bull_turn_recent=False,
            utbot_buy_last_date="N/A",
            hull_turn_bull_last_date="N/A",
            days_since_utbot_buy=99,
            days_since_hull_turn_bull=99,
            cmf=0.0,
            obv_slope=0.0,
            uptrend_persistent=False,
            hma20_slope_pct=0.0,
            hma60_slope_pct=0.0,
            pullback_ready=False,
            pullback_reentry=False,
            bull_strength_recent=False,
            volume_bullish=False,
            gap_setup_candidate=False,
            pocket_pivot_candidate=False,
            pocket_pivot_recent=False,
            new_52w_high=False,
            new_52w_closing_high=False,
            hma_ema_long_entry=False,
            hma_ema_long_aligned=False,
            hma25_ema25_cross_bull=False,
            hma_ema_short_entry=False,
            hma25_ema25_cross_bear=False,
            volume_surge=False,
            volume_climax_flag=False,
            nr7_flag=False,
            atr_contracting=False,
            inside_day_flag=False,
            thin_trade_risk=False,
            bearish_gap_failure=False,
            multi_sell=0,
            strategy_conflict_level="LOW",
            detected_signals=list(signals or []),
        )
        row.update(overrides)
        return row

    def test_build_post_close_digest_uses_trader_board_sections_and_tags_overlap(self):
        digest = build_post_close_digest(
            [self._row("ALPHA")],
            run_stamp="20260424_050000",
            generated_at=self.generated_at,
            market_date=self.market_date,
            scan_label="post-close default",
            universe_count=1,
            result_count=1,
            skip_count=0,
        )
        section_map = digest.section_map()

        self.assertEqual(
            digest.section_order,
            [
                "qbs_buy_now",
                "qbs_chase_watch",
                "qbs_pullback_wait",
                *SCAN_TAXONOMY_SECTION_ORDER,
                STEADY_WINNER_SECTION_KEY,
                EARLY_REVERSAL_KEY,
                HULL_BUY_TURN_KEY,
                STARTUP9_CONFIRM_KEY,
                TECHNICAL_BUY_CLUSTER_KEY,
                *AGGRESSIVE_NEXT_DAY_SECTION_KEYS,
                "confluence",
                "entry_now",
                "pullback_reentry",
                "steady_uptrend",
                "breakout_wait",
                "accumulation",
                "rs_leader",
                "chase_risk",
                "sell_risk",
                "five_day_top",
            ],
        )
        self.assertEqual([item.ticker for item in section_map["qbs_buy_now"].items], ["ALPHA"])
        self.assertEqual([item.ticker for item in section_map["confluence"].items], ["ALPHA"])
        confluence = section_map["confluence"].items[0]
        self.assertGreaterEqual(confluence.source_flags["membership_count"], 3)
        self.assertIn("HMA", confluence.tags)
        self.assertIn("pocket", confluence.tags)
        general_tickers = [
            item.ticker
            for key in digest.section_order
            if not key.startswith("qbs_")
            and key
            not in {
                "five_day_top",
                STARTUP9_CONFIRM_KEY,
                TECHNICAL_BUY_CLUSTER_KEY,
                STEADY_WINNER_SECTION_KEY,
                EARLY_REVERSAL_KEY,
                HULL_BUY_TURN_KEY,
                *AGGRESSIVE_NEXT_DAY_SECTION_KEYS,
                *SCAN_TAXONOMY_SECTION_ORDER,
            }
            for item in section_map[key].items
        ]
        self.assertEqual(len(general_tickers), len(set(general_tickers)))

    def test_scan_taxonomy_sections_limit_top20_and_allow_duplicates(self):
        rows = [
            self._row(
                f"TX{i:02d}",
                final_entry_score=120.0 - i,
                pocket_pivot_candidate=True,
                cmf=0.2,
                obv_slope=0.5,
                volume_ratio_20=1.8,
                pullback_ready=True,
                detected_signals=[{"key": "Hammer", "dir": "buy"}, {"key": "MA20_Support", "dir": "buy"}],
            )
            for i in range(25)
        ]
        digest = build_post_close_digest(
            rows,
            run_stamp="20260424_050000",
            generated_at=self.generated_at,
            market_date=self.market_date,
            scan_label="post-close default",
            universe_count=25,
            result_count=25,
            skip_count=0,
        )
        section_map = digest.section_map()
        buy_now = section_map["scan_taxonomy_buy_now"].items
        accumulation = section_map["scan_taxonomy_accumulation"].items

        self.assertEqual(len(buy_now), 20)
        self.assertEqual(len(accumulation), 20)
        self.assertEqual(buy_now[0].ticker, "TX00")
        self.assertIn("TX00", {item.ticker for item in accumulation})

    def _aggressive_trend_row(self, ticker: str, **overrides):
        row = self._row(
            ticker,
            final_entry_eligible=False,
            final_entry_selected=False,
            final_entry_score=0.0,
            scan_score=0.0,
            es=0.0,
            strength=0.0,
            chg=15.0,
            chg_5d=32.0,
            atr_pct=6.0,
            volume_ratio_20=1.5,
            volume_expansion_score=50.0,
            dollar_volume_20=2_000_000_000.0,
            bull_strength_recent=True,
            strong_trend_persistent=True,
            uptrend_persistent=True,
            hma_ema_long_aligned=True,
            hma20_slope_pct=5.0,
            hma60_slope_pct=3.5,
            adx=40.0,
            rs_rank_vs_index=97.0,
            ret20_pct=75.0,
            ret20_percentile=98.0,
            ret60_percentile=96.0,
            cmf=0.32,
            obv_slope=0.8,
            gap_risk_2pct=True,
            gap_risk_atr=False,
            dist_vwap_pct=35.0,
            breakout_dist_20d_high_pct=-0.1,
            drawdown_from_52w_high_pct=-0.1,
            near_52w_high_2pct=True,
            dist_bb_upper_pct=4.0,
            dist_sma20_pct=42.0,
            zscore20=2.4,
            bb_percent_b=1.08,
            utbot_sell_recent=False,
            hull_turn_bear_recent=False,
            utbot_sell_last_date="N/A",
            hull_turn_bear_last_date="N/A",
            hma_ema_short_entry=False,
            hma25_ema25_cross_bear=False,
            bearish_gap_failure=False,
            thin_trade_risk=False,
        )
        row.update(overrides)
        return row

    def test_aggressive_selector_ignores_program_scores_and_keeps_metric_candidate(self):
        high_score_bad_metrics = self._aggressive_trend_row(
            "BAD",
            final_entry_score=999.0,
            scan_score=999.0,
            es=99.0,
            atr_pct=1.5,
        )
        low_score_good_metrics = self._aggressive_trend_row("GOOD")

        sections = select_aggressive_next_day_sections(
            [high_score_bad_metrics, low_score_good_metrics],
            target_date=self.market_date,
        )
        part2_tickers = [row["ticker"] for row in sections[AGGRESSIVE_NEXT_DAY_SECTION_KEYS[1]]]

        self.assertNotIn("BAD", part2_tickers)
        self.assertIn("GOOD", part2_tickers)

    def test_aggressive_strong_trend_includes_sndk_mu_style_and_allows_cross_part_duplicates(self):
        sndk = self._aggressive_trend_row("SNDK", rs_rank_vs_index=98.9, chg=16.6, chg_5d=31.6)
        mu = self._aggressive_trend_row("MU", rs_rank_vs_index=97.3, chg=15.5, chg_5d=37.7)

        sections = select_aggressive_next_day_sections([sndk, mu], target_date=self.market_date)
        part2_tickers = [row["ticker"] for row in sections[AGGRESSIVE_NEXT_DAY_SECTION_KEYS[1]]]
        part7_tickers = [row["ticker"] for row in sections[AGGRESSIVE_NEXT_DAY_SECTION_KEYS[6]]]

        self.assertIn("SNDK", part2_tickers)
        self.assertIn("MU", part2_tickers)
        self.assertIn("SNDK", part7_tickers)
        self.assertIn("MU", part7_tickers)

    def test_aggressive_sections_apply_top20_limit(self):
        rows = [
            self._aggressive_trend_row(
                f"HV{i:02d}",
                chg=5.0 + (i * 0.1),
                chg_5d=18.0 + i,
                atr_pct=12.0 - (i * 0.1),
                rs_rank_vs_index=90.0 - (i * 0.1),
            )
            for i in range(25)
        ]

        sections = select_aggressive_next_day_sections(rows, target_date=self.market_date)

        self.assertEqual(len(sections[AGGRESSIVE_NEXT_DAY_SECTION_KEYS[3]]), AGGRESSIVE_NEXT_DAY_LIMIT)

    def test_qbs_scores_confluence_above_single_buy_turn(self):
        confluence = self._row("ALPHA")
        single_buy = self._row(
            "BETA",
            final_entry_eligible=False,
            final_entry_selected=False,
            chg_5d=0.0,
            uptrend_persistent=False,
            pullback_ready=False,
            pullback_reentry=False,
            bull_strength_recent=False,
            gap_setup_candidate=False,
            pocket_pivot_candidate=False,
            new_52w_high=False,
            latest_bar_date=self.market_date.isoformat(),
            hma_ema_long_entry=False,
            hma_ema_long_aligned=False,
            hma25_ema25_cross_bull=False,
        )

        annotated = annotate_rows_with_qbs([confluence, single_buy], target_date=self.market_date)
        by_ticker = {row["ticker"]: row for row in annotated}

        self.assertGreater(float(by_ticker["ALPHA"]["qbs_score"]), float(by_ticker["BETA"]["qbs_score"]))
        self.assertEqual(by_ticker["ALPHA"]["qbs_bucket"], "BUY_NOW")

    def test_qbs_hard_risk_and_chase_buckets(self):
        sell_conflict = self._row(
            "SELLX",
            utbot_sell_last_date=self.market_date.isoformat(),
        )
        chase = self._row("CHASE", chg=13.0)
        extreme = self._row("EXTREME", chg=21.0)

        annotated = annotate_rows_with_qbs([sell_conflict, chase, extreme], target_date=self.market_date)
        by_ticker = {row["ticker"]: row for row in annotated}

        self.assertEqual(by_ticker["SELLX"]["qbs_bucket"], "EXCLUDE")
        self.assertIn("sell_turn", by_ticker["SELLX"]["qbs_risk_flags"])
        self.assertEqual(by_ticker["CHASE"]["qbs_bucket"], "CHASE_WATCH")
        self.assertIn("chase_risk", by_ticker["CHASE"]["qbs_risk_flags"])
        self.assertEqual(by_ticker["EXTREME"]["qbs_bucket"], "CHASE_WATCH")
        self.assertIn("extreme_chase", by_ticker["EXTREME"]["qbs_risk_flags"])

    def test_technical_buy_cluster_selects_multisignal_sorts_and_formats(self):
        trend = self._technical_base_row(
            "TREND",
            signals=[
                self._technical_signal("TK_Cross_Bull", label="TK골든"),
                self._technical_signal("DMI_Cross_Bull", label="DMI강세교차"),
                self._technical_signal("ADX_New_Uptrend", label="신규상승추세"),
                self._technical_signal("MACD_Zero_Cross_Buy", label="MACD0"),
                self._technical_signal("CMF_Bull", label="CMF강세"),
            ],
            volume_ratio_20=1.82,
            cmf=0.18,
            obv_slope=0.5,
            atr_pct=4.6,
            chg=3.21,
        )
        reversal = self._technical_base_row(
            "REV",
            signals=[
                self._technical_signal("Green_Dot_T2"),
                self._technical_signal("StochRSI_Cross_Buy"),
                self._technical_signal("Bull_Divergence"),
            ],
            volume_ratio_20=1.25,
            atr_pct=6.2,
            chg=1.4,
        )
        weak = self._technical_base_row(
            "WEAK",
            signals=[self._technical_signal("Stoch_Oversold")],
            volume_ratio_20=1.5,
        )
        sell_turn = self._technical_base_row(
            "SELLX",
            signals=[
                self._technical_signal("TK_Cross_Bull"),
                self._technical_signal("DMI_Cross_Bull"),
                self._technical_signal("UTBot_Sell", direction="sell"),
            ],
            utbot_sell_last_date=self.market_date.isoformat(),
        )
        low_liquidity = self._technical_base_row(
            "THIN",
            signals=[
                self._technical_signal("Pocket_Pivot"),
                self._technical_signal("CMF_Bull"),
            ],
            dollar_volume_20=10_000_000,
        )

        digest = build_post_close_digest(
            [reversal, trend, weak, sell_turn, low_liquidity],
            run_stamp="20260424_050000",
            generated_at=self.generated_at,
            market_date=self.market_date,
            scan_label="post-close default",
            universe_count=5,
            result_count=5,
            skip_count=0,
        )
        section = digest.section_map()[TECHNICAL_BUY_CLUSTER_KEY]
        tickers = [item.ticker for item in section.items]

        self.assertIn("TREND", tickers)
        self.assertIn("REV", tickers)
        self.assertNotIn("WEAK", tickers)
        self.assertNotIn("SELLX", tickers)
        self.assertNotIn("THIN", tickers)
        self.assertEqual(tickers[0], "TREND")
        self.assertGreaterEqual(section.items[0].technical_buy_score, section.items[1].technical_buy_score)
        self.assertEqual(section.items[0].technical_buy_bucket, "추세전환형")
        self.assertEqual(section.items[1].technical_buy_bucket, "반전초입형")
        self.assertGreaterEqual(section.items[0].technical_buy_signal_count, 5)
        self.assertIn("TK골든", section.items[0].technical_buy_hits)

        message = build_post_close_message_texts(digest)[0]
        self.assertIn("기술적 매수시그널 클러스터 Top 20", message)
        self.assertIn("점수", message)
        self.assertIn("분류: 추세전환형", message)
        self.assertIn("리스크: 특이사항 없음", message)
        self.assertIn("이유:", message)

    def test_technical_buy_annotation_writes_digest_payload_fields(self):
        row = self._technical_base_row(
            "FLOW",
            signals=[
                self._technical_signal("CMF_Bull"),
                self._technical_signal("MF_Cross_Bull"),
                self._technical_signal("Pocket_Pivot"),
            ],
            volume_ratio_20=1.55,
            cmf=0.2,
        )
        weak = self._technical_base_row("WEAK", signals=[self._technical_signal("Stoch_Oversold")])

        annotated = annotate_rows_with_technical_buy([row, weak], target_date=self.market_date)
        by_ticker = {item["ticker"]: item for item in annotated}

        self.assertNotEqual(by_ticker["FLOW"]["technical_buy_score"], "")
        self.assertEqual(by_ticker["FLOW"]["technical_buy_bucket"], "수급매집형")
        self.assertIn("+", by_ticker["FLOW"]["technical_buy_hits"])
        self.assertEqual(by_ticker["FLOW"]["technical_buy_risk_flags"], "특이사항 없음")
        self.assertEqual(by_ticker["WEAK"]["technical_buy_score"], "")

    def test_qbs_high_conflict_extreme_strength_stays_chase_watch(self):
        row = self._row(
            "POET",
            chg=28.84,
            chg_5d=107.99,
            strategy_conflict_level="HIGH",
            low_conflict_bullish=False,
            final_entry_eligible=False,
            final_entry_selected=False,
            gap_setup_candidate=False,
            new_52w_high=False,
            hma_ema_long_entry=False,
            hma_ema_long_aligned=False,
        )

        annotated = annotate_rows_with_qbs([row], target_date=self.market_date)

        self.assertEqual(annotated[0]["qbs_bucket"], "CHASE_WATCH")
        self.assertIn("high_conflict", annotated[0]["qbs_risk_flags"])
        self.assertIn("extreme_chase", annotated[0]["qbs_risk_flags"])

    def test_qbs_hma_negative_not_buy_now_and_pullback_wait(self):
        hma_negative = self._row(
            "HMANEG",
            final_entry_eligible=False,
            final_entry_selected=False,
            latest_session_utbot_buy_turn=False,
            latest_session_hull_buy_turn=False,
            utbot_buy_last_date="N/A",
            hull_turn_bull_last_date="N/A",
            chg=-0.5,
            chg_5d=0.0,
            uptrend_persistent=False,
            pullback_ready=False,
            pullback_reentry=False,
            bull_strength_recent=False,
            gap_setup_candidate=False,
            pocket_pivot_candidate=False,
            new_52w_high=False,
            hma_ema_long_entry=True,
            hma_ema_long_aligned=True,
            hma25_ema25_cross_bull=True,
        )
        pullback = self._row(
            "PULL",
            final_entry_eligible=False,
            final_entry_selected=False,
            latest_session_utbot_buy_turn=False,
            latest_session_hull_buy_turn=False,
            utbot_buy_last_date="N/A",
            hull_turn_bull_last_date="N/A",
            chg=0.4,
            chg_5d=0.0,
            gap_setup_candidate=False,
            pocket_pivot_candidate=False,
            new_52w_high=False,
            hma_ema_long_entry=False,
            hma_ema_long_aligned=False,
            hma25_ema25_cross_bull=False,
        )

        annotated = annotate_rows_with_qbs([hma_negative, pullback], target_date=self.market_date)
        by_ticker = {row["ticker"]: row for row in annotated}

        self.assertNotEqual(by_ticker["HMANEG"]["qbs_bucket"], "BUY_NOW")
        self.assertEqual(by_ticker["PULL"]["qbs_bucket"], "PULLBACK_WAIT")

    def test_qbs_candidate_mutable_fields_are_isolated(self):
        first = TelegramCandidate("AAA", None, None, None, None, "qbs_buy_now", 1, "", "")
        second = TelegramCandidate("BBB", None, None, None, None, "qbs_buy_now", 2, "", "")

        first.tags.append("final")
        first.risk_flags.append("chase_risk")

        self.assertEqual(second.tags, [])
        self.assertEqual(second.risk_flags, [])

    def test_turn_sections_use_same_day_only(self):
        same_day_buy = self._row("BUYDAY")
        recent_buy_only = self._row(
            "BUYRECENT",
            latest_session_utbot_buy_turn=False,
            latest_session_hull_buy_turn=False,
            utbot_buy_last_date="2026-04-22",
            days_since_utbot_buy=1,
            hma_ema_long_entry=False,
            hma_ema_long_aligned=False,
        )
        same_day_sell = self._row(
            "SELLDAY",
            final_entry_eligible=False,
            final_entry_selected=False,
            latest_session_utbot_buy_turn=False,
            utbot_buy_last_date="N/A",
            utbot_sell_last_date=self.market_date.isoformat(),
            hull_turn_bear_last_date="N/A",
            hma_ema_long_entry=False,
            hma_ema_long_aligned=False,
        )
        risk_only = self._row(
            "RISKONLY",
            final_entry_eligible=False,
            final_entry_selected=False,
            latest_session_utbot_buy_turn=False,
            utbot_buy_last_date="N/A",
            thin_trade_risk=True,
            bearish_gap_failure=True,
            utbot_sell_last_date="N/A",
            hull_turn_bear_last_date="N/A",
            hma_ema_long_entry=False,
            hma_ema_long_aligned=False,
        )

        digest = build_post_close_digest(
            [same_day_buy, recent_buy_only, same_day_sell, risk_only],
            run_stamp="20260424_050000",
            generated_at=self.generated_at,
            market_date=self.market_date,
            scan_label="post-close default",
            universe_count=4,
            result_count=4,
            skip_count=0,
        )
        section_map = digest.section_map()

        board_tickers = {
            item.ticker
            for key in ["confluence", "entry_now", "pullback_reentry", "steady_uptrend", "breakout_wait", "accumulation", "rs_leader", "chase_risk"]
            for item in section_map[key].items
        }
        self.assertIn("BUYDAY", board_tickers)
        self.assertEqual(section_map["sell_risk"].items[0].ticker, "SELLDAY")
        self.assertIn("sell_turn", section_map["sell_risk"].items[0].risk_flags)

    def test_board_sections_and_qbs_buckets_apply_new_limits(self):
        rows = [
            self._row(
                f"T{i:02d}",
                final_entry_score=500 - i,
                chg_5d=5.0 - (i * 0.01),
                scan_score=300 - i,
                hma_ema_risk_to_ema50_pct=1.0 + i * 0.05,
            )
            for i in range(35)
        ]
        digest = build_post_close_digest(
            rows,
            run_stamp="20260424_050000",
            generated_at=self.generated_at,
            market_date=self.market_date,
            scan_label="post-close default",
            universe_count=35,
            result_count=35,
            skip_count=0,
        )
        section_map = digest.section_map()

        self.assertEqual(section_map["qbs_buy_now"].item_count, 20)
        self.assertEqual(section_map[STEADY_WINNER_SECTION_KEY].item_count, 20)
        self.assertEqual(section_map["confluence"].item_count, BOARD_SECTION_LIMIT)
        self.assertEqual(section_map["five_day_top"].item_count, 30)
        self.assertTrue(all(section.item_count <= BOARD_SECTION_LIMIT for key, section in section_map.items() if not key.startswith("qbs_") and key != "five_day_top"))

    def test_five_day_top_section_keeps_top30_sorted_and_positive_only(self):
        rows = [
            self._row(
                f"F{i:02d}",
                chg_5d=40.0 - i,
                scan_score=100.0 + i,
                es=float(i),
                rsi=55.0 + (i % 10),
                dist_sma20_pct=3.0 + i,
            )
            for i in range(32)
        ]
        rows.extend(
            [
                self._row("ZERO", chg_5d=0.0),
                self._row("NEG", chg_5d=-1.0),
            ]
        )
        digest = build_post_close_digest(
            rows,
            run_stamp="20260424_050000",
            generated_at=self.generated_at,
            market_date=self.market_date,
            scan_label="post-close default",
            universe_count=len(rows),
            result_count=len(rows),
            skip_count=0,
        )
        items = digest.section_map()["five_day_top"].items

        self.assertEqual(len(items), 30)
        self.assertEqual([item.ticker for item in items[:3]], ["F00", "F01", "F02"])
        self.assertNotIn("ZERO", [item.ticker for item in items])
        self.assertNotIn("NEG", [item.ticker for item in items])
        self.assertEqual(items[0].chg_5d, 40.0)
        self.assertEqual(items[0].chg_pct, 40.0)
        self.assertEqual(items[0].reason, items[0].status)
        self.assertIn("추격주의", items[0].reason)

    def test_steady_winner_section_scores_structure_without_hard_momentum_gates(self):
        calm = self._row(
            "CALM",
            chg=1.2,
            chg_5d=4.1,
            rs_rank_vs_index=75.0,
            ret20_pct=6.0,
            ret60_pct=14.0,
            ret20_percentile=76.0,
            ret60_percentile=78.0,
            ema200=90.0,
            dist_ema21_pct=2.0,
            drawdown_from_52w_high_pct=-7.0,
            near_52w_high_2pct=False,
            breakout_dist_20d_high_pct=-4.0,
        )
        fast = self._row(
            "FAST",
            chg=8.2,
            chg_5d=16.0,
            rs_rank_vs_index=92.0,
            ret20_pct=18.0,
            ret60_pct=33.0,
            ret20_percentile=92.0,
            ret60_percentile=94.0,
            ret120_percentile=90.0,
            ema200=90.0,
            dist_ema21_pct=5.0,
            near_52w_high_2pct=True,
        )
        low_volume = self._row(
            "LOWVOL",
            chg=1.1,
            chg_5d=5.0,
            volume_ratio_20=0.7,
            rs_rank_vs_index=82.0,
            ret20_pct=7.0,
            ret60_pct=15.0,
            ret20_percentile=86.0,
            ret60_percentile=87.0,
            ema200=90.0,
            dist_ema21_pct=2.0,
            drawdown_from_52w_high_pct=-6.0,
        )
        high_conflict = self._row(
            "HICON",
            chg=1.0,
            chg_5d=6.0,
            strategy_conflict_level="HIGH",
            low_conflict_bullish=False,
            rs_rank_vs_index=91.0,
            ret20_pct=9.0,
            ret60_pct=18.0,
            ret20_percentile=90.0,
            ret60_percentile=92.0,
            ema200=90.0,
            dist_ema21_pct=2.0,
            drawdown_from_52w_high_pct=-5.0,
        )
        sell_turn = self._row(
            "SELLX",
            chg=1.0,
            chg_5d=5.0,
            ret20_pct=8.0,
            ret60_pct=16.0,
            ema200=90.0,
            dist_ema21_pct=2.0,
            utbot_sell_last_date=self.market_date.isoformat(),
        )
        below_ema50 = self._row(
            "BELOW",
            price=90.0,
            ema50=100.0,
            chg=1.0,
            chg_5d=5.0,
            ret20_pct=8.0,
            ret60_pct=16.0,
            ema200=80.0,
            dist_ema21_pct=2.0,
        )

        digest = build_post_close_digest(
            [calm, fast, low_volume, high_conflict, sell_turn, below_ema50],
            run_stamp="20260424_050000",
            generated_at=self.generated_at,
            market_date=self.market_date,
            scan_label="post-close default",
            universe_count=6,
            result_count=6,
            skip_count=0,
        )
        items = {item.ticker: item for item in digest.section_map()[STEADY_WINNER_SECTION_KEY].items}

        self.assertIn("CALM", items)
        self.assertEqual(items["CALM"].bucket, "STEADY_WINNER")
        self.assertIn("RS70", items["CALM"].tags)
        self.assertIn("FAST", items)
        self.assertIn("acceleration_day", items["FAST"].risk_flags)
        self.assertIn("five_day_acceleration", items["FAST"].risk_flags)
        self.assertEqual(items["FAST"].entry_type, "extended_wait")
        self.assertIn("LOWVOL", items)
        self.assertIn("low_volume", items["LOWVOL"].risk_flags)
        self.assertIn("HICON", items)
        self.assertIn("high_conflict", items["HICON"].risk_flags)
        self.assertNotIn("SELLX", items)
        self.assertNotIn("BELOW", items)

        message = build_post_close_message_texts(digest)[0]
        self.assertIn("## 0-3. 계속 우상향 주도주 Top 30", message)
        self.assertIn("FAST | PUL", message)
        self.assertIn("근거:", message)
        self.assertIn("진입유형: extended_wait", message)
        self.assertIn("주의: acceleration_day+five_day_acceleration", message)

    def test_steady_winner_includes_runaway_leader_like_sndk(self):
        sndk = self._row(
            "SNDK",
            chg=11.98,
            chg_5d=40.30,
            dist_sma20_pct=41.2,
            rsi=81.1,
            rs_rank_vs_index=99.0,
            ret20_pct=35.0,
            ret60_pct=74.0,
            ret20_percentile=99.0,
            ret60_percentile=98.0,
            ret120_percentile=95.0,
            ema50=80.0,
            ema200=60.0,
            dist_ema21_pct=24.0,
            near_52w_high_2pct=True,
            breakout_dist_20d_high_pct=-1.0,
            drawdown_from_52w_high_pct=-2.0,
            cmf=0.12,
            obv_slope=1.4,
            volume_ratio_20=1.23,
            zscore20=2.8,
        )
        digest = build_post_close_digest(
            [sndk],
            run_stamp="20260424_050000",
            generated_at=self.generated_at,
            market_date=self.market_date,
            scan_label="post-close default",
            universe_count=1,
            result_count=1,
            skip_count=0,
        )
        item = digest.section_map()[STEADY_WINNER_SECTION_KEY].items[0]

        self.assertEqual(item.ticker, "SNDK")
        self.assertEqual(item.bucket, "RUNAWAY_LEADER")
        self.assertEqual(item.entry_type, "extended_wait")
        self.assertIn("runaway_leader", item.tags)
        self.assertIn("acceleration_day", item.risk_flags)
        self.assertIn("five_day_acceleration", item.risk_flags)
        self.assertIn("ma20_extension", item.risk_flags)
        self.assertIn("rsi_hot", item.risk_flags)
        self.assertNotIn("volume_climax", item.risk_flags)

        message = build_post_close_message_texts(digest)[0]
        self.assertIn("SNDK | PUL", message)
        self.assertIn("RUNAWAY_LEADER", message)
        self.assertIn("진입유형: extended_wait", message)

    def test_steady_winner_uses_stable_and_runaway_quotas_for_top30(self):
        stable_rows = [
            self._row(
                f"ST{i:02d}",
                chg=1.0 + (i * 0.01),
                chg_5d=5.0 + (i * 0.01),
                rs_rank_vs_index=88.0 + (i * 0.01),
                ret20_pct=7.0,
                ret60_pct=14.0,
                ret20_percentile=90.0,
                ret60_percentile=90.0,
                ema50=90.0,
                ema200=70.0,
                dist_ema21_pct=2.0,
                drawdown_from_52w_high_pct=-6.0,
                near_52w_high_2pct=False,
                breakout_dist_20d_high_pct=-5.0,
            )
            for i in range(25)
        ]
        runaway_rows = [
            self._row(
                f"RW{i:02d}",
                chg=9.0 + (i * 0.01),
                chg_5d=25.0 + (i * 0.1),
                dist_sma20_pct=25.0,
                rsi=82.0,
                rs_rank_vs_index=99.0 - (i * 0.01),
                ret20_pct=25.0,
                ret60_pct=50.0,
                ret20_percentile=96.0,
                ret60_percentile=97.0,
                ema50=85.0,
                ema200=65.0,
                dist_ema21_pct=10.0,
                near_52w_high_2pct=True,
                breakout_dist_20d_high_pct=-1.0,
                drawdown_from_52w_high_pct=-2.0,
                cmf=0.10,
                obv_slope=1.1,
                volume_ratio_20=1.2,
            )
            for i in range(12)
        ]
        duplicate_stable = self._row(
            "DUP",
            chg=1.0,
            chg_5d=5.0,
            rs_rank_vs_index=88.0,
            ret20_pct=7.0,
            ret60_pct=14.0,
            ret20_percentile=90.0,
            ret60_percentile=90.0,
            ema50=90.0,
            ema200=70.0,
            dist_ema21_pct=2.0,
        )
        duplicate_runaway = self._row(
            "DUP",
            chg=12.0,
            chg_5d=35.0,
            dist_sma20_pct=28.0,
            rsi=83.0,
            rs_rank_vs_index=100.0,
            ret20_pct=30.0,
            ret60_pct=60.0,
            ret20_percentile=99.0,
            ret60_percentile=99.0,
            ema50=85.0,
            ema200=65.0,
            dist_ema21_pct=12.0,
            near_52w_high_2pct=True,
            breakout_dist_20d_high_pct=-0.5,
            drawdown_from_52w_high_pct=-1.0,
            cmf=0.15,
            obv_slope=1.5,
            volume_ratio_20=1.4,
        )

        digest = build_post_close_digest(
            [*stable_rows, *runaway_rows, duplicate_stable, duplicate_runaway],
            run_stamp="20260424_050000",
            generated_at=self.generated_at,
            market_date=self.market_date,
            scan_label="post-close default",
            universe_count=39,
            result_count=39,
            skip_count=0,
        )
        items = digest.section_map()[STEADY_WINNER_SECTION_KEY].items
        tickers = [item.ticker for item in items]
        runaway_items = [item for item in items if item.bucket == "RUNAWAY_LEADER"]
        stable_items = [item for item in items if item.bucket != "RUNAWAY_LEADER"]

        self.assertEqual(len(items), 30)
        self.assertEqual(len(stable_items), 20)
        self.assertEqual(len(runaway_items), 10)
        self.assertEqual(len(tickers), len(set(tickers)))
        self.assertEqual(tickers.count("DUP"), 1)
        self.assertIn("DUP", [item.ticker for item in runaway_items])

    def test_early_reversal_section_sits_after_steady_and_includes_downtrend_reversal(self):
        row = self._early_reversal_row("MELI")
        digest = build_post_close_digest(
            [row],
            run_stamp="20260424_050000",
            generated_at=self.generated_at,
            market_date=self.market_date,
            scan_label="post-close default",
            universe_count=1,
            result_count=1,
            skip_count=0,
        )
        section_map = digest.section_map()
        item = section_map[EARLY_REVERSAL_KEY].items[0]

        expected_prefix = [
            "qbs_buy_now",
            "qbs_chase_watch",
            "qbs_pullback_wait",
            *SCAN_TAXONOMY_SECTION_ORDER,
            STEADY_WINNER_SECTION_KEY,
            EARLY_REVERSAL_KEY,
            HULL_BUY_TURN_KEY,
            STARTUP9_CONFIRM_KEY,
            TECHNICAL_BUY_CLUSTER_KEY,
        ]
        self.assertEqual(digest.section_order[: len(expected_prefix)], expected_prefix)
        self.assertEqual(item.ticker, "MELI")
        self.assertEqual(item.reversal_phase, "CONFIRMED")
        self.assertEqual(item.reversal_type, "MIXED_REVERSAL")
        self.assertIsNotNone(item.early_reversal_score)
        self.assertGreaterEqual(item.early_reversal_score or 0.0, 80.0)
        self.assertEqual(item.entry_type, "confirmed_reversal_watch")

    def test_early_reversal_includes_box_breakout_context(self):
        row = self._early_reversal_row(
            "BOX",
            ret20_pct=3.0,
            ret60_pct=6.0,
            dist_sma50_pct=2.0,
            drawdown_from_52w_high_pct=-5.0,
            atr_contracting=True,
            nr7_flag=True,
            inside_day_flag=True,
            first_higher_low_pivot2=False,
            first_higher_high_pivot2=True,
            latest_session_hull_buy_turn=False,
            latest_session_utbot_buy_turn=True,
            days_since_hull_turn_bull=99,
            days_since_utbot_buy=0,
            first_close_above_ma20_after_5bars=True,
            breakout_dist_20d_high_pct=-1.0,
        )
        digest = build_post_close_digest(
            [row],
            run_stamp="20260424_050000",
            generated_at=self.generated_at,
            market_date=self.market_date,
            scan_label="post-close default",
            universe_count=1,
            result_count=1,
            skip_count=0,
        )
        item = digest.section_map()[EARLY_REVERSAL_KEY].items[0]

        self.assertEqual(item.ticker, "BOX")
        self.assertEqual(item.reversal_type, "BOX_BREAKOUT")
        self.assertIn(item.reversal_phase, {"TRIGGERED", "CONFIRMED"})

    def test_early_reversal_requires_context_trigger_and_volume(self):
        weak_without_trigger = self._early_reversal_row(
            "WEAK",
            latest_session_hull_buy_turn=False,
            latest_session_utbot_buy_turn=False,
            days_since_hull_turn_bull=99,
            days_since_utbot_buy=99,
            first_close_above_ma20_after_5bars=False,
            first_higher_low_pivot2=False,
            first_higher_high_pivot2=False,
            atr_contracting=False,
            nr7_flag=False,
            inside_day_flag=False,
            three_weeks_tight=False,
            volume_dry_up_score=0.0,
            bb_percent_b=0.95,
        )
        trigger_without_context = self._early_reversal_row(
            "TRIG",
            ret20_pct=8.0,
            ret60_pct=16.0,
            dist_sma50_pct=3.0,
            drawdown_from_52w_high_pct=-4.0,
            atr_contracting=False,
            nr7_flag=False,
            inside_day_flag=False,
            three_weeks_tight=False,
            volume_dry_up_score=0.0,
            bb_percent_b=0.95,
        )
        no_volume = self._early_reversal_row(
            "NOVOL",
            volume_ratio_20=0.9,
            volume_expansion_score=0.0,
            obv_slope=0.0,
            cmf=0.0,
            volume_bullish=False,
        )
        digest = build_post_close_digest(
            [weak_without_trigger, trigger_without_context, no_volume],
            run_stamp="20260424_050000",
            generated_at=self.generated_at,
            market_date=self.market_date,
            scan_label="post-close default",
            universe_count=3,
            result_count=3,
            skip_count=0,
        )
        tickers = [item.ticker for item in digest.section_map()[EARLY_REVERSAL_KEY].items]

        self.assertNotIn("WEAK", tickers)
        self.assertNotIn("TRIG", tickers)
        self.assertNotIn("NOVOL", tickers)

    def test_early_reversal_allows_only_strong_prep_in_top20(self):
        weak_prep = self._early_reversal_row(
            "PREPLOW",
            latest_session_hull_buy_turn=False,
            latest_session_utbot_buy_turn=False,
            days_since_hull_turn_bull=99,
            days_since_utbot_buy=99,
            first_close_above_ma20_after_5bars=False,
            first_higher_low_pivot2=True,
            volume_ratio_20=0.9,
            volume_expansion_score=0.0,
            obv_slope=0.0,
            cmf=0.0,
            volume_bullish=False,
        )
        strong_prep = self._early_reversal_row(
            "PREPHI",
            latest_session_hull_buy_turn=False,
            latest_session_utbot_buy_turn=False,
            days_since_hull_turn_bull=99,
            days_since_utbot_buy=99,
            first_close_above_ma20_after_5bars=False,
            first_higher_low_pivot2=True,
            first_higher_high_pivot2=False,
            volume_ratio_20=1.6,
            volume_expansion_score=35.0,
            obv_slope=0.5,
            cmf=0.1,
            volume_bullish=True,
            breakout_dist_20d_high_pct=-1.0,
        )
        digest = build_post_close_digest(
            [weak_prep, strong_prep],
            run_stamp="20260424_050000",
            generated_at=self.generated_at,
            market_date=self.market_date,
            scan_label="post-close default",
            universe_count=2,
            result_count=2,
            skip_count=0,
        )
        items = {item.ticker: item for item in digest.section_map()[EARLY_REVERSAL_KEY].items}

        self.assertNotIn("PREPLOW", items)
        self.assertIn("PREPHI", items)
        self.assertEqual(items["PREPHI"].reversal_phase, "PREP")
        self.assertIn("watch_only_prep", items["PREPHI"].risk_flags)
        self.assertGreaterEqual(items["PREPHI"].early_reversal_score or 0.0, 80.0)

    def test_early_reversal_late_chase_gets_penalized_and_ranked_lower(self):
        early = self._early_reversal_row("EARLY", scan_score=200.0)
        late = self._early_reversal_row(
            "LATE",
            scan_score=220.0,
            chg_5d=18.0,
            dist_sma20_pct=13.0,
            ma20_dist_pct=13.0,
            zscore20=2.4,
            bb_percent_b=1.2,
            breakout_dist_20d_high_pct=12.0,
        )
        digest = build_post_close_digest(
            [late, early],
            run_stamp="20260424_050000",
            generated_at=self.generated_at,
            market_date=self.market_date,
            scan_label="post-close default",
            universe_count=2,
            result_count=2,
            skip_count=0,
        )
        items = digest.section_map()[EARLY_REVERSAL_KEY].items
        by_ticker = {item.ticker: item for item in items}
        tickers = [item.ticker for item in items]

        self.assertLess(tickers.index("EARLY"), tickers.index("LATE"))
        self.assertIn("late_chase", by_ticker["LATE"].risk_flags)
        self.assertIn("ma20_extended", by_ticker["LATE"].risk_flags)
        self.assertIn("zscore_hot", by_ticker["LATE"].risk_flags)
        self.assertIn("bb_overextended", by_ticker["LATE"].risk_flags)

    def test_early_reversal_hard_risks_are_excluded(self):
        rows = [
            self._early_reversal_row("SELL", utbot_sell_last_date=self.market_date.isoformat()),
            self._early_reversal_row("THIN", thin_trade_risk=True),
            self._early_reversal_row("GAP", bearish_gap_failure=True),
            self._early_reversal_row("MULTI", multi_sell=2),
            self._early_reversal_row("HIGHC", strategy_conflict_level="HIGH"),
            self._early_reversal_row("LOWV", volume_ratio_20=0.79),
        ]
        digest = build_post_close_digest(
            rows,
            run_stamp="20260424_050000",
            generated_at=self.generated_at,
            market_date=self.market_date,
            scan_label="post-close default",
            universe_count=len(rows),
            result_count=len(rows),
            skip_count=0,
        )

        self.assertEqual(digest.section_map()[EARLY_REVERSAL_KEY].items, [])

    def test_early_reversal_message_contains_ers_phase_type_and_watch_fields(self):
        row = self._early_reversal_row("MELI")
        digest = build_post_close_digest(
            [row],
            run_stamp="20260424_050000",
            generated_at=self.generated_at,
            market_date=self.market_date,
            scan_label="post-close default",
            universe_count=1,
            result_count=1,
            skip_count=0,
        )
        message = build_post_close_message_texts(digest)[0]

        self.assertIn("## 0-4.", message)
        self.assertIn("MELI | ERS", message)
        self.assertIn("CONFIRMED", message)
        self.assertIn("MIXED_REVERSAL", message)
        self.assertIn("confirmed_reversal_watch", message)
        self.assertIn("MA20", message)

    def test_hull_buy_turn_section_sits_after_early_reversal_and_includes_all_hull_rows(self):
        by_date = self._hull_buy_turn_row("DATE", latest_session_hull_buy_turn=False)
        by_flag = self._hull_buy_turn_row("FLAG", hull_turn_bull_last_date="N/A")
        digest = build_post_close_digest(
            [by_date, by_flag],
            run_stamp="20260424_050000",
            generated_at=self.generated_at,
            market_date=self.market_date,
            scan_label="post-close default",
            universe_count=2,
            result_count=2,
            skip_count=0,
        )
        section_map = digest.section_map()
        items = section_map[HULL_BUY_TURN_KEY].items

        expected_prefix = [
            "qbs_buy_now",
            "qbs_chase_watch",
            "qbs_pullback_wait",
            *SCAN_TAXONOMY_SECTION_ORDER,
            STEADY_WINNER_SECTION_KEY,
            EARLY_REVERSAL_KEY,
            HULL_BUY_TURN_KEY,
            STARTUP9_CONFIRM_KEY,
            TECHNICAL_BUY_CLUSTER_KEY,
        ]
        self.assertEqual(digest.section_order[: len(expected_prefix)], expected_prefix)
        self.assertEqual({item.ticker for item in items}, {"DATE", "FLAG"})
        self.assertTrue(all(item.bucket == "HULL_BUY_TURN" for item in items))

    def test_hull_buy_turn_sorts_utbot_overlap_first_and_keeps_risk_rows(self):
        solo = self._hull_buy_turn_row(
            "SOLO",
            volume_ratio_20=5.0,
            cmf=0.2,
            obv_slope=1.0,
            scan_score=200.0,
        )
        dual = self._hull_buy_turn_row(
            "DUAL",
            latest_session_utbot_buy_turn=True,
            utbot_buy_last_date=self.market_date.isoformat(),
            volume_ratio_20=1.0,
            cmf=0.01,
            obv_slope=0.1,
            scan_score=100.0,
        )
        risky = self._hull_buy_turn_row(
            "RISK",
            thin_trade_risk=True,
            strategy_conflict_level="HIGH",
            volume_ratio_20=0.5,
            chg_5d=18.0,
            chg=13.0,
            dist_sma20_pct=18.0,
            zscore20=2.8,
            multi_sell=2,
        )
        digest = build_post_close_digest(
            [solo, dual, risky],
            run_stamp="20260424_050000",
            generated_at=self.generated_at,
            market_date=self.market_date,
            scan_label="post-close default",
            universe_count=3,
            result_count=3,
            skip_count=0,
        )
        items = digest.section_map()[HULL_BUY_TURN_KEY].items
        by_ticker = {item.ticker: item for item in items}

        self.assertEqual(items[0].ticker, "DUAL")
        self.assertIn("UTBot동시", by_ticker["DUAL"].tags)
        self.assertIn("RISK", by_ticker)
        self.assertIn("thin_trade", by_ticker["RISK"].risk_flags)
        self.assertIn("high_conflict", by_ticker["RISK"].risk_flags)
        self.assertIn("low_volume", by_ticker["RISK"].risk_flags)
        self.assertIn("multi_sell", by_ticker["RISK"].risk_flags)
        self.assertIn("chase_risk", by_ticker["RISK"].risk_flags)
        self.assertIn("extended_day", by_ticker["RISK"].risk_flags)

    def test_hull_buy_turn_message_contains_hull_fields(self):
        row = self._hull_buy_turn_row("HULLX", volume_ratio_20=1.42, rs_rank_vs_index=78.0)
        digest = build_post_close_digest(
            [row],
            run_stamp="20260424_050000",
            generated_at=self.generated_at,
            market_date=self.market_date,
            scan_label="post-close default",
            universe_count=1,
            result_count=1,
            skip_count=0,
        )
        message = build_post_close_message_texts(digest)[0]

        self.assertIn("## 0-5.", message)
        self.assertIn("HULLX | HULL BUY", message)
        self.assertIn("근거:", message)
        self.assertIn("확인:", message)
        self.assertIn("주의:", message)
        self.assertIn("RS 78", message)

    def test_five_day_only_candidates_land_in_chase_risk_top20(self):
        rows = [
            self._row(
                f"C{i:02d}",
                final_entry_eligible=False,
                final_entry_selected=False,
                latest_session_utbot_buy_turn=False,
                latest_session_hull_buy_turn=False,
                utbot_buy_last_date="N/A",
                hull_turn_bull_last_date="N/A",
                chg=1.0,
                chg_5d=30.0 - i,
                uptrend_persistent=False,
                pullback_ready=False,
                pullback_reentry=False,
                bull_strength_recent=False,
                gap_setup_candidate=False,
                pocket_pivot_candidate=False,
                new_52w_high=False,
                hma_ema_long_entry=False,
                hma_ema_long_aligned=False,
                hma25_ema25_cross_bull=False,
                rs_rank_vs_index=20.0,
                ret20_percentile=20.0,
                ret60_percentile=20.0,
                near_52w_high_2pct=False,
                breakout_dist_20d_high_pct=-20.0,
                drawdown_from_52w_high_pct=-20.0,
                nr7_flag=False,
                inside_day_flag=False,
                three_weeks_tight=False,
                atr_contracting=False,
            )
            for i in range(25)
        ]
        digest = build_post_close_digest(
            rows,
            run_stamp="20260424_050000",
            generated_at=self.generated_at,
            market_date=self.market_date,
            scan_label="post-close default",
            universe_count=25,
            result_count=25,
            skip_count=0,
        )
        chase_items = digest.section_map()["chase_risk"].items

        self.assertEqual(len(chase_items), BOARD_SECTION_LIMIT)
        self.assertEqual([item.ticker for item in chase_items], [f"C{i:02d}" for i in range(20)])

    def test_qbs_watch_sections_limit_to_top20(self):
        chase_rows = [
            self._row(
                f"Q{i:02d}",
                chg=15.0 + (i * 0.01),
                chg_value=1.0,
                final_entry_score=200 - i,
                scan_score=250 - i,
            )
            for i in range(25)
        ]
        pullback_rows = [
            self._row(
                f"P{i:02d}",
                final_entry_eligible=False,
                final_entry_selected=False,
                latest_session_utbot_buy_turn=False,
                latest_session_hull_buy_turn=False,
                utbot_buy_last_date="N/A",
                hull_turn_bull_last_date="N/A",
                chg=-1.0 + (i * 0.001),
                chg_value=-0.1,
                chg_5d=2.0,
                pullback_reentry=True,
                pullback_ready=True,
                uptrend_persistent=True,
                bull_strength_recent=True,
                gap_setup_candidate=False,
                pocket_pivot_candidate=False,
                new_52w_high=False,
                hma_ema_long_entry=False,
                hma_ema_long_aligned=False,
                hma25_ema25_cross_bull=False,
                volume_ratio_20=1.2,
                final_entry_score=0,
                scan_score=180 - i,
            )
            for i in range(25)
        ]
        digest = build_post_close_digest(
            [*chase_rows, *pullback_rows],
            run_stamp="20260424_050000",
            generated_at=self.generated_at,
            market_date=self.market_date,
            scan_label="post-close default",
            universe_count=50,
            result_count=50,
            skip_count=0,
        )

        qbs_chase_items = digest.section_map()["qbs_chase_watch"].items
        qbs_pullback_items = digest.section_map()["qbs_pullback_wait"].items

        self.assertEqual(len(qbs_chase_items), 20)
        self.assertEqual([item.ticker for item in qbs_chase_items], [f"Q{i:02d}" for i in range(20)])
        self.assertEqual(len(qbs_pullback_items), 20)
        self.assertEqual([item.ticker for item in qbs_pullback_items], [f"P{i:02d}" for i in range(20)])

    def test_hma_selector_applies_price_over_ema50_gate(self):
        ok = self._row("OK", price=101.0, ema50=100.0)
        blocked = self._row("BLOCKED", price=99.0, ema50=100.0)
        source_sections = select_post_close_sections([ok, blocked], target_date=self.market_date)

        self.assertEqual([item["ticker"] for item in source_sections["hma_ema_trend"]], ["OK"])

    def test_message_contract_is_single_main_message(self):
        digest = build_post_close_digest(
            [self._row("ALPHA"), self._row("BETA", final_entry_score=80.0, chg_5d=9.5)],
            run_stamp="20260424_050000",
            generated_at=self.generated_at,
            market_date=self.market_date,
            scan_label="post-close default",
            universe_count=2,
            result_count=2,
            skip_count=0,
        )
        messages = build_post_close_message_texts(digest)
        self.assertEqual(len(messages), 1)
        self.assertIn("## 1.", messages[0])
        self.assertIn("## 2.", messages[0])

    def test_qbs_blocks_render_above_existing_sections_with_special_numbering(self):
        digest = build_post_close_digest(
            [self._row("ALPHA")],
            run_stamp="20260424_050000",
            generated_at=self.generated_at,
            market_date=self.market_date,
            scan_label="post-close default",
            universe_count=1,
            result_count=1,
            skip_count=0,
        )
        message = build_post_close_message_texts(digest)[0]

        qbs_0 = message.index("## 0. ")
        qbs_01 = message.index("## 0-1. ")
        qbs_02 = message.index("## 0-2. ")
        taxonomy_1 = message.index("## T1. ")
        taxonomy_13 = message.index("## T13. ")
        steady_03 = message.index("## 0-3. ")
        early_04 = message.index("## 0-4. ")
        hull_05 = message.index("## 0-5. ")
        startup_1 = message.index("## 1. ")
        tech_2 = message.index("## 2. ")
        aggressive_1 = message.index("## PART 1.")
        aggressive_8 = message.index("## PART 8.")
        normal_4 = message.index("## 4. ")
        self.assertTrue(qbs_0 < qbs_01 < qbs_02 < taxonomy_1 < taxonomy_13 < steady_03 < early_04 < hull_05 < startup_1 < tech_2 < aggressive_1 < aggressive_8 < normal_4)
        self.assertIn("QBS", message)

    def test_aggressive_message_contains_conditions_and_core_metrics(self):
        digest = build_post_close_digest(
            [self._aggressive_trend_row("SNDK")],
            run_stamp="20260424_050000",
            generated_at=self.generated_at,
            market_date=self.market_date,
            scan_label="post-close default",
            universe_count=1,
            result_count=1,
            skip_count=0,
        )
        message = build_post_close_message_texts(digest)[0]

        self.assertIn("## PART 2. 강추세 지속형", message)
        self.assertIn("조건:", message)
        self.assertIn("SNDK", message)
        self.assertIn("ATR", message)
        self.assertIn("Vol20", message)
        self.assertIn("RS", message)
        self.assertIn("ADX", message)

    def test_empty_qbs_blocks_are_always_rendered(self):
        digest = build_post_close_digest(
            [],
            run_stamp="20260424_050000",
            generated_at=self.generated_at,
            market_date=self.market_date,
            scan_label="post-close default",
            universe_count=0,
            result_count=0,
            skip_count=0,
        )
        message = build_post_close_message_texts(digest)[0]

        self.assertIn("## 0. ", message)
        self.assertIn("## 0-1. ", message)
        self.assertIn("## 0-2. ", message)
        self.assertIn("## T1. ", message)
        self.assertIn("## T13. ", message)
        self.assertIn("## PART 1.", message)
        self.assertIn("## PART 8.", message)
        self.assertIn("## 0-3. ", message)
        self.assertIn("## 0-4. ", message)
        self.assertIn("## 0-5. ", message)
        self.assertIn("## 1. ", message)
        self.assertIn("## 2. ", message)
        self.assertGreaterEqual(message.count("- 해당 없음"), 3)

    def test_chunk_split_keeps_qbs_before_existing_sections(self):
        rows = [self._row(f"T{i:02d}", final_entry_score=100.0 - i, chg_5d=15.0 - (i / 10.0)) for i in range(12)]
        digest = build_post_close_digest(
            rows,
            run_stamp="20260424_050000",
            generated_at=self.generated_at,
            market_date=self.market_date,
            scan_label="post-close default",
            universe_count=12,
            result_count=12,
            skip_count=0,
        )
        chunks = split_telegram_message_text(build_post_close_message_texts(digest)[0], chunk_size=350)
        joined = "\n".join(chunks)

        self.assertGreater(len(chunks), 1)
        self.assertTrue(
            joined.index("## 0. ")
            < joined.index("## 0-1. ")
            < joined.index("## 0-2. ")
            < joined.index("## 0-3. ")
            < joined.index("## 0-4. ")
            < joined.index("## 0-5. ")
            < joined.index("## 1. ")
            < joined.index("## 2. ")
            < joined.index("## PART 1.")
            < joined.index("## PART 8.")
            < joined.index("## 4. ")
        )

    def test_message_lines_show_board_label_change_volume_reason_and_risk(self):
        buy_hull_only = self._row(
            "BUYHULL",
            latest_session_utbot_buy_turn=False,
            latest_session_hull_buy_turn=True,
            utbot_buy_last_date="N/A",
            hull_turn_bull_last_date=self.market_date.isoformat(),
        )
        sell_both = self._row(
            "SELLBOTH",
            final_entry_eligible=False,
            final_entry_selected=False,
            latest_session_utbot_buy_turn=False,
            latest_session_hull_buy_turn=False,
            utbot_buy_last_date="N/A",
            hull_turn_bull_last_date="N/A",
            utbot_sell_last_date=self.market_date.isoformat(),
            hull_turn_bear_last_date=self.market_date.isoformat(),
            hma_ema_long_entry=False,
            hma_ema_long_aligned=False,
        )
        digest = build_post_close_digest(
            [buy_hull_only, sell_both],
            run_stamp="20260424_050000",
            generated_at=self.generated_at,
            market_date=self.market_date,
            scan_label="post-close default",
            universe_count=2,
            result_count=2,
            skip_count=0,
        )
        message = build_post_close_message_texts(digest)[0]

        self.assertIn("BUYHULL | CONFLUENCE | +2.35% | x1.45", message)
        self.assertIn("SELLBOTH | SELL_RISK | +2.35% | x1.45", message)
        self.assertIn("| sell_turn", message)

    def test_five_day_only_message_line_uses_chase_risk_section(self):
        row = self._row(
            "FIVE",
            final_entry_eligible=False,
            final_entry_selected=False,
            latest_session_utbot_buy_turn=False,
            latest_session_hull_buy_turn=False,
            utbot_buy_last_date="N/A",
            hull_turn_bull_last_date="N/A",
            chg=1.0,
            chg_5d=17.42,
            uptrend_persistent=False,
            pullback_ready=False,
            pullback_reentry=False,
            bull_strength_recent=False,
            gap_setup_candidate=False,
            pocket_pivot_candidate=False,
            new_52w_high=False,
            hma_ema_long_entry=False,
            hma_ema_long_aligned=False,
            hma25_ema25_cross_bull=False,
            rs_rank_vs_index=20.0,
            ret20_percentile=20.0,
            ret60_percentile=20.0,
            near_52w_high_2pct=False,
            breakout_dist_20d_high_pct=-20.0,
            drawdown_from_52w_high_pct=-20.0,
            nr7_flag=False,
            inside_day_flag=False,
            three_weeks_tight=False,
            atr_contracting=False,
        )
        digest = build_post_close_digest(
            [row],
            run_stamp="20260424_050000",
            generated_at=self.generated_at,
            market_date=self.market_date,
            scan_label="post-close default",
            universe_count=1,
            result_count=1,
            skip_count=0,
        )
        message = build_post_close_message_texts(digest)[0]

        self.assertIn("## 11. 단기 급등 / 추격주의 후보", message)
        self.assertIn("FIVE | CHASE_RISK | +1.00% | x1.45 | 5D", message)
        self.assertIn("## 13. 5일 상승률 Top30 (Top 1)", message)
        self.assertIn("티커 | 5일 상승률 | RSI | Vol20 | MA20이격 | 상태", message)
        self.assertIn("FIVE | +17.42% | RSI 68.2 | x1.45 | +9.0% | 강한상승/거래량동반", message)
        self.assertEqual(digest.section_map()["five_day_top"].items[0].chg_pct, 17.42)
        self.assertEqual(digest.section_map()["five_day_top"].items[0].reason, "강한상승/거래량동반")

    def test_split_telegram_message_text_prefers_section_boundaries(self):
        text = "\n\n".join(
            [
                "[오늘 종목판]\n- 시장일: 2026-04-23 (US)",
                "## 1. 오늘 최우선 후보 (Top 2)\n1. AAA | (+1.00, +2.00%) | x1.20",
                "## 2. 오늘 매수전환 (1 items)\n1. BBB | (+0.50, +1.00%) | x1.10 | UTBot",
                "## 3. 눌림목 재진입 (1 items)\n1. CCC | (+0.30, +0.80%) | x0.95",
            ]
        )
        chunks = split_telegram_message_text(text, chunk_size=120)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(any(chunk.startswith("## 2.") for chunk in chunks))
        self.assertTrue(any("## 3." in chunk for chunk in chunks))

    def test_write_local_digest_artifacts_writes_latest_and_versioned_json(self):
        digest = build_post_close_digest(
            [self._row("AAPL")],
            run_stamp="20260424_050000",
            generated_at=self.generated_at,
            market_date=self.market_date,
            scan_label="post-close default",
            universe_count=1,
            result_count=1,
            skip_count=0,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            paths = write_local_digest_artifacts(digest, out_dir=Path(temp_dir))
            latest_payload = json.loads(paths["latest_path"].read_text(encoding="utf-8"))
            versioned_payload = json.loads(paths["versioned_path"].read_text(encoding="utf-8"))

        self.assertEqual(latest_payload["version"], "2.0")
        self.assertEqual(versioned_payload["run_stamp"], "20260424_050000")
        self.assertIn("items", latest_payload["sections"][0])

    def test_digest_candidates_carry_one_month_and_one_year_returns(self):
        digest = build_post_close_digest(
            [self._row("RET", ret20_pct=7.25, ret252_pct=123.45)],
            run_stamp="20260424_050000",
            generated_at=self.generated_at,
            market_date=self.market_date,
            scan_label="post-close default",
            universe_count=1,
            result_count=1,
            skip_count=0,
        )
        section_map = digest.section_map()

        steady_item = section_map[STEADY_WINNER_SECTION_KEY].items[0]
        five_day_item = section_map["five_day_top"].items[0]
        qbs_item = section_map["qbs_buy_now"].items[0]

        self.assertEqual(steady_item.ret_1m_pct, 7.25)
        self.assertEqual(steady_item.ret_1y_pct, 123.45)
        self.assertEqual(steady_item.high_pos_pct, -6.0)
        self.assertEqual(five_day_item.ret_1m_pct, 7.25)
        self.assertEqual(five_day_item.ret_1y_pct, 123.45)
        self.assertEqual(five_day_item.high_pos_pct, -6.0)
        self.assertEqual(qbs_item.ret_1m_pct, 7.25)
        self.assertEqual(qbs_item.ret_1y_pct, 123.45)
        self.assertEqual(qbs_item.high_pos_pct, -6.0)

    def test_build_post_close_digest_bundle_keeps_publish_failure_non_blocking(self):
        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "scripts.daily_scan_and_notify.publish_digest_if_configured",
            side_effect=RuntimeError("publish unavailable"),
        ):
            bundle = _build_post_close_digest_bundle(
                rows=[self._row("AAPL")],
                out_dir=Path(temp_dir),
                run_stamp="20260424_050000",
                run_label="20260424_050000",
                run_at_kst=self.generated_at,
                market_date=self.market_date,
                scan_label="post-close default",
                universe_count=1,
                result_count=1,
                skip_count=0,
                publish_enabled=True,
            )
            self.assertTrue(Path(bundle["summary_path"]).exists())
            self.assertEqual(len(bundle["message_texts"]), 1)
            self.assertEqual(bundle["publish_status"]["reason"], "publish_error")
            self.assertIn("publish unavailable", bundle["publish_status"]["detail"])

    def test_send_telegram_if_enabled_uses_digest_message_sequence_when_present(self):
        args = SimpleNamespace(dry_run=False, skip_telegram=False)
        with patch.dict(
            "os.environ",
            {"TELEGRAM_BOT_TOKEN": "token", "TELEGRAM_CHAT_ID": "chat"},
            clear=False,
        ), patch("scripts.daily_scan_and_notify.send_digest_telegram_messages") as mock_digest_send, patch(
            "scripts.daily_scan_and_notify.send_telegram_message"
        ) as mock_single_send, patch("scripts.daily_scan_and_notify.send_telegram_document") as mock_document:
            _send_telegram_if_enabled(
                args,
                summary_text="legacy summary",
                csv_path=Path("C:/tmp/scan.csv"),
                scan_label="post-close default",
                run_at_kst=self.generated_at,
                message_texts=["main board"],
            )

        mock_digest_send.assert_called_once_with("token", "chat", ["main board"])
        mock_single_send.assert_not_called()
        mock_document.assert_called_once()

    def test_send_telegram_if_enabled_raises_when_csv_document_fails(self):
        args = SimpleNamespace(dry_run=False, skip_telegram=False)
        with patch.dict(
            "os.environ",
            {"TELEGRAM_BOT_TOKEN": "token", "TELEGRAM_CHAT_ID": "chat"},
            clear=False,
        ), patch("scripts.daily_scan_and_notify.send_digest_telegram_messages"), patch(
            "scripts.daily_scan_and_notify.send_telegram_document",
            return_value=False,
        ):
            with self.assertRaises(RuntimeError):
                _send_telegram_if_enabled(
                    args,
                    summary_text="legacy summary",
                    csv_path=Path("C:/tmp/scan.csv"),
                    scan_label="post-close default",
                    run_at_kst=self.generated_at,
                    message_texts=["main board"],
                )


class HomeDigestLoaderTests(unittest.TestCase):
    def test_extract_section_candidates_reads_items_contract(self):
        payload = {
            "sections": [
                {"key": "final_top", "items": [{"ticker": "AAPL"}, {"ticker": "MSFT"}]},
                {
                    "key": "five_day_top",
                    "items": [
                        {"ticker": "NVDA", "chg_5d": 12.3, "status": "강한상승"},
                        {"ticker": "AMD", "chg_5d": 9.8, "status": "정상상승"},
                    ],
                },
                {
                    "key": STEADY_WINNER_SECTION_KEY,
                    "items": [
                        {"ticker": "META", "pul_score": 84.0, "entry_type": "steady_hold_watch"},
                    ],
                },
                {
                    "key": EARLY_REVERSAL_KEY,
                    "items": [
                        {
                            "ticker": "MELI",
                            "early_reversal_score": 84.0,
                            "reversal_phase": "TRIGGERED",
                            "reversal_type": "DOWN_TREND_REVERSAL",
                        },
                    ],
                },
                {
                    "key": HULL_BUY_TURN_KEY,
                    "items": [
                        {"ticker": "HULLX", "bucket": "HULL_BUY_TURN", "reason": "HULL"},
                    ],
                },
            ]
        }
        self.assertEqual([item["ticker"] for item in extract_section_candidates(payload, "final_top", limit=1)], ["AAPL"])
        self.assertEqual([item["ticker"] for item in extract_section_candidates(payload, "five_day_top", limit=1)], ["NVDA"])
        self.assertEqual([item["ticker"] for item in extract_section_candidates(payload, STEADY_WINNER_SECTION_KEY, limit=1)], ["META"])
        self.assertEqual([item["ticker"] for item in extract_section_candidates(payload, EARLY_REVERSAL_KEY, limit=1)], ["MELI"])
        self.assertEqual([item["ticker"] for item in extract_section_candidates(payload, HULL_BUY_TURN_KEY, limit=1)], ["HULLX"])

    def test_telegram_board_rows_keep_five_day_and_tolerate_missing_long_returns(self):
        payload = {
            "version": "2.0",
            "section_order": [TECHNICAL_BUY_CLUSTER_KEY, STEADY_WINNER_SECTION_KEY, EARLY_REVERSAL_KEY, HULL_BUY_TURN_KEY, "five_day_top"],
            "sections": [
                {
                    "key": TECHNICAL_BUY_CLUSTER_KEY,
                    "title": "기술적 매수시그널 클러스터 Top 20",
                    "item_count": 1,
                    "ranked": True,
                    "items": [
                        {
                            "ticker": "FLOW",
                            "price": 42.0,
                            "chg_pct": 2.4,
                            "volume_ratio_20": 1.8,
                            "section_key": TECHNICAL_BUY_CLUSTER_KEY,
                            "rank": 1,
                            "technical_buy_score": 12.5,
                            "technical_buy_signal_count": 4,
                            "technical_buy_hits": ["CMF강세", "MF강세전환", "Pocket Pivot"],
                            "technical_buy_bucket": "수급매집형",
                            "technical_buy_reason": "수급매집형 / CMF강세 + Pocket Pivot",
                            "technical_buy_risk_flags": [],
                        }
                    ],
                },
                {
                    "key": STEADY_WINNER_SECTION_KEY,
                    "title": "steady",
                    "item_count": 1,
                    "ranked": True,
                    "items": [
                        {
                            "ticker": "META",
                            "price": 300.0,
                            "chg_pct": 1.2,
                            "chg_5d": 4.1,
                            "ret_1m_pct": 8.8,
                            "ret_1y_pct": 52.5,
                            "high_pos_pct": -3.2,
                            "volume_ratio_20": 0.96,
                            "section_key": STEADY_WINNER_SECTION_KEY,
                            "rank": 1,
                            "bucket": "STEADY_WINNER",
                            "pul_score": 78.0,
                            "entry_type": "steady_hold_watch",
                        }
                    ],
                },
                {
                    "key": EARLY_REVERSAL_KEY,
                    "title": "reversal",
                    "item_count": 1,
                    "ranked": True,
                    "items": [
                        {
                            "ticker": "MELI",
                            "price": 1500.0,
                            "chg_pct": 2.1,
                            "chg_5d": 4.8,
                            "ret_1m_pct": -4.0,
                            "ret_1y_pct": -18.5,
                            "high_pos_pct": -22.0,
                            "rsi": 52.0,
                            "ma20_dist_pct": 3.2,
                            "volume_ratio_20": 1.42,
                            "section_key": EARLY_REVERSAL_KEY,
                            "rank": 1,
                            "bucket": "TRIGGERED",
                            "reason": "MA20+HULL",
                            "risk_flags": ["watch_only"],
                            "early_reversal_score": 84.0,
                            "reversal_phase": "TRIGGERED",
                            "reversal_type": "DOWN_TREND_REVERSAL",
                            "entry_type": "reversal_trigger_watch",
                        }
                    ],
                },
                {
                    "key": "five_day_top",
                    "title": "5D",
                    "item_count": 1,
                    "ranked": True,
                    "items": [
                        {
                            "ticker": "NVDA",
                            "price": 120.0,
                            "chg_pct": 99.0,
                            "chg_5d": 12.3,
                            "volume_ratio_20": 1.5,
                            "section_key": "five_day_top",
                            "rank": 1,
                            "status": "strong",
                            "source_flags": {"today_chg_pct": 1.1},
                        },
                        {
                            "ticker": "FIVE",
                            "price": 110.0,
                            "chg_value": 10.0,
                            "chg_5d": 20.0,
                            "volume_ratio_20": 1.1,
                            "section_key": "five_day_top",
                            "rank": 2,
                            "status": "strong",
                        }
                    ],
                },
                {
                    "key": HULL_BUY_TURN_KEY,
                    "title": "hull",
                    "item_count": 1,
                    "ranked": True,
                    "items": [
                        {
                            "ticker": "HULLX",
                            "price": 90.0,
                            "chg_pct": 2.1,
                            "chg_5d": 4.8,
                            "ret_1m_pct": 9.0,
                            "ret_1y_pct": 33.0,
                            "high_pos_pct": -5.5,
                            "rsi": 61.0,
                            "ma20_dist_pct": 3.1,
                            "volume_ratio_20": 1.3,
                            "section_key": HULL_BUY_TURN_KEY,
                            "rank": 1,
                            "bucket": "HULL_BUY_TURN",
                            "reason": "HULL+거래량동반",
                            "risk_flags": [],
                            "source_flags": {"rs_rank_vs_index": 76.0, "hull_confirm": "MA20 +3.1% / HULL D+0"},
                            "entry_type": "hull_buy_turn_watch",
                        }
                    ],
                },
            ],
        }

        digest = home_page.telegram_digest_from_payload(payload)
        board_rows = home_page._build_telegram_board_rows(digest)
        rows_by_ticker = {row["ticker"]: row for row in board_rows}

        self.assertEqual(rows_by_ticker["META"]["one_month_pct"], 8.8)
        self.assertEqual(rows_by_ticker["FLOW"]["section"], "TECH BUY")
        self.assertEqual(rows_by_ticker["FLOW"]["bucket"], "수급매집형")
        self.assertEqual(rows_by_ticker["FLOW"]["score"], "TBS 12.5")
        self.assertEqual(rows_by_ticker["FLOW"]["score_value"], 12.5)
        self.assertEqual(rows_by_ticker["FLOW"]["entry"], "technical_cluster_watch")
        self.assertIn("CMF강세", rows_by_ticker["FLOW"]["setup"])
        self.assertEqual(rows_by_ticker["META"]["one_year_pct"], 52.5)
        self.assertEqual(rows_by_ticker["META"]["high_pos_pct"], -3.2)
        self.assertEqual(rows_by_ticker["MELI"]["section"], "REVERSAL")
        self.assertEqual(rows_by_ticker["MELI"]["bucket"], "TRIGGERED")
        self.assertEqual(rows_by_ticker["MELI"]["score"], "ERS 84")
        self.assertEqual(rows_by_ticker["MELI"]["score_value"], 84.0)
        self.assertEqual(rows_by_ticker["MELI"]["entry"], "reversal_trigger_watch")
        self.assertEqual(rows_by_ticker["MELI"]["one_month_pct"], -4.0)
        self.assertEqual(rows_by_ticker["MELI"]["one_year_pct"], -18.5)
        self.assertEqual(rows_by_ticker["MELI"]["rsi"], 52.0)
        self.assertEqual(rows_by_ticker["MELI"]["ma20"], 3.2)
        self.assertEqual(rows_by_ticker["HULLX"]["section"], "HULL")
        self.assertEqual(rows_by_ticker["HULLX"]["bucket"], "HULL_BUY_TURN")
        self.assertEqual(rows_by_ticker["HULLX"]["score"], "HULL")
        self.assertIsNone(rows_by_ticker["HULLX"]["score_value"])
        self.assertEqual(rows_by_ticker["HULLX"]["entry"], "hull_buy_turn_watch")
        self.assertEqual(rows_by_ticker["NVDA"]["five_day_pct"], 12.3)
        self.assertEqual(rows_by_ticker["NVDA"]["today_pct"], 1.1)
        self.assertIsNone(rows_by_ticker["NVDA"]["one_month_pct"])
        self.assertIsNone(rows_by_ticker["NVDA"]["one_year_pct"])
        self.assertEqual(rows_by_ticker["FIVE"]["today_pct"], 10.0)
        self.assertEqual(rows_by_ticker["FIVE"]["entry"], "momentum_watch")

    def test_telegram_board_rows_include_aggressive_payload_and_filters(self):
        part2_key = AGGRESSIVE_NEXT_DAY_SECTION_KEYS[1]
        part7_key = AGGRESSIVE_NEXT_DAY_SECTION_KEYS[6]
        payload = {
            "version": "2.0",
            "section_order": [part2_key, part7_key, "qbs_buy_now"],
            "sections": [
                {
                    "key": part2_key,
                    "title": "PART 2 강추세 지속형",
                    "item_count": 1,
                    "ranked": True,
                    "quality_floor": "조건: strong trend",
                    "items": [
                        {
                            "ticker": "SNDK",
                            "price": 156.23,
                            "chg_pct": 16.59,
                            "chg_5d": 31.62,
                            "volume_ratio_20": 1.23,
                            "section_key": part2_key,
                            "rank": 1,
                            "reason": "uptrend+volume+CMF+OBV",
                            "tags": ["near-high"],
                            "risk_flags": ["extended_day", "extended_5d"],
                            "source_flags": {
                                "atr_pct": 6.4,
                                "adx": 49.0,
                                "rs_rank_vs_index": 98.9,
                                "dist_sma20_pct": 43.7,
                                "drawdown_from_52w_high_pct": -0.1,
                                "breakout_dist_20d_high_pct": -0.1,
                                "compression_count": 0,
                                "ret20_pct": 75.0,
                            },
                        }
                    ],
                },
                {
                    "key": part7_key,
                    "title": "PART 7 갭업 후 실패 없는 추격형",
                    "item_count": 1,
                    "ranked": True,
                    "items": [
                        {
                            "ticker": "SNDK",
                            "price": 156.23,
                            "chg_pct": 16.59,
                            "chg_5d": 31.62,
                            "volume_ratio_20": 1.23,
                            "section_key": part7_key,
                            "rank": 1,
                            "reason": "gap+near-high+CMF",
                            "risk_flags": ["gap_chase"],
                            "source_flags": {
                                "atr_pct": 6.4,
                                "adx": 49.0,
                                "rs_rank_vs_index": 98.9,
                                "dist_sma20_pct": 43.7,
                                "drawdown_from_52w_high_pct": -0.1,
                                "breakout_dist_20d_high_pct": -0.1,
                                "compression_count": 0,
                            },
                        }
                    ],
                },
                {
                    "key": "qbs_buy_now",
                    "title": "buy",
                    "item_count": 1,
                    "ranked": True,
                    "items": [
                        {
                            "ticker": "AAPL",
                            "price": 200.0,
                            "chg_pct": 1.25,
                            "volume_ratio_20": 1.2,
                            "section_key": "qbs_buy_now",
                            "rank": 1,
                            "bucket": "BUY_NOW",
                            "qbs_score": 88.0,
                        }
                    ],
                },
            ],
        }

        digest = home_page.telegram_digest_from_payload(payload)
        board_rows = home_page._build_telegram_board_rows(digest)
        aggressive_rows = home_page._filter_telegram_board_rows(board_rows, "aggressive")
        part2_row = next(row for row in aggressive_rows if row["section_key"] == part2_key)

        self.assertEqual([row["section_key"] for row in aggressive_rows], [part2_key, part7_key])
        self.assertEqual([row["ticker"] for row in aggressive_rows], ["SNDK", "SNDK"])
        self.assertEqual(part2_row["section"], "P2 강추세")
        self.assertEqual(part2_row["entry"], "aggressive_next_day_watch")
        self.assertEqual(part2_row["atr"], 6.4)
        self.assertEqual(part2_row["rs"], 98.9)
        self.assertEqual(part2_row["adx"], 49.0)
        self.assertEqual(part2_row["ma20"], 43.7)
        self.assertEqual(part2_row["high_pos_pct"], -0.1)
        self.assertEqual(part2_row["breakout_dist_20d_high_pct"], -0.1)
        self.assertEqual(part2_row["compression_count"], 0)
        self.assertIn("uptrend", part2_row["setup_parts"])
        self.assertIn("extended_day", part2_row["risk"])
        self.assertTrue(part2_row["has_warning"])
        self.assertEqual([row["ticker"] for row in home_page._filter_telegram_board_rows(board_rows, "qbs")], ["AAPL"])
        self.assertEqual([row["section_key"] for row in home_page._filter_telegram_board_rows(board_rows, "trend")], [part2_key])
        self.assertEqual([row["section_key"] for row in home_page._filter_telegram_board_rows(board_rows, "entry")], [part7_key, "qbs_buy_now"])
        self.assertEqual([row["section_key"] for row in home_page._filter_telegram_board_rows(board_rows, "risk")], [part2_key, part7_key])

    def test_telegram_board_rows_include_scan_taxonomy_filters(self):
        payload = {
            "version": "2.0",
            "section_order": ["scan_taxonomy_buy_now", "scan_taxonomy_accumulation"],
            "sections": [
                {
                    "key": "scan_taxonomy_buy_now",
                    "title": "지금매수",
                    "item_count": 1,
                    "ranked": True,
                    "items": [
                        {
                            "ticker": "TSLA",
                            "price": 210.0,
                            "chg_pct": 2.4,
                            "volume_ratio_20": 1.8,
                            "section_key": "scan_taxonomy_buy_now",
                            "rank": 1,
                            "label": "STRONG_BUY_NOW",
                            "reason": "상승추세+눌림지지+거래량",
                            "source_flags": {"scan_action_label": "STRONG_BUY_NOW", "rs_rank_vs_index": 88},
                        }
                    ],
                },
                {
                    "key": "scan_taxonomy_accumulation",
                    "title": "기관매집",
                    "item_count": 1,
                    "ranked": True,
                    "items": [
                        {
                            "ticker": "TSLA",
                            "price": 210.0,
                            "chg_pct": 2.4,
                            "volume_ratio_20": 1.8,
                            "section_key": "scan_taxonomy_accumulation",
                            "rank": 1,
                            "label": "ACCUMULATION",
                            "reason": "PocketPivot+CMF+",
                        }
                    ],
                },
            ],
        }

        digest = home_page.telegram_digest_from_payload(payload)
        board_rows = home_page._build_telegram_board_rows(digest)
        taxonomy_rows = home_page._filter_telegram_board_rows(board_rows, "taxonomy")
        buy_now_rows = home_page._filter_telegram_board_rows(board_rows, "scan_taxonomy_buy_now")

        self.assertEqual([row["section_key"] for row in taxonomy_rows], ["scan_taxonomy_buy_now", "scan_taxonomy_accumulation"])
        self.assertEqual([row["ticker"] for row in taxonomy_rows], ["TSLA", "TSLA"])
        self.assertEqual(buy_now_rows[0]["section"], "지금매수")
        self.assertEqual(buy_now_rows[0]["entry"], "STRONG_BUY_NOW")

    def test_home_digest_dashboard_helpers_preserve_structure_and_render_html(self):
        part2_key = AGGRESSIVE_NEXT_DAY_SECTION_KEYS[1]
        part7_key = AGGRESSIVE_NEXT_DAY_SECTION_KEYS[6]
        payload = {
            "version": "2.0",
            "section_order": [part2_key, part7_key],
            "sections": [
                {
                    "key": part2_key,
                    "title": "PART 2 강추세 지속형",
                    "item_count": 1,
                    "ranked": True,
                    "quality_floor": "조건: strong trend",
                    "items": [
                        {
                            "ticker": "SNDK",
                            "price": 156.23,
                            "chg_pct": 16.59,
                            "chg_5d": 31.62,
                            "volume_ratio_20": 1.23,
                            "section_key": part2_key,
                            "rank": 1,
                            "reason": "uptrend+volume",
                            "risk_flags": ["extended_day"],
                            "source_flags": {"atr_pct": 6.4, "adx": 49.0, "rs_rank_vs_index": 98.9},
                        }
                    ],
                },
                {
                    "key": part7_key,
                    "title": "PART 7 갭업 후 실패 없는 추격형",
                    "item_count": 1,
                    "ranked": True,
                    "items": [
                        {
                            "ticker": "SNDK",
                            "price": 156.23,
                            "chg_pct": 16.59,
                            "chg_5d": 31.62,
                            "volume_ratio_20": 1.23,
                            "section_key": part7_key,
                            "rank": 1,
                            "reason": "gap+near-high",
                            "risk_flags": ["gap_chase"],
                            "source_flags": {"atr_pct": 6.4, "adx": 49.0, "rs_rank_vs_index": 98.9},
                        }
                    ],
                },
            ],
        }

        digest = home_page.telegram_digest_from_payload(payload)
        board_rows = home_page._build_telegram_board_rows(digest)
        aggressive_rows = home_page._filter_telegram_board_rows(board_rows, "aggressive")
        html = home_page._aggressive_board_table_html(aggressive_rows, include_rank=True)
        meta_html = home_page._telegram_section_meta_html(digest.sections[0])

        self.assertEqual([row["section_key"] for row in aggressive_rows], [part2_key, part7_key])
        self.assertEqual([row["ticker"] for row in aggressive_rows], ["SNDK", "SNDK"])
        self.assertEqual(home_page._default_telegram_board_filter(board_rows), "aggressive")
        self.assertIn("<table", html)
        self.assertIn("<th>Ticker</th>", html)
        self.assertNotIn("&lt;th", html)
        self.assertIn("조건: strong trend", meta_html)

    def test_telegram_board_rows_enrich_qbs_from_matching_detail_sections(self):
        payload = {
            "version": "2.0",
            "section_order": ["qbs_buy_now", "confluence"],
            "sections": [
                {
                    "key": "qbs_buy_now",
                    "title": "buy",
                    "item_count": 1,
                    "ranked": True,
                    "items": [
                        {
                            "ticker": "AAPL",
                            "price": 200.0,
                            "chg_pct": 1.25,
                            "volume_ratio_20": 1.2,
                            "section_key": "qbs_buy_now",
                            "rank": 1,
                            "bucket": "BUY_NOW",
                            "qbs_score": 88.0,
                        }
                    ],
                },
                {
                    "key": "confluence",
                    "title": "detail",
                    "item_count": 1,
                    "ranked": True,
                    "items": [
                        {
                            "ticker": "AAPL",
                            "price": 200.0,
                            "chg_pct": 1.25,
                            "chg_5d": 6.5,
                            "ret_1m_pct": 11.2,
                            "ret_1y_pct": 45.6,
                            "high_pos_pct": -8.9,
                            "rsi": 66.7,
                            "ma20_dist_pct": 4.4,
                            "volume_ratio_20": 1.2,
                            "section_key": "confluence",
                            "rank": 1,
                        }
                    ],
                },
            ],
        }

        digest = home_page.telegram_digest_from_payload(payload)
        qbs_row = home_page._build_telegram_board_rows(digest)[0]

        self.assertEqual(qbs_row["today_pct"], 1.25)
        self.assertEqual(qbs_row["five_day_pct"], 6.5)
        self.assertEqual(qbs_row["one_month_pct"], 11.2)
        self.assertEqual(qbs_row["one_year_pct"], 45.6)
        self.assertEqual(qbs_row["high_pos_pct"], -8.9)
        self.assertEqual(qbs_row["rsi"], 66.7)
        self.assertEqual(qbs_row["ma20"], 4.4)
        self.assertEqual(qbs_row["entry"], "buy_now")

    def test_telegram_board_rows_enrich_remaining_fields_from_market_lookup(self):
        payload = {
            "version": "2.0",
            "section_order": ["qbs_buy_now"],
            "sections": [
                {
                    "key": "qbs_buy_now",
                    "title": "buy",
                    "item_count": 1,
                    "ranked": True,
                    "items": [
                        {
                            "ticker": "AAPL",
                            "price": 200.0,
                            "chg_pct": 1.25,
                            "volume_ratio_20": 1.2,
                            "section_key": "qbs_buy_now",
                            "rank": 1,
                            "bucket": "BUY_NOW",
                            "qbs_score": 88.0,
                        }
                    ],
                }
            ],
        }

        digest = home_page.telegram_digest_from_payload(payload)
        base_rows = home_page._build_telegram_board_rows(digest)
        self.assertEqual(home_page._board_missing_metric_tickers(base_rows), ["AAPL"])

        rows = home_page._build_telegram_board_rows(
            digest,
            market_metric_lookup={
                "AAPL": {
                    "price": 201.0,
                    "today_pct": 1.5,
                    "five_day_pct": 6.5,
                    "one_month_pct": 12.0,
                    "one_year_pct": 55.0,
                    "high_pos_pct": -2.5,
                    "rsi": 67.0,
                    "vol20": 1.4,
                    "ma20": 5.5,
                }
            },
        )
        row = rows[0]

        self.assertEqual(row["price"], 200.0)
        self.assertEqual(row["today_pct"], 1.25)
        self.assertEqual(row["five_day_pct"], 6.5)
        self.assertEqual(row["one_month_pct"], 12.0)
        self.assertEqual(row["one_year_pct"], 55.0)
        self.assertEqual(row["high_pos_pct"], -2.5)
        self.assertEqual(row["rsi"], 67.0)
        self.assertEqual(row["vol20"], 1.2)
        self.assertEqual(row["ma20"], 5.5)
        self.assertEqual(home_page._board_missing_metric_tickers(rows), [])

    def test_build_telegram_digest_message_uses_actual_formatter_structure(self):
        payload = {
            "version": "2.0",
            "scan_mode": "post_close",
            "run_stamp": "run-1",
            "market_date": "2026-05-01",
            "generated_at": "2026-05-02T06:16:51+09:00",
            "section_order": ["qbs_buy_now", STEADY_WINNER_SECTION_KEY, EARLY_REVERSAL_KEY, HULL_BUY_TURN_KEY, "sell_risk"],
            "universe_count": 10,
            "result_count": 2,
            "skip_count": 1,
            "sections": [
                {
                    "key": "qbs_buy_now",
                    "title": "오늘 매수 최종 후보 Top 20",
                    "item_count": 1,
                    "ranked": True,
                    "items": [
                        {
                            "ticker": "AAPL",
                            "price": 200.0,
                            "chg_value": 1.25,
                            "chg_pct": 0.63,
                            "volume_ratio_20": 1.5,
                            "section_key": "qbs_buy_now",
                            "rank": 1,
                            "label": "BUY_NOW",
                            "reason": "final+buy",
                            "qbs_score": 88.0,
                            "tags": ["final", "buy"],
                            "risk_flags": [],
                        }
                    ],
                },
                {
                    "key": STEADY_WINNER_SECTION_KEY,
                    "title": "계속 우상향 주도주 Top 30",
                    "item_count": 1,
                    "ranked": True,
                    "items": [
                        {
                            "ticker": "META",
                            "price": 300.0,
                            "chg_pct": 1.2,
                            "chg_5d": 4.1,
                            "volume_ratio_20": 0.96,
                            "section_key": STEADY_WINNER_SECTION_KEY,
                            "rank": 1,
                            "label": "STEADY_WINNER",
                            "bucket": "STEADY_WINNER",
                            "reason": "EMA정배열+HMA상승",
                            "risk_flags": [],
                            "pul_score": 78.0,
                            "entry_type": "steady_hold_watch",
                        }
                    ],
                },
                {
                    "key": EARLY_REVERSAL_KEY,
                    "title": "초기 반전 포착 Top 20",
                    "item_count": 1,
                    "ranked": True,
                    "items": [
                        {
                            "ticker": "MELI",
                            "price": 1500.0,
                            "chg_pct": 2.1,
                            "chg_5d": 4.8,
                            "volume_ratio_20": 1.42,
                            "section_key": EARLY_REVERSAL_KEY,
                            "rank": 1,
                            "label": "TRIGGERED",
                            "bucket": "TRIGGERED",
                            "reason": "MA20+HULL",
                            "risk_flags": [],
                            "early_reversal_score": 84.0,
                            "reversal_phase": "TRIGGERED",
                            "reversal_type": "DOWN_TREND_REVERSAL",
                            "entry_type": "reversal_trigger_watch",
                            "source_flags": {"reversal_confirm": "20D -1.8% / MA20 hold"},
                        }
                    ],
                },
                {
                    "key": HULL_BUY_TURN_KEY,
                    "title": "당일 HULL 매수전환",
                    "item_count": 1,
                    "ranked": True,
                    "items": [
                        {
                            "ticker": "HULLX",
                            "price": 90.0,
                            "chg_pct": 2.1,
                            "chg_5d": 4.8,
                            "volume_ratio_20": 1.3,
                            "section_key": HULL_BUY_TURN_KEY,
                            "rank": 1,
                            "label": "HULL BUY",
                            "bucket": "HULL_BUY_TURN",
                            "reason": "HULL",
                            "risk_flags": [],
                            "source_flags": {"rs_rank_vs_index": 76.0, "hull_confirm": "MA20 +3.1% / HULL D+0"},
                            "entry_type": "hull_buy_turn_watch",
                        }
                    ],
                },
                {
                    "key": "sell_risk",
                    "title": "매도전환 / 위험 후보",
                    "item_count": 1,
                    "items": [
                        {
                            "ticker": "TSLA",
                            "price": 180.0,
                            "chg_value": -2.0,
                            "chg_pct": -1.1,
                            "volume_ratio_20": 2.0,
                            "section_key": "sell_risk",
                            "rank": 1,
                            "label": "SELL_RISK",
                            "reason": "sell_turn",
                            "risk_flags": ["sell_turn"],
                        }
                    ],
                },
            ],
        }

        message = home_page.build_telegram_digest_message(payload)

        self.assertIn("## 0. 오늘 매수 최종 후보 Top 20", message)
        self.assertIn("## 0-3. 계속 우상향 주도주 Top 30", message)
        self.assertIn("## 0-4. 초기 반전 포착 Top 20", message)
        self.assertIn("## 0-5. 당일 HULL 매수전환", message)
        self.assertIn("## 12. 매도전환 / 위험 후보", message)
        self.assertIn("AAPL", message)
        self.assertIn("META | PUL 78", message)
        self.assertIn("MELI | ERS 84", message)
        self.assertIn("HULLX | HULL BUY", message)
        self.assertIn("TSLA", message)
        self.assertLess(message.index("AAPL"), message.index("META"))
        self.assertLess(message.index("META"), message.index("MELI"))
        self.assertLess(message.index("MELI"), message.index("HULLX"))
        self.assertLess(message.index("HULLX"), message.index("TSLA"))

    def test_resolve_github_digest_config_uses_default_repo_when_unconfigured(self):
        with patch.dict(os.environ, {}, clear=True), patch("app_ui.pages.home_page._read_secret", return_value=""):
            config = home_page.resolve_github_digest_config()

        self.assertEqual(config["repo"], "dglhj7694/cipherX")
        self.assertEqual(config["branch"], "telegram-digest")
        self.assertEqual(config["path"], "post_close/latest.json")

    def test_resolve_github_digest_config_uses_github_repository_env_before_default(self):
        with patch.dict(os.environ, {"GITHUB_REPOSITORY": "owner/runtime-repo"}, clear=True), patch(
            "app_ui.pages.home_page._read_secret",
            return_value="",
        ):
            config = home_page.resolve_github_digest_config()

        self.assertEqual(config["repo"], "owner/runtime-repo")

    def test_load_latest_telegram_digest_uses_remote_then_cache_fallback(self):
        payload = {
            "market_date": "2026-04-23",
            "sections": [
                {"key": "final_top", "items": [{"ticker": "AAPL"}, {"ticker": "MSFT"}]},
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "digest.json"
            with patch(
                "app_ui.pages.home_page.resolve_github_digest_config",
                return_value={"repo": "owner/repo", "branch": "telegram-digest", "path": "post_close/latest.json", "token": ""},
            ), patch("app_ui.pages.home_page._fetch_digest_cached", return_value=payload):
                first = load_latest_telegram_digest(cache_path=cache_path)

            self.assertEqual(first["source"], "remote")
            self.assertEqual(first["payload"]["market_date"], "2026-04-23")
            self.assertEqual([item["ticker"] for item in extract_section_candidates(first["payload"], "final_top", limit=1)], ["AAPL"])

            with patch(
                "app_ui.pages.home_page.resolve_github_digest_config",
                return_value={"repo": "owner/repo", "branch": "telegram-digest", "path": "post_close/latest.json", "token": ""},
            ), patch("app_ui.pages.home_page._fetch_digest_cached", side_effect=RuntimeError("network down")):
                second = load_latest_telegram_digest(cache_path=cache_path)

            self.assertEqual(second["source"], "cache")
            self.assertEqual(second["payload"]["market_date"], "2026-04-23")
            self.assertIn("network down", second["error"])

    def test_home_digest_summary_badges_show_combined_metadata(self):
        payload = {
            "scan_label": "통합 장마감 스캔",
            "market_date": "2026-04-23",
            "briefing_refs": {
                "combined_universe": True,
                "universe_profiles": ["default", "russell2000"],
                "dedup_removed_count": 7,
            },
            "sections": [
                {"key": "final_top", "items": [{"ticker": "AAPL"}]},
            ],
        }
        digest = home_page.telegram_digest_from_payload(payload)
        badges_html = home_page._telegram_summary_badges_html(digest, source_label="원격 동기화", source_tone="accent")

        self.assertIn("통합", badges_html)
        self.assertIn("default+russell2000", badges_html)
        self.assertIn("중복제거 7", badges_html)

    def test_fetch_digest_from_github_reports_empty_or_invalid_latest(self):
        with self.assertRaisesRegex(RuntimeError, "empty"):
            home_page._validated_digest_payload({})

        with self.assertRaisesRegex(RuntimeError, "sections"):
            home_page._validated_digest_payload({"market_date": "2026-04-23"})

    def test_load_latest_telegram_digest_cache_fallback_mentions_empty_remote(self):
        payload = {
            "market_date": "2026-04-23",
            "sections": [
                {"key": "final_top", "items": [{"ticker": "AAPL"}]},
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "digest.json"
            home_page.write_digest_cache(payload, cache_path=cache_path)
            with patch(
                "app_ui.pages.home_page.resolve_github_digest_config",
                return_value={"repo": "owner/repo", "branch": "telegram-digest", "path": "post_close/latest.json", "token": ""},
            ), patch("app_ui.pages.home_page._fetch_digest_cached", side_effect=RuntimeError("GitHub digest content is empty")):
                result = load_latest_telegram_digest(cache_path=cache_path)

        self.assertEqual(result["source"], "cache")
        self.assertEqual(result["payload"]["market_date"], "2026-04-23")
        self.assertIn("GitHub digest content is empty", result["error"])


if __name__ == "__main__":
    unittest.main()
