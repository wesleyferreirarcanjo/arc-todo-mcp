from __future__ import annotations

from typing import Any

import httpx

from app.config import settings


class RagClientError(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class RagClient:
    def __init__(self) -> None:
        self._base_url = settings.rag_api_base_url.rstrip("/")
        self._timeout = settings.rag_timeout_seconds
        self._top_k = settings.rag_top_k
        self._max_context_tokens = settings.rag_max_context_tokens

    @staticmethod
    def _parse_json(response: httpx.Response) -> dict[str, Any]:
        text = response.text.strip()
        if not text:
            raise RagClientError(
                f"RAG returned an empty response ({response.status_code})",
                response.status_code,
            )
        try:
            data = response.json()
        except ValueError as exc:
            raise RagClientError(
                f"RAG returned invalid JSON ({response.status_code})",
                response.status_code,
            ) from exc
        return data if isinstance(data, dict) else {}

    async def retrieve(
        self,
        *,
        token: str,
        question: str,
        organization_id: str | None = None,
        project_id: str | None = None,
        top_k: int | None = None,
        max_context_tokens: int | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "question": question.strip(),
            "topK": top_k or self._top_k,
            "maxContextTokens": max_context_tokens or self._max_context_tokens,
        }
        if organization_id and project_id:
            body["organizationId"] = organization_id
            body["projectId"] = project_id
            path = "/retrieve/project"
        else:
            path = "/retrieve/general"

        headers = {"Authorization": f"Bearer {token}"}
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}{path}",
                    json=body,
                    headers=headers,
                )
        except httpx.RequestError as exc:
            raise RagClientError(str(exc)) from exc

        if response.status_code == 503:
            raise RagClientError("RAG is disabled", response.status_code)
        if not response.is_success:
            message = f"RAG request failed ({response.status_code})"
            try:
                data = self._parse_json(response)
                if isinstance(data.get("detail"), str):
                    message = data["detail"]
            except RagClientError:
                pass
            raise RagClientError(message, response.status_code)

        data = self._parse_json(response)
        return data if isinstance(data, dict) else {"chunks": []}


rag_client = RagClient()
