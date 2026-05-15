from __future__ import annotations

import math
from datetime import date, datetime
from typing import Any, Iterable, Mapping

from .aggressive_next_day_ranker import (
    AGGRESSIVE_FIVE_DAY_TOP_LIMIT,
    AGGRESSIVE_NEXT_DAY_LIMIT,
    AGGRESSIVE_NEXT_DAY_QUALITY_FLOORS,
    AGGRESSIVE_NEXT_DAY_SECTION_KEYS,
    AGGRESSIVE_NEXT_DAY_SECTION_TITLES,
    select_aggressive_next_day_sections,
)
from .contracts import TelegramCandidate, TelegramDigest, TelegramSection
from .early_reversal_ranker import (
    EARLY_REVERSAL_KEY,
    EARLY_REVERSAL_LIMIT,
    EARLY_REVERSAL_QUALITY_FLOOR,
    EARLY_REVERSAL_SECTION_TITLE,
    build_early_reversal_section,
)
from .final_buy_ranker import (
    QBS_BUY_NOW_KEY,
    QBS_CHASE_WATCH_KEY,
    QBS_OUTPUT_KEYS,
    QBS_OUTPUT_LIMIT,
    QBS_OUTPUT_LIMITS,
    QBS_PULLBACK_WAIT_KEY,
    build_final_buy_sections,
)
from .hull_buy_turn_ranker import (
    HULL_BUY_TURN_KEY,
    HULL_BUY_TURN_QUALITY_FLOOR,
    HULL_BUY_TURN_SECTION_TITLE,
    select_hull_buy_turn_rows,
)
from .rankers import (
    is_truthy,
    safe_float,
    same_day_buy_turn_count,
    same_day_hull_buy_turn,
    same_day_hull_sell_turn,
    same_day_sell_turn_count,
    same_day_utbot_buy_turn,
    same_day_utbot_sell_turn,
    same_session_buy_turn,
    same_session_sell_turn,
)
from .selectors import (
    BOARD_MANDATORY_SECTION_KEYS,
    BOARD_QUALITY_FLOORS,
    BOARD_SECTION_LIMIT,
    BOARD_SECTION_ORDER,
    BOARD_SECTION_TITLES,
    CORE_QUALITY_FLOORS,
    FIVE_DAY_TOP_LIMIT,
    STEADY_WINNER_QUALITY_FLOOR,
    STEADY_WINNER_SECTION_KEY,
    STEADY_WINNER_SECTION_TITLE,
    select_post_close_sections,
    select_post_close_board_sections,
)
from .startup9_confirm_ranker import (
    STARTUP9_CONFIRM_KEY,
    STARTUP9_CONFIRM_LIMIT,
    STARTUP9_CONFIRM_QUALITY_FLOOR,
    STARTUP9_CONFIRM_TITLE,
    annotate_rows_with_startup9_confirm,
    select_startup9_confirm_rows,
)
from .technical_buy_signal_ranker import (
    TECHNICAL_BUY_CLUSTER_KEY,
    TECHNICAL_BUY_CLUSTER_LIMIT,
    TECHNICAL_BUY_CLUSTER_QUALITY_FLOOR,
    TECHNICAL_BUY_CLUSTER_TITLE,
    select_technical_buy_rows,
)

QBS_SECTION_TITLES: dict[str, str] = {
    QBS_BUY_NOW_KEY: f"오늘 매수 최종 후보 Top {QBS_OUTPUT_LIMIT}",
    QBS_CHASE_WATCH_KEY: f"강하지만 추격주의 Top {QBS_OUTPUT_LIMITS[QBS_CHASE_WATCH_KEY]}",
    QBS_PULLBACK_WAIT_KEY: f"눌림 대기 후보 Top {QBS_OUTPUT_LIMITS[QBS_PULLBACK_WAIT_KEY]}",
}

QBS_QUALITY_FLOORS: dict[str, str] = {
    QBS_BUY_NOW_KEY: "QBS>=50 + final/buy confluence + no hard risk + not chase extended",
    QBS_CHASE_WATCH_KEY: "QBS>=40 + extended move / 52W / 5D chase risk",
    QBS_PULLBACK_WAIT_KEY: "QBS>=25 + pullback reentry + no hard risk",
}

QBS_DISPLAY_NUMBERS: dict[str, str] = {
    QBS_BUY_NOW_KEY: "0",
    QBS_CHASE_WATCH_KEY: "0-1",
    QBS_PULLBACK_WAIT_KEY: "0-2",
}

BOARD_SECTION_KEYS = set(BOARD_SECTION_ORDER)
FIVE_DAY_TOP_SECTION_KEY = "five_day_top"
STEADY_WINNER_DISPLAY_NUMBER = "0-3"
EARLY_REVERSAL_DISPLAY_NUMBER = "0-4"
HULL_BUY_TURN_DISPLAY_NUMBER = "0-5"
STARTUP9_CONFIRM_DISPLAY_NUMBER = "1"
TECHNICAL_BUY_DISPLAY_NUMBER = "2"
BOARD_DISPLAY_NUMBERS: dict[str, str] = {
    section_key: str(index)
    for index, section_key in enumerate(BOARD_SECTION_ORDER, start=4)
}
FIVE_DAY_TOP_DISPLAY_NUMBER = "13"
AGGRESSIVE_SECTION_KEYS = set(AGGRESSIVE_NEXT_DAY_SECTION_KEYS)


def _signed(value: Any, decimals: int = 2) -> str:
    try:
        return f"{float(value):+.{decimals}f}"
    except (TypeError, ValueError):
        return "--"


def _ratio(value: Any, decimals: int = 2) -> str:
    try:
        return f"x{float(value):.{decimals}f}"
    except (TypeError, ValueError):
        return "x--"


def _number(value: Any, decimals: int = 1) -> str:
    try:
        return f"{float(value):.{decimals}f}"
    except (TypeError, ValueError):
        return "--"


def _usd_price(value: Any) -> str:
    try:
        return f"${float(value):.2f}"
    except (TypeError, ValueError):
        return "$--"


def _optional_float(row: Mapping[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = row.get(key)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(numeric):
            return numeric
    return None


def _five_day_status_tags(row: Mapping[str, Any]) -> list[str]:
    chg_5d = safe_float(row.get("chg_5d", 0.0))
    chg_pct = safe_float(row.get("chg", 0.0))
    rsi = safe_float(row.get("rsi", row.get("RSI", 0.0)))
    volume_ratio = safe_float(row.get("volume_ratio_20", 0.0))
    ma20_dist = safe_float(row.get("ma20_dist_pct", row.get("dist_sma20_pct", 0.0)))
    zscore20 = safe_float(row.get("zscore20", 0.0))
    entry_judgment = str(row.get("entry_judgment") or "").strip().upper()

    tags: list[str] = []
    if chg_5d >= 10.0 or is_truthy(row.get("strong_trend_persistent")):
        tags.append("강한상승")
    if volume_ratio >= 1.2 or is_truthy(row.get("volume_bullish")):
        tags.append("거래량동반")
    if rsi >= 75.0 or ma20_dist >= 20.0 or zscore20 >= 3.0:
        tags.append("과열주의")
    if is_truthy(row.get("entry_chase_risk")) or chg_5d >= 20.0 or chg_pct >= 12.0:
        tags.append("추격주의")
    if is_truthy(row.get("thin_trade_risk")) or volume_ratio < 0.8:
        tags.append("저유동성주의")
    if entry_judgment == "WAIT_PULLBACK" or is_truthy(row.get("pullback_reentry")):
        tags.append("눌림대기")
    return tags or ["정상상승"]


def _five_day_status(row: Mapping[str, Any]) -> str:
    return "/".join(_five_day_status_tags(row))


def _turn_engine_text(*, utbot: bool, hull: bool) -> str:
    if utbot and hull:
        return "UTBot+HULL"
    if utbot:
        return "UTBot"
    if hull:
        return "HULL"
    return "-"


def _top_reasons(reasons: list[str], *, fallback: str) -> str:
    unique: list[str] = []
    for reason in reasons:
        text = str(reason or "").strip()
        if not text or text in unique:
            continue
        unique.append(text)
        if len(unique) >= 3:
            break
    if not unique:
        return fallback
    return " + ".join(unique)


def _hit_summary(*values: Any) -> str:
    hits: list[str] = []
    for raw_value in values:
        for item in list(raw_value or []):
            text = str(item or "").strip()
            if not text or text in hits:
                continue
            hits.append(text)
            if len(hits) >= 2:
                return " + ".join(hits)
    return ""


def _text_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        parts = value.replace("|", "+").split("+")
    elif isinstance(value, (list, tuple, set)):
        parts = list(value)
    else:
        parts = [value]
    items: list[str] = []
    for part in parts:
        text = str(part or "").strip()
        if text and text not in items:
            items.append(text)
    return items


def _dict_or_empty(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _build_final_top_reason(row: Mapping[str, Any], target_date: date) -> str:
    reasons: list[str] = []
    if same_session_buy_turn(row, target_date):
        reasons.append("same-session buy turn")
    if safe_float(row.get("volume_ratio_20", 0.0)) >= 1.2:
        reasons.append("volume lead")
    if safe_float(row.get("cmf", 0.0)) > 0.05:
        reasons.append("CMF+")
    if safe_float(row.get("obv_slope", 0.0)) > 0.0:
        reasons.append("OBV up")
    if is_truthy(row.get("low_conflict_bullish")) or str(row.get("strategy_conflict_level", "")).strip().upper() == "LOW":
        reasons.append("low conflict")
    return _top_reasons(reasons, fallback="final entry")


def _build_buy_turn_reason(row: Mapping[str, Any], target_date: date) -> str:
    reasons = ["same-day turn"]
    if same_day_buy_turn_count(row, target_date) >= 2:
        reasons.append("UTBot+HULL")
    if safe_float(row.get("volume_ratio_20", 0.0)) >= 1.2:
        reasons.append("volume lead")
    if safe_float(row.get("cmf", 0.0)) > 0.0:
        reasons.append("CMF+")
    if safe_float(row.get("obv_slope", 0.0)) > 0.0:
        reasons.append("OBV up")
    return _top_reasons(reasons, fallback="buy turn")


def _build_pullback_reason(row: Mapping[str, Any]) -> str:
    reasons: list[str] = ["uptrend persistent"]
    if is_truthy(row.get("pullback_reentry")):
        reasons.append("reentry signal")
    else:
        reasons.append("reentry ready")
    if safe_float(row.get("volume_dry_up_score", 0.0)) >= 10.0:
        reasons.append("volume dry-up")
    if safe_float(row.get("pullback_atr_multiple", 0.0)) <= 2.0:
        reasons.append("shallow pullback")
    return _top_reasons(reasons, fallback="pullback reentry")


def _build_trend_reason(row: Mapping[str, Any]) -> str:
    reasons: list[str] = []
    if safe_float(row.get("rs_rank_vs_index", 0.0)) >= 70.0:
        reasons.append("high RS")
    reasons.append("trend slope up")
    if is_truthy(row.get("volume_bullish")):
        reasons.append("volume support")
    if safe_float(row.get("zscore20", 0.0)) >= 2.5 or safe_float(row.get("dist_sma20_pct", 0.0)) >= 15.0:
        reasons.append("overheat caution")
    return _top_reasons(reasons, fallback="trend continuation")


def _build_hma_ema_reason(row: Mapping[str, Any]) -> str:
    reasons: list[str] = []
    if is_truthy(row.get("hma_ema_long_entry")):
        reasons.append("HMA25/EMA25 long entry")
    elif is_truthy(row.get("hma_ema_long_aligned")):
        reasons.append("HMA/EMA aligned")
    if is_truthy(row.get("hma25_ema25_cross_bull")):
        reasons.append("bull cross")
    if safe_float(row.get("volume_ratio_20", 0.0)) >= 1.2:
        reasons.append("volume lead")
    if safe_float(row.get("adx", 0.0)) >= 20.0:
        reasons.append("ADX trend")
    if safe_float(row.get("hma_ema_risk_to_ema50_pct", 999.0)) <= 5.0:
        reasons.append("EMA50 near")
    return _top_reasons(reasons, fallback="HMA/EMA trend")


def _build_sell_turn_reason(row: Mapping[str, Any], target_date: date) -> str:
    reasons = ["same-day turn"]
    if same_day_sell_turn_count(row, target_date) >= 2:
        reasons.append("UTBot+HULL")
    if safe_float(row.get("volume_ratio_20", 0.0)) >= 1.0:
        reasons.append("volume support")
    if safe_float(row.get("scan_score", 0.0)) > 0.0:
        reasons.append(f"score {safe_float(row.get('scan_score', 0.0)):.1f}")
    return _top_reasons(reasons, fallback="sell turn")


def _build_gap_setup_reason(row: Mapping[str, Any]) -> str:
    reasons = [
        f"GAP {int(safe_float(row.get('gap_setup_score', 0.0))):d}",
        f"G{int(safe_float(row.get('gap_setup_gate_count', 0.0))):d}/5",
    ]
    hit_text = _hit_summary(row.get("gap_setup_quality_hits"), row.get("gap_setup_hits"))
    if hit_text:
        reasons.append(hit_text)
    return _top_reasons(reasons, fallback="gap setup")


def _build_pocket_pivot_reason(row: Mapping[str, Any]) -> str:
    reasons = [
        f"PP {int(safe_float(row.get('pocket_pivot_score', 0.0))):d}",
        f"G{int(safe_float(row.get('pocket_pivot_gate_count', 0.0))):d}/5",
    ]
    hit_text = _hit_summary(row.get("pocket_pivot_quality_hits"), row.get("pocket_pivot_hits"))
    if hit_text:
        reasons.append(hit_text)
    return _top_reasons(reasons, fallback="pocket pivot")


def _build_five_day_top_reason(row: Mapping[str, Any]) -> str:
    reasons = [f"5D {_signed(row.get('chg_5d'), 2)}%"]
    if safe_float(row.get("volume_ratio_20", 0.0)) >= 1.2:
        reasons.append("volume lead")
    if safe_float(row.get("scan_score", 0.0)) > 0.0:
        reasons.append(f"score {safe_float(row.get('scan_score', 0.0)):.1f}")
    return _top_reasons(reasons, fallback="5D top")


def _build_new_52w_high_reason(row: Mapping[str, Any]) -> str:
    reasons = ["new 52W high"]
    if is_truthy(row.get("new_52w_closing_high")):
        reasons.append("closing high")
    if safe_float(row.get("volume_ratio_20", 0.0)) >= 1.2:
        reasons.append("volume lead")
    return _top_reasons(reasons, fallback="new 52W high")


def _candidate_label(section_key: str) -> str:
    if section_key in AGGRESSIVE_SECTION_KEYS:
        return str(AGGRESSIVE_NEXT_DAY_SECTION_TITLES.get(section_key, section_key))
    return {
        "confluence": "CONFLUENCE",
        "entry_now": "ENTRY",
        "steady_uptrend": "STEADY",
        "breakout_wait": "BREAKOUT_WAIT",
        "accumulation": "ACCUMULATION",
        "rs_leader": "RS_LEADER",
        "chase_risk": "CHASE_RISK",
        "sell_risk": "SELL_RISK",
        "final_top": "final",
        "buy_turn": "buy turn",
        "pullback_reentry": "pullback",
        "trend_continuation": "trend",
        "hma_ema_trend": "HMA/EMA",
        "sell_turn": "sell turn",
        "gap_setup": "gap setup",
        "pocket_pivot": "pocket pivot",
        "five_day_top": "5D top",
        STEADY_WINNER_SECTION_KEY: "PUL",
        EARLY_REVERSAL_KEY: "ERS",
        HULL_BUY_TURN_KEY: "HULL BUY",
        STARTUP9_CONFIRM_KEY: "S9 CONFIRM",
        TECHNICAL_BUY_CLUSTER_KEY: "TECH BUY",
        "new_52w_high": "52W high",
    }.get(section_key, section_key)


def _candidate_reason(section_key: str, row: Mapping[str, Any], target_date: date) -> str:
    if section_key in AGGRESSIVE_SECTION_KEYS:
        return str(row.get("aggressive_reason") or "-")
    if section_key == STARTUP9_CONFIRM_KEY:
        return str(row.get("startup9_confirm_reason") or "-")
    if section_key == TECHNICAL_BUY_CLUSTER_KEY:
        return str(row.get("technical_buy_reason") or "-")
    board_reason = str(row.get("board_reason") or "").strip()
    if section_key in BOARD_SECTION_KEYS and board_reason:
        return board_reason
    if section_key == "final_top":
        return _build_final_top_reason(row, target_date)
    if section_key == "buy_turn":
        return _build_buy_turn_reason(row, target_date)
    if section_key == "pullback_reentry":
        return _build_pullback_reason(row)
    if section_key == "trend_continuation":
        return _build_trend_reason(row)
    if section_key == "hma_ema_trend":
        return _build_hma_ema_reason(row)
    if section_key == "sell_turn":
        return _build_sell_turn_reason(row, target_date)
    if section_key == "gap_setup":
        return _build_gap_setup_reason(row)
    if section_key == "pocket_pivot":
        return _build_pocket_pivot_reason(row)
    if section_key == "five_day_top":
        return _five_day_status(row)
    if section_key == STEADY_WINNER_SECTION_KEY:
        return str(row.get("pul_reason") or "-")
    if section_key == EARLY_REVERSAL_KEY:
        return str(row.get("reversal_reason") or "-")
    if section_key == HULL_BUY_TURN_KEY:
        return str(row.get("hull_reason") or "HULL")
    if section_key == "new_52w_high":
        return _build_new_52w_high_reason(row)
    return "-"


def _candidate_source_flags(section_key: str, row: Mapping[str, Any], target_date: date) -> dict[str, Any]:
    buy_turn_utbot = same_day_utbot_buy_turn(row, target_date)
    buy_turn_hull = same_day_hull_buy_turn(row, target_date)
    sell_turn_utbot = same_day_utbot_sell_turn(row, target_date)
    sell_turn_hull = same_day_hull_sell_turn(row, target_date)
    turn_engine = ""
    if section_key == "buy_turn":
        turn_engine = _turn_engine_text(utbot=buy_turn_utbot, hull=buy_turn_hull)
    elif section_key == HULL_BUY_TURN_KEY:
        turn_engine = "HULL"
    elif section_key == "sell_turn":
        turn_engine = _turn_engine_text(utbot=sell_turn_utbot, hull=sell_turn_hull)

    return {
        "same_session_buy_turn": same_session_buy_turn(row, target_date),
        "same_session_sell_turn": same_session_sell_turn(row, target_date),
        "buy_turn_utbot": buy_turn_utbot,
        "buy_turn_hull": buy_turn_hull,
        "sell_turn_utbot": sell_turn_utbot,
        "sell_turn_hull": sell_turn_hull,
        "turn_engine": turn_engine,
        "thin_trade_risk": is_truthy(row.get("thin_trade_risk")),
        "bearish_gap_failure": is_truthy(row.get("bearish_gap_failure")),
        "hma_ema_long_aligned": is_truthy(row.get("hma_ema_long_aligned")),
        "hma_ema_long_entry": is_truthy(row.get("hma_ema_long_entry")),
        "hma_ema_short_aligned": is_truthy(row.get("hma_ema_short_aligned")),
        "hma_ema_short_entry": is_truthy(row.get("hma_ema_short_entry")),
        "hma_ema_signal_state": str(row.get("hma_ema_signal_state") or "NEUTRAL"),
        "multi_buy": int(safe_float(row.get("multi_buy", 0.0))),
        "multi_sell": int(safe_float(row.get("multi_sell", 0.0))),
        "today_chg_pct": safe_float(row.get("chg", 0.0)),
        "chg_5d": safe_float(row.get("chg_5d", 0.0)),
        "ret_1m_pct": _optional_float(row, "ret_1m_pct", "ret20_pct"),
        "ret_1y_pct": _optional_float(row, "ret_1y_pct", "ret252_pct"),
        "rsi": safe_float(row.get("rsi", row.get("RSI", 0.0))),
        "ma20_dist_pct": safe_float(row.get("ma20_dist_pct", row.get("dist_sma20_pct", 0.0))),
        "high_pos_pct": _optional_float(row, "high_pos_pct", "drawdown_from_52w_high_pct"),
        "atr_pct": safe_float(row.get("atr_pct", 0.0)),
        "adx": safe_float(row.get("adx", 0.0)),
        "ret20_percentile": safe_float(row.get("ret20_percentile", 0.0)),
        "ret60_percentile": safe_float(row.get("ret60_percentile", 0.0)),
        "ret20_pct": safe_float(row.get("ret20_pct", 0.0)),
        "zscore20": safe_float(row.get("zscore20", 0.0)),
        "bb_percent_b": safe_float(row.get("bb_percent_b", 0.0)),
        "dist_sma20_pct": safe_float(row.get("dist_sma20_pct", row.get("ma20_dist_pct", 0.0))),
        "drawdown_from_20d_high_pct": safe_float(row.get("drawdown_from_20d_high_pct", 0.0)),
        "breakout_dist_20d_high_pct": safe_float(row.get("breakout_dist_20d_high_pct", 0.0)),
        "volume_expansion_score": safe_float(row.get("volume_expansion_score", 0.0)),
        "cmf": safe_float(row.get("cmf", 0.0)),
        "obv_slope": safe_float(row.get("obv_slope", 0.0)),
        "compression_count": int(safe_float(row.get("compression_count", 0.0))),
        "rs_rank_vs_index": safe_float(row.get("rs_rank_vs_index", 0.0)),
        "status_tags": _five_day_status_tags(row) if section_key == FIVE_DAY_TOP_SECTION_KEY else [],
        "status": _five_day_status(row) if section_key == FIVE_DAY_TOP_SECTION_KEY else "",
        "pul_score": safe_float(row.get("pul_score", 0.0)) if section_key == STEADY_WINNER_SECTION_KEY else 0.0,
        "early_reversal_score": safe_float(row.get("early_reversal_score", 0.0)) if section_key == EARLY_REVERSAL_KEY else 0.0,
        "reversal_type": str(row.get("reversal_type") or "") if section_key == EARLY_REVERSAL_KEY else "",
        "reversal_phase": str(row.get("reversal_phase") or "") if section_key == EARLY_REVERSAL_KEY else "",
        "reversal_confirm": str(row.get("reversal_confirm") or "") if section_key == EARLY_REVERSAL_KEY else "",
        "hull_confirm": str(row.get("hull_confirm") or "") if section_key == HULL_BUY_TURN_KEY else "",
        "hull_utbot_same_turn": int(safe_float(row.get("hull_utbot_same_turn", 0.0))) if section_key == HULL_BUY_TURN_KEY else 0,
        "entry_type": str(row.get("entry_type") or "") if section_key in {STEADY_WINNER_SECTION_KEY, EARLY_REVERSAL_KEY, HULL_BUY_TURN_KEY, *AGGRESSIVE_SECTION_KEYS} else "",
        "technical_buy_score": safe_float(row.get("technical_buy_score", 0.0)) if section_key == TECHNICAL_BUY_CLUSTER_KEY else 0.0,
        "technical_buy_signal_count": int(safe_float(row.get("technical_buy_signal_count", 0.0))) if section_key == TECHNICAL_BUY_CLUSTER_KEY else 0,
        "technical_buy_hits": _text_list(row.get("technical_buy_hits")) if section_key == TECHNICAL_BUY_CLUSTER_KEY else [],
        "technical_buy_bucket": str(row.get("technical_buy_bucket") or "") if section_key == TECHNICAL_BUY_CLUSTER_KEY else "",
        "technical_buy_reason": str(row.get("technical_buy_reason") or "") if section_key == TECHNICAL_BUY_CLUSTER_KEY else "",
        "technical_buy_risk_flags": _text_list(row.get("technical_buy_risk_flags")) if section_key == TECHNICAL_BUY_CLUSTER_KEY else [],
        "startup9_confirm_count": int(safe_float(row.get("startup9_confirm_count", 0.0))) if section_key == STARTUP9_CONFIRM_KEY else 0,
        "startup9_confirm_grade": str(row.get("startup9_confirm_grade") or "") if section_key == STARTUP9_CONFIRM_KEY else "",
        "startup9_confirm_hits": _text_list(row.get("startup9_confirm_hits")) if section_key == STARTUP9_CONFIRM_KEY else [],
        "startup9_confirm_missing": _text_list(row.get("startup9_confirm_missing")) if section_key == STARTUP9_CONFIRM_KEY else [],
        "startup9_confirm_reason": str(row.get("startup9_confirm_reason") or "") if section_key == STARTUP9_CONFIRM_KEY else "",
        "startup9_risk_flags": _text_list(row.get("startup9_risk_flags")) if section_key == STARTUP9_CONFIRM_KEY else [],
        "startup9_score": safe_float(row.get("startup9_score", 0.0)) if section_key == STARTUP9_CONFIRM_KEY else 0.0,
        "startup9_profile": str(row.get("startup9_profile") or "") if section_key == STARTUP9_CONFIRM_KEY else "",
        "startup9_direction_state": str(row.get("startup9_direction_state") or "") if section_key == STARTUP9_CONFIRM_KEY else "",
        "startup9_confirm_map": _dict_or_empty(row.get("startup9_confirm_map")) if section_key == STARTUP9_CONFIRM_KEY else {},
        "startup9_confirm_keys": _text_list(row.get("startup9_confirm_keys")) if section_key == STARTUP9_CONFIRM_KEY else [],
        "startup9_missing_keys": _text_list(row.get("startup9_missing_keys")) if section_key == STARTUP9_CONFIRM_KEY else [],
        "startup9_hard_exclusions": _text_list(row.get("startup9_hard_exclusions")) if section_key == STARTUP9_CONFIRM_KEY else [],
        "startup9_soft_risk_flags": _text_list(row.get("startup9_soft_risk_flags")) if section_key == STARTUP9_CONFIRM_KEY else [],
        "label": _candidate_label(section_key),
        "membership": list(row.get("source_membership") or []),
        "membership_count": int(safe_float(row.get("membership_count", 0.0))),
        "board_risk": str(row.get("board_risk") or "-"),
    }


def _build_candidate(section_key: str, row: Mapping[str, Any], rank: int, target_date: date) -> TelegramCandidate:
    chg_pct = _optional_float(row, "chg_5d") if section_key == FIVE_DAY_TOP_SECTION_KEY else _optional_float(row, "chg")
    status_tags = _five_day_status_tags(row) if section_key == FIVE_DAY_TOP_SECTION_KEY else []
    steady_risk_tags = list(row.get("pul_risk_tags") or []) if section_key == STEADY_WINNER_SECTION_KEY else []
    reversal_risk_tags = list(row.get("reversal_risk_flags") or []) if section_key == EARLY_REVERSAL_KEY else []
    hull_risk_tags = list(row.get("hull_risk_flags") or []) if section_key == HULL_BUY_TURN_KEY else []
    aggressive_risk_tags = list(row.get("aggressive_risk_flags") or []) if section_key in AGGRESSIVE_SECTION_KEYS else []
    technical_hits = _text_list(row.get("technical_buy_hits")) if section_key == TECHNICAL_BUY_CLUSTER_KEY else []
    technical_risk_tags = _text_list(row.get("technical_buy_risk_flags")) if section_key == TECHNICAL_BUY_CLUSTER_KEY else []
    startup9_hits = _text_list(row.get("startup9_confirm_hits")) if section_key == STARTUP9_CONFIRM_KEY else []
    startup9_missing = _text_list(row.get("startup9_confirm_missing")) if section_key == STARTUP9_CONFIRM_KEY else []
    startup9_risk_tags = _text_list(row.get("startup9_risk_flags")) if section_key == STARTUP9_CONFIRM_KEY else []
    if technical_risk_tags == ["특이사항 없음"]:
        technical_risk_tags = []
    if startup9_risk_tags == ["특이사항 없음"]:
        startup9_risk_tags = []
    return TelegramCandidate(
        ticker=str(row.get("ticker") or "").strip().upper(),
        price=safe_float(row.get("price")) if row.get("price") is not None else None,
        chg_value=safe_float(row.get("chg_value")) if row.get("chg_value") is not None else None,
        chg_pct=chg_pct,
        volume_ratio_20=safe_float(row.get("volume_ratio_20")) if row.get("volume_ratio_20") is not None else None,
        section_key=section_key,
        rank=rank,
        label=str(
            row.get("aggressive_label")
            or (row.get("startup9_confirm_grade") if section_key == STARTUP9_CONFIRM_KEY else None)
            or row.get("technical_buy_bucket")
            or row.get("pul_bucket")
            or row.get("reversal_phase")
            or row.get("hull_bucket")
            or row.get("board_label")
            or _candidate_label(section_key)
        ),
        reason=_candidate_reason(section_key, row, target_date),
        source_flags=_candidate_source_flags(section_key, row, target_date),
        bucket=str(
            row.get("aggressive_bucket")
            or (row.get("startup9_profile") if section_key == STARTUP9_CONFIRM_KEY else None)
            or row.get("technical_buy_bucket")
            or row.get("pul_bucket")
            or row.get("reversal_phase")
            or row.get("hull_bucket")
            or ""
        ),
        tags=list(
            row.get("aggressive_tags")
            or startup9_hits
            or technical_hits
            or row.get("pul_tags")
            or row.get("reversal_tags")
            or row.get("hull_tags")
            or row.get("board_tags")
            or []
        ),
        risk_flags=aggressive_risk_tags
        or startup9_risk_tags
        or technical_risk_tags
        or steady_risk_tags
        or reversal_risk_tags
        or hull_risk_tags
        or list(row.get("board_risk_flags") or []),
        chg_5d=_optional_float(row, "chg_5d"),
        rsi=_optional_float(row, "rsi", "RSI"),
        ma20_dist_pct=_optional_float(row, "ma20_dist_pct", "dist_sma20_pct"),
        ret_1m_pct=_optional_float(row, "ret_1m_pct", "ret20_pct"),
        ret_1y_pct=_optional_float(row, "ret_1y_pct", "ret252_pct"),
        high_pos_pct=_optional_float(row, "high_pos_pct", "drawdown_from_52w_high_pct"),
        status_tags=status_tags,
        status="/".join(status_tags) if status_tags else "",
        pul_score=_optional_float(row, "pul_score"),
        early_reversal_score=_optional_float(row, "early_reversal_score"),
        reversal_type=str(row.get("reversal_type") or ""),
        reversal_phase=str(row.get("reversal_phase") or ""),
        entry_type=str(row.get("entry_type") or ""),
        technical_buy_score=_optional_float(row, "technical_buy_score"),
        technical_buy_signal_count=int(safe_float(row.get("technical_buy_signal_count", 0.0))) if section_key == TECHNICAL_BUY_CLUSTER_KEY else 0,
        technical_buy_hits=technical_hits,
        technical_buy_bucket=str(row.get("technical_buy_bucket") or ""),
        technical_buy_reason=str(row.get("technical_buy_reason") or ""),
        technical_buy_risk_flags=technical_risk_tags,
        startup9_confirm_count=int(safe_float(row.get("startup9_confirm_count", 0.0))) if section_key == STARTUP9_CONFIRM_KEY else 0,
        startup9_confirm_grade=str(row.get("startup9_confirm_grade") or ""),
        startup9_confirm_hits=startup9_hits,
        startup9_confirm_missing=startup9_missing,
        startup9_confirm_reason=str(row.get("startup9_confirm_reason") or ""),
        startup9_risk_flags=startup9_risk_tags,
        startup9_score=_optional_float(row, "startup9_score"),
        startup9_profile=str(row.get("startup9_profile") or ""),
        startup9_direction_state=str(row.get("startup9_direction_state") or ""),
    )


def _build_qbs_candidate(section_key: str, candidate: Any) -> TelegramCandidate:
    return TelegramCandidate(
        ticker=str(candidate.ticker or "").strip().upper(),
        price=candidate.price,
        chg_value=candidate.chg_value,
        chg_pct=candidate.chg_pct,
        volume_ratio_20=candidate.volume_ratio_20,
        section_key=section_key,
        rank=int(candidate.rank or 0),
        label=str(candidate.bucket or ""),
        reason="+".join(candidate.tags) or "-",
        source_flags=dict(candidate.source_flags or {}),
        qbs_score=candidate.qbs_score,
        bucket=str(candidate.bucket or ""),
        tags=list(candidate.tags or []),
        risk_flags=list(candidate.risk_flags or []),
        chg_5d=_optional_float(candidate.source_flags or {}, "chg_5d"),
        rsi=_optional_float(candidate.source_flags or {}, "rsi"),
        ma20_dist_pct=_optional_float(candidate.source_flags or {}, "ma20_dist_pct"),
        ret_1m_pct=_optional_float(candidate.source_flags or {}, "ret_1m_pct"),
        ret_1y_pct=_optional_float(candidate.source_flags or {}, "ret_1y_pct"),
        high_pos_pct=_optional_float(candidate.source_flags or {}, "high_pos_pct"),
    )


def _build_qbs_sections(section_rows: Mapping[str, Iterable[Mapping[str, Any]]], target_date: date) -> list[TelegramSection]:
    qbs_sections = build_final_buy_sections(section_rows, target_date=target_date)
    sections: list[TelegramSection] = []
    for section_key in QBS_OUTPUT_KEYS:
        candidates = list(qbs_sections.get(section_key) or [])
        items = [_build_qbs_candidate(section_key, candidate) for candidate in candidates]
        sections.append(
            TelegramSection(
                key=section_key,
                title=QBS_SECTION_TITLES[section_key],
                items=items,
                item_count=len(items),
                quality_floor=QBS_QUALITY_FLOORS[section_key],
                ranked=True,
            )
        )
    return sections


def _build_technical_buy_cluster_section(rows: Iterable[Mapping[str, Any]], target_date: date) -> TelegramSection:
    tech_rows = select_technical_buy_rows(
        rows,
        target_date=target_date,
        limit=TECHNICAL_BUY_CLUSTER_LIMIT,
    )
    items = [
        _build_candidate(TECHNICAL_BUY_CLUSTER_KEY, row, idx, target_date)
        for idx, row in enumerate(tech_rows, start=1)
    ]
    return TelegramSection(
        key=TECHNICAL_BUY_CLUSTER_KEY,
        title=TECHNICAL_BUY_CLUSTER_TITLE,
        items=items,
        item_count=len(items),
        quality_floor=TECHNICAL_BUY_CLUSTER_QUALITY_FLOOR,
        ranked=True,
    )


def _build_startup9_confirm_section(rows: Iterable[Mapping[str, Any]], target_date: date) -> TelegramSection:
    startup_rows = select_startup9_confirm_rows(
        rows,
        target_date=target_date,
        limit=STARTUP9_CONFIRM_LIMIT,
    )
    items = [
        _build_candidate(STARTUP9_CONFIRM_KEY, row, idx, target_date)
        for idx, row in enumerate(startup_rows, start=1)
    ]
    return TelegramSection(
        key=STARTUP9_CONFIRM_KEY,
        title=STARTUP9_CONFIRM_TITLE,
        items=items,
        item_count=len(items),
        quality_floor=STARTUP9_CONFIRM_QUALITY_FLOOR,
        ranked=True,
    )


def _build_aggressive_next_day_sections(rows: Iterable[Mapping[str, Any]], target_date: date) -> list[TelegramSection]:
    aggressive_rows = select_aggressive_next_day_sections(
        rows,
        target_date=target_date,
        limit=AGGRESSIVE_NEXT_DAY_LIMIT,
    )
    sections: list[TelegramSection] = []
    for section_key in AGGRESSIVE_NEXT_DAY_SECTION_KEYS:
        row_list = list(aggressive_rows.get(section_key) or [])
        items = [_build_candidate(section_key, row, idx, target_date) for idx, row in enumerate(row_list, start=1)]
        sections.append(
            TelegramSection(
                key=section_key,
                title=AGGRESSIVE_NEXT_DAY_SECTION_TITLES[section_key],
                items=items,
                item_count=len(items),
                quality_floor=AGGRESSIVE_NEXT_DAY_QUALITY_FLOORS[section_key],
                ranked=True,
            )
        )
    return sections


def build_post_close_digest(
    rows: Iterable[Mapping[str, Any]],
    *,
    run_stamp: str,
    generated_at: datetime,
    market_date: date,
    scan_label: str,
    universe_count: int,
    result_count: int,
    skip_count: int,
) -> TelegramDigest:
    row_list = [dict(row or {}) for row in (rows or [])]
    row_list = annotate_rows_with_startup9_confirm(row_list, target_date=market_date)
    section_rows = select_post_close_sections(row_list, target_date=market_date)

    sections: list[TelegramSection] = _build_qbs_sections(section_rows, market_date)
    steady_rows = list(section_rows.get(STEADY_WINNER_SECTION_KEY) or [])
    steady_items = [
        _build_candidate(STEADY_WINNER_SECTION_KEY, row, idx, market_date)
        for idx, row in enumerate(steady_rows, start=1)
    ]
    sections.append(
        TelegramSection(
            key=STEADY_WINNER_SECTION_KEY,
            title=STEADY_WINNER_SECTION_TITLE,
            items=steady_items,
            item_count=len(steady_items),
            quality_floor=STEADY_WINNER_QUALITY_FLOOR,
            ranked=True,
        )
    )
    early_rows = build_early_reversal_section(row_list, target_date=market_date)
    early_items = [
        _build_candidate(EARLY_REVERSAL_KEY, row, idx, market_date)
        for idx, row in enumerate(early_rows, start=1)
    ]
    sections.append(
        TelegramSection(
            key=EARLY_REVERSAL_KEY,
            title=EARLY_REVERSAL_SECTION_TITLE,
            items=early_items,
            item_count=len(early_items),
            quality_floor=EARLY_REVERSAL_QUALITY_FLOOR,
            ranked=True,
        )
    )
    hull_rows = select_hull_buy_turn_rows(row_list, target_date=market_date)
    hull_items = [
        _build_candidate(HULL_BUY_TURN_KEY, row, idx, market_date)
        for idx, row in enumerate(hull_rows, start=1)
    ]
    sections.append(
        TelegramSection(
            key=HULL_BUY_TURN_KEY,
            title=HULL_BUY_TURN_SECTION_TITLE,
            items=hull_items,
            item_count=len(hull_items),
            quality_floor=HULL_BUY_TURN_QUALITY_FLOOR,
            ranked=True,
        )
    )
    sections.append(_build_startup9_confirm_section(row_list, market_date))
    sections.append(_build_technical_buy_cluster_section(row_list, market_date))
    sections.extend(_build_aggressive_next_day_sections(row_list, market_date))
    qbs_top_tickers = {
        item.ticker
        for section in sections
        if section.key == QBS_BUY_NOW_KEY
        for item in section.items
    }
    board_rows = select_post_close_board_sections(
        section_rows,
        target_date=market_date,
        all_rows=row_list,
        qbs_top_tickers=qbs_top_tickers,
    )
    for section_key in BOARD_SECTION_ORDER:
        row_list = list(board_rows.get(section_key) or [])
        items = [_build_candidate(section_key, row, idx, market_date) for idx, row in enumerate(row_list, start=1)]
        sections.append(
            TelegramSection(
                key=section_key,
                title=BOARD_SECTION_TITLES[section_key],
                items=items,
                item_count=len(items),
                quality_floor=BOARD_QUALITY_FLOORS[section_key],
                ranked=True,
            )
        )
    five_day_rows = list(section_rows.get(FIVE_DAY_TOP_SECTION_KEY) or [])
    five_day_items = [
        _build_candidate(FIVE_DAY_TOP_SECTION_KEY, row, idx, market_date)
        for idx, row in enumerate(five_day_rows, start=1)
    ]
    sections.append(
        TelegramSection(
            key=FIVE_DAY_TOP_SECTION_KEY,
            title=f"5일 상승률 Top{FIVE_DAY_TOP_LIMIT}",
            items=five_day_items,
            item_count=len(five_day_items),
            quality_floor=CORE_QUALITY_FLOORS[FIVE_DAY_TOP_SECTION_KEY],
            ranked=True,
        )
    )

    return TelegramDigest(
        version="2.0",
        scan_mode="post_close",
        run_stamp=str(run_stamp or "").strip(),
        market_date=market_date.isoformat(),
        generated_at=generated_at.isoformat(),
        section_order=[
            *QBS_OUTPUT_KEYS,
            STEADY_WINNER_SECTION_KEY,
            EARLY_REVERSAL_KEY,
            HULL_BUY_TURN_KEY,
            STARTUP9_CONFIRM_KEY,
            TECHNICAL_BUY_CLUSTER_KEY,
            *AGGRESSIVE_NEXT_DAY_SECTION_KEYS,
            *BOARD_SECTION_ORDER,
            FIVE_DAY_TOP_SECTION_KEY,
        ],
        sections=sections,
        briefing_refs={
            "mode": "separate_message",
            "job": "market_briefing_notify",
            "expected_order": ["market_briefing", "main_board"],
        },
        scan_label=scan_label,
        universe_count=int(universe_count or 0),
        result_count=int(result_count or 0),
        skip_count=int(skip_count or 0),
    )


def _format_candidate_line(candidate: TelegramCandidate) -> str:
    risk = "+".join(list(candidate.risk_flags or [])) or str(candidate.source_flags.get("board_risk") or "-")
    return (
        f"{candidate.rank}. {candidate.ticker}"
        f" | {str(candidate.label or '-')}"
        f" | {_signed(candidate.chg_pct)}%"
        f" | {_ratio(candidate.volume_ratio_20)}"
        f" | {str(candidate.reason or '-')}"
        f" | {risk or '-'}"
    )


def _format_five_day_candidate_line(candidate: TelegramCandidate) -> str:
    return (
        f"{candidate.ticker}"
        f" | {_signed(candidate.chg_5d, 2)}%"
        f" | RSI {_number(candidate.rsi, 1)}"
        f" | {_ratio(candidate.volume_ratio_20, 2)}"
        f" | {_signed(candidate.ma20_dist_pct, 1)}%"
        f" | {str(candidate.status or '-')}"
    )


def _format_qbs_candidate_line(candidate: TelegramCandidate) -> str:
    tags = "+".join(list(candidate.tags or [])) or "-"
    line = (
        f"{candidate.rank}. {candidate.ticker}"
        f" | QBS {safe_float(candidate.qbs_score):.1f}"
        f" | ({_signed(candidate.chg_value)}, {_signed(candidate.chg_pct)}%)"
        f" | {_ratio(candidate.volume_ratio_20)}"
        f" | {str(candidate.bucket or '-')}"
        f" | {tags}"
    )
    risk_flags = "+".join(list(candidate.risk_flags or []))
    if risk_flags:
        line += f" | 주의:{risk_flags}"
    return line


def _format_aggressive_candidate_line(candidate: TelegramCandidate) -> str:
    flags = dict(candidate.source_flags or {})
    risk = "+".join(list(candidate.risk_flags or [])) or "-"
    return (
        f"{candidate.rank}. {candidate.ticker}"
        f" | {_signed(candidate.chg_pct, 2)}% / 5D {_signed(candidate.chg_5d, 2)}%"
        f" | ATR {_number(flags.get('atr_pct'), 1)}"
        f" | Vol20 {_ratio(candidate.volume_ratio_20, 2)}"
        f" | RS {_number(flags.get('rs_rank_vs_index'), 0)}"
        f" | ADX {_number(flags.get('adx'), 0)}"
        f" | {str(candidate.reason or '-')}"
        f" | {risk}"
    )


def _format_technical_buy_candidate_line(candidate: TelegramCandidate) -> str:
    flags = dict(candidate.source_flags or {})
    hits = list(candidate.technical_buy_hits or candidate.tags or flags.get("technical_buy_hits") or [])
    risk_flags = list(candidate.technical_buy_risk_flags or candidate.risk_flags or flags.get("technical_buy_risk_flags") or [])
    risk = "+".join(risk_flags) if risk_flags else "특이사항 없음"
    bucket = str(candidate.technical_buy_bucket or candidate.bucket or flags.get("technical_buy_bucket") or "-")
    reason = str(candidate.technical_buy_reason or candidate.reason or flags.get("technical_buy_reason") or "-")
    score = candidate.technical_buy_score
    if score is None:
        score = flags.get("technical_buy_score")
    signal_count = candidate.technical_buy_signal_count or int(safe_float(flags.get("technical_buy_signal_count", 0.0)))
    return "\n".join(
        [
            (
                f"{candidate.rank}. {candidate.ticker}"
                f" | {_usd_price(candidate.price)}"
                f" | {_signed(candidate.chg_pct, 2)}%"
            ),
            (
                f"   점수 {safe_float(score):.1f} / 신호 {int(signal_count)}개"
                f" / Vol20 {_ratio(candidate.volume_ratio_20, 2)}"
                f" / ATR {_number(flags.get('atr_pct'), 1)}%"
            ),
            f"   분류: {bucket}",
            f"   신호: {' + '.join(hits[:8]) if hits else '-'}",
            f"   리스크: {risk}",
            f"   이유: {reason}",
        ]
    )


def _format_startup9_candidate_line(candidate: TelegramCandidate) -> str:
    flags = dict(candidate.source_flags or {})
    hits = list(candidate.startup9_confirm_hits or candidate.tags or flags.get("startup9_confirm_hits") or [])
    risk_flags = list(candidate.startup9_risk_flags or candidate.risk_flags or flags.get("startup9_risk_flags") or [])
    risk = ", ".join(risk_flags) if risk_flags else "특이사항 없음"
    grade = str(candidate.startup9_confirm_grade or candidate.label or flags.get("startup9_confirm_grade") or "-")
    count = candidate.startup9_confirm_count or int(safe_float(flags.get("startup9_confirm_count", 0.0)))
    adx = flags.get("adx") if "adx" in flags else flags.get("ADX")
    reason = str(candidate.startup9_confirm_reason or candidate.reason or flags.get("startup9_confirm_reason") or "-")
    reason_hits = " + ".join(hits[:3]) if hits else reason
    return "\n".join(
        [
            (
                f"#{candidate.rank} {candidate.ticker}"
                f" | S9 {int(count)}/9 {grade}"
                f" | Vol20 {_ratio(candidate.volume_ratio_20, 2)}"
                f" | ADX {_number(adx, 1)}"
            ),
            f"   근거: {reason_hits}",
            f"   주의: {risk}",
        ]
    )


def _format_steady_winner_candidate_line(candidate: TelegramCandidate) -> str:
    risk = "+".join(list(candidate.risk_flags or [])) or "-"
    return "\n".join(
        [
            (
                f"{candidate.rank}. {candidate.ticker}"
                f" | PUL {safe_float(candidate.pul_score):.0f}"
                f" | {str(candidate.bucket or candidate.label or '-')}"
                f" | {_signed(candidate.chg_pct, 2)}% / 5D {_signed(candidate.chg_5d, 2)}%"
                f" | {_ratio(candidate.volume_ratio_20, 2)}"
            ),
            f"   근거: {str(candidate.reason or '-')}",
            f"   진입유형: {str(candidate.entry_type or '-')}",
            f"   주의: {risk}",
        ]
    )


def _format_early_reversal_candidate_line(candidate: TelegramCandidate) -> str:
    risk = "+".join(list(candidate.risk_flags or [])) or "-"
    confirm = str(candidate.source_flags.get("reversal_confirm") or "20일고점/MA20 지지")
    return "\n".join(
        [
            (
                f"{candidate.rank}. {candidate.ticker}"
                f" | ERS {safe_float(candidate.early_reversal_score):.0f}"
                f" | {str(candidate.reversal_phase or candidate.bucket or '-')}"
                f" | {str(candidate.reversal_type or '-')}"
                f" | {_signed(candidate.chg_pct, 2)}% / 5D {_signed(candidate.chg_5d, 2)}%"
                f" | {_ratio(candidate.volume_ratio_20, 2)}"
            ),
            f"   근거: {str(candidate.reason or '-')}",
            f"   진입유형: {str(candidate.entry_type or '-')}",
            f"   확인: {confirm}",
            f"   주의: {risk}",
        ]
    )


def _format_hull_buy_turn_candidate_line(candidate: TelegramCandidate) -> str:
    risk = "+".join(list(candidate.risk_flags or [])) or "-"
    confirm = str(candidate.source_flags.get("hull_confirm") or "HULL D+0")
    return "\n".join(
        [
            (
                f"{candidate.rank}. {candidate.ticker}"
                f" | HULL BUY"
                f" | {_signed(candidate.chg_pct, 2)}% / 5D {_signed(candidate.chg_5d, 2)}%"
                f" | {_ratio(candidate.volume_ratio_20, 2)}"
                f" | RS {_number((candidate.source_flags or {}).get('rs_rank_vs_index'), 0)}"
            ),
            f"   근거: {str(candidate.reason or '-')}",
            f"   확인: {confirm}",
            f"   주의: {risk}",
        ]
    )


def _qbs_section_block(display_number: str, section: TelegramSection) -> str:
    lines = [f"## {display_number}. {section.title}"]
    if not section.items:
        lines.append("- 해당 없음")
        return "\n".join(lines)
    for item in section.items:
        lines.append(_format_qbs_candidate_line(item))
    return "\n".join(lines)


def _aggressive_section_block(section: TelegramSection) -> str:
    section_limit = AGGRESSIVE_FIVE_DAY_TOP_LIMIT if section.key == AGGRESSIVE_NEXT_DAY_SECTION_KEYS[-1] else AGGRESSIVE_NEXT_DAY_LIMIT
    descriptor = f"Top {min(section.item_count, section_limit)}"
    title = str(section.title or section.key)
    if section.key in AGGRESSIVE_NEXT_DAY_SECTION_KEYS:
        part_number = AGGRESSIVE_NEXT_DAY_SECTION_KEYS.index(section.key) + 1
        prefix = f"PART {part_number}"
        if title.startswith(prefix):
            title = title[len(prefix):].lstrip(" .")
        title = f"PART {part_number}. {title}"
    lines = [f"## {title} ({descriptor})"]
    if section.quality_floor:
        lines.append(f"조건: {section.quality_floor}")
    if not section.items:
        lines.append("- ?대떦 ?놁쓬")
        return "\n".join(lines)
    for item in section.items:
        lines.append(_format_aggressive_candidate_line(item))
    return "\n".join(lines)


def _technical_buy_section_block(section: TelegramSection) -> str:
    lines = [f"## {TECHNICAL_BUY_DISPLAY_NUMBER}. {section.title}"]
    if section.quality_floor:
        lines.append(f"조건: {section.quality_floor}")
    if not section.items:
        lines.append("- 해당 없음")
        return "\n".join(lines)
    for item in section.items:
        lines.append(_format_technical_buy_candidate_line(item))
    return "\n".join(lines)


def _startup9_section_block(section: TelegramSection) -> str:
    lines = [f"## {STARTUP9_CONFIRM_DISPLAY_NUMBER}. {section.title}"]
    if section.quality_floor:
        lines.append(f"조건: {section.quality_floor}")
    if not section.items:
        lines.append("- 해당 없음")
        return "\n".join(lines)
    for item in section.items:
        lines.append(_format_startup9_candidate_line(item))
    return "\n".join(lines)


def _steady_winner_section_block(section: TelegramSection) -> str:
    lines = [f"## {STEADY_WINNER_DISPLAY_NUMBER}. {section.title}"]
    if not section.items:
        lines.append("- 해당 없음")
        return "\n".join(lines)
    for item in section.items:
        lines.append(_format_steady_winner_candidate_line(item))
    return "\n".join(lines)


def _early_reversal_section_block(section: TelegramSection) -> str:
    lines = [f"## {EARLY_REVERSAL_DISPLAY_NUMBER}. {section.title}"]
    if not section.items:
        lines.append("- 해당 없음")
        return "\n".join(lines)
    for item in section.items:
        lines.append(_format_early_reversal_candidate_line(item))
    return "\n".join(lines)


def _hull_buy_turn_section_block(section: TelegramSection) -> str:
    lines = [f"## {HULL_BUY_TURN_DISPLAY_NUMBER}. {section.title}"]
    if not section.items:
        lines.append("- 해당 없음")
        return "\n".join(lines)
    for item in section.items:
        lines.append(_format_hull_buy_turn_candidate_line(item))
    return "\n".join(lines)


def _section_block(index: int | str, section: TelegramSection) -> str:
    section_limit = FIVE_DAY_TOP_LIMIT if section.key == FIVE_DAY_TOP_SECTION_KEY else BOARD_SECTION_LIMIT
    descriptor = f"Top {min(section.item_count, section_limit)}"
    lines = [f"## {index}. {section.title} ({descriptor})"]
    if not section.items:
        lines.append("- 해당 없음")
        return "\n".join(lines)
    if section.key == FIVE_DAY_TOP_SECTION_KEY:
        lines.append("티커 | 5일 상승률 | RSI | Vol20 | MA20이격 | 상태")
        for item in section.items:
            lines.append(_format_five_day_candidate_line(item))
        return "\n".join(lines)
    for item in section.items:
        lines.append(_format_candidate_line(item))
    return "\n".join(lines)


MESSAGE_GROUP_HEADERS: dict[str, str] = {
    "decision": "[0] 오늘 의사결정 핵심",
    "startup9": "[1] Startup식 9개 강세확인 Top 20",
    "technical": "[2] 기술적 매수시그널 클러스터",
    "aggressive": "[3] 다음 거래일 공격형 매수 후보 10-PART",
    "board": "[4] 매매 유형별 후보 보드",
    "reference": "[5] 참고 랭킹",
}
MESSAGE_GROUP_DIVIDER = "━━━━━━━━━━━━━━━━━━━━"


def _message_group_for_section(section_key: str) -> str:
    if section_key in QBS_DISPLAY_NUMBERS or section_key in {STEADY_WINNER_SECTION_KEY, EARLY_REVERSAL_KEY, HULL_BUY_TURN_KEY}:
        return "decision"
    if section_key == STARTUP9_CONFIRM_KEY:
        return "startup9"
    if section_key == TECHNICAL_BUY_CLUSTER_KEY:
        return "technical"
    if section_key in AGGRESSIVE_SECTION_KEYS:
        return "aggressive"
    if section_key in BOARD_SECTION_KEYS:
        return "board"
    if section_key == FIVE_DAY_TOP_SECTION_KEY:
        return "reference"
    return ""


def _group_header(group_key: str) -> str:
    title = MESSAGE_GROUP_HEADERS.get(group_key, "")
    if not title:
        return ""
    return "\n".join([MESSAGE_GROUP_DIVIDER, title, MESSAGE_GROUP_DIVIDER])


def _ordered_digest_sections(digest: TelegramDigest) -> list[TelegramSection]:
    if not digest.section_order:
        return list(digest.sections or [])
    order_index = {str(key): idx for idx, key in enumerate(digest.section_order)}
    return sorted(
        list(digest.sections or []),
        key=lambda section: (order_index.get(str(section.key), len(order_index)), str(section.key)),
    )


def build_main_message(digest: TelegramDigest) -> str:
    blocks = [
        "\n".join(
            [
                "[오늘 종목판]",
                f"- 시장일: {digest.market_date} (US)",
                f"- 유니버스: {digest.universe_count} | 결과: {digest.result_count} | 제외: {digest.skip_count}",
                f"- 생성: {digest.generated_at}",
            ]
        )
    ]

    last_group = ""
    fallback_display_index = 12
    for section in _ordered_digest_sections(digest):
        if section.key not in BOARD_MANDATORY_SECTION_KEYS and section.item_count <= 0 and section.key not in {
            *QBS_DISPLAY_NUMBERS.keys(),
            STARTUP9_CONFIRM_KEY,
            TECHNICAL_BUY_CLUSTER_KEY,
            *AGGRESSIVE_SECTION_KEYS,
            STEADY_WINNER_SECTION_KEY,
            EARLY_REVERSAL_KEY,
            HULL_BUY_TURN_KEY,
        }:
            continue
        group_key = _message_group_for_section(section.key)
        if group_key and group_key != last_group:
            header = _group_header(group_key)
            if header:
                blocks.append(header)
            last_group = group_key
        if section.key in QBS_DISPLAY_NUMBERS:
            blocks.append(_qbs_section_block(QBS_DISPLAY_NUMBERS[section.key], section))
            continue
        if section.key == STARTUP9_CONFIRM_KEY:
            blocks.append(_startup9_section_block(section))
            continue
        if section.key == TECHNICAL_BUY_CLUSTER_KEY:
            blocks.append(_technical_buy_section_block(section))
            continue
        if section.key in AGGRESSIVE_SECTION_KEYS:
            blocks.append(_aggressive_section_block(section))
            continue
        if section.key == STEADY_WINNER_SECTION_KEY:
            blocks.append(_steady_winner_section_block(section))
            continue
        if section.key == EARLY_REVERSAL_KEY:
            blocks.append(_early_reversal_section_block(section))
            continue
        if section.key == HULL_BUY_TURN_KEY:
            blocks.append(_hull_buy_turn_section_block(section))
            continue
        display_number = BOARD_DISPLAY_NUMBERS.get(section.key)
        if section.key == FIVE_DAY_TOP_SECTION_KEY:
            display_number = FIVE_DAY_TOP_DISPLAY_NUMBER
        if display_number is None:
            display_number = str(fallback_display_index)
            fallback_display_index += 1
        blocks.append(_section_block(display_number, section))

    return "\n\n".join(blocks)


def build_post_close_message_texts(digest: TelegramDigest) -> list[str]:
    return [build_main_message(digest)]
