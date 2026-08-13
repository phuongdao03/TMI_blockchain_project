import asyncio
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import Settings
from app.core.errors import DomainError
from app.core.health import HealthService
from app.db.base import Base
from app.db.outbox import OutboxEvent
from app.main import create_application
from app.modules.audit.models import AuditLog
from app.modules.audit.service import AuditService
from app.modules.auth.firebase_provider import FirebaseClaims
from app.modules.auth.models import AuthIdentity, Role, StaffInvitation, User, UserRole
from app.modules.auth.schemas import StaffAccountData, StaffInvitationRequest
from app.modules.auth.security import OutboxPayloadCipher, hash_verification_token
from app.modules.auth.session_service import AuthPrincipal
from app.modules.auth.staff_invitation_service import StaffInvitationService

NOW = datetime(2026, 8, 8, 8, tzinfo=UTC)


def test_staff_accounts_can_only_be_provisioned_through_invitations() -> None:
    app = create_application(
        settings=Settings(app_env="local"),
        health_service=HealthService({}),
    )
    paths = app.openapi()["paths"]

    assert "post" not in paths["/api/v1/admin/staff-accounts"]
    assert "post" in paths["/api/v1/admin/staff-invitations"]
    assert "post" in paths["/api/v1/auth/staff-invitations/accept"]
    assert "post" in paths["/api/v1/auth/staff-mfa/recovery/authorize"]
    assert "post" in paths[
        "/api/v1/admin/staff-accounts/{user_id}/mfa-recovery"
    ]
    assert "post" in paths[
        "/api/v1/admin/staff-accounts/{user_id}/privileged-actions"
    ]
    assert "get" in paths[
        "/api/v1/admin/staff-accounts/privileged-actions/pending"
    ]
    assert "post" in paths[
        "/api/v1/admin/staff-accounts/privileged-actions/{action_id}/approve"
    ]


def _admin() -> AuthPrincipal:
    return AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="admin@example.com",
        roles=("SUPER_ADMIN",),
    )


def test_invitation_management_accepts_normalized_permission() -> None:
    StaffInvitationService.require_super_admin(
        AuthPrincipal(
            user_id=uuid4(),
            session_id=uuid4(),
            email="operator@example.com",
            roles=("AUDITOR",),
            permissions=("admin.staff.manage",),
        )
    )


def test_invitation_is_single_use_email_bound_and_idempotently_resendable(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'staff-invite.sqlite3').as_posix()}"
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        cipher = OutboxPayloadCipher.from_base64(
            encoded_key="MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=",
            key_id="test-key",
        )
        admin = _admin()
        clock = [NOW]
        async with factory() as session:
            async with session.begin():
                session.add(User(id=admin.user_id, email=admin.email, status="ACTIVE"))
                session.add(Role(code="REVIEWER"))
            service = StaffInvitationService(
                session=session,
                payload_cipher=cipher,
                invitation_ttl=timedelta(hours=24),
                clock=lambda: clock[0],
            )
            invitation = await service.create(
                payload=StaffInvitationRequest(
                    email="Reviewer@Example.com", role="REVIEWER"
                ),
                principal=admin,
                audit=AuditService(session),
                request_id="invite-1",
                user_agent="test",
            )
            stored = await session.get(StaffInvitation, invitation.id)
            assert stored is not None
            assert stored.email == "reviewer@example.com"
            assert "LocalOnly" not in stored.token_hash
            event = await session.scalar(
                select(OutboxEvent).where(
                    OutboxEvent.aggregate_id == invitation.id
                )
            )
            assert event is not None
            payload = cipher.decrypt(
                nonce=event.payload_nonce,
                ciphertext=event.payload_ciphertext,
                event_type=event.event_type,
                aggregate_id=event.aggregate_id,
            )
            original_token = json.loads(payload)["invitation_token"]
            await session.commit()

            resent = await service.resend(
                invitation_id=invitation.id,
                principal=admin,
                audit=AuditService(session),
                request_id="resend-1",
                user_agent="test",
            )
            assert resent.status == "PENDING"
            stored = await session.get(StaffInvitation, invitation.id)
            assert stored is not None
            events = tuple(
                (
                    await session.scalars(
                        select(OutboxEvent).where(
                            OutboxEvent.aggregate_id == invitation.id
                        )
                    )
                ).all()
            )
            assert sum(item.processed_at is None for item in events) == 1
            tokens = [
                json.loads(
                    cipher.decrypt(
                        nonce=item.payload_nonce,
                        ciphertext=item.payload_ciphertext,
                        event_type=item.event_type,
                        aggregate_id=item.aggregate_id,
                    )
                )["invitation_token"]
                for item in events
            ]
            token = next(
                value
                for value in tokens
                if hash_verification_token(value) == stored.token_hash
            )
            assert token != original_token
            await session.commit()

            with pytest.raises(DomainError) as replaced:
                await service.accept(
                    raw_token=original_token,
                    claims=FirebaseClaims(
                        subject="firebase-reviewer",
                        email="reviewer@example.com",
                        email_verified=True,
                        name=None,
                        picture=None,
                    ),
                    audit=AuditService(session),
                    request_id="accept-replaced",
                    user_agent="test",
                )
            assert replaced.value.code == "STAFF_INVITATION_INVALID"

            with pytest.raises(DomainError) as mismatch:
                await service.accept(
                    raw_token=token,
                    claims=FirebaseClaims(
                        subject="firebase-wrong",
                        email="other@example.com",
                        email_verified=True,
                        name=None,
                        picture=None,
                    ),
                    audit=AuditService(session),
                    request_id="accept-wrong",
                    user_agent="test",
                )
            assert mismatch.value.code == "STAFF_INVITATION_INVALID"

            accepted = await service.accept(
                raw_token=token,
                claims=FirebaseClaims(
                    subject="firebase-reviewer",
                    email="reviewer@example.com",
                    email_verified=True,
                    name=None,
                    picture=None,
                ),
                audit=AuditService(session),
                request_id="accept-1",
                user_agent="test",
            )
            assert accepted.email == "reviewer@example.com"
            assert accepted.status == "PENDING_MFA"
            assert await session.scalar(select(func.count(User.id))) == 2
            assert await session.scalar(select(func.count(AuthIdentity.id))) == 1
            assert await session.scalar(select(func.count()).select_from(UserRole)) == 1
            await session.commit()
            with pytest.raises(DomainError) as replay:
                await service.accept(
                    raw_token=token,
                    claims=FirebaseClaims(
                        subject="firebase-reviewer",
                        email="reviewer@example.com",
                        email_verified=True,
                        name=None,
                        picture=None,
                    ),
                    audit=AuditService(session),
                    request_id="accept-replay",
                    user_agent="test",
                )
            assert replay.value.code == "STAFF_INVITATION_INVALID"
            assert await session.scalar(select(func.count(AuditLog.id))) == 3
            await session.commit()

            revoked = await service.create(
                payload=StaffInvitationRequest(
                    email="revoked@example.com", role="REVIEWER"
                ),
                principal=admin,
                audit=AuditService(session),
                request_id="invite-revoked",
                user_agent="test",
            )
            revoked_data = await service.revoke(
                invitation_id=revoked.id,
                principal=admin,
                audit=AuditService(session),
                request_id="revoke-1",
                user_agent="test",
            )
            assert revoked_data.status == "REVOKED"

            expired = await service.create(
                payload=StaffInvitationRequest(
                    email="expired@example.com", role="REVIEWER"
                ),
                principal=admin,
                audit=AuditService(session),
                request_id="invite-expired",
                user_agent="test",
            )
            expired_event = await session.scalar(
                select(OutboxEvent).where(
                    OutboxEvent.aggregate_id == expired.id
                )
            )
            assert expired_event is not None
            expired_token = json.loads(
                cipher.decrypt(
                    nonce=expired_event.payload_nonce,
                    ciphertext=expired_event.payload_ciphertext,
                    event_type=expired_event.event_type,
                    aggregate_id=expired_event.aggregate_id,
                )
            )["invitation_token"]
            await session.commit()
            clock[0] = NOW + timedelta(days=2)
            with pytest.raises(DomainError) as expired_error:
                await service.accept(
                    raw_token=expired_token,
                    claims=FirebaseClaims(
                        subject="firebase-expired",
                        email="expired@example.com",
                        email_verified=True,
                        name=None,
                        picture=None,
                    ),
                    audit=AuditService(session),
                    request_id="accept-expired",
                    user_agent="test",
                )
            assert expired_error.value.code == "STAFF_INVITATION_INVALID"
        await engine.dispose()

    asyncio.run(scenario())


@pytest.mark.skipif(
    not os.getenv("STAFF_INVITATION_POSTGRES_TEST_URL"),
    reason="Requires an isolated PostgreSQL integration database.",
)
def test_concurrent_acceptance_creates_exactly_one_staff_account() -> None:
    async def scenario() -> None:
        engine = create_async_engine(
            os.environ["STAFF_INVITATION_POSTGRES_TEST_URL"]
        )
        factory = async_sessionmaker(engine, expire_on_commit=False)
        email = f"concurrent-{uuid4().hex}@example.com"
        cipher = OutboxPayloadCipher.from_base64(
            encoded_key="MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=",
            key_id="test-key",
        )
        invitation_id = None
        user_id = None
        try:
            async with factory() as session:
                admin_user = await session.scalar(
                    select(User).where(User.email == "admin@example.com")
                )
                assert admin_user is not None
                admin = AuthPrincipal(
                    user_id=admin_user.id,
                    session_id=uuid4(),
                    email=admin_user.email,
                    roles=("SUPER_ADMIN",),
                )
                await session.commit()
                service = StaffInvitationService(
                    session=session,
                    payload_cipher=cipher,
                    invitation_ttl=timedelta(hours=24),
                )
                invitation = await service.create(
                    payload=StaffInvitationRequest(email=email, role="REVIEWER"),
                    principal=admin,
                    audit=AuditService(session),
                    request_id="concurrent-create",
                    user_agent="test",
                )
                invitation_id = invitation.id
                event = await session.scalar(
                    select(OutboxEvent).where(
                        OutboxEvent.aggregate_id == invitation.id
                    )
                )
                assert event is not None
                token = json.loads(
                    cipher.decrypt(
                        nonce=event.payload_nonce,
                        ciphertext=event.payload_ciphertext,
                        event_type=event.event_type,
                        aggregate_id=event.aggregate_id,
                    )
                )["invitation_token"]
                await session.commit()

            async def accept_once() -> StaffAccountData:
                async with factory() as session:
                    return await StaffInvitationService(
                        session=session,
                        payload_cipher=cipher,
                        invitation_ttl=timedelta(hours=24),
                    ).accept(
                        raw_token=token,
                        claims=FirebaseClaims(
                            subject="firebase-concurrent",
                            email=email,
                            email_verified=True,
                            name=None,
                            picture=None,
                        ),
                        audit=AuditService(session),
                        request_id="concurrent-accept",
                        user_agent="test",
                    )

            results = await asyncio.gather(
                accept_once(), accept_once(), return_exceptions=True
            )
            successes = [item for item in results if isinstance(item, StaffAccountData)]
            failures = [item for item in results if isinstance(item, DomainError)]
            assert len(successes) == 1
            assert len(failures) == 1
            assert failures[0].code == "STAFF_INVITATION_INVALID"
            user_id = successes[0].id
        finally:
            async with factory.begin() as session:
                if invitation_id is not None:
                    await session.execute(
                        delete(OutboxEvent).where(
                            OutboxEvent.aggregate_id == invitation_id
                        )
                    )
                    await session.execute(
                        delete(StaffInvitation).where(
                            StaffInvitation.id == invitation_id
                        )
                    )
                if user_id is not None:
                    await session.execute(delete(User).where(User.id == user_id))
            await engine.dispose()

    asyncio.run(scenario())
