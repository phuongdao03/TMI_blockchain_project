import logging
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import TypeVar
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.operations.job_models import JobExecutionStatus
from app.modules.operations.job_service import DurableJobService, JobRegistration

T = TypeVar("T")
ErrorClassifier = Callable[[Exception], str]
RetryClassifier = Callable[[Exception], bool]
logger = logging.getLogger(__name__)


class DurableJobRunner:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._clock = clock or (lambda: datetime.now(UTC))

    async def run(
        self,
        registration: JobRegistration,
        *,
        worker_task_id: str,
        operation: Callable[[], Awaitable[T]],
        durable_job_id: UUID | None = None,
        error_code_for: ErrorClassifier | None = None,
        retryable_for: RetryClassifier | None = None,
    ) -> T | None:
        async with self._session_factory() as session:
            lifecycle = DurableJobService(session, clock=self._clock)
            job = (
                await lifecycle.resolve_for_execution(durable_job_id, registration)
                if durable_job_id is not None
                else await lifecycle.register(registration)
            )
            if job.status is JobExecutionStatus.SUCCEEDED:
                return None
            claim = await lifecycle.claim_attempt(
                job.id,
                worker_task_id=worker_task_id,
            )
        log_context = {
            "request_id": registration.correlation_id,
            "job_id": str(job.id),
            "task_name": registration.task_name,
            "queue_name": registration.queue_name,
            "attempt_no": claim.attempt.attempt_no,
            "worker_task_id": worker_task_id,
        }
        if not claim.should_execute:
            logger.info(
                "Duplicate durable job delivery skipped.",
                extra={"action": "durable_job.duplicate_skipped", **log_context},
            )
            return None

        logger.info(
            "Durable job attempt started.",
            extra={"action": "durable_job.started", **log_context},
        )

        try:
            result = await operation()
        except Exception as exc:
            error_code = (
                error_code_for(exc)
                if error_code_for is not None
                else "UNEXPECTED_WORKER_ERROR"
            )
            async with self._session_factory() as session:
                await DurableJobService(session, clock=self._clock).fail_attempt(
                    job.id,
                    claim.attempt.id,
                    safe_error_code=error_code,
                    retryable=(
                        retryable_for(exc) if retryable_for is not None else True
                    ),
                )
            logger.warning(
                "Durable job attempt failed.",
                extra={
                    "action": "durable_job.failed",
                    "error_code": error_code,
                    **log_context,
                },
            )
            raise

        async with self._session_factory() as session:
            await DurableJobService(session, clock=self._clock).succeed_attempt(
                job.id,
                claim.attempt.id,
            )
        logger.info(
            "Durable job attempt succeeded.",
            extra={"action": "durable_job.succeeded", **log_context},
        )
        return result
