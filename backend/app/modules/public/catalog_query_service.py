import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.public.catalog_cache import (
    PublicCatalogCache,
    public_catalog_cache_key,
    public_featured_cache_key,
)
from app.modules.public.catalog_repository import (
    PublicWorkListRow,
    PublicWorkRepository,
)


class PublicWorkSort(StrEnum):
    NEWEST = "newest"
    FEATURED = "featured"
    POPULAR = "popular"


@dataclass(frozen=True, slots=True)
class PublicTagView:
    name: str
    slug: str


@dataclass(frozen=True, slots=True)
class PublicWorkCardView:
    id: UUID
    slug: str
    title: str
    short_description: str
    author_display_name: str | None
    category_name: str
    category_slug: str
    tags: tuple[PublicTagView, ...]
    published_at: datetime
    is_featured: bool
    thumbnail_url: str | None
    thumbnail_alt_text: str | None


class PublicCatalogQueryService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        cache: PublicCatalogCache | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session = session
        self._repository = PublicWorkRepository(session)
        self._cache = cache
        self._clock = clock or (lambda: datetime.now(UTC))

    async def list_works(
        self,
        *,
        query: str | None,
        category_slug: str | None,
        tag_slug: str | None,
        organization_id: UUID | None,
        published_from: datetime | None,
        published_to: datetime | None,
        sort: PublicWorkSort,
        page: int,
        page_size: int,
    ) -> tuple[tuple[PublicWorkCardView, ...], int]:
        cache = self._cache if sort is not PublicWorkSort.FEATURED else None
        cache_key = public_catalog_cache_key(
            {
                "query": query.strip() if query else None,
                "category": category_slug,
                "tag": tag_slug,
                "organization": str(organization_id) if organization_id else None,
                "published_from": (
                    published_from.isoformat() if published_from else None
                ),
                "published_to": published_to.isoformat() if published_to else None,
                "sort": sort.value,
                "page": page,
                "page_size": page_size,
            }
        )
        if cache is not None:
            cached = await cache.get(cache_key)
            if cached is not None:
                try:
                    cached_result = self._deserialize(cached)
                except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                    cached_result = None
                if cached_result is not None:
                    async with self._session.begin():
                        safe = await self._repository.all_work_ids_are_public(
                            tuple(view.id for view in cached_result[0])
                        )
                    if safe:
                        return cached_result
        now = self._clock().astimezone(UTC)
        async with self._session.begin():
            rows, total = await self._repository.list_public_works(
                query=query.strip() if query else None,
                category_slug=category_slug,
                tag_slug=tag_slug,
                organization_id=organization_id,
                published_from=published_from,
                published_to=published_to,
                sort=sort.value,
                offset=(page - 1) * page_size,
                limit=page_size,
                now=now,
            )
        result = (self._to_views(rows, now), total)
        if cache is not None:
            await cache.set(cache_key, self._serialize(*result))
        return result

    async def list_featured(self, *, limit: int = 12) -> tuple[PublicWorkCardView, ...]:
        if not 1 <= limit <= 50:
            raise ValueError("limit must be between 1 and 50")
        cache_key = public_featured_cache_key(limit)
        if self._cache is not None:
            cached = await self._cache.get(cache_key)
            cached_result: tuple[tuple[PublicWorkCardView, ...], int] | None = None
            if cached is not None:
                try:
                    cached_result = self._deserialize(cached)
                except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                    pass
                if cached_result is not None:
                    views, _ = cached_result
                    async with self._session.begin():
                        safe = await self._repository.all_work_ids_are_public(
                            tuple(view.id for view in views)
                        )
                    if safe:
                        return views
        now = self._clock().astimezone(UTC)
        async with self._session.begin():
            rows = await self._repository.list_featured_public_works(
                now=now,
                limit=limit,
            )
        views = self._to_views(rows, now)
        if self._cache is not None:
            await self._cache.set(cache_key, self._serialize(views, len(views)))
        return views

    def _to_views(
        self,
        rows: tuple[PublicWorkListRow, ...],
        now: datetime,
    ) -> tuple[PublicWorkCardView, ...]:
        views: list[PublicWorkCardView] = []
        for row in rows:
            published_at = row.work.published_at
            category_slug_value = row.category.slug
            if published_at is None or category_slug_value is None:
                continue
            featured_at = self._as_utc(row.work.featured_at)
            featured_until = self._as_utc(row.work.featured_until)
            views.append(
                PublicWorkCardView(
                    id=row.work.id,
                    slug=row.work.slug,
                    title=row.work.title,
                    short_description=row.work.short_description,
                    author_display_name=row.work.author_display_name,
                    category_name=row.category.name,
                    category_slug=category_slug_value,
                    tags=tuple(PublicTagView(tag.name, tag.slug) for tag in row.tags),
                    published_at=published_at,
                    is_featured=(
                        featured_at is not None
                        and featured_at <= now
                        and (featured_until is None or featured_until > now)
                    ),
                    thumbnail_url=row.thumbnail_url,
                    thumbnail_alt_text=row.thumbnail_alt_text,
                )
            )
        return tuple(views)

    @staticmethod
    def _serialize(views: tuple[PublicWorkCardView, ...], total: int) -> str:
        return json.dumps(
            {
                "total": total,
                "items": [
                    {
                        "id": str(view.id),
                        "slug": view.slug,
                        "title": view.title,
                        "short_description": view.short_description,
                        "author_display_name": view.author_display_name,
                        "category_name": view.category_name,
                        "category_slug": view.category_slug,
                        "tags": [
                            {"name": tag.name, "slug": tag.slug} for tag in view.tags
                        ],
                        "published_at": view.published_at.isoformat(),
                        "is_featured": view.is_featured,
                        "thumbnail_url": view.thumbnail_url,
                        "thumbnail_alt_text": view.thumbnail_alt_text,
                    }
                    for view in views
                ],
            },
            separators=(",", ":"),
            sort_keys=True,
        )

    @staticmethod
    def _deserialize(value: str) -> tuple[tuple[PublicWorkCardView, ...], int]:
        payload = json.loads(value)
        views = tuple(
            PublicWorkCardView(
                id=UUID(item["id"]),
                slug=item["slug"],
                title=item["title"],
                short_description=item["short_description"],
                author_display_name=item["author_display_name"],
                category_name=item["category_name"],
                category_slug=item["category_slug"],
                tags=tuple(
                    PublicTagView(tag["name"], tag["slug"]) for tag in item["tags"]
                ),
                published_at=datetime.fromisoformat(item["published_at"]),
                is_featured=item["is_featured"],
                thumbnail_url=item.get("thumbnail_url"),
                thumbnail_alt_text=item.get("thumbnail_alt_text"),
            )
            for item in payload["items"]
        )
        return views, int(payload["total"])

    @staticmethod
    def _as_utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
