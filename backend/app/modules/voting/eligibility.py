from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.modules.auth.models import UserStatus
from app.modules.auth.session_service import AuthPrincipal
from app.modules.voting.errors import VotingCampaignNotFoundError
from app.modules.voting.models import CampaignStatus
from app.modules.voting.types import EligibilityAction, EligibilityReason
from app.modules.voting.vote_repository import VotingEligibilityRepository


@dataclass(frozen=True, slots=True)
class EligibilitySnapshot:
    user_status: UserStatus
    email_verified_at: datetime | None
    account_created_at: datetime
    roles: tuple[str, ...]
    organization_ids: tuple[UUID, ...]
    campaign_status: CampaignStatus
    start_at: datetime
    end_at: datetime
    require_verified_email: bool
    min_account_age_hours: int
    allowed_roles: tuple[str, ...]
    allowed_organization_ids: tuple[UUID, ...]
    participant_eligible: bool | None
    effective_vote_count: int
    already_voted: bool
    max_votes_per_user: int
    rule_version: int


@dataclass(frozen=True, slots=True)
class VotingEligibilityDecision:
    can_vote: bool
    reasons: tuple[EligibilityReason, ...]
    remaining_quota: int
    rule_version: int
    server_time: datetime


class VotingEligibilityEngine:
    def evaluate(
        self,
        snapshot: EligibilitySnapshot,
        *,
        now: datetime,
        action: EligibilityAction = EligibilityAction.CREATE,
    ) -> VotingEligibilityDecision:
        current_time = self._utc(now)
        reasons: list[EligibilityReason] = []
        if snapshot.user_status is not UserStatus.ACTIVE:
            reasons.append(EligibilityReason.USER_NOT_ACTIVE)
        if snapshot.require_verified_email and snapshot.email_verified_at is None:
            reasons.append(EligibilityReason.EMAIL_NOT_VERIFIED)
        minimum_created_at = current_time - timedelta(
            hours=snapshot.min_account_age_hours
        )
        if self._utc(snapshot.account_created_at) > minimum_created_at:
            reasons.append(EligibilityReason.ACCOUNT_TOO_NEW)

        if snapshot.campaign_status is CampaignStatus.PAUSED:
            reasons.append(EligibilityReason.CAMPAIGN_PAUSED)
        elif snapshot.campaign_status is not CampaignStatus.ACTIVE:
            reasons.append(EligibilityReason.CAMPAIGN_NOT_ACTIVE)
        elif current_time < self._utc(snapshot.start_at):
            reasons.append(EligibilityReason.CAMPAIGN_NOT_STARTED)
        elif current_time >= self._utc(snapshot.end_at):
            reasons.append(EligibilityReason.CAMPAIGN_ENDED)

        if snapshot.allowed_roles and not set(snapshot.roles).intersection(
            snapshot.allowed_roles
        ):
            reasons.append(EligibilityReason.ROLE_NOT_ELIGIBLE)
        if snapshot.allowed_organization_ids and not set(
            snapshot.organization_ids
        ).intersection(snapshot.allowed_organization_ids):
            reasons.append(EligibilityReason.ORGANIZATION_NOT_ELIGIBLE)
        if (
            action is not EligibilityAction.REVOKE
            and snapshot.participant_eligible is False
        ):
            reasons.append(EligibilityReason.WORK_NOT_ELIGIBLE)

        remaining_quota = max(
            snapshot.max_votes_per_user - snapshot.effective_vote_count,
            0,
        )
        if action is not EligibilityAction.REVOKE and remaining_quota == 0:
            reasons.append(EligibilityReason.VOTE_LIMIT_REACHED)
        if action is not EligibilityAction.REVOKE and snapshot.already_voted:
            reasons.append(EligibilityReason.ALREADY_VOTED)
        return VotingEligibilityDecision(
            can_vote=not reasons,
            reasons=tuple(reasons),
            remaining_quota=remaining_quota,
            rule_version=snapshot.rule_version,
            server_time=current_time,
        )

    @staticmethod
    def _utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class VotingEligibilityService:
    def __init__(
        self,
        repository: VotingEligibilityRepository,
        *,
        engine: VotingEligibilityEngine | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._engine = engine or VotingEligibilityEngine()
        self._clock = clock or (lambda: datetime.now(UTC))

    async def evaluate(
        self,
        principal: AuthPrincipal,
        campaign_id: UUID,
        *,
        work_id: UUID | None,
        for_update: bool = False,
        action: EligibilityAction = EligibilityAction.CREATE,
        exclude_vote_id: UUID | None = None,
    ) -> VotingEligibilityDecision:
        snapshot = await self._repository.snapshot(
            user_id=principal.user_id,
            roles=principal.roles,
            campaign_id=campaign_id,
            work_id=work_id,
            for_update=for_update,
            exclude_vote_id=exclude_vote_id,
        )
        if snapshot is None:
            raise VotingCampaignNotFoundError()
        return self._engine.evaluate(snapshot, now=self._clock(), action=action)
