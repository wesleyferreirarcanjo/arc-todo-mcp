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
    handler: Callable[..., Coroutine[Any, Any, Any]]


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
) -> Callable[[Callable[..., Coroutine[Any, Any, Any]]], Callable[..., Coroutine[Any, Any, Any]]]:
    def decorator(
        handler: Callable[..., Coroutine[Any, Any, Any]],
    ) -> Callable[..., Coroutine[Any, Any, Any]]:
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
    organization_id: str | None = Field(
        default=None,
        description="Organization UUID or slug. Omit to use the last board from this MCP session.",
    )
    project_id: str | None = Field(
        default=None,
        description="Project UUID, acronym (ski), slug, or name. Omit to use the last board.",
    )
    project: str | None = Field(
        default=None,
        description="Project acronym, slug, or name (e.g. ski, skill, cursor).",
    )
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
        description="Filter by parent task UUID or friendly ID",
    )
    category: str | None = Field(
        default=None,
        description="coding | meeting | design | marketing | other",
    )
    is_bug: bool | None = Field(
        default=None,
        description="Filter tasks flagged as bugs",
    )
    q: str | None = Field(
        default=None,
        description="Case-insensitive title substring. Use this for duplicate checks instead of listing the whole board.",
    )
    limit: int | None = Field(
        default=None,
        ge=1,
        le=200,
        description="Max rows to return (1-200).",
    )
    parents_only: bool | None = Field(
        default=None,
        description="If true, return only parent tasks (parentTaskId is null).",
    )
    include: str = Field(
        default="summary",
        description=(
            "summary | plan | qa | full. Default summary. "
            "summary=ids/flags/subtask stubs; plan=+business+planCode; "
            "qa=+testDescription+checklist+bug fields; full=all except duplicate description. "
            "List rows never nest project/organization objects."
        ),
    )


class ProjectTaskScopeInput(BaseModel):
    organization_id: str
    project_id: str


class ListProjectTasksInput(BaseModel):
    organization_id: str | None = Field(
        default=None,
        description="Organization UUID or slug. Optional when project is an acronym/slug or after get_task in this session.",
    )
    project_id: str | None = Field(
        default=None,
        description="Project UUID, acronym, slug, or name.",
    )
    project: str | None = Field(
        default=None,
        description="Project acronym, slug, or name (e.g. ski, skill, cursor).",
    )
    status: str | None = Field(
        default=None,
        description="todo | in_progress | dev_test | qa_test | done. Omit to include every status.",
    )
    q: str | None = Field(
        default=None,
        description="Case-insensitive title substring for duplicate checks.",
    )
    limit: int | None = Field(
        default=None,
        ge=1,
        le=200,
        description="Max rows to return (1-200).",
    )
    parents_only: bool | None = Field(
        default=None,
        description="If true, return only parent tasks (parentTaskId is null).",
    )
    include: str = Field(
        default="summary",
        description=(
            "summary | plan | qa | full. Default summary. "
            "summary=ids/flags/subtask stubs; plan=+business+planCode; "
            "qa=+testDescription+checklist+bug fields; full=all except duplicate description."
        ),
    )


class OptionalTaskScopeInput(BaseModel):
    organization_id: str | None = Field(
        default=None,
        description=(
            "Organization UUID. Required when task_id is a UUID; "
            "omit for friendly IDs like arc-1 or #arc-1."
        ),
    )
    project_id: str | None = Field(
        default=None,
        description=(
            "Project UUID. Required when task_id is a UUID; "
            "omit for friendly IDs like arc-1 or #arc-1."
        ),
    )
    task_id: str = Field(
        description="Task UUID or friendly ID like arc-1 or #arc-1",
    )


class GetTaskInput(OptionalTaskScopeInput):
    include: str = Field(
        default="plan",
        description=(
            "summary | plan | qa | full. Default plan (business + plan/code, no QA essay). "
            "summary=ids/flags/subtask stubs; qa=+testDescription+checklist+bug fields; "
            "full=all except duplicate description."
        ),
    )


class AddTaskCommentInput(OptionalTaskScopeInput):
    body: str = Field(description="Comment text to post on the task")


class DownloadTaskEvidenceInput(OptionalTaskScopeInput):
    evidence_id: str = Field(description="Task evidence (image/video) UUID")


class CreateTaskInput(BaseModel):
    organization_id: str | None = Field(
        default=None,
        description="Organization UUID or slug. Optional when project is an acronym/slug.",
    )
    project_id: str | None = Field(
        default=None,
        description="Project UUID. Prefer `project` with an acronym or slug.",
    )
    project: str | None = Field(
        default=None,
        description="Project acronym, slug, or name (e.g. ski, skill, cursor). Preferred over UUIDs.",
    )
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
        description=(
            "Report or solve a bug. true = mark as open bug (requires bug_reason, "
            "moves status to todo); false = mark bug solved."
        ),
    )
    bug_reason: str | None = Field(
        default=None,
        description="Required non-blank reason when reporting a bug (is_bug=true)",
    )
    qa_checklist_state: dict[str, Any] | None = Field(
        default=None,
        description=(
            "QA checklist state: checkedItemIds, buggedItemIds, buggedItemNotes"
        ),
    )
    include: str = Field(
        default="summary",
        description=(
            "Response shape: summary | plan | qa | full. Default summary "
            "(the agent already sent the text)."
        ),
    )


class UpdateTaskInput(OptionalTaskScopeInput):
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
        description=(
            "Report or solve a bug. true = mark as open bug (requires bug_reason, "
            "moves status to todo); false = mark bug solved."
        ),
    )
    bug_reason: str | None = Field(
        default=None,
        description="Required non-blank reason when reporting a bug (is_bug=true)",
    )
    qa_checklist_state: dict[str, Any] | None = Field(
        default=None,
        description=(
            "QA checklist state: checkedItemIds, buggedItemIds, buggedItemNotes"
        ),
    )
    include: str = Field(
        default="summary",
        description=(
            "Response shape: summary | plan | qa | full. Default summary "
            "(the agent already sent the text)."
        ),
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


class ListProjectDiagramsInput(BaseModel):
    organization_id: str = Field(description="Organization UUID")
    project_id: str = Field(description="Project UUID")


class GetProjectDiagramInput(ListProjectDiagramsInput):
    diagram_id: str = Field(description="Project diagram UUID")


class CreateProjectDiagramInput(ListProjectDiagramsInput):
    title: str = Field(description="Diagram title (required, non-empty)")
    scene_json: dict[str, Any] | None = Field(
        default=None,
        description="Optional Excalidraw scene JSON (elements, appState, files)",
    )
    thumbnail: str | None = Field(
        default=None,
        description="Optional base64 data-URL thumbnail for list cards",
    )


class UpdateProjectDiagramInput(GetProjectDiagramInput):
    title: str | None = Field(default=None, description="New diagram title")
    scene_json: dict[str, Any] | None = Field(
        default=None,
        description="Excalidraw scene JSON (elements, appState, files)",
    )
    thumbnail: str | None = Field(
        default=None,
        description="Optional base64 data-URL thumbnail for list cards",
    )


class ListProjectWireframesInput(BaseModel):
    organization_id: str = Field(description="Organization UUID")
    project_id: str = Field(description="Project UUID")


class GetProjectWireframeInput(ListProjectWireframesInput):
    wireframe_id: str = Field(description="Project wireframe UUID")


class CreateProjectWireframeInput(ListProjectWireframesInput):
    title: str = Field(description="Wireframe title (required, non-empty)")
    html: str | None = Field(
        default=None,
        description="Optional HTML document (inline CSS/JS; may contain several #page- sections). Omitted → two-screen starter.",
    )


class UpdateProjectWireframeInput(GetProjectWireframeInput):
    title: str | None = Field(default=None, description="New wireframe title")
    html: str | None = Field(
        default=None,
        description="HTML document (inline CSS/JS; may contain several #page- sections)",
    )


class ListProjectNameSessionsInput(BaseModel):
    organization_id: str = Field(description="Organization UUID")
    project_id: str = Field(description="Project UUID")


class GetNameSessionInput(ListProjectNameSessionsInput):
    name_session_id: str = Field(description="Name session UUID")


class CreateNameSessionInput(ListProjectNameSessionsInput):
    title: str = Field(description="Session title (required, non-empty)")
    naming_goal: str | None = Field(
        default=None,
        description="Optional naming goal: public_product, company, feature, api, internal_codename, campaign. Omitted defaults to public_product.",
    )
    product_description: dict[str, Any] | None = Field(
        default=None,
        description="Optional product-description canvas JSON",
    )


class UpdateNameSessionInput(GetNameSessionInput):
    title: str | None = Field(default=None, description="New session title")
    naming_goal: str | None = Field(default=None, description="Naming goal")
    product_description: dict[str, Any] | None = Field(
        default=None,
        description="Product-description canvas JSON",
    )


class NameCandidateItemInput(BaseModel):
    name: str = Field(description="Candidate name")
    family: str | None = Field(default=None, description="Optional name family")
    lane: str | None = Field(default=None, description="Optional lane id")
    rationale: str | None = Field(default=None, description="Optional rationale")


class AddNameCandidatesInput(GetNameSessionInput):
    candidates: list[NameCandidateItemInput] = Field(
        description="Candidates to add (max 20)",
        min_length=1,
        max_length=20,
    )


class CheckNameCandidateInput(GetNameSessionInput):
    candidate_id: str = Field(description="Candidate UUID in the session")


class RecommendNameCandidateInput(CheckNameCandidateInput):
    decision_note: str = Field(
        description="Why this name is recommended. Required when evidence is unresolved.",
    )


class GetProjectQaInfoInput(BaseModel):
    organization_id: str = Field(description="Organization UUID")
    project_id: str = Field(description="Project UUID")


class QaEnvironmentInput(BaseModel):
    name: str = Field(description="Environment name")
    url: str = Field(description="http or https URL")
    notes: str | None = Field(default=None, description="Optional notes")


class QaUserInput(BaseModel):
    label: str = Field(description="Role or label for the tester account")
    email: str | None = Field(default=None, description="Optional email")
    how_to_sign_in: str | None = Field(
        default=None,
        description="How to sign in, in words. Maps to howToSignIn. Do not send a password.",
    )
    notes: str | None = Field(default=None, description="Optional notes")


class UpdateProjectQaInfoInput(GetProjectQaInfoInput):
    environments: list[QaEnvironmentInput] | None = Field(
        default=None,
        description="Replace the environments list. Omit to keep the current list.",
    )
    users: list[QaUserInput] | None = Field(
        default=None,
        description="Replace the test-users list. Omit to keep the current list.",
    )
    notes: str | None = Field(
        default=None,
        description="Free-text navigation and conventions. Empty string clears. Omit to keep current.",
    )
