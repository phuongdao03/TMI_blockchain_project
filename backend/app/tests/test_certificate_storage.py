import asyncio

import httpx

from app.modules.certificates.storage import CloudinaryCertificateStorage


def test_raw_pdf_upload_records_cloudinary_public_id_with_extension() -> None:
    async def scenario() -> None:
        requested_id = "ip-certificate/production/certificates/example/v1"
        stored_id = f"{requested_id}.pdf"

        def respond(request: httpx.Request) -> httpx.Response:
            assert request.url.path.endswith("/raw/upload")
            assert stored_id.encode() in request.content
            return httpx.Response(
                200,
                json={"public_id": stored_id, "version": 7},
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            storage = CloudinaryCertificateStorage(
                cloud_name="example",
                api_key="test-key",
                api_secret="test-secret",
                timeout_seconds=5,
                client=client,
            )
            result = await storage.upload_pdf(public_id=requested_id, content=b"%PDF")

        assert result.public_id == stored_id
        assert result.version == 7

    asyncio.run(scenario())


def test_certificate_retry_recovers_matching_existing_pdf() -> None:
    async def scenario() -> None:
        requested_id = "ip-certificate/production/certificates/example/v1"
        stored_id = f"{requested_id}.pdf"
        content = b"%PDF"
        requests: list[httpx.Request] = []

        async def respond(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            if request.url.path.endswith("/raw/upload"):
                return httpx.Response(
                    400,
                    headers={"X-Cld-Error": "public id already exists"},
                    json={"error": {"message": "public id already exists"}},
                )
            if "/resources/raw/authenticated/" in request.url.path:
                return httpx.Response(
                    200,
                    json={
                        "public_id": stored_id,
                        "version": 7,
                        "resource_type": "raw",
                        "type": "authenticated",
                        "format": "pdf",
                        "bytes": len(content),
                    },
                )
            assert request.url.path.endswith("/raw/download")
            return httpx.Response(200, content=content)

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(respond),
            timeout=5,
        ) as client:
            storage = CloudinaryCertificateStorage(
                cloud_name="example",
                api_key="test-key",
                api_secret="test-secret",
                timeout_seconds=5,
                client=client,
            )
            result = await storage.upload_pdf(public_id=requested_id, content=content)

        assert result.public_id == stored_id
        assert result.version == 7
        assert [request.method for request in requests] == ["POST", "GET", "GET"]

    asyncio.run(scenario())


def test_certificate_retry_refuses_different_existing_content() -> None:
    async def scenario() -> None:
        public_id = "ip-certificate/production/certificates/example/v1.pdf"
        content = b"%PDF"

        async def respond(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/raw/upload"):
                return httpx.Response(400)
            if "/resources/raw/authenticated/" in request.url.path:
                return httpx.Response(
                    200,
                    json={
                        "public_id": public_id,
                        "version": 7,
                        "resource_type": "raw",
                        "type": "authenticated",
                        "format": "pdf",
                        "bytes": len(content),
                    },
                )
            return httpx.Response(200, content=b"NOPE")

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(respond),
            timeout=5,
        ) as client:
            storage = CloudinaryCertificateStorage(
                cloud_name="example",
                api_key="test-key",
                api_secret="test-secret",
                timeout_seconds=5,
                client=client,
            )
            try:
                await storage.upload_pdf(public_id=public_id, content=content)
            except RuntimeError as error:
                assert "different content" in str(error)
            else:
                raise AssertionError("A different existing certificate was accepted.")

    asyncio.run(scenario())
