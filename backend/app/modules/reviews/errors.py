from app.core.errors import DomainError


class ReviewNotFoundError(DomainError):
    def __init__(self, message: str = "Review resource was not found.") -> None:
        super().__init__(
            code="REVIEW_NOT_FOUND",
            message=message,
            status_code=404,
        )


class ReviewForbiddenError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="REVIEW_FORBIDDEN",
            message="Review access is forbidden.",
            status_code=403,
        )


class ReviewConflictError(DomainError):
    def __init__(
        self,
        message: str = "Review state conflicts with this action.",
    ) -> None:
        super().__init__(
            code="REVIEW_CONFLICT",
            message=message,
            status_code=409,
        )


class ReviewValidationError(DomainError):
    def __init__(self, message: str) -> None:
        super().__init__(
            code="REVIEW_VALIDATION_ERROR",
            message=message,
            status_code=422,
        )
