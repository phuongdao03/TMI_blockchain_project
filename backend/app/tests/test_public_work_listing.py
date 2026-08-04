import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.modules.dossiers.models import Category
from app.modules.public.catalog_query_service import (
    PublicCatalogQueryService,
    PublicWorkSort,
)
from app.modules.public.models import (
    DerivativeStatus,
    PublicationStatus,
    PublicMediaKind,
    PublicTag,
    PublicWork,
    PublicWorkMedia,
    PublicWorkTag,
    PublicWorkVisibility,
)


class MemoryCache:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.get_count = 0

    async def get(self, key: str) -> str | None:
        self.get_count += 1
        return self.values.get(key)

    async def set(self, key: str, value: str) -> None:
        self.values[key] = value


NOW = datetime(2026, 7, 31, 8, tzinfo=UTC)


def test_listing_filters_and_never_leaks_non_public_works(tmp_path: Path) -> None:
    async def exercise() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'listing.sqlite3').as_posix()}"
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        category = Category(id=uuid4(), code="ART", name="Art", slug="art")
        inactive_category = Category(
            id=uuid4(), code="HIDDEN", name="Hidden", slug="hidden", is_active=False
        )
        tag = PublicTag(id=uuid4(), name="Modern", slug="modern")
        organization_id = uuid4()
        thumbnail_media_id = uuid4()
        visible = PublicWork(
            id=uuid4(),
            dossier_id=uuid4(),
            owner_user_id=uuid4(),
            organization_id=organization_id,
            slug="visible-work",
            title="Visible 100% work",
            short_description="Safe public description",
            author_display_name="Approved artist",
            category_id=category.id,
            publication_status=PublicationStatus.PUBLISHED,
            visibility=PublicWorkVisibility.PUBLIC,
            published_at=NOW,
            featured_at=NOW - timedelta(days=1),
            featured_until=NOW + timedelta(days=1),
            view_count=10,
            thumbnail_media_id=thumbnail_media_id,
        )
        excluded = [
            PublicWork(
                dossier_id=uuid4(),
                owner_user_id=uuid4(),
                slug=f"excluded-{index}",
                title="Secret work",
                short_description="Must not leak",
                category_id=(inactive_category.id if index == 2 else category.id),
                publication_status=(
                    PublicationStatus.HIDDEN
                    if index == 0
                    else PublicationStatus.PUBLISHED
                ),
                visibility=(
                    PublicWorkVisibility.PUBLIC
                    if index != 1
                    else PublicWorkVisibility.UNLISTED
                ),
                published_at=NOW,
            )
            for index in range(3)
        ]
        async with factory() as session:
            async with session.begin():
                session.add_all([category, inactive_category, tag, visible, *excluded])
                session.add(PublicWorkTag(public_work_id=visible.id, tag_id=tag.id))
                session.add(
                    PublicWorkMedia(
                        public_work_id=visible.id,
                        media_asset_id=thumbnail_media_id,
                        media_kind=PublicMediaKind.IMAGE,
                        sort_order=0,
                        alt_text="Approved artwork preview",
                        derivative_status=DerivativeStatus.READY,
                        derivative_url="https://cdn.example.test/public/work.webp",
                        derivative_mime_type="image/webp",
                    )
                )
            cache = MemoryCache()
            service = PublicCatalogQueryService(
                session,
                cache=cache,
                clock=lambda: NOW,
            )
            rows, total = await service.list_works(
                query=None,
                category_slug="art",
                tag_slug="modern",
                organization_id=organization_id,
                published_from=NOW - timedelta(days=1),
                published_to=NOW + timedelta(days=1),
                sort=PublicWorkSort.NEWEST,
                page=1,
                page_size=20,
            )
            assert total == 1
            assert len(rows) == 1
            assert rows[0].slug == "visible-work"
            assert rows[0].is_featured is True
            assert rows[0].thumbnail_url == (
                "https://cdn.example.test/public/work.webp"
            )
            assert rows[0].thumbnail_alt_text == "Approved artwork preview"
            assert tuple(item.slug for item in rows[0].tags) == ("modern",)
            assert not hasattr(rows[0], "owner_user_id")
            cached_rows, cached_total = await service.list_works(
                query=None,
                category_slug="art",
                tag_slug="modern",
                organization_id=organization_id,
                published_from=NOW - timedelta(days=1),
                published_to=NOW + timedelta(days=1),
                sort=PublicWorkSort.NEWEST,
                page=1,
                page_size=20,
            )
            assert cached_rows == rows
            assert cached_total == total
            assert len(cache.values) == 1

            async with session.begin():
                visible.publication_status = PublicationStatus.HIDDEN
                visible.visibility = PublicWorkVisibility.PRIVATE
            after_hide, after_hide_total = await service.list_works(
                query=None,
                category_slug="art",
                tag_slug="modern",
                organization_id=organization_id,
                published_from=NOW - timedelta(days=1),
                published_to=NOW + timedelta(days=1),
                sort=PublicWorkSort.NEWEST,
                page=1,
                page_size=20,
            )
            assert after_hide == ()
            assert after_hide_total == 0

            fuzzed, fuzzed_total = await service.list_works(
                query="%' OR 1=1 --_",
                category_slug=None,
                tag_slug=None,
                organization_id=None,
                published_from=None,
                published_to=None,
                sort=PublicWorkSort.NEWEST,
                page=1,
                page_size=1,
            )
            assert fuzzed == ()
            assert fuzzed_total == 0
            assert len(cache.values) == 2
        await engine.dispose()

    asyncio.run(exercise())


def test_featured_query_enforces_window_and_public_state(tmp_path: Path) -> None:
    async def exercise() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'featured-list.sqlite3').as_posix()}"
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        category = Category(
            id=uuid4(), code="FEATURED", name="Featured", slug="featured"
        )

        def work(
            slug: str,
            *,
            featured_at: datetime,
            featured_until: datetime | None,
            status: PublicationStatus = PublicationStatus.PUBLISHED,
        ) -> PublicWork:
            return PublicWork(
                dossier_id=uuid4(),
                owner_user_id=uuid4(),
                slug=slug,
                title=slug,
                short_description="Safe public description",
                category_id=category.id,
                publication_status=status,
                visibility=PublicWorkVisibility.PUBLIC,
                published_at=NOW - timedelta(days=1),
                featured_at=featured_at,
                featured_until=featured_until,
            )

        async with factory() as session:
            async with session.begin():
                session.add(category)
                session.add_all(
                    [
                        work(
                            "active-featured",
                            featured_at=NOW,
                            featured_until=NOW + timedelta(seconds=1),
                        ),
                        work(
                            "expired-featured",
                            featured_at=NOW - timedelta(days=1),
                            featured_until=NOW,
                        ),
                        work(
                            "future-featured",
                            featured_at=NOW + timedelta(seconds=1),
                            featured_until=None,
                        ),
                        work(
                            "suspended-featured",
                            featured_at=NOW - timedelta(days=1),
                            featured_until=None,
                            status=PublicationStatus.SUSPENDED,
                        ),
                    ]
                )
            service = PublicCatalogQueryService(session, clock=lambda: NOW)
            rows = await service.list_featured(limit=12)
            assert tuple(row.slug for row in rows) == ("active-featured",)
            assert rows[0].is_featured is True
            assert not hasattr(rows[0], "owner_user_id")
        await engine.dispose()

    asyncio.run(exercise())
