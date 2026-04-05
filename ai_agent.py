import json
import re

from branding import BRAND_NAME


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
_AI_STRATEGY_STYLES = {
    "초단타",
    "단타",
    "스윙",
    "추세추종",
    "피보나치 되돌림",
    "퀀트/시장체크",
    "관망",
}


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
        if style not in _AI_STRATEGY_STYLES:
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
    latest = meta or {}
    history_days = min(len(dc), 126)
    history_window = dc.tail(history_days) if history_days else dc

    def _num(value, digits=2, signed=False):
        try:
            number = float(value)
        except (TypeError, ValueError):
            number = 0.0
        if number != number or number == float("inf") or number == float("-inf"):
            number = 0.0
        return f"{number:+.{digits}f}" if signed else f"{number:.{digits}f}"

    def _bool_flag(name, condition):
        return name if bool(condition) else ""

    history_overview = "범위 정보 없음"
    recent_ohlcv = []
    if history_days:
        high_series = history_window["High"] if "High" in history_window else history_window["Close"] if "Close" in history_window else []
        low_series = history_window["Low"] if "Low" in history_window else history_window["Close"] if "Close" in history_window else []
        volume_avg = history_window["Volume"].mean() if "Volume" in history_window else 0
        start_date = history_window.index[0].strftime("%Y-%m-%d")
        end_date = history_window.index[-1].strftime("%Y-%m-%d")
        start_close = _num(history_window.iloc[0].get("Close", 0))
        end_close = _num(history_window.iloc[-1].get("Close", 0))
        change_pct = _num(
            ((float(history_window.iloc[-1].get("Close", 0) or 0) / (float(history_window.iloc[0].get("Close", 0) or 1) + 1e-10)) - 1.0) * 100.0,
            2,
            True,
        )
        high_6m = _num(high_series.max() if len(high_series) else 0)
        low_6m = _num(low_series.min() if len(low_series) else 0)
        avg_vol_6m = f"{float(volume_avg or 0):,.0f}"
        history_overview = (
            f"범위={start_date}~{end_date}, 거래일={history_days}, "
            f"시작종가={start_close}, 마지막종가={end_close}, 6개월수익률={change_pct}%, "
            f"6개월고가={high_6m}, 6개월저가={low_6m}, 평균거래량={avg_vol_6m}"
        )
        for idx, row in history_window.iterrows():
            recent_ohlcv.append(
                f"{idx.strftime('%Y-%m-%d')} O={_num(row.get('Open', 0))} H={_num(row.get('High', 0))} "
                f"L={_num(row.get('Low', 0))} C={_num(row.get('Close', 0))} V={float(row.get('Volume', 0) or 0):,.0f}"
            )

    indicator_tape = []
    for idx, row in history_window.iterrows():
        close_value = float(row.get("Close", 0) or 0)
        atr_pct = ((float(row.get("ATR", 0) or 0) / (close_value + 1e-10)) * 100.0) if close_value else 0.0
        indicator_tape.append(
            f"{idx.strftime('%Y-%m-%d')} C={_num(close_value)} HMA={_num(row.get('HMA', 0))} "
            f"RSI={_num(row.get('RSI', 0), 1)} MFI={_num(row.get('MFI', 0), 1)} "
            f"MACD_H={_num(row.get('MACD_Hist', 0), 4, True)} ADX={_num(row.get('ADX', 0), 1)} "
            f"ATR%={_num(atr_pct, 2)} %B={_num(row.get('Percent_B', 0), 2)} WR={_num(row.get('Williams_R', 0), 1)} "
            f"ROC={_num(row.get('ROC', 0), 2, True)} VolR20={_num(row.get('Volume_Ratio_20', 0), 2)} "
            f"Chaikin={_num(row.get('Chaikin_Oscillator', 0), 2, True)}"
        )

    signal_lines = []
    for item in latest.get("recent_signals") or []:
        if bool(item.get("is_combined")):
            continue
        label = str(item.get("label") or item.get("key") or "").strip()
        date_text = str(item.get("date") or "").strip()
        direction = str(item.get("dir") or "").strip()
        if not label:
            continue
        signal_lines.append(f"{date_text} {direction} {label}".strip())

    latest_snapshot = (
        f"종가={_num(latest.get('price', 0))}, 등락률={_num(latest.get('price_change_pct', 0), 2, True)}%, "
        f"HMA={_num(latest_row.get('HMA', latest.get('price', 0)))}, MA20={_num(latest.get('ma20', 0))}, "
        f"MA50={_num(latest.get('ma50', 0))}, MA200={_num(latest.get('ma200', 0))}, "
        f"EMA12={_num(latest.get('ema12', 0))}, EMA26={_num(latest.get('ema26', 0))}, "
        f"RSI={_num(latest.get('rsi', 0), 1)}, MFI={_num(latest.get('mfi', 0), 1)}, WT1={_num(latest.get('wt1', 0), 1, True)}, "
        f"MACD_Hist={_num(latest.get('macd_hist', 0), 4, True)}, ADX={_num(latest.get('adx', 0), 1)}, "
        f"StochK={_num(latest.get('stochk', 0), 1)}, ATR={_num(latest.get('atr', 0))}, ATR%={_num(latest.get('atr_pct', 0), 2)}%, "
        f"%B={_num(latest.get('percent_b', 0), 2)}, WR={_num(latest.get('williams_r', 0), 1)}, "
        f"CCI={_num(latest.get('cci', 0), 1, True)}, ROC={_num(latest.get('roc', 0), 2, True)}, "
        f"RMI={_num(latest.get('rmi', 0), 1)}, TRIX={_num(latest.get('trix', 0), 3, True)}, "
        f"PriceOsc={_num(latest.get('price_oscillator', 0), 3, True)}, VolOsc={_num(latest.get('volume_oscillator', 0), 2, True)}"
    )
    structure_snapshot = (
        f"VWAP={_num(latest.get('vwap', 0))}, 고정VWAP={_num(latest.get('fixed_vwap', 0))}, "
        f"VP_POC={_num(latest.get('vp_poc', 0))}, VP_VAH={_num(latest.get('vp_vah', 0))}, VP_VAL={_num(latest.get('vp_val', 0))}, "
        f"롱RR={_num(latest.get('vp_long_rr', 0), 2)}, 숏RR={_num(latest.get('vp_short_rr', 0), 2)}, "
        f"볼밴상단={_num(latest.get('bb_up', 0))}, 볼밴하단={_num(latest.get('bb_low', 0))}, "
        f"Envelope%={_num(latest.get('envelope_percent', 0), 2)}, 채널상단={_num(latest.get('price_channel_up', 0))}, "
        f"채널중단={_num(latest.get('price_channel_mid', 0))}, 채널하단={_num(latest.get('price_channel_low', 0))}, "
        f"PSAR_Dir={int(latest.get('psar_dir', 0) or 0)}, SuperTrendGap={_num(latest.get('supertrend_gap', 0), 2, True)}%, "
        f"TenkanGap={_num(latest.get('tenkan_gap', 0), 2, True)}%, KijunGap={_num(latest.get('kijun_gap', 0), 2, True)}%, "
        f"CloudSpread={_num(latest.get('cloud_spread', 0), 2, True)}%"
    )
    flow_snapshot = (
        f"거래량비20={_num(latest.get('volume_ratio_20', 0), 2)}, 거래량비50={_num(latest.get('volume_ratio_50', 0), 2)}, "
        f"DollarVol20={_num(latest.get('dollar_volume_20', 0), 0)}, DollarVolZ={_num(latest.get('dollar_volume_z', 0), 2, True)}, "
        f"OBV기울기={_num(latest.get('obv_slope', 0), 3, True)}, IntradayIntensityIdx={_num(latest.get('intraday_intensity_index', 0), 2, True)}, "
        f"Chaikin={_num(latest.get('chaikin_oscillator', 0), 2, True)}, ADLineZ={_num(latest.get('ad_line_z', 0), 2, True)}, "
        f"MA20_ATR_Gap={_num(latest.get('ma20_atr_gap', 0), 2, True)}, ChannelPos={_num(latest.get('channel_position', 0), 2, True)}"
    )
    market_flags = [
        _bool_flag("BreadthRiskOn", latest.get("breadth_risk_on")),
        _bool_flag("BreadthRiskOff", latest.get("breadth_risk_off")),
        _bool_flag("SPYRiskOn", latest.get("spy_risk_on")),
        _bool_flag("SPYRiskOff", latest.get("spy_risk_off")),
        _bool_flag("VIXRiskOn", latest.get("vix_risk_on")),
        _bool_flag("VIXRiskOff", latest.get("vix_risk_off")),
        _bool_flag("TNXTailwind", latest.get("tnx_tailwind")),
        _bool_flag("TNXHeadwind", latest.get("tnx_headwind")),
        _bool_flag("DXYTailwind", latest.get("dxy_tailwind")),
        _bool_flag("DXYHeadwind", latest.get("dxy_headwind")),
    ]
    market_snapshot = (
        f"종목20일수익률={_num(latest.get('stock_return_20', 0), 2, True)}%, "
        f"SPY20일수익률={_num(latest.get('spy_return_20', 0), 2, True)}%, "
        f"상대수익률={_num(latest.get('excess_return_20', 0), 2, True)}%, "
        f"시장폭점수={_num(latest.get('market_breadth_score', 0), 2, True)}, "
        f"거시압력={_num(latest.get('macro_pressure_score', 0), 2, True)}, "
        f"VIX압력={_num(latest.get('vix_pressure_score', 0), 2, True)}, "
        f"TNX압력={_num(latest.get('tnx_pressure_score', 0), 2, True)}, "
        f"DXY압력={_num(latest.get('dxy_pressure_score', 0), 2, True)}, "
        f"시장상태={', '.join(flag for flag in market_flags if flag) or '중립'}"
    )

    return (
        "[A. 최근 6개월 OHLCV 일봉]\n"
        + history_overview
        + "\n"
        + "\n".join(recent_ohlcv)
        + "\n\n[B. 최신 차트 지표 스냅샷]\n"
        + latest_snapshot
        + "\n"
        + structure_snapshot
        + "\n"
        + flow_snapshot
        + "\n\n[C. 최근 6개월 핵심 지표 테이프]\n"
        + ("\n".join(indicator_tape) if indicator_tape else "(none)")
        + "\n\n[D. 시장 데이터]\n"
        + market_snapshot
        + "\n\n[E. 차트탭 시그널 이벤트]\n"
        + ("\n".join(signal_lines[-12:]) if signal_lines else "(none)")
    )


def build_ai_prompt(ticker, prompt_tape):
    return f"""
너는 {BRAND_NAME} 내부의 독립 AI 재확인 모델이다.
자연어 필드는 모두 한국어로 작성한다.

절대 규칙:
1. 아래에 제공된 최근 OHLCV, 차트 지표, 가격 구조/레벨, 시장 데이터, 차트탭 시그널 이벤트만 사용한다.
2. 우리 프로그램의 매수/매도 판단, 위원회 판단, 앙상블, veto, objective score, 10개 레이어, 각종 스코어링, action label, audit 문구는 추정하거나 언급하지 않는다.
3. 제공된 시그널 이벤트는 차트에서 관측된 이벤트로만 취급하고, 프로그램의 최종 추천으로 해석하지 않는다.
4. 입력에는 최근 약 6개월(최대 126거래일)의 일봉 및 핵심 지표 이력이 포함되어 있으니, 최근 며칠의 움직임만 보지 말고 중기 추세와 최근 변화의 연결을 함께 본다.
5. 반드시 독립적으로 다시 판단한다.
6. 레이블은 STRONG_BUY, BUY, WATCH_BUY, NEUTRAL, WATCH_SELL, SELL, STRONG_SELL 중 하나만 사용한다.
7. 매매전략은 한 줄 요약뿐 아니라 스타일별 플레이북도 함께 만든다. 플레이북은 초단타, 단타, 스윙, 추세추종, 피보나치 되돌림, 퀀트/시장체크, 관망 중 현재 데이터에 맞는 3~5개를 고른다.
8. 초단타/단타 전략은 분봉이나 체결강도 데이터가 없으므로, 일봉 기준 준비 시나리오와 장중 확인 포인트 수준에서만 적는다. 분봉 확정 표현은 금지한다.
9. 매매전략 필드는 현재 차트 기준의 진입 아이디어, 무효화 기준, 목표 구간을 짧고 실전적으로 적는다. NEUTRAL이면 관망 조건을 적는다.
10. 출력은 JSON만 반환한다. 마크다운, 설명문, 코드펜스는 금지한다.

반환 JSON 스키마:
{{
  "AI_Judgment": "one of the allowed labels",
  "AI_Confidence": 0,
  "AI_Bullish_Score": 0,
  "AI_Bearish_Score": 0,
  "AI_Risk_Flags": ["short Korean phrase"],
  "AI_Key_Drivers": ["short Korean phrase"],
  "AI_Reason": "2-4 Korean sentences explaining the call from the supplied data",
  "AI_Trade_Strategy": "1-3 Korean sentences with the practical trade approach",
  "AI_Entry_Plan": "short Korean phrase for entry or wait condition",
  "AI_Invalidation": "short Korean phrase for stop or invalidation",
  "AI_Target_Plan": "short Korean phrase for target or scale-out plan",
  "AI_Strategy_Playbook": [
    {{
      "style": "초단타 | 단타 | 스윙 | 추세추종 | 피보나치 되돌림 | 퀀트/시장체크 | 관망",
      "fit": 0,
      "summary": "1-2 Korean sentences",
      "entry": "short Korean phrase",
      "invalidation": "short Korean phrase",
      "target": "short Korean phrase"
    }}
  ]
}}

필드 규칙:
- AI_Confidence: 0-100 정수
- AI_Bullish_Score: 0-100 정수
- AI_Bearish_Score: 0-100 정수
- AI_Risk_Flags: 0-4개
- AI_Key_Drivers: 가능하면 2-4개
- AI_Reason: 제공된 데이터만 근거로 2-4문장
- AI_Trade_Strategy: 1-3문장
- AI_Entry_Plan: 1문장 이내
- AI_Invalidation: 1문장 이내
- AI_Target_Plan: 1문장 이내
- AI_Strategy_Playbook: 3-5개
- 각 playbook 항목은 제공 데이터에 기반한 스타일만 사용
- AI_Judgment가 NEUTRAL에 가깝거나 혼조면 관망을 반드시 한 항목 포함

티커:
{ticker}

입력 데이터:
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
            "AI_Trade_Strategy": "",
            "AI_Entry_Plan": "",
            "AI_Invalidation": "",
            "AI_Target_Plan": "",
            "AI_Strategy_Playbook": [],
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
            "AI_Trade_Strategy": "",
            "AI_Entry_Plan": "",
            "AI_Invalidation": "",
            "AI_Target_Plan": "",
            "AI_Strategy_Playbook": [],
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
            "AI_Trade_Strategy": "",
            "AI_Entry_Plan": "",
            "AI_Invalidation": "",
            "AI_Target_Plan": "",
            "AI_Strategy_Playbook": [],
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
        "AI_Reason": _normalize_text(data.get("AI_Reason", ""), default=""),
        "AI_Trade_Strategy": _normalize_text(data.get("AI_Trade_Strategy", ""), default=""),
        "AI_Entry_Plan": _normalize_text(data.get("AI_Entry_Plan", ""), default=""),
        "AI_Invalidation": _normalize_text(data.get("AI_Invalidation", ""), default=""),
        "AI_Target_Plan": _normalize_text(data.get("AI_Target_Plan", ""), default=""),
        "AI_Strategy_Playbook": _normalize_strategy_playbook(data.get("AI_Strategy_Playbook"), limit=5),
        "AI_Agreement": agreement,
        "AI_Disagreement_Type": disagreement_type if disagreement_type in _AI_DISAGREEMENT_TYPES else "MIXED",
        "raw_text": raw,
    }

    if not result["AI_Reason"]:
        result["AI_Reason"] = "AI가 구조화된 판단은 줬지만 사유 설명은 비어 있습니다."
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
            fallback_style = "단타"
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
