import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.base import Base
from app.modules.auth.models import User, UserStatus
from app.modules.auth.session_service import AuthPrincipal
from app.modules.media.errors import (
    MediaForbiddenError,
    MediaSignatureInvalidError,
    MediaUploadMetadataMismatchError,
    MediaValidationError,
)
from app.modules.media.gateway import (
    ProviderAssetMetadata,
    UploadAuthorization,
)
from app.modules.media.models import MediaAsset, MediaStatus
from app.modules.media.service import MediaService
from app.modules.media.types import (
    MediaPurpose,
    UploadCompletion,
    UploadIntent,
)

NOW = datetime(2026, 7, 30, 8, 0, tzinfo=UTC)


class RecordingMediaGateway:
    def __init__(self) -> None:
        self.signature_valid = True
        self.metadata: ProviderAssetMetadata | None = None
        self.deleted: list[tuple[str, str]] = []

    async def create_upload_signature(
        self,
        *,
        public_id: str,
        resource_type: str,
        timestamp: int,
        allowed_format: str,
    ) -> UploadAuthorization:
        return UploadAuthorization(
            upload_url="https://api.cloudinary.test/image/upload",
            cloud_name="test-cloud",
            api_key="test-key",
            signature="signed-upload",
            parameters={
                "allowed_formats": allowed_format,
                "overwrite": "false",
                "public_id": public_id,
                "timestamp": str(timestamp),
                "type": "authenticated",
            },
        )

    def verify_upload_result(
        self,
        *,
        public_id: str,
        version: int,
        signature: str,
    ) -> bool:
        return self.signature_valid

    async def get_asset_metadata(
        self,
        *,
        public_id: str,
        resource_type: str,
    ) -> ProviderAssetMetadata:
        assert self.metadata is not None
        return self.metadata

    def create_signed_delivery_url(
        self,
        *,
        public_id: str,
        resource_type: str,
        file_format: str,
        expires_at: int,
    ) -> str:
        return f"https://api.cloudinary.test/download?expires_at={expires_at}"

    async def delete_asset(
        self,
        *,
        public_id: str,
        resource_type: str,
    ) -> None:
        self.deleted.append((public_id, resource_type))

    async def close(self) -> None:
        return None


async def _build_service() -> tuple[
    MediaService,
    RecordingMediaGateway,
    async_sessionmaker[AsyncSession],
    AsyncEngine,
    dict[str, User],
]:
    engine = create_async_engine("sqlite+aiosqlite://")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    users = {
        name: User(
            id=uuid4(),
            email=f"{name}@tmigroup.vn",
            password_hash="not-used",
            status=UserStatus.ACTIVE,
        )
        for name in ("owner", "stranger")
    }
    async with session_factory() as session:
        session.add_all(users.values())
        await session.commit()

    gateway = RecordingMediaGateway()
    service = MediaService(
        session=session_factory(),
        gateway=gateway,
        environment="local",
        signature_ttl_seconds=3_600,
        delivery_ttl_seconds=300,
        avatar_max_bytes=5_242_880,
        evidence_max_bytes=20_971_520,
        clock=lambda: NOW,
    )
    return service, gateway, session_factory, engine, users


def _principal(user: User) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=user.id,
        session_id=uuid4(),
        email=user.email,
        roles=("APPLICANT",),
    )


def test_signed_upload_completion_delivery_and_delete() -> None:
    async def exercise() -> None:
        service, gateway, session_factory, engine, users = await _build_service()
        owner = _principal(users["owner"])

        issued = await service.create_upload_signature(
            owner,
            UploadIntent(
                purpose=MediaPurpose.AVATAR,
                filename="portrait.png",
                mime_type="image/png",
                size=2_048,
            ),
        )
        assert issued.public_id.startswith(
            f"ip-certificate/local/{owner.user_id}/avatar/"
        )
        assert issued.parameters["public_id"] == issued.public_id
        assert issued.expires_at == int(NOW.timestamp()) + 3_600

        gateway.metadata = ProviderAssetMetadata(
            public_id=issued.public_id,
            version=17,
            resource_type="image",
            delivery_type="authenticated",
            file_format="png",
            bytes=2_048,
            width=512,
            height=512,
        )
        completed = await service.complete_upload(
            owner,
            UploadCompletion(
                media_id=issued.media_id,
                public_id=issued.public_id,
                version=17,
                signature="valid-result-signature",
            ),
        )
        assert completed.status is MediaStatus.ACTIVE
        assert completed.width == 512

        delivery = await service.create_signed_url(owner, issued.media_id)
        assert delivery.expires_at == int(NOW.timestamp()) + 300
        assert "expires_at=" in delivery.url

        await service.delete_asset(owner, issued.media_id)
        assert gateway.deleted == [(issued.public_id, "image")]
        async with session_factory() as session:
            asset = await session.get(MediaAsset, issued.media_id)
            assert asset is not None
            assert asset.status is MediaStatus.DELETED
            assert asset.deleted_at is not None
            assert asset.deleted_at.replace(tzinfo=UTC) == NOW

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_completion_rejects_tampered_signature_and_provider_metadata() -> None:
    async def exercise() -> None:
        service, gateway, _, engine, users = await _build_service()
        owner = _principal(users["owner"])
        issued = await service.create_upload_signature(
            owner,
            UploadIntent(
                purpose=MediaPurpose.AVATAR,
                filename="portrait.png",
                mime_type="image/png",
                size=2_048,
            ),
        )

        gateway.signature_valid = False
        with pytest.raises(MediaSignatureInvalidError):
            await service.complete_upload(
                owner,
                UploadCompletion(
                    media_id=issued.media_id,
                    public_id=issued.public_id,
                    version=17,
                    signature="tampered",
                ),
            )

        gateway.signature_valid = True
        gateway.metadata = ProviderAssetMetadata(
            public_id=issued.public_id,
            version=17,
            resource_type="image",
            delivery_type="authenticated",
            file_format="jpg",
            bytes=2_048,
        )
        with pytest.raises(MediaUploadMetadataMismatchError):
            await service.complete_upload(
                owner,
                UploadCompletion(
                    media_id=issued.media_id,
                    public_id=issued.public_id,
                    version=17,
                    signature="valid",
                ),
            )

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_owner_scope_blocks_delivery_and_delete() -> None:
    async def exercise() -> None:
        service, gateway, _, engine, users = await _build_service()
        owner = _principal(users["owner"])
        stranger = _principal(users["stranger"])
        issued = await service.create_upload_signature(
            owner,
            UploadIntent(
                purpose=MediaPurpose.AVATAR,
                filename="portrait.png",
                mime_type="image/png",
                size=2_048,
            ),
        )

        for operation in (
            service.create_signed_url(stranger, issued.media_id),
            service.delete_asset(stranger, issued.media_id),
        ):
            with pytest.raises(MediaForbiddenError):
                await operation
        assert gateway.deleted == []

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_upload_policy_rejects_disallowed_type_size_and_extension() -> None:
    async def exercise() -> None:
        service, _, _, engine, users = await _build_service()
        owner = _principal(users["owner"])
        invalid_intents = (
            UploadIntent(
                purpose=MediaPurpose.AVATAR,
                filename="payload.pdf",
                mime_type="application/pdf",
                size=2_048,
            ),
            UploadIntent(
                purpose=MediaPurpose.AVATAR,
                filename="portrait.png",
                mime_type="image/png",
                size=5_242_881,
            ),
            UploadIntent(
                purpose=MediaPurpose.AVATAR,
                filename="portrait.jpg",
                mime_type="image/png",
                size=2_048,
            ),
        )
        for intent in invalid_intents:
            with pytest.raises(MediaValidationError):
                await service.create_upload_signature(owner, intent)

        public_video = await service.create_upload_signature(
            owner,
            UploadIntent(
                purpose=MediaPurpose.PUBLIC_WORK,
                filename="presentation.webm",
                mime_type="video/webm",
                size=2_048,
            ),
        )
        assert public_video.parameters["allowed_formats"] == "webm"

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())
