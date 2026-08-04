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
from app.modules.dossiers.models import DossierStatus, DossierVisibility
from app.modules.dossiers.types import (
    DossierStatusHistoryView,
    DossierVersionView,
    DossierView,
    SubmissionView,
)

NOW = datetime(2026, 7, 31, 8, 0, tzinfo=UTC)


class StubSubmissionService:
    def __init__(self, principal: AuthPrincipal) -> None:
        self.principal = principal
        self.dossier_id = uuid4()
        self.version_id = uuid4()
        self.keys: list[str] = []

    def _dossier(self) -> DossierView:
        return DossierView(
            id=self.dossier_id,
            code="TMI-2026-ABCDEF123456",
            owner_user_id=self.principal.user_id,
            organization_id=None,
            category_id=uuid4(),
            title="Tác phẩm số",
            slug=None,
            summary=None,
            status=DossierStatus.SUBMITTED,
            visibility=DossierVisibility.PRIVATE,
            current_version_no=1,
            submitted_at=NOW,
            created_at=NOW,
            updated_at=NOW,
            can_edit=False,
        )

    def _version(self) -> DossierVersionView:
        return DossierVersionView(
            id=self.version_id,
            dossier_id=self.dossier_id,
            version_no=1,
            snapshot_json={"schemaVersion": 1},
            canonical_hash="a" * 64,
            submitted_by=self.principal.user_id,
            submitted_at=NOW,
        )

    async def submit_dossier(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
        *,
        idempotency_key: str,
    ) -> SubmissionView:
        self.keys.append(idempotency_key)
        return SubmissionView(dossier=self._dossier(), version=self._version())

    async def resubmit_dossier(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
        *,
        idempotency_key: str,
    ) -> SubmissionView:
        self.keys.append(idempotency_key)
        return SubmissionView(dossier=self._dossier(), version=self._version())

    async def list_versions(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
    ) -> tuple[DossierVersionView, ...]:
        return (self._version(),)

    async def get_timeline(
        self,
        principal: AuthPrincipal,
        dossier_id: UUID,
    ) -> tuple[DossierStatusHistoryView, ...]:
        return (
            DossierStatusHistoryView(
                id=uuid4(),
                dossier_id=self.dossier_id,
                from_status=DossierStatus.DRAFT,
                to_status=DossierStatus.SUBMITTED,
                actor_user_id=self.principal.user_id,
                reason_code="APPLICANT_SUBMIT",
                note=None,
                created_at=NOW,
            ),
        )


async def _request(
    method: str,
    path: str,
    service: StubSubmissionService,
    principal: AuthPrincipal,
    *,
    headers: dict[str, str] | None = None,
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
            return await client.request(method, path, headers=headers)


def test_submission_version_and_timeline_contract() -> None:
    principal = AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="owner@tmigroup.vn",
        roles=("APPLICANT",),
    )
    service = StubSubmissionService(principal)
    base = f"/api/v1/dossiers/{service.dossier_id}"
    headers = {"Idempotency-Key": "browser-submit-1"}

    submitted = asyncio.run(
        _request("POST", f"{base}/submit", service, principal, headers=headers)
    )
    resubmitted = asyncio.run(
        _request("POST", f"{base}/resubmit", service, principal, headers=headers)
    )
    versions = asyncio.run(_request("GET", f"{base}/versions", service, principal))
    timeline = asyncio.run(_request("GET", f"{base}/timeline", service, principal))
    missing_key = asyncio.run(_request("POST", f"{base}/submit", service, principal))

    assert submitted.status_code == resubmitted.status_code == 200
    assert submitted.json()["data"]["version"]["canonicalHash"] == "a" * 64
    assert versions.json()["data"][0]["versionNo"] == 1
    assert timeline.json()["data"][0]["toStatus"] == "SUBMITTED"
    assert missing_key.status_code == 422
    assert service.keys == ["browser-submit-1", "browser-submit-1"]
