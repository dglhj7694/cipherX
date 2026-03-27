import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai
import html
import json
import re
import yfinance as yf
from datetime import datetime
from textwrap import dedent
from config import *
from chart import build_metadata, build_chart
from company_details import render_company_details
from localization import (
    localize_action_label,
    localize_committee_name,
    localize_context_label,
    localize_judgment_label,
    localize_regime_label,
    translate_chart_text,
)
from sectors import SECTOR_GROUPS
from theme import FONT_IMPORT_URL, FONT_STACK

SOFT_GREEN = '#63D9A2'
SOFT_GREEN_TEXT = '#B8F1D5'
SOFT_RED = '#FF8F96'
SOFT_RED_TEXT = '#FFD2D7'
SOFT_AMBER = '#F6C35E'
SOFT_AMBER_TEXT = '#F8DE9A'
SOFT_BLUE = '#A5B4FC'

_US_MARKET_DECK_HEIGHT = 728
_US_MARKET_DEFAULT_DURATION = 7000
_US_MARKET_TEXT_HEAVY_DURATION = 10000
_US_MARKET_HISTORY_PERIOD = "6mo"
_US_MARKET_MOVER_LIMIT = 120
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
    ("CL=F", "WTI"),
    ("BTC-USD", "비트코인"),
]
_MARKET_SYMBOL_NORMALIZATION_MAP = {
    "BRK.B": "BRK-B",
    "BF.B": "BF-B",
}
_MARKET_SYMBOL_FALLBACKS = {
    "DX-Y.NYB": ("DX=F",),
    "KRW=X": ("USDKRW=X",),
}
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


def _build_sector_sentence(sector_rows):
    if not sector_rows:
        return "섹터 데이터가 아직 동기화 중입니다."
    positive = sum(1 for row in sector_rows if (row.get("change_pct") or 0) > 0)
    total = len(sector_rows)
    strongest = max(sector_rows, key=lambda row: row.get("change_pct") if row.get("change_pct") is not None else -999)
    weakest = min(sector_rows, key=lambda row: row.get("change_pct") if row.get("change_pct") is not None else 999)
    return f"{total}개 섹터 중 {positive}개가 상승했습니다. {strongest['label']}이 주도했고 {weakest['label']}이 가장 약했습니다."


def _build_driver_candidates(benchmarks, macro, sector_rows):
    drivers = []
    spy = benchmarks.get("SPY", {})
    qqq = benchmarks.get("QQQ", {})
    iwm = benchmarks.get("IWM", {})
    vix = benchmarks.get("VIX", {})
    tnx = macro.get("10Y", {})
    dxy = macro.get("DXY", {})
    fx = macro.get("USDKRW", {})
    wti = macro.get("WTI", {})
    btc = macro.get("BTC", {})
    sector_breadth = sum(1 for row in sector_rows if (row.get("change_pct") or 0) > 0)

    spy_chg = spy.get("change_pct")
    qqq_chg = qqq.get("change_pct")
    iwm_chg = iwm.get("change_pct")
    vix_chg = vix.get("change_pct")
    tnx_bps = ((tnx.get("price") or 0) - (tnx.get("prev_close") or 0)) * 10 if tnx else None
    dxy_chg = dxy.get("change_pct")
    fx_chg = fx.get("change_pct")
    wti_chg = wti.get("change_pct")
    btc_chg = btc.get("change_pct")

    if qqq_chg is not None and spy_chg is not None:
        if qqq_chg < spy_chg - 0.45:
            drivers.append("나스닥이 대형주 전체보다 더 약해 성장주 압박이 크게 나타났습니다.")
        elif qqq_chg > spy_chg + 0.45:
            drivers.append("대형 기술주가 상대 강세를 보이며 시장 주도권을 일부 되찾았습니다.")

    if iwm_chg is not None and spy_chg is not None:
        if iwm_chg > spy_chg + 0.5:
            drivers.append("소형주가 선방해 위험선호가 완전히 꺾이진 않았습니다.")
        elif iwm_chg < spy_chg - 0.5:
            drivers.append("소형주 약세가 더 깊어지며 시장 전반의 위험회피 성격이 강해졌습니다.")

    if vix_chg is not None:
        if vix_chg >= 5:
            drivers.append("VIX 급등은 헤지 수요 확대와 변동성 경계 심리 강화를 보여줬습니다.")
        elif vix_chg <= -4:
            drivers.append("VIX가 빠르게 낮아지며 위험 프리미엄이 다소 완화됐습니다.")

    if tnx_bps is not None:
        if tnx_bps >= 4:
            drivers.append("10년물 금리 상승이 밸류에이션 부담을 키워 성장주에 불리하게 작용했습니다.")
        elif tnx_bps <= -4:
            drivers.append("장기금리 하락이 성장주에 우호적인 배경을 만들었습니다.")

    if dxy_chg is not None:
        if dxy_chg >= 0.35:
            drivers.append("달러 강세가 위험자산 전반에 부담으로 작용했습니다.")
        elif dxy_chg <= -0.35:
            drivers.append("달러 압력이 완화되며 위험자산이 숨을 돌렸습니다.")

    if fx_chg is not None:
        if fx_chg >= 0.45:
            drivers.append("원/달러 환율 상승은 대외 불안과 달러 선호 심리를 반영했습니다.")
        elif fx_chg <= -0.45:
            drivers.append("원/달러 환율 안정은 위험심리 완화에 우호적으로 작용했습니다.")

    if wti_chg is not None and abs(wti_chg) >= 1.8:
        if wti_chg > 0:
            drivers.append("유가 강세가 인플레이션 우려를 다시 자극했습니다.")
        else:
            drivers.append("유가 약세가 물가 부담 완화 기대를 키웠습니다.")

    if btc_chg is not None and abs(btc_chg) >= 2.5:
        if btc_chg > 0:
            drivers.append("비트코인 강세는 투기적 위험선호가 완전히 꺾이지 않았음을 시사했습니다.")
        else:
            drivers.append("비트코인 약세는 고베타 자산 전반의 심리 둔화와 맞물렸습니다.")

    if sector_rows:
        if sector_breadth <= 3:
            drivers.append(f"상승 섹터가 {sector_breadth}/{len(sector_rows)}개에 그쳐 시장 확산도가 약했습니다.")
        elif sector_breadth >= len(sector_rows) - 2:
            drivers.append(f"{sector_breadth}/{len(sector_rows)}개 섹터가 동반 상승해 광범위한 매수 흐름이 나타났습니다.")

    return drivers[:4]


def _fallback_market_headline(benchmarks, sector_rows):
    spy = benchmarks.get("SPY", {}).get("change_pct")
    qqq = benchmarks.get("QQQ", {}).get("change_pct")
    dia = benchmarks.get("DIA", {}).get("change_pct")
    iwm = benchmarks.get("IWM", {}).get("change_pct")
    vix = benchmarks.get("VIX", {}).get("change_pct")
    breadth = sum(1 for row in sector_rows if (row.get("change_pct") or 0) > 0)
    total = len(sector_rows) or 11
    if spy is None:
        return "미국장 데이터가 아직 로딩 중입니다."
    values = [value for value in [spy, qqq, dia, iwm] if value is not None]
    avg = sum(values) / max(1, len(values))
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


def _fallback_market_insight(benchmarks, macro, sector_rows):
    spy = benchmarks.get("SPY", {}).get("change_pct")
    qqq = benchmarks.get("QQQ", {}).get("change_pct")
    vix = benchmarks.get("VIX", {}).get("change_pct")
    tnx_bps = ((macro.get("10Y", {}).get("price") or 0) - (macro.get("10Y", {}).get("prev_close") or 0)) * 10 if macro.get("10Y") else 0
    breadth = sum(1 for row in sector_rows if (row.get("change_pct") or 0) > 0)
    total = len(sector_rows) or 11
    if spy is None:
        return {
            "insight": "핵심 입력값이 아직 동기화 중이라 오늘 인사이트는 데이터가 안정되면 다시 갱신됩니다.",
            "watchlist": ["SPY와 QQQ 종가 확인", "VIX와 10년물 재확인", "섹터 확산도 업데이트 대기"],
        }
    if (vix or 0) > 4 and tnx_bps > 0:
        insight = "금리와 변동성이 함께 오를 때는 반등 추격보다 확인 후 대응이 더 중요합니다."
    elif (qqq or 0) > (spy or 0) and breadth >= total // 2:
        insight = "기술주 주도력이 이어질수록 지수보다 리더 종목 추적이 더 중요합니다."
    elif breadth <= 3:
        insight = "시장 약세가 넓게 퍼질수록 신규 추격보다 방어와 현금 관리가 우선입니다."
    else:
        insight = "한 방향 베팅보다 섹터 상대강도와 금리 민감도를 함께 보는 대응이 유효합니다."
    watchlist = [
        "QQQ가 SPY 대비 상대강도를 회복하는지 확인",
        f"섹터 확산도({breadth}/{total})가 개선되는지 확인",
        "VIX와 10년물이 함께 진정되는지 확인",
    ]
    return {"insight": insight, "watchlist": watchlist}


def _market_mover_universe(limit=_US_MARKET_MOVER_LIMIT):
    raw = list(_US_MARKET_MEGA_CAPS)
    for tickers in SECTOR_GROUPS.values():
        if isinstance(tickers, (list, tuple, set)):
            raw.extend(str(ticker or "").strip() for ticker in tickers)
    filtered = []
    for ticker in _ordered_unique(_normalize_market_symbol(ticker) for ticker in raw):
        if not re.fullmatch(r"[A-Z0-9\-=]+", ticker):
            continue
        filtered.append(ticker)
        if len(filtered) >= limit:
            break
    return tuple(filtered)


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


def _extract_json_object(text):
    if not text:
        return "{}"
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if fenced:
        return fenced.group(1)
    raw = re.search(r"\{.*\}", text, re.S)
    return raw.group(0) if raw else "{}"


@st.cache_data(ttl=1800, show_spinner=False)
def _download_market_history(tickers, period=_US_MARKET_HISTORY_PERIOD):
    expanded = []
    for ticker in tickers:
        expanded.extend(_market_symbol_candidates(ticker))
    symbols = tuple(_ordered_unique(symbol for symbol in expanded if symbol))
    if not symbols:
        return pd.DataFrame()
    try:
        history = yf.download(
            tickers=list(symbols),
            period=period,
            interval="1d",
            group_by="ticker",
            auto_adjust=False,
            progress=False,
            threads=True,
        )
    except Exception:
        return pd.DataFrame()
    return history.sort_index() if isinstance(history, pd.DataFrame) else pd.DataFrame()


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
            'Format: {"headline":"...","drivers":["...","...","..."],"insight":"...","watchlist":["...","...","..."]}\n'
            "Rules:\n"
            "- headline: one short sentence.\n"
            "- drivers: two to three short bullets.\n"
            "- insight: one sentence with a practical next-session angle.\n"
            "- watchlist: two to three short points.\n"
            "- Do not mention unverified news or events.\n"
            f"- market_date_key: {market_date_key}\n"
            f"- data: {summary_json}\n"
        )
        response = model.generate_content(prompt)
        raw_text = getattr(response, "text", "") or str(response)
        parsed = json.loads(_extract_json_object(raw_text))
        return {
            "headline": str(parsed.get("headline", "")).strip(),
            "drivers": [str(item).strip() for item in parsed.get("drivers", []) if str(item).strip()],
            "insight": str(parsed.get("insight", "")).strip(),
            "watchlist": [str(item).strip() for item in parsed.get("watchlist", []) if str(item).strip()],
        }
    except Exception:
        return {}


def build_us_market_daily_payload():
    benchmark_symbols = tuple(symbol for symbol, _ in _US_MARKET_BENCHMARKS)
    macro_symbols = tuple(symbol for symbol, _ in _US_MARKET_MACRO)
    sector_symbols = tuple(symbol for symbol, _ in _US_SECTOR_ETFS)
    benchmark_history = _download_market_history(benchmark_symbols + macro_symbols + sector_symbols)
    mover_history = _download_market_history(_market_mover_universe())

    benchmark_snapshots = {}
    for symbol, _ in _US_MARKET_BENCHMARKS:
        label = "VIX" if symbol == "^VIX" else symbol
        benchmark_snapshots[label] = _build_snapshot(_extract_symbol_frame(benchmark_history, symbol))

    macro_snapshots = {}
    macro_labels = {"^TNX": "10Y", "DX-Y.NYB": "DXY", "KRW=X": "USDKRW", "CL=F": "WTI", "BTC-USD": "BTC"}
    for symbol, _ in _US_MARKET_MACRO:
        macro_snapshots[macro_labels[symbol]] = _build_snapshot(_extract_symbol_frame(benchmark_history, symbol))

    sector_rows = []
    for symbol, label in _US_SECTOR_ETFS:
        snapshot = _build_snapshot(_extract_symbol_frame(benchmark_history, symbol))
        sector_rows.append({"symbol": symbol, "label": label, "snapshot": snapshot, "change_pct": snapshot.get("change_pct")})
    sector_rows = [row for row in sector_rows if row.get("snapshot")]
    sector_sorted = sorted(sector_rows, key=lambda row: row.get("change_pct") if row.get("change_pct") is not None else -999, reverse=True)

    movers = []
    for symbol in _market_mover_universe():
        snapshot = _build_snapshot(_extract_symbol_frame(mover_history, symbol))
        if not snapshot or snapshot.get("change_pct") is None:
            continue
        movers.append({"symbol": symbol, "snapshot": snapshot, "change_pct": snapshot.get("change_pct")})
    movers_sorted = sorted(movers, key=lambda row: row["change_pct"], reverse=True)
    gainers = movers_sorted[:3]
    losers = list(reversed(movers_sorted[-3:])) if movers_sorted else []

    market_dt = None
    for candidate in [benchmark_snapshots.get("SPY", {}).get("date"), benchmark_snapshots.get("QQQ", {}).get("date")]:
        if candidate is not None:
            market_dt = candidate
            break
    market_date_key = market_dt.strftime("%Y-%m-%d") if market_dt is not None else datetime.utcnow().strftime("%Y-%m-%d")

    driver_candidates = _build_driver_candidates(benchmark_snapshots, macro_snapshots, sector_sorted)
    fallback_insight = _fallback_market_insight(benchmark_snapshots, macro_snapshots, sector_sorted)

    summary_payload = {
        "market_date": market_date_key,
        "benchmarks": {label: snapshot.get("change_pct") for label, snapshot in benchmark_snapshots.items()},
        "macro": {
            "10Y_bps": ((macro_snapshots.get("10Y", {}).get("price") or 0) - (macro_snapshots.get("10Y", {}).get("prev_close") or 0)) * 10,
            "DXY_pct": macro_snapshots.get("DXY", {}).get("change_pct"),
            "USDKRW_pct": macro_snapshots.get("USDKRW", {}).get("change_pct"),
            "WTI_pct": macro_snapshots.get("WTI", {}).get("change_pct"),
            "BTC_pct": macro_snapshots.get("BTC", {}).get("change_pct"),
        },
        "sector_top": [f"{row['symbol']} {row['change_pct']:+.2f}%" for row in sector_sorted[:3] if row.get("change_pct") is not None],
        "sector_bottom": [f"{row['symbol']} {row['change_pct']:+.2f}%" for row in sector_sorted[-3:] if row.get("change_pct") is not None],
        "gainers": [f"{row['symbol']} {row['change_pct']:+.2f}%" for row in gainers],
        "losers": [f"{row['symbol']} {row['change_pct']:+.2f}%" for row in losers],
        "breadth": {
            "up": sum(1 for row in sector_sorted if (row.get("change_pct") or 0) > 0),
            "total": len(sector_sorted),
        },
    }
    ai_copy = _generate_us_market_ai_copy(market_date_key, json.dumps(summary_payload, ensure_ascii=False))

    headline = ai_copy.get("headline") or _fallback_market_headline(benchmark_snapshots, sector_sorted)
    drivers = ai_copy.get("drivers") or driver_candidates or ["시장 방향성은 유지됐지만 거시 변수의 압박도 여전히 크게 작용했습니다."]
    insight = ai_copy.get("insight") or fallback_insight["insight"]
    watchlist = ai_copy.get("watchlist") or fallback_insight["watchlist"]

    sector_breadth = sum(1 for row in sector_sorted if (row.get("change_pct") or 0) > 0)
    sector_total = len(sector_sorted) or len(_US_SECTOR_ETFS)

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
        _build_snapshot_metric("WTI", "국제유가", macro_snapshots.get("WTI", {})),
        _build_snapshot_metric("BTC", "위험선호 프록시", macro_snapshots.get("BTC", {})),
    ]
    market_driver_metrics = [
        macro_metrics[1],
        macro_metrics[2],
        macro_metrics[0],
        macro_metrics[3],
        macro_metrics[4],
    ]
    sector_metrics = [_build_snapshot_metric(row["symbol"], row["label"], row["snapshot"]) for row in (sector_sorted[:3] + list(reversed(sector_sorted[-3:])))]
    mover_metrics = [_build_snapshot_metric(row["symbol"], _mover_reason(row["snapshot"]), row["snapshot"]) for row in gainers + losers]
    insight_metrics = [
        {"label": "확산도", "value": f"{sector_breadth}/{sector_total}", "delta": "상승 섹터", "note": "섹터 전반 흐름", "tone": "positive" if sector_breadth >= sector_total / 2 else "negative"},
        _build_snapshot_metric("VIX", "변동성", benchmark_snapshots.get("VIX", {}), inverse=True),
        _build_snapshot_metric("10Y", "미 국채 10년", macro_snapshots.get("10Y", {}), inverse=True),
        _build_snapshot_metric("USD/KRW", "원/달러 환율", macro_snapshots.get("USDKRW", {}), inverse=True),
    ]
    market_driver_bullets = [
        _build_market_bullet(
            f"달러/환율 체크: DXY {macro_metrics[1]['delta'] or 'N/A'} / USD/KRW {macro_metrics[2]['delta'] or 'N/A'}",
            _resolve_market_tone(macro_metrics[1]["tone"], macro_metrics[2]["tone"]),
        )
    ] + [_build_market_bullet(text, _infer_market_text_tone(text)) for text in drivers[:2]]

    cards = [
        {
            "id": "main_headline",
            "title": "오늘 시장 한줄",
            "subtitle": headline,
            "metrics": main_metrics,
            "bullets": [
                _build_market_bullet(
                    f"거시 점검: 10Y {macro_metrics[0]['value']} ({macro_metrics[0]['delta'] or 'N/A'}) / DXY {macro_metrics[1]['delta'] or 'N/A'}",
                    _resolve_market_tone(macro_metrics[0]["tone"], macro_metrics[1]["tone"]),
                ),
                _build_market_bullet(
                    f"환율/원자재: USD/KRW {macro_metrics[2]['delta'] or 'N/A'} / WTI {macro_metrics[3]['delta'] or 'N/A'}",
                    _resolve_market_tone(macro_metrics[2]["tone"], macro_metrics[3]["tone"]),
                ),
                _build_market_bullet(
                    f"리스크 자산: BTC {macro_metrics[4]['delta'] or 'N/A'} / 섹터 확산도 {sector_breadth}/{sector_total}",
                    _resolve_market_tone(
                        macro_metrics[4]["tone"],
                        "positive" if sector_breadth >= sector_total / 2 else "negative",
                    ),
                ),
            ],
            "tone": _tone_from_change(benchmark_snapshots.get("SPY", {}).get("change_pct")),
            "chart_hint": "SPY / QQQ / DIA / IWM / VIX",
            "duration_ms": _US_MARKET_DEFAULT_DURATION,
        },
        {
            "id": "market_drivers",
            "title": "움직인 이유",
            "subtitle": "금리, 달러, 환율, 유가, 비트코인 흐름이 시장 강약을 설명합니다.",
            "metrics": market_driver_metrics,
            "bullets": market_driver_bullets,
            "tone": _tone_from_change(benchmark_snapshots.get("SPY", {}).get("change_pct")),
            "chart_hint": "10Y / DXY / USD/KRW / WTI / BTC",
            "duration_ms": _US_MARKET_TEXT_HEAVY_DURATION,
        },
        {
            "id": "sector_pressure",
            "title": "섹터 온도",
            "subtitle": _build_sector_sentence(sector_sorted),
            "metrics": sector_metrics,
            "bullets": [_build_market_bullet(f"강세 상위: {row['symbol']} {row['change_pct']:+.2f}% / {row['label']}", "positive") for row in sector_sorted[:3]] + [_build_market_bullet(f"약세 상위: {row['symbol']} {row['change_pct']:+.2f}% / {row['label']}", "negative") for row in list(reversed(sector_sorted[-3:]))],
            "tone": "positive" if sector_breadth >= sector_total / 2 else "negative",
            "chart_hint": f"상승 섹터 {sector_breadth}/{sector_total}",
            "duration_ms": _US_MARKET_TEXT_HEAVY_DURATION,
        },
        {
            "id": "top_movers",
            "title": "주요 등락주",
            "subtitle": "메가캡과 핵심 유니버스에서 수급이 몰린 종목입니다.",
            "metrics": mover_metrics,
            "bullets": [_build_market_bullet(f"{row['symbol']} {row['change_pct']:+.2f}% / {_mover_reason(row['snapshot'])}", "positive") for row in gainers] + [_build_market_bullet(f"{row['symbol']} {row['change_pct']:+.2f}% / {_mover_reason(row['snapshot'])}", "negative") for row in losers],
            "tone": _tone_from_change(sum(row["change_pct"] for row in gainers + losers) / max(1, len(gainers + losers)) if gainers or losers else 0),
            "chart_hint": f"추적 유니버스 {len(movers_sorted)}개",
            "duration_ms": _US_MARKET_TEXT_HEAVY_DURATION,
        },
        {
            "id": "daily_insight",
            "title": "오늘 미장 인사이트",
            "subtitle": insight,
            "metrics": insight_metrics,
            "bullets": [_build_market_bullet(text, _infer_market_text_tone(text)) for text in watchlist[:3]],
            "tone": _tone_from_change(benchmark_snapshots.get("QQQ", {}).get("change_pct")),
            "chart_hint": "다음 세션 체크리스트",
            "duration_ms": _US_MARKET_TEXT_HEAVY_DURATION,
        },
    ]

    return {
        "market_date_label": _format_market_date(market_dt),
        "headline": headline,
        "cards": cards,
    }


def _build_us_market_daily_doc(payload):
    payload_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
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
            .head { display: flex; justify-content: space-between; gap: 12px; padding: 18px 14px 8px; }
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
            .bullet { display: grid; grid-template-columns: 12px minmax(0,1fr); gap: 10px; padding: 11px 12px; border-radius: 14px; border: 1px solid rgba(148,163,184,.12); background: rgba(255,255,255,.03); transition: border-color .28s ease, background .28s ease; }
            .bullet[data-tone="positive"] { border-color: rgba(99,217,162,.16); background: linear-gradient(180deg, rgba(99,217,162,.06), rgba(255,255,255,.02)); }
            .bullet[data-tone="negative"] { border-color: rgba(255,143,150,.16); background: linear-gradient(180deg, rgba(255,143,150,.06), rgba(255,255,255,.02)); }
            .bullet[data-tone="neutral"] { border-color: rgba(148,163,184,.16); background: linear-gradient(180deg, rgba(148,163,184,.05), rgba(255,255,255,.02)); }
            .bullet i { width: 10px; height: 10px; margin-top: 5px; border-radius: 999px; background: linear-gradient(180deg, rgba(148,163,184,.92), rgba(100,116,139,.82)); box-shadow: 0 0 0 4px rgba(148,163,184,.10); transition: background .28s ease, box-shadow .28s ease; }
            .bullet[data-tone="positive"] i { background: linear-gradient(180deg, rgba(99,217,162,.98), rgba(45,212,191,.82)); box-shadow: 0 0 0 4px rgba(99,217,162,.14); }
            .bullet[data-tone="negative"] i { background: linear-gradient(180deg, rgba(255,143,150,.98), rgba(251,113,133,.82)); box-shadow: 0 0 0 4px rgba(255,143,150,.14); }
            .bullet[data-tone="neutral"] i { background: linear-gradient(180deg, rgba(148,163,184,.92), rgba(100,116,139,.82)); box-shadow: 0 0 0 4px rgba(148,163,184,.10); }
            .bullet span { font-size: .90rem; line-height: 1.56; font-weight: 700; }
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
              display: flex;
              align-items: center;
              justify-content: space-between;
              gap: 12px;
              margin-top: 2px;
              padding: 12px 14px 14px;
              background: linear-gradient(180deg, rgba(10,15,28,0), rgba(10,15,28,.94) 30%);
            }
            .nav { display: inline-flex; align-items: center; gap: 8px; }
            .btn { position: relative; z-index: 4; min-width: 44px; height: 38px; padding: 0 12px; border-radius: 999px; border: 1px solid rgba(148,163,184,.14); background: rgba(255,255,255,.04); color: var(--strong); font-size: .78rem; font-weight: 900; cursor: pointer; transition: border-color .28s ease, background .28s ease; }
            .dots { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
            .dot { width: 11px; height: 11px; border: 0; border-radius: 999px; background: rgba(148,163,184,.32); cursor: pointer; }
            .dot.active { width: 24px; background: var(--tone-progress); }
            .index { color: var(--muted); font-size: .76rem; font-weight: 800; }
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
              .foot { flex-direction: column; align-items: stretch; }
              .nav { justify-content: space-between; }
            }
            @media (max-width: 560px) {
              .deck { padding: 8px; border-radius: 18px; }
              .head { padding: 16px 12px 8px; }
              .foot { padding: 10px 12px 12px; }
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
              <div class="nav"><button class="btn" id="prevBtn" type="button">이전</button><div class="dots" id="deckDots"></div><button class="btn" id="nextBtn" type="button">다음</button></div>
              <div class="index" id="deckIndex"></div>
            </div>
          </div>
          <script>
            const payload = __PAYLOAD__;
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
            let rafId = null;
            let startedAt = 0;
            let elapsedBeforePause = 0;
            let currentDuration = 7000;
            function card() { return cards[activeIndex] || {}; }
            function loopIndex(index) { return cards.length ? (index + cards.length) % cards.length : 0; }
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
            function renderBullets(bullets) {
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
            function render() {
              const current = card();
              currentDuration = Number(current.duration_ms) || 7000;
              deck.dataset.tone = "neutral";
              deckDate.textContent = payload.market_date_label || "";
              cardTitle.textContent = current.title || "";
              cardSubtitle.textContent = current.subtitle || "";
              cardHint.textContent = current.chart_hint || "";
              renderMetrics(current.metrics);
              renderBullets(current.bullets);
              renderDots();
              deckIndex.textContent = cards.length ? (activeIndex + 1) + " / " + cards.length + " 카드" : "";
              startTicker(true);
            }
            prevBtn.addEventListener("click", () => { activeIndex = loopIndex(activeIndex - 1); render(); });
            nextBtn.addEventListener("click", () => { activeIndex = loopIndex(activeIndex + 1); render(); });
            deck.addEventListener("mouseenter", pauseTicker);
            deck.addEventListener("mouseleave", resumeTicker);
            deck.addEventListener("touchstart", pauseTicker, { passive: true });
            deck.addEventListener("touchend", resumeTicker, { passive: true });
            deck.addEventListener("touchcancel", resumeTicker, { passive: true });
            if (cards.length) {
              render();
            } else {
              deck.dataset.tone = "neutral";
              deckDate.textContent = payload.market_date_label || "";
              cardTitle.textContent = "오늘 미국장 브리핑";
              cardSubtitle.textContent = "시장 데이터가 아직 동기화 중입니다.";
              cardHint.textContent = "시장 데이터 동기화";
              renderBullets(["SPY, QQQ, VIX, 10년물 입력값을 불러오는 중입니다."]);
            }
          </script>
        </body>
        </html>
        """
    ).strip()
    return template.replace("__FONT_IMPORT_URL__", FONT_IMPORT_URL).replace("__FONT_STACK__", FONT_STACK).replace("__PAYLOAD__", payload_json)


def _render_us_market_daily_deck(payload):
    components.html(
        _build_us_market_daily_doc(payload),
        height=_US_MARKET_DECK_HEIGHT,
        scrolling=False,
    )


def render_market_home_dashboard():
    payload = build_us_market_daily_payload()
    headline_copy = html.escape(
        payload.get("headline")
        or "무엇이 미국장을 움직였는지, 어디에 강약이 몰렸는지, 다음 세션에서 무엇을 볼지 빠르게 정리합니다."
    )
    badges_html = "".join(
        [
            _market_badge("미국 시장", "accent"),
            _market_badge("5장 브리핑", "warning"),
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
            if fj:fig=go.Figure(json.loads(fj));st.plotly_chart(fig,use_container_width=True,theme=None,config={'displaylogo':False,'modeBarButtonsToRemove':['lasso2d','select2d']}, key=f"{key_prefix}_price_chart");st.caption("*캔들 오버 시 툴팁, 강/약 시그널 캔들 하이라이트, 우측 매물대(VP) 오버레이를 제공합니다. 모바일에서는 판단 카드 확인 후 차트를 열면 더 읽기 쉽습니다.")
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
                fig = go.Figure(json.loads(fj))
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
                fig=go.Figure(json.loads(fj))
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
