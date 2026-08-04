from app.core.errors import DomainError


class EngagementRateLimitedError(DomainError):
    def __init__(self, *, retry_after_seconds: int) -> None:
        super().__init__(
            code="ENGAGEMENT_RATE_LIMITED",
            message="Too many engagement requests. Please try again later.",
            status_code=429,
            details={"retry_after_seconds": max(retry_after_seconds, 1)},
        )


class EngagementUnavailableError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="ENGAGEMENT_UNAVAILABLE",
            message="Engagement tracking is temporarily unavailable.",
            status_code=503,
        )
