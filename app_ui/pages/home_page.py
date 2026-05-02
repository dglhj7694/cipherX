from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Optional, Union

import requests
import streamlit as st

from telegram_pipeline.contracts import TelegramCandidate, TelegramDigest, TelegramSection
from telegram_pipeline.formatters import QBS_DISPLAY_NUMBERS, build_main_message
from telegram_pipeline.selectors import BOARD_MANDATORY_SECTION_KEYS


DIGEST_CACHE_TTL_SEC = 900
DEFAULT_DIGEST_REPO = "dglhj7694/cipherX"
DEFAULT_DIGEST_BRANCH = "telegram-digest"
DEFAULT_DIGEST_PATH = "post_close/latest.json"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _cache_path(cache_path: Optional[Union[str, Path]] = None) -> Path:
    if cache_path is not None:
        return Path(cache_path)
    return _repo_root() / "artifacts" / "app_cache" / "telegram_digest_latest.json"


def _read_secret(name: str) -> str:
    try:
        return str(st.secrets.get(name, "") or "").strip()
    except Exception:
        return ""


def resolve_github_digest_config() -> dict[str, str]:
    repo = (
        _read_secret("GITHUB_DIGEST_REPO")
        or str(os.getenv("GITHUB_DIGEST_REPO", "")).strip()
        or str(os.getenv("GITHUB_REPOSITORY", "")).strip()
        or DEFAULT_DIGEST_REPO
    )
    branch = _read_secret("GITHUB_DIGEST_BRANCH") or str(os.getenv("GITHUB_DIGEST_BRANCH", DEFAULT_DIGEST_BRANCH)).strip()
    path = _read_secret("GITHUB_DIGEST_PATH") or str(os.getenv("GITHUB_DIGEST_PATH", DEFAULT_DIGEST_PATH)).strip()
    token = _read_secret("GITHUB_DIGEST_TOKEN") or str(os.getenv("GITHUB_DIGEST_TOKEN", "")).strip()
    return {
        "repo": repo,
        "branch": branch or DEFAULT_DIGEST_BRANCH,
        "path": path or DEFAULT_DIGEST_PATH,
        "token": token,
    }


def _raw_digest_url(repo: str, branch: str, path: str) -> str:
    return f"https://raw.githubusercontent.com/{repo}/{branch}/{path.lstrip('/')}"


def _contents_api_url(repo: str, path: str) -> str:
    return f"https://api.github.com/repos/{repo}/contents/{path.lstrip('/')}"


def fetch_digest_from_github(
    *,
    repo: str,
    branch: str,
    path: str = DEFAULT_DIGEST_PATH,
    token: str = "",
    timeout_sec: int = 12,
    session: Any = requests,
) -> dict[str, Any]:
    if not repo:
        raise RuntimeError("GITHUB_DIGEST_REPO is not configured")

    if token:
        response = session.get(
            _contents_api_url(repo, path),
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "cipherX-home-digest-loader",
            },
            params={"ref": branch},
            timeout=timeout_sec,
        )
        response.raise_for_status()
        payload = response.json()
        encoded = str(payload.get("content") or "")
        if not encoded:
            raise RuntimeError("GitHub digest content is empty")
        decoded = base64.b64decode(encoded).decode("utf-8")
        return dict(json.loads(decoded))

    response = session.get(_raw_digest_url(repo, branch, path), timeout=timeout_sec)
    response.raise_for_status()
    return dict(response.json())


@st.cache_data(ttl=DIGEST_CACHE_TTL_SEC, show_spinner=False)
def _fetch_digest_cached(repo: str, branch: str, path: str, token: str) -> dict[str, Any]:
    return fetch_digest_from_github(repo=repo, branch=branch, path=path, token=token)


def write_digest_cache(payload: dict[str, Any], *, cache_path: Optional[Union[str, Path]] = None) -> Path:
    target = _cache_path(cache_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def read_digest_cache(*, cache_path: Optional[Union[str, Path]] = None) -> Optional[dict[str, Any]]:
    target = _cache_path(cache_path)
    if not target.exists():
        return None
    try:
        return dict(json.loads(target.read_text(encoding="utf-8")))
    except Exception:
        return None


def load_latest_telegram_digest(*, cache_path: Optional[Union[str, Path]] = None) -> dict[str, Any]:
    config = resolve_github_digest_config()
    repo = str(config.get("repo") or "").strip()
    if not repo:
        cached = read_digest_cache(cache_path=cache_path)
        return {
            "payload": cached,
            "source": "cache" if cached else "missing",
            "error": "GITHUB_DIGEST_REPO is not configured",
            "config": config,
        }

    try:
        payload = _fetch_digest_cached(
            repo,
            str(config.get("branch") or DEFAULT_DIGEST_BRANCH),
            str(config.get("path") or DEFAULT_DIGEST_PATH),
            str(config.get("token") or ""),
        )
        write_digest_cache(payload, cache_path=cache_path)
        return {"payload": payload, "source": "remote", "error": "", "config": config}
    except Exception as exc:
        cached = read_digest_cache(cache_path=cache_path)
        return {
            "payload": cached,
            "source": "cache" if cached else "error",
            "error": str(exc),
            "config": config,
        }


def extract_section_candidates(payload: Optional[Mapping[str, Any]], section_key: str, *, limit: Optional[int] = None) -> list[dict[str, Any]]:
    sections = list(dict(payload or {}).get("sections") or [])
    for section in sections:
        if str(dict(section or {}).get("key") or "") != str(section_key):
            continue
        items = [dict(item or {}) for item in list(dict(section or {}).get("items") or dict(section or {}).get("detail_items") or [])]
        if limit is None:
            return items
        return items[: max(0, int(limit or 0))]
    return []


def _optional_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number else None


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _text_list(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    return [str(item) for item in value if str(item or "").strip()]


def _candidate_from_payload(item: Mapping[str, Any], *, section_key: str, fallback_rank: int) -> TelegramCandidate:
    payload = dict(item or {})
    return TelegramCandidate(
        ticker=str(payload.get("ticker") or "").strip().upper(),
        price=_optional_float(payload.get("price")),
        chg_value=_optional_float(payload.get("chg_value")),
        chg_pct=_optional_float(payload.get("chg_pct")),
        volume_ratio_20=_optional_float(payload.get("volume_ratio_20")),
        section_key=str(payload.get("section_key") or section_key),
        rank=_safe_int(payload.get("rank"), fallback_rank),
        label=str(payload.get("label") or ""),
        reason=str(payload.get("reason") or ""),
        source_flags=dict(payload.get("source_flags") or {}),
        qbs_score=_optional_float(payload.get("qbs_score")),
        bucket=str(payload.get("bucket") or ""),
        tags=_text_list(payload.get("tags")),
        risk_flags=_text_list(payload.get("risk_flags")),
    )


def telegram_digest_from_payload(payload: Optional[Mapping[str, Any]]) -> TelegramDigest:
    raw = dict(payload or {})
    sections: list[TelegramSection] = []
    for section_payload in list(raw.get("sections") or []):
        section_dict = dict(section_payload or {})
        section_key = str(section_dict.get("key") or "")
        raw_items = list(section_dict.get("items") or section_dict.get("detail_items") or [])
        items = [
            _candidate_from_payload(dict(item or {}), section_key=section_key, fallback_rank=idx)
            for idx, item in enumerate(raw_items, start=1)
        ]
        sections.append(
            TelegramSection(
                key=section_key,
                title=str(section_dict.get("title") or section_key),
                items=items,
                item_count=_safe_int(section_dict.get("item_count"), len(items)),
                quality_floor=str(section_dict.get("quality_floor") or ""),
                ranked=bool(section_dict.get("ranked")),
            )
        )

    section_order = [str(item) for item in list(raw.get("section_order") or []) if str(item or "").strip()]
    if not section_order:
        section_order = [section.key for section in sections if section.key]

    return TelegramDigest(
        version=str(raw.get("version") or ""),
        scan_mode=str(raw.get("scan_mode") or ""),
        run_stamp=str(raw.get("run_stamp") or ""),
        market_date=str(raw.get("market_date") or ""),
        generated_at=str(raw.get("generated_at") or ""),
        section_order=section_order,
        sections=sections,
        briefing_refs=dict(raw.get("briefing_refs") or {}),
        scan_label=str(raw.get("scan_label") or ""),
        universe_count=_safe_int(raw.get("universe_count")),
        result_count=_safe_int(raw.get("result_count")),
        skip_count=_safe_int(raw.get("skip_count")),
    )


def build_telegram_digest_message(payload: Optional[Mapping[str, Any]]) -> str:
    return build_main_message(telegram_digest_from_payload(payload))


def _visible_telegram_sections(digest: TelegramDigest) -> list[TelegramSection]:
    mandatory = set(BOARD_MANDATORY_SECTION_KEYS)
    visible: list[TelegramSection] = []
    for section in digest.sections:
        if section.key in QBS_DISPLAY_NUMBERS:
            visible.append(section)
            continue
        if section.key in mandatory or section.item_count > 0:
            visible.append(section)
    return visible


def _collect_recent_tickers(items: Iterable[str]) -> list[str]:
    ordered: list[str] = []
    for item in items:
        ticker = str(item or "").strip().upper()
        if not ticker or ticker in ordered:
            continue
        ordered.append(ticker)
    return ordered


def _render_ticker_button_row(tickers: list[str], *, key_prefix: str, on_select_ticker: Callable[[str], None], columns: int = 5) -> None:
    if not tickers:
        return
    for start in range(0, len(tickers), columns):
        row_items = tickers[start:start + columns]
        row_columns = st.columns(columns)
        for idx, column in enumerate(row_columns):
            with column:
                if idx >= len(row_items):
                    st.empty()
                    continue
                ticker = row_items[idx]
                if st.button(ticker, key=f"{key_prefix}_{start}_{idx}", use_container_width=True):
                    on_select_ticker(ticker)


def _render_telegram_message_board(
    payload: Mapping[str, Any],
    *,
    source: str,
    digest_result: Mapping[str, Any],
    on_select_ticker: Callable[[str], None],
) -> None:
    digest = telegram_digest_from_payload(payload)
    message = build_main_message(digest)
    blocks = [block.strip() for block in message.split("\n\n") if block.strip()]
    visible_sections = _visible_telegram_sections(digest)

    if blocks:
        st.code(blocks[0], language="text")
    if digest_result.get("error") and source == "cache":
        st.caption(f"원격 갱신 실패로 마지막 성공 캐시를 표시 중입니다: {digest_result['error']}")

    for idx, section in enumerate(visible_sections):
        block = blocks[idx + 1] if idx + 1 < len(blocks) else f"## {section.title}"
        ticker_list = [item.ticker for item in section.items if item.ticker]
        expander_label = section.title or section.key or f"Section {idx + 1}"
        with st.expander(expander_label, expanded=idx < 3):
            st.code(block, language="text")
            if ticker_list:
                _render_ticker_button_row(
                    ticker_list,
                    key_prefix=f"home_telegram_{section.key or idx}",
                    on_select_ticker=on_select_ticker,
                    columns=5,
                )
            else:
                st.caption("해당 티커가 없습니다.")


def render_home_page(
    *,
    render_brand_board: Callable[..., None],
    main_board_payload: Mapping[str, Any],
    render_section_heading: Callable[..., None],
    render_empty_state: Callable[..., None],
    on_select_ticker: Callable[[str], None],
    recent_tickers: Iterable[str],
    chat_input_placeholder: str,
    parse_ticker_input: Callable[[str], list[str]],
) -> None:
    render_brand_board(main_board_payload)
    digest_result = load_latest_telegram_digest()
    payload = dict(digest_result.get("payload") or {})
    source = str(digest_result.get("source") or "missing")
    source_badge = "원격 동기화" if source == "remote" else "캐시 복구" if source == "cache" else "연결 필요"

    render_section_heading(
        "텔레그램 종목판",
        "실제 발송되는 텔레그램 메시지 순서 그대로 후보와 전환/주의 티커를 확인하고 개별 분석으로 이어갑니다.",
        badges=[
            ("홈", "accent"),
            (source_badge, "warning" if source == "cache" else "muted" if source == "missing" else "accent"),
            ("Digest TTL 900s", "muted"),
        ],
        eyebrow="Telegram Digest",
        tight=True,
    )

    if not payload:
        render_empty_state(
            "종목판을 아직 불러오지 못했습니다.",
            str(digest_result.get("error") or "원격 digest가 아직 발행되지 않았습니다."),
            badges=[
                ("원격 digest", "warning"),
                ("캐시 없음", "muted"),
            ],
        )
    else:
        _render_telegram_message_board(
            payload,
            source=source,
            digest_result=digest_result,
            on_select_ticker=on_select_ticker,
        )
    recent = _collect_recent_tickers(recent_tickers)
    render_section_heading(
        "최근 본 종목",
        "최근 분석했던 티커를 다시 열 수 있습니다.",
        badges=[(f"{len(recent)}개", "muted")],
        eyebrow="Recent",
        tight=True,
    )
    if recent:
        _render_ticker_button_row(recent[:10], key_prefix="home_recent", on_select_ticker=on_select_ticker)
    else:
        st.caption("아직 최근 분석 이력이 없습니다.")

    if ti := st.chat_input(chat_input_placeholder):
        parsed = parse_ticker_input(ti)
        if parsed:
            on_select_ticker(parsed[0])
