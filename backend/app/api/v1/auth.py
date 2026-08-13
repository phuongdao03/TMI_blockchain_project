from typing import Any
from uuid import UUID

from fastapi import APIRouter, Header, Request, Response, status

from app.core.config import Settings
from app.core.schemas import ErrorEnvelope, ResponseMeta, SuccessEnvelope
from app.modules.audit.service import AuditService
from app.modules.auth.dependencies import (
    ApplicantUpgradeServiceDependency,
    CsrfProtectedPrincipalDependency,
    CurrentPrincipalDependency,
    FirebaseAuthRuntimeDependency,
    PasswordResetServiceDependency,
    RegistrationServiceDependency,
    SessionDependency,
    SessionServiceDependency,
    SettingsDependency,
    StaffInvitationServiceDependency,
)
from app.modules.auth.oauth import create_oauth_attempt
from app.modules.auth.schemas import (
    ApplicantUpgradeRequest,
    AuthSessionData,
    AuthStatusData,
    AuthUserData,
    EmailVerifiedData,
    FirebaseExchangeRequest,
    ForgotPasswordRequest,
    LoginData,
    LoginRequest,
    PasswordResetAcceptedData,
    PasswordResetData,
    RegisterRequest,
    RegistrationAcceptedData,
    ResetPasswordRequest,
    StaffInvitationAcceptedData,
    StaffInvitationAcceptRequest,
    StaffMfaRecoveryAuthorizeRequest,
    VerifyEmailRequest,
)
from app.modules.auth.session_service import ClientMetadata, IssuedSession
from app.modules.auth.staff_account_service import StaffAccountService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    422: {
        "description": "Request validation failed.",
        "model": ErrorEnvelope,
    },
    429: {
        "description": "Registration rate limit exceeded.",
        "model": ErrorEnvelope,
    },
    503: {
        "description": "A required dependency is unavailable.",
        "model": ErrorEnvelope,
    },
}

AUTH_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {
        "description": "Authentication failed or is required.",
        "model": ErrorEnvelope,
    },
    403: {
        "description": "CSRF validation failed.",
        "model": ErrorEnvelope,
    },
    422: ERROR_RESPONSES[422],
    429: {
        "description": "Authentication rate limit exceeded.",
        "model": ErrorEnvelope,
    },
    503: ERROR_RESPONSES[503],
}

OAUTH_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"description": "OAuth request was invalid.", "model": ErrorEnvelope},
    401: AUTH_ERROR_RESPONSES[401],
    403: AUTH_ERROR_RESPONSES[403],
    409: {
        "description": "The account requires an authenticated link.",
        "model": ErrorEnvelope,
    },
    422: ERROR_RESPONSES[422],
    429: {"description": "OAuth rate limit exceeded.", "model": ErrorEnvelope},
    503: ERROR_RESPONSES[503],
}


def _client_metadata(request: Request, device_name: str | None) -> ClientMetadata:
    return ClientMetadata(
        client_ip=request.client.host if request.client is not None else "unknown",
        user_agent=request.headers.get("user-agent"),
        device_name=device_name,
    )


def _set_auth_cookies(
    response: Response,
    issued: IssuedSession,
    settings: Settings,
) -> None:
    secure = settings.app_env != "local"
    response.set_cookie(
        key=settings.auth_access_cookie_name,
        value=issued.access_token,
        max_age=settings.auth_access_ttl_seconds,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key=settings.auth_refresh_cookie_name,
        value=issued.refresh_token,
        max_age=settings.auth_refresh_ttl_seconds,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key=settings.auth_csrf_cookie_name,
        value=issued.csrf_token,
        max_age=settings.auth_refresh_ttl_seconds,
        httponly=False,
        secure=secure,
        samesite="lax",
        path="/",
    )


def _clear_auth_cookies(response: Response, settings: Settings) -> None:
    secure = settings.app_env != "local"
    for cookie_name in (
        settings.auth_access_cookie_name,
        settings.auth_refresh_cookie_name,
        settings.auth_csrf_cookie_name,
    ):
        response.delete_cookie(
            key=cookie_name,
            httponly=cookie_name != settings.auth_csrf_cookie_name,
            secure=secure,
            samesite="lax",
            path="/",
        )


@router.post(
    "/register",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=SuccessEnvelope[RegistrationAcceptedData],
    responses=ERROR_RESPONSES,
)
async def register(
    payload: RegisterRequest,
    request: Request,
    service: RegistrationServiceDependency,
) -> SuccessEnvelope[RegistrationAcceptedData]:
    client_ip = request.client.host if request.client is not None else "unknown"
    await service.register(
        email=str(payload.email),
        password=payload.password.get_secret_value(),
        client_ip=client_ip,
        account_type=payload.account_type,
    )
    return SuccessEnvelope(
        data=RegistrationAcceptedData(
            message=(
                "If the address can be registered, verification instructions "
                "will be sent."
            )
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/applicant-upgrade",
    response_model=SuccessEnvelope[AuthUserData],
    responses={
        401: AUTH_ERROR_RESPONSES[401],
        403: AUTH_ERROR_RESPONSES[403],
        409: {
            "description": "The account cannot be upgraded.",
            "model": ErrorEnvelope,
        },
        422: ERROR_RESPONSES[422],
    },
)
async def upgrade_to_applicant(
    payload: ApplicantUpgradeRequest,
    request: Request,
    principal: CsrfProtectedPrincipalDependency,
    service: ApplicantUpgradeServiceDependency,
) -> SuccessEnvelope[AuthUserData]:
    result = await service.upgrade(
        principal,
        account_type=payload.account_type,
    )
    return SuccessEnvelope(
        data=AuthUserData(
            id=result.user_id,
            email=result.email,
            roles=result.roles,
            accountType=result.account_type,
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/firebase/exchange",
    response_model=SuccessEnvelope[LoginData],
    responses=OAUTH_ERROR_RESPONSES,
)
async def exchange_firebase_token(
    payload: FirebaseExchangeRequest,
    request: Request,
    response: Response,
    runtime: FirebaseAuthRuntimeDependency,
    session_service: SessionServiceDependency,
    settings: SettingsDependency,
) -> SuccessEnvelope[LoginData]:
    client_ip = request.client.host if request.client is not None else "unknown"
    await runtime.rate_limiter.check(client_ip)
    attempt = create_oauth_attempt(
        payload.account_type,
        payload.next_path or "/dashboard",
    )
    claims = await runtime.verifier.validate_id_token(payload.id_token)
    completion = await runtime.account_service.complete(
        claims=claims,
        attempt=attempt,
        metadata=_client_metadata(request, "Firebase"),
    )
    principal = await session_service.authenticate_access(
        completion.issued.access_token
    )
    _set_auth_cookies(response, completion.issued, settings)
    return SuccessEnvelope(
        data=LoginData(
            user=AuthUserData(
                id=principal.user_id,
                email=principal.email,
                roles=principal.roles,
                accountType=principal.account_type,
            )
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/staff-invitations/accept",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=SuccessEnvelope[StaffInvitationAcceptedData],
    responses=OAUTH_ERROR_RESPONSES,
)
async def accept_staff_invitation(
    payload: StaffInvitationAcceptRequest,
    request: Request,
    runtime: FirebaseAuthRuntimeDependency,
    invitation_service: StaffInvitationServiceDependency,
    session: SessionDependency,
) -> SuccessEnvelope[StaffInvitationAcceptedData]:
    client_ip = request.client.host if request.client is not None else "unknown"
    await runtime.rate_limiter.check(client_ip)
    claims = await runtime.verifier.validate_id_token(payload.id_token)
    await invitation_service.accept(
        raw_token=payload.invitation_token.get_secret_value(),
        claims=claims,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    return SuccessEnvelope(
        data=StaffInvitationAcceptedData(status="MFA_ENROLLMENT_REQUIRED"),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/staff-mfa/recovery/authorize",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=SuccessEnvelope[StaffInvitationAcceptedData],
    responses=OAUTH_ERROR_RESPONSES,
)
async def authorize_staff_mfa_recovery(
    payload: StaffMfaRecoveryAuthorizeRequest,
    request: Request,
    runtime: FirebaseAuthRuntimeDependency,
    session: SessionDependency,
) -> SuccessEnvelope[StaffInvitationAcceptedData]:
    client_ip = request.client.host if request.client is not None else "unknown"
    await runtime.rate_limiter.check(client_ip)
    claims = await runtime.verifier.validate_id_token(payload.id_token)
    await StaffAccountService(session).authorize_mfa_reenrollment(
        claims=claims,
        audit=AuditService(session),
        request_id=request.state.request_id,
        user_agent=request.headers.get("user-agent"),
    )
    return SuccessEnvelope(
        data=StaffInvitationAcceptedData(status="MFA_ENROLLMENT_REQUIRED"),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/verify-email",
    response_model=SuccessEnvelope[EmailVerifiedData],
    responses={
        400: {
            "description": "Verification token is invalid or expired.",
            "model": ErrorEnvelope,
        },
        422: ERROR_RESPONSES[422],
    },
)
async def verify_email(
    payload: VerifyEmailRequest,
    request: Request,
    service: RegistrationServiceDependency,
) -> SuccessEnvelope[EmailVerifiedData]:
    await service.verify_email(payload.token)
    return SuccessEnvelope(
        data=EmailVerifiedData(status="verified"),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/login",
    response_model=SuccessEnvelope[LoginData],
    responses=AUTH_ERROR_RESPONSES,
)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    service: SessionServiceDependency,
    settings: SettingsDependency,
) -> SuccessEnvelope[LoginData]:
    issued = await service.login(
        email=str(payload.email),
        password=payload.password.get_secret_value(),
        metadata=_client_metadata(request, payload.device_name),
    )
    principal = await service.authenticate_access(issued.access_token)
    _set_auth_cookies(response, issued, settings)
    return SuccessEnvelope(
        data=LoginData(
            user=AuthUserData(
                id=principal.user_id,
                email=principal.email,
                roles=principal.roles,
                accountType=principal.account_type,
            )
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/refresh",
    response_model=SuccessEnvelope[AuthStatusData],
    responses=AUTH_ERROR_RESPONSES,
)
async def refresh(
    request: Request,
    response: Response,
    service: SessionServiceDependency,
    settings: SettingsDependency,
    csrf_header: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> SuccessEnvelope[AuthStatusData]:
    refresh_token = request.cookies.get(settings.auth_refresh_cookie_name)
    if refresh_token is None:
        from app.modules.auth.errors import UnauthenticatedError

        raise UnauthenticatedError()
    issued = await service.refresh(
        refresh_token=refresh_token,
        csrf_cookie=request.cookies.get(settings.auth_csrf_cookie_name),
        csrf_header=csrf_header,
        metadata=_client_metadata(request, None),
    )
    _set_auth_cookies(response, issued, settings)
    return SuccessEnvelope(
        data=AuthStatusData(status="refreshed"),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/logout",
    response_model=SuccessEnvelope[AuthStatusData],
    responses=AUTH_ERROR_RESPONSES,
)
async def logout(
    request: Request,
    response: Response,
    service: SessionServiceDependency,
    settings: SettingsDependency,
    csrf_header: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> SuccessEnvelope[AuthStatusData]:
    refresh_token = request.cookies.get(settings.auth_refresh_cookie_name)
    if refresh_token is None:
        from app.modules.auth.errors import UnauthenticatedError

        raise UnauthenticatedError()
    await service.logout(
        refresh_token=refresh_token,
        csrf_cookie=request.cookies.get(settings.auth_csrf_cookie_name),
        csrf_header=csrf_header,
    )
    _clear_auth_cookies(response, settings)
    return SuccessEnvelope(
        data=AuthStatusData(status="logged_out"),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/me",
    response_model=SuccessEnvelope[AuthUserData],
    responses={401: AUTH_ERROR_RESPONSES[401]},
)
async def me(
    request: Request,
    principal: CurrentPrincipalDependency,
) -> SuccessEnvelope[AuthUserData]:
    return SuccessEnvelope(
        data=AuthUserData(
            id=principal.user_id,
            email=principal.email,
            roles=principal.roles,
            accountType=principal.account_type,
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.get(
    "/sessions",
    response_model=SuccessEnvelope[list[AuthSessionData]],
    responses={401: AUTH_ERROR_RESPONSES[401]},
)
async def list_sessions(
    request: Request,
    principal: CurrentPrincipalDependency,
    service: SessionServiceDependency,
) -> SuccessEnvelope[list[AuthSessionData]]:
    sessions = await service.list_sessions(principal)
    return SuccessEnvelope(
        data=[
            AuthSessionData(
                id=item.id,
                device_name=item.device_name,
                user_agent=item.user_agent,
                created_at=item.created_at,
                expires_at=item.expires_at,
                is_current=item.is_current,
            )
            for item in sessions
        ],
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.delete(
    "/sessions/{session_id}",
    response_model=SuccessEnvelope[AuthStatusData],
    responses={
        401: AUTH_ERROR_RESPONSES[401],
        403: AUTH_ERROR_RESPONSES[403],
        404: {
            "description": "Session was not found.",
            "model": ErrorEnvelope,
        },
    },
)
async def revoke_session(
    session_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    service: SessionServiceDependency,
    settings: SettingsDependency,
    csrf_header: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> SuccessEnvelope[AuthStatusData]:
    await service.revoke_session(
        principal=principal,
        target_session_id=session_id,
        csrf_cookie=request.cookies.get(settings.auth_csrf_cookie_name),
        csrf_header=csrf_header,
    )
    return SuccessEnvelope(
        data=AuthStatusData(status="revoked"),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/forgot-password",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=SuccessEnvelope[PasswordResetAcceptedData],
    responses={
        422: ERROR_RESPONSES[422],
        429: AUTH_ERROR_RESPONSES[429],
        503: ERROR_RESPONSES[503],
    },
)
async def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    service: PasswordResetServiceDependency,
) -> SuccessEnvelope[PasswordResetAcceptedData]:
    client_ip = request.client.host if request.client is not None else "unknown"
    await service.request_reset(email=str(payload.email), client_ip=client_ip)
    return SuccessEnvelope(
        data=PasswordResetAcceptedData(
            message=("If the address exists, password reset instructions will be sent.")
        ),
        meta=ResponseMeta(request_id=request.state.request_id),
    )


@router.post(
    "/reset-password",
    response_model=SuccessEnvelope[PasswordResetData],
    responses={
        400: {
            "description": "Password reset token is invalid or expired.",
            "model": ErrorEnvelope,
        },
        422: ERROR_RESPONSES[422],
    },
)
async def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    response: Response,
    service: PasswordResetServiceDependency,
    settings: SettingsDependency,
) -> SuccessEnvelope[PasswordResetData]:
    await service.reset_password(
        token=payload.token,
        new_password=payload.new_password.get_secret_value(),
    )
    _clear_auth_cookies(response, settings)
    return SuccessEnvelope(
        data=PasswordResetData(status="password_reset"),
        meta=ResponseMeta(request_id=request.state.request_id),
    )
