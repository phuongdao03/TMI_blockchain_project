from datetime import datetime
from typing import TYPE_CHECKING, cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User, UserStatus
from app.modules.organizations.models import (
    MembershipStatus,
    Organization,
    OrganizationMember,
    OrganizationStatus,
)
from app.modules.public.models import (
    PublicationStatus,
    PublicWork,
    PublicWorkVisibility,
)
from app.modules.voting.events import VOTE_RESULT_EVENTS
from app.modules.voting.models import (
    CampaignWork,
    CampaignWorkStatus,
    Vote,
    VoteEvent,
    VoteStatus,
    VotingCampaign,
)

if TYPE_CHECKING:
    from app.modules.voting.eligibility import EligibilitySnapshot


class VotingEligibilityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def snapshot(
        self,
        *,
        user_id: UUID,
        roles: tuple[str, ...],
        campaign_id: UUID,
        work_id: UUID | None,
        for_update: bool,
        exclude_vote_id: UUID | None = None,
    ) -> "EligibilitySnapshot | None":
        from app.modules.voting.eligibility import EligibilitySnapshot

        campaign_statement = select(VotingCampaign).where(
            VotingCampaign.id == campaign_id
        )
        if for_update:
            campaign_statement = campaign_statement.with_for_update(read=True)
        campaign = cast(
            VotingCampaign | None,
            await self._session.scalar(campaign_statement),
        )
        if campaign is None:
            return None
        user_statement = select(User).where(User.id == user_id)
        if for_update:
            user_statement = user_statement.with_for_update()
        user = cast(User | None, await self._session.scalar(user_statement))
        if user is None:
            return None

        organization_statement = (
            select(OrganizationMember.organization_id)
            .join(
                Organization,
                Organization.id == OrganizationMember.organization_id,
            )
            .where(
                OrganizationMember.user_id == user_id,
                OrganizationMember.status == MembershipStatus.ACTIVE,
                Organization.status == OrganizationStatus.ACTIVE,
                Organization.deleted_at.is_(None),
            )
        )
        organization_ids = tuple(
            (await self._session.scalars(organization_statement)).all()
        )
        effective_statuses = (VoteStatus.VALID, VoteStatus.SUSPICIOUS)
        count_statement = select(func.count(Vote.id)).where(
            Vote.user_id == user_id,
            Vote.campaign_id == campaign_id,
            Vote.status.in_(effective_statuses),
        )
        if exclude_vote_id is not None:
            count_statement = count_statement.where(Vote.id != exclude_vote_id)
        effective_vote_count = int(await self._session.scalar(count_statement) or 0)
        already_voted = False
        participant_eligible: bool | None = None
        if work_id is not None:
            existing_statement = select(Vote.id).where(
                Vote.user_id == user_id,
                Vote.campaign_id == campaign_id,
                Vote.work_id == work_id,
                Vote.status.in_(effective_statuses),
            )
            if exclude_vote_id is not None:
                existing_statement = existing_statement.where(
                    Vote.id != exclude_vote_id
                )
            already_voted = await self._session.scalar(existing_statement) is not None
            participant_eligible = (
                await self._session.scalar(
                    select(CampaignWork.id)
                    .join(PublicWork, PublicWork.id == CampaignWork.work_id)
                    .where(
                        CampaignWork.campaign_id == campaign_id,
                        CampaignWork.work_id == work_id,
                        CampaignWork.status == CampaignWorkStatus.APPROVED,
                        PublicWork.publication_status == PublicationStatus.PUBLISHED,
                        PublicWork.visibility == PublicWorkVisibility.PUBLIC,
                        PublicWork.deleted_at.is_(None),
                    )
                )
                is not None
            )

        rules = campaign.eligibility_rules
        raw_roles = rules.get("allowed_roles", [])
        raw_organization_ids = rules.get("organization_ids", [])
        role_values = raw_roles if isinstance(raw_roles, list) else []
        organization_values = (
            raw_organization_ids if isinstance(raw_organization_ids, list) else []
        )
        allowed_roles = tuple(item for item in role_values if isinstance(item, str))
        allowed_organization_ids = tuple(
            UUID(item) for item in organization_values if isinstance(item, str)
        )
        return EligibilitySnapshot(
            user_status=user.status if user.deleted_at is None else UserStatus.DELETED,
            email_verified_at=user.email_verified_at,
            account_created_at=user.created_at,
            roles=roles,
            organization_ids=organization_ids,
            campaign_status=campaign.status,
            start_at=campaign.start_at,
            end_at=campaign.end_at,
            require_verified_email=campaign.require_verified_email,
            min_account_age_hours=campaign.min_account_age_hours,
            allowed_roles=allowed_roles,
            allowed_organization_ids=allowed_organization_ids,
            participant_eligible=participant_eligible,
            effective_vote_count=effective_vote_count,
            already_voted=already_voted,
            max_votes_per_user=campaign.max_votes_per_user,
            rule_version=campaign.rule_version,
        )


class VoteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def lock_user(self, user_id: UUID) -> User | None:
        statement = select(User).where(User.id == user_id).with_for_update()
        return cast(User | None, await self._session.scalar(statement))

    async def get_by_idempotency(
        self,
        user_id: UUID,
        idempotency_key: str,
    ) -> Vote | None:
        statement = select(Vote).where(
            Vote.user_id == user_id,
            Vote.idempotency_key == idempotency_key,
        )
        return cast(Vote | None, await self._session.scalar(statement))

    async def result_event(self, vote_id: UUID) -> VoteEvent | None:
        statement = (
            select(VoteEvent)
            .where(
                VoteEvent.vote_id == vote_id,
                VoteEvent.event_type.in_(VOTE_RESULT_EVENTS),
            )
            .order_by(VoteEvent.created_at.desc(), VoteEvent.id.desc())
        )
        return cast(VoteEvent | None, await self._session.scalar(statement))

    def add(self, vote: Vote) -> None:
        self._session.add(vote)

    def add_event(self, event: VoteEvent) -> None:
        self._session.add(event)

    async def get_owned(
        self,
        vote_id: UUID,
        user_id: UUID,
        campaign_id: UUID,
    ) -> Vote | None:
        statement = (
            select(Vote)
            .where(
                Vote.id == vote_id,
                Vote.user_id == user_id,
                Vote.campaign_id == campaign_id,
            )
            .with_for_update()
        )
        return cast(Vote | None, await self._session.scalar(statement))

    async def get_effective(
        self,
        user_id: UUID,
        campaign_id: UUID,
        work_id: UUID,
    ) -> Vote | None:
        statement = (
            select(Vote)
            .where(
                Vote.user_id == user_id,
                Vote.campaign_id == campaign_id,
                Vote.work_id == work_id,
                Vote.status.in_((VoteStatus.VALID, VoteStatus.SUSPICIOUS)),
            )
            .with_for_update()
        )
        return cast(Vote | None, await self._session.scalar(statement))

    async def campaign(self, campaign_id: UUID) -> VotingCampaign | None:
        return cast(
            VotingCampaign | None,
            await self._session.scalar(
                select(VotingCampaign).where(VotingCampaign.id == campaign_id)
            ),
        )

    async def mutation_event_by_key(
        self,
        user_id: UUID,
        idempotency_key: str,
    ) -> VoteEvent | None:
        statement = (
            select(VoteEvent)
            .where(
                VoteEvent.actor_user_id == user_id,
                VoteEvent.metadata_json["idempotency_key"].as_string()
                == idempotency_key,
            )
            .order_by(VoteEvent.created_at.desc(), VoteEvent.id.desc())
        )
        return cast(VoteEvent | None, await self._session.scalar(statement))

    async def list_user_history(
        self,
        user_id: UUID,
        *,
        campaign_id: UUID | None,
        status: VoteStatus | None,
        date_from: datetime | None,
        date_to: datetime | None,
        page: int,
        page_size: int,
    ) -> tuple[list[tuple[Vote, VotingCampaign, PublicWork]], int]:
        conditions = [Vote.user_id == user_id]
        if campaign_id is not None:
            conditions.append(Vote.campaign_id == campaign_id)
        if status is not None:
            conditions.append(Vote.status == status)
        if date_from is not None:
            conditions.append(Vote.created_at >= date_from)
        if date_to is not None:
            conditions.append(Vote.created_at < date_to)
        total = int(
            await self._session.scalar(select(func.count(Vote.id)).where(*conditions))
            or 0
        )
        statement = (
            select(Vote, VotingCampaign, PublicWork)
            .join(VotingCampaign, VotingCampaign.id == Vote.campaign_id)
            .join(PublicWork, PublicWork.id == Vote.work_id)
            .where(*conditions)
            .order_by(Vote.created_at.desc(), Vote.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = (await self._session.execute(statement)).all()
        return [
            (cast(Vote, row[0]), cast(VotingCampaign, row[1]), cast(PublicWork, row[2]))
            for row in rows
        ], total
