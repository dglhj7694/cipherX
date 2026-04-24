from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterable, Mapping

from .contracts import TelegramCandidate, TelegramDigest, TelegramSection
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
    CORE_QUALITY_FLOORS,
    CORE_SECTION_ORDER,
    CORE_SECTION_TITLES,
    FINAL_TOP_LIMIT,
    FIVE_DAY_TOP_LIMIT,
    MANDATORY_SECTION_KEYS,
    select_post_close_sections,
)


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
        "label": _candidate_label(section_key),
    }


def _build_candidate(section_key: str, row: Mapping[str, Any], rank: int, target_date: date) -> TelegramCandidate:
    return TelegramCandidate(
        ticker=str(row.get("ticker") or "").strip().upper(),
        price=safe_float(row.get("price")) if row.get("price") is not None else None,
        chg_value=safe_float(row.get("chg_value")) if row.get("chg_value") is not None else None,
        chg_pct=safe_float(row.get("chg")) if row.get("chg") is not None else None,
        volume_ratio_20=safe_float(row.get("volume_ratio_20")) if row.get("volume_ratio_20") is not None else None,
        section_key=section_key,
        rank=rank,
        label=_candidate_label(section_key),
        reason=_candidate_reason(section_key, row, target_date),
        source_flags=_candidate_source_flags(section_key, row, target_date),
    )


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
    section_rows = select_post_close_sections(rows, target_date=market_date)

    sections: list[TelegramSection] = []
    for section_key in CORE_SECTION_ORDER:
        row_list = list(section_rows.get(section_key) or [])
        items = [_build_candidate(section_key, row, idx, market_date) for idx, row in enumerate(row_list, start=1)]
        sections.append(
            TelegramSection(
                key=section_key,
                title=CORE_SECTION_TITLES[section_key],
                items=items,
                item_count=len(items),
                quality_floor=CORE_QUALITY_FLOORS[section_key],
                ranked=section_key in {"final_top", "five_day_top"},
            )
        )

    return TelegramDigest(
        version="2.0",
        scan_mode="post_close",
        run_stamp=str(run_stamp or "").strip(),
        market_date=market_date.isoformat(),
        generated_at=generated_at.isoformat(),
        section_order=list(CORE_SECTION_ORDER),
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
    line = (
        f"{candidate.rank}. {candidate.ticker}"
        f" | ({_signed(candidate.chg_value)}, {_signed(candidate.chg_pct)}%)"
        f" | {_ratio(candidate.volume_ratio_20)}"
    )
    turn_engine = str(candidate.source_flags.get("turn_engine") or "").strip()
    if turn_engine and candidate.section_key in {"buy_turn", "sell_turn"}:
        line += f" | {turn_engine}"
    return line


def _section_block(index: int, section: TelegramSection) -> str:
    if section.key == "final_top":
        descriptor = f"Top {min(section.item_count, FINAL_TOP_LIMIT)}"
    elif section.key == "five_day_top":
        descriptor = f"Top {min(section.item_count, FIVE_DAY_TOP_LIMIT)}"
    elif section.key == "hma_ema_trend":
        descriptor = f"Top {min(section.item_count, 20)}"
    else:
        descriptor = f"{section.item_count} items"
    lines = [f"## {index}. {section.title} ({descriptor})"]
    if not section.items:
        lines.append("- 해당 없음")
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
        if section.key not in MANDATORY_SECTION_KEYS and section.item_count <= 0:
            continue
        blocks.append(_section_block(display_index, section))
        display_index += 1

    return "\n\n".join(blocks)


def build_post_close_message_texts(digest: TelegramDigest) -> list[str]:
    return [build_main_message(digest)]
