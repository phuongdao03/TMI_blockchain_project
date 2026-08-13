import secrets
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import timedelta
from typing import Annotated

from fastapi import Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.modules.auth.errors import (
    CsrfValidationError,
    OAuthProviderUnavailableError,
    UnauthenticatedError,
)
from app.modules.auth.firebase_provider import FirebaseTokenVerifier
from app.modules.auth.oauth import RedisOAuthRateLimiter
from app.modules.auth.oauth_service import OAuthService
from app.modules.auth.onboarding import ApplicantUpgradeService
from app.modules.auth.password_reset_service import PasswordResetService
from app.modules.auth.rate_limit import (
    RedisAuthRateLimiter,
    RedisRegistrationRateLimiter,
)
from app.modules.auth.security import Argon2PasswordHasher, OutboxPayloadCipher
from app.modules.auth.services import RegistrationService
from app.modules.auth.session_service import AuthPrincipal, SessionService
from app.modules.auth.staff_invitation_service import StaffInvitationService
from app.modules.auth.staff_mfa import StaffMfaPolicy
from app.modules.auth.tokens import AccessTokenManager, CsrfTokenManager

SessionDependency = Annotated[AsyncSession, Depends(get_session)]
SettingsDependency = Annotated[Settings, Depends(get_settings)]


@dataclass(frozen=True, slots=True)
class FirebaseAuthRuntime:
    account_service: OAuthService
    verifier: FirebaseTokenVerifier
    rate_limiter: RedisOAuthRateLimiter


async def get_registration_service(
    session: SessionDependency,
    settings: SettingsDependency,
) -> AsyncIterator[RegistrationService]:
    secret = settings.auth_outbox_encryption_key
    cipher = OutboxPayloadCipher.from_base64(
        encoded_key=secret.get_secret_value() if secret is not None else "",
        key_id=settings.auth_outbox_key_id,
    )
    redis_client: Redis = Redis.from_url(
        settings.redis_url,
        socket_connect_timeout=settings.readiness_timeout_seconds,
        socket_timeout=settings.readiness_timeout_seconds,
    )
    service = RegistrationService(
        session=session,
        password_hasher=Argon2PasswordHasher(),
        payload_cipher=cipher,
        rate_limiter=RedisRegistrationRateLimiter(
            redis_client,
            ip_attempts=settings.auth_registration_ip_limit,
            email_attempts=settings.auth_registration_email_limit,
            window_seconds=settings.auth_registration_rate_window_seconds,
        ),
        verification_ttl=timedelta(seconds=settings.auth_verification_ttl_seconds),
    )
    try:
        yield service
    finally:
        await redis_client.aclose()


RegistrationServiceDependency = Annotated[
    RegistrationService,
    Depends(get_registration_service),
]


async def get_applicant_upgrade_service(
    session: SessionDependency,
) -> AsyncIterator[ApplicantUpgradeService]:
    yield ApplicantUpgradeService(session=session)


ApplicantUpgradeServiceDependency = Annotated[
    ApplicantUpgradeService,
    Depends(get_applicant_upgrade_service),
]


async def get_session_service(
    session: SessionDependency,
    settings: SettingsDependency,
) -> AsyncIterator[SessionService]:
    jwt_secret = settings.jwt_secret
    csrf_secret = settings.auth_csrf_secret
    redis_client: Redis = Redis.from_url(
        settings.redis_url,
        socket_connect_timeout=settings.readiness_timeout_seconds,
        socket_timeout=settings.readiness_timeout_seconds,
    )
    service = SessionService(
        session=session,
        password_hasher=Argon2PasswordHasher(),
        access_tokens=AccessTokenManager(
            secret=jwt_secret.get_secret_value() if jwt_secret is not None else "",
            issuer=settings.auth_jwt_issuer,
            audience=settings.auth_jwt_audience,
            ttl=timedelta(seconds=settings.auth_access_ttl_seconds),
        ),
        csrf_tokens=CsrfTokenManager(
            secret=csrf_secret.get_secret_value() if csrf_secret is not None else ""
        ),
        rate_limiter=RedisAuthRateLimiter(
            redis_client,
            scope="login",
            ip_attempts=settings.auth_login_ip_limit,
            email_attempts=settings.auth_login_email_limit,
            window_seconds=settings.auth_login_rate_window_seconds,
        ),
        refresh_ttl=timedelta(seconds=settings.auth_refresh_ttl_seconds),
        mfa_policy=StaffMfaPolicy(
            max_age=timedelta(seconds=settings.staff_mfa_max_age_seconds),
            enabled=settings.firebase_totp_enabled,
        ),
    )
    try:
        yield service
    finally:
        await redis_client.aclose()


SessionServiceDependency = Annotated[SessionService, Depends(get_session_service)]


async def get_staff_invitation_service(
    session: SessionDependency,
    settings: SettingsDependency,
) -> AsyncIterator[StaffInvitationService]:
    secret = settings.auth_outbox_encryption_key
    cipher = OutboxPayloadCipher.from_base64(
        encoded_key=secret.get_secret_value() if secret is not None else "",
        key_id=settings.auth_outbox_key_id,
    )
    yield StaffInvitationService(
        session=session,
        payload_cipher=cipher,
        invitation_ttl=timedelta(seconds=settings.staff_invitation_ttl_seconds),
    )


StaffInvitationServiceDependency = Annotated[
    StaffInvitationService,
    Depends(get_staff_invitation_service),
]


async def get_firebase_auth_runtime(
    session: SessionDependency,
    settings: SettingsDependency,
    session_service: SessionServiceDependency,
) -> AsyncIterator[FirebaseAuthRuntime]:
    if not settings.firebase_project_id:
        raise OAuthProviderUnavailableError()
    redis_client: Redis = Redis.from_url(
        settings.redis_url,
        socket_connect_timeout=settings.readiness_timeout_seconds,
        socket_timeout=settings.readiness_timeout_seconds,
    )
    verifier = FirebaseTokenVerifier.create(
        project_id=settings.firebase_project_id,
        jwks_uri=settings.firebase_jwks_uri,
        timeout_seconds=settings.firebase_timeout_seconds,
        emulator_host=settings.firebase_auth_emulator_host or None,
    )
    runtime = FirebaseAuthRuntime(
        account_service=OAuthService(
            session=session,
            session_issuer=session_service,
        ),
        verifier=verifier,
        rate_limiter=RedisOAuthRateLimiter(
            redis_client,
            attempts=settings.oauth_rate_limit,
            window_seconds=settings.oauth_rate_window_seconds,
        ),
    )
    try:
        yield runtime
    finally:
        await verifier.close()
        await redis_client.aclose()


FirebaseAuthRuntimeDependency = Annotated[
    FirebaseAuthRuntime,
    Depends(get_firebase_auth_runtime),
]


async def get_current_principal(
    request: Request,
    service: SessionServiceDependency,
    settings: SettingsDependency,
) -> AuthPrincipal:
    access_token = request.cookies.get(settings.auth_access_cookie_name)
    if access_token is None:
        from app.modules.auth.errors import UnauthenticatedError

        raise UnauthenticatedError()
    return await service.authenticate_access(access_token)


async def get_optional_current_principal(
    request: Request,
    service: SessionServiceDependency,
    settings: SettingsDependency,
) -> AuthPrincipal | None:
    access_token = request.cookies.get(settings.auth_access_cookie_name)
    if access_token is None:
        return None
    try:
        return await service.authenticate_access(access_token)
    except UnauthenticatedError:
        return None


CurrentPrincipalDependency = Annotated[
    AuthPrincipal,
    Depends(get_current_principal),
]

OptionalCurrentPrincipalDependency = Annotated[
    AuthPrincipal | None,
    Depends(get_optional_current_principal),
]


async def get_csrf_protected_principal(
    request: Request,
    principal: CurrentPrincipalDependency,
    settings: SettingsDependency,
) -> AuthPrincipal:
    csrf_cookie = request.cookies.get(settings.auth_csrf_cookie_name)
    csrf_header = request.headers.get("X-CSRF-Token")
    secret = settings.auth_csrf_secret
    if (
        csrf_cookie is None
        or csrf_header is None
        or not secrets.compare_digest(csrf_cookie, csrf_header)
        or not CsrfTokenManager(
            secret=secret.get_secret_value() if secret is not None else ""
        ).verify(csrf_cookie, principal.session_id)
    ):
        raise CsrfValidationError()
    return principal


CsrfProtectedPrincipalDependency = Annotated[
    AuthPrincipal,
    Depends(get_csrf_protected_principal),
]


async def get_optional_csrf_principal(
    request: Request,
    service: SessionServiceDependency,
    settings: SettingsDependency,
) -> AuthPrincipal | None:
    access_token = request.cookies.get(settings.auth_access_cookie_name)
    if access_token is None:
        return None
    principal = await service.authenticate_access(access_token)
    csrf_cookie = request.cookies.get(settings.auth_csrf_cookie_name)
    csrf_header = request.headers.get("X-CSRF-Token")
    secret = settings.auth_csrf_secret
    if (
        csrf_cookie is None
        or csrf_header is None
        or not secrets.compare_digest(csrf_cookie, csrf_header)
        or not CsrfTokenManager(
            secret=secret.get_secret_value() if secret is not None else ""
        ).verify(csrf_cookie, principal.session_id)
    ):
        raise CsrfValidationError()
    return principal


OptionalCsrfPrincipalDependency = Annotated[
    AuthPrincipal | None,
    Depends(get_optional_csrf_principal),
]


async def get_password_reset_service(
    session: SessionDependency,
    settings: SettingsDependency,
) -> AsyncIterator[PasswordResetService]:
    secret = settings.auth_outbox_encryption_key
    cipher = OutboxPayloadCipher.from_base64(
        encoded_key=secret.get_secret_value() if secret is not None else "",
        key_id=settings.auth_outbox_key_id,
    )
    redis_client: Redis = Redis.from_url(
        settings.redis_url,
        socket_connect_timeout=settings.readiness_timeout_seconds,
        socket_timeout=settings.readiness_timeout_seconds,
    )
    service = PasswordResetService(
        session=session,
        password_hasher=Argon2PasswordHasher(),
        payload_cipher=cipher,
        rate_limiter=RedisAuthRateLimiter(
            redis_client,
            scope="password-reset",
            ip_attempts=settings.auth_password_reset_ip_limit,
            email_attempts=settings.auth_password_reset_email_limit,
            window_seconds=settings.auth_password_reset_rate_window_seconds,
        ),
        reset_ttl=timedelta(seconds=settings.auth_password_reset_ttl_seconds),
    )
    try:
        yield service
    finally:
        await redis_client.aclose()


PasswordResetServiceDependency = Annotated[
    PasswordResetService,
    Depends(get_password_reset_service),
]
