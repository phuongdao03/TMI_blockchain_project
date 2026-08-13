import asyncio
from pathlib import Path
from uuid import uuid4

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
from app.modules.dossiers.document_claims import DocumentHashClaimService
from app.modules.dossiers.errors import DossierDuplicateDocumentError
from app.modules.dossiers.models import (
    Category,
    DocumentHashAnchor,
    DocumentHashClaim,
    Dossier,
    DossierStatus,
    DossierVersion,
)
from app.modules.media.models import MediaAsset, MediaStatus


async def _seed_claim_context(
    database_url: str = "sqlite+aiosqlite://",
) -> tuple[
    AsyncEngine,
    async_sessionmaker[AsyncSession],
    list[Dossier],
    list[DossierVersion],
    list[MediaAsset],
]:
    engine = create_async_engine(database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    first_user = User(
        id=uuid4(),
        email="first-claimant@tmigroup.vn",
        password_hash="unused",
        status=UserStatus.ACTIVE,
    )
    second_user = User(
        id=uuid4(),
        email="second-claimant@tmigroup.vn",
        password_hash="unused",
        status=UserStatus.ACTIVE,
    )
    category = Category(id=uuid4(), code="CLAIM", name="Claim")
    dossiers: list[Dossier] = []
    versions: list[DossierVersion] = []
    media_assets: list[MediaAsset] = []
    for index, owner in enumerate((first_user, first_user, second_user), start=1):
        dossier = Dossier(
            id=uuid4(),
            code=f"TMI-CLAIM-{index}",
            owner_user_id=owner.id,
            category_id=category.id,
            title=f"Claim dossier {index}",
            _status=DossierStatus.DRAFT,
        )
        version = DossierVersion(
            id=uuid4(),
            dossier_id=dossier.id,
            version_no=1,
            snapshot_json={},
            canonical_hash=str(index) * 64,
            submitted_by=owner.id,
        )
        media = MediaAsset(
            id=uuid4(),
            owner_user_id=owner.id,
            cloudinary_public_id=f"claim/evidence-{index}",
            cloudinary_version=1,
            resource_type="raw",
            access_mode="authenticated",
            original_filename=f"evidence-{index}.pdf",
            mime_type="application/pdf",
            bytes=128,
            sha256="a" * 64,
            status=MediaStatus.ACTIVE,
        )
        dossiers.append(dossier)
        versions.append(version)
        media_assets.append(media)

    async with sessions() as session:
        session.add_all(
            [first_user, second_user, category, *dossiers, *versions, *media_assets]
        )
        await session.commit()
    return engine, sessions, dossiers, versions, media_assets


def test_claim_is_idempotent_and_same_scope_can_reuse_exact_bytes() -> None:
    async def exercise() -> None:
        engine, sessions, dossiers, versions, media_assets = await _seed_claim_context()
        async with sessions() as session:
            service = DocumentHashClaimService(session=session)
            async with session.begin():
                first = await service.claim_document(
                    dossier=dossiers[0],
                    version=versions[0],
                    media=media_assets[0],
                )
                replay = await service.claim_document(
                    dossier=dossiers[0],
                    version=versions[0],
                    media=media_assets[0],
                )
                same_scope = await service.claim_document(
                    dossier=dossiers[1],
                    version=versions[1],
                    media=media_assets[1],
                )

            assert replay.id == first.id
            assert same_scope.id != first.id
            assert same_scope.anchor_id == first.anchor_id
            anchor_count = await session.scalar(
                select(func.count()).select_from(DocumentHashAnchor)
            )
            claim_count = await session.scalar(
                select(func.count()).select_from(DocumentHashClaim)
            )
            assert anchor_count == 1
            assert claim_count == 2
        await engine.dispose()

    asyncio.run(exercise())


def test_cross_scope_collision_is_privacy_safe() -> None:
    async def exercise() -> None:
        engine, sessions, dossiers, versions, media_assets = await _seed_claim_context()
        async with sessions() as session:
            service = DocumentHashClaimService(session=session)
            async with session.begin():
                await service.claim_document(
                    dossier=dossiers[0],
                    version=versions[0],
                    media=media_assets[0],
                )

            with pytest.raises(DossierDuplicateDocumentError) as caught:
                async with session.begin():
                    await service.claim_document(
                        dossier=dossiers[2],
                        version=versions[2],
                        media=media_assets[2],
                    )

            public_error = f"{caught.value.code} {caught.value.message}"
            assert "a" * 64 not in public_error
            assert str(dossiers[0].id) not in public_error
            assert str(dossiers[0].owner_user_id) not in public_error
            claim_count = await session.scalar(
                select(func.count()).select_from(DocumentHashClaim)
            )
            assert claim_count == 1
        await engine.dispose()

    asyncio.run(exercise())


def test_concurrent_cross_scope_claims_have_one_deterministic_winner(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        database_path = tmp_path / "concurrent-document-claims.sqlite3"
        engine, sessions, dossiers, versions, media_assets = await _seed_claim_context(
            f"sqlite+aiosqlite:///{database_path.as_posix()}"
        )

        async def attempt(index: int) -> str:
            async with sessions() as session:
                service = DocumentHashClaimService(session=session)
                try:
                    async with session.begin():
                        await service.claim_document(
                            dossier=dossiers[index],
                            version=versions[index],
                            media=media_assets[index],
                        )
                except DossierDuplicateDocumentError:
                    return "conflict"
                return "claimed"

        results = await asyncio.gather(attempt(0), attempt(2))
        assert sorted(results) == ["claimed", "conflict"]
        async with sessions() as session:
            anchor_count = await session.scalar(
                select(func.count()).select_from(DocumentHashAnchor)
            )
            claim_count = await session.scalar(
                select(func.count()).select_from(DocumentHashClaim)
            )
            assert anchor_count == 1
            assert claim_count == 1
        await engine.dispose()

    asyncio.run(exercise())
