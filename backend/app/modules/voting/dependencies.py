import logging
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request
from redis.asyncio import Redis

from app.modules.audit.service import AuditService
from app.modules.auth.dependencies import (
    CurrentPrincipalDependency,
    SessionDependency,
    SettingsDependency,
)
from app.modules.auth.errors import RateLimitUnavailableError
from app.modules.auth.rate_limit import RedisAuthRateLimiter
from app.modules.auth.security import OutboxPayloadCipher
from app.modules.voting.admin_vote_service import AdminVoteService
from app.modules.voting.aggregate_cache import RedisVoteSummaryCache
from app.modules.voting.aggregate_service import VoteAggregateService
from app.modules.voting.eligibility import VotingEligibilityService
from app.modules.voting.history_service import VoteHistoryService
from app.modules.voting.public_service import PublicVotingService
from app.modules.voting.service import VotingCampaignService
from app.modules.voting.vote_repository import (
    VoteRepository,
    VotingEligibilityRepository,
)
from app.modules.voting.vote_service import VotingService

logger = logging.getLogger(__name__)


async def get_voting_campaign_service(
    session: SessionDependency,
    settings: SettingsDependency,
) -> AsyncIterator[VotingCampaignService]:
    secret = settings.auth_outbox_encryption_key
    yield VotingCampaignService(
        session=session,
        audit=AuditService(session),
        payload_cipher=OutboxPayloadCipher.from_base64(
            encoded_key=secret.get_secret_value() if secret is not None else "",
            key_id=settings.auth_outbox_key_id,
        ),
    )


VotingCampaignServiceDependency = Annotated[
    VotingCampaignService,
    Depends(get_voting_campaign_service),
]


def get_voting_eligibility_service(
    session: SessionDependency,
) -> VotingEligibilityService:
    return VotingEligibilityService(VotingEligibilityRepository(session))


VotingEligibilityServiceDependency = Annotated[
    VotingEligibilityService,
    Depends(get_voting_eligibility_service),
]


async def get_voting_service(
    session: SessionDependency,
    settings: SettingsDependency,
) -> AsyncIterator[VotingService]:
    secret = settings.auth_outbox_encryption_key
    eligibility = VotingEligibilityService(VotingEligibilityRepository(session))
    yield VotingService(
        session=session,
        eligibility=eligibility,
        audit=AuditService(session),
        payload_cipher=OutboxPayloadCipher.from_base64(
            encoded_key=secret.get_secret_value() if secret is not None else "",
            key_id=settings.auth_outbox_key_id,
        ),
    )


VotingServiceDependency = Annotated[VotingService, Depends(get_voting_service)]


def get_vote_history_service(session: SessionDependency) -> VoteHistoryService:
    return VoteHistoryService(VoteRepository(session))


VoteHistoryServiceDependency = Annotated[
    VoteHistoryService,
    Depends(get_vote_history_service),
]


def get_admin_vote_service(session: SessionDependency) -> AdminVoteService:
    return AdminVoteService(session)


AdminVoteServiceDependency = Annotated[
    AdminVoteService,
    Depends(get_admin_vote_service),
]


async def get_public_voting_service(
    session: SessionDependency,
    settings: SettingsDependency,
) -> AsyncIterator[PublicVotingService]:
    redis_client: Redis = Redis.from_url(
        settings.redis_url,
        socket_connect_timeout=settings.readiness_timeout_seconds,
        socket_timeout=settings.readiness_timeout_seconds,
    )
    try:
        cache = RedisVoteSummaryCache(
            redis_client,
            ttl_seconds=settings.voting_summary_cache_ttl_seconds,
        )
        yield PublicVotingService(
            session,
            VoteAggregateService(session, cache=cache),
        )
    finally:
        await redis_client.aclose()


PublicVotingServiceDependency = Annotated[
    PublicVotingService,
    Depends(get_public_voting_service),
]


async def enforce_voting_rate_limit(
    campaign_id: UUID,
    request: Request,
    principal: CurrentPrincipalDependency,
    settings: SettingsDependency,
) -> None:
    redis_client: Redis = Redis.from_url(
        settings.redis_url,
        socket_connect_timeout=settings.readiness_timeout_seconds,
        socket_timeout=settings.readiness_timeout_seconds,
    )
    try:
        limiter = RedisAuthRateLimiter(
            redis_client,
            scope="vote",
            ip_attempts=settings.voting_ip_rate_limit,
            email_attempts=settings.voting_user_rate_limit,
            window_seconds=settings.voting_rate_window_seconds,
        )
        try:
            await limiter.check(
                email=f"{principal.user_id}:{campaign_id}",
                client_ip=(
                    f"{request.client.host if request.client else 'unknown'}:"
                    f"{campaign_id}"
                ),
            )
        except RateLimitUnavailableError:
            logger.warning(
                "voting_rate_limit_unavailable",
                extra={
                    "campaign_id": str(campaign_id),
                    "user_id": str(principal.user_id),
                    "outcome": "degraded",
                },
            )
    finally:
        await redis_client.aclose()
