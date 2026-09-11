import asyncio
import base64
from pathlib import Path
from typing import cast
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.modules.audit.models import AuditLog
from app.modules.audit.service import AuditService
from app.modules.auth.models import User, UserStatus
from app.modules.auth.security import OutboxPayloadCipher
from app.modules.auth.session_service import AuthPrincipal
from app.modules.blockchain.models import Certificate  # noqa: F401
from app.modules.dossiers.models import Category
from app.modules.media.errors import MediaProviderUnavailableError
from app.modules.media.gateway import (
    PublicDerivativeGateway,
    PublicDerivativeMetadata,
)
from app.modules.media.models import MediaAsset, MediaStatus
from app.modules.public.errors import (
    PublicMediaValidationError,
    PublicWorkForbiddenError,
)
from app.modules.public.media_service import (
    PublicMediaInput,
    PublicMediaService,
    PublicMediaWorker,
    PublicVideoPresentationInput,
)
from app.modules.public.models import (
    DerivativeStatus,
    PublicMediaKind,
    PublicWork,
    PublicWorkMedia,
    VideoControlsPreset,
    VideoFitMode,
    VideoQualityProfile,
)
from app.workers.celery_app import celery_app
from app.workers.public_media_tasks import reconcile_pending_public_media


class RecordingDispatcher:
    def __init__(self) -> None:
        self.ids: list[UUID] = []

    def enqueue(self, relation_id: UUID) -> None:
        self.ids.append(relation_id)


def test_pending_public_media_reconciliation_is_scheduled() -> None:
    assert reconcile_pending_public_media.name in celery_app.tasks
    assert (
        celery_app.conf.beat_schedule["reconcile-pending-public-media"]["task"]
        == reconcile_pending_public_media.name
    )


class DerivativeGateway:
    def __init__(self) -> None:
        self.fail = True
        self.calls = 0

    async def create_public_derivative(self, **_: object) -> PublicDerivativeMetadata:
        self.calls += 1
        if self.fail:
            raise MediaProviderUnavailableError()
        return PublicDerivativeMetadata(
            public_id="ip-certificate/public/derivatives/relation",
            url=(
                "https://res.cloudinary.com/demo/image/upload/"
                "ip-certificate/public/derivatives/relation.webp"
            ),
            mime_type="image/webp",
            bytes=2048,
            width=1600,
            height=900,
        )

    async def close(self) -> None:
        return None


def _principal(user_id: UUID, *roles: str) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=user_id,
        session_id=uuid4(),
        email="media-admin@example.test",
        roles=roles,
    )


def test_public_media_permissions_validation_order_removal_and_retry(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'public-media.sqlite3').as_posix()}"
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        owner_id = uuid4()
        work_id = uuid4()
        first_id = uuid4()
        second_id = uuid4()
        unsupported_id = uuid4()
        async with factory() as session:
            async with session.begin():
                session.add(
                    User(
                        id=owner_id,
                        email="media-admin@example.test",
                        password_hash="hash",
                        status=UserStatus.ACTIVE,
                    )
                )
                category = Category(code="MEDIA", name="Media", slug="media")
                session.add(category)
                await session.flush()
                session.add(
                    PublicWork(
                        id=work_id,
                        dossier_id=uuid4(),
                        owner_user_id=owner_id,
                        slug="media-work",
                        title="Media work",
                        short_description="Description",
                        category_id=category.id,
                        thumbnail_media_id=uuid4(),
                    )
                )
                session.add_all(
                    [
                        MediaAsset(
                            id=first_id,
                            owner_user_id=owner_id,
                            cloudinary_public_id="private/owner/first-source",
                            cloudinary_version=1,
                            resource_type="image",
                            access_mode="authenticated",
                            original_filename="first.png",
                            mime_type="image/png",
                            bytes=1024,
                            width=800,
                            height=600,
                            status=MediaStatus.ACTIVE,
                        ),
                        MediaAsset(
                            id=second_id,
                            owner_user_id=owner_id,
                            cloudinary_public_id="private/owner/second-source",
                            cloudinary_version=1,
                            resource_type="image",
                            access_mode="authenticated",
                            original_filename="second.jpg",
                            mime_type="image/jpeg",
                            bytes=1024,
                            width=800,
                            height=600,
                            status=MediaStatus.ACTIVE,
                        ),
                        MediaAsset(
                            id=unsupported_id,
                            owner_user_id=owner_id,
                            cloudinary_public_id="private/owner/unsupported",
                            cloudinary_version=1,
                            resource_type="raw",
                            access_mode="authenticated",
                            original_filename="archive.zip",
                            mime_type="application/zip",
                            bytes=1024,
                            status=MediaStatus.ACTIVE,
                        ),
                    ]
                )
            dispatcher = RecordingDispatcher()
            payload_cipher = OutboxPayloadCipher.from_base64(
                encoded_key=base64.b64encode(b"m" * 32).decode(),
                key_id="public-media-test-v1",
            )
            service = PublicMediaService(
                session=session,
                audit=AuditService(session),
                dispatcher=dispatcher,
                payload_cipher=payload_cipher,
            )
            admin = _principal(owner_id, "SUPER_ADMIN")
            with pytest.raises(PublicWorkForbiddenError):
                await service.attach(
                    _principal(owner_id, "USER"),
                    work_id,
                    PublicMediaInput(first_id, 0, None, "Alt"),
                    request_id="forbidden",
                )
            with pytest.raises(PublicMediaValidationError):
                await service.attach(
                    admin,
                    work_id,
                    PublicMediaInput(unsupported_id, 0, None, None),
                    request_id="unsupported",
                )
            with pytest.raises(PublicMediaValidationError):
                await service.attach(
                    admin,
                    work_id,
                    PublicMediaInput(first_id, 0, None, ""),
                    request_id="missing-alt",
                )
            first = await service.attach(
                admin,
                work_id,
                PublicMediaInput(first_id, 10, " First ", " First image "),
                request_id="first",
            )
            second = await service.attach(
                admin,
                work_id,
                PublicMediaInput(second_id, 5, None, "Second image"),
                request_id="second",
            )
            assert dispatcher.ids == [first.id, second.id]
            await service.reorder(
                admin,
                work_id,
                (first.id, second.id),
                request_id="order",
            )
            rows = await service.list_admin(admin, work_id)
            assert tuple(row.id for row in rows) == (first.id, second.id)
            assert tuple(row.sort_order for row in rows) == (0, 1)

            gateway = DerivativeGateway()
            worker = PublicMediaWorker(
                session=session,
                gateway=cast(PublicDerivativeGateway, gateway),
                environment="local",
                payload_cipher=payload_cipher,
            )
            with pytest.raises(MediaProviderUnavailableError):
                await worker.process(first.id)
            failed = await session.get(PublicWorkMedia, first.id)
            assert failed is not None
            assert failed.derivative_status is DerivativeStatus.FAILED
            assert failed.attempt_count == 1

            gateway.fail = False
            await worker.process(first.id)
            await worker.process(first.id)
            ready = await session.get(PublicWorkMedia, first.id)
            assert ready is not None
            assert ready.derivative_status is DerivativeStatus.READY
            assert ready.attempt_count == 2
            assert gateway.calls == 2

            gallery = await service.list_public(work_id)
            assert len(gallery) == 1
            assert gallery[0].kind is PublicMediaKind.IMAGE
            assert gallery[0].is_thumbnail is True
            serialized = repr(gallery[0])
            assert "first-source" not in serialized
            assert gallery[0].url is not None
            assert "derivatives/relation" in gallery[0].url

            await service.remove(
                admin,
                work_id,
                first.id,
                request_id="remove",
            )
            assert await session.get(MediaAsset, first_id) is not None
            assert await session.get(PublicWorkMedia, first.id) is None
            audit_count = await session.scalar(
                select(func.count()).select_from(AuditLog)
            )
            assert audit_count == 4
        await engine.dispose()

    asyncio.run(exercise())


def test_public_video_worker_creates_a_safe_playable_derivative(tmp_path: Path) -> None:
    class VideoGateway:
        async def create_public_derivative(
            self, **kwargs: object
        ) -> PublicDerivativeMetadata:
            assert kwargs["source_resource_type"] == "video"
            assert kwargs["source_format"] == "mp4"
            assert kwargs["transformation"] == "c_limit,w_640,q_auto:eco,vc_auto"
            assert str(kwargs["derivative_public_id"]).startswith(
                "tmi/local/public/works/"
            )
            return PublicDerivativeMetadata(
                public_id="ip-certificate/public/derivatives/video-relation",
                url=(
                    "https://res.cloudinary.com/demo/video/upload/"
                    "ip-certificate/public/derivatives/video-relation.mp4"
                ),
                mime_type="video/mp4",
                bytes=4096,
                width=1920,
                height=1080,
                duration_ms=12_000,
            )

    async def exercise() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'public-video.sqlite3').as_posix()}"
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        owner_id = uuid4()
        work_id = uuid4()
        relation_id = uuid4()
        async with factory() as session:
            async with session.begin():
                session.add(
                    User(
                        id=owner_id,
                        email="video-owner@example.test",
                        password_hash="hash",
                        status=UserStatus.ACTIVE,
                    )
                )
                category = Category(code="VIDEO", name="Video", slug="video")
                session.add(category)
                await session.flush()
                work = PublicWork(
                    id=work_id,
                    dossier_id=uuid4(),
                    owner_user_id=owner_id,
                    slug="welcome-video",
                    title="Welcome video",
                    short_description="Approved public video",
                    category_id=category.id,
                )
                video = MediaAsset(
                    owner_user_id=owner_id,
                    cloudinary_public_id="private/owner/welcome-video",
                    cloudinary_version=1,
                    resource_type="video",
                    access_mode="authenticated",
                    original_filename="welcome.mp4",
                    mime_type="video/mp4",
                    bytes=4096,
                    status=MediaStatus.ACTIVE,
                )
                session.add_all([work, video])
                await session.flush()
                session.add(
                    PublicWorkMedia(
                        id=relation_id,
                        public_work_id=work_id,
                        media_asset_id=video.id,
                        media_kind=PublicMediaKind.VIDEO,
                        sort_order=0,
                    )
                )

            dispatcher = RecordingDispatcher()
            service = PublicMediaService(
                session=session,
                audit=AuditService(session),
                dispatcher=dispatcher,
                payload_cipher=OutboxPayloadCipher.from_base64(
                    encoded_key=base64.b64encode(b"v" * 32).decode(),
                    key_id="video-test-v1",
                ),
            )
            configured = await service.configure_video(
                _principal(owner_id, "SUPER_ADMIN"),
                work_id,
                relation_id,
                PublicVideoPresentationInput(
                    poster_media_asset_id=None,
                    controls_preset=VideoControlsPreset.MINIMAL,
                    fit_mode=VideoFitMode.COVER,
                    quality_profile=VideoQualityProfile.DATA_SAVER,
                    max_width=640,
                    autoplay=True,
                    loop=True,
                    muted=True,
                ),
                request_id="video-presentation",
            )
            assert configured.derivative_status is DerivativeStatus.PENDING
            assert dispatcher.ids == [relation_id]

            worker = PublicMediaWorker(
                session=session,
                gateway=cast(PublicDerivativeGateway, VideoGateway()),
                environment="local",
                payload_cipher=OutboxPayloadCipher.from_base64(
                    encoded_key=base64.b64encode(b"v" * 32).decode(),
                    key_id="video-test-v1",
                ),
            )
            await worker.process(relation_id)

            relation = await session.get(PublicWorkMedia, relation_id)
            assert relation is not None
            assert relation.derivative_status is DerivativeStatus.READY
            assert relation.derivative_url is not None
            assert "private/owner/welcome-video" not in relation.derivative_url
            assert relation.derivative_mime_type == "video/mp4"
            public_video = (await service.list_public(work_id))[0]
            assert public_video.controls_preset is VideoControlsPreset.MINIMAL
            assert public_video.fit_mode is VideoFitMode.COVER
            assert public_video.autoplay is True
            assert public_video.muted is True
        await engine.dispose()

    asyncio.run(exercise())
