from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from .dependencies import AppDependencies, build_dependencies
from .session_defaults import build_default_session_state, ensure_session_defaults


@dataclass
class AppInitContext:
    mode: str
    chart_period: str
    chart_days: int
    dependencies: AppDependencies


_CHART_PERIOD_TO_DAYS = {
    "3개월": 63,
    "6개월": 126,
    "1년": 252,
    "2년": 504,
}


def init_app(*, initial_messages, default_mode, app_mode_options, chart_period_options) -> AppInitContext:
    defaults = build_default_session_state(initial_messages, default_mode)
    ensure_session_defaults(defaults)

    mode = str(st.session_state.get("_mode", default_mode))
    if mode not in app_mode_options:
        mode = default_mode
        st.session_state["_mode"] = mode

    chart_period = str(st.session_state.get("period", chart_period_options[0]))
    if chart_period not in chart_period_options:
        chart_period = chart_period_options[0]
        st.session_state["period"] = chart_period

    chart_days = _CHART_PERIOD_TO_DAYS.get(chart_period, 126)
    return AppInitContext(
        mode=mode,
        chart_period=chart_period,
        chart_days=chart_days,
        dependencies=build_dependencies(st.session_state.get("runtime_gemini_api_key")),
    )
