"""FastAPI dependency wiring for THV verifier wallet links."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends

from app.modules.audit.service import AuditService
from app.modules.auth.dependencies import SessionDependency, SettingsDependency
from app.modules.blockchain.errors import BlockchainUnavailableError
from app.modules.blockchain.proof_registry_gateway import THVProofRegistryGateway
from app.modules.blockchain.transport import SUPPORTED_CHAINS, BlockchainGatewayError
from app.modules.blockchain.wallet_link_service import WalletLinkService


async def get_wallet_link_service(
    session: SessionDependency,
    settings: SettingsDependency,
) -> AsyncIterator[WalletLinkService]:
    if not settings.thv_proof_registry_configured:
        raise BlockchainUnavailableError("THV proof registry is not configured.")
    address = settings.thv_proof_registry_contract_address.strip()
    allowed_contracts = set(settings.blockchain_contract_allowlist)
    if settings.blockchain_network == "local" and not allowed_contracts:
        allowed_contracts = {address}
    try:
        gateway = THVProofRegistryGateway(
            rpc_url=settings.blockchain_rpc_url,
            network=settings.blockchain_network,
            chain_id=settings.blockchain_chain_id,
            contract_address=address,
            abi_path=settings.thv_proof_registry_contract_abi_path,
            allowed_networks=SUPPORTED_CHAINS,
            allowed_contracts={settings.blockchain_network: allowed_contracts},
        )
    except BlockchainGatewayError as exc:
        raise BlockchainUnavailableError(
            "THV proof registry configuration is unavailable."
        ) from exc
    service = WalletLinkService(
        session=session,
        gateway=gateway,
        chain_id=settings.blockchain_chain_id,
        challenge_ttl_seconds=settings.blockchain_wallet_challenge_ttl_seconds,
        audit=AuditService(session, settings=settings),
    )
    try:
        yield service
    finally:
        await gateway.close()


WalletLinkServiceDependency = Annotated[
    WalletLinkService,
    Depends(get_wallet_link_service),
]
