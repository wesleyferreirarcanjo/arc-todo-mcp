import pytest
import respx
from httpx import Response

from app.config import settings
from app.tools.hub import (
    HubDevicesPresenceInput,
    HubListDevicesInput,
    HubListReleasesInput,
    HubListSharesInput,
    HubRevokeDeviceInput,
    HubRevokeShareInput,
    HubYankReleaseInput,
    hub_devices_presence,
    hub_list_devices,
    hub_list_releases,
    hub_list_shares,
    hub_revoke_device,
    hub_revoke_share,
    hub_yank_release,
)

HUB = "http://hub.test"


@pytest.fixture
def hub_settings(monkeypatch):
    monkeypatch.setattr(settings, "arc_hub_base_url", HUB)
    monkeypatch.setattr(settings, "arc_hub_token", "hub-secret-token")
    return settings


@pytest.mark.asyncio
@respx.mock
async def test_list_devices_and_presence(hub_settings, caller_auth):
    devices = respx.get(f"{HUB}/v1/devices").mock(
        return_value=Response(200, json=[{"id": "dev-1", "name": "desk"}])
    )
    presence = respx.get(f"{HUB}/v1/devices/presence").mock(
        return_value=Response(200, json=[{"id": "dev-1", "state": "online"}])
    )

    result = await hub_list_devices(HubListDevicesInput())
    assert devices.called
    assert "dev-1" in result
    # Hub auth comes from server config, marked as MCP traffic.
    req = devices.calls[0].request
    assert req.headers["Authorization"] == "Bearer hub-secret-token"
    assert req.headers["X-Arc-Source"] == "mcp"

    result = await hub_devices_presence(HubDevicesPresenceInput())
    assert presence.called
    assert "online" in result


@pytest.mark.asyncio
@respx.mock
async def test_hub_token_never_leaks(hub_settings, caller_auth):
    respx.get(f"{HUB}/v1/devices").mock(return_value=Response(200, json=[]))
    result = await hub_list_devices(HubListDevicesInput())
    assert "hub-secret-token" not in result


@pytest.mark.asyncio
async def test_requires_caller_token(hub_settings):
    from app.arc_todo_client import ArcTodoApiError

    with pytest.raises(ArcTodoApiError):
        await hub_list_devices(HubListDevicesInput())


@pytest.mark.asyncio
async def test_requires_hub_config(monkeypatch, caller_auth):
    monkeypatch.setattr(settings, "arc_hub_base_url", None)
    monkeypatch.setattr(settings, "arc_hub_token", None)
    from app.arc_todo_client import ArcTodoApiError

    with pytest.raises(ArcTodoApiError, match="not configured"):
        await hub_list_devices(HubListDevicesInput())


@pytest.mark.asyncio
@respx.mock
async def test_releases_and_yank(hub_settings, caller_auth):
    respx.get(f"{HUB}/v1/releases").mock(
        return_value=Response(200, json=[{"version": "1.2.3"}])
    )
    yank = respx.post(f"{HUB}/v1/releases/1.2.3/yank").mock(
        return_value=Response(200, text="")
    )

    result = await hub_list_releases(HubListReleasesInput())
    assert "1.2.3" in result

    refused = await hub_yank_release(
        HubYankReleaseInput(version="1.2.3", confirm=False)
    )
    assert "Refused" in refused
    assert not yank.called

    result = await hub_yank_release(
        HubYankReleaseInput(version="1.2.3", confirm=True)
    )
    assert yank.called
    assert "1.2.3" in result


@pytest.mark.asyncio
@respx.mock
async def test_revoke_device_requires_confirm(hub_settings, caller_auth):
    revoke = respx.post(f"{HUB}/v1/devices/dev-9/revoke").mock(
        return_value=Response(200, json={"revoked": True})
    )

    refused = await hub_revoke_device(
        HubRevokeDeviceInput(device_id="dev-9", confirm=False)
    )
    assert "Refused" in refused
    assert not revoke.called

    result = await hub_revoke_device(
        HubRevokeDeviceInput(device_id="dev-9", confirm=True)
    )
    assert revoke.called
    assert "revoked" in result


@pytest.mark.asyncio
@respx.mock
async def test_shares_list_and_revoke(hub_settings, caller_auth):
    shares = respx.get(f"{HUB}/v1/shares").mock(
        return_value=Response(
            200, json={"shares": [{"id": "sh1", "url": f"{HUB}/s/tok"}]}
        )
    )
    revoke = respx.post(f"{HUB}/v1/shares/sh1/revoke").mock(
        return_value=Response(200, json={"id": "sh1"})
    )

    result = await hub_list_shares(HubListSharesInput(session_id="sess-1"))
    assert "session=sess-1" in str(shares.calls[0].request.url)
    assert "sh1" in result

    refused = await hub_revoke_share(
        HubRevokeShareInput(share_id="sh1", confirm=False)
    )
    assert "Refused" in refused
    assert not revoke.called

    await hub_revoke_share(HubRevokeShareInput(share_id="sh1", confirm=True))
    assert revoke.called


@pytest.mark.asyncio
@respx.mock
async def test_hub_error_surfaces_status(hub_settings, caller_auth):
    respx.get(f"{HUB}/v1/devices").mock(return_value=Response(503))
    from app.arc_todo_client import ArcTodoApiError

    with pytest.raises(ArcTodoApiError, match="503"):
        await hub_list_devices(HubListDevicesInput())
