import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID

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
from app.modules.auth.roles import (
    USER_REGISTRATION_ROLE,
    VIEWER_REGISTRATION_ROLE,
)
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
        auto_create_affiliate_profiles: bool = False,
        affiliate_enabled: bool = False,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session = session
        self._auth_repository = AuthRepository(session)
        self._outbox_repository = OutboxRepository(session)
        self._password_hasher = password_hasher
        self._payload_cipher = payload_cipher
        self._rate_limiter = rate_limiter
        self._verification_ttl = verification_ttl
        self._affiliate_profile_auto_create = auto_create_affiliate_profiles
        self._affiliate_enabled = affiliate_enabled
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
        referral_code: str | None = None,
        referral_click_id: UUID | None = None,
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
                user = await self._persist_registration(
                    email=normalized_email,
                    password_hash=password_hash,
                    account_type=account_type,
                )
                if self._affiliate_enabled and referral_code:
                    await self._capture_signup_referral(
                        user_id=user.id,
                        referral_code=referral_code,
                        click_id=referral_click_id,
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
    ) -> User:
        now = self._clock()
        user = User(
            email=email,
            password_hash=password_hash,
            status=UserStatus.PENDING,
            account_type=account_type,
        )
        self._auth_repository.add_user(user)
        await self._session.flush()

        role_code = (
            VIEWER_REGISTRATION_ROLE
            if account_type is AccountType.PUBLIC_USER
            else USER_REGISTRATION_ROLE
        )
        role = await self._auth_repository.get_role_by_code(role_code)
        if role is None:
            role = Role(code=role_code)
            self._auth_repository.add_role(role)
            await self._session.flush()
        self._auth_repository.add_user_role(UserRole(user_id=user.id, role_id=role.id))

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
        return user

    async def _capture_signup_referral(
        self, *, user_id: UUID, referral_code: str, click_id: UUID | None
    ) -> None:
        from app.core.errors import DomainError
        from app.modules.affiliate.service import AffiliateService

        try:
            await AffiliateService(
                self._session,
                affiliate_enabled=self._affiliate_enabled,
                clock=self._clock,
            ).capture_signup_referral_in_current_transaction(
                referred_user_id=user_id,
                referral_code=referral_code,
                click_id=click_id,
            )
        except DomainError as exc:
            # Invalid/expired referral data must not prevent account registration.
            if exc.status_code >= 500:
                raise

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
            if self._affiliate_profile_auto_create:
                role_codes = await self._auth_repository.get_role_codes(user.id)
                if set(role_codes) == {"USER"}:
                    await self._ensure_affiliate_profile(user.id)

    async def _ensure_affiliate_profile(self, user_id: UUID) -> None:
        from app.core.errors import DomainError
        from app.modules.affiliate.service import AffiliateService

        try:
            await AffiliateService(self._session).ensure_profile_in_current_transaction(
                user_id,
                allow_pending=False,
            )
        except DomainError as exc:
            if exc.status_code != 403:
                raise

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
