import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from html.parser import HTMLParser
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.service import AuditService
from app.modules.auth.authorization import AuthorizationPolicy, PolicyRequirement
from app.modules.auth.session_service import AuthPrincipal
from app.modules.cms.errors import (
    CmsForbiddenError,
    CmsGuideArticleDeleteConflictError,
    CmsGuideArticleInvalidError,
    CmsGuideFeedbackConflictError,
    CmsNotFoundError,
    CmsSlugConflictError,
)
from app.modules.cms.models import (
    GUIDE_AUDIENCES,
    CmsBanner,
    CmsCategory,
    CmsContentStatus,
    CmsGuideArticle,
    CmsGuideFeedback,
    CmsPage,
    CmsPost,
    CmsVersion,
)
from app.modules.cms.repository import CmsRepository
from app.modules.cms.sanitizer import sanitize_rich_text
from app.modules.memberships.cycle import active_membership_cycle
from app.modules.memberships.models import MembershipDiamondApplication

CMS_ROLES = frozenset({"SUPER_ADMIN"})


@dataclass(frozen=True, slots=True)
class CmsPostInput:
    title: str
    slug: str
    excerpt: str | None
    body_html: str
    category_id: UUID | None


@dataclass(frozen=True, slots=True)
class CmsPageInput:
    title: str
    slug: str
    body_html: str


@dataclass(frozen=True, slots=True)
class CmsBannerInput:
    title: str
    slug: str
    image_url: str
    link_url: str | None


@dataclass(frozen=True, slots=True)
class CmsCategoryInput:
    name: str
    slug: str
    description: str | None


@dataclass(frozen=True, slots=True)
class CmsGuideArticleInput:
    title: str
    slug: str
    summary: str
    category: str
    audiences: tuple[str, ...]
    body_html: str
    sort_order: int


class _GuideTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def normalize_guide_text(value: str) -> str:
    parser = _GuideTextParser()
    parser.feed(value)
    parser.close()
    decomposed = unicodedata.normalize("NFKD", " ".join(parser.parts))
    without_marks = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return " ".join(
        without_marks.replace("đ", "d").replace("Đ", "d").casefold().split()
    )


class CmsService:
    def __init__(self, *, session: AsyncSession, audit: AuditService) -> None:
        self._session = session
        self._repository = CmsRepository(session)
        self._audit = audit

    async def create_post(
        self, principal: AuthPrincipal, data: CmsPostInput, *, request_id: str
    ) -> CmsPost:
        self._require_admin(principal)
        try:
            async with self._session.begin():
                if await self._repository.slug_exists(data.slug):
                    raise CmsSlugConflictError()
                post = CmsPost(
                    category_id=data.category_id,
                    title=data.title.strip(),
                    slug=data.slug.strip().lower(),
                    excerpt=data.excerpt.strip() if data.excerpt else None,
                    body_html=sanitize_rich_text(data.body_html),
                    status=CmsContentStatus.DRAFT,
                    version=1,
                    created_by=principal.user_id,
                    updated_by=principal.user_id,
                )
                self._repository.add_post(post)
                await self._session.flush()
                self._snapshot(post, principal.user_id)
                self._audit.record(
                    actor_user_id=principal.user_id,
                    action="cms.post.created",
                    resource_type="cms_post",
                    resource_id=str(post.id),
                    after=self._serialize(post),
                    request_id=request_id,
                )
            return post
        except IntegrityError as exc:
            await self._session.rollback()
            raise CmsSlugConflictError() from exc

    async def publish_post(
        self, principal: AuthPrincipal, post_id: UUID, *, request_id: str
    ) -> CmsPost:
        self._require_admin(principal)
        async with self._session.begin():
            post = await self._repository.get_post(post_id, for_update=True)
            if post is None:
                raise CmsNotFoundError()
            before = self._serialize(post)
            if post.status is not CmsContentStatus.PUBLISHED:
                post.status = CmsContentStatus.PUBLISHED
                post.published_at = datetime.now(UTC)
                post.updated_by = principal.user_id
                post.version += 1
                await self._session.flush()
                self._snapshot(post, principal.user_id)
                self._audit.record(
                    actor_user_id=principal.user_id,
                    action="cms.post.published",
                    resource_type="cms_post",
                    resource_id=str(post.id),
                    before=before,
                    after=self._serialize(post),
                    request_id=request_id,
                )
        return post

    async def list_posts(
        self, principal: AuthPrincipal, *, page: int, page_size: int
    ) -> tuple[tuple[CmsPost, ...], int]:
        self._require_admin(principal)
        async with self._session.begin():
            return await self._repository.list_posts(page=page, page_size=page_size)

    async def list_public_posts(
        self, *, page: int, page_size: int
    ) -> tuple[tuple[CmsPost, ...], int]:
        async with self._session.begin():
            return await self._repository.list_posts(
                page=page, page_size=page_size, status=CmsContentStatus.PUBLISHED
            )

    async def get_public_post(self, slug: str) -> CmsPost:
        async with self._session.begin():
            post = await self._repository.get_public_post_by_slug(slug)
            if post is None:
                raise CmsNotFoundError()
            return post

    async def update_post(
        self,
        principal: AuthPrincipal,
        post_id: UUID,
        data: CmsPostInput,
        *,
        request_id: str,
    ) -> CmsPost:
        self._require_admin(principal)
        try:
            async with self._session.begin():
                post = await self._repository.get_post(post_id, for_update=True)
                if post is None:
                    raise CmsNotFoundError()
                if data.slug != post.slug and await self._repository.slug_exists(
                    data.slug
                ):
                    raise CmsSlugConflictError()
                before = self._serialize(post)
                post.title = data.title.strip()
                post.slug = data.slug.strip().lower()
                post.excerpt = data.excerpt.strip() if data.excerpt else None
                post.body_html = sanitize_rich_text(data.body_html)
                post.category_id = data.category_id
                post.version += 1
                post.updated_by = principal.user_id
                await self._session.flush()
                self._snapshot(post, principal.user_id)
                self._audit.record(
                    actor_user_id=principal.user_id,
                    action="cms.post.updated",
                    resource_type="cms_post",
                    resource_id=str(post.id),
                    before=before,
                    after=self._serialize(post),
                    request_id=request_id,
                )
            return post
        except IntegrityError as exc:
            await self._session.rollback()
            raise CmsSlugConflictError() from exc

    async def set_post_status(
        self,
        principal: AuthPrincipal,
        post_id: UUID,
        new_status: CmsContentStatus,
        *,
        request_id: str,
    ) -> CmsPost:
        if new_status is CmsContentStatus.PUBLISHED:
            return await self.publish_post(principal, post_id, request_id=request_id)
        self._require_admin(principal)
        async with self._session.begin():
            post = await self._repository.get_post(post_id, for_update=True)
            if post is None:
                raise CmsNotFoundError()
            before = self._serialize(post)
            post.status = new_status
            post.published_at = None
            post.version += 1
            post.updated_by = principal.user_id
            await self._session.flush()
            self._snapshot(post, principal.user_id)
            self._audit.record(
                actor_user_id=principal.user_id,
                action=f"cms.post.{new_status.value.lower()}",
                resource_type="cms_post",
                resource_id=str(post.id),
                before=before,
                after=self._serialize(post),
                request_id=request_id,
            )
        return post

    async def create_guide_article(
        self,
        principal: AuthPrincipal,
        data: CmsGuideArticleInput,
        *,
        request_id: str,
    ) -> CmsGuideArticle:
        self._require_admin(principal)
        body_html = sanitize_rich_text(data.body_html)
        audiences = self._validate_guide_audiences(data.audiences)
        if not normalize_guide_text(body_html) or not data.summary.strip():
            raise CmsGuideArticleInvalidError()
        slug = data.slug.strip().lower()
        try:
            async with self._session.begin():
                if await self._repository.guide_slug_exists(slug):
                    raise CmsSlugConflictError()
                article = CmsGuideArticle(
                    title=data.title.strip(),
                    slug=slug,
                    summary=data.summary.strip(),
                    category=data.category.strip().lower(),
                    audiences=list(audiences),
                    body_html=body_html,
                    search_text=normalize_guide_text(
                        f"{data.title} {data.summary} {data.category} {body_html}"
                    ),
                    search_title=normalize_guide_text(data.title),
                    search_summary=normalize_guide_text(data.summary),
                    sort_order=data.sort_order,
                    status=CmsContentStatus.DRAFT,
                    version=1,
                    created_by=principal.user_id,
                    updated_by=principal.user_id,
                )
                self._repository.add_guide_article(article)
                await self._session.flush()
                self._add_snapshot(
                    "guide_article",
                    article.id,
                    article.version,
                    self._serialize_guide_article(article),
                    principal.user_id,
                )
                self._audit.record(
                    actor_user_id=principal.user_id,
                    action="cms.guide_article.created",
                    resource_type="cms_guide_article",
                    resource_id=str(article.id),
                    after=self._serialize_guide_article(article),
                    request_id=request_id,
                )
            return article
        except IntegrityError as exc:
            await self._session.rollback()
            raise CmsSlugConflictError() from exc

    async def update_guide_article(
        self,
        principal: AuthPrincipal,
        article_id: UUID,
        data: CmsGuideArticleInput,
        *,
        request_id: str,
    ) -> CmsGuideArticle:
        self._require_admin(principal)
        body_html = sanitize_rich_text(data.body_html)
        audiences = self._validate_guide_audiences(data.audiences)
        if not normalize_guide_text(body_html) or not data.summary.strip():
            raise CmsGuideArticleInvalidError()
        slug = data.slug.strip().lower()
        try:
            async with self._session.begin():
                article = await self._repository.get_guide_article(
                    article_id, for_update=True
                )
                if article is None:
                    raise CmsNotFoundError()
                if slug != article.slug and await self._repository.guide_slug_exists(
                    slug
                ):
                    raise CmsSlugConflictError()
                before = self._serialize_guide_article(article)
                article.title = data.title.strip()
                article.slug = slug
                article.summary = data.summary.strip()
                article.category = data.category.strip().lower()
                article.audiences = list(audiences)
                article.body_html = body_html
                article.search_text = normalize_guide_text(
                    f"{article.title} {article.summary} {article.category} {body_html}"
                )
                article.search_title = normalize_guide_text(article.title)
                article.search_summary = normalize_guide_text(article.summary)
                article.sort_order = data.sort_order
                article.version += 1
                article.updated_by = principal.user_id
                await self._session.flush()
                after = self._serialize_guide_article(article)
                self._add_snapshot(
                    "guide_article",
                    article.id,
                    article.version,
                    after,
                    principal.user_id,
                )
                self._audit.record(
                    actor_user_id=principal.user_id,
                    action="cms.guide_article.updated",
                    resource_type="cms_guide_article",
                    resource_id=str(article.id),
                    before=before,
                    after=after,
                    request_id=request_id,
                )
            return article
        except IntegrityError as exc:
            await self._session.rollback()
            raise CmsSlugConflictError() from exc

    async def set_guide_article_status(
        self,
        principal: AuthPrincipal,
        article_id: UUID,
        new_status: CmsContentStatus,
        *,
        request_id: str,
    ) -> CmsGuideArticle:
        self._require_admin(principal)
        async with self._session.begin():
            article = await self._repository.get_guide_article(
                article_id, for_update=True
            )
            if article is None:
                raise CmsNotFoundError()
            before = self._serialize_guide_article(article)
            article.status = new_status
            article.published_at = (
                datetime.now(UTC) if new_status is CmsContentStatus.PUBLISHED else None
            )
            article.version += 1
            article.updated_by = principal.user_id
            await self._session.flush()
            after = self._serialize_guide_article(article)
            self._add_snapshot(
                "guide_article",
                article.id,
                article.version,
                after,
                principal.user_id,
            )
            self._audit.record(
                actor_user_id=principal.user_id,
                action=f"cms.guide_article.{new_status.value.lower()}",
                resource_type="cms_guide_article",
                resource_id=str(article.id),
                before=before,
                after=after,
                request_id=request_id,
            )
        return article

    async def delete_guide_article(
        self, principal: AuthPrincipal, article_id: UUID, *, request_id: str
    ) -> None:
        self._require_admin(principal)
        async with self._session.begin():
            article = await self._repository.get_guide_article(
                article_id, for_update=True
            )
            if article is None:
                raise CmsNotFoundError()
            if article.status is CmsContentStatus.PUBLISHED:
                raise CmsGuideArticleDeleteConflictError()
            before = {
                "title": article.title,
                "slug": article.slug,
                "status": article.status.value,
                "version": article.version,
            }
            await self._repository.delete_guide_versions(article.id)
            await self._repository.delete_guide_article(article)
            self._audit.record(
                actor_user_id=principal.user_id,
                action="cms.guide_article.deleted",
                resource_type="cms_guide_article",
                resource_id=str(article.id),
                before=before,
                request_id=request_id,
            )

    async def list_admin_guide_articles(
        self,
        principal: AuthPrincipal,
        *,
        page: int,
        page_size: int,
        status: CmsContentStatus | None = None,
        audience: str | None = None,
        category: str | None = None,
        query: str | None = None,
    ) -> tuple[tuple[CmsGuideArticle, ...], int]:
        self._require_admin(principal)
        normalized_query = normalize_guide_text(query) if query else None
        async with self._session.begin():
            return await self._repository.list_guide_articles(
                page=page,
                page_size=page_size,
                status=status,
                audiences=(audience,) if audience else None,
                category=category.strip().lower() if category else None,
                query=normalized_query,
            )

    async def list_admin_guide_feedback(
        self, principal: AuthPrincipal, article_id: UUID, *, page: int, page_size: int
    ) -> tuple[tuple[CmsGuideFeedback, ...], int]:
        self._require_admin(principal)
        async with self._session.begin():
            article = await self._repository.get_guide_article(article_id)
            if article is None:
                raise CmsNotFoundError()
            return await self._repository.list_guide_feedback(
                article_id, page=page, page_size=page_size
            )

    async def list_public_guide_articles(
        self,
        *,
        page: int,
        page_size: int,
        query: str | None = None,
        category: str | None = None,
    ) -> tuple[tuple[CmsGuideArticle, ...], int]:
        normalized_query = normalize_guide_text(query) if query else None
        async with self._session.begin():
            return await self._repository.list_guide_articles(
                page=page,
                page_size=page_size,
                status=CmsContentStatus.PUBLISHED,
                audiences=("PUBLIC",),
                category=category.strip().lower() if category else None,
                query=normalized_query,
            )

    async def list_accessible_guide_articles(
        self,
        principal: AuthPrincipal,
        *,
        is_employee: bool,
        page: int,
        page_size: int,
        query: str | None = None,
        category: str | None = None,
    ) -> tuple[tuple[CmsGuideArticle, ...], int]:
        normalized_query = normalize_guide_text(query) if query else None
        async with self._session.begin():
            audience_tags = await self._guide_audiences(principal, is_employee)
            return await self._repository.list_guide_articles(
                page=page,
                page_size=page_size,
                status=CmsContentStatus.PUBLISHED,
                audiences=tuple(sorted(audience_tags)),
                category=category.strip().lower() if category else None,
                query=normalized_query,
            )

    async def get_public_guide_article(self, slug: str) -> CmsGuideArticle:
        async with self._session.begin():
            article = await self._repository.get_public_guide_article_by_slug(slug)
            if article is None:
                raise CmsNotFoundError()
            return article

    async def get_accessible_guide_article(
        self, principal: AuthPrincipal, slug: str, *, is_employee: bool
    ) -> CmsGuideArticle:
        async with self._session.begin():
            audience_tags = await self._guide_audiences(principal, is_employee)
            article = await self._repository.get_accessible_guide_article_by_slug(
                slug, tuple(sorted(audience_tags))
            )
            if article is None:
                raise CmsNotFoundError()
            return article

    async def _guide_audiences(
        self, principal: AuthPrincipal, is_employee: bool
    ) -> tuple[str, ...]:
        audience_tags = {"PUBLIC", *principal.roles}
        if is_employee:
            audience_tags.add("EMPLOYEE")

        tier, _ = await active_membership_cycle(
            self._session, principal.user_id
        )
        if tier == "PRESTIGE":
            approved = await self._session.scalar(
                select(MembershipDiamondApplication.id)
                .where(
                    MembershipDiamondApplication.user_id == principal.user_id,
                    MembershipDiamondApplication.status == "APPROVED",
                )
                .limit(1)
            )
            if approved is None:
                tier = "COMPANION"

        tier_audiences = {
            "MEMBER": (),
            "SILVER": ("MEMBERSHIP_SILVER",),
            "COMPANION": ("MEMBERSHIP_SILVER", "MEMBERSHIP_COMPANION"),
            "PRESTIGE": (
                "MEMBERSHIP_SILVER",
                "MEMBERSHIP_COMPANION",
                "MEMBERSHIP_PRESTIGE",
            ),
        }
        audience_tags.update(tier_audiences[tier])
        return tuple(sorted(audience_tags))

    async def record_guide_feedback(
        self,
        slug: str,
        *,
        helpful: bool,
        comment: str | None,
        client_token: str,
    ) -> None:
        token_hash = sha256(client_token.encode("utf-8")).hexdigest()
        normalized_comment = comment.strip()[:500] if comment else None
        try:
            async with self._session.begin():
                article = await self._repository.get_public_guide_article_by_slug(slug)
                if article is None:
                    raise CmsNotFoundError()
                if await self._repository.get_guide_feedback(article.id, token_hash):
                    raise CmsGuideFeedbackConflictError()
                self._repository.add_guide_feedback(
                    CmsGuideFeedback(
                        article_id=article.id,
                        helpful=helpful,
                        comment=normalized_comment or None,
                        client_token_hash=token_hash,
                    )
                )
                await self._session.flush()
        except IntegrityError as exc:
            await self._session.rollback()
            raise CmsGuideFeedbackConflictError() from exc

    @staticmethod
    def _validate_guide_audiences(audiences: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(
            dict.fromkeys(audience.strip().upper() for audience in audiences)
        )
        if (
            not normalized
            or any(audience not in GUIDE_AUDIENCES for audience in normalized)
            or ("PUBLIC" in normalized and len(normalized) != 1)
        ):
            raise CmsGuideArticleInvalidError()
        return normalized

    @staticmethod
    def _serialize_guide_article(article: CmsGuideArticle) -> dict[str, object]:
        return {
            "id": str(article.id),
            "title": article.title,
            "slug": article.slug,
            "summary": article.summary,
            "category": article.category,
            "audiences": article.audiences,
            "body_html": article.body_html,
            "sort_order": article.sort_order,
            "status": article.status.value,
            "version": article.version,
            "published_at": article.published_at.isoformat()
            if article.published_at
            else None,
        }

    async def create_page(
        self, principal: AuthPrincipal, data: CmsPageInput, *, request_id: str
    ) -> CmsPage:
        self._require_admin(principal)
        async with self._session.begin():
            if await self._repository.page_slug_exists(data.slug):
                raise CmsSlugConflictError()
            row = CmsPage(
                title=data.title.strip(),
                slug=data.slug,
                body_html=sanitize_rich_text(data.body_html),
                status=CmsContentStatus.DRAFT,
                version=1,
                created_by=principal.user_id,
                updated_by=principal.user_id,
            )
            self._repository.add_page(row)
            await self._session.flush()
            self._add_snapshot(
                "page", row.id, 1, self._serialize_page(row), principal.user_id
            )
            self._audit.record(
                actor_user_id=principal.user_id,
                action="cms.page.created",
                resource_type="cms_page",
                resource_id=str(row.id),
                after=self._serialize_page(row),
                request_id=request_id,
            )
        return row

    async def create_banner(
        self, principal: AuthPrincipal, data: CmsBannerInput, *, request_id: str
    ) -> CmsBanner:
        self._require_admin(principal)
        async with self._session.begin():
            if await self._repository.banner_slug_exists(data.slug):
                raise CmsSlugConflictError()
            row = CmsBanner(
                title=data.title.strip(),
                slug=data.slug,
                image_url=data.image_url,
                link_url=data.link_url,
                status=CmsContentStatus.DRAFT,
                version=1,
                created_by=principal.user_id,
                updated_by=principal.user_id,
            )
            self._repository.add_banner(row)
            await self._session.flush()
            self._add_snapshot(
                "banner", row.id, 1, self._serialize_banner(row), principal.user_id
            )
            self._audit.record(
                actor_user_id=principal.user_id,
                action="cms.banner.created",
                resource_type="cms_banner",
                resource_id=str(row.id),
                after=self._serialize_banner(row),
                request_id=request_id,
            )
        return row

    async def create_category(
        self, principal: AuthPrincipal, data: CmsCategoryInput, *, request_id: str
    ) -> CmsCategory:
        self._require_admin(principal)
        async with self._session.begin():
            if await self._repository.category_slug_exists(data.slug):
                raise CmsSlugConflictError()
            row = CmsCategory(
                name=data.name.strip(), slug=data.slug, description=data.description
            )
            self._repository.add_category(row)
            await self._session.flush()
            self._audit.record(
                actor_user_id=principal.user_id,
                action="cms.category.created",
                resource_type="cms_category",
                resource_id=str(row.id),
                after={"name": row.name, "slug": row.slug},
                request_id=request_id,
            )
        return row

    async def list_pages(self, principal: AuthPrincipal) -> tuple[CmsPage, ...]:
        self._require_admin(principal)
        async with self._session.begin():
            return await self._repository.list_pages()

    async def list_banners(self, principal: AuthPrincipal) -> tuple[CmsBanner, ...]:
        self._require_admin(principal)
        async with self._session.begin():
            return await self._repository.list_banners()

    async def list_categories(
        self, principal: AuthPrincipal
    ) -> tuple[CmsCategory, ...]:
        self._require_admin(principal)
        async with self._session.begin():
            return await self._repository.list_categories()

    async def update_page(
        self,
        principal: AuthPrincipal,
        item_id: UUID,
        data: CmsPageInput,
        *,
        request_id: str,
    ) -> CmsPage:
        self._require_admin(principal)
        async with self._session.begin():
            row = await self._repository.get_page(item_id, for_update=True)
            if row is None:
                raise CmsNotFoundError()
            if data.slug != row.slug and await self._repository.page_slug_exists(
                data.slug
            ):
                raise CmsSlugConflictError()
            before = self._serialize_page(row)
            row.title = data.title.strip()
            row.slug = data.slug.strip().lower()
            row.body_html = sanitize_rich_text(data.body_html)
            row.version += 1
            row.updated_by = principal.user_id
            await self._session.flush()
            self._add_snapshot(
                "page",
                row.id,
                row.version,
                self._serialize_page(row),
                principal.user_id,
            )
            self._audit.record(
                actor_user_id=principal.user_id,
                action="cms.page.updated",
                resource_type="cms_page",
                resource_id=str(row.id),
                before=before,
                after=self._serialize_page(row),
                request_id=request_id,
            )
        return row

    async def update_banner(
        self,
        principal: AuthPrincipal,
        item_id: UUID,
        data: CmsBannerInput,
        *,
        request_id: str,
    ) -> CmsBanner:
        self._require_admin(principal)
        async with self._session.begin():
            row = await self._repository.get_banner(item_id, for_update=True)
            if row is None:
                raise CmsNotFoundError()
            if data.slug != row.slug and await self._repository.banner_slug_exists(
                data.slug
            ):
                raise CmsSlugConflictError()
            before = self._serialize_banner(row)
            row.title = data.title.strip()
            row.slug = data.slug.strip().lower()
            row.image_url = data.image_url
            row.link_url = data.link_url
            row.version += 1
            row.updated_by = principal.user_id
            await self._session.flush()
            self._add_snapshot(
                "banner",
                row.id,
                row.version,
                self._serialize_banner(row),
                principal.user_id,
            )
            self._audit.record(
                actor_user_id=principal.user_id,
                action="cms.banner.updated",
                resource_type="cms_banner",
                resource_id=str(row.id),
                before=before,
                after=self._serialize_banner(row),
                request_id=request_id,
            )
        return row

    async def update_category(
        self,
        principal: AuthPrincipal,
        item_id: UUID,
        data: CmsCategoryInput,
        *,
        request_id: str,
    ) -> CmsCategory:
        self._require_admin(principal)
        async with self._session.begin():
            row = await self._repository.get_category(item_id)
            if row is None:
                raise CmsNotFoundError()
            if data.slug != row.slug and await self._repository.category_slug_exists(
                data.slug
            ):
                raise CmsSlugConflictError()
            before: dict[str, object] = {
                "name": row.name,
                "slug": row.slug,
                "description": row.description,
            }
            row.name = data.name.strip()
            row.slug = data.slug.strip().lower()
            row.description = data.description
            await self._session.flush()
            after: dict[str, object] = {
                "name": row.name,
                "slug": row.slug,
                "description": row.description,
            }
            self._audit.record(
                actor_user_id=principal.user_id,
                action="cms.category.updated",
                resource_type="cms_category",
                resource_id=str(row.id),
                before=before,
                after=after,
                request_id=request_id,
            )
        return row

    async def publish_page(
        self, principal: AuthPrincipal, item_id: UUID, *, request_id: str
    ) -> CmsPage:
        self._require_admin(principal)
        async with self._session.begin():
            row = await self._repository.get_page(item_id, for_update=True)
            if row is None:
                raise CmsNotFoundError()
            row.status = CmsContentStatus.PUBLISHED
            row.published_at = datetime.now(UTC)
            row.version += 1
            row.updated_by = principal.user_id
            await self._session.flush()
            self._add_snapshot(
                "page",
                row.id,
                row.version,
                self._serialize_page(row),
                principal.user_id,
            )
            self._audit.record(
                actor_user_id=principal.user_id,
                action="cms.page.published",
                resource_type="cms_page",
                resource_id=str(row.id),
                after=self._serialize_page(row),
                request_id=request_id,
            )
        return row

    async def publish_banner(
        self, principal: AuthPrincipal, item_id: UUID, *, request_id: str
    ) -> CmsBanner:
        self._require_admin(principal)
        async with self._session.begin():
            row = await self._repository.get_banner(item_id, for_update=True)
            if row is None:
                raise CmsNotFoundError()
            row.status = CmsContentStatus.PUBLISHED
            row.published_at = datetime.now(UTC)
            row.version += 1
            row.updated_by = principal.user_id
            await self._session.flush()
            self._add_snapshot(
                "banner",
                row.id,
                row.version,
                self._serialize_banner(row),
                principal.user_id,
            )
            self._audit.record(
                actor_user_id=principal.user_id,
                action="cms.banner.published",
                resource_type="cms_banner",
                resource_id=str(row.id),
                after=self._serialize_banner(row),
                request_id=request_id,
            )
        return row

    async def archive_page(
        self, principal: AuthPrincipal, item_id: UUID, *, request_id: str
    ) -> CmsPage:
        self._require_admin(principal)
        async with self._session.begin():
            row = await self._repository.get_page(item_id, for_update=True)
            if row is None:
                raise CmsNotFoundError()
            before = self._serialize_page(row)
            row.status = CmsContentStatus.ARCHIVED
            row.published_at = None
            row.version += 1
            row.updated_by = principal.user_id
            await self._session.flush()
            self._add_snapshot(
                "page",
                row.id,
                row.version,
                self._serialize_page(row),
                principal.user_id,
            )
            self._audit.record(
                actor_user_id=principal.user_id,
                action="cms.page.archived",
                resource_type="cms_page",
                resource_id=str(row.id),
                before=before,
                after=self._serialize_page(row),
                request_id=request_id,
            )
        return row

    async def archive_banner(
        self, principal: AuthPrincipal, item_id: UUID, *, request_id: str
    ) -> CmsBanner:
        self._require_admin(principal)
        async with self._session.begin():
            row = await self._repository.get_banner(item_id, for_update=True)
            if row is None:
                raise CmsNotFoundError()
            before = self._serialize_banner(row)
            row.status = CmsContentStatus.ARCHIVED
            row.published_at = None
            row.version += 1
            row.updated_by = principal.user_id
            await self._session.flush()
            self._add_snapshot(
                "banner",
                row.id,
                row.version,
                self._serialize_banner(row),
                principal.user_id,
            )
            self._audit.record(
                actor_user_id=principal.user_id,
                action="cms.banner.archived",
                resource_type="cms_banner",
                resource_id=str(row.id),
                before=before,
                after=self._serialize_banner(row),
                request_id=request_id,
            )
        return row

    async def delete_category(
        self, principal: AuthPrincipal, item_id: UUID, *, request_id: str
    ) -> None:
        self._require_admin(principal)
        async with self._session.begin():
            row = await self._repository.get_category(item_id)
            if row is None:
                raise CmsNotFoundError()
            before: dict[str, object] = {
                "name": row.name,
                "slug": row.slug,
                "description": row.description,
            }
            await self._repository.delete_category(row)
            self._audit.record(
                actor_user_id=principal.user_id,
                action="cms.category.deleted",
                resource_type="cms_category",
                resource_id=str(row.id),
                before=before,
                request_id=request_id,
            )

    def _add_snapshot(
        self,
        resource_type: str,
        resource_id: UUID,
        version: int,
        snapshot: dict[str, object],
        actor_id: UUID,
    ) -> None:
        self._repository.add_version(
            CmsVersion(
                resource_type=resource_type,
                resource_id=resource_id,
                version_no=version,
                snapshot_json=snapshot,
                created_by=actor_id,
                created_at=datetime.now(UTC),
            )
        )

    @staticmethod
    def _serialize_page(row: CmsPage) -> dict[str, object]:
        return {
            "id": str(row.id),
            "title": row.title,
            "slug": row.slug,
            "body_html": row.body_html,
            "status": row.status.value,
            "version": row.version,
        }

    @staticmethod
    def _serialize_banner(row: CmsBanner) -> dict[str, object]:
        return {
            "id": str(row.id),
            "title": row.title,
            "slug": row.slug,
            "image_url": row.image_url,
            "link_url": row.link_url,
            "status": row.status.value,
            "version": row.version,
        }

    def _snapshot(self, post: CmsPost, actor_id: UUID) -> None:
        self._repository.add_version(
            CmsVersion(
                resource_type="post",
                resource_id=post.id,
                version_no=post.version,
                snapshot_json=self._serialize(post),
                created_by=actor_id,
                created_at=datetime.now(UTC),
            )
        )

    @staticmethod
    def _serialize(post: CmsPost) -> dict[str, object]:
        return {
            "id": str(post.id),
            "title": post.title,
            "slug": post.slug,
            "excerpt": post.excerpt,
            "body_html": post.body_html,
            "status": post.status.value,
            "version": post.version,
        }

    @staticmethod
    def _require_admin(principal: AuthPrincipal) -> None:
        AuthorizationPolicy.require_capability(
            principal,
            PolicyRequirement(permission="cms.manage", compatible_roles=CMS_ROLES),
            CmsForbiddenError,
        )
