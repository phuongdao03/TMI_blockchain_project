import asyncio
from typing import cast
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.modules.ranking.public_repository import PublicRankingRepository
from app.modules.ranking.public_service import PublicRankingService


class FakeTransaction:
    async def __aenter__(self) -> None:
        return None

    async def __aexit__(self, *args: object) -> None:
        return None


class FakeSession:
    def begin(self) -> FakeTransaction:
        return FakeTransaction()


class MissingSnapshotRepository:
    async def get_snapshot(self, *, campaign_slug: str, version: int | None) -> None:
        del campaign_slug, version
        return None

    async def list_items(self, **kwargs: object) -> tuple[tuple[object, ...], int]:
        raise AssertionError(f"list_items must not be called: {kwargs}")


def test_public_ranking_service_hides_missing_and_unpublished_snapshots() -> None:
    service = PublicRankingService(
        cast(AsyncSession, FakeSession()),
        cast(PublicRankingRepository, MissingSnapshotRepository()),
    )

    with pytest.raises(DomainError) as captured:
        asyncio.run(
            service.get_ranking(
                campaign_slug="draft-campaign",
                version=None,
                category_id=UUID("50000000-0000-0000-0000-000000000001"),
                page=1,
                page_size=20,
            )
        )

    assert captured.value.code == "RANKING_PUBLIC_NOT_FOUND"
    assert captured.value.status_code == 404
