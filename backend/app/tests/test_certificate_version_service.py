import asyncio
from datetime import UTC, datetime
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
from app.modules.audit.service import AuditService
from app.modules.auth.models import User, UserStatus
from app.modules.auth.security import hash_verification_token
from app.modules.auth.session_service import AuthPrincipal
from app.modules.blockchain.models import (
    Certificate,
    CertificateStatus,
    CertificateVersion,
    CertificateVersionStatus,
)
from app.modules.certificates.errors import (
    CertificateConflictError,
    CertificateForbiddenError,
)
from app.modules.certificates.metadata import CertificateMetadataBuilder
from app.modules.certificates.version_service import CertificateVersionService
from app.modules.council.models import (
    CouncilCase,
    CouncilCaseDecision,
    CouncilSession,
    CouncilSessionStatus,
)
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

NOW = datetime(2026, 8, 11, 9, 0, tzinfo=UTC)
REQUEST_REASON = "Correct the ownership evidence after the approved legal update."
REJECTION_REASON = "The correction evidence does not support the requested change."


def _principal(
    user_id: UUID,
    *roles: str,
    permissions: tuple[str, ...],
) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=user_id,
        session_id=uuid4(),
        email=f"{user_id}@example.test",
        roles=roles,
        permissions=permissions,
    )


async def _fixture() -> tuple[
    CertificateVersionService,
    async_sessionmaker[AsyncSession],
    AsyncEngine,
    UUID,
    UUID,
    UUID,
    UUID,
    UUID,
]:
    engine = create_async_engine("sqlite+aiosqlite://")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    owner_id = uuid4()
    admin_id = uuid4()
    outsider_id = uuid4()
    dossier_id = uuid4()
    target_version_id = uuid4()
    certificate_id = uuid4()
    media_id = uuid4()
    snapshot = {
        "schemaVersion": 1,
        "dossier": {"code": "DOS-CORRECTION", "title": "Corrected work"},
        "evidences": [
            {
                "mediaAssetId": str(media_id),
                "media": {
                    "mimeType": "application/pdf",
                    "bytes": 128,
                    "sha256": "a" * 64,
                    "hashAlgorithm": "SHA-256",
                    "hashByteLength": 128,
                    "inspectionPolicyVersion": CURRENT_INSPECTION_POLICY_VERSION,
                    "storageObjectVersion": 4,
                    "hashComputedAt": "2026-08-11T09:00:00Z",
                },
            }
        ],
    }
    category = Category(id=uuid4(), code="CERT", name="Certificate")
    dossier = Dossier(
        id=dossier_id,
        code="DOS-CORRECTION",
        owner_user_id=owner_id,
        category_id=category.id,
        title="Corrected work",
        current_version_no=2,
    )
    dossier._set_status_from_workflow(DossierStatus.CERTIFICATE_ISSUED)
    source_version = DossierVersion(
        id=uuid4(),
        dossier_id=dossier_id,
        version_no=1,
        snapshot_json={"schemaVersion": 1, "evidences": []},
        canonical_hash="1" * 64,
        submitted_by=owner_id,
    )
    target_version = DossierVersion(
        id=target_version_id,
        dossier_id=dossier_id,
        version_no=2,
        snapshot_json=snapshot,
        canonical_hash=snapshot_sha256(snapshot),
        submitted_by=owner_id,
    )
    certificate = Certificate(
        id=certificate_id,
        certificate_number="TMI-2026-CORRECTION",
        dossier_id=dossier_id,
        current_version_no=1,
        status=CertificateStatus.ACTIVE,
        issued_at=NOW,
        public_token_hash="b" * 64,
        qr_payload="https://tmi.example/verify/token",
    )
    active_version = CertificateVersion(
        id=uuid4(),
        certificate_id=certificate_id,
        version_no=1,
        dossier_version_id=source_version.id,
        metadata_json={"certificateVersion": 1},
        metadata_hash="c" * 64,
        status=CertificateVersionStatus.ACTIVE,
    )
    media = MediaAsset(
        id=media_id,
        owner_user_id=owner_id,
        cloudinary_public_id="evidence/correction",
        cloudinary_version=4,
        resource_type="raw",
        access_mode="authenticated",
        original_filename="correction.pdf",
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
        dossier_version_id=target_version_id,
        media_asset_id=media_id,
        evidence_type="OWNERSHIP_DOCUMENT",
        title="Corrected ownership evidence",
    )
    council_session = CouncilSession(
        id=uuid4(),
        code="COUNCIL-CORRECTION",
        title="Correction approval",
        scheduled_at=NOW,
        status=CouncilSessionStatus.CLOSED,
        quorum_required=1,
    )
    council_case = CouncilCase(
        id=uuid4(),
        session_id=council_session.id,
        dossier_id=dossier_id,
        dossier_version_id=target_version_id,
        decision=CouncilCaseDecision.APPROVE,
    )
    users = [
        User(id=user_id, email=f"{user_id}@example.test", status=UserStatus.ACTIVE)
        for user_id in (owner_id, admin_id, outsider_id)
    ]
    async with sessions() as session:
        session.add_all(
            [
                *users,
                category,
                dossier,
                source_version,
                target_version,
                certificate,
                active_version,
                media,
                evidence,
                council_session,
                council_case,
            ]
        )
        await session.commit()

    session = sessions()
    service = CertificateVersionService(
        session=session,
        metadata_builder=CertificateMetadataBuilder(),
        audit=AuditService(session),
        clock=lambda: NOW,
        public_base_url="https://tmi.example",
        environment="test",
        token_factory=lambda: "version-token-for-test",
    )
    return (
        service,
        sessions,
        engine,
        certificate_id,
        target_version_id,
        owner_id,
        admin_id,
        outsider_id,
    )


def test_request_and_reject_preserve_active_version_history() -> None:
    async def scenario() -> None:
        (
            service,
            sessions,
            engine,
            certificate_id,
            target_version_id,
            owner_id,
            admin_id,
            _,
        ) = await _fixture()
        owner = _principal(
            owner_id,
            "APPLICANT",
            permissions=("certificate.version.request",),
        )
        requested = await service.request(
            owner,
            certificate_id=certificate_id,
            dossier_version_id=target_version_id,
            reason=REQUEST_REASON,
        )
        assert requested.version_no == 2
        assert requested.status is CertificateVersionStatus.PENDING_APPROVAL

        admin = _principal(
            admin_id,
            "SUPER_ADMIN",
            permissions=("certificate.version.decide",),
        )
        rejected = await service.reject(
            admin,
            requested.id,
            reason=REJECTION_REASON,
        )
        assert rejected.status is CertificateVersionStatus.REJECTED

        async with sessions() as check:
            certificate = await check.get(Certificate, certificate_id)
            active = await check.scalar(
                select(CertificateVersion).where(
                    CertificateVersion.certificate_id == certificate_id,
                    CertificateVersion.status == CertificateVersionStatus.ACTIVE,
                )
            )
            audit_actions = tuple(
                await check.scalars(select(AuditLog.action).order_by(AuditLog.action))
            )
        assert certificate is not None and certificate.current_version_no == 1
        assert active is not None and active.version_no == 1
        assert audit_actions == (
            "certificate.version.rejected",
            "certificate.version.requested",
        )
        await service.close()
        await engine.dispose()

    asyncio.run(scenario())


def test_correction_request_gets_its_own_immutable_qr_token() -> None:
    async def scenario() -> None:
        (
            service,
            sessions,
            engine,
            certificate_id,
            target_version_id,
            owner_id,
            _,
            _,
        ) = await _fixture()
        owner = _principal(
            owner_id,
            "APPLICANT",
            permissions=("certificate.version.request",),
        )

        requested = await service.request(
            owner,
            certificate_id=certificate_id,
            dossier_version_id=target_version_id,
            reason=REQUEST_REASON,
        )

        async with sessions() as check:
            stored = await check.get(CertificateVersion, requested.id)
        assert stored is not None
        assert stored.qr_payload == "https://tmi.example/verify/version-token-for-test"
        assert stored.public_token_hash == hash_verification_token(
            "version-token-for-test"
        )
        await service.close()
        await engine.dispose()

    asyncio.run(scenario())


def test_request_requires_owner_and_prevents_duplicate_open_request() -> None:
    async def scenario() -> None:
        (
            service,
            _,
            engine,
            certificate_id,
            target_version_id,
            owner_id,
            _,
            outsider_id,
        ) = await _fixture()
        outsider = _principal(
            outsider_id,
            "APPLICANT",
            permissions=("certificate.version.request",),
        )
        with pytest.raises(CertificateForbiddenError):
            await service.request(
                outsider,
                certificate_id=certificate_id,
                dossier_version_id=target_version_id,
                reason=REQUEST_REASON,
            )
        owner = _principal(
            owner_id,
            "APPLICANT",
            permissions=("certificate.version.request",),
        )
        await service.request(
            owner,
            certificate_id=certificate_id,
            dossier_version_id=target_version_id,
            reason=REQUEST_REASON,
        )
        with pytest.raises(CertificateConflictError):
            await service.request(
                owner,
                certificate_id=certificate_id,
                dossier_version_id=target_version_id,
                reason=REQUEST_REASON,
            )
        await service.close()
        await engine.dispose()

    asyncio.run(scenario())


def test_requester_cannot_decide_their_own_request() -> None:
    async def scenario() -> None:
        (
            service,
            _,
            engine,
            certificate_id,
            target_version_id,
            owner_id,
            _,
            _,
        ) = await _fixture()
        requester = _principal(
            owner_id,
            "SUPER_ADMIN",
            permissions=(
                "certificate.version.request",
                "certificate.version.decide",
            ),
        )
        requested = await service.request(
            requester,
            certificate_id=certificate_id,
            dossier_version_id=target_version_id,
            reason=REQUEST_REASON,
        )
        with pytest.raises(CertificateForbiddenError):
            await service.approve(requester, requested.id)
        await service.close()
        await engine.dispose()

    asyncio.run(scenario())
