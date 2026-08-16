import logging
from time import perf_counter
from uuid import UUID, uuid4

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app.core.logging import reset_request_id, set_request_id

logger = logging.getLogger(__name__)


class PreviewModeMiddleware(BaseHTTPMiddleware):
    """Deny unavailable state changes during the public-preview release."""

    _SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
    _ALLOWED_MUTATION_PREFIXES = (
        "/api/v1/auth/",
        "/api/v1/users/me",
    )

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        is_allowed_mutation = request.url.path.startswith(
            self._ALLOWED_MUTATION_PREFIXES
        )
        if request.method not in self._SAFE_METHODS and not is_allowed_mutation:
            request_id = getattr(request.state, "request_id", "")
            return JSONResponse(
                status_code=503,
                content={
                    "success": False,
                    "error": {
                        "code": "FEATURE_NOT_AVAILABLE",
                        "message": (
                            "Chức năng này chưa khả dụng trong phiên bản trải nghiệm."
                        ),
                        "details": {},
                        "request_id": request_id,
                    },
                },
                headers={"Retry-After": "86400", "X-Release-Mode": "preview"},
            )
        response = await call_next(request)
        response.headers["X-Release-Mode"] = "preview"
        return response


def _validated_request_id(candidate: str | None) -> str:
    if candidate is not None:
        try:
            return str(UUID(candidate))
        except ValueError:
            pass
    return str(uuid4())


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request_id = _validated_request_id(request.headers.get("X-Request-ID"))
        request.state.request_id = request_id
        token = set_request_id(request_id)
        started_at = perf_counter()

        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            route = request.scope.get("route")
            route_path = getattr(route, "path", "<unmatched>")
            logger.info(
                "request_completed",
                extra={
                    "action": f"{request.method} {route_path}",
                    "duration_ms": round((perf_counter() - started_at) * 1000, 2),
                    "request_id": request_id,
                },
            )
            return response
        finally:
            reset_request_id(token)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, *, production: bool) -> None:
        super().__init__(app)
        self._production = production

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; "
            "form-action 'none'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        if "Referrer-Policy" not in response.headers:
            response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = (
            "camera=(), geolocation=(), microphone=()"
        )
        if request.url.path.startswith("/api/v1/public/"):
            response.headers["Cache-Control"] = "no-store"
        if self._production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response
