import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol, TypeGuard
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.modules.audit.service import AuditService
from app.modules.auth.errors import (
    OAuthAccountLinkRequiredError,
    OAuthIdentityInvalidError,
)
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
from app.modules.auth.repositories import AuthRepository
from app.modules.auth.roles import (
    USER_REGISTRATION_ROLE,
    VIEWER_REGISTRATION_ROLE,
)
from app.modules.auth.schemas import INTERNAL_MANAGED_ROLES
from app.modules.auth.session_service import ClientMetadata, IssuedSession

logger = logging.getLogger(__name__)


class OAuthSessionIssuer(Protocol):
    async def issue_for_user(
        self,
        *,
        user_id: UUID,
        metadata: ClientMetadata,
    ) -> IssuedSession: ...


@dataclass(frozen=True, slots=True)
class OAuthCompletion:
    user_id: UUID
    issued: IssuedSession


class OAuthService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        session_issuer: OAuthSessionIssuer,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session = session
        self._repository = AuthRepository(session)
        self._session_issuer = session_issuer
        self._clock = clock or (lambda: datetime.now(UTC))

    async def complete(
        self,
        *,
        claims: FirebaseClaims,
        attempt: OAuthAttempt,
        metadata: ClientMetadata,
    ) -> OAuthCompletion:
        provider = AuthProvider.FIREBASE
        try:
            account_type = AccountType(attempt.account_type)
        except ValueError as exc:
            raise OAuthIdentityInvalidError() from exc
        if attempt.purpose not in {"login", "link"}:
            raise OAuthIdentityInvalidError()
        if (attempt.purpose == "link") != (attempt.user_id is not None):
            raise OAuthIdentityInvalidError()

        now = self._clock()
        user: User
        event: str
        try:
            async with self._session.begin():
                user, event = await self._resolve_user(
                    claims=claims,
                    account_type=account_type,
                    attempt=attempt,
                    now=now,
                    provider=provider,
                )
                user.last_login_at = now
        except OAuthAccountLinkRequiredError:
            logger.info(
                "security_audit",
                extra={"action": "auth.oauth.account_link_required"},
            )
            raise
        except IntegrityError as exc:
            await self._session.rollback()
            raise OAuthAccountLinkRequiredError() from exc

        issued = await self._session_issuer.issue_for_user(
            user_id=user.id,
            metadata=metadata,
        )
        logger.info(
            "security_audit",
            extra={
                "action": event,
                "user_id": str(user.id),
                "provider": provider.value,
            },
        )
        return OAuthCompletion(user_id=user.id, issued=issued)

    async def _resolve_user(
        self,
        *,
        claims: FirebaseClaims,
        account_type: AccountType,
        attempt: OAuthAttempt,
        now: datetime,
        provider: AuthProvider,
    ) -> tuple[User, str]:
        identity = await self._repository.get_identity(
            provider=provider,
            subject=claims.subject,
        )

        if attempt.purpose == "link":
            user = await self._linked_user(attempt.user_id)
            if identity is not None and identity.user_id != user.id:
                raise OAuthIdentityInvalidError()
            existing_for_user = await self._repository.get_identity_for_user(
                user_id=user.id,
                provider=provider,
            )
            if (
                existing_for_user is not None
                and existing_for_user.provider_subject != claims.subject
            ):
                raise OAuthIdentityInvalidError()
            if identity is None:
                self._repository.add_identity(
                    AuthIdentity(
                        user_id=user.id,
                        provider=provider,
                        provider_subject=claims.subject,
                        last_login_at=now,
                    )
                )
            else:
                identity.last_login_at = now
            return user, "auth.oauth.identity.linked"

        if identity is not None:
            identity_user = await self._repository.get_user_by_id(identity.user_id)
            if identity_user is not None:
                await self._activate_pending_staff(
                    identity_user,
                    claims=claims,
                    now=now,
                )
            if not self._is_active(identity_user):
                raise OAuthIdentityInvalidError()
            identity.last_login_at = now
            return identity_user, "auth.oauth.login.succeeded"

        existing_user = await self._repository.get_user_by_email(claims.email)
        if existing_user is not None:
            raise OAuthAccountLinkRequiredError()

        user = User(
            email=claims.email,
            password_hash=None,
            status=UserStatus.ACTIVE,
            email_verified_at=now,
            account_type=account_type,
        )
        self._repository.add_user(user)
        await self._session.flush()
        role_code = (
            VIEWER_REGISTRATION_ROLE
            if account_type is AccountType.PUBLIC_USER
            else USER_REGISTRATION_ROLE
        )
        role = await self._repository.get_role_by_code(role_code)
        if role is None:
            role = Role(code=role_code)
            self._repository.add_role(role)
            await self._session.flush()
        self._repository.add_user_role(UserRole(user_id=user.id, role_id=role.id))
        self._repository.add_identity(
            AuthIdentity(
                user_id=user.id,
                provider=provider,
                provider_subject=claims.subject,
                last_login_at=now,
            )
        )
        return user, "auth.oauth.signup.succeeded"

    async def _activate_pending_staff(
        self,
        user: User,
        *,
        claims: FirebaseClaims,
        now: datetime,
    ) -> None:
        if user.status is not UserStatus.PENDING:
            return
        roles = await self._repository.get_role_codes(user.id)
        if not set(roles).intersection(INTERNAL_MANAGED_ROLES | {"SUPER_ADMIN"}):
            return
        if not claims.email_verified or user.email.lower() != claims.email.lower():
            raise DomainError(
                code="OAUTH_IDENTITY_INVALID",
                message="The verified staff identity does not match the invitation.",
                status_code=403,
            )
        user.status = UserStatus.ACTIVE
        AuditService(self._session).record(
            actor_user_id=user.id,
            action="auth.staff_account.activated",
            resource_type="user",
            resource_id=str(user.id),
            before={"status": UserStatus.PENDING.value},
            after={"status": UserStatus.ACTIVE.value},
        )

    async def _linked_user(self, raw_user_id: str | None) -> User:
        if raw_user_id is None:
            raise OAuthIdentityInvalidError()
        try:
            user_id = UUID(raw_user_id)
        except ValueError as exc:
            raise OAuthIdentityInvalidError() from exc
        user = await self._repository.get_user_by_id(user_id)
        if not self._is_active(user):
            raise OAuthIdentityInvalidError()
        return user

    @staticmethod
    def _is_active(user: User | None) -> TypeGuard[User]:
        return (
            user is not None
            and user.status is UserStatus.ACTIVE
            and user.email_verified_at is not None
        )


__all__ = [
    "OAuthCompletion",
    "OAuthService",
    "OAuthSessionIssuer",
]
