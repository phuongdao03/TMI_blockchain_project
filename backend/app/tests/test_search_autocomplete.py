import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from uuid import UUID, uuid4

from redis.asyncio import Redis
from sqlalchemy import event
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
from app.modules.search.autocomplete_cache import RedisAutocompleteCache
from app.modules.search.normalization import SearchQueryNormalizer
from app.modules.search.repository import SearchRepository
from app.modules.search.types import (
    AutocompleteKind,
    AutocompleteSuggestion,
)


class MemoryRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.read_keys: list[str] = []

    async def get(self, key: str) -> str | None:
        self.read_keys.append(key)
        return self.values.get(key)

    async def eval(
        self,
        script: str,
        key_count: int,
        generation_key: str,
        cache_key: str,
        generation: str,
        payload: str,
        ttl: str,
    ) -> int:
        del script, key_count, ttl
        current = self.values.get(generation_key, "0")
        if current != generation:
            return 0
        self.values[cache_key] = payload
        return 1


def test_autocomplete_cache_is_hashed_and_catalog_generation_scoped() -> None:
    async def exercise() -> None:
        redis = MemoryRedis()
        cache = RedisAutocompleteCache(cast(Redis, redis), ttl_seconds=60)
        result = (
            AutocompleteSuggestion(
                kind=AutocompleteKind.WORK,
                label="Sơn mài công khai",
                slug="son-mai-cong-khai",
            ),
        )
        await cache.set("son mai", result)
        assert await cache.get("son mai") == result
        assert all("son mai" not in key for key in redis.read_keys)

        redis.values["public:catalog:v1:generation"] = "1"
        assert await cache.get("son mai") is None

    asyncio.run(exercise())


def test_autocomplete_repository_never_suggests_non_public_works(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'autocomplete.sqlite3').as_posix()}"
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        category_id, tag_id = uuid4(), uuid4()
        async with factory() as session:
            async with session.begin():
                category = Category(
                    id=category_id,
                    code="SON_MAI",
                    name="Sơn mài",
                    slug="son-mai",
                )
                tag = PublicTag(
                    id=tag_id,
                    name="Sơn mài Việt",
                    slug="son-mai-viet",
                )
                public = _work(category_id, "son-mai-cong-khai")
                private = _work(
                    category_id,
                    "son-mai-bi-mat",
                    visibility=PublicWorkVisibility.PRIVATE,
                )
                session.add_all([category, tag, public, private])
                await session.flush()
                session.add(PublicWorkTag(public_work_id=public.id, tag_id=tag_id))

            statement_count = 0

            def count_statement(*_: object) -> None:
                nonlocal statement_count
                statement_count += 1

            event.listen(engine.sync_engine, "before_cursor_execute", count_statement)
            try:
                suggestions = await SearchRepository(session).autocomplete(
                    SearchQueryNormalizer().normalize("Sơn"),
                    limit=8,
                )
            finally:
                event.remove(
                    engine.sync_engine,
                    "before_cursor_execute",
                    count_statement,
                )

        values = {(item.kind, item.slug) for item in suggestions}
        assert statement_count == 1
        assert (AutocompleteKind.WORK, "son-mai-cong-khai") in values
        assert (AutocompleteKind.WORK, "son-mai-bi-mat") not in values
        assert (AutocompleteKind.CATEGORY, "son-mai") in values
        assert (AutocompleteKind.TAG, "son-mai-viet") in values
        await engine.dispose()

    asyncio.run(exercise())


def _work(
    category_id: UUID,
    slug: str,
    *,
    visibility: PublicWorkVisibility = PublicWorkVisibility.PUBLIC,
) -> PublicWork:
    return PublicWork(
        dossier_id=uuid4(),
        owner_user_id=uuid4(),
        slug=slug,
        title=f"Sơn mài {slug.rsplit('-', maxsplit=1)[-1]}",
        short_description="Public autocomplete fixture",
        category_id=category_id,
        publication_status=PublicationStatus.PUBLISHED,
        visibility=visibility,
        published_at=datetime.now(UTC),
    )
