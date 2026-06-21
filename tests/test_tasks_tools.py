import pytest
import respx
from httpx import Response
from mcp.types import ListToolsRequest

from app.arc_todo_client import arc_todo_client
from app.mcp_server import build_mcp_server
from app.tools.handlers import create_task, list_tasks, update_task
from app.tool_registry import CreateTaskInput, ListTasksInput, UpdateTaskInput


@pytest.mark.asyncio
async def test_build_mcp_server_registers_only_enabled_tools():
    enabled = {"check_arc_todo_api_health", "list_tasks"}
    _, session_manager = build_mcp_server(enabled)

    list_tools_handler = session_manager.app.request_handlers[ListToolsRequest]
    result = await list_tools_handler(None)
    tools = result.root.tools
    tool_names = {tool.name for tool in tools}

    assert "check_arc_todo_api_health" in tool_names
    assert "list_tasks" in tool_names
    assert "create_task" not in tool_names


@pytest.fixture
def api_client(monkeypatch):
    monkeypatch.setenv("ARC_TODO_API_BASE_URL", "http://api.test")
    monkeypatch.setenv("ARC_TODO_ACCESS_TOKEN", "token-abc")
    arc_todo_client._base_url = "http://api.test"
    arc_todo_client._token = "token-abc"
    return arc_todo_client


@pytest.mark.asyncio
@respx.mock
async def test_create_task_maps_parent_task_id(api_client):
    org_id = "57df4a79-d87d-40e1-9fb0-2da29d8ebecf"
    project_id = "d576e04d-f683-4b88-a374-0aab28a4be10"
    parent_id = "11111111-1111-1111-1111-111111111111"
    route = respx.post(
        f"http://api.test/organizations/{org_id}/projects/{project_id}/tasks"
    ).mock(
        return_value=Response(
            201,
            json={
                "id": "22222222-2222-2222-2222-222222222222",
                "title": "Subtask",
                "parentTaskId": parent_id,
            },
        )
    )

    result = await create_task(
        CreateTaskInput(
            organization_id=org_id,
            project_id=project_id,
            title="Subtask",
            parent_task_id=parent_id,
        )
    )

    assert route.called
    assert '"parentTaskId":' in route.calls[0].request.content.decode()
    assert parent_id in result


@pytest.mark.asyncio
@respx.mock
async def test_list_tasks_maps_parent_task_id_filter(api_client):
    parent_id = "11111111-1111-1111-1111-111111111111"
    route = respx.get("http://api.test/tasks").mock(
        return_value=Response(200, json=[])
    )

    await list_tasks(ListTasksInput(parent_task_id=parent_id))

    assert route.called
    assert route.calls[0].request.url.params["parentTaskId"] == parent_id


@pytest.mark.asyncio
@respx.mock
async def test_update_task_maps_parent_task_id(api_client):
    org_id = "57df4a79-d87d-40e1-9fb0-2da29d8ebecf"
    project_id = "d576e04d-f683-4b88-a374-0aab28a4be10"
    task_id = "22222222-2222-2222-2222-222222222222"
    parent_id = "11111111-1111-1111-1111-111111111111"
    route = respx.patch(
        f"http://api.test/organizations/{org_id}/projects/{project_id}/tasks/{task_id}"
    ).mock(
        return_value=Response(
            200,
            json={
                "id": task_id,
                "title": "Subtask",
                "parentTaskId": parent_id,
            },
        )
    )

    await update_task(
        UpdateTaskInput(
            organization_id=org_id,
            project_id=project_id,
            task_id=task_id,
            parent_task_id=parent_id,
        )
    )

    assert route.called
    assert '"parentTaskId":' in route.calls[0].request.content.decode()
