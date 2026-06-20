# Coolify — arc-todo MCP

Python FastAPI MCP server deployed in Coolify project **`arc-todo`** on server **`main`** (`72.60.59.203`).

## Project

| Field | Value |
| --- | --- |
| Coolify project name | `arc-todo` |
| Coolify project UUID | `qzmm8hhki6jz02yrrc21zung` |
| Environment | `production` (`oqofaco0eved39jqee22w7jo`) |
| Server UUID | `r9rokxstz1zlccajjxyenk93` |
| Destination UUID | `wchjqtdyj949s0ale2zofwgd` |

## This application

| Field | Value |
| --- | --- |
| Coolify resource name | `arc-todo-mcp` |
| Application UUID | `qv9bek5he3ns8upu71rphbrc` |
| Repository | [wesleyferreirarcanjo/arc-todo-mcp](https://github.com/wesleyferreirarcanjo/arc-todo-mcp) |
| Branch | `main` |
| Build pack | Dockerfile |
| Public URL | `http://qv9bek5he3ns8upu71rphbrc.72.60.59.203.sslip.io` |
| MCP endpoint | `http://qv9bek5he3ns8upu71rphbrc.72.60.59.203.sslip.io/mcp` |
| Health check | `GET /health` → `{ "status": "ok" }` |

### Build / run

| Step | Command |
| --- | --- |
| Build | `docker build -f Dockerfile .` |
| Start | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Port | `8000` |

## Related resources

| Resource | UUID | Notes |
| --- | --- | --- |
| API `arc-todo-api` | `lmsx2avrg1k29ex12w6e3gce` | `http://lmsx2avrg1k29ex12w6e3gce.72.60.59.203.sslip.io` |
| Frontend `arc-todo-web` | `ifo33mi1s8efs8myb5g441vh` | MCP tool settings UI |
| PostgreSQL `arc-todo-postgres` | `bibl6ncxa3xkph2r8ubmbl4t` | Stores MCP tool settings via API |
| Chatbot `arc-todo-chatbot` | `nyagev0aqp4qow1zri6wise5` | `http://nyagev0aqp4qow1zri6wise5.72.60.59.203.sslip.io` |
| MinIO `arc-todo-minio` | `jsx5tkzb1b8hj5oz0ydt491u` | Used by API only |

## Environment variables (production)

Secrets are stored in Coolify only. Do not commit real values.

| Variable | Purpose |
| --- | --- |
| `PORT` | `8000` |
| `ARC_TODO_API_BASE_URL` | Public or internal API URL |
| `ARC_TODO_USERNAME` | Service account username |
| `ARC_TODO_PASSWORD` | *(redacted — Coolify secret)* |
| `ARC_TODO_ACCESS_TOKEN` | Optional bearer token instead of username/password |
| `MCP_TOOL_SETTINGS_REFRESH_ON_START` | `true` |

## Deploy order

1. Ensure `arc-todo-postgres` is `running:healthy`.
2. Ensure `arc-todo-minio` is `running:healthy`.
3. Deploy / restart `arc-todo-api` so the `mcp_tool_settings` migration runs.
4. Deploy `arc-todo-web` so `/settings/mcp-tools` is available.
5. Configure enabled MCP tools in the web app.
6. Deploy / restart `arc-todo-mcp` so it loads enabled tools on startup.
7. Deploy / restart `arc-todo-chatbot` after chatbot settings are configured in the web app (see [../arc-todo-chatbot/coolify.md](../arc-todo-chatbot/coolify.md)).

## Notes

- Disabled tools are omitted from MCP discovery after the MCP service restarts.
- Tool settings are stored in PostgreSQL through `arc-todo-api`, not in this service.
- Git source uses the Coolify deploy key (`private_key_uuid`: `lms2y9fjpybdznft4t7uf3td`). Repository is public (same as API/web).
- See [../arc-todo-api/coolify.md](../arc-todo-api/coolify.md), [../arc-todo-web/coolify.md](../arc-todo-web/coolify.md), and [../arc-todo-chatbot/coolify.md](../arc-todo-chatbot/coolify.md).
