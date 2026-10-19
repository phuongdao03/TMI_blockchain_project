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


class CmsGuideFeedbackConflictError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="GUIDE_FEEDBACK_ALREADY_SUBMITTED",
            message="Feedback has already been submitted for this article.",
            status_code=409,
        )


class CmsGuideArticleDeleteConflictError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="CMS_GUIDE_ARTICLE_MUST_BE_ARCHIVED",
            message="Archive a published guide article before deleting it.",
            status_code=409,
        )


class CmsGuideArticleInvalidError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="CMS_GUIDE_ARTICLE_INVALID",
            message="Guide article content or audience is invalid.",
            status_code=422,
        )
