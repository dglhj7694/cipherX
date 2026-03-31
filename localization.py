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


SIGNAL_MEANING_MAP = {
    "Down_3_Days": "3거래일 연속 약세가 이어져 단기 매도 압력이 누적됐다는 뜻입니다.",
    "Down_4_Days": "4거래일 연속 하락이 이어져 단기 추세가 눈에 띄게 약해졌다는 뜻입니다.",
    "Down_5_Days": "5거래일 연속 하락이 이어져 매도 우위가 강하게 누적됐다는 뜻입니다.",
    "Up_3_Days": "3거래일 연속 상승이 이어져 단기 매수 우위가 유지되고 있다는 뜻입니다.",
    "Up_4_Days": "4거래일 연속 상승이 이어져 단기 추세가 강하게 이어지고 있다는 뜻입니다.",
    "Up_5_Days": "5거래일 연속 상승이 이어져 과열 여부까지 함께 점검해야 하는 구간이라는 뜻입니다.",
    "Stoch_Oversold": "스토캐스틱이 과매도권에 들어와 단기 반등 가능성을 열어두는 신호입니다.",
    "Stoch_Reached_OS": "스토캐스틱이 과매도권에 근접해 단기 반등 시도를 볼 수 있는 구간이라는 뜻입니다.",
    "Stoch_Overbought": "스토캐스틱이 과매수권이라 단기 과열 부담을 함께 봐야 한다는 뜻입니다.",
    "Stoch_Reached_OB": "스토캐스틱이 과매수권에 근접해 단기 숨고르기 가능성을 살펴야 한다는 뜻입니다.",
    "MACD_Cross_Buy": "MACD가 시그널선을 상향 돌파해 모멘텀이 개선될 수 있다는 뜻입니다.",
    "MACD_Cross_Sell": "MACD가 시그널선을 하향 이탈해 단기 모멘텀이 약해졌다는 뜻입니다.",
    "MACD_Zero_Cross_Buy": "MACD가 기준선 위로 올라와 중기 흐름이 강세 쪽으로 기울 수 있다는 뜻입니다.",
    "MACD_Zero_Cross_Sell": "MACD가 기준선 아래로 내려가며 중기 모멘텀이 약해졌다는 뜻입니다.",
    "MF_Cross_Bull": "자금 흐름 지표가 매수 쪽으로 기울어 수급 개선 가능성을 보여주는 신호입니다.",
    "MF_Cross_Bear": "자금 흐름 지표가 매도 쪽으로 기울어 수급이 약해졌다는 뜻입니다.",
    "DMI_Cross_Bull": "방향성 지표에서 상승 쪽 힘이 하락 쪽 힘을 앞서기 시작했다는 뜻입니다.",
    "DMI_Cross_Bear": "방향성 지표에서 하락 쪽 힘이 상승 쪽 힘을 앞서기 시작했다는 뜻입니다.",
    "ADX_New_Uptrend": "추세 강도와 방향이 함께 개선돼 새로운 상승 추세 가능성을 보여주는 신호입니다.",
    "ADX_New_Downtrend": "추세 강도와 방향이 함께 약세 쪽으로 기울어 하락 추세 가능성을 보여주는 신호입니다.",
    "BB_Lower_Walk": "주가가 볼린저 하단을 따라 내려가며 약세 압력이 이어지고 있다는 뜻입니다.",
    "BB_Upper_Walk": "주가가 볼린저 상단을 따라 올라가며 강한 상승 압력이 이어지고 있다는 뜻입니다.",
    "BB_Lower_Break": "볼린저 하단을 이탈해 단기 변동성 확대와 약세 압력을 경계해야 한다는 뜻입니다.",
    "BB_Upper_Break": "볼린저 상단을 돌파해 단기 추세 가속 가능성을 보여주는 신호입니다.",
    "BB_Lower_Bounce": "볼린저 하단에서 반등이 나와 단기 지지 확인 신호로 볼 수 있다는 뜻입니다.",
    "Fell_Below_20MA": "주가가 20일선을 밑돌아 단기 추세가 약해졌다는 뜻입니다.",
    "Fell_Below_50MA": "주가가 50일선을 밑돌아 중기 추세 훼손 가능성이 커졌다는 뜻입니다.",
    "Fell_Below_200MA": "주가가 200일선을 밑돌아 장기 추세가 약세로 기울 수 있다는 뜻입니다.",
    "Cross_Above_20MA": "주가가 20일선을 회복해 단기 추세가 개선될 가능성을 보여주는 신호입니다.",
    "Cross_Above_50MA": "주가가 50일선을 회복해 중기 흐름 개선 가능성을 보여주는 신호입니다.",
    "Cross_Above_200MA": "주가가 200일선을 회복해 장기 추세가 다시 강세 쪽으로 기울 수 있다는 뜻입니다.",
    "MA20_Support": "20일선 부근에서 지지가 확인돼 단기 추세가 버티는지 보는 신호입니다.",
    "MA20_Resistance": "20일선이 저항으로 작용해 단기 반등이 막히는지 보는 신호입니다.",
    "MA50_Support": "50일선 지지가 확인돼 중기 추세가 유지되는지 보는 신호입니다.",
    "MA50_Resistance": "50일선이 저항으로 작용해 중기 약세가 이어지는지 보는 신호입니다.",
    "MA200_Support": "200일선 지지가 확인돼 장기 추세가 살아 있는지 보는 신호입니다.",
    "MA200_Resistance": "200일선이 저항으로 작용해 장기 회복이 막히는지 보는 신호입니다.",
    "Expansion_BD": "변동성 확장과 함께 하방 이탈이 나와 약세 압력이 커졌다는 뜻입니다.",
    "Expansion_BO": "변동성 확장과 함께 상방 돌파가 나와 추세 가속 가능성을 보여주는 신호입니다.",
    "Expansion_Pivot_Sell": "확장 국면에서 매도 쪽 피벗이 형성돼 단기 하락 압력을 경계해야 한다는 뜻입니다.",
    "Expansion_Pivot_Buy": "확장 국면에서 매수 쪽 피벗이 형성돼 단기 반등이나 추세 재개를 볼 수 있다는 뜻입니다.",
    "Gap_Up_Closed": "갭 상승분을 지키지 못해 추격 매수가 약해졌다는 뜻입니다.",
    "Gap_Down_Closed": "갭 하락분을 빠르게 메워 단기 회복 탄력이 붙을 수 있다는 뜻입니다.",
    "Pocket_Pivot": "거래량을 동반한 선도성 매수 신호로 해석할 수 있습니다.",
    "Shooting_Star": "윗꼬리 매물이 나오며 단기 저항 가능성을 보여주는 캔들 신호입니다.",
    "New_52W_Closing_High": "장기 추세가 여전히 강하다는 뜻이지만, 과열 여부도 함께 확인해야 합니다.",
    "Three_Weeks_Tight": "가격이 좁은 범위에 응축돼 있어 추세 재가속 준비 구간으로 볼 수 있다는 뜻입니다.",
    "Volume_Surge": "거래량이 평소보다 크게 늘어 해당 방향 움직임의 신뢰도를 높여주는 신호입니다.",
}


SIGNAL_MEANING_MAP.update({
    "Fib_382_Support": "최근 상승 파동의 38.2% 되돌림 구간에서 지지가 확인돼 얕은 조정 뒤 재상승 가능성을 보여주는 신호입니다.",
    "Fib_50_Support": "최근 상승 파동의 절반 되돌림 구간에서 지지가 확인돼 눌림목 매수 구간으로 해석할 수 있는 신호입니다.",
    "Fib_618_Support": "61.8% 되돌림 구간을 지켜 황금비 지지선에서 추세가 살아 있는지 보는 신호입니다.",
    "Fib_382_Resistance": "38.2% 되돌림 구간에서 저항이 확인돼 반등이 아직 저항에 막히는지 보는 신호입니다.",
    "Fib_50_Resistance": "절반 되돌림 구간에서 저항이 확인돼 반등이 중간 되돌림 수준에서 꺾이는지 보는 신호입니다.",
    "Fib_618_Resistance": "61.8% 되돌림 구간에서 저항이 확인돼 약세 추세가 쉽게 끝나지 않을 수 있음을 보여주는 신호입니다.",
    "Fib_618_Breakdown": "61.8% 되돌림이 무너지며 단순 조정보다 추세 훼손 가능성이 커졌음을 보여주는 신호입니다.",
    "Fib_618_Reclaim": "61.8% 되돌림을 다시 회복해 하락 압력 완화와 반등 시도 강화를 보여주는 신호입니다.",
    "Fib_Confluence_Buy": "피보나치 지지와 이동평균선·볼륨 프로파일 지지가 겹쳐 신뢰도가 높아진 매수 구간입니다.",
    "Fib_Confluence_Sell": "피보나치 저항과 이동평균선·볼륨 프로파일 저항이 겹쳐 신뢰도가 높아진 매도 구간입니다.",
})

COMBO_MEANING_MAP = {
    "CS_Breakout_Confirm_Buy": "돌파 뒤 눌림을 버티며 상방 추세가 확인되는 조합 신호입니다.",
    "CS_Breakout_Confirm_Sell": "하방 이탈 뒤 반등 실패가 겹쳐 약세 추세가 확인되는 조합 신호입니다.",
    "CS_Trend_Continuation_Buy": "상승 추세 속 눌림 이후 재출발 가능성을 보여주는 조합 신호입니다.",
    "CS_Trend_Continuation_Sell": "하락 추세 속 반등 이후 재차 약세가 이어질 가능성을 보여주는 조합 신호입니다.",
    "CS_Squeeze_Breakout_Buy": "압축 구간 이후 상방 돌파가 확인돼 추세 확장 가능성을 보여주는 조합 신호입니다.",
    "CS_Squeeze_Breakdown_Sell": "압축 구간 이후 하방 이탈이 확인돼 약세 확장 가능성을 보여주는 조합 신호입니다.",
}


def _generic_signal_meaning(signal_key: str, is_combo: bool = False) -> str:
    key = str(signal_key or "").lower()
    if "buy" in key or "bull" in key:
        return "매수 쪽 힘이 붙을 수 있는 구간으로 해석하는 기술 신호입니다."
    if "sell" in key or "bear" in key:
        return "매도 쪽 압력이 강해질 수 있는 구간으로 해석하는 기술 신호입니다."
    if "support" in key:
        return "지지 여부를 확인하는 기술 신호입니다."
    if "resistance" in key:
        return "저항 여부를 확인하는 기술 신호입니다."
    if "breakout" in key:
        return "저항 돌파 여부를 확인하는 기술 신호입니다."
    if "breakdown" in key:
        return "지지 이탈 여부를 확인하는 기술 신호입니다."
    if "oversold" in key:
        return "과매도 구간 여부를 확인하는 기술 신호입니다."
    if "overbought" in key:
        return "과매수 구간 여부를 확인하는 기술 신호입니다."
    if is_combo:
        return "여러 기술 신호가 한쪽 방향으로 겹친 조합 신호입니다."
    return "단기 방향성을 판단하는 데 참고하는 기술 신호입니다."


def explain_signal_meaning(
    key: str,
    desc: Any = None,
    *,
    is_combo: bool = False,
) -> str:
    mapping = COMBO_MEANING_MAP if is_combo else SIGNAL_MEANING_MAP
    meaning = str(mapping.get(key, "") or "").strip()
    if meaning:
        return meaning
    raw_desc = str(desc or "").strip()
    if raw_desc and not is_broken_text(raw_desc):
        return raw_desc
    return _generic_signal_meaning(key, is_combo=is_combo)


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
