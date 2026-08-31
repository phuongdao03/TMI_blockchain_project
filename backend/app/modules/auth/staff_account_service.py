from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.modules.audit.service import AuditService
from app.modules.auth.authorization import AuthorizationPolicy, PolicyRequirement
from app.modules.auth.firebase_provider import FirebaseClaims
from app.modules.auth.models import (
    AuthProvider,
    Permission,
    User,
    UserPermission,
    UserPermissionRevision,
    UserStatus,
)
from app.modules.auth.repositories import AuthRepository
from app.modules.auth.schemas import (
    INTERNAL_MANAGED_ROLES,
    StaffAccountData,
    StaffAccountStatus,
    StaffAccountUpdateRequest,
    StaffPermissionData,
    StaffPermissionReplaceRequest,
)
from app.modules.auth.session_service import AuthPrincipal


class StaffAccountService:
    MFA_RECOVERY_WINDOW = timedelta(hours=24)
    MANAGE_STAFF = PolicyRequirement(
        permission="admin.staff.manage",
        compatible_roles=frozenset({"SUPER_ADMIN"}),
    )
    ASSIGN_PERMISSIONS = PolicyRequirement(permission="staff.permissions.assign")

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

    async def get_permissions(
        self, user_id: UUID, principal: AuthPrincipal
    ) -> StaffPermissionData:
        self._require_permission_assignment(principal)
        async with self._session.begin():
            user = await self._repository.get_user_by_id(user_id)
            if user is None:
                raise self._permission_error(
                    "STAFF_ACCOUNT_NOT_FOUND", "The staff account was not found.", 404
                )
            permissions = await self._direct_permission_codes(user_id)
            revision = await self._session.get(UserPermissionRevision, user_id)
            return StaffPermissionData(
                userId=user_id,
                permissions=permissions,
                version=revision.version if revision is not None else 0,
            )

    async def replace_permissions(
        self,
        *,
        user_id: UUID,
        payload: StaffPermissionReplaceRequest,
        principal: AuthPrincipal,
        audit: AuditService,
        request_id: str | None,
        user_agent: str | None,
    ) -> StaffPermissionData:
        self._require_permission_assignment(principal)
        if user_id == principal.user_id:
            raise self._permission_error(
                "STAFF_PERMISSION_SELF_ASSIGNMENT",
                "You cannot change your own administrative permissions.",
                409,
            )
        requested = tuple(sorted(set(payload.permissions)))
        if len(requested) != len(payload.permissions) or any(
            not code or len(code) > 128 for code in requested
        ):
            raise self._permission_error(
                "STAFF_PERMISSION_INVALID",
                "Permissions must be unique valid catalog codes.",
                422,
            )
        if "SUPER_ADMIN" not in principal.roles and not set(requested).issubset(
            principal.permissions
        ):
            raise self._permission_error(
                "STAFF_PERMISSION_ESCALATION",
                "You cannot assign a permission you do not hold.",
                403,
            )
        async with self._session.begin():
            target = await self._repository.get_user_by_id_for_update(user_id)
            if target is None:
                raise self._permission_error(
                    "STAFF_ACCOUNT_NOT_FOUND", "The staff account was not found.", 404
                )
            target_roles = set(await self._repository.get_role_codes(user_id))
            if "SUPER_ADMIN" in target_roles:
                raise self._permission_error(
                    "STAFF_ACCOUNT_PROTECTED",
                    "Super Administrator permissions are managed out of band.",
                    409,
                )
            revision = await self._session.scalar(
                select(UserPermissionRevision)
                .where(UserPermissionRevision.user_id == user_id)
                .with_for_update()
            )
            current_version = revision.version if revision is not None else 0
            if current_version != payload.expected_version:
                raise self._permission_error(
                    "STAFF_PERMISSION_VERSION_CONFLICT",
                    "The permission set changed; reload and try again.",
                    409,
                )
            catalog = {
                row.code: row
                for row in (
                    await self._session.scalars(
                        select(Permission).where(Permission.code.in_(requested))
                    )
                ).all()
            }
            if set(catalog) != set(requested):
                raise self._permission_error(
                    "STAFF_PERMISSION_INVALID",
                    "One or more permissions are not in the catalog.",
                    422,
                )
            before = await self._direct_permission_codes(user_id)
            await self._session.execute(
                delete(UserPermission).where(UserPermission.user_id == user_id)
            )
            next_version = current_version + 1
            self._session.add_all(
                [
                    UserPermission(
                        user_id=user_id,
                        permission_id=catalog[code].id,
                        granted_by_user_id=principal.user_id,
                        reason=payload.reason,
                        version=next_version,
                    )
                    for code in requested
                ]
            )
            if revision is None:
                revision = UserPermissionRevision(
                    user_id=user_id,
                    updated_by_user_id=principal.user_id,
                    reason=payload.reason,
                    version=next_version,
                )
                self._session.add(revision)
            else:
                revision.version = next_version
                revision.updated_by_user_id = principal.user_id
                revision.reason = payload.reason
            audit.record(
                actor_user_id=principal.user_id,
                action="admin.staff_permissions.replaced",
                resource_type="user",
                resource_id=str(user_id),
                before={"permissions": list(before), "version": current_version},
                after={
                    "permissions": list(requested),
                    "reason": payload.reason,
                    "version": next_version,
                },
                request_id=request_id,
                user_agent=user_agent,
            )
        return StaffPermissionData(
            userId=user_id, permissions=requested, version=next_version
        )

    async def _direct_permission_codes(self, user_id: UUID) -> tuple[str, ...]:
        statement = (
            select(Permission.code)
            .join(UserPermission, UserPermission.permission_id == Permission.id)
            .where(UserPermission.user_id == user_id)
            .order_by(Permission.code)
        )
        return tuple((await self._session.scalars(statement)).all())

    @staticmethod
    def _require_permission_assignment(principal: AuthPrincipal) -> None:
        AuthorizationPolicy.require_capability(
            principal,
            StaffAccountService.ASSIGN_PERMISSIONS,
            lambda: StaffAccountService._permission_error(
                "STAFF_PERMISSION_FORBIDDEN",
                "Staff permission management is forbidden.",
                403,
            ),
        )

    @staticmethod
    def _permission_error(code: str, message: str, status: int) -> DomainError:
        return DomainError(code=code, message=message, status_code=status)

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
