from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from audit import build_audit_payload
from chart import build_chart, build_metadata, serialize_chart_figure
from domain import AnalysisRequest, AnalysisViewModel
from strategy import build_strategy_payload
from utils import compute_and_cache


@dataclass
class AnalysisArtifacts:
    data_frame: Any | None
    display_frame: Any | None
    meta: AnalysisViewModel | None
    prompt_text: str | None
    chart_json: str | None
    audit: dict[str, Any] | None


class AnalysisService:
    def analyze(self, request: AnalysisRequest, prompt_builder) -> AnalysisArtifacts:
        cache_buster = int(time.time()) if request.refresh else None
        df = compute_and_cache(request.ticker, cache_buster, bias_mode=request.bias_mode)
        if df is None or getattr(df, "empty", True) or len(df) < 50:
            return AnalysisArtifacts(None, None, None, "데이터 부족", None, None)

        dc = df.dropna(subset=["WT1", "WT2"]).tail(request.chart_days).copy()
        if dc.empty:
            return AnalysisArtifacts(df, dc, None, "차트 데이터 부족", None, None)

        meta_payload = build_metadata(dc, request.ticker)
        meta = AnalysisViewModel.from_payload(meta_payload)
        audit = build_audit_payload(
            df,
            ticker=request.ticker,
            lookback_bars=max(request.chart_days, 252),
            bias_mode=request.bias_mode,
        )
        prompt_text = prompt_builder(dc, meta.to_dict())
        chart_json = serialize_chart_figure(build_chart(dc, request.ticker))
        return AnalysisArtifacts(df, dc, meta, prompt_text, chart_json, audit)

    def build_strategy_payload(self, display_frame):
        return build_strategy_payload(display_frame)
