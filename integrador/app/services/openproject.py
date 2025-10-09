"""Async client for interacting with the OpenProject API."""
from __future__ import annotations

import html
import json
from typing import Any, Dict, Iterable, Optional

import httpx

from ..config import get_settings
from ..models import SearchResult, WorkPackageResult, ZammadWebhookPayload


class OpenProjectError(RuntimeError):
    """Raised when OpenProject responds with an error."""


class OpenProjectService:
    """Service wrapper responsible for OpenProject interactions."""

    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = str(settings.op_base_url).rstrip("/")
        self._token = settings.op_token
        self._project_id = settings.op_project_id
        self._timeout = httpx.Timeout(settings.request_timeout)
        self._retries = max(1, settings.request_retries)

    @property
    def headers(self) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        return headers

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> httpx.Response:
        url = f"{self._base_url}{path}"
        last_exc: Exception | None = None
        for attempt in range(1, self._retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout, headers=self.headers) as client:
                    response = await client.request(method, url, params=params, json=json_body)
                if response.status_code >= 500:
                    raise OpenProjectError(f"OpenProject upstream error: {response.status_code}")
                if response.status_code >= 400:
                    detail = response.text
                    raise OpenProjectError(f"OpenProject request failed: {detail}")
                return response
            except (httpx.RequestError, OpenProjectError) as exc:  # noqa: PERF203
                last_exc = exc
                if attempt == self._retries:
                    raise
        assert last_exc  # pragma: no cover
        raise last_exc

    async def _find_work_package(self, subject: str) -> Dict[str, Any] | None:
        filters = json.dumps([
            {"subject": {"operator": "~", "values": [subject]}},
            {"project": {"operator": "=", "values": [str(self._project_id)]}},
        ])
        response = await self._request(
            "GET",
            "/work_packages",
            params={"filters": filters, "pageSize": "10"},
        )
        data = response.json()
        elements = data.get("_embedded", {}).get("elements", [])
        for element in elements:
            if element.get("subject") == subject:
                return element
        return None

    async def upsert_from_zammad(self, payload: ZammadWebhookPayload) -> WorkPackageResult:
        ticket = payload.ticket
        subject = self._build_subject(ticket.id, ticket.title)
        description = self._render_description(payload)

        existing = await self._find_work_package(subject)
        if existing:
            work_package_id = int(existing["id"])
            body = {
                "lockVersion": existing["lockVersion"],
                "subject": subject,
                "description": {"format": "markdown", "raw": description},
            }
            await self._request("PATCH", f"/work_packages/{work_package_id}", json_body=body)
            action = "updated"
            status = existing.get("_embedded", {}).get("status", {}).get("name")
        else:
            body = {
                "subject": subject,
                "description": {"format": "markdown", "raw": description},
                "_links": {
                    "project": {"href": f"/api/v3/projects/{self._project_id}"},
                },
            }
            response = await self._request("POST", "/work_packages", json_body=body)
            data = response.json()
            work_package_id = int(data["id"])
            status = data.get("_embedded", {}).get("status", {}).get("name")
            action = "created"

        return WorkPackageResult(
            id=work_package_id,
            subject=subject,
            url=f"{self._base_url}/work_packages/{work_package_id}",
            action=action,
            status=status,
        )

    async def search(self, query: str, limit: int = 5) -> Iterable[SearchResult]:
        filters = json.dumps(
            [
                {"subject": {"operator": "~", "values": [query]}},
                {"project": {"operator": "=", "values": [str(self._project_id)]}},
            ]
        )
        response = await self._request(
            "GET",
            "/work_packages",
            params={"filters": filters, "pageSize": str(limit)},
        )
        data = response.json()
        results: list[SearchResult] = []
        for element in data.get("_embedded", {}).get("elements", []):
            results.append(
                SearchResult(
                    id=int(element["id"]),
                    subject=element.get("subject", ""),
                    status=element.get("_embedded", {}).get("status", {}).get("name"),
                    url=f"{self._base_url}/work_packages/{element['id']}",
                )
            )
        return results

    async def create(self, subject: str, description: str) -> WorkPackageResult:
        body = {
            "subject": subject,
            "description": {"format": "markdown", "raw": description},
            "_links": {"project": {"href": f"/api/v3/projects/{self._project_id}"}},
        }
        response = await self._request("POST", "/work_packages", json_body=body)
        data = response.json()
        return WorkPackageResult(
            id=int(data["id"]),
            subject=data.get("subject", subject),
            url=f"{self._base_url}/work_packages/{data['id']}",
            action="created",
            status=data.get("_embedded", {}).get("status", {}).get("name"),
        )

    @staticmethod
    def _build_subject(ticket_id: int, title: str) -> str:
        safe_title = " ".join(title.split())
        return f"[Zammad #{ticket_id}] {safe_title}"[:255]

    @staticmethod
    def _render_description(payload: ZammadWebhookPayload) -> str:
        ticket = payload.ticket
        article = payload.article
        customer = payload.customer

        body_lines = [
            f"**Ticket:** #{ticket.id}",
            f"**Estado:** {html.escape(ticket.state or 'Desconocido')}",
        ]
        if customer:
            customer_name = " ".join(filter(None, [customer.firstname, customer.lastname])) or customer.email or "Sin cliente"
            body_lines.append(f"**Cliente:** {html.escape(customer_name)}")
        if article and article.body:
            body_lines.append("\n---\n")
            body_lines.append(html.escape(article.body))
        return "\n".join(body_lines)


def get_openproject_service() -> OpenProjectService:
    return OpenProjectService()


__all__ = ["OpenProjectError", "OpenProjectService", "get_openproject_service"]
