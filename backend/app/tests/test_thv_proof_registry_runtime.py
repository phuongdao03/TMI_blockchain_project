import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from web3 import Web3

from app.core.config import Settings
from app.db.base import Base
from app.db.outbox import OutboxEvent
from app.modules.auth.models import User, UserStatus
from app.modules.auth.security import OutboxPayloadCipher
from app.modules.auth.session_service import AuthPrincipal
from app.modules.blockchain.errors import (
    BlockchainConflictError,
    BlockchainForbiddenError,
    BlockchainUnavailableError,
)
from app.modules.blockchain.gateway import ChainTransaction, TransactionReceipt
from app.modules.blockchain.human_signing import normalize_wallet_address
from app.modules.blockchain.models import (
    BlockchainTransaction,
    BlockchainTransactionStatus,
    BlockchainWalletLink,
)
from app.modules.blockchain.proof_registry_dependencies import (
    get_thv_proof_registry_service,
)
from app.modules.blockchain.proof_registry_gateway import (
    THVProofRecord,
    THVProofRegistryGateway,
)
from app.modules.blockchain.proof_registry_service import (
    THVProofRegistryService,
    derive_thv_asset_id,
)
from app.modules.dossiers.models import Category, Dossier, DossierStatus, DossierVersion
from app.modules.media.models import MediaAsset  # noqa: F401

NOW = datetime(2026, 8, 24, 12, 0, tzinfo=UTC)
CONTRACT = "0x" + "12" * 20
WALLET = normalize_wallet_address("0x" + "34" * 20) or ""
PAYLOAD = b"thv-proof-registry-calldata"
OUTBOX_KEY = b"proof-registry-outbox-key-32byte"


class ProofRegistryGateway:
    contract_address = CONTRACT

    def __init__(self) -> None:
        self.recorded = False
        self.transaction_hash = "0x" + "90" * 32

    async def has_verifier_role(self, wallet_address: str) -> bool:
        return wallet_address == WALLET

    async def get_proof(self, asset_id: bytes, version: int) -> THVProofRecord:
        return THVProofRecord(
            asset_id=asset_id,
            proof_hash=bytes.fromhex("ab" * 32) if self.recorded else bytes(32),
            version=version,
            recorded_at=int(NOW.timestamp()) if self.recorded else 0,
            signer=WALLET if self.recorded else "0x" + "00" * 20,
            exists=self.recorded,
        )

    def encode_record_proof(
        self,
        *,
        asset_id: bytes,
        proof_hash: bytes,
        version: int,
    ) -> bytes:
        assert len(asset_id) == 32
        assert len(proof_hash) == 32
        assert version > 0
        return PAYLOAD

    async def estimate_gas(self, *, signer: str, payload: bytes) -> int:
        assert signer == WALLET
        assert payload == PAYLOAD
        return 88_000

    async def gas_price(self) -> int:
        return 1_000_000_000

    async def balance(self, wallet_address: str) -> int:
        assert wallet_address == WALLET
        return 10**18

    async def transaction(self, tx_hash: str) -> ChainTransaction | None:
        if tx_hash != self.transaction_hash:
            return None
        self.recorded = True
        return ChainTransaction(
            transaction_hash=tx_hash,
            sender=WALLET,
            recipient=CONTRACT,
            data=PAYLOAD,
            chain_id=31_337,
            value=0,
        )

    async def receipt(self, tx_hash: str) -> TransactionReceipt | None:
        if tx_hash != self.transaction_hash:
            return None
        return TransactionReceipt(
            transaction_hash=tx_hash,
            block_number=10,
            block_hash="0x" + "77" * 32,
            contract_address=CONTRACT,
            event_names=("ProofRecorded",),
            succeeded=True,
        )

    async def latest_block_number(self) -> int:
        return 11

    async def block_hash(self, block_number: int) -> str:
        assert block_number == 10
        return "0x" + "77" * 32


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "app_env": "local",
        "blockchain_network": "local",
        "blockchain_chain_id": 31_337,
        "certificate_contract_address": CONTRACT,
    }
    values.update(overrides)
    return Settings.model_validate(values)


def test_thv_proof_registry_is_disabled_without_a_contract_address() -> None:
    settings = _settings()

    assert settings.thv_proof_registry_contract_address == ""
    assert not settings.thv_proof_registry_configured


def test_thv_proof_registry_address_must_be_allowlisted_outside_local() -> None:
    with pytest.raises(ValidationError, match="THV proof registry contract address"):
        Settings.model_validate(
            {
                "app_env": "staging",
                "payment_provider": "payos",
                "payos_client_id": "client",
                "payos_api_key": "api-key",
                "payos_checksum_key": "checksum",
                "payos_return_url": "https://app.example/payments/return",
                "payos_cancel_url": "https://app.example/payments/cancel",
                "blockchain_network": "amoy",
                "blockchain_chain_id": 80_002,
                "certificate_contract_address": CONTRACT,
                "thv_proof_registry_contract_address": "0x" + "56" * 20,
                "blockchain_allowed_contract_addresses": CONTRACT,
            }
        )


def test_thv_proof_registry_dependency_fails_closed_when_disabled() -> None:
    async def exercise() -> None:
        dependency = get_thv_proof_registry_service(
            cast(AsyncSession, object()),
            _settings(),
        )
        with pytest.raises(BlockchainUnavailableError):
            await anext(dependency)

    asyncio.run(exercise())


def test_thv_proof_registry_dependency_fails_closed_for_invalid_runtime_config() -> (
    None
):
    async def exercise() -> None:
        dependency = get_thv_proof_registry_service(
            cast(AsyncSession, object()),
            _settings(
                thv_proof_registry_contract_address=CONTRACT,
                thv_proof_registry_contract_abi_path=Path(
                    "missing-proof-registry.abi.json"
                ),
            ),
        )
        with pytest.raises(BlockchainUnavailableError, match="configuration"):
            await anext(dependency)

    asyncio.run(exercise())


def test_thv_proof_registry_requires_super_admin_with_signing_capability() -> None:
    service = object.__new__(THVProofRegistryService)
    moderator = AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="moderator@tmigroup.vn",
        roles=("MODERATOR",),
        permissions=("blockchain.sign",),
    )
    super_admin_without_grant = AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="superadmin@tmigroup.vn",
        roles=("SUPER_ADMIN",),
        permissions=(),
    )
    authorized_super_admin = AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="authorized-superadmin@tmigroup.vn",
        roles=("SUPER_ADMIN",),
        permissions=("blockchain.sign",),
    )

    with pytest.raises(BlockchainForbiddenError):
        service._require_signer(moderator)
    with pytest.raises(BlockchainForbiddenError):
        service._require_signer(super_admin_without_grant)

    service._require_signer(authorized_super_admin)


def test_thv_asset_id_is_stable_and_does_not_expose_the_dossier_uuid() -> None:
    dossier_id = uuid4()

    assert derive_thv_asset_id(dossier_id) == derive_thv_asset_id(dossier_id)
    assert derive_thv_asset_id(dossier_id) != dossier_id.bytes
    assert derive_thv_asset_id(dossier_id) != derive_thv_asset_id(uuid4())


def test_static_abi_encodes_the_contract_record_proof_signature() -> None:
    gateway = THVProofRegistryGateway(
        rpc_url="http://127.0.0.1:8545",
        network="local",
        chain_id=31_337,
        contract_address=CONTRACT,
        abi_path=(
            Path(__file__).resolve().parents[3]
            / "contracts"
            / "artifacts"
            / "THVProofRegistry.abi.json"
        ),
        allowed_networks={"local": 31_337},
        allowed_contracts={"local": {CONTRACT}},
    )

    payload = gateway.encode_record_proof(
        asset_id=bytes.fromhex("11" * 32),
        proof_hash=bytes.fromhex("22" * 32),
        version=1,
    )

    assert payload[:4] == Web3.keccak(text="recordProof(bytes32,bytes32,uint64)")[:4]
    assert len(payload) == 4 + (32 * 3)


def test_thv_proof_intent_requires_an_approved_dossier_version() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        user = User(
            id=uuid4(),
            email="proof-signer@tmigroup.vn",
            password_hash="unused",
            status=UserStatus.ACTIVE,
        )
        category = Category(id=uuid4(), code="PROOF", name="Proof")
        dossier = Dossier(
            id=uuid4(),
            code="THV-2026-PROOF-001",
            owner_user_id=user.id,
            category_id=category.id,
            title="Hồ sơ đã phê duyệt",
            current_version_no=1,
        )
        dossier._set_status_from_workflow(DossierStatus.APPROVED)
        dossier_version = DossierVersion(
            id=uuid4(),
            dossier_id=dossier.id,
            version_no=1,
            snapshot_json={},
            canonical_hash="ab" * 32,
            submitted_by=user.id,
            submitted_at=NOW,
        )
        wallet_link = BlockchainWalletLink(
            id=uuid4(),
            user_id=user.id,
            wallet_address=WALLET,
            chain_id=31_337,
            verified_at=NOW,
        )
        async with sessions() as session:
            session.add_all([user, category, dossier, dossier_version, wallet_link])
            await session.commit()

        principal = AuthPrincipal(
            user_id=user.id,
            session_id=uuid4(),
            email=user.email,
            roles=("SUPER_ADMIN",),
            permissions=("blockchain.sign",),
        )
        gateway = ProofRegistryGateway()
        service = THVProofRegistryService(
            session=sessions(),
            gateway=cast(THVProofRegistryGateway, gateway),
            network="local",
            chain_id=31_337,
            contract_address=CONTRACT,
            signing_enabled=True,
            payload_cipher=OutboxPayloadCipher(key=OUTBOX_KEY, key_id="proof-key-v1"),
            required_confirmations=2,
            intent_ttl=timedelta(minutes=10),
            clock=lambda: NOW,
        )
        pending = await service.signing_queue(principal)
        assert len(pending) == 1
        assert pending[0].dossier_id == dossier.id
        assert pending[0].transaction_id is None
        assert pending[0].status is BlockchainTransactionStatus.CREATED

        intent = await service.prepare_record_proof_intent(
            principal,
            dossier_id=dossier.id,
            version_no=1,
            connected_wallet=WALLET,
        )
        assert intent.transaction_request == {
            "to": CONTRACT,
            "data": "0x" + PAYLOAD.hex(),
            "chainId": "31337",
            "value": "0",
        }
        assert intent.proof_hash == "0x" + "ab" * 32
        assert intent.version == 1
        assert intent.transaction_id is not None
        assert intent.intent_id is not None

        submitted = await service.submit_transaction(
            principal,
            transaction_id=intent.transaction_id,
            intent_id=intent.intent_id,
            transaction_hash=gateway.transaction_hash,
            connected_wallet=WALLET,
        )
        assert submitted.status is BlockchainTransactionStatus.BROADCAST

        confirmed = await service.transaction_status(
            principal,
            transaction_id=intent.transaction_id,
            reconcile=True,
        )
        assert confirmed.status is BlockchainTransactionStatus.CONFIRMED
        assert confirmed.confirmations == 2
        confirmed_again = await service.transaction_status(
            principal,
            transaction_id=intent.transaction_id,
            reconcile=True,
        )
        assert confirmed_again.status is BlockchainTransactionStatus.CONFIRMED
        assert await service.signing_queue(principal) == []
        async with sessions() as session:
            stored_transaction = await session.get(
                BlockchainTransaction, intent.transaction_id
            )
            assert stored_transaction is not None
            assert stored_transaction.receipt_event_name == "ProofRecorded"
            assert stored_transaction.signer_wallet_address == WALLET
            events = tuple(
                await session.scalars(
                    select(OutboxEvent).where(
                        OutboxEvent.event_type == "blockchain.anchored"
                    )
                )
            )
            assert len(events) == 1
            payload = json.loads(
                OutboxPayloadCipher(key=OUTBOX_KEY, key_id="proof-key-v1").decrypt(
                    nonce=events[0].payload_nonce,
                    ciphertext=events[0].payload_ciphertext,
                    event_type=events[0].event_type,
                    aggregate_id=events[0].aggregate_id,
                )
            )
            assert payload == {
                "dossier_id": str(dossier.id),
                "owner_user_id": str(user.id),
                "transaction_hash": gateway.transaction_hash,
                "transaction_id": str(intent.transaction_id),
            }

        async with sessions() as session:
            stored = await session.get(Dossier, dossier.id)
            assert stored is not None
            stored._set_status_from_workflow(DossierStatus.UNDER_REVIEW)
            await session.commit()

        with pytest.raises(BlockchainConflictError, match="approval"):
            await service.prepare_record_proof_intent(
                principal,
                dossier_id=dossier.id,
                version_no=1,
                connected_wallet=WALLET,
            )
        await engine.dispose()

    asyncio.run(exercise())
