from typing import cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import Role, User, UserRole, UserStatus
from app.modules.dossiers.models import Dossier, DossierVersion
from app.modules.reviews.models import (
    Review,
    ReviewAssignment,
    ReviewAssignmentStatus,
    SimilarityCaseStatus,
    SimilarityReviewCase,
    SimilaritySignalType,
)

ACTIVE_ASSIGNMENT_STATUSES = (
    ReviewAssignmentStatus.ASSIGNED,
    ReviewAssignmentStatus.IN_PROGRESS,
)


class ReviewRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add_assignment(self, assignment: ReviewAssignment) -> None:
        self._session.add(assignment)

    def add_review(self, review: Review) -> None:
        self._session.add(review)

    def add_similarity_case(self, case: SimilarityReviewCase) -> None:
        self._session.add(case)

    async def find_similarity_case(
        self,
        *,
        left_version_id: UUID,
        right_version_id: UUID,
        signal_type: SimilaritySignalType,
        policy_version: str,
    ) -> SimilarityReviewCase | None:
        return cast(
            SimilarityReviewCase | None,
            await self._session.scalar(
                select(SimilarityReviewCase).where(
                    SimilarityReviewCase.left_dossier_version_id == left_version_id,
                    SimilarityReviewCase.right_dossier_version_id == right_version_id,
                    SimilarityReviewCase.signal_type == signal_type,
                    SimilarityReviewCase.policy_version == policy_version,
                )
            ),
        )

    async def get_similarity_case(
        self,
        case_id: UUID,
        *,
        reviewer_user_id: UUID | None = None,
        for_update: bool = False,
    ) -> SimilarityReviewCase | None:
        statement = select(SimilarityReviewCase).where(
            SimilarityReviewCase.id == case_id
        )
        if reviewer_user_id is not None:
            statement = statement.where(
                SimilarityReviewCase.assigned_reviewer_user_id == reviewer_user_id
            )
        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        return cast(
            SimilarityReviewCase | None,
            await self._session.scalar(statement),
        )

    async def list_similarity_cases(
        self,
        *,
        reviewer_user_id: UUID | None,
        status: SimilarityCaseStatus | None,
        offset: int,
        limit: int,
    ) -> tuple[tuple[SimilarityReviewCase, ...], int]:
        criteria = []
        if reviewer_user_id is not None:
            criteria.append(
                SimilarityReviewCase.assigned_reviewer_user_id == reviewer_user_id
            )
        if status is not None:
            criteria.append(SimilarityReviewCase.status == status)
        total = await self._session.scalar(
            select(func.count()).select_from(SimilarityReviewCase).where(*criteria)
        )
        rows = await self._session.scalars(
            select(SimilarityReviewCase)
            .where(*criteria)
            .order_by(
                SimilarityReviewCase.created_at.desc(),
                SimilarityReviewCase.id.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
        return tuple(rows.all()), int(total or 0)

    async def get_active_reviewer(self, user_id: UUID) -> User | None:
        return cast(
            User | None,
            await self._session.scalar(
                select(User)
                .join(UserRole, UserRole.user_id == User.id)
                .join(Role, Role.id == UserRole.role_id)
                .where(
                    User.id == user_id,
                    User.status == UserStatus.ACTIVE,
                    Role.code == "MODERATOR",
                )
            ),
        )

    async def get_active_assignment(
        self,
        reviewer_user_id: UUID,
        dossier_version_id: UUID,
    ) -> ReviewAssignment | None:
        return cast(
            ReviewAssignment | None,
            await self._session.scalar(
                select(ReviewAssignment).where(
                    ReviewAssignment.reviewer_user_id == reviewer_user_id,
                    ReviewAssignment.dossier_version_id == dossier_version_id,
                    ReviewAssignment.status.in_(ACTIVE_ASSIGNMENT_STATUSES),
                )
            ),
        )

    async def get_owned_assignment(
        self,
        assignment_id: UUID,
        reviewer_user_id: UUID,
        *,
        for_update: bool = False,
    ) -> ReviewAssignment | None:
        statement = select(ReviewAssignment).where(
            ReviewAssignment.id == assignment_id,
            ReviewAssignment.reviewer_user_id == reviewer_user_id,
        )
        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        return cast(
            ReviewAssignment | None,
            await self._session.scalar(statement),
        )

    async def get_version(self, version_id: UUID) -> DossierVersion | None:
        return cast(
            DossierVersion | None,
            await self._session.get(DossierVersion, version_id),
        )

    async def list_owned_assignments(
        self,
        reviewer_user_id: UUID,
        *,
        status: ReviewAssignmentStatus | None,
        offset: int,
        limit: int,
    ) -> tuple[
        tuple[tuple[ReviewAssignment, Dossier, DossierVersion], ...],
        int,
    ]:
        criteria = [ReviewAssignment.reviewer_user_id == reviewer_user_id]
        if status is not None:
            criteria.append(ReviewAssignment.status == status)
        total = await self._session.scalar(
            select(func.count()).select_from(ReviewAssignment).where(*criteria)
        )
        rows = await self._session.execute(
            select(ReviewAssignment, Dossier, DossierVersion)
            .join(Dossier, Dossier.id == ReviewAssignment.dossier_id)
            .join(
                DossierVersion,
                DossierVersion.id == ReviewAssignment.dossier_version_id,
            )
            .where(*criteria)
            .order_by(
                ReviewAssignment.due_at.is_(None),
                ReviewAssignment.due_at,
                ReviewAssignment.id,
            )
            .offset(offset)
            .limit(limit)
        )
        return tuple(rows.tuples().all()), int(total or 0)

    async def get_review(
        self,
        assignment_id: UUID,
        *,
        for_update: bool = False,
    ) -> Review | None:
        statement = select(Review).where(Review.assignment_id == assignment_id)
        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        return cast(Review | None, await self._session.scalar(statement))

    async def get_council_review_gate(
        self,
        dossier_version_id: UUID,
    ) -> tuple[int, int]:
        """Return (submitted_reviews, unfinished_assignments) for a version."""
        submitted_reviews = await self._session.scalar(
            select(func.count())
            .select_from(ReviewAssignment)
            .join(Review, Review.assignment_id == ReviewAssignment.id)
            .where(
                ReviewAssignment.dossier_version_id == dossier_version_id,
                ReviewAssignment.status == ReviewAssignmentStatus.SUBMITTED,
                Review.submitted_at.is_not(None),
                Review.total_score.is_not(None),
                Review.recommendation.is_not(None),
            )
        )
        unfinished_assignments = await self._session.scalar(
            select(func.count())
            .select_from(ReviewAssignment)
            .where(
                ReviewAssignment.dossier_version_id == dossier_version_id,
                ReviewAssignment.status.in_(ACTIVE_ASSIGNMENT_STATUSES),
            )
        )
        return int(submitted_reviews or 0), int(unfinished_assignments or 0)
