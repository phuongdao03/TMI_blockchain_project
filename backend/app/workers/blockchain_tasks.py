import asyncio
from collections.abc import Awaitable, Callable
from typing import Protocol
from uuid import UUID

from redis.asyncio import Redis

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.modules.blockchain.errors import BlockchainTransientError
from app.modules.blockchain.gateway import SUPPORTED_CHAINS, BlockchainGateway
from app.modules.blockchain.nonce_lock import RedisNonceLock
from app.modules.blockchain.service import BlockchainTransactionService
from app.modules.blockchain.signer import create_transaction_signer
from app.workers.celery_app import celery_app
from app.workers.dispatcher import enqueue_blockchain_confirmation
from app.workers.durable import DurableJobRunner
from app.workers.job_intents import (
    blockchain_broadcast_intent,
    blockchain_confirmation_intent,
    blockchain_reconciliation_intent,
)


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


def _blockchain_error_code(error: Exception) -> str:
    return (
        "BLOCKCHAIN_TRANSIENT"
        if isinstance(error, BlockchainTransientError)
        else "BLOCKCHAIN_WORKER_FAILED"
    )


def _blockchain_retryable(error: Exception) -> bool:
    return isinstance(error, BlockchainTransientError)


async def _run_durable_broadcast(
    transaction_id: UUID,
    *,
    task_id: str,
    retry_no: int,
    durable_job_id: UUID | None = None,
    runner: DurableJobRunner | None = None,
) -> bool | None:
    active_runner = runner or DurableJobRunner(get_session_factory())

    async def operation() -> bool:
        await _broadcast(transaction_id)
        return True

    return await active_runner.run(
        blockchain_broadcast_intent(transaction_id, task_id=task_id),
        worker_task_id=f"{task_id}:{retry_no + 1}",
        operation=operation,
        durable_job_id=durable_job_id,
        error_code_for=_blockchain_error_code,
        retryable_for=_blockchain_retryable,
    )


async def _run_durable_confirmation(
    transaction_id: UUID,
    *,
    task_id: str,
    retry_no: int,
    durable_job_id: UUID | None = None,
) -> None:
    await DurableJobRunner(get_session_factory()).run(
        blockchain_confirmation_intent(transaction_id, task_id=task_id),
        worker_task_id=f"{task_id}:{retry_no + 1}",
        operation=lambda: _confirm(transaction_id),
        durable_job_id=durable_job_id,
        error_code_for=_blockchain_error_code,
        retryable_for=_blockchain_retryable,
    )


async def _run_durable_reconciliation(
    *,
    task_id: str,
    retry_no: int,
    durable_job_id: UUID | None = None,
) -> None:
    await DurableJobRunner(get_session_factory()).run(
        blockchain_reconciliation_intent(task_id=task_id),
        worker_task_id=f"{task_id}:{retry_no + 1}",
        operation=_reconcile,
        durable_job_id=durable_job_id,
        error_code_for=_blockchain_error_code,
        retryable_for=_blockchain_retryable,
    )


async def _with_service(
    operation: Callable[[BlockchainTransactionService], Awaitable[None]],
) -> None:
    settings = get_settings()
    secret = settings.blockchain_signer_private_key
    address = settings.certificate_contract_address
    gateway = BlockchainGateway(
        rpc_url=settings.blockchain_rpc_url,
        network=settings.blockchain_network,
        chain_id=settings.blockchain_chain_id,
        contract_address=address,
        abi_path=settings.blockchain_contract_abi_path,
        allowed_networks=SUPPORTED_CHAINS,
        allowed_contracts={settings.blockchain_network: {address}},
    )
    redis_client: Redis = Redis.from_url(settings.redis_url)
    signer = create_transaction_signer(
        mode=settings.blockchain_signer_mode,
        private_key=secret.get_secret_value() if secret is not None else "",
        managed_url=settings.blockchain_managed_signer_url,
        managed_key_id=settings.blockchain_managed_signer_key_id,
        managed_expected_address=settings.blockchain_managed_signer_expected_address,
        managed_timeout_seconds=settings.blockchain_managed_signer_timeout_seconds,
    )
    try:
        async with get_session_factory()() as session:
            service = BlockchainTransactionService(
                session=session,
                gateway=gateway,
                signer=signer,
                nonce_lock=RedisNonceLock(redis_client),
                network=settings.blockchain_network,
                chain_id=settings.blockchain_chain_id,
                contract_address=address,
                required_confirmations=settings.blockchain_required_confirmations,
                nonce_lock_ttl_seconds=settings.blockchain_nonce_lock_ttl_seconds,
                enqueue_certificate_issue=lambda dossier_id: celery_app.send_task(
                    "app.workers.certificate_tasks.issue_certificate",
                    args=[str(dossier_id)],
                ),
                enqueue_certificate_version=lambda version_id: celery_app.send_task(
                    "app.workers.certificate_tasks.render_certificate_version",
                    args=[str(version_id)],
                ),
            )
            await operation(service)
    finally:
        await signer.aclose()
        await gateway.close()
        await redis_client.aclose()


async def _broadcast(transaction_id: UUID) -> None:
    async def operation(service: BlockchainTransactionService) -> None:
        payload = await service.resolve_payload(transaction_id)
        await service.broadcast(transaction_id, payload)

    await _with_service(operation)


async def _confirm(transaction_id: UUID) -> None:
    async def operation(service: BlockchainTransactionService) -> None:
        await service.confirm(transaction_id)

    await _with_service(operation)


async def _reconcile() -> None:
    async def operation(service: BlockchainTransactionService) -> None:
        await service.reconcile()

    await _with_service(operation)


@celery_app.task(
    bind=True,
    autoretry_for=(BlockchainTransientError,),
    max_retries=5,
    retry_backoff=True,
    retry_jitter=True,
)  # type: ignore[untyped-decorator]
def broadcast_blockchain_transaction(
    task: BoundTask,
    transaction_id: str,
    durable_job_id: str | None = None,
) -> None:
    parsed_id = UUID(transaction_id)
    task_id, retry_no = _task_identity(task)
    executed = asyncio.run(
        _run_durable_broadcast(
            parsed_id,
            task_id=task_id,
            retry_no=retry_no,
            durable_job_id=UUID(durable_job_id) if durable_job_id else None,
        )
    )
    if executed:
        asyncio.run(enqueue_blockchain_confirmation(parsed_id))


@celery_app.task(
    bind=True,
    autoretry_for=(BlockchainTransientError,),
    max_retries=5,
    retry_backoff=True,
    retry_jitter=True,
)  # type: ignore[untyped-decorator]
def confirm_blockchain_transaction(
    task: BoundTask,
    transaction_id: str,
    durable_job_id: str | None = None,
) -> None:
    task_id, retry_no = _task_identity(task)
    asyncio.run(
        _run_durable_confirmation(
            UUID(transaction_id),
            task_id=task_id,
            retry_no=retry_no,
            durable_job_id=UUID(durable_job_id) if durable_job_id else None,
        )
    )


@celery_app.task(
    bind=True,
    autoretry_for=(BlockchainTransientError,),
    max_retries=3,
    retry_backoff=True,
    retry_jitter=True,
)  # type: ignore[untyped-decorator]
def reconcile_blockchain_transactions(
    task: BoundTask,
    durable_job_id: str | None = None,
) -> None:
    task_id, retry_no = _task_identity(task)
    asyncio.run(
        _run_durable_reconciliation(
            task_id=task_id,
            retry_no=retry_no,
            durable_job_id=UUID(durable_job_id) if durable_job_id else None,
        )
    )
