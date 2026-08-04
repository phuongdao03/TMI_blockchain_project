import hashlib
import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.service import AuditService
from app.modules.search.history_models import (
    SearchHistoryEntry,
    SearchHistoryPreference,
)
from app.modules.search.history_repository import SearchHistoryRepository
from app.modules.search.history_types import SearchHistoryItem, SearchHistoryState
from app.modules.search.normalization import SearchQueryNormalizer

logger = logging.getLogger(__name__)


class SearchHistoryService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        retention_days: int,
        list_limit: int = 10,
        normalizer: SearchQueryNormalizer | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not 1 <= retention_days <= 365:
            raise ValueError("retention_days must be between 1 and 365")
        if not 1 <= list_limit <= 50:
            raise ValueError("list_limit must be between 1 and 50")
        self._session = session
        self._repository = SearchHistoryRepository(session)
        self._audit = AuditService(session)
        self._retention_days = retention_days
        self._list_limit = list_limit
        self._normalizer = normalizer or SearchQueryNormalizer()
        self._clock = clock or (lambda: datetime.now(UTC))

    async def get(self, user_id: UUID) -> SearchHistoryState:
        async with self._session.begin():
            preference = await self._repository.preference(user_id)
            if preference is None or not preference.is_enabled:
                return SearchHistoryState(is_enabled=False, items=())
            rows = await self._repository.list_for_user(
                user_id,
                limit=self._list_limit,
            )
        return SearchHistoryState(
            is_enabled=True,
            items=tuple(
                SearchHistoryItem(
                    id=row.id,
                    display_query=row.display_query,
                    searched_at=self._as_utc(row.searched_at),
                )
                for row in rows
            ),
        )

    async def set_consent(
        self,
        user_id: UUID,
        *,
        enabled: bool,
    ) -> SearchHistoryState:
        now = self._clock()
        async with self._session.begin():
            preference = await self._repository.preference(user_id, for_update=True)
            was_enabled = preference.is_enabled if preference is not None else False
            if preference is None:
                preference = SearchHistoryPreference(user_id=user_id)
                self._repository.add_preference(preference)
            preference.is_enabled = enabled
            preference.enabled_at = now if enabled else None
            preference.updated_at = now
            if not enabled:
                await self._repository.clear(user_id)
            self._audit.record(
                actor_user_id=user_id,
                action="search.history.consent_changed",
                resource_type="search_history_preference",
                resource_id=str(user_id),
                before={"is_enabled": was_enabled},
                after={"is_enabled": enabled},
            )
        logger.info(
            "search_history_consent_changed",
            extra={"user_id": str(user_id), "enabled": enabled},
        )
        return await self.get(user_id)

    async def record(self, user_id: UUID, query: str) -> bool:
        normalized = self._normalizer.normalize(query)
        if normalized.is_empty:
            return False
        query_hash = hashlib.sha256(normalized.normalized.encode("utf-8")).hexdigest()
        now = self._clock()
        try:
            async with self._session.begin():
                preference = await self._repository.preference(user_id)
                if preference is None or not preference.is_enabled:
                    return False
                existing = await self._repository.entry_by_hash(
                    user_id,
                    query_hash,
                    for_update=True,
                )
                if existing is None:
                    self._repository.add_entry(
                        SearchHistoryEntry(
                            user_id=user_id,
                            display_query=normalized.raw,
                            query_hash=query_hash,
                            searched_at=now,
                        )
                    )
                else:
                    existing.display_query = normalized.raw
                    existing.searched_at = now
                    existing.updated_at = now
                await self._session.flush()
        except IntegrityError:
            await self._session.rollback()
            async with self._session.begin():
                existing = await self._repository.entry_by_hash(
                    user_id,
                    query_hash,
                    for_update=True,
                )
                if existing is None:
                    raise
                existing.display_query = normalized.raw
                existing.searched_at = now
                existing.updated_at = now
        return True

    async def clear(self, user_id: UUID) -> int:
        async with self._session.begin():
            deleted = await self._repository.clear(user_id)
            self._audit.record(
                actor_user_id=user_id,
                action="search.history.cleared",
                resource_type="search_history",
                resource_id=str(user_id),
                after={"deleted_count": deleted},
            )
        logger.info(
            "search_history_cleared",
            extra={"user_id": str(user_id), "deleted_count": deleted},
        )
        return deleted

    async def purge_expired(self) -> int:
        cutoff = self._clock() - timedelta(days=self._retention_days)
        async with self._session.begin():
            deleted = await self._repository.purge_before(cutoff)
        logger.info(
            "search_history_retention_completed",
            extra={"deleted_count": deleted},
        )
        return deleted

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
