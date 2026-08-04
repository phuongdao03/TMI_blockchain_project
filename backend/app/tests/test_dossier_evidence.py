import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

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
from app.modules.dossiers.errors import (
    DossierForbiddenError,
    DossierInvalidStateError,
    DossierValidationError,
)
from app.modules.dossiers.models import (
    Category,
    Dossier,
    DossierEvidence,
    DossierVersion,
)
from app.modules.dossiers.service import DossierService
from app.modules.dossiers.types import (
    CreateDossier,
    CreateEvidence,
    EvidenceChanges,
)
from app.modules.media.models import MediaAsset, MediaStatus

CATEGORY_ID = UUID("4d28db19-1507-5a45-a50d-cd0aa83029ec")
NOW = datetime(2026, 7, 31, 8, 0, tzinfo=UTC)


async def _build_service() -> tuple[
    DossierService,
    async_sessionmaker[AsyncSession],
    AsyncEngine,
    dict[str, User],
    dict[str, MediaAsset],
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

    def asset(
        name: str,
        owner: User,
        status: MediaStatus,
        sha256: str | None,
    ) -> MediaAsset:
        return MediaAsset(
            id=uuid4(),
            owner_user_id=owner.id,
            cloudinary_public_id=f"evidence/{name}",
            cloudinary_version=1,
            resource_type="raw",
            access_mode="authenticated",
            original_filename=f"{name}.pdf",
            mime_type="application/pdf",
            bytes=1024,
            sha256=sha256,
            status=status,
        )

    assets = {
        "active": asset("active", users["owner"], MediaStatus.ACTIVE, "a" * 64),
        "pending": asset("pending", users["owner"], MediaStatus.PENDING, None),
        "foreign": asset(
            "foreign",
            users["stranger"],
            MediaStatus.ACTIVE,
            "b" * 64,
        ),
    }
    async with session_factory() as session:
        session.add_all(
            [
                *users.values(),
                Category(
                    id=CATEGORY_ID,
                    code="DIGITAL_INTELLECTUAL_ASSET",
                    name="Tài sản trí tuệ số",
                ),
                *assets.values(),
            ]
        )
        await session.commit()

    service = DossierService(session=session_factory(), clock=lambda: NOW)
    return service, session_factory, engine, users, assets


def _principal(user: User) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=user.id,
        session_id=uuid4(),
        email=user.email,
        roles=("APPLICANT",),
    )


def test_attach_update_and_remove_active_owned_evidence() -> None:
    async def exercise() -> None:
        service, session_factory, engine, users, assets = await _build_service()
        principal = _principal(users["owner"])
        dossier = await service.create_dossier(
            principal,
            CreateDossier(category_id=CATEGORY_ID, title="Hồ sơ có chứng cứ"),
        )

        evidence = await service.attach_evidence(
            principal,
            dossier.id,
            CreateEvidence(
                media_asset_id=assets["active"].id,
                evidence_type="OWNERSHIP_DOCUMENT",
                title="Giấy xác nhận quyền sở hữu",
                issued_at=NOW,
                display_order=1,
                is_public=False,
            ),
        )
        assert evidence.dossier_version_id is None
        assert evidence.sha256 == "a" * 64

        updated = await service.update_evidence(
            principal,
            dossier.id,
            evidence.id,
            EvidenceChanges(
                title="Giấy xác nhận đã cập nhật",
                display_order=0,
                provided_fields=frozenset({"title", "display_order"}),
            ),
        )
        assert updated.title == "Giấy xác nhận đã cập nhật"
        assert updated.display_order == 0
        detail = await service.get_dossier_detail(principal, dossier.id)
        assert detail.evidences[0].id == evidence.id

        await service.remove_evidence(principal, dossier.id, evidence.id)
        async with session_factory() as session:
            assert await session.get(DossierEvidence, evidence.id) is None

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_evidence_rejects_pending_foreign_media_and_locked_rows() -> None:
    async def exercise() -> None:
        service, session_factory, engine, users, assets = await _build_service()
        principal = _principal(users["owner"])
        dossier = await service.create_dossier(
            principal,
            CreateDossier(category_id=CATEGORY_ID, title="Kiểm tra chứng cứ"),
        )

        with pytest.raises(DossierInvalidStateError):
            await service.attach_evidence(
                principal,
                dossier.id,
                CreateEvidence(
                    media_asset_id=assets["pending"].id,
                    evidence_type="OTHER",
                    title="Tệp chưa hoàn tất",
                ),
            )
        with pytest.raises(DossierForbiddenError):
            await service.attach_evidence(
                principal,
                dossier.id,
                CreateEvidence(
                    media_asset_id=assets["foreign"].id,
                    evidence_type="OTHER",
                    title="Tệp của người khác",
                ),
            )
        with pytest.raises(DossierValidationError):
            await service.attach_evidence(
                principal,
                dossier.id,
                CreateEvidence(
                    media_asset_id=assets["active"].id,
                    evidence_type="invalid type",
                    title="Sai loại",
                ),
            )

        evidence = await service.attach_evidence(
            principal,
            dossier.id,
            CreateEvidence(
                media_asset_id=assets["active"].id,
                evidence_type="OTHER",
                title="Hợp lệ",
            ),
        )
        async with session_factory() as session:
            async with session.begin():
                row = await session.get(DossierEvidence, evidence.id)
                dossier_row = await session.get(Dossier, dossier.id)
                assert row is not None
                assert dossier_row is not None
                version = DossierVersion(
                    dossier_id=dossier.id,
                    version_no=1,
                    snapshot_json={},
                    canonical_hash="c" * 64,
                    submitted_by=users["owner"].id,
                    submitted_at=NOW,
                )
                session.add(version)
                await session.flush()
                row.dossier_version_id = version.id

        with pytest.raises(DossierInvalidStateError):
            await service.update_evidence(
                principal,
                dossier.id,
                evidence.id,
                EvidenceChanges(
                    title="Không được sửa",
                    provided_fields=frozenset({"title"}),
                ),
            )

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())
