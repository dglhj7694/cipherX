from __future__ import annotations

from engine_objective import compute_objective_judgment


def compute_objective_scores(df, vol_ratio):
    return compute_objective_judgment(df, vol_ratio)
