import asyncio

from sqlalchemy.exc import OperationalError

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.modules.community.admin_service import CommunityAdminService
from app.modules.community.retention import CommunityMediaRetentionService
from app.modules.media.dependencies import get_media_service
from app.workers.celery_app import celery_app


async def _purge_deleted_community_media() -> int:
    async with get_session_factory()() as session:
        async for media_service in get_media_service(session, get_settings()):
            deleted_posts = await CommunityAdminService(
                session
            ).purge_legacy_deleted_posts(media_service, limit=1)
            deleted_assets = await CommunityMediaRetentionService(
                session
            ).purge_deleted_assets(media_service, limit=1)
            return deleted_posts + deleted_assets
    return 0


@celery_app.task(
    autoretry_for=(OperationalError,),
    max_retries=5,
    retry_backoff=True,
    retry_jitter=True,
)  # type: ignore[untyped-decorator]
def purge_deleted_community_media() -> int:
    return asyncio.run(_purge_deleted_community_media())
