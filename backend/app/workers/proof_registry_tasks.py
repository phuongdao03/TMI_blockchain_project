"""Read-only reconciliation workers for THVProofRegistry transactions."""

import asyncio
from datetime import timedelta
from uuid import UUID

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.modules.auth.security import OutboxPayloadCipher
from app.modules.blockchain.errors import BlockchainUnavailableError
from app.modules.blockchain.proof_registry_gateway import THVProofRegistryGateway
from app.modules.blockchain.proof_registry_service import THVProofRegistryService
from app.modules.blockchain.transport import SUPPORTED_CHAINS, BlockchainGatewayError
from app.workers.celery_app import celery_app


async def _with_service(transaction_id: UUID | None = None) -> None:
    settings = get_settings()
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
    secret = settings.auth_outbox_encryption_key
    try:
        async with get_session_factory()() as session:
            service = THVProofRegistryService(
                session=session,
                gateway=gateway,
                network=settings.blockchain_network,
                chain_id=settings.blockchain_chain_id,
                contract_address=address,
                signing_enabled=settings.blockchain_signing_enabled,
                payload_cipher=OutboxPayloadCipher.from_base64(
                    encoded_key=(
                        secret.get_secret_value() if secret is not None else ""
                    ),
                    key_id=settings.auth_outbox_key_id,
                ),
                required_confirmations=settings.blockchain_required_confirmations,
                intent_ttl=timedelta(
                    seconds=settings.blockchain_transaction_intent_ttl_seconds
                ),
            )
            if transaction_id is None:
                await service.reconcile_pending()
            else:
                await service.reconcile_transaction(transaction_id)
    finally:
        await gateway.close()


@celery_app.task(
    autoretry_for=(BlockchainUnavailableError,),
    max_retries=5,
    retry_backoff=True,
    retry_jitter=True,
)  # type: ignore[untyped-decorator]
def confirm_proof_registry_transaction(transaction_id: str) -> None:
    asyncio.run(_with_service(UUID(transaction_id)))


@celery_app.task(
    autoretry_for=(BlockchainUnavailableError,),
    max_retries=3,
    retry_backoff=True,
    retry_jitter=True,
)  # type: ignore[untyped-decorator]
def reconcile_proof_registry_transactions() -> None:
    asyncio.run(_with_service())
