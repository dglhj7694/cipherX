from __future__ import annotations

from engine_layers import compute_10layer_scores


def compute_layer_scores(df, vol_ratio, hma_rising_values, registry):
    return compute_10layer_scores(df, vol_ratio, hma_rising_values, registry)
