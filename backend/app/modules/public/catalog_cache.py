import hashlib
import json
import logging
from collections.abc import Mapping
from time import monotonic
from typing import Protocol

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.modules.public.telemetry import CatalogTelemetry, catalog_telemetry

CACHE_SCHEMA_VERSION = "v1"
GENERATION_KEY = f"public:catalog:{CACHE_SCHEMA_VERSION}:generation"
logger = logging.getLogger(__name__)


def public_catalog_cache_key(parameters: Mapping[str, object]) -> str:
    canonical = json.dumps(
        {"scope": "published-public", **parameters},
        separators=(",", ":"),
        sort_keys=True,
        default=str,
    )
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    return f"works:list:{digest}"


def public_featured_cache_key(limit: int) -> str:
    return f"works:featured:{limit}"


def public_detail_cache_key(slug: str) -> str:
    digest = hashlib.sha256(slug.strip().lower().encode()).hexdigest()
    return f"work:detail:{digest}"


def public_taxonomy_cache_key(kind: str) -> str:
    if kind not in {"categories", "category-tree", "tags"}:
        raise ValueError("Unsupported taxonomy cache kind.")
    return f"taxonomy:{kind}"


class PublicCatalogCache(Protocol):
    async def get(self, key: str) -> str | None: ...

    async def set(self, key: str, value: str) -> None: ...


class CatalogCacheInvalidator(Protocol):
    async def invalidate(self, *, reason: str) -> int | None: ...


class RedisPublicCatalogCache:
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
        scope = self._scope(key)
        try:
            generation = await self._current_generation()
            self._generation = generation
            value = await self._redis.get(self._versioned_key(generation, key))
        except (RedisError, OSError, TimeoutError):
            self._record(scope, "error", started)
            logger.warning(
                "public_catalog_cache_unavailable",
                extra={"action": "cache_get", "cache_scope": scope},
            )
            return None
        outcome = "miss" if value is None else "hit"
        self._record(scope, outcome, started)
        if value is None:
            return None
        return value.decode() if isinstance(value, bytes) else str(value)

    async def set(self, key: str, value: str) -> None:
        started = monotonic()
        scope = self._scope(key)
        try:
            generation = self._generation or await self._current_generation()
            stored = await self._redis.eval(
                self._SET_IF_CURRENT,
                2,
                GENERATION_KEY,
                self._versioned_key(generation, key),
                generation,
                value,
                str(self._ttl_seconds),
            )
        except (RedisError, OSError, TimeoutError):
            self._record(scope, "error", started)
            logger.warning(
                "public_catalog_cache_unavailable",
                extra={"action": "cache_set", "cache_scope": scope},
            )
            return
        self._record(scope, "write" if int(stored) == 1 else "stale", started)

    async def invalidate(self, *, reason: str) -> int | None:
        started = monotonic()
        try:
            generation = int(await self._redis.incr(GENERATION_KEY))
            await self._redis.expire(
                GENERATION_KEY,
                max(self._ttl_seconds * 4, 86_400),
            )
        except (RedisError, OSError, TimeoutError):
            self._record("all", "invalidation_error", started)
            logger.error(
                "public_catalog_cache_invalidation_failed",
                extra={"action": "cache_invalidate", "outcome": reason},
            )
            return None
        self._generation = str(generation)
        self._record("all", "invalidated", started)
        logger.info(
            "public_catalog_cache_invalidated",
            extra={
                "action": "cache_invalidate",
                "outcome": reason,
                "cache_generation": generation,
            },
        )
        return generation

    async def _current_generation(self) -> str:
        value = await self._redis.get(GENERATION_KEY)
        if value is None:
            return "0"
        return value.decode() if isinstance(value, bytes) else str(value)

    def _record(self, scope: str, outcome: str, started: float) -> None:
        self._telemetry.record_cache(
            scope=scope,
            outcome=outcome,
            duration_seconds=monotonic() - started,
        )

    @staticmethod
    def _versioned_key(generation: str, key: str) -> str:
        return f"public:{CACHE_SCHEMA_VERSION}:g{generation}:{key}"

    @staticmethod
    def _scope(key: str) -> str:
        return key.split(":", maxsplit=1)[0]
