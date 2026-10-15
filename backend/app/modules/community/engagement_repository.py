from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal, cast
from uuid import UUID

from sqlalchemy import func, literal, or_, select, update
from sqlalchemy.engine import CursorResult, Row
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.selectable import Select

from app.modules.auth.models import User, UserStatus
from app.modules.community.models import (
    CommunityBookmark,
    CommunityCategory,
    CommunityComment,
    CommunityCommentLike,
    CommunityFollow,
    CommunityLike,
    CommunityPost,
    CommunityPostStatus,
    CommunityProfile,
)
from app.modules.community.repository import CommunityPostRow, CommunityRepository


@dataclass(frozen=True, slots=True)
class CommunityCommentRow:
    comment: CommunityComment
    author_username: str | None
    author_display_name: str | None
    author_avatar_url: str | None
    like_count: int
    viewer_has_liked: bool


CommunityCommentTuple = tuple[
    CommunityComment, str | None, str | None, str | None, int, bool
]


@dataclass(frozen=True, slots=True)
class CommunityCommentThread:
    root: CommunityCommentRow
    replies: tuple[CommunityCommentRow, ...]


@dataclass(frozen=True, slots=True)
class CommunityCommentPage:
    items: tuple[CommunityCommentThread, ...]
    total: int


@dataclass(frozen=True, slots=True)
class CommunityMemberRecord:
    user: User
    profile: CommunityProfile


@dataclass(frozen=True, slots=True)
class CommunityMemberListRecord:
    user: User
    profile: CommunityProfile
    viewer_is_following: bool


class CommunityEngagementRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._posts = CommunityRepository(session)

    async def get_public_post(
        self, post_id: UUID, *, viewer_user_id: UUID | None = None
    ) -> CommunityPostRow | None:
        return await self._posts.get_public_post_by_id(
            post_id,
            viewer_user_id=viewer_user_id,
        )

    async def list_active_mention_recipients(
        self, usernames: tuple[str, ...]
    ) -> tuple[UUID, ...]:
        return await self._posts.list_active_mention_recipients(usernames)

    async def list_member_posts(
        self,
        member_id: UUID,
        *,
        viewer_user_id: UUID | None,
        offset: int,
        limit: int,
    ) -> tuple[tuple[CommunityPostRow, ...], int]:
        return await self._posts.list_public_posts(
            category_slug=None,
            author_user_id=member_id,
            viewer_user_id=viewer_user_id,
            offset=offset,
            limit=limit,
        )

    async def list_bookmarks(
        self,
        user_id: UUID,
        *,
        viewer_user_id: UUID,
        offset: int,
        limit: int,
    ) -> tuple[tuple[CommunityPostRow, ...], int]:
        public_filters = self._posts._public_filters()
        count_result = await self._session.execute(
            select(func.count(CommunityBookmark.id))
            .join(
                CommunityPost,
                CommunityPost.id == CommunityBookmark.post_id,
            )
            .join(
                CommunityCategory,
                CommunityCategory.id == CommunityPost.category_id,
            )
            .join(User, User.id == CommunityPost.author_user_id)
            .where(*public_filters, CommunityBookmark.user_id == user_id)
        )
        total = int(count_result.scalar_one() or 0)
        bookmark_entry = aliased(CommunityBookmark)
        result = await self._session.execute(
            self._posts._post_rows_statement(viewer_user_id=viewer_user_id)
            .join(
                bookmark_entry,
                bookmark_entry.post_id == CommunityPost.id,
            )
            .where(*public_filters, bookmark_entry.user_id == user_id)
            .order_by(bookmark_entry.created_at.desc(), bookmark_entry.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return CommunityRepository._rows(result.all()), total

    async def get_active_user(self, user_id: UUID) -> User | None:
        return cast(
            User | None,
            await self._session.scalar(
                select(User).where(
                    User.id == user_id,
                    User.status == UserStatus.ACTIVE,
                )
            ),
        )

    async def get_member_by_username(
        self, username: str
    ) -> CommunityMemberRecord | None:
        result = await self._session.execute(
            select(User, CommunityProfile)
            .join(CommunityProfile, CommunityProfile.user_id == User.id)
            .where(
                CommunityProfile.username == username,
                User.status == UserStatus.ACTIVE,
            )
            .limit(1)
        )
        row = result.first()
        return CommunityMemberRecord(*row) if row is not None else None

    async def username_taken(self, username: str, *, except_user_id: UUID) -> bool:
        return bool(
            await self._session.scalar(
                select(CommunityProfile.user_id)
                .where(
                    func.lower(CommunityProfile.username) == username.lower(),
                    CommunityProfile.user_id != except_user_id,
                )
                .limit(1)
            )
        )

    async def list_member_relations(
        self,
        member_id: UUID,
        *,
        relation_kind: Literal["followers", "following"],
        viewer_user_id: UUID | None,
        offset: int,
        limit: int,
    ) -> tuple[tuple[CommunityMemberListRecord, ...], int]:
        if relation_kind == "followers":
            relation_filter = CommunityFollow.followed_user_id == member_id
            listed_user_id = CommunityFollow.follower_user_id
        else:
            relation_filter = CommunityFollow.follower_user_id == member_id
            listed_user_id = CommunityFollow.followed_user_id
        viewer_is_following: ColumnElement[bool] = literal(False)
        if viewer_user_id is not None:
            followed_relation = aliased(CommunityFollow)
            viewer_is_following = (
                select(followed_relation.id)
                .where(
                    followed_relation.follower_user_id == viewer_user_id,
                    followed_relation.followed_user_id == User.id,
                )
                .exists()
            )
        total = int(
            await self._session.scalar(
                select(func.count(CommunityFollow.id))
                .join(User, User.id == listed_user_id)
                .where(relation_filter, User.status == UserStatus.ACTIVE)
            )
            or 0
        )
        result = await self._session.execute(
            select(CommunityFollow, User, CommunityProfile, viewer_is_following)
            .join(User, User.id == listed_user_id)
            .join(CommunityProfile, CommunityProfile.user_id == User.id)
            .where(relation_filter, User.status == UserStatus.ACTIVE)
            .order_by(CommunityFollow.created_at.desc(), CommunityFollow.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return (
            tuple(
                CommunityMemberListRecord(user, profile, bool(is_following))
                for _relation, user, profile, is_following in result.all()
            ),
            total,
        )

    async def get_profile(self, user_id: UUID) -> CommunityProfile | None:
        return await self._posts.get_community_profile(user_id)

    def add_profile(self, profile: CommunityProfile) -> None:
        self._posts.add_community_profile(profile)

    async def member_metrics(
        self,
        member_id: UUID,
        *,
        viewer_user_id: UUID | None,
    ) -> tuple[int, int, int, bool]:
        post_count = int(
            await self._session.scalar(
                select(func.count(CommunityPost.id))
                .join(
                    CommunityCategory,
                    CommunityCategory.id == CommunityPost.category_id,
                )
                .where(
                    CommunityPost.author_user_id == member_id,
                    CommunityPost.status == CommunityPostStatus.PUBLISHED,
                    CommunityPost.deleted_at.is_(None),
                    CommunityPost.published_at.is_not(None),
                    CommunityCategory.is_active.is_(True),
                )
            )
            or 0
        )
        follower_count = int(
            await self._session.scalar(
                select(func.count(CommunityFollow.id))
                .join(User, User.id == CommunityFollow.follower_user_id)
                .where(
                    CommunityFollow.followed_user_id == member_id,
                    User.status == UserStatus.ACTIVE,
                )
            )
            or 0
        )
        following_count = int(
            await self._session.scalar(
                select(func.count(CommunityFollow.id))
                .join(User, User.id == CommunityFollow.followed_user_id)
                .where(
                    CommunityFollow.follower_user_id == member_id,
                    User.status == UserStatus.ACTIVE,
                )
            )
            or 0
        )
        viewer_is_following = False
        if viewer_user_id is not None:
            viewer_is_following = bool(
                await self._session.scalar(
                    select(CommunityFollow.id)
                    .where(
                        CommunityFollow.follower_user_id == viewer_user_id,
                        CommunityFollow.followed_user_id == member_id,
                    )
                    .limit(1)
                )
            )
        return post_count, follower_count, following_count, viewer_is_following

    async def list_comment_threads(
        self,
        post_id: UUID,
        *,
        viewer_user_id: UUID | None,
        sort: str,
        offset: int,
        limit: int,
    ) -> CommunityCommentPage:
        total = int(
            await self._session.scalar(
                select(func.count(CommunityComment.id))
                .join(User, User.id == CommunityComment.author_user_id)
                .where(
                    CommunityComment.post_id == post_id,
                    CommunityComment.parent_id.is_(None),
                    or_(
                        CommunityComment.deleted_at.is_not(None),
                        CommunityComment.moderation_hidden_at.is_not(None),
                        User.status == UserStatus.ACTIVE,
                    ),
                )
            )
            or 0
        )
        roots_result = await self._session.execute(
            self._comment_rows_statement(viewer_user_id=viewer_user_id)
            .where(
                CommunityComment.post_id == post_id,
                CommunityComment.parent_id.is_(None),
                or_(
                    CommunityComment.deleted_at.is_not(None),
                    CommunityComment.moderation_hidden_at.is_not(None),
                    User.status == UserStatus.ACTIVE,
                ),
            )
            .order_by(
                CommunityComment.created_at.desc()
                if sort == "newest"
                else CommunityComment.created_at,
                CommunityComment.id.desc() if sort == "newest" else CommunityComment.id,
            )
            .offset(offset)
            .limit(limit)
        )
        roots = self._comment_rows(roots_result.all())
        if not roots:
            return CommunityCommentPage(items=(), total=total)
        root_ids = tuple(row.comment.id for row in roots)
        reply_ids = (
            select(
                CommunityComment.id.label("comment_id"),
                CommunityComment.parent_id.label("root_id"),
            )
            .where(
                CommunityComment.post_id == post_id,
                CommunityComment.parent_id.in_(root_ids),
            )
            .cte("community_comment_descendants", recursive=True)
        )
        child = aliased(CommunityComment)
        reply_ids = reply_ids.union_all(
            select(child.id.label("comment_id"), reply_ids.c.root_id).where(
                child.post_id == post_id,
                child.parent_id == reply_ids.c.comment_id,
            )
        )
        replies_result = await self._session.execute(
            self._comment_rows_statement(viewer_user_id=viewer_user_id)
            .add_columns(reply_ids.c.root_id)
            .join(reply_ids, reply_ids.c.comment_id == CommunityComment.id)
            .where(
                or_(
                    CommunityComment.deleted_at.is_not(None),
                    CommunityComment.moderation_hidden_at.is_not(None),
                    User.status == UserStatus.ACTIVE,
                ),
            )
            .order_by(
                CommunityComment.created_at.desc()
                if sort == "newest"
                else CommunityComment.created_at,
                CommunityComment.id.desc() if sort == "newest" else CommunityComment.id,
            )
        )
        reply_rows = replies_result.all()
        replies_by_parent: dict[UUID, list[CommunityCommentRow]] = {
            root_id: [] for root_id in root_ids
        }
        for row in reply_rows:
            reply = CommunityCommentRow(row[0], row[1], row[2], row[3], row[4], row[5])
            replies_by_parent[cast(UUID, row[6])].append(reply)
        return CommunityCommentPage(
            items=tuple(
                CommunityCommentThread(
                    root=root,
                    replies=tuple(replies_by_parent[root.comment.id]),
                )
                for root in roots
            ),
            total=total,
        )

    async def get_comment_row(
        self,
        comment_id: UUID,
        *,
        viewer_user_id: UUID | None = None,
    ) -> CommunityCommentRow | None:
        result = await self._session.execute(
            self._comment_rows_statement(viewer_user_id=viewer_user_id)
            .where(
                CommunityComment.id == comment_id,
                User.status == UserStatus.ACTIVE,
            )
            .limit(1)
        )
        rows = self._comment_rows(result.all())
        return rows[0] if rows else None

    async def get_comment(self, comment_id: UUID) -> CommunityComment | None:
        result = await self._session.execute(
            select(CommunityComment).where(CommunityComment.id == comment_id).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_comment_for_update(self, comment_id: UUID) -> CommunityComment | None:
        result = await self._session.scalar(
            select(CommunityComment)
            .where(CommunityComment.id == comment_id)
            .with_for_update()
        )
        return result

    async def get_like(self, post_id: UUID, user_id: UUID) -> CommunityLike | None:
        result = await self._session.scalar(
            select(CommunityLike).where(
                CommunityLike.post_id == post_id,
                CommunityLike.user_id == user_id,
            )
        )
        return result

    async def get_bookmark(
        self, post_id: UUID, user_id: UUID
    ) -> CommunityBookmark | None:
        result = await self._session.scalar(
            select(CommunityBookmark).where(
                CommunityBookmark.post_id == post_id,
                CommunityBookmark.user_id == user_id,
            )
        )
        return result

    async def get_follow(
        self, follower_user_id: UUID, followed_user_id: UUID
    ) -> CommunityFollow | None:
        result = await self._session.scalar(
            select(CommunityFollow).where(
                CommunityFollow.follower_user_id == follower_user_id,
                CommunityFollow.followed_user_id == followed_user_id,
            )
        )
        return result

    def add_comment(self, comment: CommunityComment) -> None:
        self._session.add(comment)

    async def get_comment_like(
        self,
        comment_id: UUID,
        user_id: UUID,
    ) -> CommunityCommentLike | None:
        return cast(
            CommunityCommentLike | None,
            await self._session.scalar(
                select(CommunityCommentLike).where(
                    CommunityCommentLike.comment_id == comment_id,
                    CommunityCommentLike.user_id == user_id,
                )
            ),
        )

    def add_comment_like(self, like: CommunityCommentLike) -> None:
        self._session.add(like)

    async def comment_like_count(self, comment_id: UUID) -> int:
        return int(
            await self._session.scalar(
                select(func.count(CommunityCommentLike.id))
                .join(User, User.id == CommunityCommentLike.user_id)
                .where(
                    CommunityCommentLike.comment_id == comment_id,
                    User.status == UserStatus.ACTIVE,
                )
            )
            or 0
        )

    async def increment_public_post_view(self, post_id: UUID) -> bool:
        result = cast(
            CursorResult[Any],
            await self._session.execute(
                update(CommunityPost)
                .where(
                    CommunityPost.id == post_id,
                    CommunityPost.status == CommunityPostStatus.PUBLISHED,
                    CommunityPost.deleted_at.is_(None),
                    CommunityPost.published_at.is_not(None),
                    CommunityPost.category_id.in_(
                        select(CommunityCategory.id).where(
                            CommunityCategory.is_active.is_(True)
                        )
                    ),
                    CommunityPost.author_user_id.in_(
                        select(User.id).where(User.status == UserStatus.ACTIVE)
                    ),
                )
                .values(view_count=CommunityPost.view_count + 1)
            ),
        )
        return bool(result.rowcount == 1)

    def add_like(self, like: CommunityLike) -> None:
        self._session.add(like)

    def add_bookmark(self, bookmark: CommunityBookmark) -> None:
        self._session.add(bookmark)

    def add_follow(self, follow: CommunityFollow) -> None:
        self._session.add(follow)

    async def like_count(self, post_id: UUID) -> int:
        return int(
            await self._session.scalar(
                select(func.count(CommunityLike.id))
                .join(User, User.id == CommunityLike.user_id)
                .where(
                    CommunityLike.post_id == post_id,
                    User.status == UserStatus.ACTIVE,
                )
            )
            or 0
        )

    async def follower_count(self, member_id: UUID) -> int:
        return int(
            await self._session.scalar(
                select(func.count(CommunityFollow.id))
                .join(User, User.id == CommunityFollow.follower_user_id)
                .where(
                    CommunityFollow.followed_user_id == member_id,
                    User.status == UserStatus.ACTIVE,
                )
            )
            or 0
        )

    @staticmethod
    def _comment_rows_statement(
        *, viewer_user_id: UUID | None = None
    ) -> Select[CommunityCommentTuple]:
        like_user = aliased(User)
        like_count = (
            select(func.count(CommunityCommentLike.id))
            .join(like_user, like_user.id == CommunityCommentLike.user_id)
            .where(CommunityCommentLike.comment_id == CommunityComment.id)
            .where(like_user.status == UserStatus.ACTIVE)
            .scalar_subquery()
        )
        viewer_has_liked: ColumnElement[bool] = literal(False)
        if viewer_user_id is not None:
            viewer_has_liked = (
                select(CommunityCommentLike.id)
                .where(
                    CommunityCommentLike.comment_id == CommunityComment.id,
                    CommunityCommentLike.user_id == viewer_user_id,
                )
                .exists()
            )
        return (
            select(
                CommunityComment,
                CommunityProfile.username,
                CommunityProfile.display_name,
                CommunityProfile.avatar_url,
                like_count,
                viewer_has_liked,
            )
            .join(User, User.id == CommunityComment.author_user_id)
            .outerjoin(
                CommunityProfile,
                CommunityProfile.user_id == CommunityComment.author_user_id,
            )
        )

    @staticmethod
    def _comment_rows(
        rows: Sequence[Row[CommunityCommentTuple]],
    ) -> tuple[CommunityCommentRow, ...]:
        return tuple(
            CommunityCommentRow(
                comment,
                username,
                display_name,
                avatar_url,
                like_count,
                viewer_has_liked,
            )
            for (
                comment,
                username,
                display_name,
                avatar_url,
                like_count,
                viewer_has_liked,
            ) in rows
        )
