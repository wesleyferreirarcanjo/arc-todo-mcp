import json

import pytest
import respx
from httpx import Response

from app.arc_todo_client import ArcTodoApiError, arc_todo_client
from app.caller_auth import MISSING_CALLER_TOKEN_MESSAGE
from app.tools.handlers import (
    create_seo_site,
    list_project_seo_sites,
    list_seo_keywords,
    run_seo_audit,
)
from app.tool_registry import (
    CreateSeoSiteInput,
    ListProjectSeoSitesInput,
    ListSeoKeywordsInput,
    RunSeoAuditInput,
)

ORG = "57df4a79-d87d-40e1-9fb0-2da29d8ebecf"
PROJECT = "d576e04d-f683-4b88-a374-0aab28a4be10"
SITE = "0c1e2d3a-4b5c-6789-abcd-ef0123456789"


def _point_client(monkeypatch):
    monkeypatch.setenv("ARC_TODO_API_BASE_URL", "http://api.test")
    monkeypatch.setenv("ARC_TODO_ACCESS_TOKEN", "service-token")
    arc_todo_client._base_url = "http://api.test"
    arc_todo_client._token = "service-token"


@pytest.mark.asyncio
@respx.mock
async def test_list_project_seo_sites_uses_caller_jwt(monkeypatch, caller_auth):
    _point_client(monkeypatch)
    route = respx.get(
        f"http://api.test/organizations/{ORG}/projects/{PROJECT}/seo-sites"
    ).mock(return_value=Response(200, json=[{"id": SITE, "hostname": "example.com"}]))

    result = await list_project_seo_sites(
        ListProjectSeoSitesInput(organization_id=ORG, project_id=PROJECT)
    )

    assert route.called
    assert route.calls[0].request.headers["Authorization"] == "Bearer token-abc"
    assert "example.com" in result
    assert "gscRefreshToken" not in result


@pytest.mark.asyncio
@respx.mock
async def test_create_seo_site_posts_hostname(monkeypatch, caller_auth):
    _point_client(monkeypatch)
    route = respx.post(
        f"http://api.test/organizations/{ORG}/projects/{PROJECT}/seo-sites"
    ).mock(return_value=Response(201, json={"id": SITE, "hostname": "example.com"}))

    result = await create_seo_site(
        CreateSeoSiteInput(
            organization_id=ORG,
            project_id=PROJECT,
            hostname="example.com",
        )
    )

    assert route.called
    body = json.loads(route.calls[0].request.content)
    assert body["hostname"] == "example.com"
    assert "example.com" in result


@pytest.mark.asyncio
@respx.mock
async def test_run_seo_audit_posts_audit(monkeypatch, caller_auth):
    _point_client(monkeypatch)
    route = respx.post(
        f"http://api.test/organizations/{ORG}/projects/{PROJECT}/seo-sites/{SITE}/audit"
    ).mock(return_value=Response(201, json={"id": "run-1", "status": "queued"}))

    result = await run_seo_audit(
        RunSeoAuditInput(organization_id=ORG, project_id=PROJECT, site_id=SITE)
    )

    assert route.called
    assert "run-1" in result


@pytest.mark.asyncio
@respx.mock
async def test_list_seo_keywords_posts_keywords(monkeypatch, caller_auth):
    _point_client(monkeypatch)
    route = respx.post(
        f"http://api.test/organizations/{ORG}/projects/{PROJECT}/seo-sites/{SITE}/keywords"
    ).mock(
        return_value=Response(
            400,
            json={
                "code": "ERR-ARC-SEO-06",
                "message": "Connect Search Console for this site first.",
            },
        )
    )

    with pytest.raises(ArcTodoApiError, match="Connect Search Console"):
        await list_seo_keywords(
            ListSeoKeywordsInput(
                organization_id=ORG, project_id=PROJECT, site_id=SITE
            )
        )
    assert route.called


@pytest.mark.asyncio
async def test_list_project_seo_sites_does_not_use_service_account(monkeypatch):
    _point_client(monkeypatch)
    with pytest.raises(ArcTodoApiError, match="arc_todo_token"):
        await list_project_seo_sites(
            ListProjectSeoSitesInput(organization_id=ORG, project_id=PROJECT)
        )
    assert MISSING_CALLER_TOKEN_MESSAGE
