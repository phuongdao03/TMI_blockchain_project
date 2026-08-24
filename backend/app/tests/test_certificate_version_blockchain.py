import asyncio
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
from app.modules.blockchain.errors import BlockchainConflictError
from app.modules.blockchain.gateway import (
    BlockchainGateway,
    CertificateRecord,
    TransactionReceipt,
)
from app.modules.blockchain.models import (
    BlockchainTransaction,
    BlockchainTransactionStatus,
    Certificate,
    CertificateStatus,
    CertificateVersion,
    CertificateVersionStatus,
)
from app.modules.blockchain.nonce_lock import NonceLock
from app.modules.blockchain.service import BlockchainTransactionService
from app.modules.blockchain.signer import TransactionSigner
from app.modules.dossiers.canonical import snapshot_sha256
from app.modules.dossiers.models import (
    Category,
    Dossier,
    DossierEvidence,
    DossierStatus,
    DossierVersion,
)
from app.modules.media.models import MediaAsset, MediaStatus
from app.modules.media.provenance import CURRENT_INSPECTION_POLICY_VERSION

NOW = datetime(2026, 8, 11, 10, 0, tzinfo=UTC)
CONTRACT = "0x" + "12" * 20
TX_HASH = "0x" + "56" * 32


class VersionGateway:
    event_name = "CertificateUpdated"
    certificate_record: CertificateRecord | None = None

    def encode_update_certificate(
        self,
        *,
        certificate_id: bytes,
        dossier_hash: bytes,
        metadata_hash: bytes,
        version: int,
    ) -> bytes:
        assert len(certificate_id) == 32
        assert len(dossier_hash) == 32
        assert len(metadata_hash) == 32
        assert version == 2
        return b"update-certificate-v2"

    def encode_revoke_certificate(
        self,
        *,
        certificate_id: bytes,
        reason_hash: bytes,
    ) -> bytes:
        assert len(certificate_id) == 32
        assert len(reason_hash) == 32
        return b"revoke-certificate"

    async def receipt(self, tx_hash: str) -> TransactionReceipt | None:
        assert tx_hash == TX_HASH
        return TransactionReceipt(
            transaction_hash=TX_HASH,
            block_number=9,
            block_hash="0x" + "78" * 32,
            contract_address=CONTRACT,
            event_names=(self.event_name,),
            succeeded=True,
        )

    async def latest_block_number(self) -> int:
        return 10

    async def block_hash(self, block_number: int) -> str:
        assert block_number == 9
        return "0x" + "78" * 32

    async def get_certificate(self, certificate_id: bytes) -> CertificateRecord:
        assert len(certificate_id) == 32
        assert self.certificate_record is not None
        return self.certificate_record


async def _service(
    *,
    human_signer: bool = False,
) -> tuple[
    BlockchainTransactionService,
    async_sessionmaker[AsyncSession],
    AsyncEngine,
    UUID,
    UUID,
    UUID,
    list[UUID],
    VersionGateway,
]:
    engine = create_async_engine("sqlite+aiosqlite://")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    owner_id = uuid4()
    admin_id = uuid4()
    dossier_id = uuid4()
    certificate_id = uuid4()
    active_version_id = uuid4()
    requested_version_id = uuid4()
    media_id = uuid4()
    snapshot = {
        "schemaVersion": 1,
        "evidences": [
            {
                "mediaAssetId": str(media_id),
                "media": {
                    "bytes": 128,
                    "sha256": "a" * 64,
                    "hashAlgorithm": "SHA-256",
                    "hashByteLength": 128,
                    "inspectionPolicyVersion": CURRENT_INSPECTION_POLICY_VERSION,
                    "storageObjectVersion": 4,
                    "hashComputedAt": "2026-08-11T10:00:00Z",
                },
            }
        ],
    }
    category = Category(id=uuid4(), code="CHAIN", name="Blockchain")
    dossier = Dossier(
        id=dossier_id,
        code="DOS-CHAIN-UPDATE",
        owner_user_id=owner_id,
        category_id=category.id,
        title="Blockchain update",
        current_version_no=2,
    )
    dossier._set_status_from_workflow(DossierStatus.CERTIFICATE_ISSUED)
    dossier_v1 = DossierVersion(
        id=uuid4(),
        dossier_id=dossier_id,
        version_no=1,
        snapshot_json={},
        canonical_hash="1" * 64,
        submitted_by=owner_id,
    )
    dossier_v2 = DossierVersion(
        id=uuid4(),
        dossier_id=dossier_id,
        version_no=2,
        snapshot_json=snapshot,
        canonical_hash=snapshot_sha256(snapshot),
        submitted_by=owner_id,
    )
    certificate = Certificate(
        id=certificate_id,
        certificate_number="TMI-2026-CHAIN-UPDATE",
        dossier_id=dossier_id,
        current_version_no=1,
        status=CertificateStatus.ACTIVE,
        issued_at=NOW,
        public_token_hash="b" * 64,
        qr_payload="https://tmi.example/verify/token",
    )
    active = CertificateVersion(
        id=active_version_id,
        certificate_id=certificate_id,
        version_no=1,
        dossier_version_id=dossier_v1.id,
        metadata_json={"certificateVersion": 1},
        metadata_hash="c" * 64,
        status=CertificateVersionStatus.ACTIVE,
    )
    requested = CertificateVersion(
        id=requested_version_id,
        certificate_id=certificate_id,
        version_no=2,
        predecessor_version_id=active_version_id,
        dossier_version_id=dossier_v2.id,
        metadata_json={"certificateVersion": 2},
        metadata_hash="d" * 64,
        public_token_hash="e" * 64,
        qr_payload="https://tmi.example/verify/version-2-token",
        status=CertificateVersionStatus.PENDING_APPROVAL,
        change_reason="Correct the approved certificate ownership information.",
        requested_by=owner_id,
        requested_at=NOW,
    )
    media = MediaAsset(
        id=media_id,
        owner_user_id=owner_id,
        cloudinary_public_id="evidence/version-update",
        cloudinary_version=4,
        resource_type="raw",
        access_mode="authenticated",
        original_filename="version-update.pdf",
        mime_type="application/pdf",
        bytes=128,
        sha256="a" * 64,
        hash_algorithm="SHA-256",
        hash_byte_length=128,
        inspection_policy_version=CURRENT_INSPECTION_POLICY_VERSION,
        hash_storage_version=4,
        hash_computed_at=NOW,
        status=MediaStatus.ACTIVE,
    )
    evidence = DossierEvidence(
        id=uuid4(),
        dossier_id=dossier_id,
        dossier_version_id=dossier_v2.id,
        media_asset_id=media_id,
        evidence_type="OWNERSHIP_DOCUMENT",
        title="Updated evidence",
    )
    users = [
        User(id=value, email=f"{value}@example.test", status=UserStatus.ACTIVE)
        for value in (owner_id, admin_id)
    ]
    async with sessions() as session:
        session.add_all(
            [
                *users,
                category,
                dossier,
                dossier_v1,
                dossier_v2,
                certificate,
                active,
                requested,
                media,
                evidence,
            ]
        )
        await session.commit()
    enqueued: list[UUID] = []
    gateway = VersionGateway()
    service = BlockchainTransactionService(
        session=sessions(),
        gateway=cast(BlockchainGateway, gateway),
        signer=None if human_signer else cast(TransactionSigner, object()),
        nonce_lock=cast(NonceLock, object()),
        network="local",
        chain_id=31_337,
        contract_address=CONTRACT,
        required_confirmations=2,
        nonce_lock_ttl_seconds=30,
        enqueue_broadcast=enqueued.append,
        clock=lambda: NOW,
    )
    return (
        service,
        sessions,
        engine,
        requested_version_id,
        active_version_id,
        admin_id,
        enqueued,
        gateway,
    )


def test_update_anchor_is_idempotent_and_promotes_only_after_confirmation() -> None:
    async def scenario() -> None:
        (
            service,
            sessions,
            engine,
            requested_version_id,
            active_version_id,
            admin_id,
            enqueued,
            _,
        ) = await _service()
        first = await service.request_certificate_update_anchor(
            certificate_version_id=requested_version_id,
            actor_user_id=admin_id,
        )
        replay = await service.request_certificate_update_anchor(
            certificate_version_id=requested_version_id,
            actor_user_id=admin_id,
        )
        assert replay.id == first.id
        assert enqueued == [first.id]

        async with sessions() as check:
            requested = await check.get(CertificateVersion, requested_version_id)
            active = await check.get(CertificateVersion, active_version_id)
            assert requested is not None and active is not None
            assert requested.status is CertificateVersionStatus.ANCHOR_PENDING
            assert active.status is CertificateVersionStatus.ACTIVE
            transaction = await check.get(BlockchainTransaction, first.id)
            assert transaction is not None
            request_audits = (
                await check.scalars(
                    select(AuditLog).where(
                        AuditLog.action == "blockchain.certificate_update.requested"
                    )
                )
            ).all()
            assert len(request_audits) == 1
            assert request_audits[0].actor_user_id == admin_id
            assert request_audits[0].after_json == {"status": "CREATED"}
            transaction.status = BlockchainTransactionStatus.BROADCAST
            transaction.tx_hash = TX_HASH
            await check.commit()

        await service.confirm(first.id)

        async with sessions() as check:
            requested = await check.get(CertificateVersion, requested_version_id)
            active = await check.get(CertificateVersion, active_version_id)
            assert requested is not None
            certificate = await check.get(Certificate, requested.certificate_id)
            assert certificate is not None
            dossier = await check.get(Dossier, certificate.dossier_id)
        assert requested.status is CertificateVersionStatus.ACTIVE
        assert active is not None
        assert active.status is CertificateVersionStatus.SUPERSEDED
        assert certificate is not None and certificate.current_version_no == 2
        assert certificate.public_token_hash == "e" * 64
        assert certificate.qr_payload == "https://tmi.example/verify/version-2-token"
        assert dossier is not None
        assert dossier.status is DossierStatus.CERTIFICATE_ISSUED
        await service._session.close()  # noqa: SLF001
        await engine.dispose()

    asyncio.run(scenario())


def test_update_anchor_requires_a_version_bound_qr_link() -> None:
    async def scenario() -> None:
        (
            service,
            sessions,
            engine,
            requested_version_id,
            _,
            admin_id,
            enqueued,
            _,
        ) = await _service()
        async with sessions() as session:
            requested = await session.get(CertificateVersion, requested_version_id)
            assert requested is not None
            requested.public_token_hash = None
            requested.qr_payload = None
            await session.commit()

        with pytest.raises(BlockchainConflictError, match="version-bound QR"):
            await service.request_certificate_update_anchor(
                certificate_version_id=requested_version_id,
                actor_user_id=admin_id,
            )

        assert enqueued == []
        await service._session.close()  # noqa: SLF001
        await engine.dispose()

    asyncio.run(scenario())


def test_human_reconciliation_keeps_historical_transaction_confirmed() -> None:
    async def scenario() -> None:
        (
            service,
            sessions,
            engine,
            requested_version_id,
            active_version_id,
            _,
            _,
            gateway,
        ) = await _service(human_signer=True)
        gateway.event_name = "CertificateIssued"

        async with sessions() as session:
            certificate = await session.scalar(select(Certificate))
            active = await session.get(CertificateVersion, active_version_id)
            requested = await session.get(CertificateVersion, requested_version_id)
            dossier_v1 = await session.scalar(
                select(DossierVersion).where(DossierVersion.version_no == 1)
            )
            dossier_v2 = await session.scalar(
                select(DossierVersion).where(DossierVersion.version_no == 2)
            )
            assert (
                certificate is not None
                and active is not None
                and requested is not None
                and dossier_v1 is not None
                and dossier_v2 is not None
            )
            certificate.current_version_no = 2
            active.status = CertificateVersionStatus.SUPERSEDED
            await session.flush()
            requested.status = CertificateVersionStatus.ACTIVE
            transaction = BlockchainTransaction(
                dossier_id=certificate.dossier_id,
                dossier_version_id=dossier_v1.id,
                certificate_id=certificate.id,
                network="local",
                chain_id=31_337,
                contract_address=CONTRACT,
                method="issueCertificate",
                payload_hash="e" * 64,
                tx_hash=TX_HASH,
                status=BlockchainTransactionStatus.CONFIRMED,
                confirmations=2,
                broadcast_at=NOW,
                confirmed_at=NOW,
            )
            session.add(transaction)
            gateway.certificate_record = CertificateRecord(
                dossier_hash=bytes.fromhex(dossier_v2.canonical_hash),
                metadata_hash=bytes.fromhex(requested.metadata_hash),
                revocation_reason_hash=bytes(32),
                issued_at=int(NOW.timestamp()),
                expires_at=0,
                version=2,
                revoked=False,
            )
            await session.commit()
            transaction_id = transaction.id

        await service.confirm(transaction_id)

        async with sessions() as session:
            confirmed_transaction = await session.get(
                BlockchainTransaction,
                transaction_id,
            )
            assert confirmed_transaction is not None
            assert confirmed_transaction.status is BlockchainTransactionStatus.CONFIRMED
            assert confirmed_transaction.error_code is None
            assert confirmed_transaction.error_message is None
        await service._session.close()  # noqa: SLF001
        await engine.dispose()

    asyncio.run(scenario())


def test_revocation_becomes_effective_only_after_confirmation() -> None:
    async def scenario() -> None:
        (
            service,
            sessions,
            engine,
            requested_version_id,
            active_version_id,
            admin_id,
            enqueued,
            gateway,
        ) = await _service()
        async with sessions() as setup:
            requested = await setup.get(CertificateVersion, requested_version_id)
            active = await setup.get(CertificateVersion, active_version_id)
            assert requested is not None and active is not None
            requested.status = CertificateVersionStatus.REJECTED
            certificate_id = active.certificate_id
            await setup.commit()

        transaction = await service.request_certificate_revocation(
            certificate_id=certificate_id,
            reason="Withdraw the certificate after a confirmed legal cancellation.",
            actor_user_id=admin_id,
        )
        replay = await service.request_certificate_revocation(
            certificate_id=certificate_id,
            reason="Withdraw the certificate after a confirmed legal cancellation.",
            actor_user_id=admin_id,
        )
        assert replay.id == transaction.id
        assert enqueued == [transaction.id]

        async with sessions() as check:
            certificate = await check.get(Certificate, certificate_id)
            active = await check.get(CertificateVersion, active_version_id)
            assert certificate is not None and active is not None
            assert certificate.status is CertificateStatus.ACTIVE
            assert active.status is CertificateVersionStatus.ACTIVE
            row = await check.get(BlockchainTransaction, transaction.id)
            assert row is not None
            request_audits = (
                await check.scalars(
                    select(AuditLog).where(
                        AuditLog.action == "blockchain.certificate_revocation.requested"
                    )
                )
            ).all()
            assert len(request_audits) == 1
            assert request_audits[0].actor_user_id == admin_id
            assert request_audits[0].after_json == {"status": "CREATED"}
            assert "legal cancellation" not in str(request_audits[0].after_json)
            row.status = BlockchainTransactionStatus.BROADCAST
            row.tx_hash = TX_HASH
            await check.commit()

        gateway.event_name = "CertificateRevoked"
        await service.confirm(transaction.id)

        async with sessions() as check:
            certificate = await check.get(Certificate, certificate_id)
            active = await check.get(CertificateVersion, active_version_id)
        assert certificate is not None and active is not None
        assert certificate.status is CertificateStatus.REVOKED
        assert certificate.revoked_at is not None
        assert certificate.revoked_at.replace(tzinfo=UTC) == NOW
        assert active.status is CertificateVersionStatus.REVOKED
        assert active.revoked_at is not None
        assert active.revoked_at.replace(tzinfo=UTC) == NOW
        await service._session.close()  # noqa: SLF001
        await engine.dispose()

    asyncio.run(scenario())
