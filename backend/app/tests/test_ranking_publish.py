import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.core.errors import DomainError
from app.modules.auth.session_service import AuthPrincipal
from app.modules.ranking.publish import (
    RankingPublicationCampaign,
    RankingPublicationService,
    RankingPublicationSnapshot,
)
from app.modules.voting.models import CampaignStatus

CAMPAIGN_ID = UUID("30000000-0000-0000-0000-000000000001")
SNAPSHOT_ID = UUID("60000000-0000-0000-0000-000000000001")
ACTOR_ID = UUID("50000000-0000-0000-0000-000000000001")
NOW = datetime(2026, 8, 3, 8, tzinfo=UTC)


class FakePublicationRepository:
    def __init__(self, status: CampaignStatus = CampaignStatus.RESULT_PENDING) -> None:
        self.campaign = RankingPublicationCampaign(CAMPAIGN_ID, status)
        self.snapshot = RankingPublicationSnapshot(SNAPSHOT_ID, CAMPAIGN_ID, 3)
        self.published: tuple[UUID, UUID, datetime] | None = None
        self.committed = False

    async def get_campaign(
        self, campaign_id: UUID
    ) -> RankingPublicationCampaign | None:
        return self.campaign if campaign_id == CAMPAIGN_ID else None

    async def get_snapshot(
        self, campaign_id: UUID, version: int
    ) -> RankingPublicationSnapshot | None:
        if campaign_id == CAMPAIGN_ID and version == self.snapshot.version:
            return self.snapshot
        return None

    async def publish(
        self, campaign_id: UUID, snapshot_id: UUID, published_at: datetime
    ) -> None:
        self.published = (campaign_id, snapshot_id, published_at)

    async def commit(self) -> None:
        self.committed = True


class FakeAudit:
    recorded: dict[str, object] | None = None

    def record(self, **values: object) -> None:
        self.recorded = values


class RecordingInvalidator:
    def __init__(self) -> None:
        self.reasons: list[str] = []

    async def invalidate(self, *, reason: str) -> int:
        self.reasons.append(reason)
        return len(self.reasons)


def _principal(roles: tuple[str, ...] = ("SUPER_ADMIN",)) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=ACTOR_ID,
        session_id=uuid4(),
        email="admin@tmigroup.vn",
        roles=roles,
    )


def test_publish_selects_snapshot_and_transitions_campaign() -> None:
    repository = FakePublicationRepository()
    audit = FakeAudit()
    invalidator = RecordingInvalidator()
    result = asyncio.run(
        RankingPublicationService(
            repository,
            audit=audit,
            clock=lambda: NOW,
            cache_invalidator=invalidator,
        ).publish(
            _principal(),
            CAMPAIGN_ID,
            version=3,
            request_id="request-1813",
        )
    )

    assert result.campaign_id == CAMPAIGN_ID
    assert result.snapshot_id == SNAPSHOT_ID
    assert result.version == 3
    assert result.published_at == NOW
    assert repository.published == (CAMPAIGN_ID, SNAPSHOT_ID, NOW)
    assert repository.committed is True
    assert audit.recorded is not None
    assert audit.recorded["action"] == "ranking.results.published"
    assert audit.recorded["actor_user_id"] == ACTOR_ID
    assert audit.recorded["request_id"] == "request-1813"
    assert invalidator.reasons == ["ranking.results.published"]


def test_publish_rejects_non_system_admin() -> None:
    repository = FakePublicationRepository()
    with pytest.raises(DomainError) as error:
        asyncio.run(
            RankingPublicationService(repository, audit=FakeAudit()).publish(
                _principal(("CONTENT_ADMIN",)), CAMPAIGN_ID, version=3
            )
        )

    assert error.value.code == "RANKING_PUBLICATION_FORBIDDEN"
    assert error.value.status_code == 403


def test_publish_rejects_campaign_not_pending() -> None:
    repository = FakePublicationRepository(CampaignStatus.PUBLISHED)
    with pytest.raises(DomainError) as error:
        asyncio.run(
            RankingPublicationService(repository, audit=FakeAudit()).publish(
                _principal(), CAMPAIGN_ID, version=3
            )
        )

    assert error.value.code == "RANKING_PUBLICATION_STATE_INVALID"
    assert error.value.status_code == 409
