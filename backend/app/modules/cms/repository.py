from typing import cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.cms.models import (
    CmsBanner,
    CmsCategory,
    CmsContentStatus,
    CmsPage,
    CmsPost,
    CmsVersion,
)


class CmsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add_post(self, post: CmsPost) -> None:
        self._session.add(post)

    def add_page(self, page: CmsPage) -> None:
        self._session.add(page)

    def add_banner(self, banner: CmsBanner) -> None:
        self._session.add(banner)

    def add_category(self, category: CmsCategory) -> None:
        self._session.add(category)

    def add_version(self, version: CmsVersion) -> None:
        self._session.add(version)

    async def delete_category(self, category: CmsCategory) -> None:
        await self._session.delete(category)

    async def get_post(
        self, post_id: UUID, *, for_update: bool = False
    ) -> CmsPost | None:
        statement = select(CmsPost).where(CmsPost.id == post_id)
        if for_update:
            statement = statement.with_for_update()
        return cast(CmsPost | None, await self._session.scalar(statement))

    async def slug_exists(self, slug: str) -> bool:
        return (
            await self._session.scalar(select(CmsPost.id).where(CmsPost.slug == slug))
        ) is not None

    async def page_slug_exists(self, slug: str) -> bool:
        return (
            await self._session.scalar(select(CmsPage.id).where(CmsPage.slug == slug))
        ) is not None

    async def banner_slug_exists(self, slug: str) -> bool:
        return (
            await self._session.scalar(
                select(CmsBanner.id).where(CmsBanner.slug == slug)
            )
        ) is not None

    async def category_slug_exists(self, slug: str) -> bool:
        return (
            await self._session.scalar(
                select(CmsCategory.id).where(CmsCategory.slug == slug)
            )
        ) is not None

    async def get_page(
        self, item_id: UUID, *, for_update: bool = False
    ) -> CmsPage | None:
        statement = select(CmsPage).where(CmsPage.id == item_id)
        if for_update:
            statement = statement.with_for_update()
        return cast(CmsPage | None, await self._session.scalar(statement))

    async def get_banner(
        self, item_id: UUID, *, for_update: bool = False
    ) -> CmsBanner | None:
        statement = select(CmsBanner).where(CmsBanner.id == item_id)
        if for_update:
            statement = statement.with_for_update()
        return cast(CmsBanner | None, await self._session.scalar(statement))

    async def get_category(self, item_id: UUID) -> CmsCategory | None:
        return cast(
            CmsCategory | None,
            await self._session.scalar(
                select(CmsCategory).where(CmsCategory.id == item_id)
            ),
        )

    async def get_public_post_by_slug(self, slug: str) -> CmsPost | None:
        return cast(
            CmsPost | None,
            await self._session.scalar(
                select(CmsPost).where(
                    CmsPost.slug == slug,
                    CmsPost.status == CmsContentStatus.PUBLISHED,
                )
            ),
        )

    async def list_posts(
        self, *, page: int, page_size: int, status: CmsContentStatus | None = None
    ) -> tuple[tuple[CmsPost, ...], int]:
        filters = [CmsPost.status == status] if status is not None else []
        rows = tuple(
            (
                await self._session.scalars(
                    select(CmsPost)
                    .where(*filters)
                    .order_by(CmsPost.created_at.desc(), CmsPost.id.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).all()
        )
        total = int(
            (
                await self._session.scalar(
                    select(func.count()).select_from(CmsPost).where(*filters)
                )
            )
            or 0
        )
        return rows, total

    async def list_pages(self) -> tuple[CmsPage, ...]:
        return tuple(
            (
                await self._session.scalars(
                    select(CmsPage).order_by(CmsPage.created_at.desc())
                )
            ).all()
        )

    async def list_banners(self) -> tuple[CmsBanner, ...]:
        return tuple(
            (
                await self._session.scalars(
                    select(CmsBanner).order_by(CmsBanner.created_at.desc())
                )
            ).all()
        )

    async def list_categories(self) -> tuple[CmsCategory, ...]:
        return tuple(
            (
                await self._session.scalars(
                    select(CmsCategory).order_by(CmsCategory.name)
                )
            ).all()
        )
