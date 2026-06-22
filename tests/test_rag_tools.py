import json

import pytest
import respx
from httpx import Response
from mcp.types import ListToolsRequest

from app.mcp_server import build_mcp_server
from app.rag_client import rag_client
from app.tools.handlers import retrieve_knowledge
from app.tool_registry import RetrieveKnowledgeInput


ORG_ID = "57df4a79-d87d-40e1-9fb0-2da29d8ebecf"
PROJECT_ID = "d576e04d-f683-4b88-a374-0aab28a4be10"


@pytest.fixture
def rag_env(monkeypatch):
    monkeypatch.setenv("RAG_API_BASE_URL", "http://rag.test")
    rag_client._base_url = "http://rag.test"


@pytest.fixture
def mock_token(monkeypatch):
    async def _token():
        return "token-abc"

    monkeypatch.setattr("app.tools.handlers.arc_todo_client.get_bearer_token", _token)


@pytest.mark.asyncio
async def test_build_mcp_server_includes_retrieve_knowledge():
    _, session_manager = build_mcp_server({"retrieve_knowledge"})
    list_tools_handler = session_manager.app.request_handlers[ListToolsRequest]
    result = await list_tools_handler(None)
    tool_names = {tool.name for tool in result.root.tools}
    assert "retrieve_knowledge" in tool_names


@pytest.mark.asyncio
@respx.mock
async def test_retrieve_knowledge_general_route(rag_env, mock_token):
    route = respx.post("http://rag.test/retrieve/general").mock(
        return_value=Response(
            200,
            json={
                "mode": "general",
                "question": "How do I deploy?",
                "chunks": [{"id": "c1", "text": "Deploy with Coolify"}],
                "tokenUsage": {"totalTokens": 10},
                "indexStatus": {"totalChunks": 1},
            },
        )
    )

    result = await retrieve_knowledge(
        RetrieveKnowledgeInput(question="How do I deploy?", top_k=3)
    )

    assert route.called
    body = json.loads(route.calls[0].request.content)
    assert body["question"] == "How do I deploy?"
    assert body["topK"] == 3
    assert body["maxContextTokens"] == 4000
    assert "organizationId" not in body
    assert "Deploy with Coolify" in result


@pytest.mark.asyncio
@respx.mock
async def test_retrieve_knowledge_project_route(rag_env, mock_token):
    route = respx.post("http://rag.test/retrieve/project").mock(
        return_value=Response(
            200,
            json={
                "mode": "project",
                "organizationId": ORG_ID,
                "projectId": PROJECT_ID,
                "question": "project docs",
                "chunks": [],
                "tokenUsage": {},
                "indexStatus": {},
            },
        )
    )

    await retrieve_knowledge(
        RetrieveKnowledgeInput(
            question="project docs",
            organization_id=ORG_ID,
            project_id=PROJECT_ID,
        )
    )

    assert route.called
    body = json.loads(route.calls[0].request.content)
    assert body["organizationId"] == ORG_ID
    assert body["projectId"] == PROJECT_ID
    assert route.calls[0].request.headers["authorization"] == "Bearer token-abc"


@pytest.mark.asyncio
async def test_retrieve_knowledge_rejects_partial_scope(mock_token):
    with pytest.raises(ValueError, match="organization_id and project_id"):
        await retrieve_knowledge(
            RetrieveKnowledgeInput(question="test", organization_id=ORG_ID)
        )


@pytest.mark.asyncio
@respx.mock
async def test_retrieve_knowledge_rag_disabled(rag_env, mock_token):
    respx.post("http://rag.test/retrieve/general").mock(
        return_value=Response(503, json={"detail": "RAG is disabled"})
    )

    result = await retrieve_knowledge(RetrieveKnowledgeInput(question="test"))

    assert '"error": "RAG is disabled"' in result
