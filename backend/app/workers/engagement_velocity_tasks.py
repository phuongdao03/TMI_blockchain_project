import asyncio
import logging
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy.exc import OperationalError

from app.db.session import get_session_factory
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _generate_engagement_velocity_snapshot(
    now: datetime | None = None,
    as_of_date: date | None = None,
) -> UUID | None:
    from app.modules.audit.service import AuditService
    from app.modules.engagement.velocity_repository import EngagementVelocityRepository
    from app.modules.engagement.velocity_service import EngagementVelocityService

    async with get_session_factory()() as session:
        snapshot = await EngagementVelocityService(
            session,
            repository=EngagementVelocityRepository(session),
            audit=AuditService(session),
        ).create(
            now=now or datetime.now(UTC),
            as_of_date=as_of_date,
        )
        return snapshot.id if snapshot is not None else None


@celery_app.task(  # type: ignore[untyped-decorator]
    name="app.workers.engagement_velocity_tasks.generate_engagement_velocity_snapshot",
    autoretry_for=(OperationalError,),
    max_retries=5,
    retry_backoff=True,
    retry_jitter=True,
)
def generate_engagement_velocity_snapshot(
    now: str | None = None,
    as_of_date: str | None = None,
) -> str | None:
    normalized_now: datetime | None = None
    normalized_date: date | None = None
    if now is not None:
        try:
            normalized_now = datetime.fromisoformat(now)
        except ValueError as error:
            raise ValueError("now must be a valid ISO-8601 datetime") from error
    if as_of_date is not None:
        try:
            normalized_date = date.fromisoformat(as_of_date)
        except ValueError as error:
            raise ValueError("as_of_date must be a valid ISO-8601 date") from error
    try:
        snapshot_id = asyncio.run(
            _generate_engagement_velocity_snapshot(normalized_now, normalized_date)
        )
    except Exception as error:
        logger.exception(
            "engagement_velocity_snapshot_job_failed",
            extra={
                "action": "engagement.velocity.snapshot",
                "error_code": type(error).__name__,
                "outcome": "failure",
            },
        )
        raise
    logger.info(
        "engagement_velocity_snapshot_job_completed",
        extra={
            "action": "engagement.velocity.snapshot",
            "snapshot_id": str(snapshot_id) if snapshot_id is not None else None,
            "outcome": "created" if snapshot_id is not None else "noop",
        },
    )
    return str(snapshot_id) if snapshot_id is not None else None
