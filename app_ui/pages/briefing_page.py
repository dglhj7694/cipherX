from __future__ import annotations

from typing import Any, Callable, Mapping

import streamlit as st


def render_briefing_page(
    *,
    render_brand_board: Callable[..., None],
    main_board_payload: Mapping[str, Any],
    render_section_heading: Callable[..., None],
    market_daily_payload: Mapping[str, Any],
    render_market_daily_action_grid: Callable[..., None],
    on_select_ticker: Callable[[str], None],
    chat_input_placeholder: str,
    parse_ticker_input: Callable[[str], list[str]],
) -> None:
    render_brand_board(main_board_payload)
    render_section_heading(
        "오늘 먼저 볼 강한 종목",
        "시장 브리핑에서 고른 종목을 바로 개별 분석으로 넘깁니다.",
        badges=[
            ("브리핑", "accent"),
            ("즉시 분석 전환", "warning"),
        ],
        eyebrow="Daily To Analysis",
        tight=True,
    )
    render_market_daily_action_grid(market_daily_payload, key_prefix="briefing_dynamic")
    if ti := st.chat_input(chat_input_placeholder):
        parsed = parse_ticker_input(ti)
        if parsed:
            on_select_ticker(parsed[0])
