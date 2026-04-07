from __future__ import annotations

from dataclasses import dataclass

from config import GEMINI_API_KEY, GEMINI_API_KEY_FROM_SECRETS
from services.ai_signal_service import AIKeyState, resolve_ai_key


@dataclass
class AppDependencies:
    gemini_key_state: AIKeyState


def build_dependencies(runtime_key: str | None = None) -> AppDependencies:
    return AppDependencies(
        gemini_key_state=resolve_ai_key(runtime_key, GEMINI_API_KEY, GEMINI_API_KEY_FROM_SECRETS)
    )
