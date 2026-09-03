import json

import pytest
import respx
from httpx import Response

from app.arc_todo_client import arc_todo_client
from app.tools.handlers import add_name_candidates, check_name_candidate
from app.tool_registry import AddNameCandidatesInput, CheckNameCandidateInput, NameCandidateItemInput

ORG = "57df4a79-d87d-40e1-9fb0-2da29d8ebecf"
PROJECT = "d576e04d-f683-4b88-a374-0aab28a4be10"
SESSION = "3f5d500d-58f6-4469-8230-f41d27a2511c"


@pytest.mark.asyncio
@respx.mock
async def test_add_name_candidates_forces_mcp_source(monkeypatch, caller_auth):
    monkeypatch.setenv("ARC_TODO_API_BASE_URL", "http://api.test")
    monkeypatch.setenv("ARC_TODO_ACCESS_TOKEN", "token-abc")
    arc_todo_client._base_url = "http://api.test"
    arc_todo_client._token = "token-abc"

    route = respx.post(
        f"http://api.test/organizations/{ORG}/projects/{PROJECT}/name-sessions/{SESSION}/candidates"
    ).mock(
        return_value=Response(
            201,
            json={
                "candidates": [
                    {"id": "cand-1", "name": "Helios", "sources": ["mcp"]}
                ]
            },
        )
    )

    result = await add_name_candidates(
        AddNameCandidatesInput(
            organization_id=ORG,
            project_id=PROJECT,
            name_session_id=SESSION,
            candidates=[NameCandidateItemInput(name="Helios", family="invented")],
        )
    )

    assert route.called
    body = json.loads(route.calls[0].request.content)
    assert body["source"] == "mcp"
    assert body["candidates"][0]["name"] == "Helios"
    assert '"sources": [' in result or "Helios" in result


@pytest.mark.asyncio
@respx.mock
async def test_check_name_candidate_uses_session_name(monkeypatch, caller_auth):
    monkeypatch.setenv("ARC_TODO_API_BASE_URL", "http://api.test")
    monkeypatch.setenv("ARC_TODO_ACCESS_TOKEN", "token-abc")
    arc_todo_client._base_url = "http://api.test"
    arc_todo_client._token = "token-abc"

    respx.get(
        f"http://api.test/organizations/{ORG}/projects/{PROJECT}/name-sessions/{SESSION}"
    ).mock(
        return_value=Response(
            200,
            json={
                "id": SESSION,
                "candidates": [{"id": "cand-1", "name": "Helios"}],
            },
        )
    )
    check = respx.post(
        f"http://api.test/organizations/{ORG}/projects/{PROJECT}/name-sessions/{SESSION}/check"
    ).mock(
        return_value=Response(
            200,
            json={
                "id": "cand-1",
                "name": "Helios",
                "domainChecks": [{"host": "helios.com", "availability": "unknown"}],
            },
        )
    )

    result = await check_name_candidate(
        CheckNameCandidateInput(
            organization_id=ORG,
            project_id=PROJECT,
            name_session_id=SESSION,
            candidate_id="cand-1",
        )
    )

    assert check.called
    body = json.loads(check.calls[0].request.content)
    assert body == {"name": "Helios"}
    assert "unknown" in result
    assert "buy" not in result.lower()


def test_names_catalog_does_not_create_sessions():
    from app.tools import handlers as _handlers  # noqa: F401
    from app.tool_registry import MCP_TOOL_REGISTRY

    keys = {item.key for item in MCP_TOOL_REGISTRY if item.group == "names"}
    assert "create_name_session" not in keys
    assert {
        "list_project_name_sessions",
        "get_name_session",
        "update_name_session",
        "add_name_candidates",
        "check_name_candidate",
        "recommend_name_candidate",
    } <= keys
