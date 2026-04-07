from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Mapping, Protocol


@dataclass
class HoldingsPayload:
    symbol: str
    tickers: list[str] = field(default_factory=list)
    note: str = ""
    error: str = ""
    as_of: str = ""

    @classmethod
    def from_value(cls, value, *, symbol: str) -> "HoldingsPayload":
        if isinstance(value, cls):
            return value
        if isinstance(value, Mapping):
            return cls(
                symbol=str(value.get("symbol") or symbol).strip().upper(),
                tickers=[str(item).strip().upper() for item in (value.get("tickers") or []) if str(item).strip()],
                note=str(value.get("note") or ""),
                error=str(value.get("error") or ""),
                as_of=str(value.get("as_of") or ""),
            )
        return cls(symbol=symbol)

    def to_dict(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "tickers": list(self.tickers),
            "note": self.note,
            "error": self.error,
            "as_of": self.as_of,
        }


class HoldingsProvider(Protocol):
    def supports(self, symbol: str) -> bool: ...
    def fetch(self, symbol: str) -> HoldingsPayload: ...


class FunctionHoldingsProvider:
    def __init__(self, *, supported_symbols: set[str] | None = None, fetcher: Callable[[str], object]):
        self.supported_symbols = {str(item).strip().upper() for item in (supported_symbols or set()) if str(item).strip()}
        self.fetcher = fetcher

    def supports(self, symbol: str) -> bool:
        normalized = str(symbol or "").strip().upper()
        if not normalized:
            return False
        if not self.supported_symbols:
            return True
        return normalized in self.supported_symbols

    def fetch(self, symbol: str) -> HoldingsPayload:
        normalized = str(symbol or "").strip().upper()
        return HoldingsPayload.from_value(self.fetcher(normalized), symbol=normalized)
