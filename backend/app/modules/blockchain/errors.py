from app.core.errors import DomainError


class BlockchainNotFoundError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="BLOCKCHAIN_TRANSACTION_NOT_FOUND",
            message="Blockchain transaction was not found.",
            status_code=404,
        )


class BlockchainForbiddenError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="BLOCKCHAIN_FORBIDDEN",
            message="Blockchain administration access is forbidden.",
            status_code=403,
        )


class BlockchainConflictError(DomainError):
    def __init__(self, message: str) -> None:
        super().__init__(
            code="BLOCKCHAIN_STATE_CONFLICT",
            message=message,
            status_code=409,
        )


class BlockchainUnavailableError(DomainError):
    def __init__(self, message: str = "Blockchain service is unavailable.") -> None:
        super().__init__(
            code="BLOCKCHAIN_UNAVAILABLE",
            message=message,
            status_code=503,
        )


class BlockchainTransientError(RuntimeError):
    """Signals a retryable worker failure after durable failure recording."""
