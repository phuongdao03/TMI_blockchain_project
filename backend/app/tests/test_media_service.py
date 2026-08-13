import asyncio
import hashlib
from datetime import UTC, datetime
from uuid import uuid4

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
from app.modules.auth.models import User, UserStatus
from app.modules.auth.session_service import AuthPrincipal
from app.modules.media.encryption import DocumentEncryptionKeyring
from app.modules.media.errors import (
    MediaForbiddenError,
    MediaInvalidStateError,
    MediaSignatureInvalidError,
    MediaUploadMetadataMismatchError,
    MediaValidationError,
)
from app.modules.media.gateway import (
    ProviderAssetMetadata,
    StoredEncryptedAsset,
    UploadAuthorization,
)
from app.modules.media.models import (
    MediaAsset,
    MediaConfidentiality,
    MediaEncryptionStatus,
    MediaStatus,
)
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
        self.inspection_jobs: list[str] = []
        self.download_content: bytes | None = None

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

    async def download_asset(
        self,
        *,
        public_id: str,
        resource_type: str,
        file_format: str,
        max_bytes: int,
    ) -> bytes:
        if self.download_content is None:
            raise AssertionError("Inspection is outside this service test.")
        return self.download_content

    async def upload_encrypted_asset(
        self,
        *,
        public_id: str,
        content: bytes,
    ) -> StoredEncryptedAsset:
        return StoredEncryptedAsset(
            public_id=public_id,
            version=1,
            bytes=len(content),
        )

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


async def _build_service(
    *,
    encryption_keyring: DocumentEncryptionKeyring | None = None,
) -> tuple[
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
        enqueue_inspection=lambda media_id: gateway.inspection_jobs.append(
            str(media_id)
        ),
        clock=lambda: NOW,
        encryption_keyring=encryption_keyring,
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
            sha256="f" * 64,
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
        assert completed.status is MediaStatus.QUARANTINED
        assert completed.width == 512
        async with session_factory() as session:
            quarantined = await session.get(MediaAsset, issued.media_id)
            assert quarantined is not None
            assert quarantined.sha256 is None
            assert quarantined.confidentiality is MediaConfidentiality.PRIVATE

        assert gateway.inspection_jobs == [str(issued.media_id)]

        replayed = await service.complete_upload(
            owner,
            UploadCompletion(
                media_id=issued.media_id,
                public_id=issued.public_id,
                version=17,
                signature="valid-result-signature",
            ),
        )
        assert replayed.status is MediaStatus.QUARANTINED
        assert gateway.inspection_jobs == [str(issued.media_id), str(issued.media_id)]

        with pytest.raises(MediaInvalidStateError):
            await service.create_signed_url(owner, issued.media_id)

        async with session_factory() as session:
            asset = await session.get(MediaAsset, issued.media_id)
            assert asset is not None
            asset.status = MediaStatus.ACTIVE
            await session.commit()

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
            audit_actions = (
                await session.scalars(
                    select(AuditLog.action)
                    .where(AuditLog.resource_id == str(issued.media_id))
                    .order_by(AuditLog.created_at)
                )
            ).all()
            assert audit_actions == [
                "media.upload_authorized",
                "media.upload_quarantined",
                "media.inspection_requeued",
                "media.delivery_signed",
                "media.deleted",
            ]

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_private_delivery_decrypts_only_after_owner_authorization() -> None:
    async def exercise() -> None:
        keyring = DocumentEncryptionKeyring(
            active_key_id="document-v1",
            keys={"document-v1": b"k" * 32},
        )
        service, gateway, session_factory, engine, users = await _build_service(
            encryption_keyring=keyring
        )
        owner = _principal(users["owner"])
        media_id = uuid4()
        content = b"private file bytes"
        digest = hashlib.sha256(content).hexdigest()
        encrypted = keyring.encrypt(content, media_id=media_id, sha256=digest)
        gateway.download_content = encrypted.ciphertext
        asset = MediaAsset(
            id=media_id,
            owner_user_id=owner.user_id,
            cloudinary_public_id="private/plaintext-removed",
            cloudinary_version=1,
            resource_type="image",
            access_mode="authenticated",
            original_filename="portrait.png",
            mime_type="image/png",
            bytes=len(content),
            sha256=digest,
            status=MediaStatus.ACTIVE,
            confidentiality=MediaConfidentiality.PRIVATE,
            encryption_status=MediaEncryptionStatus.ENCRYPTED,
            encryption_algorithm="AES-256-GCM",
            encryption_key_id=encrypted.key_id,
            encryption_nonce=encrypted.nonce,
            encryption_tag=encrypted.tag,
            encrypted_object_public_id="private/ciphertext",
            encrypted_object_version=9,
            encrypted_bytes=len(encrypted.ciphertext),
            encrypted_at=NOW,
        )
        async with session_factory() as session:
            session.add(asset)
            await session.commit()

        delivery = await service.download_content(owner, media_id)
        assert delivery.content == content
        assert delivery.mime_type == "image/png"
        signed = await service.create_signed_url(owner, media_id)
        assert signed.url == f"/api/v1/media/{media_id}/content"
        with pytest.raises(MediaForbiddenError):
            await service.download_content(_principal(users["stranger"]), media_id)
        await service.delete_asset(owner, media_id)
        assert gateway.deleted == [("private/ciphertext", "raw")]

        legacy = MediaAsset(
            id=uuid4(),
            owner_user_id=owner.user_id,
            cloudinary_public_id="private/legacy-plaintext",
            cloudinary_version=1,
            resource_type="image",
            access_mode="authenticated",
            original_filename="legacy.png",
            mime_type="image/png",
            bytes=10,
            status=MediaStatus.ACTIVE,
            confidentiality=MediaConfidentiality.PRIVATE,
            encryption_status=MediaEncryptionStatus.LEGACY_UNENCRYPTED,
        )
        async with session_factory() as session:
            session.add(legacy)
            await session.commit()
        with pytest.raises(MediaInvalidStateError):
            await service.create_signed_url(owner, legacy.id)

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
            UploadIntent(
                purpose=MediaPurpose.DOSSIER_EVIDENCE,
                filename="invoice.exe.pdf",
                mime_type="application/pdf",
                size=2_048,
            ),
            UploadIntent(
                purpose=MediaPurpose.AVATAR,
                filename="portrait.png",
                mime_type="image/png",
                size=2_048,
                confidentiality=MediaConfidentiality.PUBLIC,
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
                confidentiality=MediaConfidentiality.PUBLIC,
            ),
        )
        assert public_video.parameters["allowed_formats"] == "webm"

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())
