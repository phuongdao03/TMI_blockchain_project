from datetime import UTC, datetime
from uuid import UUID

from app.modules.operations.job_service import JobRegistration


def blockchain_broadcast_intent(
    transaction_id: UUID,
    *,
    task_id: str,
    scheduled_at: datetime | None = None,
) -> JobRegistration:
    return JobRegistration(
        task_name="blockchain.broadcast",
        queue_name="blockchain",
        resource_type="blockchain_transaction",
        resource_id=str(transaction_id),
        idempotency_key=f"broadcast:{transaction_id}:{task_id}",
        intent={"transaction_id": str(transaction_id)},
        max_attempts=6,
        scheduled_at=scheduled_at or datetime.now(UTC),
        correlation_id=task_id,
    )


def blockchain_confirmation_intent(
    transaction_id: UUID,
    *,
    task_id: str,
    scheduled_at: datetime | None = None,
) -> JobRegistration:
    return JobRegistration(
        task_name="blockchain.confirm",
        queue_name="blockchain",
        resource_type="blockchain_transaction",
        resource_id=str(transaction_id),
        idempotency_key=f"confirm:{transaction_id}:{task_id}",
        intent={"transaction_id": str(transaction_id)},
        max_attempts=6,
        scheduled_at=scheduled_at or datetime.now(UTC),
        correlation_id=task_id,
    )


def blockchain_reconciliation_intent(
    *,
    task_id: str,
    scheduled_at: datetime | None = None,
) -> JobRegistration:
    return JobRegistration(
        task_name="blockchain.reconcile",
        queue_name="blockchain",
        resource_type="blockchain_reconciliation",
        resource_id=task_id,
        idempotency_key=f"reconcile:{task_id}",
        intent={"scope": "pending_transactions"},
        max_attempts=4,
        scheduled_at=scheduled_at or datetime.now(UTC),
        correlation_id=task_id,
    )


def payment_reconciliation_intent(
    *,
    task_id: str,
    scheduled_at: datetime | None = None,
) -> JobRegistration:
    return JobRegistration(
        task_name="payment.reconcile_pending",
        queue_name="payments",
        resource_type="payment_reconciliation",
        resource_id=task_id,
        idempotency_key=f"reconcile:{task_id}",
        intent={"scope": "pending_payments"},
        max_attempts=4,
        scheduled_at=scheduled_at or datetime.now(UTC),
        correlation_id=task_id,
    )
