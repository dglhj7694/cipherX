from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any

import requests

from .contracts import TelegramDigest


def write_local_digest_artifacts(
    digest: TelegramDigest,
    *,
    out_dir: Path,
    relative_path: str = "post_close",
) -> dict[str, Path]:
    digest_dir = Path(out_dir) / "telegram_digest" / str(relative_path or "post_close").strip("/\\")
    runs_dir = digest_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    latest_path = digest_dir / "latest.json"
    versioned_path = runs_dir / f"{digest.run_stamp}.json"
    payload = json.dumps(digest.to_dict(), ensure_ascii=False, indent=2)
    versioned_path.write_text(payload, encoding="utf-8")
    latest_path.write_text(payload, encoding="utf-8")
    return {
        "latest_path": latest_path,
        "versioned_path": versioned_path,
    }


def _api_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "cipherX-telegram-digest-publisher",
    }


def _request_json(method: str, url: str, *, token: str, timeout: int = 20, **kwargs: Any) -> Any:
    response = requests.request(method, url, headers=_api_headers(token), timeout=timeout, **kwargs)
    response.raise_for_status()
    if response.content:
        return response.json()
    return {}


def _ensure_branch(repo_full_name: str, branch: str, token: str) -> None:
    ref_url = f"https://api.github.com/repos/{repo_full_name}/git/ref/heads/{branch}"
    response = requests.get(ref_url, headers=_api_headers(token), timeout=20)
    if response.status_code == 200:
        return
    if response.status_code != 404:
        response.raise_for_status()

    repo_url = f"https://api.github.com/repos/{repo_full_name}"
    repo_payload = _request_json("GET", repo_url, token=token)
    default_branch = str(repo_payload.get("default_branch") or "").strip()
    if not default_branch:
        raise RuntimeError(f"Could not resolve default branch for {repo_full_name}")
    base_ref_url = f"https://api.github.com/repos/{repo_full_name}/git/ref/heads/{default_branch}"
    base_ref_payload = _request_json("GET", base_ref_url, token=token)
    base_sha = str(dict(base_ref_payload.get("object") or {}).get("sha") or "").strip()
    if not base_sha:
        raise RuntimeError(f"Could not resolve base SHA for {repo_full_name}:{default_branch}")
    create_url = f"https://api.github.com/repos/{repo_full_name}/git/refs"
    _request_json(
        "POST",
        create_url,
        token=token,
        json={"ref": f"refs/heads/{branch}", "sha": base_sha},
    )


def _upsert_file(repo_full_name: str, branch: str, path: str, content: str, token: str, commit_message: str) -> None:
    contents_url = f"https://api.github.com/repos/{repo_full_name}/contents/{path}"
    response = requests.get(contents_url, headers=_api_headers(token), timeout=20, params={"ref": branch})
    sha = ""
    if response.status_code == 200:
        sha = str(response.json().get("sha") or "").strip()
    elif response.status_code != 404:
        response.raise_for_status()

    body: dict[str, Any] = {
        "message": commit_message,
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": branch,
    }
    if sha:
        body["sha"] = sha

    put_response = requests.put(contents_url, headers=_api_headers(token), timeout=20, json=body)
    put_response.raise_for_status()


def publish_digest_to_github(
    digest: TelegramDigest,
    *,
    repo_full_name: str,
    branch: str,
    base_path: str,
    token: str,
) -> dict[str, Any]:
    clean_base_path = str(base_path or "post_close").strip("/\\")
    if not repo_full_name or not branch or not token:
        raise RuntimeError("repo_full_name, branch, and token are required")

    _ensure_branch(repo_full_name, branch, token)
    payload = json.dumps(digest.to_dict(), ensure_ascii=False, indent=2)
    latest_remote_path = f"{clean_base_path}/latest.json"
    versioned_remote_path = f"{clean_base_path}/runs/{digest.run_stamp}.json"
    _upsert_file(
        repo_full_name,
        branch,
        latest_remote_path,
        payload,
        token,
        commit_message=f"Publish telegram digest latest for {digest.run_stamp}",
    )
    _upsert_file(
        repo_full_name,
        branch,
        versioned_remote_path,
        payload,
        token,
        commit_message=f"Publish telegram digest run {digest.run_stamp}",
    )
    return {
        "ok": True,
        "repo_full_name": repo_full_name,
        "branch": branch,
        "latest_remote_path": latest_remote_path,
        "versioned_remote_path": versioned_remote_path,
    }


def publish_digest_if_configured(
    digest: TelegramDigest,
    *,
    enabled: bool = True,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    environment = dict(os.environ if env is None else env)
    token = str(environment.get("DIGEST_PUBLISH_TOKEN") or environment.get("GITHUB_TOKEN") or environment.get("GH_TOKEN") or "").strip()
    repo_full_name = str(environment.get("DIGEST_PUBLISH_REPO") or environment.get("GITHUB_REPOSITORY") or "").strip()
    branch = str(environment.get("DIGEST_PUBLISH_BRANCH") or "telegram-digest").strip()
    base_path = str(environment.get("DIGEST_PUBLISH_PATH") or "post_close").strip()

    if not enabled:
        return {"ok": False, "skipped": True, "reason": "disabled"}
    if not token:
        return {"ok": False, "skipped": True, "reason": "missing_token"}
    if not repo_full_name:
        return {"ok": False, "skipped": True, "reason": "missing_repo"}

    return publish_digest_to_github(
        digest,
        repo_full_name=repo_full_name,
        branch=branch,
        base_path=base_path,
        token=token,
    )
