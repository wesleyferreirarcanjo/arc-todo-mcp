from __future__ import annotations

import contextlib
from typing import Any

from mcp.server import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.types import TextContent, Tool
from starlette.applications import Starlette
from starlette.routing import Mount
from pydantic import BaseModel

from app.tool_registry import MCP_TOOL_REGISTRY, ToolDefinition

# Import handlers so @register_tool decorators populate MCP_TOOL_REGISTRY.
import app.tools.handlers  # noqa: F401


def _json_schema(model: type[BaseModel] | None) -> dict[str, Any]:
    if model is None:
        return {"type": "object", "properties": {}, "additionalProperties": False}
    schema = model.model_json_schema()
    schema.setdefault("additionalProperties", False)
    return schema


def build_mcp_server(enabled_keys: set[str]) -> tuple[Server, StreamableHTTPSessionManager]:
    from app.tools.handlers import set_enabled_keys

    set_enabled_keys(enabled_keys)

    enabled_tools: dict[str, ToolDefinition] = {
        tool.key: tool
        for tool in sorted(MCP_TOOL_REGISTRY, key=lambda t: t.sort_order)
        if tool.key in enabled_keys
    }

    server = Server("arc-todo")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name=tool.key,
                description=tool.description,
                inputSchema=_json_schema(tool.input_model),
            )
            for tool in enabled_tools.values()
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        tool = enabled_tools.get(name)
        if tool is None:
            raise ValueError(f"Tool '{name}' is not enabled")

        if tool.input_model is None:
            result = await tool.handler(None)
        else:
            validated = tool.input_model.model_validate(arguments)
            result = await tool.handler(validated)

        return [TextContent(type="text", text=result)]

    session_manager = StreamableHTTPSessionManager(server)
    return server, session_manager


def build_mcp_asgi_app(session_manager: StreamableHTTPSessionManager) -> Starlette:
    from mcp.server.fastmcp.server import StreamableHTTPASGIApp

    return Starlette(routes=[Mount("/", app=StreamableHTTPASGIApp(session_manager))])


@contextlib.asynccontextmanager
async def mcp_lifespan(session_manager: StreamableHTTPSessionManager):
    async with session_manager.run():
        yield
