"""Slash command endpoint for Mattermost."""
from __future__ import annotations

import logging
from typing import Annotated, Iterable

from fastapi import APIRouter, Depends, HTTPException, Request
from starlette import status

from ..models import SearchResult, SlashCommandRequest, SlashCommandResponse
from ..security import ApiKeyDependency
from ..services.openproject import OpenProjectError, OpenProjectService, get_openproject_service

logger = logging.getLogger("integrador.slash")

router = APIRouter(prefix="", tags=["slash"])


@router.post("/slash/op")
async def handle_slash_command(
    request: Request,
    _: ApiKeyDependency,
    service: Annotated[OpenProjectService, Depends(get_openproject_service)],
) -> SlashCommandResponse:
    """Parse the slash command and delegate to the service."""

    payload = await _load_slash_payload(request)
    command = payload.text.strip()
    if not command:
        return SlashCommandResponse(text="Proporciona un comando. Ejemplos: 'buscar foo', 'crear Título | descripción'.")

    action, _, arguments = command.partition(" ")
    action = action.lower()

    try:
        if action == "buscar":
            results = await service.search(arguments or payload.text)
            return _render_search_results(results)
        if action == "crear":
            subject, description = _parse_create(arguments)
            work_package = await service.create(subject, description)
            return SlashCommandResponse(text=f"Work package creado: {work_package.url}")
    except OpenProjectError as exc:  # pragma: no cover - network failure
        logger.exception("OpenProject failure", extra={"endpoint": "/slash/op"})
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Error comunicando con OpenProject") from exc

    return SlashCommandResponse(text="Comando no reconocido. Usa 'buscar <texto>' o 'crear <título> | <descripción>'.")


def _render_search_results(results: Iterable[SearchResult]) -> SlashCommandResponse:
    entries = list(results)
    if not entries:
        return SlashCommandResponse(text="Sin resultados para el criterio solicitado.")
    lines = ["Resultados:"]
    for item in entries:
        status = item.status or "N/D"
        lines.append(f"- {item.subject} ({status}) -> {item.url}")
    return SlashCommandResponse(text="\n".join(lines))


def _parse_create(arguments: str) -> tuple[str, str]:
    subject, separator, description = arguments.partition("|")
    if not separator:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Formato inválido. Usa: crear <título> | <descripción>")
    subject = subject.strip()
    description = description.strip() or subject
    if not subject:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Debes proporcionar un título para el work package")
    return subject, description


async def _load_slash_payload(request: Request) -> SlashCommandRequest:
    content_type = request.headers.get("content-type", "")
    raw: dict[str, str]
    if content_type.startswith("application/json"):
        data = await request.json()
        raw = {key: str(value) for key, value in data.items()}
    else:
        body = (await request.body()).decode("utf-8")
        from urllib.parse import parse_qs

        parsed = parse_qs(body, keep_blank_values=True)
        raw = {key: values[-1] for key, values in parsed.items() if values}
    try:
        return SlashCommandRequest(**raw)
    except Exception as exc:  # pragma: no cover - validation bubble up
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payload inválido para slash command") from exc
