import html
import json
import re
import textwrap

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


def _html_block(markup):
    text = textwrap.dedent(str(markup or "")).strip()
    text = re.sub(r"\n[ \t]+(?=<)", "\n", text)
    return text


def _join_html(parts):
    return "".join(_html_block(part) for part in parts if str(part or "").strip())


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
    if len(cleaned) == 1:
        return cleaned[0]
    if len(cleaned) == 2:
        return f"{cleaned[0]}와 {cleaned[1]}"
    return f"{', '.join(cleaned[:-1])}, {cleaned[-1]}"


def _judgment_explainer(meta, title):
    raw_judgment = str(meta.get("judgment", "")).strip()
    final_label = localize_action_label(meta.get("action_label", "").strip() or raw_judgment or title or "NEUTRAL")
    pre_veto_label = localize_judgment_label(str(meta.get("pre_veto_judgment", "")).strip())
    downgrade_count = _safe_int(meta.get("downgrade_count", 0))
    macro_risk_off_count = _safe_int(meta.get("macro_risk_off_count", 0))
    macro_risk_on_count = _safe_int(meta.get("macro_risk_on_count", 0))
    continuation_buy = _safe_float(meta.get("continuation_buy_score", 0))
    continuation_sell = _safe_float(meta.get("continuation_sell_score", 0))
    macro_pressure = _safe_float(meta.get("macro_pressure_score", 0))
    ut_gap = max(_safe_float(meta.get("utbot_stop_atr_gap", 0)), 0.0)
    breadth_score = _safe_float(meta.get("market_breadth_score", 0))
    judgment_tone = _tone_from_text(raw_judgment or final_label)

    supportive = []
    risk = []

    if continuation_buy >= 2.5:
        supportive.append("타이트한 continuation 신호")
    elif continuation_buy >= 1.0:
        supportive.append("추세 지속 신호")
    if meta.get("bullish_gap_reversal"):
        supportive.append("갭다운 회복 패턴")
    if meta.get("diag_support_hold"):
        supportive.append("사선 지지 유지")
    if meta.get("diag_breakout_bull"):
        supportive.append("사선 돌파 구조")
    if ut_gap and ut_gap <= 0.9 and continuation_buy >= continuation_sell:
        supportive.append("UTBot 기준선 근처 지지")
    if breadth_score >= 1.0 or meta.get("breadth_risk_on") or macro_risk_on_count >= 2:
        supportive.append("시장 breadth 확산")

    if continuation_sell >= 2.5:
        risk.append("구조 약화와 매도 압력 누적")
    elif continuation_sell >= 1.0:
        risk.append("매도 압력 겹침")
    if meta.get("bearish_gap_failure"):
        risk.append("갭업 실패 패턴")
    if meta.get("diag_resistance_reject"):
        risk.append("사선 저항 거부")
    if meta.get("diag_breakdown_bear"):
        risk.append("사선 이탈 구조")
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

    if pre_veto_label and pre_veto_label != final_label and downgrade_count > 0:
        cause_text = risk_text or support_text
        if cause_text:
            return f"초기 판단은 {pre_veto_label}였지만 {cause_text} 때문에 {downgrade_count}단계 조정돼 현재는 {final_label}로 봅니다."
        return f"초기 판단은 {pre_veto_label}였지만 보호 규칙이 적용돼 현재는 {final_label}로 조정됐습니다."

    if judgment_tone == "positive":
        if support_text and risk_text:
            return f"{final_label} 판단은 {support_text}에 기반합니다. 다만 {risk_text}는 함께 확인해야 할 리스크입니다."
        if support_text:
            return f"{final_label} 판단은 {support_text}에 기반합니다."
        if risk_text:
            return f"{final_label} 판단이지만 {risk_text}는 함께 경계해야 합니다."
    elif judgment_tone == "negative":
        if risk_text and support_text:
            return f"{final_label} 판단은 {risk_text} 때문입니다. 다만 {support_text}는 반대 근거로 남아 있습니다."
        if risk_text:
            return f"{final_label} 판단은 {risk_text} 때문입니다."
        if support_text:
            return f"{final_label} 판단이지만 {support_text}는 반대 근거로 남아 있습니다."
    else:
        if support_text and risk_text:
            return f"매수 쪽에서는 {support_text}, 매도 쪽에서는 {risk_text}가 동시에 보여 판단을 보수적으로 유지했습니다."
        if support_text or risk_text:
            return f"{final_label} 판단은 {_join_reason_phrases([support_text, risk_text])}에 영향을 받았습니다."
    return ""


def render_judgment_card(meta):
    raw_judgment = str(meta.get("judgment", "NEUTRAL"))
    action = localize_action_label(meta.get("action_label", ""))
    tone = _tone_from_text(raw_judgment or action)
    title = action or localize_judgment_label(raw_judgment)
    es = _safe_float(meta.get("ensemble_score", 0))
    confidence = _safe_float(meta.get("confidence", 0))
    buy_agree = _safe_int(meta.get("buy_agree", 0))
    sell_agree = _safe_int(meta.get("sell_agree", 0))
    detail_text = str(meta.get("judgment_detail") or meta.get("judgment_reason") or "").strip()
    contrast = str(meta.get("contrast_notes", "")).strip()
    badges = []
    if abs(_safe_float(meta.get("reversal_synergy", 0))) > 5:
        badges.append(_badge(f"반전 시너지 {_safe_float(meta.get('reversal_synergy', 0)):+.1f}", "positive" if _safe_float(meta.get("reversal_synergy", 0)) > 0 else "negative"))
    if abs(_safe_float(meta.get("prediction_boost", 0))) > 3:
        badges.append(_badge(f"예측 보정 {_safe_float(meta.get('prediction_boost', 0)):+.1f}", "positive" if _safe_float(meta.get("prediction_boost", 0)) > 0 else "negative"))
    if meta.get("veto_flags"):
        badges.append(_badge(f"제한 조건 {meta.get('veto_flags')}", "warning"))
    risk_tags = []
    if meta.get("smart_money_bearish_div"):
        risk_tags.append(_badge("\uC2A4\uB9C8\uD2B8\uBA38\uB2C8 \uC57D\uC138 \uB2E4\uC774\uBC84\uC804\uC2A4", "negative"))
    elif meta.get("smart_money_bullish_div"):
        risk_tags.append(_badge("\uC2A4\uB9C8\uD2B8\uBA38\uB2C8 \uC9C0\uC9C0", "positive"))
    if _safe_float(meta.get("volume_ratio_20", 1)) < 0.7:
        risk_tags.append(_badge(f"\uC800\uAC70\uB798\uB7C9 {_safe_float(meta.get('volume_ratio_20', 1)):.1f}x", "warning"))
    if meta.get("blowoff_top_hard"):
        risk_tags.append(_badge("\uAE09\uB4F1 \uACFC\uC5F4 \uACBD\uACE0", "negative"))
    if meta.get("thin_trade_risk"):
        risk_tags.append(_badge("저유동성 종목", "warning"))
    if meta.get("flip_guard_triggered"):
        risk_tags.append(_badge("판단 급반전 보호", "warning"))

    pre_veto_label = localize_judgment_label(str(meta.get("pre_veto_judgment", "")).strip())
    downgrade_count = _safe_int(meta.get("downgrade_count", 0))
    market_filter_bias = _safe_float(meta.get("market_filter_bias", 0))
    macro_pressure = _safe_float(meta.get("macro_pressure_score", 0))
    breadth_score = _safe_float(meta.get("market_breadth_score", 0))
    continuation_buy = _safe_float(meta.get("continuation_buy_score", 0))
    continuation_sell = _safe_float(meta.get("continuation_sell_score", 0))
    trend_inflection_buy = _safe_float(meta.get("trend_inflection_buy_score", 0))
    trend_inflection_sell = _safe_float(meta.get("trend_inflection_sell_score", 0))
    market_turn_bull_score = _safe_float(meta.get("market_turn_bull_score", 0))
    market_turn_bear_score = _safe_float(meta.get("market_turn_bear_score", 0))
    ut_gap = max(_safe_float(meta.get("utbot_stop_atr_gap", 0)), 0.0)
    macro_risk_off_count = _safe_int(meta.get("macro_risk_off_count", 0))
    macro_risk_on_count = _safe_int(meta.get("macro_risk_on_count", 0))

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
        explain_tags.append(_badge("사선 지지 유지", "positive"))
    if meta.get("diag_breakout_bull"):
        explain_tags.append(_badge("사선 돌파", "positive"))
    if meta.get("diag_resistance_reject"):
        explain_tags.append(_badge("사선 저항 거부", "negative"))
    if meta.get("diag_breakdown_bear"):
        explain_tags.append(_badge("사선 이탈", "negative"))

    """
    # legacy block 1 disabled
    flow_cards = [
        _mini_stat_card("초기 판단", pre_veto_label or title or "-", _tone_from_text(pre_veto_label or title or "")),
        _mini_stat_card("최종 판단", title or localize_judgment_label(raw_judgment), tone),
        _mini_stat_card("강등 횟수", f"{downgrade_count}회", "warning" if downgrade_count else "muted"),
        _mini_stat_card("시장 필터", f"{market_filter_bias:+.1f}", "positive" if market_filter_bias > 0.3 else "negative" if market_filter_bias < -0.3 else "warning"),
    ]
    driver_cards = [
        _mini_stat_card("지속 매수", f"{continuation_buy:.1f}", "positive" if continuation_buy >= max(continuation_sell, 1.0) else "muted"),
        _mini_stat_card("지속 매도", f"{continuation_sell:.1f}", "negative" if continuation_sell >= max(continuation_buy, 1.0) else "muted"),
        _mini_stat_card("거시 압력", f"{macro_pressure:+.1f}", "negative" if macro_pressure > 0.5 else "positive" if macro_pressure < -0.5 else "warning"),
        _mini_stat_card("UT 거리", f"{ut_gap:.2f} ATR", "positive" if ut_gap <= 0.9 else "negative" if ut_gap >= 2.0 else "warning"),
        _mini_stat_card("시장 폭", f"{breadth_score:+.1f}", "positive" if breadth_score > 0.5 else "negative" if breadth_score < -0.5 else "warning"),
    ]
    """
    """
    flow_cards = [
        _mini_stat_card("초기 판단", pre_veto_label or title or "-", _tone_from_text(pre_veto_label or title or "")),
        _mini_stat_card("최종 판단", title or localize_judgment_label(raw_judgment), tone),
        _mini_stat_card("강등 횟수", f"{downgrade_count}회", "warning" if downgrade_count else "muted"),
        _mini_stat_card("시장 필터", f"{market_filter_bias:+.1f}", "positive" if market_filter_bias > 0.3 else "negative" if market_filter_bias < -0.3 else "warning"),
    ]
    driver_cards = [
        _mini_stat_card("지속 매수", f"{continuation_buy:.1f}", "positive" if continuation_buy >= max(continuation_sell, 1.0) else "muted"),
        _mini_stat_card("지속 매도", f"{continuation_sell:.1f}", "negative" if continuation_sell >= max(continuation_buy, 1.0) else "muted"),
        _mini_stat_card("거시 압력", f"{macro_pressure:+.1f}", "negative" if macro_pressure > 0.5 else "positive" if macro_pressure < -0.5 else "warning"),
        _mini_stat_card("UT 거리", f"{ut_gap:.2f} ATR", "positive" if ut_gap <= 0.9 else "negative" if ut_gap >= 2.0 else "warning"),
        _mini_stat_card("시장 폭", f"{breadth_score:+.1f}", "positive" if breadth_score > 0.5 else "negative" if breadth_score < -0.5 else "warning"),
    ]
    """
    flow_cards = [
        _mini_stat_card("\uCD08\uAE30 \uD310\uB2E8", pre_veto_label or title or "-", _tone_from_text(pre_veto_label or title or "")),
        _mini_stat_card("\uCD5C\uC885 \uD310\uB2E8", title or localize_judgment_label(raw_judgment), tone),
        _mini_stat_card("\uAC15\uB4F1 \uD69F\uC218", f"{downgrade_count}\uD68C", "warning" if downgrade_count else "muted"),
        _mini_stat_card("\uC2DC\uC7A5 \uD544\uD130", f"{market_filter_bias:+.1f}", "positive" if market_filter_bias > 0.3 else "negative" if market_filter_bias < -0.3 else "warning"),
    ]
    driver_cards = [
        _mini_stat_card("\uC9C0\uC18D \uB9E4\uC218", f"{continuation_buy:.1f}", "positive" if continuation_buy >= max(continuation_sell, 1.0) else "muted"),
        _mini_stat_card("\uC9C0\uC18D \uB9E4\uB3C4", f"{continuation_sell:.1f}", "negative" if continuation_sell >= max(continuation_buy, 1.0) else "muted"),
        _mini_stat_card("\uCD94\uC138 \uC804\uD658 \uB9E4\uC218", f"{trend_inflection_buy:.1f}", "positive" if trend_inflection_buy >= max(trend_inflection_sell, 1.0) else "muted"),
        _mini_stat_card("\uCD94\uC138 \uC804\uD658 \uB9E4\uB3C4", f"{trend_inflection_sell:.1f}", "negative" if trend_inflection_sell >= max(trend_inflection_buy, 1.0) else "muted"),
        _mini_stat_card("\uC2DC\uC7A5 \uC804\uD658 \uAC15\uC138", f"{market_turn_bull_score:.1f}", "positive" if market_turn_bull_score >= max(market_turn_bear_score, 1.0) else "muted"),
        _mini_stat_card("\uC2DC\uC7A5 \uC804\uD658 \uC57D\uC138", f"{market_turn_bear_score:.1f}", "negative" if market_turn_bear_score >= max(market_turn_bull_score, 1.0) else "muted"),
        _mini_stat_card("\uAC70\uC2DC \uC555\uB825", f"{macro_pressure:+.1f}", "negative" if macro_pressure > 0.5 else "positive" if macro_pressure < -0.5 else "warning"),
        _mini_stat_card("UT \uAC70\uB9AC", f"{ut_gap:.2f} ATR", "positive" if ut_gap <= 0.9 else "negative" if ut_gap >= 2.0 else "warning"),
        _mini_stat_card("\uC2DC\uC7A5 \uD3ED", f"{breadth_score:+.1f}", "positive" if breadth_score > 0.5 else "negative" if breadth_score < -0.5 else "warning"),
    ]
    explainer_text = _judgment_explainer(meta, title)

    summary_html = f"""
    <div class="sigl-card sigl-card--{'positive' if tone == 'positive' else 'negative' if tone == 'negative' else 'warning'}">
      <div class="sigl-section-head">
        <div>
          <p class="sigl-section-title">종합 판단</p>
          <p class="sigl-section-copy">현재 가격, 시그널 합의, 리스크를 한 번에 요약합니다.</p>
        </div>
        <div class="sigl-inline">{''.join(badges)}</div>
      </div>
      <div class="sigl-grid sigl-grid--3">
        {_progress_metric_card('결론', title or '중립', localize_judgment_label(raw_judgment), tone, confidence)}
        {_progress_metric_card('종합 점수', f'{es:+.1f}', f'신뢰도 {confidence:.0f}%', tone if tone != 'muted' else 'accent', min(abs(es) / 80 * 100, 100))}
        {_progress_metric_card('합의 비율', f'{buy_agree}:{sell_agree}', localize_context_label(meta.get('context', 0)), 'accent', buy_agree / max(buy_agree + sell_agree, 1) * 100)}
      </div>
    """
    if explainer_text:
        summary_html += f"<div class='sigl-note'><strong>\uC65C \uC774\uB7F0 \uD310\uB2E8\uC774 \uB098\uC654\uB098</strong><br><span class='sigl-summary'>{_esc(explainer_text)}</span></div>"
    summary_html += f"<div class='sigl-note'><strong>\uD310\uB2E8 \uACBD\uB85C</strong><div class='sigl-grid sigl-grid--4'>{''.join(flow_cards)}</div></div>"
    summary_html += f"<div class='sigl-note'><strong>\uD575\uC2EC \uADFC\uAC70</strong><div class='sigl-grid sigl-grid--4'>{''.join(driver_cards)}</div><div class='sigl-chip-row'>{''.join(explain_tags)}</div></div>"
    if detail_text:
        summary_html += f"<div class='sigl-note'><strong>판단 요약</strong><br><span class='sigl-summary'>{_esc(translate_chart_text(detail_text))}</span></div>"
    if contrast or risk_tags:
        contrast_html = f"<p class='sigl-summary' style='margin:0 0 10px'>{_esc(translate_chart_text(contrast))}</p>" if contrast else ""
        summary_html += f"<div class='sigl-note'><strong>리스크 체크</strong>{contrast_html}<div class='sigl-chip-row'>{''.join(risk_tags)}</div></div>"
    summary_html += "</div>"
    _render_panel_html(
        summary_html,
        min_height=_judgment_panel_height(detail_text, contrast, len(risk_tags) + len(explain_tags)),
    )


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
        tier_label = {1: "핵심 T1", 2: "보강 T2", 3: "참고 T3"}.get(item.get("tier"), "참고")
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
              <p class="sigl-section-copy">다중 조건이 함께 만족된 고신뢰 패턴만 모아서 보여줍니다.</p>
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
    rows = []
    for name in layer_names:
        buy_value = max(_safe_float(meta.get("buy_layers", {}).get(name, 0)), 0.0)
        sell_value = max(_safe_float(meta.get("sell_layers", {}).get(name, 0)), 0.0)
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
        "<p class='sigl-section-copy'>매수와 매도 쪽에 각 레이어가 얼마나 기여하는지 보여줍니다.</p>"
        "</div>"
        "<div class='sigl-inline'>"
        f"{_badge(f'매수 {_safe_int(meta.get('buy_active', 0))}/10', 'positive')}"
        f"{_badge(f'매도 {_safe_int(meta.get('sell_active', 0))}/10', 'negative')}"
        "</div>"
        "</div>"
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
            "- `10개 레이어`: 추세, 모멘텀, 거래량, 자금 흐름 등이 매수/매도 쪽에 얼마나 기여하는지 비교합니다."
        )


def render_analysis(msg, key_prefix="analysis"):
    meta = msg.get("meta")
    fig_json = msg.get("fig_json")
    if meta:
        render_price_header(meta, key_prefix=key_prefix)
    if not (meta or fig_json):
        return

    tab_chart, tab_judgment, tab_layers, tab_scans, tab_company = st.tabs(
        ["차트", "판단/리스크", "10개 레이어", "콤보 스캔", "기업 정보"]
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
            st.caption("*차트에는 가격 흐름, 거래량 프로파일, 보조 지표와 패턴 신호가 함께 표시됩니다.")

    with tab_judgment:
        if meta:
            render_judgment_card(meta)
            st.markdown("<div class='sigl-stack-gap'></div>", unsafe_allow_html=True)
            render_committee_panel_clean(meta)
            st.markdown("<div class='sigl-stack-gap sigl-stack-gap--lg'></div>", unsafe_allow_html=True)
            render_leading_lagging(meta)
            render_indicator_help()

    with tab_layers:
        if meta:
            render_10layer_bars_clean(meta, html_key=f"{key_prefix}_10layer")

    with tab_scans:
        if meta:
            render_combined_scans(meta)

    with tab_company:
        if meta:
            render_company_details(meta["ticker"], key_prefix=f"{key_prefix}_company")
