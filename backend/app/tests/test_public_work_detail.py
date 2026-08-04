import asyncio
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.modules.dossiers.models import Category
from app.modules.media.models import MediaAsset, MediaStatus
from app.modules.public.detail_service import PublicWorkDetailService
from app.modules.public.models import (
    DerivativeStatus,
    PublicationStatus,
    PublicMediaKind,
    PublicWork,
    PublicWorkMedia,
    PublicWorkSlugHistory,
    PublicWorkVisibility,
)
from app.modules.public.schemas import PublicWorkDetailProjectionData


class MemoryCache:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.values.get(key)

    async def set(self, key: str, value: str) -> None:
        self.values[key] = value


NOW = datetime(2026, 7, 31, tzinfo=UTC)


def test_public_detail_visibility_slug_history_and_allowlist(tmp_path: Path) -> None:
    async def exercise() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'detail.sqlite3').as_posix()}"
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        category_id = uuid4()
        public_id = uuid4()
        media_id = uuid4()
        related_id = uuid4()
        related_media_id = uuid4()
        async with factory() as session:
            async with session.begin():
                session.add(
                    Category(
                        id=category_id,
                        code="DETAIL",
                        name="Detail",
                        slug="detail",
                    )
                )
                session.add_all(
                    [
                        PublicWork(
                            id=public_id,
                            dossier_id=uuid4(),
                            owner_user_id=uuid4(),
                            slug="public-work",
                            title="Public work",
                            short_description="Public description",
                            category_id=category_id,
                            thumbnail_media_id=media_id,
                            publication_status=PublicationStatus.PUBLISHED,
                            visibility=PublicWorkVisibility.PUBLIC,
                            published_at=NOW,
                        ),
                        PublicWork(
                            dossier_id=uuid4(),
                            owner_user_id=uuid4(),
                            slug="suspended-work",
                            title="Suspended work",
                            short_description="Must not leak",
                            category_id=category_id,
                            publication_status=PublicationStatus.SUSPENDED,
                            visibility=PublicWorkVisibility.PUBLIC,
                            published_at=NOW,
                        ),
                        PublicWork(
                            dossier_id=uuid4(),
                            owner_user_id=uuid4(),
                            slug="hidden-work",
                            title="Hidden work",
                            short_description="Must not leak",
                            category_id=category_id,
                            publication_status=PublicationStatus.HIDDEN,
                            visibility=PublicWorkVisibility.PUBLIC,
                            published_at=NOW,
                        ),
                        PublicWork(
                            id=related_id,
                            dossier_id=uuid4(),
                            owner_user_id=uuid4(),
                            slug="related-public-work",
                            title="Related public work",
                            short_description="Related description",
                            category_id=category_id,
                            thumbnail_media_id=related_media_id,
                            publication_status=PublicationStatus.PUBLISHED,
                            visibility=PublicWorkVisibility.PUBLIC,
                            published_at=NOW,
                        ),
                        PublicWork(
                            dossier_id=uuid4(),
                            owner_user_id=uuid4(),
                            slug="unlisted-work",
                            title="Unlisted work",
                            short_description="Direct link description",
                            category_id=category_id,
                            publication_status=PublicationStatus.PUBLISHED,
                            visibility=PublicWorkVisibility.UNLISTED,
                            published_at=NOW,
                        ),
                        PublicWork(
                            dossier_id=uuid4(),
                            owner_user_id=uuid4(),
                            slug="private-work",
                            title="Private work",
                            short_description="Must not leak",
                            category_id=category_id,
                            publication_status=PublicationStatus.PUBLISHED,
                            visibility=PublicWorkVisibility.PRIVATE,
                            published_at=NOW,
                        ),
                    ]
                )
                session.add_all(
                    [
                        MediaAsset(
                            id=media_id,
                            owner_user_id=uuid4(),
                            cloudinary_public_id="private/owner/source-object-key",
                            cloudinary_version=1,
                            resource_type="image",
                            access_mode="authenticated",
                            original_filename="source.png",
                            mime_type="image/png",
                            bytes=1024,
                            width=800,
                            height=600,
                            status=MediaStatus.ACTIVE,
                        ),
                        MediaAsset(
                            id=related_media_id,
                            owner_user_id=uuid4(),
                            cloudinary_public_id="private/owner/related-source",
                            cloudinary_version=1,
                            resource_type="image",
                            access_mode="authenticated",
                            original_filename="related.png",
                            mime_type="image/png",
                            bytes=512,
                            width=640,
                            height=480,
                            status=MediaStatus.ACTIVE,
                        ),
                    ]
                )
                session.add_all(
                    [
                        PublicWorkMedia(
                            public_work_id=public_id,
                            media_asset_id=media_id,
                            media_kind=PublicMediaKind.IMAGE,
                            sort_order=0,
                            alt_text="Public artwork",
                            derivative_status=DerivativeStatus.READY,
                            derivative_url=(
                                "https://res.cloudinary.com/demo/image/upload/"
                                "public/derivatives/safe.webp"
                            ),
                            derivative_public_id="public/derivatives/safe",
                            derivative_mime_type="image/webp",
                            derivative_width=1600,
                            derivative_height=900,
                        ),
                        PublicWorkMedia(
                            public_work_id=related_id,
                            media_asset_id=related_media_id,
                            media_kind=PublicMediaKind.IMAGE,
                            sort_order=0,
                            alt_text="Related artwork",
                            derivative_status=DerivativeStatus.READY,
                            derivative_url=(
                                "https://res.cloudinary.com/demo/image/upload/"
                                "public/derivatives/related.webp"
                            ),
                            derivative_public_id="public/derivatives/related",
                            derivative_mime_type="image/webp",
                            derivative_width=640,
                            derivative_height=480,
                        ),
                    ]
                )
                session.add(
                    PublicWorkSlugHistory(
                        public_work_id=public_id,
                        slug="old-public-work",
                    )
                )
            cache = MemoryCache()
            service = PublicWorkDetailService(session, cache=cache)
            public = await service.get("public-work")
            assert public is not None
            assert public.redirected is False
            assert public.certificate is None
            assert public.proof is None
            assert not hasattr(public, "owner_user_id")
            assert public.media[0].is_thumbnail is True
            assert tuple(item.slug for item in public.related_works) == (
                "related-public-work",
            )
            assert public.related_works[0].thumbnail_url is not None
            assert public.related_works[0].thumbnail_url.endswith("related.webp")
            assert public.related_works[0].thumbnail_alt_text == "Related artwork"
            payload = PublicWorkDetailProjectionData.model_validate(
                public
            ).model_dump_json()
            assert "source-object-key" not in payload
            assert "public/derivatives/safe.webp" in payload
            assert await service.get("public-work") == public
            assert len(cache.values) == 1

            unlisted = await service.get("unlisted-work")
            assert unlisted is not None
            assert unlisted.visibility is PublicWorkVisibility.UNLISTED
            assert await service.get("private-work") is None
            assert await service.get("suspended-work") is None
            assert await service.get("hidden-work") is None

            old = await service.get("old-public-work")
            assert old is not None
            assert old.redirected is True
            assert old.canonical_slug == "public-work"
        await engine.dispose()

    asyncio.run(exercise())
