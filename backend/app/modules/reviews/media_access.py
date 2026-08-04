from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.session_service import AuthPrincipal
from app.modules.dossiers.models import DossierEvidence
from app.modules.reviews.models import (
    ReviewAssignment,
    ReviewAssignmentStatus,
)

DELIVERABLE_ASSIGNMENT_STATUSES = (
    ReviewAssignmentStatus.IN_PROGRESS,
    ReviewAssignmentStatus.SUBMITTED,
)


class ReviewMediaAccessPolicy:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def can_deliver(
        self,
        principal: AuthPrincipal,
        media_id: UUID,
    ) -> bool:
        if "REVIEWER" not in principal.roles:
            return False
        allowed = await self._session.scalar(
            select(
                exists().where(
                    DossierEvidence.media_asset_id == media_id,
                    DossierEvidence.dossier_version_id
                    == ReviewAssignment.dossier_version_id,
                    ReviewAssignment.reviewer_user_id == principal.user_id,
                    ReviewAssignment.status.in_(DELIVERABLE_ASSIGNMENT_STATUSES),
                )
            )
        )
        return bool(allowed)
