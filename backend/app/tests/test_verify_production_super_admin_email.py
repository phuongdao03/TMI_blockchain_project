import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast

import pytest
from sqlalchemy import Table, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings
from app.db.base import Base
from app.modules.audit.service import AuditService
from app.modules.auth.models import (
    AuthIdentity,
    AuthProvider,
    AuthSession,
    Role,
    User,
    UserRole,
    UserStatus,
)
from app.scripts.bootstrap_production_super_admin import ProductionFirebaseIdentity
from app.scripts.verify_production_super_admin_email import (
    VERIFICATION_CONFIRMATION,
    require_production_verification_confirmation,
    verify_production_super_admin_email,
)


async def _factory() -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    tables = cast(
        list[Table],
        [
            User.__table__,
            Role.__table__,
            AuthIdentity.__table__,
            AuthSession.__table__,
            UserRole.__table__,
        ],
    )
    async with engine.begin() as connection:
        await connection.run_sync(lambda sync: Base.metadata.create_all(sync, tables))
    return engine, async_sessionmaker(engine, expire_on_commit=False)


class _AuditRecorder:
    def __init__(self) -> None:
        self.records: list[dict[str, object]] = []

    def record(self, **kwargs: object) -> None:
        self.records.append(kwargs)


class _FirebaseEmailVerifier:
    def __init__(
        self,
        *,
        changed: bool = True,
        revoke_error: Exception | None = None,
    ) -> None:
        self.changed = changed
        self.revoke_error = revoke_error
        self.verify_calls: list[tuple[str, str]] = []
        self.revoked_uids: list[str] = []

    async def verify_email_for_identity(self, uid: str, *, expected_email: str) -> bool:
        self.verify_calls.append((uid, expected_email))
        return self.changed

    async def revoke_refresh_tokens(self, uid: str) -> None:
        self.revoked_uids.append(uid)
        if self.revoke_error is not None:
            raise self.revoke_error


def _audit_operation_id(record: dict[str, object]) -> str:
    after = cast(dict[str, object], record["after"])
    operation_id = after["operation_id"]
    assert isinstance(operation_id, str)
    return operation_id


def test_verification_requires_production_and_exact_confirmation() -> None:
    production_settings = cast(Settings, SimpleNamespace(app_env="production"))
    local_settings = cast(Settings, SimpleNamespace(app_env="local"))

    with pytest.raises(RuntimeError, match="APP_ENV=production"):
        require_production_verification_confirmation(
            local_settings,
            VERIFICATION_CONFIRMATION,
        )
    with pytest.raises(RuntimeError, match="confirmation is invalid"):
        require_production_verification_confirmation(production_settings, "incorrect")

    require_production_verification_confirmation(
        production_settings,
        VERIFICATION_CONFIRMATION,
    )


def test_verification_updates_bound_super_admin_and_revokes_sessions() -> None:
    async def scenario() -> None:
        engine, factory = await _factory()
        try:
            async with factory() as session:
                target = User(
                    email="super.admin@example.test",
                    status=UserStatus.ACTIVE,
                )
                super_admin = Role(code="SUPER_ADMIN")
                session.add_all([target, super_admin])
                await session.flush()
                session.add_all(
                    [
                        AuthIdentity(
                            user_id=target.id,
                            provider=AuthProvider.FIREBASE,
                            provider_subject="firebase-test-super-admin",
                        ),
                        UserRole(user_id=target.id, role_id=super_admin.id),
                        AuthSession(
                            user_id=target.id,
                            refresh_token_hash="r" * 64,
                            expires_at=datetime.now(UTC),
                        ),
                    ]
                )
                await session.commit()

                firebase = _FirebaseEmailVerifier()
                audit = _AuditRecorder()
                result = await verify_production_super_admin_email(
                    session,
                    ProductionFirebaseIdentity(
                        email="super.admin@example.test",
                        provider_subject="firebase-test-super-admin",
                    ),
                    firebase_admin=firebase,
                    audit=cast(AuditService, audit),
                )

                assert result.user_id == target.id
                assert result.email_verified_changed is True
                assert firebase.verify_calls == [
                    ("firebase-test-super-admin", "super.admin@example.test")
                ]
                assert firebase.revoked_uids == ["firebase-test-super-admin"]

                await session.refresh(target)
                assert target.email_verified_at is not None
                assert (
                    await session.scalar(
                        select(AuthSession.revoked_at).where(
                            AuthSession.user_id == target.id
                        )
                    )
                    is not None
                )
                assert [record["action"] for record in audit.records] == [
                    "production.firebase_identity.email_verification_requested",
                    "production.firebase_identity.email_verification_completed",
                ]
                assert _audit_operation_id(audit.records[0]) == _audit_operation_id(
                    audit.records[1]
                )
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_retry_reconciles_a_firebase_verified_identity_after_partial_failure() -> None:
    async def scenario() -> None:
        engine, factory = await _factory()
        try:
            async with factory() as session:
                target = User(
                    email="super.admin@example.test",
                    status=UserStatus.ACTIVE,
                )
                super_admin = Role(code="SUPER_ADMIN")
                session.add_all([target, super_admin])
                await session.flush()
                session.add_all(
                    [
                        AuthIdentity(
                            user_id=target.id,
                            provider=AuthProvider.FIREBASE,
                            provider_subject="firebase-test-super-admin",
                        ),
                        UserRole(user_id=target.id, role_id=super_admin.id),
                        AuthSession(
                            user_id=target.id,
                            refresh_token_hash="s" * 64,
                            expires_at=datetime.now(UTC),
                        ),
                    ]
                )
                await session.commit()

                firebase = _FirebaseEmailVerifier(changed=False)
                audit = _AuditRecorder()
                result = await verify_production_super_admin_email(
                    session,
                    ProductionFirebaseIdentity(
                        email="super.admin@example.test",
                        provider_subject="firebase-test-super-admin",
                    ),
                    firebase_admin=firebase,
                    audit=cast(AuditService, audit),
                )

                assert result.email_verified_changed is False
                assert firebase.revoked_uids == ["firebase-test-super-admin"]
                await session.refresh(target)
                assert target.email_verified_at is not None
                assert (
                    await session.scalar(
                        select(AuthSession.revoked_at).where(
                            AuthSession.user_id == target.id
                        )
                    )
                    is not None
                )
                assert audit.records[1]["before"] == {
                    "firebase_verification": True,
                    "application_verification": False,
                }
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_revocation_failure_keeps_a_requested_audit_record_for_retry() -> None:
    async def scenario() -> None:
        engine, factory = await _factory()
        try:
            async with factory() as session:
                target = User(
                    email="super.admin@example.test",
                    status=UserStatus.ACTIVE,
                )
                super_admin = Role(code="SUPER_ADMIN")
                session.add_all([target, super_admin])
                await session.flush()
                session.add_all(
                    [
                        AuthIdentity(
                            user_id=target.id,
                            provider=AuthProvider.FIREBASE,
                            provider_subject="firebase-test-super-admin",
                        ),
                        UserRole(user_id=target.id, role_id=super_admin.id),
                        AuthSession(
                            user_id=target.id,
                            refresh_token_hash="t" * 64,
                            expires_at=datetime.now(UTC),
                        ),
                    ]
                )
                await session.commit()

                audit = _AuditRecorder()
                with pytest.raises(RuntimeError, match="Firebase revocation failed"):
                    await verify_production_super_admin_email(
                        session,
                        ProductionFirebaseIdentity(
                            email="super.admin@example.test",
                            provider_subject="firebase-test-super-admin",
                        ),
                        firebase_admin=_FirebaseEmailVerifier(
                            revoke_error=RuntimeError("Firebase revocation failed")
                        ),
                        audit=cast(AuditService, audit),
                    )

                assert [record["action"] for record in audit.records] == [
                    "production.firebase_identity.email_verification_requested",
                    "production.firebase_identity.email_verification_reconciliation_needed",
                ]
                assert (
                    await session.scalar(
                        select(AuthSession.revoked_at).where(
                            AuthSession.user_id == target.id
                        )
                    )
                    is None
                )
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_verification_refuses_a_firebase_uid_not_bound_to_the_super_admin() -> None:
    async def scenario() -> None:
        engine, factory = await _factory()
        try:
            async with factory() as session:
                target = User(
                    email="super.admin@example.test",
                    status=UserStatus.ACTIVE,
                )
                super_admin = Role(code="SUPER_ADMIN")
                session.add_all([target, super_admin])
                await session.flush()
                session.add_all(
                    [
                        AuthIdentity(
                            user_id=target.id,
                            provider=AuthProvider.FIREBASE,
                            provider_subject="another-firebase-uid",
                        ),
                        UserRole(user_id=target.id, role_id=super_admin.id),
                    ]
                )
                await session.commit()

                firebase = _FirebaseEmailVerifier()
                with pytest.raises(RuntimeError, match="does not match"):
                    await verify_production_super_admin_email(
                        session,
                        ProductionFirebaseIdentity(
                            email="super.admin@example.test",
                            provider_subject="firebase-test-super-admin",
                        ),
                        firebase_admin=firebase,
                    )

                assert firebase.verify_calls == []
                assert firebase.revoked_uids == []
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_verification_refuses_a_non_super_admin_before_calling_firebase() -> None:
    async def scenario() -> None:
        engine, factory = await _factory()
        try:
            async with factory() as session:
                target = User(
                    email="super.admin@example.test",
                    status=UserStatus.ACTIVE,
                )
                session.add(target)
                await session.flush()
                session.add(
                    AuthIdentity(
                        user_id=target.id,
                        provider=AuthProvider.FIREBASE,
                        provider_subject="firebase-test-super-admin",
                    )
                )
                await session.commit()

                firebase = _FirebaseEmailVerifier()
                with pytest.raises(RuntimeError, match="SUPER_ADMIN"):
                    await verify_production_super_admin_email(
                        session,
                        ProductionFirebaseIdentity(
                            email="super.admin@example.test",
                            provider_subject="firebase-test-super-admin",
                        ),
                        firebase_admin=firebase,
                    )

                assert firebase.verify_calls == []
        finally:
            await engine.dispose()

    asyncio.run(scenario())
