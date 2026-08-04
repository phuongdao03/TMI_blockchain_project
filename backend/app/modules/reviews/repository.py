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
                    Role.code == "REVIEWER",
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
