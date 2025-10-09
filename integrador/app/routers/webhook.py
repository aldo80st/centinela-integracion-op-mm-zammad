"""Webhook endpoint to receive events from Zammad."""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from starlette import status

from ..models import WorkPackageResult, ZammadWebhookPayload
from ..security import ApiKeyDependency
from ..services.mattermost import MattermostError, MattermostService, get_mattermost_service
from ..services.openproject import OpenProjectError, OpenProjectService, get_openproject_service

logger = logging.getLogger("integrador.webhook")

router = APIRouter(prefix="", tags=["webhook"])


@router.post("/zammad/webhook")
async def handle_zammad_webhook(
    request: Request,
    payload: ZammadWebhookPayload,
    _: ApiKeyDependency,
    openproject_service: Annotated[OpenProjectService, Depends(get_openproject_service)],
    mattermost_service: Annotated[MattermostService, Depends(get_mattermost_service)],
) -> WorkPackageResult:
    """Process an event coming from Zammad."""

    corr_id = getattr(request.state, "corr_id", "unknown")
    try:
        work_package = await openproject_service.upsert_from_zammad(payload)
    except OpenProjectError as exc:  # pragma: no cover - network failure
        logger.exception("OpenProject failure", extra={"corr_id": corr_id, "endpoint": "/zammad/webhook"})
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Error sincronizando con OpenProject") from exc

    message = f"Ticket #{payload.ticket.id} {work_package.action} en OpenProject"
    try:
        await mattermost_service.send_message(
            message,
            props={
                "props": {
                    "attachments": [
                        {
                            "title": work_package.subject,
                            "title_link": work_package.url,
                            "text": f"Estado: {work_package.status or 'N/D'}",
                            "footer": f"correlation-id: {corr_id}",
                        }
                    ]
                }
            },
        )
    except MattermostError:
        logger.exception("Mattermost failure", extra={"corr_id": corr_id, "endpoint": "/zammad/webhook"})
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Error enviando notificación a Mattermost")

    return work_package
