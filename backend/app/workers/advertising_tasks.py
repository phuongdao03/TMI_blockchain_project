import asyncio

from sqlalchemy.exc import OperationalError

from app.db.session import get_session_factory
from app.modules.advertising.delivery import AdvertisingDeliveryService
from app.modules.advertising.inventory import AdvertisingInventoryService
from app.workers.celery_app import celery_app


async def _expire_advertising_reservations() -> int:
    async with get_session_factory()() as session:
        return await AdvertisingInventoryService(session).expire_holds()


async def _advance_advertising_campaigns() -> int:
    async with get_session_factory()() as session:
        return await AdvertisingDeliveryService(session).advance_lifecycle()


async def _notify_available_advertising_waitlists() -> int:
    async with get_session_factory()() as session:
        return await AdvertisingInventoryService(session).notify_available_waitlists()


@celery_app.task(
    autoretry_for=(OperationalError,),
    max_retries=5,
    retry_backoff=True,
    retry_jitter=True,
)  # type: ignore[untyped-decorator]
def expire_advertising_reservations() -> int:
    return asyncio.run(_expire_advertising_reservations())


@celery_app.task(
    autoretry_for=(OperationalError,),
    max_retries=5,
    retry_backoff=True,
    retry_jitter=True,
)  # type: ignore[untyped-decorator]
def advance_advertising_campaigns() -> int:
    return asyncio.run(_advance_advertising_campaigns())


@celery_app.task(
    autoretry_for=(OperationalError,),
    max_retries=5,
    retry_backoff=True,
    retry_jitter=True,
)  # type: ignore[untyped-decorator]
def notify_available_advertising_waitlists() -> int:
    return asyncio.run(_notify_available_advertising_waitlists())
