from __future__ import annotations


RUNTIME_COMBO_REGISTRY = {
    "CS_Trend_Continuation_Buy": {
        "name": "Trend Continuation Buy",
        "kor": "추세 지속 매수",
        "dir": "buy",
        "tier": 2,
        "icon": "UP",
        "color": "#34D399",
        "desc": "상승 추세 눌림 이후 재가속",
        "win": "60-72%",
    },
    "CS_Trend_Continuation_Sell": {
        "name": "Trend Continuation Sell",
        "kor": "추세 지속 매도",
        "dir": "sell",
        "tier": 2,
        "icon": "DN",
        "color": "#F87171",
        "desc": "하락 추세 반등 실패 이후 재하락",
        "win": "60-72%",
    },
    "CS_Reversal_Cluster_Buy": {
        "name": "Reversal Cluster Buy",
        "kor": "반전 클러스터 매수",
        "dir": "buy",
        "tier": 1,
        "icon": "REV",
        "color": "#22C55E",
        "desc": "다이버전스와 반전 시그널 동시 발생",
        "win": "68-80%",
    },
    "CS_Reversal_Cluster_Sell": {
        "name": "Reversal Cluster Sell",
        "kor": "반전 클러스터 매도",
        "dir": "sell",
        "tier": 1,
        "icon": "REV",
        "color": "#EF4444",
        "desc": "다이버전스와 반전 시그널 동시 발생",
        "win": "68-80%",
    },
    "CS_Breakout_Confirm_Buy": {
        "name": "Breakout Confirm Buy",
        "kor": "돌파 확인 매수",
        "dir": "buy",
        "tier": 2,
        "icon": "BRK",
        "color": "#60A5FA",
        "desc": "거래량과 ADX가 동반된 상향 돌파",
        "win": "62-74%",
    },
    "CS_Breakout_Confirm_Sell": {
        "name": "Breakout Confirm Sell",
        "kor": "붕괴 확인 매도",
        "dir": "sell",
        "tier": 2,
        "icon": "BRK",
        "color": "#F97316",
        "desc": "거래량과 ADX가 동반된 하향 붕괴",
        "win": "62-74%",
    },
    "CS_Ichimoku_Breakout_Sell": {
        "name": "Ichimoku Breakdown",
        "kor": "이치모쿠 하향 이탈",
        "dir": "sell",
        "tier": 2,
        "icon": "ICHI",
        "color": "#FB7185",
        "desc": "구름 하단 이탈과 bearish TK 정렬",
        "win": "60-70%",
    },
    "CS_Conflict_Warning": {
        "name": "Conflict Warning",
        "kor": "방향 충돌 경고",
        "dir": "neutral",
        "tier": 3,
        "icon": "WARN",
        "color": "#F59E0B",
        "desc": "강한 매수와 매도 조건이 동시에 발생",
        "win": "N/A",
    },
}


def ensure_runtime_combo_registry(registry: dict) -> dict:
    for key, value in RUNTIME_COMBO_REGISTRY.items():
        registry.setdefault(key, value)
    return registry
