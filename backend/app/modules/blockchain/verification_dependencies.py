from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.modules.audit.service import AuditService
from app.modules.auth.dependencies import SessionDependency, SettingsDependency
from app.modules.auth.session_service import AuthPrincipal
from app.modules.blockchain.verification import (
    DocumentVerificationStatus,
    PrivateDocumentVerificationService,
    SqlDocumentProofRepository,
)
from app.modules.reviews.media_access import ReviewMediaAccessPolicy


async def get_document_verification_service(
    session: SessionDependency,
    settings: SettingsDependency,
) -> AsyncIterator[PrivateDocumentVerificationService]:
    audit = AuditService(session, settings=settings)

    async def record_result(
        principal: AuthPrincipal,
        media_id: UUID,
        result: DocumentVerificationStatus,
    ) -> None:
        audit.record(
            actor_user_id=principal.user_id,
            action="document.verification.completed",
            resource_type="media_asset",
            resource_id=str(media_id),
            after={"status": result.value},
        )
        await session.commit()

    yield PrivateDocumentVerificationService(
        repository=SqlDocumentProofRepository(session),
        access_policy=ReviewMediaAccessPolicy(session),
        max_bytes=settings.document_verification_max_bytes,
        record_result=record_result,
    )


DocumentVerificationServiceDependency = Annotated[
    PrivateDocumentVerificationService,
    Depends(get_document_verification_service),
]
