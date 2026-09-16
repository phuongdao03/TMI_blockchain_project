import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.modules.public.retained_video_cache import RetainedVideoCache


def test_range_and_cover_requests_share_one_retained_download() -> None:
    async def exercise() -> None:
        cache = RetainedVideoCache(max_bytes=6)
        load = AsyncMock(return_value=b"video")
        results = await asyncio.gather(
            cache.get("asset", load), cache.get("asset", load)
        )
        assert list(results) == [b"video", b"video"]
        assert await cache.get("asset", load) == b"video"
        assert load.await_count == 1

    asyncio.run(exercise())


def test_expiry_and_memory_budget_do_not_keep_plaintext_indefinitely() -> None:
    async def exercise() -> None:
        cache = RetainedVideoCache(max_bytes=6)
        load = AsyncMock(return_value=b"video")
        with patch(
            "app.modules.public.retained_video_cache.monotonic", return_value=100
        ):
            await cache.get("first", load)
            await cache.get("second", load)
            assert sum(len(entry[1]) for entry in cache._entries.values()) <= 6
        with patch(
            "app.modules.public.retained_video_cache.monotonic", return_value=221
        ):
            await cache.get("second", load)
            assert load.await_count == 3
        oversized = AsyncMock(return_value=b"too large")
        await cache.get("large", oversized)
        await cache.get("large", oversized)
        assert oversized.await_count == 2

    asyncio.run(exercise())


def test_failed_download_can_be_retried() -> None:
    async def exercise() -> None:
        cache = RetainedVideoCache()
        load = AsyncMock(side_effect=[ValueError("bad input"), b"video"])
        with pytest.raises(ValueError):
            await cache.get("asset", load)
        assert await cache.get("asset", load) == b"video"

    asyncio.run(exercise())
