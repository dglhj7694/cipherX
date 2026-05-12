from __future__ import annotations

import html
from copy import deepcopy
from datetime import datetime
from typing import Any


def _text(value: Any, default: str = "-") -> str:
    text = str(value or "").strip()
    return text if text else default


def _int_text(value: Any) -> str:
    try:
        return str(int(round(float(value))))
    except (TypeError, ValueError):
        return "0"


def _join_items(items: Any, default: str = "-") -> str:
    if isinstance(items, str):
        values = [items]
    elif isinstance(items, (list, tuple)):
        values = list(items)
    else:
        values = []
    cleaned = []
    seen = set()
    for item in values:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        cleaned.append(text)
    return ", ".join(cleaned) if cleaned else default


def _list_items(items: Any) -> list[str]:
    if isinstance(items, str):
        values = [items]
    elif isinstance(items, (list, tuple)):
        values = list(items)
    else:
        values = []
    cleaned = []
    seen = set()
    for item in values:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        cleaned.append(text)
    return cleaned


def _esc(value: Any, default: str = "-") -> str:
    return html.escape(_text(value, default))


def _clamped_int(value: Any, default: int = 0) -> int:
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        number = default
    return max(0, min(100, number))


def _tone_for_judgment(value: Any) -> str:
    label = str(value or "").upper()
    if "SELL" in label:
        return "negative"
    if "BUY" in label:
        return "positive"
    if "WATCH" in label or "WAIT" in label or "HOLD" in label:
        return "warning"
    return "accent"


def _tone_for_impact(value: Any) -> str:
    label = str(value or "").lower()
    if "bear" in label or "risk" in label or "negative" in label:
        return "negative"
    if "bull" in label or "positive" in label:
        return "positive"
    if "mixed" in label or "watch" in label or "neutral" in label:
        return "warning"
    return "muted"


def _badge(label: Any, tone: str = "muted") -> str:
    text = _esc(label, "")
    if not text:
        return ""
    return f"<span class='sigl-badge sigl-badge--{tone}'>{text}</span>"


def _chips(items: Any, *, default: str, tone: str) -> str:
    values = _list_items(items)
    if not values:
        values = [default]
        tone = "muted"
    return "".join(_badge(item, tone) for item in values[:10])


def _metric_card(label: str, value: str, *, tone: str = "accent", width: int | None = None) -> str:
    bar = ""
    if width is not None:
        safe_width = max(0, min(100, int(width)))
        bar = (
            "<div class='sigl-ai-meter'>"
            f"<span class='sigl-ai-meter__fill sigl-ai-meter__fill--{tone}' style='width:{safe_width}%'></span>"
            "</div>"
        )
    return (
        f"<div class='sigl-ai-metric sigl-ai-metric--{tone}'>"
        f"<span>{_esc(label)}</span>"
        f"<strong>{_esc(value)}</strong>"
        f"{bar}"
        "</div>"
    )


def _format_evidence_details(items: Any) -> str:
    if not isinstance(items, (list, tuple)):
        return "- 상세 근거가 비어 있습니다."
    lines = []
    for item in items[:8]:
        if not isinstance(item, dict):
            text = _text(item, "")
            if text:
                lines.append(f"- {text}")
            continue
        category = _text(item.get("category"), "근거")
        observation = _text(item.get("observation"), "")
        interpretation = _text(item.get("interpretation"), "")
        impact = _text(item.get("impact"), "neutral")
        importance = _int_text(item.get("importance"))
        body = observation
        if interpretation and interpretation != "-":
            body = f"{body} → {interpretation}" if body else interpretation
        lines.append(f"- **{category}** [{impact}, {importance}점]: {body or '-'}")
    return "\n".join(lines) if lines else "- 상세 근거가 비어 있습니다."


def _evidence_details_html(items: Any) -> str:
    if not isinstance(items, (list, tuple)) or not items:
        return "<div class='sigl-ai-empty'>상세 근거가 비어 있습니다.</div>"
    cards = []
    for item in items[:10]:
        if not isinstance(item, dict):
            text = _esc(item, "")
            if text:
                cards.append(f"<div class='sigl-ai-evidence-card'><p>{text}</p></div>")
            continue
        category = _esc(item.get("category"), "근거")
        observation = _esc(item.get("observation"), "")
        interpretation = _esc(item.get("interpretation"), "")
        impact = _text(item.get("impact"), "neutral")
        tone = _tone_for_impact(impact)
        importance = _clamped_int(item.get("importance"))
        interpretation_html = (
            f"<p class='sigl-ai-evidence-card__interpretation'>{interpretation}</p>"
            if interpretation and interpretation != "-"
            else ""
        )
        cards.append(
            f"<div class='sigl-ai-evidence-card sigl-ai-evidence-card--{tone}'>"
            "<div class='sigl-ai-evidence-card__top'>"
            f"{_badge(category, tone)}"
            f"<span>{_esc(impact)} · {importance}점</span>"
            "</div>"
            f"<p>{observation or '-'}</p>"
            f"{interpretation_html}"
            "<div class='sigl-ai-meter sigl-ai-meter--compact'>"
            f"<span class='sigl-ai-meter__fill sigl-ai-meter__fill--{tone}' style='width:{importance}%'></span>"
            "</div>"
            "</div>"
        )
    return "<div class='sigl-ai-evidence-grid'>" + "".join(cards) + "</div>"


def _playbook_html(items: Any) -> str:
    if not isinstance(items, (list, tuple)) or not items:
        return "<div class='sigl-ai-empty'>전략 플레이북이 비어 있습니다.</div>"
    cards = []
    for item in items[:5]:
        if not isinstance(item, dict):
            continue
        fit = _clamped_int(item.get("fit"))
        cards.append(
            "<div class='sigl-ai-playbook-card'>"
            "<div class='sigl-ai-playbook-card__top'>"
            f"<strong>{_esc(item.get('style'), '전략')}</strong>"
            f"<span>{fit}점</span>"
            "</div>"
            f"<p>{_esc(item.get('summary'))}</p>"
            "<div class='sigl-ai-playbook-card__rows'>"
            f"<span>진입</span><b>{_esc(item.get('entry'))}</b>"
            f"<span>무효화</span><b>{_esc(item.get('invalidation'))}</b>"
            f"<span>목표</span><b>{_esc(item.get('target'))}</b>"
            "</div>"
            "<div class='sigl-ai-meter sigl-ai-meter--compact'>"
            f"<span class='sigl-ai-meter__fill sigl-ai-meter__fill--accent' style='width:{fit}%'></span>"
            "</div>"
            "</div>"
        )
    if not cards:
        return "<div class='sigl-ai-empty'>전략 플레이북이 비어 있습니다.</div>"
    return "<div class='sigl-ai-playbook-grid'>" + "".join(cards) + "</div>"


def format_ai_signal_report(
    ticker: str,
    ai_result: dict[str, Any],
    *,
    engine_judgment: str = "",
    generated_at: str | None = None,
) -> str:
    result = dict(ai_result or {})
    timestamp = generated_at or datetime.now().isoformat(timespec="seconds")
    playbook = result.get("AI_Strategy_Playbook") or []
    playbook_lines = []
    for item in playbook[:5]:
        if not isinstance(item, dict):
            continue
        style = _text(item.get("style"), "전략")
        fit = _int_text(item.get("fit"))
        summary = _text(item.get("summary"))
        entry = _text(item.get("entry"))
        invalidation = _text(item.get("invalidation"))
        target = _text(item.get("target"))
        playbook_lines.append(
            f"- **{style}** ({fit}점): {summary}\n"
            f"  - 진입: {entry}\n"
            f"  - 무효화: {invalidation}\n"
            f"  - 목표: {target}"
        )
    if not playbook_lines:
        playbook_lines.append("- 전략 플레이북이 비어 있습니다.")

    engine_suffix = f" / 엔진 {engine_judgment}" if engine_judgment else ""
    return (
        f"## {str(ticker or '').upper()} AI분석 리포트\n\n"
        f"- 생성시각: {timestamp}\n"
        f"- 판단: **{_text(result.get('AI_Judgment'), 'NEUTRAL')}**"
        f" / 신뢰도 {_int_text(result.get('AI_Confidence'))}%"
        f" / Bull {_int_text(result.get('AI_Bullish_Score'))}"
        f" / Bear {_int_text(result.get('AI_Bearish_Score'))}{engine_suffix}\n"
        f"- 엔진 비교: {_text(result.get('AI_Agreement'), 'UNAVAILABLE')}"
        f" / {_text(result.get('AI_Disagreement_Type'), 'MIXED')}\n"
        f"- 핵심 근거: {_join_items(result.get('AI_Key_Drivers'))}\n"
        f"- 리스크: {_join_items(result.get('AI_Risk_Flags'), '특이사항 없음')}\n\n"
        f"### 상세 근거\n"
        f"{_format_evidence_details(result.get('AI_Evidence_Details'))}\n\n"
        f"### 반대 근거 / 데이터 한계\n"
        f"- 반대 근거: {_join_items(result.get('AI_Counter_Evidence'), '뚜렷한 반대 근거 없음')}\n"
        f"- 데이터 한계: {_join_items(result.get('AI_Data_Limits'), '특이사항 없음')}\n\n"
        f"### 판단 이유\n"
        f"{_text(result.get('AI_Reason'), 'AI 판단 사유가 비어 있습니다.')}\n\n"
        f"### 대응 전략\n"
        f"{_text(result.get('AI_Trade_Strategy'), '전략 요약이 비어 있습니다.')}\n\n"
        f"- 진입: {_text(result.get('AI_Entry_Plan'))}\n"
        f"- 무효화: {_text(result.get('AI_Invalidation'))}\n"
        f"- 목표: {_text(result.get('AI_Target_Plan'))}\n\n"
        f"### 전략 플레이북\n"
        + "\n".join(playbook_lines)
    )


def format_ai_signal_report_html(
    ticker: str,
    ai_result: dict[str, Any],
    *,
    engine_judgment: str = "",
    generated_at: str | None = None,
) -> str:
    result = dict(ai_result or {})
    ticker_text = str(ticker or "").upper() or "TICKER"
    timestamp = generated_at or datetime.now().isoformat(timespec="seconds")
    judgment = _text(result.get("AI_Judgment"), "NEUTRAL")
    tone = _tone_for_judgment(judgment)
    card_tone = {
        "positive": "sigl-card--positive",
        "negative": "sigl-card--negative",
        "warning": "sigl-card--warning",
    }.get(tone, "sigl-card--accent")
    confidence = _clamped_int(result.get("AI_Confidence"))
    bull = _clamped_int(result.get("AI_Bullish_Score"))
    bear = _clamped_int(result.get("AI_Bearish_Score"))
    agreement = _text(result.get("AI_Agreement"), "UNAVAILABLE")
    disagreement = _text(result.get("AI_Disagreement_Type"), "MIXED")
    engine_html = (
        _metric_card("엔진 비교", f"{agreement} / {disagreement}", tone="muted")
        if not engine_judgment
        else _metric_card("엔진 비교", f"{agreement} / {disagreement} · 엔진 {engine_judgment}", tone="muted")
    )
    return (
        f"<div class='sigl-ai-report sigl-card {card_tone}'>"
        "<div class='sigl-ai-report__hero'>"
        "<div>"
        "<div class='sigl-ai-report__eyebrow'>AI Signal-Assisted</div>"
        f"<h3>{_esc(ticker_text)} AI분석 리포트</h3>"
        f"<p>검증된 보조지표 기반 독립 판단 · {html.escape(str(timestamp))}</p>"
        "</div>"
        f"<div class='sigl-ai-report__judgment sigl-ai-report__judgment--{tone}'>"
        "<span>AI 판단</span>"
        f"<strong>{_esc(judgment)}</strong>"
        "</div>"
        "</div>"
        "<div class='sigl-ai-metric-grid'>"
        f"{_metric_card('신뢰도', f'{confidence}%', tone=tone, width=confidence)}"
        f"{_metric_card('Bull 점수', str(bull), tone='positive', width=bull)}"
        f"{_metric_card('Bear 점수', str(bear), tone='negative', width=bear)}"
        f"{engine_html}"
        "</div>"
        "<div class='sigl-ai-two-col'>"
        "<section class='sigl-ai-panel'>"
        "<h4>핵심 근거</h4>"
        f"<div class='sigl-chip-row'>{_chips(result.get('AI_Key_Drivers'), default='핵심 근거 없음', tone='positive')}</div>"
        "</section>"
        "<section class='sigl-ai-panel'>"
        "<h4>리스크</h4>"
        f"<div class='sigl-chip-row'>{_chips(result.get('AI_Risk_Flags'), default='특이사항 없음', tone='warning')}</div>"
        "</section>"
        "</div>"
        "<section class='sigl-ai-section'>"
        "<div class='sigl-ai-section__head'><h4>상세 근거</h4><span>관측값과 해석을 분리해 표시</span></div>"
        f"{_evidence_details_html(result.get('AI_Evidence_Details'))}"
        "</section>"
        "<div class='sigl-ai-two-col'>"
        "<section class='sigl-ai-panel'>"
        "<h4>반대 근거</h4>"
        f"<div class='sigl-chip-row'>{_chips(result.get('AI_Counter_Evidence'), default='뚜렷한 반대 근거 없음', tone='negative')}</div>"
        "</section>"
        "<section class='sigl-ai-panel'>"
        "<h4>데이터 한계</h4>"
        f"<div class='sigl-chip-row'>{_chips(result.get('AI_Data_Limits'), default='특이사항 없음', tone='muted')}</div>"
        "</section>"
        "</div>"
        "<section class='sigl-ai-section sigl-ai-section--reason'>"
        "<h4>판단 이유</h4>"
        f"<p>{_esc(result.get('AI_Reason'), 'AI 판단 사유가 비어 있습니다.')}</p>"
        "</section>"
        "<section class='sigl-ai-section'>"
        "<div class='sigl-ai-section__head'><h4>대응 전략</h4><span>진입 전 시나리오 확인용</span></div>"
        f"<p class='sigl-ai-strategy-summary'>{_esc(result.get('AI_Trade_Strategy'), '전략 요약이 비어 있습니다.')}</p>"
        "<div class='sigl-ai-action-grid'>"
        f"{_metric_card('진입', _text(result.get('AI_Entry_Plan')), tone='positive')}"
        f"{_metric_card('무효화', _text(result.get('AI_Invalidation')), tone='negative')}"
        f"{_metric_card('목표', _text(result.get('AI_Target_Plan')), tone='accent')}"
        "</div>"
        "</section>"
        "<section class='sigl-ai-section'>"
        "<div class='sigl-ai-section__head'><h4>전략 플레이북</h4><span>스타일별 적합도</span></div>"
        f"{_playbook_html(result.get('AI_Strategy_Playbook'))}"
        "</section>"
        "</div>"
    )


def build_ai_report_message(
    *,
    ticker: str,
    ai_result: dict[str, Any],
    source_analysis_index: int,
    engine_judgment: str = "",
    generated_at: str | None = None,
) -> dict[str, Any]:
    return {
        "role": "assistant",
        "type": "report",
        "ticker": str(ticker or "").upper(),
        "content": format_ai_signal_report(
            ticker,
            ai_result,
            engine_judgment=engine_judgment,
            generated_at=generated_at,
        ),
        "ai_result": deepcopy(dict(ai_result or {})),
        "source_analysis_index": source_analysis_index,
        "engine_judgment": engine_judgment,
        "generated_at": generated_at or datetime.now().isoformat(timespec="seconds"),
    }


def attach_ai_result_to_analysis_message(message: dict[str, Any], ai_result: dict[str, Any]) -> dict[str, Any]:
    updated = deepcopy(dict(message or {}))
    meta = deepcopy(dict(updated.get("meta") or {}))
    meta["ai_signal_assisted"] = deepcopy(dict(ai_result or {}))
    updated["meta"] = meta
    return updated
