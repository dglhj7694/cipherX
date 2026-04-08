from typing import Iterable

import numpy as np
import pandas as pd

from config import CTX_KOR, DEFAULT_BIAS_MODE, resolve_bias_mode


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
TRANSACTION_COST_BPS = 10
TRANSACTION_COST_RATE = TRANSACTION_COST_BPS / 10000.0
WALKFORWARD_WINDOW = 63
WALKFORWARD_STEP = 21


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


def _context_name(value) -> str:
    try:
        key = int(value)
    except Exception:
        return str(value or "-")
    return CTX_KOR.get(key, str(key))


def _series_text(frame: pd.DataFrame, column: str, default: str = "") -> pd.Series:
    value = frame.get(column)
    if value is None:
        return pd.Series(default, index=frame.index, dtype=object)
    if isinstance(value, pd.Series):
        return value.reindex(frame.index).fillna(default).astype(str)
    return pd.Series(str(value or default), index=frame.index, dtype=object)


def _last_bias_mode(df: pd.DataFrame, bias_mode: str | None = None) -> str:
    explicit = str(bias_mode or "").strip()
    if explicit:
        return resolve_bias_mode(explicit)
    value = df.get("Bias_Mode")
    if isinstance(value, pd.Series) and not value.dropna().empty:
        return resolve_bias_mode(str(value.dropna().iloc[-1]))
    return DEFAULT_BIAS_MODE


def _simulate_leg(position: pd.Series, leg_returns: pd.Series) -> dict:
    pos = pd.to_numeric(position, errors="coerce").fillna(0.0).astype(float)
    returns = pd.to_numeric(leg_returns, errors="coerce").fillna(0.0).astype(float)
    turnover = pos.diff().abs().fillna(pos.abs())
    cost = turnover * TRANSACTION_COST_RATE
    net = (pos * returns) - cost
    curve = (1.0 + net).cumprod()
    running_peak = curve.cummax()
    drawdown = (curve / running_peak) - 1.0
    return {
        "return": float(curve.iloc[-1] - 1.0) if not curve.empty else 0.0,
        "max_drawdown": float(drawdown.min()) if not drawdown.empty else 0.0,
        "turnover": float(turnover.sum()),
        "cost_drag": float(cost.sum()),
        "active_share": float((pos != 0).mean()) if len(pos) else 0.0,
        "avg_daily": float(net.mean()) if len(net) else 0.0,
    }


def _build_simulation_summary(df: pd.DataFrame) -> dict:
    if df is None or df.empty:
        return {}
    daily_returns = pd.to_numeric(df.get("Close"), errors="coerce").pct_change().fillna(0.0)
    lagged_direction = pd.to_numeric(df.get("_direction"), errors="coerce").fillna(0.0).shift(1).fillna(0.0)
    long_position = (lagged_direction > 0).astype(float)
    short_position = (lagged_direction < 0).astype(float)

    overall = _simulate_leg(lagged_direction, daily_returns)
    long_only = _simulate_leg(long_position, daily_returns)
    short_only = _simulate_leg(short_position, -daily_returns)
    return {
        "cost_bps": TRANSACTION_COST_BPS,
        "samples": int(len(df)),
        "overall_return": overall["return"],
        "overall_max_drawdown": overall["max_drawdown"],
        "overall_turnover": overall["turnover"],
        "overall_cost_drag": overall["cost_drag"],
        "overall_active_share": overall["active_share"],
        "long_return": long_only["return"],
        "long_max_drawdown": long_only["max_drawdown"],
        "long_turnover": long_only["turnover"],
        "long_cost_drag": long_only["cost_drag"],
        "long_active_share": long_only["active_share"],
        "short_return": short_only["return"],
        "short_max_drawdown": short_only["max_drawdown"],
        "short_turnover": short_only["turnover"],
        "short_cost_drag": short_only["cost_drag"],
        "short_active_share": short_only["active_share"],
    }


def _regime_summary_row(df: pd.DataFrame, name: str, ref_horizon: int) -> dict:
    buy_mask = df["Trade_Judgment"].isin(BUY_LABELS)
    sell_mask = df["Trade_Judgment"].isin(SELL_LABELS)
    neutral_mask = df["Trade_Judgment"].isin(NEUTRAL_LABELS)
    buy_values = pd.to_numeric(df.loc[buy_mask, f"_fwd_{ref_horizon}"], errors="coerce").dropna()
    sell_values = pd.to_numeric(df.loc[sell_mask, f"_fwd_{ref_horizon}"], errors="coerce").dropna()
    sim = _build_simulation_summary(df)
    return {
        "name": name,
        "samples": int(len(df)),
        "buy_samples": int(buy_mask.sum()),
        "sell_samples": int(sell_mask.sum()),
        "neutral_samples": int(neutral_mask.sum()),
        "buy_share": float(buy_mask.mean()) if len(df) else 0.0,
        "sell_share": float(sell_mask.mean()) if len(df) else 0.0,
        "avg_es": _safe_mean(df.get("Ensemble_Score", pd.Series(dtype=float))),
        "avg_confidence": _safe_mean(df.get("Judgment_Confidence", pd.Series(dtype=float))),
        "buy_hit_ref": float((buy_values > 0).mean()) if not buy_values.empty else None,
        "sell_hit_ref": float((sell_values < 0).mean()) if not sell_values.empty else None,
        "buy_edge_ref": float(buy_values.mean()) if not buy_values.empty else None,
        "sell_edge_ref": float((-sell_values).mean()) if not sell_values.empty else None,
        "net_return": sim.get("overall_return"),
        "max_drawdown": sim.get("overall_max_drawdown"),
        "turnover": sim.get("overall_turnover"),
    }


def _build_walkforward_rows(df: pd.DataFrame, ref_horizon: int) -> list[dict]:
    if len(df) < WALKFORWARD_WINDOW:
        return []
    rows = []
    for start in range(0, len(df) - WALKFORWARD_WINDOW + 1, WALKFORWARD_STEP):
        window = df.iloc[start : start + WALKFORWARD_WINDOW].copy()
        if window.empty:
            continue
        sim = _build_simulation_summary(window)
        buy_mask = window["Trade_Judgment"].isin(BUY_LABELS)
        sell_mask = window["Trade_Judgment"].isin(SELL_LABELS)
        buy_values = pd.to_numeric(window.loc[buy_mask, f"_fwd_{ref_horizon}"], errors="coerce").dropna()
        sell_values = pd.to_numeric(window.loc[sell_mask, f"_fwd_{ref_horizon}"], errors="coerce").dropna()
        rows.append(
            {
                "name": f"{window.index[0].strftime('%Y-%m-%d')} ~ {window.index[-1].strftime('%Y-%m-%d')}",
                "samples": int(len(window)),
                "buy_share": float(buy_mask.mean()) if len(window) else 0.0,
                "sell_share": float(sell_mask.mean()) if len(window) else 0.0,
                "avg_confidence": _safe_mean(window.get("Judgment_Confidence", pd.Series(dtype=float))),
                "buy_edge_ref": float(buy_values.mean()) if not buy_values.empty else None,
                "sell_edge_ref": float((-sell_values).mean()) if not sell_values.empty else None,
                "net_return": sim.get("overall_return"),
                "max_drawdown": sim.get("overall_max_drawdown"),
                "turnover": sim.get("overall_turnover"),
            }
        )
    return rows


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
        row[f"edge_net_{horizon}"] = float(edge.mean() - TRANSACTION_COST_RATE) if direction != 0 and not edge.empty else None
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
    bias_mode: str | None = None,
) -> dict:
    horizons = tuple(sorted({int(h) for h in horizons if int(h) > 0}))
    if df is None or df.empty:
        return {"available": False, "reason": "\uB370\uC774\uD130\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4."}
    if "Close" not in df.columns or "Trade_Judgment" not in df.columns:
        return {"available": False, "reason": "\uAC10\uC0AC\uC5D0 \uD544\uC694\uD55C \uD310\uB2E8 \uCEEC\uB7FC\uC774 \uC5C6\uC2B5\uB2C8\uB2E4."}

    max_horizon = max(horizons, default=5)
    work = df.copy().dropna(subset=["Close"]).tail(max(lookback_bars, max_horizon + 40)).copy()
    bias_mode = _last_bias_mode(work, bias_mode=bias_mode)
    if len(work) <= max_horizon + 10:
        return {"available": False, "reason": "\uAC10\uC0AC\uC5D0 \uD544\uC694\uD55C \uD45C\uBCF8\uC774 \uBD80\uC871\uD569\uB2C8\uB2E4."}

    work["Trade_Judgment"] = work["Trade_Judgment"].astype(str).fillna("NEUTRAL")
    work["PreVeto_Judgment"] = work.get("PreVeto_Judgment", work["Trade_Judgment"]).astype(str).fillna("NEUTRAL")
    work["Committee_Judgment"] = _series_text(work, "Committee_Judgment", default="NEUTRAL")
    work["Objective_Adjustment"] = _series_text(work, "Objective_Adjustment", default="NONE")
    work["Judgment_Confidence"] = pd.to_numeric(work.get("Judgment_Confidence"), errors="coerce")
    work["Ensemble_Score"] = pd.to_numeric(work.get("Ensemble_Score"), errors="coerce")
    work["Flip_Guard_Triggered"] = _bool_series(work, "Flip_Guard_Triggered")
    work["_direction"] = work["Trade_Judgment"].map(_direction_for_label).fillna(0).astype(int)
    work["_committee_direction"] = work["Committee_Judgment"].map(_direction_for_label).fillna(0).astype(int)
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
    objective_conflict_mask = eval_rows["Objective_Adjustment"].eq("DOWNGRADE") & (eval_rows["_committee_direction"] != 0)
    buy_downgrade_help = _safe_rate(
        (pd.to_numeric(eval_rows.loc[buy_downgrade_mask, f"_fwd_{ref_horizon}"], errors="coerce") <= 0).astype(float)
    )
    sell_downgrade_help = _safe_rate(
        (pd.to_numeric(eval_rows.loc[sell_downgrade_mask, f"_fwd_{ref_horizon}"], errors="coerce") >= 0).astype(float)
    )
    objective_conflict_edge = pd.to_numeric(eval_rows.loc[objective_conflict_mask, f"_fwd_{ref_horizon}"], errors="coerce") * pd.to_numeric(
        eval_rows.loc[objective_conflict_mask, "_committee_direction"], errors="coerce"
    )
    objective_conflict_help = _safe_rate((objective_conflict_edge <= 0).astype(float))
    objective_conflict_hurt = _safe_rate((objective_conflict_edge > 0).astype(float))

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
    regime_rows = []
    context_series = pd.to_numeric(eval_rows.get("Market_Context"), errors="coerce").fillna(0).astype(int)
    for ctx_code in sorted(context_series.unique()):
        regime_mask = context_series == ctx_code
        subset = eval_rows.loc[regime_mask].copy()
        if subset.empty:
            continue
        regime_rows.append(_regime_summary_row(subset, _context_name(ctx_code), ref_horizon))
    walkforward_rows = _build_walkforward_rows(eval_rows, ref_horizon)
    simulation_summary = _build_simulation_summary(work)

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
        "sim_return": simulation_summary.get("overall_return"),
        "sim_max_drawdown": simulation_summary.get("overall_max_drawdown"),
        "sim_turnover": simulation_summary.get("overall_turnover"),
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
        "objective_conflict_count": int(objective_conflict_mask.sum()),
        "objective_conflict_help_rate": objective_conflict_help,
        "objective_conflict_hurt_rate": objective_conflict_hurt,
    }

    return {
        "available": True,
        "ticker": str(ticker or "").upper(),
        "bias_mode": bias_mode,
        "horizons": list(horizons),
        "reference_horizon": ref_horizon,
        "summary": summary,
        "distribution": distribution,
        "label_rows": label_rows,
        "group_rows": group_rows,
        "regime_rows": regime_rows,
        "turn_rows": turn_rows,
        "walkforward_rows": walkforward_rows,
        "veto_stats": veto_stats,
        "simulation_summary": simulation_summary,
        "examples": _build_examples(eval_rows, horizon=ref_horizon, topn=5),
        "method_note": (
            f"\uCD5C\uADFC {len(work)}\uBD09 \uB370\uC774\uD130\uB97C \uAE30\uC900\uC73C\uB85C "
            f"{', '.join(str(h) for h in horizons)}\uBD09 \uD6C4 \uC218\uC775\uB960\uACFC SPY/QQQ \uB300\uBE44 \uBC29\uD5A5 \uCD08\uACFC\uC218\uC775\uC744 \uACC4\uC0B0\uD588\uACE0, "
            f"\uB864\uB9C1 \uC2DC\uBBAC\uB808\uC774\uC158\uC5D0\uB294 \uD3EC\uC9C0\uC158 \uBCC0\uACBD\uB2F9 {TRANSACTION_COST_BPS}bp \uBE44\uC6A9\uC744 \uBC18\uC601\uD588\uC2B5\uB2C8\uB2E4."
        ),
    }
