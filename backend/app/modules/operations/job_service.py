import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.modules.audit.service import AuditService
from app.modules.operations.job_models import (
    JobAttempt,
    JobAttemptStatus,
    JobExecution,
    JobExecutionStatus,
)
from app.modules.operations.job_repository import DurableJobRepository

SAFE_NAME = re.compile(r"[A-Za-z0-9_.:-]{1,128}")
SAFE_ERROR_CODE = re.compile(r"[A-Z][A-Z0-9_]{0,63}")
SENSITIVE_KEY_PARTS = (
    "password",
    "token",
    "secret",
    "credential",
    "authorization",
    "cookie",
    "privatekey",
    "apikey",
)


@dataclass(frozen=True, slots=True)
class JobRegistration:
    task_name: str
    queue_name: str
    resource_type: str
    resource_id: str
    idempotency_key: str
    intent: dict[str, object]
    max_attempts: int
    scheduled_at: datetime
    correlation_id: str


@dataclass(frozen=True, slots=True)
class JobAttemptClaim:
    attempt: JobAttempt
    should_execute: bool


class DurableJobService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session = session
        self._jobs = DurableJobRepository(session)
        self._audit = AuditService(session)
        self._clock = clock or (lambda: datetime.now(UTC))

    async def register(self, registration: JobRegistration) -> JobExecution:
        self._validate_registration(registration)
        try:
            async with self._session.begin():
                existing = await self._jobs.get_by_idempotency(
                    task_name=registration.task_name,
                    idempotency_key=registration.idempotency_key,
                    for_update=True,
                )
                if existing is not None:
                    return self._validated_replay(existing, registration)
                job = JobExecution(
                    task_name=registration.task_name,
                    queue_name=registration.queue_name,
                    resource_type=registration.resource_type,
                    resource_id=registration.resource_id,
                    idempotency_key=registration.idempotency_key,
                    intent_json=dict(registration.intent),
                    status=JobExecutionStatus.QUEUED,
                    max_attempts=registration.max_attempts,
                    scheduled_at=self._as_utc(registration.scheduled_at),
                    correlation_id=registration.correlation_id,
                )
                self._jobs.add_job(job)
                await self._session.flush()
                return job
        except IntegrityError:
            # A concurrent registrar can win after the lookup and before flush.
            # Recover only when the expected immutable idempotent record exists.
            async with self._session.begin():
                existing = await self._jobs.get_by_idempotency(
                    task_name=registration.task_name,
                    idempotency_key=registration.idempotency_key,
                    for_update=True,
                )
                if existing is None:
                    raise
                return self._validated_replay(existing, registration)

    async def start_attempt(self, job_id: UUID, *, worker_task_id: str) -> JobAttempt:
        return (await self.claim_attempt(job_id, worker_task_id=worker_task_id)).attempt

    async def resolve_for_execution(
        self,
        job_id: UUID,
        registration: JobRegistration,
    ) -> JobExecution:
        self._validate_registration(registration)
        async with self._session.begin():
            job = await self._require_job(job_id, for_update=True)
            if not self._same_execution_intent(job, registration):
                raise self._error(
                    "JOB_INTENT_MISMATCH",
                    "The worker intent does not match the durable job.",
                    409,
                )
            return job

    async def claim_attempt(
        self, job_id: UUID, *, worker_task_id: str
    ) -> JobAttemptClaim:
        self._validate_name(worker_task_id, "JOB_WORKER_TASK_ID_INVALID")
        async with self._session.begin():
            job = await self._require_job(job_id, for_update=True)
            duplicate = await self._jobs.get_attempt_by_worker_task_id(worker_task_id)
            if duplicate is not None:
                if duplicate.job_id != job_id:
                    raise self._error(
                        "JOB_WORKER_TASK_ID_CONFLICT",
                        "The worker task identifier is already in use.",
                        409,
                    )
                return JobAttemptClaim(attempt=duplicate, should_execute=False)
            if job.status is not JobExecutionStatus.QUEUED:
                raise self._error(
                    "JOB_NOT_STARTABLE",
                    "The job cannot start from its current state.",
                    409,
                )
            attempt_no = job.total_attempts + 1
            attempt = JobAttempt(
                job_id=job.id,
                attempt_no=attempt_no,
                worker_task_id=worker_task_id,
                status=JobAttemptStatus.RUNNING,
                started_at=self._clock(),
            )
            self._jobs.add_attempt(attempt)
            job.status = JobExecutionStatus.RUNNING
            job.total_attempts = attempt_no
            job.version += 1
            await self._session.flush()
            return JobAttemptClaim(attempt=attempt, should_execute=True)

    async def fail_attempt(
        self,
        job_id: UUID,
        attempt_id: UUID,
        *,
        safe_error_code: str,
        retryable: bool = True,
    ) -> JobExecution:
        if SAFE_ERROR_CODE.fullmatch(safe_error_code) is None:
            raise self._error(
                "JOB_ERROR_CODE_INVALID",
                "The job error code is invalid.",
                422,
            )
        async with self._session.begin():
            job = await self._require_job(job_id, for_update=True)
            attempt = await self._require_attempt(attempt_id, for_update=True)
            if attempt.job_id != job.id:
                raise self._error(
                    "JOB_ATTEMPT_MISMATCH",
                    "The attempt does not belong to the job.",
                    409,
                )
            if attempt.status is not JobAttemptStatus.RUNNING:
                return job
            cycle_attempt = attempt.attempt_no - job.replay_count * job.max_attempts
            exhausted = not retryable or cycle_attempt >= job.max_attempts
            attempt.status = (
                JobAttemptStatus.EXHAUSTED
                if exhausted
                else JobAttemptStatus.RETRYABLE_FAILED
            )
            attempt.safe_error_code = safe_error_code
            attempt.finished_at = self._clock()
            job.status = (
                JobExecutionStatus.DEAD_LETTERED
                if exhausted
                else JobExecutionStatus.QUEUED
            )
            job.last_error_code = safe_error_code
            job.completed_at = self._clock() if exhausted else None
            job.version += 1
            return job

    async def succeed_attempt(self, job_id: UUID, attempt_id: UUID) -> JobExecution:
        async with self._session.begin():
            job = await self._require_job(job_id, for_update=True)
            attempt = await self._require_attempt(attempt_id, for_update=True)
            if attempt.job_id != job.id:
                raise self._error(
                    "JOB_ATTEMPT_MISMATCH",
                    "The attempt does not belong to the job.",
                    409,
                )
            if attempt.status is JobAttemptStatus.SUCCEEDED:
                return job
            if attempt.status is not JobAttemptStatus.RUNNING:
                raise self._error(
                    "JOB_ATTEMPT_NOT_RUNNING",
                    "The attempt is not running.",
                    409,
                )
            attempt.status = JobAttemptStatus.SUCCEEDED
            attempt.finished_at = self._clock()
            job.status = JobExecutionStatus.SUCCEEDED
            job.last_error_code = None
            job.completed_at = self._clock()
            job.version += 1
            return job

    async def replay(
        self,
        job_id: UUID,
        *,
        expected_version: int,
        actor_user_id: UUID | None = None,
        reason: str | None = None,
    ) -> JobExecution:
        normalized_reason = self._operator_reason(actor_user_id, reason)
        async with self._session.begin():
            job = await self._require_job(job_id, for_update=False)
            self._require_version(job, expected_version)
            if job.status is not JobExecutionStatus.DEAD_LETTERED:
                raise self._error(
                    "JOB_NOT_REPLAYABLE",
                    "The job cannot be replayed from its current state.",
                    409,
                )
            before = {"status": job.status.value, "version": job.version}
            result = await self._session.execute(
                update(JobExecution)
                .where(
                    JobExecution.id == job.id,
                    JobExecution.version == expected_version,
                    JobExecution.status == JobExecutionStatus.DEAD_LETTERED,
                )
                .values(
                    status=JobExecutionStatus.QUEUED,
                    replay_count=JobExecution.replay_count + 1,
                    completed_at=None,
                    cancel_requested_at=None,
                    version=JobExecution.version + 1,
                )
                .execution_options(synchronize_session=False)
            )
            if self._row_count(result) != 1:
                raise self._version_conflict()
            await self._session.refresh(job)
            if actor_user_id is not None:
                self._audit.record(
                    actor_user_id=actor_user_id,
                    action="operations.job.replayed",
                    resource_type="job_execution",
                    resource_id=str(job.id),
                    before=before,
                    after={
                        "status": job.status.value,
                        "version": job.version,
                        "reason": normalized_reason,
                    },
                )
            return job

    async def cancel(
        self,
        job_id: UUID,
        *,
        expected_version: int,
        actor_user_id: UUID | None = None,
        reason: str | None = None,
    ) -> JobExecution:
        normalized_reason = self._operator_reason(actor_user_id, reason)
        async with self._session.begin():
            job = await self._require_job(job_id, for_update=False)
            self._require_version(job, expected_version)
            if job.status not in {
                JobExecutionStatus.QUEUED,
                JobExecutionStatus.DEAD_LETTERED,
            }:
                raise self._error(
                    "JOB_NOT_CANCELLABLE",
                    "The job cannot be cancelled from its current state.",
                    409,
                )
            before = {"status": job.status.value, "version": job.version}
            now = self._clock()
            result = await self._session.execute(
                update(JobExecution)
                .where(
                    JobExecution.id == job.id,
                    JobExecution.version == expected_version,
                    JobExecution.status.in_(
                        {
                            JobExecutionStatus.QUEUED,
                            JobExecutionStatus.DEAD_LETTERED,
                        }
                    ),
                )
                .values(
                    status=JobExecutionStatus.CANCELLED,
                    cancel_requested_at=now,
                    completed_at=now,
                    version=JobExecution.version + 1,
                )
                .execution_options(synchronize_session=False)
            )
            if self._row_count(result) != 1:
                raise self._version_conflict()
            await self._session.refresh(job)
            if actor_user_id is not None:
                self._audit.record(
                    actor_user_id=actor_user_id,
                    action="operations.job.cancelled",
                    resource_type="job_execution",
                    resource_id=str(job.id),
                    before=before,
                    after={
                        "status": job.status.value,
                        "version": job.version,
                        "reason": normalized_reason,
                    },
                )
            return job

    @classmethod
    def _require_version(cls, job: JobExecution, expected_version: int) -> None:
        if expected_version < 1 or job.version != expected_version:
            raise cls._version_conflict()

    @staticmethod
    def _row_count(result: object) -> int:
        return int(cast(CursorResult[object], result).rowcount)

    @classmethod
    def _version_conflict(cls) -> DomainError:
        return cls._error(
            "JOB_VERSION_CONFLICT",
            "The job was changed by another operation.",
            409,
        )

    @classmethod
    def _operator_reason(
        cls,
        actor_user_id: UUID | None,
        reason: str | None,
    ) -> str | None:
        if actor_user_id is None and reason is None:
            return None
        normalized = " ".join((reason or "").split())
        if actor_user_id is None or not 10 <= len(normalized) <= 500:
            raise cls._error(
                "JOB_REASON_INVALID",
                "The operator reason is invalid.",
                422,
            )
        return normalized

    async def _require_job(self, job_id: UUID, *, for_update: bool) -> JobExecution:
        job = await self._jobs.get_job(job_id, for_update=for_update)
        if job is None:
            raise self._error("JOB_NOT_FOUND", "The job was not found.", 404)
        return job

    async def _require_attempt(
        self, attempt_id: UUID, *, for_update: bool
    ) -> JobAttempt:
        attempt = await self._jobs.get_attempt(attempt_id, for_update=for_update)
        if attempt is None:
            raise self._error(
                "JOB_ATTEMPT_NOT_FOUND", "The job attempt was not found.", 404
            )
        return attempt

    @classmethod
    def _validate_registration(cls, registration: JobRegistration) -> None:
        for identifier in (
            registration.task_name,
            registration.queue_name,
            registration.resource_type,
            registration.resource_id,
            registration.idempotency_key,
            registration.correlation_id,
        ):
            cls._validate_name(identifier, "JOB_INTENT_INVALID")
        if registration.max_attempts < 1 or registration.max_attempts > 20:
            raise cls._error("JOB_INTENT_INVALID", "The job intent is invalid.", 422)
        if not registration.intent or len(registration.intent) > 16:
            raise cls._error("JOB_INTENT_INVALID", "The job intent is invalid.", 422)
        for key, intent_value in registration.intent.items():
            normalized_key = re.sub(r"[^a-z0-9]", "", key.casefold())
            if (
                SAFE_NAME.fullmatch(key) is None
                or any(part in normalized_key for part in SENSITIVE_KEY_PARTS)
                or not cls._safe_intent_value(intent_value)
            ):
                raise cls._error(
                    "JOB_INTENT_INVALID", "The job intent is invalid.", 422
                )

    @staticmethod
    def _safe_intent_value(value: object) -> bool:
        if value is None or isinstance(value, bool | int):
            return True
        return isinstance(value, str) and len(value) <= 256

    @staticmethod
    def _validate_name(value: str, code: str) -> None:
        if SAFE_NAME.fullmatch(value) is None:
            raise DurableJobService._error(code, "The job identifier is invalid.", 422)

    @staticmethod
    def _same_intent(job: JobExecution, registration: JobRegistration) -> bool:
        return (
            DurableJobService._same_execution_intent(job, registration)
            and job.correlation_id == registration.correlation_id
        )

    @staticmethod
    def _same_execution_intent(
        job: JobExecution,
        registration: JobRegistration,
    ) -> bool:
        return (
            job.task_name == registration.task_name
            and job.queue_name == registration.queue_name
            and job.resource_type == registration.resource_type
            and job.resource_id == registration.resource_id
            and job.intent_json == registration.intent
            and job.max_attempts == registration.max_attempts
        )

    @classmethod
    def _validated_replay(
        cls,
        job: JobExecution,
        registration: JobRegistration,
    ) -> JobExecution:
        if not cls._same_intent(job, registration):
            raise cls._error(
                "JOB_IDEMPOTENCY_CONFLICT",
                "The job idempotency key is already bound to another intent.",
                409,
            )
        return job

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        return (
            value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
        )

    @staticmethod
    def _error(code: str, message: str, status_code: int) -> DomainError:
        return DomainError(code=code, message=message, status_code=status_code)

    async def close(self) -> None:
        await self._session.close()
