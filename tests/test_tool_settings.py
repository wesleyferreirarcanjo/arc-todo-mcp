import pytest
import respx
from httpx import Response

from app.tool_settings import fetch_enabled_tool_keys


@pytest.mark.asyncio
@respx.mock
async def test_fetch_enabled_tool_keys_with_password(monkeypatch):
    monkeypatch.setenv("ARC_TODO_API_BASE_URL", "http://api.test")
    monkeypatch.setenv("ARC_TODO_USERNAME", "admin")
    monkeypatch.setenv("ARC_TODO_PASSWORD", "secret")
    monkeypatch.delenv("ARC_TODO_ACCESS_TOKEN", raising=False)

    respx.post("http://api.test/auth/login").mock(
        return_value=Response(200, json={"access_token": "token-123"})
    )
    respx.get("http://api.test/mcp-tools/enabled").mock(
        return_value=Response(200, json={"keys": ["list_tasks", "get_task"]})
    )

    keys = await fetch_enabled_tool_keys()
    assert keys == {"list_tasks", "get_task"}


@pytest.mark.asyncio
@respx.mock
async def test_fetch_enabled_tool_keys_with_access_token(monkeypatch):
    monkeypatch.setenv("ARC_TODO_API_BASE_URL", "http://api.test")
    monkeypatch.setenv("ARC_TODO_ACCESS_TOKEN", "token-abc")
    monkeypatch.delenv("ARC_TODO_USERNAME", raising=False)
    monkeypatch.delenv("ARC_TODO_PASSWORD", raising=False)

    route = respx.get("http://api.test/mcp-tools/enabled").mock(
        return_value=Response(200, json={"keys": ["check_arc_todo_api_health"]})
    )

    keys = await fetch_enabled_tool_keys()
    assert keys == {"check_arc_todo_api_health"}
    assert route.calls[0].request.headers["Authorization"] == "Bearer token-abc"
