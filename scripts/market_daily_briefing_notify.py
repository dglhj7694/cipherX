from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping
from zoneinfo import ZoneInfo

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

KST = ZoneInfo("Asia/Seoul")
DEFAULT_DETAIL_LIMIT = 30
DEFAULT_CORE_MOVER_LIMIT = 10
DEFAULT_QUICK_TARGET_LIMIT = 8
DEFAULT_CHUNK_SIZE = 3500
SECTOR_LABELS_KO: dict[str, str] = {
    "XLK": "기술",
    "XLF": "금융",
    "XLE": "에너지",
    "XLV": "헬스케어",
    "XLI": "산업재",
    "XLY": "경기소비재",
    "XLP": "필수소비재",
    "XLU": "유틸리티",
    "XLB": "소재",
    "XLC": "커뮤니케이션",
    "XLRE": "부동산",
}


def _safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        numeric = float(value)
        if math.isnan(numeric):
            return default
        return numeric
    except Exception:
        return default


def _coerce_text(value: Any) -> str:
    if isinstance(value, (bytes, bytearray)):
        raw = bytes(value)
        for encoding in ("utf-8", "cp949", "euc-kr"):
            try:
                return raw.decode(encoding).strip()
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", errors="replace").strip()
    if isinstance(value, str):
        return value.strip()
    return str(value or "").strip()


def _fmt_signed(value: Any, decimals: int = 2) -> str:
    numeric = _safe_float(value, None)
    if numeric is None:
        return "N/A"
    return f"{numeric:+.{decimals}f}"


def _fmt_price(value: Any) -> str:
    numeric = _safe_float(value, None)
    if numeric is None:
        return "N/A"
    return f"{numeric:.2f}"


def _fmt_ratio(value: Any, decimals: int = 2) -> str:
    numeric = _safe_float(value, None)
    if numeric is None:
        return "N/A"
    return f"{numeric:.{decimals}f}x"


def _fmt_pct_point(value: Any, decimals: int = 2) -> str:
    numeric = _safe_float(value, None)
    if numeric is None:
        return "N/A"
    return f"{numeric:+.{decimals}f}%p"


def _extract_card(payload: Mapping[str, Any], card_id: str) -> dict[str, Any]:
    for card in list(payload.get("cards") or []):
        if isinstance(card, dict) and _coerce_text(card.get("id")) == card_id:
            return card
    return {}


def _extract_bullet_texts(card: Mapping[str, Any], *, limit: int = 3) -> list[str]:
    lines: list[str] = []
    for item in list(card.get("bullets") or []):
        text = _coerce_text(item.get("text")) if isinstance(item, dict) else _coerce_text(item)
        if not text:
            continue
        lines.append(text)
        if len(lines) >= max(0, int(limit)):
            break
    return lines


def _format_sector_rank_lines_legacy(payload: Mapping[str, Any]) -> list[str]:
    sector_card = _extract_card(payload, "sector_pressure")
    metrics = [item for item in list(sector_card.get("metrics") or []) if isinstance(item, dict)]
    lines: list[str] = []
    for idx, metric in enumerate(metrics, start=1):
        label = _coerce_text(metric.get("label")) or "-"
        delta = _coerce_text(metric.get("delta")) or "N/A"
        note = _coerce_text(metric.get("note"))
        lines.append(f"{idx}. {label} {delta}" + (f" ({note})" if note else ""))
    return lines


def _format_mover_line(row: Mapping[str, Any], rank: int) -> str:
    symbol = _coerce_text(row.get("symbol")) or "-"
    price = _fmt_price(row.get("price"))
    change_value = _fmt_signed(row.get("change_value"), 2)
    change_pct = _fmt_signed(row.get("change_pct"), 2)
    volume_ratio = _fmt_ratio(row.get("volume_ratio"), 2)
    reason = _coerce_text(row.get("reason")) or "-"
    return f"{rank}. {symbol} | {price} ({change_value}, {change_pct}%) | 거래량 {volume_ratio} | {reason}"


def _normalize_10y_snapshot(entry: Mapping[str, Any]) -> dict[str, float | None]:
    price_raw = _safe_float(entry.get("price"), None)
    change_raw = _safe_float(entry.get("change_value"), None)
    change_pct = _safe_float(entry.get("change_pct"), None)
    if price_raw is None:
        return {"level_pct": None, "change_bp": None, "change_pct": change_pct}
    if abs(price_raw) >= 20:
        level_pct = price_raw / 10.0
        change_bp = change_raw * 10.0 if change_raw is not None else None
    else:
        level_pct = price_raw
        change_bp = change_raw * 100.0 if change_raw is not None else None
    return {"level_pct": level_pct, "change_bp": change_bp, "change_pct": change_pct}


def _build_sector_label_map(sector_rank: list[Mapping[str, Any]]) -> dict[str, str]:
    label_map = dict(SECTOR_LABELS_KO)
    for row in sector_rank:
        symbol = _coerce_text(row.get("symbol")).upper()
        label = _coerce_text(row.get("label"))
        if symbol and symbol not in label_map and label:
            label_map[symbol] = label
    return label_map


def _format_sector_symbol_with_label(symbol: str, label_map: Mapping[str, str]) -> str:
    normalized = _coerce_text(symbol).upper()
    if not normalized:
        return ""
    label = _coerce_text(label_map.get(normalized))
    return f"{normalized} ({label})" if label else normalized


def _format_snapshot_line(display_name: str, entry: Mapping[str, Any]) -> str:
    symbol = _coerce_text(entry.get("symbol"))
    prefix = f"{display_name} ({symbol})" if symbol and symbol != display_name else display_name
    if display_name == "10Y":
        normalized = _normalize_10y_snapshot(entry)
        value_text = f"{normalized['level_pct']:.2f}%" if normalized["level_pct"] is not None else "N/A"
        delta_text = f"{normalized['change_bp']:+.1f}bp" if normalized["change_bp"] is not None else f"{_fmt_signed(normalized['change_pct'], 2)}%"
        return f"- {prefix}: {value_text} ({delta_text})"
    price = _safe_float(entry.get("price"), None)
    change_value = _safe_float(entry.get("change_value"), None)
    change_pct = _safe_float(entry.get("change_pct"), None)
    return f"- {prefix}: {_fmt_price(price)} ({_fmt_signed(change_value, 2)}, {_fmt_signed(change_pct, 2)}%)"


def _build_index_interpretation_lines(benchmarks: Mapping[str, Any]) -> list[str]:
    qqq = dict(benchmarks.get("NASDAQ100") or {})
    spy = dict(benchmarks.get("S&P500") or {})
    iwm = dict(benchmarks.get("RUSSELL2000") or {})
    vix = dict(benchmarks.get("VIX") or {})
    qqq_chg = _safe_float(qqq.get("change_pct"), None)
    spy_chg = _safe_float(spy.get("change_pct"), None)
    iwm_chg = _safe_float(iwm.get("change_pct"), None)
    vix_chg = _safe_float(vix.get("change_pct"), None)
    lines: list[str] = []
    if qqq_chg is not None and spy_chg is not None:
        spread = qqq_chg - spy_chg
        lines.append(f"- 해석: QQQ-SPY 스프레드 {_fmt_signed(spread, 2)}%p -> {'대형 기술주 우위' if spread >= 0 else '광범위 업종 우위'}")
    if iwm_chg is not None and spy_chg is not None:
        spread = iwm_chg - spy_chg
        lines.append(f"- 해석: IWM-SPY 스프레드 {_fmt_signed(spread, 2)}%p -> {'소형주 확산 우호' if spread >= 0 else '소형주 확산 제한'}")
    if vix_chg is not None:
        lines.append(f"- 해석: VIX {_fmt_signed(vix_chg, 2)}% -> {'공포 완화' if vix_chg < 0 else '방어 심리 확대'}")
    return lines


def _build_macro_interpretation_lines(macro: Mapping[str, Any]) -> list[str]:
    lines: list[str] = []
    tnx_entry = dict(macro.get("10Y") or {})
    tnx_normalized = _normalize_10y_snapshot(tnx_entry)
    tnx_change_bp = _safe_float(tnx_normalized.get("change_bp"), None)
    dxy_change = _safe_float(dict(macro.get("DXY") or {}).get("change_pct"), None)
    wti_change = _safe_float(dict(macro.get("WTI") or {}).get("change_pct"), None)
    gold_change = _safe_float(dict(macro.get("Gold") or {}).get("change_pct"), None)
    btc_change = _safe_float(dict(macro.get("BTC") or {}).get("change_pct"), None)
    if tnx_change_bp is not None:
        lines.append(f"- 해석: 10Y {_fmt_signed(tnx_change_bp, 1)}bp -> {'금리 부담 완화' if tnx_change_bp < 0 else '금리 부담 잔존'}")
    if dxy_change is not None:
        lines.append(f"- 해석: DXY {_fmt_signed(dxy_change, 2)}% -> {'달러 압력 완화' if dxy_change < 0 else '달러 압력 확대'}")
    if wti_change is not None:
        lines.append(f"- 해석: WTI {_fmt_signed(wti_change, 2)}% -> {'인플레 민감도 완화' if wti_change < 0 else '인플레 민감도 상승'}")
    if gold_change is not None and btc_change is not None:
        lines.append(f"- 해석: Gold {_fmt_signed(gold_change, 2)}% / BTC {_fmt_signed(btc_change, 2)}%로 위험선호 강도 점검")
    return lines


def _build_report_core_briefing_text(
    report: Mapping[str, Any],
    *,
    run_at_kst: datetime,
    detail_limit: int,
    core_mover_limit: int,
    quick_target_limit: int,
) -> str:
    market_date_label = _coerce_text(report.get("market_date_label")) or "Latest session"
    headline = _coerce_text(report.get("headline")) or "오늘 미국장 핵심 흐름"
    one_liner = _coerce_text(report.get("one_liner")) or headline

    def _normalize_for_compare(text: str) -> str:
        return re.sub(r"[\s\.\,\-\|]+", "", str(text or "").lower())

    executive = dict(report.get("executive_summary") or {})
    sentiment = dict(report.get("sentiment") or {})
    risk_state_display = _coerce_text(executive.get("risk_state_display")) or _coerce_text(sentiment.get("risk_state_display")) or _coerce_text(sentiment.get("risk_state")) or "N/A"
    fear_greed_score = sentiment.get("fear_greed_score", executive.get("fear_greed_score"))
    fear_greed_label = _coerce_text(sentiment.get("fear_greed_label") or executive.get("fear_greed_label")) or "N/A"
    fear_greed_source_key = _coerce_text(sentiment.get("fear_greed_source") or executive.get("fear_greed_source")).lower()
    fear_greed_source_label = {"cnn": "CNN", "proxy": "Proxy"}.get(fear_greed_source_key, "")
    if not fear_greed_source_label and fear_greed_source_key:
        fear_greed_source_label = fear_greed_source_key
    fear_greed_source_suffix = f", {fear_greed_source_label}" if fear_greed_source_label else ""

    benchmarks = dict(report.get("benchmarks") or {})
    macro = dict(report.get("macro") or {})
    relative_strength = dict(report.get("relative_strength") or {})
    sector_rank = [item for item in list(report.get("sector_rank") or []) if isinstance(item, dict)]
    market_structure = dict(report.get("market_structure") or {})
    market_structure_text = _coerce_text(report.get("market_structure_text"))
    session_flow = dict(report.get("session_flow") or {})
    sector_summary = dict(report.get("sector_summary") or {})

    movers = dict(report.get("movers") or {})
    core_movers = dict(report.get("core_movers") or {})
    core_cap = max(1, int(core_mover_limit or DEFAULT_CORE_MOVER_LIMIT))
    quick_cap = max(1, int(quick_target_limit or DEFAULT_QUICK_TARGET_LIMIT))

    gainers = [dict(item or {}) for item in list(core_movers.get("gainers") or movers.get("gainers") or [])][:core_cap]
    losers = [dict(item or {}) for item in list(core_movers.get("losers") or movers.get("losers") or [])][:core_cap]

    action_points = dict(report.get("action_points") or {})
    insight_bullets = [_coerce_text(item) for item in list(action_points.get("insight_bullets") or []) if _coerce_text(item)]
    analysis_actions = [dict(item or {}) for item in list(action_points.get("analysis_actions") or []) if isinstance(item, dict)]

    quick_targets = [dict(item or {}) for item in list(report.get("quick_targets") or []) if isinstance(item, dict)]

    if not quick_targets:
        quick_targets = [{"symbol": _coerce_text(item.get("symbol"))} for item in analysis_actions[:quick_cap] if _coerce_text(item.get("symbol"))]

    breadth_summary = _coerce_text(report.get("breadth_summary")) or _coerce_text(market_structure.get("breadth_summary")) or "상승 섹터 정보 없음"
    if not market_structure_text:
        market_structure_text = (
            f"QQQ-SPY {_fmt_pct_point(relative_strength.get('QQQ_SPY'))}, "
            f"IWM-SPY {_fmt_pct_point(relative_strength.get('IWM_SPY'))}, {breadth_summary}를 고려하면 "
            "지수 추격보다 리더주 선별 대응이 유리합니다."
        )

    strong_sectors = [_coerce_text(item.get("symbol")) for item in sector_rank[:3] if _coerce_text(item.get("symbol"))]
    weak_sectors = [_coerce_text(item.get("symbol")) for item in list(reversed(sector_rank[-3:])) if _coerce_text(item.get("symbol"))]
    sector_label_map = _build_sector_label_map(sector_rank)
    strong_sector_labels = [_format_sector_symbol_with_label(symbol, sector_label_map) for symbol in strong_sectors]
    weak_sector_labels = [_format_sector_symbol_with_label(symbol, sector_label_map) for symbol in weak_sectors]
    close_text = _coerce_text(session_flow.get("close")) or one_liner
    if _normalize_for_compare(close_text) == _normalize_for_compare(one_liner):
        close_text = "종가 기준으로는 지수 방향보다 리더십 유지 여부가 더 중요한 세션이었습니다."

    lines = [
        f"[오늘 미국장 핵심 브리핑] {run_at_kst.strftime('%Y-%m-%d %H:%M:%S')} KST",
        f"- 기준 세션: {market_date_label}",
        "",
        "1) 한줄 결론",
        f"- {one_liner}",
        "",
        "2) 시장 상태",
        f"- 시장 상태: {risk_state_display}",
        f"- 공포탐욕: {int(_safe_float(fear_greed_score, 50) or 50)}/100 ({fear_greed_label}{fear_greed_source_suffix})",
        f"- 구조 해석: {_coerce_text(market_structure.get('label')) or '혼조'} / {_coerce_text(market_structure.get('note')) or one_liner}",
        "",
        "3) Session Flow",
        f"- 장전: {_coerce_text(session_flow.get('premarket')) or (insight_bullets[0] if insight_bullets else headline)}",
        f"- 정규장: {_coerce_text(session_flow.get('regular')) or one_liner}",
        f"- 마감: {close_text}",
        "",
        "4) Index Snapshot",
        _format_snapshot_line("NASDAQ100", dict(benchmarks.get("NASDAQ100") or {})),
        _format_snapshot_line("S&P500", dict(benchmarks.get("S&P500") or {})),
        _format_snapshot_line("DOW", dict(benchmarks.get("DOW") or {})),
        _format_snapshot_line("RUSSELL2000", dict(benchmarks.get("RUSSELL2000") or {})),
        _format_snapshot_line("VIX", dict(benchmarks.get("VIX") or {})),
    ]
    lines.extend(_build_index_interpretation_lines(benchmarks))
    lines += [
        "",
        "5) Macro Snapshot",
        _format_snapshot_line("10Y", dict(macro.get("10Y") or {})),
        _format_snapshot_line("DXY", dict(macro.get("DXY") or {})),
        _format_snapshot_line("USD/KRW", dict(macro.get("USD/KRW") or {})),
        _format_snapshot_line("Gold", dict(macro.get("Gold") or {})),
        _format_snapshot_line("WTI", dict(macro.get("WTI") or {})),
        _format_snapshot_line("BTC", dict(macro.get("BTC") or {})),
    ]
    lines.extend(_build_macro_interpretation_lines(macro))
    lines += [
        "",
        "6) Market Structure",
        f"- Breadth: {breadth_summary}",
        f"- Relative Strength: QQQ-SPY {_fmt_pct_point(relative_strength.get('QQQ_SPY'))} / IWM-SPY {_fmt_pct_point(relative_strength.get('IWM_SPY'))}",
        f"- Leadership: {_coerce_text(market_structure.get('leadership_summary')) or _coerce_text(market_structure.get('label')) or '혼조'}",
        f"- 해석: {market_structure_text}",
        "",
        "7) Sector Summary",
        f"- 강한 섹터: {', '.join(strong_sector_labels) if strong_sector_labels else 'N/A'}",
        f"- 약한 섹터: {', '.join(weak_sector_labels) if weak_sector_labels else 'N/A'}",
        f"- 해석: {_coerce_text(sector_summary.get('interpretation')) or one_liner}",
        "",
        f"8) Top Movers +{len(gainers)} / -{len(losers)} (max {core_cap})",
        "상승:",
    ]
    if gainers:
        lines.extend([_format_mover_line(row, idx) for idx, row in enumerate(gainers, start=1)])
    else:
        lines.append("- 표시할 상승 종목이 없습니다.")
    lines.append("하락:")
    if losers:
        lines.extend([_format_mover_line(row, idx) for idx, row in enumerate(losers, start=1)])
    else:
        lines.append("- 표시할 하락 종목이 없습니다.")

    lines += ["", f"9) 빠른 분석 대상 (max {quick_cap})"]
    if quick_targets:
        for target in quick_targets[:quick_cap]:
            symbol = _coerce_text(target.get("symbol")) or "-"
            reason = _coerce_text(target.get("reason")) or _coerce_text(target.get("source")) or "주도 후보"
            lines.append(f"- {symbol} — {reason}")
    else:
        lines.append("- 오늘 빠른 분석 대상이 아직 집계되지 않았습니다.")

    return "\n".join(lines)


def _build_report_detail_briefing_text(
    report: Mapping[str, Any],
    *,
    run_at_kst: datetime,
    detail_limit: int,
) -> str:
    limit = max(1, int(detail_limit or DEFAULT_DETAIL_LIMIT))
    market_date_label = _coerce_text(report.get("market_date_label")) or "Latest session"
    breadth_summary = _coerce_text(report.get("breadth_summary"))
    sector_rank = [item for item in list(report.get("sector_rank") or []) if isinstance(item, dict)]
    theme_clusters = [item for item in list(report.get("theme_clusters") or []) if isinstance(item, dict)]
    movers = dict(report.get("movers") or {})
    gainers = [dict(item or {}) for item in list(movers.get("gainers") or [])][:limit]
    losers = [dict(item or {}) for item in list(movers.get("losers") or [])][:limit]

    lines = [
        f"[오늘 미국장 상세 브리핑] {run_at_kst.strftime('%Y-%m-%d %H:%M:%S')} KST",
        f"- 기준 세션: {market_date_label}",
        f"- breadth 요약: {breadth_summary or '상승 섹터 정보 없음'}",
        "",
        "1) 전체 섹터 순위",
    ]

    if sector_rank:
        for row in sector_rank:
            rank = int(_safe_float(row.get("rank"), 0) or 0)
            symbol = _coerce_text(row.get("symbol")) or "-"
            label = _coerce_text(row.get("label")) or "-"
            chg = _fmt_signed(row.get("change_pct"), 2)
            lines.append(f"{rank}. {symbol} {label} | {chg}%")
    else:
        lines.append("- 섹터 데이터가 없습니다.")

    lines += ["", "2) 테마 묶음 요약"]
    if theme_clusters:
        for idx, row in enumerate(theme_clusters, start=1):
            theme = _coerce_text(row.get("theme")) or "-"
            count = int(_safe_float(row.get("count"), 0) or 0)
            symbols = [str(item) for item in list(row.get("sample_symbols") or []) if _coerce_text(item)]
            lines.append(f"{idx}. {theme} | {count}개 | {', '.join(symbols[:4]) if symbols else '-'}")
    else:
        lines.append("- 해당 없음")

    lines += [
        "",
        f"3) Top Movers +{len(gainers)} / -{len(losers)} (max {limit})",
        "상승:",
    ]
    if gainers:
        lines.extend([_format_mover_line(row, idx) for idx, row in enumerate(gainers, start=1)])
    else:
        lines.append("- 표시할 상승 종목이 없습니다.")

    lines.append("하락:")
    if losers:
        lines.extend([_format_mover_line(row, idx) for idx, row in enumerate(losers, start=1)])
    else:
        lines.append("- 표시할 하락 종목이 없습니다.")

    return "\n".join(lines)


def _build_legacy_briefing_text(
    payload: Mapping[str, Any],
    *,
    run_at_kst: datetime,
    detail_limit: int,
) -> str:
    data = dict(payload or {})
    limit = max(1, int(detail_limit or DEFAULT_DETAIL_LIMIT))

    main_card = _extract_card(data, "main_headline")
    insight_card = _extract_card(data, "daily_insight")
    headline = _coerce_text(data.get("headline")) or _coerce_text(main_card.get("subtitle")) or "오늘 미국장 핵심 흐름"
    market_date_label = _coerce_text(data.get("market_date_label")) or "최신 세션"
    insight_title = _coerce_text(insight_card.get("subtitle")) or "행동 인사이트"
    insight_bullets = _extract_bullet_texts(insight_card, limit=3)
    sector_lines = _format_sector_rank_lines_legacy(data)
    gainers = [item for item in list(data.get("gainers_detail") or []) if isinstance(item, dict)][:limit]
    losers = [item for item in list(data.get("losers_detail") or []) if isinstance(item, dict)][:limit]

    lines = [
        f"[오늘 미국장 데일리 브리핑] {run_at_kst.strftime('%Y-%m-%d %H:%M:%S')} KST",
        f"- 기준 세션: {market_date_label}",
        f"- 헤드라인: {headline}",
        "",
        f"핵심 인사이트: {insight_title}",
    ]

    if insight_bullets:
        lines.extend([f"- {text}" for text in insight_bullets])
    else:
        lines.append("- 핵심 인사이트 데이터가 아직 집계되지 않았습니다.")

    lines += ["", "섹터 강약도"]
    if sector_lines:
        lines.extend(sector_lines)
    else:
        lines.append("- 섹터 데이터가 없습니다.")

    lines += ["", f"주요 등락주 상승 {len(gainers)}개 (요청 {limit})"]
    if gainers:
        lines.extend([_format_mover_line(row, idx) for idx, row in enumerate(gainers, start=1)])
    else:
        lines.append("- 표시할 상승 종목이 없습니다.")

    lines += ["", f"주요 등락주 하락 {len(losers)}개 (요청 {limit})"]
    if losers:
        lines.extend([_format_mover_line(row, idx) for idx, row in enumerate(losers, start=1)])
    else:
        lines.append("- 표시할 하락 종목이 없습니다.")

    return "\n".join(lines)


def build_market_daily_briefing_messages(
    payload: Mapping[str, Any],
    *,
    run_at_kst: datetime,
    detail_limit: int = DEFAULT_DETAIL_LIMIT,
    core_mover_limit: int = DEFAULT_CORE_MOVER_LIMIT,
    quick_target_limit: int = DEFAULT_QUICK_TARGET_LIMIT,
) -> list[str]:
    data = dict(payload or {})
    report = data.get("briefing_report")
    if isinstance(report, dict) and report:
        core = _build_report_core_briefing_text(
            report,
            run_at_kst=run_at_kst,
            detail_limit=detail_limit,
            core_mover_limit=core_mover_limit,
            quick_target_limit=quick_target_limit,
        )
        detail = _build_report_detail_briefing_text(
            report,
            run_at_kst=run_at_kst,
            detail_limit=detail_limit,
        )
        return [core, detail]
    return [_build_legacy_briefing_text(data, run_at_kst=run_at_kst, detail_limit=detail_limit)]


def build_market_daily_briefing_text(
    payload: Mapping[str, Any],
    *,
    run_at_kst: datetime,
    detail_limit: int = DEFAULT_DETAIL_LIMIT,
) -> str:
    # Backward-compatible single text contract for callers/tests that still use one string.
    return "\n\n".join(
        build_market_daily_briefing_messages(
            payload,
            run_at_kst=run_at_kst,
            detail_limit=detail_limit,
            core_mover_limit=DEFAULT_CORE_MOVER_LIMIT,
            quick_target_limit=DEFAULT_QUICK_TARGET_LIMIT,
        )
    )


def build_market_daily_briefing_failure_text(*, run_at_kst: datetime, reason: str) -> str:
    reason_text = _coerce_text(reason) or "unknown_error"
    return (
        f"[오늘 미국장 데일리 브리핑] {run_at_kst.strftime('%Y-%m-%d %H:%M:%S')} KST\n"
        "- 브리핑 생성 실패: 오늘 미국장 payload를 만들지 못했습니다.\n"
        f"- 원인: {reason_text[:400]}\n"
        "- 안내: 다음 전환 알림과 전체 CSV 전송은 계속 진행됩니다."
    )


def _is_section_header_line(line: str) -> bool:
    return bool(re.match(r"^\d+\)\s+\S+", str(line or "").strip()))


def _chunk_lines_with_limit(lines: list[str], *, limit: int) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for line in lines:
        line_text = str(line)
        line_len = len(line_text) + 1
        if line_len > limit:
            if current:
                chunks.append("\n".join(current))
                current = []
                current_len = 0
            start = 0
            while start < len(line_text):
                end = min(start + limit, len(line_text))
                chunks.append(line_text[start:end])
                start = end
            continue
        if current and (current_len + line_len > limit):
            chunks.append("\n".join(current))
            current = [line_text]
            current_len = line_len
        else:
            current.append(line_text)
            current_len += line_len
    if current:
        chunks.append("\n".join(current))
    return chunks


def split_telegram_message_text(text: str, *, chunk_size: int = DEFAULT_CHUNK_SIZE) -> list[str]:
    raw = str(text or "")
    limit = max(1, int(chunk_size))
    if len(raw) <= limit:
        return [raw]
    lines = raw.splitlines()
    if not lines:
        return [raw]

    # Prefer section-boundary splitting first, then line-level split for very large sections.
    blocks: list[list[str]] = []
    current_block: list[str] = []
    for line in lines:
        if _is_section_header_line(line) and current_block:
            blocks.append(current_block)
            current_block = [line]
        else:
            current_block.append(line)
    if current_block:
        blocks.append(current_block)

    chunks: list[str] = []
    current_chunk_lines: list[str] = []
    current_chunk_len = 0

    for block_lines in blocks:
        block_text = "\n".join(block_lines)
        block_len = len(block_text)
        if block_len <= limit:
            extra_len = block_len + (1 if current_chunk_lines else 0)
            if current_chunk_lines and (current_chunk_len + extra_len > limit):
                chunks.append("\n".join(current_chunk_lines))
                current_chunk_lines = list(block_lines)
                current_chunk_len = block_len
            else:
                current_chunk_lines.extend(block_lines)
                current_chunk_len = len("\n".join(current_chunk_lines))
            continue

        if current_chunk_lines:
            chunks.append("\n".join(current_chunk_lines))
            current_chunk_lines = []
            current_chunk_len = 0
        chunks.extend(_chunk_lines_with_limit(block_lines, limit=limit))

    if current_chunk_lines:
        chunks.append("\n".join(current_chunk_lines))
    return chunks or [raw]


def _telegram_api(token: str, method: str) -> str:
    return f"https://api.telegram.org/bot{token}/{method}"


def _telegram_send_message_payload(chat_id: str, text: str) -> bytes:
    payload = {
        "chat_id": _coerce_text(chat_id),
        "text": _coerce_text(text),
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def send_telegram_message(token: str, chat_id: str, text: str, *, chunk_size: int = DEFAULT_CHUNK_SIZE) -> None:
    chunks = split_telegram_message_text(text, chunk_size=chunk_size)
    for chunk_idx, chunk in enumerate(chunks, start=1):
        if not _coerce_text(chunk):
            continue
        success = False
        last_error = ""
        for attempt in range(1, 4):
            try:
                response = requests.post(
                    _telegram_api(token, "sendMessage"),
                    data=_telegram_send_message_payload(chat_id, chunk),
                    headers={"Content-Type": "application/json; charset=utf-8"},
                    timeout=30,
                )
                response.raise_for_status()
                payload = response.json()
                if payload.get("ok"):
                    success = True
                    break
                else:
                    last_error = f"Payload not ok: {payload}"
            except Exception as exc:
                last_error = str(exc)
            
            if attempt < 3:
                time.sleep(2)
        
        if not success:
            print(f"[ERROR] Failed to send Telegram chunk {chunk_idx}/{len(chunks)} after 3 attempts. Last error: {last_error}")


def write_text_artifact(text: str, *, out_dir: Path, run_label: str, suffix: str = "") -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    postfix = f"_{suffix}" if suffix else ""
    output_path = out_dir / f"market_daily_briefing{postfix}_{run_label}.txt"
    output_path.write_text(str(text or ""), encoding="utf-8")
    return output_path


def load_market_daily_payload() -> dict[str, Any]:
    from ui import build_us_market_daily_payload

    payload = build_us_market_daily_payload()
    return dict(payload or {})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Today US market briefing -> Telegram")
    parser.add_argument("--out-dir", default="artifacts/daily_scan/market_briefing", help="Output directory for briefing artifacts")
    parser.add_argument("--detail-limit", type=int, default=DEFAULT_DETAIL_LIMIT, help="Mover detail count for each side (A-2)")
    parser.add_argument("--core-mover-limit", type=int, default=DEFAULT_CORE_MOVER_LIMIT, help="Mover count for each side (A-1)")
    parser.add_argument("--quick-target-limit", type=int, default=DEFAULT_QUICK_TARGET_LIMIT, help="Quick analysis target count for A-1")
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE, help="Telegram message chunk size")
    parser.add_argument("--skip-telegram", action="store_true", help="Build briefing but skip Telegram send")
    parser.add_argument("--dry-run", action="store_true", help="Build briefing and write artifacts only")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_at_kst = datetime.now(KST)
    run_label = run_at_kst.strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out_dir)

    payload_error = ""
    payload: dict[str, Any] | None = None
    try:
        payload = load_market_daily_payload()
    except Exception as exc:
        payload_error = str(exc)
        payload = None

    if payload:
        messages = build_market_daily_briefing_messages(
            payload,
            run_at_kst=run_at_kst,
            detail_limit=int(args.detail_limit),
            core_mover_limit=int(args.core_mover_limit),
            quick_target_limit=int(args.quick_target_limit),
        )
        print("[BRIEFING] Payload build completed.")
    else:
        messages = [
            build_market_daily_briefing_failure_text(
                run_at_kst=run_at_kst,
                reason=payload_error,
            )
        ]
        print(f"[BRIEFING] Payload build failed: {payload_error}")

    artifact_paths: list[Path] = []
    if len(messages) == 1:
        artifact_paths.append(write_text_artifact(messages[0], out_dir=out_dir, run_label=run_label))
    else:
        artifact_paths.append(write_text_artifact(messages[0], out_dir=out_dir, run_label=run_label, suffix="core"))
        artifact_paths.append(write_text_artifact(messages[1], out_dir=out_dir, run_label=run_label, suffix="detail"))
    print("[BRIEFING] Text artifacts saved:", ", ".join(str(path) for path in artifact_paths))

    if args.dry_run or args.skip_telegram:
        print("[BRIEFING] Telegram send skipped by option.")
        return 0

    token = _coerce_text(os.getenv("TELEGRAM_BOT_TOKEN", ""))
    chat_id = _coerce_text(os.getenv("TELEGRAM_CHAT_ID", ""))
    if not token or not chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID must be set")

    print(f"[BRIEFING] Sending Telegram briefing messages: {len(messages)}")
    for idx, text in enumerate(messages, start=1):
        send_telegram_message(token, chat_id, text, chunk_size=int(args.chunk_size))
        print(f"[BRIEFING] Telegram message {idx}/{len(messages)} completed.")
    print("[BRIEFING] Telegram briefing completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
