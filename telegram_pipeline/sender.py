from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Iterable

import requests


def _telegram_api(token: str, method: str) -> str:
    return f"https://api.telegram.org/bot{token}/{method}"


def _telegram_send_message_payload(chat_id: str, text: str) -> bytes:
    payload = {
        "chat_id": str(chat_id or "").strip(),
        "text": str(text or ""),
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def split_telegram_message_text(text: str, *, chunk_size: int = 3500) -> list[str]:
    raw = str(text or "")
    limit = max(1, int(chunk_size))
    if len(raw) <= limit:
        return [raw]

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for line in raw.splitlines():
        line_len = len(line) + 1
        if line_len > limit:
            if current:
                chunks.append("\n".join(current))
                current = []
                current_len = 0
            start = 0
            while start < len(line):
                end = min(start + limit, len(line))
                chunks.append(line[start:end])
                start = end
            continue
        if current and current_len + line_len > limit:
            chunks.append("\n".join(current))
            current = [line]
            current_len = line_len
        else:
            current.append(line)
            current_len += line_len
    if current:
        chunks.append("\n".join(current))
    return chunks or [raw]


def send_telegram_message(token: str, chat_id: str, text: str, *, chunk_size: int = 3500) -> None:
    chunks = split_telegram_message_text(text, chunk_size=chunk_size)
    for chunk_idx, chunk in enumerate(chunks, start=1):
        if not str(chunk or "").strip():
            continue
        success = False
        last_error = ""
        for attempt in range(1, 4):
            try:
                response = requests.post(
                    _telegram_api(token, "sendMessage"),
                    data=_telegram_send_message_payload(chat_id, chunk),
                    headers={"Content-Type": "application/json; charset=utf-8"},
                    timeout=30,
                )
                response.raise_for_status()
                payload = response.json()
                if payload.get("ok"):
                    success = True
                    break
                last_error = f"Payload not ok: {payload}"
            except Exception as exc:
                last_error = str(exc)
            if attempt < 3:
                time.sleep(2)
        if not success:
            print(f"[ERROR] Failed to send Telegram message chunk {chunk_idx}/{len(chunks)} after 3 attempts. Last error: {last_error}")


def send_telegram_messages(token: str, chat_id: str, texts: Iterable[str], *, chunk_size: int = 3500) -> None:
    for index, text in enumerate(list(texts or []), start=1):
        if not str(text or "").strip():
            continue
        print(f"[SCAN] Sending Telegram message {index}...")
        send_telegram_message(token, chat_id, str(text), chunk_size=chunk_size)


def send_telegram_document(token: str, chat_id: str, file_path: Path, caption: str = "") -> None:
    success = False
    last_error = ""
    for attempt in range(1, 4):
        try:
            with file_path.open("rb") as handle:
                response = requests.post(
                    _telegram_api(token, "sendDocument"),
                    data={"chat_id": chat_id, "caption": caption},
                    files={"document": (file_path.name, handle, "text/csv")},
                    timeout=60,
                )
            response.raise_for_status()
            payload = response.json()
            if payload.get("ok"):
                success = True
                break
            last_error = f"Payload not ok: {payload}"
        except Exception as exc:
            last_error = str(exc)
        if attempt < 3:
            time.sleep(2)
    if not success:
        print(f"[ERROR] Failed to send Telegram document {file_path.name} after 3 attempts. Last error: {last_error}")
