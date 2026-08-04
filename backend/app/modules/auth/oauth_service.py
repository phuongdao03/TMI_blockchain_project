import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol, TypeGuard
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.errors import (
    OAuthAccountLinkRequiredError,
    OAuthIdentityInvalidError,
)
from app.modules.auth.models import (
    AccountType,
    AuthIdentity,
    AuthProvider,
    Role,
    User,
    UserRole,
    UserStatus,
)
from app.modules.auth.oauth import (
    OAuthAttempt,
    OAuthAttemptRateLimiter,
    OAuthStateStore,
)
from app.modules.auth.oauth_provider import GoogleOIDCClaims, GoogleOIDCProvider
from app.modules.auth.repositories import AuthRepository
from app.modules.auth.roles import PUBLIC_REGISTRATION_ROLE
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


@dataclass(frozen=True, slots=True)
class OAuthRuntime:
    account_service: "OAuthService"
    state_store: OAuthStateStore
    rate_limiter: OAuthAttemptRateLimiter
    provider: GoogleOIDCProvider


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
        claims: GoogleOIDCClaims,
        attempt: OAuthAttempt,
        metadata: ClientMetadata,
    ) -> OAuthCompletion:
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
                "provider": AuthProvider.GOOGLE.value,
            },
        )
        return OAuthCompletion(user_id=user.id, issued=issued)

    async def _resolve_user(
        self,
        *,
        claims: GoogleOIDCClaims,
        account_type: AccountType,
        attempt: OAuthAttempt,
        now: datetime,
    ) -> tuple[User, str]:
        identity = await self._repository.get_identity(
            provider=AuthProvider.GOOGLE,
            subject=claims.subject,
        )

        if attempt.purpose == "link":
            user = await self._linked_user(attempt.user_id)
            if identity is not None and identity.user_id != user.id:
                raise OAuthIdentityInvalidError()
            existing_for_user = await self._repository.get_identity_for_user(
                user_id=user.id,
                provider=AuthProvider.GOOGLE,
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
                        provider=AuthProvider.GOOGLE,
                        provider_subject=claims.subject,
                        last_login_at=now,
                    )
                )
            else:
                identity.last_login_at = now
            return user, "auth.oauth.identity.linked"

        if identity is not None:
            identity_user = await self._repository.get_user_by_id(identity.user_id)
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
        if account_type is not AccountType.PUBLIC_USER:
            role = await self._repository.get_role_by_code(PUBLIC_REGISTRATION_ROLE)
            if role is None:
                role = Role(code=PUBLIC_REGISTRATION_ROLE)
                self._repository.add_role(role)
                await self._session.flush()
            self._repository.add_user_role(UserRole(user_id=user.id, role_id=role.id))
        self._repository.add_identity(
            AuthIdentity(
                user_id=user.id,
                provider=AuthProvider.GOOGLE,
                provider_subject=claims.subject,
                last_login_at=now,
            )
        )
        return user, "auth.oauth.signup.succeeded"

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
    "OAuthRuntime",
    "OAuthService",
    "OAuthSessionIssuer",
]
