import hashlib
import secrets
from dataclasses import dataclass
from typing import Protocol, cast
from urllib.parse import urlsplit

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.modules.auth.errors import (
    OAuthProviderUnavailableError,
    OAuthRateLimitedError,
    OAuthStateInvalidError,
)
from app.modules.auth.models import AccountType

OAUTH_RATE_LIMIT_SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
return {count, redis.call('TTL', KEYS[1])}
"""


@dataclass(frozen=True, slots=True)
class OAuthAttempt:
    state: str
    nonce: str
    account_type: str
    next_path: str
    purpose: str = "login"
    user_id: str | None = None


class OAuthAttemptRateLimiter(Protocol):
    async def check(self, client_ip: str) -> None: ...


def validate_oauth_next(next_path: str | None) -> str:
    value = "/" if next_path is None else next_path
    if not isinstance(value, str) or len(value) > 512:
        raise OAuthStateInvalidError()
    if not value.startswith("/") or value.startswith("//"):
        raise OAuthStateInvalidError()
    if any(ord(character) < 0x20 for character in value) or "\\" in value:
        raise OAuthStateInvalidError()
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc or parsed.fragment:
        raise OAuthStateInvalidError()
    return value


def create_oauth_attempt(
    account_type: str | AccountType,
    next_path: str | None,
    *,
    purpose: str = "login",
    user_id: str | None = None,
) -> OAuthAttempt:
    try:
        normalized_account_type = AccountType(account_type).value
    except ValueError as exc:
        raise OAuthStateInvalidError() from exc
    if purpose not in {"login", "link"} or (
        (purpose == "link") != (user_id is not None)
    ):
        raise OAuthStateInvalidError()
    return OAuthAttempt(
        state=secrets.token_urlsafe(32),
        nonce=secrets.token_urlsafe(32),
        account_type=normalized_account_type,
        next_path=validate_oauth_next(next_path),
        purpose=purpose,
        user_id=user_id,
    )


class RedisOAuthRateLimiter:
    def __init__(
        self,
        redis: Redis,
        *,
        attempts: int,
        window_seconds: int,
    ) -> None:
        self._redis = redis
        self._attempts = attempts
        self._window_seconds = window_seconds

    async def check(self, client_ip: str) -> None:
        digest = hashlib.sha256(client_ip.encode()).hexdigest()
        key = f"auth:oauth:rate:{digest}"
        try:
            result = await self._redis.eval(
                OAUTH_RATE_LIMIT_SCRIPT,
                1,
                key,
                self._window_seconds,
            )
        except (RedisError, OSError, TimeoutError) as exc:
            raise OAuthProviderUnavailableError() from exc
        count, retry_after = cast(list[int], result)
        if count > self._attempts:
            raise OAuthRateLimitedError(retry_after_seconds=max(retry_after, 1))
