from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Numeric,
    and_,
    bindparam,
    case,
    cast,
    exists,
    func,
    literal,
    or_,
    select,
    union_all,
)
from sqlalchemy.engine.row import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.sql import Select
from sqlalchemy.sql.elements import BindParameter, ColumnElement

from app.modules.blockchain.models import Certificate
from app.modules.dossiers.models import Category
from app.modules.organizations.models import Organization, OrganizationStatus
from app.modules.public.models import (
    PublicationStatus,
    PublicTag,
    PublicWork,
    PublicWorkTag,
    PublicWorkVisibility,
)
from app.modules.search.cursor import SearchCursorCodec
from app.modules.search.errors import SearchQueryInvalidError
from app.modules.search.normalization import NormalizedSearchQuery
from app.modules.search.types import (
    AutocompleteKind,
    AutocompleteSuggestion,
    SearchCursor,
    SearchFacets,
    SearchFacetValue,
    SearchFilters,
    SearchPage,
    SearchSort,
    SearchWorkProjection,
    TagMatchMode,
)


class SearchRepository:
    def __init__(
        self,
        session: AsyncSession,
        *,
        statement_timeout_ms: int = 400,
        trigram_min_length: int = 4,
        trigram_threshold: float = 0.3,
        trigram_max_boost: float = 0.25,
        cursor_codec: SearchCursorCodec | None = None,
    ) -> None:
        if not 50 <= statement_timeout_ms <= 5_000:
            raise ValueError("statement_timeout_ms must be between 50 and 5000")
        self._session = session
        self._statement_timeout_ms = statement_timeout_ms
        if not 3 <= trigram_min_length <= 20:
            raise ValueError("trigram_min_length must be between 3 and 20")
        if not 0.1 <= trigram_threshold <= 0.9:
            raise ValueError("trigram_threshold must be between 0.1 and 0.9")
        if not 0.0 <= trigram_max_boost <= 0.5:
            raise ValueError("trigram_max_boost must be between 0 and 0.5")
        self._trigram_min_length = trigram_min_length
        self._trigram_threshold = trigram_threshold
        self._trigram_max_boost = trigram_max_boost
        self._cursor_codec = cursor_codec or SearchCursorCodec()

    async def search(
        self,
        query: NormalizedSearchQuery,
        *,
        filters: SearchFilters | None = None,
        sort: SearchSort = SearchSort.RELEVANCE,
        cursor: str | None = None,
        page_size: int = 20,
    ) -> SearchPage:
        if query.is_empty and sort is SearchSort.RELEVANCE:
            raise SearchQueryInvalidError("relevance_requires_query")
        if not 1 <= page_size <= 100:
            raise SearchQueryInvalidError("invalid_page_size", limit=100)
        after = (
            self._cursor_codec.decode(cursor, expected_sort=sort) if cursor else None
        )
        dialect = self._session.bind.dialect.name if self._session.bind else ""
        if dialect == "postgresql":
            await self._session.execute(
                select(
                    func.set_config(
                        "statement_timeout",
                        str(self._statement_timeout_ms),
                        True,
                    )
                )
            )
            if len(query.unaccented) >= self._trigram_min_length:
                await self._session.execute(
                    select(
                        func.set_config(
                            "pg_trgm.similarity_threshold",
                            str(self._trigram_threshold),
                            True,
                        )
                    )
                )
        statement = self._statement(
            query=query,
            filters=filters or SearchFilters(),
            sort=sort,
            after=after,
            limit=page_size + 1,
            postgresql=dialect == "postgresql",
            trigram_min_length=self._trigram_min_length,
            trigram_max_boost=self._trigram_max_boost,
        )
        rows = (await self._session.execute(statement)).all()
        visible_rows = rows[:page_size]
        items = tuple(
            SearchWorkProjection(
                id=row.id,
                slug=row.slug,
                title=row.title,
                short_description=row.short_description,
                author_display_name=row.author_display_name,
                category_name=row.category_name,
                category_slug=row.category_slug,
                certificate_number=row.certificate_number,
                certificate_status=row.certificate_status,
                published_at=self._as_utc(row.published_at),
            )
            for row in visible_rows
        )
        next_cursor = None
        if len(rows) > page_size and visible_rows:
            last = visible_rows[-1]
            next_cursor = self._cursor_codec.encode(
                SearchCursor(
                    exact_match=int(last.exact_match),
                    relevance=Decimal(str(last.relevance)),
                    published_at=self._as_utc(last.published_at),
                    work_id=last.id,
                    sort=sort,
                    view_count=last.view_count,
                )
            )
        return SearchPage(items=items, next_cursor=next_cursor)

    async def facets(
        self,
        query: NormalizedSearchQuery,
        *,
        filters: SearchFilters | None = None,
    ) -> SearchFacets:
        dialect = self._session.bind.dialect.name if self._session.bind else ""
        if dialect == "postgresql":
            await self._session.execute(
                select(
                    func.set_config(
                        "statement_timeout",
                        str(self._statement_timeout_ms),
                        True,
                    )
                )
            )
            if len(query.unaccented) >= self._trigram_min_length:
                await self._session.execute(
                    select(
                        func.set_config(
                            "pg_trgm.similarity_threshold",
                            str(self._trigram_threshold),
                            True,
                        )
                    )
                )
        _, _, match = self._search_expressions(
            query=query,
            postgresql=dialect == "postgresql",
            trigram_min_length=self._trigram_min_length,
            trigram_max_boost=self._trigram_max_boost,
        )
        clauses = self._filter_clauses(
            filters=filters or SearchFilters(),
            match=match,
        )
        matching_works = (
            select(PublicWork.id.label("work_id"))
            .join(Category, Category.id == PublicWork.category_id)
            .outerjoin(Certificate, Certificate.id == PublicWork.certificate_id)
            .where(*clauses)
            .subquery("matching_search_works")
        )
        category_counts = (
            select(
                literal("category").label("kind"),
                Category.slug.label("slug"),
                Category.name.label("label"),
                func.count(matching_works.c.work_id).label("count"),
            )
            .select_from(matching_works)
            .join(PublicWork, PublicWork.id == matching_works.c.work_id)
            .join(Category, Category.id == PublicWork.category_id)
            .group_by(Category.slug, Category.name)
        )
        tag_counts = (
            select(
                literal("tag").label("kind"),
                PublicTag.slug.label("slug"),
                PublicTag.name.label("label"),
                func.count(matching_works.c.work_id).label("count"),
            )
            .select_from(matching_works)
            .join(
                PublicWorkTag,
                PublicWorkTag.public_work_id == matching_works.c.work_id,
            )
            .join(PublicTag, PublicTag.id == PublicWorkTag.tag_id)
            .where(PublicTag.is_active.is_(True))
            .group_by(PublicTag.slug, PublicTag.name)
        )
        rows: Sequence[RowMapping] = (
            (await self._session.execute(union_all(category_counts, tag_counts)))
            .mappings()
            .all()
        )
        categories = sorted(
            (
                SearchFacetValue(
                    slug=row["slug"],
                    label=row["label"],
                    count=int(row["count"]),
                )
                for row in rows
                if row["kind"] == "category" and row["slug"] is not None
            ),
            key=lambda item: (-item.count, item.label.casefold(), item.slug),
        )
        tags = sorted(
            (
                SearchFacetValue(
                    slug=row["slug"],
                    label=row["label"],
                    count=int(row["count"]),
                )
                for row in rows
                if row["kind"] == "tag" and row["slug"] is not None
            ),
            key=lambda item: (-item.count, item.label.casefold(), item.slug),
        )
        return SearchFacets(categories=tuple(categories), tags=tuple(tags))

    async def autocomplete(
        self,
        query: NormalizedSearchQuery,
        *,
        limit: int = 8,
    ) -> tuple[AutocompleteSuggestion, ...]:
        if query.is_empty:
            raise SearchQueryInvalidError("too_short", limit=2)
        if not 1 <= limit <= 12:
            raise SearchQueryInvalidError("invalid_autocomplete_limit", limit=12)
        dialect = self._session.bind.dialect.name if self._session.bind else ""
        postgresql = dialect == "postgresql"
        if postgresql:
            await self._session.execute(
                select(
                    func.set_config(
                        "statement_timeout",
                        str(self._statement_timeout_ms),
                        True,
                    )
                )
            )
        prefix: BindParameter[str] = bindparam(
            "autocomplete_prefix",
            f"{query.unaccented if postgresql else query.normalized}%",
        )

        def matches(column: Any) -> ColumnElement[bool]:
            normalized = func.lower(column)
            if postgresql:
                normalized = func.immutable_unaccent(normalized)
            return normalized.like(prefix)

        now = datetime.now(UTC)
        visible = (
            PublicWork.deleted_at.is_(None),
            PublicWork.publication_status == PublicationStatus.PUBLISHED,
            PublicWork.visibility == PublicWorkVisibility.PUBLIC,
            PublicWork.published_at.is_not(None),
            PublicWork.published_at <= now,
        )
        work_category = aliased(Category)
        tagged_category = aliased(Category)
        title_suggestions = (
            select(
                literal(AutocompleteKind.WORK.value).label("kind"),
                PublicWork.title.label("label"),
                PublicWork.slug.label("slug"),
                literal(0).label("priority"),
            )
            .join(work_category, work_category.id == PublicWork.category_id)
            .where(
                *visible,
                work_category.is_active.is_(True),
                matches(PublicWork.title),
            )
        )
        category_has_public_work = exists(
            select(literal(1))
            .select_from(PublicWork)
            .where(*visible, PublicWork.category_id == Category.id)
        )
        category_suggestions = select(
            literal(AutocompleteKind.CATEGORY.value).label("kind"),
            Category.name.label("label"),
            Category.slug.label("slug"),
            literal(1).label("priority"),
        ).where(
            Category.is_active.is_(True),
            Category.slug.is_not(None),
            matches(Category.name),
            category_has_public_work,
        )
        tag_has_public_work = exists(
            select(literal(1))
            .select_from(PublicWorkTag)
            .join(PublicWork, PublicWork.id == PublicWorkTag.public_work_id)
            .join(tagged_category, tagged_category.id == PublicWork.category_id)
            .where(
                *visible,
                PublicWorkTag.tag_id == PublicTag.id,
                tagged_category.is_active.is_(True),
            )
        )
        tag_suggestions = select(
            literal(AutocompleteKind.TAG.value).label("kind"),
            PublicTag.name.label("label"),
            PublicTag.slug.label("slug"),
            literal(2).label("priority"),
        ).where(
            PublicTag.is_active.is_(True),
            matches(PublicTag.name),
            tag_has_public_work,
        )
        candidates = union_all(
            title_suggestions,
            category_suggestions,
            tag_suggestions,
        ).subquery("autocomplete_candidates")
        statement = (
            select(candidates.c.kind, candidates.c.label, candidates.c.slug)
            .order_by(
                candidates.c.priority.asc(),
                candidates.c.label.asc(),
                candidates.c.slug.asc(),
            )
            .limit(limit)
        )
        rows: Sequence[RowMapping] = (
            (await self._session.execute(statement)).mappings().all()
        )
        return tuple(
            AutocompleteSuggestion(
                kind=AutocompleteKind(row["kind"]),
                label=row["label"],
                slug=row["slug"],
            )
            for row in rows
        )

    @staticmethod
    def _statement(
        *,
        query: NormalizedSearchQuery,
        filters: SearchFilters | None = None,
        sort: SearchSort = SearchSort.RELEVANCE,
        after: SearchCursor | None,
        limit: int,
        postgresql: bool,
        trigram_min_length: int = 4,
        trigram_max_boost: float = 0.25,
    ) -> Select[tuple[object, ...]]:
        certificate_exact, relevance, match = SearchRepository._search_expressions(
            query=query,
            postgresql=postgresql,
            trigram_min_length=trigram_min_length,
            trigram_max_boost=trigram_max_boost,
        )
        where_clauses = SearchRepository._filter_clauses(
            filters=filters or SearchFilters(),
            match=match,
        )
        if after is not None:
            where_clauses.append(
                SearchRepository._cursor_predicate(
                    sort=sort,
                    after=after,
                    certificate_exact=certificate_exact,
                    relevance=relevance,
                )
            )
        order_by = SearchRepository._order_by(
            sort=sort,
            certificate_exact=certificate_exact,
            relevance=relevance,
        )
        return (
            select(
                PublicWork.id.label("id"),
                PublicWork.slug.label("slug"),
                PublicWork.title.label("title"),
                PublicWork.short_description.label("short_description"),
                PublicWork.author_display_name.label("author_display_name"),
                Category.name.label("category_name"),
                Category.slug.label("category_slug"),
                func.nullif(PublicWork.search_certificate_text, "").label(
                    "certificate_number"
                ),
                Certificate.status.label("certificate_status"),
                PublicWork.published_at.label("published_at"),
                PublicWork.view_count.label("view_count"),
                certificate_exact,
                relevance,
            )
            .join(Category, Category.id == PublicWork.category_id)
            .outerjoin(Certificate, Certificate.id == PublicWork.certificate_id)
            .where(*where_clauses)
            .order_by(*order_by)
            .limit(limit)
        )

    @staticmethod
    def _filter_clauses(
        *,
        filters: SearchFilters,
        match: ColumnElement[bool],
    ) -> list[ColumnElement[bool]]:
        where_clauses: list[ColumnElement[bool]] = [
            PublicWork.publication_status == PublicationStatus.PUBLISHED,
            PublicWork.visibility == PublicWorkVisibility.PUBLIC,
            PublicWork.deleted_at.is_(None),
            Category.is_active.is_(True),
            Category.slug.is_not(None),
            PublicWork.published_at.is_not(None),
            match,
        ]
        if filters.category_slug is not None:
            where_clauses.append(Category.slug == filters.category_slug)
        if filters.organization_code is not None:
            where_clauses.append(
                PublicWork.organization_id.in_(
                    select(Organization.id).where(
                        func.lower(Organization.code) == filters.organization_code,
                        Organization.status == OrganizationStatus.ACTIVE,
                        Organization.deleted_at.is_(None),
                    )
                )
            )
        if filters.published_from is not None:
            where_clauses.append(PublicWork.published_at >= filters.published_from)
        if filters.published_to is not None:
            where_clauses.append(PublicWork.published_at <= filters.published_to)
        if filters.has_blockchain_proof is True:
            where_clauses.append(PublicWork.certificate_id.is_not(None))
        elif filters.has_blockchain_proof is False:
            where_clauses.append(PublicWork.certificate_id.is_(None))
        if filters.certificate_status is not None:
            where_clauses.append(Certificate.status == filters.certificate_status)
        tag_predicates = [
            exists(
                select(1)
                .select_from(PublicWorkTag)
                .join(PublicTag, PublicTag.id == PublicWorkTag.tag_id)
                .where(
                    PublicWorkTag.public_work_id == PublicWork.id,
                    PublicTag.slug == tag_slug,
                    PublicTag.is_active.is_(True),
                )
            )
            for tag_slug in filters.tag_slugs
        ]
        if tag_predicates:
            where_clauses.append(
                and_(*tag_predicates)
                if filters.tag_match is TagMatchMode.ALL
                else or_(*tag_predicates)
            )
        return where_clauses

    @staticmethod
    def _search_expressions(
        *,
        query: NormalizedSearchQuery,
        postgresql: bool,
        trigram_min_length: int,
        trigram_max_boost: float,
    ) -> tuple[ColumnElement[int], ColumnElement[Decimal], ColumnElement[bool]]:
        query_parameter: BindParameter[str] = bindparam(
            "search_query", value=query.unaccented
        )
        certificate_exact = case(
            (
                func.lower(PublicWork.search_certificate_text)
                == bindparam("exact_query", value=query.raw.casefold()),
                1,
            ),
            else_=0,
        ).label("exact_match")
        if query.is_empty:
            return (
                certificate_exact,
                cast(literal(0), Numeric(12, 6)).label("relevance"),
                literal(True),
            )
        if not postgresql:
            text_match = func.lower(PublicWork.search_vector).contains(query_parameter)
            return (
                certificate_exact,
                cast(case((text_match, 1), else_=0), Numeric).label("relevance"),
                or_(text_match, certificate_exact == 1),
            )
        tsquery = func.websearch_to_tsquery("simple", query_parameter)
        fts_match = PublicWork.search_vector.op("@@")(tsquery)
        fts_rank = func.ts_rank_cd(PublicWork.search_vector, tsquery)
        fuzzy_match: ColumnElement[bool] = literal(False)
        fuzzy_score: ColumnElement[float] = literal(0.0)
        if len(query.unaccented) >= trigram_min_length:
            title = func.public.immutable_unaccent(func.lower(PublicWork.title))
            author = func.public.immutable_unaccent(
                func.lower(func.coalesce(PublicWork.author_display_name, ""))
            )
            fuzzy_match = or_(
                title.op("%")(query_parameter),
                author.op("%")(query_parameter),
            )
            fuzzy_score = func.least(
                func.greatest(
                    func.similarity(title, query_parameter),
                    func.similarity(author, query_parameter),
                )
                * bindparam("trigram_max_boost", value=trigram_max_boost),
                bindparam("trigram_boost_cap", value=trigram_max_boost),
            )
        relevance = cast(
            func.round(
                cast(
                    case((fts_match, 1.0), else_=0.0) + fts_rank + fuzzy_score,
                    Numeric,
                ),
                6,
            ),
            Numeric(12, 6),
        ).label("relevance")
        return (
            certificate_exact,
            relevance,
            or_(fts_match, fuzzy_match, certificate_exact == 1),
        )

    @staticmethod
    def _order_by(
        *,
        sort: SearchSort,
        certificate_exact: ColumnElement[int],
        relevance: ColumnElement[Decimal],
    ) -> tuple[ColumnElement[Any], ...]:
        if sort is SearchSort.NEWEST:
            return (PublicWork.published_at.desc(), PublicWork.id.asc())
        if sort is SearchSort.OLDEST:
            return (PublicWork.published_at.asc(), PublicWork.id.asc())
        if sort is SearchSort.MOST_VIEWED:
            return (
                PublicWork.view_count.desc(),
                PublicWork.published_at.desc(),
                PublicWork.id.asc(),
            )
        return (
            certificate_exact.desc(),
            relevance.desc(),
            PublicWork.published_at.desc(),
            PublicWork.id.asc(),
        )

    @staticmethod
    def _cursor_predicate(
        *,
        sort: SearchSort,
        after: SearchCursor,
        certificate_exact: ColumnElement[int],
        relevance: ColumnElement[Decimal],
    ) -> ColumnElement[bool]:
        if sort is SearchSort.NEWEST:
            return or_(
                PublicWork.published_at < after.published_at,
                and_(
                    PublicWork.published_at == after.published_at,
                    PublicWork.id > after.work_id,
                ),
            )
        if sort is SearchSort.OLDEST:
            return or_(
                PublicWork.published_at > after.published_at,
                and_(
                    PublicWork.published_at == after.published_at,
                    PublicWork.id > after.work_id,
                ),
            )
        if sort is SearchSort.MOST_VIEWED:
            return or_(
                PublicWork.view_count < after.view_count,
                and_(
                    PublicWork.view_count == after.view_count,
                    PublicWork.published_at < after.published_at,
                ),
                and_(
                    PublicWork.view_count == after.view_count,
                    PublicWork.published_at == after.published_at,
                    PublicWork.id > after.work_id,
                ),
            )
        return or_(
            certificate_exact < after.exact_match,
            and_(
                certificate_exact == after.exact_match,
                relevance < after.relevance,
            ),
            and_(
                certificate_exact == after.exact_match,
                relevance == after.relevance,
                PublicWork.published_at < after.published_at,
            ),
            and_(
                certificate_exact == after.exact_match,
                relevance == after.relevance,
                PublicWork.published_at == after.published_at,
                PublicWork.id > after.work_id,
            ),
        )

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        return (
            value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
        )
