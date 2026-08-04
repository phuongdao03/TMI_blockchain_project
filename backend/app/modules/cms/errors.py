from app.core.errors import DomainError


class CmsSlugConflictError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="CMS_SLUG_CONFLICT", message="Slug is already in use.", status_code=409
        )


class CmsNotFoundError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="CMS_NOT_FOUND", message="CMS content was not found.", status_code=404
        )


class CmsForbiddenError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="CMS_FORBIDDEN", message="CMS access is forbidden.", status_code=403
        )
