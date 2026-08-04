from typing import Literal

import httpx
from pydantic import BaseModel, ValidationError
from redis.asyncio import Redis
from redis.exceptions import RedisError


class JsonRpcResponse(BaseModel):
    jsonrpc: Literal["2.0"]
    id: int
    result: str | None = None
    error: dict[str, object] | None = None


class RedisProbe:
    def __init__(self, *, url: str, timeout_seconds: float) -> None:
        self._client: Redis = Redis.from_url(
            url,
            socket_connect_timeout=timeout_seconds,
            socket_timeout=timeout_seconds,
        )

    async def check(self) -> bool:
        try:
            return bool(await self._client.ping())
        except (RedisError, OSError, TimeoutError):
            return False

    async def close(self) -> None:
        await self._client.aclose()


class AnvilProbe:
    def __init__(self, *, url: str, timeout_seconds: float) -> None:
        self._url = url
        self._client = httpx.AsyncClient(timeout=timeout_seconds)

    async def check(self) -> bool:
        try:
            response = await self._client.post(
                self._url,
                json={
                    "jsonrpc": "2.0",
                    "method": "web3_clientVersion",
                    "params": [],
                    "id": 1,
                },
            )
            response.raise_for_status()
            payload = JsonRpcResponse.model_validate(response.json())
            return payload.result is not None and payload.error is None
        except (httpx.HTTPError, ValidationError, ValueError):
            return False

    async def close(self) -> None:
        await self._client.aclose()
