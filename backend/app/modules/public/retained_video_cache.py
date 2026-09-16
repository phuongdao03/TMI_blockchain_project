"""Short-lived RAM reuse for legacy video; callers must authorize every request."""

import asyncio
from collections import OrderedDict
from collections.abc import Callable, Coroutine
from time import monotonic
from typing import Any

from fastapi import HTTPException


class RetainedVideoCache:
    def __init__(self, *, max_bytes: int = 128 * 1024 * 1024, ttl: float = 120) -> None:
        self.max_bytes, self.ttl = max_bytes, ttl
        self._entries: OrderedDict[str, tuple[float, bytes]] = OrderedDict()
        self._pending: dict[str, asyncio.Task[bytes]] = {}

    def _expire(self, key: str, expiry: float) -> None:
        entry = self._entries.get(key)
        if entry is not None and entry[0] == expiry:
            del self._entries[key]

    async def get(
        self, key: str, load: Callable[[], Coroutine[Any, Any, bytes]]
    ) -> bytes:
        now = monotonic()
        for stale in tuple(self._entries):
            if self._entries[stale][0] <= now:
                del self._entries[stale]
        if key in self._entries:
            self._entries.move_to_end(key)
            return self._entries[key][1]
        pending = self._pending.get(key)
        if pending is None:
            if len(self._pending) >= 2:
                raise HTTPException(
                    status_code=503, detail="Video đang bận. Hãy thử lại sau."
                )
            pending = asyncio.create_task(load())
            self._pending[key] = pending
            pending.add_done_callback(lambda task: self._finish(key, task))
        return await asyncio.shield(pending)

    def _finish(self, key: str, task: asyncio.Task[bytes]) -> None:
        self._pending.pop(key, None)
        if task.cancelled() or task.exception() is not None:
            return
        content = task.result()
        if len(content) > self.max_bytes:
            return
        while self._entries and (
            len(self._entries) >= 4
            or sum(len(entry[1]) for entry in self._entries.values()) + len(content)
            > self.max_bytes
        ):
            self._entries.popitem(last=False)
        expiry = monotonic() + self.ttl
        self._entries[key] = (expiry, content)
        asyncio.get_running_loop().call_later(self.ttl, self._expire, key, expiry)


retained_video_cache = RetainedVideoCache()
