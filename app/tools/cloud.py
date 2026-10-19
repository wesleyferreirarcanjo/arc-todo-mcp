from __future__ import annotations

from pydantic import Field

from app.arc_todo_client import arc_todo_client
from app.tool_registry import CallerTokenInput, register_tool

# Every cloud call is audited by the arc-cloud master; source must be `mcp`
# here so the audit_log row is distinguishable from UI calls.
_MCP_SOURCE_HEADER = {"X-Arc-Source": "mcp"}


async def _cloud(
    method: str, path: str, *, json_body: dict | None = None
) -> object:
    return await arc_todo_client.request(
        method, path, json_body=json_body, extra_headers=_MCP_SOURCE_HEADER
    )


class CloudListServersInput(CallerTokenInput):
    pass


class CloudAddSshServerInput(CallerTokenInput):
    name: str = Field(description="Unique server name")
    role: str = Field(
        default="target",
        description="target | build — build machines are never deploy targets",
    )
    ssh_host: str = Field(description="SSH host IP or hostname")
    ssh_port: int = Field(default=22, ge=1, le=65535)
    ssh_user: str = Field(default="root")
    ssh_private_key: str = Field(
        description=(
            "PEM/OpenSSH private key for the SSH user. Stored encrypted by "
            "arc-cloud and never returned or logged."
        )
    )


class CloudAddAgentServerInput(CallerTokenInput):
    name: str = Field(description="Unique server name")
    role: str = Field(
        default="target",
        description="target | build — build machines are never deploy targets",
    )


class CloudServerIdInput(CallerTokenInput):
    server_id: str = Field(description="arc-cloud server UUID")


class CloudRemoveServerInput(CloudServerIdInput):
    confirm: bool = Field(
        default=False,
        description="Must be true to actually remove the server",
    )


@register_tool(
    key="cloud_list_servers",
    group="cloud",
    display_name="List cloud servers",
    description=(
        "List arc-cloud managed Docker servers with transport, status, "
        "Docker version, and panel detection."
    ),
    sort_order=100,
    input_model=CloudListServersInput,
)
async def cloud_list_servers(_: CloudListServersInput) -> str:
    data = await _cloud("GET", "/cloud/servers")
    return arc_todo_client.format_result(data)


@register_tool(
    key="cloud_add_ssh_server",
    group="cloud",
    display_name="Add SSH server",
    description=(
        "Register a Docker server managed over SSH. The private key is "
        "stored encrypted and never returned."
    ),
    sort_order=101,
    input_model=CloudAddSshServerInput,
)
async def cloud_add_ssh_server(input: CloudAddSshServerInput) -> str:
    data = await _cloud(
        "POST",
        "/cloud/servers",
        json_body={
            "name": input.name,
            "role": input.role,
            "transport": "ssh",
            "sshHost": input.ssh_host,
            "sshPort": input.ssh_port,
            "sshUser": input.ssh_user,
            "sshPrivateKey": input.ssh_private_key,
        },
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="cloud_add_agent_server",
    group="cloud",
    display_name="Add agent server",
    description=(
        "Register a server controlled by an outbound arc-cloud agent. "
        "Returns a one-time agent token for the agent install command."
    ),
    sort_order=102,
    input_model=CloudAddAgentServerInput,
)
async def cloud_add_agent_server(input: CloudAddAgentServerInput) -> str:
    data = await _cloud(
        "POST",
        "/cloud/servers",
        json_body={
            "name": input.name,
            "role": input.role,
            "transport": "agent",
        },
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="cloud_list_containers",
    group="cloud",
    display_name="List server containers",
    description=(
        "List Docker containers on one arc-cloud server "
        "(id, name, image, state, status)."
    ),
    sort_order=103,
    input_model=CloudServerIdInput,
)
async def cloud_list_containers(input: CloudServerIdInput) -> str:
    data = await _cloud("GET", f"/cloud/servers/{input.server_id}/containers")
    return arc_todo_client.format_result(data)


@register_tool(
    key="cloud_refresh_server",
    group="cloud",
    display_name="Refresh server",
    description=(
        "Re-probe one arc-cloud server for Docker version, swarm state, "
        "and panel detection."
    ),
    sort_order=104,
    input_model=CloudServerIdInput,
)
async def cloud_refresh_server(input: CloudServerIdInput) -> str:
    data = await _cloud("POST", f"/cloud/servers/{input.server_id}/refresh")
    return arc_todo_client.format_result(data)


@register_tool(
    key="cloud_remove_server",
    group="cloud",
    display_name="Remove server",
    description=(
        "Remove a server from arc-cloud management. Destructive: requires "
        "confirm=true. Does not touch containers on the host."
    ),
    default_enabled=False,
    sort_order=105,
    input_model=CloudRemoveServerInput,
)
async def cloud_remove_server(input: CloudRemoveServerInput) -> str:
    if not input.confirm:
        return (
            "Refused: pass confirm=true to remove this server from Cloud "
            "management. Removing it does not stop containers on the host."
        )
    await _cloud("DELETE", f"/cloud/servers/{input.server_id}")
    return arc_todo_client.format_result({"removed": input.server_id})


class CloudProxyConfirmInput(CloudServerIdInput):
    confirm: bool = Field(
        default=False,
        description="Must be true to run this proxy action",
    )


@register_tool(
    key="cloud_proxy_status",
    group="cloud",
    display_name="Cloud proxy status",
    description=(
        "Show the arc-cloud Traefik proxy state on one server "
        "(not_installed, installing, running, restoring, error) with "
        "version and last detail. Poll this after install/rollback."
    ),
    sort_order=106,
    input_model=CloudServerIdInput,
)
async def cloud_proxy_status(input: CloudServerIdInput) -> str:
    data = await _cloud("GET", f"/cloud/servers/{input.server_id}/proxy")
    return arc_todo_client.format_result(data)


@register_tool(
    key="cloud_install_proxy",
    group="cloud",
    display_name="Install cloud proxy",
    description=(
        "Take over ports 80/443 with the arc-cloud Traefik proxy while "
        "preserving the detected panel routes (Coolify labels or Easypanel "
        "route files). Requires confirm=true. Async: returns 202 "
        "'installing' and the work continues master-side — poll "
        "cloud_proxy_status until running or error (detail names refusals). "
        "Refuses build machines and unsafe routing; auto-rolls-back on "
        "post-check failure."
    ),
    default_enabled=False,
    sort_order=107,
    input_model=CloudProxyConfirmInput,
)
async def cloud_install_proxy(input: CloudProxyConfirmInput) -> str:
    if not input.confirm:
        return (
            "Refused: pass confirm=true to install arc-cloud-proxy on this "
            "server. The install takes over ports 80/443; unsafe routing is "
            "refused and any post-check failure rolls back automatically."
        )
    data = await _cloud("POST", f"/cloud/servers/{input.server_id}/proxy")
    return arc_todo_client.format_result(data)


@register_tool(
    key="cloud_rollback_proxy",
    group="cloud",
    display_name="Rollback cloud proxy",
    description=(
        "Remove arc-cloud-proxy and restore the panel proxy recorded at "
        "install, then re-check the routed hosts. Requires confirm=true. "
        "Async: returns 202 'restoring' — poll cloud_proxy_status until "
        "not_installed or error."
    ),
    default_enabled=False,
    sort_order=108,
    input_model=CloudProxyConfirmInput,
)
async def cloud_rollback_proxy(input: CloudProxyConfirmInput) -> str:
    if not input.confirm:
        return (
            "Refused: pass confirm=true to remove arc-cloud-proxy and "
            "restore the panel proxy."
        )
    data = await _cloud(
        "POST", f"/cloud/servers/{input.server_id}/proxy/rollback"
    )
    return arc_todo_client.format_result(data)


# ---------------------------------------------------------------------------
# Apps — image or compose deployments with encrypted env, domains, and a
# health-gated zero-downtime switch.
# ---------------------------------------------------------------------------


class CloudListAppsInput(CallerTokenInput):
    server_id: str | None = Field(
        default=None, description="Optional arc-cloud server UUID filter"
    )


class CloudAppIdInput(CallerTokenInput):
    app_id: str = Field(description="arc-cloud app UUID")


class CloudCreateAppInput(CallerTokenInput):
    name: str = Field(
        description="Unique app slug: ^[a-z0-9][a-z0-9-]{0,61}$"
    )
    server_id: str = Field(
        description="Target server UUID — build machines are refused"
    )
    source: str = Field(default="image", description="image | compose")
    image: str | None = Field(
        default=None, description="Image ref, e.g. ghcr.io/org/app:tag"
    )
    compose_yaml: str | None = Field(
        default=None, description="Compose file for source=compose"
    )
    port: int = Field(default=80, ge=1, le=65535)
    health_path: str = Field(default="/")
    domains: list[str] = Field(default_factory=list)


class CloudUpdateAppInput(CallerTokenInput):
    app_id: str = Field(description="arc-cloud app UUID")
    name: str | None = None
    server_id: str | None = None
    image: str | None = None
    compose_yaml: str | None = None
    port: int | None = Field(default=None, ge=1, le=65535)
    health_path: str | None = None
    domains: list[str] | None = None


class CloudSetEnvInput(CloudAppIdInput):
    env: dict[str, str] = Field(
        description=(
            "Full environment map — replaces all existing values. Stored "
            "encrypted by arc-cloud and masked in every output."
        )
    )


class CloudGetEnvInput(CloudAppIdInput):
    reveal: bool = Field(
        default=False,
        description=(
            "false returns masked values. true returns plaintext and is "
            "recorded in the arc-cloud audit log."
        ),
    )


class CloudDeployInput(CloudAppIdInput):
    image_ref: str | None = Field(
        default=None,
        description="Image ref override; blank deploys the stored image",
    )


class CloudDeploymentIdInput(CallerTokenInput):
    deployment_id: str = Field(description="arc-cloud deployment UUID")


class CloudStopInput(CloudAppIdInput):
    confirm: bool = Field(
        default=False, description="Must be true to stop a running app"
    )


class CloudDeleteAppInput(CloudAppIdInput):
    confirm: bool = Field(
        default=False,
        description="Must be true — deletes the app, its containers, and history",
    )


class CloudAppLogsInput(CloudAppIdInput):
    tail: int = Field(default=200, ge=1, le=1000)


@register_tool(
    key="cloud_list_apps",
    group="cloud",
    display_name="List cloud apps",
    description=(
        "List arc-cloud applications with source, server, domains, and "
        "status (running, deploying, stopped, failed)."
    ),
    sort_order=109,
    input_model=CloudListAppsInput,
)
async def cloud_list_apps(input: CloudListAppsInput) -> str:
    query = f"?serverId={input.server_id}" if input.server_id else ""
    data = await _cloud("GET", f"/cloud/apps{query}")
    return arc_todo_client.format_result(data)


@register_tool(
    key="cloud_create_app",
    group="cloud",
    display_name="Create cloud app",
    description=(
        "Create an arc-cloud application from a container image or a "
        "compose file, with port, health check path, and HTTPS domains. "
        "Build machines are refused as targets."
    ),
    sort_order=110,
    input_model=CloudCreateAppInput,
)
async def cloud_create_app(input: CloudCreateAppInput) -> str:
    body: dict = {
        "name": input.name,
        "serverId": input.server_id,
        "source": input.source,
        "port": input.port,
        "healthPath": input.health_path,
        "domains": input.domains,
    }
    if input.image:
        body["image"] = input.image
    if input.compose_yaml:
        body["composeYaml"] = input.compose_yaml
    data = await _cloud("POST", "/cloud/apps", json_body=body)
    return arc_todo_client.format_result(data)


@register_tool(
    key="cloud_update_app",
    group="cloud",
    display_name="Update cloud app",
    description=(
        "Update an app's image, compose file, port, health check, domains, "
        "or target server. Omitted fields keep their current values."
    ),
    sort_order=111,
    input_model=CloudUpdateAppInput,
)
async def cloud_update_app(input: CloudUpdateAppInput) -> str:
    body = {
        key: value
        for key, value in {
            "name": input.name,
            "serverId": input.server_id,
            "image": input.image,
            "composeYaml": input.compose_yaml,
            "port": input.port,
            "healthPath": input.health_path,
            "domains": input.domains,
        }.items()
        if value is not None
    }
    data = await _cloud("PATCH", f"/cloud/apps/{input.app_id}", json_body=body)
    return arc_todo_client.format_result(data)


@register_tool(
    key="cloud_set_env",
    group="cloud",
    display_name="Set app environment",
    description=(
        "Replace an app's environment variables. Stored AES-256-GCM "
        "encrypted; deploy logs mask every value."
    ),
    sort_order=112,
    input_model=CloudSetEnvInput,
)
async def cloud_set_env(input: CloudSetEnvInput) -> str:
    data = await _cloud(
        "PUT", f"/cloud/apps/{input.app_id}/env", json_body={"env": input.env}
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="cloud_get_env",
    group="cloud",
    display_name="Get app environment",
    description=(
        "Read an app's environment keys. Values are masked by default; "
        "reveal=true returns plaintext and is audited server-side."
    ),
    sort_order=113,
    input_model=CloudGetEnvInput,
)
async def cloud_get_env(input: CloudGetEnvInput) -> str:
    query = "?reveal=true" if input.reveal else ""
    data = await _cloud("GET", f"/cloud/apps/{input.app_id}/env{query}")
    return arc_todo_client.format_result(data)


@register_tool(
    key="cloud_deploy",
    group="cloud",
    display_name="Deploy cloud app",
    description=(
        "Deploy an app. The new container must pass its health check "
        "before the old one is removed — the running version stays up on "
        "failure. Returns a deploymentId for cloud_get_deployment."
    ),
    sort_order=114,
    input_model=CloudDeployInput,
)
async def cloud_deploy(input: CloudDeployInput) -> str:
    body = {"imageRef": input.image_ref} if input.image_ref else {}
    data = await _cloud(
        "POST", f"/cloud/apps/{input.app_id}/deploy", json_body=body
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="cloud_get_deployment",
    group="cloud",
    display_name="Get deployment",
    description=(
        "Show one deployment's status, trigger, actor, and full masked "
        "deploy log."
    ),
    sort_order=115,
    input_model=CloudDeploymentIdInput,
)
async def cloud_get_deployment(input: CloudDeploymentIdInput) -> str:
    data = await _cloud("GET", f"/cloud/deployments/{input.deployment_id}")
    return arc_todo_client.format_result(data)


@register_tool(
    key="cloud_list_deployments",
    group="cloud",
    display_name="List app deployments",
    description="List an app's deployment history, newest first.",
    sort_order=116,
    input_model=CloudAppIdInput,
)
async def cloud_list_deployments(input: CloudAppIdInput) -> str:
    data = await _cloud("GET", f"/cloud/apps/{input.app_id}/deployments")
    return arc_todo_client.format_result(data)


@register_tool(
    key="cloud_rollback",
    group="cloud",
    display_name="Rollback cloud app",
    description=(
        "Deploy the image ref of the latest previous healthy deployment. "
        "Health-gated like a normal deploy: the current version stays up "
        "until the rollback target passes its check."
    ),
    sort_order=117,
    input_model=CloudAppIdInput,
)
async def cloud_rollback(input: CloudAppIdInput) -> str:
    data = await _cloud("POST", f"/cloud/apps/{input.app_id}/rollback", json_body={})
    return arc_todo_client.format_result(data)


@register_tool(
    key="cloud_restart_app",
    group="cloud",
    display_name="Restart cloud app",
    description="Restart the currently running app container or compose stack.",
    sort_order=118,
    input_model=CloudAppIdInput,
)
async def cloud_restart_app(input: CloudAppIdInput) -> str:
    data = await _cloud("POST", f"/cloud/apps/{input.app_id}/restart", json_body={})
    return arc_todo_client.format_result(data)


@register_tool(
    key="cloud_start_app",
    group="cloud",
    display_name="Start cloud app",
    description="Start a stopped app's container or compose stack.",
    sort_order=119,
    input_model=CloudAppIdInput,
)
async def cloud_start_app(input: CloudAppIdInput) -> str:
    data = await _cloud("POST", f"/cloud/apps/{input.app_id}/start", json_body={})
    return arc_todo_client.format_result(data)


@register_tool(
    key="cloud_stop_app",
    group="cloud",
    display_name="Stop cloud app",
    description=(
        "Stop a running app's container or compose stack. The app stops "
        "serving its domains. Requires confirm=true."
    ),
    default_enabled=False,
    sort_order=120,
    input_model=CloudStopInput,
)
async def cloud_stop_app(input: CloudStopInput) -> str:
    if not input.confirm:
        return (
            "Refused: pass confirm=true to stop this app — it stops "
            "serving its domains until started again."
        )
    data = await _cloud("POST", f"/cloud/apps/{input.app_id}/stop", json_body={})
    return arc_todo_client.format_result(data)


@register_tool(
    key="cloud_delete_app",
    group="cloud",
    display_name="Delete cloud app",
    description=(
        "Delete an app, its container/compose stack on the server, and "
        "its deployment history. Requires confirm=true."
    ),
    default_enabled=False,
    sort_order=121,
    input_model=CloudDeleteAppInput,
)
async def cloud_delete_app(input: CloudDeleteAppInput) -> str:
    if not input.confirm:
        return (
            "Refused: pass confirm=true to delete this app, its "
            "containers, and its deployment history."
        )
    await _cloud("DELETE", f"/cloud/apps/{input.app_id}")
    return arc_todo_client.format_result({"removed": input.app_id})


@register_tool(
    key="cloud_app_logs",
    group="cloud",
    display_name="App container logs",
    description=(
        "Tail the running app container's output (1-1000 lines, masked). "
        "For compose apps this follows the first running service."
    ),
    sort_order=122,
    input_model=CloudAppLogsInput,
)
async def cloud_app_logs(input: CloudAppLogsInput) -> str:
    data = await _cloud("GET", f"/cloud/apps/{input.app_id}/logs?tail={input.tail}")
    return arc_todo_client.format_result(data)


# ---------------------------------------------------------------------------
# Git builds — source config, build policy/machines, GitHub App, deploy keys.
# ---------------------------------------------------------------------------


class CloudSetAppSourceInput(CloudAppIdInput):
    git_provider: str | None = Field(
        default=None,
        description=(
            "github_app | deploy_key | public — empty string clears the "
            "git source and reverts to image/compose deploys"
        ),
    )
    repo: str | None = Field(
        default=None,
        description="owner/repo (GitHub) or a full URL / absolute path (lab)",
    )
    branch: str | None = Field(default=None)
    dockerfile: str | None = Field(default=None, description="default Dockerfile")
    context: str | None = Field(default=None, description="default .")
    auto_deploy: bool | None = Field(
        default=None,
        description="Deploy on every signed push webhook to this branch",
    )
    registry: str | None = Field(
        default=None, description="ghcr | private — set with registry_repo"
    )
    registry_repo: str | None = Field(
        default=None,
        description="Image base the build tags, e.g. ghcr.io/owner/app",
    )
    registry_user: str | None = Field(default=None)
    registry_pass: str | None = Field(
        default=None,
        description="Registry password — stored encrypted, never returned",
    )


class CloudSetBuildPolicyInput(CloudAppIdInput):
    build_policy: str = Field(
        description=(
            "local_preferred (build machine if online, else target) | "
            "local_only (queue until a machine is online) | "
            "server_only (always the target)"
        )
    )
    allowed_build_servers: list[str] | None = Field(
        default=None,
        description="Build machine UUIDs allowed for this app; empty = any",
    )


class CloudBuildDeployInput(CloudAppIdInput):
    ref: str | None = Field(
        default=None,
        description=(
            "Branch or pushed commit sha; empty builds the configured "
            "branch tip. Unknown commits fail commit_not_pushed."
        ),
    )


class CloudSetBuildMachineInput(CloudServerIdInput):
    accept_builds: bool | None = Field(
        default=None, description="Whether this build machine accepts builds"
    )
    build_priority: int | None = Field(
        default=None, description="Higher wins when several machines are free"
    )
    max_parallel_builds: int | None = Field(
        default=None, ge=1, le=16, description="Concurrent build slots"
    )


class CloudSetBuildCheckoutInput(CloudServerIdInput):
    app_id: str = Field(description="arc-cloud app UUID")
    path: str = Field(
        description=(
            "Existing checkout path on the build machine — reused with "
            "fetch + detached worktree. Empty clears the mapping."
        )
    )


@register_tool(
    key="cloud_build_and_deploy",
    group="cloud",
    display_name="Build and deploy from git",
    description=(
        "Build an app's Docker image from its git source and deploy it. "
        "Builds run on a build machine when one is online (per build "
        "policy), else on the target server. The commit must be pushed — "
        "every deployment maps to a commit sha. Returns a deploymentId."
    ),
    sort_order=123,
    input_model=CloudBuildDeployInput,
)
async def cloud_build_and_deploy(input: CloudBuildDeployInput) -> str:
    body = {"ref": input.ref} if input.ref else {}
    data = await _cloud(
        "POST", f"/cloud/apps/{input.app_id}/build-deploy", json_body=body
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="cloud_set_app_source",
    group="cloud",
    display_name="Set app git source",
    description=(
        "Configure an app to build from git: provider (github_app, "
        "deploy_key, or public repo), repo, branch, Dockerfile path, "
        "context, auto-deploy on push, and the registry the image is "
        "pushed to (ghcr.io/owner/repo by default). Set git_provider to "
        "an empty string to switch back to image/compose deploys."
    ),
    sort_order=124,
    input_model=CloudSetAppSourceInput,
)
async def cloud_set_app_source(input: CloudSetAppSourceInput) -> str:
    source_body = {
        key: value
        for key, value in {
            "gitProvider": input.git_provider,
            "repo": input.repo,
            "branch": input.branch,
            "dockerfile": input.dockerfile,
            "context": input.context,
            "autoDeploy": input.auto_deploy,
        }.items()
        if value is not None
    }
    if source_body:
        await _cloud(
            "PUT", f"/cloud/apps/{input.app_id}/source", json_body=source_body
        )
    registry_body = {
        key: value
        for key, value in {
            "registry": input.registry,
            "registryRepo": input.registry_repo,
            "registryUser": input.registry_user,
            "registryPass": input.registry_pass,
        }.items()
        if value is not None
    }
    if registry_body:
        await _cloud(
            "PUT",
            f"/cloud/apps/{input.app_id}/registry",
            json_body=registry_body,
        )
    if not source_body and not registry_body:
        return "Nothing to update — pass at least one field."
    data = await _cloud("GET", f"/cloud/apps/{input.app_id}")
    return arc_todo_client.format_result(data)


@register_tool(
    key="cloud_set_build_policy",
    group="cloud",
    display_name="Set app build policy",
    description=(
        "Set where an app's builds run: local_preferred (build machine "
        "when online, target fallback), local_only (queues while no "
        "machine is online), or server_only (always the target). "
        "Optionally restrict which build machines may build this app."
    ),
    sort_order=125,
    input_model=CloudSetBuildPolicyInput,
)
async def cloud_set_build_policy(input: CloudSetBuildPolicyInput) -> str:
    body: dict = {"buildPolicy": input.build_policy}
    if input.allowed_build_servers is not None:
        body["allowedBuildServers"] = input.allowed_build_servers
    data = await _cloud(
        "PUT", f"/cloud/apps/{input.app_id}/build-policy", json_body=body
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="cloud_set_build_machine",
    group="cloud",
    display_name="Configure build machine",
    description=(
        "Configure a build-role server: whether it accepts builds, its "
        "priority (higher wins), and max parallel builds. Build machines "
        "never run deployed applications."
    ),
    sort_order=126,
    input_model=CloudSetBuildMachineInput,
)
async def cloud_set_build_machine(input: CloudSetBuildMachineInput) -> str:
    body = {
        key: value
        for key, value in {
            "acceptBuilds": input.accept_builds,
            "buildPriority": input.build_priority,
            "maxParallelBuilds": input.max_parallel_builds,
        }.items()
        if value is not None
    }
    if not body:
        return "Nothing to update — pass at least one field."
    data = await _cloud(
        "PUT", f"/cloud/servers/{input.server_id}/build-settings", json_body=body
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="cloud_set_build_checkout",
    group="cloud",
    display_name="Map app checkout path",
    description=(
        "Map an app to an existing git checkout on a build machine — the "
        "build fetches into it and uses a detached worktree, so the "
        "working tree is never touched. Empty path clears the mapping."
    ),
    sort_order=127,
    input_model=CloudSetBuildCheckoutInput,
)
async def cloud_set_build_checkout(input: CloudSetBuildCheckoutInput) -> str:
    data = await _cloud(
        "PUT",
        f"/cloud/servers/{input.server_id}/checkouts/{input.app_id}",
        json_body={"path": input.path},
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="cloud_github_app_status",
    group="cloud",
    display_name="GitHub App status",
    description=(
        "Show whether the arc-cloud GitHub App is configured (app id, "
        "installation id, webhook secret present). Required for private "
        "repos, push webhooks, and ghcr pushes."
    ),
    sort_order=128,
    input_model=CallerTokenInput,
)
async def cloud_github_app_status(_: CallerTokenInput) -> str:
    data = await _cloud("GET", "/cloud/github-app")
    return arc_todo_client.format_result(data)


@register_tool(
    key="cloud_create_deploy_key",
    group="cloud",
    display_name="Create app deploy key",
    description=(
        "Generate an Ed25519 deploy key for an app's deploy_key git "
        "source. Returns the public key once — add it as a read-only "
        "deploy key on the GitHub repo. The private key is stored "
        "encrypted and never returned."
    ),
    sort_order=129,
    input_model=CloudAppIdInput,
)
async def cloud_create_deploy_key(input: CloudAppIdInput) -> str:
    data = await _cloud(
        "POST", f"/cloud/apps/{input.app_id}/deploy-key", json_body={}
    )
    return arc_todo_client.format_result(data)


# ---------------------------------------------------------------------------
# Panel import — read-only Coolify/Easypanel reads create draft apps that
# cannot deploy until confirmed.
# ---------------------------------------------------------------------------


class CloudImportCoolifyInput(CallerTokenInput):
    coolify_app_uuid: str = Field(description="Coolify application UUID")
    server_id: str = Field(
        description="arc-cloud target server UUID for the new draft app"
    )
    name: str | None = Field(
        default=None, description="Optional app slug; defaults to the panel name"
    )


class CloudImportEasypanelInput(CallerTokenInput):
    project: str = Field(description="Easypanel project name (a-z0-9-_)")
    service: str = Field(description="Easypanel app service name")
    server_id: str = Field(
        description="arc-cloud target server UUID for the new draft app"
    )
    name: str | None = Field(
        default=None, description="Optional app slug; defaults to project-service"
    )


@register_tool(
    key="cloud_list_coolify_apps",
    group="cloud",
    display_name="List Coolify apps",
    description=(
        "List applications on the configured Coolify instance (uuid, name, "
        "domains, build pack, status). Read-only."
    ),
    sort_order=130,
    input_model=CallerTokenInput,
)
async def cloud_list_coolify_apps(_: CallerTokenInput) -> str:
    data = await _cloud("GET", "/cloud/coolify/apps")
    return arc_todo_client.format_result(data)


@register_tool(
    key="cloud_import_coolify_app",
    group="cloud",
    display_name="Import Coolify app",
    description=(
        "Read a Coolify application (source, env, domains, port, volumes) "
        "and create an arc-cloud draft app — nothing is deployed and no "
        "domains are claimed. Returns the side-by-side summary to review; "
        "then call cloud_confirm_import."
    ),
    sort_order=131,
    input_model=CloudImportCoolifyInput,
)
async def cloud_import_coolify_app(input: CloudImportCoolifyInput) -> str:
    body: dict = {"serverId": input.server_id}
    if input.name:
        body["name"] = input.name
    data = await _cloud(
        "POST",
        f"/cloud/coolify/apps/{input.coolify_app_uuid}/import",
        json_body=body,
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="cloud_list_easypanel_apps",
    group="cloud",
    display_name="List Easypanel apps",
    description=(
        "List projects and their services on the configured Easypanel "
        "instance (project, service, type). Read-only."
    ),
    sort_order=132,
    input_model=CallerTokenInput,
)
async def cloud_list_easypanel_apps(_: CallerTokenInput) -> str:
    data = await _cloud("GET", "/cloud/easypanel/apps")
    return arc_todo_client.format_result(data)


@register_tool(
    key="cloud_import_easypanel_app",
    group="cloud",
    display_name="Import Easypanel app",
    description=(
        "Read an Easypanel app service (source, env, domains, port, mounts) "
        "and create an arc-cloud draft app — nothing is deployed and no "
        "domains are claimed. Returns the side-by-side summary to review; "
        "then call cloud_confirm_import."
    ),
    sort_order=133,
    input_model=CloudImportEasypanelInput,
)
async def cloud_import_easypanel_app(input: CloudImportEasypanelInput) -> str:
    body: dict = {"serverId": input.server_id}
    if input.name:
        body["name"] = input.name
    data = await _cloud(
        "POST",
        f"/cloud/easypanel/apps/{input.project}/{input.service}/import",
        json_body=body,
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="cloud_confirm_import",
    group="cloud",
    display_name="Confirm imported app",
    description=(
        "Confirm a draft app created by a panel import — unlocks deploy and "
        "lifecycle actions. Refuses on apps that are not pending imports."
    ),
    sort_order=134,
    input_model=CloudAppIdInput,
)
async def cloud_confirm_import(input: CloudAppIdInput) -> str:
    data = await _cloud(
        "POST", f"/cloud/apps/{input.app_id}/confirm-import", json_body={}
    )
    return arc_todo_client.format_result(data)
