from __future__ import annotations

from ui_localized import render_analysis


def render_analysis_message(
    message: dict,
    *,
    key_prefix: str,
    allow_plan_save: bool = False,
) -> None:
    render_analysis(message, key_prefix=key_prefix, allow_plan_save=allow_plan_save)
