import asyncio
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.modules.ranking.repository import RankingSnapshotRepository
from app.modules.ranking.service import YearlyRankingService
from app.modules.voting.models import PeriodType
from app.workers import ranking_tasks
from app.workers.celery_app import celery_app

FIRST_YEAR_ID = UUID("30000000-0000-0000-0000-000000000001")
SECOND_YEAR_ID = UUID("30000000-0000-0000-0000-000000000002")
THIRD_YEAR_ID = UUID("30000000-0000-0000-0000-000000000003")


class FakeYearlyRankingRepository:
    def __init__(self, campaign_ids: tuple[UUID, ...]) -> None:
        self.campaign_ids = campaign_ids
        self.received_limit: int | None = None
        self.received_period_type: PeriodType | None = None

    async def list_pending_periodic_campaign_ids(
        self, *, period_type: PeriodType, limit: int
    ) -> tuple[UUID, ...]:
        self.received_limit = limit
        self.received_period_type = period_type
        return self.campaign_ids[:limit]


def test_yearly_service_enqueues_bounded_pending_campaigns() -> None:
    repository = FakeYearlyRankingRepository((FIRST_YEAR_ID, SECOND_YEAR_ID))
    enqueued: list[UUID] = []

    count = asyncio.run(
        YearlyRankingService(repository, enqueue=enqueued.append).reconcile(limit=1)
    )

    assert count == 1
    assert repository.received_limit == 1
    assert repository.received_period_type == PeriodType.YEARLY
    assert enqueued == [FIRST_YEAR_ID]


def test_yearly_service_rejects_invalid_batch_limit() -> None:
    repository = FakeYearlyRankingRepository(())

    with pytest.raises(ValueError, match="limit"):
        asyncio.run(
            YearlyRankingService(
                repository, enqueue=lambda _campaign_id: None
            ).reconcile(limit=0)
        )

    assert repository.received_limit is None


def test_repository_lists_only_closed_yearly_campaigns_without_snapshot(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'yearly.sqlite3').as_posix()}"
        )
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "CREATE TABLE voting_campaigns ("
                    "id CHAR(32) PRIMARY KEY, status VARCHAR(32) NOT NULL, "
                    "campaign_type VARCHAR(32) NOT NULL, "
                    "period_type VARCHAR(32) NOT NULL, end_at DATETIME NOT NULL)"
                )
            )
            await connection.execute(
                text(
                    "CREATE TABLE ranking_snapshots ("
                    "id CHAR(32) PRIMARY KEY, campaign_id CHAR(32) NOT NULL, "
                    "version BIGINT NOT NULL)"
                )
            )
            campaigns = (
                (FIRST_YEAR_ID, "ENDED", "PERIODIC", "YEARLY", "2027-01-01"),
                (
                    SECOND_YEAR_ID,
                    "RESULT_PENDING",
                    "PERIODIC",
                    "YEARLY",
                    "2028-01-01",
                ),
                (
                    THIRD_YEAR_ID,
                    "PUBLISHED",
                    "PERIODIC",
                    "YEARLY",
                    "2029-01-01",
                ),
                (UUID(int=4), "ENDED", "PERIODIC", "MONTHLY", "2027-01-01"),
                (UUID(int=5), "ENDED", "PERIODIC", "QUARTERLY", "2027-01-01"),
                (UUID(int=6), "ACTIVE", "PERIODIC", "YEARLY", "2027-01-01"),
                (UUID(int=7), "ENDED", "SPECIAL", "CUSTOM", "2027-01-01"),
            )
            for campaign_id, status, campaign_type, period_type, end_at in campaigns:
                await connection.execute(
                    text(
                        "INSERT INTO voting_campaigns VALUES "
                        "(:id, :status, :campaign_type, :period_type, :end_at)"
                    ),
                    {
                        "id": campaign_id.hex,
                        "status": status,
                        "campaign_type": campaign_type,
                        "period_type": period_type,
                        "end_at": end_at,
                    },
                )
            await connection.execute(
                text("INSERT INTO ranking_snapshots VALUES (:id, :campaign_id, 1)"),
                {"id": UUID(int=8).hex, "campaign_id": SECOND_YEAR_ID.hex},
            )

        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            campaign_ids = await RankingSnapshotRepository(
                session
            ).list_pending_yearly_campaign_ids(limit=10)

        assert campaign_ids == (FIRST_YEAR_ID, THIRD_YEAR_ID)
        await engine.dispose()

    asyncio.run(exercise())


def test_yearly_worker_and_hourly_schedule_are_registered(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_reconcile() -> int:
        return 2

    monkeypatch.setattr(ranking_tasks, "_reconcile_yearly_rankings", fake_reconcile)

    assert ranking_tasks.reconcile_yearly_rankings.run() == 2
    assert ranking_tasks.reconcile_yearly_rankings.max_retries == 5
    schedule = celery_app.conf.beat_schedule["reconcile-yearly-rankings"]
    assert schedule["task"] == ranking_tasks.reconcile_yearly_rankings.name
    assert schedule["schedule"] == 3600.0
