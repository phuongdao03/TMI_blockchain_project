import asyncio
from typing import Protocol
from uuid import UUID

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.modules.payments.provider import build_payment_gateway
from app.modules.payments.service import PaymentService
from app.workers.celery_app import celery_app
from app.workers.durable import DurableJobRunner
from app.workers.job_intents import payment_reconciliation_intent


class BoundTaskRequest(Protocol):
    id: str | None
    retries: int


class BoundTask(Protocol):
    request: BoundTaskRequest


def _task_identity(task: BoundTask) -> tuple[str, int]:
    task_id = task.request.id
    if not task_id:
        raise RuntimeError("Celery task identity is unavailable.")
    return task_id, int(task.request.retries)


def _payment_error_code(error: Exception) -> str:
    return (
        "PAYMENT_PROVIDER_UNAVAILABLE"
        if isinstance(error, ConnectionError)
        else "PAYMENT_WORKER_FAILED"
    )


def _payment_retryable(error: Exception) -> bool:
    return isinstance(error, ConnectionError)


async def _run_durable_payment_reconciliation(
    *,
    task_id: str,
    retry_no: int,
    durable_job_id: UUID | None = None,
    runner: DurableJobRunner | None = None,
) -> int | None:
    return await (runner or DurableJobRunner(get_session_factory())).run(
        payment_reconciliation_intent(task_id=task_id),
        worker_task_id=f"{task_id}:{retry_no + 1}",
        operation=_reconcile_pending_payments,
        durable_job_id=durable_job_id,
        error_code_for=_payment_error_code,
        retryable_for=_payment_retryable,
    )


async def _reconcile_pending_payments() -> int:
    settings = get_settings()
    if settings.payment_provider.strip().lower() != "payos":
        return 0
    gateway = build_payment_gateway(settings)
    try:
        async with get_session_factory()() as session:
            service = PaymentService(
                session=session,
                gateway=gateway,
                provider_name="payos",
                amount_minor=settings.payment_amount_minor,
                currency=settings.payment_currency,
                order_ttl_seconds=settings.payment_order_ttl_seconds,
                enqueue_certificate_issue=lambda dossier_id: celery_app.send_task(
                    "app.workers.certificate_tasks.issue_certificate",
                    args=[str(dossier_id)],
                ),
            )
            return await service.reconcile_pending()
    finally:
        await gateway.close()


@celery_app.task(  # type: ignore[untyped-decorator]
    bind=True,
    autoretry_for=(ConnectionError,),
    max_retries=3,
    retry_backoff=True,
    retry_jitter=True,
)
def reconcile_pending_payments(
    task: BoundTask,
    durable_job_id: str | None = None,
) -> int | None:
    task_id, retry_no = _task_identity(task)
    return asyncio.run(
        _run_durable_payment_reconciliation(
            task_id=task_id,
            retry_no=retry_no,
            durable_job_id=UUID(durable_job_id) if durable_job_id else None,
        )
    )
