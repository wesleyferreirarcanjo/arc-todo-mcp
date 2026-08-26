from __future__ import annotations

from typing import Any

from app.caller_auth import get_caller_token
from app.task_id_resolver import is_friendly_task_id, is_uuid, resolve_task_scope

_last_board: dict[str, tuple[str, str]] = {}


def reset_last_board() -> None:
    _last_board.clear()


def remember_board(organization_id: str, project_id: str) -> None:
    token = get_caller_token() or ""
    _last_board[token] = (organization_id, project_id)


def last_board() -> tuple[str, str] | None:
    token = get_caller_token() or ""
    return _last_board.get(token)


def _hint_if_not_uuid(value: str | None) -> str | None:
    if not value or not value.strip():
        return None
    stripped = value.strip()
    return None if is_uuid(stripped) else stripped


async def resolve_board_scope(
    client: Any,
    *,
    organization_id: str | None = None,
    project_id: str | None = None,
    project: str | None = None,
    parent_task_id: str | None = None,
    use_last: bool = False,
    required: bool = True,
) -> tuple[str | None, str | None]:
    org_id = organization_id.strip() if organization_id and is_uuid(organization_id.strip()) else None
    proj_id = project_id.strip() if project_id and is_uuid(project_id.strip()) else None
    project_hint = (project or "").strip() or _hint_if_not_uuid(project_id)
    org_hint = _hint_if_not_uuid(organization_id)

    if org_id and proj_id:
        remember_board(org_id, proj_id)
        return org_id, proj_id

    if (org_id or proj_id) and not project_hint and not org_hint:
        return org_id, proj_id

    if parent_task_id and is_friendly_task_id(parent_task_id):
        resolved = await resolve_task_scope(client, parent_task_id)
        parent_org = resolved.get("organization_id")
        parent_project = resolved.get("project_id")
        if parent_org and parent_project:
            remember_board(parent_org, parent_project)
            return parent_org, parent_project

    if project_hint or org_hint:
        params = {
            k: v
            for k, v in {
                "projectHint": project_hint,
                "organizationHint": org_hint or project_hint,
            }.items()
            if v
        }
        data = await client.request("GET", "/scope/resolve", params=params)
        status = data.get("status") if isinstance(data, dict) else None
        if status == "resolved":
            org = data["organization"]["id"]
            proj = data["project"]["id"]
            remember_board(org, proj)
            return org, proj
        if status == "ambiguous":
            names = []
            for candidate in data.get("candidates") or []:
                org_name = candidate.get("organization", {}).get("slug") or candidate.get(
                    "organization", {}
                ).get("name")
                proj_name = candidate.get("project", {}).get("name")
                names.append(f"{org_name}/{proj_name}")
            raise ValueError(
                "Project hint is ambiguous. Pass a unique acronym or slug. "
                + (", ".join(names) if names else "")
            )
        raise ValueError(
            "Could not resolve project. Pass a project acronym (ski), "
            "org/project slug (skill), or organization_id + project_id UUIDs."
        )

    if use_last:
        remembered = last_board()
        if remembered:
            return remembered

    if required:
        raise ValueError(
            "project is required (acronym, slug, or name). "
            "organization_id and project_id UUIDs are optional."
        )
    return None, None
