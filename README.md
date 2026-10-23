# Arc Todo MCP

Python FastAPI MCP server for Arc Todo. Exposes Streamable HTTP MCP at `/mcp` and wraps the existing Arc Todo REST API for tasks and workspace context.

## Prerequisites

- Python 3.11+
- Running [arc-todo-api](../arc-todo-api)

## Setup

```bash
cd arc-todo-mcp
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env
```

## Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `PORT` | `8000` | HTTP port |
| `ARC_TODO_API_BASE_URL` | `http://localhost:3000` | Arc Todo API base URL |
| `ARC_TODO_ACCESS_TOKEN` | — | Required service JWT (startup `/mcp-tools/enabled`; no password login) |
| `ARC_HUB_BASE_URL` | — | arc-hub origin; enables the `hub_*` admin tools (unset disables them with a "not configured" error) |
| `ARC_HUB_TOKEN` | — | Server-side hub bearer for `hub_*` tools; never a tool argument |
| `MCP_TOOL_SETTINGS_REFRESH_ON_START` | `true` | Load enabled tools from API on startup |

## Run locally

```bash
uvicorn app.main:app --reload --port 8000
```

Endpoints:

- `GET /health` → `{ "status": "ok" }`
- `POST /mcp` → Streamable HTTP MCP transport

Configure enabled tools in the web app at `/settings/mcp-tools`, then restart this service so MCP discovery reflects the saved settings.

## Tests

```bash
pytest
```

## Deployment

See [coolify.md](./coolify.md).
