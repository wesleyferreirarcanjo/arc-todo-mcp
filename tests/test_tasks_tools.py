import pytest
from mcp.types import ListToolsRequest

from app.mcp_server import build_mcp_server


@pytest.mark.asyncio
async def test_build_mcp_server_registers_only_enabled_tools():
    enabled = {"check_arc_todo_api_health", "list_tasks"}
    _, session_manager = build_mcp_server(enabled)

    list_tools_handler = session_manager.app.request_handlers[ListToolsRequest]
    result = await list_tools_handler(None)
    tools = result.root.tools
    tool_names = {tool.name for tool in tools}

    assert "check_arc_todo_api_health" in tool_names
    assert "list_tasks" in tool_names
    assert "create_task" not in tool_names
