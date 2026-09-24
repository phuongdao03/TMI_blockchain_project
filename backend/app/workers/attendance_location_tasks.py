import asyncio

from sqlalchemy.exc import OperationalError

from app.db.session import get_session_factory
from app.modules.hr.service import HrService
from app.workers.celery_app import celery_app


async def _purge_expired_attendance_locations() -> int:
    async with get_session_factory()() as session:
        return await HrService(session).purge_expired_attendance_locations()


@celery_app.task(
    autoretry_for=(OperationalError,),
    max_retries=5,
    retry_backoff=True,
    retry_jitter=True,
)  # type: ignore[untyped-decorator]
def purge_expired_attendance_locations() -> int:
    return asyncio.run(_purge_expired_attendance_locations())
