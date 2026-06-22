# Arc Todo MCP

Python FastAPI MCP server for Arc Todo. Exposes Streamable HTTP MCP at `/mcp` and wraps the existing Arc Todo REST API for tasks, knowledge, and workspace context.

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
| `ARC_TODO_USERNAME` | — | Service account username |
| `ARC_TODO_PASSWORD` | — | Service account password |
| `ARC_TODO_ACCESS_TOKEN` | — | Optional pre-issued bearer token |
| `MCP_TOOL_SETTINGS_REFRESH_ON_START` | `true` | Load enabled tools from API on startup |
| `RAG_API_BASE_URL` | `http://localhost:8020` | Arc Todo RAG service base URL |
| `RAG_TIMEOUT_SECONDS` | `30` | RAG HTTP request timeout |
| `RAG_TOP_K` | `5` | Default max chunks when not specified in tool call |
| `RAG_MAX_CONTEXT_TOKENS` | `4000` | Default context token budget when not specified |

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
