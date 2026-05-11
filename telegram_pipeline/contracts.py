from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class TelegramCandidate:
    ticker: str
    price: float | None
    chg_value: float | None
    chg_pct: float | None
    volume_ratio_20: float | None
    section_key: str
    rank: int
    label: str
    reason: str
    source_flags: dict[str, Any] = field(default_factory=dict)
    qbs_score: float | None = None
    bucket: str = ""
    tags: list[str] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)
    chg_5d: float | None = None
    rsi: float | None = None
    ma20_dist_pct: float | None = None
    ret_1m_pct: float | None = None
    ret_1y_pct: float | None = None
    high_pos_pct: float | None = None
    status_tags: list[str] = field(default_factory=list)
    status: str = ""
    pul_score: float | None = None
    early_reversal_score: float | None = None
    reversal_type: str = ""
    reversal_phase: str = ""
    entry_type: str = ""
    technical_buy_score: float | None = None
    technical_buy_signal_count: int = 0
    technical_buy_hits: list[str] = field(default_factory=list)
    technical_buy_bucket: str = ""
    technical_buy_reason: str = ""
    technical_buy_risk_flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TelegramSection:
    key: str
    title: str
    items: list[TelegramCandidate] = field(default_factory=list)
    item_count: int = 0
    quality_floor: str = ""
    ranked: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["items"] = [item.to_dict() for item in self.items]
        return payload


@dataclass
class TelegramDigest:
    version: str
    scan_mode: str
    run_stamp: str
    market_date: str
    generated_at: str
    section_order: list[str]
    sections: list[TelegramSection] = field(default_factory=list)
    briefing_refs: dict[str, Any] = field(default_factory=dict)
    scan_label: str = ""
    universe_count: int = 0
    result_count: int = 0
    skip_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["sections"] = [section.to_dict() for section in self.sections]
        return payload

    def section_map(self) -> dict[str, TelegramSection]:
        return {section.key: section for section in self.sections}
