import asyncio
import hashlib
from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

import pytest
from eth_account import Account
from eth_account.messages import encode_defunct
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.modules.auth.models import User, UserStatus
from app.modules.auth.session_service import AuthPrincipal
from app.modules.blockchain.errors import (
    BlockchainConflictError,
    BlockchainForbiddenError,
)
from app.modules.blockchain.gateway import (
    BlockchainGateway,
    CertificateRecord,
    ChainTransaction,
    TransactionReceipt,
)
from app.modules.blockchain.human_signing import (
    build_wallet_challenge_message,
    normalize_wallet_address,
    recover_wallet_address,
)
from app.modules.blockchain.human_signing_service import HumanSigningService
from app.modules.blockchain.models import (
    BlockchainTransaction,
    BlockchainTransactionStatus,
    Certificate,
    CertificateVersion,
)
from app.modules.blockchain.nonce_lock import NonceLock
from app.modules.blockchain.service import BlockchainTransactionService
from app.modules.dossiers.models import Category, Dossier, DossierStatus, DossierVersion
from app.modules.media.models import MediaAsset  # noqa: F401

NOW = datetime(2026, 8, 23, 12, 0, tzinfo=UTC)
CONTRACT = "0x" + "12" * 20
PAYLOAD = b"human-signed-certificate-call"


class HumanGateway:
    wallet_address = ""
    transaction_data = PAYLOAD

    async def has_issuer_role(self, wallet_address: str) -> bool:
        return wallet_address == self.wallet_address

    def encode_issue_certificate(self, **_: object) -> bytes:
        return PAYLOAD

    async def estimate_gas(self, *, signer: str, payload: bytes) -> int:
        assert signer == self.wallet_address
        assert payload == PAYLOAD
        return 91_000

    async def gas_price(self) -> int:
        return 1_000_000_000

    async def balance(self, wallet_address: str) -> int:
        assert wallet_address == self.wallet_address
        return 10**18

    async def transaction(self, transaction_hash: str) -> ChainTransaction:
        return ChainTransaction(
            transaction_hash=transaction_hash,
            sender=self.wallet_address,
            recipient=CONTRACT,
            data=self.transaction_data,
            chain_id=31_337,
            value=0,
        )

    async def receipt(self, transaction_hash: str) -> TransactionReceipt:
        return TransactionReceipt(
            transaction_hash=transaction_hash,
            block_number=7,
            block_hash="0x" + "56" * 32,
            contract_address=CONTRACT,
            event_names=("CertificateIssued",),
            succeeded=True,
        )

    async def block_hash(self, block_number: int) -> str:
        assert block_number == 7
        return "0x" + "56" * 32

    async def latest_block_number(self) -> int:
        return 7

    async def get_certificate(self, certificate_id: bytes) -> CertificateRecord:
        assert len(certificate_id) == 32
        return CertificateRecord(
            dossier_hash=bytes.fromhex("ab" * 32),
            metadata_hash=bytes.fromhex("ef" * 32),
            revocation_reason_hash=bytes(32),
            issued_at=int(NOW.timestamp()),
            expires_at=0,
            version=1,
            revoked=False,
        )


def test_wallet_challenge_recovers_the_connected_wallet() -> None:
    account = Account.create()
    message = build_wallet_challenge_message(
        user_id=UUID("00000000-0000-0000-0000-000000000123"),
        wallet_address=account.address,
        chain_id=31_337,
        nonce="nonce-for-test-only",
        expires_at=datetime(2026, 8, 23, 12, 10, tzinfo=UTC),
    )
    signature = Account.sign_message(
        encode_defunct(text=message),
        account.key,
    ).signature.hex()

    assert "THV Wallet Verification" in message
    assert recover_wallet_address(message, signature) == normalize_wallet_address(
        account.address
    )


def test_wallet_address_normalization_rejects_invalid_addresses() -> None:
    assert normalize_wallet_address("not-an-address") is None


def test_only_super_admin_with_the_signing_capability_can_sign() -> None:
    service = object.__new__(HumanSigningService)
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


def test_human_signer_links_wallet_and_submits_only_matching_intent() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        user = User(
            id=uuid4(),
            email="blockchain-signer@tmigroup.vn",
            password_hash="unused",
            status=UserStatus.ACTIVE,
        )
        category = Category(id=uuid4(), code="BLOCKCHAIN", name="Blockchain")
        dossier = Dossier(
            id=uuid4(),
            code="THV-2026-HUMAN-001",
            owner_user_id=user.id,
            category_id=category.id,
            title="Hồ sơ chờ ký thủ công",
        )
        dossier._set_status_from_workflow(DossierStatus.ANCHOR_PENDING)
        dossier_version = DossierVersion(
            id=uuid4(),
            dossier_id=dossier.id,
            version_no=1,
            snapshot_json={},
            canonical_hash="ab" * 32,
            submitted_by=user.id,
            submitted_at=NOW,
        )
        certificate = Certificate(
            id=uuid4(),
            certificate_number="THV-CERT-HUMAN-001",
            dossier_id=dossier.id,
            current_version_no=1,
            issued_at=NOW,
            expires_at=None,
            public_token_hash="cd" * 32,
            qr_payload="https://thv.example/verify/token",
        )
        certificate_version = CertificateVersion(
            id=uuid4(),
            certificate_id=certificate.id,
            version_no=1,
            predecessor_version_id=None,
            dossier_version_id=dossier_version.id,
            metadata_json={},
            metadata_hash="ef" * 32,
        )
        transaction = BlockchainTransaction(
            id=uuid4(),
            dossier_id=dossier.id,
            dossier_version_id=dossier_version.id,
            certificate_id=certificate.id,
            network="local",
            chain_id=31_337,
            contract_address=CONTRACT,
            method="issueCertificate",
            payload_hash=hashlib.sha256(PAYLOAD).hexdigest(),
            status=BlockchainTransactionStatus.CREATED,
            confirmations=0,
        )
        async with sessions() as session:
            session.add_all(
                [
                    user,
                    category,
                    dossier,
                    dossier_version,
                    certificate,
                    certificate_version,
                    transaction,
                ]
            )
            await session.commit()

        account = Account.create()
        gateway = HumanGateway()
        gateway.wallet_address = normalize_wallet_address(account.address) or ""
        principal = AuthPrincipal(
            user_id=user.id,
            session_id=uuid4(),
            email=user.email,
            roles=("SUPER_ADMIN",),
            permissions=("blockchain.sign",),
        )
        service = HumanSigningService(
            session=sessions(),
            gateway=cast(BlockchainGateway, gateway),
            network="local",
            chain_id=31_337,
            contract_address=CONTRACT,
            challenge_ttl_seconds=300,
            intent_ttl_seconds=600,
            signing_enabled=True,
            clock=lambda: NOW,
            nonce_factory=lambda: "human-signer-nonce",
        )
        challenge = await service.create_wallet_challenge(
            principal,
            wallet_address=gateway.wallet_address,
            chain_id=31_337,
        )
        signature = Account.sign_message(
            encode_defunct(text=challenge.message),
            account.key,
        ).signature.hex()
        link = await service.verify_wallet_link(
            principal,
            challenge_id=challenge.id,
            nonce=challenge.nonce,
            signature=signature,
        )
        assert link.wallet_address == gateway.wallet_address

        intent = await service.prepare_intent(
            principal,
            transaction_id=transaction.id,
            connected_wallet=gateway.wallet_address,
        )
        assert intent.transaction_request["to"].lower() == CONTRACT.lower()
        assert intent.transaction_request["data"] == "0x" + PAYLOAD.hex()

        gateway.transaction_data = b"tampered-calldata"
        with pytest.raises(BlockchainConflictError):
            await service.submit_transaction(
                principal,
                transaction_id=transaction.id,
                intent_id=intent.id,
                transaction_hash="0x" + "34" * 32,
                connected_wallet=gateway.wallet_address,
            )
        gateway.transaction_data = PAYLOAD

        submitted = await service.submit_transaction(
            principal,
            transaction_id=transaction.id,
            intent_id=intent.id,
            transaction_hash="0x" + "34" * 32,
            connected_wallet=gateway.wallet_address,
        )
        assert submitted.status is BlockchainTransactionStatus.BROADCAST
        reconciler = BlockchainTransactionService(
            session=sessions(),
            gateway=cast(BlockchainGateway, gateway),
            signer=None,
            nonce_lock=cast(NonceLock, None),
            network="local",
            chain_id=31_337,
            contract_address=CONTRACT,
            required_confirmations=1,
            nonce_lock_ttl_seconds=30,
            clock=lambda: NOW,
        )
        await reconciler.confirm(transaction.id)
        async with sessions() as session:
            stored = await session.get(BlockchainTransaction, transaction.id)
            assert stored is not None
            assert stored.error_message is None
            assert stored.status is BlockchainTransactionStatus.CONFIRMED
            assert stored.signer_user_id == user.id
            assert stored.signer_wallet_address == gateway.wallet_address
            assert stored.tx_hash == "0x" + "34" * 32
        revoked = await service.revoke_current_wallet(principal)
        assert revoked.status.value == "REVOKED"
        await engine.dispose()

    asyncio.run(exercise())
