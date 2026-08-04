from uuid import UUID

from sqlalchemy import and_, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.public.models import PublicWork
from app.modules.ranking.formula import RankingCandidate
from app.modules.ranking.models import RankingSnapshot, RankingSnapshotItem
from app.modules.ranking.types import (
    CLOSED_RANKING_CAMPAIGN_STATUSES,
    RankingCampaignSource,
    RankingSnapshotDraft,
)
from app.modules.voting.models import (
    CampaignType,
    CampaignWork,
    CampaignWorkStatus,
    PeriodType,
    Vote,
    VoteStatus,
    VotingCampaign,
)


class RankingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_campaign(self, campaign_id: UUID) -> RankingCampaignSource | None:
        row = (
            await self._session.execute(
                select(
                    VotingCampaign.id,
                    VotingCampaign.status,
                    VotingCampaign.rule_version,
                    VotingCampaign.end_at,
                ).where(VotingCampaign.id == campaign_id)
            )
        ).one_or_none()
        if row is None:
            return None
        return RankingCampaignSource(
            campaign_id=row.id,
            status=row.status,
            rule_version=row.rule_version,
            end_at=row.end_at,
        )

    async def list_candidates(self, campaign_id: UUID) -> tuple[RankingCandidate, ...]:
        rows = (
            await self._session.execute(
                select(
                    CampaignWork.work_id,
                    PublicWork.category_id,
                    func.count(Vote.id).label("effective_vote_count"),
                )
                .select_from(CampaignWork)
                .join(PublicWork, PublicWork.id == CampaignWork.work_id)
                .outerjoin(
                    Vote,
                    and_(
                        Vote.campaign_id == CampaignWork.campaign_id,
                        Vote.work_id == CampaignWork.work_id,
                        Vote.status == VoteStatus.VALID,
                    ),
                )
                .where(
                    CampaignWork.campaign_id == campaign_id,
                    CampaignWork.status == CampaignWorkStatus.APPROVED,
                )
                .group_by(CampaignWork.work_id, PublicWork.category_id)
                .order_by(CampaignWork.work_id)
            )
        ).all()
        return tuple(
            RankingCandidate(
                work_id=row.work_id,
                category_id=row.category_id,
                effective_vote_count=int(row.effective_vote_count),
            )
            for row in rows
        )


class RankingSnapshotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_pending_monthly_campaign_ids(
        self, *, limit: int
    ) -> tuple[UUID, ...]:
        return await self.list_pending_periodic_campaign_ids(
            period_type=PeriodType.MONTHLY,
            limit=limit,
        )

    async def list_pending_quarterly_campaign_ids(
        self, *, limit: int
    ) -> tuple[UUID, ...]:
        return await self.list_pending_periodic_campaign_ids(
            period_type=PeriodType.QUARTERLY,
            limit=limit,
        )

    async def list_pending_yearly_campaign_ids(self, *, limit: int) -> tuple[UUID, ...]:
        return await self.list_pending_periodic_campaign_ids(
            period_type=PeriodType.YEARLY,
            limit=limit,
        )

    async def list_pending_periodic_campaign_ids(
        self, *, period_type: PeriodType, limit: int
    ) -> tuple[UUID, ...]:
        has_snapshot = exists(
            select(RankingSnapshot.id).where(
                RankingSnapshot.campaign_id == VotingCampaign.id
            )
        )
        statement = (
            select(VotingCampaign.id)
            .where(
                VotingCampaign.campaign_type == CampaignType.PERIODIC,
                VotingCampaign.period_type == period_type,
                VotingCampaign.status.in_(CLOSED_RANKING_CAMPAIGN_STATUSES),
                ~has_snapshot,
            )
            .order_by(VotingCampaign.end_at, VotingCampaign.id)
            .limit(limit)
        )
        return tuple((await self._session.scalars(statement)).all())

    async def next_version(self, campaign_id: UUID) -> int:
        await self._session.execute(
            select(VotingCampaign.id)
            .where(VotingCampaign.id == campaign_id)
            .with_for_update()
        )
        current = await self._session.scalar(
            select(func.max(RankingSnapshot.version)).where(
                RankingSnapshot.campaign_id == campaign_id
            )
        )
        return int(current or 0) + 1

    async def add(self, draft: RankingSnapshotDraft) -> None:
        self._session.add(
            RankingSnapshot(
                id=draft.id,
                campaign_id=draft.campaign_id,
                version=draft.version,
                formula_version=draft.formula_version,
                campaign_rule_version=draft.campaign_rule_version,
                source_digest=draft.source_digest,
                result_digest=draft.result_digest,
                candidate_count=draft.candidate_count,
                total_valid_votes=draft.total_valid_votes,
                created_at=draft.created_at,
            )
        )
        self._session.add_all(
            [
                RankingSnapshotItem(
                    snapshot_id=draft.id,
                    work_id=item.work_id,
                    category_id=item.category_id,
                    rank=item.rank,
                    category_rank=item.category_rank,
                    display_order=item.display_order,
                    score=item.score,
                    effective_vote_count=item.effective_vote_count,
                )
                for item in draft.items
            ]
        )
        await self._session.flush()

    async def commit(self) -> None:
        await self._session.commit()
