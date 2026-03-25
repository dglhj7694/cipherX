from __future__ import annotations

from typing import Any


CONTEXT_LABELS_KO = {
    0: "기본 흐름(Basic)",
    1: "극과매도(Extreme Oversold)",
    2: "극과매수(Extreme Overbought)",
    3: "강한 상승 추세(Strong Uptrend)",
    4: "강한 하락 추세(Strong Downtrend)",
    5: "매집 구간(Accumulation)",
    6: "분산 구간(Distribution)",
    7: "횡보 구간(Range)",
    8: "바닥 다지기(Bottoming)",
    9: "천장 형성(Topping)",
    10: "거래량 감소(Volume Dry-Up)",
    11: "급등락 직후(Post Explosion)",
}

CONTEXT_SLUG_TO_CODE = {
    "default": 0,
    "extreme_oversold": 1,
    "extreme_overbought": 2,
    "strong_trend_up": 3,
    "strong_trend_down": 4,
    "accumulation": 5,
    "distribution": 6,
    "ranging": 7,
    "bottoming": 8,
    "topping": 9,
    "vol_dry": 10,
    "post_explosion": 11,
}

PATTERN_NAME_MAP = {
    "Symmetrical Triangle": "대칭 삼각형(Symmetrical Triangle)",
    "Ascending Triangle": "상승 삼각형(Ascending Triangle)",
    "Descending Triangle": "하락 삼각형(Descending Triangle)",
    "Rising Wedge": "상승 쐐기(Rising Wedge)",
    "Falling Wedge": "하락 쐐기(Falling Wedge)",
    "Channel": "평행 채널(Channel)",
    "Bull Flag": "상승 깃발형(Bull Flag)",
    "Bear Flag": "하락 깃발형(Bear Flag)",
}

PATTERN_STATE_MAP = {
    "FORMING": "형성 중(FORMING)",
    "BREAKOUT_UP": "상향 돌파(BREAKOUT_UP)",
    "BREAKOUT_DOWN": "하향 이탈(BREAKOUT_DOWN)",
}

LEGEND_NAME_MAP = {
    "Price": "가격(Price)",
    "20MA": "20일선(20MA)",
    "50MA": "50일선(50MA)",
    "200MA": "200일선(200MA)",
    "Bollinger Band": "볼린저 밴드(Bollinger Band)",
    "Hull MA": "헐 이동평균(Hull MA)",
    "SuperTrend": "슈퍼트렌드(SuperTrend)",
    "UTBot Stop": "UTBot 기준선(UTBot Stop)",
    "UTBot Signal": "UTBot 신호(UTBot Signal)",
    "Hull Turn": "헐 전환 신호(Hull Turn)",
    "VuManChu Signal": "VuManChu 신호(VuManChu Signal)",
    "Trend Overlay": "추세선 오버레이(Trend Overlay)",
    "Pattern Overlay": "패턴 오버레이(Pattern Overlay)",
    "Volume Profile": "거래량 프로파일(Volume Profile)",
    "POC": "핵심 가격대(POC)",
    "VAH": "가치영역 상단(VAH)",
    "VAL": "가치영역 하단(VAL)",
    "Strong Buy": "강한 매수 신호(Strong Buy)",
    "Strong Sell": "강한 매도 신호(Strong Sell)",
    "Vol": "거래량(Vol)",
    "WT1": "웨이브트렌드(WT1)",
    "MACD": "MACD",
    "MFI": "자금 흐름(MFI)",
    "SlowK": "스토캐스틱 SlowK",
    "SqMom": "스퀴즈 모멘텀(SqMom)",
    "Ensemble": "종합 점수(Ensemble)",
}

SUBPLOT_TITLE_MAP = {
    "Vol": "거래량(Vol)",
    "WaveTrend": "웨이브트렌드(WaveTrend)",
    "MACD": "MACD",
    "Money Flow": "자금 흐름(Money Flow)",
    "Stoch Slow": "스토캐스틱 슬로우(Stoch Slow)",
    "Squeeze Mom": "스퀴즈 모멘텀(Squeeze Momentum)",
    "5-Committee Ensemble": "5위원회 종합 점수(5-Committee Ensemble)",
}

COMMITTEE_NAME_MAP = {
    "Trend": "추세",
    "Momentum": "모멘텀",
    "Money": "자금 흐름",
    "Structure": "구조",
    "Leading": "선행",
}

JUDGMENT_LABEL_MAP = {
    "STRONG_BUY": "강한 매수(Strong Buy)",
    "BUY": "매수 우위(Buy)",
    "WATCH_BUY": "매수 관찰(Watch Buy)",
    "WATCH_SELL": "매도 관찰(Watch Sell)",
    "SELL": "매도 우위(Sell)",
    "STRONG_SELL": "강한 매도(Strong Sell)",
    "MIXED": "혼조(Mixed)",
    "NEUTRAL": "중립(Neutral)",
}

ACTION_LABEL_MAP = {
    "STRONG BUY": "강한 매수(Strong Buy)",
    "BUY": "매수 우위(Buy)",
    "WATCH BUY": "매수 관찰(Watch Buy)",
    "WATCH SELL": "매도 관찰(Watch Sell)",
    "SELL": "매도 우위(Sell)",
    "STRONG SELL": "강한 매도(Strong Sell)",
    "MIXED": "혼조(Mixed)",
    "NEUTRAL": "중립(Neutral)",
}

COMBO_LABEL_MAP = {
    "CS_Ultimate_Buy": "종합 최우선 매수(Ultimate Buy)",
    "CS_Triple_Oversold_Reversal": "과매도 3중 반전(Triple Oversold Reversal)",
    "CS_Breakout_Momentum_Buy": "돌파 모멘텀 매수(Breakout Momentum Buy)",
    "CS_Institutional_Accumulation": "기관 매집 흐름(Institutional Accumulation)",
    "CS_Divergence_Confluence_Buy": "상승 다이버전스 합류(Divergence Confluence Buy)",
    "CS_Capitulation_Bottom": "투매 바닥 반전(Capitulation Bottom)",
    "CS_Triple_Confirm_Buy": "3중 확인 매수(Triple Confirm Buy)",
    "CS_VuManChu_Squeeze_Buy": "VuManChu 스퀴즈 매수(VuManChu Squeeze Buy)",
    "CS_Ultimate_Sell": "종합 최우선 매도(Ultimate Sell)",
    "CS_Triple_Overbought_Exhaustion": "과매수 3중 소진(Triple Overbought Exhaustion)",
    "CS_Breakdown_Momentum_Sell": "이탈 모멘텀 매도(Breakdown Momentum Sell)",
    "CS_Parabolic_Exhaustion_Sell": "포물선 급등 소진(Parabolic Exhaustion Sell)",
    "CS_Divergence_Confluence_Sell": "하락 다이버전스 합류(Divergence Confluence Sell)",
    "CS_Blow_Off_Top": "급등 과열 천장(Blow-Off Top)",
    "CS_Triple_Confirm_Sell": "3중 확인 매도(Triple Confirm Sell)",
    "CS_VuManChu_Squeeze_Sell": "VuManChu 스퀴즈 매도(VuManChu Squeeze Sell)",
    "CS_Trend_Pullback_Buy": "추세 눌림목 매수(Trend Pullback Buy)",
    "CS_Squeeze_Breakout_Buy": "스퀴즈 상향 돌파(Squeeze Breakout Buy)",
    "CS_MA_Confluence_Buy": "이동평균 합류 매수(MA Confluence Buy)",
    "CS_Cooper_Setup_Buy": "쿠퍼 셋업 매수(Cooper Setup Buy)",
    "CS_Volume_Climax_Rev_Buy": "거래량 급증 반전(Volume Climax Reversal Buy)",
    "CS_Ichimoku_Breakout_Buy": "일목 돌파 매수(Ichimoku Breakout Buy)",
    "CS_Trend_Rejection_Sell": "추세 저항 반락(Trend Rejection Sell)",
    "CS_Squeeze_Breakdown_Sell": "스퀴즈 하향 이탈(Squeeze Breakdown Sell)",
    "CS_MA_Breakdown_Sell": "이동평균 이탈 매도(MA Breakdown Sell)",
    "CS_Cooper_Setup_Sell": "쿠퍼 셋업 매도(Cooper Setup Sell)",
    "CS_Gap_Failure_Sell": "갭 상승 실패(Gap Failure Sell)",
    "CS_Bottom_Fishing_Buy": "바닥권 저가 매수(Bottom Fishing Buy)",
    "CS_Top_Fishing_Sell": "천장권 경계 매도(Top Fishing Sell)",
    "CS_Oversold_Bounce_Buy": "과매도 반등(Oversold Bounce Buy)",
    "CS_Momentum_Accel_Buy": "모멘텀 가속 매수(Momentum Acceleration Buy)",
    "CS_Structure_Support_Buy": "구조 지지 매수(Structure Support Buy)",
    "CS_Overbought_Fade_Sell": "과매수 둔화 매도(Overbought Fade Sell)",
    "CS_Volatility_Explosion": "변동성 폭발 준비(Volatility Explosion)",
}

COMBO_DESC_MAP = {
    "CS_Ultimate_Buy": "여러 핵심 매수 신호가 한 번에 겹친 강한 매수 조합입니다.",
    "CS_Ultimate_Sell": "여러 핵심 매도 신호가 한 번에 겹친 강한 매도 조합입니다.",
    "CS_Triple_Confirm_Buy": "UTBot, Hull, WaveTrend 계열이 함께 매수 쪽으로 맞물린 상태입니다.",
    "CS_Triple_Confirm_Sell": "UTBot, Hull, WaveTrend 계열이 함께 매도 쪽으로 맞물린 상태입니다.",
    "CS_Trend_Pullback_Buy": "상승 추세 안에서 눌림목이 나온 뒤 다시 매수 우위가 붙는 구간입니다.",
    "CS_Trend_Rejection_Sell": "하락 추세 안에서 반등이 저항을 맞고 다시 밀리는 구간입니다.",
}

SIGNAL_LABEL_MAP = {
    "UTBot_Buy": "UTBot 매수 전환(UTBot Buy)",
    "UTBot_Sell": "UTBot 매도 전환(UTBot Sell)",
    "Hull_Turn_Bull": "헐 상승 전환(Hull Turn Bull)",
    "Hull_Turn_Bear": "헐 하락 전환(Hull Turn Bear)",
    "VuManChu_Bull": "VuManChu 상승 신호(VuManChu Bull)",
    "VuManChu_Bear": "VuManChu 하락 신호(VuManChu Bear)",
    "Gold_Dot": "골드 닷(Gold Dot)",
    "Green_Dot_T1": "초록 닷 T1(Green Dot T1)",
    "Green_Dot_T2": "초록 닷 T2(Green Dot T2)",
    "Blood_Diamond": "블러드 다이아몬드(Blood Diamond)",
    "Red_Dot_T1": "빨간 닷 T1(Red Dot T1)",
    "Red_Dot_T2": "빨간 닷 T2(Red Dot T2)",
}

SIGNAL_DESC_MAP = {
    "UTBot_Buy": "UTBot 기준선이 매수 방향으로 전환됐다는 뜻입니다.",
    "UTBot_Sell": "UTBot 기준선이 매도 방향으로 전환됐다는 뜻입니다.",
    "Hull_Turn_Bull": "헐 이동평균이 다시 위로 꺾이며 추세가 살아나는 신호입니다.",
    "Hull_Turn_Bear": "헐 이동평균이 아래로 꺾이며 추세가 약해지는 신호입니다.",
    "VuManChu_Bull": "여러 반전 조건이 겹친 상승 신호입니다.",
    "VuManChu_Bear": "여러 반전 조건이 겹친 하락 신호입니다.",
    "Gold_Dot": "강한 바닥 반전 가능성을 높게 보는 핵심 매수 신호입니다.",
    "Blood_Diamond": "강한 천장 경계 가능성을 높게 보는 핵심 매도 신호입니다.",
}

TOKEN_MAP = {
    "Buy": "매수",
    "Sell": "매도",
    "Bull": "상승",
    "Bear": "하락",
    "Cross": "교차",
    "Breakout": "돌파",
    "Breakdown": "이탈",
    "Support": "지지",
    "Resistance": "저항",
    "Divergence": "다이버전스",
    "Squeeze": "스퀴즈",
    "Momentum": "모멘텀",
    "Volume": "거래량",
    "Trend": "추세",
    "Signal": "신호",
}

CHART_TEXT_REPLACEMENTS = {
    "Boundary": "경계",
    "State": "상태",
    "Period": "기간",
    "Type": "유형",
    "Support Trendline": "지지 추세선",
    "Resistance Trendline": "저항 추세선",
    "Current Price": "현재 값",
    "Projected Price": "예상 가격",
    "Upper Projected Price": "상단 예상 가격",
    "Lower Projected Price": "하단 예상 가격",
    "Channel Projected Price": "채널 예상 가격",
    "Squeeze ON": "스퀴즈 ON",
    "WaveTrend pressure": "과매수/과매도 압력 지표",
    "RSI momentum": "RSI 모멘텀",
    "Volume vs average": "평균 대비 거래량",
    "Trend strength": "추세 강도",
    "UT direction": "UT 방향",
    "Hull direction": "Hull 방향",
    "Final action and confidence": "최종 판단과 신뢰도",
}


def is_broken_text(text: Any) -> bool:
    if text is None:
        return True
    s = str(text).strip()
    if not s:
        return True
    return any(ord(ch) == 65533 for ch in s) or s.count("?") >= 2


def _spaced_key(name: str) -> str:
    return name.replace("_", " ")


def _generic_signal_label(signal_key: str) -> str:
    base = _spaced_key(signal_key)
    for src, dst in TOKEN_MAP.items():
        base = base.replace(src, dst)
    return f"{base}({signal_key})"


def _generic_signal_desc(signal_key: str) -> str:
    key = signal_key.lower()
    if "buy" in key or "bull" in key:
        return "매수 쪽으로 힘이 붙고 있음을 보여주는 신호입니다."
    if "sell" in key or "bear" in key:
        return "매도 쪽으로 힘이 붙고 있음을 보여주는 신호입니다."
    if "div" in key:
        return "가격과 지표의 방향이 어긋나는 다이버전스 신호입니다."
    if "cross" in key:
        return "두 기준선이 교차하며 방향 전환 가능성을 보여주는 신호입니다."
    return "현재 차트 흐름을 보조적으로 설명해 주는 기술 신호입니다."


def localize_context_label(value: Any) -> str:
    if isinstance(value, int):
        return CONTEXT_LABELS_KO.get(value, "기본 흐름(Basic)")
    raw = str(value or "").strip()
    if raw in CONTEXT_SLUG_TO_CODE:
        return CONTEXT_LABELS_KO[CONTEXT_SLUG_TO_CODE[raw]]
    for code, label in CONTEXT_LABELS_KO.items():
        if raw == label or raw in label:
            return label
    return "기본 흐름(Basic)"


def localize_pattern_name(name: Any) -> str:
    raw = str(name or "").strip()
    return PATTERN_NAME_MAP.get(raw, raw or "패턴(Pattern)")


def localize_pattern_state(state: Any) -> str:
    raw = str(state or "").strip()
    return PATTERN_STATE_MAP.get(raw, raw or "상태(State)")


def localize_legend_name(name: Any) -> str:
    raw = str(name or "").strip()
    return LEGEND_NAME_MAP.get(raw, raw)


def localize_subplot_title(title: Any) -> str:
    raw = str(title or "").strip()
    return SUBPLOT_TITLE_MAP.get(raw, raw)


def localize_committee_name(name: Any) -> str:
    raw = str(name or "").strip()
    return COMMITTEE_NAME_MAP.get(raw, raw)


def localize_judgment_label(value: Any) -> str:
    raw = str(value or "").strip().upper()
    return JUDGMENT_LABEL_MAP.get(raw, str(value or "중립(Neutral)"))


def localize_action_label(value: Any) -> str:
    raw = str(value or "").strip().upper()
    return ACTION_LABEL_MAP.get(raw, str(value or "중립(Neutral)"))


def localize_combo(key: str, kor: Any = None, desc: Any = None) -> tuple[str, str]:
    label = COMBO_LABEL_MAP.get(key)
    if not label:
        raw = str(kor or "").strip()
        label = raw if raw and not is_broken_text(raw) else _generic_signal_label(key)
    detail = COMBO_DESC_MAP.get(key)
    if not detail:
        raw_desc = str(desc or "").strip()
        detail = raw_desc if raw_desc and not is_broken_text(raw_desc) else "여러 조건이 한 번에 겹친 조합 신호입니다."
    return label, detail


def localize_signal(key: str, kor: Any = None, desc: Any = None) -> tuple[str, str]:
    label = SIGNAL_LABEL_MAP.get(key)
    if not label:
        raw = str(kor or "").strip()
        label = raw if raw and not is_broken_text(raw) else _generic_signal_label(key)
    detail = SIGNAL_DESC_MAP.get(key)
    if not detail:
        raw_desc = str(desc or "").strip()
        detail = raw_desc if raw_desc and not is_broken_text(raw_desc) else _generic_signal_desc(key)
    return label, detail


def localize_regime_label(regime: Any, fallback: Any = None) -> str:
    if isinstance(regime, (int, float)):
        code = int(regime)
        mapping = {
            2: "강한 상승장(Strong Bull)",
            1: "상승장(Bull)",
            0: "중립장(Neutral)",
            -1: "하락장(Bear)",
            -2: "강한 하락장(Strong Bear)",
        }
        return mapping.get(code, "중립장(Neutral)")
    raw = str(fallback or regime or "").strip()
    upper = raw.upper()
    for key, label in (
        ("STRONG BULL", "강한 상승장(Strong Bull)"),
        ("BULL", "상승장(Bull)"),
        ("NEUTRAL", "중립장(Neutral)"),
        ("STRONG BEAR", "강한 하락장(Strong Bear)"),
        ("BEAR", "하락장(Bear)"),
    ):
        if key in upper:
            return label
    return raw or "중립장(Neutral)"


def translate_chart_text(text: Any) -> str:
    raw = str(text or "")
    translated = raw
    for src, dst in CHART_TEXT_REPLACEMENTS.items():
        translated = translated.replace(src, dst)
    translated = translated.replace("->", "→")
    translated = translated.replace("Current projected price", "현재 예상 가격")
    return translated
