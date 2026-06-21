from __future__ import annotations

import re

UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.I,
)
FRIENDLY_TASK_ID_PATTERN = re.compile(r"^#?[a-z]{3}-\d+$", re.I)


def is_uuid(value: str) -> bool:
    return bool(value and UUID_PATTERN.match(value))


def is_friendly_task_id(value: str) -> bool:
    return bool(value and FRIENDLY_TASK_ID_PATTERN.match(value.strip()))


async def resolve_task_scope(client, task_id: str) -> dict[str, str]:
    if is_uuid(task_id):
        return {"task_id": task_id}

    data = await client.request(
        "GET",
        "/tasks/resolve",
        params={"identifier": task_id.strip()},
    )
    return {
        "task_id": data["id"],
        "organization_id": data["organizationId"],
        "project_id": data["projectId"],
    }
