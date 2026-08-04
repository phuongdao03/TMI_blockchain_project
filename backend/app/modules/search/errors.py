from app.core.errors import DomainError


class SearchQueryInvalidError(DomainError, ValueError):
    def __init__(self, reason: str, *, limit: int | None = None) -> None:
        details: dict[str, object] = {"reason": reason}
        if limit is not None:
            details["limit"] = limit
        super().__init__(
            code="SEARCH_QUERY_INVALID",
            message="Search query is invalid.",
            status_code=422,
            details=details,
        )


class SearchFilterInvalidError(DomainError, ValueError):
    def __init__(self, reason: str) -> None:
        super().__init__(
            code="SEARCH_FILTER_INVALID",
            message="Search filter is invalid.",
            status_code=422,
            details={"reason": reason},
        )


class SearchSortInvalidError(DomainError, ValueError):
    def __init__(self, reason: str = "unsupported_sort") -> None:
        super().__init__(
            code="SEARCH_SORT_INVALID",
            message="Search sort is invalid.",
            status_code=422,
            details={"reason": reason},
        )


class SearchRateLimitedError(DomainError):
    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__(
            code="SEARCH_RATE_LIMITED",
            message="Search rate limit exceeded.",
            status_code=429,
            details={"retryAfterSeconds": retry_after_seconds},
        )


class SearchRateLimitUnavailableError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="SEARCH_RATE_LIMIT_UNAVAILABLE",
            message="Search rate limit is temporarily unavailable.",
            status_code=503,
        )


class SearchIndexUnavailableError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="SEARCH_INDEX_UNAVAILABLE",
            message="Search is temporarily unavailable.",
            status_code=503,
        )
