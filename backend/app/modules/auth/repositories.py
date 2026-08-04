from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.outbox import OutboxEvent
from app.modules.auth.models import (
    AuthIdentity,
    AuthProvider,
    AuthSession,
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
    VerificationToken,
)


class AuthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_user_by_email(self, email: str) -> User | None:
        return cast(
            User | None,
            await self._session.scalar(select(User).where(User.email == email)),
        )

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        return await self._session.get(User, user_id)

    async def get_identity(
        self,
        *,
        provider: AuthProvider,
        subject: str,
    ) -> AuthIdentity | None:
        return cast(
            AuthIdentity | None,
            await self._session.scalar(
                select(AuthIdentity).where(
                    AuthIdentity.provider == provider,
                    AuthIdentity.provider_subject == subject,
                )
            ),
        )

    async def get_identity_for_user(
        self,
        *,
        user_id: UUID,
        provider: AuthProvider,
    ) -> AuthIdentity | None:
        return cast(
            AuthIdentity | None,
            await self._session.scalar(
                select(AuthIdentity).where(
                    AuthIdentity.user_id == user_id,
                    AuthIdentity.provider == provider,
                )
            ),
        )

    def add_identity(self, identity: AuthIdentity) -> None:
        self._session.add(identity)

    async def get_verification_token_for_update(
        self,
        *,
        token_hash: str,
        purpose: str,
    ) -> VerificationToken | None:
        statement = (
            select(VerificationToken)
            .where(
                VerificationToken.token_hash == token_hash,
                VerificationToken.purpose == purpose,
            )
            .with_for_update()
        )
        return cast(
            VerificationToken | None,
            await self._session.scalar(statement),
        )

    def add_user(self, user: User) -> None:
        self._session.add(user)

    def add_verification_token(self, token: VerificationToken) -> None:
        self._session.add(token)

    async def list_unconsumed_verification_tokens(
        self,
        *,
        user_id: UUID,
        purpose: str,
        for_update: bool = False,
    ) -> tuple[VerificationToken, ...]:
        statement = select(VerificationToken).where(
            VerificationToken.user_id == user_id,
            VerificationToken.purpose == purpose,
            VerificationToken.consumed_at.is_(None),
        )
        if for_update:
            statement = statement.with_for_update()
        return tuple((await self._session.scalars(statement)).all())

    def add_auth_session(self, auth_session: AuthSession) -> None:
        self._session.add(auth_session)

    async def get_auth_session(
        self,
        session_id: UUID,
        *,
        for_update: bool = False,
    ) -> AuthSession | None:
        statement = select(AuthSession).where(AuthSession.id == session_id)
        if for_update:
            statement = statement.with_for_update()
        return cast(AuthSession | None, await self._session.scalar(statement))

    async def get_auth_session_by_refresh_hash(
        self,
        refresh_token_hash: str,
        *,
        for_update: bool = False,
    ) -> AuthSession | None:
        statement = select(AuthSession).where(
            AuthSession.refresh_token_hash == refresh_token_hash
        )
        if for_update:
            statement = statement.with_for_update()
        return cast(AuthSession | None, await self._session.scalar(statement))

    async def list_active_auth_sessions(
        self,
        *,
        user_id: UUID,
        now: datetime,
        for_update: bool = False,
    ) -> tuple[AuthSession, ...]:
        statement = (
            select(AuthSession)
            .where(
                AuthSession.user_id == user_id,
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > now,
            )
            .order_by(AuthSession.created_at.desc())
            .limit(100)
        )
        if for_update:
            statement = statement.with_for_update()
        return tuple((await self._session.scalars(statement)).all())

    async def get_owned_auth_session(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
        for_update: bool = False,
    ) -> AuthSession | None:
        statement = select(AuthSession).where(
            AuthSession.id == session_id,
            AuthSession.user_id == user_id,
        )
        if for_update:
            statement = statement.with_for_update()
        return cast(AuthSession | None, await self._session.scalar(statement))

    async def get_role_codes(self, user_id: UUID) -> tuple[str, ...]:
        statement = (
            select(Role.code)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
            .order_by(Role.code)
        )
        return tuple((await self._session.scalars(statement)).all())

    async def get_permission_codes(self, user_id: UUID) -> tuple[str, ...]:
        statement = (
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
            .distinct()
            .order_by(Permission.code)
        )
        return tuple((await self._session.scalars(statement)).all())

    async def list_user_ids_by_role_codes(
        self, role_codes: frozenset[str]
    ) -> tuple[UUID, ...]:
        statement = (
            select(UserRole.user_id)
            .join(Role, Role.id == UserRole.role_id)
            .where(Role.code.in_(role_codes))
            .distinct()
            .order_by(UserRole.user_id)
        )
        return tuple((await self._session.scalars(statement)).all())

    async def get_role_by_code(self, code: str) -> Role | None:
        return cast(
            Role | None,
            await self._session.scalar(select(Role).where(Role.code == code)),
        )

    def add_role(self, role: Role) -> None:
        self._session.add(role)

    def add_user_role(self, user_role: UserRole) -> None:
        self._session.add(user_role)


class OutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, event: OutboxEvent) -> None:
        self._session.add(event)
