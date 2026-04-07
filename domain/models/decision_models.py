from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from domain.enums import Label


@dataclass
class DecisionEvidence:
    buy_total: float
    sell_total: float
    ensemble_score: float
    objective_buy_score: float
    objective_sell_score: float
    buy_agree: int
    sell_agree: int
    market_context: str
    veto_flags: list[str] = field(default_factory=list)
    contrast_notes: list[str] = field(default_factory=list)


@dataclass
class CommitteeReview:
    label: str
    pre_veto_label: str
    confidence: float
    buy_agree: int
    sell_agree: int
    reason: str
    detail: str
    action_label: str
    contrast_notes: list[str] = field(default_factory=list)
    downgrade_count: int = 0
    macro_risk_off_count: int = 0
    macro_risk_on_count: int = 0
    flip_guard_triggered: bool = False


@dataclass
class ObjectiveReview:
    buy_score: float
    sell_score: float
    conflict_score: float
    advisory_label: str
    alignment: str
    adjustment: str
    confidence: float
    reason: str
    detail: str
    action_label: str
    contrast_notes: list[str] = field(default_factory=list)


@dataclass
class FinalDecision:
    label: Label
    confidence: float
    action_label: str
    decision_score: float
    reason: str
    detail: str
    pre_veto_label: str = "NEUTRAL"
    buy_agree: int = 0
    sell_agree: int = 0
    contrast_notes: list[str] = field(default_factory=list)
    downgrade_count: int = 0
    macro_risk_off_count: int = 0
    macro_risk_on_count: int = 0
    flip_guard_triggered: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "confidence": float(self.confidence),
            "action_label": str(self.action_label),
            "decision_score": float(self.decision_score),
            "reason": str(self.reason),
            "detail": str(self.detail),
            "pre_veto_label": str(self.pre_veto_label),
            "buy_agree": int(self.buy_agree),
            "sell_agree": int(self.sell_agree),
            "contrast_notes": list(self.contrast_notes),
            "downgrade_count": int(self.downgrade_count),
            "macro_risk_off_count": int(self.macro_risk_off_count),
            "macro_risk_on_count": int(self.macro_risk_on_count),
            "flip_guard_triggered": bool(self.flip_guard_triggered),
        }


@dataclass
class EngineResult:
    frame: pd.DataFrame
    evidence: DecisionEvidence
    committee: CommitteeReview
    objective: ObjectiveReview
    decision: FinalDecision
