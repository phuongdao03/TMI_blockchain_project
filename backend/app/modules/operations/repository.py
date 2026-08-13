from datetime import datetime
from typing import cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User
from app.modules.blockchain.models import (
    BlockchainTransaction,
    BlockchainTransactionStatus,
)
from app.modules.dossiers.models import Dossier
from app.modules.operations.job_models import (
    JobAttempt,
    JobAttemptStatus,
    JobExecution,
    JobExecutionStatus,
)
from app.modules.payments.models import PaymentOrder, PaymentStatus
from app.modules.reviews.models import ReviewAssignment, ReviewAssignmentStatus


class OperationsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def dossier_funnel(self) -> dict[str, int]:
        rows = await self._session.execute(
            select(Dossier._status, func.count()).group_by(Dossier._status)
        )
        return {status.value: int(count) for status, count in rows}

    async def overdue_reviews(self, now: datetime) -> int:
        return int(
            (
                await self._session.scalar(
                    select(func.count())
                    .select_from(ReviewAssignment)
                    .where(
                        ReviewAssignment.due_at < now,
                        ReviewAssignment.status.in_(
                            (
                                ReviewAssignmentStatus.ASSIGNED,
                                ReviewAssignmentStatus.IN_PROGRESS,
                            )
                        ),
                    )
                )
            )
            or 0
        )

    async def reviewer_workload(self) -> tuple[tuple[str, int], ...]:
        rows = await self._session.execute(
            select(User.email, func.count())
            .join(User, User.id == ReviewAssignment.reviewer_user_id)
            .where(
                ReviewAssignment.status.in_(
                    (
                        ReviewAssignmentStatus.ASSIGNED,
                        ReviewAssignmentStatus.IN_PROGRESS,
                    )
                )
            )
            .group_by(User.email)
            .order_by(func.count().desc())
            .limit(20)
        )
        return tuple((str(email), int(count)) for email, count in rows)

    async def payment_failures(self) -> int:
        return int(
            (
                await self._session.scalar(
                    select(func.count())
                    .select_from(PaymentOrder)
                    .where(PaymentOrder.status == PaymentStatus.FAILED)
                )
            )
            or 0
        )

    async def blockchain_failures(self) -> int:
        return int(
            (
                await self._session.scalar(
                    select(func.count())
                    .select_from(BlockchainTransaction)
                    .where(
                        BlockchainTransaction.status
                        == BlockchainTransactionStatus.FAILED
                    )
                )
            )
            or 0
        )

    async def job_status_counts(self) -> dict[str, int]:
        rows = await self._session.execute(
            select(JobExecution.status, func.count()).group_by(JobExecution.status)
        )
        return {status.value: int(count) for status, count in rows}

    async def oldest_queued_at(self) -> datetime | None:
        return cast(
            datetime | None,
            await self._session.scalar(
                select(func.min(JobExecution.scheduled_at)).where(
                    JobExecution.status == JobExecutionStatus.QUEUED
                )
            ),
        )

    async def job_retry_failures(self) -> int:
        return int(
            (
                await self._session.scalar(
                    select(func.count())
                    .select_from(JobAttempt)
                    .where(
                        JobAttempt.status.in_(
                            {
                                JobAttemptStatus.RETRYABLE_FAILED,
                                JobAttemptStatus.EXHAUSTED,
                            }
                        )
                    )
                )
            )
            or 0
        )

    async def dead_lettered_jobs_by_task(self) -> dict[str, int]:
        rows = await self._session.execute(
            select(JobExecution.task_name, func.count())
            .where(JobExecution.status == JobExecutionStatus.DEAD_LETTERED)
            .group_by(JobExecution.task_name)
        )
        return {str(task_name): int(count) for task_name, count in rows}
