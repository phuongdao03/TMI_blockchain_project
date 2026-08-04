import asyncio
from datetime import UTC, datetime
from uuid import UUID

from app.modules.ranking.formula import RankingCandidate, calculate_rankings
from app.modules.ranking.snapshot import (
    RankingSnapshotService,
    create_snapshot_draft,
)
from app.modules.ranking.types import (
    RankingCampaignSource,
    RankingRun,
    RankingSnapshotDraft,
)
from app.modules.voting.models import CampaignStatus

CAMPAIGN_ID = UUID("30000000-0000-0000-0000-000000000001")
WORK_A = UUID("40000000-0000-0000-0000-000000000001")
WORK_B = UUID("40000000-0000-0000-0000-000000000002")
CATEGORY_ID = UUID("40000000-0000-0000-0001-000000000001")
OTHER_CATEGORY_ID = UUID("40000000-0000-0000-0001-000000000002")
NOW = datetime(2026, 8, 3, 8, tzinfo=UTC)


def _run() -> RankingRun:
    return RankingRun(
        campaign=RankingCampaignSource(
            campaign_id=CAMPAIGN_ID,
            status=CampaignStatus.ENDED,
            rule_version=7,
            end_at=NOW,
        ),
        calculation=calculate_rankings(
            (
                RankingCandidate(WORK_A, CATEGORY_ID, 2),
                RankingCandidate(WORK_B, CATEGORY_ID, 5),
            )
        ),
    )


def test_snapshot_draft_contains_deterministic_audit_digests() -> None:
    first = create_snapshot_draft(_run(), version=1, created_at=NOW)
    second = create_snapshot_draft(_run(), version=2, created_at=NOW)

    assert first.source_digest == second.source_digest
    assert first.result_digest == second.result_digest
    assert len(first.source_digest) == 64
    assert len(first.result_digest) == 64
    assert first.candidate_count == 2
    assert first.total_valid_votes == 7
    assert [item.display_order for item in first.items] == [1, 2]
    assert [item.rank for item in first.items] == [1, 2]
    assert [item.category_id for item in first.items] == [CATEGORY_ID, CATEGORY_ID]
    assert [item.category_rank for item in first.items] == [1, 2]


def test_snapshot_digests_cover_frozen_category_ranking() -> None:
    original = create_snapshot_draft(_run(), version=1, created_at=NOW)
    changed_run = RankingRun(
        campaign=_run().campaign,
        calculation=calculate_rankings(
            (
                RankingCandidate(WORK_A, OTHER_CATEGORY_ID, 2),
                RankingCandidate(WORK_B, CATEGORY_ID, 5),
            )
        ),
    )
    changed = create_snapshot_draft(changed_run, version=1, created_at=NOW)

    assert changed.source_digest != original.source_digest
    assert changed.result_digest != original.result_digest


def test_snapshot_service_persists_and_commits_next_version() -> None:
    class FakeCalculator:
        async def calculate(self, campaign_id: UUID) -> RankingRun:
            assert campaign_id == CAMPAIGN_ID
            return _run()

    class FakeSnapshotRepository:
        saved: RankingSnapshotDraft | None = None
        committed = False

        async def next_version(self, campaign_id: UUID) -> int:
            assert campaign_id == CAMPAIGN_ID
            return 3

        async def add(self, draft: RankingSnapshotDraft) -> None:
            self.saved = draft

        async def commit(self) -> None:
            self.committed = True

    class FakeAudit:
        recorded: dict[str, object] | None = None

        def record(self, **values: object) -> None:
            self.recorded = values

    repository = FakeSnapshotRepository()
    audit = FakeAudit()
    result = asyncio.run(
        RankingSnapshotService(FakeCalculator(), repository, audit=audit).create(
            CAMPAIGN_ID,
            created_at=NOW,
        )
    )

    assert result.version == 3
    assert repository.saved == result
    assert repository.committed is True
    assert audit.recorded is not None
    assert audit.recorded["action"] == "ranking.snapshot.created"
    assert audit.recorded["resource_id"] == str(result.id)
    assert "work" not in str(audit.recorded).lower()


def test_initial_snapshot_is_idempotent_after_first_version() -> None:
    class FakeCalculator:
        async def calculate(self, campaign_id: UUID) -> RankingRun:
            raise AssertionError(f"calculation must not run for {campaign_id}")

    class FakeSnapshotRepository:
        committed = False

        async def next_version(self, campaign_id: UUID) -> int:
            assert campaign_id == CAMPAIGN_ID
            return 2

        async def add(self, draft: RankingSnapshotDraft) -> None:
            raise AssertionError(f"snapshot must not be added: {draft.id}")

        async def commit(self) -> None:
            self.committed = True

    class FakeAudit:
        def record(self, **values: object) -> None:
            raise AssertionError(f"audit must not be recorded: {values}")

    repository = FakeSnapshotRepository()
    result = asyncio.run(
        RankingSnapshotService(
            FakeCalculator(),
            repository,
            audit=FakeAudit(),
        ).create_initial(CAMPAIGN_ID, created_at=NOW)
    )

    assert result is None
    assert repository.committed is True
