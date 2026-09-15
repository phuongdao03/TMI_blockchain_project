import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.modules.blockchain.models import CertificateStatus
from app.modules.media.models import MediaEncryptionStatus, MediaStatus
from app.modules.public.errors import PublicWorkNotFoundError
from app.modules.public.media_delivery import (
    PublicMediaDeliveryService,
    content_response,
)
from app.modules.public.models import (
    DerivativeStatus,
    PublicationStatus,
    PublicWorkVisibility,
    VideoQualityProfile,
)


@pytest.mark.parametrize(
    ("requested", "expected", "header"),
    [
        ("bytes=1-3", b"bcd", "bytes 1-3/6"),
        ("bytes=3-", b"def", "bytes 3-5/6"),
        ("bytes=-2", b"ef", "bytes 4-5/6"),
        ("bytes=0-99", b"abcdef", "bytes 0-5/6"),
    ],
)
def test_legacy_video_seeking(requested: str, expected: bytes, header: str) -> None:
    response = content_response(b"abcdef", "video/mp4", requested)
    assert response.status_code == 206
    assert response.body == expected
    assert response.headers["content-range"] == header
    assert response.headers["cache-control"] == "private, no-store"


@pytest.mark.parametrize(
    "requested", ["bytes=9-", "bytes=-0", "bytes=2-1", "bytes=0-1,3-4", "invalid"]
)
def test_invalid_range(requested: str) -> None:
    with pytest.raises(HTTPException) as error:
        content_response(b"abcdef", "video/mp4", requested)
    assert error.value.status_code == 416


def test_encrypted_video_poster_delivers_real_frame_without_upload() -> None:
    async def exercise() -> None:
        work_id, dossier_id = uuid4(), uuid4()
        work = SimpleNamespace(
            dossier_id=dossier_id,
            publication_status=PublicationStatus.PUBLISHED,
            published_at=datetime.now(UTC),
            visibility=PublicWorkVisibility.PUBLIC,
        )
        relation = SimpleNamespace(
            public_work_id=work_id, derivative_status=DerivativeStatus.READY
        )
        asset = SimpleNamespace(
            id=uuid4(),
            status=MediaStatus.ACTIVE,
            deleted_at=None,
            access_mode="authenticated",
            encryption_status=MediaEncryptionStatus.ENCRYPTED,
            mime_type="video/mp4",
        )
        session = MagicMock()
        session.begin.return_value.__aenter__ = AsyncMock()
        session.begin.return_value.__aexit__ = AsyncMock(return_value=False)
        gateway = MagicMock()
        retained_video = b"decrypted retained video"
        jpeg_frame = b"\xff\xd8real video frame\xff\xd9"
        with (
            patch("app.modules.public.media_delivery.PublicMediaRepository") as media,
            patch("app.modules.public.media_delivery.PublicWorkRepository") as catalog,
            patch(
                "app.modules.public.media_delivery.read_retained_content",
                new=AsyncMock(return_value=retained_video),
            ),
            patch(
                "app.modules.public.media_delivery.extract_video_poster",
                new=AsyncMock(return_value=jpeg_frame),
                create=True,
            ),
        ):
            media.return_value.get_relation_with_asset = AsyncMock(
                return_value=(relation, asset)
            )
            media.return_value.is_source_evidence_asset = AsyncMock(return_value=True)
            catalog.return_value.get_publication_context = AsyncMock(
                return_value=SimpleNamespace(
                    work=work,
                    category=SimpleNamespace(is_active=True),
                    certificate=SimpleNamespace(
                        status=CertificateStatus.ACTIVE,
                        dossier_id=dossier_id,
                        expires_at=None,
                    ),
                )
            )
            response = await PublicMediaDeliveryService(session, gateway, None).deliver(
                work_id, uuid4(), None, None, poster=True
            )
            assert response.status_code == 200
            assert response.headers["content-type"] == "image/jpeg"
            assert response.body == jpeg_frame
            assert response.headers["cache-control"] == "private, no-store"
            assert gateway.mock_calls == []

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "blocked",
    [
        None,
        "hidden",
        "private",
        "revoked",
        "category",
        "source",
        "deleted",
        "unattached",
    ],
)
def test_public_delivery_checks_policy_before_provider_access(
    blocked: str | None,
) -> None:
    async def exercise() -> None:
        work_id, dossier_id = uuid4(), uuid4()
        work = SimpleNamespace(
            dossier_id=dossier_id,
            publication_status=PublicationStatus.PUBLISHED,
            published_at=datetime.now(UTC),
            visibility=PublicWorkVisibility.PUBLIC,
        )
        certificate = SimpleNamespace(
            status=CertificateStatus.ACTIVE, dossier_id=dossier_id, expires_at=None
        )
        category = SimpleNamespace(is_active=True)
        relation = SimpleNamespace(
            public_work_id=work_id,
            derivative_status=DerivativeStatus.READY,
            video_max_width=1280,
            video_quality_profile=VideoQualityProfile.BALANCED,
        )
        asset = SimpleNamespace(
            id=uuid4(),
            status=MediaStatus.ACTIVE,
            deleted_at=None,
            access_mode="authenticated",
            encryption_status=MediaEncryptionStatus.LEGACY_UNENCRYPTED,
            mime_type="video/mp4",
            sha256="a" * 64,
            cloudinary_public_id="protected/original",
            resource_type="video",
        )
        if blocked == "hidden":
            work.publication_status = PublicationStatus.DRAFT
        elif blocked == "private":
            work.visibility = PublicWorkVisibility.PRIVATE
        elif blocked == "revoked":
            certificate.status = CertificateStatus.REVOKED
        elif blocked == "category":
            category.is_active = False
        elif blocked == "deleted":
            asset.deleted_at = datetime.now(UTC)
        elif blocked == "unattached":
            relation.public_work_id = uuid4()
        session = MagicMock()
        session.begin.return_value.__aenter__ = AsyncMock()
        session.begin.return_value.__aexit__ = AsyncMock(return_value=False)
        gateway = MagicMock()
        gateway.create_signed_delivery_url.return_value = (
            "https://example.test/temporary"
        )
        with (
            patch("app.modules.public.media_delivery.PublicMediaRepository") as media,
            patch("app.modules.public.media_delivery.PublicWorkRepository") as catalog,
        ):
            media.return_value.get_relation_with_asset = AsyncMock(
                return_value=(relation, asset)
            )
            media.return_value.is_source_evidence_asset = AsyncMock(
                return_value=blocked != "source"
            )
            catalog.return_value.get_publication_context = AsyncMock(
                return_value=SimpleNamespace(
                    work=work, certificate=certificate, category=category
                )
            )
            service = PublicMediaDeliveryService(session, gateway, None)
            if blocked:
                with pytest.raises(PublicWorkNotFoundError):
                    await service.deliver(work_id, uuid4(), None, None)
                gateway.create_signed_delivery_url.assert_not_called()
            else:
                response = await service.deliver(work_id, uuid4(), None, None)
                assert response.status_code == 307
                assert (
                    gateway.create_signed_delivery_url.call_args.kwargs["public_id"]
                    == "protected/original"
                )
                assert (
                    "q_auto:good"
                    in gateway.create_signed_delivery_url.call_args.kwargs[
                        "transformation"
                    ]
                )

    asyncio.run(exercise())
