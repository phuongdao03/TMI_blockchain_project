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
)
from app.modules.public.models import (
    DerivativeStatus,
    PublicMediaKind,
    PublicWork,
    PublicWorkMedia,
)


class RecordingDispatcher:
    def __init__(self) -> None:
        self.ids: list[UUID] = []

    def enqueue(self, relation_id: UUID) -> None:
        self.ids.append(relation_id)


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
