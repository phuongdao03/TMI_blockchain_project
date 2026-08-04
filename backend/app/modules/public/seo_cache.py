import json
from collections.abc import Sequence
from typing import Protocol

from redis.asyncio import Redis
from redis.exceptions import RedisError

SITEMAP_MANIFEST_KEY = "public:sitemap:manifest:v1"


class PublicSitemapCache(Protocol):
    async def get_manifest(self) -> dict[str, object] | None: ...

    async def get_page(
        self, generation: str, page: int
    ) -> list[dict[str, object]] | None: ...

    async def replace(
        self,
        manifest: dict[str, object],
        pages: Sequence[list[dict[str, object]]],
    ) -> None: ...


class RedisPublicSitemapCache:
    def __init__(self, redis: Redis, *, ttl_seconds: int) -> None:
        self._redis = redis
        self._ttl_seconds = ttl_seconds

    async def get_manifest(self) -> dict[str, object] | None:
        raw = await self._get(SITEMAP_MANIFEST_KEY)
        if raw is None:
            return None
        try:
            value = json.loads(raw)
            return value if isinstance(value, dict) else None
        except (TypeError, json.JSONDecodeError):
            return None

    async def get_page(
        self, generation: str, page: int
    ) -> list[dict[str, object]] | None:
        raw = await self._get(self._page_key(generation, page))
        if raw is None:
            return None
        try:
            value = json.loads(raw)
            return value if isinstance(value, list) else None
        except (TypeError, json.JSONDecodeError):
            return None

    async def replace(
        self,
        manifest: dict[str, object],
        pages: Sequence[list[dict[str, object]]],
    ) -> None:
        generation = str(manifest["generation"])
        try:
            pipeline = self._redis.pipeline(transaction=True)
            for index, page in enumerate(pages, start=1):
                pipeline.set(
                    self._page_key(generation, index),
                    json.dumps(page, separators=(",", ":")),
                    ex=self._ttl_seconds,
                )
            pipeline.set(
                SITEMAP_MANIFEST_KEY,
                json.dumps(manifest, separators=(",", ":")),
                ex=self._ttl_seconds,
            )
            await pipeline.execute()
        except (RedisError, OSError, TimeoutError):
            return

    async def _get(self, key: str) -> str | None:
        try:
            value = await self._redis.get(key)
        except (RedisError, OSError, TimeoutError):
            return None
        if value is None:
            return None
        return value.decode() if isinstance(value, bytes) else str(value)

    @staticmethod
    def _page_key(generation: str, page: int) -> str:
        return f"public:sitemap:{generation}:{page}"
