import asyncio
from uuid import UUID

from sqlalchemy.exc import OperationalError

from app.db.session import get_session_factory
from app.modules.reviews.similarity_detection import SimilarityDetectionService
from app.workers.celery_app import celery_app


async def _detect(dossier_version_id: UUID) -> None:
    async with get_session_factory()() as session:
        service = SimilarityDetectionService(session=session)
        await service.detect(dossier_version_id)


@celery_app.task(
    name="app.workers.similarity_tasks.detect_near_duplicate_candidates",
    autoretry_for=(OperationalError,),
    max_retries=5,
    retry_backoff=True,
    retry_jitter=True,
)  # type: ignore[untyped-decorator]
def detect_near_duplicate_candidates(dossier_version_id: str) -> None:
    asyncio.run(_detect(UUID(dossier_version_id)))
