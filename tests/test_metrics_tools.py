import json

import pytest
import respx
from httpx import Response

from app.arc_todo_client import arc_todo_client
from app.tools.metrics import (
    MetricsAppMetricsInput,
    MetricsAppSeriesInput,
    MetricsCreateAgentTokenInput,
    MetricsCreateAppTokenInput,
    MetricsListAgentTokensInput,
    MetricsListAppTokensInput,
    MetricsListServersInput,
    MetricsResourceSeriesInput,
    MetricsRevokeAgentTokenInput,
    MetricsRevokeAppTokenInput,
    MetricsServerResourcesInput,
    MetricsServerSeriesInput,
    metrics_app_metrics,
    metrics_app_series,
    metrics_create_agent_token,
    metrics_create_app_token,
    metrics_list_agent_tokens,
    metrics_list_app_tokens,
    metrics_list_servers,
    metrics_resource_series,
    metrics_revoke_agent_token,
    metrics_revoke_app_token,
    metrics_server_resources,
    metrics_server_series,
)

SERVER_ID = "11111111-1111-4111-8111-111111111111"
TOKEN_ID = "33333333-3333-4333-8333-333333333333"


def _point_client(monkeypatch):
    monkeypatch.setenv("ARC_TODO_API_BASE_URL", "http://api.test")
    monkeypatch.setenv("ARC_TODO_ACCESS_TOKEN", "service-token")
    arc_todo_client._base_url = "http://api.test"
    arc_todo_client._token = "service-token"


@pytest.mark.asyncio
@respx.mock
async def test_list_servers(monkeypatch, caller_auth):
    _point_client(monkeypatch)
    route = respx.get("http://api.test/metrics/servers").mock(
        return_value=Response(200, json=[{"id": SERVER_ID, "name": "arc-lab-1"}])
    )

    result = await metrics_list_servers(MetricsListServersInput())

    assert route.called
    assert route.calls[0].request.headers["X-Arc-Source"] == "mcp"
    assert "arc-lab-1" in result


@pytest.mark.asyncio
@respx.mock
async def test_server_resources_and_series_pass_window(monkeypatch, caller_auth):
    _point_client(monkeypatch)
    res_route = respx.get(
        f"http://api.test/metrics/servers/{SERVER_ID}/resources"
    ).mock(return_value=Response(200, json=[]))
    series_route = respx.get(
        f"http://api.test/metrics/servers/{SERVER_ID}/series"
    ).mock(return_value=Response(200, json={"points": []}))

    await metrics_server_resources(
        MetricsServerResourcesInput(server_id=SERVER_ID, window="7d")
    )
    await metrics_server_series(
        MetricsServerSeriesInput(server_id=SERVER_ID, window="1h")
    )

    assert "window=7d" in str(res_route.calls[0].request.url)
    assert "window=1h" in str(series_route.calls[0].request.url)


@pytest.mark.asyncio
@respx.mock
async def test_resource_series_uses_resource_id(monkeypatch, caller_auth):
    _point_client(monkeypatch)
    route = respx.get("http://api.test/metrics/resources/42/series").mock(
        return_value=Response(200, json={"points": []})
    )

    await metrics_resource_series(
        MetricsResourceSeriesInput(resource_id=42, window="30d")
    )

    assert "window=30d" in str(route.calls[0].request.url)


@pytest.mark.asyncio
@respx.mock
async def test_token_tools(monkeypatch, caller_auth):
    _point_client(monkeypatch)
    list_route = respx.get("http://api.test/metrics/agent-tokens").mock(
        return_value=Response(200, json=[])
    )
    create_route = respx.post("http://api.test/metrics/agent-tokens").mock(
        return_value=Response(201, json={"id": TOKEN_ID, "token": "amt_once"})
    )

    await metrics_list_agent_tokens(MetricsListAgentTokensInput())
    assert list_route.called

    result = await metrics_create_agent_token(
        MetricsCreateAgentTokenInput(server_name="arc-lab-1")
    )
    assert json.loads(create_route.calls[0].request.content) == {
        "serverName": "arc-lab-1"
    }
    assert "amt_once" in result


@pytest.mark.asyncio
@respx.mock
async def test_revoke_requires_confirm(monkeypatch, caller_auth):
    _point_client(monkeypatch)
    route = respx.delete(
        f"http://api.test/metrics/agent-tokens/{TOKEN_ID}"
    ).mock(return_value=Response(204))

    refused = await metrics_revoke_agent_token(
        MetricsRevokeAgentTokenInput(token_id=TOKEN_ID, confirm=False)
    )
    assert "Refused" in refused
    assert not route.called

    result = await metrics_revoke_agent_token(
        MetricsRevokeAgentTokenInput(token_id=TOKEN_ID, confirm=True)
    )
    assert route.called
    assert "revoked" in result


@pytest.mark.asyncio
@respx.mock
async def test_app_token_tools(monkeypatch, caller_auth):
    _point_client(monkeypatch)
    list_route = respx.get("http://api.test/metrics/app-tokens").mock(
        return_value=Response(200, json=[])
    )
    create_route = respx.post("http://api.test/metrics/app-tokens").mock(
        return_value=Response(201, json={"id": TOKEN_ID, "token": "aap_once"})
    )
    revoke_route = respx.delete(
        f"http://api.test/metrics/app-tokens/{TOKEN_ID}"
    ).mock(return_value=Response(204))

    await metrics_list_app_tokens(MetricsListAppTokensInput())
    assert list_route.called

    result = await metrics_create_app_token(
        MetricsCreateAppTokenInput(app="arccloud:my-app")
    )
    assert json.loads(create_route.calls[0].request.content) == {
        "app": "arccloud:my-app"
    }
    assert "aap_once" in result

    refused = await metrics_revoke_app_token(
        MetricsRevokeAppTokenInput(token_id=TOKEN_ID, confirm=False)
    )
    assert "Refused" in refused
    assert not revoke_route.called

    await metrics_revoke_app_token(
        MetricsRevokeAppTokenInput(token_id=TOKEN_ID, confirm=True)
    )
    assert revoke_route.called


@pytest.mark.asyncio
@respx.mock
async def test_app_metrics_and_series(monkeypatch, caller_auth):
    _point_client(monkeypatch)
    metrics_route = respx.get("http://api.test/metrics/app-metrics").mock(
        return_value=Response(200, json=[])
    )
    series_route = respx.get("http://api.test/metrics/app-series").mock(
        return_value=Response(200, json={"series": []})
    )

    await metrics_app_metrics(MetricsAppMetricsInput(app="arccloud:my-app"))
    url = str(metrics_route.calls[0].request.url)
    assert "app=arccloud%3Amy-app" in url

    await metrics_app_series(
        MetricsAppSeriesInput(
            app="arccloud:my-app", metric="requests_total", window="1h"
        )
    )
    url = str(series_route.calls[0].request.url)
    assert "metric=requests_total" in url
    assert "window=1h" in url
