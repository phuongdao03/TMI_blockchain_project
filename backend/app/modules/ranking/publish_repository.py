from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ranking.models import RankingSnapshot
from app.modules.ranking.publish import (
    RankingPublicationCampaign,
    RankingPublicationRepositoryPort,
    RankingPublicationSnapshot,
)
from app.modules.voting.models import CampaignStatus, VotingCampaign


class RankingPublicationRepository(RankingPublicationRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_campaign(
        self, campaign_id: UUID
    ) -> RankingPublicationCampaign | None:
        row = (
            await self._session.execute(
                select(VotingCampaign.id, VotingCampaign.status)
                .where(VotingCampaign.id == campaign_id)
                .with_for_update()
            )
        ).one_or_none()
        if row is None:
            return None
        return RankingPublicationCampaign(id=row.id, status=row.status)

    async def get_snapshot(
        self, campaign_id: UUID, version: int
    ) -> RankingPublicationSnapshot | None:
        row = (
            await self._session.execute(
                select(
                    RankingSnapshot.id,
                    RankingSnapshot.campaign_id,
                    RankingSnapshot.version,
                ).where(
                    RankingSnapshot.campaign_id == campaign_id,
                    RankingSnapshot.version == version,
                )
            )
        ).one_or_none()
        if row is None:
            return None
        return RankingPublicationSnapshot(
            id=row.id,
            campaign_id=row.campaign_id,
            version=int(row.version),
        )

    async def publish(
        self, campaign_id: UUID, snapshot_id: UUID, published_at: datetime
    ) -> None:
        campaign = await self._session.scalar(
            select(VotingCampaign)
            .where(VotingCampaign.id == campaign_id)
            .with_for_update()
        )
        if campaign is None:
            return
        campaign.status = CampaignStatus.PUBLISHED
        campaign.published_snapshot_id = snapshot_id
        campaign.results_published_at = published_at
        await self._session.flush()

    async def commit(self) -> None:
        await self._session.commit()
