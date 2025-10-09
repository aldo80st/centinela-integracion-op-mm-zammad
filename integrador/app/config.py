"""Application configuration utilities.

The service reads configuration exclusively from environment variables. Each
variable supports the `_FILE` convention so that Docker/Kubernetes secrets can
be mounted as files without changing the code.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import List

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, field_validator


class Settings(BaseModel):
    """Runtime configuration loaded from the environment."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    op_base_url: AnyHttpUrl = AnyHttpUrl("https://openproject.example/api/v3")
    op_token: str = ""
    op_project_id: int = 1
    mm_webhook_url: AnyHttpUrl | None = None
    api_key: str = "change-me"
    allowed_origins: List[str] = ["http://localhost", "https://localhost"]
    request_timeout: float = 10.0
    request_retries: int = 3
    log_level: str = "INFO"
    timezone: str = "America/Mexico_City"
    environment: str = "development"

    @field_validator("op_token", "api_key", mode="before")
    @classmethod
    def ensure_not_empty(cls, value: str) -> str:
        if value is None:
            return ""
        return value.strip()

    @field_validator("op_project_id", mode="before")
    @classmethod
    def parse_int(cls, value: int | str) -> int:
        if isinstance(value, int):
            return value
        if value is None or value == "":
            return 1
        return int(value)

    @field_validator("request_timeout", mode="before")
    @classmethod
    def parse_float(cls, value: float | str) -> float:
        if isinstance(value, (float, int)):
            return float(value)
        if value in (None, ""):
            return 10.0
        return float(value)

    @field_validator("request_retries", mode="before")
    @classmethod
    def parse_retries(cls, value: int | str) -> int:
        if isinstance(value, int):
            return value
        if value in (None, ""):
            return 3
        return int(value)

    @field_validator("mm_webhook_url", mode="before")
    @classmethod
    def empty_to_none(cls, value: str | None) -> str | None:
        if value in (None, "", "none", "None"):
            return None
        return value

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: List[str] | str) -> List[str]:
        if isinstance(value, list):
            return [origin.strip() for origin in value if origin and origin.strip()]
        if value is None:
            return ["http://localhost", "https://localhost"]
        return [origin.strip() for origin in value.split(",") if origin.strip()]


def read_env(name: str, default: str | None = None) -> str | None:
    """Read an environment variable honouring the `<NAME>_FILE` convention."""

    file_key = f"{name}_FILE"
    if file_key in os.environ:
        path = os.environ[file_key]
        if path:
            with open(path, "r", encoding="utf-8") as handle:
                return handle.read().strip()
    if name in os.environ:
        return os.environ[name]
    return default


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""

    raw = {
        "op_base_url": read_env("OP_BASE_URL", "https://openproject.example/api/v3"),
        "op_token": read_env("OP_TOKEN", ""),
        "op_project_id": read_env("OP_PROJECT_ID", "1"),
        "mm_webhook_url": read_env("MM_WEBHOOK_URL"),
        "api_key": read_env("API_KEY", "change-me"),
        "allowed_origins": read_env("ALLOWED_ORIGINS", "http://localhost,https://localhost"),
        "request_timeout": read_env("REQUEST_TIMEOUT", "10"),
        "request_retries": read_env("REQUEST_RETRIES", "3"),
        "log_level": read_env("LOG_LEVEL", "INFO"),
        "timezone": read_env("TZ", "America/Mexico_City"),
        "environment": read_env("ENVIRONMENT", "development"),
    }
    # Remove keys explicitly set to None so defaults apply.
    filtered = {key: value for key, value in raw.items() if value is not None}
    return Settings(**filtered)


__all__ = ["Settings", "get_settings"]
