import json

import pytest
import respx
from httpx import Response

from app.arc_todo_client import arc_todo_client
from app.tools.observer import (
    ObserverCreateAppTokenInput,
    ObserverCreateTokenInput,
    ObserverExplainInput,
    ObserverListAppTokensInput,
    ObserverListTokensInput,
    ObserverRevokeAppTokenInput,
    ObserverRevokeTokenInput,
    ObserverSearchInput,
    ObserverTailInput,
    observer_create_app_token,
    observer_create_token,
    observer_explain,
    observer_list_app_tokens,
    observer_list_tokens,
    observer_revoke_app_token,
    observer_revoke_token,
    observer_search,
    observer_tail,
)

TOKEN_ID = "33333333-3333-4333-8333-333333333333"


def _point_client(monkeypatch):
    monkeypatch.setenv("ARC_TODO_API_BASE_URL", "http://api.test")
    monkeypatch.setenv("ARC_TODO_ACCESS_TOKEN", "service-token")
    arc_todo_client._base_url = "http://api.test"
    arc_todo_client._token = "service-token"


@pytest.mark.asyncio
@respx.mock
async def test_search_builds_query_and_sends_mcp_header(monkeypatch, caller_auth):
    _point_client(monkeypatch)
    route = respx.get("http://api.test/observer/logs").mock(
        return_value=Response(200, json={"lines": [], "has_more": False})
    )

    result = await observer_search(
        ObserverSearchInput(
            server="arc-lab-1",
            app="myapp",
            level="error",
            q="boom",
            from_ms=1759990000000,
            limit=50,
        )
    )

    assert route.called
    url = str(route.calls[0].request.url)
    assert "server=arc-lab-1" in url
    assert "app=myapp" in url
    assert "level=error" in url
    assert "q=boom" in url
    assert "fromMs=1759990000000" in url
    assert "limit=50" in url
    assert route.calls[0].request.headers["X-Arc-Source"] == "mcp"
    assert "has_more" in result


@pytest.mark.asyncio
@respx.mock
async def test_tail_passes_after_cursor(monkeypatch, caller_auth):
    _point_client(monkeypatch)
    route = respx.get("http://api.test/observer/tail").mock(
        return_value=Response(200, json={"lines": [], "has_more": False})
    )

    await observer_tail(
        ObserverTailInput(server="arc-lab-1", after_ms=1760000000000, limit=100)
    )

    url = str(route.calls[0].request.url)
    assert "afterMs=1760000000000" in url
    assert "server=arc-lab-1" in url


@pytest.mark.asyncio
@respx.mock
async def test_explain_posts_scoped_body(monkeypatch, caller_auth):
    _point_client(monkeypatch)
    route = respx.post("http://api.test/observer/explain").mock(
        return_value=Response(
            200,
            json={
                "explanation": "OOM killer restarted the container.",
                "usedTools": [],
                "linesUsed": 12,
                "fromMs": 1,
                "toMs": 2,
            },
        )
    )

    result = await observer_explain(
        ObserverExplainInput(server_id=TOKEN_ID, app="myapp", minutes=30)
    )

    body = json.loads(route.calls[0].request.content)
    assert body == {"serverId": TOKEN_ID, "app": "myapp", "minutes": 30}
    assert "OOM killer" in result


@pytest.mark.asyncio
@respx.mock
async def test_token_tools(monkeypatch, caller_auth):
    _point_client(monkeypatch)
    list_route = respx.get("http://api.test/observer/agent-tokens").mock(
        return_value=Response(200, json=[])
    )
    create_route = respx.post("http://api.test/observer/agent-tokens").mock(
        return_value=Response(201, json={"id": TOKEN_ID, "token": "aob_once"})
    )

    await observer_list_tokens(ObserverListTokensInput())
    assert list_route.called

    result = await observer_create_token(
        ObserverCreateTokenInput(server_name="arc-lab-1")
    )
    assert json.loads(create_route.calls[0].request.content) == {
        "serverName": "arc-lab-1"
    }
    assert "aob_once" in result


@pytest.mark.asyncio
@respx.mock
async def test_revoke_requires_confirm(monkeypatch, caller_auth):
    _point_client(monkeypatch)
    route = respx.delete(
        f"http://api.test/observer/agent-tokens/{TOKEN_ID}"
    ).mock(return_value=Response(204))

    refused = await observer_revoke_token(
        ObserverRevokeTokenInput(token_id=TOKEN_ID, confirm=False)
    )
    assert "Refused" in refused
    assert not route.called

    result = await observer_revoke_token(
        ObserverRevokeTokenInput(token_id=TOKEN_ID, confirm=True)
    )
    assert route.called
    assert "revoked" in result


@pytest.mark.asyncio
@respx.mock
async def test_app_token_tools(monkeypatch, caller_auth):
    _point_client(monkeypatch)
    list_route = respx.get("http://api.test/observer/app-tokens").mock(
        return_value=Response(200, json=[])
    )
    create_route = respx.post("http://api.test/observer/app-tokens").mock(
        return_value=Response(201, json={"id": TOKEN_ID, "token": "aap_once"})
    )
    revoke_route = respx.delete(
        f"http://api.test/observer/app-tokens/{TOKEN_ID}"
    ).mock(return_value=Response(204))

    await observer_list_app_tokens(ObserverListAppTokensInput())
    assert list_route.called

    result = await observer_create_app_token(
        ObserverCreateAppTokenInput(app="arccloud:my-app")
    )
    assert json.loads(create_route.calls[0].request.content) == {
        "app": "arccloud:my-app"
    }
    assert "aap_once" in result

    refused = await observer_revoke_app_token(
        ObserverRevokeAppTokenInput(token_id=TOKEN_ID, confirm=False)
    )
    assert "Refused" in refused
    assert not revoke_route.called

    await observer_revoke_app_token(
        ObserverRevokeAppTokenInput(token_id=TOKEN_ID, confirm=True)
    )
    assert revoke_route.called
