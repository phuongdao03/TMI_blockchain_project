from app.core.errors import DomainError


class InvalidVerificationTokenError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="VERIFICATION_TOKEN_INVALID",
            message="Verification token is invalid or expired.",
            status_code=400,
        )


class RateLimitExceededError(DomainError):
    def __init__(self, *, retry_after_seconds: int) -> None:
        super().__init__(
            code="RATE_LIMITED",
            message="Too many requests. Please try again later.",
            status_code=429,
            details={"retry_after_seconds": retry_after_seconds},
        )


class RateLimitUnavailableError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="RATE_LIMIT_UNAVAILABLE",
            message="Registration is temporarily unavailable.",
            status_code=503,
        )


class InvalidCredentialsError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="INVALID_CREDENTIALS",
            message="Email or password is incorrect.",
            status_code=401,
        )


class UnauthenticatedError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="UNAUTHENTICATED",
            message="Authentication is required.",
            status_code=401,
        )


class ApplicantUpgradeNotAllowedError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="APPLICANT_UPGRADE_NOT_ALLOWED",
            message="This account cannot be upgraded to an applicant account.",
            status_code=409,
        )


class CsrfValidationError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="CSRF_VALIDATION_FAILED",
            message="Request authenticity could not be verified.",
            status_code=403,
        )


class AuthSessionNotFoundError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="AUTH_SESSION_NOT_FOUND",
            message="Session was not found.",
            status_code=404,
        )


class InvalidPasswordResetTokenError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="PASSWORD_RESET_TOKEN_INVALID",
            message="Password reset token is invalid or expired.",
            status_code=400,
        )


class OAuthProviderUnavailableError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="OAUTH_PROVIDER_UNAVAILABLE",
            message="The identity provider is temporarily unavailable.",
            status_code=503,
        )


class OAuthStateInvalidError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="OAUTH_STATE_INVALID",
            message="The OAuth request is invalid or expired.",
            status_code=400,
        )


class OAuthIdentityInvalidError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="OAUTH_IDENTITY_INVALID",
            message="The identity provider response is invalid.",
            status_code=400,
        )


class OAuthAccountLinkRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="OAUTH_ACCOUNT_LINK_REQUIRED",
            message=(
                "This email is already registered. Sign in with the existing "
                "method before linking a new identity."
            ),
            status_code=409,
        )


class OAuthRateLimitedError(DomainError):
    def __init__(self, *, retry_after_seconds: int = 1) -> None:
        super().__init__(
            code="OAUTH_RATE_LIMITED",
            message="Too many OAuth attempts. Please try again later.",
            status_code=429,
            details={"retry_after_seconds": max(retry_after_seconds, 1)},
        )
