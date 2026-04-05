import html
import json
import math
import re
import textwrap
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from company_details import render_company_details
from config import COMMITTEE_NAMES, CONTEXT_WEIGHTS, CTX_LABELS
from localization import (
    localize_action_label,
    localize_committee_name,
    localize_context_label,
    localize_judgment_label,
    localize_regime_label,
    translate_chart_text,
)
from theme import PLOTLY_FONT_FAMILY


SOFT_GREEN = "#63D9A2"
SOFT_RED = "#FF8F96"
SOFT_AMBER = "#F6C35E"
SOFT_BLUE = "#8EA4FF"
SOFT_MUTED = "#94A3B8"


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _us_market_time_text():
    try:
        now_et = datetime.now(ZoneInfo("America/New_York"))
    except Exception:
        return ""
    return now_et.strftime("미국시간 %H:%M ET")


def _esc(value):
    return html.escape(str(value or ""))


def _tone_from_text(value):
    text = str(value or "").upper()
    if any(token in text for token in ("BUY", "\uB9E4\uC218")):
        return "positive"
    if any(token in text for token in ("SELL", "\uB9E4\uB3C4")):
        return "negative"
    if any(token in text for token in ("WATCH", "HOLD", "NEUTRAL", "\uAD00\uB9DD", "\uBCF4\uC720")):
        return "warning"
    return "muted"


def _tone_color(tone):
    return {
        "positive": SOFT_GREEN,
        "negative": SOFT_RED,
        "warning": SOFT_AMBER,
        "accent": SOFT_BLUE,
        "muted": SOFT_MUTED,
    }.get(tone, SOFT_BLUE)


def _badge(label, tone="muted"):
    safe = _esc(label)
    if not safe:
        return ""
    return f"<span class='sigl-badge sigl-badge--{tone}'>{safe}</span>"


def _interpretation_badge_tone(text, default="accent"):
    value = str(text or "").strip()
    if not value:
        return default
    if any(token in value for token in ("상방", "강세", "우세", "회복", "지지", "유입", "돌파", "추세 유지", "매수", "롱")):
        return "positive"
    if any(token in value for token in ("하방", "약세", "이탈", "역풍", "저항", "매도", "숏", "위험", "리스크", "붕괴")):
        return "negative"
    if any(token in value for token in ("대기", "확인", "혼재", "중립", "변동성", "과열", "눌림", "경계")):
        return "warning"
    return default


def _html_block(markup):
    text = textwrap.dedent(str(markup or "")).strip()
    text = re.sub(r"\n[ \t]+(?=<)", "\n", text)
    return text


def _category_chart_height(count, *, min_height=320, per_item=34, extra=120, max_height=None):
    total = max(min_height, extra + max(int(count), 0) * per_item)
    if max_height is not None:
        total = min(total, max_height)
    return total


def _join_html(parts):
    return "".join(_html_block(part) for part in parts if str(part or "").strip())


def _ordered_unique(items):
    seen = set()
    ordered = []
    for item in items:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        ordered.append(text)
    return ordered


def _render_panel_html(inner_html, min_height=240):
    del min_height
    st.markdown(f"<div class='sigl-html-block'>{_html_block(inner_html)}</div>", unsafe_allow_html=True)


def _progress_metric_card(label, value, sub, tone, fill):
    return (
        f"<div class='sigl-metric-card'>"
        f"<p class='sigl-metric-label'>{_esc(label)}</p>"
        f"<p class='sigl-metric-value' style='color:{_tone_color(tone)}'>{_esc(value)}</p>"
        f"<p class='sigl-metric-sub'>{_esc(sub)}</p>"
        f"<div class='sigl-progress'><div class='sigl-progress__fill' style='--fill:{max(0, min(fill, 100)):.1f}%;--tone:{_tone_color(tone)}'></div></div>"
        f"</div>"
    )


def _mini_stat_card(label, value, tone="muted", tooltip=""):
    title_attr = f" title='{_esc(tooltip)}'" if tooltip else ""
    return (
        f"<div class='sigl-metric-card'{title_attr}>"
        f"<p class='sigl-metric-label'>{_esc(label)}</p>"
        f"<p class='sigl-metric-value' style='font-size:1.02rem;color:{_tone_color(tone)}'>{_esc(value)}</p>"
        f"</div>"
    )


def _render_ensemble_gauge(es, chart_key=None):
    gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=es,
        number={"font": {"size": 28, "family": PLOTLY_FONT_FAMILY}},
        gauge={
            "axis": {"range": [-100, 100], "tickwidth": 1, "tickcolor": "#64748B"},
            "bar": {"color": SOFT_BLUE, "thickness": 0.35},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [-100, -30], "color": "rgba(255,143,150,0.24)"},
                {"range": [-30, 30], "color": "rgba(246,195,94,0.18)"},
                {"range": [30, 100], "color": "rgba(99,217,162,0.24)"},
            ],
            "threshold": {"line": {"color": "#E2E8F0", "width": 2}, "thickness": 0.8, "value": es},
        },
    ))
    gauge.update_layout(
        height=180,
        margin=dict(l=6, r=6, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E2E8F0", family=PLOTLY_FONT_FAMILY),
    )
    st.plotly_chart(
        gauge,
        use_container_width=True,
        theme=None,
        config={"displayModeBar": False},
        key=chart_key,
    )


def _risk_size_hint(atr_pct):
    if atr_pct >= 6:
        return "작게", "negative"
    if atr_pct >= 3.5:
        return "축소", "warning"
    return "기본", "positive"


def _bottom_line_text(meta):
    action = localize_action_label(meta.get("action_label", "").strip() or meta.get("judgment", "NEUTRAL"))
    es = _safe_float(meta.get("ensemble_score", 0))
    context = localize_context_label(meta.get("context", 0))
    judgment = str(meta.get("judgment", "")).upper()
    if "BUY" in judgment:
        return f"결론은 {action}입니다. 현재는 매수 우위 구간으로 보이며 ES {es:+.1f}, 시장 맥락은 {context}입니다."
    if "SELL" in judgment:
        return f"결론은 {action}입니다. 지금은 매도 우위 구간으로 보이며 ES {es:+.1f}, 시장 맥락은 {context}입니다."
    if "MIXED" in judgment:
        return f"결론은 {action}입니다. 방향성이 갈리는 구간이라 ES {es:+.1f}, 시장 맥락 {context}를 함께 봐야 합니다."
    return f"결론은 {action}입니다. 추가 확인이 필요한 중립 구간이며 ES {es:+.1f}, 시장 맥락은 {context}입니다."


def _narrative_text(meta):
    rsi = _safe_float(meta.get("rsi", 50))
    wt = _safe_float(meta.get("wt1", 0))
    cmf = _safe_float(meta.get("cmf", 0))
    bbp = _safe_float(meta.get("percent_b", 0.5))
    if rsi >= 70 and wt > 20:
        return "단기 과열 해석이 가능해 추격 진입보다 눌림 확인이 중요합니다."
    if rsi <= 30 and wt < -20:
        return "과매도 해석이 가능하지만 반전 확인 전까지는 분할 대응이 더 안전합니다."
    if cmf > 0.05 and bbp < 0.3:
        return "가격 위치는 낮지만 자금 흐름이 버티고 있어 바닥 탐색 신호로 볼 수 있습니다."
    if cmf < -0.05 and bbp > 0.7:
        return "가격은 높은 편이지만 자금 흐름이 약해 조정 위험을 함께 점검해야 합니다."
    return "추세, 모멘텀, 자금 흐름이 완전히 정렬된 상태는 아니므로 확인 신호를 함께 보는 편이 좋습니다."


def render_price_header(meta, key_prefix="analysis"):
    change = _safe_float(meta.get("price_change", 0))
    change_pct = _safe_float(meta.get("price_change_pct", 0))
    change_class = "up" if change > 0 else ("down" if change < 0 else "flat")
    tone = _tone_from_text(meta.get("judgment") or meta.get("action_label"))
    regime_label = localize_regime_label(meta.get("regime"), meta.get("regime_label"))
    context_label = localize_context_label(meta.get("context", 0))
    action_label = localize_action_label(meta.get("action_label", ""))
    confidence = _safe_float(meta.get("confidence", 0))
    es = _safe_float(meta.get("ensemble_score", 0))
    volume_ratio = _safe_float(meta.get("volume", 0)) / max(_safe_float(meta.get("avg_volume", 1), 1), 1)
    chips = "".join([
        _badge(action_label or localize_judgment_label(meta.get("judgment", "")), tone),
        _badge(f"신뢰도 {confidence:.0f}%", tone),
        _badge(f"맥락 {context_label}", "accent"),
        _badge(f"WT { _safe_float(meta.get('wt1', 0)):.0f}", "positive" if _safe_float(meta.get("wt1", 0)) < -20 else ("negative" if _safe_float(meta.get("wt1", 0)) > 20 else "warning")),
        _badge(f"RSI { _safe_float(meta.get('rsi', 0)):.0f}", "positive" if _safe_float(meta.get("rsi", 0)) < 40 else ("negative" if _safe_float(meta.get("rsi", 0)) > 60 else "warning")),
        _badge(f"거래량 {volume_ratio:.1f}x", "positive" if volume_ratio > 1.5 else "muted"),
        _badge(f"ADX { _safe_float(meta.get('adx', 0)):.0f}", "positive" if _safe_float(meta.get("adx", 0)) > 25 else "muted"),
    ])
    header_html = f"""
    <div class="sigl-card sigl-card--accent">
      <div class="sigl-price-header">
        <div class="sigl-price-top">
          <div>
            <p class="sigl-price-meta">{_esc(meta.get('ticker'))} · {_esc(meta.get('last_date'))} · {_esc(regime_label)} · {_esc(context_label)}</p>
            <p class="sigl-price-value">
              ${_safe_float(meta.get('price', 0)):.2f}
              <span class="sigl-price-change--{change_class}" style="font-size:1.08rem;margin-left:10px;font-weight:800">
                {change:+.2f} ({change_pct:+.2f}%)
              </span>
            </p>
          </div>
          <div class="sigl-focus-stack">
            {_badge(f"ES {es:+.1f}", tone if tone != 'muted' else 'accent')}
            {_badge(f"B:S {_safe_int(meta.get('buy_agree', 0))}:{_safe_int(meta.get('sell_agree', 0))}", "muted")}
            {_badge(_esc(regime_label), "accent")}
          </div>
        </div>
        <div class="sigl-chip-row">{chips}</div>
        <div class="sigl-note">
          <strong>{_esc(_bottom_line_text(meta))}</strong><br>
          <span class="sigl-summary">{_esc(_narrative_text(meta))}</span>
        </div>
      </div>
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)

    buy_total = _safe_float(meta.get("buy_total", 0))
    sell_total = _safe_float(meta.get("sell_total", 0))
    buy_active = _safe_int(meta.get("buy_active", 0))
    sell_active = _safe_int(meta.get("sell_active", 0))
    high_52 = _safe_float(meta.get("high_52w", meta.get("price", 0)), _safe_float(meta.get("price", 0)))
    low_52 = _safe_float(meta.get("low_52w", meta.get("price", 0)), _safe_float(meta.get("price", 0)))
    range_52 = max(high_52 - low_52, 0.01)
    pos_52 = min(max((_safe_float(meta.get("price", 0)) - low_52) / range_52 * 100, 0), 100)

    metric_html = "".join([
        _progress_metric_card("종합 점수", f"{es:+.1f}", f"매수 합의 {buy_active} · 매도 합의 {sell_active}", tone if tone != "muted" else "accent", min(abs(es) / 80 * 100, 100)),
        _progress_metric_card("매수 강도", f"{buy_total:.1f}", f"활성 레이어 {buy_active}/10", "positive", min(buy_total / 40 * 100, 100)),
        _progress_metric_card("매도 강도", f"{sell_total:.1f}", f"활성 레이어 {sell_active}/10", "negative", min(sell_total / 40 * 100, 100)),
        _progress_metric_card("52주 위치", f"{pos_52:.0f}%", f"저점 {low_52:.2f} · 고점 {high_52:.2f}", "accent", pos_52),
    ])
    st.markdown(f"<div class='sigl-grid sigl-grid--4'>{metric_html}</div>", unsafe_allow_html=True)
    _render_ensemble_gauge(es, chart_key=f"{key_prefix}_ensemble_gauge")


def _judgment_panel_height(detail_text="", contrast="", risk_tag_count=0):
    height = 320
    if detail_text:
        height += 80
    if contrast or risk_tag_count:
        height += 90
    return height


def _committee_panel_height(card_count):
    return max(320, 120 + max(int(card_count), 1) * 44)


def _leading_lagging_panel_height(stat_count):
    rows = max(1, (max(int(stat_count), 1) + 3) // 4)
    return max(320, 220 + rows * 58)


def _combined_scan_panel_height(card_count):
    return max(260, 160 + max(int(card_count), 1) * 48)


def _join_reason_phrases(parts):
    cleaned = [str(part).strip() for part in parts if str(part or "").strip()]
    if not cleaned:
        return ""
    def _has_final_consonant(word):
        text = str(word or "").strip()
        if not text:
            return False
        last = text[-1]
        code = ord(last)
        if 0xAC00 <= code <= 0xD7A3:
            return (code - 0xAC00) % 28 != 0
        return False
    if len(cleaned) == 1:
        return cleaned[0]
    if len(cleaned) == 2:
        particle = "과" if _has_final_consonant(cleaned[0]) else "와"
        return f"{cleaned[0]} {particle} {cleaned[1]}"
    return f"{', '.join(cleaned[:-1])}, {cleaned[-1]}"


def _has_final_consonant(word):
    text = str(word or "").strip()
    if not text:
        return False
    last = text[-1]
    code = ord(last)
    if 0xAC00 <= code <= 0xD7A3:
        return (code - 0xAC00) % 28 != 0
    return False


def _topic_text(word):
    text = str(word or "").strip()
    if not text:
        return ""
    particle = "은" if _has_final_consonant(text) else "는"
    return f"{text}{particle}"


def _translate_note_text(text):
    raw = str(text or "").strip()
    if not raw:
        return ""
    translated = translate_chart_text(raw)
    replacements = [
        ("macro backdrop stayed risk-off", "거시 환경이 위험회피 쪽에 머물렀습니다"),
        ("macro pressure magnitude stayed elevated", "거시 압력이 높은 상태로 유지됐습니다"),
        ("market turn stack turned defensive early", "시장 전환 스택이 초기에 방어적으로 기울었습니다"),
        ("continuation-quality stack stayed aligned", "추세 지속형 시그널 정렬이 유지됐습니다"),
        ("leader / theme-stock mode stayed active", "리더주·테마주 강세 흐름이 유지됐습니다"),
        ("leader stock looked extended, but breakdown confirmation was incomplete", "리더주 과열 신호는 있었지만 하락 확증은 부족했습니다"),
        ("breakdown confirmation was incomplete", "하락 확증은 아직 부족했습니다"),
        ("Money veto: breakout quality deteriorated", "수급 질이 약해져 돌파 신뢰도가 떨어졌습니다"),
        ("Money veto: downside follow-through deteriorated", "하락 추종력이 약해져 매도 신뢰도가 떨어졌습니다"),
        ("Blow-off top detected - take profit / sell bias", "급등 과열 구간이 감지돼 차익실현 우위로 봤습니다"),
        ("BUY with caution", "매수는 가능하지만 보수적으로 접근해야 합니다"),
        ("SELL with caution", "매도는 가능하지만 보수적으로 확인해야 합니다"),
        ("RISK WARNING / trim or tighten stops", "리스크 경고: 비중 축소 또는 손절선 조정"),
        ("CONTINUATION WATCH / pullback-entry candidate", "추세 지속 관찰: 눌림목 진입 후보"),
        ("REDUCE / wait for deeper breakdown confirmation", "비중 축소: 더 깊은 하락 확증 확인 필요"),
        ("TAKE_PROFIT / SELL", "차익실현 / 매도 우위"),
        ("caution", "주의"),
        ("risk-off", "위험회피"),
        ("risk-on", "위험선호"),
    ]
    for src, dst in replacements:
        translated = translated.replace(src, dst)
    translated = translated.replace("|", " · ")
    translated = translated.replace(";", " · ")
    translated = re.sub(r"예측(?=[+-]\d)", "예측 ", translated)
    translated = re.sub(r"\s{2,}", " ", translated).strip(" .")
    return translated


def _root_reason_parts(meta, side):
    parts = []
    if side == "buy":
        if meta.get("bullish_gap_reversal"):
            parts.append("갭다운 이후 회복 패턴이 확인됐고")
        if meta.get("diag_support_hold") or meta.get("box_support_hold") or meta.get("channel_support_hold"):
            parts.append("핵심 지지 구조가 유지됐고")
        if meta.get("triangle_breakout_bull") or meta.get("box_breakout_bull") or meta.get("channel_breakout_bull"):
            parts.append("상방 돌파 구조가 확인됐고")
        if _safe_float(meta.get("continuation_buy_score", 0)) >= 1.5:
            parts.append("추세 지속형 매수 신호가 유지됐고")
        if _safe_float(meta.get("trend_inflection_buy_score", 0)) >= 1.5:
            parts.append("초기 상승 전환 신호가 포착됐고")
        if _safe_float(meta.get("price_change_pct", 0)) >= 2 and (_safe_float(meta.get("volume", 0)) / max(_safe_float(meta.get("avg_volume", 1), 1), 1)) >= 1.2:
            parts.append("거래량을 동반한 상승이 나왔기 때문입니다")
    else:
        if meta.get("bearish_gap_failure"):
            parts.append("갭업 실패 패턴이 확인됐고")
        if meta.get("diag_breakdown_bear") or meta.get("box_breakdown_bear") or meta.get("channel_breakdown_bear") or meta.get("triangle_breakdown_bear"):
            parts.append("핵심 지지 구조 이탈이 나타났고")
        if _safe_float(meta.get("continuation_sell_score", 0)) >= 1.5:
            parts.append("매도 압력이 누적됐고")
        if _safe_float(meta.get("trend_inflection_sell_score", 0)) >= 1.5 or _safe_float(meta.get("market_turn_bear_score", 0)) >= 1.5:
            parts.append("초기 약세 전환 신호가 감지됐고")
        volume_ratio = _safe_float(meta.get("volume", 0)) / max(_safe_float(meta.get("avg_volume", 1), 1), 1)
        if _safe_float(meta.get("price_change_pct", 0)) <= -2 and volume_ratio >= 1.2:
            parts.append("거래량을 동반한 하락이 나왔기 때문입니다")
    if not parts:
        return []
    if not parts[-1].endswith("니다") and not parts[-1].endswith("입니다"):
        parts[-1] = parts[-1].rstrip("고") + "기 때문입니다"
    return parts


def _macro_pressure_help(meta):
    pressure = _safe_float(meta.get("macro_pressure_score", 0))
    if abs(pressure) < 1.0:
        return ""
    components = []
    vix_score = _safe_float(meta.get("vix_pressure_score", 0))
    tnx_score = _safe_float(meta.get("tnx_pressure_score", 0))
    dxy_score = _safe_float(meta.get("dxy_pressure_score", 0))
    breadth_score = _safe_float(meta.get("market_breadth_score", 0))

    if pressure > 0:
        if meta.get("vix_risk_off"):
            components.append("VIX 부담")
        if meta.get("tnx_headwind"):
            components.append("고금리 부담")
        if meta.get("dxy_headwind"):
            components.append("달러 강세 부담")
        if meta.get("breadth_risk_off") or breadth_score < -0.5:
            components.append("시장 breadth 약세")
    else:
        if meta.get("vix_risk_on"):
            components.append("VIX 완화")
        if meta.get("tnx_tailwind"):
            components.append("금리 완화")
        if meta.get("dxy_tailwind"):
            components.append("달러 완화")
        if meta.get("breadth_risk_on") or breadth_score > 0.5:
            components.append("시장 breadth 확산")

    if not components:
        if pressure > 0:
            if vix_score >= 0.4:
                components.append("VIX 부담")
            if (tnx_score * 0.8) >= 0.3:
                components.append("고금리 부담")
            if (dxy_score * 0.8) >= 0.3:
                components.append("달러 강세 부담")
            if breadth_score < -0.5:
                components.append("시장 breadth 약세")
        else:
            if vix_score <= -0.4:
                components.append("VIX 완화")
            if (tnx_score * 0.8) <= -0.3:
                components.append("금리 완화")
            if (dxy_score * 0.8) <= -0.3:
                components.append("달러 완화")
            if breadth_score > 0.5:
                components.append("시장 breadth 확산")

    if not components:
        off_count = _safe_int(meta.get("macro_risk_off_count", 0))
        on_count = _safe_int(meta.get("macro_risk_on_count", 0))
        if pressure > 0:
            return f"거시 압력은 VIX, 금리, 달러, 시장 breadth 가운데 부담 요인이 겹친 결과입니다. 현재는 부담 신호가 {max(off_count, 1)}개 확인됐습니다."
        return f"거시 압력은 VIX, 금리, 달러, 시장 breadth 가운데 우호 요인이 겹친 결과입니다. 현재는 우호 신호가 {max(on_count, 1)}개 확인됐습니다."

    return f"거시 압력은 {_join_reason_phrases(components[:4])}이 함께 작용한 결과입니다."


def _signal_meaning(label):
    text = str(label or "").strip()
    token = text.lower()
    rules = [
        (["3일연속↓", "3 day"], "며칠째 약한 흐름이 이어져 단기 매도 압력이 누적됐다는 뜻입니다."),
        (["stoch과매도", "stochastic reached oversold", "stoch oversold"], "스토캐스틱이 과매도권에 들어가 단기 반등 가능성도 함께 열려 있다는 뜻입니다."),
        (["stochastic buy signal"], "스토캐스틱 기준 반등 시도가 시작됐다는 뜻입니다."),
        (["bb하단붕괴", "lower bollinger band walk", "fell below lower bollinger"], "볼린저 하단을 따라 내려가며 약세 압력이 이어졌다는 뜻입니다."),
        (["macd bearish centerline cross"], "MACD가 기준선 아래로 내려가며 중기 모멘텀이 약해졌다는 뜻입니다."),
        (["fell below 20", "20 dma", "20일선"], "단기 기준선인 20일선을 밑돌아 단기 추세가 약해졌다는 뜻입니다."),
        (["fell below 50", "50 dma", "50일선"], "중기 기준선인 50일선을 이탈해 추세 훼손 가능성이 커졌다는 뜻입니다."),
        (["directional movement crossover bearish"], "방향성 지표에서 하락 쪽 힘이 상승 쪽 힘을 앞섰다는 뜻입니다."),
        (["expansion breakdown", "expansion pivot sell"], "변동성 확장과 함께 하락 압력이 커졌다는 뜻입니다."),
        (["new 52 week closing high"], "장기 추세가 여전히 강하다는 뜻입니다."),
        (["pocket pivot"], "거래량을 동반한 선도성 매수 신호로 해석할 수 있습니다."),
        (["shooting star"], "윗꼬리 매물이 나와 단기 저항 가능성을 보여줍니다."),
        (["multi", "다중시간대약세"], "여러 시간대 흐름이 동시에 약해졌다는 뜻입니다."),
        (["gap"], "시가 급등락 이후 가격이 그 방향을 유지하지 못했는지 확인해야 한다는 뜻입니다."),
        (["breakdown"], "지지 이탈이 나와 추가 약세를 경계해야 한다는 뜻입니다."),
        (["breakout"], "저항 돌파가 나와 추세 재개 가능성을 높게 본다는 뜻입니다."),
        (["support"], "지지선이 방어되는지 보는 신호입니다."),
        (["resistance"], "저항대에서 되밀릴 가능성을 보는 신호입니다."),
    ]
    for keywords, message in rules:
        if any(keyword in token or keyword in text for keyword in keywords):
            return message
    return "단기 방향성을 판단하는 데 참고되는 기술 신호입니다."


def _build_signal_reason_text(meta, side):
    items = _recent_signal_items(meta, limit=6)
    if not items:
        return ""
    desired_tone = "negative" if side == "sell" else "positive"
    selected = [(label, tone) for label, tone in items if tone == desired_tone][:2]
    if not selected:
        selected = items[:2]
    if not selected:
        return ""
    parts = []
    for label, _ in selected:
        parts.append(f"{label} 신호가 나왔고, {_signal_meaning(label)}")
    return " ".join(parts)


def _build_indicator_reason_text(meta, side):
    notes = []
    slowk = _safe_float(meta.get("slowk", 50))
    rsi = _safe_float(meta.get("rsi", 50))
    percent_b = _safe_float(meta.get("percent_b", 0.5))
    volume_ratio = _safe_float(meta.get("volume", 0)) / max(_safe_float(meta.get("avg_volume", 1), 1), 1)
    macd_hist = _safe_float(meta.get("macd_hist", 0))

    if side == "sell":
        if macd_hist < 0:
            notes.append("MACD 히스토그램도 음수권이라 모멘텀이 약한 편입니다.")
        if percent_b <= 0.2:
            notes.append("주가가 볼린저 하단 부근에 있어 약세 압력이 이어진 흔적이 보입니다.")
        if volume_ratio >= 1.2 and _safe_float(meta.get("price_change_pct", 0)) < 0:
            notes.append(f"거래량도 평균 대비 {volume_ratio:.1f}배 수준이라 하락 강도가 약하지 않았습니다.")
        if slowk <= 20 or rsi <= 35:
            notes.append("다만 Slow Stochastic과 RSI는 과매도권에 가까워 단기 반등 가능성도 함께 열려 있습니다.")
    else:
        if macd_hist > 0:
            notes.append("MACD 히스토그램이 플러스권이라 모멘텀은 아직 버티는 편입니다.")
        if percent_b >= 0.8:
            notes.append("주가가 볼린저 상단 부근이라 추세는 강하지만 단기 과열은 경계해야 합니다.")
        if volume_ratio >= 1.2 and _safe_float(meta.get("price_change_pct", 0)) > 0:
            notes.append(f"거래량도 평균 대비 {volume_ratio:.1f}배 수준이라 상승 강도 확인에 도움이 됩니다.")
        if slowk <= 20 or rsi <= 35:
            notes.append("Slow Stochastic과 RSI는 과매도권이라 기술적 반등 여지도 열려 있습니다.")
    return " ".join(notes[:2])


def _normalize_compare_text(text):
    normalized = str(text or "").strip()
    if not normalized:
        return ""
    normalized = re.sub(r"ES\s*=\s*[+-]?\d+(?:\.\d+)?\s*·\s*", "", normalized)
    normalized = re.sub(r"예측\s*[+-]?\d+(?:\.\d+)?\s*·\s*", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip(" ·.")


def _judgment_code(meta, title=""):
    haystack = " ".join(
        str(value or "")
        for value in (
            meta.get("action_label", ""),
            meta.get("judgment", ""),
            meta.get("pre_veto_judgment", ""),
            title,
        )
    ).upper()
    if "STRONG_BUY" in haystack or "강한 매수" in haystack:
        return "STRONG_BUY"
    if "WATCH_BUY" in haystack or "매수 관찰" in haystack:
        return "WATCH_BUY"
    if "BUY" in haystack or "매수 우위" in haystack:
        return "BUY"
    if "STRONG_SELL" in haystack or "강한 매도" in haystack:
        return "STRONG_SELL"
    if "WATCH_SELL" in haystack or "매도 관찰" in haystack:
        return "WATCH_SELL"
    if "SELL" in haystack or "매도 우위" in haystack:
        return "SELL"
    if "MIXED" in haystack or "혼조" in haystack:
        return "MIXED"
    return "NEUTRAL"


def _display_action_title(meta, fallback_title=""):
    code = _judgment_code(meta, fallback_title)
    return {
        "STRONG_BUY": "강한 매수",
        "BUY": "매수 우위",
        "WATCH_BUY": "매수 관찰",
        "WATCH_SELL": "리스크 경고",
        "SELL": "매도 우위",
        "STRONG_SELL": "강한 매도",
        "MIXED": "혼조",
        "NEUTRAL": "중립",
    }.get(code, fallback_title or "중립")


def _format_level_list(levels):
    return ", ".join(f"{level:.2f}" for level in levels if level > 0)


def _level_specs(meta):
    return [
        ("VAL", meta.get("vp_val"), "거래량 하단 지지"),
        ("POC", meta.get("vp_poc"), "거래량 중심"),
        ("VAH", meta.get("vp_vah"), "거래량 상단 저항"),
        ("20일선", meta.get("ma20"), "단기 기준선"),
        ("50일선", meta.get("ma50"), "중기 기준선"),
        ("200일선", meta.get("ma200"), "장기 기준선"),
        ("Fib 61.8%", meta.get("fib_618"), "핵심 되돌림"),
        ("Fib 50%", meta.get("fib_50"), "중립 되돌림"),
        ("Fib 38.2%", meta.get("fib_382"), "얕은 되돌림"),
        ("볼린저 하단", meta.get("bb_low"), "볼밴 하단"),
        ("볼린저 상단", meta.get("bb_up"), "볼밴 상단"),
        ("채널 하단", meta.get("price_channel_low"), "가격 채널 지지"),
        ("채널 상단", meta.get("price_channel_up"), "가격 채널 저항"),
    ]


def _collect_support_resistance_levels(meta):
    price = _safe_float(meta.get("price", 0))
    supports = []
    resistances = []
    for label, raw_value, note in _level_specs(meta):
        value = _safe_float(raw_value, float("nan"))
        if not math.isfinite(value) or value <= 0:
            continue
        item = {
            "label": label,
            "value": round(value, 2),
            "note": note,
            "distance": abs(price - value),
        }
        if value <= price:
            supports.append(item)
        if value >= price:
            resistances.append(item)

    def _dedupe_and_sort(items):
        picked = []
        seen = set()
        for item in sorted(items, key=lambda row: (row["distance"], row["value"])):
            key = round(item["value"], 2)
            if key in seen:
                continue
            seen.add(key)
            picked.append(item)
        return picked

    return _dedupe_and_sort(supports), _dedupe_and_sort(resistances)


def _extract_named_levels(meta):
    supports, resistances = _collect_support_resistance_levels(meta)
    return (
        [(item["label"], item["value"]) for item in supports[:3]],
        [(item["label"], item["value"]) for item in resistances[:3]],
    )


def _extract_price_levels(meta):
    supports_named, resistances_named = _extract_named_levels(meta)
    supports = [value for _, value in supports_named]
    resistances = [value for _, value in resistances_named]
    return supports, resistances


def _build_level_reason_points(meta, side):
    supports_named, resistances_named = _extract_named_levels(meta)
    reasons = []
    if side == "buy":
        if supports_named:
            label, value = supports_named[0]
            reasons.append(f"가장 가까운 지지선은 {label} {value:.2f}로, 이 구간을 지키면 매수 시나리오가 유지됩니다.")
        if resistances_named:
            label, value = resistances_named[0]
            reasons.append(f"첫 저항은 {label} {value:.2f}로, 이 구간 돌파가 나오면 추세 재개 확인에 도움이 됩니다.")
    else:
        if supports_named:
            label, value = supports_named[0]
            reasons.append(f"가장 가까운 지지선은 {label} {value:.2f}로, 이 구간 이탈이 이어지면 약세 해석이 더 강해집니다.")
        if resistances_named:
            label, value = resistances_named[0]
            reasons.append(f"첫 저항은 {label} {value:.2f}로, 이 구간 회복 실패가 이어지면 매도 우위 해석에 힘이 실립니다.")
    return reasons


def _build_level_focus_text(meta, side):
    supports_named, resistances_named = _extract_named_levels(meta)
    if side == "buy":
        if supports_named and resistances_named:
            return f"가까운 지지선은 {supports_named[0][0]} {supports_named[0][1]:.2f}, 첫 저항은 {resistances_named[0][0]} {resistances_named[0][1]:.2f}입니다."
        if supports_named:
            return f"가까운 지지선은 {supports_named[0][0]} {supports_named[0][1]:.2f}입니다."
        if resistances_named:
            return f"첫 저항은 {resistances_named[0][0]} {resistances_named[0][1]:.2f}입니다."
    else:
        if supports_named and resistances_named:
            return f"가까운 지지선은 {supports_named[0][0]} {supports_named[0][1]:.2f}, 첫 회복 확인선은 {resistances_named[0][0]} {resistances_named[0][1]:.2f}입니다."
        if supports_named:
            return f"가까운 지지선은 {supports_named[0][0]} {supports_named[0][1]:.2f}입니다."
        if resistances_named:
            return f"첫 회복 확인선은 {resistances_named[0][0]} {resistances_named[0][1]:.2f}입니다."
    return ""


def _compress_decisive_ma_labels(labels, side):
    labels = list(labels or [])
    if not labels:
        return labels

    if side == "buy":
        ma_family = ["20일선 위 유지", "50일선 위 유지", "200일선 위 유지", "중장기 정배열"]
        replacement = "200일선 위 유지" if "200일선 위 유지" in labels else (
            "중장기 정배열" if "중장기 정배열" in labels else (
                "50일선 위 유지" if "50일선 위 유지" in labels else "20일선 위 유지"
            )
        )
    else:
        ma_family = ["20일선 하회", "50일선 하회", "200일선 하회", "중장기 역배열"]
        replacement = "200일선 하회" if "200일선 하회" in labels else (
            "중장기 역배열" if "중장기 역배열" in labels else (
                "50일선 하회" if "50일선 하회" in labels else "20일선 하회"
            )
        )

    if not any(label in labels for label in ma_family):
        return labels

    compressed = []
    inserted = False
    for label in labels:
        if label in ma_family:
            if not inserted:
                compressed.append(replacement)
                inserted = True
            continue
        compressed.append(label)
    return _ordered_unique(compressed)


def _signal_badge_tone(label, direction=""):
    label_text = str(label or "").strip()
    token = f"{direction} {label_text}".lower()
    positive_keywords = [
        "회복", "지지", "돌파", "반등", "매수", "bull", "support", "breakout", "reclaim", "pocket", "상승", "과매도",
    ]
    negative_keywords = [
        "하락", "붕괴", "이탈", "약세", "매도", "bear", "breakdown", "failure", "reject", "gap up", "급락", "3일연속↓",
    ]
    warning_keywords = ["과매수", "중립", "혼조", "watch", "경계", "squeeze"]

    if "sell" in token:
        return "negative"
    if "buy" in token:
        return "positive"
    if any(keyword in token for keyword in negative_keywords):
        return "negative"
    if any(keyword in token for keyword in positive_keywords):
        return "positive"
    if any(keyword in token for keyword in warning_keywords):
        return "warning"
    return "accent"


def _signal_session_date(meta):
    last_date = str(meta.get("last_date", "")).strip()
    if len(last_date) >= 10 and "-" in last_date:
        return last_date[5:].replace("-", "/")
    return ""


def _recent_signal_payload(item):
    if isinstance(item, dict):
        return {
            "key": str(item.get("key", "") or "").strip(),
            "icon": str(item.get("icon", "") or "").strip(),
            "label": str(item.get("label", "") or "").strip(),
            "date": str(item.get("date", "") or "").strip(),
            "direction": str(item.get("dir", "") or "").strip(),
            "is_combined": bool(item.get("is_combined")),
            "desc": str(item.get("desc", "") or "").strip(),
            "meaning": str(item.get("meaning", "") or "").strip(),
        }
    if isinstance(item, (list, tuple)) and len(item) >= 5:
        return {
            "key": "",
            "icon": str(item[0] or "").strip(),
            "label": str(item[1] or "").strip(),
            "date": str(item[2] or "").strip(),
            "direction": str(item[3] or "").strip(),
            "is_combined": bool(item[4]),
            "desc": "",
            "meaning": "",
        }
    return {
        "key": "",
        "icon": "",
        "label": str(item or "").strip(),
        "date": "",
        "direction": "",
        "is_combined": False,
        "desc": "",
        "meaning": "",
    }


def _recent_signal_payloads(meta, limit=3):
    recent = list(meta.get("recent_signals") or []) + list(meta.get("derived_signal_events") or [])
    target_date = _signal_session_date(meta)

    def collect(items, date_filter=""):
        picked = []
        seen = set()
        for item in reversed(items):
            payload = _recent_signal_payload(item)
            label = payload["label"]
            date_text = payload["date"]
            direction = payload["direction"]
            if date_filter and date_text != date_filter:
                continue
            if not label or label in seen:
                continue
            seen.add(label)
            payload["tone"] = _signal_badge_tone(label, direction)
            picked.append(payload)
            if limit is not None and len(picked) >= limit:
                break
        return picked

    today_items = collect(recent, target_date)
    if today_items:
        return today_items
    return collect(recent, "")


def _recent_signal_items(meta, limit=3):
    return [(payload["label"], payload["tone"]) for payload in _recent_signal_payloads(meta, limit=limit)]


def _recent_signal_labels(meta, limit=3):
    return [label for label, _ in _recent_signal_items(meta, limit=limit)]


def _split_signal_groups(meta, limit=6):
    positive, negative, warning = [], [], []
    for label, tone in _recent_signal_items(meta, limit=limit):
        if tone == "positive":
            positive.append(label)
        elif tone == "negative":
            negative.append(label)
        else:
            warning.append(label)
    return positive, negative, warning


def _signal_explanation_text(payload):
    key = str(payload.get("key") or "").strip()
    label = str(payload.get("label") or "").strip()
    token = f"{key} {label}".lower()
    overrides = [
        (["market_turn_bull", "시장 강세 전환"], "시장 전반이 위험선호 쪽으로 기울기 시작해 개별 종목 신호에도 순풍이 붙기 쉬운 상태입니다."),
        (["market_turn_bear", "시장 약세 전환"], "시장 전반이 방어적으로 돌아서며 개별 종목의 반등 신호가 희석될 수 있는 상태입니다."),
        (["bb_lower_touch", "bb하단터치"], "볼린저 하단에 닿아 과매도/눌림 구간을 시험하는 신호입니다."),
        (["bb_lower_bounce"], "볼린저 하단에서 반등이 나와 단기 지지 확인 가능성을 보여주는 신호입니다."),
        (["bb_lower_break"], "볼린저 하단 이탈로 약세 압력과 변동성 확대를 함께 경계해야 하는 신호입니다."),
        (["bb_upper_touch"], "볼린저 상단에 닿아 단기 과열 또는 저항 테스트를 시사하는 신호입니다."),
        (["vwap_bounce_buy"], "VWAP 부근에서 수급이 다시 살아나며 단기 평균 가격대를 지지로 바꾸려는 신호입니다."),
        (["vwap_reject_sell"], "VWAP 회복에 실패해 단기 평균 가격대가 다시 저항으로 작동할 수 있음을 보여주는 신호입니다."),
        (["fib_618_reclaim"], "61.8% 되돌림을 다시 회복해 하락 압력이 완화되고 반등 시도가 강화되는 신호입니다."),
        (["fib_618_breakdown"], "61.8% 되돌림이 무너지며 단순 조정보다 추세 훼손 가능성이 커졌음을 보여주는 신호입니다."),
        (["volume_poc_breakout"], "거래량 중심 가격대인 POC를 상향 돌파해 매수 우위가 살아나는지 보는 신호입니다."),
        (["volume_poc_breakdown"], "거래량 중심 가격대인 POC를 하향 이탈해 매도 우위가 커지는지 보는 신호입니다."),
        (["vp_val_support"], "VAL 부근 지지가 확인돼 하단 매수세가 실제로 들어오는지 보는 신호입니다."),
        (["vp_vah_resistance"], "VAH 부근 저항이 확인돼 상단 매물이 다시 나오는지 보는 신호입니다."),
    ]
    for keywords, message in overrides:
        if any(keyword in token for keyword in keywords):
            return message
    text = str(payload.get("meaning") or "").strip()
    if text:
        return text
    text = str(payload.get("desc") or "").strip()
    if text:
        return text
    return "단기 방향성을 판단할 때 참고하는 기술 신호입니다."


def _signal_level_context(payload, meta):
    key = str(payload.get("key") or "").strip()
    label = str(payload.get("label") or "").strip()
    token = f"{key} {label}".lower()

    def level(label_text, meta_key):
        value = _safe_float(meta.get(meta_key, 0))
        if value <= 0:
            return ""
        return f"{label_text} ({_fmt_chart_price(value)})"

    rules = [
        (["bb_lower_touch", "bb_lower_bounce", "bb lower", "bb하단"], lambda: level("BB Low", "bb_low")),
        (["bb_upper_touch", "bb_upper_break", "bb upper", "bb상단"], lambda: level("BB Up", "bb_up")),
        (["vwap_bounce_buy", "vwap_reject_sell", "vwap"], lambda: level("VWAP", "vwap")),
        (["fixed_vwap"], lambda: level("고정 VWAP", "fixed_vwap")),
        (["ma20_support", "fell_below_20ma", "20ma"], lambda: level("MA20", "ma20")),
        (["ma50_support", "fell_below_50ma", "50ma"], lambda: level("MA50", "ma50")),
        (["ma200_support", "fell_below_200ma", "200ma"], lambda: level("MA200", "ma200")),
        (["fib_618", "fib 61.8"], lambda: level("Fib 61.8", "fib_618")),
        (["fib_50", "fib 50"], lambda: level("Fib 50", "fib_50")),
        (["fib_382", "fib 38.2"], lambda: level("Fib 38.2", "fib_382")),
        (["volume_poc", "poc breakout", "poc breakdown", "poc"], lambda: level("POC", "vp_poc")),
        (["vp_val_support", "val support", "val"], lambda: level("VAL", "vp_val")),
        (["vp_vah_resistance", "vah resistance", "vah"], lambda: level("VAH", "vp_vah")),
    ]
    for keywords, resolver in rules:
        if any(keyword in token for keyword in keywords):
            resolved = resolver()
            if resolved:
                return resolved
    return ""


def _build_signal_explanation_html(meta, limit=None):
    rows = []
    for payload in _recent_signal_payloads(meta, limit=limit):
        label = str(payload.get("label") or "").strip()
        if not label:
            continue
        rows.append(
            "<div class='sigl-summary' style='margin-top:6px'>"
            f"• <strong>{_esc(label)}</strong>: {_esc(_signal_explanation_text(payload))}"
            "</div>"
        )
    return "".join(rows)


def _build_signal_narrative(meta):
    positive, negative, warning = _split_signal_groups(meta, limit=6)

    if positive and negative:
        pos_text = _join_reason_phrases(positive[:2])
        neg_text = _join_reason_phrases(negative[:2])
        return f"기술적으로는 {pos_text} 같은 강세 신호와 {neg_text} 같은 약세 신호가 동시에 나타나, 단기 방향성은 엇갈린 모습입니다."
    if positive:
        pos_text = _join_reason_phrases(positive[:3])
        if len(positive) >= 2:
            return f"기술적으로는 {pos_text} 등 강세 신호가 확인돼 단기 반등 또는 추세 재개 가능성을 열어두고 있습니다."
        return f"기술적으로는 {pos_text} 신호가 포착돼 단기 반등 가능성을 점검하는 구간입니다."
    if negative:
        neg_text = _join_reason_phrases(negative[:3])
        if len(negative) >= 2:
            return f"기술적으로는 {neg_text} 등 약세 신호가 확인돼 추가 약세 가능성을 경계하는 구간입니다."
        return f"기술적으로는 {neg_text} 신호가 포착돼 하락 압력 확대 여부를 확인하는 구간입니다."
    if warning:
        warn_text = _join_reason_phrases(warning[:2])
        return f"기술적으로는 {warn_text} 신호가 보여 단기 경계가 필요한 구간입니다."
    return ""


def _build_momentum_narrative(meta):
    slowk = _safe_float(meta.get("slowk", 50))
    rsi = _safe_float(meta.get("rsi", 50))
    percent_b = _safe_float(meta.get("percent_b", 0.5))

    if slowk <= 20 or rsi <= 35:
        if percent_b <= 0.15:
            return "현재 Slow Stochastic과 RSI는 과매도권에 가깝고, 주가도 볼린저 하단 부근이라 기술적 반등 가능성을 함께 열어두고 있습니다."
        return "현재 Slow Stochastic과 RSI는 과매도권에 가까워 단기 반등 가능성을 함께 열어두고 있습니다."
    if slowk >= 80 or rsi >= 65:
        if percent_b >= 0.85:
            return "현재 Slow Stochastic과 RSI는 과열권에 가깝고, 주가도 볼린저 상단 부근이라 단기 숨고르기 가능성을 함께 경계해야 합니다."
        return "현재 Slow Stochastic과 RSI는 과열권에 가까워 단기 과열 부담을 함께 반영해야 합니다."
    return ""


def _build_recap_headline(meta):
    ticker = str(meta.get("ticker", "")).upper()
    signal_items = _recent_signal_items(meta, limit=2)
    change_pct = _safe_float(meta.get("price_change_pct", 0))

    if signal_items:
        lead_label, lead_tone = signal_items[0]
        if lead_tone == "positive":
            if abs(change_pct) >= 2:
                return f"{ticker}, {abs(change_pct):.2f}% 움직임 속 {lead_label} 포착"
            return f"{ticker}, {lead_label} 신호 포착"
        if lead_tone == "negative":
            if abs(change_pct) >= 2:
                return f"{ticker}, {abs(change_pct):.2f}% 움직임 속 {lead_label} 경고"
            return f"{ticker}, {lead_label} 신호로 약세 경계"
        return f"{ticker}, {lead_label} 확인된 흐름"
    if change_pct >= 2:
        return f"{ticker}, 강한 상승 뒤 추세 판단 구간"
    if change_pct <= -2:
        return f"{ticker}, 큰 폭 하락 뒤 반응 확인 구간"
    return f"{ticker}, 기술적 판단 요약"


def _build_judgment_recap(meta, title):
    ticker = str(meta.get("ticker", "")).upper()
    date_text = str(meta.get("last_date", "")).strip()
    change_pct = _safe_float(meta.get("price_change_pct", 0))
    volume_ratio = _safe_float(meta.get("volume", 0)) / max(_safe_float(meta.get("avg_volume", 1), 1), 1)
    supports_named, resistances_named = _extract_named_levels(meta)
    supports, resistances = _extract_price_levels(meta)
    signal_narrative = _build_signal_narrative(meta)
    momentum_narrative = _build_momentum_narrative(meta)

    if change_pct >= 0.2:
        move_text = f"{change_pct:+.2f}% 상승"
    elif change_pct <= -0.2:
        move_text = f"{change_pct:+.2f}% 하락"
    else:
        move_text = f"{change_pct:+.2f}% 보합권"

    if volume_ratio >= 1.8:
        volume_text = f"거래량은 평소 대비 {volume_ratio:.1f}배로 크게 늘었습니다."
    elif volume_ratio >= 1.15:
        volume_text = f"거래량은 평소 대비 {volume_ratio:.1f}배로 다소 늘었습니다."
    elif volume_ratio <= 0.7:
        volume_text = f"거래량은 평소 대비 {volume_ratio:.1f}배로 줄었습니다."
    else:
        volume_text = f"거래량은 평소와 비슷한 {volume_ratio:.1f}배 수준이었습니다."

    recap = f"{date_text} {ticker}는 {move_text} 마감했고, {volume_text}"
    if signal_narrative:
        recap += f" {signal_narrative}"
    if supports:
        support_text = ", ".join(f"{value:.2f}" for value in supports[:3])
        recap += f" 주요 지지 후보는 {support_text}입니다."
        if supports_named:
            recap += f" 가장 가까운 지지 축은 {supports_named[0][0]} {supports_named[0][1]:.2f}입니다."
    if resistances:
        resistance_text = ", ".join(f"{value:.2f}" for value in resistances[:3])
        recap += f" 저항 후보는 {resistance_text}입니다."
        if resistances_named:
            recap += f" 가장 먼저 봐야 할 회복 구간은 {resistances_named[0][0]} {resistances_named[0][1]:.2f}입니다."
    if momentum_narrative:
        recap += f" {momentum_narrative}"
    return recap


def _build_beginner_explanation(meta, title):
    code = _judgment_code(meta, title)
    tone = _tone_from_text(title)
    market_filter_bias = _safe_float(meta.get("market_filter_bias", 0))
    continuation_buy = _safe_float(meta.get("continuation_buy_score", 0))
    continuation_sell = _safe_float(meta.get("continuation_sell_score", 0))
    downgrade_count = _safe_int(meta.get("downgrade_count", 0))
    buy_level_text = _build_level_focus_text(meta, "buy")
    sell_level_text = _build_level_focus_text(meta, "sell")

    if code == "STRONG_BUY":
        return f"쉽게 말해 상승 흐름이 강하게 유지되고 있어 매수 쪽 근거가 충분한 구간입니다. {buy_level_text} 다만 첫 눌림 없이 추격하면 변동성에 흔들릴 수 있습니다.".strip()
    if code == "BUY":
        tail = " 시장 필터가 일부 부담이지만 전체 흐름은 아직 매수 쪽이 우세합니다." if market_filter_bias < 0 else ""
        level_tail = f" {buy_level_text}" if buy_level_text else ""
        return f"쉽게 말해 지금은 매수 쪽 신호가 더 많아 상승 재개 가능성을 보는 구간입니다.{tail}{level_tail}"
    if code == "WATCH_BUY":
        level_tail = f" {buy_level_text}" if buy_level_text else ""
        return f"쉽게 말해 당장 강하게 사기보다는 눌림이 지지되는지 확인한 뒤 따라붙기 좋은 후보 구간입니다.{level_tail}"
    if code == "WATCH_SELL":
        warnings = []
        if meta.get("bearish_gap_failure"):
            warnings.append("갭업 실패")
        if meta.get("diag_breakdown_bear") or meta.get("box_breakdown_bear") or meta.get("channel_breakdown_bear") or meta.get("triangle_breakdown_bear"):
            warnings.append("지지 구조 약화")
        if continuation_sell >= 1.5:
            warnings.append("매도 압력 확대")
        if _safe_int(meta.get("macro_risk_off_count", 0)) >= 2 or _safe_float(meta.get("macro_pressure_score", 0)) >= 1.5:
            warnings.append("거시 부담")
        warnings_text = _join_reason_phrases(warnings[:2]) or "단기 경고 신호"
        if _safe_float(meta.get("rsi", 50)) <= 35 or _safe_float(meta.get("slowk", 50)) <= 20:
            return f"쉽게 말해 지금은 {warnings_text} 때문에 흔들림을 경계해야 하는 구간입니다. {sell_level_text} 다만 이미 과매도권에 가까워 급락 확정으로 보기보다는 보유분 방어와 반등 확인이 더 중요합니다."
        return f"쉽게 말해 지금은 {warnings_text}이 겹쳐 단기 위험 관리가 필요한 구간입니다. {sell_level_text} 아직 하락 추세가 완전히 굳었다기보다 상승 흐름이 약해졌는지 확인하는 단계에 가깝습니다."
    if code == "SELL":
        tail = " 다만 추세주라면 반등 실패가 이어지는지 한 번 더 확인하는 편이 좋습니다." if meta.get("leader_stock_mode") else ""
        level_tail = f" {sell_level_text}" if sell_level_text else ""
        return f"쉽게 말해 매도 쪽 압력이 더 강해져 상승 흐름이 약해졌다고 보는 구간입니다.{tail}{level_tail}"
    if code == "STRONG_SELL":
        level_tail = f" {sell_level_text}" if sell_level_text else ""
        return f"쉽게 말해 상승 흐름이 상당히 꺾였고 추가 하락 위험이 커져 방어를 우선해야 하는 구간입니다.{level_tail}"
    if code == "MIXED":
        level_tail = f" {buy_level_text or sell_level_text}" if (buy_level_text or sell_level_text) else ""
        return f"쉽게 말해 좋은 신호와 나쁜 신호가 함께 있어 방향을 단정하기 어렵습니다. 서두르기보다 확인이 먼저입니다.{level_tail}"
    base = "쉽게 말해 지금은 확실한 방향성이 약해 관망 쪽이 더 자연스러운 구간입니다."
    if continuation_buy >= 1 and continuation_sell < 1:
        return base + " 다만 매수 신호가 조금 더 살아 있어 눌림 확인은 해볼 수 있습니다."
    if continuation_sell >= 1 and continuation_buy < 1:
        return base + " 다만 매도 압력이 조금 더 강해 무리한 추격은 피하는 편이 좋습니다."
    if tone == "warning" and downgrade_count > 0:
        return base + f" 보호 규칙 때문에 판단이 {downgrade_count}단계 보수적으로 조정됐습니다."
    return base


def _build_action_guide(meta, title):
    code = _judgment_code(meta, title)
    ut_gap = max(_safe_float(meta.get("utbot_stop_atr_gap", 0)), 0.0)
    volume_ratio = _safe_float(meta.get("volume", 0)) / max(_safe_float(meta.get("avg_volume", 1), 1), 1)
    supports_named, resistances_named = _extract_named_levels(meta)
    support_label, support_level = supports_named[0] if supports_named else ("", 0.0)
    resistance_label, resistance_level = resistances_named[0] if resistances_named else ("", 0.0)
    ma20 = _safe_float(meta.get("ma20", 0))
    objective_alignment = str(meta.get("objective_alignment", "MIXED")).upper()
    objective_confidence = _safe_float(meta.get("objective_confidence", 0))
    conflict_layers = _safe_int(meta.get("signal_conflict_layers", 0))
    thin_trade_risk = bool(meta.get("thin_trade_risk"))
    layer_edge = _safe_float(meta.get("buy_total", 0)) - _safe_float(meta.get("sell_total", 0))

    def _level_text(label, value):
        return f"{label} {value:.2f}" if label and value > 0 else ""

    def _guide_tail():
        if thin_trade_risk:
            return " 거래대금이 얇아 어떤 방향이든 신규 대응은 평소보다 작은 비중이 적절합니다."
        if objective_alignment == "CONFLICT":
            return " 다만 객관 차트 엔진이 반대 방향을 가리켜 공격적 확대는 늦추고 종가 확인을 우선하는 편이 좋습니다."
        if conflict_layers >= 3:
            return f" 다만 10개 레이어 중 {conflict_layers}개가 충돌해 한 번에 크게 베팅하기보다 분할 대응이 더 적합합니다."
        if objective_alignment == "ALIGNED" and objective_confidence >= 65 and abs(layer_edge) >= 4:
            if code in {"STRONG_BUY", "BUY", "WATCH_BUY"}:
                return " 객관 차트 엔진과 10개 레이어가 같은 방향이라 확인 신호가 이어지면 비중 확대를 조금 더 자신 있게 검토할 수 있습니다."
            if code in {"WATCH_SELL", "SELL", "STRONG_SELL"}:
                return " 객관 차트 엔진과 10개 레이어가 같은 방향이라 반등 실패나 지지 이탈 시 방어 강도를 더 빠르게 높일 수 있습니다."
            return " 객관 차트 엔진과 10개 레이어가 같은 방향이라 다음 확인 신호의 의미가 더 커졌습니다."
        return ""

    guide_tail = _guide_tail()

    if code == "STRONG_BUY":
        if support_level > 0:
            return f"실전 대응: 추격 매수보다 {support_label} {support_level:.2f} 부근 첫 눌림이 지지되는지 확인한 뒤 분할 진입하는 편이 좋습니다.{guide_tail}"
        return f"실전 대응: 추격 매수보다 첫 눌림이나 장중 지지 확인 후 분할 진입이 유리합니다.{guide_tail}"
    if code == "BUY":
        if ut_gap >= 2.0:
            if support_level > 0:
                return f"실전 대응: 방향은 매수 우위지만 이격이 커서 추격보다 {support_label} {support_level:.2f} 지지 여부를 본 뒤 분할 접근이 좋습니다.{guide_tail}"
            return f"실전 대응: 방향은 매수 우위지만 이격이 커서 추격보다 눌림 확인 후 분할 접근이 좋습니다.{guide_tail}"
        if support_level > 0 and resistance_level > 0:
            return f"실전 대응: {support_label} {support_level:.2f}를 지키는지 보며 분할 진입하고, {resistance_label} {resistance_level:.2f} 돌파가 이어지면 매수 확신을 높여볼 수 있습니다.{guide_tail}"
        return f"실전 대응: 추세가 유지되는지 보며 분할 진입하고, 지지선 이탈 시 빠르게 리스크를 줄이는 접근이 좋습니다.{guide_tail}"
    if code == "WATCH_BUY":
        if support_level > 0:
            trigger_text = _level_text("20일선", ma20) if ma20 > 0 else _level_text(resistance_label, resistance_level)
            if trigger_text:
                return f"실전 대응: {support_label} {support_level:.2f} 지지가 유지되는지 확인한 뒤 소액으로 접근하고, {trigger_text}를 종가 기준으로 회복하면 매수 관점을 강화할 수 있습니다.{guide_tail}"
            return f"실전 대응: {support_label} {support_level:.2f} 지지가 유지되는지 확인한 뒤 소액으로 먼저 접근하는 전략이 좋습니다.{guide_tail}"
        return f"실전 대응: 박스/채널/이평 지지가 유지되는지 확인한 뒤 소액으로 먼저 접근하는 전략이 좋습니다.{guide_tail}"
    if code == "WATCH_SELL":
        parts = []
        if support_level > 0:
            parts.append(f"1차 지지는 {support_label} {support_level:.2f}입니다")
        if ma20 > 0:
            parts.append(f"20일선은 {ma20:.2f}입니다")
        if resistance_level > 0 and resistance_label != "20일선":
            parts.append(f"1차 회복 확인선은 {resistance_label} {resistance_level:.2f}입니다")
        joined = ". ".join(parts)
        if joined:
            return f"실전 대응: 신규 숏보다 보유분 방어가 우선입니다. {joined}. {support_label or '지지선'}을 지키며 반등하고 20일선이나 첫 저항을 종가 기준으로 회복하면 매수 경고는 완화될 수 있고, 반대로 지지 이탈 시 리스크 관리를 더 강하게 가져가는 편이 좋습니다.{guide_tail}"
        return f"실전 대응: 신규 숏보다 기존 보유분의 비중 축소, 손절선 상향, 반등 실패 확인에 초점을 두는 편이 좋습니다.{guide_tail}"
    if code == "SELL":
        if resistance_level > 0:
            return f"실전 대응: 반등이 나오더라도 {resistance_label} {resistance_level:.2f} 회복 실패가 이어지는지 확인하면서 비중 축소를 우선하는 편이 좋습니다.{guide_tail}"
        return f"실전 대응: 반등이 나와도 저항 회복 실패가 이어지는지 확인하면서 비중 축소를 우선하는 편이 좋습니다.{guide_tail}"
    if code == "STRONG_SELL":
        if support_level > 0 and resistance_level > 0:
            return f"실전 대응: 방어가 우선입니다. {support_label} {support_level:.2f} 이탈이 이어지면 손실 확대를 막는 쪽에 집중하고, 반대로 {resistance_label} {resistance_level:.2f}를 종가 기준으로 회복하기 전까지는 공격적 대응을 늦추는 편이 좋습니다.{guide_tail}"
        return f"실전 대응: 방어가 우선입니다. 손실 확대를 막기 위해 현금 비중 확대나 빠른 정리가 더 중요합니다.{guide_tail}"
    if code == "MIXED":
        if support_level > 0 and resistance_level > 0:
            return f"실전 대응: 방향 베팅보다 {support_label} {support_level:.2f} 지지와 {resistance_label} {resistance_level:.2f} 돌파 여부를 확인한 뒤 대응하는 편이 좋습니다.{guide_tail}"
        return f"실전 대응: 방향 베팅보다 확인 신호를 기다리며 포지션 크기를 줄이는 편이 좋습니다.{guide_tail}"
    if volume_ratio <= 0.7:
        return f"실전 대응: 거래량이 약해 신호 신뢰도가 낮을 수 있으니 무리한 진입보다 관망이 낫습니다.{guide_tail}"
    if support_level > 0 and resistance_level > 0:
        return f"실전 대응: {support_label} {support_level:.2f} 지지와 {resistance_label} {resistance_level:.2f} 회복 여부가 확인되기 전까지는 작은 포지션으로 대응하거나 관망하는 편이 좋습니다.{guide_tail}"
    return f"실전 대응: 명확한 방향 확인 전까지는 작은 포지션으로 대응하거나 관망하는 편이 좋습니다.{guide_tail}"


def _build_professional_reasons(meta):
    reasons = []
    continuation_buy = _safe_float(meta.get("continuation_buy_score", 0))
    continuation_sell = _safe_float(meta.get("continuation_sell_score", 0))
    trend_buy = _safe_float(meta.get("trend_inflection_buy_score", 0))
    trend_sell = _safe_float(meta.get("trend_inflection_sell_score", 0))
    market_turn_bull = _safe_float(meta.get("market_turn_bull_score", 0))
    market_turn_bear = _safe_float(meta.get("market_turn_bear_score", 0))
    macro_pressure = _safe_float(meta.get("macro_pressure_score", 0))
    change_pct = _safe_float(meta.get("price_change_pct", 0))
    volume_ratio = _safe_float(meta.get("volume", 0)) / max(_safe_float(meta.get("avg_volume", 1), 1), 1)
    slowk = _safe_float(meta.get("slowk", 50))
    rsi = _safe_float(meta.get("rsi", 50))
    macd_hist = _safe_float(meta.get("macd_hist", 0))
    percent_b = _safe_float(meta.get("percent_b", 0.5))
    price = _safe_float(meta.get("price", 0))
    ma20 = _safe_float(meta.get("ma20", 0))
    ma50 = _safe_float(meta.get("ma50", 0))
    ma200 = _safe_float(meta.get("ma200", 0))
    objective_alignment = str(meta.get("objective_alignment", "MIXED")).upper()
    objective_confidence = _safe_float(meta.get("objective_confidence", 0))
    layer_edge = _safe_float(meta.get("buy_total", 0)) - _safe_float(meta.get("sell_total", 0))
    conflict_layers = _safe_int(meta.get("signal_conflict_layers", 0))
    sell_bias = continuation_sell > continuation_buy or trend_sell > trend_buy or market_turn_bear > market_turn_bull

    if layer_edge >= 4:
        reasons.append(f"10개 레이어 합산이 매수 쪽으로 {layer_edge:+.1f} 우위라 추세 추종 또는 눌림 매수 전략이 상대적으로 유리했습니다.")
    elif layer_edge <= -4:
        reasons.append(f"10개 레이어 합산이 매도 쪽으로 {layer_edge:+.1f} 우위라 비중 축소와 방어 전략이 더 자연스러웠습니다.")
    elif conflict_layers >= 3:
        reasons.append(f"10개 레이어 중 {conflict_layers}개가 충돌해 방향 확신보다 확인 신호가 더 중요했습니다.")

    if objective_alignment == "ALIGNED" and objective_confidence >= 60:
        reasons.append(f"객관 차트 엔진도 같은 방향을 {objective_confidence:.0f}% 신뢰도로 확인해 판단 일관성이 높았습니다.")
    elif objective_alignment == "CONFLICT":
        reasons.append("객관 차트 엔진이 반대 방향을 가리켜 최종 판단을 그대로 공격적으로 해석하기보다 보수적으로 볼 필요가 있었습니다.")

    if continuation_buy >= 2:
        reasons.append(f"continuation 점수 {continuation_buy:.1f}로 추세 지속형 매수 스택이 유지됐습니다.")
    elif continuation_sell >= 2:
        reasons.append(f"continuation 점수 {continuation_sell:.1f}로 구조 약화와 매도 압력이 누적됐습니다.")

    if trend_buy >= 1.5 or market_turn_bull >= 1.5:
        reasons.append("초기 상승 전환 신호가 감지돼 눌림 이후 재가속 가능성을 높게 봤습니다.")
    elif trend_sell >= 1.5 or market_turn_bear >= 1.5:
        reasons.append("초기 약세 전환 신호가 감지돼 기존 상승 추세 약화를 경계했습니다.")

    if change_pct <= -2 and volume_ratio >= 1.2:
        reasons.append(f"평균 대비 {volume_ratio:.1f}배 거래량을 동반한 하락이라 매도 압력 확인으로 해석했습니다.")
    elif change_pct >= 2 and volume_ratio >= 1.2:
        reasons.append(f"평균 대비 {volume_ratio:.1f}배 거래량을 동반한 상승이라 추세 추종 매수 근거가 강화됐습니다.")

    if price > 0 and ma20 > 0 and ma50 > 0:
        if not sell_bias and price > ma20 and price > ma50:
            if ma200 > 0 and price > ma200 and ma20 > ma50 > ma200:
                reasons.append("주가가 20·50·200일선 위에서 정배열을 유지해 중장기 추세가 아직 우호적이었습니다.")
            else:
                reasons.append("주가가 20일선과 50일선 위를 유지해 단기 추세가 완전히 꺾이지는 않았습니다.")
        elif sell_bias and price < ma20 and price < ma50:
            if ma200 > 0 and price < ma200 and ma20 < ma50 < ma200:
                reasons.append("주가가 20·50·200일선 아래에 있어 중장기 흐름도 약세 쪽으로 기울었습니다.")
            else:
                reasons.append("주가가 20일선과 50일선을 밑돌아 단기·중기 추세가 약해졌습니다.")

    level_reasons = _build_level_reason_points(meta, "sell" if sell_bias else "buy")
    if level_reasons:
        reasons.extend(level_reasons[:1])

    if sell_bias and macd_hist < 0:
        reasons.append("MACD 히스토그램이 음수권이라 하락 모멘텀이 우세한 편이었습니다.")
    elif not sell_bias and macd_hist > 0:
        reasons.append("MACD 히스토그램이 플러스권이라 상승 모멘텀이 아직 살아 있었습니다.")

    if sell_bias and percent_b <= 0.2:
        reasons.append("주가가 볼린저 하단 부근에 머물러 하단 압력이 이어졌습니다.")
    elif not sell_bias and percent_b >= 0.8:
        reasons.append("주가가 볼린저 상단 부근에서 버텨 추세 탄력이 유지되는 흐름이었습니다.")

    if meta.get("bullish_gap_reversal"):
        reasons.append("갭다운 이후 회복 패턴이 나와 하방 흡수 가능성을 반영했습니다.")
    if meta.get("bearish_gap_failure"):
        reasons.append("갭업 실패 패턴이 확인돼 상단 추격 수요 약화로 해석했습니다.")
    if meta.get("fib_618_support"):
        reasons.append("최근 상승 파동의 61.8% 되돌림 구간을 지켜 단순 조정에 그칠 가능성을 열어뒀습니다.")
    elif meta.get("fib_50_support") or meta.get("fib_382_support"):
        reasons.append("최근 상승 파동의 피보나치 되돌림 구간에서 지지가 확인돼 눌림목 성격을 점검했습니다.")
    if meta.get("fib_618_breakdown"):
        reasons.append("61.8% 되돌림이 무너지며 단순 조정보다 추세 훼손 가능성이 커졌습니다.")
    elif meta.get("fib_618_resistance") or meta.get("fib_50_resistance"):
        reasons.append("피보나치 되돌림 구간이 저항으로 작용해 반등 탄력이 제한됐습니다.")
    if meta.get("fib_confluence_buy"):
        reasons.append("피보나치 지지와 이평선·볼륨 프로파일 지지가 겹쳐 지지 신뢰도가 높아졌습니다.")
    if meta.get("fib_confluence_sell"):
        reasons.append("피보나치 저항과 이평선·볼륨 프로파일 저항이 겹쳐 상단 부담이 커졌습니다.")
    if meta.get("fib_ext_1618_up_hit"):
        reasons.append("상방 1.618 확장 목표권에 닿아 단기 과열 또는 목표가 도달 구간일 수 있습니다.")
    if meta.get("fib_ext_1618_down_hit"):
        reasons.append("하방 1.618 확장 구간에 닿아 단기 투매 마무리 여부를 함께 점검할 필요가 있습니다.")

    structure_terms = []
    if meta.get("diag_support_hold"):
        structure_terms.append("사선 지지 유지")
    if meta.get("diag_breakdown_bear"):
        structure_terms.append("사선 이탈")
    if meta.get("box_breakout_bull"):
        structure_terms.append("박스 돌파")
    if meta.get("box_breakdown_bear"):
        structure_terms.append("박스 이탈")
    if meta.get("channel_support_hold"):
        structure_terms.append("채널 지지")
    if meta.get("channel_breakdown_bear"):
        structure_terms.append("채널 이탈")
    if meta.get("triangle_breakout_bull"):
        structure_terms.append("삼각 상방 돌파")
    if meta.get("triangle_breakdown_bear"):
        structure_terms.append("삼각 하방 이탈")
    if structure_terms:
        reasons.append(f"구조 패턴 측면에서는 {_join_reason_phrases(structure_terms[:3])}이 핵심 근거였습니다.")

    if slowk <= 20 or rsi <= 35:
        reasons.append("Stochastic/RSI 기준으로는 단기 과매도 구간에 가까워 기술적 반등 가능성도 함께 열어뒀습니다.")
    elif slowk >= 80 or rsi >= 65:
        reasons.append("Stochastic/RSI 기준으로는 단기 과열권에 가까워 추격 리스크를 함께 반영했습니다.")

    derived_reason_points = []
    for item in meta.get("derived_reason_states") or []:
        text = str(item.get("meaning") or item.get("desc") or "").strip()
        if text:
            derived_reason_points.append(text)
    for text in derived_reason_points[:2]:
        if text not in reasons:
            reasons.append(text)

    macro_help = _macro_pressure_help(meta)
    if macro_help:
        if len(reasons) >= 4:
            reasons = reasons[:4]
        reasons.append(macro_help)

    return reasons[:5]


def _side_reason_points(meta, side):
    points = []
    continuation_buy = _safe_float(meta.get("continuation_buy_score", 0))
    continuation_sell = _safe_float(meta.get("continuation_sell_score", 0))
    trend_buy = _safe_float(meta.get("trend_inflection_buy_score", 0))
    trend_sell = _safe_float(meta.get("trend_inflection_sell_score", 0))
    market_turn_bull = _safe_float(meta.get("market_turn_bull_score", 0))
    market_turn_bear = _safe_float(meta.get("market_turn_bear_score", 0))
    change_pct = _safe_float(meta.get("price_change_pct", 0))
    volume_ratio = _safe_float(meta.get("volume", 0)) / max(_safe_float(meta.get("avg_volume", 1), 1), 1)
    macd_hist = _safe_float(meta.get("macd_hist", 0))
    percent_b = _safe_float(meta.get("percent_b", 0.5))
    breadth_score = _safe_float(meta.get("market_breadth_score", 0))
    macro_pressure = _safe_float(meta.get("macro_pressure_score", 0))
    price = _safe_float(meta.get("price", 0))
    ma20 = _safe_float(meta.get("ma20", 0))
    ma50 = _safe_float(meta.get("ma50", 0))
    ma200 = _safe_float(meta.get("ma200", 0))

    if side == "buy":
        if meta.get("bullish_gap_reversal"):
            points.append("갭다운 이후 빠른 회복")
        if meta.get("fib_618_support"):
            points.append("Fib 61.8% 지지")
        elif meta.get("fib_50_support"):
            points.append("Fib 50% 지지")
        if meta.get("fib_618_reclaim"):
            points.append("Fib 61.8% 회복")
        if meta.get("fib_confluence_buy"):
            points.append("피보 중첩 지지")
        if price > 0 and ma20 > 0 and price > ma20:
            points.append("20일선 위 유지")
        if price > 0 and ma50 > 0 and price > ma50:
            points.append("50일선 위 유지")
        if price > 0 and ma200 > 0 and price > ma200:
            points.append("200일선 위 유지")
        if price > 0 and ma20 > 0 and ma50 > 0 and ma200 > 0 and price > ma20 and ma20 > ma50 > ma200:
            points.append("중장기 정배열")
        if meta.get("diag_support_hold") or meta.get("box_support_hold") or meta.get("channel_support_hold"):
            points.append("핵심 지지 구조 유지")
        if meta.get("diag_breakout_bull") or meta.get("box_breakout_bull") or meta.get("channel_breakout_bull") or meta.get("triangle_breakout_bull"):
            points.append("상방 돌파 구조 확인")
        if continuation_buy >= 1.5:
            points.append("추세 지속형 매수 스택")
        if change_pct >= 2 and volume_ratio >= 1.2:
            points.append(f"거래량 동반 상승({volume_ratio:.1f}배)")
        if trend_buy >= 1.5 or market_turn_bull >= 1.5:
            points.append("초기 상승 전환 신호")
        if macd_hist > 0:
            points.append("MACD 양수 모멘텀")
        if percent_b >= 0.8:
            points.append("볼린저 상단 지지")
        if meta.get("breadth_risk_on") or breadth_score > 0.5:
            points.append("시장 breadth 확산")
        if macro_pressure <= -1.0:
            points.append("거시 부담 완화")
    else:
        if meta.get("bearish_gap_failure"):
            points.append("갭업 실패 패턴")
        if meta.get("fib_618_breakdown"):
            points.append("Fib 61.8% 이탈")
        elif meta.get("fib_618_resistance"):
            points.append("Fib 61.8% 저항")
        elif meta.get("fib_50_resistance"):
            points.append("Fib 50% 저항")
        if meta.get("fib_confluence_sell"):
            points.append("피보 중첩 저항")
        if price > 0 and ma20 > 0 and price < ma20:
            points.append("20일선 하회")
        if price > 0 and ma50 > 0 and price < ma50:
            points.append("50일선 하회")
        if price > 0 and ma200 > 0 and price < ma200:
            points.append("200일선 하회")
        if price > 0 and ma20 > 0 and ma50 > 0 and ma200 > 0 and price < ma20 and ma20 < ma50 < ma200:
            points.append("중장기 역배열")
        if meta.get("diag_breakdown_bear") or meta.get("box_breakdown_bear") or meta.get("channel_breakdown_bear") or meta.get("triangle_breakdown_bear"):
            points.append("핵심 지지 구조 이탈")
        if continuation_sell >= 1.5:
            points.append("매도 압력 누적")
        if change_pct <= -2 and volume_ratio >= 1.2:
            points.append(f"거래량 동반 하락({volume_ratio:.1f}배)")
        if trend_sell >= 1.5 or market_turn_bear >= 1.5:
            points.append("초기 약세 전환 신호")
        if macd_hist < 0:
            points.append("MACD 음수 모멘텀")
        if percent_b <= 0.2:
            points.append("볼린저 하단 압력")
        if meta.get("breadth_risk_off") or breadth_score < -0.5:
            points.append("시장 breadth 약세")
        if macro_pressure >= 1.0:
            points.append("거시 역풍")
    return _ordered_unique(points)


def _build_decisive_driver_badges(meta, title):
    code = _judgment_code(meta, title)
    if code in {"STRONG_BUY", "BUY", "WATCH_BUY"}:
        labels = _compress_decisive_ma_labels(_side_reason_points(meta, "buy"), "buy")[:3]
        return "".join(_badge(label, "positive") for label in labels)
    if code in {"STRONG_SELL", "SELL", "WATCH_SELL"}:
        labels = _compress_decisive_ma_labels(_side_reason_points(meta, "sell"), "sell")[:3]
        return "".join(_badge(label, "negative") for label in labels)

    buy_labels = _compress_decisive_ma_labels(_side_reason_points(meta, "buy"), "buy")[:2]
    sell_labels = _compress_decisive_ma_labels(_side_reason_points(meta, "sell"), "sell")[:2]
    return "".join(
        [_badge(label, "positive") for label in buy_labels]
        + [_badge(label, "negative") for label in sell_labels]
    )


def _build_reason_compare_html(meta):
    buy_points = _side_reason_points(meta, "buy")[:4]
    sell_points = _side_reason_points(meta, "sell")[:4]
    buy_level_points = _build_level_reason_points(meta, "buy")[:2]
    sell_level_points = _build_level_reason_points(meta, "sell")[:2]

    def render_points(points, empty_text):
        if not points:
            return f"<p class='sigl-summary' style='margin:0'>{_esc(empty_text)}</p>"
        return "".join(
            f"<div class='sigl-summary' style='margin-bottom:6px'>• {_esc(point)}</div>"
            for point in points
        )

    buy_html = render_points(buy_points + buy_level_points, "뚜렷한 매수 근거는 아직 제한적입니다.")
    sell_html = render_points(sell_points + sell_level_points, "뚜렷한 매도 근거는 아직 제한적입니다.")
    return f"""
    <div class="sigl-grid sigl-grid--2">
      <div class="sigl-card" style="border-color:rgba(99,217,162,0.22)">
        <div class="sigl-section-head">
          <div>
            <p class="sigl-section-title">매수 근거</p>
            <p class="sigl-section-copy">상승 쪽으로 해석되는 핵심 근거입니다.</p>
          </div>
        </div>
        {buy_html}
      </div>
      <div class="sigl-card" style="border-color:rgba(255,143,150,0.22)">
        <div class="sigl-section-head">
          <div>
            <p class="sigl-section-title">매도 근거</p>
            <p class="sigl-section-copy">하락 쪽으로 해석되는 핵심 근거입니다.</p>
          </div>
        </div>
        {sell_html}
      </div>
    </div>
    """


def _judgment_explainer(meta, title):
    raw_judgment = str(meta.get("judgment", "")).strip()
    final_code = _judgment_code(meta, title or raw_judgment)
    final_label = _display_action_title(meta, title or raw_judgment)
    pre_veto_label = localize_judgment_label(str(meta.get("pre_veto_judgment", "")).strip())
    pre_veto_code = _judgment_code({"judgment": meta.get("pre_veto_judgment", "")}, pre_veto_label)
    pre_veto_title = _display_action_title({"judgment": pre_veto_code}, pre_veto_label)
    downgrade_count = _safe_int(meta.get("downgrade_count", 0))
    macro_risk_off_count = _safe_int(meta.get("macro_risk_off_count", 0))
    macro_risk_on_count = _safe_int(meta.get("macro_risk_on_count", 0))
    continuation_buy = _safe_float(meta.get("continuation_buy_score", 0))
    continuation_sell = _safe_float(meta.get("continuation_sell_score", 0))
    macro_pressure = _safe_float(meta.get("macro_pressure_score", 0))
    ut_gap = max(_safe_float(meta.get("utbot_stop_atr_gap", 0)), 0.0)
    breadth_score = _safe_float(meta.get("market_breadth_score", 0))
    judgment_tone = _tone_from_text(raw_judgment or final_label)
    buy_level_text = _build_level_focus_text(meta, "buy")
    sell_level_text = _build_level_focus_text(meta, "sell")

    supportive = []
    risk = []

    if continuation_buy >= 2.5:
        supportive.append("추세 지속형 continuation 신호")
    elif continuation_buy >= 1.0:
        supportive.append("추세 지지 신호")
    if meta.get("bullish_gap_reversal"):
        supportive.append("갭다운 이후 빠른 회복")
    if meta.get("diag_support_hold"):
        supportive.append("사선 지지 유지")
    if meta.get("diag_breakout_bull"):
        supportive.append("사선 돌파 구조")
    if meta.get("box_support_hold"):
        supportive.append("박스권 지지 유지")
    if meta.get("box_breakout_bull"):
        supportive.append("박스권 상단 돌파")
    if meta.get("channel_support_hold"):
        supportive.append("상승 채널 지지 유지")
    if meta.get("channel_breakout_bull"):
        supportive.append("채널 상단 돌파")
    if meta.get("triangle_breakout_bull"):
        supportive.append("삼각수렴 상방 돌파")
    if ut_gap and ut_gap <= 0.9 and continuation_buy >= continuation_sell:
        supportive.append("UTBot 기준선 근처 지지")
    if breadth_score >= 1.0 or meta.get("breadth_risk_on") or macro_risk_on_count >= 2:
        supportive.append("시장 breadth 확산")

    if continuation_sell >= 2.5:
        risk.append("구조 약화와 매도 압력 누적")
    elif continuation_sell >= 1.0:
        risk.append("매도 압력 경합")
    if meta.get("bearish_gap_failure"):
        risk.append("갭업 실패 함정")
    if meta.get("diag_resistance_reject"):
        risk.append("사선 저항 확인")
    if meta.get("diag_breakdown_bear"):
        risk.append("사선 이탈 구조")
    if meta.get("box_resistance_reject"):
        risk.append("박스권 상단 저항")
    if meta.get("box_breakdown_bear"):
        risk.append("박스권 하단 이탈")
    if meta.get("channel_resistance_reject"):
        risk.append("채널 상단 저항")
    if meta.get("channel_breakdown_bear"):
        risk.append("채널 하단 이탈")
    if meta.get("triangle_breakdown_bear"):
        risk.append("삼각수렴 하방 이탈")
    elif meta.get("desc_triangle"):
        risk.append("하락 삼각수렴 압력")
    if ut_gap >= 2.0 and continuation_buy >= continuation_sell:
        risk.append("UTBot 기준선과의 과도한 이격")
    if meta.get("thin_trade_risk"):
        risk.append("얇은 거래대금")
    if macro_risk_off_count >= 2 or macro_pressure >= 1.5:
        risk.append(f"거시 역풍 {max(macro_risk_off_count, 1)}개")
    if meta.get("narrow_leadership"):
        risk.append("메가캡 쏠림 장세")
    if meta.get("flip_guard_triggered"):
        risk.append("급반전 보호 구간")

    support_text = _join_reason_phrases(supportive[:3])
    risk_text = _join_reason_phrases(risk[:3])

    if pre_veto_label and pre_veto_code != final_code and downgrade_count > 0:
        initial_side = "sell" if "SELL" in pre_veto_code else "buy"
        initial_parts = _root_reason_parts(meta, initial_side)
        initial_text = " ".join(initial_parts[:3]).strip().rstrip(". ")
        initial_sentence = initial_text if initial_text.endswith(("입니다", "니다")) else f"{initial_text}입니다"
        indicator_reason = _build_indicator_reason_text(meta, initial_side)
        adjustment_text = support_text if "SELL" in pre_veto_code else risk_text
        reason_chunks = [chunk for chunk in [initial_sentence, indicator_reason] if chunk]
        reason_text = " ".join(reason_chunks).strip()
        if reason_text and not reason_text.endswith((".", "다.", "요.")):
            reason_text += "."
        if reason_text and adjustment_text:
            level_tail = f" {sell_level_text if initial_side == 'sell' else buy_level_text}" if (sell_level_text if initial_side == "sell" else buy_level_text) else ""
            return f"{pre_veto_title} 판단의 출발점은 {reason_text} 다만 {adjustment_text}이 함께 보여 최종 판단은 {final_label}입니다.{level_tail}"
        if reason_text:
            level_tail = f" {sell_level_text if initial_side == 'sell' else buy_level_text}" if (sell_level_text if initial_side == "sell" else buy_level_text) else ""
            return f"{pre_veto_title} 판단의 출발점은 {reason_text} 최종 판단은 {final_label}입니다.{level_tail}"
        cause_text = adjustment_text or risk_text or support_text
        if cause_text:
            level_tail = f" {sell_level_text if initial_side == 'sell' else buy_level_text}" if (sell_level_text if initial_side == "sell" else buy_level_text) else ""
            return f"{pre_veto_title}로 보기 시작한 이유는 {cause_text}입니다. 최종 판단은 {final_label}입니다.{level_tail}"
        return f"최종 판단은 {final_label}입니다."

    if judgment_tone == "positive":
        if support_text and risk_text:
            level_tail = f" {buy_level_text}" if buy_level_text else ""
            return f"{final_label}입니다. {support_text}이 핵심 근거입니다. 다만 {risk_text}는 함께 확인해야 할 리스크입니다.{level_tail}"
        if support_text:
            level_tail = f" {buy_level_text}" if buy_level_text else ""
            return f"{final_label}입니다. {support_text}이 핵심 근거입니다.{level_tail}"
        if risk_text:
            level_tail = f" {buy_level_text}" if buy_level_text else ""
            return f"{final_label}입니다. 다만 {risk_text}는 함께 경계해야 합니다.{level_tail}"
    elif judgment_tone == "negative":
        if risk_text and support_text:
            level_tail = f" {sell_level_text}" if sell_level_text else ""
            return f"{final_label}입니다. {risk_text}이 핵심 근거입니다. 다만 {support_text}는 반대 근거로 남아 있습니다.{level_tail}"
        if risk_text:
            level_tail = f" {sell_level_text}" if sell_level_text else ""
            return f"{final_label}입니다. {risk_text}이 핵심 근거입니다.{level_tail}"
        if support_text:
            level_tail = f" {sell_level_text}" if sell_level_text else ""
            return f"{final_label}입니다. 다만 {support_text}는 반대 근거로 남아 있습니다.{level_tail}"
    else:
        if support_text and risk_text:
            level_tail = f" {buy_level_text or sell_level_text}" if (buy_level_text or sell_level_text) else ""
            return f"{final_label}입니다. 매수 쪽에서는 {support_text}, 매도 쪽에서는 {risk_text}가 동시에 보여 판단을 보수적으로 유지했습니다.{level_tail}"
        if support_text or risk_text:
            level_tail = f" {buy_level_text or sell_level_text}" if (buy_level_text or sell_level_text) else ""
            return f"{final_label}입니다. {_join_reason_phrases([support_text, risk_text])}의 영향을 받았습니다.{level_tail}"
    return ""


def _objective_pair_tone(buy_value, sell_value, gap=0.35):
    if buy_value > sell_value + gap:
        return "positive"
    if sell_value > buy_value + gap:
        return "negative"
    return "warning"


def _build_objective_component_cards(meta):
    specs = [
        ("추세", "objective_trend_buy", "objective_trend_sell"),
        ("모멘텀", "objective_momentum_buy", "objective_momentum_sell"),
        ("수급", "objective_money_buy", "objective_money_sell"),
        ("반전", "objective_reversal_buy", "objective_reversal_sell"),
        ("가격 위치", "objective_location_buy", "objective_location_sell"),
        ("시그널", "objective_signal_buy", "objective_signal_sell"),
        ("콤보", "objective_combo_buy", "objective_combo_sell"),
    ]
    cards = []
    for label, buy_key, sell_key in specs:
        buy_value = _safe_float(meta.get(buy_key, 0))
        sell_value = _safe_float(meta.get(sell_key, 0))
        cards.append(
            _mini_stat_card(
                label,
                f"B {buy_value:.1f} · S {sell_value:.1f}",
                _objective_pair_tone(buy_value, sell_value),
            )
        )
    return "".join(cards)


def _build_objective_indicator_badges(meta):
    price = _safe_float(meta.get("price", 0))
    vwap = _safe_float(meta.get("vwap", 0))
    fixed_vwap = _safe_float(meta.get("fixed_vwap", 0))
    envelope_percent = _safe_float(meta.get("envelope_percent", 0.5))
    psar_dir = _safe_int(meta.get("psar_dir", 0))
    williams_r = _safe_float(meta.get("williams_r", -50))
    cci = _safe_float(meta.get("cci", 0))
    roc = _safe_float(meta.get("roc", 0))
    rmi = _safe_float(meta.get("rmi", 50))
    mass_index = _safe_float(meta.get("mass_index", 0))
    chaikin = _safe_float(meta.get("chaikin_oscillator", 0))

    badges = []
    if vwap:
        badges.append(_badge("VWAP 상단" if price >= vwap else "VWAP 하단", "positive" if price >= vwap else "negative"))
    if fixed_vwap:
        badges.append(_badge("고정 VWAP 상단" if price >= fixed_vwap else "고정 VWAP 하단", "positive" if price >= fixed_vwap else "negative"))
    badges.append(_badge(f"Envelope {envelope_percent:.2f}", "positive" if envelope_percent <= 0.2 else "negative" if envelope_percent >= 0.8 else "warning"))
    badges.append(_badge("PSAR 상승" if psar_dir >= 0 else "PSAR 하락", "positive" if psar_dir >= 0 else "negative"))
    badges.append(_badge(f"WR {williams_r:.0f}", "positive" if williams_r <= -80 else "negative" if williams_r >= -20 else "muted"))
    badges.append(_badge(f"CCI {cci:.0f}", "positive" if cci <= -100 else "negative" if cci >= 100 else "muted"))
    badges.append(_badge(f"ROC {roc:+.1f}", "positive" if roc > 0 else "negative" if roc < 0 else "muted"))
    badges.append(_badge(f"RMI {rmi:.0f}", "positive" if rmi >= 55 else "negative" if rmi <= 45 else "warning"))
    if mass_index:
        badges.append(_badge(f"Mass {mass_index:.1f}", "warning" if mass_index >= 26.5 else "muted"))
    badges.append(_badge(f"Chaikin {chaikin:+.2f}", "positive" if chaikin > 0 else "negative" if chaikin < 0 else "muted"))
    if meta.get("fractal_low"):
        badges.append(_badge("Fractal Low", "positive"))
    if meta.get("fractal_high"):
        badges.append(_badge("Fractal High", "negative"))
    return "".join(badges)


def _build_chart_interpretation_badges(meta):
    price = _safe_float(meta.get("price", 0))
    vwap = _safe_float(meta.get("vwap", 0))
    fixed_vwap = _safe_float(meta.get("fixed_vwap", 0))
    vp_poc = _safe_float(meta.get("vp_poc", 0))
    atr = max(_safe_float(meta.get("atr", 0)), 1e-6)
    vp_long_rr = _safe_float(meta.get("vp_long_rr", 0))
    vp_short_rr = _safe_float(meta.get("vp_short_rr", 0))
    envelope_percent = _safe_float(meta.get("envelope_percent", 0.5))
    percent_b = _safe_float(meta.get("percent_b", 0.5))
    williams_r = _safe_float(meta.get("williams_r", -50))
    cci = _safe_float(meta.get("cci", 0))
    rsi = _safe_float(meta.get("rsi", 50))
    mfi = _safe_float(meta.get("mfi", 50))
    slowk = _safe_float(meta.get("slowk", 50))
    rmi = _safe_float(meta.get("rmi", 50))
    wt1 = _safe_float(meta.get("wt1", 0))
    macd_hist = _safe_float(meta.get("macd_hist", 0))
    adx = _safe_float(meta.get("adx", 0))
    rs_ratio = _safe_float(meta.get("rs_ratio", 1))
    composite_accel = _safe_float(meta.get("composite_accel", 0))
    chaikin = _safe_float(meta.get("chaikin_oscillator", 0))
    cmf = _safe_float(meta.get("cmf", 0))
    mass_index = _safe_float(meta.get("mass_index", 0))
    atr_pct = _safe_float(meta.get("atr_pct", 0))
    volume_ratio_20 = _safe_float(meta.get("volume_ratio_20", 1))
    volume_ratio_50 = _safe_float(meta.get("volume_ratio_50", 1))
    dollar_volume_z = _safe_float(meta.get("dollar_volume_z", 0))
    channel_position = _safe_float(meta.get("channel_position", 0))
    supertrend_gap = _safe_float(meta.get("supertrend_gap", 0))
    ad_line_z = _safe_float(meta.get("ad_line_z", 0))
    tenkan_gap = _safe_float(meta.get("tenkan_gap", 0))
    kijun_gap = _safe_float(meta.get("kijun_gap", 0))
    cloud_spread = _safe_float(meta.get("cloud_spread", 0))
    disparity_20 = _safe_float(meta.get("disparity_20", 0))
    disparity_50 = _safe_float(meta.get("disparity_50", 0))
    hma_rising = bool(meta.get("hma_rising"))
    utbot_dir = _safe_int(meta.get("utbot_dir", 0))
    psar_dir = _safe_int(meta.get("psar_dir", 0))
    squeeze_on = bool(meta.get("squeeze_on"))
    leader_stock_mode = bool(meta.get("leader_stock_mode"))
    narrow_leadership = bool(meta.get("narrow_leadership"))
    change_pct = _safe_float(meta.get("price_change_pct", 0))
    breadth_score = _safe_float(meta.get("market_breadth_score", 0))
    macro_pressure = _safe_float(meta.get("macro_pressure_score", 0))

    badges = []
    seen = set()

    def add(label, tone):
        text = str(label or "").strip()
        if not text or text in seen:
            return
        seen.add(text)
        badges.append(_badge(text, tone))

    lead_signal = (_recent_signal_payloads(meta, limit=1) or [{}])[0]
    lead_signal_label = str(lead_signal.get("label") or "").strip()
    lead_signal_tone = str(lead_signal.get("tone") or "warning").strip() or "warning"
    if lead_signal_label:
        add(f"대표 신호 · {lead_signal_label}", lead_signal_tone)

    if change_pct >= 2 and volume_ratio_20 >= 1.2:
        add("강한 상승 + 거래량 동반 · 추세 확인 우호", "positive")
    elif change_pct <= -2 and volume_ratio_20 >= 1.2:
        add("강한 하락 + 거래량 동반 · 매도 압력 확인", "negative")
    elif change_pct > 0 and volume_ratio_20 <= 0.85:
        add("가벼운 반등 · 추격보다 확인 우선", "warning")
    elif change_pct < 0 and volume_ratio_20 <= 0.85:
        add("거래량 없는 하락 · 공포 과대해석 주의", "warning")

    if vwap and fixed_vwap:
        if price >= vwap and price >= fixed_vwap:
            add("VWAP 위 안착 · 단기와 중기 기준선 모두 상방", "positive")
        elif price < vwap and price < fixed_vwap:
            add("VWAP 아래 체류 · 반등보다 회복 확인이 먼저", "negative")
        elif price >= vwap:
            add("단기 반등 시도 · 고정 VWAP 저항은 남음", "warning")
        else:
            add("단기 추진력 약화 · VWAP 재탈환 필요", "negative")
    elif vwap:
        add("VWAP 위 안착 · 단기 매수 우위" if price >= vwap else "VWAP 아래 체류 · 단기 매도 우위", "positive" if price >= vwap else "negative")

    if hma_rising and utbot_dir >= 0 and psar_dir >= 0:
        add("HMA·UTBot·PSAR 동시 상방 · 추세 지속 쪽 우세", "positive")
    elif (not hma_rising) and utbot_dir < 0 and psar_dir < 0:
        add("HMA·UTBot·PSAR 동시 하방 · 되돌림보다 방어 우선", "negative")
    elif hma_rising or utbot_dir >= 0 or psar_dir >= 0:
        add("추세 해석 혼재 · 상방 시도와 저항이 공존", "warning")

    bullish_momentum = sum([rsi >= 55, rmi >= 55, macd_hist > 0, wt1 > 0])
    bearish_momentum = sum([rsi <= 45, rmi <= 45, macd_hist < 0, wt1 < 0])
    if bullish_momentum >= 3 and mfi >= 55 and slowk >= 50:
        add("모멘텀 플러스 · 눌림 매수 해석이 쉬운 구간", "positive")
    elif bearish_momentum >= 3 and mfi <= 45 and slowk <= 50:
        add("모멘텀 마이너스 · 반등도 확인이 필요한 구간", "negative")
    elif (williams_r <= -80) or (cci <= -100):
        add("과매도권 진입 · 기술적 반등 후보", "warning")
    elif (williams_r >= -20) or (cci >= 100):
        add("과열권 근접 · 추격 매수는 부담", "warning")

    if adx >= 25 and bullish_momentum >= 3 and supertrend_gap > 0:
        add("ADX 확장 · 상승 추세형 장세로 읽기 쉬움", "positive")
    elif adx >= 25 and bearish_momentum >= 3 and supertrend_gap < 0:
        add("ADX 확장 · 하락 추세형 압력이 강한 구간", "negative")
    elif adx <= 18 and squeeze_on:
        add("추세 힘은 약함 · 스퀴즈 뒤 방향 분출 대기", "warning")

    if envelope_percent >= 0.82 or percent_b >= 0.82:
        add("상단 밴드 근접 · 단기 과열/되돌림 경계", "warning")
    elif envelope_percent <= 0.18 or percent_b <= 0.18:
        add("하단 밴드 근접 · 눌림 반등 자리 탐색", "warning")

    if vp_poc:
        poc_gap_atr = (price - vp_poc) / atr
        if poc_gap_atr >= 0.4 and vp_long_rr >= vp_short_rr + 0.2:
            add("POC 위 + 롱 RR 우세 · 지지 기반 상방 우위", "positive")
        elif poc_gap_atr <= -0.4 and vp_short_rr >= vp_long_rr + 0.2:
            add("POC 아래 + 숏 RR 우세 · 저항 기반 하방 우위", "negative")
        elif abs(poc_gap_atr) <= 0.25:
            add("POC 근처 균형권 · 방향 선택 대기", "warning")

    if tenkan_gap > 0 and kijun_gap > 0 and cloud_spread > 0:
        add("일목 구조 상방 · 기준선 위 추세 유지", "positive")
    elif tenkan_gap < 0 and kijun_gap < 0 and cloud_spread < 0:
        add("일목 구조 하방 · 기준선 아래 약세 유지", "negative")

    if volume_ratio_20 >= 1.2 and (chaikin > 0 or cmf > 0.03 or ad_line_z > 0.4 or dollar_volume_z > 0.5):
        add("거래량·자금 유입 동반 · 신호 신뢰도 보강", "positive")
    elif bool(meta.get("thin_trade_risk")):
        add("거래대금 얇음 · 신호 신뢰도 한 단계 낮춤", "negative")
    elif volume_ratio_20 < 0.9 and volume_ratio_50 < 0.95 and (chaikin <= 0 or cmf < 0 or ad_line_z < -0.4):
        add("거래량 둔화 · 추세 연속성은 약한 편", "warning")

    if rs_ratio >= 1.02 and composite_accel > 0.2:
        add("시장 대비 상대강도 우위 · 주도주 성격 강화", "positive" if leader_stock_mode else "accent")
    elif rs_ratio <= 0.98 and composite_accel < -0.2:
        add("시장 대비 상대약세 · 반등보다 추세 확인 우선", "negative")
    elif narrow_leadership:
        add("리더주 편중 장세 · 선별 접근이 중요", "warning")

    if breadth_score >= 1.0 and macro_pressure <= -1.0:
        add("시장 바탕 우호 · 개별 차트 해석에 순풍", "positive")
    elif breadth_score <= -1.0 and macro_pressure >= 1.0:
        add("시장 역풍 동반 · 개별 신호 희석 가능", "negative")

    if mass_index >= 26.5 and atr_pct >= 4:
        add("변동성 확장 · 방향 전환과 흔들림 주의", "warning")

    if meta.get("fib_618_reclaim") or meta.get("diag_support_hold") or meta.get("box_support_hold") or meta.get("channel_support_hold"):
        add("지지 구조 유지/회복 · 눌림 방어 확인", "positive")
    elif meta.get("fib_618_breakdown") or meta.get("diag_breakdown_bear") or meta.get("box_breakdown_bear") or meta.get("channel_breakdown_bear"):
        add("지지 이탈 경고 · 아래 지지 재탐색 가능", "negative")
    elif meta.get("diag_breakout_bull") or meta.get("box_breakout_bull") or meta.get("channel_breakout_bull") or meta.get("triangle_breakout_bull"):
        add("돌파 구조 형성 · 추세 재가속 후보", "positive")
    elif channel_position >= 30:
        add("채널 상단권 접근 · 상승은 유지되나 과열 점검", "warning")
    elif channel_position <= -30:
        add("채널 하단권 접근 · 지지 확인이 먼저", "warning")
    elif disparity_20 >= 5 or disparity_50 >= 8:
        add("이격 확대 구간 · 추세는 좋지만 추격 부담", "warning")
    elif disparity_20 <= -5 or disparity_50 <= -8:
        add("이격 과도 완화 구간 · 반등 여지와 변동성 공존", "warning")

    if meta.get("fractal_low"):
        add("Fractal Low 발생 · 단기 저점 탐색 시도", "positive")
    if meta.get("fractal_high"):
        add("Fractal High 발생 · 단기 고점 경고", "negative")

    return "".join(badges[:8])


def _build_chart_interpretation_detail_badges(meta):
    price = _safe_float(meta.get("price", 0))
    vwap = _safe_float(meta.get("vwap", 0))
    vp_poc = _safe_float(meta.get("vp_poc", 0))
    vp_vah = _safe_float(meta.get("vp_vah", 0))
    vp_val = _safe_float(meta.get("vp_val", 0))
    fib_618 = _safe_float(meta.get("fib_618", 0))
    vp_long_rr = _safe_float(meta.get("vp_long_rr", 0))
    vp_short_rr = _safe_float(meta.get("vp_short_rr", 0))

    support_text, resistance_text = _chart_levels_text(meta)
    _, position_line, _, bull_line, bear_line = _chart_scenario_text(meta)

    nearest_support = support_text.split(" · ")[0].strip()
    nearest_resistance = resistance_text.split(" · ")[0].strip()

    if price >= max(vwap, vp_poc, 0):
        stance_text = "기준선 위 · 상방 유지 구도"
    elif price < min(x for x in [vwap, vp_poc] if x > 0) if any(x > 0 for x in [vwap, vp_poc]) else False:
        stance_text = "기준선 아래 · 반등보다 회복 확인"
    else:
        stance_text = "기준선 혼재 · 방향 재정리 구간"

    if vp_long_rr > vp_short_rr:
        position_badge = f"롱 우위 · RR {vp_long_rr:.2f} vs {vp_short_rr:.2f}"
    elif vp_short_rr > vp_long_rr:
        position_badge = f"숏 우위 · RR {vp_short_rr:.2f} vs {vp_long_rr:.2f}"
    else:
        position_badge = f"우위 혼재 · RR {vp_long_rr:.2f} vs {vp_short_rr:.2f}"

    level_text = f"지지 {nearest_support} / 저항 {nearest_resistance}"

    if "매수(롱)" in position_line:
        strategy_badge = f"전략 · {(_named_chart_level('POC', vp_poc) or _named_chart_level('VWAP', vwap) or '지지 구간')} 눌림 확인"
    elif "매도(숏)" in position_line:
        strategy_badge = f"전략 · {(_named_chart_level('VWAP', vwap) or _named_chart_level('POC', vp_poc) or '저항 구간')} 반등 실패 확인"
    else:
        strategy_badge = "전략 · 성급한 진입보다 방향 확인 우선"

    badge_specs = [
        (f"구도 · {stance_text}", _interpretation_badge_tone(stance_text)),
        (f"포지션 · {position_badge}", _interpretation_badge_tone(position_badge)),
        (f"가까운 레벨 · {level_text}", "accent"),
        (strategy_badge, "warning"),
    ]
    return "".join(_badge(text, tone) for text, tone in badge_specs if str(text or "").strip())


def _build_chart_tab_summary(meta):
    price = _safe_float(meta.get("price", 0))
    vwap = _safe_float(meta.get("vwap", 0))
    fixed_vwap = _safe_float(meta.get("fixed_vwap", 0))
    vp_poc = _safe_float(meta.get("vp_poc", 0))
    atr = max(_safe_float(meta.get("atr", 0)), 1e-6)
    vp_long_rr = _safe_float(meta.get("vp_long_rr", 0))
    vp_short_rr = _safe_float(meta.get("vp_short_rr", 0))
    percent_b = _safe_float(meta.get("percent_b", 0.5))
    envelope_percent = _safe_float(meta.get("envelope_percent", 0.5))
    rsi = _safe_float(meta.get("rsi", 50))
    mfi = _safe_float(meta.get("mfi", 50))
    slowk = _safe_float(meta.get("slowk", 50))
    rmi = _safe_float(meta.get("rmi", 50))
    wt1 = _safe_float(meta.get("wt1", 0))
    macd_hist = _safe_float(meta.get("macd_hist", 0))
    adx = _safe_float(meta.get("adx", 0))
    rs_ratio = _safe_float(meta.get("rs_ratio", 1))
    composite_accel = _safe_float(meta.get("composite_accel", 0))
    chaikin = _safe_float(meta.get("chaikin_oscillator", 0))
    cmf = _safe_float(meta.get("cmf", 0))
    volume_ratio_20 = _safe_float(meta.get("volume_ratio_20", 1))
    volume_ratio_50 = _safe_float(meta.get("volume_ratio_50", 1))
    mass_index = _safe_float(meta.get("mass_index", 0))
    atr_pct = _safe_float(meta.get("atr_pct", 0))
    tenkan_gap = _safe_float(meta.get("tenkan_gap", 0))
    kijun_gap = _safe_float(meta.get("kijun_gap", 0))
    cloud_spread = _safe_float(meta.get("cloud_spread", 0))
    ad_line_z = _safe_float(meta.get("ad_line_z", 0))
    channel_position = _safe_float(meta.get("channel_position", 0))
    disparity_20 = _safe_float(meta.get("disparity_20", 0))
    disparity_50 = _safe_float(meta.get("disparity_50", 0))
    squeeze_on = bool(meta.get("squeeze_on"))
    leader_stock_mode = bool(meta.get("leader_stock_mode"))
    bb_low = _safe_float(meta.get("bb_low", 0))
    bb_up = _safe_float(meta.get("bb_up", 0))

    vwap_text = _named_chart_level("VWAP", vwap)
    fixed_vwap_text = _named_chart_level("고정 VWAP", fixed_vwap)
    poc_text = _named_chart_level("POC", vp_poc)
    bb_low_text = _named_chart_level("BB Low", bb_low)
    bb_up_text = _named_chart_level("BB Up", bb_up)

    sentences = []

    if vwap and fixed_vwap:
        if price >= vwap and price >= fixed_vwap:
            if bool(meta.get("hma_rising")) and _safe_int(meta.get("utbot_dir", 0)) >= 0:
                sentences.append(f"가격은 {vwap_text}과 {fixed_vwap_text} 위에 있고 HMA와 UTBot도 상방이라, 단기와 중기 추세 해석이 비교적 깔끔한 편입니다.")
            else:
                sentences.append(f"가격은 {vwap_text}과 {fixed_vwap_text} 위에 있어 단기와 중기 기준선 모두 상방에 놓여 있습니다.")
        elif price < vwap and price < fixed_vwap:
            if (not bool(meta.get("hma_rising"))) and _safe_int(meta.get("utbot_dir", 0)) < 0:
                sentences.append(f"가격은 {vwap_text}과 {fixed_vwap_text} 아래에 있고 HMA와 UTBot도 약세라, 반등 시도보다 기준선 회복 여부를 먼저 봐야 하는 자리입니다.")
            else:
                sentences.append(f"가격은 {vwap_text}과 {fixed_vwap_text} 아래에 있어 반등 시도보다 기준선 회복 여부를 먼저 봐야 하는 자리입니다.")
        elif price >= vwap:
            sentences.append(f"가격은 {vwap_text}을 회복했지만 아직 {fixed_vwap_text} 아래라 단기 반등과 중기 저항이 동시에 걸려 있는 모습입니다.")
        else:
            sentences.append(f"가격은 {fixed_vwap_text} 위는 유지하고 있지만 {vwap_text} 아래로 밀려 있어 단기 추진력이 약해진 상태입니다.")

    bullish_momentum = sum([rsi >= 55, rmi >= 55, macd_hist > 0, wt1 > 0])
    bearish_momentum = sum([rsi <= 45, rmi <= 45, macd_hist < 0, wt1 < 0])
    if bullish_momentum >= 3 and mfi >= 55 and slowk >= 50:
        if adx >= 25:
            sentences.append("RSI, MFI, Slow Stochastic, RMI, MACD, 웨이브트렌드가 대체로 상방이고 ADX까지 따라와, 추세형 상승으로 읽기 쉬운 구간입니다.")
        else:
            sentences.append("RSI, MFI, Slow Stochastic, RMI, MACD, 웨이브트렌드가 대체로 상방이라 눌림이 나와도 매수 해석이 비교적 쉬운 구간입니다.")
    elif bearish_momentum >= 3 and mfi <= 45 and slowk <= 50:
        if adx >= 25:
            sentences.append("RSI, MFI, Slow Stochastic, RMI, MACD, 웨이브트렌드가 하방 쪽으로 정렬되고 ADX도 높아, 약세 추세 압력을 가볍게 보기 어렵습니다.")
        else:
            sentences.append("RSI, MFI, Slow Stochastic, RMI, MACD, 웨이브트렌드 기준 모멘텀이 하방 쪽이라 반등이 나와도 추세 전환으로 보기 전 확인이 더 필요합니다.")
    elif percent_b <= 0.18 or envelope_percent <= 0.18:
        sentences.append(f"밴드 위치는 하단에 가까워 {bb_low_text or '볼린저 하단'} 부근 눌림이 깊은 대신 기술적 반등 여지도 함께 열려 있습니다.")
    elif percent_b >= 0.82 or envelope_percent >= 0.82:
        sentences.append(f"밴드 위치는 상단에 가까워 {bb_up_text or '볼린저 상단'} 부근 과열 부담이 있어, 추세는 강해도 단기 추격보다는 숨고르기 가능성을 같이 체크해야 합니다.")
    else:
        if squeeze_on and adx <= 18:
            sentences.append("모멘텀은 한쪽으로 완전히 기울지 않았고 스퀴즈와 낮은 ADX가 겹쳐, 방향성이 곧 정리될 준비 구간으로 해석하는 편이 좋습니다.")
        else:
            sentences.append("모멘텀은 한쪽으로 완전히 기울지 않아 추세 재개와 되돌림 가능성이 함께 열려 있는 중립권에 가깝습니다.")

    if tenkan_gap > 0 and kijun_gap > 0 and cloud_spread > 0:
        sentences.append("일목균형표 기준으로도 전환선, 기준선, 구름대가 모두 상방 쪽이어서 구조적인 추세 해석은 아직 살아 있습니다.")
    elif tenkan_gap < 0 and kijun_gap < 0 and cloud_spread < 0:
        sentences.append("일목균형표 기준으로는 전환선, 기준선, 구름대가 모두 하방 쪽이라 구조적인 약세 구도가 유지되고 있습니다.")
    elif abs(tenkan_gap) <= 1 and abs(kijun_gap) <= 1:
        sentences.append("일목균형표상 주요 기준선 근처에서 공방 중이라 추세 확정보다 방향 확인이 우선인 구간입니다.")

    if vp_poc:
        poc_gap_atr = (price - vp_poc) / atr
        if poc_gap_atr >= 0.4 and vp_long_rr >= vp_short_rr + 0.2:
            sentences.append(f"거래량 중심 가격대인 {poc_text} 위에서 롱 보상비가 더 좋아, 구조적으로는 지지 우위 쪽 해석이 가능합니다.")
        elif poc_gap_atr <= -0.4 and vp_short_rr >= vp_long_rr + 0.2:
            sentences.append(f"{poc_text} 아래에 머물고 숏 보상비가 더 좋아, 구조적으로는 저항 우위와 추가 하방 경계를 우선해야 합니다.")
        else:
            sentences.append(f"가격은 아직 {poc_text} 근처 균형대에 가까워, 방향이 한 번 더 정리되는 과정을 기다리는 구간으로 볼 수 있습니다.")

    if volume_ratio_20 >= 1.2 and volume_ratio_50 >= 1.0 and (chaikin > 0 or cmf > 0.03 or ad_line_z > 0.4):
        rs_text = "시장 대비 상대강도도 우위" if rs_ratio >= 1.02 and composite_accel > 0.2 else "수급도 나쁘지 않은 편"
        leader_text = " 리더주 성격도 동반돼" if leader_stock_mode else ""
        sentences.append(f"거래량과 자금 흐름이 함께 받쳐주고 있고 {rs_text}이며{leader_text} 신호 해석의 신뢰도는 비교적 괜찮은 편입니다.")
    elif bool(meta.get("thin_trade_risk")):
        sentences.append("다만 거래대금이 얇아 보이는 패턴보다 실제 체결의 질이 더 중요하므로, 신호 신뢰도는 한 단계 낮춰 보는 편이 안전합니다.")
    elif rs_ratio <= 0.98 and composite_accel < -0.2 and (chaikin < 0 or cmf < 0 or ad_line_z < -0.4):
        sentences.append("상대강도와 가속도가 시장보다 약하고 수급도 빠지는 편이라, 같은 반등이 나와도 다른 강한 종목보다 해석 우선순위는 낮습니다.")
    elif mass_index >= 26.5 and atr_pct >= 4:
        sentences.append("변동성 확장 신호도 올라와 있어 같은 방향 추세가 이어지더라도 중간 흔들림은 커질 수 있습니다.")
    elif disparity_20 >= 5 or disparity_50 >= 8 or channel_position >= 30:
        sentences.append("채널 상단과 이동평균 이격이 함께 높아져 있어 방향은 살아 있어도 추격 진입은 손익비가 나빠질 수 있습니다.")
    elif disparity_20 <= -5 or disparity_50 <= -8 or channel_position <= -30:
        sentences.append("채널 하단과 이격 완화 구간이라 기술적 반등 여지는 있지만, 추세 전환으로 보기 전 지지 확인이 먼저 필요합니다.")

    ordered = _ordered_unique(sentences)
    if len(ordered) <= 6:
        return " ".join(ordered)
    return " ".join(ordered[:5] + [ordered[-1]])


def _fmt_chart_price(value):
    value = _safe_float(value, float("nan"))
    if not math.isfinite(value) or value <= 0:
        return ""
    return f"${value:.2f}"


def _chart_headline_text(meta):
    ticker = str(meta.get("ticker", "")).upper()
    date_text = str(meta.get("last_date", "")).strip()
    change_pct = _safe_float(meta.get("price_change_pct", 0))
    price = _safe_float(meta.get("price", 0))
    vwap = _safe_float(meta.get("vwap", 0))
    percent_b = _safe_float(meta.get("percent_b", 0.5))
    rsi = _safe_float(meta.get("rsi", 50))
    rmi = _safe_float(meta.get("rmi", 50))
    wt1 = _safe_float(meta.get("wt1", 0))
    macd_hist = _safe_float(meta.get("macd_hist", 0))

    bullish = sum([price >= vwap if vwap else False, rsi >= 55, rmi >= 55, wt1 > 0, macd_hist > 0])
    bearish = sum([price < vwap if vwap else False, rsi <= 45, rmi <= 45, wt1 < 0, macd_hist < 0])

    if bullish >= 4:
        core = "추세 우위 유지"
    elif bearish >= 4:
        core = "기준선 아래 약세 압력"
    elif percent_b <= 0.18:
        core = "하단 눌림 반등 시험"
    elif percent_b >= 0.82:
        core = "상단 과열 부담 점검"
    else:
        core = "방향성 재정리 구간"

    move = "상승" if change_pct > 0 else ("하락" if change_pct < 0 else "보합")
    prefix = f"{ticker} 분석" if ticker else "종목 분석"
    suffix = f" ({date_text})" if date_text else ""
    return f"{prefix}{suffix}: {change_pct:+.2f}% {move} · {core} · 종가 ({_fmt_chart_price(price)})"


def _chart_volume_text(meta):
    volume = _safe_float(meta.get("volume", 0))
    avg_volume = max(_safe_float(meta.get("avg_volume", 1), 1), 1)
    volume_ratio = volume / avg_volume
    chaikin = _safe_float(meta.get("chaikin_oscillator", 0))
    cmf = _safe_float(meta.get("cmf", 0))
    ad_line_z = _safe_float(meta.get("ad_line_z", 0))
    thin_trade = bool(meta.get("thin_trade_risk"))
    change_pct = _safe_float(meta.get("price_change_pct", 0))

    if thin_trade:
        return f"거래량은 평균 대비 {volume_ratio:.1f}배 수준으로 얇은 편이라, 신호보다 실제 체결 강도와 슬리피지를 더 보수적으로 해석하는 편이 좋습니다."
    if volume_ratio >= 1.5 and (chaikin > 0 or cmf > 0.03 or ad_line_z > 0.4):
        return f"거래량은 평균 대비 {volume_ratio:.1f}배로 강하고 자금 유입도 동반돼, 현재 방향 해석의 신뢰도가 비교적 높은 편입니다."
    if volume_ratio >= 1.3 and change_pct < 0 and (chaikin <= 0 or cmf < 0):
        return f"거래량은 평균 대비 {volume_ratio:.1f}배로 늘었지만 수급은 약해, 매도 압력 확인 구간으로 읽는 편이 자연스럽습니다."
    if volume_ratio <= 0.8 and change_pct < 0:
        return f"거래량은 평균 대비 {volume_ratio:.1f}배로 크지 않아, 하락 자체보다 아직 확정 매물인지 여부를 더 확인해야 하는 장면입니다."
    if volume_ratio <= 0.8 and change_pct > 0:
        return f"거래량은 평균 대비 {volume_ratio:.1f}배로 가벼운 편이라, 상승이 이어지려면 추가 거래량 유입이 필요합니다."
    return f"거래량은 평균 대비 {volume_ratio:.1f}배 수준으로 무난하며, 가격 방향에 비해 수급은 아직 한쪽으로 과하게 쏠리지는 않았습니다."


def _chart_pattern_text(meta):
    recent_payloads = _recent_signal_payloads(meta, limit=2)
    if recent_payloads:
        labels = [str(item.get("label") or "").strip() for item in recent_payloads if str(item.get("label") or "").strip()]
        if labels:
            headline = (
                f"최근에는 {_join_reason_phrases(labels)}가 함께 나타났고, 단기 방향성은 이 조합이 유지되는지 여부가 핵심입니다."
                if len(labels) >= 2
                else f"최근에는 {labels[0]} 신호가 가장 중요하게 보이며, 이 신호가 후속 추세로 이어지는지 확인하는 구간입니다."
            )
            explain_bits = []
            for payload in recent_payloads[:2]:
                label = str(payload.get("label") or "").strip()
                if not label:
                    continue
                meaning = _signal_explanation_text(payload)
                level_note = _signal_level_context(payload, meta)
                if level_note:
                    explain_bits.append(f"{_topic_text(label)} {meaning} 관련 가격대는 {level_note}입니다.")
                else:
                    explain_bits.append(f"{_topic_text(label)} {meaning}")
            if explain_bits:
                return f"{headline} {' '.join(explain_bits)}"
    if meta.get("diag_breakout_bull") or meta.get("box_breakout_bull") or meta.get("channel_breakout_bull") or meta.get("triangle_breakout_bull"):
        return "구조적으로는 돌파 패턴이 감지돼, 눌림 뒤 재상승이 이어질 수 있는지를 보는 구간입니다."
    if meta.get("diag_breakdown_bear") or meta.get("box_breakdown_bear") or meta.get("channel_breakdown_bear") or meta.get("triangle_breakdown_bear"):
        return "구조적으로는 지지 이탈 패턴이 감지돼, 반등이 나와도 저항 전환 여부를 먼저 확인해야 합니다."
    if meta.get("fib_618_reclaim"):
        return "피보나치 61.8% 구간 재탈환이 보여, 눌림 이후 지지 회복 시도가 나오는 장면으로 해석할 수 있습니다."
    if meta.get("fib_618_breakdown"):
        return "피보나치 61.8% 구간 이탈이 보여, 구조 훼손 가능성을 더 경계해야 하는 장면입니다."
    return "뚜렷한 단일 패턴 하나보다 여러 보조지표와 구조 신호를 함께 읽는 편이 더 정확한 구간입니다."


def _chart_levels_text(meta):
    supports, resistances = _collect_support_resistance_levels(meta)

    def fmt(items):
        rows = []
        for item in items[:3]:
            rows.append(f"{item['label']} ({_fmt_chart_price(item['value'])}) · {item['note']}")
        return " · ".join(rows)

    support_text = fmt(supports) or "아직 가까운 하단 지지선 정리가 부족합니다."
    resistance_text = fmt(resistances) or "아직 가까운 상단 저항선 정리가 부족합니다."
    return support_text, resistance_text


def _named_chart_level(label, value):
    value = _safe_float(value, 0)
    if value <= 0:
        return ""
    return f"{label} ({_fmt_chart_price(value)})"


def _chart_scenario_text(meta):
    price = _safe_float(meta.get("price", 0))
    vwap = _safe_float(meta.get("vwap", 0))
    vp_poc = _safe_float(meta.get("vp_poc", 0))
    vp_val = _safe_float(meta.get("vp_val", 0))
    vp_vah = _safe_float(meta.get("vp_vah", 0))
    fib_618 = _safe_float(meta.get("fib_618"), 0)
    fib_382 = _safe_float(meta.get("fib_382"), 0)
    vp_long_rr = _safe_float(meta.get("vp_long_rr", 0))
    vp_short_rr = _safe_float(meta.get("vp_short_rr", 0))
    rsi = _safe_float(meta.get("rsi", 50))
    rmi = _safe_float(meta.get("rmi", 50))
    macd_hist = _safe_float(meta.get("macd_hist", 0))
    chaikin = _safe_float(meta.get("chaikin_oscillator", 0))
    cmf = _safe_float(meta.get("cmf", 0))
    rs_ratio = _safe_float(meta.get("rs_ratio", 1))
    price_channel_up = _safe_float(meta.get("price_channel_up", 0))
    price_channel_low = _safe_float(meta.get("price_channel_low", 0))

    bull_markers = sum([price >= vwap if vwap else False, price >= vp_poc if vp_poc else False, rsi >= 55, rmi >= 55, macd_hist > 0, chaikin > 0 or cmf > 0, rs_ratio >= 1.0, vp_long_rr >= vp_short_rr])
    bear_markers = sum([price < vwap if vwap else False, price < vp_poc if vp_poc else False, rsi <= 45, rmi <= 45, macd_hist < 0, chaikin < 0 or cmf < 0, rs_ratio < 1.0, vp_short_rr > vp_long_rr])

    current_price = f"현재 가격 ({_fmt_chart_price(price)})" if price > 0 else "현재 가격"
    bull_levels = [_named_chart_level("VWAP", vwap), _named_chart_level("POC", vp_poc)]
    bear_levels = [_named_chart_level("POC", vp_poc), _named_chart_level("Fib 61.8", fib_618)]
    bull_reference = _join_reason_phrases([level for level in bull_levels if level]) or "핵심 기준선"
    bear_reference = _join_reason_phrases([level for level in bear_levels if level]) or "핵심 지지선"
    bullish_condition = f"{_join_reason_phrases([level for level in bull_levels if level])} 위 유지" if any(bull_levels) else "핵심 기준선 위 유지"
    bearish_condition = f"{_join_reason_phrases([level for level in bear_levels if level])} 이탈" if any(bear_levels) else "핵심 지지 이탈"
    if vp_vah > 0:
        bullish_target = f"VAH ({_fmt_chart_price(vp_vah)})"
    elif fib_382 > 0:
        bullish_target = f"Fib 38.2 ({_fmt_chart_price(fib_382)})"
    elif price_channel_up > 0:
        bullish_target = f"채널 상단 ({_fmt_chart_price(price_channel_up)})"
    else:
        bullish_target = ""

    if vp_val > 0:
        bearish_target = f"VAL ({_fmt_chart_price(vp_val)})"
    elif fib_618 > 0:
        bearish_target = f"Fib 61.8 ({_fmt_chart_price(fib_618)})"
    elif price_channel_low > 0:
        bearish_target = f"채널 하단 ({_fmt_chart_price(price_channel_low)})"
    else:
        bearish_target = ""

    if price >= max(vwap, vp_poc, 0):
        base = f"{current_price}은 {bull_reference} 위에 있어, 기준선 위 추세 유지 시도가 이어지는 베이스 시나리오가 우세합니다."
    elif price < min(x for x in [vwap, vp_poc] if x > 0) if any(x > 0 for x in [vwap, vp_poc]) else False:
        base = f"{current_price}은 {bear_reference}보다 약한 위치에 있어, 반등보다 회복 확인이 먼저인 베이스 시나리오입니다."
    else:
        base = f"{current_price}은 주요 기준선 사이에 있어, 방향을 다시 정리하는 베이스 시나리오로 보는 편이 자연스럽습니다."

    if bull_markers >= bear_markers + 2 and vp_long_rr >= max(vp_short_rr, 0.1):
        position_line = f"현재는 매수(롱) 포지션이 더 유리한 편입니다. 상방 가능성이 한 단계 우세하고, VP 기준 손익비도 롱 {vp_long_rr:.2f}배 vs 숏 {vp_short_rr:.2f}배입니다."
        aggressive_entry = _named_chart_level("POC", vp_poc) or _named_chart_level("VWAP", vwap) or _named_chart_level("Fib 61.8", fib_618)
        conservative_entry = bullish_target
        invalidation = _named_chart_level("Fib 61.8", fib_618) or _named_chart_level("VAL", vp_val) or _named_chart_level("POC", vp_poc)
        strategy_line = f"전략은 {bullish_condition}를 전제로, 공격적으로는 {aggressive_entry or '가까운 지지대'} 지지 확인 후 접근하고 보수적으로는 {conservative_entry or '상단 돌파'} 확인 뒤 추세 추종을 보는 편이 좋습니다. 무효화는 {invalidation or '핵심 지지'} 이탈입니다."
    elif bear_markers >= bull_markers + 2 and vp_short_rr >= max(vp_long_rr, 0.1):
        position_line = f"현재는 매도(숏) 포지션이 더 유리한 편입니다. 하방 가능성이 한 단계 우세하고, VP 기준 손익비도 숏 {vp_short_rr:.2f}배 vs 롱 {vp_long_rr:.2f}배입니다."
        aggressive_entry = _named_chart_level("POC", vp_poc) or _named_chart_level("VWAP", vwap) or _named_chart_level("VAH", vp_vah)
        conservative_entry = bearish_target
        invalidation = _named_chart_level("VWAP", vwap) or _named_chart_level("VAH", vp_vah) or _named_chart_level("POC", vp_poc)
        strategy_line = f"전략은 {bearish_condition}를 전제로, 공격적으로는 {aggressive_entry or '가까운 저항대'} 반등 실패를 보고 접근하고 보수적으로는 {conservative_entry or '하단 이탈'} 확인 뒤 추세 추종을 보는 편이 좋습니다. 무효화는 {invalidation or '핵심 저항'} 회복입니다."
    elif vp_long_rr > vp_short_rr:
        position_line = f"가능성은 아직 엇갈리지만 손익비만 보면 롱 {vp_long_rr:.2f}배가 숏 {vp_short_rr:.2f}배보다 나아, 눌림 매수 쪽이 조금 더 유리합니다."
        aggressive_entry = _named_chart_level("POC", vp_poc) or _named_chart_level("Fib 61.8", fib_618)
        invalidation = _named_chart_level("Fib 61.8", fib_618) or _named_chart_level("POC", vp_poc)
        strategy_line = f"전략은 성급한 추격보다 {aggressive_entry or '가까운 지지대'} 반응을 보는 쪽이 낫고, {invalidation or '핵심 지지'}가 무너지면 롱 시나리오는 다시 점검해야 합니다."
    elif vp_short_rr > vp_long_rr:
        position_line = f"가능성은 아직 엇갈리지만 손익비만 보면 숏 {vp_short_rr:.2f}배가 롱 {vp_long_rr:.2f}배보다 나아, 반등 매도 쪽이 조금 더 유리합니다."
        aggressive_entry = _named_chart_level("VWAP", vwap) or _named_chart_level("POC", vp_poc) or _named_chart_level("VAH", vp_vah)
        invalidation = _named_chart_level("VWAP", vwap) or _named_chart_level("VAH", vp_vah)
        strategy_line = f"전략은 급락 추격보다 {aggressive_entry or '가까운 저항대'} 반등 실패를 보는 쪽이 낫고, {invalidation or '핵심 저항'}를 회복하면 숏 시나리오는 다시 점검해야 합니다."
    else:
        position_line = f"현재는 롱 {vp_long_rr:.2f}배와 숏 {vp_short_rr:.2f}배의 손익비 차이가 크지 않아, 방향 우위보다 확인 신호가 더 중요합니다."
        strategy_line = f"전략은 {_named_chart_level('VWAP', vwap) or '기준선'}와 {_named_chart_level('POC', vp_poc) or '중심 가격대'} 사이에서 방향이 정리될 때까지 기다렸다가, 상단 안착 또는 하단 이탈 중 한쪽이 확정될 때 대응하는 편이 좋습니다."

    bull_line = f"상방 시나리오는 {bullish_condition} 시 {bullish_target or '상단 저항대'} 재도전입니다."
    bear_line = f"리스크 시나리오는 {bearish_condition} 이탈 시 {bearish_target or '다음 지지대'} 재확인입니다."
    return base, position_line, strategy_line, bull_line, bear_line


def _build_chart_summary_html(meta):
    headline = _chart_headline_text(meta)
    summary = _build_chart_tab_summary(meta)
    volume_text = _chart_volume_text(meta)
    pattern_text = _chart_pattern_text(meta)
    support_text, resistance_text = _chart_levels_text(meta)
    base_line, position_line, strategy_line, bull_line, bear_line = _chart_scenario_text(meta)

    overview_text = f"{summary} {volume_text}".strip()

    return _html_block(
        "<div class='sigl-note'><strong>차트 요약</strong><br>"
        f"<div class='sigl-summary' style='font-weight:700;margin-bottom:8px'>{_esc(headline)}</div>"
        "<div class='sigl-summary' style='margin-bottom:8px'><strong>내용 요약</strong>: "
        f"{_esc(overview_text)}</div>"
        "<div class='sigl-summary' style='margin-bottom:6px'><strong>패턴 / 시그널 해석</strong>: "
        f"{_esc(pattern_text)}</div>"
        "<div class='sigl-summary' style='margin-bottom:6px'><strong>핵심 지지선</strong>: "
        f"{_esc(support_text)}</div>"
        "<div class='sigl-summary' style='margin-bottom:6px'><strong>핵심 저항선</strong>: "
        f"{_esc(resistance_text)}</div>"
        f"<div class='sigl-summary' style='margin-bottom:4px'><strong>포지션 우위</strong>: {_esc(position_line)}</div>"
        f"<div class='sigl-summary' style='margin-bottom:6px'><strong>전략 포인트</strong>: {_esc(strategy_line)}</div>"
        "<div class='sigl-summary' style='margin-bottom:4px'><strong>시나리오</strong>: "
        f"{_esc(base_line)}</div>"
        f"<div class='sigl-summary'>• {_esc(bull_line)}</div>"
        f"<div class='sigl-summary'>• {_esc(bear_line)}</div>"
        "</div>"
    )


def render_chart_indicator_snapshot(meta):
    price = _safe_float(meta.get("price", 0))
    vwap = _safe_float(meta.get("vwap", 0))
    fixed_vwap = _safe_float(meta.get("fixed_vwap", 0))
    envelope_percent = _safe_float(meta.get("envelope_percent", 0.5))
    psar_dir = _safe_int(meta.get("psar_dir", 0))
    williams_r = _safe_float(meta.get("williams_r", -50))
    cci = _safe_float(meta.get("cci", 0))
    roc = _safe_float(meta.get("roc", 0))
    rmi = _safe_float(meta.get("rmi", 50))
    trix = _safe_float(meta.get("trix", 0))
    momentum_10 = _safe_float(meta.get("momentum_10", 0))
    mass_index = _safe_float(meta.get("mass_index", 0))
    vol_osc = _safe_float(meta.get("volume_oscillator", 0))
    intensity_idx = _safe_float(meta.get("intraday_intensity_index", 0))
    chaikin = _safe_float(meta.get("chaikin_oscillator", 0))
    obv_trend = str(meta.get("obv_trend", "flat"))
    rsi = _safe_float(meta.get("rsi", 50))
    mfi = _safe_float(meta.get("mfi", 50))
    stochk = _safe_float(meta.get("stochk", 50))
    wt1 = _safe_float(meta.get("wt1", 0))
    macd_hist = _safe_float(meta.get("macd_hist", 0))
    cmf = _safe_float(meta.get("cmf", 0))
    obv_slope = _safe_float(meta.get("obv_slope", 0))
    composite_accel = _safe_float(meta.get("composite_accel", 0))
    rs_ratio = _safe_float(meta.get("rs_ratio", 1))
    adx = _safe_float(meta.get("adx", 0))
    atr_pct = _safe_float(meta.get("atr_pct", 0))
    volume_ratio_20 = _safe_float(meta.get("volume_ratio_20", 1))
    volume_ratio_50 = _safe_float(meta.get("volume_ratio_50", 1))
    dollar_volume_20 = _safe_float(meta.get("dollar_volume_20", 0))
    dollar_volume_z = _safe_float(meta.get("dollar_volume_z", 0))
    price_slope_5_pct = _safe_float(meta.get("price_slope_5_pct", _safe_float(meta.get("price_slope_5", 0)) * 100.0))
    excess_return_20 = _safe_float(meta.get("excess_return_20", 0))
    ma20_atr_gap = _safe_float(meta.get("ma20_atr_gap", 0))
    channel_position = _safe_float(meta.get("channel_position", 0))
    supertrend_gap = _safe_float(meta.get("supertrend_gap", 0))
    ad_line_z = _safe_float(meta.get("ad_line_z", 0))
    tenkan_gap = _safe_float(meta.get("tenkan_gap", 0))
    kijun_gap = _safe_float(meta.get("kijun_gap", 0))
    cloud_spread = _safe_float(meta.get("cloud_spread", 0))
    disparity_20 = _safe_float(meta.get("disparity_20", 0))
    disparity_50 = _safe_float(meta.get("disparity_50", 0))
    disparity_200 = _safe_float(meta.get("disparity_200", 0))
    ensemble_score = _safe_float(meta.get("ensemble_score", 0))
    buy_agree = _safe_float(meta.get("buy_agree", 0))
    sell_agree = _safe_float(meta.get("sell_agree", 0))
    continuation_buy = _safe_float(meta.get("continuation_buy_score", 0))
    continuation_sell = _safe_float(meta.get("continuation_sell_score", 0))
    trend_inflection_buy = _safe_float(meta.get("trend_inflection_buy_score", 0))
    trend_inflection_sell = _safe_float(meta.get("trend_inflection_sell_score", 0))
    market_turn_bull = _safe_float(meta.get("market_turn_bull_score", 0))
    market_turn_bear = _safe_float(meta.get("market_turn_bear_score", 0))
    breadth_score = _safe_float(meta.get("market_breadth_score", 0))
    macro_pressure = _safe_float(meta.get("macro_pressure_score", 0))

    def _clip(value, lo=-1.0, hi=1.0):
        return max(lo, min(hi, value))

    def _bar_colors(values):
        return [SOFT_GREEN if value >= 0 else SOFT_RED for value in values]

    def _base_layout(fig, title, x_range=(-1.05, 1.05), height=390, left_margin=118):
        fig.update_layout(
            title=dict(text=title, x=0.02, xanchor="left", font=dict(size=15, family=PLOTLY_FONT_FAMILY)),
            height=height,
            margin=dict(l=left_margin, r=28, t=62, b=26),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#E2E8F0", family=PLOTLY_FONT_FAMILY),
            xaxis=dict(
                range=list(x_range),
                gridcolor="rgba(51,65,85,.25)",
                zerolinecolor="rgba(148,163,184,.40)",
                tickfont=dict(size=10),
                automargin=True,
            ),
            yaxis=dict(
                gridcolor="rgba(0,0,0,0)",
                tickfont=dict(size=11),
                automargin=True,
            ),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1.0, font=dict(size=10)),
        )
        fig.add_vline(x=0, line_width=1, line_color="rgba(148,163,184,.45)")

    component_labels = ["추세", "모멘텀", "수급", "반전", "가격 위치", "시그널", "콤보"]
    buy_values = [
        _safe_float(meta.get("objective_trend_buy", 0)),
        _safe_float(meta.get("objective_momentum_buy", 0)),
        _safe_float(meta.get("objective_money_buy", 0)),
        _safe_float(meta.get("objective_reversal_buy", 0)),
        _safe_float(meta.get("objective_location_buy", 0)),
        _safe_float(meta.get("objective_signal_buy", 0)),
        _safe_float(meta.get("objective_combo_buy", 0)),
    ]
    sell_values = [
        -_safe_float(meta.get("objective_trend_sell", 0)),
        -_safe_float(meta.get("objective_momentum_sell", 0)),
        -_safe_float(meta.get("objective_money_sell", 0)),
        -_safe_float(meta.get("objective_reversal_sell", 0)),
        -_safe_float(meta.get("objective_location_sell", 0)),
        -_safe_float(meta.get("objective_signal_sell", 0)),
        -_safe_float(meta.get("objective_combo_sell", 0)),
    ]

    objective_indicator_labels = ["VWAP", "고정 VWAP", "Envelope", "PSAR", "Williams %R", "CCI", "ROC", "RMI", "TRIX", "Momentum", "Vol Osc", "강도", "Chaikin", "OBV"]
    objective_indicator_scores = [
        1.0 if price >= vwap else -1.0,
        1.0 if price >= fixed_vwap else -1.0,
        _clip((0.5 - envelope_percent) / 0.5),
        1.0 if psar_dir >= 0 else -1.0,
        _clip(((-50.0) - williams_r) / 50.0),
        _clip((-cci) / 200.0),
        _clip(roc / 5.0),
        _clip((rmi - 50.0) / 25.0),
        _clip(trix / 1.5),
        _clip(momentum_10 / max(abs(price) * 0.03, 1e-6)),
        _clip(vol_osc / 20.0),
        _clip(intensity_idx / 25.0),
        _clip(chaikin / max(abs(chaikin), 3.0)),
        1.0 if obv_trend == "rising" else -1.0,
    ]
    objective_indicator_meta = [
        f"{vwap:.2f}",
        f"{fixed_vwap:.2f}",
        f"{envelope_percent:.2f}",
        "상승" if psar_dir >= 0 else "하락",
        f"{williams_r:.0f}",
        f"{cci:.0f}",
        f"{roc:+.1f}",
        f"{rmi:.0f}",
        f"{trix:+.2f}",
        f"{momentum_10:+.2f}",
        f"{vol_osc:+.1f}",
        f"{intensity_idx:+.1f}",
        f"{chaikin:+.2f}",
        "상승" if obv_trend == "rising" else "하락",
    ]

    legacy_labels = ["WT1", "RSI", "MFI", "Stoch", "MACD Hist", "CMF", "OBV Slope", "CompAccel", "RS Ratio", "ADX 품질", "ATR 리스크"]
    legacy_scores = [
        _clip(wt1 / 60.0),
        _clip((rsi - 50.0) / 20.0),
        _clip((mfi - 50.0) / 20.0),
        _clip((stochk - 50.0) / 25.0),
        _clip(macd_hist / 0.8),
        _clip(cmf / 0.12),
        _clip(obv_slope / 0.6),
        _clip(composite_accel / 1.6),
        _clip((rs_ratio - 1.0) / 0.08),
        _clip(((adx - 20.0) / 15.0) * (1 if rsi >= 50 else -1)),
        _clip(-(atr_pct - 3.0) / 3.0),
    ]
    legacy_meta = [
        f"{wt1:+.1f}",
        f"{rsi:.1f}",
        f"{mfi:.1f}",
        f"{stochk:.1f}",
        f"{macd_hist:+.3f}",
        f"{cmf:+.3f}",
        f"{obv_slope:+.3f}",
        f"{composite_accel:+.2f}",
        f"{rs_ratio:.3f}",
        f"{adx:.1f}",
        f"{atr_pct:.2f}%",
    ]

    supplemental_raw_labels = [
        "Vol R20",
        "Vol R50",
        "Dollar Vol",
        "Slope 5d",
        "Excess 20d",
        "MA20/ATR",
        "Channel Pos",
        "ST Gap",
        "Disp20",
        "Disp50",
        "Disp200",
        "AD Line Z",
        "Mass",
        "Tenkan Gap",
        "Kijun Gap",
        "Cloud",
    ]
    supplemental_raw_scores = [
        _clip((volume_ratio_20 - 1.0) / 0.7),
        _clip((volume_ratio_50 - 1.0) / 0.7),
        _clip(dollar_volume_z / 2.0),
        _clip(price_slope_5_pct / 6.0),
        _clip(excess_return_20 / 8.0),
        _clip(ma20_atr_gap / 3.0),
        _clip(channel_position / 50.0),
        _clip(supertrend_gap / 4.0),
        _clip(disparity_20 / 6.0),
        _clip(disparity_50 / 8.0),
        _clip(disparity_200 / 12.0),
        _clip(ad_line_z / 2.0),
        _clip((26.5 - mass_index) / 2.5),
        _clip(tenkan_gap / 6.0),
        _clip(kijun_gap / 8.0),
        _clip(cloud_spread / 6.0),
    ]
    supplemental_raw_meta = [
        f"{volume_ratio_20:.2f}",
        f"{volume_ratio_50:.2f}",
        f"${dollar_volume_20:,.0f}",
        f"{price_slope_5_pct:+.2f}%",
        f"{excess_return_20:+.2f}%",
        f"{ma20_atr_gap:+.2f}",
        f"{channel_position:+.1f}",
        f"{supertrend_gap:+.2f}%",
        f"{disparity_20:+.2f}",
        f"{disparity_50:+.2f}",
        f"{disparity_200:+.2f}",
        f"{ad_line_z:+.2f}",
        f"{mass_index:.2f}",
        f"{tenkan_gap:+.2f}%",
        f"{kijun_gap:+.2f}%",
        f"{cloud_spread:+.2f}%",
    ]

    system_labels = ["Ensemble", "합의 차", "지속 축", "전환 축", "시장 전환", "시장 폭", "거시 압력", "판단 신뢰", "리더주 모드"]
    confidence = _safe_float(meta.get("confidence", 0))
    system_scores = [
        _clip(ensemble_score / 50.0),
        _clip((buy_agree - sell_agree) / 4.0),
        _clip((continuation_buy - continuation_sell) / 3.0),
        _clip((trend_inflection_buy - trend_inflection_sell) / 3.0),
        _clip((market_turn_bull - market_turn_bear) / 3.0),
        _clip(breadth_score / 3.0),
        _clip((-macro_pressure) / 3.0),
        _clip((confidence - 50.0) / 35.0),
        1.0 if meta.get("leader_stock_mode") else (-0.2 if meta.get("narrow_leadership") else 0.0),
    ]
    system_meta = [
        f"{ensemble_score:+.1f}",
        f"{buy_agree:.0f}:{sell_agree:.0f}",
        f"{continuation_buy:.1f}/{continuation_sell:.1f}",
        f"{trend_inflection_buy:.1f}/{trend_inflection_sell:.1f}",
        f"{market_turn_bull:.1f}/{market_turn_bear:.1f}",
        f"{breadth_score:+.1f}",
        f"{macro_pressure:+.1f}",
        f"{confidence:.0f}%",
        "ON" if meta.get("leader_stock_mode") else "OFF",
    ]

    raw_indicator_labels = legacy_labels + objective_indicator_labels + supplemental_raw_labels
    raw_indicator_scores = legacy_scores + objective_indicator_scores + supplemental_raw_scores
    raw_indicator_meta = legacy_meta + objective_indicator_meta + supplemental_raw_meta

    st.markdown("#### 보조 차트")
    st.caption("왼쪽은 엔진 해석 요약 축이고, 오른쪽은 기존 + 추가 지표의 최신값을 정규화한 방향성 요약 축입니다. 오른쪽은 원시 시계열 전체를 그대로 펼친 것이 아니라, 최신 상태를 한눈에 비교하기 위한 스냅샷입니다.")

    col_left, col_right = st.columns([0.92, 1.08])
    with col_left:
        st.caption("엔진 해석 요약")
        component_range = max(max(buy_values or [0]), max(abs(v) for v in sell_values) if sell_values else 0, 1.0) * 1.15
        objective_component_fig = go.Figure()
        objective_component_fig.add_trace(go.Bar(
            x=buy_values,
            y=component_labels,
            orientation="h",
            name="매수",
            marker_color=SOFT_GREEN,
            opacity=0.88,
            hovertemplate="매수 %{y}: %{x:.1f}<extra></extra>",
        ))
        objective_component_fig.add_trace(go.Bar(
            x=sell_values,
            y=component_labels,
            orientation="h",
            name="매도",
            marker_color=SOFT_RED,
            opacity=0.82,
            hovertemplate="매도 %{y}: %{x:.1f}<extra></extra>",
        ))
        objective_component_fig.update_layout(barmode="relative")
        component_height = _category_chart_height(len(component_labels), min_height=360, per_item=38, extra=120)
        _base_layout(objective_component_fig, "매수 vs 매도 축 비교", x_range=(-component_range, component_range), height=component_height, left_margin=108)
        st.plotly_chart(objective_component_fig, use_container_width=True, theme=None, config={"displayModeBar": False})

        system_fig = go.Figure(go.Bar(
            x=system_scores,
            y=system_labels,
            orientation="h",
            marker_color=_bar_colors(system_scores),
            opacity=0.86,
            customdata=system_meta,
            hovertemplate="%{y}: %{customdata}<br>정규화 %{x:+.2f}<extra></extra>",
        ))
        system_height = _category_chart_height(len(system_labels), min_height=380, per_item=38, extra=128)
        _base_layout(system_fig, "시장 / 시스템 상태축", height=system_height, left_margin=124)
        st.plotly_chart(system_fig, use_container_width=True, theme=None, config={"displayModeBar": False})

    with col_right:
        st.caption("원시 지표 기반 방향성 요약")
        raw_indicator_fig = go.Figure(go.Bar(
            x=raw_indicator_scores,
            y=raw_indicator_labels,
            orientation="h",
            marker_color=_bar_colors(raw_indicator_scores),
            opacity=0.86,
            customdata=raw_indicator_meta,
            hovertemplate="%{y}: %{customdata}<br>정규화 %{x:+.2f}<extra></extra>",
        ))
        raw_height = _category_chart_height(len(raw_indicator_labels), min_height=1180, per_item=28, extra=150)
        _base_layout(raw_indicator_fig, "원시 지표 최신 스냅샷", height=raw_height, left_margin=144)
        st.plotly_chart(raw_indicator_fig, use_container_width=True, theme=None, config={"displayModeBar": False})

    chart_badges = _build_chart_interpretation_badges(meta)
    if chart_badges:
        st.markdown(
            _html_block(
                "<div class='sigl-note'><strong>한눈에 해석</strong><br>"
                f"<div class='sigl-chip-row'>{chart_badges}</div>"
                f"<div class='sigl-chip-row'>{_build_chart_interpretation_detail_badges(meta)}</div>"
                "</div>"
            ),
            unsafe_allow_html=True,
        )


def render_judgment_card(meta):
    raw_judgment = str(meta.get("judgment", "NEUTRAL"))
    action = localize_action_label(meta.get("action_label", ""))
    tone = _tone_from_text(raw_judgment or action)
    title = _display_action_title(meta, action or localize_judgment_label(raw_judgment))
    es = _safe_float(meta.get("ensemble_score", 0))
    confidence = _safe_float(meta.get("confidence", 0))
    buy_agree = _safe_int(meta.get("buy_agree", 0))
    sell_agree = _safe_int(meta.get("sell_agree", 0))
    detail_text = _translate_note_text(meta.get("judgment_detail") or meta.get("judgment_reason") or "")
    contrast = _translate_note_text(meta.get("contrast_notes", ""))

    reversal_synergy = _safe_float(meta.get("reversal_synergy", 0))
    prediction_boost = _safe_float(meta.get("prediction_boost", 0))
    pre_veto_label = localize_judgment_label(str(meta.get("pre_veto_judgment", "")).strip())
    downgrade_count = _safe_int(meta.get("downgrade_count", 0))
    market_filter_bias = _safe_float(meta.get("market_filter_bias", 0))
    continuation_buy = _safe_float(meta.get("continuation_buy_score", 0))
    continuation_sell = _safe_float(meta.get("continuation_sell_score", 0))
    trend_inflection_buy = _safe_float(meta.get("trend_inflection_buy_score", 0))
    trend_inflection_sell = _safe_float(meta.get("trend_inflection_sell_score", 0))
    market_turn_bull_score = _safe_float(meta.get("market_turn_bull_score", 0))
    market_turn_bear_score = _safe_float(meta.get("market_turn_bear_score", 0))
    macro_pressure = _safe_float(meta.get("macro_pressure_score", 0))
    breadth_score = _safe_float(meta.get("market_breadth_score", 0))
    objective_buy_score = _safe_float(meta.get("objective_buy_score", 0))
    objective_sell_score = _safe_float(meta.get("objective_sell_score", 0))
    objective_conflict_score = _safe_float(meta.get("objective_conflict_score", 0))
    objective_label = localize_judgment_label(str(meta.get("objective_judgment", "NEUTRAL")))
    objective_confidence = _safe_float(meta.get("objective_confidence", 0))
    objective_alignment = str(meta.get("objective_alignment", "MIXED")).upper()
    objective_adjustment = str(meta.get("objective_adjustment", "NONE")).upper()
    objective_reason = _translate_note_text(meta.get("objective_reason", ""))
    objective_alignment_label = {"ALIGNED": "일치", "CONFLICT": "충돌", "MIXED": "혼합"}.get(objective_alignment, objective_alignment)
    objective_adjustment_label = {"NONE": "없음", "CONFIRM": "확인", "UPGRADE": "강화", "ACTIVATE": "활성", "DOWNGRADE": "보수조정", "MIXED": "혼합보정"}.get(objective_adjustment, objective_adjustment)
    ut_gap = max(_safe_float(meta.get("utbot_stop_atr_gap", 0)), 0.0)
    macro_risk_off_count = _safe_int(meta.get("macro_risk_off_count", 0))
    macro_risk_on_count = _safe_int(meta.get("macro_risk_on_count", 0))

    badges = []
    if abs(reversal_synergy) > 5:
        badges.append(_badge(f"반전 시너지 {reversal_synergy:+.1f}", "positive" if reversal_synergy > 0 else "negative"))
    if abs(prediction_boost) > 3:
        badges.append(_badge(f"예측 보정 {prediction_boost:+.1f}", "positive" if prediction_boost > 0 else "negative"))
    if meta.get("leader_stock_mode"):
        badges.append(_badge("리더주 모드", "positive"))

    explain_tags = []
    if macro_risk_on_count:
        explain_tags.append(_badge(f"거시 우호 {macro_risk_on_count}", "positive"))
    if macro_risk_off_count:
        explain_tags.append(_badge(f"거시 역풍 {macro_risk_off_count}", "negative"))
    if meta.get("market_turn_bull"):
        explain_tags.append(_badge("시장 전환 초기 강세", "positive"))
    if meta.get("market_turn_bear"):
        explain_tags.append(_badge("시장 전환 초기 약세", "negative"))
    if meta.get("trend_inflection_bull"):
        explain_tags.append(_badge("종목 추세 전환 매수", "positive"))
    if meta.get("trend_inflection_bear"):
        explain_tags.append(_badge("종목 추세 전환 매도", "negative"))
    if meta.get("breadth_risk_on"):
        explain_tags.append(_badge("시장 폭 확산", "positive"))
    if meta.get("breadth_risk_off"):
        explain_tags.append(_badge("시장 폭 약화", "negative"))
    if meta.get("narrow_leadership"):
        explain_tags.append(_badge("메가캡 쏠림", "warning"))
    if meta.get("bullish_gap_reversal"):
        explain_tags.append(_badge("갭다운 회복", "positive"))
    if meta.get("bearish_gap_failure"):
        explain_tags.append(_badge("갭업 실패", "negative"))
    if meta.get("diag_support_hold"):
        explain_tags.append(_badge("사선 지지", "positive"))
    if meta.get("diag_breakout_bull"):
        explain_tags.append(_badge("사선 돌파", "positive"))
    if meta.get("diag_resistance_reject"):
        explain_tags.append(_badge("사선 저항", "negative"))
    if meta.get("diag_breakdown_bear"):
        explain_tags.append(_badge("사선 이탈", "negative"))
    if meta.get("box_support_hold"):
        explain_tags.append(_badge("박스 지지", "positive"))
    if meta.get("box_breakout_bull"):
        explain_tags.append(_badge("박스 돌파", "positive"))
    if meta.get("channel_support_hold"):
        explain_tags.append(_badge("채널 지지", "positive"))
    if meta.get("channel_breakout_bull"):
        explain_tags.append(_badge("채널 돌파", "positive"))
    if meta.get("triangle_breakout_bull"):
        explain_tags.append(_badge("삼각 돌파", "positive"))
    if meta.get("box_resistance_reject"):
        explain_tags.append(_badge("박스 저항", "negative"))
    if meta.get("box_breakdown_bear"):
        explain_tags.append(_badge("박스 이탈", "negative"))
    if meta.get("channel_resistance_reject"):
        explain_tags.append(_badge("채널 저항", "negative"))
    if meta.get("channel_breakdown_bear"):
        explain_tags.append(_badge("채널 이탈", "negative"))
    if meta.get("triangle_breakdown_bear"):
        explain_tags.append(_badge("삼각 이탈", "negative"))
    if meta.get("fractal_low"):
        explain_tags.append(_badge("Fractal Low", "positive"))
    if meta.get("fractal_high"):
        explain_tags.append(_badge("Fractal High", "negative"))
    if _safe_int(meta.get("psar_dir", 0)) >= 0:
        explain_tags.append(_badge("PSAR 상승", "positive"))
    else:
        explain_tags.append(_badge("PSAR 하락", "negative"))

    risk_tags = []
    if meta.get("flip_guard_triggered"):
        risk_tags.append(_badge("급반전 보호", "warning"))
    if meta.get("thin_trade_risk"):
        risk_tags.append(_badge("얇은 거래대금", "warning"))
    if ut_gap >= 2.0 and continuation_buy >= continuation_sell:
        risk_tags.append(_badge("UT 과열", "warning"))
    if breadth_score < -0.5:
        risk_tags.append(_badge("시장 breadth 약세", "negative"))

    flow_cards = [
        _mini_stat_card("초기 판단", pre_veto_label or title or "-", _tone_from_text(pre_veto_label or title or "")),
        _mini_stat_card("최종 판단", title or localize_judgment_label(raw_judgment), tone),
        _mini_stat_card("강등 횟수", f"{downgrade_count}회", "warning" if downgrade_count else "muted"),
        _mini_stat_card("시장 필터", f"{market_filter_bias:+.1f}", "positive" if market_filter_bias > 0.3 else "negative" if market_filter_bias < -0.3 else "warning"),
    ]
    driver_cards = [
        _mini_stat_card("지속 매수", f"{continuation_buy:.1f}", "positive" if continuation_buy >= max(continuation_sell, 1.0) else "muted"),
        _mini_stat_card("지속 매도", f"{continuation_sell:.1f}", "negative" if continuation_sell >= max(continuation_buy, 1.0) else "muted"),
        _mini_stat_card("추세 전환 매수", f"{trend_inflection_buy:.1f}", "positive" if trend_inflection_buy >= max(trend_inflection_sell, 1.0) else "muted"),
        _mini_stat_card("추세 전환 매도", f"{trend_inflection_sell:.1f}", "negative" if trend_inflection_sell >= max(trend_inflection_buy, 1.0) else "muted"),
        _mini_stat_card("시장 전환 강세", f"{market_turn_bull_score:.1f}", "positive" if market_turn_bull_score >= max(market_turn_bear_score, 1.0) else "muted"),
        _mini_stat_card("시장 전환 약세", f"{market_turn_bear_score:.1f}", "negative" if market_turn_bear_score >= max(market_turn_bull_score, 1.0) else "muted"),
        _mini_stat_card("거시 압력", f"{macro_pressure:+.1f}", "negative" if macro_pressure > 0.5 else "positive" if macro_pressure < -0.5 else "warning"),
        _mini_stat_card("UT 거리", f"{ut_gap:.2f} ATR", "positive" if ut_gap <= 0.9 else "negative" if ut_gap >= 2.0 else "warning"),
        _mini_stat_card("시장 폭", f"{breadth_score:+.1f}", "positive" if breadth_score > 0.5 else "negative" if breadth_score < -0.5 else "warning"),
    ]
    explainer_text = _judgment_explainer(meta, title)
    recap_text = _build_judgment_recap(meta, title)
    recap_headline = _build_recap_headline(meta)
    beginner_text = _build_beginner_explanation(meta, title)
    action_guide = _build_action_guide(meta, title)
    professional_reasons = _build_professional_reasons(meta)
    decisive_driver_badges = _build_decisive_driver_badges(meta, title)
    compare_html = _build_reason_compare_html(meta)
    pro_reason_html = "".join(
        f"<div class='sigl-summary' style='margin-bottom:6px'>• {_esc(line)}</div>"
        for line in professional_reasons
    )
    recent_signal_badges = "".join(
        _badge(label, tone_name)
        for label, tone_name in _recent_signal_items(meta, limit=None)
    )
    recent_signal_explanations = _build_signal_explanation_html(meta, limit=None)
    objective_badges = _build_objective_indicator_badges(meta)
    objective_pairs = [
        ("추세", _safe_float(meta.get("objective_trend_buy", 0)), _safe_float(meta.get("objective_trend_sell", 0))),
        ("모멘텀", _safe_float(meta.get("objective_momentum_buy", 0)), _safe_float(meta.get("objective_momentum_sell", 0))),
        ("수급", _safe_float(meta.get("objective_money_buy", 0)), _safe_float(meta.get("objective_money_sell", 0))),
        ("반전", _safe_float(meta.get("objective_reversal_buy", 0)), _safe_float(meta.get("objective_reversal_sell", 0))),
        ("가격 위치", _safe_float(meta.get("objective_location_buy", 0)), _safe_float(meta.get("objective_location_sell", 0))),
        ("시그널", _safe_float(meta.get("objective_signal_buy", 0)), _safe_float(meta.get("objective_signal_sell", 0))),
        ("콤보", _safe_float(meta.get("objective_combo_buy", 0)), _safe_float(meta.get("objective_combo_sell", 0))),
    ]
    leader_name, leader_buy, leader_sell = max(objective_pairs, key=lambda item: abs(item[1] - item[2]))
    objective_leader_text = f"{leader_name} {'매수' if leader_buy >= leader_sell else '매도'} 우위"
    objective_alignment_tone = {"ALIGNED": "positive", "CONFLICT": "negative", "MIXED": "warning"}.get(objective_alignment, "muted")
    objective_tone = _tone_from_text(objective_label)
    objective_summary_cards = [
        _mini_stat_card("객관 매수", f"{objective_buy_score:.1f}", "positive" if objective_buy_score >= objective_sell_score else "muted"),
        _mini_stat_card("객관 매도", f"{objective_sell_score:.1f}", "negative" if objective_sell_score >= objective_buy_score else "muted"),
        _mini_stat_card("충돌도", f"{objective_conflict_score:.1f}", "warning" if objective_conflict_score >= 1.5 else "muted"),
        _mini_stat_card("우세축", objective_leader_text, _objective_pair_tone(leader_buy, leader_sell)),
        _mini_stat_card("객관 판단", objective_label or "-", objective_tone),
        _mini_stat_card("객관 신뢰", f"{objective_confidence:.0f}%", objective_tone if objective_confidence >= 55 else "muted"),
    ]
    objective_meta_badges = "".join(
        badge
        for badge in [
            _badge(f"정렬 {objective_alignment_label}", objective_alignment_tone),
            _badge(f"보정 {objective_adjustment_label}", "accent" if objective_adjustment not in {"NONE", "MIXED"} else "muted"),
        ]
        if badge
    )
    same_note = bool(
        detail_text
        and contrast
        and (
            detail_text == contrast
            or _normalize_compare_text(detail_text) == _normalize_compare_text(contrast)
            or _normalize_compare_text(contrast) in _normalize_compare_text(detail_text)
        )
    )

    summary_html = f"""
    <div class="sigl-card sigl-card--{'positive' if tone == 'positive' else 'negative' if tone == 'negative' else 'warning'}">
      <div class="sigl-section-head">
        <div>
          <p class="sigl-section-title">종합 판단</p>
        </div>
        <div class="sigl-inline">{''.join(badges)}</div>
      </div>
      <div class="sigl-grid sigl-grid--3">
        {_progress_metric_card('결론', title or '중립', localize_judgment_label(raw_judgment), tone, confidence)}
        {_progress_metric_card('종합 점수', f'{es:+.1f}', f'신뢰도 {confidence:.0f}%', tone if tone != 'muted' else 'accent', min(abs(es) / 80 * 100, 100))}
        {_progress_metric_card('합의 비율', f'{buy_agree}:{sell_agree}', localize_context_label(meta.get('context', 0)), 'accent', buy_agree / max(buy_agree + sell_agree, 1) * 100)}
      </div>
    """
    if recap_text:
        headline_html = f"<div class='sigl-summary' style='font-weight:700;margin-bottom:6px'>{_esc(recap_headline)}</div>" if recap_headline else ""
        summary_html += f"<div class='sigl-note'><strong>한눈에 Recap</strong><br>{headline_html}<span class='sigl-summary'>{_esc(recap_text)}</span></div>"
    summary_html += (
        "<div class='sigl-note'><strong>객관 엔진 요약</strong>"
        f"<div class='sigl-grid sigl-grid--4'>{''.join(objective_summary_cards)}</div>"
        f"<div class='sigl-chip-row'>{objective_badges}{objective_meta_badges}</div>"
        "</div>"
    )
    if objective_reason:
        summary_html += f"<div class='sigl-note'><strong>객관 엔진 메모</strong><br><span class='sigl-summary'>{_esc(objective_reason)}</span></div>"
    if recent_signal_badges:
        summary_html += (
            "<div class='sigl-note'><strong>이날 발생한 시그널</strong>"
            f"<div class='sigl-chip-row'>{recent_signal_badges}</div>"
            f"{recent_signal_explanations}"
            "</div>"
        )
    if decisive_driver_badges:
        summary_html += f"<div class='sigl-note'><strong>결정타 3개</strong><div class='sigl-chip-row'>{decisive_driver_badges}</div></div>"
    if beginner_text:
        summary_html += f"<div class='sigl-note'><strong>쉽게 말해</strong><br><span class='sigl-summary'>{_esc(beginner_text)}</span></div>"
    reason_block_parts = []
    if explainer_text:
        reason_block_parts.append(
            f"<p class='sigl-summary' style='margin:0 0 10px'>{_esc(explainer_text)}</p>"
        )
    if pro_reason_html:
        reason_block_parts.append(pro_reason_html)
    if reason_block_parts:
        summary_html += (
            "<div class='sigl-note'><strong>왜 이런 판단이 나왔나</strong>"
            f"{''.join(reason_block_parts)}</div>"
        )
    if action_guide:
        summary_html += f"<div class='sigl-note'><strong>실전 대응</strong><br><span class='sigl-summary'>{_esc(action_guide)}</span></div>"
    if compare_html:
        summary_html += f"<div class='sigl-note'><strong>매수 vs 매도 근거</strong>{compare_html}</div>"
    summary_html += f"<div class='sigl-note'><strong>판단 경로</strong><div class='sigl-grid sigl-grid--4'>{''.join(flow_cards)}</div></div>"
    summary_html += f"<div class='sigl-note'><strong>핵심 근거</strong><div class='sigl-grid sigl-grid--4'>{''.join(driver_cards)}</div><div class='sigl-chip-row'>{''.join(explain_tags)}</div></div>"
    if detail_text and same_note:
        summary_html += f"<div class='sigl-note'><strong>전문 메모 / 리스크 체크</strong><br><span class='sigl-summary'>{_esc(detail_text)}</span><div class='sigl-chip-row'>{''.join(risk_tags)}</div></div>"
    else:
        if detail_text:
            summary_html += f"<div class='sigl-note'><strong>전문 메모</strong><br><span class='sigl-summary'>{_esc(detail_text)}</span></div>"
        if (contrast and not same_note) or risk_tags:
            contrast_html = f"<p class='sigl-summary' style='margin:0 0 10px'>{_esc(contrast)}</p>" if contrast and not same_note else ""
            summary_html += f"<div class='sigl-note'><strong>리스크 체크</strong>{contrast_html}<div class='sigl-chip-row'>{''.join(risk_tags)}</div></div>"
    summary_html += "</div>"
    _render_panel_html(
        summary_html,
        min_height=_judgment_panel_height(detail_text, contrast, len(risk_tags) + len(explain_tags)),
    )


def render_ai_signal_assisted_card(meta):
    ai = meta.get("ai_signal_assisted") or {}
    if not isinstance(ai, dict):
        return

    agreement_map = {
        "EXACT": ("정확히 일치", "positive"),
        "ALIGNED": ("같은 방향", "positive"),
        "MIXED": ("부분 불일치", "warning"),
        "DISAGREE": ("반대 의견", "negative"),
        "UNAVAILABLE": ("미사용", "muted"),
    }
    disagreement_map = {
        "NONE": "없음",
        "TIMING": "타이밍",
        "RISK": "리스크",
        "TREND": "방향",
        "MIXED": "혼합",
    }

    def _playbook_tone(style_text, fit_score):
        if any(token in str(style_text or "") for token in ("관망", "대기")):
            return "warning"
        if fit_score >= 70:
            return tone if tone in ("positive", "negative") else "accent"
        if fit_score >= 45:
            return "warning"
        return "muted"

    title = "AI SIGNAL-ASSISTED"
    subtitle = "엔진 점수 없이 OHLCV, 가격 구조, 보조지표, 시장 데이터, 차트 시그널 이벤트만으로 만든 독립 2차 의견입니다."
    if not ai.get("available"):
        reason = _translate_note_text(ai.get("AI_Reason") or ai.get("reason") or "AI 보조 판단을 생성하지 못했습니다.")
        _render_panel_html(
            f"""
            <div class="sigl-card">
              <div class="sigl-section-head">
                <div>
                  <p class="sigl-section-title">{title}</p>
                  <p class="sigl-section-copy">{subtitle}</p>
                </div>
                <div class="sigl-inline">{_badge('미사용', 'muted')}</div>
              </div>
              <div class="sigl-summary">{_esc(reason)}</div>
            </div>
            """
        )
        return

    engine_label = localize_judgment_label(str(meta.get("judgment", "NEUTRAL")))
    ai_label_raw = str(ai.get("AI_Judgment", "NEUTRAL"))
    ai_label = localize_judgment_label(ai_label_raw)
    tone = _tone_from_text(ai_label_raw or ai_label)
    ai_confidence = _safe_float(ai.get("AI_Confidence", 0))
    bullish = _safe_float(ai.get("AI_Bullish_Score", 0))
    bearish = _safe_float(ai.get("AI_Bearish_Score", 0))
    agreement_label, agreement_tone = agreement_map.get(ai.get("AI_Agreement"), ("확인 필요", "warning"))
    disagreement_label = disagreement_map.get(str(ai.get("AI_Disagreement_Type", "MIXED")).upper(), "혼합")
    reason = _translate_note_text(ai.get("AI_Reason", ""))
    trade_strategy = _translate_note_text(ai.get("AI_Trade_Strategy", ""))
    entry_plan = _translate_note_text(ai.get("AI_Entry_Plan", ""))
    invalidation = _translate_note_text(ai.get("AI_Invalidation", ""))
    target_plan = _translate_note_text(ai.get("AI_Target_Plan", ""))
    playbook = ai.get("AI_Strategy_Playbook") if isinstance(ai.get("AI_Strategy_Playbook"), list) else []
    drivers = [_translate_note_text(item) for item in (ai.get("AI_Key_Drivers") if isinstance(ai.get("AI_Key_Drivers"), list) else [])]
    risks = [_translate_note_text(item) for item in (ai.get("AI_Risk_Flags") if isinstance(ai.get("AI_Risk_Flags"), list) else [])]

    badges = [
        _badge(ai_label, tone),
        _badge(agreement_label, agreement_tone),
        _badge(f"불일치 유형 {disagreement_label}", "accent" if disagreement_label != "없음" else "muted"),
    ]
    driver_badges = "".join(_badge(item, tone) for item in drivers if str(item or "").strip())
    risk_badges = "".join(_badge(item, "warning") for item in risks if str(item or "").strip())

    summary_html = f"""
    <div class="sigl-card sigl-card--{'positive' if tone == 'positive' else 'negative' if tone == 'negative' else 'warning'}">
      <div class="sigl-section-head">
        <div>
          <p class="sigl-section-title">{title}</p>
          <p class="sigl-section-copy">{subtitle}</p>
        </div>
        <div class="sigl-inline">{''.join(badges)}</div>
      </div>
      <div class="sigl-grid sigl-grid--3">
        {_progress_metric_card('AI 판단', ai_label, f'엔진 판단 {engine_label}', tone, ai_confidence)}
        {_progress_metric_card('AI 신뢰도', f'{ai_confidence:.0f}%', agreement_label, tone, ai_confidence)}
        {_progress_metric_card('Bull vs Bear', f'{bullish:.0f} / {bearish:.0f}', disagreement_label, 'accent', bullish)}
      </div>
    """
    if reason:
        summary_html += f"<div class='sigl-note'><strong>AI 판단 이유</strong><br><span class='sigl-summary'>{_esc(reason)}</span></div>"
    if trade_strategy:
        summary_html += f"<div class='sigl-note'><strong>AI 매매전략</strong><br><span class='sigl-summary'>{_esc(trade_strategy)}</span></div>"
    summary_html += (
        f"<div class='sigl-note'><strong>비교 스냅샷</strong><div class='sigl-grid sigl-grid--4'>"
        f"{_mini_stat_card('엔진 판단', engine_label, _tone_from_text(str(meta.get('judgment', 'NEUTRAL'))))}"
        f"{_mini_stat_card('AI 판단', ai_label, tone)}"
        f"{_mini_stat_card('엔진 신뢰도', f'{_safe_float(meta.get('confidence', 0)):.0f}%', _tone_from_text(str(meta.get('judgment', 'NEUTRAL'))))}"
        f"{_mini_stat_card('불일치 유형', disagreement_label, 'accent' if disagreement_label != '없음' else 'muted')}"
        f"</div></div>"
    )
    if entry_plan or invalidation or target_plan:
        strategy_cards = []
        if entry_plan:
            strategy_cards.append(_mini_stat_card("진입 아이디어", entry_plan, tone))
        if invalidation:
            strategy_cards.append(_mini_stat_card("무효화 기준", invalidation, "warning"))
        if target_plan:
            strategy_cards.append(_mini_stat_card("목표 구간", target_plan, "accent"))
        summary_html += f"<div class='sigl-note'><strong>실행 플랜</strong><div class='sigl-grid sigl-grid--3'>{''.join(strategy_cards)}</div></div>"
    if playbook:
        playbook_cards = []
        for item in playbook[:5]:
            if not isinstance(item, dict):
                continue
            style_text = _translate_note_text(item.get("style", ""))
            fit_score = _safe_float(item.get("fit", 0))
            summary_text = _translate_note_text(item.get("summary", ""))
            entry_text = _translate_note_text(item.get("entry", ""))
            invalidation_text = _translate_note_text(item.get("invalidation", ""))
            target_text = _translate_note_text(item.get("target", ""))
            if not any([style_text, summary_text, entry_text, invalidation_text, target_text]):
                continue
            item_tone = _playbook_tone(style_text, fit_score)
            details = []
            if summary_text:
                details.append(f"<div class='sigl-summary' style='margin-bottom:8px'>{_esc(summary_text)}</div>")
            if entry_text:
                details.append(f"<div class='sigl-summary' style='margin-bottom:4px'><strong>진입</strong>: {_esc(entry_text)}</div>")
            if invalidation_text:
                details.append(f"<div class='sigl-summary' style='margin-bottom:4px'><strong>무효화</strong>: {_esc(invalidation_text)}</div>")
            if target_text:
                details.append(f"<div class='sigl-summary'><strong>목표</strong>: {_esc(target_text)}</div>")
            playbook_cards.append(
                "<div class='sigl-note'>"
                "<div style='display:flex;justify-content:space-between;gap:8px;align-items:center;margin-bottom:8px'>"
                f"<strong>{_esc(style_text or '전략')}</strong>"
                f"{_badge(f'적합도 {fit_score:.0f}%', item_tone)}"
                "</div>"
                f"{''.join(details)}"
                "</div>"
            )
        if playbook_cards:
            summary_html += (
                "<div class='sigl-note'><strong>스타일별 플레이북</strong>"
                f"<div class='sigl-grid sigl-grid--2' style='margin-top:12px'>{''.join(playbook_cards)}</div>"
                "</div>"
            )
    if driver_badges:
        summary_html += f"<div class='sigl-note'><strong>AI 핵심 근거</strong><div class='sigl-chip-row'>{driver_badges}</div></div>"
    if risk_badges:
        summary_html += f"<div class='sigl-note'><strong>AI 리스크 플래그</strong><div class='sigl-chip-row'>{risk_badges}</div></div>"
    summary_html += "</div>"
    _render_panel_html(summary_html)


def render_committee_panel(meta):
    committee = meta.get("committee", {})
    if not committee:
        return
    ctx_code = meta.get("context", 0)
    ctx_name = CTX_LABELS.get(ctx_code, "default")
    weights = CONTEXT_WEIGHTS.get(ctx_name, CONTEXT_WEIGHTS["default"])
    vote_map = {"BUY": "매수", "SELL": "매도", "NEUTRAL": "중립", "ABSTAIN": "보류"}
    cards = []
    for idx, committee_name in enumerate(COMMITTEE_NAMES):
        data = committee.get(committee_name, {})
        score = _safe_float(data.get("score", 0))
        conviction = _safe_float(data.get("conviction", 0))
        vote = str(data.get("vote", "NEUTRAL"))
        weight = weights[idx] if idx < len(weights) else 0.2
        tone = "positive" if score > 0 else ("negative" if score < 0 else "warning")
        cards.append(
            f"""
            <div class="sigl-committee-card" style="--tone:{_tone_color(tone)}">
              <p class="sigl-committee-name">{_esc(localize_committee_name(committee_name))} · 비중 {weight:.0%}</p>
              <p class="sigl-committee-score">{score:+.0f}</p>
              {_badge(vote_map.get(vote, vote), tone if tone != 'warning' else 'warning')}
              <p class="sigl-committee-foot">확신도 {conviction:.0f}%</p>
              <div class="sigl-progress"><div class="sigl-progress__fill" style="--fill:{min(abs(score) / 40 * 100, 100):.1f}%;--tone:{_tone_color(tone)}"></div></div>
            </div>
            """
        )
    panel_html = f"""
        <div class="sigl-card">
          <div class="sigl-section-head">
            <div>
              <p class="sigl-section-title">5위원회 종합 판단</p>
              <p class="sigl-section-copy">위원회별 점수와 확신도를 같은 규격으로 비교합니다.</p>
            </div>
          </div>
          <div class="sigl-grid sigl-grid--5">{''.join(cards)}</div>
        </div>
        """
    _render_panel_html(panel_html, min_height=_committee_panel_height(len(cards)))
    if meta.get("veto_flags"):
        st.warning(f"제한 조건: {meta.get('veto_flags')}")
    if abs(_safe_float(meta.get("reversal_synergy", 0))) > 5:
        st.info(f"반전 시너지: {_safe_float(meta.get('reversal_synergy', 0)):+.1f}")


def render_10layer_bars(meta, html_key="analysis"):
    del html_key
    layer_names = ["Trend", "Momentum", "Candle", "BB", "Volume", "MF", "Pattern", "Combined", "Leading", "Lagging"]
    layer_labels = {
        "Trend": "\uCD94\uC138",
        "Momentum": "\uBAA8\uBA58\uD140",
        "Candle": "\uCEA4\uB4E4",
        "BB": "\uBCFC\uB9B0\uC800",
        "Volume": "\uAC70\uB798\uB7C9",
        "MF": "\uC790\uAE08 \uD750\uB984",
        "Pattern": "\uD328\uD134",
        "Combined": "\uCF64\uBCF4",
        "Leading": "\uC120\uD589",
        "Lagging": "\uD6C4\uD589",
    }
    rows = []
    for name in layer_names:
        buy_value = max(_safe_float(meta.get("buy_layers", {}).get(name, 0)), 0.0)
        sell_value = max(_safe_float(meta.get("sell_layers", {}).get(name, 0)), 0.0)
        buy_pct = min((buy_value / 12.0) * 50.0, 50.0)
        sell_pct = min((sell_value / 12.0) * 50.0, 50.0)
        rows.append(
            f"""
            <div class="sigl-layer-row">
              <div class="sigl-layer-score--buy">{buy_value:.1f}</div>
              <div class="sigl-layer-track">
                <div class="sigl-layer-fill--buy" style="--buy-left:{50.0 - buy_pct:.2f}%;--buy-width:{buy_pct:.2f}%"></div>
                <div class="sigl-layer-fill--sell" style="--sell-width:{sell_pct:.2f}%"></div>
                <div class="sigl-layer-center"></div>
                <div class="sigl-layer-label">{_esc(layer_labels.get(name, name))}</div>
              </div>
              <div class="sigl-layer-score--sell">{sell_value:.1f}</div>
            </div>
            """
        )
    panel_html = f"""
        <div class="sigl-card">
          <div class="sigl-section-head">
            <div>
              <p class="sigl-section-title">10개 레이어 비교</p>
              <p class="sigl-section-copy">매수와 매도 쪽에 각 레이어가 얼마나 기여하는지 보여줍니다.</p>
            </div>
            <div class="sigl-inline">
              {_badge(f"매수 {_safe_int(meta.get('buy_active', 0))}/10", 'positive')}
              {_badge(f"매도 {_safe_int(meta.get('sell_active', 0))}/10", 'negative')}
            </div>
          </div>
          <div class="sigl-layer-board">{''.join(rows)}</div>
        </div>
        """
    _render_panel_html(panel_html, min_height=max(520, 170 + len(layer_names) * 42))




def render_leading_lagging(meta):
    leading = translate_chart_text(meta.get("leading_verdict", ""))
    lagging = translate_chart_text(meta.get("lagging_verdict", ""))
    accel = _safe_float(meta.get("composite_accel", 0))
    setup_buy = _safe_float(meta.get("setup_pressure_buy", 0))
    setup_sell = _safe_float(meta.get("setup_pressure_sell", 0))
    max_setup = max(setup_buy, setup_sell, 1)
    buy_width = min(setup_buy / max_setup * 50, 50)
    sell_width = min(setup_sell / max_setup * 50, 50)

    flow_text = (
        "\uC57D\uC138 \uB2E4\uC774\uBC84\uC804\uC2A4"
        if meta.get("smart_money_bearish_div")
        else ("\uC790\uAE08 \uC720\uC785 \uC9C0\uC9C0" if meta.get("smart_money_bullish_div") else "\uC911\uB9BD")
    )
    flow_tone = "negative" if meta.get("smart_money_bearish_div") else ("positive" if meta.get("smart_money_bullish_div") else "muted")
    size_label, size_tone = _risk_size_hint(_safe_float(meta.get("atr_pct", 0)))

    utbot_dir = _safe_int(meta.get("utbot_dir", 0))
    utbot_label = "UT \uB9E4\uC218" if utbot_dir == 1 else ("UT \uB9E4\uB3C4" if utbot_dir == -1 else "UT \uC911\uB9BD")
    utbot_tone = "positive" if utbot_dir == 1 else ("negative" if utbot_dir == -1 else "accent")
    hma_rising = bool(meta.get("hma_rising"))

    stat_cards = [
        _mini_stat_card("BB %B", f"{_safe_float(meta.get('percent_b', 0.5)) * 100:.0f}%", "positive" if _safe_float(meta.get("percent_b", 0.5)) < 0.3 else ("negative" if _safe_float(meta.get("percent_b", 0.5)) > 0.7 else "warning")),
        _mini_stat_card("CMF", f"{_safe_float(meta.get('cmf', 0)):+.3f}", "positive" if _safe_float(meta.get("cmf", 0)) > 0.05 else ("negative" if _safe_float(meta.get("cmf", 0)) < -0.05 else "muted")),
        _mini_stat_card("\uC790\uAE08 \uD750\uB984", flow_text, flow_tone),
        _mini_stat_card("OBV \uAE30\uC6B8\uAE30", f"{_safe_float(meta.get('obv_slope', 0)):+.2f}", "positive" if _safe_float(meta.get("obv_slope", 0)) > 0 else ("negative" if _safe_float(meta.get("obv_slope", 0)) < 0 else "muted")),
        _mini_stat_card("\uCD5C\uADFC \uAC70\uB798\uB7C9", f"{_safe_float(meta.get('volume_ratio_20', 1)):.1f}x", "positive" if _safe_float(meta.get("volume_ratio_20", 1)) >= 1 else ("warning" if _safe_float(meta.get("volume_ratio_20", 1)) >= 0.7 else "negative")),
        _mini_stat_card("ATR%", f"{_safe_float(meta.get('atr_pct', 0)):.1f}%", "accent"),
        _mini_stat_card("\uAD8C\uC7A5 \uBE44\uC911", size_label, size_tone),
        _mini_stat_card("50\uC77C\uC120 \uAC70\uB9AC", f"{_safe_float(meta.get('ma50_dist', 0)):+.1f}%", "positive" if _safe_float(meta.get("ma50_dist", 0)) > 0 else "negative"),
        _mini_stat_card("200\uC77C\uC120 \uAC70\uB9AC", f"{_safe_float(meta.get('ma200_dist', 0)):+.1f}%", "positive" if _safe_float(meta.get("ma200_dist", 0)) > 0 else "negative"),
    ]

    panel_html = f"""
        <div class="sigl-grid sigl-grid--2">
          <div class="sigl-card">
            <div class="sigl-section-head">
              <div>
                <p class="sigl-section-title">\uC120\uD589 \uC9C0\uD45C</p>
                <p class="sigl-section-copy">\uC18D\uB3C4\uC640 \uC804\uD658 \uC2E0\uD638 \uC911\uC2EC\uC758 \uD574\uC11D\uC785\uB2C8\uB2E4.</p>
              </div>
            </div>
            <p class="sigl-metric-value" style="font-size:1.18rem;color:{_tone_color('positive' if accel >= 0 else 'negative')}">{_esc(leading)}</p>
            <div class="sigl-chip-row">
              {_badge(f'\uAC00\uC18D\uB3C4 {accel:+.2f}', 'positive' if accel > 0 else ('negative' if accel < 0 else 'muted'))}
              {_badge(utbot_label, utbot_tone)}
              {_badge('HMA \uC0C1\uC2B9' if hma_rising else 'HMA \uD558\uB77D', 'positive' if hma_rising else 'negative')}
            </div>
          </div>
          <div class="sigl-card">
            <div class="sigl-section-head">
              <div>
                <p class="sigl-section-title">\uD6C4\uD589 \uC9C0\uD45C</p>
                <p class="sigl-section-copy">\uAD6C\uC870\uC640 \uB204\uC801 \uCD94\uC138\uB97C \uC911\uC2EC\uC73C\uB85C \uBD05\uB2C8\uB2E4.</p>
              </div>
            </div>
            <p class="sigl-metric-value" style="font-size:1.18rem;color:{_tone_color(_tone_from_text(lagging))}">{_esc(lagging)}</p>
            <div class="sigl-chip-row">
              {_badge(localize_regime_label(meta.get('regime'), meta.get('regime_label')), 'accent')}
              {_badge(f"RS {_safe_float(meta.get('rs_ratio', 1)):.3f}", 'muted')}
            </div>
          </div>
        </div>
        <div class="sigl-card" style="margin-top:12px">
          <div class="sigl-section-head">
            <div>
              <p class="sigl-section-title">\uB9E4\uC218/\uB9E4\uB3C4 \uC555\uB825</p>
              <p class="sigl-section-copy">\uD604\uC7AC \uC14B\uC5C5 \uC555\uB825\uC774 \uC5B4\uB290 \uCABD\uC73C\uB85C \uB354 \uAE30\uC6B8\uC5C8\uB294\uC9C0 \uBCF4\uC5EC\uC90D\uB2C8\uB2E4.</p>
            </div>
          </div>
          <div class="sigl-inline" style="justify-content:space-between">
            <span class="sigl-summary">\uB9E4\uC218 \uC555\uB825 {setup_buy:.1f}</span>
            <span class="sigl-summary">\uB9E4\uB3C4 \uC555\uB825 {setup_sell:.1f}</span>
          </div>
          <div class="sigl-bar-split" style="--buy:{buy_width:.2f}%;--sell:{sell_width:.2f}%">
            <div class="sigl-bar-split__buy"></div>
            <div class="sigl-bar-split__sell"></div>
            <div class="sigl-bar-split__center"></div>
          </div>
        </div>
        <div class="sigl-card" style="margin-top:12px">
          <div class="sigl-section-head">
            <div>
              <p class="sigl-section-title">\uBCF4\uC870 \uC9C0\uD45C \uC2A4\uB0C5\uC0F7</p>
              <p class="sigl-section-copy">\uACFC\uC5F4, \uC790\uAE08 \uD750\uB984, \uBCC0\uB3D9\uC131, \uC704\uCE58 \uC815\uBCF4\uB97C \uAC19\uC740 \uADDC\uACA9\uC73C\uB85C \uBD05\uB2C8\uB2E4.</p>
            </div>
          </div>
          <div class="sigl-grid sigl-grid--4">{''.join(stat_cards)}</div>
        </div>
        """
    _render_panel_html(panel_html)


def render_combined_scans(meta):
    scans = meta.get("combined_scans", [])
    if not scans:
        st.info("현재 활성화된 콤보 스캔이 없습니다.")
        return
    buy_count = sum(1 for item in scans if item.get("dir") == "buy")
    sell_count = sum(1 for item in scans if item.get("dir") == "sell")
    tier1_count = sum(1 for item in scans if item.get("tier") == 1)
    tone = "warning" if tier1_count > 0 else ("positive" if buy_count > sell_count else "negative" if sell_count > buy_count else "accent")
    cards = []
    for item in scans:
        direction = item.get("dir")
        item_tone = "positive" if direction == "buy" else ("negative" if direction == "sell" else "warning")
        tier_label = {1: "우선 T1", 2: "보강 T2", 3: "참고 T3"}.get(item.get("tier"), "참고")
        cards.append(
            f"""
            <div class="sigl-card sigl-card--{'positive' if item_tone == 'positive' else 'negative' if item_tone == 'negative' else 'warning'}">
              <div class="sigl-section-head">
                <div>
                  <p class="sigl-section-title">{_esc(item.get('kor'))}</p>
                  <p class="sigl-section-copy">{_esc(item.get('win'))}</p>
                </div>
                <div class="sigl-inline">
                  {_badge(tier_label, item_tone)}
                  {_badge(item.get('date', '--/--') if not item.get('is_today') else '오늘', 'accent')}
                </div>
              </div>
            </div>
            """
        )
    panel_html = f"""
        <div class="sigl-card sigl-card--{'warning' if tone == 'warning' else 'positive' if tone == 'positive' else 'negative' if tone == 'negative' else 'accent'}">
          <div class="sigl-section-head">
            <div>
              <p class="sigl-section-title">콤보 스캔</p>
              <p class="sigl-section-copy">여러 조건이 함께 만족된 고확신 패턴만 모아서 보여줍니다.</p>
            </div>
            <div class="sigl-inline">
              {_badge(f'T1 {tier1_count}', 'warning')}
              {_badge(f'매수 {buy_count}', 'positive')}
              {_badge(f'매도 {sell_count}', 'negative')}
            </div>
          </div>
        </div>
        <div class="sigl-grid sigl-grid--2" style="margin-top:12px">{''.join(cards)}</div>
        """
    _render_panel_html(panel_html, min_height=_combined_scan_panel_height(len(cards)))


def render_committee_panel_clean(meta):
    committee = meta.get("committee", {})
    if not committee:
        return
    ctx_code = meta.get("context", 0)
    ctx_name = CTX_LABELS.get(ctx_code, "default")
    weights = CONTEXT_WEIGHTS.get(ctx_name, CONTEXT_WEIGHTS["default"])
    vote_map = {"BUY": "매수", "SELL": "매도", "NEUTRAL": "중립", "ABSTAIN": "보류"}
    cards = []
    for idx, committee_name in enumerate(COMMITTEE_NAMES):
        data = committee.get(committee_name, {})
        score = _safe_float(data.get("score", 0))
        conviction = _safe_float(data.get("conviction", 0))
        vote = str(data.get("vote", "NEUTRAL"))
        weight = weights[idx] if idx < len(weights) else 0.2
        tone = "positive" if score > 0 else ("negative" if score < 0 else "warning")
        cards.append(
            (
                f"<div class='sigl-committee-card' style='--tone:{_tone_color(tone)}'>"
                f"<p class='sigl-committee-name'>{_esc(localize_committee_name(committee_name))} · 비중 {weight:.0%}</p>"
                f"<p class='sigl-committee-score'>{score:+.0f}</p>"
                f"{_badge(vote_map.get(vote, vote), tone if tone != 'warning' else 'warning')}"
                f"<p class='sigl-committee-foot'>확신도 {conviction:.0f}%</p>"
                f"<div class='sigl-progress'><div class='sigl-progress__fill' style='--fill:{min(abs(score) / 40 * 100, 100):.1f}%;--tone:{_tone_color(tone)}'></div></div>"
                "</div>"
            )
        )
    panel_html = (
        "<div class='sigl-card'>"
        "<div class='sigl-section-head'>"
        "<div>"
        "<p class='sigl-section-title'>5위원회 종합 판단</p>"
        "<p class='sigl-section-copy'>위원회별 점수와 확신도를 같은 규격으로 비교합니다.</p>"
        "</div>"
        "</div>"
        f"<div class='sigl-grid sigl-grid--5'>{_join_html(cards)}</div>"
        "</div>"
    )
    _render_panel_html(panel_html, min_height=_committee_panel_height(len(cards)))
    if meta.get("veto_flags"):
        st.warning(f"제한 조건: {meta.get('veto_flags')}")
    if abs(_safe_float(meta.get("reversal_synergy", 0))) > 5:
        st.info(f"반전 시너지: {_safe_float(meta.get('reversal_synergy', 0)):+.1f}")


def render_10layer_bars_clean(meta, html_key="analysis"):
    del html_key
    layer_names = ["Trend", "Momentum", "Candle", "BB", "Volume", "MF", "Pattern", "Combined", "Leading", "Lagging"]
    layer_labels = {
        "Trend": "추세",
        "Momentum": "모멘텀",
        "Candle": "캔들",
        "BB": "볼린저",
        "Volume": "거래량",
        "MF": "자금 흐름",
        "Pattern": "패턴",
        "Combined": "콤보",
        "Leading": "선행",
        "Lagging": "후행",
    }
    buy_layers = meta.get("buy_layers", {}) or {}
    sell_layers = meta.get("sell_layers", {}) or {}
    buy_total = _safe_float(meta.get("buy_total", 0))
    sell_total = _safe_float(meta.get("sell_total", 0))
    layer_edge = buy_total - sell_total
    conflict_layers = _safe_int(meta.get("signal_conflict_layers", 0))
    objective_alignment = str(meta.get("objective_alignment", "MIXED")).upper()
    objective_confidence = _safe_float(meta.get("objective_confidence", 0))
    thin_trade_risk = bool(meta.get("thin_trade_risk"))
    objective_alignment_label = {"ALIGNED": "일치", "CONFLICT": "충돌", "MIXED": "혼합"}.get(objective_alignment, objective_alignment)
    objective_alignment_tone = {"ALIGNED": "positive", "CONFLICT": "negative", "MIXED": "warning"}.get(objective_alignment, "muted")
    ranked_buy = sorted(((name, max(_safe_float(buy_layers.get(name, 0)), 0.0)) for name in layer_names), key=lambda item: item[1], reverse=True)
    ranked_sell = sorted(((name, max(_safe_float(sell_layers.get(name, 0)), 0.0)) for name in layer_names), key=lambda item: item[1], reverse=True)
    top_buy = [(name, value) for name, value in ranked_buy if value > 0][:3]
    top_sell = [(name, value) for name, value in ranked_sell if value > 0][:3]
    dominant_buy = layer_labels.get(top_buy[0][0], top_buy[0][0]) if top_buy else "-"
    dominant_sell = layer_labels.get(top_sell[0][0], top_sell[0][0]) if top_sell else "-"
    buy_profile = sum(max(_safe_float(buy_layers.get(name, 0)), 0.0) for name in ("Trend", "Momentum", "Leading", "Lagging"))
    reversal_profile = sum(max(_safe_float(buy_layers.get(name, 0)), 0.0) for name in ("Candle", "BB", "Pattern"))
    sell_profile = sum(max(_safe_float(sell_layers.get(name, 0)), 0.0) for name in ("Trend", "Momentum", "Leading", "Lagging"))
    sell_reversal_profile = sum(max(_safe_float(sell_layers.get(name, 0)), 0.0) for name in ("Candle", "BB", "Pattern"))
    if layer_edge >= 4:
        layer_profile = "추세 추종형" if buy_profile >= reversal_profile else "눌림·반전 탐색형"
        layer_profile_tone = "positive"
    elif layer_edge <= -4:
        layer_profile = "방어·리스크 관리형" if sell_profile >= sell_reversal_profile else "상단 반락 대응형"
        layer_profile_tone = "negative"
    else:
        layer_profile = "혼합·확인 대기형"
        layer_profile_tone = "warning"
    supports_named, resistances_named = _extract_named_levels(meta)
    support_text = f"{supports_named[0][0]} {supports_named[0][1]:.2f}" if supports_named else "가까운 지지선"
    resistance_text = f"{resistances_named[0][0]} {resistances_named[0][1]:.2f}" if resistances_named else "가까운 저항선"
    if layer_edge >= 4 and objective_alignment == "ALIGNED":
        strategy_note = f"매수 레이어가 우세하고 객관 엔진도 같은 방향({objective_confidence:.0f}% 신뢰)입니다. {support_text} 지지 확인 뒤 분할 진입하고, {resistance_text} 돌파가 이어질 때 추세 추종을 강화하는 쪽이 자연스럽습니다."
    elif layer_edge <= -4 and objective_alignment == "ALIGNED":
        strategy_note = f"매도 레이어가 우세하고 객관 엔진도 같은 방향({objective_confidence:.0f}% 신뢰)입니다. {resistance_text} 회복 실패나 {support_text} 이탈 시 비중 축소와 방어 강화를 우선하는 편이 좋습니다."
    elif objective_alignment == "CONFLICT" or conflict_layers >= 3:
        strategy_note = f"레이어와 객관 엔진의 충돌이 커서 한 방향 베팅보다 {support_text} 지지와 {resistance_text} 회복·이탈 확인을 먼저 보는 편이 좋습니다."
    else:
        strategy_note = f"현재는 {layer_profile} 성격이지만 확신은 중간 수준입니다. {support_text} 반응과 {resistance_text} 돌파·실패를 확인한 뒤 비중을 조절하는 접근이 적합합니다."
    if thin_trade_risk:
        strategy_note += " 거래대금이 얇아 신규 대응은 평소보다 작게 가져가는 편이 안전합니다."
    summary_cards = [
        _mini_stat_card("레이어 우세", f"{layer_edge:+.1f}", "positive" if layer_edge > 1 else "negative" if layer_edge < -1 else "warning"),
        _mini_stat_card("매수 핵심", dominant_buy, "positive" if top_buy else "muted"),
        _mini_stat_card("매도 핵심", dominant_sell, "negative" if top_sell else "muted"),
        _mini_stat_card("레이어 충돌", f"{conflict_layers}개", "warning" if conflict_layers >= 3 else "muted"),
        _mini_stat_card("전략 성격", layer_profile, layer_profile_tone),
    ]
    layer_badges = "".join(
        [_badge(f"매수 {layer_labels.get(name, name)} {value:.1f}", "positive") for name, value in top_buy]
        + [_badge(f"매도 {layer_labels.get(name, name)} {value:.1f}", "negative") for name, value in top_sell]
    )
    rows = []
    for name in layer_names:
        buy_value = max(_safe_float(buy_layers.get(name, 0)), 0.0)
        sell_value = max(_safe_float(sell_layers.get(name, 0)), 0.0)
        buy_pct = min((buy_value / 12.0) * 50.0, 50.0)
        sell_pct = min((sell_value / 12.0) * 50.0, 50.0)
        rows.append(
            (
                "<div class='sigl-layer-row'>"
                f"<div class='sigl-layer-score--buy'>{buy_value:.1f}</div>"
                "<div class='sigl-layer-track'>"
                f"<div class='sigl-layer-fill--buy' style='--buy-left:{50.0 - buy_pct:.2f}%;--buy-width:{buy_pct:.2f}%'></div>"
                f"<div class='sigl-layer-fill--sell' style='--sell-width:{sell_pct:.2f}%'></div>"
                "<div class='sigl-layer-center'></div>"
                f"<div class='sigl-layer-label'>{_esc(layer_labels.get(name, name))}</div>"
                "</div>"
                f"<div class='sigl-layer-score--sell'>{sell_value:.1f}</div>"
                "</div>"
            )
        )
    panel_html = (
        "<div class='sigl-card'>"
        "<div class='sigl-section-head'>"
        "<div>"
        "<p class='sigl-section-title'>10개 레이어 비교</p>"
        "</div>"
        "<div class='sigl-inline'>"
        f"{_badge(f'매수 {_safe_int(meta.get('buy_active', 0))}/10', 'positive')}"
        f"{_badge(f'매도 {_safe_int(meta.get('sell_active', 0))}/10', 'negative')}"
        f"{_badge(f'정렬 {objective_alignment_label}', objective_alignment_tone)}"
        "</div>"
        "</div>"
        f"<div class='sigl-grid sigl-grid--5'>{''.join(summary_cards)}</div>"
        f"<div class='sigl-chip-row'>{layer_badges}</div>"
        f"<div class='sigl-note'><strong>레이어 전략 해석</strong><br><span class='sigl-summary'>{_esc(strategy_note)}</span></div>"
        f"<div class='sigl-layer-board'>{_join_html(rows)}</div>"
        "</div>"
    )
    _render_panel_html(panel_html, min_height=max(520, 170 + len(layer_names) * 42))


def render_indicator_help():
    with st.expander("차트 보는 법 / 지표 설명", expanded=False):
        st.markdown(
            "- `최종 판단 / 액션`: 현재 구간에서 시스템이 보는 방향과 우선순위입니다.\n"
            "- `리스크 체크`: 다이버전스, 거래량, 과열 경고 같은 반론 포인트를 모아 보여줍니다.\n"
            "- `WT1`: 과매수/과매도 성격을 빠르게 보는 지표입니다.\n"
            "- `ADX`: 추세 강도를 보여주며 방향 자체를 뜻하지는 않습니다.\n"
            "- `CMF / OBV`: 자금 유입과 이탈 흐름을 보는 보조 지표입니다.\n"
            "- `종합 점수(Ensemble Score)`: -100~+100 범위의 종합 방향 점수입니다.\n"
            "- `10개 레이어`: 추세, 모멘텀, 거래량, 자금 흐름 등이 매수/매도 쪽에 얼마나 기여하는지 비교합니다.\n"
            "- `VWAP / 고정 VWAP / Envelope / Price Channel / PSAR`: 가격 위치와 구조를 읽는 지표입니다.\n"
            "- `Williams %R / CCI / RMI / TRIX / Mass Index`: 과열, 반전, 모멘텀 전환을 읽는 지표입니다.\n"
            "- `Volume Osc / Intraday Intensity / Chaikin`: 수급과 체결 에너지 방향을 확인하는 지표입니다."
        )


def _fmt_audit_number(value, digits=1, signed=False):
    if value is None:
        return "-"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "-"
    if math.isnan(number):
        return "-"
    prefix = "+" if signed and number > 0 else ""
    return f"{prefix}{number:.{digits}f}"


def _fmt_audit_percent(value, digits=1, signed=False):
    if value is None:
        return "-"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "-"
    if math.isnan(number):
        return "-"
    scaled = number * 100.0
    prefix = "+" if signed and scaled > 0 else ""
    return f"{prefix}{scaled:.{digits}f}%"


# Safe overrides for audit rendering and analysis tabs.
def _fmt_audit_number(value, digits=1, signed=False):
    if value is None:
        return "-"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "-"
    if math.isnan(number):
        return "-"
    prefix = "+" if signed and number > 0 else ""
    return f"{prefix}{number:.{digits}f}"


def _fmt_audit_percent(value, digits=1, signed=False):
    if value is None:
        return "-"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "-"
    if math.isnan(number):
        return "-"
    scaled = number * 100.0
    prefix = "+" if signed and scaled > 0 else ""
    return f"{prefix}{scaled:.{digits}f}%"


def _build_audit_summary_cards(summary, h_ref):
    buy_tone = "positive" if (summary.get("buy_edge_ref") or 0) > 0 else "warning"
    sell_tone = "positive" if (summary.get("sell_edge_ref") or 0) > 0 else "warning"
    buy_spy_tone = "positive" if (summary.get("buy_edge_excess_spy_ref") or 0) > 0 else "warning"
    sell_spy_tone = "positive" if (summary.get("sell_edge_excess_spy_ref") or 0) > 0 else "warning"
    buy_qqq_tone = "positive" if (summary.get("buy_edge_excess_qqq_ref") or 0) > 0 else "warning"
    sell_qqq_tone = "positive" if (summary.get("sell_edge_excess_qqq_ref") or 0) > 0 else "warning"
    return "".join(
        [
            _mini_stat_card("\uD3C9\uAC00 \uD45C\uBCF8", f"{_safe_int(summary.get('samples', 0)):,}", "accent", "\uBBF8\uB798 \uC218\uC775\uB960\uC744 \uACC4\uC0B0\uD560 \uC218 \uC788\uB294 \uAD6C\uAC04 \uC218"),
            _mini_stat_card("BUY \uBE44\uC911", _fmt_audit_percent(summary.get("buy_share")), "positive", "BUY \uACC4\uC5F4 \uB77C\uBCA8 \uBE44\uC911"),
            _mini_stat_card("SELL \uBE44\uC911", _fmt_audit_percent(summary.get("sell_share")), "negative", "SELL \uACC4\uC5F4 \uB77C\uBCA8 \uBE44\uC911"),
            _mini_stat_card("\uC911\uB9BD/\uD63C\uC870", _fmt_audit_percent(summary.get("neutral_share")), "warning", "NEUTRAL + MIXED \uBE44\uC911"),
            _mini_stat_card(f"BUY {h_ref}\uBD09 \uBC29\uD5A5\uC218\uC775", _fmt_audit_percent(summary.get("buy_edge_ref"), signed=True), buy_tone, "BUY \uACC4\uC5F4 \uD310\uB2E8 \uC774\uD6C4 \uBC29\uD5A5 \uAE30\uC900 \uD3C9\uADE0 \uC218\uC775"),
            _mini_stat_card(f"SELL {h_ref}\uBD09 \uBC29\uD5A5\uC218\uC775", _fmt_audit_percent(summary.get("sell_edge_ref"), signed=True), sell_tone, "SELL \uACC4\uC5F4 \uD310\uB2E8 \uC774\uD6C4 \uBC29\uD5A5 \uAE30\uC900 \uD3C9\uADE0 \uC218\uC775"),
            _mini_stat_card(f"BUY {h_ref}\uBD09 SPY \uCD08\uACFC", _fmt_audit_percent(summary.get("buy_edge_excess_spy_ref"), signed=True), buy_spy_tone, "BUY \uACC4\uC5F4 \uD310\uB2E8 \uC774\uD6C4 SPY \uB300\uBE44 \uBC29\uD5A5 \uCD08\uACFC\uC218\uC775"),
            _mini_stat_card(f"SELL {h_ref}\uBD09 SPY \uCD08\uACFC", _fmt_audit_percent(summary.get("sell_edge_excess_spy_ref"), signed=True), sell_spy_tone, "SELL \uACC4\uC5F4 \uD310\uB2E8 \uC774\uD6C4 SPY \uB300\uBE44 \uBC29\uD5A5 \uCD08\uACFC\uC218\uC775"),
            _mini_stat_card(f"BUY {h_ref}\uBD09 QQQ \uCD08\uACFC", _fmt_audit_percent(summary.get("buy_edge_excess_qqq_ref"), signed=True), buy_qqq_tone, "BUY \uACC4\uC5F4 \uD310\uB2E8 \uC774\uD6C4 QQQ \uB300\uBE44 \uBC29\uD5A5 \uCD08\uACFC\uC218\uC775"),
            _mini_stat_card(f"SELL {h_ref}\uBD09 QQQ \uCD08\uACFC", _fmt_audit_percent(summary.get("sell_edge_excess_qqq_ref"), signed=True), sell_qqq_tone, "SELL \uACC4\uC5F4 \uD310\uB2E8 \uC774\uD6C4 QQQ \uB300\uBE44 \uBC29\uD5A5 \uCD08\uACFC\uC218\uC775"),
            _mini_stat_card("\uAC15\uB4F1 \uBE44\uC911", _fmt_audit_percent(summary.get("downgraded_share")), "warning", "PreVeto \uB300\uBE44 \uCD5C\uC885 \uD310\uB2E8 \uC870\uC815 \uBE44\uC911"),
            _mini_stat_card("Flip Guard \uBE44\uC911", _fmt_audit_percent(summary.get("flip_guard_share")), "muted", "\uAE09\uBC18\uC804 \uBCF4\uD638 \uC791\uB3D9 \uBE44\uC911"),
        ]
    )


def _build_audit_frame(rows, horizons, label_key):
    if not rows:
        return pd.DataFrame()
    records = []
    for row in rows:
        record = {
            label_key: row.get("name") or row.get("label") or "-",
            "\uD45C\uBCF8": _safe_int(row.get("samples", 0)),
            "\uD3C9\uADE0 ES": _fmt_audit_number(row.get("avg_es"), signed=True),
            "\uD3C9\uADE0 \uC2E0\uB8B0\uB3C4": _fmt_audit_number(row.get("avg_confidence")),
            "\uAC15\uB4F1 \uBE44\uC911": _fmt_audit_percent(row.get("downgrade_rate")),
        }
        for horizon in horizons:
            record[f"{horizon}\uBD09 \uD3C9\uADE0"] = _fmt_audit_percent(row.get(f"avg_{horizon}"), signed=True)
            record[f"{horizon}\uBD09 \uC801\uC911"] = _fmt_audit_percent(row.get(f"hit_{horizon}"))
            record[f"{horizon}\uBD09 \uBC29\uD5A5\uC218\uC775"] = _fmt_audit_percent(row.get(f"edge_{horizon}"), signed=True)
            record[f"{horizon}\uBD09 SPY \uCD08\uACFC"] = _fmt_audit_percent(row.get(f"edge_excess_spy_{horizon}"), signed=True)
            record[f"{horizon}\uBD09 QQQ \uCD08\uACFC"] = _fmt_audit_percent(row.get(f"edge_excess_qqq_{horizon}"), signed=True)
        records.append(record)
    return pd.DataFrame(records)


def _build_example_frame(rows, horizon):
    if not rows:
        return pd.DataFrame()
    records = []
    for row in rows:
        records.append(
            {
                "\uB0A0\uC9DC": row.get("date", "-"),
                "\uD310\uB2E8": row.get("label", "-"),
                "\uC885\uAC00": _fmt_audit_number(row.get("close"), digits=2),
                f"{horizon}\uBD09 \uC218\uC775": _fmt_audit_percent(row.get(f"ret_{horizon}"), signed=True),
                f"{horizon}\uBD09 \uBC29\uD5A5\uC218\uC775": _fmt_audit_percent(row.get(f"edge_{horizon}"), signed=True),
                f"{horizon}\uBD09 SPY \uCD08\uACFC": _fmt_audit_percent(row.get(f"spy_excess_{horizon}"), signed=True),
                f"{horizon}\uBD09 QQQ \uCD08\uACFC": _fmt_audit_percent(row.get(f"qqq_excess_{horizon}"), signed=True),
                "ES": _fmt_audit_number(row.get("ensemble_score"), signed=True),
                "\uC2E0\uB8B0\uB3C4": _fmt_audit_number(row.get("confidence")),
                "\uAC15\uB4F1": "\uC608" if row.get("downgraded") else "-",
                "Flip Guard": "\uC608" if row.get("flip_guard") else "-",
                "\uC0AC\uC720": row.get("reason", ""),
            }
        )
    return pd.DataFrame(records)


def render_audit_panel(audit):
    if not audit or not audit.get("available"):
        reason = (audit or {}).get("reason") or "\uBC31\uD14C\uC2A4\uD2B8/\uAC10\uC0AC \uD45C\uBCF8\uC774 \uC544\uC9C1 \uBD80\uC871\uD569\uB2C8\uB2E4."
        st.info(reason)
        return

    summary = audit.get("summary", {})
    horizons = list(audit.get("horizons", []))
    h_ref = _safe_int(audit.get("reference_horizon", 5), 5)
    distribution = audit.get("distribution", [])
    method_note = (
        f"\uCD5C\uADFC {_safe_int(summary.get('lookback_bars', 0))}\uBD09 \uAE30\uC900\uC73C\uB85C "
        f"{', '.join(str(h) for h in horizons)}\uBD09 \uD6C4 \uC218\uC775\uB960\uACFC SPY/QQQ \uB300\uBE44 \uBC29\uD5A5 \uCD08\uACFC\uC218\uC775\uC744 \uBE44\uAD50\uD588\uC2B5\uB2C8\uB2E4. "
        "\uC218\uC218\uB8CC, \uC2AC\uB9AC\uD53C\uC9C0, \uCCB4\uACB0 \uC9C0\uC5F0\uC740 \uBC18\uC601\uD558\uC9C0 \uC54A\uC740 "
        "\uAC10\uC0AC\uC6A9 \uC9C0\uD45C\uC785\uB2C8\uB2E4."
    )
    veto_stats = audit.get("veto_stats", {})

    _render_panel_html(
        f"""
        <div class="sigl-card">
          <div class="sigl-section-head">
            <div>
              <p class="sigl-section-title">\uBC31\uD14C\uC2A4\uD2B8/\uAC10\uC0AC \uC694\uC57D</p>
              <p class="sigl-section-copy">\uCD5C\uADFC \uD310\uB2E8\uC774 \uC2E4\uC81C \uC5B4\uB5A4 \uACB0\uACFC\uB85C \uC774\uC5B4\uC84C\uB294\uC9C0, \uAC15\uB4F1\uACFC flip guard\uAC00 \uC5B4\uB5A4 \uC601\uD5A5\uC744 \uC918\uB294\uC9C0 \uC810\uAC80\uD569\uB2C8\uB2E4.</p>
            </div>
            <div class="sigl-inline">
              {_badge((audit.get('ticker') or '-').upper(), 'accent')}
              {_badge(f"\uAE30\uC900 {summary.get('as_of', '-')}", 'muted')}
            </div>
          </div>
          <div class="sigl-grid sigl-grid--4">{_build_audit_summary_cards(summary, h_ref)}</div>
        </div>
        """
    )

    if distribution:
        dist_badges = "".join(
            _badge(
                f"{item.get('label')} {item.get('count', 0)}\uAC74 \u00B7 {_fmt_audit_percent(item.get('share'))}",
                _tone_from_text(item.get("label")),
            )
            for item in distribution
        )
        _render_panel_html(
            f"""
            <div class="sigl-card sigl-card--accent">
              <div class="sigl-section-head">
                <div>
                  <p class="sigl-section-title">\uB77C\uBCA8 \uBD84\uD3EC</p>
                  <p class="sigl-section-copy">\uCD5C\uADFC \uC2DC\uC2A4\uD15C\uC774 \uC5B4\uB5A4 \uD310\uB2E8\uC744 \uC5BC\uB9C8\uB098 \uC790\uC8FC \uB0C8\uB294\uC9C0 \uD655\uC778\uD569\uB2C8\uB2E4.</p>
                </div>
              </div>
              <div class="sigl-inline" style="flex-wrap:wrap">{dist_badges}</div>
            </div>
            """
        )

    if method_note:
        st.caption(method_note)

    label_df = _build_audit_frame(audit.get("label_rows", []), horizons, "\uD310\uB2E8")
    if not label_df.empty:
        st.markdown("#### \uD310\uB2E8\uBCC4 \uC131\uACFC")
        st.dataframe(label_df, use_container_width=True, hide_index=True)

    group_df = _build_audit_frame(audit.get("group_rows", []), horizons, "\uADF8\uB8F9")
    if not group_df.empty:
        st.markdown("#### \uBC29\uD5A5 \uADF8\uB8F9\uBCC4 \uC131\uACFC")
        st.dataframe(group_df, use_container_width=True, hide_index=True)

    turn_df = _build_audit_frame(audit.get("turn_rows", []), horizons, "\uC804\uD658 \uC2E0\uD638")
    if not turn_df.empty:
        st.markdown("#### \uC804\uD658 \uC2E0\uD638 \uAC10\uC0AC")
        st.dataframe(turn_df, use_container_width=True, hide_index=True)

    veto_cards = "".join(
        [
            _mini_stat_card("\uAC15\uB4F1 \uD69F\uC218", f"{_safe_int(veto_stats.get('downgraded_count', 0)):,}", "warning"),
            _mini_stat_card("\uB9E4\uC218 \uAC15\uB4F1 \uB3C4\uC6C0", _fmt_audit_percent(veto_stats.get("buy_downgrade_help_rate")), "positive"),
            _mini_stat_card("\uB9E4\uB3C4 \uAC15\uB4F1 \uB3C4\uC6C0", _fmt_audit_percent(veto_stats.get("sell_downgrade_help_rate")), "positive"),
            _mini_stat_card("\uD310\uB2E8 \uAE09\uBC18\uC804", f"{_safe_int(veto_stats.get('flip_count', 0)):,}", "negative"),
            _mini_stat_card("Flip Guard \uBC1C\uB3D9", f"{_safe_int(veto_stats.get('flip_guard_count', 0)):,}", "muted"),
            _mini_stat_card("Flip Guard \uBE44\uC911", _fmt_audit_percent(veto_stats.get("flip_guard_share")), "muted"),
        ]
    )
    _render_panel_html(
        f"""
        <div class="sigl-card">
          <div class="sigl-section-head">
            <div>
              <p class="sigl-section-title">\uAC15\uB4F1/\uB9AC\uC2A4\uD06C \uAC10\uC0AC</p>
              <p class="sigl-section-copy">\uCD5C\uC885 \uD310\uB2E8\uC744 \uBCF4\uC218\uC801\uC73C\uB85C \uC870\uC815\uD55C \uADDC\uCE59\uB4E4\uC774 \uC2E4\uC81C\uB85C \uB3C4\uC6C0\uC774 \uB410\uB294\uC9C0 \uCD94\uC801\uD569\uB2C8\uB2E4.</p>
            </div>
          </div>
          <div class="sigl-grid sigl-grid--3">{veto_cards}</div>
        </div>
        """
    )

    examples = audit.get("examples", {})
    best_df = _build_example_frame(examples.get("best", []), h_ref)
    worst_df = _build_example_frame(examples.get("worst", []), h_ref)
    if not best_df.empty or not worst_df.empty:
        st.markdown("#### \uB300\uD45C \uC0AC\uB840")
        col_best, col_worst = st.columns(2)
        with col_best:
            st.caption(f"\uC798 \uB9DE\uC740 \uC0AC\uB840 \u00B7 {h_ref}\uBD09 \uBC29\uD5A5\uC218\uC775 \uAE30\uC900")
            if best_df.empty:
                st.info("\uD45C\uC2DC\uD560 \uC0AC\uB840\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4.")
            else:
                st.dataframe(best_df, use_container_width=True, hide_index=True)
        with col_worst:
            st.caption(f"\uC8FC\uC758\uAC00 \uD544\uC694\uD588\uB358 \uC0AC\uB840 \u00B7 {h_ref}\uBD09 \uBC29\uD5A5\uC218\uC775 \uAE30\uC900")
            if worst_df.empty:
                st.info("\uD45C\uC2DC\uD560 \uC0AC\uB840\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4.")
            else:
                st.dataframe(worst_df, use_container_width=True, hide_index=True)


def render_analysis(msg, key_prefix="analysis"):
    meta = msg.get("meta")
    fig_json = msg.get("fig_json")
    audit = msg.get("audit")
    if meta:
        render_price_header(meta, key_prefix=key_prefix)
    if not (meta or fig_json):
        return

    tab_chart, tab_judgment, tab_audit, tab_layers, tab_scans, tab_company = st.tabs(
        [
            "\uCC28\uD2B8",
            "\uD310\uB2E8/\uB9AC\uC2A4\uD06C",
            "\uBC31\uD14C\uC2A4\uD2B8/\uAC10\uC0AC",
            "10\uAC1C \uB808\uC774\uC5B4",
            "\uCF64\uBCF4 \uC2A4\uCE94",
            "\uAE30\uC5C5 \uC815\uBCF4",
        ]
    )

    with tab_chart:
        if fig_json:
            fig = go.Figure(json.loads(fig_json))
            st.plotly_chart(
                fig,
                use_container_width=True,
                theme=None,
                config={"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]},
                key=f"{key_prefix}_price_chart",
            )
            if meta:
                render_chart_indicator_snapshot(meta)
            if meta:
                st.markdown(
                    _build_chart_summary_html(meta),
                    unsafe_allow_html=True,
                )

    with tab_judgment:
        if meta:
            render_judgment_card(meta)
            st.markdown("<div class='sigl-stack-gap'></div>", unsafe_allow_html=True)
            render_ai_signal_assisted_card(meta)
            st.markdown("<div class='sigl-stack-gap'></div>", unsafe_allow_html=True)
            render_committee_panel_clean(meta)
            st.markdown("<div class='sigl-stack-gap sigl-stack-gap--lg'></div>", unsafe_allow_html=True)
            render_leading_lagging(meta)
            render_indicator_help()

    with tab_audit:
        render_audit_panel(audit)

    with tab_layers:
        if meta:
            render_10layer_bars_clean(meta, html_key=f"{key_prefix}_10layer")

    with tab_scans:
        if meta:
            render_combined_scans(meta)

    with tab_company:
        if meta:
            render_company_details(meta["ticker"], key_prefix=f"{key_prefix}_company")



