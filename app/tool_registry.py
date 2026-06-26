from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Coroutine

from pydantic import BaseModel, Field


@dataclass(frozen=True)
class ToolDefinition:
    key: str
    group: str
    display_name: str
    description: str
    default_enabled: bool
    sort_order: int
    input_model: type[BaseModel] | None
    handler: Callable[..., Coroutine[Any, Any, str]]


MCP_TOOL_REGISTRY: list[ToolDefinition] = []


def register_tool(
    *,
    key: str,
    group: str,
    display_name: str,
    description: str,
    default_enabled: bool = True,
    sort_order: int = 0,
    input_model: type[BaseModel] | None = None,
) -> Callable[[Callable[..., Coroutine[Any, Any, str]]], Callable[..., Coroutine[Any, Any, str]]]:
    def decorator(
        handler: Callable[..., Coroutine[Any, Any, str]],
    ) -> Callable[..., Coroutine[Any, Any, str]]:
        MCP_TOOL_REGISTRY.append(
            ToolDefinition(
                key=key,
                group=group,
                display_name=display_name,
                description=description,
                default_enabled=default_enabled,
                sort_order=sort_order,
                input_model=input_model,
                handler=handler,
            )
        )
        return handler

    return decorator


def registry_entry_dict(tool: ToolDefinition) -> dict[str, Any]:
    return {
        "key": tool.key,
        "group": tool.group,
        "displayName": tool.display_name,
        "description": tool.description,
        "defaultEnabled": tool.default_enabled,
        "sortOrder": tool.sort_order,
    }


class EmptyInput(BaseModel):
    pass


class OrganizationIdInput(BaseModel):
    organization_id: str = Field(description="Organization UUID")


class GetOrganizationInput(BaseModel):
    organization_id: str = Field(description="Organization UUID")


class ListOrganizationMembersInput(BaseModel):
    organization_id: str = Field(description="Organization UUID")


class CreateOrganizationUserInput(BaseModel):
    organization_id: str = Field(description="Organization UUID")
    username: str
    password: str = Field(min_length=6)
    role: str | None = Field(
        default=None,
        description="owner | admin | member",
    )


class AddOrganizationMemberInput(BaseModel):
    organization_id: str = Field(description="Organization UUID")
    username: str
    role: str | None = Field(
        default=None,
        description="owner | admin | member",
    )


class ListOrganizationActivityInput(BaseModel):
    organization_id: str = Field(description="Organization UUID")
    user_id: str | None = Field(default=None, description="Filter by actor user UUID")
    limit: int | None = Field(default=None, ge=1, le=100)
    offset: int | None = Field(default=None, ge=0)


class ListProjectsInput(BaseModel):
    organization_id: str = Field(description="Organization UUID")


class CreateProjectInput(BaseModel):
    organization_id: str = Field(description="Organization UUID")
    name: str
    description: str | None = None
    color: str | None = Field(
        default=None,
        description="Optional hex color (e.g. #8778a3)",
    )


class GetProjectInput(BaseModel):
    organization_id: str = Field(description="Organization UUID")
    project_id: str = Field(description="Project UUID")


class ListPersonsInput(BaseModel):
    organization_id: str | None = Field(
        default=None,
        description="Optional organization UUID. Omit for global persons.",
    )


class GetPersonInput(BaseModel):
    organization_id: str | None = Field(
        default=None,
        description="Optional organization UUID. Omit for global person lookup.",
    )
    person_id: str = Field(description="Person UUID")


class ListTasksInput(BaseModel):
    organization_id: str | None = None
    project_id: str | None = None
    status: str | None = Field(
        default=None,
        description="todo | in_progress | dev_test | qa_test | done",
    )
    criticity: str | None = Field(
        default=None,
        description="low | medium | high | critical",
    )
    parent_task_id: str | None = Field(
        default=None,
        description="Filter by parent task UUID",
    )
    category: str | None = Field(
        default=None,
        description="coding | meeting | design | marketing | other",
    )
    is_bug: bool | None = Field(
        default=None,
        description="Filter tasks flagged as bugs",
    )


class ProjectTaskScopeInput(BaseModel):
    organization_id: str
    project_id: str


class GetTaskInput(ProjectTaskScopeInput):
    task_id: str = Field(
        description="Task UUID or friendly ID like arc-1 or #arc-1",
    )


class CreateTaskInput(ProjectTaskScopeInput):
    title: str
    description: str | None = None
    business_description: str | None = Field(
        default=None,
        description="Business intent, scope, and acceptance criteria",
    )
    plan_code_description: str | None = Field(
        default=None,
        description="Technical execution plan for agents or developers",
    )
    test_description: str | None = Field(
        default=None,
        description="Verification steps for Dev Test, QA Test, and final checks",
    )
    status: str = "todo"
    criticity: str = "medium"
    due_date: str | None = None
    parent_task_id: str | None = Field(
        default=None,
        description="Parent task UUID or friendly ID for one-level subtasks",
    )
    category: str = Field(
        default="other",
        description="coding | meeting | design | marketing | other",
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Structured metadata. For coding tasks: repositoryUrl, branch, commits, "
            "pullRequestUrl, deploymentUrl, implementationNotes"
        ),
    )
    is_bug: bool | None = Field(
        default=None,
        description="Flag task as bug. Setting true moves status to todo.",
    )
    bug_reason: str | None = Field(
        default=None,
        description="Optional reason when flagging a task as bug",
    )
    qa_checklist_state: dict[str, Any] | None = Field(
        default=None,
        description="QA checklist progress with checkedItemIds array",
    )


class UpdateTaskInput(GetTaskInput):
    title: str | None = None
    description: str | None = None
    business_description: str | None = Field(
        default=None,
        description="Business intent, scope, and acceptance criteria",
    )
    plan_code_description: str | None = Field(
        default=None,
        description="Technical execution plan for agents or developers",
    )
    test_description: str | None = Field(
        default=None,
        description="Verification steps for Dev Test, QA Test, and final checks",
    )
    status: str | None = None
    criticity: str | None = None
    due_date: str | None = None
    parent_task_id: str | None = Field(
        default=None,
        description="Parent task UUID or friendly ID; null detaches subtask",
    )
    category: str | None = Field(
        default=None,
        description="coding | meeting | design | marketing | other",
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Structured metadata. For coding tasks: repositoryUrl, branch, commits, "
            "pullRequestUrl, deploymentUrl, implementationNotes"
        ),
    )
    is_bug: bool | None = Field(
        default=None,
        description="Flag task as bug. Setting true moves status to todo.",
    )
    bug_reason: str | None = Field(
        default=None,
        description="Optional reason when flagging a task as bug",
    )
    qa_checklist_state: dict[str, Any] | None = Field(
        default=None,
        description="QA checklist progress with checkedItemIds array",
    )


class KnowledgeScopeInput(BaseModel):
    scope: str = Field(description="general | organization | project | person")
    organization_id: str | None = None
    project_id: str | None = None
    person_id: str | None = None
    file_name: str | None = None
    mime_type: str | None = None
    has_attachments: bool | None = None


class KnowledgeEntryInput(KnowledgeScopeInput):
    knowledge_id: str


class CreateKnowledgeInput(KnowledgeScopeInput):
    title: str
    content: str


class UpdateKnowledgeInput(KnowledgeEntryInput):
    title: str | None = None
    content: str | None = None


class ListAttachmentsInput(KnowledgeEntryInput):
    file_name: str | None = None
    mime_type: str | None = None
    tag: str | None = None


class UploadAttachmentInput(KnowledgeEntryInput):
    filename: str
    mime_type: str
    content_base64: str
    description: str | None = None
    tags: str | None = None


class DownloadAttachmentInput(KnowledgeEntryInput):
    attachment_id: str


class DeleteAttachmentInput(DownloadAttachmentInput):
    pass


class RetrieveKnowledgeInput(BaseModel):
    question: str = Field(description="Natural-language question to search indexed knowledge")
    organization_id: str | None = Field(
        default=None,
        description="Organization UUID. With project_id selects project scope; alone selects organization scope.",
    )
    project_id: str | None = Field(
        default=None,
        description="Project UUID. Requires organization_id for project-scoped retrieval.",
    )
    person_id: str | None = Field(
        default=None,
        description="Person UUID for person-scoped retrieval (includes general + person knowledge).",
    )
    top_k: int | None = Field(
        default=None,
        description="Max chunks to return (default from RAG settings)",
    )
    max_context_tokens: int | None = Field(
        default=None,
        description="Token budget for context (default from RAG settings)",
    )
