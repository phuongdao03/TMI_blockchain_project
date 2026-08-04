from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.modules.auth.session_service import AuthPrincipal
from app.modules.voting.models import CampaignStatus, VoteStatus
from app.modules.voting.vote_repository import VoteRepository


@dataclass(frozen=True, slots=True)
class VoteHistoryItem:
    vote_id: UUID
    campaign_id: UUID
    campaign_name: str
    campaign_slug: str
    work_id: UUID
    work_title: str
    work_slug: str
    status: VoteStatus
    created_at: datetime
    revoked_at: datetime | None
    can_change: bool
    can_revoke: bool


class VoteHistoryService:
    def __init__(self, repository: VoteRepository) -> None:
        self._repository = repository

    async def list(
        self,
        principal: AuthPrincipal,
        *,
        campaign_id: UUID | None,
        status: VoteStatus | None,
        date_from: datetime | None,
        date_to: datetime | None,
        page: int,
        page_size: int,
        now: datetime | None = None,
    ) -> tuple[list[VoteHistoryItem], int]:
        server_time = self._utc(now or datetime.now(UTC))
        rows, total = await self._repository.list_user_history(
            principal.user_id,
            campaign_id=campaign_id,
            status=status,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size,
        )
        items: list[VoteHistoryItem] = []
        effective = {VoteStatus.VALID, VoteStatus.SUSPICIOUS}
        for vote, campaign, work in rows:
            mutable = (
                vote.status in effective
                and campaign.status is CampaignStatus.ACTIVE
                and self._utc(campaign.start_at) <= server_time
                and server_time < self._utc(campaign.end_at)
            )
            items.append(
                VoteHistoryItem(
                    vote_id=vote.id,
                    campaign_id=campaign.id,
                    campaign_name=campaign.name,
                    campaign_slug=campaign.slug,
                    work_id=work.id,
                    work_title=work.title,
                    work_slug=work.slug,
                    status=vote.status,
                    created_at=vote.created_at,
                    revoked_at=vote.revoked_at,
                    can_change=mutable and campaign.allow_vote_change,
                    can_revoke=mutable and campaign.allow_vote_revoke,
                )
            )
        return items, total

    @staticmethod
    def _utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
