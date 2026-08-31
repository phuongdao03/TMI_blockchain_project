from datetime import datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import delete, distinct, func, or_, select
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
    UserPermission,
    UserRole,
    UserStatus,
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

    async def get_user_by_id_for_update(self, user_id: UUID) -> User | None:
        statement = select(User).where(User.id == user_id).with_for_update()
        return cast(User | None, await self._session.scalar(statement))

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
        role_permissions = (
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
        )
        user_permissions = (
            select(Permission.code)
            .join(
                UserPermission,
                UserPermission.permission_id == Permission.id,
            )
            .where(
                UserPermission.user_id == user_id,
                or_(
                    UserPermission.expires_at.is_(None),
                    UserPermission.expires_at > func.now(),
                ),
            )
        )
        effective = role_permissions.union(user_permissions).subquery()
        statement = select(effective.c.code).order_by(effective.c.code)
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

    async def list_internal_users(
        self,
        *,
        page: int,
        page_size: int,
        query: str | None = None,
        role_code: str | None = None,
        account_status: str | None = None,
    ) -> tuple[tuple[User, str], ...]:
        internal_codes = ("MODERATOR", "SUPER_ADMIN")
        statement = (
            select(User, Role.code)
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .where(
                Role.code.in_(internal_codes),
                User.status.in_(
                    (UserStatus.PENDING, UserStatus.ACTIVE, UserStatus.SUSPENDED)
                ),
            )
            .order_by(User.created_at.desc(), User.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        if query:
            statement = statement.where(User.email.ilike(f"%{query.strip()}%"))
        if role_code:
            statement = statement.where(Role.code == role_code)
        statement = self._filter_staff_status(statement, account_status)
        rows = (await self._session.execute(statement)).all()
        return tuple((user, str(code)) for user, code in rows)

    async def count_internal_users(
        self,
        *,
        query: str | None = None,
        role_code: str | None = None,
        account_status: str | None = None,
    ) -> int:
        internal_codes = ("MODERATOR", "SUPER_ADMIN")
        statement = (
            select(func.count(distinct(User.id)))
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .where(
                Role.code.in_(internal_codes),
                User.status.in_(
                    (UserStatus.PENDING, UserStatus.ACTIVE, UserStatus.SUSPENDED)
                ),
            )
        )
        if query:
            statement = statement.where(User.email.ilike(f"%{query.strip()}%"))
        if role_code:
            statement = statement.where(Role.code == role_code)
        statement = self._filter_staff_status(statement, account_status)
        return int(await self._session.scalar(statement) or 0)

    @staticmethod
    def _filter_staff_status(statement: Any, account_status: str | None) -> Any:
        if account_status == "PENDING_MFA":
            return statement.where(User.status == UserStatus.PENDING)
        if account_status == "ACTIVE":
            return statement.where(User.status == UserStatus.ACTIVE)
        if account_status == "SUSPENDED":
            return statement.where(
                User.status == UserStatus.SUSPENDED,
                User.disabled_at.is_(None),
            )
        if account_status == "DISABLED":
            return statement.where(
                User.status == UserStatus.SUSPENDED,
                User.disabled_at.is_not(None),
            )
        return statement

    async def list_user_roles(self, user_id: UUID) -> tuple[tuple[UserRole, Role], ...]:
        statement = (
            select(UserRole, Role)
            .join(Role, Role.id == UserRole.role_id)
            .where(UserRole.user_id == user_id)
            .order_by(Role.code)
        )
        result = await self._session.execute(statement)
        return tuple((row[0], row[1]) for row in result.all())

    async def delete_user_role(self, user_id: UUID, role_id: UUID) -> None:
        await self._session.execute(
            delete(UserRole).where(
                UserRole.user_id == user_id,
                UserRole.role_id == role_id,
            )
        )

    async def revoke_active_auth_sessions_for_user(
        self, user_id: UUID, now: datetime
    ) -> int:
        sessions = await self.list_active_auth_sessions(
            user_id=user_id, now=now, for_update=True
        )
        for auth_session in sessions:
            auth_session.revoked_at = now
        return len(sessions)


class OutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, event: OutboxEvent) -> None:
        self._session.add(event)
