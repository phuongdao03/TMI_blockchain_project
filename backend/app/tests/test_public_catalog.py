import asyncio
from typing import cast

import pytest
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ClauseElement

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
        "publicEvidences": [
            {
                "title": "Tác phẩm công khai",
                "type": "ARTWORK_IMAGE",
                "sha256": "ab" * 32,
                "accessScope": "PUBLIC",
                "privateOriginalUrl": "https://private.example/original.png",
            },
            {
                "title": "Legacy document",
                "type": "LEGACY",
                "sha256": "cd" * 32,
                "isPublic": True,
            },
            {
                "title": "Internal document",
                "type": "IDENTITY",
                "sha256": "ef" * 32,
                "accessScope": "INTERNAL",
            },
        ],
        "ownerUserId": "private-user",
        "privateEvidence": {"mediaAssetId": "private-media"},
        "rendition": {"pdfSha256": "private-file-hash"},
    }

    result = PublicCatalogService._public_metadata(metadata)

    assert result == {
        "schemaVersion": 1,
        "asset": {"title": "TMI"},
        "publicEvidences": [
            {
                "title": "Tác phẩm công khai",
                "type": "ARTWORK_IMAGE",
                "sha256": "ab" * 32,
                "accessScope": "PUBLIC",
            }
        ],
    }
    serialized = str(result)
    assert "private" not in serialized
    assert "Legacy" not in serialized
    assert "Internal" not in serialized


def test_public_serializer_only_returns_safe_explicit_public_fields() -> None:
    result = PublicCatalogService._public_metadata(
        {
            "schemaVersion": 2,
            "publicFields": [
                {
                    "key": "story",
                    "label": "Public story",
                    "value": "Approved narrative",
                },
                {
                    "key": "email",
                    "label": "Private email",
                    "value": {"email": "owner-private@example.test"},
                },
            ],
        }
    )

    assert result == {
        "schemaVersion": 2,
        "publicFields": [
            {
                "key": "story",
                "label": "Public story",
                "value": "Approved narrative",
            }
        ],
    }
    assert "owner-private@example.test" not in str(result)


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


def test_public_version_history_excludes_unconfirmed_workflow_versions() -> None:
    class Result:
        @staticmethod
        def all() -> list[object]:
            return []

    class Session:
        statement: object | None = None

        async def execute(self, statement: object) -> Result:
            self.statement = statement
            return Result()

    async def scenario() -> None:
        session = Session()
        repository = PublicRepository(cast(AsyncSession, session))

        await repository.list_certificate_versions("TMI-2026-0001")

        assert session.statement is not None
        statement = cast(ClauseElement, session.statement)
        sql = str(statement.compile(compile_kwargs={"literal_binds": True})).lower()
        expected_statuses = (
            "certificate_versions.status in ('active', 'superseded', 'revoked')"
        )
        assert expected_statuses in sql
        assert "blockchain_transactions.status = 'confirmed'" in sql

    asyncio.run(scenario())
