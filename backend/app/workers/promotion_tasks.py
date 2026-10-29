import asyncio
from uuid import UUID

from sqlalchemy import select

from app.db.session import get_session_factory
from app.modules.promotions.distribution import PromotionDistributionService
from app.modules.promotions.distribution_models import PromotionDistributionJob
from app.workers.celery_app import celery_app


async def process_distribution_jobs(*, job_id: UUID | None = None) -> int:
    async with get_session_factory()() as session:
        query = select(PromotionDistributionJob.id).where(
            PromotionDistributionJob.status.in_(["PENDING", "RUNNING", "PAUSED"])
        )
        if job_id is not None:
            query = query.where(PromotionDistributionJob.id == job_id)
        ids = list(
            await session.scalars(
                query.order_by(PromotionDistributionJob.created_at).limit(20)
            )
        )
    completed = 0
    for candidate in ids:
        for _ in range(10):
            async with get_session_factory()() as session:
                if await PromotionDistributionService(session).run_batch(candidate):
                    completed += 1
                    break
    return completed


@celery_app.task(autoretry_for=(ConnectionError,), max_retries=3, retry_backoff=True)  # type: ignore[untyped-decorator]
def distribute_promotions(job_id: str | None = None) -> int:
    return asyncio.run(
        process_distribution_jobs(job_id=UUID(job_id) if job_id else None)
    )


async def _notify_expiring() -> int:
    from app.modules.promotions.reminders import notify_expiring_vouchers

    async with get_session_factory()() as session:
        return await notify_expiring_vouchers(session)


@celery_app.task  # type: ignore[untyped-decorator]
def notify_expiring_promotions() -> int:
    return asyncio.run(_notify_expiring())
