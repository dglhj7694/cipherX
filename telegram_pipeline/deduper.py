from __future__ import annotations

from typing import Any, Iterable, Mapping


def _ticker(row: Mapping[str, Any]) -> str:
    return str(dict(row or {}).get("ticker") or "").strip().upper()


def dedupe_core_sections(
    sections: Mapping[str, Iterable[Mapping[str, Any]]],
    *,
    dedupe_order: Iterable[str],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, bool]]:
    assigned: dict[str, str] = {}
    deduped: dict[str, list[dict[str, Any]]] = {}
    dedupe_applied: dict[str, bool] = {}

    for key in dedupe_order:
        unique_rows: list[dict[str, Any]] = []
        removed = 0
        for raw_row in sections.get(key) or []:
            row = dict(raw_row or {})
            ticker = _ticker(row)
            if not ticker:
                continue
            if ticker in assigned:
                removed += 1
                continue
            assigned[ticker] = key
            unique_rows.append(row)
        deduped[str(key)] = unique_rows
        dedupe_applied[str(key)] = removed > 0

    for key, raw_rows in sections.items():
        if key in deduped:
            continue
        deduped[str(key)] = [dict(row or {}) for row in (raw_rows or [])]
        dedupe_applied[str(key)] = False

    return deduped, dedupe_applied
