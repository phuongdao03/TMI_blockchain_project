from uuid import UUID

from sqlalchemy import exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.authorization import AuthorizationPolicy, PolicyRequirement
from app.modules.auth.session_service import AuthPrincipal
from app.modules.dossiers.models import DossierEvidence
from app.modules.reviews.models import (
    ReviewAssignment,
    ReviewAssignmentStatus,
    SimilarityCaseStatus,
    SimilarityReviewCase,
)

DELIVERABLE_ASSIGNMENT_STATUSES = (
    ReviewAssignmentStatus.IN_PROGRESS,
    ReviewAssignmentStatus.SUBMITTED,
)
DELIVERABLE_SIMILARITY_STATUSES = (
    SimilarityCaseStatus.ASSIGNED,
    SimilarityCaseStatus.RESOLVED,
)


class ReviewMediaAccessPolicy:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def can_deliver(
        self,
        principal: AuthPrincipal,
        media_id: UUID,
    ) -> bool:
        if not AuthorizationPolicy.allows_capability(
            principal,
            PolicyRequirement(
                permission="review.submit",
                compatible_roles=frozenset({"REVIEWER"}),
                allow_super_admin=False,
            ),
        ):
            return False
        review_assignment = exists().where(
            DossierEvidence.media_asset_id == media_id,
            DossierEvidence.dossier_version_id
            == ReviewAssignment.dossier_version_id,
            ReviewAssignment.reviewer_user_id == principal.user_id,
            ReviewAssignment.status.in_(DELIVERABLE_ASSIGNMENT_STATUSES),
        )
        similarity_assignment = exists().where(
            DossierEvidence.media_asset_id == media_id,
            or_(
                DossierEvidence.dossier_version_id
                == SimilarityReviewCase.left_dossier_version_id,
                DossierEvidence.dossier_version_id
                == SimilarityReviewCase.right_dossier_version_id,
            ),
            SimilarityReviewCase.assigned_reviewer_user_id == principal.user_id,
            SimilarityReviewCase.status.in_(DELIVERABLE_SIMILARITY_STATUSES),
        )
        allowed = await self._session.scalar(
            select(or_(review_assignment, similarity_assignment))
        )
        return bool(allowed)
