from __future__ import annotations

import numpy as np
import pandas as pd


def apply_layer_totals(df, layer_names, combo_registry):
    buy_raw = sum(df[f"BL_{name}"].clip(lower=0) for name in layer_names)
    sell_raw = sum(df[f"SL_{name}"].clip(lower=0) for name in layer_names)
    df["Buy_Active_Layers"] = sum((df[f"BL_{name}"] > 0).astype(int) for name in layer_names)
    df["Sell_Active_Layers"] = sum((df[f"SL_{name}"] > 0).astype(int) for name in layer_names)

    conflict_layers = sum(((df[f"BL_{name}"] > 0) & (df[f"SL_{name}"] > 0)).astype(int) for name in layer_names)
    buy_core = (df["BL_Trend"] + df["BL_Momentum"] + df["BL_Leading"]).clip(lower=0)
    sell_core = (df["SL_Trend"] + df["SL_Momentum"] + df["SL_Leading"]).clip(lower=0)
    buy_quality = (1.0 + ((buy_core - sell_core) / 36.0).clip(-0.20, 0.35)).astype(float)
    sell_quality = (1.0 + ((sell_core - buy_core) / 36.0).clip(-0.20, 0.35)).astype(float)
    conflict_penalty = (conflict_layers * 0.7).clip(0, 6).astype(float)

    idx = df.index
    t1_buy_cols = [cn for cn, cfg in combo_registry.items() if cfg.get("dir") == "buy" and cfg.get("tier") == 1 and cn in df.columns]
    t1_sell_cols = [cn for cn, cfg in combo_registry.items() if cfg.get("dir") == "sell" and cfg.get("tier") == 1 and cn in df.columns]
    t1_buy_boost = sum(df[col].fillna(False).astype(float) for col in t1_buy_cols) if t1_buy_cols else pd.Series(0.0, index=idx)
    t1_sell_boost = sum(df[col].fillna(False).astype(float) for col in t1_sell_cols) if t1_sell_cols else pd.Series(0.0, index=idx)

    df["Signal_Conflict_Layers"] = conflict_layers
    df["Buy_Quality_Factor"] = buy_quality
    df["Sell_Quality_Factor"] = sell_quality
    df["Buy_Total"] = ((buy_raw * buy_quality) + (t1_buy_boost * 0.8) - conflict_penalty).clip(lower=0)
    df["Sell_Total"] = ((sell_raw * sell_quality) + (t1_sell_boost * 0.8) - conflict_penalty).clip(lower=0)

    ls_ = df["BL_Leading"] - df["SL_Leading"]
    lgs = df["BL_Lagging"] - df["SL_Lagging"]
    df["Leading_Verdict"] = pd.Series(
        np.select(
            [ls_ > 3, ls_ > 1, ls_ < -3, ls_ < -1],
            ["강한 상승 가속", "상승 압박", "강한 하락 가속", "하락 압박"],
            default="중립",
        ),
        index=idx,
    )
    df["Lagging_Verdict"] = pd.Series(
        np.select(
            [lgs > 3, lgs > 1, lgs < -3, lgs < -1],
            ["강한 상승 추세", "상승 추세", "강한 하락 추세", "하락 추세"],
            default="비추세/횡보",
        ),
        index=idx,
    )
    return df
