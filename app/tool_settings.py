from __future__ import annotations

import httpx

from app.config import get_settings


async def fetch_enabled_tool_keys() -> set[str]:
    """Load enabled MCP tool keys from arc-todo-api at startup."""
    settings = get_settings()
    base_url = settings.arc_todo_api_base_url.rstrip("/")
    token = settings.arc_todo_access_token
    if not token:
        raise RuntimeError(
            "Cannot load MCP tool settings without ARC_TODO_ACCESS_TOKEN"
        )
    headers = {"Authorization": f"Bearer {token}"}

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
