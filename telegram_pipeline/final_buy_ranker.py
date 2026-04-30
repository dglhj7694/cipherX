from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Iterable, Mapping

from .rankers import (
    is_truthy,
    safe_float,
    same_day_hull_buy_turn,
    same_day_utbot_buy_turn,
    same_session_sell_turn,
)
from .selectors import select_post_close_sections

QBS_BUY_NOW_KEY = "qbs_buy_now"
QBS_CHASE_WATCH_KEY = "qbs_chase_watch"
QBS_PULLBACK_WAIT_KEY = "qbs_pullback_wait"
QBS_OUTPUT_KEYS: tuple[str, ...] = (
    QBS_BUY_NOW_KEY,
    QBS_CHASE_WATCH_KEY,
    QBS_PULLBACK_WAIT_KEY,
)

BUCKET_BUY_NOW = "BUY_NOW"
BUCKET_CHASE_WATCH = "CHASE_WATCH"
BUCKET_PULLBACK_WAIT = "PULLBACK_WAIT"
BUCKET_EXCLUDE = "EXCLUDE"

QBS_BUY_NOW_LIMIT = 20
QBS_CHASE_WATCH_LIMIT = 10
QBS_PULLBACK_WAIT_LIMIT = 10
QBS_OUTPUT_LIMIT = QBS_BUY_NOW_LIMIT
QBS_OUTPUT_LIMITS: dict[str, int] = {
    QBS_BUY_NOW_KEY: QBS_BUY_NOW_LIMIT,
    QBS_CHASE_WATCH_KEY: QBS_CHASE_WATCH_LIMIT,
    QBS_PULLBACK_WAIT_KEY: QBS_PULLBACK_WAIT_LIMIT,
}
QBS_BUY_NOW_MIN = 50.0
QBS_CHASE_MIN = 40.0
QBS_PULLBACK_MIN = 25.0

QBS_SECTION_KEYS: tuple[str, ...] = (
    "final_top",
    "buy_turn",
    "pullback_reentry",
    "trend_continuation",
    "hma_ema_trend",
    "sell_turn",
    "gap_setup",
    "pocket_pivot",
    "five_day_top",
    "new_52w_high",
)

ROW_SOURCE_PRIORITY: tuple[str, ...] = (
    "final_top",
    "buy_turn",
    "trend_continuation",
    "hma_ema_trend",
    "pocket_pivot",
    "new_52w_high",
    "five_day_top",
    "pullback_reentry",
    "gap_setup",
    "sell_turn",
)

SECTION_SCORES: dict[str, float] = {
    "final_top": 20.0,
    "buy_turn": 18.0,
    "trend_continuation": 15.0,
    "hma_ema_trend": 12.0,
    "pocket_pivot": 12.0,
    "new_52w_high": 10.0,
    "five_day_top": 8.0,
    "pullback_reentry": 6.0,
    "gap_setup": 4.0,
}

SECTION_TAGS: dict[str, str] = {
    "final_top": "final",
    "buy_turn": "buy",
    "trend_continuation": "trend",
    "hma_ema_trend": "HMA",
    "pocket_pivot": "pocket",
    "new_52w_high": "52W",
    "five_day_top": "5D",
    "pullback_reentry": "pullback",
    "gap_setup": "gap",
}


@dataclass
class FinalBuyCandidate:
    ticker: str
    qbs_score: float
    bucket: str
    tags: list[str] = field(default_factory=list)
    chg_pct: float | None = None
    chg_value: float | None = None
    volume_ratio_20: float | None = None
    risk_flags: list[str] = field(default_factory=list)
    rank: int = 0
    price: float | None = None
    source_flags: dict[str, Any] = field(default_factory=dict)
    membership_count: int = 0
    entry_judgment: str = ""
    rr: float | None = None
    risk_judgment: str = ""


def _ticker(row: Mapping[str, Any]) -> str:
    return str(row.get("ticker") or "").strip().upper()


def _unique_append(items: list[str], value: str) -> None:
    text = str(value or "").strip()
    if text and text not in items:
        items.append(text)


def _optional_float(row: Mapping[str, Any], key: str) -> float | None:
    if row.get(key) is None:
        return None
    return safe_float(row.get(key))


def _row_number(row: Mapping[str, Any], *keys: str, default: float = 0.0) -> float:
    for key in keys:
        if row.get(key) is not None:
            return safe_float(row.get(key), default)
    return default


def _build_membership(section_rows: Mapping[str, Iterable[Mapping[str, Any]]]) -> tuple[dict[str, set[str]], dict[str, dict[str, dict[str, Any]]]]:
    membership: dict[str, set[str]] = {}
    rows_by_section: dict[str, dict[str, dict[str, Any]]] = {}

    for section_key in QBS_SECTION_KEYS:
        section_map: dict[str, dict[str, Any]] = {}
        for raw_row in section_rows.get(section_key) or []:
            row = dict(raw_row or {})
            ticker = _ticker(row)
            if not ticker or ticker in section_map:
                continue
            section_map[ticker] = row
            membership.setdefault(ticker, set()).add(section_key)
        rows_by_section[section_key] = section_map

    return membership, rows_by_section


def _canonical_row(ticker: str, rows_by_section: Mapping[str, Mapping[str, Mapping[str, Any]]]) -> dict[str, Any]:
    for section_key in ROW_SOURCE_PRIORITY:
        row = dict(rows_by_section.get(section_key, {}).get(ticker) or {})
        if row:
            return row
    return {"ticker": ticker}


def _section_tags(membership: set[str]) -> list[str]:
    tags: list[str] = []
    for section_key in ROW_SOURCE_PRIORITY:
        tag = SECTION_TAGS.get(section_key, "")
        if section_key in membership and tag:
            _unique_append(tags, tag)
    return tags


def _volume_score(volume_ratio: float) -> float:
    if volume_ratio >= 3.0:
        return 12.0
    if volume_ratio >= 2.0:
        return 10.0
    if volume_ratio >= 1.5:
        return 8.0
    if volume_ratio >= 1.2:
        return 5.0
    if volume_ratio >= 1.0:
        return 3.0
    if volume_ratio < 0.8:
        return -8.0
    return 0.0


def _quality_score(row: Mapping[str, Any]) -> float:
    score = 0.0
    final_entry_score = _row_number(row, "final_entry_score")
    if final_entry_score >= 90.0:
        score += 8.0
    elif final_entry_score >= 80.0:
        score += 6.0
    elif final_entry_score >= 70.0:
        score += 4.0

    scan_score = _row_number(row, "scan_score")
    if scan_score >= 150.0:
        score += 6.0
    elif scan_score >= 120.0:
        score += 4.0
    elif scan_score >= 100.0:
        score += 2.0

    if is_truthy(row.get("uptrend_persistent")):
        score += 6.0
    if is_truthy(row.get("bull_strength_recent")):
        score += 4.0

    rs_rank = _row_number(row, "rs_rank_vs_index")
    if rs_rank >= 80.0:
        score += 5.0
    elif rs_rank >= 70.0:
        score += 3.0

    adx = _row_number(row, "adx")
    if adx >= 25.0:
        score += 4.0
    elif adx >= 20.0:
        score += 2.0

    if is_truthy(row.get("low_conflict_bullish")):
        score += 3.0

    return score


def _buy_turn_score(row: Mapping[str, Any], target_date: date, tags: list[str]) -> float:
    utbot = same_day_utbot_buy_turn(row, target_date)
    hull = same_day_hull_buy_turn(row, target_date)
    if utbot and hull:
        _unique_append(tags, "UTBot+HULL")
        return 15.0
    if hull:
        _unique_append(tags, "HULL")
        return 10.0
    if utbot:
        _unique_append(tags, "UTBot")
        return 8.0
    return 0.0


def _hma_ema_score(row: Mapping[str, Any]) -> float:
    score = 0.0
    if is_truthy(row.get("hma_ema_long_entry")):
        score += 10.0
    elif is_truthy(row.get("hma_ema_long_aligned")):
        score += 6.0

    ema50_risk = _row_number(row, "hma_ema_risk_to_ema50_pct", "HMA_EMA_Risk_To_EMA50_Pct", default=999.0)
    if ema50_risk <= 5.0:
        score += 4.0
    elif ema50_risk <= 10.0:
        score += 2.0

    return score


def _confluence_score(membership: set[str]) -> float:
    score = 0.0
    combos = (
        ("final_top", "buy_turn", 10.0),
        ("final_top", "trend_continuation", 8.0),
        ("final_top", "new_52w_high", 8.0),
        ("final_top", "hma_ema_trend", 6.0),
        ("buy_turn", "hma_ema_trend", 6.0),
        ("buy_turn", "pocket_pivot", 7.0),
        ("buy_turn", "new_52w_high", 7.0),
        ("pocket_pivot", "new_52w_high", 5.0),
    )
    for left, right, value in combos:
        if left in membership and right in membership:
            score += value
    return score


def _risk_flags(row: Mapping[str, Any], membership: set[str], target_date: date) -> tuple[list[str], bool, float]:
    flags: list[str] = []
    penalty = 0.0

    if "sell_turn" in membership or same_session_sell_turn(row, target_date):
        _unique_append(flags, "sell_turn")
    if is_truthy(row.get("thin_trade_risk")):
        _unique_append(flags, "thin_trade")
    if is_truthy(row.get("bearish_gap_failure")):
        _unique_append(flags, "gap_failure")
    if str(row.get("strategy_conflict_level") or "").strip().upper() == "HIGH":
        _unique_append(flags, "high_conflict")
        penalty -= 10.0

    hard_exclude = any(flag in flags for flag in {"sell_turn", "thin_trade", "gap_failure"})

    chg_pct = _row_number(row, "chg")
    if chg_pct >= 20.0:
        _unique_append(flags, "extreme_chase")
        penalty -= 8.0
    elif chg_pct >= 12.0:
        _unique_append(flags, "chase_risk")
        penalty -= 4.0

    if chg_pct < 0.0:
        _unique_append(flags, "negative_day")
        penalty -= 6.0
    if chg_pct <= -3.0:
        _unique_append(flags, "weak_pullback")
        penalty -= 8.0

    volume_ratio = _row_number(row, "volume_ratio_20")
    if volume_ratio < 0.8:
        _unique_append(flags, "low_volume")

    if _row_number(row, "multi_sell") >= 2.0:
        _unique_append(flags, "multi_sell")
        penalty -= 10.0

    if "five_day_top" in membership and chg_pct < 0.0:
        _unique_append(flags, "five_day_fade")
        penalty -= 5.0
    if "hma_ema_trend" in membership and chg_pct < 0.0:
        _unique_append(flags, "hma_negative_day")
        penalty -= 5.0

    if is_truthy(row.get("hma_ema_short_entry")) or is_truthy(row.get("hma_ema_short_aligned")):
        _unique_append(flags, "hma_short_conflict")
        penalty -= 8.0

    return flags, hard_exclude, penalty


def _is_chase(row: Mapping[str, Any], membership: set[str]) -> bool:
    chg_pct = _row_number(row, "chg")
    chg_5d = _row_number(row, "chg_5d")
    return bool(
        chg_pct >= 12.0
        or ("new_52w_high" in membership and chg_pct >= 8.0)
        or ("five_day_top" in membership and chg_5d >= 20.0)
    )


def _classify_bucket(
    *,
    score: float,
    row: Mapping[str, Any],
    membership: set[str],
    risk_flags: list[str],
    hard_exclude: bool,
) -> str:
    if hard_exclude:
        return BUCKET_EXCLUDE

    chg_pct = _row_number(row, "chg")
    volume_ratio = _row_number(row, "volume_ratio_20")
    has_core = "final_top" in membership or "buy_turn" in membership
    chase = _is_chase(row, membership)
    has_hma_only = membership == {"hma_ema_trend"}

    if (
        score >= QBS_BUY_NOW_MIN
        and has_core
        and not chase
        and chg_pct >= 0.0
        and volume_ratio >= 1.0
        and "multi_sell" not in risk_flags
        and "high_conflict" not in risk_flags
        and not (has_hma_only and chg_pct < 0.0)
    ):
        return BUCKET_BUY_NOW

    if score >= QBS_CHASE_MIN and chase and chg_pct >= 0.0:
        return BUCKET_CHASE_WATCH

    if (
        score >= QBS_PULLBACK_MIN
        and "pullback_reentry" in membership
        and chg_pct > -3.0
        and not chase
    ):
        return BUCKET_PULLBACK_WAIT

    return ""


def _score_candidate(ticker: str, row: Mapping[str, Any], membership: set[str], target_date: date) -> FinalBuyCandidate:
    tags = _section_tags(membership)
    score = sum(SECTION_SCORES.get(section_key, 0.0) for section_key in membership)
    score += _buy_turn_score(row, target_date, tags)
    score += _hma_ema_score(row)
    score += _volume_score(_row_number(row, "volume_ratio_20"))
    score += _quality_score(row)
    score += _confluence_score(membership)

    risk_flags, hard_exclude, risk_penalty = _risk_flags(row, membership, target_date)
    score += risk_penalty
    score = round(score, 1)
    bucket = _classify_bucket(
        score=score,
        row=row,
        membership=membership,
        risk_flags=risk_flags,
        hard_exclude=hard_exclude,
    )

    return FinalBuyCandidate(
        ticker=ticker,
        qbs_score=score,
        bucket=bucket,
        tags=tags,
        chg_pct=_optional_float(row, "chg"),
        chg_value=_optional_float(row, "chg_value"),
        volume_ratio_20=_optional_float(row, "volume_ratio_20"),
        risk_flags=risk_flags,
        price=_optional_float(row, "price"),
        source_flags={
            "membership": sorted(membership),
            "membership_count": len(membership),
            "hard_exclude": hard_exclude,
            "entry_judgment": str(row.get("entry_judgment") or "").strip(),
            "rr": _optional_float(row, "rr"),
            "risk_judgment": str(row.get("risk_judgment") or "").strip(),
        },
        membership_count=len(membership),
        entry_judgment=str(row.get("entry_judgment") or "").strip(),
        rr=_optional_float(row, "rr"),
        risk_judgment=str(row.get("risk_judgment") or "").strip(),
    )


def _candidate_sort_key(candidate: FinalBuyCandidate) -> tuple[float, float, float, str]:
    return (
        -safe_float(candidate.qbs_score),
        -safe_float(candidate.membership_count),
        -safe_float(candidate.volume_ratio_20),
        str(candidate.ticker),
    )


def rank_final_buy_candidates(
    section_rows: Mapping[str, Iterable[Mapping[str, Any]]],
    *,
    target_date: date,
) -> list[FinalBuyCandidate]:
    membership, rows_by_section = _build_membership(section_rows)
    candidates = [
        _score_candidate(ticker, _canonical_row(ticker, rows_by_section), ticker_membership, target_date)
        for ticker, ticker_membership in membership.items()
    ]

    grouped: dict[str, list[FinalBuyCandidate]] = {}
    for candidate in candidates:
        grouped.setdefault(candidate.bucket, []).append(candidate)
    for bucket_candidates in grouped.values():
        bucket_candidates.sort(key=_candidate_sort_key)
        for rank, candidate in enumerate(bucket_candidates, start=1):
            candidate.rank = rank

    candidates.sort(key=_candidate_sort_key)
    return candidates


def build_final_buy_sections(
    section_rows: Mapping[str, Iterable[Mapping[str, Any]]],
    *,
    target_date: date,
) -> dict[str, list[FinalBuyCandidate]]:
    candidates = rank_final_buy_candidates(section_rows, target_date=target_date)
    bucket_to_key = {
        BUCKET_BUY_NOW: QBS_BUY_NOW_KEY,
        BUCKET_CHASE_WATCH: QBS_CHASE_WATCH_KEY,
        BUCKET_PULLBACK_WAIT: QBS_PULLBACK_WAIT_KEY,
    }
    sections = {key: [] for key in QBS_OUTPUT_KEYS}
    for candidate in candidates:
        output_key = bucket_to_key.get(candidate.bucket)
        if not output_key:
            continue
        if len(sections[output_key]) >= QBS_OUTPUT_LIMITS.get(output_key, QBS_OUTPUT_LIMIT):
            continue
        sections[output_key].append(candidate)
    return sections


def annotate_rows_with_qbs(
    rows: Iterable[Mapping[str, Any]],
    *,
    target_date: date,
) -> list[dict[str, Any]]:
    row_list = [dict(row or {}) for row in rows or []]
    section_rows = select_post_close_sections(row_list, target_date=target_date)
    candidates = rank_final_buy_candidates(section_rows, target_date=target_date)
    by_ticker = {candidate.ticker: candidate for candidate in candidates}

    annotated: list[dict[str, Any]] = []
    for row in row_list:
        row_dict = dict(row or {})
        candidate = by_ticker.get(_ticker(row_dict))
        row_dict["qbs_score"] = ""
        row_dict["qbs_bucket"] = ""
        row_dict["qbs_rank"] = ""
        row_dict["qbs_tags"] = ""
        row_dict["qbs_risk_flags"] = ""
        row_dict["qbs_membership_count"] = ""
        if candidate is not None:
            row_dict["qbs_score"] = f"{candidate.qbs_score:.1f}"
            row_dict["qbs_bucket"] = candidate.bucket
            row_dict["qbs_rank"] = candidate.rank if candidate.bucket else ""
            row_dict["qbs_tags"] = "+".join(candidate.tags)
            row_dict["qbs_risk_flags"] = "+".join(candidate.risk_flags)
            row_dict["qbs_membership_count"] = candidate.membership_count
        annotated.append(row_dict)
    return annotated
