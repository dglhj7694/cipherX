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
from telegram_pipeline.early_reversal_ranker import EARLY_REVERSAL_KEY
from telegram_pipeline.formatters import QBS_DISPLAY_NUMBERS, STEADY_WINNER_DISPLAY_NUMBER, build_main_message
from telegram_pipeline.selectors import BOARD_MANDATORY_SECTION_KEYS, STEADY_WINNER_SECTION_KEY
from theme import FONT_STACK


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
        if section.key == STEADY_WINNER_SECTION_KEY:
            visible.append(section)
            continue
        if section.key == EARLY_REVERSAL_KEY:
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


def _section_tone(section_key: str) -> str:
    key = str(section_key or "")
    if key in {"qbs_chase_watch", "chase_risk"}:
        return "warning"
    if key in {"sell_turn", "sell_risk"}:
        return "negative"
    if key in {"qbs_pullback_wait", "pullback_reentry", "breakout_wait"}:
        return "info"
    if key == EARLY_REVERSAL_KEY:
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
    for flag in list(item.risk_flags or [])[:3]:
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
    defaults = {
        "qbs_buy_now": "buy_now",
        "qbs_chase_watch": "chase_watch",
        "qbs_pullback_wait": "pullback_wait",
        STEADY_WINNER_SECTION_KEY: "watchlist",
        EARLY_REVERSAL_KEY: "reversal_watch",
        "five_day_top": "momentum_watch",
    }
    return defaults.get(str(section_key or ""), "-")


def _board_section_label(section_key: str) -> str:
    labels = {
        "qbs_buy_now": "BUY_NOW",
        "qbs_chase_watch": "CHASE",
        "qbs_pullback_wait": "PULLBACK",
        STEADY_WINNER_SECTION_KEY: "STEADY",
        EARLY_REVERSAL_KEY: "REVERSAL",
        "five_day_top": "5D TOP",
    }
    return labels.get(str(section_key or ""), str(section_key or "-"))


def _board_bucket_label(item: TelegramCandidate, section_key: str) -> str:
    if section_key == "five_day_top":
        return _candidate_status_text(item)
    if section_key == EARLY_REVERSAL_KEY:
        return str(item.reversal_phase or item.bucket or item.label or "-").strip() or "-"
    return str(item.bucket or item.label or "-").strip() or "-"


def _board_score_text(item: TelegramCandidate, section_key: str) -> str:
    if section_key == STEADY_WINNER_SECTION_KEY:
        return _format_pul(item.pul_score)
    if section_key == EARLY_REVERSAL_KEY:
        return _format_ers(item.early_reversal_score)
    if section_key in QBS_DISPLAY_NUMBERS:
        return _format_qbs(item.qbs_score)
    return "--"


def _split_reason_parts(text: str) -> list[str]:
    normalized = str(text or "").replace("/", "+").replace(",", "+")
    return [part.strip() for part in normalized.split("+") if part.strip()]


def _board_risk_text(item: TelegramCandidate, section_key: str) -> str:
    parts: list[str] = []
    parts.extend(str(flag).strip() for flag in list(item.risk_flags or []) if str(flag or "").strip())
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
        "climax",
        "low_volume",
        "high_conflict",
        "sell",
        "gap",
        "thin",
        "overheat",
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
            metrics["entry"] = _first_text(metrics.get("entry"), item.entry_type)
            if section.key == STEADY_WINNER_SECTION_KEY and item.pul_score is not None:
                metrics["score"] = _first_text(metrics.get("score"), _format_pul(item.pul_score))
                metrics["score_value"] = _first_number(metrics.get("score_value"), item.pul_score)
            elif section.key == EARLY_REVERSAL_KEY and item.early_reversal_score is not None:
                metrics["score"] = _first_text(metrics.get("score"), _format_ers(item.early_reversal_score))
                metrics["score_value"] = _first_number(metrics.get("score_value"), item.early_reversal_score)
            elif section.key in QBS_DISPLAY_NUMBERS and item.qbs_score is not None:
                metrics["score"] = _first_text(metrics.get("score"), _format_qbs(item.qbs_score))
                metrics["score_value"] = _first_number(metrics.get("score_value"), item.qbs_score)
    return lookup


def _build_telegram_board_rows(
    digest: TelegramDigest,
    *,
    market_metric_lookup: Mapping[str, Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    board_section_keys = {*QBS_DISPLAY_NUMBERS.keys(), STEADY_WINNER_SECTION_KEY, EARLY_REVERSAL_KEY, "five_day_top"}
    metric_lookup = _collect_digest_metric_lookup(digest)
    market_lookup = {str(ticker or "").strip().upper(): dict(metrics or {}) for ticker, metrics in dict(market_metric_lookup or {}).items()}
    rows: list[dict[str, Any]] = []
    for section in _visible_telegram_sections(digest):
        if section.key not in board_section_keys:
            continue
        for idx, item in enumerate(section.items, start=1):
            ticker = str(item.ticker or "").strip().upper()
            fallback = metric_lookup.get(ticker, {})
            market_fallback = market_lookup.get(ticker, {})
            risk_text = _board_risk_text(item, section.key)
            row = {
                "rank": item.rank or idx,
                "ticker": item.ticker,
                "section_key": section.key,
                "section": _board_section_label(section.key),
                "bucket": _board_bucket_label(item, section.key),
                "price": _first_number(item.price, fallback.get("price"), market_fallback.get("price")),
                "today_pct": _first_number(_board_today_pct(item, section.key), fallback.get("today_pct"), market_fallback.get("today_pct")),
                "five_day_pct": _first_number(_board_five_day_pct(item, section.key), fallback.get("five_day_pct"), market_fallback.get("five_day_pct")),
                "one_month_pct": _first_number(
                    item.ret_1m_pct,
                    _candidate_source_number(item, "ret_1m_pct", "ret20_pct"),
                    fallback.get("one_month_pct"),
                    market_fallback.get("one_month_pct"),
                ),
                "one_year_pct": _first_number(
                    item.ret_1y_pct,
                    _candidate_source_number(item, "ret_1y_pct", "ret252_pct"),
                    fallback.get("one_year_pct"),
                    market_fallback.get("one_year_pct"),
                ),
                "high_pos_pct": _first_number(
                    item.high_pos_pct,
                    _candidate_source_number(item, "high_pos_pct", "drawdown_from_52w_high_pct"),
                    fallback.get("high_pos_pct"),
                    market_fallback.get("high_pos_pct"),
                ),
                "score": _first_text(_board_score_text(item, section.key), fallback.get("score")),
                "score_value": _first_number(
                    item.pul_score
                    if section.key == STEADY_WINNER_SECTION_KEY
                    else item.early_reversal_score
                    if section.key == EARLY_REVERSAL_KEY
                    else item.qbs_score,
                    fallback.get("score_value"),
                ),
                "rsi": _first_number(item.rsi, _candidate_source_number(item, "rsi", "RSI"), fallback.get("rsi"), market_fallback.get("rsi")),
                "vol20": _first_number(item.volume_ratio_20, fallback.get("vol20"), market_fallback.get("vol20")),
                "ma20": _first_number(
                    item.ma20_dist_pct,
                    _candidate_source_number(item, "ma20_dist_pct", "dist_sma20_pct"),
                    fallback.get("ma20"),
                    market_fallback.get("ma20"),
                ),
                "entry": _board_entry_text(item, section.key, fallback.get("entry")),
                "risk": risk_text,
                "risk_flags": list(item.risk_flags or []),
            }
            row["has_warning"] = _board_has_warning(row)
            rows.append(row)
    return rows


def _filter_telegram_board_rows(rows: list[dict[str, Any]], filter_key: str) -> list[dict[str, Any]]:
    if filter_key == "qbs":
        return [row for row in rows if str(row.get("section_key") or "") in QBS_DISPLAY_NUMBERS]
    if filter_key == "steady":
        return [row for row in rows if row.get("section_key") == STEADY_WINNER_SECTION_KEY]
    if filter_key == "reversal":
        return [row for row in rows if row.get("section_key") == EARLY_REVERSAL_KEY]
    if filter_key == "five_day":
        return [row for row in rows if row.get("section_key") == "five_day_top"]
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


def _board_missing_metric_tickers(rows: Iterable[Mapping[str, Any]]) -> list[str]:
    tickers: list[str] = []
    for row in rows:
        ticker = str(row.get("ticker") or "").strip().upper()
        if not ticker or ticker in tickers:
            continue
        if any(_optional_float(row.get(field)) is None for field in BOARD_REQUIRED_NUMERIC_FIELDS):
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


def _board_cell(text: Any, tone: str = "muted", *, strong: bool = False) -> str:
    if tone not in {"positive", "negative", "warning", "info", "muted", "accent"}:
        tone = "muted"
    class_name = "cpx-board-cell"
    if strong:
        class_name += " cpx-board-cell--strong"
    return f"<span class='{class_name}' data-tone='{tone}'>{_html_text(text)}</span>"


def _board_rows_html(rows: list[dict[str, Any]]) -> str:
    body_rows: list[str] = []
    for row in rows:
        section_key = str(row.get("section_key") or "")
        score_tone = _qbs_tone(row.get("score_value"))
        if section_key == STEADY_WINNER_SECTION_KEY:
            score_tone = _qbs_tone(row.get("score_value"))
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
        "all": "All",
        "qbs": "QBS",
        "steady": "Steady Winner",
        "reversal": "Reversal",
        "five_day": "5D Top",
        "risk": "Risk",
    }
    filter_key = st.radio(
        "Telegram board filter",
        options=list(filter_options),
        format_func=lambda key: filter_options.get(str(key), str(key)),
        horizontal=True,
        key="home_telegram_digest_board_filter",
        label_visibility="collapsed",
    )
    filtered_rows = _filter_telegram_board_rows(rows, str(filter_key))
    if not filtered_rows:
        st.markdown("<div class='cpx-digest-empty'>No board rows.</div>", unsafe_allow_html=True)
        return

    st.markdown(
        f"""
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
                        <th>PUL/QBS</th>
                        <th>RSI</th>
                        <th>Vol20</th>
                        <th>MA20</th>
                        <th>Entry</th>
                        <th>Risk</th>
                    </tr>
                </thead>
                <tbody>{_board_rows_html(filtered_rows)}</tbody>
            </table>
        </div>
        """,
        unsafe_allow_html=True,
    )
    board_tickers = _collect_recent_tickers(str(row.get("ticker") or "") for row in filtered_rows)
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
        table.cpx-board-table {{
            width: 100%;
            min-width: 1280px;
            border-collapse: separate;
            border-spacing: 0;
            font-family: {FONT_STACK};
            letter-spacing: 0;
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
        @media (max-width: 760px) {{
            .cpx-digest-metrics {{
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }}
            .cpx-digest-summary {{
                padding: 14px;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_telegram_summary_card(digest: TelegramDigest) -> None:
    metric_items = [
        ("시장일", digest.market_date or "--"),
        ("유니버스", f"{digest.universe_count:,}"),
        ("결과", f"{digest.result_count:,}"),
        ("제외", f"{digest.skip_count:,}"),
    ]
    metrics_html = "".join(
        f"<div class='cpx-digest-metric'><b>{_html_text(label)}</b><strong>{_html_text(value)}</strong></div>"
        for label, value in metric_items
    )
    badges_html = "".join(
        [
            _badge_html(digest.scan_label or digest.scan_mode or "post-close", "accent"),
            _badge_html(f"섹션 {len(_visible_telegram_sections(digest))}", "info"),
            _badge_html(f"생성 {digest.generated_at or digest.run_stamp or '--'}", "muted"),
        ]
    )
    st.markdown(
        f"""
        <div class='cpx-digest-summary'>
            <div class='cpx-digest-summary__top'>
                <div>
                    <div class='cpx-digest-eyebrow'>Telegram Message</div>
                    <div class='cpx-digest-title'>오늘 종목판</div>
                </div>
                <div class='cpx-digest-badges'>{badges_html}</div>
            </div>
            <div class='cpx-digest-metrics'>{metrics_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_telegram_section_table(section: TelegramSection) -> None:
    tone = _section_tone(section.key)
    meta_html = "".join(
        [
            _badge_html(f"{section.item_count}개", tone),
            _badge_html("랭킹" if section.ranked else "보드", "muted"),
        ]
    )
    if section.quality_floor:
        meta_html += f"<span class='cpx-digest-quality'>{_html_text(section.quality_floor)}</span>"
    st.markdown(f"<div class='cpx-digest-section-meta'>{meta_html}</div>", unsafe_allow_html=True)

    if not section.items:
        st.markdown("<div class='cpx-digest-empty'>해당 티커가 없습니다.</div>", unsafe_allow_html=True)
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
    _render_telegram_summary_card(digest)
    if digest_result.get("error") and source == "cache":
        st.caption(f"원격 갱신 실패로 마지막 성공 캐시를 표시 중입니다: {digest_result['error']}")

    _render_telegram_visual_board(digest, on_select_ticker=on_select_ticker)

    board_display_index = 1
    for idx, section in enumerate(visible_sections):
        ticker_list = [item.ticker for item in section.items if item.ticker]
        if section.key in QBS_DISPLAY_NUMBERS:
            display_number = QBS_DISPLAY_NUMBERS[section.key]
        elif section.key == STEADY_WINNER_SECTION_KEY:
            display_number = STEADY_WINNER_DISPLAY_NUMBER
        elif section.key == EARLY_REVERSAL_KEY:
            display_number = "0-4"
        else:
            display_number = str(board_display_index)
            board_display_index += 1
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
