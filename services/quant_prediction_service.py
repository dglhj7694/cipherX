from __future__ import annotations

import math
import re
from typing import Any, Iterable, Mapping

from sectors import SECTOR_GROUPS
from services.market_heatmap_service import normalize_heatmap_row_keys

QUANT_PREDICTION_MODEL_VERSION = "rule-v1"
QUANT_PREDICTION_TARGET = "next_session_direction"
QUANT_PREDICTION_FIELDS: tuple[str, ...] = (
    "ticker",
    "sector",
    "price",
    "prediction_label",
    "up_probability",
    "down_probability",
    "confidence",
    "chg",
    "chg_5d",
    "ret20_pct",
    "volume_ratio_20",
    "atr_pct",
    "rs_rank_vs_index",
    "adx",
    "dist_sma20_pct",
    "drawdown_from_52w_high_pct",
    "prediction_reason",
    "risk_flags",
    "source",
)

RISK_TOKEN_PENALTIES: tuple[tuple[str, int, str], ...] = (
    ("bearish_gap_failure", 14, "gap failure"),
    ("gap_failure", 14, "gap failure"),
    ("sell", 12, "sell signal"),
    ("breakdown", 10, "breakdown risk"),
    ("thin", 8, "thin liquidity"),
    ("low_volume", 7, "light volume"),
    ("extended_day", 5, "extended day"),
    ("extended_5d", 5, "extended 5D"),
    ("hot_zscore", 5, "hot z-score"),
    ("overheat", 5, "overheat"),
)


def _sector_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for sector, tickers in SECTOR_GROUPS.items():
        for ticker in tickers or []:
            symbol = str(ticker or "").strip().upper()
            if symbol and symbol not in lookup:
                lookup[symbol] = str(sector or "Unclassified")
    return lookup


SECTOR_LOOKUP = _sector_lookup()


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
        number = _optional_float(row.get(key))
        if number is not None:
            return number
    return None


def _first_text(row: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        text = str(row.get(key) or "").strip()
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


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _sector_for_ticker(ticker: str, fallback: str = "") -> str:
    if fallback:
        return str(fallback).strip()
    return SECTOR_LOOKUP.get(str(ticker or "").strip().upper(), "Unclassified")


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


def _normalize_prediction_input(row: Mapping[str, Any], *, source: str, fallback_sector: str = "") -> dict[str, Any] | None:
    normalized = normalize_heatmap_row_keys(row)
    ticker = _first_text(normalized, "ticker", "symbol").upper()
    if not ticker:
        return None
    risk_flags = _split_flags(
        normalized.get("risk_flags")
        or normalized.get("qbs_risk_flags")
        or normalized.get("board_risk")
        or normalized.get("warning_flags")
    )
    return {
        "ticker": ticker,
        "sector": _sector_for_ticker(ticker, _first_text(normalized, "sector", "sector_label") or fallback_sector),
        "price": _first_number(normalized, "price", "last", "close"),
        "chg": _first_number(normalized, "chg", "chg_pct", "change_pct", "day_change", "today_chg_pct"),
        "chg_5d": _first_number(normalized, "chg_5d", "five_day_change", "five_day_pct"),
        "ret20_pct": _first_number(normalized, "ret20_pct", "ret_1m_pct", "one_month_pct"),
        "ret20_percentile": _first_number(normalized, "ret20_percentile"),
        "volume_ratio_20": _first_number(normalized, "volume_ratio_20", "volume_ratio"),
        "dollar_volume_20": _first_number(normalized, "dollar_volume_20"),
        "atr_pct": _first_number(normalized, "atr_pct"),
        "rs_rank_vs_index": _first_number(normalized, "rs_rank_vs_index", "rs"),
        "adx": _first_number(normalized, "adx"),
        "dist_sma20_pct": _first_number(normalized, "dist_sma20_pct", "ma20_dist_pct"),
        "drawdown_from_52w_high_pct": _first_number(normalized, "drawdown_from_52w_high_pct", "high_pos_pct"),
        "breakout_dist_20d_high_pct": _first_number(normalized, "breakout_dist_20d_high_pct"),
        "signal_count": _signal_count(normalized),
        "risk_flags": risk_flags,
        "source": source,
    }


def _risk_penalty(risk_flags: Iterable[str]) -> tuple[int, list[str]]:
    penalty = 0
    reasons: list[str] = []
    risk_text = " ".join(str(flag or "").lower() for flag in risk_flags)
    for token, points, label in RISK_TOKEN_PENALTIES:
        if token in risk_text:
            penalty += points
            if label not in reasons:
                reasons.append(label)
    return penalty, reasons


def _score_prediction(row: Mapping[str, Any]) -> dict[str, Any]:
    points = 0.0
    evidence = 0
    reasons: list[str] = []
    risks: list[str] = list(row.get("risk_flags") or [])

    def add(points_delta: float, reason: str) -> None:
        nonlocal points, evidence
        points += points_delta
        evidence += 1
        if reason and reason not in reasons:
            reasons.append(reason)

    rs = _optional_float(row.get("rs_rank_vs_index"))
    if rs is not None:
        if rs >= 85:
            add(12, "RS 85+")
        elif rs >= 70:
            add(8, "RS 70+")
        elif rs >= 55:
            add(4, "RS improving")
        elif rs < 45:
            add(-7, "weak RS")

    ret20 = _optional_float(row.get("ret20_pct"))
    if ret20 is not None:
        if ret20 >= 15:
            add(8, "20D momentum")
        elif ret20 >= 5:
            add(4, "positive 20D")
        elif ret20 <= -8:
            add(-8, "negative 20D")

    ret20_percentile = _optional_float(row.get("ret20_percentile"))
    if ret20_percentile is not None:
        if ret20_percentile >= 90:
            add(6, "20D percentile 90+")
        elif ret20_percentile <= 35:
            add(-5, "low 20D percentile")

    chg_5d = _optional_float(row.get("chg_5d"))
    if chg_5d is not None:
        if 4 <= chg_5d <= 18:
            add(5, "5D momentum")
        elif chg_5d > 28:
            add(-4, "5D extended")
            risks.append("extended_5d")
        elif chg_5d <= -6:
            add(-6, "5D weakness")

    chg = _optional_float(row.get("chg"))
    if chg is not None:
        if 0.5 <= chg <= 8:
            add(4, "positive session")
        elif chg > 14:
            add(-4, "day extended")
            risks.append("extended_day")
        elif chg <= -3:
            add(-7, "negative session")

    adx = _optional_float(row.get("adx"))
    if adx is not None:
        if adx >= 35:
            add(8, "ADX strong")
        elif adx >= 25:
            add(6, "ADX trend")
        elif adx >= 18:
            add(3, "ADX building")
        elif adx < 12:
            add(-4, "weak ADX")

    volume = _optional_float(row.get("volume_ratio_20"))
    if volume is not None:
        if volume >= 1.5:
            add(8, "volume expansion")
        elif volume >= 1.0:
            add(4, "volume support")
        elif volume < 0.7:
            add(-5, "light volume")

    atr = _optional_float(row.get("atr_pct"))
    if atr is not None:
        if 3 <= atr <= 12:
            add(5, "tradeable ATR")
        elif 1.5 <= atr < 3:
            add(1, "moderate ATR")
        elif atr < 1.5:
            add(-4, "low volatility")
        elif atr > 18:
            add(-6, "extreme ATR")
            risks.append("extreme_atr")

    ma20 = _optional_float(row.get("dist_sma20_pct"))
    if ma20 is not None:
        if -2 <= ma20 <= 10:
            add(6, "MA20 zone")
        elif 10 < ma20 <= 25:
            add(2, "above MA20")
        elif ma20 > 25:
            add(-8, "MA20 extended")
            risks.append("ma20_extended")
        elif ma20 < -8:
            add(-7, "below MA20")

    high_pos = _optional_float(row.get("drawdown_from_52w_high_pct"))
    if high_pos is not None:
        if -8 <= high_pos <= 0:
            add(6, "near 52W high")
        elif -15 <= high_pos < -8:
            add(2, "within 52W range")
        elif high_pos < -28:
            add(-5, "far from high")

    high_20d = _optional_float(row.get("breakout_dist_20d_high_pct"))
    if high_20d is not None:
        if -4 <= high_20d <= 1:
            add(5, "near 20D high")
        elif high_20d < -12:
            add(-4, "far from 20D high")

    signal_count = _optional_float(row.get("signal_count"))
    if signal_count is not None and signal_count > 0:
        add(min(5.0, signal_count), "signal cluster")

    risk_points, risk_reasons = _risk_penalty(risks)
    if risk_points:
        points -= risk_points
        for reason in risk_reasons:
            if reason not in reasons:
                reasons.append(reason)

    up_probability = round(_clamp(50.0 + points, 5.0, 95.0), 1)
    down_probability = round(100.0 - up_probability, 1)
    confidence = round(_clamp(abs(up_probability - 50.0) * 1.35 + evidence * 3.0 - len(risk_reasons) * 2.0, 8.0, 92.0), 1)
    if up_probability >= 62:
        label = "UP"
    elif up_probability <= 42:
        label = "DOWN"
    else:
        label = "NEUTRAL"

    return {
        "prediction_label": label,
        "up_probability": up_probability,
        "down_probability": down_probability,
        "confidence": confidence,
        "prediction_reason": reasons[:5],
        "risk_flags": risks[:6],
        "quant_score": round(50.0 + points, 2),
    }


def _with_prediction(row: Mapping[str, Any]) -> dict[str, Any]:
    base = dict(row)
    prediction = _score_prediction(base)
    base.update(prediction)
    return base


def _rows_from_scanner(scanner_rows: Iterable[Mapping[str, Any]], max_rows: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in scanner_rows or []:
        row = _normalize_prediction_input(raw, source="scanner")
        if not row or row["ticker"] in seen:
            continue
        seen.add(row["ticker"])
        rows.append(_with_prediction(row))
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
            row = _normalize_prediction_input(merged, source=f"telegram:{section_key}")
            if not row or row["ticker"] in seen:
                continue
            seen.add(row["ticker"])
            rows.append(_with_prediction(row))
            if len(rows) >= max_rows:
                return rows
    return rows


def _rows_from_market_payload(market_payload: Mapping[str, Any], max_rows: int) -> list[dict[str, Any]]:
    payload = dict(market_payload or {})
    report = dict(payload.get("briefing_report") or {})
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    sources = [
        *list(payload.get("gainers_detail") or []),
        *list(payload.get("losers_detail") or []),
        *list(dict(report.get("movers") or {}).get("gainers") or []),
        *list(dict(report.get("movers") or {}).get("losers") or []),
        *list(dict(report.get("core_movers") or {}).get("gainers") or []),
        *list(dict(report.get("core_movers") or {}).get("losers") or []),
    ]
    for item in sources:
        row = _normalize_prediction_input(dict(item or {}), source="market:movers")
        if not row or row["ticker"] in seen:
            continue
        seen.add(row["ticker"])
        rows.append(_with_prediction(row))
        if len(rows) >= max_rows:
            return rows

    for item in list(report.get("sector_rank") or []):
        item_dict = dict(item or {})
        symbol = _first_text(item_dict, "symbol", "ticker").upper()
        label = _first_text(item_dict, "label", "name")
        if not symbol or symbol in seen:
            continue
        row = _normalize_prediction_input({**item_dict, "ticker": symbol, "sector": label or symbol}, source="market:sector_rank")
        if row:
            seen.add(symbol)
            rows.append(_with_prediction(row))
        if len(rows) >= max_rows:
            return rows
    return rows


def _sort_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            float(row.get("up_probability") or 0.0),
            float(row.get("confidence") or 0.0),
            float(row.get("volume_ratio_20") or 0.0),
            float(row.get("atr_pct") or 0.0),
        ),
        reverse=True,
    )


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    up_rows = [row for row in rows if row.get("prediction_label") == "UP"]
    down_rows = [row for row in rows if row.get("prediction_label") == "DOWN"]
    neutral_rows = [row for row in rows if row.get("prediction_label") == "NEUTRAL"]
    avg_up = sum(float(row.get("up_probability") or 0.0) for row in rows) / len(rows) if rows else 0.0
    return {
        "ticker_count": len(rows),
        "up_count": len(up_rows),
        "neutral_count": len(neutral_rows),
        "down_count": len(down_rows),
        "average_up_probability": round(avg_up, 1),
        "top_up": rows[:10],
    }


def build_quant_prediction_payload(
    scanner_rows: Iterable[Mapping[str, Any]] | None,
    telegram_payload: Mapping[str, Any] | None,
    market_payload: Mapping[str, Any] | None,
    max_rows: int = 80,
) -> dict[str, Any]:
    limit = max(1, int(max_rows or 80))
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

    rows = _sort_rows(rows)[:limit]
    return {
        "source": source,
        "rows": rows,
        "row_count": len(rows),
        "fields": list(QUANT_PREDICTION_FIELDS),
        "model_version": QUANT_PREDICTION_MODEL_VERSION,
        "target": QUANT_PREDICTION_TARGET,
        "summary": _summary(rows),
        "note": "Rule-based v1. Uses price, volume, volatility, trend, relative strength, and risk flags only; no LLM/news input.",
    }
