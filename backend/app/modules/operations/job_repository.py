from typing import cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.operations.job_models import JobAttempt, JobExecution


class DurableJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add_job(self, job: JobExecution) -> None:
        self._session.add(job)

    def add_attempt(self, attempt: JobAttempt) -> None:
        self._session.add(attempt)

    async def get_job(
        self, job_id: UUID, *, for_update: bool = False
    ) -> JobExecution | None:
        statement = select(JobExecution).where(JobExecution.id == job_id)
        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        return cast(JobExecution | None, await self._session.scalar(statement))

    async def get_by_idempotency(
        self, *, task_name: str, idempotency_key: str, for_update: bool = False
    ) -> JobExecution | None:
        statement = select(JobExecution).where(
            JobExecution.task_name == task_name,
            JobExecution.idempotency_key == idempotency_key,
        )
        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        return cast(JobExecution | None, await self._session.scalar(statement))

    async def get_attempt(
        self, attempt_id: UUID, *, for_update: bool = False
    ) -> JobAttempt | None:
        statement = select(JobAttempt).where(JobAttempt.id == attempt_id)
        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        return cast(JobAttempt | None, await self._session.scalar(statement))

    async def get_attempt_by_worker_task_id(
        self, worker_task_id: str
    ) -> JobAttempt | None:
        return cast(
            JobAttempt | None,
            await self._session.scalar(
                select(JobAttempt).where(JobAttempt.worker_task_id == worker_task_id)
            ),
        )

    async def list_jobs(
        self,
        *,
        status: str | None,
        task_name: str | None,
        offset: int,
        limit: int,
    ) -> tuple[tuple[JobExecution, ...], int]:
        filters = []
        if status is not None:
            filters.append(JobExecution.status == status)
        if task_name is not None:
            filters.append(JobExecution.task_name == task_name)
        total = await self._session.scalar(
            select(func.count()).select_from(JobExecution).where(*filters)
        )
        rows = await self._session.scalars(
            select(JobExecution)
            .where(*filters)
            .order_by(JobExecution.created_at.desc(), JobExecution.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return tuple(rows.all()), int(total or 0)

    async def list_attempts(self, job_id: UUID) -> tuple[JobAttempt, ...]:
        rows = await self._session.scalars(
            select(JobAttempt)
            .where(JobAttempt.job_id == job_id)
            .order_by(JobAttempt.attempt_no)
        )
        return tuple(rows.all())
