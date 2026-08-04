from datetime import datetime, timedelta

from sqlalchemy import and_, case, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.dossiers.models import Category as Category  # noqa: F401
from app.modules.public.models import (
    PublicationStatus,
    PublicWork,
    PublicWorkVisibility,
)
from app.modules.ranking.trending_formula import TrendingCandidate
from app.modules.ranking.trending_models import TrendingSnapshot, TrendingSnapshotItem
from app.modules.ranking.trending_types import (
    TrendingSnapshotDraft,
    TrendingWindow,
)
from app.modules.voting.models import Vote, VoteStatus


class TrendingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_candidates(
        self,
        *,
        window: TrendingWindow,
    ) -> tuple[TrendingCandidate, ...]:
        recent_boundary = window.window_end - timedelta(hours=24)
        older_boundary = window.window_end - timedelta(hours=48)
        weighted_vote = case(
            (Vote.id.is_(None), 0),
            (Vote.created_at > recent_boundary, 4),
            (Vote.created_at > older_boundary, 2),
            else_=1,
        )
        statement = (
            select(
                PublicWork.id,
                PublicWork.category_id,
                func.coalesce(func.sum(weighted_vote), 0).label("trending_score"),
            )
            .select_from(PublicWork)
            .outerjoin(
                Vote,
                and_(
                    Vote.work_id == PublicWork.id,
                    Vote.status == VoteStatus.VALID,
                    Vote.created_at >= window.window_start,
                    Vote.created_at < window.window_end,
                ),
            )
            .where(
                PublicWork.publication_status == PublicationStatus.PUBLISHED,
                PublicWork.visibility == PublicWorkVisibility.PUBLIC,
                PublicWork.deleted_at.is_(None),
            )
            .group_by(PublicWork.id, PublicWork.category_id)
            .order_by(PublicWork.id)
        )
        rows = (await self._session.execute(statement)).all()
        return tuple(
            TrendingCandidate(
                work_id=row.id,
                category_id=row.category_id,
                score=int(row.trending_score),
            )
            for row in rows
        )


class TrendingSnapshotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_window(
        self,
        *,
        window_start: datetime,
        window_end: datetime,
    ) -> TrendingSnapshot | None:
        result = await self._session.scalars(
            select(TrendingSnapshot).where(
                TrendingSnapshot.window_start == window_start,
                TrendingSnapshot.window_end == window_end,
            )
        )
        return result.one_or_none()

    async def add(self, draft: TrendingSnapshotDraft) -> bool:
        self._session.add(
            TrendingSnapshot(
                id=draft.id,
                window_start=draft.window_start,
                window_end=draft.window_end,
                formula_version=draft.formula_version,
                source_digest=draft.source_digest,
                result_digest=draft.result_digest,
                candidate_count=draft.candidate_count,
                total_score=draft.total_score,
                created_at=draft.created_at,
            )
        )
        self._session.add_all(
            [
                TrendingSnapshotItem(
                    snapshot_id=draft.id,
                    work_id=item.work_id,
                    category_id=item.category_id,
                    rank=item.rank,
                    display_order=item.display_order,
                    score=item.score,
                )
                for item in draft.items
            ]
        )
        try:
            await self._session.flush()
        except IntegrityError:
            await self._session.rollback()
            existing = await self.get_by_window(
                window_start=draft.window_start,
                window_end=draft.window_end,
            )
            if existing is None:
                raise
            return False
        return True

    async def commit(self) -> None:
        await self._session.commit()
