import logging
import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.outbox import OutboxEvent
from app.modules.auth.errors import InvalidPasswordResetTokenError
from app.modules.auth.models import UserStatus, VerificationToken
from app.modules.auth.rate_limit import RegistrationRateLimiter
from app.modules.auth.repositories import AuthRepository, OutboxRepository
from app.modules.auth.security import (
    Argon2PasswordHasher,
    OutboxPayloadCipher,
    hash_verification_token,
)

logger = logging.getLogger(__name__)

PASSWORD_RESET_PURPOSE = "PASSWORD_RESET"
PASSWORD_RESET_REQUESTED_EVENT = "user.password_reset_requested"


class PasswordResetService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        password_hasher: Argon2PasswordHasher,
        payload_cipher: OutboxPayloadCipher,
        rate_limiter: RegistrationRateLimiter,
        reset_ttl: timedelta,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session = session
        self._auth_repository = AuthRepository(session)
        self._outbox_repository = OutboxRepository(session)
        self._password_hasher = password_hasher
        self._payload_cipher = payload_cipher
        self._rate_limiter = rate_limiter
        self._reset_ttl = reset_ttl
        self._clock = clock or (lambda: datetime.now(UTC))

    async def request_reset(
        self,
        *,
        email: str,
        client_ip: str,
    ) -> None:
        normalized_email = email.strip().lower()
        await self._rate_limiter.check(
            email=normalized_email,
            client_ip=client_ip,
        )
        raw_token = secrets.token_urlsafe(32)
        token_hash = hash_verification_token(raw_token)
        now = self._clock()

        async with self._session.begin():
            user = await self._auth_repository.get_user_by_email(normalized_email)
            if (
                user is None
                or user.status is not UserStatus.ACTIVE
                or user.email_verified_at is None
            ):
                return

            previous_tokens = (
                await self._auth_repository.list_unconsumed_verification_tokens(
                    user_id=user.id,
                    purpose=PASSWORD_RESET_PURPOSE,
                    for_update=True,
                )
            )
            for previous_token in previous_tokens:
                previous_token.consumed_at = now

            self._auth_repository.add_verification_token(
                VerificationToken(
                    user_id=user.id,
                    purpose=PASSWORD_RESET_PURPOSE,
                    token_hash=token_hash,
                    expires_at=now + self._reset_ttl,
                )
            )
            encrypted = self._payload_cipher.encrypt(
                {
                    "email": normalized_email,
                    "reset_token": raw_token,
                    "user_id": str(user.id),
                },
                event_type=PASSWORD_RESET_REQUESTED_EVENT,
                aggregate_id=user.id,
            )
            self._outbox_repository.add(
                OutboxEvent(
                    event_type=PASSWORD_RESET_REQUESTED_EVENT,
                    aggregate_type="user",
                    aggregate_id=user.id,
                    payload_ciphertext=encrypted.ciphertext,
                    payload_nonce=encrypted.nonce,
                    key_id=encrypted.key_id,
                    occurred_at=now,
                )
            )

        logger.info(
            "security_audit",
            extra={
                "action": "auth.password_reset.requested",
                "user_id": str(user.id),
            },
        )

    async def reset_password(self, *, token: str, new_password: str) -> None:
        now = self._clock()
        user_id: object | None = None
        async with self._session.begin():
            verification = (
                await self._auth_repository.get_verification_token_for_update(
                    token_hash=hash_verification_token(token),
                    purpose=PASSWORD_RESET_PURPOSE,
                )
            )
            if (
                verification is None
                or verification.consumed_at is not None
                or self._as_utc(verification.expires_at) <= now
            ):
                raise InvalidPasswordResetTokenError()

            user = await self._auth_repository.get_user_by_id(verification.user_id)
            if user is None or user.status is not UserStatus.ACTIVE:
                raise InvalidPasswordResetTokenError()

            user.password_hash = await self._password_hasher.hash(new_password)
            outstanding_tokens = (
                await self._auth_repository.list_unconsumed_verification_tokens(
                    user_id=user.id,
                    purpose=PASSWORD_RESET_PURPOSE,
                    for_update=True,
                )
            )
            for outstanding_token in outstanding_tokens:
                outstanding_token.consumed_at = now

            active_sessions = await self._auth_repository.list_active_auth_sessions(
                user_id=user.id,
                now=now,
                for_update=True,
            )
            for auth_session in active_sessions:
                auth_session.revoked_at = now
            user_id = user.id

        logger.info(
            "security_audit",
            extra={
                "action": "auth.password_reset.completed",
                "user_id": str(user_id),
            },
        )

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    async def close(self) -> None:
        await self._session.close()
