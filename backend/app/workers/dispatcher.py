from collections.abc import Callable, Sequence
from typing import Protocol, cast
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import get_session_factory
from app.modules.operations.job_models import JobExecution
from app.modules.operations.job_service import DurableJobService, JobRegistration
from app.workers.celery_app import celery_app
from app.workers.job_intents import (
    blockchain_confirmation_intent,
    blockchain_reconciliation_intent,
)

BLOCKCHAIN_CONFIRMATION_TASK = (
    "app.workers.proof_registry_tasks.confirm_proof_registry_transaction"
)
BLOCKCHAIN_RECONCILIATION_TASK = (
    "app.workers.proof_registry_tasks.reconcile_proof_registry_transactions"
)
PAYMENT_RECONCILIATION_TASK = "app.workers.payment_tasks.reconcile_pending_payments"


class JobReplayPolicyError(RuntimeError):
    pass


class TaskPublisher(Protocol):
    def send_task(self, name: str, **options: object) -> object: ...


class DurableJobDispatcher:
    """Persist immutable work intent before publishing it to the broker."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        publisher: TaskPublisher,
    ) -> None:
        self._session_factory = session_factory
        self._publisher = publisher

    async def dispatch(
        self,
        registration: JobRegistration,
        *,
        celery_task_name: str,
        args: Sequence[object],
        countdown: int | None = None,
    ) -> JobExecution:
        async with self._session_factory() as session:
            job = await DurableJobService(session).register(registration)

        options: dict[str, object] = {
            "args": list(args),
            "kwargs": {"durable_job_id": str(job.id)},
            "queue": registration.queue_name,
            "task_id": registration.correlation_id,
        }
        if countdown is not None:
            options["countdown"] = countdown
        self._publisher.send_task(celery_task_name, **options)
        return job

    def publish_existing(
        self,
        job: JobExecution,
        *,
        celery_task_name: str,
        args: Sequence[object],
        task_id: str,
    ) -> None:
        self._publisher.send_task(
            celery_task_name,
            args=list(args),
            kwargs={"durable_job_id": str(job.id)},
            queue=job.queue_name,
            task_id=task_id,
        )


def _runtime_dispatcher() -> DurableJobDispatcher:
    return DurableJobDispatcher(
        get_session_factory(),
        cast(TaskPublisher, celery_app),
    )


async def enqueue_blockchain_broadcast(transaction_id: UUID) -> None:
    """Compatibility seam for archived callers; legacy writes stay disabled."""
    del transaction_id
    raise JobReplayPolicyError(
        "Archived CertificateRegistry broadcast jobs are not publishable."
    )


async def enqueue_blockchain_confirmation(
    transaction_id: UUID,
    *,
    countdown: int = 15,
) -> None:
    task_id = str(uuid4())
    await _runtime_dispatcher().dispatch(
        blockchain_confirmation_intent(transaction_id, task_id=task_id),
        celery_task_name=BLOCKCHAIN_CONFIRMATION_TASK,
        args=[str(transaction_id)],
        countdown=countdown,
    )


async def enqueue_blockchain_reconciliation() -> None:
    task_id = str(uuid4())
    await _runtime_dispatcher().dispatch(
        blockchain_reconciliation_intent(task_id=task_id),
        celery_task_name=BLOCKCHAIN_RECONCILIATION_TASK,
        args=[],
    )


async def replay_durable_job(
    job: JobExecution,
    *,
    dispatcher: DurableJobDispatcher | None = None,
    task_id_factory: Callable[[], str] | None = None,
) -> None:
    task_name, args = validate_durable_job_replay(job)
    (dispatcher or _runtime_dispatcher()).publish_existing(
        job,
        celery_task_name=task_name,
        args=args,
        task_id=(task_id_factory or (lambda: str(uuid4())))(),
    )


def validate_durable_job_replay(job: JobExecution) -> tuple[str, list[object]]:
    if job.task_name == "blockchain.broadcast":
        raise JobReplayPolicyError(
            "Archived CertificateRegistry broadcast jobs are not replayable."
        )
    if job.task_name == "blockchain.confirm":
        transaction_id = job.intent_json.get("transaction_id")
        if not isinstance(transaction_id, str) or transaction_id != job.resource_id:
            raise JobReplayPolicyError("Blockchain replay intent is invalid.")
        return BLOCKCHAIN_CONFIRMATION_TASK, [transaction_id]
    if job.task_name == "blockchain.reconcile":
        if job.intent_json != {"scope": "pending_transactions"}:
            raise JobReplayPolicyError("Blockchain replay intent is invalid.")
        return BLOCKCHAIN_RECONCILIATION_TASK, []
    if job.task_name == "payment.reconcile_pending":
        if job.intent_json != {"scope": "pending_payments"}:
            raise JobReplayPolicyError("Payment replay intent is invalid.")
        return PAYMENT_RECONCILIATION_TASK, []
    raise JobReplayPolicyError("The durable job type is not replayable.")
