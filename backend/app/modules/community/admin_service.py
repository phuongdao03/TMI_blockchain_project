from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

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
    CommunitySettingsRequest,
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
    CommunityPostStatus,
    CommunityReport,
    CommunityReportResolution,
    CommunityReportStatus,
    CommunitySettings,
)
from app.modules.community.repository import CommunityPostRow

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
            target = (
                await self._repository.get_public_post(post_id)
                if post_id is not None
                else await self._repository.get_public_comment(comment_id)
            )
            if target is None:
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
                    self._event(
                        principal,
                        target_type="POST",
                        target_id=str(post.id),
                        action=CommunityModerationEventAction.POST_HIDDEN,
                        reason=payload.reason,
                        request_id=request_id,
                        report_id=report.id,
                    )
                else:
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
            self._event(
                principal,
                target_type="POST",
                target_id=str(post.id),
                action=action,
                reason=reason,
                request_id=request_id,
            )
            await self._session.flush()
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
    ) -> datetime:
        self._require(principal, _MODERATE)
        async with self._session.begin():
            post = await self._repository.get_post(post_id, for_update=True)
            if post is None:
                raise CommunityNotFoundError()
            if (
                post.status is CommunityPostStatus.DELETED
                or post.deleted_at is not None
                or post.admin_deleted
            ):
                raise CommunityConflictError()
            now = datetime.now(UTC)
            post.pre_delete_status = post.status.value
            post.admin_deleted = True
            post.status = CommunityPostStatus.DELETED
            post.deleted_at = now
            post.updated_at = now
            self._event(
                principal,
                target_type="POST",
                target_id=str(post.id),
                action=CommunityModerationEventAction.POST_ADMIN_DELETED,
                reason=reason,
                request_id=request_id,
                event_data={"restoredStatus": post.pre_delete_status},
            )
            await self._session.flush()
            return now

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
        """Restore an admin deletion, or retain the hidden-post restore route."""
        self._require(principal, _MODERATE)
        async with self._session.begin():
            post = await self._repository.get_post(post_id, for_update=True)
            if post is None:
                raise CommunityNotFoundError()
            if post.admin_deleted:
                if post.pre_delete_status is None:
                    raise CommunityConflictError()
                restored = CommunityPostStatus(post.pre_delete_status)
                if restored is CommunityPostStatus.DELETED:
                    raise CommunityConflictError()
                post.status = restored
                post.deleted_at = None
                post.admin_deleted = False
                post.pre_delete_status = None
                post.updated_at = datetime.now(UTC)
                self._event(
                    principal,
                    target_type="POST",
                    target_id=str(post.id),
                    action=CommunityModerationEventAction.POST_ADMIN_RESTORED,
                    reason=reason,
                    request_id=request_id,
                    event_data={"restoredStatus": restored.value},
                )
                await self._session.flush()
                return True, restored.value
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
            if (
                restriction.revoked_at is not None
                or _as_utc(restriction.expires_at) <= datetime.now(UTC)
            ):
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
                    "HIDDEN"
                    if comment.moderation_hidden_at is not None
                    else "VISIBLE"
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
                if name in payload.model_fields_set and value is not None or (
                    name == "icon" and name in payload.model_fields_set
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

    async def get_settings(self, principal: AuthPrincipal) -> CommunitySettings:
        self._require(principal, _MANAGE)
        async with self._session.begin():
            return await self._ensure_settings()

    async def update_settings(
        self,
        principal: AuthPrincipal,
        payload: CommunitySettingsRequest,
        *,
        request_id: str,
    ) -> CommunitySettings:
        self._require(principal, _MANAGE)
        async with self._session.begin():
            settings = await self._ensure_settings()
            before = settings.pre_moderation_enabled
            settings.pre_moderation_enabled = payload.pre_moderation_enabled
            settings.updated_by_user_id = principal.user_id
            settings.updated_at = datetime.now(UTC)
            self._event(
                principal,
                target_type="SETTINGS",
                target_id="1",
                action=CommunityModerationEventAction.SETTINGS_UPDATED,
                reason=payload.reason,
                request_id=request_id,
                event_data={
                    "preModerationEnabled": {
                        "before": before,
                        "after": settings.pre_moderation_enabled,
                    }
                },
            )
            await self._session.flush()
            return settings

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

    async def _ensure_settings(self) -> CommunitySettings:
        settings = await self._repository.get_settings()
        if settings is None:
            settings = CommunitySettings(singleton_id=1, pre_moderation_enabled=True)
            self._repository.add_settings(settings)
            await self._session.flush()
        return settings

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
    ) -> None:
        self._repository.add_moderation_event(
            CommunityModerationEvent(
                target_type=target_type,
                target_id=target_id,
                action=action.value,
                actor_user_id=principal.user_id,
                report_id=report_id,
                reason=reason,
                request_id=request_id,
                event_data=event_data,
            )
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
