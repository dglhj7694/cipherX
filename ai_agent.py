import json
import re

from branding import BRAND_NAME
from config import COMBINED_SCAN_REGISTRY, SIGNAL_REGISTRY


_AI_LABELS = {
    "STRONG_BUY",
    "BUY",
    "WATCH_BUY",
    "NEUTRAL",
    "WATCH_SELL",
    "SELL",
    "STRONG_SELL",
}
_AI_DISAGREEMENT_TYPES = {"NONE", "TIMING", "RISK", "TREND", "MIXED"}


def _clamp_int(value, default=0, lo=0, hi=100):
    try:
        return max(lo, min(hi, int(round(float(value)))))
    except (TypeError, ValueError):
        return default


def _normalize_text_list(value, limit=4):
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, (list, tuple)):
        items = list(value)
    else:
        items = []
    out = []
    seen = set()
    for item in items:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
        if len(out) >= limit:
            break
    return out


def _judgment_side(label):
    text = str(label or "").upper()
    if "BUY" in text:
        return "BUY"
    if "SELL" in text:
        return "SELL"
    return "NEUTRAL"


def _compare_ai_vs_engine(ai_label, engine_label):
    ai_side = _judgment_side(ai_label)
    engine_side = _judgment_side(engine_label)
    if ai_label == engine_label:
        return "EXACT", "NONE"
    if ai_side == engine_side:
        return "ALIGNED", "TIMING"
    if "NEUTRAL" in {ai_side, engine_side}:
        return "MIXED", "RISK"
    return "DISAGREE", "TREND"


def _extract_json_blob(raw_text):
    raw = str(raw_text or "").strip()
    if not raw:
        return ""
    code_match = re.search(r"```json\s*(\{.*?\})\s*```", raw, re.DOTALL | re.IGNORECASE)
    if code_match:
        return code_match.group(1).strip()
    brace_match = re.search(r"(\{.*\})", raw, re.DOTALL)
    if brace_match:
        return brace_match.group(1).strip()
    return ""


def build_prompt_text(dc, meta):
    latest_row = dc.iloc[-1] if len(dc) else {}
    recent_ohlcv = []
    for idx, row in dc.tail(20).iterrows():
        recent_ohlcv.append(
            f"{idx.strftime('%m/%d')} O={row.get('Open', 0):.2f} H={row.get('High', 0):.2f} "
            f"L={row.get('Low', 0):.2f} C={row.get('Close', 0):.2f} V={row.get('Volume', 0):,.0f}"
        )

    indicator_tape = []
    for idx, row in dc.tail(10).iterrows():
        indicator_tape.append(
            f"{idx.strftime('%m/%d')} C={row.get('Close', 0):.2f} HMA={row.get('HMA', 0):.2f} "
            f"RSI={row.get('RSI', 0):.1f} MFI={row.get('MFI', 0):.1f} WT1={row.get('WT1', 0):.1f} "
            f"MACD_Hist={row.get('MACD_Hist', 0):+.4f} ADX={row.get('ADX', 0):.1f} "
            f"StochK={row.get('StochK', 0):.1f} StochD={row.get('StochD', 0):.1f} "
            f"ATR={row.get('ATR', 0):.2f} Percent_B={row.get('Percent_B', 0):.2f} "
            f"WR={row.get('Williams_R', 0):.1f} CCI={row.get('CCI', 0):.1f} "
            f"ROC={row.get('ROC', 0):+.2f} RMI={row.get('RMI', 0):.1f} TRIX={row.get('TRIX', 0):+.3f}"
        )

    signal_lines = []
    combo_lines = []
    for idx, row in dc.tail(20).iterrows():
        day_signals = []
        for key, cfg in SIGNAL_REGISTRY.items():
            if row.get(key, False):
                day_signals.append(f"{cfg['dir']}:{cfg['kor']}")
        if day_signals:
            signal_lines.append(f"{idx.strftime('%m/%d')}: {', '.join(day_signals)}")

        day_combos = []
        for key, cfg in COMBINED_SCAN_REGISTRY.items():
            if row.get(key, False):
                day_combos.append(f"{cfg['dir']}:{cfg['kor']}[T{cfg['tier']}]")
        if day_combos:
            combo_lines.append(f"{idx.strftime('%m/%d')}: {', '.join(day_combos)}")

    latest = meta
    latest_snapshot = (
        f"Last={latest.get('price', 0):.2f}, HMA={latest_row.get('HMA', 0):.2f}, "
        f"RSI={latest.get('rsi', 0):.1f}, MFI={latest.get('mfi', 0):.1f}, WT1={latest.get('wt1', 0):.1f}, "
        f"MACD_Hist={latest.get('macd_hist', 0):+.4f}, ADX={latest.get('adx', 0):.1f}, "
        f"StochK={latest.get('stochk', 0):.1f}, StochD={latest_row.get('StochD', latest.get('slowk', 0)):.1f}, "
        f"ATR={latest.get('atr', 0):.2f}, Percent_B={latest.get('percent_b', 0):.2f}, "
        f"Williams_R={latest.get('williams_r', 0):.1f}, CCI={latest.get('cci', 0):.1f}, "
        f"ROC={latest.get('roc', 0):+.2f}, RMI={latest.get('rmi', 0):.1f}, "
        f"TRIX={latest.get('trix', 0):+.3f}, Price_Osc={latest.get('price_oscillator', 0):+.3f}"
    )
    structure_snapshot = (
        f"VP_POC={latest.get('vp_poc', 0):.2f}, VP_VAH={latest.get('vp_vah', 0):.2f}, "
        f"VP_VAL={latest.get('vp_val', 0):.2f}, VP_Long_RR={latest.get('vp_long_rr', 0):.2f}, "
        f"VP_Short_RR={latest.get('vp_short_rr', 0):.2f}, VWAP={latest.get('vwap', 0):.2f}, "
        f"Fixed_VWAP={latest.get('fixed_vwap', 0):.2f}, Envelope%={latest.get('envelope_percent', 0):.2f}, "
        f"Vol_Osc={latest.get('volume_oscillator', 0):+.2f}, Mass_Index={latest.get('mass_index', 0):.2f}"
    )

    return (
        "[A. Recent OHLCV]\n"
        + "\n".join(recent_ohlcv)
        + "\n\n[B. Latest Indicator Snapshot]\n"
        + latest_snapshot
        + "\n"
        + structure_snapshot
        + "\n\n[C. Recent Indicator Tape]\n"
        + ("\n".join(indicator_tape) if indicator_tape else "(none)")
        + "\n\n[D. Signal Detection List]\n"
        + ("\n".join(signal_lines[-15:]) if signal_lines else "(none)")
        + "\n\n[E. Combo Signal Detection List]\n"
        + ("\n".join(combo_lines[-10:]) if combo_lines else "(none)")
    )


def build_ai_prompt(ticker, prompt_tape):
    return f"""
You are the independent AI second-opinion model inside {BRAND_NAME}.
Write every natural-language field in Korean.

Hard rules:
1. Use only the supplied OHLCV, indicators, signal detection list, and combo signal detection list.
2. Do not mention committee, ensemble, veto, action label, confidence from another system, or any engine audit wording.
3. Do not assume you know the existing engine judgment.
4. Make an independent call from the objective data only.
5. Use exactly one label from: STRONG_BUY, BUY, WATCH_BUY, NEUTRAL, WATCH_SELL, SELL, STRONG_SELL.
6. Return only valid JSON. No markdown, no prose before or after the JSON.

Required JSON schema:
{{
  "AI_Judgment": "one of the allowed labels",
  "AI_Confidence": 0,
  "AI_Bullish_Score": 0,
  "AI_Bearish_Score": 0,
  "AI_Risk_Flags": ["short Korean phrase"],
  "AI_Key_Drivers": ["short Korean phrase"],
  "AI_Reason": "2-4 Korean sentences explaining the call from the supplied data"
}}

Field rules:
- AI_Confidence: integer 0-100
- AI_Bullish_Score: integer 0-100
- AI_Bearish_Score: integer 0-100
- AI_Risk_Flags: 0-4 items
- AI_Key_Drivers: 2-4 items when possible

Ticker:
{ticker}

Input:
{prompt_tape}
""".strip()


def parse_ai_signal_assisted_response(raw_text, engine_judgment=""):
    raw = str(raw_text or "").strip()
    if not raw:
        return {
            "available": False,
            "AI_Judgment": "NEUTRAL",
            "AI_Confidence": 0,
            "AI_Bullish_Score": 0,
            "AI_Bearish_Score": 0,
            "AI_Risk_Flags": [],
            "AI_Key_Drivers": [],
            "AI_Reason": "AI 응답이 비어 있습니다.",
            "AI_Agreement": "UNAVAILABLE",
            "AI_Disagreement_Type": "MIXED",
            "raw_text": raw,
        }

    blob = _extract_json_blob(raw)
    if not blob:
        return {
            "available": False,
            "AI_Judgment": "NEUTRAL",
            "AI_Confidence": 0,
            "AI_Bullish_Score": 0,
            "AI_Bearish_Score": 0,
            "AI_Risk_Flags": [],
            "AI_Key_Drivers": [],
            "AI_Reason": "AI 응답을 구조화된 JSON으로 읽지 못했습니다.",
            "AI_Agreement": "UNAVAILABLE",
            "AI_Disagreement_Type": "MIXED",
            "raw_text": raw,
        }

    try:
        data = json.loads(blob)
    except json.JSONDecodeError:
        return {
            "available": False,
            "AI_Judgment": "NEUTRAL",
            "AI_Confidence": 0,
            "AI_Bullish_Score": 0,
            "AI_Bearish_Score": 0,
            "AI_Risk_Flags": [],
            "AI_Key_Drivers": [],
            "AI_Reason": "AI JSON 파싱에 실패했습니다.",
            "AI_Agreement": "UNAVAILABLE",
            "AI_Disagreement_Type": "MIXED",
            "raw_text": raw,
        }

    label = str(data.get("AI_Judgment", "NEUTRAL")).strip().upper()
    if label not in _AI_LABELS:
        label = "NEUTRAL"

    agreement, disagreement_type = _compare_ai_vs_engine(label, engine_judgment)
    result = {
        "available": True,
        "AI_Judgment": label,
        "AI_Confidence": _clamp_int(data.get("AI_Confidence"), default=0),
        "AI_Bullish_Score": _clamp_int(data.get("AI_Bullish_Score"), default=0),
        "AI_Bearish_Score": _clamp_int(data.get("AI_Bearish_Score"), default=0),
        "AI_Risk_Flags": _normalize_text_list(data.get("AI_Risk_Flags"), limit=4),
        "AI_Key_Drivers": _normalize_text_list(data.get("AI_Key_Drivers"), limit=4),
        "AI_Reason": str(data.get("AI_Reason", "") or "").strip(),
        "AI_Agreement": agreement,
        "AI_Disagreement_Type": disagreement_type if disagreement_type in _AI_DISAGREEMENT_TYPES else "MIXED",
        "raw_text": raw,
    }

    if not result["AI_Reason"]:
        result["AI_Reason"] = "AI가 구조화된 판단은 줬지만 사유 설명은 비어 있습니다."
    return result
