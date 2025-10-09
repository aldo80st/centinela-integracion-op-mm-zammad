"""Pydantic models shared across routers and services."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    """Base model forbidding unknown fields."""

    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class ZammadUser(StrictModel):
    id: Optional[int] = None
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    email: Optional[str] = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if "@" not in value:
            raise ValueError("correo inválido")
        return value


class ZammadArticle(StrictModel):
    id: Optional[int] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    content_type: Optional[str] = Field(default=None, alias="contentType")


class ZammadTicket(StrictModel):
    id: int
    title: str
    group: Optional[str] = None
    state: Optional[str] = None
    priority: Optional[str] = None
    created_at: Optional[datetime] = Field(default=None, alias="createdAt")
    updated_at: Optional[datetime] = Field(default=None, alias="updatedAt")


class ZammadWebhookPayload(StrictModel):
    event: str
    ticket: ZammadTicket
    article: Optional[ZammadArticle] = None
    customer: Optional[ZammadUser] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SlashCommandRequest(StrictModel):
    token: str
    team_id: str = Field(alias="team_id")
    channel_id: str = Field(alias="channel_id")
    channel_name: str = Field(alias="channel_name")
    user_id: str = Field(alias="user_id")
    user_name: str = Field(alias="user_name")
    command: str
    text: str
    trigger_id: Optional[str] = Field(default=None, alias="trigger_id")


class SlashCommandResponse(BaseModel):
    response_type: str = "ephemeral"
    text: str
    attachments: Optional[List[Dict[str, Any]]] = None


class WorkPackageResult(StrictModel):
    id: int
    subject: str
    url: str
    action: str
    status: Optional[str] = None


class SearchResult(StrictModel):
    id: int
    subject: str
    status: Optional[str] = None
    url: Optional[str] = None
