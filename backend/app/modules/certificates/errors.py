from app.core.errors import DomainError


class CertificateNotFoundError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="CERTIFICATE_NOT_FOUND",
            message="Certificate was not found.",
            status_code=404,
        )


class CertificateForbiddenError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="CERTIFICATE_FORBIDDEN",
            message="Certificate access is forbidden.",
            status_code=403,
        )


class CertificateConflictError(DomainError):
    def __init__(self, message: str) -> None:
        super().__init__(
            code="CERTIFICATE_STATE_CONFLICT",
            message=message,
            status_code=409,
        )


class CertificateGenerationError(RuntimeError):
    """A recoverable certificate rendition or storage failure."""
