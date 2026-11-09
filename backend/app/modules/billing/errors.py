from collections.abc import Mapping

from app.core.errors import DomainError


class PriceCatalogConflictError(DomainError):
    """Raised when billing cannot resolve one authoritative listed price."""

    def __init__(
        self,
        message: str,
        *,
        details: Mapping[str, object] | None = None,
        code: str = "BILLING_POLICY_CONFLICT",
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=409,
            details=details,
        )
