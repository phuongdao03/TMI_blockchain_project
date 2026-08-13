import asyncio
from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)

from app.db.base import Base
from app.modules.audit.models import AuditLog
from app.modules.auth.models import User, UserStatus
from app.modules.auth.security import OutboxPayloadCipher
from app.modules.blockchain.models import (
    BlockchainTransaction,
    BlockchainTransactionStatus,
    Certificate,
    CertificateStatus,
    CertificateVersion,
)
from app.modules.certificates.errors import CertificateGenerationError
from app.modules.certificates.metadata import (
    CertificateMetadataBuilder,
    CertificateNumberingService,
)
from app.modules.certificates.pdf import CertificatePdfRenderer, RenderedCertificate
from app.modules.certificates.service import CertificateService
from app.modules.certificates.storage import CertificateStorage, StoredCertificate
from app.modules.dossiers.models import (
    Category,
    Dossier,
    DossierStatus,
    DossierVersion,
)
from app.modules.media.gateway import MediaGateway
from app.modules.media.models import MediaAsset  # noqa: F401

NOW = datetime(2026, 7, 31, 10, 0, tzinfo=UTC)


class FailingRenderer:
    def render(self, *, metadata: object, verification_url: str) -> None:
        del metadata, verification_url
        raise OSError("render failed")


class SuccessfulRenderer:
    def render(
        self,
        *,
        metadata: object,
        verification_url: str,
    ) -> RenderedCertificate:
        assert metadata
        assert verification_url.startswith("https://")
        return RenderedCertificate(
            content=b"%PDF-version",
            qr_png=b"png",
            sha256="66" * 32,
            template_version="test-v1",
            generator_version="test",
        )


class SuccessfulStorage:
    async def upload_pdf(
        self,
        *,
        public_id: str,
        content: bytes,
    ) -> StoredCertificate:
        assert public_id.endswith("/v1")
        assert content == b"%PDF-version"
        return StoredCertificate(
            public_id=public_id,
            version=1,
            bytes=len(content),
            sha256="77" * 32,
        )


async def _issuance_service(
    status: DossierStatus,
) -> tuple[CertificateService, AsyncEngine, UUID]:
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
    category = Category(id=uuid4(), code=uuid4().hex[:12], name="Certificate")
    dossier = Dossier(
        id=uuid4(),
        code=f"DOS-{uuid4().hex[:12]}",
        owner_user_id=user.id,
        category_id=category.id,
        title="Issued asset",
        current_version_no=1,
    )
    dossier._set_status_from_workflow(status)
    dossier_version = DossierVersion(
        id=uuid4(),
        dossier_id=dossier.id,
        version_no=1,
        snapshot_json={"dossier": {"title": dossier.title}},
        canonical_hash="11" * 32,
        submitted_by=user.id,
    )
    certificate = Certificate(
        id=uuid4(),
        certificate_number=f"TMI-2026-{uuid4().hex[:12].upper()}",
        dossier_id=dossier.id,
        current_version_no=1,
        status=CertificateStatus.ACTIVE,
        issued_at=NOW,
        public_token_hash="22" * 32,
        qr_payload="https://tmi.example/kiem-tra/token",
    )
    transaction = BlockchainTransaction(
        id=uuid4(),
        dossier_id=dossier.id,
        dossier_version_id=dossier_version.id,
        certificate_id=certificate.id,
        network="local",
        chain_id=31_337,
        contract_address="0x" + "12" * 20,
        method="issueCertificate",
        payload_hash="33" * 32,
        tx_hash="0x" + "44" * 32,
        status=BlockchainTransactionStatus.CONFIRMED,
        confirmations=1,
        confirmed_at=NOW,
    )
    version = CertificateVersion(
        id=uuid4(),
        certificate_id=certificate.id,
        version_no=1,
        dossier_version_id=dossier_version.id,
        metadata_json={"certificateNumber": certificate.certificate_number},
        metadata_hash="55" * 32,
        blockchain_transaction_id=transaction.id,
    )
    async with sessions() as session:
        session.add_all(
            [
                user,
                category,
                dossier,
                dossier_version,
                certificate,
                transaction,
                version,
            ]
        )
        await session.commit()
    service = CertificateService(
        session=sessions(),
        media_gateway=cast(MediaGateway, object()),
        storage=cast(CertificateStorage, object()),
        renderer=cast(CertificatePdfRenderer, FailingRenderer()),
        metadata_builder=CertificateMetadataBuilder(),
        numbering=CertificateNumberingService(),
        payload_cipher=OutboxPayloadCipher(
            key=bytes(range(32)),
            key_id="certificate-test-v1",
        ),
        public_base_url="https://tmi.example",
        environment="test",
        delivery_ttl_seconds=300,
        validity_days=365,
        clock=lambda: NOW,
    )
    return service, engine, dossier.id


def test_pending_anchor_is_a_noop_and_safe_to_replay() -> None:
    async def scenario() -> None:
        service, engine, dossier_id = await _issuance_service(
            DossierStatus.ANCHOR_PENDING
        )
        assert await service.process_issuance(dossier_id) is None
        assert await service.process_issuance(dossier_id) is None
        await service._session.close()  # noqa: SLF001
        await engine.dispose()

    asyncio.run(scenario())


def test_duplicate_issue_event_returns_one_logical_certificate() -> None:
    async def scenario() -> None:
        service, engine, dossier_id = await _issuance_service(
            DossierStatus.CERTIFICATE_ISSUED
        )
        first = await service.process_issuance(dossier_id)
        second = await service.process_issuance(dossier_id)
        assert first is not None
        assert second is not None
        assert first.id == second.id
        assert first.certificate_number == second.certificate_number
        await service._session.close()  # noqa: SLF001
        await engine.dispose()

    asyncio.run(scenario())


def test_failed_pdf_keeps_issuance_recoverable() -> None:
    async def scenario() -> None:
        service, engine, dossier_id = await _issuance_service(DossierStatus.ANCHORED)
        with pytest.raises(CertificateGenerationError):
            await service.process_issuance(dossier_id)
        await service._session.close()  # noqa: SLF001
        await engine.dispose()

    asyncio.run(scenario())


def test_version_pdf_preserves_anchored_metadata() -> None:
    async def scenario() -> None:
        service, engine, dossier_id = await _issuance_service(
            DossierStatus.CERTIFICATE_ISSUED
        )
        service._renderer = cast(CertificatePdfRenderer, SuccessfulRenderer())  # noqa: SLF001
        service._storage = cast(CertificateStorage, SuccessfulStorage())  # noqa: SLF001
        async with service._session.begin():  # noqa: SLF001
            certificate = await service._certificates.get_by_dossier(dossier_id)  # noqa: SLF001
            assert certificate is not None
            version = await service._certificates.get_version(  # noqa: SLF001
                (
                    await service._certificates.list_versions(certificate.id)  # noqa: SLF001
                )[0].id
            )
            assert version is not None
            version_id = version.id
            original_metadata = dict(version.metadata_json)
            original_hash = version.metadata_hash

        await service.render_version(version_id)

        async with service._session.begin():  # noqa: SLF001
            rendered_version = await service._certificates.get_version(version_id)  # noqa: SLF001
            rendered_certificate = await service._certificates.get_by_dossier(  # noqa: SLF001
                dossier_id
            )
        assert rendered_version is not None and rendered_certificate is not None
        assert rendered_version.pdf_media_id == rendered_certificate.pdf_media_id
        assert rendered_version.metadata_json == original_metadata
        assert rendered_version.metadata_hash == original_hash
        async with service._session.begin():  # noqa: SLF001
            audit_rows = (
                await service._session.scalars(  # noqa: SLF001
                    select(AuditLog).where(
                        AuditLog.action == "certificate.version.rendered"
                    )
                )
            ).all()
        assert len(audit_rows) == 1
        assert audit_rows[0].actor_service == "certificate-issuance-worker"
        assert audit_rows[0].resource_id == str(version_id)
        assert audit_rows[0].after_json == {"pdf_ready": True}
        await service._session.close()  # noqa: SLF001
        await engine.dispose()

    asyncio.run(scenario())


def test_successful_issuance_is_audited_once_across_worker_replay() -> None:
    async def scenario() -> None:
        service, engine, dossier_id = await _issuance_service(DossierStatus.ANCHORED)
        service._renderer = cast(CertificatePdfRenderer, SuccessfulRenderer())  # noqa: SLF001
        service._storage = cast(CertificateStorage, SuccessfulStorage())  # noqa: SLF001

        first = await service.process_issuance(dossier_id)
        second = await service.process_issuance(dossier_id)
        assert first is not None and second is not None
        assert first.id == second.id
        assert first.pdf_ready is True

        async with service._session.begin():  # noqa: SLF001
            audit_rows = (
                await service._session.scalars(  # noqa: SLF001
                    select(AuditLog).where(AuditLog.action == "certificate.issued")
                )
            ).all()
        assert len(audit_rows) == 1
        assert audit_rows[0].actor_service == "certificate-issuance-worker"
        assert audit_rows[0].resource_id == str(first.id)
        assert audit_rows[0].after_json == {
            "status": "ACTIVE",
            "pdf_ready": True,
        }
        await service._session.close()  # noqa: SLF001
        await engine.dispose()

    asyncio.run(scenario())


def test_issuance_rolls_back_business_state_when_audit_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        service, engine, dossier_id = await _issuance_service(DossierStatus.ANCHORED)
        service._renderer = cast(CertificatePdfRenderer, SuccessfulRenderer())  # noqa: SLF001
        service._storage = cast(CertificateStorage, SuccessfulStorage())  # noqa: SLF001

        def reject_audit(**_: object) -> None:
            raise RuntimeError("audit unavailable")

        monkeypatch.setattr(service._audit_service, "record", reject_audit)  # noqa: SLF001
        with pytest.raises(RuntimeError, match="audit unavailable"):
            await service.process_issuance(dossier_id)

        async with service._session.begin():  # noqa: SLF001
            certificate = await service._certificates.get_by_dossier(dossier_id)  # noqa: SLF001
            dossier = await service._dossiers.get_by_id(dossier_id)  # noqa: SLF001
        assert certificate is not None and dossier is not None
        assert certificate.pdf_media_id is None
        assert dossier.status is DossierStatus.ANCHORED
        await service._session.close()  # noqa: SLF001
        await engine.dispose()

    asyncio.run(scenario())
