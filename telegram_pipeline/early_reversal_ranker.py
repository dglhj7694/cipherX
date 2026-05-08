from __future__ import annotations

from datetime import date
from typing import Any, Iterable, Mapping

from .rankers import is_truthy, safe_float, same_session_sell_turn

EARLY_REVERSAL_KEY = "early_reversal"
EARLY_REVERSAL_LIMIT = 20
EARLY_REVERSAL_SECTION_TITLE = f"초기 반전 포착 Top {EARLY_REVERSAL_LIMIT}"
EARLY_REVERSAL_QUALITY_FLOOR = (
    "downtrend/box context + reversal trigger/strong prep + volume confirmation + no hard risk"
)

PHASE_RANK: dict[str, int] = {
    "PREP": 1,
    "TRIGGERED": 2,
    "CONFIRMED": 3,
}


def _unique_append(values: list[str], value: str) -> None:
    if value and value not in values:
        values.append(value)


def _ticker(row: Mapping[str, Any]) -> str:
    return str(row.get("ticker") or "").strip().upper()


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


def _hard_excluded(row: Mapping[str, Any], target_date: date) -> bool:
    if same_session_sell_turn(row, target_date) or is_truthy(row.get("same_session_sell_turn")):
        return True
    if is_truthy(row.get("thin_trade_risk")):
        return True
    if is_truthy(row.get("bearish_gap_failure")):
        return True
    if safe_float(row.get("multi_sell", 0.0)) >= 2.0:
        return True
    if str(row.get("strategy_conflict_level") or "").strip().upper() == "HIGH":
        return True
    if safe_float(row.get("volume_ratio_20", 0.0)) < 0.8:
        return True
    return False


def _context_score(row: Mapping[str, Any], tags: list[str]) -> tuple[float, int, int]:
    score = 0.0
    weak_count = 0
    compression_count = 0

    ret20 = _optional_number(row, "ret20_pct")
    ret60 = _optional_number(row, "ret60_pct")
    if ret60 is not None and ret60 < 0.0:
        score += 5.0
        weak_count += 1
        _unique_append(tags, "RET60약세")
    if safe_float(row.get("dist_sma50_pct", 0.0)) < 0.0:
        score += 5.0
        weak_count += 1
        _unique_append(tags, "MA50아래")
    if safe_float(row.get("drawdown_from_52w_high_pct", 0.0)) <= -15.0:
        score += 6.0
        weak_count += 1
        _unique_append(tags, "52W낙폭")
    if ret20 is not None and ret60 is not None and ret20 < 0.0 and ret60 < 0.0:
        score += 4.0
        weak_count += 1
        _unique_append(tags, "RET20/60약세")

    if is_truthy(row.get("atr_contracting")):
        score += 4.0
        compression_count += 1
        _unique_append(tags, "ATR수축")
    if is_truthy(row.get("nr7_flag")):
        score += 3.0
        compression_count += 1
        _unique_append(tags, "NR7")
    if is_truthy(row.get("inside_day_flag")):
        score += 3.0
        compression_count += 1
        _unique_append(tags, "InsideDay")
    if is_truthy(row.get("three_weeks_tight")):
        score += 4.0
        compression_count += 1
        _unique_append(tags, "3주타이트")
    if safe_float(row.get("volume_dry_up_score", 0.0)) >= 10.0:
        compression_count += 1
        _unique_append(tags, "거래량건조")

    return min(score, 20.0), weak_count, compression_count


def _compression_score(row: Mapping[str, Any], tags: list[str]) -> float:
    score = 0.0
    bb_percent_b = safe_float(row.get("bb_percent_b", 0.0))
    if 0.35 <= bb_percent_b <= 0.85:
        score += 4.0
        _unique_append(tags, "BB압축")
    if safe_float(row.get("volume_dry_up_score", 0.0)) >= 10.0:
        score += 4.0
        _unique_append(tags, "거래량건조")
    if is_truthy(row.get("first_higher_low_pivot2")):
        score += 5.0
        _unique_append(tags, "HigherLow")
    if is_truthy(row.get("tight_close_near_high_3d")):
        score += 4.0
        _unique_append(tags, "고가근접종가")
    dd20 = _optional_number(row, "drawdown_from_20d_high_pct")
    if dd20 is not None and -8.0 <= dd20 <= -1.0:
        score += 3.0
        _unique_append(tags, "얕은바닥")
    return min(score, 15.0)


def _trigger_score(row: Mapping[str, Any], tags: list[str]) -> tuple[float, bool]:
    score = 0.0
    major_trigger = False
    if is_truthy(row.get("latest_session_hull_buy_turn")):
        score += 10.0
        major_trigger = True
        _unique_append(tags, "HULL전환")
    if is_truthy(row.get("latest_session_utbot_buy_turn")):
        score += 10.0
        major_trigger = True
        _unique_append(tags, "UTBot전환")
    if safe_float(row.get("days_since_hull_turn_bull", 999.0)) <= 5.0:
        score += 6.0
        _unique_append(tags, "HULL5일내")
    if safe_float(row.get("days_since_utbot_buy", 999.0)) <= 5.0:
        score += 6.0
        _unique_append(tags, "UTBot5일내")
    if is_truthy(row.get("first_close_above_ma20_after_5bars")):
        score += 10.0
        major_trigger = True
        _unique_append(tags, "MA20회복")
    if is_truthy(row.get("first_higher_low_pivot2")):
        score += 6.0
        _unique_append(tags, "HigherLow")
    if is_truthy(row.get("first_higher_high_pivot2")):
        score += 6.0
        _unique_append(tags, "HigherHigh")
    return min(score, 30.0), major_trigger


def _volume_score(row: Mapping[str, Any], tags: list[str]) -> tuple[float, bool]:
    score = 0.0
    confirmed = False
    volume_ratio = safe_float(row.get("volume_ratio_20", 0.0))
    if volume_ratio >= 1.15:
        score += 6.0
        confirmed = True
        _unique_append(tags, "거래량증가")
    if volume_ratio >= 1.5:
        score += 4.0
        _unique_append(tags, "거래량강화")
    if safe_float(row.get("volume_expansion_score", 0.0)) >= 25.0:
        score += 5.0
        confirmed = True
        _unique_append(tags, "거래확장")
    if safe_float(row.get("obv_slope", 0.0)) > 0.0:
        score += 4.0
        confirmed = True
        _unique_append(tags, "OBV+")
    if safe_float(row.get("cmf", 0.0)) > 0.0:
        score += 4.0
        confirmed = True
        _unique_append(tags, "CMF+")
    if is_truthy(row.get("volume_bullish")):
        score += 3.0
        _unique_append(tags, "수급양호")
    return min(score, 20.0), confirmed


def _location_score_and_risks(row: Mapping[str, Any], risk_flags: list[str]) -> tuple[float, float]:
    score = 0.0
    penalty = 0.0
    chg_pct = safe_float(row.get("chg", 0.0))
    chg_5d = safe_float(row.get("chg_5d", 0.0))
    ma20_dist = safe_float(row.get("ma20_dist_pct", row.get("dist_sma20_pct", 0.0)))
    zscore20 = safe_float(row.get("zscore20", 0.0))
    bb_percent_b = safe_float(row.get("bb_percent_b", 0.0))

    if -3.0 <= chg_5d <= 10.0:
        score += 5.0
    if -3.0 <= ma20_dist <= 8.0:
        score += 5.0
    if zscore20 <= 1.8:
        score += 3.0
    if bb_percent_b <= 1.05:
        score += 2.0

    if chg_5d > 15.0:
        penalty -= 8.0
        _unique_append(risk_flags, "late_chase")
    if ma20_dist > 12.0:
        penalty -= 8.0
        _unique_append(risk_flags, "ma20_extended")
    if zscore20 > 2.2:
        penalty -= 8.0
        _unique_append(risk_flags, "zscore_hot")
    if bb_percent_b > 1.15:
        penalty -= 6.0
        _unique_append(risk_flags, "bb_overextended")
    if chg_pct < 0.0:
        penalty -= 6.0
        _unique_append(risk_flags, "negative_day")
    if chg_5d > 25.0 or ma20_dist > 25.0 or zscore20 > 3.2 or bb_percent_b > 1.35:
        penalty -= 15.0
        _unique_append(risk_flags, "too_extended")
    return min(score, 15.0), penalty


def _reversal_type(weak_count: int, compression_count: int) -> str:
    if weak_count > 0 and compression_count > 0:
        return "MIXED_REVERSAL"
    if weak_count > 0:
        return "DOWN_TREND_REVERSAL"
    return "BOX_BREAKOUT"


def _reversal_phase(row: Mapping[str, Any], *, major_trigger: bool, volume_confirmed: bool) -> str:
    breakout_near = safe_float(row.get("breakout_dist_20d_high_pct", -999.0)) >= -3.0
    structure_confirmed = bool(
        is_truthy(row.get("first_higher_low_pivot2"))
        or is_truthy(row.get("first_higher_high_pivot2"))
        or breakout_near
    )
    if major_trigger and structure_confirmed and safe_float(row.get("volume_ratio_20", 0.0)) >= 1.15:
        return "CONFIRMED"
    if major_trigger and volume_confirmed:
        return "TRIGGERED"
    return "PREP"


def _entry_type(row: Mapping[str, Any], phase: str, reversal_type: str) -> str:
    if phase == "CONFIRMED":
        return "confirmed_reversal_watch"
    if reversal_type == "BOX_BREAKOUT":
        return "breakout_reversal_watch"
    if phase == "TRIGGERED":
        return "reversal_trigger_watch"
    return "early_reversal_watch"


def _confirmation_text(row: Mapping[str, Any]) -> str:
    breakout = _optional_number(row, "breakout_dist_20d_high_pct")
    ma20_dist = _optional_number(row, "ma20_dist_pct", "dist_sma20_pct")
    parts: list[str] = []
    if breakout is not None:
        parts.append(f"20일고점 {breakout:+.1f}%")
    if ma20_dist is not None:
        parts.append(f"MA20 {ma20_dist:+.1f}% 지지")
    return " / ".join(parts) if parts else "20일고점/MA20 지지"


def _breakout_proximity_score(row: Mapping[str, Any]) -> float:
    breakout = _optional_number(row, "breakout_dist_20d_high_pct")
    if breakout is None:
        return 0.0
    distance = abs(breakout)
    if -3.0 <= breakout <= 3.0:
        return 10.0 - min(distance, 3.0)
    if 3.0 < breakout <= 8.0:
        return max(0.0, 5.0 - (breakout - 3.0))
    return max(0.0, 4.0 - min(distance, 20.0) / 5.0)


def _display_reason(tags: list[str]) -> str:
    priority = (
        "MA20회복",
        "HULL전환",
        "UTBot전환",
        "거래량증가",
        "거래확장",
        "OBV+",
        "CMF+",
        "HigherLow",
        "HigherHigh",
        "20일고점근접",
        "ATR수축",
        "NR7",
        "InsideDay",
        "BB압축",
    )
    ordered: list[str] = []
    for tag in priority:
        if tag in tags:
            _unique_append(ordered, tag)
    for tag in tags:
        _unique_append(ordered, tag)
    return "+".join(ordered[:8]) if ordered else "-"


def _decorate_row(row: Mapping[str, Any], *, target_date: date) -> dict[str, Any] | None:
    row_dict = dict(row or {})
    ticker = _ticker(row_dict)
    if not ticker or _hard_excluded(row_dict, target_date):
        return None

    reason_tags: list[str] = []
    risk_flags: list[str] = []
    context_score, weak_count, compression_count = _context_score(row_dict, reason_tags)
    context_ok = weak_count >= 2 or compression_count >= 2 or (weak_count >= 1 and compression_count >= 1)
    if not context_ok:
        return None

    compression_score = _compression_score(row_dict, reason_tags)
    trigger_score, major_trigger = _trigger_score(row_dict, reason_tags)
    volume_score, volume_confirmed = _volume_score(row_dict, reason_tags)
    if not volume_confirmed:
        return None

    location_score, location_penalty = _location_score_and_risks(row_dict, risk_flags)
    breakout_proximity_score = _breakout_proximity_score(row_dict)
    strong_prep = compression_score >= 12.0 and volume_score >= 14.0 and breakout_proximity_score >= 7.0
    prep_bonus = 0.0
    if not major_trigger and strong_prep:
        prep_bonus = 15.0
        _unique_append(reason_tags, "20일고점근접")
        _unique_append(reason_tags, "강한PREP")
    if not major_trigger and not strong_prep:
        return None

    phase = _reversal_phase(row_dict, major_trigger=major_trigger, volume_confirmed=volume_confirmed)
    if phase == "PREP":
        _unique_append(risk_flags, "watch_only_prep")

    if not reason_tags or (trigger_score <= 0.0 and phase != "PREP"):
        _unique_append(risk_flags, "fake_rebound_risk")
        location_penalty -= 10.0

    score = round(context_score + compression_score + trigger_score + volume_score + location_score + prep_bonus + max(location_penalty, -45.0), 1)
    if phase == "PREP" and score < 80.0:
        return None
    if score < 45.0:
        return None

    row_dict["ticker"] = ticker
    row_dict["early_reversal_score"] = score
    row_dict["reversal_type"] = _reversal_type(weak_count, compression_count)
    row_dict["reversal_phase"] = phase
    row_dict["entry_type"] = _entry_type(row_dict, phase, row_dict["reversal_type"])
    row_dict["reversal_reason"] = _display_reason(reason_tags)
    row_dict["reversal_tags"] = reason_tags
    row_dict["reversal_risk_flags"] = risk_flags
    row_dict["reversal_confirm"] = _confirmation_text(row_dict)
    row_dict["reversal_location_score"] = round(location_score, 1)
    row_dict["reversal_volume_score"] = round(volume_score, 1)
    row_dict["reversal_breakout_proximity_score"] = round(breakout_proximity_score, 1)
    row_dict["reversal_phase_rank"] = PHASE_RANK.get(phase, 0)
    return row_dict


def _sort_key(row: Mapping[str, Any]) -> tuple[float, float, float, float, float, str]:
    return (
        -safe_float(row.get("early_reversal_score", 0.0)),
        -safe_float(row.get("reversal_phase_rank", 0.0)),
        -safe_float(row.get("reversal_location_score", 0.0)),
        -safe_float(row.get("reversal_volume_score", 0.0)),
        -safe_float(row.get("reversal_breakout_proximity_score", 0.0)),
        str(row.get("ticker", "")),
    )


def rank_early_reversal_candidates(rows: Iterable[Mapping[str, Any]], *, target_date: date) -> list[dict[str, Any]]:
    best_by_ticker: dict[str, dict[str, Any]] = {}
    for raw_row in rows or []:
        row = _decorate_row(raw_row, target_date=target_date)
        if not row:
            continue
        ticker = _ticker(row)
        existing = best_by_ticker.get(ticker)
        if existing is None or safe_float(row.get("early_reversal_score", 0.0)) > safe_float(existing.get("early_reversal_score", 0.0)):
            best_by_ticker[ticker] = row

    selected = list(best_by_ticker.values())
    selected.sort(key=_sort_key)
    return selected


def build_early_reversal_section(rows: Iterable[Mapping[str, Any]], *, target_date: date) -> list[dict[str, Any]]:
    confirmed = []
    triggered = []
    prep = []
    for row in rank_early_reversal_candidates(rows, target_date=target_date):
        phase = str(row.get("reversal_phase") or "")
        if phase == "CONFIRMED":
            confirmed.append(row)
        elif phase == "TRIGGERED":
            triggered.append(row)
        else:
            prep.append(row)

    combined: list[dict[str, Any]] = []
    seen: set[str] = set()
    for pool in (confirmed, triggered, prep):
        for row in pool:
            ticker = _ticker(row)
            if not ticker or ticker in seen:
                continue
            seen.add(ticker)
            combined.append(row)
            if len(combined) >= EARLY_REVERSAL_LIMIT:
                return sorted(combined, key=_sort_key)
    return sorted(combined, key=_sort_key)[:EARLY_REVERSAL_LIMIT]
