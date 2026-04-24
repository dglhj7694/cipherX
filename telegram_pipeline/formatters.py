from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterable, Mapping

from .contracts import TelegramCandidate, TelegramDigest, TelegramSection
from .deduper import dedupe_core_sections
from .rankers import (
    buy_turn_signal_count,
    is_truthy,
    same_session_buy_turn,
    same_session_sell_turn,
    safe_float,
    sell_turn_signal_count,
)
from .selectors import (
    CORE_QUALITY_FLOORS,
    CORE_SECTION_ORDER,
    CORE_SECTION_TITLES,
    DEDUPE_PRIORITY,
    DETAIL_TOP_N,
    SUMMARY_TOP_N,
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


def _tier_for_rank(rank: int) -> str:
    if rank <= 5:
        return "A"
    if rank <= 10:
        return "B"
    return "C"


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
    reasons: list[str] = []
    if same_session_buy_turn(row, target_date):
        reasons.append("당일 전환")
    else:
        reasons.append("최근 2일 전환")
    if buy_turn_signal_count(row) >= 2:
        reasons.append("복수 매수전환")
    if safe_float(row.get("volume_ratio_20", 0.0)) >= 1.2:
        reasons.append("거래량 우위")
    if safe_float(row.get("cmf", 0.0)) > 0.0:
        reasons.append("CMF 양호")
    if safe_float(row.get("obv_slope", 0.0)) > 0.0:
        reasons.append("OBV 상승")
    return _top_reasons(reasons, fallback="매수전환 확인")


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
    reasons: list[str] = []
    if same_session_sell_turn(row, target_date):
        reasons.append("당일 매도전환")
    elif is_truthy(row.get("utbot_sell_recent")) or is_truthy(row.get("hull_turn_bear_recent")):
        reasons.append("최근 매도전환")
    if sell_turn_signal_count(row, target_date) >= 3:
        reasons.append("복수 약세 신호")
    if is_truthy(row.get("bearish_gap_failure")):
        reasons.append("갭 실패")
    if is_truthy(row.get("thin_trade_risk")):
        reasons.append("유동성 주의")
    if safe_float(row.get("drawdown_from_20d_high_pct", 0.0)) <= -5.0:
        reasons.append("20일 고점 이탈")
    return _top_reasons(reasons, fallback="주의 신호")


def _candidate_label(section_key: str) -> str:
    return {
        "final_top": "최우선",
        "buy_turn": "매수전환",
        "pullback_reentry": "눌림목",
        "trend_continuation": "추세지속",
        "sell_turn": "주의",
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
    return "-"


def _candidate_source_flags(section_key: str, row: Mapping[str, Any], target_date: date) -> dict[str, Any]:
    return {
        "same_session_buy_turn": same_session_buy_turn(row, target_date),
        "same_session_sell_turn": same_session_sell_turn(row, target_date),
        "utbot_buy_recent": is_truthy(row.get("utbot_buy_recent")),
        "utbot_sell_recent": is_truthy(row.get("utbot_sell_recent")),
        "hull_turn_bull_recent": is_truthy(row.get("hull_turn_bull_recent")),
        "hull_turn_bear_recent": is_truthy(row.get("hull_turn_bear_recent")),
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
        tier=_tier_for_rank(rank),
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
    raw_sections = select_post_close_sections(rows, target_date=market_date)
    deduped_sections, dedupe_applied = dedupe_core_sections(raw_sections, dedupe_order=DEDUPE_PRIORITY)

    sections: list[TelegramSection] = []
    for section_key in CORE_SECTION_ORDER:
        row_list = raw_sections.get(section_key, []) if section_key == "final_top" else deduped_sections.get(section_key, [])
        detail_rows = list(row_list[:DETAIL_TOP_N])
        summary_rows = list(detail_rows[:SUMMARY_TOP_N])
        detail_items = [_build_candidate(section_key, row, idx, market_date) for idx, row in enumerate(detail_rows, start=1)]
        summary_items = [_build_candidate(section_key, row, idx, market_date) for idx, row in enumerate(summary_rows, start=1)]
        sections.append(
            TelegramSection(
                key=section_key,
                title=CORE_SECTION_TITLES[section_key],
                summary_items=summary_items,
                detail_items=detail_items,
                sent_count=len(detail_items),
                quality_floor=CORE_QUALITY_FLOORS[section_key],
                dedupe_applied=bool(dedupe_applied.get(section_key, False)),
            )
        )

    return TelegramDigest(
        version="1.0",
        scan_mode="post_close",
        run_stamp=str(run_stamp or "").strip(),
        market_date=market_date.isoformat(),
        generated_at=generated_at.isoformat(),
        section_order=list(CORE_SECTION_ORDER),
        sections=sections,
        briefing_refs={
            "mode": "separate_message",
            "job": "market_briefing_notify",
            "expected_order": ["시장 브리핑", "핵심 요약", "섹션별 상세"],
        },
        scan_label=scan_label,
        universe_count=int(universe_count or 0),
        result_count=int(result_count or 0),
        skip_count=int(skip_count or 0),
    )


def _format_candidate_line(candidate: TelegramCandidate) -> str:
    return (
        f"{candidate.rank}. {candidate.ticker}"
        f" | ({_signed(candidate.chg_value)}, {_signed(candidate.chg_pct)}%)"
        f" | {_ratio(candidate.volume_ratio_20)}"
        f" | {candidate.label}"
        f" | {candidate.reason}"
    )


def build_summary_message(digest: TelegramDigest) -> str:
    lines = [
        "[오늘 종목판 핵심 요약]",
        f"- 시장일: {digest.market_date} (US)",
        f"- 유니버스: {digest.universe_count} | 결과: {digest.result_count} | 제외: {digest.skip_count}",
        f"- 생성: {digest.generated_at}",
        "",
    ]
    for index, section in enumerate(digest.sections, start=1):
        lines.append(f"{index}) {section.title} Top {len(section.summary_items)} / {section.sent_count}")
        if not section.summary_items:
            lines.append("- 해당 없음")
        else:
            for item in section.summary_items:
                lines.append(_format_candidate_line(item))
        lines.append("")
    if lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def build_detail_message(digest: TelegramDigest, section: TelegramSection, *, index: int, total: int) -> str:
    lines = [
        f"[오늘 종목판 상세 {index}/{total}]",
        f"- 섹션: {section.title}",
        f"- 시장일: {digest.market_date} (US)",
        f"- 전송: {section.sent_count}/{DETAIL_TOP_N}",
        f"- 품질 기준: {section.quality_floor}",
        f"- 중복 정리: {'Y' if section.dedupe_applied else 'N'}",
        "",
    ]
    if not section.detail_items:
        lines.append("- 해당 없음")
        return "\n".join(lines)

    tier_rows = {
        "A": [item for item in section.detail_items if item.tier == "A"],
        "B": [item for item in section.detail_items if item.tier == "B"],
        "C": [item for item in section.detail_items if item.tier == "C"],
    }
    for tier_key, tier_title in (("A", "A티어 (1~5)"), ("B", "B티어 (6~10)"), ("C", "C티어 (11~20)")):
        tier_items = tier_rows[tier_key]
        if not tier_items:
            continue
        lines.append(tier_title)
        for item in tier_items:
            lines.append(_format_candidate_line(item))
        lines.append("")
    if lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def build_post_close_message_texts(digest: TelegramDigest) -> list[str]:
    messages = [build_summary_message(digest)]
    total = len(digest.sections)
    for index, section in enumerate(digest.sections, start=1):
        messages.append(build_detail_message(digest, section, index=index, total=total))
    return messages
