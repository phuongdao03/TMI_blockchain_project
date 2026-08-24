from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.outbox import OutboxEvent
from app.modules.audit.service import AuditService
from app.modules.auth.authorization import AuthorizationPolicy, PolicyRequirement
from app.modules.auth.repositories import OutboxRepository
from app.modules.auth.security import OutboxPayloadCipher
from app.modules.auth.session_service import AuthPrincipal
from app.modules.media.models import MediaStatus
from app.modules.media.repository import MediaAssetRepository
from app.modules.public.backfill import RESERVED_SLUGS, SLUG_PATTERN
from app.modules.public.catalog_repository import PublicWorkRepository
from app.modules.public.errors import (
    PublicWorkForbiddenError,
    PublicWorkMetadataValidationError,
    PublicWorkNotFoundError,
    PublicWorkSlugConflictError,
    PublicWorkVersionConflictError,
)
from app.modules.public.media_service import PublicMediaQueryService, PublicMediaView
from app.modules.public.models import (
    PublicationStatus,
    PublicWork,
    PublicWorkSlugHistory,
    PublicWorkVisibility,
)
from app.modules.public.publication_policy import (
    PUBLICATION_CHECK_CODES,
    publication_checklist,
)

EDITOR_ROLES = frozenset({"SUPER_ADMIN"})


@dataclass(frozen=True, slots=True)
class PublicWorkEditorInput:
    expected_version: int
    slug: str
    title: str
    short_description: str
    full_description: str | None
    author_display_name: str | None
    category_id: UUID
    tag_ids: tuple[UUID, ...]
    visibility: PublicWorkVisibility
    thumbnail_media_id: UUID | None


@dataclass(frozen=True, slots=True)
class NormalizedEditorInput:
    slug: str
    title: str
    short_description: str
    full_description: str | None
    author_display_name: str | None


@dataclass(frozen=True, slots=True)
class ChecklistItem:
    code: str
    passed: bool


@dataclass(frozen=True, slots=True)
class PublicWorkEditorView:
    work: PublicWork
    category_name: str
    tag_ids: tuple[UUID, ...]
    checklist: tuple[ChecklistItem, ...]


@dataclass(frozen=True, slots=True)
class PublicWorkPreviewView:
    slug: str
    title: str
    short_description: str
    full_description: str | None
    author_display_name: str | None
    category_name: str
    media: tuple[PublicMediaView, ...]
    can_publish: bool


class PublicWorkEditorService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        audit: AuditService,
        payload_cipher: OutboxPayloadCipher,
    ) -> None:
        self._session = session
        self._repository = PublicWorkRepository(session)
        self._media_repository = MediaAssetRepository(session)
        self._media_query = PublicMediaQueryService(session)
        self._audit = audit
        self._outbox = OutboxRepository(session)
        self._payload_cipher = payload_cipher

    async def list(
        self,
        principal: AuthPrincipal,
        *,
        query: str | None,
        status: PublicationStatus | None,
        page: int,
        page_size: int,
    ) -> tuple[tuple[PublicWork, ...], int]:
        self._require_editor(principal)
        if page < 1 or not 1 <= page_size <= 100:
            raise ValueError("invalid editor pagination")
        async with self._session.begin():
            return await self._repository.list_admin_works(
                query=query.strip() if query else None,
                status=status,
                offset=(page - 1) * page_size,
                limit=page_size,
            )

    async def get(
        self, principal: AuthPrincipal, work_id: UUID
    ) -> PublicWorkEditorView:
        self._require_editor(principal)
        async with self._session.begin():
            context = await self._repository.get_publication_context(work_id)
            if context is None:
                raise PublicWorkNotFoundError()
            failed = set(publication_checklist(context))
            checklist = tuple(
                ChecklistItem(code, code not in failed)
                for code in PUBLICATION_CHECK_CODES
            )
            return PublicWorkEditorView(
                work=context.work,
                category_name=context.category.name,
                tag_ids=await self._repository.list_work_tag_ids(work_id),
                checklist=checklist,
            )

    async def update(
        self,
        principal: AuthPrincipal,
        work_id: UUID,
        data: PublicWorkEditorInput,
        *,
        request_id: str,
    ) -> PublicWork:
        self._require_editor(principal)
        values = self._validate_input(data)
        try:
            async with self._session.begin():
                work = await self._repository.get_by_id(work_id, for_update=True)
                if work is None:
                    raise PublicWorkNotFoundError()
                if work.version != data.expected_version:
                    raise PublicWorkVersionConflictError(current_version=work.version)
                if not await self._repository.claim_version(
                    work, data.expected_version
                ):
                    await self._session.refresh(work, attribute_names=["version"])
                    raise PublicWorkVersionConflictError(current_version=work.version)
                category = await self._repository.get_category(data.category_id)
                if category is None or not category.is_active:
                    raise PublicWorkMetadataValidationError(
                        "An active category is required."
                    )
                if data.thumbnail_media_id is not None:
                    thumbnail = await self._media_repository.get_by_id(
                        data.thumbnail_media_id
                    )
                    if (
                        thumbnail is None
                        or thumbnail.status is not MediaStatus.ACTIVE
                        or thumbnail.deleted_at is not None
                        or not thumbnail.mime_type.startswith("image/")
                    ):
                        raise PublicWorkMetadataValidationError(
                            "Thumbnail must be an active image asset."
                        )
                unique_tag_ids = tuple(dict.fromkeys(data.tag_ids))
                if len(unique_tag_ids) > 50:
                    raise PublicWorkMetadataValidationError(
                        "A public work can contain at most 50 tags."
                    )
                for tag_id in unique_tag_ids:
                    tag = await self._repository.get_tag(tag_id)
                    if tag is None or not tag.is_active:
                        raise PublicWorkMetadataValidationError(
                            "Every selected tag must be active."
                        )
                if values.slug != work.slug:
                    if await self._repository.slug_exists(values.slug):
                        raise PublicWorkSlugConflictError()
                    self._repository.add_slug_history(
                        PublicWorkSlugHistory(
                            public_work_id=work.id,
                            slug=work.slug,
                        )
                    )
                work.slug = values.slug
                work.title = values.title
                work.short_description = values.short_description
                work.full_description = values.full_description
                work.author_display_name = values.author_display_name
                work.category_id = data.category_id
                work.visibility = data.visibility
                work.thumbnail_media_id = data.thumbnail_media_id
                await self._repository.replace_work_tags(work.id, unique_tag_ids)
                self._record_update(principal, work, unique_tag_ids, request_id)
            return work
        except IntegrityError as error:
            await self._session.rollback()
            raise PublicWorkSlugConflictError() from error

    async def preview(
        self, principal: AuthPrincipal, work_id: UUID
    ) -> PublicWorkPreviewView:
        editor = await self.get(principal, work_id)
        media = await self._media_query.list_public(work_id)
        return PublicWorkPreviewView(
            slug=editor.work.slug,
            title=editor.work.title,
            short_description=editor.work.short_description,
            full_description=editor.work.full_description,
            author_display_name=editor.work.author_display_name,
            category_name=editor.category_name,
            media=media,
            can_publish=all(item.passed for item in editor.checklist),
        )

    def _record_update(
        self,
        principal: AuthPrincipal,
        work: PublicWork,
        tag_ids: tuple[UUID, ...],
        request_id: str,
    ) -> None:
        after: dict[str, object] = {
            "slug": work.slug,
            "title": work.title,
            "category_id": str(work.category_id),
            "visibility": work.visibility.value,
            "thumbnail_media_id": (
                str(work.thumbnail_media_id) if work.thumbnail_media_id else None
            ),
            "tag_ids": [str(tag_id) for tag_id in tag_ids],
            "version": work.version,
        }
        self._audit.record(
            actor_user_id=principal.user_id,
            action="public_work.metadata_updated",
            resource_type="public_work",
            resource_id=str(work.id),
            after=after,
            request_id=request_id,
        )
        encrypted = self._payload_cipher.encrypt(
            {
                "public_work_id": str(work.id),
                "slug": work.slug,
                "version": str(work.version),
                "invalidate_cache": "true",
            },
            event_type="public_work.metadata_updated",
            aggregate_id=work.id,
        )
        self._outbox.add(
            OutboxEvent(
                event_type="public_work.metadata_updated",
                aggregate_type="public_work",
                aggregate_id=work.id,
                payload_ciphertext=encrypted.ciphertext,
                payload_nonce=encrypted.nonce,
                key_id=encrypted.key_id,
            )
        )

    @staticmethod
    def _validate_input(data: PublicWorkEditorInput) -> NormalizedEditorInput:
        slug = data.slug.strip().lower()
        title = data.title.strip()
        short_description = data.short_description.strip()
        full_description = PublicWorkEditorService._plain_text(
            data.full_description, max_length=20_000
        )
        author = PublicWorkEditorService._plain_text(
            data.author_display_name, max_length=255
        )
        if (
            not SLUG_PATTERN.fullmatch(slug)
            or len(slug) > 180
            or slug in RESERVED_SLUGS
        ):
            raise PublicWorkMetadataValidationError("Public slug is invalid.")
        if not 3 <= len(title) <= 255:
            raise PublicWorkMetadataValidationError(
                "Title must contain 3 to 255 characters."
            )
        if not 10 <= len(short_description) <= 500:
            raise PublicWorkMetadataValidationError(
                "Short description must contain 10 to 500 characters."
            )
        return NormalizedEditorInput(
            slug=slug,
            title=title,
            short_description=short_description,
            full_description=full_description,
            author_display_name=author,
        )

    @staticmethod
    def _plain_text(value: str | None, *, max_length: int) -> str | None:
        normalized = value.strip() if value else ""
        if len(normalized) > max_length or any(
            character in normalized for character in "<>\x00"
        ):
            raise PublicWorkMetadataValidationError(
                "Editorial text must be plain text within the allowed length."
            )
        return normalized or None

    @staticmethod
    def _require_editor(principal: AuthPrincipal) -> None:
        AuthorizationPolicy.require_capability(
            principal,
            PolicyRequirement(
                permission="public_content.manage", compatible_roles=EDITOR_ROLES
            ),
            PublicWorkForbiddenError,
        )
