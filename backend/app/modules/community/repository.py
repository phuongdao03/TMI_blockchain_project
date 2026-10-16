import hashlib
import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from sqlalchemy import and_, delete, exists, func, literal, or_, select
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.selectable import Select

from app.modules.auth.models import User, UserStatus
from app.modules.community.errors import CommunityNotFoundError
from app.modules.community.models import (
    CommunityBookmark,
    CommunityCategory,
    CommunityComment,
    CommunityFollow,
    CommunityLike,
    CommunityMemberRestriction,
    CommunityModerationLog,
    CommunityPost,
    CommunityPostMedia,
    CommunityPostStatus,
    CommunityPostTag,
    CommunityProfile,
    CommunityTag,
)
from app.modules.media.models import MediaAsset, MediaConfidentiality, MediaStatus
from app.modules.media.types import (
    AVATAR_IMAGE_MIME_TYPES,
    COMMUNITY_POST_IMAGE_MAX_BYTES,
    COMMUNITY_POST_IMAGE_MAX_COUNT,
    COMMUNITY_POST_IMAGE_MIME_TYPES,
    MediaPurpose,
)
from app.modules.public.models import (
    PublicationStatus,
    PublicWork,
    PublicWorkVisibility,
)


@dataclass(frozen=True, slots=True)
class CommunityPostRow:
    post: CommunityPost
    category: CommunityCategory
    author_username: str | None
    author_display_name: str | None
    author_avatar_url: str | None
    like_count: int
    comment_count: int
    viewer_has_liked: bool
    viewer_has_bookmarked: bool
    related_work_id: UUID | None
    related_work_title: str | None
    related_work_slug: str | None
    tags: tuple[CommunityTag, ...]


CommunityPostTuple = tuple[
    CommunityPost,
    CommunityCategory,
    str | None,
    str | None,
    str | None,
    int,
    int,
    bool,
    bool,
    UUID | None,
    str | None,
    str | None,
]


class CommunityRepository:
    def __init__(
        self,
        session: AsyncSession,
        *,
        image_max_count: int = COMMUNITY_POST_IMAGE_MAX_COUNT,
        image_max_bytes: int = COMMUNITY_POST_IMAGE_MAX_BYTES,
        avatar_max_bytes: int = 5_242_880,
    ) -> None:
        self._session = session
        self._image_max_count = image_max_count
        self._image_max_bytes = image_max_bytes
        self._avatar_max_bytes = avatar_max_bytes

    async def is_member_restricted(self, user_id: UUID, scope: str) -> bool:
        now = datetime.now(UTC)
        return bool(
            await self._session.scalar(
                select(CommunityMemberRestriction.id)
                .where(
                    CommunityMemberRestriction.member_user_id == user_id,
                    CommunityMemberRestriction.scope == scope,
                    CommunityMemberRestriction.starts_at <= now,
                    CommunityMemberRestriction.expires_at > now,
                    CommunityMemberRestriction.revoked_at.is_(None),
                )
                .limit(1)
            )
        )

    async def list_active_categories(self) -> tuple[CommunityCategory, ...]:
        result = await self._session.scalars(
            select(CommunityCategory)
            .where(CommunityCategory.is_active.is_(True))
            .order_by(CommunityCategory.sort_order, CommunityCategory.name)
        )
        return tuple(result.all())

    async def list_active_mention_recipients(
        self, usernames: tuple[str, ...]
    ) -> tuple[UUID, ...]:
        if not usernames:
            return ()
        result = await self._session.scalars(
            select(CommunityProfile.user_id)
            .join(User, User.id == CommunityProfile.user_id)
            .where(
                User.status == UserStatus.ACTIVE,
                func.lower(CommunityProfile.username).in_(usernames),
            )
            .order_by(CommunityProfile.username)
            .limit(20)
        )
        return tuple(result.all())

    async def get_category(
        self, category_id: UUID, *, active_only: bool = False
    ) -> CommunityCategory | None:
        statement = select(CommunityCategory).where(CommunityCategory.id == category_id)
        if active_only:
            statement = statement.where(CommunityCategory.is_active.is_(True))
        return cast(CommunityCategory | None, await self._session.scalar(statement))

    async def list_public_posts(
        self,
        *,
        category_slug: str | None,
        tag_slug: str | None = None,
        related_work_id: UUID | None = None,
        query: str | None = None,
        sort: str = "recent",
        following_user_id: UUID | None = None,
        author_user_id: UUID | None = None,
        viewer_user_id: UUID | None = None,
        offset: int,
        limit: int,
    ) -> tuple[tuple[CommunityPostRow, ...], int]:
        filters = self._public_filters()
        if category_slug is not None:
            filters.append(CommunityCategory.slug == category_slug)
        if tag_slug is not None:
            filters.append(
                exists(
                    select(CommunityPostTag.post_id)
                    .join(CommunityTag, CommunityTag.id == CommunityPostTag.tag_id)
                    .where(
                        CommunityPostTag.post_id == CommunityPost.id,
                        CommunityTag.slug == tag_slug,
                    )
                )
            )
        if related_work_id is not None:
            filters.extend(
                [
                    CommunityPost.related_work_id == related_work_id,
                    exists(
                        select(PublicWork.id).where(
                            PublicWork.id == related_work_id,
                            PublicWork.publication_status
                            == PublicationStatus.PUBLISHED,
                            PublicWork.visibility == PublicWorkVisibility.PUBLIC,
                            PublicWork.published_at.is_not(None),
                            PublicWork.deleted_at.is_(None),
                        )
                    ),
                ]
            )
        if query is not None:
            escaped_query = (
                query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            )
            pattern = f"%{escaped_query}%"
            filters.append(
                or_(
                    CommunityPost.title.ilike(pattern, escape="\\"),
                    CommunityPost.content.ilike(pattern, escape="\\"),
                )
            )
        if following_user_id is not None:
            filters.append(
                exists(
                    select(CommunityFollow.id).where(
                        CommunityFollow.follower_user_id == following_user_id,
                        CommunityFollow.followed_user_id
                        == CommunityPost.author_user_id,
                    )
                )
            )
        if author_user_id is not None:
            filters.append(CommunityPost.author_user_id == author_user_id)
        count_result = await self._session.execute(
            select(func.count(CommunityPost.id))
            .join(
                CommunityCategory,
                CommunityCategory.id == CommunityPost.category_id,
            )
            .join(User, User.id == CommunityPost.author_user_id)
            .where(*filters)
        )
        total = int(count_result.scalar_one() or 0)
        like_count = self._like_count_expression()
        comment_count = self._comment_count_expression()
        ordering = {
            "recent": (CommunityPost.published_at.desc(), CommunityPost.id.desc()),
            "popular": (
                like_count.desc(),
                CommunityPost.published_at.desc(),
                CommunityPost.id.desc(),
            ),
            "discussed": (
                comment_count.desc(),
                CommunityPost.published_at.desc(),
                CommunityPost.id.desc(),
            ),
            "following": (CommunityPost.published_at.desc(), CommunityPost.id.desc()),
        }[sort]
        result = await self._session.execute(
            self._post_rows_statement(viewer_user_id=viewer_user_id)
            .where(*filters)
            .order_by(*ordering)
            .offset(offset)
            .limit(limit)
        )
        return self._rows(result.all()), total

    async def list_owned_posts(
        self,
        user_id: UUID,
        *,
        status: CommunityPostStatus | None,
        offset: int,
        limit: int,
    ) -> tuple[tuple[CommunityPostRow, ...], int]:
        owner_statuses = (
            CommunityPostStatus.DRAFT,
            CommunityPostStatus.PENDING,
            CommunityPostStatus.PUBLISHED,
            CommunityPostStatus.REJECTED,
            CommunityPostStatus.HIDDEN,
        )
        filters: list[ColumnElement[bool]] = [
            CommunityPost.author_user_id == user_id,
            CommunityPost.deleted_at.is_(None),
            CommunityPost.status.in_(owner_statuses),
        ]
        if status is not None:
            filters.append(CommunityPost.status == status)
        count_result = await self._session.execute(
            select(func.count(CommunityPost.id)).where(*filters)
        )
        total = int(count_result.scalar_one() or 0)
        result = await self._session.execute(
            self._post_rows_statement(viewer_user_id=user_id)
            .where(*filters)
            .order_by(CommunityPost.updated_at.desc(), CommunityPost.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return self._rows(result.all()), total

    async def get_owned_post_row(
        self, post_id: UUID, *, user_id: UUID
    ) -> CommunityPostRow | None:
        owner_statuses = (
            CommunityPostStatus.DRAFT,
            CommunityPostStatus.PENDING,
            CommunityPostStatus.PUBLISHED,
            CommunityPostStatus.REJECTED,
            CommunityPostStatus.HIDDEN,
        )
        result = await self._session.execute(
            self._post_rows_statement(viewer_user_id=user_id)
            .where(
                CommunityPost.id == post_id,
                CommunityPost.author_user_id == user_id,
                CommunityPost.deleted_at.is_(None),
                CommunityPost.status.in_(owner_statuses),
            )
            .limit(1)
        )
        rows = self._rows(result.all())
        return rows[0] if rows else None

    async def replace_post_tags(
        self,
        *,
        post_id: UUID,
        labels: list[str],
    ) -> None:
        normalized: dict[str, str] = {}
        for label in labels:
            slug = _tag_slug(label)
            if not slug or slug in normalized:
                raise CommunityNotFoundError()
            normalized[slug] = label

        tags_by_slug: dict[str, CommunityTag] = {}
        if normalized:
            existing = await self._session.scalars(
                select(CommunityTag).where(CommunityTag.slug.in_(normalized))
            )
            tags_by_slug = {tag.slug: tag for tag in existing.all()}
            for slug, label in normalized.items():
                if slug not in tags_by_slug:
                    tag = CommunityTag(name=label, slug=slug)
                    self._session.add(tag)
                    tags_by_slug[slug] = tag
            await self._session.flush()

        await self._session.execute(
            delete(CommunityPostTag).where(CommunityPostTag.post_id == post_id)
        )
        for tag in sorted(
            tags_by_slug.values(),
            key=lambda item: (item.name.casefold(), item.slug),
        ):
            self._session.add(CommunityPostTag(post_id=post_id, tag_id=tag.id))
        await self._session.flush()

    async def get_public_post(
        self, slug: str, *, viewer_user_id: UUID | None = None
    ) -> CommunityPostRow | None:
        result = await self._session.execute(
            self._post_rows_statement(viewer_user_id=viewer_user_id)
            .where(CommunityPost.slug == slug, *self._public_filters())
            .limit(1)
        )
        rows = self._rows(result.all())
        return rows[0] if rows else None

    async def get_public_post_by_id(
        self, post_id: UUID, *, viewer_user_id: UUID | None = None
    ) -> CommunityPostRow | None:
        result = await self._session.execute(
            self._post_rows_statement(viewer_user_id=viewer_user_id)
            .where(CommunityPost.id == post_id, *self._public_filters())
            .limit(1)
        )
        rows = self._rows(result.all())
        return rows[0] if rows else None

    async def get_post(
        self, post_id: UUID, *, for_update: bool = False
    ) -> CommunityPost | None:
        statement = select(CommunityPost).where(CommunityPost.id == post_id)
        if for_update:
            statement = statement.with_for_update()
        return cast(CommunityPost | None, await self._session.scalar(statement))

    async def get_post_row(
        self, post_id: UUID, *, viewer_user_id: UUID | None = None
    ) -> CommunityPostRow | None:
        result = await self._session.execute(
            self._post_rows_statement(viewer_user_id=viewer_user_id)
            .where(CommunityPost.id == post_id)
            .limit(1)
        )
        rows = self._rows(result.all())
        return rows[0] if rows else None

    async def get_deliverable_community_image(
        self,
        *,
        slug: str,
        media_id: UUID,
        viewer_user_id: UUID | None,
    ) -> MediaAsset | None:
        owner_draft = and_(
            CommunityPost.author_user_id == viewer_user_id,
            CommunityPost.status.in_(
                (
                    CommunityPostStatus.DRAFT,
                    CommunityPostStatus.PENDING,
                    CommunityPostStatus.REJECTED,
                    CommunityPostStatus.HIDDEN,
                )
            ),
            CommunityPost.deleted_at.is_(None),
            CommunityCategory.is_active.is_(True),
            User.status == UserStatus.ACTIVE,
        )
        public_post = and_(*self._public_filters())
        statement = (
            select(MediaAsset)
            .join(
                CommunityPostMedia,
                CommunityPostMedia.media_asset_id == MediaAsset.id,
            )
            .join(CommunityPost, CommunityPost.id == CommunityPostMedia.post_id)
            .join(CommunityCategory, CommunityCategory.id == CommunityPost.category_id)
            .join(User, User.id == CommunityPost.author_user_id)
            .where(
                CommunityPost.slug == slug,
                CommunityPostMedia.media_asset_id == media_id,
                or_(public_post, owner_draft),
                MediaAsset.purpose == MediaPurpose.COMMUNITY_POST.value,
                MediaAsset.status == MediaStatus.ACTIVE,
                MediaAsset.deleted_at.is_(None),
                MediaAsset.inspected_at.is_not(None),
                MediaAsset.mime_type.in_(COMMUNITY_POST_IMAGE_MIME_TYPES),
                MediaAsset.bytes > 0,
                MediaAsset.bytes <= self._image_max_bytes,
                MediaAsset.sha256.is_not(None),
                MediaAsset.access_mode == "authenticated",
                MediaAsset.confidentiality == MediaConfidentiality.PRIVATE,
            )
        )
        if viewer_user_id is None:
            statement = statement.where(
                CommunityPost.status == CommunityPostStatus.PUBLISHED
            )
        return cast(MediaAsset | None, await self._session.scalar(statement.limit(1)))

    async def get_deliverable_community_avatar(
        self,
        media_id: UUID,
    ) -> MediaAsset | None:
        statement = (
            select(MediaAsset)
            .join(
                CommunityProfile,
                CommunityProfile.avatar_media_id == MediaAsset.id,
            )
            .join(User, User.id == CommunityProfile.user_id)
            .where(
                MediaAsset.id == media_id,
                MediaAsset.owner_user_id == CommunityProfile.user_id,
                User.status == UserStatus.ACTIVE,
                MediaAsset.purpose == MediaPurpose.AVATAR.value,
                MediaAsset.status == MediaStatus.ACTIVE,
                MediaAsset.deleted_at.is_(None),
                MediaAsset.inspected_at.is_not(None),
                MediaAsset.mime_type.in_(AVATAR_IMAGE_MIME_TYPES),
                MediaAsset.bytes > 0,
                MediaAsset.bytes <= self._avatar_max_bytes,
                MediaAsset.sha256.is_not(None),
                MediaAsset.access_mode == "authenticated",
                MediaAsset.confidentiality == MediaConfidentiality.PRIVATE,
            )
        )
        return cast(MediaAsset | None, await self._session.scalar(statement.limit(1)))

    async def get_community_profile(self, user_id: UUID) -> CommunityProfile | None:
        return cast(
            CommunityProfile | None,
            await self._session.scalar(
                select(CommunityProfile).where(CommunityProfile.user_id == user_id)
            ),
        )

    def add_community_profile(self, profile: CommunityProfile) -> None:
        self._session.add(profile)

    def add_post(self, post: CommunityPost) -> None:
        self._session.add(post)

    async def replace_post_images(
        self,
        *,
        post_id: UUID,
        media_ids: list[UUID],
        owner_user_id: UUID,
    ) -> None:
        if len(media_ids) > self._image_max_count or len(set(media_ids)) != len(
            media_ids
        ):
            raise CommunityNotFoundError()
        if media_ids:
            result = await self._session.scalars(
                select(MediaAsset).where(
                    MediaAsset.id.in_(media_ids),
                    MediaAsset.owner_user_id == owner_user_id,
                    MediaAsset.purpose == MediaPurpose.COMMUNITY_POST.value,
                    MediaAsset.status == MediaStatus.ACTIVE,
                    MediaAsset.deleted_at.is_(None),
                    MediaAsset.inspected_at.is_not(None),
                    MediaAsset.mime_type.in_(COMMUNITY_POST_IMAGE_MIME_TYPES),
                    MediaAsset.bytes > 0,
                    MediaAsset.bytes <= self._image_max_bytes,
                    MediaAsset.sha256.is_not(None),
                    MediaAsset.access_mode == "authenticated",
                    MediaAsset.confidentiality == MediaConfidentiality.PRIVATE,
                )
            )
            if len(result.all()) != len(media_ids):
                raise CommunityNotFoundError()
            attached_elsewhere = await self._session.scalar(
                select(func.count(CommunityPostMedia.media_asset_id)).where(
                    CommunityPostMedia.media_asset_id.in_(media_ids),
                    CommunityPostMedia.post_id != post_id,
                )
            )
            if attached_elsewhere:
                raise CommunityNotFoundError()
        await self._session.execute(
            delete(CommunityPostMedia).where(CommunityPostMedia.post_id == post_id)
        )
        for index, media_id in enumerate(media_ids):
            self._session.add(
                CommunityPostMedia(
                    post_id=post_id,
                    media_asset_id=media_id,
                    sort_order=index,
                )
            )
        await self._session.flush()

    async def get_public_related_work(self, work_id: UUID) -> PublicWork | None:
        return cast(
            PublicWork | None,
            await self._session.scalar(
                select(PublicWork).where(
                    PublicWork.id == work_id,
                    PublicWork.publication_status == PublicationStatus.PUBLISHED,
                    PublicWork.visibility == PublicWorkVisibility.PUBLIC,
                    PublicWork.published_at.is_not(None),
                    PublicWork.deleted_at.is_(None),
                )
            ),
        )

    def add_moderation_log(self, log: CommunityModerationLog) -> None:
        self._session.add(log)

    @staticmethod
    def _like_count_expression() -> ColumnElement[int]:
        like_user = aliased(User)
        return (
            select(func.count(CommunityLike.id))
            .join(like_user, like_user.id == CommunityLike.user_id)
            .where(
                CommunityLike.post_id == CommunityPost.id,
                like_user.status == UserStatus.ACTIVE,
            )
            .scalar_subquery()
        )

    @staticmethod
    def _comment_count_expression() -> ColumnElement[int]:
        comment_user = aliased(User)
        return (
            select(func.count(CommunityComment.id))
            .join(comment_user, comment_user.id == CommunityComment.author_user_id)
            .where(
                CommunityComment.post_id == CommunityPost.id,
                CommunityComment.deleted_at.is_(None),
                CommunityComment.moderation_hidden_at.is_(None),
                comment_user.status == UserStatus.ACTIVE,
            )
            .scalar_subquery()
        )

    @staticmethod
    def _public_filters() -> list[ColumnElement[bool]]:
        return [
            CommunityPost.status == CommunityPostStatus.PUBLISHED,
            CommunityPost.deleted_at.is_(None),
            CommunityPost.published_at.is_not(None),
            CommunityCategory.is_active.is_(True),
            User.status == UserStatus.ACTIVE,
        ]

    @staticmethod
    def _post_rows_statement(
        *, viewer_user_id: UUID | None = None
    ) -> Select[CommunityPostTuple]:
        like_count = CommunityRepository._like_count_expression()
        comment_count = CommunityRepository._comment_count_expression()
        viewer_has_liked: ColumnElement[bool] = literal(False)
        viewer_has_bookmarked: ColumnElement[bool] = literal(False)
        if viewer_user_id is not None:
            viewer_has_liked = (
                select(CommunityLike.id)
                .where(
                    CommunityLike.post_id == CommunityPost.id,
                    CommunityLike.user_id == viewer_user_id,
                )
                .exists()
            )
            viewer_has_bookmarked = (
                select(CommunityBookmark.id)
                .where(
                    CommunityBookmark.post_id == CommunityPost.id,
                    CommunityBookmark.user_id == viewer_user_id,
                )
                .exists()
            )
        related_work = aliased(PublicWork)
        related_work_is_public = and_(
            related_work.id == CommunityPost.related_work_id,
            related_work.publication_status == PublicationStatus.PUBLISHED,
            related_work.visibility == PublicWorkVisibility.PUBLIC,
            related_work.published_at.is_not(None),
            related_work.deleted_at.is_(None),
        )
        return (
            select(
                CommunityPost,
                CommunityCategory,
                CommunityProfile.username,
                CommunityProfile.display_name,
                CommunityProfile.avatar_url,
                like_count,
                comment_count,
                viewer_has_liked,
                viewer_has_bookmarked,
                related_work.id,
                related_work.title,
                related_work.slug,
            )
            .join(CommunityCategory, CommunityCategory.id == CommunityPost.category_id)
            .join(User, User.id == CommunityPost.author_user_id)
            .outerjoin(
                CommunityProfile,
                CommunityProfile.user_id == CommunityPost.author_user_id,
            )
            .outerjoin(related_work, related_work_is_public)
            .options(
                selectinload(CommunityPost.image_relations).selectinload(
                    CommunityPostMedia.media_asset
                ),
                selectinload(CommunityPost.tag_relations).selectinload(
                    CommunityPostTag.tag
                ),
            )
        )

    @staticmethod
    def _rows(
        rows: Sequence[Row[CommunityPostTuple]],
    ) -> tuple[CommunityPostRow, ...]:
        return tuple(
            CommunityPostRow(
                post,
                category,
                username,
                display_name,
                avatar_url,
                like_count,
                comment_count,
                viewer_has_liked,
                viewer_has_bookmarked,
                related_work_id,
                related_work_title,
                related_work_slug,
                tuple(
                    sorted(
                        (relation.tag for relation in post.tag_relations),
                        key=lambda tag: (tag.name.casefold(), tag.slug),
                    )
                ),
            )
            for (
                post,
                category,
                username,
                display_name,
                avatar_url,
                like_count,
                comment_count,
                viewer_has_liked,
                viewer_has_bookmarked,
                related_work_id,
                related_work_title,
                related_work_slug,
            ) in rows
        )


def _tag_slug(label: str) -> str:
    source = label.replace("đ", "d").replace("Đ", "D")
    normalized = unicodedata.normalize("NFKD", source)
    ascii_label = normalized.encode("ascii", "ignore").decode().lower()
    base = re.sub(r"[^a-z0-9]+", "-", ascii_label).strip("-")
    if not base:
        base = f"tag-{hashlib.sha256(label.encode()).hexdigest()[:8]}"
    if len(base) > 56:
        suffix = hashlib.sha256(label.casefold().encode()).hexdigest()[:6]
        return f"{base[:56].rstrip('-')}-{suffix}"
    return base
