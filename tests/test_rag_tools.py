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


@pytest.mark.asyncio
async def test_build_mcp_server_includes_retrieve_knowledge():
    _, session_manager = build_mcp_server({"retrieve_knowledge"})
    list_tools_handler = session_manager.app.request_handlers[ListToolsRequest]
    result = await list_tools_handler(None)
    tool_names = {tool.name for tool in result.root.tools}
    assert "retrieve_knowledge" in tool_names


@pytest.mark.asyncio
@respx.mock
async def test_retrieve_knowledge_general_route(rag_env, caller_auth):
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
    assert route.calls[0].request.headers["authorization"] == "Bearer token-abc"


@pytest.mark.asyncio
@respx.mock
async def test_retrieve_knowledge_project_route(rag_env, caller_auth):
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
@respx.mock
async def test_retrieve_knowledge_organization_route(rag_env, caller_auth):
    route = respx.post("http://rag.test/retrieve/organization").mock(
        return_value=Response(
            200,
            json={
                "mode": "organization",
                "organizationId": ORG_ID,
                "question": "org docs",
                "chunks": [],
                "tokenUsage": {},
                "indexStatus": {},
            },
        )
    )

    await retrieve_knowledge(
        RetrieveKnowledgeInput(
            question="org docs",
            organization_id=ORG_ID,
        )
    )

    assert route.called
    body = json.loads(route.calls[0].request.content)
    assert body["organizationId"] == ORG_ID
    assert "projectId" not in body


@pytest.mark.asyncio
@respx.mock
async def test_retrieve_knowledge_person_route(rag_env, caller_auth):
    person_id = "person-123"
    route = respx.post("http://rag.test/retrieve/person").mock(
        return_value=Response(
            200,
            json={
                "mode": "person",
                "personId": person_id,
                "question": "contact notes",
                "chunks": [],
                "tokenUsage": {},
                "indexStatus": {},
            },
        )
    )

    await retrieve_knowledge(
        RetrieveKnowledgeInput(
            question="contact notes",
            person_id=person_id,
        )
    )

    assert route.called
    body = json.loads(route.calls[0].request.content)
    assert body["personId"] == person_id


@pytest.mark.asyncio
async def test_retrieve_knowledge_rejects_project_without_org(caller_auth):
    with pytest.raises(ValueError, match="organization_id is required"):
        await retrieve_knowledge(
            RetrieveKnowledgeInput(question="test", project_id=PROJECT_ID)
        )


@pytest.mark.asyncio
async def test_retrieve_knowledge_requires_caller_token(rag_env):
    with pytest.raises(ValueError, match="Missing Authorization bearer token"):
        await retrieve_knowledge(RetrieveKnowledgeInput(question="test"))


@pytest.mark.asyncio
@respx.mock
async def test_retrieve_knowledge_rag_disabled(rag_env, caller_auth):
    respx.post("http://rag.test/retrieve/general").mock(
        return_value=Response(503, json={"detail": "RAG is disabled"})
    )

    result = await retrieve_knowledge(RetrieveKnowledgeInput(question="test"))

    assert '"error": "RAG is disabled"' in result
