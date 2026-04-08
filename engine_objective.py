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
    base_labels = np.asarray(df.get("Committee_Judgment", pd.Series("NEUTRAL", index=idx)).astype(str).values, dtype=object)

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

    signal_buy = pd.Series(0.0, index=idx)
    signal_sell = pd.Series(0.0, index=idx)
    combo_buy = (F("CS_Breakout_Confirm_Buy").astype(float) * 3.0) + (F("CS_Reversal_Cluster_Buy").astype(float) * 3.0) + (F("CS_Trend_Continuation_Buy").astype(float) * 2.0)
    combo_sell = (F("CS_Breakout_Confirm_Sell").astype(float) * 3.0) + (F("CS_Reversal_Cluster_Sell").astype(float) * 3.0) + (F("CS_Trend_Continuation_Sell").astype(float) * 2.0)

    buy_score = trend_buy + momentum_buy + money_buy + reversal_buy + location_buy + signal_buy + combo_buy
    sell_score = trend_sell + momentum_sell + money_sell + reversal_sell + location_sell + signal_sell + combo_sell
    conflict_score = np.minimum(buy_score, sell_score)

    objective_labels = np.array([_label_from_scores(b, s, c) for b, s, c in zip(buy_score, sell_score, conflict_score)], dtype=object)
    objective_pre_labels = objective_labels.copy()
    objective_conf = np.clip(np.abs(buy_score - sell_score) * 2.0 + conflict_score, 5, 99)
    objective_buy_agree = np.where(buy_score >= sell_score, 1, 0)
    objective_sell_agree = np.where(sell_score > buy_score, 1, 0)

    objective_reasons = []
    objective_details = []
    objective_actions = []
    objective_contrasts = []
    objective_alignment = []
    objective_adjustment = []

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
        committee_label = str(base_labels[i])
        committee_side = judgment_side(committee_label)
        objective_side = judgment_side(obj_label)
        if committee_side != 0 and objective_side == committee_side and abs(gap) >= 20:
            objective_alignment.append("ALIGNED")
            objective_adjustment.append("CONFIRM")
        elif committee_side != 0 and objective_side == -committee_side and abs(gap) >= 24:
            objective_alignment.append("CONFLICT")
            objective_adjustment.append("DOWNGRADE")
        elif objective_side == 0:
            objective_alignment.append("MIXED")
            objective_adjustment.append("NONE")
        else:
            objective_alignment.append("MIXED")
            objective_adjustment.append("NONE")

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
    return df
