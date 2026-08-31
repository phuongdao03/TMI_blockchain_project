from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import Select, asc, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.core.errors import DomainError
from app.modules.audit.service import AuditService
from app.modules.auth.authorization import AuthorizationPolicy, PolicyRequirement
from app.modules.auth.firebase_admin_gateway import (
    FirebaseAdminClient,
    FirebaseAdminError,
)
from app.modules.auth.models import (
    AuthIdentity,
    AuthProvider,
    Role,
    User,
    UserRole,
    UserStatus,
)
from app.modules.auth.repositories import AuthRepository
from app.modules.auth.session_service import AuthPrincipal
from app.modules.users.models import UserProfile

SortField = Literal["createdAt", "email", "lastLoginAt", "status"]
SortOrder = Literal["asc", "desc"]
SORT_COLUMNS = {
    "createdAt": User.created_at,
    "email": User.email,
    "lastLoginAt": User.last_login_at,
    "status": User.status,
}


@dataclass(frozen=True, slots=True)
class AdminUserQuery:
    page: int
    page_size: int
    search: str | None = None
    status: UserStatus | None = None
    provider: AuthProvider | None = None
    verified: bool | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None
    sort_by: SortField = "createdAt"
    sort_order: SortOrder = "desc"

    def __post_init__(self) -> None:
        if self.page < 1 or not 1 <= self.page_size <= 100:
            raise ValueError("Admin user pagination is invalid.")
        if self.sort_by not in SORT_COLUMNS or self.sort_order not in {"asc", "desc"}:
            raise ValueError("Admin user sorting is invalid.")
        if (
            self.created_from
            and self.created_to
            and self.created_from >= self.created_to
        ):
            raise ValueError("Admin user date range is invalid.")


class AdminUserData(BaseModel):
    model_config = ConfigDict(
        extra="forbid", populate_by_name=True, serialize_by_alias=True
    )

    id: UUID
    email: EmailStr
    full_name: str | None = Field(default=None, alias="fullName")
    status: UserStatus
    is_email_verified: bool = Field(alias="isEmailVerified")
    providers: tuple[str, ...]
    roles: tuple[str, ...]
    created_at: datetime = Field(alias="createdAt")
    last_login_at: datetime | None = Field(default=None, alias="lastLoginAt")
    disabled_at: datetime | None = Field(default=None, alias="disabledAt")
    deleted_at: datetime | None = Field(default=None, alias="deletedAt")


class AdminUserStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    status: Literal[UserStatus.ACTIVE, UserStatus.SUSPENDED]
    expected_status: UserStatus = Field(alias="expectedStatus")
    reason: str = Field(min_length=10, max_length=500)


class AdminUserService:
    READ_USERS = PolicyRequirement(permission="users.read")
    SUSPEND_USERS = PolicyRequirement(permission="users.suspend")

    def __init__(
        self,
        session: AsyncSession,
        *,
        firebase_admin: FirebaseAdminClient | None = None,
    ) -> None:
        self._session = session
        self._firebase_admin = firebase_admin

    async def list(
        self, principal: AuthPrincipal, query: AdminUserQuery
    ) -> tuple[tuple[AdminUserData, ...], int]:
        self._require_read(principal)
        statement = self._apply_filters(
            select(User, UserProfile.full_name).outerjoin(
                UserProfile, UserProfile.user_id == User.id
            ),
            query,
        )
        count_statement = self._apply_filters(
            select(func.count(User.id)).outerjoin(
                UserProfile, UserProfile.user_id == User.id
            ),
            query,
        )
        sort_column = SORT_COLUMNS[query.sort_by]
        direction = asc if query.sort_order == "asc" else desc
        statement = (
            statement.order_by(direction(sort_column), direction(User.id))
            .offset((query.page - 1) * query.page_size)
            .limit(query.page_size)
        )
        async with self._session.begin():
            raw_rows = tuple(
                (row[0], row[1])
                for row in (await self._session.execute(statement)).all()
            )
            total = int((await self._session.scalar(count_statement)) or 0)
            return await self._hydrate(raw_rows), total

    async def detail(self, principal: AuthPrincipal, user_id: UUID) -> AdminUserData:
        self._require_read(principal)
        async with self._session.begin():
            row = (
                await self._session.execute(
                    select(User, UserProfile.full_name)
                    .outerjoin(UserProfile, UserProfile.user_id == User.id)
                    .where(User.id == user_id)
                )
            ).one_or_none()
            if row is None:
                raise DomainError(
                    code="ADMIN_USER_NOT_FOUND",
                    message="The user account was not found.",
                    status_code=404,
                )
            return (await self._hydrate(((row[0], row[1]),)))[0]

    async def change_status(
        self,
        principal: AuthPrincipal,
        user_id: UUID,
        payload: AdminUserStatusRequest,
        *,
        audit: AuditService,
        request_id: str | None,
        user_agent: str | None,
    ) -> AdminUserData:
        AuthorizationPolicy.require_capability(
            principal,
            self.SUSPEND_USERS,
            lambda: DomainError(
                code="ADMIN_USER_STATUS_FORBIDDEN",
                message="User status management is forbidden.",
                status_code=403,
            ),
        )
        if user_id == principal.user_id:
            raise DomainError(
                code="ADMIN_USER_SELF_SUSPEND",
                message="You cannot change your own account status.",
                status_code=409,
            )
        repository = AuthRepository(self._session)
        async with self._session.begin():
            user = await repository.get_user_by_id_for_update(user_id)
            if user is None:
                raise DomainError(
                    code="ADMIN_USER_NOT_FOUND",
                    message="The user account was not found.",
                    status_code=404,
                )
            if "SUPER_ADMIN" in await repository.get_role_codes(user_id):
                raise DomainError(
                    code="ADMIN_USER_PROTECTED",
                    message="Super Administrator is managed out of band.",
                    status_code=409,
                )
            if user.status is not payload.expected_status:
                raise DomainError(
                    code="ADMIN_USER_STATUS_CONFLICT",
                    message="The user status changed; reload and try again.",
                    status_code=409,
                )
            if user.status not in {UserStatus.ACTIVE, UserStatus.SUSPENDED}:
                raise DomainError(
                    code="ADMIN_USER_STATUS_INVALID",
                    message="This account status cannot be changed here.",
                    status_code=409,
                )
            if user.disabled_at is not None:
                raise DomainError(
                    code="ADMIN_USER_DISABLED",
                    message="A disabled account cannot be restored here.",
                    status_code=409,
                )
            before_status = user.status
            firebase_identity = await repository.get_identity_for_user(
                user_id=user.id,
                provider=AuthProvider.FIREBASE,
            )
            if firebase_identity is not None:
                if self._firebase_admin is None:
                    raise DomainError(
                        code="FIREBASE_ADMIN_UNAVAILABLE",
                        message="Firebase account synchronization is unavailable.",
                        status_code=503,
                    )
                try:
                    await self._firebase_admin.set_disabled(
                        firebase_identity.provider_subject,
                        disabled=payload.status is UserStatus.SUSPENDED,
                    )
                except FirebaseAdminError as exc:
                    raise DomainError(
                        code="FIREBASE_USER_SYNC_FAILED",
                        message="Firebase account status could not be synchronized.",
                        status_code=502,
                    ) from exc
            user.status = payload.status
            if payload.status is UserStatus.SUSPENDED:
                await repository.revoke_active_auth_sessions_for_user(
                    user.id, datetime.now(UTC)
                )
            audit.record(
                actor_user_id=principal.user_id,
                action="admin.user.status_changed",
                resource_type="user",
                resource_id=str(user.id),
                before={"status": before_status.value},
                after={"status": user.status.value, "reason": payload.reason},
                request_id=request_id,
                user_agent=user_agent,
            )
            full_name = await self._session.scalar(
                select(UserProfile.full_name).where(UserProfile.user_id == user.id)
            )
            return (await self._hydrate(((user, full_name),)))[0]

    @staticmethod
    def _apply_filters(statement: Select[Any], query: AdminUserQuery) -> Select[Any]:
        if query.search:
            term = query.search.strip()
            conditions: list[ColumnElement[bool]] = [
                User.email.ilike(f"%{term}%"),
                UserProfile.full_name.ilike(f"%{term}%"),
            ]
            try:
                conditions.append(User.id == UUID(term))
            except ValueError:
                pass
            statement = statement.where(or_(*conditions))
        if query.status is not None:
            statement = statement.where(User.status == query.status)
        if query.verified is True:
            statement = statement.where(User.email_verified_at.is_not(None))
        elif query.verified is False:
            statement = statement.where(User.email_verified_at.is_(None))
        if query.provider is not None:
            statement = statement.where(
                select(AuthIdentity.id)
                .where(
                    AuthIdentity.user_id == User.id,
                    AuthIdentity.provider == query.provider,
                )
                .exists()
            )
        if query.created_from is not None:
            statement = statement.where(User.created_at >= query.created_from)
        if query.created_to is not None:
            statement = statement.where(User.created_at < query.created_to)
        return statement

    async def _hydrate(
        self, rows: tuple[tuple[User, str | None], ...]
    ) -> tuple[AdminUserData, ...]:
        user_ids = tuple(row[0].id for row in rows)
        if not user_ids:
            return ()
        role_rows = (
            await self._session.execute(
                select(UserRole.user_id, Role.code)
                .join(Role, Role.id == UserRole.role_id)
                .where(UserRole.user_id.in_(user_ids))
                .order_by(Role.code)
            )
        ).all()
        identity_rows = (
            await self._session.execute(
                select(AuthIdentity.user_id, AuthIdentity.provider)
                .where(AuthIdentity.user_id.in_(user_ids))
                .order_by(AuthIdentity.provider)
            )
        ).all()
        roles: dict[UUID, list[str]] = {user_id: [] for user_id in user_ids}
        providers: dict[UUID, list[str]] = {user_id: [] for user_id in user_ids}
        for user_id, code in role_rows:
            roles[user_id].append(str(code))
        for user_id, provider in identity_rows:
            providers[user_id].append(provider.value)
        return tuple(
            AdminUserData(
                id=user.id,
                email=user.email,
                fullName=full_name,
                status=user.status,
                isEmailVerified=user.email_verified_at is not None,
                providers=tuple(providers[user.id]),
                roles=tuple(roles[user.id]),
                createdAt=user.created_at,
                lastLoginAt=user.last_login_at,
                disabledAt=user.disabled_at,
                deletedAt=user.deleted_at,
            )
            for user, full_name in rows
        )

    @staticmethod
    def _require_read(principal: AuthPrincipal) -> None:
        AuthorizationPolicy.require_capability(
            principal,
            AdminUserService.READ_USERS,
            lambda: DomainError(
                code="ADMIN_USER_FORBIDDEN",
                message="User administration is forbidden.",
                status_code=403,
            ),
        )
