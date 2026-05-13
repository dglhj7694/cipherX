from __future__ import annotations

import base64
import html
import json
import os
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Optional, Union

import requests
import streamlit as st

from telegram_pipeline.contracts import TelegramCandidate, TelegramDigest, TelegramSection
from telegram_pipeline.aggressive_next_day_ranker import AGGRESSIVE_NEXT_DAY_SECTION_KEYS
from telegram_pipeline.early_reversal_ranker import EARLY_REVERSAL_KEY
from telegram_pipeline.formatters import (
    BOARD_DISPLAY_NUMBERS,
    EARLY_REVERSAL_DISPLAY_NUMBER,
    FIVE_DAY_TOP_DISPLAY_NUMBER,
    HULL_BUY_TURN_DISPLAY_NUMBER,
    QBS_DISPLAY_NUMBERS,
    STEADY_WINNER_DISPLAY_NUMBER,
    STARTUP9_CONFIRM_DISPLAY_NUMBER,
    TECHNICAL_BUY_DISPLAY_NUMBER,
    build_main_message,
)
from telegram_pipeline.hull_buy_turn_ranker import HULL_BUY_TURN_KEY
from telegram_pipeline.selectors import BOARD_MANDATORY_SECTION_KEYS, BOARD_SECTION_ORDER, STEADY_WINNER_SECTION_KEY
from telegram_pipeline.startup9_confirm_ranker import STARTUP9_CONFIRM_KEY
from telegram_pipeline.technical_buy_signal_ranker import TECHNICAL_BUY_CLUSTER_KEY
from theme import FONT_STACK


DIGEST_CACHE_TTL_SEC = 900
DEFAULT_DIGEST_REPO = "dglhj7694/cipherX"
DEFAULT_DIGEST_BRANCH = "telegram-digest"
DEFAULT_DIGEST_PATH = "post_close/latest.json"

AGGRESSIVE_SECTION_KEY_SET = set(AGGRESSIVE_NEXT_DAY_SECTION_KEYS)
AGGRESSIVE_SECTION_SHORT_LABELS = {
    AGGRESSIVE_NEXT_DAY_SECTION_KEYS[0]: "P1 초기전환",
    AGGRESSIVE_NEXT_DAY_SECTION_KEYS[1]: "P2 강추세",
    AGGRESSIVE_NEXT_DAY_SECTION_KEYS[2]: "P3 눌림",
    AGGRESSIVE_NEXT_DAY_SECTION_KEYS[3]: "P4 위성",
    AGGRESSIVE_NEXT_DAY_SECTION_KEYS[4]: "P5 포켓/거래량",
    AGGRESSIVE_NEXT_DAY_SECTION_KEYS[5]: "P6 압축",
    AGGRESSIVE_NEXT_DAY_SECTION_KEYS[6]: "P7 갭추격",
    AGGRESSIVE_NEXT_DAY_SECTION_KEYS[7]: "P8 신고가",
}
AGGRESSIVE_ENTRY_SECTION_KEYS = {
    AGGRESSIVE_NEXT_DAY_SECTION_KEYS[0],
    AGGRESSIVE_NEXT_DAY_SECTION_KEYS[2],
    AGGRESSIVE_NEXT_DAY_SECTION_KEYS[4],
    AGGRESSIVE_NEXT_DAY_SECTION_KEYS[6],
}
AGGRESSIVE_TREND_SECTION_KEYS = {
    AGGRESSIVE_NEXT_DAY_SECTION_KEYS[1],
    AGGRESSIVE_NEXT_DAY_SECTION_KEYS[5],
    AGGRESSIVE_NEXT_DAY_SECTION_KEYS[7],
}
DECISION_SECTION_KEYS = {
    *QBS_DISPLAY_NUMBERS.keys(),
    STEADY_WINNER_SECTION_KEY,
    EARLY_REVERSAL_KEY,
    HULL_BUY_TURN_KEY,
}
BOARD_TYPE_SECTION_KEYS = set(BOARD_SECTION_ORDER)


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
    if value is None:
        return []
    if isinstance(value, str):
        parts = value.replace("|", "+").split("+")
    elif isinstance(value, (list, tuple, set)):
        parts = list(value)
    else:
        parts = [value]
    return [str(item).strip() for item in parts if str(item or "").strip()]


def _candidate_from_payload(item: Mapping[str, Any], *, section_key: str, fallback_rank: int) -> TelegramCandidate:
    payload = dict(item or {})
    source_flags = dict(payload.get("source_flags") or {})
    chg_5d = _optional_float(payload.get("chg_5d") if payload.get("chg_5d") is not None else source_flags.get("chg_5d"))
    chg_pct = chg_5d if section_key == "five_day_top" and chg_5d is not None else _optional_float(payload.get("chg_pct"))
    rsi = _optional_float(payload.get("rsi") if payload.get("rsi") is not None else source_flags.get("rsi", source_flags.get("RSI")))
    ma20_dist_pct = _optional_float(
        payload.get("ma20_dist_pct")
        if payload.get("ma20_dist_pct") is not None
        else source_flags.get("ma20_dist_pct", source_flags.get("dist_sma20_pct"))
    )
    high_pos_pct = _optional_float(
        payload.get("high_pos_pct")
        if payload.get("high_pos_pct") is not None
        else source_flags.get("high_pos_pct", source_flags.get("drawdown_from_52w_high_pct"))
    )
    return TelegramCandidate(
        ticker=str(payload.get("ticker") or "").strip().upper(),
        price=_optional_float(payload.get("price")),
        chg_value=_optional_float(payload.get("chg_value")),
        chg_pct=chg_pct,
        volume_ratio_20=_optional_float(payload.get("volume_ratio_20")),
        section_key=str(payload.get("section_key") or section_key),
        rank=_safe_int(payload.get("rank"), fallback_rank),
        label=str(payload.get("label") or ""),
        reason=str(payload.get("reason") or ""),
        source_flags=source_flags,
        qbs_score=_optional_float(payload.get("qbs_score")),
        bucket=str(payload.get("bucket") or ""),
        tags=_text_list(payload.get("tags")),
        risk_flags=_text_list(payload.get("risk_flags")),
        chg_5d=chg_5d,
        rsi=rsi,
        ma20_dist_pct=ma20_dist_pct,
        ret_1m_pct=_optional_float(
            payload.get("ret_1m_pct")
            if payload.get("ret_1m_pct") is not None
            else source_flags.get("ret_1m_pct", source_flags.get("ret20_pct"))
        ),
        ret_1y_pct=_optional_float(
            payload.get("ret_1y_pct")
            if payload.get("ret_1y_pct") is not None
            else source_flags.get("ret_1y_pct", source_flags.get("ret252_pct"))
        ),
        high_pos_pct=high_pos_pct,
        status_tags=_text_list(payload.get("status_tags")),
        status=str(payload.get("status") or ""),
        pul_score=_optional_float(payload.get("pul_score")),
        early_reversal_score=_optional_float(payload.get("early_reversal_score")),
        reversal_type=str(payload.get("reversal_type") or source_flags.get("reversal_type") or ""),
        reversal_phase=str(payload.get("reversal_phase") or source_flags.get("reversal_phase") or ""),
        entry_type=str(payload.get("entry_type") or ""),
        technical_buy_score=_optional_float(payload.get("technical_buy_score") if payload.get("technical_buy_score") is not None else source_flags.get("technical_buy_score")),
        technical_buy_signal_count=_safe_int(
            payload.get("technical_buy_signal_count")
            if payload.get("technical_buy_signal_count") is not None
            else source_flags.get("technical_buy_signal_count")
        ),
        technical_buy_hits=_text_list(payload.get("technical_buy_hits") or source_flags.get("technical_buy_hits")),
        technical_buy_bucket=str(payload.get("technical_buy_bucket") or source_flags.get("technical_buy_bucket") or ""),
        technical_buy_reason=str(payload.get("technical_buy_reason") or source_flags.get("technical_buy_reason") or ""),
        technical_buy_risk_flags=_text_list(payload.get("technical_buy_risk_flags") or source_flags.get("technical_buy_risk_flags")),
        startup9_confirm_count=_safe_int(
            payload.get("startup9_confirm_count")
            if payload.get("startup9_confirm_count") is not None
            else source_flags.get("startup9_confirm_count")
        ),
        startup9_confirm_grade=str(payload.get("startup9_confirm_grade") or source_flags.get("startup9_confirm_grade") or ""),
        startup9_confirm_hits=_text_list(payload.get("startup9_confirm_hits") or source_flags.get("startup9_confirm_hits")),
        startup9_confirm_missing=_text_list(payload.get("startup9_confirm_missing") or source_flags.get("startup9_confirm_missing")),
        startup9_confirm_reason=str(payload.get("startup9_confirm_reason") or source_flags.get("startup9_confirm_reason") or ""),
        startup9_risk_flags=_text_list(payload.get("startup9_risk_flags") or source_flags.get("startup9_risk_flags")),
        startup9_score=_optional_float(payload.get("startup9_score") if payload.get("startup9_score") is not None else source_flags.get("startup9_score")),
        startup9_profile=str(payload.get("startup9_profile") or source_flags.get("startup9_profile") or ""),
        startup9_direction_state=str(payload.get("startup9_direction_state") or source_flags.get("startup9_direction_state") or ""),
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
    section_list = list(digest.sections or [])
    if digest.section_order:
        order_index = {str(key): idx for idx, key in enumerate(digest.section_order)}
        section_list.sort(key=lambda section: (order_index.get(str(section.key), len(order_index)), str(section.key)))
    for section in section_list:
        if section.key in QBS_DISPLAY_NUMBERS:
            visible.append(section)
            continue
        if section.key == TECHNICAL_BUY_CLUSTER_KEY:
            visible.append(section)
            continue
        if section.key == STARTUP9_CONFIRM_KEY:
            visible.append(section)
            continue
        if section.key == STEADY_WINNER_SECTION_KEY:
            visible.append(section)
            continue
        if section.key == EARLY_REVERSAL_KEY:
            visible.append(section)
            continue
        if section.key == HULL_BUY_TURN_KEY:
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

def _html_text(value: Any) -> str:
    return html.escape(str(value or "").strip())


def _format_float(value: Any, decimals: int = 2, *, signed: bool = False, suffix: str = "") -> str:
    number = _optional_float(value)
    if number is None:
        return "--"
    body = f"{number:+.{decimals}f}" if signed else f"{number:.{decimals}f}"
    return f"{body}{suffix}"


def _format_qbs(value: Any) -> str:
    number = _optional_float(value)
    if number is None:
        return "QBS --"
    return f"QBS {number:.0f}" if float(number).is_integer() else f"QBS {number:.1f}"


def _format_pul(value: Any) -> str:
    number = _optional_float(value)
    if number is None:
        return "PUL --"
    return f"PUL {number:.0f}" if float(number).is_integer() else f"PUL {number:.1f}"


def _format_ers(value: Any) -> str:
    number = _optional_float(value)
    if number is None:
        return "ERS --"
    return f"ERS {number:.0f}" if float(number).is_integer() else f"ERS {number:.1f}"


def _format_technical_buy(value: Any) -> str:
    number = _optional_float(value)
    if number is None:
        return "TBS --"
    return f"TBS {number:.0f}" if float(number).is_integer() else f"TBS {number:.1f}"


def _format_ratio(value: Any) -> str:
    number = _optional_float(value)
    if number is None:
        return "x--"
    return f"x{number:.2f}"


def _change_tone(value: Any) -> str:
    number = _optional_float(value)
    if number is None:
        return "muted"
    if number > 0:
        return "positive"
    if number < 0:
        return "negative"
    return "muted"


def _volume_tone(value: Any) -> str:
    number = _optional_float(value)
    if number is None:
        return "muted"
    if number >= 2:
        return "warning"
    if number >= 1.2:
        return "positive"
    return "muted"


def _qbs_tone(value: Any) -> str:
    number = _optional_float(value)
    if number is None:
        return "muted"
    if number >= 50:
        return "positive"
    if number >= 40:
        return "warning"
    if number >= 25:
        return "info"
    return "muted"


def _technical_buy_tone(value: Any) -> str:
    number = _optional_float(value)
    if number is None:
        return "muted"
    if number >= 10:
        return "positive"
    if number >= 7:
        return "info"
    if number >= 5:
        return "warning"
    return "muted"


def _section_tone(section_key: str) -> str:
    key = str(section_key or "")
    if key in AGGRESSIVE_SECTION_KEY_SET:
        if key in {AGGRESSIVE_NEXT_DAY_SECTION_KEYS[3], AGGRESSIVE_NEXT_DAY_SECTION_KEYS[6]}:
            return "warning"
        if key in {AGGRESSIVE_NEXT_DAY_SECTION_KEYS[5], AGGRESSIVE_NEXT_DAY_SECTION_KEYS[7]}:
            return "info"
        return "positive"
    if key in {"qbs_chase_watch", "chase_risk"}:
        return "warning"
    if key in {"sell_turn", "sell_risk"}:
        return "negative"
    if key in {"qbs_pullback_wait", "pullback_reentry", "breakout_wait"}:
        return "info"
    if key == TECHNICAL_BUY_CLUSTER_KEY:
        return "positive"
    if key == STARTUP9_CONFIRM_KEY:
        return "positive"
    if key == EARLY_REVERSAL_KEY:
        return "info"
    if key == HULL_BUY_TURN_KEY:
        return "info"
    return "positive"


def _signal_tone(label: str, section_key: str) -> str:
    text = str(label or "").upper()
    if "SELL" in text or "RISK" in text:
        return "negative"
    if "CHASE" in text:
        return "warning"
    if "PULLBACK" in text or "WAIT" in text:
        return "info"
    if str(section_key or "") in AGGRESSIVE_SECTION_KEY_SET:
        return _section_tone(section_key)
    if text:
        return "positive"
    return _section_tone(section_key)


def _badge_html(label: Any, tone: str = "muted") -> str:
    text = _html_text(label)
    if not text:
        return ""
    if tone not in {"accent", "positive", "negative", "warning", "info", "muted"}:
        tone = "muted"
    return f"<span class='cpx-digest-badge' data-tone='{tone}'>{text}</span>"


def _candidate_signal_label(item: TelegramCandidate) -> str:
    return str(item.bucket or item.label or item.section_key or "").strip()


def _candidate_tags_html(item: TelegramCandidate) -> str:
    badges: list[str] = []
    reason = str(item.reason or "").strip()
    if reason:
        parts = [part.strip() for part in reason.replace("/", "+").split("+")]
        short_parts = [part for part in parts if part and len(part) <= 18]
        for part in short_parts[:4]:
            badges.append(_badge_html(part, "accent"))
        if not short_parts:
            badges.append(f"<span class='cpx-digest-reason'>{_html_text(reason)}</span>")

    for tag in list(item.tags or [])[:3]:
        badges.append(_badge_html(tag, "muted"))
    for hit in list(item.technical_buy_hits or [])[:4]:
        badges.append(_badge_html(hit, "accent"))
    for hit in list(item.startup9_confirm_hits or [])[:4]:
        badges.append(_badge_html(hit, "accent"))
    for flag in list(item.risk_flags or [])[:3]:
        badges.append(_badge_html(flag, "negative"))
    for flag in list(item.technical_buy_risk_flags or [])[:3]:
        badges.append(_badge_html(flag, "negative"))
    for flag in list(item.startup9_risk_flags or [])[:3]:
        badges.append(_badge_html(flag, "negative"))
    return "".join(badges) or _badge_html("reason --", "muted")


def _candidate_status_text(item: TelegramCandidate) -> str:
    status = str(item.status or "").strip()
    if status:
        return status
    tags = [str(tag or "").strip() for tag in list(item.status_tags or []) if str(tag or "").strip()]
    return "/".join(tags) if tags else "-"


def _candidate_source_number(item: TelegramCandidate, *keys: str) -> float | None:
    flags = dict(item.source_flags or {})
    for key in keys:
        value = flags.get(key)
        if value is None:
            continue
        number = _optional_float(value)
        if number is not None:
            return number
    return None


def _board_today_pct(item: TelegramCandidate, section_key: str) -> float | None:
    today_pct = _candidate_source_number(item, "today_chg_pct", "chg")
    if today_pct is not None:
        return today_pct
    if section_key == "five_day_top":
        price = _optional_float(item.price)
        change_value = _optional_float(item.chg_value)
        previous_price = (price - change_value) if price is not None and change_value is not None else None
        if previous_price is not None and abs(previous_price) > 1e-10:
            return (change_value / previous_price) * 100.0
        return None
    return item.chg_pct


def _board_five_day_pct(item: TelegramCandidate, section_key: str) -> float | None:
    five_day_pct = item.chg_5d
    if five_day_pct is None:
        five_day_pct = _candidate_source_number(item, "chg_5d")
    if five_day_pct is None and section_key == "five_day_top":
        five_day_pct = item.chg_pct
    return five_day_pct


def _first_number(*values: Any) -> float | None:
    for value in values:
        number = _optional_float(value)
        if number is not None:
            return number
    return None


def _first_text(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text and text not in {"-", "--"}:
            return text
    return "-"


def _board_entry_text(item: TelegramCandidate, section_key: str, fallback_entry: Any = None) -> str:
    explicit = _first_text(item.entry_type, fallback_entry)
    if explicit != "-":
        return explicit
    if str(section_key or "") in AGGRESSIVE_SECTION_KEY_SET:
        return "aggressive_next_day_watch"
    defaults = {
        "qbs_buy_now": "buy_now",
        "qbs_chase_watch": "chase_watch",
        "qbs_pullback_wait": "pullback_wait",
        STARTUP9_CONFIRM_KEY: "startup9_confirm_watch",
        TECHNICAL_BUY_CLUSTER_KEY: "technical_cluster_watch",
        STEADY_WINNER_SECTION_KEY: "watchlist",
        EARLY_REVERSAL_KEY: "reversal_watch",
        HULL_BUY_TURN_KEY: "hull_buy_turn_watch",
        "five_day_top": "momentum_watch",
    }
    return defaults.get(str(section_key or ""), "-")


def _board_section_label(section_key: str) -> str:
    key = str(section_key or "")
    if key in AGGRESSIVE_SECTION_SHORT_LABELS:
        return AGGRESSIVE_SECTION_SHORT_LABELS[key]
    labels = {
        "qbs_buy_now": "BUY_NOW",
        "qbs_chase_watch": "CHASE",
        "qbs_pullback_wait": "PULLBACK",
        STARTUP9_CONFIRM_KEY: "S9",
        TECHNICAL_BUY_CLUSTER_KEY: "TECH BUY",
        STEADY_WINNER_SECTION_KEY: "STEADY",
        EARLY_REVERSAL_KEY: "REVERSAL",
        HULL_BUY_TURN_KEY: "HULL",
        "five_day_top": "5D TOP",
    }
    return labels.get(key, key or "-")


def _board_bucket_label(item: TelegramCandidate, section_key: str) -> str:
    if str(section_key or "") in AGGRESSIVE_SECTION_KEY_SET:
        return _board_section_label(section_key)
    if section_key == "five_day_top":
        return _candidate_status_text(item)
    if section_key == STARTUP9_CONFIRM_KEY:
        return str(item.startup9_profile or item.startup9_confirm_grade or item.bucket or item.label or "-").strip() or "-"
    if section_key == TECHNICAL_BUY_CLUSTER_KEY:
        return str(item.technical_buy_bucket or item.bucket or item.label or "-").strip() or "-"
    if section_key == EARLY_REVERSAL_KEY:
        return str(item.reversal_phase or item.bucket or item.label or "-").strip() or "-"
    if section_key == HULL_BUY_TURN_KEY:
        return "HULL_BUY_TURN"
    return str(item.bucket or item.label or "-").strip() or "-"


def _board_score_text(item: TelegramCandidate, section_key: str) -> str:
    if str(section_key or "") in AGGRESSIVE_SECTION_KEY_SET:
        return "AGG"
    if section_key == STEADY_WINNER_SECTION_KEY:
        return _format_pul(item.pul_score)
    if section_key == EARLY_REVERSAL_KEY:
        return _format_ers(item.early_reversal_score)
    if section_key == HULL_BUY_TURN_KEY:
        return "HULL"
    if section_key == STARTUP9_CONFIRM_KEY:
        return f"S9 {int(item.startup9_confirm_count or 0)}/9"
    if section_key == TECHNICAL_BUY_CLUSTER_KEY:
        return _format_technical_buy(item.technical_buy_score)
    if section_key in QBS_DISPLAY_NUMBERS:
        return _format_qbs(item.qbs_score)
    return "--"


def _split_reason_parts(text: str) -> list[str]:
    normalized = str(text or "").replace("/", "+").replace(",", "+")
    return [part.strip() for part in normalized.split("+") if part.strip()]


def _board_setup_parts(item: TelegramCandidate, *, limit: int = 4) -> list[str]:
    parts: list[str] = []
    for part in _split_reason_parts(str(item.reason or "")):
        if part and part not in parts:
            parts.append(part)
    for tag in list(item.tags or []):
        text = str(tag or "").strip()
        if text and text not in parts:
            parts.append(text)
    for hit in list(item.technical_buy_hits or []):
        text = str(hit or "").strip()
        if text and text not in parts:
            parts.append(text)
    for hit in list(item.startup9_confirm_hits or []):
        text = str(hit or "").strip()
        if text and text not in parts:
            parts.append(text)
    return parts[: max(0, int(limit or 0))]


def _board_risk_parts(text: str, *, limit: int = 4) -> list[str]:
    parts: list[str] = []
    for part in _split_reason_parts(text):
        if part and part not in parts:
            parts.append(part)
    return parts[: max(0, int(limit or 0))]


def _board_risk_text(item: TelegramCandidate, section_key: str) -> str:
    parts: list[str] = []
    parts.extend(str(flag).strip() for flag in list(item.risk_flags or []) if str(flag or "").strip())
    parts.extend(str(flag).strip() for flag in list(item.technical_buy_risk_flags or []) if str(flag or "").strip())
    parts.extend(str(flag).strip() for flag in list(item.startup9_risk_flags or []) if str(flag or "").strip())
    if str(section_key or "") in AGGRESSIVE_SECTION_KEY_SET:
        seen: list[str] = []
        for part in parts:
            if part not in seen:
                seen.append(part)
        return "+".join(seen[:4]) if seen else "-"
    if section_key == "five_day_top":
        parts.extend(_split_reason_parts(_candidate_status_text(item)))
    if not parts:
        parts.extend(str(tag).strip() for tag in list(item.tags or []) if str(tag or "").strip())
    if not parts and item.reason:
        parts.extend(_split_reason_parts(str(item.reason)))
    seen: list[str] = []
    for part in parts:
        if part not in seen:
            seen.append(part)
    return "+".join(seen[:4]) if seen else "-"


def _board_has_warning(row: Mapping[str, Any]) -> bool:
    risk_text = str(row.get("risk") or "").lower()
    if not risk_text or risk_text == "-":
        return False
    warning_tokens = (
        "risk",
        "주의",
        "hot",
        "extension",
        "extended_day",
        "extended_5d",
        "climax",
        "low_volume",
        "low_vol20",
        "high_conflict",
        "sell",
        "gap",
        "gap_chase",
        "thin",
        "overheat",
        "hot_zscore",
        "ma20_extended",
        "satellite_size",
    )
    if any(token in risk_text for token in warning_tokens):
        return True
    return bool(row.get("risk_flags"))


def _collect_digest_metric_lookup(digest: TelegramDigest) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for section in _visible_telegram_sections(digest):
        for item in section.items:
            ticker = str(item.ticker or "").strip().upper()
            if not ticker:
                continue
            metrics = lookup.setdefault(ticker, {})
            metrics["price"] = _first_number(metrics.get("price"), item.price)
            metrics["today_pct"] = _first_number(metrics.get("today_pct"), _board_today_pct(item, section.key))
            metrics["five_day_pct"] = _first_number(metrics.get("five_day_pct"), _board_five_day_pct(item, section.key))
            metrics["one_month_pct"] = _first_number(
                metrics.get("one_month_pct"),
                item.ret_1m_pct,
                _candidate_source_number(item, "ret_1m_pct", "ret20_pct"),
            )
            metrics["one_year_pct"] = _first_number(
                metrics.get("one_year_pct"),
                item.ret_1y_pct,
                _candidate_source_number(item, "ret_1y_pct", "ret252_pct"),
            )
            metrics["high_pos_pct"] = _first_number(
                metrics.get("high_pos_pct"),
                item.high_pos_pct,
                _candidate_source_number(item, "high_pos_pct", "drawdown_from_52w_high_pct"),
            )
            metrics["rsi"] = _first_number(metrics.get("rsi"), item.rsi, _candidate_source_number(item, "rsi", "RSI"))
            metrics["ma20"] = _first_number(
                metrics.get("ma20"),
                item.ma20_dist_pct,
                _candidate_source_number(item, "ma20_dist_pct", "dist_sma20_pct"),
            )
            metrics["vol20"] = _first_number(metrics.get("vol20"), item.volume_ratio_20)
            metrics["atr"] = _first_number(metrics.get("atr"), _candidate_source_number(item, "atr_pct"))
            metrics["adx"] = _first_number(metrics.get("adx"), _candidate_source_number(item, "adx"))
            metrics["rs"] = _first_number(metrics.get("rs"), _candidate_source_number(item, "rs_rank_vs_index"))
            metrics["breakout_dist_20d_high_pct"] = _first_number(
                metrics.get("breakout_dist_20d_high_pct"),
                _candidate_source_number(item, "breakout_dist_20d_high_pct"),
            )
            metrics["compression_count"] = _first_number(
                metrics.get("compression_count"),
                _candidate_source_number(item, "compression_count"),
            )
            metrics["entry"] = _first_text(metrics.get("entry"), item.entry_type)
            if section.key == STEADY_WINNER_SECTION_KEY and item.pul_score is not None:
                metrics["score"] = _first_text(metrics.get("score"), _format_pul(item.pul_score))
                metrics["score_value"] = _first_number(metrics.get("score_value"), item.pul_score)
            elif section.key == EARLY_REVERSAL_KEY and item.early_reversal_score is not None:
                metrics["score"] = _first_text(metrics.get("score"), _format_ers(item.early_reversal_score))
                metrics["score_value"] = _first_number(metrics.get("score_value"), item.early_reversal_score)
            elif section.key == HULL_BUY_TURN_KEY:
                metrics["score"] = _first_text(metrics.get("score"), "HULL")
            elif section.key == STARTUP9_CONFIRM_KEY:
                metrics["score"] = _first_text(metrics.get("score"), f"S9 {int(item.startup9_confirm_count or 0)}/9")
                metrics["score_value"] = _first_number(metrics.get("score_value"), item.startup9_score)
            elif section.key == TECHNICAL_BUY_CLUSTER_KEY and item.technical_buy_score is not None:
                metrics["score"] = _first_text(metrics.get("score"), _format_technical_buy(item.technical_buy_score))
                metrics["score_value"] = _first_number(metrics.get("score_value"), item.technical_buy_score)
            elif section.key in QBS_DISPLAY_NUMBERS and item.qbs_score is not None:
                metrics["score"] = _first_text(metrics.get("score"), _format_qbs(item.qbs_score))
                metrics["score_value"] = _first_number(metrics.get("score_value"), item.qbs_score)
    return lookup


def _build_telegram_board_row(
    section_key: str,
    item: TelegramCandidate,
    idx: int,
    *,
    metric_fallback: Mapping[str, Any] | None = None,
    market_fallback: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    section_key = str(section_key or "")
    fallback = dict(metric_fallback or {})
    market = dict(market_fallback or {})
    risk_text = _board_risk_text(item, section_key)
    score_value: float | None = None
    if section_key == STEADY_WINNER_SECTION_KEY:
        score_value = item.pul_score
    elif section_key == EARLY_REVERSAL_KEY:
        score_value = item.early_reversal_score
    elif section_key == STARTUP9_CONFIRM_KEY:
        score_value = item.startup9_score
    elif section_key == TECHNICAL_BUY_CLUSTER_KEY:
        score_value = item.technical_buy_score
    elif section_key in QBS_DISPLAY_NUMBERS:
        score_value = item.qbs_score
    row = {
        "rank": item.rank or idx,
        "ticker": item.ticker,
        "section_key": section_key,
        "section": _board_section_label(section_key),
        "part": _board_section_label(section_key),
        "bucket": _board_bucket_label(item, section_key),
        "price": _first_number(item.price, fallback.get("price"), market.get("price")),
        "today_pct": _first_number(_board_today_pct(item, section_key), fallback.get("today_pct"), market.get("today_pct")),
        "five_day_pct": _first_number(_board_five_day_pct(item, section_key), fallback.get("five_day_pct"), market.get("five_day_pct")),
        "one_month_pct": _first_number(
            item.ret_1m_pct,
            _candidate_source_number(item, "ret_1m_pct", "ret20_pct"),
            fallback.get("one_month_pct"),
            market.get("one_month_pct"),
        ),
        "one_year_pct": _first_number(
            item.ret_1y_pct,
            _candidate_source_number(item, "ret_1y_pct", "ret252_pct"),
            fallback.get("one_year_pct"),
            market.get("one_year_pct"),
        ),
        "high_pos_pct": _first_number(
            item.high_pos_pct,
            _candidate_source_number(item, "high_pos_pct", "drawdown_from_52w_high_pct"),
            fallback.get("high_pos_pct"),
            market.get("high_pos_pct"),
        ),
        "breakout_dist_20d_high_pct": _first_number(
            _candidate_source_number(item, "breakout_dist_20d_high_pct"),
            fallback.get("breakout_dist_20d_high_pct"),
        ),
        "score": _first_text(_board_score_text(item, section_key), fallback.get("score")),
        "score_value": _first_number(score_value, fallback.get("score_value")),
        "rsi": _first_number(item.rsi, _candidate_source_number(item, "rsi", "RSI"), fallback.get("rsi"), market.get("rsi")),
        "vol20": _first_number(item.volume_ratio_20, fallback.get("vol20"), market.get("vol20")),
        "ma20": _first_number(
            item.ma20_dist_pct,
            _candidate_source_number(item, "ma20_dist_pct", "dist_sma20_pct"),
            fallback.get("ma20"),
            market.get("ma20"),
        ),
        "atr": _first_number(_candidate_source_number(item, "atr_pct"), fallback.get("atr")),
        "adx": _first_number(_candidate_source_number(item, "adx"), fallback.get("adx")),
        "rs": _first_number(_candidate_source_number(item, "rs_rank_vs_index"), fallback.get("rs")),
        "compression_count": _first_number(_candidate_source_number(item, "compression_count"), fallback.get("compression_count")),
        "entry": _board_entry_text(item, section_key, fallback.get("entry")),
        "setup": "+".join(_board_setup_parts(item)) or "-",
        "setup_parts": _board_setup_parts(item),
        "risk": risk_text,
        "risk_flags": list(item.risk_flags or []),
        "risk_parts": _board_risk_parts(risk_text),
    }
    row["has_warning"] = _board_has_warning(row)
    return row


def _build_telegram_board_rows(
    digest: TelegramDigest,
    *,
    market_metric_lookup: Mapping[str, Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    board_section_keys = {
        *QBS_DISPLAY_NUMBERS.keys(),
        *AGGRESSIVE_SECTION_KEY_SET,
        STARTUP9_CONFIRM_KEY,
        TECHNICAL_BUY_CLUSTER_KEY,
        STEADY_WINNER_SECTION_KEY,
        EARLY_REVERSAL_KEY,
        HULL_BUY_TURN_KEY,
        "five_day_top",
    }
    metric_lookup = _collect_digest_metric_lookup(digest)
    market_lookup = {str(ticker or "").strip().upper(): dict(metrics or {}) for ticker, metrics in dict(market_metric_lookup or {}).items()}
    rows: list[dict[str, Any]] = []
    for section in _visible_telegram_sections(digest):
        if section.key not in board_section_keys:
            continue
        for idx, item in enumerate(section.items, start=1):
            ticker = str(item.ticker or "").strip().upper()
            rows.append(
                _build_telegram_board_row(
                    section.key,
                    item,
                    idx,
                    metric_fallback=metric_lookup.get(ticker, {}),
                    market_fallback=market_lookup.get(ticker, {}),
                )
            )
    return rows


def _filter_telegram_board_rows(rows: list[dict[str, Any]], filter_key: str) -> list[dict[str, Any]]:
    if filter_key == "decision":
        return [row for row in rows if str(row.get("section_key") or "") in DECISION_SECTION_KEYS]
    if filter_key == "aggressive":
        return [row for row in rows if str(row.get("section_key") or "") in AGGRESSIVE_SECTION_KEY_SET]
    if filter_key == "qbs":
        return [row for row in rows if str(row.get("section_key") or "") in QBS_DISPLAY_NUMBERS]
    if filter_key == "technical":
        return [row for row in rows if str(row.get("section_key") or "") == TECHNICAL_BUY_CLUSTER_KEY]
    if filter_key == "startup9":
        return [row for row in rows if str(row.get("section_key") or "") == STARTUP9_CONFIRM_KEY]
    if filter_key == "entry":
        entry_keys = {"qbs_buy_now", "qbs_chase_watch", STARTUP9_CONFIRM_KEY, TECHNICAL_BUY_CLUSTER_KEY, HULL_BUY_TURN_KEY, *AGGRESSIVE_ENTRY_SECTION_KEYS}
        return [row for row in rows if str(row.get("section_key") or "") in entry_keys]
    if filter_key == "trend":
        trend_keys = {STEADY_WINNER_SECTION_KEY, "five_day_top", *AGGRESSIVE_TREND_SECTION_KEYS}
        return [row for row in rows if str(row.get("section_key") or "") in trend_keys]
    if filter_key == "reversal":
        return [
            row
            for row in rows
            if str(row.get("section_key") or "") in {EARLY_REVERSAL_KEY, AGGRESSIVE_NEXT_DAY_SECTION_KEYS[0]}
        ]
    if filter_key == "hull":
        return [row for row in rows if row.get("section_key") == HULL_BUY_TURN_KEY]
    if filter_key == "five_day":
        return [row for row in rows if row.get("section_key") == "five_day_top"]
    if filter_key == "board":
        return [row for row in rows if str(row.get("section_key") or "") in BOARD_TYPE_SECTION_KEYS]
    if filter_key == "risk":
        return [row for row in rows if bool(row.get("has_warning"))]
    return rows


BOARD_REQUIRED_NUMERIC_FIELDS: tuple[str, ...] = (
    "price",
    "today_pct",
    "five_day_pct",
    "one_month_pct",
    "one_year_pct",
    "high_pos_pct",
    "rsi",
    "vol20",
    "ma20",
)
AGGRESSIVE_BOARD_REQUIRED_NUMERIC_FIELDS: tuple[str, ...] = (
    "price",
    "today_pct",
    "five_day_pct",
    "high_pos_pct",
    "vol20",
    "ma20",
)


def _board_missing_metric_tickers(rows: Iterable[Mapping[str, Any]]) -> list[str]:
    tickers: list[str] = []
    for row in rows:
        ticker = str(row.get("ticker") or "").strip().upper()
        if not ticker or ticker in tickers:
            continue
        required_fields = (
            AGGRESSIVE_BOARD_REQUIRED_NUMERIC_FIELDS
            if str(row.get("section_key") or "") in AGGRESSIVE_SECTION_KEY_SET
            else BOARD_REQUIRED_NUMERIC_FIELDS
        )
        if any(_optional_float(row.get(field)) is None for field in required_fields):
            tickers.append(ticker)
    return tickers


def _history_return_pct(values: Any, periods: int) -> float | None:
    try:
        clean = values.dropna()
    except Exception:
        return None
    if len(clean) < 2:
        return None
    offset = min(max(1, periods), len(clean) - 1)
    current = _optional_float(clean.iloc[-1])
    previous = _optional_float(clean.iloc[-(offset + 1)])
    if current is None or previous is None or abs(previous) <= 1e-10:
        return None
    return ((current - previous) / previous) * 100.0


def _history_rsi(close_values: Any, period: int = 14) -> float | None:
    try:
        close = close_values.dropna()
        delta = close.diff()
        gains = delta.clip(lower=0).tail(period)
        losses = (-delta.clip(upper=0)).tail(period)
        avg_gain = float(gains.mean())
        avg_loss = float(losses.mean())
    except Exception:
        return None
    if avg_loss <= 1e-10:
        return 100.0 if avg_gain > 1e-10 else 50.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _board_metrics_from_history_frame(frame: Any) -> dict[str, float]:
    if frame is None or getattr(frame, "empty", True):
        return {}
    if "Close" not in getattr(frame, "columns", []):
        return {}
    close = frame["Close"].dropna()
    if len(close) < 2:
        return {}
    latest_price = _optional_float(close.iloc[-1])
    metrics: dict[str, float] = {}
    if latest_price is not None:
        metrics["price"] = latest_price
    for key, periods in (
        ("today_pct", 1),
        ("five_day_pct", 5),
        ("one_month_pct", 20),
        ("one_year_pct", 252),
    ):
        value = _history_return_pct(close, periods)
        if value is not None:
            metrics[key] = value
    try:
        high_source = frame["High"].dropna() if "High" in getattr(frame, "columns", []) else close
        high_252 = _optional_float(high_source.tail(252).max())
    except Exception:
        high_252 = None
    if latest_price is not None and high_252 is not None and abs(high_252) > 1e-10:
        metrics["high_pos_pct"] = ((latest_price - high_252) / high_252) * 100.0
    rsi = _history_rsi(close)
    if rsi is not None:
        metrics["rsi"] = rsi
    try:
        ma20 = _optional_float(close.tail(20).mean())
    except Exception:
        ma20 = None
    if latest_price is not None and ma20 is not None and abs(ma20) > 1e-10:
        metrics["ma20"] = ((latest_price - ma20) / ma20) * 100.0
    if "Volume" in getattr(frame, "columns", []):
        try:
            volume = frame["Volume"].dropna()
            latest_volume = _optional_float(volume.iloc[-1])
            avg20_volume = _optional_float(volume.tail(20).mean())
            if latest_volume is not None and avg20_volume is not None and avg20_volume > 1e-10:
                metrics["vol20"] = latest_volume / avg20_volume
        except Exception:
            pass
    return metrics


def _yfinance_symbol(ticker: str) -> str:
    return str(ticker or "").strip().upper().replace(".", "-")


@st.cache_data(ttl=1800, show_spinner=False)
def _fetch_board_market_metric_lookup(tickers: tuple[str, ...]) -> dict[str, dict[str, float]]:
    symbols = [str(ticker or "").strip().upper() for ticker in tickers if str(ticker or "").strip()]
    if not symbols:
        return {}
    try:
        import pandas as pd  # type: ignore
        import yfinance as yf  # type: ignore
    except Exception:
        return {}

    yf_to_ticker = {_yfinance_symbol(ticker): ticker for ticker in symbols}
    try:
        data = yf.download(
            list(yf_to_ticker),
            period="18mo",
            interval="1d",
            group_by="ticker",
            auto_adjust=False,
            progress=False,
            threads=True,
        )
    except Exception:
        return {}
    if data is None or getattr(data, "empty", True):
        return {}

    result: dict[str, dict[str, float]] = {}
    if len(yf_to_ticker) == 1:
        ticker = next(iter(yf_to_ticker.values()))
        frame = data
        if isinstance(getattr(data, "columns", None), pd.MultiIndex):
            yf_symbol = next(iter(yf_to_ticker))
            try:
                frame = data[yf_symbol]
            except Exception:
                pass
        metrics = _board_metrics_from_history_frame(frame)
        if metrics:
            result[ticker] = metrics
        return result

    columns = getattr(data, "columns", None)
    if not isinstance(columns, pd.MultiIndex):
        return result
    available_symbols = set(str(value).upper() for value in columns.get_level_values(0))
    for yf_symbol, ticker in yf_to_ticker.items():
        if yf_symbol not in available_symbols:
            continue
        try:
            frame = data[yf_symbol]
        except Exception:
            continue
        metrics = _board_metrics_from_history_frame(frame)
        if metrics:
            result[ticker] = metrics
    return result


def _metric_tone(value: Any, *, warning_abs: float | None = None) -> str:
    number = _optional_float(value)
    if number is None:
        return "muted"
    if warning_abs is not None and abs(number) >= warning_abs:
        return "warning"
    return _change_tone(number)


def _rsi_tone(value: Any) -> str:
    number = _optional_float(value)
    if number is None:
        return "muted"
    if number >= 75:
        return "warning"
    if number >= 50:
        return "positive"
    if number < 40:
        return "negative"
    return "muted"


def _high_pos_tone(value: Any) -> str:
    number = _optional_float(value)
    if number is None:
        return "muted"
    if number >= -5.0:
        return "positive"
    if number >= -15.0:
        return "info"
    if number >= -30.0:
        return "warning"
    return "negative"


def _atr_tone(value: Any) -> str:
    number = _optional_float(value)
    if number is None:
        return "muted"
    if number >= 8:
        return "warning"
    if number >= 4:
        return "positive"
    if number >= 3:
        return "info"
    return "muted"


def _adx_tone(value: Any) -> str:
    number = _optional_float(value)
    if number is None:
        return "muted"
    if number >= 35:
        return "warning"
    if number >= 25:
        return "positive"
    if number >= 18:
        return "info"
    return "muted"


def _rs_tone(value: Any) -> str:
    number = _optional_float(value)
    if number is None:
        return "muted"
    if number >= 85:
        return "positive"
    if number >= 70:
        return "info"
    if number < 50:
        return "warning"
    return "muted"


def _board_cell(text: Any, tone: str = "muted", *, strong: bool = False) -> str:
    if tone not in {"positive", "negative", "warning", "info", "muted", "accent"}:
        tone = "muted"
    class_name = "cpx-board-cell"
    if strong:
        class_name += " cpx-board-cell--strong"
    return f"<span class='{class_name}' data-tone='{tone}'>{_html_text(text)}</span>"


def _board_token_html(text: Any, tone: str = "muted") -> str:
    label = _html_text(text)
    if not label:
        return ""
    if tone not in {"positive", "negative", "warning", "info", "muted", "accent"}:
        tone = "muted"
    return f"<span class='cpx-board-token' data-tone='{tone}'>{label}</span>"


def _board_tokens_html(values: Any, tone: str = "muted", *, limit: int = 4) -> str:
    if isinstance(values, str):
        tokens = _split_reason_parts(values)
    else:
        tokens = [str(value or "").strip() for value in list(values or []) if str(value or "").strip()]
    tokens = tokens[: max(0, int(limit or 0))]
    if not tokens:
        return _board_cell("-", "muted")
    return f"<div class='cpx-board-token-list'>{''.join(_board_token_html(token, tone) for token in tokens)}</div>"


def _render_digest_html(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


def _board_high_text(row: Mapping[str, Any]) -> str:
    high_52w = _format_float(row.get("high_pos_pct"), 1, signed=True, suffix="%")
    high_20d = _format_float(row.get("breakout_dist_20d_high_pct"), 1, signed=True, suffix="%")
    if high_20d != "--":
        return f"52W {high_52w} / 20D {high_20d}"
    return high_52w


def _board_rows_html(rows: list[dict[str, Any]]) -> str:
    body_rows: list[str] = []
    for row in rows:
        section_key = str(row.get("section_key") or "")
        score_tone = _qbs_tone(row.get("score_value"))
        if section_key == STEADY_WINNER_SECTION_KEY:
            score_tone = _qbs_tone(row.get("score_value"))
        if section_key == TECHNICAL_BUY_CLUSTER_KEY:
            score_tone = _technical_buy_tone(row.get("score_value"))
        risk_tone = "warning" if row.get("has_warning") else "muted"
        body_rows.append(
            "<tr>"
            f"<td>{_board_cell(row.get('ticker'), 'accent', strong=True)}</td>"
            f"<td>{_board_cell(row.get('section'), _section_tone(section_key))}</td>"
            f"<td>{_board_cell(row.get('bucket'), _signal_tone(row.get('bucket'), section_key))}</td>"
            f"<td class='cpx-board-num'>{_html_text(_format_float(row.get('price'), 2))}</td>"
            f"<td>{_board_cell(_format_float(row.get('today_pct'), 2, signed=True, suffix='%'), _metric_tone(row.get('today_pct')))}</td>"
            f"<td>{_board_cell(_format_float(row.get('five_day_pct'), 2, signed=True, suffix='%'), _metric_tone(row.get('five_day_pct')))}</td>"
            f"<td>{_board_cell(_format_float(row.get('one_month_pct'), 2, signed=True, suffix='%'), _metric_tone(row.get('one_month_pct')))}</td>"
            f"<td>{_board_cell(_format_float(row.get('one_year_pct'), 2, signed=True, suffix='%'), _metric_tone(row.get('one_year_pct')))}</td>"
            f"<td>{_board_cell(_format_float(row.get('high_pos_pct'), 2, signed=True, suffix='%'), _high_pos_tone(row.get('high_pos_pct')))}</td>"
            f"<td>{_board_cell(row.get('score'), score_tone)}</td>"
            f"<td>{_board_cell(_format_float(row.get('rsi'), 1), _rsi_tone(row.get('rsi')))}</td>"
            f"<td>{_board_cell(_format_ratio(row.get('vol20')), _volume_tone(row.get('vol20')))}</td>"
            f"<td>{_board_cell(_format_float(row.get('ma20'), 1, signed=True, suffix='%'), _metric_tone(row.get('ma20'), warning_abs=20.0))}</td>"
            f"<td>{_board_cell(row.get('entry') or '-', 'info' if row.get('entry') not in {None, '', '-'} else 'muted')}</td>"
            f"<td>{_board_cell(row.get('risk') or '-', risk_tone)}</td>"
            "</tr>"
        )
    return "".join(body_rows)


def _aggressive_board_rows_html(rows: list[dict[str, Any]], *, include_rank: bool = False) -> str:
    body_rows: list[str] = []
    for row in rows:
        section_key = str(row.get("section_key") or "")
        risk_tone = "warning" if row.get("has_warning") else "muted"
        rank_cell = f"<td class='cpx-board-num'>#{_html_text(row.get('rank'))}</td>" if include_rank else ""
        body_rows.append(
            "<tr>"
            f"{rank_cell}"
            f"<td>{_board_cell(row.get('ticker'), 'accent', strong=True)}</td>"
            f"<td>{_board_cell(row.get('part') or row.get('section'), _section_tone(section_key))}</td>"
            f"<td>{_board_cell(_format_float(row.get('today_pct'), 2, signed=True, suffix='%'), _metric_tone(row.get('today_pct')))}</td>"
            f"<td>{_board_cell(_format_float(row.get('five_day_pct'), 2, signed=True, suffix='%'), _metric_tone(row.get('five_day_pct')))}</td>"
            f"<td>{_board_cell(_format_float(row.get('atr'), 1), _atr_tone(row.get('atr')))}</td>"
            f"<td>{_board_cell(_format_ratio(row.get('vol20')), _volume_tone(row.get('vol20')))}</td>"
            f"<td>{_board_cell(_format_float(row.get('rs'), 0), _rs_tone(row.get('rs')))}</td>"
            f"<td>{_board_cell(_format_float(row.get('adx'), 0), _adx_tone(row.get('adx')))}</td>"
            f"<td>{_board_cell(_format_float(row.get('ma20'), 1, signed=True, suffix='%'), _metric_tone(row.get('ma20'), warning_abs=20.0))}</td>"
            f"<td>{_board_cell(_board_high_text(row), _high_pos_tone(row.get('high_pos_pct')))}</td>"
            f"<td>{_board_tokens_html(row.get('setup_parts') or row.get('setup'), 'accent', limit=4)}</td>"
            f"<td>{_board_tokens_html(row.get('risk_parts') or row.get('risk'), risk_tone, limit=4)}</td>"
            "</tr>"
        )
    return "".join(body_rows)


def _aggressive_board_table_html(rows: list[dict[str, Any]], *, include_rank: bool = False) -> str:
    rank_header = "<th>Rank</th>" if include_rank else ""
    return (
        "<div class='cpx-board-wrap cpx-board-wrap--aggressive'>"
        "<table class='cpx-board-table cpx-board-table--aggressive'>"
        "<thead><tr>"
        f"{rank_header}"
        "<th>Ticker</th>"
        "<th>Part</th>"
        "<th>Today</th>"
        "<th>5D</th>"
        "<th>ATR</th>"
        "<th>Vol20</th>"
        "<th>RS</th>"
        "<th>ADX</th>"
        "<th>MA20</th>"
        "<th>High</th>"
        "<th>Setup</th>"
        "<th>Risk</th>"
        "</tr></thead>"
        f"<tbody>{_aggressive_board_rows_html(rows, include_rank=include_rank)}</tbody>"
        "</table>"
        "</div>"
    )


def _render_aggressive_board_table(rows: list[dict[str, Any]], *, include_rank: bool = False) -> None:
    _render_digest_html(_aggressive_board_table_html(rows, include_rank=include_rank))


def _board_table_html(rows: list[dict[str, Any]]) -> str:
    return f"""
    <div class='cpx-board-wrap'>
        <table class='cpx-board-table'>
            <thead>
                <tr>
                    <th>Ticker</th>
                    <th>Section</th>
                    <th>Bucket</th>
                    <th>Price</th>
                    <th>Today</th>
                    <th>5D</th>
                    <th>1M</th>
                    <th>1Y</th>
                    <th>High</th>
                    <th>S9/PUL/QBS/TBS</th>
                    <th>RSI</th>
                    <th>Vol20</th>
                    <th>MA20</th>
                    <th>Entry</th>
                    <th>Risk</th>
                </tr>
            </thead>
            <tbody>{_board_rows_html(rows)}</tbody>
        </table>
    </div>
    """


def _default_telegram_board_filter(rows: Iterable[Mapping[str, Any]]) -> str:
    row_list = list(rows)
    if any(str(row.get("section_key") or "") in DECISION_SECTION_KEYS for row in row_list):
        return "decision"
    if any(str(row.get("section_key") or "") == STARTUP9_CONFIRM_KEY for row in row_list):
        return "startup9"
    if any(str(row.get("section_key") or "") in AGGRESSIVE_SECTION_KEY_SET for row in row_list):
        return "aggressive"
    if any(str(row.get("section_key") or "") == TECHNICAL_BUY_CLUSTER_KEY for row in row_list):
        return "technical"
    return "all"


def _telegram_board_overview_html(rows: list[dict[str, Any]], filter_label: str) -> str:
    unique_tickers = _collect_recent_tickers(str(row.get("ticker") or "") for row in rows)
    decision_count = sum(1 for row in rows if str(row.get("section_key") or "") in DECISION_SECTION_KEYS)
    aggressive_count = sum(1 for row in rows if str(row.get("section_key") or "") in AGGRESSIVE_SECTION_KEY_SET)
    qbs_count = sum(1 for row in rows if str(row.get("section_key") or "") in QBS_DISPLAY_NUMBERS)
    startup9_count = sum(1 for row in rows if str(row.get("section_key") or "") == STARTUP9_CONFIRM_KEY)
    technical_count = sum(1 for row in rows if str(row.get("section_key") or "") == TECHNICAL_BUY_CLUSTER_KEY)
    board_count = sum(1 for row in rows if str(row.get("section_key") or "") in BOARD_TYPE_SECTION_KEYS)
    warning_count = sum(1 for row in rows if row.get("has_warning"))
    items = [
        ("View", filter_label),
        ("Rows", f"{len(rows):,}"),
        ("Tickers", f"{len(unique_tickers):,}"),
        ("Decision", f"{decision_count:,}"),
        ("Aggressive", f"{aggressive_count:,}"),
        ("QBS", f"{qbs_count:,}"),
        ("S9", f"{startup9_count:,}"),
        ("Tech", f"{technical_count:,}"),
        ("Board", f"{board_count:,}"),
        ("Risk", f"{warning_count:,}"),
    ]
    metric_html = "".join(
        f"<div class='cpx-board-stat'><b>{_html_text(label)}</b><strong>{_html_text(value)}</strong></div>"
        for label, value in items
    )
    return (
        "<div class='cpx-board-dashboard-head'>"
        "<div>"
        "<div class='cpx-digest-eyebrow'>Trading Board</div>"
        "<div class='cpx-board-dashboard-title'>통합 후보 압축표</div>"
        "<p>Telegram 메시지 섹션과 중복 티커 노출 정책을 유지한 상태로, 다음 거래일 후보를 한 화면에서 비교합니다.</p>"
        "</div>"
        f"<div class='cpx-board-stats'>{metric_html}</div>"
        "</div>"
    )


def _render_telegram_visual_board(digest: TelegramDigest, *, on_select_ticker: Callable[[str], None]) -> None:
    rows = _build_telegram_board_rows(digest)
    missing_metric_tickers = _board_missing_metric_tickers(rows)
    if missing_metric_tickers:
        market_metric_lookup = _fetch_board_market_metric_lookup(tuple(missing_metric_tickers))
        if market_metric_lookup:
            rows = _build_telegram_board_rows(digest, market_metric_lookup=market_metric_lookup)
    if not rows:
        return
    filter_options = {
        "decision": "Decision",
        "qbs": "QBS",
        "startup9": "Startup9",
        "technical": "Tech Buy",
        "aggressive": "Aggressive",
        "board": "Board",
        "entry": "Entry",
        "trend": "Trend",
        "reversal": "Reversal",
        "hull": "HULL",
        "five_day": "Momentum",
        "risk": "Risk",
        "all": "All",
    }
    option_keys = list(filter_options)
    default_filter = _default_telegram_board_filter(rows)
    filter_key = st.radio(
        "Telegram board filter",
        options=option_keys,
        index=option_keys.index(default_filter),
        format_func=lambda key: filter_options.get(str(key), str(key)),
        horizontal=True,
        key="home_telegram_digest_board_filter_v2",
        label_visibility="collapsed",
    )
    filtered_rows = _filter_telegram_board_rows(rows, str(filter_key))
    if not filtered_rows:
        st.markdown("<div class='cpx-digest-empty'>No board rows.</div>", unsafe_allow_html=True)
        return

    _render_digest_html(_telegram_board_overview_html(rows, filter_options.get(str(filter_key), str(filter_key))))
    if str(filter_key) == "aggressive":
        _render_aggressive_board_table(filtered_rows)
    else:
        _render_digest_html(_board_table_html(filtered_rows))
    board_tickers = _collect_recent_tickers(str(row.get("ticker") or "") for row in filtered_rows)
    st.markdown("<div class='cpx-board-action-label'>빠른 분석</div>", unsafe_allow_html=True)
    _render_ticker_button_row(
        board_tickers[:40],
        key_prefix=f"home_telegram_board_{filter_key}",
        on_select_ticker=on_select_ticker,
        columns=8,
    )


def _render_telegram_digest_styles() -> None:
    st.markdown(
        f"""
        <style>
        .cpx-digest-summary,
        .cpx-digest-table {{
            font-family: {FONT_STACK};
            letter-spacing: 0;
        }}
        .cpx-digest-summary {{
            margin: 2px 0 16px;
            padding: 16px;
            border: 1px solid rgba(148, 163, 184, .18);
            border-radius: 8px;
            background:
                linear-gradient(180deg, rgba(19, 28, 45, .96), rgba(15, 23, 42, .90));
            box-shadow: 0 14px 28px rgba(2, 6, 23, .16);
        }}
        .cpx-digest-summary__top {{
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 14px;
            flex-wrap: wrap;
        }}
        .cpx-digest-eyebrow {{
            color: var(--sigl-text-muted, #94A3B8);
            font-size: .72rem;
            font-weight: 900;
            text-transform: uppercase;
        }}
        .cpx-digest-title {{
            margin-top: 4px;
            color: var(--sigl-text-strong, #F8FAFC);
            font-size: 1rem;
            font-weight: 900;
        }}
        .cpx-digest-badges,
        .cpx-digest-tags {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
        }}
        .cpx-digest-badge {{
            display: inline-flex;
            align-items: center;
            min-height: 24px;
            padding: 4px 9px;
            border-radius: 999px;
            border: 1px solid rgba(148, 163, 184, .18);
            background: rgba(148, 163, 184, .08);
            color: var(--sigl-text, #E2E8F0);
            font-size: .72rem;
            font-weight: 800;
            line-height: 1;
            white-space: nowrap;
        }}
        .cpx-digest-badge[data-tone="accent"] {{
            border-color: rgba(142, 164, 255, .36);
            background: rgba(142, 164, 255, .14);
            color: #DDE5FF;
        }}
        .cpx-digest-badge[data-tone="positive"] {{
            border-color: rgba(99, 217, 162, .36);
            background: rgba(99, 217, 162, .12);
            color: #B8F4D3;
        }}
        .cpx-digest-badge[data-tone="negative"] {{
            border-color: rgba(255, 143, 150, .38);
            background: rgba(255, 143, 150, .12);
            color: #FFC4C8;
        }}
        .cpx-digest-badge[data-tone="warning"] {{
            border-color: rgba(246, 195, 94, .40);
            background: rgba(246, 195, 94, .13);
            color: #FFE0A3;
        }}
        .cpx-digest-badge[data-tone="info"] {{
            border-color: rgba(125, 211, 252, .38);
            background: rgba(125, 211, 252, .12);
            color: #BCEBFF;
        }}
        .cpx-digest-metrics {{
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 8px;
            margin-top: 14px;
        }}
        .cpx-digest-metric {{
            min-width: 0;
            padding: 10px 11px;
            border: 1px solid rgba(148, 163, 184, .14);
            border-radius: 8px;
            background: rgba(255, 255, 255, .035);
        }}
        .cpx-digest-metric b {{
            display: block;
            color: var(--sigl-text-muted, #94A3B8);
            font-size: .68rem;
            font-weight: 850;
        }}
        .cpx-digest-metric strong {{
            display: block;
            margin-top: 4px;
            color: var(--sigl-text-strong, #F8FAFC);
            font-size: .95rem;
            font-weight: 900;
        }}
        .cpx-digest-section-meta {{
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 8px;
            margin: 0 0 10px;
        }}
        .cpx-digest-quality {{
            color: var(--sigl-text-muted, #94A3B8);
            font-size: .76rem;
            font-weight: 700;
        }}
        .cpx-digest-table-wrap {{
            width: 100%;
            overflow-x: auto;
            border: 1px solid rgba(148, 163, 184, .16);
            border-radius: 8px;
            background: rgba(15, 23, 42, .55);
            margin-bottom: 12px;
        }}
        table.cpx-digest-table {{
            width: 100%;
            min-width: 880px;
            border-collapse: collapse;
        }}
        .cpx-digest-table th {{
            padding: 10px 12px;
            border-bottom: 1px solid rgba(148, 163, 184, .16);
            background: rgba(255, 255, 255, .035);
            color: var(--sigl-text-muted, #94A3B8);
            font-size: .70rem;
            font-weight: 900;
            text-align: left;
            text-transform: uppercase;
        }}
        .cpx-digest-table td {{
            padding: 10px 12px;
            border-top: 1px solid rgba(148, 163, 184, .10);
            color: var(--sigl-text, #E2E8F0);
            font-size: .80rem;
            font-weight: 750;
            vertical-align: middle;
        }}
        .cpx-digest-table tr:hover td {{
            background: rgba(142, 164, 255, .06);
        }}
        .cpx-digest-rank {{
            color: var(--sigl-text-muted, #94A3B8);
            font-weight: 900;
        }}
        .cpx-digest-ticker {{
            color: var(--sigl-text-strong, #F8FAFC);
            font-weight: 950;
        }}
        .cpx-digest-num {{
            font-variant-numeric: tabular-nums;
            white-space: nowrap;
        }}
        .cpx-digest-reason {{
            color: var(--sigl-text-muted, #94A3B8);
            font-size: .76rem;
            font-weight: 750;
        }}
        .cpx-digest-empty {{
            padding: 14px 2px 4px;
            color: var(--sigl-text-muted, #94A3B8);
            font-size: .82rem;
            font-weight: 750;
        }}
        .cpx-board-wrap {{
            width: 100%;
            max-height: 760px;
            overflow: auto;
            border: 1px solid rgba(148, 163, 184, .16);
            border-radius: 8px;
            background: rgba(15, 23, 42, .68);
            margin: 8px 0 12px;
        }}
        .cpx-board-wrap--aggressive {{
            max-height: 720px;
        }}
        table.cpx-board-table {{
            width: 100%;
            min-width: 1280px;
            border-collapse: separate;
            border-spacing: 0;
            font-family: {FONT_STACK};
            letter-spacing: 0;
        }}
        table.cpx-board-table--aggressive {{
            min-width: 1120px;
        }}
        .cpx-board-table th {{
            position: sticky;
            top: 0;
            z-index: 1;
            padding: 8px 10px;
            border-bottom: 1px solid rgba(148, 163, 184, .18);
            background: rgba(15, 23, 42, .98);
            color: var(--sigl-text-muted, #94A3B8);
            font-size: .68rem;
            font-weight: 950;
            text-align: left;
            text-transform: uppercase;
            white-space: nowrap;
        }}
        .cpx-board-table td {{
            padding: 6px 8px;
            border-top: 1px solid rgba(148, 163, 184, .08);
            color: var(--sigl-text, #E2E8F0);
            font-size: .76rem;
            font-weight: 800;
            vertical-align: middle;
            white-space: nowrap;
        }}
        .cpx-board-table tr:hover td {{
            background: rgba(142, 164, 255, .06);
        }}
        .cpx-board-num {{
            font-variant-numeric: tabular-nums;
            color: var(--sigl-text-strong, #F8FAFC);
        }}
        .cpx-board-cell {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 58px;
            max-width: 240px;
            min-height: 24px;
            padding: 4px 8px;
            border-radius: 6px;
            border: 1px solid rgba(148, 163, 184, .14);
            background: rgba(148, 163, 184, .08);
            color: var(--sigl-text, #E2E8F0);
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            font-variant-numeric: tabular-nums;
        }}
        .cpx-board-cell--strong {{
            min-width: 66px;
            font-weight: 950;
        }}
        .cpx-board-cell[data-tone="accent"] {{
            border-color: rgba(142, 164, 255, .42);
            background: rgba(142, 164, 255, .16);
            color: #E5EAFF;
        }}
        .cpx-board-cell[data-tone="positive"] {{
            border-color: rgba(99, 217, 162, .34);
            background: rgba(16, 185, 129, .18);
            color: #BDF7D6;
        }}
        .cpx-board-cell[data-tone="negative"] {{
            border-color: rgba(255, 143, 150, .34);
            background: rgba(239, 68, 68, .18);
            color: #FFC4C8;
        }}
        .cpx-board-cell[data-tone="warning"] {{
            border-color: rgba(246, 195, 94, .40);
            background: rgba(245, 158, 11, .18);
            color: #FFE2A8;
        }}
        .cpx-board-cell[data-tone="info"] {{
            border-color: rgba(125, 211, 252, .34);
            background: rgba(14, 165, 233, .16);
            color: #C8EEFF;
        }}
        .cpx-board-token-list {{
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 4px;
            max-width: 260px;
        }}
        .cpx-board-token {{
            display: inline-flex;
            align-items: center;
            min-height: 20px;
            padding: 3px 6px;
            border-radius: 6px;
            border: 1px solid rgba(148, 163, 184, .14);
            background: rgba(148, 163, 184, .08);
            color: var(--sigl-text, #E2E8F0);
            font-size: .68rem;
            font-weight: 850;
            line-height: 1;
            white-space: nowrap;
        }}
        .cpx-board-token[data-tone="accent"] {{
            border-color: rgba(142, 164, 255, .34);
            background: rgba(142, 164, 255, .14);
            color: #E5EAFF;
        }}
        .cpx-board-token[data-tone="positive"] {{
            border-color: rgba(99, 217, 162, .30);
            background: rgba(16, 185, 129, .16);
            color: #BDF7D6;
        }}
        .cpx-board-token[data-tone="negative"] {{
            border-color: rgba(255, 143, 150, .30);
            background: rgba(239, 68, 68, .16);
            color: #FFC4C8;
        }}
        .cpx-board-token[data-tone="warning"] {{
            border-color: rgba(246, 195, 94, .36);
            background: rgba(245, 158, 11, .16);
            color: #FFE2A8;
        }}
        .cpx-board-token[data-tone="info"] {{
            border-color: rgba(125, 211, 252, .30);
            background: rgba(14, 165, 233, .14);
            color: #C8EEFF;
        }}
        .cpx-digest-summary {{
            margin: 2px 0 18px;
            padding: 18px;
            border-color: rgba(148, 163, 184, .20);
            background:
                linear-gradient(180deg, rgba(17, 24, 39, .98), rgba(12, 18, 32, .94));
        }}
        .cpx-digest-title {{
            font-size: 1.18rem;
            letter-spacing: 0;
        }}
        .cpx-digest-subtitle {{
            max-width: 720px;
            margin: 6px 0 0;
            color: var(--sigl-text-muted, #94A3B8);
            font-size: .80rem;
            font-weight: 700;
            line-height: 1.45;
        }}
        .cpx-digest-metrics {{
            grid-template-columns: repeat(6, minmax(0, 1fr));
            gap: 10px;
        }}
        .cpx-digest-metric {{
            min-height: 62px;
            border-color: rgba(148, 163, 184, .16);
            background: rgba(255, 255, 255, .045);
        }}
        .cpx-board-dashboard-head {{
            display: flex;
            justify-content: space-between;
            gap: 18px;
            align-items: stretch;
            margin: 12px 0 10px;
            padding: 16px;
            border: 1px solid rgba(148, 163, 184, .18);
            border-radius: 8px;
            background: rgba(15, 23, 42, .62);
        }}
        .cpx-board-dashboard-title {{
            margin-top: 4px;
            color: var(--sigl-text-strong, #F8FAFC);
            font-size: 1rem;
            font-weight: 950;
        }}
        .cpx-board-dashboard-head p {{
            max-width: 650px;
            margin: 6px 0 0;
            color: var(--sigl-text-muted, #94A3B8);
            font-size: .78rem;
            font-weight: 720;
            line-height: 1.45;
        }}
        .cpx-board-stats {{
            display: grid;
            grid-template-columns: repeat(3, minmax(88px, 1fr));
            gap: 8px;
            min-width: min(460px, 100%);
        }}
        .cpx-board-stat {{
            padding: 9px 10px;
            border: 1px solid rgba(148, 163, 184, .14);
            border-radius: 8px;
            background: rgba(255, 255, 255, .04);
        }}
        .cpx-board-stat b {{
            display: block;
            color: var(--sigl-text-muted, #94A3B8);
            font-size: .64rem;
            font-weight: 900;
            text-transform: uppercase;
        }}
        .cpx-board-stat strong {{
            display: block;
            margin-top: 3px;
            color: var(--sigl-text-strong, #F8FAFC);
            font-size: .88rem;
            font-weight: 950;
            font-variant-numeric: tabular-nums;
        }}
        .cpx-board-wrap {{
            border-color: rgba(148, 163, 184, .18);
            background: rgba(9, 14, 25, .72);
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, .035);
        }}
        .cpx-board-table th {{
            letter-spacing: .02em;
        }}
        .cpx-board-table td {{
            padding: 7px 8px;
        }}
        .cpx-board-cell {{
            justify-content: flex-start;
        }}
        .cpx-board-action-label {{
            margin: 4px 0 8px;
            color: var(--sigl-text-muted, #94A3B8);
            font-size: .72rem;
            font-weight: 900;
            text-transform: uppercase;
        }}
        .cpx-home-recent-shell {{
            margin-top: 12px;
            padding: 14px;
            border: 1px solid rgba(148, 163, 184, .16);
            border-radius: 8px;
            background: rgba(15, 23, 42, .46);
        }}
        .cpx-home-empty {{
            margin: 6px 0 18px;
            padding: 18px;
            border: 1px solid rgba(246, 195, 94, .22);
            border-radius: 8px;
            background: rgba(245, 158, 11, .08);
            color: var(--sigl-text, #E2E8F0);
        }}
        .cpx-home-empty strong {{
            display: block;
            color: var(--sigl-text-strong, #F8FAFC);
            font-size: 1rem;
            font-weight: 950;
        }}
        .cpx-home-empty span {{
            display: block;
            margin-top: 6px;
            color: var(--sigl-text-muted, #94A3B8);
            font-size: .82rem;
            font-weight: 720;
        }}
        div[data-testid="stRadio"] {{
            margin: 8px 0 4px;
        }}
        div[data-testid="stRadio"] > div {{
            gap: 8px;
            flex-wrap: wrap;
        }}
        div[data-testid="stRadio"] label {{
            min-height: 32px;
            padding: 5px 10px;
            border: 1px solid rgba(148, 163, 184, .18);
            border-radius: 999px;
            background: rgba(148, 163, 184, .07);
        }}
        div[data-testid="stRadio"] label:has(input:checked) {{
            border-color: rgba(142, 164, 255, .46);
            background: rgba(142, 164, 255, .16);
        }}
        @media (max-width: 760px) {{
            .cpx-digest-metrics {{
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }}
            .cpx-digest-summary {{
                padding: 14px;
            }}
            .cpx-board-dashboard-head {{
                display: block;
            }}
            .cpx-board-stats {{
                grid-template-columns: repeat(2, minmax(0, 1fr));
                margin-top: 12px;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _digest_source_badge(source: str) -> tuple[str, str]:
    if source == "remote":
        return "원격 동기화", "accent"
    if source == "cache":
        return "캐시 복구", "warning"
    if source == "missing":
        return "연결 필요", "muted"
    return str(source or "unknown"), "muted"


def _render_telegram_summary_card(digest: TelegramDigest, *, source: str = "", digest_result: Mapping[str, Any] | None = None) -> None:
    source_label, source_tone = _digest_source_badge(source)
    visible_section_count = len(_visible_telegram_sections(digest))
    generated_text = digest.generated_at or digest.run_stamp or "--"
    metric_items = [
        ("시장일", digest.market_date or "--"),
        ("생성", generated_text),
        ("유니버스", f"{digest.universe_count:,}"),
        ("결과", f"{digest.result_count:,}"),
        ("제외", f"{digest.skip_count:,}"),
        ("섹션", f"{visible_section_count:,}"),
    ]
    metrics_html = "".join(
        f"<div class='cpx-digest-metric'><b>{_html_text(label)}</b><strong>{_html_text(value)}</strong></div>"
        for label, value in metric_items
    )
    badges_html = "".join(
        [
            _badge_html(digest.scan_label or digest.scan_mode or "post-close", "accent"),
            _badge_html(source_label, source_tone),
            _badge_html("구조 유지", "info"),
            _badge_html("TTL 900s", "muted"),
        ]
    )
    config = dict((digest_result or {}).get("config") or {})
    config_text = " / ".join(
        part
        for part in [
            str(config.get("repo") or "").strip(),
            str(config.get("branch") or "").strip(),
            str(config.get("path") or "").strip(),
        ]
        if part
    )
    subtitle = config_text or "Telegram digest payload를 그대로 사용해 후보를 비교합니다."
    st.markdown(
        f"""
        <div class='cpx-digest-summary'>
            <div class='cpx-digest-summary__top'>
                <div>
                    <div class='cpx-digest-eyebrow'>Telegram Digest Dashboard</div>
                    <div class='cpx-digest-title'>오늘 종목판</div>
                    <p class='cpx-digest-subtitle'>{_html_text(subtitle)}</p>
                </div>
                <div class='cpx-digest-badges'>{badges_html}</div>
            </div>
            <div class='cpx-digest-metrics'>{metrics_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _telegram_section_meta_html(section: TelegramSection) -> str:
    tone = _section_tone(section.key)
    meta_html = "".join(
        [
            _badge_html(f"{section.item_count}개", tone),
            _badge_html("랭킹" if section.ranked else "보드", "muted"),
        ]
    )
    if section.quality_floor:
        meta_html += f"<span class='cpx-digest-quality'>{_html_text(section.quality_floor)}</span>"
    return f"<div class='cpx-digest-section-meta'>{meta_html}</div>"


def _render_telegram_section_table(section: TelegramSection) -> None:
    st.markdown(_telegram_section_meta_html(section), unsafe_allow_html=True)

    if not section.items:
        st.markdown("<div class='cpx-digest-empty'>해당 티커가 없습니다.</div>", unsafe_allow_html=True)
        return

    if section.key in AGGRESSIVE_SECTION_KEY_SET:
        rows = [
            _build_telegram_board_row(section.key, item, idx)
            for idx, item in enumerate(section.items, start=1)
        ]
        _render_aggressive_board_table(rows, include_rank=True)
        return

    if section.key == STARTUP9_CONFIRM_KEY:
        rows = [
            "<tr>"
            f"<td class='cpx-digest-rank'>#{item.rank or idx}</td>"
            f"<td><span class='cpx-digest-ticker'>{_html_text(item.ticker)}</span></td>"
            f"<td>{_badge_html(f'S9 {int(item.startup9_confirm_count or 0)}/9', 'accent')}</td>"
            f"<td>{_badge_html(item.startup9_confirm_grade or item.label or '-', _signal_tone(item.startup9_confirm_grade or item.label, section.key))}</td>"
            f"<td>{_badge_html(item.startup9_profile or item.bucket or '-', 'info')}</td>"
            f"<td>{_badge_html(_format_float(item.chg_pct, 2, signed=True, suffix='%'), _change_tone(item.chg_pct))}</td>"
            f"<td>{_badge_html(_format_ratio(item.volume_ratio_20), _volume_tone(item.volume_ratio_20))}</td>"
            f"<td><div class='cpx-digest-tags'>{_candidate_tags_html(item)}</div></td>"
            "</tr>"
            for idx, item in enumerate(section.items, start=1)
        ]
        st.markdown(
            f"""
            <div class='cpx-digest-table-wrap'>
                <table class='cpx-digest-table'>
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Ticker</th>
                            <th>S9</th>
                            <th>Grade</th>
                            <th>Profile</th>
                            <th>Today</th>
                            <th>Vol20</th>
                            <th>Reason/Risk</th>
                        </tr>
                    </thead>
                    <tbody>{''.join(rows)}</tbody>
                </table>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    if section.key == TECHNICAL_BUY_CLUSTER_KEY:
        rows = [
            "<tr>"
            f"<td class='cpx-digest-rank'>#{item.rank or idx}</td>"
            f"<td><span class='cpx-digest-ticker'>{_html_text(item.ticker)}</span></td>"
            f"<td>{_badge_html(_format_technical_buy(item.technical_buy_score), _technical_buy_tone(item.technical_buy_score))}</td>"
            f"<td>{_badge_html(item.technical_buy_bucket or item.bucket or '-', _signal_tone(item.technical_buy_bucket or item.bucket, section.key))}</td>"
            f"<td>{_badge_html(_format_float(item.chg_pct, 2, signed=True, suffix='%'), _change_tone(item.chg_pct))}</td>"
            f"<td>{_badge_html(_format_ratio(item.volume_ratio_20), _volume_tone(item.volume_ratio_20))}</td>"
            f"<td>{_badge_html(str(item.technical_buy_signal_count or '-'), 'accent')}</td>"
            f"<td><div class='cpx-digest-tags'>{_candidate_tags_html(item)}</div></td>"
            "</tr>"
            for idx, item in enumerate(section.items, start=1)
        ]
        st.markdown(
            f"""
            <div class='cpx-digest-table-wrap'>
                <table class='cpx-digest-table'>
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Ticker</th>
                            <th>TBS</th>
                            <th>Bucket</th>
                            <th>Today</th>
                            <th>Vol20</th>
                            <th>Signals</th>
                            <th>Reason/Risk</th>
                        </tr>
                    </thead>
                    <tbody>{''.join(rows)}</tbody>
                </table>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    if section.key == STEADY_WINNER_SECTION_KEY:
        rows = [
            "<tr>"
            f"<td class='cpx-digest-rank'>#{item.rank or idx}</td>"
            f"<td><span class='cpx-digest-ticker'>{_html_text(item.ticker)}</span></td>"
            f"<td>{_badge_html(_format_pul(item.pul_score), _qbs_tone(item.pul_score))}</td>"
            f"<td>{_badge_html(item.bucket or item.label or '-', _signal_tone(item.bucket or item.label, section.key))}</td>"
            f"<td>{_badge_html(_format_float(item.chg_pct, 2, signed=True, suffix='%') + ' / 5D ' + _format_float(item.chg_5d, 2, signed=True, suffix='%'), _change_tone(item.chg_pct))}</td>"
            f"<td>{_badge_html(_format_ratio(item.volume_ratio_20), _volume_tone(item.volume_ratio_20))}</td>"
            f"<td>{_badge_html(item.entry_type or '-', 'info' if item.entry_type else 'muted')}</td>"
            f"<td><div class='cpx-digest-tags'>{_candidate_tags_html(item)}</div></td>"
            "</tr>"
            for idx, item in enumerate(section.items, start=1)
        ]
        st.markdown(
            f"""
            <div class='cpx-digest-table-wrap'>
                <table class='cpx-digest-table'>
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Ticker</th>
                            <th>PUL</th>
                            <th>Bucket</th>
                            <th>Change/5D</th>
                            <th>Vol20</th>
                            <th>Entry Type</th>
                            <th>Reason/Risk</th>
                        </tr>
                    </thead>
                    <tbody>{''.join(rows)}</tbody>
                </table>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    if section.key == EARLY_REVERSAL_KEY:
        rows = [
            "<tr>"
            f"<td class='cpx-digest-rank'>#{item.rank or idx}</td>"
            f"<td><span class='cpx-digest-ticker'>{_html_text(item.ticker)}</span></td>"
            f"<td>{_badge_html(_format_ers(item.early_reversal_score), _qbs_tone(item.early_reversal_score))}</td>"
            f"<td>{_badge_html(item.reversal_phase or '-', _signal_tone(item.reversal_phase, section.key))}</td>"
            f"<td>{_badge_html(item.reversal_type or '-', 'info' if item.reversal_type else 'muted')}</td>"
            f"<td>{_badge_html(_format_float(item.chg_pct, 2, signed=True, suffix='%') + ' / 5D ' + _format_float(item.chg_5d, 2, signed=True, suffix='%'), _change_tone(item.chg_pct))}</td>"
            f"<td>{_badge_html(_format_ratio(item.volume_ratio_20), _volume_tone(item.volume_ratio_20))}</td>"
            f"<td>{_badge_html(item.entry_type or '-', 'info' if item.entry_type else 'muted')}</td>"
            f"<td><div class='cpx-digest-tags'>{_candidate_tags_html(item)}</div></td>"
            "</tr>"
            for idx, item in enumerate(section.items, start=1)
        ]
        st.markdown(
            f"""
            <div class='cpx-digest-table-wrap'>
                <table class='cpx-digest-table'>
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Ticker</th>
                            <th>ERS</th>
                            <th>Phase</th>
                            <th>Type</th>
                            <th>Change/5D</th>
                            <th>Vol20</th>
                            <th>Entry Type</th>
                            <th>Reason/Risk</th>
                        </tr>
                    </thead>
                    <tbody>{''.join(rows)}</tbody>
                </table>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    if section.key == HULL_BUY_TURN_KEY:
        rows = [
            "<tr>"
            f"<td class='cpx-digest-rank'>#{item.rank or idx}</td>"
            f"<td><span class='cpx-digest-ticker'>{_html_text(item.ticker)}</span></td>"
            f"<td>{_badge_html(_format_float(item.chg_pct, 2, signed=True, suffix='%') + ' / 5D ' + _format_float(item.chg_5d, 2, signed=True, suffix='%'), _change_tone(item.chg_pct))}</td>"
            f"<td class='cpx-digest-num'>{_html_text(_format_float(item.rsi, 1))}</td>"
            f"<td>{_badge_html(_format_ratio(item.volume_ratio_20), _volume_tone(item.volume_ratio_20))}</td>"
            f"<td>{_badge_html(_format_float(item.ma20_dist_pct, 1, signed=True, suffix='%'), _change_tone(item.ma20_dist_pct))}</td>"
            f"<td class='cpx-digest-num'>{_html_text(_format_float((item.source_flags or {}).get('rs_rank_vs_index'), 0))}</td>"
            f"<td><div class='cpx-digest-tags'>{_candidate_tags_html(item)}</div></td>"
            "</tr>"
            for idx, item in enumerate(section.items, start=1)
        ]
        st.markdown(
            f"""
            <div class='cpx-digest-table-wrap'>
                <table class='cpx-digest-table'>
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Ticker</th>
                            <th>Today/5D</th>
                            <th>RSI</th>
                            <th>Vol20</th>
                            <th>MA20</th>
                            <th>RS</th>
                            <th>Reason/Risk</th>
                        </tr>
                    </thead>
                    <tbody>{''.join(rows)}</tbody>
                </table>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    if section.key == "five_day_top":
        rows = [
            "<tr>"
            f"<td class='cpx-digest-rank'>#{item.rank or idx}</td>"
            f"<td><span class='cpx-digest-ticker'>{_html_text(item.ticker)}</span></td>"
            f"<td>{_badge_html(_format_float(item.chg_5d, 2, signed=True, suffix='%'), _change_tone(item.chg_5d))}</td>"
            f"<td class='cpx-digest-num'>{_html_text(_format_float(item.rsi, 1))}</td>"
            f"<td>{_badge_html(_format_ratio(item.volume_ratio_20), _volume_tone(item.volume_ratio_20))}</td>"
            f"<td>{_badge_html(_format_float(item.ma20_dist_pct, 1, signed=True, suffix='%'), _change_tone(item.ma20_dist_pct))}</td>"
            f"<td><div class='cpx-digest-tags'>{''.join(_badge_html(tag, _signal_tone(tag, section.key)) for tag in (_candidate_status_text(item).split('/') if _candidate_status_text(item) != '-' else ['-']))}</div></td>"
            "</tr>"
            for idx, item in enumerate(section.items, start=1)
        ]
        st.markdown(
            f"""
            <div class='cpx-digest-table-wrap'>
                <table class='cpx-digest-table'>
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>티커</th>
                            <th>5일 상승률</th>
                            <th>RSI</th>
                            <th>Vol20</th>
                            <th>MA20이격</th>
                            <th>상태</th>
                        </tr>
                    </thead>
                    <tbody>{''.join(rows)}</tbody>
                </table>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    rows: list[str] = []
    for idx, item in enumerate(section.items, start=1):
        rank = item.rank or idx
        change_text = " / ".join(
            part
            for part in [
                _format_float(item.chg_value, 2, signed=True),
                _format_float(item.chg_pct, 2, signed=True, suffix="%"),
            ]
            if part != "--"
        ) or "--"
        signal_label = _candidate_signal_label(item)
        rows.append(
            "<tr>"
            f"<td class='cpx-digest-rank'>#{rank}</td>"
            f"<td><span class='cpx-digest-ticker'>{_html_text(item.ticker)}</span></td>"
            f"<td class='cpx-digest-num'>{_html_text(_format_float(item.price, 2))}</td>"
            f"<td>{_badge_html(change_text, _change_tone(item.chg_pct))}</td>"
            f"<td>{_badge_html(_format_ratio(item.volume_ratio_20), _volume_tone(item.volume_ratio_20))}</td>"
            f"<td>{_badge_html(_format_qbs(item.qbs_score), _qbs_tone(item.qbs_score))}</td>"
            f"<td>{_badge_html(signal_label or section.title, _signal_tone(signal_label, section.key))}</td>"
            f"<td><div class='cpx-digest-tags'>{_candidate_tags_html(item)}</div></td>"
            "</tr>"
        )

    st.markdown(
        f"""
        <div class='cpx-digest-table-wrap'>
            <table class='cpx-digest-table'>
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Ticker</th>
                        <th>Price</th>
                        <th>Change</th>
                        <th>Volume</th>
                        <th>QBS</th>
                        <th>Signal</th>
                        <th>Reason</th>
                    </tr>
                </thead>
                <tbody>{''.join(rows)}</tbody>
            </table>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_telegram_message_board(
    payload: Mapping[str, Any],
    *,
    source: str,
    digest_result: Mapping[str, Any],
    on_select_ticker: Callable[[str], None],
) -> None:
    digest = telegram_digest_from_payload(payload)
    visible_sections = _visible_telegram_sections(digest)

    _render_telegram_digest_styles()
    _render_telegram_summary_card(digest, source=source, digest_result=digest_result)
    if digest_result.get("error") and source == "cache":
        st.caption(f"원격 갱신 실패로 마지막 성공 캐시를 표시 중입니다: {digest_result['error']}")

    _render_telegram_visual_board(digest, on_select_ticker=on_select_ticker)

    st.markdown(
        "<div class='cpx-board-action-label' style='margin-top:18px'>섹션별 상세</div>",
        unsafe_allow_html=True,
    )
    board_group_labels = {
        "decision": "[0] 오늘 의사결정 핵심",
        "startup9": "[1] Startup식 9개 강세확인 Top 20",
        "technical": "[2] 기술적 매수시그널 클러스터",
        "aggressive": "[3] 다음 거래일 공격형 매수 후보 8-PART",
        "board": "[4] 매매 유형별 후보 보드",
        "reference": "[5] 참고 랭킹",
    }
    last_group = ""
    for idx, section in enumerate(visible_sections):
        ticker_list = [item.ticker for item in section.items if item.ticker]
        if section.key in QBS_DISPLAY_NUMBERS:
            display_number = QBS_DISPLAY_NUMBERS[section.key]
            group_key = "decision"
        elif section.key == STARTUP9_CONFIRM_KEY:
            display_number = STARTUP9_CONFIRM_DISPLAY_NUMBER
            group_key = "startup9"
        elif section.key == TECHNICAL_BUY_CLUSTER_KEY:
            display_number = TECHNICAL_BUY_DISPLAY_NUMBER
            group_key = "technical"
        elif section.key == STEADY_WINNER_SECTION_KEY:
            display_number = STEADY_WINNER_DISPLAY_NUMBER
            group_key = "decision"
        elif section.key == EARLY_REVERSAL_KEY:
            display_number = EARLY_REVERSAL_DISPLAY_NUMBER
            group_key = "decision"
        elif section.key == HULL_BUY_TURN_KEY:
            display_number = HULL_BUY_TURN_DISPLAY_NUMBER
            group_key = "decision"
        elif section.key in AGGRESSIVE_SECTION_KEY_SET:
            display_number = f"PART {AGGRESSIVE_NEXT_DAY_SECTION_KEYS.index(section.key) + 1}"
            group_key = "aggressive"
        elif section.key == "five_day_top":
            display_number = FIVE_DAY_TOP_DISPLAY_NUMBER
            group_key = "reference"
        else:
            display_number = BOARD_DISPLAY_NUMBERS.get(section.key, "-")
            group_key = "board" if section.key in BOARD_TYPE_SECTION_KEYS else ""
        if group_key and group_key != last_group:
            st.markdown(
                f"<div class='cpx-board-action-label' style='margin-top:14px'>{_html_text(board_group_labels.get(group_key, group_key))}</div>",
                unsafe_allow_html=True,
            )
            last_group = group_key
        expander_label = f"{display_number}. {section.title or section.key or f'Section {idx + 1}'}"
        with st.expander(expander_label, expanded=idx < 3):
            _render_telegram_section_table(section)
            if ticker_list:
                _render_ticker_button_row(
                    ticker_list,
                    key_prefix=f"home_telegram_{section.key or idx}",
                    on_select_ticker=on_select_ticker,
                    columns=5,
                )


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
    source_badge, source_tone = _digest_source_badge(source)

    render_section_heading(
        "Telegram Digest Dashboard",
        "실제 발송되는 텔레그램 메시지 구조는 유지하고, 후보 비교와 개별 분석 진입을 홈 화면에서 바로 처리합니다.",
        badges=[
            ("홈", "accent"),
            (source_badge, source_tone),
            ("Digest TTL 900s", "muted"),
        ],
        eyebrow="Telegram Digest",
        tight=True,
    )

    if not payload:
        _render_telegram_digest_styles()
        _render_digest_html(
            "<div class='cpx-home-empty'>"
            "<strong>종목판을 아직 불러오지 못했습니다.</strong>"
            f"<span>{_html_text(str(digest_result.get('error') or '원격 digest가 아직 발행되지 않았습니다.'))}</span>"
            "</div>"
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
    st.markdown("<div class='cpx-home-recent-shell'>", unsafe_allow_html=True)
    if recent:
        _render_ticker_button_row(recent[:10], key_prefix="home_recent", on_select_ticker=on_select_ticker)
    else:
        st.caption("아직 최근 분석 이력이 없습니다.")
    st.markdown("</div>", unsafe_allow_html=True)

    if ti := st.chat_input(chat_input_placeholder):
        parsed = parse_ticker_input(ti)
        if parsed:
            on_select_ticker(parsed[0])
