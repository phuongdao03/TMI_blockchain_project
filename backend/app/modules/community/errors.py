from app.core.errors import DomainError


class CommunityNotFoundError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="COMMUNITY_NOT_FOUND",
            message="Community content was not found.",
            status_code=404,
        )


class CommunityForbiddenError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="COMMUNITY_FORBIDDEN",
            message="Community action is forbidden.",
            status_code=403,
        )


class CommunityConflictError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="COMMUNITY_STATE_CONFLICT",
            message="Community content is not in a valid state for this action.",
            status_code=409,
        )


class CommunityValidationError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="COMMUNITY_REQUEST_INVALID",
            message="Community request is invalid.",
            status_code=422,
        )


class CommunityRateLimitedError(DomainError):
    def __init__(self, *, retry_after_seconds: int) -> None:
        super().__init__(
            code="COMMUNITY_RATE_LIMITED",
            message="Too many community actions. Please try again later.",
            status_code=429,
            details={"retry_after_seconds": retry_after_seconds},
        )


class CommunityRateLimitUnavailableError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="COMMUNITY_RATE_LIMIT_UNAVAILABLE",
            message="Community actions are temporarily unavailable.",
            status_code=503,
        )
