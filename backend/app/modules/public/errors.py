from collections.abc import Sequence

from app.core.errors import DomainError


class PublicWorkNotFoundError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="PUBLIC_WORK_NOT_FOUND",
            message="Public work was not found.",
            status_code=404,
        )


class PublicWorkForbiddenError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="PUBLIC_WORK_FORBIDDEN",
            message="Public work management is forbidden.",
            status_code=403,
        )


class PublicWorkNotPublishableError(DomainError):
    def __init__(self, reasons: Sequence[str]) -> None:
        super().__init__(
            code="PUBLIC_WORK_NOT_PUBLISHABLE",
            message="Public work does not satisfy the publication checklist.",
            status_code=409,
            details={"reasons": list(reasons)},
        )


class PublicWorkVersionConflictError(DomainError):
    def __init__(self, *, current_version: int) -> None:
        super().__init__(
            code="PUBLIC_WORK_VERSION_CONFLICT",
            message="Public work was modified by another request.",
            status_code=409,
            details={"current_version": current_version},
        )


class PublicWorkReasonRequiredError(DomainError, ValueError):
    def __init__(self) -> None:
        super().__init__(
            code="PUBLIC_WORK_REASON_REQUIRED",
            message="A reason is required for this action.",
            status_code=422,
        )


class PublicWorkScheduleError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="PUBLIC_WORK_SCHEDULE_INVALID",
            message="Publish time must be a future UTC timestamp.",
            status_code=422,
        )


class PublicWorkFeaturedWindowError(DomainError, ValueError):
    def __init__(self) -> None:
        super().__init__(
            code="PUBLIC_WORK_FEATURED_WINDOW_INVALID",
            message=(
                "Featured timestamps must be timezone-aware and the end must be "
                "later than both the start and current time."
            ),
            status_code=422,
        )


class TaxonomyNotFoundError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="TAXONOMY_NOT_FOUND",
            message="Category or tag was not found.",
            status_code=404,
        )


class TaxonomySlugConflictError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="TAXONOMY_SLUG_CONFLICT",
            message="Normalized taxonomy slug is already in use.",
            status_code=409,
        )


class TaxonomyCycleError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="TAXONOMY_CYCLE",
            message="Category parent would create a cycle.",
            status_code=409,
        )


class TaxonomyInUseError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="TAXONOMY_IN_USE",
            message="Taxonomy in use cannot be deactivated.",
            status_code=409,
        )


class PublicMediaNotFoundError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="PUBLIC_MEDIA_NOT_FOUND",
            message="Public work media relation was not found.",
            status_code=404,
        )


class PublicMediaValidationError(DomainError, ValueError):
    def __init__(self, message: str) -> None:
        super().__init__(
            code="PUBLIC_MEDIA_INVALID",
            message=message,
            status_code=422,
        )


class PublicMediaConflictError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="PUBLIC_MEDIA_CONFLICT",
            message="Media is already attached or ordering is stale.",
            status_code=409,
        )


class PublicWorkMetadataValidationError(DomainError, ValueError):
    def __init__(self, message: str) -> None:
        super().__init__(
            code="PUBLIC_WORK_METADATA_INVALID",
            message=message,
            status_code=422,
        )


class PublicWorkSlugConflictError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="PUBLIC_WORK_SLUG_CONFLICT",
            message="Public work slug is already reserved.",
            status_code=409,
        )


class ContentReportDuplicateError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="CONTENT_REPORT_DUPLICATE",
            message="An equivalent report was already submitted recently.",
            status_code=409,
        )


class ContentReportNotFoundError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="CONTENT_REPORT_NOT_FOUND",
            message="Content report was not found.",
            status_code=404,
        )


class ContentReportTransitionError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="CONTENT_REPORT_TRANSITION_INVALID",
            message="Content report status transition is invalid.",
            status_code=409,
        )
