from __future__ import annotations

from domain import AnalysisRequest, AnalysisResponse
from services.analysis_service import AnalysisService


class AnalysisWorkflow:
    def __init__(self, analysis_service: AnalysisService | None = None):
        self.analysis_service = analysis_service or AnalysisService()

    def run(self, request: AnalysisRequest, *, prompt_builder):
        artifacts = self.analysis_service.analyze(request, prompt_builder)
        return AnalysisResponse(
            chart_json=artifacts.chart_json,
            meta=artifacts.meta,
            prompt_text=artifacts.prompt_text,
            audit=artifacts.audit,
            ai_result=None,
        )
