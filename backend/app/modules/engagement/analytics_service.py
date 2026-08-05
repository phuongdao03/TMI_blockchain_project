import logging
from datetime import UTC, date, datetime, time, timedelta
from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.engagement.analytics_repository import EngagementAnalyticsRepository
from app.modules.engagement.analytics_types import EngagementAnalyticsSnapshotView
from app.modules.engagement.telemetry import (
    EngagementAnalyticsTelemetry,
    engagement_analytics_telemetry,
)

logger = logging.getLogger(__name__)
DAILY_SNAPSHOT_GRACE = timedelta(minutes=10)


class EngagementAnalyticsRepositoryPort(Protocol):
    async def get_snapshot(
        self,
        metric_date: date,
    ) -> EngagementAnalyticsSnapshotView | None: ...

    async def aggregate(self, metric_date: date) -> dict[str, int]: ...

    async def create_snapshot(
        self,
        *,
        metric_date: date,
        metrics: dict[str, int],
    ) -> EngagementAnalyticsSnapshotView: ...


class EngagementAnalyticsAuditPort(Protocol):
    def record(
        self,
        *,
        actor_user_id: UUID | None,
        action: str,
        resource_type: str,
        resource_id: str,
        after: dict[str, object] | None = None,
        request_id: str | None = None,
    ) -> object: ...


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def eligible_metric_date(*, now: datetime) -> date | None:
    normalized = _as_utc(now)
    metric_date = normalized.date() - timedelta(days=1)
    eligible_at = datetime.combine(
        metric_date + timedelta(days=1),
        time.min,
        tzinfo=UTC,
    ) + DAILY_SNAPSHOT_GRACE
    return metric_date if normalized >= eligible_at else None


class EngagementAnalyticsService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        repository: EngagementAnalyticsRepositoryPort | None = None,
        audit: EngagementAnalyticsAuditPort,
        telemetry: EngagementAnalyticsTelemetry | None = None,
    ) -> None:
        self._session = session
        self._repository = repository or EngagementAnalyticsRepository(session)
        self._audit = audit
        self._telemetry = telemetry or engagement_analytics_telemetry

    async def snapshot(
        self,
        *,
        now: datetime,
        metric_date: date | None = None,
    ) -> EngagementAnalyticsSnapshotView | None:
        normalized_now = _as_utc(now)
        target_date = metric_date or eligible_metric_date(now=normalized_now)
        if target_date is None:
            self._telemetry.record("not_ready")
            return None
        eligible_at = datetime.combine(
            target_date + timedelta(days=1),
            time.min,
            tzinfo=UTC,
        ) + DAILY_SNAPSHOT_GRACE
        if normalized_now < eligible_at:
            self._telemetry.record("not_ready")
            return None

        async with self._session.begin():
            existing = await self._repository.get_snapshot(target_date)
            if existing is not None:
                self._telemetry.record("noop")
                return existing
            metrics = await self._repository.aggregate(target_date)
            snapshot = await self._repository.create_snapshot(
                metric_date=target_date,
                metrics=metrics,
            )
            self._audit.record(
                actor_user_id=None,
                action="engagement.analytics.snapshot.created",
                resource_type="engagement_analytics_snapshot",
                resource_id=target_date.isoformat(),
                after={**metrics, "metric_date": target_date.isoformat()},
                request_id=f"engagement-analytics:{target_date.isoformat()}",
            )
            self._telemetry.record("created")
            logger.info(
                "engagement_analytics_snapshot_created",
                extra={
                    "action": "engagement.analytics.snapshot.created",
                    "metric_date": target_date.isoformat(),
                    "outcome": "created",
                },
            )
            return snapshot
