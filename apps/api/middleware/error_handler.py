"""Standardized error envelope: { "error": { "code", "message", "details" } }

Registered via app.add_exception_handler in main.py.
All unhandled exceptions produce this shape, so API consumers never see
raw FastAPI/Pydantic error payloads.
"""
from __future__ import annotations

from typing import Any

import structlog
from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.responses import Response

logger = structlog.get_logger(__name__)


def _error_body(code: str, message: str, details: Any = None) -> dict[str, Any]:
    body: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details is not None:
        body["error"]["details"] = details
    return body


async def http_exception_handler(request: Request, exc: HTTPException) -> Response:
    code = _status_to_code(exc.status_code)
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(code, str(exc.detail)),
        headers=getattr(exc, "headers", None) or {},
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> Response:
    details = [
        {"loc": list(err["loc"]), "msg": err["msg"], "type": err["type"]}
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=_error_body("VALIDATION_ERROR", "Request validation failed", details),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> Response:
    logger.exception("Unhandled exception", path=request.url.path, exc=repr(exc))
    return JSONResponse(
        status_code=500,
        content=_error_body("INTERNAL_ERROR", "An unexpected error occurred"),
    )


def _status_to_code(status_code: int) -> str:
    return {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMIT_EXCEEDED",
        500: "INTERNAL_ERROR",
    }.get(status_code, f"HTTP_{status_code}")
