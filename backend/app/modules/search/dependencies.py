from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from redis.asyncio import Redis

from app.modules.auth.dependencies import SessionDependency, SettingsDependency
from app.modules.auth.errors import RateLimitExceededError, RateLimitUnavailableError
from app.modules.public.rate_limit import RedisPublicRateLimiter
from app.modules.search.autocomplete_cache import RedisAutocompleteCache
from app.modules.search.discovery_cache import RedisDiscoveryCache
from app.modules.search.discovery_repository import SearchDiscoveryRepository
from app.modules.search.discovery_service import SearchDiscoveryService
from app.modules.search.errors import (
    SearchRateLimitedError,
    SearchRateLimitUnavailableError,
)
from app.modules.search.repository import SearchRepository
from app.modules.search.service import PublicSearchService


async def get_public_search_service(
    session: SessionDependency,
    settings: SettingsDependency,
) -> AsyncIterator[PublicSearchService]:
    redis_client: Redis = Redis.from_url(
        settings.redis_url,
        socket_connect_timeout=settings.readiness_timeout_seconds,
        socket_timeout=settings.readiness_timeout_seconds,
    )
    try:
        yield PublicSearchService(
            SearchRepository(
                session,
                statement_timeout_ms=settings.search_statement_timeout_ms,
                trigram_min_length=settings.search_trigram_min_length,
                trigram_threshold=settings.search_trigram_threshold,
                trigram_max_boost=settings.search_trigram_max_boost,
            ),
            autocomplete_cache=RedisAutocompleteCache(
                redis_client,
                ttl_seconds=settings.search_autocomplete_cache_ttl_seconds,
            ),
            event_recorder=SearchDiscoveryService(
                SearchDiscoveryRepository(session),
                minimum_trending_count=settings.search_trending_minimum_count,
            ),
            result_cache=RedisDiscoveryCache(
                redis_client,
                ttl_seconds=settings.public_catalog_cache_ttl_seconds,
            ),
        )
    finally:
        await redis_client.aclose()


PublicSearchDependency = Annotated[
    PublicSearchService,
    Depends(get_public_search_service),
]


async def enforce_public_search_rate_limit(
    request: Request,
    settings: SettingsDependency,
) -> None:
    redis_client: Redis = Redis.from_url(
        settings.redis_url,
        socket_connect_timeout=settings.readiness_timeout_seconds,
        socket_timeout=settings.readiness_timeout_seconds,
    )
    try:
        limiter = RedisPublicRateLimiter(
            redis_client,
            attempts=settings.search_rate_limit,
            window_seconds=settings.search_rate_window_seconds,
            scope="public:search:ip",
        )
        try:
            await limiter.check(
                request.client.host if request.client is not None else "unknown"
            )
        except RateLimitExceededError as error:
            retry_after = error.details.get("retry_after_seconds", 1)
            retry_after_seconds = retry_after if isinstance(retry_after, int) else 1
            raise SearchRateLimitedError(retry_after_seconds) from error
        except RateLimitUnavailableError as error:
            raise SearchRateLimitUnavailableError() from error
    finally:
        await redis_client.aclose()
