from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.modules.audit.service import AuditService
from app.modules.auth.authorization import AuthorizationPolicy, PolicyRequirement
from app.modules.auth.models import (
    PrivilegedAction,
    PrivilegedActionStatus,
    PrivilegedActionType,
    Role,
    UserRole,
    UserStatus,
)
from app.modules.auth.repositories import AuthRepository
from app.modules.auth.schemas import (
    INTERNAL_MANAGED_ROLES,
    PrivilegedActionData,
    PrivilegedActionRequest,
)
from app.modules.auth.session_service import AuthPrincipal


class StaffPrivilegedActionService:
    REQUEST_ACTION = PolicyRequirement(
        permission="admin.staff.manage",
        compatible_roles=frozenset({"SUPER_ADMIN"}),
    )
    APPROVE_ACTION = PolicyRequirement(
        permission="admin.staff.approve",
        compatible_roles=frozenset({"SUPER_ADMIN"}),
    )

    def __init__(
        self,
        *,
        session: AsyncSession,
        clock: Callable[[], datetime] | None = None,
        request_ttl: timedelta = timedelta(hours=24),
    ) -> None:
        self._session = session
        self._repository = AuthRepository(session)
        self._clock = clock or (lambda: datetime.now(UTC))
        self._request_ttl = request_ttl

    async def request(
        self,
        *,
        target_user_id: UUID,
        payload: PrivilegedActionRequest,
        principal: AuthPrincipal,
        audit: AuditService,
        request_id: str | None,
        user_agent: str | None,
    ) -> PrivilegedActionData:
        self._require(principal, self.REQUEST_ACTION, "PRIVILEGED_ACTION_FORBIDDEN")
        if target_user_id == principal.user_id:
            raise DomainError(
                code="PRIVILEGED_ACTION_SELF_TARGET",
                message="You cannot request this action for your own account.",
                status_code=409,
            )
        action_type = PrivilegedActionType(payload.action)
        if (action_type is PrivilegedActionType.ROLE_CHANGE) != (
            payload.requested_role is not None
        ):
            raise DomainError(
                code="PRIVILEGED_ACTION_INVALID",
                message="The privileged action request is invalid.",
                status_code=422,
            )
        now = self._clock()
        action = PrivilegedAction(
            target_user_id=target_user_id,
            action_type=action_type,
            requested_role_code=payload.requested_role,
            reason=payload.reason,
            context={},
            requested_by_user_id=principal.user_id,
            expires_at=now + self._request_ttl,
        )
        try:
            async with self._session.begin():
                target = await self._repository.get_user_by_id_for_update(
                    target_user_id
                )
                if target is None or target.status not in {
                    UserStatus.ACTIVE,
                    UserStatus.SUSPENDED,
                } or target.disabled_at is not None:
                    raise DomainError(
                        code="STAFF_ACCOUNT_NOT_MANAGEABLE",
                        message="The staff account cannot be changed.",
                        status_code=409,
                    )
                roles = await self._repository.get_role_codes(target.id)
                staff_roles = INTERNAL_MANAGED_ROLES | {"SUPER_ADMIN"}
                if not set(roles).intersection(staff_roles):
                    raise DomainError(
                        code="STAFF_ACCOUNT_NOT_FOUND",
                        message="The staff account was not found.",
                        status_code=404,
                    )
                self._session.add(action)
                await self._session.flush()
                audit.record(
                    actor_user_id=principal.user_id,
                    action="admin.privileged_action.requested",
                    resource_type="privileged_action",
                    resource_id=str(action.id),
                    after={
                        "action": action.action_type.value,
                        "target_user_id": str(target.id),
                        "requested_role": action.requested_role_code,
                    },
                    request_id=request_id,
                    user_agent=user_agent,
                )
        except IntegrityError as exc:
            await self._session.rollback()
            raise DomainError(
                code="PRIVILEGED_ACTION_ALREADY_PENDING",
                message="A matching privileged action is already pending.",
                status_code=409,
            ) from exc
        return self._to_data(action)

    async def approve(
        self,
        *,
        action_id: UUID,
        principal: AuthPrincipal,
        audit: AuditService,
        request_id: str | None,
        user_agent: str | None,
    ) -> PrivilegedActionData:
        self._require(principal, self.APPROVE_ACTION, "PRIVILEGED_ACTION_FORBIDDEN")
        now = self._clock()
        async with self._session.begin():
            action = await self._session.scalar(
                select(PrivilegedAction)
                .where(PrivilegedAction.id == action_id)
                .with_for_update()
            )
            if action is None:
                raise DomainError(
                    code="PRIVILEGED_ACTION_NOT_FOUND",
                    message="The privileged action was not found.",
                    status_code=404,
                )
            if action.status is not PrivilegedActionStatus.PENDING:
                raise DomainError(
                    code="PRIVILEGED_ACTION_RESOLVED",
                    message="The privileged action is no longer pending.",
                    status_code=409,
                )
            if self._as_utc(action.expires_at) <= now:
                raise DomainError(
                    code="PRIVILEGED_ACTION_EXPIRED",
                    message="The privileged action has expired.",
                    status_code=409,
                )
            if action.requested_by_user_id == principal.user_id:
                raise DomainError(
                    code="PRIVILEGED_ACTION_SELF_APPROVAL",
                    message="The requester cannot approve this action.",
                    status_code=409,
                )
            target = await self._repository.get_user_by_id_for_update(
                action.target_user_id
            )
            if target is None:
                raise DomainError(
                    code="STAFF_ACCOUNT_NOT_FOUND",
                    message="The staff account was not found.",
                    status_code=404,
                )
            if target.disabled_at is not None:
                raise DomainError(
                    code="STAFF_ACCOUNT_DISABLED",
                    message="A disabled staff account cannot be changed.",
                    status_code=409,
                )
            before_roles = await self._repository.list_user_roles(target.id)
            before: dict[str, object] = {
                "status": target.status.value,
                "roles": sorted(role.code for _, role in before_roles),
            }
            if action.action_type is PrivilegedActionType.ROLE_CHANGE:
                await self._apply_role_change(action, target.id, before_roles)
            else:
                target.status = UserStatus.SUSPENDED
                target.mfa_recovery_authorized_at = now
            revoked = await self._repository.revoke_active_auth_sessions_for_user(
                target.id, now
            )
            action.status = PrivilegedActionStatus.APPROVED
            action.approved_by_user_id = principal.user_id
            action.resolved_at = now
            audit.record(
                actor_user_id=principal.user_id,
                action="admin.privileged_action.approved",
                resource_type="privileged_action",
                resource_id=str(action.id),
                before=before,
                after={
                    "action": action.action_type.value,
                    "requested_role": action.requested_role_code,
                    "revoked_sessions": revoked,
                },
                request_id=request_id,
                user_agent=user_agent,
            )
        return self._to_data(action)

    async def list_pending(
        self,
        *,
        principal: AuthPrincipal,
        page: int,
        page_size: int,
    ) -> tuple[list[PrivilegedActionData], int]:
        self._require(principal, self.APPROVE_ACTION, "PRIVILEGED_ACTION_FORBIDDEN")
        now = self._clock()
        statement = (
            select(PrivilegedAction)
            .where(
                PrivilegedAction.status == PrivilegedActionStatus.PENDING,
                PrivilegedAction.expires_at > now,
            )
            .order_by(PrivilegedAction.created_at.asc(), PrivilegedAction.id)
        )
        rows = tuple(
            (
                await self._session.scalars(
                    statement.offset((page - 1) * page_size).limit(page_size)
                )
            ).all()
        )
        total = int(
            await self._session.scalar(
                select(func.count(PrivilegedAction.id)).where(
                    PrivilegedAction.status == PrivilegedActionStatus.PENDING,
                    PrivilegedAction.expires_at > now,
                )
            )
            or 0
        )
        return [self._to_data(row) for row in rows], total

    async def _apply_role_change(
        self,
        action: PrivilegedAction,
        target_user_id: UUID,
        current_roles: tuple[tuple[UserRole, Role], ...],
    ) -> None:
        requested = action.requested_role_code
        if requested is None or requested not in INTERNAL_MANAGED_ROLES | {
            "SUPER_ADMIN"
        }:
            raise DomainError(
                code="STAFF_ROLE_INVALID",
                message="The requested internal role is not supported.",
                status_code=422,
            )
        role = await self._repository.get_role_by_code(requested)
        if role is None:
            raise DomainError(
                code="STAFF_ROLE_NOT_FOUND",
                message="The requested internal role is not configured.",
                status_code=409,
            )
        for user_role, current_role in current_roles:
            if current_role.code in INTERNAL_MANAGED_ROLES | {"SUPER_ADMIN"}:
                await self._repository.delete_user_role(
                    target_user_id, user_role.role_id
                )
        self._repository.add_user_role(
            UserRole(user_id=target_user_id, role_id=role.id)
        )

    @staticmethod
    def _require(
        principal: AuthPrincipal,
        requirement: PolicyRequirement,
        code: str,
    ) -> None:
        AuthorizationPolicy.require_capability(
            principal,
            requirement,
            lambda: DomainError(
                code=code,
                message="Privileged account management is forbidden.",
                status_code=403,
            ),
        )

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @staticmethod
    def _to_data(action: PrivilegedAction) -> PrivilegedActionData:
        return PrivilegedActionData(
            id=action.id,
            targetUserId=action.target_user_id,
            action=action.action_type.value,
            status=action.status.value,
            requestedRole=action.requested_role_code,
            requestedByUserId=action.requested_by_user_id,
            approvedByUserId=action.approved_by_user_id,
            reason=action.reason,
            expiresAt=action.expires_at,
            resolvedAt=action.resolved_at,
        )


__all__ = ["StaffPrivilegedActionService"]
