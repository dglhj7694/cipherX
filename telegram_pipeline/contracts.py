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
    tier: str
    label: str
    reason: str
    source_flags: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TelegramSection:
    key: str
    title: str
    summary_items: list[TelegramCandidate] = field(default_factory=list)
    detail_items: list[TelegramCandidate] = field(default_factory=list)
    sent_count: int = 0
    quality_floor: str = ""
    dedupe_applied: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["summary_items"] = [item.to_dict() for item in self.summary_items]
        payload["detail_items"] = [item.to_dict() for item in self.detail_items]
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
