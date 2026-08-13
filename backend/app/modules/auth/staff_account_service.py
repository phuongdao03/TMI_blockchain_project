from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.modules.audit.service import AuditService
from app.modules.auth.authorization import AuthorizationPolicy, PolicyRequirement
from app.modules.auth.firebase_provider import FirebaseClaims
from app.modules.auth.models import AuthProvider, User, UserStatus
from app.modules.auth.repositories import AuthRepository
from app.modules.auth.schemas import (
    INTERNAL_MANAGED_ROLES,
    StaffAccountData,
    StaffAccountStatus,
    StaffAccountUpdateRequest,
)
from app.modules.auth.session_service import AuthPrincipal


class StaffAccountService:
    MFA_RECOVERY_WINDOW = timedelta(hours=24)
    MANAGE_STAFF = PolicyRequirement(
        permission="admin.staff.manage",
        compatible_roles=frozenset({"SUPER_ADMIN"}),
    )

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = AuthRepository(session)

    @staticmethod
    def require_super_admin(principal: AuthPrincipal) -> None:
        AuthorizationPolicy.require_capability(
            principal,
            StaffAccountService.MANAGE_STAFF,
            lambda: DomainError(
                code="STAFF_ACCOUNT_FORBIDDEN",
                message="Staff account management is forbidden.",
                status_code=403,
            ),
        )

    async def list(
        self,
        *,
        page: int,
        page_size: int,
        query: str | None = None,
        role: str | None = None,
        status: StaffAccountStatus | None = None,
    ) -> tuple[list[StaffAccountData], int]:
        if (
            role is not None
            and role not in INTERNAL_MANAGED_ROLES
            and role != "SUPER_ADMIN"
        ):
            raise DomainError(
                code="STAFF_ROLE_INVALID",
                message="The requested internal role is not supported.",
                status_code=422,
            )
        rows = await self._repository.list_internal_users(
            page=page,
            page_size=page_size,
            query=query,
            role_code=role,
            account_status=status,
        )
        total = await self._repository.count_internal_users(
            query=query, role_code=role, account_status=status
        )
        return [self._to_data(user, role_code) for user, role_code in rows], total

    async def update(
        self,
        *,
        user_id: UUID,
        payload: StaffAccountUpdateRequest,
        principal: AuthPrincipal,
        audit: AuditService,
        request_id: str | None,
        user_agent: str | None,
    ) -> StaffAccountData:
        self.require_super_admin(principal)
        if payload.role is None and payload.status is None:
            raise DomainError(
                code="STAFF_ACCOUNT_NO_CHANGES",
                message="At least one account field must be changed.",
                status_code=422,
            )
        if payload.role is not None:
            raise DomainError(
                code="STAFF_ROLE_DUAL_CONTROL_REQUIRED",
                message="Role changes require a separate approval.",
                status_code=409,
            )
        if user_id == principal.user_id and payload.status in {
            "SUSPENDED",
            "DISABLED",
        }:
            raise DomainError(
                code="STAFF_ACCOUNT_SELF_SUSPEND",
                message="You cannot suspend your own administrator account.",
                status_code=409,
            )
        async with self._session.begin():
            user = await self._repository.get_user_by_id_for_update(user_id)
            if user is None:
                raise DomainError(
                    code="STAFF_ACCOUNT_NOT_FOUND",
                    message="The staff account was not found.",
                    status_code=404,
                )
            if user.status not in {UserStatus.ACTIVE, UserStatus.SUSPENDED}:
                raise DomainError(
                    code="STAFF_ACCOUNT_NOT_MANAGEABLE",
                    message="Only active or suspended staff accounts can be managed.",
                    status_code=409,
                )
            if user.disabled_at is not None and payload.status != "DISABLED":
                raise DomainError(
                    code="STAFF_ACCOUNT_DISABLED",
                    message="A disabled staff account cannot be reactivated directly.",
                    status_code=409,
                )
            current_roles = await self._repository.list_user_roles(user.id)
            current_codes = {role.code for _, role in current_roles}
            if "SUPER_ADMIN" in current_codes:
                raise DomainError(
                    code="STAFF_ACCOUNT_PROTECTED",
                    message=(
                        "The bootstrap administrator account must be managed "
                        "out of band."
                    ),
                    status_code=409,
                )
            before: dict[str, object] = {
                "status": user.status.value,
                "roles": sorted(current_codes),
            }
            current_internal_role = next(
                (
                    code
                    for code in sorted(current_codes)
                    if code in INTERNAL_MANAGED_ROLES
                ),
                "",
            )
            if payload.status is not None:
                now = datetime.now(UTC)
                if payload.status == "ACTIVE":
                    user.status = UserStatus.ACTIVE
                    user.disabled_at = None
                elif payload.status == "SUSPENDED":
                    user.status = UserStatus.SUSPENDED
                    user.disabled_at = None
                else:
                    user.status = UserStatus.SUSPENDED
                    user.disabled_at = now
                if payload.status != "ACTIVE":
                    await self._repository.revoke_active_auth_sessions_for_user(
                        user.id, now
                    )
            await self._session.flush()
            after: dict[str, object] = {
                "status": user.status.value,
                "role": current_internal_role,
            }
            audit.record(
                actor_user_id=principal.user_id,
                action="admin.staff_account.updated",
                resource_type="user",
                resource_id=str(user.id),
                before=before,
                after=after,
                request_id=request_id,
                user_agent=user_agent,
            )
            role_code = current_internal_role
        return self._to_data(user, role_code)

    async def authorize_mfa_reenrollment(
        self,
        *,
        claims: FirebaseClaims,
        audit: AuditService,
        request_id: str | None,
        user_agent: str | None,
    ) -> None:
        invalid = DomainError(
            code="STAFF_MFA_RECOVERY_INVALID",
            message="The MFA recovery request is invalid or expired.",
            status_code=400,
        )
        if not claims.email_verified:
            raise invalid
        now = datetime.now(UTC)
        async with self._session.begin():
            identity = await self._repository.get_identity(
                provider=AuthProvider.FIREBASE,
                subject=claims.subject,
            )
            if identity is None:
                raise invalid
            user = await self._repository.get_user_by_id_for_update(identity.user_id)
            if (
                user is None
                or user.email.lower() != claims.email.lower()
                or user.status is not UserStatus.SUSPENDED
                or user.mfa_recovery_authorized_at is None
            ):
                raise invalid
            authorized_at = user.mfa_recovery_authorized_at
            if authorized_at.tzinfo is None:
                authorized_at = authorized_at.replace(tzinfo=UTC)
            if authorized_at + self.MFA_RECOVERY_WINDOW <= now:
                raise invalid
            roles = await self._repository.get_role_codes(user.id)
            if not set(roles).intersection(INTERNAL_MANAGED_ROLES):
                raise invalid
            user.status = UserStatus.PENDING
            audit.record(
                actor_user_id=user.id,
                action="auth.staff_mfa_recovery.authorized",
                resource_type="user",
                resource_id=str(user.id),
                before={"status": UserStatus.SUSPENDED.value},
                after={
                    "status": "PENDING_MFA",
                    "mfa_enrollment_required": True,
                },
                request_id=request_id,
                user_agent=user_agent,
            )

    @staticmethod
    def _to_data(user: User, role_code: str) -> StaffAccountData:
        status: StaffAccountStatus = cast(StaffAccountStatus, user.status.value)
        if user.status is UserStatus.PENDING:
            status = "PENDING_MFA"
        elif user.disabled_at is not None or user.status is UserStatus.DELETED:
            status = "DISABLED"
        return StaffAccountData(
            id=user.id,
            email=user.email,
            role=role_code,
            status=status,
            createdAt=user.created_at,
            lastLoginAt=user.last_login_at,
        )
