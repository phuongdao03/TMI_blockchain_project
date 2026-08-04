from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from app.core.errors import DomainError
from app.modules.auth.session_service import AuthPrincipal
from app.modules.ranking.ranking_cache import RankingCacheInvalidator
from app.modules.voting.models import CampaignStatus

RANKING_PUBLICATION_ROLES = frozenset({"SUPER_ADMIN"})


@dataclass(frozen=True, slots=True)
class RankingPublicationCampaign:
    id: UUID
    status: CampaignStatus


@dataclass(frozen=True, slots=True)
class RankingPublicationSnapshot:
    id: UUID
    campaign_id: UUID
    version: int


@dataclass(frozen=True, slots=True)
class RankingPublicationResult:
    campaign_id: UUID
    snapshot_id: UUID
    version: int
    published_at: datetime


class RankingPublicationRepositoryPort(Protocol):
    async def get_campaign(
        self, campaign_id: UUID
    ) -> RankingPublicationCampaign | None: ...

    async def get_snapshot(
        self, campaign_id: UUID, version: int
    ) -> RankingPublicationSnapshot | None: ...

    async def publish(
        self, campaign_id: UUID, snapshot_id: UUID, published_at: datetime
    ) -> None: ...

    async def commit(self) -> None: ...


class RankingAuditPort(Protocol):
    def record(
        self,
        *,
        actor_user_id: UUID | None,
        action: str,
        resource_type: str,
        resource_id: str,
        before: dict[str, object] | None = None,
        after: dict[str, object] | None = None,
        request_id: str | None = None,
    ) -> object: ...


class RankingPublicationService:
    def __init__(
        self,
        repository: RankingPublicationRepositoryPort,
        *,
        audit: RankingAuditPort,
        clock: Callable[[], datetime] | None = None,
        cache_invalidator: RankingCacheInvalidator | None = None,
    ) -> None:
        self._repository = repository
        self._audit = audit
        self._clock = clock or (lambda: datetime.now(UTC))
        self._cache_invalidator = cache_invalidator

    async def publish(
        self,
        principal: AuthPrincipal,
        campaign_id: UUID,
        *,
        version: int,
        request_id: str | None = None,
    ) -> RankingPublicationResult:
        if RANKING_PUBLICATION_ROLES.isdisjoint(principal.roles):
            raise DomainError(
                code="RANKING_PUBLICATION_FORBIDDEN",
                message="Ranking publication is forbidden.",
                status_code=403,
            )
        campaign = await self._repository.get_campaign(campaign_id)
        if campaign is None:
            raise DomainError(
                code="RANKING_CAMPAIGN_NOT_FOUND",
                message="Ranking campaign was not found.",
                status_code=404,
            )
        if campaign.status is not CampaignStatus.RESULT_PENDING:
            raise DomainError(
                code="RANKING_PUBLICATION_STATE_INVALID",
                message="Only a pending ranking result can be published.",
                status_code=409,
            )
        snapshot = await self._repository.get_snapshot(campaign_id, version)
        if snapshot is None:
            raise DomainError(
                code="RANKING_SNAPSHOT_NOT_FOUND",
                message="The requested ranking snapshot was not found.",
                status_code=404,
            )
        published_at = self._as_utc(self._clock())
        await self._repository.publish(campaign_id, snapshot.id, published_at)
        self._audit.record(
            actor_user_id=principal.user_id,
            action="ranking.results.published",
            resource_type="voting_campaign",
            resource_id=str(campaign_id),
            after={
                "campaign_id": str(campaign_id),
                "snapshot_id": str(snapshot.id),
                "version": snapshot.version,
                "published_at": published_at.isoformat(),
            },
            request_id=request_id,
        )
        await self._repository.commit()
        if self._cache_invalidator is not None:
            await self._cache_invalidator.invalidate(
                reason="ranking.results.published"
            )
        return RankingPublicationResult(
            campaign_id=campaign_id,
            snapshot_id=snapshot.id,
            version=snapshot.version,
            published_at=published_at,
        )

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
