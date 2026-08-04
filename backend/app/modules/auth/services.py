import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.outbox import OutboxEvent
from app.modules.auth.errors import (
    InvalidVerificationTokenError,
    RateLimitExceededError,
)
from app.modules.auth.models import (
    AccountType,
    Role,
    User,
    UserRole,
    UserStatus,
    VerificationToken,
)
from app.modules.auth.rate_limit import RegistrationRateLimiter
from app.modules.auth.repositories import AuthRepository, OutboxRepository
from app.modules.auth.roles import PUBLIC_REGISTRATION_ROLE
from app.modules.auth.security import (
    Argon2PasswordHasher,
    OutboxPayloadCipher,
    hash_verification_token,
)

EMAIL_VERIFICATION_PURPOSE = "EMAIL_VERIFICATION"
USER_REGISTERED_EVENT = "user.registered"


class RegistrationService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        password_hasher: Argon2PasswordHasher,
        payload_cipher: OutboxPayloadCipher,
        rate_limiter: RegistrationRateLimiter,
        verification_ttl: timedelta,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session = session
        self._auth_repository = AuthRepository(session)
        self._outbox_repository = OutboxRepository(session)
        self._password_hasher = password_hasher
        self._payload_cipher = payload_cipher
        self._rate_limiter = rate_limiter
        self._verification_ttl = verification_ttl
        self._clock = clock or (lambda: datetime.now(UTC))

    @staticmethod
    def _normalize_email(email: str) -> str:
        return email.strip().lower()

    async def register(
        self,
        *,
        email: str,
        password: str,
        client_ip: str,
        account_type: AccountType = AccountType.INDIVIDUAL_APPLICANT,
    ) -> None:
        normalized_email = self._normalize_email(email)
        await self._rate_limiter.check(
            email=normalized_email,
            client_ip=client_ip,
        )

        # Hash before the lookup so existing and new addresses have similar timing.
        password_hash = await self._password_hasher.hash(password)

        try:
            async with self._session.begin():
                if (
                    await self._auth_repository.get_user_by_email(normalized_email)
                    is not None
                ):
                    return
                await self._persist_registration(
                    email=normalized_email,
                    password_hash=password_hash,
                    account_type=account_type,
                )
        except IntegrityError:
            await self._session.rollback()
            async with self._session.begin():
                existing_user = await self._auth_repository.get_user_by_email(
                    normalized_email
                )
            if existing_user is None:
                raise

    async def _persist_registration(
        self,
        *,
        email: str,
        password_hash: str,
        account_type: AccountType,
    ) -> None:
        now = self._clock()
        user = User(
            email=email,
            password_hash=password_hash,
            status=UserStatus.PENDING,
            account_type=account_type,
        )
        self._auth_repository.add_user(user)
        await self._session.flush()

        if account_type is not AccountType.PUBLIC_USER:
            applicant_role = await self._auth_repository.get_role_by_code(
                PUBLIC_REGISTRATION_ROLE
            )
            if applicant_role is None:
                applicant_role = Role(code=PUBLIC_REGISTRATION_ROLE)
                self._auth_repository.add_role(applicant_role)
                await self._session.flush()
            self._auth_repository.add_user_role(
                UserRole(user_id=user.id, role_id=applicant_role.id)
            )

        raw_token = secrets.token_urlsafe(32)
        self._auth_repository.add_verification_token(
            VerificationToken(
                user_id=user.id,
                purpose=EMAIL_VERIFICATION_PURPOSE,
                token_hash=hash_verification_token(raw_token),
                expires_at=now + self._verification_ttl,
            )
        )

        encrypted = self._payload_cipher.encrypt(
            {
                "email": email,
                "user_id": str(user.id),
                "account_type": account_type.value,
                "verification_token": raw_token,
            },
            event_type=USER_REGISTERED_EVENT,
            aggregate_id=user.id,
        )
        self._outbox_repository.add(
            OutboxEvent(
                event_type=USER_REGISTERED_EVENT,
                aggregate_type="user",
                aggregate_id=user.id,
                payload_ciphertext=encrypted.ciphertext,
                payload_nonce=encrypted.nonce,
                key_id=encrypted.key_id,
                occurred_at=now,
            )
        )

    async def verify_email(self, token: str) -> None:
        now = self._clock()
        async with self._session.begin():
            verification = (
                await self._auth_repository.get_verification_token_for_update(
                    token_hash=hash_verification_token(token),
                    purpose=EMAIL_VERIFICATION_PURPOSE,
                )
            )
            if (
                verification is None
                or verification.consumed_at is not None
                or self._as_utc(verification.expires_at) <= now
            ):
                raise InvalidVerificationTokenError()

            user = await self._auth_repository.get_user_by_id(verification.user_id)
            if user is None:
                raise InvalidVerificationTokenError()

            verification.consumed_at = now
            user.email_verified_at = now
            user.status = UserStatus.ACTIVE

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    async def close(self) -> None:
        await self._session.close()


__all__ = [
    "InvalidVerificationTokenError",
    "RateLimitExceededError",
    "RegistrationService",
]
