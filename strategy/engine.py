from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Iterable

import numpy as np
import pandas as pd


VISIBLE_STATUSES = {"ACTIVE", "CONFIRMING", "TRIGGER_WAIT", "READY", "INTEREST"}


@dataclass(frozen=True)
class StrategyDefinition:
    id: str
    label: str
    category: str
    direction: str
    family: str


@dataclass
class StrategyResult:
    id: str
    label: str
    direction: str
    category: str
    score: float
    status: str
    phase: str
    entry_hint: str
    setup_score: float
    trigger_score: float
    risk_score: float
    entry_price: float | None = None
    matched_conditions: list[str] = field(default_factory=list)
    missing_conditions: list[str] = field(default_factory=list)
    failed_conditions: list[str] = field(default_factory=list)
    stop_loss: float | None = None
    target_1: float | None = None
    target_2: float | None = None
    rr: float | None = None
    conflict_reasons: list[str] = field(default_factory=list)
    explanation: str = ""
    last5_change: list[str] = field(default_factory=list)
    invalidation_text: str = ""
    note: str = ""

    def to_dict(self) -> dict:
        payload = asdict(self)
        for key in ("score", "entry_price", "setup_score", "trigger_score", "risk_score", "stop_loss", "target_1", "target_2", "rr"):
            payload[key] = _round_or_none(payload.get(key))
        return payload


@dataclass
class StrategySummary:
    active_count: int
    visible_count: int
    bullish_count: int
    bearish_count: int
    long_short_bias: str
    conflict_level: str
    top_strategy: dict | None
    secondary_strategies: list[dict] = field(default_factory=list)
    hidden_invalid_count: int = 0
    dominant_reasons: list[str] = field(default_factory=list)
    opposing_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


STRATEGY_DEFINITIONS: tuple[StrategyDefinition, ...] = (
    StrategyDefinition("trend_pullback_long", "추세 지속 눌림목", "trend", "LONG", "trend_pullback"),
    StrategyDefinition("trend_pullback_short", "추세 지속 눌림목", "trend", "SHORT", "trend_pullback"),
    StrategyDefinition("breakout_confirmation_long", "돌파 확인형", "breakout", "LONG", "breakout_confirmation"),
    StrategyDefinition("breakout_confirmation_short", "돌파 확인형", "breakout", "SHORT", "breakout_confirmation"),
    StrategyDefinition("squeeze_expansion_long", "스퀴즈 발사형", "volatility", "LONG", "squeeze_expansion"),
    StrategyDefinition("squeeze_expansion_short", "스퀴즈 발사형", "volatility", "SHORT", "squeeze_expansion"),
    StrategyDefinition("reversal_cluster_long", "반전 클러스터", "reversal", "LONG", "reversal_cluster"),
    StrategyDefinition("reversal_cluster_short", "반전 클러스터", "reversal", "SHORT", "reversal_cluster"),
    StrategyDefinition("supertrend_psar_long", "SuperTrend + PSAR 이중확인", "confirmation", "LONG", "supertrend_psar"),
    StrategyDefinition("supertrend_psar_short", "SuperTrend + PSAR 이중확인", "confirmation", "SHORT", "supertrend_psar"),
    StrategyDefinition("obv_divergence_long", "OBV 다이버전스", "divergence", "LONG", "obv_divergence"),
    StrategyDefinition("obv_divergence_short", "OBV 다이버전스", "divergence", "SHORT", "obv_divergence"),
    StrategyDefinition("keltner_pullback_long", "Keltner Pullback", "trend", "LONG", "keltner_pullback"),
    StrategyDefinition("keltner_pullback_short", "Keltner Pullback", "trend", "SHORT", "keltner_pullback"),
    StrategyDefinition("keltner_breakout_long", "Keltner Breakout", "breakout", "LONG", "keltner_breakout"),
    StrategyDefinition("keltner_breakout_short", "Keltner Breakout", "breakout", "SHORT", "keltner_breakout"),
    StrategyDefinition("keltner_mean_reversion_long", "Keltner Mean Reversion", "reversal", "LONG", "keltner_mean_reversion"),
    StrategyDefinition("keltner_mean_reversion_short", "Keltner Mean Reversion", "reversal", "SHORT", "keltner_mean_reversion"),
    StrategyDefinition("vwap_reclaim_long", "VWAP 반등/거절형", "trend", "LONG", "vwap_reclaim"),
    StrategyDefinition("vwap_reclaim_short", "VWAP 반등/거절형", "trend", "SHORT", "vwap_reclaim"),
    StrategyDefinition("morning_star_fib_long", "Morning Star + Fib 골든존", "reversal", "LONG", "morning_star_fib"),
    StrategyDefinition("morning_star_fib_short", "Morning Star + Fib 골든존", "reversal", "SHORT", "morning_star_fib"),
    StrategyDefinition("fractal_breakout_long", "Fractal Breakout", "breakout", "LONG", "fractal_breakout"),
    StrategyDefinition("fractal_breakout_short", "Fractal Breakout", "breakout", "SHORT", "fractal_breakout"),
    StrategyDefinition("anchored_vwap_long", "Anchored VWAP", "trend", "LONG", "anchored_vwap"),
    StrategyDefinition("anchored_vwap_short", "Anchored VWAP", "trend", "SHORT", "anchored_vwap"),
    StrategyDefinition("institutional_accumulation_long", "기관 매집형", "accumulation", "LONG", "accumulation_pattern"),
    StrategyDefinition("poc_rotation_long", "POC 리클레임 / VAH-VAL 회전", "levels", "LONG", "poc_rotation"),
    StrategyDefinition("poc_rotation_short", "POC 리클레임 / VAH-VAL 회전", "levels", "SHORT", "poc_rotation"),
    StrategyDefinition("ichimoku_breakout_long", "Ichimoku 돌파형", "breakout", "LONG", "ichimoku_breakout"),
    StrategyDefinition("ichimoku_breakout_short", "Ichimoku 돌파형", "breakout", "SHORT", "ichimoku_breakout"),
    StrategyDefinition("fractal_alligator_long", "Fractal + Alligator", "trend", "LONG", "fractal_alligator"),
    StrategyDefinition("fractal_alligator_short", "Fractal + Alligator", "trend", "SHORT", "fractal_alligator"),
    StrategyDefinition("chaikin_flow_long", "Chaikin 독립 전략", "flow", "LONG", "chaikin_flow"),
    StrategyDefinition("chaikin_flow_short", "Chaikin 독립 전략", "flow", "SHORT", "chaikin_flow"),
)


def build_strategy_payload(dc: pd.DataFrame) -> dict:
    engine = StrategyEngine()
    return engine.build_payload(dc)


class StrategyEngine:
    def __init__(self, definitions: Iterable[StrategyDefinition] | None = None):
        self.definitions = tuple(definitions or STRATEGY_DEFINITIONS)

    def build_payload(self, dc: pd.DataFrame) -> dict:
        if dc is None or dc.empty:
            empty_summary = StrategySummary(
                active_count=0,
                visible_count=0,
                bullish_count=0,
                bearish_count=0,
                long_short_bias="BALANCED",
                conflict_level="LOW",
                top_strategy=None,
            )
            return {"summary": empty_summary.to_dict(), "results": [], "visible_results": []}
        market_state = _build_market_state(dc)
        results = [self._evaluate(definition, market_state) for definition in self.definitions]
        results.sort(key=lambda item: (item.score, item.trigger_score, item.setup_score), reverse=True)
        visible = [item for item in results if item.status in VISIBLE_STATUSES]
        summary = _build_summary(visible, results)
        return {
            "summary": summary.to_dict(),
            "results": [item.to_dict() for item in results],
            "visible_results": [item.to_dict() for item in visible],
        }

    def _evaluate(self, definition: StrategyDefinition, market_state: dict) -> StrategyResult:
        evaluators = {
            "trend_pullback": _evaluate_trend_pullback,
            "breakout_confirmation": _evaluate_breakout_confirmation,
            "squeeze_expansion": _evaluate_squeeze_expansion,
            "reversal_cluster": _evaluate_reversal_cluster,
            "supertrend_psar": _evaluate_supertrend_psar,
            "obv_divergence": _evaluate_obv_divergence,
            "keltner_pullback": _evaluate_keltner_pullback,
            "keltner_breakout": _evaluate_keltner_breakout,
            "keltner_mean_reversion": _evaluate_keltner_mean_reversion,
            "vwap_reclaim": _evaluate_vwap_reclaim,
            "morning_star_fib": _evaluate_morning_star_fib,
            "fractal_breakout": _evaluate_fractal_breakout,
            "anchored_vwap": _evaluate_anchored_vwap,
            "accumulation_pattern": _evaluate_accumulation_pattern,
            "poc_rotation": _evaluate_poc_rotation,
            "ichimoku_breakout": _evaluate_ichimoku_breakout,
            "fractal_alligator": _evaluate_fractal_alligator,
            "chaikin_flow": _evaluate_chaikin_flow,
        }
        return evaluators[definition.family](definition, market_state)


def _build_market_state(dc: pd.DataFrame) -> dict:
    frame = dc.copy()
    latest = frame.iloc[-1]
    previous = frame.iloc[-2] if len(frame) > 1 else latest
    close = _scalar(latest.get("Close"))
    atr = max(_scalar(latest.get("ATR")), close * 0.01, 0.01)
    prev_window = frame.iloc[:-1] if len(frame) > 1 else frame
    recent5 = frame.tail(5)
    recent20 = frame.tail(20)
    breakout_level = _series_max(prev_window, "High", default=close)
    breakdown_level = _series_min(prev_window, "Low", default=close)
    swing_high_5 = _series_max(recent5, "High", default=close)
    swing_low_5 = _series_min(recent5, "Low", default=close)
    swing_high_20 = _series_max(recent20, "High", default=close)
    swing_low_20 = _series_min(recent20, "Low", default=close)
    ema8 = _scalar(latest.get("EMA8"), close)
    ema21 = _scalar(latest.get("EMA21"), close)
    ma20 = _scalar(latest.get("MA20"), close)
    ma50 = _scalar(latest.get("MA50"), close)
    ma200 = _scalar(latest.get("MA200"), close)
    vwap = _scalar(latest.get("VWAP"), close)
    fixed_vwap = _scalar(latest.get("Fixed_VWAP"), vwap)
    supertrend = _scalar(latest.get("SuperTrend"), close)
    price_channel_up = _scalar(latest.get("Price_Channel_Up"), breakout_level)
    price_channel_low = _scalar(latest.get("Price_Channel_Low"), breakdown_level)
    price_channel_mid = _scalar(latest.get("Price_Channel_Mid"), (price_channel_up + price_channel_low) / 2.0)
    bb_up = _scalar(latest.get("BB_Up"), swing_high_20)
    bb_low = _scalar(latest.get("BB_Low"), swing_low_20)
    kc_upper = _scalar(latest.get("KC_Upper"), bb_up)
    kc_mid = _scalar(latest.get("KC_Mid"), ma20)
    kc_lower = _scalar(latest.get("KC_Lower"), bb_low)
    vp_vah = _scalar(latest.get("VP_VAH"), np.nan)
    vp_val = _scalar(latest.get("VP_VAL"), np.nan)
    vp_poc = _scalar(latest.get("VP_POC"), np.nan)
    fib_382 = _scalar(latest.get("Fib_382"), np.nan)
    fib_50 = _scalar(latest.get("Fib_50"), np.nan)
    fib_618 = _scalar(latest.get("Fib_618"), np.nan)
    fib_ext_up = _scalar(latest.get("Fib_Ext_1618_Up"), np.nan)
    fib_ext_down = _scalar(latest.get("Fib_Ext_1618_Down"), np.nan)
    tenkan = _scalar(latest.get("Ichimoku_Tenkan"), np.nan)
    kijun = _scalar(latest.get("Ichimoku_Kijun"), np.nan)
    senkou_a = _scalar(latest.get("Ichimoku_SenkouA"), np.nan)
    senkou_b = _scalar(latest.get("Ichimoku_SenkouB"), np.nan)
    cloud_top = _finite_max([senkou_a, senkou_b], np.nan)
    cloud_bottom = _finite_min([senkou_a, senkou_b], np.nan)
    volume_ratio = max(_scalar(latest.get("Volume_Ratio_20"), 1.0), 0.0)
    volume_ratio_50 = max(_scalar(latest.get("Volume_Ratio_50"), volume_ratio), 0.0)
    macd_hist = _scalar(latest.get("MACD_Hist"))
    macd_hist_prev = _scalar(previous.get("MACD_Hist"))
    wt1 = _scalar(latest.get("WT1"))
    wt1_prev = _scalar(previous.get("WT1"))
    obv_slope = _scalar(latest.get("OBV_Slope"))
    chaikin = _scalar(latest.get("Chaikin_Oscillator"))
    cmf = _scalar(latest.get("CMF"))
    composite_accel = _scalar(latest.get("Composite_Accel"))
    rsi = _scalar(latest.get("RSI"), 50.0)
    stochk = _scalar(latest.get("StochK"), 50.0)
    mfi = _scalar(latest.get("MFI"), 50.0)
    price_change_5 = _pct_change(close, _scalar(recent5.iloc[0].get("Close"), close))
    ema21_prev = _scalar(previous.get("EMA21"), ema21)
    ma50_prev = _scalar(previous.get("MA50"), ma50)
    vwap_prev = _scalar(previous.get("VWAP"), vwap)
    fixed_vwap_prev = _scalar(previous.get("Fixed_VWAP"), fixed_vwap)
    chaikin_prev = _scalar(previous.get("Chaikin_Oscillator"), chaikin)
    bb_width = _scalar(latest.get("BB_Width"))
    bb_width_prev = _scalar(previous.get("BB_Width"), bb_width)
    recent_fractal_high = _recent_flagged_level(frame, "Fractal_High", "High", default=swing_high_20)
    recent_fractal_low = _recent_flagged_level(frame, "Fractal_Low", "Low", default=swing_low_20)

    bullish_reversal_candle = any(
        _bool_latest(frame, column)
        for column in ("Hammer", "Bullish_Engulfing", "Morning_Star", "Outside_Bullish", "Doji_Bullish", "Three_Bar_Reversal_Buy")
    )
    bearish_reversal_candle = any(
        _bool_latest(frame, column)
        for column in ("Shooting_Star", "Bearish_Engulfing", "Evening_Star", "Outside_Bearish", "Doji_Bearish", "Three_Bar_Reversal_Sell")
    )

    market_state = {
        "frame": frame,
        "price": {
            "close": close,
            "open": _scalar(latest.get("Open"), close),
            "high": _scalar(latest.get("High"), close),
            "low": _scalar(latest.get("Low"), close),
            "previous_close": _scalar(previous.get("Close"), close),
            "atr": atr,
            "entry": close,
            "ema8": ema8,
            "ema21": ema21,
            "ma20": ma20,
            "ma50": ma50,
            "ma200": ma200,
            "vwap": vwap,
            "fixed_vwap": fixed_vwap,
            "supertrend": supertrend,
            "psar": _scalar(latest.get("Parabolic_SAR"), close),
            "bb_up": bb_up,
            "bb_low": bb_low,
            "kc_upper": kc_upper,
            "kc_mid": kc_mid,
            "kc_lower": kc_lower,
            "price_channel_up": price_channel_up,
            "price_channel_low": price_channel_low,
            "price_channel_mid": price_channel_mid,
        },
        "trend": {
            "ema21_above_ma50": ema21 >= ma50,
            "ema21_below_ma50": ema21 <= ma50,
            "ema21_rising": ema21 >= ema21_prev,
            "ema21_falling": ema21 <= ema21_prev,
            "ma50_rising": ma50 >= ma50_prev,
            "ma50_falling": ma50 <= ma50_prev,
            "close_above_ema21": close >= ema21,
            "close_below_ema21": close <= ema21,
            "close_above_ma20": close >= ma20,
            "close_below_ma20": close <= ma20,
            "close_above_ma50": close >= ma50,
            "close_below_ma50": close <= ma50,
            "close_above_vwap": close >= vwap,
            "close_below_vwap": close <= vwap,
            "close_above_fixed_vwap": close >= fixed_vwap,
            "close_below_fixed_vwap": close <= fixed_vwap,
            "close_above_supertrend": close >= supertrend,
            "close_below_supertrend": close <= supertrend,
            "vwap_reclaimed_long": close >= vwap and _scalar(previous.get("Close"), close) <= vwap_prev,
            "vwap_reclaimed_short": close <= vwap and _scalar(previous.get("Close"), close) >= vwap_prev,
            "fixed_vwap_holding_long": close >= fixed_vwap and fixed_vwap >= fixed_vwap_prev,
            "fixed_vwap_holding_short": close <= fixed_vwap and fixed_vwap <= fixed_vwap_prev,
            "supertrend_bullish": _scalar(latest.get("ST_Direction")) >= 1,
            "supertrend_bearish": _scalar(latest.get("ST_Direction")) <= -1,
            "psar_bullish": _scalar(latest.get("PSAR_Direction")) >= 0,
            "psar_bearish": _scalar(latest.get("PSAR_Direction")) < 0,
            "adx_strong": _scalar(latest.get("ADX")) >= 18,
            "adx_expanding": _scalar(latest.get("ADX")) >= _scalar(previous.get("ADX")),
            "plus_di_dominant": _scalar(latest.get("Plus_DI")) >= _scalar(latest.get("Minus_DI")),
            "minus_di_dominant": _scalar(latest.get("Minus_DI")) >= _scalar(latest.get("Plus_DI")),
            "higher_high_recent": close >= breakout_level or _bool_recent(frame, "New_52W_High", 10),
            "lower_low_recent": close <= breakdown_level or _bool_recent(frame, "New_52W_Low", 10),
            "bullish_trend_stack": close >= ma50 and ma50 >= ma200,
            "bearish_trend_stack": close <= ma50 and ma50 <= ma200,
        },
        "momentum": {
            "macd_hist_positive": macd_hist >= 0,
            "macd_hist_negative": macd_hist <= 0,
            "macd_hist_rising": macd_hist >= macd_hist_prev,
            "macd_hist_falling": macd_hist <= macd_hist_prev,
            "wt_rising": wt1 >= wt1_prev,
            "wt_falling": wt1 <= wt1_prev,
            "rsi": rsi,
            "stochk": stochk,
            "mfi": mfi,
            "oversold": (rsi <= 35) or (stochk <= 25) or (wt1 <= -50),
            "overbought": (rsi >= 65) or (stochk >= 75) or (wt1 >= 50),
            "deep_oversold": (rsi <= 30) or (stochk <= 15) or (wt1 <= -65),
            "deep_overbought": (rsi >= 70) or (stochk >= 85) or (wt1 >= 65),
            "composite_accel": composite_accel,
            "momentum_up": composite_accel >= 0,
            "momentum_down": composite_accel <= 0,
            "squeeze_on": _bool_latest(frame, "Squeeze_On") or _bool_latest(frame, "BB_Squeeze"),
            "squeeze_recent": _bool_recent(frame, "Squeeze_On", 5) or _bool_recent(frame, "BB_Squeeze", 5),
            "squeeze_off": _bool_latest(frame, "Squeeze_Fire_Buy") or _bool_latest(frame, "Squeeze_Fire_Sell"),
            "bb_width_contracting": bb_width <= bb_width_prev,
            "chaikin_rising": chaikin >= chaikin_prev,
            "chaikin_falling": chaikin <= chaikin_prev,
        },
        "volatility": {
            "bb_width": bb_width,
            "bb_width_prev": bb_width_prev,
            "atr_pct": _pct_of(atr, close),
            "channel_span_pct": _pct_of(price_channel_up - price_channel_low, close),
        },
        "volume_flow": {
            "volume_ratio": volume_ratio,
            "volume_ratio_50": volume_ratio_50,
            "volume_support": volume_ratio >= 1.0 or volume_ratio_50 >= 1.0,
            "volume_burst": volume_ratio >= 1.4,
            "volume_dry_up": _bool_recent(frame, "Volume_Dry_Up", 2),
            "obv_rising": _scalar(latest.get("OBV")) >= _series_mean(recent20, "OBV", default=_scalar(latest.get("OBV"))),
            "obv_slope_positive": obv_slope >= 0,
            "obv_slope_negative": obv_slope <= 0,
            "cmf_positive": cmf >= 0,
            "cmf_negative": cmf <= 0,
            "chaikin_positive": chaikin >= 0,
            "chaikin_negative": chaikin <= 0,
            "chaikin_cross_up": chaikin >= 0 and chaikin_prev <= 0,
            "chaikin_cross_down": chaikin <= 0 and chaikin_prev >= 0,
            "money_flow_improving": (cmf >= 0) or (chaikin >= 0) or _bool_latest(frame, "MF_Cross_Bull"),
            "money_flow_weakening": (cmf <= 0) or (chaikin <= 0) or _bool_latest(frame, "MF_Cross_Bear"),
        },
        "structure": {
            "breakout_level": breakout_level,
            "breakdown_level": breakdown_level,
            "swing_high_5": swing_high_5,
            "swing_low_5": swing_low_5,
            "swing_high_20": swing_high_20,
            "swing_low_20": swing_low_20,
            "pullback_near_ma20_long": _near_zone(_scalar(latest.get("Low"), close), ma20, atr, 0.6) and close >= ma20 * 0.99,
            "pullback_near_ma20_short": _near_zone(_scalar(latest.get("High"), close), ma20, atr, 0.6) and close <= ma20 * 1.01,
            "pullback_near_ema21_long": _near_zone(_scalar(latest.get("Low"), close), ema21, atr, 0.6) and close >= ema21 * 0.99,
            "pullback_near_ema21_short": _near_zone(_scalar(latest.get("High"), close), ema21, atr, 0.6) and close <= ema21 * 1.01,
            "pullback_near_kc_mid_long": _near_zone(_scalar(latest.get("Low"), close), kc_mid, atr, 0.6),
            "pullback_near_kc_mid_short": _near_zone(_scalar(latest.get("High"), close), kc_mid, atr, 0.6),
            "pullback_near_fixed_vwap_long": _near_zone(_scalar(latest.get("Low"), close), fixed_vwap, atr, 0.8),
            "pullback_near_fixed_vwap_short": _near_zone(_scalar(latest.get("High"), close), fixed_vwap, atr, 0.8),
            "near_breakout_long": _near_zone(close, breakout_level, atr, 1.5) or _near_zone(close, price_channel_up, atr, 1.5),
            "near_breakout_short": _near_zone(close, breakdown_level, atr, 1.5) or _near_zone(close, price_channel_low, atr, 1.5),
            "lower_zone": close <= min(bb_low, ma20, vwap) or _near_zone(close, swing_low_20, atr, 1.0),
            "upper_zone": close >= max(bb_up, ma20, vwap) or _near_zone(close, swing_high_20, atr, 1.0),
            "outside_keltner_lower": _scalar(latest.get("Low"), close) <= kc_lower,
            "outside_keltner_upper": _scalar(latest.get("High"), close) >= kc_upper,
            "inside_value_area": np.isfinite(vp_val) and np.isfinite(vp_vah) and vp_val <= close <= vp_vah,
            "near_vp_poc": _near_zone(close, vp_poc, atr, 0.8),
            "near_vp_val": _near_zone(close, vp_val, atr, 0.8),
            "near_vp_vah": _near_zone(close, vp_vah, atr, 0.8),
            "recent_fractal_high": recent_fractal_high,
            "recent_fractal_low": recent_fractal_low,
            "fractal_breakout_long": close >= recent_fractal_high if np.isfinite(recent_fractal_high) else False,
            "fractal_breakout_short": close <= recent_fractal_low if np.isfinite(recent_fractal_low) else False,
            "price_change_5": price_change_5,
            "price_above_breakout": close >= breakout_level,
            "price_below_breakdown": close <= breakdown_level,
        },
        "levels": {
            "vwap": vwap,
            "fixed_vwap": fixed_vwap,
            "ema21": ema21,
            "ma50": ma50,
            "kc_upper": kc_upper,
            "kc_mid": kc_mid,
            "kc_lower": kc_lower,
            "vp_poc": vp_poc,
            "vp_vah": vp_vah,
            "vp_val": vp_val,
            "fib_382": fib_382,
            "fib_50": fib_50,
            "fib_618": fib_618,
            "fib_ext_up": fib_ext_up,
            "fib_ext_down": fib_ext_down,
            "tenkan": tenkan,
            "kijun": kijun,
            "cloud_top": cloud_top,
            "cloud_bottom": cloud_bottom,
            "nearest_resistance": _nearest_resistance(close, [breakout_level, swing_high_20, bb_up, price_channel_up, vp_vah, fib_ext_up]),
            "nearest_support": _nearest_support(close, [breakdown_level, swing_low_20, bb_low, price_channel_low, vp_val, vp_poc]),
        },
        "patterns": {
            "bullish_reversal_candle": bullish_reversal_candle,
            "bearish_reversal_candle": bearish_reversal_candle,
            "morning_star": _bool_latest(frame, "Morning_Star"),
            "evening_star": _bool_latest(frame, "Evening_Star"),
            "fractal_high": _bool_latest(frame, "Fractal_High"),
            "fractal_low": _bool_latest(frame, "Fractal_Low"),
            "pocket_pivot": _bool_latest(frame, "Pocket_Pivot"),
            "bullish_divergence": any(
                _bool_latest(frame, column)
                for column in ("Bull_Divergence", "RSI_Bull_Divergence", "MF_Bull_Div", "OBV_Div_Buy", "Smart_Money_Bullish_Div")
            ),
            "bearish_divergence": any(
                _bool_latest(frame, column)
                for column in ("Bear_Divergence", "RSI_Bear_Divergence", "MF_Bear_Div", "OBV_Div_Sell", "Smart_Money_Bearish_Div")
            ),
            "volume_climax_buy": _bool_latest(frame, "Volume_Climax_Buy"),
            "volume_climax_sell": _bool_latest(frame, "Volume_Climax_Sell"),
            "parabolic_bottom": _bool_latest(frame, "Parabolic_Bottom_Buy"),
            "parabolic_top": _bool_latest(frame, "Parabolic_Top_Sell"),
            "obv_div_buy": _bool_latest(frame, "OBV_Div_Buy") or _bool_latest(frame, "Smart_Money_Bullish_Div"),
            "obv_div_sell": _bool_latest(frame, "OBV_Div_Sell") or _bool_latest(frame, "Smart_Money_Bearish_Div"),
        },
        "signals": {
            key: _bool_latest(frame, key)
            for key in (
                "EMA_Pullback_Buy",
                "EMA_Pullback_Sell",
                "VWAP_Bounce_Buy",
                "VWAP_Reject_Sell",
                "SuperTrend_Buy",
                "SuperTrend_Sell",
                "UTBot_Buy",
                "UTBot_Sell",
                "Hull_Turn_Bull",
                "Hull_Turn_Bear",
                "Squeeze_Fire_Buy",
                "Squeeze_Fire_Sell",
                "Squeeze_Mom_Cross_Up",
                "Squeeze_Mom_Cross_Down",
                "BB_Squeeze_End_Bull",
                "BB_Squeeze_End_Bear",
                "Expansion_BO",
                "Expansion_BD",
                "Kumo_Breakout_Bull",
                "Kumo_Breakout_Bear",
                "TK_Cross_Bull",
                "TK_Cross_Bear",
                "BB_Upper_Break",
                "BB_Lower_Break",
                "CMF_Bull",
                "CMF_Bear",
                "Pocket_Pivot",
                "Volume_POC_Breakout",
                "Volume_POC_Breakdown",
                "VP_VAH_Resistance",
                "VP_VAL_Support",
                "Fib_50_Support",
                "Fib_50_Resistance",
                "Fib_618_Support",
                "Fib_618_Resistance",
                "Fib_618_Reclaim",
                "Fib_618_Breakdown",
                "Fib_Confluence_Buy",
                "Fib_Confluence_Sell",
                "Box_Breakout_Bull",
                "Box_Breakdown_Bear",
                "Channel_Breakout_Bull",
                "Channel_Breakdown_Bear",
                "Triangle_Breakout_Bull",
                "Triangle_Breakdown_Bear",
                "CS_Trend_Continuation_Buy",
                "CS_Trend_Continuation_Sell",
                "CS_Breakout_Confirm_Buy",
                "CS_Breakout_Confirm_Sell",
                "CS_Squeeze_Breakout_Buy",
                "CS_Squeeze_Breakdown_Sell",
                "CS_Reversal_Cluster_Buy",
                "CS_Reversal_Cluster_Sell",
                "CS_Divergence_Confluence_Buy",
                "CS_Divergence_Confluence_Sell",
                "CS_Triple_Confirm_Buy",
                "CS_Triple_Confirm_Sell",
                "CS_Institutional_Accumulation",
                "CS_Ichimoku_Breakout_Buy",
                "CS_Conflict_Warning",
            )
        },
    }
    return market_state


def _evaluate_trend_pullback(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    trend = state["trend"]
    structure = state["structure"]
    volume_flow = state["volume_flow"]
    momentum = state["momentum"]
    patterns = state["patterns"]
    signals = state["signals"]

    setup_items = [
        (_side(long_side, trend["ema21_above_ma50"] and trend["ema21_rising"], trend["ema21_below_ma50"] and trend["ema21_falling"]), "EMA21 / MA50 추세 정렬", 15),
        (_side(long_side, trend["close_above_ema21"], trend["close_below_ema21"]), "가격이 EMA21 방향 위상 유지", 10),
        (_side(long_side, structure["pullback_near_ema21_long"] or structure["pullback_near_ma20_long"] or structure["pullback_near_kc_mid_long"], structure["pullback_near_ema21_short"] or structure["pullback_near_ma20_short"] or structure["pullback_near_kc_mid_short"]), "눌림 구간 접근", 12),
        (_side(long_side, trend["higher_high_recent"] or signals["CS_Trend_Continuation_Buy"], trend["lower_low_recent"] or signals["CS_Trend_Continuation_Sell"]), "최근 추세 재개 이력", 5),
        (_side(long_side, volume_flow["volume_support"], volume_flow["volume_support"]), "거래량 바닥 이탈 없음", 3),
    ]
    trigger_items = [
        (_side(long_side, signals["EMA_Pullback_Buy"] or patterns["bullish_reversal_candle"], signals["EMA_Pullback_Sell"] or patterns["bearish_reversal_candle"]), "눌림 뒤 방향 전환 캔들", 15),
        (_side(long_side, signals["UTBot_Buy"] or signals["Hull_Turn_Bull"], signals["UTBot_Sell"] or signals["Hull_Turn_Bear"]), "보조 추세 신호 정렬", 10),
        (_side(long_side, trend["psar_bullish"], trend["psar_bearish"]), "PSAR 추세 유지", 5),
        (_side(long_side, momentum["macd_hist_rising"] and momentum["wt_rising"], momentum["macd_hist_falling"] and momentum["wt_falling"]), "모멘텀 재가속", 5),
    ]
    setup_score, setup_matched, setup_missing = _score_group(setup_items)
    trigger_score, trigger_matched, trigger_missing = _score_group(trigger_items)
    trigger_passed = trigger_score >= 20
    phase = "TRIGGERED" if trigger_passed else "PULLBACK_WAIT" if setup_score >= 25 else "SETUP_INVALID"
    stop_loss, target_1, target_2, rr = _risk_template_trend(state, long_side)
    conflict_reasons = _default_conflicts(state, long_side)
    risk_score = _risk_score(stop_loss, target_1, state["price"]["entry"], rr, conflict_reasons)
    total_score = _total_score(setup_score, trigger_score, risk_score)
    status = _status_from_score(total_score, trigger_passed, rr, setup_score, trigger_score, phase)
    entry_hint = _entry_hint(status, phase, long_side, "trend_pullback")
    entry_price = _entry_price(state, long_side, "trend_pullback", phase, status)
    matched = setup_matched + trigger_matched
    missing = setup_missing + trigger_missing
    failed = _failed_from_conflicts(conflict_reasons)
    explanation = _build_explanation(definition.label, status, matched, missing, conflict_reasons)
    return StrategyResult(
        id=definition.id,
        label=definition.label,
        direction=definition.direction,
        category=definition.category,
        score=total_score,
        status=status,
        phase=phase,
        entry_hint=entry_hint,
        entry_price=entry_price,
        setup_score=setup_score,
        trigger_score=trigger_score,
        risk_score=risk_score,
        matched_conditions=matched,
        missing_conditions=missing,
        failed_conditions=failed,
        stop_loss=stop_loss,
        target_1=target_1,
        target_2=target_2,
        rr=rr,
        conflict_reasons=conflict_reasons,
        explanation=explanation,
        last5_change=_recent_change_notes(state, long_side),
        invalidation_text=_trend_invalidation_text(state, long_side, stop_loss),
        note=_phase_note(phase, conflict_reasons),
    )


def _evaluate_breakout_confirmation(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    trend = state["trend"]
    structure = state["structure"]
    volume_flow = state["volume_flow"]
    momentum = state["momentum"]
    signals = state["signals"]

    setup_items = [
        (_side(long_side, structure["near_breakout_long"], structure["near_breakout_short"]), "돌파 후보 레벨 인접", 12),
        (_side(long_side, volume_flow["volume_support"], volume_flow["volume_support"]), "거래량 점증", 8),
        (_side(long_side, trend["adx_strong"], trend["adx_strong"]), "ADX로 추세 힘 확인", 8),
        (_side(long_side, trend["close_above_ema21"] and trend["close_above_vwap"], trend["close_below_ema21"] and trend["close_below_vwap"]), "기준선 정렬", 10),
        (_side(long_side, trend["plus_di_dominant"], trend["minus_di_dominant"]), "방향성 우위", 7),
    ]
    trigger_signal_long = any(signals[key] for key in ("Expansion_BO", "Kumo_Breakout_Bull", "BB_Upper_Break", "Box_Breakout_Bull", "Channel_Breakout_Bull", "Triangle_Breakout_Bull", "CS_Breakout_Confirm_Buy"))
    trigger_signal_short = any(signals[key] for key in ("Expansion_BD", "Kumo_Breakout_Bear", "BB_Lower_Break", "Box_Breakdown_Bear", "Channel_Breakdown_Bear", "Triangle_Breakdown_Bear", "CS_Breakout_Confirm_Sell"))
    hold_long = state["price"]["close"] >= structure["breakout_level"] * 0.995
    hold_short = state["price"]["close"] <= structure["breakdown_level"] * 1.005
    trigger_items = [
        (_side(long_side, trigger_signal_long, trigger_signal_short), "돌파 시그널 발생", 15),
        (_side(long_side, hold_long, hold_short), "돌파 레벨 종가 유지", 10),
        (_side(long_side, volume_flow["volume_burst"], volume_flow["volume_burst"]), "돌파봉 거래량 증가", 5),
        (_side(long_side, momentum["macd_hist_rising"], momentum["macd_hist_falling"]), "모멘텀 후속 확인", 5),
    ]
    setup_score, setup_matched, setup_missing = _score_group(setup_items)
    trigger_score, trigger_matched, trigger_missing = _score_group(trigger_items)
    trigger_passed = trigger_score >= 25
    phase = "BREAKOUT_CONFIRMED" if trigger_passed else "BREAKOUT_PENDING" if trigger_score >= 15 else "SETUP_INVALID"
    stop_loss, target_1, target_2, rr = _risk_template_breakout(state, long_side)
    conflict_reasons = _default_conflicts(state, long_side)
    if _side(long_side, not hold_long and trigger_signal_long, not hold_short and trigger_signal_short):
        conflict_reasons.append("돌파 레벨 위/아래 안착이 아직 부족합니다.")
    risk_score = _risk_score(stop_loss, target_1, state["price"]["entry"], rr, conflict_reasons)
    total_score = _total_score(setup_score, trigger_score, risk_score)
    status = _status_from_score(total_score, trigger_passed, rr, setup_score, trigger_score, phase)
    entry_hint = _entry_hint(status, phase, long_side, "breakout")
    entry_price = _entry_price(state, long_side, "breakout", phase, status)
    matched = setup_matched + trigger_matched
    missing = setup_missing + trigger_missing
    failed = _failed_from_conflicts(conflict_reasons)
    explanation = _build_explanation(definition.label, status, matched, missing, conflict_reasons)
    return StrategyResult(
        id=definition.id,
        label=definition.label,
        direction=definition.direction,
        category=definition.category,
        score=total_score,
        status=status,
        phase=phase,
        entry_hint=entry_hint,
        entry_price=entry_price,
        setup_score=setup_score,
        trigger_score=trigger_score,
        risk_score=risk_score,
        matched_conditions=matched,
        missing_conditions=missing,
        failed_conditions=failed,
        stop_loss=stop_loss,
        target_1=target_1,
        target_2=target_2,
        rr=rr,
        conflict_reasons=conflict_reasons,
        explanation=explanation,
        last5_change=_recent_change_notes(state, long_side),
        invalidation_text=_breakout_invalidation_text(state, long_side, stop_loss),
        note=_phase_note(phase, conflict_reasons),
    )


def _evaluate_squeeze_expansion(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    trend = state["trend"]
    momentum = state["momentum"]
    volume_flow = state["volume_flow"]
    signals = state["signals"]

    setup_items = [
        (_side(long_side, momentum["squeeze_recent"], momentum["squeeze_recent"]), "Squeeze On / BB 압축 지속", 20),
        (_side(long_side, momentum["bb_width_contracting"], momentum["bb_width_contracting"]), "밴드 폭 축소", 10),
        (_side(long_side, momentum["macd_hist_rising"] or momentum["wt_rising"], momentum["macd_hist_falling"] or momentum["wt_falling"]), "압축 속 모멘텀 방향성 준비", 8),
        (_side(long_side, volume_flow["volume_dry_up"] or not volume_flow["volume_burst"], volume_flow["volume_dry_up"] or not volume_flow["volume_burst"]), "변동성 압축 구간", 7),
    ]
    trigger_items = [
        (_side(long_side, signals["Squeeze_Fire_Buy"] or signals["BB_Squeeze_End_Bull"] or signals["CS_Squeeze_Breakout_Buy"], signals["Squeeze_Fire_Sell"] or signals["BB_Squeeze_End_Bear"] or signals["CS_Squeeze_Breakdown_Sell"]), "Squeeze Off / 방향 분출", 15),
        (_side(long_side, signals["Squeeze_Mom_Cross_Up"] or momentum["macd_hist_rising"], signals["Squeeze_Mom_Cross_Down"] or momentum["macd_hist_falling"]), "모멘텀 히스토그램 확장", 8),
        (_side(long_side, volume_flow["volume_burst"], volume_flow["volume_burst"]), "거래량 동반", 7),
        (_side(long_side, trend["close_above_ema21"] or trend["close_above_vwap"], trend["close_below_ema21"] or trend["close_below_vwap"]), "기준선 정렬 가산", 5),
    ]
    setup_score, setup_matched, setup_missing = _score_group(setup_items)
    trigger_score, trigger_matched, trigger_missing = _score_group(trigger_items)
    trigger_passed = trigger_score >= 20
    phase = "TRIGGERED" if trigger_passed else "SQUEEZE_READY" if setup_score >= 20 else "SETUP_INVALID"
    stop_loss, target_1, target_2, rr = _risk_template_breakout(state, long_side)
    conflict_reasons = _default_conflicts(state, long_side)
    if _side(long_side, momentum["squeeze_on"], momentum["squeeze_on"]) and not trigger_passed:
        conflict_reasons.append("아직 Squeeze Off가 확정되지 않았습니다.")
    risk_score = _risk_score(stop_loss, target_1, state["price"]["entry"], rr, conflict_reasons)
    total_score = _total_score(setup_score, trigger_score, risk_score)
    status = _status_from_score(total_score, trigger_passed, rr, setup_score, trigger_score, phase)
    entry_hint = _entry_hint(status, phase, long_side, "squeeze")
    entry_price = _entry_price(state, long_side, "squeeze", phase, status)
    matched = setup_matched + trigger_matched
    missing = setup_missing + trigger_missing
    failed = _failed_from_conflicts(conflict_reasons)
    explanation = _build_explanation(definition.label, status, matched, missing, conflict_reasons)
    return StrategyResult(
        id=definition.id,
        label=definition.label,
        direction=definition.direction,
        category=definition.category,
        score=total_score,
        status=status,
        phase=phase,
        entry_hint=entry_hint,
        entry_price=entry_price,
        setup_score=setup_score,
        trigger_score=trigger_score,
        risk_score=risk_score,
        matched_conditions=matched,
        missing_conditions=missing,
        failed_conditions=failed,
        stop_loss=stop_loss,
        target_1=target_1,
        target_2=target_2,
        rr=rr,
        conflict_reasons=conflict_reasons,
        explanation=explanation,
        last5_change=_recent_change_notes(state, long_side),
        invalidation_text=_breakout_invalidation_text(state, long_side, stop_loss),
        note=_phase_note(phase, conflict_reasons),
    )


def _evaluate_reversal_cluster(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    trend = state["trend"]
    structure = state["structure"]
    volume_flow = state["volume_flow"]
    momentum = state["momentum"]
    patterns = state["patterns"]
    signals = state["signals"]

    setup_items = [
        (_side(long_side, momentum["deep_oversold"] or structure["price_change_5"] <= -5.0, momentum["deep_overbought"] or structure["price_change_5"] >= 5.0), "과매도 / 과매수 스트레치", 15),
        (_side(long_side, structure["lower_zone"], structure["upper_zone"]), "밴드/구조 하단 접근", 10),
        (_side(long_side, patterns["bullish_divergence"] or volume_flow["money_flow_improving"], patterns["bearish_divergence"] or volume_flow["money_flow_weakening"]), "다이버전스 또는 자금흐름 개선", 12),
        (_side(long_side, trend["bearish_trend_stack"] or trend["close_below_vwap"], trend["bullish_trend_stack"] or trend["close_above_vwap"]), "추세 말단 / 반전 후보 구간", 8),
    ]
    trigger_items = [
        (_side(long_side, patterns["bullish_reversal_candle"] or patterns["volume_climax_buy"] or patterns["parabolic_bottom"], patterns["bearish_reversal_candle"] or patterns["volume_climax_sell"] or patterns["parabolic_top"]), "반전 캔들 또는 클라이맥스", 15),
        (_side(long_side, momentum["macd_hist_rising"] and momentum["wt_rising"], momentum["macd_hist_falling"] and momentum["wt_falling"]), "모멘텀 개선", 10),
        (_side(long_side, signals["VWAP_Bounce_Buy"] or trend["close_above_vwap"] or signals["UTBot_Buy"] or signals["Hull_Turn_Bull"], signals["VWAP_Reject_Sell"] or trend["close_below_vwap"] or signals["UTBot_Sell"] or signals["Hull_Turn_Bear"]), "기준선 / 확인 신호 회복", 10),
    ]
    setup_score, setup_matched, setup_missing = _score_group(setup_items)
    trigger_score, trigger_matched, trigger_missing = _score_group(trigger_items)
    trigger_passed = trigger_score >= 20
    phase = "TRIGGERED" if trigger_passed else "REVERSAL_READY" if setup_score >= 20 else "SETUP_INVALID"
    stop_loss, target_1, target_2, rr = _risk_template_reversal(state, long_side)
    conflict_reasons = _default_conflicts(state, long_side)
    if _side(long_side, not trend["close_above_vwap"], not trend["close_below_vwap"]):
        conflict_reasons.append("기준선 회복/재이탈 확인이 더 필요합니다.")
    risk_score = _risk_score(stop_loss, target_1, state["price"]["entry"], rr, conflict_reasons)
    total_score = _total_score(setup_score, trigger_score, risk_score)
    status = _status_from_score(total_score, trigger_passed, rr, setup_score, trigger_score, phase)
    entry_hint = _entry_hint(status, phase, long_side, "reversal")
    entry_price = _entry_price(state, long_side, "reversal", phase, status)
    matched = setup_matched + trigger_matched
    missing = setup_missing + trigger_missing
    failed = _failed_from_conflicts(conflict_reasons)
    explanation = _build_explanation(definition.label, status, matched, missing, conflict_reasons)
    return StrategyResult(
        id=definition.id,
        label=definition.label,
        direction=definition.direction,
        category=definition.category,
        score=total_score,
        status=status,
        phase=phase,
        entry_hint=entry_hint,
        entry_price=entry_price,
        setup_score=setup_score,
        trigger_score=trigger_score,
        risk_score=risk_score,
        matched_conditions=matched,
        missing_conditions=missing,
        failed_conditions=failed,
        stop_loss=stop_loss,
        target_1=target_1,
        target_2=target_2,
        rr=rr,
        conflict_reasons=conflict_reasons,
        explanation=explanation,
        last5_change=_recent_change_notes(state, long_side),
        invalidation_text=_reversal_invalidation_text(state, long_side, stop_loss),
        note=_phase_note(phase, conflict_reasons),
    )


def _evaluate_supertrend_psar(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    trend = state["trend"]
    momentum = state["momentum"]
    signals = state["signals"]

    setup_items = [
        (_side(long_side, trend["supertrend_bullish"], trend["supertrend_bearish"]), "SuperTrend 방향 일치", 15),
        (_side(long_side, trend["psar_bullish"], trend["psar_bearish"]), "PSAR 방향 일치", 15),
        (_side(long_side, trend["close_above_supertrend"] and trend["close_above_ema21"], trend["close_below_supertrend"] and trend["close_below_ema21"]), "가격이 추세 기준선 위상 유지", 10),
        (_side(long_side, trend["adx_strong"] and trend["plus_di_dominant"], trend["adx_strong"] and trend["minus_di_dominant"]), "추세 강도 확인", 5),
    ]
    trigger_items = [
        (_side(long_side, signals["SuperTrend_Buy"] or signals["CS_Triple_Confirm_Buy"], signals["SuperTrend_Sell"] or signals["CS_Triple_Confirm_Sell"]), "SuperTrend 전환 / 3중 확인", 15),
        (_side(long_side, signals["UTBot_Buy"] or signals["Hull_Turn_Bull"], signals["UTBot_Sell"] or signals["Hull_Turn_Bear"]), "보조 추세 신호 정렬", 10),
        (_side(long_side, momentum["macd_hist_rising"] or momentum["wt_rising"], momentum["macd_hist_falling"] or momentum["wt_falling"]), "모멘텀 동조화", 10),
    ]
    setup_score, setup_matched, setup_missing = _score_group(setup_items)
    trigger_score, trigger_matched, trigger_missing = _score_group(trigger_items)
    trigger_passed = trigger_score >= 15 and _side(long_side, trend["supertrend_bullish"] and trend["psar_bullish"], trend["supertrend_bearish"] and trend["psar_bearish"])
    phase = "DOUBLE_CONFIRMED" if trigger_passed else "TREND_ALIGNED" if setup_score >= 20 else "SETUP_INVALID"
    stop_loss, target_1, target_2, rr = _risk_template_trend(state, long_side)
    conflict_reasons = _default_conflicts(state, long_side)
    if _side(long_side, not trend["psar_bullish"], not trend["psar_bearish"]):
        conflict_reasons.append("PSAR 방향 전환이 아직 완전하지 않습니다.")
    risk_score = _risk_score(stop_loss, target_1, state["price"]["entry"], rr, conflict_reasons)
    total_score = _total_score(setup_score, trigger_score, risk_score)
    status = _status_from_score(total_score, trigger_passed, rr, setup_score, trigger_score, phase)
    entry_hint = _entry_hint(status, phase, long_side, "supertrend_psar")
    entry_price = _entry_price(state, long_side, "supertrend_psar", phase, status)
    matched = setup_matched + trigger_matched
    missing = setup_missing + trigger_missing
    failed = _failed_from_conflicts(conflict_reasons)
    explanation = _build_explanation(definition.label, status, matched, missing, conflict_reasons)
    return StrategyResult(
        id=definition.id,
        label=definition.label,
        direction=definition.direction,
        category=definition.category,
        score=total_score,
        status=status,
        phase=phase,
        entry_hint=entry_hint,
        entry_price=entry_price,
        setup_score=setup_score,
        trigger_score=trigger_score,
        risk_score=risk_score,
        matched_conditions=matched,
        missing_conditions=missing,
        failed_conditions=failed,
        stop_loss=stop_loss,
        target_1=target_1,
        target_2=target_2,
        rr=rr,
        conflict_reasons=conflict_reasons,
        explanation=explanation,
        last5_change=_recent_change_notes(state, long_side),
        invalidation_text=_trend_invalidation_text(state, long_side, stop_loss),
        note=_phase_note(phase, conflict_reasons),
    )


def _evaluate_obv_divergence(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    trend = state["trend"]
    structure = state["structure"]
    volume_flow = state["volume_flow"]
    momentum = state["momentum"]
    patterns = state["patterns"]
    signals = state["signals"]

    setup_items = [
        (_side(long_side, patterns["obv_div_buy"], patterns["obv_div_sell"]), "OBV / 스마트머니 다이버전스", 20),
        (_side(long_side, structure["lower_zone"] or structure["price_change_5"] <= -4.0, structure["upper_zone"] or structure["price_change_5"] >= 4.0), "가격은 극단 구간 접근", 10),
        (_side(long_side, volume_flow["money_flow_improving"], volume_flow["money_flow_weakening"]), "자금흐름 보조 확인", 5),
        (_side(long_side, momentum["oversold"], momentum["overbought"]), "오실레이터 극단 구간", 10),
    ]
    trigger_items = [
        (_side(long_side, patterns["bullish_reversal_candle"], patterns["bearish_reversal_candle"]), "확인 트리거 캔들", 15),
        (_side(long_side, signals["VWAP_Bounce_Buy"] or state["price"]["close"] >= state["price"]["ema8"] or trend["close_above_vwap"], signals["VWAP_Reject_Sell"] or state["price"]["close"] <= state["price"]["ema8"] or trend["close_below_vwap"]), "VWAP / EMA8 회복", 10),
        (_side(long_side, signals["UTBot_Buy"] or momentum["macd_hist_rising"], signals["UTBot_Sell"] or momentum["macd_hist_falling"]), "보조 모멘텀 확인", 10),
    ]
    setup_score, setup_matched, setup_missing = _score_group(setup_items)
    trigger_score, trigger_matched, trigger_missing = _score_group(trigger_items)
    trigger_passed = trigger_score >= 15
    phase = "DIVERGENCE_CONFIRMED" if trigger_passed else "DIVERGENCE_READY" if setup_score >= 20 else "SETUP_INVALID"
    stop_loss, target_1, target_2, rr = _risk_template_reversal(state, long_side)
    conflict_reasons = _default_conflicts(state, long_side)
    if _side(long_side, not trend["close_above_vwap"], not trend["close_below_vwap"]):
        conflict_reasons.append("다이버전스 이후 기준선 확인이 아직 약합니다.")
    risk_score = _risk_score(stop_loss, target_1, state["price"]["entry"], rr, conflict_reasons)
    total_score = _total_score(setup_score, trigger_score, risk_score)
    status = _status_from_score(total_score, trigger_passed, rr, setup_score, trigger_score, phase)
    entry_hint = _entry_hint(status, phase, long_side, "obv_divergence")
    entry_price = _entry_price(state, long_side, "obv_divergence", phase, status)
    matched = setup_matched + trigger_matched
    missing = setup_missing + trigger_missing
    failed = _failed_from_conflicts(conflict_reasons)
    explanation = _build_explanation(definition.label, status, matched, missing, conflict_reasons)
    return StrategyResult(
        id=definition.id,
        label=definition.label,
        direction=definition.direction,
        category=definition.category,
        score=total_score,
        status=status,
        phase=phase,
        entry_hint=entry_hint,
        entry_price=entry_price,
        setup_score=setup_score,
        trigger_score=trigger_score,
        risk_score=risk_score,
        matched_conditions=matched,
        missing_conditions=missing,
        failed_conditions=failed,
        stop_loss=stop_loss,
        target_1=target_1,
        target_2=target_2,
        rr=rr,
        conflict_reasons=conflict_reasons,
        explanation=explanation,
        last5_change=_recent_change_notes(state, long_side),
        invalidation_text=_reversal_invalidation_text(state, long_side, stop_loss),
        note=_phase_note(phase, conflict_reasons),
    )


def _evaluate_keltner_pullback(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    trend = state["trend"]
    structure = state["structure"]
    volume_flow = state["volume_flow"]
    momentum = state["momentum"]
    patterns = state["patterns"]
    signals = state["signals"]

    setup_items = [
        (_side(long_side, trend["ema21_above_ma50"] and trend["close_above_ma20"], trend["ema21_below_ma50"] and trend["close_below_ma20"]), "상위 추세와 Keltner 기준선 정렬", 15),
        (_side(long_side, structure["pullback_near_kc_mid_long"], structure["pullback_near_kc_mid_short"]), "Keltner mid 눌림 구간 접근", 15),
        (_side(long_side, trend["close_above_vwap"], trend["close_below_vwap"]), "VWAP 방향 우위 유지", 8),
        (_side(long_side, volume_flow["volume_support"], volume_flow["volume_support"]), "눌림 중 거래량 지지", 7),
    ]
    trigger_items = [
        (_side(long_side, signals["EMA_Pullback_Buy"] or patterns["bullish_reversal_candle"], signals["EMA_Pullback_Sell"] or patterns["bearish_reversal_candle"]), "Keltner 눌림 뒤 반전 캔들", 15),
        (_side(long_side, signals["UTBot_Buy"] or signals["Hull_Turn_Bull"], signals["UTBot_Sell"] or signals["Hull_Turn_Bear"]), "보조 추세 신호 정렬", 10),
        (_side(long_side, momentum["macd_hist_rising"], momentum["macd_hist_falling"]), "모멘텀 재확장", 10),
    ]
    return _build_result_from_groups(
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
        risk_template=_risk_template_trend,
        invalidation_builder=_trend_invalidation_text,
    )


def _evaluate_keltner_breakout(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    trend = state["trend"]
    volume_flow = state["volume_flow"]
    momentum = state["momentum"]
    structure = state["structure"]
    signals = state["signals"]

    setup_items = [
        (_side(long_side, structure["near_breakout_long"], structure["near_breakout_short"]), "Keltner 상단/하단 돌파 구간 접근", 12),
        (_side(long_side, trend["close_above_ema21"], trend["close_below_ema21"]), "EMA21 방향 정렬", 10),
        (_side(long_side, trend["adx_strong"], trend["adx_strong"]), "추세 강도 확보", 8),
        (_side(long_side, volume_flow["volume_support"], volume_flow["volume_support"]), "돌파 전 거래량 준비", 10),
        (_side(long_side, momentum["bb_width_contracting"] or momentum["squeeze_recent"], momentum["bb_width_contracting"] or momentum["squeeze_recent"]), "돌파 전 변동성 수축", 5),
    ]
    trigger_items = [
        (_side(long_side, state["price"]["close"] >= state["price"]["kc_upper"] or signals["Expansion_BO"], state["price"]["close"] <= state["price"]["kc_lower"] or signals["Expansion_BD"]), "Keltner 밴드 돌파 종가 확정", 15),
        (_side(long_side, signals["Channel_Breakout_Bull"] or signals["Box_Breakout_Bull"] or signals["CS_Breakout_Confirm_Buy"], signals["Channel_Breakdown_Bear"] or signals["Box_Breakdown_Bear"] or signals["CS_Breakout_Confirm_Sell"]), "돌파 확인 시그널 발생", 10),
        (_side(long_side, volume_flow["volume_burst"], volume_flow["volume_burst"]), "돌파봉 거래량 증가", 5),
        (_side(long_side, momentum["macd_hist_rising"], momentum["macd_hist_falling"]), "돌파 후 모멘텀 확장", 5),
    ]
    extra_conflicts = []
    if _side(long_side, state["price"]["close"] < state["price"]["kc_upper"], state["price"]["close"] > state["price"]["kc_lower"]):
        extra_conflicts.append("Keltner 외곽 밴드 안착이 아직 완전하지 않습니다.")
    return _build_result_from_groups(
        definition,
        state,
        long_side,
        "keltner_breakout",
        setup_items,
        trigger_items,
        trigger_threshold=20,
        setup_threshold=20,
        triggered_phase="KELTNER_BREAKOUT_CONFIRMED",
        ready_phase="KELTNER_BREAKOUT_PENDING",
        risk_template=_risk_template_breakout,
        invalidation_builder=_breakout_invalidation_text,
        extra_conflicts=extra_conflicts,
    )


def _evaluate_keltner_mean_reversion(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    structure = state["structure"]
    volume_flow = state["volume_flow"]
    momentum = state["momentum"]
    patterns = state["patterns"]
    signals = state["signals"]
    trend = state["trend"]

    setup_items = [
        (_side(long_side, structure["outside_keltner_lower"], structure["outside_keltner_upper"]), "Keltner 외곽 과확장", 15),
        (_side(long_side, momentum["deep_oversold"], momentum["deep_overbought"]), "오실레이터 극단 구간", 10),
        (_side(long_side, volume_flow["money_flow_improving"], volume_flow["money_flow_weakening"]), "자금흐름 개선", 10),
        (_side(long_side, structure["price_change_5"] <= -3.0, structure["price_change_5"] >= 3.0), "단기 과매도/과매수 확인", 10),
    ]
    trigger_items = [
        (_side(long_side, patterns["bullish_reversal_candle"] or patterns["volume_climax_buy"], patterns["bearish_reversal_candle"] or patterns["volume_climax_sell"]), "반전 캔들 확인", 15),
        (_side(long_side, state["price"]["close"] >= state["price"]["kc_mid"] or signals["VWAP_Bounce_Buy"], state["price"]["close"] <= state["price"]["kc_mid"] or signals["VWAP_Reject_Sell"]), "Keltner mid 복귀", 10),
        (_side(long_side, momentum["macd_hist_rising"], momentum["macd_hist_falling"]), "반전 모멘텀 개선", 10),
    ]
    if _side(long_side, not trend["close_above_vwap"], not trend["close_below_vwap"]):
        extra_conflicts = ["VWAP 방향 회복이 아직 완전하지 않습니다."]
    else:
        extra_conflicts = []
    return _build_result_from_groups(
        definition,
        state,
        long_side,
        "keltner_mean_reversion",
        setup_items,
        trigger_items,
        trigger_threshold=20,
        setup_threshold=20,
        triggered_phase="TRIGGERED",
        ready_phase="MEAN_REVERSION_READY",
        risk_template=_risk_template_reversal,
        invalidation_builder=_reversal_invalidation_text,
        extra_conflicts=extra_conflicts,
    )


def _evaluate_vwap_reclaim(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    trend = state["trend"]
    structure = state["structure"]
    volume_flow = state["volume_flow"]
    momentum = state["momentum"]
    signals = state["signals"]

    setup_items = [
        (_side(long_side, structure["pullback_near_fixed_vwap_long"] or structure["pullback_near_kc_mid_long"], structure["pullback_near_fixed_vwap_short"] or structure["pullback_near_kc_mid_short"]), "VWAP / AVWAP 재테스트 구간", 12),
        (_side(long_side, trend["close_above_ema21"], trend["close_below_ema21"]), "단기 추세 정렬", 10),
        (_side(long_side, volume_flow["money_flow_improving"], volume_flow["money_flow_weakening"]), "수급 방향 일치", 10),
        (_side(long_side, volume_flow["volume_support"], volume_flow["volume_support"]), "거래량 지지", 8),
    ]
    trigger_items = [
        (_side(long_side, signals["VWAP_Bounce_Buy"] or trend["vwap_reclaimed_long"], signals["VWAP_Reject_Sell"] or trend["vwap_reclaimed_short"]), "VWAP 재장악 / 거절 확인", 15),
        (_side(long_side, trend["close_above_vwap"], trend["close_below_vwap"]), "종가 기준 VWAP 우위", 10),
        (_side(long_side, signals["UTBot_Buy"] or momentum["macd_hist_rising"], signals["UTBot_Sell"] or momentum["macd_hist_falling"]), "후속 확인 신호", 10),
    ]
    return _build_result_from_groups(
        definition,
        state,
        long_side,
        "vwap_reclaim",
        setup_items,
        trigger_items,
        trigger_threshold=20,
        setup_threshold=18,
        triggered_phase="VWAP_RECLAIM_CONFIRMED",
        ready_phase="VWAP_RECLAIM_PENDING",
        risk_template=_risk_template_reversal,
        invalidation_builder=_reversal_invalidation_text,
    )


def _evaluate_morning_star_fib(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    volume_flow = state["volume_flow"]
    momentum = state["momentum"]
    signals = state["signals"]
    patterns = state["patterns"]
    structure = state["structure"]

    fib_support_long = any(signals[key] for key in ("Fib_50_Support", "Fib_618_Support", "Fib_618_Reclaim", "Fib_Confluence_Buy"))
    fib_support_short = any(signals[key] for key in ("Fib_50_Resistance", "Fib_618_Resistance", "Fib_618_Breakdown", "Fib_Confluence_Sell"))
    setup_items = [
        (_side(long_side, fib_support_long, fib_support_short), "Fib 0.5 / 0.618 골든존 지지", 18),
        (_side(long_side, structure["lower_zone"] or structure["pullback_near_fixed_vwap_long"], structure["upper_zone"] or structure["pullback_near_fixed_vwap_short"]), "가격 구조상 되돌림 완료", 12),
        (_side(long_side, volume_flow["money_flow_improving"], volume_flow["money_flow_weakening"]), "자금흐름 확인", 8),
        (_side(long_side, structure["price_change_5"] < 0, structure["price_change_5"] > 0), "직전 조정 파동 존재", 7),
    ]
    trigger_items = [
        (_side(long_side, patterns["morning_star"] or patterns["bullish_reversal_candle"], patterns["evening_star"] or patterns["bearish_reversal_candle"]), "패턴 캔들 완성", 15),
        (_side(long_side, signals["VWAP_Bounce_Buy"] or state["price"]["close"] >= state["price"]["ema8"], signals["VWAP_Reject_Sell"] or state["price"]["close"] <= state["price"]["ema8"]), "3번째 봉 기준선 회복", 10),
        (_side(long_side, momentum["macd_hist_rising"], momentum["macd_hist_falling"]), "모멘텀 개선", 10),
    ]
    return _build_result_from_groups(
        definition,
        state,
        long_side,
        "morning_star_fib",
        setup_items,
        trigger_items,
        trigger_threshold=18,
        setup_threshold=20,
        triggered_phase="FIB_CONFIRM",
        ready_phase="FIB_GOLDEN_ZONE_WAIT",
        risk_template=_risk_template_reversal,
        invalidation_builder=_reversal_invalidation_text,
    )


def _evaluate_fractal_breakout(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    trend = state["trend"]
    volume_flow = state["volume_flow"]
    momentum = state["momentum"]
    patterns = state["patterns"]
    structure = state["structure"]
    signals = state["signals"]

    setup_items = [
        (_side(long_side, trend["close_above_ema21"], trend["close_below_ema21"]), "EMA21 방향 우위", 12),
        (_side(long_side, np.isfinite(structure["recent_fractal_high"]), np.isfinite(structure["recent_fractal_low"])), "최근 유효 fractal 존재", 10),
        (_side(long_side, volume_flow["volume_support"], volume_flow["volume_support"]), "거래량 준비", 8),
        (_side(long_side, trend["adx_strong"], trend["adx_strong"]), "추세 강도 확인", 8),
    ]
    trigger_items = [
        (_side(long_side, structure["fractal_breakout_long"], structure["fractal_breakout_short"]), "fractal 돌파 / 이탈 확정", 15),
        (_side(long_side, patterns["fractal_high"] or signals["Channel_Breakout_Bull"], patterns["fractal_low"] or signals["Channel_Breakdown_Bear"]), "fractal 시그널 동반", 10),
        (_side(long_side, volume_flow["volume_burst"], volume_flow["volume_burst"]), "돌파 거래량 증가", 5),
        (_side(long_side, momentum["macd_hist_rising"], momentum["macd_hist_falling"]), "후속 모멘텀 정렬", 5),
    ]
    return _build_result_from_groups(
        definition,
        state,
        long_side,
        "fractal_breakout",
        setup_items,
        trigger_items,
        trigger_threshold=18,
        setup_threshold=18,
        triggered_phase="FRACTAL_BREAKOUT_CONFIRMED",
        ready_phase="FRACTAL_BREAKOUT_PENDING",
        risk_template=_risk_template_breakout,
        invalidation_builder=_breakout_invalidation_text,
    )


def _evaluate_anchored_vwap(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    trend = state["trend"]
    structure = state["structure"]
    volume_flow = state["volume_flow"]
    momentum = state["momentum"]
    patterns = state["patterns"]
    signals = state["signals"]

    setup_items = [
        (_side(long_side, trend["fixed_vwap_holding_long"], trend["fixed_vwap_holding_short"]), "Anchored VWAP 방향 유지", 15),
        (_side(long_side, structure["pullback_near_fixed_vwap_long"], structure["pullback_near_fixed_vwap_short"]), "AVWAP 리테스트 구간", 12),
        (_side(long_side, trend["ema21_above_ma50"], trend["ema21_below_ma50"]), "상위 추세 정렬", 10),
        (_side(long_side, volume_flow["volume_support"], volume_flow["volume_support"]), "거래량 바닥 붕괴 없음", 8),
    ]
    trigger_items = [
        (_side(long_side, signals["VWAP_Bounce_Buy"] or patterns["bullish_reversal_candle"], signals["VWAP_Reject_Sell"] or patterns["bearish_reversal_candle"]), "AVWAP 반등 / 거절 캔들", 15),
        (_side(long_side, trend["close_above_fixed_vwap"], trend["close_below_fixed_vwap"]), "종가 기준 AVWAP 유지", 10),
        (_side(long_side, signals["UTBot_Buy"] or momentum["macd_hist_rising"], signals["UTBot_Sell"] or momentum["macd_hist_falling"]), "후속 추세 확인", 10),
    ]
    return _build_result_from_groups(
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
        risk_template=_risk_template_trend,
        invalidation_builder=_trend_invalidation_text,
    )


def _evaluate_accumulation_pattern(definition: StrategyDefinition, state: dict) -> StrategyResult:
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
    return _build_result_from_groups(
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
        risk_template=_risk_template_trend,
        invalidation_builder=_trend_invalidation_text,
    )


def _evaluate_poc_rotation(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    structure = state["structure"]
    volume_flow = state["volume_flow"]
    trend = state["trend"]
    momentum = state["momentum"]
    signals = state["signals"]

    setup_items = [
        (_side(long_side, structure["near_vp_poc"] or structure["near_vp_val"] or structure["inside_value_area"], structure["near_vp_poc"] or structure["near_vp_vah"] or structure["inside_value_area"]), "POC / Value Area 근접", 15),
        (_side(long_side, signals["VP_VAL_Support"] or trend["close_above_vwap"], signals["VP_VAH_Resistance"] or trend["close_below_vwap"]), "Value Area 지지/저항 확인", 10),
        (_side(long_side, volume_flow["volume_support"], volume_flow["volume_support"]), "회전 매매용 거래량 유지", 8),
        (_side(long_side, volume_flow["money_flow_improving"], volume_flow["money_flow_weakening"]), "수급 방향 일치", 7),
    ]
    trigger_items = [
        (_side(long_side, signals["Volume_POC_Breakout"] or (structure["near_vp_poc"] and trend["close_above_vwap"]), signals["Volume_POC_Breakdown"] or (structure["near_vp_poc"] and trend["close_below_vwap"])), "POC 재장악 / 이탈", 15),
        (_side(long_side, momentum["macd_hist_rising"], momentum["macd_hist_falling"]), "회전 모멘텀 확인", 10),
        (_side(long_side, volume_flow["volume_burst"] or signals["VP_VAL_Support"], volume_flow["volume_burst"] or signals["VP_VAH_Resistance"]), "Value Area 리액션 동반", 10),
    ]
    return _build_result_from_groups(
        definition,
        state,
        long_side,
        "poc_rotation",
        setup_items,
        trigger_items,
        trigger_threshold=18,
        setup_threshold=18,
        triggered_phase="POC_RECLAIM_CONFIRMED",
        ready_phase="VALUE_ROTATION_READY",
        risk_template=_risk_template_breakout,
        invalidation_builder=_breakout_invalidation_text,
    )


def _evaluate_ichimoku_breakout(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    levels = state["levels"]
    trend = state["trend"]
    volume_flow = state["volume_flow"]
    momentum = state["momentum"]
    signals = state["signals"]

    above_cloud = np.isfinite(levels["cloud_top"]) and state["price"]["close"] >= levels["cloud_top"]
    below_cloud = np.isfinite(levels["cloud_bottom"]) and state["price"]["close"] <= levels["cloud_bottom"]
    tk_bull = signals["TK_Cross_Bull"] or (levels["tenkan"] >= levels["kijun"])
    tk_bear = signals["TK_Cross_Bear"] or (levels["tenkan"] <= levels["kijun"])
    setup_items = [
        (_side(long_side, above_cloud, below_cloud), "구름대 상/하단 이탈", 15),
        (_side(long_side, tk_bull, tk_bear), "Tenkan / Kijun 정렬", 10),
        (_side(long_side, trend["adx_strong"], trend["adx_strong"]), "추세 강도 확인", 10),
        (_side(long_side, volume_flow["volume_support"], volume_flow["volume_support"]), "구름 돌파 거래량 준비", 10),
    ]
    trigger_items = [
        (_side(long_side, signals["Kumo_Breakout_Bull"] or signals["CS_Ichimoku_Breakout_Buy"], signals["Kumo_Breakout_Bear"]), "Kumo 돌파 신호 발생", 15),
        (_side(long_side, signals["TK_Cross_Bull"] or tk_bull, signals["TK_Cross_Bear"] or tk_bear), "TK 교차 확인", 10),
        (_side(long_side, momentum["macd_hist_rising"], momentum["macd_hist_falling"]), "모멘텀 후속 확장", 10),
    ]
    return _build_result_from_groups(
        definition,
        state,
        long_side,
        "ichimoku_breakout",
        setup_items,
        trigger_items,
        trigger_threshold=18,
        setup_threshold=18,
        triggered_phase="ICHI_BREAKOUT_CONFIRMED",
        ready_phase="ICHI_PENDING",
        risk_template=_risk_template_breakout,
        invalidation_builder=_breakout_invalidation_text,
    )


def _evaluate_fractal_alligator(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    trend = state["trend"]
    structure = state["structure"]
    volume_flow = state["volume_flow"]
    momentum = state["momentum"]
    signals = state["signals"]
    patterns = state["patterns"]

    setup_items = [
        (_side(long_side, trend["close_above_ema21"] and trend["ema21_above_ma50"], trend["close_below_ema21"] and trend["ema21_below_ma50"]), "Alligator 대체 추세 정렬", 15),
        (_side(long_side, np.isfinite(structure["recent_fractal_high"]), np.isfinite(structure["recent_fractal_low"])), "fractal 레벨 준비", 10),
        (_side(long_side, trend["adx_expanding"], trend["adx_expanding"]), "sleeping → awakening 추세 강화", 10),
        (_side(long_side, volume_flow["volume_support"], volume_flow["volume_support"]), "거래량 유지", 10),
    ]
    trigger_items = [
        (_side(long_side, structure["fractal_breakout_long"], structure["fractal_breakout_short"]), "fractal 돌파", 15),
        (_side(long_side, signals["Hull_Turn_Bull"] or signals["UTBot_Buy"], signals["Hull_Turn_Bear"] or signals["UTBot_Sell"]), "추세 전환 보조 신호", 10),
        (_side(long_side, patterns["fractal_high"] or momentum["macd_hist_rising"], patterns["fractal_low"] or momentum["macd_hist_falling"]), "돌파 후 방향성 유지", 10),
    ]
    return _build_result_from_groups(
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
        risk_template=_risk_template_trend,
        invalidation_builder=_trend_invalidation_text,
    )


def _evaluate_chaikin_flow(definition: StrategyDefinition, state: dict) -> StrategyResult:
    long_side = definition.direction == "LONG"
    volume_flow = state["volume_flow"]
    momentum = state["momentum"]
    structure = state["structure"]
    trend = state["trend"]
    signals = state["signals"]

    setup_items = [
        (_side(long_side, volume_flow["chaikin_positive"], volume_flow["chaikin_negative"]), "Chaikin 방향 전환", 15),
        (_side(long_side, volume_flow["cmf_positive"], volume_flow["cmf_negative"]), "CMF 방향 동조", 10),
        (_side(long_side, structure["lower_zone"] or structure["price_change_5"] <= -2.0, structure["upper_zone"] or structure["price_change_5"] >= 2.0), "가격은 아직 바닥/천장권", 10),
        (_side(long_side, volume_flow["volume_support"], volume_flow["volume_support"]), "수급 유입 유지", 10),
    ]
    trigger_items = [
        (_side(long_side, volume_flow["chaikin_cross_up"] or signals["CMF_Bull"], volume_flow["chaikin_cross_down"] or signals["CMF_Bear"]), "Chaikin / CMF 트리거", 15),
        (_side(long_side, trend["close_above_vwap"] or state["price"]["close"] >= state["price"]["ema8"], trend["close_below_vwap"] or state["price"]["close"] <= state["price"]["ema8"]), "가격 확인 봉", 10),
        (_side(long_side, momentum["macd_hist_rising"], momentum["macd_hist_falling"]), "모멘텀 개선", 10),
    ]
    return _build_result_from_groups(
        definition,
        state,
        long_side,
        "chaikin_flow",
        setup_items,
        trigger_items,
        trigger_threshold=18,
        setup_threshold=18,
        triggered_phase="CHAIKIN_CONFIRMED",
        ready_phase="CHAIKIN_READY",
        risk_template=_risk_template_reversal,
        invalidation_builder=_reversal_invalidation_text,
    )


def _build_result_from_groups(
    definition: StrategyDefinition,
    state: dict,
    long_side: bool,
    family: str,
    setup_items: list[tuple[bool, str, int]],
    trigger_items: list[tuple[bool, str, int]],
    trigger_threshold: float,
    setup_threshold: float,
    triggered_phase: str,
    ready_phase: str,
    risk_template,
    invalidation_builder,
    extra_conflicts: list[str] | None = None,
) -> StrategyResult:
    setup_score, setup_matched, setup_missing = _score_group(setup_items)
    trigger_score, trigger_matched, trigger_missing = _score_group(trigger_items)
    trigger_passed = trigger_score >= trigger_threshold
    phase = triggered_phase if trigger_passed else ready_phase if setup_score >= setup_threshold else "SETUP_INVALID"
    stop_loss, target_1, target_2, rr = risk_template(state, long_side)
    conflict_reasons = _default_conflicts(state, long_side)
    if extra_conflicts:
        conflict_reasons.extend(extra_conflicts)
    conflict_reasons = _ordered_unique(conflict_reasons)
    risk_score = _risk_score(stop_loss, target_1, state["price"]["entry"], rr, conflict_reasons)
    total_score = _total_score(setup_score, trigger_score, risk_score)
    status = _status_from_score(total_score, trigger_passed, rr, setup_score, trigger_score, phase)
    entry_hint = _entry_hint(status, phase, long_side, family)
    entry_price = _entry_price(state, long_side, family, phase, status)
    matched = setup_matched + trigger_matched
    missing = setup_missing + trigger_missing
    failed = _failed_from_conflicts(conflict_reasons)
    explanation = _build_explanation(definition.label, status, matched, missing, conflict_reasons)
    return StrategyResult(
        id=definition.id,
        label=definition.label,
        direction=definition.direction,
        category=definition.category,
        score=total_score,
        status=status,
        phase=phase,
        entry_hint=entry_hint,
        entry_price=entry_price,
        setup_score=setup_score,
        trigger_score=trigger_score,
        risk_score=risk_score,
        matched_conditions=matched,
        missing_conditions=missing,
        failed_conditions=failed,
        stop_loss=stop_loss,
        target_1=target_1,
        target_2=target_2,
        rr=rr,
        conflict_reasons=conflict_reasons,
        explanation=explanation,
        last5_change=_recent_change_notes(state, long_side),
        invalidation_text=invalidation_builder(state, long_side, stop_loss),
        note=_phase_note(phase, conflict_reasons),
    )


def _build_summary(visible: list[StrategyResult], results: list[StrategyResult]) -> StrategySummary:
    bullish = [item for item in visible if item.direction == "LONG"]
    bearish = [item for item in visible if item.direction == "SHORT"]
    active_count = sum(1 for item in visible if item.status == "ACTIVE")
    top_strategy = visible[0].to_dict() if visible else None
    secondary = [item.to_dict() for item in visible[1:3]]
    long_short_bias = "BALANCED"
    if len(bullish) > len(bearish):
        long_short_bias = "LONG"
    elif len(bearish) > len(bullish):
        long_short_bias = "SHORT"
    elif bullish and bearish:
        top_long = max(item.score for item in bullish)
        top_short = max(item.score for item in bearish)
        if top_long > top_short:
            long_short_bias = "LONG"
        elif top_short > top_long:
            long_short_bias = "SHORT"
    conflict_level = _conflict_level(bullish, bearish)
    dominant_reasons = top_strategy.get("matched_conditions", [])[:3] if top_strategy else []
    opposing_reasons: list[str] = []
    if top_strategy:
        opposite_pool = bearish if top_strategy["direction"] == "LONG" else bullish
        if opposite_pool:
            opposing_reasons = [f"{opposite_pool[0].label} {opposite_pool[0].score:.0f}점"] + opposite_pool[0].conflict_reasons[:2]
        else:
            opposing_reasons = top_strategy.get("conflict_reasons", [])[:2]
    return StrategySummary(
        active_count=active_count,
        visible_count=len(visible),
        bullish_count=len(bullish),
        bearish_count=len(bearish),
        long_short_bias=long_short_bias,
        conflict_level=conflict_level,
        top_strategy=top_strategy,
        secondary_strategies=secondary,
        hidden_invalid_count=max(len(results) - len(visible), 0),
        dominant_reasons=dominant_reasons,
        opposing_reasons=opposing_reasons,
    )


def _conflict_level(bullish: list[StrategyResult], bearish: list[StrategyResult]) -> str:
    if not bullish or not bearish:
        return "LOW"
    top_long = max(item.score for item in bullish)
    top_short = max(item.score for item in bearish)
    diff = abs(top_long - top_short)
    score = 1.0
    if min(len(bullish), len(bearish)) >= 2:
        score += 1.0
    if diff <= 10:
        score += 1.0
    elif diff <= 20:
        score += 0.5
    if min(top_long, top_short) >= 60:
        score += 1.0
    if score >= 3.0:
        return "HIGH"
    if score >= 1.5:
        return "MEDIUM"
    return "LOW"


def _score_group(items: list[tuple[bool, str, int]]) -> tuple[float, list[str], list[str]]:
    score = 0.0
    matched: list[str] = []
    missing: list[str] = []
    for condition, label, weight in items:
        if condition:
            score += float(weight)
            matched.append(label)
        else:
            missing.append(label)
    return score, matched, missing


def _risk_template_trend(state: dict, long_side: bool) -> tuple[float | None, float | None, float | None, float | None]:
    entry = state["price"]["entry"]
    atr = state["price"]["atr"]
    ma50 = state["price"]["ma50"]
    swing_low = state["structure"]["swing_low_5"]
    swing_high = state["structure"]["swing_high_5"]
    prev_extreme_high = state["structure"]["swing_high_20"]
    prev_extreme_low = state["structure"]["swing_low_20"]
    channel_up = state["price"]["price_channel_up"]
    channel_low = state["price"]["price_channel_low"]
    if long_side:
        stop_loss = min(swing_low, ma50) - (0.3 * atr)
        target_1 = max(prev_extreme_high, entry + (1.2 * atr))
        target_2 = max(channel_up, entry + (2.0 * atr))
    else:
        stop_loss = max(swing_high, ma50) + (0.3 * atr)
        target_1 = min(prev_extreme_low, entry - (1.2 * atr))
        target_2 = min(channel_low, entry - (2.0 * atr))
    return stop_loss, target_1, target_2, _rr(entry, stop_loss, target_1)


def _risk_template_breakout(state: dict, long_side: bool) -> tuple[float | None, float | None, float | None, float | None]:
    entry = state["price"]["entry"]
    atr = state["price"]["atr"]
    breakout_level = state["structure"]["breakout_level"]
    breakdown_level = state["structure"]["breakdown_level"]
    latest_low = state["price"]["low"]
    latest_high = state["price"]["high"]
    channel_up = state["price"]["price_channel_up"]
    channel_low = state["price"]["price_channel_low"]
    if long_side:
        stop_loss = min(breakout_level, latest_low) - (0.5 * atr)
        target_1 = entry + (1.5 * atr)
        target_2 = max(channel_up, entry + (2.5 * atr))
    else:
        stop_loss = max(breakdown_level, latest_high) + (0.5 * atr)
        target_1 = entry - (1.5 * atr)
        target_2 = min(channel_low, entry - (2.5 * atr))
    return stop_loss, target_1, target_2, _rr(entry, stop_loss, target_1)


def _risk_template_reversal(state: dict, long_side: bool) -> tuple[float | None, float | None, float | None, float | None]:
    entry = state["price"]["entry"]
    atr = state["price"]["atr"]
    swing_low = state["structure"]["swing_low_5"]
    swing_high = state["structure"]["swing_high_5"]
    vwap = state["levels"]["vwap"]
    ema21 = state["levels"]["ema21"]
    prev_extreme_high = state["structure"]["swing_high_20"]
    prev_extreme_low = state["structure"]["swing_low_20"]
    if long_side:
        stop_loss = swing_low - (0.5 * atr)
        target_1 = max(vwap, ema21, entry + (1.0 * atr))
        target_2 = max(prev_extreme_high, entry + (2.0 * atr))
    else:
        stop_loss = swing_high + (0.5 * atr)
        target_1 = min(vwap, ema21, entry - (1.0 * atr))
        target_2 = min(prev_extreme_low, entry - (2.0 * atr))
    return stop_loss, target_1, target_2, _rr(entry, stop_loss, target_1)


def _risk_score(stop_loss: float | None, target_1: float | None, entry: float, rr: float | None, conflicts: list[str]) -> float:
    if stop_loss is None or target_1 is None:
        return 0.0
    score = 5.0
    if rr is not None:
        if rr >= 2.0:
            score += 10.0
        elif rr >= 1.5:
            score += 8.0
        elif rr >= 1.3:
            score += 6.0
        elif rr >= 1.0:
            score += 3.0
    stop_gap = abs(entry - stop_loss) / max(entry, 0.01)
    if stop_gap <= 0.08:
        score += 5.0
    elif stop_gap <= 0.12:
        score += 3.0
    elif stop_gap <= 0.2:
        score += 1.0
    penalty = min(len(conflicts) * 2.5, 10.0)
    return max(0.0, min(20.0, score - penalty))


def _total_score(setup_score: float, trigger_score: float, risk_score: float) -> float:
    return max(0.0, min(100.0, setup_score + trigger_score + risk_score))


def _status_from_score(
    total_score: float,
    trigger_passed: bool,
    rr: float | None,
    setup_score: float = 0.0,
    trigger_score: float = 0.0,
    phase: str = "",
) -> str:
    phase = str(phase or "").upper()
    trigger_wait_phases = {
        "PULLBACK_WAIT",
        "BREAKOUT_PENDING",
        "SQUEEZE_READY",
        "REVERSAL_READY",
        "DIVERGENCE_READY",
        "TREND_ALIGNED",
        "MEAN_REVERSION_READY",
        "VWAP_RECLAIM_PENDING",
        "FIB_GOLDEN_ZONE_WAIT",
        "FRACTAL_BREAKOUT_PENDING",
        "AVWAP_HOLD",
        "ACCUMULATION_READY",
        "VALUE_ROTATION_READY",
        "ICHI_PENDING",
        "ALLIGATOR_AWAKENING",
        "CHAIKIN_READY",
        "KELTNER_BREAKOUT_PENDING",
    }
    if total_score >= 80 and trigger_passed and (rr is None or rr >= 1.3):
        return "ACTIVE"
    if trigger_passed:
        return "CONFIRMING"
    if phase in trigger_wait_phases or trigger_score >= 15:
        if total_score >= 60 or (setup_score >= 25 and trigger_score >= 10):
            return "TRIGGER_WAIT"
        if setup_score >= 20 or total_score >= 50:
            return "READY"
        if setup_score >= 10 or total_score >= 35:
            return "INTEREST"
        return "INVALID"
    if setup_score >= 20 or total_score >= 55:
        return "READY"
    if setup_score >= 10 or total_score >= 35:
        return "INTEREST"
    return "INVALID"


def _entry_hint(status: str, phase: str, long_side: bool, family: str) -> str:
    if status == "CONFIRMING":
        return "확인 진행"
    if status == "INVALID":
        return "무효"
    if family == "breakout" and phase == "BREAKOUT_PENDING":
        return "돌파 확인 대기"
    if family == "squeeze" and phase == "SQUEEZE_READY":
        return "돌파 확인 대기"
    if family == "trend_pullback" and phase == "PULLBACK_WAIT":
        return "눌림 대기"
    if family == "reversal" and phase == "REVERSAL_READY":
        return "확인 캔들 대기"
    if family == "obv_divergence" and phase == "DIVERGENCE_READY":
        return "확인 캔들 대기"
    if family == "supertrend_psar" and phase == "TREND_ALIGNED":
        return "추세 확인 대기"
    return "현재가 추격 가능" if status == "ACTIVE" else ("눌림 대기" if long_side else "반등 대기")


def _default_conflicts(state: dict, long_side: bool) -> list[str]:
    conflicts: list[str] = []
    price = state["price"]
    levels = state["levels"]
    trend = state["trend"]
    patterns = state["patterns"]
    atr = price["atr"]
    close = price["close"]
    nearest_resistance = levels["nearest_resistance"]
    nearest_support = levels["nearest_support"]
    if long_side:
        if np.isfinite(nearest_resistance) and (nearest_resistance - close) <= atr:
            conflicts.append("가까운 저항대가 1 ATR 안쪽에 있습니다.")
        if patterns["bearish_divergence"]:
            conflicts.append("반대 방향 다이버전스가 남아 있습니다.")
        if trend["bearish_trend_stack"] and trend["close_below_vwap"]:
            conflicts.append("상위 추세가 아직 완전히 상방으로 돌지 않았습니다.")
    else:
        if np.isfinite(nearest_support) and (close - nearest_support) <= atr:
            conflicts.append("가까운 지지대가 1 ATR 안쪽에 있습니다.")
        if patterns["bullish_divergence"]:
            conflicts.append("반대 방향 다이버전스가 남아 있습니다.")
        if trend["bullish_trend_stack"] and trend["close_above_vwap"]:
            conflicts.append("상위 추세가 아직 완전히 하방으로 돌지 않았습니다.")
    if state["signals"].get("CS_Conflict_Warning"):
        conflicts.append("기존 엔진도 방향 충돌을 경고하고 있습니다.")
    return _ordered_unique(conflicts)


def _recent_change_notes(state: dict, long_side: bool) -> list[str]:
    frame = state["frame"]
    if frame.empty:
        return []
    recent = frame.tail(5)
    notes: list[str] = []
    close_now = _scalar(recent.iloc[-1].get("Close"))
    close_then = _scalar(recent.iloc[0].get("Close"), close_now)
    change_pct = _pct_change(close_now, close_then)
    notes.append(f"최근 5봉 가격 변화 {change_pct:+.1f}%")
    volume_ratio = _scalar(recent.iloc[-1].get("Volume_Ratio_20"), 1.0)
    notes.append(f"최근 거래량은 20일 평균 대비 {volume_ratio:.1f}배")
    macd_delta = _scalar(recent.iloc[-1].get("MACD_Hist")) - _scalar(recent.iloc[0].get("MACD_Hist"))
    notes.append(f"MACD 히스토그램은 5봉 기준 {macd_delta:+.3f} 변화")
    if long_side:
        notes.append("VWAP 위 안착 여부가 마지막 확인 포인트입니다." if state["trend"]["close_above_vwap"] else "VWAP 재회복 여부가 마지막 확인 포인트입니다.")
    else:
        notes.append("VWAP 아래 유지 여부가 마지막 확인 포인트입니다." if state["trend"]["close_below_vwap"] else "VWAP 재이탈 여부가 마지막 확인 포인트입니다.")
    return notes[:4]


def _build_explanation(label: str, status: str, matched: list[str], missing: list[str], conflicts: list[str]) -> str:
    status_text = {
        "ACTIVE": "강하게 성립했습니다.",
        "WATCH": "부분 성립 중입니다.",
        "WEAK_WATCH": "감시 구간입니다.",
        "INVALID": "아직 조건이 부족합니다.",
    }.get(status, "부분 성립 중입니다.")
    good = ", ".join(matched[:3]) or "핵심 근거가 아직 약합니다"
    weak = ", ".join((missing + conflicts)[:3])
    if weak:
        return f"{label} 전략이 {status_text} {good}는 확인됐지만, {weak}는 추가 확인이 필요합니다."
    return f"{label} 전략이 {status_text} {good}가 동시에 맞물렸습니다."


def _phase_note(phase: str, conflicts: list[str]) -> str:
    phase_notes = {
        "TRIGGERED": "실제 트리거가 확인된 상태입니다.",
        "PULLBACK_WAIT": "눌림 뒤 재반등 확인을 기다리는 구간입니다.",
        "BREAKOUT_PENDING": "첫 돌파는 나왔지만 확인 봉이 더 필요합니다.",
        "BREAKOUT_CONFIRMED": "돌파와 유지 조건이 함께 맞물렸습니다.",
        "SQUEEZE_READY": "압축은 충분하지만 방향 분출이 남았습니다.",
        "REVERSAL_READY": "반전 환경은 좋지만 확인 캔들이 더 필요합니다.",
        "DOUBLE_CONFIRMED": "SuperTrend와 PSAR가 같은 방향으로 정렬됐습니다.",
        "TREND_ALIGNED": "추세 기준선은 정렬됐지만 진입 트리거는 약합니다.",
        "DIVERGENCE_READY": "다이버전스는 있지만 확인 트리거가 남았습니다.",
        "DIVERGENCE_CONFIRMED": "다이버전스 뒤 확인 신호가 붙었습니다.",
        "SETUP_INVALID": "환경 자체가 아직 전략형이 아닙니다.",
    }
    note = phase_notes.get(phase, "")
    if conflicts:
        note = f"{note} 반대 근거도 함께 확인해야 합니다."
    return note


def _build_explanation(label: str, status: str, matched: list[str], missing: list[str], conflicts: list[str]) -> str:
    status_text = {
        "ACTIVE": "강하게 성립했습니다.",
        "CONFIRMING": "확인 진행 단계입니다.",
        "TRIGGER_WAIT": "트리거 대기 단계입니다.",
        "READY": "준비 단계입니다.",
        "INTEREST": "관심 단계입니다.",
        "INVALID": "아직 조건이 부족합니다.",
    }.get(status, "준비 단계입니다.")
    good = ", ".join(matched[:3]) or "핵심 근거가 아직 충분하지 않습니다"
    weak = ", ".join((missing + conflicts)[:3])
    if weak:
        return f"{label} 전략은 {status_text} {good}는 확인됐지만, {weak}은 추가 확인이 필요합니다."
    return f"{label} 전략은 {status_text} {good}가 함께 맞물리고 있습니다."


def _trend_invalidation_text(state: dict, long_side: bool, stop_loss: float | None) -> str:
    if stop_loss is None:
        return "핵심 지지/저항 이탈 시 무효"
    if long_side:
        return f"EMA50 또는 최근 스윙로우 하향 이탈 시 무효 ({stop_loss:.2f} 아래)."
    return f"EMA50 또는 최근 스윙하이 상향 회복 시 무효 ({stop_loss:.2f} 위)."


def _breakout_invalidation_text(state: dict, long_side: bool, stop_loss: float | None) -> str:
    level = state["structure"]["breakout_level"] if long_side else state["structure"]["breakdown_level"]
    if stop_loss is None:
        return "돌파/이탈 레벨 재진입 시 무효"
    if long_side:
        return f"돌파 레벨 {level:.2f} 재이탈 또는 {stop_loss:.2f} 하향 시 무효."
    return f"이탈 레벨 {level:.2f} 재회복 또는 {stop_loss:.2f} 상향 시 무효."


def _reversal_invalidation_text(state: dict, long_side: bool, stop_loss: float | None) -> str:
    if stop_loss is None:
        return "직전 저점/고점 이탈 시 무효"
    if long_side:
        return f"직전 저점 또는 {stop_loss:.2f} 이탈 시 반전 시나리오 무효."
    return f"직전 고점 또는 {stop_loss:.2f} 회복 시 반전 시나리오 무효."


def _side(long_side: bool, long_value: bool, short_value: bool) -> bool:
    return bool(long_value if long_side else short_value)


def _failed_from_conflicts(conflicts: list[str]) -> list[str]:
    return [text for text in conflicts[:3]]


def _rr(entry: float, stop_loss: float | None, target_1: float | None) -> float | None:
    if stop_loss is None or target_1 is None:
        return None
    risk = abs(entry - stop_loss)
    reward = abs(target_1 - entry)
    if risk <= 1e-9:
        return None
    return reward / risk


def _nearest_resistance(close: float, levels: Iterable[float]) -> float:
    candidates = [float(level) for level in levels if np.isfinite(level) and level >= close]
    return min(candidates) if candidates else float("inf")


def _nearest_support(close: float, levels: Iterable[float]) -> float:
    candidates = [float(level) for level in levels if np.isfinite(level) and level <= close]
    return max(candidates) if candidates else float("-inf")


def _near_zone(price: float, level: float, atr: float, atr_multiple: float) -> bool:
    if not np.isfinite(level):
        return False
    return abs(price - level) <= (atr * atr_multiple)


def _bool_latest(df: pd.DataFrame, column: str) -> bool:
    if column not in df.columns or df.empty:
        return False
    value = df[column].iloc[-1]
    if pd.isna(value):
        return False
    return bool(value)


def _bool_recent(df: pd.DataFrame, column: str, bars: int) -> bool:
    if column not in df.columns or df.empty:
        return False
    for value in df[column].tail(max(bars, 1)):
        if pd.isna(value):
            continue
        if bool(value):
            return True
    return False


def _series_max(df: pd.DataFrame, column: str, default: float) -> float:
    if column not in df.columns or df.empty:
        return default
    return _scalar(df[column].max(), default)


def _series_min(df: pd.DataFrame, column: str, default: float) -> float:
    if column not in df.columns or df.empty:
        return default
    return _scalar(df[column].min(), default)


def _series_mean(df: pd.DataFrame, column: str, default: float) -> float:
    if column not in df.columns or df.empty:
        return default
    return _scalar(df[column].mean(), default)


def _scalar(value, default: float = 0.0) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return default
    if np.isnan(numeric):
        return default
    return numeric


def _pct_change(current: float, previous: float) -> float:
    if abs(previous) <= 1e-9:
        return 0.0
    return ((current - previous) / previous) * 100.0


def _pct_of(value: float, base: float) -> float:
    if abs(base) <= 1e-9:
        return 0.0
    return (value / base) * 100.0


def _round_or_none(value: float | None) -> float | None:
    if value is None:
        return None
    if not np.isfinite(value):
        return None
    return round(float(value), 2)


def _ordered_unique(items: Iterable[str]) -> list[str]:
    seen = set()
    ordered: list[str] = []
    for item in items:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        ordered.append(text)
    return ordered


def _finite_max(values: Iterable[float], default: float) -> float:
    candidates = [float(value) for value in values if np.isfinite(value)]
    return max(candidates) if candidates else default


def _finite_min(values: Iterable[float], default: float) -> float:
    candidates = [float(value) for value in values if np.isfinite(value)]
    return min(candidates) if candidates else default


def _recent_flagged_level(df: pd.DataFrame, flag_column: str, price_column: str, default: float) -> float:
    if flag_column not in df.columns or price_column not in df.columns or df.empty:
        return default
    flagged = df[df[flag_column].fillna(False)]
    if flagged.empty:
        return default
    return _scalar(flagged[price_column].iloc[-1], default)


def _build_summary(visible: list[StrategyResult], results: list[StrategyResult]) -> StrategySummary:
    bullish = [item for item in visible if item.direction == "LONG"]
    bearish = [item for item in visible if item.direction == "SHORT"]
    active_count = sum(1 for item in visible if item.status == "ACTIVE")
    top_strategy = visible[0].to_dict() if visible else None
    secondary = [item.to_dict() for item in visible[1:3]]
    long_short_bias = "BALANCED"
    if len(bullish) > len(bearish):
        long_short_bias = "LONG"
    elif len(bearish) > len(bullish):
        long_short_bias = "SHORT"
    elif bullish and bearish:
        top_long = max(item.score for item in bullish)
        top_short = max(item.score for item in bearish)
        if top_long > top_short:
            long_short_bias = "LONG"
        elif top_short > top_long:
            long_short_bias = "SHORT"
    conflict_level = _conflict_level(bullish, bearish)
    dominant_reasons = top_strategy.get("matched_conditions", [])[:3] if top_strategy else []
    opposing_reasons: list[str] = []
    if top_strategy:
        opposite_pool = bearish if top_strategy["direction"] == "LONG" else bullish
        if opposite_pool:
            opposing_reasons = [f"{opposite_pool[0].label} {opposite_pool[0].score:.0f}점"] + opposite_pool[0].conflict_reasons[:2]
        else:
            opposing_reasons = top_strategy.get("conflict_reasons", [])[:2]
    return StrategySummary(
        active_count=active_count,
        visible_count=len(visible),
        bullish_count=len(bullish),
        bearish_count=len(bearish),
        long_short_bias=long_short_bias,
        conflict_level=conflict_level,
        top_strategy=top_strategy,
        secondary_strategies=secondary,
        hidden_invalid_count=max(len(results) - len(visible), 0),
        dominant_reasons=dominant_reasons,
        opposing_reasons=opposing_reasons,
    )


def _entry_price(state: dict, long_side: bool, family: str, phase: str, status: str) -> float | None:
    if status == "INVALID":
        return None
    current = state["price"]["entry"]
    price = state["price"]
    levels = state["levels"]
    structure = state["structure"]

    if status in {"ACTIVE", "CONFIRMING"}:
        return current

    if family in {"breakout", "squeeze"}:
        return structure["breakout_level"] if long_side else structure["breakdown_level"]
    if family == "keltner_breakout":
        return price["kc_upper"] if long_side else price["kc_lower"]
    if family == "ichimoku_breakout":
        ref = levels["cloud_top"] if long_side else levels["cloud_bottom"]
        return ref if np.isfinite(ref) else current
    if family in {"fractal_breakout", "fractal_alligator"}:
        ref = structure["recent_fractal_high"] if long_side else structure["recent_fractal_low"]
        return ref if np.isfinite(ref) else current
    if family in {"trend_pullback", "supertrend_psar"}:
        return _finite_max([price["ema21"], price["ma20"]], current) if long_side else _finite_min([price["ema21"], price["ma20"]], current)
    if family == "keltner_pullback":
        return price["kc_mid"]
    if family == "anchored_vwap":
        return levels["fixed_vwap"]
    if family == "vwap_reclaim":
        return levels["vwap"]
    if family == "keltner_mean_reversion":
        return levels["kc_mid"]
    if family in {"reversal", "obv_divergence", "chaikin_flow"}:
        return _finite_max([price["ema8"], levels["vwap"]], current) if long_side else _finite_min([price["ema8"], levels["vwap"]], current)
    if family == "morning_star_fib":
        ref = _finite_max([levels["fib_618"], levels["fib_50"]], current) if long_side else _finite_min([levels["fib_618"], levels["fib_50"]], current)
        return ref if np.isfinite(ref) else current
    if family == "accumulation_pattern":
        ref = _finite_max([levels["vp_poc"], levels["fixed_vwap"], structure["breakout_level"]], current)
        return ref if np.isfinite(ref) else current
    if family == "poc_rotation":
        ref = _finite_max([levels["vp_poc"], levels["vp_val"]], current) if long_side else _finite_min([levels["vp_poc"], levels["vp_vah"]], current)
        return ref if np.isfinite(ref) else current
    if phase in {"BREAKOUT_PENDING", "KELTNER_BREAKOUT_PENDING", "FRACTAL_BREAKOUT_PENDING", "ICHI_PENDING"}:
        return structure["breakout_level"] if long_side else structure["breakdown_level"]
    return current


def _entry_hint(status: str, phase: str, long_side: bool, family: str) -> str:
    if status == "INVALID":
        return "무효"
    phase_hints = {
        "BREAKOUT_PENDING": "돌파 확인 대기",
        "KELTNER_BREAKOUT_PENDING": "Keltner 돌파 확인 대기",
        "SQUEEZE_READY": "압축 해제 대기",
        "PULLBACK_WAIT": "눌림 대기",
        "REVERSAL_READY": "확인 캔들 대기",
        "DIVERGENCE_READY": "확인 캔들 대기",
        "TREND_ALIGNED": "추세 확인 대기",
        "MEAN_REVERSION_READY": "평균회귀 확인 대기",
        "VWAP_RECLAIM_PENDING": "VWAP 재장악 확인 대기",
        "FIB_GOLDEN_ZONE_WAIT": "골든존 반응 대기",
        "FRACTAL_BREAKOUT_PENDING": "fractal 돌파 대기",
        "AVWAP_HOLD": "AVWAP 지지 확인 대기",
        "ACCUMULATION_READY": "박스 상단 돌파 대기",
        "VALUE_ROTATION_READY": "POC 재장악 대기",
        "ICHI_PENDING": "구름 돌파 확인 대기",
        "ALLIGATOR_AWAKENING": "추세 각성 확인 대기",
        "CHAIKIN_READY": "자금 유입 확인 대기",
    }
    if phase in phase_hints:
        return phase_hints[phase]
    if family in {"breakout", "keltner_breakout", "fractal_breakout", "ichimoku_breakout"}:
        return "현재가 추격 가능" if status == "ACTIVE" else "돌파 확인 대기"
    if family in {"trend_pullback", "keltner_pullback", "anchored_vwap"}:
        return "현재가 추격 가능" if status == "ACTIVE" else ("눌림 대기" if long_side else "반등 대기")
    if family in {"reversal", "keltner_mean_reversion", "morning_star_fib", "chaikin_flow", "vwap_reclaim", "obv_divergence"}:
        return "현재가 추격 가능" if status == "ACTIVE" else "확인 캔들 대기"
    if family == "accumulation_pattern":
        return "박스 상단 돌파 대기" if status != "ACTIVE" else "현재가 추격 가능"
    if family == "poc_rotation":
        return "POC 재장악 확인 대기" if status != "ACTIVE" else "현재가 추격 가능"
    if family == "fractal_alligator":
        return "fractal 돌파 추격 가능" if status == "ACTIVE" else "추세 각성 대기"
    return "현재가 추격 가능" if status == "ACTIVE" else ("눌림 대기" if long_side else "반등 대기")


def _phase_note(phase: str, conflicts: list[str]) -> str:
    phase_notes = {
        "TRIGGERED": "실제 트리거가 확인된 상태입니다.",
        "PULLBACK_WAIT": "눌림 뒤 재반등 확인을 기다리는 구간입니다.",
        "BREAKOUT_PENDING": "첫 돌파는 나왔지만 확인 봉이 더 필요합니다.",
        "BREAKOUT_CONFIRMED": "돌파와 유지 조건이 함께 충족됐습니다.",
        "KELTNER_BREAKOUT_PENDING": "Keltner 외곽 밴드 안착 확인이 남아 있습니다.",
        "KELTNER_BREAKOUT_CONFIRMED": "Keltner 밴드 돌파가 추세 확장으로 이어지고 있습니다.",
        "SQUEEZE_READY": "압축은 충분하지만 방향 분출이 아직 필요합니다.",
        "REVERSAL_READY": "반전 환경은 좋지만 확인 캔들이 더 필요합니다.",
        "DOUBLE_CONFIRMED": "SuperTrend와 PSAR가 같은 방향으로 정렬됐습니다.",
        "TREND_ALIGNED": "추세 기준선은 정렬됐지만 진입 트리거는 약합니다.",
        "DIVERGENCE_READY": "다이버전스는 있지만 확인 트리거가 부족합니다.",
        "DIVERGENCE_CONFIRMED": "다이버전스 뒤 확인 신호가 붙었습니다.",
        "MEAN_REVERSION_READY": "과확장 되돌림은 시작됐지만 평균 복귀 확인이 더 필요합니다.",
        "VWAP_RECLAIM_PENDING": "VWAP 재장악 직전 단계로 확인 봉이 남아 있습니다.",
        "VWAP_RECLAIM_CONFIRMED": "VWAP 재장악과 종가 유지가 확인됐습니다.",
        "FIB_GOLDEN_ZONE_WAIT": "Fib 골든존 반응은 좋지만 패턴 완성은 아직입니다.",
        "FIB_CONFIRM": "Fib 골든존에서 반전 패턴이 확인됐습니다.",
        "FRACTAL_BREAKOUT_PENDING": "fractal 레벨은 준비됐지만 돌파는 아직입니다.",
        "FRACTAL_BREAKOUT_CONFIRMED": "fractal 돌파와 유지가 확인됐습니다.",
        "AVWAP_HOLD": "Anchored VWAP 지지 여부를 확인하는 단계입니다.",
        "AVWAP_CONFIRMED": "Anchored VWAP 위 유지와 반등이 확인됐습니다.",
        "ACCUMULATION_READY": "매집 유사 구조는 좋지만 박스 상단 돌파가 필요합니다.",
        "ACCUMULATION_CONFIRMED": "매집 유사 패턴 뒤 수급 동반 돌파가 확인됐습니다.",
        "VALUE_ROTATION_READY": "POC / Value Area 회전은 시작됐지만 확인 봉이 필요합니다.",
        "POC_RECLAIM_CONFIRMED": "POC 재장악 또는 이탈이 방향성 있게 확인됐습니다.",
        "ICHI_PENDING": "구름 돌파 직전 단계로 TK 확인이 더 필요합니다.",
        "ICHI_BREAKOUT_CONFIRMED": "Ichimoku 구름 돌파와 TK 정렬이 함께 확인됐습니다.",
        "ALLIGATOR_AWAKENING": "추세 스택은 각성 중이지만 fractal 돌파가 남아 있습니다.",
        "CHAIKIN_READY": "Chaikin 흐름은 개선됐지만 가격 확인 봉이 더 필요합니다.",
        "CHAIKIN_CONFIRMED": "Chaikin / CMF 흐름과 가격 확인이 함께 나왔습니다.",
        "SETUP_INVALID": "환경 자체가 아직 전략 성립에 부족합니다.",
    }
    note = phase_notes.get(phase, "")
    if conflicts:
        note = f"{note} 반대 근거도 함께 확인해야 합니다."
    return note
