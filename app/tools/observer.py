from __future__ import annotations

from pydantic import Field

from app.arc_todo_client import arc_todo_client
from app.tool_registry import CallerTokenInput, register_tool

_MCP_SOURCE_HEADER = {"X-Arc-Source": "mcp"}


async def _observer(
    method: str, path: str, *, json_body: dict | None = None
) -> object:
    return await arc_todo_client.request(
        method, path, json_body=json_body, extra_headers=_MCP_SOURCE_HEADER
    )


class ObserverSearchInput(CallerTokenInput):
    server: str | None = Field(
        default=None,
        description="Server name or UUID. Omit to search all servers.",
    )
    app: str | None = Field(
        default=None,
        description="Application/container name filter.",
    )
    q: str | None = Field(
        default=None,
        description="Free-text substring filter on the log message.",
    )
    level: str | None = Field(
        default=None,
        description="trace | debug | info | warn | error",
    )
    from_ms: int | None = Field(
        default=None,
        description="Inclusive lower bound, epoch milliseconds.",
    )
    to_ms: int | None = Field(
        default=None,
        description="Inclusive upper bound, epoch milliseconds.",
    )
    before_ms: int | None = Field(
        default=None,
        description="Pagination: exclusive upper bound for the next older page.",
    )
    limit: int | None = Field(
        default=None, ge=1, le=1000, description="Max lines, 1-1000 (default 200)."
    )


class ObserverTailInput(CallerTokenInput):
    server: str | None = Field(
        default=None, description="Server name or UUID filter."
    )
    app: str | None = Field(default=None, description="App/container filter.")
    after_ms: int | None = Field(
        default=None,
        description="Only lines newer than this epoch-millis cursor.",
    )
    limit: int | None = Field(
        default=None, ge=1, le=500, description="Max lines, 1-500 (default 100)."
    )


class ObserverExplainInput(CallerTokenInput):
    server_id: str | None = Field(
        default=None, description="Optional server UUID scope."
    )
    app: str | None = Field(default=None, description="Optional app scope.")
    minutes: int | None = Field(
        default=None,
        ge=1,
        le=1440,
        description="Look-back window in minutes (default 60, max 1440).",
    )
    query: str | None = Field(
        default=None,
        description="Optional question, e.g. 'why did the app restart'.",
    )


class ObserverListTokensInput(CallerTokenInput):
    pass


class ObserverCreateTokenInput(CallerTokenInput):
    server_name: str = Field(
        description="Server name for the token (lowercase, e.g. arc-lab-1)."
    )


class ObserverRevokeTokenInput(CallerTokenInput):
    token_id: str = Field(description="Observer token UUID from observer_list_tokens")
    confirm: bool = Field(
        default=False,
        description="Must be true to revoke the token",
    )


def _search_query(input: ObserverSearchInput) -> str:
    params: dict[str, str] = {}
    if input.server:
        params["server"] = input.server
    if input.app:
        params["app"] = input.app
    if input.q:
        params["q"] = input.q
    if input.level:
        params["level"] = input.level
    if input.from_ms is not None:
        params["fromMs"] = str(input.from_ms)
    if input.to_ms is not None:
        params["toMs"] = str(input.to_ms)
    if input.before_ms is not None:
        params["beforeMs"] = str(input.before_ms)
    if input.limit is not None:
        params["limit"] = str(input.limit)
    if not params:
        return ""
    from urllib.parse import urlencode

    return f"?{urlencode(params)}"


@register_tool(
    key="observer_search",
    group="observer",
    display_name="Search logs",
    description=(
        "Search collected container logs across servers. Filter by server, "
        "app, level, free text, and epoch-millis bounds. Returns newest-first "
        "lines with has_more; pass the oldest line ts as before_ms to page back."
    ),
    sort_order=140,
    input_model=ObserverSearchInput,
)
async def observer_search(input: ObserverSearchInput) -> str:
    data = await _observer("GET", f"/observer/logs{_search_query(input)}")
    return arc_todo_client.format_result(data)


@register_tool(
    key="observer_tail",
    group="observer",
    display_name="Tail logs",
    description=(
        "Read the newest container log lines for a server/app, oldest first. "
        "Pass the newest returned line ts as after_ms to fetch only newer "
        "lines on the next call."
    ),
    sort_order=141,
    input_model=ObserverTailInput,
)
async def observer_tail(input: ObserverTailInput) -> str:
    params: dict[str, str] = {}
    if input.server:
        params["server"] = input.server
    if input.app:
        params["app"] = input.app
    if input.after_ms is not None:
        params["afterMs"] = str(input.after_ms)
    if input.limit is not None:
        params["limit"] = str(input.limit)
    query = ""
    if params:
        from urllib.parse import urlencode

        query = f"?{urlencode(params)}"
    data = await _observer("GET", f"/observer/tail{query}")
    return arc_todo_client.format_result(data)


@register_tool(
    key="observer_explain",
    group="observer",
    display_name="Explain error logs",
    description=(
        "Ask the AI to explain recent error-level log lines (default: last 60 "
        "minutes, up to 24h). Optionally scope to a server/app and add a "
        "question. Powered by arc-todo-chatbot (DeepSeek)."
    ),
    sort_order=142,
    input_model=ObserverExplainInput,
)
async def observer_explain(input: ObserverExplainInput) -> str:
    body = {
        key: value
        for key, value in {
            "serverId": input.server_id,
            "app": input.app,
            "minutes": input.minutes,
            "query": input.query,
        }.items()
        if value is not None
    }
    data = await _observer("POST", "/observer/explain", json_body=body)
    return arc_todo_client.format_result(data)


@register_tool(
    key="observer_list_tokens",
    group="observer",
    display_name="List observer agent tokens",
    description=(
        "List observer ingest tokens (one per server). Returns id, server "
        "name, created/revoked/last-seen timestamps. Token values are never shown."
    ),
    sort_order=143,
    input_model=ObserverListTokensInput,
)
async def observer_list_tokens(_: ObserverListTokensInput) -> str:
    data = await _observer("GET", "/observer/agent-tokens")
    return arc_todo_client.format_result(data)


@register_tool(
    key="observer_create_token",
    group="observer",
    display_name="Create observer agent token",
    description=(
        "Create an ingest token for a server name. The aob_ token is "
        "returned exactly once — copy it into the agent OBSERVER_AGENT_TOKEN."
    ),
    sort_order=144,
    input_model=ObserverCreateTokenInput,
)
async def observer_create_token(input: ObserverCreateTokenInput) -> str:
    data = await _observer(
        "POST",
        "/observer/agent-tokens",
        json_body={"serverName": input.server_name},
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="observer_revoke_token",
    group="observer",
    display_name="Revoke observer agent token",
    description=(
        "Revoke an observer ingest token by id. Requires confirm=true. "
        "The agent on that server stops shipping logs."
    ),
    default_enabled=False,
    sort_order=145,
    input_model=ObserverRevokeTokenInput,
)
async def observer_revoke_token(input: ObserverRevokeTokenInput) -> str:
    if not input.confirm:
        return (
            "Refused: pass confirm=true to revoke this observer token — the "
            "agent on that server stops shipping logs."
        )
    await _observer("DELETE", f"/observer/agent-tokens/{input.token_id}")
    return arc_todo_client.format_result({"revoked": input.token_id})


class ObserverListAppTokensInput(CallerTokenInput):
    pass


class ObserverCreateAppTokenInput(CallerTokenInput):
    app: str = Field(
        min_length=1,
        max_length=200,
        description=(
            "App key the token writes for, e.g. arccloud:my-app or a "
            "free-form name. All logs sent with the token land under this app."
        ),
    )


class ObserverRevokeAppTokenInput(CallerTokenInput):
    token_id: str = Field(
        description="App token UUID from observer_list_app_tokens"
    )
    confirm: bool = Field(
        default=False,
        description="Must be true to revoke the token",
    )


@register_tool(
    key="observer_list_app_tokens",
    group="observer",
    display_name="List observer app tokens",
    description=(
        "List observer app-ingest tokens (aap_, one per app key). Returns id, "
        "app, created/revoked/last-seen timestamps. Token values are never shown."
    ),
    sort_order=146,
    input_model=ObserverListAppTokensInput,
)
async def observer_list_app_tokens(_: ObserverListAppTokensInput) -> str:
    data = await _observer("GET", "/observer/app-tokens")
    return arc_todo_client.format_result(data)


@register_tool(
    key="observer_create_app_token",
    group="observer",
    display_name="Create observer app token",
    description=(
        "Create an app-ingest token bound to an app key (e.g. arccloud:my-app "
        "or a free-form name). The aap_ token is returned exactly once — put "
        "it in the app's log SDK config."
    ),
    sort_order=147,
    input_model=ObserverCreateAppTokenInput,
)
async def observer_create_app_token(input: ObserverCreateAppTokenInput) -> str:
    data = await _observer(
        "POST",
        "/observer/app-tokens",
        json_body={"app": input.app},
    )
    return arc_todo_client.format_result(data)


@register_tool(
    key="observer_revoke_app_token",
    group="observer",
    display_name="Revoke observer app token",
    description=(
        "Revoke an observer app-ingest token by id. Requires confirm=true. "
        "The app stops being able to send logs."
    ),
    default_enabled=False,
    sort_order=148,
    input_model=ObserverRevokeAppTokenInput,
)
async def observer_revoke_app_token(input: ObserverRevokeAppTokenInput) -> str:
    if not input.confirm:
        return (
            "Refused: pass confirm=true to revoke this observer app token — "
            "the app stops being able to send logs."
        )
    await _observer("DELETE", f"/observer/app-tokens/{input.token_id}")
    return arc_todo_client.format_result({"revoked": input.token_id})
