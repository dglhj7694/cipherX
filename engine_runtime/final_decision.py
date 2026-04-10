from __future__ import annotations

import numpy as np
import pandas as pd

from engine_committee import (
    OBJECTIVE_BUY_LABELS,
    OBJECTIVE_SELL_LABELS,
    append_note,
    default_action_label,
    downgrade_buy,
    downgrade_sell,
    judgment_side,
)


def _series(df, name, default, index):
    return df.get(name, pd.Series(default, index=index)).fillna(default)


def compute_final_decision(df):
    if df is None or df.empty:
        return df

    idx = df.index
    committee_label = np.asarray(_series(df, "Committee_Judgment", "NEUTRAL", idx).astype(str).values, dtype=object)
    committee_preveto = np.asarray(_series(df, "Committee_PreVeto_Judgment", "NEUTRAL", idx).astype(str).values, dtype=object)
    committee_conf = _series(df, "Committee_Confidence", 0.0, idx).astype(float).values
    committee_buy_agree = _series(df, "Committee_Buy_Agree", 0, idx).astype(int).values
    committee_sell_agree = _series(df, "Committee_Sell_Agree", 0, idx).astype(int).values
    committee_reason = np.asarray(_series(df, "Committee_Judgment_Reason", "", idx).astype(str).values, dtype=object)
    committee_detail = np.asarray(_series(df, "Committee_Judgment_Detail", "", idx).astype(str).values, dtype=object)
    committee_action = np.asarray(_series(df, "Committee_Action_Label", "", idx).astype(str).values, dtype=object)
    committee_contrast = np.asarray(_series(df, "Committee_Contrast_Notes", "", idx).astype(str).values, dtype=object)
    committee_downgrade = _series(df, "Committee_Downgrade_Count", 0, idx).astype(int).values
    macro_risk_off = _series(df, "Committee_Macro_Risk_Off_Count", 0, idx).astype(int).values
    macro_risk_on = _series(df, "Committee_Macro_Risk_On_Count", 0, idx).astype(int).values
    flip_guard = _series(df, "Committee_Flip_Guard_Triggered", False, idx).astype(bool).values

    objective_label = np.asarray(_series(df, "Objective_Judgment", "NEUTRAL", idx).astype(str).values, dtype=object)
    objective_reason = np.asarray(_series(df, "Objective_Reason", "", idx).astype(str).values, dtype=object)
    objective_detail = np.asarray(_series(df, "Objective_Detail", "", idx).astype(str).values, dtype=object)
    objective_buy_score = _series(df, "Objective_Buy_Score", 0.0, idx).astype(float).values
    objective_sell_score = _series(df, "Objective_Sell_Score", 0.0, idx).astype(float).values
    leading_buy_score = _series(df, "Leading_Buy_Score", 0.0, idx).astype(float).values
    leading_sell_score = _series(df, "Leading_Sell_Score", 0.0, idx).astype(float).values
    leading_spread = _series(df, "Leading_Score_Spread", 0.0, idx).astype(float).values
    leading_noise_block = _series(df, "Leading_Noise_Block", False, idx).astype(bool).values
    leading_buy_block = _series(df, "Leading_Buy_Noise_Block", False, idx).astype(bool).values
    leading_sell_block = _series(df, "Leading_Sell_Noise_Block", False, idx).astype(bool).values
    leading_reason = np.asarray(_series(df, "Leading_Core_Reasons", "", idx).astype(str).values, dtype=object)
    leading_noise_flags = np.asarray(_series(df, "Leading_Noise_Flags", "", idx).astype(str).values, dtype=object)

    final_label = committee_label.copy()
    final_conf = committee_conf.copy()
    final_buy_agree = committee_buy_agree.copy()
    final_sell_agree = committee_sell_agree.copy()
    final_reason = committee_reason.copy()
    final_detail = committee_detail.copy()
    final_action = committee_action.copy()
    final_contrast = committee_contrast.copy()
    final_downgrade = committee_downgrade.copy()
    final_score = _series(df, "Ensemble_Score", 0.0, idx).astype(float).values.copy()

    for i in range(len(df)):
        gap = float(objective_buy_score[i] - objective_sell_score[i])
        base_label = str(final_label[i])
        obj_label = str(objective_label[i])
        base_side = judgment_side(base_label)
        obj_side = judgment_side(obj_label)
        lead_reason_text = str(leading_reason[i] or "").strip()
        lead_noise_text = str(leading_noise_flags[i] or "").strip()

        if lead_reason_text:
            final_detail[i] = append_note(final_detail[i], f"Leading {lead_reason_text}")
        if lead_noise_text:
            final_contrast[i] = append_note(final_contrast[i], f"Leading noise {lead_noise_text}", "; ")

        if base_side > 0 and leading_buy_block[i]:
            severe = bool((leading_sell_score[i] >= leading_buy_score[i]) or (leading_spread[i] <= 0) or (leading_buy_score[i] < 42.0))
            next_label = downgrade_buy(base_label, severe=severe)
            if next_label != final_label[i]:
                final_label[i] = next_label
                final_downgrade[i] += 1
        elif base_side < 0 and leading_sell_block[i]:
            severe = bool((leading_buy_score[i] >= leading_sell_score[i]) or (leading_spread[i] >= 0) or (leading_sell_score[i] < 42.0))
            next_label = downgrade_sell(base_label, severe=severe)
            if next_label != final_label[i]:
                final_label[i] = next_label
                final_downgrade[i] += 1

        current_label = str(final_label[i])
        current_side = judgment_side(current_label)

        if current_side != 0 and obj_side == current_side and abs(gap) >= 20:
            final_detail[i] = append_note(final_detail[i], f"Objective confirms {'buy' if obj_side > 0 else 'sell'} side")
        elif current_side != 0 and obj_side == -current_side and abs(gap) >= 24:
            next_label = downgrade_buy(current_label, severe=False) if current_side > 0 else downgrade_sell(current_label, severe=False)
            if next_label != final_label[i]:
                final_label[i] = next_label
                final_downgrade[i] += 1
            final_contrast[i] = append_note(final_contrast[i], f"Objective conflict {gap:+.1f}", "; ")

        if leading_noise_block[i] and judgment_side(str(final_label[i])) == 0:
            final_contrast[i] = append_note(final_contrast[i], "Leading noise filter neutralized direction", "; ")

        if not str(final_reason[i] or "").strip():
            final_reason[i] = str(objective_reason[i])
        if not str(final_detail[i] or "").strip():
            final_detail[i] = str(objective_detail[i])
        if not str(final_action[i] or "").strip():
            final_action[i] = default_action_label(str(final_label[i]))
        else:
            final_action[i] = default_action_label(str(final_label[i]))

    df["PreVeto_Judgment"] = committee_preveto
    df["Trade_Judgment"] = final_label
    df["Judgment_Confidence"] = final_conf
    df["Buy_Agree"] = final_buy_agree
    df["Sell_Agree"] = final_sell_agree
    df["Downgrade_Count"] = final_downgrade
    df["Macro_Risk_Off_Count"] = macro_risk_off
    df["Macro_Risk_On_Count"] = macro_risk_on
    df["Flip_Guard_Triggered"] = flip_guard
    df["Judgment_Reason"] = final_reason
    df["Judgment_Detail"] = final_detail
    df["Action_Label"] = final_action
    df["Contrast_Notes"] = final_contrast
    df["Final_Decision_Score"] = final_score

    is_buy = pd.Series(final_label, index=idx).isin(list(OBJECTIVE_BUY_LABELS))
    is_sell = pd.Series(final_label, index=idx).isin(list(OBJECTIVE_SELL_LABELS))
    df["System_Turn_Bull"] = (is_buy & ~is_buy.shift(1, fill_value=False)).values
    df["System_Turn_Bear"] = (is_sell & ~is_sell.shift(1, fill_value=False)).values
    return df
