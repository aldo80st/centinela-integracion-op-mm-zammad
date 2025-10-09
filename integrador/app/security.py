"""Security helpers for API key validation."""
from __future__ import annotations

import hmac
from typing import Annotated

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from starlette import status

from .config import get_settings


api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(header: Annotated[str | None, Security(api_key_header)]) -> None:
    """Validate the API key provided by the caller."""

    settings = get_settings()
    expected = settings.api_key
    if not expected:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="API key not configured")
    if header is None or not hmac.compare_digest(header, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key")


ApiKeyDependency = Annotated[None, Depends(verify_api_key)]

__all__ = ["verify_api_key", "ApiKeyDependency"]
