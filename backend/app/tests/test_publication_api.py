from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import create_application
from app.modules.auth.dependencies import get_csrf_protected_principal
from app.modules.auth.session_service import AuthPrincipal
from app.modules.public.errors import PublicWorkForbiddenError
from app.modules.public.models import (
    PublicationStatus,
    PublicWork,
    PublicWorkVisibility,
)
from app.modules.public.publication_dependencies import get_publication_service


class StubPublicationService:
    def __init__(self, *, forbidden: bool = False) -> None:
        self.forbidden = forbidden
        self.calls: list[tuple[str, int]] = []
        self.row = PublicWork(
            id=uuid4(),
            dossier_id=uuid4(),
            certificate_id=uuid4(),
            owner_user_id=uuid4(),
            slug="api-work",
            title="API work",
            short_description="Approved description",
            category_id=uuid4(),
            publication_status=PublicationStatus.PUBLISHED,
            visibility=PublicWorkVisibility.PUBLIC,
            published_at=datetime(2026, 7, 31, tzinfo=UTC),
            version=2,
        )

    async def publish(
        self, _principal: object, _work_id: object, **data: object
    ) -> PublicWork:
        if self.forbidden:
            raise PublicWorkForbiddenError()
        expected_version = data["expected_version"]
        assert isinstance(expected_version, int)
        self.calls.append(("publish", expected_version))
        return self.row

    async def feature(
        self, _principal: object, _work_id: object, **data: object
    ) -> PublicWork:
        expected_version = data["expected_version"]
        assert isinstance(expected_version, int)
        self.calls.append(("feature", expected_version))
        self.row.featured_at = data["featured_at"]  # type: ignore[assignment]
        self.row.featured_until = data["featured_until"]  # type: ignore[assignment]
        return self.row


def _principal() -> AuthPrincipal:
    return AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="content-admin@example.test",
        roles=("CONTENT_ADMIN",),
    )


def test_publication_admin_contract_and_allowlisted_response() -> None:
    service = StubPublicationService()
    app = create_application()
    app.dependency_overrides[get_publication_service] = lambda: service
    app.dependency_overrides[get_csrf_protected_principal] = _principal
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/admin/public-works/{service.row.id}/publish",
                json={"expectedVersion": 1, "visibility": "PUBLIC"},
            )
            assert response.status_code == 200
            assert response.json()["data"] == {
                "id": str(service.row.id),
                "dossierId": str(service.row.dossier_id),
                "certificateId": str(service.row.certificate_id),
                "slug": "api-work",
                "title": "API work",
                "shortDescription": "Approved description",
                "publicationStatus": "PUBLISHED",
                "visibility": "PUBLIC",
                "publishedAt": "2026-07-31T00:00:00Z",
                "scheduledPublishAt": None,
                "featuredAt": None,
                "featuredUntil": None,
                "version": 2,
            }
            assert service.calls == [("publish", 1)]

            featured = client.post(
                f"/api/v1/admin/public-works/{service.row.id}/feature",
                json={
                    "expectedVersion": 2,
                    "featuredAt": "2026-07-31T08:00:00+07:00",
                    "featuredUntil": "2026-08-01T08:00:00+07:00",
                },
            )
            assert featured.status_code == 200
            assert featured.json()["data"]["featuredAt"] == (
                "2026-07-31T08:00:00+07:00"
            )
            assert service.calls[-1] == ("feature", 2)

            invalid = client.post(
                f"/api/v1/admin/public-works/{service.row.id}/publish",
                json={"expectedVersion": 0, "visibility": "PUBLIC"},
            )
            assert invalid.status_code == 422
            assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"

        paths = app.openapi()["paths"]
        for action in (
            "publish",
            "schedule",
            "hide",
            "suspend",
            "archive",
            "feature",
            "unfeature",
        ):
            assert f"/api/v1/admin/public-works/{{work_id}}/{action}" in paths
        assert "/api/v1/public/works/featured" in paths
    finally:
        app.dependency_overrides.clear()


def test_publication_admin_forbidden_error_is_stable() -> None:
    service = StubPublicationService(forbidden=True)
    app = create_application()
    app.dependency_overrides[get_publication_service] = lambda: service
    app.dependency_overrides[get_csrf_protected_principal] = _principal
    try:
        with TestClient(app) as client:
            response = client.post(
                f"/api/v1/admin/public-works/{service.row.id}/publish",
                json={"expectedVersion": 1, "visibility": "PUBLIC"},
            )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "PUBLIC_WORK_FORBIDDEN"
    finally:
        app.dependency_overrides.clear()
