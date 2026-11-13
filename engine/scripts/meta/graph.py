"""Shared Meta Graph API helpers for launch.py and health.py.

Credentials come only from the environment (or the repo-root .env through
utils.get_env). Every error message passes through redact() so a token never
reaches the terminal, a log or a state file.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from utils import get_env  # noqa: E402

GRAPH_VERSION = "v25.0"
GRAPH_URL = f"https://graph.facebook.com/{GRAPH_VERSION}"

# Codes Meta uses for rate limits; a run that hits one stops with state saved.
RATE_LIMIT_CODES = {4, 17, 32, 613, 80004}

_TOKEN_PATTERNS = [
    (re.compile(r"access_token=[^&\s\"']+", re.I), "access_token=[redacted]"),
    (re.compile(r"EAA[A-Za-z0-9]{10,}"), "[redacted-token]"),
]


def redact(text: object, token: str | None = None) -> str:
    out = str(text)
    if token:
        out = out.replace(token, "[redacted-token]")
    for pattern, repl in _TOKEN_PATTERNS:
        out = pattern.sub(repl, out)
    return out


class GraphError(Exception):
    def __init__(self, message: str, code: int | None = None):
        super().__init__(message)
        self.code = code

    @property
    def rate_limited(self) -> bool:
        return self.code in RATE_LIMIT_CODES


def ad_account_id(raw: str) -> str:
    raw = raw.strip()
    return raw if raw.startswith("act_") else f"act_{raw}"


def credentials(required: tuple[str, ...]) -> dict[str, str]:
    """Read META_* settings. Exits listing every missing required name, never values."""
    names = ("META_ACCESS_TOKEN", "META_AD_ACCOUNT_ID", "META_PAGE_ID", "META_INSTAGRAM_ACTOR_ID")
    values = {name: (get_env(name) or "").strip() for name in names}
    missing = [name for name in required if not values.get(name)]
    if missing:
        raise SystemExit(f"Error: missing {', '.join(missing)} (set in the environment or the repo-root .env)")
    if values["META_AD_ACCOUNT_ID"]:
        values["META_AD_ACCOUNT_ID"] = ad_account_id(values["META_AD_ACCOUNT_ID"])
    return values


def credential_status() -> dict[str, str]:
    """'set' or 'missing' per setting, for dry runs. Never returns a value."""
    names = ("META_ACCESS_TOKEN", "META_AD_ACCOUNT_ID", "META_PAGE_ID", "META_INSTAGRAM_ACTOR_ID")
    return {name: "set" if get_env(name) else "missing" for name in names}


def _encode(value: object) -> str:
    return value if isinstance(value, str) else json.dumps(value)


class Graph:
    def __init__(self, token: str, timeout: float = 120):
        self.token = token
        self.client = httpx.Client(timeout=timeout)

    def _url(self, path: str) -> str:
        return path if path.startswith("http") else f"{GRAPH_URL}/{path.lstrip('/')}"

    def _check(self, method: str, path: str, response: httpx.Response) -> dict:
        where = path.split("?")[0].replace(GRAPH_URL, "")
        try:
            data = response.json()
        except ValueError:
            raise GraphError(redact(f"{method} {where}: HTTP {response.status_code} {response.text[:300]}", self.token)) from None
        error = data.get("error") if isinstance(data, dict) else None
        if error:
            extra = " | ".join(
                str(x)
                for x in (
                    error.get("error_user_title"),
                    error.get("error_user_msg"),
                    error.get("error_subcode") and f"sub={error['error_subcode']}",
                )
                if x
            )
            message = f"{method} {where}: {error.get('message')} (code {error.get('code')}{'; ' + extra if extra else ''})"
            raise GraphError(redact(message, self.token), error.get("code"))
        return data

    def get(self, path: str, **params: object) -> dict:
        query = {k: _encode(v) for k, v in params.items()}
        if not path.startswith("http"):
            query["access_token"] = self.token
        try:
            response = self.client.get(self._url(path), params=query)
        except httpx.HTTPError as exc:
            raise GraphError(redact(f"GET {path.split('?')[0]}: {exc}", self.token)) from None
        return self._check("GET", path, response)

    def paged(self, path: str, partial_ok: bool = False, **params: object) -> list[dict]:
        """Follow paging. With partial_ok, an error on a later page keeps what was read and warns."""
        out: list[dict] = []
        page = self.get(path, **params)
        while True:
            out += page.get("data", [])
            nxt = (page.get("paging") or {}).get("next")
            if not nxt:
                return out
            try:
                page = self.get(nxt)
            except GraphError as exc:
                if not partial_ok:
                    raise
                print(f"warning: stopped paging {path} early ({exc}); older rows missing", file=sys.stderr)
                return out

    def post(self, path: str, data: dict[str, object], files: dict | None = None) -> dict:
        body = {k: _encode(v) for k, v in data.items() if v is not None}
        body["access_token"] = self.token
        try:
            response = self.client.post(self._url(path), data=body, files=files)
        except httpx.HTTPError as exc:
            raise GraphError(redact(f"POST {path}: {exc}", self.token)) from None
        return self._check("POST", path, response)
