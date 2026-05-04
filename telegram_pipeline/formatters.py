from __future__ import annotations

import math
from datetime import date, datetime
from typing import Any, Iterable, Mapping

from .contracts import TelegramCandidate, TelegramDigest, TelegramSection
from .final_buy_ranker import (
    QBS_BUY_NOW_KEY,
    QBS_CHASE_WATCH_KEY,
    QBS_OUTPUT_KEYS,
    QBS_OUTPUT_LIMIT,
    QBS_OUTPUT_LIMITS,
    QBS_PULLBACK_WAIT_KEY,
    build_final_buy_sections,
)
from .rankers import (
    is_truthy,
    safe_float,
    same_day_buy_turn_count,
    same_day_hull_buy_turn,
    same_day_hull_sell_turn,
    same_day_sell_turn_count,
    same_day_utbot_buy_turn,
    same_day_utbot_sell_turn,
    same_session_buy_turn,
    same_session_sell_turn,
)
from .selectors import (
    BOARD_MANDATORY_SECTION_KEYS,
    BOARD_QUALITY_FLOORS,
    BOARD_SECTION_LIMIT,
    BOARD_SECTION_ORDER,
    BOARD_SECTION_TITLES,
    CORE_QUALITY_FLOORS,
    FIVE_DAY_TOP_LIMIT,
    select_post_close_sections,
    select_post_close_board_sections,
)

QBS_SECTION_TITLES: dict[str, str] = {
    QBS_BUY_NOW_KEY: f"오늘 매수 최종 후보 Top {QBS_OUTPUT_LIMIT}",
    QBS_CHASE_WATCH_KEY: f"강하지만 추격주의 Top {QBS_OUTPUT_LIMITS[QBS_CHASE_WATCH_KEY]}",
    QBS_PULLBACK_WAIT_KEY: f"눌림 대기 후보 Top {QBS_OUTPUT_LIMITS[QBS_PULLBACK_WAIT_KEY]}",
}

QBS_QUALITY_FLOORS: dict[str, str] = {
    QBS_BUY_NOW_KEY: "QBS>=50 + final/buy confluence + no hard risk + not chase extended",
    QBS_CHASE_WATCH_KEY: "QBS>=40 + extended move / 52W / 5D chase risk",
    QBS_PULLBACK_WAIT_KEY: "QBS>=25 + pullback reentry + no hard risk",
}

QBS_DISPLAY_NUMBERS: dict[str, str] = {
    QBS_BUY_NOW_KEY: "0",
    QBS_CHASE_WATCH_KEY: "0-1",
    QBS_PULLBACK_WAIT_KEY: "0-2",
}

BOARD_SECTION_KEYS = set(BOARD_SECTION_ORDER)
FIVE_DAY_TOP_SECTION_KEY = "five_day_top"


def _signed(value: Any, decimals: int = 2) -> str:
    try:
        return f"{float(value):+.{decimals}f}"
    except (TypeError, ValueError):
        return "--"


def _ratio(value: Any, decimals: int = 2) -> str:
    try:
        return f"x{float(value):.{decimals}f}"
    except (TypeError, ValueError):
        return "x--"


def _number(value: Any, decimals: int = 1) -> str:
    try:
        return f"{float(value):.{decimals}f}"
    except (TypeError, ValueError):
        return "--"


def _optional_float(row: Mapping[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = row.get(key)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(numeric):
            return numeric
    return None


def _five_day_status_tags(row: Mapping[str, Any]) -> list[str]:
    chg_5d = safe_float(row.get("chg_5d", 0.0))
    chg_pct = safe_float(row.get("chg", 0.0))
    rsi = safe_float(row.get("rsi", row.get("RSI", 0.0)))
    volume_ratio = safe_float(row.get("volume_ratio_20", 0.0))
    ma20_dist = safe_float(row.get("ma20_dist_pct", row.get("dist_sma20_pct", 0.0)))
    zscore20 = safe_float(row.get("zscore20", 0.0))
    entry_judgment = str(row.get("entry_judgment") or "").strip().upper()

    tags: list[str] = []
    if chg_5d >= 10.0 or is_truthy(row.get("strong_trend_persistent")):
        tags.append("강한상승")
    if volume_ratio >= 1.2 or is_truthy(row.get("volume_bullish")):
        tags.append("거래량동반")
    if rsi >= 75.0 or ma20_dist >= 20.0 or zscore20 >= 3.0:
        tags.append("과열주의")
    if is_truthy(row.get("entry_chase_risk")) or chg_5d >= 20.0 or chg_pct >= 12.0:
        tags.append("추격주의")
    if is_truthy(row.get("thin_trade_risk")) or volume_ratio < 0.8:
        tags.append("저유동성주의")
    if entry_judgment == "WAIT_PULLBACK" or is_truthy(row.get("pullback_reentry")):
        tags.append("눌림대기")
    return tags or ["정상상승"]


def _five_day_status(row: Mapping[str, Any]) -> str:
    return "/".join(_five_day_status_tags(row))


def _turn_engine_text(*, utbot: bool, hull: bool) -> str:
    if utbot and hull:
        return "UTBot+HULL"
    if utbot:
        return "UTBot"
    if hull:
        return "HULL"
    return "-"


def _top_reasons(reasons: list[str], *, fallback: str) -> str:
    unique: list[str] = []
    for reason in reasons:
        text = str(reason or "").strip()
        if not text or text in unique:
            continue
        unique.append(text)
        if len(unique) >= 3:
            break
    if not unique:
        return fallback
    return " + ".join(unique)


def _hit_summary(*values: Any) -> str:
    hits: list[str] = []
    for raw_value in values:
        for item in list(raw_value or []):
            text = str(item or "").strip()
            if not text or text in hits:
                continue
            hits.append(text)
            if len(hits) >= 2:
                return " + ".join(hits)
    return ""


def _build_final_top_reason(row: Mapping[str, Any], target_date: date) -> str:
    reasons: list[str] = []
    if same_session_buy_turn(row, target_date):
        reasons.append("same-session buy turn")
    if safe_float(row.get("volume_ratio_20", 0.0)) >= 1.2:
        reasons.append("volume lead")
    if safe_float(row.get("cmf", 0.0)) > 0.05:
        reasons.append("CMF+")
    if safe_float(row.get("obv_slope", 0.0)) > 0.0:
        reasons.append("OBV up")
    if is_truthy(row.get("low_conflict_bullish")) or str(row.get("strategy_conflict_level", "")).strip().upper() == "LOW":
        reasons.append("low conflict")
    return _top_reasons(reasons, fallback="final entry")


def _build_buy_turn_reason(row: Mapping[str, Any], target_date: date) -> str:
    reasons = ["same-day turn"]
    if same_day_buy_turn_count(row, target_date) >= 2:
        reasons.append("UTBot+HULL")
    if safe_float(row.get("volume_ratio_20", 0.0)) >= 1.2:
        reasons.append("volume lead")
    if safe_float(row.get("cmf", 0.0)) > 0.0:
        reasons.append("CMF+")
    if safe_float(row.get("obv_slope", 0.0)) > 0.0:
        reasons.append("OBV up")
    return _top_reasons(reasons, fallback="buy turn")


def _build_pullback_reason(row: Mapping[str, Any]) -> str:
    reasons: list[str] = ["uptrend persistent"]
    if is_truthy(row.get("pullback_reentry")):
        reasons.append("reentry signal")
    else:
        reasons.append("reentry ready")
    if safe_float(row.get("volume_dry_up_score", 0.0)) >= 10.0:
        reasons.append("volume dry-up")
    if safe_float(row.get("pullback_atr_multiple", 0.0)) <= 2.0:
        reasons.append("shallow pullback")
    return _top_reasons(reasons, fallback="pullback reentry")


def _build_trend_reason(row: Mapping[str, Any]) -> str:
    reasons: list[str] = []
    if safe_float(row.get("rs_rank_vs_index", 0.0)) >= 70.0:
        reasons.append("high RS")
    reasons.append("trend slope up")
    if is_truthy(row.get("volume_bullish")):
        reasons.append("volume support")
    if safe_float(row.get("zscore20", 0.0)) >= 2.5 or safe_float(row.get("dist_sma20_pct", 0.0)) >= 15.0:
        reasons.append("overheat caution")
    return _top_reasons(reasons, fallback="trend continuation")


def _build_hma_ema_reason(row: Mapping[str, Any]) -> str:
    reasons: list[str] = []
    if is_truthy(row.get("hma_ema_long_entry")):
        reasons.append("HMA25/EMA25 long entry")
    elif is_truthy(row.get("hma_ema_long_aligned")):
        reasons.append("HMA/EMA aligned")
    if is_truthy(row.get("hma25_ema25_cross_bull")):
        reasons.append("bull cross")
    if safe_float(row.get("volume_ratio_20", 0.0)) >= 1.2:
        reasons.append("volume lead")
    if safe_float(row.get("adx", 0.0)) >= 20.0:
        reasons.append("ADX trend")
    if safe_float(row.get("hma_ema_risk_to_ema50_pct", 999.0)) <= 5.0:
        reasons.append("EMA50 near")
    return _top_reasons(reasons, fallback="HMA/EMA trend")


def _build_sell_turn_reason(row: Mapping[str, Any], target_date: date) -> str:
    reasons = ["same-day turn"]
    if same_day_sell_turn_count(row, target_date) >= 2:
        reasons.append("UTBot+HULL")
    if safe_float(row.get("volume_ratio_20", 0.0)) >= 1.0:
        reasons.append("volume support")
    if safe_float(row.get("scan_score", 0.0)) > 0.0:
        reasons.append(f"score {safe_float(row.get('scan_score', 0.0)):.1f}")
    return _top_reasons(reasons, fallback="sell turn")


def _build_gap_setup_reason(row: Mapping[str, Any]) -> str:
    reasons = [
        f"GAP {int(safe_float(row.get('gap_setup_score', 0.0))):d}",
        f"G{int(safe_float(row.get('gap_setup_gate_count', 0.0))):d}/5",
    ]
    hit_text = _hit_summary(row.get("gap_setup_quality_hits"), row.get("gap_setup_hits"))
    if hit_text:
        reasons.append(hit_text)
    return _top_reasons(reasons, fallback="gap setup")


def _build_pocket_pivot_reason(row: Mapping[str, Any]) -> str:
    reasons = [
        f"PP {int(safe_float(row.get('pocket_pivot_score', 0.0))):d}",
        f"G{int(safe_float(row.get('pocket_pivot_gate_count', 0.0))):d}/5",
    ]
    hit_text = _hit_summary(row.get("pocket_pivot_quality_hits"), row.get("pocket_pivot_hits"))
    if hit_text:
        reasons.append(hit_text)
    return _top_reasons(reasons, fallback="pocket pivot")


def _build_five_day_top_reason(row: Mapping[str, Any]) -> str:
    reasons = [f"5D {_signed(row.get('chg_5d'), 2)}%"]
    if safe_float(row.get("volume_ratio_20", 0.0)) >= 1.2:
        reasons.append("volume lead")
    if safe_float(row.get("scan_score", 0.0)) > 0.0:
        reasons.append(f"score {safe_float(row.get('scan_score', 0.0)):.1f}")
    return _top_reasons(reasons, fallback="5D top")


def _build_new_52w_high_reason(row: Mapping[str, Any]) -> str:
    reasons = ["new 52W high"]
    if is_truthy(row.get("new_52w_closing_high")):
        reasons.append("closing high")
    if safe_float(row.get("volume_ratio_20", 0.0)) >= 1.2:
        reasons.append("volume lead")
    return _top_reasons(reasons, fallback="new 52W high")


def _candidate_label(section_key: str) -> str:
    return {
        "confluence": "CONFLUENCE",
        "entry_now": "ENTRY",
        "steady_uptrend": "STEADY",
        "breakout_wait": "BREAKOUT_WAIT",
        "accumulation": "ACCUMULATION",
        "rs_leader": "RS_LEADER",
        "chase_risk": "CHASE_RISK",
        "sell_risk": "SELL_RISK",
        "final_top": "final",
        "buy_turn": "buy turn",
        "pullback_reentry": "pullback",
        "trend_continuation": "trend",
        "hma_ema_trend": "HMA/EMA",
        "sell_turn": "sell turn",
        "gap_setup": "gap setup",
        "pocket_pivot": "pocket pivot",
        "five_day_top": "5D top",
        "new_52w_high": "52W high",
    }.get(section_key, section_key)


def _candidate_reason(section_key: str, row: Mapping[str, Any], target_date: date) -> str:
    board_reason = str(row.get("board_reason") or "").strip()
    if section_key in BOARD_SECTION_KEYS and board_reason:
        return board_reason
    if section_key == "final_top":
        return _build_final_top_reason(row, target_date)
    if section_key == "buy_turn":
        return _build_buy_turn_reason(row, target_date)
    if section_key == "pullback_reentry":
        return _build_pullback_reason(row)
    if section_key == "trend_continuation":
        return _build_trend_reason(row)
    if section_key == "hma_ema_trend":
        return _build_hma_ema_reason(row)
    if section_key == "sell_turn":
        return _build_sell_turn_reason(row, target_date)
    if section_key == "gap_setup":
        return _build_gap_setup_reason(row)
    if section_key == "pocket_pivot":
        return _build_pocket_pivot_reason(row)
    if section_key == "five_day_top":
        return _build_five_day_top_reason(row)
    if section_key == "new_52w_high":
        return _build_new_52w_high_reason(row)
    return "-"


def _candidate_source_flags(section_key: str, row: Mapping[str, Any], target_date: date) -> dict[str, Any]:
    buy_turn_utbot = same_day_utbot_buy_turn(row, target_date)
    buy_turn_hull = same_day_hull_buy_turn(row, target_date)
    sell_turn_utbot = same_day_utbot_sell_turn(row, target_date)
    sell_turn_hull = same_day_hull_sell_turn(row, target_date)
    turn_engine = ""
    if section_key == "buy_turn":
        turn_engine = _turn_engine_text(utbot=buy_turn_utbot, hull=buy_turn_hull)
    elif section_key == "sell_turn":
        turn_engine = _turn_engine_text(utbot=sell_turn_utbot, hull=sell_turn_hull)

    return {
        "same_session_buy_turn": same_session_buy_turn(row, target_date),
        "same_session_sell_turn": same_session_sell_turn(row, target_date),
        "buy_turn_utbot": buy_turn_utbot,
        "buy_turn_hull": buy_turn_hull,
        "sell_turn_utbot": sell_turn_utbot,
        "sell_turn_hull": sell_turn_hull,
        "turn_engine": turn_engine,
        "thin_trade_risk": is_truthy(row.get("thin_trade_risk")),
        "bearish_gap_failure": is_truthy(row.get("bearish_gap_failure")),
        "hma_ema_long_aligned": is_truthy(row.get("hma_ema_long_aligned")),
        "hma_ema_long_entry": is_truthy(row.get("hma_ema_long_entry")),
        "hma_ema_short_aligned": is_truthy(row.get("hma_ema_short_aligned")),
        "hma_ema_short_entry": is_truthy(row.get("hma_ema_short_entry")),
        "hma_ema_signal_state": str(row.get("hma_ema_signal_state") or "NEUTRAL"),
        "multi_buy": int(safe_float(row.get("multi_buy", 0.0))),
        "multi_sell": int(safe_float(row.get("multi_sell", 0.0))),
        "chg_5d": safe_float(row.get("chg_5d", 0.0)),
        "rsi": safe_float(row.get("rsi", row.get("RSI", 0.0))),
        "ma20_dist_pct": safe_float(row.get("ma20_dist_pct", row.get("dist_sma20_pct", 0.0))),
        "status_tags": _five_day_status_tags(row) if section_key == FIVE_DAY_TOP_SECTION_KEY else [],
        "status": _five_day_status(row) if section_key == FIVE_DAY_TOP_SECTION_KEY else "",
        "label": _candidate_label(section_key),
        "membership": list(row.get("source_membership") or []),
        "membership_count": int(safe_float(row.get("membership_count", 0.0))),
        "board_risk": str(row.get("board_risk") or "-"),
    }


def _build_candidate(section_key: str, row: Mapping[str, Any], rank: int, target_date: date) -> TelegramCandidate:
    status_tags = _five_day_status_tags(row) if section_key == FIVE_DAY_TOP_SECTION_KEY else []
    return TelegramCandidate(
        ticker=str(row.get("ticker") or "").strip().upper(),
        price=safe_float(row.get("price")) if row.get("price") is not None else None,
        chg_value=safe_float(row.get("chg_value")) if row.get("chg_value") is not None else None,
        chg_pct=safe_float(row.get("chg")) if row.get("chg") is not None else None,
        volume_ratio_20=safe_float(row.get("volume_ratio_20")) if row.get("volume_ratio_20") is not None else None,
        section_key=section_key,
        rank=rank,
        label=str(row.get("board_label") or _candidate_label(section_key)),
        reason=_candidate_reason(section_key, row, target_date),
        source_flags=_candidate_source_flags(section_key, row, target_date),
        tags=list(row.get("board_tags") or []),
        risk_flags=list(row.get("board_risk_flags") or []),
        chg_5d=_optional_float(row, "chg_5d"),
        rsi=_optional_float(row, "rsi", "RSI"),
        ma20_dist_pct=_optional_float(row, "ma20_dist_pct", "dist_sma20_pct"),
        status_tags=status_tags,
        status="/".join(status_tags) if status_tags else "",
    )


def _build_qbs_candidate(section_key: str, candidate: Any) -> TelegramCandidate:
    return TelegramCandidate(
        ticker=str(candidate.ticker or "").strip().upper(),
        price=candidate.price,
        chg_value=candidate.chg_value,
        chg_pct=candidate.chg_pct,
        volume_ratio_20=candidate.volume_ratio_20,
        section_key=section_key,
        rank=int(candidate.rank or 0),
        label=str(candidate.bucket or ""),
        reason="+".join(candidate.tags) or "-",
        source_flags=dict(candidate.source_flags or {}),
        qbs_score=candidate.qbs_score,
        bucket=str(candidate.bucket or ""),
        tags=list(candidate.tags or []),
        risk_flags=list(candidate.risk_flags or []),
    )


def _build_qbs_sections(section_rows: Mapping[str, Iterable[Mapping[str, Any]]], target_date: date) -> list[TelegramSection]:
    qbs_sections = build_final_buy_sections(section_rows, target_date=target_date)
    sections: list[TelegramSection] = []
    for section_key in QBS_OUTPUT_KEYS:
        candidates = list(qbs_sections.get(section_key) or [])
        items = [_build_qbs_candidate(section_key, candidate) for candidate in candidates]
        sections.append(
            TelegramSection(
                key=section_key,
                title=QBS_SECTION_TITLES[section_key],
                items=items,
                item_count=len(items),
                quality_floor=QBS_QUALITY_FLOORS[section_key],
                ranked=True,
            )
        )
    return sections


def build_post_close_digest(
    rows: Iterable[Mapping[str, Any]],
    *,
    run_stamp: str,
    generated_at: datetime,
    market_date: date,
    scan_label: str,
    universe_count: int,
    result_count: int,
    skip_count: int,
) -> TelegramDigest:
    row_list = [dict(row or {}) for row in (rows or [])]
    section_rows = select_post_close_sections(row_list, target_date=market_date)

    sections: list[TelegramSection] = _build_qbs_sections(section_rows, market_date)
    qbs_top_tickers = {
        item.ticker
        for section in sections
        if section.key == QBS_BUY_NOW_KEY
        for item in section.items
    }
    board_rows = select_post_close_board_sections(
        section_rows,
        target_date=market_date,
        all_rows=row_list,
        qbs_top_tickers=qbs_top_tickers,
    )
    for section_key in BOARD_SECTION_ORDER:
        row_list = list(board_rows.get(section_key) or [])
        items = [_build_candidate(section_key, row, idx, market_date) for idx, row in enumerate(row_list, start=1)]
        sections.append(
            TelegramSection(
                key=section_key,
                title=BOARD_SECTION_TITLES[section_key],
                items=items,
                item_count=len(items),
                quality_floor=BOARD_QUALITY_FLOORS[section_key],
                ranked=True,
            )
        )
    five_day_rows = list(section_rows.get(FIVE_DAY_TOP_SECTION_KEY) or [])
    five_day_items = [
        _build_candidate(FIVE_DAY_TOP_SECTION_KEY, row, idx, market_date)
        for idx, row in enumerate(five_day_rows, start=1)
    ]
    sections.append(
        TelegramSection(
            key=FIVE_DAY_TOP_SECTION_KEY,
            title=f"5일 상승률 Top{FIVE_DAY_TOP_LIMIT}",
            items=five_day_items,
            item_count=len(five_day_items),
            quality_floor=CORE_QUALITY_FLOORS[FIVE_DAY_TOP_SECTION_KEY],
            ranked=True,
        )
    )

    return TelegramDigest(
        version="2.0",
        scan_mode="post_close",
        run_stamp=str(run_stamp or "").strip(),
        market_date=market_date.isoformat(),
        generated_at=generated_at.isoformat(),
        section_order=[*QBS_OUTPUT_KEYS, *BOARD_SECTION_ORDER, FIVE_DAY_TOP_SECTION_KEY],
        sections=sections,
        briefing_refs={
            "mode": "separate_message",
            "job": "market_briefing_notify",
            "expected_order": ["market_briefing", "main_board"],
        },
        scan_label=scan_label,
        universe_count=int(universe_count or 0),
        result_count=int(result_count or 0),
        skip_count=int(skip_count or 0),
    )


def _format_candidate_line(candidate: TelegramCandidate) -> str:
    risk = "+".join(list(candidate.risk_flags or [])) or str(candidate.source_flags.get("board_risk") or "-")
    return (
        f"{candidate.rank}. {candidate.ticker}"
        f" | {str(candidate.label or '-')}"
        f" | {_signed(candidate.chg_pct)}%"
        f" | {_ratio(candidate.volume_ratio_20)}"
        f" | {str(candidate.reason or '-')}"
        f" | {risk or '-'}"
    )


def _format_five_day_candidate_line(candidate: TelegramCandidate) -> str:
    return (
        f"{candidate.ticker}"
        f" | {_signed(candidate.chg_5d, 2)}%"
        f" | RSI {_number(candidate.rsi, 1)}"
        f" | {_ratio(candidate.volume_ratio_20, 2)}"
        f" | {_signed(candidate.ma20_dist_pct, 1)}%"
        f" | {str(candidate.status or '-')}"
    )


def _format_qbs_candidate_line(candidate: TelegramCandidate) -> str:
    tags = "+".join(list(candidate.tags or [])) or "-"
    line = (
        f"{candidate.rank}. {candidate.ticker}"
        f" | QBS {safe_float(candidate.qbs_score):.1f}"
        f" | ({_signed(candidate.chg_value)}, {_signed(candidate.chg_pct)}%)"
        f" | {_ratio(candidate.volume_ratio_20)}"
        f" | {str(candidate.bucket or '-')}"
        f" | {tags}"
    )
    risk_flags = "+".join(list(candidate.risk_flags or []))
    if risk_flags:
        line += f" | 주의:{risk_flags}"
    return line


def _qbs_section_block(display_number: str, section: TelegramSection) -> str:
    lines = [f"## {display_number}. {section.title}"]
    if not section.items:
        lines.append("- 해당 없음")
        return "\n".join(lines)
    for item in section.items:
        lines.append(_format_qbs_candidate_line(item))
    return "\n".join(lines)


def _section_block(index: int, section: TelegramSection) -> str:
    section_limit = FIVE_DAY_TOP_LIMIT if section.key == FIVE_DAY_TOP_SECTION_KEY else BOARD_SECTION_LIMIT
    descriptor = f"Top {min(section.item_count, section_limit)}"
    lines = [f"## {index}. {section.title} ({descriptor})"]
    if not section.items:
        lines.append("- 해당 없음")
        return "\n".join(lines)
    if section.key == FIVE_DAY_TOP_SECTION_KEY:
        lines.append("티커 | 5일 상승률 | RSI | Vol20 | MA20이격 | 상태")
        for item in section.items:
            lines.append(_format_five_day_candidate_line(item))
        return "\n".join(lines)
    for item in section.items:
        lines.append(_format_candidate_line(item))
    return "\n".join(lines)


def build_main_message(digest: TelegramDigest) -> str:
    blocks = [
        "\n".join(
            [
                "[오늘 종목판]",
                f"- 시장일: {digest.market_date} (US)",
                f"- 유니버스: {digest.universe_count} | 결과: {digest.result_count} | 제외: {digest.skip_count}",
                f"- 생성: {digest.generated_at}",
            ]
        )
    ]

    display_index = 1
    for section in digest.sections:
        if section.key in QBS_DISPLAY_NUMBERS:
            blocks.append(_qbs_section_block(QBS_DISPLAY_NUMBERS[section.key], section))
            continue
        if section.key not in BOARD_MANDATORY_SECTION_KEYS and section.item_count <= 0:
            continue
        blocks.append(_section_block(display_index, section))
        display_index += 1

    return "\n\n".join(blocks)


def build_post_close_message_texts(digest: TelegramDigest) -> list[str]:
    return [build_main_message(digest)]
