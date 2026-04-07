from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from domain import AnalysisRequest, ScannerRequest, ScannerResultRow
from services.analysis_service import AnalysisService


class ScannerWorkflow:
    def __init__(self, analysis_service: AnalysisService | None = None):
        self.analysis_service = analysis_service or AnalysisService()

    def run(self, request: ScannerRequest, *, row_builder):
        results: list[dict] = []
        if not request.tickers:
            return results
        with ThreadPoolExecutor(max_workers=min(max(1, request.max_workers), len(request.tickers))) as executor:
            futures = {
                executor.submit(
                    self.analysis_service.analyze,
                    AnalysisRequest(ticker=ticker, chart_days=request.chart_days, refresh=False),
                    row_builder["prompt_builder"],
                ): ticker
                for ticker in request.tickers
            }
            for future in as_completed(futures):
                ticker = futures[future]
                artifacts = future.result()
                if not artifacts.meta:
                    continue
                row = row_builder["build_row"](ticker, artifacts)
                if isinstance(row, ScannerResultRow):
                    results.append(row.to_dict())
                elif isinstance(row, dict):
                    results.append(row)
        return results
