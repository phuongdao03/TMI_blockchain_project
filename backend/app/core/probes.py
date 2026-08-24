import asyncio
from typing import Literal
from urllib.parse import quote

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


class CloudinaryProbe:
    """Validate that Cloudinary accepts the configured production credentials."""

    def __init__(
        self,
        *,
        cloud_name: str,
        api_key: str,
        api_secret: str,
        timeout_seconds: float,
    ) -> None:
        self._url = f"https://api.cloudinary.com/v1_1/{quote(cloud_name, safe='')}/ping"
        self._client = httpx.AsyncClient(
            auth=(api_key, api_secret), timeout=timeout_seconds
        )

    async def check(self) -> bool:
        try:
            response = await self._client.get(self._url)
            return response.is_success
        except httpx.HTTPError:
            return False

    async def close(self) -> None:
        await self._client.aclose()


class ClamAvProbe:
    """Check that the ClamAV daemon accepts its null-terminated PING command."""

    def __init__(self, *, host: str, port: int, timeout_seconds: float) -> None:
        self._host = host
        self._port = port
        self._timeout_seconds = timeout_seconds

    async def check(self) -> bool:
        try:
            async with asyncio.timeout(self._timeout_seconds):
                reader, writer = await asyncio.open_connection(self._host, self._port)
                try:
                    writer.write(b"zPING\0")
                    await writer.drain()
                    response = await reader.readuntil(b"\0")
                finally:
                    writer.close()
                    await writer.wait_closed()
        except (OSError, TimeoutError, asyncio.IncompleteReadError):
            return False
        return response.rstrip(b"\0") == b"PONG"

    async def close(self) -> None:
        return None
