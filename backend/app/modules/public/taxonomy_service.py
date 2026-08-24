import json
import re
import unicodedata
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
from app.modules.dossiers.models import Category
from app.modules.public.catalog_cache import (
    PublicCatalogCache,
    public_taxonomy_cache_key,
)
from app.modules.public.catalog_repository import PublicWorkRepository
from app.modules.public.errors import (
    PublicWorkForbiddenError,
    PublicWorkNotFoundError,
    TaxonomyCycleError,
    TaxonomyInUseError,
    TaxonomyNotFoundError,
    TaxonomySlugConflictError,
)
from app.modules.public.models import PublicTag

TAXONOMY_ADMIN_ROLES = frozenset({"SUPER_ADMIN"})
SLUG_PATTERN = re.compile(r"[^a-z0-9]+")


def normalize_taxonomy_slug(value: str) -> str:
    value = value.replace("Đ", "D").replace("đ", "d")
    ascii_value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    )
    slug = SLUG_PATTERN.sub("-", ascii_value.lower()).strip("-")
    if not slug or len(slug) > 160:
        raise ValueError("taxonomy slug must contain 1 to 160 ASCII characters")
    return slug


@dataclass(frozen=True, slots=True)
class CategoryInput:
    name: str
    slug: str
    description: str | None
    parent_id: UUID | None
    display_order: int
    is_active: bool
    code: str | None = None


@dataclass(frozen=True, slots=True)
class TagInput:
    name: str
    slug: str
    is_active: bool


class TaxonomyService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        audit: AuditService,
        payload_cipher: OutboxPayloadCipher,
        cache: PublicCatalogCache | None = None,
    ) -> None:
        self._session = session
        self._repository = PublicWorkRepository(session)
        self._audit = audit
        self._outbox = OutboxRepository(session)
        self._payload_cipher = payload_cipher
        self._cache = cache

    async def create_category(
        self, principal: AuthPrincipal, data: CategoryInput, *, request_id: str
    ) -> Category:
        self._require_admin(principal)
        slug = normalize_taxonomy_slug(data.slug)
        try:
            async with self._session.begin():
                await self._validate_category(slug, data.parent_id, None)
                category = Category(
                    code=(data.code or slug.replace("-", "_")).upper(),
                    name=data.name.strip(),
                    slug=slug,
                    description=self._optional_text(data.description),
                    parent_id=data.parent_id,
                    display_order=data.display_order,
                    is_active=data.is_active,
                )
                self._repository.add_category(category)
                await self._session.flush()
                self._audit_change(principal, category, "created", request_id)
                self._event(
                    category.id,
                    aggregate_type="public_category",
                    event_type="public_category.created",
                    payload={"slug": category.slug or ""},
                )
            return category
        except IntegrityError as error:
            await self._session.rollback()
            raise TaxonomySlugConflictError() from error

    async def update_category(
        self,
        principal: AuthPrincipal,
        category_id: UUID,
        data: CategoryInput,
        *,
        request_id: str,
    ) -> Category:
        self._require_admin(principal)
        slug = normalize_taxonomy_slug(data.slug)
        try:
            async with self._session.begin():
                category = await self._repository.get_category(
                    category_id, for_update=True
                )
                if category is None:
                    raise TaxonomyNotFoundError()
                await self._validate_category(slug, data.parent_id, category_id)
                if category.is_active and not data.is_active:
                    if await self._repository.category_use_count(category_id):
                        raise TaxonomyInUseError()
                category.name = data.name.strip()
                category.slug = slug
                category.description = self._optional_text(data.description)
                category.parent_id = data.parent_id
                category.display_order = data.display_order
                category.is_active = data.is_active
                self._audit_change(principal, category, "updated", request_id)
                await self._session.flush()
                self._event(
                    category.id,
                    aggregate_type="public_category",
                    event_type="public_category.updated",
                    payload={"slug": category.slug or ""},
                )
            return category
        except IntegrityError as error:
            await self._session.rollback()
            raise TaxonomySlugConflictError() from error

    async def create_tag(
        self, principal: AuthPrincipal, data: TagInput, *, request_id: str
    ) -> PublicTag:
        self._require_admin(principal)
        slug = normalize_taxonomy_slug(data.slug)
        try:
            async with self._session.begin():
                if await self._repository.tag_slug_exists(slug):
                    raise TaxonomySlugConflictError()
                tag = PublicTag(
                    name=data.name.strip(), slug=slug, is_active=data.is_active
                )
                self._repository.add_tag(tag)
                await self._session.flush()
                self._audit.record(
                    actor_user_id=principal.user_id,
                    action="public_tag.created",
                    resource_type="public_tag",
                    resource_id=str(tag.id),
                    after=self._tag_data(tag),
                    request_id=request_id,
                )
                self._event(
                    tag.id,
                    aggregate_type="public_tag",
                    event_type="public_tag.created",
                    payload={"slug": tag.slug},
                )
            return tag
        except IntegrityError as error:
            await self._session.rollback()
            raise TaxonomySlugConflictError() from error

    async def update_tag(
        self,
        principal: AuthPrincipal,
        tag_id: UUID,
        data: TagInput,
        *,
        request_id: str,
    ) -> PublicTag:
        self._require_admin(principal)
        slug = normalize_taxonomy_slug(data.slug)
        try:
            async with self._session.begin():
                tag = await self._repository.get_tag(tag_id, for_update=True)
                if tag is None:
                    raise TaxonomyNotFoundError()
                if await self._repository.tag_slug_exists(slug, excluding=tag_id):
                    raise TaxonomySlugConflictError()
                tag.name = data.name.strip()
                tag.slug = slug
                tag.is_active = data.is_active
                self._audit.record(
                    actor_user_id=principal.user_id,
                    action="public_tag.updated",
                    resource_type="public_tag",
                    resource_id=str(tag.id),
                    after=self._tag_data(tag),
                    request_id=request_id,
                )
                await self._session.flush()
                self._event(
                    tag.id,
                    aggregate_type="public_tag",
                    event_type="public_tag.updated",
                    payload={"slug": tag.slug},
                )
            return tag
        except IntegrityError as error:
            await self._session.rollback()
            raise TaxonomySlugConflictError() from error

    async def assign_tags(
        self,
        principal: AuthPrincipal,
        work_id: UUID,
        tag_ids: tuple[UUID, ...],
        *,
        request_id: str,
    ) -> None:
        self._require_admin(principal)
        unique_ids = tuple(dict.fromkeys(tag_ids))
        async with self._session.begin():
            work = await self._repository.get_by_id(work_id, for_update=True)
            if work is None:
                raise PublicWorkNotFoundError()
            for tag_id in unique_ids:
                tag = await self._repository.get_tag(tag_id)
                if tag is None or not tag.is_active:
                    raise TaxonomyNotFoundError()
            await self._repository.replace_work_tags(work_id, unique_ids)
            self._audit.record(
                actor_user_id=principal.user_id,
                action="public_work.tags_updated",
                resource_type="public_work",
                resource_id=str(work_id),
                after={"tag_ids": [str(tag_id) for tag_id in unique_ids]},
                request_id=request_id,
            )
            self._event(
                work_id,
                aggregate_type="public_work",
                event_type="public_work.tags_updated",
                payload={"tag_count": str(len(unique_ids))},
            )

    async def list_categories(self, *, public_only: bool) -> tuple[Category, ...]:
        cache_key = public_taxonomy_cache_key("category-tree")
        if public_only and self._cache is not None:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                categories = self._deserialize_categories(cached)
                if categories is not None:
                    return categories
        async with self._session.begin():
            categories = await self._repository.list_categories(public_only=public_only)
        if public_only and self._cache is not None:
            await self._cache.set(
                cache_key,
                json.dumps(
                    [
                        {
                            "id": str(item.id),
                            "code": item.code,
                            "name": item.name,
                            "slug": item.slug,
                            "description": item.description,
                            "parent_id": (
                                str(item.parent_id) if item.parent_id else None
                            ),
                            "display_order": item.display_order,
                            "is_active": item.is_active,
                        }
                        for item in categories
                    ],
                    separators=(",", ":"),
                    sort_keys=True,
                ),
            )
        return categories

    async def list_tags(self, *, public_only: bool) -> tuple[PublicTag, ...]:
        cache_key = public_taxonomy_cache_key("tags")
        if public_only and self._cache is not None:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                tags = self._deserialize_tags(cached)
                if tags is not None:
                    return tags
        async with self._session.begin():
            tags = await self._repository.list_tags(public_only=public_only)
        if public_only and self._cache is not None:
            await self._cache.set(
                cache_key,
                json.dumps(
                    [
                        {
                            "id": str(item.id),
                            "name": item.name,
                            "slug": item.slug,
                            "is_active": item.is_active,
                        }
                        for item in tags
                    ],
                    separators=(",", ":"),
                    sort_keys=True,
                ),
            )
        return tags

    async def list_admin_categories(
        self, principal: AuthPrincipal
    ) -> tuple[Category, ...]:
        self._require_admin(principal)
        return await self.list_categories(public_only=False)

    async def list_admin_tags(self, principal: AuthPrincipal) -> tuple[PublicTag, ...]:
        self._require_admin(principal)
        return await self.list_tags(public_only=False)

    async def _validate_category(
        self, slug: str, parent_id: UUID | None, category_id: UUID | None
    ) -> None:
        if await self._repository.category_slug_exists(slug, excluding=category_id):
            raise TaxonomySlugConflictError()
        if parent_id is None:
            return
        parent = await self._repository.get_category(parent_id)
        if parent is None:
            raise TaxonomyNotFoundError()
        if category_id is not None and await self._repository.category_has_descendant(
            category_id, parent_id
        ):
            raise TaxonomyCycleError()

    def _audit_change(
        self,
        principal: AuthPrincipal,
        category: Category,
        action: str,
        request_id: str,
    ) -> None:
        self._audit.record(
            actor_user_id=principal.user_id,
            action=f"public_category.{action}",
            resource_type="public_category",
            resource_id=str(category.id),
            after={
                "name": category.name,
                "slug": category.slug,
                "parent_id": str(category.parent_id) if category.parent_id else None,
                "is_active": category.is_active,
            },
            request_id=request_id,
        )

    @staticmethod
    def _tag_data(tag: PublicTag) -> dict[str, object]:
        return {"name": tag.name, "slug": tag.slug, "is_active": tag.is_active}

    @staticmethod
    def _optional_text(value: str | None) -> str | None:
        normalized = value.strip() if value else ""
        return normalized or None

    @staticmethod
    def _require_admin(principal: AuthPrincipal) -> None:
        AuthorizationPolicy.require_capability(
            principal,
            PolicyRequirement(
                permission="public_content.manage",
                compatible_roles=TAXONOMY_ADMIN_ROLES,
            ),
            PublicWorkForbiddenError,
        )

    def _event(
        self,
        aggregate_id: UUID,
        *,
        aggregate_type: str,
        event_type: str,
        payload: dict[str, str],
    ) -> None:
        event_payload: dict[str, str] = {
            "invalidate_cache": "true",
            **payload,
        }
        encrypted = self._payload_cipher.encrypt(
            event_payload,
            event_type=event_type,
            aggregate_id=aggregate_id,
        )
        self._outbox.add(
            OutboxEvent(
                event_type=event_type,
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
                payload_ciphertext=encrypted.ciphertext,
                payload_nonce=encrypted.nonce,
                key_id=encrypted.key_id,
            )
        )

    @staticmethod
    def _deserialize_categories(value: str) -> tuple[Category, ...] | None:
        try:
            payload = json.loads(value)
            return tuple(
                Category(
                    id=UUID(item["id"]),
                    code=item["code"],
                    name=item["name"],
                    slug=item["slug"],
                    description=item["description"],
                    parent_id=(UUID(item["parent_id"]) if item["parent_id"] else None),
                    display_order=int(item["display_order"]),
                    is_active=bool(item["is_active"]),
                )
                for item in payload
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return None

    @staticmethod
    def _deserialize_tags(value: str) -> tuple[PublicTag, ...] | None:
        try:
            payload = json.loads(value)
            return tuple(
                PublicTag(
                    id=UUID(item["id"]),
                    name=item["name"],
                    slug=item["slug"],
                    is_active=bool(item["is_active"]),
                )
                for item in payload
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return None
