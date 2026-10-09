import json

import pytest
import respx
from httpx import Response

from app.arc_todo_client import arc_todo_client
from app.tools.cloud import (
    CloudAddAgentServerInput,
    CloudAddSshServerInput,
    CloudAppIdInput,
    CloudAppLogsInput,
    CloudCreateAppInput,
    CloudDeleteAppInput,
    CloudDeployInput,
    CloudDeploymentIdInput,
    CloudGetEnvInput,
    CloudImportCoolifyInput,
    CloudImportEasypanelInput,
    CloudListAppsInput,
    CloudListServersInput,
    CloudProxyConfirmInput,
    CloudRemoveServerInput,
    CloudServerIdInput,
    CloudSetEnvInput,
    CloudStopInput,
    cloud_add_agent_server,
    cloud_add_ssh_server,
    cloud_app_logs,
    cloud_create_app,
    cloud_delete_app,
    cloud_deploy,
    cloud_confirm_import,
    cloud_get_deployment,
    cloud_get_env,
    cloud_import_coolify_app,
    cloud_import_easypanel_app,
    cloud_list_coolify_apps,
    cloud_list_easypanel_apps,
    cloud_install_proxy,
    cloud_list_apps,
    cloud_list_containers,
    cloud_list_deployments,
    cloud_list_servers,
    cloud_proxy_status,
    cloud_refresh_server,
    cloud_remove_server,
    cloud_restart_app,
    cloud_rollback,
    cloud_rollback_proxy,
    cloud_set_env,
    cloud_stop_app,
)

SERVER = "11111111-1111-4111-8111-111111111111"
APP = "22222222-2222-4222-8222-222222222222"


def _point_client(monkeypatch):
    monkeypatch.setenv("ARC_TODO_API_BASE_URL", "http://api.test")
    monkeypatch.setenv("ARC_TODO_ACCESS_TOKEN", "service-token")
    arc_todo_client._base_url = "http://api.test"
    arc_todo_client._token = "service-token"


@pytest.mark.asyncio
@respx.mock
async def test_list_servers_sends_mcp_source_header(monkeypatch, caller_auth):
    _point_client(monkeypatch)
    route = respx.get("http://api.test/cloud/servers").mock(
        return_value=Response(
            200, json=[{"id": SERVER, "name": "arc-lab-1", "status": "online"}]
        )
    )

    result = await cloud_list_servers(CloudListServersInput())

    assert route.called
    assert route.calls[0].request.headers["Authorization"] == "Bearer token-abc"
    assert route.calls[0].request.headers["X-Arc-Source"] == "mcp"
    assert "arc-lab-1" in result


@pytest.mark.asyncio
@respx.mock
async def test_add_ssh_server_posts_camel_case_body(monkeypatch, caller_auth):
    _point_client(monkeypatch)
    route = respx.post("http://api.test/cloud/servers").mock(
        return_value=Response(201, json={"id": SERVER, "name": "arc-lab-1"})
    )

    result = await cloud_add_ssh_server(
        CloudAddSshServerInput(
            name="arc-lab-1",
            role="target",
            ssh_host="192.168.1.10",
            ssh_private_key="KEY-MATERIAL",
        )
    )

    assert route.called
    body = json.loads(route.calls[0].request.content)
    assert body["transport"] == "ssh"
    assert body["sshHost"] == "192.168.1.10"
    assert body["sshPort"] == 22
    assert body["sshUser"] == "root"
    # The key goes to the API once; the tool result must not echo it.
    assert "KEY-MATERIAL" in body["sshPrivateKey"]
    assert "KEY-MATERIAL" not in result


@pytest.mark.asyncio
@respx.mock
async def test_add_agent_server_returns_one_time_token(monkeypatch, caller_auth):
    _point_client(monkeypatch)
    route = respx.post("http://api.test/cloud/servers").mock(
        return_value=Response(
            201,
            json={
                "server": {"id": SERVER, "name": "wesley-pc", "role": "build"},
                "agentToken": "act_once",
            },
        )
    )

    result = await cloud_add_agent_server(
        CloudAddAgentServerInput(name="wesley-pc", role="build")
    )

    assert route.called
    body = json.loads(route.calls[0].request.content)
    assert body == {"name": "wesley-pc", "role": "build", "transport": "agent"}
    assert "act_once" in result


@pytest.mark.asyncio
@respx.mock
async def test_list_containers_and_refresh_hit_server_routes(
    monkeypatch, caller_auth
):
    _point_client(monkeypatch)
    containers_route = respx.get(
        f"http://api.test/cloud/servers/{SERVER}/containers"
    ).mock(return_value=Response(200, json=[{"name": "web"}]))
    refresh_route = respx.post(
        f"http://api.test/cloud/servers/{SERVER}/refresh"
    ).mock(return_value=Response(200, json={"id": SERVER, "status": "online"}))

    containers = await cloud_list_containers(CloudServerIdInput(server_id=SERVER))
    refreshed = await cloud_refresh_server(CloudServerIdInput(server_id=SERVER))

    assert containers_route.called and refresh_route.called
    assert "web" in containers
    assert "online" in refreshed


@pytest.mark.asyncio
@respx.mock
async def test_remove_server_requires_confirm_and_skips_http(
    monkeypatch, caller_auth
):
    _point_client(monkeypatch)
    route = respx.delete(f"http://api.test/cloud/servers/{SERVER}").mock(
        return_value=Response(204)
    )

    refused = await cloud_remove_server(
        CloudRemoveServerInput(server_id=SERVER, confirm=False)
    )

    assert not route.called
    assert "Refused" in refused
    assert "confirm=true" in refused


@pytest.mark.asyncio
@respx.mock
async def test_remove_server_with_confirm_deletes(monkeypatch, caller_auth):
    _point_client(monkeypatch)
    route = respx.delete(f"http://api.test/cloud/servers/{SERVER}").mock(
        return_value=Response(204)
    )

    result = await cloud_remove_server(
        CloudRemoveServerInput(server_id=SERVER, confirm=True)
    )

    assert route.called
    assert route.calls[0].request.headers["X-Arc-Source"] == "mcp"
    assert SERVER in result


@pytest.mark.asyncio
@respx.mock
async def test_proxy_status_gets_server_route(monkeypatch, caller_auth):
    _point_client(monkeypatch)
    route = respx.get(f"http://api.test/cloud/servers/{SERVER}/proxy").mock(
        return_value=Response(
            200,
            json={
                "state": "running",
                "version": "3.5.0",
                "detail": None,
                "hosts": ["app.coolify.test"],
            },
        )
    )

    result = await cloud_proxy_status(CloudServerIdInput(server_id=SERVER))

    assert route.called
    assert route.calls[0].request.headers["X-Arc-Source"] == "mcp"
    assert "running" in result
    assert "3.5.0" in result


@pytest.mark.asyncio
@respx.mock
async def test_install_and_rollback_require_confirm(monkeypatch, caller_auth):
    _point_client(monkeypatch)
    install_route = respx.post(
        f"http://api.test/cloud/servers/{SERVER}/proxy"
    ).mock(return_value=Response(200, json={"state": "running"}))
    rollback_route = respx.post(
        f"http://api.test/cloud/servers/{SERVER}/proxy/rollback"
    ).mock(return_value=Response(200, json={"state": "not_installed"}))

    refused_install = await cloud_install_proxy(
        CloudProxyConfirmInput(server_id=SERVER, confirm=False)
    )
    refused_rollback = await cloud_rollback_proxy(
        CloudProxyConfirmInput(server_id=SERVER, confirm=False)
    )

    assert not install_route.called
    assert not rollback_route.called
    assert "Refused" in refused_install
    assert "Refused" in refused_rollback

    installed = await cloud_install_proxy(
        CloudProxyConfirmInput(server_id=SERVER, confirm=True)
    )
    rolled_back = await cloud_rollback_proxy(
        CloudProxyConfirmInput(server_id=SERVER, confirm=True)
    )

    assert install_route.called and rollback_route.called
    assert "running" in installed
    assert "not_installed" in rolled_back


def test_cloud_tools_registered_with_expected_defaults():
    from app.tool_registry import MCP_TOOL_REGISTRY

    import app.tools.cloud  # noqa: F401

    by_key = {tool.key: tool for tool in MCP_TOOL_REGISTRY}
    for key in (
        "cloud_list_servers",
        "cloud_add_ssh_server",
        "cloud_add_agent_server",
        "cloud_list_containers",
        "cloud_refresh_server",
        "cloud_proxy_status",
        "cloud_list_apps",
        "cloud_create_app",
        "cloud_update_app",
        "cloud_set_env",
        "cloud_get_env",
        "cloud_deploy",
        "cloud_get_deployment",
        "cloud_list_deployments",
        "cloud_rollback",
        "cloud_restart_app",
        "cloud_start_app",
        "cloud_app_logs",
        "cloud_list_coolify_apps",
        "cloud_import_coolify_app",
        "cloud_list_easypanel_apps",
        "cloud_import_easypanel_app",
        "cloud_confirm_import",
    ):
        assert by_key[key].default_enabled is True
        assert by_key[key].group == "cloud"
    assert by_key["cloud_remove_server"].default_enabled is False
    assert by_key["cloud_install_proxy"].default_enabled is False
    assert by_key["cloud_rollback_proxy"].default_enabled is False
    assert by_key["cloud_stop_app"].default_enabled is False
    assert by_key["cloud_delete_app"].default_enabled is False


# ---------------------------------------------------------------------------
# Apps
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_list_apps_and_create_image_app(monkeypatch, caller_auth):
    _point_client(monkeypatch)
    list_route = respx.get("http://api.test/cloud/apps").mock(
        return_value=Response(200, json=[{"id": APP, "name": "whoami"}])
    )
    create_route = respx.post("http://api.test/cloud/apps").mock(
        return_value=Response(201, json={"id": APP, "name": "whoami"})
    )

    listed = await cloud_list_apps(CloudListAppsInput())
    created = await cloud_create_app(
        CloudCreateAppInput(
            name="whoami",
            server_id=SERVER,
            image="traefik/whoami:v1.10",
            domains=["app.arc.test"],
        )
    )

    assert list_route.called and create_route.called
    body = json.loads(create_route.calls[0].request.content)
    assert body["source"] == "image"
    assert body["serverId"] == SERVER
    assert body["image"] == "traefik/whoami:v1.10"
    assert body["domains"] == ["app.arc.test"]
    assert "whoami" in listed and "whoami" in created


@pytest.mark.asyncio
@respx.mock
async def test_env_roundtrip_masks_by_default_and_reveals_on_request(
    monkeypatch, caller_auth
):
    _point_client(monkeypatch)
    put_route = respx.put(f"http://api.test/cloud/apps/{APP}/env").mock(
        return_value=Response(200, json={"keys": ["SECRET"]})
    )

    def env_response(request):
        if request.url.params.get("reveal") == "true":
            return Response(200, json={"env": {"SECRET": "real-value"}})
        return Response(200, json={"env": {"SECRET": "••••••••"}})

    env_route = respx.get(f"http://api.test/cloud/apps/{APP}/env").mock(
        side_effect=env_response
    )

    await cloud_set_env(CloudSetEnvInput(app_id=APP, env={"SECRET": "real-value"}))
    masked = await cloud_get_env(CloudGetEnvInput(app_id=APP))
    revealed = await cloud_get_env(CloudGetEnvInput(app_id=APP, reveal=True))

    assert put_route.called
    assert json.loads(put_route.calls[0].request.content) == {
        "env": {"SECRET": "real-value"}
    }
    # Masked call must NOT send reveal — only the explicit reveal does,
    # and that request is what the master audits.
    urls = [str(call.request.url) for call in env_route.calls]
    assert "reveal=true" not in urls[0]
    assert "reveal=true" in urls[1]
    assert "real-value" not in masked
    assert "real-value" in revealed


@pytest.mark.asyncio
@respx.mock
async def test_deploy_rollback_and_deployment_views(monkeypatch, caller_auth):
    _point_client(monkeypatch)
    deploy_route = respx.post(f"http://api.test/cloud/apps/{APP}/deploy").mock(
        return_value=Response(202, json={"deploymentId": "dep-1"})
    )
    rollback_route = respx.post(
        f"http://api.test/cloud/apps/{APP}/rollback"
    ).mock(return_value=Response(202, json={"deploymentId": "dep-2"}))
    dep_route = respx.get("http://api.test/cloud/deployments/dep-1").mock(
        return_value=Response(200, json={"id": "dep-1", "status": "healthy"})
    )
    list_route = respx.get(
        f"http://api.test/cloud/apps/{APP}/deployments"
    ).mock(return_value=Response(200, json=[{"id": "dep-1"}]))

    deployed = await cloud_deploy(
        CloudDeployInput(app_id=APP, image_ref="traefik/whoami:v1.10.1")
    )
    rolled_back = await cloud_rollback(CloudAppIdInput(app_id=APP))
    dep = await cloud_get_deployment(CloudDeploymentIdInput(deployment_id="dep-1"))
    history = await cloud_list_deployments(CloudAppIdInput(app_id=APP))

    assert deploy_route.called and rollback_route.called
    assert json.loads(deploy_route.calls[0].request.content) == {
        "imageRef": "traefik/whoami:v1.10.1"
    }
    assert "dep-1" in deployed and "dep-2" in rolled_back
    assert "healthy" in dep and "dep-1" in history
    assert dep_route.called and list_route.called


@pytest.mark.asyncio
@respx.mock
async def test_lifecycle_and_logs(monkeypatch, caller_auth):
    _point_client(monkeypatch)
    restart_route = respx.post(
        f"http://api.test/cloud/apps/{APP}/restart"
    ).mock(return_value=Response(200, json={"status": "running"}))
    logs_route = respx.get(
        f"http://api.test/cloud/apps/{APP}/logs", params={"tail": "50"}
    ).mock(return_value=Response(200, json={"lines": ["ready"]}))

    restarted = await cloud_restart_app(CloudAppIdInput(app_id=APP))
    logs = await cloud_app_logs(CloudAppLogsInput(app_id=APP, tail=50))

    assert restart_route.called and logs_route.called
    assert "running" in restarted and "ready" in logs


@pytest.mark.asyncio
@respx.mock
async def test_stop_and_delete_require_confirm(monkeypatch, caller_auth):
    _point_client(monkeypatch)
    stop_route = respx.post(f"http://api.test/cloud/apps/{APP}/stop").mock(
        return_value=Response(200, json={"status": "stopped"})
    )
    delete_route = respx.delete(f"http://api.test/cloud/apps/{APP}").mock(
        return_value=Response(204)
    )

    refused_stop = await cloud_stop_app(CloudStopInput(app_id=APP, confirm=False))
    refused_delete = await cloud_delete_app(
        CloudDeleteAppInput(app_id=APP, confirm=False)
    )
    assert not stop_route.called and not delete_route.called
    assert "Refused" in refused_stop and "Refused" in refused_delete

    stopped = await cloud_stop_app(CloudStopInput(app_id=APP, confirm=True))
    deleted = await cloud_delete_app(CloudDeleteAppInput(app_id=APP, confirm=True))
    assert stop_route.called and delete_route.called
    assert "stopped" in stopped and APP in deleted


# ---------------------------------------------------------------------------
# Panel import — read-only panel reads, draft apps until confirmed.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_list_coolify_and_easypanel_apps(monkeypatch, caller_auth):
    _point_client(monkeypatch)
    coolify_route = respx.get("http://api.test/cloud/coolify/apps").mock(
        return_value=Response(
            200, json=[{"uuid": "abc-123", "name": "blog", "status": "running"}]
        )
    )
    easypanel_route = respx.get("http://api.test/cloud/easypanel/apps").mock(
        return_value=Response(
            200,
            json=[{"project": "blog", "service": "blog", "type": "app"}],
        )
    )

    coolify = await cloud_list_coolify_apps(CloudListServersInput())
    easypanel = await cloud_list_easypanel_apps(CloudListServersInput())

    assert coolify_route.called and easypanel_route.called
    assert "blog" in coolify and "blog" in easypanel


@pytest.mark.asyncio
@respx.mock
async def test_import_coolify_app_posts_draft_body(monkeypatch, caller_auth):
    _point_client(monkeypatch)
    route = respx.post(
        "http://api.test/cloud/coolify/apps/abc-123/import"
    ).mock(
        return_value=Response(
            201,
            json={
                "app": {"id": APP, "importState": "draft"},
                "summary": {"panel": "coolify", "envCount": 2},
            },
        )
    )

    result = await cloud_import_coolify_app(
        CloudImportCoolifyInput(coolify_app_uuid="abc-123", server_id=SERVER)
    )

    assert route.called
    body = json.loads(route.calls[0].request.content)
    assert body["serverId"] == SERVER
    assert "abc-123" in route.calls[0].request.url.path
    assert "draft" in result


@pytest.mark.asyncio
@respx.mock
async def test_import_easypanel_app_encodes_path(monkeypatch, caller_auth):
    _point_client(monkeypatch)
    route = respx.post(
        "http://api.test/cloud/easypanel/apps/blog/blog-web/import"
    ).mock(
        return_value=Response(201, json={"app": {"id": APP}, "summary": {}})
    )

    result = await cloud_import_easypanel_app(
        CloudImportEasypanelInput(
            project="blog", service="blog-web", server_id=SERVER, name="blog-web"
        )
    )

    assert route.called
    body = json.loads(route.calls[0].request.content)
    assert body["serverId"] == SERVER
    assert body["name"] == "blog-web"
    assert APP in result


@pytest.mark.asyncio
@respx.mock
async def test_confirm_import_posts_confirm_route(monkeypatch, caller_auth):
    _point_client(monkeypatch)
    route = respx.post(
        f"http://api.test/cloud/apps/{APP}/confirm-import"
    ).mock(return_value=Response(200, json={"id": APP, "importState": None}))

    result = await cloud_confirm_import(CloudAppIdInput(app_id=APP))

    assert route.called
    assert APP in result
