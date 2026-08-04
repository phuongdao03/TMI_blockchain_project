import asyncio
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
from app.modules.auth.models import User, UserStatus
from app.modules.auth.session_service import AuthPrincipal
from app.modules.dossiers.canonical import canonical_json_bytes, snapshot_sha256
from app.modules.dossiers.errors import (
    DossierInvalidStateError,
    DossierValidationError,
)
from app.modules.dossiers.models import (
    Category,
    Dossier,
    DossierEvidence,
    DossierStatus,
    DossierStatusHistory,
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

CATEGORY_ID = UUID("4d28db19-1507-5a45-a50d-cd0aa83029ec")
NOW = datetime(2026, 7, 31, 8, 0, tzinfo=UTC)


async def _build_service() -> tuple[
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
        )
    )
    service = DossierService(
        session=session_factory(),
        clock=lambda: NOW,
        uuid_factory=lambda: next(generated_ids),
    )
    return service, session_factory, engine, user, media


def _principal(user: User) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=user.id,
        session_id=uuid4(),
        email=user.email,
        roles=("APPLICANT",),
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
            "62e29fe48a0092c60bd12d44dab91137208a9bd67b1613bfb8abf41cea7c27b1"
        )

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


def test_canonical_json_has_stable_utf8_ordering() -> None:
    first = {"z": ["Tiếng Việt", {"b": 2, "a": 1}], "a": True}
    second = {"a": True, "z": ["Tiếng Việt", {"a": 1, "b": 2}]}

    assert canonical_json_bytes(first) == canonical_json_bytes(second)
    assert snapshot_sha256(first) == (
        "7ab179d25482b5d49581e8177dec372b4ca9dbef043948c854edc6032ad146d1"
    )
