import hashlib
import hmac
import secrets


class EngagementVisitorContext:
    def __init__(self, *, secret: str) -> None:
        self._secret = secret.encode()

    def issue(self) -> str:
        token = secrets.token_urlsafe(32)
        return f"{token}.{self._signature(token)}"

    def is_valid(self, value: str | None) -> bool:
        if value is None:
            return False
        token, separator, signature = value.partition(".")
        return (
            bool(separator)
            and len(token) == 43
            and hmac.compare_digest(signature, self._signature(token))
        )

    def digest(self, value: str) -> str:
        return hmac.new(
            self._secret,
            value.encode(),
            hashlib.sha256,
        ).hexdigest()

    def _signature(self, token: str) -> str:
        return hmac.new(
            self._secret,
            token.encode(),
            hashlib.sha256,
        ).hexdigest()
