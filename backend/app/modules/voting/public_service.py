from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.public.models import (
    PublicationStatus,
    PublicWork,
    PublicWorkVisibility,
)
from app.modules.voting.aggregate_service import VoteAggregateItem, VoteAggregateService
from app.modules.voting.errors import VotingCampaignNotFoundError
from app.modules.voting.models import (
    CampaignStatus,
    CampaignWork,
    CampaignWorkStatus,
    VotingCampaign,
)

PUBLIC_CAMPAIGN_STATUSES = (
    CampaignStatus.SCHEDULED,
    CampaignStatus.ACTIVE,
    CampaignStatus.PAUSED,
    CampaignStatus.ENDED,
    CampaignStatus.RESULT_PENDING,
    CampaignStatus.PUBLISHED,
)


@dataclass(frozen=True, slots=True)
class PublicCampaignWorkItem:
    work_id: UUID
    title: str
    slug: str
    short_description: str


class PublicVotingService:
    def __init__(
        self,
        session: AsyncSession,
        aggregate_service: VoteAggregateService,
    ) -> None:
        self._session = session
        self._aggregates = aggregate_service

    async def list_campaigns(
        self, *, page: int, page_size: int
    ) -> tuple[list[VotingCampaign], int]:
        criteria = VotingCampaign.status.in_(PUBLIC_CAMPAIGN_STATUSES)
        rows = list(
            (
                await self._session.scalars(
                    select(VotingCampaign)
                    .where(criteria)
                    .order_by(VotingCampaign.start_at.desc(), VotingCampaign.id.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).all()
        )
        total = int(
            await self._session.scalar(
                select(func.count(VotingCampaign.id)).where(criteria)
            )
            or 0
        )
        return rows, total

    async def campaign(self, slug: str) -> VotingCampaign:
        row = await self._session.scalar(
            select(VotingCampaign).where(
                VotingCampaign.slug == slug,
                VotingCampaign.status.in_(PUBLIC_CAMPAIGN_STATUSES),
            )
        )
        if row is None:
            raise VotingCampaignNotFoundError()
        return row

    async def works(self, slug: str) -> list[PublicCampaignWorkItem]:
        campaign = await self.campaign(slug)
        rows = (
            await self._session.execute(
                select(PublicWork)
                .join(CampaignWork, CampaignWork.work_id == PublicWork.id)
                .where(
                    CampaignWork.campaign_id == campaign.id,
                    CampaignWork.status == CampaignWorkStatus.APPROVED,
                    PublicWork.publication_status == PublicationStatus.PUBLISHED,
                    PublicWork.visibility == PublicWorkVisibility.PUBLIC,
                    PublicWork.deleted_at.is_(None),
                )
                .order_by(PublicWork.title, PublicWork.id)
            )
        ).scalars()
        return [
            PublicCampaignWorkItem(
                work_id=work.id,
                title=work.title,
                slug=work.slug,
                short_description=work.short_description,
            )
            for work in rows
        ]

    async def summary(self, slug: str) -> list[VoteAggregateItem]:
        campaign = await self.campaign(slug)
        return await self._aggregates.summary(campaign.id)

    @staticmethod
    def server_time() -> datetime:
        return datetime.now(UTC)
