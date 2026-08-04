import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.dossiers.models import Dossier
from app.modules.public.catalog_repository import PublicWorkRepository
from app.modules.public.models import (
    PublicationStatus,
    PublicWork,
    PublicWorkVisibility,
)

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RESERVED_SLUGS = frozenset(
    {
        "admin",
        "api",
        "login",
        "register",
        "search",
        "sitemap",
        "verify",
    }
)


@dataclass(frozen=True, slots=True)
class PublicWorkBackfillReport:
    scanned: int
    eligible: int
    created: int
    skipped: int
    skip_reasons: dict[str, int]


class PublicWorkDraftBackfill:
    def __init__(self, session: AsyncSession, *, batch_size: int = 500) -> None:
        if batch_size < 1 or batch_size > 5_000:
            raise ValueError("batch_size must be between 1 and 5000")
        self._session = session
        self._repository = PublicWorkRepository(session)
        self._batch_size = batch_size

    async def run(self, *, dry_run: bool = True) -> PublicWorkBackfillReport:
        if self._session.in_transaction():
            return await self._run(dry_run=dry_run)
        async with self._session.begin():
            return await self._run(dry_run=dry_run)

    async def _run(self, *, dry_run: bool) -> PublicWorkBackfillReport:
        reasons: Counter[str] = Counter()
        reserved_in_batch: set[str] = set()
        cursor = None
        scanned = 0
        eligible = 0
        while True:
            sources = await self._repository.list_backfill_sources(
                after=cursor,
                limit=self._batch_size,
            )
            if not sources:
                break
            scanned += len(sources)
            for source in sources:
                draft, reason = await self._draft_from_source(
                    source.dossier,
                    certificate_id=source.certificate_id,
                    reserved_in_batch=reserved_in_batch,
                )
                if draft is None:
                    reasons[reason or "invalid_legacy_data"] += 1
                    continue
                eligible += 1
                reserved_in_batch.add(draft.slug)
                if not dry_run:
                    self._repository.add(draft)
            if not dry_run:
                await self._session.flush()
            last_dossier = sources[-1].dossier
            cursor = last_dossier.id

        return PublicWorkBackfillReport(
            scanned=scanned,
            eligible=eligible,
            created=0 if dry_run else eligible,
            skipped=sum(reasons.values()),
            skip_reasons=dict(sorted(reasons.items())),
        )

    async def _draft_from_source(
        self,
        dossier: Dossier,
        *,
        certificate_id: UUID | None,
        reserved_in_batch: set[str],
    ) -> tuple[PublicWork | None, str | None]:
        title = dossier.title.strip()
        if not title:
            return None, "missing_public_title"
        description = (dossier.summary or "").strip()
        if not description:
            return None, "missing_public_description"
        slug = await self._available_slug(dossier, reserved_in_batch)
        if slug is None:
            return None, "invalid_public_slug"
        return (
            PublicWork(
                dossier_id=dossier.id,
                certificate_id=certificate_id,
                owner_user_id=dossier.owner_user_id,
                organization_id=dossier.organization_id,
                slug=slug,
                title=title,
                short_description=description[:500],
                full_description=None,
                publication_status=PublicationStatus.DRAFT,
                visibility=PublicWorkVisibility.PRIVATE,
                author_display_name=None,
                category_id=dossier.category_id,
                thumbnail_media_id=None,
                published_at=None,
            ),
            None,
        )

    async def _available_slug(
        self,
        dossier: Dossier,
        reserved_in_batch: set[str],
    ) -> str | None:
        preferred = (dossier.slug or "").strip().lower()
        if not self._valid_slug(preferred):
            preferred = self._slugify(dossier.title)
        candidates = (
            preferred,
            f"{preferred}-{self._slugify(dossier.code)}" if preferred else "",
        )
        for candidate in candidates:
            candidate = candidate[:180].rstrip("-")
            if (
                self._valid_slug(candidate)
                and candidate not in reserved_in_batch
                and not await self._repository.slug_exists(candidate)
            ):
                return candidate
        return None

    @staticmethod
    def _valid_slug(slug: str) -> bool:
        return (
            0 < len(slug) <= 180
            and slug not in RESERVED_SLUGS
            and SLUG_PATTERN.fullmatch(slug) is not None
        )

    @staticmethod
    def _slugify(value: str) -> str:
        ascii_value = (
            unicodedata.normalize("NFKD", value)
            .encode("ascii", "ignore")
            .decode("ascii")
        )
        return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")
