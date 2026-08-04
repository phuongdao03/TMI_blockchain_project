from app.core.errors import DomainError


class PaymentNotFoundError(DomainError):
    def __init__(self, message: str = "Payment order was not found.") -> None:
        super().__init__(
            code="PAYMENT_NOT_FOUND",
            message=message,
            status_code=404,
        )


class PaymentForbiddenError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="PAYMENT_FORBIDDEN",
            message="Payment order access is forbidden.",
            status_code=403,
        )


class PaymentConflictError(DomainError):
    def __init__(self, message: str = "Payment order state conflicts.") -> None:
        super().__init__(
            code="PAYMENT_CONFLICT",
            message=message,
            status_code=409,
        )


class PaymentAmountMismatchError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="PAYMENT_AMOUNT_MISMATCH",
            message="Webhook amount or currency does not match the order.",
            status_code=409,
        )


class PaymentProviderError(DomainError):
    def __init__(self, message: str = "Payment provider is unavailable.") -> None:
        super().__init__(
            code="PAYMENT_PROVIDER_UNAVAILABLE",
            message=message,
            status_code=503,
        )


class PaymentInvalidWebhookError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="PAYMENT_WEBHOOK_INVALID",
            message="Payment webhook verification failed.",
            status_code=400,
        )
