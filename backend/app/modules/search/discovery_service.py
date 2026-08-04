import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID

from app.core.errors import DomainError
from app.modules.audit.service import AuditService
from app.modules.auth.session_service import AuthPrincipal
from app.modules.search.discovery_models import SearchEvent, SearchSnapshotPeriod
from app.modules.search.discovery_repository import SearchDiscoveryRepository
from app.modules.search.discovery_types import (
    RelatedWork,
    SearchAnalyticsSummary,
    TrendingSearch,
)
from app.modules.search.privacy import is_safe_aggregate_query

ADMIN_ROLES = frozenset({"CONTENT_ADMIN", "SUPER_ADMIN"})


class DiscoveryCachePort(Protocol):
    async def get(self, key: str) -> str | None: ...
    async def set(self, key: str, value: str) -> None: ...
    async def reserve(self, key: str, *, seconds: int = 3) -> bool: ...
    async def release(self, key: str) -> None: ...


class SearchDiscoveryService:
    def __init__(
        self,
        repository: SearchDiscoveryRepository,
        *,
        cache: DiscoveryCachePort | None = None,
        audit: AuditService | None = None,
        minimum_trending_count: int = 5,
    ) -> None:
        self._repository = repository
        self._cache = cache
        self._audit = audit
        self._minimum_count = minimum_trending_count

    async def record_search(
        self,
        *,
        request_id: str,
        normalized_query: str,
        category_slug: str | None,
        result_count: int,
        duration_ms: int,
    ) -> bool:
        query_hash = hashlib.sha256(normalized_query.encode()).hexdigest()
        safe_query = (
            normalized_query if is_safe_aggregate_query(normalized_query) else None
        )
        created = await self._repository.add_event(
            SearchEvent(
                request_id=request_id,
                query_hash=query_hash,
                normalized_query=safe_query,
                category_slug=category_slug,
                result_count=max(result_count, 0),
                duration_ms=max(duration_ms, 0),
            )
        )
        await self._repository.commit()
        return created

    async def record_click(self, *, request_id: str, work_id: UUID) -> bool:
        recorded = await self._repository.record_click(request_id, work_id)
        await self._repository.commit()
        return recorded

    async def materialize(
        self, *, period: SearchSnapshotPeriod, now: datetime | None = None
    ) -> int:
        current = (now or datetime.now(UTC)).astimezone(UTC)
        if period is SearchSnapshotPeriod.HOURLY:
            end = current.replace(minute=0, second=0, microsecond=0)
            start = end - timedelta(hours=1)
        else:
            end = current.replace(hour=0, minute=0, second=0, microsecond=0)
            start = end - timedelta(days=1)
        count = await self._repository.aggregate(
            start=start, end=end, period=period.value, minimum_count=self._minimum_count
        )
        await self._repository.commit()
        return count

    async def trending(
        self,
        *,
        period: SearchSnapshotPeriod = SearchSnapshotPeriod.DAILY,
        limit: int = 10,
    ) -> tuple[TrendingSearch, ...]:
        if not 1 <= limit <= 25:
            raise DomainError(
                code="SEARCH_LIMIT_INVALID",
                message="Search limit is invalid.",
                status_code=422,
            )
        key = f"trending:{period.value.lower()}:{limit}"
        if self._cache:
            cached = await self._cache.get(key)
            if cached is not None:
                return tuple(TrendingSearch(**item) for item in json.loads(cached))
        rows = await self._repository.trending(period=period.value, limit=limit)
        if self._cache:
            await self._cache.set(
                key,
                json.dumps(
                    [
                        {
                            "query_hash": row.query_hash,
                            "query": row.query,
                            "search_count": row.search_count,
                        }
                        for row in rows
                    ],
                    ensure_ascii=False,
                ),
            )
        return rows

    async def related(self, *, slug: str, limit: int = 6) -> tuple[RelatedWork, ...]:
        if not 1 <= limit <= 12:
            raise DomainError(
                code="SEARCH_LIMIT_INVALID",
                message="Search limit is invalid.",
                status_code=422,
            )
        digest = hashlib.sha256(f"{slug.casefold()}:{limit}".encode()).hexdigest()
        key = f"related:{digest}"
        if self._cache:
            cached = await self._cache.get(key)
            if cached is not None:
                return tuple(
                    RelatedWork(
                        id=UUID(item["id"]),
                        slug=item["slug"],
                        title=item["title"],
                        short_description=item["short_description"],
                        category_name=item["category_name"],
                        category_slug=item["category_slug"],
                        published_at=datetime.fromisoformat(item["published_at"]),
                    )
                    for item in json.loads(cached)
                )
        rows = await self._repository.related(
            slug=slug, limit=limit, now=datetime.now(UTC)
        )
        if self._cache:
            await self._cache.set(
                key,
                json.dumps(
                    [
                        {
                            "id": str(row.id),
                            "slug": row.slug,
                            "title": row.title,
                            "short_description": row.short_description,
                            "category_name": row.category_name,
                            "category_slug": row.category_slug,
                            "published_at": row.published_at.isoformat(),
                        }
                        for row in rows
                    ],
                    ensure_ascii=False,
                ),
            )
        return rows

    async def analytics(
        self,
        principal: AuthPrincipal,
        *,
        start: datetime,
        end: datetime,
        category: str | None = None,
    ) -> SearchAnalyticsSummary:
        self._require_admin(principal)
        if end <= start or end - start > timedelta(days=366):
            raise DomainError(
                code="SEARCH_PERIOD_INVALID",
                message="Search analytics period is invalid.",
                status_code=422,
            )
        return await self._repository.analytics(start=start, end=end, category=category)

    async def suppress(
        self,
        principal: AuthPrincipal,
        *,
        query_hash: str,
        reason: str,
        suppressed: bool,
        request_id: str,
    ) -> None:
        self._require_admin(principal)
        if len(query_hash) != 64 or any(
            char not in "0123456789abcdef" for char in query_hash
        ):
            raise DomainError(
                code="SEARCH_HASH_INVALID",
                message="Search phrase hash is invalid.",
                status_code=422,
            )
        await self._repository.suppress(
            query_hash=query_hash,
            actor_id=principal.user_id,
            reason=reason,
            suppressed=suppressed,
        )
        if self._audit:
            self._audit.record(
                actor_user_id=principal.user_id,
                action="search.trending.suppress"
                if suppressed
                else "search.trending.restore",
                resource_type="search_phrase",
                resource_id=query_hash,
                after={"suppressed": suppressed, "reason": reason},
                request_id=request_id,
            )
        await self._repository.commit()

    async def audit_export(
        self,
        principal: AuthPrincipal,
        *,
        request_id: str,
        start: datetime,
        end: datetime,
        category: str | None,
    ) -> None:
        self._require_admin(principal)
        if self._audit:
            self._audit.record(
                actor_user_id=principal.user_id,
                action="search.analytics.export",
                resource_type="search_analytics",
                resource_id=f"{start.date()}:{end.date()}",
                after={"category": category, "aggregate_only": True},
                request_id=request_id,
            )
            await self._repository.commit()

    @staticmethod
    def _require_admin(principal: AuthPrincipal) -> None:
        if ADMIN_ROLES.isdisjoint(principal.roles):
            raise DomainError(
                code="SEARCH_ANALYTICS_FORBIDDEN",
                message="Search analytics access is forbidden.",
                status_code=403,
            )
