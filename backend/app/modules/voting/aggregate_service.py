import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.public.models import (
    PublicationStatus,
    PublicWork,
    PublicWorkVisibility,
)
from app.modules.voting.models import (
    CampaignWork,
    CampaignWorkStatus,
    Vote,
    VoteAggregate,
    VoteStatus,
)


class VoteSummaryCache(Protocol):
    async def get(self, campaign_id: UUID) -> str | None: ...

    async def set(self, campaign_id: UUID, payload: str) -> None: ...

    async def invalidate(self, campaign_id: UUID) -> None: ...


@dataclass(frozen=True, slots=True)
class VoteAggregateItem:
    work_id: UUID
    work_title: str
    work_slug: str
    effective_count: int
    refreshed_at: datetime


class VoteAggregateService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        cache: VoteSummaryCache | None = None,
    ) -> None:
        self._session = session
        self._cache = cache

    async def recount_work(
        self,
        campaign_id: UUID,
        work_id: UUID,
        *,
        now: datetime | None = None,
    ) -> VoteAggregate:
        refreshed_at = self._utc(now or datetime.now(UTC))
        count = int(
            await self._session.scalar(
                select(func.count(Vote.id)).where(
                    Vote.campaign_id == campaign_id,
                    Vote.work_id == work_id,
                    Vote.status == VoteStatus.VALID,
                )
            )
            or 0
        )
        row = await self._session.get(VoteAggregate, (campaign_id, work_id))
        if row is None:
            row = VoteAggregate(
                campaign_id=campaign_id,
                work_id=work_id,
                effective_count=count,
                version=1,
                refreshed_at=refreshed_at,
            )
            self._session.add(row)
        else:
            row.effective_count = count
            row.version += 1
            row.refreshed_at = refreshed_at
        await self._session.flush()
        return row

    async def recount_campaign(
        self,
        campaign_id: UUID,
        *,
        now: datetime | None = None,
    ) -> int:
        work_ids = tuple(
            (
                await self._session.scalars(
                    select(CampaignWork.work_id).where(
                        CampaignWork.campaign_id == campaign_id,
                        CampaignWork.status == CampaignWorkStatus.APPROVED,
                    )
                )
            ).all()
        )
        stale = delete(VoteAggregate).where(VoteAggregate.campaign_id == campaign_id)
        if work_ids:
            stale = stale.where(VoteAggregate.work_id.not_in(work_ids))
        await self._session.execute(stale)
        for work_id in work_ids:
            await self.recount_work(campaign_id, work_id, now=now)
        return len(work_ids)

    async def summary(self, campaign_id: UUID) -> list[VoteAggregateItem]:
        if self._cache is not None:
            cached = await self._cache.get(campaign_id)
            if cached is not None:
                return [
                    VoteAggregateItem(
                        work_id=UUID(item["work_id"]),
                        work_title=item["work_title"],
                        work_slug=item["work_slug"],
                        effective_count=item["effective_count"],
                        refreshed_at=self._utc(
                            datetime.fromisoformat(item["refreshed_at"])
                        ),
                    )
                    for item in json.loads(cached)
                ]
        rows = (
            await self._session.execute(
                select(VoteAggregate, PublicWork)
                .join(PublicWork, PublicWork.id == VoteAggregate.work_id)
                .join(
                    CampaignWork,
                    (CampaignWork.campaign_id == VoteAggregate.campaign_id)
                    & (CampaignWork.work_id == VoteAggregate.work_id),
                )
                .where(
                    VoteAggregate.campaign_id == campaign_id,
                    CampaignWork.status == CampaignWorkStatus.APPROVED,
                    PublicWork.publication_status == PublicationStatus.PUBLISHED,
                    PublicWork.visibility == PublicWorkVisibility.PUBLIC,
                    PublicWork.deleted_at.is_(None),
                )
                .order_by(VoteAggregate.effective_count.desc(), VoteAggregate.work_id)
            )
        ).all()
        result = [
            VoteAggregateItem(
                work_id=aggregate.work_id,
                work_title=work.title,
                work_slug=work.slug,
                effective_count=aggregate.effective_count,
                refreshed_at=aggregate.refreshed_at,
            )
            for aggregate, work in rows
        ]
        if self._cache is not None:
            payload = json.dumps(
                [
                    {
                        **asdict(item),
                        "work_id": str(item.work_id),
                        "refreshed_at": item.refreshed_at.isoformat(),
                    }
                    for item in result
                ],
                separators=(",", ":"),
            )
            await self._cache.set(campaign_id, payload)
        return result

    @staticmethod
    def _utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
