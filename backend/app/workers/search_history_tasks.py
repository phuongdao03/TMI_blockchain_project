import asyncio

from sqlalchemy.exc import OperationalError

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.modules.search.history_service import SearchHistoryService
from app.workers.celery_app import celery_app


async def _purge_expired_search_history() -> int:
    settings = get_settings()
    async with get_session_factory()() as session:
        return await SearchHistoryService(
            session,
            retention_days=settings.search_history_retention_days,
            list_limit=settings.search_history_list_limit,
        ).purge_expired()


@celery_app.task(
    autoretry_for=(OperationalError,),
    max_retries=5,
    retry_backoff=True,
    retry_jitter=True,
)  # type: ignore[untyped-decorator]
def purge_expired_search_history() -> int:
    return asyncio.run(_purge_expired_search_history())
