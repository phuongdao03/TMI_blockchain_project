from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.main import create_application
from app.modules.auth.dependencies import get_current_principal
from app.modules.auth.session_service import AuthPrincipal
from app.modules.public.publication_dependencies import get_public_work_editor_service


def test_certificate_listing_requires_csrf_before_calling_editor() -> None:
    app = create_application()
    called = False

    def forbidden_service() -> None:
        nonlocal called
        called = True

    principal = AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        roles=("SUPER_ADMIN",),
        email="admin@example.test",
    )
    app.dependency_overrides[get_current_principal] = lambda: principal
    app.dependency_overrides[get_public_work_editor_service] = forbidden_service
    with TestClient(app) as client:
        response = client.patch(
            f"/api/v1/admin/certificates/{UUID(int=1)}/listing",
            json={"expectedWorkVersion": 1, "showCertificate": True},
        )
        assert response.status_code == 403
        assert not called
