from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.modules.auth.models import User, UserStatus
from app.modules.community.models import (
    CommunityCategory,
    CommunityComment,
    CommunityCommentLike,
    CommunityFollow,
    CommunityMemberRestriction,
    CommunityModerationEvent,
    CommunityPost,
    CommunityPostStatus,
    CommunityProfile,
    CommunityReport,
    CommunitySettings,
)
from app.modules.community.repository import CommunityPostRow, CommunityRepository


@dataclass(frozen=True, slots=True)
class CommunityReportRow:
    report: CommunityReport
    reporter_username: str | None
    reporter_display_name: str | None
    reporter_avatar_url: str | None
    post: CommunityPost | None
    post_author_username: str | None
    post_author_display_name: str | None
    post_author_avatar_url: str | None
    comment: CommunityComment | None
    comment_post: CommunityPost | None
    comment_author_username: str | None
    comment_author_display_name: str | None
    comment_author_avatar_url: str | None


@dataclass(frozen=True, slots=True)
class CommunityModerationEventRow:
    event: CommunityModerationEvent
    actor_username: str | None
    actor_display_name: str | None
    actor_avatar_url: str | None


@dataclass(frozen=True, slots=True)
class CommunityReportPage:
    items: tuple[CommunityReportRow, ...]
    total: int


@dataclass(frozen=True, slots=True)
class CommunityModerationEventPage:
    items: tuple[CommunityModerationEventRow, ...]
    total: int


@dataclass(frozen=True, slots=True)
class CommunityAdminCommentRow:
    comment: CommunityComment
    post: CommunityPost
    author_username: str | None
    author_display_name: str | None
    author_avatar_url: str | None
    like_count: int


@dataclass(frozen=True, slots=True)
class CommunityAdminMemberRow:
    user: User
    profile: CommunityProfile | None
    published_post_count: int
    comment_count: int
    follower_count: int
    following_count: int
    last_activity_at: datetime | None
    active_restrictions: tuple[CommunityMemberRestriction, ...]


@dataclass(frozen=True, slots=True)
class CommunityAdminMemberPage:
    items: tuple[CommunityAdminMemberRow, ...]
    total: int


@dataclass(frozen=True, slots=True)
class CommunityAdminPostPage:
    items: tuple[CommunityPostRow, ...]
    total: int


@dataclass(frozen=True, slots=True)
class CommunityRestrictionRow:
    restriction: CommunityMemberRestriction
    member_username: str | None
    member_display_name: str | None
    member_avatar_url: str | None
    actor_username: str | None
    actor_display_name: str | None
    actor_avatar_url: str | None
    status: str


@dataclass(frozen=True, slots=True)
class CommunityRestrictionPage:
    items: tuple[CommunityRestrictionRow, ...]
    total: int


class CommunityAdminRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_admin_posts(
        self,
        *,
        query: str | None,
        status: str | None,
        offset: int,
        limit: int,
    ) -> tuple[tuple[CommunityPostRow, ...], int]:
        filters: list[object] = []
        if status is not None:
            filters.append(CommunityPost.status == status)
        if query:
            pattern = _like_pattern(query)
            filters.append(
                or_(
                    CommunityPost.title.ilike(pattern, escape="\\"),
                    CommunityPost.excerpt.ilike(pattern, escape="\\"),
                    CommunityPost.content.ilike(pattern, escape="\\"),
                )
            )
        total = int(
            await self._session.scalar(
                select(func.count(CommunityPost.id))
                .join(
                    CommunityCategory,
                    CommunityCategory.id == CommunityPost.category_id,
                )
                .join(User, User.id == CommunityPost.author_user_id)
                .where(*filters)
            )
            or 0
        )
        rows = await self._session.execute(
            CommunityRepository._post_rows_statement()
            .where(*filters)
            .order_by(CommunityPost.updated_at.desc(), CommunityPost.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return CommunityRepository._rows(rows.all()), total

    async def list_admin_comments(
        self,
        *,
        query: str | None,
        post_id: UUID | None,
        author_username: str | None,
        visibility: str,
        offset: int,
        limit: int,
    ) -> tuple[tuple[CommunityAdminCommentRow, ...], int]:
        author_profile = aliased(CommunityProfile)
        filters: list[object] = []
        if post_id is not None:
            filters.append(CommunityComment.post_id == post_id)
        if author_username is not None:
            filters.append(
                func.lower(author_profile.username) == author_username.lower()
            )
        if visibility == "VISIBLE":
            filters.extend(
                [
                    CommunityComment.deleted_at.is_(None),
                    CommunityComment.moderation_hidden_at.is_(None),
                ]
            )
        elif visibility == "HIDDEN":
            filters.extend(
                [
                    CommunityComment.deleted_at.is_(None),
                    CommunityComment.moderation_hidden_at.is_not(None),
                ]
            )
        elif visibility == "DELETED":
            filters.append(CommunityComment.deleted_at.is_not(None))
        if query:
            filters.append(
                or_(
                    CommunityComment.deleted_at.is_(None),
                    CommunityComment.admin_deleted.is_(True),
                )
            )
            filters.append(
                CommunityComment.content.ilike(_like_pattern(query), escape="\\")
            )
        base = (
            select(
                CommunityComment,
                CommunityPost,
                author_profile.username,
                author_profile.display_name,
                author_profile.avatar_url,
                select(func.count(CommunityCommentLike.id))
                .where(CommunityCommentLike.comment_id == CommunityComment.id)
                .scalar_subquery(),
            )
            .join(CommunityPost, CommunityPost.id == CommunityComment.post_id)
            .outerjoin(
                author_profile,
                author_profile.user_id == CommunityComment.author_user_id,
            )
            .where(*filters)
        )
        total = int(
            await self._session.scalar(
                select(func.count(CommunityComment.id))
                .join(CommunityPost, CommunityPost.id == CommunityComment.post_id)
                .outerjoin(
                    author_profile,
                    author_profile.user_id == CommunityComment.author_user_id,
                )
                .where(*filters)
            )
            or 0
        )
        rows = await self._session.execute(
            base.order_by(
                CommunityComment.created_at.desc(), CommunityComment.id.desc()
            )
            .offset(offset)
            .limit(limit)
        )
        return tuple(CommunityAdminCommentRow(*row) for row in rows.all()), total

    async def get_member(
        self, user_id: UUID
    ) -> tuple[User, CommunityProfile | None] | None:
        row = await self._session.execute(
            select(User, CommunityProfile)
            .outerjoin(CommunityProfile, CommunityProfile.user_id == User.id)
            .where(User.id == user_id, User.status == UserStatus.ACTIVE)
            .limit(1)
        )
        result = row.first()
        return (result[0], result[1]) if result else None

    async def list_admin_members(
        self,
        *,
        query: str | None,
        offset: int,
        limit: int,
    ) -> CommunityAdminMemberPage:
        filters: list[object] = [User.status == UserStatus.ACTIVE]
        if query:
            pattern = _like_pattern(query)
            filters.append(
                or_(
                    CommunityProfile.username.ilike(pattern, escape="\\"),
                    CommunityProfile.display_name.ilike(pattern, escape="\\"),
                )
            )
        published_count = (
            select(func.count(CommunityPost.id))
            .where(
                CommunityPost.author_user_id == User.id,
                CommunityPost.status == CommunityPostStatus.PUBLISHED,
                CommunityPost.deleted_at.is_(None),
            )
            .correlate(User)
            .scalar_subquery()
        )
        comment_count = (
            select(func.count(CommunityComment.id))
            .where(
                CommunityComment.author_user_id == User.id,
                CommunityComment.deleted_at.is_(None),
            )
            .correlate(User)
            .scalar_subquery()
        )
        follower_count = (
            select(func.count(CommunityFollow.id))
            .where(CommunityFollow.followed_user_id == User.id)
            .correlate(User)
            .scalar_subquery()
        )
        following_count = (
            select(func.count(CommunityFollow.id))
            .where(CommunityFollow.follower_user_id == User.id)
            .correlate(User)
            .scalar_subquery()
        )
        latest_post = (
            select(func.max(CommunityPost.updated_at))
            .where(CommunityPost.author_user_id == User.id)
            .correlate(User)
            .scalar_subquery()
        )
        latest_comment = (
            select(func.max(CommunityComment.created_at))
            .where(CommunityComment.author_user_id == User.id)
            .correlate(User)
            .scalar_subquery()
        )
        activity_at = case(
            (latest_post.is_(None), latest_comment),
            (latest_comment.is_(None), latest_post),
            (latest_post >= latest_comment, latest_post),
            else_=latest_comment,
        )
        total = int(
            await self._session.scalar(
                select(func.count(User.id))
                .outerjoin(CommunityProfile, CommunityProfile.user_id == User.id)
                .where(*filters)
            )
            or 0
        )
        rows = await self._session.execute(
            select(User, CommunityProfile, published_count, comment_count,
                   follower_count, following_count, activity_at)
            .outerjoin(CommunityProfile, CommunityProfile.user_id == User.id)
            .where(*filters)
            .order_by(User.created_at.desc(), User.id.desc())
            .offset(offset)
            .limit(limit)
        )
        values = rows.all()
        user_ids = [row[0].id for row in values]
        active_by_user: dict[UUID, list[CommunityMemberRestriction]] = {
            item: [] for item in user_ids
        }
        if user_ids:
            now = datetime.now(UTC)
            restrictions = await self._session.scalars(
                select(CommunityMemberRestriction)
                .where(
                    CommunityMemberRestriction.member_user_id.in_(user_ids),
                    CommunityMemberRestriction.starts_at <= now,
                    CommunityMemberRestriction.expires_at > now,
                    CommunityMemberRestriction.revoked_at.is_(None),
                )
                .order_by(CommunityMemberRestriction.expires_at)
            )
            for restriction in restrictions:
                active_by_user[restriction.member_user_id].append(restriction)
        items = tuple(
            CommunityAdminMemberRow(
                user=row[0], profile=row[1], published_post_count=row[2],
                comment_count=row[3], follower_count=row[4], following_count=row[5],
                last_activity_at=row[6],
                active_restrictions=tuple(active_by_user[row[0].id]),
            )
            for row in values
        )
        return CommunityAdminMemberPage(items, total)

    def add_restriction(self, restriction: CommunityMemberRestriction) -> None:
        self._session.add(restriction)

    async def get_restriction_for_update(
        self, member_id: UUID, restriction_id: UUID
    ) -> CommunityMemberRestriction | None:
        return cast(
            CommunityMemberRestriction | None,
            await self._session.scalar(
                select(CommunityMemberRestriction)
                .where(
                    CommunityMemberRestriction.member_user_id == member_id,
                    CommunityMemberRestriction.id == restriction_id,
                )
                .with_for_update()
            ),
        )

    async def get_restriction_row(
        self, restriction_id: UUID
    ) -> CommunityRestrictionRow | None:
        member = aliased(CommunityProfile)
        actor = aliased(CommunityProfile)
        now = datetime.now(UTC)
        row = await self._session.execute(
            select(
                CommunityMemberRestriction,
                member.username,
                member.display_name,
                member.avatar_url,
                actor.username,
                actor.display_name,
                actor.avatar_url,
            )
            .outerjoin(
                member,
                member.user_id == CommunityMemberRestriction.member_user_id,
            )
            .outerjoin(actor, actor.user_id == CommunityMemberRestriction.actor_user_id)
            .where(CommunityMemberRestriction.id == restriction_id)
            .limit(1)
        )
        values = row.first()
        if values is None:
            return None
        restriction = values[0]
        status = (
            "REVOKED" if restriction.revoked_at is not None
            else "ACTIVE"
            if _as_utc(restriction.starts_at) <= now < _as_utc(restriction.expires_at)
            else "EXPIRED"
        )
        return CommunityRestrictionRow(*values, status)

    async def list_member_restrictions(
        self, member_id: UUID, *, offset: int, limit: int
    ) -> CommunityRestrictionPage:
        member = aliased(CommunityProfile)
        actor = aliased(CommunityProfile)
        total = int(
            await self._session.scalar(
                select(func.count(CommunityMemberRestriction.id)).where(
                    CommunityMemberRestriction.member_user_id == member_id
                )
            )
            or 0
        )
        now = datetime.now(UTC)
        rows = await self._session.execute(
            select(
                CommunityMemberRestriction,
                member.username, member.display_name, member.avatar_url,
                actor.username, actor.display_name, actor.avatar_url,
            )
            .join(User, User.id == CommunityMemberRestriction.member_user_id)
            .outerjoin(
                member,
                member.user_id == CommunityMemberRestriction.member_user_id,
            )
            .outerjoin(actor, actor.user_id == CommunityMemberRestriction.actor_user_id)
            .where(CommunityMemberRestriction.member_user_id == member_id)
            .order_by(
                CommunityMemberRestriction.created_at.desc(),
                CommunityMemberRestriction.id.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
        result: list[CommunityRestrictionRow] = []
        for row in rows.all():
            restriction = row[0]
            status = (
                "REVOKED" if restriction.revoked_at is not None
                else "ACTIVE"
                if (
                    _as_utc(restriction.starts_at)
                    <= now
                    < _as_utc(restriction.expires_at)
                )
                else "EXPIRED"
            )
            result.append(CommunityRestrictionRow(*row, status))
        return CommunityRestrictionPage(tuple(result), total)


    async def get_public_post(self, post_id: UUID) -> CommunityPost | None:
        author = aliased(User)
        return cast(
            CommunityPost | None,
            await self._session.scalar(
                select(CommunityPost)
                .join(
                    CommunityCategory,
                    CommunityCategory.id == CommunityPost.category_id,
                )
                .join(author, author.id == CommunityPost.author_user_id)
                .where(
                    CommunityPost.id == post_id,
                    CommunityPost.status == CommunityPostStatus.PUBLISHED,
                    CommunityPost.deleted_at.is_(None),
                    CommunityPost.published_at.is_not(None),
                    CommunityCategory.is_active.is_(True),
                    author.status == UserStatus.ACTIVE,
                )
            ),
        )

    async def get_post(
        self, post_id: UUID, *, for_update: bool = False
    ) -> CommunityPost | None:
        statement = select(CommunityPost).where(CommunityPost.id == post_id)
        if for_update:
            statement = statement.with_for_update()
        return cast(CommunityPost | None, await self._session.scalar(statement))

    async def get_comment(
        self, comment_id: UUID, *, for_update: bool = False
    ) -> CommunityComment | None:
        statement = select(CommunityComment).where(CommunityComment.id == comment_id)
        if for_update:
            statement = statement.with_for_update()
        return cast(CommunityComment | None, await self._session.scalar(statement))

    async def get_public_comment(self, comment_id: UUID) -> CommunityComment | None:
        post_author = aliased(User)
        comment_author = aliased(User)
        return cast(
            CommunityComment | None,
            await self._session.scalar(
                select(CommunityComment)
                .join(CommunityPost, CommunityPost.id == CommunityComment.post_id)
                .join(
                    CommunityCategory,
                    CommunityCategory.id == CommunityPost.category_id,
                )
                .join(post_author, post_author.id == CommunityPost.author_user_id)
                .join(
                    comment_author,
                    comment_author.id == CommunityComment.author_user_id,
                )
                .where(
                    CommunityComment.id == comment_id,
                    CommunityComment.deleted_at.is_(None),
                    CommunityComment.moderation_hidden_at.is_(None),
                    CommunityPost.status == CommunityPostStatus.PUBLISHED,
                    CommunityPost.deleted_at.is_(None),
                    CommunityPost.published_at.is_not(None),
                    CommunityCategory.is_active.is_(True),
                    post_author.status == UserStatus.ACTIVE,
                    comment_author.status == UserStatus.ACTIVE,
                )
            ),
        )

    async def get_open_report(
        self,
        reporter_user_id: UUID,
        *,
        post_id: UUID | None,
        comment_id: UUID | None,
    ) -> CommunityReport | None:
        filters: list[object] = [
            CommunityReport.reporter_user_id == reporter_user_id,
            CommunityReport.status == "OPEN",
        ]
        filters.append(
            CommunityReport.post_id == post_id
            if post_id is not None
            else CommunityReport.comment_id == comment_id
        )
        return cast(
            CommunityReport | None,
            await self._session.scalar(select(CommunityReport).where(*filters)),
        )

    def add_report(self, report: CommunityReport) -> None:
        self._session.add(report)

    async def get_report_for_update(self, report_id: UUID) -> CommunityReport | None:
        return cast(
            CommunityReport | None,
            await self._session.scalar(
                select(CommunityReport)
                .where(CommunityReport.id == report_id)
                .with_for_update()
            ),
        )

    async def get_report_row(self, report_id: UUID) -> CommunityReportRow | None:
        result = await self._session.execute(
            self._report_rows_statement()
            .where(CommunityReport.id == report_id)
            .limit(1)
        )
        rows = self._report_rows(result.all())
        return rows[0] if rows else None

    async def list_reports(
        self,
        *,
        status: str,
        offset: int,
        limit: int,
    ) -> CommunityReportPage:
        total = int(
            await self._session.scalar(
                select(func.count(CommunityReport.id)).where(
                    CommunityReport.status == status
                )
            )
            or 0
        )
        result = await self._session.execute(
            self._report_rows_statement()
            .where(CommunityReport.status == status)
            .order_by(CommunityReport.created_at.desc(), CommunityReport.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return CommunityReportPage(items=self._report_rows(result.all()), total=total)

    @staticmethod
    def _report_rows_statement():
        reporter_profile = aliased(CommunityProfile)
        post_target = aliased(CommunityPost)
        post_author_profile = aliased(CommunityProfile)
        comment_target = aliased(CommunityComment)
        comment_post = aliased(CommunityPost)
        comment_author_profile = aliased(CommunityProfile)
        return (
            select(
                CommunityReport,
                reporter_profile.username,
                reporter_profile.display_name,
                reporter_profile.avatar_url,
                post_target,
                post_author_profile.username,
                post_author_profile.display_name,
                post_author_profile.avatar_url,
                comment_target,
                comment_post,
                comment_author_profile.username,
                comment_author_profile.display_name,
                comment_author_profile.avatar_url,
            )
            .join(User, User.id == CommunityReport.reporter_user_id)
            .outerjoin(
                reporter_profile,
                reporter_profile.user_id == CommunityReport.reporter_user_id,
            )
            .outerjoin(post_target, post_target.id == CommunityReport.post_id)
            .outerjoin(
                post_author_profile,
                post_author_profile.user_id == post_target.author_user_id,
            )
            .outerjoin(comment_target, comment_target.id == CommunityReport.comment_id)
            .outerjoin(comment_post, comment_post.id == comment_target.post_id)
            .outerjoin(
                comment_author_profile,
                comment_author_profile.user_id == comment_target.author_user_id,
            )
        )

    @staticmethod
    def _report_rows(rows: list[tuple[object, ...]]) -> tuple[CommunityReportRow, ...]:
        return tuple(CommunityReportRow(*row) for row in rows)

    async def list_categories(self) -> tuple[CommunityCategory, ...]:
        result = await self._session.scalars(
            select(CommunityCategory).order_by(
                CommunityCategory.sort_order,
                CommunityCategory.name,
            )
        )
        return tuple(result.all())

    async def get_category(
        self,
        category_id: UUID,
        *,
        for_update: bool = False,
    ) -> CommunityCategory | None:
        statement = select(CommunityCategory).where(CommunityCategory.id == category_id)
        if for_update:
            statement = statement.with_for_update()
        return cast(CommunityCategory | None, await self._session.scalar(statement))

    async def get_category_by_slug(self, slug: str) -> CommunityCategory | None:
        return cast(
            CommunityCategory | None,
            await self._session.scalar(
                select(CommunityCategory).where(CommunityCategory.slug == slug)
            ),
        )

    def add_category(self, category: CommunityCategory) -> None:
        self._session.add(category)

    async def get_settings(self) -> CommunitySettings | None:
        return cast(
            CommunitySettings | None,
            await self._session.get(CommunitySettings, 1),
        )

    def add_settings(self, settings: CommunitySettings) -> None:
        self._session.add(settings)

    def add_moderation_event(self, event: CommunityModerationEvent) -> None:
        self._session.add(event)

    async def list_moderation_events(
        self,
        *,
        target_type: str | None,
        target_id: str | None,
        offset: int,
        limit: int,
    ) -> CommunityModerationEventPage:
        actor_profile = aliased(CommunityProfile)
        filters: list[object] = []
        if target_type is not None:
            filters.append(CommunityModerationEvent.target_type == target_type)
        if target_id is not None:
            filters.append(CommunityModerationEvent.target_id == target_id)
        total = int(
            await self._session.scalar(
                select(func.count(CommunityModerationEvent.id)).where(*filters)
            )
            or 0
        )
        rows = await self._session.execute(
            select(
                CommunityModerationEvent,
                actor_profile.username,
                actor_profile.display_name,
                actor_profile.avatar_url,
            )
            .join(User, User.id == CommunityModerationEvent.actor_user_id)
            .outerjoin(
                actor_profile,
                actor_profile.user_id == CommunityModerationEvent.actor_user_id,
            )
            .where(*filters)
            .order_by(
                CommunityModerationEvent.created_at.desc(),
                CommunityModerationEvent.id.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
        return CommunityModerationEventPage(
            items=tuple(
                CommunityModerationEventRow(*row) for row in rows.all()
            ),
            total=total,
        )


def _like_pattern(query: str) -> str:
    escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
