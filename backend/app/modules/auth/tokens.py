import hashlib
import hmac
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
from jwt import InvalidTokenError


class TokenConfigurationError(RuntimeError):
    """Raised when token signing configuration is unsafe."""


class InvalidAccessTokenError(ValueError):
    """Raised when an access token cannot be trusted."""


@dataclass(frozen=True, slots=True)
class AccessTokenIdentity:
    user_id: UUID
    session_id: UUID


class AccessTokenManager:
    def __init__(
        self,
        *,
        secret: str,
        issuer: str,
        audience: str,
        ttl: timedelta,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if len(secret.encode()) < 32:
            raise TokenConfigurationError("JWT_SECRET must contain at least 32 bytes.")
        self._secret = secret
        self._issuer = issuer
        self._audience = audience
        self._ttl = ttl
        self._clock = clock or (lambda: datetime.now(UTC))

    def issue(self, *, user_id: UUID, session_id: UUID) -> str:
        now = self._clock()
        return jwt.encode(
            {
                "aud": self._audience,
                "exp": now + self._ttl,
                "iat": now,
                "iss": self._issuer,
                "jti": str(uuid4()),
                "nbf": now,
                "sid": str(session_id),
                "sub": str(user_id),
                "typ": "access",
            },
            self._secret,
            algorithm="HS256",
        )

    def decode(self, token: str) -> AccessTokenIdentity:
        try:
            claims = jwt.decode(
                token,
                self._secret,
                algorithms=["HS256"],
                audience=self._audience,
                issuer=self._issuer,
                options={
                    "require": [
                        "aud",
                        "exp",
                        "iat",
                        "iss",
                        "jti",
                        "nbf",
                        "sid",
                        "sub",
                        "typ",
                    ]
                },
            )
            if claims["typ"] != "access":
                raise InvalidAccessTokenError("Unexpected token type.")
            return AccessTokenIdentity(
                user_id=UUID(claims["sub"]),
                session_id=UUID(claims["sid"]),
            )
        except (InvalidTokenError, KeyError, TypeError, ValueError) as exc:
            raise InvalidAccessTokenError("Invalid access token.") from exc


class CsrfTokenManager:
    def __init__(self, *, secret: str) -> None:
        if len(secret.encode()) < 32:
            raise TokenConfigurationError(
                "CSRF signing secret must contain at least 32 bytes."
            )
        self._secret = secret.encode()

    def issue(self, session_id: UUID) -> str:
        nonce = secrets.token_urlsafe(32)
        signature = self._signature(session_id, nonce)
        return f"{nonce}.{signature}"

    def verify(self, token: str, session_id: UUID) -> bool:
        try:
            nonce, supplied_signature = token.split(".", maxsplit=1)
        except ValueError:
            return False
        expected_signature = self._signature(session_id, nonce)
        return hmac.compare_digest(supplied_signature, expected_signature)

    def _signature(self, session_id: UUID, nonce: str) -> str:
        message = f"{session_id}:{nonce}".encode()
        return hmac.new(self._secret, message, hashlib.sha256).hexdigest()


def new_opaque_token() -> str:
    return secrets.token_urlsafe(32)


def hash_opaque_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def hash_ip_address(client_ip: str) -> str:
    return hashlib.sha256(client_ip.encode()).hexdigest()
