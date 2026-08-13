import asyncio
from datetime import UTC, date, datetime, timedelta
from typing import cast
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.engagement.analytics_service import (
    DAILY_SNAPSHOT_GRACE,
    EngagementAnalyticsService,
    eligible_metric_date,
)
from app.modules.engagement.analytics_types import EngagementAnalyticsSnapshotView
from app.modules.engagement.telemetry import EngagementAnalyticsTelemetry


class FakeTransaction:
    async def __aenter__(self) -> None:
        return None

    async def __aexit__(self, *args: object) -> None:
        return None


class FakeSession:
    def begin(self) -> FakeTransaction:
        return FakeTransaction()


class FakeRepository:
    def __init__(self, existing: EngagementAnalyticsSnapshotView | None = None) -> None:
        self.existing = existing
        self.created: list[tuple[date, dict[str, int]]] = []

    async def get_snapshot(
        self,
        metric_date: date,
    ) -> EngagementAnalyticsSnapshotView | None:
        return self.existing

    async def aggregate(self, metric_date: date) -> dict[str, int]:
        assert metric_date == date(2026, 8, 4)
        return {
            "unique_views": 12,
            "share_events": 3,
            "qr_scans": 4,
            "report_requests": 1,
            "favorite_events": 5,
        }

    async def create_snapshot(
        self,
        *,
        metric_date: date,
        metrics: dict[str, int],
    ) -> EngagementAnalyticsSnapshotView:
        self.created.append((metric_date, metrics))
        snapshot = EngagementAnalyticsSnapshotView(
            id=UUID("60000000-0000-0000-0000-000000000001"),
            metric_date=metric_date,
            generated_at=datetime(2026, 8, 5, 0, 11, tzinfo=UTC),
            **metrics,
        )
        self.existing = snapshot
        return snapshot


class FakeAudit:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    def record(self, **event: object) -> None:
        self.events.append(event)


def test_daily_window_requires_ten_minute_utc_grace() -> None:
    day = date(2026, 8, 4)
    assert DAILY_SNAPSHOT_GRACE == timedelta(minutes=10)
    assert (
        eligible_metric_date(
            now=datetime(2026, 8, 5, 0, 9, tzinfo=UTC),
        )
        is None
    )
    assert (
        eligible_metric_date(
            now=datetime(2026, 8, 5, 0, 10, tzinfo=UTC),
        )
        == day
    )


def test_snapshot_is_idempotent_and_records_audit_telemetry() -> None:
    repository = FakeRepository()
    audit = FakeAudit()
    telemetry = EngagementAnalyticsTelemetry()
    service = EngagementAnalyticsService(
        cast(AsyncSession, FakeSession()),
        repository=repository,
        audit=audit,
        telemetry=telemetry,
    )
    now = datetime(2026, 8, 5, 0, 10, tzinfo=UTC)

    created = asyncio.run(service.snapshot(now=now))
    rerun = asyncio.run(service.snapshot(now=now))

    assert created is not None
    assert rerun is not None
    assert len(repository.created) == 1
    assert audit.events[0]["action"] == "engagement.analytics.snapshot.created"
    assert telemetry.snapshot() == {"created": 1, "noop": 1}


def test_snapshot_returns_none_before_grace_period() -> None:
    service = EngagementAnalyticsService(
        cast(AsyncSession, FakeSession()),
        repository=FakeRepository(),
        audit=FakeAudit(),
        telemetry=EngagementAnalyticsTelemetry(),
    )

    assert (
        asyncio.run(service.snapshot(now=datetime(2026, 8, 5, 0, 9, tzinfo=UTC)))
        is None
    )
