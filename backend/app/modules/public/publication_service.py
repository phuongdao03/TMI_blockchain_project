import logging
from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.db.outbox import OutboxEvent
from app.modules.audit.service import AuditService
from app.modules.auth.authorization import AuthorizationPolicy, PolicyRequirement
from app.modules.auth.repositories import OutboxRepository
from app.modules.auth.security import OutboxPayloadCipher
from app.modules.auth.session_service import AuthPrincipal
from app.modules.public.catalog_repository import (
    PublicWorkPublicationContext,
    PublicWorkRepository,
)
from app.modules.public.errors import (
    PublicWorkFeaturedWindowError,
    PublicWorkForbiddenError,
    PublicWorkNotFoundError,
    PublicWorkNotPublishableError,
    PublicWorkReasonRequiredError,
    PublicWorkScheduleError,
    PublicWorkVersionConflictError,
)
from app.modules.public.models import (
    PublicationStatus,
    PublicWork,
    PublicWorkVisibility,
)
from app.modules.public.publication_policy import publication_checklist

PUBLICATION_ADMIN_ROLES = frozenset({"CONTENT_ADMIN", "SUPER_ADMIN"})
logger = logging.getLogger(__name__)


class PublicationAction(StrEnum):
    PUBLISH = "PUBLISH"
    SCHEDULE = "SCHEDULE"
    HIDE = "HIDE"
    SUSPEND = "SUSPEND"
    ARCHIVE = "ARCHIVE"


class PublicationTransitionError(DomainError):
    def __init__(
        self,
        current: PublicationStatus,
        action: PublicationAction,
    ) -> None:
        self.current = current
        self.action = action
        super().__init__(
            code="INVALID_VISIBILITY_TRANSITION",
            message=f"{action.value} is not allowed from {current.value}.",
            status_code=409,
            details={"current_status": current.value, "action": action.value},
        )


ALLOWED_ACTIONS: dict[PublicationStatus, frozenset[PublicationAction]] = {
    PublicationStatus.DRAFT: frozenset(
        {
            PublicationAction.PUBLISH,
            PublicationAction.SCHEDULE,
            PublicationAction.SUSPEND,
            PublicationAction.ARCHIVE,
        }
    ),
    PublicationStatus.PENDING_PUBLICATION: frozenset(
        {
            PublicationAction.PUBLISH,
            PublicationAction.SCHEDULE,
            PublicationAction.HIDE,
            PublicationAction.SUSPEND,
            PublicationAction.ARCHIVE,
        }
    ),
    PublicationStatus.PUBLISHED: frozenset(
        {
            PublicationAction.HIDE,
            PublicationAction.SUSPEND,
            PublicationAction.ARCHIVE,
        }
    ),
    PublicationStatus.HIDDEN: frozenset(
        {
            PublicationAction.PUBLISH,
            PublicationAction.SCHEDULE,
            PublicationAction.SUSPEND,
            PublicationAction.ARCHIVE,
        }
    ),
    PublicationStatus.SUSPENDED: frozenset(
        {PublicationAction.HIDE, PublicationAction.ARCHIVE}
    ),
    PublicationStatus.ARCHIVED: frozenset(),
}


def assert_transition(
    current: PublicationStatus,
    action: PublicationAction,
) -> None:
    if action not in ALLOWED_ACTIONS[current]:
        raise PublicationTransitionError(current, action)


class PublicationService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        audit: AuditService,
        payload_cipher: OutboxPayloadCipher,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session = session
        self._repository = PublicWorkRepository(session)
        self._audit = audit
        self._outbox = OutboxRepository(session)
        self._payload_cipher = payload_cipher
        self._clock = clock or (lambda: datetime.now(UTC))

    async def publish(
        self,
        principal: AuthPrincipal,
        work_id: UUID,
        *,
        expected_version: int,
        visibility: PublicWorkVisibility,
        request_id: str,
    ) -> PublicWork:
        self._require_admin(principal)
        if visibility is PublicWorkVisibility.PRIVATE:
            raise PublicWorkNotPublishableError(["visibility_must_be_public"])
        async with self._session.begin():
            context = await self._required_context(work_id)
            await self._claim_version(context.work, expected_version)
            assert_transition(
                context.work.publication_status,
                PublicationAction.PUBLISH,
            )
            self._require_publishable(context)
            self._apply_publish(
                context.work,
                visibility=visibility,
                published_at=self._clock(),
            )
            await self._record_change(
                context.work,
                principal.user_id,
                action="public_work.published",
                request_id=request_id,
            )
        return context.work

    async def schedule(
        self,
        principal: AuthPrincipal,
        work_id: UUID,
        *,
        expected_version: int,
        visibility: PublicWorkVisibility,
        publish_at: datetime,
        request_id: str,
    ) -> PublicWork:
        self._require_admin(principal)
        now = self._clock()
        normalized_publish_at = self._as_utc(publish_at)
        if (
            publish_at.tzinfo is None
            or normalized_publish_at <= self._as_utc(now)
            or visibility is PublicWorkVisibility.PRIVATE
        ):
            raise PublicWorkScheduleError()
        async with self._session.begin():
            context = await self._required_context(work_id)
            await self._claim_version(context.work, expected_version)
            assert_transition(
                context.work.publication_status,
                PublicationAction.SCHEDULE,
            )
            self._require_publishable(context)
            context.work.publication_status = PublicationStatus.PENDING_PUBLICATION
            context.work.visibility = visibility
            context.work.scheduled_publish_at = normalized_publish_at
            context.work.featured_at = None
            context.work.featured_until = None
            await self._record_change(
                context.work,
                principal.user_id,
                action="public_work.updated",
                request_id=request_id,
            )
        return context.work

    async def hide(
        self,
        principal: AuthPrincipal,
        work_id: UUID,
        *,
        expected_version: int,
        request_id: str,
    ) -> PublicWork:
        return await self._restrict_visibility(
            principal,
            work_id,
            expected_version=expected_version,
            action=PublicationAction.HIDE,
            target=PublicationStatus.HIDDEN,
            reason=None,
            request_id=request_id,
        )

    async def suspend(
        self,
        principal: AuthPrincipal,
        work_id: UUID,
        *,
        expected_version: int,
        reason: str,
        request_id: str,
    ) -> PublicWork:
        return await self._restrict_visibility(
            principal,
            work_id,
            expected_version=expected_version,
            action=PublicationAction.SUSPEND,
            target=PublicationStatus.SUSPENDED,
            reason=self._required_reason(reason),
            request_id=request_id,
        )

    async def archive(
        self,
        principal: AuthPrincipal,
        work_id: UUID,
        *,
        expected_version: int,
        reason: str,
        request_id: str,
    ) -> PublicWork:
        return await self._restrict_visibility(
            principal,
            work_id,
            expected_version=expected_version,
            action=PublicationAction.ARCHIVE,
            target=PublicationStatus.ARCHIVED,
            reason=self._required_reason(reason),
            request_id=request_id,
        )

    async def feature(
        self,
        principal: AuthPrincipal,
        work_id: UUID,
        *,
        expected_version: int,
        featured_at: datetime,
        featured_until: datetime | None,
        request_id: str,
    ) -> PublicWork:
        self._require_admin(principal)
        if featured_at.tzinfo is None or (
            featured_until is not None and featured_until.tzinfo is None
        ):
            raise PublicWorkFeaturedWindowError()
        normalized_start = self._as_utc(featured_at)
        normalized_end = (
            self._as_utc(featured_until) if featured_until is not None else None
        )
        now = self._as_utc(self._clock())
        if normalized_end is not None and (
            normalized_end <= normalized_start or normalized_end <= now
        ):
            raise PublicWorkFeaturedWindowError()
        async with self._session.begin():
            context = await self._required_context(work_id)
            work = context.work
            await self._claim_version(work, expected_version)
            if (
                work.publication_status is not PublicationStatus.PUBLISHED
                or work.visibility is not PublicWorkVisibility.PUBLIC
            ):
                raise PublicWorkNotPublishableError(
                    ["featured_requires_published_public"]
                )
            work.featured_at = normalized_start
            work.featured_until = normalized_end
            await self._record_change(
                work,
                principal.user_id,
                action="public_work.featured",
                request_id=request_id,
            )
        return context.work

    async def unfeature(
        self,
        principal: AuthPrincipal,
        work_id: UUID,
        *,
        expected_version: int,
        request_id: str,
    ) -> PublicWork:
        self._require_admin(principal)
        async with self._session.begin():
            context = await self._required_context(work_id)
            work = context.work
            await self._claim_version(work, expected_version)
            work.featured_at = None
            work.featured_until = None
            await self._record_change(
                work,
                principal.user_id,
                action="public_work.unfeatured",
                request_id=request_id,
            )
        return context.work

    async def publish_due(self, *, now: datetime, limit: int = 100) -> int:
        if not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")
        normalized_now = self._as_utc(now)
        async with self._session.begin():
            work_ids = await self._repository.list_due_publication_ids(
                now=normalized_now,
                limit=limit,
            )
        published = 0
        for work_id in work_ids:
            async with self._session.begin():
                context = await self._required_context(work_id)
                work = context.work
                scheduled_at = work.scheduled_publish_at
                if (
                    work.publication_status is not PublicationStatus.PENDING_PUBLICATION
                    or scheduled_at is None
                    or self._as_utc(scheduled_at) > normalized_now
                ):
                    continue
                try:
                    self._require_publishable(context)
                except PublicWorkNotPublishableError as error:
                    logger.warning(
                        "scheduled_public_work_not_publishable",
                        extra={
                            "public_work_id": str(work.id),
                            "error_code": error.code,
                        },
                    )
                    continue
                await self._claim_version(work, work.version)
                self._apply_publish(
                    work,
                    visibility=work.visibility,
                    published_at=normalized_now,
                )
                await self._record_change(
                    work,
                    None,
                    action="public_work.published",
                    request_id="scheduled-publication",
                )
                published += 1
        return published

    async def _restrict_visibility(
        self,
        principal: AuthPrincipal,
        work_id: UUID,
        *,
        expected_version: int,
        action: PublicationAction,
        target: PublicationStatus,
        reason: str | None,
        request_id: str,
    ) -> PublicWork:
        self._require_admin(principal)
        async with self._session.begin():
            context = await self._required_context(work_id)
            work = context.work
            await self._claim_version(work, expected_version)
            assert_transition(work.publication_status, action)
            work.publication_status = target
            work.visibility = PublicWorkVisibility.PRIVATE
            work.scheduled_publish_at = None
            work.featured_at = None
            work.featured_until = None
            await self._record_change(
                work,
                principal.user_id,
                action=f"public_work.{action.value.lower()}",
                request_id=request_id,
                reason=reason,
            )
        return context.work

    async def _required_context(
        self,
        work_id: UUID,
    ) -> PublicWorkPublicationContext:
        context = await self._repository.get_publication_context(
            work_id,
            for_update=True,
        )
        if context is None:
            raise PublicWorkNotFoundError()
        return context

    @staticmethod
    def _require_publishable(context: PublicWorkPublicationContext) -> None:
        reasons = publication_checklist(context)
        if reasons:
            raise PublicWorkNotPublishableError(reasons)

    @staticmethod
    def _apply_publish(
        work: PublicWork,
        *,
        visibility: PublicWorkVisibility,
        published_at: datetime,
    ) -> None:
        work.publication_status = PublicationStatus.PUBLISHED
        work.visibility = visibility
        work.published_at = published_at
        work.scheduled_publish_at = None
        work.featured_at = None
        work.featured_until = None

    async def _record_change(
        self,
        work: PublicWork,
        actor_user_id: UUID | None,
        *,
        action: str,
        request_id: str,
        reason: str | None = None,
    ) -> None:
        await self._session.flush()
        after = self._serialize(work)
        if reason is not None:
            after["reason"] = reason
        self._audit.record(
            actor_user_id=actor_user_id,
            action=action,
            resource_type="public_work",
            resource_id=str(work.id),
            after=after,
            request_id=request_id,
        )
        encrypted = self._payload_cipher.encrypt(
            {
                "public_work_id": str(work.id),
                "slug": work.slug,
                "status": work.publication_status.value,
                "visibility": work.visibility.value,
                "version": str(work.version),
                "invalidate_cache": "true",
            },
            event_type=action,
            aggregate_id=work.id,
        )
        self._outbox.add(
            OutboxEvent(
                event_type=action,
                aggregate_type="public_work",
                aggregate_id=work.id,
                payload_ciphertext=encrypted.ciphertext,
                payload_nonce=encrypted.nonce,
                key_id=encrypted.key_id,
                occurred_at=self._clock(),
            )
        )

    @staticmethod
    def _serialize(work: PublicWork) -> dict[str, object]:
        return {
            "id": str(work.id),
            "publication_status": work.publication_status.value,
            "visibility": work.visibility.value,
            "version": work.version,
            "published_at": (
                work.published_at.isoformat() if work.published_at else None
            ),
            "scheduled_publish_at": (
                work.scheduled_publish_at.isoformat()
                if work.scheduled_publish_at
                else None
            ),
            "featured_at": (work.featured_at.isoformat() if work.featured_at else None),
            "featured_until": (
                work.featured_until.isoformat() if work.featured_until else None
            ),
        }

    async def _claim_version(
        self,
        work: PublicWork,
        expected_version: int,
    ) -> None:
        if work.version != expected_version or not await self._repository.claim_version(
            work,
            expected_version,
        ):
            await self._session.refresh(work, attribute_names=["version"])
            raise PublicWorkVersionConflictError(current_version=work.version)

    @staticmethod
    def _require_admin(principal: AuthPrincipal) -> None:
        AuthorizationPolicy.require_capability(
            principal,
            PolicyRequirement(
                permission="public_content.manage",
                compatible_roles=PUBLICATION_ADMIN_ROLES,
            ),
            PublicWorkForbiddenError,
        )

    @staticmethod
    def _required_reason(reason: str) -> str:
        normalized = " ".join(reason.split())
        if not normalized:
            raise PublicWorkReasonRequiredError()
        return normalized

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
