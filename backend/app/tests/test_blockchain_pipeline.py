import asyncio
import hashlib
from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.base import Base
from app.modules.audit.models import AuditLog
from app.modules.auth.models import User, UserStatus
from app.modules.auth.session_service import AuthPrincipal
from app.modules.blockchain.errors import (
    BlockchainConflictError,
    BlockchainForbiddenError,
    BlockchainTransientError,
)
from app.modules.blockchain.gateway import BlockchainGateway, TransactionReceipt
from app.modules.blockchain.models import (
    BlockchainTransaction,
    BlockchainTransactionStatus,
)
from app.modules.blockchain.nonce_lock import NonceLock
from app.modules.blockchain.service import BlockchainTransactionService
from app.modules.blockchain.signer import TransactionSigner
from app.modules.dossiers.models import (
    Category,
    Dossier,
    DossierStatus,
    DossierVersion,
)
from app.modules.media.models import MediaAsset  # noqa: F401

NOW = datetime(2026, 7, 31, 9, 0, tzinfo=UTC)
CONTRACT = "0x" + "12" * 20
PAYLOAD = b"contract-call-payload"


class FakeSigner:
    address = "0x" + "34" * 20

    async def sign(self, transaction: dict[str, int | str]) -> bytes:
        assert transaction["nonce"] == 7
        return b"signed"

    async def aclose(self) -> None:
        return None


class FakeNonceLock:
    releases = 0

    async def acquire(self, key: str, *, ttl_seconds: int) -> str | None:
        assert key.startswith("blockchain:nonce:local:")
        assert ttl_seconds == 30
        return "lock-token"

    async def release(self, key: str, token: str) -> None:
        assert token == "lock-token"
        self.releases += 1


class FakeGateway:
    broadcasts = 0
    fail_broadcast = False
    receipt_result: TransactionReceipt | None = None
    latest_block = 10
    canonical_block_hash = "0x" + "78" * 32

    async def pending_nonce(self, signer: str) -> int:
        return 7

    async def estimate_gas(self, *, signer: str, payload: bytes) -> int:
        assert payload == PAYLOAD
        return 100_000

    async def gas_price(self) -> int:
        return 2

    async def broadcast(self, raw_transaction: bytes) -> str:
        self.broadcasts += 1
        if self.fail_broadcast:
            raise RuntimeError("RPC unavailable")
        assert raw_transaction == b"signed"
        return "0x" + "56" * 32

    async def receipt(self, tx_hash: str) -> TransactionReceipt | None:
        return self.receipt_result

    async def latest_block_number(self) -> int:
        return self.latest_block

    async def block_hash(self, block_number: int) -> str:
        assert block_number == 9
        return self.canonical_block_hash


async def _pipeline(
    *,
    status: BlockchainTransactionStatus = BlockchainTransactionStatus.CREATED,
) -> tuple[
    BlockchainTransactionService,
    async_sessionmaker[AsyncSession],
    AsyncEngine,
    FakeGateway,
    UUID,
    UUID,
]:
    engine = create_async_engine("sqlite+aiosqlite://")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    user = User(
        id=uuid4(),
        email=f"{uuid4().hex}@tmigroup.vn",
        password_hash="unused",
        status=UserStatus.ACTIVE,
    )
    category = Category(id=uuid4(), code=uuid4().hex[:12], name="Blockchain")
    dossier = Dossier(
        id=uuid4(),
        code=f"DOS-{uuid4().hex[:12]}",
        owner_user_id=user.id,
        category_id=category.id,
        title="Paid dossier",
    )
    dossier._set_status_from_workflow(DossierStatus.ANCHOR_PENDING)
    version = DossierVersion(
        id=uuid4(),
        dossier_id=dossier.id,
        version_no=1,
        snapshot_json={},
        canonical_hash="ab" * 32,
        submitted_by=user.id,
    )
    transaction = BlockchainTransaction(
        id=uuid4(),
        dossier_id=dossier.id,
        dossier_version_id=version.id,
        network="local",
        chain_id=31_337,
        contract_address=CONTRACT,
        method="issueCertificate",
        payload_hash=hashlib.sha256(PAYLOAD).hexdigest(),
        status=status,
        confirmations=0,
        tx_hash=(
            "0x" + "56" * 32
            if status
            in {
                BlockchainTransactionStatus.BROADCAST,
                BlockchainTransactionStatus.CONFIRMED,
            }
            else None
        ),
        broadcast_at=(
            NOW
            if status
            in {
                BlockchainTransactionStatus.BROADCAST,
                BlockchainTransactionStatus.CONFIRMED,
            }
            else None
        ),
    )
    async with sessions() as session:
        session.add_all([user, category, dossier, version, transaction])
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
    )
    return service, sessions, engine, gateway, transaction.id, dossier.id


def test_broadcast_is_idempotent_for_duplicate_delivery() -> None:
    async def exercise() -> None:
        service, sessions, engine, gateway, transaction_id, _ = await _pipeline()
        await service.broadcast(transaction_id, PAYLOAD)
        await service.broadcast(transaction_id, PAYLOAD)

        async with sessions() as session:
            transaction = await session.get(BlockchainTransaction, transaction_id)
            assert transaction is not None
            assert transaction.status is BlockchainTransactionStatus.BROADCAST
            assert transaction.nonce == 7
            audit_rows = (
                await session.scalars(
                    select(AuditLog).where(
                        AuditLog.action == "blockchain.transaction.broadcasted"
                    )
                )
            ).all()
            assert len(audit_rows) == 1
            assert audit_rows[0].actor_service == "blockchain-broadcast-worker"
            assert audit_rows[0].resource_id == str(transaction_id)
            assert audit_rows[0].after_json == {"status": "BROADCAST"}
        assert gateway.broadcasts == 1
        await engine.dispose()

    asyncio.run(exercise())


def test_anchor_replay_is_blocked_when_snapshot_provenance_is_incomplete() -> None:
    async def exercise() -> None:
        service, sessions, engine, _, transaction_id, dossier_id = await _pipeline()
        async with sessions() as session:
            transaction = await session.get(BlockchainTransaction, transaction_id)
            assert transaction is not None
            dossier = await session.get(Dossier, dossier_id)
            assert dossier is not None
            version_id = transaction.dossier_version_id
            actor_user_id = dossier.owner_user_id

        with pytest.raises(BlockchainConflictError, match="reverified"):
            await service.request_anchor(
                dossier_id=dossier_id,
                dossier_version_id=version_id,
                certificate_id=None,
                method="issueCertificate",
                payload=PAYLOAD,
                actor_user_id=actor_user_id,
            )

        await engine.dispose()

    asyncio.run(exercise())


def test_rpc_failure_is_durable_and_retryable() -> None:
    async def exercise() -> None:
        service, sessions, engine, gateway, transaction_id, _ = await _pipeline()
        gateway.fail_broadcast = True

        with pytest.raises(BlockchainTransientError):
            await service.broadcast(transaction_id, PAYLOAD)

        async with sessions() as session:
            transaction = await session.get(BlockchainTransaction, transaction_id)
            assert transaction is not None
            assert transaction.status is BlockchainTransactionStatus.FAILED
            assert transaction.error_code == "RPC_FAILURE"
            assert transaction.error_message == "Blockchain RPC request failed."
            audit_row = await session.scalar(
                select(AuditLog).where(
                    AuditLog.action == "blockchain.transaction.failed"
                )
            )
            assert audit_row is not None
            assert audit_row.actor_service == "blockchain-broadcast-worker"
            assert audit_row.after_json == {
                "status": "FAILED",
                "error_code": "RPC_FAILURE",
            }
            assert "RPC unavailable" not in str(audit_row.after_json)
        await engine.dispose()

    asyncio.run(exercise())


def test_reverted_receipt_marks_transaction_failed() -> None:
    async def exercise() -> None:
        service, sessions, engine, gateway, transaction_id, _ = await _pipeline(
            status=BlockchainTransactionStatus.BROADCAST
        )
        gateway.receipt_result = TransactionReceipt(
            transaction_hash="0x" + "56" * 32,
            block_number=9,
            block_hash="0x" + "78" * 32,
            contract_address=CONTRACT,
            event_names=("CertificateIssued",),
            succeeded=False,
        )
        await service.confirm(transaction_id)

        async with sessions() as session:
            transaction = await session.get(BlockchainTransaction, transaction_id)
            assert transaction is not None
            assert transaction.status is BlockchainTransactionStatus.FAILED
            assert transaction.error_code == "TRANSACTION_REVERTED"
            audit_row = await session.scalar(
                select(AuditLog).where(
                    AuditLog.action == "blockchain.transaction.failed"
                )
            )
            assert audit_row is not None
            assert audit_row.actor_service == "blockchain-confirmation-worker"
            assert audit_row.after_json == {
                "status": "FAILED",
                "error_code": "TRANSACTION_REVERTED",
            }
        await engine.dispose()

    asyncio.run(exercise())


def test_confirmation_updates_transaction_and_dossier_atomically() -> None:
    async def exercise() -> None:
        (
            service,
            sessions,
            engine,
            gateway,
            transaction_id,
            dossier_id,
        ) = await _pipeline(status=BlockchainTransactionStatus.BROADCAST)
        gateway.receipt_result = TransactionReceipt(
            transaction_hash="0x" + "56" * 32,
            block_number=9,
            block_hash="0x" + "78" * 32,
            contract_address=CONTRACT,
            event_names=("CertificateIssued",),
            succeeded=True,
        )
        gateway.latest_block = 10
        await service.confirm(transaction_id)
        await service.confirm(transaction_id)

        async with sessions() as session:
            transaction = await session.get(BlockchainTransaction, transaction_id)
            dossier = await session.get(Dossier, dossier_id)
            assert transaction is not None
            assert dossier is not None
            assert transaction.confirmations == 2
            assert transaction.status is BlockchainTransactionStatus.CONFIRMED
            assert transaction.receipt_block_number == 9
            assert transaction.receipt_block_hash == "0x" + "78" * 32
            assert transaction.receipt_event_name == "CertificateIssued"
            assert dossier.status is DossierStatus.ANCHORED
            audit_rows = (
                await session.scalars(
                    select(AuditLog).where(
                        AuditLog.action == "blockchain.transaction.confirmed"
                    )
                )
            ).all()
            assert len(audit_rows) == 1
            assert audit_rows[0].actor_service == "blockchain-confirmation-worker"
            assert audit_rows[0].after_json == {
                "status": "CONFIRMED",
                "confirmations": 2,
            }
        await engine.dispose()

    asyncio.run(exercise())


def test_receipt_for_another_contract_is_rejected() -> None:
    async def exercise() -> None:
        service, sessions, engine, gateway, transaction_id, _ = await _pipeline(
            status=BlockchainTransactionStatus.BROADCAST
        )
        gateway.receipt_result = TransactionReceipt(
            transaction_hash="0x" + "56" * 32,
            block_number=9,
            block_hash="0x" + "78" * 32,
            contract_address="0x" + "99" * 20,
            event_names=("CertificateIssued",),
            succeeded=True,
        )

        await service.confirm(transaction_id)

        async with sessions() as session:
            transaction = await session.get(BlockchainTransaction, transaction_id)
            assert transaction is not None
            assert transaction.status is BlockchainTransactionStatus.FAILED
            assert transaction.error_code == "RECEIPT_MISMATCH"
            audit_row = await session.scalar(
                select(AuditLog).where(
                    AuditLog.action == "blockchain.transaction.failed"
                )
            )
            assert audit_row is not None
            assert audit_row.after_json == {
                "status": "FAILED",
                "error_code": "RECEIPT_MISMATCH",
            }
        await engine.dispose()

    asyncio.run(exercise())


def test_reconciliation_detects_canonical_block_drift() -> None:
    async def exercise() -> None:
        service, sessions, engine, gateway, transaction_id, _ = await _pipeline(
            status=BlockchainTransactionStatus.CONFIRMED
        )
        async with sessions() as session:
            transaction = await session.get(BlockchainTransaction, transaction_id)
            assert transaction is not None
            transaction.receipt_block_number = 9
            transaction.receipt_block_hash = "0x" + "77" * 32
            transaction.receipt_event_name = "CertificateIssued"
            await session.commit()
        gateway.receipt_result = TransactionReceipt(
            transaction_hash="0x" + "56" * 32,
            block_number=9,
            block_hash="0x" + "77" * 32,
            contract_address=CONTRACT,
            event_names=("CertificateIssued",),
            succeeded=True,
        )
        gateway.canonical_block_hash = "0x" + "88" * 32

        await service.confirm(transaction_id)
        await service.confirm(transaction_id)

        async with sessions() as session:
            transaction = await session.get(BlockchainTransaction, transaction_id)
            assert transaction is not None
            assert transaction.status is BlockchainTransactionStatus.CONFIRMED
            assert transaction.error_code == "CHAIN_STATE_MISMATCH"
            audit_rows = (
                await session.scalars(
                    select(AuditLog).where(
                        AuditLog.action == "blockchain.reconciliation.mismatch"
                    )
                )
            ).all()
            assert len(audit_rows) == 1
            assert audit_rows[0].after_json == {
                "error_code": "CHAIN_STATE_MISMATCH"
            }
        await engine.dispose()

    asyncio.run(exercise())


def test_admin_listing_enforces_blockchain_role() -> None:
    async def exercise() -> None:
        service, _, engine, _, _, _ = await _pipeline()
        principal = AuthPrincipal(
            user_id=uuid4(),
            session_id=uuid4(),
            email="applicant@tmigroup.vn",
            roles=("APPLICANT",),
        )
        with pytest.raises(BlockchainForbiddenError):
            await service.list_admin(
                principal,
                status=None,
                page=1,
                page_size=20,
            )
        await engine.dispose()

    asyncio.run(exercise())


def test_retry_rolls_back_when_audit_cannot_be_persisted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def exercise() -> None:
        service, sessions, engine, _, transaction_id, _ = await _pipeline(
            status=BlockchainTransactionStatus.FAILED
        )
        principal = AuthPrincipal(
            user_id=uuid4(),
            session_id=uuid4(),
            email="blockchain-admin@tmigroup.vn",
            roles=("BLOCKCHAIN_ADMIN",),
        )

        def reject_audit(**_: object) -> None:
            raise RuntimeError("audit unavailable")

        monkeypatch.setattr(service._audit_service, "record", reject_audit)  # noqa: SLF001
        with pytest.raises(RuntimeError, match="audit unavailable"):
            await service.retry_admin(principal, transaction_id)

        async with sessions() as session:
            transaction = await session.get(BlockchainTransaction, transaction_id)
            assert transaction is not None
            assert transaction.status is BlockchainTransactionStatus.FAILED
        await engine.dispose()

    asyncio.run(exercise())
