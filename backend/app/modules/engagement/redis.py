from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.modules.engagement.errors import EngagementUnavailableError
from app.modules.engagement.visitor import EngagementVisitorContext


class RedisViewDeduplicator:
    def __init__(
        self,
        client: Redis,
        *,
        visitor_context: EngagementVisitorContext,
        ttl_seconds: int,
    ) -> None:
        self._client = client
        self._visitor_context = visitor_context
        self._ttl_seconds = ttl_seconds

    async def accept(self, *, visitor: str, public_work_id: str) -> bool:
        key = (
            f"engagement:view:{public_work_id}:{self._visitor_context.digest(visitor)}"
        )
        try:
            return bool(
                await self._client.set(
                    key,
                    "1",
                    ex=self._ttl_seconds,
                    nx=True,
                )
            )
        except (RedisError, OSError, TimeoutError) as exc:
            raise EngagementUnavailableError() from exc


class RedisShareDeduplicator:
    def __init__(
        self,
        client: Redis,
        *,
        visitor_context: EngagementVisitorContext,
        ttl_seconds: int,
    ) -> None:
        self._client = client
        self._visitor_context = visitor_context
        self._ttl_seconds = ttl_seconds

    async def accept(
        self,
        *,
        visitor: str,
        public_work_id: str,
        channel: str,
    ) -> bool:
        key = (
            "engagement:share:"
            f"{public_work_id}:{channel}:{self._visitor_context.digest(visitor)}"
        )
        try:
            return bool(
                await self._client.set(
                    key,
                    "1",
                    ex=self._ttl_seconds,
                    nx=True,
                )
            )
        except (RedisError, OSError, TimeoutError) as exc:
            raise EngagementUnavailableError() from exc


class RedisQrScanDeduplicator:
    def __init__(
        self,
        client: Redis,
        *,
        visitor_context: EngagementVisitorContext,
        ttl_seconds: int,
    ) -> None:
        self._client = client
        self._visitor_context = visitor_context
        self._ttl_seconds = ttl_seconds

    async def accept(self, *, visitor: str, public_work_id: str) -> bool:
        key = f"engagement:qr:{public_work_id}:{self._visitor_context.digest(visitor)}"
        try:
            return bool(await self._client.set(key, "1", ex=self._ttl_seconds, nx=True))
        except (RedisError, OSError, TimeoutError) as exc:
            raise EngagementUnavailableError() from exc
