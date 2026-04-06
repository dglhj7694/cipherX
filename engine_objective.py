from __future__ import annotations

from config import COMBINED_SCAN_REGISTRY, SIGNAL_REGISTRY


OBJECTIVE_BUY_LABELS = {"STRONG_BUY", "BUY", "WATCH_BUY"}
OBJECTIVE_SELL_LABELS = {"STRONG_SELL", "SELL", "WATCH_SELL"}
OBJECTIVE_SIGNAL_EXCLUDE = {"System_Turn_Bull", "System_Turn_Bear"}

# Objective layer treats combo scans as confirmation, not primary evidence.
OBJECTIVE_COMBO_BASE = {1: 1.8, 2: 1.2, 3: 0.6}


def objective_event_name(name):
    raw = str(name or "")
    if raw in SIGNAL_REGISTRY:
        return str(SIGNAL_REGISTRY.get(raw, {}).get("kor") or raw.replace("_", " "))
    if raw in COMBINED_SCAN_REGISTRY:
        return str(COMBINED_SCAN_REGISTRY.get(raw, {}).get("kor") or raw.replace("_", " "))
    return raw.replace("_", " ")


def objective_recent_registry_score(i, specs, bool_arrays, lookback, decay):
    score = 0.0
    strong_hits = 0
    hits = []
    for name, base, is_strong in specs:
        arr = bool_arrays.get(name)
        if arr is None:
            continue
        best = 0.0
        best_age = None
        max_age = min(i, lookback - 1)
        for age in range(max_age + 1):
            if arr[i - age]:
                cur = base * (decay**age)
                if cur > best:
                    best = cur
                    best_age = age
        if best > 0:
            score += best
            hits.append((best, name, best_age))
            if is_strong:
                strong_hits += 1
    hits.sort(key=lambda x: x[0], reverse=True)
    return score, strong_hits, hits


def objective_action_label(label):
    return {
        "STRONG_BUY": "강한 매수 / 객관 근거 최상",
        "BUY": "매수 우위 / 객관 추세 지속",
        "WATCH_BUY": "매수 관찰 / 확인 대기",
        "NEUTRAL": "중립 / 추가 정렬 대기",
        "MIXED": "혼조 / 객관 근거 충돌",
        "WATCH_SELL": "매도 관찰 / 리스크 경계",
        "SELL": "매도 우위 / 객관 하락 정렬",
        "STRONG_SELL": "강한 매도 / 객관 하락 정렬 최상",
    }.get(label, "중립 / 추가 정렬 대기")
