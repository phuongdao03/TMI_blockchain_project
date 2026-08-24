from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.outbox import OutboxEvent
from app.modules.audit.service import AuditService
from app.modules.auth.authorization import AuthorizationPolicy, PolicyRequirement
from app.modules.auth.repositories import OutboxRepository
from app.modules.auth.security import OutboxPayloadCipher
from app.modules.auth.session_service import AuthPrincipal
from app.modules.media.errors import MediaProviderUnavailableError
from app.modules.media.gateway import PublicDerivativeGateway
from app.modules.media.models import MediaAsset, MediaStatus
from app.modules.public.errors import (
    PublicMediaConflictError,
    PublicMediaNotFoundError,
    PublicMediaValidationError,
    PublicWorkForbiddenError,
    PublicWorkNotFoundError,
)
from app.modules.public.media_repository import PublicMediaRepository
from app.modules.public.models import (
    DerivativeStatus,
    PublicMediaKind,
    PublicWorkMedia,
)

PUBLIC_MEDIA_ADMIN_ROLES = frozenset({"SUPER_ADMIN"})
PUBLIC_MEDIA_MIME_KINDS = {
    "image/jpeg": PublicMediaKind.IMAGE,
    "image/png": PublicMediaKind.IMAGE,
    "image/webp": PublicMediaKind.IMAGE,
    "audio/mpeg": PublicMediaKind.AUDIO,
    "audio/mp4": PublicMediaKind.AUDIO,
    "audio/ogg": PublicMediaKind.AUDIO,
    "video/mp4": PublicMediaKind.VIDEO,
    "video/webm": PublicMediaKind.VIDEO,
    "application/pdf": PublicMediaKind.DOCUMENT,
}
_SOURCE_FORMATS = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}
IMAGE_DERIVATIVE_TRANSFORMATION = "c_limit,w_1600,h_1600,q_auto,f_webp"


class PublicMediaDispatcher(Protocol):
    def enqueue(self, relation_id: UUID) -> None: ...


@dataclass(frozen=True, slots=True)
class PublicMediaInput:
    media_asset_id: UUID
    sort_order: int
    caption: str | None
    alt_text: str | None


@dataclass(frozen=True, slots=True)
class PublicMediaView:
    id: UUID
    kind: PublicMediaKind
    sort_order: int
    caption: str | None
    alt_text: str | None
    url: str | None
    mime_type: str | None
    width: int | None
    height: int | None
    duration_ms: int | None
    is_thumbnail: bool


class PublicMediaQueryService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = PublicMediaRepository(session)

    async def list_public(self, work_id: UUID) -> tuple[PublicMediaView, ...]:
        async with self._session.begin():
            work = await self._repository.get_work(work_id)
            if work is None:
                return ()
            rows = tuple(
                row
                for row in await self._repository.list_for_work(work_id)
                if row.derivative_status is DerivativeStatus.READY
            )
        fallback = next(
            (row for row in rows if row.media_kind is PublicMediaKind.IMAGE), None
        )
        thumbnail_id = work.thumbnail_media_id
        selected = next(
            (row for row in rows if row.media_asset_id == thumbnail_id), fallback
        )
        return tuple(
            PublicMediaView(
                id=row.id,
                kind=row.media_kind,
                sort_order=row.sort_order,
                caption=row.caption,
                alt_text=row.alt_text,
                url=row.derivative_url,
                mime_type=row.derivative_mime_type,
                width=row.derivative_width,
                height=row.derivative_height,
                duration_ms=row.duration_ms,
                is_thumbnail=selected is not None and row.id == selected.id,
            )
            for row in rows
        )


class PublicMediaService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        audit: AuditService,
        dispatcher: PublicMediaDispatcher,
        payload_cipher: OutboxPayloadCipher,
    ) -> None:
        self._session = session
        self._repository = PublicMediaRepository(session)
        self._audit = audit
        self._dispatcher = dispatcher
        self._outbox = OutboxRepository(session)
        self._payload_cipher = payload_cipher

    async def attach(
        self,
        principal: AuthPrincipal,
        work_id: UUID,
        data: PublicMediaInput,
        *,
        request_id: str,
    ) -> PublicWorkMedia:
        self._require_admin(principal)
        if data.sort_order < 0:
            raise PublicMediaValidationError("Media sort order cannot be negative.")
        try:
            async with self._session.begin():
                if await self._repository.get_work(work_id, for_update=True) is None:
                    raise PublicWorkNotFoundError()
                asset = await self._repository.get_asset(data.media_asset_id)
                kind = self._validate_asset(asset)
                caption = self._plain_text(data.caption, "caption")
                alt_text = self._plain_text(data.alt_text, "alt text")
                if kind is PublicMediaKind.IMAGE and not alt_text:
                    raise PublicMediaValidationError(
                        "Image alt text is required for public accessibility."
                    )
                relation = PublicWorkMedia(
                    public_work_id=work_id,
                    media_asset_id=data.media_asset_id,
                    media_kind=kind,
                    sort_order=data.sort_order,
                    caption=caption,
                    alt_text=alt_text,
                )
                self._repository.add(relation)
                await self._session.flush()
                self._audit.record(
                    actor_user_id=principal.user_id,
                    action="public_work.media_attached",
                    resource_type="public_work",
                    resource_id=str(work_id),
                    after={"relation_id": str(relation.id), "kind": kind.value},
                    request_id=request_id,
                )
                self._event(work_id, "public_work.media_attached")
            self._dispatcher.enqueue(relation.id)
            return relation
        except IntegrityError as error:
            await self._session.rollback()
            raise PublicMediaConflictError() from error

    async def reorder(
        self,
        principal: AuthPrincipal,
        work_id: UUID,
        relation_ids: tuple[UUID, ...],
        *,
        request_id: str,
    ) -> None:
        self._require_admin(principal)
        if len(relation_ids) != len(set(relation_ids)):
            raise PublicMediaConflictError()
        async with self._session.begin():
            if await self._repository.get_work(work_id, for_update=True) is None:
                raise PublicWorkNotFoundError()
            rows = await self._repository.list_for_work(work_id)
            if {row.id for row in rows} != set(relation_ids):
                raise PublicMediaConflictError()
            by_id = {row.id: row for row in rows}
            for order, relation_id in enumerate(relation_ids):
                by_id[relation_id].sort_order = order
            self._audit.record(
                actor_user_id=principal.user_id,
                action="public_work.media_reordered",
                resource_type="public_work",
                resource_id=str(work_id),
                after={"relation_ids": [str(value) for value in relation_ids]},
                request_id=request_id,
            )
            self._event(work_id, "public_work.media_reordered")

    async def remove(
        self,
        principal: AuthPrincipal,
        work_id: UUID,
        relation_id: UUID,
        *,
        request_id: str,
    ) -> None:
        self._require_admin(principal)
        async with self._session.begin():
            relation = await self._repository.get_relation(relation_id, for_update=True)
            if relation is None or relation.public_work_id != work_id:
                raise PublicMediaNotFoundError()
            await self._repository.delete(relation)
            self._audit.record(
                actor_user_id=principal.user_id,
                action="public_work.media_removed",
                resource_type="public_work",
                resource_id=str(work_id),
                before={"relation_id": str(relation_id)},
                request_id=request_id,
            )
            self._event(work_id, "public_work.media_removed")

    async def list_admin(
        self, principal: AuthPrincipal, work_id: UUID
    ) -> tuple[PublicWorkMedia, ...]:
        self._require_admin(principal)
        async with self._session.begin():
            if await self._repository.get_work(work_id) is None:
                raise PublicWorkNotFoundError()
            return await self._repository.list_for_work(work_id)

    async def list_public(self, work_id: UUID) -> tuple[PublicMediaView, ...]:
        return await PublicMediaQueryService(self._session).list_public(work_id)

    @staticmethod
    def _validate_asset(asset: MediaAsset | None) -> PublicMediaKind:
        if asset is None or asset.status is not MediaStatus.ACTIVE:
            raise PublicMediaValidationError("Media must be an active retained asset.")
        try:
            return PUBLIC_MEDIA_MIME_KINDS[asset.mime_type]
        except KeyError as error:
            raise PublicMediaValidationError(
                "MIME type is not supported by the public gallery."
            ) from error

    @staticmethod
    def _plain_text(value: str | None, field: str) -> str | None:
        normalized = value.strip() if value else ""
        if len(normalized) > 500 or any(
            character in normalized for character in "<>\x00"
        ):
            raise PublicMediaValidationError(f"Media {field} is invalid.")
        return normalized or None

    @staticmethod
    def _require_admin(principal: AuthPrincipal) -> None:
        AuthorizationPolicy.require_capability(
            principal,
            PolicyRequirement(
                permission="public_content.manage",
                compatible_roles=PUBLIC_MEDIA_ADMIN_ROLES,
            ),
            PublicWorkForbiddenError,
        )

    def _event(self, work_id: UUID, event_type: str) -> None:
        _record_media_cache_event(
            self._outbox,
            self._payload_cipher,
            work_id=work_id,
            event_type=event_type,
        )


class PublicMediaWorker:
    def __init__(
        self,
        *,
        session: AsyncSession,
        gateway: PublicDerivativeGateway,
        environment: str,
        payload_cipher: OutboxPayloadCipher,
    ) -> None:
        self._session = session
        self._repository = PublicMediaRepository(session)
        self._gateway = gateway
        self._environment = environment
        self._outbox = OutboxRepository(session)
        self._payload_cipher = payload_cipher

    async def process(self, relation_id: UUID) -> None:
        async with self._session.begin():
            joined = await self._repository.get_relation_with_asset(
                relation_id, for_update=True
            )
            if joined is None:
                return
            relation, asset = joined
            if relation.derivative_status is DerivativeStatus.READY:
                return
            relation.derivative_status = DerivativeStatus.PROCESSING
            relation.attempt_count += 1
            relation.failure_code = None
            source_public_id = asset.cloudinary_public_id
            source_resource_type = asset.resource_type
            source_format = _SOURCE_FORMATS.get(asset.mime_type)
            media_kind = relation.media_kind
            duration_ms = asset.duration_ms
            width = asset.width
            height = asset.height
        if media_kind is not PublicMediaKind.IMAGE:
            async with self._session.begin():
                current = await self._repository.get_relation(
                    relation_id, for_update=True
                )
                if current is not None:
                    current.derivative_status = DerivativeStatus.READY
                    current.derivative_mime_type = asset.mime_type
                    current.duration_ms = duration_ms
                    current.derivative_width = width
                    current.derivative_height = height
                    self._event(current.public_work_id)
            return
        if source_format is None:
            await self._mark_failed(relation_id, "UNSUPPORTED_MIME")
            raise PublicMediaValidationError("Image MIME type is unsupported.")
        derivative_public_id = (
            f"ip-certificate/{self._environment}/public/derivatives/{relation_id}"
        )
        try:
            derivative = await self._gateway.create_public_derivative(
                source_public_id=source_public_id,
                source_resource_type=source_resource_type,
                source_format=source_format,
                derivative_public_id=derivative_public_id,
                transformation=IMAGE_DERIVATIVE_TRANSFORMATION,
            )
        except MediaProviderUnavailableError:
            await self._mark_failed(relation_id, "PROVIDER_UNAVAILABLE")
            raise
        async with self._session.begin():
            current = await self._repository.get_relation(relation_id, for_update=True)
            if current is None or current.derivative_status is DerivativeStatus.READY:
                return
            current.derivative_status = DerivativeStatus.READY
            current.derivative_public_id = derivative.public_id
            current.derivative_url = derivative.url
            current.derivative_mime_type = derivative.mime_type
            current.derivative_width = derivative.width
            current.derivative_height = derivative.height
            current.duration_ms = derivative.duration_ms
            current.failure_code = None
            self._event(current.public_work_id)

    async def _mark_failed(self, relation_id: UUID, code: str) -> None:
        async with self._session.begin():
            relation = await self._repository.get_relation(relation_id, for_update=True)
            if relation is not None:
                relation.derivative_status = DerivativeStatus.FAILED
                relation.failure_code = code

    def _event(self, work_id: UUID) -> None:
        _record_media_cache_event(
            self._outbox,
            self._payload_cipher,
            work_id=work_id,
            event_type="public_work.media_ready",
        )


def _record_media_cache_event(
    outbox: OutboxRepository,
    payload_cipher: OutboxPayloadCipher,
    *,
    work_id: UUID,
    event_type: str,
) -> None:
    encrypted = payload_cipher.encrypt(
        {"public_work_id": str(work_id), "invalidate_cache": "true"},
        event_type=event_type,
        aggregate_id=work_id,
    )
    outbox.add(
        OutboxEvent(
            event_type=event_type,
            aggregate_type="public_work",
            aggregate_id=work_id,
            payload_ciphertext=encrypted.ciphertext,
            payload_nonce=encrypted.nonce,
            key_id=encrypted.key_id,
        )
    )
