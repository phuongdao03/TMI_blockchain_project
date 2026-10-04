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
