from app.core.errors import DomainError


class AdvertisingNotFoundError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="ADVERTISING_NOT_FOUND",
            message="Không tìm thấy nội dung quảng cáo.",
            status_code=404,
        )


class AdvertisingConflictError(DomainError):
    def __init__(
        self,
        message: str,
        *,
        code: str = "ADVERTISING_CONFLICT",
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=409,
            details=details,
        )


class AdvertisingForbiddenError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="ADVERTISING_FORBIDDEN",
            message="Bạn không có quyền thực hiện thao tác này.",
            status_code=403,
        )
