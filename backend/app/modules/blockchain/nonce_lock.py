import secrets
from typing import Protocol

from redis.asyncio import Redis
from redis.exceptions import RedisError


class NonceLock(Protocol):
    async def acquire(self, key: str, *, ttl_seconds: int) -> str | None: ...

    async def release(self, key: str, token: str) -> None: ...


class RedisNonceLock:
    _RELEASE_SCRIPT = """
if redis.call("GET", KEYS[1]) == ARGV[1] then
  return redis.call("DEL", KEYS[1])
end
return 0
"""

    def __init__(self, client: Redis) -> None:
        self._client = client

    async def acquire(self, key: str, *, ttl_seconds: int) -> str | None:
        token = secrets.token_urlsafe(32)
        try:
            acquired = await self._client.set(
                key,
                token,
                ex=ttl_seconds,
                nx=True,
            )
        except RedisError as exc:
            raise RuntimeError("Nonce lock backend is unavailable.") from exc
        return token if acquired else None

    async def release(self, key: str, token: str) -> None:
        try:
            await self._client.eval(self._RELEASE_SCRIPT, 1, key, token)
        except RedisError:
            # TTL guarantees eventual release. Never mask the transaction result.
            return
