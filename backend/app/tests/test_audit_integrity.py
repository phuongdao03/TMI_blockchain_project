from datetime import UTC, datetime
from typing import cast
from uuid import uuid4

import pytest
from pydantic import SecretStr, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.logging import reset_request_id, set_request_id
from app.modules.audit.models import AuditActorType
from app.modules.audit.service import (
    AuditIntegrityStatus,
    AuditService,
    redact,
)


class _RepositorySession:
    def __init__(self) -> None:
        self.rows: list[object] = []

    def add(self, row: object) -> None:
        self.rows.append(row)


def _settings() -> Settings:
    return Settings(
        audit_integrity_key=SecretStr("audit-integrity-test-key-32-bytes"),
        audit_integrity_key_id="test-v1",
        audit_retention_days=2_555,
    )


def test_recursive_redaction_handles_normalized_sensitive_key_variants() -> None:
    payload = {
        "accessToken": "token-value",
        "api_key": "key-value",
        "nested": [{"refresh-token": "refresh-value"}],
        "profile": {"displayName": "Nguyen Van A", "emailAddress": "a@b.vn"},
    }

    assert redact(payload) == {
        "accessToken": "[REDACTED]",
        "api_key": "[REDACTED]",
        "nested": [{"refresh-token": "[REDACTED]"}],
        "profile": {
            "displayName": "Nguyen Van A",
            "emailAddress": "[REDACTED]",
        },
    }


def test_audit_record_is_sealed_and_detects_tampering() -> None:
    session = _RepositorySession()
    service = AuditService(cast(AsyncSession, session), settings=_settings())
    actor_id = uuid4()

    row = service.record(
        actor_user_id=actor_id,
        action="dossier.approved",
        resource_type="dossier",
        resource_id="DOS-001",
        after={"status": "APPROVED", "password": "never-store-this"},
        request_id="req-audit-1",
    )

    assert row.actor_type is AuditActorType.USER
    assert row.integrity_key_id == "test-v1"
    assert row.integrity_hash is not None and len(row.integrity_hash) == 64
    assert row.retention_until is not None
    assert service.verify_integrity(row) is AuditIntegrityStatus.VERIFIED
    assert row.after_json == {"status": "APPROVED", "password": "[REDACTED]"}

    row.after_json = {"status": "REJECTED"}
    assert service.verify_integrity(row) is AuditIntegrityStatus.TAMPERED


def test_historical_integrity_key_verifies_rows_after_rotation() -> None:
    session = _RepositorySession()
    old_service = AuditService(cast(AsyncSession, session), settings=_settings())
    row = old_service.record(
        actor_user_id=None,
        action="audit.rotation.tested",
        resource_type="audit_log",
        resource_id="row-1",
    )
    rotated_settings = Settings(
        audit_integrity_key=SecretStr("new-audit-integrity-key-32-bytes!!"),
        audit_integrity_key_id="test-v2",
        audit_integrity_verification_keys={
            "test-v1": SecretStr("audit-integrity-test-key-32-bytes")
        },
    )
    rotated_service = AuditService(
        cast(AsyncSession, _RepositorySession()), settings=rotated_settings
    )

    assert rotated_service.verify_integrity(row) is AuditIntegrityStatus.VERIFIED

    row.after_json = {"status": "tampered"}
    assert rotated_service.verify_integrity(row) is AuditIntegrityStatus.TAMPERED


def test_integrity_keyring_rejects_unsafe_or_ambiguous_configuration() -> None:
    with pytest.raises(ValidationError, match="verification key must contain"):
        Settings(audit_integrity_verification_keys={"audit-v0": SecretStr("too-short")})

    with pytest.raises(ValidationError, match="different key material"):
        Settings(
            audit_integrity_key=SecretStr("active-audit-integrity-key-32-bytes"),
            audit_integrity_key_id="audit-v1",
            audit_integrity_verification_keys={
                "audit-v1": SecretStr("different-audit-integrity-key-32-bytes")
            },
        )


def test_service_actor_and_legacy_unsealed_status_are_explicit() -> None:
    session = _RepositorySession()
    service = AuditService(cast(AsyncSession, session), settings=_settings())
    row = service.record(
        actor_user_id=None,
        actor_service="blockchain-worker",
        action="blockchain.confirmed",
        resource_type="transaction",
        resource_id="tx-1",
    )
    assert row.actor_type is AuditActorType.SERVICE
    assert service.verify_integrity(row) is AuditIntegrityStatus.VERIFIED

    row.integrity_hash = None
    row.integrity_key_id = None
    assert service.verify_integrity(row) is AuditIntegrityStatus.UNSEALED


def test_actor_identity_is_unambiguous() -> None:
    service = AuditService(
        cast(AsyncSession, _RepositorySession()), settings=_settings()
    )
    with pytest.raises(ValueError, match="both a user and a service"):
        service.record(
            actor_user_id=uuid4(),
            actor_service="worker",
            action="test.invalid",
            resource_type="test",
            resource_id="1",
        )


def test_integrity_payload_uses_stable_utc_timestamp() -> None:
    session = _RepositorySession()
    service = AuditService(cast(AsyncSession, session), settings=_settings())
    row = service.record(
        actor_user_id=None,
        action="auth.login.failed",
        resource_type="authentication",
        resource_id="anonymous",
    )
    assert isinstance(row.created_at, datetime)
    assert row.created_at.tzinfo is UTC
    row.created_at = row.created_at.replace(tzinfo=None)
    assert row.retention_until is not None
    row.retention_until = row.retention_until.replace(tzinfo=None)
    assert service.verify_integrity(row) is AuditIntegrityStatus.VERIFIED


def test_untrusted_user_agent_is_bounded_before_storage() -> None:
    service = AuditService(
        cast(AsyncSession, _RepositorySession()), settings=_settings()
    )
    row = service.record(
        actor_user_id=None,
        action="auth.login.failed",
        resource_type="authentication",
        resource_id="anonymous",
        user_agent="x" * 10_000,
    )
    assert row.user_agent == "x" * 512
    assert service.verify_integrity(row) is AuditIntegrityStatus.VERIFIED


def test_audit_record_inherits_valid_request_context_unless_explicit() -> None:
    service = AuditService(
        cast(AsyncSession, _RepositorySession()), settings=_settings()
    )
    token = set_request_id("a89ccf4d-3575-4ff7-b624-445163e04892")
    try:
        inherited = service.record(
            actor_user_id=None,
            action="test.inherited_request",
            resource_type="test",
            resource_id="1",
        )
        explicit = service.record(
            actor_user_id=None,
            action="test.explicit_request",
            resource_type="test",
            resource_id="2",
            request_id="worker-job-1",
        )
    finally:
        reset_request_id(token)

    assert inherited.request_id == "a89ccf4d-3575-4ff7-b624-445163e04892"
    assert explicit.request_id == "worker-job-1"
