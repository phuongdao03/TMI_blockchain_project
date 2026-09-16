import asyncio
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.modules.audit.service import AuditService
from app.modules.blockchain.models import CertificateStatus
from app.modules.public.editor_service import PublicWorkEditorService
from app.modules.public.errors import (
    PublicWorkForbiddenError,
    PublicWorkMetadataValidationError,
    PublicWorkVersionConflictError,
)
from app.tests.test_publication_workflow import _cipher, _principal, _seed


def test_listing_toggle_does_not_publish_or_mutate_issued_certificate(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'visibility.sqlite3').as_posix()}"
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            work_id, owner_id = await _seed(session)
            service = PublicWorkEditorService(
                session=session, audit=AuditService(session), payload_cipher=_cipher()
            )
            async with session.begin():
                context = await service._repository.get_publication_context(work_id)
                assert context is not None and context.certificate is not None
                certificate = context.certificate
                original = (
                    certificate.certificate_number,
                    certificate.qr_payload,
                    certificate.status,
                    certificate.current_version_no,
                )
                publication_status = context.work.publication_status
            with pytest.raises(PublicWorkForbiddenError):
                await service.configure_certificate_listing(
                    _principal(owner_id, "USER"),
                    certificate.id,
                    expected_version=1,
                    show=False,
                    request_id="forbidden",
                )
            updated = await service.configure_certificate_listing(
                _principal(owner_id, "SUPER_ADMIN"),
                certificate.id,
                expected_version=1,
                show=False,
                request_id="hide",
            )
            assert updated.show_certificate is False and updated.version == 2
            assert updated.publication_status == publication_status
            assert (
                certificate.certificate_number,
                certificate.qr_payload,
                certificate.status,
                certificate.current_version_no,
            ) == original
            assert (
                await service.preview(_principal(owner_id, "SUPER_ADMIN"), work_id)
            ).certificate is None
            with pytest.raises(PublicWorkVersionConflictError):
                await service.configure_certificate_listing(
                    _principal(owner_id, "SUPER_ADMIN"),
                    certificate.id,
                    expected_version=1,
                    show=True,
                    request_id="stale",
                )
            async with session.begin():
                certificate.status = CertificateStatus.REVOKED
            with pytest.raises(PublicWorkMetadataValidationError):
                await service.configure_certificate_listing(
                    _principal(owner_id, "SUPER_ADMIN"),
                    certificate.id,
                    expected_version=2,
                    show=True,
                    request_id="revoked",
                )
        await engine.dispose()

    asyncio.run(exercise())
