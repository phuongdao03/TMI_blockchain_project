import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.db.outbox import OutboxEvent
from app.modules.audit.service import AuditService
from app.modules.auth.authorization import AuthorizationPolicy, PolicyRequirement
from app.modules.auth.repositories import OutboxRepository
from app.modules.auth.security import OutboxPayloadCipher
from app.modules.auth.session_service import AuthPrincipal
from app.modules.voting.errors import (
    VotingCampaignForbiddenError,
    VotingCampaignInvalidTransitionError,
    VotingCampaignNotFoundError,
    VotingCampaignPreflightError,
    VotingCampaignReasonRequiredError,
    VotingCampaignRulesLockedError,
    VotingCampaignSlugConflictError,
    VotingParticipantInvalidTransitionError,
    VotingParticipantNotFoundError,
    VotingParticipantSetLockedError,
    VotingParticipantWorkNotEligibleError,
)
from app.modules.voting.models import (
    CampaignEvent,
    CampaignStatus,
    CampaignType,
    CampaignWork,
    CampaignWorkStatus,
    PeriodType,
    VotingCampaign,
)
from app.modules.voting.repository import (
    CampaignParticipantView,
    CampaignWorkRepository,
    VotingCampaignRepository,
)
from app.modules.voting.telemetry import voting_lifecycle_telemetry

CAMPAIGN_READ_PERMISSION = "voting.campaign.read"
CAMPAIGN_MANAGE_PERMISSION = "voting.campaign.manage"
logger = logging.getLogger(__name__)


class CampaignLifecycleAction(StrEnum):
    SCHEDULE = "SCHEDULE"
    ACTIVATE = "ACTIVATE"
    PAUSE = "PAUSE"
    RESUME = "RESUME"
    END = "END"
    CANCEL = "CANCEL"


CAMPAIGN_ACTION_TARGETS: dict[CampaignLifecycleAction, CampaignStatus] = {
    CampaignLifecycleAction.SCHEDULE: CampaignStatus.SCHEDULED,
    CampaignLifecycleAction.ACTIVATE: CampaignStatus.ACTIVE,
    CampaignLifecycleAction.PAUSE: CampaignStatus.PAUSED,
    CampaignLifecycleAction.RESUME: CampaignStatus.ACTIVE,
    CampaignLifecycleAction.END: CampaignStatus.ENDED,
    CampaignLifecycleAction.CANCEL: CampaignStatus.CANCELLED,
}

CAMPAIGN_ALLOWED_ACTIONS: dict[CampaignStatus, frozenset[CampaignLifecycleAction]] = {
    CampaignStatus.DRAFT: frozenset(
        {CampaignLifecycleAction.SCHEDULE, CampaignLifecycleAction.CANCEL}
    ),
    CampaignStatus.SCHEDULED: frozenset(
        {CampaignLifecycleAction.ACTIVATE, CampaignLifecycleAction.CANCEL}
    ),
    CampaignStatus.ACTIVE: frozenset(
        {CampaignLifecycleAction.PAUSE, CampaignLifecycleAction.END}
    ),
    CampaignStatus.PAUSED: frozenset(
        {
            CampaignLifecycleAction.RESUME,
            CampaignLifecycleAction.END,
            CampaignLifecycleAction.CANCEL,
        }
    ),
    CampaignStatus.ENDED: frozenset(),
    CampaignStatus.RESULT_PENDING: frozenset(),
    CampaignStatus.PUBLISHED: frozenset(),
    CampaignStatus.CANCELLED: frozenset(),
}

REASON_REQUIRED_ACTIONS = frozenset(
    {
        CampaignLifecycleAction.PAUSE,
        CampaignLifecycleAction.RESUME,
        CampaignLifecycleAction.END,
        CampaignLifecycleAction.CANCEL,
    }
)


def assert_campaign_transition(
    current: CampaignStatus,
    action: CampaignLifecycleAction,
) -> None:
    if action not in CAMPAIGN_ALLOWED_ACTIONS[current]:
        raise VotingCampaignInvalidTransitionError(
            current=current,
            action=action.value,
        )


@dataclass(frozen=True, slots=True)
class VotingCampaignInput:
    name: str
    slug: str
    description: str
    campaign_type: CampaignType
    period_type: PeriodType
    timezone: str
    start_at: datetime
    end_at: datetime
    max_votes_per_user: int
    max_votes_per_work_per_user: int
    allow_vote_change: bool
    allow_vote_revoke: bool
    require_verified_email: bool
    min_account_age_hours: int
    eligibility_rules: dict[str, object]


class VotingCampaignService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        audit: AuditService,
        payload_cipher: OutboxPayloadCipher,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session = session
        self._repository = VotingCampaignRepository(session)
        self._participants = CampaignWorkRepository(session)
        self._audit = audit
        self._outbox = OutboxRepository(session)
        self._payload_cipher = payload_cipher
        self._clock = clock or (lambda: datetime.now(UTC))

    async def create(
        self,
        principal: AuthPrincipal,
        payload: VotingCampaignInput,
        *,
        request_id: str,
    ) -> VotingCampaign:
        self._require(principal, CAMPAIGN_MANAGE_PERMISSION)
        campaign = VotingCampaign(
            **self._values(payload),
            status=CampaignStatus.DRAFT,
            rule_version=1,
            created_by=principal.user_id,
        )
        try:
            async with self._session.begin():
                if await self._repository.slug_exists(payload.slug):
                    raise VotingCampaignSlugConflictError()
                self._repository.add(campaign)
                await self._session.flush()
                after = self._serialize(campaign)
                self._repository.add_event(
                    self._event(campaign.id, "CAMPAIGN_CREATED", principal, after=after)
                )
                self._audit.record(
                    actor_user_id=principal.user_id,
                    action="voting.campaign.created",
                    resource_type="voting_campaign",
                    resource_id=str(campaign.id),
                    after=after,
                    request_id=request_id,
                )
        except IntegrityError as exc:
            raise VotingCampaignSlugConflictError() from exc
        return campaign

    async def transition(
        self,
        principal: AuthPrincipal,
        campaign_id: UUID,
        action: CampaignLifecycleAction,
        *,
        request_id: str,
        reason: str | None = None,
    ) -> VotingCampaign:
        self._require(principal, CAMPAIGN_MANAGE_PERMISSION)
        try:
            normalized_reason = self._normalize_reason(action, reason)
            async with self._session.begin():
                campaign, changed = await self._apply_transition(
                    campaign_id,
                    action,
                    actor_user_id=principal.user_id,
                    reason=normalized_reason,
                    request_id=request_id,
                    now=self._as_utc(self._clock()),
                )
        except DomainError:
            voting_lifecycle_telemetry.record("manual_failure")
            raise
        voting_lifecycle_telemetry.record(
            "manual_success" if changed else "manual_noop"
        )
        return campaign

    async def reconcile_due(self, *, now: datetime, limit: int = 100) -> int:
        if not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")
        normalized_now = self._as_utc(now)
        async with self._session.begin():
            activation_ids = await self._repository.list_due_activation_ids(
                now=normalized_now,
                limit=limit,
            )
            end_ids = await self._repository.list_due_end_ids(
                now=normalized_now,
                limit=limit,
            )
            missed_activation_ids = await self._repository.list_missed_activation_ids(
                now=normalized_now,
                limit=limit,
            )

        for campaign_id in missed_activation_ids:
            voting_lifecycle_telemetry.record("scheduler_failure")
            logger.error(
                "voting_campaign_activation_window_missed",
                extra={
                    "action": CampaignLifecycleAction.ACTIVATE.value,
                    "campaign_id": str(campaign_id),
                    "error_code": "VOTING_CAMPAIGN_ACTIVATION_WINDOW_MISSED",
                    "outcome": "failure",
                },
            )

        changed_count = 0
        for campaign_id, action in (
            *(
                (campaign_id, CampaignLifecycleAction.ACTIVATE)
                for campaign_id in activation_ids
            ),
            *((campaign_id, CampaignLifecycleAction.END) for campaign_id in end_ids),
        ):
            try:
                async with self._session.begin():
                    _, changed = await self._apply_transition(
                        campaign_id,
                        action,
                        actor_user_id=None,
                        reason="Scheduled lifecycle transition",
                        request_id="voting-lifecycle-scheduler",
                        now=normalized_now,
                    )
            except DomainError as error:
                voting_lifecycle_telemetry.record("scheduler_failure")
                logger.error(
                    "voting_campaign_lifecycle_transition_failed",
                    extra={
                        "action": action.value,
                        "campaign_id": str(campaign_id),
                        "error_code": error.code,
                        "outcome": "failure",
                    },
                )
                continue
            if changed:
                changed_count += 1
                voting_lifecycle_telemetry.record("scheduler_success")
        return changed_count

    async def _apply_transition(
        self,
        campaign_id: UUID,
        action: CampaignLifecycleAction,
        *,
        actor_user_id: UUID | None,
        reason: str | None,
        request_id: str,
        now: datetime,
    ) -> tuple[VotingCampaign, bool]:
        campaign = await self._repository.get(campaign_id, for_update=True)
        if campaign is None:
            raise VotingCampaignNotFoundError()
        target = CAMPAIGN_ACTION_TARGETS[action]
        if campaign.status is target:
            return campaign, False
        assert_campaign_transition(campaign.status, action)
        await self._preflight(campaign, action, now=now)
        before = self._serialize(campaign)
        campaign.status = target
        await self._session.flush()
        after = self._serialize(campaign)
        event_type = f"CAMPAIGN_{self._past_tense(action).upper()}"
        self._repository.add_event(
            CampaignEvent(
                campaign_id=campaign.id,
                event_type=event_type,
                actor_user_id=actor_user_id,
                reason=reason,
                before_snapshot=before,
                after_snapshot=after,
                created_at=now,
            )
        )
        audit_action = f"voting.campaign.{self._past_tense(action)}"
        self._audit.record(
            actor_user_id=actor_user_id,
            action=audit_action,
            resource_type="voting_campaign",
            resource_id=str(campaign.id),
            before=before,
            after={**after, "reason": reason},
            request_id=request_id,
        )
        encrypted = self._payload_cipher.encrypt(
            {
                "campaign_id": str(campaign.id),
                "status": campaign.status.value,
                "action": action.value,
                "rule_version": str(campaign.rule_version),
            },
            event_type=audit_action,
            aggregate_id=campaign.id,
        )
        self._outbox.add(
            OutboxEvent(
                event_type=audit_action,
                aggregate_type="voting_campaign",
                aggregate_id=campaign.id,
                payload_ciphertext=encrypted.ciphertext,
                payload_nonce=encrypted.nonce,
                key_id=encrypted.key_id,
                occurred_at=now,
            )
        )
        logger.info(
            "voting_campaign_lifecycle_transitioned",
            extra={
                "action": action.value,
                "campaign_id": str(campaign.id),
                "outcome": "success",
                "user_id": str(actor_user_id) if actor_user_id is not None else None,
            },
        )
        return campaign, True

    async def _preflight(
        self,
        campaign: VotingCampaign,
        action: CampaignLifecycleAction,
        *,
        now: datetime,
    ) -> None:
        reasons: list[str] = []
        start_at = self._as_utc(campaign.start_at)
        end_at = self._as_utc(campaign.end_at)
        if action is CampaignLifecycleAction.SCHEDULE and start_at <= now:
            reasons.append("START_TIME_NOT_FUTURE")
        if (
            action
            in {
                CampaignLifecycleAction.ACTIVATE,
                CampaignLifecycleAction.RESUME,
            }
            and not start_at <= now < end_at
        ):
            reasons.append("OUTSIDE_ACTIVE_WINDOW")
        if (
            action
            in {
                CampaignLifecycleAction.SCHEDULE,
                CampaignLifecycleAction.ACTIVATE,
                CampaignLifecycleAction.RESUME,
            }
            and await self._repository.count_eligible_participants(campaign.id) < 1
        ):
            reasons.append("NO_ELIGIBLE_PARTICIPANTS")
        if reasons:
            raise VotingCampaignPreflightError(reasons)

    @staticmethod
    def _normalize_reason(
        action: CampaignLifecycleAction,
        reason: str | None,
    ) -> str | None:
        normalized = " ".join(reason.split()) if reason is not None else None
        if action in REASON_REQUIRED_ACTIONS and not normalized:
            raise VotingCampaignReasonRequiredError()
        return normalized

    @staticmethod
    def _past_tense(action: CampaignLifecycleAction) -> str:
        return {
            CampaignLifecycleAction.SCHEDULE: "scheduled",
            CampaignLifecycleAction.ACTIVATE: "activated",
            CampaignLifecycleAction.PAUSE: "paused",
            CampaignLifecycleAction.RESUME: "resumed",
            CampaignLifecycleAction.END: "ended",
            CampaignLifecycleAction.CANCEL: "cancelled",
        }[action]

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    async def update(
        self,
        principal: AuthPrincipal,
        campaign_id: UUID,
        payload: VotingCampaignInput,
        *,
        request_id: str,
    ) -> VotingCampaign:
        self._require(principal, CAMPAIGN_MANAGE_PERMISSION)
        try:
            async with self._session.begin():
                campaign = await self._repository.get(campaign_id, for_update=True)
                if campaign is None:
                    raise VotingCampaignNotFoundError()
                if campaign.status is not CampaignStatus.DRAFT:
                    raise VotingCampaignRulesLockedError()
                if await self._repository.slug_exists(
                    payload.slug, exclude_id=campaign.id
                ):
                    raise VotingCampaignSlugConflictError()
                before = self._serialize(campaign)
                for field, value in self._values(payload).items():
                    setattr(campaign, field, value)
                await self._session.flush()
                after = self._serialize(campaign)
                self._repository.add_event(
                    self._event(
                        campaign.id,
                        "CAMPAIGN_UPDATED",
                        principal,
                        before=before,
                        after=after,
                    )
                )
                self._audit.record(
                    actor_user_id=principal.user_id,
                    action="voting.campaign.updated",
                    resource_type="voting_campaign",
                    resource_id=str(campaign.id),
                    before=before,
                    after=after,
                    request_id=request_id,
                )
        except IntegrityError as exc:
            raise VotingCampaignSlugConflictError() from exc
        return campaign

    async def get(self, principal: AuthPrincipal, campaign_id: UUID) -> VotingCampaign:
        self._require(principal, CAMPAIGN_READ_PERMISSION)
        campaign = await self._repository.get(campaign_id)
        if campaign is None:
            raise VotingCampaignNotFoundError()
        return campaign

    async def list(
        self,
        principal: AuthPrincipal,
        *,
        status: CampaignStatus | None,
        page: int,
        page_size: int,
    ) -> tuple[tuple[VotingCampaign, ...], int]:
        self._require(principal, CAMPAIGN_READ_PERMISSION)
        return await self._repository.list(
            status=status,
            page=page,
            page_size=page_size,
        )

    async def list_participants(
        self,
        principal: AuthPrincipal,
        campaign_id: UUID,
        *,
        status: CampaignWorkStatus | None,
        page: int,
        page_size: int,
    ) -> tuple[tuple[CampaignParticipantView, ...], int]:
        self._require(principal, CAMPAIGN_READ_PERMISSION)
        if await self._repository.get(campaign_id) is None:
            raise VotingCampaignNotFoundError()
        return await self._participants.list(
            campaign_id,
            status=status,
            page=page,
            page_size=page_size,
        )

    async def add_participant(
        self,
        principal: AuthPrincipal,
        campaign_id: UUID,
        work_id: UUID,
        *,
        reason: str,
        request_id: str,
    ) -> CampaignParticipantView:
        rows = await self.add_participants(
            principal,
            campaign_id,
            (work_id,),
            reason=reason,
            request_id=request_id,
        )
        return rows[0]

    async def add_participants(
        self,
        principal: AuthPrincipal,
        campaign_id: UUID,
        work_ids: tuple[UUID, ...],
        *,
        reason: str,
        request_id: str,
    ) -> tuple[CampaignParticipantView, ...]:
        self._require(principal, CAMPAIGN_MANAGE_PERMISSION)
        normalized_reason = self._participant_reason(reason)
        now = self._as_utc(self._clock())
        async with self._session.begin():
            campaign = await self._mutable_participant_campaign(campaign_id)
            eligible = []
            for work_id in work_ids:
                work = await self._participants.eligible_work(work_id)
                if work is None:
                    raise VotingParticipantWorkNotEligibleError()
                eligible.append(work)

            result: list[CampaignWork] = []
            for work in eligible:
                participant = await self._participants.get_by_work(campaign.id, work.id)
                if (
                    participant is not None
                    and participant.status is not CampaignWorkStatus.REMOVED
                ):
                    result.append(participant)
                    continue
                before = self._serialize_participant(participant)
                if participant is None:
                    participant = CampaignWork(
                        campaign_id=campaign.id,
                        work_id=work.id,
                        status=CampaignWorkStatus.PENDING,
                        metadata_json={},
                    )
                    self._participants.add(participant)
                else:
                    participant.status = CampaignWorkStatus.PENDING
                    participant.approved_by = None
                    participant.approved_at = None
                await self._session.flush()
                self._record_participant_change(
                    campaign=campaign,
                    participant=participant,
                    action="added",
                    event_type="CAMPAIGN_PARTICIPANT_ADDED",
                    principal=principal,
                    reason=normalized_reason,
                    request_id=request_id,
                    now=now,
                    before=before,
                )
                result.append(participant)
            views = tuple(
                [
                    await self._participants.view(campaign_id, participant.id)
                    for participant in result
                ]
            )
        if any(view is None for view in views):
            raise VotingParticipantNotFoundError()
        return tuple(view for view in views if view is not None)

    async def approve_participant(
        self,
        principal: AuthPrincipal,
        campaign_id: UUID,
        participant_id: UUID,
        *,
        reason: str,
        request_id: str,
    ) -> CampaignParticipantView:
        self._require(principal, CAMPAIGN_MANAGE_PERMISSION)
        normalized_reason = self._participant_reason(reason)
        now = self._as_utc(self._clock())
        async with self._session.begin():
            campaign = await self._mutable_participant_campaign(campaign_id)
            participant = await self._participants.get(
                campaign.id, participant_id, for_update=True
            )
            if participant is None:
                raise VotingParticipantNotFoundError()
            if participant.status is CampaignWorkStatus.REMOVED:
                raise VotingParticipantInvalidTransitionError()
            if await self._participants.eligible_work(participant.work_id) is None:
                raise VotingParticipantWorkNotEligibleError()
            if participant.status is CampaignWorkStatus.APPROVED:
                view = await self._participants.view(campaign.id, participant.id)
                if view is None:
                    raise VotingParticipantNotFoundError()
                return view
            before = self._serialize_participant(participant)
            participant.status = CampaignWorkStatus.APPROVED
            participant.approved_by = principal.user_id
            participant.approved_at = now
            await self._session.flush()
            self._record_participant_change(
                campaign=campaign,
                participant=participant,
                action="approved",
                event_type="CAMPAIGN_PARTICIPANT_APPROVED",
                principal=principal,
                reason=normalized_reason,
                request_id=request_id,
                now=now,
                before=before,
            )
            view = await self._participants.view(campaign_id, participant_id)
            if view is None:
                raise VotingParticipantNotFoundError()
        return view

    async def remove_participant(
        self,
        principal: AuthPrincipal,
        campaign_id: UUID,
        participant_id: UUID,
        *,
        reason: str,
        request_id: str,
    ) -> CampaignParticipantView:
        self._require(principal, CAMPAIGN_MANAGE_PERMISSION)
        normalized_reason = self._participant_reason(reason)
        now = self._as_utc(self._clock())
        async with self._session.begin():
            campaign = await self._mutable_participant_campaign(campaign_id)
            participant = await self._participants.get(
                campaign.id, participant_id, for_update=True
            )
            if participant is None:
                raise VotingParticipantNotFoundError()
            if participant.status is CampaignWorkStatus.REMOVED:
                view = await self._participants.view(campaign.id, participant.id)
                if view is None:
                    raise VotingParticipantNotFoundError()
                return view
            before = self._serialize_participant(participant)
            participant.status = CampaignWorkStatus.REMOVED
            participant.approved_by = None
            participant.approved_at = None
            await self._session.flush()
            self._record_participant_change(
                campaign=campaign,
                participant=participant,
                action="removed",
                event_type="CAMPAIGN_PARTICIPANT_REMOVED",
                principal=principal,
                reason=normalized_reason,
                request_id=request_id,
                now=now,
                before=before,
            )
            view = await self._participants.view(campaign_id, participant_id)
            if view is None:
                raise VotingParticipantNotFoundError()
        return view

    async def _mutable_participant_campaign(self, campaign_id: UUID) -> VotingCampaign:
        campaign = await self._repository.get(campaign_id, for_update=True)
        if campaign is None:
            raise VotingCampaignNotFoundError()
        if campaign.status not in {CampaignStatus.DRAFT, CampaignStatus.SCHEDULED}:
            raise VotingParticipantSetLockedError(current=campaign.status)
        return campaign

    def _record_participant_change(
        self,
        *,
        campaign: VotingCampaign,
        participant: CampaignWork,
        action: str,
        event_type: str,
        principal: AuthPrincipal,
        reason: str,
        request_id: str,
        now: datetime,
        before: dict[str, object] | None,
    ) -> None:
        after = self._serialize_participant(participant)
        assert after is not None
        self._repository.add_event(
            CampaignEvent(
                campaign_id=campaign.id,
                event_type=event_type,
                actor_user_id=principal.user_id,
                reason=reason,
                before_snapshot=before,
                after_snapshot=after,
                created_at=now,
            )
        )
        audit_action = f"voting.campaign.participant_{action}"
        self._audit.record(
            actor_user_id=principal.user_id,
            action=audit_action,
            resource_type="campaign_work",
            resource_id=str(participant.id),
            before=before,
            after={**after, "reason": reason},
            request_id=request_id,
        )
        encrypted = self._payload_cipher.encrypt(
            {
                "campaign_id": str(campaign.id),
                "participant_id": str(participant.id),
                "work_id": str(participant.work_id),
                "status": participant.status.value,
            },
            event_type=audit_action,
            aggregate_id=participant.id,
        )
        self._outbox.add(
            OutboxEvent(
                event_type=audit_action,
                aggregate_type="campaign_work",
                aggregate_id=participant.id,
                payload_ciphertext=encrypted.ciphertext,
                payload_nonce=encrypted.nonce,
                key_id=encrypted.key_id,
                occurred_at=now,
            )
        )
        logger.info(
            "voting_campaign_participant_changed",
            extra={
                "action": action,
                "campaign_id": str(campaign.id),
                "work_id": str(participant.work_id),
                "outcome": "success",
                "user_id": str(principal.user_id),
            },
        )

    @staticmethod
    def _participant_reason(reason: str) -> str:
        normalized = " ".join(reason.split())
        if not normalized:
            raise VotingCampaignReasonRequiredError()
        return normalized

    @staticmethod
    def _serialize_participant(
        participant: CampaignWork | None,
    ) -> dict[str, object] | None:
        if participant is None:
            return None
        return {
            "id": str(participant.id),
            "campaign_id": str(participant.campaign_id),
            "work_id": str(participant.work_id),
            "status": participant.status.value,
            "approved_at": (
                participant.approved_at.isoformat()
                if participant.approved_at is not None
                else None
            ),
        }

    @staticmethod
    def _require(principal: AuthPrincipal, permission: str) -> None:
        AuthorizationPolicy.require_capability(
            principal,
            PolicyRequirement(permission=permission, allow_super_admin=False),
            VotingCampaignForbiddenError,
        )

    @staticmethod
    def _values(payload: VotingCampaignInput) -> dict[str, object]:
        return {
            "name": payload.name,
            "slug": payload.slug,
            "description": payload.description,
            "campaign_type": payload.campaign_type,
            "period_type": payload.period_type,
            "timezone": payload.timezone,
            "start_at": payload.start_at.astimezone(UTC),
            "end_at": payload.end_at.astimezone(UTC),
            "max_votes_per_user": payload.max_votes_per_user,
            "max_votes_per_work_per_user": payload.max_votes_per_work_per_user,
            "allow_vote_change": payload.allow_vote_change,
            "allow_vote_revoke": payload.allow_vote_revoke,
            "require_verified_email": payload.require_verified_email,
            "min_account_age_hours": payload.min_account_age_hours,
            "eligibility_rules": payload.eligibility_rules,
        }

    @staticmethod
    def _serialize(campaign: VotingCampaign) -> dict[str, object]:
        return {
            "id": str(campaign.id),
            "name": campaign.name,
            "slug": campaign.slug,
            "description": campaign.description,
            "status": campaign.status.value,
            "campaign_type": campaign.campaign_type.value,
            "period_type": campaign.period_type.value,
            "timezone": campaign.timezone,
            "start_at": campaign.start_at.isoformat(),
            "end_at": campaign.end_at.isoformat(),
            "max_votes_per_user": campaign.max_votes_per_user,
            "max_votes_per_work_per_user": campaign.max_votes_per_work_per_user,
            "allow_vote_change": campaign.allow_vote_change,
            "allow_vote_revoke": campaign.allow_vote_revoke,
            "require_verified_email": campaign.require_verified_email,
            "min_account_age_hours": campaign.min_account_age_hours,
            "eligibility_rules": campaign.eligibility_rules,
            "rule_version": campaign.rule_version,
        }

    @staticmethod
    def _event(
        campaign_id: UUID,
        event_type: str,
        principal: AuthPrincipal,
        *,
        before: dict[str, object] | None = None,
        after: dict[str, object] | None = None,
    ) -> CampaignEvent:
        return CampaignEvent(
            campaign_id=campaign_id,
            event_type=event_type,
            actor_user_id=principal.user_id,
            before_snapshot=before,
            after_snapshot=after,
            created_at=datetime.now(UTC),
        )
