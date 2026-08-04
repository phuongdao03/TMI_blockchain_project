import asyncio
import logging
from collections.abc import Mapping
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy import select

from app.core.config import Settings, get_settings
from app.db.session import get_session_factory
from app.modules.voting.aggregate_cache import RedisVoteSummaryCache
from app.modules.voting.aggregate_service import VoteAggregateService
from app.modules.voting.models import VoteAggregate, VotingCampaign
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


async def handle_voting_aggregate_event(
    *,
    aggregate_type: str,
    payload: Mapping[str, object],
    settings: Settings,
) -> None:
    redis_client: Redis = Redis.from_url(settings.redis_url)
    cache = RedisVoteSummaryCache(
        redis_client,
        ttl_seconds=settings.voting_summary_cache_ttl_seconds,
    )
    try:
        invalidate_campaign_ids: set[UUID] = set()
        async with get_session_factory()() as session:
            async with session.begin():
                service = VoteAggregateService(session)
                if aggregate_type == "vote":
                    campaign_value = payload.get("campaign_id")
                    work_value = payload.get("work_id")
                    if isinstance(campaign_value, str) and isinstance(work_value, str):
                        await service.recount_work(
                            UUID(campaign_value), UUID(work_value)
                        )
                        invalidate_campaign_ids.add(UUID(campaign_value))
                elif aggregate_type == "voting_campaign":
                    campaign_value = payload.get("campaign_id")
                    if isinstance(campaign_value, str):
                        invalidate_campaign_ids.add(UUID(campaign_value))
                elif aggregate_type == "public_work":
                    work_value = payload.get("public_work_id")
                    if isinstance(work_value, str):
                        campaign_ids = tuple(
                            (
                                await session.scalars(
                                    select(VoteAggregate.campaign_id)
                                    .where(VoteAggregate.work_id == UUID(work_value))
                                    .distinct()
                                )
                            ).all()
                        )
                        invalidate_campaign_ids.update(campaign_ids)
        for campaign_id in invalidate_campaign_ids:
            await cache.invalidate(campaign_id)
    finally:
        await redis_client.aclose()


async def _reconcile_all() -> None:
    settings = get_settings()
    redis_client: Redis = Redis.from_url(settings.redis_url)
    cache = RedisVoteSummaryCache(
        redis_client,
        ttl_seconds=settings.voting_summary_cache_ttl_seconds,
    )
    try:
        async with get_session_factory()() as session:
            campaign_ids = tuple(
                (await session.scalars(select(VotingCampaign.id))).all()
            )
            await session.rollback()
            for campaign_id in campaign_ids:
                async with session.begin():
                    await VoteAggregateService(session).recount_campaign(campaign_id)
                await cache.invalidate(campaign_id)
    finally:
        await redis_client.aclose()
    logger.info(
        "voting_aggregates_reconciled",
        extra={"action": "recount", "outcome": "success"},
    )


@celery_app.task  # type: ignore[misc]
def reconcile_vote_aggregates() -> None:
    asyncio.run(_reconcile_all())
