from app.core.errors import DomainError


class MediaValidationError(DomainError):
    def __init__(self, message: str) -> None:
        super().__init__(
            code="MEDIA_VALIDATION_ERROR",
            message=message,
            status_code=422,
        )


class MediaNotFoundError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="MEDIA_NOT_FOUND",
            message="Media asset was not found.",
            status_code=404,
        )


class MediaForbiddenError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="MEDIA_FORBIDDEN",
            message="Media asset access is forbidden.",
            status_code=403,
        )


class MediaInvalidStateError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="MEDIA_INVALID_STATE",
            message="Media asset is not in the required state.",
            status_code=409,
        )


class MediaSignatureInvalidError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="MEDIA_SIGNATURE_INVALID",
            message="Upload result signature is invalid.",
            status_code=422,
        )


class MediaUploadMetadataMismatchError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="MEDIA_UPLOAD_METADATA_MISMATCH",
            message="Uploaded asset metadata does not match the authorization.",
            status_code=422,
        )


class MediaProviderUnavailableError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="MEDIA_PROVIDER_UNAVAILABLE",
            message="Media provider is unavailable.",
            status_code=503,
        )
