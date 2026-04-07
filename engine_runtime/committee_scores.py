from __future__ import annotations

from engine_committee import compute_committee_ensemble


def compute_committee_scores(df, vol_ratio, hma_rising_values):
    return compute_committee_ensemble(df, vol_ratio, hma_rising_values)
