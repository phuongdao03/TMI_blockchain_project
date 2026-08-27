from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends

from app.modules.auth.dependencies import SessionDependency, SettingsDependency
from app.modules.auth.security import OutboxPayloadCipher
from app.modules.dossiers.service import DossierService
from app.workers.celery_app import celery_app


async def get_dossier_service(
    session: SessionDependency,
    settings: SettingsDependency,
) -> AsyncIterator[DossierService]:
    secret = settings.auth_outbox_encryption_key
    yield DossierService(
        session=session,
        payload_cipher=OutboxPayloadCipher.from_base64(
            encoded_key=secret.get_secret_value() if secret is not None else "",
            key_id=settings.auth_outbox_key_id,
        ),
        enqueue_similarity_detection=lambda version_id: celery_app.send_task(
            "app.workers.similarity_tasks.detect_near_duplicate_candidates",
            args=[str(version_id)],
        ),
    )


DossierServiceDependency = Annotated[
    DossierService,
    Depends(get_dossier_service),
]
