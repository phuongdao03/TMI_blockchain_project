import logging
from collections.abc import Mapping
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class DomainError(Exception):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        status_code: int,
        details: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = dict(details or {})


class ServiceNotReadyError(DomainError):
    def __init__(self, *, details: Mapping[str, object]) -> None:
        super().__init__(
            code="SERVICE_NOT_READY",
            message="Service dependencies are unavailable.",
            status_code=503,
            details=details,
        )


def _request_id(request: Request) -> str:
    request_id: str = getattr(request.state, "request_id", "unknown")
    return request_id


def _error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: Mapping[str, object] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {
                "code": code,
                "message": message,
                "details": dict(details or {}),
                "request_id": _request_id(request),
            },
        },
    )


async def domain_error_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, DomainError):
        raise TypeError("domain_error_handler received an unsupported exception")
    return _error_response(
        request,
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details,
    )


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):
        raise TypeError("validation_error_handler received an unsupported exception")

    errors: list[dict[str, Any]] = [
        {
            "location": list(error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        }
        for error in exc.errors()
    ]
    return _error_response(
        request,
        status_code=422,
        code="VALIDATION_ERROR",
        message="Request validation failed.",
        details={"errors": errors},
    )


async def http_error_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, StarletteHTTPException):
        raise TypeError("http_error_handler received an unsupported exception")

    code_by_status = {
        401: "UNAUTHENTICATED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
    }
    code = code_by_status.get(exc.status_code, "HTTP_ERROR")
    message = str(exc.detail) if exc.status_code < 500 else "Request failed."
    return _error_response(
        request,
        status_code=exc.status_code,
        code=code,
        message=message,
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "unhandled_error",
        extra={
            "error_code": "INTERNAL_SERVER_ERROR",
            "request_id": _request_id(request),
        },
        exc_info=exc,
    )
    return _error_response(
        request,
        status_code=500,
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred.",
    )


def install_exception_handlers(app: FastAPI) -> None:
    # Source: https://fastapi.tiangolo.com/tutorial/handling-errors/#install-custom-exception-handlers
    app.add_exception_handler(DomainError, domain_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
