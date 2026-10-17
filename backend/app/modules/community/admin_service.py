from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.authorization import AuthorizationPolicy, PolicyRequirement
from app.modules.auth.session_service import AuthPrincipal
from app.modules.community.admin_repository import (
    CommunityAdminCommentRow,
    CommunityAdminMemberPage,
    CommunityAdminRepository,
    CommunityModerationEventPage,
    CommunityReportPage,
    CommunityReportRow,
    CommunityRestrictionPage,
    CommunityRestrictionRow,
)
from app.modules.community.admin_schemas import (
    CommunityCategoryCreateRequest,
    CommunityCategoryPatchRequest,
    CommunityMemberRestrictionCreateRequest,
    CommunityMemberRestrictionRevokeRequest,
    CommunityReportRequest,
    CommunityReportResolutionRequest,
)
from app.modules.community.errors import (
    CommunityConflictError,
    CommunityForbiddenError,
    CommunityNotFoundError,
)
from app.modules.community.models import (
    CommunityCategory,
    CommunityMemberRestriction,
    CommunityModerationEvent,
    CommunityModerationEventAction,
    CommunityPost,
    CommunityPostStatus,
    CommunityReport,
    CommunityReportResolution,
    CommunityReportStatus,
)
from app.modules.community.repository import CommunityPostRow, CommunityRepository
from app.modules.community.service import CommunityMediaAssetDeleter, CommunityService
from app.modules.media.errors import MediaInvalidStateError
from app.modules.notifications.service import NotificationService

_MODERATE = PolicyRequirement(permission="community.moderate")
_MANAGE = PolicyRequirement(permission="community.manage")
_DELETED_COMMENT = "Bình luận đã bị xóa."
_HIDDEN_COMMENT = "Bình luận đã bị ẩn."


@dataclass(frozen=True, slots=True)
class CommunityReportSubmission:
    row: CommunityReportRow
    created: bool


@dataclass(frozen=True, slots=True)
class CommunityAdminCommentPage:
    items: tuple[CommunityAdminCommentRow, ...]
    total: int


@dataclass(frozen=True, slots=True)
class CommunityAdminPostResultPage:
    items: tuple[CommunityPostRow, ...]
    total: int


class CommunityAdminService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = CommunityAdminRepository(session)

    async def report_post(
        self,
        principal: AuthPrincipal,
        post_id: UUID,
        payload: CommunityReportRequest,
        *,
        request_id: str,
    ) -> CommunityReportSubmission:
        return await self._report(
            principal,
            post_id=post_id,
            comment_id=None,
            payload=payload,
            request_id=request_id,
        )

    async def report_comment(
        self,
        principal: AuthPrincipal,
        comment_id: UUID,
        payload: CommunityReportRequest,
        *,
        request_id: str,
    ) -> CommunityReportSubmission:
        return await self._report(
            principal,
            post_id=None,
            comment_id=comment_id,
            payload=payload,
            request_id=request_id,
        )

    async def _report(
        self,
        principal: AuthPrincipal,
        *,
        post_id: UUID | None,
        comment_id: UUID | None,
        payload: CommunityReportRequest,
        request_id: str,
    ) -> CommunityReportSubmission:
        async with self._session.begin():
            existing = await self._repository.get_open_report(
                principal.user_id,
                post_id=post_id,
                comment_id=comment_id,
            )
            if existing is not None:
                row = await self._repository.get_report_row(existing.id)
                if row is None:
                    raise CommunityNotFoundError()
                return CommunityReportSubmission(row, False)
            if post_id is not None:
                if await self._repository.get_public_post(post_id) is None:
                    raise CommunityNotFoundError()
            elif comment_id is not None:
                if await self._repository.get_public_comment(comment_id) is None:
                    raise CommunityNotFoundError()
            else:
                raise CommunityNotFoundError()
            report = CommunityReport(
                id=uuid4(),
                reporter_user_id=principal.user_id,
                post_id=post_id,
                comment_id=comment_id,
                reason=payload.reason,
                details=payload.details,
                status=CommunityReportStatus.OPEN.value,
                request_id=request_id,
            )
            try:
                async with self._session.begin_nested():
                    self._repository.add_report(report)
                    await self._session.flush()
            except IntegrityError:
                duplicate = await self._repository.get_open_report(
                    principal.user_id,
                    post_id=post_id,
                    comment_id=comment_id,
                )
                if duplicate is None:
                    raise
                report = duplicate
                created = False
            else:
                created = True
            row = await self._repository.get_report_row(report.id)
            if row is None:
                raise CommunityNotFoundError()
            return CommunityReportSubmission(row, created)

    async def list_reports(
        self,
        principal: AuthPrincipal,
        *,
        status: str,
        page: int,
        page_size: int,
    ) -> CommunityReportPage:
        self._require(principal, _MODERATE)
        async with self._session.begin():
            return await self._repository.list_reports(
                status=status,
                offset=(page - 1) * page_size,
                limit=page_size,
            )

    async def resolve_report(
        self,
        principal: AuthPrincipal,
        report_id: UUID,
        payload: CommunityReportResolutionRequest,
        *,
        request_id: str,
    ) -> CommunityReportRow:
        self._require(principal, _MODERATE)
        async with self._session.begin():
            report = await self._repository.get_report_for_update(report_id)
            if report is None:
                raise CommunityNotFoundError()
            if report.status != CommunityReportStatus.OPEN.value:
                raise CommunityConflictError()
            now = datetime.now(UTC)
            removed_post: CommunityPost | None = None
            removal_event: CommunityModerationEvent | None = None
            if payload.action == CommunityReportResolution.HIDE.value:
                if report.post_id is not None:
                    post = await self._repository.get_post(
                        report.post_id,
                        for_update=True,
                    )
                    if post is None or post.status is not CommunityPostStatus.PUBLISHED:
                        raise CommunityConflictError()
                    post.status = CommunityPostStatus.HIDDEN
                    post.moderation_reason = payload.reason
                    post.updated_at = now
                    removed_post = post
                    removal_event = self._event(
                        principal,
                        target_type="POST",
                        target_id=str(post.id),
                        action=CommunityModerationEventAction.POST_HIDDEN,
                        reason=payload.reason,
                        request_id=request_id,
                        report_id=report.id,
                    )
                else:
                    if report.comment_id is None:
                        raise CommunityConflictError()
                    comment = await self._repository.get_comment(
                        report.comment_id, for_update=True
                    )
                    if (
                        comment is None
                        or comment.deleted_at is not None
                        or comment.moderation_hidden_at is not None
                    ):
                        raise CommunityConflictError()
                    comment.moderation_hidden_at = now
                    self._event(
                        principal,
                        target_type="COMMENT",
                        target_id=str(comment.id),
                        action=CommunityModerationEventAction.COMMENT_HIDDEN,
                        reason=payload.reason,
                        request_id=request_id,
                        report_id=report.id,
                    )
                report.status = CommunityReportStatus.RESOLVED.value
            else:
                report.status = CommunityReportStatus.DISMISSED.value
                self._event(
                    principal,
                    target_type="POST" if report.post_id is not None else "COMMENT",
                    target_id=str(report.post_id or report.comment_id),
                    action=CommunityModerationEventAction.REPORT_DISMISSED,
                    reason=payload.reason,
                    request_id=request_id,
                    report_id=report.id,
                )
            report.resolution_action = payload.action
            report.resolution_reason = payload.reason
            report.resolved_at = now
            report.resolved_by_user_id = principal.user_id
            report.resolved_request_id = request_id
            await self._session.flush()
            if removed_post is not None and removal_event is not None:
                await self._notify_post_removed(
                    removed_post,
                    event_id=removal_event.id,
                    reason=payload.reason,
                )
            row = await self._repository.get_report_row(report.id)
            if row is None:
                raise CommunityNotFoundError()
            return row

    async def set_post_visibility(
        self,
        principal: AuthPrincipal,
        post_id: UUID,
        *,
        visible: bool,
        reason: str,
        request_id: str,
    ) -> str:
        self._require(principal, _MODERATE)
        async with self._session.begin():
            post = await self._repository.get_post(post_id, for_update=True)
            if post is None or post.status is CommunityPostStatus.DELETED:
                raise CommunityNotFoundError()
            category = await self._repository.get_category(post.category_id)
            if visible:
                if post.status is not CommunityPostStatus.HIDDEN:
                    raise CommunityConflictError()
                if category is None or not category.is_active:
                    raise CommunityConflictError()
                post.status = CommunityPostStatus.PUBLISHED
                action = CommunityModerationEventAction.POST_RESTORED
                state = "VISIBLE"
                post.moderation_reason = None
            else:
                if post.status is not CommunityPostStatus.PUBLISHED:
                    raise CommunityConflictError()
                post.status = CommunityPostStatus.HIDDEN
                action = CommunityModerationEventAction.POST_HIDDEN
                state = "HIDDEN"
                post.moderation_reason = reason
            post.updated_at = datetime.now(UTC)
            event = self._event(
                principal,
                target_type="POST",
                target_id=str(post.id),
                action=action,
                reason=reason,
                request_id=request_id,
            )
            await self._session.flush()
            if not visible:
                await self._notify_post_removed(
                    post,
                    event_id=event.id,
                    reason=reason,
                )
            return state

    async def list_admin_posts(
        self,
        principal: AuthPrincipal,
        *,
        query: str | None,
        status: str | None,
        page: int,
        page_size: int,
    ) -> CommunityAdminPostResultPage:
        self._require(principal, _MODERATE)
        async with self._session.begin():
            items, total = await self._repository.list_admin_posts(
                query=query,
                status=status,
                offset=(page - 1) * page_size,
                limit=page_size,
            )
        return CommunityAdminPostResultPage(items=items, total=total)

    async def list_admin_comments(
        self,
        principal: AuthPrincipal,
        *,
        query: str | None,
        post_id: UUID | None,
        author_username: str | None,
        visibility: str,
        page: int,
        page_size: int,
    ) -> CommunityAdminCommentPage:
        self._require(principal, _MODERATE)
        async with self._session.begin():
            items, total = await self._repository.list_admin_comments(
                query=query,
                post_id=post_id,
                author_username=author_username,
                visibility=visibility,
                offset=(page - 1) * page_size,
                limit=page_size,
            )
        return CommunityAdminCommentPage(items, total)

    async def set_post_pinned(
        self,
        principal: AuthPrincipal,
        post_id: UUID,
        *,
        pinned: bool,
        reason: str,
        request_id: str,
    ) -> bool:
        self._require(principal, _MODERATE)
        async with self._session.begin():
            post = await self._repository.get_post(post_id, for_update=True)
            if post is None:
                raise CommunityNotFoundError()
            if await self._repository.get_public_post(post_id) is None:
                raise CommunityConflictError()
            if pinned:
                if post.pinned_at is not None:
                    raise CommunityConflictError()
                post.pinned_at = datetime.now(UTC)
                action = CommunityModerationEventAction.POST_PINNED
            else:
                if post.pinned_at is None:
                    raise CommunityConflictError()
                post.pinned_at = None
                action = CommunityModerationEventAction.POST_UNPINNED
            self._event(
                principal,
                target_type="POST",
                target_id=str(post.id),
                action=action,
                reason=reason,
                request_id=request_id,
            )
            await self._session.flush()
            return post.pinned_at is not None

    async def set_comments_locked(
        self,
        principal: AuthPrincipal,
        post_id: UUID,
        *,
        locked: bool,
        reason: str,
        request_id: str,
    ) -> bool:
        self._require(principal, _MODERATE)
        async with self._session.begin():
            post = await self._repository.get_post(post_id, for_update=True)
            if post is None or post.status is CommunityPostStatus.DELETED:
                raise CommunityNotFoundError()
            if locked == (post.comments_locked_at is not None):
                raise CommunityConflictError()
            post.comments_locked_at = datetime.now(UTC) if locked else None
            self._event(
                principal,
                target_type="POST",
                target_id=str(post.id),
                action=(
                    CommunityModerationEventAction.COMMENTS_LOCKED
                    if locked
                    else CommunityModerationEventAction.COMMENTS_UNLOCKED
                ),
                reason=reason,
                request_id=request_id,
            )
            await self._session.flush()
            return post.comments_locked_at is not None

    async def admin_delete_post(
        self,
        principal: AuthPrincipal,
        post_id: UUID,
        *,
        reason: str,
        request_id: str,
        media_asset_deleter: CommunityMediaAssetDeleter,
    ) -> datetime:
        self._require(principal, _MODERATE)
        media_ids: tuple[UUID, ...]
        async with self._session.begin():
            post = await self._repository.get_post(post_id, for_update=True)
            if post is None:
                raise CommunityNotFoundError()
            if post.admin_deleted:
                event = await self._session.scalar(
                    select(CommunityModerationEvent)
                    .where(
                        CommunityModerationEvent.target_type == "POST",
                        CommunityModerationEvent.target_id == str(post_id),
                        CommunityModerationEvent.action
                        == CommunityModerationEventAction.POST_ADMIN_DELETED.value,
                    )
                    .order_by(CommunityModerationEvent.created_at.desc())
                    .limit(1)
                    .with_for_update()
                )
                if event is None:
                    raise CommunityConflictError()
                event.reason = None
                event.event_data = None
                event.report_id = None
                now = post.deleted_at or datetime.now(UTC)
            elif (
                post.status is CommunityPostStatus.DELETED
                or post.deleted_at is not None
            ):
                raise CommunityConflictError()
            else:
                now = datetime.now(UTC)
                post.admin_deleted = True
                post.status = CommunityPostStatus.DELETED
                post.deleted_at = now
                post.updated_at = now
                event = self._event(
                    principal,
                    target_type="POST",
                    target_id=str(post.id),
                    action=CommunityModerationEventAction.POST_ADMIN_DELETED,
                    reason=None,
                    request_id=request_id,
                )
            owner_user_id = post.author_user_id
            deletion_event_id = event.id
            media_ids = await CommunityRepository(self._session).list_owned_post_media(
                post.id, owner_user_id
            )
            await self._session.flush()

        for media_id in media_ids:
            try:
                await media_asset_deleter.delete_community_post_asset(
                    principal,
                    media_id,
                    owner_user_id=owner_user_id,
                )
            except MediaInvalidStateError:
                continue

        async with self._session.begin():
            post = await self._repository.get_post(post_id, for_update=True)
            if post is None:
                return now
            await CommunityRepository(self._session).permanently_delete_post_content(
                post_id,
                deletion_event_id=deletion_event_id,
                media_asset_ids=media_ids,
                media_asset_owner_id=owner_user_id,
            )
        return now

    async def purge_legacy_deleted_posts(
        self,
        media_asset_deleter: CommunityMediaAssetDeleter,
        *,
        limit: int = 100,
    ) -> int:
        async with self._session.begin():
            rows = await self._session.execute(
                select(
                    CommunityPost.id,
                    CommunityPost.author_user_id,
                    CommunityPost.admin_deleted,
                )
                .where(
                    CommunityPost.status == CommunityPostStatus.DELETED,
                    CommunityPost.deleted_at.is_not(None),
                )
                .order_by(CommunityPost.deleted_at, CommunityPost.id)
                .limit(limit)
            )
            candidates = tuple(rows.all())

        purged = 0
        for post_id, owner_user_id, admin_deleted in candidates:
            expected_action = (
                CommunityModerationEventAction.POST_ADMIN_DELETED.value
                if admin_deleted
                else CommunityModerationEventAction.OWNER_DELETED.value
            )
            async with self._session.begin():
                event_row = await self._session.execute(
                    select(
                        CommunityModerationEvent.actor_user_id,
                        CommunityModerationEvent.request_id,
                    )
                    .where(
                        CommunityModerationEvent.target_type == "POST",
                        CommunityModerationEvent.target_id == str(post_id),
                        CommunityModerationEvent.action == expected_action,
                    )
                    .order_by(CommunityModerationEvent.created_at.desc())
                    .limit(1)
                )
                event_data = event_row.first()
            if event_data is None:
                continue
            event_actor_id, event_request_id = event_data

            if admin_deleted:
                actor = AuthPrincipal(
                    user_id=event_actor_id,
                    session_id=uuid4(),
                    email="community-retention@system.invalid",
                    roles=(),
                    permissions=("community.moderate",),
                )
                await self.admin_delete_post(
                    actor,
                    post_id,
                    reason="",
                    request_id=event_request_id,
                    media_asset_deleter=media_asset_deleter,
                )
            else:
                owner = AuthPrincipal(
                    user_id=owner_user_id,
                    session_id=uuid4(),
                    email="community-retention@system.invalid",
                    roles=(),
                )
                await CommunityService(self._session).delete_post(
                    owner,
                    post_id,
                    request_id=event_request_id,
                    media_asset_deleter=media_asset_deleter,
                )
            purged += 1
        return purged

    async def admin_restore_post(
        self,
        principal: AuthPrincipal,
        post_id: UUID,
        *,
        reason: str,
        request_id: str,
    ) -> str:
        self._require(principal, _MODERATE)
        async with self._session.begin():
            post = await self._repository.get_post(post_id, for_update=True)
            if post is None:
                raise CommunityNotFoundError()
            if not post.admin_deleted or post.pre_delete_status is None:
                raise CommunityConflictError()
            restored_status = CommunityPostStatus(post.pre_delete_status)
            if restored_status is CommunityPostStatus.DELETED:
                raise CommunityConflictError()
            post.status = restored_status
            post.admin_deleted = False
            post.deleted_at = None
            post.pre_delete_status = None
            post.updated_at = datetime.now(UTC)
            self._event(
                principal,
                target_type="POST",
                target_id=str(post.id),
                action=CommunityModerationEventAction.POST_ADMIN_RESTORED,
                reason=reason,
                request_id=request_id,
                event_data={"restoredStatus": restored_status.value},
            )
            await self._session.flush()
            return restored_status.value

    async def restore_post_moderation_state(
        self,
        principal: AuthPrincipal,
        post_id: UUID,
        *,
        reason: str,
        request_id: str,
    ) -> tuple[bool, str]:
        """Restore post visibility after a moderation hide."""
        self._require(principal, _MODERATE)
        async with self._session.begin():
            post = await self._repository.get_post(post_id, for_update=True)
            if post is None:
                raise CommunityNotFoundError()
            if post.admin_deleted:
                raise CommunityConflictError()
            if (
                post.deleted_at is not None
                or post.status is not CommunityPostStatus.HIDDEN
            ):
                raise CommunityConflictError()
            category = await self._repository.get_category(post.category_id)
            if category is None or not category.is_active:
                raise CommunityConflictError()
            post.status = CommunityPostStatus.PUBLISHED
            post.moderation_reason = None
            post.updated_at = datetime.now(UTC)
            self._event(
                principal,
                target_type="POST",
                target_id=str(post.id),
                action=CommunityModerationEventAction.POST_RESTORED,
                reason=reason,
                request_id=request_id,
            )
            await self._session.flush()
            return False, "VISIBLE"

    async def admin_delete_comment(
        self,
        principal: AuthPrincipal,
        comment_id: UUID,
        *,
        reason: str,
        request_id: str,
    ) -> str:
        self._require(principal, _MODERATE)
        async with self._session.begin():
            comment = await self._repository.get_comment(comment_id, for_update=True)
            if comment is None:
                raise CommunityNotFoundError()
            if comment.deleted_at is not None:
                raise CommunityConflictError()
            comment.pre_delete_hidden_at = comment.moderation_hidden_at
            comment.admin_deleted = True
            comment.deleted_at = datetime.now(UTC)
            self._event(
                principal,
                target_type="COMMENT",
                target_id=str(comment.id),
                action=CommunityModerationEventAction.COMMENT_ADMIN_DELETED,
                reason=reason,
                request_id=request_id,
                event_data={
                    "priorVisibility": (
                        "HIDDEN" if comment.moderation_hidden_at else "VISIBLE"
                    )
                },
            )
            await self._session.flush()
            return "DELETED"

    async def list_admin_members(
        self,
        principal: AuthPrincipal,
        *,
        query: str | None,
        page: int,
        page_size: int,
    ) -> CommunityAdminMemberPage:
        self._require(principal, _MODERATE)
        async with self._session.begin():
            return await self._repository.list_admin_members(
                query=query,
                offset=(page - 1) * page_size,
                limit=page_size,
            )

    async def create_member_restriction(
        self,
        principal: AuthPrincipal,
        member_id: UUID,
        payload: CommunityMemberRestrictionCreateRequest,
        *,
        request_id: str,
    ) -> CommunityRestrictionRow:
        self._require(principal, _MODERATE)
        async with self._session.begin():
            member = await self._repository.get_member(member_id)
            if member is None:
                raise CommunityNotFoundError()
            now = datetime.now(UTC)
            restriction = CommunityMemberRestriction(
                id=uuid4(),
                member_user_id=member_id,
                scope=payload.scope,
                reason=payload.reason,
                starts_at=now,
                expires_at=now + timedelta(minutes=payload.duration_minutes),
                actor_user_id=principal.user_id,
                request_id=request_id,
            )
            self._repository.add_restriction(restriction)
            self._event(
                principal,
                target_type="MEMBER",
                target_id=str(member_id),
                action=CommunityModerationEventAction.MEMBER_RESTRICTED,
                reason=payload.reason,
                request_id=request_id,
                event_data={
                    "restrictionId": str(restriction.id),
                    "scope": payload.scope,
                    "expiresAt": restriction.expires_at.isoformat(),
                },
            )
            await self._session.flush()
            row = await self._repository.get_restriction_row(restriction.id)
            if row is None:
                raise CommunityNotFoundError()
            return row

    async def list_member_restrictions(
        self,
        principal: AuthPrincipal,
        member_id: UUID,
        *,
        page: int,
        page_size: int,
    ) -> CommunityRestrictionPage:
        self._require(principal, _MODERATE)
        async with self._session.begin():
            if await self._repository.get_member(member_id) is None:
                raise CommunityNotFoundError()
            return await self._repository.list_member_restrictions(
                member_id,
                offset=(page - 1) * page_size,
                limit=page_size,
            )

    async def revoke_member_restriction(
        self,
        principal: AuthPrincipal,
        member_id: UUID,
        restriction_id: UUID,
        payload: CommunityMemberRestrictionRevokeRequest,
        *,
        request_id: str,
    ) -> CommunityRestrictionRow:
        self._require(principal, _MODERATE)
        async with self._session.begin():
            restriction = await self._repository.get_restriction_for_update(
                member_id, restriction_id
            )
            if restriction is None:
                raise CommunityNotFoundError()
            if restriction.revoked_at is not None or _as_utc(
                restriction.expires_at
            ) <= datetime.now(UTC):
                raise CommunityConflictError()
            now = datetime.now(UTC)
            restriction.revoked_at = now
            restriction.revoked_by_user_id = principal.user_id
            restriction.revocation_reason = payload.reason
            restriction.revoked_request_id = request_id
            self._event(
                principal,
                target_type="MEMBER",
                target_id=str(member_id),
                action=CommunityModerationEventAction.MEMBER_RESTRICTION_REVOKED,
                reason=payload.reason,
                request_id=request_id,
                event_data={
                    "restrictionId": str(restriction.id),
                    "scope": restriction.scope,
                },
            )
            await self._session.flush()
            row = await self._repository.get_restriction_row(restriction.id)
            if row is None:
                raise CommunityNotFoundError()
            return row

    async def set_comment_visibility(
        self,
        principal: AuthPrincipal,
        comment_id: UUID,
        *,
        visible: bool,
        reason: str,
        request_id: str,
    ) -> str:
        self._require(principal, _MODERATE)
        async with self._session.begin():
            comment = await self._repository.get_comment(comment_id, for_update=True)
            if comment is None:
                raise CommunityNotFoundError()
            if comment.deleted_at is not None:
                if not visible or not comment.admin_deleted:
                    raise CommunityConflictError()
                comment.deleted_at = None
                comment.admin_deleted = False
                comment.moderation_hidden_at = comment.pre_delete_hidden_at
                comment.pre_delete_hidden_at = None
                action = CommunityModerationEventAction.COMMENT_ADMIN_RESTORED
                state = (
                    "HIDDEN" if comment.moderation_hidden_at is not None else "VISIBLE"
                )
            elif visible:
                if comment.moderation_hidden_at is None:
                    raise CommunityConflictError()
                comment.moderation_hidden_at = None
                action = CommunityModerationEventAction.COMMENT_RESTORED
                state = "VISIBLE"
            else:
                if comment.moderation_hidden_at is not None:
                    raise CommunityConflictError()
                if await self._repository.get_public_post(comment.post_id) is None:
                    raise CommunityConflictError()
                comment.moderation_hidden_at = datetime.now(UTC)
                action = CommunityModerationEventAction.COMMENT_HIDDEN
                state = "HIDDEN"
            self._event(
                principal,
                target_type="COMMENT",
                target_id=str(comment.id),
                action=action,
                reason=reason,
                request_id=request_id,
            )
            await self._session.flush()
            return state

    async def list_categories(
        self, principal: AuthPrincipal
    ) -> tuple[CommunityCategory, ...]:
        self._require(principal, _MANAGE)
        async with self._session.begin():
            return await self._repository.list_categories()

    async def create_category(
        self,
        principal: AuthPrincipal,
        payload: CommunityCategoryCreateRequest,
        *,
        request_id: str,
    ) -> CommunityCategory:
        self._require(principal, _MANAGE)
        async with self._session.begin():
            if await self._repository.get_category_by_slug(payload.slug) is not None:
                raise CommunityConflictError()
            category = CommunityCategory(
                id=uuid4(),
                name=payload.name,
                slug=payload.slug,
                description=payload.description,
                icon=payload.icon,
                sort_order=payload.sort_order,
                is_active=payload.is_active,
            )
            self._repository.add_category(category)
            self._event(
                principal,
                target_type="CATEGORY",
                target_id=str(category.id),
                action=CommunityModerationEventAction.CATEGORY_CREATED,
                reason=payload.reason,
                request_id=request_id,
                event_data={"slug": category.slug},
            )
            await self._session.flush()
            return category

    async def update_category(
        self,
        principal: AuthPrincipal,
        category_id: UUID,
        payload: CommunityCategoryPatchRequest,
        *,
        request_id: str,
    ) -> CommunityCategory:
        self._require(principal, _MANAGE)
        async with self._session.begin():
            category = await self._repository.get_category(category_id, for_update=True)
            if category is None:
                raise CommunityNotFoundError()
            if payload.slug is not None and payload.slug != category.slug:
                duplicate = await self._repository.get_category_by_slug(payload.slug)
                if duplicate is not None:
                    raise CommunityConflictError()
            previous = {
                "name": category.name,
                "slug": category.slug,
                "description": category.description,
                "icon": category.icon,
                "sortOrder": category.sort_order,
                "isActive": category.is_active,
            }
            editable_fields = (
                "name",
                "slug",
                "description",
                "icon",
                "sort_order",
                "is_active",
            )
            for name in editable_fields:
                value = getattr(payload, name)
                if (
                    name in payload.model_fields_set
                    and value is not None
                    or (name == "icon" and name in payload.model_fields_set)
                ):
                    setattr(category, name, value)
            current = {
                "name": category.name,
                "slug": category.slug,
                "description": category.description,
                "icon": category.icon,
                "sortOrder": category.sort_order,
                "isActive": category.is_active,
            }
            self._event(
                principal,
                target_type="CATEGORY",
                target_id=str(category.id),
                action=CommunityModerationEventAction.CATEGORY_UPDATED,
                reason=payload.reason,
                request_id=request_id,
                event_data={"before": previous, "after": current},
            )
            await self._session.flush()
            return category

    async def list_moderation_events(
        self,
        principal: AuthPrincipal,
        *,
        target_type: str | None,
        target_id: str | None,
        page: int,
        page_size: int,
    ) -> CommunityModerationEventPage:
        self._require(principal, _MODERATE)
        async with self._session.begin():
            return await self._repository.list_moderation_events(
                target_type=target_type,
                target_id=target_id,
                offset=(page - 1) * page_size,
                limit=page_size,
            )

    def _event(
        self,
        principal: AuthPrincipal,
        *,
        target_type: str,
        target_id: str,
        action: CommunityModerationEventAction,
        reason: str | None,
        request_id: str,
        report_id: UUID | None = None,
        event_data: dict[str, object] | None = None,
    ) -> CommunityModerationEvent:
        event = CommunityModerationEvent(
            id=uuid4(),
            target_type=target_type,
            target_id=target_id,
            action=action.value,
            actor_user_id=principal.user_id,
            report_id=report_id,
            reason=reason,
            request_id=request_id,
            event_data=event_data,
        )
        self._repository.add_moderation_event(event)
        return event

    async def _notify_post_removed(
        self,
        post: CommunityPost,
        *,
        event_id: UUID,
        reason: str,
    ) -> None:
        await NotificationService(self._session).consume_in_transaction(
            event_id=event_id,
            user_id=post.author_user_id,
            event_type="COMMUNITY_POST_REMOVED",
            title="Bài viết của bạn đã bị gỡ",
            body=(
                f"Bài viết “{post.title}” đã bị gỡ. Lý do: {reason} "
                "Bạn có thể chỉnh sửa nội dung hoặc liên hệ quản trị viên "
                "nếu cần thêm thông tin."
            ),
            data={
                "actionPath": "/community/mine",
            },
        )

    @staticmethod
    def _require(principal: AuthPrincipal, requirement: PolicyRequirement) -> None:
        AuthorizationPolicy.require_capability(
            principal,
            requirement,
            CommunityForbiddenError,
        )


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
