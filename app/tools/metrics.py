from __future__ import annotations

from pydantic import Field

from app.arc_todo_client import arc_todo_client
from app.tool_registry import CallerTokenInput, register_tool

# Same convention as the cloud/observer tools: mark the call's origin so
# server-side logs can tell MCP traffic from UI traffic.
_MCP_SOURCE_HEADER = {"X-Arc-Source": "mcp"}

METRICS_WINDOW_DESCRIPTION = "Time window: 1h | 24h | 7d | 30d | 1y"


async def _metrics(
    method: str, path: str, *, json_body: dict | None = None
) -> object:
    return await arc_todo_client.request(
        method, path, json_body=json_body, extra_headers=_MCP_SOURCE_HEADER
    )


class MetricsListServersInput(CallerTokenInput):
    pass


class MetricsServerResourcesInput(CallerTokenInput):
    server_id: str = Field(
        description="Metrics server UUID from metrics_list_servers"
    )
    window: str = Field(
        default="24h",
        description=METRICS_WINDOW_DESCRIPTION,
    )


class MetricsServerSeriesInput(CallerTokenInput):
    server_id: str = Field(
        description="Metrics server UUID from metrics_list_servers"
    )
    window: str = Field(
        default="24h",
        description=METRICS_WINDOW_DESCRIPTION,
    )


class MetricsResourceSeriesInput(CallerTokenInput):
    resource_id: int = Field(
        ge=1,
        description="Resource id from metrics_server_resources",
    )
    window: str = Field(
        default="24h",
        description=METRICS_WINDOW_DESCRIPTION,
    )


class MetricsListAgentTokensInput(CallerTokenInput):
    pass


class MetricsCreateAgentTokenInput(CallerTokenInput):
    server_name: str = Field(
        description="Server name for the token (lowercase, e.g. arc-lab-1)."
    )


class MetricsRevokeAgentTokenInput(CallerTokenInput):
    token_id: str = Field(
        description="Agent token UUID from metrics_list_agent_tokens"
    )
    confirm: bool = Field(
        default=False,
        description="Must be true to revoke the token",
    )


@register_tool(
    key="metrics_list_servers",
    group="metrics",
    display_name="List metrics servers",
    description=(
        "List servers reporting to arc-todo-metrics with status "
        "(online/stale/revoked), hostname, and current host CPU/memory/disk."
    ),
    sort_order=150,
    input_model=MetricsListServersInput,
)
async def metrics_list_servers(_: MetricsListServersInput) -> str:
    data = await _metrics("GET", "/metrics/servers")
    return arc_todo_client.format_result(data)


@register_tool(
    key="metrics_server_resources",
    group="metrics",
    display_name="List server app resources",
    description=(
        "List the app/container resources on one metrics server with "
        "windowed CPU/memory averages and peaks. Same rows as the Metrics "
        "page app table."
    ),
    sort_order=151,
    input_model=MetricsServerResourcesInput,
)
async def metrics_server_resources(input: MetricsServerResourcesInput) -> str:
    data = await _metrics(
        "GET",
        f"/metrics/servers/{input.server_id}/resources?window={input.window}",
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="metrics_server_series",
    group="metrics",
    display_name="Server host series",
    description=(
        "Time series for one server's host metrics (CPU, memory, disk, "
        "network, restarts) over the window, bucketed to at most 500 points."
    ),
    sort_order=152,
    input_model=MetricsServerSeriesInput,
)
async def metrics_server_series(input: MetricsServerSeriesInput) -> str:
    data = await _metrics(
        "GET",
        f"/metrics/servers/{input.server_id}/series?window={input.window}",
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="metrics_resource_series",
    group="metrics",
    display_name="App resource series",
    description=(
        "Time series for one app/container resource (CPU, memory, network, "
        "disk, restarts, OOM kills) over the window."
    ),
    sort_order=153,
    input_model=MetricsResourceSeriesInput,
)
async def metrics_resource_series(input: MetricsResourceSeriesInput) -> str:
    data = await _metrics(
        "GET",
        f"/metrics/resources/{input.resource_id}/series?window={input.window}",
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="metrics_list_agent_tokens",
    group="metrics",
    display_name="List metrics agent tokens",
    description=(
        "List metrics agent tokens (one per server). Returns id, server "
        "name, created/revoked/last-seen timestamps. Token values are never shown."
    ),
    sort_order=154,
    input_model=MetricsListAgentTokensInput,
)
async def metrics_list_agent_tokens(_: MetricsListAgentTokensInput) -> str:
    data = await _metrics("GET", "/metrics/agent-tokens")
    return arc_todo_client.format_result(data)


@register_tool(
    key="metrics_create_agent_token",
    group="metrics",
    display_name="Create metrics agent token",
    description=(
        "Create an ingest token for a server name. The amt_ token is "
        "returned exactly once — copy it into the agent METRICS_AGENT_TOKEN."
    ),
    sort_order=155,
    input_model=MetricsCreateAgentTokenInput,
)
async def metrics_create_agent_token(
    input: MetricsCreateAgentTokenInput,
) -> str:
    data = await _metrics(
        "POST",
        "/metrics/agent-tokens",
        json_body={"serverName": input.server_name},
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="metrics_revoke_agent_token",
    group="metrics",
    display_name="Revoke metrics agent token",
    description=(
        "Revoke a metrics agent token by id. Requires confirm=true. "
        "The agent on that server stops reporting metrics."
    ),
    default_enabled=False,
    sort_order=156,
    input_model=MetricsRevokeAgentTokenInput,
)
async def metrics_revoke_agent_token(
    input: MetricsRevokeAgentTokenInput,
) -> str:
    if not input.confirm:
        return (
            "Refused: pass confirm=true to revoke this metrics agent token — "
            "the agent on that server stops reporting metrics."
        )
    await _metrics("DELETE", f"/metrics/agent-tokens/{input.token_id}")
    return arc_todo_client.format_result({"revoked": input.token_id})


class MetricsListAppTokensInput(CallerTokenInput):
    pass


class MetricsCreateAppTokenInput(CallerTokenInput):
    app: str = Field(
        min_length=1,
        max_length=200,
        description=(
            "App key the token writes for, e.g. arccloud:my-app or a "
            "free-form name. All metrics sent with the token land under this app."
        ),
    )


class MetricsRevokeAppTokenInput(CallerTokenInput):
    token_id: str = Field(
        description="App token UUID from metrics_list_app_tokens"
    )
    confirm: bool = Field(
        default=False,
        description="Must be true to revoke the token",
    )


class MetricsAppMetricsInput(CallerTokenInput):
    app: str | None = Field(
        default=None,
        description="Optional app key filter, e.g. arccloud:my-app.",
    )


class MetricsAppSeriesInput(CallerTokenInput):
    app: str = Field(description="App key, e.g. arccloud:my-app.")
    metric: str = Field(
        description="Custom metric name from metrics_app_metrics."
    )
    window: str = Field(
        default="24h",
        description=METRICS_WINDOW_DESCRIPTION,
    )


@register_tool(
    key="metrics_list_app_tokens",
    group="metrics",
    display_name="List metrics app tokens",
    description=(
        "List metrics app-ingest tokens (aap_, one per app key). Returns id, "
        "app, created/revoked/last-seen timestamps. Token values are never shown."
    ),
    sort_order=157,
    input_model=MetricsListAppTokensInput,
)
async def metrics_list_app_tokens(_: MetricsListAppTokensInput) -> str:
    data = await _metrics("GET", "/metrics/app-tokens")
    return arc_todo_client.format_result(data)


@register_tool(
    key="metrics_create_app_token",
    group="metrics",
    display_name="Create metrics app token",
    description=(
        "Create an app-ingest token bound to an app key (e.g. arccloud:my-app "
        "or a free-form name). The aap_ token is returned exactly once — put "
        "it in the app's metrics SDK config."
    ),
    sort_order=158,
    input_model=MetricsCreateAppTokenInput,
)
async def metrics_create_app_token(input: MetricsCreateAppTokenInput) -> str:
    data = await _metrics(
        "POST",
        "/metrics/app-tokens",
        json_body={"app": input.app},
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="metrics_revoke_app_token",
    group="metrics",
    display_name="Revoke metrics app token",
    description=(
        "Revoke a metrics app-ingest token by id. Requires confirm=true. "
        "The app stops being able to send metrics."
    ),
    default_enabled=False,
    sort_order=159,
    input_model=MetricsRevokeAppTokenInput,
)
async def metrics_revoke_app_token(input: MetricsRevokeAppTokenInput) -> str:
    if not input.confirm:
        return (
            "Refused: pass confirm=true to revoke this metrics app token — "
            "the app stops being able to send metrics."
        )
    await _metrics("DELETE", f"/metrics/app-tokens/{input.token_id}")
    return arc_todo_client.format_result({"revoked": input.token_id})


@register_tool(
    key="metrics_app_metrics",
    group="metrics",
    display_name="List app custom metrics",
    description=(
        "List custom app metrics ingested through the SDK "
        "(POST /v1/apps/ingest/metrics). Optionally filter by app key. "
        "Returns one row per (app, metric) with series count and last-seen timestamp."
    ),
    sort_order=160,
    input_model=MetricsAppMetricsInput,
)
async def metrics_app_metrics(input: MetricsAppMetricsInput) -> str:
    query = ""
    if input.app:
        from urllib.parse import urlencode

        query = f"?{urlencode({'app': input.app})}"
    data = await _metrics("GET", f"/metrics/app-metrics{query}")
    return arc_todo_client.format_result(data)


@register_tool(
    key="metrics_app_series",
    group="metrics",
    display_name="App custom metric series",
    description=(
        "Time series for one custom app metric (SDK ingest) over the window, "
        "one line per label set, bucketed to at most 500 points."
    ),
    sort_order=161,
    input_model=MetricsAppSeriesInput,
)
async def metrics_app_series(input: MetricsAppSeriesInput) -> str:
    from urllib.parse import urlencode

    query = urlencode(
        {"app": input.app, "metric": input.metric, "window": input.window}
    )
    data = await _metrics("GET", f"/metrics/app-series?{query}")
    return arc_todo_client.format_result(data)
