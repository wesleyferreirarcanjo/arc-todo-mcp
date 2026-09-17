import json

import pytest
import respx
from httpx import Response

from app.arc_todo_client import ArcTodoApiError, arc_todo_client
from app.tools.handlers import (
    create_organization,
    create_project,
    delete_organization,
    update_organization,
    update_project,
)
from app.tool_registry import (
    CreateOrganizationInput,
    CreateProjectInput,
    GetOrganizationInput,
    UpdateOrganizationInput,
    UpdateProjectInput,
)

ORG_ID = "57df4a79-d87d-40e1-9fb0-2da29d8ebecf"
PROJECT_ID = "d576e04d-f683-4b88-a374-0aab28a4be10"
ACL_403 = {
    "statusCode": 403,
    "code": "ERR-ARC-ACL-01",
    "message": "This action is limited to administrators.",
}


def _point_client(monkeypatch):
    monkeypatch.setenv("ARC_TODO_API_BASE_URL", "http://api.test")
    monkeypatch.setenv("ARC_TODO_ACCESS_TOKEN", "token-abc")
    arc_todo_client._base_url = "http://api.test"
    arc_todo_client._token = "token-abc"


@pytest.mark.asyncio
@respx.mock
async def test_create_project_calls_api(monkeypatch, caller_auth):
    _point_client(monkeypatch)
    list_route = respx.get(f"http://api.test/organizations/{ORG_ID}/projects").mock(
        return_value=Response(200, json=[])
    )
    create_route = respx.post(
        f"http://api.test/organizations/{ORG_ID}/projects"
    ).mock(
        return_value=Response(
            201,
            json={
                "id": PROJECT_ID,
                "organizationId": ORG_ID,
                "name": "arc-todo",
                "description": None,
                "color": "#8778a3",
            },
        )
    )

    result = await create_project(
        CreateProjectInput(
            organization_id=ORG_ID,
            name="arc-todo",
            color="#8778a3",
        )
    )

    assert list_route.called
    assert create_route.called
    assert create_route.calls[0].request.headers["Authorization"] == "Bearer token-abc"
    assert '"name":"arc-todo"' in result
    assert '"color":"#8778a3"' in result


@pytest.mark.asyncio
@respx.mock
async def test_create_project_returns_existing_on_trimmed_name(monkeypatch, caller_auth):
    _point_client(monkeypatch)
    existing = {
        "id": PROJECT_ID,
        "organizationId": ORG_ID,
        "name": "arc-todo",
        "color": "#8778a3",
    }
    list_route = respx.get(f"http://api.test/organizations/{ORG_ID}/projects").mock(
        return_value=Response(200, json=[existing])
    )
    create_route = respx.post(f"http://api.test/organizations/{ORG_ID}/projects")

    result = await create_project(
        CreateProjectInput(organization_id=ORG_ID, name="  arc-todo  ")
    )

    assert list_route.called
    assert not create_route.called
    assert json.loads(result)["id"] == PROJECT_ID


@pytest.mark.asyncio
@respx.mock
async def test_create_organization_posts_when_missing(monkeypatch, caller_auth):
    _point_client(monkeypatch)
    list_route = respx.get("http://api.test/organizations").mock(
        return_value=Response(200, json=[])
    )
    create_route = respx.post("http://api.test/organizations").mock(
        return_value=Response(
            201,
            json={
                "id": ORG_ID,
                "name": "Throwaway",
                "slug": "throwaway",
                "color": "#737373",
            },
        )
    )

    result = await create_organization(
        CreateOrganizationInput(name="Throwaway", color="#737373")
    )

    assert list_route.called
    assert create_route.called
    body = json.loads(create_route.calls[0].request.content)
    assert body == {"name": "Throwaway", "color": "#737373"}
    assert json.loads(result)["id"] == ORG_ID


@pytest.mark.asyncio
@respx.mock
async def test_create_organization_returns_existing_on_trimmed_name(
    monkeypatch, caller_auth
):
    _point_client(monkeypatch)
    existing = {
        "id": ORG_ID,
        "name": "Throwaway",
        "slug": "throwaway",
        "color": "#737373",
    }
    list_route = respx.get("http://api.test/organizations").mock(
        return_value=Response(200, json=[existing])
    )
    create_route = respx.post("http://api.test/organizations")

    result = await create_organization(CreateOrganizationInput(name=" Throwaway "))

    assert list_route.called
    assert not create_route.called
    assert json.loads(result)["id"] == ORG_ID


@pytest.mark.asyncio
@respx.mock
async def test_update_organization_patches_name_and_color(monkeypatch, caller_auth):
    _point_client(monkeypatch)
    route = respx.patch(f"http://api.test/organizations/{ORG_ID}").mock(
        return_value=Response(
            200,
            json={
                "id": ORG_ID,
                "name": "Renamed",
                "slug": "throwaway",
                "color": "#111111",
            },
        )
    )

    result = await update_organization(
        UpdateOrganizationInput(
            organization_id=ORG_ID,
            name="Renamed",
            color="#111111",
        )
    )

    assert route.called
    body = json.loads(route.calls[0].request.content)
    assert body == {"name": "Renamed", "color": "#111111"}
    assert '"name":"Renamed"' in result


@pytest.mark.asyncio
@respx.mock
async def test_delete_organization_calls_api(monkeypatch, caller_auth):
    _point_client(monkeypatch)
    route = respx.delete(f"http://api.test/organizations/{ORG_ID}").mock(
        return_value=Response(204)
    )

    result = await delete_organization(GetOrganizationInput(organization_id=ORG_ID))

    assert route.called
    assert result == '{"deleted": true}'


@pytest.mark.asyncio
@respx.mock
async def test_update_project_patches_fields(monkeypatch, caller_auth):
    _point_client(monkeypatch)
    route = respx.patch(
        f"http://api.test/organizations/{ORG_ID}/projects/{PROJECT_ID}"
    ).mock(
        return_value=Response(
            200,
            json={
                "id": PROJECT_ID,
                "organizationId": ORG_ID,
                "name": "Renamed project",
                "description": "Notes",
                "color": "#222222",
            },
        )
    )

    result = await update_project(
        UpdateProjectInput(
            organization_id=ORG_ID,
            project_id=PROJECT_ID,
            name="Renamed project",
            description="Notes",
            color="#222222",
        )
    )

    assert route.called
    body = json.loads(route.calls[0].request.content)
    assert body == {
        "name": "Renamed project",
        "description": "Notes",
        "color": "#222222",
    }
    assert '"name":"Renamed project"' in result


@pytest.mark.asyncio
@respx.mock
async def test_create_organization_passthrough_admin_403(monkeypatch, caller_auth):
    _point_client(monkeypatch)
    respx.get("http://api.test/organizations").mock(return_value=Response(200, json=[]))
    respx.post("http://api.test/organizations").mock(
        return_value=Response(403, json=ACL_403)
    )

    with pytest.raises(ArcTodoApiError, match="ERR-ARC-ACL-01") as exc:
        await create_organization(CreateOrganizationInput(name="Throwaway"))

    assert exc.value.status_code == 403
