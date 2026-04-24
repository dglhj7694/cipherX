from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterable, Mapping

from .contracts import TelegramCandidate, TelegramDigest, TelegramSection
from .rankers import (
    is_truthy,
    safe_float,
    same_day_hull_buy_turn,
    same_day_hull_sell_turn,
    same_day_buy_turn_count,
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
        return f"x{float(value):.{decimals}f}배"
    except (TypeError, ValueError):
        return "x--배"


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
    reasons: list[str] = ["A/B/C 통과"]
    if same_session_buy_turn(row, target_date):
        reasons.append("당일 매수전환")
    if safe_float(row.get("volume_ratio_20", 0.0)) >= 1.2:
        reasons.append("거래량 우위")
    if safe_float(row.get("cmf", 0.0)) > 0.05:
        reasons.append("CMF 양호")
    if safe_float(row.get("obv_slope", 0.0)) > 0.0:
        reasons.append("OBV 상승")
    if is_truthy(row.get("low_conflict_bullish")) or str(row.get("strategy_conflict_level", "")).strip().upper() == "LOW":
        reasons.append("충돌 낮음")
    return _top_reasons(reasons, fallback="A/B/C 통과")


def _build_buy_turn_reason(row: Mapping[str, Any], target_date: date) -> str:
    reasons = ["당일 전환"]
    if same_day_buy_turn_count(row, target_date) >= 2:
        reasons.append("UTBot+HULL 동시")
    if safe_float(row.get("volume_ratio_20", 0.0)) >= 1.2:
        reasons.append("거래량 우위")
    if safe_float(row.get("cmf", 0.0)) > 0.0:
        reasons.append("CMF 양호")
    if safe_float(row.get("obv_slope", 0.0)) > 0.0:
        reasons.append("OBV 상승")
    return _top_reasons(reasons, fallback="당일 매수전환")


def _build_pullback_reason(row: Mapping[str, Any]) -> str:
    reasons: list[str] = ["상승 구조 유지"]
    if is_truthy(row.get("pullback_reentry")):
        reasons.append("재진입 신호")
    else:
        reasons.append("재진입 준비")
    if safe_float(row.get("volume_dry_up_score", 0.0)) >= 10.0:
        reasons.append("거래량 건조")
    if safe_float(row.get("pullback_atr_multiple", 0.0)) <= 2.0:
        reasons.append("적정 눌림")
    return _top_reasons(reasons, fallback="눌림목 재진입")


def _build_trend_reason(row: Mapping[str, Any]) -> str:
    reasons: list[str] = []
    if safe_float(row.get("rs_rank_vs_index", 0.0)) >= 70.0:
        reasons.append("상대강도 우위")
    reasons.append("추세 기울기 유지")
    if is_truthy(row.get("volume_bullish")):
        reasons.append("거래량 동반")
    if safe_float(row.get("zscore20", 0.0)) >= 2.5 or safe_float(row.get("dist_sma20_pct", 0.0)) >= 15.0:
        reasons.append("과열 경계")
    return _top_reasons(reasons, fallback="추세 지속 후보")


def _build_sell_turn_reason(row: Mapping[str, Any], target_date: date) -> str:
    reasons = ["당일 전환"]
    if same_day_sell_turn_count(row, target_date) >= 2:
        reasons.append("UTBot+HULL 동시")
    if safe_float(row.get("volume_ratio_20", 0.0)) >= 1.0:
        reasons.append("거래량 동반")
    if safe_float(row.get("scan_score", 0.0)) > 0.0:
        reasons.append(f"점수 {safe_float(row.get('scan_score', 0.0)):.1f}")
    return _top_reasons(reasons, fallback="당일 매도전환")


def _build_gap_setup_reason(row: Mapping[str, Any]) -> str:
    reasons = [
        f"GAP {int(safe_float(row.get('gap_setup_score', 0.0))):d}",
        f"G{int(safe_float(row.get('gap_setup_gate_count', 0.0))):d}/5",
    ]
    hit_text = _hit_summary(row.get("gap_setup_quality_hits"), row.get("gap_setup_hits"))
    if hit_text:
        reasons.append(hit_text)
    return _top_reasons(reasons, fallback="돌파 임박")


def _build_pocket_pivot_reason(row: Mapping[str, Any]) -> str:
    reasons = [
        f"PP {int(safe_float(row.get('pocket_pivot_score', 0.0))):d}",
        f"G{int(safe_float(row.get('pocket_pivot_gate_count', 0.0))):d}/5",
    ]
    hit_text = _hit_summary(row.get("pocket_pivot_quality_hits"), row.get("pocket_pivot_hits"))
    if hit_text:
        reasons.append(hit_text)
    return _top_reasons(reasons, fallback="기관 매집 포착")


def _build_five_day_top_reason(row: Mapping[str, Any]) -> str:
    reasons = [f"5일 {_signed(row.get('chg_5d'), 2)}%"]
    if safe_float(row.get("volume_ratio_20", 0.0)) >= 1.2:
        reasons.append("거래량 우위")
    if safe_float(row.get("scan_score", 0.0)) > 0.0:
        reasons.append(f"점수 {safe_float(row.get('scan_score', 0.0)):.1f}")
    return _top_reasons(reasons, fallback="5일 상승률 상위")


def _build_new_52w_high_reason(row: Mapping[str, Any]) -> str:
    reasons = ["52주 신고가 갱신"]
    if is_truthy(row.get("new_52w_closing_high")):
        reasons.append("종가 신고가")
    if safe_float(row.get("volume_ratio_20", 0.0)) >= 1.2:
        reasons.append("거래량 우위")
    return _top_reasons(reasons, fallback="52주 신고가")


def _candidate_label(section_key: str) -> str:
    return {
        "final_top": "최우선",
        "buy_turn": "매수전환",
        "pullback_reentry": "눌림목",
        "trend_continuation": "추세지속",
        "sell_turn": "매도전환",
        "gap_setup": "돌파임박",
        "pocket_pivot": "기관매집",
        "five_day_top": "5일상승",
        "new_52w_high": "52주신고",
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
            "expected_order": ["시장 브리핑", "종목판 메인"],
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
    descriptor = f"Top {min(section.item_count, FINAL_TOP_LIMIT if section.key == 'final_top' else FIVE_DAY_TOP_LIMIT)}" if section.ranked else f"{section.item_count}개"
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
