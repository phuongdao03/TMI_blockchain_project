from collections.abc import Mapping

from app.modules.public.catalog_cache import CatalogCacheInvalidator

CACHE_AGGREGATE_TYPES = frozenset(
    {"public_work", "public_category", "public_tag"}
)


class CatalogCacheEventHandler:
    def __init__(self, invalidator: CatalogCacheInvalidator) -> None:
        self._invalidator = invalidator

    async def handle(
        self,
        *,
        aggregate_type: str,
        event_type: str,
        payload: Mapping[str, object],
    ) -> bool:
        if (
            aggregate_type not in CACHE_AGGREGATE_TYPES
            or payload.get("invalidate_cache") != "true"
        ):
            return False
        return (
            await self._invalidator.invalidate(reason=event_type)
        ) is not None
