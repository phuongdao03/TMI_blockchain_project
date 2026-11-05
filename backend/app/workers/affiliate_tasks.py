"""Background release of manually approved affiliate commissions after hold."""

import asyncio

from app.db.session import get_session_factory
from app.modules.affiliate.service import AffiliateService
from app.workers.celery_app import celery_app


async def _release_matured_commissions() -> int:
    async with get_session_factory()() as session:
        return await AffiliateService(session).release_matured_commissions()


@celery_app.task(  # type: ignore[untyped-decorator]
    name="app.workers.affiliate_tasks.release_matured_commissions",
    max_retries=0,
)
def release_matured_commissions() -> int:
    """Release only commissions already approved and past their hold window."""
    return asyncio.run(_release_matured_commissions())
