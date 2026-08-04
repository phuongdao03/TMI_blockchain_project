from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.modules.ranking.public_repository import PublicRankingRepository
from app.modules.ranking.public_types import PublicRankingPage
from app.modules.ranking.ranking_cache import (
    RankingCache,
    deserialize_ranking_page,
    public_ranking_cache_key,
    serialize_ranking_page,
)


class PublicRankingService:
    def __init__(
        self,
        session: AsyncSession,
        repository: PublicRankingRepository,
        *,
        cache: RankingCache | None = None,
    ) -> None:
        self._session = session
        self._repository = repository
        self._cache = cache

    async def get_ranking(
        self,
        *,
        campaign_slug: str,
        version: int | None,
        category_id: UUID | None,
        page: int,
        page_size: int,
    ) -> PublicRankingPage:
        if page < 1 or page_size < 1:
            raise ValueError("page and page_size must be positive")
        cache_key = public_ranking_cache_key(
            campaign_slug=campaign_slug,
            version=version,
            category_id=category_id,
            page=page,
            page_size=page_size,
        )
        if self._cache is not None:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                page_view = deserialize_ranking_page(cached)
                if page_view is not None:
                    return page_view
        async with self._session.begin():
            snapshot = await self._repository.get_snapshot(
                campaign_slug=campaign_slug,
                version=version,
            )
            if snapshot is None:
                raise DomainError(
                    code="RANKING_PUBLIC_NOT_FOUND",
                    message="The published ranking was not found.",
                    status_code=404,
                )
            items, total = await self._repository.list_items(
                snapshot_id=snapshot.id,
                category_id=category_id,
                offset=(page - 1) * page_size,
                limit=page_size,
            )
        result = PublicRankingPage(
            snapshot=snapshot,
            items=items,
            page=page,
            page_size=page_size,
            total=total,
        )
        if self._cache is not None:
            await self._cache.set(cache_key, serialize_ranking_page(result))
        return result
