import hashlib
import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from sqlalchemy import and_, case, delete, exists, func, literal, or_, select, update
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.selectable import Select

from app.modules.auth.models import Role, User, UserRole, UserStatus
from app.modules.community.errors import CommunityNotFoundError
from app.modules.community.models import (
    CommunityBookmark,
    CommunityCategory,
    CommunityComment,
    CommunityCommentLike,
    CommunityFollow,
    CommunityLike,
    CommunityMemberRestriction,
    CommunityModerationEvent,
    CommunityModerationLog,
    CommunityPost,
    CommunityPostMedia,
    CommunityPostStatus,
    CommunityPostTag,
    CommunityProfile,
    CommunityReport,
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
from app.modules.notifications.models import Notification
from app.modules.public.models import (
    PublicationStatus,
    PublicWork,
    PublicWorkVisibility,
)
from app.modules.users.models import UserProfile


@dataclass(frozen=True, slots=True)
class CommunityPostRow:
    post: CommunityPost
    category: CommunityCategory
    author_username: str | None
    author_display_name: str | None
    author_avatar_url: str | None
    author_avatar_media_id: UUID | None
    author_is_admin: bool
    author_is_moderator: bool
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
    UUID | None,
    bool,
    bool,
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

    @staticmethod
    def _has_role(user_id: object, role_code: str) -> ColumnElement[bool]:
        return (
            select(UserRole.user_id)
            .join(Role, Role.id == UserRole.role_id)
            .where(UserRole.user_id == user_id, Role.code == role_code)
            .exists()
        )

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

    async def list_owned_active_post_media(
        self,
        post_id: UUID,
        owner_user_id: UUID,
    ) -> tuple[UUID, ...]:
        rows = await self._session.scalars(
            select(MediaAsset.id)
            .join(
                CommunityPostMedia,
                CommunityPostMedia.media_asset_id == MediaAsset.id,
            )
            .where(
                CommunityPostMedia.post_id == post_id,
                MediaAsset.owner_user_id == owner_user_id,
                MediaAsset.purpose == MediaPurpose.COMMUNITY_POST.value,
                MediaAsset.status != MediaStatus.DELETED,
            )
            .order_by(CommunityPostMedia.sort_order)
        )
        return tuple(rows.all())

    async def permanently_delete_post_content(
        self,
        post_id: UUID,
        *,
        owner_deleted_event_id: UUID,
    ) -> None:
        comment_rows = await self._session.scalars(
            select(CommunityComment.id).where(CommunityComment.post_id == post_id)
        )
        comment_ids = tuple(comment_rows.all())

        report_filter = CommunityReport.post_id == post_id
        if comment_ids:
            report_filter = or_(
                report_filter,
                CommunityReport.comment_id.in_(comment_ids),
            )
        report_rows = await self._session.scalars(
            select(CommunityReport.id).where(report_filter)
        )
        report_ids = tuple(report_rows.all())

        event_filter = and_(
            CommunityModerationEvent.target_type == "POST",
            CommunityModerationEvent.target_id == str(post_id),
        )
        if comment_ids:
            event_filter = or_(
                event_filter,
                and_(
                    CommunityModerationEvent.target_type == "COMMENT",
                    CommunityModerationEvent.target_id.in_(
                        [str(comment_id) for comment_id in comment_ids]
                    ),
                ),
            )
        if report_ids:
            event_filter = or_(
                event_filter,
                CommunityModerationEvent.report_id.in_(report_ids),
            )

        related_event_rows = await self._session.scalars(
            select(CommunityModerationEvent.id).where(
                event_filter,
                CommunityModerationEvent.id != owner_deleted_event_id,
            )
        )
        related_event_ids = tuple(related_event_rows.all())
        if related_event_ids:
            await self._session.execute(
                delete(Notification).where(
                    Notification.source_event_id.in_(related_event_ids)
                )
            )
            await self._session.execute(
                delete(CommunityModerationEvent).where(
                    CommunityModerationEvent.id.in_(related_event_ids)
                )
            )

        if report_ids:
            await self._session.execute(
                delete(CommunityReport).where(CommunityReport.id.in_(report_ids))
            )
        if comment_ids:
            await self._session.execute(
                delete(CommunityCommentLike).where(
                    CommunityCommentLike.comment_id.in_(comment_ids)
                )
            )
            await self._session.execute(
                update(CommunityComment)
                .where(CommunityComment.parent_id.in_(comment_ids))
                .values(parent_id=None)
            )
            await self._session.execute(
                delete(CommunityComment).where(CommunityComment.post_id == post_id)
            )

        await self._session.execute(
            delete(CommunityLike).where(CommunityLike.post_id == post_id)
        )
        await self._session.execute(
            delete(CommunityBookmark).where(CommunityBookmark.post_id == post_id)
        )
        await self._session.execute(
            delete(CommunityModerationLog).where(
                CommunityModerationLog.post_id == post_id
            )
        )
        await self._session.execute(
            delete(CommunityPostMedia).where(CommunityPostMedia.post_id == post_id)
        )
        await self._session.execute(
            delete(CommunityPostTag).where(CommunityPostTag.post_id == post_id)
        )
        await self._session.execute(
            delete(CommunityPost).where(CommunityPost.id == post_id)
        )

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
            .join(User, User.id == MediaAsset.owner_user_id)
            .outerjoin(CommunityProfile, CommunityProfile.user_id == User.id)
            .outerjoin(UserProfile, UserProfile.user_id == User.id)
            .where(
                MediaAsset.id == media_id,
                User.status == UserStatus.ACTIVE,
                or_(
                    CommunityProfile.avatar_media_id == MediaAsset.id,
                    UserProfile.avatar_media_id == MediaAsset.id,
                ),
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
        display_name = case(
            (UserProfile.user_id.is_(None), CommunityProfile.display_name),
            else_=UserProfile.display_name,
        )
        legacy_avatar_url = case(
            (UserProfile.user_id.is_(None), CommunityProfile.avatar_url),
            else_=UserProfile.avatar_url,
        )
        return (
            select(
                CommunityPost,
                CommunityCategory,
                CommunityProfile.username,
                display_name,
                legacy_avatar_url,
                UserProfile.avatar_media_id,
                CommunityRepository._has_role(
                    CommunityPost.author_user_id, "SUPER_ADMIN"
                ),
                CommunityRepository._has_role(
                    CommunityPost.author_user_id, "MODERATOR"
                ),
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
            .outerjoin(
                UserProfile,
                UserProfile.user_id == CommunityPost.author_user_id,
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
                avatar_media_id,
                bool(is_admin),
                bool(is_moderator),
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
                avatar_media_id,
                is_admin,
                is_moderator,
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
