import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.core.errors import DomainError
from app.modules.auth.session_service import AuthPrincipal
from app.modules.ranking.formula import RankingCandidate, calculate_rankings
from app.modules.ranking.recount import RankingRecountService
from app.modules.ranking.snapshot import RankingSnapshotService
from app.modules.ranking.types import (
    RankingCampaignSource,
    RankingRun,
    RankingSnapshotDraft,
)
from app.modules.voting.models import CampaignStatus

CAMPAIGN_ID = UUID("30000000-0000-0000-0000-000000000001")
WORK_ID = UUID("40000000-0000-0000-0000-000000000001")
CATEGORY_ID = UUID("40000000-0000-0000-0001-000000000001")
ACTOR_ID = UUID("50000000-0000-0000-0000-000000000001")
NOW = datetime(2026, 8, 3, 8, tzinfo=UTC)


def _run(status: CampaignStatus = CampaignStatus.PUBLISHED) -> RankingRun:
    return RankingRun(
        campaign=RankingCampaignSource(
            campaign_id=CAMPAIGN_ID,
            status=status,
            rule_version=7,
            end_at=NOW,
        ),
        calculation=calculate_rankings(
            (RankingCandidate(WORK_ID, CATEGORY_ID, 4),)
        ),
    )


class FakeCalculator:
    async def calculate(self, campaign_id: UUID) -> RankingRun:
        assert campaign_id == CAMPAIGN_ID
        return _run()


class FakeSnapshotRepository:
    saved: RankingSnapshotDraft | None = None
    committed = False

    async def next_version(self, campaign_id: UUID) -> int:
        assert campaign_id == CAMPAIGN_ID
        return 4

    async def add(self, draft: RankingSnapshotDraft) -> None:
        self.saved = draft

    async def commit(self) -> None:
        self.committed = True


class FakeAudit:
    recorded: dict[str, object] | None = None

    def record(self, **values: object) -> None:
        self.recorded = values


def test_recount_creates_next_snapshot_version_and_records_actor() -> None:
    repository = FakeSnapshotRepository()
    audit = FakeAudit()
    result = asyncio.run(
        RankingSnapshotService(FakeCalculator(), repository, audit=audit).recount(
            CAMPAIGN_ID,
            actor_user_id=ACTOR_ID,
            created_at=NOW,
            request_id="request-1812",
        )
    )

    assert result.version == 4
    assert repository.saved == result
    assert repository.committed is True
    assert audit.recorded is not None
    assert audit.recorded["action"] == "ranking.snapshot.recounted"
    assert audit.recorded["actor_user_id"] == ACTOR_ID
    assert audit.recorded["request_id"] == "request-1812"


def test_recount_request_requires_system_admin_and_dispatches_context() -> None:
    dispatched: list[tuple[UUID, UUID, str | None]] = []

    def enqueue(campaign_id: UUID, actor_user_id: UUID, request_id: str | None) -> None:
        dispatched.append((campaign_id, actor_user_id, request_id))

    service = RankingRecountService(enqueue=enqueue)
    principal = AuthPrincipal(
        user_id=ACTOR_ID,
        session_id=uuid4(),
        email="admin@tmigroup.vn",
        roles=("SUPER_ADMIN",),
    )

    result = asyncio.run(
        service.request(
            principal,
            CAMPAIGN_ID,
            request_id="request-1812",
        )
    )

    assert result.status == "queued"
    assert result.campaign_id == CAMPAIGN_ID
    assert dispatched == [(CAMPAIGN_ID, ACTOR_ID, "request-1812")]


def test_recount_request_rejects_non_system_admin() -> None:
    service = RankingRecountService(enqueue=lambda *_: None)
    principal = AuthPrincipal(
        user_id=ACTOR_ID,
        session_id=uuid4(),
        email="content@tmigroup.vn",
        roles=("CONTENT_ADMIN",),
    )

    with pytest.raises(DomainError) as error:
        asyncio.run(service.request(principal, CAMPAIGN_ID))

    assert error.value.code == "RANKING_RECOUNT_FORBIDDEN"
    assert error.value.status_code == 403
