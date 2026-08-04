import asyncio
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from app.modules.ranking.trending_formula import TrendingCandidate, calculate_trending
from app.modules.ranking.trending_models import TrendingSnapshot
from app.modules.ranking.trending_service import TrendingCalculator
from app.modules.ranking.trending_snapshot import (
    TrendingSnapshotService,
    create_trending_snapshot_draft,
)
from app.modules.ranking.trending_types import (
    TrendingRun,
    TrendingSnapshotDraft,
    TrendingWindow,
)

WINDOW_END = datetime(2026, 8, 3, 8, 37, tzinfo=UTC)
WORK_ID = UUID("53000000-0000-0000-0000-000000000001")
CATEGORY_ID = UUID("54000000-0000-0000-0000-000000000001")


def test_trending_snapshot_uses_floored_hour_and_auditable_digests() -> None:
    class FakeRepository:
        async def list_candidates(
            self, *, window: TrendingWindow
        ) -> tuple[TrendingCandidate, ...]:
            assert window.window_end == datetime(2026, 8, 3, 8, tzinfo=UTC)
            assert window.window_start == datetime(2026, 7, 27, 8, tzinfo=UTC)
            return (TrendingCandidate(WORK_ID, CATEGORY_ID, 4),)

    run = asyncio.run(
        TrendingCalculator(FakeRepository()).calculate(window_end=WINDOW_END)
    )
    first = create_trending_snapshot_draft(run, created_at=WINDOW_END)
    second = create_trending_snapshot_draft(run, created_at=WINDOW_END)

    assert first.source_digest == second.source_digest
    assert first.result_digest == second.result_digest
    assert first.candidate_count == 1
    assert first.total_score == 4
    assert first.items[0].rank == 1


def test_trending_snapshot_service_is_idempotent_for_window() -> None:
    class FakeCalculator:
        async def calculate(self, *, window_end: datetime) -> TrendingRun:
            return TrendingRun(
                window=TrendingWindow(
                    datetime(2026, 7, 27, 8, tzinfo=UTC),
                    datetime(2026, 8, 3, 8, tzinfo=UTC),
                ),
                calculation=calculate_trending(()),
            )

    class FakeSnapshotRepository:
        committed = False

        async def get_by_window(
            self,
            *,
            window_start: datetime,
            window_end: datetime,
        ) -> TrendingSnapshot | None:
            return cast(TrendingSnapshot, object())

        async def add(self, draft: TrendingSnapshotDraft) -> bool:
            raise AssertionError(f"snapshot must not be added: {draft}")

        async def commit(self) -> None:
            self.committed = True

    class FakeAudit:
        def record(self, **values: object) -> object:
            raise AssertionError(f"audit must not be recorded: {values}")

    repository = FakeSnapshotRepository()
    result = asyncio.run(
        TrendingSnapshotService(
            FakeCalculator(),
            repository,
            audit=FakeAudit(),
        ).create(window_end=WINDOW_END)
    )

    assert result is None
    assert repository.committed is True


def test_trending_snapshot_service_persists_and_audits_new_window() -> None:
    class FakeCalculator:
        async def calculate(self, *, window_end: datetime) -> TrendingRun:
            return TrendingRun(
                window=TrendingWindow(
                    datetime(2026, 7, 27, 8, tzinfo=UTC),
                    datetime(2026, 8, 3, 8, tzinfo=UTC),
                ),
                calculation=calculate_trending(
                    (TrendingCandidate(WORK_ID, CATEGORY_ID, 4),)
                ),
            )

    class FakeSnapshotRepository:
        saved: TrendingSnapshotDraft | None = None
        committed = False

        async def get_by_window(
            self,
            *,
            window_start: datetime,
            window_end: datetime,
        ) -> TrendingSnapshot | None:
            return None

        async def add(self, draft: TrendingSnapshotDraft) -> bool:
            self.saved = draft
            return True

        async def commit(self) -> None:
            self.committed = True

    class FakeAudit:
        recorded: dict[str, object] | None = None

        def record(self, **values: object) -> object:
            self.recorded = values
            return None

    repository = FakeSnapshotRepository()
    audit = FakeAudit()
    result = asyncio.run(
        TrendingSnapshotService(
            FakeCalculator(),
            repository,
            audit=audit,
        ).create(window_end=WINDOW_END, created_at=WINDOW_END)
    )

    assert result is not None
    assert repository.saved == result
    assert repository.committed is True
    assert audit.recorded is not None
    assert audit.recorded["action"] == "ranking.trending.snapshot.created"
