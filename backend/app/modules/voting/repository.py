from dataclasses import dataclass
from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.public.models import (
    PublicationStatus,
    PublicWork,
    PublicWorkVisibility,
)
from app.modules.voting.models import (
    CampaignEvent,
    CampaignStatus,
    CampaignWork,
    CampaignWorkStatus,
    VotingCampaign,
)


class VotingCampaignRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, campaign: VotingCampaign) -> None:
        self._session.add(campaign)

    def add_event(self, event: CampaignEvent) -> None:
        self._session.add(event)

    async def get(
        self,
        campaign_id: UUID,
        *,
        for_update: bool = False,
    ) -> VotingCampaign | None:
        statement = select(VotingCampaign).where(VotingCampaign.id == campaign_id)
        if for_update:
            statement = statement.with_for_update()
        return cast(VotingCampaign | None, await self._session.scalar(statement))

    async def slug_exists(self, slug: str, *, exclude_id: UUID | None = None) -> bool:
        statement = select(VotingCampaign.id).where(VotingCampaign.slug == slug)
        if exclude_id is not None:
            statement = statement.where(VotingCampaign.id != exclude_id)
        return await self._session.scalar(statement) is not None

    async def list(
        self,
        *,
        status: CampaignStatus | None,
        page: int,
        page_size: int,
    ) -> tuple[tuple[VotingCampaign, ...], int]:
        criteria = (VotingCampaign.status == status,) if status is not None else ()
        statement = (
            select(VotingCampaign)
            .where(*criteria)
            .order_by(VotingCampaign.created_at.desc(), VotingCampaign.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        total_statement = (
            select(func.count()).select_from(VotingCampaign).where(*criteria)
        )
        rows = tuple((await self._session.scalars(statement)).all())
        total = int(await self._session.scalar(total_statement) or 0)
        return rows, total

    async def count_eligible_participants(self, campaign_id: UUID) -> int:
        statement = (
            select(func.count(CampaignWork.id))
            .join(PublicWork, PublicWork.id == CampaignWork.work_id)
            .where(
                CampaignWork.campaign_id == campaign_id,
                CampaignWork.status == CampaignWorkStatus.APPROVED,
                PublicWork.publication_status == PublicationStatus.PUBLISHED,
                PublicWork.visibility == PublicWorkVisibility.PUBLIC,
                PublicWork.deleted_at.is_(None),
            )
        )
        return int(await self._session.scalar(statement) or 0)

    async def list_due_activation_ids(
        self,
        *,
        now: datetime,
        limit: int,
    ) -> tuple[UUID, ...]:
        statement = (
            select(VotingCampaign.id)
            .where(
                VotingCampaign.status == CampaignStatus.SCHEDULED,
                VotingCampaign.start_at <= now,
                VotingCampaign.end_at > now,
            )
            .order_by(VotingCampaign.start_at, VotingCampaign.id)
            .limit(limit)
        )
        return tuple((await self._session.scalars(statement)).all())

    async def list_due_end_ids(
        self,
        *,
        now: datetime,
        limit: int,
    ) -> tuple[UUID, ...]:
        statement = (
            select(VotingCampaign.id)
            .where(
                VotingCampaign.status.in_(
                    (CampaignStatus.ACTIVE, CampaignStatus.PAUSED)
                ),
                VotingCampaign.end_at <= now,
            )
            .order_by(VotingCampaign.end_at, VotingCampaign.id)
            .limit(limit)
        )
        return tuple((await self._session.scalars(statement)).all())

    async def list_missed_activation_ids(
        self,
        *,
        now: datetime,
        limit: int,
    ) -> tuple[UUID, ...]:
        statement = (
            select(VotingCampaign.id)
            .where(
                VotingCampaign.status == CampaignStatus.SCHEDULED,
                VotingCampaign.end_at <= now,
            )
            .order_by(VotingCampaign.end_at, VotingCampaign.id)
            .limit(limit)
        )
        return tuple((await self._session.scalars(statement)).all())


@dataclass(frozen=True, slots=True)
class CampaignParticipantView:
    id: UUID
    campaign_id: UUID
    work_id: UUID
    status: CampaignWorkStatus
    title: str
    slug: str
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CampaignWorkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, participant: CampaignWork) -> None:
        self._session.add(participant)

    async def get_by_work(
        self,
        campaign_id: UUID,
        work_id: UUID,
    ) -> CampaignWork | None:
        statement = select(CampaignWork).where(
            CampaignWork.campaign_id == campaign_id,
            CampaignWork.work_id == work_id,
        )
        return cast(CampaignWork | None, await self._session.scalar(statement))

    async def get(
        self,
        campaign_id: UUID,
        participant_id: UUID,
        *,
        for_update: bool = False,
    ) -> CampaignWork | None:
        statement = select(CampaignWork).where(
            CampaignWork.id == participant_id,
            CampaignWork.campaign_id == campaign_id,
        )
        if for_update:
            statement = statement.with_for_update()
        return cast(CampaignWork | None, await self._session.scalar(statement))

    async def eligible_work(self, work_id: UUID) -> PublicWork | None:
        statement = select(PublicWork).where(
            PublicWork.id == work_id,
            PublicWork.publication_status == PublicationStatus.PUBLISHED,
            PublicWork.visibility == PublicWorkVisibility.PUBLIC,
            PublicWork.deleted_at.is_(None),
        )
        return cast(PublicWork | None, await self._session.scalar(statement))

    async def view(
        self,
        campaign_id: UUID,
        participant_id: UUID,
    ) -> CampaignParticipantView | None:
        statement = (
            select(CampaignWork, PublicWork.title, PublicWork.slug)
            .join(PublicWork, PublicWork.id == CampaignWork.work_id)
            .where(
                CampaignWork.id == participant_id,
                CampaignWork.campaign_id == campaign_id,
            )
        )
        row = (await self._session.execute(statement)).one_or_none()
        if row is None:
            return None
        participant, title, slug = row
        return CampaignParticipantView(
            id=participant.id,
            campaign_id=participant.campaign_id,
            work_id=participant.work_id,
            status=participant.status,
            title=title,
            slug=slug,
            approved_at=participant.approved_at,
            created_at=participant.created_at,
            updated_at=participant.updated_at,
        )

    async def list(
        self,
        campaign_id: UUID,
        *,
        status: CampaignWorkStatus | None,
        page: int,
        page_size: int,
    ) -> tuple[tuple[CampaignParticipantView, ...], int]:
        criteria = [CampaignWork.campaign_id == campaign_id]
        if status is not None:
            criteria.append(CampaignWork.status == status)
        statement = (
            select(CampaignWork, PublicWork.title, PublicWork.slug)
            .join(PublicWork, PublicWork.id == CampaignWork.work_id)
            .where(*criteria)
            .order_by(CampaignWork.created_at.desc(), CampaignWork.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        total_statement = (
            select(func.count()).select_from(CampaignWork).where(*criteria)
        )
        result = await self._session.execute(statement)
        rows = tuple(
            CampaignParticipantView(
                id=participant.id,
                campaign_id=participant.campaign_id,
                work_id=participant.work_id,
                status=participant.status,
                title=title,
                slug=slug,
                approved_at=participant.approved_at,
                created_at=participant.created_at,
                updated_at=participant.updated_at,
            )
            for participant, title, slug in result.all()
        )
        total = int(await self._session.scalar(total_statement) or 0)
        return rows, total
