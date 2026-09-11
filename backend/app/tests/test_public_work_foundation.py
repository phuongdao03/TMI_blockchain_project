import asyncio
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.modules.auth.models import User, UserStatus
from app.modules.blockchain.models import (
    BlockchainTransaction,
    BlockchainTransactionStatus,
    Certificate,
    CertificateStatus,
    CertificateVersion,
)
from app.modules.dossiers.models import (
    Category,
    Dossier,
    DossierEvidence,
    DossierStatus,
    DossierVersion,
    EvidenceVisibility,
)
from app.modules.media.models import MediaAsset, MediaStatus
from app.modules.public.backfill import PublicWorkDraftBackfill
from app.modules.public.catalog_repository import PublicWorkRepository
from app.modules.public.media_repository import PublicMediaRepository
from app.modules.public.models import (
    PublicationStatus,
    PublicMediaKind,
    PublicWork,
    PublicWorkMedia,
    PublicWorkSlugHistory,
    PublicWorkVisibility,
)


def test_public_work_repository_and_draft_backfill_are_safe(tmp_path: Path) -> None:
    async def exercise() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'public-work.sqlite3').as_posix()}"
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)

        owner_id = uuid4()
        category_id = uuid4()
        eligible_dossier_id = uuid4()
        incomplete_dossier_id = uuid4()
        certificate_id = uuid4()
        dossier_version_id = uuid4()
        incomplete_dossier_version_id = uuid4()
        public_video_id = uuid4()
        incomplete_video_id = uuid4()
        private_document_id = uuid4()
        async with factory() as session:
            async with session.begin():
                session.add(
                    User(
                        id=owner_id,
                        email="owner@catalog.test",
                        password_hash="hash",
                        status=UserStatus.ACTIVE,
                    )
                )
                session.add(
                    Category(
                        id=category_id,
                        code="PUBLIC_WORK",
                        name="Public work",
                    )
                )
                session.add_all(
                    [
                        Dossier(
                            id=eligible_dossier_id,
                            code="DOS-ELIGIBLE",
                            owner_user_id=owner_id,
                            category_id=category_id,
                            title="Tác phẩm đủ điều kiện",
                            slug="tac-pham-du-dieu-kien",
                            summary="Mô tả công khai đã được duyệt.",
                            current_version_no=1,
                            _status=DossierStatus.CERTIFICATE_ISSUED,
                        ),
                        Dossier(
                            id=incomplete_dossier_id,
                            code="DOS-INCOMPLETE",
                            owner_user_id=owner_id,
                            category_id=category_id,
                            title="Thiếu mô tả",
                            slug=None,
                            summary=None,
                            current_version_no=1,
                            _status=DossierStatus.PAID,
                        ),
                    ]
                )
                session.add(
                    DossierVersion(
                        id=dossier_version_id,
                        dossier_id=eligible_dossier_id,
                        version_no=1,
                        snapshot_json={},
                        canonical_hash="c" * 64,
                        submitted_by=owner_id,
                    )
                )
                session.add(
                    DossierVersion(
                        id=incomplete_dossier_version_id,
                        dossier_id=incomplete_dossier_id,
                        version_no=1,
                        snapshot_json={},
                        canonical_hash="e" * 64,
                        submitted_by=owner_id,
                    )
                )
                session.add(
                    BlockchainTransaction(
                        dossier_id=incomplete_dossier_id,
                        dossier_version_id=incomplete_dossier_version_id,
                        network="polygon",
                        chain_id=137,
                        contract_address="0x" + "1" * 40,
                        method="recordProof",
                        payload_hash="e" * 64,
                        tx_hash="0x" + "2" * 64,
                        status=BlockchainTransactionStatus.CONFIRMED,
                        confirmations=1,
                        confirmed_at=datetime(2026, 7, 31, tzinfo=UTC),
                    )
                )
                session.add_all(
                    [
                        MediaAsset(
                            id=public_video_id,
                            owner_user_id=owner_id,
                            cloudinary_public_id="private/owner/welcome-video",
                            resource_type="video",
                            access_mode="authenticated",
                            original_filename="welcome.mp4",
                            mime_type="video/mp4",
                            bytes=4096,
                            status=MediaStatus.ACTIVE,
                        ),
                        MediaAsset(
                            id=incomplete_video_id,
                            owner_user_id=owner_id,
                            cloudinary_public_id="private/owner/incomplete-video",
                            resource_type="video",
                            access_mode="authenticated",
                            original_filename="incomplete.mp4",
                            mime_type="video/mp4",
                            bytes=2048,
                            status=MediaStatus.ACTIVE,
                        ),
                        MediaAsset(
                            id=private_document_id,
                            owner_user_id=owner_id,
                            cloudinary_public_id="private/owner/identity-card",
                            resource_type="image",
                            access_mode="authenticated",
                            original_filename="identity.png",
                            mime_type="image/png",
                            bytes=1024,
                            status=MediaStatus.ACTIVE,
                        ),
                    ]
                )
                session.add(
                    Certificate(
                        id=certificate_id,
                        certificate_number="TMI-2026-1501",
                        dossier_id=eligible_dossier_id,
                        current_version_no=1,
                        status=CertificateStatus.ACTIVE,
                        issued_at=datetime(2026, 7, 31, tzinfo=UTC),
                        public_token_hash="a" * 64,
                        qr_payload="https://example.test/verify/public",
                    )
                )
                session.add(
                    CertificateVersion(
                        certificate_id=certificate_id,
                        version_no=1,
                        dossier_version_id=dossier_version_id,
                        metadata_json={},
                        metadata_hash="d" * 64,
                    )
                )
                session.add_all(
                    [
                        DossierEvidence(
                            dossier_id=incomplete_dossier_id,
                            dossier_version_id=incomplete_dossier_version_id,
                            media_asset_id=incomplete_video_id,
                            evidence_type="INTRO_VIDEO",
                            evidence_role="PRIMARY_WORK",
                            access_scope=EvidenceVisibility.PRIVATE,
                            title="Video đã ký",
                            display_order=0,
                            is_public=False,
                        ),
                        DossierEvidence(
                            dossier_id=eligible_dossier_id,
                            dossier_version_id=dossier_version_id,
                            media_asset_id=public_video_id,
                            evidence_type="INTRO_VIDEO",
                            evidence_role="PRIMARY_WORK",
                            access_scope=EvidenceVisibility.PRIVATE,
                            title="Video chào mừng Tinh hoa Việt",
                            display_order=0,
                            is_public=False,
                        ),
                        DossierEvidence(
                            dossier_id=eligible_dossier_id,
                            dossier_version_id=dossier_version_id,
                            media_asset_id=private_document_id,
                            evidence_type="IDENTITY_DOCUMENT",
                            evidence_role="IDENTITY",
                            access_scope=EvidenceVisibility.PRIVATE,
                            title="Giấy tờ riêng tư",
                            display_order=1,
                            is_public=False,
                        ),
                    ]
                )
                session.add(
                    PublicWork(
                        dossier_id=incomplete_dossier_id,
                        certificate_id=None,
                        owner_user_id=owner_id,
                        organization_id=None,
                        slug="ban-nhap-cu",
                        title="Bản nháp cũ",
                        short_description="Chưa đồng bộ video",
                        publication_status=PublicationStatus.DRAFT,
                        visibility=PublicWorkVisibility.PRIVATE,
                        category_id=category_id,
                    )
                )

            backfill = PublicWorkDraftBackfill(session, batch_size=1)
            dry_run = await backfill.run(dry_run=True)
            assert dry_run.scanned == 1
            assert dry_run.eligible == 1
            assert dry_run.created == 0
            assert dry_run.skipped == 0
            assert dry_run.skip_reasons == {}
            assert (
                await session.scalar(select(func.count()).select_from(PublicWork)) == 1
            )

            applied = await backfill.run(dry_run=False)
            assert applied.created == 1
            work = await PublicWorkRepository(session).get_by_dossier_id(
                eligible_dossier_id
            )
            assert work is not None
            assert work.publication_status is PublicationStatus.DRAFT
            assert work.visibility is PublicWorkVisibility.PRIVATE
            assert work.certificate_id == certificate_id
            assert work.published_at is None
            assert work.slug == "tac-pham-du-dieu-kien"
            incomplete_work = await PublicWorkRepository(session).get_by_dossier_id(
                incomplete_dossier_id
            )
            assert incomplete_work is not None
            assert incomplete_work.short_description == "Chưa đồng bộ video"
            public_media = tuple(
                await session.scalars(
                    select(PublicWorkMedia).where(
                        PublicWorkMedia.public_work_id == work.id
                    )
                )
            )
            assert len(public_media) == 1
            assert public_media[0].media_asset_id == public_video_id
            assert public_media[0].media_kind is PublicMediaKind.VIDEO
            incomplete_media = tuple(
                await session.scalars(
                    select(PublicWorkMedia).where(
                        PublicWorkMedia.public_work_id == incomplete_work.id
                    )
                )
            )
            assert len(incomplete_media) == 1
            assert incomplete_media[0].media_asset_id == incomplete_video_id
            source_candidates = await PublicMediaRepository(
                session
            ).list_current_evidence_assets(eligible_dossier_id)
            assert tuple(asset.id for _, asset in source_candidates) == (
                public_video_id,
                private_document_id,
            )
            assert public_media[0].caption == "Video chào mừng Tinh hoa Việt"

            await backfill.ensure_draft(
                eligible_dossier_id,
                certificate_id=certificate_id,
            )
            assert (
                await session.scalar(select(func.count()).select_from(PublicWorkMedia))
                == 2
            )

            history = PublicWorkSlugHistory(
                public_work_id=work.id,
                slug="slug-cu",
            )
            PublicWorkRepository(session).add_slug_history(history)
            await session.commit()
            resolved = await PublicWorkRepository(session).resolve_slug("slug-cu")
            assert resolved is not None
            assert resolved[0].id == work.id
            assert resolved[1] is True

        await engine.dispose()

    asyncio.run(exercise())
