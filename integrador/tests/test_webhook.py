import os
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.anyio("asyncio")

os.environ.setdefault("OP_BASE_URL", "https://example.com/api/v3")
os.environ.setdefault("OP_TOKEN", "token")
os.environ.setdefault("API_KEY", "test-key")
os.environ.setdefault("OP_PROJECT_ID", "1")

from app.main import app  # noqa: E402  pylint: disable=wrong-import-position
from app.models import WorkPackageResult, ZammadWebhookPayload  # noqa: E402
from app.services.mattermost import MattermostError, MattermostService, get_mattermost_service  # noqa: E402
from app.services.openproject import OpenProjectError, OpenProjectService, get_openproject_service  # noqa: E402


class DummyOP(OpenProjectService):
    async def upsert_from_zammad(self, payload: ZammadWebhookPayload) -> WorkPackageResult:  # type: ignore[override]
        return WorkPackageResult(id=1, subject="Test", url="https://example.com/1", action="created", status="new")


class DummyMM(MattermostService):
    async def send_message(self, text: str, *, props: dict[str, Any] | None = None) -> None:  # type: ignore[override]
        return None


@pytest.fixture(autouse=True)
def override_services():
    app.dependency_overrides[get_openproject_service] = lambda: DummyOP()
    app.dependency_overrides[get_mattermost_service] = lambda: DummyMM()
    yield
    app.dependency_overrides.clear()


async def test_webhook_success() -> None:
    payload = {
        "event": "ticket.updated",
        "ticket": {"id": 99, "title": "Issue", "state": "new"},
        "article": {"id": 1, "body": "Contenido"},
    }
    headers = {"X-API-Key": "test-key"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/zammad/webhook", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == 1


async def test_webhook_invalid_payload() -> None:
    headers = {"X-API-Key": "test-key"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/zammad/webhook", json={"wrong": "data"}, headers=headers)
    assert response.status_code == 422


async def test_webhook_missing_api_key() -> None:
    payload = {"event": "ticket.updated", "ticket": {"id": 1, "title": "Issue"}}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/zammad/webhook", json=payload)
    assert response.status_code == 401


async def test_webhook_openproject_failure() -> None:
    class FailingOP(OpenProjectService):
        async def upsert_from_zammad(self, payload: ZammadWebhookPayload) -> WorkPackageResult:  # type: ignore[override]
            raise OpenProjectError("boom")

    app.dependency_overrides[get_openproject_service] = lambda: FailingOP()
    headers = {"X-API-Key": "test-key"}
    payload = {"event": "ticket.updated", "ticket": {"id": 1, "title": "Issue"}}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/zammad/webhook", json=payload, headers=headers)
    assert response.status_code == 502
    app.dependency_overrides[get_openproject_service] = lambda: DummyOP()


async def test_webhook_mattermost_failure() -> None:
    class FailingMM(MattermostService):
        async def send_message(self, text: str, *, props: dict[str, Any] | None = None) -> None:  # type: ignore[override]
            raise MattermostError("fail")

    app.dependency_overrides[get_mattermost_service] = lambda: FailingMM()
    headers = {"X-API-Key": "test-key"}
    payload = {"event": "ticket.updated", "ticket": {"id": 1, "title": "Issue"}}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/zammad/webhook", json=payload, headers=headers)
    assert response.status_code == 502
    app.dependency_overrides[get_mattermost_service] = lambda: DummyMM()
