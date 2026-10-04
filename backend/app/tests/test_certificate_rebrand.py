import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.modules.blockchain.models import (
    BlockchainTransaction,
    BlockchainTransactionStatus,
    Certificate,
    CertificateStatus,
    CertificateVersion,
    CertificateVersionStatus,
)
from app.modules.certificates.rebrand import (
    CertificateRebrandService,
    replacement_metadata,
)
from app.modules.certificates.repository import CertificateRepository
from app.modules.dossiers.models import Dossier, DossierStatus, DossierVisibility
from app.modules.public.models import (
    PublicationStatus,
    PublicWork,
    PublicWorkVisibility,
)
from app.modules.public.repository import PublicRepository
from app.tests.test_certificate_issuance import (
    SuccessfulRenderer,
    SuccessfulStorage,
    _issuance_service,
)


async def _attach_confirmed_proof(session, dossier_id):
    async with session.begin():
        old = await session.scalar(
            select(Certificate).where(Certificate.dossier_id == dossier_id)
        )
        version = await session.scalar(
            select(CertificateVersion).where(
                CertificateVersion.certificate_id == old.id
            )
        )
        version.metadata_json = {
            **version.metadata_json,
            "asset": {"title": "Public asset", "subject": "Chưa công bố"},
        }
        proof = BlockchainTransaction(
            id=uuid4(),
            dossier_id=dossier_id,
            dossier_version_id=version.dossier_version_id,
            network="local",
            chain_id=31_337,
            contract_address="0x" + "12" * 20,
            method="recordProof",
            payload_hash="ab" * 32,
            tx_hash="0x" + "cd" * 32,
            status=BlockchainTransactionStatus.CONFIRMED,
            confirmations=1,
            confirmed_at=datetime(2026, 9, 16, tzinfo=UTC),
        )
        session.add(proof)
        return proof.id


def test_replacement_metadata_uses_thv_and_public_author() -> None:
    source: dict[str, object] = {
        "certificateNumber": "TMI-2026-OLD",
        "certificateVersion": 3,
        "dossierCode": "TMI-2026-DOSSIER",
        "asset": {"title": "Tác phẩm", "subject": "Chủ thể hồ sơ TMI"},
    }

    metadata, digest = replacement_metadata(
        source,
        certificate_number="THV-2026-NEW",
        issued_at=datetime(2026, 9, 16, tzinfo=UTC),
        expires_at=datetime(2027, 9, 16, tzinfo=UTC),
        author_display_name="Tác giả đã công bố",
    )

    assert metadata["certificateNumber"] == "THV-2026-NEW"
    assert metadata["certificateVersion"] == 1
    assert metadata["dossierCode"] == "TMI-2026-DOSSIER"
    assert metadata["asset"] == {
        "title": "Tác phẩm",
        "subject": "Tác giả đã công bố",
    }
    assert len(digest) == 64
    assert source["certificateNumber"] == "TMI-2026-OLD"


def test_thv_reissue_preparation_keeps_legacy_proof_live_until_new_anchor() -> None:
    async def scenario() -> None:
        _, engine, dossier_id = await _issuance_service(DossierStatus.PUBLISHED)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with sessions() as session:
                proof_id = await _attach_confirmed_proof(session, dossier_id)
                reissue = CertificateRebrandService(
                    session,
                    public_base_url="https://decu.tinhhoaviet.org.vn",
                    environment="test",
                    validity_days=365,
                )
                preview = await reissue.run(dry_run=True)
                assert preview.candidates == 1 and preview.prepared == 0
                report = await reissue.run(dry_run=False)
                assert report.prepared == 1
                assert (await reissue.run(dry_run=False)).prepared == 0
                async with session.begin():
                    certificates = tuple(
                        await session.scalars(
                            select(Certificate).where(
                                Certificate.dossier_id == dossier_id
                            )
                        )
                    )
                    legacy = next(
                        row
                        for row in certificates
                        if row.certificate_number.startswith("CNS-")
                    )
                    replacement = next(
                        row
                        for row in certificates
                        if row.certificate_number.startswith("THV-")
                    )
                    new_version = await session.scalar(
                        select(CertificateVersion).where(
                            CertificateVersion.certificate_id == replacement.id
                        )
                    )
                    assert legacy.status is CertificateStatus.ACTIVE
                    assert new_version is not None
                    assert new_version.status is CertificateVersionStatus.ANCHOR_PENDING
                    assert new_version.blockchain_transaction_id == proof_id
                    assert (
                        new_version.metadata_json["certificateNumber"]
                        == replacement.certificate_number
                    )
                    admin_rows, admin_total = await CertificateRepository(
                        session
                    ).list_admin(
                        search=None,
                        status=None,
                        publication_status=None,
                        offset=0,
                        limit=10,
                    )
                    assert admin_total == len(admin_rows) == 1
                    assert admin_rows[0][0].id == legacy.id
                    requests, request_total = await CertificateRepository(
                        session
                    ).list_version_requests(offset=0, limit=10)
                    assert requests == () and request_total == 0
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_reissue_requires_a_confirmed_thv_dossier_proof() -> None:
    async def scenario() -> None:
        _, engine, dossier_id = await _issuance_service(DossierStatus.PUBLISHED)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with sessions() as session:
                reissue = CertificateRebrandService(
                    session,
                    public_base_url="https://decu.tinhhoaviet.org.vn",
                    environment="test",
                    validity_days=365,
                )
                with pytest.raises(RuntimeError, match="confirmed THV dossier proof"):
                    await reissue.run(dry_run=False)
                async with session.begin():
                    numbers = tuple(
                        await session.scalars(
                            select(Certificate.certificate_number).where(
                                Certificate.dossier_id == dossier_id
                            )
                        )
                    )
                    assert all(not number.startswith("THV-") for number in numbers)
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_reissue_renders_pdf_then_revokes_old_and_switches_public_work() -> None:
    async def scenario() -> None:
        certificate_service, engine, dossier_id = await _issuance_service(
            DossierStatus.PUBLISHED
        )
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with sessions() as session:
                proof_id = await _attach_confirmed_proof(session, dossier_id)
                async with session.begin():
                    dossier = await session.get(Dossier, dossier_id)
                    dossier.visibility = DossierVisibility.PUBLIC
                    dossier.published_at = datetime(2026, 9, 16, tzinfo=UTC)
                    old = await session.scalar(
                        select(Certificate).where(Certificate.dossier_id == dossier_id)
                    )
                    session.add(
                        PublicWork(
                            id=uuid4(),
                            dossier_id=dossier_id,
                            certificate_id=old.id,
                            owner_user_id=dossier.owner_user_id,
                            category_id=dossier.category_id,
                            slug="thv-reissue-test",
                            title="Public asset",
                            short_description="Published asset",
                            publication_status=PublicationStatus.PUBLISHED,
                            visibility=PublicWorkVisibility.PUBLIC,
                            published_at=datetime(2026, 9, 16, tzinfo=UTC),
                            author_display_name="Public author",
                        )
                    )
                reissue = CertificateRebrandService(
                    session,
                    public_base_url="https://decu.tinhhoaviet.org.vn",
                    environment="test",
                    validity_days=365,
                )
                report = await reissue.run(dry_run=False)
                assert report.prepared == 1
                version_ids = await reissue.ready_to_render()
                assert version_ids == report.replacement_version_ids
                async with session.begin():
                    old = await session.scalar(
                        select(Certificate).where(
                            Certificate.dossier_id == dossier_id,
                            Certificate.certificate_number.startswith("CNS-"),
                        )
                    )
                    assert old.status is CertificateStatus.ACTIVE
            certificate_service._renderer = SuccessfulRenderer()
            certificate_service._storage = SuccessfulStorage()
            await certificate_service.render_version(version_ids[0])
            async with sessions() as session:
                async with session.begin():
                    rows = tuple(
                        await session.scalars(
                            select(Certificate).where(
                                Certificate.dossier_id == dossier_id
                            )
                        )
                    )
                    old = next(
                        row for row in rows if row.certificate_number.startswith("CNS-")
                    )
                    new = next(
                        row for row in rows if row.certificate_number.startswith("THV-")
                    )
                    version = await session.scalar(
                        select(CertificateVersion).where(
                            CertificateVersion.certificate_id == new.id
                        )
                    )
                    public_work = await session.scalar(
                        select(PublicWork).where(PublicWork.dossier_id == dossier_id)
                    )
                    assert old.status is CertificateStatus.REVOKED
                    assert new.status is CertificateStatus.ACTIVE
                    assert new.pdf_media_id is not None
                    assert version.status is CertificateVersionStatus.ACTIVE
                    assert version.blockchain_transaction_id == proof_id
                    assert version.metadata_json["asset"]["subject"] == "Public author"
                    assert public_work.certificate_id == new.id
                    by_transaction = await PublicRepository(
                        session
                    ).find_by_transaction("0x" + "cd" * 32)
                    assert by_transaction is not None
                    assert by_transaction.certificate_number == new.certificate_number
                    assets, total = await PublicRepository(session).list_assets(
                        query=None, category=None, offset=0, limit=10
                    )
                    assert total == len(assets) == 1
                    assert assets[0][0].id == new.id
                    public_asset = await PublicRepository(session).get_asset(
                        "issued-asset"
                    )
                    assert public_asset is not None
                    assert public_asset[0].id == new.id
                    categories = await PublicRepository(session).list_categories()
                    assert any(count == 1 for _, count in categories)
            await certificate_service._session.close()
        finally:
            await engine.dispose()

    asyncio.run(scenario())
