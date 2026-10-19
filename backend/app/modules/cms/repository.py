from typing import cast
from uuid import UUID

from sqlalchemy import String, and_, case, delete, func, or_, select
from sqlalchemy import cast as sql_cast
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.modules.cms.models import (
    CmsBanner,
    CmsCategory,
    CmsContentStatus,
    CmsGuideArticle,
    CmsGuideFeedback,
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

    def add_guide_article(self, article: CmsGuideArticle) -> None:
        self._session.add(article)

    def add_guide_feedback(self, feedback: CmsGuideFeedback) -> None:
        self._session.add(feedback)

    async def delete_category(self, category: CmsCategory) -> None:
        await self._session.delete(category)

    async def delete_guide_article(self, article: CmsGuideArticle) -> None:
        await self._session.delete(article)

    async def delete_guide_versions(self, article_id: UUID) -> None:
        await self._session.execute(
            delete(CmsVersion).where(
                CmsVersion.resource_type == "guide_article",
                CmsVersion.resource_id == article_id,
            )
        )

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

    async def get_guide_article(
        self, item_id: UUID, *, for_update: bool = False
    ) -> CmsGuideArticle | None:
        statement = select(CmsGuideArticle).where(CmsGuideArticle.id == item_id)
        if for_update:
            statement = statement.with_for_update()
        return cast(CmsGuideArticle | None, await self._session.scalar(statement))

    async def get_public_guide_article_by_slug(
        self, slug: str
    ) -> CmsGuideArticle | None:
        return cast(
            CmsGuideArticle | None,
            await self._session.scalar(
                select(CmsGuideArticle).where(
                    CmsGuideArticle.slug == slug,
                    CmsGuideArticle.status == CmsContentStatus.PUBLISHED,
                    sql_cast(CmsGuideArticle.audiences, String).ilike('%"PUBLIC"%'),
                )
            ),
        )

    async def guide_slug_exists(self, slug: str) -> bool:
        return (
            await self._session.scalar(
                select(CmsGuideArticle.id).where(CmsGuideArticle.slug == slug)
            )
        ) is not None

    async def get_accessible_guide_article_by_slug(
        self, slug: str, audiences: tuple[str, ...]
    ) -> CmsGuideArticle | None:
        return cast(
            CmsGuideArticle | None,
            await self._session.scalar(
                select(CmsGuideArticle).where(
                    CmsGuideArticle.slug == slug,
                    CmsGuideArticle.status == CmsContentStatus.PUBLISHED,
                    self._guide_audience_filter(audiences),
                )
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

    async def list_guide_articles(
        self,
        *,
        page: int,
        page_size: int,
        status: CmsContentStatus | None = None,
        audiences: tuple[str, ...] | None = None,
        category: str | None = None,
        query: str | None = None,
    ) -> tuple[tuple[CmsGuideArticle, ...], int]:
        filters = self._guide_filters(
            status=status, audiences=audiences, category=category, query=query
        )
        statement = select(CmsGuideArticle).where(*filters)
        if query:
            query_terms = tuple(query.split())
            all_title_terms = and_(
                *(
                    CmsGuideArticle.search_title.contains(term, autoescape=True)
                    for term in query_terms
                )
            )
            relevance = case(
                (CmsGuideArticle.search_title == query, 0),
                (
                    CmsGuideArticle.search_title.startswith(query, autoescape=True),
                    1,
                ),
                (all_title_terms, 2),
                (
                    CmsGuideArticle.search_summary.contains(query, autoescape=True),
                    3,
                ),
                else_=4,
            )
            statement = statement.order_by(
                relevance, CmsGuideArticle.sort_order, CmsGuideArticle.slug
            )
        else:
            statement = statement.order_by(
                CmsGuideArticle.sort_order, CmsGuideArticle.slug
            )
        rows = tuple(
            (
                await self._session.scalars(
                    statement.offset((page - 1) * page_size).limit(page_size)
                )
            ).all()
        )
        total = int(
            (
                await self._session.scalar(
                    select(func.count()).select_from(CmsGuideArticle).where(*filters)
                )
            )
            or 0
        )
        return rows, total

    async def get_guide_feedback(
        self, article_id: UUID, client_token_hash: str
    ) -> CmsGuideFeedback | None:
        return cast(
            CmsGuideFeedback | None,
            await self._session.scalar(
                select(CmsGuideFeedback).where(
                    CmsGuideFeedback.article_id == article_id,
                    CmsGuideFeedback.client_token_hash == client_token_hash,
                )
            ),
        )

    async def list_guide_feedback(
        self, article_id: UUID, *, page: int, page_size: int
    ) -> tuple[tuple[CmsGuideFeedback, ...], int]:
        criterion = CmsGuideFeedback.article_id == article_id
        rows = tuple(
            (
                await self._session.scalars(
                    select(CmsGuideFeedback)
                    .where(criterion)
                    .order_by(
                        CmsGuideFeedback.created_at.desc(), CmsGuideFeedback.id.desc()
                    )
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).all()
        )
        total = int(
            await self._session.scalar(
                select(func.count()).select_from(CmsGuideFeedback).where(criterion)
            )
            or 0
        )
        return rows, total

    @staticmethod
    def _guide_audience_filter(audiences: tuple[str, ...]) -> ColumnElement[bool]:
        return or_(
            *(
                sql_cast(CmsGuideArticle.audiences, String).ilike(f'%"{audience}"%')
                for audience in audiences
            )
        )

    @classmethod
    def _guide_filters(
        cls,
        *,
        status: CmsContentStatus | None,
        audiences: tuple[str, ...] | None,
        category: str | None,
        query: str | None,
    ) -> list[ColumnElement[bool]]:
        filters: list[ColumnElement[bool]] = []
        if status is not None:
            filters.append(CmsGuideArticle.status == status)
        if audiences is not None:
            filters.append(cls._guide_audience_filter(audiences))
        if category:
            filters.append(CmsGuideArticle.category == category)
        if query:
            terms = tuple(query.split())
            filters.append(
                and_(
                    *(
                        CmsGuideArticle.search_text.contains(term, autoescape=True)
                        for term in terms
                    )
                )
            )
        return filters
