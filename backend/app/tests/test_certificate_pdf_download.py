import asyncio
import hashlib
from typing import cast
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.modules.auth.session_service import AuthPrincipal
from app.modules.blockchain.models import (
    Certificate,
    CertificateVersion,
    CertificateVersionStatus,
)
from app.modules.certificates.errors import (
    CertificateConflictError,
    CertificateForbiddenError,
    CertificateGenerationError,
)
from app.modules.dossiers.models import Dossier, DossierStatus
from app.modules.media.errors import MediaProviderUnavailableError
from app.modules.media.gateway import MediaGateway
from app.modules.media.models import MediaAsset, MediaStatus
from app.tests.test_certificate_issuance import _issuance_service


def test_pdf_download_checks_ownership_and_content_hash() -> None:
    content = b"%PDF-1.4\nTinh Hoa Viet\n"

    class Gateway:
        actual = content

        async def download_asset(self, **kwargs: object) -> bytes:
            assert kwargs["file_format"] == "pdf"
            return self.actual

    async def scenario() -> None:
        service, engine, dossier_id = await _issuance_service(
            DossierStatus.CERTIFICATE_ISSUED
        )
        gateway = Gateway()
        service._media_gateway = cast(MediaGateway, gateway)
        try:
            async with service._session.begin():
                dossier = await service._session.get(Dossier, dossier_id)
                certificate = await service._session.scalar(
                    select(Certificate).where(Certificate.dossier_id == dossier_id)
                )
                media = MediaAsset(
                    id=uuid4(),
                    owner_user_id=dossier.owner_user_id,
                    cloudinary_public_id="thv/certificates/test",
                    cloudinary_version=1,
                    resource_type="raw",
                    access_mode="authenticated",
                    original_filename="THV-2026-TEST.pdf",
                    mime_type="application/pdf",
                    bytes=len(content),
                    sha256=hashlib.sha256(content).hexdigest(),
                    status=MediaStatus.ACTIVE,
                )
                service._session.add(media)
                await service._session.flush()
                certificate.pdf_media_id = media.id
                certificate_id = certificate.id
                owner_id = dossier.owner_user_id
            owner = AuthPrincipal(
                user_id=owner_id,
                session_id=uuid4(),
                email="owner@example.test",
                roles=("USER",),
            )
            downloaded, filename = await service.download_pdf(owner, certificate_id)
            assert downloaded == content
            assert filename.endswith(".pdf")
            stranger = AuthPrincipal(
                user_id=uuid4(),
                session_id=uuid4(),
                email="stranger@example.test",
                roles=("USER",),
            )
            with pytest.raises(CertificateForbiddenError):
                await service.download_pdf(stranger, certificate_id)
            gateway.actual = b"%PDF-tampered"
            with pytest.raises(CertificateGenerationError):
                await service.download_pdf(owner, certificate_id)
        finally:
            await service._session.close()
            await engine.dispose()

    asyncio.run(scenario())


def test_pdf_download_recovers_legacy_raw_public_id_without_extension() -> None:
    content = b"%PDF-1.4\nTinh Hoa Viet\n"

    class Gateway:
        requested: list[str] = []

        async def download_asset(self, **kwargs: object) -> bytes:
            public_id = str(kwargs["public_id"])
            self.requested.append(public_id)
            if not public_id.endswith(".pdf"):
                raise MediaProviderUnavailableError()
            return content

    async def scenario() -> None:
        service, engine, dossier_id = await _issuance_service(
            DossierStatus.CERTIFICATE_ISSUED
        )
        gateway = Gateway()
        service._media_gateway = cast(MediaGateway, gateway)
        try:
            async with service._session.begin():
                dossier = await service._session.get(Dossier, dossier_id)
                certificate = await service._session.scalar(
                    select(Certificate).where(Certificate.dossier_id == dossier_id)
                )
                media = MediaAsset(
                    id=uuid4(),
                    owner_user_id=dossier.owner_user_id,
                    cloudinary_public_id="ip-certificate/production/certificates/test/v1",
                    cloudinary_version=1,
                    resource_type="raw",
                    access_mode="authenticated",
                    original_filename="THV-2026-TEST.pdf",
                    mime_type="application/pdf",
                    bytes=len(content),
                    sha256=hashlib.sha256(content).hexdigest(),
                    status=MediaStatus.ACTIVE,
                )
                service._session.add(media)
                await service._session.flush()
                certificate.pdf_media_id = media.id
                certificate_id = certificate.id
                owner_id = dossier.owner_user_id
            owner = AuthPrincipal(
                user_id=owner_id,
                session_id=uuid4(),
                email="owner@example.test",
                roles=("USER",),
            )
            downloaded, _ = await service.download_pdf(owner, certificate_id)
            assert downloaded == content
            assert gateway.requested == [
                "ip-certificate/production/certificates/test/v1",
                "ip-certificate/production/certificates/test/v1.pdf",
            ]
        finally:
            await service._session.close()
            await engine.dispose()

    asyncio.run(scenario())


def test_historical_pdf_download_uses_requested_version_and_checks_access() -> None:
    content = b"%PDF-1.4\nHistorical certificate\n"

    class Gateway:
        actual = content

        async def download_asset(self, **kwargs: object) -> bytes:
            return self.actual

    async def scenario() -> None:
        service, engine, dossier_id = await _issuance_service(
            DossierStatus.CERTIFICATE_ISSUED
        )
        gateway = Gateway()
        service._media_gateway = cast(MediaGateway, gateway)
        try:
            async with service._session.begin():
                dossier = await service._session.get(Dossier, dossier_id)
                certificate = await service._session.scalar(
                    select(Certificate).where(Certificate.dossier_id == dossier_id)
                )
                assert dossier is not None and certificate is not None
                predecessor = await service._session.scalar(
                    select(CertificateVersion).where(
                        CertificateVersion.certificate_id == certificate.id,
                        CertificateVersion.version_no == 1,
                    )
                )
                assert predecessor is not None
                media = MediaAsset(
                    id=uuid4(),
                    owner_user_id=dossier.owner_user_id,
                    cloudinary_public_id="thv/certificates/historical-v1",
                    cloudinary_version=1,
                    resource_type="raw",
                    access_mode="authenticated",
                    original_filename="THV-2026-TEST-v1.pdf",
                    mime_type="application/pdf",
                    bytes=len(content),
                    sha256=hashlib.sha256(content).hexdigest(),
                    status=MediaStatus.ACTIVE,
                )
                service._session.add(media)
                await service._session.flush()
                predecessor.pdf_media_id = media.id
                predecessor.status = CertificateVersionStatus.SUPERSEDED
                service._session.add(
                    CertificateVersion(
                        id=uuid4(),
                        certificate_id=certificate.id,
                        version_no=2,
                        predecessor_version_id=predecessor.id,
                        dossier_version_id=predecessor.dossier_version_id,
                        metadata_json=dict(predecessor.metadata_json),
                        metadata_hash=predecessor.metadata_hash,
                        status=CertificateVersionStatus.ACTIVE,
                        change_reason="Corrected historical certificate content.",
                    )
                )
                certificate.current_version_no = 2
                certificate.pdf_media_id = None
                certificate_id = certificate.id
                owner_id = dossier.owner_user_id
            owner = AuthPrincipal(
                user_id=owner_id,
                session_id=uuid4(),
                email="owner@example.test",
                roles=("USER",),
            )
            downloaded, filename = await service.download_version_pdf(
                owner, certificate_id, 1
            )
            assert downloaded == content
            assert filename.endswith("-v1.pdf")
            with pytest.raises(CertificateConflictError):
                await service.download_version_pdf(owner, certificate_id, 2)
            stranger = AuthPrincipal(
                user_id=uuid4(),
                session_id=uuid4(),
                email="stranger@example.test",
                roles=("USER",),
            )
            with pytest.raises(CertificateForbiddenError):
                await service.download_version_pdf(stranger, certificate_id, 1)
            gateway.actual = b"%PDF-tampered"
            with pytest.raises(CertificateGenerationError):
                await service.download_version_pdf(owner, certificate_id, 1)
        finally:
            await service._session.close()
            await engine.dispose()

    asyncio.run(scenario())
