import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar, cast
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from app.modules.blockchain.errors import BlockchainTransientError
from app.modules.operations.job_service import JobRegistration
from app.workers import blockchain_tasks, payment_tasks
from app.workers.durable import DurableJobRunner

T = TypeVar("T")


class CapturingRunner:
    def __init__(self) -> None:
        self.registration: JobRegistration | None = None
        self.worker_task_id: str | None = None
        self.error_code_for: Callable[[Exception], str] | None = None
        self.retryable_for: Callable[[Exception], bool] | None = None

    async def run(
        self,
        registration: JobRegistration,
        *,
        worker_task_id: str,
        operation: Callable[[], Awaitable[T]],
        durable_job_id: UUID | None = None,
        error_code_for: Callable[[Exception], str] | None = None,
        retryable_for: Callable[[Exception], bool] | None = None,
    ) -> T:
        del durable_job_id
        self.registration = registration
        self.worker_task_id = worker_task_id
        self.error_code_for = error_code_for
        self.retryable_for = retryable_for
        return await operation()


def test_blockchain_broadcast_runs_inside_durable_job_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transaction_id = uuid4()
    operation = AsyncMock()
    monkeypatch.setattr(blockchain_tasks, "_broadcast", operation)
    runner = CapturingRunner()

    asyncio.run(
        blockchain_tasks._run_durable_broadcast(
            transaction_id,
            task_id="celery-blockchain-1",
            retry_no=2,
            runner=cast(DurableJobRunner, runner),
        )
    )

    assert runner.registration is not None
    assert runner.registration.task_name == "blockchain.broadcast"
    assert runner.registration.intent == {"transaction_id": str(transaction_id)}
    assert runner.registration.idempotency_key == (
        f"broadcast:{transaction_id}:celery-blockchain-1"
    )
    assert runner.worker_task_id == "celery-blockchain-1:3"
    transient = BlockchainTransientError("temporary")
    assert runner.error_code_for is not None
    assert runner.retryable_for is not None
    assert runner.error_code_for(transient) == "BLOCKCHAIN_TRANSIENT"
    assert runner.retryable_for(transient) is True
    assert runner.retryable_for(ValueError("bad payload")) is False
    operation.assert_awaited_once_with(transaction_id)


def test_payment_reconciliation_runs_inside_durable_job_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operation = AsyncMock(return_value=3)
    monkeypatch.setattr(payment_tasks, "_reconcile_pending_payments", operation)
    runner = CapturingRunner()

    result = asyncio.run(
        payment_tasks._run_durable_payment_reconciliation(
            task_id="celery-payment-1",
            retry_no=0,
            runner=cast(DurableJobRunner, runner),
        )
    )

    assert result == 3
    assert runner.registration is not None
    assert runner.registration.task_name == "payment.reconcile_pending"
    assert runner.registration.idempotency_key == "reconcile:celery-payment-1"
    assert runner.registration.intent == {"scope": "pending_payments"}
    assert runner.worker_task_id == "celery-payment-1:1"
    unavailable = ConnectionError("provider unavailable")
    assert runner.error_code_for is not None
    assert runner.retryable_for is not None
    assert runner.error_code_for(unavailable) == "PAYMENT_PROVIDER_UNAVAILABLE"
    assert runner.retryable_for(unavailable) is True
    assert runner.retryable_for(ValueError("bad payload")) is False
    operation.assert_awaited_once_with()
