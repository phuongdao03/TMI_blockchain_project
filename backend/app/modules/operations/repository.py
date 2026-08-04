from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.blockchain.models import (
    BlockchainTransaction,
    BlockchainTransactionStatus,
)
from app.modules.dossiers.models import Dossier
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
            select(ReviewAssignment.reviewer_user_id, func.count())
            .where(
                ReviewAssignment.status.in_(
                    (
                        ReviewAssignmentStatus.ASSIGNED,
                        ReviewAssignmentStatus.IN_PROGRESS,
                    )
                )
            )
            .group_by(ReviewAssignment.reviewer_user_id)
            .order_by(func.count().desc())
            .limit(20)
        )
        return tuple((str(user_id), int(count)) for user_id, count in rows)

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
