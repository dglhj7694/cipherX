import json
import math
import re
from typing import Any

from branding import BRAND_NAME


AI_LABELS = (
    "STRONG_BUY",
    "BUY",
    "WATCH_BUY",
    "NEUTRAL",
    "WATCH_SELL",
    "SELL",
    "STRONG_SELL",
)
AI_DISAGREEMENT_TYPES = ("NONE", "TIMING", "RISK", "TREND", "MIXED")
AI_STRATEGY_STYLES = (
    "초단타",
    "단기",
    "스윙",
    "추세추종",
    "눌림목 되돌림",
    "대기/시장체크",
    "관망",
)

_AI_LABEL_SET = set(AI_LABELS)
_AI_DISAGREEMENT_TYPE_SET = set(AI_DISAGREEMENT_TYPES)
_AI_STRATEGY_STYLE_SET = set(AI_STRATEGY_STYLES)


def _clamp_int(value, default=0, lo=0, hi=100):
    try:
        return max(lo, min(hi, int(round(float(value)))))
    except (TypeError, ValueError):
        return default


def _safe_float(value, default=0.0):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _num(value, digits=2, signed=False):
    number = _safe_float(value)
    return f"{number:+.{digits}f}" if signed else f"{number:.{digits}f}"


def _money(value):
    number = _safe_float(value)
    if abs(number) >= 1_000_000_000:
        return f"{number / 1_000_000_000:.2f}B"
    if abs(number) >= 1_000_000:
        return f"{number / 1_000_000:.2f}M"
    return f"{number:,.0f}"


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


def _normalize_text(value, default="", limit=220):
    text = str(value or "").strip()
    if not text:
        return default
    text = re.sub(r"\s+", " ", text)
    if limit > 0:
        return text[:limit].strip()
    return text


def _normalize_strategy_playbook(value, limit=5):
    if not isinstance(value, (list, tuple)):
        return []
    out = []
    seen = set()
    for item in value:
        if not isinstance(item, dict):
            continue
        style = _normalize_text(item.get("style") or item.get("name"), limit=40)
        if not style:
            continue
        if style not in _AI_STRATEGY_STYLE_SET:
            style = style[:40]
        if style in seen:
            continue
        summary = _normalize_text(item.get("summary"), limit=220)
        entry = _normalize_text(item.get("entry"), limit=120)
        invalidation = _normalize_text(item.get("invalidation"), limit=120)
        target = _normalize_text(item.get("target"), limit=120)
        if not any([summary, entry, invalidation, target]):
            continue
        seen.add(style)
        out.append(
            {
                "style": style,
                "fit": _clamp_int(item.get("fit"), default=0),
                "summary": summary,
                "entry": entry,
                "invalidation": invalidation,
                "target": target,
            }
        )
        if len(out) >= limit:
            break
    return out


def _normalize_evidence_details(value, limit=8):
    if not isinstance(value, (list, tuple)):
        return []
    out = []
    seen = set()
    for item in value:
        if isinstance(item, dict):
            category = _normalize_text(item.get("category") or item.get("name"), limit=40)
            observation = _normalize_text(item.get("observation") or item.get("evidence"), limit=180)
            interpretation = _normalize_text(item.get("interpretation") or item.get("meaning"), limit=220)
            impact = _normalize_text(item.get("impact"), default="neutral", limit=20).lower()
            importance = _clamp_int(item.get("importance"), default=50)
        else:
            category = "근거"
            observation = _normalize_text(item, limit=180)
            interpretation = ""
            impact = "neutral"
            importance = 50
        if impact not in {"bullish", "bearish", "neutral", "risk"}:
            impact = "neutral"
        if not any([category, observation, interpretation]):
            continue
        key = (category, observation, interpretation, impact)
        if key in seen:
            continue
        seen.add(key)
        out.append(
            {
                "category": category or "근거",
                "observation": observation,
                "interpretation": interpretation,
                "impact": impact,
                "importance": importance,
            }
        )
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


def _row_value(row, key, fallback=0):
    try:
        return row.get(key, fallback)
    except AttributeError:
        return fallback


def _date_text(index_value):
    if hasattr(index_value, "strftime"):
        return index_value.strftime("%Y-%m-%d")
    return str(index_value or "")


def _latest_price_line(meta, latest_row):
    return (
        f"price={_num(meta.get('price', _row_value(latest_row, 'Close')))}, "
        f"change={_num(meta.get('price_change_pct', 0), 2, True)}%, "
        f"open={_num(_row_value(latest_row, 'Open'))}, high={_num(_row_value(latest_row, 'High'))}, "
        f"low={_num(_row_value(latest_row, 'Low'))}, close={_num(_row_value(latest_row, 'Close'))}, "
        f"volume={_money(_row_value(latest_row, 'Volume'))}"
    )


def _missing(value):
    if value is None:
        return True
    try:
        return bool(value != value)
    except Exception:
        return False


def _first_row_value(row, columns):
    candidates = (columns,) if isinstance(columns, str) else tuple(columns)
    for column in candidates:
        value = _row_value(row, column, None)
        if not _missing(value):
            return value
    return None


def _indicator_spec(label, columns, digits=2, signed=False, kind="num"):
    return {
        "label": label,
        "columns": columns,
        "digits": digits,
        "signed": signed,
        "kind": kind,
    }


def _format_indicator_field(row, spec):
    value = _first_row_value(row, spec["columns"])
    if _missing(value):
        return ""
    label = spec["label"]
    kind = spec.get("kind", "num")
    if kind == "flag":
        return f"{label}=1" if bool(value) else ""
    if kind == "money":
        return f"{label}={_money(value)}"
    if kind == "int":
        return f"{label}={_num(value, 0, spec.get('signed', False))}"
    if isinstance(value, str):
        text = value.strip()
        return f"{label}={text}" if text else ""
    return f"{label}={_num(value, spec.get('digits', 2), spec.get('signed', False))}"


def _format_indicator_group(row, name, fields):
    parts = []
    for spec in fields:
        text = _format_indicator_field(row, spec)
        if text:
            parts.append(text)
    return f"{name}[{' '.join(parts)}]" if parts else ""


INDICATOR_TAPE_GROUPS = (
    (
        "Vol",
        (
            _indicator_spec("V", "Volume", kind="money"),
            _indicator_spec("Vol20", "Volume_Ratio_20", 2),
            _indicator_spec("Vol50", "Volume_Ratio_50", 2),
            _indicator_spec("VolOsc", "Volume_Oscillator", 2, True),
            _indicator_spec("Dollar20", "Dollar_Volume_20", kind="money"),
        ),
    ),
    (
        "WaveTrend",
        (
            _indicator_spec("WT1", "WT1", 1, True),
            _indicator_spec("WT2", "WT2", 1, True),
            _indicator_spec("WTAccel", "WT_Accel", 2, True),
            _indicator_spec("RSI_MFI", "RSI_MFI", 1, True),
        ),
    ),
    (
        "MACD",
        (
            _indicator_spec("Line", "MACD_Line", 4, True),
            _indicator_spec("Signal", "MACD_Signal", 4, True),
            _indicator_spec("Hist", "MACD_Hist", 4, True),
            _indicator_spec("Accel", "MACD_Accel", 4, True),
        ),
    ),
    (
        "MoneyFlow",
        (
            _indicator_spec("MFI", "MFI", 1),
            _indicator_spec("CMF", "CMF", 3, True),
            _indicator_spec("Chaikin", "Chaikin_Oscillator", 2, True),
            _indicator_spec("III", "Intraday_Intensity_Index", 2, True),
        ),
    ),
    (
        "StochSlow",
        (
            _indicator_spec("K", "SlowK", 1),
            _indicator_spec("D", "SlowD", 1),
            _indicator_spec("StochK", "StochK", 1),
            _indicator_spec("StochD", "StochD", 1),
        ),
    ),
    (
        "SqueezeMom",
        (
            _indicator_spec("On", "Squeeze_On", kind="flag"),
            _indicator_spec("Mom", "Squeeze_Momentum", 3, True),
            _indicator_spec("Rising", "Squeeze_Mom_Rising", kind="flag"),
            _indicator_spec("Positive", "Squeeze_Mom_Positive", kind="flag"),
            _indicator_spec("BBWidth", "BB_Width", 4),
        ),
    ),
    (
        "ReversalPack",
        (
            _indicator_spec("WilliamsR", "Williams_R", 1, True),
            _indicator_spec("CCI", "CCI", 1, True),
            _indicator_spec("Mass", "Mass_Index", 2),
            _indicator_spec("SmartBullDiv", "Smart_Money_Bullish_Div", kind="flag"),
            _indicator_spec("SmartBearDiv", "Smart_Money_Bearish_Div", kind="flag"),
        ),
    ),
    (
        "MomentumPack",
        (
            _indicator_spec("ROC", "ROC", 2, True),
            _indicator_spec("RMI", "RMI", 1),
            _indicator_spec("TRIX", "TRIX", 3, True),
            _indicator_spec("Mom10", "Momentum_10", 2, True),
            _indicator_spec("PriceOsc", "Price_Oscillator", 3, True),
        ),
    ),
    (
        "FlowPack",
        (
            _indicator_spec("OBV", "OBV", 0, True),
            _indicator_spec("OBVSlope", "OBV_Slope", 3, True),
            _indicator_spec("ADLine", "AD_Line", 0, True),
            _indicator_spec("ADLineZ", "AD_Line_Z", 2, True),
        ),
    ),
    (
        "ADX/DMI",
        (
            _indicator_spec("ADX", "ADX", 1),
            _indicator_spec("+DI", "Plus_DI", 1),
            _indicator_spec("-DI", "Minus_DI", 1),
        ),
    ),
    (
        "BB/VWAP",
        (
            _indicator_spec("PctB", "Percent_B", 2),
            _indicator_spec("BBUp", "BB_Up", 2),
            _indicator_spec("BBLow", "BB_Low", 2),
            _indicator_spec("VWAP", "VWAP", 2),
            _indicator_spec("VWAPOsc", "VWAP_Osc", 2, True),
            _indicator_spec("AVWAP", "Fixed_VWAP", 2),
        ),
    ),
    (
        "RSI/StochRSI",
        (
            _indicator_spec("RSI", "RSI", 1),
            _indicator_spec("RSIAccel", "RSI_Accel", 2, True),
            _indicator_spec("StochK", "StochK", 1),
            _indicator_spec("StochD", "StochD", 1),
        ),
    ),
    (
        "CMF/OBV/AD",
        (
            _indicator_spec("CMF", "CMF", 3, True),
            _indicator_spec("OBVSlope", "OBV_Slope", 3, True),
            _indicator_spec("ADLine", "AD_Line", 0, True),
            _indicator_spec("Chaikin", "Chaikin_Oscillator", 2, True),
        ),
    ),
    (
        "Ichimoku/Mass",
        (
            _indicator_spec("Tenkan", "Ichimoku_Tenkan", 2),
            _indicator_spec("Kijun", "Ichimoku_Kijun", 2),
            _indicator_spec("SenkouA", "Ichimoku_SenkouA", 2),
            _indicator_spec("SenkouB", "Ichimoku_SenkouB", 2),
            _indicator_spec("Mass", "Mass_Index", 2),
        ),
    ),
    (
        "Volatility/Liquidity",
        (
            _indicator_spec("ATR", "ATR", 2),
            _indicator_spec("ATRpct", "ATR_Pct", 2),
            _indicator_spec("BBWidth", "BB_Width", 4),
            _indicator_spec("Thin", "Thin_Trade_Risk", kind="flag"),
            _indicator_spec("Dollar20", "Dollar_Volume_20", kind="money"),
        ),
    ),
    (
        "RS/Acceleration",
        (
            _indicator_spec("RSRatio", "RS_Ratio", 3),
            _indicator_spec("RSScore", "RS_Score", 2, True),
            _indicator_spec("PriceSlope5", "Price_Slope_5", 4, True),
            _indicator_spec("CompAccel", "Composite_Accel", 2, True),
            _indicator_spec("WTAccel", "WT_Accel", 2, True),
        ),
    ),
    (
        "Position/Structure",
        (
            _indicator_spec("MA20GapATR", "MA20_ATR_Gap", 2, True),
            _indicator_spec("ChannelPos", "Channel_Position", 2, True),
            _indicator_spec("ChUp", "Price_Channel_Up", 2),
            _indicator_spec("ChMid", "Price_Channel_Mid", 2),
            _indicator_spec("ChLow", "Price_Channel_Low", 2),
        ),
    ),
    (
        "HMA/UTBot",
        (
            _indicator_spec("HMA", "HMA", 2),
            _indicator_spec("HMA25", "HMA25", 2),
            _indicator_spec("HMA25Up", "HMA25_Slope_Up", kind="flag"),
            _indicator_spec("HMA25Dn", "HMA25_Slope_Down", kind="flag"),
            _indicator_spec("UTDir", "UTBot_Dir", 0, True, "int"),
            _indicator_spec("UTStop", "UTBot_Stop", 2),
        ),
    ),
    (
        "VP/POC/RR",
        (
            _indicator_spec("POC", "VP_POC", 2),
            _indicator_spec("VAH", "VP_VAH", 2),
            _indicator_spec("VAL", "VP_VAL", 2),
            _indicator_spec("LongRR", "VP_Long_RR", 2),
            _indicator_spec("ShortRR", "VP_Short_RR", 2),
            _indicator_spec("Upside", "Upside_Space_Score", 2, True),
        ),
    ),
    (
        "FibStructure",
        (
            _indicator_spec("SwingH", "Fib_Swing_High", 2),
            _indicator_spec("SwingL", "Fib_Swing_Low", 2),
            _indicator_spec("Fib382", "Fib_382", 2),
            _indicator_spec("Fib50", "Fib_50", 2),
            _indicator_spec("Fib618", "Fib_618", 2),
            _indicator_spec("ExtUp", "Fib_Ext_1618_Up", 2),
            _indicator_spec("ExtDn", "Fib_Ext_1618_Down", 2),
        ),
    ),
    (
        "MA/EMA",
        (
            _indicator_spec("MA20", "MA20", 2),
            _indicator_spec("MA50", "MA50", 2),
            _indicator_spec("MA200", "MA200", 2),
            _indicator_spec("EMA12", "EMA12", 2),
            _indicator_spec("EMA26", "EMA26", 2),
            _indicator_spec("EMA50", "EMA50", 2),
            _indicator_spec("EMA200", "EMA200", 2),
        ),
    ),
    (
        "Trendline/Pattern",
        (
            _indicator_spec("TLFit", "Trendline_Fit", 2),
            _indicator_spec("TLDistATR", "Trendline_Dist_ATR", 2, True),
            _indicator_spec("TLSlopePct", "Trendline_Slope_Pct", 2, True),
            _indicator_spec("BoxBase", "Box_Base", kind="flag"),
            _indicator_spec("ChannelUp", "Channel_Up", kind="flag"),
            _indicator_spec("ChannelDn", "Channel_Down", kind="flag"),
        ),
    ),
)


def build_prompt_text(dc, meta):
    meta = dict(meta or {})
    row_count = len(dc) if dc is not None else 0
    latest_row = dc.iloc[-1] if row_count else {}
    history_days = min(row_count, 126)
    history_window = dc.tail(history_days) if history_days else dc

    if history_days:
        first_row = history_window.iloc[0]
        last_row = history_window.iloc[-1]
        start_date = _date_text(history_window.index[0])
        end_date = _date_text(history_window.index[-1])
        first_close = _safe_float(_row_value(first_row, "Close"), 1.0)
        last_close = _safe_float(_row_value(last_row, "Close"))
        change_pct = ((last_close / max(first_close, 1e-10)) - 1.0) * 100.0
        high_value = history_window["High"].max() if "High" in history_window else last_close
        low_value = history_window["Low"].min() if "Low" in history_window else last_close
        avg_volume = history_window["Volume"].mean() if "Volume" in history_window else 0
        history_overview = (
            f"range={start_date}~{end_date}, bars={history_days}, "
            f"start_close={_num(first_close)}, last_close={_num(last_close)}, "
            f"period_return={_num(change_pct, 2, True)}%, high={_num(high_value)}, low={_num(low_value)}, "
            f"avg_volume={_money(avg_volume)}"
        )
    else:
        history_overview = "range=unavailable, bars=0"

    latest_snapshot = _latest_price_line(meta, latest_row)
    indicator_snapshot = (
        f"HMA={_num(_row_value(latest_row, 'HMA', meta.get('price')))}, "
        f"MA20={_num(meta.get('ma20', _row_value(latest_row, 'MA20')))}, "
        f"MA50={_num(meta.get('ma50', _row_value(latest_row, 'MA50')))}, "
        f"MA200={_num(meta.get('ma200', _row_value(latest_row, 'MA200')))}, "
        f"RSI={_num(meta.get('rsi', _row_value(latest_row, 'RSI')), 1)}, "
        f"MFI={_num(meta.get('mfi', _row_value(latest_row, 'MFI')), 1)}, "
        f"WT1={_num(meta.get('wt1', _row_value(latest_row, 'WT1')), 1, True)}, "
        f"MACD_Hist={_num(meta.get('macd_hist', _row_value(latest_row, 'MACD_Hist')), 4, True)}, "
        f"ADX={_num(meta.get('adx', _row_value(latest_row, 'ADX')), 1)}, "
        f"ATR%={_num(meta.get('atr_pct', 0), 2)}%, "
        f"Percent_B={_num(meta.get('percent_b', _row_value(latest_row, 'Percent_B')), 2)}, "
        f"Volume_Ratio_20={_num(meta.get('volume_ratio_20', _row_value(latest_row, 'Volume_Ratio_20')), 2)}"
    )
    structure_snapshot = (
        f"VWAP={_num(meta.get('vwap', 0))}, fixed_vwap={_num(meta.get('fixed_vwap', 0))}, "
        f"VP_POC={_num(meta.get('vp_poc', 0))}, VP_VAH={_num(meta.get('vp_vah', 0))}, VP_VAL={_num(meta.get('vp_val', 0))}, "
        f"BB_UP={_num(meta.get('bb_up', 0))}, BB_LOW={_num(meta.get('bb_low', 0))}, "
        f"MA20_ATR_Gap={_num(meta.get('ma20_atr_gap', 0), 2, True)}, "
        f"ChannelPos={_num(meta.get('channel_position', 0), 2, True)}"
    )
    flow_snapshot = (
        f"DollarVol20={_money(meta.get('dollar_volume_20', 0))}, "
        f"DollarVolZ={_num(meta.get('dollar_volume_z', 0), 2, True)}, "
        f"OBV_slope={_num(meta.get('obv_slope', 0), 3, True)}, "
        f"CMF={_num(meta.get('cmf', 0), 3, True)}, "
        f"Chaikin={_num(meta.get('chaikin_oscillator', 0), 2, True)}, "
        f"ADLineZ={_num(meta.get('ad_line_z', 0), 2, True)}"
    )
    market_snapshot = (
        f"stock_return_20={_num(meta.get('stock_return_20', 0), 2, True)}%, "
        f"spy_return_20={_num(meta.get('spy_return_20', 0), 2, True)}%, "
        f"excess_return_20={_num(meta.get('excess_return_20', 0), 2, True)}%, "
        f"market_breadth_score={_num(meta.get('market_breadth_score', 0), 2, True)}, "
        f"macro_pressure={_num(meta.get('macro_pressure_score', 0), 2, True)}, "
        f"vix_pressure={_num(meta.get('vix_pressure_score', 0), 2, True)}, "
        f"tnx_pressure={_num(meta.get('tnx_pressure_score', 0), 2, True)}, "
        f"dxy_pressure={_num(meta.get('dxy_pressure_score', 0), 2, True)}"
    )

    indicator_tape = []
    if history_days:
        for idx, row in history_window.tail(60).iterrows():
            close_value = _safe_float(_row_value(row, "Close"))
            atr = _safe_float(_row_value(row, "ATR"))
            atr_pct = (atr / max(close_value, 1e-10)) * 100.0 if close_value else 0.0
            groups = [
                group_text
                for group_text in (
                    _format_indicator_group(row, group_name, fields)
                    for group_name, fields in INDICATOR_TAPE_GROUPS
                )
                if group_text
            ]
            indicator_tape.append(
                f"{_date_text(idx)} C={_num(close_value)} ATR%={_num(atr_pct, 2)} "
                + " | ".join(groups)
            )

    return (
        "# PROMPT TAPE\n"
        f"ticker={meta.get('ticker', '')}\n\n"
        "## A. 데이터 범위\n"
        f"{history_overview}\n\n"
        "## B. 최신 가격 스냅샷\n"
        f"{latest_snapshot}\n"
        "\n\n"
        "## C. 검증된 보조지표 스냅샷\n"
        f"{indicator_snapshot}\n"
        f"{structure_snapshot}\n"
        f"{flow_snapshot}\n\n"
        "## D. 시장/상대강도 맥락\n"
        f"{market_snapshot}\n\n"
        "## E. 최근 60봉 보조지표 테이프\n"
        + ("\n".join(indicator_tape) if indicator_tape else "none")
    )


def build_ai_prompt(ticker, prompt_tape):
    allowed_labels = ", ".join(AI_LABELS)
    allowed_styles = " | ".join(AI_STRATEGY_STYLES)
    return f"""
당신은 {BRAND_NAME}의 AI 보조 분석 모델입니다.
아래 PROMPT TAPE에 들어 있는 OHLCV, 검증된 보조지표, 수급/구조 지표, 시장/상대강도 맥락만 근거로 판단하세요.

분석 규칙:
1. 제공된 데이터 밖의 뉴스, 실적, 추정치, 개인적 추측은 사용하지 않습니다.
2. PROMPT TAPE에는 프로그램 엔진의 판단, 점수, 전략 후보, 시그널 라벨이 포함되지 않습니다. AI는 보조지표 데이터만으로 독립적인 2차 판단을 내립니다.
3. 매수/매도 단정 대신 현재 데이터에서 가능한 진입 조건, 무효화 기준, 리스크를 명확히 씁니다.
4. 단기 과열, 갭 실패, 추격 위험, 저유동성, 최근 매도 전환이 보이면 리스크에 반영합니다.
5. 결과는 JSON 객체만 반환합니다. Markdown, 설명 문장, 코드블록은 절대 붙이지 않습니다.

허용 라벨:
{allowed_labels}

허용 전략 스타일:
{allowed_styles}

반환 JSON 스키마:
{{
  "AI_Judgment": "one of allowed labels",
  "AI_Confidence": 0,
  "AI_Bullish_Score": 0,
  "AI_Bearish_Score": 0,
  "AI_Risk_Flags": ["짧은 한국어 리스크"],
  "AI_Key_Drivers": ["짧은 한국어 근거"],
  "AI_Evidence_Details": [
    {{
      "category": "가격/추세 | 모멘텀 | 수급/거래량 | 변동성/위치 | 시장/상대강도 | 리스크",
      "observation": "PROMPT TAPE에서 직접 읽은 수치 또는 변화",
      "interpretation": "그 관찰값이 판단에 미치는 의미",
      "impact": "bullish | bearish | neutral | risk",
      "importance": 0
    }}
  ],
  "AI_Counter_Evidence": ["판단과 반대되는 보조지표 근거"],
  "AI_Data_Limits": ["판단을 제한하는 데이터 한계"],
  "AI_Reason": "상세 근거를 종합해 4-6문장으로 설명",
  "AI_Trade_Strategy": "실전 대응을 1-3문장으로 요약",
  "AI_Entry_Plan": "진입 또는 대기 조건 1문장",
  "AI_Invalidation": "무효화 또는 손절 기준 1문장",
  "AI_Target_Plan": "목표/분할청산 구간 1문장",
  "AI_Strategy_Playbook": [
    {{
      "style": "{allowed_styles}",
      "fit": 0,
      "summary": "1-2문장",
      "entry": "짧은 진입 조건",
      "invalidation": "짧은 무효화 조건",
      "target": "짧은 목표 조건"
    }}
  ]
}}

필드 규칙:
- AI_Confidence, AI_Bullish_Score, AI_Bearish_Score는 0-100 정수입니다.
- AI_Risk_Flags는 0-4개, AI_Key_Drivers는 가능하면 2-4개입니다.
- AI_Evidence_Details는 4-8개를 작성하고, 각 항목은 PROMPT TAPE에 있는 보조지표 수치 또는 흐름을 observation에 직접 언급해야 합니다.
- AI_Counter_Evidence는 주 판단과 반대되는 보조지표가 있으면 1-4개 작성하고, 없으면 빈 배열로 둡니다.
- AI_Data_Limits는 데이터만으로 확정할 수 없는 점이나 확인이 필요한 조건을 0-3개 작성합니다.
- AI_Strategy_Playbook은 현재 데이터에 맞는 3-5개 스타일만 선택합니다.
- 혼조 또는 NEUTRAL에 가까우면 "관망" 또는 "대기/시장체크" 항목을 반드시 포함합니다.

티커:
{ticker}

PROMPT TAPE:
{prompt_tape}
""".strip()


def parse_ai_signal_assisted_response(raw_text, engine_judgment=""):
    raw = str(raw_text or "").strip()
    if not raw:
        return unavailable_ai_parse_result("AI 응답이 비어 있습니다.", raw)

    blob = _extract_json_blob(raw)
    if not blob:
        return unavailable_ai_parse_result("AI 응답을 구조화된 JSON으로 읽지 못했습니다.", raw)

    try:
        data = json.loads(blob)
    except json.JSONDecodeError:
        return unavailable_ai_parse_result("AI JSON 파싱에 실패했습니다.", raw)

    label = str(data.get("AI_Judgment", "NEUTRAL")).strip().upper()
    if label not in _AI_LABEL_SET:
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
        "AI_Evidence_Details": _normalize_evidence_details(data.get("AI_Evidence_Details"), limit=8),
        "AI_Counter_Evidence": _normalize_text_list(data.get("AI_Counter_Evidence"), limit=4),
        "AI_Data_Limits": _normalize_text_list(data.get("AI_Data_Limits"), limit=3),
        "AI_Reason": _normalize_text(data.get("AI_Reason", ""), default=""),
        "AI_Trade_Strategy": _normalize_text(data.get("AI_Trade_Strategy", ""), default=""),
        "AI_Entry_Plan": _normalize_text(data.get("AI_Entry_Plan", ""), default=""),
        "AI_Invalidation": _normalize_text(data.get("AI_Invalidation", ""), default=""),
        "AI_Target_Plan": _normalize_text(data.get("AI_Target_Plan", ""), default=""),
        "AI_Strategy_Playbook": _normalize_strategy_playbook(data.get("AI_Strategy_Playbook"), limit=5),
        "AI_Agreement": agreement,
        "AI_Disagreement_Type": disagreement_type if disagreement_type in _AI_DISAGREEMENT_TYPE_SET else "MIXED",
        "raw_text": raw,
    }

    if not result["AI_Reason"]:
        result["AI_Reason"] = "AI가 구조화된 판단은 줬지만 사유 설명은 비어 있습니다."
    if not result["AI_Evidence_Details"] and result["AI_Key_Drivers"]:
        result["AI_Evidence_Details"] = [
            {
                "category": "핵심 근거",
                "observation": driver,
                "interpretation": "AI가 핵심 근거로 제시한 항목입니다.",
                "impact": "neutral",
                "importance": max(40, 80 - index * 10),
            }
            for index, driver in enumerate(result["AI_Key_Drivers"][:4])
        ]
    if result["AI_Strategy_Playbook"] and not result["AI_Trade_Strategy"]:
        result["AI_Trade_Strategy"] = result["AI_Strategy_Playbook"][0].get("summary", "")
    if result["AI_Strategy_Playbook"] and not result["AI_Entry_Plan"]:
        result["AI_Entry_Plan"] = result["AI_Strategy_Playbook"][0].get("entry", "")
    if result["AI_Strategy_Playbook"] and not result["AI_Invalidation"]:
        result["AI_Invalidation"] = result["AI_Strategy_Playbook"][0].get("invalidation", "")
    if result["AI_Strategy_Playbook"] and not result["AI_Target_Plan"]:
        result["AI_Target_Plan"] = result["AI_Strategy_Playbook"][0].get("target", "")
    if not result["AI_Trade_Strategy"]:
        result["AI_Trade_Strategy"] = "전략 요약이 비어 있어 핵심 레벨 확인 후 보수적으로 대응하는 편이 좋습니다."
    if not result["AI_Strategy_Playbook"]:
        if label == "NEUTRAL":
            fallback_style = "관망"
        elif label in {"WATCH_BUY", "WATCH_SELL"}:
            fallback_style = "단기"
        else:
            fallback_style = "추세추종"
        result["AI_Strategy_Playbook"] = [
            {
                "style": fallback_style,
                "fit": result["AI_Confidence"],
                "summary": result["AI_Trade_Strategy"],
                "entry": result["AI_Entry_Plan"],
                "invalidation": result["AI_Invalidation"],
                "target": result["AI_Target_Plan"],
            }
        ]
    return result


def unavailable_ai_parse_result(message: str, raw_text: str = "") -> dict[str, Any]:
    return {
        "available": False,
        "AI_Judgment": "NEUTRAL",
        "AI_Confidence": 0,
        "AI_Bullish_Score": 0,
        "AI_Bearish_Score": 0,
        "AI_Risk_Flags": [],
        "AI_Key_Drivers": [],
        "AI_Evidence_Details": [],
        "AI_Counter_Evidence": [],
        "AI_Data_Limits": [],
        "AI_Reason": message,
        "AI_Trade_Strategy": "",
        "AI_Entry_Plan": "",
        "AI_Invalidation": "",
        "AI_Target_Plan": "",
        "AI_Strategy_Playbook": [],
        "AI_Agreement": "UNAVAILABLE",
        "AI_Disagreement_Type": "MIXED",
        "raw_text": raw_text,
    }
