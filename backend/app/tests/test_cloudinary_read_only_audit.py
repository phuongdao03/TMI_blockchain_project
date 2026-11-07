import asyncio

import httpx
import pytest

from app.scripts.cloudinary_read_only_audit import (
    CloudinaryAuditError,
    _page,
)


def test_cloudinary_audit_paginates_with_get_only() -> None:
    async def scenario() -> None:
        requests: list[httpx.Request] = []

        async def respond(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            if request.url.params.get("next_cursor") == "next":
                return httpx.Response(200, json={"resources": [{"public_id": "b"}]})
            return httpx.Response(
                200,
                json={
                    "resources": [{"public_id": "a"}],
                    "next_cursor": "next",
                },
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            resources, complete = await _page(
                client,
                config={
                    "CLOUDINARY_CLOUD_NAME": "demo",
                    "CLOUDINARY_API_KEY": "key",
                    "CLOUDINARY_API_SECRET": "secret",
                },
                resource_type="image",
                delivery_type="authenticated",
                prefix="cns/local/",
                request_count=[0],
                request_limit=2,
            )

        assert [request.method for request in requests] == ["GET", "GET"]
        assert [resource["public_id"] for resource in resources] == ["a", "b"]
        assert complete

    asyncio.run(scenario())


def test_cloudinary_audit_stops_when_admin_api_is_rate_limited() -> None:
    async def scenario() -> None:
        requests: list[httpx.Request] = []

        async def respond(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(420)

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            with pytest.raises(CloudinaryAuditError, match="HTTP 420"):
                await _page(
                    client,
                    config={
                        "CLOUDINARY_CLOUD_NAME": "demo",
                        "CLOUDINARY_API_KEY": "key",
                        "CLOUDINARY_API_SECRET": "secret",
                    },
                    resource_type="image",
                    delivery_type="authenticated",
                    prefix="cns/local/",
                    request_count=[0],
                    request_limit=2,
                )

        assert len(requests) == 1

    asyncio.run(scenario())
