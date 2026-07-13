from __future__ import annotations

from typing import Any


__all__ = [
    "AIKeyState",
    "AnalysisService",
    "build_ai_client",
    "build_beginner_trade_guide",
    "build_entry_trade_plan",
    "build_holding_trade_plan",
    "assess_trade_plan",
    "add_trade_plan",
    "calculate_position_size",
    "calculate_execution_ticket",
    "calculate_long_holding_scenario",
    "calculate_portfolio_risk_summary",
    "decode_trade_plan_bundle",
    "delete_trade_plan",
    "encode_trade_plan_bundle",
    "generate_ai_signal_assisted",
    "merge_trade_plans",
    "inspect_portfolio_risk_plans",
    "update_trade_plan_status",
    "validate_execution_levels",
    "validate_trade_plan",
]


def __getattr__(name: str) -> Any:
    """Load service exports only when requested.

    Importing a small independent service should not initialize the optional AI
    client or the chart/analysis stack.
    """

    if name in {"AIKeyState", "build_ai_client", "generate_ai_signal_assisted"}:
        from .ai_signal_service import AIKeyState, build_ai_client, generate_ai_signal_assisted

        exports = {
            "AIKeyState": AIKeyState,
            "build_ai_client": build_ai_client,
            "generate_ai_signal_assisted": generate_ai_signal_assisted,
        }
    elif name == "AnalysisService":
        from .analysis_service import AnalysisService

        exports = {"AnalysisService": AnalysisService}
    elif name in {
        "build_beginner_trade_guide",
        "calculate_execution_ticket",
        "calculate_position_size",
        "validate_execution_levels",
    }:
        from .beginner_trade_guide import (
            build_beginner_trade_guide,
            calculate_execution_ticket,
            calculate_position_size,
            validate_execution_levels,
        )

        exports = {
            "build_beginner_trade_guide": build_beginner_trade_guide,
            "calculate_execution_ticket": calculate_execution_ticket,
            "calculate_position_size": calculate_position_size,
            "validate_execution_levels": validate_execution_levels,
        }
    elif name == "calculate_long_holding_scenario":
        from .holding_scenario import calculate_long_holding_scenario

        exports = {"calculate_long_holding_scenario": calculate_long_holding_scenario}
    elif name in {"calculate_portfolio_risk_summary", "inspect_portfolio_risk_plans"}:
        from .portfolio_risk_service import calculate_portfolio_risk_summary, inspect_portfolio_risk_plans

        exports = {
            "calculate_portfolio_risk_summary": calculate_portfolio_risk_summary,
            "inspect_portfolio_risk_plans": inspect_portfolio_risk_plans,
        }
    elif name in {
        "add_trade_plan",
        "assess_trade_plan",
        "build_entry_trade_plan",
        "build_holding_trade_plan",
        "decode_trade_plan_bundle",
        "delete_trade_plan",
        "encode_trade_plan_bundle",
        "merge_trade_plans",
        "update_trade_plan_status",
        "validate_trade_plan",
    }:
        from .trade_plan_service import (
            add_trade_plan,
            assess_trade_plan,
            build_entry_trade_plan,
            build_holding_trade_plan,
            decode_trade_plan_bundle,
            delete_trade_plan,
            encode_trade_plan_bundle,
            merge_trade_plans,
            update_trade_plan_status,
            validate_trade_plan,
        )

        exports = {
            "add_trade_plan": add_trade_plan,
            "assess_trade_plan": assess_trade_plan,
            "build_entry_trade_plan": build_entry_trade_plan,
            "build_holding_trade_plan": build_holding_trade_plan,
            "decode_trade_plan_bundle": decode_trade_plan_bundle,
            "delete_trade_plan": delete_trade_plan,
            "encode_trade_plan_bundle": encode_trade_plan_bundle,
            "merge_trade_plans": merge_trade_plans,
            "update_trade_plan_status": update_trade_plan_status,
            "validate_trade_plan": validate_trade_plan,
        }
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    globals().update(exports)
    return exports[name]
