import hashlib
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.outbox import OutboxEvent
from app.modules.audit.service import AuditService
from app.modules.auth.repositories import OutboxRepository
from app.modules.auth.security import OutboxPayloadCipher
from app.modules.auth.session_service import AuthPrincipal
from app.modules.voting.eligibility import VotingEligibilityService
from app.modules.voting.errors import (
    VotingChangeNotAllowedError,
    VotingEligibilityDeniedError,
    VotingIdempotencyConflictError,
    VotingRevokeNotAllowedError,
    VotingVoteNotFoundError,
)
from app.modules.voting.events import VoteEventType, VoteOutboxEventType
from app.modules.voting.models import Vote, VoteEvent, VoteStatus
from app.modules.voting.types import EligibilityAction, EligibilityReason
from app.modules.voting.vote_repository import VoteRepository

VOTE_SOURCE_WEB = "WEB"
logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class VoteMutationResult:
    vote_id: UUID
    campaign_id: UUID
    work_id: UUID
    status: VoteStatus
    remaining_quota: int
    rule_version: int
    created_at: datetime
    previous_vote_id: UUID | None = None


class VotingService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        eligibility: VotingEligibilityService,
        audit: AuditService,
        payload_cipher: OutboxPayloadCipher,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session = session
        self._eligibility = eligibility
        self._repository = VoteRepository(session)
        self._audit = audit
        self._outbox = OutboxRepository(session)
        self._payload_cipher = payload_cipher
        self._clock = clock or (lambda: datetime.now(UTC))

    async def create_vote(
        self,
        principal: AuthPrincipal,
        campaign_id: UUID,
        work_id: UUID,
        *,
        idempotency_key: str,
        request_id: str,
    ) -> VoteMutationResult:
        fingerprint = self._fingerprint(campaign_id, work_id)
        now = self._utc(self._clock())
        async with self._session.begin():
            await self._repository.lock_user(principal.user_id)
            existing = await self._repository.get_by_idempotency(
                principal.user_id,
                idempotency_key,
            )
            if existing is not None:
                if existing.campaign_id != campaign_id or existing.work_id != work_id:
                    raise VotingIdempotencyConflictError()
                return await self._replay(existing)

            decision = await self._eligibility.evaluate(
                principal,
                campaign_id,
                work_id=work_id,
                for_update=True,
            )
            if not decision.can_vote:
                raise VotingEligibilityDeniedError(decision.reasons[0])
            vote = Vote(
                campaign_id=campaign_id,
                work_id=work_id,
                user_id=principal.user_id,
                status=VoteStatus.VALID,
                source=VOTE_SOURCE_WEB,
                idempotency_key=idempotency_key,
            )
            self._repository.add(vote)
            try:
                await self._session.flush()
            except IntegrityError as exc:
                raise VotingEligibilityDeniedError(
                    EligibilityReason.ALREADY_VOTED
                ) from exc
            result = VoteMutationResult(
                vote_id=vote.id,
                campaign_id=campaign_id,
                work_id=work_id,
                status=VoteStatus.VALID,
                remaining_quota=decision.remaining_quota - 1,
                rule_version=decision.rule_version,
                created_at=now,
            )
            metadata = {
                "action": "CREATE",
                "idempotency_key": idempotency_key,
                "idempotency_fingerprint": fingerprint,
                "status": result.status.value,
                "remaining_quota": result.remaining_quota,
                "rule_version": result.rule_version,
                "created_at": now.isoformat(),
                "correlation_id": request_id,
                "causation_id": request_id,
            }
            self._repository.add_event(
                VoteEvent(
                    vote_id=vote.id,
                    event_type=VoteEventType.CREATED.value,
                    actor_user_id=principal.user_id,
                    metadata_json=metadata,
                    created_at=now,
                )
            )
            encrypted = self._payload_cipher.encrypt(
                {
                    "vote_id": str(vote.id),
                    "campaign_id": str(campaign_id),
                    "work_id": str(work_id),
                    "status": VoteStatus.VALID.value,
                    "rule_version": str(result.rule_version),
                    "correlation_id": request_id,
                    "causation_id": request_id,
                },
                event_type=VoteOutboxEventType.CREATED.value,
                aggregate_id=vote.id,
            )
            self._outbox.add(
                OutboxEvent(
                    event_type=VoteOutboxEventType.CREATED.value,
                    aggregate_type="vote",
                    aggregate_id=vote.id,
                    payload_ciphertext=encrypted.ciphertext,
                    payload_nonce=encrypted.nonce,
                    key_id=encrypted.key_id,
                    occurred_at=now,
                )
            )
            self._record_audit(
                principal=principal,
                action="voting.vote.created",
                result=result,
                request_id=request_id,
            )
        logger.info(
            "voting_vote_created",
            extra={
                "action": "create",
                "campaign_id": str(campaign_id),
                "work_id": str(work_id),
                "user_id": str(principal.user_id),
                "outcome": "success",
            },
        )
        return result

    async def change_vote(
        self,
        principal: AuthPrincipal,
        campaign_id: UUID,
        source_vote_id: UUID,
        target_work_id: UUID,
        *,
        idempotency_key: str,
        request_id: str,
    ) -> VoteMutationResult:
        now = self._utc(self._clock())
        async with self._session.begin():
            await self._repository.lock_user(principal.user_id)
            existing = await self._repository.get_by_idempotency(
                principal.user_id, idempotency_key
            )
            if existing is not None:
                if (
                    existing.campaign_id != campaign_id
                    or existing.work_id != target_work_id
                ):
                    raise VotingIdempotencyConflictError()
                return await self._replay(existing)
            if (
                await self._repository.mutation_event_by_key(
                    principal.user_id, idempotency_key
                )
                is not None
            ):
                raise VotingIdempotencyConflictError()
            source = await self._repository.get_owned(
                source_vote_id, principal.user_id, campaign_id
            )
            if source is None or source.status not in {
                VoteStatus.VALID,
                VoteStatus.SUSPICIOUS,
            }:
                raise VotingVoteNotFoundError()
            if source.work_id == target_work_id:
                raise VotingIdempotencyConflictError()
            campaign = await self._repository.campaign(campaign_id)
            if campaign is None:
                raise VotingVoteNotFoundError()
            if not campaign.allow_vote_change:
                raise VotingChangeNotAllowedError()
            decision = await self._eligibility.evaluate(
                principal,
                campaign_id,
                work_id=target_work_id,
                for_update=True,
                action=EligibilityAction.CHANGE,
                exclude_vote_id=source.id,
            )
            if not decision.can_vote:
                raise VotingEligibilityDeniedError(decision.reasons[0])
            source_previous_status = source.status
            source.status = VoteStatus.REVOKED_BY_USER
            source.revoked_at = now
            replacement = Vote(
                campaign_id=campaign_id,
                work_id=target_work_id,
                user_id=principal.user_id,
                status=VoteStatus.VALID,
                source=VOTE_SOURCE_WEB,
                idempotency_key=idempotency_key,
            )
            self._repository.add(replacement)
            try:
                await self._session.flush()
            except IntegrityError as exc:
                raise VotingEligibilityDeniedError(
                    EligibilityReason.ALREADY_VOTED
                ) from exc
            result = VoteMutationResult(
                vote_id=replacement.id,
                campaign_id=campaign_id,
                work_id=target_work_id,
                status=VoteStatus.VALID,
                remaining_quota=decision.remaining_quota - 1,
                rule_version=decision.rule_version,
                created_at=now,
                previous_vote_id=source.id,
            )
            common = self._result_metadata(
                result,
                action="CHANGE",
                idempotency_key=idempotency_key,
                request_id=request_id,
            )
            self._repository.add_event(
                VoteEvent(
                    vote_id=source.id,
                    event_type=VoteEventType.REVOKED_FOR_CHANGE.value,
                    actor_user_id=principal.user_id,
                    metadata_json={
                        "replacement_vote_id": str(replacement.id),
                        "correlation_id": request_id,
                        "causation_id": request_id,
                    },
                    created_at=now,
                )
            )
            self._repository.add_event(
                VoteEvent(
                    vote_id=replacement.id,
                    event_type=VoteEventType.CREATED_BY_CHANGE.value,
                    actor_user_id=principal.user_id,
                    metadata_json=common,
                    created_at=now,
                )
            )
            self._add_outbox(
                event_type=VoteOutboxEventType.CHANGED.value,
                vote=replacement,
                result=result,
                request_id=request_id,
                now=now,
            )
            self._record_audit(
                principal=principal,
                action="voting.vote.changed",
                result=result,
                request_id=request_id,
                before={
                    "vote_id": str(source.id),
                    "status": source_previous_status.value,
                },
            )
        return result

    async def revoke_vote(
        self,
        principal: AuthPrincipal,
        campaign_id: UUID,
        work_id: UUID,
        *,
        idempotency_key: str,
        request_id: str,
    ) -> VoteMutationResult:
        now = self._utc(self._clock())
        async with self._session.begin():
            await self._repository.lock_user(principal.user_id)
            if (
                await self._repository.get_by_idempotency(
                    principal.user_id, idempotency_key
                )
                is not None
            ):
                raise VotingIdempotencyConflictError()
            replay_event = await self._repository.mutation_event_by_key(
                principal.user_id, idempotency_key
            )
            if replay_event is not None:
                vote = await self._repository.get_owned(
                    replay_event.vote_id, principal.user_id, campaign_id
                )
                if vote is None or vote.work_id != work_id:
                    raise VotingIdempotencyConflictError()
                return self._result_from_event(vote, replay_event)
            vote = await self._repository.get_effective(
                principal.user_id, campaign_id, work_id
            )
            if vote is None:
                raise VotingVoteNotFoundError()
            campaign = await self._repository.campaign(campaign_id)
            if campaign is None:
                raise VotingVoteNotFoundError()
            if not campaign.allow_vote_revoke:
                raise VotingRevokeNotAllowedError()
            decision = await self._eligibility.evaluate(
                principal,
                campaign_id,
                work_id=None,
                for_update=True,
                action=EligibilityAction.REVOKE,
            )
            if not decision.can_vote:
                raise VotingEligibilityDeniedError(decision.reasons[0])
            previous_status = vote.status
            vote.status = VoteStatus.REVOKED_BY_USER
            vote.revoked_at = now
            await self._session.flush()
            result = VoteMutationResult(
                vote_id=vote.id,
                campaign_id=campaign_id,
                work_id=work_id,
                status=VoteStatus.REVOKED_BY_USER,
                remaining_quota=decision.remaining_quota + 1,
                rule_version=decision.rule_version,
                created_at=now,
            )
            metadata = self._result_metadata(
                result,
                action="REVOKE",
                idempotency_key=idempotency_key,
                request_id=request_id,
            )
            self._repository.add_event(
                VoteEvent(
                    vote_id=vote.id,
                    event_type=VoteEventType.REVOKED.value,
                    actor_user_id=principal.user_id,
                    metadata_json=metadata,
                    created_at=now,
                )
            )
            self._add_outbox(
                event_type=VoteOutboxEventType.REVOKED.value,
                vote=vote,
                result=result,
                request_id=request_id,
                now=now,
            )
            self._record_audit(
                principal=principal,
                action="voting.vote.revoked",
                result=result,
                request_id=request_id,
                before={"vote_id": str(vote.id), "status": previous_status.value},
            )
        return result

    async def _replay(self, vote: Vote) -> VoteMutationResult:
        event = await self._repository.result_event(vote.id)
        if event is None:
            raise VotingIdempotencyConflictError()
        return self._result_from_event(vote, event)

    def _result_from_event(self, vote: Vote, event: VoteEvent) -> VoteMutationResult:
        metadata = event.metadata_json
        remaining_quota = metadata.get("remaining_quota")
        rule_version = metadata.get("rule_version")
        created_at = metadata.get("created_at")
        previous_vote_id = metadata.get("previous_vote_id")
        status = metadata.get("status")
        if (
            not isinstance(remaining_quota, int)
            or not isinstance(rule_version, int)
            or not isinstance(created_at, str)
        ):
            raise VotingIdempotencyConflictError()
        return VoteMutationResult(
            vote_id=vote.id,
            campaign_id=vote.campaign_id,
            work_id=vote.work_id,
            status=VoteStatus(status) if isinstance(status, str) else vote.status,
            remaining_quota=remaining_quota,
            rule_version=rule_version,
            created_at=self._utc(datetime.fromisoformat(created_at)),
            previous_vote_id=(
                UUID(previous_vote_id) if isinstance(previous_vote_id, str) else None
            ),
        )

    @staticmethod
    def _result_metadata(
        result: VoteMutationResult,
        *,
        action: str,
        idempotency_key: str,
        request_id: str,
    ) -> dict[str, object]:
        return {
            "action": action,
            "idempotency_key": idempotency_key,
            "status": result.status.value,
            "remaining_quota": result.remaining_quota,
            "rule_version": result.rule_version,
            "created_at": result.created_at.isoformat(),
            "previous_vote_id": (
                str(result.previous_vote_id)
                if result.previous_vote_id is not None
                else None
            ),
            "correlation_id": request_id,
            "causation_id": request_id,
        }

    def _add_outbox(
        self,
        *,
        event_type: str,
        vote: Vote,
        result: VoteMutationResult,
        request_id: str,
        now: datetime,
    ) -> None:
        encrypted = self._payload_cipher.encrypt(
            {
                "vote_id": str(vote.id),
                "campaign_id": str(vote.campaign_id),
                "work_id": str(vote.work_id),
                "status": vote.status.value,
                "rule_version": str(result.rule_version),
                "correlation_id": request_id,
                "causation_id": request_id,
            },
            event_type=event_type,
            aggregate_id=vote.id,
        )
        self._outbox.add(
            OutboxEvent(
                event_type=event_type,
                aggregate_type="vote",
                aggregate_id=vote.id,
                payload_ciphertext=encrypted.ciphertext,
                payload_nonce=encrypted.nonce,
                key_id=encrypted.key_id,
                occurred_at=now,
            )
        )

    def _record_audit(
        self,
        *,
        principal: AuthPrincipal,
        action: str,
        result: VoteMutationResult,
        request_id: str,
        before: dict[str, object] | None = None,
    ) -> None:
        self._audit.record(
            actor_user_id=principal.user_id,
            action=action,
            resource_type="vote",
            resource_id=str(result.vote_id),
            before=before,
            after={
                "vote_id": str(result.vote_id),
                "campaign_id": str(result.campaign_id),
                "work_id": str(result.work_id),
                "status": result.status.value,
                "rule_version": result.rule_version,
            },
            request_id=request_id,
        )

    @staticmethod
    def _fingerprint(campaign_id: UUID, work_id: UUID) -> str:
        return hashlib.sha256(f"CREATE:{campaign_id}:{work_id}".encode()).hexdigest()

    @staticmethod
    def _utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
