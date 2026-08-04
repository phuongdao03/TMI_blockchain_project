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
from app.modules.dossiers.dependencies import get_dossier_service
from app.modules.dossiers.types import CreateEvidence, EvidenceChanges, EvidenceView

NOW = datetime(2026, 7, 31, 8, 0, tzinfo=UTC)


class StubEvidenceService:
    def __init__(self) -> None:
        self.evidence_id = uuid4()
        self.media_id = uuid4()
        self.created: CreateEvidence | None = None
        self.updated: EvidenceChanges | None = None

    def _view(self, dossier_id: UUID) -> EvidenceView:
        return EvidenceView(
            id=self.evidence_id,
            dossier_id=dossier_id,
            dossier_version_id=None,
            media_asset_id=self.media_id,
            evidence_type="OWNERSHIP_DOCUMENT",
            title="Giấy xác nhận",
            description=None,
            issued_at=NOW,
            display_order=0,
            is_public=False,
            mime_type="application/pdf",
            bytes=1024,
            sha256="a" * 64,
        )

    async def attach_evidence(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
        payload: CreateEvidence,
    ) -> EvidenceView:
        self.created = payload
        return self._view(dossier_id)

    async def update_evidence(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
        evidence_id: UUID,
        changes: EvidenceChanges,
    ) -> EvidenceView:
        self.updated = changes
        return self._view(dossier_id)

    async def remove_evidence(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
        evidence_id: UUID,
    ) -> None:
        return None


async def _request(
    method: str,
    path: str,
    service: StubEvidenceService,
    principal: AuthPrincipal,
    *,
    json: dict[str, object] | None = None,
) -> httpx.Response:
    app = create_application(
        settings=Settings.model_validate({"app_env": "local"}),
        health_service=HealthService({}),
    )
    app.dependency_overrides[get_dossier_service] = lambda: service
    app.dependency_overrides[get_current_principal] = lambda: principal
    app.dependency_overrides[get_csrf_protected_principal] = lambda: principal
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.request(method, path, json=json)


def test_evidence_attachment_api_contract() -> None:
    principal = AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="owner@tmigroup.vn",
        roles=("APPLICANT",),
    )
    service = StubEvidenceService()
    dossier_id = uuid4()
    base = f"/api/v1/dossiers/{dossier_id}/evidences"

    created = asyncio.run(
        _request(
            "POST",
            base,
            service,
            principal,
            json={
                "mediaAssetId": str(service.media_id),
                "evidenceType": "OWNERSHIP_DOCUMENT",
                "title": "Giấy xác nhận",
                "issuedAt": NOW.isoformat(),
            },
        )
    )
    updated = asyncio.run(
        _request(
            "PATCH",
            f"{base}/{service.evidence_id}",
            service,
            principal,
            json={"title": "Giấy xác nhận mới", "displayOrder": 2},
        )
    )
    removed = asyncio.run(
        _request(
            "DELETE",
            f"{base}/{service.evidence_id}",
            service,
            principal,
        )
    )

    assert created.status_code == 201
    assert created.json()["data"]["sha256"] == "a" * 64
    assert updated.status_code == 200
    assert removed.json()["data"] == {"status": "removed"}
    assert service.created is not None
    assert service.created.media_asset_id == service.media_id
    assert service.updated is not None
    assert service.updated.provided_fields == {"title", "display_order"}
