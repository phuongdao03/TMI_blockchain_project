import asyncio
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.errors import DomainError
from app.db.base import Base
from app.modules.audit.models import AuditLog
from app.modules.auth.firebase_provider import FirebaseClaims
from app.modules.auth.models import (
    AccountType,
    AuthIdentity,
    AuthProvider,
    Role,
    User,
    UserRole,
    UserStatus,
)
from app.modules.auth.oauth import OAuthAttempt
from app.modules.auth.oauth_service import OAuthCompletion, OAuthService
from app.modules.auth.session_service import ClientMetadata, IssuedSession

NOW = datetime(2026, 8, 4, 8, tzinfo=UTC)


class FakeIssuer:
    def __init__(self) -> None:
        self.user_id: UUID | None = None

    async def issue_for_user(
        self,
        *,
        user_id: UUID,
        metadata: ClientMetadata,
        mfa_verified_at: datetime | None = None,
    ) -> IssuedSession:
        del metadata, mfa_verified_at
        self.user_id = user_id
        return IssuedSession("access", "refresh", "csrf")


def _claims(
    email: str = "viewer@gmail.com",
    subject: str = "google-subject",
) -> FirebaseClaims:
    return FirebaseClaims(
        subject=subject,
        email=email,
        email_verified=True,
        name="Viewer",
        picture=None,
    )


def _attempt(
    account_type: AccountType = AccountType.PUBLIC_USER,
    *,
    purpose: str = "login",
    user_id: str | None = None,
) -> OAuthAttempt:
    return OAuthAttempt(
        state="state",
        nonce="nonce",
        account_type=account_type.value,
        next_path="/dashboard",
        purpose=purpose,
        user_id=user_id,
    )


def test_oauth_signup_collision_and_existing_identity_are_safe(tmp_path: Path) -> None:
    async def scenario() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'oauth-service.sqlite3').as_posix()}"
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        issuer = FakeIssuer()
        metadata = ClientMetadata("127.0.0.1", "test", "Firebase")
        async with factory() as session:
            service = OAuthService(
                session=session,
                session_issuer=issuer,
                clock=lambda: NOW,
            )
            result = await service.complete(
                claims=_claims(),
                attempt=_attempt(AccountType.INDIVIDUAL_APPLICANT),
                metadata=metadata,
            )
            assert isinstance(result, OAuthCompletion)
            user = await session.get(User, result.user_id)
            assert user is not None and user.status is UserStatus.ACTIVE
            assert user.password_hash is None
            assert user.email_verified_at is not None
            assert issuer.user_id == user.id
            role = await session.scalar(select(Role).where(Role.code == "APPLICANT"))
            assert role is not None

            await session.rollback()
            async with session.begin():
                session.add(
                    User(
                        email="collision@example.test",
                        password_hash="password-hash",
                        status=UserStatus.ACTIVE,
                        email_verified_at=NOW,
                    )
                )
            with pytest.raises(DomainError) as collision:
                await service.complete(
                    claims=_claims(email="collision@example.test", subject="other"),
                    attempt=_attempt(),
                    metadata=metadata,
                )
            assert collision.value.code == "OAUTH_ACCOUNT_LINK_REQUIRED"

            identity = await session.scalar(
                select(AuthIdentity).where(
                    AuthIdentity.provider_subject == "google-subject"
                )
            )
            assert identity is not None
            await session.rollback()
            result = await service.complete(
                claims=_claims(subject="google-subject"),
                attempt=_attempt(AccountType.ORGANIZATION_APPLICANT),
                metadata=metadata,
            )
            assert result.user_id == identity.user_id
        await engine.dispose()

    asyncio.run(scenario())


def test_pending_staff_is_activated_only_by_verified_totp(tmp_path: Path) -> None:
    async def scenario() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'staff-activation.sqlite3').as_posix()}"
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory.begin() as session:
            staff = User(
                email="reviewer@example.com",
                status=UserStatus.PENDING,
                email_verified_at=NOW,
            )
            role = Role(code="REVIEWER")
            session.add_all((staff, role))
            await session.flush()
            session.add_all(
                (
                    UserRole(user_id=staff.id, role_id=role.id),
                    AuthIdentity(
                        user_id=staff.id,
                        provider=AuthProvider.FIREBASE,
                        provider_subject="firebase-staff",
                    ),
                )
            )
            staff_id = staff.id

        async with factory() as session:
            service = OAuthService(
                session=session,
                session_issuer=FakeIssuer(),
                clock=lambda: NOW,
            )
            with pytest.raises(DomainError) as missing_mfa:
                await service.complete(
                    claims=_claims(
                        email="reviewer@example.com", subject="firebase-staff"
                    ),
                    attempt=_attempt(),
                    metadata=ClientMetadata("127.0.0.1", "test", "Firebase"),
                )
            assert missing_mfa.value.code == "STAFF_MFA_REQUIRED"
            await session.rollback()

            await service.complete(
                claims=FirebaseClaims(
                    subject="firebase-staff",
                    email="reviewer@example.com",
                    email_verified=True,
                    name=None,
                    picture=None,
                    auth_time=NOW,
                    sign_in_second_factor="totp",
                ),
                attempt=_attempt(),
                metadata=ClientMetadata("127.0.0.1", "test", "Firebase"),
            )

        async with factory() as session:
            activated = await session.get(User, staff_id)
            assert activated is not None
            assert activated.status is UserStatus.ACTIVE
            assert "auth.staff_mfa.activated" in set(
                (await session.scalars(select(AuditLog.action))).all()
            )
        await engine.dispose()

    asyncio.run(scenario())


def test_oauth_link_requires_authenticated_target_and_never_grants_privileged_role(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'oauth-link.sqlite3').as_posix()}"
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        issuer = FakeIssuer()
        async with factory() as session:
            async with session.begin():
                user = User(
                    email="owner@example.test",
                    password_hash="hash",
                    status=UserStatus.ACTIVE,
                    email_verified_at=NOW,
                    account_type=AccountType.PUBLIC_USER,
                )
                session.add(user)
                await session.flush()
                user_id = user.id
            service = OAuthService(
                session=session,
                session_issuer=issuer,
                clock=lambda: NOW,
            )
            await service.complete(
                claims=_claims(email="owner@gmail.com", subject="owner-google"),
                attempt=_attempt(purpose="link", user_id=str(user_id)),
                metadata=ClientMetadata("127.0.0.1", None, None),
            )
            identity = await session.scalar(
                select(AuthIdentity).where(AuthIdentity.user_id == user_id)
            )
            assert identity is not None and identity.provider is AuthProvider.FIREBASE
            roles = (
                await session.execute(
                    text(
                        "SELECT code FROM roles JOIN user_roles "
                        "ON roles.id = user_roles.role_id "
                        "WHERE user_roles.user_id = :user_id"
                    ),
                    {"user_id": str(user_id)},
                )
            ).all()
            assert roles == []
        await engine.dispose()

    asyncio.run(scenario())
