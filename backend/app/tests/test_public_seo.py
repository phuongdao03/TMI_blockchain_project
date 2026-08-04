import asyncio
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.modules.dossiers.models import Category
from app.modules.public.models import (
    PublicationStatus,
    PublicWork,
    PublicWorkVisibility,
)
from app.modules.public.seo_service import PublicSeoService

NOW = datetime(2026, 7, 31, tzinfo=UTC)


def test_sitemap_is_visibility_safe_and_paginated(tmp_path: Path) -> None:
    async def exercise() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'seo.sqlite3').as_posix()}"
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        category_id = uuid4()
        async with factory() as session:
            async with session.begin():
                session.add(
                    Category(
                        id=category_id,
                        code="SEO",
                        name="SEO & metadata",
                        slug="seo-metadata",
                    )
                )
                for index in range(5):
                    session.add(
                        _work(
                            category_id,
                            slug=f"public-{index}",
                            visibility=PublicWorkVisibility.PUBLIC,
                            status=PublicationStatus.PUBLISHED,
                        )
                    )
                session.add_all(
                    [
                        _work(
                            category_id,
                            slug="unlisted-secret",
                            visibility=PublicWorkVisibility.UNLISTED,
                            status=PublicationStatus.PUBLISHED,
                        ),
                        _work(
                            category_id,
                            slug="suspended-secret",
                            visibility=PublicWorkVisibility.PUBLIC,
                            status=PublicationStatus.SUSPENDED,
                        ),
                        _work(
                            category_id,
                            slug="private-secret",
                            visibility=PublicWorkVisibility.PRIVATE,
                            status=PublicationStatus.PUBLISHED,
                        ),
                    ]
                )
            service = PublicSeoService(session, page_size=2)
            manifest = await service.manifest()
            assert manifest.total == 5
            assert manifest.page_count == 3
            slugs: tuple[str, ...] = ()
            for page in range(1, manifest.page_count + 1):
                slugs += tuple(entry.slug for entry in await service.page(page))
            assert slugs == tuple(f"public-{index}" for index in range(5))
            assert not any("secret" in slug for slug in slugs)

            first = await service.repository.get_by_slug("public-0")
            assert first is not None
            first.slug = "public-renamed"
            await session.commit()
            rebuilt = await service.rebuild()
            assert rebuilt.total == 5
            rebuilt_slugs: tuple[str, ...] = ()
            for page in range(1, rebuilt.page_count + 1):
                rebuilt_slugs += tuple(entry.slug for entry in await service.page(page))
            assert "public-0" not in rebuilt_slugs
            assert "public-renamed" in rebuilt_slugs
        await engine.dispose()

    asyncio.run(exercise())


def _work(
    category_id: UUID,
    *,
    slug: str,
    visibility: PublicWorkVisibility,
    status: PublicationStatus,
) -> PublicWork:
    return PublicWork(
        dossier_id=uuid4(),
        owner_user_id=uuid4(),
        slug=slug,
        title=f"Title <&> {slug}",
        short_description="SEO description",
        category_id=category_id,
        publication_status=status,
        visibility=visibility,
        published_at=NOW,
    )
