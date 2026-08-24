from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.errors import DomainError
from app.db.base import Base
from app.modules.audit.models import AuditLog
from app.modules.audit.service import AuditService
from app.modules.auth.firebase_provider import FirebaseClaims
from app.modules.auth.models import (
    AuthIdentity,
    AuthProvider,
    AuthSession,
    Role,
    User,
    UserRole,
    UserStatus,
)
from app.modules.auth.security import Argon2PasswordHasher
from app.modules.auth.session_service import (
    ClientMetadata,
    SessionService,
)
from app.modules.auth.staff_account_service import StaffAccountService
from app.modules.auth.staff_mfa import StaffMfaPolicy
from app.modules.auth.tokens import AccessTokenManager, CsrfTokenManager

NOW = datetime.now(UTC).replace(microsecond=0) - timedelta(minutes=1)


def test_privileged_staff_requires_recent_totp_evidence() -> None:
    policy = StaffMfaPolicy(max_age=timedelta(hours=12))

    with pytest.raises(DomainError) as missing:
        policy.require(roles=("MODERATOR",), mfa_verified_at=None, now=NOW)
    assert missing.value.code == "STAFF_MFA_REQUIRED"

    with pytest.raises(DomainError) as stale:
        policy.require(
            roles=("MODERATOR",),
            mfa_verified_at=NOW - timedelta(hours=12),
            now=NOW,
        )
    assert stale.value.code == "STAFF_MFA_REAUTH_REQUIRED"

    policy.require(
        roles=("SUPER_ADMIN",),
        mfa_verified_at=NOW - timedelta(minutes=5),
        now=NOW,
    )


def test_mfa_is_not_required_for_applicant_sessions() -> None:
    StaffMfaPolicy(max_age=timedelta(hours=12)).require(
        roles=("USER",),
        mfa_verified_at=None,
        now=NOW,
    )


class NoopRateLimiter:
    async def check(self, *, email: str, client_ip: str) -> None:
        del email, client_ip


def test_privileged_application_session_preserves_and_expires_mfa_evidence(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        current = [NOW]
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'staff-mfa.sqlite3').as_posix()}"
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory.begin() as session:
            user = User(
                email="reviewer@example.com",
                status=UserStatus.ACTIVE,
                email_verified_at=NOW,
            )
            role = Role(code="MODERATOR")
            session.add_all((user, role))
            await session.flush()
            session.add(UserRole(user_id=user.id, role_id=role.id))
            user_id = user.id
        service = SessionService(
            session=factory(),
            password_hasher=Argon2PasswordHasher(),
            access_tokens=AccessTokenManager(
                secret="a" * 64,
                issuer="tmi-platform",
                audience="tmi-web",
                ttl=timedelta(days=1),
                clock=lambda: current[0],
            ),
            csrf_tokens=CsrfTokenManager(secret="b" * 64),
            rate_limiter=NoopRateLimiter(),
            refresh_ttl=timedelta(days=30),
            mfa_policy=StaffMfaPolicy(max_age=timedelta(hours=12)),
            clock=lambda: current[0],
        )
        metadata = ClientMetadata("127.0.0.1", "test", "browser")
        with pytest.raises(DomainError) as missing:
            await service.issue_for_user(user_id=user_id, metadata=metadata)
        assert missing.value.code == "STAFF_MFA_REQUIRED"

        issued = await service.issue_for_user(
            user_id=user_id,
            metadata=metadata,
            mfa_verified_at=NOW,
        )
        async with factory() as session:
            stored = (await session.scalars(select(AuthSession))).one()
            assert stored.mfa_verified_at is not None

        current[0] = NOW + timedelta(hours=12)
        with pytest.raises(DomainError) as stale:
            await service.authenticate_access(issued.access_token)
        assert stale.value.code == "STAFF_MFA_REAUTH_REQUIRED"

        await service.close()
        await engine.dispose()

    import asyncio

    asyncio.run(scenario())


def test_staff_mfa_recovery_suspends_then_requires_same_firebase_identity(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        database_path = (tmp_path / "staff-mfa-recovery.sqlite3").as_posix()
        engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory.begin() as session:
            admin = User(
                email="admin@example.com",
                status=UserStatus.ACTIVE,
                email_verified_at=NOW,
            )
            staff = User(
                email="reviewer@example.com",
                status=UserStatus.SUSPENDED,
                email_verified_at=NOW,
                mfa_recovery_authorized_at=NOW,
            )
            admin_role = Role(code="SUPER_ADMIN")
            staff_role = Role(code="MODERATOR")
            session.add_all((admin, staff, admin_role, staff_role))
            await session.flush()
            session.add_all(
                (
                    UserRole(user_id=admin.id, role_id=admin_role.id),
                    UserRole(user_id=staff.id, role_id=staff_role.id),
                    AuthIdentity(
                        user_id=staff.id,
                        provider=AuthProvider.FIREBASE,
                        provider_subject="firebase-staff",
                    ),
                )
            )
            staff_id = staff.id

        async with factory() as session:
            service = StaffAccountService(session)
            with pytest.raises(DomainError) as wrong_identity:
                await service.authorize_mfa_reenrollment(
                    claims=FirebaseClaims(
                        subject="different-user",
                        email="reviewer@example.com",
                        email_verified=True,
                        name=None,
                        picture=None,
                    ),
                    audit=AuditService(session),
                    request_id="request-2",
                    user_agent="test",
                )
            assert wrong_identity.value.code == "STAFF_MFA_RECOVERY_INVALID"

            await service.authorize_mfa_reenrollment(
                claims=FirebaseClaims(
                    subject="firebase-staff",
                    email="reviewer@example.com",
                    email_verified=True,
                    name=None,
                    picture=None,
                ),
                audit=AuditService(session),
                request_id="request-3",
                user_agent="test",
            )

        async with factory() as session:
            recovered = await session.get(User, staff_id)
            assert recovered is not None
            assert recovered.status is UserStatus.PENDING
            assert recovered.mfa_recovery_authorized_at is not None
            actions = set((await session.scalars(select(AuditLog.action))).all())
            assert actions == {"auth.staff_mfa_recovery.authorized"}
        await engine.dispose()

    import asyncio

    asyncio.run(scenario())
