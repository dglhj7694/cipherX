from __future__ import annotations

import ast
import json
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Iterable, Mapping

from .rankers import is_truthy, parse_iso_date, safe_float, same_session_sell_turn

TECHNICAL_BUY_CLUSTER_KEY = "technical_buy_cluster"
TECHNICAL_BUY_CLUSTER_LIMIT = 20
TECHNICAL_BUY_CLUSTER_TITLE = f"기술적 매수시그널 클러스터 Top {TECHNICAL_BUY_CLUSTER_LIMIT}"
TECHNICAL_BUY_CLUSTER_QUALITY_FLOOR = "매수시그널 다중 발생 + 유동성 통과 + 최근 매도전환 없음"

TECHNICAL_BUY_RECENT_WINDOW = 5
TECHNICAL_BUY_MIN_SCORE = 5.0
TECHNICAL_BUY_MIN_SIGNAL_COUNT = 2
TECHNICAL_BUY_MIN_DOLLAR_VOLUME_20 = 20_000_000.0

BUCKET_TREND_TURN = "추세전환형"
BUCKET_REVERSAL_EARLY = "반전초입형"
BUCKET_SQUEEZE_BREAKOUT = "스퀴즈돌파형"
BUCKET_ACCUMULATION = "수급매집형"
BUCKET_PULLBACK_REENTRY = "눌림재진입형"
BUCKET_LEADER = "신고가/리더형"
BUCKET_MIXED = "혼합형"


@dataclass(frozen=True)
class TechnicalSignalDef:
    label: str
    score: float
    bucket: str


@dataclass
class TechnicalBuyCandidate:
    ticker: str
    technical_buy_score: float
    signal_count: int
    hits: list[str] = field(default_factory=list)
    bucket: str = ""
    reason: str = ""
    risk_flags: list[str] = field(default_factory=list)
    rank: int = 0
    price: float | None = None
    chg_value: float | None = None
    chg_pct: float | None = None
    volume_ratio_20: float | None = None
    atr_pct: float | None = None
    source_flags: dict[str, Any] = field(default_factory=dict)


SIGNAL_DEFS: dict[str, TechnicalSignalDef] = {
    "System_Turn_Bull": TechnicalSignalDef("전면매수전환", 3.5, BUCKET_TREND_TURN),
    "Trend_Inflection_Bull": TechnicalSignalDef("상승전환초입", 3.0, BUCKET_TREND_TURN),
    "UTBot_Buy": TechnicalSignalDef("UTBot Buy", 3.0, BUCKET_TREND_TURN),
    "Hull_Turn_Bull": TechnicalSignalDef("Hull Turn Bull", 2.8, BUCKET_TREND_TURN),
    "TK_Cross_Bull": TechnicalSignalDef("TK골든", 2.0, BUCKET_TREND_TURN),
    "DMI_Cross_Bull": TechnicalSignalDef("DMI강세교차", 2.0, BUCKET_TREND_TURN),
    "ADX_New_Uptrend": TechnicalSignalDef("신규상승추세", 2.2, BUCKET_TREND_TURN),
    "ADX_Momentum_Buy": TechnicalSignalDef("ADX점화", 1.8, BUCKET_TREND_TURN),
    "MACD_Cross_Buy": TechnicalSignalDef("MACD매수교차", 1.6, BUCKET_TREND_TURN),
    "MACD_Zero_Cross_Buy": TechnicalSignalDef("MACD0상향", 1.8, BUCKET_TREND_TURN),
    "StochRSI_Cross_Buy": TechnicalSignalDef("StRSI매수", 1.0, BUCKET_REVERSAL_EARLY),
    "Stoch_RSI_Buy": TechnicalSignalDef("StRSI매수", 1.0, BUCKET_REVERSAL_EARLY),
    "Stoch_Oversold": TechnicalSignalDef("Stoch과매도", 0.7, BUCKET_REVERSAL_EARLY),
    "Green_Dot_T1": TechnicalSignalDef("Green Dot T1", 2.3, BUCKET_REVERSAL_EARLY),
    "Green_Dot_T2": TechnicalSignalDef("Green Dot T2", 1.8, BUCKET_REVERSAL_EARLY),
    "Gold_Dot": TechnicalSignalDef("Gold Dot", 3.0, BUCKET_REVERSAL_EARLY),
    "Bull_Divergence": TechnicalSignalDef("Bull Divergence", 2.2, BUCKET_REVERSAL_EARLY),
    "RSI_Bull_Divergence": TechnicalSignalDef("RSI Bull Divergence", 1.8, BUCKET_REVERSAL_EARLY),
    "Morning_Star": TechnicalSignalDef("Morning Star", 1.8, BUCKET_REVERSAL_EARLY),
    "Hammer": TechnicalSignalDef("Hammer", 1.4, BUCKET_REVERSAL_EARLY),
    "Bullish_Engulfing": TechnicalSignalDef("Bullish Engulfing", 1.6, BUCKET_REVERSAL_EARLY),
    "Outside_Bullish": TechnicalSignalDef("Outside Bullish", 1.5, BUCKET_REVERSAL_EARLY),
    "OBV_Div_Buy": TechnicalSignalDef("OBV Div Buy", 1.6, BUCKET_ACCUMULATION),
    "MF_Bull_Div": TechnicalSignalDef("MF Bull Div", 1.8, BUCKET_ACCUMULATION),
    "CMF_Bull": TechnicalSignalDef("CMF강세", 1.6, BUCKET_ACCUMULATION),
    "MF_Cross_Bull": TechnicalSignalDef("MF강세전환", 1.6, BUCKET_ACCUMULATION),
    "MF_Accel_Up": TechnicalSignalDef("MF가속상승", 1.2, BUCKET_ACCUMULATION),
    "Pocket_Pivot": TechnicalSignalDef("Pocket Pivot", 2.5, BUCKET_ACCUMULATION),
    "Volume_Surge": TechnicalSignalDef("Volume Surge", 1.2, BUCKET_ACCUMULATION),
    "Volume_Climax_Buy": TechnicalSignalDef("Volume Climax Buy", 2.3, BUCKET_ACCUMULATION),
    "Squeeze_Fire_Buy": TechnicalSignalDef("Squeeze Fire Buy", 2.5, BUCKET_SQUEEZE_BREAKOUT),
    "BB_Squeeze_End_Bull": TechnicalSignalDef("BB Squeeze End Bull", 2.0, BUCKET_SQUEEZE_BREAKOUT),
    "BB_Upper_Break": TechnicalSignalDef("BB상단돌파", 1.7, BUCKET_SQUEEZE_BREAKOUT),
    "Kumo_Breakout_Bull": TechnicalSignalDef("Kumo상향돌파", 2.2, BUCKET_SQUEEZE_BREAKOUT),
    "NR7": TechnicalSignalDef("NR7", 0.7, BUCKET_SQUEEZE_BREAKOUT),
    "NR7_2": TechnicalSignalDef("NR7_2", 1.0, BUCKET_SQUEEZE_BREAKOUT),
    "Calm_After_Storm": TechnicalSignalDef("Calm After Storm", 0.8, BUCKET_SQUEEZE_BREAKOUT),
    "EMA_Pullback_Buy": TechnicalSignalDef("EMA눌림목", 2.0, BUCKET_PULLBACK_REENTRY),
    "MA20_Support": TechnicalSignalDef("MA20지지", 1.2, BUCKET_PULLBACK_REENTRY),
    "MA50_Support": TechnicalSignalDef("MA50지지", 1.4, BUCKET_PULLBACK_REENTRY),
    "Pullback_123_Bull": TechnicalSignalDef("Pullback 123 Bull", 2.0, BUCKET_PULLBACK_REENTRY),
    "NonADX_123_Bull": TechnicalSignalDef("NonADX 123 Bull", 1.8, BUCKET_PULLBACK_REENTRY),
    "New_52W_High": TechnicalSignalDef("52주신고가", 2.0, BUCKET_LEADER),
    "New_52W_Closing_High": TechnicalSignalDef("52주종가신고", 1.8, BUCKET_LEADER),
    "CS_Ultimate_Buy": TechnicalSignalDef("CS Ultimate Buy", 3.5, BUCKET_MIXED),
    "CS_Triple_Confirm_Buy": TechnicalSignalDef("CS Triple Confirm", 3.2, BUCKET_TREND_TURN),
    "CS_Breakout_Momentum_Buy": TechnicalSignalDef("CS Breakout Momentum", 3.0, BUCKET_SQUEEZE_BREAKOUT),
    "CS_Squeeze_Breakout_Buy": TechnicalSignalDef("CS Squeeze Breakout", 3.0, BUCKET_SQUEEZE_BREAKOUT),
    "CS_Breakout_Confirm_Buy": TechnicalSignalDef("CS Breakout Confirm", 3.0, BUCKET_SQUEEZE_BREAKOUT),
    "CS_Ichimoku_Breakout_Buy": TechnicalSignalDef("CS Ichimoku Breakout", 2.8, BUCKET_SQUEEZE_BREAKOUT),
    "CS_Institutional_Accumulation": TechnicalSignalDef("CS 기관매집", 3.0, BUCKET_ACCUMULATION),
    "CS_Divergence_Confluence_Buy": TechnicalSignalDef("CS 다이버전스", 2.8, BUCKET_REVERSAL_EARLY),
    "CS_Reversal_Cluster_Buy": TechnicalSignalDef("CS 반전클러스터", 3.2, BUCKET_REVERSAL_EARLY),
    "CS_Trend_Pullback_Buy": TechnicalSignalDef("CS 추세눌림", 2.8, BUCKET_PULLBACK_REENTRY),
    "CS_Trend_Continuation_Buy": TechnicalSignalDef("CS 추세지속", 2.6, BUCKET_PULLBACK_REENTRY),
    "CS_MA_Confluence_Buy": TechnicalSignalDef("CS MA컨플루언스", 2.4, BUCKET_PULLBACK_REENTRY),
    "CS_Cooper_Setup_Buy": TechnicalSignalDef("CS Cooper", 2.4, BUCKET_SQUEEZE_BREAKOUT),
    "CS_Volume_Climax_Rev_Buy": TechnicalSignalDef("CS 거래량반전", 2.6, BUCKET_ACCUMULATION),
    "CS_Oversold_Bounce_Buy": TechnicalSignalDef("CS 과매도반등", 2.0, BUCKET_REVERSAL_EARLY),
    "CS_Momentum_Accel_Buy": TechnicalSignalDef("CS 모멘텀가속", 2.2, BUCKET_TREND_TURN),
    "CS_Structure_Support_Buy": TechnicalSignalDef("CS 구조지지", 1.8, BUCKET_PULLBACK_REENTRY),
    "CS_Bottom_Fishing_Buy": TechnicalSignalDef("CS 바닥낚시", 2.4, BUCKET_REVERSAL_EARLY),
    "CS_Triple_Oversold_Reversal": TechnicalSignalDef("CS 과매도반전", 2.2, BUCKET_REVERSAL_EARLY),
    "CS_Capitulation_Bottom": TechnicalSignalDef("CS 투매바닥", 2.6, BUCKET_REVERSAL_EARLY),
    "CS_VuManChu_Squeeze_Buy": TechnicalSignalDef("CS VMC Squeeze", 2.5, BUCKET_SQUEEZE_BREAKOUT),
}

HARD_SELL_SIGNAL_KEYS = {
    "System_Turn_Bear",
    "Trend_Inflection_Bear",
    "UTBot_Sell",
    "Hull_Turn_Bear",
}

RISK_SELL_SIGNAL_KEYS = {
    "DMI_Cross_Bear": "dmi_bear",
    "MACD_Zero_Cross_Sell": "macd_zero_sell",
    "MACD_Cross_Sell": "macd_sell",
    "TK_Cross_Bear": "tk_bear",
    "Kumo_Breakout_Bear": "kumo_bear",
}


def _ticker(row: Mapping[str, Any]) -> str:
    return str(row.get("ticker") or "").strip().upper()


def _unique_append(items: list[str], value: str) -> None:
    text = str(value or "").strip()
    if text and text not in items:
        items.append(text)


def _optional_number(row: Mapping[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = row.get(key)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if number == number:
            return number
    return None


def _has_number(row: Mapping[str, Any], *keys: str) -> bool:
    return _optional_number(row, *keys) is not None


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


def _is_recent_item(item: Mapping[str, Any], target_date: date) -> bool:
    days_raw = item.get("days_ago")
    if days_raw is not None:
        days = int(safe_float(days_raw, default=999.0))
        return 0 <= days <= TECHNICAL_BUY_RECENT_WINDOW
    item_date = parse_iso_date(item.get("date"))
    if item_date is None:
        return True
    days = (target_date - item_date).days
    return 0 <= days <= TECHNICAL_BUY_RECENT_WINDOW


def _recent_date_field(row: Mapping[str, Any], key: str, target_date: date) -> bool:
    item_date = parse_iso_date(row.get(key))
    if item_date is None:
        return False
    days = (target_date - item_date).days
    return 0 <= days <= TECHNICAL_BUY_RECENT_WINDOW


def _has_latest_bar(row: Mapping[str, Any], target_date: date) -> bool:
    latest_bar_date = parse_iso_date(row.get("latest_bar_date"))
    return latest_bar_date is None or latest_bar_date == target_date


def _add_signal_hit(
    hits: dict[str, TechnicalSignalDef],
    key: str,
    *,
    label: str | None = None,
    score: float | None = None,
    bucket: str | None = None,
) -> None:
    definition = SIGNAL_DEFS.get(key)
    if definition is None and label and score is not None and bucket:
        definition = TechnicalSignalDef(label, score, bucket)
    if definition is None:
        return
    if key not in hits:
        hits[key] = definition


def _detected_signal_hits(row: Mapping[str, Any], target_date: date) -> tuple[dict[str, TechnicalSignalDef], list[str], list[str]]:
    hits: dict[str, TechnicalSignalDef] = {}
    hard_sells: list[str] = []
    risk_sells: list[str] = []

    for item in _parse_detected_signals(row.get("detected_signals")):
        if not _is_recent_item(item, target_date):
            continue
        key = str(item.get("key") or "").strip()
        if not key:
            continue
        direction = str(item.get("dir") or item.get("direction") or "").strip().lower()
        if key in HARD_SELL_SIGNAL_KEYS:
            _unique_append(hard_sells, key)
            continue
        risk_tag = RISK_SELL_SIGNAL_KEYS.get(key)
        if risk_tag:
            _unique_append(risk_sells, risk_tag)
            continue
        if key in SIGNAL_DEFS and direction != "sell":
            _add_signal_hit(hits, key)

    return hits, hard_sells, risk_sells


def _row_derived_hits(row: Mapping[str, Any], target_date: date, hits: dict[str, TechnicalSignalDef]) -> None:
    if is_truthy(row.get("latest_session_utbot_buy_turn")) or _recent_date_field(row, "utbot_buy_last_date", target_date) or is_truthy(row.get("utbot_buy_recent")):
        _add_signal_hit(hits, "UTBot_Buy")
    if is_truthy(row.get("latest_session_hull_buy_turn")) or _recent_date_field(row, "hull_turn_bull_last_date", target_date) or is_truthy(row.get("hull_turn_bull_recent")):
        _add_signal_hit(hits, "Hull_Turn_Bull")
    if is_truthy(row.get("system_turn_bull_recent")):
        _add_signal_hit(hits, "System_Turn_Bull")
    if is_truthy(row.get("trend_inflection_bull_recent")):
        _add_signal_hit(hits, "Trend_Inflection_Bull")

    direct_bool_keys = (
        "TK_Cross_Bull",
        "DMI_Cross_Bull",
        "ADX_New_Uptrend",
        "MACD_Cross_Buy",
        "MACD_Zero_Cross_Buy",
        "StochRSI_Cross_Buy",
        "Stoch_Oversold",
        "Green_Dot_T1",
        "Green_Dot_T2",
        "Gold_Dot",
        "Bull_Divergence",
        "RSI_Bull_Divergence",
        "OBV_Div_Buy",
        "MF_Bull_Div",
        "CMF_Bull",
        "MF_Cross_Bull",
        "MF_Accel_Up",
        "Squeeze_Fire_Buy",
        "BB_Squeeze_End_Bull",
        "BB_Upper_Break",
        "Kumo_Breakout_Bull",
        "EMA_Pullback_Buy",
        "MA20_Support",
        "MA50_Support",
        "Pullback_123_Bull",
        "NonADX_123_Bull",
        "Volume_Climax_Buy",
        "NR7",
        "NR7_2",
        "Calm_After_Storm",
        "Morning_Star",
        "Hammer",
        "Bullish_Engulfing",
        "Outside_Bullish",
    )
    for key in direct_bool_keys:
        if is_truthy(row.get(key)) or is_truthy(row.get(key.lower())):
            _add_signal_hit(hits, key)

    if is_truthy(row.get("pocket_pivot_candidate")) or is_truthy(row.get("pocket_pivot_recent")):
        _add_signal_hit(hits, "Pocket_Pivot")
    if is_truthy(row.get("volume_surge")) or safe_float(row.get("volume_ratio_20", 0.0)) >= 2.0:
        _add_signal_hit(hits, "Volume_Surge")
    if is_truthy(row.get("volume_climax_flag")) and safe_float(row.get("chg", 0.0)) >= 0.0:
        _add_signal_hit(hits, "Volume_Climax_Buy")
    if is_truthy(row.get("new_52w_high")) and _has_latest_bar(row, target_date):
        _add_signal_hit(hits, "New_52W_High")
    if is_truthy(row.get("new_52w_closing_high")) and _has_latest_bar(row, target_date):
        _add_signal_hit(hits, "New_52W_Closing_High")
    if is_truthy(row.get("pullback_reentry")):
        _add_signal_hit(hits, "Pullback_123_Bull")
    if is_truthy(row.get("pullback_ready")):
        _add_signal_hit(hits, "EMA_Pullback_Buy")
    if is_truthy(row.get("first_close_above_ma20_after_5bars")):
        _add_signal_hit(hits, "MA20_Support")
    if is_truthy(row.get("nr7_flag")):
        _add_signal_hit(hits, "NR7")
    if is_truthy(row.get("atr_contracting")) or is_truthy(row.get("inside_day_flag")):
        _add_signal_hit(hits, "Calm_After_Storm")
    if safe_float(row.get("cmf", 0.0)) >= 0.10:
        _add_signal_hit(hits, "CMF_Bull")


def _hard_exclusion_reason(row: Mapping[str, Any], target_date: date, hard_sells: list[str]) -> str:
    if same_session_sell_turn(row, target_date) or is_truthy(row.get("same_session_sell_turn")):
        return "recent_sell_turn"
    if is_truthy(row.get("utbot_sell_recent")) or _recent_date_field(row, "utbot_sell_last_date", target_date):
        return "recent_sell_turn"
    if is_truthy(row.get("hull_turn_bear_recent")) or _recent_date_field(row, "hull_turn_bear_last_date", target_date):
        return "recent_sell_turn"
    if hard_sells:
        return "recent_sell_turn"
    if is_truthy(row.get("thin_trade_risk")):
        return "thin_trade_risk"
    if is_truthy(row.get("bearish_gap_failure")) or is_truthy(row.get("bearish_gap_failure__2")):
        return "bearish_gap_failure"
    if safe_float(row.get("multi_sell", 0.0)) >= 2.0:
        return "multi_sell"
    if _has_number(row, "dollar_volume_20") and safe_float(row.get("dollar_volume_20"), 0.0) < TECHNICAL_BUY_MIN_DOLLAR_VOLUME_20:
        return "low_dollar_volume"
    return ""


def _risk_flags_and_penalty(row: Mapping[str, Any], risk_sells: list[str]) -> tuple[list[str], float]:
    flags: list[str] = []
    penalty = 0.0
    for tag in risk_sells:
        _unique_append(flags, tag)
        penalty -= 1.0

    if safe_float(row.get("rsi", row.get("RSI", 0.0))) >= 75.0:
        _unique_append(flags, "rsi_hot")
        penalty -= 1.2
    if safe_float(row.get("ma20_dist_pct", row.get("dist_sma20_pct", 0.0))) >= 18.0:
        _unique_append(flags, "ma20_extended")
        penalty -= 1.4
    if safe_float(row.get("chg", 0.0)) >= 12.0:
        _unique_append(flags, "extended_day")
        penalty -= 1.4
    elif safe_float(row.get("chg", 0.0)) >= 8.0:
        _unique_append(flags, "day_chase")
        penalty -= 0.7
    if safe_float(row.get("chg_5d", 0.0)) >= 25.0:
        _unique_append(flags, "extended_5d")
        penalty -= 1.8
    elif safe_float(row.get("chg_5d", 0.0)) >= 15.0:
        _unique_append(flags, "five_day_chase")
        penalty -= 0.9
    if _has_number(row, "volume_ratio_20") and safe_float(row.get("volume_ratio_20"), 0.0) < 0.8:
        _unique_append(flags, "low_volume")
        penalty -= 0.8
    if is_truthy(row.get("gap_risk_2pct")) or is_truthy(row.get("gap_risk_atr")):
        _unique_append(flags, "gap_chase_risk")
        penalty -= 0.7
    if str(row.get("strategy_conflict_level") or "").strip().upper() == "HIGH":
        _unique_append(flags, "high_conflict")
        penalty -= 1.5
    if is_truthy(row.get("hma_ema_short_entry")) or is_truthy(row.get("hma25_ema25_cross_bear")):
        _unique_append(flags, "short_setup_conflict")
        penalty -= 1.3
    return flags, penalty


def _cluster_bonus(signal_count: int, bucket_count: int) -> float:
    bonus = 0.0
    if signal_count >= 3:
        bonus += 1.0
    if signal_count >= 5:
        bonus += 1.0
    if bucket_count >= 2:
        bonus += 0.7
    if bucket_count >= 3:
        bonus += 0.5
    return bonus


def _volume_bonus(row: Mapping[str, Any]) -> float:
    ratio = safe_float(row.get("volume_ratio_20", 0.0))
    if ratio >= 2.0:
        return 1.5
    if ratio >= 1.5:
        return 1.0
    if ratio >= 1.2:
        return 0.5
    if _has_number(row, "volume_ratio_20") and ratio < 0.8:
        return -0.8
    return 0.0


def _flow_bonus(row: Mapping[str, Any], hits: Mapping[str, TechnicalSignalDef]) -> float:
    bonus = 0.0
    if safe_float(row.get("cmf", 0.0)) >= 0.10:
        bonus += 0.5
    elif safe_float(row.get("cmf", 0.0)) > 0.0:
        bonus += 0.3
    if safe_float(row.get("obv_slope", 0.0)) >= 0.3:
        bonus += 0.5
    if any(key.startswith("MF_") or key in {"OBV_Div_Buy", "Pocket_Pivot", "Volume_Climax_Buy"} for key in hits):
        bonus += 0.5
    return min(bonus, 1.5)


def _bucket_from_scores(bucket_scores: Mapping[str, float]) -> str:
    if not bucket_scores:
        return ""
    ordered = sorted(bucket_scores.items(), key=lambda item: (-item[1], item[0]))
    if len(ordered) >= 2 and ordered[0][1] - ordered[1][1] <= 1.0:
        return BUCKET_MIXED
    top_bucket = ordered[0][0]
    return BUCKET_MIXED if top_bucket == BUCKET_MIXED else top_bucket


def _hit_labels(hits: Mapping[str, TechnicalSignalDef]) -> list[str]:
    return [definition.label for _, definition in sorted(hits.items(), key=lambda item: (-item[1].score, item[1].label))]


def _reason_text(bucket: str, hits: list[str], volume_ratio: float | None) -> str:
    parts: list[str] = []
    if bucket:
        parts.append(bucket)
    if hits:
        parts.append(" + ".join(hits[:3]))
    if volume_ratio is not None and volume_ratio >= 1.2:
        parts.append(f"Vol20 x{volume_ratio:.2f}")
    return " / ".join(parts) if parts else "-"


def _score_row(row: Mapping[str, Any], *, target_date: date) -> TechnicalBuyCandidate | None:
    ticker = _ticker(row)
    if not ticker:
        return None

    hits, hard_sells, risk_sells = _detected_signal_hits(row, target_date)
    _row_derived_hits(row, target_date, hits)

    hard_reason = _hard_exclusion_reason(row, target_date, hard_sells)
    if hard_reason:
        return None

    signal_count = len(hits)
    if signal_count < TECHNICAL_BUY_MIN_SIGNAL_COUNT:
        return None

    bucket_scores: dict[str, float] = {}
    for definition in hits.values():
        bucket_scores[definition.bucket] = bucket_scores.get(definition.bucket, 0.0) + definition.score

    risk_flags, penalty = _risk_flags_and_penalty(row, risk_sells)
    score = sum(definition.score for definition in hits.values())
    score += _cluster_bonus(signal_count, len(bucket_scores))
    score += _volume_bonus(row)
    score += _flow_bonus(row, hits)
    score += penalty
    score = round(score, 1)
    if score < TECHNICAL_BUY_MIN_SCORE:
        return None

    bucket = _bucket_from_scores(bucket_scores)
    labels = _hit_labels(hits)
    volume_ratio = _optional_number(row, "volume_ratio_20")
    risk_display = risk_flags if risk_flags else []

    return TechnicalBuyCandidate(
        ticker=ticker,
        technical_buy_score=score,
        signal_count=signal_count,
        hits=labels,
        bucket=bucket,
        reason=_reason_text(bucket, labels, volume_ratio),
        risk_flags=risk_display,
        price=_optional_number(row, "price"),
        chg_value=_optional_number(row, "chg_value"),
        chg_pct=_optional_number(row, "chg"),
        volume_ratio_20=volume_ratio,
        atr_pct=_optional_number(row, "atr_pct"),
        source_flags={
            "technical_buy_score": score,
            "technical_buy_signal_count": signal_count,
            "technical_buy_hits": labels,
            "technical_buy_bucket": bucket,
            "technical_buy_reason": _reason_text(bucket, labels, volume_ratio),
            "technical_buy_risk_flags": risk_display,
            "technical_buy_signal_keys": list(hits.keys()),
            "bucket_scores": dict(bucket_scores),
            "risk_penalty": round(penalty, 1),
            "volume_bonus": round(_volume_bonus(row), 1),
            "flow_bonus": round(_flow_bonus(row, hits), 1),
        },
    )


def _candidate_sort_key(candidate: TechnicalBuyCandidate) -> tuple[float, float, float, str]:
    return (
        -safe_float(candidate.technical_buy_score),
        -safe_float(candidate.signal_count),
        -safe_float(candidate.volume_ratio_20),
        str(candidate.ticker),
    )


def rank_technical_buy_candidates(
    rows: Iterable[Mapping[str, Any]],
    *,
    target_date: date,
    limit: int | None = None,
) -> list[TechnicalBuyCandidate]:
    best_by_ticker: dict[str, TechnicalBuyCandidate] = {}
    for raw_row in rows or []:
        candidate = _score_row(raw_row or {}, target_date=target_date)
        if candidate is None:
            continue
        existing = best_by_ticker.get(candidate.ticker)
        if existing is None or _candidate_sort_key(candidate) < _candidate_sort_key(existing):
            best_by_ticker[candidate.ticker] = candidate

    ranked = sorted(best_by_ticker.values(), key=_candidate_sort_key)
    selected = ranked if limit is None else ranked[:limit]
    for rank, candidate in enumerate(selected, start=1):
        candidate.rank = rank
    return selected


def _decorate_row_with_candidate(row: Mapping[str, Any], candidate: TechnicalBuyCandidate) -> dict[str, Any]:
    row_dict = dict(row or {})
    row_dict["ticker"] = candidate.ticker
    row_dict["technical_buy_score"] = f"{candidate.technical_buy_score:.1f}"
    row_dict["technical_buy_signal_count"] = candidate.signal_count
    row_dict["technical_buy_hits"] = "+".join(candidate.hits)
    row_dict["technical_buy_bucket"] = candidate.bucket
    row_dict["technical_buy_reason"] = candidate.reason
    row_dict["technical_buy_risk_flags"] = "+".join(candidate.risk_flags) if candidate.risk_flags else "특이사항 없음"
    row_dict["technical_buy_rank"] = candidate.rank
    return row_dict


def select_technical_buy_rows(
    rows: Iterable[Mapping[str, Any]],
    *,
    target_date: date,
    limit: int = TECHNICAL_BUY_CLUSTER_LIMIT,
) -> list[dict[str, Any]]:
    row_list = [dict(row or {}) for row in rows or []]
    candidates = rank_technical_buy_candidates(row_list, target_date=target_date, limit=limit)
    by_ticker = {candidate.ticker: candidate for candidate in candidates}
    source_by_ticker = {_ticker(row): row for row in row_list if _ticker(row)}
    return [
        _decorate_row_with_candidate(source_by_ticker.get(candidate.ticker, {"ticker": candidate.ticker}), candidate)
        for candidate in candidates
    ]


def annotate_rows_with_technical_buy(
    rows: Iterable[Mapping[str, Any]],
    *,
    target_date: date,
) -> list[dict[str, Any]]:
    row_list = [dict(row or {}) for row in rows or []]
    candidates = rank_technical_buy_candidates(row_list, target_date=target_date, limit=None)
    by_ticker = {candidate.ticker: candidate for candidate in candidates}

    annotated: list[dict[str, Any]] = []
    for row in row_list:
        row_dict = dict(row or {})
        row_dict["technical_buy_score"] = ""
        row_dict["technical_buy_signal_count"] = ""
        row_dict["technical_buy_hits"] = ""
        row_dict["technical_buy_bucket"] = ""
        row_dict["technical_buy_reason"] = ""
        row_dict["technical_buy_risk_flags"] = ""
        candidate = by_ticker.get(_ticker(row_dict))
        if candidate is not None:
            row_dict.update(_decorate_row_with_candidate(row_dict, candidate))
        annotated.append(row_dict)
    return annotated
