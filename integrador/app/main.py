"""FastAPI application entrypoint for the Integrador service."""
from __future__ import annotations

import json
import logging
import os
import time
import uuid
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Callable, DefaultDict, Tuple

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY
from zoneinfo import ZoneInfo

from .config import get_settings
from .routers import slash, webhook

settings = get_settings()


class JSONLogFormatter(logging.Formatter):
    """Formatter producing JSON lines suitable for structured logging."""

    def format(self, record: logging.LogRecord) -> str:  # noqa: D401
        log: dict[str, Any] = {
            "timestamp": datetime.now(tz=ZoneInfo(settings.timezone)).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        if record.__dict__.get("corr_id"):
            log["corr_id"] = record.__dict__["corr_id"]
        if record.__dict__.get("endpoint"):
            log["endpoint"] = record.__dict__["endpoint"]
        if record.__dict__.get("duration") is not None:
            log["duration_ms"] = round(record.__dict__["duration"] * 1000, 2)
        if record.exc_info:
            log["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(log, ensure_ascii=False)


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JSONLogFormatter())
    root = logging.getLogger()
    root.setLevel(settings.log_level.upper())
    root.handlers = [handler]


REQUEST_COUNT: DefaultDict[Tuple[str, str, str], int] = defaultdict(int)
REQUEST_LATENCY_SUM: DefaultDict[str, float] = defaultdict(float)
REQUEST_LATENCY_COUNT: DefaultDict[str, int] = defaultdict(int)


class CorrelationMiddleware(BaseHTTPMiddleware):
    """Attach a correlation id to each request."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Response]) -> Response:
        corr_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        request.state.corr_id = corr_id
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start
        endpoint = request.url.path
        status_code = getattr(request.state, "status_code", None) or getattr(response, "status_code", 500)
        REQUEST_COUNT[(request.method, endpoint, str(status_code))] += 1
        REQUEST_LATENCY_SUM[endpoint] += duration
        REQUEST_LATENCY_COUNT[endpoint] += 1
        logging.getLogger("integrador").info(
            "request completed",
            extra={"corr_id": corr_id, "endpoint": endpoint, "duration": duration, "status_code": status_code},
        )
        response.headers["X-Correlation-ID"] = corr_id
        return response


@asynccontextmanager
async def lifespan(_: FastAPI):
    os.environ["TZ"] = settings.timezone
    yield


configure_logging()
app = FastAPI(title="Integrador OP/Zammad/Mattermost", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)
app.add_middleware(CorrelationMiddleware)
app.include_router(webhook.router)
app.include_router(slash.router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:  # pragma: no cover - safety net
    logging.getLogger("integrador").exception(
        "Unhandled exception",
        extra={"endpoint": request.url.path, "corr_id": getattr(request.state, "corr_id", "unknown")},
    )
    return JSONResponse(status_code=500, content={"detail": "Error interno"})


@app.middleware("http")
async def capture_status(request: Request, call_next: Callable[[Request], Response]) -> Response:
    try:
        response = await call_next(request)
    except Exception:  # pragma: no cover - ensures status for logging
        request.state.status_code = 500
        raise
    request.state.status_code = response.status_code
    return response


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}


@app.get("/metrics", response_class=PlainTextResponse, tags=["meta"])
async def metrics() -> PlainTextResponse:
    lines = [
        "# HELP integrador_requests_total Total HTTP requests",
        "# TYPE integrador_requests_total counter",
    ]
    for (method, endpoint, status), value in REQUEST_COUNT.items():
        lines.append(
            f'integrador_requests_total{{method="{method}",endpoint="{endpoint}",status="{status}"}} {value}'
        )

    lines.extend(
        [
            "# HELP integrador_request_latency_seconds Average HTTP request latency",
            "# TYPE integrador_request_latency_seconds gauge",
        ]
    )
    for endpoint, total in REQUEST_LATENCY_SUM.items():
        count = REQUEST_LATENCY_COUNT.get(endpoint, 0)
        average = total / count if count else 0.0
        lines.append(f'integrador_request_latency_seconds{{endpoint="{endpoint}"}} {average}')

    body = "\n".join(lines) + "\n"
    return PlainTextResponse(content=body, media_type="text/plain; version=0.0.4")
