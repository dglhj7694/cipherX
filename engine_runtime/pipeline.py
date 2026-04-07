from __future__ import annotations

import pandas as pd

from domain import CommitteeReview, DecisionEvidence, EngineResult, FinalDecision, ObjectiveReview
from engine_combo_registry import ensure_runtime_combo_registry
from engine_combo_scans import detect_combined_scans
from engine_runtime.committee_scores import compute_committee_scores
from engine_runtime.final_decision import compute_final_decision
from engine_runtime.objective_scores import compute_objective_scores
from engine_runtime.scoring.layer_scores import compute_layer_scores


def apply_runtime_pipeline(df: pd.DataFrame, vol_ratio, hma_rising, hma_rising_values, combo_registry):
    registry = ensure_runtime_combo_registry(combo_registry)
    df = detect_combined_scans(df, vol_ratio, hma_rising, registry=registry)
    df = compute_layer_scores(df, vol_ratio, hma_rising_values, registry)
    df = compute_committee_scores(df, vol_ratio, hma_rising_values)
    df = compute_objective_scores(df, vol_ratio)
    df = compute_final_decision(df)
    return df


def build_engine_result(df: pd.DataFrame) -> EngineResult:
    if df is None or df.empty:
        raise ValueError("frame is empty")
    latest = df.iloc[-1]
    evidence = DecisionEvidence(
        buy_total=float(latest.get("Buy_Total", 0) or 0),
        sell_total=float(latest.get("Sell_Total", 0) or 0),
        ensemble_score=float(latest.get("Ensemble_Score", 0) or 0),
        objective_buy_score=float(latest.get("Objective_Buy_Score", 0) or 0),
        objective_sell_score=float(latest.get("Objective_Sell_Score", 0) or 0),
        buy_agree=int(latest.get("Buy_Agree", 0) or 0),
        sell_agree=int(latest.get("Sell_Agree", 0) or 0),
        market_context=str(latest.get("Market_Context", "")),
        veto_flags=[str(latest.get("Veto_Flags", "")).strip()] if str(latest.get("Veto_Flags", "")).strip() else [],
        contrast_notes=[str(latest.get("Contrast_Notes", "")).strip()] if str(latest.get("Contrast_Notes", "")).strip() else [],
    )
    committee = CommitteeReview(
        label=str(latest.get("Committee_Judgment", "NEUTRAL")),
        pre_veto_label=str(latest.get("Committee_PreVeto_Judgment", "NEUTRAL")),
        confidence=float(latest.get("Committee_Confidence", 0) or 0),
        buy_agree=int(latest.get("Committee_Buy_Agree", 0) or 0),
        sell_agree=int(latest.get("Committee_Sell_Agree", 0) or 0),
        reason=str(latest.get("Committee_Judgment_Reason", "")),
        detail=str(latest.get("Committee_Judgment_Detail", "")),
        action_label=str(latest.get("Committee_Action_Label", "")),
        contrast_notes=[str(latest.get("Committee_Contrast_Notes", "")).strip()] if str(latest.get("Committee_Contrast_Notes", "")).strip() else [],
        downgrade_count=int(latest.get("Committee_Downgrade_Count", 0) or 0),
        macro_risk_off_count=int(latest.get("Committee_Macro_Risk_Off_Count", 0) or 0),
        macro_risk_on_count=int(latest.get("Committee_Macro_Risk_On_Count", 0) or 0),
        flip_guard_triggered=bool(latest.get("Committee_Flip_Guard_Triggered", False)),
    )
    objective = ObjectiveReview(
        buy_score=float(latest.get("Objective_Buy_Score", 0) or 0),
        sell_score=float(latest.get("Objective_Sell_Score", 0) or 0),
        conflict_score=float(latest.get("Objective_Conflict_Score", 0) or 0),
        advisory_label=str(latest.get("Objective_Judgment", "NEUTRAL")),
        alignment=str(latest.get("Objective_Alignment", "MIXED")),
        adjustment=str(latest.get("Objective_Adjustment", "NONE")),
        confidence=float(latest.get("Objective_Confidence", 0) or 0),
        reason=str(latest.get("Objective_Reason", "")),
        detail=str(latest.get("Objective_Detail", "")),
        action_label=str(latest.get("Objective_Action_Label", "")),
        contrast_notes=[str(latest.get("Objective_Contrast_Notes", "")).strip()] if str(latest.get("Objective_Contrast_Notes", "")).strip() else [],
    )
    decision = FinalDecision(
        label=str(latest.get("Trade_Judgment", "NEUTRAL")),
        confidence=float(latest.get("Judgment_Confidence", 0) or 0),
        action_label=str(latest.get("Action_Label", "")),
        decision_score=float(latest.get("Final_Decision_Score", latest.get("Ensemble_Score", 0)) or 0),
        reason=str(latest.get("Judgment_Reason", "")),
        detail=str(latest.get("Judgment_Detail", "")),
        pre_veto_label=str(latest.get("PreVeto_Judgment", "NEUTRAL")),
        buy_agree=int(latest.get("Buy_Agree", 0) or 0),
        sell_agree=int(latest.get("Sell_Agree", 0) or 0),
        contrast_notes=[str(latest.get("Contrast_Notes", "")).strip()] if str(latest.get("Contrast_Notes", "")).strip() else [],
        downgrade_count=int(latest.get("Downgrade_Count", 0) or 0),
        macro_risk_off_count=int(latest.get("Macro_Risk_Off_Count", 0) or 0),
        macro_risk_on_count=int(latest.get("Macro_Risk_On_Count", 0) or 0),
        flip_guard_triggered=bool(latest.get("Flip_Guard_Triggered", False)),
    )
    return EngineResult(frame=df, evidence=evidence, committee=committee, objective=objective, decision=decision)
