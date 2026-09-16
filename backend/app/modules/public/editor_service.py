import json
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.outbox import OutboxEvent
from app.modules.audit.service import AuditService
from app.modules.auth.authorization import AuthorizationPolicy, PolicyRequirement
from app.modules.auth.repositories import OutboxRepository
from app.modules.auth.security import OutboxPayloadCipher
from app.modules.auth.session_service import AuthPrincipal
from app.modules.blockchain.models import CertificateStatus
from app.modules.public.backfill import RESERVED_SLUGS, SLUG_PATTERN
from app.modules.public.catalog_repository import (
    PublicWorkPublicationContext,
    PublicWorkRepository,
)
from app.modules.public.detail_service import (
    PublicCertificateSummary,
    PublicProofSummary,
)
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
class PublicWorkAdminView:
    work: PublicWork
    dossier_code: str


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
class SourceField:
    key: str
    label: str
    value: str


@dataclass(frozen=True, slots=True)
class PublicWorkEditorView:
    work: PublicWork
    dossier_code: str
    category_name: str
    tag_ids: tuple[UUID, ...]
    checklist: tuple[ChecklistItem, ...]
    source_version_no: int
    source_fields: tuple[SourceField, ...]


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
    certificate: PublicCertificateSummary | None = None
    proof: PublicProofSummary | None = None


def _source_fields(
    context: PublicWorkPublicationContext,
) -> tuple[int, tuple[SourceField, ...]]:
    version = context.dossier_version
    fields = [
        SourceField("title", "Tiêu đề hồ sơ", context.dossier.title),
    ]
    if context.dossier.summary:
        fields.append(SourceField("summary", "Mô tả hồ sơ", context.dossier.summary))
    if version is None:
        return context.dossier.current_version_no, tuple(fields)

    dossier_snapshot = version.snapshot_json.get("dossier")
    if not isinstance(dossier_snapshot, dict):
        return version.version_no, tuple(fields)
    snapshot_title = dossier_snapshot.get("title")
    snapshot_summary = dossier_snapshot.get("summary")
    if isinstance(snapshot_title, str) and snapshot_title.strip():
        fields[0] = SourceField("title", "Tiêu đề hồ sơ", snapshot_title.strip())
    if isinstance(snapshot_summary, str) and snapshot_summary.strip():
        summary = SourceField("summary", "Mô tả hồ sơ", snapshot_summary.strip())
        if len(fields) == 1:
            fields.append(summary)
        else:
            fields[1] = summary

    dossier_type = dossier_snapshot.get("dossierType")
    public_fields = (
        dossier_type.get("publicFields") if isinstance(dossier_type, dict) else None
    )
    if not isinstance(public_fields, list):
        return version.version_no, tuple(fields)
    for index, item in enumerate(public_fields):
        if not isinstance(item, dict):
            continue
        raw_value = item.get("value")
        if raw_value in (None, "", [], {}):
            continue
        value = (
            raw_value.strip()
            if isinstance(raw_value, str)
            else json.dumps(raw_value, ensure_ascii=False, separators=(",", ":"))
        )
        key = item.get("key")
        label = item.get("label")
        fields.append(
            SourceField(
                key=key if isinstance(key, str) and key else f"field-{index + 1}",
                label=(
                    label
                    if isinstance(label, str) and label
                    else f"Thông tin {index + 1}"
                ),
                value=value,
            )
        )
    return version.version_no, tuple(fields)


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
    ) -> tuple[tuple[PublicWorkAdminView, ...], int]:
        self._require_editor(principal)
        if page < 1 or not 1 <= page_size <= 100:
            raise ValueError("invalid editor pagination")
        async with self._session.begin():
            rows, total = await self._repository.list_admin_works(
                query=query.strip() if query else None,
                status=status,
                offset=(page - 1) * page_size,
                limit=page_size,
            )
            return tuple(PublicWorkAdminView(work, code) for work, code in rows), total

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
            source_version_no, source_fields = _source_fields(context)
            return PublicWorkEditorView(
                work=context.work,
                dossier_code=context.dossier.code,
                category_name=context.category.name,
                tag_ids=await self._repository.list_work_tag_ids(work_id),
                checklist=checklist,
                source_version_no=source_version_no,
                source_fields=source_fields,
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
                if (
                    data.thumbnail_media_id is not None
                    and data.thumbnail_media_id != work.thumbnail_media_id
                    and await self._repository.ready_cover_kind(
                        work.id, data.thumbnail_media_id
                    )
                    is None
                ):
                    raise PublicWorkMetadataValidationError(
                        "Cover must be a ready image or video attached to the work."
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
        async with self._session.begin():
            row = await self._repository.get_public_work_detail(work_id)
        certificate = row.certificate if row and row.work.show_certificate else None
        if certificate is not None and (
            certificate.status is not CertificateStatus.ACTIVE
            or (
                certificate.expires_at is not None
                and certificate.expires_at.replace(tzinfo=UTC) <= datetime.now(UTC)
            )
        ):
            certificate = None
        transaction = row.transaction if row else None
        return PublicWorkPreviewView(
            slug=editor.work.slug,
            title=editor.work.title,
            short_description=editor.work.short_description,
            full_description=editor.work.full_description,
            author_display_name=editor.work.author_display_name,
            category_name=editor.category_name,
            media=media,
            can_publish=all(item.passed for item in editor.checklist),
            certificate=(
                PublicCertificateSummary(
                    certificate.certificate_number,
                    certificate.status,
                    certificate.issued_at,
                    certificate.expires_at,
                )
                if certificate
                else None
            ),
            proof=(
                PublicProofSummary(
                    transaction.network,
                    transaction.tx_hash,
                    transaction.status,
                    transaction.confirmations,
                    transaction.confirmed_at,
                )
                if transaction
                else None
            ),
        )

    async def configure_certificate_listing(
        self,
        principal: AuthPrincipal,
        certificate_id: UUID,
        *,
        expected_version: int,
        show: bool,
        request_id: str,
    ) -> PublicWork:
        self._require_editor(principal)
        async with self._session.begin():
            work = await self._session.scalar(
                select(PublicWork)
                .where(
                    PublicWork.certificate_id == certificate_id,
                    PublicWork.deleted_at.is_(None),
                )
                .with_for_update()
            )
            if work is None:
                raise PublicWorkNotFoundError()
            if work.version != expected_version:
                raise PublicWorkVersionConflictError(current_version=work.version)
            context = await self._repository.get_publication_context(work.id)
            certificate = context.certificate if context else None
            if show and (
                certificate is None
                or certificate.status is not CertificateStatus.ACTIVE
                or (
                    certificate.expires_at is not None
                    and certificate.expires_at.replace(tzinfo=UTC) <= datetime.now(UTC)
                )
            ):
                raise PublicWorkMetadataValidationError(
                    "Only an active certificate may appear with the work."
                )
            if not await self._repository.claim_version(work, expected_version):
                raise PublicWorkVersionConflictError(current_version=work.version)
            work.show_certificate = show
            self._record_update(
                principal,
                work,
                await self._repository.list_work_tag_ids(work.id),
                request_id,
            )
            return work

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
            "show_certificate": work.show_certificate,
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
