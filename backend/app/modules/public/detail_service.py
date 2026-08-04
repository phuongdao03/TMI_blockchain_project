from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from pydantic import TypeAdapter, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.blockchain.models import (
    BlockchainTransactionStatus,
    CertificateStatus,
)
from app.modules.public.catalog_cache import PublicCatalogCache, public_detail_cache_key
from app.modules.public.catalog_query_service import PublicTagView, PublicWorkCardView
from app.modules.public.catalog_repository import PublicWorkRepository
from app.modules.public.media_service import PublicMediaQueryService, PublicMediaView
from app.modules.public.models import PublicationStatus, PublicWorkVisibility


@dataclass(frozen=True, slots=True)
class PublicCertificateSummary:
    certificate_number: str
    status: CertificateStatus
    issued_at: datetime
    expires_at: datetime | None


@dataclass(frozen=True, slots=True)
class PublicProofSummary:
    network: str
    transaction_hash: str | None
    status: BlockchainTransactionStatus
    confirmations: int
    confirmed_at: datetime | None


@dataclass(frozen=True, slots=True)
class PublicWorkDetailView:
    id: UUID
    slug: str
    title: str
    short_description: str
    full_description: str | None
    author_display_name: str | None
    organization_display_name: str | None
    category_name: str
    category_slug: str
    tags: tuple[PublicTagView, ...]
    published_at: datetime
    visibility: PublicWorkVisibility
    certificate: PublicCertificateSummary | None
    proof: PublicProofSummary | None
    media: tuple[PublicMediaView, ...]
    related_works: tuple[PublicWorkCardView, ...]
    canonical_slug: str
    redirected: bool


class PublicWorkDetailService:
    _adapter: TypeAdapter[PublicWorkDetailView] = TypeAdapter(PublicWorkDetailView)

    def __init__(
        self,
        session: AsyncSession,
        *,
        cache: PublicCatalogCache | None = None,
    ) -> None:
        self._session = session
        self._repository = PublicWorkRepository(session)
        self._media = PublicMediaQueryService(session)
        self._cache = cache

    async def get(self, slug: str) -> PublicWorkDetailView | None:
        async with self._session.begin():
            resolved = await self._repository.resolve_slug(slug)
            if resolved is None:
                return None
            work, redirected = resolved
            if (
                work.publication_status is not PublicationStatus.PUBLISHED
                or work.visibility
                not in {PublicWorkVisibility.PUBLIC, PublicWorkVisibility.UNLISTED}
            ):
                return None
            work_version = work.version
        cache_key = public_detail_cache_key(slug)
        if self._cache is not None:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                cached_detail = self._deserialize(cached, expected_version=work_version)
                if cached_detail is not None:
                    return cached_detail
        async with self._session.begin():
            row = await self._repository.get_public_work_detail(work.id)
        if row is None or row.work.published_at is None or row.category.slug is None:
            return None
        certificate = (
            PublicCertificateSummary(
                row.certificate.certificate_number,
                row.certificate.status,
                row.certificate.issued_at,
                row.certificate.expires_at,
            )
            if row.certificate is not None
            else None
        )
        transaction = row.transaction
        proof = (
            PublicProofSummary(
                transaction.network,
                transaction.tx_hash,
                transaction.status,
                transaction.confirmations,
                transaction.confirmed_at,
            )
            if transaction is not None
            else None
        )
        async with self._session.begin():
            related_rows = await self._repository.list_related_public_works(
                work_id=row.work.id,
                category_id=row.work.category_id,
                tag_ids=tuple(tag.id for tag in row.tags),
                now=datetime.now(UTC),
            )
        related_works = tuple(
            PublicWorkCardView(
                id=related.work.id,
                slug=related.work.slug,
                title=related.work.title,
                short_description=related.work.short_description,
                author_display_name=related.work.author_display_name,
                category_name=related.category.name,
                category_slug=related.category.slug or "",
                tags=tuple(PublicTagView(tag.name, tag.slug) for tag in related.tags),
                published_at=related.work.published_at,
                is_featured=(
                    related.work.featured_at is not None
                    and (
                        related.work.featured_until is None
                        or related.work.featured_until > datetime.now(UTC)
                    )
                ),
                thumbnail_url=related.thumbnail_url,
                thumbnail_alt_text=related.thumbnail_alt_text,
            )
            for related in related_rows
            if related.work.published_at is not None
            and related.category.slug is not None
        )
        media = await self._media.list_public(row.work.id)
        detail = PublicWorkDetailView(
            id=row.work.id,
            slug=row.work.slug,
            title=row.work.title,
            short_description=row.work.short_description,
            full_description=row.work.full_description,
            author_display_name=row.work.author_display_name,
            organization_display_name=(
                row.organization.display_name if row.organization else None
            ),
            category_name=row.category.name,
            category_slug=row.category.slug,
            tags=tuple(PublicTagView(tag.name, tag.slug) for tag in row.tags),
            published_at=row.work.published_at,
            visibility=row.work.visibility,
            certificate=certificate,
            proof=proof,
            media=media,
            related_works=related_works,
            canonical_slug=row.work.slug,
            redirected=redirected,
        )
        if self._cache is not None:
            await self._cache.set(cache_key, self._serialize(detail, work_version))
        return detail

    @classmethod
    def _serialize(cls, detail: PublicWorkDetailView, version: int) -> str:
        import json

        return json.dumps(
            {
                "version": version,
                "detail": cls._adapter.dump_python(detail, mode="json"),
            },
            separators=(",", ":"),
            sort_keys=True,
        )

    @classmethod
    def _deserialize(
        cls, value: str, *, expected_version: int
    ) -> PublicWorkDetailView | None:
        import json

        try:
            payload = json.loads(value)
            if int(payload["version"]) != expected_version:
                return None
            return cls._adapter.validate_python(payload["detail"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError, ValidationError):
            return None
