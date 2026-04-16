import streamlit as st
import streamlit.components.v1 as components
from collections import Counter
import base64
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai
import html
import json
import re
import yfinance as yf
from datetime import datetime, timedelta
from textwrap import dedent
try:
    import cloudscraper
except Exception:
    cloudscraper = None
try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None
from config import *
from chart import build_metadata, build_chart, load_chart_figure
from company_details import render_company_details
from localization import (
    localize_action_label,
    localize_committee_name,
    localize_context_label,
    localize_judgment_label,
    localize_regime_label,
    translate_chart_text,
)
from etf_sources import resolve_etf_universe
from sectors import SECTOR_GROUPS
from theme import FONT_IMPORT_URL, FONT_STACK

SOFT_GREEN = '#63D9A2'
SOFT_GREEN_TEXT = '#B8F1D5'
SOFT_RED = '#FF8F96'
SOFT_RED_TEXT = '#FFD2D7'
SOFT_AMBER = '#F6C35E'
SOFT_AMBER_TEXT = '#F8DE9A'
SOFT_BLUE = '#A5B4FC'

_US_MARKET_DECK_HEIGHT = 692
_US_MARKET_DEFAULT_DURATION = 7000
_US_MARKET_TEXT_HEAVY_DURATION = 10000
_US_MARKET_DAILY_PAYLOAD_TTL_SEC = 900
_US_MARKET_HISTORY_PERIOD = "6mo"
_US_MARKET_MOVER_HISTORY_PERIOD = "3mo"
_US_MARKET_DOWNLOAD_CHUNK_SIZE = 200
_US_MARKET_TOP_MOVER_CARD_COUNT = 9
_US_MARKET_TOP_MOVER_DETAIL_COUNT = 30
_US_MARKET_ANALYSIS_ACTION_COUNT = 12
_US_MARKET_NEWS_LOOKBACK_HOURS = 36
_US_MARKET_NEWS_MAX_ITEMS = 5
_US_MARKET_NEWS_SECTION_MAX_ITEMS = 3
_US_MARKET_NEWS_PER_TICKER_LIMIT = 8
_US_MARKET_NEWS_AI_ITEMS_PER_SECTION = 3
_US_MARKET_NEWS_ARTICLE_FETCH_LIMIT = 12
_US_MARKET_NEWS_SECTION_SUMMARY_ITEMS = 5
_US_MARKET_NEWS_EXCERPT_MAX_CHARS = 320
_US_MARKET_NEWS_ARTICLE_FETCH_TIMEOUT_SEC = 4
_US_MARKET_NEWS_GOOD_EXCERPT_SCORE = 140
_US_MARKET_NEWS_MEGA_CAP_LIMIT = 8
_US_MARKET_NEWS_GAINER_SYMBOL_LIMIT = 4
_US_MARKET_NEWS_LOSER_SYMBOL_LIMIT = 4
_US_MARKET_NEWS_SECTION_ORDER = [
    "시장 총평",
    "거시·연준",
    "실적·개별주",
    "외부 변수",
    "원자재·암호",
]
_US_MARKET_NEWS_SECTION_IDS = {
    "시장 총평": "market_snapshot",
    "거시·연준": "macro_fed",
    "실적·개별주": "earnings_stocks",
    "외부 변수": "external_risks",
    "원자재·암호": "commodities_crypto",
}
_US_MARKET_BENCHMARKS = [
    ("SPY", "S&P 500"),
    ("QQQ", "나스닥 100"),
    ("DIA", "다우"),
    ("IWM", "러셀 2000"),
    ("^VIX", "변동성"),
]
_US_MARKET_MACRO = [
    ("^TNX", "미 국채 10년"),
    ("DX-Y.NYB", "달러 인덱스"),
    ("KRW=X", "원/달러 환율"),
    ("GLD", "금 ETF"),
    ("CL=F", "WTI"),
    ("BTC-USD", "비트코인"),
]
_US_MARKET_SYSTEMIC_NEWS_SYMBOLS = [
    "SPY", "QQQ", "DIA", "IWM", "^VIX", "^TNX", "DX-Y.NYB", "KRW=X", "GLD", "CL=F", "BTC-USD", "XLE",
]
_MARKET_NEWS_DISPLAY_LABELS = {
    "SPY": "S&P 500",
    "QQQ": "나스닥 100",
    "DIA": "다우",
    "IWM": "러셀 2000",
    "^VIX": "VIX",
    "^TNX": "미 국채 10년",
    "DX-Y.NYB": "달러 인덱스",
    "KRW=X": "원/달러",
    "GLD": "금",
    "CL=F": "WTI",
    "BTC-USD": "비트코인",
    "XLE": "에너지",
}
_MARKET_SYMBOL_NORMALIZATION_MAP = {
    "BRK.B": "BRK-B",
    "BF.B": "BF-B",
}
_MARKET_SYMBOL_FALLBACKS = {
    "DX-Y.NYB": ("DX=F",),
    "KRW=X": ("USDKRW=X",),
}
_MARKET_NEWS_TITLE_TRANSLATIONS = [
    (r"\bafter-hours\b", "시간외"),
    (r"\bpre-market\b", "개장 전"),
    (r"\bpremarket\b", "개장 전"),
    (r"\bfederal reserve\b", "연준"),
    (r"\bfed\b", "연준"),
    (r"\bearnings\b", "실적"),
    (r"\bguidance\b", "가이던스"),
    (r"\boutlook\b", "전망"),
    (r"\brevenue\b", "매출"),
    (r"\bprofit\b", "이익"),
    (r"\bquarterly\b", "분기"),
    (r"\bresults\b", "결과"),
    (r"\bforecasts?\b", "전망"),
    (r"\bforecast\b", "전망"),
    (r"\btariffs?\b", "관세"),
    (r"\bsanctions?\b", "제재"),
    (r"\blawsuit\b", "소송"),
    (r"\bsettlement\b", "합의"),
    (r"\bmerger\b", "합병"),
    (r"\bacquisition\b", "인수"),
    (r"\bpartnership\b", "파트너십"),
    (r"\bagreement\b", "합의"),
    (r"\bdeal\b", "계약"),
    (r"\bbitcoin\b", "비트코인"),
    (r"\bethereum\b", "이더리움"),
    (r"\bcrypto(?:currency)?\b", "가상자산"),
    (r"\bsemiconductor\b", "반도체"),
    (r"\bchipmaker\b", "반도체 기업"),
    (r"\bchips\b", "칩"),
    (r"\bchip\b", "칩"),
    (r"\boil\b", "유가"),
    (r"\bcrude\b", "원유"),
    (r"\bgold\b", "금"),
    (r"\byields?\b", "금리"),
    (r"\brate cuts?\b", "금리 인하"),
    (r"\brate hikes?\b", "금리 인상"),
    (r"\bbeats?\b", "상회"),
    (r"\bmiss(?:es|ed)?\b", "하회"),
    (r"\braises?\b", "상향"),
    (r"\bcuts?\b", "하향"),
    (r"\bsurges?\b", "급등"),
    (r"\bjumps?\b", "급등"),
    (r"\brall(?:y|ies|ied)\b", "강세"),
    (r"\brises?\b", "상승"),
    (r"\bgains?\b", "상승"),
    (r"\bfalls?\b", "하락"),
    (r"\bdrops?\b", "하락"),
    (r"\bslips?\b", "약세"),
    (r"\bsinks?\b", "급락"),
    (r"\bstocks\b", "주식"),
    (r"\bstock\b", "주가"),
    (r"\bshares\b", "주가"),
]
_US_SECTOR_ETFS = [
    ("XLK", "기술"),
    ("XLF", "금융"),
    ("XLE", "에너지"),
    ("XLV", "헬스케어"),
    ("XLI", "산업재"),
    ("XLY", "경기소비재"),
    ("XLP", "필수소비재"),
    ("XLU", "유틸리티"),
    ("XLB", "소재"),
    ("XLC", "커뮤니케이션"),
    ("XLRE", "부동산"),
]
_US_CYCLICAL_SECTOR_SYMBOLS = {"XLK", "XLY", "XLI", "XLB", "XLF", "XLE", "XLC"}
_US_DEFENSIVE_SECTOR_SYMBOLS = {"XLV", "XLP", "XLU", "XLRE"}
_US_MARKET_MEGA_CAPS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "AVGO", "TSLA",
    "AMD", "NFLX", "JPM", "BRK-B", "XOM", "LLY", "UNH", "COST",
]


def _market_badge(label, tone="muted"):
    safe_label = html.escape(str(label or "").strip())
    if not safe_label:
        return ""
    return f"<span class='sigl-badge sigl-badge--{tone}'>{safe_label}</span>"


def _ordered_unique(items):
    seen = set()
    ordered = []
    for item in items:
        key = str(item or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        ordered.append(key)
    return ordered


def _normalize_market_symbol(symbol):
    raw = str(symbol or "").strip().upper()
    return _MARKET_SYMBOL_NORMALIZATION_MAP.get(raw, raw)


def _market_news_display_label(symbol):
    normalized = _normalize_market_symbol(symbol)
    return _MARKET_NEWS_DISPLAY_LABELS.get(normalized, normalized)


def _market_symbol_candidates(symbol):
    raw = _normalize_market_symbol(symbol)
    if not raw:
        return tuple()
    candidates = [raw]
    for fallback in _MARKET_SYMBOL_FALLBACKS.get(raw, ()):
        normalized = _normalize_market_symbol(fallback)
        if normalized and normalized not in candidates:
            candidates.append(normalized)
    return tuple(candidates)


def _format_market_date(dt_value):
    if dt_value is None:
        return "최신 세션"
    if hasattr(dt_value, "to_pydatetime"):
        dt_value = dt_value.to_pydatetime()
    return f"{dt_value:%Y.%m.%d} 미국장 마감"


def _format_change_pct(change_pct):
    if change_pct is None or pd.isna(change_pct):
        return "N/A"
    return f"{change_pct:+.2f}%"


def _safe_market_float(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    try:
        return float(value)
    except Exception:
        return None


def _format_mover_price_summary(snapshot, change_pct=None):
    snapshot = snapshot or {}
    price = _safe_market_float(snapshot.get("price"))
    prev_close = _safe_market_float(snapshot.get("prev_close"))
    pct = _safe_market_float(change_pct if change_pct is not None else snapshot.get("change_pct"))
    delta = (price - prev_close) if (price is not None and prev_close is not None) else None

    price_text = f"${price:,.2f}" if price is not None else "N/A"
    pct_text = _format_change_pct(pct)
    if delta is None:
        return price_text if pct is None else f"{price_text} ({pct_text})"
    return f"{price_text} ({delta:+,.2f}, {pct_text})"


def _tone_from_change(change_pct, inverse=False, neutral_band=0.12):
    if change_pct is None or pd.isna(change_pct):
        return "neutral"
    effective = -change_pct if inverse else change_pct
    if effective > neutral_band:
        return "positive"
    if effective < -neutral_band:
        return "negative"
    return "neutral"


def _resolve_market_tone(*tones):
    normalized = [tone for tone in tones if tone in {"positive", "negative", "neutral"}]
    if not normalized:
        return "neutral"
    positives = sum(1 for tone in normalized if tone == "positive")
    negatives = sum(1 for tone in normalized if tone == "negative")
    if positives > negatives:
        return "positive"
    if negatives > positives:
        return "negative"
    return "neutral"


def _build_market_bullet(text, tone="neutral"):
    safe_text = str(text or "").strip()
    if not safe_text:
        return {"text": "", "tone": "neutral"}
    return {"text": safe_text, "tone": tone if tone in {"positive", "negative", "neutral"} else "neutral"}


def _infer_market_text_tone(text):
    sample = str(text or "").lower()
    if not sample:
        return "neutral"
    positive_keywords = [
        "강세", "완화", "우호", "반등", "회복", "상승", "선방", "주도", "지지", "개선",
        "risk-on", "strength", "eased", "friendlier", "support", "bounce", "led",
    ]
    negative_keywords = [
        "압박", "약세", "위험회피", "부담", "급등", "변동성", "우려", "둔화", "하락", "이탈",
        "차익실현", "risk-off", "lagged", "pressure", "weakness", "hedging", "caution", "pullback",
    ]
    positive_hits = sum(1 for keyword in positive_keywords if keyword in sample)
    negative_hits = sum(1 for keyword in negative_keywords if keyword in sample)
    if positive_hits > negative_hits:
        return "positive"
    if negative_hits > positive_hits:
        return "negative"
    return "neutral"


def _extract_symbol_frame(history, symbol):
    if history is None or getattr(history, "empty", True):
        return pd.DataFrame()
    frame = None
    candidates = _market_symbol_candidates(symbol)
    if isinstance(history.columns, pd.MultiIndex):
        level_zero = list(history.columns.get_level_values(0))
        level_one = list(history.columns.get_level_values(1))
        for candidate in candidates:
            if candidate in level_zero:
                frame = history[candidate].copy()
                break
            if candidate in level_one:
                frame = history.xs(candidate, axis=1, level=1).copy()
                break
    else:
        frame = history.copy()
    if frame is None or frame.empty or "Close" not in frame.columns:
        return pd.DataFrame()
    frame = frame.dropna(how="all")
    frame = frame.dropna(subset=["Close"])
    return frame


def _build_snapshot(frame):
    if frame is None or frame.empty or "Close" not in frame.columns:
        return {}
    close = frame["Close"].dropna()
    if close.empty:
        return {}
    price = float(close.iloc[-1])
    prev_close = float(close.iloc[-2]) if len(close) >= 2 else price
    change_pct = ((price - prev_close) / prev_close * 100.0) if prev_close else None
    five_day_change = ((price - float(close.iloc[-6])) / float(close.iloc[-6]) * 100.0) if len(close) >= 6 and float(close.iloc[-6]) else None
    month_change = ((price - float(close.iloc[-21])) / float(close.iloc[-21]) * 100.0) if len(close) >= 21 and float(close.iloc[-21]) else None
    volume_ratio = None
    if "Volume" in frame.columns:
        volume = frame["Volume"].dropna()
        if not volume.empty:
            base_volume = float(volume.tail(20).mean())
            if base_volume > 0:
                volume_ratio = float(volume.iloc[-1]) / base_volume
    return {
        "price": price,
        "prev_close": prev_close,
        "change_pct": change_pct,
        "five_day_change": five_day_change,
        "month_change": month_change,
        "volume_ratio": volume_ratio,
        "date": close.index[-1],
    }


def _build_snapshot_metric(label, note, snapshot, inverse=False):
    if not snapshot:
        return {"label": label, "value": "N/A", "delta": "", "note": note, "tone": "neutral"}
    price = snapshot.get("price")
    prev_close = snapshot.get("prev_close")
    change_pct = snapshot.get("change_pct")
    tone = _tone_from_change(change_pct, inverse=inverse)
    if label == "10Y":
        value = f"{(price or 0) / 10:.2f}%"
        delta = ""
        if price is not None and prev_close is not None:
            delta = f"{(price - prev_close) * 10:+.1f}bp"
    elif label == "USD/KRW":
        value = f"₩{price:,.1f}" if price is not None else "N/A"
        delta = _format_change_pct(change_pct)
    elif label == "BTC":
        value = f"${price:,.0f}" if price is not None else "N/A"
        delta = _format_change_pct(change_pct)
    elif label in {"WTI", "DXY", "VIX"}:
        value = f"{price:.2f}" if price is not None else "N/A"
        delta = _format_change_pct(change_pct)
    else:
        value = f"{price:.2f}" if price is not None else "N/A"
        delta = _format_change_pct(change_pct)
    return {"label": label, "value": value, "delta": delta, "note": note, "tone": tone}


def _relative_change(lhs_snapshot, rhs_snapshot):
    lhs_change = (lhs_snapshot or {}).get("change_pct")
    rhs_change = (rhs_snapshot or {}).get("change_pct")
    if lhs_change is None or rhs_change is None or pd.isna(lhs_change) or pd.isna(rhs_change):
        return None
    return float(lhs_change) - float(rhs_change)


def _format_pct_point(change_pct):
    if change_pct is None or pd.isna(change_pct):
        return "N/A"
    return f"{change_pct:+.2f}%p"


def _build_relative_strength_metric(label, note, spread):
    if spread is None or pd.isna(spread):
        return {"label": label, "value": "N/A", "delta": "", "note": note, "tone": "neutral"}
    tone = _tone_from_change(spread, neutral_band=0.18)
    delta = "상대 강세" if tone == "positive" else "상대 약세" if tone == "negative" else "중립"
    return {
        "label": label,
        "value": _format_pct_point(spread),
        "delta": delta,
        "note": note,
        "tone": tone,
    }


def _build_market_regime(benchmarks, macro, sector_rows):
    qqq_vs_spy = _relative_change(benchmarks.get("QQQ", {}), benchmarks.get("SPY", {}))
    iwm_vs_spy = _relative_change(benchmarks.get("IWM", {}), benchmarks.get("SPY", {}))
    vix_snapshot = benchmarks.get("VIX", {})
    vix_level = vix_snapshot.get("price")
    vix_change = vix_snapshot.get("change_pct")
    tnx_snapshot = macro.get("10Y", {})
    tnx_bps = ((tnx_snapshot.get("price") or 0) - (tnx_snapshot.get("prev_close") or 0)) * 10 if tnx_snapshot else None
    dxy_change = macro.get("DXY", {}).get("change_pct")
    fx_change = macro.get("USDKRW", {}).get("change_pct")
    wti_change = macro.get("WTI", {}).get("change_pct")
    btc_change = macro.get("BTC", {}).get("change_pct")
    gold_change = macro.get("Gold", {}).get("change_pct")
    sector_up = sum(1 for row in sector_rows if (row.get("change_pct") or 0) > 0)
    sector_total = len(sector_rows) or 11

    score = 0
    breadth_ratio = sector_up / sector_total if sector_total else 0.5
    if sector_total:
        if breadth_ratio >= 0.64:
            score += 2
        elif breadth_ratio <= 0.36:
            score -= 2

    if qqq_vs_spy is not None:
        if qqq_vs_spy >= 0.30:
            score += 1
        elif qqq_vs_spy <= -0.30:
            score -= 1

    if iwm_vs_spy is not None:
        if iwm_vs_spy >= 0.30:
            score += 2
        elif iwm_vs_spy <= -0.30:
            score -= 2

    if vix_change is not None:
        if vix_change <= -4:
            score += 2
        elif vix_change >= 5:
            score -= 2

    if vix_level is not None:
        if vix_level <= 18:
            score += 1
        elif vix_level >= 25:
            score -= 1

    if dxy_change is not None:
        if dxy_change <= -0.35:
            score += 1
        elif dxy_change >= 0.35:
            score -= 1

    if fx_change is not None:
        if fx_change <= -0.35:
            score += 1
        elif fx_change >= 0.35:
            score -= 1

    if wti_change is not None:
        if wti_change >= 1.5:
            score += 1
        elif wti_change <= -1.5:
            score -= 1

    if btc_change is not None:
        if btc_change >= 2.0:
            score += 1
        elif btc_change <= -2.0:
            score -= 1

    if gold_change is not None:
        if gold_change >= 0.8:
            score -= 1
        elif gold_change <= -0.8:
            score += 1

    # Falling yields can mean either risk support or a flight to safety, so we
    # only score them once other assets show the context around that move.
    if tnx_bps is not None:
        safety_context = ((vix_change or 0) >= 3) or ((dxy_change or 0) >= 0.25) or ((gold_change or 0) >= 0.6)
        reflation_context = breadth_ratio >= 0.58 or ((wti_change or 0) >= 1.2) or ((qqq_vs_spy or 0) >= 0.2)
        if tnx_bps <= -4 and safety_context:
            score -= 1
        elif tnx_bps >= 4 and reflation_context:
            score += 1

    clamped = max(-10, min(10, score))
    fear_greed_score = round((clamped + 10) / 20 * 100)
    if clamped >= 4:
        state = "RISK-ON"
        state_note = "위험 선호"
        tone = "positive"
    elif clamped <= -4:
        state = "RISK-OFF"
        state_note = "위험 회피"
        tone = "negative"
    else:
        state = "MIXED"
        state_note = "혼조"
        tone = "neutral"

    if fear_greed_score >= 65:
        fear_greed_label = "탐욕"
        fear_greed_tone = "positive"
    elif fear_greed_score <= 35:
        fear_greed_label = "공포"
        fear_greed_tone = "negative"
    else:
        fear_greed_label = "중립"
        fear_greed_tone = "neutral"
    state_display = f"{state_note} ({state})"

    return {
        "state": state,
        "state_note": state_note,
        "state_display": state_display,
        "tone": tone,
        "score": clamped,
        "fear_greed_score": fear_greed_score,
        "fear_greed_label": fear_greed_label,
        "fear_greed_tone": fear_greed_tone,
        "qqq_vs_spy": qqq_vs_spy,
        "iwm_vs_spy": iwm_vs_spy,
        "sector_up": sector_up,
        "sector_total": sector_total,
    }


def _build_risk_state_metric(regime):
    regime = regime or {}
    return {
        "label": "리스크",
        "value": regime.get("state_note", "혼조"),
        "delta": regime.get("state", "MIXED"),
        "note": "위험 선호/회피",
        "tone": regime.get("tone", "neutral"),
    }


def _build_fear_greed_proxy_metric(regime):
    regime = regime or {}
    return {
        "label": "심리",
        "value": f"{int(regime.get('fear_greed_score', 50))}/100",
        "delta": regime.get("fear_greed_label", "중립"),
        "note": "공포·탐욕 프록시",
        "tone": regime.get("fear_greed_tone", "neutral"),
    }


def _describe_market_structure(benchmarks, macro, sector_rows):
    qqq_vs_spy = _relative_change(benchmarks.get("QQQ", {}), benchmarks.get("SPY", {}))
    iwm_vs_spy = _relative_change(benchmarks.get("IWM", {}), benchmarks.get("SPY", {}))
    vix_change = benchmarks.get("VIX", {}).get("change_pct")
    dxy_change = macro.get("DXY", {}).get("change_pct")
    gold_change = macro.get("Gold", {}).get("change_pct")
    tnx_snapshot = macro.get("10Y", {})
    tnx_bps = ((tnx_snapshot.get("price") or 0) - (tnx_snapshot.get("prev_close") or 0)) * 10 if tnx_snapshot else None
    sector_up = sum(1 for row in sector_rows if (row.get("change_pct") or 0) > 0)
    sector_total = len(sector_rows) or 11
    breadth_ratio = sector_up / sector_total if sector_total else 0.5
    strongest_sector = max(sector_rows, key=lambda row: row.get("change_pct") if row.get("change_pct") is not None else -999) if sector_rows else None
    weakest_sector = min(sector_rows, key=lambda row: row.get("change_pct") if row.get("change_pct") is not None else 999) if sector_rows else None

    if qqq_vs_spy is not None and qqq_vs_spy >= 0.45 and breadth_ratio <= 0.4:
        return {"label": "메가캡 쏠림", "note": "지수보다 일부 리더 종목 중심", "tone": "neutral"}
    if iwm_vs_spy is not None and iwm_vs_spy >= 0.45 and breadth_ratio >= 0.6:
        return {"label": "광범위 반등", "note": "소형주와 섹터 확산 동반", "tone": "positive"}
    if gold_change is not None and gold_change >= 0.8 and (((vix_change or 0) >= 3) or ((dxy_change or 0) >= 0.25)):
        return {"label": "방어형", "note": "안전자산 선호 우위", "tone": "negative"}
    if tnx_bps is not None and tnx_bps >= 4 and weakest_sector and weakest_sector.get("symbol") == "XLK":
        return {"label": "금리부담형", "note": "기술주 duration 압박", "tone": "negative"}
    if strongest_sector and strongest_sector.get("symbol") in {"XLU", "XLP", "XLV"} and breadth_ratio <= 0.5:
        return {"label": "방어주 주도", "note": "안정성 선호 우위", "tone": "negative"}
    if breadth_ratio <= 0.36:
        return {"label": "확산 약세", "note": "하락 종목 우위", "tone": "negative"}
    if breadth_ratio >= 0.64:
        return {"label": "광범위 매수", "note": "대부분 섹터 동반 상승", "tone": "positive"}
    return {"label": "혼조형", "note": "섹터 간 온도 차 확대", "tone": "neutral"}


def _build_sector_sentence(sector_rows):
    if not sector_rows:
        return "섹터 데이터가 아직 동기화 중입니다."
    positive = sum(1 for row in sector_rows if (row.get("change_pct") or 0) > 0)
    total = len(sector_rows)
    strongest = max(sector_rows, key=lambda row: row.get("change_pct") if row.get("change_pct") is not None else -999)
    weakest = min(sector_rows, key=lambda row: row.get("change_pct") if row.get("change_pct") is not None else 999)
    strongest_change = strongest.get("change_pct")
    weakest_change = weakest.get("change_pct")
    breadth_note = "광범위한 상승" if positive >= max(7, total - 3) else "하락 우위" if positive <= max(3, total // 3) else "선별 장세"
    return (
        f"{total}개 섹터 중 {positive}개가 상승한 {breadth_note}였습니다. "
        f"{strongest['label']} {_format_change_pct(strongest_change)}가 주도했고 {weakest['label']} {_format_change_pct(weakest_change)}가 가장 부진했습니다."
    )


def _build_driver_candidates(benchmarks, macro, sector_rows):
    drivers = []
    def add_driver(text):
        if text and text not in drivers:
            drivers.append(text)

    spy = benchmarks.get("SPY", {})
    qqq = benchmarks.get("QQQ", {})
    iwm = benchmarks.get("IWM", {})
    vix = benchmarks.get("VIX", {})
    tnx = macro.get("10Y", {})
    dxy = macro.get("DXY", {})
    fx = macro.get("USDKRW", {})
    gold = macro.get("Gold", {})
    wti = macro.get("WTI", {})
    btc = macro.get("BTC", {})
    sector_breadth = sum(1 for row in sector_rows if (row.get("change_pct") or 0) > 0)
    sector_count = len(sector_rows)
    sector_total = sector_count or 11
    breadth_ratio = sector_breadth / sector_count if sector_count else 0.5
    qqq_vs_spy = _relative_change(qqq, spy)
    iwm_vs_spy = _relative_change(iwm, spy)
    strongest_sector = max(sector_rows, key=lambda row: row.get("change_pct") if row.get("change_pct") is not None else -999) if sector_rows else None
    weakest_sector = min(sector_rows, key=lambda row: row.get("change_pct") if row.get("change_pct") is not None else 999) if sector_rows else None

    spy_chg = spy.get("change_pct")
    qqq_chg = qqq.get("change_pct")
    iwm_chg = iwm.get("change_pct")
    vix_chg = vix.get("change_pct")
    tnx_bps = ((tnx.get("price") or 0) - (tnx.get("prev_close") or 0)) * 10 if tnx else None
    dxy_chg = dxy.get("change_pct")
    fx_chg = fx.get("change_pct")
    gold_chg = gold.get("change_pct")
    wti_chg = wti.get("change_pct")
    btc_chg = btc.get("change_pct")

    if vix_chg is not None and gold_chg is not None and tnx_bps is not None:
        if vix_chg >= 5 and gold_chg >= 0.8 and tnx_bps <= -4:
            add_driver("VIX 급등과 금 강세, 장기금리 하락이 겹치며 전형적인 위험회피 흐름이 나타났습니다.")

    if iwm_vs_spy is not None and vix_chg is not None and sector_count:
        if iwm_vs_spy >= 0.5 and breadth_ratio >= 0.6 and vix_chg <= -4:
            add_driver("소형주와 섹터 확산도가 함께 개선되고 VIX도 낮아지며 더 넓은 위험선호 흐름이 나타났습니다.")

    if qqq_vs_spy is not None and sector_count:
        if qqq_vs_spy >= 0.45 and breadth_ratio <= 0.4:
            add_driver("대형 기술주만 상대적으로 강해 시장 전반보다 메가캡 쏠림 성격이 두드러졌습니다.")

    if wti_chg is not None and tnx_bps is not None and qqq_vs_spy is not None:
        if wti_chg >= 1.8 and tnx_bps >= 4 and qqq_vs_spy <= -0.2:
            add_driver("유가와 금리가 함께 오르며 인플레이션 및 밸류에이션 부담이 성장주를 눌렀습니다.")

    if dxy_chg is not None and gold_chg is not None:
        if dxy_chg >= 0.35 and gold_chg >= 0.8:
            add_driver("달러와 금이 함께 강세를 보이며 안전자산 선호가 뚜렷했습니다.")

    if dxy_chg is not None and btc_chg is not None:
        if dxy_chg >= 0.35 and btc_chg <= -2.5:
            add_driver("달러 강세와 비트코인 약세가 겹치며 투기적 위험선호 심리가 빠르게 식었습니다.")

    if strongest_sector:
        if strongest_sector.get("symbol") in {"XLU", "XLP", "XLV"} and breadth_ratio <= 0.5:
            add_driver("방어 섹터가 상단을 차지하며 투자자들이 공격적 베팅보다 안정성을 우선했습니다.")
        elif strongest_sector.get("symbol") in {"XLI", "XLY", "XLB", "XLE"} and (iwm_vs_spy or -999) >= 0.3:
            add_driver("경기민감 섹터와 소형주가 함께 버티며 경기 기대가 일부 살아났습니다.")

    if qqq_chg is not None and spy_chg is not None:
        if qqq_chg < spy_chg - 0.45:
            add_driver("나스닥이 대형주 전체보다 더 약해 성장주 압박이 크게 나타났습니다.")
        elif qqq_chg > spy_chg + 0.45:
            add_driver("대형 기술주가 상대 강세를 보이며 시장 주도권을 일부 되찾았습니다.")

    if iwm_chg is not None and spy_chg is not None:
        if iwm_chg > spy_chg + 0.5:
            add_driver("소형주가 선방해 위험선호가 완전히 꺾이진 않았습니다.")
        elif iwm_chg < spy_chg - 0.5:
            add_driver("소형주 약세가 더 깊어지며 시장 전반의 위험회피 성격이 강해졌습니다.")

    if vix_chg is not None:
        if vix_chg >= 5:
            add_driver("VIX 급등은 헤지 수요 확대와 변동성 경계 심리 강화를 보여줬습니다.")
        elif vix_chg <= -4:
            add_driver("VIX가 빠르게 낮아지며 위험 프리미엄이 다소 완화됐습니다.")

    if tnx_bps is not None:
        if tnx_bps >= 4:
            if weakest_sector and weakest_sector.get("symbol") == "XLK":
                add_driver("장기금리 상승과 함께 기술주가 약세 선두에 서며 duration 부담이 부각됐습니다.")
            else:
                add_driver("10년물 금리 상승이 밸류에이션 부담을 키워 성장주에 불리하게 작용했습니다.")
        elif tnx_bps <= -4:
            if ((vix_chg or 0) >= 3) or ((dxy_chg or 0) >= 0.25) or ((gold_chg or 0) >= 0.6):
                add_driver("장기금리 하락은 안전자산 선호 강화와 함께 나타나며 위험회피 흐름을 뒷받침했습니다.")
            else:
                add_driver("장기금리 하락이 성장주에 우호적인 배경을 만들었습니다.")

    if dxy_chg is not None:
        if dxy_chg >= 0.35:
            add_driver("달러 강세가 위험자산 전반에 부담으로 작용했습니다.")
        elif dxy_chg <= -0.35:
            add_driver("달러 압력이 완화되며 위험자산이 숨을 돌렸습니다.")

    if fx_chg is not None:
        if fx_chg >= 0.45:
            add_driver("원/달러 환율 상승은 대외 불안과 달러 선호 심리를 반영했습니다.")
        elif fx_chg <= -0.45:
            add_driver("원/달러 환율 안정은 위험심리 완화에 우호적으로 작용했습니다.")

    if gold_chg is not None:
        if gold_chg >= 0.9:
            add_driver("금 강세는 방어 자산 선호가 남아 있음을 보여줬습니다.")
        elif gold_chg <= -0.9:
            add_driver("금 약세는 방어 수요가 일부 완화됐음을 시사했습니다.")

    if wti_chg is not None and abs(wti_chg) >= 1.8:
        if wti_chg > 0:
            add_driver("유가 강세가 인플레이션 우려를 다시 자극했습니다.")
        else:
            add_driver("유가 약세가 물가 부담 완화 기대를 키웠습니다.")

    if btc_chg is not None and abs(btc_chg) >= 2.5:
        if btc_chg > 0:
            add_driver("비트코인 강세는 투기적 위험선호가 완전히 꺾이지 않았음을 시사했습니다.")
        else:
            add_driver("비트코인 약세는 고베타 자산 전반의 심리 둔화와 맞물렸습니다.")

    if sector_rows:
        if sector_breadth <= 3:
            add_driver(f"상승 섹터가 {sector_breadth}/{sector_total}개에 그쳐 시장 확산도가 약했습니다.")
        elif sector_breadth >= len(sector_rows) - 2:
            add_driver(f"{sector_breadth}/{sector_total}개 섹터가 동반 상승해 광범위한 매수 흐름이 나타났습니다.")

    return drivers[:6]


def _fallback_market_headline(benchmarks, macro, sector_rows):
    spy = benchmarks.get("SPY", {}).get("change_pct")
    qqq = benchmarks.get("QQQ", {}).get("change_pct")
    dia = benchmarks.get("DIA", {}).get("change_pct")
    iwm = benchmarks.get("IWM", {}).get("change_pct")
    vix = benchmarks.get("VIX", {}).get("change_pct")
    qqq_vs_spy = _relative_change(benchmarks.get("QQQ", {}), benchmarks.get("SPY", {}))
    iwm_vs_spy = _relative_change(benchmarks.get("IWM", {}), benchmarks.get("SPY", {}))
    gold_chg = macro.get("Gold", {}).get("change_pct")
    tnx_snapshot = macro.get("10Y", {})
    tnx_bps = ((tnx_snapshot.get("price") or 0) - (tnx_snapshot.get("prev_close") or 0)) * 10 if tnx_snapshot else None
    breadth = sum(1 for row in sector_rows if (row.get("change_pct") or 0) > 0)
    total = len(sector_rows) or 11
    weakest_sector = min(sector_rows, key=lambda row: row.get("change_pct") if row.get("change_pct") is not None else 999) if sector_rows else None
    if spy is None:
        return "미국장 데이터가 아직 로딩 중입니다."
    values = [value for value in [spy, qqq, dia, iwm] if value is not None]
    avg = sum(values) / max(1, len(values))
    if gold_chg is not None and gold_chg >= 0.8 and (vix or 0) >= 3 and breadth <= max(3, total // 3):
        return "안전자산 선호가 강화되며 방어 심리가 짙어진 장이었습니다."
    if iwm_vs_spy is not None and iwm_vs_spy >= 0.45 and breadth >= max(7, int(total * 0.6)):
        return "소형주와 섹터 확산이 동반된 건강한 반등 장이었습니다."
    if qqq_vs_spy is not None and qqq_vs_spy >= 0.45 and breadth <= max(4, total // 3):
        return "지수는 버텼지만 메가캡 중심 쏠림이 강한 장이었습니다."
    if tnx_bps is not None and tnx_bps >= 4 and weakest_sector and weakest_sector.get("symbol") == "XLK":
        return "인플레이션과 금리 부담이 기술주를 눌렀던 장이었습니다."
    if avg <= -0.8 and (vix or 0) > 3:
        return "변동성 확대와 함께 위험회피가 지배한 장이었습니다."
    if avg >= 0.8 and breadth >= max(7, total - 3):
        return "지수와 섹터가 함께 오른 광범위한 위험선호 장이었습니다."
    if qqq is not None and spy is not None and qqq < spy - 0.5:
        return "기술주가 시장보다 약해 성장주 압박이 두드러졌습니다."
    if qqq is not None and spy is not None and qqq > spy + 0.5:
        return "대형 기술주가 반등을 주도하며 시장 리더십을 회복했습니다."
    if breadth <= 3:
        return "하락 우위 흐름 속에 방어적 색채가 짙었습니다."
    return "방향성은 있었지만 섹터 간 온도 차가 큰 장이었습니다."


def _coerce_market_text_list(value, max_items=None):
    if isinstance(value, (list, tuple, set)):
        items = [str(item or "").strip() for item in value if str(item or "").strip()]
    else:
        text = str(value or "").strip()
        items = [text] if text else []
    items = _ordered_unique(items)
    return items[:max_items] if max_items is not None else items


def _join_market_phrases(parts):
    values = [str(part or "").strip() for part in parts if str(part or "").strip()]
    if not values:
        return ""
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return f"{values[0]}와 {values[1]}"
    return ", ".join(values[:-1]) + f"와 {values[-1]}"


def _normalize_market_action_text(text):
    sample = str(text or "").strip()
    if not sample:
        return ""
    sample = re.sub(r"\s+", " ", sample)
    return sample.rstrip(". ")


def _build_actionable_insight_subtitle(short_view, watchlist):
    base = _normalize_market_action_text(short_view)
    checks = _coerce_market_text_list(watchlist, max_items=1)
    if checks:
        follow = _normalize_market_action_text(checks[0])
        if base:
            return f"{base} · 오늘 행동: {follow}"
        return f"오늘 행동: {follow}"
    if base:
        return f"{base} · 오늘 행동: 개장 30분 내 리더십과 금리·달러 반응을 먼저 확인"
    return "오늘 행동: 개장 30분 내 리더십과 금리·달러 반응을 먼저 확인"


def _build_market_insight_news_context(news_bundle):
    ranked_items = list((news_bundle or {}).get("ranked_items") or (news_bundle or {}).get("items") or [])
    high_signal_items = [
        item for item in ranked_items
        if not _is_low_signal_market_news_item(item) and str(item.get("event_type") or "").strip() != "market_update"
    ]
    lead_items = list((high_signal_items or ranked_items)[:_US_MARKET_NEWS_SECTION_SUMMARY_ITEMS])
    if not lead_items:
        return {
            "focus": "",
            "lead_sections": [],
            "lead_events": [],
            "lead_issues": [],
            "section_notes": {},
            "high_signal_count": 0,
        }

    section_counts = Counter(str(item.get("section") or "").strip() for item in lead_items if str(item.get("section") or "").strip())
    event_counts = Counter(str(item.get("event_type") or "").strip() for item in lead_items if str(item.get("event_type") or "").strip())
    lead_sections = [section for section, _ in section_counts.most_common(2) if section]
    lead_events = [
        _market_news_event_label_ko(event_type)
        for event_type, _ in event_counts.most_common(3)
        if event_type
    ]
    lead_issues = _ordered_unique(
        _build_market_news_issue_phrase_ko(item)
        for item in lead_items
        if _build_market_news_issue_phrase_ko(item)
    )[:3]

    macro_weight = sum(section_counts.get(section, 0) for section in {"거시·연준", "외부 변수", "원자재·암호"})
    stock_weight = section_counts.get("실적·개별주", 0)
    event_text = _join_market_phrases(lead_events[:2])
    if macro_weight >= max(2, stock_weight + 1):
        focus = f"시장은 개별 종목보다 {event_text or '거시·외부 변수'}에 더 예민했습니다."
    elif stock_weight >= max(2, macro_weight + 1):
        focus = f"시장은 거시보다 {event_text or '실적과 리더 종목 재료'}에 더 민감하게 반응했습니다."
    elif section_counts.get("시장 총평", 0) >= max(2, macro_weight, stock_weight):
        focus = "시장은 지수 방향 자체보다 내부 확산과 리더십 변화에 더 주목했습니다."
    else:
        focus = f"시장은 한 가지 뉴스보다 {event_text or '복합 재료'} 조합을 함께 해석하는 흐름이었습니다."

    section_notes = {}
    for section_label in _US_MARKET_NEWS_SECTION_ORDER:
        section_items = [item for item in lead_items if item.get("section") == section_label][:3]
        if not section_items:
            continue
        issue_text = _build_market_news_section_issue_text(section_items, limit=2)
        if issue_text:
            section_notes[section_label] = issue_text

    return {
        "focus": focus,
        "lead_sections": lead_sections,
        "lead_events": lead_events[:3],
        "lead_issues": lead_issues,
        "section_notes": section_notes,
        "high_signal_count": len(high_signal_items),
    }


def _build_market_divergence_notes(benchmarks, macro, sector_rows, market_regime, market_structure):
    spy = benchmarks.get("SPY", {}).get("change_pct")
    qqq_vs_spy = market_regime.get("qqq_vs_spy")
    iwm_vs_spy = market_regime.get("iwm_vs_spy")
    vix_chg = benchmarks.get("VIX", {}).get("change_pct")
    tnx_snapshot = macro.get("10Y", {})
    tnx_bps = ((tnx_snapshot.get("price") or 0) - (tnx_snapshot.get("prev_close") or 0)) * 10 if tnx_snapshot else None
    dxy_chg = macro.get("DXY", {}).get("change_pct")
    gold_chg = macro.get("Gold", {}).get("change_pct")
    btc_chg = macro.get("BTC", {}).get("change_pct")
    sector_up = sum(1 for row in sector_rows if (row.get("change_pct") or 0) > 0)
    sector_total = len(sector_rows) or len(_US_SECTOR_ETFS)
    breadth_ratio = sector_up / sector_total if sector_total else 0.5
    strongest_sector = max(sector_rows, key=lambda row: row.get("change_pct") if row.get("change_pct") is not None else -999) if sector_rows else None

    notes = []
    if spy is not None and spy > 0 and breadth_ratio <= 0.45:
        notes.append(f"지수는 {_format_change_pct(spy)} 올랐지만 상승 섹터가 {sector_up}/{sector_total}에 그쳐 체감 강도는 표면 수익률보다 약했습니다.")
    elif spy is not None and spy < 0 and breadth_ratio >= 0.55:
        notes.append(f"S&P 500은 {_format_change_pct(spy)} 밀렸지만 상승 섹터가 {sector_up}/{sector_total}로 버텨 지수보다 내부 체력은 덜 훼손됐습니다.")

    if qqq_vs_spy is not None and qqq_vs_spy >= 0.45 and breadth_ratio <= 0.45:
        notes.append(f"QQQ가 SPY를 {_format_pct_point(qqq_vs_spy)} 앞섰지만 확산은 좁아 메가캡 의존 성격이 강했습니다.")
    elif iwm_vs_spy is not None and iwm_vs_spy >= 0.35 and breadth_ratio >= 0.55:
        notes.append(f"IWM이 SPY를 {_format_pct_point(iwm_vs_spy)} 앞서며 반등이 메가캡 밖으로 번지는지 확인할 만한 장이었습니다.")

    if tnx_bps is not None and tnx_bps >= 4 and qqq_vs_spy is not None and qqq_vs_spy >= 0.2:
        notes.append(f"10년물 금리가 {tnx_bps:+.1f}bp 오른 날에도 나스닥이 상대 강세를 보여 금리보다 빅테크 선호가 우세했습니다.")
    elif tnx_bps is not None and tnx_bps <= -4 and (((gold_chg or 0) >= 0.8) or ((vix_chg or 0) >= 3)):
        notes.append("금리 하락이 곧바로 위험선호로 이어지기보다 금·VIX 흐름을 동반한 방어적 해석에 가까웠습니다.")

    if (dxy_chg or 0) >= 0.35 and (btc_chg or 0) <= -2.0:
        notes.append("달러 강세와 비트코인 약세가 함께 나타나며 위험자산 심리 회복은 제한적이었습니다.")

    if strongest_sector and strongest_sector.get("symbol") in {"XLU", "XLP", "XLV"} and breadth_ratio <= 0.5:
        notes.append(f"{strongest_sector['label']}가 가장 강했고 상승 섹터도 제한돼 표면 지수보다 방어주 선호가 숨어 있었습니다.")

    if not notes:
        notes.append(f"시장은 {market_structure.get('label', '혼조형')} 흐름이었고 리스크 상태는 {market_regime.get('state_display', '혼조')} 수준이었습니다.")
    return _ordered_unique(notes)[:3]


def _classify_market_leadership_state(qqq_vs_spy, iwm_vs_spy, breadth_ratio):
    if qqq_vs_spy is not None and qqq_vs_spy >= 0.60 and breadth_ratio <= 0.36:
        return "mega_cap_extreme"
    if qqq_vs_spy is not None and qqq_vs_spy >= 0.45 and breadth_ratio <= 0.45:
        return "mega_cap_narrow"
    if iwm_vs_spy is not None and iwm_vs_spy >= 0.45 and breadth_ratio >= 0.64:
        return "small_cap_broad"
    if iwm_vs_spy is not None and iwm_vs_spy >= 0.30 and breadth_ratio >= 0.55:
        return "small_cap_rotation"
    if breadth_ratio >= 0.64:
        return "broad_risk_on"
    if breadth_ratio <= 0.36:
        return "broad_risk_off"
    return "mixed"


def _classify_market_rates_state(tnx_bps, qqq_vs_spy, iwm_vs_spy, gold_chg, vix_chg, breadth_ratio):
    if tnx_bps is None:
        return "rates_unknown"
    if tnx_bps >= 6 and qqq_vs_spy is not None and qqq_vs_spy >= 0.20:
        return "rates_up_tech_resilient"
    if tnx_bps >= 6 and iwm_vs_spy is not None and iwm_vs_spy >= 0.20 and breadth_ratio >= 0.55:
        return "rates_up_reflation"
    if tnx_bps >= 4:
        return "rates_up_growth_pressure"
    if tnx_bps <= -6 and (((gold_chg or 0) >= 0.8) or ((vix_chg or 0) >= 3)):
        return "rates_down_safety"
    if tnx_bps <= -4 and breadth_ratio >= 0.55 and (vix_chg or 0) <= 1:
        return "rates_down_risk_support"
    if tnx_bps <= -4:
        return "rates_down_mixed"
    return "rates_stable"


def _classify_market_overlay_state(dxy_chg, btc_chg, gold_chg, vix_chg, wti_chg, breadth_ratio):
    if (dxy_chg or 0) >= 0.35 and (btc_chg or 0) <= -2.0 and ((((gold_chg or 0) >= 0.6)) or (((vix_chg or 0) >= 2))):
        return "dollar_defensive"
    if (dxy_chg or 0) <= -0.35 and (btc_chg or 0) >= 2.0 and breadth_ratio >= 0.55:
        return "dollar_risk_on"
    if (gold_chg or 0) >= 0.8 and (vix_chg or 0) >= 3:
        return "safe_haven_bid"
    if (wti_chg or 0) >= 2.0 and breadth_ratio <= 0.50:
        return "oil_shock"
    if (wti_chg or 0) <= -2.0 and breadth_ratio >= 0.55:
        return "oil_relief"
    return "overlay_none"


def _classify_market_sector_state(sector_rows, breadth_ratio):
    strongest_sector = max(sector_rows, key=lambda row: row.get("change_pct") if row.get("change_pct") is not None else -999) if sector_rows else None
    if not strongest_sector:
        return {"state": "sector_mixed", "symbol": "", "label": ""}
    symbol = str(strongest_sector.get("symbol") or "").strip().upper()
    label = str(strongest_sector.get("label") or symbol or "섹터").strip() or "섹터"
    if symbol in _US_DEFENSIVE_SECTOR_SYMBOLS and breadth_ratio <= 0.50:
        return {"state": "defensive_led", "symbol": symbol, "label": label}
    if symbol == "XLE" and breadth_ratio <= 0.55:
        return {"state": "energy_led", "symbol": symbol, "label": label}
    if symbol == "XLK" and breadth_ratio <= 0.50:
        return {"state": "tech_led_narrow", "symbol": symbol, "label": label}
    if symbol in _US_CYCLICAL_SECTOR_SYMBOLS and breadth_ratio >= 0.55:
        return {"state": "cyclical_led", "symbol": symbol, "label": label}
    if symbol == "XLK":
        return {"state": "tech_led", "symbol": symbol, "label": label}
    return {"state": "sector_mixed", "symbol": symbol, "label": label}


def _build_market_strategy_points(benchmarks, macro, sector_rows, market_regime, news_context=None):
    qqq_vs_spy = market_regime.get("qqq_vs_spy")
    iwm_vs_spy = market_regime.get("iwm_vs_spy")
    tnx_snapshot = macro.get("10Y", {})
    tnx_bps = ((tnx_snapshot.get("price") or 0) - (tnx_snapshot.get("prev_close") or 0)) * 10 if tnx_snapshot else None
    dxy_chg = macro.get("DXY", {}).get("change_pct")
    gold_chg = macro.get("Gold", {}).get("change_pct")
    wti_chg = macro.get("WTI", {}).get("change_pct")
    btc_chg = macro.get("BTC", {}).get("change_pct")
    vix_chg = benchmarks.get("VIX", {}).get("change_pct")
    sector_up = sum(1 for row in sector_rows if (row.get("change_pct") or 0) > 0)
    sector_total = len(sector_rows) or len(_US_SECTOR_ETFS)
    breadth_ratio = sector_up / sector_total if sector_total else 0.5
    leadership_state = _classify_market_leadership_state(qqq_vs_spy, iwm_vs_spy, breadth_ratio)
    rates_state = _classify_market_rates_state(tnx_bps, qqq_vs_spy, iwm_vs_spy, gold_chg, vix_chg, breadth_ratio)
    overlay_state = _classify_market_overlay_state(dxy_chg, btc_chg, gold_chg, vix_chg, wti_chg, breadth_ratio)
    sector_state = _classify_market_sector_state(sector_rows, breadth_ratio)
    lead_sections = set(_coerce_market_text_list((news_context or {}).get("lead_sections")))
    lead_events = set(_coerce_market_text_list((news_context or {}).get("lead_events")))

    ranked_points = []

    def add_point(text, priority):
        safe_text = str(text or "").strip()
        if safe_text:
            ranked_points.append((int(priority), safe_text))

    if leadership_state == "mega_cap_extreme":
        add_point("메가캡 쏠림이 극단적인 구간이라 지수 추격보다 리더 종목과 핵심 반도체 주도주 선별이 더 유리합니다.", 100)
    elif leadership_state == "mega_cap_narrow":
        if rates_state == "rates_up_tech_resilient":
            add_point("금리 재상승에도 빅테크가 버티는 장이라 지수보다 리더 종목 강도 유지 여부를 먼저 확인하는 대응이 좋습니다.", 96)
        elif sector_state.get("state") in {"tech_led", "tech_led_narrow"}:
            add_point("기술주 중심 쏠림이 강한 장이라 섹터 확산 전까지는 지수 추격보다 리더 종목 선별이 유리합니다.", 94)
        else:
            add_point("메가캡 강세가 시장 전반 확산으로 번지기 전까지는 지수 추격보다 리더 종목 선별이 유리합니다.", 92)
    elif leadership_state == "small_cap_broad":
        add_point("소형주와 광범위 확산이 동반된 장이라 메가캡 한정 대응보다 순환매 수혜 업종을 넓게 보는 편이 좋습니다.", 94)
    elif leadership_state == "small_cap_rotation":
        add_point("소형주 상대 강세가 이어지면 대형 기술주 집중보다 경기민감 업종과 중소형주 확산을 함께 보는 대응이 유효합니다.", 90)
    elif leadership_state == "broad_risk_on":
        add_point("섹터 확산이 넓은 장이라 지수 추격보다 강세가 이어지는 업종군을 넓게 가져가는 접근이 더 자연스럽습니다.", 82)
    elif leadership_state == "broad_risk_off":
        add_point("하락 확산이 넓은 구간에서는 신규 베타 확대보다 반등 강도가 확인된 업종만 선별하는 편이 안전합니다.", 82)

    if rates_state == "rates_up_tech_resilient":
        add_point("10년물 금리 상승에도 빅테크가 버티면 추세 지속 신호가 될 수 있어 나스닥 리더십 유지 여부를 먼저 확인해야 합니다.", 88)
    elif rates_state == "rates_up_reflation":
        add_point("금리 상승이 경기민감 강세와 동행하면 성장주 방어보다 금융·산업재·에너지 순환매 지속 여부를 먼저 보는 편이 좋습니다.", 86)
    elif rates_state == "rates_up_growth_pressure":
        add_point("10년물 금리 반등이 이어지면 성장주와 장기 듀레이션 자산의 민감도를 먼저 점검해야 합니다.", 84)
    elif rates_state == "rates_down_safety":
        add_point("금리 하락을 곧바로 호재로 보기보다 금·VIX가 함께 식는지 확인한 뒤 베타를 늘리는 편이 안전합니다.", 84)
    elif rates_state == "rates_down_risk_support":
        add_point("금리 하락이 섹터 확산 개선으로 이어지면 메가캡보다 경기민감·소형주 쪽 확산을 먼저 확인하는 대응이 좋습니다.", 80)
    elif rates_state == "rates_down_mixed":
        add_point("금리 하락이 나와도 방어자산이 함께 강하면 안전자산 선호 해석인지 먼저 구분해야 합니다.", 76)

    if overlay_state == "dollar_defensive":
        add_point("달러 강세와 고베타 약세가 겹친 만큼 위험선호 복귀를 서두르기보다 DXY와 비트코인 진정 여부를 먼저 확인해야 합니다.", 83)
    elif overlay_state == "dollar_risk_on":
        add_point("달러 완화와 비트코인 반등이 같이 이어지면 위험선호 확산 신호로 해석할 여지가 있어 베타 확대 여지를 열어둘 만합니다.", 74)
    elif overlay_state == "safe_haven_bid":
        add_point("금과 VIX가 함께 강한 구간에서는 지수 반등보다 방어자산 진정 여부를 먼저 확인하는 편이 안전합니다.", 78)
    elif overlay_state == "oil_shock":
        add_point("유가 급등이 이어지면 에너지 강세만 보기보다 운송·소비 업종 부담으로 번지는지 함께 체크해야 합니다.", 76)
    elif overlay_state == "oil_relief":
        add_point("유가 부담 완화가 이어지면 항공·운송·소비처럼 비용 민감 업종의 반응을 같이 보는 대응이 좋습니다.", 68)

    if sector_state.get("state") == "defensive_led":
        add_point("방어주 주도가 이어지면 신규 베타 확대보다 현금 비중과 손절 기준 관리가 우선입니다.", 79)
    elif sector_state.get("state") == "cyclical_led":
        add_point(f"{sector_state.get('label') or '경기민감 섹터'} 중심 순환매가 이어지면 지수보다 경기민감 업종을 넓게 보는 대응이 좋습니다.", 72)
    elif sector_state.get("state") == "energy_led" and overlay_state != "oil_shock":
        add_point("에너지 주도가 유가 뉴스 하루 반응인지, 금융·산업재로 번지는 순환매인지 구분해서 볼 필요가 있습니다.", 66)
    elif sector_state.get("state") == "tech_led_narrow":
        add_point("기술주가 시장보다 강해도 확산이 좁다면 반도체·플랫폼 리더십이 하루짜리인지 확인하는 대응이 필요합니다.", 70)

    if {"거시·연준", "외부 변수", "원자재·암호"} & lead_sections:
        if {"연준·금리", "경제지표"} & lead_events:
            add_point("다음 세션은 거시 헤드라인보다 10Y와 달러가 같은 방향으로 재반응하는지 확인해야 합니다.", 81)
        elif "지정학" in lead_events:
            add_point("지정학 뉴스는 제목보다 유가와 달러가 같은 방향으로 재반응하는지 확인해야 실제 시장 영향도를 더 신뢰할 수 있습니다.", 80)
        else:
            add_point("다음 세션은 뉴스보다 10Y·DXY·WTI가 같은 방향으로 재반응하는지 확인해야 합니다.", 72)
    elif "실적·개별주" in lead_sections:
        if {"실적 상회", "가이던스 상향", "계약·협업"} & lead_events:
            add_point("주도 종목 호재가 하루 재료에 그치지 않는지 거래량과 동종 업종 확산으로 확인할 필요가 있습니다.", 76)
        elif {"실적 하회", "가이던스 하향", "규제·조사"} & lead_events:
            add_point("악재성 개별주 뉴스는 해당 종목에만 머무는지, 섹터 전체 밸류에이션 부담으로 번지는지 함께 확인해야 합니다.", 74)
        else:
            add_point("주도 종목 뉴스가 하루 재료에 그치지 않는지 거래량과 섹터 확산으로 확인할 필요가 있습니다.", 70)

    if not ranked_points:
        add_point("한 방향 베팅보다 상대강도와 금리 반응을 함께 보며 포지션 크기를 조절하는 대응이 유효합니다.", 50)

    ordered_points = []
    seen = set()
    for _, text in sorted(ranked_points, key=lambda row: row[0], reverse=True):
        if text in seen:
            continue
        seen.add(text)
        ordered_points.append(text)
        if len(ordered_points) >= 3:
            break
    return ordered_points


def _build_market_insight_watchlist(benchmarks, macro, sector_rows, market_regime, news_context=None):
    qqq_vs_spy = market_regime.get("qqq_vs_spy")
    iwm_vs_spy = market_regime.get("iwm_vs_spy")
    tnx_snapshot = macro.get("10Y", {})
    tnx_bps = ((tnx_snapshot.get("price") or 0) - (tnx_snapshot.get("prev_close") or 0)) * 10 if tnx_snapshot else None
    dxy_chg = macro.get("DXY", {}).get("change_pct")
    gold_chg = macro.get("Gold", {}).get("change_pct")
    btc_chg = macro.get("BTC", {}).get("change_pct")
    vix_chg = benchmarks.get("VIX", {}).get("change_pct")
    sector_up = sum(1 for row in sector_rows if (row.get("change_pct") or 0) > 0)
    sector_total = len(sector_rows) or len(_US_SECTOR_ETFS)
    breadth_ratio = sector_up / sector_total if sector_total else 0.5

    watchlist = []
    lead_sections = set(_coerce_market_text_list((news_context or {}).get("lead_sections")))
    if {"거시·연준", "외부 변수", "원자재·암호"} & lead_sections:
        watchlist.append("10Y·DXY·WTI가 장 초반에도 같은 방향으로 움직이는지 확인")
    elif "실적·개별주" in lead_sections:
        watchlist.append("주도 종목 강세가 동종 업종과 섹터 전반으로 확산되는지 확인")

    if qqq_vs_spy is not None and qqq_vs_spy >= 0.45 and breadth_ratio <= 0.45:
        watchlist.append("메가캡 쏠림이 시장 전반 확산으로 번지는지 확인")
    else:
        watchlist.append("QQQ가 SPY 대비 상대강도를 회복하는지 확인")

    if iwm_vs_spy is not None and iwm_vs_spy >= 0.35:
        watchlist.append("IWM 상대강도가 하루 반짝이 아닌지 확인")
    else:
        watchlist.append("IWM이 SPY 대비 상대강도를 회복하는지 확인")

    if tnx_bps is not None and tnx_bps <= -4 and (((gold_chg or 0) >= 0.8) or ((vix_chg or 0) >= 3)):
        watchlist.append("10Y·Gold·VIX 조합이 위험회피 완화로 이어지는지 확인")
    elif (dxy_chg or 0) >= 0.35 and (btc_chg or 0) <= -2.5:
        watchlist.append("달러 강세와 비트코인 약세가 진정되는지 확인")
    else:
        watchlist.append("Gold/BTC와 VIX로 방어 심리 지속 여부 확인")

    return _ordered_unique(watchlist)[:4]


def _fallback_market_insight(benchmarks, macro, sector_rows, news_context=None, market_regime=None, market_structure=None):
    spy = benchmarks.get("SPY", {}).get("change_pct")
    qqq = benchmarks.get("QQQ", {}).get("change_pct")
    iwm = benchmarks.get("IWM", {}).get("change_pct")
    vix = benchmarks.get("VIX", {}).get("change_pct")
    tnx_bps = ((macro.get("10Y", {}).get("price") or 0) - (macro.get("10Y", {}).get("prev_close") or 0)) * 10 if macro.get("10Y") else 0
    dxy_chg = macro.get("DXY", {}).get("change_pct")
    gold_chg = macro.get("Gold", {}).get("change_pct")
    btc_chg = macro.get("BTC", {}).get("change_pct")
    breadth = sum(1 for row in sector_rows if (row.get("change_pct") or 0) > 0)
    total = len(sector_rows) or 11
    qqq_vs_spy = _relative_change(benchmarks.get("QQQ", {}), benchmarks.get("SPY", {}))
    iwm_vs_spy = _relative_change(benchmarks.get("IWM", {}), benchmarks.get("SPY", {}))
    strongest_sector = max(sector_rows, key=lambda row: row.get("change_pct") if row.get("change_pct") is not None else -999) if sector_rows else None
    market_regime = market_regime or _build_market_regime(benchmarks, macro, sector_rows)
    market_structure = market_structure or _describe_market_structure(benchmarks, macro, sector_rows)
    news_context = news_context or {}
    divergence_notes = _build_market_divergence_notes(benchmarks, macro, sector_rows, market_regime, market_structure)
    strategy_points = _build_market_strategy_points(benchmarks, macro, sector_rows, market_regime, news_context=news_context)
    watchlist = _build_market_insight_watchlist(benchmarks, macro, sector_rows, market_regime, news_context=news_context)
    if spy is None:
        return {
            "short_view": "핵심 입력값이 아직 동기화 중이라 오늘 인사이트는 데이터가 안정되면 다시 갱신됩니다.",
            "deep_dive": [
                "지수와 거시 입력값이 아직 완전히 들어오지 않아 시장 맥락을 확정하기 이릅니다.",
                "데이터가 안정되면 시장이 무엇에 더 민감했는지 다시 정리합니다.",
            ],
            "strategy": ["QQQ와 SPY, IWM과 SPY 상대강도가 먼저 안정되는지 확인해야 합니다."],
            "insight": "핵심 입력값이 아직 동기화 중이라 오늘 인사이트는 데이터가 안정되면 다시 갱신됩니다.",
            "watchlist": ["QQQ와 SPY 상대강도 확인", "IWM과 SPY 상대강도 확인", "Gold/BTC 방어 심리 확인"],
        }

    if tnx_bps <= -4 and (gold_chg or 0) >= 0.8 and (vix or 0) >= 3:
        short_view = "금리 하락보다 안전자산 선호 해석이 더 중요했던 장이었습니다."
    elif qqq_vs_spy is not None and qqq_vs_spy >= 0.45 and breadth <= max(4, total // 3):
        short_view = "지수 반등보다 메가캡 쏠림 여부를 먼저 따져봐야 했던 장이었습니다."
    elif iwm_vs_spy is not None and iwm_vs_spy >= 0.35 and breadth >= max(total // 2, 6):
        short_view = "메가캡 편중 완화와 시장 확산 여부가 핵심이었던 장이었습니다."
    elif (dxy_chg or 0) >= 0.35 and (btc_chg or 0) <= -2.5:
        short_view = "달러 강세가 위험선호 회복을 눌렀는지가 핵심이었던 장이었습니다."
    elif strongest_sector and strongest_sector.get("symbol") in {"XLU", "XLP", "XLV"} and breadth <= max(total // 2, 5):
        short_view = "표면 지수보다 방어주 주도가 말해준 경계 심리가 더 중요했던 장이었습니다."
    elif (vix or 0) > 4 and tnx_bps > 0:
        short_view = "금리와 변동성이 함께 올라 추세보다 리스크 관리가 중요했던 장이었습니다."
    elif (qqq or 0) > (spy or 0) and breadth >= total // 2:
        short_view = "빅테크 리더십은 유지됐지만 확산 여부를 함께 봐야 했던 장이었습니다."
    elif iwm is not None and spy is not None and iwm > spy and breadth >= total // 2:
        short_view = "소형주가 받쳐주며 시장 전반 회복 신호의 신뢰도가 높아진 장이었습니다."
    elif gold_chg is not None and btc_chg is not None and gold_chg > 0.8 and btc_chg < 0:
        short_view = "금 강세와 비트코인 약세가 함께 나오며 방어 심리가 더 중요한 장이었습니다."
    elif breadth <= 3:
        short_view = "하락이 넓게 퍼진 만큼 방향성보다 방어와 체력 관리가 중요했던 장이었습니다."
    else:
        short_view = "지수 방향보다 상대강도와 거시 변수 해석이 더 중요했던 장이었습니다."

    deep_dive = []
    if str(news_context.get("focus") or "").strip():
        deep_dive.append(str(news_context.get("focus") or "").strip())
    lead_issues = _coerce_market_text_list(news_context.get("lead_issues"), max_items=2)
    if lead_issues:
        deep_dive.append(f"뉴스 흐름에서는 {_join_market_phrases(lead_issues)}가 함께 부각됐습니다.")
    deep_dive.extend(divergence_notes)
    if not deep_dive:
        deep_dive.append(f"시장 내부 체력은 {market_structure['label']} 흐름이었고, 리스크 상태는 {market_regime['state_display']}로 해석됩니다.")

    return {
        "short_view": short_view,
        "deep_dive": _ordered_unique(deep_dive)[:3],
        "strategy": _coerce_market_text_list(strategy_points, max_items=3),
        "insight": short_view,
        "watchlist": _coerce_market_text_list(watchlist, max_items=4),
    }


def _resolve_market_mover_etf_payload():
    try:
        return resolve_etf_universe(
            [
                {"requested": "S&P500", "resolved": "SPY"},
                {"requested": "MSCI(USA)", "resolved": "EUSA"},
            ]
        )
    except Exception as exc:
        return {
            "items": [],
            "tickers": [],
            "note": "",
            "errors": [str(exc)],
        }


def _market_mover_universe(etf_payload=None):
    payload = etf_payload if isinstance(etf_payload, dict) else _resolve_market_mover_etf_payload()
    raw = []
    for tickers in SECTOR_GROUPS.values():
        if isinstance(tickers, (list, tuple, set)):
            raw.extend(str(ticker or "").strip() for ticker in tickers)
    raw.extend(str(ticker or "").strip() for ticker in (payload.get("tickers") or []))

    filtered = []
    for ticker in _ordered_unique(_normalize_market_symbol(ticker) for ticker in raw):
        if not re.fullmatch(r"[A-Z0-9\-=]+", ticker):
            continue
        filtered.append(ticker)
    return tuple(filtered)


def _build_market_news_universe(gainers, losers):
    priority_movers = []
    for row in list(gainers or [])[:_US_MARKET_NEWS_GAINER_SYMBOL_LIMIT]:
        symbol = str(row.get("symbol") or "").strip()
        if symbol:
            priority_movers.append(symbol)
    for row in list(losers or [])[:_US_MARKET_NEWS_LOSER_SYMBOL_LIMIT]:
        symbol = str(row.get("symbol") or "").strip()
        if symbol:
            priority_movers.append(symbol)
    return _ordered_unique(
        [*_US_MARKET_SYSTEMIC_NEWS_SYMBOLS]
        + list(_US_MARKET_MEGA_CAPS[:_US_MARKET_NEWS_MEGA_CAP_LIMIT])
        + priority_movers
    )


def _mover_reason(snapshot):
    change_pct = snapshot.get("change_pct")
    volume_ratio = snapshot.get("volume_ratio")
    five_day_change = snapshot.get("five_day_change")
    month_change = snapshot.get("month_change")
    if change_pct is None:
        return "데이터 부족"
    direction = "상승 탄력 확대" if change_pct > 0 else "급한 조정"
    if volume_ratio is not None and volume_ratio >= 1.7:
        return f"거래량 {volume_ratio:.1f}배와 함께 {direction}"
    if five_day_change is not None and change_pct > 0 and five_day_change < 0:
        return "최근 약세 이후 기술적 반등"
    if five_day_change is not None and change_pct < 0 and five_day_change > 0:
        return "단기 급등 뒤 차익실현"
    if month_change is not None and month_change > 8:
        return "월간 강세 흐름 속 추세 연장"
    if month_change is not None and month_change < -8:
        return "월간 약세 흐름 속 추가 하락"
    return "단기 수급이 빠르게 이동"


def _average_market_change(rows):
    values = [row.get("change_pct") for row in (rows or []) if row.get("change_pct") is not None and not pd.isna(row.get("change_pct"))]
    if not values:
        return None
    return float(sum(values) / len(values))


def _build_mover_context(snapshot):
    snapshot = snapshot or {}
    parts = []
    volume_ratio = snapshot.get("volume_ratio")
    five_day_change = snapshot.get("five_day_change")
    month_change = snapshot.get("month_change")
    if volume_ratio is not None and not pd.isna(volume_ratio) and volume_ratio >= 1.25:
        parts.append(f"거래량 {volume_ratio:.1f}배")
    if five_day_change is not None and not pd.isna(five_day_change):
        parts.append(f"5일 {_format_change_pct(five_day_change)}")
    if month_change is not None and not pd.isna(month_change):
        parts.append(f"1개월 {_format_change_pct(month_change)}")
    return " · ".join(parts[:2])


def _build_mover_detail_bullet(row):
    row = row or {}
    symbol = str(row.get("symbol") or "").strip()
    change_pct = row.get("change_pct")
    snapshot = row.get("snapshot") or {}
    tone = "positive" if (change_pct or 0) >= 0 else "negative"
    price_summary = _format_mover_price_summary(snapshot, change_pct=change_pct)
    base = f"{symbol} {price_summary} / {_mover_reason(snapshot)}"
    context = _build_mover_context(snapshot)
    if context:
        base += f" · {context}"
    return _build_market_bullet(base, tone)


def _build_mover_detail_row(row):
    row = row or {}
    symbol = str(row.get("symbol") or "").strip()
    snapshot = row.get("snapshot") or {}
    price = _safe_market_float(snapshot.get("price"))
    prev_close = _safe_market_float(snapshot.get("prev_close"))
    change_value = (price - prev_close) if (price is not None and prev_close is not None) else None
    return {
        "symbol": symbol,
        "price": price,
        "prev_close": prev_close,
        "change_value": change_value,
        "change_pct": row.get("change_pct"),
        "price_summary": _format_mover_price_summary(snapshot, change_pct=row.get("change_pct")),
        "volume_ratio": snapshot.get("volume_ratio"),
        "five_day_change": snapshot.get("five_day_change"),
        "month_change": snapshot.get("month_change"),
        "reason": _mover_reason(snapshot),
    }


def _build_market_analysis_actions(movers_sorted, limit=_US_MARKET_ANALYSIS_ACTION_COUNT):
    max_items = max(0, int(limit or 0))
    if max_items <= 0:
        return []

    actions = []
    seen = set()
    for row in list(movers_sorted or []):
        change_pct = row.get("change_pct")
        if change_pct is None or pd.isna(change_pct):
            continue
        try:
            change_pct = float(change_pct)
        except Exception:
            continue
        if change_pct <= 0:
            continue

        symbol = _normalize_market_symbol(row.get("symbol"))
        if not symbol or symbol in seen:
            continue
        if not re.fullmatch(r"[A-Z0-9\-=]+", symbol):
            continue

        seen.add(symbol)
        actions.append(
            {
                "symbol": symbol,
                "change_pct": change_pct,
                "rank": len(actions) + 1,
                "source": "gainers_today",
            }
        )
        if len(actions) >= max_items:
            break
    return actions


def _extract_json_object(text):
    if not text:
        return "{}"
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if fenced:
        return fenced.group(1)
    raw = re.search(r"\{.*\}", text, re.S)
    return raw.group(0) if raw else "{}"


def _is_market_news_rate_limited(err):
    sample = str(err or "").lower()
    return "too many requests" in sample or "rate limit" in sample or "429" in sample


def _normalize_market_news_title(title):
    normalized = re.sub(r"\W+", " ", str(title or "").lower())
    return re.sub(r"\s+", " ", normalized).strip()


def _normalize_market_news_url(url):
    normalized = str(url or "").strip().split("#", 1)[0].split("?", 1)[0].rstrip("/")
    return normalized.lower()


def _market_news_has_korean(text):
    return bool(re.search(r"[가-힣]", str(text or "")))


def _partially_translate_market_news_title(title):
    translated = str(title or "").strip()
    if not translated:
        return ""
    for pattern, replacement in _MARKET_NEWS_TITLE_TRANSLATIONS:
        translated = re.sub(pattern, replacement, translated, flags=re.I)
    translated = translated.replace(" - ", " · ")
    translated = re.sub(r"\s+([,:;.!?])", r"\1", translated)
    translated = re.sub(r"\s+", " ", translated).strip()
    return translated


def _fallback_market_news_title_ko(item):
    raw_title = str(item.get("title") or "").strip()
    if not raw_title:
        return ""
    translated = _partially_translate_market_news_title(raw_title)
    if translated != raw_title or _market_news_has_korean(translated):
        return translated
    display_label = item.get("display_label") or item.get("ticker") or "시장"
    tag = item.get("tag") or "핵심"
    return f"{display_label} {tag} 관련: {raw_title}"


def _should_show_market_news_raw_title(title_ko, title_raw):
    ko = str(title_ko or "").strip()
    raw = str(title_raw or "").strip()
    if not ko or not raw or ko == raw:
        return False
    return _normalize_market_news_title(raw) not in _normalize_market_news_title(ko)


def _clean_market_news_excerpt(text, max_chars=_US_MARKET_NEWS_EXCERPT_MAX_CHARS):
    sample = html.unescape(str(text or "")).strip()
    if not sample:
        return ""
    sample = re.sub(r"<[^>]+>", " ", sample)
    sample = re.sub(r"\s+", " ", sample).strip(" -:\n\t")
    if not sample:
        return ""
    if len(sample) <= max_chars:
        return sample
    truncated = sample[:max_chars].rsplit(" ", 1)[0].strip()
    return (truncated or sample[:max_chars]).rstrip(" ,;:") + "..."


def _market_news_parse_text(*parts):
    joined = " ".join(str(part or "").strip() for part in parts if str(part or "").strip())
    return re.sub(r"\s+", " ", joined).strip().lower()


def _market_news_excerpt_score(text, title=""):
    sample = str(text or "").strip()
    if not sample:
        return -1
    title_norm = _normalize_market_news_title(title)
    sample_norm = _normalize_market_news_title(sample)
    score = min(len(sample), _US_MARKET_NEWS_EXCERPT_MAX_CHARS)
    if title_norm and sample_norm and title_norm == sample_norm:
        score -= 120
    if len(sample.split()) >= 14:
        score += 30
    if re.search(r"\b(revenue|earnings|guidance|forecast|contract|probe|tariff|ceasefire|opec|yield|cpi|bitcoin)\b", sample, re.I):
        score += 24
    return score


def _extract_market_news_meta_description(soup):
    if soup is None:
        return ""
    selectors = [
        ("meta", {"property": "og:description"}),
        ("meta", {"name": "description"}),
        ("meta", {"name": "twitter:description"}),
    ]
    for tag_name, attrs in selectors:
        tag = soup.find(tag_name, attrs=attrs)
        content = _clean_market_news_excerpt(tag.get("content") if tag else "")
        if content:
            return content
    return ""


def _extract_market_news_paragraph_excerpt(soup):
    if soup is None:
        return ""
    for tag_name in ["script", "style", "noscript", "header", "footer", "nav", "svg"]:
        for node in soup.find_all(tag_name):
            node.decompose()
    containers = []
    for selector in ["article", "main"]:
        containers.extend(soup.find_all(selector))
    if not containers:
        containers = soup.find_all(["section", "div"], limit=25)
    paragraphs = []
    seen = set()
    for container in containers:
        for p in container.find_all("p", limit=20):
            text = _clean_market_news_excerpt(p.get_text(" ", strip=True), max_chars=_US_MARKET_NEWS_EXCERPT_MAX_CHARS)
            norm = _normalize_market_news_title(text)
            if len(text) < 80 or norm in seen:
                continue
            seen.add(norm)
            paragraphs.append(text)
            if len(paragraphs) >= 3:
                break
        if len(paragraphs) >= 3:
            break
    combined = " ".join(paragraphs[:2]).strip()
    return _clean_market_news_excerpt(combined) if combined else ""


@st.cache_data(ttl=7200, show_spinner=False)
def _fetch_market_news_article_excerpt(url):
    if not url or cloudscraper is None or BeautifulSoup is None:
        return {"excerpt": "", "source_depth": "headline"}
    try:
        scraper = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "windows", "mobile": False}
        )
        response = scraper.get(
            str(url).strip(),
            timeout=_US_MARKET_NEWS_ARTICLE_FETCH_TIMEOUT_SEC,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        if not getattr(response, "ok", False):
            return {"excerpt": "", "source_depth": "headline"}
        soup = BeautifulSoup(getattr(response, "text", "") or "", "html.parser")
        meta_excerpt = _extract_market_news_meta_description(soup)
        body_excerpt = _extract_market_news_paragraph_excerpt(soup)
        if _market_news_excerpt_score(body_excerpt) > _market_news_excerpt_score(meta_excerpt):
            excerpt = body_excerpt
            source_depth = "article"
        else:
            excerpt = meta_excerpt or body_excerpt
            source_depth = "snippet" if meta_excerpt else ("article" if body_excerpt else "headline")
        return {"excerpt": excerpt, "source_depth": source_depth}
    except Exception:
        return {"excerpt": "", "source_depth": "headline"}


def _detect_market_news_event_type(text, tag):
    sample = str(text or "")
    if re.search(r"\b(beat|beats|tops|top estimates|better than expected|above estimates)\b", sample):
        return "earnings_beat"
    if re.search(r"\b(miss|misses|below estimates|short of estimates|falls after earnings)\b", sample):
        return "earnings_miss"
    if re.search(r"\b(raises outlook|raise[s]? guidance|lift[s]? forecast|upgrades? outlook|boosts? forecast)\b", sample):
        return "guidance_up"
    if re.search(r"\b(cuts? outlook|cut[s]? guidance|lowers? forecast|warns?|trim[s]? outlook)\b", sample):
        return "guidance_down"
    if re.search(r"\b(wins? contract|agreement|partnership|collaboration|joint venture|alliance|deal signed|supply deal)\b", sample):
        return "contract_partnership"
    if re.search(r"\b(acquire|acquisition|merger|buyout|takeover|stake in)\b", sample):
        return "mna"
    if re.search(r"\b(lawsuit|sues|sued|court|judge|trial|settlement|appeal)\b", sample):
        return "lawsuit"
    if re.search(r"\b(regulator|regulatory|probe|investigation|antitrust|ftc|doj|sec|ban|export control)\b", sample):
        return "regulation_probe"
    if re.search(r"\b(powell|fed|fomc|federal reserve|rate cut|rate hike|treasury yield|bond yield)\b", sample):
        return "fed_rates"
    if re.search(r"\b(cpi|pce|gdp|payroll|jobless|retail sales|pmi|ism|inflation report)\b", sample):
        return "macro_data"
    if re.search(r"\b(tariff|sanction|white house|congress|senate|budget|tax plan|administration)\b", sample):
        return "policy_politics"
    if re.search(r"\b(hormuz|middle east|iran|israel|ukraine|russia|war|attack|ceasefire|tanker|shipping lane)\b", sample):
        return "geopolitics"
    if re.search(r"\b(oil|crude|brent|wti|opec|refinery|energy price|diesel)\b", sample):
        return "oil_commodities"
    if re.search(r"\b(bitcoin|ethereum|crypto|cryptocurrency|stablecoin|token|spot etf)\b", sample):
        return "crypto"
    if re.search(r"\b(ai|artificial intelligence|openai|copilot|chatgpt|llm)\b", sample):
        return "ai"
    if re.search(r"\b(semiconductor|chip|chips|gpu|foundry|memory|hbm)\b", sample):
        return "semiconductor"
    if re.search(r"\b(demand|orders|bookings|traffic|spending|consumption)\b", sample):
        return "demand"
    if re.search(r"\b(production|output|capacity|factory|supply|shipments?)\b", sample):
        return "production"
    tag_map = {
        "연준": "fed_rates",
        "경제지표": "macro_data",
        "정책/정치": "policy_politics",
        "암호화폐": "crypto",
        "파트너십": "contract_partnership",
        "실적": "earnings",
        "가이던스": "guidance",
        "AI": "ai",
        "반도체": "semiconductor",
        "지정학": "geopolitics",
        "원자재": "oil_commodities",
        "규제": "regulation_probe",
        "M&A": "mna",
        "금리": "fed_rates",
        "수요": "demand",
        "생산": "production",
        "소송": "lawsuit",
    }
    return tag_map.get(tag, "market_update")


def _detect_market_news_event_direction(text, event_type, change_pct=None):
    sample = str(text or "")
    if event_type in {"earnings_beat", "guidance_up", "contract_partnership"}:
        return "positive"
    if event_type in {"earnings_miss", "guidance_down", "lawsuit", "regulation_probe"}:
        return "negative"
    if re.search(r"\b(beat|beats|raises|upgrades|wins|surges|jumps|rallies|strong demand)\b", sample):
        return "positive"
    if re.search(r"\b(miss|misses|cuts|warns|downgrade|slumps|falls|drops|probe|lawsuit)\b", sample):
        return "negative"
    if change_pct is not None and not pd.isna(change_pct):
        if float(change_pct) >= 1:
            return "positive"
        if float(change_pct) <= -1:
            return "negative"
    return "neutral"


def _build_market_news_fact_ko(subject, event_type, event_direction):
    fact_map = {
        "earnings_beat": f"{subject}가 실적 기대를 웃돌았거나 호실적 신호가 부각된 소식",
        "earnings_miss": f"{subject}가 실적 기대를 밑돌았거나 실적 실망 우려가 부각된 소식",
        "guidance_up": f"{subject}의 가이던스·전망 상향이 부각된 소식",
        "guidance_down": f"{subject}의 가이던스·전망 하향이 부각된 소식",
        "contract_partnership": f"{subject}의 협업·계약·수주 관련 소식",
        "mna": f"{subject}의 인수·합병 또는 지분 거래 관련 소식",
        "lawsuit": f"{subject} 관련 소송이나 법적 분쟁 소식",
        "regulation_probe": f"{subject} 관련 규제·조사 이슈 소식",
        "fed_rates": "연준 발언이나 금리 기대 재조정 관련 소식",
        "macro_data": "경제지표 발표나 해석 변화 관련 소식",
        "policy_politics": "정책·정치 변수 변화 관련 소식",
        "geopolitics": "전쟁·분쟁·운송 차질 같은 지정학 리스크 소식",
        "oil_commodities": f"{subject} 관련 유가·원자재 변수 변화 소식",
        "crypto": f"{subject} 관련 가상자산 가격·제도 변화 소식",
        "ai": f"{subject} 관련 AI 기대나 투자심리 변화 소식",
        "semiconductor": f"{subject} 관련 반도체 수요·공급망 소식",
        "demand": f"{subject} 수요 흐름 변화와 연결된 소식",
        "production": f"{subject} 생산·공급 변화와 연결된 소식",
        "guidance": f"{subject} 전망 변화와 관련된 소식",
        "earnings": f"{subject} 실적과 관련된 소식",
        "market_update": f"{subject} 관련 핵심 업데이트",
    }
    base = fact_map.get(event_type, f"{subject} 관련 핵심 소식")
    if event_direction == "positive" and event_type not in {"earnings_beat", "guidance_up", "contract_partnership", "ai"}:
        return f"{base}이 긍정적으로 해석된 뉴스"
    if event_direction == "negative" and event_type not in {"earnings_miss", "guidance_down", "lawsuit", "regulation_probe"}:
        return f"{base}이 부담으로 해석된 뉴스"
    return base


def _build_market_news_impact_ko(subject, event_type, tag, section_label):
    impact_map = {
        "earnings_beat": "실적 기대와 밸류에이션 재평가 가능성을 키울 수 있습니다.",
        "earnings_miss": "실적 기대 하향과 단기 주가 변동성을 키울 수 있습니다.",
        "guidance_up": "앞으로의 실적 기대를 끌어올리는 재료가 될 수 있습니다.",
        "guidance_down": "향후 실적 기대를 낮추며 경계 심리를 키울 수 있습니다.",
        "contract_partnership": "신규 매출 기대나 성장 스토리를 강화할 수 있습니다.",
        "mna": "밸류에이션 기대와 업계 재편 기대를 자극할 수 있습니다.",
        "lawsuit": "법적 불확실성과 비용 부담 우려를 키울 수 있습니다.",
        "regulation_probe": "규제 불확실성과 멀티플 부담 요인으로 작용할 수 있습니다.",
        "fed_rates": "금리 민감주와 달러·채권 흐름 해석에 영향을 줄 수 있습니다.",
        "macro_data": "경기와 금리 경로 기대를 다시 조정하게 만들 수 있습니다.",
        "policy_politics": "정책 변수에 따른 시장 변동성을 키울 수 있습니다.",
        "geopolitics": "유가·금·달러 같은 방어 자산 흐름에 영향을 줄 수 있습니다.",
        "oil_commodities": "인플레이션 기대와 에너지 민감 섹터 심리에 영향을 줄 수 있습니다.",
        "crypto": "위험선호 심리와 가상자산 관련 종목 흐름에 영향을 줄 수 있습니다.",
        "ai": "AI 투자심리와 관련 공급망 기대를 자극할 수 있습니다.",
        "semiconductor": "반도체 업황 기대와 공급망 심리에 영향을 줄 수 있습니다.",
        "demand": "실적 추정치와 업황 기대를 다시 보게 만드는 재료입니다.",
        "production": "공급과 마진 전망을 다시 조정하게 만들 수 있습니다.",
        "guidance": "향후 분기 실적 기대를 조정하게 만드는 재료입니다.",
        "earnings": "단기 실적 해석과 주가 민감도를 높이는 재료입니다.",
        "market_update": "해당 카테고리의 대표 심리를 설명하는 뉴스입니다.",
    }
    if section_label == "시장 총평":
        return "지수와 시장 폭 해석에 참고할 만한 흐름입니다."
    return impact_map.get(event_type, f"{subject} 관련 심리와 수급 해석에 영향을 줄 수 있습니다.")


def _build_market_news_structured_fields(item):
    subject = str(item.get("display_label") or item.get("ticker") or "시장").strip() or "시장"
    title = str(item.get("title") or "").strip()
    body_excerpt = str(item.get("body_excerpt") or "").strip()
    tag = str(item.get("tag") or "시장").strip()
    section_label = str(item.get("section") or "").strip()
    combined = _market_news_parse_text(title, body_excerpt)
    event_type = _detect_market_news_event_type(combined, tag)
    event_direction = _detect_market_news_event_direction(combined, event_type, item.get("change_pct"))
    key_fact_ko = _build_market_news_fact_ko(subject, event_type, event_direction)
    market_impact_ko = _build_market_news_impact_ko(subject, event_type, tag, section_label)
    return {
        "event_type": event_type,
        "event_direction": event_direction,
        "subject": subject,
        "key_fact_ko": key_fact_ko,
        "market_impact_ko": market_impact_ko,
    }


def _build_market_news_takeaway_ko(item):
    fields = _build_market_news_structured_fields(item)
    event_type = str(fields.get("event_type") or "").strip()
    event_direction = str(fields.get("event_direction") or "").strip()
    section_label = str(item.get("section") or "").strip()
    subject = _market_news_subject_for_takeaway(item, event_type, fields.get("subject"))
    prefix = _market_news_takeaway_tag(item, event_type)
    fact_phrase = _build_market_news_fact_phrase_ko(item, fields)
    reaction_phrase = _market_news_reaction_phrase(item, event_direction)
    impact_phrase = _market_news_impact_tail_ko(event_type, section_label, event_direction)
    if fact_phrase and reaction_phrase:
        core = f"{fact_phrase}에 {reaction_phrase}"
    else:
        core = fact_phrase or reaction_phrase or "핵심 이슈 부각"
    if impact_phrase:
        return f"{prefix} {subject}, {core}, {impact_phrase}"
    return f"{prefix} {subject}, {core}"


def _market_news_event_label_ko(event_type):
    labels = {
        "earnings_beat": "실적 상회",
        "earnings_miss": "실적 하회",
        "guidance_up": "가이던스 상향",
        "guidance_down": "가이던스 하향",
        "contract_partnership": "계약·협업",
        "mna": "인수합병",
        "lawsuit": "소송",
        "regulation_probe": "규제·조사",
        "fed_rates": "연준·금리",
        "macro_data": "경제지표",
        "policy_politics": "정책·정치",
        "geopolitics": "지정학",
        "oil_commodities": "원자재",
        "crypto": "가상자산",
        "ai": "AI",
        "semiconductor": "반도체",
        "demand": "수요",
        "production": "생산",
        "guidance": "가이던스",
        "earnings": "실적",
        "market_update": "시장 업데이트",
    }
    return labels.get(str(event_type or "").strip(), "핵심 뉴스")


def _market_news_event_score(event_type):
    weights = {
        "fed_rates": 18,
        "macro_data": 18,
        "geopolitics": 18,
        "policy_politics": 14,
        "oil_commodities": 14,
        "earnings_beat": 14,
        "earnings_miss": 14,
        "guidance_up": 14,
        "guidance_down": 14,
        "earnings": 12,
        "guidance": 12,
        "regulation_probe": 14,
        "lawsuit": 12,
        "crypto": 12,
        "contract_partnership": 10,
        "mna": 10,
        "ai": 8,
        "semiconductor": 8,
        "demand": 6,
        "production": 6,
        "market_update": 2,
    }
    return weights.get(str(event_type or "").strip(), 0)


def _market_news_takeaway_tag(item, event_type=""):
    tag_map = {
        "earnings_beat": "실적",
        "earnings_miss": "실적",
        "guidance_up": "가이던스",
        "guidance_down": "가이던스",
        "contract_partnership": "계약",
        "mna": "M&A",
        "lawsuit": "소송",
        "regulation_probe": "규제",
        "fed_rates": "금리",
        "macro_data": "지표",
        "policy_politics": "정책",
        "geopolitics": "지정학",
        "oil_commodities": "원자재",
        "crypto": "암호화폐",
        "ai": "AI",
        "semiconductor": "반도체",
        "demand": "수요",
        "production": "생산",
        "guidance": "가이던스",
        "earnings": "실적",
        "market_update": "시황",
    }
    tag_label = tag_map.get(str(event_type or "").strip()) or str(item.get("tag") or "핵심").strip() or "핵심"
    if tag_label == "정책/정치":
        tag_label = "정책"
    return f"[{tag_label}]"


def _extract_market_news_numeric_clues(*parts):
    sample = " ".join(str(part or "").strip() for part in parts if str(part or "").strip())
    if not sample:
        return []
    clues = []
    patterns = [
        r"\b\d{1,3}(?:,\d{3})*(?:\.\d+)?%",
        r"\$\d{1,4}(?:,\d{3})*(?:\.\d+)?(?:\s*(?:billion|million|trillion|bn|mn|tn))?",
        r"\b\d{1,4}(?:,\d{3})*(?:\.\d+)?\s*(?:bp|bps|basis points?|million|billion|trillion)\b",
        r"\b\d{1,4}(?:,\d{3})*(?:\.\d+)?x\b",
    ]
    for pattern in patterns:
        for match in re.findall(pattern, sample, re.I):
            value = str(match or "").strip()
            if value:
                clues.append(value)
    return _ordered_unique(clues)


def _is_low_signal_market_news_item(item_or_title, body_excerpt=""):
    if isinstance(item_or_title, dict):
        title = str(item_or_title.get("title") or "").strip()
        body_excerpt = str(item_or_title.get("body_excerpt") or "").strip()
    else:
        title = str(item_or_title or "").strip()
        body_excerpt = str(body_excerpt or "").strip()
    sample = _market_news_parse_text(title, body_excerpt)
    if not sample:
        return False
    patterns = [
        r"\bhow .+ compares?\b",
        r"\bfor investors\b",
        r"\bwhat to know\b",
        r"\bexplainer\b",
        r"\bopinion\b",
        r"\banalysis\b",
        r"\bshould you\b",
        r"\bcomparison\b",
        r"\bcompare(?:s|d)?\b",
        r"\bdiversification\b",
    ]
    if any(re.search(pattern, sample) for pattern in patterns):
        return True
    if re.search(r"\bvs\.?\b", sample) and re.search(r"\b(compare|comparison|diversification|investors?)\b", sample):
        return True
    return False


def _build_market_news_context_phrase_ko(item, fields):
    title = str(item.get("title") or "").strip()
    body_excerpt = str(item.get("body_excerpt") or "").strip()
    sample = _market_news_parse_text(title, body_excerpt)
    event_type = str(fields.get("event_type") or "").strip()
    if _is_low_signal_market_news_item(item):
        if re.search(r"\biwm\b", sample) and re.search(r"\bqqq\b", sample):
            return "중소형주·대형성장주 비교 기사"
        if re.search(r"\bvs\.?\b", sample):
            return "자산 비교 해설 기사"
        return "시장 해설 기사"
    if re.search(r"\b(loan|borrowing|borrow|funding|financing|debt)\b", sample):
        if re.search(r"\bopenai\b", sample) and re.search(r"\barm\b", sample):
            return "OpenAI·Arm 투자 확대 보도"
        return "대규모 차입·투자 확대 보도"
    if event_type == "fed_rates":
        if re.search(r"\b(yield|treasury)\b", sample):
            return "국채금리 변동"
        if re.search(r"\b(powell|fomc|federal reserve|fed)\b", sample):
            return "연준 발언"
        return "금리 기대 재조정"
    if event_type == "macro_data":
        if re.search(r"\bcpi\b", sample):
            return "CPI 발표"
        if re.search(r"\bpce\b", sample):
            return "PCE 발표"
        if re.search(r"\b(payroll|jobless|employment|labor market)\b", sample):
            return "고용지표 발표"
        if re.search(r"\bgdp\b", sample):
            return "GDP 발표"
        if re.search(r"\b(retail sales)\b", sample):
            return "소매판매 발표"
        if re.search(r"\b(pmi|ism)\b", sample):
            return "PMI·ISM 발표"
        return "경제지표 발표"
    if event_type == "geopolitics":
        if re.search(r"\b(hormuz|strait of hormuz)\b", sample):
            return "호르무즈 해협 리스크"
        if re.search(r"\b(middle east|iran|israel|gaza)\b", sample):
            return "중동 지정학 리스크"
        if re.search(r"\b(ukraine|russia)\b", sample):
            return "우크라이나 지정학 리스크"
        return "지정학 리스크"
    if event_type == "oil_commodities":
        if re.search(r"\b(opec)\b", sample):
            return "OPEC·유가 변수"
        return "유가·원자재 급등락"
    if event_type == "crypto":
        if re.search(r"\bspot etf\b", sample):
            return "현물 ETF 이슈"
        if re.search(r"\bbitcoin\b", sample):
            return "비트코인 이슈"
        return "가상자산 이슈"
    context_map = {
        "earnings_beat": "실적 예상치 상회",
        "earnings_miss": "실적 예상치 하회",
        "guidance_up": "가이던스 상향",
        "guidance_down": "가이던스 하향",
        "contract_partnership": "대형 계약·협업 보도",
        "mna": "인수·지분 거래 보도",
        "lawsuit": "소송·법적 분쟁",
        "regulation_probe": "규제·조사 이슈",
        "policy_politics": "정책 변수 부각",
        "ai": "AI 투자·수요 기대 보도",
        "semiconductor": "반도체 수요·공급망 보도",
        "demand": "수요 변화 신호",
        "production": "생산·공급 변수",
        "guidance": "전망 변화 보도",
        "earnings": "실적 발표 보도",
        "market_update": "시장 흐름 점검 기사",
    }
    return context_map.get(event_type, "핵심 이슈 보도")


def _market_news_comparison_phrase(text, event_type):
    sample = str(text or "")
    if re.search(r"\b(beat|beats|top estimates|above estimates|better than expected|tops)\b", sample):
        return "예상치 상회"
    if re.search(r"\b(miss|misses|below estimates|short of estimates|worse than expected)\b", sample):
        return "예상치 하회"
    if re.search(r"\b(raises outlook|raise[s]? guidance|lift[s]? forecast|boosts? forecast|upgrades? outlook)\b", sample):
        return "전망 상향"
    if re.search(r"\b(cuts? outlook|cut[s]? guidance|lowers? forecast|warns?|trim[s]? outlook)\b", sample):
        return "전망 하향"
    fallback_map = {
        "earnings_beat": "호실적 신호",
        "earnings_miss": "실적 실망 우려",
        "guidance_up": "전망 상향",
        "guidance_down": "전망 하향",
        "contract_partnership": "계약·협업 보도",
        "mna": "인수·지분 거래",
        "lawsuit": "법적 분쟁",
        "regulation_probe": "규제·조사",
        "fed_rates": "금리 기대 재조정",
        "macro_data": "경제지표 해석 변화",
        "policy_politics": "정책 변수 부각",
        "geopolitics": "지정학 리스크",
        "oil_commodities": "유가·원자재 급변",
        "crypto": "가상자산 이슈",
        "ai": "AI 기대 부각",
        "semiconductor": "반도체 업황 기대",
        "demand": "수요 변화",
        "production": "생산 변수",
        "guidance": "전망 변화",
        "earnings": "실적 발표",
        "market_update": "시장 업데이트",
    }
    return fallback_map.get(str(event_type or "").strip(), "핵심 이슈")


def _market_news_subject_for_takeaway(item, event_type, subject):
    base = str(subject or item.get("display_label") or item.get("ticker") or "시장").strip() or "시장"
    if event_type == "macro_data" and base in {"S&P 500", "나스닥 100", "다우", "러셀 2000"}:
        return "미국 경제지표"
    if event_type == "fed_rates" and base in {"S&P 500", "나스닥 100", "다우", "러셀 2000"}:
        return "연준·금리"
    return base


def _market_news_reaction_phrase(item, event_direction):
    change_pct = item.get("change_pct")
    if change_pct is not None and not pd.isna(change_pct):
        move = float(change_pct)
        if abs(move) <= 0.35:
            return f"{_format_change_pct(move)} 보합권"
        if move >= 3:
            return f"{_format_change_pct(move)} 급등"
        if move > 0:
            return f"{_format_change_pct(move)} 상승"
        if move <= -3:
            return f"{_format_change_pct(move)} 급락"
        return f"{_format_change_pct(move)} 하락"
    if event_direction == "positive":
        return "강세 재료 부각"
    if event_direction == "negative":
        return "경계 심리 확대"
    return "해석 엇갈림"


def _market_news_impact_tail_ko(event_type, section_label, event_direction):
    impact_map = {
        "earnings_beat": "밸류 재평가 재료",
        "earnings_miss": "추정치 하향 부담",
        "guidance_up": "향후 실적 기대 상향 재료",
        "guidance_down": "실적 기대 후퇴 부담",
        "contract_partnership": "신규 매출 기대 재료",
        "mna": "업계 재편 기대 요인",
        "lawsuit": "불확실성 확대 부담",
        "regulation_probe": "멀티플 할인 부담",
        "fed_rates": "성장주 밸류 변수",
        "macro_data": "연준 경로 재평가 요인",
        "policy_politics": "업종별 수급 변수",
        "geopolitics": "유가·방어자산 변동성 요인",
        "oil_commodities": "인플레 기대 자극 요인",
        "crypto": "위험선호 민감도 변수",
        "ai": "공급망 심리 개선 재료",
        "semiconductor": "업황 재평가 요인",
        "demand": "실적 추정치 조정 요인",
        "production": "마진 전망 변수",
        "guidance": "실적 전망 조정 변수",
        "earnings": "실적 민감도 요인",
        "market_update": "지수 방향 판단 재료",
    }
    if section_label == "시장 총평":
        return "시장 폭 판단 재료"
    if event_direction == "negative" and event_type == "market_update":
        return "지수 하방 부담"
    return impact_map.get(str(event_type or "").strip(), "시장 해석 변수")


def _build_market_news_fact_phrase_ko(item, fields):
    event_type = str(fields.get("event_type") or "").strip()
    title = str(item.get("title") or "").strip()
    body_excerpt = str(item.get("body_excerpt") or "").strip()
    combined = _market_news_parse_text(title, body_excerpt)
    context_phrase = _build_market_news_context_phrase_ko(item, fields)
    if _is_low_signal_market_news_item(item) or event_type == "market_update":
        return context_phrase
    comparison = _market_news_comparison_phrase(combined, event_type)
    numeric_clues = _extract_market_news_numeric_clues(title, body_excerpt)[:1]
    parts = []
    if context_phrase:
        parts.append(context_phrase)
    if comparison and comparison not in parts:
        parts.append(comparison)
    if numeric_clues and event_type in {"macro_data", "fed_rates", "earnings_beat", "earnings_miss", "guidance_up", "guidance_down", "oil_commodities", "crypto"}:
        parts.append(numeric_clues[0])
    return " / ".join(_ordered_unique(parts)) if parts else (context_phrase or comparison)


def _build_market_news_issue_phrase_ko(item):
    fields = _build_market_news_structured_fields(item)
    event_type = str(fields.get("event_type") or "").strip()
    subject = _market_news_subject_for_takeaway(item, event_type, fields.get("subject"))
    context_phrase = _build_market_news_context_phrase_ko(item, fields)
    fact_phrase = context_phrase or _build_market_news_fact_phrase_ko(item, fields) or _market_news_event_label_ko(event_type)
    if _is_low_signal_market_news_item(item):
        return context_phrase
    if event_type == "market_update":
        return context_phrase
    if subject in {"연준·금리", "미국 경제지표"}:
        return f"{subject} {fact_phrase}"
    return f"{subject}의 {fact_phrase}" if fact_phrase else subject


def _build_market_news_section_issue_text(section_items, limit=2):
    issues = []
    for item in list(section_items or [])[:limit]:
        phrase = _build_market_news_issue_phrase_ko(item)
        if phrase:
            issues.append(phrase)
    return "와 ".join(_ordered_unique(issues)[:limit])


def _is_generic_market_news_section_summary(text):
    sample = str(text or "").strip()
    if not sample:
        return True
    if len(re.findall(r"\d+(?:\.\d+)?%", sample)) >= 2:
        return True
    if "시장 업데이트" in sample or "흐름 점검 기사" in sample:
        return True
    generic_patterns = [
        "관련 뉴스",
        "해석에 참고",
        "이슈가 중심",
        "뉴스가 중심",
        "흐름이 민감도",
        "영향을 줬습니다",
        "시장 심리에 영향을 준 하루",
    ]
    return any(pattern in sample for pattern in generic_patterns)


def _classify_market_news_tag(title, ticker=""):
    sample = f" {ticker} {title} ".lower()
    if any(keyword in sample for keyword in [
        "hormuz", "strait of hormuz", "middle east", "red sea", "iran", "israel", "gaza", "ukraine", "russia",
        "missile", "drone strike", "airstrike", "attack", "conflict", "war", "ceasefire", "tanker", "shipping lane",
    ]):
        return "지정학"
    if any(keyword in sample for keyword in [
        "oil", "crude", "brent", "wti", "opec", "gas", "lng", "diesel", "refinery", "energy price",
    ]):
        return "원자재"
    if any(keyword in sample for keyword in [
        "powell", "fomc", "fed", "federal reserve", "waller", "bostic", "bowman", "kashkari", "williams",
    ]):
        return "연준"
    if any(keyword in sample for keyword in [
        "cpi", "pce", "gdp", "nonfarm payroll", "payrolls", "jobless claims", "retail sales", "ism", "pmi",
        "inflation report", "employment report", "labor market",
    ]):
        return "경제지표"
    if any(keyword in sample for keyword in [
        "tariff", "sanction", "white house", "congress", "senate", "house bill", "budget", "tax plan", "treasury department",
        "election", "administration", "policy proposal",
    ]):
        return "정책/정치"
    if any(keyword in sample for keyword in [
        "bitcoin", "btc", "ethereum", "eth", "crypto", "cryptocurrency", "stablecoin", "token", "spot etf",
    ]):
        return "암호화폐"
    if any(keyword in sample for keyword in [
        "partnership", "partner", "collaboration", "joint venture", "agreement", "alliance",
    ]):
        return "파트너십"
    if any(keyword in sample for keyword in ["guidance", "outlook", "forecast", "raises outlook", "cuts outlook", "sees "]):
        return "가이던스"
    if any(keyword in sample for keyword in ["earnings", "results", "quarterly", "quarter ", " eps", "revenue", "profit", "sales beat"]):
        return "실적"
    if re.search(r"\bai\b", sample) or any(keyword in sample for keyword in ["artificial intelligence", "openai", "copilot", "chatgpt", "llm"]):
        return "AI"
    if any(keyword in sample for keyword in ["semiconductor", " chip", "chips", "gpu", "hbm", "foundry", "memory"]):
        return "반도체"
    if any(keyword in sample for keyword in ["regulator", "regulatory", "antitrust", "ftc", "doj", "sec ", "probe", "investigation", "tariff", "ban", "export control"]):
        return "규제"
    if "m&a" in sample or any(keyword in sample for keyword in ["acquire", "acquires", "acquisition", "merger", "deal", "buyout", "takeover", "stake"]):
        return "M&A"
    if any(keyword in sample for keyword in ["fed", "fomc", "rate cut", "rates", "yield", "yields", "treasury", "inflation", "cpi", "ppi", "payroll", "jobless"]):
        return "금리"
    if any(keyword in sample for keyword in ["demand", "orders", "bookings", "spending", "traffic", "consumption"]):
        return "수요"
    if any(keyword in sample for keyword in ["production", "output", "capacity", "factory", "supply", "shipment", "shipments"]):
        return "생산"
    if any(keyword in sample for keyword in ["lawsuit", "sues", "sued", "court", "judge", "trial", "settlement", "appeal"]):
        return "소송"
    return "시장"


def _market_news_tag_score(tag):
    weights = {
        "연준": 22,
        "경제지표": 22,
        "정책/정치": 20,
        "암호화폐": 18,
        "파트너십": 14,
        "실적": 22,
        "가이던스": 22,
        "AI": 16,
        "반도체": 15,
        "지정학": 24,
        "원자재": 20,
        "규제": 18,
        "M&A": 14,
        "금리": 18,
        "수요": 10,
        "생산": 10,
        "소송": 12,
        "시장": 6,
    }
    return weights.get(str(tag or "").strip(), 6)


def _classify_market_news_section(item):
    ticker = str(item.get("ticker") or "").strip().upper()
    tag = str(item.get("tag") or "").strip()
    if tag in {"연준", "경제지표", "금리"} or ticker in {"^TNX", "DX-Y.NYB", "KRW=X"}:
        return "거시·연준"
    if tag in {"지정학", "규제", "정책/정치", "소송"}:
        return "외부 변수"
    if tag in {"원자재", "암호화폐"} or ticker in {"GLD", "CL=F", "BTC-USD", "XLE"}:
        return "원자재·암호"
    if ticker in {"SPY", "QQQ", "DIA", "IWM", "^VIX"} and tag == "시장":
        return "시장 총평"
    return "실적·개별주"


def _market_news_time_score(timestamp, reference_dt):
    if not timestamp:
        return 0
    try:
        age_hours = max(0.0, (reference_dt - datetime.fromtimestamp(timestamp)).total_seconds() / 3600)
    except Exception:
        return 0
    if age_hours <= 6:
        return 24
    if age_hours <= 12:
        return 18
    if age_hours <= 24:
        return 10
    if age_hours <= _US_MARKET_NEWS_LOOKBACK_HOURS:
        return 4
    return -20


def _score_market_news_item(item, mover_symbols, mega_cap_symbols, benchmark_symbols, systemic_symbols, reference_dt):
    ticker = str(item.get("ticker") or "").strip().upper()
    score = _market_news_tag_score(item.get("tag"))
    score += _market_news_event_score(item.get("event_type"))
    score += _market_news_time_score(item.get("timestamp"), reference_dt)
    if _is_low_signal_market_news_item(item):
        score -= 26
    if ticker in mover_symbols:
        score += 35
    if ticker in mega_cap_symbols:
        score += 18
    if ticker in benchmark_symbols:
        score += 14
    if ticker in systemic_symbols or item.get("is_systemic"):
        score += 24
    if str(item.get("event_type") or "").strip() == "market_update":
        score -= 10
    if str(item.get("source_depth") or "").strip() == "snippet":
        score += 3
    if str(item.get("source_depth") or "").strip() == "article":
        score += 5
    change_pct = item.get("change_pct")
    if change_pct is not None and not pd.isna(change_pct):
        move = abs(float(change_pct))
        if move >= 5:
            score += 16
        elif move >= 3:
            score += 10
        elif move >= 1.5:
            score += 6
    return score


def _market_news_item_tone(item):
    change_pct = item.get("change_pct")
    if change_pct is not None and not pd.isna(change_pct):
        ticker = str(item.get("ticker") or "").strip().upper()
        inverse_tickers = {"^VIX", "DX-Y.NYB", "KRW=X", "GLD", "CL=F"}
        return _tone_from_change(change_pct, inverse=ticker in inverse_tickers, neutral_band=0.35)
    tag = str(item.get("tag") or "").strip()
    if tag in {"규제", "소송", "지정학", "정책/정치"}:
        return "negative"
    if tag in {"AI", "M&A", "실적", "가이던스", "원자재", "파트너십", "암호화폐"}:
        return "positive"
    return "neutral"


@st.cache_data(ttl=900, show_spinner=False)
def _fetch_market_news_items(ticker_str):
    try:
        news_list = yf.Ticker(ticker_str).news
        items = []
        for idx, raw in enumerate((news_list or [])[:_US_MARKET_NEWS_PER_TICKER_LIMIT]):
            title = str(raw.get("title") or raw.get("content", {}).get("title") or "").strip()
            if not title:
                continue
            link = str(raw.get("link") or raw.get("content", {}).get("canonicalUrl", {}).get("url") or "").strip()
            publisher = str(raw.get("publisher") or raw.get("content", {}).get("provider", {}).get("displayName") or "Yahoo Finance").strip()
            timestamp = raw.get("providerPublishTime", 0) or 0
            if not timestamp:
                raw_date = str(raw.get("content", {}).get("pubDate") or raw.get("date") or "").strip()
                parsed_date = pd.to_datetime(raw_date, errors="coerce")
                if not pd.isna(parsed_date):
                    timestamp = int(parsed_date.timestamp())
            raw_summary = (
                raw.get("summary")
                or raw.get("description")
                or raw.get("content", {}).get("summary")
                or raw.get("content", {}).get("description")
                or raw.get("content", {}).get("snippet")
                or ""
            )
            content_summary = _clean_market_news_excerpt(raw_summary)
            date_label = datetime.fromtimestamp(timestamp).strftime("%m-%d %H:%M") if timestamp else ""
            items.append(
                {
                    "raw_key": f"{ticker_str}-{idx}-{timestamp}",
                    "ticker": str(ticker_str or "").strip().upper(),
                    "title": title,
                    "publisher": publisher or "Yahoo Finance",
                    "date": date_label,
                    "timestamp": int(timestamp) if timestamp else 0,
                    "link": link,
                    "content_summary": content_summary,
                }
            )
        return {"items": items, "error": None, "rate_limited": False}
    except Exception as err:
        return {"items": [], "error": str(err), "rate_limited": _is_market_news_rate_limited(err)}


def _collect_market_news(news_universe, snapshot_lookup, gainers, losers):
    reference_dt = datetime.now()
    cutoff_dt = reference_dt - timedelta(hours=_US_MARKET_NEWS_LOOKBACK_HOURS)
    mover_symbols = {str(row.get("symbol") or "").strip().upper() for row in gainers + losers if row.get("symbol")}
    mega_cap_symbols = {str(symbol).strip().upper() for symbol in _US_MARKET_MEGA_CAPS}
    benchmark_symbols = {"SPY", "QQQ"}
    systemic_symbols = {str(symbol).strip().upper() for symbol in _US_MARKET_SYSTEMIC_NEWS_SYMBOLS}
    deduped = {}
    rate_limited = False

    for ticker in _ordered_unique(_normalize_market_symbol(symbol) for symbol in news_universe):
        payload = _fetch_market_news_items(ticker)
        rate_limited = rate_limited or bool(payload.get("rate_limited"))
        for raw_item in payload.get("items", []):
            timestamp = int(raw_item.get("timestamp") or 0)
            if not timestamp:
                continue
            try:
                if datetime.fromtimestamp(timestamp) < cutoff_dt:
                    continue
            except Exception:
                continue
            title = str(raw_item.get("title") or "").strip()
            if not title:
                continue
            dedupe_key = _normalize_market_news_url(raw_item.get("link")) or _normalize_market_news_title(title)
            if not dedupe_key:
                continue
            ticker_symbol = str(raw_item.get("ticker") or ticker).strip().upper()
            tag = _classify_market_news_tag(title, ticker_symbol)
            snapshot = snapshot_lookup.get(ticker_symbol, {})
            item = {
                "key": dedupe_key,
                "ticker": ticker_symbol,
                "display_label": _market_news_display_label(ticker_symbol),
                "title": title,
                "publisher": str(raw_item.get("publisher") or "Yahoo Finance").strip() or "Yahoo Finance",
                "date": str(raw_item.get("date") or "").strip() or datetime.fromtimestamp(timestamp).strftime("%m-%d %H:%M"),
                "timestamp": timestamp,
                "link": str(raw_item.get("link") or "").strip(),
                "body_excerpt": str(raw_item.get("content_summary") or "").strip(),
                "source_depth": "snippet" if str(raw_item.get("content_summary") or "").strip() else "headline",
                "tag": tag,
                "change_pct": snapshot.get("change_pct"),
                "is_mover": ticker_symbol in mover_symbols,
                "is_megacap": ticker_symbol in mega_cap_symbols,
                "is_benchmark": ticker_symbol in benchmark_symbols,
                "is_systemic": ticker_symbol in systemic_symbols,
            }
            item["section"] = _classify_market_news_section(item)
            item["body_excerpt"] = _clean_market_news_excerpt(item.get("body_excerpt"))
            item["source_depth"] = item.get("source_depth") or ("snippet" if item.get("body_excerpt") else "headline")
            item.update(_build_market_news_structured_fields(item))
            item["score"] = _score_market_news_item(item, mover_symbols, mega_cap_symbols, benchmark_symbols, systemic_symbols, reference_dt)
            existing = deduped.get(dedupe_key)
            if existing is None or item["score"] > existing["score"]:
                deduped[dedupe_key] = item

    ranked = sorted(
        deduped.values(),
        key=lambda item: (item.get("score", 0), item.get("timestamp", 0)),
        reverse=True,
    )
    display_keys = set()
    for section_name in _US_MARKET_NEWS_SECTION_ORDER:
        section_items = [item for item in ranked if item.get("section") == section_name][:_US_MARKET_NEWS_SECTION_MAX_ITEMS]
        for item in section_items:
            display_keys.add(str(item.get("key") or "").strip())
    fetched_articles = 0
    for item in ranked:
        item_key = str(item.get("key") or "").strip()
        if item_key not in display_keys or fetched_articles >= _US_MARKET_NEWS_ARTICLE_FETCH_LIMIT:
            item["body_excerpt"] = _clean_market_news_excerpt(item.get("body_excerpt"))
            item["source_depth"] = item.get("source_depth") or ("snippet" if item.get("body_excerpt") else "headline")
            item.update(_build_market_news_structured_fields(item))
            continue
        current_excerpt = _clean_market_news_excerpt(item.get("body_excerpt"))
        current_score = _market_news_excerpt_score(current_excerpt, item.get("title"))
        if current_excerpt and current_score >= _US_MARKET_NEWS_GOOD_EXCERPT_SCORE:
            item["body_excerpt"] = current_excerpt
            item["source_depth"] = item.get("source_depth") or "snippet"
            item.update(_build_market_news_structured_fields(item))
            continue
        article_payload = _fetch_market_news_article_excerpt(item.get("link"))
        article_excerpt = _clean_market_news_excerpt(article_payload.get("excerpt"))
        if _market_news_excerpt_score(article_excerpt, item.get("title")) > _market_news_excerpt_score(current_excerpt, item.get("title")):
            item["body_excerpt"] = article_excerpt
            item["source_depth"] = article_payload.get("source_depth") or "article"
        elif current_excerpt:
            item["body_excerpt"] = current_excerpt
            item["source_depth"] = item.get("source_depth") or "snippet"
        else:
            item["source_depth"] = "headline"
        item.update(_build_market_news_structured_fields(item))
        fetched_articles += 1
    selected = []
    per_ticker = Counter()
    for section_name in ["거시·연준", "외부 변수", "원자재·암호", "실적·개별주", "시장 총평"]:
        picked = _pick_market_news_section_item(ranked, section_name)
        if not picked:
            continue
        ticker = str(picked.get("ticker") or "").strip().upper()
        if per_ticker[ticker] >= 2 or picked in selected:
            continue
        selected.append(picked)
        per_ticker[ticker] += 1
        if len(selected) >= _US_MARKET_NEWS_MAX_ITEMS:
            break
    for item in ranked:
        ticker = str(item.get("ticker") or "").strip().upper()
        if item in selected:
            continue
        if per_ticker[ticker] >= 2:
            continue
        selected.append(item)
        per_ticker[ticker] += 1
        if len(selected) >= _US_MARKET_NEWS_MAX_ITEMS:
            break
    return {"items": selected, "ranked_items": ranked, "rate_limited": rate_limited}


def _fallback_market_news_takeaway(item):
    return _build_market_news_takeaway_ko(item)


def _fallback_market_news_summary(news_items, rate_limited=False):
    if not news_items:
        return "오늘 시장 핵심 뉴스는 제한적으로 확인됐습니다."
    lead_items = news_items[:_US_MARKET_NEWS_SECTION_SUMMARY_ITEMS]
    event_counts = Counter(item.get("event_type") or _detect_market_news_event_type(_market_news_parse_text(item.get("title"), item.get("body_excerpt")), item.get("tag")) for item in lead_items)
    top_events = [_market_news_event_label_ko(event) for event, _ in event_counts.most_common(2) if event]
    focus_labels = _ordered_unique(item.get("display_label") or item.get("ticker") or "시장" for item in lead_items)[:3]
    focus_parts = []
    if sum(1 for item in lead_items if item.get("section") in {"거시·연준", "외부 변수", "원자재·암호"}) >= max(1, len(lead_items) // 2):
        focus_parts.append("거시 변수")
    if sum(1 for item in lead_items if item.get("is_megacap")) >= max(1, len(lead_items) // 2):
        focus_parts.append("메가캡")
    if sum(1 for item in lead_items if item.get("is_mover")) >= max(1, len(lead_items) // 2):
        focus_parts.append("주요 등락주")
    if top_events:
        event_label = "·".join(top_events)
        focus_label = "와 ".join(focus_parts) if focus_parts else ("·".join(focus_labels[:2]) if focus_labels else "시장 핵심 종목")
        return f"{event_label} 이슈가 {focus_label} 중심으로 시장을 이끌었습니다."
    if rate_limited:
        return "오늘 시장 핵심 뉴스는 제한적으로 확인됐습니다."
    if focus_labels:
        return f"{'·'.join(focus_labels[:2])} 관련 뉴스가 시장 심리에 영향을 준 하루였습니다."
    return "시장 핵심 종목과 거시 변수 뉴스가 시장 심리에 영향을 준 하루였습니다."


@st.cache_data(ttl=1800, show_spinner=False)
def _generate_market_news_ai_copy(market_date_key, news_json):
    if not GEMINI_API_KEY:
        return {}
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-flash-latest")
        prompt = (
            "You are a US market news editor. Answer in concise Korean.\n"
            "Return pure JSON only.\n"
            'Format: {"summary":"...","sections":[{"section":"...","summary":"..."}],"items":[{"key":"...","title_ko":"...","fact_ko":"...","impact_ko":"...","takeaway":"..."}]}\n'
            "Rules:\n"
            "- summary: one short sentence.\n"
            "- sections: one short sentence for each section.\n"
            "- items: one Korean title, one fact phrase, one impact phrase, and one final one-line takeaway for each key.\n"
            "- Each item may include a source link. If the link is accessible to you, use it to better understand the article before writing the Korean summary.\n"
            "- If the link is not accessible, rely on the headline, body_excerpt, and metadata only.\n"
            "- Use headline, link, body_excerpt, ticker, display_label, section, tag, publisher, time, change_pct, source_depth, event_type, event_direction, key_fact_ko, and market_impact_ko.\n"
            "- Do not fabricate facts that are not supported by the article link or provided metadata.\n"
            "- Prefer smooth, natural Korean over rigid label-like phrasing.\n"
            "- Do not mechanically list isolated numbers like 1.95%·1.75% without explaining what they refer to.\n"
            "- If a news item is only a comparison/explainer article, say its direct market impact is limited instead of overstating it.\n"
            "- Translate headlines naturally into Korean when possible.\n"
            "- Keep numbers, tickers, company names, and product names intact.\n"
            "- item takeaway should be one smooth Korean line that tells what happened and why it matters.\n"
            "- section summary should explain the actual situation in plain Korean using the top items in that section.\n"
            "- For 시장 총평, prioritize index moves and sector breadth over generic market-update articles.\n"
            "- Do not mention information absent from the input.\n"
            f"- market_date_key: {market_date_key}\n"
            f"- data: {news_json}\n"
        )
        response = model.generate_content(prompt)
        raw_text = getattr(response, "text", "") or str(response)
        parsed = json.loads(_extract_json_object(raw_text))
        section_summaries = []
        for row in parsed.get("sections", []):
            if not isinstance(row, dict):
                continue
            section = str(row.get("section", "")).strip()
            summary = str(row.get("summary", "")).strip()
            if not section or not summary:
                continue
            section_summaries.append({"section": section, "summary": summary})
        item_copies = []
        raw_items = parsed.get("items", [])
        if not raw_items and isinstance(parsed.get("takeaways"), list):
            raw_items = [{"key": row.get("key"), "takeaway": row.get("text")} for row in parsed.get("takeaways", []) if isinstance(row, dict)]
        for row in raw_items:
            if not isinstance(row, dict):
                continue
            key = str(row.get("key", "")).strip()
            title_ko = str(row.get("title_ko", "")).strip()
            fact_ko = str(row.get("fact_ko", "")).strip()
            impact_ko = str(row.get("impact_ko", "")).strip()
            takeaway = str(row.get("takeaway", "") or row.get("text", "")).strip()
            if not key or not takeaway:
                continue
            item_copies.append({"key": key, "title_ko": title_ko, "fact_ko": fact_ko, "impact_ko": impact_ko, "takeaway": takeaway})
        return {
            "summary": str(parsed.get("summary", "")).strip(),
            "sections": section_summaries,
            "items": item_copies,
        }
    except Exception:
        return {}


def _build_market_snapshot_news_summary(benchmark_snapshots, sector_rows):
    spy = benchmark_snapshots.get("SPY", {}).get("change_pct")
    qqq = benchmark_snapshots.get("QQQ", {}).get("change_pct")
    dia = benchmark_snapshots.get("DIA", {}).get("change_pct")
    breadth = sum(1 for row in sector_rows if (row.get("change_pct") or 0) > 0)
    total = len(sector_rows) or len(_US_SECTOR_ETFS)
    strongest = max(sector_rows, key=lambda row: row.get("change_pct") if row.get("change_pct") is not None else -999) if sector_rows else None
    weakest = min(sector_rows, key=lambda row: row.get("change_pct") if row.get("change_pct") is not None else 999) if sector_rows else None
    text = (
        f"다우 {_format_change_pct(dia)} / S&P 500 {_format_change_pct(spy)} / 나스닥 {_format_change_pct(qqq)}. "
        f"상승 섹터 {breadth}/{total}개"
    )
    if strongest and weakest:
        text += f", {strongest['label']} 강세 · {weakest['label']} 약세 흐름이었습니다."
    return text


def _build_market_news_section_pool(ranked_items, section_name):
    items = [item for item in ranked_items if item.get("section") == section_name]
    return {"count": len(items), "items": items}


def _fallback_market_news_section_summary(section_label, section_items, fallback_text):
    if not section_items:
        return fallback_text
    top_items = section_items[:_US_MARKET_NEWS_SECTION_SUMMARY_ITEMS]
    high_signal_items = [
        item for item in top_items
        if not _is_low_signal_market_news_item(item) and str(item.get("event_type") or "") != "market_update"
    ]
    issue_text = _build_market_news_section_issue_text(high_signal_items or top_items, limit=2)
    event_counts = Counter(item.get("event_type") or _detect_market_news_event_type(_market_news_parse_text(item.get("title"), item.get("body_excerpt")), item.get("tag")) for item in top_items)
    dominant_event = next(iter(event_counts.keys()), "")
    dominant_label = _market_news_event_label_ko(dominant_event)
    if section_label == "시장 총평":
        if high_signal_items and issue_text:
            return f"시장 총평에서는 {issue_text}가 부각됐고, 관련 헤드라인이 지수 방향과 시장 폭 판단 재료가 됐습니다."
        return fallback_text
    if section_label == "거시·연준":
        if issue_text:
            return f"거시·연준에서는 {issue_text}가 부각됐고, 금리 기대 재조정의 핵심 변수로 작용했습니다."
        return f"거시·연준에서는 {dominant_label} 이슈가 중심이었고, 금리 기대를 다시 흔들었습니다."
    if section_label == "실적·개별주":
        if issue_text:
            return f"실적·개별주에서는 {issue_text}가 부각됐고, 개별주 변동성 확대 재료가 됐습니다."
        return f"실적·개별주에서는 {dominant_label} 뉴스가 중심이었고, 개별주 변동성을 키웠습니다."
    if section_label == "외부 변수":
        if issue_text:
            return f"외부 변수에서는 {issue_text}가 부각됐고, 위험회피 심리를 자극하는 변수로 작용했습니다."
        return f"외부 변수에서는 {dominant_label} 이슈가 이어졌고, 시장 경계 심리를 자극했습니다."
    if section_label == "원자재·암호":
        if issue_text:
            return f"원자재·암호에서는 {issue_text}가 부각됐고, 관련 자산 민감도를 키우는 요인이었습니다."
        return f"원자재·암호에서는 {dominant_label} 뉴스가 중심이었고, 관련 자산 민감도를 키웠습니다."
    return fallback_text


def _market_news_section_tone(items, fallback="neutral"):
    tones = [_market_news_item_tone(item) for item in items]
    if tones:
        return _resolve_market_tone(*(tones + [fallback]))
    return fallback


def _resolve_market_news_section_summary(section_label, section_items, ai_summary, fallback_summary):
    summary = str(ai_summary or "").strip()
    if summary and not _is_generic_market_news_section_summary(summary):
        return summary
    return _fallback_market_news_section_summary(section_label, section_items, fallback_summary)


def _build_market_news_metric(label, value, delta, note, tone="neutral"):
    return {
        "label": str(label or "").strip(),
        "value": str(value or "").strip() or "0건",
        "delta": str(delta or "").strip(),
        "note": str(note or "").strip(),
        "tone": tone if tone in {"positive", "negative", "neutral"} else "neutral",
    }


def _pick_market_news_section_item(items, section_name, used_keys=None):
    used_keys = used_keys or set()
    for item in items:
        if item.get("section") != section_name:
            continue
        if item.get("key") in used_keys:
            continue
        return item
    return None


def _build_market_news_section_entry(section_label, section_pool, section_summary_map, item_copy_map, fallback_summary, fallback_tone="neutral"):
    section_items = list((section_pool or {}).get("items") or [])
    rendered_items = []
    for item in section_items:
        item_copy = item_copy_map.get(str(item.get("key") or "").strip(), {})
        structured = _build_market_news_structured_fields(item)
        title_raw = str(item.get("title") or "").strip()
        title_ko = str(item_copy.get("title_ko") or "").strip() or _fallback_market_news_title_ko(item)
        key_fact_ko = str(item_copy.get("fact_ko") or "").strip() or str(item.get("key_fact_ko") or structured.get("key_fact_ko") or "").strip()
        market_impact_ko = str(item_copy.get("impact_ko") or "").strip() or str(item.get("market_impact_ko") or structured.get("market_impact_ko") or "").strip()
        takeaway_ko = str(item_copy.get("takeaway") or "").strip() or _fallback_market_news_takeaway(item)
        rendered_items.append(
            {
                "key": str(item.get("key") or "").strip(),
                "display_label": item.get("display_label") or item.get("ticker") or "시장",
                "tag": item.get("tag") or "시장",
                "publisher": item.get("publisher") or "Yahoo Finance",
                "date": item.get("date") or "시간 미상",
                "title_ko": title_ko,
                "title_raw": title_raw if _should_show_market_news_raw_title(title_ko, title_raw) else "",
                "body_excerpt": item.get("body_excerpt") or "",
                "event_type": item.get("event_type") or structured.get("event_type") or "",
                "event_direction": item.get("event_direction") or structured.get("event_direction") or "",
                "subject": item.get("subject") or structured.get("subject") or item.get("display_label") or item.get("ticker") or "시장",
                "key_fact_ko": key_fact_ko,
                "market_impact_ko": market_impact_ko,
                "source_depth": item.get("source_depth") or "headline",
                "takeaway_ko": takeaway_ko,
                "link": item.get("link") or "",
                "tone": _market_news_item_tone(item),
            }
        )
    return {
        "id": _US_MARKET_NEWS_SECTION_IDS.get(section_label, _normalize_market_news_title(section_label).replace(" ", "_") or "market_news_section"),
        "label": section_label,
        "summary_ko": _resolve_market_news_section_summary(section_label, section_items, section_summary_map.get(section_label), fallback_summary),
        "count": int((section_pool or {}).get("count") or len(section_items)),
        "tone": _market_news_section_tone(section_items, fallback_tone),
        "expanded": False,
        "items": rendered_items,
    }


def _build_market_news_card(market_date_key, benchmark_snapshots, macro_snapshots, sector_rows, gainers, losers, news_bundle):
    news_items = list(news_bundle.get("items") or [])
    ranked_items = list(news_bundle.get("ranked_items") or news_items)
    rate_limited = bool(news_bundle.get("rate_limited"))
    section_pools = {section_label: _build_market_news_section_pool(ranked_items, section_label) for section_label in _US_MARKET_NEWS_SECTION_ORDER}
    ai_sections = []
    for section_label in _US_MARKET_NEWS_SECTION_ORDER:
        section_items_payload = []
        for item in section_pools[section_label]["items"][:_US_MARKET_NEWS_AI_ITEMS_PER_SECTION]:
            section_items_payload.append(
                {
                    "key": item.get("key"),
                    "ticker": item.get("ticker"),
                    "display_label": item.get("display_label"),
                    "section": item.get("section"),
                    "tag": item.get("tag"),
                    "title": item.get("title"),
                    "link": item.get("link"),
                    "body_excerpt": item.get("body_excerpt"),
                    "publisher": item.get("publisher"),
                    "time": item.get("date"),
                    "change_pct": item.get("change_pct"),
                    "source_depth": item.get("source_depth"),
                    "event_type": item.get("event_type"),
                    "event_direction": item.get("event_direction"),
                    "subject": item.get("subject"),
                    "key_fact_ko": item.get("key_fact_ko"),
                    "market_impact_ko": item.get("market_impact_ko"),
                }
            )
        if section_items_payload:
            ai_sections.append({"section": section_label, "items": section_items_payload})
    ai_payload = {"market_date": market_date_key, "sections": ai_sections}
    ai_copy = _generate_market_news_ai_copy(market_date_key, json.dumps(ai_payload, ensure_ascii=False)) if ai_sections else {}
    item_copy_map = {
        str(item.get("key", "")).strip(): item
        for item in ai_copy.get("items", [])
        if isinstance(item, dict) and str(item.get("key", "")).strip()
    }
    section_summary_map = {
        str(item.get("section", "")).strip(): str(item.get("summary", "")).strip()
        for item in ai_copy.get("sections", [])
        if isinstance(item, dict) and str(item.get("section", "")).strip() and str(item.get("summary", "")).strip()
    }

    subtitle = ai_copy.get("summary") or _fallback_market_news_summary(ranked_items[: max(_US_MARKET_NEWS_SECTION_SUMMARY_ITEMS, _US_MARKET_NEWS_MAX_ITEMS)], rate_limited=rate_limited)

    top_gainer = gainers[0] if gainers else None
    top_loser = losers[0] if losers else None
    tnx = macro_snapshots.get("10Y", {})
    dxy = macro_snapshots.get("DXY", {})
    wti = macro_snapshots.get("WTI", {})
    gold = macro_snapshots.get("Gold", {})
    btc = macro_snapshots.get("BTC", {})
    market_fallback = _build_market_snapshot_news_summary(benchmark_snapshots, sector_rows)
    macro_fallback = (
        f"10Y {((tnx.get('price') or 0) / 10):.2f}% / DXY {_format_change_pct(dxy.get('change_pct'))} / "
        f"달러 {_format_change_pct(macro_snapshots.get('USDKRW', {}).get('change_pct'))} 흐름이 핵심 변수였습니다."
    )
    stock_fallback = (
        f"주요 종목 뉴스는 제한적이었지만 {top_gainer['symbol']} {_format_change_pct(top_gainer.get('change_pct'))}"
        if top_gainer else "실적·개별주 관련 핵심 헤드라인은 제한적으로 확인됐습니다."
    )
    if top_gainer and top_loser:
        stock_fallback += f" / {top_loser['symbol']} {_format_change_pct(top_loser.get('change_pct'))}가 두드러졌습니다."
    risk_fallback = (
        f"지정학·정책 헤드라인은 제한적이었지만 WTI {_format_change_pct(wti.get('change_pct'))} / 금 {_format_change_pct(gold.get('change_pct'))} 움직임은 체크가 필요합니다."
    )
    commodity_fallback = (
        f"WTI {_format_change_pct(wti.get('change_pct'))} / 금 {_format_change_pct(gold.get('change_pct'))} / 비트코인 {_format_change_pct(btc.get('change_pct'))} 흐름이 원자재·암호 섹터를 설명합니다."
    )
    section_fallbacks = {
        "시장 총평": market_fallback,
        "거시·연준": macro_fallback,
        "실적·개별주": stock_fallback,
        "외부 변수": risk_fallback,
        "원자재·암호": commodity_fallback,
    }
    section_fallback_tones = {
        "시장 총평": _tone_from_change(benchmark_snapshots.get("SPY", {}).get("change_pct")),
        "거시·연준": "neutral",
        "실적·개별주": "neutral",
        "외부 변수": "negative" if abs((wti.get("change_pct") or 0)) >= 1.5 else "neutral",
        "원자재·암호": _resolve_market_tone(_tone_from_change(wti.get("change_pct"), inverse=True, neutral_band=0.35), _tone_from_change(btc.get("change_pct"), neutral_band=0.35)),
    }
    sections = [
        _build_market_news_section_entry(
            section_label,
            section_pools.get(section_label),
            section_summary_map,
            item_copy_map,
            section_fallbacks.get(section_label, "오늘 핵심 뉴스는 제한적으로 확인됐습니다."),
            section_fallback_tones.get(section_label, "neutral"),
        )
        for section_label in _US_MARKET_NEWS_SECTION_ORDER
    ]
    bullets = []
    if rate_limited:
        bullets.append(_build_market_bullet("뉴스 데이터 일부는 Yahoo Finance 요청 제한의 영향을 받았습니다.", "negative"))

    earnings_count = sum(1 for item in ranked_items if item.get("tag") in {"실적", "가이던스", "파트너십", "M&A", "AI"})
    macro_count = sum(1 for item in ranked_items if item.get("tag") in {"연준", "경제지표", "금리"})
    risk_count = sum(1 for item in ranked_items if item.get("tag") in {"규제", "정책/정치", "지정학", "소송"})
    commodity_count = sum(1 for item in ranked_items if item.get("tag") in {"원자재", "암호화폐"})
    breadth = sum(1 for row in sector_rows if (row.get("change_pct") or 0) > 0)
    total = len(sector_rows) or len(_US_SECTOR_ETFS)
    metrics = [
        _build_market_news_metric("시장 총평", f"{breadth}/{total}", "상승 섹터", "3대 지수·시장 폭", "positive" if breadth >= total / 2 else "negative"),
        _build_market_news_metric("거시·연준", f"{macro_count}건", "금리/지표", "Fed·경제지표", "negative" if macro_count else "neutral"),
        _build_market_news_metric("실적·개별주", f"{earnings_count}건", "실적/계약", "빅테크·주도주", "positive" if earnings_count else "neutral"),
        _build_market_news_metric("외부 변수", f"{risk_count}건", "정책/지정학", "전쟁·관세·규제", "negative" if risk_count else "neutral"),
        _build_market_news_metric("원자재·암호", f"{commodity_count}건", "WTI/Gold/BTC", "유가·금·비트코인", _resolve_market_tone(_tone_from_change(wti.get("change_pct"), inverse=True, neutral_band=0.35), _tone_from_change(btc.get("change_pct"), neutral_band=0.35))),
    ]
    item_tones = [_market_news_item_tone(item) for item in ranked_items]
    market_tone = _tone_from_change(benchmark_snapshots.get("SPY", {}).get("change_pct"))
    tone = _resolve_market_tone(*(item_tones + [market_tone])) if item_tones else "neutral"
    return {
        "id": "market_news",
        "title": "핵심 뉴스",
        "subtitle": subtitle,
        "metrics": metrics,
        "bullets": bullets,
        "sections": sections,
        "notice": "뉴스 데이터 일부는 Yahoo Finance 요청 제한의 영향을 받았습니다." if rate_limited else "",
        "tone": tone,
        "chart_hint": "시장 총평 / 거시·연준 / 실적·개별주 / 외부 변수 / 원자재·암호",
        "duration_ms": _US_MARKET_TEXT_HEAVY_DURATION,
    }


@st.cache_data(ttl=1800, show_spinner=False)
def _download_market_history(tickers, period=_US_MARKET_HISTORY_PERIOD):
    expanded = []
    for ticker in tickers:
        expanded.extend(_market_symbol_candidates(ticker))
    symbols = tuple(_ordered_unique(symbol for symbol in expanded if symbol))
    if not symbols:
        return pd.DataFrame()

    chunk_size = max(1, int(_US_MARKET_DOWNLOAD_CHUNK_SIZE or 1))
    chunks = [symbols[idx:idx + chunk_size] for idx in range(0, len(symbols), chunk_size)]
    downloaded_frames = []
    for chunk in chunks:
        try:
            history = yf.download(
                tickers=list(chunk),
                period=period,
                interval="1d",
                group_by="ticker",
                auto_adjust=False,
                progress=False,
                threads=True,
            )
        except Exception:
            continue

        if not isinstance(history, pd.DataFrame) or history.empty:
            continue

        chunk_frame = history.sort_index()
        if not isinstance(chunk_frame.columns, pd.MultiIndex) and len(chunk) == 1:
            symbol = str(chunk[0]).strip().upper()
            if symbol:
                chunk_frame.columns = pd.MultiIndex.from_product([[symbol], list(chunk_frame.columns)])
        downloaded_frames.append(chunk_frame)

    if not downloaded_frames:
        return pd.DataFrame()

    merged = pd.concat(downloaded_frames, axis=1)
    if isinstance(merged.columns, pd.MultiIndex):
        merged = merged.loc[:, ~merged.columns.duplicated()]
    else:
        merged = merged.loc[:, ~merged.columns.duplicated()]
    return merged.sort_index()


@st.cache_data(ttl=21600, show_spinner=False)
def _generate_us_market_ai_copy(market_date_key, summary_json):
    if not GEMINI_API_KEY:
        return {}
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-flash-latest")
        prompt = (
            "You are a US market close editor. Use only the JSON data below and answer in concise Korean.\n"
            "Return pure JSON only.\n"
            'Format: {"headline":"...","drivers":["...","...","..."],"insight_short_view":"...","insight_deep_dive":["...","..."],"insight_strategy":["...","..."],"watchlist":["...","...","..."]}\n'
            "Rules:\n"
            "- headline: one short but explanatory sentence.\n"
            "- drivers: three to four short bullets that explain what moved the market and why it mattered.\n"
            "- insight_short_view: one sharp line that explains what the market cared about most today.\n"
            "- insight_deep_dive: two to three short lines that explain the narrative, divergence, or hidden context behind the move.\n"
            "- insight_strategy: two to three action-oriented lines for next-session execution (what to do first).\n"
            "- watchlist: three to four actionable checkpoints, written as concrete checks/triggers.\n"
            "- Prefer explanation over slogans; mention cause and implication together.\n"
            "- Use decisive, behavior-oriented Korean phrasing instead of abstract commentary when possible.\n"
            "- If the JSON includes news_context or divergence notes, use them to explain what mattered beneath the index move.\n"
            "- Do not invent historical statistics that are not present in the data.\n"
            "- Do not mention unverified news or events.\n"
            f"- market_date_key: {market_date_key}\n"
            f"- data: {summary_json}\n"
        )
        response = model.generate_content(prompt)
        raw_text = getattr(response, "text", "") or str(response)
        parsed = json.loads(_extract_json_object(raw_text))
        insight_short_view = str(parsed.get("insight_short_view", "")).strip()
        if not insight_short_view:
            insight_short_view = str(parsed.get("insight", "")).strip()
        drivers = _coerce_market_text_list(parsed.get("drivers"), max_items=4)
        watchlist = _coerce_market_text_list(parsed.get("watchlist"), max_items=4)
        return {
            "headline": str(parsed.get("headline", "")).strip(),
            "drivers": drivers,
            "insight": insight_short_view,
            "insight_short_view": insight_short_view,
            "insight_deep_dive": _coerce_market_text_list(parsed.get("insight_deep_dive"), max_items=3),
            "insight_strategy": _coerce_market_text_list(parsed.get("insight_strategy"), max_items=3),
            "watchlist": watchlist,
        }
    except Exception:
        return {}


@st.cache_data(ttl=_US_MARKET_DAILY_PAYLOAD_TTL_SEC, show_spinner=False)
def build_us_market_daily_payload():
    benchmark_symbols = tuple(symbol for symbol, _ in _US_MARKET_BENCHMARKS)
    macro_symbols = tuple(symbol for symbol, _ in _US_MARKET_MACRO)
    sector_symbols = tuple(symbol for symbol, _ in _US_SECTOR_ETFS)
    mover_etf_payload = _resolve_market_mover_etf_payload()
    mover_universe = _market_mover_universe(mover_etf_payload)
    if mover_etf_payload.get("errors"):
        print(f"[MARKET-MOVER-ETF] {' | '.join(str(item) for item in mover_etf_payload.get('errors', []))}")

    benchmark_history = _download_market_history(benchmark_symbols + macro_symbols + sector_symbols)
    mover_history = _download_market_history(mover_universe, period=_US_MARKET_MOVER_HISTORY_PERIOD)

    benchmark_snapshots = {}
    for symbol, _ in _US_MARKET_BENCHMARKS:
        label = "VIX" if symbol == "^VIX" else symbol
        benchmark_snapshots[label] = _build_snapshot(_extract_symbol_frame(benchmark_history, symbol))

    macro_snapshots = {}
    macro_labels = {"^TNX": "10Y", "DX-Y.NYB": "DXY", "KRW=X": "USDKRW", "GLD": "Gold", "CL=F": "WTI", "BTC-USD": "BTC"}
    for symbol, _ in _US_MARKET_MACRO:
        macro_snapshots[macro_labels[symbol]] = _build_snapshot(_extract_symbol_frame(benchmark_history, symbol))
    macro_snapshot_lookup = {
        "^TNX": macro_snapshots.get("10Y", {}),
        "DX-Y.NYB": macro_snapshots.get("DXY", {}),
        "KRW=X": macro_snapshots.get("USDKRW", {}),
        "GLD": macro_snapshots.get("Gold", {}),
        "CL=F": macro_snapshots.get("WTI", {}),
        "BTC-USD": macro_snapshots.get("BTC", {}),
    }

    sector_rows = []
    for symbol, label in _US_SECTOR_ETFS:
        snapshot = _build_snapshot(_extract_symbol_frame(benchmark_history, symbol))
        sector_rows.append({"symbol": symbol, "label": label, "snapshot": snapshot, "change_pct": snapshot.get("change_pct")})
    sector_rows = [row for row in sector_rows if row.get("snapshot")]
    sector_sorted = sorted(sector_rows, key=lambda row: row.get("change_pct") if row.get("change_pct") is not None else -999, reverse=True)
    sector_snapshot_lookup = {row["symbol"]: row["snapshot"] for row in sector_rows}

    movers = []
    for symbol in mover_universe:
        snapshot = _build_snapshot(_extract_symbol_frame(mover_history, symbol))
        if not snapshot or snapshot.get("change_pct") is None:
            continue
        movers.append({"symbol": symbol, "snapshot": snapshot, "change_pct": snapshot.get("change_pct")})
    movers_sorted = sorted(movers, key=lambda row: row["change_pct"], reverse=True)
    analysis_actions = _build_market_analysis_actions(movers_sorted, limit=_US_MARKET_ANALYSIS_ACTION_COUNT)
    gainers = movers_sorted[:_US_MARKET_TOP_MOVER_CARD_COUNT]
    losers = list(reversed(movers_sorted[-_US_MARKET_TOP_MOVER_CARD_COUNT:])) if movers_sorted else []
    gainers_detail = [_build_mover_detail_row(row) for row in movers_sorted[:_US_MARKET_TOP_MOVER_DETAIL_COUNT]]
    losers_detail_source = list(reversed(movers_sorted[-_US_MARKET_TOP_MOVER_DETAIL_COUNT:])) if movers_sorted else []
    losers_detail = [_build_mover_detail_row(row) for row in losers_detail_source]
    snapshot_lookup = dict(benchmark_snapshots)
    snapshot_lookup["^VIX"] = benchmark_snapshots.get("VIX", {})
    snapshot_lookup.update(macro_snapshot_lookup)
    snapshot_lookup.update(sector_snapshot_lookup)
    snapshot_lookup.update({row["symbol"]: row["snapshot"] for row in movers})

    market_dt = None
    for candidate in [benchmark_snapshots.get("SPY", {}).get("date"), benchmark_snapshots.get("QQQ", {}).get("date")]:
        if candidate is not None:
            market_dt = candidate
            break
    market_date_key = market_dt.strftime("%Y-%m-%d") if market_dt is not None else datetime.utcnow().strftime("%Y-%m-%d")
    news_universe = _build_market_news_universe(gainers, losers)
    market_news_bundle = _collect_market_news(news_universe, snapshot_lookup, gainers, losers)

    market_regime = _build_market_regime(benchmark_snapshots, macro_snapshots, sector_sorted)
    market_structure = _describe_market_structure(benchmark_snapshots, macro_snapshots, sector_sorted)
    qqq_vs_spy = market_regime.get("qqq_vs_spy")
    iwm_vs_spy = market_regime.get("iwm_vs_spy")
    driver_candidates = _build_driver_candidates(benchmark_snapshots, macro_snapshots, sector_sorted)
    insight_news_context = _build_market_insight_news_context(market_news_bundle)
    divergence_notes = _build_market_divergence_notes(benchmark_snapshots, macro_snapshots, sector_sorted, market_regime, market_structure)
    strategy_points = _build_market_strategy_points(benchmark_snapshots, macro_snapshots, sector_sorted, market_regime, news_context=insight_news_context)
    fallback_insight = _fallback_market_insight(
        benchmark_snapshots,
        macro_snapshots,
        sector_sorted,
        news_context=insight_news_context,
        market_regime=market_regime,
        market_structure=market_structure,
    )

    summary_payload = {
        "market_date": market_date_key,
        "benchmarks": {label: snapshot.get("change_pct") for label, snapshot in benchmark_snapshots.items()},
        "macro": {
            "10Y_bps": ((macro_snapshots.get("10Y", {}).get("price") or 0) - (macro_snapshots.get("10Y", {}).get("prev_close") or 0)) * 10,
            "DXY_pct": macro_snapshots.get("DXY", {}).get("change_pct"),
            "USDKRW_pct": macro_snapshots.get("USDKRW", {}).get("change_pct"),
            "Gold_pct": macro_snapshots.get("Gold", {}).get("change_pct"),
            "WTI_pct": macro_snapshots.get("WTI", {}).get("change_pct"),
            "BTC_pct": macro_snapshots.get("BTC", {}).get("change_pct"),
        },
        "relative_strength": {
            "QQQ_vs_SPY": qqq_vs_spy,
            "IWM_vs_SPY": iwm_vs_spy,
        },
        "sector_top": [f"{row['symbol']} {row['change_pct']:+.2f}%" for row in sector_sorted[:3] if row.get("change_pct") is not None],
        "sector_bottom": [f"{row['symbol']} {row['change_pct']:+.2f}%" for row in sector_sorted[-3:] if row.get("change_pct") is not None],
        "gainers": [f"{row['symbol']} {row['change_pct']:+.2f}%" for row in gainers],
        "losers": [f"{row['symbol']} {row['change_pct']:+.2f}%" for row in losers],
        "breadth": {
            "up": sum(1 for row in sector_sorted if (row.get("change_pct") or 0) > 0),
            "total": len(sector_sorted),
        },
        "risk_proxy": {
            "state": market_regime.get("state"),
            "state_note": market_regime.get("state_note"),
            "score": market_regime.get("score"),
            "fear_greed_score": market_regime.get("fear_greed_score"),
            "fear_greed_label": market_regime.get("fear_greed_label"),
        },
        "market_structure": market_structure.get("label"),
        "market_structure_note": market_structure.get("note"),
        "news_context": {
            "focus": insight_news_context.get("focus"),
            "lead_sections": insight_news_context.get("lead_sections"),
            "lead_events": insight_news_context.get("lead_events"),
            "lead_issues": insight_news_context.get("lead_issues"),
        },
        "divergence_notes": divergence_notes[:3],
        "strategy_bias": strategy_points[:3],
    }
    ai_copy = _generate_us_market_ai_copy(market_date_key, json.dumps(summary_payload, ensure_ascii=False))

    headline = ai_copy.get("headline") or _fallback_market_headline(benchmark_snapshots, macro_snapshots, sector_sorted)
    drivers = ai_copy.get("drivers") or driver_candidates or ["시장 방향성은 유지됐지만 거시 변수의 압박도 여전히 크게 작용했습니다."]
    raw_insight_short_view = ai_copy.get("insight_short_view") or ai_copy.get("insight") or fallback_insight["short_view"]
    insight_deep_dive = ai_copy.get("insight_deep_dive") or fallback_insight["deep_dive"]
    insight_strategy = ai_copy.get("insight_strategy") or fallback_insight["strategy"]
    watchlist = ai_copy.get("watchlist") or fallback_insight["watchlist"]
    insight_short_view = _build_actionable_insight_subtitle(raw_insight_short_view, watchlist)

    sector_breadth = sum(1 for row in sector_sorted if (row.get("change_pct") or 0) > 0)
    sector_total = len(sector_sorted) or len(_US_SECTOR_ETFS)
    strongest_sector = sector_sorted[0] if sector_sorted else None
    weakest_sector = sector_sorted[-1] if sector_sorted else None
    sector_spread = None
    if strongest_sector and weakest_sector and strongest_sector.get("change_pct") is not None and weakest_sector.get("change_pct") is not None:
        sector_spread = float(strongest_sector["change_pct"] - weakest_sector["change_pct"])
    top_gainer = gainers[0] if gainers else None
    top_loser = losers[0] if losers else None
    avg_gainer_change = _average_market_change(gainers)
    avg_loser_change = _average_market_change(losers)
    cyclical_up = sum(1 for row in sector_sorted if row.get("symbol") in _US_CYCLICAL_SECTOR_SYMBOLS and (row.get("change_pct") or 0) > 0)
    defensive_up = sum(1 for row in sector_sorted if row.get("symbol") in _US_DEFENSIVE_SECTOR_SYMBOLS and (row.get("change_pct") or 0) > 0)

    main_metrics = [
        _build_snapshot_metric("SPY", "미국 대형주", benchmark_snapshots.get("SPY", {})),
        _build_snapshot_metric("QQQ", "나스닥 100", benchmark_snapshots.get("QQQ", {})),
        _build_snapshot_metric("DIA", "다우", benchmark_snapshots.get("DIA", {})),
        _build_snapshot_metric("IWM", "러셀 2000", benchmark_snapshots.get("IWM", {})),
        _build_snapshot_metric("VIX", "변동성", benchmark_snapshots.get("VIX", {}), inverse=True),
    ]
    macro_metrics = [
        _build_snapshot_metric("10Y", "미 국채 10년", macro_snapshots.get("10Y", {}), inverse=True),
        _build_snapshot_metric("DXY", "달러 인덱스", macro_snapshots.get("DXY", {}), inverse=True),
        _build_snapshot_metric("USD/KRW", "원/달러 환율", macro_snapshots.get("USDKRW", {}), inverse=True),
        _build_snapshot_metric("Gold", "금 ETF", macro_snapshots.get("Gold", {}), inverse=True),
        _build_snapshot_metric("WTI", "국제유가", macro_snapshots.get("WTI", {})),
        _build_snapshot_metric("BTC", "위험선호 프록시", macro_snapshots.get("BTC", {})),
    ]
    macro_metric_map = {metric["label"]: metric for metric in macro_metrics}
    qqq_vs_spy_metric = _build_relative_strength_metric("QQQ-SPY", "기술주 상대강도", qqq_vs_spy)
    iwm_vs_spy_metric = _build_relative_strength_metric("IWM-SPY", "소형주 상대강도", iwm_vs_spy)
    market_driver_metrics = [
        macro_metric_map["DXY"],
        macro_metric_map["USD/KRW"],
        macro_metric_map["10Y"],
        macro_metric_map["Gold"],
        macro_metric_map["WTI"],
        macro_metric_map["BTC"],
    ]
    sector_metrics = [_build_snapshot_metric(row["symbol"], row["label"], row["snapshot"]) for row in sector_sorted]
    mover_metrics = [_build_snapshot_metric(row["symbol"], _mover_reason(row["snapshot"]), row["snapshot"]) for row in gainers + losers]
    insight_metrics = [
        _build_risk_state_metric(market_regime),
        _build_fear_greed_proxy_metric(market_regime),
        qqq_vs_spy_metric,
        iwm_vs_spy_metric,
        _build_snapshot_metric("Gold", "금 ETF", macro_snapshots.get("Gold", {}), inverse=True),
        {"label": "확산도", "value": f"{sector_breadth}/{sector_total}", "delta": "상승 섹터", "note": "섹터 전반 흐름", "tone": "positive" if sector_breadth >= sector_total / 2 else "negative"},
    ]
    market_driver_summary = str(drivers[0]).strip() if drivers else ""
    market_driver_details = drivers[1:4] if market_driver_summary else drivers[:3]
    if not market_driver_summary:
        market_driver_summary = "금리, 달러, 환율, 금, 유가, 비트코인 흐름이 시장 강약을 설명합니다."
    main_bullets = [
        _build_market_bullet(
            f"시장 상태: {market_regime['state_display']} · 구조: {market_structure['label']} · 심리 {market_regime['fear_greed_score']}/100({market_regime['fear_greed_label']})",
            _resolve_market_tone(market_regime["tone"], market_structure["tone"]),
        ),
        _build_market_bullet(
            f"리더십/확산: QQQ-SPY {_format_pct_point(qqq_vs_spy)} / IWM-SPY {_format_pct_point(iwm_vs_spy)} / 섹터 확산도 {sector_breadth}/{sector_total}",
            _resolve_market_tone(qqq_vs_spy_metric["tone"], iwm_vs_spy_metric["tone"], "positive" if sector_breadth >= sector_total / 2 else "negative"),
        ),
        _build_market_bullet(
            f"섹터 지도: {strongest_sector['label']} {_format_change_pct(strongest_sector.get('change_pct'))} 주도 / {weakest_sector['label']} {_format_change_pct(weakest_sector.get('change_pct'))} 부진",
            _resolve_market_tone(_tone_from_change(strongest_sector.get("change_pct")), _tone_from_change(weakest_sector.get("change_pct"))),
        ) if strongest_sector and weakest_sector else _build_market_bullet("섹터 지도는 데이터 동기화 후 갱신됩니다.", "neutral"),
        _build_market_bullet(
            f"거시 배경: 10Y {macro_metric_map['10Y']['value']} ({macro_metric_map['10Y']['delta'] or 'N/A'}) / DXY {macro_metric_map['DXY']['delta'] or 'N/A'} / Gold {macro_metric_map['Gold']['delta'] or 'N/A'}",
            _resolve_market_tone(macro_metric_map["10Y"]["tone"], macro_metric_map["DXY"]["tone"], macro_metric_map["Gold"]["tone"]),
        ),
    ]
    if top_gainer and top_loser:
        main_bullets.append(
            _build_market_bullet(
                f"주목 종목: {top_gainer['symbol']} {_format_change_pct(top_gainer.get('change_pct'))} 강세 / {top_loser['symbol']} {_format_change_pct(top_loser.get('change_pct'))} 약세",
                _tone_from_change(((top_gainer.get("change_pct") or 0) + (top_loser.get("change_pct") or 0)) / 2, neutral_band=0.5),
            )
        )
    market_driver_bullets = [
        _build_market_bullet(
            f"달러/방어 체크: DXY {macro_metric_map['DXY']['delta'] or 'N/A'} / USD/KRW {macro_metric_map['USD/KRW']['delta'] or 'N/A'} / Gold {macro_metric_map['Gold']['delta'] or 'N/A'}",
            _resolve_market_tone(macro_metric_map["DXY"]["tone"], macro_metric_map["USD/KRW"]["tone"], macro_metric_map["Gold"]["tone"]),
        ),
        _build_market_bullet(
            f"금리/원자재/위험선호: 10Y {macro_metric_map['10Y']['delta'] or 'N/A'} / WTI {macro_metric_map['WTI']['delta'] or 'N/A'} / BTC {macro_metric_map['BTC']['delta'] or 'N/A'}",
            _resolve_market_tone(macro_metric_map["10Y"]["tone"], macro_metric_map["WTI"]["tone"], macro_metric_map["BTC"]["tone"]),
        ),
        _build_market_bullet(
            f"시장 내부 체력: QQQ-SPY {_format_pct_point(qqq_vs_spy)} / IWM-SPY {_format_pct_point(iwm_vs_spy)} / 확산도 {sector_breadth}/{sector_total}",
            _resolve_market_tone(qqq_vs_spy_metric["tone"], iwm_vs_spy_metric["tone"], "positive" if sector_breadth >= sector_total / 2 else "negative"),
        ),
    ] + [_build_market_bullet(text, _infer_market_text_tone(text)) for text in market_driver_details[:2]]
    sector_bullets = []
    sector_bullets.append(
        _build_market_bullet(
            f"섹터 확산: 상승 {sector_breadth}/{sector_total}개 · 경기민감 {cyclical_up}개 상승 / 방어 {defensive_up}개 상승",
            "positive" if sector_breadth >= sector_total / 2 else "negative",
        )
    )
    if strongest_sector and weakest_sector and sector_spread is not None:
        sector_bullets.append(
            _build_market_bullet(
                f"리더십 격차: {strongest_sector['label']} {_format_change_pct(strongest_sector.get('change_pct'))} vs {weakest_sector['label']} {_format_change_pct(weakest_sector.get('change_pct'))} · 스프레드 {sector_spread:+.2f}%p",
                _resolve_market_tone(_tone_from_change(sector_spread, neutral_band=0.6), _tone_from_change(strongest_sector.get("change_pct"))),
            )
        )
    if sector_sorted[:3]:
        sector_bullets.append(
            _build_market_bullet(
                "강세 상위: " + " / ".join(f"{row['symbol']} {_format_change_pct(row.get('change_pct'))} {row['label']}" for row in sector_sorted[:3]),
                "positive",
            )
        )
    weak_sector_rows = list(reversed(sector_sorted[-3:])) if sector_sorted else []
    if weak_sector_rows:
        sector_bullets.append(
            _build_market_bullet(
                "약세 상위: " + " / ".join(f"{row['symbol']} {_format_change_pct(row.get('change_pct'))} {row['label']}" for row in weak_sector_rows),
                "negative",
            )
        )
    mover_subtitle = "섹터 전체 + S&P500 + MSCI(USA) 합집합 유니버스에서 수급이 몰린 종목입니다."
    if avg_gainer_change is not None and avg_loser_change is not None:
        mover_subtitle = (
            f"상승 상위 평균 {_format_change_pct(avg_gainer_change)} / 하락 상위 평균 {_format_change_pct(avg_loser_change)}. "
            "거래량과 단기 추세가 동반된 종목 중심으로 수급이 움직였습니다."
        )
    insight_bullets = [
        _build_market_bullet(
            f"판단 근거: {text}",
            _infer_market_text_tone(text),
        )
        for text in _coerce_market_text_list(insight_deep_dive, max_items=3)
    ]
    insight_bullets += [
        _build_market_bullet(
            f"오늘 행동: {_normalize_market_action_text(text)}",
            _infer_market_text_tone(text),
        )
        for text in _coerce_market_text_list(insight_strategy, max_items=3)
    ]
    insight_bullets += [
        _build_market_bullet(
            f"개장 체크: {_normalize_market_action_text(text)}",
            _infer_market_text_tone(text),
        )
        for text in _coerce_market_text_list(watchlist, max_items=3)
    ]
    if not insight_bullets:
        insight_bullets = [
            _build_market_bullet(
                f"판단 근거: {market_structure['label']} · {market_structure['note']} / 리스크 상태 {market_regime['state_display']}",
                _resolve_market_tone(market_structure["tone"], market_regime["tone"]),
            )
        ]
    market_news_card = _build_market_news_card(
        market_date_key,
        benchmark_snapshots,
        macro_snapshots,
        sector_sorted,
        gainers,
        losers,
        market_news_bundle,
    )

    cards = [
        {
            "id": "main_headline",
            "title": "오늘 시장 한줄",
            "subtitle": headline,
            "metrics": main_metrics,
            "bullets": main_bullets,
            "tone": _tone_from_change(benchmark_snapshots.get("SPY", {}).get("change_pct")),
            "chart_hint": "SPY / QQQ / DIA / IWM / VIX / 리스크",
            "duration_ms": _US_MARKET_TEXT_HEAVY_DURATION,
        },
        {
            "id": "market_drivers",
            "title": "움직인 이유",
            "subtitle": market_driver_summary,
            "metrics": market_driver_metrics,
            "bullets": market_driver_bullets,
            "tone": _tone_from_change(benchmark_snapshots.get("SPY", {}).get("change_pct")),
            "chart_hint": "10Y / DXY / USD/KRW / Gold / WTI / BTC",
            "duration_ms": _US_MARKET_TEXT_HEAVY_DURATION,
        },
        market_news_card,
        {
            "id": "sector_pressure",
            "title": "주요 섹터",
            "subtitle": _build_sector_sentence(sector_sorted),
            "metrics": sector_metrics,
            "bullets": sector_bullets,
            "tone": "positive" if sector_breadth >= sector_total / 2 else "negative",
            "chart_hint": f"상승 섹터 {sector_breadth}/{sector_total}",
            "duration_ms": _US_MARKET_TEXT_HEAVY_DURATION,
        },
        {
            "id": "top_movers",
            "title": "주요 등락주",
            "subtitle": mover_subtitle,
            "metrics": mover_metrics,
            "bullets": [_build_mover_detail_bullet(row) for row in gainers] + [_build_mover_detail_bullet(row) for row in losers],
            "tone": _tone_from_change(sum(row["change_pct"] for row in gainers + losers) / max(1, len(gainers + losers)) if gainers or losers else 0),
            "chart_hint": f"추적 유니버스 {len(movers_sorted)}개",
            "duration_ms": _US_MARKET_TEXT_HEAVY_DURATION,
        },
        {
            "id": "daily_insight",
            "title": "오늘 미장 인사이트",
            "subtitle": insight_short_view,
            "metrics": insight_metrics,
            "bullets": insight_bullets,
            "tone": _tone_from_change(benchmark_snapshots.get("QQQ", {}).get("change_pct")),
            "chart_hint": "오늘 행동 / 개장 체크 / 리스크 상태",
            "duration_ms": _US_MARKET_TEXT_HEAVY_DURATION,
        },
    ]

    def _snapshot_report_entry(symbol, label, snapshot):
        snapshot = snapshot or {}
        price = _safe_market_float(snapshot.get("price"))
        prev_close = _safe_market_float(snapshot.get("prev_close"))
        change_value = (price - prev_close) if (price is not None and prev_close is not None) else None
        return {
            "symbol": str(symbol or ""),
            "label": str(label or ""),
            "price": price,
            "prev_close": prev_close,
            "change_value": change_value,
            "change_pct": snapshot.get("change_pct"),
            "five_day_change": snapshot.get("five_day_change"),
            "month_change": snapshot.get("month_change"),
            "volume_ratio": snapshot.get("volume_ratio"),
        }

    def _build_breadth_summary(up_count, total_count):
        total = int(total_count or 0)
        up = int(up_count or 0)
        if total <= 0:
            return "상승 섹터 0/0, 확산 데이터 없음"
        ratio = up / total
        if ratio >= 0.64:
            state = "확산 강함"
        elif ratio <= 0.36:
            state = "확산 약함"
        else:
            state = "확산 중립"
        return f"상승 섹터 {up}/{total}, {state}"

    def _collect_theme_clusters(rows, max_items=6):
        theme_map = [
            ("양자", "양자"),
            ("ai", "AI"),
            ("반도체", "반도체"),
            ("원전", "원전"),
            ("우주", "우주"),
            ("클라우드", "클라우드"),
            ("바이오", "바이오"),
            ("에너지", "에너지"),
            ("금융", "금융"),
        ]
        clusters = {}
        for raw_row in list(rows or []):
            row = dict(raw_row or {})
            symbol = str(row.get("symbol") or "").strip()
            if not symbol:
                continue
            reason = str(row.get("reason") or "").strip()
            reason_lower = reason.lower()
            theme = "기타"
            for keyword, label in theme_map:
                if keyword in reason_lower:
                    theme = label
                    break
            node = clusters.setdefault(theme, {"theme": theme, "count": 0, "sample_symbols": []})
            node["count"] += 1
            if symbol not in node["sample_symbols"] and len(node["sample_symbols"]) < 4:
                node["sample_symbols"].append(symbol)
        ranked = sorted(clusters.values(), key=lambda item: (-int(item.get("count") or 0), str(item.get("theme") or "")))
        return ranked[: max(1, int(max_items or 1))]

    breadth_summary = _build_breadth_summary(sector_breadth, sector_total)
    leadership_summary = (
        f"QQQ-SPY {_format_pct_point(qqq_vs_spy)} / "
        f"IWM-SPY {_format_pct_point(iwm_vs_spy)} / "
        f"섹터 확산도 {sector_breadth}/{sector_total}"
    )

    premarket_flow = str(drivers[0]).strip() if drivers else str(market_driver_summary).strip()
    regular_flow = str(drivers[1]).strip() if len(drivers) > 1 else str(market_structure.get("note") or insight_short_view).strip()
    close_flow = str(insight_short_view).strip() or (str(drivers[2]).strip() if len(drivers) > 2 else "")
    session_flow = {
        "premarket": premarket_flow or "거시 변수와 뉴스 흐름이 방향성을 만들었습니다.",
        "regular": regular_flow or "장중에는 주도주와 확산도 흐름이 핵심이었습니다.",
        "close": close_flow or "마감 기준으로는 다음 세션 확인형 대응이 유효합니다.",
    }

    favorable_points = [str(item).strip() for item in _coerce_market_text_list(insight_strategy, max_items=3) if str(item).strip()]
    avoid_candidates = [str(item).strip() for item in divergence_notes[:3] if str(item).strip()]
    avoid_candidates += [str(item).strip() for item in _coerce_market_text_list(watchlist, max_items=3) if str(item).strip()]
    avoid_points = _ordered_unique(avoid_candidates)[:3]
    checkpoints = [str(item).strip() for item in _coerce_market_text_list(watchlist, max_items=3) if str(item).strip()]

    reason_by_symbol = {}
    for detail_row in gainers_detail + losers_detail:
        symbol = str((detail_row or {}).get("symbol") or "").strip()
        if symbol and symbol not in reason_by_symbol:
            reason_by_symbol[symbol] = str((detail_row or {}).get("reason") or "").strip()

    quick_targets = []
    for action in analysis_actions[:8]:
        symbol = str((action or {}).get("symbol") or "").strip()
        if not symbol:
            continue
        quick_targets.append(
            {
                "symbol": symbol,
                "change_pct": (action or {}).get("change_pct"),
                "rank": (action or {}).get("rank"),
                "source": str((action or {}).get("source") or "gainers_today"),
                "reason": reason_by_symbol.get(symbol, ""),
            }
        )

    theme_clusters = _collect_theme_clusters(gainers_detail + losers_detail, max_items=6)

    briefing_report = {
        "market_date_label": _format_market_date(market_dt),
        "headline": headline,
        "one_liner": insight_short_view,
        "breadth_summary": breadth_summary,
        "session_flow": session_flow,
        "market_structure": {
            "label": market_structure.get("label"),
            "note": market_structure.get("note"),
            "breadth_summary": breadth_summary,
            "leadership_summary": leadership_summary,
        },
        "sector_summary": {
            "strong": [str(row.get("symbol")) for row in sector_sorted[:3] if str(row.get("symbol") or "").strip()],
            "weak": [str(row.get("symbol")) for row in reversed(sector_sorted[-3:]) if str(row.get("symbol") or "").strip()],
            "interpretation": str(market_structure.get("note") or insight_short_view),
        },
        "theme_clusters": theme_clusters,
        "response_guidance": {
            "favorable": favorable_points,
            "avoid": avoid_points,
        },
        "checkpoints": checkpoints,
        "quick_targets": quick_targets,
        "executive_summary": {
            "risk_state": market_regime.get("state"),
            "risk_state_display": market_regime.get("state_display"),
            "fear_greed_score": market_regime.get("fear_greed_score"),
            "fear_greed_label": market_regime.get("fear_greed_label"),
            "short_view": insight_short_view,
        },
        "benchmarks": {
            "NASDAQ100": _snapshot_report_entry("QQQ", "NASDAQ100", benchmark_snapshots.get("QQQ", {})),
            "S&P500": _snapshot_report_entry("SPY", "S&P500", benchmark_snapshots.get("SPY", {})),
            "DOW": _snapshot_report_entry("DIA", "DOW", benchmark_snapshots.get("DIA", {})),
            "RUSSELL2000": _snapshot_report_entry("IWM", "RUSSELL2000", benchmark_snapshots.get("IWM", {})),
            "VIX": _snapshot_report_entry("VIX", "VIX", benchmark_snapshots.get("VIX", {})),
        },
        "macro": {
            "10Y": _snapshot_report_entry("10Y", "10Y", macro_snapshots.get("10Y", {})),
            "DXY": _snapshot_report_entry("DXY", "DXY", macro_snapshots.get("DXY", {})),
            "USD/KRW": _snapshot_report_entry("USD/KRW", "USD/KRW", macro_snapshots.get("USDKRW", {})),
            "Gold": _snapshot_report_entry("Gold", "Gold", macro_snapshots.get("Gold", {})),
            "WTI": _snapshot_report_entry("WTI", "WTI", macro_snapshots.get("WTI", {})),
            "BTC": _snapshot_report_entry("BTC", "BTC", macro_snapshots.get("BTC", {})),
        },
        "relative_strength": {
            "QQQ_SPY": qqq_vs_spy,
            "IWM_SPY": iwm_vs_spy,
        },
        "sentiment": {
            "risk_state": market_regime.get("state"),
            "risk_state_display": market_regime.get("state_display"),
            "fear_greed_score": market_regime.get("fear_greed_score"),
            "fear_greed_label": market_regime.get("fear_greed_label"),
        },
        "sector_rank": [
            {
                "rank": idx,
                **_snapshot_report_entry(row.get("symbol"), row.get("label"), row.get("snapshot") or {}),
            }
            for idx, row in enumerate(sector_sorted, start=1)
        ],
        "movers": {
            "gainers": [dict(row or {}) for row in gainers_detail[:_US_MARKET_TOP_MOVER_DETAIL_COUNT]],
            "losers": [dict(row or {}) for row in losers_detail[:_US_MARKET_TOP_MOVER_DETAIL_COUNT]],
        },
        "core_movers": {
            "gainers": [dict(row or {}) for row in gainers_detail[:10]],
            "losers": [dict(row or {}) for row in losers_detail[:10]],
        },
        "action_points": {
            "insight_short_view": insight_short_view,
            "insight_bullets": [str((item or {}).get("text") or "") for item in insight_bullets if str((item or {}).get("text") or "").strip()],
            "analysis_actions": [dict(item or {}) for item in analysis_actions[:_US_MARKET_ANALYSIS_ACTION_COUNT]],
            "watchlist": [str(item) for item in _coerce_market_text_list(watchlist, max_items=4)],
        },
    }

    return {
        "market_date_label": _format_market_date(market_dt),
        "headline": headline,
        "cards": cards,
        "mover_universe_count": len(movers_sorted),
        "mover_detail_limit": _US_MARKET_TOP_MOVER_DETAIL_COUNT,
        "gainers_detail": gainers_detail,
        "losers_detail": losers_detail,
        "analysis_actions": analysis_actions,
        "briefing_report": briefing_report,
    }


_COMPONENT_SURROGATE_RE = re.compile(r"[\ud800-\udfff]")
_COMPONENT_JSON_TEXT_TRANSLATION = str.maketrans({
    "\u2028": " ",
    "\u2029": " ",
})


def _sanitize_component_text(value):
    if not isinstance(value, str) or not value:
        return value
    value = _COMPONENT_SURROGATE_RE.sub("\uFFFD", value)
    return value.translate(_COMPONENT_JSON_TEXT_TRANSLATION)


def _sanitize_component_payload(value):
    if isinstance(value, str):
        return _sanitize_component_text(value)
    if isinstance(value, list):
        return [_sanitize_component_payload(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_component_payload(item) for item in value]
    if isinstance(value, dict):
        return {
            _sanitize_component_text(key) if isinstance(key, str) else key: _sanitize_component_payload(item)
            for key, item in value.items()
        }
    return value


def _encode_component_payload(payload):
    payload_json = json.dumps(
        _sanitize_component_payload(payload),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return base64.b64encode(payload_json.encode("utf-8")).decode("ascii")


def _build_us_market_daily_doc(payload):
    payload_b64 = _encode_component_payload(payload)
    template = dedent(
        """
        <!doctype html>
        <html>
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <link href="__FONT_IMPORT_URL__" rel="stylesheet">
          <style>
            :root {
              color-scheme: dark;
              --border: rgba(148,163,184,.16);
              --copy: #cbd5e1;
              --muted: #8fa1bc;
              --strong: #f8fafc;
              --positive: #63d9a2;
              --negative: #ff8f96;
              --neutral: #f6c35e;
            }
            * { box-sizing: border-box; }
            html, body {
              margin: 0;
              width: 100%;
              height: 100%;
              overflow: hidden;
              background: transparent;
              font-family: __FONT_STACK__;
            }
            body { color: var(--copy); }
            .deck {
              --tone-border: rgba(148,163,184,.16);
              --tone-progress: linear-gradient(90deg, rgba(165,180,252,.96), rgba(129,140,248,.96));
              --tone-kicker-border: rgba(165,180,252,.24);
              --tone-kicker-bg: rgba(165,180,252,.10);
              --tone-kicker-copy: #d6ddff;
              --tone-hint-border: rgba(255,255,255,.08);
              --tone-hint-bg: rgba(255,255,255,.04);
              --tone-hint-copy: #e2e8f0;
              --tone-bullet-fill: linear-gradient(180deg, rgba(99,217,162,.96), rgba(45,212,191,.80));
              --tone-bullet-shadow: rgba(99,217,162,.10);
              display: grid;
              grid-template-rows: auto auto 1fr auto;
              width: 100%;
              height: 100%;
              padding: 10px;
              border-radius: 24px;
              border: 1px solid var(--tone-border);
              background:
                radial-gradient(circle at top right, rgba(165,180,252,.14), transparent 24%),
                radial-gradient(circle at bottom left, rgba(99,217,162,.10), transparent 28%),
                linear-gradient(180deg, rgba(19,28,45,.90), rgba(10,15,28,.98));
              box-shadow: 0 22px 44px rgba(2,6,23,.28), inset 0 1px 0 rgba(255,255,255,.04);
              overflow: hidden;
              transition: border-color .28s ease, background .28s ease, box-shadow .28s ease;
            }
            .progress { height: 4px; background: rgba(255,255,255,.04); margin: -10px -10px 0; }
            .progress > div { height: 100%; width: 100%; transform-origin: left center; transform: scaleX(0); background: var(--tone-progress); transition: background .28s ease; }
            .deck[data-tone="neutral"] {
              --tone-border: rgba(148,163,184,.16);
              --tone-progress: linear-gradient(90deg, rgba(165,180,252,.96), rgba(129,140,248,.96));
              --tone-kicker-border: rgba(165,180,252,.24);
              --tone-kicker-bg: rgba(165,180,252,.10);
              --tone-kicker-copy: #d6ddff;
              --tone-hint-border: rgba(255,255,255,.08);
              --tone-hint-bg: rgba(255,255,255,.04);
              --tone-hint-copy: #e2e8f0;
              --tone-bullet-fill: linear-gradient(180deg, rgba(148,163,184,.92), rgba(100,116,139,.82));
              --tone-bullet-shadow: rgba(148,163,184,.10);
            }
            .deck[data-tone="positive"] {
              --tone-border: rgba(99,217,162,.24);
              --tone-progress: linear-gradient(90deg, rgba(99,217,162,.98), rgba(45,212,191,.88));
              --tone-kicker-border: rgba(99,217,162,.26);
              --tone-kicker-bg: rgba(99,217,162,.10);
              --tone-kicker-copy: #d7ffed;
              --tone-hint-border: rgba(99,217,162,.18);
              --tone-hint-bg: rgba(99,217,162,.08);
              --tone-hint-copy: #d7ffed;
              --tone-bullet-fill: linear-gradient(180deg, rgba(99,217,162,.98), rgba(45,212,191,.82));
              --tone-bullet-shadow: rgba(99,217,162,.12);
            }
            .deck[data-tone="negative"] {
              --tone-border: rgba(255,143,150,.24);
              --tone-progress: linear-gradient(90deg, rgba(255,143,150,.98), rgba(251,113,133,.88));
              --tone-kicker-border: rgba(255,143,150,.24);
              --tone-kicker-bg: rgba(255,143,150,.10);
              --tone-kicker-copy: #ffe1e5;
              --tone-hint-border: rgba(255,143,150,.18);
              --tone-hint-bg: rgba(255,143,150,.08);
              --tone-hint-copy: #ffe7ea;
              --tone-bullet-fill: linear-gradient(180deg, rgba(255,143,150,.98), rgba(251,113,133,.82));
              --tone-bullet-shadow: rgba(255,143,150,.12);
            }
            .head { display: flex; justify-content: space-between; gap: 12px; padding: 16px 14px 8px; }
            .kicker { display: inline-flex; align-items: center; min-height: 30px; padding: 0 10px; border-radius: 999px; border: 1px solid var(--tone-kicker-border); background: var(--tone-kicker-bg); color: var(--tone-kicker-copy); font-size: .72rem; font-weight: 900; transition: border-color .28s ease, background .28s ease, color .28s ease; }
            .date { color: var(--muted); font-size: .76rem; font-weight: 700; text-align: right; }
            .body {
              display: block;
              min-height: 0;
              padding: 0 14px 10px;
              overflow-y: auto;
              overflow-x: hidden;
              overscroll-behavior: contain;
              -webkit-overflow-scrolling: touch;
              scrollbar-width: thin;
              scrollbar-color: rgba(148,163,184,.38) transparent;
            }
            .body::-webkit-scrollbar { width: 8px; height: 8px; }
            .body::-webkit-scrollbar-thumb { background: rgba(148,163,184,.32); border-radius: 999px; }
            .body::-webkit-scrollbar-track { background: transparent; }
            .story {
              position: relative;
              z-index: 1;
              display: flex;
              flex-direction: column;
              gap: 12px;
              width: 100%;
              min-width: 0;
              min-height: max-content;
              align-self: start;
            }
            .story-grid {
              display: grid;
              grid-template-columns: minmax(260px, 0.42fr) minmax(380px, 0.58fr);
              gap: 18px;
              width: 100%;
              margin-top: 18px;
              align-items: start;
            }
            .title { margin: 0; color: var(--strong); font-size: 1.16rem; font-weight: 900; transition: color .28s ease; }
            .subtitle { margin: 0; color: #eef2ff; font-size: 1rem; line-height: 1.56; font-weight: 700; transition: color .28s ease; }
            .hint { display: inline-flex; align-items: center; width: fit-content; min-height: 30px; padding: 0 10px; border-radius: 999px; border: 1px solid var(--tone-hint-border); background: var(--tone-hint-bg); color: var(--tone-hint-copy); font-size: .76rem; font-weight: 800; transition: border-color .28s ease, background .28s ease, color .28s ease; }
            .bullets { display: flex; flex-direction: column; gap: 10px; width: 100%; min-width: 0; }
            .bullets--news { gap: 12px; }
            .bullet { display: grid; grid-template-columns: 12px minmax(0,1fr); gap: 10px; padding: 11px 12px; border-radius: 14px; border: 1px solid rgba(148,163,184,.12); background: rgba(255,255,255,.03); transition: border-color .28s ease, background .28s ease; }
            .bullet[data-tone="positive"] { border-color: rgba(99,217,162,.16); background: linear-gradient(180deg, rgba(99,217,162,.06), rgba(255,255,255,.02)); }
            .bullet[data-tone="negative"] { border-color: rgba(255,143,150,.16); background: linear-gradient(180deg, rgba(255,143,150,.06), rgba(255,255,255,.02)); }
            .bullet[data-tone="neutral"] { border-color: rgba(148,163,184,.16); background: linear-gradient(180deg, rgba(148,163,184,.05), rgba(255,255,255,.02)); }
            .bullet i { width: 10px; height: 10px; margin-top: 5px; border-radius: 999px; background: linear-gradient(180deg, rgba(148,163,184,.92), rgba(100,116,139,.82)); box-shadow: 0 0 0 4px rgba(148,163,184,.10); transition: background .28s ease, box-shadow .28s ease; }
            .bullet[data-tone="positive"] i { background: linear-gradient(180deg, rgba(99,217,162,.98), rgba(45,212,191,.82)); box-shadow: 0 0 0 4px rgba(99,217,162,.14); }
            .bullet[data-tone="negative"] i { background: linear-gradient(180deg, rgba(255,143,150,.98), rgba(251,113,133,.82)); box-shadow: 0 0 0 4px rgba(255,143,150,.14); }
            .bullet[data-tone="neutral"] i { background: linear-gradient(180deg, rgba(148,163,184,.92), rgba(100,116,139,.82)); box-shadow: 0 0 0 4px rgba(148,163,184,.10); }
            .bullet span { font-size: .90rem; line-height: 1.56; font-weight: 700; }
            .news-notice {
              padding: 11px 12px;
              border-radius: 14px;
              border: 1px solid rgba(255,143,150,.16);
              background: linear-gradient(180deg, rgba(255,143,150,.08), rgba(255,255,255,.02));
              color: #ffe2e5;
              font-size: .84rem;
              line-height: 1.5;
              font-weight: 700;
            }
            .news-section {
              border-radius: 16px;
              border: 1px solid rgba(148,163,184,.16);
              background: linear-gradient(180deg, rgba(148,163,184,.05), rgba(255,255,255,.02));
              overflow: hidden;
              transition: border-color .28s ease, background .28s ease;
            }
            .news-section[data-tone="positive"] {
              border-color: rgba(99,217,162,.16);
              background: linear-gradient(180deg, rgba(99,217,162,.06), rgba(255,255,255,.02));
            }
            .news-section[data-tone="negative"] {
              border-color: rgba(255,143,150,.16);
              background: linear-gradient(180deg, rgba(255,143,150,.06), rgba(255,255,255,.02));
            }
            .news-section__head {
              display: grid;
              grid-template-columns: minmax(0, 1fr) auto;
              gap: 12px;
              align-items: start;
              padding: 13px 14px;
            }
            .news-section__copy {
              min-width: 0;
              display: flex;
              flex-direction: column;
              gap: 6px;
            }
            .news-section__topline {
              display: flex;
              flex-wrap: wrap;
              gap: 8px;
              align-items: center;
            }
            .news-section__label {
              color: var(--strong);
              font-size: .9rem;
              font-weight: 900;
            }
            .news-section__count {
              display: inline-flex;
              align-items: center;
              min-height: 24px;
              padding: 0 8px;
              border-radius: 999px;
              border: 1px solid rgba(148,163,184,.16);
              background: rgba(255,255,255,.04);
              color: var(--muted);
              font-size: .72rem;
              font-weight: 800;
            }
            .news-section__summary {
              margin: 0;
              color: #edf2ff;
              font-size: .9rem;
              line-height: 1.56;
              font-weight: 700;
            }
            .news-section__toggle {
              min-width: 72px;
              height: 34px;
              padding: 0 12px;
              border-radius: 999px;
              border: 1px solid rgba(148,163,184,.16);
              background: rgba(255,255,255,.05);
              color: var(--strong);
              font-size: .76rem;
              font-weight: 900;
              cursor: pointer;
              position: relative;
              z-index: 2;
              transition: border-color .28s ease, background .28s ease;
            }
            .news-section__toggle:hover {
              border-color: rgba(165,180,252,.28);
              background: rgba(255,255,255,.08);
            }
            .news-section__body {
              display: grid;
              gap: 10px;
              padding: 0 14px 14px;
            }
            .news-item {
              padding: 12px;
              border-radius: 14px;
              border: 1px solid rgba(148,163,184,.12);
              background: rgba(8,12,23,.30);
            }
            .news-item[data-tone="positive"] { border-color: rgba(99,217,162,.16); }
            .news-item[data-tone="negative"] { border-color: rgba(255,143,150,.16); }
            .news-item__meta {
              margin: 0 0 6px;
              color: var(--muted);
              font-size: .73rem;
              line-height: 1.4;
              font-weight: 800;
            }
            .news-item__title,
            .news-item__title:visited {
              display: block;
              margin: 0;
              color: #f8fbff;
              font-size: .9rem;
              line-height: 1.5;
              font-weight: 900;
              text-decoration: none;
            }
            .news-item__title:hover {
              color: #dbe6ff;
              text-decoration: underline;
            }
            .news-item__title--plain:hover {
              color: #f8fbff;
              text-decoration: none;
            }
            .news-item__raw {
              margin: 6px 0 0;
              color: #b7c3d8;
              font-size: .76rem;
              line-height: 1.45;
              font-weight: 700;
            }
            .news-item__takeaway {
              margin: 8px 0 0;
              color: #edf2ff;
              font-size: .84rem;
              line-height: 1.55;
              font-weight: 700;
            }
            .metrics {
              position: relative;
              z-index: 1;
              display: grid;
              width: 100%;
              padding-left: 14px;
              border-left: 1px solid rgba(148,163,184,.14);
              grid-template-columns: repeat(auto-fit, minmax(min(100%, 165px), 1fr));
              gap: 10px;
              align-content: start;
              min-height: max-content;
              align-self: start;
            }
            .metric { position: relative; width: 100%; min-width: 0; padding: 13px 14px; border-radius: 16px; border: 1px solid rgba(148,163,184,.12); background: rgba(255,255,255,.03); overflow: hidden; }
            .metric:after { content: ""; position: absolute; right: 12px; top: 12px; width: 8px; height: 8px; border-radius: 999px; background: rgba(148,163,184,.6); }
            .metric[data-tone="positive"]:after { background: var(--positive); box-shadow: 0 0 0 4px rgba(99,217,162,.12); }
            .metric[data-tone="negative"]:after { background: var(--negative); box-shadow: 0 0 0 4px rgba(255,143,150,.10); }
            .metric[data-tone="neutral"]:after { background: var(--neutral); box-shadow: 0 0 0 4px rgba(246,195,94,.12); }
            .metric b { display: block; color: var(--muted); font-size: .72rem; font-weight: 800; text-transform: uppercase; }
            .metric strong { display: block; margin-top: 8px; color: var(--strong); font-size: 1.08rem; font-weight: 900; }
            .metric em { display: block; margin-top: 6px; font-style: normal; font-size: .82rem; font-weight: 800; }
            .metric[data-tone="positive"] em { color: var(--positive); }
            .metric[data-tone="negative"] em { color: var(--negative); }
            .metric[data-tone="neutral"] em { color: var(--neutral); }
            .metric small { display: block; margin-top: 8px; color: var(--muted); font-size: .72rem; font-weight: 700; padding-right: 18px; }
            .foot {
              position: relative;
              z-index: 3;
              display: grid;
              grid-template-columns: auto minmax(0, 1fr) auto;
              align-items: center;
              gap: 10px;
              margin-top: 2px;
              padding: 10px 14px 12px;
              background: linear-gradient(180deg, rgba(10,15,28,0), rgba(10,15,28,.94) 34%);
            }
            .status {
              min-width: 0;
              display: grid;
              justify-items: center;
              align-content: center;
              gap: 7px;
              padding: 0 8px;
            }
            .btn {
              position: relative;
              z-index: 4;
              min-width: 62px;
              height: 36px;
              padding: 0 14px;
              border-radius: 999px;
              border: 1px solid rgba(148,163,184,.14);
              background: rgba(255,255,255,.04);
              color: var(--strong);
              font-size: .78rem;
              font-weight: 900;
              cursor: pointer;
              transition: border-color .28s ease, background .28s ease;
            }
            .btn--prev { justify-self: start; }
            .btn--next { justify-self: end; }
            .dots {
              display: flex;
              align-items: center;
              justify-content: center;
              gap: 8px;
              flex-wrap: wrap;
              width: 100%;
            }
            .dot { width: 11px; height: 11px; border: 0; border-radius: 999px; background: rgba(148,163,184,.32); cursor: pointer; }
            .dot.active { width: 24px; background: var(--tone-progress); }
            .index { color: var(--muted); font-size: .76rem; font-weight: 800; text-align: center; white-space: nowrap; }
            @media (max-width: 980px) {
              .head { flex-direction: column; align-items: flex-start; }
              .date { text-align: left; }
              .body {
                display: block;
                padding: 0 12px 10px;
              }
              .story {
                display: flex;
                width: 100%;
                min-height: max-content;
                padding-bottom: 2px;
                margin: 0;
                flex: 0 0 auto;
              }
              .story-grid {
                grid-template-columns: 1fr;
                gap: 18px;
                margin-top: 18px;
              }
              .news-section__head {
                grid-template-columns: 1fr;
              }
              .news-section__toggle {
                width: 100%;
              }
              .metrics {
                display: grid;
                width: 100%;
                min-height: max-content;
                margin-top: 0;
                padding-left: 0;
                padding-top: 12px;
                border-left: 0;
                border-top: 1px solid rgba(148,163,184,.14);
                grid-template-columns: repeat(auto-fit, minmax(min(100%, 200px), 1fr));
                flex: 0 0 auto;
              }
              .foot {
                grid-template-columns: repeat(2, minmax(0, 1fr));
                grid-template-areas:
                  "status status"
                  "prev next";
                align-items: stretch;
              }
              .status {
                grid-area: status;
                padding: 0;
              }
              .btn {
                width: 100%;
              }
              .btn--prev {
                grid-area: prev;
              }
              .btn--next {
                grid-area: next;
              }
            }
            @media (max-width: 560px) {
              .deck { padding: 8px; border-radius: 18px; }
              .head { padding: 16px 12px 8px; }
              .foot { padding: 10px 12px 12px; }
              .dots { gap: 7px; }
              .dot { width: 10px; height: 10px; }
              .dot.active { width: 22px; }
              .metrics { grid-template-columns: 1fr; }
            }
          </style>
        </head>
        <body>
          <div class="deck" id="deck" data-tone="neutral">
            <div class="progress"><div id="progressBar"></div></div>
            <div class="head"><div class="kicker">오늘 미국장</div><div class="date" id="deckDate"></div></div>
            <div class="body">
              <div class="story">
                <p class="title" id="cardTitle"></p>
                <p class="subtitle" id="cardSubtitle"></p>
                <div class="hint" id="cardHint"></div>
              </div>
              <div class="story-grid">
                <div class="bullets" id="cardBullets"></div>
                <div class="metrics" id="cardMetrics"></div>
              </div>
            </div>
            <div class="foot">
              <button class="btn btn--prev" id="prevBtn" type="button">이전</button>
              <div class="status"><div class="dots" id="deckDots"></div><div class="index" id="deckIndex"></div></div>
              <button class="btn btn--next" id="nextBtn" type="button">다음</button>
            </div>
          </div>
          <script>
            let payload = { market_date_label: "", cards: [] };
            try {
              const payloadBytes = Uint8Array.from(atob("__PAYLOAD_B64__"), (char) => char.charCodeAt(0));
              payload = JSON.parse(new TextDecoder("utf-8").decode(payloadBytes));
            } catch (error) {
              console.error("Failed to decode market daily payload", error);
            }
            const cards = Array.isArray(payload.cards) ? payload.cards : [];
            const deck = document.getElementById("deck");
            const deckDate = document.getElementById("deckDate");
            const cardTitle = document.getElementById("cardTitle");
            const cardSubtitle = document.getElementById("cardSubtitle");
            const cardHint = document.getElementById("cardHint");
            const cardBullets = document.getElementById("cardBullets");
            const cardMetrics = document.getElementById("cardMetrics");
            const deckDots = document.getElementById("deckDots");
            const deckIndex = document.getElementById("deckIndex");
            const progressBar = document.getElementById("progressBar");
            const prevBtn = document.getElementById("prevBtn");
            const nextBtn = document.getElementById("nextBtn");
            let activeIndex = 0;
            let paused = false;
            let hoverPaused = false;
            let expandedPaused = false;
            let rafId = null;
            let startedAt = 0;
            let elapsedBeforePause = 0;
            let currentDuration = 7000;
            function card() { return cards[activeIndex] || {}; }
            function loopIndex(index) { return cards.length ? (index + cards.length) % cards.length : 0; }
            function resolveDeckTone(value) {
              return value === "positive" || value === "negative" ? value : "neutral";
            }
            function stopTicker() { if (rafId) { cancelAnimationFrame(rafId); rafId = null; } }
            function tick(now) {
              if (paused) return;
              if (!startedAt) startedAt = now;
              const elapsed = elapsedBeforePause + (now - startedAt);
              const progress = Math.min(elapsed / currentDuration, 1);
              progressBar.style.transform = "scaleX(" + progress + ")";
              if (progress >= 1) {
                elapsedBeforePause = 0;
                startedAt = 0;
                activeIndex = loopIndex(activeIndex + 1);
                render();
                return;
              }
              rafId = requestAnimationFrame(tick);
            }
            function startTicker(reset) {
              stopTicker();
              if (reset) { elapsedBeforePause = 0; startedAt = 0; }
              progressBar.style.transform = "scaleX(" + (elapsedBeforePause / currentDuration) + ")";
              if (!paused) rafId = requestAnimationFrame(tick);
            }
            function pauseTicker() {
              if (paused || !cards.length) return;
              paused = true;
              if (startedAt) { elapsedBeforePause += performance.now() - startedAt; startedAt = 0; }
              stopTicker();
            }
            function resumeTicker() {
              if (!paused || !cards.length) return;
              paused = false;
              startTicker(false);
            }
            function syncTickerPause() {
              if (hoverPaused || expandedPaused) {
                pauseTicker();
              } else {
                resumeTicker();
              }
            }
            function renderDots() {
              deckDots.innerHTML = "";
              cards.forEach((item, index) => {
                const dot = document.createElement("button");
                dot.type = "button";
                dot.className = "dot" + (index === activeIndex ? " active" : "");
                dot.addEventListener("click", () => { activeIndex = index; render(); });
                deckDots.appendChild(dot);
              });
            }
            function renderMetrics(metrics) {
              cardMetrics.innerHTML = "";
              (metrics || []).forEach((metric) => {
                const item = document.createElement("article");
                item.className = "metric";
                item.dataset.tone = metric.tone || "neutral";
                item.innerHTML = "<b>" + (metric.label || "") + "</b><strong>" + (metric.value || "N/A") + "</strong>" + (metric.delta ? "<em>" + metric.delta + "</em>" : "") + (metric.note ? "<small>" + metric.note + "</small>" : "");
                cardMetrics.appendChild(item);
              });
            }
            function setBulletMode(isNews) {
              cardBullets.className = isNews ? "bullets bullets--news" : "bullets";
            }
            function renderBullets(bullets) {
              setBulletMode(false);
              cardBullets.innerHTML = "";
              (bullets || []).forEach((entry) => {
                const bullet = typeof entry === "string" ? { text: entry, tone: "neutral" } : (entry || {});
                const row = document.createElement("div");
                row.className = "bullet";
                row.dataset.tone = bullet.tone || "neutral";
                const dot = document.createElement("i");
                const copy = document.createElement("span");
                copy.textContent = bullet.text || "";
                row.appendChild(dot);
                row.appendChild(copy);
                cardBullets.appendChild(row);
              });
            }
            function renderNewsSections(current) {
              const sections = Array.isArray(current.sections) ? current.sections : [];
              if (!sections.length) {
                renderBullets(current.bullets);
                return;
              }
              setBulletMode(true);
              cardBullets.innerHTML = "";
              if (current.notice) {
                const notice = document.createElement("div");
                notice.className = "news-notice";
                notice.textContent = current.notice;
                cardBullets.appendChild(notice);
              }
              sections.forEach((section) => {
                const itemCount = Number(section.count) || ((Array.isArray(section.items) ? section.items.length : 0));
                const visibleCount = Array.isArray(section.items) ? section.items.length : 0;
                const hasItems = Array.isArray(section.items) && section.items.length > 0;
                const box = document.createElement("section");
                box.className = "news-section";
                box.dataset.tone = section.tone || "neutral";

                const head = document.createElement("div");
                head.className = "news-section__head";

                const copy = document.createElement("div");
                copy.className = "news-section__copy";

                const topline = document.createElement("div");
                topline.className = "news-section__topline";

                const label = document.createElement("span");
                label.className = "news-section__label";
                label.textContent = section.label || "";
                topline.appendChild(label);

                if (itemCount > 0) {
                  const count = document.createElement("span");
                  count.className = "news-section__count";
                  count.textContent = itemCount > visibleCount && visibleCount > 0
                    ? "상위 " + visibleCount + " / " + itemCount + "건"
                    : itemCount + "건";
                  topline.appendChild(count);
                }

                const summary = document.createElement("p");
                summary.className = "news-section__summary";
                summary.textContent = section.summary_ko || "";

                copy.appendChild(topline);
                copy.appendChild(summary);
                head.appendChild(copy);

                if (hasItems) {
                  const toggle = document.createElement("button");
                  toggle.type = "button";
                  toggle.className = "news-section__toggle";

                  const body = document.createElement("div");
                  body.className = "news-section__body";

                  let expanded = Boolean(section.expanded);
                  const syncExpanded = () => {
                    box.dataset.expanded = expanded ? "true" : "false";
                    body.style.display = expanded ? "grid" : "none";
                    toggle.textContent = expanded ? "접기" : "더보기";
                    toggle.setAttribute("aria-expanded", expanded ? "true" : "false");
                  };

                  (section.items || []).forEach((entry) => {
                    const item = entry || {};
                    const row = document.createElement("article");
                    row.className = "news-item";
                    row.dataset.tone = item.tone || "neutral";

                    const meta = document.createElement("p");
                    meta.className = "news-item__meta";
                    meta.textContent = [item.display_label, item.tag, item.publisher, item.date].filter(Boolean).join(" · ");
                    row.appendChild(meta);

                    if (item.link) {
                      const title = document.createElement("a");
                      title.className = "news-item__title";
                      title.href = item.link;
                      title.target = "_blank";
                      title.rel = "noopener noreferrer";
                      title.textContent = item.title_ko || item.title_raw || "";
                      row.appendChild(title);
                    } else {
                      const title = document.createElement("p");
                      title.className = "news-item__title news-item__title--plain";
                      title.textContent = item.title_ko || item.title_raw || "";
                      row.appendChild(title);
                    }

                    if (item.title_raw) {
                      const raw = document.createElement("p");
                      raw.className = "news-item__raw";
                      raw.textContent = item.title_raw;
                      row.appendChild(raw);
                    }

                    if (item.takeaway_ko) {
                      const takeaway = document.createElement("p");
                      takeaway.className = "news-item__takeaway";
                      takeaway.textContent = "한줄 요약: " + item.takeaway_ko;
                      row.appendChild(takeaway);
                    }

                    body.appendChild(row);
                  });

                  toggle.addEventListener("click", (event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    expanded = !expanded;
                    expandedPaused = expanded;
                    syncExpanded();
                    syncTickerPause();
                  });

                  syncExpanded();
                  head.appendChild(toggle);
                  box.appendChild(head);
                  box.appendChild(body);
                } else {
                  box.appendChild(head);
                }

                cardBullets.appendChild(box);
              });
            }
            function render() {
              const current = card();
              currentDuration = Number(current.duration_ms) || 7000;
              expandedPaused = false;
              paused = hoverPaused;
              deck.dataset.tone = resolveDeckTone(current.tone);
              deckDate.textContent = payload.market_date_label || "";
              cardTitle.textContent = current.title || "";
              cardSubtitle.textContent = current.subtitle || "";
              cardHint.textContent = current.chart_hint || "";
              renderMetrics(current.metrics);
              if (Array.isArray(current.sections) && current.sections.length) {
                renderNewsSections(current);
              } else {
                renderBullets(current.bullets);
              }
              renderDots();
              deckIndex.textContent = cards.length ? (activeIndex + 1) + " / " + cards.length + " 카드" : "";
              startTicker(true);
              syncTickerPause();
            }
            prevBtn.addEventListener("click", () => { activeIndex = loopIndex(activeIndex - 1); render(); });
            nextBtn.addEventListener("click", () => { activeIndex = loopIndex(activeIndex + 1); render(); });
            deck.addEventListener("mouseenter", () => { hoverPaused = true; syncTickerPause(); });
            deck.addEventListener("mouseleave", () => { hoverPaused = false; syncTickerPause(); });
            deck.addEventListener("touchstart", () => { hoverPaused = true; syncTickerPause(); }, { passive: true });
            deck.addEventListener("touchend", () => { hoverPaused = false; syncTickerPause(); }, { passive: true });
            deck.addEventListener("touchcancel", () => { hoverPaused = false; syncTickerPause(); }, { passive: true });
            if (cards.length) {
              render();
            } else {
              deck.dataset.tone = "neutral";
              deckDate.textContent = payload.market_date_label || "";
              cardTitle.textContent = "데일리 브리핑 불러오는 중";
              cardSubtitle.textContent = "오늘 미국장 데일리 브리핑을 만드는 중입니다. 잠시만 기다려주세요.";
              cardHint.textContent = "데일리 브리핑 로딩 중";
              renderBullets([
                "시장 지수, 거시 지표, 주요 뉴스와 등락주를 정리하고 있습니다.",
                "로딩이 끝나면 오늘 미국장 흐름과 핵심 뉴스를 카드 형태로 보여드립니다.",
              ]);
            }
          </script>
        </body>
        </html>
        """
    ).strip()
    return template.replace("__FONT_IMPORT_URL__", FONT_IMPORT_URL).replace("__FONT_STACK__", FONT_STACK).replace("__PAYLOAD_B64__", payload_b64)


def _render_us_market_daily_deck(payload):
    components.html(
        _build_us_market_daily_doc(payload),
        height=_US_MARKET_DECK_HEIGHT,
        scrolling=False,
    )

def render_market_home_dashboard():
    with st.spinner("데일리 브리핑 만드는 중입니다. 시장 데이터와 핵심 뉴스를 불러오고 있습니다."):
        payload = _sanitize_component_payload(build_us_market_daily_payload())
    card_count = len(payload.get("cards") or [])
    headline_copy = html.escape(
        payload.get("headline")
        or "무엇이 미국장을 움직였는지, 어디에 강약이 몰렸는지, 다음 세션에서 무엇을 볼지 빠르게 정리합니다."
    )
    badges_html = "".join(
        [
            _market_badge("미국 시장", "accent"),
            _market_badge(f"{card_count or 5}장 브리핑", "warning"),
            _market_badge("Gemini" if GEMINI_API_KEY else "규칙 기반", "muted"),
        ]
    )
    st.markdown(
        dedent(
            f"""
            <div class="sigl-market-dashboard-anchor"></div>
            <div class="sigl-market-dashboard__hero">
              <div class="sigl-market-dashboard__intro">
                <p class="sigl-page-head__eyebrow">오늘 미국장</p>
                <p class="sigl-page-head__title">데일리 브리핑</p>
                <p class="sigl-market-dashboard__copy">{headline_copy}</p>
              </div>
              <div class="sigl-market-dashboard__meta">{badges_html}</div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )
    _render_us_market_daily_deck(payload)
    st.markdown(
        """
        <style>
        .sigl-mover-detail-table td.sigl-mover-cell-symbol,
        .sigl-mover-detail-table th.sigl-mover-cell-symbol{
          min-width:156px;
        }
        .sigl-mover-symbol-line{
          display:flex;
          align-items:center;
          gap:6px;
          flex-wrap:wrap;
          min-width:0;
        }
        .sigl-mover-symbol-text{
          display:none;
          font-weight:800;
          color:var(--sigl-text-strong);
        }
        @media (max-width: 640px){
          .sigl-mover-detail-table td.sigl-mover-cell-symbol,
          .sigl-mover-detail-table th.sigl-mover-cell-symbol{
            position:sticky;
            left:0;
            z-index:2;
            background:rgba(15,23,42,.98)!important;
            box-shadow:8px 0 12px rgba(2,6,23,.22);
          }
          .sigl-mover-detail-table td.sigl-mover-cell-symbol .sigl-badge{
            display:inline-flex!important;
            padding:4px 8px!important;
            font-size:.68rem!important;
            line-height:1!important;
          }
          .sigl-mover-symbol-text{
            display:inline-block;
          }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    mover_universe_count = int(payload.get("mover_universe_count", 0) or 0)
    mover_detail_limit = int(payload.get("mover_detail_limit", _US_MARKET_TOP_MOVER_DETAIL_COUNT) or _US_MARKET_TOP_MOVER_DETAIL_COUNT)
    gainers_detail = list(payload.get("gainers_detail") or [])
    losers_detail = list(payload.get("losers_detail") or [])

    def _mover_change_badge(value):
        if value is None or pd.isna(value):
            return _market_badge("N/A", "muted")
        number = float(value)
        tone = "positive" if number > 0 else "negative" if number < 0 else "warning"
        return _market_badge(_format_change_pct(number), tone)

    def _mover_volume_badge(value):
        if value is None or pd.isna(value):
            return _market_badge("N/A", "muted")
        number = float(value)
        tone = "positive" if number >= 1.2 else "warning" if number >= 0.8 else "negative"
        return _market_badge(f"{number:.2f}x", tone)

    def _build_mover_detail_table_html(rows, title, tone, empty_copy):
        safe_title = html.escape(str(title or "").strip() or "상세 목록")
        if not rows:
            safe_empty_copy = html.escape(str(empty_copy or "").strip() or "표시할 데이터가 없습니다.")
            return (
                f"<div class='sigl-card sigl-table-card sigl-card--{tone}'>"
                "<div class='sigl-section-head'>"
                "<div>"
                f"<p class='sigl-section-title'>{safe_title}</p>"
                "<p class='sigl-section-copy'>표시 0개</p>"
                "</div>"
                f"<div class='sigl-inline'>{_market_badge('N/A', 'muted')}</div>"
                "</div>"
                f"<p class='sigl-summary'>{safe_empty_copy}</p>"
                "</div>"
            )

        row_html = []
        for row in rows:
            row = row or {}
            symbol = html.escape(str(row.get("symbol") or "").strip() or "-")
            price_summary = html.escape(str(row.get("price_summary") or "N/A"))
            reason = html.escape(str(row.get("reason") or "데이터 부족"))
            row_html.append(
                "".join(
                    [
                        "<tr>",
                        "<td class='sigl-mover-cell-symbol'>"
                        "<div class='sigl-mover-symbol-line'>"
                        f"<span class='sigl-mover-symbol-text'>{symbol}</span>"
                        f"{_market_badge(symbol, 'accent')}"
                        "</div>"
                        f"<span class='sigl-summary'>{price_summary}</span>"
                        "</td>",
                        f"<td>{_mover_volume_badge(row.get('volume_ratio'))}</td>",
                        f"<td>{_mover_change_badge(row.get('five_day_change'))}</td>",
                        f"<td>{_mover_change_badge(row.get('month_change'))}</td>",
                        f"<td><span class='sigl-summary'>{reason}</span></td>",
                        "</tr>",
                    ]
                )
            )

        return (
            f"<div class='sigl-card sigl-table-card sigl-card--{tone}'>"
            "<div class='sigl-section-head'>"
            "<div>"
            f"<p class='sigl-section-title'>{safe_title}</p>"
            f"<p class='sigl-section-copy'>표시 {len(rows)}개</p>"
            "</div>"
            f"<div class='sigl-inline'>{_market_badge(f'상위 {mover_detail_limit}', 'warning')}</div>"
            "</div>"
            "<div class='sigl-table-wrap'>"
            "<table class='sigl-data-table sigl-mover-detail-table'>"
            "<thead><tr>"
            "<th class='sigl-mover-cell-symbol'>종목 / 현재가(전일대비)</th><th>거래량</th><th>5일</th><th>1개월</th><th>사유</th>"
            "</tr></thead>"
            f"<tbody>{''.join(row_html)}</tbody>"
            "</table>"
            "</div>"
            "</div>"
        )

    with st.expander("주요 등락주 더보기", expanded=False):
        summary_html = (
            "<div class='sigl-section-shell sigl-section-shell--tight'>"
            "<div class='sigl-section-head'>"
            "<div>"
            "<p class='sigl-section-title'>주요 등락주 상세 추적</p>"
            f"<p class='sigl-section-copy'>추적 유니버스 {mover_universe_count}개 기준 · 상위 {mover_detail_limit}개 표시</p>"
            "</div>"
            "<div class='sigl-inline'>"
            f"{_market_badge('상승 상세', 'positive')}"
            f"{_market_badge('하락 상세', 'negative')}"
            f"{_market_badge(f'상위 {mover_detail_limit}', 'warning')}"
            "</div>"
            "</div>"
            "<div class='sigl-grid sigl-grid--2'>"
            f"{_build_mover_detail_table_html(gainers_detail, '상승 더보기', 'positive', '표시할 상승 종목이 없습니다.')}"
            f"{_build_mover_detail_table_html(losers_detail, '하락 더보기', 'negative', '표시할 하락 종목이 없습니다.')}"
            "</div>"
            "</div>"
        )
        st.markdown(summary_html, unsafe_allow_html=True)
    return payload

def _mini_stat_card(label, value, color, tooltip):
    return (
        f"<div class='stat-mini' title='{tooltip}'>"
        f"<p class='sm-label'>{label}</p>"
        f"<p class='sm-value' style='color:{color}'>{value}</p>"
        "</div>"
    )

def _bottom_line_text(m):
    action=m.get('action_label','').strip() or m.get('judgment','NEUTRAL')
    es=float(m.get('ensemble_score',0));ctx=m.get('context_label','기본')
    if 'BUY' in str(m.get('judgment','')):
        return f"결론: {action}. 지금은 매수 우위 구간이며, 분할 진입 관점이 유효합니다. (ES {es:+.1f}, {ctx})"
    if 'SELL' in str(m.get('judgment','')):
        return f"결론: {action}. 지금은 매도/리스크 관리 우위 구간이며, 비중 축소가 우선입니다. (ES {es:+.1f}, {ctx})"
    if str(m.get('judgment',''))=='MIXED':
        return f"결론: {action}. 방향성 혼재 구간이라 신규 진입보다 관망이 유리합니다. (ES {es:+.1f}, {ctx})"
    return f"결론: {action}. 확정 신호가 약해 관망 후 확인 진입이 적절합니다. (ES {es:+.1f}, {ctx})"

def _narrative_text(m):
    rsi=float(m.get('rsi',50));wt=float(m.get('wt1',0));mom=float(m.get('buy_layers',{}).get('Momentum',0)-m.get('sell_layers',{}).get('Momentum',0))
    cmf=float(m.get('cmf',0));bbp=float(m.get('percent_b',0.5))
    if rsi>=70 and mom>0:
        return "RSI가 과매수권이지만 모멘텀 레이어가 여전히 우세해 추세 관성은 살아 있습니다."
    if rsi<=30 and mom<0:
        return "RSI가 과매도권이며 모멘텀도 약세라, 반등은 확인 신호 동반 시에만 유효합니다."
    if wt<-55 and cmf>0:
        return "WaveTrend 과매도와 자금 유입(CMF+)이 겹쳐 바닥 반전 시나리오 확률이 높아지는 구간입니다."
    if wt>55 and cmf<0:
        return "WaveTrend 과매수와 자금 이탈(CMF-)이 동반되어 고점 소진 가능성을 경계해야 합니다."
    if bbp<0.2 and mom>0:
        return "가격이 밴드 하단 근처이면서 모멘텀이 개선되어 눌림 이후 재상승 구조로 해석됩니다."
    if bbp>0.8 and mom<0:
        return "가격이 밴드 상단에 위치한 상태에서 모멘텀이 둔화되어 단기 조정 리스크가 커졌습니다."
    return "추세·모멘텀·자금흐름이 뚜렷하게 한쪽으로 쏠리진 않아, 확인형 대응이 유리합니다."

def _render_ensemble_gauge(es, chart_key=None):
    gauge=go.Figure(go.Indicator(
        mode="gauge+number",
        value=es,
        number={'suffix':'', 'font':{'size':28}},
        gauge={
            'axis':{'range':[-100,100], 'tickwidth':1, 'tickcolor':'#64748B'},
            'bar':{'color':'#A5B4FC', 'thickness':0.35},
            'bgcolor':'rgba(0,0,0,0)',
            'borderwidth':0,
            'steps':[
                {'range':[-100,-30],'color':'rgba(243,165,165,0.32)'},
                {'range':[-30,30],'color':'rgba(245,199,123,0.22)'},
                {'range':[30,100],'color':'rgba(126,216,182,0.32)'},
            ],
            'threshold':{'line':{'color':'#E2E8F0','width':2},'thickness':0.8,'value':es}
        }
    ))
    gauge.update_layout(height=180,margin=dict(l=6,r=6,t=8,b=8),paper_bgcolor='rgba(0,0,0,0)',font=dict(color='#E2E8F0'))
    st.plotly_chart(gauge,use_container_width=True,theme=None,config={'displayModeBar':False}, key=chart_key)

def render_price_header(m, key_prefix="analysis"):
    chg = m['price_change']
    cp = m['price_change_pct']
    cc = 'price-change-up' if chg >= 0 else 'price-change-down'
    ci = '+' if chg >= 0 else '-'

    vr_ = m['volume'] / max(m['avg_volume'], 1)
    jg = m['judgment']
    cf = m['confidence']
    es = float(m.get('ensemble_score', 0))
    jc = SOFT_GREEN if 'BUY' in jg else (SOFT_RED if 'SELL' in jg else SOFT_AMBER)

    act = m.get('action_label', '')
    hero_chip = f"<span class='ind-mini' style='background:{jc}22;color:{jc};border:1px solid {jc}44' title='Final action and confidence'>[{act}] {cf:.0f}%</span>"
    specs = [
        ('ind-b' if m['wt1'] < -20 else ('ind-s' if m['wt1'] > 20 else 'ind-n'), f"WT{m['wt1']:.0f}", "WaveTrend pressure"),
        ('ind-b' if m['rsi'] < 40 else ('ind-s' if m['rsi'] > 60 else 'ind-n'), f"RSI{m['rsi']:.0f}", "RSI momentum"),
        ('ind-b' if vr_ > 1.5 else 'ind-n', f"Vol{vr_:.1f}x", "Volume vs average"),
        ('ind-b' if m['adx'] > 25 else 'ind-n', f"ADX{m['adx']:.0f}", "Trend strength"),
        ('ind-b' if m.get('utbot_dir', 0) == 1 else ('ind-s' if m.get('utbot_dir', 0) == -1 else 'ind-n'), '[UT] B' if m.get('utbot_dir', 0) == 1 else ('[UT] S' if m.get('utbot_dir', 0) == -1 else '[UT] -'), "UT direction"),
        ('ind-b' if m.get('hma_rising') else 'ind-s', '[HMA] UP' if m.get('hma_rising') else '[HMA] DN', "Hull direction"),
    ]
    ih = hero_chip + "".join([f"<span class='ind-mini {c}' title='{tip}'>{l}</span>" for c, l, tip in specs])

    bottom = _bottom_line_text(m).strip()
    narrative = _narrative_text(m).strip()
    insight_body = f"<p style='margin:0;color:#F8FAFC;font-weight:700'>{bottom}</p>"
    if narrative and narrative not in bottom:
        insight_body += f"<p style='margin:6px 0 0;color:#CBD5E1;font-size:.86rem;font-weight:500'>{narrative}</p>"

    st.markdown(
        f"""
        <div class="price-header fade-up">
            <p style="color:#64748B;font-size:.8rem;margin:0">{m['ticker']} - {m['last_date']} - <b style="color:#A5B4FC">{m['regime_label']}</b> - <span style='color:#A5B4FC'>[CTX] {m.get('context_label', 'default')}</span></p>
            <p class="price-big" style="color:#F8FAFC">${m['price']:.2f}<span class="{cc}" style="font-size:1.1rem;margin-left:10px;font-weight:700">{ci}{abs(chg):.2f}({abs(cp):.2f}%)</span></p>
            <div style="margin-top:10px;display:flex;gap:4px;flex-wrap:wrap">{ih}</div>
            <div style='margin-top:12px;background:linear-gradient(140deg,rgba(99,102,241,.13),rgba(15,23,42,.75));border:1px solid rgba(99,102,241,.28);border-radius:10px;padding:10px 12px'>
                {insight_body}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    esc = SOFT_GREEN if es > 0 else (SOFT_RED if es < 0 else SOFT_AMBER)
    es_pct = min(abs(es) / 80 * 100, 100)
    bt_ = float(m.get('buy_total', 0))
    st_ = float(m.get('sell_total', 0))
    ba_ = int(m.get('buy_active', 0))
    sa_ = int(m.get('sell_active', 0))
    bt_pct = min(bt_ / 40 * 100, 100)
    st_pct = min(st_ / 40 * 100, 100)

    h52 = float(m.get('high_52w', m['price']))
    l52 = float(m.get('low_52w', m['price']))
    rng = max(h52 - l52, 0.01)
    pos52 = min(max((m['price'] - l52) / rng * 100, 0), 100)

    def metric_card(title, value, sub, color, fill, bar_color):
        return f"""
        <div style='background:linear-gradient(165deg,rgba(15,23,42,.92),rgba(2,6,23,.86));border:1px solid rgba(148,163,184,.18);border-left:3px solid {color};border-radius:12px;padding:12px 14px;min-height:108px'>
            <p style='margin:0 0 6px;color:#94A3B8;font-size:.74rem;font-weight:700;letter-spacing:.2px'>{title}</p>
            <p style='margin:0;color:{color};font-size:1.55rem;font-weight:800;line-height:1.1'>{value}</p>
            <p style='margin:4px 0 8px;color:#CBD5E1;font-size:.78rem'>{sub}</p>
            <div style='height:7px;background:rgba(148,163,184,.15);border-radius:999px;overflow:hidden'>
                <div style='height:100%;width:{fill:.1f}%;background:{bar_color};border-radius:999px;box-shadow:0 0 10px rgba(148,163,184,.25)'></div>
            </div>
        </div>
        """

    metric_html = "".join([
        metric_card('Ensemble Score', f"{es:+.1f}", f"B{m.get('buy_agree', 0)} : S{m.get('sell_agree', 0)}", esc, es_pct, esc),
        metric_card('BUY Score (10L)', f"{bt_:.1f}", f"{ba_}/10 layers active", SOFT_GREEN, bt_pct, 'linear-gradient(90deg,#237650,#63D9A2)'),
        metric_card('SELL Score (10L)', f"{st_:.1f}", f"{sa_}/10 layers active", SOFT_RED, st_pct, 'linear-gradient(90deg,#FF8F96,#8A4B54)'),
        metric_card('52W Price Position', f"{pos52:.0f}%", f"${l52:.1f} - ${h52:.1f}", '#A5B4FC', pos52, 'linear-gradient(90deg,#FF8F96,#F6C35E,#63D9A2)'),
    ])

    st.markdown(
        f"""
        <div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:16px'>
            {metric_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

    _render_ensemble_gauge(es, chart_key=f"{key_prefix}_ensemble_gauge")

def _risk_size_hint(atr_pct):
    if atr_pct >= 6:
        return 'Small', SOFT_RED
    if atr_pct >= 3.5:
        return 'Reduced', SOFT_AMBER_TEXT
    return 'Standard', SOFT_GREEN

def render_judgment_card(m):
    jg=m['judgment'];es=m.get('ensemble_score',0);cf=m['confidence']
    cc='score-card-buy' if 'BUY' in jg else('score-card-sell' if 'SELL' in jg else 'score-card-neutral')
    jc=SOFT_GREEN if 'BUY' in jg else(SOFT_RED if 'SELL' in jg else SOFT_AMBER)
    ba=m.get('buy_agree',0);sa=m.get('sell_agree',0);veto=m.get('veto_flags','');syn=m.get('reversal_synergy',0);pred=m.get('prediction_boost',0)
    reason=m.get('judgment_reason','');detail=m.get('judgment_detail','');action=m.get('action_label','')
    detail_text=(detail or '').strip() or (reason or '').strip()
    detail_norm=" ".join(detail_text.split())
    detail_html = (
        f"<div style=\"margin:16px 0;background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.06);"
        f"border-radius:12px;padding:14px 18px;border-left:3px solid {jc}\">"
        f"<p style=\"color:#94A3B8;font-size:.72rem;font-weight:700;margin:0 0 6px\">근거 요약</p>"
        f"<p style=\"color:#CBD5E1;font-size:.82rem;margin:0\">{detail_text}</p>"
        f"</div>"
    ) if detail_text else ""
    contrast=(m.get('contrast_notes','') or '').strip()
    contrast_norm=" ".join(contrast.split())
    long_rr=float(m.get('vp_long_rr',1) or 1);short_rr=float(m.get('vp_short_rr',1) or 1)
    volume_ratio=float(m.get('volume_ratio_20',1) or 1)
    risk_tags=[]
    if m.get('smart_money_bearish_div'):
        risk_tags.append(("Smart money divergence", SOFT_RED))
    elif m.get('smart_money_bullish_div'):
        risk_tags.append(("Money flow support", SOFT_GREEN))
    if 'BUY' in jg and long_rr < 1:
        risk_tags.append((f"Long RR {long_rr:.2f}", SOFT_AMBER_TEXT))
    if 'SELL' in jg and short_rr < 1:
        risk_tags.append((f"Short RR {short_rr:.2f}", SOFT_AMBER_TEXT))
    if volume_ratio < 0.7:
        risk_tags.append((f"Low vol {volume_ratio:.1f}x", SOFT_AMBER_TEXT))
    if m.get('blowoff_top_hard'):
        risk_tags.append(("Blow-off risk", SOFT_RED))
    risk_html=""
    if contrast or risk_tags:
        chips="".join([f"<span style='display:inline-flex;align-items:center;gap:4px;padding:4px 9px;border-radius:999px;background:{col}22;border:1px solid {col}44;color:{col};font-size:.72rem;font-weight:700'>{label}</span>" for label,col in risk_tags])
        show_contrast=bool(contrast) and contrast_norm not in detail_norm and detail_norm not in contrast_norm
        risk_parts = [
            "<div style=\"margin:14px 0 0;background:rgba(15,23,42,.58);border:1px solid rgba(148,163,184,.14);border-radius:12px;padding:14px 16px\">",
            "<p style=\"color:#94A3B8;font-size:.72rem;font-weight:700;margin:0 0 8px\">Risk Check</p>",
        ]
        if show_contrast:
            risk_parts.append(f"<p style='color:#CBD5E1;font-size:.8rem;margin:0 0 10px'>{contrast}</p>")
        risk_parts.append(f"<div style='display:flex;gap:8px;flex-wrap:wrap'>{chips}</div>")
        risk_parts.append("</div>")
        risk_html="".join(risk_parts)
    circ=2*3.14159*36;offset=circ*(1-cf/100)
    # Committee vote dots
    committee=m.get('committee',{})
    dots_html=""
    if committee:
        dots=[]
        abbr={'Trend':'TR','Momentum':'MO','Money':'MN','Structure':'ST','Leading':'LD'}
        for cm in COMMITTEE_NAMES:
            data=committee.get(cm,{});vote=data.get('vote','NEUTRAL')
            dcls='buy' if vote=='BUY' else ('sell' if vote=='SELL' else ('abstain' if vote=='ABSTAIN' else 'neutral'))
            vc=SOFT_GREEN if vote=='BUY' else(SOFT_RED if vote=='SELL' else '#475569')
            dots.append(f"<span style='display:inline-flex;align-items:center;gap:2px;margin:0 3px'><span class='vote-dot {dcls}'></span><span style='color:{vc};font-size:.6rem;font-weight:600'>{abbr.get(cm,cm[:2])}</span></span>")
        dots_html=f"<div style='margin-top:10px;display:flex;align-items:center;justify-content:center;gap:2px'><span style='color:#475569;font-size:.65rem;margin-right:4px'>위원회</span>{''.join(dots)}</div>"
    veto_html=f"<div style='margin-top:8px;text-align:center'><span style='background:rgba(243,165,165,.15);color:{SOFT_RED_TEXT};padding:4px 10px;border-radius:6px;font-size:.72rem;font-weight:700'>VETO {veto}</span></div>" if veto else ""
    # Badges
    badges=""
    if abs(syn)>5:badges+=f"<span style='background:rgba({'52,211,153' if syn>0 else '248,113,113'},.12);color:{SOFT_GREEN if syn>0 else SOFT_RED};padding:3px 8px;border-radius:6px;font-size:.72rem;font-weight:700'>SYN {syn:+.1f}</span> "
    if abs(pred)>3:badges+=f"<span style='background:rgba({'52,211,153' if pred>0 else '248,113,113'},.12);color:{SOFT_GREEN if pred>0 else SOFT_RED};padding:3px 8px;border-radius:6px;font-size:.72rem;font-weight:700'>PRED {pred:+.1f}</span>"
    # Ensemble gauge
    es_norm=min(max((es+80)/160*100,0),100)
    es_c=SOFT_GREEN if es>0 else SOFT_RED if es<0 else SOFT_AMBER
    # Agree ratio bar
    total_agree=max(ba+sa,1);ba_pct=ba/total_agree*100
    card_html = dedent(f"""
    <div class="score-card {cc} fade-up">
        <div style="display:flex;align-items:center;justify-content:center;gap:28px;flex-wrap:wrap">
            <div class="conf-ring"><svg viewBox="0 0 80 80"><circle class="ring-bg" cx="40" cy="40" r="36"/><circle class="ring-fg" cx="40" cy="40" r="36" stroke="{jc}" stroke-dasharray="{circ:.1f}" stroke-dashoffset="{offset:.1f}"/></svg><span class="ring-text" style="color:{jc}">{cf:.0f}%</span></div>
            <div>
                <p style="font-size:1.8rem;font-weight:800;color:{jc};margin:0;letter-spacing:-.5px">{action}</p>
                {dots_html}
            </div>
        </div>{detail_html}{risk_html}
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-top:14px">
            <div style="background:rgba(255,255,255,.03);border-radius:10px;padding:12px;text-align:center">
                <p style="color:#64748B;font-size:.68rem;font-weight:700;margin:0 0 4px">Ensemble</p>
                <p style="color:{es_c};font-size:1.3rem;font-weight:800;margin:0">{es:+.1f}</p>
                <div style="height:3px;background:rgba(255,255,255,.06);border-radius:2px;margin-top:6px;overflow:hidden"><div style="height:100%;width:{es_norm}%;background:{es_c};border-radius:2px"></div></div>
            </div>
            <div style="background:rgba(255,255,255,.03);border-radius:10px;padding:12px;text-align:center">
                <p style="color:#64748B;font-size:.68rem;font-weight:700;margin:0 0 4px">Agree B:S</p>
                <p style="color:#F8FAFC;font-size:1.3rem;font-weight:800;margin:0">{ba}:{sa}</p>
                <div style="height:3px;background:rgba(243,165,165,.28);border-radius:2px;margin-top:6px;overflow:hidden"><div style="height:100%;width:{ba_pct}%;background:{SOFT_GREEN};border-radius:2px"></div></div>
            </div>
            <div style="background:rgba(255,255,255,.03);border-radius:10px;padding:12px;text-align:center">
                <p style="color:#64748B;font-size:.68rem;font-weight:700;margin:0 0 4px">Context</p>
                <p style="color:#A5B4FC;font-size:1.05rem;font-weight:800;margin:0">{m.get('context_label','기본')}</p>
                <div style="height:3px;background:rgba(165,180,252,.15);border-radius:2px;margin-top:6px;overflow:hidden"><div style="height:100%;width:100%;background:#A5B4FC;border-radius:2px;opacity:.4"></div></div>
            </div>
        </div>
        <div style='margin-top:10px;display:flex;justify-content:center;gap:8px;flex-wrap:wrap'>{badges}</div>{veto_html}
    </div>
    """).strip()
    st.markdown(card_html, unsafe_allow_html=True)

def render_committee_panel(m):
    committee=m.get('committee',{})
    if not committee:return
    ctx_code=m.get('context',0);ctx_name=CTX_LABELS.get(ctx_code,'default');weights=CONTEXT_WEIGHTS.get(ctx_name,CONTEXT_WEIGHTS['default'])
    cards_html=""
    for ci,cm in enumerate(COMMITTEE_NAMES):
        data=committee.get(cm,{});score=data.get('score',0);conv=data.get('conviction',0);vote=data.get('vote','NEUTRAL');weight=weights[ci] if ci<len(weights) else 0.2
        sc=SOFT_GREEN if score>0 else(SOFT_RED if score<0 else '#94A3B8')
        vc=f'background:rgba(126,216,182,.14);color:{SOFT_GREEN}' if vote=='BUY' else(f'background:rgba(243,165,165,.14);color:{SOFT_RED}' if vote=='SELL' else('background:rgba(71,85,105,.3);color:#64748B' if vote=='ABSTAIN' else f'background:rgba(245,199,123,.14);color:{SOFT_AMBER}'))
        bar_w=min(abs(score)/40*100,100)
        bdr=f'border-left:3px solid {sc}' if abs(score)>10 else ''
        cards_html+=f"""<div class='cm-card' style='{bdr}'>
            <p class='cm-name'>{cm} ×{weight:.0%}</p>
            <p class='cm-score' style='color:{sc}'>{score:+.0f}</p>
            <span class='cm-vote' style='{vc}'>{vote}</span>
            <p style='color:#64748B;font-size:.65rem;margin:4px 0 0'>확신 {conv:.0f}%</p>
            <div class='cm-mini-bar'><div class='cm-mini-fill' style='width:{bar_w}%;background:{sc}'></div></div>
        </div>"""
    st.markdown(f"<div style='display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-top:12px'>{cards_html}</div>",unsafe_allow_html=True)
    veto=m.get('veto_flags','')
    if veto:st.warning(f"**[VETO]** {veto}")
    syn=m.get('reversal_synergy',0)
    if abs(syn)>5:st.info(f"**[SYNERGY]** {syn:+.1f}")

def render_10layer_bars(m, html_key="analysis"):
    layer_names = ['Trend', 'Momentum', 'Candle', 'BB', 'Volume', 'MF', 'Pattern', 'Combined', 'Leading', 'Lagging']
    buy_layers = m.get('buy_layers', {})
    sell_layers = m.get('sell_layers', {})
    max_val = 12.0

    rows = []
    for name in layer_names:
        bv = max(float(buy_layers.get(name, 0)), 0.0)
        sv = max(float(sell_layers.get(name, 0)), 0.0)
        bpct = min((bv / max_val) * 50.0, 50.0)
        spct = min((sv / max_val) * 50.0, 50.0)
        bop = 1.0 if bv > 0 else 0.35
        sop = 1.0 if sv > 0 else 0.35
        row_glow = "box-shadow:0 0 10px rgba(99,102,241,.18);" if abs(bv - sv) >= 4 else ""

        rows.append(
            f"<div style='display:grid;grid-template-columns:58px 1fr 58px;gap:10px;align-items:center;margin-bottom:8px;padding:2px;border-radius:10px;{row_glow}'>"
            f"<div style='text-align:right;color:{SOFT_GREEN};font-size:.88rem;font-weight:700;opacity:{bop:.2f}'>{bv:.1f}</div>"
            "<div style='position:relative;height:30px;border-radius:10px;border:1px solid rgba(148,163,184,.2);background:linear-gradient(90deg,rgba(126,216,182,.08),rgba(148,163,184,.04),rgba(243,165,165,.08));overflow:hidden'>"
            f"<div style='position:absolute;left:{50.0 - bpct:.2f}%;top:4px;bottom:4px;width:{bpct:.2f}%;background:linear-gradient(90deg,#237650,#63D9A2);border-radius:6px 0 0 6px;opacity:{bop:.2f}'></div>"
            f"<div style='position:absolute;left:50%;top:4px;bottom:4px;width:{spct:.2f}%;background:linear-gradient(90deg,#FF8F96,#8A4B54);border-radius:0 6px 6px 0;opacity:{sop:.2f}'></div>"
            "<div style='position:absolute;left:50%;top:0;bottom:0;width:1px;background:rgba(226,232,240,.55)'></div>"
            f"<div style='position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);font-size:.72rem;color:#CBD5E1;font-weight:700;background:rgba(2,6,23,.78);padding:2px 8px;border-radius:999px;border:1px solid rgba(148,163,184,.25)'>{name}</div>"
            "</div>"
            f"<div style='text-align:left;color:{SOFT_RED};font-size:.88rem;font-weight:700;opacity:{sop:.2f}'>{sv:.1f}</div>"
            "</div>"
        )

    buy_active = int(m.get('buy_active', 0))
    sell_active = int(m.get('sell_active', 0))

    rows_html = "".join(rows)
    panel_html = (
        "<div style='background:rgba(15,19,32,.55);backdrop-filter:blur(12px);border:1px solid rgba(255,255,255,.08);border-radius:14px;padding:16px 14px;margin-bottom:12px'>"
        "<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:8px'>"
        f"<span style='color:{SOFT_GREEN};font-weight:800;font-size:.86rem'>BUY ({buy_active}/10)</span>"
        "<span style='color:#94A3B8;font-size:.76rem;font-weight:700'>10-Layer Buy/Sell comparison</span>"
        f"<span style='color:{SOFT_RED};font-weight:800;font-size:.86rem'>SELL ({sell_active}/10)</span>"
        "</div>"
        "<div style='display:flex;justify-content:center;gap:10px;margin:0 0 10px'>"
        f"<span style='color:{SOFT_GREEN};font-size:.7rem'>left = buy pressure</span>"
        f"<span style='color:{SOFT_RED};font-size:.7rem'>right = sell pressure</span>"
        "</div>"
        f"{rows_html}"
        "</div>"
    )
    panel_h=max(430,120+len(layer_names)*44)
    html_doc=f"""<!doctype html><html><head><meta charset='utf-8'><link href='{FONT_IMPORT_URL}' rel='stylesheet'></head><body style='margin:0;background:transparent;color:#E2E8F0;font-family:{FONT_STACK}'><!-- {html_key} -->{panel_html}</body></html>"""
    components.html(html_doc,height=panel_h,scrolling=False)
def render_leading_lagging(m):
    lv=m['leading_verdict'];lgv=m['lagging_verdict'];ac=m['composite_accel']
    lc=SOFT_GREEN if '상승' in lv else(SOFT_RED if '하락' in lv else SOFT_AMBER)
    lgc=SOFT_GREEN if '상승' in lgv else(SOFT_RED if '하락' in lgv else SOFT_AMBER)
    # Setup Pressure tug-of-war
    spb=m.get('setup_pressure_buy',0);sps=m.get('setup_pressure_sell',0)
    maxsp=max(spb,sps,1);bw=min(spb/maxsp*50,50);sw=min(sps/maxsp*50,50)
    tow_label=f"매수 압력 {spb:.1f}" if spb>sps else(f"매도 압력 {sps:.1f}" if sps>spb else "균형")
    tow_color=SOFT_GREEN if spb>sps else(SOFT_RED if sps>spb else SOFT_AMBER)
    # Tech snapshot stats
    pb_=m.get('percent_b',0.5);pb_pct=pb_*100
    cmf_=m.get('cmf',0);cmf_c=SOFT_GREEN if cmf_>0.05 else(SOFT_RED if cmf_<-0.05 else '#94A3B8')
    obv_c=SOFT_GREEN if m.get('obv_trend')=='rising' else SOFT_RED
    obv_slope=m.get('obv_slope',0);obv_slope_c=SOFT_GREEN if obv_slope>0 else(SOFT_RED if obv_slope<0 else '#94A3B8')
    atr_pct=m.get('atr_pct',0)
    volume_ratio=m.get('volume_ratio_20',1);vol_c=SOFT_GREEN if volume_ratio>=1 else(SOFT_AMBER_TEXT if volume_ratio>=0.7 else SOFT_RED)
    long_rr=m.get('vp_long_rr',1);short_rr=m.get('vp_short_rr',1)
    long_rr_c=SOFT_GREEN if long_rr>=1.35 else(SOFT_AMBER_TEXT if long_rr>=1 else SOFT_RED)
    short_rr_c=SOFT_GREEN if short_rr>=1.35 else(SOFT_AMBER_TEXT if short_rr>=1 else SOFT_RED)
    ma50d=m.get('ma50_dist',0);ma200d=m.get('ma200_dist',0)
    ma50c=SOFT_GREEN if ma50d>0 else SOFT_RED
    ma200c=SOFT_GREEN if ma200d>0 else SOFT_RED
    size_label,size_color=_risk_size_hint(atr_pct)
    flow_text='하락 다이버전스' if m.get('smart_money_bearish_div') else('상승 지지' if m.get('smart_money_bullish_div') else '정렬')
    flow_color=SOFT_RED if m.get('smart_money_bearish_div') else(SOFT_GREEN if m.get('smart_money_bullish_div') else '#94A3B8')
    st.markdown(f"""<div style='display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px'>
        <div style='background:rgba(255,255,255,.03);border:1px solid #1E293B;border-radius:12px;padding:16px'>
            <p style='font-weight:700;color:#A5B4FC;margin:0 0 8px;font-size:.85rem'>선행 지표 (Leading)</p>
            <p style='color:{lc};font-weight:800;font-size:1.15rem;margin:0 0 8px'>{lv}</p>
            <div style='display:flex;gap:10px;flex-wrap:wrap'>
                <span style='color:#94A3B8;font-size:.78rem'>가속도: <b style='color:{SOFT_GREEN if ac>0 else SOFT_RED}'>{ac:+.2f}</b></span>
                <span style='color:#94A3B8;font-size:.78rem'>UT: {'Buy' if m.get('utbot_dir',0)==1 else('Sell' if m.get('utbot_dir',0)==-1 else 'N')}</span>
                <span style='color:#94A3B8;font-size:.78rem'>Hull: {'Up' if m.get('hma_rising') else 'Down'}</span>
            </div>
        </div>
        <div style='background:rgba(255,255,255,.03);border:1px solid #1E293B;border-radius:12px;padding:16px'>
            <p style='font-weight:700;color:#A5B4FC;margin:0 0 8px;font-size:.85rem'>후행 지표 (Lagging)</p>
            <p style='color:{lgc};font-weight:800;font-size:1.15rem;margin:0 0 8px'>{lgv}</p>
            <div style='display:flex;gap:14px'>
                <span style='color:#94A3B8;font-size:.78rem'>Context: <b>{m['regime_label']}</b></span>
                <span style='color:#94A3B8;font-size:.78rem'>RS: <b style='color:{SOFT_GREEN if m["rs_ratio"]>1.03 else(SOFT_RED if m["rs_ratio"]<.97 else SOFT_AMBER)}'>{m['rs_ratio']:.3f}</b></span>
            </div>
        </div>
    </div>""",unsafe_allow_html=True)
    # Setup Pressure
    st.markdown(f"""<div style='background:rgba(255,255,255,.03);border:1px solid #1E293B;border-radius:12px;padding:14px;margin-bottom:12px'>
        <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:4px'>
            <span style='color:{SOFT_GREEN};font-size:.78rem;font-weight:700'>매수 셋업 {spb:.1f}</span>
            <span style='color:{tow_color};font-size:.78rem;font-weight:700'>{tow_label}</span>
            <span style='color:{SOFT_RED};font-size:.78rem;font-weight:700'>매도 셋업 {sps:.1f}</span>
        </div>
        <div class='tow-bar'><div class='tow-buy' style='width:{bw}%'></div><div class='tow-sell' style='width:{sw}%'></div><div class='tow-center'></div></div>
    </div>""",unsafe_allow_html=True)
    # Tech snapshot
    snapshot_cards = "".join([
        _mini_stat_card('BB %B', f"{pb_pct:.0f}%", SOFT_GREEN if pb_<0.3 else(SOFT_RED if pb_>0.7 else SOFT_AMBER), '볼린저 밴드 내 현재 위치입니다. 30% 이하는 눌림, 70% 이상은 과열 가능성으로 읽습니다.'),
        _mini_stat_card('CMF', f"{cmf_:+.3f}", cmf_c, 'Chaikin Money Flow. 0 위면 자금 유입 우위, 0 아래면 자금 이탈 우위입니다.'),
        _mini_stat_card('Money Flow', flow_text, flow_color, '가격과 수급이 같은 방향인지 확인합니다. 다이버전스면 추세 신뢰도가 떨어질 수 있습니다.'),
        _mini_stat_card('OBV Slope', f"{obv_slope:+.2f}", obv_slope_c, 'OBV 기울기입니다. 가격 상승 중 OBV가 꺾이면 스마트 머니 경고로 해석합니다.'),
        _mini_stat_card('Vol 20d', f"{volume_ratio:.1f}x", vol_c, '최근 거래량이 20일 평균 대비 얼마나 붙는지 보여줍니다. 1배 미만이면 추격 신호 신뢰도가 낮아질 수 있습니다.'),
        _mini_stat_card('Long RR', f"{long_rr:.2f}", long_rr_c, '현재가에서 저항(VAH)과 지지(POC/VAL)까지의 비율입니다. 1 미만이면 롱 손익비가 답답합니다.'),
        _mini_stat_card('Short RR', f"{short_rr:.2f}", short_rr_c, '현재가에서 하방 공간과 상단 저항을 비교한 값입니다. 숏 관점의 구조적 공간을 확인할 때 봅니다.'),
        _mini_stat_card('ATR%', f"{atr_pct:.1f}%", SOFT_BLUE, '평균 변동폭이 현재가 대비 얼마나 큰지 보여줍니다. 값이 높을수록 포지션 크기를 줄이는 편이 안전합니다.'),
        _mini_stat_card('Risk Size', size_label, size_color, 'ATR 기반 권장 비중 힌트입니다. Standard보다 Reduced/Small이면 손절 폭과 비중을 함께 낮추는 편이 좋습니다.'),
        _mini_stat_card('MA50 이격', f"{ma50d:+.1f}%", ma50c, '현재가가 50일선에서 얼마나 벌어졌는지 보여줍니다. 이격이 과하면 눌림 없이 추격하기 어렵습니다.'),
        _mini_stat_card('MA200 이격', f"{ma200d:+.1f}%", ma200c, '중장기 추세선과의 거리입니다. 장기 추세 위/아래 여부를 가장 빠르게 읽을 수 있습니다.'),
    ])
    st.markdown(f"""<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:8px'>{snapshot_cards}</div>""",unsafe_allow_html=True)

def render_combined_scans(m):
    scans=m.get('combined_scans',[])
    if not scans:st.info("활성 Combined Scan 없음");return
    bn=sum(1 for s in scans if s['dir']=='buy');sn_=sum(1 for s in scans if s['dir']=='sell');t1=sum(1 for s in scans if s['tier']==1)
    hc='#E8C56C' if t1>0 else(SOFT_GREEN if bn>sn_ else(SOFT_RED if sn_>bn else SOFT_AMBER))
    st.markdown(f"<div style='background:rgba(255,215,0,.06);border:1px solid {hc}33;border-radius:12px;padding:12px;margin-bottom:10px'><span style='font-size:1.2rem;font-weight:800;color:{hc}'>[COMBO] {len(scans)} Active</span> <span style='color:#94A3B8;margin-left:12px'>T1:{t1} B:{bn} S:{sn_}</span></div>",unsafe_allow_html=True)
    cards=[]
    for s in scans:
        tb={1:'T1',2:'T2',3:'T3'}.get(s['tier'],'T?');is_buy=s['dir']=='buy';is_sell=s['dir']=='sell'
        dc_=SOFT_GREEN if is_buy else(SOFT_RED if is_sell else SOFT_AMBER)
        bg='linear-gradient(160deg,rgba(5,46,22,.55),rgba(15,23,42,.6))' if is_buy else('linear-gradient(160deg,rgba(69,10,10,.55),rgba(30,41,59,.6))' if is_sell else 'linear-gradient(160deg,rgba(120,53,15,.5),rgba(30,41,59,.6))')
        ic='🟢' if is_buy else('🔴' if is_sell else '🟠')
        td="<span style='background:#FFD700;color:#111827;padding:2px 6px;border-radius:999px;font-size:.64rem;font-weight:800'>TODAY</span>" if s['is_today'] else f"<span style='color:#94A3B8;font-size:.72rem'>{s['date']}</span>"
        cards.append(f"""<div style='background:{bg};border:1px solid {dc_}55;border-radius:14px;padding:12px 12px 10px;box-shadow:0 8px 24px rgba(0,0,0,.25)'>
            <div style='display:flex;justify-content:space-between;align-items:center;gap:8px'>
                <span style='color:{dc_};font-weight:800'>{ic} {s['kor']}</span>
                <span style='color:#E2E8F0;font-size:.68rem;background:rgba(15,23,42,.6);padding:2px 8px;border-radius:999px'>{tb}</span>
            </div>
            <div style='margin-top:8px;display:flex;justify-content:space-between;align-items:center'>
                <span style='color:#60A5FA;font-size:.72rem'>WinRate {s['win']}</span>
                {td}
            </div>
        </div>""")
    st.markdown(f"<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px'>{''.join(cards)}</div>",unsafe_allow_html=True)

def render_indicator_help():
    with st.expander("ℹ️ 화면 읽는 법 / 지표 도움말"):
        st.markdown(
            "- `Action / Confidence`: 현재 결론과 신뢰도입니다. 첫 화면에서 가장 먼저 보시면 됩니다.\n"
            "- `Risk Check`: 수급 다이버전스, 손익비, 저거래량, 과열 경고를 모아 보여줍니다.\n"
            "- `WT`: 과매수/과매도 반전 압력입니다.\n"
            "- `ADX`: 추세 강도이며 방향 지표는 아닙니다.\n"
            "- `CMF / OBV Slope`: 자금 유입/이탈과 스마트 머니 방향성을 읽는 핵심 지표입니다.\n"
            "- `Ensemble Score`: -100~+100 종합 방향 점수입니다.\n"
            "- `10-Layer`: 추세, 모멘텀, 구조, 자금 등 레이어별 기여도 비교입니다."
        )

def render_analysis(msg, key_prefix="analysis"):
    m,fj=msg.get('meta'),msg.get('fig_json')
    if m:
        render_price_header(m, key_prefix=key_prefix)
    if m or fj:
        t0,t1,t2,t3,t4=st.tabs(["차트","판단·리스크","10-Layer","콤보스캔","기업정보"])
        with t0:
            if fj:fig=load_chart_figure(fj);st.plotly_chart(fig,use_container_width=True,theme=None,config={'displaylogo':False,'modeBarButtonsToRemove':['lasso2d','select2d']}, key=f"{key_prefix}_price_chart");st.caption("*캔들 오버 시 툴팁, 강/약 시그널 캔들 하이라이트, 우측 매물대(VP) 오버레이를 제공합니다. 모바일에서는 판단 카드 확인 후 차트를 열면 더 읽기 쉽습니다.")
        with t1:
            if m:
                render_judgment_card(m)
                st.markdown("#### 🏛️ 5-Committee Ensemble")
                render_committee_panel(m)
                st.markdown("---")
                render_leading_lagging(m)
                render_indicator_help()
        with t2:
            if m:render_10layer_bars(m, html_key=f"{key_prefix}_10layer")
        with t3:
            if m:render_combined_scans(m)
        with t4:
            if m:render_company_details(m['ticker'], key_prefix=f"{key_prefix}_company")


def _risk_size_hint(atr_pct):
    if atr_pct >= 6:
        return '작게(Small)', SOFT_RED
    if atr_pct >= 3.5:
        return '줄여서(Reduced)', SOFT_AMBER_TEXT
    return '기본(Standard)', SOFT_GREEN


def _bottom_line_text(m):
    action = localize_action_label(m.get('action_label', '').strip() or m.get('judgment', 'NEUTRAL'))
    es = float(m.get('ensemble_score', 0))
    ctx = localize_context_label(m.get('context', 0))
    raw_judgment = str(m.get('judgment', ''))
    if 'BUY' in raw_judgment:
        return f"결론: {action}. 지금은 매수 우위 구간으로 보이며 분할 접근이 유리합니다. (ES {es:+.1f}, {ctx})"
    if 'SELL' in raw_judgment:
        return f"결론: {action}. 지금은 매도 우위 구간으로 보여 비중 축소나 리스크 관리가 먼저입니다. (ES {es:+.1f}, {ctx})"
    if 'MIXED' in raw_judgment:
        return f"결론: {action}. 방향성이 섞인 구간이라 추격 진입보다 관찰이 낫습니다. (ES {es:+.1f}, {ctx})"
    return f"결론: {action}. 확정 신호가 약해 관찰 후 확인 진입이 적절합니다. (ES {es:+.1f}, {ctx})"


def _narrative_text(m):
    rsi = float(m.get('rsi', 50))
    wt = float(m.get('wt1', 0))
    mom = float(m.get('buy_layers', {}).get('Momentum', 0) - m.get('sell_layers', {}).get('Momentum', 0))
    cmf = float(m.get('cmf', 0))
    bbp = float(m.get('percent_b', 0.5))
    if rsi >= 70 and mom > 0:
        return "RSI는 높지만 모멘텀이 아직 살아 있어, 강한 추세의 막바지 과열인지 여부를 함께 봐야 합니다."
    if rsi <= 30 and mom < 0:
        return "RSI가 낮고 모멘텀도 약해 아직은 섣부른 반등 기대보다 확인 신호가 더 중요합니다."
    if wt < -55 and cmf > 0:
        return "WaveTrend는 과매도권이지만 자금 흐름은 버티고 있어 바닥 반전 후보로 볼 수 있습니다."
    if wt > 55 and cmf < 0:
        return "WaveTrend는 과열권인데 자금 흐름이 약해 고점 소진 가능성을 경계해야 합니다."
    if bbp < 0.2 and mom > 0:
        return "가격은 밴드 하단 근처지만 모멘텀은 개선돼 눌림목 뒤 재상승 가능성을 볼 수 있습니다."
    if bbp > 0.8 and mom < 0:
        return "가격은 밴드 상단 근처인데 모멘텀이 둔해져 단기 조정 위험이 커진 구간입니다."
    return "추세, 모멘텀, 자금 흐름이 한쪽으로 강하게 정렬되지는 않아 확인 신호를 더 보는 편이 좋습니다."


def render_price_header(m, key_prefix="analysis"):
    chg = m['price_change']
    cp = m['price_change_pct']
    cc = 'price-change-up' if chg >= 0 else 'price-change-down'
    ci = '+' if chg >= 0 else '-'
    vr_ = m['volume'] / max(m['avg_volume'], 1)
    raw_jg = str(m.get('judgment', 'NEUTRAL'))
    cf = float(m.get('confidence', 0))
    es = float(m.get('ensemble_score', 0))
    jc = SOFT_GREEN if 'BUY' in raw_jg else (SOFT_RED if 'SELL' in raw_jg else SOFT_AMBER)
    act = localize_action_label(m.get('action_label', ''))
    regime_label = localize_regime_label(m.get('regime'), m.get('regime_label'))
    context_label = localize_context_label(m.get('context', 0))

    hero_chip = f"<span class='ind-mini' style='background:{jc}22;color:{jc};border:1px solid {jc}44' title='최종 판단과 신뢰도'>[{act}] {cf:.0f}%</span>"
    specs = [
        ('ind-b' if m['wt1'] < -20 else ('ind-s' if m['wt1'] > 20 else 'ind-n'), f"WT {m['wt1']:.0f}", "웨이브트렌드 압력"),
        ('ind-b' if m['rsi'] < 40 else ('ind-s' if m['rsi'] > 60 else 'ind-n'), f"RSI {m['rsi']:.0f}", "RSI 모멘텀"),
        ('ind-b' if vr_ > 1.5 else 'ind-n', f"거래량 {vr_:.1f}x", "평균 대비 거래량"),
        ('ind-b' if m['adx'] > 25 else 'ind-n', f"ADX {m['adx']:.0f}", "추세 강도"),
        ('ind-b' if m.get('utbot_dir', 0) == 1 else ('ind-s' if m.get('utbot_dir', 0) == -1 else 'ind-n'), 'UT 매수' if m.get('utbot_dir', 0) == 1 else ('UT 매도' if m.get('utbot_dir', 0) == -1 else 'UT 중립'), "UTBot 방향"),
        ('ind-b' if m.get('hma_rising') else 'ind-s', 'HMA 상승' if m.get('hma_rising') else 'HMA 하락', "헐 이동평균 방향"),
    ]
    ih = hero_chip + "".join([f"<span class='ind-mini {c}' title='{tip}'>{l}</span>" for c, l, tip in specs])
    bottom = _bottom_line_text(m).strip()
    narrative = _narrative_text(m).strip()
    insight_body = f"<p style='margin:0;color:#F8FAFC;font-weight:700'>{bottom}</p>"
    if narrative and narrative not in bottom:
        insight_body += f"<p style='margin:6px 0 0;color:#CBD5E1;font-size:.86rem;font-weight:500'>{narrative}</p>"

    st.markdown(
        f"""
        <div class="price-header fade-up">
            <p style="color:#64748B;font-size:.8rem;margin:0">{m['ticker']} · {m['last_date']} · <b style="color:#A5B4FC">{regime_label}</b> · <span style='color:#A5B4FC'>시장 맥락 {context_label}</span></p>
            <p class="price-big" style="color:#F8FAFC">${m['price']:.2f}<span class="{cc}" style="font-size:1.1rem;margin-left:10px;font-weight:700">{ci}{abs(chg):.2f}({abs(cp):.2f}%)</span></p>
            <div style="margin-top:10px;display:flex;gap:4px;flex-wrap:wrap">{ih}</div>
            <div style='margin-top:12px;background:linear-gradient(140deg,rgba(99,102,241,.13),rgba(15,23,42,.75));border:1px solid rgba(99,102,241,.28);border-radius:10px;padding:10px 12px'>
                {insight_body}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    esc = SOFT_GREEN if es > 0 else (SOFT_RED if es < 0 else SOFT_AMBER)
    es_pct = min(abs(es) / 80 * 100, 100)
    bt_ = float(m.get('buy_total', 0))
    st_ = float(m.get('sell_total', 0))
    ba_ = int(m.get('buy_active', 0))
    sa_ = int(m.get('sell_active', 0))
    bt_pct = min(bt_ / 40 * 100, 100)
    st_pct = min(st_ / 40 * 100, 100)
    h52 = float(m.get('high_52w', m['price']))
    l52 = float(m.get('low_52w', m['price']))
    rng = max(h52 - l52, 0.01)
    pos52 = min(max((m['price'] - l52) / rng * 100, 0), 100)

    def metric_card(title, value, sub, color, fill, bar_color):
        return f"""
        <div style='background:linear-gradient(165deg,rgba(15,23,42,.92),rgba(2,6,23,.86));border:1px solid rgba(148,163,184,.18);border-left:3px solid {color};border-radius:12px;padding:12px 14px;min-height:108px'>
            <p style='margin:0 0 6px;color:#94A3B8;font-size:.74rem;font-weight:700;letter-spacing:.2px'>{title}</p>
            <p style='margin:0;color:{color};font-size:1.55rem;font-weight:800;line-height:1.1'>{value}</p>
            <p style='margin:4px 0 8px;color:#CBD5E1;font-size:.78rem'>{sub}</p>
            <div style='height:7px;background:rgba(148,163,184,.15);border-radius:999px;overflow:hidden'>
                <div style='height:100%;width:{fill:.1f}%;background:{bar_color};border-radius:999px'></div>
            </div>
        </div>
        """

    metric_html = "".join(
        [
            metric_card("종합 점수(Ensemble)", f"{es:+.1f}", f"매수 합의 {m.get('buy_agree', 0)} · 매도 합의 {m.get('sell_agree', 0)}", esc, es_pct, esc),
            metric_card("매수 압력", f"{bt_:.1f}", f"활성 레이어 {ba_}/10", SOFT_GREEN, bt_pct, "linear-gradient(90deg,#247A55,#63D9A2)"),
            metric_card("매도 압력", f"{st_:.1f}", f"활성 레이어 {sa_}/10", SOFT_RED, st_pct, "linear-gradient(90deg,#B85B65,#FF8F96)"),
            metric_card("52주 위치", f"{pos52:.0f}%", f"52주 저점 {l52:.2f} · 고점 {h52:.2f}", SOFT_BLUE, pos52, SOFT_BLUE),
        ]
    )
    st.markdown(f"<div style='display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:10px 0 14px'>{metric_html}</div>", unsafe_allow_html=True)
    _render_ensemble_gauge(es, chart_key=f"{key_prefix}_ensemble_gauge")


def render_judgment_card(m):
    raw_jg = str(m.get('judgment', 'NEUTRAL'))
    jg = localize_judgment_label(raw_jg)
    action = localize_action_label(m.get('action_label', ''))
    es = float(m.get('ensemble_score', 0))
    cf = float(m.get('confidence', 0))
    ba = int(m.get('buy_agree', 0))
    sa = int(m.get('sell_agree', 0))
    veto = str(m.get('veto_flags', '')).strip()
    syn = float(m.get('reversal_synergy', 0))
    pred = float(m.get('prediction_boost', 0))
    detail_text = (str(m.get('judgment_detail', '')).strip() or str(m.get('judgment_reason', '')).strip())
    contrast = str(m.get('contrast_notes', '')).strip()
    jc = SOFT_GREEN if 'BUY' in raw_jg else (SOFT_RED if 'SELL' in raw_jg else SOFT_AMBER)
    cc = 'score-card-buy' if 'BUY' in raw_jg else ('score-card-sell' if 'SELL' in raw_jg else 'score-card-neutral')
    circ = 2 * 3.14159 * 36
    offset = circ * (1 - cf / 100)
    es_norm = min(max((es + 80) / 160 * 100, 0), 100)
    es_c = SOFT_GREEN if es > 0 else SOFT_RED if es < 0 else SOFT_AMBER
    total_agree = max(ba + sa, 1)
    ba_pct = ba / total_agree * 100

    risk_tags = []
    if m.get('smart_money_bearish_div'):
        risk_tags.append(("스마트 머니 약세 다이버전스", SOFT_RED))
    elif m.get('smart_money_bullish_div'):
        risk_tags.append(("자금 흐름 지지", SOFT_GREEN))
    if float(m.get('volume_ratio_20', 1) or 1) < 0.7:
        risk_tags.append((f"저거래량 {float(m.get('volume_ratio_20', 1)):.1f}x", SOFT_AMBER_TEXT))
    if m.get('blowoff_top_hard'):
        risk_tags.append(("급등 과열 경고", SOFT_RED))
    if 'BUY' in raw_jg and float(m.get('vp_long_rr', 1) or 1) < 1:
        risk_tags.append((f"매수 손익비 {float(m.get('vp_long_rr', 1)):.2f}", SOFT_AMBER_TEXT))
    if 'SELL' in raw_jg and float(m.get('vp_short_rr', 1) or 1) < 1:
        risk_tags.append((f"매도 손익비 {float(m.get('vp_short_rr', 1)):.2f}", SOFT_AMBER_TEXT))
    chips = "".join([f"<span style='display:inline-flex;align-items:center;gap:4px;padding:4px 9px;border-radius:999px;background:{col}22;border:1px solid {col}44;color:{col};font-size:.72rem;font-weight:700'>{label}</span>" for label, col in risk_tags])
    detail_html = (
        f"<div style='margin:16px 0;background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.06);border-radius:12px;padding:14px 18px;border-left:3px solid {jc}'>"
        f"<p style='color:#94A3B8;font-size:.72rem;font-weight:700;margin:0 0 6px'>판단 근거 요약</p>"
        f"<p style='color:#CBD5E1;font-size:.82rem;margin:0'>{translate_chart_text(detail_text)}</p>"
        f"</div>"
    ) if detail_text else ""
    contrast_html = (
        f"<p style='color:#CBD5E1;font-size:.8rem;margin:0 0 10px'>{translate_chart_text(contrast)}</p>"
        if contrast else ""
    )
    risk_html = (
        f"<div style='margin:14px 0 0;background:rgba(15,23,42,.58);border:1px solid rgba(148,163,184,.14);border-radius:12px;padding:14px 16px'>"
        f"<p style='color:#94A3B8;font-size:.72rem;font-weight:700;margin:0 0 8px'>위험 점검(Risk Check)</p>"
        f"{contrast_html}"
        f"<div style='display:flex;gap:8px;flex-wrap:wrap'>{chips}</div>"
        f"</div>"
    ) if contrast or risk_tags else ""
    badges = ""
    if abs(syn) > 5:
        badges += f"<span style='background:rgba({'52,211,153' if syn > 0 else '248,113,113'},.12);color:{SOFT_GREEN if syn > 0 else SOFT_RED};padding:3px 8px;border-radius:6px;font-size:.72rem;font-weight:700'>반전 시너지 {syn:+.1f}</span> "
    if abs(pred) > 3:
        badges += f"<span style='background:rgba({'52,211,153' if pred > 0 else '248,113,113'},.12);color:{SOFT_GREEN if pred > 0 else SOFT_RED};padding:3px 8px;border-radius:6px;font-size:.72rem;font-weight:700'>예측 보정 {pred:+.1f}</span>"
    veto_html = f"<div style='margin-top:8px;text-align:center'><span style='background:rgba(243,165,165,.15);color:{SOFT_RED_TEXT};padding:4px 10px;border-radius:6px;font-size:.72rem;font-weight:700'>제한 조건 {veto}</span></div>" if veto else ""

    st.markdown(
        dedent(
            f"""
            <div class="score-card {cc} fade-up">
                <div style="display:flex;align-items:center;justify-content:center;gap:28px;flex-wrap:wrap">
                    <div class="conf-ring"><svg viewBox="0 0 80 80"><circle class="ring-bg" cx="40" cy="40" r="36"/><circle class="ring-fg" cx="40" cy="40" r="36" stroke="{jc}" stroke-dasharray="{circ:.1f}" stroke-dashoffset="{offset:.1f}"/></svg><span class="ring-text" style="color:{jc}">{cf:.0f}%</span></div>
                    <div>
                        <p style="font-size:1.8rem;font-weight:800;color:{jc};margin:0;letter-spacing:-.5px">{action or jg}</p>
                        <p style="margin:8px 0 0;color:#CBD5E1;font-size:.8rem;text-align:center">{jg}</p>
                    </div>
                </div>{detail_html}{risk_html}
                <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-top:14px">
                    <div style="background:rgba(255,255,255,.03);border-radius:10px;padding:12px;text-align:center">
                        <p style="color:#64748B;font-size:.68rem;font-weight:700;margin:0 0 4px">종합 점수</p>
                        <p style="color:{es_c};font-size:1.3rem;font-weight:800;margin:0">{es:+.1f}</p>
                        <div style="height:3px;background:rgba(255,255,255,.06);border-radius:2px;margin-top:6px;overflow:hidden"><div style="height:100%;width:{es_norm}%;background:{es_c};border-radius:2px"></div></div>
                    </div>
                    <div style="background:rgba(255,255,255,.03);border-radius:10px;padding:12px;text-align:center">
                        <p style="color:#64748B;font-size:.68rem;font-weight:700;margin:0 0 4px">매수:매도 합의</p>
                        <p style="color:#F8FAFC;font-size:1.3rem;font-weight:800;margin:0">{ba}:{sa}</p>
                        <div style="height:3px;background:rgba(243,165,165,.28);border-radius:2px;margin-top:6px;overflow:hidden"><div style="height:100%;width:{ba_pct}%;background:{SOFT_GREEN};border-radius:2px"></div></div>
                    </div>
                    <div style="background:rgba(255,255,255,.03);border-radius:10px;padding:12px;text-align:center">
                        <p style="color:#64748B;font-size:.68rem;font-weight:700;margin:0 0 4px">시장 맥락</p>
                        <p style="color:#A5B4FC;font-size:1.05rem;font-weight:800;margin:0">{localize_context_label(m.get('context', 0))}</p>
                        <div style="height:3px;background:rgba(165,180,252,.15);border-radius:2px;margin-top:6px;overflow:hidden"><div style="height:100%;width:100%;background:#A5B4FC;border-radius:2px;opacity:.4"></div></div>
                    </div>
                </div>
                <div style='margin-top:10px;display:flex;justify-content:center;gap:8px;flex-wrap:wrap'>{badges}</div>{veto_html}
            </div>
            """
        ).strip(),
        unsafe_allow_html=True,
    )


def render_committee_panel(m):
    committee = m.get('committee', {})
    if not committee:
        return
    ctx_code = m.get('context', 0)
    ctx_name = CTX_LABELS.get(ctx_code, 'default')
    weights = CONTEXT_WEIGHTS.get(ctx_name, CONTEXT_WEIGHTS['default'])
    cards_html = ""
    vote_map = {'BUY': '매수', 'SELL': '매도', 'NEUTRAL': '중립', 'ABSTAIN': '보류'}
    for ci, cm in enumerate(COMMITTEE_NAMES):
        data = committee.get(cm, {})
        score = data.get('score', 0)
        conv = data.get('conviction', 0)
        vote = data.get('vote', 'NEUTRAL')
        weight = weights[ci] if ci < len(weights) else 0.2
        sc = SOFT_GREEN if score > 0 else (SOFT_RED if score < 0 else '#94A3B8')
        vc = f'background:rgba(126,216,182,.14);color:{SOFT_GREEN}' if vote == 'BUY' else (f'background:rgba(243,165,165,.14);color:{SOFT_RED}' if vote == 'SELL' else ('background:rgba(71,85,105,.3);color:#64748B' if vote == 'ABSTAIN' else f'background:rgba(245,199,123,.14);color:{SOFT_AMBER}'))
        bar_w = min(abs(score) / 40 * 100, 100)
        bdr = f'border-left:3px solid {sc}' if abs(score) > 10 else ''
        cards_html += f"""<div class='cm-card' style='{bdr}'>
            <p class='cm-name'>{localize_committee_name(cm)} · 비중 {weight:.0%}</p>
            <p class='cm-score' style='color:{sc}'>{score:+.0f}</p>
            <span class='cm-vote' style='{vc}'>{vote_map.get(vote, vote)}</span>
            <p style='color:#64748B;font-size:.65rem;margin:4px 0 0'>확신도 {conv:.0f}%</p>
            <div class='cm-mini-bar'><div class='cm-mini-fill' style='width:{bar_w}%;background:{sc}'></div></div>
        </div>"""
    st.markdown(f"<div style='display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-top:12px'>{cards_html}</div>", unsafe_allow_html=True)
    veto = m.get('veto_flags', '')
    if veto:
        st.warning(f"제한 조건: {veto}")
    syn = m.get('reversal_synergy', 0)
    if abs(syn) > 5:
        st.info(f"반전 시너지: {syn:+.1f}")


def render_10layer_bars(m, html_key="analysis"):
    layer_names = ['Trend', 'Momentum', 'Candle', 'BB', 'Volume', 'MF', 'Pattern', 'Combined', 'Leading', 'Lagging']
    layer_labels = {
        'Trend': '추세',
        'Momentum': '모멘텀',
        'Candle': '캔들',
        'BB': '볼린저',
        'Volume': '거래량',
        'MF': '자금 흐름',
        'Pattern': '패턴',
        'Combined': '콤보',
        'Leading': '선행',
        'Lagging': '후행',
    }
    buy_layers = m.get('buy_layers', {})
    sell_layers = m.get('sell_layers', {})
    max_val = 12.0
    rows = []
    for name in layer_names:
        bv = max(float(buy_layers.get(name, 0)), 0.0)
        sv = max(float(sell_layers.get(name, 0)), 0.0)
        bpct = min((bv / max_val) * 50.0, 50.0)
        spct = min((sv / max_val) * 50.0, 50.0)
        bop = 1.0 if bv > 0 else 0.35
        sop = 1.0 if sv > 0 else 0.35
        row_glow = "box-shadow:0 0 10px rgba(99,102,241,.18);" if abs(bv - sv) >= 4 else ""
        rows.append(
            f"<div style='display:grid;grid-template-columns:58px 1fr 58px;gap:10px;align-items:center;margin-bottom:8px;padding:2px;border-radius:10px;{row_glow}'>"
            f"<div style='text-align:right;color:{SOFT_GREEN};font-size:.88rem;font-weight:700;opacity:{bop:.2f}'>{bv:.1f}</div>"
            "<div style='position:relative;height:30px;border-radius:10px;border:1px solid rgba(148,163,184,.2);background:linear-gradient(90deg,rgba(126,216,182,.08),rgba(148,163,184,.04),rgba(243,165,165,.08));overflow:hidden'>"
            f"<div style='position:absolute;left:{50.0 - bpct:.2f}%;top:4px;bottom:4px;width:{bpct:.2f}%;background:linear-gradient(90deg,#237650,#63D9A2);border-radius:6px 0 0 6px;opacity:{bop:.2f}'></div>"
            f"<div style='position:absolute;left:50%;top:4px;bottom:4px;width:{spct:.2f}%;background:linear-gradient(90deg,#FF8F96,#8A4B54);border-radius:0 6px 6px 0;opacity:{sop:.2f}'></div>"
            "<div style='position:absolute;left:50%;top:0;bottom:0;width:1px;background:rgba(226,232,240,.55)'></div>"
            f"<div style='position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);font-size:.72rem;color:#CBD5E1;font-weight:700;background:rgba(2,6,23,.78);padding:2px 8px;border-radius:999px;border:1px solid rgba(148,163,184,.25)'>{layer_labels.get(name, name)}</div>"
            "</div>"
            f"<div style='text-align:left;color:{SOFT_RED};font-size:.88rem;font-weight:700;opacity:{sop:.2f}'>{sv:.1f}</div>"
            "</div>"
        )
    buy_active = int(m.get('buy_active', 0))
    sell_active = int(m.get('sell_active', 0))
    rows_html = "".join(rows)
    panel_html = (
        "<div style='background:rgba(15,19,32,.55);backdrop-filter:blur(12px);border:1px solid rgba(255,255,255,.08);border-radius:14px;padding:16px 14px;margin-bottom:12px'>"
        "<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:8px'>"
        f"<span style='color:{SOFT_GREEN};font-weight:800;font-size:.86rem'>매수 ({buy_active}/10)</span>"
        "<span style='color:#94A3B8;font-size:.76rem;font-weight:700'>10개 레이어 비교</span>"
        f"<span style='color:{SOFT_RED};font-weight:800;font-size:.86rem'>매도 ({sell_active}/10)</span>"
        "</div>"
        "<div style='display:flex;justify-content:center;gap:10px;margin:0 0 10px'>"
        f"<span style='color:{SOFT_GREEN};font-size:.7rem'>왼쪽 = 매수 압력</span>"
        f"<span style='color:{SOFT_RED};font-size:.7rem'>오른쪽 = 매도 압력</span>"
        "</div>"
        f"{rows_html}"
        "</div>"
    )
    panel_h = max(430, 120 + len(layer_names) * 44)
    html_doc = f"<!doctype html><html><head><meta charset='utf-8'><link href='{FONT_IMPORT_URL}' rel='stylesheet'></head><body style='margin:0;background:transparent;color:#E2E8F0;font-family:{FONT_STACK}'><!-- {html_key} -->{panel_html}</body></html>"
    components.html(html_doc, height=panel_h, scrolling=False)


def render_leading_lagging(m):
    lv = translate_chart_text(m.get('leading_verdict', ''))
    lgv = translate_chart_text(m.get('lagging_verdict', ''))
    ac = float(m.get('composite_accel', 0))
    lc = SOFT_GREEN if '+' in f"{ac:+.2f}" or '상승' in lv else (SOFT_RED if '하락' in lv else SOFT_AMBER)
    lgc = SOFT_GREEN if '상승' in lgv else (SOFT_RED if '하락' in lgv else SOFT_AMBER)
    spb = float(m.get('setup_pressure_buy', 0))
    sps = float(m.get('setup_pressure_sell', 0))
    maxsp = max(spb, sps, 1)
    bw = min(spb / maxsp * 50, 50)
    sw = min(sps / maxsp * 50, 50)
    tow_label = f"매수 압력 {spb:.1f}" if spb > sps else (f"매도 압력 {sps:.1f}" if sps > spb else "균형")
    tow_color = SOFT_GREEN if spb > sps else (SOFT_RED if sps > spb else SOFT_AMBER)
    pb_ = float(m.get('percent_b', 0.5))
    cmf_ = float(m.get('cmf', 0))
    cmf_c = SOFT_GREEN if cmf_ > 0.05 else (SOFT_RED if cmf_ < -0.05 else '#94A3B8')
    obv_slope = float(m.get('obv_slope', 0))
    obv_slope_c = SOFT_GREEN if obv_slope > 0 else (SOFT_RED if obv_slope < 0 else '#94A3B8')
    atr_pct = float(m.get('atr_pct', 0))
    volume_ratio = float(m.get('volume_ratio_20', 1))
    vol_c = SOFT_GREEN if volume_ratio >= 1 else (SOFT_AMBER_TEXT if volume_ratio >= 0.7 else SOFT_RED)
    long_rr = float(m.get('vp_long_rr', 1))
    short_rr = float(m.get('vp_short_rr', 1))
    long_rr_c = SOFT_GREEN if long_rr >= 1.35 else (SOFT_AMBER_TEXT if long_rr >= 1 else SOFT_RED)
    short_rr_c = SOFT_GREEN if short_rr >= 1.35 else (SOFT_AMBER_TEXT if short_rr >= 1 else SOFT_RED)
    ma50d = float(m.get('ma50_dist', 0))
    ma200d = float(m.get('ma200_dist', 0))
    ma50c = SOFT_GREEN if ma50d > 0 else SOFT_RED
    ma200c = SOFT_GREEN if ma200d > 0 else SOFT_RED
    size_label, size_color = _risk_size_hint(atr_pct)
    flow_text = '하락 다이버전스' if m.get('smart_money_bearish_div') else ('상승 지지' if m.get('smart_money_bullish_div') else '중립')
    flow_color = SOFT_RED if m.get('smart_money_bearish_div') else (SOFT_GREEN if m.get('smart_money_bullish_div') else '#94A3B8')
    st.markdown(f"""<div style='display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px'>
        <div style='background:rgba(255,255,255,.03);border:1px solid #1E293B;border-radius:12px;padding:16px'>
            <p style='font-weight:700;color:#A5B4FC;margin:0 0 8px;font-size:.85rem'>선행 지표(Leading)</p>
            <p style='color:{lc};font-weight:800;font-size:1.15rem;margin:0 0 8px'>{lv}</p>
            <div style='display:flex;gap:10px;flex-wrap:wrap'>
                <span style='color:#94A3B8;font-size:.78rem'>가속도: <b style='color:{SOFT_GREEN if ac > 0 else SOFT_RED}'>{ac:+.2f}</b></span>
                <span style='color:#94A3B8;font-size:.78rem'>UT: {'매수' if m.get('utbot_dir', 0) == 1 else ('매도' if m.get('utbot_dir', 0) == -1 else '중립')}</span>
                <span style='color:#94A3B8;font-size:.78rem'>Hull: {'상승' if m.get('hma_rising') else '하락'}</span>
            </div>
        </div>
        <div style='background:rgba(255,255,255,.03);border:1px solid #1E293B;border-radius:12px;padding:16px'>
            <p style='font-weight:700;color:#A5B4FC;margin:0 0 8px;font-size:.85rem'>후행 지표(Lagging)</p>
            <p style='color:{lgc};font-weight:800;font-size:1.15rem;margin:0 0 8px'>{lgv}</p>
            <div style='display:flex;gap:14px'>
                <span style='color:#94A3B8;font-size:.78rem'>시장 국면: <b>{localize_regime_label(m.get('regime'), m.get('regime_label'))}</b></span>
                <span style='color:#94A3B8;font-size:.78rem'>상대강도 RS: <b style='color:{SOFT_GREEN if m["rs_ratio"] > 1.03 else (SOFT_RED if m["rs_ratio"] < .97 else SOFT_AMBER)}'>{m['rs_ratio']:.3f}</b></span>
            </div>
        </div>
    </div>""", unsafe_allow_html=True)
    st.markdown(f"""<div style='background:rgba(255,255,255,.03);border:1px solid #1E293B;border-radius:12px;padding:14px;margin-bottom:12px'>
        <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:4px'>
            <span style='color:{SOFT_GREEN};font-size:.78rem;font-weight:700'>매수 압력 {spb:.1f}</span>
            <span style='color:{tow_color};font-size:.78rem;font-weight:700'>{tow_label}</span>
            <span style='color:{SOFT_RED};font-size:.78rem;font-weight:700'>매도 압력 {sps:.1f}</span>
        </div>
        <div class='tow-bar'><div class='tow-buy' style='width:{bw}%'></div><div class='tow-sell' style='width:{sw}%'></div><div class='tow-center'></div></div>
    </div>""", unsafe_allow_html=True)
    snapshot_cards = "".join([
        _mini_stat_card('BB %B', f"{pb_ * 100:.0f}%", SOFT_GREEN if pb_ < 0.3 else (SOFT_RED if pb_ > 0.7 else SOFT_AMBER), '볼린저 밴드 안에서 현재 위치를 보여줍니다.'),
        _mini_stat_card('CMF', f"{cmf_:+.3f}", cmf_c, '0 위면 자금 유입 우위, 0 아래면 자금 이탈 우위로 봅니다.'),
        _mini_stat_card('자금 흐름', flow_text, flow_color, '가격과 자금 흐름이 같은 방향인지, 다이버전스가 있는지 봅니다.'),
        _mini_stat_card('OBV 기울기', f"{obv_slope:+.2f}", obv_slope_c, 'OBV 기울기로 거래량 흐름의 방향을 봅니다.'),
        _mini_stat_card('최근 거래량', f"{volume_ratio:.1f}x", vol_c, '최근 거래량이 20일 평균 대비 얼마나 붙는지 보여줍니다.'),
        _mini_stat_card('매수 손익비', f"{long_rr:.2f}", long_rr_c, '현재가 기준 매수 관점 손익비입니다.'),
        _mini_stat_card('매도 손익비', f"{short_rr:.2f}", short_rr_c, '현재가 기준 매도 관점 손익비입니다.'),
        _mini_stat_card('ATR%', f"{atr_pct:.1f}%", SOFT_BLUE, '평균 변동폭이 현재가 대비 어느 정도인지 보여줍니다.'),
        _mini_stat_card('권장 비중', size_label, size_color, '변동성이 높을수록 포지션 크기를 줄이는 쪽이 안전합니다.'),
        _mini_stat_card('50일선 거리', f"{ma50d:+.1f}%", ma50c, '현재가와 50일선 사이 거리입니다.'),
        _mini_stat_card('200일선 거리', f"{ma200d:+.1f}%", ma200c, '현재가와 200일선 사이 거리입니다.'),
    ])
    st.markdown(f"<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:8px'>{snapshot_cards}</div>", unsafe_allow_html=True)


def render_combined_scans(m):
    scans = m.get('combined_scans', [])
    if not scans:
        st.info("현재 활성화된 콤보 스캔이 없습니다.")
        return
    bn = sum(1 for s in scans if s['dir'] == 'buy')
    sn_ = sum(1 for s in scans if s['dir'] == 'sell')
    t1 = sum(1 for s in scans if s['tier'] == 1)
    hc = '#E8C56C' if t1 > 0 else (SOFT_GREEN if bn > sn_ else (SOFT_RED if sn_ > bn else SOFT_AMBER))
    st.markdown(f"<div style='background:rgba(255,215,0,.06);border:1px solid {hc}33;border-radius:12px;padding:12px;margin-bottom:10px'><span style='font-size:1.2rem;font-weight:800;color:{hc}'>콤보 스캔 {len(scans)}개 활성</span> <span style='color:#94A3B8;margin-left:12px'>T1:{t1} · 매수:{bn} · 매도:{sn_}</span></div>", unsafe_allow_html=True)
    cards = []
    for s in scans:
        tb = {1: '핵심 T1', 2: '보강 T2', 3: '참고 T3'}.get(s['tier'], '참고')
        is_buy = s['dir'] == 'buy'
        is_sell = s['dir'] == 'sell'
        dc_ = SOFT_GREEN if is_buy else (SOFT_RED if is_sell else SOFT_AMBER)
        bg = 'linear-gradient(160deg,rgba(5,46,22,.55),rgba(15,23,42,.6))' if is_buy else ('linear-gradient(160deg,rgba(69,10,10,.55),rgba(30,41,59,.6))' if is_sell else 'linear-gradient(160deg,rgba(120,53,15,.5),rgba(30,41,59,.6))')
        ic = '상승' if is_buy else ('하락' if is_sell else '중립')
        td = "<span style='background:#FFD700;color:#111827;padding:2px 6px;border-radius:999px;font-size:.64rem;font-weight:800'>오늘</span>" if s.get('is_today') else f"<span style='color:#94A3B8;font-size:.72rem'>{s['date']}</span>"
        cards.append(f"""<div style='background:{bg};border:1px solid {dc_}55;border-radius:14px;padding:12px 12px 10px;box-shadow:0 8px 24px rgba(0,0,0,.25)'>
            <div style='display:flex;justify-content:space-between;align-items:center;gap:8px'>
                <span style='color:{dc_};font-weight:800'>{ic} · {s['kor']}</span>
                <span style='color:#E2E8F0;font-size:.68rem;background:rgba(15,23,42,.6);padding:2px 8px;border-radius:999px'>{tb}</span>
            </div>
            <div style='margin-top:8px;display:flex;justify-content:space-between;align-items:center'>
                <span style='color:#60A5FA;font-size:.72rem'>승률 {s['win']}</span>
                {td}
            </div>
        </div>""")
    st.markdown(f"<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px'>{''.join(cards)}</div>", unsafe_allow_html=True)


def render_indicator_help():
    with st.expander("차트 읽는 법 / 지표 설명", expanded=False):
        st.markdown(
            "- `최종 판단 / 신뢰도`: 지금 시점에서 시스템이 보는 기본 방향과 신뢰도입니다.\n"
            "- `위험 점검(Risk Check)`: 스마트 머니 다이버전스, 손익비, 저거래량, 과열 경고를 모아 보여줍니다.\n"
            "- `WT1`: 과매수/과매도 압력을 빠르게 보는 지표입니다.\n"
            "- `ADX`: 추세의 강도를 보여주며 방향 자체를 뜻하지는 않습니다.\n"
            "- `CMF / OBV 기울기`: 자금 유입과 이탈 흐름을 보는 보조 지표입니다.\n"
            "- `종합 점수(Ensemble Score)`: -100~+100 범위의 종합 방향 점수입니다.\n"
            "- `10개 레이어`: 추세, 모멘텀, 구조, 자금 흐름 등이 매수/매도 쪽으로 얼마나 기여하는지 비교합니다."
        )


def render_analysis(msg, key_prefix="analysis"):
    m, fj = msg.get('meta'), msg.get('fig_json')
    if m:
        render_price_header(m, key_prefix=key_prefix)
    if m or fj:
        t0, t1, t2, t3, t4 = st.tabs(["차트", "판단/리스크", "10개 레이어", "콤보 스캔", "기업 정보"])
        with t0:
            if fj:
                fig = load_chart_figure(fj)
                st.plotly_chart(fig, use_container_width=True, theme=None, config={'displaylogo': False, 'modeBarButtonsToRemove': ['lasso2d', 'select2d']}, key=f"{key_prefix}_price_chart")
                st.caption("*캔들 툴팁, 거래량 프로파일(VP), 자동 추세선/평행채널, 패턴 오버레이를 제공합니다. 모바일에서는 판단 카드 확인 후 차트를 열면 더 읽기 쉽습니다.")
        with t1:
            if m:
                render_judgment_card(m)
                st.markdown("#### 5위원회 종합 판단")
                render_committee_panel(m)
                st.markdown("---")
                render_leading_lagging(m)
                render_indicator_help()
        with t2:
            if m:
                render_10layer_bars(m, html_key=f"{key_prefix}_10layer")
        with t3:
            if m:
                render_combined_scans(m)
        with t4:
            if m:
                render_company_details(m['ticker'], key_prefix=f"{key_prefix}_company")

# Re-declare with normalized labels/caption so the active definition matches the current chart features.
def render_analysis(msg, key_prefix="analysis"):
    m,fj=msg.get('meta'),msg.get('fig_json')
    if m:
        render_price_header(m, key_prefix=key_prefix)
    if m or fj:
        t0,t1,t2,t3,t4=st.tabs(["차트","판단/리스크","10-Layer","콤보스캔","기업정보"])
        with t0:
            if fj:
                fig=load_chart_figure(fj)
                st.plotly_chart(fig,use_container_width=True,theme=None,config={'displaylogo':False,'modeBarButtonsToRemove':['lasso2d','select2d']}, key=f"{key_prefix}_price_chart")
                st.caption("*캔들 툴팁, 우측 매물대(VP), 자동 추세선/평행채널, 패턴 오버레이를 제공합니다. 모바일에서는 판단 카드 확인 후 차트를 열면 더 읽기 쉽습니다.")
        with t1:
            if m:
                render_judgment_card(m)
                st.markdown("#### 5-Committee Ensemble")
                render_committee_panel(m)
                st.markdown("---")
                render_leading_lagging(m)
                render_indicator_help()
        with t2:
            if m:render_10layer_bars(m, html_key=f"{key_prefix}_10layer")
        with t3:
            if m:render_combined_scans(m)
        with t4:
            if m:render_company_details(m['ticker'], key_prefix=f"{key_prefix}_company")
