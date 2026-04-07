from __future__ import annotations

from domain import AnalysisViewModel


def build_analysis_view_model(payload: dict) -> AnalysisViewModel:
    return AnalysisViewModel.from_payload(payload)
