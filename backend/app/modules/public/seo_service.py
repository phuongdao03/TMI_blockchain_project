from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from math import ceil
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.public.catalog_repository import PublicWorkRepository
from app.modules.public.seo_cache import PublicSitemapCache


@dataclass(frozen=True, slots=True)
class PublicSitemapEntry:
    slug: str
    last_modified: datetime


@dataclass(frozen=True, slots=True)
class PublicSitemapManifest:
    generation: str
    total: int
    page_size: int
    page_count: int
    generated_at: datetime


class PublicSeoService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        cache: PublicSitemapCache | None = None,
        page_size: int = 10_000,
    ) -> None:
        if not 1 <= page_size <= 50_000:
            raise ValueError("Sitemap page size must be between 1 and 50000.")
        self.repository = PublicWorkRepository(session)
        self._cache = cache
        self._page_size = page_size
        self._snapshot_manifest: PublicSitemapManifest | None = None

    async def manifest(self) -> PublicSitemapManifest:
        if self._snapshot_manifest is not None:
            return self._snapshot_manifest
        cached = await self._cache.get_manifest() if self._cache else None
        parsed = self._parse_manifest(cached)
        if parsed is not None:
            self._snapshot_manifest = parsed
            return parsed
        return await self.rebuild()

    async def page(self, page: int) -> tuple[PublicSitemapEntry, ...]:
        manifest = await self.manifest()
        if page < 1 or page > manifest.page_count:
            return ()
        cached = (
            await self._cache.get_page(manifest.generation, page)
            if self._cache
            else None
        )
        parsed = self._parse_page(cached)
        if parsed is not None:
            return parsed
        return await self._query_page(page, now=manifest.generated_at)

    async def rebuild(self) -> PublicSitemapManifest:
        now = datetime.now(UTC)
        total = await self.repository.count_sitemap_works(now=now)
        page_count = ceil(total / self._page_size)
        pages = [
            await self._query_page(page, now=now) for page in range(1, page_count + 1)
        ]
        manifest = PublicSitemapManifest(
            generation=uuid4().hex,
            total=total,
            page_size=self._page_size,
            page_count=page_count,
            generated_at=now,
        )
        self._snapshot_manifest = manifest
        if self._cache:
            await self._cache.replace(
                self._manifest_payload(manifest),
                [self._page_payload(page) for page in pages],
            )
        return manifest

    async def _query_page(
        self, page: int, *, now: datetime
    ) -> tuple[PublicSitemapEntry, ...]:
        works = await self.repository.list_sitemap_works(
            now=now,
            offset=(page - 1) * self._page_size,
            limit=self._page_size,
        )
        return tuple(
            PublicSitemapEntry(slug=work.slug, last_modified=work.updated_at)
            for work in works
        )

    @staticmethod
    def _manifest_payload(manifest: PublicSitemapManifest) -> dict[str, object]:
        payload = asdict(manifest)
        payload["generated_at"] = manifest.generated_at.isoformat()
        return payload

    @staticmethod
    def _page_payload(
        entries: tuple[PublicSitemapEntry, ...],
    ) -> list[dict[str, object]]:
        return [
            {"slug": entry.slug, "last_modified": entry.last_modified.isoformat()}
            for entry in entries
        ]

    @staticmethod
    def _parse_manifest(
        payload: dict[str, object] | None,
    ) -> PublicSitemapManifest | None:
        if payload is None:
            return None
        try:
            return PublicSitemapManifest(
                generation=str(payload["generation"]),
                total=int(str(payload["total"])),
                page_size=int(str(payload["page_size"])),
                page_count=int(str(payload["page_count"])),
                generated_at=datetime.fromisoformat(str(payload["generated_at"])),
            )
        except (KeyError, TypeError, ValueError):
            return None

    @staticmethod
    def _parse_page(
        payload: list[dict[str, object]] | None,
    ) -> tuple[PublicSitemapEntry, ...] | None:
        if payload is None:
            return None
        try:
            return tuple(
                PublicSitemapEntry(
                    slug=str(item["slug"]),
                    last_modified=datetime.fromisoformat(str(item["last_modified"])),
                )
                for item in payload
            )
        except (KeyError, TypeError, ValueError):
            return None
