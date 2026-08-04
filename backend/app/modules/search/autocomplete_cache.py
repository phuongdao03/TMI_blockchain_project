import hashlib
import json
import logging

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.modules.public.catalog_cache import GENERATION_KEY
from app.modules.search.types import AutocompleteKind, AutocompleteSuggestion

logger = logging.getLogger(__name__)
CACHE_VERSION = "v1"


class RedisAutocompleteCache:
    _SET_IF_CURRENT = """
local current = redis.call('GET', KEYS[1])
if not current then current = '0' end
if current ~= ARGV[1] then return 0 end
redis.call('SET', KEYS[2], ARGV[2], 'EX', ARGV[3])
return 1
"""

    def __init__(self, redis: Redis, *, ttl_seconds: int) -> None:
        self._redis = redis
        self._ttl_seconds = ttl_seconds
        self._generation: str | None = None

    async def get(
        self,
        normalized_query: str,
    ) -> tuple[AutocompleteSuggestion, ...] | None:
        try:
            generation = await self._current_generation()
            self._generation = generation
            value = await self._redis.get(self._key(generation, normalized_query))
            if value is None:
                return None
            payload = json.loads(value)
            return tuple(
                AutocompleteSuggestion(
                    kind=AutocompleteKind(item["kind"]),
                    label=item["label"],
                    slug=item["slug"],
                )
                for item in payload
            )
        except (RedisError, OSError, TimeoutError, ValueError, TypeError, KeyError):
            logger.warning(
                "search_autocomplete_cache_unavailable",
                extra={"action": "cache_get", "cache_scope": "autocomplete"},
            )
            return None

    async def set(
        self,
        normalized_query: str,
        suggestions: tuple[AutocompleteSuggestion, ...],
    ) -> None:
        payload = json.dumps(
            [
                {"kind": item.kind.value, "label": item.label, "slug": item.slug}
                for item in suggestions
            ],
            ensure_ascii=False,
            separators=(",", ":"),
        )
        try:
            generation = self._generation or await self._current_generation()
            await self._redis.eval(
                self._SET_IF_CURRENT,
                2,
                GENERATION_KEY,
                self._key(generation, normalized_query),
                generation,
                payload,
                str(self._ttl_seconds),
            )
        except (RedisError, OSError, TimeoutError):
            logger.warning(
                "search_autocomplete_cache_unavailable",
                extra={"action": "cache_set", "cache_scope": "autocomplete"},
            )

    async def _current_generation(self) -> str:
        value = await self._redis.get(GENERATION_KEY)
        if value is None:
            return "0"
        return value.decode() if isinstance(value, bytes) else str(value)

    @staticmethod
    def _key(generation: str, normalized_query: str) -> str:
        digest = hashlib.sha256(normalized_query.encode()).hexdigest()
        return f"public:search:autocomplete:{CACHE_VERSION}:g{generation}:{digest}"
