from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends

from app.modules.auth.dependencies import SessionDependency, SettingsDependency
from app.modules.blockchain.gateway import SUPPORTED_CHAINS, BlockchainGateway
from app.modules.blockchain.human_signing_service import HumanSigningService
from app.workers.dispatcher import enqueue_blockchain_reconciliation


async def get_human_signing_service(
    session: SessionDependency,
    settings: SettingsDependency,
) -> AsyncIterator[HumanSigningService]:
    address = settings.certificate_contract_address
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
    service = HumanSigningService(
        session=session,
        gateway=gateway,
        network=settings.blockchain_network,
        chain_id=settings.blockchain_chain_id,
        contract_address=address,
        challenge_ttl_seconds=settings.blockchain_wallet_challenge_ttl_seconds,
        intent_ttl_seconds=settings.blockchain_transaction_intent_ttl_seconds,
        signing_enabled=settings.blockchain_signing_enabled,
        enqueue_reconcile=enqueue_blockchain_reconciliation,
    )
    try:
        yield service
    finally:
        await gateway.close()


HumanSigningServiceDependency = Annotated[
    HumanSigningService,
    Depends(get_human_signing_service),
]
