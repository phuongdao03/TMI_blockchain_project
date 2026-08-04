from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.dossiers.models import Category
from app.modules.public.models import (
    PublicationStatus,
    PublicWork,
    PublicWorkVisibility,
)
from app.modules.ranking.models import RankingSnapshot, RankingSnapshotItem
from app.modules.ranking.public_types import (
    PublicRankingItemView,
    PublicRankingSnapshotView,
)
from app.modules.voting.models import CampaignStatus, VotingCampaign


class PublicRankingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_snapshot(
        self,
        *,
        campaign_slug: str,
        version: int | None,
    ) -> PublicRankingSnapshotView | None:
        criteria = [
            VotingCampaign.slug == campaign_slug,
            VotingCampaign.status == CampaignStatus.PUBLISHED,
        ]
        if version is None:
            criteria.append(VotingCampaign.published_snapshot_id == RankingSnapshot.id)
        statement = (
            select(
                RankingSnapshot.id,
                RankingSnapshot.campaign_id,
                RankingSnapshot.version,
                RankingSnapshot.formula_version,
                RankingSnapshot.campaign_rule_version,
                RankingSnapshot.source_digest,
                RankingSnapshot.result_digest,
                RankingSnapshot.candidate_count,
                RankingSnapshot.total_valid_votes,
                RankingSnapshot.created_at,
            )
            .join(VotingCampaign, VotingCampaign.id == RankingSnapshot.campaign_id)
            .where(*criteria)
            .order_by(RankingSnapshot.version.desc())
            .limit(1)
        )
        if version is not None:
            statement = statement.where(RankingSnapshot.version == version)
        row = (await self._session.execute(statement)).one_or_none()
        if row is None:
            return None
        return PublicRankingSnapshotView(
            id=row.id,
            campaign_id=row.campaign_id,
            version=int(row.version),
            formula_version=row.formula_version,
            campaign_rule_version=int(row.campaign_rule_version),
            source_digest=row.source_digest,
            result_digest=row.result_digest,
            candidate_count=int(row.candidate_count),
            total_valid_votes=int(row.total_valid_votes),
            created_at=row.created_at,
        )

    async def list_items(
        self,
        *,
        snapshot_id: UUID,
        category_id: UUID | None,
        offset: int,
        limit: int,
    ) -> tuple[tuple[PublicRankingItemView, ...], int]:
        criteria = [
            RankingSnapshotItem.snapshot_id == snapshot_id,
            PublicWork.publication_status == PublicationStatus.PUBLISHED,
            PublicWork.visibility == PublicWorkVisibility.PUBLIC,
            PublicWork.deleted_at.is_(None),
        ]
        if category_id is not None:
            criteria.append(RankingSnapshotItem.category_id == category_id)

        source = (
            select(
                RankingSnapshotItem.work_id,
                PublicWork.slug,
                PublicWork.title,
                PublicWork.short_description,
                PublicWork.author_display_name,
                RankingSnapshotItem.category_id,
                Category.name.label("category_name"),
                Category.slug.label("category_slug"),
                RankingSnapshotItem.rank,
                RankingSnapshotItem.category_rank,
                RankingSnapshotItem.display_order,
                RankingSnapshotItem.score,
                RankingSnapshotItem.effective_vote_count,
            )
            .join(PublicWork, PublicWork.id == RankingSnapshotItem.work_id)
            .join(Category, Category.id == RankingSnapshotItem.category_id)
            .where(*criteria)
        )
        total = int(
            await self._session.scalar(
                select(func.count()).select_from(source.order_by(None).subquery())
            )
            or 0
        )
        rows = (
            await self._session.execute(
                source.order_by(
                    RankingSnapshotItem.display_order,
                    RankingSnapshotItem.work_id,
                )
                .offset(offset)
                .limit(limit)
            )
        ).all()
        return (
            tuple(
                PublicRankingItemView(
                    work_id=row.work_id,
                    slug=row.slug,
                    title=row.title,
                    short_description=row.short_description,
                    author_display_name=row.author_display_name,
                    category_id=row.category_id,
                    category_name=row.category_name,
                    category_slug=row.category_slug,
                    rank=int(row.rank),
                    category_rank=int(row.category_rank),
                    display_order=int(row.display_order),
                    score=int(row.score),
                    effective_vote_count=int(row.effective_vote_count),
                )
                for row in rows
            ),
            total,
        )
