import asyncio
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.modules.ranking.repository import RankingSnapshotRepository
from app.modules.ranking.service import MonthlyRankingService
from app.modules.voting.models import PeriodType
from app.workers import ranking_tasks
from app.workers.celery_app import celery_app

JANUARY_ID = UUID("10000000-0000-0000-0000-000000000001")
FEBRUARY_ID = UUID("10000000-0000-0000-0000-000000000002")
MARCH_ID = UUID("10000000-0000-0000-0000-000000000003")


class FakeMonthlyRankingRepository:
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


def test_monthly_service_enqueues_bounded_pending_campaigns() -> None:
    repository = FakeMonthlyRankingRepository((JANUARY_ID, FEBRUARY_ID))
    enqueued: list[UUID] = []

    count = asyncio.run(
        MonthlyRankingService(repository, enqueue=enqueued.append).reconcile(limit=1)
    )

    assert count == 1
    assert repository.received_limit == 1
    assert repository.received_period_type == PeriodType.MONTHLY
    assert enqueued == [JANUARY_ID]


def test_monthly_service_rejects_invalid_batch_limit() -> None:
    repository = FakeMonthlyRankingRepository(())

    with pytest.raises(ValueError, match="limit"):
        asyncio.run(
            MonthlyRankingService(
                repository, enqueue=lambda _campaign_id: None
            ).reconcile(limit=0)
        )

    assert repository.received_limit is None


def test_repository_lists_only_closed_monthly_campaigns_without_snapshot(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'monthly.sqlite3').as_posix()}"
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
                (JANUARY_ID, "ENDED", "PERIODIC", "MONTHLY", "2026-02-01"),
                (FEBRUARY_ID, "RESULT_PENDING", "PERIODIC", "MONTHLY", "2026-03-01"),
                (MARCH_ID, "PUBLISHED", "PERIODIC", "MONTHLY", "2026-04-01"),
                (UUID(int=4), "ENDED", "PERIODIC", "YEARLY", "2026-01-01"),
                (UUID(int=5), "ENDED", "SPECIAL", "CUSTOM", "2026-01-01"),
                (UUID(int=6), "ACTIVE", "PERIODIC", "MONTHLY", "2026-01-01"),
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
                {"id": UUID(int=7).hex, "campaign_id": FEBRUARY_ID.hex},
            )

        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            campaign_ids = await RankingSnapshotRepository(
                session
            ).list_pending_monthly_campaign_ids(limit=10)

        assert campaign_ids == (JANUARY_ID, MARCH_ID)
        await engine.dispose()

    asyncio.run(exercise())


def test_monthly_worker_and_hourly_schedule_are_registered(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_reconcile() -> int:
        return 2

    monkeypatch.setattr(ranking_tasks, "_reconcile_monthly_rankings", fake_reconcile)

    assert ranking_tasks.reconcile_monthly_rankings.run() == 2
    assert ranking_tasks.reconcile_monthly_rankings.max_retries == 5
    schedule = celery_app.conf.beat_schedule["reconcile-monthly-rankings"]
    assert schedule["task"] == ranking_tasks.reconcile_monthly_rankings.name
    assert schedule["schedule"] == 3600.0
