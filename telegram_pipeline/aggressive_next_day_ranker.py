from __future__ import annotations

from datetime import date
from typing import Any, Callable, Iterable, Mapping

from .rankers import is_truthy, safe_float, same_session_sell_turn

AGGRESSIVE_NEXT_DAY_LIMIT = 20

AGGRESSIVE_PART_1_KEY = "aggressive_initial_turn"
AGGRESSIVE_PART_2_KEY = "aggressive_strong_trend"
AGGRESSIVE_PART_3_KEY = "aggressive_pullback_reentry"
AGGRESSIVE_PART_4_KEY = "aggressive_high_vol_satellite"
AGGRESSIVE_PART_5_KEY = "aggressive_pocket_pivot_volume"
AGGRESSIVE_PART_6_KEY = "aggressive_compression_launch"
AGGRESSIVE_PART_7_KEY = "aggressive_gap_chase"
AGGRESSIVE_PART_8_KEY = "aggressive_near_high_breakout"

AGGRESSIVE_NEXT_DAY_SECTION_KEYS: tuple[str, ...] = (
    AGGRESSIVE_PART_1_KEY,
    AGGRESSIVE_PART_2_KEY,
    AGGRESSIVE_PART_3_KEY,
    AGGRESSIVE_PART_4_KEY,
    AGGRESSIVE_PART_5_KEY,
    AGGRESSIVE_PART_6_KEY,
    AGGRESSIVE_PART_7_KEY,
    AGGRESSIVE_PART_8_KEY,
)

AGGRESSIVE_NEXT_DAY_SECTION_TITLES: dict[str, str] = {
    AGGRESSIVE_PART_1_KEY: "PART 1 초기 전환형",
    AGGRESSIVE_PART_2_KEY: "PART 2 강추세 지속형",
    AGGRESSIVE_PART_3_KEY: "PART 3 눌림목 재진입형",
    AGGRESSIVE_PART_4_KEY: "PART 4 초고변동 위성형",
    AGGRESSIVE_PART_5_KEY: "PART 5 포켓피봇 / 거래량 선행형",
    AGGRESSIVE_PART_6_KEY: "PART 6 압축 후 발사 대기형",
    AGGRESSIVE_PART_7_KEY: "PART 7 갭업 후 실패 없는 추격형",
    AGGRESSIVE_PART_8_KEY: "PART 8 신고가 근처 돌파 대기형",
}

AGGRESSIVE_NEXT_DAY_QUALITY_FLOORS: dict[str, str] = {
    AGGRESSIVE_PART_1_KEY: (
        "공통필터 + UTBot/HULL D+3 이내/MA20 재탈환/higher-low 중 1개 + "
        "5D -8~+15%, MA20 -5~+10%, Z<=2.1, %B<=1.08 + CMF/OBV/거래량 확인"
    ),
    AGGRESSIVE_PART_2_KEY: (
        "공통필터 + ATR>=4, 상승추세, ADX>=25, HMA20/60 상승 + "
        "RS>=85 또는 Ret20Pctile>=90 + 5D>=8%, Ret20>=15% + 거래량/CMF/OBV"
    ),
    AGGRESSIVE_PART_3_KEY: (
        "공통필터 + 상승추세, RS>=55 + 눌림/재진입/higher-low + "
        "20D 고점 -12~-0.8% 또는 swing -15~-2%, MA20 -6~+8%, 0.2~3.5 ATR 눌림"
    ),
    AGGRESSIVE_PART_4_KEY: (
        "공통필터 + ATR>=8 또는 ATR>=6+큰 변동 + 양봉 + Vol20>=1.2/확장 + "
        "CMF/OBV 양호 + RS>=70 또는 Ret20Pctile>=75"
    ),
    AGGRESSIVE_PART_5_KEY: (
        "공통필터 + 포켓피봇 candidate/recent/D+5 또는 Vol20>=1.5+OBV/CMF + "
        "MA20 -8~+25%, ATR 필터 + 추세/RS/수익률 확인"
    ),
    AGGRESSIVE_PART_6_KEY: (
        "공통필터 + NR7/Inside/3WT/ATR수축/거래량건조 중 2개 + "
        "%B 0.35~0.95, MA20 -6~+8%, 20D 고점 -10~-0.5%, RS>=50, 당일 +8% 미만"
    ),
    AGGRESSIVE_PART_7_KEY: (
        "공통필터 + 갭 추정 + 당일 +3~+20%, VWAP 위, Vol20>=1.0 + "
        "20D/52W 고점 근처 + BB상단 이탈 없음 + CMF/OBV 양호"
    ),
    AGGRESSIVE_PART_8_KEY: (
        "공통필터 + 52W/20D 고점 3% 이내 + RS>=75 또는 Ret20Pctile>=80 + "
        "HMA20/60 양호 + Vol20>=0.8 또는 dry-up + 당일 <=12%, MA20<=25%"
    ),
}

_Selector = Callable[[Mapping[str, Any], date], bool]
_SortKey = Callable[[Mapping[str, Any]], tuple[Any, ...]]


def _ticker(row: Mapping[str, Any]) -> str:
    return str(row.get("ticker") or "").strip().upper()


def _unique_append(values: list[str], value: str) -> None:
    text = str(value or "").strip()
    if text and text not in values:
        values.append(text)


def _number(row: Mapping[str, Any], *keys: str, default: float = 0.0) -> float:
    for key in keys:
        if key in row and row.get(key) is not None:
            return safe_float(row.get(key), default)
    return default


def _is_common_eligible(row: Mapping[str, Any], target_date: date) -> bool:
    if not _ticker(row):
        return False
    if _number(row, "atr_pct") < 3.0:
        return False
    if _number(row, "dollar_volume_20") < 20_000_000.0:
        return False
    if is_truthy(row.get("thin_trade_risk")):
        return False
    if is_truthy(row.get("bearish_gap_failure")) or is_truthy(row.get("bearish_gap_failure__2")):
        return False
    if same_session_sell_turn(row, target_date):
        return False
    if is_truthy(row.get("utbot_sell_recent")) or is_truthy(row.get("hull_turn_bear_recent")):
        return False
    if is_truthy(row.get("hma_ema_short_entry")) or is_truthy(row.get("hma25_ema25_cross_bear")):
        return False
    return True


def _is_uptrend(row: Mapping[str, Any]) -> bool:
    return bool(
        is_truthy(row.get("uptrend_persistent"))
        or is_truthy(row.get("hma_ema_long_aligned"))
        or str(row.get("weekly_trend_context") or "").strip().upper() == "STRONG_UPTREND"
    )


def _has_turn_trigger(row: Mapping[str, Any]) -> bool:
    return bool(
        is_truthy(row.get("latest_session_utbot_buy_turn"))
        or is_truthy(row.get("latest_session_hull_buy_turn"))
        or _number(row, "days_since_utbot_buy", default=999.0) <= 3.0
        or _number(row, "days_since_hull_turn_bull", default=999.0) <= 3.0
        or is_truthy(row.get("first_close_above_ma20_after_5bars"))
        or is_truthy(row.get("first_higher_low_pivot2"))
    )


def _flow_ok(row: Mapping[str, Any]) -> bool:
    return bool(
        _number(row, "cmf") >= 0.0
        or _number(row, "obv_slope") > 0.0
        or _number(row, "volume_ratio_20") >= 1.5
    )


def _strong_flow_ok(row: Mapping[str, Any]) -> bool:
    return bool(
        _number(row, "volume_ratio_20") >= 1.0
        or (_number(row, "obv_slope") > 0.2 and _number(row, "cmf") > 0.05)
    )


def _relative_strength_ok(row: Mapping[str, Any], *, rs: float, ret20_percentile: float) -> bool:
    return bool(_number(row, "rs_rank_vs_index") >= rs or _number(row, "ret20_percentile") >= ret20_percentile)


def _compression_count(row: Mapping[str, Any]) -> int:
    return int(
        sum(
            [
                is_truthy(row.get("nr7_flag")),
                is_truthy(row.get("inside_day_flag")),
                is_truthy(row.get("three_weeks_tight")),
                is_truthy(row.get("atr_contracting")),
                _number(row, "volume_dry_up_score") >= 10.0,
                _number(row, "volume_dry_up_score_3") >= 10.0,
                _number(row, "volume_dry_up_score_5") >= 10.0,
                _number(row, "volume_dry_up_score_10") >= 10.0,
            ]
        )
    )


def _near_high(row: Mapping[str, Any]) -> bool:
    return bool(
        is_truthy(row.get("near_52w_high_2pct"))
        or _number(row, "drawdown_from_52w_high_pct", default=-999.0) >= -3.0
        or -3.0 <= _number(row, "breakout_dist_20d_high_pct", default=-999.0) <= 0.5
    )


def _part_1(row: Mapping[str, Any], target_date: date) -> bool:
    if not _is_common_eligible(row, target_date):
        return False
    if not _has_turn_trigger(row):
        return False
    if not _flow_ok(row):
        return False
    if not (
        _number(row, "rs_rank_vs_index") >= 50.0
        or _number(row, "ret20_percentile") >= 60.0
        or _number(row, "volume_ratio_20") >= 1.5
    ):
        return False
    return bool(
        -8.0 <= _number(row, "chg_5d") <= 15.0
        and -5.0 <= _number(row, "dist_sma20_pct", "ma20_dist_pct") <= 10.0
        and _number(row, "zscore20") <= 2.1
        and _number(row, "bb_percent_b") <= 1.08
    )


def _part_2(row: Mapping[str, Any], target_date: date) -> bool:
    if not _is_common_eligible(row, target_date):
        return False
    return bool(
        _number(row, "atr_pct") >= 4.0
        and _is_uptrend(row)
        and (
            is_truthy(row.get("bull_strength_recent"))
            or is_truthy(row.get("strong_trend_persistent"))
            or _number(row, "ret20_percentile") >= 90.0
        )
        and _number(row, "adx") >= 25.0
        and _number(row, "hma20_slope_pct") >= 0.8
        and _number(row, "hma60_slope_pct") >= 0.5
        and _relative_strength_ok(row, rs=85.0, ret20_percentile=90.0)
        and _number(row, "chg_5d") >= 8.0
        and _number(row, "ret20_pct") >= 15.0
        and _strong_flow_ok(row)
    )


def _part_3(row: Mapping[str, Any], target_date: date) -> bool:
    if not _is_common_eligible(row, target_date):
        return False
    pullback_zone = (
        -12.0 <= _number(row, "drawdown_from_20d_high_pct") <= -0.8
        or -15.0 <= _number(row, "pullback_from_swing_high_pct") <= -2.0
    )
    return bool(
        _is_uptrend(row)
        and _number(row, "rs_rank_vs_index") >= 55.0
        and _number(row, "hma60_slope_pct") > 0.0
        and (
            is_truthy(row.get("pullback_ready"))
            or is_truthy(row.get("pullback_reentry"))
            or is_truthy(row.get("first_higher_low_pivot2"))
        )
        and pullback_zone
        and -6.0 <= _number(row, "dist_sma20_pct", "ma20_dist_pct") <= 8.0
        and 0.2 <= _number(row, "pullback_atr_multiple") <= 3.5
        and (_number(row, "volume_dry_up_score") >= 5.0 or _number(row, "volume_ratio_20") <= 1.1)
        and (_number(row, "obv_slope") >= 0.0 or _number(row, "cmf") >= 0.0)
        and _number(row, "chg_5d") <= 15.0
    )


def _part_4(row: Mapping[str, Any], target_date: date) -> bool:
    if not _is_common_eligible(row, target_date):
        return False
    high_volatility = _number(row, "atr_pct") >= 8.0 or (
        _number(row, "atr_pct") >= 6.0
        and (abs(_number(row, "chg")) >= 7.0 or _number(row, "chg_5d") >= 15.0)
    )
    return bool(
        high_volatility
        and _number(row, "chg") > 0.0
        and (_number(row, "volume_ratio_20") >= 1.2 or _number(row, "volume_expansion_score") >= 25.0)
        and (_number(row, "obv_slope") > 0.0 or _number(row, "cmf") > 0.0)
        and _relative_strength_ok(row, rs=70.0, ret20_percentile=75.0)
    )


def _part_5(row: Mapping[str, Any], target_date: date) -> bool:
    if not _is_common_eligible(row, target_date):
        return False
    pocket_pivot = bool(
        is_truthy(row.get("pocket_pivot_candidate"))
        or is_truthy(row.get("pocket_pivot_recent"))
        or _number(row, "days_since_pocket_pivot", default=999.0) <= 5.0
    )
    volume_lead = bool(
        _number(row, "volume_ratio_20") >= 1.5
        and _number(row, "obv_slope") > 0.2
        and _number(row, "cmf") > 0.05
    )
    return bool(
        (pocket_pivot or volume_lead)
        and (_number(row, "volume_ratio_20") >= 1.0 or _number(row, "volume_expansion_score") >= 20.0 or pocket_pivot)
        and _number(row, "obv_slope") >= 0.0
        and _number(row, "cmf") >= 0.0
        and -8.0 <= _number(row, "dist_sma20_pct", "ma20_dist_pct") <= 25.0
        and (_is_uptrend(row) or _number(row, "rs_rank_vs_index") >= 55.0 or _number(row, "ret20_percentile") >= 70.0)
    )


def _part_6(row: Mapping[str, Any], target_date: date) -> bool:
    if not _is_common_eligible(row, target_date):
        return False
    return bool(
        _number(row, "rs_rank_vs_index") >= 50.0
        and _compression_count(row) >= 2
        and 0.35 <= _number(row, "bb_percent_b") <= 0.95
        and -6.0 <= _number(row, "dist_sma20_pct", "ma20_dist_pct") <= 8.0
        and (
            -10.0 <= _number(row, "drawdown_from_20d_high_pct") <= -0.5
            or -8.0 <= _number(row, "breakout_dist_20d_high_pct") <= -0.5
        )
        and (_number(row, "cmf") >= 0.0 or _number(row, "obv_slope") >= 0.0)
        and _number(row, "chg") < 8.0
    )


def _part_7(row: Mapping[str, Any], target_date: date) -> bool:
    if not _is_common_eligible(row, target_date):
        return False
    gap_estimated = is_truthy(row.get("gap_risk_2pct")) or is_truthy(row.get("gap_risk_atr"))
    return bool(
        gap_estimated
        and 3.0 <= _number(row, "chg") <= 20.0
        and _number(row, "dist_vwap_pct") > 0.0
        and _number(row, "volume_ratio_20") >= 1.0
        and (_number(row, "breakout_dist_20d_high_pct") >= -2.0 or is_truthy(row.get("near_52w_high_2pct")))
        and _number(row, "dist_bb_upper_pct") >= -3.0
        and (_number(row, "cmf") > 0.0 or _number(row, "obv_slope") > 0.0)
    )


def _part_8(row: Mapping[str, Any], target_date: date) -> bool:
    if not _is_common_eligible(row, target_date):
        return False
    return bool(
        _near_high(row)
        and _relative_strength_ok(row, rs=75.0, ret20_percentile=80.0)
        and _number(row, "hma20_slope_pct") > 0.0
        and _number(row, "hma60_slope_pct") >= 0.0
        and (_number(row, "volume_ratio_20") >= 0.8 or _number(row, "volume_dry_up_score") >= 5.0)
        and _number(row, "chg") <= 12.0
        and _number(row, "dist_sma20_pct", "ma20_dist_pct") <= 25.0
    )


def _sort_part_1(row: Mapping[str, Any]) -> tuple[Any, ...]:
    turn_count = int(is_truthy(row.get("latest_session_utbot_buy_turn"))) + int(is_truthy(row.get("latest_session_hull_buy_turn")))
    return (
        -turn_count,
        -int(is_truthy(row.get("first_close_above_ma20_after_5bars"))),
        -_number(row, "rs_rank_vs_index"),
        -_number(row, "volume_ratio_20"),
        -_number(row, "atr_pct"),
        _ticker(row),
    )


def _sort_part_2(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        -_number(row, "rs_rank_vs_index"),
        -_number(row, "ret20_percentile"),
        -_number(row, "adx"),
        -(_number(row, "hma20_slope_pct") + _number(row, "hma60_slope_pct")),
        -_number(row, "chg_5d"),
        -_number(row, "volume_ratio_20"),
        _ticker(row),
    )


def _sort_part_3(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        -int(is_truthy(row.get("pullback_reentry"))),
        -_number(row, "rs_rank_vs_index"),
        abs(_number(row, "dist_sma20_pct", "ma20_dist_pct")),
        -_number(row, "volume_dry_up_score"),
        _ticker(row),
    )


def _sort_part_4(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        -_number(row, "atr_pct"),
        -_number(row, "volume_expansion_score"),
        -_number(row, "chg_5d"),
        -_number(row, "chg"),
        -_number(row, "rs_rank_vs_index"),
        _ticker(row),
    )


def _sort_part_5(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        -int(is_truthy(row.get("pocket_pivot_candidate"))),
        _number(row, "days_since_pocket_pivot", default=999.0),
        -_number(row, "pocket_pivot_gate_count"),
        -_number(row, "volume_ratio_20"),
        -_number(row, "obv_slope"),
        -_number(row, "cmf"),
        -_number(row, "rs_rank_vs_index"),
        _ticker(row),
    )


def _sort_part_6(row: Mapping[str, Any]) -> tuple[Any, ...]:
    dry_up = max(
        _number(row, "volume_dry_up_score"),
        _number(row, "volume_dry_up_score_3"),
        _number(row, "volume_dry_up_score_5"),
        _number(row, "volume_dry_up_score_10"),
    )
    return (
        -_compression_count(row),
        -_number(row, "rs_rank_vs_index"),
        -dry_up,
        abs(_number(row, "breakout_dist_20d_high_pct")),
        _ticker(row),
    )


def _sort_part_7(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        -_number(row, "chg"),
        -_number(row, "volume_ratio_20"),
        abs(_number(row, "breakout_dist_20d_high_pct")),
        -_number(row, "cmf"),
        -_number(row, "rs_rank_vs_index"),
        _ticker(row),
    )


def _sort_part_8(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        abs(_number(row, "breakout_dist_20d_high_pct")),
        -_number(row, "rs_rank_vs_index"),
        -_number(row, "ret20_percentile"),
        -_number(row, "volume_ratio_20"),
        _ticker(row),
    )


_SELECTORS: dict[str, _Selector] = {
    AGGRESSIVE_PART_1_KEY: _part_1,
    AGGRESSIVE_PART_2_KEY: _part_2,
    AGGRESSIVE_PART_3_KEY: _part_3,
    AGGRESSIVE_PART_4_KEY: _part_4,
    AGGRESSIVE_PART_5_KEY: _part_5,
    AGGRESSIVE_PART_6_KEY: _part_6,
    AGGRESSIVE_PART_7_KEY: _part_7,
    AGGRESSIVE_PART_8_KEY: _part_8,
}

_SORT_KEYS: dict[str, _SortKey] = {
    AGGRESSIVE_PART_1_KEY: _sort_part_1,
    AGGRESSIVE_PART_2_KEY: _sort_part_2,
    AGGRESSIVE_PART_3_KEY: _sort_part_3,
    AGGRESSIVE_PART_4_KEY: _sort_part_4,
    AGGRESSIVE_PART_5_KEY: _sort_part_5,
    AGGRESSIVE_PART_6_KEY: _sort_part_6,
    AGGRESSIVE_PART_7_KEY: _sort_part_7,
    AGGRESSIVE_PART_8_KEY: _sort_part_8,
}


def _aggressive_tags(row: Mapping[str, Any], section_key: str) -> list[str]:
    tags: list[str] = []
    if is_truthy(row.get("latest_session_utbot_buy_turn")) or _number(row, "days_since_utbot_buy", default=999.0) <= 3.0:
        _unique_append(tags, "UTBot")
    if is_truthy(row.get("latest_session_hull_buy_turn")) or _number(row, "days_since_hull_turn_bull", default=999.0) <= 3.0:
        _unique_append(tags, "HULL")
    if is_truthy(row.get("first_close_above_ma20_after_5bars")):
        _unique_append(tags, "MA20 reclaim")
    if is_truthy(row.get("first_higher_low_pivot2")):
        _unique_append(tags, "higher-low")
    if _is_uptrend(row):
        _unique_append(tags, "uptrend")
    if _number(row, "volume_ratio_20") >= 1.2:
        _unique_append(tags, "volume")
    if _number(row, "cmf") > 0.0:
        _unique_append(tags, "CMF+")
    if _number(row, "obv_slope") > 0.0:
        _unique_append(tags, "OBV+")
    if _compression_count(row) >= 2:
        _unique_append(tags, "compression")
    if _near_high(row):
        _unique_append(tags, "near-high")
    if section_key == AGGRESSIVE_PART_5_KEY and (
        is_truthy(row.get("pocket_pivot_candidate")) or is_truthy(row.get("pocket_pivot_recent"))
    ):
        _unique_append(tags, "pocket")
    if section_key == AGGRESSIVE_PART_7_KEY:
        _unique_append(tags, "gap")
    return tags[:6]


def _risk_flags(row: Mapping[str, Any], section_key: str) -> list[str]:
    flags: list[str] = []
    if _number(row, "volume_ratio_20") < 0.8:
        _unique_append(flags, "low_vol20")
    if _number(row, "zscore20") >= 2.7:
        _unique_append(flags, "hot_zscore")
    if _number(row, "dist_sma20_pct", "ma20_dist_pct") >= 25.0:
        _unique_append(flags, "ma20_extended")
    if _number(row, "chg") >= 12.0:
        _unique_append(flags, "extended_day")
    if _number(row, "chg_5d") >= 25.0:
        _unique_append(flags, "extended_5d")
    if section_key == AGGRESSIVE_PART_4_KEY:
        _unique_append(flags, "satellite_size")
    if section_key == AGGRESSIVE_PART_7_KEY:
        _unique_append(flags, "gap_chase")
    return flags


def _decorate(row: Mapping[str, Any], section_key: str) -> dict[str, Any]:
    row_dict = dict(row or {})
    row_dict["ticker"] = _ticker(row_dict)
    tags = _aggressive_tags(row_dict, section_key)
    risks = _risk_flags(row_dict, section_key)
    row_dict["aggressive_bucket"] = section_key
    row_dict["aggressive_label"] = AGGRESSIVE_NEXT_DAY_SECTION_TITLES.get(section_key, section_key)
    row_dict["aggressive_reason"] = "+".join(tags) if tags else "-"
    row_dict["aggressive_tags"] = tags
    row_dict["aggressive_risk_flags"] = risks
    row_dict["entry_type"] = str(row_dict.get("entry_type") or "aggressive_next_day_watch")
    row_dict["compression_count"] = _compression_count(row_dict)
    return row_dict


def _select_section(
    rows: Iterable[Mapping[str, Any]],
    *,
    section_key: str,
    target_date: date,
    limit: int,
) -> list[dict[str, Any]]:
    selector = _SELECTORS[section_key]
    sort_key = _SORT_KEYS[section_key]
    best_by_ticker: dict[str, dict[str, Any]] = {}
    for raw_row in rows or []:
        row = dict(raw_row or {})
        if not selector(row, target_date):
            continue
        decorated = _decorate(row, section_key)
        ticker = _ticker(decorated)
        if not ticker:
            continue
        existing = best_by_ticker.get(ticker)
        if existing is None or sort_key(decorated) < sort_key(existing):
            best_by_ticker[ticker] = decorated
    selected = list(best_by_ticker.values())
    selected.sort(key=sort_key)
    return selected[: max(0, int(limit or 0))]


def select_aggressive_next_day_sections(
    rows: Iterable[Mapping[str, Any]],
    *,
    target_date: date,
    limit: int = AGGRESSIVE_NEXT_DAY_LIMIT,
) -> dict[str, list[dict[str, Any]]]:
    row_list = [dict(row or {}) for row in (rows or [])]
    return {
        section_key: _select_section(row_list, section_key=section_key, target_date=target_date, limit=limit)
        for section_key in AGGRESSIVE_NEXT_DAY_SECTION_KEYS
    }
