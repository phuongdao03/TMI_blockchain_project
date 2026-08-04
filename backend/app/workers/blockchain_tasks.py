import asyncio
from collections.abc import Awaitable, Callable
from uuid import UUID

from redis.asyncio import Redis

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.modules.blockchain.errors import BlockchainTransientError
from app.modules.blockchain.gateway import BlockchainGateway
from app.modules.blockchain.nonce_lock import RedisNonceLock
from app.modules.blockchain.service import BlockchainTransactionService
from app.modules.blockchain.signer import LocalPrivateKeySigner
from app.workers.celery_app import celery_app


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
        allowed_networks={"local": 31_337, "amoy": 80_002},
        allowed_contracts={settings.blockchain_network: {address}},
    )
    redis_client: Redis = Redis.from_url(settings.redis_url)
    try:
        async with get_session_factory()() as session:
            service = BlockchainTransactionService(
                session=session,
                gateway=gateway,
                signer=LocalPrivateKeySigner(
                    secret.get_secret_value() if secret is not None else ""
                ),
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
            )
            await operation(service)
    finally:
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
    autoretry_for=(BlockchainTransientError,),
    max_retries=5,
    retry_backoff=True,
    retry_jitter=True,
)  # type: ignore[untyped-decorator]
def broadcast_blockchain_transaction(transaction_id: str) -> None:
    parsed_id = UUID(transaction_id)
    asyncio.run(_broadcast(parsed_id))
    confirm_blockchain_transaction.apply_async(args=[transaction_id], countdown=15)


@celery_app.task(
    autoretry_for=(BlockchainTransientError,),
    max_retries=5,
    retry_backoff=True,
    retry_jitter=True,
)  # type: ignore[untyped-decorator]
def confirm_blockchain_transaction(transaction_id: str) -> None:
    asyncio.run(_confirm(UUID(transaction_id)))


@celery_app.task(
    autoretry_for=(BlockchainTransientError,),
    max_retries=3,
    retry_backoff=True,
    retry_jitter=True,
)  # type: ignore[untyped-decorator]
def reconcile_blockchain_transactions() -> None:
    asyncio.run(_reconcile())
