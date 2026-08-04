import hashlib
from typing import Protocol, cast

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.modules.auth.errors import (
    RateLimitExceededError,
    RateLimitUnavailableError,
)

RATE_LIMIT_SCRIPT = """
local ip_count = redis.call("INCR", KEYS[1])
if ip_count == 1 then
  redis.call("EXPIRE", KEYS[1], ARGV[3])
end
local email_count = redis.call("INCR", KEYS[2])
if email_count == 1 then
  redis.call("EXPIRE", KEYS[2], ARGV[3])
end
local retry_after = math.max(
  redis.call("TTL", KEYS[1]),
  redis.call("TTL", KEYS[2])
)
return {ip_count, email_count, retry_after}
"""


class RegistrationRateLimiter(Protocol):
    async def check(self, *, email: str, client_ip: str) -> None: ...


class RedisAuthRateLimiter:
    def __init__(
        self,
        client: Redis,
        *,
        scope: str,
        ip_attempts: int,
        email_attempts: int,
        window_seconds: int,
    ) -> None:
        self._client = client
        self._scope = scope
        self._ip_attempts = ip_attempts
        self._email_attempts = email_attempts
        self._window_seconds = window_seconds

    def _key(self, dimension: str, value: str) -> str:
        digest = hashlib.sha256(value.encode()).hexdigest()
        return f"auth:{self._scope}:{dimension}:{digest}"

    async def check(self, *, email: str, client_ip: str) -> None:
        try:
            raw_result = await self._client.eval(
                RATE_LIMIT_SCRIPT,
                2,
                self._key("ip", client_ip),
                self._key("email", email),
                self._ip_attempts,
                self._email_attempts,
                self._window_seconds,
            )
        except (RedisError, OSError, TimeoutError) as exc:
            raise RateLimitUnavailableError() from exc

        result = cast(list[int], raw_result)
        ip_count, email_count, retry_after = result
        if ip_count > self._ip_attempts or email_count > self._email_attempts:
            raise RateLimitExceededError(retry_after_seconds=max(retry_after, 1))


class RedisRegistrationRateLimiter(RedisAuthRateLimiter):
    def __init__(
        self,
        client: Redis,
        *,
        ip_attempts: int,
        email_attempts: int,
        window_seconds: int,
    ) -> None:
        super().__init__(
            client,
            scope="register",
            ip_attempts=ip_attempts,
            email_attempts=email_attempts,
            window_seconds=window_seconds,
        )
