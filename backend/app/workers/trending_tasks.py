import asyncio
import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import OperationalError

from app.db.session import get_session_factory
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _generate_trending_snapshot(
    window_end: datetime | None = None,
) -> UUID | None:
    from app.modules.audit.service import AuditService
    from app.modules.ranking.trending_repository import (
        TrendingRepository,
        TrendingSnapshotRepository,
    )
    from app.modules.ranking.trending_service import TrendingCalculator
    from app.modules.ranking.trending_snapshot import TrendingSnapshotService

    async with get_session_factory()() as session:
        draft = await TrendingSnapshotService(
            TrendingCalculator(TrendingRepository(session)),
            TrendingSnapshotRepository(session),
            audit=AuditService(session),
        ).create(
            window_end=window_end or datetime.now(UTC),
            request_id="trending-job",
        )
        return draft.id if draft is not None else None


@celery_app.task(  # type: ignore[untyped-decorator]
    name="app.workers.trending_tasks.generate_trending_snapshot",
    autoretry_for=(OperationalError,),
    max_retries=5,
    retry_backoff=True,
    retry_jitter=True,
)
def generate_trending_snapshot(window_end: str | None = None) -> str | None:
    normalized_window_end: datetime | None = None
    if window_end is not None:
        try:
            normalized_window_end = datetime.fromisoformat(window_end)
        except ValueError as error:
            raise ValueError("window_end must be a valid ISO-8601 datetime") from error
    try:
        snapshot_id = asyncio.run(_generate_trending_snapshot(normalized_window_end))
    except Exception as error:
        logger.exception(
            "trending_snapshot_job_failed",
            extra={
                "action": "generate_trending_snapshot",
                "error_code": type(error).__name__,
                "outcome": "failure",
            },
        )
        raise
    logger.info(
        "trending_snapshot_job_completed",
        extra={
            "action": "generate_trending_snapshot",
            "snapshot_id": str(snapshot_id) if snapshot_id is not None else None,
            "outcome": "created" if snapshot_id is not None else "noop",
        },
    )
    return str(snapshot_id) if snapshot_id is not None else None
