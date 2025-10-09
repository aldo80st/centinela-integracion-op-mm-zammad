"""Mattermost webhook client."""
from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from ..config import get_settings


class MattermostError(RuntimeError):
    """Raised when sending a notification to Mattermost fails."""


class MattermostService:
    def __init__(self) -> None:
        settings = get_settings()
        self._webhook_url = settings.mm_webhook_url
        self._timeout = httpx.Timeout(settings.request_timeout)
        self._retries = max(1, settings.request_retries)

    async def send_message(self, text: str, *, props: Optional[Dict[str, Any]] = None) -> None:
        if not self._webhook_url:
            return
        payload = {"text": text}
        if props:
            payload.update(props)
        last_exc: Exception | None = None
        for attempt in range(1, self._retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.post(self._webhook_url, json=payload)
                if response.status_code >= 400:
                    raise MattermostError(response.text)
                return
            except (httpx.RequestError, MattermostError) as exc:  # noqa: PERF203
                last_exc = exc
                if attempt == self._retries:
                    raise
        assert last_exc  # pragma: no cover
        raise last_exc


def get_mattermost_service() -> MattermostService:
    return MattermostService()


__all__ = ["MattermostError", "MattermostService", "get_mattermost_service"]
