from collections.abc import Awaitable, Callable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.modules.auth.authorization import AuthorizationPolicy, PolicyRequirement
from app.modules.auth.session_service import AuthPrincipal
from app.modules.operations.job_models import JobAttempt, JobExecution
from app.modules.operations.job_repository import DurableJobRepository
from app.modules.operations.job_service import DurableJobService
from app.workers.dispatcher import validate_durable_job_replay

READ_ROLES = frozenset({"SUPER_ADMIN"})
ReplayPublisher = Callable[[JobExecution], Awaitable[None]]


class JobOperationsService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        replay_publisher: ReplayPublisher | None = None,
    ) -> None:
        self._session = session
        self._jobs = DurableJobRepository(session)
        self._lifecycle = DurableJobService(session)
        self._replay_publisher = replay_publisher

    async def list_jobs(
        self,
        principal: AuthPrincipal,
        *,
        page: int,
        page_size: int,
        status: str | None = None,
        task_name: str | None = None,
    ) -> tuple[tuple[JobExecution, ...], int]:
        self._require_read(principal)
        async with self._session.begin():
            return await self._jobs.list_jobs(
                status=status,
                task_name=task_name,
                offset=(page - 1) * page_size,
                limit=page_size,
            )

    async def detail(
        self,
        principal: AuthPrincipal,
        job_id: UUID,
    ) -> tuple[JobExecution, tuple[JobAttempt, ...]]:
        self._require_read(principal)
        async with self._session.begin():
            job = await self._jobs.get_job(job_id)
            if job is None:
                raise self._error("JOB_NOT_FOUND", "The job was not found.", 404)
            return job, await self._jobs.list_attempts(job.id)

    async def replay_job(
        self,
        principal: AuthPrincipal,
        job_id: UUID,
        *,
        expected_version: int,
        reason: str,
    ) -> JobExecution:
        self._require_manage(principal)
        if self._replay_publisher is None:
            raise self._error(
                "JOB_REPLAY_UNAVAILABLE",
                "Job replay is unavailable.",
                503,
            )
        async with self._session.begin():
            candidate = await self._jobs.get_job(job_id)
            if candidate is None:
                raise self._error("JOB_NOT_FOUND", "The job was not found.", 404)
            try:
                validate_durable_job_replay(candidate)
            except RuntimeError as exc:
                raise self._error(
                    "JOB_NOT_REPLAYABLE",
                    "The job type cannot be replayed.",
                    409,
                ) from exc
        replayed = await self._lifecycle.replay(
            job_id,
            expected_version=expected_version,
            actor_user_id=principal.user_id,
            reason=reason,
        )
        await self._replay_publisher(replayed)
        return replayed

    async def cancel_job(
        self,
        principal: AuthPrincipal,
        job_id: UUID,
        *,
        expected_version: int,
        reason: str,
    ) -> JobExecution:
        self._require_manage(principal)
        return await self._lifecycle.cancel(
            job_id,
            expected_version=expected_version,
            actor_user_id=principal.user_id,
            reason=reason,
        )

    @staticmethod
    def _require_read(principal: AuthPrincipal) -> None:
        if "operations.jobs.manage" in principal.permissions:
            return
        JobOperationsService._require(
            principal,
            PolicyRequirement(
                permission="operations.read",
                compatible_roles=READ_ROLES,
            ),
        )

    @staticmethod
    def _require_manage(principal: AuthPrincipal) -> None:
        JobOperationsService._require(
            principal,
            PolicyRequirement(permission="operations.jobs.manage"),
        )

    @staticmethod
    def _require(principal: AuthPrincipal, requirement: PolicyRequirement) -> None:
        AuthorizationPolicy.require_capability(
            principal,
            requirement,
            lambda: JobOperationsService._error(
                "JOB_OPERATIONS_FORBIDDEN",
                "Job operations are forbidden.",
                403,
            ),
        )

    @staticmethod
    def _error(code: str, message: str, status_code: int) -> DomainError:
        return DomainError(code=code, message=message, status_code=status_code)
