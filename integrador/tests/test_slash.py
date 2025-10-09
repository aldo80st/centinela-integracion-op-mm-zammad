import os
from typing import Iterable

import pytest
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.anyio("asyncio")

os.environ.setdefault("OP_BASE_URL", "https://example.com/api/v3")
os.environ.setdefault("OP_TOKEN", "token")
os.environ.setdefault("API_KEY", "test-key")
os.environ.setdefault("OP_PROJECT_ID", "1")

from app.main import app  # noqa: E402  pylint: disable=wrong-import-position
from app.models import SearchResult, WorkPackageResult  # noqa: E402
from app.services.openproject import OpenProjectService, get_openproject_service  # noqa: E402


class SlashOP(OpenProjectService):
    async def search(self, query: str, limit: int = 5) -> Iterable[SearchResult]:  # type: ignore[override]
        return [SearchResult(id=1, subject=f"{query} result", status="open", url="https://example.com/1")]

    async def create(self, subject: str, description: str) -> WorkPackageResult:  # type: ignore[override]
        return WorkPackageResult(id=2, subject=subject, url="https://example.com/2", action="created", status="new")


@pytest.fixture(autouse=True)
def override_service():
    app.dependency_overrides[get_openproject_service] = lambda: SlashOP()
    yield
    app.dependency_overrides.clear()


async def test_slash_search_command() -> None:
    headers = {"X-API-Key": "test-key"}
    payload = {
        "token": "t",
        "team_id": "team",
        "channel_id": "chan",
        "channel_name": "general",
        "user_id": "user",
        "user_name": "user",
        "command": "/op",
        "text": "buscar pruebas",
    }
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/slash/op", data=payload, headers=headers)
    assert response.status_code == 200
    assert "Resultados" in response.json()["text"]


async def test_slash_create_command() -> None:
    headers = {"X-API-Key": "test-key"}
    payload = {
        "token": "t",
        "team_id": "team",
        "channel_id": "chan",
        "channel_name": "general",
        "user_id": "user",
        "user_name": "user",
        "command": "/op",
        "text": "crear Incidencia | descripción",
    }
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/slash/op", data=payload, headers=headers)
    assert response.status_code == 200
    assert "Work package creado" in response.json()["text"]


async def test_slash_missing_key() -> None:
    payload = {
        "token": "t",
        "team_id": "team",
        "channel_id": "chan",
        "channel_name": "general",
        "user_id": "user",
        "user_name": "user",
        "command": "/op",
        "text": "buscar",
    }
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/slash/op", data=payload)
    assert response.status_code == 401
