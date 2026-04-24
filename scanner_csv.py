from __future__ import annotations

import csv
import io
from typing import Any, Callable, Iterable, Mapping

CORE_SIGNAL_GROUP: dict[str, dict[str, str]] = {
    "System_Turn_Bull": {"dir": "buy"},
    "System_Turn_Bear": {"dir": "sell"},
    "Trend_Inflection_Bull": {"dir": "buy"},
    "Trend_Inflection_Bear": {"dir": "sell"},
    "UTBot_Buy": {"dir": "buy"},
    "UTBot_Sell": {"dir": "sell"},
    "Hull_Turn_Bull": {"dir": "buy"},
    "Hull_Turn_Bear": {"dir": "sell"},
    "EMA_Pullback_Buy": {"dir": "buy"},
    "EMA_Pullback_Sell": {"dir": "sell"},
    "Volume_Surge": {"dir": "neutral"},
    "Volume_Climax_Buy": {"dir": "buy"},
    "Volume_Climax_Sell": {"dir": "sell"},
}

BOOL_TO_YN_KEYS: set[str] = {
    "volume_surge",
    "volume_abnormal",
    "volume_bullish",
    "thin_trade_risk",
    "bearish_gap_failure",
    "bull_turn_recent",
    "uptrend_or_pullback",
    "pullback_ready",
    "bull_strength_recent",
    "uptrend_persistent",
    "strong_trend_persistent",
    "pullback_reentry",
    "low_conflict_bullish",
    "utbot_buy_recent",
    "utbot_sell_recent",
    "hull_turn_bull_recent",
    "hull_turn_bear_recent",
    "latest_session_utbot_buy_turn",
    "latest_session_hull_buy_turn",
    "ichimoku_above_cloud",
    "ichimoku_below_cloud",
    "volume_climax_flag",
    "gap_risk_2pct",
    "gap_risk_atr",
    "first_close_above_ma20_after_5bars",
    "first_higher_low_pivot2",
    "first_higher_high_pivot2",
    "atr_contracting",
    "nr7_flag",
    "inside_day_flag",
    "three_weeks_tight",
    "tight_close_near_high_3d",
    "near_52w_high_2pct",
    "pocket_pivot_recent",
    "gap_setup_candidate",
    "pocket_pivot_candidate",
}

SCANNER_CSV_FIELD_SPECS: tuple[dict[str, str], ...] = (
    {"group": "기본", "key": "ticker", "label": "티커", "type": "text", "description": "스캔 대상 종목 코드", "rule": "유니버스 티커", "example": "AAPL"},
    {"group": "기본", "key": "price", "label": "현재가", "type": "number", "description": "최근 종가", "rule": "최신 봉 Close", "example": "182.34"},
    {"group": "기본", "key": "chg", "label": "등락률(%)", "type": "number", "description": "직전 봉 대비 변화율", "rule": "(현재가-직전가)/직전가*100", "example": "1.24"},
    {"group": "판단", "key": "scan_score", "label": "스캔점수", "type": "number", "description": "스캐너 랭킹 점수", "rule": "기존 scan_score 산식 유지", "example": "18.6"},
    {"group": "판단", "key": "strength", "label": "강도점수", "type": "number", "description": "신호 강도 보조 지표", "rule": "기존 strength 산식", "example": "22.1"},
    {"group": "판단", "key": "jg", "label": "판단라벨", "type": "text", "description": "현지화된 판단 라벨", "rule": "Trade_Judgment 현지화", "example": "매수"},
    {"group": "판단", "key": "jg_key", "label": "판단키", "type": "text", "description": "엔진 판단 원본 키", "rule": "Trade_Judgment 원본", "example": "WATCH_BUY"},
    {"group": "판단", "key": "action", "label": "액션라벨", "type": "text", "description": "현지화된 액션", "rule": "Action_Label 현지화", "example": "관망 매수"},
    {"group": "판단", "key": "es", "label": "ES", "type": "number", "description": "Ensemble Score", "rule": "Ensemble_Score", "example": "6.0"},
    {"group": "판단", "key": "cf", "label": "신뢰도(%)", "type": "number", "description": "판단 신뢰도", "rule": "Judgment_Confidence", "example": "74"},
    {"group": "판단", "key": "ctx", "label": "시장맥락", "type": "text", "description": "시장 컨텍스트 라벨", "rule": "Market_Context 현지화", "example": "중립"},
    {"group": "판단", "key": "latest_sig", "label": "최근시그널일", "type": "date", "description": "최근 콤보 시그널 발생일", "rule": "최근 5봉 콤보 기준", "example": "2026-04-14"},
    {"group": "전략", "key": "strategy_active_count", "label": "활성전략수", "type": "number", "description": "전략 엔진 활성 수", "rule": "strategy_summary.active_count", "example": "2"},
    {"group": "다중", "key": "multi_buy", "label": "멀티시그널매수수", "type": "number", "description": "최근 멀티 시그널 중 매수 개수", "rule": "최근 5봉 콤보 집계", "example": "3"},
    {"group": "다중", "key": "multi_sell", "label": "멀티시그널매도수", "type": "number", "description": "최근 멀티 시그널 중 매도 개수", "rule": "최근 5봉 콤보 집계", "example": "1"},
    {"group": "거래량", "key": "volume_ratio_20", "label": "거래량비율20", "type": "number", "description": "현재 거래량 / 20봉 평균 거래량", "rule": "Volume_Ratio_20", "example": "1.35"},
    {"group": "거래량", "key": "volume_ratio_50", "label": "거래량비율50", "type": "number", "description": "현재 거래량 / 50봉 평균 거래량", "rule": "Volume_Ratio_50", "example": "1.18"},
    {"group": "거래량", "key": "volume_oscillator", "label": "거래량오실레이터", "type": "number", "description": "거래량 모멘텀 지표", "rule": "Volume_Oscillator", "example": "4.7"},
    {"group": "거래량", "key": "dollar_volume_20", "label": "20일평균거래대금", "type": "number", "description": "20봉 평균 거래대금", "rule": "Dollar_Volume_20", "example": "145000000"},
    {"group": "거래량", "key": "volume_surge", "label": "거래량급증", "type": "bool", "description": "거래량 급증 여부", "rule": "Volume_Surge", "example": "Y"},
    {"group": "거래량", "key": "volume_abnormal", "label": "비정상거래량", "type": "bool", "description": "비정상 거래량 여부", "rule": "Volume_Surge or R20>=2.0", "example": "Y"},
    {"group": "거래량", "key": "volume_bullish", "label": "거래량동반강세", "type": "bool", "description": "강세와 거래량 동반 여부", "rule": "R20>=1.2 and (surge or climax or vol_osc>0)", "example": "N"},
    {"group": "거래량", "key": "thin_trade_risk", "label": "유동성주의", "type": "bool", "description": "얇은 거래대금 위험", "rule": "Thin_Trade_Risk", "example": "N"},
    {"group": "리스크", "key": "bearish_gap_failure", "label": "약세갭실패", "type": "bool", "description": "약세 갭 실패 경고", "rule": "Bearish_Gap_Failure", "example": "N"},
    {"group": "추세", "key": "bull_turn_recent", "label": "최근추세전환", "type": "bool", "description": "최근 5봉 내 추세전환 감지", "rule": "System/TrendInflection/UTBot/Hull", "example": "Y"},
    {"group": "추세", "key": "uptrend_or_pullback", "label": "우상향또는눌림", "type": "bool", "description": "우상향 구조 또는 눌림목 여부", "rule": "Close>MA20>MA50 or EMA_Pullback_Buy", "example": "Y"},
    {"group": "추세", "key": "pullback_ready", "label": "눌림목준비", "type": "bool", "description": "최근 눌림목 매수 신호", "rule": "EMA_Pullback_Buy 최근 5봉", "example": "N"},
    {"group": "추세", "key": "bull_strength_recent", "label": "최근강세발굴", "type": "bool", "description": "강세 발굴 프리셋 조건 충족", "rule": "WATCH_BUY+ and 전환/우상향 and 전략/콤보 and 거래량동반", "example": "Y"},
    {"group": "추세", "key": "uptrend_persistent", "label": "우상향지속", "type": "bool", "description": "구조형 우상향 지속 조건 충족", "rule": "Close>MA20>MA50 and MA20/MA50 비감소 and WATCH_BUY+ or LONG bias and 최근 약세전환 없음", "example": "Y"},
    {"group": "추세", "key": "strong_trend_persistent", "label": "강한추세지속", "type": "bool", "description": "품질 기준을 통과한 강한 추세 지속", "rule": "우상향지속 and ADX>=20 and ES>=8 and CF>=65 and 거래량동반강세 and 충돌LOW", "example": "N"},
    {"group": "추세", "key": "pullback_reentry", "label": "눌림목재진입", "type": "bool", "description": "추세 중 눌림목 재진입 후보", "rule": "우상향지속 and (눌림신호 or 추세/눌림 콤보) and 롱 풀백 전략 가시 and WATCH_BUY+", "example": "Y"},
    {"group": "추세", "key": "low_conflict_bullish", "label": "저충돌강세", "type": "bool", "description": "충돌/리스크 낮은 강세 필터", "rule": "WATCH_BUY+ and 충돌LOW and bias!=SHORT and multi_sell<=1 and thin_trade/flip_guard 없음", "example": "Y"},
    {"group": "전환", "key": "utbot_buy_recent", "label": "UTBot매수전환", "type": "bool", "description": "최근 5봉 내 UTBot 매수 전환", "rule": "UTBot_Buy", "example": "Y"},
    {"group": "전환", "key": "utbot_buy_last_date", "label": "UTBot매수전환일", "type": "date", "description": "UTBot 매수 전환 발생일", "rule": "최근 5봉 마지막 발생일", "example": "2026-04-14"},
    {"group": "전환", "key": "utbot_sell_recent", "label": "UTBot매도전환", "type": "bool", "description": "최근 5봉 내 UTBot 매도 전환", "rule": "UTBot_Sell", "example": "N"},
    {"group": "전환", "key": "utbot_sell_last_date", "label": "UTBot매도전환일", "type": "date", "description": "UTBot 매도 전환 발생일", "rule": "최근 5봉 마지막 발생일", "example": "없음"},
    {"group": "전환", "key": "hull_turn_bull_recent", "label": "Hull상승전환", "type": "bool", "description": "최근 5봉 내 Hull 상승 전환", "rule": "Hull_Turn_Bull", "example": "Y"},
    {"group": "전환", "key": "hull_turn_bull_last_date", "label": "Hull상승전환일", "type": "date", "description": "Hull 상승 전환 발생일", "rule": "최근 5봉 마지막 발생일", "example": "2026-04-13"},
    {"group": "전환", "key": "hull_turn_bear_recent", "label": "Hull하락전환", "type": "bool", "description": "최근 5봉 내 Hull 하락 전환", "rule": "Hull_Turn_Bear", "example": "N"},
    {"group": "전환", "key": "hull_turn_bear_last_date", "label": "Hull하락전환일", "type": "date", "description": "Hull 하락 전환 발생일", "rule": "최근 5봉 마지막 발생일", "example": "없음"},
    {"group": "탐지", "key": "detected_combo_count", "label": "탐지콤보수", "type": "number", "description": "최근 5봉 콤보 탐지 개수", "rule": "COMBINED_SCAN_REGISTRY", "example": "4"},
    {"group": "탐지", "key": "detected_combo_summary", "label": "탐지콤보요약", "type": "text", "description": "탐지된 콤보 요약", "rule": "라벨(YYYY-MM-DD) | ...", "example": "트렌드 풀백(2026-04-14)"},
    {"group": "탐지", "key": "detected_transition_count", "label": "탐지전환수", "type": "number", "description": "최근 5봉 전환 탐지 개수", "rule": "UTBot/Hull 전환", "example": "2"},
    {"group": "탐지", "key": "detected_transition_summary", "label": "탐지전환요약", "type": "text", "description": "탐지된 전환 요약", "rule": "라벨(YYYY-MM-DD) | ...", "example": "UTBot 전환↑(2026-04-14)"},
    {"group": "탐지", "key": "detected_core_count", "label": "탐지핵심수", "type": "number", "description": "최근 5봉 핵심 시그널 탐지 개수", "rule": "System/Trend/UTBot/Hull/EMA/Volume", "example": "3"},
    {"group": "탐지", "key": "detected_core_summary", "label": "탐지핵심요약", "type": "text", "description": "탐지된 핵심 시그널 요약", "rule": "라벨(YYYY-MM-DD) | ...", "example": "초기 강세 전환(2026-04-14)"},
    {"group": "탐지", "key": "detected_signal_total_count", "label": "탐지시그널총수", "type": "number", "description": "탐지 시그널 총개수", "rule": "combo/transition/core 전체", "example": "9"},
    {"group": "탐지", "key": "detected_buy_signal_latest_date", "label": "매수탐지최근일", "type": "date", "description": "매수 방향 탐지 시그널 중 가장 최근 날짜", "rule": "최근 5봉 기준 direction=buy", "example": "2026-04-14"},
    {"group": "탐지", "key": "detected_signal_latest_date", "label": "탐지최근일", "type": "date", "description": "탐지 시그널 중 가장 최근 날짜", "rule": "최근 5봉 기준", "example": "2026-04-14"},
)


def scanner_csv_field_specs() -> tuple[dict[str, str], ...]:
    return SCANNER_CSV_FIELD_SPECS


def _to_bool_series(series: Any) -> Any:
    try:
        return series.fillna(False).astype(bool)
    except Exception:
        try:
            return series.fillna(False)
        except Exception:
            return series


def _recent_true_index(frame: Any, key: str, window: int) -> Any:
    if frame is None or key not in getattr(frame, "columns", []):
        return None
    series = _to_bool_series(frame[key].tail(window))
    try:
        if not bool(series.any()):
            return None
        return series[series].index[-1]
    except Exception:
        return None


def _safe_days_ago(as_of: Any, ts: Any) -> int:
    try:
        return int((as_of - ts).days)
    except Exception:
        return 0


def _fmt_date(ts: Any, fmt: str) -> str:
    try:
        return str(ts.strftime(fmt))
    except Exception:
        return str(ts)


def _build_item(*, group: str, key: str, label: str, direction: str, icon: str, ts: Any, as_of: Any, tier: int = 9) -> dict[str, Any]:
    return {
        "group": group,
        "key": key,
        "label": str(label),
        "dir": str(direction or "neutral"),
        "icon": str(icon or ""),
        "tier": int(tier),
        "date": _fmt_date(ts, "%Y-%m-%d"),
        "date_short": _fmt_date(ts, "%m/%d"),
        "days_ago": _safe_days_ago(as_of, ts),
    }


def summarize_detected_signal_items(items: Iterable[Mapping[str, Any]], *, limit: int = 8, empty_text: str = "없음") -> str:
    item_list = list(items or [])
    if not item_list:
        return empty_text
    shown = item_list[:limit]
    parts = [f"{str(item.get('label', '-')).strip()}({str(item.get('date', ''))})" for item in shown]
    remain = len(item_list) - len(shown)
    if remain > 0:
        parts.append(f"+{remain}개")
    return " | ".join(parts)


def build_detected_signal_payload(
    *,
    frame: Any,
    recent_window: int,
    combo_registry: Mapping[str, Mapping[str, Any]],
    transition_cfg: Mapping[str, Mapping[str, Any]],
    core_signal_cfg: Mapping[str, Mapping[str, Any]],
    localize_combo_fn: Callable[[str, Any, Any], tuple[str, str]],
    localize_signal_fn: Callable[[str, Any, Any], tuple[str, str]],
    summary_limit: int = 8,
) -> dict[str, Any]:
    if frame is None or len(frame) == 0:
        empty = {
            "combo_items": [],
            "transition_items": [],
            "core_items": [],
            "all_items": [],
            "detected_combo_count": 0,
            "detected_combo_summary": "없음",
            "detected_transition_count": 0,
            "detected_transition_summary": "없음",
            "detected_core_count": 0,
            "detected_core_summary": "없음",
            "detected_signal_total_count": 0,
            "detected_buy_signal_latest_date": "없음",
            "detected_signal_latest_date": "없음",
            "latest_combo_ts": None,
            "utbot_buy_recent": False,
            "utbot_buy_last_date": "없음",
            "utbot_sell_recent": False,
            "utbot_sell_last_date": "없음",
            "hull_turn_bull_recent": False,
            "hull_turn_bull_last_date": "없음",
            "hull_turn_bear_recent": False,
            "hull_turn_bear_last_date": "없음",
        }
        return empty

    as_of = frame.index[-1]

    combo_items: list[dict[str, Any]] = []
    latest_combo_ts = None
    for combo_key, cfg in combo_registry.items():
        ts = _recent_true_index(frame, str(combo_key), recent_window)
        if ts is None:
            continue
        label, _ = localize_combo_fn(str(combo_key), cfg.get("kor"), cfg.get("desc"))
        item = _build_item(
            group="combo",
            key=str(combo_key),
            label=label,
            direction=str(cfg.get("dir", "neutral")),
            icon=str(cfg.get("icon", "")),
            ts=ts,
            as_of=as_of,
            tier=int(cfg.get("tier", 9) or 9),
        )
        combo_items.append(item)
        if latest_combo_ts is None or ts > latest_combo_ts:
            latest_combo_ts = ts

    combo_items.sort(key=lambda item: (int(item.get("tier", 9)), int(item.get("days_ago", 99)), str(item.get("key", ""))))

    transition_items: list[dict[str, Any]] = []
    for signal_key, cfg in transition_cfg.items():
        ts = _recent_true_index(frame, str(signal_key), recent_window)
        if ts is None:
            continue
        transition_items.append(
            _build_item(
                group="transition",
                key=str(signal_key),
                label=str(cfg.get("label") or signal_key),
                direction=str(cfg.get("dir", "neutral")),
                icon=str(cfg.get("icon", "")),
                ts=ts,
                as_of=as_of,
            )
        )
    transition_items.sort(key=lambda item: (int(item.get("days_ago", 99)), str(item.get("key", ""))))

    core_items: list[dict[str, Any]] = []
    for signal_key, cfg in core_signal_cfg.items():
        ts = _recent_true_index(frame, str(signal_key), recent_window)
        if ts is None:
            continue
        label, _ = localize_signal_fn(str(signal_key), None, None)
        core_items.append(
            _build_item(
                group="core",
                key=str(signal_key),
                label=label,
                direction=str(cfg.get("dir", "neutral")),
                icon="",
                ts=ts,
                as_of=as_of,
            )
        )
    core_items.sort(key=lambda item: (int(item.get("days_ago", 99)), str(item.get("key", ""))))

    all_items = [*combo_items, *transition_items, *core_items]
    unique_pairs = {(str(item.get("key", "")), str(item.get("date", ""))) for item in all_items}
    latest_buy_date = max(
        (str(item.get("date", "")) for item in all_items if str(item.get("dir", "")).strip().lower() == "buy"),
        default="없음",
    )
    latest_date = max((str(item.get("date", "")) for item in all_items), default="없음")

    transition_map = {str(item.get("key")): item for item in transition_items}

    payload = {
        "combo_items": combo_items,
        "transition_items": transition_items,
        "core_items": core_items,
        "all_items": all_items,
        "detected_combo_count": len(combo_items),
        "detected_combo_summary": summarize_detected_signal_items(combo_items, limit=summary_limit),
        "detected_transition_count": len(transition_items),
        "detected_transition_summary": summarize_detected_signal_items(transition_items, limit=summary_limit),
        "detected_core_count": len(core_items),
        "detected_core_summary": summarize_detected_signal_items(core_items, limit=summary_limit),
        "detected_signal_total_count": len(unique_pairs),
        "detected_buy_signal_latest_date": latest_buy_date if latest_buy_date else "없음",
        "detected_signal_latest_date": latest_date if latest_date else "없음",
        "latest_combo_ts": latest_combo_ts,
        "utbot_buy_recent": "UTBot_Buy" in transition_map,
        "utbot_buy_last_date": str(transition_map.get("UTBot_Buy", {}).get("date") or "없음"),
        "utbot_sell_recent": "UTBot_Sell" in transition_map,
        "utbot_sell_last_date": str(transition_map.get("UTBot_Sell", {}).get("date") or "없음"),
        "hull_turn_bull_recent": "Hull_Turn_Bull" in transition_map,
        "hull_turn_bull_last_date": str(transition_map.get("Hull_Turn_Bull", {}).get("date") or "없음"),
        "hull_turn_bear_recent": "Hull_Turn_Bear" in transition_map,
        "hull_turn_bear_last_date": str(transition_map.get("Hull_Turn_Bear", {}).get("date") or "없음"),
    }
    return payload


def _column_header(spec: Mapping[str, str]) -> str:
    return f"{spec.get('label', '')}({spec.get('key', '')})"


def _normalized_csv_row(row: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(row or {})
    for key in BOOL_TO_YN_KEYS:
        normalized[key] = "Y" if bool(normalized.get(key)) else "N"
    for key in (
        "detected_combo_summary",
        "detected_transition_summary",
        "detected_core_summary",
        "utbot_buy_last_date",
        "utbot_sell_last_date",
        "hull_turn_bull_last_date",
        "hull_turn_bear_last_date",
        "system_turn_bull_last_date",
        "detected_buy_signal_latest_date",
        "detected_signal_latest_date",
    ):
        value = str(normalized.get(key) or "").strip()
        normalized[key] = value or "없음"
    return normalized


def scanner_rows_to_csv_bytes(
    rows: Iterable[Mapping[str, Any]],
    *,
    field_specs: Iterable[Mapping[str, str]] | None = None,
) -> bytes:
    specs = tuple(field_specs) if field_specs is not None else scanner_csv_field_specs()
    field_names = [str(spec["key"]) for spec in specs]

    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=field_names, extrasaction="ignore")
    writer.writerow({key: _column_header(spec) for key, spec in zip(field_names, specs)})

    for row in rows or []:
        normalized = _normalized_csv_row(row)
        writer.writerow({key: normalized.get(key, "") for key in field_names})

    return out.getvalue().encode("utf-8-sig")


def scanner_csv_dictionary_to_csv_bytes() -> bytes:
    out = io.StringIO()
    writer = csv.DictWriter(
        out,
        fieldnames=["그룹", "헤더표시명", "내부키", "값형식", "설명", "계산/판정기준", "예시"],
        extrasaction="ignore",
    )
    writer.writeheader()

    for spec in scanner_csv_field_specs():
        writer.writerow(
            {
                "그룹": spec.get("group", ""),
                "헤더표시명": _column_header(spec),
                "내부키": spec.get("key", ""),
                "값형식": spec.get("type", ""),
                "설명": spec.get("description", ""),
                "계산/판정기준": spec.get("rule", ""),
                "예시": spec.get("example", ""),
            }
        )

    return out.getvalue().encode("utf-8-sig")


def scanner_csv_help_lines() -> list[str]:
    return [
        "CSV 헤더 형식: 한글표시명(내부키)",
        "탐지 시그널 기준: 최근 5봉", 
        "탐지 그룹 combo: COMBINED_SCAN_REGISTRY에서 최근 5봉 true", 
        "탐지 그룹 transition: UT/Hull 전환(UTBot_Buy/Sell, Hull_Turn_Bull/Bear)",
        "탐지 그룹 core: System/TrendInflection/UTBot/Hull/EMA Pullback/Volume 신호",
        "요약 컬럼 형식: 라벨(YYYY-MM-DD) | ... , 최대 8개 이후 +N개",
    ]
