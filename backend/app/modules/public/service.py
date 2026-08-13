import json

from pydantic import TypeAdapter, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.public.catalog_cache import (
    PublicCatalogCache,
    public_taxonomy_cache_key,
)
from app.modules.public.repository import PublicRepository, PublicRow
from app.modules.public.types import (
    PublicAssetDetailView,
    PublicAssetView,
    PublicCategoryView,
    PublicCertificateVersionView,
    PublicHomeView,
    PublicMapMarkerView,
)
from app.modules.public.verification import public_evidence_proofs


class PublicCatalogService:
    _category_adapter: TypeAdapter[tuple[PublicCategoryView, ...]] = TypeAdapter(
        tuple[PublicCategoryView, ...]
    )

    def __init__(
        self,
        session: AsyncSession,
        *,
        cache: PublicCatalogCache | None = None,
    ) -> None:
        self._session = session
        self.repository = PublicRepository(session)
        self._cache = cache

    async def home(self) -> PublicHomeView:
        async with self._session.begin():
            rows, total = await self.repository.list_assets(
                query=None,
                category=None,
                offset=0,
                limit=6,
            )
            categories = await self.repository.list_categories()
        return PublicHomeView(
            certificate_count=total,
            category_count=sum(1 for _, count in categories if count > 0),
            latest_assets=tuple(self._asset(row) for row in rows),
        )

    async def categories(self) -> tuple[PublicCategoryView, ...]:
        cache_key = public_taxonomy_cache_key("categories")
        if self._cache is not None:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                try:
                    return self._category_adapter.validate_json(cached)
                except ValidationError:
                    pass
        async with self._session.begin():
            rows = await self.repository.list_categories()
        categories = tuple(
            PublicCategoryView(
                id=category.id,
                code=category.code,
                name=category.name,
                slug=category.slug,
                description=category.description,
                asset_count=count,
            )
            for category, count in rows
        )
        if self._cache is not None:
            await self._cache.set(
                cache_key,
                json.dumps(
                    self._category_adapter.dump_python(categories, mode="json"),
                    separators=(",", ":"),
                    sort_keys=True,
                ),
            )
        return categories

    async def certificate_versions(
        self,
        certificate_number: str,
    ) -> tuple[PublicCertificateVersionView, ...]:
        async with self._session.begin():
            rows = await self.repository.list_certificate_versions(
                certificate_number.strip().upper()
            )
        return tuple(
            PublicCertificateVersionView(
                version_no=version.version_no,
                status=version.status,
                metadata_hash=version.metadata_hash,
                transaction_hash=(
                    transaction.tx_hash if transaction is not None else None
                ),
                block_number=(
                    transaction.receipt_block_number
                    if transaction is not None
                    else None
                ),
                confirmed_at=(
                    transaction.confirmed_at if transaction is not None else None
                ),
                created_at=version.created_at,
                issuer_label="TMI Certificate",
                documents=public_evidence_proofs(version.metadata_json),
            )
            for version, transaction in rows
        )

    async def assets(
        self,
        *,
        query: str | None,
        category: str | None,
        page: int,
        page_size: int,
    ) -> tuple[tuple[PublicAssetView, ...], int]:
        async with self._session.begin():
            rows, total = await self.repository.list_assets(
                query=query,
                category=category,
                offset=(page - 1) * page_size,
                limit=page_size,
            )
        return tuple(self._asset(row) for row in rows), total

    async def asset(self, slug: str) -> PublicAssetDetailView | None:
        async with self._session.begin():
            row = await self.repository.get_asset(slug)
        if row is None:
            return None
        _, version, _, _, transaction = row
        return PublicAssetDetailView(
            asset=self._asset(row),
            metadata=self._public_metadata(version.metadata_json),
            network=transaction.network if transaction is not None else None,
            contract_address=(
                transaction.contract_address if transaction is not None else None
            ),
            confirmations=(transaction.confirmations if transaction is not None else 0),
        )

    async def map_markers(
        self,
        *,
        category: str | None,
        min_latitude: float | None = None,
        max_latitude: float | None = None,
        min_longitude: float | None = None,
        max_longitude: float | None = None,
    ) -> tuple[PublicMapMarkerView, ...]:
        async with self._session.begin():
            rows, _ = await self.repository.list_assets(
                query=None,
                category=category,
                offset=0,
                limit=500,
            )
        markers: list[PublicMapMarkerView] = []
        for row in rows:
            location = row[1].metadata_json.get("location")
            if not isinstance(location, dict):
                continue
            latitude = location.get("latitude")
            longitude = location.get("longitude")
            if not isinstance(latitude, (float, int)) or not isinstance(
                longitude, (float, int)
            ):
                continue
            if min_latitude is not None and latitude < min_latitude:
                continue
            if max_latitude is not None and latitude > max_latitude:
                continue
            if min_longitude is not None and longitude < min_longitude:
                continue
            if max_longitude is not None and longitude > max_longitude:
                continue
            asset = self._asset(row)
            markers.append(
                PublicMapMarkerView(
                    slug=asset.slug,
                    title=asset.title,
                    category_name=asset.category_name,
                    latitude=float(latitude),
                    longitude=float(longitude),
                )
            )
        return tuple(markers)

    @staticmethod
    def _asset(row: PublicRow) -> PublicAssetView:
        certificate, _, dossier, category, transaction = row
        if dossier.slug is None:
            raise ValueError("Published public dossier must have a slug.")
        return PublicAssetView(
            slug=dossier.slug,
            title=dossier.title,
            summary=dossier.summary,
            category_code=category.code,
            category_name=category.name,
            certificate_number=certificate.certificate_number,
            certificate_status=certificate.status,
            issued_at=certificate.issued_at,
            transaction_hash=(transaction.tx_hash if transaction is not None else None),
        )

    @staticmethod
    def _public_metadata(metadata: dict[str, object]) -> dict[str, object]:
        return {
            key: value
            for key, value in metadata.items()
            if key
            in {
                "schemaVersion",
                "certificate",
                "dossier",
                "asset",
                "issuedAt",
                "expiresAt",
                "publicEvidences",
                "blockchain",
            }
        }
