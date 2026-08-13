import asyncio
from collections.abc import AsyncIterator
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
from app.modules.blockchain.verification import (
    DocumentVerificationStatus,
    DocumentVerificationView,
)
from app.modules.blockchain.verification_dependencies import (
    get_document_verification_service,
)
from app.modules.public.dependencies import (
    enforce_public_rate_limit,
    get_public_verification,
)
from app.modules.public.verification import (
    PublicEvidenceProof,
    VerificationStatus,
    VerificationView,
)


class StubPublicVerification:
    async def verify_number(self, number: str) -> VerificationView:
        return VerificationView(
            status=VerificationStatus.VALID,
            checked_at=datetime(2026, 8, 12, 8, 0, tzinfo=UTC),
            certificate_number=number,
            documents=(
                PublicEvidenceProof(
                    title="Public proof",
                    evidence_type="OWNERSHIP",
                    sha256=(
                        "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
                    ),
                ),
            ),
        )


class StubDocumentVerification:
    def __init__(self) -> None:
        self.private_media_id: UUID | None = None

    async def verify_public(
        self,
        *,
        expected_sha256: str | None,
        certificate_is_confirmed: bool,
        chunks: AsyncIterator[bytes],
    ) -> DocumentVerificationView:
        async for _chunk in chunks:
            pass
        return DocumentVerificationView(
            status=(
                DocumentVerificationStatus.MATCH
                if expected_sha256 and certificate_is_confirmed
                else DocumentVerificationStatus.NOT_FOUND
            ),
            checked_at=datetime(2026, 8, 12, 8, 0, tzinfo=UTC),
        )

    async def verify(
        self,
        principal: AuthPrincipal,
        media_id: UUID,
        chunks: AsyncIterator[bytes],
    ) -> DocumentVerificationView:
        self.private_media_id = media_id
        async for _chunk in chunks:
            pass
        return DocumentVerificationView(
            status=DocumentVerificationStatus.NOT_AUTHORIZED,
            checked_at=datetime(2026, 8, 12, 8, 0, tzinfo=UTC),
        )


async def _request(
    method: str,
    path: str,
    *,
    content: bytes,
    content_type: str = "application/octet-stream",
    content_length: int | None = None,
) -> httpx.Response:
    app = create_application(
        settings=Settings.model_validate({"app_env": "local"}),
        health_service=HealthService({}),
    )
    principal = AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="applicant@example.test",
        roles=("APPLICANT",),
    )
    service = StubDocumentVerification()
    app.dependency_overrides[enforce_public_rate_limit] = lambda: None
    app.dependency_overrides[get_public_verification] = StubPublicVerification
    app.dependency_overrides[get_document_verification_service] = lambda: service
    app.dependency_overrides[get_current_principal] = lambda: principal
    app.dependency_overrides[get_csrf_protected_principal] = lambda: principal
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            headers = {"Content-Type": content_type}
            if content_length is not None:
                headers["Content-Length"] = str(content_length)
            return await client.request(
                method,
                path,
                content=content,
                headers=headers,
            )


def test_document_verification_routes_are_english_and_return_bounded_statuses() -> None:
    public_response = asyncio.run(
        _request(
            "POST",
            "/api/v1/public/certificates/TMI-2026-0001/documents/0/verifications",
            content=b"hello",
        )
    )
    private_response = asyncio.run(
        _request(
            "POST",
            f"/api/v1/media/{uuid4()}/verifications",
            content=b"hello",
        )
    )

    assert public_response.status_code == 200
    assert public_response.json()["data"] == {
        "status": "MATCH",
        "checkedAt": "2026-08-12T08:00:00Z",
    }
    assert private_response.status_code == 200
    assert private_response.json()["data"]["status"] == "NOT_AUTHORIZED"


def test_document_verification_openapi_does_not_add_vietnamese_paths() -> None:
    paths = create_application(settings=Settings()).openapi()["paths"]

    assert (
        "/api/v1/public/certificates/{number}/documents/{document_index}/verifications"
        in paths
    )
    assert "/api/v1/media/{media_id}/verifications" in paths
    assert all("xac-minh" not in path and "tai-lieu" not in path for path in paths)


def test_document_verification_rejects_non_binary_and_oversized_bodies_early() -> None:
    wrong_type = asyncio.run(
        _request(
            "POST",
            "/api/v1/public/certificates/TMI-2026-0001/documents/0/verifications",
            content=b"hello",
            content_type="application/json",
        )
    )
    oversized = asyncio.run(
        _request(
            "POST",
            f"/api/v1/media/{uuid4()}/verifications",
            content=b"hello",
            content_length=26_214_401,
        )
    )

    assert wrong_type.status_code == 415
    assert oversized.status_code == 413
