from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from redis.asyncio import Redis

from app.modules.audit.service import AuditService
from app.modules.auth.dependencies import SessionDependency, SettingsDependency
from app.modules.auth.errors import RateLimitExceededError, RateLimitUnavailableError
from app.modules.blockchain.gateway import SUPPORTED_CHAINS, BlockchainGateway
from app.modules.engagement.errors import (
    EngagementRateLimitedError,
    EngagementUnavailableError,
)
from app.modules.engagement.redis import RedisShareDeduplicator, RedisViewDeduplicator
from app.modules.engagement.service import EngagementService
from app.modules.engagement.visitor import EngagementVisitorContext
from app.modules.public.cache import RedisVerificationCache
from app.modules.public.catalog_cache import RedisPublicCatalogCache
from app.modules.public.rate_limit import RedisPublicRateLimiter
from app.modules.public.service import PublicCatalogService
from app.modules.public.verification import PublicVerificationService


async def get_public_catalog(
    session: SessionDependency,
    settings: SettingsDependency,
) -> AsyncIterator[PublicCatalogService]:
    redis_client: Redis = Redis.from_url(settings.redis_url)
    try:
        yield PublicCatalogService(
            session,
            cache=RedisPublicCatalogCache(
                redis_client,
                ttl_seconds=settings.public_catalog_cache_ttl_seconds,
            ),
        )
    finally:
        await redis_client.aclose()


async def get_public_verification(
    session: SessionDependency,
    settings: SettingsDependency,
) -> AsyncIterator[PublicVerificationService]:
    address = settings.certificate_contract_address
    gateway = BlockchainGateway(
        rpc_url=settings.blockchain_rpc_url,
        network=settings.blockchain_network,
        chain_id=settings.blockchain_chain_id,
        contract_address=address,
        abi_path=settings.blockchain_contract_abi_path,
        allowed_networks=SUPPORTED_CHAINS,
        allowed_contracts={settings.blockchain_network: {address}},
    )
    repository = PublicCatalogService(session).repository
    redis_client: Redis = Redis.from_url(settings.redis_url)
    try:
        yield PublicVerificationService(
            gateway=gateway,
            find_by_token=repository.find_by_token,
            find_by_number=repository.find_by_number,
            find_by_transaction=repository.find_by_transaction,
            explorer_base_url=settings.blockchain_explorer_base_url,
            cache=RedisVerificationCache(
                redis_client,
                ttl_seconds=settings.public_verification_cache_ttl_seconds,
            ),
            audit=AuditService(session, settings=settings),
            audit_session=session,
        )
    finally:
        await gateway.close()
        await redis_client.aclose()


PublicCatalogDependency = Annotated[
    PublicCatalogService,
    Depends(get_public_catalog),
]
PublicVerificationDependency = Annotated[
    PublicVerificationService,
    Depends(get_public_verification),
]


async def get_engagement_service(
    session: SessionDependency,
    settings: SettingsDependency,
) -> AsyncIterator[EngagementService]:
    secret = settings.engagement_visitor_hmac_secret
    if secret is None:
        raise EngagementUnavailableError()
    redis_client: Redis = Redis.from_url(settings.redis_url)
    try:
        yield EngagementService(
            session,
            views=RedisViewDeduplicator(
                redis_client,
                visitor_context=EngagementVisitorContext(
                    secret=secret.get_secret_value(),
                ),
                ttl_seconds=settings.engagement_view_dedupe_ttl_seconds,
            ),
            shares=RedisShareDeduplicator(
                redis_client,
                visitor_context=EngagementVisitorContext(
                    secret=secret.get_secret_value(),
                ),
                ttl_seconds=settings.engagement_view_dedupe_ttl_seconds,
            ),
        )
    finally:
        await redis_client.aclose()


EngagementServiceDependency = Annotated[
    EngagementService,
    Depends(get_engagement_service),
]


async def enforce_public_rate_limit(
    request: Request,
    settings: SettingsDependency,
) -> None:
    redis_client: Redis = Redis.from_url(settings.redis_url)
    try:
        limiter = RedisPublicRateLimiter(
            redis_client,
            attempts=settings.public_rate_limit,
            window_seconds=settings.public_rate_window_seconds,
        )
        await limiter.check(
            request.client.host if request.client is not None else "unknown"
        )
    finally:
        await redis_client.aclose()


async def enforce_public_report_rate_limit(
    request: Request,
    settings: SettingsDependency,
) -> None:
    redis_client: Redis = Redis.from_url(settings.redis_url)
    try:
        limiter = RedisPublicRateLimiter(
            redis_client,
            attempts=settings.public_report_rate_limit,
            window_seconds=settings.public_report_rate_window_seconds,
            scope="public:content-report:ip",
        )
        await limiter.check(
            request.client.host if request.client is not None else "unknown"
        )
    finally:
        await redis_client.aclose()


async def enforce_public_engagement_rate_limit(
    request: Request,
    settings: SettingsDependency,
) -> None:
    redis_client: Redis = Redis.from_url(settings.redis_url)
    try:
        limiter = RedisPublicRateLimiter(
            redis_client,
            attempts=settings.public_engagement_rate_limit,
            window_seconds=settings.public_engagement_rate_window_seconds,
            scope="public:engagement:ip",
        )
        try:
            await limiter.check(
                request.client.host if request.client is not None else "unknown"
            )
        except RateLimitExceededError as exc:
            raw_retry_after = exc.details.get("retry_after_seconds", 1)
            retry_after = raw_retry_after if isinstance(raw_retry_after, int) else 1
            raise EngagementRateLimitedError(
                retry_after_seconds=retry_after,
            ) from exc
        except RateLimitUnavailableError as exc:
            raise EngagementUnavailableError() from exc
    finally:
        await redis_client.aclose()
