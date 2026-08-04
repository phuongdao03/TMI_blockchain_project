import hashlib
import logging
from time import monotonic

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.modules.public.catalog_cache import GENERATION_KEY
from app.modules.public.telemetry import CatalogTelemetry, catalog_telemetry

logger = logging.getLogger(__name__)
CACHE_VERSION = "v1"


def discovery_cache_key(namespace: str, canonical: str) -> str:
    if namespace not in {"result", "related", "trending"}:
        raise ValueError("Unsupported search cache namespace.")
    return f"{namespace}:{hashlib.sha256(canonical.encode()).hexdigest()}"


class RedisDiscoveryCache:
    _SET_IF_CURRENT = """
local current = redis.call('GET', KEYS[1])
if not current then current = '0' end
if current ~= ARGV[1] then return 0 end
redis.call('SET', KEYS[2], ARGV[2], 'EX', ARGV[3])
return 1
"""

    def __init__(
        self,
        redis: Redis,
        *,
        ttl_seconds: int,
        telemetry: CatalogTelemetry = catalog_telemetry,
    ) -> None:
        self._redis = redis
        self._ttl_seconds = ttl_seconds
        self._telemetry = telemetry
        self._generation: str | None = None

    async def get(self, key: str) -> str | None:
        started = monotonic()
        scope = key.split(":", 1)[0]
        try:
            generation = await self._current_generation()
            self._generation = generation
            value = await self._redis.get(self._key(generation, key))
            self._telemetry.record_cache(
                scope=f"search-{scope}",
                outcome="miss" if value is None else "hit",
                duration_seconds=monotonic() - started,
            )
            if value is None:
                return None
            return value.decode() if isinstance(value, bytes) else str(value)
        except (RedisError, OSError, TimeoutError):
            self._telemetry.record_cache(
                scope=f"search-{scope}",
                outcome="error",
                duration_seconds=monotonic() - started,
            )
            logger.warning(
                "search_cache_unavailable",
                extra={"cache_scope": scope, "action": "get"},
            )
            return None

    async def set(self, key: str, value: str) -> None:
        started = monotonic()
        scope = key.split(":", 1)[0]
        try:
            generation = self._generation or await self._current_generation()
            stored = await self._redis.eval(
                self._SET_IF_CURRENT,
                2,
                GENERATION_KEY,
                self._key(generation, key),
                generation,
                value,
                str(self._ttl_seconds),
            )
            self._telemetry.record_cache(
                scope=f"search-{scope}",
                outcome="write" if int(stored) else "stale",
                duration_seconds=monotonic() - started,
            )
        except (RedisError, OSError, TimeoutError):
            self._telemetry.record_cache(
                scope=f"search-{scope}",
                outcome="error",
                duration_seconds=monotonic() - started,
            )
            logger.warning(
                "search_cache_unavailable",
                extra={"cache_scope": scope, "action": "set"},
            )

    async def reserve(self, key: str, *, seconds: int = 3) -> bool:
        try:
            generation = await self._current_generation()
            result = await self._redis.set(
                f"{self._key(generation, key)}:lock", "1", ex=seconds, nx=True
            )
            return bool(result)
        except (RedisError, OSError, TimeoutError):
            return True

    async def release(self, key: str) -> None:
        try:
            generation = self._generation or await self._current_generation()
            await self._redis.delete(f"{self._key(generation, key)}:lock")
        except (RedisError, OSError, TimeoutError):
            return

    async def _current_generation(self) -> str:
        value = await self._redis.get(GENERATION_KEY)
        if value is None:
            return "0"
        return value.decode() if isinstance(value, bytes) else str(value)

    @staticmethod
    def _key(generation: str, key: str) -> str:
        return f"public:search:{CACHE_VERSION}:g{generation}:{key}"
