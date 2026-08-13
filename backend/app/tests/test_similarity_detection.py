import asyncio
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.modules.auth.models import User, UserStatus
from app.modules.dossiers.models import Category, Dossier, DossierVersion
from app.modules.media.models import MediaAsset  # noqa: F401
from app.modules.reviews.models import SimilarityReviewCase, SimilaritySignalType
from app.modules.reviews.similarity_detection import SimilarityDetectionService

NOW = datetime(2026, 8, 10, 11, 0, tzinfo=UTC)


def _snapshot(title: str, perceptual_hash: str) -> dict[str, object]:
    return {
        "schemaVersion": 1,
        "dossier": {"title": title},
        "evidences": [
            {
                "media": {
                    "mimeType": "image/jpeg",
                    "perceptualHash": perceptual_hash,
                }
            }
        ],
    }


def test_detection_creates_explainable_text_and_image_cases_only() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        owner = User(
            id=uuid4(),
            email="owner@tmigroup.vn",
            password_hash="unused",
            status=UserStatus.ACTIVE,
        )
        category = Category(id=uuid4(), code="ART", name="Artwork")
        versions: list[DossierVersion] = []
        rows: list[object] = [owner, category]
        candidates = (
            ("Autumn melody", "0000000000000003"),
            ("Industrial identity system", "ffffffffffffffff"),
            ("Autumn melody", "0000000000000000"),
        )
        for index, (title, perceptual_hash) in enumerate(candidates):
            dossier = Dossier(
                id=uuid4(),
                code=f"DOS-{index}",
                owner_user_id=owner.id,
                category_id=category.id,
                title=title,
            )
            version = DossierVersion(
                id=uuid4(),
                dossier_id=dossier.id,
                version_no=1,
                snapshot_json=_snapshot(title, perceptual_hash),
                canonical_hash=f"{index + 1}" * 64,
                submitted_by=owner.id,
                submitted_at=NOW,
            )
            versions.append(version)
            rows.extend((dossier, version))
        async with sessions() as session:
            session.add_all(rows)
            await session.commit()

        service = SimilarityDetectionService(session=sessions())
        await service.detect(versions[2].id)
        await service.detect(versions[2].id)

        async with sessions() as session:
            cases = tuple((await session.scalars(select(SimilarityReviewCase))).all())
        assert len(cases) == 2
        assert {case.signal_type for case in cases} == {
            SimilaritySignalType.TEXT,
            SimilaritySignalType.IMAGE,
        }
        assert all(
            versions[1].id
            not in {
                case.left_dossier_version_id,
                case.right_dossier_version_id,
            }
            for case in cases
        )
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())
