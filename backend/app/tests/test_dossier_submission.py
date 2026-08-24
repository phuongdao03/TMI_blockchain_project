import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
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
from app.modules.dossiers.canonical import canonical_json_bytes, snapshot_sha256
from app.modules.dossiers.errors import (
    DossierDuplicateContentError,
    DossierDuplicateDocumentError,
    DossierForbiddenError,
    DossierInvalidStateError,
    DossierValidationError,
)
from app.modules.dossiers.models import (
    Category,
    DocumentHashAdjudication,
    DocumentHashClaim,
    Dossier,
    DossierEvidence,
    DossierStatus,
    DossierStatusHistory,
    DossierType,
    DossierTypeVersion,
    DossierVersion,
)
from app.modules.dossiers.service import DossierService
from app.modules.dossiers.types import (
    CreateDossier,
    CreateEvidence,
    DossierView,
    EvidenceView,
)
from app.modules.media.models import MediaAsset, MediaStatus
from app.modules.media.provenance import CURRENT_INSPECTION_POLICY_VERSION

CATEGORY_ID = UUID("4d28db19-1507-5a45-a50d-cd0aa83029ec")
NOW = datetime(2026, 7, 31, 8, 0, tzinfo=UTC)


async def _build_service(
    enqueue_similarity_detection: Callable[[UUID], None] | None = None,
) -> tuple[
    DossierService,
    async_sessionmaker[AsyncSession],
    AsyncEngine,
    User,
    MediaAsset,
]:
    engine = create_async_engine("sqlite+aiosqlite://")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    user = User(
        id=UUID("5a5ada41-1cf5-471c-a09a-03ac2ab3fb1d"),
        email="owner@tmigroup.vn",
        password_hash="not-used",
        status=UserStatus.ACTIVE,
    )
    media = MediaAsset(
        id=UUID("846c61be-2f2d-413c-a629-c66be1bc65df"),
        owner_user_id=user.id,
        cloudinary_public_id="evidence/ownership",
        cloudinary_version=1,
        resource_type="raw",
        access_mode="authenticated",
        original_filename="ownership.pdf",
        mime_type="application/pdf",
        bytes=2048,
        sha256="a" * 64,
        hash_algorithm="SHA-256",
        hash_byte_length=2048,
        inspection_policy_version=CURRENT_INSPECTION_POLICY_VERSION,
        hash_storage_version=1,
        hash_computed_at=NOW,
        status=MediaStatus.ACTIVE,
    )
    async with session_factory() as session:
        session.add_all(
            [
                user,
                media,
                Category(
                    id=CATEGORY_ID,
                    code="DIGITAL_INTELLECTUAL_ASSET",
                    name="Tài sản trí tuệ số",
                ),
            ]
        )
        await session.commit()

    generated_ids = iter(
        (
            UUID("17c53b29-35ea-4fb8-8b64-9c9cd8313c4a"),
            UUID("27c53b29-35ea-4fb8-8b64-9c9cd8313c4a"),
            UUID("37c53b29-35ea-4fb8-8b64-9c9cd8313c4a"),
            UUID("47c53b29-35ea-4fb8-8b64-9c9cd8313c4a"),
            UUID("57c53b29-35ea-4fb8-8b64-9c9cd8313c4a"),
            UUID("67c53b29-35ea-4fb8-8b64-9c9cd8313c4a"),
            UUID("77c53b29-35ea-4fb8-8b64-9c9cd8313c4a"),
            UUID("87c53b29-35ea-4fb8-8b64-9c9cd8313c4a"),
        )
    )
    service = DossierService(
        session=session_factory(),
        clock=lambda: NOW,
        uuid_factory=lambda: next(generated_ids),
        enqueue_similarity_detection=enqueue_similarity_detection,
    )
    return service, session_factory, engine, user, media


def _principal(user: User) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=user.id,
        session_id=uuid4(),
        email=user.email,
        roles=("USER",),
    )


async def _draft_with_evidence(
    service: DossierService,
    principal: AuthPrincipal,
    media: MediaAsset,
) -> tuple[DossierView, EvidenceView]:
    dossier = await service.create_dossier(
        principal,
        CreateDossier(
            category_id=CATEGORY_ID,
            title="Tác phẩm số TMI",
            summary="Bản mô tả tác phẩm.",
        ),
    )
    evidence = await service.attach_evidence(
        principal,
        dossier.id,
        CreateEvidence(
            media_asset_id=media.id,
            evidence_type="OWNERSHIP_DOCUMENT",
            title="Giấy xác nhận",
            issued_at=NOW,
        ),
    )
    return dossier, evidence


def test_submit_is_atomic_idempotent_and_locks_canonical_snapshot() -> None:
    async def exercise() -> None:
        service, session_factory, engine, user, media = await _build_service()
        principal = _principal(user)
        dossier, evidence = await _draft_with_evidence(
            service,
            principal,
            media,
        )

        submitted = await service.submit_dossier(
            principal,
            dossier.id,
            idempotency_key="submit-browser-request-1",
        )
        replay = await service.submit_dossier(
            principal,
            dossier.id,
            idempotency_key="submit-browser-request-1",
        )

        assert submitted.dossier.status is DossierStatus.SUBMITTED
        assert submitted.version.version_no == 1
        assert replay.version.id == submitted.version.id
        assert (
            snapshot_sha256(submitted.version.snapshot_json)
            == submitted.version.canonical_hash
        )
        assert submitted.version.canonical_hash == (
            "1e78af4a1c2de118ee9427ccf47e3048089f54b09b288c5d80a9ae7d29f49a71"
        )
        evidences = submitted.version.snapshot_json["evidences"]
        assert isinstance(evidences, list)
        first_evidence = evidences[0]
        assert isinstance(first_evidence, dict)
        assert first_evidence["evidenceRole"] == "OWNERSHIP_DOCUMENT"
        assert first_evidence["accessScope"] == "PRIVATE"
        assert first_evidence["isPublic"] is False
        media_snapshot = first_evidence["media"]
        assert isinstance(media_snapshot, dict)
        assert media_snapshot["hashAlgorithm"] == "SHA-256"
        assert media_snapshot["hashByteLength"] == 2048
        assert (
            media_snapshot["inspectionPolicyVersion"]
            == CURRENT_INSPECTION_POLICY_VERSION
        )
        assert media_snapshot["storageObjectVersion"] == 1
        assert media_snapshot["hashComputedAt"] == "2026-07-31T08:00:00.000000Z"

        async with session_factory() as session:
            dossier_row = await session.get(Dossier, dossier.id)
            evidence_row = await session.get(DossierEvidence, evidence.id)
            version_count = await session.scalar(
                select(func.count()).select_from(DossierVersion)
            )
            history_count = await session.scalar(
                select(func.count()).select_from(DossierStatusHistory)
            )
            assert dossier_row is not None
            assert dossier_row.current_version_no == 1
            assert dossier_row.submitted_at is not None
            assert evidence_row is not None
            assert evidence_row.dossier_version_id == submitted.version.id
            assert version_count == 1
            assert history_count == 1

        versions = await service.list_versions(principal, dossier.id)
        timeline = await service.get_timeline(principal, dossier.id)
        assert len(versions) == 1
        assert versions[0].id == submitted.version.id
        assert versions[0].canonical_hash == submitted.version.canonical_hash
        assert timeline[0].from_status is DossierStatus.DRAFT
        assert timeline[0].to_status is DossierStatus.SUBMITTED

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_submitted_dynamic_dossier_freezes_only_explicit_public_fields() -> None:
    async def exercise() -> None:
        service, session_factory, engine, user, media = await _build_service()
        principal = _principal(user)
        dossier_type_id = uuid4()
        dossier_type_version_id = uuid4()
        async with session_factory() as session:
            async with session.begin():
                session.add(
                    DossierType(
                        id=dossier_type_id,
                        category_id=CATEGORY_ID,
                        code="PUBLIC_FIELD_TEST",
                        name="Public field test",
                    )
                )
                session.add(
                    DossierTypeVersion(
                        id=dossier_type_version_id,
                        dossier_type_id=dossier_type_id,
                        version_no=1,
                        schema_json={
                            "fields": [
                                {
                                    "key": "story",
                                    "label": "Câu chuyện tác phẩm",
                                    "type": "textarea",
                                    "maxLength": 2_000,
                                    "publicVisibility": True,
                                },
                                {
                                    "key": "owner_email",
                                    "label": "Email chủ sở hữu",
                                    "type": "email",
                                },
                            ]
                        },
                    )
                )

        dossier = await service.create_dossier(
            principal,
            CreateDossier(
                category_id=CATEGORY_ID,
                title="Hồ sơ có trường công khai",
                dossier_type_version_id=dossier_type_version_id,
                form_data={
                    "story": "  Câu chuyện được công bố có kiểm soát.  ",
                    "owner_email": "private@example.test",
                },
            ),
        )
        await service.attach_evidence(
            principal,
            dossier.id,
            CreateEvidence(
                media_asset_id=media.id,
                evidence_type="OWNERSHIP_DOCUMENT",
                title="Giấy xác nhận",
                issued_at=NOW,
            ),
        )
        submitted = await service.submit_dossier(
            principal,
            dossier.id,
            idempotency_key="freeze-explicit-public-fields",
        )
        snapshot_dossier = submitted.version.snapshot_json["dossier"]
        assert isinstance(snapshot_dossier, dict)
        dossier_type = snapshot_dossier["dossierType"]
        assert isinstance(dossier_type, dict)
        assert dossier_type["publicFields"] == [
            {
                "key": "story",
                "label": "Câu chuyện tác phẩm",
                "value": "Câu chuyện được công bố có kiểm soát.",
            }
        ]
        assert dossier_type["formData"] == {
            "story": "Câu chuyện được công bố có kiểm soát.",
            "owner_email": "private@example.test",
        }

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_submit_checklist_failure_rolls_back_and_resubmit_creates_version_two() -> None:
    async def exercise() -> None:
        service, session_factory, engine, user, media = await _build_service()
        principal = _principal(user)
        empty = await service.create_dossier(
            principal,
            CreateDossier(category_id=CATEGORY_ID, title="Thiếu chứng cứ"),
        )
        with pytest.raises(DossierValidationError):
            await service.submit_dossier(
                principal,
                empty.id,
                idempotency_key="missing-evidence",
            )
        async with session_factory() as session:
            row = await session.get(Dossier, empty.id)
            assert row is not None
            assert row.status is DossierStatus.DRAFT
            assert row.current_version_no == 0

        dossier, _ = await _draft_with_evidence(service, principal, media)
        first = await service.submit_dossier(
            principal,
            dossier.id,
            idempotency_key="first-submit",
        )
        async with session_factory() as session:
            async with session.begin():
                row = await session.get(Dossier, dossier.id)
                assert row is not None
                row._set_status_from_workflow(DossierStatus.NEEDS_SUPPLEMENT)

        replacement = MediaAsset(
            id=uuid4(),
            owner_user_id=user.id,
            cloudinary_public_id="evidence/supplement",
            cloudinary_version=1,
            resource_type="raw",
            access_mode="authenticated",
            original_filename="supplement.pdf",
            mime_type="application/pdf",
            bytes=4096,
            sha256="b" * 64,
            hash_algorithm="SHA-256",
            hash_byte_length=4096,
            inspection_policy_version=CURRENT_INSPECTION_POLICY_VERSION,
            hash_storage_version=1,
            hash_computed_at=NOW,
            status=MediaStatus.ACTIVE,
        )
        async with session_factory() as session:
            session.add(replacement)
            await session.commit()
        await service.attach_evidence(
            principal,
            dossier.id,
            CreateEvidence(
                media_asset_id=replacement.id,
                evidence_type="SUPPLEMENT",
                title="Tài liệu bổ sung",
            ),
        )
        second = await service.resubmit_dossier(
            principal,
            dossier.id,
            idempotency_key="second-submit",
        )

        assert first.version.version_no == 1
        assert second.version.version_no == 2
        assert first.version.id != second.version.id
        assert len(await service.list_versions(principal, dossier.id)) == 2
        with pytest.raises(DossierInvalidStateError):
            await service.resubmit_dossier(
                principal,
                empty.id,
                idempotency_key="wrong-state",
            )

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_exact_duplicate_content_is_rejected_across_dossiers() -> None:
    async def exercise() -> None:
        service, session_factory, engine, user, media = await _build_service()
        second_user = User(
            id=UUID("7a5ada41-1cf5-471c-a09a-03ac2ab3fb1d"),
            email="second-owner@tmigroup.vn",
            password_hash="not-used",
            status=UserStatus.ACTIVE,
        )
        second_media = MediaAsset(
            id=UUID("946c61be-2f2d-413c-a629-c66be1bc65df"),
            owner_user_id=second_user.id,
            cloudinary_public_id="evidence/ownership-copy",
            cloudinary_version=1,
            resource_type="raw",
            access_mode="authenticated",
            original_filename="ownership.pdf",
            mime_type="application/pdf",
            bytes=media.bytes,
            sha256=media.sha256,
            hash_algorithm="SHA-256",
            hash_byte_length=media.bytes,
            inspection_policy_version=CURRENT_INSPECTION_POLICY_VERSION,
            hash_storage_version=1,
            hash_computed_at=NOW,
            status=MediaStatus.ACTIVE,
        )
        async with session_factory() as session:
            session.add_all([second_user, second_media])
            await session.commit()

        first_principal = _principal(user)
        second_principal = _principal(second_user)
        first, _ = await _draft_with_evidence(service, first_principal, media)
        await service.submit_dossier(
            first_principal,
            first.id,
            idempotency_key="first-owner-submit",
        )
        second, _ = await _draft_with_evidence(
            service,
            second_principal,
            second_media,
        )
        with pytest.raises(DossierDuplicateContentError):
            await service.submit_dossier(
                second_principal,
                second.id,
                idempotency_key="second-owner-submit",
            )

        async with session_factory() as session:
            assert (
                await session.scalar(select(func.count()).select_from(DossierVersion))
                == 1
            )

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_exact_document_collision_requires_privileged_reasoned_override() -> None:
    async def exercise() -> None:
        service, session_factory, engine, user, media = await _build_service()
        second_user = User(
            id=uuid4(),
            email="document-conflict@tmigroup.vn",
            password_hash="not-used",
            status=UserStatus.ACTIVE,
        )
        admin_user = User(
            id=uuid4(),
            email="claim-admin@tmigroup.vn",
            password_hash="not-used",
            status=UserStatus.ACTIVE,
        )
        copied_media = MediaAsset(
            id=uuid4(),
            owner_user_id=second_user.id,
            cloudinary_public_id="evidence/exact-document-copy",
            cloudinary_version=1,
            resource_type="raw",
            access_mode="authenticated",
            original_filename="copy.pdf",
            mime_type="application/pdf",
            bytes=media.bytes,
            sha256=media.sha256,
            hash_algorithm="SHA-256",
            hash_byte_length=media.bytes,
            inspection_policy_version=CURRENT_INSPECTION_POLICY_VERSION,
            hash_storage_version=1,
            hash_computed_at=NOW,
            status=MediaStatus.ACTIVE,
        )
        unique_media = MediaAsset(
            id=uuid4(),
            owner_user_id=second_user.id,
            cloudinary_public_id="evidence/unique-document",
            cloudinary_version=1,
            resource_type="raw",
            access_mode="authenticated",
            original_filename="unique.pdf",
            mime_type="application/pdf",
            bytes=1024,
            sha256="b" * 64,
            hash_algorithm="SHA-256",
            hash_byte_length=1024,
            inspection_policy_version=CURRENT_INSPECTION_POLICY_VERSION,
            hash_storage_version=1,
            hash_computed_at=NOW,
            status=MediaStatus.ACTIVE,
        )
        async with session_factory() as session:
            session.add_all([second_user, admin_user, copied_media, unique_media])
            await session.commit()

        first, _ = await _draft_with_evidence(service, _principal(user), media)
        first_submission = await service.submit_dossier(
            _principal(user),
            first.id,
            idempotency_key="first-document-claim",
        )
        second_principal = _principal(second_user)
        second, _ = await _draft_with_evidence(
            service,
            second_principal,
            copied_media,
        )
        await service.attach_evidence(
            second_principal,
            second.id,
            CreateEvidence(
                media_asset_id=unique_media.id,
                evidence_type="SUPPORTING_DOCUMENT",
                title="Additional evidence",
            ),
        )

        with pytest.raises(DossierDuplicateDocumentError):
            await service.submit_dossier(
                second_principal,
                second.id,
                idempotency_key="cross-owner-document-conflict",
            )

        with pytest.raises(DossierForbiddenError):
            await service.grant_document_hash_override(
                second_principal,
                second.id,
                media_asset_id=copied_media.id,
                reason="Applicant cannot approve their own conflict.",
            )
        admin = AuthPrincipal(
            user_id=admin_user.id,
            session_id=uuid4(),
            email=admin_user.email,
            roles=("SUPER_ADMIN",),
            permissions=("document_claim.override",),
        )
        async with session_factory() as session:
            async with session.begin():
                stale_media = await session.get(MediaAsset, copied_media.id)
                assert stale_media is not None
                stale_media.inspection_policy_version = "legacy-unverified-v1"
        await service.close()
        service = DossierService(session=session_factory(), clock=lambda: NOW)
        with pytest.raises(DossierValidationError, match="trusted provenance"):
            await service.grant_document_hash_override(
                admin,
                second.id,
                media_asset_id=copied_media.id,
                reason="Reviewed ownership evidence and approved authorized reuse.",
            )
        async with session_factory() as session:
            async with session.begin():
                trusted_media = await session.get(MediaAsset, copied_media.id)
                assert trusted_media is not None
                trusted_media.inspection_policy_version = (
                    CURRENT_INSPECTION_POLICY_VERSION
                )
        await service.close()
        service = DossierService(session=session_factory(), clock=lambda: NOW)
        decision = await service.grant_document_hash_override(
            admin,
            second.id,
            media_asset_id=copied_media.id,
            reason="Reviewed ownership evidence and approved authorized reuse.",
        )
        replay = await service.grant_document_hash_override(
            admin,
            second.id,
            media_asset_id=copied_media.id,
            reason="Reviewed ownership evidence and approved authorized reuse.",
        )
        submitted = await service.submit_dossier(
            second_principal,
            second.id,
            idempotency_key="approved-cross-owner-document",
        )

        assert replay.id == decision.id
        assert submitted.dossier.status is DossierStatus.SUBMITTED

        async with session_factory() as session:
            claim_count = await session.scalar(
                select(func.count()).select_from(DocumentHashClaim)
            )
            adjudication_count = await session.scalar(
                select(func.count()).select_from(DocumentHashAdjudication)
            )
            override_audit_count = await session.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(AuditLog.action == "DOCUMENT_HASH_OVERRIDE_GRANTED")
            )
            original_claim = await session.scalar(
                select(DocumentHashClaim).where(
                    DocumentHashClaim.media_asset_id == media.id
                )
            )
            assert claim_count == 3
            assert adjudication_count == 1
            assert override_audit_count == 1
            assert original_claim is not None
            assert original_claim.dossier_id == first.id
            assert original_claim.dossier_version_id == first_submission.version.id

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_submit_rejects_evidence_with_incomplete_hash_provenance() -> None:
    async def exercise() -> None:
        service, session_factory, engine, user, media = await _build_service()
        principal = _principal(user)
        dossier, _ = await _draft_with_evidence(service, principal, media)

        async with session_factory() as session:
            async with session.begin():
                row = await session.get(MediaAsset, media.id)
                assert row is not None
                row.inspection_policy_version = "legacy-unverified-v1"

        with pytest.raises(DossierValidationError, match="trusted provenance"):
            await service.submit_dossier(
                principal,
                dossier.id,
                idempotency_key="legacy-hash-submit",
            )

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_canonical_json_has_stable_utf8_ordering() -> None:
    first = {"z": ["Tiếng Việt", {"b": 2, "a": 1}], "a": True}
    second = {"a": True, "z": ["Tiếng Việt", {"a": 1, "b": 2}]}

    assert canonical_json_bytes(first) == canonical_json_bytes(second)
    assert snapshot_sha256(first) == (
        "7ab179d25482b5d49581e8177dec372b4ca9dbef043948c854edc6032ad146d1"
    )


def test_new_submission_queues_similarity_detection_once() -> None:
    async def exercise() -> None:
        queued: list[UUID] = []
        service, _, engine, user, media = await _build_service(queued.append)
        principal = _principal(user)
        dossier, _ = await _draft_with_evidence(service, principal, media)

        submitted = await service.submit_dossier(
            principal,
            dossier.id,
            idempotency_key="queue-similarity-once",
        )
        await service.submit_dossier(
            principal,
            dossier.id,
            idempotency_key="queue-similarity-once",
        )

        assert queued == [submitted.version.id]
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())
