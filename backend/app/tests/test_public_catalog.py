import asyncio
from typing import cast

import pytest
from redis.asyncio import Redis

from app.modules.auth.errors import RateLimitExceededError
from app.modules.public.rate_limit import RedisPublicRateLimiter
from app.modules.public.repository import PublicRepository
from app.modules.public.service import PublicCatalogService


class FakeRedis:
    def __init__(self, results: list[list[int]]) -> None:
        self.results = results
        self.keys: list[str] = []

    async def eval(
        self,
        script: str,
        key_count: int,
        key: str,
        window: int,
    ) -> list[int]:
        del script, key_count, window
        self.keys.append(key)
        return self.results.pop(0)


def test_public_serializer_allowlists_metadata_and_removes_rendition() -> None:
    metadata = {
        "schemaVersion": 1,
        "asset": {"title": "TMI"},
        "publicEvidences": [{"sha256": "ab" * 32}],
        "ownerUserId": "private-user",
        "privateEvidence": {"mediaAssetId": "private-media"},
        "rendition": {"pdfSha256": "private-file-hash"},
    }

    result = PublicCatalogService._public_metadata(metadata)

    assert result == {
        "schemaVersion": 1,
        "asset": {"title": "TMI"},
        "publicEvidences": [{"sha256": "ab" * 32}],
    }
    assert "private" not in str(result)


def test_public_rate_limit_hashes_ip_and_blocks_above_limit() -> None:
    async def scenario() -> None:
        redis = FakeRedis([[1, 60], [3, 42]])
        limiter = RedisPublicRateLimiter(
            cast(Redis, redis),
            attempts=2,
            window_seconds=60,
        )
        await limiter.check("203.0.113.7")
        with pytest.raises(RateLimitExceededError):
            await limiter.check("203.0.113.7")
        assert all("203.0.113.7" not in key for key in redis.keys)

    asyncio.run(scenario())


def test_rate_limit_key_is_namespaced_by_scope_and_hashes_identity() -> None:
    async def scenario() -> None:
        redis = FakeRedis([[1, 60]])
        limiter = RedisPublicRateLimiter(
            cast(Redis, redis),
            attempts=2,
            window_seconds=60,
            scope="media:upload-signature:user",
        )
        await limiter.check("user-123")

        assert redis.keys[0].startswith("media:upload-signature:user:")
        assert "user-123" not in redis.keys[0]

    asyncio.run(scenario())


def test_public_search_builds_published_query_and_category_filters() -> None:
    statement = PublicRepository._public_statement().where(  # noqa: SLF001
        *PublicRepository._filters(  # noqa: SLF001
            query="TMI",
            category="BRAND",
        )
    )
    sql = str(statement.compile(compile_kwargs={"literal_binds": True})).lower()

    assert "dossiers.status = 'published'" in sql
    assert "dossiers.visibility = 'public'" in sql
    assert "lower(dossiers.title)" in sql
    assert "lower(certificates.certificate_number)" in sql
    assert "lower(categories.code) = 'brand'" in sql
