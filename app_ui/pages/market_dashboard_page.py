from __future__ import annotations

import html
from typing import Any, Callable, Iterable, Mapping

import pandas as pd
import plotly.express as px
import streamlit as st

from services.market_heatmap_service import build_market_heatmap_payload
from services.quant_prediction_service import build_quant_prediction_payload

from .home_page import load_latest_telegram_digest


def _optional_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number else None


def _format_float(value: Any, decimals: int = 2, *, signed: bool = False, suffix: str = "") -> str:
    number = _optional_float(value)
    if number is None:
        return "--"
    body = f"{number:+.{decimals}f}" if signed else f"{number:.{decimals}f}"
    return f"{body}{suffix}"


def _source_label(source: str) -> str:
    return {
        "scanner": "Scanner",
        "telegram": "Telegram Digest",
        "market": "Market Briefing",
        "empty": "No Data",
    }.get(str(source or ""), str(source or "No Data"))


def _metric_tone(metric_key: str) -> tuple[list[str], float | None]:
    if metric_key in {"chg", "chg_5d"}:
        return ["#EF4444", "#334155", "#22C55E"], 0.0
    if metric_key in {"volume_ratio_20", "atr_pct", "signal_count"}:
        return ["#334155", "#38BDF8", "#F59E0B"], None
    if metric_key in {"rs_rank_vs_index", "adx"}:
        return ["#334155", "#8EA4FF", "#22C55E"], None
    return ["#334155", "#8EA4FF", "#22C55E"], None


def _metric_display_value(row: Mapping[str, Any], metric_key: str) -> str:
    if metric_key in {"chg", "chg_5d", "atr_pct"}:
        return _format_float(row.get(metric_key), 2, signed=metric_key in {"chg", "chg_5d"}, suffix="%")
    if metric_key == "volume_ratio_20":
        return "x" + _format_float(row.get(metric_key), 2)
    if metric_key in {"rs_rank_vs_index", "adx", "signal_count"}:
        return _format_float(row.get(metric_key), 0)
    return _format_float(row.get(metric_key), 2)


def _format_ratio(value: Any) -> str:
    return "x" + _format_float(value, 2)


def _clean_heatmap_rows(rows: Iterable[Mapping[str, Any]], metric_key: str) -> pd.DataFrame:
    frame = pd.DataFrame([dict(row or {}) for row in rows or []])
    if frame.empty:
        return frame
    for key in ("sector", "ticker", "source"):
        if key not in frame:
            frame[key] = ""
        frame[key] = frame[key].fillna("").astype(str)
    for key in ("size", metric_key, "chg", "chg_5d", "volume_ratio_20", "atr_pct", "rs_rank_vs_index", "adx", "signal_count"):
        if key not in frame:
            frame[key] = None
        frame[key] = pd.to_numeric(frame[key], errors="coerce")
    frame["sector"] = frame["sector"].where(frame["sector"].str.strip() != "", "Unclassified")
    frame["ticker"] = frame["ticker"].str.upper()
    frame["size"] = frame["size"].fillna(1.0).clip(lower=0.1)
    frame["metric_value"] = frame[metric_key].fillna(0.0)
    frame["metric_text"] = [_metric_display_value(row, metric_key) for row in frame.to_dict("records")]
    frame["root"] = "Market"
    return frame


def _render_heatmap_styles() -> None:
    st.markdown(
        """
        <style>
        .sigl-dashboard-note {
            color: var(--sigl-text-muted, #94A3B8);
            font-size: .82rem;
            font-weight: 750;
            margin: -4px 0 10px;
        }
        .sigl-heatmap-meta {
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 8px;
            margin: 0 0 12px;
        }
        .sigl-heatmap-pill {
            display: inline-flex;
            align-items: center;
            min-height: 24px;
            padding: 4px 9px;
            border: 1px solid rgba(148, 163, 184, .18);
            border-radius: 999px;
            background: rgba(148, 163, 184, .08);
            color: var(--sigl-text, #E2E8F0);
            font-size: .72rem;
            font-weight: 850;
            white-space: nowrap;
        }
        .sigl-heatmap-pill[data-tone="accent"] {
            border-color: rgba(142, 164, 255, .38);
            background: rgba(142, 164, 255, .14);
            color: #E5EAFF;
        }
        .sigl-heatmap-pill[data-tone="positive"] {
            border-color: rgba(99, 217, 162, .34);
            background: rgba(16, 185, 129, .14);
            color: #BDF7D6;
        }
        .sigl-heatmap-pill[data-tone="warning"] {
            border-color: rgba(246, 195, 94, .38);
            background: rgba(245, 158, 11, .12);
            color: #FFE0A3;
        }
        .sigl-heatmap-pill[data-tone="negative"] {
            border-color: rgba(255, 143, 150, .34);
            background: rgba(239, 68, 68, .13);
            color: #FFC4C8;
        }
        .sigl-quant-panel {
            width: 100%;
            overflow: hidden;
            border: 1px solid rgba(148, 163, 184, .18);
            border-radius: 8px;
            background: rgba(9, 14, 25, .70);
            margin: 8px 0 14px;
        }
        .sigl-quant-head {
            display: flex;
            justify-content: space-between;
            align-items: stretch;
            gap: 16px;
            padding: 16px;
            border-bottom: 1px solid rgba(148, 163, 184, .14);
            background: rgba(15, 23, 42, .66);
        }
        .sigl-quant-title {
            color: var(--sigl-text-strong, #F8FAFC);
            font-size: 1rem;
            font-weight: 950;
        }
        .sigl-quant-head p {
            max-width: 720px;
            margin: 6px 0 0;
            color: var(--sigl-text-muted, #94A3B8);
            font-size: .78rem;
            font-weight: 720;
            line-height: 1.45;
        }
        .sigl-quant-stats {
            display: grid;
            grid-template-columns: repeat(5, minmax(78px, 1fr));
            gap: 8px;
            min-width: min(520px, 100%);
        }
        .sigl-quant-stat {
            padding: 9px 10px;
            border: 1px solid rgba(148, 163, 184, .14);
            border-radius: 8px;
            background: rgba(255, 255, 255, .04);
        }
        .sigl-quant-stat b {
            display: block;
            color: var(--sigl-text-muted, #94A3B8);
            font-size: .64rem;
            font-weight: 900;
            text-transform: uppercase;
        }
        .sigl-quant-stat strong {
            display: block;
            margin-top: 3px;
            color: var(--sigl-text-strong, #F8FAFC);
            font-size: .88rem;
            font-weight: 950;
            font-variant-numeric: tabular-nums;
        }
        .sigl-quant-table-wrap {
            width: 100%;
            max-height: 560px;
            overflow: auto;
        }
        table.sigl-quant-table {
            width: 100%;
            min-width: 1180px;
            border-collapse: separate;
            border-spacing: 0;
        }
        .sigl-quant-table th {
            position: sticky;
            top: 0;
            z-index: 1;
            padding: 8px 10px;
            border-bottom: 1px solid rgba(148, 163, 184, .18);
            background: rgba(15, 23, 42, .98);
            color: var(--sigl-text-muted, #94A3B8);
            font-size: .68rem;
            font-weight: 950;
            text-align: left;
            text-transform: uppercase;
            white-space: nowrap;
        }
        .sigl-quant-table td {
            padding: 7px 10px;
            border-top: 1px solid rgba(148, 163, 184, .08);
            color: var(--sigl-text, #E2E8F0);
            font-size: .76rem;
            font-weight: 800;
            vertical-align: middle;
            white-space: nowrap;
        }
        .sigl-quant-table tr:hover td {
            background: rgba(142, 164, 255, .06);
        }
        .sigl-quant-cell {
            display: inline-flex;
            align-items: center;
            min-height: 24px;
            padding: 4px 8px;
            border-radius: 6px;
            border: 1px solid rgba(148, 163, 184, .14);
            background: rgba(148, 163, 184, .08);
            font-variant-numeric: tabular-nums;
        }
        .sigl-quant-cell[data-tone="accent"] {
            border-color: rgba(142, 164, 255, .40);
            background: rgba(142, 164, 255, .14);
            color: #E5EAFF;
        }
        .sigl-quant-cell[data-tone="positive"] {
            border-color: rgba(99, 217, 162, .34);
            background: rgba(16, 185, 129, .16);
            color: #BDF7D6;
        }
        .sigl-quant-cell[data-tone="warning"] {
            border-color: rgba(246, 195, 94, .38);
            background: rgba(245, 158, 11, .15);
            color: #FFE2A8;
        }
        .sigl-quant-cell[data-tone="negative"] {
            border-color: rgba(255, 143, 150, .34);
            background: rgba(239, 68, 68, .16);
            color: #FFC4C8;
        }
        .sigl-quant-token-list {
            display: flex;
            flex-wrap: wrap;
            gap: 4px;
            max-width: 300px;
        }
        .sigl-quant-token {
            display: inline-flex;
            align-items: center;
            min-height: 20px;
            padding: 3px 6px;
            border-radius: 6px;
            border: 1px solid rgba(148, 163, 184, .14);
            background: rgba(148, 163, 184, .08);
            color: var(--sigl-text, #E2E8F0);
            font-size: .68rem;
            font-weight: 850;
            line-height: 1;
        }
        .sigl-quant-token[data-tone="positive"] {
            border-color: rgba(99, 217, 162, .30);
            background: rgba(16, 185, 129, .14);
            color: #BDF7D6;
        }
        .sigl-quant-token[data-tone="warning"] {
            border-color: rgba(246, 195, 94, .34);
            background: rgba(245, 158, 11, .13);
            color: #FFE0A3;
        }
        @media (max-width: 760px) {
            .sigl-quant-head {
                display: block;
            }
            .sigl-quant-stats {
                grid-template-columns: repeat(2, minmax(0, 1fr));
                margin-top: 12px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _pill(text: Any, tone: str = "muted") -> str:
    safe_text = html.escape(str(text or "").strip())
    return f"<span class='sigl-heatmap-pill' data-tone='{html.escape(tone)}'>{safe_text}</span>"


def _prediction_tone(label: Any, up_probability: Any = None) -> str:
    text = str(label or "").upper()
    if text == "UP":
        return "positive"
    if text == "DOWN":
        return "negative"
    number = _optional_float(up_probability)
    if number is not None and number >= 62:
        return "positive"
    if number is not None and number <= 42:
        return "negative"
    return "warning"


def _quant_cell(text: Any, tone: str = "muted") -> str:
    if tone not in {"accent", "positive", "warning", "negative", "muted"}:
        tone = "muted"
    safe_text = html.escape(str(text if text is not None else "--"))
    return f"<span class='sigl-quant-cell' data-tone='{tone}'>{safe_text}</span>"


def _quant_token_html(text: Any, tone: str = "muted") -> str:
    safe_text = html.escape(str(text or "").strip())
    if not safe_text:
        return ""
    if tone not in {"positive", "warning", "muted"}:
        tone = "muted"
    return f"<span class='sigl-quant-token' data-tone='{tone}'>{safe_text}</span>"


def _quant_tokens_html(values: Any, tone: str = "muted", *, limit: int = 4) -> str:
    items = [str(item or "").strip() for item in list(values or []) if str(item or "").strip()]
    items = items[: max(0, int(limit or 0))]
    if not items:
        return _quant_cell("-", "muted")
    return f"<div class='sigl-quant-token-list'>{''.join(_quant_token_html(item, tone) for item in items)}</div>"


def _quant_summary_html(payload: Mapping[str, Any]) -> str:
    summary = dict(dict(payload or {}).get("summary") or {})
    rows = list(dict(payload or {}).get("rows") or [])
    source = str(dict(payload or {}).get("source") or "empty")
    stats = [
        ("Source", _source_label(source)),
        ("Tickers", f"{int(summary.get('ticker_count') or len(rows)):,}"),
        ("UP", f"{int(summary.get('up_count') or 0):,}"),
        ("Neutral", f"{int(summary.get('neutral_count') or 0):,}"),
        ("Avg Up", _format_float(summary.get("average_up_probability"), 1, suffix="%")),
    ]
    stats_html = "".join(
        f"<div class='sigl-quant-stat'><b>{html.escape(label)}</b><strong>{html.escape(str(value))}</strong></div>"
        for label, value in stats
    )
    note = str(dict(payload or {}).get("note") or "")
    return (
        "<div class='sigl-quant-head'>"
        "<div>"
        "<div class='sigl-dashboard-note' style='margin:0 0 4px'>Next Session</div>"
        "<div class='sigl-quant-title'>Quant Prediction</div>"
        f"<p>{html.escape(note)}</p>"
        "</div>"
        f"<div class='sigl-quant-stats'>{stats_html}</div>"
        "</div>"
    )


def _quant_rows_html(rows: Iterable[Mapping[str, Any]]) -> str:
    body: list[str] = []
    for row in rows:
        label = str(row.get("prediction_label") or "NEUTRAL")
        tone = _prediction_tone(label, row.get("up_probability"))
        body.append(
            "<tr>"
            f"<td>{_quant_cell(row.get('ticker'), 'accent')}</td>"
            f"<td>{_quant_cell(label, tone)}</td>"
            f"<td>{_quant_cell(_format_float(row.get('up_probability'), 1, suffix='%'), tone)}</td>"
            f"<td>{_quant_cell(_format_float(row.get('down_probability'), 1, suffix='%'), 'negative' if label == 'DOWN' else 'muted')}</td>"
            f"<td>{_quant_cell(_format_float(row.get('confidence'), 1, suffix='%'), tone)}</td>"
            f"<td>{_quant_cell(_format_float(row.get('chg'), 2, signed=True, suffix='%'), 'positive' if (_optional_float(row.get('chg')) or 0) > 0 else 'negative' if (_optional_float(row.get('chg')) or 0) < 0 else 'muted')}</td>"
            f"<td>{_quant_cell(_format_float(row.get('chg_5d'), 2, signed=True, suffix='%'), 'positive' if (_optional_float(row.get('chg_5d')) or 0) > 0 else 'negative' if (_optional_float(row.get('chg_5d')) or 0) < 0 else 'muted')}</td>"
            f"<td>{_quant_cell(_format_float(row.get('atr_pct'), 1, suffix='%'), 'warning' if (_optional_float(row.get('atr_pct')) or 0) >= 12 else 'muted')}</td>"
            f"<td>{_quant_cell(_format_ratio(row.get('volume_ratio_20')), 'positive' if (_optional_float(row.get('volume_ratio_20')) or 0) >= 1.2 else 'muted')}</td>"
            f"<td>{_quant_cell(_format_float(row.get('rs_rank_vs_index'), 0), 'positive' if (_optional_float(row.get('rs_rank_vs_index')) or 0) >= 70 else 'muted')}</td>"
            f"<td>{_quant_cell(_format_float(row.get('adx'), 0), 'positive' if (_optional_float(row.get('adx')) or 0) >= 25 else 'muted')}</td>"
            f"<td>{_quant_tokens_html(row.get('prediction_reason'), 'positive', limit=4)}</td>"
            f"<td>{_quant_tokens_html(row.get('risk_flags'), 'warning', limit=4)}</td>"
            "</tr>"
        )
    return "".join(body)


def _render_quant_prediction(
    prediction_payload: Mapping[str, Any],
    *,
    render_empty_state: Callable[..., None],
) -> None:
    rows = list(dict(prediction_payload or {}).get("rows") or [])
    if not rows:
        render_empty_state(
            "Quant Prediction 데이터가 없습니다",
            "scanner 결과, Telegram digest, market mover 중 하나가 있어야 다음 거래일 확률 추정표를 만들 수 있습니다.",
            badges=[("Quant", "warning"), ("No Data", "muted")],
            tone="warning",
        )
        return

    top_rows = rows[:20]
    table_html = (
        "<div class='sigl-quant-panel'>"
        f"{_quant_summary_html(prediction_payload)}"
        "<div class='sigl-quant-table-wrap'>"
        "<table class='sigl-quant-table'>"
        "<thead><tr>"
        "<th>Ticker</th><th>Label</th><th>Up</th><th>Down</th><th>Confidence</th>"
        "<th>Today</th><th>5D</th><th>ATR</th><th>Vol20</th><th>RS</th><th>ADX</th>"
        "<th>Reason</th><th>Risk</th>"
        "</tr></thead>"
        f"<tbody>{_quant_rows_html(top_rows)}</tbody>"
        "</table>"
        "</div>"
        "</div>"
    )
    st.markdown(table_html, unsafe_allow_html=True)


def _render_top_table(title: str, rows: list[dict[str, Any]], metric_key: str) -> None:
    st.caption(title)
    if not rows:
        st.caption("표시할 데이터가 없습니다.")
        return
    table_rows = []
    for row in rows[:8]:
        table_rows.append(
            {
                "Ticker": row.get("ticker"),
                "Sector": row.get("sector"),
                "Change": _format_float(row.get("chg"), 2, signed=True, suffix="%"),
                "5D": _format_float(row.get("chg_5d"), 2, signed=True, suffix="%"),
                "Vol20": "x" + _format_float(row.get("volume_ratio_20"), 2),
                "ATR": _format_float(row.get("atr_pct"), 2, suffix="%"),
                "Metric": _metric_display_value(row, metric_key),
            }
        )
    st.dataframe(pd.DataFrame(table_rows), width="stretch", hide_index=True, height=312)


def _render_market_heatmap(
    heatmap_payload: Mapping[str, Any],
    *,
    render_empty_state: Callable[..., None],
) -> None:
    rows = list(dict(heatmap_payload or {}).get("rows") or [])
    source = str(dict(heatmap_payload or {}).get("source") or "empty")
    summary = dict(dict(heatmap_payload or {}).get("summary") or {})
    options = dict(dict(heatmap_payload or {}).get("metric_options") or {})
    if not rows:
        render_empty_state(
            "Heatmap 데이터가 없습니다",
            "scanner 결과 또는 Telegram digest 동기화가 필요합니다.",
            badges=[("Heatmap", "warning"), ("No Data", "muted")],
            tone="warning",
        )
        return

    option_keys = list(options.keys()) or ["Change"]
    metric_label = st.radio(
        "Heatmap metric",
        options=option_keys,
        horizontal=True,
        format_func=lambda key: str(key),
        key="market_dashboard_heatmap_metric",
        label_visibility="collapsed",
    )
    metric_key = str(options.get(str(metric_label)) or "chg")
    frame = _clean_heatmap_rows(rows, metric_key)
    scale, midpoint = _metric_tone(metric_key)
    badges = "".join(
        [
            _pill(_source_label(source), "accent"),
            _pill(f"{int(summary.get('ticker_count') or len(rows))} tickers", "positive"),
            _pill(f"{int(summary.get('sector_count') or 0)} sectors", "muted"),
        ]
    )
    st.markdown(f"<div class='sigl-heatmap-meta'>{badges}</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='sigl-dashboard-note'>Quant Prediction과 AI News Judgment는 이 Heatmap 값에 섞지 않고 별도 모듈로 분리됩니다.</div>",
        unsafe_allow_html=True,
    )

    fig = px.treemap(
        frame,
        path=["root", "sector", "ticker"],
        values="size",
        color="metric_value",
        color_continuous_scale=scale,
        color_continuous_midpoint=midpoint,
        hover_data={
            "root": False,
            "sector": True,
            "ticker": True,
            "size": ":.2f",
            "metric_value": ":.2f",
            "metric_text": True,
            "chg": ":.2f",
            "chg_5d": ":.2f",
            "volume_ratio_20": ":.2f",
            "atr_pct": ":.2f",
            "rs_rank_vs_index": ":.0f",
            "adx": ":.0f",
            "signal_count": ":.0f",
        },
    )
    fig.update_traces(
        marker_line_width=1,
        marker_line_color="rgba(15,23,42,.78)",
        textfont=dict(color="#F8FAFC", size=13),
        hovertemplate="<b>%{label}</b><br>%{customdata[1]}<br>Metric %{customdata[4]}<br>Change %{customdata[5]:+.2f}%<br>5D %{customdata[6]:+.2f}%<extra></extra>",
    )
    fig.update_layout(
        height=640,
        margin=dict(l=0, r=0, t=8, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E2E8F0"),
        coloraxis_colorbar=dict(
            title=dict(text=str(metric_label), font=dict(color="#CBD5E1")),
            tickfont=dict(color="#CBD5E1"),
        ),
    )
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    gain_col, decline_col, volume_col, atr_col = st.columns(4)
    with gain_col:
        _render_top_table("상승 상위", list(summary.get("top_gain") or []), metric_key)
    with decline_col:
        _render_top_table("하락 상위", list(summary.get("top_decline") or []), metric_key)
    with volume_col:
        _render_top_table("거래량 상위", list(summary.get("top_volume") or []), metric_key)
    with atr_col:
        _render_top_table("고변동 상위", list(summary.get("top_volatility") or []), metric_key)


def render_market_dashboard_page(
    *,
    render_brand_board: Callable[..., None],
    main_board_payload: Mapping[str, Any],
    render_section_heading: Callable[..., None],
    render_empty_state: Callable[..., None],
    render_market_daily_dashboard: Callable[[], Mapping[str, Any]],
    render_market_daily_action_grid: Callable[..., None],
    scanner_rows: Iterable[Mapping[str, Any]],
    on_select_ticker: Callable[[str], None],
    chat_input_placeholder: str,
    parse_ticker_input: Callable[[str], list[str]],
) -> None:
    _render_heatmap_styles()
    render_brand_board(main_board_payload)
    render_section_heading(
        "Market Dashboard",
        "Market Briefing, Heatmap, Action Candidates를 한 화면에서 봅니다.",
        badges=[("Dashboard", "accent"), ("Heatmap v1", "positive"), ("Quant v1", "info")],
        eyebrow="Today Market",
        tight=True,
    )

    market_payload = dict(render_market_daily_dashboard() or {})
    digest_result = load_latest_telegram_digest()
    telegram_payload = dict(digest_result.get("payload") or {})
    heatmap_payload = build_market_heatmap_payload(
        scanner_rows=scanner_rows,
        telegram_payload=telegram_payload,
        market_payload=market_payload,
        max_rows=250,
    )
    quant_prediction_payload = build_quant_prediction_payload(
        scanner_rows=scanner_rows,
        telegram_payload=telegram_payload,
        market_payload=market_payload,
        max_rows=80,
    )

    render_section_heading(
        "Market Heatmap",
        "섹터와 종목별 자금 흐름을 스캐너, Telegram digest, 브리핑 데이터 순서로 시각화합니다.",
        badges=[("Scanner 우선", "accent"), ("Telegram fallback", "warning"), ("No AI Prediction", "muted")],
        eyebrow="Heatmap",
        tight=True,
    )
    _render_market_heatmap(heatmap_payload, render_empty_state=render_empty_state)

    render_section_heading(
        "Quant Prediction",
        "가격, 거래량, 변동성, 추세, 상대강도 기반으로 다음 거래일 방향 확률을 추정합니다. 뉴스/LLM 판단은 섞지 않습니다.",
        badges=[("Rule v1", "accent"), ("No LLM", "muted"), ("Top 20", "positive")],
        eyebrow="Prediction",
        tight=True,
    )
    _render_quant_prediction(quant_prediction_payload, render_empty_state=render_empty_state)

    render_section_heading(
        "Action Candidates",
        "브리핑에서 고른 종목을 바로 개별 분석으로 넘깁니다.",
        badges=[("즉시 분석 전환", "warning")],
        eyebrow="Daily To Analysis",
        tight=True,
    )
    render_market_daily_action_grid(market_payload, key_prefix="dashboard_action")

    if ti := st.chat_input(chat_input_placeholder):
        parsed = parse_ticker_input(ti)
        if parsed:
            on_select_ticker(parsed[0])
