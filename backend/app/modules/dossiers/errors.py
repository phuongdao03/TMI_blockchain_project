from app.core.errors import DomainError


class DossierNotFoundError(DomainError):
    def __init__(self, message: str = "Dossier was not found.") -> None:
        super().__init__(
            code="DOSSIER_NOT_FOUND",
            message=message,
            status_code=404,
        )


class DossierForbiddenError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="DOSSIER_FORBIDDEN",
            message="Dossier access is forbidden.",
            status_code=403,
        )


class DossierInvalidStateError(DomainError):
    def __init__(self, message: str = "Dossier is not in the required state.") -> None:
        super().__init__(
            code="DOSSIER_INVALID_STATE",
            message=message,
            status_code=409,
        )


class DossierValidationError(DomainError):
    def __init__(self, message: str) -> None:
        super().__init__(
            code="DOSSIER_VALIDATION_ERROR",
            message=message,
            status_code=422,
        )
