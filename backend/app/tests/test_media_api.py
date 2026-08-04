import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

import httpx

from app.core.config import Settings
from app.core.health import HealthService
from app.main import create_application
from app.modules.auth.dependencies import (
    get_csrf_protected_principal,
    get_current_principal,
)
from app.modules.auth.session_service import AuthPrincipal
from app.modules.media.dependencies import (
    enforce_upload_signature_rate_limit,
    get_media_service,
)
from app.modules.media.models import MediaStatus
from app.modules.media.types import (
    MediaAssetView,
    SignedDeliveryView,
    UploadCompletion,
    UploadIntent,
    UploadSignatureView,
)

NOW = datetime(2026, 7, 30, 8, 0, tzinfo=UTC)


class StubMediaService:
    def __init__(self) -> None:
        self.media_id = uuid4()
        self.public_id = f"ip-certificate/local/user/avatar/{self.media_id}"
        self.intent: UploadIntent | None = None
        self.completion: UploadCompletion | None = None
        self.deleted: UUID | None = None

    async def create_upload_signature(
        self,
        principal: AuthPrincipal,
        intent: UploadIntent,
    ) -> UploadSignatureView:
        self.intent = intent
        return UploadSignatureView(
            media_id=self.media_id,
            public_id=self.public_id,
            upload_url="https://api.cloudinary.test/image/upload",
            cloud_name="demo",
            api_key="key",
            signature="signature",
            parameters={
                "public_id": self.public_id,
                "timestamp": "1785398400",
                "type": "authenticated",
            },
            expires_at=1_785_398_700,
        )

    async def complete_upload(
        self,
        principal: AuthPrincipal,
        completion: UploadCompletion,
    ) -> MediaAssetView:
        self.completion = completion
        return MediaAssetView(
            id=self.media_id,
            status=MediaStatus.ACTIVE,
            mime_type="image/png",
            bytes=2_048,
            width=512,
            height=512,
            duration_ms=None,
        )

    async def create_signed_url(
        self,
        principal: AuthPrincipal,
        media_id: UUID,
    ) -> SignedDeliveryView:
        return SignedDeliveryView(
            url="https://api.cloudinary.test/download?signed=1",
            expires_at=1_785_398_700,
        )

    async def delete_asset(
        self,
        principal: AuthPrincipal,
        media_id: UUID,
    ) -> None:
        self.deleted = media_id


async def _request(
    method: str,
    path: str,
    service: StubMediaService,
    principal: AuthPrincipal,
    *,
    json: dict[str, object] | None = None,
) -> httpx.Response:
    app = create_application(
        settings=Settings.model_validate({"app_env": "local"}),
        health_service=HealthService({}),
    )
    app.dependency_overrides[get_media_service] = lambda: service
    app.dependency_overrides[enforce_upload_signature_rate_limit] = lambda: None
    app.dependency_overrides[get_current_principal] = lambda: principal
    app.dependency_overrides[get_csrf_protected_principal] = lambda: principal
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.request(method, path, json=json)


def test_media_api_contract_and_validation() -> None:
    principal = AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="owner@tmigroup.vn",
        roles=("APPLICANT",),
    )
    service = StubMediaService()
    base = "/api/v1/media"

    issued = asyncio.run(
        _request(
            "POST",
            f"{base}/upload-signature",
            service,
            principal,
            json={
                "purpose": "AVATAR",
                "filename": "portrait.png",
                "mimeType": "image/png",
                "size": 2_048,
            },
        )
    )
    completed = asyncio.run(
        _request(
            "POST",
            f"{base}/complete",
            service,
            principal,
            json={
                "mediaId": str(service.media_id),
                "publicId": service.public_id,
                "version": 17,
                "signature": "a" * 40,
            },
        )
    )
    delivery = asyncio.run(
        _request(
            "GET",
            f"{base}/{service.media_id}/signed-url",
            service,
            principal,
        )
    )
    deleted = asyncio.run(
        _request(
            "DELETE",
            f"{base}/{service.media_id}",
            service,
            principal,
        )
    )
    invalid = asyncio.run(
        _request(
            "POST",
            f"{base}/upload-signature",
            service,
            principal,
            json={
                "purpose": "AVATAR",
                "filename": "../portrait.exe",
                "mimeType": "application/x-msdownload",
                "size": 2_048,
            },
        )
    )

    assert issued.status_code == 201
    assert issued.json()["data"]["parameters"]["type"] == "authenticated"
    assert completed.json()["data"]["status"] == "ACTIVE"
    assert delivery.json()["data"]["expiresAt"] == 1_785_398_700
    assert deleted.json()["data"] == {"status": "deleted"}
    assert invalid.status_code == 422
    assert service.intent is not None
    assert service.completion is not None
    assert service.deleted == service.media_id
