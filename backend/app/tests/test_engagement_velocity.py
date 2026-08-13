import asyncio
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import cast
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.engagement.velocity_formula import (
    calculate_velocity,
)
from app.modules.engagement.velocity_service import EngagementVelocityService
from app.modules.engagement.velocity_types import (
    EngagementVelocityDaily,
    EngagementVelocitySnapshotDraft,
    EngagementVelocitySnapshotView,
)

WORK_A = UUID("00000000-0000-0000-0000-000000000001")
WORK_B = UUID("00000000-0000-0000-0000-000000000002")
CATEGORY = UUID("10000000-0000-0000-0000-000000000001")


def test_velocity_applies_seven_day_decay_and_ignores_older_rows() -> None:
    rows = (
        EngagementVelocityDaily(
            work_id=WORK_A,
            category_id=CATEGORY,
            metric_date=date(2026, 8, 5),
            views=10,
            shares=2,
            qr_scans=1,
            favorites=3,
        ),
        EngagementVelocityDaily(
            work_id=WORK_A,
            category_id=CATEGORY,
            metric_date=date(2026, 8, 4),
            views=1,
            shares=0,
            qr_scans=0,
            favorites=0,
        ),
        EngagementVelocityDaily(
            work_id=WORK_A,
            category_id=CATEGORY,
            metric_date=date(2026, 7, 29),
            views=999,
            shares=999,
            qr_scans=999,
            favorites=999,
        ),
    )

    result = calculate_velocity(rows, as_of_date=date(2026, 8, 5))

    assert result.items[0].score == Decimal("26.82000000")


def test_velocity_ties_use_public_work_uuid_and_competition_ranks() -> None:
    rows = (
        EngagementVelocityDaily(
            work_id=WORK_B,
            category_id=CATEGORY,
            metric_date=date(2026, 8, 5),
            views=1,
            shares=0,
            qr_scans=0,
            favorites=0,
        ),
        EngagementVelocityDaily(
            work_id=WORK_A,
            category_id=CATEGORY,
            metric_date=date(2026, 8, 5),
            views=1,
            shares=0,
            qr_scans=0,
            favorites=0,
        ),
    )

    result = calculate_velocity(rows, as_of_date=date(2026, 8, 5))

    assert [item.work_id for item in result.items] == [WORK_A, WORK_B]
    assert [item.rank for item in result.items] == [1, 1]
    assert [item.display_order for item in result.items] == [1, 2]


class FakeTransaction:
    async def __aenter__(self) -> None:
        return None

    async def __aexit__(self, *args: object) -> None:
        return None


class FakeSession:
    def begin(self) -> FakeTransaction:
        return FakeTransaction()


class FakeRepository:
    def __init__(self) -> None:
        self.existing: EngagementVelocitySnapshotView | None = None
        self.created = 0

    async def get_by_window(
        self,
        *,
        window_start: date,
        window_end: date,
    ) -> EngagementVelocitySnapshotView | None:
        return self.existing

    async def list_daily_candidates(
        self,
        *,
        window_start: date,
        window_end: date,
    ) -> tuple[EngagementVelocityDaily, ...]:
        return (
            EngagementVelocityDaily(
                work_id=WORK_A,
                category_id=CATEGORY,
                metric_date=window_end,
                views=2,
                shares=0,
                qr_scans=0,
                favorites=0,
            ),
        )

    async def add(self, draft: object) -> bool:
        assert isinstance(draft, EngagementVelocitySnapshotDraft)
        if self.existing is not None:
            return False
        self.created += 1
        self.existing = EngagementVelocitySnapshotView(
            id=draft.id,
            window_start=draft.window_start,
            window_end=draft.window_end,
            formula_version=draft.formula_version,
            generated_at=draft.generated_at,
            items=draft.items,
        )
        return True


class FakeAudit:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    def record(self, **event: object) -> None:
        self.events.append(event)


def test_velocity_snapshot_is_idempotent_and_audited() -> None:
    repository = FakeRepository()
    audit = FakeAudit()
    service = EngagementVelocityService(
        cast(AsyncSession, FakeSession()),
        repository=repository,
        audit=audit,
    )
    now = datetime(2026, 8, 6, 0, 10, tzinfo=UTC)

    created = asyncio.run(service.create(now=now))
    rerun = asyncio.run(service.create(now=now))

    assert created is not None
    assert rerun is not None
    assert repository.created == 1
    assert audit.events[0]["action"] == "engagement.velocity.snapshot.created"
