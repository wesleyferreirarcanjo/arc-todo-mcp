from __future__ import annotations

import contextvars
from contextlib import contextmanager
from typing import Iterator

_caller_token: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "caller_token", default=None
)


def get_caller_token() -> str | None:
    return _caller_token.get()


def require_caller_token() -> str:
    token = get_caller_token()
    if not token:
        raise ValueError(
            "Missing Authorization bearer token. "
            "Set headers.Authorization to Bearer <your Arc Todo JWT> in mcp.json."
        )
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
