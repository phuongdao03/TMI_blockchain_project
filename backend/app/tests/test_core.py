import json
import logging
from asyncio import run
from typing import Final
from uuid import UUID

import httpx
import pytest
from fastapi import FastAPI

from app.core.config import Settings
from app.core.health import HealthService
from app.core.logging import JsonFormatter
from app.main import create_application


class StaticProbe:
    def __init__(self, is_available: bool) -> None:
        self._is_available = is_available

    async def check(self) -> bool:
        return self._is_available

    async def close(self) -> None:
        return None


class StructuredLogRecord(logging.LogRecord):
    request_id: str
    action: str
    duration_ms: float


def build_app(
    *,
    redis_available: bool = True,
    anvil_available: bool = True,
    settings: Settings | None = None,
) -> FastAPI:
    service = HealthService(
        {
            "redis": StaticProbe(redis_available),
            "anvil": StaticProbe(anvil_available),
        }
    )
    resolved_settings = settings or Settings.model_validate({"app_env": "local"})
    return create_application(settings=resolved_settings, health_service=service)


async def send_request(
    app: FastAPI,
    path: str,
    *,
    headers: dict[str, str] | None = None,
    raise_app_exceptions: bool = True,
) -> httpx.Response:
    transport = httpx.ASGITransport(
        app=app,
        raise_app_exceptions=raise_app_exceptions,
    )
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.get(path, headers=headers)


def get(
    app: FastAPI,
    path: str,
    *,
    headers: dict[str, str] | None = None,
    raise_app_exceptions: bool = True,
) -> httpx.Response:
    return run(
        send_request(
            app,
            path,
            headers=headers,
            raise_app_exceptions=raise_app_exceptions,
        )
    )


def test_health_endpoint_returns_success_envelope() -> None:
    response = get(build_app(), "/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"] == {"service": "backend", "status": "ok"}
    assert payload["meta"]["request_id"] == response.headers["X-Request-ID"]
    UUID(response.headers["X-Request-ID"])


def test_request_id_middleware_accepts_valid_uuid() -> None:
    request_id: Final = "a89ccf4d-3575-4ff7-b624-445163e04892"

    response = get(
        build_app(),
        "/health",
        headers={"X-Request-ID": request_id},
    )

    assert response.headers["X-Request-ID"] == request_id
    assert response.json()["meta"]["request_id"] == request_id


def test_request_id_middleware_replaces_invalid_value() -> None:
    response = get(
        build_app(),
        "/health",
        headers={"X-Request-ID": "not-a-uuid"},
    )

    generated_request_id = response.headers["X-Request-ID"]
    assert generated_request_id != "not-a-uuid"
    UUID(generated_request_id)


def test_security_headers_are_present_and_hsts_is_production_only() -> None:
    local_response = get(build_app(), "/health")
    production_response = get(
        build_app(
            settings=Settings.model_validate(
                {
                    "app_env": "production",
                    "cors_allowed_origins": "https://app.tmigroup.vn",
                }
            )
        ),
        "/health",
    )

    assert local_response.headers["X-Content-Type-Options"] == "nosniff"
    assert local_response.headers["X-Frame-Options"] == "DENY"
    assert local_response.headers["Referrer-Policy"] == "no-referrer"
    assert "default-src 'none'" in local_response.headers["Content-Security-Policy"]
    assert "Strict-Transport-Security" not in local_response.headers
    assert production_response.headers["Strict-Transport-Security"].startswith(
        "max-age=31536000"
    )


def test_cors_uses_environment_allowlist_and_rejects_unknown_origin() -> None:
    app = build_app(
        settings=Settings.model_validate(
            {
                "app_env": "local",
                "cors_allowed_origins": "https://app.tmigroup.vn",
            }
        )
    )

    allowed = get(
        app,
        "/health",
        headers={"Origin": "https://app.tmigroup.vn"},
    )
    rejected = get(
        app,
        "/health",
        headers={"Origin": "https://evil.example"},
    )

    assert allowed.headers["Access-Control-Allow-Origin"] == "https://app.tmigroup.vn"
    assert "Access-Control-Allow-Origin" not in rejected.headers


def test_production_cors_rejects_wildcard_and_non_tls_origins() -> None:
    for origin in ("*", "http://app.tmigroup.vn"):
        settings = Settings.model_validate(
            {"app_env": "production", "cors_allowed_origins": origin}
        )
        with pytest.raises(ValueError):
            _ = settings.cors_origins


def test_ready_endpoint_reports_available_dependencies() -> None:
    response = get(build_app(), "/ready")

    assert response.status_code == 200
    assert response.json()["data"] == {
        "dependencies": {"anvil": "up", "redis": "up"},
        "status": "ready",
    }


def test_ready_endpoint_returns_safe_error_when_dependency_is_down() -> None:
    response = get(build_app(anvil_available=False), "/ready")

    payload = response.json()
    assert response.status_code == 503
    assert payload["success"] is False
    assert payload["error"]["code"] == "SERVICE_NOT_READY"
    assert payload["error"]["message"] == "Service dependencies are unavailable."
    assert payload["error"]["details"] == {
        "dependencies": {"anvil": "down", "redis": "up"}
    }
    assert payload["error"]["request_id"] == response.headers["X-Request-ID"]


def test_readiness_openapi_declares_standard_error_envelope() -> None:
    response = get(build_app(), "/openapi.json")

    response_schema = response.json()["paths"]["/ready"]["get"]["responses"]["503"][
        "content"
    ]["application/json"]["schema"]
    assert response_schema == {
        "$ref": "#/components/schemas/ErrorEnvelope",
    }


def test_not_found_uses_standard_error_envelope() -> None:
    response = get(build_app(), "/missing")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
    assert response.json()["error"]["details"] == {}


def test_validation_error_uses_422_envelope() -> None:
    app = build_app()

    @app.get("/validated/{item_id}")
    async def validated(item_id: int) -> dict[str, int]:
        return {"item_id": item_id}

    response = get(app, "/validated/not-an-integer")

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "VALIDATION_ERROR"
    assert payload["error"]["message"] == "Request validation failed."
    assert payload["error"]["details"]["errors"][0]["location"] == [
        "path",
        "item_id",
    ]
    assert "input" not in payload["error"]["details"]["errors"][0]


def test_unhandled_error_does_not_expose_internal_details() -> None:
    app = build_app()

    @app.get("/explode")
    async def explode() -> None:
        raise RuntimeError("secret-internal-detail")

    response = get(app, "/explode", raise_app_exceptions=False)

    assert response.status_code == 500
    body = response.text
    assert response.json()["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert "secret-internal-detail" not in body
    assert "Traceback" not in body


def test_json_formatter_emits_required_safe_fields() -> None:
    formatter = JsonFormatter(service="backend", environment="local")
    record = StructuredLogRecord(
        name="app.core",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="request_completed",
        args=(),
        exc_info=None,
    )
    request_id = "a89ccf4d-3575-4ff7-b624-445163e04892"
    record.request_id = request_id
    record.action = "GET /health"
    record.duration_ms = 4.2

    payload = json.loads(formatter.format(record))

    assert payload["level"] == "INFO"
    assert payload["service"] == "backend"
    assert payload["environment"] == "local"
    assert payload["request_id"] == request_id
    assert payload["action"] == "GET /health"
    assert payload["duration_ms"] == 4.2
    assert "timestamp" in payload
