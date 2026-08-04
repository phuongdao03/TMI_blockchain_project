import asyncio
from datetime import UTC, datetime
from urllib.parse import parse_qs, urlparse

import httpx

from app.modules.media.gateway import CloudinaryMediaGateway


def test_cloudinary_signatures_and_expiring_private_url() -> None:
    async def exercise() -> None:
        gateway = CloudinaryMediaGateway(
            cloud_name="demo",
            api_key="api-key",
            api_secret="abcd",
        )
        issued = await gateway.create_upload_signature(
            public_id="ip-certificate/local/user/avatar/asset",
            resource_type="image",
            timestamp=1_596_000_000,
            allowed_format="png",
        )
        assert issued.signature == gateway.sign_parameters(issued.parameters)
        assert gateway.verify_upload_result(
            public_id="sample",
            version=1_315_063_250,
            signature=gateway.sign_parameters(
                {"public_id": "sample", "version": "1315063250"}
            ),
        )
        assert not gateway.verify_upload_result(
            public_id="sample",
            version=1_315_063_250,
            signature="tampered",
        )

        expires_at = int(datetime(2026, 7, 30, 8, 5, tzinfo=UTC).timestamp())
        url = gateway.create_signed_delivery_url(
            public_id="ip-certificate/local/user/avatar/asset",
            resource_type="image",
            file_format="png",
            expires_at=expires_at,
        )
        query = parse_qs(urlparse(url).query)
        assert query["expires_at"] == [str(expires_at)]
        assert query["type"] == ["authenticated"]
        assert query["api_key"] == ["api-key"]
        assert query["signature"]
        await gateway.close()

    asyncio.run(exercise())


def test_cloudinary_metadata_and_delete_contract() -> None:
    async def exercise() -> None:
        requests: list[httpx.Request] = []

        async def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            if request.method == "GET":
                return httpx.Response(
                    200,
                    json={
                        "public_id": "folder/asset",
                        "version": 17,
                        "resource_type": "image",
                        "type": "authenticated",
                        "format": "png",
                        "bytes": 2_048,
                        "width": 512,
                        "height": 512,
                    },
                )
            return httpx.Response(200, json={"result": "ok"})

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        gateway = CloudinaryMediaGateway(
            cloud_name="demo",
            api_key="api-key",
            api_secret="abcd",
            clock=lambda: 1_785_398_400,
            client=client,
        )
        metadata = await gateway.get_asset_metadata(
            public_id="folder/asset",
            resource_type="image",
        )
        await gateway.delete_asset(
            public_id="folder/asset",
            resource_type="image",
        )

        assert metadata.file_format == "png"
        assert metadata.width == 512
        assert requests[0].url.path.endswith(
            "/resources/image/authenticated/folder/asset"
        )
        delete_form = parse_qs(requests[1].content.decode())
        assert delete_form["type"] == ["authenticated"]
        assert delete_form["invalidate"] == ["true"]
        assert delete_form["signature"]
        await gateway.close()
        await client.aclose()

    asyncio.run(exercise())


def test_cloudinary_creates_isolated_public_derivative() -> None:
    async def exercise() -> None:
        requests: list[httpx.Request] = []

        async def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(
                200,
                json={
                    "public_id": "ip-certificate/public/derivatives/relation-id",
                    "secure_url": (
                        "https://res.cloudinary.com/demo/image/upload/"
                        "ip-certificate/public/derivatives/relation-id.webp"
                    ),
                    "resource_type": "image",
                    "format": "webp",
                    "width": 1600,
                    "height": 900,
                    "bytes": 4096,
                },
            )

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        gateway = CloudinaryMediaGateway(
            cloud_name="demo",
            api_key="api-key",
            api_secret="abcd",
            clock=lambda: 1_785_398_400,
            client=client,
        )
        derivative = await gateway.create_public_derivative(
            source_public_id="ip-certificate/private/owner/source-id",
            source_resource_type="image",
            source_format="png",
            derivative_public_id=(
                "ip-certificate/public/derivatives/relation-id"
            ),
            transformation="c_limit,w_1600,h_1600,q_auto,f_webp",
        )

        assert derivative.mime_type == "image/webp"
        assert derivative.width == 1600
        assert "private/owner/source-id" not in derivative.url
        form = parse_qs(requests[0].content.decode())
        assert requests[0].url.path.endswith("/image/upload")
        assert form["public_id"] == [
            "ip-certificate/public/derivatives/relation-id"
        ]
        assert form["type"] == ["upload"]
        assert form["overwrite"] == ["true"]
        assert form["invalidate"] == ["true"]
        assert form["transformation"] == [
            "c_limit,w_1600,h_1600,q_auto,f_webp"
        ]
        assert "private%2Fowner%2Fsource-id" in form["file"][0]
        assert form["signature"]
        await gateway.close()
        await client.aclose()

    asyncio.run(exercise())
