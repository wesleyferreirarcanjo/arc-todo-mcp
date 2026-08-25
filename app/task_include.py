from __future__ import annotations

from typing import Any

INCLUDE_SUMMARY = "summary"
INCLUDE_PLAN = "plan"
INCLUDE_QA = "qa"
INCLUDE_FULL = "full"
VALID_INCLUDES = (INCLUDE_SUMMARY, INCLUDE_PLAN, INCLUDE_QA, INCLUDE_FULL)

INCLUDE_FIELD_DESCRIPTION = (
    "summary | plan | qa | full. "
    "summary=ids/flags/subtask stubs; "
    "plan=+business+planCode; "
    "qa=+testDescription+checklist+bug fields; "
    "full=all fields except duplicate description alias."
)

SUMMARY_KEYS = (
    "id",
    "displayId",
    "title",
    "status",
    "criticity",
    "category",
    "isBug",
    "parentTaskId",
    "dueDate",
    "taskNumber",
    "projectId",
    "organizationId",
    "subtaskProgress",
    "project",
    "organization",
)

PLAN_KEYS = SUMMARY_KEYS + ("businessDescription", "planCodeDescription")

QA_KEYS = SUMMARY_KEYS + (
    "testDescription",
    "qaChecklistState",
    "qaChecklistProgress",
    "bugReason",
    "buggedAt",
    "buggedById",
    "bugReportCount",
    "bugResolveCount",
)

SUBTASK_STUB_KEYS = ("id", "displayId", "title", "status", "isBug")


def normalize_include(value: str | None, default: str) -> str:
    include = (value or default).strip().lower()
    if include not in VALID_INCLUDES:
        allowed = ", ".join(VALID_INCLUDES)
        raise ValueError(f"include must be one of: {allowed}")
    return include


def _pick(task: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return {key: task[key] for key in keys if key in task}


def _stub_subtasks(task: dict[str, Any]) -> list[dict[str, Any]] | None:
    children = task.get("subtasks")
    if not isinstance(children, list):
        return None
    return [
        _pick(child, SUBTASK_STUB_KEYS)
        for child in children
        if isinstance(child, dict)
    ]


def project_task(task: dict[str, Any], include: str) -> dict[str, Any]:
    if include == INCLUDE_FULL:
        projected = {key: value for key, value in task.items() if key != "description"}
        children = projected.get("subtasks")
        if isinstance(children, list):
            projected["subtasks"] = [
                project_task(child, INCLUDE_FULL) if isinstance(child, dict) else child
                for child in children
            ]
        return projected

    if include == INCLUDE_PLAN:
        projected = _pick(task, PLAN_KEYS)
    elif include == INCLUDE_QA:
        projected = _pick(task, QA_KEYS)
    else:
        projected = _pick(task, SUMMARY_KEYS)

    stubs = _stub_subtasks(task)
    if stubs is not None:
        projected["subtasks"] = stubs
    return projected


def project_payload(data: Any, include: str) -> Any:
    if isinstance(data, list):
        return [
            project_task(item, include) if isinstance(item, dict) else item
            for item in data
        ]
    if isinstance(data, dict):
        return project_task(data, include)
    return data
