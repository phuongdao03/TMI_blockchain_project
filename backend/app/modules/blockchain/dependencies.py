from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis

from app.modules.auth.dependencies import SessionDependency, SettingsDependency
from app.modules.blockchain.gateway import BlockchainGateway
from app.modules.blockchain.nonce_lock import RedisNonceLock
from app.modules.blockchain.service import BlockchainTransactionService
from app.modules.blockchain.signer import LocalPrivateKeySigner
from app.workers.blockchain_tasks import (
    broadcast_blockchain_transaction,
    reconcile_blockchain_transactions,
)
from app.workers.celery_app import celery_app


async def get_blockchain_service(
    session: SessionDependency,
    settings: SettingsDependency,
) -> AsyncIterator[BlockchainTransactionService]:
    address = settings.certificate_contract_address
    secret = settings.blockchain_signer_private_key
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
        enqueue_broadcast=lambda transaction_id: (
            broadcast_blockchain_transaction.delay(str(transaction_id))
        ),
        enqueue_reconcile=lambda: reconcile_blockchain_transactions.delay(),
        enqueue_certificate_issue=lambda dossier_id: celery_app.send_task(
            "app.workers.certificate_tasks.issue_certificate",
            args=[str(dossier_id)],
        ),
    )
    try:
        yield service
    finally:
        await gateway.close()
        await redis_client.aclose()


BlockchainServiceDependency = Annotated[
    BlockchainTransactionService,
    Depends(get_blockchain_service),
]
