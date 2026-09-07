import asyncio
import hashlib
import json
from datetime import UTC, datetime
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from app.modules.media.gateway import CloudinaryMediaGateway, MediaContentTooLargeError


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
            max_bytes=2_048,
        )
        assert issued.signature == gateway.sign_parameters(issued.parameters)
        assert "max_file_size" not in issued.parameters
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
            derivative_public_id=("ip-certificate/public/derivatives/relation-id"),
            transformation="c_limit,w_1600,h_1600,q_auto,f_webp",
        )

        assert derivative.mime_type == "image/webp"
        assert derivative.width == 1600
        assert "private/owner/source-id" not in derivative.url
        form = parse_qs(requests[0].content.decode())
        assert requests[0].url.path.endswith("/image/upload")
        assert form["public_id"] == ["ip-certificate/public/derivatives/relation-id"]
        assert form["type"] == ["upload"]
        assert form["overwrite"] == ["true"]
        assert form["invalidate"] == ["true"]
        assert form["transformation"] == ["c_limit,w_1600,h_1600,q_auto,f_webp"]
        assert "private%2Fowner%2Fsource-id" in form["file"][0]
        assert form["signature"]
        await gateway.close()
        await client.aclose()

    asyncio.run(exercise())


def test_cloudinary_streams_private_content_with_a_hard_size_limit() -> None:
    async def exercise() -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path.endswith("/image/download")
            return httpx.Response(200, content=b"0123456789")

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        gateway = CloudinaryMediaGateway(
            cloud_name="demo",
            api_key="api-key",
            api_secret="abcd",
            clock=lambda: 1_785_398_400,
            client=client,
        )
        content = await gateway.download_asset(
            public_id="private/asset",
            resource_type="image",
            file_format="png",
            max_bytes=10,
        )
        assert content == b"0123456789"

        with pytest.raises(MediaContentTooLargeError):
            await gateway.download_asset(
                public_id="private/asset",
                resource_type="image",
                file_format="png",
                max_bytes=9,
            )
        await gateway.close()
        await client.aclose()

    asyncio.run(exercise())


def test_cloudinary_uploads_encrypted_bytes_as_authenticated_raw_asset() -> None:
    async def exercise() -> None:
        requests: list[httpx.Request] = []

        async def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(
                200,
                json={
                    "public_id": "private/document-ciphertext",
                    "version": 9,
                    "resource_type": "raw",
                    "type": "authenticated",
                    "bytes": 18,
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
        ciphertext = b"encrypted-content!"
        stored = await gateway.upload_encrypted_asset(
            public_id="private/document-ciphertext",
            content=ciphertext,
        )

        assert stored.version == 9
        assert stored.bytes == len(ciphertext)
        assert requests[0].url.path.endswith("/raw/upload")
        assert ciphertext in requests[0].content
        assert b'filename="document"' in requests[0].content
        assert b'filename="document.enc"' not in requests[0].content
        assert b'name="type"' in requests[0].content
        assert b"authenticated" in requests[0].content
        assert b'name="signature"' in requests[0].content
        await gateway.close()
        await client.aclose()

    asyncio.run(exercise())


def test_cloudinary_chunks_large_encrypted_assets_and_reassembles_them() -> None:
    async def exercise() -> None:
        requests: list[httpx.Request] = []
        uploaded: dict[str, bytes] = {}
        deleted: list[str] = []

        def multipart_value(request: httpx.Request, name: str) -> bytes:
            marker = f'name="{name}"'.encode()
            start = request.content.index(marker)
            start = request.content.index(b"\r\n\r\n", start) + 4
            boundary = b"\r\n--" + request.headers["content-type"].split(
                "boundary=", 1
            )[1].encode()
            end = request.content.index(boundary, start)
            return request.content[start:end]

        async def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            if request.method == "POST" and request.url.path.endswith("/raw/upload"):
                uploaded_public_id = multipart_value(request, "public_id").decode()
                uploaded_content = multipart_value(request, "file")
                uploaded[uploaded_public_id] = uploaded_content
                return httpx.Response(
                    200,
                    json={
                        "public_id": uploaded_public_id,
                        "version": len(uploaded),
                        "resource_type": "raw",
                        "type": "authenticated",
                        "bytes": len(uploaded_content),
                    },
                )
            if request.method == "POST" and request.url.path.endswith("/raw/destroy"):
                deleted.append(parse_qs(request.content.decode())["public_id"][0])
                return httpx.Response(200, json={"result": "ok"})
            public_id = parse_qs(request.url.query.decode())["public_id"][0]
            return httpx.Response(200, content=uploaded[public_id])

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        gateway = CloudinaryMediaGateway(
            cloud_name="demo",
            api_key="api-key",
            api_secret="abcd",
            clock=lambda: 1_785_398_400,
            client=client,
        )
        ciphertext = b"a" * (8 * 1_048_576) + b"encrypted-tail"
        stored = await gateway.upload_encrypted_asset(
            public_id="private/large-ciphertext",
            content=ciphertext,
        )

        assert stored.public_id == "private/large-ciphertext"
        assert stored.bytes == len(ciphertext)
        assert len(uploaded) == 3
        assert uploaded["private/large-ciphertext.part-00000"] == ciphertext[
            : 8 * 1_048_576
        ]
        assert uploaded["private/large-ciphertext.part-00001"] == b"encrypted-tail"
        manifest_bytes = uploaded["private/large-ciphertext"]
        assert manifest_bytes.startswith(b"TMI-ENCRYPTED-PARTS-V1\n")
        manifest = json.loads(manifest_bytes.split(b"\n", 1)[1])
        assert manifest == {
            "bytes": len(ciphertext),
            "parts": [
                {
                    "bytes": 8 * 1_048_576,
                    "public_id": "private/large-ciphertext.part-00000",
                    "sha256": hashlib.sha256(ciphertext[: 8 * 1_048_576]).hexdigest(),
                },
                {
                    "bytes": len(b"encrypted-tail"),
                    "public_id": "private/large-ciphertext.part-00001",
                    "sha256": hashlib.sha256(b"encrypted-tail").hexdigest(),
                },
            ],
            "version": 1,
        }

        downloaded = await gateway.download_asset(
            public_id=stored.public_id,
            resource_type="raw",
            file_format="bin",
            max_bytes=len(ciphertext),
        )
        assert downloaded == ciphertext

        await gateway.delete_asset(
            public_id=stored.public_id,
            resource_type="raw",
        )
        assert deleted == [
            "private/large-ciphertext.part-00000",
            "private/large-ciphertext.part-00001",
            "private/large-ciphertext",
        ]
        await gateway.close()
        await client.aclose()

    asyncio.run(exercise())
