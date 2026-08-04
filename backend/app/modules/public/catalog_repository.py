from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from sqlalchemy import and_, delete, exists, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.modules.blockchain.models import (
    BlockchainTransaction,
    Certificate,
    CertificateVersion,
)
from app.modules.dossiers.models import Category, Dossier, DossierStatus
from app.modules.media.models import MediaAsset
from app.modules.organizations.models import Organization
from app.modules.public.models import (
    DerivativeStatus,
    PublicationStatus,
    PublicMediaKind,
    PublicTag,
    PublicWork,
    PublicWorkMedia,
    PublicWorkSlugHistory,
    PublicWorkTag,
    PublicWorkVisibility,
)


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class PublicWorkBackfillSource:
    dossier: Dossier
    certificate_id: UUID | None


@dataclass(frozen=True, slots=True)
class PublicWorkPublicationContext:
    work: PublicWork
    dossier: Dossier
    certificate: Certificate | None
    category: Category
    thumbnail: MediaAsset | None


@dataclass(frozen=True, slots=True)
class PublicWorkListRow:
    work: PublicWork
    category: Category
    tags: tuple[PublicTag, ...]
    thumbnail_url: str | None
    thumbnail_alt_text: str | None


@dataclass(frozen=True, slots=True)
class PublicWorkDetailRow:
    work: PublicWork
    category: Category
    organization: Organization | None
    certificate: Certificate | None
    transaction: BlockchainTransaction | None
    tags: tuple[PublicTag, ...]


class PublicWorkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, work: PublicWork) -> None:
        self._session.add(work)

    def add_slug_history(self, history: PublicWorkSlugHistory) -> None:
        self._session.add(history)

    def add_tag(self, tag: PublicTag) -> None:
        self._session.add(tag)

    def add_category(self, category: Category) -> None:
        self._session.add(category)

    async def _ready_thumbnails(
        self, works: tuple[PublicWork, ...]
    ) -> dict[UUID, PublicWorkMedia]:
        work_ids = tuple(work.id for work in works)
        if not work_ids:
            return {}
        media_rows = await self._session.scalars(
            select(PublicWorkMedia)
            .where(
                PublicWorkMedia.public_work_id.in_(work_ids),
                PublicWorkMedia.media_kind == PublicMediaKind.IMAGE,
                PublicWorkMedia.derivative_status == DerivativeStatus.READY,
                PublicWorkMedia.derivative_url.is_not(None),
            )
            .order_by(
                PublicWorkMedia.public_work_id,
                PublicWorkMedia.sort_order,
                PublicWorkMedia.created_at,
                PublicWorkMedia.id,
            )
        )
        candidates: dict[UUID, list[PublicWorkMedia]] = {
            work_id: [] for work_id in work_ids
        }
        for media in media_rows:
            candidates[media.public_work_id].append(media)
        selected: dict[UUID, PublicWorkMedia] = {}
        for work in works:
            work_candidates = candidates[work.id]
            if not work_candidates:
                continue
            selected[work.id] = next(
                (
                    media
                    for media in work_candidates
                    if media.media_asset_id == work.thumbnail_media_id
                ),
                work_candidates[0],
            )
        return selected

    async def get_by_id(
        self,
        work_id: UUID,
        *,
        for_update: bool = False,
    ) -> PublicWork | None:
        statement = select(PublicWork).where(
            PublicWork.id == work_id,
            PublicWork.deleted_at.is_(None),
        )
        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        return cast(PublicWork | None, await self._session.scalar(statement))

    async def get_by_slug(self, slug: str) -> PublicWork | None:
        return cast(
            PublicWork | None,
            await self._session.scalar(
                select(PublicWork).where(
                    PublicWork.slug == slug,
                    PublicWork.deleted_at.is_(None),
                )
            ),
        )

    async def find_published_public_id(self, slug: str) -> UUID | None:
        statement = select(PublicWork.id).where(
            PublicWork.slug == slug,
            PublicWork.publication_status == PublicationStatus.PUBLISHED,
            PublicWork.visibility == PublicWorkVisibility.PUBLIC,
            PublicWork.deleted_at.is_(None),
        )
        return cast(UUID | None, await self._session.scalar(statement))

    async def get_by_dossier_id(self, dossier_id: UUID) -> PublicWork | None:
        return cast(
            PublicWork | None,
            await self._session.scalar(
                select(PublicWork).where(
                    PublicWork.dossier_id == dossier_id,
                    PublicWork.deleted_at.is_(None),
                )
            ),
        )

    async def list_admin_works(
        self,
        *,
        query: str | None,
        status: PublicationStatus | None,
        offset: int,
        limit: int,
    ) -> tuple[tuple[PublicWork, ...], int]:
        filters: list[ColumnElement[bool]] = [PublicWork.deleted_at.is_(None)]
        if status is not None:
            filters.append(PublicWork.publication_status == status)
        if query:
            escaped = (
                query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            )
            pattern = f"%{escaped}%"
            filters.append(
                or_(
                    PublicWork.title.ilike(pattern, escape="\\"),
                    PublicWork.slug.ilike(pattern, escape="\\"),
                )
            )
        rows = await self._session.scalars(
            select(PublicWork)
            .where(*filters)
            .order_by(PublicWork.updated_at.desc(), PublicWork.id.desc())
            .offset(offset)
            .limit(limit)
        )
        total = await self._session.scalar(
            select(func.count()).select_from(PublicWork).where(*filters)
        )
        return tuple(rows), int(total or 0)

    async def get_publication_context(
        self,
        work_id: UUID,
        *,
        for_update: bool = False,
    ) -> PublicWorkPublicationContext | None:
        statement = (
            select(PublicWork, Dossier, Certificate, Category, MediaAsset)
            .join(Dossier, Dossier.id == PublicWork.dossier_id)
            .join(Category, Category.id == PublicWork.category_id)
            .outerjoin(Certificate, Certificate.id == PublicWork.certificate_id)
            .outerjoin(MediaAsset, MediaAsset.id == PublicWork.thumbnail_media_id)
            .where(
                PublicWork.id == work_id,
                PublicWork.deleted_at.is_(None),
            )
        )
        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        row = (await self._session.execute(statement)).one_or_none()
        if row is None:
            return None
        return PublicWorkPublicationContext(
            work=row[0],
            dossier=row[1],
            certificate=row[2],
            category=row[3],
            thumbnail=row[4],
        )

    async def claim_version(self, work: PublicWork, expected_version: int) -> bool:
        result = await self._session.execute(
            update(PublicWork)
            .where(
                PublicWork.id == work.id,
                PublicWork.version == expected_version,
            )
            .values(version=PublicWork.version + 1)
            .execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:  # type: ignore[attr-defined]
            return False
        work.version = expected_version + 1
        return True

    async def list_due_publication_ids(
        self,
        *,
        now: datetime,
        limit: int,
    ) -> tuple[UUID, ...]:
        rows = await self._session.scalars(
            select(PublicWork.id)
            .where(
                PublicWork.publication_status == PublicationStatus.PENDING_PUBLICATION,
                PublicWork.scheduled_publish_at.is_not(None),
                PublicWork.scheduled_publish_at <= now,
                PublicWork.deleted_at.is_(None),
            )
            .order_by(PublicWork.scheduled_publish_at, PublicWork.id)
            .limit(limit)
        )
        return tuple(rows.all())

    async def get_category(
        self, category_id: UUID, *, for_update: bool = False
    ) -> Category | None:
        statement = select(Category).where(Category.id == category_id)
        if for_update:
            statement = statement.with_for_update()
        return cast(Category | None, await self._session.scalar(statement))

    async def get_tag(
        self, tag_id: UUID, *, for_update: bool = False
    ) -> PublicTag | None:
        statement = select(PublicTag).where(PublicTag.id == tag_id)
        if for_update:
            statement = statement.with_for_update()
        return cast(PublicTag | None, await self._session.scalar(statement))

    async def category_slug_exists(
        self, slug: str, *, excluding: UUID | None = None
    ) -> bool:
        filters = [Category.slug == slug]
        if excluding is not None:
            filters.append(Category.id != excluding)
        return bool(await self._session.scalar(select(exists().where(*filters))))

    async def tag_slug_exists(
        self, slug: str, *, excluding: UUID | None = None
    ) -> bool:
        filters = [PublicTag.slug == slug]
        if excluding is not None:
            filters.append(PublicTag.id != excluding)
        return bool(await self._session.scalar(select(exists().where(*filters))))

    async def list_categories(self, *, public_only: bool) -> tuple[Category, ...]:
        filters = (
            (Category.is_active.is_(True), Category.slug.is_not(None))
            if public_only
            else ()
        )
        rows = await self._session.scalars(
            select(Category)
            .where(*filters)
            .order_by(Category.display_order, Category.name)
        )
        return tuple(rows.all())

    async def list_tags(self, *, public_only: bool) -> tuple[PublicTag, ...]:
        filters = (PublicTag.is_active.is_(True),) if public_only else ()
        rows = await self._session.scalars(
            select(PublicTag).where(*filters).order_by(PublicTag.name)
        )
        return tuple(rows.all())

    async def category_has_descendant(self, category_id: UUID, parent_id: UUID) -> bool:
        cursor: UUID | None = parent_id
        visited: set[UUID] = set()
        while cursor is not None:
            if cursor == category_id or cursor in visited:
                return True
            visited.add(cursor)
            cursor = await self._session.scalar(
                select(Category.parent_id).where(Category.id == cursor)
            )
        return False

    async def category_use_count(self, category_id: UUID) -> int:
        total = await self._session.scalar(
            select(func.count())
            .select_from(PublicWork)
            .where(
                PublicWork.category_id == category_id,
                PublicWork.deleted_at.is_(None),
                PublicWork.publication_status != PublicationStatus.ARCHIVED,
            )
        )
        return int(total or 0)

    async def replace_work_tags(
        self, public_work_id: UUID, tag_ids: tuple[UUID, ...]
    ) -> None:
        await self._session.execute(
            delete(PublicWorkTag).where(PublicWorkTag.public_work_id == public_work_id)
        )
        self._session.add_all(
            PublicWorkTag(public_work_id=public_work_id, tag_id=tag_id)
            for tag_id in tag_ids
        )

    async def list_work_tag_ids(self, public_work_id: UUID) -> tuple[UUID, ...]:
        rows = await self._session.scalars(
            select(PublicWorkTag.tag_id)
            .where(PublicWorkTag.public_work_id == public_work_id)
            .order_by(PublicWorkTag.tag_id)
        )
        return tuple(rows.all())

    async def list_public_works(
        self,
        *,
        query: str | None,
        category_slug: str | None,
        tag_slug: str | None,
        organization_id: UUID | None,
        published_from: datetime | None,
        published_to: datetime | None,
        sort: str,
        offset: int,
        limit: int,
        now: datetime,
    ) -> tuple[tuple[PublicWorkListRow, ...], int]:
        filters = [
            PublicWork.publication_status == PublicationStatus.PUBLISHED,
            PublicWork.visibility == PublicWorkVisibility.PUBLIC,
            PublicWork.deleted_at.is_(None),
            PublicWork.published_at.is_not(None),
            Category.is_active.is_(True),
        ]
        if query:
            escaped = (
                query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            )
            pattern = f"%{escaped}%"
            filters.append(
                or_(
                    PublicWork.title.ilike(pattern, escape="\\"),
                    PublicWork.short_description.ilike(pattern, escape="\\"),
                    PublicWork.author_display_name.ilike(pattern, escape="\\"),
                )
            )
        if category_slug:
            filters.append(Category.slug == category_slug)
        if organization_id:
            filters.append(PublicWork.organization_id == organization_id)
        if published_from:
            filters.append(PublicWork.published_at >= published_from)
        if published_to:
            filters.append(PublicWork.published_at <= published_to)
        if tag_slug:
            filters.append(
                exists(
                    select(PublicWorkTag.tag_id)
                    .join(PublicTag, PublicTag.id == PublicWorkTag.tag_id)
                    .where(
                        PublicWorkTag.public_work_id == PublicWork.id,
                        PublicTag.slug == tag_slug,
                        PublicTag.is_active.is_(True),
                    )
                )
            )
        featured = and_(
            PublicWork.featured_at.is_not(None),
            PublicWork.featured_at <= now,
            or_(
                PublicWork.featured_until.is_(None),
                PublicWork.featured_until > now,
            ),
        )
        orders = {
            "newest": (PublicWork.published_at.desc(), PublicWork.id.desc()),
            "popular": (
                PublicWork.view_count.desc(),
                PublicWork.published_at.desc(),
                PublicWork.id.desc(),
            ),
            "featured": (
                featured.desc(),
                PublicWork.published_at.desc(),
                PublicWork.id.desc(),
            ),
        }
        base = select(PublicWork, Category).join(
            Category, Category.id == PublicWork.category_id
        )
        rows = (
            await self._session.execute(
                base.where(*filters).order_by(*orders[sort]).offset(offset).limit(limit)
            )
        ).all()
        total = await self._session.scalar(
            select(func.count())
            .select_from(PublicWork)
            .join(Category, Category.id == PublicWork.category_id)
            .where(*filters)
        )
        work_ids = tuple(row[0].id for row in rows)
        tags_by_work: dict[UUID, list[PublicTag]] = {
            work_id: [] for work_id in work_ids
        }
        if work_ids:
            tag_rows = await self._session.execute(
                select(PublicWorkTag.public_work_id, PublicTag)
                .join(PublicTag, PublicTag.id == PublicWorkTag.tag_id)
                .where(
                    PublicWorkTag.public_work_id.in_(work_ids),
                    PublicTag.is_active.is_(True),
                )
                .order_by(PublicTag.name, PublicTag.id)
            )
            for work_id, tag in tag_rows.tuples():
                tags_by_work[work_id].append(tag)
        thumbnails = await self._ready_thumbnails(tuple(row[0] for row in rows))

        def to_list_row(work: PublicWork, category: Category) -> PublicWorkListRow:
            selected = thumbnails.get(work.id)
            return PublicWorkListRow(
                work,
                category,
                tuple(tags_by_work[work.id]),
                selected.derivative_url if selected else None,
                selected.alt_text if selected else None,
            )

        return (
            tuple(to_list_row(row[0], row[1]) for row in rows),
            int(total or 0),
        )

    async def list_featured_public_works(
        self,
        *,
        now: datetime,
        limit: int,
    ) -> tuple[PublicWorkListRow, ...]:
        rows, _ = await self.list_public_works(
            query=None,
            category_slug=None,
            tag_slug=None,
            organization_id=None,
            published_from=None,
            published_to=None,
            sort="featured",
            offset=0,
            limit=limit,
            now=now,
        )
        return tuple(
            row
            for row in rows
            if row.work.featured_at is not None
            and _as_utc(row.work.featured_at) <= now
            and (
                row.work.featured_until is None
                or _as_utc(row.work.featured_until) > now
            )
        )

    async def all_work_ids_are_public(self, work_ids: tuple[UUID, ...]) -> bool:
        if not work_ids:
            return True
        total = await self._session.scalar(
            select(func.count())
            .select_from(PublicWork)
            .where(
                PublicWork.id.in_(work_ids),
                PublicWork.publication_status == PublicationStatus.PUBLISHED,
                PublicWork.visibility == PublicWorkVisibility.PUBLIC,
                PublicWork.deleted_at.is_(None),
            )
        )
        return int(total or 0) == len(work_ids)

    async def get_public_work_detail(self, work_id: UUID) -> PublicWorkDetailRow | None:
        row = (
            await self._session.execute(
                select(
                    PublicWork,
                    Category,
                    Organization,
                    Certificate,
                    BlockchainTransaction,
                )
                .join(Category, Category.id == PublicWork.category_id)
                .outerjoin(
                    Organization,
                    Organization.id == PublicWork.organization_id,
                )
                .outerjoin(Certificate, Certificate.id == PublicWork.certificate_id)
                .outerjoin(
                    CertificateVersion,
                    (CertificateVersion.certificate_id == Certificate.id)
                    & (CertificateVersion.version_no == Certificate.current_version_no),
                )
                .outerjoin(
                    BlockchainTransaction,
                    BlockchainTransaction.id
                    == CertificateVersion.blockchain_transaction_id,
                )
                .where(
                    PublicWork.id == work_id,
                    PublicWork.deleted_at.is_(None),
                )
            )
        ).one_or_none()
        if row is None:
            return None
        tag_rows = await self._session.scalars(
            select(PublicTag)
            .join(PublicWorkTag, PublicWorkTag.tag_id == PublicTag.id)
            .where(
                PublicWorkTag.public_work_id == work_id,
                PublicTag.is_active.is_(True),
            )
            .order_by(PublicTag.name, PublicTag.id)
        )
        return PublicWorkDetailRow(
            work=row[0],
            category=row[1],
            organization=row[2],
            certificate=row[3],
            transaction=row[4],
            tags=tuple(tag_rows.all()),
        )

    async def list_related_public_works(
        self,
        *,
        work_id: UUID,
        category_id: UUID,
        tag_ids: tuple[UUID, ...],
        now: datetime,
        limit: int = 4,
    ) -> tuple[PublicWorkListRow, ...]:
        tag_match = exists(
            select(PublicWorkTag.tag_id).where(
                PublicWorkTag.public_work_id == PublicWork.id,
                PublicWorkTag.tag_id.in_(tag_ids),
            )
        )
        relation_filter = (
            PublicWork.category_id == category_id
            if not tag_ids
            else or_(PublicWork.category_id == category_id, tag_match)
        )
        rows = (
            await self._session.execute(
                select(PublicWork, Category)
                .join(Category, Category.id == PublicWork.category_id)
                .where(
                    PublicWork.id != work_id,
                    PublicWork.publication_status == PublicationStatus.PUBLISHED,
                    PublicWork.visibility == PublicWorkVisibility.PUBLIC,
                    PublicWork.published_at.is_not(None),
                    PublicWork.published_at <= now,
                    PublicWork.deleted_at.is_(None),
                    Category.is_active.is_(True),
                    relation_filter,
                )
                .order_by(
                    PublicWork.featured_at.desc().nullslast(),
                    PublicWork.published_at.desc(),
                    PublicWork.id,
                )
                .limit(max(limit * 5, limit))
            )
        ).all()
        work_ids = tuple(row[0].id for row in rows)
        tags_by_work: dict[UUID, list[PublicTag]] = {
            candidate_id: [] for candidate_id in work_ids
        }
        if work_ids:
            tag_rows = await self._session.execute(
                select(PublicWorkTag.public_work_id, PublicTag)
                .join(PublicTag, PublicTag.id == PublicWorkTag.tag_id)
                .where(
                    PublicWorkTag.public_work_id.in_(work_ids),
                    PublicTag.is_active.is_(True),
                )
                .order_by(PublicTag.name, PublicTag.id)
            )
            for candidate_id, tag in tag_rows.tuples():
                tags_by_work[candidate_id].append(tag)
        requested_tags = set(tag_ids)
        ranked = sorted(
            rows,
            key=lambda row: len(
                requested_tags & {tag.id for tag in tags_by_work[row[0].id]}
            ),
            reverse=True,
        )
        selected_rows = ranked[:limit]
        thumbnails = await self._ready_thumbnails(
            tuple(work for work, _category in selected_rows)
        )
        return tuple(
            PublicWorkListRow(
                work,
                category,
                tuple(tags_by_work[work.id]),
                thumbnails[work.id].derivative_url if work.id in thumbnails else None,
                thumbnails[work.id].alt_text if work.id in thumbnails else None,
            )
            for work, category in selected_rows
        )

    async def count_sitemap_works(self, *, now: datetime) -> int:
        total = await self._session.scalar(
            select(func.count())
            .select_from(PublicWork)
            .join(Category, Category.id == PublicWork.category_id)
            .where(
                PublicWork.publication_status == PublicationStatus.PUBLISHED,
                PublicWork.visibility == PublicWorkVisibility.PUBLIC,
                PublicWork.published_at.is_not(None),
                PublicWork.published_at <= now,
                PublicWork.deleted_at.is_(None),
                Category.is_active.is_(True),
            )
        )
        return int(total or 0)

    async def list_sitemap_works(
        self,
        *,
        now: datetime,
        offset: int,
        limit: int,
    ) -> tuple[PublicWork, ...]:
        return tuple(
            (
                await self._session.scalars(
                    select(PublicWork)
                    .join(Category, Category.id == PublicWork.category_id)
                    .where(
                        PublicWork.publication_status == PublicationStatus.PUBLISHED,
                        PublicWork.visibility == PublicWorkVisibility.PUBLIC,
                        PublicWork.published_at.is_not(None),
                        PublicWork.published_at <= now,
                        PublicWork.deleted_at.is_(None),
                        Category.is_active.is_(True),
                    )
                    .order_by(PublicWork.slug, PublicWork.id)
                    .offset(offset)
                    .limit(limit)
                )
            ).all()
        )

    async def slug_exists(self, slug: str) -> bool:
        current = exists(select(PublicWork.id).where(PublicWork.slug == slug))
        historical = exists(
            select(PublicWorkSlugHistory.id).where(PublicWorkSlugHistory.slug == slug)
        )
        return bool(await self._session.scalar(select(current | historical)))

    async def resolve_slug(self, slug: str) -> tuple[PublicWork, bool] | None:
        current = cast(
            PublicWork | None,
            await self._session.scalar(
                select(PublicWork).where(
                    PublicWork.slug == slug,
                    PublicWork.deleted_at.is_(None),
                )
            ),
        )
        if current is not None:
            return current, False
        historical = await self._session.execute(
            select(PublicWork)
            .join(
                PublicWorkSlugHistory,
                PublicWorkSlugHistory.public_work_id == PublicWork.id,
            )
            .where(
                PublicWorkSlugHistory.slug == slug,
                PublicWork.deleted_at.is_(None),
            )
        )
        work = historical.scalar_one_or_none()
        return (work, True) if work is not None else None

    async def list_backfill_sources(
        self,
        *,
        after: UUID | None,
        limit: int,
    ) -> tuple[PublicWorkBackfillSource, ...]:
        certificate_id = (
            select(Certificate.id)
            .where(Certificate.dossier_id == Dossier.id)
            .order_by(Certificate.issued_at.desc(), Certificate.id.desc())
            .limit(1)
            .scalar_subquery()
        )
        cursor_filter = () if after is None else (Dossier.id > after,)
        rows = await self._session.execute(
            select(Dossier, certificate_id.label("certificate_id"))
            .where(
                Dossier.status.in_(
                    (
                        DossierStatus.CERTIFICATE_ISSUED,
                        DossierStatus.PUBLISHED,
                    )
                ),
                Dossier.deleted_at.is_(None),
                ~exists(
                    select(PublicWork.id).where(PublicWork.dossier_id == Dossier.id)
                ),
                *cursor_filter,
            )
            .order_by(Dossier.id)
            .limit(limit)
        )
        return tuple(
            PublicWorkBackfillSource(dossier=row[0], certificate_id=row[1])
            for row in rows.tuples().all()
        )
