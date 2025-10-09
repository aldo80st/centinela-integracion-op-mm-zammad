import os

import pytest
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.anyio("asyncio")

os.environ.setdefault("OP_BASE_URL", "https://example.com/api/v3")
os.environ.setdefault("OP_TOKEN", "token")
os.environ.setdefault("API_KEY", "test-key")
os.environ.setdefault("OP_PROJECT_ID", "1")

from app.main import app  # noqa: E402  pylint: disable=wrong-import-position


async def test_health_endpoint() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
