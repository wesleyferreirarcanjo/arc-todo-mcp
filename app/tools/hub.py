from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import httpx
from pydantic import Field

from app.arc_todo_client import ArcTodoApiError, arc_todo_client
from app.caller_auth import MISSING_CALLER_TOKEN_MESSAGE, get_caller_token
from app.config import settings
from app.tool_registry import CallerTokenInput, register_tool

# Same convention as the cloud/observer/metrics tools: mark the call's origin
# so server-side logs can tell MCP traffic from UI traffic. The hub token is
# only ever read from server-side settings here.
_MCP_SOURCE_HEADER = {"X-Arc-Source": "mcp"}


async def _hub(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
) -> object:
    # Hub admin tools still require the caller identity every other tenant
    # tool requires; the hub bearer comes from server config only.
    if not get_caller_token():
        raise ArcTodoApiError(MISSING_CALLER_TOKEN_MESSAGE, 401)
    if not settings.arc_hub_base_url or not settings.arc_hub_token:
        raise ArcTodoApiError(
            "arc-hub is not configured on this MCP server "
            "(ARC_HUB_BASE_URL / ARC_HUB_TOKEN)"
        )
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.request(
            method,
            f"{settings.arc_hub_base_url.rstrip('/')}{path}",
            params=params,
            headers={
                "Authorization": f"Bearer {settings.arc_hub_token}",
                **_MCP_SOURCE_HEADER,
            },
        )
    if not response.is_success:
        raise ArcTodoApiError(
            f"arc-hub request failed ({response.status_code}): "
            f"{response.text.strip() or 'error'}",
            response.status_code,
        )
    if response.status_code == 204 or not response.content:
        return {"ok": True}
    try:
        return response.json()
    except ValueError:
        return {"ok": True, "status": response.status_code}


class HubListDevicesInput(CallerTokenInput):
    pass


class HubDevicesPresenceInput(CallerTokenInput):
    pass


class HubListReleasesInput(CallerTokenInput):
    pass


class HubYankReleaseInput(CallerTokenInput):
    version: str = Field(
        description="Release version to yank, e.g. 1.4.2 (leading v optional)."
    )
    confirm: bool = Field(
        default=False,
        description="Must be true to yank the release",
    )


class HubRevokeDeviceInput(CallerTokenInput):
    device_id: str = Field(
        description="Device id from hub_list_devices / hub_devices_presence"
    )
    confirm: bool = Field(
        default=False,
        description="Must be true to revoke the device",
    )


class HubListSharesInput(CallerTokenInput):
    session_id: str = Field(
        description="Sync session id the shares were published for"
    )


class HubRevokeShareInput(CallerTokenInput):
    share_id: str = Field(
        description="Share id from hub_list_shares (not the public token)"
    )
    confirm: bool = Field(
        default=False,
        description="Must be true to revoke the share",
    )


@register_tool(
    key="hub_list_devices",
    group="hub",
    display_name="List hub devices",
    description=(
        "List devices known to arc-hub (id, name, last-seen). Includes sync "
        "clients and paired remote-control hosts."
    ),
    sort_order=170,
    input_model=HubListDevicesInput,
)
async def hub_list_devices(_: HubListDevicesInput) -> str:
    data = await _hub("GET", "/v1/devices")
    return arc_todo_client.format_result(data)


@register_tool(
    key="hub_devices_presence",
    group="hub",
    display_name="Hub device presence",
    description=(
        "Presence for every hub device: state (online|stale|paused|offline), "
        "paired/revoked/remote-enabled flags, active session count, and live "
        "sessions."
    ),
    sort_order=171,
    input_model=HubDevicesPresenceInput,
)
async def hub_devices_presence(_: HubDevicesPresenceInput) -> str:
    data = await _hub("GET", "/v1/devices/presence")
    return arc_todo_client.format_result(data)


@register_tool(
    key="hub_list_releases",
    group="hub",
    display_name="List hub releases",
    description=(
        "List published Arc IDE releases: version, platform, size, sha256, "
        "publish date, and yanked flag."
    ),
    sort_order=172,
    input_model=HubListReleasesInput,
)
async def hub_list_releases(_: HubListReleasesInput) -> str:
    data = await _hub("GET", "/v1/releases")
    return arc_todo_client.format_result(data)


@register_tool(
    key="hub_yank_release",
    group="hub",
    display_name="Yank hub release",
    description=(
        "Yank a published release version so devices stop getting it as an "
        "update. Requires confirm=true."
    ),
    default_enabled=False,
    sort_order=173,
    input_model=HubYankReleaseInput,
)
async def hub_yank_release(input: HubYankReleaseInput) -> str:
    if not input.confirm:
        return (
            "Refused: pass confirm=true to yank this release — devices will "
            "stop being offered the update."
        )
    await _hub("POST", f"/v1/releases/{input.version}/yank")
    return arc_todo_client.format_result({"yanked": input.version})


@register_tool(
    key="hub_revoke_device",
    group="hub",
    display_name="Revoke hub device",
    description=(
        "Revoke a paired device: remote control is disabled and heartbeats "
        "are rejected until it pairs again. Requires confirm=true."
    ),
    default_enabled=False,
    sort_order=174,
    input_model=HubRevokeDeviceInput,
)
async def hub_revoke_device(input: HubRevokeDeviceInput) -> str:
    if not input.confirm:
        return (
            "Refused: pass confirm=true to revoke this device — remote "
            "control stops working until it pairs again."
        )
    data = await _hub("POST", f"/v1/devices/{input.device_id}/revoke")
    return arc_todo_client.format_result(data)


@register_tool(
    key="hub_list_shares",
    group="hub",
    display_name="List hub shares",
    description=(
        "List published session-share links for one sync session id: share "
        "id, URL, expiry, revocation, size, and content hash."
    ),
    sort_order=175,
    input_model=HubListSharesInput,
)
async def hub_list_shares(input: HubListSharesInput) -> str:
    data = await _hub(
        "GET",
        f"/v1/shares?{urlencode({'session': input.session_id})}",
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="hub_revoke_share",
    group="hub",
    display_name="Revoke hub share",
    description=(
        "Revoke a published share link by share id — the public /s/ page "
        "immediately returns 410. Requires confirm=true."
    ),
    default_enabled=False,
    sort_order=176,
    input_model=HubRevokeShareInput,
)
async def hub_revoke_share(input: HubRevokeShareInput) -> str:
    if not input.confirm:
        return (
            "Refused: pass confirm=true to revoke this share — the public "
            "link stops working immediately."
        )
    data = await _hub("POST", f"/v1/shares/{input.share_id}/revoke")
    return arc_todo_client.format_result(data)
