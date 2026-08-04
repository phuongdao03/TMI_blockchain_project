from app.core.errors import DomainError


class CouncilNotFoundError(DomainError):
    def __init__(self, message: str = "Council resource was not found.") -> None:
        super().__init__(
            code="COUNCIL_NOT_FOUND",
            message=message,
            status_code=404,
        )


class CouncilForbiddenError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="COUNCIL_FORBIDDEN",
            message="Council access is forbidden.",
            status_code=403,
        )


class CouncilConflictError(DomainError):
    def __init__(
        self,
        message: str = "Council state conflicts with this action.",
    ) -> None:
        super().__init__(
            code="COUNCIL_CONFLICT",
            message=message,
            status_code=409,
        )


class CouncilValidationError(DomainError):
    def __init__(self, message: str) -> None:
        super().__init__(
            code="COUNCIL_VALIDATION_ERROR",
            message=message,
            status_code=422,
        )
