import asyncio
from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.modules.auth.models import User, UserStatus
from app.modules.blockchain.gateway import BlockchainGateway, TransactionReceipt
from app.modules.blockchain.models import (
    BlockchainTransaction,
    BlockchainTransactionStatus,
    DocumentBlockchainEvidence,
    DocumentEvidenceStatus,
)
from app.modules.blockchain.nonce_lock import NonceLock
from app.modules.blockchain.service import BlockchainTransactionService
from app.modules.blockchain.signer import TransactionSigner
from app.modules.dossiers.models import (
    Category,
    DocumentClaimantScope,
    DocumentHashAnchor,
    DocumentHashClaim,
    Dossier,
    DossierStatus,
    DossierVersion,
)
from app.modules.media.models import MediaAsset, MediaStatus

NOW = datetime(2026, 8, 12, 9, 30, tzinfo=UTC)
CONTRACT = "0x" + "12" * 20
DOC_PAYLOAD = b"document-evidence-contract-call"


class FakeSigner:
    address = "0x" + "34" * 20

    async def sign(self, transaction: dict[str, int | str]) -> bytes:
        return b"signed"

    async def aclose(self) -> None:
        return None


class FakeNonceLock:
    async def acquire(self, key: str, *, ttl_seconds: int) -> str | None:
        return "lock"

    async def release(self, key: str, token: str) -> None:
        return None


class FakeGateway:
    encoded: tuple[bytes, bytes, bytes, int, int] | None = None
    receipt_result: TransactionReceipt | None = None
    chain_record: object | None = None

    def encode_anchor_document_evidence(
        self,
        *,
        evidence_key: bytes,
        commitment: bytes,
        previous_evidence_key: bytes,
        version: int,
        recorded_at: int,
    ) -> bytes:
        self.encoded = (
            evidence_key,
            commitment,
            previous_evidence_key,
            version,
            recorded_at,
        )
        return DOC_PAYLOAD

    async def receipt(self, tx_hash: str) -> TransactionReceipt | None:
        return self.receipt_result

    async def block_hash(self, block_number: int) -> str:
        return "0x" + "78" * 32

    async def latest_block_number(self) -> int:
        return 10

    async def get_document_evidence(self, evidence_key: bytes) -> object:
        assert len(evidence_key) == 32
        if self.chain_record is not None:
            return self.chain_record
        return type(
            "ChainRecord",
            (),
            {
                "commitment": self.encoded[1] if self.encoded else bytes(32),
                "previous_evidence_key": (
                    self.encoded[2] if self.encoded else bytes(32)
                ),
                "version": self.encoded[3] if self.encoded else 0,
                "recorded_at": self.encoded[4] if self.encoded else 0,
            },
        )()


async def _pipeline() -> tuple[
    BlockchainTransactionService,
    async_sessionmaker[AsyncSession],
    FakeGateway,
    UUID,
]:
    engine = create_async_engine("sqlite+aiosqlite://")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    user = User(
        id=uuid4(),
        email="document-owner@tmigroup.vn",
        password_hash="unused",
        status=UserStatus.ACTIVE,
    )
    category = Category(id=uuid4(), code="DOCUMENT", name="Document")
    dossier = Dossier(
        id=uuid4(),
        code="DOS-DOCUMENT",
        owner_user_id=user.id,
        category_id=category.id,
        title="Approved document dossier",
    )
    dossier._set_status_from_workflow(DossierStatus.PAID)
    version = DossierVersion(
        id=uuid4(),
        dossier_id=dossier.id,
        version_no=1,
        snapshot_json={},
        canonical_hash="11" * 32,
        submitted_by=user.id,
        submitted_at=NOW,
    )
    media = MediaAsset(
        id=uuid4(),
        owner_user_id=user.id,
        cloudinary_public_id="evidence/document-proof",
        cloudinary_version=1,
        resource_type="raw",
        access_mode="authenticated",
        original_filename="private-document.pdf",
        mime_type="application/pdf",
        bytes=1024,
        sha256="ab" * 32,
        status=MediaStatus.ACTIVE,
    )
    anchor = DocumentHashAnchor(id=uuid4(), sha256="ab" * 32, created_at=NOW)
    claim = DocumentHashClaim(
        id=uuid4(),
        anchor_id=anchor.id,
        media_asset_id=media.id,
        dossier_id=dossier.id,
        dossier_version_id=version.id,
        claimant_scope_type=DocumentClaimantScope.USER,
        claimant_scope_id=user.id,
        claimed_at=NOW,
    )
    async with sessions() as session:
        session.add_all([user, category, dossier, version, media, anchor, claim])
        await session.commit()
    gateway = FakeGateway()
    service = BlockchainTransactionService(
        session=sessions(),
        gateway=cast(BlockchainGateway, gateway),
        signer=cast(TransactionSigner, FakeSigner()),
        nonce_lock=cast(NonceLock, FakeNonceLock()),
        network="local",
        chain_id=31_337,
        contract_address=CONTRACT,
        required_confirmations=2,
        nonce_lock_ttl_seconds=30,
        clock=lambda: NOW,
        submitter_reference_factory=lambda: "cd" * 32,
    )
    return service, sessions, gateway, claim.id


def test_document_evidence_request_is_idempotent_and_contains_no_pii() -> None:
    async def exercise() -> None:
        service, sessions, gateway, claim_id = await _pipeline()

        created = await service.request_document_evidence(
            document_hash_claim_id=claim_id,
            actor_user_id=uuid4(),
        )
        replay = await service.request_document_evidence(
            document_hash_claim_id=claim_id,
            actor_user_id=uuid4(),
        )

        assert created.transaction_id == replay.transaction_id
        assert created.status is DocumentEvidenceStatus.QUEUED
        assert gateway.encoded is not None
        assert gateway.encoded[2] == bytes(32)
        assert gateway.encoded[3:] == (1, int(NOW.timestamp()))
        async with sessions() as session:
            evidence = await session.get(DocumentBlockchainEvidence, created.id)
            transaction = await session.get(
                BlockchainTransaction,
                created.transaction_id,
            )
            assert evidence is not None
            assert transaction is not None
            assert transaction.document_evidence_id == evidence.id
            assert transaction.method == "anchorDocumentEvidence"
            assert transaction.status is BlockchainTransactionStatus.CREATED

    asyncio.run(exercise())


def test_document_evidence_confirmation_updates_lifecycle() -> None:
    async def exercise() -> None:
        service, sessions, gateway, claim_id = await _pipeline()
        evidence = await service.request_document_evidence(
            document_hash_claim_id=claim_id,
            actor_user_id=uuid4(),
        )
        async with sessions() as session:
            transaction = await session.get(
                BlockchainTransaction,
                evidence.transaction_id,
            )
            assert transaction is not None
            transaction.status = BlockchainTransactionStatus.BROADCAST
            transaction.tx_hash = "0x" + "56" * 32
            await session.commit()
        gateway.receipt_result = TransactionReceipt(
            transaction_hash="0x" + "56" * 32,
            block_number=9,
            block_hash="0x" + "78" * 32,
            contract_address=CONTRACT,
            event_names=("DocumentEvidenceAnchored",),
            succeeded=True,
        )

        await service.confirm(evidence.transaction_id)

        async with sessions() as session:
            row = await session.get(DocumentBlockchainEvidence, evidence.id)
            assert row is not None
            assert row.status is DocumentEvidenceStatus.CONFIRMED

    asyncio.run(exercise())


def test_confirmed_document_evidence_reconciliation_detects_state_mismatch() -> None:
    async def exercise() -> None:
        service, sessions, gateway, claim_id = await _pipeline()
        evidence = await service.request_document_evidence(
            document_hash_claim_id=claim_id,
            actor_user_id=uuid4(),
        )
        async with sessions() as session:
            transaction = await session.get(
                BlockchainTransaction,
                evidence.transaction_id,
            )
            assert transaction is not None
            transaction.status = BlockchainTransactionStatus.CONFIRMED
            transaction.tx_hash = "0x" + "56" * 32
            transaction.receipt_block_number = 9
            transaction.receipt_block_hash = "0x" + "78" * 32
            transaction.receipt_event_name = "DocumentEvidenceAnchored"
            row = await session.get(DocumentBlockchainEvidence, evidence.id)
            assert row is not None
            row.status = DocumentEvidenceStatus.CONFIRMED
            await session.commit()
        gateway.receipt_result = TransactionReceipt(
            transaction_hash="0x" + "56" * 32,
            block_number=9,
            block_hash="0x" + "78" * 32,
            contract_address=CONTRACT,
            event_names=("DocumentEvidenceAnchored",),
            succeeded=True,
        )
        gateway.chain_record = type(
            "ChainRecord",
            (),
            {
                "commitment": bytes.fromhex("ff" * 32),
                "previous_evidence_key": bytes(32),
                "version": 1,
                "recorded_at": int(NOW.timestamp()),
            },
        )()

        await service.confirm(evidence.transaction_id)

        async with sessions() as session:
            transaction = await session.get(
                BlockchainTransaction,
                evidence.transaction_id,
            )
            row = await session.get(DocumentBlockchainEvidence, evidence.id)
            assert transaction is not None
            assert row is not None
            assert transaction.error_code == "CHAIN_STATE_MISMATCH"
            assert row.status is DocumentEvidenceStatus.FAILED

    asyncio.run(exercise())
