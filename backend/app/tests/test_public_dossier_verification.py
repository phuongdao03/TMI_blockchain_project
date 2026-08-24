import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.modules.auth.models import User, UserStatus
from app.modules.blockchain.models import (
    Certificate,
    CertificateStatus,
    CertificateVersion,
    CertificateVersionStatus,
)
from app.modules.dossiers.models import (
    Category,
    Dossier,
    DossierEvidence,
    DossierStatus,
    DossierVersion,
    DossierVisibility,
    EvidenceVisibility,
)
from app.modules.media.models import MediaAsset, MediaStatus
from app.modules.public.dossier_verification import (
    PublicDossierVerificationService,
)
from app.modules.public.repository import PublicRepository
from app.modules.public.schemas import PublicDossierVerificationData

NOW = datetime(2026, 8, 24, tzinfo=UTC)


def test_public_dossier_verification_projects_only_safe_frozen_documents(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'public-dossier.sqlite3').as_posix()}"
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        owner_id = uuid4()
        category_id = uuid4()
        dossier_id = uuid4()
        dossier_version_id = uuid4()
        certificate_id = uuid4()
        public_asset_id = uuid4()
        private_asset_id = uuid4()

        async with sessions() as session:
            async with session.begin():
                session.add(
                    User(
                        id=owner_id,
                        email="owner-private@example.test",
                        password_hash="not-public",
                        status=UserStatus.ACTIVE,
                    )
                )
                session.add(
                    Category(
                        id=category_id,
                        code="BRAND",
                        name="Thương hiệu",
                    )
                )
                session.add(
                    Dossier(
                        id=dossier_id,
                        code="THV-2026-PUBLIC01",
                        owner_user_id=owner_id,
                        category_id=category_id,
                        title="Bộ nhận diện công khai",
                        slug="bo-nhan-dien-cong-khai",
                        summary="Thông tin đã được phê duyệt để công bố.",
                        visibility=DossierVisibility.PUBLIC,
                        _status=DossierStatus.PUBLISHED,
                        current_version_no=1,
                        published_at=NOW,
                        form_data_json={"ownerEmail": "owner-private@example.test"},
                    )
                )
                session.add(
                    DossierVersion(
                        id=dossier_version_id,
                        dossier_id=dossier_id,
                        version_no=1,
                        snapshot_json={
                            "dossier": {
                                "dossierType": {
                                    "formData": {
                                        "ownerEmail": "owner-private@example.test"
                                    },
                                    "publicFields": [
                                        {
                                            "key": "story",
                                            "label": "Câu chuyện tác phẩm",
                                            "value": (
                                                "Một dấu ấn đã được duyệt công bố."
                                            ),
                                        }
                                    ],
                                }
                            },
                            "evidences": [
                                {
                                    "title": "Ảnh đại diện tác phẩm",
                                    "evidenceType": "ARTWORK_IMAGE",
                                    "accessScope": "PUBLIC_PREVIEW",
                                    "description": (
                                        "Private note must never be exposed."
                                    ),
                                    "media": {
                                        "mimeType": "image/png",
                                        "bytes": 1024,
                                        "sha256": "b" * 64,
                                        "storageObjectKey": (
                                            "private/original-public-proof"
                                        ),
                                    },
                                },
                                {
                                    "title": "Giấy tờ định danh",
                                    "evidenceType": "IDENTITY_DOCUMENT",
                                    "accessScope": "INTERNAL",
                                    "media": {
                                        "mimeType": "application/pdf",
                                        "bytes": 2048,
                                        "sha256": "c" * 64,
                                    },
                                },
                            ],
                            "private": "never expose",
                        },
                        canonical_hash="a" * 64,
                        submitted_by=owner_id,
                        submitted_at=NOW,
                    )
                )
                session.add_all(
                    [
                        MediaAsset(
                            id=public_asset_id,
                            owner_user_id=owner_id,
                            cloudinary_public_id="private/original-public-proof",
                            resource_type="image",
                            access_mode="authenticated",
                            original_filename="artwork.png",
                            mime_type="image/png",
                            bytes=1024,
                            sha256="b" * 64,
                            status=MediaStatus.ACTIVE,
                        ),
                        MediaAsset(
                            id=private_asset_id,
                            owner_user_id=owner_id,
                            cloudinary_public_id="private/identity-document",
                            resource_type="raw",
                            access_mode="authenticated",
                            original_filename="identity.pdf",
                            mime_type="application/pdf",
                            bytes=2048,
                            sha256="c" * 64,
                            status=MediaStatus.ACTIVE,
                        ),
                    ]
                )
                session.add_all(
                    [
                        DossierEvidence(
                            dossier_id=dossier_id,
                            dossier_version_id=dossier_version_id,
                            media_asset_id=public_asset_id,
                            evidence_type="ARTWORK_IMAGE",
                            evidence_role="ARTWORK_IMAGE",
                            access_scope=EvidenceVisibility.PUBLIC_PREVIEW,
                            title="Ảnh đại diện tác phẩm",
                            description="Private note must never be exposed.",
                            display_order=1,
                            is_public=True,
                        ),
                        DossierEvidence(
                            dossier_id=dossier_id,
                            dossier_version_id=dossier_version_id,
                            media_asset_id=private_asset_id,
                            evidence_type="IDENTITY_DOCUMENT",
                            evidence_role="IDENTITY_DOCUMENT",
                            access_scope=EvidenceVisibility.INTERNAL,
                            title="Giấy tờ định danh",
                            description="Private identity evidence.",
                            display_order=2,
                            is_public=False,
                        ),
                    ]
                )
                session.add(
                    Certificate(
                        id=certificate_id,
                        certificate_number="THV-2026-CERT01",
                        dossier_id=dossier_id,
                        current_version_no=1,
                        status=CertificateStatus.ACTIVE,
                        issued_at=NOW,
                        public_token_hash="d" * 64,
                        qr_payload="https://example.test/xac-minh/THV-2026-PUBLIC01",
                    )
                )
                session.add(
                    CertificateVersion(
                        certificate_id=certificate_id,
                        version_no=1,
                        dossier_version_id=dossier_version_id,
                        metadata_json={
                            "certificateVersion": 1,
                            "dossierCode": "THV-2026-PUBLIC01",
                            "asset": {
                                "title": "Bộ nhận diện phiên bản 1",
                                "category": "Thương hiệu phiên bản 1",
                            },
                        },
                        metadata_hash="e" * 64,
                        status=CertificateVersionStatus.ACTIVE,
                    )
                )

            view = await PublicDossierVerificationService(session).get(
                "THV-2026-PUBLIC01"
            )
            assert view is not None
            serialized = PublicDossierVerificationData.model_validate(view).model_dump(
                mode="json", by_alias=True
            )
            assert serialized["code"] == "THV-2026-PUBLIC01"
            assert serialized["publicFields"] == [
                {
                    "key": "story",
                    "label": "Câu chuyện tác phẩm",
                    "value": "Một dấu ấn đã được duyệt công bố.",
                }
            ]
            assert serialized["documents"] == [
                {
                    "title": "Ảnh đại diện tác phẩm",
                    "evidenceType": "ARTWORK_IMAGE",
                    "accessScope": "PUBLIC_PREVIEW",
                    "mimeType": "image/png",
                    "bytes": 1024,
                    "sha256": "b" * 64,
                }
            ]
            payload_text = json.dumps(serialized, ensure_ascii=False)
            for secret in (
                "owner-private@example.test",
                "private/original-public-proof",
                "identity.pdf",
                "Private note",
                "cloudinary",
                "objectKey",
                "ownerEmail",
                "never expose",
            ):
                assert secret not in payload_text

            # A QR code issued for a superseded certificate version must still
            # resolve the snapshot it originally represented, never whatever
            # happens to be the newest certificate version today.
            stored_dossier = await session.get(Dossier, dossier_id)
            stored_certificate = await session.get(Certificate, certificate_id)
            stored_category = await session.get(Category, category_id)
            previous_version = await session.scalar(
                select(CertificateVersion).where(
                    CertificateVersion.certificate_id == certificate_id,
                    CertificateVersion.version_no == 1,
                )
            )
            assert (
                stored_dossier is not None
                and stored_certificate is not None
                and stored_category is not None
                and previous_version is not None
            )
            previous_version.status = CertificateVersionStatus.SUPERSEDED
            previous_version.public_token_hash = "d" * 64
            previous_version.qr_payload = "https://example.test/verify/history-v1"
            next_dossier_version = DossierVersion(
                id=uuid4(),
                dossier_id=dossier_id,
                version_no=2,
                snapshot_json={"dossier": {"title": "PhiÃªn báº£n má»›i"}},
                canonical_hash="f" * 64,
                submitted_by=owner_id,
                submitted_at=NOW,
            )
            next_certificate_version = CertificateVersion(
                certificate_id=certificate_id,
                version_no=2,
                predecessor_version_id=previous_version.id,
                dossier_version_id=next_dossier_version.id,
                metadata_json={"certificateVersion": 2},
                metadata_hash="1" * 64,
                public_token_hash="2" * 64,
                qr_payload="https://example.test/verify/current-v2",
                status=CertificateVersionStatus.ACTIVE,
            )
            stored_dossier.current_version_no = 2
            stored_dossier.title = "Tên hồ sơ hiện tại không được dùng cho QR cũ"
            stored_category.name = "Danh mục hiện tại không được dùng cho QR cũ"
            stored_certificate.current_version_no = 2
            stored_certificate.public_token_hash = "2" * 64
            stored_certificate.qr_payload = "https://example.test/verify/current-v2"
            session.add_all((next_dossier_version, next_certificate_version))
            await session.commit()

            historical = await PublicRepository(session).find_by_token("d" * 64)
            assert historical is not None
            assert historical.version == 1
            assert historical.dossier_hash == "a" * 64
            assert historical.metadata_hash == "e" * 64
            assert historical.asset_title == "Bộ nhận diện phiên bản 1"
            assert historical.category_name == "Thương hiệu phiên bản 1"
            assert historical.dossier_code == "THV-2026-PUBLIC01"

            # A public verification token/number must stop resolving as soon as
            # the dossier is no longer public, even though its certificate exists.
            stored_dossier.visibility = DossierVisibility.PRIVATE
            await session.commit()
            assert (
                await PublicRepository(session).find_by_number("THV-2026-CERT01")
            ) is None

        await engine.dispose()

    asyncio.run(exercise())


def test_public_dossier_verification_hides_private_and_unpublished_dossiers(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        database_path = tmp_path / "public-dossier-gate.sqlite3"
        engine = create_async_engine(f"sqlite+aiosqlite:///{database_path.as_posix()}")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        owner_id = uuid4()
        category_id = uuid4()
        async with sessions() as session:
            async with session.begin():
                session.add(
                    User(
                        id=owner_id,
                        email="owner@example.test",
                        password_hash="not-used",
                        status=UserStatus.ACTIVE,
                    )
                )
                session.add(Category(id=category_id, code="ART", name="Nghệ thuật"))
                for index, (status, visibility) in enumerate(
                    (
                        (DossierStatus.DRAFT, DossierVisibility.PUBLIC),
                        (DossierStatus.PUBLISHED, DossierVisibility.PRIVATE),
                        (DossierStatus.PUBLISHED, DossierVisibility.UNLISTED),
                    ),
                    start=1,
                ):
                    session.add(
                        Dossier(
                            code=f"THV-2026-HIDDEN{index}",
                            owner_user_id=owner_id,
                            category_id=category_id,
                            title="Hồ sơ không công khai",
                            _status=status,
                            visibility=visibility,
                        )
                    )

            service = PublicDossierVerificationService(session)
            for code in (
                "THV-2026-HIDDEN1",
                "THV-2026-HIDDEN2",
                "THV-2026-HIDDEN3",
                "THV-2026-MISSING",
            ):
                assert await service.get(code) is None

        await engine.dispose()

    asyncio.run(exercise())
