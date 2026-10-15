import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import quote
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.authorization import AuthorizationPolicy, PolicyRequirement
from app.modules.auth.errors import UnauthenticatedError
from app.modules.auth.session_service import AuthPrincipal
from app.modules.community.errors import (
    CommunityConflictError,
    CommunityForbiddenError,
    CommunityNotFoundError,
    CommunityValidationError,
)
from app.modules.community.mentions import extract_community_mentions
from app.modules.community.models import (
    CommunityCategory,
    CommunityModerationAction,
    CommunityModerationEvent,
    CommunityModerationEventAction,
    CommunityModerationLog,
    CommunityPost,
    CommunityPostStatus,
    CommunityProfile,
    CommunitySettings,
)
from app.modules.community.repository import CommunityPostRow, CommunityRepository
from app.modules.community.schemas import CommunityPostRequest
from app.modules.media.types import (
    COMMUNITY_POST_IMAGE_MAX_BYTES,
    COMMUNITY_POST_IMAGE_MAX_COUNT,
)
from app.modules.notifications.service import NotificationService

MODERATE_COMMUNITY = PolicyRequirement(permission="community.moderate")


@dataclass(frozen=True, slots=True)
class CommunityPostPage:
    items: tuple[CommunityPostRow, ...]
    total: int


class CommunityService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        image_max_count: int = COMMUNITY_POST_IMAGE_MAX_COUNT,
        image_max_bytes: int = COMMUNITY_POST_IMAGE_MAX_BYTES,
    ) -> None:
        self._session = session
        self._image_max_count = image_max_count
        self._repository = CommunityRepository(
            session,
            image_max_count=image_max_count,
            image_max_bytes=image_max_bytes,
        )

    async def list_categories(self) -> tuple[CommunityCategory, ...]:
        async with self._session.begin():
            return await self._repository.list_active_categories()

    async def list_public_posts(
        self,
        *,
        category_slug: str | None,
        tag_slug: str | None = None,
        related_work_id: UUID | None = None,
        query: str | None = None,
        sort: str = "recent",
        page: int,
        page_size: int,
        viewer_user_id: UUID | None = None,
    ) -> CommunityPostPage:
        if sort == "following" and viewer_user_id is None:
            raise UnauthenticatedError()
        if query is not None:
            query = query.strip()
            if not query:
                raise CommunityValidationError()
        async with self._session.begin():
            items, total = await self._repository.list_public_posts(
                category_slug=category_slug,
                tag_slug=tag_slug,
                related_work_id=related_work_id,
                query=query,
                sort=sort,
                following_user_id=(
                    viewer_user_id if sort == "following" else None
                ),
                viewer_user_id=viewer_user_id,
                offset=(page - 1) * page_size,
                limit=page_size,
            )
        return CommunityPostPage(items=items, total=total)

    async def list_owned_posts(
        self,
        principal: AuthPrincipal,
        *,
        status: CommunityPostStatus | None,
        page: int,
        page_size: int,
    ) -> CommunityPostPage:
        async with self._session.begin():
            items, total = await self._repository.list_owned_posts(
                principal.user_id,
                status=status,
                offset=(page - 1) * page_size,
                limit=page_size,
            )
        return CommunityPostPage(items=items, total=total)

    async def get_owned_post(
        self,
        principal: AuthPrincipal,
        post_id: UUID,
    ) -> CommunityPostRow:
        async with self._session.begin():
            row = await self._repository.get_owned_post_row(
                post_id,
                user_id=principal.user_id,
            )
        if row is None:
            raise CommunityNotFoundError()
        return row

    async def get_public_post(
        self, slug: str, *, viewer_user_id: UUID | None = None
    ) -> CommunityPostRow:
        async with self._session.begin():
            row = await self._repository.get_public_post(
                slug,
                viewer_user_id=viewer_user_id,
            )
        if row is None:
            raise CommunityNotFoundError()
        return row

    async def create_draft(
        self,
        principal: AuthPrincipal,
        payload: CommunityPostRequest,
    ) -> CommunityPostRow:
        self._validate_image_count(payload)
        async with self._session.begin():
            await self._ensure_not_restricted(principal.user_id, "POSTS")
            category = await self._active_category(payload.category_id)
            await self._validate_related_work(payload.related_work_id)
            post = self._new_post(principal, payload, category)
            self._repository.add_post(post)
            await self._session.flush()
            await self._repository.replace_post_tags(
                post_id=post.id,
                labels=payload.tags,
            )
            await self._repository.replace_post_images(
                post_id=post.id,
                media_ids=payload.image_media_ids,
                owner_user_id=principal.user_id,
            )
            await self._ensure_community_profile(principal.user_id)
            row = await self._repository.get_post_row(post.id)
            if row is None:
                raise CommunityNotFoundError()
            return row

    async def submit(
        self,
        principal: AuthPrincipal,
        post_id: UUID,
        *,
        request_id: str,
    ) -> CommunityPostRow:
        async with self._session.begin():
            post = await self._owned_post(principal, post_id, for_update=True)
            if post.status is not CommunityPostStatus.DRAFT:
                raise CommunityConflictError()
            await self._ensure_not_restricted(principal.user_id, "POSTS")
            settings = await self._session.get(CommunitySettings, 1)
            pre_moderation = (
                settings.pre_moderation_enabled if settings is not None else True
            )
            category = await self._repository.get_category(post.category_id)
            if category is None or not category.is_active:
                raise CommunityNotFoundError()
            now = datetime.now(UTC)
            post.status = (
                CommunityPostStatus.PENDING
                if pre_moderation
                else CommunityPostStatus.PUBLISHED
            )
            post.submitted_at = now
            if not pre_moderation:
                post.published_at = now
            post.updated_at = now
            post.moderation_reason = None
            event_id = self._log(
                post,
                principal,
                (
                    CommunityModerationAction.SUBMITTED
                    if pre_moderation
                    else CommunityModerationAction.PUBLISHED
                ),
                reason=None,
                request_id=request_id,
            )
            await self._session.flush()
            if not pre_moderation:
                await self._notify_post_mentions(post, event_id=event_id)
            row = await self._repository.get_post_row(post.id)
            if row is None:
                raise CommunityNotFoundError()
            return row

    async def update_post(
        self,
        principal: AuthPrincipal,
        post_id: UUID,
        payload: CommunityPostRequest,
    ) -> CommunityPostRow:
        self._validate_image_count(payload)
        async with self._session.begin():
            post = await self._owned_post(principal, post_id, for_update=True)
            if post.status not in {
                CommunityPostStatus.DRAFT,
                CommunityPostStatus.REJECTED,
            }:
                raise CommunityConflictError()
            await self._ensure_not_restricted(principal.user_id, "POSTS")
            category = await self._active_category(payload.category_id)
            await self._validate_related_work(payload.related_work_id)
            was_rejected = post.status is CommunityPostStatus.REJECTED
            post.title = payload.title
            post.content = payload.content
            post.excerpt = _excerpt(payload.content)
            post.category_id = category.id
            post.related_work_id = payload.related_work_id
            post.slug = _slug(payload.title, post.id)
            post.updated_at = datetime.now(UTC)
            await self._repository.replace_post_tags(
                post_id=post.id,
                labels=payload.tags,
            )
            await self._repository.replace_post_images(
                post_id=post.id,
                media_ids=payload.image_media_ids,
                owner_user_id=principal.user_id,
            )
            if was_rejected:
                post.status = CommunityPostStatus.DRAFT
                post.submitted_at = None
                post.moderation_reason = None
            await self._session.flush()
            await self._ensure_community_profile(principal.user_id)
            row = await self._repository.get_post_row(post.id)
            if row is None:
                raise CommunityNotFoundError()
            return row

    async def delete_post(
        self,
        principal: AuthPrincipal,
        post_id: UUID,
        *,
        request_id: str,
    ) -> None:
        async with self._session.begin():
            post = await self._owned_post(principal, post_id, for_update=True)
            if post.status is CommunityPostStatus.DELETED:
                raise CommunityConflictError()
            now = datetime.now(UTC)
            post.status = CommunityPostStatus.DELETED
            post.deleted_at = now
            post.updated_at = now
            self._log(
                post,
                principal,
                CommunityModerationAction.OWNER_DELETED,
                reason=None,
                request_id=request_id,
            )

    async def moderation_queue(
        self,
        principal: AuthPrincipal,
        *,
        page: int,
        page_size: int,
    ) -> CommunityPostPage:
        self._require_moderator(principal)
        async with self._session.begin():
            items, total = await self._repository.list_moderation_queue(
                offset=(page - 1) * page_size,
                limit=page_size,
            )
        return CommunityPostPage(items=items, total=total)

    async def publish(
        self,
        principal: AuthPrincipal,
        post_id: UUID,
        *,
        reason: str,
        request_id: str,
    ) -> CommunityPostRow:
        return await self._moderate(
            principal,
            post_id,
            status=CommunityPostStatus.PUBLISHED,
            action=CommunityModerationAction.PUBLISHED,
            reason=reason,
            request_id=request_id,
        )

    async def reject(
        self,
        principal: AuthPrincipal,
        post_id: UUID,
        *,
        reason: str,
        request_id: str,
    ) -> CommunityPostRow:
        return await self._moderate(
            principal,
            post_id,
            status=CommunityPostStatus.REJECTED,
            action=CommunityModerationAction.REJECTED,
            reason=reason,
            request_id=request_id,
        )

    async def _moderate(
        self,
        principal: AuthPrincipal,
        post_id: UUID,
        *,
        status: CommunityPostStatus,
        action: CommunityModerationAction,
        reason: str,
        request_id: str,
    ) -> CommunityPostRow:
        self._require_moderator(principal)
        async with self._session.begin():
            post = await self._repository.get_post(post_id, for_update=True)
            if post is None or post.status is CommunityPostStatus.DELETED:
                raise CommunityNotFoundError()
            if post.status is not CommunityPostStatus.PENDING:
                raise CommunityConflictError()
            category = await self._repository.get_category(post.category_id)
            if category is None:
                raise CommunityNotFoundError()
            if status is CommunityPostStatus.PUBLISHED and not category.is_active:
                raise CommunityConflictError()
            post.status = status
            post.moderation_reason = reason
            now = datetime.now(UTC)
            post.updated_at = now
            if status is CommunityPostStatus.PUBLISHED:
                post.published_at = now
            event_id = self._log(
                post,
                principal,
                action,
                reason=reason,
                request_id=request_id,
            )
            await self._session.flush()
            await self._notify_post_author(
                post,
                principal,
                event_id=event_id,
                published=status is CommunityPostStatus.PUBLISHED,
            )
            if status is CommunityPostStatus.PUBLISHED:
                await self._notify_post_mentions(post, event_id=event_id)
            row = await self._repository.get_post_row(post.id)
            if row is None:
                raise CommunityNotFoundError()
            return row

    async def _active_category(self, category_id: UUID) -> CommunityCategory:
        category = await self._repository.get_category(category_id, active_only=True)
        if category is None:
            raise CommunityNotFoundError()
        return category

    async def _validate_related_work(self, work_id: UUID | None) -> None:
        if work_id is not None:
            work = await self._repository.get_public_related_work(work_id)
            if work is None:
                raise CommunityNotFoundError()

    def _validate_image_count(self, payload: CommunityPostRequest) -> None:
        if len(payload.image_media_ids) > self._image_max_count:
            raise CommunityValidationError()

    async def _ensure_not_restricted(self, user_id: UUID, scope: str) -> None:
        if await self._repository.is_member_restricted(user_id, scope):
            raise CommunityForbiddenError()

    async def _ensure_community_profile(self, user_id: UUID) -> CommunityProfile:
        profile = await self._repository.get_community_profile(user_id)
        if profile is None:
            profile = CommunityProfile(
                user_id=user_id,
                username=f"member-{user_id.hex}",
            )
            self._repository.add_community_profile(profile)
            await self._session.flush()
        return profile

    async def _owned_post(
        self,
        principal: AuthPrincipal,
        post_id: UUID,
        *,
        for_update: bool,
    ) -> CommunityPost:
        post = await self._repository.get_post(post_id, for_update=for_update)
        if post is None or post.status is CommunityPostStatus.DELETED:
            raise CommunityNotFoundError()
        if post.author_user_id != principal.user_id:
            raise CommunityForbiddenError()
        return post

    @staticmethod
    def _new_post(
        principal: AuthPrincipal,
        payload: CommunityPostRequest,
        category: CommunityCategory,
    ) -> CommunityPost:
        post_id = uuid4()
        return CommunityPost(
            id=post_id,
            author_user_id=principal.user_id,
            category_id=category.id,
            related_work_id=payload.related_work_id,
            title=payload.title,
            slug=_slug(payload.title, post_id),
            content=payload.content,
            excerpt=_excerpt(payload.content),
            status=CommunityPostStatus.DRAFT,
        )

    def _log(
        self,
        post: CommunityPost,
        principal: AuthPrincipal,
        action: CommunityModerationAction,
        *,
        reason: str | None,
        request_id: str,
    ) -> UUID:
        self._repository.add_moderation_log(
            CommunityModerationLog(
                post_id=post.id,
                actor_user_id=principal.user_id,
                action=action,
                reason=reason,
                request_id=request_id,
            )
        )
        event_id = uuid4()
        self._session.add(
            CommunityModerationEvent(
                id=event_id,
                target_type="POST",
                target_id=str(post.id),
                action=CommunityModerationEventAction(action.value).value,
                actor_user_id=principal.user_id,
                reason=reason,
                request_id=request_id,
            )
        )
        return event_id

    async def _notify_post_author(
        self,
        post: CommunityPost,
        actor: AuthPrincipal,
        *,
        event_id: UUID,
        published: bool,
    ) -> None:
        if post.author_user_id == actor.user_id:
            return
        event_type = (
            "COMMUNITY_POST_PUBLISHED"
            if published
            else "COMMUNITY_POST_REJECTED"
        )
        title = "Bài viết đã được duyệt" if published else "Bài viết chưa được duyệt"
        body = (
            f'Bài viết “{post.title}” đã được duyệt.'
            if published
            else f'Bài viết “{post.title}” chưa được duyệt.'
        )
        action_path = (
            f"/community/posts/{quote(post.slug, safe='-._~')}"
            if published
            else "/community/new"
        )
        await NotificationService(self._session).consume_in_transaction(
            event_id=event_id,
            user_id=post.author_user_id,
            event_type=event_type,
            title=title,
            body=body,
            data={"actionPath": action_path},
        )

    async def _notify_post_mentions(
        self,
        post: CommunityPost,
        *,
        event_id: UUID,
    ) -> None:
        mentioned_user_ids = await self._repository.list_active_mention_recipients(
            extract_community_mentions(post.content)
        )
        for user_id in mentioned_user_ids:
            if user_id == post.author_user_id:
                continue
            await NotificationService(self._session).consume_in_transaction(
                event_id=event_id,
                user_id=user_id,
                event_type="COMMUNITY_MENTION",
                title="Báº¡n Ä‘Æ°á»£c nháº¯c Ä‘áº¿n trong cá»™ng Ä‘á»“ng",
                body="CÃ³ thÃ nh viÃªn nháº¯c Ä‘áº¿n báº¡n trong má»™t bÃ i viáº¿t.",
                data={
                    "actionPath": (
                        f"/community/posts/{quote(post.slug, safe='-._~')}"
                    )
                },
            )

    @staticmethod
    def _require_moderator(principal: AuthPrincipal) -> None:
        AuthorizationPolicy.require_capability(
            principal,
            MODERATE_COMMUNITY,
            CommunityForbiddenError,
        )


def _slug(title: str, post_id: UUID) -> str:
    title_ascii = title.replace("đ", "d").replace("Đ", "D")
    normalized = unicodedata.normalize("NFKD", title_ascii)
    ascii_title = normalized.encode("ascii", "ignore").decode().lower()
    base = re.sub(r"[^a-z0-9]+", "-", ascii_title).strip("-") or "bai-viet"
    return f"{base[:190].rstrip('-')}-{post_id.hex[:8]}"


def _excerpt(content: str) -> str:
    return re.sub(r"\s+", " ", content).strip()[:320]
