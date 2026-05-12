from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import google.generativeai as genai


@dataclass
class AIKeyState:
    active_key: str
    source: str

    @property
    def available(self) -> bool:
        return bool(str(self.active_key).strip())


def mask_secret(value: str | None) -> str:
    text = str(value or "").strip()
    if not text:
        return "미설정"
    if len(text) <= 8:
        return "*" * len(text)
    return f"{text[:4]}...{text[-4:]}"


def resolve_ai_key(
    runtime_key: str | None,
    configured_key: str | None,
    configured_from_secrets: bool = False,
) -> AIKeyState:
    runtime_key = str(runtime_key or "").strip()
    configured_key = str(configured_key or "").strip()
    active_key = runtime_key or configured_key
    if runtime_key:
        source = "세션 입력"
    elif configured_from_secrets and configured_key:
        source = "secret"
    elif configured_key:
        source = "환경변수"
    else:
        source = "미설정"
    return AIKeyState(active_key=active_key, source=source)


def build_ai_client(api_key: str):
    api_key = str(api_key or "").strip()
    if not api_key:
        raise RuntimeError("Gemini API key missing")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-flash-latest")


def unavailable_ai_result(message: str) -> dict[str, Any]:
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
        "raw_text": "",
    }


def generate_ai_signal_assisted(
    *,
    runtime_key: str | None,
    configured_key: str | None,
    configured_from_secrets: bool,
    prompt: str,
    engine_judgment: str,
    parser: Callable[[str], dict[str, Any]] | Callable[..., dict[str, Any]],
    client_factory: Callable[[str], Any] | None = None,
) -> dict[str, Any]:
    key_state = resolve_ai_key(runtime_key, configured_key, configured_from_secrets)
    if not key_state.available:
        return unavailable_ai_result(
            "Gemini API 키가 없어 AI 보조 판단을 생성하지 못했습니다. Analysis Workspace의 AI Key Setup에서 입력해 주세요."
        )

    try:
        model = (client_factory or build_ai_client)(key_state.active_key)
        response = model.generate_content(prompt)
        raw_text = str(getattr(response, "text", "") or "").strip()
        return parser(raw_text, engine_judgment=engine_judgment)
    except Exception as exc:
        return unavailable_ai_result(f"AI 보조 판단 생성 중 오류가 발생했습니다: {exc}")
