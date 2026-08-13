import asyncio
import hashlib
from base64 import b64decode
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.modules.audit.models import AuditLog
from app.modules.auth.models import User, UserStatus
from app.modules.media.encryption import DocumentEncryptionKeyring
from app.modules.media.errors import MediaProviderUnavailableError
from app.modules.media.gateway import ProviderAssetMetadata, StoredEncryptedAsset
from app.modules.media.inspection import (
    InspectionRejectedError,
    InspectionUnavailableError,
    MalwareScanResult,
    MediaInspectionPolicy,
    MediaInspectionService,
)
from app.modules.media.models import (
    MediaAsset,
    MediaConfidentiality,
    MediaEncryptionStatus,
    MediaStatus,
)
from app.modules.media.provenance import CURRENT_INSPECTION_POLICY_VERSION

NOW = datetime(2026, 8, 10, 9, 0, tzinfo=UTC)
PNG = b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAoAAAAICAIAAABPmPnhAAAAG0lEQVR4nGNkYGAQ"
    "YeDChVgYJLkYGHCioSsNAHzyBJef8jPiAAAAAElFTkSuQmCC"
)
SAFE_PDF = b"%PDF-1.7\n1 0 obj<</Type/Catalog>>endobj\n%%EOF\n"


class RecordingContentGateway:
    def __init__(self, content: bytes) -> None:
        self.content = content
        self.version = 1
        self.encrypted_uploads: list[tuple[str, bytes]] = []
        self.deleted: list[tuple[str, str]] = []
        self.fail_delete_once = False

    async def download_asset(
        self,
        *,
        public_id: str,
        resource_type: str,
        file_format: str,
        max_bytes: int,
    ) -> bytes:
        for encrypted_public_id, encrypted_content in self.encrypted_uploads:
            if encrypted_public_id == public_id:
                return encrypted_content
        if len(self.content) > max_bytes:
            raise InspectionRejectedError("SIZE_LIMIT_EXCEEDED")
        return self.content

    async def get_asset_metadata(
        self,
        *,
        public_id: str,
        resource_type: str,
    ) -> ProviderAssetMetadata:
        return ProviderAssetMetadata(
            public_id=public_id,
            version=self.version,
            resource_type=resource_type,
            delivery_type="authenticated",
            file_format="png",
            bytes=len(self.content),
        )

    async def upload_encrypted_asset(
        self,
        *,
        public_id: str,
        content: bytes,
    ) -> StoredEncryptedAsset:
        self.encrypted_uploads.append((public_id, content))
        return StoredEncryptedAsset(
            public_id=public_id,
            version=9,
            bytes=len(content),
        )

    async def delete_asset(self, *, public_id: str, resource_type: str) -> None:
        if self.fail_delete_once:
            self.fail_delete_once = False
            raise MediaProviderUnavailableError()
        self.deleted.append((public_id, resource_type))


class StubScanner:
    def __init__(self, result: MalwareScanResult | Exception) -> None:
        self.result = result

    async def scan(self, content: bytes) -> MalwareScanResult:
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def test_content_policy_rejects_mime_spoof_and_active_or_malformed_pdf() -> None:
    policy = MediaInspectionPolicy()

    with pytest.raises(InspectionRejectedError, match="MAGIC_BYTES_MISMATCH"):
        policy.validate("portrait.png", "image/png", SAFE_PDF)
    with pytest.raises(InspectionRejectedError, match="PDF_ACTIVE_CONTENT"):
        policy.validate(
            "evidence.pdf",
            "application/pdf",
            b"%PDF-1.7\n<</OpenAction 2 0 R>>\n%%EOF",
        )
    with pytest.raises(InspectionRejectedError, match="PDF_MALFORMED"):
        policy.validate("evidence.pdf", "application/pdf", b"%PDF-1.7\n")


def test_inspection_activates_only_clean_media_and_uses_server_hash() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        owner = User(
            id=uuid4(),
            email="owner@tmigroup.vn",
            password_hash="not-used",
            status=UserStatus.ACTIVE,
        )
        media = MediaAsset(
            id=uuid4(),
            owner_user_id=owner.id,
            cloudinary_public_id="private/clean-image",
            cloudinary_version=1,
            resource_type="image",
            access_mode="authenticated",
            original_filename="portrait.png",
            mime_type="image/png",
            bytes=len(PNG),
            status=MediaStatus.QUARANTINED,
        )
        async with sessions() as session:
            session.add_all((owner, media))
            await session.commit()
        async with sessions() as session:
            service = MediaInspectionService(
                session=session,
                gateway=RecordingContentGateway(PNG),
                scanner=StubScanner(MalwareScanResult.clean()),
                max_attempts=3,
                clock=lambda: NOW,
            )
            await service.inspect(media.id)
        async with sessions() as session:
            stored = await session.get(MediaAsset, media.id)
            assert stored is not None
            assert stored.status is MediaStatus.ACTIVE
            assert stored.sha256 == (
                "c6bafdaaa55a1027a9c2a50af22eb72b662aa5b0f36480286c18ded678df4e1b"
            )
            audit_row = await session.scalar(
                select(AuditLog).where(AuditLog.action == "media.inspected")
            )
            assert audit_row is not None
            assert audit_row.actor_service == "media-inspection-worker"
            assert audit_row.resource_id == str(media.id)
            assert audit_row.after_json == {
                "status": "ACTIVE",
                "result_code": "CLEAN",
            }
            assert stored.perceptual_hash == "0000000000000000"
            assert stored.inspection_attempts == 1
            assert stored.inspection_reason_code is None
            assert stored.inspected_at is not None
            assert stored.hash_algorithm == "SHA-256"
            assert stored.hash_byte_length == len(PNG)
            assert stored.hash_storage_version == 1
            assert stored.inspection_policy_version == (
                CURRENT_INSPECTION_POLICY_VERSION
            )
            assert stored.hash_computed_at == stored.inspected_at
        await engine.dispose()

    asyncio.run(exercise())


def test_inspection_encrypts_private_original_before_activation() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        owner = User(
            id=uuid4(),
            email="private-owner@tmigroup.vn",
            password_hash="not-used",
            status=UserStatus.ACTIVE,
        )
        media = MediaAsset(
            id=uuid4(),
            owner_user_id=owner.id,
            cloudinary_public_id="private/staging-image",
            cloudinary_version=1,
            resource_type="image",
            access_mode="authenticated",
            original_filename="portrait.png",
            mime_type="image/png",
            bytes=len(PNG),
            confidentiality=MediaConfidentiality.PRIVATE,
            status=MediaStatus.QUARANTINED,
        )
        async with sessions() as session:
            session.add_all((owner, media))
            await session.commit()
        gateway = RecordingContentGateway(PNG)
        keyring = DocumentEncryptionKeyring(
            active_key_id="document-v1",
            keys={"document-v1": b"k" * 32},
        )
        async with sessions() as session:
            service = MediaInspectionService(
                session=session,
                gateway=gateway,
                scanner=StubScanner(MalwareScanResult.clean()),
                max_attempts=3,
                encryption_keyring=keyring,
                private_encryption_required=True,
                clock=lambda: NOW,
            )
            await service.inspect(media.id)

        async with sessions() as session:
            service = MediaInspectionService(
                session=session,
                gateway=gateway,
                scanner=StubScanner(MalwareScanResult.clean()),
                max_attempts=3,
                encryption_keyring=keyring,
                private_encryption_required=True,
                clock=lambda: NOW,
            )
            await service.reverify(media.id)

        async with sessions() as session:
            stored = await session.get(MediaAsset, media.id)
            assert stored is not None
            assert stored.status is MediaStatus.ACTIVE
            assert stored.encryption_status is MediaEncryptionStatus.ENCRYPTED
            assert stored.encryption_algorithm == "AES-256-GCM"
            assert stored.encryption_key_id == "document-v1"
            assert stored.encryption_nonce is not None
            assert stored.encryption_tag is not None
            assert stored.encrypted_object_public_id is not None
            assert stored.encrypted_object_version == 9
        assert len(gateway.encrypted_uploads) == 1
        assert gateway.encrypted_uploads[0][1] != PNG
        assert gateway.deleted == [("private/staging-image", "image")]
        await engine.dispose()

    asyncio.run(exercise())


def test_private_encryption_retry_reuses_ciphertext_after_delete_failure() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        owner = User(
            id=uuid4(),
            email="retry-private@tmigroup.vn",
            password_hash="not-used",
            status=UserStatus.ACTIVE,
        )
        media = MediaAsset(
            id=uuid4(),
            owner_user_id=owner.id,
            cloudinary_public_id="private/retry-staging",
            cloudinary_version=1,
            resource_type="image",
            access_mode="authenticated",
            original_filename="retry.png",
            mime_type="image/png",
            bytes=len(PNG),
            confidentiality=MediaConfidentiality.PRIVATE,
            status=MediaStatus.QUARANTINED,
        )
        async with sessions() as session:
            session.add_all((owner, media))
            await session.commit()
        gateway = RecordingContentGateway(PNG)
        gateway.fail_delete_once = True
        keyring = DocumentEncryptionKeyring(
            active_key_id="document-v1", keys={"document-v1": b"k" * 32}
        )

        async with sessions() as session:
            service = MediaInspectionService(
                session=session,
                gateway=gateway,
                scanner=StubScanner(MalwareScanResult.clean()),
                max_attempts=3,
                encryption_keyring=keyring,
                private_encryption_required=True,
                clock=lambda: NOW,
            )
            with pytest.raises(InspectionUnavailableError):
                await service.inspect(media.id)
        async with sessions() as session:
            stored = await session.get(MediaAsset, media.id)
            assert stored is not None
            assert stored.status is MediaStatus.QUARANTINED
            assert stored.encryption_status is MediaEncryptionStatus.ENCRYPTED

        async with sessions() as session:
            service = MediaInspectionService(
                session=session,
                gateway=gateway,
                scanner=StubScanner(MalwareScanResult.clean()),
                max_attempts=3,
                encryption_keyring=keyring,
                private_encryption_required=True,
                clock=lambda: NOW,
            )
            await service.inspect(media.id)
        async with sessions() as session:
            stored = await session.get(MediaAsset, media.id)
            assert stored is not None
            assert stored.status is MediaStatus.ACTIVE
        assert len(gateway.encrypted_uploads) == 1
        assert gateway.deleted == [("private/retry-staging", "image")]
        await engine.dispose()

    asyncio.run(exercise())


def test_inspection_rolls_back_activation_when_audit_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        owner = User(
            id=uuid4(),
            email="audit-rollback@tmigroup.vn",
            password_hash="not-used",
            status=UserStatus.ACTIVE,
        )
        media = MediaAsset(
            id=uuid4(),
            owner_user_id=owner.id,
            cloudinary_public_id="private/audit-rollback",
            cloudinary_version=1,
            resource_type="image",
            access_mode="authenticated",
            original_filename="portrait.png",
            mime_type="image/png",
            bytes=len(PNG),
            status=MediaStatus.QUARANTINED,
        )
        async with sessions() as session:
            session.add_all((owner, media))
            await session.commit()
        async with sessions() as session:
            service = MediaInspectionService(
                session=session,
                gateway=RecordingContentGateway(PNG),
                scanner=StubScanner(MalwareScanResult.clean()),
                max_attempts=3,
                clock=lambda: NOW,
            )

            def reject_audit(**_: object) -> None:
                raise RuntimeError("audit unavailable")

            monkeypatch.setattr(
                service._audit_service,  # noqa: SLF001
                "record",
                reject_audit,
            )
            with pytest.raises(RuntimeError, match="audit unavailable"):
                await service.inspect(media.id)

        async with sessions() as session:
            stored = await session.get(MediaAsset, media.id)
            assert stored is not None
            assert stored.status is MediaStatus.QUARANTINED
            assert stored.sha256 is None
        await engine.dispose()

    asyncio.run(exercise())


def test_reverification_rejects_changed_bytes_without_overwriting_hash() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        owner = User(
            id=uuid4(),
            email="replacement@tmigroup.vn",
            password_hash="not-used",
            status=UserStatus.ACTIVE,
        )
        media = MediaAsset(
            id=uuid4(),
            owner_user_id=owner.id,
            cloudinary_public_id="private/replaced-image",
            cloudinary_version=1,
            resource_type="image",
            access_mode="authenticated",
            original_filename="portrait.png",
            mime_type="image/png",
            bytes=len(PNG),
            status=MediaStatus.QUARANTINED,
        )
        async with sessions() as session:
            session.add_all((owner, media))
            await session.commit()
        gateway = RecordingContentGateway(PNG)
        async with sessions() as session:
            service = MediaInspectionService(
                session=session,
                gateway=gateway,
                scanner=StubScanner(MalwareScanResult.clean()),
                max_attempts=3,
                clock=lambda: NOW,
            )
            await service.inspect(media.id)
        original_hash = hashlib.sha256(PNG).hexdigest()
        gateway.content = PNG[:-1] + b"x"
        gateway.version = 2
        async with sessions() as session:
            service = MediaInspectionService(
                session=session,
                gateway=gateway,
                scanner=StubScanner(MalwareScanResult.clean()),
                max_attempts=3,
                clock=lambda: NOW,
            )
            await service.reverify(media.id)
        async with sessions() as session:
            stored = await session.get(MediaAsset, media.id)
            assert stored is not None
            assert stored.status is MediaStatus.REJECTED
            assert stored.inspection_reason_code == "HASH_MISMATCH"
            assert stored.sha256 == original_hash
            assert stored.hash_storage_version == 1
        await engine.dispose()

    asyncio.run(exercise())


def test_malware_is_permanently_rejected_and_scanner_outage_stays_quarantined() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        owner = User(
            id=uuid4(),
            email="owner@tmigroup.vn",
            password_hash="not-used",
            status=UserStatus.ACTIVE,
        )
        infected = MediaAsset(
            id=uuid4(),
            owner_user_id=owner.id,
            cloudinary_public_id="private/infected",
            cloudinary_version=1,
            resource_type="image",
            access_mode="authenticated",
            original_filename="infected.png",
            mime_type="image/png",
            bytes=len(PNG),
            status=MediaStatus.QUARANTINED,
        )
        unavailable = MediaAsset(
            id=uuid4(),
            owner_user_id=owner.id,
            cloudinary_public_id="private/unavailable",
            cloudinary_version=1,
            resource_type="image",
            access_mode="authenticated",
            original_filename="retry.png",
            mime_type="image/png",
            bytes=len(PNG),
            status=MediaStatus.QUARANTINED,
        )
        async with sessions() as session:
            session.add_all((owner, infected, unavailable))
            await session.commit()

        async with sessions() as session:
            service = MediaInspectionService(
                session=session,
                gateway=RecordingContentGateway(PNG),
                scanner=StubScanner(MalwareScanResult.infected("EICAR-Test-Signature")),
                max_attempts=3,
                clock=lambda: NOW,
            )
            await service.inspect(infected.id)
        async with sessions() as session:
            service = MediaInspectionService(
                session=session,
                gateway=RecordingContentGateway(PNG),
                scanner=StubScanner(InspectionUnavailableError("SCANNER_UNAVAILABLE")),
                max_attempts=3,
                clock=lambda: NOW,
            )
            with pytest.raises(InspectionUnavailableError):
                await service.inspect(unavailable.id)

        async with sessions() as session:
            infected_stored = await session.get(MediaAsset, infected.id)
            unavailable_stored = await session.get(MediaAsset, unavailable.id)
            assert infected_stored is not None
            assert infected_stored.status is MediaStatus.REJECTED
            assert infected_stored.inspection_reason_code == "MALWARE_DETECTED"
            assert unavailable_stored is not None
            assert unavailable_stored.status is MediaStatus.QUARANTINED
            assert unavailable_stored.inspection_attempts == 1
            assert unavailable_stored.inspection_reason_code == "SCANNER_UNAVAILABLE"
        await engine.dispose()

    asyncio.run(exercise())
