from __future__ import annotations

import httpx

from app.config import get_settings


async def fetch_enabled_tool_keys() -> set[str]:
    """Load enabled MCP tool keys from arc-todo-api at startup."""
    settings = get_settings()
    base_url = settings.arc_todo_api_base_url.rstrip("/")
    headers: dict[str, str] = {}

    if settings.arc_todo_access_token:
        headers["Authorization"] = f"Bearer {settings.arc_todo_access_token}"
    elif settings.arc_todo_username and settings.arc_todo_password:
        async with httpx.AsyncClient(timeout=30.0) as client:
            login = await client.post(
                f"{base_url}/auth/login",
                json={
                    "username": settings.arc_todo_username,
                    "password": settings.arc_todo_password,
                },
            )
            login.raise_for_status()
            headers["Authorization"] = f"Bearer {login.json()['access_token']}"
    else:
        raise RuntimeError(
            "Cannot load MCP tool settings without ARC_TODO_ACCESS_TOKEN or "
            "ARC_TODO_USERNAME/ARC_TODO_PASSWORD"
        )

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{base_url}/mcp-tools/enabled",
            headers=headers,
        )
        response.raise_for_status()
        payload = response.json()
        keys = payload.get("keys", payload)
        if isinstance(keys, list):
            return set(keys)
        raise RuntimeError("Unexpected /mcp-tools/enabled response shape")
