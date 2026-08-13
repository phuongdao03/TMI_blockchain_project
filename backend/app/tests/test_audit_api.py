from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.config import Settings
from app.db.session import get_session
from app.main import create_application
from app.modules.audit.dependencies import get_audit_service
from app.modules.audit.models import AuditActorType, AuditLog
from app.modules.audit.service import AuditIntegrityStatus
from app.modules.auth.dependencies import (
    get_csrf_protected_principal,
    get_current_principal,
)
from app.modules.auth.session_service import AuthPrincipal


class _FakeSession:
    @asynccontextmanager
    async def begin(self):  # type: ignore[no-untyped-def]
        yield


class _StubAuditService:
    def __init__(self) -> None:
        now = datetime.now(UTC)
        self.row = AuditLog(
            id=uuid4(),
            actor_user_id=None,
            actor_type=AuditActorType.SERVICE,
            actor_service="blockchain-worker",
            action="blockchain.confirmed",
            resource_type="transaction",
            resource_id="tx-1",
            request_id="req-original",
            created_at=now,
            retention_until=now + timedelta(days=2_555),
        )
        self.filters: dict[str, object] = {}
        self.recorded: list[dict[str, object]] = []

    async def search(self, **filters: object) -> tuple[tuple[AuditLog, ...], int]:
        self.filters = filters
        return (self.row,), 1

    def verify_integrity(self, _row: AuditLog) -> AuditIntegrityStatus:
        return AuditIntegrityStatus.VERIFIED

    def record(self, **event: object) -> AuditLog:
        self.recorded.append(event)
        return self.row


def _principal(*roles: str) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="auditor@example.test",
        roles=roles,
        permissions=("audit.read",) if "SUPER_ADMIN" in roles else (),
    )


def test_audit_search_is_scoped_reports_integrity_and_records_the_read() -> None:
    service = _StubAuditService()
    app = create_application(
        settings=Settings(audit_integrity_key=SecretStr("x" * 32))
    )
    app.dependency_overrides[get_session] = lambda: _FakeSession()
    app.dependency_overrides[get_audit_service] = lambda: service
    app.dependency_overrides[get_current_principal] = lambda: _principal("SUPER_ADMIN")
    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/admin/audit",
                params={
                    "page": 2,
                    "pageSize": 10,
                    "resourceType": "transaction",
                    "createdFrom": "2026-08-01T00:00:00Z",
                },
            )
        assert response.status_code == 200, response.text
        data = response.json()["data"][0]
        assert data["actorType"] == "SERVICE"
        assert data["actorService"] == "blockchain-worker"
        assert data["integrityStatus"] == "VERIFIED"
        assert "integrityHash" not in data
        assert service.filters["page"] == 2
        assert service.filters["resource_type"] == "transaction"
        assert service.recorded[0]["action"] == "audit.read"
    finally:
        app.dependency_overrides.clear()


def test_audit_search_rejects_unprivileged_users_and_invalid_ranges() -> None:
    service = _StubAuditService()
    app = create_application()
    app.dependency_overrides[get_session] = lambda: _FakeSession()
    app.dependency_overrides[get_audit_service] = lambda: service
    try:
        app.dependency_overrides[get_current_principal] = lambda: _principal(
            "APPLICANT"
        )
        with TestClient(app) as client:
            forbidden = client.get("/api/v1/admin/audit")
        assert forbidden.status_code == 403
        assert service.recorded == []

        app.dependency_overrides[get_current_principal] = lambda: _principal(
            "SUPER_ADMIN"
        )
        with TestClient(app) as client:
            invalid = client.get(
                "/api/v1/admin/audit",
                params={
                    "createdFrom": "2026-08-02T00:00:00Z",
                    "createdTo": "2026-08-01T00:00:00Z",
                },
            )
        assert invalid.status_code == 422
        assert invalid.json()["error"]["code"] == "AUDIT_DATE_RANGE_INVALID"
    finally:
        app.dependency_overrides.clear()


def test_audit_export_is_bounded_safe_and_records_privileged_access() -> None:
    service = _StubAuditService()
    service.row.resource_id = "=spreadsheet-command"
    app = create_application()
    app.dependency_overrides[get_session] = lambda: _FakeSession()
    app.dependency_overrides[get_audit_service] = lambda: service
    app.dependency_overrides[get_current_principal] = lambda: _principal("SUPER_ADMIN")
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/admin/audit/exports.csv?limit=100")
        assert response.status_code == 200, response.text
        assert response.headers["cache-control"] == "no-store"
        assert "attachment; filename=" in response.headers["content-disposition"]
        assert "'=spreadsheet-command" in response.text
        assert "integrity_hash" not in response.text
        assert service.filters["page_size"] == 100
        assert service.recorded[0]["action"] == "audit.exported"
    finally:
        app.dependency_overrides.clear()


def test_audit_integrity_check_is_bounded_typed_and_audited() -> None:
    service = _StubAuditService()
    principal = _principal("SUPER_ADMIN")
    app = create_application()
    app.dependency_overrides[get_session] = lambda: _FakeSession()
    app.dependency_overrides[get_audit_service] = lambda: service
    app.dependency_overrides[get_current_principal] = lambda: principal
    app.dependency_overrides[get_csrf_protected_principal] = lambda: principal
    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/admin/audit/integrity-checks?limit=250")
        assert response.status_code == 200, response.text
        assert response.json()["data"] == {
            "isComplete": True,
            "scanned": 1,
            "total": 1,
            "counts": {
                "VERIFIED": 1,
                "TAMPERED": 0,
                "UNSEALED": 0,
                "KEY_UNAVAILABLE": 0,
            },
        }
        assert service.filters["page_size"] == 250
        assert service.recorded[0]["action"] == "audit.integrity_checked"
    finally:
        app.dependency_overrides.clear()


def test_audit_export_and_integrity_check_reject_unprivileged_users() -> None:
    service = _StubAuditService()
    principal = _principal("APPLICANT")
    app = create_application()
    app.dependency_overrides[get_session] = lambda: _FakeSession()
    app.dependency_overrides[get_audit_service] = lambda: service
    app.dependency_overrides[get_current_principal] = lambda: principal
    app.dependency_overrides[get_csrf_protected_principal] = lambda: principal
    try:
        with TestClient(app) as client:
            exported = client.get("/api/v1/admin/audit/exports.csv")
            checked = client.post("/api/v1/admin/audit/integrity-checks")
        assert exported.status_code == 403
        assert checked.status_code == 403
        assert service.recorded == []
    finally:
        app.dependency_overrides.clear()
