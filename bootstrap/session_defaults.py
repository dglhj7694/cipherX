from __future__ import annotations

from typing import Any

import streamlit as st


def build_default_session_state(initial_messages: list[dict[str, Any]], default_mode: str) -> dict[str, Any]:
    return {
        "_mode": default_mode,
        "_auto": None,
        "quick": None,
        "period": "6개월",
        "runtime_gemini_api_key": "",
        "runtime_gemini_api_key_input": "",
        "show_runtime_gemini_key_setup": False,
        "messages": [dict(item) for item in initial_messages],
        "pending_ai_ticker": None,
        "pending_ai_prompt": None,
        "last_ticker": None,
        "scan_results": [],
        "scan_source": "",
        "scan_total": 0,
        "scan_focus_idx": None,
        "scan_focus_ticker": None,
        "scan_nav_select_idx": None,
        "selected_sector": None,
        "selected_sectors": [],
        "scan_tickers_override": None,
        "scan_etf_items": [],
        "scan_etf_tickers_override": None,
        "scan_etf_note": "",
        "scan_etf_errors": [],
        "scan_etf_picker": [],
        "scan_sector_picker": [],
        "_clear_scan_pending": False,
    }


def ensure_session_defaults(defaults: dict[str, Any]) -> None:
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_session_state(defaults: dict[str, Any]) -> None:
    for key, value in defaults.items():
        if isinstance(value, list):
            st.session_state[key] = list(value)
        elif isinstance(value, dict):
            st.session_state[key] = dict(value)
        else:
            st.session_state[key] = value
