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
from app.modules.dossiers.errors import DossierForbiddenError
from app.modules.dossiers.models import (
    DocumentHashAdjudicationAction,
    DossierStatus,
    DossierVisibility,
)
from app.modules.dossiers.types import (
    CreateDossier,
    DocumentHashAdjudicationView,
    DossierChanges,
    DossierDetailView,
    DossierPage,
    DossierView,
)

NOW = datetime(2026, 7, 31, 8, 0, tzinfo=UTC)


class StubDossierService:
    def __init__(self, principal: AuthPrincipal) -> None:
        self.principal = principal
        self.dossier_id = uuid4()
        self.category_id = uuid4()
        self.created: CreateDossier | None = None
        self.updated: DossierChanges | None = None
        self.filters: tuple[DossierStatus | None, UUID | None, int, int] | None = None
        self.forbidden = False
        self.override_request: tuple[UUID, UUID, str] | None = None

    def _view(self) -> DossierView:
        return DossierView(
            id=self.dossier_id,
            code="TMI-2026-ABCDEF123456",
            owner_user_id=self.principal.user_id,
            organization_id=None,
            category_id=self.category_id,
            title="Bộ nhận diện TMI",
            slug="bo-nhan-dien-tmi",
            summary="Hồ sơ quyền sở hữu.",
            status=DossierStatus.DRAFT,
            visibility=DossierVisibility.PRIVATE,
            current_version_no=0,
            submitted_at=None,
            created_at=NOW,
            updated_at=NOW,
            can_edit=True,
        )

    def _require_access(self) -> None:
        if self.forbidden:
            raise DossierForbiddenError()

    async def create_dossier(
        self,
        principal: AuthPrincipal,
        payload: CreateDossier,
    ) -> DossierView:
        self.created = payload
        return self._view()

    async def list_dossiers(
        self,
        principal: AuthPrincipal,
        *,
        status: DossierStatus | None = None,
        category_id: UUID | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> DossierPage:
        self.filters = (status, category_id, page, page_size)
        return DossierPage(items=(self._view(),), total=1)

    async def get_dossier(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
    ) -> DossierView:
        self._require_access()
        return self._view()

    async def get_dossier_detail(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
    ) -> DossierDetailView:
        self._require_access()
        return DossierDetailView(dossier=self._view(), evidences=())

    async def update_dossier(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
        changes: DossierChanges,
    ) -> DossierView:
        self.updated = changes
        return self._view()

    async def delete_dossier(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
    ) -> None:
        return None

    async def grant_document_hash_override(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
        *,
        media_asset_id: UUID,
        reason: str,
    ) -> DocumentHashAdjudicationView:
        self.override_request = (dossier_id, media_asset_id, reason)
        return DocumentHashAdjudicationView(
            id=uuid4(),
            dossier_id=dossier_id,
            media_asset_id=media_asset_id,
            action=DocumentHashAdjudicationAction.ALLOW_REANCHOR,
            created_at=NOW,
        )


async def _request(
    method: str,
    path: str,
    service: StubDossierService,
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


def _principal() -> AuthPrincipal:
    return AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="owner@tmigroup.vn",
        roles=("APPLICANT",),
    )


def test_dossier_crud_contract_filters_and_pagination() -> None:
    principal = _principal()
    service = StubDossierService(principal)
    base = "/api/v1/dossiers"

    created = asyncio.run(
        _request(
            "POST",
            base,
            service,
            principal,
            json={
                "categoryId": str(service.category_id),
                "title": "Bộ nhận diện TMI",
                "slug": "bo-nhan-dien-tmi",
                "summary": "Hồ sơ quyền sở hữu.",
                "visibility": "PRIVATE",
            },
        )
    )
    listed = asyncio.run(
        _request(
            "GET",
            (
                f"{base}?status=DRAFT&categoryId={service.category_id}"
                "&page=2&pageSize=10"
            ),
            service,
            principal,
        )
    )
    detail = asyncio.run(
        _request("GET", f"{base}/{service.dossier_id}", service, principal)
    )
    updated = asyncio.run(
        _request(
            "PATCH",
            f"{base}/{service.dossier_id}",
            service,
            principal,
            json={"title": "Bộ nhận diện TMI Group", "summary": None},
        )
    )
    deleted = asyncio.run(
        _request("DELETE", f"{base}/{service.dossier_id}", service, principal)
    )

    assert created.status_code == 201
    assert created.json()["data"]["code"] == "TMI-2026-ABCDEF123456"
    assert created.json()["data"]["canEdit"] is True
    assert listed.status_code == detail.status_code == updated.status_code == 200
    assert listed.json()["meta"] == {
        "requestId": listed.json()["meta"]["requestId"],
        "page": 2,
        "pageSize": 10,
        "total": 1,
    }
    assert deleted.json()["data"] == {"status": "deleted"}
    assert service.created is not None
    assert service.created.category_id == service.category_id
    assert service.filters == (
        DossierStatus.DRAFT,
        service.category_id,
        2,
        10,
    )
    assert service.updated is not None
    assert service.updated.provided_fields == {"title", "summary"}


def test_dossier_validation_and_forbidden_error_contract() -> None:
    principal = _principal()
    service = StubDossierService(principal)
    base = "/api/v1/dossiers"

    invalid = asyncio.run(
        _request(
            "POST",
            base,
            service,
            principal,
            json={"categoryId": str(service.category_id), "title": "   "},
        )
    )
    empty_patch = asyncio.run(
        _request(
            "PATCH",
            f"{base}/{service.dossier_id}",
            service,
            principal,
            json={},
        )
    )
    service.forbidden = True
    forbidden = asyncio.run(
        _request("GET", f"{base}/{service.dossier_id}", service, principal)
    )

    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"
    assert empty_patch.status_code == 422
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "DOSSIER_FORBIDDEN"


def test_document_claim_override_api_uses_english_resource_contract() -> None:
    principal = _principal()
    service = StubDossierService(principal)
    media_asset_id = uuid4()
    response = asyncio.run(
        _request(
            "POST",
            f"/api/v1/dossiers/{service.dossier_id}/document-claim-overrides",
            service,
            principal,
            json={
                "mediaAssetId": str(media_asset_id),
                "reason": "Ownership evidence was reviewed and approved.",
            },
        )
    )

    assert response.status_code == 201
    assert response.json()["data"] == {
        "id": response.json()["data"]["id"],
        "dossierId": str(service.dossier_id),
        "mediaAssetId": str(media_asset_id),
        "action": "ALLOW_REANCHOR",
        "createdAt": NOW.isoformat().replace("+00:00", "Z"),
    }
    assert service.override_request == (
        service.dossier_id,
        media_asset_id,
        "Ownership evidence was reviewed and approved.",
    )
