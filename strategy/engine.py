from __future__ import annotations

from typing import Iterable

import pandas as pd

from .evaluators import STRATEGY_EVALUATORS
from .models import VISIBLE_STATUSES, StrategyDefinition, StrategyResult, StrategySummary
from .registry import build_strategy_definitions
from .state_builder import build_market_state as _build_market_state
from .summary import build_summary as _build_summary


STRATEGY_DEFINITIONS: tuple[StrategyDefinition, ...] = build_strategy_definitions(StrategyDefinition)


def build_strategy_payload(dc: pd.DataFrame) -> dict:
    engine = StrategyEngine()
    return engine.build_payload(dc)


class StrategyEngine:
    def __init__(self, definitions: Iterable[StrategyDefinition] | None = None):
        self.definitions = tuple(definitions or STRATEGY_DEFINITIONS)

    def build_payload(self, dc: pd.DataFrame) -> dict:
        if dc is None or dc.empty:
            empty_summary = StrategySummary(
                active_count=0,
                visible_count=0,
                bullish_count=0,
                bearish_count=0,
                long_short_bias="BALANCED",
                conflict_level="LOW",
                top_strategy=None,
            )
            return {"summary": empty_summary.to_dict(), "results": [], "visible_results": []}
        market_state = _build_market_state(dc)
        results = [self._evaluate(definition, market_state) for definition in self.definitions]
        results.sort(key=lambda item: (item.score, item.trigger_score, item.setup_score), reverse=True)
        visible = [item for item in results if item.status in VISIBLE_STATUSES]
        summary = _build_summary(visible, results)
        return {
            "summary": summary.to_dict(),
            "results": [item.to_dict() for item in results],
            "visible_results": [item.to_dict() for item in visible],
        }

    def _evaluate(self, definition: StrategyDefinition, market_state: dict) -> StrategyResult:
        return STRATEGY_EVALUATORS[definition.family](definition, market_state)


