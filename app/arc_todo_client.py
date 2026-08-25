from __future__ import annotations

import json
from typing import Any

import httpx

from app.caller_auth import get_caller_token
from app.config import settings


class ArcTodoApiError(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ArcTodoClient:
    def __init__(self) -> None:
        self._base_url = settings.arc_todo_api_base_url.rstrip("/")
        self._token = settings.arc_todo_access_token
        self._username = settings.arc_todo_username
        self._password = settings.arc_todo_password

    async def get_service_bearer_token(self) -> str:
        """Service-account token for startup / no-user-context calls only."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            await self._ensure_service_token(client)
            if not self._token:
                raise ArcTodoApiError("No service bearer token available")
            return self._token

    async def _ensure_service_token(self, client: httpx.AsyncClient) -> None:
        if self._token:
            return
        if not self._username or not self._password:
            raise ArcTodoApiError(
                "Missing credentials: set ARC_TODO_ACCESS_TOKEN or "
                "ARC_TODO_USERNAME and ARC_TODO_PASSWORD"
            )
        response = await client.post(
            f"{self._base_url}/auth/login",
            json={"username": self._username, "password": self._password},
        )
        if not response.is_success:
            await self._raise_api_error(response)
        data = response.json()
        self._token = data["access_token"]

    def _auth_headers(self, *, allow_service_account: bool = False) -> dict[str, str]:
        caller = get_caller_token()
        if caller:
            return {"Authorization": f"Bearer {caller}"}
        if allow_service_account and self._token:
            return {"Authorization": f"Bearer {self._token}"}
        raise ArcTodoApiError(
            "Missing Authorization bearer token. "
            "Set headers.Authorization to Bearer <your Arc Todo JWT> in mcp.json.",
            401,
        )

    async def _raise_api_error(self, response: httpx.Response) -> None:
        message = f"Request failed ({response.status_code})"
        try:
            data = response.json()
            if isinstance(data.get("message"), list):
                message = ", ".join(data["message"])
            elif isinstance(data.get("message"), str):
                message = data["message"]
        except Exception:
            pass
        raise ArcTodoApiError(message, response.status_code)

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        auth: bool = True,
    ) -> Any:
        async with httpx.AsyncClient(timeout=60.0) as client:
            headers = None
            if auth:
                headers = self._auth_headers(allow_service_account=False)
            response = await client.request(
                method,
                f"{self._base_url}{path}",
                params=params,
                json=json_body,
                headers=headers,
            )
            if not response.is_success:
                await self._raise_api_error(response)
            if response.status_code == 204:
                return None
            if not response.content:
                return None
            return response.json()

    async def request_public(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> Any:
        return await self.request(method, path, params=params, auth=False)

    async def upload_multipart(
        self,
        path: str,
        *,
        file_field: str,
        filename: str,
        content: bytes,
        mime_type: str,
        form_fields: dict[str, str] | None = None,
    ) -> Any:
        async with httpx.AsyncClient(timeout=120.0) as client:
            files = {file_field: (filename, content, mime_type)}
            data = form_fields or {}
            response = await client.post(
                f"{self._base_url}{path}",
                headers=self._auth_headers(allow_service_account=False),
                files=files,
                data=data,
            )
            if not response.is_success:
                await self._raise_api_error(response)
            return response.json()

    async def download(self, path: str) -> tuple[bytes, str, str]:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(
                f"{self._base_url}{path}",
                headers=self._auth_headers(allow_service_account=False),
            )
            if not response.is_success:
                await self._raise_api_error(response)
            content_type = response.headers.get("content-type", "application/octet-stream")
            filename = "download"
            disposition = response.headers.get("content-disposition")
            if disposition:
                if "filename*=" in disposition:
                    part = disposition.split("filename*=UTF-8''", 1)[-1]
                    filename = httpx.URL(part).raw_path.decode() if part else filename
                elif 'filename="' in disposition:
                    filename = disposition.split('filename="', 1)[-1].split('"', 1)[0]
            return response.content, content_type, filename

    @staticmethod
    def format_result(data: Any) -> str:
        return json.dumps(data, separators=(",", ":"), default=str)


arc_todo_client = ArcTodoClient()
