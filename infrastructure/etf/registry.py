from __future__ import annotations

from .base import HoldingsPayload, HoldingsProvider


class HoldingsProviderRegistry:
    def __init__(self, providers: list[HoldingsProvider], fallback: HoldingsProvider | None = None):
        self.providers = list(providers)
        self.fallback = fallback

    def fetch(self, symbol: str) -> HoldingsPayload:
        normalized = str(symbol or "").strip().upper()
        if not normalized:
            return HoldingsPayload(symbol="", tickers=[], error="ETF 심볼이 비어 있습니다.")

        last_payload = HoldingsPayload(symbol=normalized)
        for provider in self.providers:
            if not provider.supports(normalized):
                continue
            payload = provider.fetch(normalized)
            if payload.tickers:
                return payload
            if payload.error or payload.note:
                last_payload = payload

        if self.fallback and self.fallback.supports(normalized):
            payload = self.fallback.fetch(normalized)
            if payload.tickers or (not last_payload.error and not last_payload.note):
                return payload
        return last_payload
