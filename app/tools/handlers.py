from __future__ import annotations

import base64

from app.arc_todo_client import arc_todo_client
from app.task_id_resolver import is_uuid, resolve_task_scope
from app.tool_registry import (
    CreateKnowledgeInput,
    CreateProjectInput,
    CreateTaskInput,
    DeleteAttachmentInput,
    DownloadAttachmentInput,
    EmptyInput,
    GetOrganizationInput,
    GetPersonInput,
    GetProjectInput,
    GetTaskInput,
    KnowledgeEntryInput,
    KnowledgeScopeInput,
    ListAttachmentsInput,
    ListPersonsInput,
    ListProjectsInput,
    ListTasksInput,
    ProjectTaskScopeInput,
    UpdateKnowledgeInput,
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
    key="list_projects",
    group="context",
    display_name="List projects",
    description="List projects in an organization.",
    sort_order=12,
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
    sort_order=13,
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
    sort_order=14,
    input_model=GetProjectInput,
)
async def get_project(input: GetProjectInput) -> str:
    data = await arc_todo_client.request(
        "GET",
        f"/organizations/{input.organization_id}/projects/{input.project_id}",
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="list_persons",
    group="context",
    display_name="List persons",
    description="List persons globally or within an organization.",
    sort_order=15,
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
    sort_order=16,
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
    if input.status is not None:
        body["status"] = input.status
    if input.criticity is not None:
        body["criticity"] = input.criticity
    if input.due_date is not None:
        body["dueDate"] = input.due_date
    if input.parent_task_id is not None:
        body["parentTaskId"] = input.parent_task_id
    return body


@register_tool(
    key="list_tasks",
    group="tasks",
    display_name="List tasks",
    description="List tasks across organizations with optional filters including parent_task_id.",
    sort_order=20,
    input_model=ListTasksInput,
)
async def list_tasks(input: ListTasksInput) -> str:
    params = {
        k: v
        for k, v in {
            "organizationId": input.organization_id,
            "projectId": input.project_id,
            "status": input.status,
            "criticity": input.criticity,
            "parentTaskId": input.parent_task_id,
        }.items()
        if v is not None
    }
    data = await arc_todo_client.request("GET", "/tasks", params=params)
    return arc_todo_client.format_result(data)


@register_tool(
    key="list_project_tasks",
    group="tasks",
    display_name="List project tasks",
    description="List tasks within a specific project.",
    sort_order=21,
    input_model=ProjectTaskScopeInput,
)
async def list_project_tasks(input: ProjectTaskScopeInput) -> str:
    data = await arc_todo_client.request(
        "GET",
        f"/organizations/{input.organization_id}/projects/{input.project_id}/tasks",
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="get_task",
    group="tasks",
    display_name="Get task",
    description="Fetch one task by organization, project, and task ID.",
    sort_order=22,
    input_model=GetTaskInput,
)
async def get_task(input: GetTaskInput) -> str:
    resolved = await resolve_task_scope(arc_todo_client, input.task_id)
    org_id = resolved.get("organization_id") or input.organization_id
    project_id = resolved.get("project_id") or input.project_id
    task_id = resolved["task_id"]
    data = await arc_todo_client.request(
        "GET",
        f"/organizations/{org_id}/projects/{project_id}/tasks/{task_id}",
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="create_task",
    group="tasks",
    display_name="Create task",
    description="Create a task in a project. Optional parent_task_id creates a direct subtask.",
    sort_order=23,
    input_model=CreateTaskInput,
)
async def create_task(input: CreateTaskInput) -> str:
    body = _task_body(input)
    if input.parent_task_id and not is_uuid(input.parent_task_id):
        parent = await resolve_task_scope(arc_todo_client, input.parent_task_id)
        body["parentTaskId"] = parent["task_id"]
    data = await arc_todo_client.request(
        "POST",
        f"/organizations/{input.organization_id}/projects/{input.project_id}/tasks",
        json_body=body,
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="update_task",
    group="tasks",
    display_name="Update task",
    description="Update a task in a project. Set parent_task_id to attach as subtask or null to detach.",
    sort_order=24,
    input_model=UpdateTaskInput,
)
async def update_task(input: UpdateTaskInput) -> str:
    resolved = await resolve_task_scope(arc_todo_client, input.task_id)
    org_id = resolved.get("organization_id") or input.organization_id
    project_id = resolved.get("project_id") or input.project_id
    task_id = resolved["task_id"]
    body = _task_body(input)
    if input.parent_task_id and not is_uuid(input.parent_task_id):
        parent = await resolve_task_scope(arc_todo_client, input.parent_task_id)
        body["parentTaskId"] = parent["task_id"]
    data = await arc_todo_client.request(
        "PATCH",
        f"/organizations/{org_id}/projects/{project_id}/tasks/{task_id}",
        json_body=body,
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="delete_task",
    group="tasks",
    display_name="Delete task",
    description="Delete a task from a project.",
    sort_order=25,
    input_model=GetTaskInput,
)
async def delete_task(input: GetTaskInput) -> str:
    resolved = await resolve_task_scope(arc_todo_client, input.task_id)
    org_id = resolved.get("organization_id") or input.organization_id
    project_id = resolved.get("project_id") or input.project_id
    task_id = resolved["task_id"]
    await arc_todo_client.request(
        "DELETE",
        f"/organizations/{org_id}/projects/{project_id}/tasks/{task_id}",
    )
    return '{"deleted": true}'


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
