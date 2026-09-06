import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.db.outbox import OutboxEvent
from app.modules.audit.service import AuditService
from app.modules.auth.authorization import AuthorizationPolicy, PolicyRequirement
from app.modules.auth.firebase_provider import FirebaseClaims
from app.modules.auth.models import (
    AuthIdentity,
    AuthProvider,
    StaffInvitation,
    User,
    UserRole,
    UserStatus,
)
from app.modules.auth.repositories import AuthRepository, OutboxRepository
from app.modules.auth.schemas import (
    INTERNAL_MANAGED_ROLES,
    StaffAccountData,
    StaffInvitationData,
    StaffInvitationRequest,
    StaffInvitationStatus,
)
from app.modules.auth.security import OutboxPayloadCipher, hash_verification_token
from app.modules.auth.session_service import AuthPrincipal
from app.modules.notifications.models import Notification
from app.modules.organizations.models import (
    MembershipRole,
    MembershipStatus,
    Organization,
    OrganizationMember,
)

STAFF_INVITATION_EVENT = "staff.invited"


class StaffInvitationService:
    MANAGE_STAFF = PolicyRequirement(
        permission="admin.staff.manage",
        compatible_roles=frozenset({"SUPER_ADMIN"}),
    )

    def __init__(
        self,
        *,
        session: AsyncSession,
        payload_cipher: OutboxPayloadCipher,
        invitation_ttl: timedelta,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session = session
        self._auth = AuthRepository(session)
        self._outbox = OutboxRepository(session)
        self._payload_cipher = payload_cipher
        self._invitation_ttl = invitation_ttl
        self._clock = clock or (lambda: datetime.now(UTC))

    @staticmethod
    def require_super_admin(principal: AuthPrincipal) -> None:
        StaffInvitationService._require_admin(principal)

    async def create(
        self,
        *,
        payload: StaffInvitationRequest,
        principal: AuthPrincipal,
        audit: AuditService,
        request_id: str | None,
        user_agent: str | None,
    ) -> StaffInvitationData:
        self._require_admin(principal)
        email = str(payload.email).strip().lower()
        now = self._clock()
        try:
            async with self._session.begin():
                target_user = await self._validate_target(
                    email=email,
                    role_code=payload.role,
                    organization_id=payload.organization_id,
                )
                active = tuple(
                    (
                        await self._session.scalars(
                            select(StaffInvitation)
                            .where(
                                StaffInvitation.email == email,
                                StaffInvitation.accepted_at.is_(None),
                                StaffInvitation.revoked_at.is_(None),
                            )
                            .with_for_update()
                        )
                    ).all()
                )
                for previous in active:
                    previous.revoked_at = now
                    previous_user = await self._auth.get_user_by_email(previous.email)
                    if previous_user is not None:
                        await self._resolve_recipient_notification(
                            invitation=previous,
                            user_id=previous_user.id,
                            decision="REPLACED",
                            now=now,
                        )
                invitation, raw_token = self._new_invitation(
                    email=email,
                    role_code=payload.role,
                    organization_id=payload.organization_id,
                    created_by_user_id=principal.user_id,
                    now=now,
                )
                self._session.add(invitation)
                await self._session.flush()
                self._enqueue(invitation, raw_token=raw_token, now=now)
                if target_user is not None:
                    self._session.add(
                        Notification(
                            user_id=target_user.id,
                            source_event_id=invitation.id,
                            type="staff.reviewer_invited",
                            title="Lời mời trở thành Người kiểm duyệt",
                            body=(
                                "Quản trị viên mời bạn tham gia thẩm định hồ sơ. "
                                "Hãy xem và xác nhận lời mời."
                            ),
                            data_json={
                                "actionPath": "/notifications",
                                "invitationId": str(invitation.id),
                                "role": invitation.role_code,
                            },
                            created_at=now,
                        )
                    )
                audit.record(
                    actor_user_id=principal.user_id,
                    action="admin.staff_invitation.created",
                    resource_type="staff_invitation",
                    resource_id=str(invitation.id),
                    after={"email": email, "role": payload.role},
                    request_id=request_id,
                    user_agent=user_agent,
                )
        except IntegrityError as exc:
            await self._session.rollback()
            raise DomainError(
                code="STAFF_INVITATION_CONFLICT",
                message="An active invitation already exists for this email.",
                status_code=409,
            ) from exc
        return self._to_data(invitation, now=now)

    async def resend(
        self,
        *,
        invitation_id: UUID,
        principal: AuthPrincipal,
        audit: AuditService,
        request_id: str | None,
        user_agent: str | None,
    ) -> StaffInvitationData:
        self._require_admin(principal)
        now = self._clock()
        async with self._session.begin():
            invitation = await self._locked(invitation_id)
            self._require_pending(invitation, now=now)
            await self._cancel_pending_delivery(invitation.id, now=now)
            raw_token = secrets.token_urlsafe(32)
            invitation.token_hash = hash_verification_token(raw_token)
            invitation.expires_at = now + self._invitation_ttl
            self._enqueue(invitation, raw_token=raw_token, now=now)
            audit.record(
                actor_user_id=principal.user_id,
                action="admin.staff_invitation.resent",
                resource_type="staff_invitation",
                resource_id=str(invitation.id),
                request_id=request_id,
                user_agent=user_agent,
            )
        return self._to_data(invitation, now=now)

    async def revoke(
        self,
        *,
        invitation_id: UUID,
        principal: AuthPrincipal,
        audit: AuditService,
        request_id: str | None,
        user_agent: str | None,
    ) -> StaffInvitationData:
        self._require_admin(principal)
        now = self._clock()
        async with self._session.begin():
            invitation = await self._locked(invitation_id)
            self._require_pending(invitation, now=now)
            await self._cancel_pending_delivery(invitation.id, now=now)
            invitation.revoked_at = now
            invited_user = await self._auth.get_user_by_email(invitation.email)
            if invited_user is not None:
                await self._resolve_recipient_notification(
                    invitation=invitation,
                    user_id=invited_user.id,
                    decision="REVOKED",
                    now=now,
                )
            audit.record(
                actor_user_id=principal.user_id,
                action="admin.staff_invitation.revoked",
                resource_type="staff_invitation",
                resource_id=str(invitation.id),
                request_id=request_id,
                user_agent=user_agent,
            )
        return self._to_data(invitation, now=now)

    async def accept(
        self,
        *,
        raw_token: str,
        claims: FirebaseClaims,
        audit: AuditService,
        request_id: str | None,
        user_agent: str | None,
    ) -> StaffAccountData:
        if not claims.email_verified:
            raise self._invalid()
        now = self._clock()
        try:
            async with self._session.begin():
                invitation = await self._session.scalar(
                    select(StaffInvitation)
                    .where(
                        StaffInvitation.token_hash == hash_verification_token(raw_token)
                    )
                    .with_for_update()
                )
                self._require_pending(invitation, now=now)
                assert invitation is not None
                email = claims.email.strip().lower()
                if email != invitation.email:
                    raise self._invalid()
                existing_user = await self._auth.get_user_by_email(email)
                identity = await self._auth.get_identity(
                    provider=AuthProvider.FIREBASE,
                    subject=claims.subject,
                )
                if existing_user is not None and (
                    identity is None or identity.user_id != existing_user.id
                ):
                    raise self._invalid()
                if existing_user is None and identity is not None:
                    raise self._invalid()
                role = await self._auth.get_role_by_code(invitation.role_code)
                if role is None or role.code not in INTERNAL_MANAGED_ROLES:
                    raise self._invalid()

                if existing_user is None:
                    user = User(
                        email=email,
                        password_hash=None,
                        status=UserStatus.ACTIVE,
                        email_verified_at=now,
                    )
                    self._auth.add_user(user)
                    await self._session.flush()
                    self._auth.add_identity(
                        AuthIdentity(
                            user_id=user.id,
                            provider=AuthProvider.FIREBASE,
                            provider_subject=claims.subject,
                            last_login_at=now,
                        )
                    )
                else:
                    user = existing_user
                    if (
                        user.status is not UserStatus.ACTIVE
                        or user.email_verified_at is None
                    ):
                        raise self._invalid()
                if not await self._session.get(UserRole, (user.id, role.id)):
                    self._auth.add_user_role(UserRole(user_id=user.id, role_id=role.id))
                if invitation.organization_id is not None:
                    self._session.add(
                        OrganizationMember(
                            organization_id=invitation.organization_id,
                            user_id=user.id,
                            role_code=MembershipRole.MEMBER,
                            status=MembershipStatus.ACTIVE,
                            joined_at=now,
                        )
                    )
                invitation.accepted_at = now
                invitation.accepted_user_id = user.id
                audit.record(
                    actor_user_id=user.id,
                    action="auth.staff_invitation.accepted",
                    resource_type="staff_invitation",
                    resource_id=str(invitation.id),
                    after={"role": invitation.role_code},
                    request_id=request_id,
                    user_agent=user_agent,
                )
        except IntegrityError as exc:
            await self._session.rollback()
            raise self._invalid() from exc
        return StaffAccountData(
            id=user.id,
            email=user.email,
            role=invitation.role_code,
            status="ACTIVE",
            createdAt=user.created_at,
            lastLoginAt=user.last_login_at,
        )

    async def accept_existing(
        self,
        *,
        invitation_id: UUID,
        principal: AuthPrincipal,
        audit: AuditService,
        request_id: str | None,
        user_agent: str | None,
    ) -> None:
        now = self._clock()
        async with self._session.begin():
            invitation = await self._locked(invitation_id)
            self._require_pending(invitation, now=now)
            if invitation.email != principal.email.strip().lower():
                raise DomainError(
                    code="STAFF_INVITATION_FORBIDDEN",
                    message="This invitation belongs to another account.",
                    status_code=403,
                )
            user = await self._auth.get_user_by_id_for_update(principal.user_id)
            if (
                user is None
                or user.email.strip().lower() != invitation.email
                or user.status is not UserStatus.ACTIVE
                or user.email_verified_at is None
            ):
                raise self._invalid()
            role = await self._auth.get_role_by_code(invitation.role_code)
            if role is None or role.code not in INTERNAL_MANAGED_ROLES:
                raise self._invalid()
            current_roles = set(await self._auth.get_role_codes(user.id))
            if "SUPER_ADMIN" in current_roles:
                raise self._invalid()
            if role.code not in current_roles:
                self._auth.add_user_role(UserRole(user_id=user.id, role_id=role.id))
            invitation.accepted_at = now
            invitation.accepted_user_id = user.id
            await self._resolve_recipient_notification(
                invitation=invitation, user_id=user.id, decision="ACCEPTED", now=now
            )
            audit.record(
                actor_user_id=user.id,
                action="auth.staff_invitation.accepted",
                resource_type="staff_invitation",
                resource_id=str(invitation.id),
                after={"role": invitation.role_code},
                request_id=request_id,
                user_agent=user_agent,
            )

    async def decline_existing(
        self,
        *,
        invitation_id: UUID,
        principal: AuthPrincipal,
        audit: AuditService,
        request_id: str | None,
        user_agent: str | None,
    ) -> None:
        now = self._clock()
        async with self._session.begin():
            invitation = await self._locked(invitation_id)
            self._require_pending(invitation, now=now)
            if invitation.email != principal.email.strip().lower():
                raise DomainError(
                    code="STAFF_INVITATION_FORBIDDEN",
                    message="This invitation belongs to another account.",
                    status_code=403,
                )
            invitation.revoked_at = now
            await self._resolve_recipient_notification(
                invitation=invitation,
                user_id=principal.user_id,
                decision="DECLINED",
                now=now,
            )
            audit.record(
                actor_user_id=principal.user_id,
                action="auth.staff_invitation.declined",
                resource_type="staff_invitation",
                resource_id=str(invitation.id),
                request_id=request_id,
                user_agent=user_agent,
            )

    async def list(
        self, *, page: int, page_size: int
    ) -> tuple[list[StaffInvitationData], int]:
        statement = (
            select(StaffInvitation)
            .order_by(StaffInvitation.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = tuple((await self._session.scalars(statement)).all())
        total = int(
            (await self._session.scalar(select(func.count(StaffInvitation.id)))) or 0
        )
        now = self._clock()
        return [self._to_data(row, now=now) for row in rows], total

    async def _validate_target(
        self, *, email: str, role_code: str, organization_id: UUID | None
    ) -> User | None:
        user = await self._auth.get_user_by_email(email)
        role = await self._auth.get_role_by_code(role_code)
        if role is None or role_code not in INTERNAL_MANAGED_ROLES:
            raise DomainError(
                code="STAFF_ROLE_NOT_FOUND",
                message="The requested internal function is not configured.",
                status_code=409,
            )
        if organization_id is not None:
            organization = await self._session.get(Organization, organization_id)
            if organization is None:
                raise DomainError(
                    code="STAFF_ORGANIZATION_NOT_FOUND",
                    message="The selected organization was not found.",
                    status_code=404,
                )
        if user is not None:
            roles = set(await self._auth.get_role_codes(user.id))
            if user.status is not UserStatus.ACTIVE or user.email_verified_at is None:
                raise DomainError(
                    code="STAFF_INVITATION_TARGET_INELIGIBLE",
                    message="Only active, verified accounts can be invited.",
                    status_code=409,
                )
            if "SUPER_ADMIN" in roles or role_code in roles:
                raise DomainError(
                    code="STAFF_INVITATION_TARGET_ALREADY_PRIVILEGED",
                    message="This account already has an equal or higher role.",
                    status_code=409,
                )
        return user

    def _new_invitation(
        self,
        *,
        email: str,
        role_code: str,
        organization_id: UUID | None,
        created_by_user_id: UUID,
        now: datetime,
    ) -> tuple[StaffInvitation, str]:
        raw_token = secrets.token_urlsafe(32)
        return (
            StaffInvitation(
                email=email,
                role_code=role_code,
                organization_id=organization_id,
                token_hash=hash_verification_token(raw_token),
                expires_at=now + self._invitation_ttl,
                created_by_user_id=created_by_user_id,
            ),
            raw_token,
        )

    def _enqueue(
        self, invitation: StaffInvitation, *, raw_token: str, now: datetime
    ) -> None:
        encrypted = self._payload_cipher.encrypt(
            {
                "email": invitation.email,
                "invitation_id": str(invitation.id),
                "invitation_token": raw_token,
                "role": invitation.role_code,
            },
            event_type=STAFF_INVITATION_EVENT,
            aggregate_id=invitation.id,
        )
        self._outbox.add(
            OutboxEvent(
                event_type=STAFF_INVITATION_EVENT,
                aggregate_type="staff_invitation",
                aggregate_id=invitation.id,
                payload_ciphertext=encrypted.ciphertext,
                payload_nonce=encrypted.nonce,
                key_id=encrypted.key_id,
                occurred_at=now,
            )
        )

    async def _cancel_pending_delivery(
        self, invitation_id: UUID, *, now: datetime
    ) -> None:
        await self._session.execute(
            update(OutboxEvent)
            .where(
                OutboxEvent.event_type == STAFF_INVITATION_EVENT,
                OutboxEvent.aggregate_id == invitation_id,
                OutboxEvent.processed_at.is_(None),
            )
            .values(processed_at=now)
        )

    async def _resolve_recipient_notification(
        self,
        *,
        invitation: StaffInvitation,
        user_id: UUID,
        decision: str,
        now: datetime,
    ) -> None:
        notification = await self._session.scalar(
            select(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.source_event_id == invitation.id,
            )
            .with_for_update()
        )
        if notification is not None:
            notification.data_json = {
                **notification.data_json,
                "decision": decision,
            }
            notification.read_at = now

    async def _locked(self, invitation_id: UUID) -> StaffInvitation:
        invitation = await self._session.scalar(
            select(StaffInvitation)
            .where(StaffInvitation.id == invitation_id)
            .with_for_update()
        )
        if invitation is None:
            raise DomainError(
                code="STAFF_INVITATION_NOT_FOUND",
                message="The invitation was not found.",
                status_code=404,
            )
        return invitation

    def _require_pending(
        self, invitation: StaffInvitation | None, *, now: datetime
    ) -> None:
        if (
            invitation is None
            or invitation.accepted_at is not None
            or invitation.revoked_at is not None
            or self._as_utc(invitation.expires_at) <= now
        ):
            raise self._invalid()

    @staticmethod
    def _require_admin(principal: AuthPrincipal) -> None:
        AuthorizationPolicy.require_capability(
            principal,
            StaffInvitationService.MANAGE_STAFF,
            lambda: DomainError(
                code="STAFF_INVITATION_FORBIDDEN",
                message="Staff invitation management is forbidden.",
                status_code=403,
            ),
        )

    def _to_data(
        self, invitation: StaffInvitation, *, now: datetime
    ) -> StaffInvitationData:
        status: StaffInvitationStatus = "PENDING"
        if invitation.accepted_at is not None:
            status = "ACCEPTED"
        elif invitation.revoked_at is not None:
            status = "REVOKED"
        elif self._as_utc(invitation.expires_at) <= now:
            status = "EXPIRED"
        return StaffInvitationData(
            id=invitation.id,
            email=invitation.email,
            role=invitation.role_code,
            organizationId=invitation.organization_id,
            status=status,
            expiresAt=invitation.expires_at,
            createdAt=invitation.created_at,
        )

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @staticmethod
    def _invalid() -> DomainError:
        return DomainError(
            code="STAFF_INVITATION_INVALID",
            message="The invitation is invalid or has expired.",
            status_code=400,
        )


__all__ = ["STAFF_INVITATION_EVENT", "StaffInvitationService"]
