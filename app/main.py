from __future__ import annotations

import contextlib

from fastapi import FastAPI

from app.mcp_server import build_mcp_asgi_app, build_mcp_server, mcp_lifespan
from app.tool_settings import fetch_enabled_tool_keys


@contextlib.asynccontextmanager
async def lifespan(application: FastAPI):
    enabled_keys = await fetch_enabled_tool_keys()
    _, session_manager = build_mcp_server(enabled_keys)
    application.mount("/mcp", build_mcp_asgi_app(session_manager))
    async with mcp_lifespan(session_manager):
        yield


app = FastAPI(title="Arc Todo MCP", lifespan=lifespan)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
