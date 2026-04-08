from __future__ import annotations

from config import DEFAULT_BIAS_MODE
from engine_committee import compute_committee_ensemble


def compute_committee_scores(df, vol_ratio, hma_rising_values, bias_mode=DEFAULT_BIAS_MODE):
    return compute_committee_ensemble(df, vol_ratio, hma_rising_values, bias_mode=bias_mode)
