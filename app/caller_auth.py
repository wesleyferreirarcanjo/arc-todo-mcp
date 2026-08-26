from __future__ import annotations

import contextvars
import threading
from collections.abc import Mapping
from contextlib import contextmanager
from typing import Any, Iterator

_caller_token: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "caller_token", default=None
)

_session_tokens: dict[str, str] = {}
_session_lock = threading.Lock()

SESSION_ID_HEADER = "mcp-session-id"
ALT_TOKEN_HEADERS = ("x-arc-todo-token", "x-api-key")

MISSING_CALLER_TOKEN_MESSAGE = (
    "Missing Authorization bearer token. "
    "Cursor IDE: set headers.Authorization to Bearer <jwt> in mcp.json. "
    "Grok/cloud HTTP connectors drop Authorization and do not reuse MCP sessions — "
    "pass arc_todo_token on EVERY tenant tool call (same JWT as the "
    "arc_todo_token secret). set_caller_auth only proves the JWT; it does not "
    "stick across calls. A secret-card file is not sent as a header."
)


def get_caller_token() -> str | None:
    return _caller_token.get()


def require_caller_token() -> str:
    token = get_caller_token()
    if not token:
        raise ValueError(MISSING_CALLER_TOKEN_MESSAGE)
    return token


@contextmanager
def caller_token_scope(token: str | None) -> Iterator[None]:
    reset_token = _caller_token.set(token)
    try:
        yield
    finally:
        _caller_token.reset(reset_token)


def extract_bearer_from_authorization(authorization: str | None) -> str | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    return token or None


def normalize_caller_token(raw: Any) -> str | None:
    if raw is None:
        return None
    token = str(raw).strip().strip('"').strip("'")
    if not token:
        return None
    bearer = extract_bearer_from_authorization(token)
    if bearer:
        return bearer
    return token


def extract_token_from_headers(headers: Mapping[str, str] | None) -> str | None:
    if headers is None:
        return None
    get = headers.get
    token = extract_bearer_from_authorization(get("authorization"))
    if token:
        return token
    for key in ALT_TOKEN_HEADERS:
        raw = get(key)
        if not raw:
            continue
        token = normalize_caller_token(raw)
        if token:
            return token
    return None


def get_session_id(headers: Mapping[str, str] | None) -> str | None:
    if headers is None:
        return None
    session_id = headers.get(SESSION_ID_HEADER)
    if session_id is None:
        return None
    session_id = session_id.strip()
    return session_id or None


def get_session_token(session_id: str | None) -> str | None:
    if not session_id:
        return None
    with _session_lock:
        return _session_tokens.get(session_id)


def remember_session_token(session_id: str | None, token: str | None) -> None:
    if not session_id or not token:
        return
    with _session_lock:
        _session_tokens[session_id] = token


def reset_session_tokens() -> None:
    with _session_lock:
        _session_tokens.clear()


def inline_token_from_arguments(arguments: Mapping[str, Any] | None) -> str | None:
    if not arguments:
        return None
    return normalize_caller_token(
        arguments.get("arc_todo_token")
    ) or normalize_caller_token(arguments.get("token"))


def resolve_caller_token(
    headers: Mapping[str, str] | None,
    *,
    tool_name: str | None = None,
    arguments: Mapping[str, Any] | None = None,
) -> str | None:
    del tool_name
    session_id = get_session_id(headers)
    return (
        inline_token_from_arguments(arguments)
        or extract_token_from_headers(headers)
        or get_session_token(session_id)
    )
