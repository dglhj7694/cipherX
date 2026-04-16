from __future__ import annotations

import argparse
import math
import os
import sys
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
DEFAULT_CHUNK_SIZE = 3500


def _safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        numeric = float(value)
        if math.isnan(numeric):
            return default
        return numeric
    except Exception:
        return default


def _coerce_text(value: Any) -> str:
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
        if not isinstance(card, dict):
            continue
        if _coerce_text(card.get("id")) == card_id:
            return card
    return {}


def _extract_bullet_texts(card: Mapping[str, Any], *, limit: int = 3) -> list[str]:
    lines: list[str] = []
    for item in list(card.get("bullets") or []):
        if isinstance(item, dict):
            text = _coerce_text(item.get("text"))
        else:
            text = _coerce_text(item)
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
        if note:
            lines.append(f"{idx}. {label} {delta} ({note})")
        else:
            lines.append(f"{idx}. {label} {delta}")
    return lines


def _format_mover_line(row: Mapping[str, Any], rank: int) -> str:
    symbol = _coerce_text(row.get("symbol")) or "-"
    price = _fmt_price(row.get("price"))
    change_value = _fmt_signed(row.get("change_value"), 2)
    change_pct = _fmt_signed(row.get("change_pct"), 2)
    volume_ratio = _fmt_ratio(row.get("volume_ratio"), 2)
    reason = _coerce_text(row.get("reason")) or "-"
    return f"{rank}. {symbol} | {price} ({change_value}, {change_pct}%) | 거래량 {volume_ratio} | {reason}"


def _format_snapshot_line(display_name: str, entry: Mapping[str, Any]) -> str:
    symbol = _coerce_text(entry.get("symbol"))
    prefix = f"{display_name} ({symbol})" if symbol and symbol != display_name else display_name
    price = _safe_float(entry.get("price"), None)
    change_value = _safe_float(entry.get("change_value"), None)
    change_pct = _safe_float(entry.get("change_pct"), None)
    if display_name == "10Y":
        value_text = f"{(price / 10):.2f}%" if price is not None else "N/A"
        delta_text = f"{(change_value * 10):+.1f}bp" if change_value is not None else f"{_fmt_signed(change_pct, 2)}%"
        return f"- {prefix}: {value_text} ({delta_text})"
    return f"- {prefix}: {_fmt_price(price)} ({_fmt_signed(change_value, 2)}, {_fmt_signed(change_pct, 2)}%)"


def _build_report_briefing_text(
    report: Mapping[str, Any],
    *,
    run_at_kst: datetime,
    detail_limit: int,
) -> str:
    limit = max(1, int(detail_limit or DEFAULT_DETAIL_LIMIT))
    market_date_label = _coerce_text(report.get("market_date_label")) or "Latest session"
    headline = _coerce_text(report.get("headline")) or "오늘 미국장 주요 흐름"

    executive = dict(report.get("executive_summary") or {})
    sentiment = dict(report.get("sentiment") or {})
    risk_state_display = _coerce_text(executive.get("risk_state_display")) or _coerce_text(sentiment.get("risk_state_display")) or _coerce_text(sentiment.get("risk_state")) or "N/A"
    fear_greed_score = sentiment.get("fear_greed_score", executive.get("fear_greed_score"))
    fear_greed_label = _coerce_text(sentiment.get("fear_greed_label") or executive.get("fear_greed_label")) or "N/A"
    short_view = _coerce_text(executive.get("short_view")) or "-"

    benchmarks = dict(report.get("benchmarks") or {})
    macro = dict(report.get("macro") or {})
    relative_strength = dict(report.get("relative_strength") or {})
    sector_rank = [item for item in list(report.get("sector_rank") or []) if isinstance(item, dict)]

    movers = dict(report.get("movers") or {})
    gainers = [dict(item or {}) for item in list(movers.get("gainers") or [])][:limit]
    losers = [dict(item or {}) for item in list(movers.get("losers") or [])][:limit]

    action_points = dict(report.get("action_points") or {})
    insight_bullets = [_coerce_text(item) for item in list(action_points.get("insight_bullets") or []) if _coerce_text(item)]
    watchlist = [_coerce_text(item) for item in list(action_points.get("watchlist") or []) if _coerce_text(item)]
    analysis_actions = [dict(item or {}) for item in list(action_points.get("analysis_actions") or []) if isinstance(item, dict)]
    action_symbols = [_coerce_text(item.get("symbol")) for item in analysis_actions if _coerce_text(item.get("symbol"))]

    lines = [
        f"[오늘 미국장 데일리 브리핑 리포트] {run_at_kst.strftime('%Y-%m-%d %H:%M:%S')} KST",
        f"- 기준 세션: {market_date_label}",
        "",
        "1) Executive Summary",
        f"- 헤드라인: {headline}",
        f"- 시장 상태: {risk_state_display}",
        f"- 공탐지수(Fear/Greed): {int(_safe_float(fear_greed_score, 50) or 50)}/100 ({fear_greed_label})",
        f"- 핵심 한줄: {short_view}",
        "",
        "2) Index Snapshot",
        _format_snapshot_line("NASDAQ100", dict(benchmarks.get("NASDAQ100") or {})),
        _format_snapshot_line("S&P500", dict(benchmarks.get("S&P500") or {})),
        _format_snapshot_line("DOW", dict(benchmarks.get("DOW") or {})),
        _format_snapshot_line("RUSSELL2000", dict(benchmarks.get("RUSSELL2000") or {})),
        _format_snapshot_line("VIX", dict(benchmarks.get("VIX") or {})),
        "",
        "3) Macro Snapshot",
        _format_snapshot_line("10Y", dict(macro.get("10Y") or {})),
        _format_snapshot_line("DXY", dict(macro.get("DXY") or {})),
        _format_snapshot_line("USD/KRW", dict(macro.get("USD/KRW") or {})),
        _format_snapshot_line("Gold", dict(macro.get("Gold") or {})),
        _format_snapshot_line("WTI", dict(macro.get("WTI") or {})),
        _format_snapshot_line("BTC", dict(macro.get("BTC") or {})),
        "",
        "4) Relative Strength",
        f"- QQQ-SPY: {_fmt_pct_point(relative_strength.get('QQQ_SPY'))}",
        f"- IWM-SPY: {_fmt_pct_point(relative_strength.get('IWM_SPY'))}",
        "",
        "5) Sector Strength (강->약)",
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

    lines += [
        "",
        f"6) Top Movers +{len(gainers)} / -{len(losers)} (max {limit})",
        "상승:",
    ]
    if gainers:
        lines.extend([_format_mover_line(row, idx) for idx, row in enumerate(gainers, start=1)])
    else:
        lines.append("- 상승 종목 데이터가 없습니다.")

    lines.append("하락:")
    if losers:
        lines.extend([_format_mover_line(row, idx) for idx, row in enumerate(losers, start=1)])
    else:
        lines.append("- 하락 종목 데이터가 없습니다.")

    lines += [
        "",
        "7) Action Checklist",
    ]
    if insight_bullets:
        lines.extend([f"- 인사이트: {text}" for text in insight_bullets[:5]])
    if watchlist:
        lines.extend([f"- 체크포인트: {text}" for text in watchlist[:4]])
    if action_symbols:
        lines.append(f"- 빠른 분석 대상: {', '.join(action_symbols[:12])}")
    if not insight_bullets and not watchlist and not action_symbols:
        lines.append("- 실행 체크리스트 데이터가 없습니다.")

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
    insight_title = _coerce_text(insight_card.get("subtitle")) or "행동형 인사이트"
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

    lines.append("")
    lines.append("섹터 강약도 (강->약):")
    if sector_lines:
        lines.extend(sector_lines)
    else:
        lines.append("- 섹터 강약도 데이터가 없습니다.")

    lines.append("")
    lines.append(f"주요 등락주 상승 {len(gainers)}개 (요청 상한 {limit}):")
    if gainers:
        lines.extend([_format_mover_line(row, idx) for idx, row in enumerate(gainers, start=1)])
    else:
        lines.append("- 상승 종목 데이터가 없습니다.")

    lines.append("")
    lines.append(f"주요 등락주 하락 {len(losers)}개 (요청 상한 {limit}):")
    if losers:
        lines.extend([_format_mover_line(row, idx) for idx, row in enumerate(losers, start=1)])
    else:
        lines.append("- 하락 종목 데이터가 없습니다.")

    return "\n".join(lines)


def build_market_daily_briefing_text(
    payload: Mapping[str, Any],
    *,
    run_at_kst: datetime,
    detail_limit: int = DEFAULT_DETAIL_LIMIT,
) -> str:
    data = dict(payload or {})
    report = data.get("briefing_report")
    if isinstance(report, dict) and report:
        return _build_report_briefing_text(report, run_at_kst=run_at_kst, detail_limit=detail_limit)
    return _build_legacy_briefing_text(data, run_at_kst=run_at_kst, detail_limit=detail_limit)


def build_market_daily_briefing_failure_text(*, run_at_kst: datetime, reason: str) -> str:
    reason_text = _coerce_text(reason) or "unknown_error"
    return (
        f"[오늘 미국장 데일리 브리핑] {run_at_kst.strftime('%Y-%m-%d %H:%M:%S')} KST\n"
        "- 브리핑 생성 실패: 오늘 미국장 payload를 만들지 못했습니다.\n"
        f"- 원인: {reason_text[:400]}\n"
        "- 안내: 스캐너 전환 알림과 전체 CSV 전송은 계속 진행됩니다."
    )


def split_telegram_message_text(text: str, *, chunk_size: int = DEFAULT_CHUNK_SIZE) -> list[str]:
    raw = str(text or "")
    limit = max(1, int(chunk_size))
    if len(raw) <= limit:
        return [raw]
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for line in raw.splitlines():
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
    return chunks or [raw]


def _telegram_api(token: str, method: str) -> str:
    return f"https://api.telegram.org/bot{token}/{method}"


def send_telegram_message(token: str, chat_id: str, text: str, *, chunk_size: int = DEFAULT_CHUNK_SIZE) -> None:
    chunks = split_telegram_message_text(text, chunk_size=chunk_size)
    for chunk in chunks:
        if not _coerce_text(chunk):
            continue
        response = requests.post(
            _telegram_api(token, "sendMessage"),
            json={"chat_id": chat_id, "text": chunk},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("ok"):
            raise RuntimeError(f"Telegram sendMessage failed: {payload}")


def write_text_artifact(text: str, *, out_dir: Path, run_label: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / f"market_daily_briefing_{run_label}.txt"
    output_path.write_text(str(text or ""), encoding="utf-8")
    return output_path


def load_market_daily_payload() -> dict[str, Any]:
    from ui import build_us_market_daily_payload

    payload = build_us_market_daily_payload()
    return dict(payload or {})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Today US market detailed briefing -> Telegram")
    parser.add_argument("--out-dir", default="artifacts/daily_scan/market_briefing", help="Output directory for briefing artifacts")
    parser.add_argument("--detail-limit", type=int, default=DEFAULT_DETAIL_LIMIT, help="Mover detail count for each side")
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
        briefing_text = build_market_daily_briefing_text(
            payload,
            run_at_kst=run_at_kst,
            detail_limit=int(args.detail_limit),
        )
        print("[BRIEFING] Payload build completed.")
    else:
        briefing_text = build_market_daily_briefing_failure_text(
            run_at_kst=run_at_kst,
            reason=payload_error,
        )
        print(f"[BRIEFING] Payload build failed: {payload_error}")

    artifact_path = write_text_artifact(briefing_text, out_dir=out_dir, run_label=run_label)
    print(f"[BRIEFING] Text artifact saved: {artifact_path}")

    if args.dry_run or args.skip_telegram:
        print("[BRIEFING] Telegram send skipped by option.")
        return 0

    token = _coerce_text(os.getenv("TELEGRAM_BOT_TOKEN", ""))
    chat_id = _coerce_text(os.getenv("TELEGRAM_CHAT_ID", ""))
    if not token or not chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID must be set")

    print("[BRIEFING] Sending Telegram briefing...")
    send_telegram_message(token, chat_id, briefing_text, chunk_size=int(args.chunk_size))
    print("[BRIEFING] Telegram briefing completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
