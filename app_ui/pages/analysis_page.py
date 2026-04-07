from __future__ import annotations

from ui_localized import render_analysis


def render_analysis_message(message: dict, *, key_prefix: str) -> None:
    render_analysis(message, key_prefix=key_prefix)
