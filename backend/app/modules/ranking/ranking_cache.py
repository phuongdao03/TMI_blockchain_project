import hashlib
import json
import logging
from collections.abc import Mapping
from datetime import datetime
from typing import Protocol
from uuid import UUID

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.modules.ranking.public_types import (
    PublicRankingItemView,
    PublicRankingPage,
    PublicRankingSnapshotView,
)

CACHE_SCHEMA_VERSION = "v1"
GENERATION_KEY = f"public:ranking:{CACHE_SCHEMA_VERSION}:generation"
logger = logging.getLogger(__name__)


def public_ranking_cache_key(
    *,
    campaign_slug: str,
    version: int | None,
    category_id: UUID | None,
    page: int,
    page_size: int,
) -> str:
    canonical = json.dumps(
        {
            "scope": "published-public-ranking",
            "campaign_slug": campaign_slug.strip().lower(),
            "version": version if version is not None else "published",
            "category_id": str(category_id) if category_id is not None else None,
            "page": page,
            "page_size": page_size,
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    return f"ranking:public:{digest}"


class RankingCache(Protocol):
    async def get(self, key: str) -> str | None: ...

    async def set(self, key: str, value: str) -> None: ...


class RankingCacheInvalidator(Protocol):
    async def invalidate(self, *, reason: str) -> int | None: ...


class RedisRankingCache:
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

    async def get(self, key: str) -> str | None:
        scope = self._scope(key)
        try:
            generation = await self._current_generation()
            self._generation = generation
            value = await self._redis.get(self._versioned_key(generation, key))
        except (RedisError, OSError, TimeoutError):
            logger.warning(
                "public_ranking_cache_unavailable",
                extra={"action": "cache_get", "cache_scope": scope},
            )
            return None
        outcome = "miss" if value is None else "hit"
        logger.debug(
            "public_ranking_cache_%s",
            outcome,
            extra={"action": "cache_get", "cache_scope": scope},
        )
        if value is None:
            return None
        return value.decode() if isinstance(value, bytes) else str(value)

    async def set(self, key: str, value: str) -> None:
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
            logger.warning(
                "public_ranking_cache_unavailable",
                extra={"action": "cache_set", "cache_scope": scope},
            )
            return
        logger.debug(
            "public_ranking_cache_%s",
            "write" if int(stored) == 1 else "stale",
            extra={"action": "cache_set", "cache_scope": scope},
        )

    async def invalidate(self, *, reason: str) -> int | None:
        try:
            generation = int(await self._redis.incr(GENERATION_KEY))
            await self._redis.expire(
                GENERATION_KEY,
                max(self._ttl_seconds * 4, 86_400),
            )
        except (RedisError, OSError, TimeoutError):
            logger.error(
                "public_ranking_cache_invalidation_failed",
                extra={"action": "cache_invalidate", "outcome": reason},
            )
            return None
        self._generation = str(generation)
        logger.info(
            "public_ranking_cache_invalidated",
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

    @staticmethod
    def _versioned_key(generation: str, key: str) -> str:
        return f"public:{CACHE_SCHEMA_VERSION}:g{generation}:{key}"

    @staticmethod
    def _scope(key: str) -> str:
        return key.split(":", maxsplit=1)[0]


def serialize_ranking_page(page: PublicRankingPage) -> str:
    snapshot = page.snapshot
    payload = {
        "snapshot": {
            "id": str(snapshot.id),
            "campaign_id": str(snapshot.campaign_id),
            "version": snapshot.version,
            "formula_version": snapshot.formula_version,
            "campaign_rule_version": snapshot.campaign_rule_version,
            "source_digest": snapshot.source_digest,
            "result_digest": snapshot.result_digest,
            "candidate_count": snapshot.candidate_count,
            "total_valid_votes": snapshot.total_valid_votes,
            "created_at": snapshot.created_at.isoformat(),
        },
        "items": [
            {
                "work_id": str(item.work_id),
                "slug": item.slug,
                "title": item.title,
                "short_description": item.short_description,
                "author_display_name": item.author_display_name,
                "category_id": str(item.category_id),
                "category_name": item.category_name,
                "category_slug": item.category_slug,
                "rank": item.rank,
                "category_rank": item.category_rank,
                "display_order": item.display_order,
                "score": item.score,
                "effective_vote_count": item.effective_vote_count,
            }
            for item in page.items
        ],
        "page": page.page,
        "page_size": page.page_size,
        "total": page.total,
    }
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def deserialize_ranking_page(value: str) -> PublicRankingPage | None:
    try:
        payload = json.loads(value)
        snapshot_data = _mapping(payload["snapshot"])
        item_data = payload["items"]
        if not isinstance(item_data, list):
            return None
        snapshot = PublicRankingSnapshotView(
            id=UUID(str(snapshot_data["id"])),
            campaign_id=UUID(str(snapshot_data["campaign_id"])),
            version=_int(snapshot_data["version"]),
            formula_version=str(snapshot_data["formula_version"]),
            campaign_rule_version=_int(snapshot_data["campaign_rule_version"]),
            source_digest=str(snapshot_data["source_digest"]),
            result_digest=str(snapshot_data["result_digest"]),
            candidate_count=_int(snapshot_data["candidate_count"]),
            total_valid_votes=_int(snapshot_data["total_valid_votes"]),
            created_at=datetime.fromisoformat(str(snapshot_data["created_at"])),
        )
        items = tuple(
            PublicRankingItemView(
                work_id=UUID(str(_mapping(item)["work_id"])),
                slug=str(_mapping(item)["slug"]),
                title=str(_mapping(item)["title"]),
                short_description=str(_mapping(item)["short_description"]),
                author_display_name=_optional_str(_mapping(item)["author_display_name"]),
                category_id=UUID(str(_mapping(item)["category_id"])),
                category_name=str(_mapping(item)["category_name"]),
                category_slug=_optional_str(_mapping(item)["category_slug"]),
                rank=_int(_mapping(item)["rank"]),
                category_rank=_int(_mapping(item)["category_rank"]),
                display_order=_int(_mapping(item)["display_order"]),
                score=_int(_mapping(item)["score"]),
                effective_vote_count=_int(_mapping(item)["effective_vote_count"]),
            )
            for item in item_data
        )
        return PublicRankingPage(
            snapshot=snapshot,
            items=items,
            page=_int(payload["page"]),
            page_size=_int(payload["page_size"]),
            total=_int(payload["total"]),
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        logger.warning("public_ranking_cache_payload_invalid")
        return None


def _mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError("cache payload object expected")
    return value


def _optional_str(value: object) -> str | None:
    return None if value is None else str(value)


def _int(value: object) -> int:
    return int(str(value))
