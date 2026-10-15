from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal
from urllib.parse import quote
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.session_service import AuthPrincipal
from app.modules.community.engagement_repository import (
    CommunityCommentPage,
    CommunityCommentRow,
    CommunityEngagementRepository,
    CommunityMemberListRecord,
    CommunityMemberRecord,
)
from app.modules.community.engagement_schemas import (
    CommunityCommentRequest,
    CommunityMemberProfileEditRequest,
)
from app.modules.community.errors import (
    CommunityConflictError,
    CommunityForbiddenError,
    CommunityNotFoundError,
    CommunityValidationError,
)
from app.modules.community.mentions import extract_community_mentions
from app.modules.community.models import (
    CommunityBookmark,
    CommunityComment,
    CommunityCommentLike,
    CommunityFollow,
    CommunityLike,
    CommunityMemberRestriction,
    CommunityProfile,
)
from app.modules.community.service import CommunityPostPage
from app.modules.engagement.errors import EngagementUnavailableError
from app.modules.engagement.redis import RedisViewDeduplicator
from app.modules.media.models import MediaAsset, MediaConfidentiality, MediaStatus
from app.modules.media.types import AVATAR_IMAGE_MIME_TYPES, MediaPurpose
from app.modules.notifications.service import NotificationService

_DISPLAY_NAME_FALLBACK = "Thành viên"


@dataclass(frozen=True, slots=True)
class CommunityMemberView:
    member: CommunityMemberRecord
    published_post_count: int
    follower_count: int
    following_count: int
    viewer_is_following: bool


class CommunityEngagementService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        views: RedisViewDeduplicator | None = None,
        avatar_max_bytes: int = 5_242_880,
    ) -> None:
        self._session = session
        self._repository = CommunityEngagementRepository(session)
        self._views = views
        self._avatar_max_bytes = avatar_max_bytes

    async def list_comments(
        self,
        post_id: UUID,
        *,
        viewer_user_id: UUID | None,
        sort: str,
        page: int,
        page_size: int,
    ) -> CommunityCommentPage:
        async with self._session.begin():
            if await self._repository.get_public_post(post_id) is None:
                raise CommunityNotFoundError()
            return await self._repository.list_comment_threads(
                post_id,
                viewer_user_id=viewer_user_id,
                sort=sort,
                offset=(page - 1) * page_size,
                limit=page_size,
            )

    async def create_comment(
        self,
        principal: AuthPrincipal,
        post_id: UUID,
        payload: CommunityCommentRequest,
    ) -> CommunityCommentRow:
        async with self._session.begin():
            post = await self._repository.get_public_post(post_id)
            if post is None:
                raise CommunityNotFoundError()
            await self._ensure_not_restricted(principal.user_id, "COMMENTS")
            if post.post.comments_locked_at is not None:
                raise CommunityConflictError()
            await self._ensure_community_profile(principal.user_id)
            recipient_id = post.post.author_user_id
            if payload.parent_id is not None:
                parent = await self._repository.get_comment(payload.parent_id)
                if parent is None or parent.post_id != post_id:
                    raise CommunityNotFoundError()
                recipient_id = parent.author_user_id
            comment = CommunityComment(
                id=uuid4(),
                post_id=post_id,
                author_user_id=principal.user_id,
                parent_id=payload.parent_id,
                content=payload.content,
                created_at=datetime.now(UTC),
            )
            self._repository.add_comment(comment)
            await self._session.flush()
            mentioned_user_ids = set(
                await self._repository.list_active_mention_recipients(
                    extract_community_mentions(payload.content)
                )
            )
            if (
                recipient_id != principal.user_id
                and recipient_id not in mentioned_user_ids
            ):
                is_reply = payload.parent_id is not None
                await NotificationService(self._session).consume_in_transaction(
                    event_id=comment.id,
                    user_id=recipient_id,
                    event_type=("COMMUNITY_REPLY" if is_reply else "COMMUNITY_COMMENT"),
                    title="Có phản hồi mới" if is_reply else "Có bình luận mới",
                    body=f"Có hoạt động mới trong bài viết “{post.post.title}”.",
                    data={
                        "actionPath": (
                            f"/community/posts/{quote(post.post.slug, safe='-._~')}"
                        )
                    },
                )
            for mentioned_user_id in mentioned_user_ids:
                if mentioned_user_id == principal.user_id:
                    continue
                await NotificationService(self._session).consume_in_transaction(
                    event_id=comment.id,
                    user_id=mentioned_user_id,
                    event_type="COMMUNITY_MENTION",
                    title=("Báº¡n Ä‘Æ°á»£c nháº¯c Ä‘áº¿n trong cá»™ng Ä‘á»“ng"),
                    body=(
                        "CÃ³ thÃ nh viÃªn nháº¯c Ä‘áº¿n báº¡n "
                        "trong má»™t cuá»™c tháº£o luáº­n."
                    ),
                    data={
                        "actionPath": (
                            f"/community/posts/{quote(post.post.slug, safe='-._~')}"
                        )
                    },
                )
            row = await self._repository.get_comment_row(comment.id)
            if row is None:
                raise CommunityNotFoundError()
            return row

    async def update_comment(
        self,
        principal: AuthPrincipal,
        comment_id: UUID,
        content: str,
    ) -> CommunityCommentRow:
        async with self._session.begin():
            comment = await self._repository.get_comment_for_update(comment_id)
            self._require_comment_owner(comment, principal)
            if comment.deleted_at is not None:
                raise CommunityConflictError()
            await self._ensure_not_restricted(principal.user_id, "COMMENTS")
            comment.content = content
            await self._session.flush()
            row = await self._repository.get_comment_row(comment.id)
            if row is None:
                raise CommunityNotFoundError()
            return row

    async def delete_comment(
        self,
        principal: AuthPrincipal,
        comment_id: UUID,
    ) -> None:
        async with self._session.begin():
            comment = await self._repository.get_comment_for_update(comment_id)
            self._require_comment_owner(comment, principal)
            if comment.deleted_at is not None:
                return
            comment.content = "Bình luận đã bị xóa."
            comment.deleted_at = datetime.now(UTC)
            await self._session.flush()

    async def set_comment_like(
        self,
        principal: AuthPrincipal,
        comment_id: UUID,
        *,
        is_liked: bool,
    ) -> tuple[int, bool]:
        async with self._session.begin():
            comment = await self._repository.get_comment(comment_id)
            if (
                comment is None
                or comment.deleted_at is not None
                or comment.moderation_hidden_at is not None
                or await self._repository.get_public_post(comment.post_id) is None
            ):
                raise CommunityNotFoundError()
            await self._ensure_community_profile(principal.user_id)
            relation = await self._repository.get_comment_like(
                comment_id,
                principal.user_id,
            )
            if is_liked and relation is None:
                like = CommunityCommentLike(
                    id=uuid4(),
                    comment_id=comment_id,
                    user_id=principal.user_id,
                )
                await self._insert_if_absent(like, self._repository.add_comment_like)
            elif not is_liked and relation is not None:
                await self._session.delete(relation)
                await self._session.flush()
            return await self._repository.comment_like_count(comment_id), is_liked

    async def record_post_view(self, post_id: UUID, *, visitor: str) -> bool:
        if self._views is None:
            raise EngagementUnavailableError()
        async with self._session.begin():
            if await self._repository.get_public_post(post_id) is None:
                raise CommunityNotFoundError()
            accepted = await self._views.accept(
                visitor=visitor,
                public_work_id=str(post_id),
            )
            if not accepted:
                return False
            if not await self._repository.increment_public_post_view(post_id):
                raise CommunityNotFoundError()
            return True

    async def set_like(
        self,
        principal: AuthPrincipal,
        post_id: UUID,
        *,
        is_liked: bool,
    ) -> tuple[int, bool]:
        async with self._session.begin():
            post = await self._repository.get_public_post(post_id)
            if post is None:
                raise CommunityNotFoundError()
            await self._ensure_community_profile(principal.user_id)
            relation = await self._repository.get_like(post_id, principal.user_id)
            if is_liked and relation is None:
                like = CommunityLike(
                    id=uuid4(),
                    post_id=post_id,
                    user_id=principal.user_id,
                )
                inserted = await self._insert_if_absent(
                    like,
                    self._repository.add_like,
                )
                if inserted and post.post.author_user_id != principal.user_id:
                    await NotificationService(self._session).consume_in_transaction(
                        event_id=like.id,
                        user_id=post.post.author_user_id,
                        event_type="COMMUNITY_POST_LIKED",
                        title="Bài viết có lượt thích mới",
                        body=f"Bài viết “{post.post.title}” có lượt thích mới.",
                        data={
                            "actionPath": (
                                f"/community/posts/{quote(post.post.slug, safe='-._~')}"
                            )
                        },
                    )
            elif not is_liked and relation is not None:
                await self._session.delete(relation)
                await self._session.flush()
            return await self._repository.like_count(post_id), is_liked

    async def set_bookmark(
        self,
        principal: AuthPrincipal,
        post_id: UUID,
        *,
        is_bookmarked: bool,
    ) -> bool:
        async with self._session.begin():
            if await self._repository.get_public_post(post_id) is None:
                raise CommunityNotFoundError()
            await self._ensure_community_profile(principal.user_id)
            relation = await self._repository.get_bookmark(
                post_id,
                principal.user_id,
            )
            if is_bookmarked and relation is None:
                bookmark = CommunityBookmark(
                    id=uuid4(),
                    post_id=post_id,
                    user_id=principal.user_id,
                )
                await self._insert_if_absent(
                    bookmark,
                    self._repository.add_bookmark,
                )
            elif not is_bookmarked and relation is not None:
                await self._session.delete(relation)
                await self._session.flush()
            return is_bookmarked

    async def member_profile(
        self,
        member_id: UUID,
        *,
        viewer_user_id: UUID | None,
    ) -> CommunityMemberView:
        async with self._session.begin():
            user = await self._repository.get_active_user(member_id)
            if user is None:
                raise CommunityNotFoundError()
            profile = await self._ensure_community_profile(member_id)
            record = CommunityMemberRecord(user, profile)
            return await self._member_view(record, viewer_user_id)

    async def member_profile_by_username(
        self,
        username: str,
        *,
        viewer_user_id: UUID | None,
    ) -> CommunityMemberView:
        async with self._session.begin():
            record = await self._repository.get_member_by_username(username)
            if record is None:
                raise CommunityNotFoundError()
            return await self._member_view(record, viewer_user_id)

    async def update_member_profile(
        self,
        principal: AuthPrincipal,
        payload: CommunityMemberProfileEditRequest,
    ) -> CommunityMemberView:
        async with self._session.begin():
            profile = await self._ensure_community_profile(principal.user_id)
            username = payload.username
            if (
                "username" in payload.model_fields_set
                and username is not None
                and username != profile.username
                and await self._repository.username_taken(
                    username,
                    except_user_id=principal.user_id,
                )
            ):
                raise CommunityConflictError()
            avatar_media_id = payload.avatar_media_id
            if (
                "avatar_media_id" in payload.model_fields_set
                and avatar_media_id is not None
            ):
                avatar = await self._session.scalar(
                    select(MediaAsset).where(MediaAsset.id == avatar_media_id)
                )
                if (
                    avatar is None
                    or avatar.owner_user_id != principal.user_id
                    or avatar.purpose != MediaPurpose.AVATAR.value
                    or avatar.status is not MediaStatus.ACTIVE
                    or avatar.deleted_at is not None
                    or avatar.inspected_at is None
                    or avatar.mime_type not in AVATAR_IMAGE_MIME_TYPES
                    or avatar.bytes <= 0
                    or avatar.bytes > self._avatar_max_bytes
                    or avatar.sha256 is None
                    or avatar.access_mode != "authenticated"
                    or avatar.confidentiality is not MediaConfidentiality.PRIVATE
                ):
                    raise CommunityValidationError()
            try:
                async with self._session.begin_nested():
                    if "username" in payload.model_fields_set:
                        if username is None:
                            raise CommunityConflictError()
                        profile.username = username
                    if "display_name" in payload.model_fields_set:
                        profile.display_name = payload.display_name
                    if "avatar_url" in payload.model_fields_set:
                        profile.avatar_url = payload.avatar_url
                        profile.avatar_media_id = None
                    if "avatar_media_id" in payload.model_fields_set:
                        profile.avatar_media_id = avatar_media_id
                        profile.avatar_url = (
                            f"/api/v1/community/avatars/{avatar_media_id}"
                            if avatar_media_id is not None
                            else None
                        )
                    if "bio" in payload.model_fields_set:
                        profile.bio = payload.bio
                    await self._session.flush()
            except IntegrityError as exc:
                raise CommunityConflictError() from exc
            user = await self._repository.get_active_user(principal.user_id)
            if user is None:
                raise CommunityNotFoundError()
            return await self._member_view(
                CommunityMemberRecord(user, profile),
                viewer_user_id=principal.user_id,
            )

    async def member_relations(
        self,
        username: str,
        *,
        relation_kind: Literal["followers", "following"],
        viewer_user_id: UUID | None,
        page: int,
        page_size: int,
    ) -> tuple[tuple[CommunityMemberListRecord, ...], int]:
        async with self._session.begin():
            member = await self._repository.get_member_by_username(username)
            if member is None:
                raise CommunityNotFoundError()
            items, total = await self._repository.list_member_relations(
                member.user.id,
                relation_kind=relation_kind,
                viewer_user_id=viewer_user_id,
                offset=(page - 1) * page_size,
                limit=page_size,
            )
            return items, total

    async def member_posts(
        self,
        username: str,
        *,
        viewer_user_id: UUID | None,
        page: int,
        page_size: int,
    ) -> CommunityPostPage:
        async with self._session.begin():
            record = await self._repository.get_member_by_username(username)
            if record is None:
                raise CommunityNotFoundError()
            items, total = await self._repository.list_member_posts(
                record.user.id,
                viewer_user_id=viewer_user_id,
                offset=(page - 1) * page_size,
                limit=page_size,
            )
            return CommunityPostPage(items=items, total=total)

    async def bookmarks(
        self,
        principal: AuthPrincipal,
        *,
        page: int,
        page_size: int,
    ) -> CommunityPostPage:
        async with self._session.begin():
            await self._ensure_community_profile(principal.user_id)
            items, total = await self._repository.list_bookmarks(
                principal.user_id,
                viewer_user_id=principal.user_id,
                offset=(page - 1) * page_size,
                limit=page_size,
            )
            return CommunityPostPage(items=items, total=total)

    async def set_follow(
        self,
        principal: AuthPrincipal,
        member_id: UUID,
        *,
        is_following: bool,
    ) -> int:
        if member_id == principal.user_id:
            raise CommunityConflictError()
        async with self._session.begin():
            member = await self._repository.get_active_user(member_id)
            if member is None:
                raise CommunityNotFoundError()
            follower_profile = await self._ensure_community_profile(principal.user_id)
            await self._ensure_community_profile(member_id)
            relation = await self._repository.get_follow(
                principal.user_id,
                member_id,
            )
            if is_following and relation is None:
                follow = CommunityFollow(
                    id=uuid4(),
                    follower_user_id=principal.user_id,
                    followed_user_id=member_id,
                )
                inserted = await self._insert_if_absent(
                    follow,
                    self._repository.add_follow,
                )
                if inserted:
                    follower_name = (
                        follower_profile.display_name or _DISPLAY_NAME_FALLBACK
                    )
                    await NotificationService(self._session).consume_in_transaction(
                        event_id=follow.id,
                        user_id=member_id,
                        event_type="COMMUNITY_FOLLOW",
                        title="Bạn có người theo dõi mới",
                        body=f"{follower_name} đã theo dõi bạn.",
                        data={
                            "actionPath": (
                                "/community/members/"
                                f"{quote(follower_profile.username, safe='-._~')}"
                            )
                        },
                    )
            elif not is_following and relation is not None:
                await self._session.delete(relation)
                await self._session.flush()
            return await self._repository.follower_count(member_id)

    async def _member_view(
        self,
        record: CommunityMemberRecord,
        viewer_user_id: UUID | None,
    ) -> CommunityMemberView:
        metrics = await self._repository.member_metrics(
            record.user.id,
            viewer_user_id=viewer_user_id,
        )
        return CommunityMemberView(record, *metrics)

    async def _ensure_community_profile(self, user_id: UUID) -> CommunityProfile:
        profile = await self._repository.get_profile(user_id)
        if profile is not None:
            return profile
        profile = CommunityProfile(
            user_id=user_id,
            username=f"member-{user_id.hex}",
        )
        try:
            async with self._session.begin_nested():
                self._repository.add_profile(profile)
                await self._session.flush()
        except IntegrityError:
            profile = await self._repository.get_profile(user_id)
            if profile is None:
                raise
        return profile

    async def _ensure_not_restricted(self, user_id: UUID, scope: str) -> None:
        now = datetime.now(UTC)
        restriction_id = await self._session.scalar(
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
        if restriction_id is not None:
            raise CommunityForbiddenError()

    @staticmethod
    def _require_comment_owner(
        comment: CommunityComment | None,
        principal: AuthPrincipal,
    ) -> None:
        if comment is None:
            raise CommunityNotFoundError()
        if comment.author_user_id != principal.user_id:
            raise CommunityForbiddenError()

    async def _insert_if_absent(self, relation: object, add) -> bool:
        try:
            async with self._session.begin_nested():
                add(relation)
                await self._session.flush()
        except IntegrityError:
            return False
        return True
