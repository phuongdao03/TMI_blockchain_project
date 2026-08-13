import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.modules.auth.models import User  # noqa: F401
from app.modules.blockchain.models import Certificate  # noqa: F401
from app.modules.dossiers.models import Category
from app.modules.media.models import MediaAsset  # noqa: F401
from app.modules.organizations.models import Organization  # noqa: F401
from app.modules.public.models import (
    PublicationStatus,
    PublicTag,
    PublicWork,
    PublicWorkTag,
    PublicWorkVisibility,
)
from app.modules.search.errors import SearchQueryInvalidError
from app.modules.search.normalization import SearchQueryNormalizer
from app.modules.search.repository import SearchRepository
from app.modules.search.types import SearchFilters, SearchSort, TagMatchMode

NOW = datetime(2026, 8, 1, tzinfo=UTC)


def test_visibility_exact_boost_and_cursor_are_stable(tmp_path: Path) -> None:
    async def exercise() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'search.sqlite3').as_posix()}"
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        category_id = uuid4()
        async with factory() as session:
            async with session.begin():
                session.add(
                    Category(
                        id=category_id,
                        code="SEARCH",
                        name="Search",
                        slug="search",
                    )
                )
                session.add_all(
                    [
                        _work(
                            category_id,
                            slug="exact-certificate",
                            certificate="TMI-001",
                            vector="unrelated words",
                            published_at=NOW - timedelta(days=2),
                        ),
                        _work(
                            category_id,
                            slug="text-newer",
                            vector="tmi-001 public text",
                            published_at=NOW,
                        ),
                        _work(
                            category_id,
                            slug="text-older",
                            vector="tmi-001 public text",
                            published_at=NOW - timedelta(days=1),
                        ),
                        _work(
                            category_id,
                            slug="unlisted-secret",
                            vector="tmi-001 private title",
                            visibility=PublicWorkVisibility.UNLISTED,
                            published_at=NOW,
                        ),
                        _work(
                            category_id,
                            slug="suspended-secret",
                            vector="tmi-001 private title",
                            status=PublicationStatus.SUSPENDED,
                            published_at=NOW,
                        ),
                    ]
                )
            repository = SearchRepository(session)
            query = SearchQueryNormalizer().normalize("TMI-001")
            slugs: list[str] = []
            cursor: str | None = None
            while True:
                page = await repository.search(query, cursor=cursor, page_size=2)
                slugs.extend(item.slug for item in page.items)
                assert all(not hasattr(item, "owner_user_id") for item in page.items)
                cursor = page.next_cursor
                if cursor is None:
                    break
            assert slugs == ["exact-certificate", "text-newer", "text-older"]
            assert len(slugs) == len(set(slugs))

            with pytest.raises(SearchQueryInvalidError) as invalid_cursor:
                await repository.search(query, cursor="not-a-cursor")
            assert invalid_cursor.value.details == {"reason": "invalid_cursor"}
        await engine.dispose()

    asyncio.run(exercise())


def test_postgresql_statement_is_bound_visibility_scoped_and_deterministic() -> None:
    injection = "x' OR 1=1 --"
    query = SearchQueryNormalizer().normalize(injection)
    statement = SearchRepository._statement(
        query=query,
        after=None,
        limit=21,
        postgresql=True,
    )
    compiled = statement.compile(
        dialect=postgresql.dialect()  # type: ignore[no-untyped-call]
    )
    sql = str(compiled)
    assert injection not in sql
    assert injection.casefold() in compiled.params.values()
    assert "websearch_to_tsquery" in sql
    assert "publication_status" in sql
    assert "visibility" in sql
    assert "deleted_at IS NULL" in sql
    assert "categories.is_active IS true" in sql
    assert sql.index("exact_match DESC") < sql.index("relevance DESC")
    assert "public_works.published_at DESC" in sql
    assert "public_works.id ASC" in sql


def test_trigram_is_guarded_bounded_and_never_outranks_fts() -> None:
    long_query = SearchQueryNormalizer().normalize("nghe thuat")
    long_statement = SearchRepository._statement(
        query=long_query,
        after=None,
        limit=21,
        postgresql=True,
        trigram_min_length=4,
        trigram_max_boost=0.2,
    )
    long_compiled = long_statement.compile(
        dialect=postgresql.dialect()  # type: ignore[no-untyped-call]
    )
    sql = str(long_compiled)
    assert "similarity" in sql
    assert "immutable_unaccent" in sql
    assert "least" in sql
    assert long_compiled.params["trigram_max_boost"] == 0.2
    assert long_compiled.params["trigram_boost_cap"] == 0.2
    assert "WHEN" in sql and "THEN" in sql

    short_statement = SearchRepository._statement(
        query=SearchQueryNormalizer().normalize("ab"),
        after=None,
        limit=21,
        postgresql=True,
        trigram_min_length=4,
    )
    short_sql = str(
        short_statement.compile(
            dialect=postgresql.dialect()  # type: ignore[no-untyped-call]
        )
    )
    assert "similarity" not in short_sql
    assert "immutable_unaccent" not in short_sql


def test_filters_and_non_relevance_sort_are_bound_and_visibility_scoped() -> None:
    statement = SearchRepository._statement(
        query=SearchQueryNormalizer().normalize("di san"),
        filters=SearchFilters(
            category_slug="my-thuat",
            tag_slugs=("di-san", "son-mai"),
            tag_match=TagMatchMode.ALL,
            organization_code="tmi-group",
            has_blockchain_proof=True,
        ),
        sort=SearchSort.MOST_VIEWED,
        after=None,
        limit=21,
        postgresql=True,
    )
    compiled = statement.compile(
        dialect=postgresql.dialect()  # type: ignore[no-untyped-call]
    )
    sql = str(compiled)
    assert "public_works.visibility" in sql
    assert "public_works.publication_status" in sql
    assert "categories.slug" in sql
    assert sql.count("EXISTS") == 2
    assert "organizations.code" in sql
    assert "public_works.certificate_id IS NOT NULL" in sql
    assert sql.index("public_works.view_count DESC") < sql.index(
        "public_works.published_at DESC"
    )
    assert {"my-thuat", "di-san", "son-mai", "tmi-group"}.issubset(
        set(compiled.params.values())
    )


def test_facets_count_only_the_filtered_public_set_with_all_tag_semantics(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'facets.sqlite3').as_posix()}"
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        art_id, craft_id = uuid4(), uuid4()
        heritage_id, lacquer_id = uuid4(), uuid4()
        public_both = _work(
            art_id,
            slug="public-both",
            vector="son mai heritage",
            published_at=NOW,
        )
        public_one = _work(
            craft_id,
            slug="public-one",
            vector="son mai craft",
            published_at=NOW,
        )
        private_both = _work(
            art_id,
            slug="private-both",
            vector="son mai secret",
            visibility=PublicWorkVisibility.PRIVATE,
            published_at=NOW,
        )
        async with factory() as session:
            async with session.begin():
                session.add_all(
                    [
                        Category(id=art_id, code="ART", name="Mỹ thuật", slug="art"),
                        Category(
                            id=craft_id,
                            code="CRAFT",
                            name="Thủ công",
                            slug="craft",
                        ),
                        PublicTag(id=heritage_id, name="Di sản", slug="heritage"),
                        PublicTag(id=lacquer_id, name="Sơn mài", slug="lacquer"),
                        public_both,
                        public_one,
                        private_both,
                    ]
                )
                await session.flush()
                session.add_all(
                    [
                        PublicWorkTag(
                            public_work_id=public_both.id,
                            tag_id=heritage_id,
                        ),
                        PublicWorkTag(
                            public_work_id=public_both.id,
                            tag_id=lacquer_id,
                        ),
                        PublicWorkTag(
                            public_work_id=public_one.id,
                            tag_id=heritage_id,
                        ),
                        PublicWorkTag(
                            public_work_id=private_both.id,
                            tag_id=heritage_id,
                        ),
                        PublicWorkTag(
                            public_work_id=private_both.id,
                            tag_id=lacquer_id,
                        ),
                    ]
                )

            repository = SearchRepository(session)
            statement_count = 0

            def count_statement(*_: object) -> None:
                nonlocal statement_count
                statement_count += 1

            event.listen(
                engine.sync_engine,
                "before_cursor_execute",
                count_statement,
            )
            try:
                facets = await repository.facets(
                    SearchQueryNormalizer().normalize("son mai"),
                    filters=SearchFilters(
                        tag_slugs=("heritage", "lacquer"),
                        tag_match=TagMatchMode.ALL,
                    ),
                )
            finally:
                event.remove(
                    engine.sync_engine,
                    "before_cursor_execute",
                    count_statement,
                )
        assert statement_count == 1
        assert [(item.slug, item.count) for item in facets.categories] == [("art", 1)]
        assert [(item.slug, item.count) for item in facets.tags] == [
            ("heritage", 1),
            ("lacquer", 1),
        ]
        await engine.dispose()

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "options",
    (
        {"trigram_min_length": 2},
        {"trigram_threshold": 0.01},
        {"trigram_max_boost": 0.9},
        {"statement_timeout_ms": 10},
    ),
)
def test_search_resource_guards_reject_unsafe_configuration(
    options: dict[str, float | int],
) -> None:
    with pytest.raises(ValueError):
        SearchRepository(None, **options)  # type: ignore[arg-type]


def _work(
    category_id: UUID,
    *,
    slug: str,
    vector: str,
    published_at: datetime,
    certificate: str = "",
    status: PublicationStatus = PublicationStatus.PUBLISHED,
    visibility: PublicWorkVisibility = PublicWorkVisibility.PUBLIC,
) -> PublicWork:
    return PublicWork(
        dossier_id=uuid4(),
        owner_user_id=uuid4(),
        slug=slug,
        title=slug,
        short_description="Approved public search result",
        category_id=category_id,
        publication_status=status,
        visibility=visibility,
        published_at=published_at,
        search_certificate_text=certificate,
        search_vector=vector,
    )
