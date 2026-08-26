import pytest
import respx
from httpx import Response
from mcp.types import ListToolsRequest

from app.arc_todo_client import arc_todo_client
from app.mcp_server import build_mcp_server
from app.tools.handlers import (
    create_task,
    delete_project,
    download_task_evidence,
    get_task,
    list_project_tasks,
    list_task_comments,
    list_task_evidence,
    list_task_history,
    list_tasks,
    move_task,
    update_task,
    add_task_comment,
)
from app.tool_registry import (
    AddTaskCommentInput,
    CreateTaskInput,
    DownloadTaskEvidenceInput,
    GetProjectInput,
    GetTaskInput,
    ListProjectTasksInput,
    ListTasksInput,
    MoveTaskInput,
    UpdateTaskInput,
)


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
def api_client(monkeypatch, caller_auth):
    monkeypatch.setenv("ARC_TODO_API_BASE_URL", "http://api.test")
    monkeypatch.setenv("ARC_TODO_ACCESS_TOKEN", "token-abc")
    arc_todo_client._base_url = "http://api.test"
    arc_todo_client._token = "token-abc"
    return arc_todo_client


@pytest.mark.asyncio
@respx.mock
async def test_delete_project_calls_project_endpoint(api_client):
    org_id = "57df4a79-d87d-40e1-9fb0-2da29d8ebecf"
    project_id = "d576e04d-f683-4b88-a374-0aab28a4be10"
    route = respx.delete(
        f"http://api.test/organizations/{org_id}/projects/{project_id}"
    ).mock(return_value=Response(204))

    result = await delete_project(
        GetProjectInput(organization_id=org_id, project_id=project_id)
    )

    assert route.called
    assert result == '{"deleted": true}'


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


@pytest.mark.asyncio
@respx.mock
async def test_get_task_resolves_friendly_task_id(api_client):
    org_id = "57df4a79-d87d-40e1-9fb0-2da29d8ebecf"
    project_id = "d576e04d-f683-4b88-a374-0aab28a4be10"
    task_id = "22222222-2222-2222-2222-222222222222"
    resolve_route = respx.get("http://api.test/tasks/resolve").mock(
        return_value=Response(
            200,
            json={
                "id": task_id,
                "displayId": "#arc-1",
                "taskNumber": 1,
                "organizationId": org_id,
                "projectId": project_id,
                "title": "Friendly task",
            },
        )
    )
    get_route = respx.get(
        f"http://api.test/organizations/{org_id}/projects/{project_id}/tasks/{task_id}"
    ).mock(
        return_value=Response(
            200,
            json={"id": task_id, "title": "Friendly task", "displayId": "#arc-1"},
        )
    )

    from app.tools.handlers import get_task
    from app.tool_registry import GetTaskInput

    result = await get_task(
        GetTaskInput(
            organization_id=org_id,
            project_id=project_id,
            task_id="arc-1",
        )
    )

    assert resolve_route.called
    assert get_route.called
    assert task_id in result


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


@pytest.mark.asyncio
@respx.mock
async def test_create_task_maps_category_and_metadata(api_client):
    org_id = "57df4a79-d87d-40e1-9fb0-2da29d8ebecf"
    project_id = "d576e04d-f683-4b88-a374-0aab28a4be10"
    route = respx.post(
        f"http://api.test/organizations/{org_id}/projects/{project_id}/tasks"
    ).mock(
        return_value=Response(
            201,
            json={
                "id": "22222222-2222-2222-2222-222222222222",
                "title": "Coding task",
                "category": "coding",
                "metadata": {"repositoryUrl": "https://github.com/example/repo"},
            },
        )
    )

    await create_task(
        CreateTaskInput(
            organization_id=org_id,
            project_id=project_id,
            title="Coding task",
            category="coding",
            metadata={
                "repositoryUrl": "https://github.com/example/repo",
                "branch": "main",
                "commits": ["abc123"],
            },
        )
    )

    body = route.calls[0].request.content.decode()
    assert '"category":"coding"' in body or '"category": "coding"' in body
    assert "repositoryUrl" in body
    assert '"branch":"main"' in body or '"branch": "main"' in body


@pytest.mark.asyncio
@respx.mock
async def test_update_task_maps_is_bug(api_client):
    org_id = "57df4a79-d87d-40e1-9fb0-2da29d8ebecf"
    project_id = "d576e04d-f683-4b88-a374-0aab28a4be10"
    task_id = "22222222-2222-2222-2222-222222222222"
    route = respx.patch(
        f"http://api.test/organizations/{org_id}/projects/{project_id}/tasks/{task_id}"
    ).mock(
        return_value=Response(
            200,
            json={
                "id": task_id,
                "title": "Bug task",
                "isBug": True,
                "status": "todo",
            },
        )
    )

    await update_task(
        UpdateTaskInput(
            organization_id=org_id,
            project_id=project_id,
            task_id=task_id,
            is_bug=True,
            bug_reason="Broken checklist",
        )
    )

    body = route.calls[0].request.content.decode()
    assert "isBug" in body
    assert "bugReason" in body


@pytest.mark.asyncio
@respx.mock
async def test_list_tasks_maps_category_filter(api_client):
    route = respx.get("http://api.test/tasks").mock(
        return_value=Response(200, json=[])
    )

    await list_tasks(ListTasksInput(category="coding"))

    assert route.called
    assert route.calls[0].request.url.params["category"] == "coding"


@pytest.mark.asyncio
@respx.mock
async def test_list_task_comments_calls_comments_endpoint(api_client):
    org_id = "57df4a79-d87d-40e1-9fb0-2da29d8ebecf"
    project_id = "d576e04d-f683-4b88-a374-0aab28a4be10"
    task_id = "22222222-2222-2222-2222-222222222222"
    route = respx.get(
        f"http://api.test/organizations/{org_id}/projects/{project_id}/tasks/{task_id}/comments"
    ).mock(
        return_value=Response(
            200,
            json=[
                {
                    "id": "c1",
                    "taskId": task_id,
                    "body": "Icon breaks on mobile",
                    "createdById": "u1",
                    "createdAt": "2026-08-05T12:00:00.000Z",
                    "updatedAt": "2026-08-05T12:00:00.000Z",
                }
            ],
        )
    )

    result = await list_task_comments(
        GetTaskInput(
            organization_id=org_id,
            project_id=project_id,
            task_id=task_id,
        )
    )

    assert route.called
    assert "Icon breaks on mobile" in result


@pytest.mark.asyncio
@respx.mock
async def test_add_task_comment_posts_body(api_client):
    org_id = "57df4a79-d87d-40e1-9fb0-2da29d8ebecf"
    project_id = "d576e04d-f683-4b88-a374-0aab28a4be10"
    task_id = "22222222-2222-2222-2222-222222222222"
    route = respx.post(
        f"http://api.test/organizations/{org_id}/projects/{project_id}/tasks/{task_id}/comments"
    ).mock(
        return_value=Response(
            201,
            json={
                "id": "c2",
                "taskId": task_id,
                "body": "Fixed icon padding",
                "createdById": "u1",
                "createdAt": "2026-08-05T13:00:00.000Z",
                "updatedAt": "2026-08-05T13:00:00.000Z",
            },
        )
    )

    result = await add_task_comment(
        AddTaskCommentInput(
            organization_id=org_id,
            project_id=project_id,
            task_id=task_id,
            body="Fixed icon padding",
        )
    )

    assert route.called
    assert '"body": "Fixed icon padding"' in route.calls[0].request.content.decode() or (
        '"body":"Fixed icon padding"' in route.calls[0].request.content.decode()
    )
    assert "Fixed icon padding" in result


@pytest.mark.asyncio
@respx.mock
async def test_list_task_evidence_calls_evidence_endpoint(api_client):
    org_id = "57df4a79-d87d-40e1-9fb0-2da29d8ebecf"
    project_id = "d576e04d-f683-4b88-a374-0aab28a4be10"
    task_id = "22222222-2222-2222-2222-222222222222"
    route = respx.get(
        f"http://api.test/organizations/{org_id}/projects/{project_id}/tasks/{task_id}/evidence"
    ).mock(
        return_value=Response(
            200,
            json=[
                {
                    "id": "e1",
                    "taskId": task_id,
                    "originalFilename": "icon-bug.png",
                    "mimeType": "image/png",
                    "sizeBytes": 1234,
                    "uploadedById": "u1",
                    "createdAt": "2026-08-05T12:00:00.000Z",
                }
            ],
        )
    )

    result = await list_task_evidence(
        GetTaskInput(
            organization_id=org_id,
            project_id=project_id,
            task_id=task_id,
        )
    )

    assert route.called
    assert "icon-bug.png" in result


@pytest.mark.asyncio
@respx.mock
async def test_list_task_history_calls_history_endpoint(api_client):
    org_id = "57df4a79-d87d-40e1-9fb0-2da29d8ebecf"
    project_id = "d576e04d-f683-4b88-a374-0aab28a4be10"
    task_id = "22222222-2222-2222-2222-222222222222"
    route = respx.get(
        f"http://api.test/organizations/{org_id}/projects/{project_id}/tasks/{task_id}/history"
    ).mock(
        return_value=Response(
            200,
            json=[
                {
                    "id": "h1",
                    "taskId": task_id,
                    "field": "isBug",
                    "oldValue": "false",
                    "newValue": "true",
                    "changedById": "u1",
                    "createdAt": "2026-08-05T12:00:00.000Z",
                },
                {
                    "id": "h2",
                    "taskId": task_id,
                    "field": "bugReason",
                    "oldValue": None,
                    "newValue": "Falha no checklist item 2",
                    "changedById": "u1",
                    "createdAt": "2026-08-05T12:00:00.000Z",
                },
            ],
        )
    )

    result = await list_task_history(
        GetTaskInput(
            organization_id=org_id,
            project_id=project_id,
            task_id=task_id,
        )
    )

    assert route.called
    assert "isBug" in result
    assert "Falha no checklist item 2" in result


@pytest.mark.asyncio
@respx.mock
async def test_download_task_evidence_returns_image_content(api_client):
    from mcp.types import ImageContent, TextContent

    org_id = "57df4a79-d87d-40e1-9fb0-2da29d8ebecf"
    project_id = "d576e04d-f683-4b88-a374-0aab28a4be10"
    task_id = "22222222-2222-2222-2222-222222222222"
    evidence_id = "33333333-3333-3333-3333-333333333333"
    png_bytes = b"\x89PNG\r\n\x1a\nfake"
    route = respx.get(
        f"http://api.test/organizations/{org_id}/projects/{project_id}/tasks/{task_id}"
        f"/evidence/{evidence_id}/download"
    ).mock(
        return_value=Response(
            200,
            content=png_bytes,
            headers={
                "content-type": "image/png",
                "content-disposition": 'attachment; filename="icon-bug.png"',
            },
        )
    )

    result = await download_task_evidence(
        DownloadTaskEvidenceInput(
            organization_id=org_id,
            project_id=project_id,
            task_id=task_id,
            evidence_id=evidence_id,
        )
    )

    assert route.called
    assert len(result) == 2
    assert isinstance(result[0], TextContent)
    assert "icon-bug.png" in result[0].text
    assert "contentBase64" not in result[0].text
    assert isinstance(result[1], ImageContent)
    assert result[1].mimeType == "image/png"


FAT_TASK = {
    "id": "22222222-2222-2222-2222-222222222222",
    "displayId": "#arc-1",
    "title": "Fix login freeze",
    "description": "duplicate alias of business",
    "businessDescription": "Users cannot sign in",
    "planCodeDescription": "Patch LoginPage.tsx",
    "testDescription": "Abrir /login e tentar entrar",
    "status": "todo",
    "criticity": "high",
    "category": "coding",
    "isBug": True,
    "bugReason": "Button stuck",
    "qaChecklistState": {"checkedItemIds": ["item-1"]},
    "assignee": {"id": "u1", "username": "admin"},
    "createdById": "u1",
    "project": {
        "id": "d576e04d-f683-4b88-a374-0aab28a4be10",
        "name": "Arc Todo",
        "acronym": "arc",
    },
    "organization": {
        "id": "57df4a79-d87d-40e1-9fb0-2da29d8ebecf",
        "name": "Cursor",
        "slug": "cursor",
    },
    "subtasks": [
        {
            "id": "33333333-3333-3333-3333-333333333333",
            "displayId": "#arc-2",
            "title": "Wire UI",
            "status": "todo",
            "isBug": False,
            "planCodeDescription": "child plan should not leak",
            "testDescription": "child qa should not leak",
        }
    ],
}


@pytest.mark.asyncio
@respx.mock
async def test_get_task_default_plan_is_compact_and_omits_qa(api_client):
    org_id = "57df4a79-d87d-40e1-9fb0-2da29d8ebecf"
    project_id = "d576e04d-f683-4b88-a374-0aab28a4be10"
    task_id = FAT_TASK["id"]
    respx.get("http://api.test/tasks/resolve").mock(
        return_value=Response(
            200,
            json={
                "id": task_id,
                "displayId": "#arc-1",
                "taskNumber": 1,
                "organizationId": org_id,
                "projectId": project_id,
                "title": FAT_TASK["title"],
            },
        )
    )
    respx.get(
        f"http://api.test/organizations/{org_id}/projects/{project_id}/tasks/{task_id}"
    ).mock(return_value=Response(200, json=FAT_TASK))

    result = await get_task(GetTaskInput(task_id="#arc-1"))

    assert "\n" not in result
    assert ": " not in result
    assert "Patch LoginPage.tsx" in result
    assert "Users cannot sign in" in result
    assert "Abrir /login" not in result
    assert "duplicate alias" not in result
    assert "Button stuck" not in result
    assert "child plan should not leak" not in result
    assert "#arc-2" in result
    assert '"isBug":true' in result


@pytest.mark.asyncio
@respx.mock
async def test_get_task_include_qa_returns_test_description(api_client):
    org_id = "57df4a79-d87d-40e1-9fb0-2da29d8ebecf"
    project_id = "d576e04d-f683-4b88-a374-0aab28a4be10"
    task_id = FAT_TASK["id"]
    respx.get(
        f"http://api.test/organizations/{org_id}/projects/{project_id}/tasks/{task_id}"
    ).mock(return_value=Response(200, json=FAT_TASK))

    result = await get_task(
        GetTaskInput(
            organization_id=org_id,
            project_id=project_id,
            task_id=task_id,
            include="qa",
        )
    )

    assert "Abrir /login" in result
    assert "Button stuck" in result
    assert "Patch LoginPage.tsx" not in result


@pytest.mark.asyncio
@respx.mock
async def test_list_tasks_default_summary_omits_descriptions(api_client):
    respx.get("http://api.test/tasks").mock(
        return_value=Response(200, json=[FAT_TASK])
    )

    result = await list_tasks(ListTasksInput())

    assert "Users cannot sign in" not in result
    assert "Patch LoginPage.tsx" not in result
    assert "Abrir /login" not in result
    assert "Fix login freeze" in result
    assert '"isBug":true' in result
    assert '"name":"Arc Todo"' not in result
    assert '"slug":"cursor"' not in result


@pytest.mark.asyncio
@respx.mock
async def test_list_project_tasks_default_summary(api_client):
    org_id = "57df4a79-d87d-40e1-9fb0-2da29d8ebecf"
    project_id = "d576e04d-f683-4b88-a374-0aab28a4be10"
    respx.get(
        f"http://api.test/organizations/{org_id}/projects/{project_id}/tasks"
    ).mock(return_value=Response(200, json=[FAT_TASK]))

    result = await list_project_tasks(
        ListProjectTasksInput(organization_id=org_id, project_id=project_id)
    )

    assert "Patch LoginPage.tsx" not in result
    assert "Fix login freeze" in result


@pytest.mark.asyncio
async def test_get_task_uuid_without_scope_raises(api_client):
    with pytest.raises(ValueError, match="organization_id and project_id are required"):
        await get_task(
            GetTaskInput(task_id="22222222-2222-2222-2222-222222222222")
        )


@pytest.mark.asyncio
@respx.mock
async def test_list_tasks_passes_q_limit_and_parents_only(api_client):
    route = respx.get("http://api.test/tasks").mock(
        return_value=Response(200, json=[])
    )

    await list_tasks(
        ListTasksInput(q="login freeze", limit=5, parents_only=True, status="todo")
    )

    params = route.calls[0].request.url.params
    assert params["q"] == "login freeze"
    assert params["limit"] == "5"
    assert params["parentsOnly"] == "true"
    assert params["status"] == "todo"


@pytest.mark.asyncio
@respx.mock
async def test_list_project_tasks_passes_status_and_parents_only(api_client):
    org_id = "57df4a79-d87d-40e1-9fb0-2da29d8ebecf"
    project_id = "d576e04d-f683-4b88-a374-0aab28a4be10"
    route = respx.get(
        f"http://api.test/organizations/{org_id}/projects/{project_id}/tasks"
    ).mock(return_value=Response(200, json=[]))

    await list_project_tasks(
        ListProjectTasksInput(
            organization_id=org_id,
            project_id=project_id,
            status="todo",
            parents_only=True,
            q="MCP token",
        )
    )

    params = route.calls[0].request.url.params
    assert params["status"] == "todo"
    assert params["parentsOnly"] == "true"
    assert params["q"] == "MCP token"


@pytest.mark.asyncio
@respx.mock
async def test_create_task_resolves_project_acronym(api_client):
    org_id = "57df4a79-d87d-40e1-9fb0-2da29d8ebecf"
    project_id = "d576e04d-f683-4b88-a374-0aab28a4be10"
    resolve_route = respx.get("http://api.test/scope/resolve").mock(
        return_value=Response(
            200,
            json={
                "status": "resolved",
                "organization": {"id": org_id, "name": "Cursor", "slug": "cursor"},
                "project": {
                    "id": project_id,
                    "name": "Arc Todo Skills",
                    "organizationId": org_id,
                },
            },
        )
    )
    create_route = respx.post(
        f"http://api.test/organizations/{org_id}/projects/{project_id}/tasks"
    ).mock(
        return_value=Response(
            201,
            json={"id": "22222222-2222-2222-2222-222222222222", "title": "New task"},
        )
    )

    await create_task(CreateTaskInput(project="ski", title="New task"))

    assert resolve_route.called
    assert resolve_route.calls[0].request.url.params["projectHint"] == "ski"
    assert create_route.called


@pytest.mark.asyncio
@respx.mock
async def test_list_project_tasks_resolves_slug_and_defaults_after_get_task(
    api_client,
):
    org_id = "57df4a79-d87d-40e1-9fb0-2da29d8ebecf"
    project_id = "d576e04d-f683-4b88-a374-0aab28a4be10"
    task_id = FAT_TASK["id"]
    respx.get("http://api.test/tasks/resolve").mock(
        return_value=Response(
            200,
            json={
                "id": task_id,
                "displayId": "#ski-52",
                "taskNumber": 52,
                "organizationId": org_id,
                "projectId": project_id,
                "title": FAT_TASK["title"],
            },
        )
    )
    respx.get(
        f"http://api.test/organizations/{org_id}/projects/{project_id}/tasks/{task_id}"
    ).mock(return_value=Response(200, json=FAT_TASK))
    list_route = respx.get(
        f"http://api.test/organizations/{org_id}/projects/{project_id}/tasks"
    ).mock(return_value=Response(200, json=[]))

    await get_task(GetTaskInput(task_id="#ski-52"))
    await list_project_tasks(ListProjectTasksInput(status="todo"))

    assert list_route.called
    assert list_route.calls[0].request.url.params["status"] == "todo"


@pytest.mark.asyncio
@respx.mock
async def test_move_task_patches_status_and_returns_ack(api_client):
    org_id = "57df4a79-d87d-40e1-9fb0-2da29d8ebecf"
    project_id = "d576e04d-f683-4b88-a374-0aab28a4be10"
    task_id = FAT_TASK["id"]
    respx.get("http://api.test/tasks/resolve").mock(
        return_value=Response(
            200,
            json={
                "id": task_id,
                "displayId": "#arc-1",
                "organizationId": org_id,
                "projectId": project_id,
            },
        )
    )
    route = respx.patch(
        f"http://api.test/organizations/{org_id}/projects/{project_id}/tasks/{task_id}"
    ).mock(return_value=Response(200, json=FAT_TASK))

    result = await move_task(MoveTaskInput(task_id="#arc-1", status="dev_test"))

    assert route.called
    body = route.calls[0].request.content.decode()
    assert '"status"' in body
    assert "dev_test" in body
    assert "Patch LoginPage.tsx" not in result
    assert "subtasks" not in result
    assert "Fix login freeze" in result


@pytest.mark.asyncio
@respx.mock
async def test_update_task_default_ack_omits_plan_and_subtasks(api_client):
    org_id = "57df4a79-d87d-40e1-9fb0-2da29d8ebecf"
    project_id = "d576e04d-f683-4b88-a374-0aab28a4be10"
    task_id = FAT_TASK["id"]
    respx.patch(
        f"http://api.test/organizations/{org_id}/projects/{project_id}/tasks/{task_id}"
    ).mock(return_value=Response(200, json=FAT_TASK))

    result = await update_task(
        UpdateTaskInput(
            organization_id=org_id,
            project_id=project_id,
            task_id=task_id,
            title="Fix login freeze",
        )
    )

    assert "Patch LoginPage.tsx" not in result
    assert "Users cannot sign in" not in result
    assert "subtasks" not in result
    assert "Fix login freeze" in result



