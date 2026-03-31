from typing import Iterable

import numpy as np
import pandas as pd


BUY_LABELS = ("STRONG_BUY", "BUY", "WATCH_BUY")
SELL_LABELS = ("STRONG_SELL", "SELL", "WATCH_SELL")
NEUTRAL_LABELS = ("NEUTRAL", "MIXED")
LABEL_ORDER = (
    "STRONG_BUY",
    "BUY",
    "WATCH_BUY",
    "NEUTRAL",
    "MIXED",
    "WATCH_SELL",
    "SELL",
    "STRONG_SELL",
)


def _direction_for_label(label: str) -> int:
    text = str(label or "").upper()
    if text in BUY_LABELS:
        return 1
    if text in SELL_LABELS:
        return -1
    return 0


def _safe_mean(series: pd.Series) -> float | None:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return None
    return float(values.mean())


def _safe_rate(series: pd.Series) -> float | None:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return None
    return float(values.mean())


def _bool_series(frame: pd.DataFrame, column: str) -> pd.Series:
    value = frame.get(column)
    if value is None:
        return pd.Series(False, index=frame.index, dtype=bool)
    if isinstance(value, pd.Series):
        return value.reindex(frame.index).fillna(False).astype(bool)
    return pd.Series(bool(value), index=frame.index, dtype=bool)


def _summarize_subset(
    df: pd.DataFrame,
    mask: pd.Series,
    name: str,
    horizons: Iterable[int],
    direction: int,
) -> dict:
    subset = df.loc[mask].copy()
    row = {
        "name": name,
        "samples": int(len(subset)),
        "avg_es": _safe_mean(subset.get("Ensemble_Score", pd.Series(dtype=float))),
        "avg_confidence": _safe_mean(subset.get("Judgment_Confidence", pd.Series(dtype=float))),
        "downgrade_rate": _safe_rate(subset.get("_downgraded", pd.Series(dtype=float))),
    }
    for horizon in horizons:
        col = f"_fwd_{horizon}"
        values = pd.to_numeric(subset.get(col, pd.Series(dtype=float)), errors="coerce").dropna()
        row[f"avg_{horizon}"] = float(values.mean()) if not values.empty else None
        if direction > 0:
            hits = (values > 0).astype(float)
            edge = values
        elif direction < 0:
            hits = (values < 0).astype(float)
            edge = -values
        else:
            hits = pd.Series(dtype=float)
            edge = pd.Series(dtype=float)
        row[f"hit_{horizon}"] = float(hits.mean()) if not hits.empty else None
        row[f"edge_{horizon}"] = float(edge.mean()) if not edge.empty else None
        for bench in ("spy", "qqq"):
            excess_values = pd.to_numeric(subset.get(f"_excess_{bench}_{horizon}", pd.Series(dtype=float)), errors="coerce").dropna()
            if direction > 0:
                excess_edge = excess_values
            elif direction < 0:
                excess_edge = -excess_values
            else:
                excess_edge = pd.Series(dtype=float)
            row[f"edge_excess_{bench}_{horizon}"] = float(excess_edge.mean()) if not excess_edge.empty else None
    return row


def _build_examples(df: pd.DataFrame, horizon: int = 5, topn: int = 5) -> dict:
    col = f"_fwd_{horizon}"
    if col not in df.columns:
        return {"best": [], "worst": []}
    actionable = df.loc[df["_direction"] != 0].copy()
    actionable = actionable[pd.notna(actionable[col])].copy()
    if actionable.empty:
        return {"best": [], "worst": []}

    actionable["_edge"] = actionable[col] * actionable["_direction"]
    actionable["_date"] = actionable.index.strftime("%Y-%m-%d")
    best = actionable.sort_values("_edge", ascending=False).head(topn)
    worst = actionable.sort_values("_edge", ascending=True).head(topn)

    def _rows(frame: pd.DataFrame) -> list[dict]:
        rows = []
        for _, row in frame.iterrows():
            rows.append(
                {
                    "date": row["_date"],
                    "label": str(row.get("Trade_Judgment", "")),
                    "close": float(row["Close"]) if pd.notna(row.get("Close")) else None,
                    f"ret_{horizon}": float(row[col]) if pd.notna(row.get(col)) else None,
                    f"edge_{horizon}": float(row["_edge"]) if pd.notna(row.get("_edge")) else None,
                    f"spy_excess_{horizon}": float(row.get(f"_edge_excess_spy_{horizon}")) if pd.notna(row.get(f"_edge_excess_spy_{horizon}")) else None,
                    f"qqq_excess_{horizon}": float(row.get(f"_edge_excess_qqq_{horizon}")) if pd.notna(row.get(f"_edge_excess_qqq_{horizon}")) else None,
                    "ensemble_score": float(row["Ensemble_Score"]) if pd.notna(row.get("Ensemble_Score")) else None,
                    "confidence": float(row["Judgment_Confidence"]) if pd.notna(row.get("Judgment_Confidence")) else None,
                    "downgraded": bool(row.get("_downgraded", False)),
                    "flip_guard": bool(row.get("Flip_Guard_Triggered", False)),
                    "reason": str(row.get("Judgment_Reason", "") or ""),
                }
            )
        return rows

    return {"best": _rows(best), "worst": _rows(worst)}


def build_audit_payload(
    df: pd.DataFrame,
    ticker: str = "",
    lookback_bars: int = 252,
    horizons: Iterable[int] = (3, 5, 10, 20),
) -> dict:
    horizons = tuple(sorted({int(h) for h in horizons if int(h) > 0}))
    if df is None or df.empty:
        return {"available": False, "reason": "\uB370\uC774\uD130\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4."}
    if "Close" not in df.columns or "Trade_Judgment" not in df.columns:
        return {"available": False, "reason": "\uAC10\uC0AC\uC5D0 \uD544\uC694\uD55C \uD310\uB2E8 \uCEEC\uB7FC\uC774 \uC5C6\uC2B5\uB2C8\uB2E4."}

    max_horizon = max(horizons, default=5)
    work = df.copy().dropna(subset=["Close"]).tail(max(lookback_bars, max_horizon + 40)).copy()
    if len(work) <= max_horizon + 10:
        return {"available": False, "reason": "\uAC10\uC0AC\uC5D0 \uD544\uC694\uD55C \uD45C\uBCF8\uC774 \uBD80\uC871\uD569\uB2C8\uB2E4."}

    work["Trade_Judgment"] = work["Trade_Judgment"].astype(str).fillna("NEUTRAL")
    work["PreVeto_Judgment"] = work.get("PreVeto_Judgment", work["Trade_Judgment"]).astype(str).fillna("NEUTRAL")
    work["Judgment_Confidence"] = pd.to_numeric(work.get("Judgment_Confidence"), errors="coerce")
    work["Ensemble_Score"] = pd.to_numeric(work.get("Ensemble_Score"), errors="coerce")
    work["Flip_Guard_Triggered"] = _bool_series(work, "Flip_Guard_Triggered")
    work["_direction"] = work["Trade_Judgment"].map(_direction_for_label).fillna(0).astype(int)
    work["_downgraded"] = work["PreVeto_Judgment"] != work["Trade_Judgment"]

    for horizon in horizons:
        work[f"_fwd_{horizon}"] = work["Close"].shift(-horizon) / work["Close"] - 1.0
        spy_raw = work.get("SPY_Close")
        qqq_raw = work.get("QQQ_Close")
        spy_close = pd.to_numeric(spy_raw, errors="coerce").where(lambda s: s > 0) if isinstance(spy_raw, pd.Series) else None
        qqq_close = pd.to_numeric(qqq_raw, errors="coerce").where(lambda s: s > 0) if isinstance(qqq_raw, pd.Series) else None
        if spy_close is not None and spy_close.notna().any():
            work[f"_spy_fwd_{horizon}"] = spy_close.shift(-horizon) / spy_close - 1.0
            work[f"_excess_spy_{horizon}"] = work[f"_fwd_{horizon}"] - work[f"_spy_fwd_{horizon}"]
            work[f"_edge_excess_spy_{horizon}"] = work[f"_excess_spy_{horizon}"] * work["_direction"]
        if qqq_close is not None and qqq_close.notna().any():
            work[f"_qqq_fwd_{horizon}"] = qqq_close.shift(-horizon) / qqq_close - 1.0
            work[f"_excess_qqq_{horizon}"] = work[f"_fwd_{horizon}"] - work[f"_qqq_fwd_{horizon}"]
            work[f"_edge_excess_qqq_{horizon}"] = work[f"_excess_qqq_{horizon}"] * work["_direction"]

    eval_rows = work.iloc[:-max_horizon].copy() if len(work) > max_horizon else work.copy()
    if eval_rows.empty:
        return {"available": False, "reason": "\uBBF8\uB798 \uC218\uC775\uB960\uC744 \uACC4\uC0B0\uD560 \uD45C\uBCF8\uC774 \uBD80\uC871\uD569\uB2C8\uB2E4."}

    distribution = []
    total_eval = max(len(eval_rows), 1)
    for label in LABEL_ORDER:
        count = int((eval_rows["Trade_Judgment"] == label).sum())
        if count:
            distribution.append({"label": label, "count": count, "share": count / total_eval})

    label_rows = []
    for label in LABEL_ORDER:
        mask = eval_rows["Trade_Judgment"] == label
        if mask.any():
            label_rows.append(_summarize_subset(eval_rows, mask, label, horizons, _direction_for_label(label)))

    group_specs = [
        ("BUY \uACC4\uC5F4", eval_rows["Trade_Judgment"].isin(BUY_LABELS), 1),
        ("SELL \uACC4\uC5F4", eval_rows["Trade_Judgment"].isin(SELL_LABELS), -1),
        ("\uC911\uB9BD/\uD63C\uC870", eval_rows["Trade_Judgment"].isin(NEUTRAL_LABELS), 0),
    ]
    group_rows = [
        _summarize_subset(eval_rows, mask, name, horizons, direction)
        for name, mask, direction in group_specs
        if mask.any()
    ]

    ref_horizon = 5 if 5 in horizons else horizons[0]
    buy_downgrade_mask = eval_rows["_downgraded"] & eval_rows["PreVeto_Judgment"].isin(BUY_LABELS)
    sell_downgrade_mask = eval_rows["_downgraded"] & eval_rows["PreVeto_Judgment"].isin(SELL_LABELS)
    buy_downgrade_help = _safe_rate(
        (pd.to_numeric(eval_rows.loc[buy_downgrade_mask, f"_fwd_{ref_horizon}"], errors="coerce") <= 0).astype(float)
    )
    sell_downgrade_help = _safe_rate(
        (pd.to_numeric(eval_rows.loc[sell_downgrade_mask, f"_fwd_{ref_horizon}"], errors="coerce") >= 0).astype(float)
    )

    flip_pairs = (
        eval_rows["Trade_Judgment"].shift(1).map(_direction_for_label).fillna(0).astype(int) * eval_rows["_direction"]
    ) == -1
    flip_count = int(flip_pairs.sum())

    turn_specs = [
        ("\uC885\uBAA9 \uCD94\uC138 \uC804\uD658 \uB9E4\uC218", _bool_series(eval_rows, "Trend_Inflection_Bull"), 1),
        ("\uC885\uBAA9 \uCD94\uC138 \uC804\uD658 \uB9E4\uB3C4", _bool_series(eval_rows, "Trend_Inflection_Bear"), -1),
        ("\uC2DC\uC7A5 \uC804\uD658 \uCD08\uAE30 \uAC15\uC138", _bool_series(eval_rows, "Market_Turn_Bull"), 1),
        ("\uC2DC\uC7A5 \uC804\uD658 \uCD08\uAE30 \uC57D\uC138", _bool_series(eval_rows, "Market_Turn_Bear"), -1),
    ]
    turn_rows = [
        _summarize_subset(eval_rows, mask, name, horizons, direction)
        for name, mask, direction in turn_specs
        if mask.any()
    ]

    buy_group = next((row for row in group_rows if row["name"] == "BUY \uACC4\uC5F4"), None)
    sell_group = next((row for row in group_rows if row["name"] == "SELL \uACC4\uC5F4"), None)
    summary = {
        "samples": int(len(eval_rows)),
        "lookback_bars": int(len(work)),
        "as_of": work.index[-1].strftime("%Y-%m-%d"),
        "buy_share": float(eval_rows["Trade_Judgment"].isin(BUY_LABELS).mean()),
        "sell_share": float(eval_rows["Trade_Judgment"].isin(SELL_LABELS).mean()),
        "neutral_share": float(eval_rows["Trade_Judgment"].isin(NEUTRAL_LABELS).mean()),
        "downgraded_share": float(eval_rows["_downgraded"].mean()),
        "flip_guard_share": float(eval_rows["Flip_Guard_Triggered"].mean()),
        "avg_confidence": _safe_mean(eval_rows["Judgment_Confidence"]),
        "buy_edge_ref": buy_group.get(f"edge_{ref_horizon}") if buy_group else None,
        "sell_edge_ref": sell_group.get(f"edge_{ref_horizon}") if sell_group else None,
        "buy_edge_excess_spy_ref": buy_group.get(f"edge_excess_spy_{ref_horizon}") if buy_group else None,
        "sell_edge_excess_spy_ref": sell_group.get(f"edge_excess_spy_{ref_horizon}") if sell_group else None,
        "buy_edge_excess_qqq_ref": buy_group.get(f"edge_excess_qqq_{ref_horizon}") if buy_group else None,
        "sell_edge_excess_qqq_ref": sell_group.get(f"edge_excess_qqq_{ref_horizon}") if sell_group else None,
        "buy_hit_ref": buy_group.get(f"hit_{ref_horizon}") if buy_group else None,
        "sell_hit_ref": sell_group.get(f"hit_{ref_horizon}") if sell_group else None,
    }

    veto_stats = {
        "downgraded_count": int(eval_rows["_downgraded"].sum()),
        "downgraded_share": float(eval_rows["_downgraded"].mean()),
        "buy_downgrade_count": int(buy_downgrade_mask.sum()),
        "sell_downgrade_count": int(sell_downgrade_mask.sum()),
        "buy_downgrade_help_rate": buy_downgrade_help,
        "sell_downgrade_help_rate": sell_downgrade_help,
        "flip_guard_count": int(eval_rows["Flip_Guard_Triggered"].sum()),
        "flip_guard_share": float(eval_rows["Flip_Guard_Triggered"].mean()),
        "flip_count": flip_count,
        "flip_rate": float(flip_pairs.mean()) if len(eval_rows) else None,
    }

    return {
        "available": True,
        "ticker": str(ticker or "").upper(),
        "horizons": list(horizons),
        "reference_horizon": ref_horizon,
        "summary": summary,
        "distribution": distribution,
        "label_rows": label_rows,
        "group_rows": group_rows,
        "turn_rows": turn_rows,
        "veto_stats": veto_stats,
        "examples": _build_examples(eval_rows, horizon=ref_horizon, topn=5),
        "method_note": (
            f"\uCD5C\uADFC {len(work)}\uBD09 \uB370\uC774\uD130\uB97C \uAE30\uC900\uC73C\uB85C "
            f"{', '.join(str(h) for h in horizons)}\uBD09 \uD6C4 \uC218\uC775\uB960\uACFC SPY/QQQ \uB300\uBE44 \uBC29\uD5A5 \uCD08\uACFC\uC218\uC775\uC744 \uACC4\uC0B0\uD588\uC2B5\uB2C8\uB2E4."
        ),
    }
