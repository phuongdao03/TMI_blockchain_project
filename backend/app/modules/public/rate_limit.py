import hashlib
from typing import cast

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.modules.auth.errors import (
    RateLimitExceededError,
    RateLimitUnavailableError,
)

PUBLIC_RATE_LIMIT_SCRIPT = """
local count = redis.call("INCR", KEYS[1])
if count == 1 then
  redis.call("EXPIRE", KEYS[1], ARGV[1])
end
return {count, redis.call("TTL", KEYS[1])}
"""


class RedisPublicRateLimiter:
    def __init__(
        self,
        client: Redis,
        *,
        attempts: int,
        window_seconds: int,
        scope: str = "public:request:ip",
    ) -> None:
        self._client = client
        self._attempts = attempts
        self._window_seconds = window_seconds
        self._scope = scope

    async def check(self, client_ip: str) -> None:
        digest = hashlib.sha256(client_ip.encode()).hexdigest()
        try:
            raw = await self._client.eval(
                PUBLIC_RATE_LIMIT_SCRIPT,
                1,
                f"{self._scope}:{digest}",
                self._window_seconds,
            )
        except (RedisError, OSError, TimeoutError) as exc:
            raise RateLimitUnavailableError() from exc
        count, retry_after = cast(list[int], raw)
        if count > self._attempts:
            raise RateLimitExceededError(retry_after_seconds=max(retry_after, 1))
