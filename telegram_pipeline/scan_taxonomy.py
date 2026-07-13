from __future__ import annotations

import ast
import json
from dataclasses import dataclass
from datetime import date
from typing import Any, Iterable, Mapping

from .rankers import is_truthy, safe_float, same_session_buy_turn, same_session_sell_turn

SCAN_TAXONOMY_LIMIT = 20
SCAN_TAXONOMY_SECTION_PREFIX = "scan_taxonomy_"


@dataclass(frozen=True)
class ScanTaxonomyTab:
    key: str
    title: str
    action_label: str
    quality_floor: str

    @property
    def section_key(self) -> str:
        return f"{SCAN_TAXONOMY_SECTION_PREFIX}{self.key}"

    @property
    def csv_key(self) -> str:
        return f"scan_tab_{self.key}"


SCAN_TAXONOMY_TABS: tuple[ScanTaxonomyTab, ...] = (
    ScanTaxonomyTab("buy_turn", "매수전환", "RECLAIM_BUY", "20/50선 회복 또는 전환 신호 + 거래량/모멘텀 확인"),
    ScanTaxonomyTab("rise_ready", "상승대기", "WATCH_EXPLOSION", "압축 + 추세 유지 + 상방 압력"),
    ScanTaxonomyTab("trend_continue", "상승지속", "TREND_FOLLOW", "정배열/ADX/RS 기반 추세 지속"),
    ScanTaxonomyTab("buy_now", "지금매수", "STRONG_BUY_NOW", "상승추세 + 눌림/지지 + 반전/거래량"),
    ScanTaxonomyTab("pullback", "눌림목", "BUY_ON_PULLBACK", "강한 종목의 단기 조정 후 재진입"),
    ScanTaxonomyTab("pre_breakout", "돌파직전", "WATCH_EXPLOSION", "고점 근처 압축 + 거래량 대기"),
    ScanTaxonomyTab("breakout_confirm", "돌파확인", "BUY_ON_BREAKOUT", "돌파/신고가 + 거래량 + 종가 강세"),
    ScanTaxonomyTab("accumulation", "기관매집", "ACCUMULATION", "Pocket Pivot/CMF/OBV 기반 수급 축적"),
    ScanTaxonomyTab("rebreakout", "재돌파", "RECLAIM_BUY", "이탈 후 20/50선 또는 전환 신호 빠른 회복"),
    ScanTaxonomyTab("gap_and_go", "갭앤고", "GAP_AND_GO", "갭업 후 갭 유지 추정 + 거래량 동반"),
    ScanTaxonomyTab("speculative_satellite", "초고변동 위성", "SPECULATIVE_SATELLITE", "고변동/급등/거래량 위성 후보"),
    ScanTaxonomyTab("wait", "관망", "WAIT", "압축/관심은 있으나 주요 매수 트리거 부족"),
    ScanTaxonomyTab("avoid", "제외/위험", "AVOID", "매도전환/갭실패/유동성/과열 리스크 우세"),
)

SCAN_TAXONOMY_TAB_BY_KEY: dict[str, ScanTaxonomyTab] = {tab.key: tab for tab in SCAN_TAXONOMY_TABS}
SCAN_TAXONOMY_TAB_BY_SECTION: dict[str, ScanTaxonomyTab] = {tab.section_key: tab for tab in SCAN_TAXONOMY_TABS}
SCAN_TAXONOMY_KEYS: tuple[str, ...] = tuple(tab.key for tab in SCAN_TAXONOMY_TABS)
SCAN_TAXONOMY_SECTION_ORDER: tuple[str, ...] = tuple(tab.section_key for tab in SCAN_TAXONOMY_TABS)
SCAN_TAXONOMY_SECTION_TITLES: dict[str, str] = {tab.section_key: tab.title for tab in SCAN_TAXONOMY_TABS}
SCAN_TAXONOMY_QUALITY_FLOORS: dict[str, str] = {tab.section_key: tab.quality_floor for tab in SCAN_TAXONOMY_TABS}

SCAN_TAXONOMY_OUTPUT_KEYS: tuple[str, ...] = (
    "scan_action_label",
    "scan_taxonomy_primary",
    "scan_taxonomy_primary_title",
    "scan_taxonomy_matches",
    "scan_taxonomy_reason",
    "scan_taxonomy_risk_flags",
)
SCAN_TAXONOMY_TAB_FIELD_KEYS: tuple[str, ...] = tuple(tab.csv_key for tab in SCAN_TAXONOMY_TABS)

PRIMARY_TAB_PRIORITY: tuple[str, ...] = (
    "avoid",
    "buy_now",
    "buy_turn",
    "rebreakout",
    "breakout_confirm",
    "pullback",
    "pre_breakout",
    "rise_ready",
    "accumulation",
    "trend_continue",
    "gap_and_go",
    "speculative_satellite",
    "wait",
)

BUY_TURN_SIGNALS = {
    "System_Turn_Bull",
    "Trend_Inflection_Bull",
    "UTBot_Buy",
    "Hull_Turn_Bull",
    "Cross_Above_20MA",
    "Cross_Above_50MA",
    "Cross_Above_200MA",
    "MACD_Cross_Buy",
    "MACD_Zero_Cross_Buy",
    "DMI_Cross_Bull",
    "ADX_New_Uptrend",
}
PULLBACK_SIGNALS = {
    "EMA_Pullback_Buy",
    "MA20_Support",
    "MA50_Support",
    "MA200_Support",
    "Pullback_123_Bull",
    "NonADX_123_Bull",
    "CS_Trend_Pullback_Buy",
    "CS_MA_Confluence_Buy",
    "CS_Structure_Support_Buy",
}
REVERSAL_SIGNALS = {
    "Hammer",
    "Bullish_Engulfing",
    "Morning_Star",
    "Outside_Bullish",
    "Setup_180_Bull",
    "Lizard_Bullish",
    "Three_Bar_Reversal_Buy",
    "StochRSI_Cross_Buy",
    "StochSlow_Cross_Buy",
}
COMPRESSION_SIGNALS = {
    "BB_Squeeze",
    "BB_Squeeze_Started",
    "NR7",
    "NR7_2",
    "Inside_Day",
    "Narrow_Range_Bar",
    "Boomer_Buy",
    "Three_Weeks_Tight",
    "Calm_After_Storm",
    "CS_Volatility_Explosion",
}
BREAKOUT_SIGNALS = {
    "Expansion_BO",
    "Expansion_Pivot_Buy",
    "BB_Upper_Break",
    "BB_Squeeze_End_Bull",
    "Squeeze_Fire_Buy",
    "Squeeze_Mom_Cross_Up",
    "Volume_Dry_Breakout_Buy",
    "Kumo_Breakout_Bull",
    "CS_Breakout_Momentum_Buy",
    "CS_Squeeze_Breakout_Buy",
    "CS_Breakout_Confirm_Buy",
    "CS_Ichimoku_Breakout_Buy",
    "New_52W_High",
    "New_52W_Closing_High",
}
ACCUMULATION_SIGNALS = {
    "Pocket_Pivot",
    "OBV_Div_Buy",
    "MF_Bull_Div",
    "CMF_Bull",
    "MF_Cross_Bull",
    "MF_Accel_Up",
    "CS_Institutional_Accumulation",
    "Volume_Surge",
}
GAP_UP_SIGNALS = {"Gap_Up", "Bullish_Gap_Reversal"}
SELL_RISK_SIGNALS = {
    "System_Turn_Bear",
    "Trend_Inflection_Bear",
    "UTBot_Sell",
    "Hull_Turn_Bear",
    "Fell_Below_20MA",
    "Fell_Below_50MA",
    "Fell_Below_200MA",
    "MACD_Cross_Sell",
    "MACD_Zero_Cross_Sell",
    "DMI_Cross_Bear",
    "Shooting_Star",
    "Bearish_Engulfing",
    "Gap_Up_Closed",
    "Gilligans_Sell",
    "Expansion_Double_Sticks",
    "Squeeze_Fire_Sell",
    "BB_Squeeze_End_Bear",
}


def _ticker(row: Mapping[str, Any]) -> str:
    return str(row.get("ticker") or "").strip().upper()


def _unique_append(items: list[str], value: str) -> None:
    text = str(value or "").strip()
    if text and text not in items:
        items.append(text)


def _text_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.replace("|", "+").replace(",", "+").split("+") if part.strip()]
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item or "").strip()]
    return [str(value).strip()] if str(value or "").strip() else []


def _parse_detected_signals(raw_value: Any) -> list[Mapping[str, Any]]:
    if raw_value is None:
        return []
    if isinstance(raw_value, Mapping):
        return [raw_value]
    if isinstance(raw_value, (list, tuple)):
        return [item for item in raw_value if isinstance(item, Mapping)]
    if isinstance(raw_value, str):
        text = raw_value.strip()
        if not text or text in {"-", "없음", "N/A", "n/a"}:
            return []
        for loader in (json.loads, ast.literal_eval):
            try:
                parsed = loader(text)
            except Exception:
                continue
            if isinstance(parsed, Mapping):
                return [parsed]
            if isinstance(parsed, (list, tuple)):
                return [item for item in parsed if isinstance(item, Mapping)]
    return []


def _signal_keys(row: Mapping[str, Any]) -> set[str]:
    keys: set[str] = set()
    for item in _parse_detected_signals(row.get("detected_signals")):
        key = str(item.get("key") or "").strip()
        if key:
            keys.add(key)
    for key in (
        BUY_TURN_SIGNALS
        | PULLBACK_SIGNALS
        | REVERSAL_SIGNALS
        | COMPRESSION_SIGNALS
        | BREAKOUT_SIGNALS
        | ACCUMULATION_SIGNALS
        | GAP_UP_SIGNALS
        | SELL_RISK_SIGNALS
    ):
        if is_truthy(row.get(key)):
            keys.add(key)
    return keys


def _has_any(signals: set[str], candidates: set[str]) -> bool:
    return bool(signals.intersection(candidates))


def _is_skipped(row: Mapping[str, Any]) -> bool:
    return str(row.get("scan_status") or "").strip().lower() == "skipped"


def _trend_ok(row: Mapping[str, Any]) -> bool:
    return bool(
        is_truthy(row.get("uptrend_persistent"))
        or is_truthy(row.get("strong_trend_persistent"))
        or is_truthy(row.get("hma_ema_long_aligned"))
        or is_truthy(row.get("hma_ema_long_entry"))
        or (
            safe_float(row.get("dist_ema50_pct", row.get("dist_sma50_pct", 0.0))) > 0.0
            and safe_float(row.get("ret20_pct", 0.0)) > 0.0
        )
    )


def _strong_trend(row: Mapping[str, Any]) -> bool:
    return bool(
        is_truthy(row.get("strong_trend_persistent"))
        or (
            _trend_ok(row)
            and safe_float(row.get("adx", 0.0)) >= 20.0
            and safe_float(row.get("rs_rank_vs_index", 0.0)) >= 60.0
        )
        or (
            is_truthy(row.get("hma_ema_long_aligned"))
            and safe_float(row.get("hma20_slope_pct", 0.0)) > 0.0
            and safe_float(row.get("hma60_slope_pct", 0.0)) > 0.0
        )
    )


def _volume_expanding(row: Mapping[str, Any]) -> bool:
    return bool(
        is_truthy(row.get("volume_surge"))
        or is_truthy(row.get("volume_bullish"))
        or safe_float(row.get("volume_ratio_20", 0.0)) >= 1.3
        or safe_float(row.get("volume_expansion_score", 0.0)) >= 30.0
    )


def _volume_surge(row: Mapping[str, Any]) -> bool:
    return bool(is_truthy(row.get("volume_surge")) or safe_float(row.get("volume_ratio_20", 0.0)) >= 1.5)


def _volume_dryup(row: Mapping[str, Any]) -> bool:
    return bool(
        safe_float(row.get("volume_ratio_20", 0.0)) <= 0.9
        or safe_float(row.get("volume_dry_up_score", 0.0)) >= 20.0
        or safe_float(row.get("volume_dry_up_score_5", 0.0)) >= 20.0
    )


def _compression(row: Mapping[str, Any], signals: set[str]) -> bool:
    return bool(
        _has_any(signals, COMPRESSION_SIGNALS)
        or is_truthy(row.get("nr7_flag"))
        or is_truthy(row.get("inside_day_flag"))
        or is_truthy(row.get("three_weeks_tight"))
        or is_truthy(row.get("atr_contracting"))
        or is_truthy(row.get("gap_setup_candidate"))
    )


def _near_high(row: Mapping[str, Any]) -> bool:
    return bool(
        is_truthy(row.get("near_52w_high_2pct"))
        or safe_float(row.get("drawdown_from_52w_high_pct", -999.0)) >= -5.0
        or safe_float(row.get("breakout_dist_20d_high_pct", -999.0)) >= -3.0
    )


def _buy_turn(row: Mapping[str, Any], signals: set[str], target_date: date) -> bool:
    return bool(
        same_session_buy_turn(row, target_date)
        or is_truthy(row.get("bull_turn_recent"))
        or is_truthy(row.get("first_close_above_ma20_after_5bars"))
        or is_truthy(row.get("hma25_ema25_cross_bull"))
        or _has_any(signals, BUY_TURN_SIGNALS)
    )


def _pullback(row: Mapping[str, Any], signals: set[str]) -> bool:
    pullback_depth = safe_float(row.get("drawdown_from_20d_high_pct", 0.0))
    swing_depth = safe_float(row.get("pullback_from_swing_high_pct", 0.0))
    return bool(
        is_truthy(row.get("pullback_ready"))
        or is_truthy(row.get("pullback_reentry"))
        or _has_any(signals, PULLBACK_SIGNALS)
        or (_trend_ok(row) and (-12.0 <= pullback_depth <= -1.0 or -12.0 <= swing_depth <= -2.0))
    )


def _reversal(row: Mapping[str, Any], signals: set[str]) -> bool:
    return bool(
        _has_any(signals, REVERSAL_SIGNALS)
        or is_truthy(row.get("first_higher_low_pivot2"))
        or is_truthy(row.get("first_higher_high_pivot2"))
    )


def _breakout(row: Mapping[str, Any], signals: set[str]) -> bool:
    return bool(
        _has_any(signals, BREAKOUT_SIGNALS)
        or is_truthy(row.get("new_52w_high"))
        or is_truthy(row.get("new_52w_closing_high"))
        or safe_float(row.get("breakout_dist_20d_high_pct", -999.0)) >= 0.0
        or (safe_float(row.get("dist_bb_upper_pct", -999.0)) >= 0.0 and safe_float(row.get("bb_percent_b", 0.0)) >= 0.95)
    )


def _accumulation(row: Mapping[str, Any], signals: set[str]) -> bool:
    return bool(
        is_truthy(row.get("pocket_pivot_candidate"))
        or is_truthy(row.get("pocket_pivot_recent"))
        or _has_any(signals, ACCUMULATION_SIGNALS)
        or (
            _trend_ok(row)
            and safe_float(row.get("volume_ratio_20", 0.0)) >= 1.3
            and safe_float(row.get("cmf", 0.0)) > 0.05
            and safe_float(row.get("obv_slope", 0.0)) > 0.1
        )
    )


def _gap_and_go(row: Mapping[str, Any], signals: set[str]) -> bool:
    gap_up = _has_any(signals, GAP_UP_SIGNALS) or safe_float(row.get("session_gap_pct", 0.0)) >= 2.0
    return bool(
        gap_up
        and safe_float(row.get("chg", 0.0)) >= 0.0
        and _volume_surge(row)
        and not is_truthy(row.get("bearish_gap_failure"))
        and "Gap_Up_Closed" not in signals
    )


def _satellite(row: Mapping[str, Any]) -> bool:
    return bool(
        safe_float(row.get("chg_5d", 0.0)) >= 15.0
        or safe_float(row.get("chg", 0.0)) >= 8.0
        or (
            safe_float(row.get("atr_pct", 0.0)) >= 6.0
            and _volume_surge(row)
            and safe_float(row.get("dollar_volume_20", 0.0)) >= 5_000_000.0
        )
    )


def _risk_flags(row: Mapping[str, Any], signals: set[str], target_date: date) -> list[str]:
    flags: list[str] = []
    if same_session_sell_turn(row, target_date):
        _unique_append(flags, "sell_turn")
    elif is_truthy(row.get("utbot_sell_recent")) or is_truthy(row.get("hull_turn_bear_recent")):
        _unique_append(flags, "recent_sell_pressure")
    if safe_float(row.get("multi_sell", 0.0)) >= 2.0:
        _unique_append(flags, "multi_sell")
    if is_truthy(row.get("thin_trade_risk")):
        _unique_append(flags, "thin_trade")
    if is_truthy(row.get("bearish_gap_failure")):
        _unique_append(flags, "gap_failure")
    if str(row.get("strategy_conflict_level") or "").strip().upper() == "HIGH":
        _unique_append(flags, "high_conflict")
    if _has_any(signals, SELL_RISK_SIGNALS):
        _unique_append(flags, "bearish_signal")
    if safe_float(row.get("volume_ratio_20", 0.0)) >= 4.0 and safe_float(row.get("chg", 0.0)) >= 10.0:
        _unique_append(flags, "volume_climax")
    if safe_float(row.get("zscore20", 0.0)) >= 3.0 or safe_float(row.get("dist_sma20_pct", row.get("ma20_dist_pct", 0.0))) >= 20.0:
        _unique_append(flags, "overheat_extension")
    return flags


def _avoid(row: Mapping[str, Any], risk_flags: list[str]) -> bool:
    hard = {"sell_turn", "multi_sell", "thin_trade", "gap_failure", "bearish_signal"}
    return bool(hard.intersection(risk_flags) or len(risk_flags) >= 2)


def _reason_for_tab(
    tab_key: str,
    *,
    row: Mapping[str, Any],
    signals: set[str],
    risk_flags: list[str],
    target_date: date,
) -> str:
    reason: list[str] = []
    if tab_key == "buy_turn":
        if same_session_buy_turn(row, target_date):
            _unique_append(reason, "당일전환")
        for key in ("System_Turn_Bull", "Trend_Inflection_Bull", "UTBot_Buy", "Hull_Turn_Bull", "Cross_Above_20MA", "Cross_Above_50MA", "MACD_Cross_Buy", "DMI_Cross_Bull"):
            if key in signals:
                _unique_append(reason, key)
        if _volume_expanding(row):
            _unique_append(reason, "거래량확인")
    elif tab_key == "rise_ready":
        if _compression(row, signals):
            _unique_append(reason, "압축")
        if _trend_ok(row):
            _unique_append(reason, "추세유지")
        if safe_float(row.get("rs_rank_vs_index", 0.0)) >= 60.0:
            _unique_append(reason, f"RS{int(safe_float(row.get('rs_rank_vs_index', 0.0)))}")
    elif tab_key == "trend_continue":
        if _strong_trend(row):
            _unique_append(reason, "강추세")
        if safe_float(row.get("adx", 0.0)) >= 20.0:
            _unique_append(reason, f"ADX{int(safe_float(row.get('adx', 0.0)))}")
        if _near_high(row):
            _unique_append(reason, "고점근처")
    elif tab_key == "buy_now":
        _unique_append(reason, "상승추세")
        if _pullback(row, signals):
            _unique_append(reason, "눌림지지")
        if _reversal(row, signals) or _buy_turn(row, signals, target_date):
            _unique_append(reason, "반전/전환")
        if _volume_expanding(row):
            _unique_append(reason, "거래량")
    elif tab_key == "pullback":
        if _trend_ok(row):
            _unique_append(reason, "추세중")
        if _pullback(row, signals):
            _unique_append(reason, "눌림")
        if safe_float(row.get("pullback_atr_multiple", 999.0)) <= 3.0:
            _unique_append(reason, "손절폭관리")
    elif tab_key == "pre_breakout":
        if _near_high(row):
            _unique_append(reason, "고점근처")
        if _compression(row, signals):
            _unique_append(reason, "압축")
        if _volume_dryup(row):
            _unique_append(reason, "거래량건조")
    elif tab_key == "breakout_confirm":
        if _breakout(row, signals):
            _unique_append(reason, "돌파확인")
        if is_truthy(row.get("new_52w_closing_high")):
            _unique_append(reason, "52주종가신고")
        if _volume_surge(row):
            _unique_append(reason, "거래량급증")
    elif tab_key == "accumulation":
        if is_truthy(row.get("pocket_pivot_candidate")) or "Pocket_Pivot" in signals:
            _unique_append(reason, "PocketPivot")
        if safe_float(row.get("cmf", 0.0)) > 0.05:
            _unique_append(reason, "CMF+")
        if safe_float(row.get("obv_slope", 0.0)) > 0.1:
            _unique_append(reason, "OBV+")
    elif tab_key == "rebreakout":
        _unique_append(reason, "이탈후회복")
        if _buy_turn(row, signals, target_date):
            _unique_append(reason, "재전환")
    elif tab_key == "gap_and_go":
        _unique_append(reason, "갭업유지")
        if _volume_surge(row):
            _unique_append(reason, "거래량")
    elif tab_key == "speculative_satellite":
        if safe_float(row.get("chg_5d", 0.0)) >= 15.0:
            _unique_append(reason, "5일급등")
        if safe_float(row.get("atr_pct", 0.0)) >= 6.0:
            _unique_append(reason, "고ATR")
        if _volume_surge(row):
            _unique_append(reason, "거래량")
    elif tab_key == "avoid":
        reason.extend(risk_flags)
    elif tab_key == "wait":
        if _compression(row, signals):
            _unique_append(reason, "방향대기")
        if safe_float(row.get("volume_ratio_20", 0.0)) < 1.0:
            _unique_append(reason, "거래량부족")
        if not reason:
            _unique_append(reason, "트리거부족")
    return "+".join(reason[:6]) if reason else "-"


def _taxonomy_score(row: Mapping[str, Any], tab_key: str) -> float:
    base = safe_float(row.get("final_entry_score", 0.0)) * 0.35
    base += safe_float(row.get("scan_score", 0.0)) * 0.08
    base += safe_float(row.get("qbs_score", 0.0)) * 0.12
    base += safe_float(row.get("technical_buy_score", 0.0)) * 1.5
    base += safe_float(row.get("startup9_score", 0.0)) * 0.2
    base += min(12.0, safe_float(row.get("volume_ratio_20", 0.0)) * 3.0)
    base += safe_float(row.get("rs_rank_vs_index", 0.0)) * 0.12
    if tab_key == "avoid":
        base += safe_float(row.get("multi_sell", 0.0)) * 20.0
        base += 25.0 if is_truthy(row.get("thin_trade_risk")) else 0.0
        base += 25.0 if is_truthy(row.get("bearish_gap_failure")) else 0.0
    elif tab_key == "speculative_satellite":
        base += safe_float(row.get("chg_5d", 0.0)) * 1.2 + safe_float(row.get("atr_pct", 0.0)) * 2.0
    elif tab_key in {"pre_breakout", "rise_ready"}:
        base += safe_float(row.get("gap_setup_score", 0.0)) * 5.0 + safe_float(row.get("volume_dry_up_score", 0.0)) * 0.2
    elif tab_key == "accumulation":
        base += safe_float(row.get("pocket_pivot_score", 0.0)) * 5.0 + max(0.0, safe_float(row.get("cmf", 0.0)) * 30.0)
    elif tab_key == "trend_continue":
        base += safe_float(row.get("adx", 0.0)) * 0.8 + safe_float(row.get("ret60_percentile", 0.0)) * 0.15
    return round(base, 4)


def evaluate_scan_taxonomy(row: Mapping[str, Any], *, target_date: date) -> dict[str, Any]:
    row_dict = dict(row or {})
    empty = {
        "scan_action_label": "",
        "scan_taxonomy_primary": "",
        "scan_taxonomy_primary_title": "",
        "scan_taxonomy_matches": "",
        "scan_taxonomy_reason": "",
        "scan_taxonomy_risk_flags": "",
        "scan_taxonomy_tags": [],
        "scan_taxonomy_scores": {},
        **{tab.csv_key: "N" for tab in SCAN_TAXONOMY_TABS},
    }
    if _is_skipped(row_dict) or not _ticker(row_dict):
        return empty

    signals = _signal_keys(row_dict)
    risk_flags = _risk_flags(row_dict, signals, target_date)
    avoid = _avoid(row_dict, risk_flags)
    buy_turn = _buy_turn(row_dict, signals, target_date)
    compression = _compression(row_dict, signals)
    trend_ok = _trend_ok(row_dict)
    strong_trend = _strong_trend(row_dict)
    pullback = _pullback(row_dict, signals)
    reversal = _reversal(row_dict, signals)
    breakout = _breakout(row_dict, signals)
    accumulation = _accumulation(row_dict, signals)
    near_high = _near_high(row_dict)
    volume_expanding = _volume_expanding(row_dict)
    volume_dryup = _volume_dryup(row_dict)

    matched: set[str] = set()
    if buy_turn and (volume_expanding or safe_float(row_dict.get("multi_buy", 0.0)) >= 2.0 or safe_float(row_dict.get("technical_buy_signal_count", 0.0)) >= 2.0):
        matched.add("buy_turn")
    if compression and trend_ok and not breakout:
        matched.add("rise_ready")
    if strong_trend and not avoid:
        matched.add("trend_continue")
    if trend_ok and pullback and (reversal or buy_turn) and volume_expanding and not avoid:
        matched.add("buy_now")
    if trend_ok and pullback and not avoid:
        matched.add("pullback")
    if trend_ok and near_high and (compression or is_truthy(row_dict.get("gap_setup_candidate"))) and not breakout:
        matched.add("pre_breakout")
    if breakout and volume_expanding and not avoid:
        matched.add("breakout_confirm")
    if accumulation and trend_ok and not avoid:
        matched.add("accumulation")
    if buy_turn and (is_truthy(row_dict.get("utbot_sell_recent")) or is_truthy(row_dict.get("hull_turn_bear_recent")) or _has_any(signals, {"Fell_Below_20MA", "Fell_Below_50MA"})):
        matched.add("rebreakout")
    if _gap_and_go(row_dict, signals) and not avoid:
        matched.add("gap_and_go")
    if _satellite(row_dict):
        matched.add("speculative_satellite")
    if avoid:
        matched.add("avoid")
    if not matched or (matched == {"speculative_satellite"} and not volume_expanding):
        matched.add("wait")
    if "avoid" not in matched and not matched.intersection({"buy_turn", "buy_now", "pullback", "pre_breakout", "breakout_confirm", "accumulation", "rebreakout", "gap_and_go", "trend_continue", "speculative_satellite"}):
        matched.add("wait")
    if "avoid" in matched:
        matched.discard("buy_now")
        matched.discard("breakout_confirm")
        matched.discard("gap_and_go")

    primary_key = next((key for key in PRIMARY_TAB_PRIORITY if key in matched), "wait")
    primary_tab = SCAN_TAXONOMY_TAB_BY_KEY[primary_key]
    ordered_matches = [key for key in SCAN_TAXONOMY_KEYS if key in matched]
    reason_by_key = {
        key: _reason_for_tab(key, row=row_dict, signals=signals, risk_flags=risk_flags, target_date=target_date)
        for key in ordered_matches
    }
    tags = [reason for reason in reason_by_key.values() if reason and reason != "-"]
    scores = {key: _taxonomy_score(row_dict, key) for key in ordered_matches}
    output = {
        "scan_action_label": primary_tab.action_label,
        "scan_taxonomy_primary": primary_key,
        "scan_taxonomy_primary_title": primary_tab.title,
        "scan_taxonomy_matches": "+".join(ordered_matches),
        "scan_taxonomy_reason": reason_by_key.get(primary_key, "-"),
        "scan_taxonomy_risk_flags": "+".join(risk_flags) if risk_flags else "",
        "scan_taxonomy_tags": tags,
        "scan_taxonomy_scores": scores,
    }
    for tab in SCAN_TAXONOMY_TABS:
        output[tab.csv_key] = "Y" if tab.key in matched else "N"
    return output


def annotate_rows_with_scan_taxonomy(rows: Iterable[Mapping[str, Any]], *, target_date: date) -> list[dict[str, Any]]:
    annotated: list[dict[str, Any]] = []
    for raw_row in rows or []:
        row = dict(raw_row or {})
        row.update(evaluate_scan_taxonomy(row, target_date=target_date))
        annotated.append(row)
    return annotated


def select_scan_taxonomy_sections(
    rows: Iterable[Mapping[str, Any]],
    *,
    target_date: date,
    limit: int = SCAN_TAXONOMY_LIMIT,
) -> dict[str, list[dict[str, Any]]]:
    row_list = [dict(row or {}) for row in (rows or [])]
    if any("scan_taxonomy_matches" not in row for row in row_list):
        row_list = annotate_rows_with_scan_taxonomy(row_list, target_date=target_date)
    output: dict[str, list[dict[str, Any]]] = {tab.section_key: [] for tab in SCAN_TAXONOMY_TABS}
    section_limit = max(0, int(limit or 0))
    for tab in SCAN_TAXONOMY_TABS:
        selected = [row for row in row_list if is_truthy(row.get(tab.csv_key))]
        selected.sort(
            key=lambda row, key=tab.key: (
                -safe_float(dict(row.get("scan_taxonomy_scores") or {}).get(key, _taxonomy_score(row, key))),
                -safe_float(row.get("final_entry_score", 0.0)),
                -safe_float(row.get("scan_score", 0.0)),
                -safe_float(row.get("volume_ratio_20", 0.0)),
                str(row.get("ticker", "")),
            )
        )
        output[tab.section_key] = selected[:section_limit]
    return output
