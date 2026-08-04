import asyncio
import logging
from collections.abc import Mapping
from uuid import UUID

from sqlalchemy.exc import OperationalError

from app.db.session import get_session_factory
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _generate_ranking_snapshot(campaign_id: UUID) -> UUID | None:
    # Keep domain imports local so loading the Celery registry does not mutate
    # SQLAlchemy metadata in workers/tests that do not load the ranking module.
    from app.modules.audit.service import AuditService
    from app.modules.ranking.repository import (
        RankingRepository,
        RankingSnapshotRepository,
    )
    from app.modules.ranking.service import RankingService
    from app.modules.ranking.snapshot import RankingSnapshotService

    async with get_session_factory()() as session:
        draft = await RankingSnapshotService(
            RankingService(RankingRepository(session)),
            RankingSnapshotRepository(session),
            audit=AuditService(session),
        ).create_initial(
            campaign_id,
            request_id=f"ranking-job:{campaign_id}",
        )
        return draft.id if draft is not None else None


async def _recount_ranking_snapshot(
    campaign_id: UUID,
    *,
    actor_user_id: UUID | None,
    request_id: str | None,
) -> UUID:
    from app.modules.audit.service import AuditService
    from app.modules.ranking.repository import (
        RankingRepository,
        RankingSnapshotRepository,
    )
    from app.modules.ranking.service import RankingService
    from app.modules.ranking.snapshot import RankingSnapshotService

    async with get_session_factory()() as session:
        draft = await RankingSnapshotService(
            RankingService(RankingRepository(session)),
            RankingSnapshotRepository(session),
            audit=AuditService(session),
        ).recount(
            campaign_id,
            actor_user_id=actor_user_id,
            request_id=request_id,
        )
        return draft.id


async def _reconcile_monthly_rankings() -> int:
    from app.modules.ranking.repository import RankingSnapshotRepository
    from app.modules.ranking.service import MonthlyRankingService

    def enqueue(campaign_id: UUID) -> None:
        generate_ranking_snapshot.delay(str(campaign_id))

    async with get_session_factory()() as session:
        return await MonthlyRankingService(
            RankingSnapshotRepository(session),
            enqueue=enqueue,
        ).reconcile()


async def _reconcile_quarterly_rankings() -> int:
    from app.modules.ranking.repository import RankingSnapshotRepository
    from app.modules.ranking.service import QuarterlyRankingService

    def enqueue(campaign_id: UUID) -> None:
        generate_ranking_snapshot.delay(str(campaign_id))

    async with get_session_factory()() as session:
        return await QuarterlyRankingService(
            RankingSnapshotRepository(session),
            enqueue=enqueue,
        ).reconcile()


async def _reconcile_yearly_rankings() -> int:
    from app.modules.ranking.repository import RankingSnapshotRepository
    from app.modules.ranking.service import YearlyRankingService

    def enqueue(campaign_id: UUID) -> None:
        generate_ranking_snapshot.delay(str(campaign_id))

    async with get_session_factory()() as session:
        return await YearlyRankingService(
            RankingSnapshotRepository(session),
            enqueue=enqueue,
        ).reconcile()


@celery_app.task(  # type: ignore[untyped-decorator]
    name="app.workers.ranking_tasks.generate_ranking_snapshot",
    autoretry_for=(OperationalError,),
    max_retries=5,
    retry_backoff=True,
    retry_jitter=True,
)
def generate_ranking_snapshot(campaign_id: str) -> str | None:
    try:
        normalized_campaign_id = UUID(campaign_id)
    except (TypeError, ValueError, AttributeError) as error:
        raise ValueError("campaign_id must be a valid UUID") from error
    try:
        snapshot_id = asyncio.run(_generate_ranking_snapshot(normalized_campaign_id))
    except Exception as error:
        logger.exception(
            "ranking_snapshot_job_failed",
            extra={
                "action": "generate_initial_snapshot",
                "campaign_id": str(normalized_campaign_id),
                "error_code": type(error).__name__,
                "outcome": "failure",
            },
        )
        raise
    logger.info(
        "ranking_snapshot_job_completed",
        extra={
            "action": "generate_initial_snapshot",
            "campaign_id": str(normalized_campaign_id),
            "snapshot_id": str(snapshot_id) if snapshot_id is not None else None,
            "outcome": "created" if snapshot_id is not None else "noop",
        },
    )
    return str(snapshot_id) if snapshot_id is not None else None


@celery_app.task(  # type: ignore[untyped-decorator]
    name="app.workers.ranking_tasks.recount_ranking_snapshot",
    autoretry_for=(OperationalError,),
    max_retries=5,
    retry_backoff=True,
    retry_jitter=True,
)
def recount_ranking_snapshot(
    campaign_id: str,
    *,
    actor_user_id: str | None = None,
    request_id: str | None = None,
) -> str:
    try:
        normalized_campaign_id = UUID(campaign_id)
        normalized_actor_user_id = (
            UUID(actor_user_id) if actor_user_id is not None else None
        )
    except (TypeError, ValueError, AttributeError) as error:
        raise ValueError(
            "campaign and actor identifiers must be valid UUIDs"
        ) from error
    try:
        snapshot_id = asyncio.run(
            _recount_ranking_snapshot(
                normalized_campaign_id,
                actor_user_id=normalized_actor_user_id,
                request_id=request_id,
            )
        )
    except Exception as error:
        logger.exception(
            "ranking_recount_job_failed",
            extra={
                "action": "recount_snapshot",
                "campaign_id": str(normalized_campaign_id),
                "error_code": type(error).__name__,
                "outcome": "failure",
            },
        )
        raise
    logger.info(
        "ranking_recount_job_completed",
        extra={
            "action": "recount_snapshot",
            "campaign_id": str(normalized_campaign_id),
            "snapshot_id": str(snapshot_id),
            "outcome": "created",
        },
    )
    return str(snapshot_id)


@celery_app.task(  # type: ignore[untyped-decorator]
    name="app.workers.ranking_tasks.reconcile_monthly_rankings",
    autoretry_for=(OperationalError,),
    max_retries=5,
    retry_backoff=True,
    retry_jitter=True,
)
def reconcile_monthly_rankings() -> int:
    try:
        enqueued_count = asyncio.run(_reconcile_monthly_rankings())
    except Exception as error:
        logger.exception(
            "monthly_ranking_reconciliation_failed",
            extra={
                "action": "reconcile_monthly_rankings",
                "error_code": type(error).__name__,
                "outcome": "failure",
            },
        )
        raise
    logger.info(
        "monthly_ranking_reconciliation_completed",
        extra={
            "action": "reconcile_monthly_rankings",
            "enqueued_count": enqueued_count,
            "outcome": "success",
        },
    )
    return enqueued_count


@celery_app.task(  # type: ignore[untyped-decorator]
    name="app.workers.ranking_tasks.reconcile_quarterly_rankings",
    autoretry_for=(OperationalError,),
    max_retries=5,
    retry_backoff=True,
    retry_jitter=True,
)
def reconcile_quarterly_rankings() -> int:
    try:
        enqueued_count = asyncio.run(_reconcile_quarterly_rankings())
    except Exception as error:
        logger.exception(
            "quarterly_ranking_reconciliation_failed",
            extra={
                "action": "reconcile_quarterly_rankings",
                "error_code": type(error).__name__,
                "outcome": "failure",
            },
        )
        raise
    logger.info(
        "quarterly_ranking_reconciliation_completed",
        extra={
            "action": "reconcile_quarterly_rankings",
            "enqueued_count": enqueued_count,
            "outcome": "success",
        },
    )
    return enqueued_count


@celery_app.task(  # type: ignore[untyped-decorator]
    name="app.workers.ranking_tasks.reconcile_yearly_rankings",
    autoretry_for=(OperationalError,),
    max_retries=5,
    retry_backoff=True,
    retry_jitter=True,
)
def reconcile_yearly_rankings() -> int:
    try:
        enqueued_count = asyncio.run(_reconcile_yearly_rankings())
    except Exception as error:
        logger.exception(
            "yearly_ranking_reconciliation_failed",
            extra={
                "action": "reconcile_yearly_rankings",
                "error_code": type(error).__name__,
                "outcome": "failure",
            },
        )
        raise
    logger.info(
        "yearly_ranking_reconciliation_completed",
        extra={
            "action": "reconcile_yearly_rankings",
            "enqueued_count": enqueued_count,
            "outcome": "success",
        },
    )
    return enqueued_count


def enqueue_ranking_for_campaign_event(
    *,
    event_type: str,
    payload: Mapping[str, object],
) -> bool:
    if event_type != "voting.campaign.ended" or payload.get("status") != "ENDED":
        return False
    campaign_value = payload.get("campaign_id")
    if not isinstance(campaign_value, str):
        return False
    try:
        campaign_id = UUID(campaign_value)
    except ValueError:
        return False
    generate_ranking_snapshot.delay(str(campaign_id))
    return True
