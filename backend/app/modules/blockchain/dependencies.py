from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis

from app.modules.auth.dependencies import SessionDependency, SettingsDependency
from app.modules.blockchain.gateway import SUPPORTED_CHAINS, BlockchainGateway
from app.modules.blockchain.nonce_lock import RedisNonceLock
from app.modules.blockchain.service import BlockchainTransactionService
from app.modules.blockchain.signer import create_transaction_signer
from app.workers.celery_app import celery_app
from app.workers.dispatcher import (
    enqueue_blockchain_broadcast,
    enqueue_blockchain_reconciliation,
)


async def get_blockchain_service(
    session: SessionDependency,
    settings: SettingsDependency,
) -> AsyncIterator[BlockchainTransactionService]:
    address = settings.certificate_contract_address
    secret = settings.blockchain_signer_private_key
    allowed_contracts = set(settings.blockchain_contract_allowlist)
    if settings.blockchain_network == "local" and not allowed_contracts:
        allowed_contracts = {address}
    gateway = BlockchainGateway(
        rpc_url=settings.blockchain_rpc_url,
        network=settings.blockchain_network,
        chain_id=settings.blockchain_chain_id,
        contract_address=address,
        abi_path=settings.blockchain_contract_abi_path,
        allowed_networks=SUPPORTED_CHAINS,
        allowed_contracts={settings.blockchain_network: allowed_contracts},
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
        enqueue_broadcast=enqueue_blockchain_broadcast,
        enqueue_reconcile=enqueue_blockchain_reconciliation,
        enqueue_certificate_issue=lambda dossier_id: celery_app.send_task(
            "app.workers.certificate_tasks.issue_certificate",
            args=[str(dossier_id)],
        ),
        enqueue_certificate_version=lambda version_id: celery_app.send_task(
            "app.workers.certificate_tasks.render_certificate_version",
            args=[str(version_id)],
        ),
    )
    try:
        yield service
    finally:
        await signer.aclose()
        await gateway.close()
        await redis_client.aclose()


BlockchainServiceDependency = Annotated[
    BlockchainTransactionService,
    Depends(get_blockchain_service),
]
