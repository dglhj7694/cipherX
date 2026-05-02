from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Optional, Union

import requests
import streamlit as st


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
        "오늘 최우선 후보와 전환/주의 티커를 바로 열어 개별 분석으로 이어갑니다.",
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
        final_top = extract_section_candidates(payload, "qbs_buy_now", limit=5)
        entry_now = extract_section_candidates(payload, "entry_now", limit=5)
        sell_risk = extract_section_candidates(payload, "sell_risk", limit=5)

        render_section_heading(
            "오늘 최우선 후보 Top 5",
            "텔레그램 종목판의 메인 랭킹입니다. 버튼을 누르면 바로 분석 모드로 전환됩니다.",
            badges=[
                (f"{len(final_top)}개", "accent"),
                (str(payload.get("market_date") or "US close"), "muted"),
            ],
            eyebrow="Primary Board",
            tight=True,
        )
        _render_ticker_button_row([str(item.get("ticker") or "") for item in final_top], key_prefix="home_final", on_select_ticker=on_select_ticker)
        if digest_result.get("error") and source == "cache":
            st.caption(f"원격 갱신 실패로 마지막 성공 캐시를 표시 중입니다: {digest_result['error']}")

        quick_left, quick_right = st.columns(2)
        with quick_left:
            render_section_heading(
                "지금 진입형 바로가기",
                "매수전환, MA20 재탈환, HMA/EMA 진입형 티커를 바로 검증합니다.",
                badges=[(f"{len(entry_now)}개", "accent")],
                eyebrow="Quick Verify",
                tight=True,
            )
            _render_ticker_button_row([str(item.get("ticker") or "") for item in entry_now], key_prefix="home_buy", on_select_ticker=on_select_ticker, columns=2)
        with quick_right:
            render_section_heading(
                "매도전환 / 위험",
                "매도전환이나 강한 위험 신호가 나온 티커를 먼저 확인합니다.",
                badges=[(f"{len(sell_risk)}개", "warning")],
                eyebrow="Risk First",
                tight=True,
            )
            _render_ticker_button_row([str(item.get("ticker") or "") for item in sell_risk], key_prefix="home_sell", on_select_ticker=on_select_ticker, columns=2)

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
