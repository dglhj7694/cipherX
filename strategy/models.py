from __future__ import annotations

from dataclasses import asdict, dataclass, field

from .utils import round_or_none


VISIBLE_STATUSES = {
    "ACTIVE",
    "CONFIRMING",
    "TRIGGER_WAIT",
    "READY",
    "INTEREST",
    "LONG_ENTRY",
    "LONG_ALIGNED",
    "LONG_WAIT",
    "SHORT_ENTRY",
    "SHORT_ALIGNED",
    "SHORT_WAIT",
    "EXIT_WARNING",
}


@dataclass(frozen=True)
class StrategyDefinition:
    id: str
    label: str
    category: str
    direction: str
    family: str
    ui_label: str | None = None
    presentation_type: str = "strategy"
    implementation_level: str = "implemented"
    deterministic: bool = True


@dataclass
class StrategyResult:
    id: str
    label: str
    canonical_label: str
    direction: str
    category: str
    score: float
    status: str
    phase: str
    entry_hint: str
    setup_score: float
    trigger_score: float
    risk_score: float
    presentation_type: str = "strategy"
    implementation_level: str = "implemented"
    deterministic: bool = True
    entry_reference_type: str = "ENTRY_PRICE"
    entry_reference_text: str = ""
    entry_price: float | None = None
    interest_low: float | None = None
    interest_high: float | None = None
    confirmation_level: float | None = None
    invalidation_level: float | None = None
    matched_conditions: list[str] = field(default_factory=list)
    missing_conditions: list[str] = field(default_factory=list)
    failed_conditions: list[str] = field(default_factory=list)
    stop_loss: float | None = None
    target_1: float | None = None
    target_2: float | None = None
    rr: float | None = None
    conflict_reasons: list[str] = field(default_factory=list)
    explanation: str = ""
    last5_change: list[str] = field(default_factory=list)
    invalidation_text: str = ""
    note: str = ""

    def to_dict(self) -> dict:
        payload = asdict(self)
        for key in (
            "score",
            "entry_price",
            "interest_low",
            "interest_high",
            "confirmation_level",
            "invalidation_level",
            "setup_score",
            "trigger_score",
            "risk_score",
            "stop_loss",
            "target_1",
            "target_2",
            "rr",
        ):
            payload[key] = round_or_none(payload.get(key))
        return payload


@dataclass
class StrategySummary:
    active_count: int
    visible_count: int
    bullish_count: int
    bearish_count: int
    long_short_bias: str
    conflict_level: str
    top_strategy: dict | None
    secondary_strategies: list[dict] = field(default_factory=list)
    hidden_invalid_count: int = 0
    dominant_reasons: list[str] = field(default_factory=list)
    opposing_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)
