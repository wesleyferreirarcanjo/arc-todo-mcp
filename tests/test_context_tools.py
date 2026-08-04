import pytest
import respx
from httpx import Response

from app.arc_todo_client import arc_todo_client
from app.tools.handlers import create_project
from app.tool_registry import CreateProjectInput


@pytest.mark.asyncio
@respx.mock
async def test_create_project_calls_api(monkeypatch, caller_auth):
    monkeypatch.setenv("ARC_TODO_API_BASE_URL", "http://api.test")
    monkeypatch.setenv("ARC_TODO_ACCESS_TOKEN", "token-abc")
    arc_todo_client._base_url = "http://api.test"
    arc_todo_client._token = "token-abc"

    org_id = "57df4a79-d87d-40e1-9fb0-2da29d8ebecf"
    route = respx.post(f"http://api.test/organizations/{org_id}/projects").mock(
        return_value=Response(
            201,
            json={
                "id": "d576e04d-f683-4b88-a374-0aab28a4be10",
                "organizationId": org_id,
                "name": "arc-todo",
                "description": None,
                "color": "#8778a3",
            },
        )
    )

    result = await create_project(
        CreateProjectInput(
            organization_id=org_id,
            name="arc-todo",
            color="#8778a3",
        )
    )

    assert route.called
    assert route.calls[0].request.headers["Authorization"] == "Bearer token-abc"
    assert '"name": "arc-todo"' in result
    assert '"color": "#8778a3"' in result
