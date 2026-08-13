from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends

from app.modules.auth.dependencies import SessionDependency
from app.modules.dossiers.service import DossierService
from app.workers.celery_app import celery_app


async def get_dossier_service(
    session: SessionDependency,
) -> AsyncIterator[DossierService]:
    yield DossierService(
        session=session,
        enqueue_similarity_detection=lambda version_id: celery_app.send_task(
            "app.workers.similarity_tasks.detect_near_duplicate_candidates",
            args=[str(version_id)],
        ),
    )


DossierServiceDependency = Annotated[
    DossierService,
    Depends(get_dossier_service),
]
