from __future__ import annotations

import numpy as np

from ..models import StrategyDefinition, StrategyResult
from ..risk import default_conflicts, risk_template_trend, trend_invalidation_text
from .common import build_result, build_result_from_groups, score_group, side


def evaluate_trend_pullback(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    trend = state["trend"]
    structure = state["structure"]
    volume_flow = state["volume_flow"]
    momentum = state["momentum"]
    patterns = state["patterns"]
    signals = state["signals"]

    setup_items = [
        (side(long_side, trend["ema21_above_ma50"] and trend["ema21_rising"], trend["ema21_below_ma50"] and trend["ema21_falling"]), "EMA21 / MA50 추세 정렬", 15),
        (side(long_side, trend["close_above_ema21"], trend["close_below_ema21"]), "가격이 EMA21 방향 위상 유지", 10),
        (side(long_side, structure["pullback_near_ema21_long"] or structure["pullback_near_ma20_long"] or structure["pullback_near_kc_mid_long"], structure["pullback_near_ema21_short"] or structure["pullback_near_ma20_short"] or structure["pullback_near_kc_mid_short"]), "눌림 구간 접근", 12),
        (side(long_side, trend["higher_high_recent"] or signals["CS_Trend_Continuation_Buy"], trend["lower_low_recent"] or signals["CS_Trend_Continuation_Sell"]), "최근 추세 재개 이력", 5),
        (side(long_side, volume_flow["volume_support"], volume_flow["volume_support"]), "거래량 바닥 이탈 없음", 3),
    ]
    trigger_items = [
        (side(long_side, signals["EMA_Pullback_Buy"] or patterns["bullish_reversal_candle"], signals["EMA_Pullback_Sell"] or patterns["bearish_reversal_candle"]), "눌림 뒤 방향 전환 캔들", 15),
        (side(long_side, signals["UTBot_Buy"] or signals["Hull_Turn_Bull"], signals["UTBot_Sell"] or signals["Hull_Turn_Bear"]), "보조 추세 신호 정렬", 10),
        (side(long_side, trend["psar_bullish"], trend["psar_bearish"]), "PSAR 추세 유지", 5),
        (side(long_side, momentum["macd_hist_rising"] and momentum["wt_rising"], momentum["macd_hist_falling"] and momentum["wt_falling"]), "모멘텀 재가속", 5),
    ]
    setup_score, setup_matched, setup_missing = score_group(setup_items)
    trigger_score, trigger_matched, trigger_missing = score_group(trigger_items)
    trigger_passed = trigger_score >= 20
    phase = "TRIGGERED" if trigger_passed else "PULLBACK_WAIT" if setup_score >= 25 else "SETUP_INVALID"
    stop_loss, target_1, target_2, rr = risk_template_trend(state, long_side)
    conflicts = default_conflicts(state, long_side)
    return build_result(
        definition=definition,
        state=state,
        long_side=long_side,
        family="trend_pullback",
        setup_score=setup_score,
        trigger_score=trigger_score,
        trigger_passed=trigger_passed,
        phase=phase,
        stop_loss=stop_loss,
        target_1=target_1,
        target_2=target_2,
        rr=rr,
        matched=setup_matched + trigger_matched,
        missing=setup_missing + trigger_missing,
        conflict_reasons=conflicts,
        invalidation_builder=trend_invalidation_text,
    )


def evaluate_supertrend_psar(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    trend = state["trend"]
    momentum = state["momentum"]
    signals = state["signals"]

    setup_items = [
        (side(long_side, trend["supertrend_bullish"], trend["supertrend_bearish"]), "SuperTrend 방향 일치", 15),
        (side(long_side, trend["psar_bullish"], trend["psar_bearish"]), "PSAR 방향 일치", 15),
        (side(long_side, trend["close_above_supertrend"] and trend["close_above_ema21"], trend["close_below_supertrend"] and trend["close_below_ema21"]), "가격이 추세 기준선 위상 유지", 10),
        (side(long_side, trend["adx_strong"] and trend["plus_di_dominant"], trend["adx_strong"] and trend["minus_di_dominant"]), "추세 강도 확인", 5),
    ]
    trigger_items = [
        (side(long_side, signals["SuperTrend_Buy"] or signals["CS_Triple_Confirm_Buy"], signals["SuperTrend_Sell"] or signals["CS_Triple_Confirm_Sell"]), "SuperTrend 전환 / 3중 확인", 15),
        (side(long_side, signals["UTBot_Buy"] or signals["Hull_Turn_Bull"], signals["UTBot_Sell"] or signals["Hull_Turn_Bear"]), "보조 추세 신호 정렬", 10),
        (side(long_side, momentum["macd_hist_rising"] or momentum["wt_rising"], momentum["macd_hist_falling"] or momentum["wt_falling"]), "모멘텀 동조화", 10),
    ]
    setup_score, setup_matched, setup_missing = score_group(setup_items)
    trigger_score, trigger_matched, trigger_missing = score_group(trigger_items)
    trigger_passed = trigger_score >= 15 and side(long_side, trend["supertrend_bullish"] and trend["psar_bullish"], trend["supertrend_bearish"] and trend["psar_bearish"])
    phase = "DOUBLE_CONFIRMED" if trigger_passed else "TREND_ALIGNED" if setup_score >= 20 else "SETUP_INVALID"
    stop_loss, target_1, target_2, rr = risk_template_trend(state, long_side)
    conflicts = default_conflicts(state, long_side)
    if side(long_side, not trend["psar_bullish"], not trend["psar_bearish"]):
        conflicts.append("PSAR 방향 전환이 아직 완전하지 않습니다.")
    return build_result(
        definition=definition,
        state=state,
        long_side=long_side,
        family="supertrend_psar",
        setup_score=setup_score,
        trigger_score=trigger_score,
        trigger_passed=trigger_passed,
        phase=phase,
        stop_loss=stop_loss,
        target_1=target_1,
        target_2=target_2,
        rr=rr,
        matched=setup_matched + trigger_matched,
        missing=setup_missing + trigger_missing,
        conflict_reasons=conflicts,
        invalidation_builder=trend_invalidation_text,
    )


def evaluate_keltner_pullback(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    trend = state["trend"]
    structure = state["structure"]
    volume_flow = state["volume_flow"]
    momentum = state["momentum"]
    patterns = state["patterns"]
    signals = state["signals"]

    setup_items = [
        (side(long_side, trend["ema21_above_ma50"] and trend["close_above_ma20"], trend["ema21_below_ma50"] and trend["close_below_ma20"]), "상위 추세와 Keltner 기준선 정렬", 15),
        (side(long_side, structure["pullback_near_kc_mid_long"], structure["pullback_near_kc_mid_short"]), "Keltner mid 눌림 구간 접근", 15),
        (side(long_side, trend["close_above_vwap"], trend["close_below_vwap"]), "VWAP 방향 우위 유지", 8),
        (side(long_side, volume_flow["volume_support"], volume_flow["volume_support"]), "눌림 중 거래량 지지", 7),
    ]
    trigger_items = [
        (side(long_side, signals["EMA_Pullback_Buy"] or patterns["bullish_reversal_candle"], signals["EMA_Pullback_Sell"] or patterns["bearish_reversal_candle"]), "Keltner 눌림 뒤 반전 캔들", 15),
        (side(long_side, signals["UTBot_Buy"] or signals["Hull_Turn_Bull"], signals["UTBot_Sell"] or signals["Hull_Turn_Bear"]), "보조 추세 신호 정렬", 10),
        (side(long_side, momentum["macd_hist_rising"], momentum["macd_hist_falling"]), "모멘텀 재확장", 10),
    ]
    return build_result_from_groups(
        definition,
        state,
        long_side,
        "keltner_pullback",
        setup_items,
        trigger_items,
        trigger_threshold=20,
        setup_threshold=20,
        triggered_phase="TRIGGERED",
        ready_phase="PULLBACK_WAIT",
        risk_template=risk_template_trend,
        invalidation_builder=trend_invalidation_text,
    )


def evaluate_anchored_vwap(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    trend = state["trend"]
    structure = state["structure"]
    volume_flow = state["volume_flow"]
    momentum = state["momentum"]
    patterns = state["patterns"]
    signals = state["signals"]

    setup_items = [
        (side(long_side, trend["fixed_vwap_holding_long"], trend["fixed_vwap_holding_short"]), "Anchored VWAP 방향 유지", 15),
        (side(long_side, structure["pullback_near_fixed_vwap_long"], structure["pullback_near_fixed_vwap_short"]), "AVWAP 리테스트 구간", 12),
        (side(long_side, trend["ema21_above_ma50"], trend["ema21_below_ma50"]), "상위 추세 정렬", 10),
        (side(long_side, volume_flow["volume_support"], volume_flow["volume_support"]), "거래량 바닥 붕괴 없음", 8),
    ]
    trigger_items = [
        (side(long_side, signals["VWAP_Bounce_Buy"] or patterns["bullish_reversal_candle"], signals["VWAP_Reject_Sell"] or patterns["bearish_reversal_candle"]), "AVWAP 반등 / 거절 캔들", 15),
        (side(long_side, trend["close_above_fixed_vwap"], trend["close_below_fixed_vwap"]), "종가 기준 AVWAP 유지", 10),
        (side(long_side, signals["UTBot_Buy"] or momentum["macd_hist_rising"], signals["UTBot_Sell"] or momentum["macd_hist_falling"]), "후속 추세 확인", 10),
    ]
    return build_result_from_groups(
        definition,
        state,
        long_side,
        "anchored_vwap",
        setup_items,
        trigger_items,
        trigger_threshold=20,
        setup_threshold=20,
        triggered_phase="AVWAP_CONFIRMED",
        ready_phase="AVWAP_HOLD",
        risk_template=risk_template_trend,
        invalidation_builder=trend_invalidation_text,
    )


def evaluate_accumulation_pattern(definition: StrategyDefinition, state: dict) -> StrategyResult:
    volume_flow = state["volume_flow"]
    structure = state["structure"]
    trend = state["trend"]
    momentum = state["momentum"]
    patterns = state["patterns"]
    signals = state["signals"]

    setup_items = [
        (signals["CS_Institutional_Accumulation"] or patterns["pocket_pivot"], "매집 유사 패턴 발생", 18),
        (volume_flow["obv_rising"] and volume_flow["cmf_positive"], "OBV / CMF 동반 개선", 12),
        (trend["close_above_ma50"] or structure["near_vp_poc"], "가격이 핵심 기준선 위 유지", 8),
        (trend["close_above_fixed_vwap"] or structure["pullback_near_fixed_vwap_long"], "AVWAP 방어", 7),
    ]
    trigger_items = [
        (patterns["pocket_pivot"] or signals["Volume_POC_Breakout"], "Pocket Pivot 또는 POC 돌파", 15),
        (volume_flow["volume_support"], "거래량 동반", 10),
        (momentum["macd_hist_rising"] or trend["close_above_vwap"], "초기 추세 확인", 10),
    ]
    return build_result_from_groups(
        definition,
        state,
        True,
        "accumulation_pattern",
        setup_items,
        trigger_items,
        trigger_threshold=18,
        setup_threshold=18,
        triggered_phase="ACCUMULATION_CONFIRMED",
        ready_phase="ACCUMULATION_READY",
        risk_template=risk_template_trend,
        invalidation_builder=trend_invalidation_text,
    )


def evaluate_fractal_alligator(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    trend = state["trend"]
    structure = state["structure"]
    volume_flow = state["volume_flow"]
    momentum = state["momentum"]
    signals = state["signals"]
    patterns = state["patterns"]

    setup_items = [
        (side(long_side, trend["close_above_ema21"] and trend["ema21_above_ma50"], trend["close_below_ema21"] and trend["ema21_below_ma50"]), "Alligator 대체 추세 정렬", 15),
        (side(long_side, np.isfinite(structure["recent_fractal_high"]), np.isfinite(structure["recent_fractal_low"])), "fractal 레벨 준비", 10),
        (side(long_side, trend["adx_expanding"], trend["adx_expanding"]), "sleeping → awakening 추세 강화", 10),
        (side(long_side, volume_flow["volume_support"], volume_flow["volume_support"]), "거래량 유지", 10),
    ]
    trigger_items = [
        (side(long_side, structure["fractal_breakout_long"], structure["fractal_breakout_short"]), "fractal 돌파", 15),
        (side(long_side, signals["Hull_Turn_Bull"] or signals["UTBot_Buy"], signals["Hull_Turn_Bear"] or signals["UTBot_Sell"]), "추세 전환 보조 신호", 10),
        (side(long_side, patterns["fractal_high"] or momentum["macd_hist_rising"], patterns["fractal_low"] or momentum["macd_hist_falling"]), "돌파 후 방향성 유지", 10),
    ]
    return build_result_from_groups(
        definition,
        state,
        long_side,
        "fractal_alligator",
        setup_items,
        trigger_items,
        trigger_threshold=18,
        setup_threshold=18,
        triggered_phase="FRACTAL_BREAKOUT_CONFIRMED",
        ready_phase="ALLIGATOR_AWAKENING",
        risk_template=risk_template_trend,
        invalidation_builder=trend_invalidation_text,
    )


def evaluate_hma_ema_trend(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    hma_ema = dict(state.get("hma_ema") or {})
    price = dict(state.get("price") or {})

    close = float(price.get("close") or 0.0)
    ema15 = float(hma_ema.get("ema15") or close)
    ema25 = float(hma_ema.get("ema25") or close)
    ema50 = float(hma_ema.get("ema50") or close)
    ema200 = float(hma_ema.get("ema200") or close)
    hma25 = float(hma_ema.get("hma25") or close)

    long_entry = bool(hma_ema.get("long_entry"))
    long_aligned = bool(hma_ema.get("long_aligned"))
    short_entry = bool(hma_ema.get("short_entry"))
    short_aligned = bool(hma_ema.get("short_aligned"))
    long_exit_warning = bool(hma_ema.get("hma25_ema15_cross_bear"))
    short_exit_warning = bool(hma_ema.get("hma25_ema15_cross_bull"))

    if long_side:
        if (long_entry or long_aligned) and long_exit_warning:
            status = "EXIT_WARNING"
        elif long_entry:
            status = "LONG_ENTRY"
        elif long_aligned:
            status = "LONG_ALIGNED"
        elif close > ema200:
            status = "LONG_WAIT"
        else:
            status = "NEUTRAL"
    else:
        if (short_entry or short_aligned) and short_exit_warning:
            status = "EXIT_WARNING"
        elif short_entry:
            status = "SHORT_ENTRY"
        elif short_aligned:
            status = "SHORT_ALIGNED"
        elif close < ema200:
            status = "SHORT_WAIT"
        else:
            status = "NEUTRAL"

    phase = status
    score_table = {
        "LONG_ENTRY": 90.0,
        "LONG_ALIGNED": 78.0,
        "LONG_WAIT": 62.0,
        "SHORT_ENTRY": 90.0,
        "SHORT_ALIGNED": 78.0,
        "SHORT_WAIT": 62.0,
        "EXIT_WARNING": 70.0,
        "NEUTRAL": 35.0,
    }
    score = score_table.get(status, 35.0)
    score += min(float(hma_ema.get("risk_to_ema50_pct") or 0.0), 10.0) * -0.25
    score += min(float(state.get("volume_flow", {}).get("volume_ratio", 1.0)), 2.0) * 2.0
    score = max(0.0, min(100.0, score))

    if long_side:
        setup_checks = [
            (close > ema200, "EMA200 above"),
            (hma25 > ema25, "HMA25 > EMA25"),
            (hma25 > ema15, "HMA25 > EMA15"),
            (bool(hma_ema.get("ema15_slope_up")), "EMA15 slope up"),
            (bool(hma_ema.get("ema25_slope_up")), "EMA25 slope up"),
            (bool(hma_ema.get("ema50_slope_up")), "EMA50 slope up"),
            (bool(hma_ema.get("hma25_slope_up")), "HMA25 slope up"),
        ]
        trigger_checks = [
            (bool(hma_ema.get("hma25_ema25_cross_bull")), "HMA25/EMA25 bull cross"),
            (long_entry, "Long entry"),
        ]
        rr_valid = bool(hma_ema.get("long_rr_valid"))
        stop_loss = hma_ema.get("long_virtual_stop")
        target_1 = hma_ema.get("long_target_2r")
        target_2 = hma_ema.get("long_target_3r")
        exit_warning = long_exit_warning
    else:
        setup_checks = [
            (close < ema200, "EMA200 below"),
            (hma25 < ema25, "HMA25 < EMA25"),
            (hma25 < ema15, "HMA25 < EMA15"),
            (bool(hma_ema.get("ema15_slope_down")), "EMA15 slope down"),
            (bool(hma_ema.get("ema25_slope_down")), "EMA25 slope down"),
            (bool(hma_ema.get("ema50_slope_down")), "EMA50 slope down"),
            (bool(hma_ema.get("hma25_slope_down")), "HMA25 slope down"),
        ]
        trigger_checks = [
            (bool(hma_ema.get("hma25_ema25_cross_bear")), "HMA25/EMA25 bear cross"),
            (short_entry, "Short entry"),
        ]
        rr_valid = bool(hma_ema.get("short_rr_valid"))
        stop_loss = hma_ema.get("short_virtual_stop")
        target_1 = hma_ema.get("short_target_2r")
        target_2 = hma_ema.get("short_target_3r")
        exit_warning = short_exit_warning

    matched = [label for ok, label in [*setup_checks, *trigger_checks] if ok]
    missing = [label for ok, label in [*setup_checks, *trigger_checks] if not ok]
    conflicts = list(default_conflicts(state, long_side))
    if not rr_valid:
        conflicts.append("EMA50 virtual stop is invalid at current price location.")
    if long_side and (short_entry or short_aligned):
        conflicts.append("Opposite short alignment is present.")
    if (not long_side) and (long_entry or long_aligned):
        conflicts.append("Opposite long alignment is present.")
    if exit_warning:
        conflicts.append("HMA25 crossed EMA15 against position direction.")

    stop_loss_value = float(stop_loss) if isinstance(stop_loss, (int, float)) else None
    target_1_value = float(target_1) if isinstance(target_1, (int, float)) else None
    target_2_value = float(target_2) if isinstance(target_2, (int, float)) else None
    rr = 2.0 if rr_valid else None

    if status in {"LONG_ENTRY", "SHORT_ENTRY"}:
        entry_hint = "Current entry allowed"
        entry_reference_type = "ENTRY_PRICE"
        entry_reference_text = f"진입가 {close:.2f}"
    elif status in {"LONG_ALIGNED", "SHORT_ALIGNED"}:
        entry_hint = "Aligned and monitoring trigger"
        entry_reference_type = "CONFIRMATION"
        entry_reference_text = f"확인 진행 {close:.2f}"
    elif status in {"LONG_WAIT", "SHORT_WAIT"}:
        entry_hint = "Wait for HMA25/EMA25 trigger"
        entry_reference_type = "CONFIRMATION"
        entry_reference_text = f"확인선 {ema25:.2f}"
    elif status == "EXIT_WARNING":
        entry_hint = "Exit warning"
        entry_reference_type = "CONFIRMATION"
        entry_reference_text = f"경고선 EMA15 {ema15:.2f}"
    else:
        entry_hint = "Neutral"
        entry_reference_type = "ZONE"
        entry_reference_text = "-"

    invalidation_text = (
        f"EMA50 below break invalidates long setup ({ema50:.2f} below)."
        if long_side
        else f"EMA50 above reclaim invalidates short setup ({ema50:.2f} above)."
    )
    if exit_warning:
        invalidation_text += " HMA25/EMA15 cross indicates weakening."

    explanation = (
        f"{definition.ui_label or definition.label} status is {status}. "
        f"EMA200 baseline and HMA/EMA alignment are tracked with EMA50 virtual stop."
    )

    return StrategyResult(
        id=definition.id,
        label=str(definition.ui_label or definition.label),
        canonical_label=definition.label,
        direction=definition.direction,
        category=definition.category,
        score=score,
        status=status,
        phase=phase,
        entry_hint=entry_hint,
        setup_score=max(0.0, min(40.0, float(sum(1 for ok, _ in setup_checks if ok) * 5))),
        trigger_score=max(0.0, min(40.0, float(sum(1 for ok, _ in trigger_checks if ok) * 10))),
        risk_score=20.0 if rr_valid else 8.0,
        presentation_type=definition.presentation_type,
        implementation_level=definition.implementation_level,
        deterministic=definition.deterministic,
        entry_reference_type=entry_reference_type,
        entry_reference_text=entry_reference_text,
        entry_price=close,
        interest_low=min(close, ema25),
        interest_high=max(close, ema25),
        confirmation_level=ema25,
        invalidation_level=stop_loss_value,
        matched_conditions=matched,
        missing_conditions=missing,
        failed_conditions=conflicts[:3],
        stop_loss=stop_loss_value,
        target_1=target_1_value,
        target_2=target_2_value,
        rr=rr,
        conflict_reasons=conflicts,
        explanation=explanation,
        last5_change=[],
        invalidation_text=invalidation_text,
        note=f"{phase} | EMA200 baseline | EMA50 virtual stop",
    )
