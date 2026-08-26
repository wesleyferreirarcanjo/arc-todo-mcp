from __future__ import annotations

import base64
from typing import Any

from mcp.types import ImageContent, TextContent

from app.arc_todo_client import arc_todo_client
from app.board_scope import remember_board, resolve_board_scope
from app.caller_auth import require_caller_token
from app.rag_client import RagClientError, rag_client
from app.task_id_resolver import is_uuid, resolve_task_scope
from app.task_include import normalize_include, project_payload
from app.tool_registry import (
    AddOrganizationMemberInput,
    AddTaskCommentInput,
    CreateOrganizationUserInput,
    CreateKnowledgeInput,
    CreateProjectDiagramInput,
    CreateProjectInput,
    CreateProjectWireframeInput,
    CreateTaskInput,
    DeleteAttachmentInput,
    DownloadAttachmentInput,
    DownloadTaskEvidenceInput,
    EmptyInput,
    GetOrganizationInput,
    GetPersonInput,
    GetProjectDiagramInput,
    GetProjectInput,
    GetProjectWireframeInput,
    GetTaskInput,
    KnowledgeEntryInput,
    KnowledgeScopeInput,
    ListAttachmentsInput,
    ListOrganizationActivityInput,
    ListOrganizationMembersInput,
    ListPersonsInput,
    ListProjectDiagramsInput,
    ListProjectWireframesInput,
    ListProjectNameSessionsInput,
    GetNameSessionInput,
    CreateNameSessionInput,
    UpdateNameSessionInput,
    AddNameCandidatesInput,
    CheckNameCandidateInput,
    RecommendNameCandidateInput,
    ListProjectTasksInput,
    ListProjectsInput,
    ListTasksInput,
    OptionalTaskScopeInput,
    RetrieveKnowledgeInput,
    UpdateKnowledgeInput,
    UpdateProjectDiagramInput,
    UpdateProjectWireframeInput,
    GetProjectQaInfoInput,
    UpdateProjectQaInfoInput,
    UpdateTaskInput,
    UploadAttachmentInput,
    register_tool,
)


@register_tool(
    key="check_arc_todo_api_health",
    group="system",
    display_name="Check API health",
    description="Check whether the Arc Todo API is reachable and healthy.",
    sort_order=1,
    input_model=EmptyInput,
)
async def check_arc_todo_api_health(_: EmptyInput) -> str:
    data = await arc_todo_client.request_public("GET", "/health")
    return arc_todo_client.format_result(data)


_enabled_keys: set[str] = set()


def set_enabled_keys(keys: set[str]) -> None:
    global _enabled_keys
    _enabled_keys = keys


@register_tool(
    key="list_enabled_mcp_tools",
    group="system",
    display_name="List enabled MCP tools",
    description="List MCP tools registered by this server at startup.",
    sort_order=2,
    input_model=EmptyInput,
)
async def list_enabled_mcp_tools(_: EmptyInput) -> str:
    return arc_todo_client.format_result(sorted(_enabled_keys))


@register_tool(
    key="list_organizations",
    group="context",
    display_name="List organizations",
    description="List organizations the authenticated user belongs to.",
    sort_order=10,
    input_model=EmptyInput,
)
async def list_organizations(_: EmptyInput) -> str:
    data = await arc_todo_client.request("GET", "/organizations")
    return arc_todo_client.format_result(data)


@register_tool(
    key="get_organization",
    group="context",
    display_name="Get organization",
    description="Fetch one organization by ID.",
    sort_order=11,
    input_model=GetOrganizationInput,
)
async def get_organization(input: GetOrganizationInput) -> str:
    data = await arc_todo_client.request(
        "GET",
        f"/organizations/{input.organization_id}",
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="list_organization_members",
    group="context",
    display_name="List organization members",
    description="List login members of an organization with roles.",
    sort_order=12,
    input_model=ListOrganizationMembersInput,
)
async def list_organization_members(input: ListOrganizationMembersInput) -> str:
    data = await arc_todo_client.request(
        "GET",
        f"/organizations/{input.organization_id}/members",
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="create_organization_user",
    group="context",
    display_name="Create organization user",
    description="Create a login user and add them to an organization.",
    sort_order=13,
    input_model=CreateOrganizationUserInput,
)
async def create_organization_user(input: CreateOrganizationUserInput) -> str:
    body: dict[str, str] = {
        "username": input.username,
        "password": input.password,
    }
    if input.role:
        body["role"] = input.role
    data = await arc_todo_client.request(
        "POST",
        f"/organizations/{input.organization_id}/users",
        json_body=body,
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="add_organization_member",
    group="context",
    display_name="Add organization member",
    description="Add an existing login user to an organization by username.",
    sort_order=14,
    input_model=AddOrganizationMemberInput,
)
async def add_organization_member(input: AddOrganizationMemberInput) -> str:
    body: dict[str, str] = {"username": input.username}
    if input.role:
        body["role"] = input.role
    data = await arc_todo_client.request(
        "POST",
        f"/organizations/{input.organization_id}/members",
        json_body=body,
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="list_organization_activity",
    group="activity",
    display_name="List organization activity",
    description="List recent user activity for an organization.",
    sort_order=30,
    input_model=ListOrganizationActivityInput,
)
async def list_organization_activity(input: ListOrganizationActivityInput) -> str:
    params: dict[str, str | int] = {}
    if input.user_id:
        params["userId"] = input.user_id
    if input.limit is not None:
        params["limit"] = input.limit
    if input.offset is not None:
        params["offset"] = input.offset
    data = await arc_todo_client.request(
        "GET",
        f"/organizations/{input.organization_id}/activity",
        params=params or None,
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="list_projects",
    group="context",
    display_name="List projects",
    description="List projects in an organization.",
    sort_order=16,
    input_model=ListProjectsInput,
)
async def list_projects(input: ListProjectsInput) -> str:
    data = await arc_todo_client.request(
        "GET",
        f"/organizations/{input.organization_id}/projects",
    )
    return arc_todo_client.format_result(data)


def _project_body(input: CreateProjectInput) -> dict[str, str]:
    body: dict[str, str] = {"name": input.name}
    if input.description is not None:
        body["description"] = input.description
    if input.color is not None:
        body["color"] = input.color
    return body


@register_tool(
    key="create_project",
    group="context",
    display_name="Create project",
    description="Create a project in an organization.",
    sort_order=17,
    input_model=CreateProjectInput,
)
async def create_project(input: CreateProjectInput) -> str:
    data = await arc_todo_client.request(
        "POST",
        f"/organizations/{input.organization_id}/projects",
        json_body=_project_body(input),
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="get_project",
    group="context",
    display_name="Get project",
    description="Fetch one project by organization and project ID.",
    sort_order=18,
    input_model=GetProjectInput,
)
async def get_project(input: GetProjectInput) -> str:
    data = await arc_todo_client.request(
        "GET",
        f"/organizations/{input.organization_id}/projects/{input.project_id}",
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="delete_project",
    group="context",
    display_name="Delete project",
    description="Delete a project from an organization.",
    sort_order=19,
    input_model=GetProjectInput,
)
async def delete_project(input: GetProjectInput) -> str:
    await arc_todo_client.request(
        "DELETE",
        f"/organizations/{input.organization_id}/projects/{input.project_id}",
    )
    return '{"deleted": true}'


@register_tool(
    key="list_persons",
    group="context",
    display_name="List persons",
    description="List persons globally or within an organization.",
    sort_order=20,
    input_model=ListPersonsInput,
)
async def list_persons(input: ListPersonsInput) -> str:
    if input.organization_id:
        path = f"/organizations/{input.organization_id}/persons"
    else:
        path = "/persons"
    data = await arc_todo_client.request("GET", path)
    return arc_todo_client.format_result(data)


@register_tool(
    key="get_person",
    group="context",
    display_name="Get person",
    description="Fetch one person globally or within an organization.",
    sort_order=21,
    input_model=GetPersonInput,
)
async def get_person(input: GetPersonInput) -> str:
    if input.organization_id:
        path = f"/organizations/{input.organization_id}/persons/{input.person_id}"
    else:
        path = f"/persons/{input.person_id}"
    data = await arc_todo_client.request("GET", path)
    return arc_todo_client.format_result(data)


def _task_body(input: CreateTaskInput | UpdateTaskInput) -> dict:
    body: dict = {}
    if isinstance(input, CreateTaskInput):
        body["title"] = input.title
    elif input.title is not None:
        body["title"] = input.title
    if input.description is not None:
        body["description"] = input.description
    if input.business_description is not None:
        body["businessDescription"] = input.business_description
    if input.plan_code_description is not None:
        body["planCodeDescription"] = input.plan_code_description
    if input.test_description is not None:
        body["testDescription"] = input.test_description
    if input.status is not None:
        body["status"] = input.status
    if input.criticity is not None:
        body["criticity"] = input.criticity
    if input.due_date is not None:
        body["dueDate"] = input.due_date
    if input.parent_task_id is not None:
        body["parentTaskId"] = input.parent_task_id
    if input.category is not None:
        body["category"] = input.category
    if input.metadata is not None:
        body["metadata"] = input.metadata
    if input.is_bug is not None:
        body["isBug"] = input.is_bug
    if input.bug_reason is not None:
        body["bugReason"] = input.bug_reason
    if input.qa_checklist_state is not None:
        body["qaChecklistState"] = input.qa_checklist_state
    return body


@register_tool(
    key="list_tasks",
    group="tasks",
    display_name="List tasks",
    description=(
        "List tasks with optional filters. Default include=summary. "
        "Rows omit nested project/organization objects. "
        "Pass q, limit, and parents_only for duplicate checks. "
        "organization_id/project_id UUIDs are optional: use project=ski (acronym) "
        "or a friendly task id on another call in this session."
    ),
    sort_order=20,
    input_model=ListTasksInput,
)
async def list_tasks(input: ListTasksInput) -> str:
    org_id, project_id = await resolve_board_scope(
        arc_todo_client,
        organization_id=input.organization_id,
        project_id=input.project_id,
        project=input.project,
        use_last=True,
        required=False,
    )
    parent_task_id = input.parent_task_id
    if parent_task_id and not is_uuid(parent_task_id):
        parent = await resolve_task_scope(arc_todo_client, parent_task_id)
        parent_task_id = parent["task_id"]
        if not org_id:
            org_id = parent.get("organization_id")
        if not project_id:
            project_id = parent.get("project_id")
    params = _list_filter_params(
        organization_id=org_id,
        project_id=project_id,
        status=input.status,
        criticity=input.criticity,
        parent_task_id=parent_task_id,
        category=input.category,
        is_bug=input.is_bug,
        q=input.q,
        limit=input.limit,
        parents_only=input.parents_only,
    )
    data = await arc_todo_client.request("GET", "/tasks", params=params)
    include = normalize_include(input.include, "summary")
    return arc_todo_client.format_result(
        project_payload(data, include, omit_nested_scope=True)
    )


@register_tool(
    key="list_project_tasks",
    group="tasks",
    display_name="List project tasks",
    description=(
        "List tasks in one project. Leaner than list_tasks (no nested org/project). "
        "Pass project=ski (acronym) or slug; UUIDs optional. "
        "status, q, limit, and parents_only filter the board so duplicate checks "
        "do not pull every status."
    ),
    sort_order=21,
    input_model=ListProjectTasksInput,
)
async def list_project_tasks(input: ListProjectTasksInput) -> str:
    org_id, project_id = await resolve_board_scope(
        arc_todo_client,
        organization_id=input.organization_id,
        project_id=input.project_id,
        project=input.project,
        use_last=True,
        required=True,
    )
    params = _list_filter_params(
        status=input.status,
        q=input.q,
        limit=input.limit,
        parents_only=input.parents_only,
    )
    data = await arc_todo_client.request(
        "GET",
        f"/organizations/{org_id}/projects/{project_id}/tasks",
        params=params,
    )
    include = normalize_include(input.include, "summary")
    return arc_todo_client.format_result(
        project_payload(data, include, omit_nested_scope=True)
    )


@register_tool(
    key="get_task",
    group="tasks",
    display_name="Get task",
    description=(
        "Fetch one task. Default include=plan (business + plan/code, no QA essay). "
        "Friendly IDs like #arc-1 do not need organization_id/project_id. "
        "include: summary | plan | qa | full."
    ),
    sort_order=22,
    input_model=GetTaskInput,
)
async def get_task(input: GetTaskInput) -> str:
    org_id, project_id, task_id = await _resolve_task_path(input)
    data = await arc_todo_client.request(
        "GET",
        f"/organizations/{org_id}/projects/{project_id}/tasks/{task_id}",
    )
    include = normalize_include(input.include, "plan")
    return arc_todo_client.format_result(project_payload(data, include))


@register_tool(
    key="create_task",
    group="tasks",
    display_name="Create task",
    description="Create a task in a project. Pass project=ski (acronym) or skill (slug) instead of UUIDs. Optional parent_task_id creates a direct subtask.",
    sort_order=23,
    input_model=CreateTaskInput,
)
async def create_task(input: CreateTaskInput) -> str:
    org_id, project_id = await resolve_board_scope(
        arc_todo_client,
        organization_id=input.organization_id,
        project_id=input.project_id,
        project=input.project,
        parent_task_id=input.parent_task_id,
        use_last=False,
        required=True,
    )
    body = _task_body(input)
    if input.parent_task_id and not is_uuid(input.parent_task_id):
        parent = await resolve_task_scope(arc_todo_client, input.parent_task_id)
        body["parentTaskId"] = parent["task_id"]
    data = await arc_todo_client.request(
        "POST",
        f"/organizations/{org_id}/projects/{project_id}/tasks",
        json_body=body,
    )
    include = normalize_include(input.include, "summary")
    return arc_todo_client.format_result(project_payload(data, include))


@register_tool(
    key="update_task",
    group="tasks",
    display_name="Update task",
    description="Update a task in a project. Set parent_task_id to attach as subtask or null to detach. Setting is_bug=true reports an open bug (requires bug_reason) and moves it to todo; is_bug=false marks the bug solved.",
    sort_order=24,
    input_model=UpdateTaskInput,
)
async def update_task(input: UpdateTaskInput) -> str:
    org_id, project_id, task_id = await _resolve_task_path(input)
    body = _task_body(input)
    if input.parent_task_id and not is_uuid(input.parent_task_id):
        parent = await resolve_task_scope(arc_todo_client, input.parent_task_id)
        body["parentTaskId"] = parent["task_id"]
    data = await arc_todo_client.request(
        "PATCH",
        f"/organizations/{org_id}/projects/{project_id}/tasks/{task_id}",
        json_body=body,
    )
    include = normalize_include(input.include, "summary")
    return arc_todo_client.format_result(project_payload(data, include))


@register_tool(
    key="delete_task",
    group="tasks",
    display_name="Delete task",
    description="Delete a task from a project.",
    sort_order=25,
    input_model=OptionalTaskScopeInput,
)
async def delete_task(input: OptionalTaskScopeInput) -> str:
    org_id, project_id, task_id = await _resolve_task_path(input)
    await arc_todo_client.request(
        "DELETE",
        f"/organizations/{org_id}/projects/{project_id}/tasks/{task_id}",
    )
    return '{"deleted":true}'


async def _resolve_task_path(input: OptionalTaskScopeInput) -> tuple[str, str, str]:
    resolved = await resolve_task_scope(arc_todo_client, input.task_id)
    org_id = resolved.get("organization_id") or input.organization_id
    project_id = resolved.get("project_id") or input.project_id
    if not org_id or not project_id:
        raise ValueError(
            "organization_id and project_id are required when task_id is a UUID. "
            "For friendly IDs like #arc-1 they can be omitted."
        )
    remember_board(org_id, project_id)
    return org_id, project_id, resolved["task_id"]


def _list_filter_params(
    *,
    organization_id: str | None = None,
    project_id: str | None = None,
    status: str | None = None,
    criticity: str | None = None,
    parent_task_id: str | None = None,
    category: str | None = None,
    is_bug: bool | None = None,
    q: str | None = None,
    limit: int | None = None,
    parents_only: bool | None = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if organization_id:
        params["organizationId"] = organization_id
    if project_id:
        params["projectId"] = project_id
    if status:
        params["status"] = status
    if criticity:
        params["criticity"] = criticity
    if parent_task_id:
        params["parentTaskId"] = parent_task_id
    if category:
        params["category"] = category
    if is_bug is not None:
        params["isBug"] = "true" if is_bug else "false"
    if q:
        params["q"] = q
    if limit is not None:
        params["limit"] = limit
    if parents_only is not None:
        params["parentsOnly"] = "true" if parents_only else "false"
    return params


@register_tool(
    key="list_task_comments",
    group="tasks",
    display_name="List task comments",
    description=(
        "List comments on a task. Use only when is_bug is true or the user asked. "
        "Supports friendly task IDs."
    ),
    sort_order=26,
    input_model=OptionalTaskScopeInput,
)
async def list_task_comments(input: OptionalTaskScopeInput) -> str:
    org_id, project_id, task_id = await _resolve_task_path(input)
    data = await arc_todo_client.request(
        "GET",
        f"/organizations/{org_id}/projects/{project_id}/tasks/{task_id}/comments",
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="add_task_comment",
    group="tasks",
    display_name="Add task comment",
    description="Post a comment on a task. Supports friendly task IDs.",
    sort_order=27,
    input_model=AddTaskCommentInput,
)
async def add_task_comment(input: AddTaskCommentInput) -> str:
    org_id, project_id, task_id = await _resolve_task_path(input)
    data = await arc_todo_client.request(
        "POST",
        f"/organizations/{org_id}/projects/{project_id}/tasks/{task_id}/comments",
        json_body={"body": input.body},
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="list_task_evidence",
    group="tasks",
    display_name="List task evidence",
    description=(
        "List image/video evidence attachments on a task. "
        "Use only when is_bug is true or the user asked. Supports friendly task IDs."
    ),
    sort_order=28,
    input_model=OptionalTaskScopeInput,
)
async def list_task_evidence(input: OptionalTaskScopeInput) -> str:
    org_id, project_id, task_id = await _resolve_task_path(input)
    data = await arc_todo_client.request(
        "GET",
        f"/organizations/{org_id}/projects/{project_id}/tasks/{task_id}/evidence",
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="download_task_evidence",
    group="tasks",
    display_name="Download task evidence",
    description=(
        "Download one task evidence file. Images return as MCP image content for vision; "
        "all files also include filename/mime/size metadata (and base64 for non-images)."
    ),
    sort_order=29,
    input_model=DownloadTaskEvidenceInput,
)
async def download_task_evidence(input: DownloadTaskEvidenceInput) -> list[Any]:
    org_id, project_id, task_id = await _resolve_task_path(input)
    content, mime_type, filename = await arc_todo_client.download(
        f"/organizations/{org_id}/projects/{project_id}/tasks/{task_id}"
        f"/evidence/{input.evidence_id}/download",
    )
    mime = (mime_type or "application/octet-stream").split(";")[0].strip()
    b64 = base64.b64encode(content).decode("ascii")
    meta: dict[str, Any] = {
        "id": input.evidence_id,
        "filename": filename,
        "mimeType": mime,
        "sizeBytes": len(content),
    }
    if not mime.startswith("image/"):
        meta["contentBase64"] = b64
    parts: list[Any] = [TextContent(type="text", text=arc_todo_client.format_result(meta))]
    if mime.startswith("image/"):
        parts.append(ImageContent(type="image", data=b64, mimeType=mime))
    return parts


@register_tool(
    key="list_task_history",
    group="tasks",
    display_name="List task history",
    description=(
        "List field-change history for a task (title, description, dueDate, isBug, bugReason). "
        "Use only when is_bug is true or the user asked. Supports friendly task IDs."
    ),
    sort_order=30,
    input_model=OptionalTaskScopeInput,
)
async def list_task_history(input: OptionalTaskScopeInput) -> str:
    org_id, project_id, task_id = await _resolve_task_path(input)
    data = await arc_todo_client.request(
        "GET",
        f"/organizations/{org_id}/projects/{project_id}/tasks/{task_id}/history",
    )
    return arc_todo_client.format_result(data)


def _knowledge_collection_path(input: KnowledgeScopeInput) -> str:
    scope = input.scope
    if scope == "general":
        return "/knowledge"
    if scope == "organization":
        if not input.organization_id:
            raise ValueError("organization_id is required for organization scope")
        return f"/organizations/{input.organization_id}/knowledge"
    if scope == "project":
        if not input.organization_id or not input.project_id:
            raise ValueError("organization_id and project_id are required for project scope")
        return (
            f"/organizations/{input.organization_id}/projects/{input.project_id}/knowledge"
        )
    if scope == "person":
        if input.organization_id and input.person_id:
            return (
                f"/organizations/{input.organization_id}/persons/{input.person_id}/knowledge"
            )
        if input.person_id:
            return f"/persons/{input.person_id}/knowledge"
        raise ValueError("person_id is required for person scope")
    raise ValueError(f"Unsupported scope: {scope}")


def _knowledge_entry_path(input: KnowledgeEntryInput) -> str:
    return f"{_knowledge_collection_path(input)}/{input.knowledge_id}"


def _attachments_base_path(input: KnowledgeEntryInput) -> str:
    return f"{_knowledge_entry_path(input)}/attachments"


@register_tool(
    key="list_knowledge",
    group="knowledge",
    display_name="List knowledge",
    description="List knowledge entries for a scope or cross-scope filters.",
    sort_order=30,
    input_model=KnowledgeScopeInput,
)
async def list_knowledge(input: KnowledgeScopeInput) -> str:
    if input.scope == "general" and not any(
        [input.organization_id, input.project_id, input.person_id, input.file_name, input.mime_type, input.has_attachments]
    ):
        data = await arc_todo_client.request("GET", "/knowledge")
    elif input.scope == "general" and any(
        [input.scope, input.organization_id, input.project_id, input.person_id]
    ):
        params = {
            k: v
            for k, v in {
                "scope": input.scope,
                "organizationId": input.organization_id,
                "projectId": input.project_id,
                "personId": input.person_id,
                "fileName": input.file_name,
                "mimeType": input.mime_type,
                "hasAttachments": "true" if input.has_attachments else None,
            }.items()
            if v is not None
        }
        data = await arc_todo_client.request("GET", "/knowledge", params=params)
    else:
        data = await arc_todo_client.request("GET", _knowledge_collection_path(input))
    return arc_todo_client.format_result(data)


@register_tool(
    key="get_knowledge",
    group="knowledge",
    display_name="Get knowledge",
    description="Fetch one knowledge entry in the selected scope.",
    sort_order=31,
    input_model=KnowledgeEntryInput,
)
async def get_knowledge(input: KnowledgeEntryInput) -> str:
    data = await arc_todo_client.request("GET", _knowledge_entry_path(input))
    return arc_todo_client.format_result(data)


@register_tool(
    key="create_knowledge",
    group="knowledge",
    display_name="Create knowledge",
    description="Create a knowledge entry in the selected scope.",
    sort_order=32,
    input_model=CreateKnowledgeInput,
)
async def create_knowledge(input: CreateKnowledgeInput) -> str:
    data = await arc_todo_client.request(
        "POST",
        _knowledge_collection_path(input),
        json_body={"title": input.title, "content": input.content},
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="update_knowledge",
    group="knowledge",
    display_name="Update knowledge",
    description="Update a knowledge entry in the selected scope.",
    sort_order=33,
    input_model=UpdateKnowledgeInput,
)
async def update_knowledge(input: UpdateKnowledgeInput) -> str:
    body = {
        k: v
        for k, v in {"title": input.title, "content": input.content}.items()
        if v is not None
    }
    data = await arc_todo_client.request(
        "PATCH",
        _knowledge_entry_path(input),
        json_body=body,
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="delete_knowledge",
    group="knowledge",
    display_name="Delete knowledge",
    description="Delete a knowledge entry in the selected scope.",
    sort_order=34,
    input_model=KnowledgeEntryInput,
)
async def delete_knowledge(input: KnowledgeEntryInput) -> str:
    await arc_todo_client.request("DELETE", _knowledge_entry_path(input))
    return '{"deleted": true}'


@register_tool(
    key="list_knowledge_attachments",
    group="knowledge",
    display_name="List knowledge attachments",
    description="List attachments for a knowledge entry.",
    sort_order=35,
    input_model=ListAttachmentsInput,
)
async def list_knowledge_attachments(input: ListAttachmentsInput) -> str:
    params = {
        k: v
        for k, v in {
            "fileName": input.file_name,
            "mimeType": input.mime_type,
            "tag": input.tag,
        }.items()
        if v is not None
    }
    data = await arc_todo_client.request(
        "GET",
        _attachments_base_path(input),
        params=params,
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="upload_knowledge_attachment",
    group="knowledge",
    display_name="Upload knowledge attachment",
    description="Upload a base64-encoded file attachment to a knowledge entry.",
    sort_order=36,
    input_model=UploadAttachmentInput,
)
async def upload_knowledge_attachment(input: UploadAttachmentInput) -> str:
    content = base64.b64decode(input.content_base64)
    form_fields: dict[str, str] = {}
    if input.description:
        form_fields["description"] = input.description
    if input.tags:
        form_fields["tags"] = input.tags
    data = await arc_todo_client.upload_multipart(
        _attachments_base_path(input),
        file_field="file",
        filename=input.filename,
        content=content,
        mime_type=input.mime_type,
        form_fields=form_fields,
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="download_knowledge_attachment",
    group="knowledge",
    display_name="Download knowledge attachment",
    description="Download an attachment and return base64-encoded content.",
    sort_order=37,
    input_model=DownloadAttachmentInput,
)
async def download_knowledge_attachment(input: DownloadAttachmentInput) -> str:
    content, mime_type, filename = await arc_todo_client.download(
        f"{_attachments_base_path(input)}/{input.attachment_id}/download",
    )
    payload = {
        "filename": filename,
        "mimeType": mime_type,
        "sizeBytes": len(content),
        "contentBase64": base64.b64encode(content).decode("ascii"),
    }
    return arc_todo_client.format_result(payload)


@register_tool(
    key="delete_knowledge_attachment",
    group="knowledge",
    display_name="Delete knowledge attachment",
    description="Delete an attachment from a knowledge entry.",
    sort_order=38,
    input_model=DeleteAttachmentInput,
)
async def delete_knowledge_attachment(input: DeleteAttachmentInput) -> str:
    await arc_todo_client.request(
        "DELETE",
        f"{_attachments_base_path(input)}/{input.attachment_id}",
    )
    return '{"deleted": true}'


@register_tool(
    key="retrieve_knowledge",
    group="rag",
    display_name="Retrieve knowledge",
    description=(
        "Search indexed Arc Todo knowledge for relevant chunks. "
        "Omit scope ids for general knowledge; provide organization_id for org scope; "
        "organization_id + project_id for project scope (includes general + org + project chunks); "
        "person_id for person scope."
    ),
    sort_order=40,
    input_model=RetrieveKnowledgeInput,
)
async def retrieve_knowledge(input: RetrieveKnowledgeInput) -> str:
    if input.project_id and not input.organization_id:
        raise ValueError("organization_id is required when project_id is provided")

    token = require_caller_token()
    try:
        data = await rag_client.retrieve(
            token=token,
            question=input.question,
            organization_id=input.organization_id,
            project_id=input.project_id,
            person_id=input.person_id,
            top_k=input.top_k,
            max_context_tokens=input.max_context_tokens,
        )
    except RagClientError as exc:
        if exc.status_code == 503:
            return arc_todo_client.format_result({"error": "RAG is disabled"})
        raise ValueError(str(exc)) from exc
    return arc_todo_client.format_result(data)


def _diagrams_collection_path(organization_id: str, project_id: str) -> str:
    return f"/organizations/{organization_id}/projects/{project_id}/diagrams"


def _diagram_path(organization_id: str, project_id: str, diagram_id: str) -> str:
    return f"{_diagrams_collection_path(organization_id, project_id)}/{diagram_id}"


@register_tool(
    key="list_project_diagrams",
    group="diagrams",
    display_name="List project diagrams",
    description="List Excalidraw diagrams for a project (id, title, thumbnail, timestamps).",
    sort_order=50,
    input_model=ListProjectDiagramsInput,
)
async def list_project_diagrams(input: ListProjectDiagramsInput) -> str:
    data = await arc_todo_client.request(
        "GET",
        _diagrams_collection_path(input.organization_id, input.project_id),
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="get_project_diagram",
    group="diagrams",
    display_name="Get project diagram",
    description="Fetch one project diagram including Excalidraw scene_json.",
    sort_order=51,
    input_model=GetProjectDiagramInput,
)
async def get_project_diagram(input: GetProjectDiagramInput) -> str:
    data = await arc_todo_client.request(
        "GET",
        _diagram_path(input.organization_id, input.project_id, input.diagram_id),
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="create_project_diagram",
    group="diagrams",
    display_name="Create project diagram",
    description="Create a project Excalidraw diagram with a title and optional scene_json.",
    sort_order=52,
    input_model=CreateProjectDiagramInput,
)
async def create_project_diagram(input: CreateProjectDiagramInput) -> str:
    body: dict[str, Any] = {"title": input.title}
    if input.scene_json is not None:
        body["sceneJson"] = input.scene_json
    if input.thumbnail is not None:
        body["thumbnail"] = input.thumbnail
    data = await arc_todo_client.request(
        "POST",
        _diagrams_collection_path(input.organization_id, input.project_id),
        json_body=body,
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="update_project_diagram",
    group="diagrams",
    display_name="Update project diagram",
    description="Update a project diagram title and/or Excalidraw scene_json.",
    sort_order=53,
    input_model=UpdateProjectDiagramInput,
)
async def update_project_diagram(input: UpdateProjectDiagramInput) -> str:
    body = {
        k: v
        for k, v in {
            "title": input.title,
            "sceneJson": input.scene_json,
            "thumbnail": input.thumbnail,
        }.items()
        if v is not None
    }
    data = await arc_todo_client.request(
        "PATCH",
        _diagram_path(input.organization_id, input.project_id, input.diagram_id),
        json_body=body,
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="delete_project_diagram",
    group="diagrams",
    display_name="Delete project diagram",
    description="Delete a project Excalidraw diagram.",
    sort_order=54,
    input_model=GetProjectDiagramInput,
)
async def delete_project_diagram(input: GetProjectDiagramInput) -> str:
    await arc_todo_client.request(
        "DELETE",
        _diagram_path(input.organization_id, input.project_id, input.diagram_id),
    )
    return '{"deleted": true}'


def _qa_info_path(organization_id: str, project_id: str) -> str:
    return f"/organizations/{organization_id}/projects/{project_id}/qa-info"


@register_tool(
    key="get_project_qa_info",
    group="qa",
    display_name="Get project QA info",
    description="Fetch the project QA info profile (environments, test users, notes). Empty when none is saved yet.",
    sort_order=80,
    input_model=GetProjectQaInfoInput,
)
async def get_project_qa_info(input: GetProjectQaInfoInput) -> str:
    data = await arc_todo_client.request(
        "GET",
        _qa_info_path(input.organization_id, input.project_id),
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="update_project_qa_info",
    group="qa",
    display_name="Update project QA info",
    description="Create or replace the project QA info profile. Omit a field to keep the current value. No password field.",
    sort_order=81,
    input_model=UpdateProjectQaInfoInput,
)
async def update_project_qa_info(input: UpdateProjectQaInfoInput) -> str:
    body: dict[str, Any] = {}
    if input.environments is not None:
        body["environments"] = [
            {
                key: value
                for key, value in {
                    "name": item.name,
                    "url": item.url,
                    "notes": item.notes,
                }.items()
                if value is not None
            }
            for item in input.environments
        ]
    if input.users is not None:
        body["users"] = [
            {
                key: value
                for key, value in {
                    "label": item.label,
                    "email": item.email,
                    "howToSignIn": item.how_to_sign_in,
                    "notes": item.notes,
                }.items()
                if value is not None
            }
            for item in input.users
        ]
    if input.notes is not None:
        body["notes"] = input.notes
    data = await arc_todo_client.request(
        "PUT",
        _qa_info_path(input.organization_id, input.project_id),
        json_body=body,
    )
    return arc_todo_client.format_result(data)


def _wireframes_collection_path(organization_id: str, project_id: str) -> str:
    return f"/organizations/{organization_id}/projects/{project_id}/wireframes"


def _wireframe_path(
    organization_id: str, project_id: str, wireframe_id: str
) -> str:
    return f"{_wireframes_collection_path(organization_id, project_id)}/{wireframe_id}"


@register_tool(
    key="list_project_wireframes",
    group="wireframes",
    display_name="List project wireframes",
    description="List HTML wireframe prototypes for a project (id, title, timestamps; omits html).",
    sort_order=60,
    input_model=ListProjectWireframesInput,
)
async def list_project_wireframes(input: ListProjectWireframesInput) -> str:
    data = await arc_todo_client.request(
        "GET",
        _wireframes_collection_path(input.organization_id, input.project_id),
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="get_project_wireframe",
    group="wireframes",
    display_name="Get project wireframe",
    description="Fetch one project wireframe including the HTML document.",
    sort_order=61,
    input_model=GetProjectWireframeInput,
)
async def get_project_wireframe(input: GetProjectWireframeInput) -> str:
    data = await arc_todo_client.request(
        "GET",
        _wireframe_path(
            input.organization_id, input.project_id, input.wireframe_id
        ),
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="create_project_wireframe",
    group="wireframes",
    display_name="Create project wireframe",
    description="Create a project HTML wireframe with a title and optional html document.",
    sort_order=62,
    input_model=CreateProjectWireframeInput,
)
async def create_project_wireframe(input: CreateProjectWireframeInput) -> str:
    body: dict[str, Any] = {"title": input.title}
    if input.html is not None:
        body["html"] = input.html
    data = await arc_todo_client.request(
        "POST",
        _wireframes_collection_path(input.organization_id, input.project_id),
        json_body=body,
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="update_project_wireframe",
    group="wireframes",
    display_name="Update project wireframe",
    description="Update a project wireframe title and/or HTML document.",
    sort_order=63,
    input_model=UpdateProjectWireframeInput,
)
async def update_project_wireframe(input: UpdateProjectWireframeInput) -> str:
    body = {
        k: v
        for k, v in {
            "title": input.title,
            "html": input.html,
        }.items()
        if v is not None
    }
    data = await arc_todo_client.request(
        "PATCH",
        _wireframe_path(
            input.organization_id, input.project_id, input.wireframe_id
        ),
        json_body=body,
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="delete_project_wireframe",
    group="wireframes",
    display_name="Delete project wireframe",
    description="Delete a project HTML wireframe.",
    sort_order=64,
    input_model=GetProjectWireframeInput,
)
async def delete_project_wireframe(input: GetProjectWireframeInput) -> str:
    await arc_todo_client.request(
        "DELETE",
        _wireframe_path(
            input.organization_id, input.project_id, input.wireframe_id
        ),
    )
    return '{"deleted": true}'


def _name_sessions_collection_path(organization_id: str, project_id: str) -> str:
    return f"/organizations/{organization_id}/projects/{project_id}/name-sessions"


def _name_session_path(
    organization_id: str, project_id: str, name_session_id: str
) -> str:
    return f"{_name_sessions_collection_path(organization_id, project_id)}/{name_session_id}"


@register_tool(
    key="list_project_name_sessions",
    group="names",
    display_name="List project name sessions",
    description="List naming sessions for a project (id, title, recommendedName, timestamps; omits bulky candidates).",
    sort_order=70,
    input_model=ListProjectNameSessionsInput,
)
async def list_project_name_sessions(input: ListProjectNameSessionsInput) -> str:
    data = await arc_todo_client.request(
        "GET",
        _name_sessions_collection_path(input.organization_id, input.project_id),
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="get_name_session",
    group="names",
    display_name="Get name session",
    description="Fetch one naming session including product description, lanes, candidates, evidence, and recommendation.",
    sort_order=71,
    input_model=GetNameSessionInput,
)
async def get_name_session(input: GetNameSessionInput) -> str:
    data = await arc_todo_client.request(
        "GET",
        _name_session_path(
            input.organization_id, input.project_id, input.name_session_id
        ),
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="create_name_session",
    group="names",
    display_name="Create name session",
    description="Create a project naming session with a required title.",
    sort_order=72,
    input_model=CreateNameSessionInput,
)
async def create_name_session(input: CreateNameSessionInput) -> str:
    body: dict[str, Any] = {"title": input.title}
    if input.naming_goal is not None:
        body["namingGoal"] = input.naming_goal
    if input.product_description is not None:
        body["productDescription"] = input.product_description
    data = await arc_todo_client.request(
        "POST",
        _name_sessions_collection_path(input.organization_id, input.project_id),
        json_body=body,
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="update_name_session",
    group="names",
    display_name="Update name session",
    description="Update naming session title, goal, or product description.",
    sort_order=73,
    input_model=UpdateNameSessionInput,
)
async def update_name_session(input: UpdateNameSessionInput) -> str:
    body = {
        k: v
        for k, v in {
            "title": input.title,
            "namingGoal": input.naming_goal,
            "productDescription": input.product_description,
        }.items()
        if v is not None
    }
    data = await arc_todo_client.request(
        "PATCH",
        _name_session_path(
            input.organization_id, input.project_id, input.name_session_id
        ),
        json_body=body,
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="add_name_candidates",
    group="names",
    display_name="Add name candidates",
    description="Add up to 20 name candidates to a session. Source is recorded as MCP. Do not claim trademark or legal clearance.",
    sort_order=74,
    input_model=AddNameCandidatesInput,
)
async def add_name_candidates(input: AddNameCandidatesInput) -> str:
    body = {
        "source": "mcp",
        "candidates": [
            {
                k: v
                for k, v in {
                    "name": item.name,
                    "family": item.family,
                    "laneId": item.lane,
                    "rationale": item.rationale,
                }.items()
                if v is not None
            }
            for item in input.candidates
        ],
    }
    data = await arc_todo_client.request(
        "POST",
        f"{_name_session_path(input.organization_id, input.project_id, input.name_session_id)}/candidates",
        json_body=body,
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="check_name_candidate",
    group="names",
    display_name="Check name candidate",
    description="Run DNS/RDAP checks for a candidate. Does not register or buy a domain.",
    sort_order=75,
    input_model=CheckNameCandidateInput,
)
async def check_name_candidate(input: CheckNameCandidateInput) -> str:
    session = await arc_todo_client.request(
        "GET",
        _name_session_path(
            input.organization_id, input.project_id, input.name_session_id
        ),
    )
    candidates = session.get("candidates") if isinstance(session, dict) else None
    name = None
    if isinstance(candidates, list):
        for item in candidates:
            if isinstance(item, dict) and item.get("id") == input.candidate_id:
                name = item.get("name")
                break
    if not name:
        return '{"error": "Candidate not found"}'
    data = await arc_todo_client.request(
        "POST",
        f"{_name_session_path(input.organization_id, input.project_id, input.name_session_id)}/check",
        json_body={"name": name},
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="recommend_name_candidate",
    group="names",
    display_name="Recommend name candidate",
    description="Recommend a candidate with a decision note. Never claim trademark or legal clearance.",
    sort_order=76,
    input_model=RecommendNameCandidateInput,
)
async def recommend_name_candidate(input: RecommendNameCandidateInput) -> str:
    data = await arc_todo_client.request(
        "POST",
        f"{_name_session_path(input.organization_id, input.project_id, input.name_session_id)}/recommend",
        json_body={
            "candidateId": input.candidate_id,
            "decisionNote": input.decision_note,
        },
    )
    return arc_todo_client.format_result(data)
