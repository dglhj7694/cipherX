from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AnalysisRequest:
    ticker: str
    chart_days: int
    refresh: bool = False
    bias_mode: str = "equity_long_bias"


@dataclass
class AnalysisViewModel:
    ticker: str
    price: float
    change_pct: float
    decision_label: str
    action_label: str
    confidence: float
    ensemble_score: float
    context_label: str
    leading_verdict: str
    lagging_verdict: str
    combined_scans: list[dict[str, Any]] = field(default_factory=list)
    top_strategy: dict[str, Any] | None = None
    strategy_summary: dict[str, Any] = field(default_factory=dict)
    ai_signal_assisted: dict[str, Any] | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "AnalysisViewModel":
        payload = dict(payload or {})
        known_keys = {
            "ticker",
            "price",
            "price_change_pct",
            "judgment",
            "action_label",
            "confidence",
            "ensemble_score",
            "context_label",
            "leading_verdict",
            "lagging_verdict",
            "combined_scans",
            "top_strategy",
            "strategy_summary",
            "ai_signal_assisted",
        }
        extras = {key: value for key, value in payload.items() if key not in known_keys}
        return cls(
            ticker=str(payload.get("ticker", "")),
            price=float(payload.get("price", 0) or 0),
            change_pct=float(payload.get("price_change_pct", 0) or 0),
            decision_label=str(payload.get("judgment", "NEUTRAL")),
            action_label=str(payload.get("action_label", "")),
            confidence=float(payload.get("confidence", 0) or 0),
            ensemble_score=float(payload.get("ensemble_score", 0) or 0),
            context_label=str(payload.get("context_label", "")),
            leading_verdict=str(payload.get("leading_verdict", "")),
            lagging_verdict=str(payload.get("lagging_verdict", "")),
            combined_scans=list(payload.get("combined_scans") or []),
            top_strategy=dict(payload.get("top_strategy") or {}) if payload.get("top_strategy") else None,
            strategy_summary=dict(payload.get("strategy_summary") or {}),
            ai_signal_assisted=dict(payload.get("ai_signal_assisted") or {}) if payload.get("ai_signal_assisted") else None,
            extras=extras,
        )

    def to_dict(self) -> dict[str, Any]:
        payload = dict(self.extras)
        payload.update(
            {
                "ticker": self.ticker,
                "price": self.price,
                "price_change_pct": self.change_pct,
                "judgment": self.decision_label,
                "action_label": self.action_label,
                "confidence": self.confidence,
                "ensemble_score": self.ensemble_score,
                "context_label": self.context_label,
                "leading_verdict": self.leading_verdict,
                "lagging_verdict": self.lagging_verdict,
                "combined_scans": self.combined_scans,
                "top_strategy": self.top_strategy,
                "strategy_summary": self.strategy_summary,
                "ai_signal_assisted": self.ai_signal_assisted,
            }
        )
        return payload


@dataclass
class AnalysisResponse:
    chart_json: str | None
    meta: AnalysisViewModel | None
    prompt_text: str | None
    audit: dict[str, Any] | None
    ai_result: dict[str, Any] | None = None


@dataclass
class ScannerRequest:
    tickers: list[str]
    chart_days: int
    max_workers: int = 8


@dataclass
class ScannerResultRow:
    ticker: str
    decision: str
    confidence: float
    ensemble_score: float
    scan_score: float
    top_strategy: dict[str, Any] | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = dict(self.extras)
        payload.update(
            {
                "ticker": self.ticker,
                "decision": self.decision,
                "confidence": self.confidence,
                "ensemble_score": self.ensemble_score,
                "scan_score": self.scan_score,
                "top_strategy": self.top_strategy,
            }
        )
        return payload
