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


class ApplicantProfileIncompleteError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="APPLICANT_PROFILE_INCOMPLETE",
            message="Complete your applicant profile before creating a dossier.",
            status_code=409,
        )


class DossierInvalidStateError(DomainError):
    def __init__(self, message: str = "Dossier is not in the required state.") -> None:
        super().__init__(
            code="DOSSIER_INVALID_STATE",
            message=message,
            status_code=409,
        )


class DossierDuplicateContentError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="DOSSIER_DUPLICATE_CONTENT",
            message=(
                "This dossier matches an existing submission and cannot be "
                "submitted as a separate work."
            ),
            status_code=409,
        )


class DossierDuplicateDocumentError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="DOSSIER_DOCUMENT_CONFLICT",
            message=(
                "A submitted document conflicts with an existing protected "
                "record. Contact support if you are authorized to reuse it."
            ),
            status_code=409,
        )


class DossierValidationError(DomainError):
    def __init__(self, message: str) -> None:
        super().__init__(
            code="DOSSIER_VALIDATION_ERROR",
            message=message,
            status_code=422,
        )
