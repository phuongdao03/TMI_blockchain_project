import asyncio
import logging
from datetime import UTC, date, datetime

from sqlalchemy.exc import OperationalError

from app.db.session import get_session_factory
from app.modules.engagement.analytics_repository import EngagementAnalyticsRepository
from app.modules.engagement.analytics_service import EngagementAnalyticsService
from app.modules.engagement.telemetry import engagement_analytics_telemetry
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _generate_daily_engagement_snapshot(
    *,
    now: datetime,
    metric_date: date | None,
) -> str | None:
    from app.modules.audit.service import AuditService

    async with get_session_factory()() as session:
        snapshot = await EngagementAnalyticsService(
            session,
            repository=EngagementAnalyticsRepository(session),
            audit=AuditService(session),
            telemetry=engagement_analytics_telemetry,
        ).snapshot(now=now, metric_date=metric_date)
        return str(snapshot.id) if snapshot is not None else None


@celery_app.task(  # type: ignore[untyped-decorator]
    name="app.workers.engagement_tasks.generate_daily_engagement_snapshot",
    autoretry_for=(OperationalError,),
    max_retries=5,
    retry_backoff=True,
    retry_jitter=True,
)
def generate_daily_engagement_snapshot(
    now: str | None = None,
    metric_date: str | None = None,
) -> str | None:
    normalized_now = datetime.now(UTC) if now is None else _parse_datetime(now)
    normalized_date = None if metric_date is None else _parse_date(metric_date)
    try:
        snapshot_id = asyncio.run(
            _generate_daily_engagement_snapshot(
                now=normalized_now,
                metric_date=normalized_date,
            )
        )
    except Exception as error:
        logger.exception(
            "engagement_analytics_snapshot_job_failed",
            extra={
                "action": "engagement.analytics.snapshot",
                "error_code": type(error).__name__,
                "outcome": "failure",
            },
        )
        raise
    logger.info(
        "engagement_analytics_snapshot_job_completed",
        extra={
            "action": "engagement.analytics.snapshot",
            "snapshot_id": snapshot_id,
            "outcome": "created" if snapshot_id is not None else "noop",
        },
    )
    return snapshot_id


def _parse_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError("now must be a valid ISO-8601 datetime") from error
    return (
        parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
    )


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ValueError("metric_date must be a valid ISO-8601 date") from error
