from __future__ import annotations

import math
import re
from typing import Any, Iterable, Mapping

from sectors import SECTOR_GROUPS

HEATMAP_METRIC_OPTIONS: dict[str, str] = {
    "Change": "chg",
    "5D": "chg_5d",
    "Vol20": "volume_ratio_20",
    "ATR": "atr_pct",
    "RS": "rs_rank_vs_index",
    "ADX": "adx",
    "Signal": "signal_count",
}

HEATMAP_ROW_FIELDS: tuple[str, ...] = (
    "ticker",
    "sector",
    "price",
    "chg",
    "chg_5d",
    "volume_ratio_20",
    "dollar_volume_20",
    "atr_pct",
    "rs_rank_vs_index",
    "adx",
    "signal_count",
    "source",
    "risk_flags",
)

_PAREN_KEY_RE = re.compile(r"\(([A-Za-z0-9_]+)\)")


def _sector_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for sector, tickers in SECTOR_GROUPS.items():
        for ticker in tickers or []:
            symbol = str(ticker or "").strip().upper()
            if symbol and symbol not in lookup:
                lookup[symbol] = str(sector or "Unclassified")
    return lookup


SECTOR_LOOKUP = _sector_lookup()


def _canonical_key(key: Any) -> str:
    text = str(key or "").strip()
    matches = _PAREN_KEY_RE.findall(text)
    if matches:
        return matches[-1].strip().lower()
    return text.strip().lower()


def normalize_heatmap_row_keys(row: Mapping[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in dict(row or {}).items():
        canonical = _canonical_key(key)
        if not canonical or canonical in normalized:
            continue
        normalized[canonical] = value
    return normalized


def _optional_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _first_number(row: Mapping[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = row.get(key)
        if value is None:
            continue
        number = _optional_float(value)
        if number is not None:
            return number
    return None


def _first_text(row: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        text = str(value or "").strip()
        if text and text.lower() not in {"nan", "none", "null", "-", "--"}:
            return text
    return ""


def _split_flags(value: Any) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        raw_items = list(value)
    else:
        raw_items = re.split(r"[+|,/]", str(value or ""))
    flags: list[str] = []
    for item in raw_items:
        text = str(item or "").strip()
        if text and text.lower() not in {"nan", "none", "null", "-", "--"} and text not in flags:
            flags.append(text)
    return flags


def _sector_for_ticker(ticker: str, fallback: str = "") -> str:
    symbol = str(ticker or "").strip().upper()
    if fallback:
        return str(fallback).strip()
    return SECTOR_LOOKUP.get(symbol, "Unclassified")


def _size_value(row: Mapping[str, Any]) -> float:
    dollar_volume = _optional_float(row.get("dollar_volume_20"))
    if dollar_volume is not None and dollar_volume > 0:
        return dollar_volume
    volume_ratio = _optional_float(row.get("volume_ratio_20"))
    if volume_ratio is not None and volume_ratio > 0:
        return max(volume_ratio, 0.1)
    return 1.0


def _signal_count(row: Mapping[str, Any]) -> float | None:
    direct = _first_number(
        row,
        "signal_count",
        "detected_signal_total_count",
        "detected_core_count",
        "membership_count",
        "qbs_membership_count",
    )
    if direct is not None:
        return direct
    combo = _optional_float(row.get("detected_combo_count")) or 0.0
    transition = _optional_float(row.get("detected_transition_count")) or 0.0
    core = _optional_float(row.get("detected_core_count")) or 0.0
    total = combo + transition + core
    return total if total > 0 else None


def _standard_row(row: Mapping[str, Any], *, source: str, fallback_sector: str = "") -> dict[str, Any] | None:
    normalized = normalize_heatmap_row_keys(row)
    ticker = _first_text(normalized, "ticker", "symbol").upper()
    if not ticker:
        return None
    sector = _sector_for_ticker(ticker, _first_text(normalized, "sector", "sector_label") or fallback_sector)
    output = {
        "ticker": ticker,
        "sector": sector,
        "price": _first_number(normalized, "price", "last", "close"),
        "chg": _first_number(normalized, "chg", "chg_pct", "change_pct", "day_change", "today_chg_pct"),
        "chg_5d": _first_number(normalized, "chg_5d", "five_day_change", "five_day_pct"),
        "volume_ratio_20": _first_number(normalized, "volume_ratio_20", "volume_ratio"),
        "dollar_volume_20": _first_number(normalized, "dollar_volume_20"),
        "atr_pct": _first_number(normalized, "atr_pct"),
        "rs_rank_vs_index": _first_number(normalized, "rs_rank_vs_index"),
        "adx": _first_number(normalized, "adx"),
        "signal_count": _signal_count(normalized),
        "source": source,
        "risk_flags": _split_flags(normalized.get("risk_flags") or normalized.get("qbs_risk_flags") or normalized.get("board_risk")),
    }
    output["size"] = _size_value(output)
    return output


def _rows_from_scanner(scanner_rows: Iterable[Mapping[str, Any]], max_rows: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in scanner_rows or []:
        row = _standard_row(raw, source="scanner")
        if row:
            rows.append(row)
        if len(rows) >= max_rows:
            break
    return rows


def _rows_from_telegram(telegram_payload: Mapping[str, Any], max_rows: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for section in list(dict(telegram_payload or {}).get("sections") or []):
        section_dict = dict(section or {})
        section_key = str(section_dict.get("key") or "telegram").strip() or "telegram"
        for item in list(section_dict.get("items") or section_dict.get("detail_items") or []):
            item_dict = dict(item or {})
            flags = dict(item_dict.get("source_flags") or {})
            merged = {**flags, **item_dict}
            row = _standard_row(merged, source=f"telegram:{section_key}")
            if not row or row["ticker"] in seen:
                continue
            seen.add(row["ticker"])
            rows.append(row)
            if len(rows) >= max_rows:
                return rows
    return rows


def _rows_from_market_payload(market_payload: Mapping[str, Any], max_rows: int) -> list[dict[str, Any]]:
    payload = dict(market_payload or {})
    report = dict(payload.get("briefing_report") or {})
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    mover_sources = [
        *list(payload.get("gainers_detail") or []),
        *list(payload.get("losers_detail") or []),
        *list(dict(report.get("movers") or {}).get("gainers") or []),
        *list(dict(report.get("movers") or {}).get("losers") or []),
        *list(dict(report.get("core_movers") or {}).get("gainers") or []),
        *list(dict(report.get("core_movers") or {}).get("losers") or []),
    ]
    for item in mover_sources:
        row = _standard_row(dict(item or {}), source="market:movers")
        if not row or row["ticker"] in seen:
            continue
        seen.add(row["ticker"])
        rows.append(row)
        if len(rows) >= max_rows:
            return rows

    for item in list(report.get("sector_rank") or []):
        item_dict = dict(item or {})
        symbol = _first_text(item_dict, "symbol", "ticker").upper()
        label = _first_text(item_dict, "label", "name")
        if not symbol or symbol in seen:
            continue
        row = _standard_row({**item_dict, "ticker": symbol, "sector": label or symbol}, source="market:sector_rank")
        if row:
            seen.add(symbol)
            rows.append(row)
        if len(rows) >= max_rows:
            return rows
    return rows


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    def top_by(key: str, *, reverse: bool = True, limit: int = 8) -> list[dict[str, Any]]:
        sortable = [row for row in rows if _optional_float(row.get(key)) is not None]
        sortable.sort(key=lambda row: float(row.get(key) or 0.0), reverse=reverse)
        return sortable[:limit]

    sectors = sorted({str(row.get("sector") or "Unclassified") for row in rows})
    return {
        "ticker_count": len(rows),
        "sector_count": len(sectors),
        "top_gain": top_by("chg", reverse=True),
        "top_decline": top_by("chg", reverse=False),
        "top_volume": top_by("volume_ratio_20", reverse=True),
        "top_volatility": top_by("atr_pct", reverse=True),
    }


def build_market_heatmap_payload(
    scanner_rows: Iterable[Mapping[str, Any]] | None,
    telegram_payload: Mapping[str, Any] | None,
    market_payload: Mapping[str, Any] | None,
    max_rows: int = 250,
) -> dict[str, Any]:
    limit = max(1, int(max_rows or 250))
    rows = _rows_from_scanner(scanner_rows or [], limit)
    source = "scanner"
    if not rows:
        rows = _rows_from_telegram(dict(telegram_payload or {}), limit)
        source = "telegram"
    if not rows:
        rows = _rows_from_market_payload(dict(market_payload or {}), limit)
        source = "market"
    if not rows:
        source = "empty"

    return {
        "source": source,
        "rows": rows,
        "row_count": len(rows),
        "metric_options": dict(HEATMAP_METRIC_OPTIONS),
        "fields": list(HEATMAP_ROW_FIELDS),
        "summary": _summary(rows),
    }
