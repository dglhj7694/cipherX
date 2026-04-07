# -*- coding: utf-8 -*-
from __future__ import annotations

import numpy as np
import pandas as pd

from config import *
from engine_committee import (
    append_note,
    default_action_label,
    downgrade_buy,
    downgrade_sell,
    judgment_side,
    promote_buy,
    promote_sell,
)


OBJECTIVE_BUY_LABELS = {"STRONG_BUY", "BUY", "WATCH_BUY"}
OBJECTIVE_SELL_LABELS = {"STRONG_SELL", "SELL", "WATCH_SELL"}
OBJECTIVE_SIGNAL_EXCLUDE = {"System_Turn_Bull", "System_Turn_Bear"}

# Objective layer treats combo scans as confirmation, not primary evidence.
OBJECTIVE_COMBO_BASE = {1: 1.8, 2: 1.2, 3: 0.6}


def objective_event_name(name):
    raw = str(name or "")
    if raw in SIGNAL_REGISTRY:
        return str(SIGNAL_REGISTRY.get(raw, {}).get("kor") or raw.replace("_", " "))
    if raw in COMBINED_SCAN_REGISTRY:
        return str(COMBINED_SCAN_REGISTRY.get(raw, {}).get("kor") or raw.replace("_", " "))
    return raw.replace("_", " ")


def objective_recent_registry_score(i, specs, bool_arrays, lookback, decay):
    score = 0.0
    strong_hits = 0
    hits = []
    for name, base, is_strong in specs:
        arr = bool_arrays.get(name)
        if arr is None:
            continue
        best = 0.0
        best_age = None
        max_age = min(i, lookback - 1)
        for age in range(max_age + 1):
            if arr[i - age]:
                cur = base * (decay ** age)
                if cur > best:
                    best = cur
                    best_age = age
        if best > 0:
            score += best
            hits.append((best, name, best_age))
            if is_strong:
                strong_hits += 1
    hits.sort(key=lambda x: x[0], reverse=True)
    return score, strong_hits, hits


def objective_action_label(label):
    return {
        "STRONG_BUY": "Objective strong buy",
        "BUY": "Objective buy",
        "WATCH_BUY": "Objective watch buy",
        "NEUTRAL": "Objective neutral",
        "MIXED": "Objective mixed",
        "WATCH_SELL": "Objective watch sell",
        "SELL": "Objective sell",
        "STRONG_SELL": "Objective strong sell",
    }.get(label, "Objective neutral")


def _label_from_scores(buy_score, sell_score, conflict_score):
    gap = float(buy_score - sell_score)
    if conflict_score >= 18 and abs(gap) < 10:
        return "MIXED"
    if gap >= 28:
        return "STRONG_BUY"
    if gap >= 12:
        return "BUY"
    if gap >= 4:
        return "WATCH_BUY"
    if gap <= -28:
        return "STRONG_SELL"
    if gap <= -12:
        return "SELL"
    if gap <= -4:
        return "WATCH_SELL"
    return "NEUTRAL"


def compute_objective_judgment(df, vol_ratio):
    if df is None or df.empty:
        return df

    idx = df.index
    N = lambda c, d=0: df.get(c, pd.Series(d, index=idx)).fillna(d)
    F = lambda c: df.get(c, pd.Series(False, index=idx)).fillna(False)

    close = df["Close"]
    ma50 = N("MA50", np.nan)
    ma200 = N("MA200", np.nan)
    rsi = N("RSI", 50.0)
    wt1 = N("WT1", 0.0)
    wt2 = N("WT2", 0.0)
    cmf = N("CMF", 0.0)
    obv = N("OBV", 0.0)
    obv_up = (obv > obv.shift(5)).fillna(False)
    macd_hist = N("MACD_Hist", 0.0)
    st_dir = N("ST_Direction", 0)
    buy_total = N("Buy_Total", 0.0)
    sell_total = N("Sell_Total", 0.0)
    ensemble = N("Ensemble_Score", 0.0)
    base_labels = np.asarray(df.get("Trade_Judgment", pd.Series("NEUTRAL", index=idx)).astype(str).values, dtype=object)
    base_pre_labels = np.asarray(df.get("PreVeto_Judgment", pd.Series("NEUTRAL", index=idx)).astype(str).values, dtype=object)
    base_conf = N("Judgment_Confidence", 0.0).astype(float).values
    base_buy_agree = N("Buy_Agree", 0).astype(int).values
    base_sell_agree = N("Sell_Agree", 0).astype(int).values
    base_downgrade = N("Downgrade_Count", 0).astype(int).values
    base_macro_off = N("Macro_Risk_Off_Count", 0).astype(int).values
    base_macro_on = N("Macro_Risk_On_Count", 0).astype(int).values
    base_flip_guard = N("Flip_Guard_Triggered", False).astype(bool).values
    base_reasons = np.asarray(df.get("Judgment_Reason", pd.Series("", index=idx)).astype(str).values, dtype=object)
    base_details = np.asarray(df.get("Judgment_Detail", pd.Series("", index=idx)).astype(str).values, dtype=object)
    base_actions = np.asarray(df.get("Action_Label", pd.Series("", index=idx)).astype(str).values, dtype=object)
    base_contrast = np.asarray(df.get("Contrast_Notes", pd.Series("", index=idx)).astype(str).values, dtype=object)

    trend_buy = ((close > ma50).fillna(False).astype(float) * 8.0) + ((close > ma200).fillna(False).astype(float) * 10.0) + ((st_dir == 1).astype(float) * 6.0)
    trend_sell = ((close < ma50).fillna(False).astype(float) * 8.0) + ((close < ma200).fillna(False).astype(float) * 10.0) + ((st_dir == -1).astype(float) * 6.0)

    momentum_buy = ((rsi > 50).astype(float) * 6.0) + ((wt1 > wt2).astype(float) * 6.0) + ((macd_hist > macd_hist.shift(1)).fillna(False).astype(float) * 4.0)
    momentum_sell = ((rsi < 50).astype(float) * 6.0) + ((wt1 < wt2).astype(float) * 6.0) + ((macd_hist < macd_hist.shift(1)).fillna(False).astype(float) * 4.0)

    money_buy = ((cmf > 0).astype(float) * 6.0) + (obv_up.astype(float) * 5.0)
    money_sell = ((cmf < 0).astype(float) * 6.0) + ((~obv_up).astype(float) * 5.0)

    reversal_buy = (F("Bullish_Engulfing").astype(float) * 5.0) + (F("Hammer").astype(float) * 4.0) + (F("Morning_Star").astype(float) * 5.0)
    reversal_sell = (F("Bearish_Engulfing").astype(float) * 5.0) + (F("Shooting_Star").astype(float) * 4.0) + (F("Evening_Star").astype(float) * 5.0)

    location_buy = (F("Fib_618_Support").astype(float) * 4.0) + (F("Box_Support_Hold").astype(float) * 4.0) + (F("Channel_Support_Hold").astype(float) * 4.0)
    location_sell = (F("Fib_618_Resistance").astype(float) * 4.0) + (F("Box_Resistance_Reject").astype(float) * 4.0) + (F("Channel_Resistance_Reject").astype(float) * 4.0)

    signal_buy = buy_total * 0.25 + ensemble.clip(lower=0) * 0.20
    signal_sell = sell_total * 0.25 + (-ensemble.clip(upper=0)) * 0.20
    combo_buy = (F("CS_Breakout_Confirm_Buy").astype(float) * 3.0) + (F("CS_Reversal_Cluster_Buy").astype(float) * 3.0) + (F("CS_Trend_Continuation_Buy").astype(float) * 2.0)
    combo_sell = (F("CS_Breakout_Confirm_Sell").astype(float) * 3.0) + (F("CS_Reversal_Cluster_Sell").astype(float) * 3.0) + (F("CS_Trend_Continuation_Sell").astype(float) * 2.0)

    buy_score = trend_buy + momentum_buy + money_buy + reversal_buy + location_buy + signal_buy + combo_buy
    sell_score = trend_sell + momentum_sell + money_sell + reversal_sell + location_sell + signal_sell + combo_sell
    conflict_score = np.minimum(buy_score, sell_score)

    objective_labels = np.array([_label_from_scores(b, s, c) for b, s, c in zip(buy_score, sell_score, conflict_score)], dtype=object)
    objective_pre_labels = objective_labels.copy()
    objective_conf = np.clip(np.abs(buy_score - sell_score) * 2.0 + conflict_score, 5, 99)
    objective_buy_agree = np.where(buy_score >= sell_score, np.maximum(base_buy_agree, 1), 0)
    objective_sell_agree = np.where(sell_score > buy_score, np.maximum(base_sell_agree, 1), 0)
    objective_alignment = np.where(buy_score > sell_score, "BUY", np.where(sell_score > buy_score, "SELL", "MIXED"))
    objective_adjustment = np.where(objective_labels != "NEUTRAL", "ACTIVE", "NONE")

    objective_reasons = []
    objective_details = []
    objective_actions = []
    objective_contrasts = []
    final_labels = base_labels.copy()
    final_conf = base_conf.copy()
    final_buy_agree = base_buy_agree.copy()
    final_sell_agree = base_sell_agree.copy()
    final_downgrade = base_downgrade.copy()
    final_reasons = base_reasons.copy()
    final_details = base_details.copy()
    final_actions = base_actions.copy()
    final_contrast = base_contrast.copy()

    for i in range(len(df)):
        gap = float(buy_score.iloc[i] - sell_score.iloc[i])
        obj_label = str(objective_labels[i])
        side_text = "buy" if gap > 0 else ("sell" if gap < 0 else "mixed")
        reason = f"Objective layer sees {side_text} pressure."
        detail = f"buy={buy_score.iloc[i]:.1f} | sell={sell_score.iloc[i]:.1f} | gap={gap:+.1f}"
        action = objective_action_label(obj_label)
        conflict = "Conflict elevated" if conflict_score.iloc[i] >= 18 else ""
        objective_reasons.append(reason)
        objective_details.append(detail)
        objective_actions.append(action)
        objective_contrasts.append(conflict)

        base_label = str(final_labels[i])
        base_side = judgment_side(base_label)
        obj_side = judgment_side(obj_label)
        if base_label in {"NEUTRAL", "MIXED"} and obj_side != 0 and abs(gap) >= 10:
            final_labels[i] = obj_label
            final_reasons[i] = append_note(final_reasons[i], reason, " ")
            final_details[i] = append_note(final_details[i], detail)
            final_actions[i] = default_action_label(final_labels[i])
        elif base_side != 0 and obj_side == base_side and abs(gap) >= 20:
            promoted = promote_buy(base_label) if obj_side > 0 else promote_sell(base_label)
            final_labels[i] = promoted
            final_details[i] = append_note(final_details[i], f"Objective confirms {side_text} side")
            final_actions[i] = default_action_label(final_labels[i])
        elif base_side != 0 and obj_side == -base_side and abs(gap) >= 24:
            final_labels[i] = downgrade_buy(base_label, severe=False) if base_side > 0 else downgrade_sell(base_label, severe=False)
            final_downgrade[i] += 1
            final_contrast[i] = append_note(final_contrast[i], f"Objective conflict {gap:+.1f}", "; ")
            final_actions[i] = default_action_label(final_labels[i])

        final_conf[i] = max(float(final_conf[i]), float(objective_conf[i]) * 0.85)
        final_buy_agree[i] = max(int(final_buy_agree[i]), int(objective_buy_agree[i]))
        final_sell_agree[i] = max(int(final_sell_agree[i]), int(objective_sell_agree[i]))
        if not str(final_reasons[i] or "").strip():
            final_reasons[i] = reason
        if not str(final_details[i] or "").strip():
            final_details[i] = detail
        if not str(final_actions[i] or "").strip():
            final_actions[i] = default_action_label(final_labels[i])

    df["Objective_Buy_Score"] = buy_score
    df["Objective_Sell_Score"] = sell_score
    df["Objective_Conflict_Score"] = conflict_score
    df["Objective_Trend_Buy"] = trend_buy
    df["Objective_Trend_Sell"] = trend_sell
    df["Objective_Momentum_Buy"] = momentum_buy
    df["Objective_Momentum_Sell"] = momentum_sell
    df["Objective_Money_Buy"] = money_buy
    df["Objective_Money_Sell"] = money_sell
    df["Objective_Reversal_Buy"] = reversal_buy
    df["Objective_Reversal_Sell"] = reversal_sell
    df["Objective_Location_Buy"] = location_buy
    df["Objective_Location_Sell"] = location_sell
    df["Objective_Signal_Buy"] = signal_buy
    df["Objective_Signal_Sell"] = signal_sell
    df["Objective_Combo_Buy"] = combo_buy
    df["Objective_Combo_Sell"] = combo_sell
    df["Objective_Judgment"] = objective_labels
    df["Objective_PreVeto_Judgment"] = objective_pre_labels
    df["Objective_Confidence"] = objective_conf
    df["Objective_Buy_Agree"] = objective_buy_agree
    df["Objective_Sell_Agree"] = objective_sell_agree
    df["Objective_Reason"] = objective_reasons
    df["Objective_Detail"] = objective_details
    df["Objective_Action_Label"] = objective_actions
    df["Objective_Contrast_Notes"] = objective_contrasts
    df["Objective_Alignment"] = objective_alignment
    df["Objective_Adjustment"] = objective_adjustment

    df["PreVeto_Judgment"] = base_pre_labels
    df["Trade_Judgment"] = final_labels
    df["Judgment_Confidence"] = final_conf
    df["Buy_Agree"] = final_buy_agree
    df["Sell_Agree"] = final_sell_agree
    df["Downgrade_Count"] = final_downgrade
    df["Macro_Risk_Off_Count"] = base_macro_off
    df["Macro_Risk_On_Count"] = base_macro_on
    df["Flip_Guard_Triggered"] = base_flip_guard
    df["Judgment_Reason"] = final_reasons
    df["Judgment_Detail"] = final_details
    df["Action_Label"] = final_actions
    df["Contrast_Notes"] = final_contrast

    is_buy = pd.Series(final_labels, index=idx).isin(list(OBJECTIVE_BUY_LABELS))
    is_sell = pd.Series(final_labels, index=idx).isin(list(OBJECTIVE_SELL_LABELS))
    df["System_Turn_Bull"] = (is_buy & ~is_buy.shift(1).fillna(False)).values
    df["System_Turn_Bear"] = (is_sell & ~is_sell.shift(1).fillna(False)).values
    return df
