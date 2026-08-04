import hashlib
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.session_service import AuthPrincipal
from app.modules.public.models import PublicWork
from app.modules.voting.errors import VotingCampaignForbiddenError
from app.modules.voting.models import Vote, VoteStatus, VotingCampaign

VOTE_READ_PERMISSION = "voting.vote.read"


@dataclass(frozen=True, slots=True)
class AdminVoteItem:
    vote_id: UUID
    campaign_id: UUID
    campaign_name: str
    work_id: UUID
    work_title: str
    voter_reference: str
    status: VoteStatus
    source: str
    risk_score: str
    created_at: datetime
    revoked_at: datetime | None


class AdminVoteService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self,
        principal: AuthPrincipal,
        campaign_id: UUID,
        *,
        work_id: UUID | None,
        status: VoteStatus | None,
        page: int,
        page_size: int,
    ) -> tuple[list[AdminVoteItem], int]:
        self._require_read(principal)
        conditions = [Vote.campaign_id == campaign_id]
        if work_id is not None:
            conditions.append(Vote.work_id == work_id)
        if status is not None:
            conditions.append(Vote.status == status)
        total = int(
            await self._session.scalar(select(func.count(Vote.id)).where(*conditions))
            or 0
        )
        rows = (
            await self._session.execute(
                select(Vote, VotingCampaign.name, PublicWork.title)
                .join(VotingCampaign, VotingCampaign.id == Vote.campaign_id)
                .join(PublicWork, PublicWork.id == Vote.work_id)
                .where(*conditions)
                .order_by(Vote.created_at.desc(), Vote.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).all()
        return [
            AdminVoteItem(
                vote_id=vote.id,
                campaign_id=vote.campaign_id,
                campaign_name=campaign_name,
                work_id=vote.work_id,
                work_title=work_title,
                voter_reference=self._reference(vote.campaign_id, vote.user_id),
                status=vote.status,
                source=vote.source,
                risk_score=str(vote.risk_score),
                created_at=vote.created_at,
                revoked_at=vote.revoked_at,
            )
            for vote, campaign_name, work_title in rows
        ], total

    @staticmethod
    def _reference(campaign_id: UUID, user_id: UUID) -> str:
        digest = hashlib.sha256(f"{campaign_id}:{user_id}".encode()).hexdigest()
        return f"voter-{digest[:16]}"

    @staticmethod
    def _require_read(principal: AuthPrincipal) -> None:
        if VOTE_READ_PERMISSION not in principal.permissions:
            raise VotingCampaignForbiddenError()
