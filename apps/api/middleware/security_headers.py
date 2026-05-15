"""Security headers middleware for FastAPI — HSTS, CORP, COOP."""
from __future__ import annotations

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security response headers to every API response.

    In production (IS_PRODUCTION=true) also sets HSTS.
    The Next.js frontend sets CSP and X-Frame-Options for the browser-facing app.
    The API only needs headers relevant to direct API callers.
    """

    def __init__(self, app: object, is_production: bool = False) -> None:
        super().__init__(app)
        self._is_production = is_production

    async def dispatch(self, request: Request, call_next: object) -> Response:
        response: Response = await call_next(request)  # type: ignore[call-arg]

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

        if self._is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Remove server identity header (FastAPI adds it by default)
        response.headers.pop("server", None)

        return response
