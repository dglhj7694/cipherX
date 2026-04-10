from __future__ import annotations

from typing import Iterable, Mapping

from config import COMBINED_SCAN_REGISTRY, SIGNAL_REGISTRY


COOPER_BUY_SIGNAL_KEYS: tuple[str, ...] = (
    "Pullback_123_Bull",
    "Setup_180_Bull",
    "Boomer_Buy",
    "Expansion_BO",
    "Expansion_Pivot_Buy",
    "Gilligans_Buy",
    "Lizard_Bull",
    "Slingshot_Bull",
)

COOPER_SELL_SIGNAL_KEYS: tuple[str, ...] = (
    "Pullback_123_Bear",
    "Setup_180_Bear",
    "Boomer_Sell",
    "Expansion_BD",
    "Expansion_Pivot_Sell",
    "Expansion_Double_Sticks",
    "Gilligans_Sell",
    "Lizard_Bear",
    "Slingshot_Bear",
)

CORE_CONFIRM_BUY_KEYS: tuple[str, ...] = (
    "UTBot_Buy",
    "Hull_Turn_Bull",
    "VuManChu_Bull",
    "VWAP_Bounce_Buy",
    "CS_Triple_Confirm_Buy",
    "CS_VuManChu_Squeeze_Buy",
    "CS_Cooper_Setup_Buy",
)

CORE_CONFIRM_SELL_KEYS: tuple[str, ...] = (
    "UTBot_Sell",
    "Hull_Turn_Bear",
    "VuManChu_Bear",
    "VWAP_Reject_Sell",
    "CS_Triple_Confirm_Sell",
    "CS_VuManChu_Squeeze_Sell",
    "CS_Cooper_Setup_Sell",
)


SIGNAL_PLAN_ITEMS: tuple[dict[str, object], ...] = (
    {
        "slug": "cooper_123_pullback",
        "title": "Jeff Cooper 1-2-3 Pullback",
        "status": "implemented",
        "registry_keys": ("Pullback_123_Bull", "Pullback_123_Bear"),
    },
    {
        "slug": "cooper_180_setup",
        "title": "Jeff Cooper 180 Setup",
        "status": "implemented",
        "registry_keys": ("Setup_180_Bull", "Setup_180_Bear"),
    },
    {
        "slug": "cooper_boomer",
        "title": "Jeff Cooper Boomer",
        "status": "implemented",
        "registry_keys": ("Boomer_Buy", "Boomer_Sell"),
    },
    {
        "slug": "cooper_expansion_breakout",
        "title": "Jeff Cooper Expansion Breakout / Breakdown",
        "status": "implemented",
        "registry_keys": ("Expansion_BO", "Expansion_BD"),
    },
    {
        "slug": "cooper_expansion_pivot",
        "title": "Jeff Cooper Expansion Pivot",
        "status": "implemented",
        "registry_keys": ("Expansion_Pivot_Buy", "Expansion_Pivot_Sell"),
    },
    {
        "slug": "cooper_expansion_double_sticks",
        "title": "Jeff Cooper Expansion Range Double Sticks",
        "status": "implemented",
        "registry_keys": ("Expansion_Double_Sticks",),
    },
    {
        "slug": "cooper_gilligans",
        "title": "Jeff Cooper Gilligan's Island",
        "status": "implemented",
        "registry_keys": ("Gilligans_Buy", "Gilligans_Sell"),
    },
    {
        "slug": "cooper_lizard",
        "title": "Jeff Cooper Lizard",
        "status": "implemented",
        "registry_keys": ("Lizard_Bull", "Lizard_Bear"),
    },
    {
        "slug": "cooper_slingshot",
        "title": "Jeff Cooper Slingshot",
        "status": "implemented",
        "registry_keys": ("Slingshot_Bull", "Slingshot_Bear"),
    },
    {
        "slug": "core_utbot",
        "title": "UT Bot",
        "status": "implemented",
        "registry_keys": ("UTBot_Buy", "UTBot_Sell"),
    },
    {
        "slug": "core_hull",
        "title": "Hull MA",
        "status": "implemented",
        "registry_keys": ("Hull_Turn_Bull", "Hull_Turn_Bear"),
    },
    {
        "slug": "core_vumanchu",
        "title": "VuManChu",
        "status": "implemented",
        "registry_keys": ("VuManChu_Bull", "VuManChu_Bear"),
    },
    {
        "slug": "core_vwap",
        "title": "VWAP / Fixed VWAP",
        "status": "partial",
        "registry_keys": ("VWAP_Bounce_Buy", "VWAP_Reject_Sell"),
        "note": "Fixed VWAP is used through context/level logic rather than a dedicated signal registry key.",
    },
)


def build_signal_plan_snapshot(
    signal_registry: Mapping[str, object] | None = None,
    combo_registry: Mapping[str, object] | None = None,
) -> dict[str, object]:
    signal_registry = signal_registry or SIGNAL_REGISTRY
    combo_registry = combo_registry or COMBINED_SCAN_REGISTRY
    items: list[dict[str, object]] = []
    counts = {"implemented": 0, "partial": 0, "deferred": 0}
    for item in SIGNAL_PLAN_ITEMS:
        keys = tuple(str(key) for key in item.get("registry_keys", ()))
        matched = [key for key in keys if key in signal_registry or key in combo_registry]
        status = str(item.get("status", "deferred"))
        if not matched:
            status = "deferred"
        counts[status] = counts.get(status, 0) + 1
        items.append(
            {
                "slug": str(item.get("slug", "")),
                "title": str(item.get("title", "")),
                "status": status,
                "registry_keys": keys,
                "matched_keys": tuple(matched),
                "note": str(item.get("note", "")),
            }
        )
    return {"counts": counts, "items": items}


def filter_present_keys(keys: Iterable[str], available_columns: Iterable[str]) -> tuple[str, ...]:
    available = {str(column) for column in available_columns}
    return tuple(key for key in keys if key in available)
