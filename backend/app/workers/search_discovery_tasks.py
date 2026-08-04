import asyncio

from app.db.session import get_session_factory
from app.modules.search.discovery_models import SearchSnapshotPeriod
from app.modules.search.discovery_repository import SearchDiscoveryRepository
from app.modules.search.discovery_service import SearchDiscoveryService
from app.workers.celery_app import celery_app


async def _materialize(period: SearchSnapshotPeriod) -> int:
    async with get_session_factory()() as session:
        return await SearchDiscoveryService(
            SearchDiscoveryRepository(session)
        ).materialize(period=period)


@celery_app.task(  # type: ignore[untyped-decorator]
    name="app.workers.search_discovery_tasks.materialize_hourly_search_discovery"
)
def materialize_hourly_search_discovery() -> int:
    return asyncio.run(_materialize(SearchSnapshotPeriod.HOURLY))


@celery_app.task(  # type: ignore[untyped-decorator]
    name="app.workers.search_discovery_tasks.materialize_daily_search_discovery"
)
def materialize_daily_search_discovery() -> int:
    return asyncio.run(_materialize(SearchSnapshotPeriod.DAILY))
