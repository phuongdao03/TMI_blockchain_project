import logging
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.errors import (
    AuthSessionNotFoundError,
    CsrfValidationError,
    InvalidCredentialsError,
    UnauthenticatedError,
)
from app.modules.auth.models import AccountType, AuthSession, UserStatus
from app.modules.auth.rate_limit import RegistrationRateLimiter
from app.modules.auth.repositories import AuthRepository
from app.modules.auth.security import Argon2PasswordHasher
from app.modules.auth.tokens import (
    AccessTokenManager,
    CsrfTokenManager,
    InvalidAccessTokenError,
    hash_ip_address,
    hash_opaque_token,
    new_opaque_token,
)

logger = logging.getLogger(__name__)

DUMMY_PASSWORD_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$eayLhPLyNdl5Amv2daXufQ"
    "$yXiRZIKlgiTaRf1D+d+N7L8VbGg/OXqcXXLZUE1Sv4Y"
)


@dataclass(frozen=True, slots=True)
class ClientMetadata:
    client_ip: str
    user_agent: str | None
    device_name: str | None


@dataclass(frozen=True, slots=True)
class IssuedSession:
    access_token: str
    refresh_token: str
    csrf_token: str


@dataclass(frozen=True, slots=True)
class AuthPrincipal:
    user_id: UUID
    session_id: UUID
    email: str
    roles: tuple[str, ...]
    account_type: AccountType | None = None
    permissions: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SessionView:
    id: UUID
    device_name: str | None
    user_agent: str | None
    created_at: datetime
    expires_at: datetime
    is_current: bool


class SessionService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        password_hasher: Argon2PasswordHasher,
        access_tokens: AccessTokenManager,
        csrf_tokens: CsrfTokenManager,
        rate_limiter: RegistrationRateLimiter,
        refresh_ttl: timedelta,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session = session
        self._repository = AuthRepository(session)
        self._password_hasher = password_hasher
        self._access_tokens = access_tokens
        self._csrf_tokens = csrf_tokens
        self._rate_limiter = rate_limiter
        self._refresh_ttl = refresh_ttl
        self._clock = clock or (lambda: datetime.now(UTC))

    async def login(
        self,
        *,
        email: str,
        password: str,
        metadata: ClientMetadata,
    ) -> IssuedSession:
        normalized_email = email.strip().lower()
        await self._rate_limiter.check(
            email=normalized_email,
            client_ip=metadata.client_ip,
        )

        async with self._session.begin():
            user = await self._repository.get_user_by_email(normalized_email)
            candidate_hash = (
                user.password_hash
                if user is not None and user.password_hash is not None
                else DUMMY_PASSWORD_HASH
            )
            password_is_valid = await self._password_hasher.verify(
                candidate_hash,
                password,
            )
            if (
                user is None
                or user.password_hash is None
                or not password_is_valid
                or user.status is not UserStatus.ACTIVE
                or user.email_verified_at is None
            ):
                logger.warning(
                    "security_audit",
                    extra={
                        "action": "auth.login.failed",
                        "user_id": str(user.id) if user is not None else None,
                    },
                )
                raise InvalidCredentialsError()

            if self._password_hasher.needs_rehash(user.password_hash):
                user.password_hash = await self._password_hasher.hash(password)

            now = self._clock()
            refresh_token = new_opaque_token()
            auth_session = AuthSession(
                user_id=user.id,
                refresh_token_hash=hash_opaque_token(refresh_token),
                device_name=self._limited(metadata.device_name, 255),
                ip_hash=hash_ip_address(metadata.client_ip),
                user_agent=self._limited(metadata.user_agent, 1024),
                expires_at=now + self._refresh_ttl,
            )
            self._repository.add_auth_session(auth_session)
            user.last_login_at = now
            await self._session.flush()

            access_token = self._access_tokens.issue(
                user_id=user.id,
                session_id=auth_session.id,
            )
            csrf_token = self._csrf_tokens.issue(auth_session.id)

        logger.info(
            "security_audit",
            extra={"action": "auth.login.succeeded", "user_id": str(user.id)},
        )
        return IssuedSession(
            access_token=access_token,
            refresh_token=refresh_token,
            csrf_token=csrf_token,
        )

    async def issue_for_user(
        self,
        *,
        user_id: UUID,
        metadata: ClientMetadata,
    ) -> IssuedSession:
        now = self._clock()
        async with self._session.begin():
            user = await self._repository.get_user_by_id(user_id)
            if (
                user is None
                or user.status is not UserStatus.ACTIVE
                or user.email_verified_at is None
            ):
                raise UnauthenticatedError()
            issued = await self._create_session(
                user_id=user.id,
                metadata=metadata,
                rotated_from_id=None,
                now=now,
            )
        logger.info(
            "security_audit",
            extra={"action": "auth.oauth.session.issued", "user_id": str(user_id)},
        )
        return issued

    async def refresh(
        self,
        *,
        refresh_token: str,
        csrf_cookie: str | None,
        csrf_header: str | None,
        metadata: ClientMetadata,
    ) -> IssuedSession:
        now = self._clock()
        reuse_detected = False
        issued: IssuedSession | None = None
        user_id: UUID | None = None

        async with self._session.begin():
            previous = await self._repository.get_auth_session_by_refresh_hash(
                hash_opaque_token(refresh_token),
                for_update=True,
            )
            if previous is None:
                raise UnauthenticatedError()
            self._require_csrf(
                session_id=previous.id,
                csrf_cookie=csrf_cookie,
                csrf_header=csrf_header,
            )
            user_id = previous.user_id

            if previous.revoked_at is not None:
                active_sessions = await self._repository.list_active_auth_sessions(
                    user_id=previous.user_id,
                    now=now,
                    for_update=True,
                )
                for active_session in active_sessions:
                    active_session.revoked_at = now
                reuse_detected = True
            elif self._as_utc(previous.expires_at) <= now:
                raise UnauthenticatedError()
            else:
                previous.revoked_at = now
                issued = await self._create_session(
                    user_id=previous.user_id,
                    metadata=metadata,
                    rotated_from_id=previous.id,
                    now=now,
                )

        if reuse_detected:
            logger.warning(
                "security_audit",
                extra={
                    "action": "auth.refresh.reuse_detected",
                    "user_id": str(user_id),
                },
            )
            raise UnauthenticatedError()
        if issued is None:
            raise RuntimeError("Refresh rotation did not issue a session.")

        logger.info(
            "security_audit",
            extra={"action": "auth.refresh.rotated", "user_id": str(user_id)},
        )
        return issued

    async def logout(
        self,
        *,
        refresh_token: str,
        csrf_cookie: str | None,
        csrf_header: str | None,
    ) -> None:
        now = self._clock()
        user_id: UUID | None = None
        async with self._session.begin():
            auth_session = await self._repository.get_auth_session_by_refresh_hash(
                hash_opaque_token(refresh_token),
                for_update=True,
            )
            if auth_session is None:
                raise UnauthenticatedError()
            self._require_csrf(
                session_id=auth_session.id,
                csrf_cookie=csrf_cookie,
                csrf_header=csrf_header,
            )
            user_id = auth_session.user_id
            if auth_session.revoked_at is None:
                auth_session.revoked_at = now

        logger.info(
            "security_audit",
            extra={"action": "auth.session.logged_out", "user_id": str(user_id)},
        )

    async def list_sessions(
        self,
        principal: AuthPrincipal,
    ) -> tuple[SessionView, ...]:
        async with self._session.begin():
            sessions = await self._repository.list_active_auth_sessions(
                user_id=principal.user_id,
                now=self._clock(),
            )
        return tuple(
            SessionView(
                id=auth_session.id,
                device_name=auth_session.device_name,
                user_agent=auth_session.user_agent,
                created_at=auth_session.created_at,
                expires_at=auth_session.expires_at,
                is_current=auth_session.id == principal.session_id,
            )
            for auth_session in sessions
        )

    async def revoke_session(
        self,
        *,
        principal: AuthPrincipal,
        target_session_id: UUID,
        csrf_cookie: str | None,
        csrf_header: str | None,
    ) -> None:
        now = self._clock()
        async with self._session.begin():
            current_session = await self._repository.get_auth_session(
                principal.session_id
            )
            if current_session is None:
                raise UnauthenticatedError()
            self._require_csrf(
                session_id=current_session.id,
                csrf_cookie=csrf_cookie,
                csrf_header=csrf_header,
            )
            target = await self._repository.get_owned_auth_session(
                user_id=principal.user_id,
                session_id=target_session_id,
                for_update=True,
            )
            if target is None:
                raise AuthSessionNotFoundError()
            if target.revoked_at is None:
                target.revoked_at = now

        logger.info(
            "security_audit",
            extra={
                "action": "auth.session.revoked",
                "user_id": str(principal.user_id),
            },
        )

    async def authenticate_access(self, access_token: str) -> AuthPrincipal:
        try:
            identity = self._access_tokens.decode(access_token)
        except InvalidAccessTokenError as exc:
            raise UnauthenticatedError() from exc

        async with self._session.begin():
            user = await self._repository.get_user_by_id(identity.user_id)
            auth_session = await self._repository.get_auth_session(identity.session_id)
            now = self._clock()
            if (
                user is None
                or user.status is not UserStatus.ACTIVE
                or user.email_verified_at is None
                or auth_session is None
                or auth_session.user_id != user.id
                or auth_session.revoked_at is not None
                or self._as_utc(auth_session.expires_at) <= now
            ):
                raise UnauthenticatedError()
            roles = await self._repository.get_role_codes(user.id)
            permissions = await self._repository.get_permission_codes(user.id)

        return AuthPrincipal(
            user_id=user.id,
            session_id=auth_session.id,
            email=user.email,
            roles=roles,
            account_type=user.account_type,
            permissions=permissions,
        )

    async def _create_session(
        self,
        *,
        user_id: UUID,
        metadata: ClientMetadata,
        rotated_from_id: UUID | None,
        now: datetime,
    ) -> IssuedSession:
        refresh_token = new_opaque_token()
        auth_session = AuthSession(
            user_id=user_id,
            refresh_token_hash=hash_opaque_token(refresh_token),
            device_name=self._limited(metadata.device_name, 255),
            ip_hash=hash_ip_address(metadata.client_ip),
            user_agent=self._limited(metadata.user_agent, 1024),
            expires_at=now + self._refresh_ttl,
            rotated_from_id=rotated_from_id,
        )
        self._repository.add_auth_session(auth_session)
        await self._session.flush()
        return IssuedSession(
            access_token=self._access_tokens.issue(
                user_id=user_id,
                session_id=auth_session.id,
            ),
            refresh_token=refresh_token,
            csrf_token=self._csrf_tokens.issue(auth_session.id),
        )

    def _require_csrf(
        self,
        *,
        session_id: UUID,
        csrf_cookie: str | None,
        csrf_header: str | None,
    ) -> None:
        if (
            csrf_cookie is None
            or csrf_header is None
            or not secrets.compare_digest(csrf_cookie, csrf_header)
            or not self._csrf_tokens.verify(csrf_cookie, session_id)
        ):
            raise CsrfValidationError()

    @staticmethod
    def _limited(value: str | None, maximum: int) -> str | None:
        return value[:maximum] if value is not None else None

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    async def close(self) -> None:
        await self._session.close()


__all__ = [
    "ClientMetadata",
    "InvalidCredentialsError",
    "SessionService",
    "UnauthenticatedError",
]
