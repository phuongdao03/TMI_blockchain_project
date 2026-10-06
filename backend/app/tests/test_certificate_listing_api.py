from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.main import create_application
from app.modules.auth.dependencies import get_current_principal
from app.modules.auth.session_service import AuthPrincipal
from app.modules.certificates.dependencies import get_certificate_version_service
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


def test_issued_content_correction_requires_csrf() -> None:
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
    app.dependency_overrides[get_certificate_version_service] = forbidden_service
    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/admin/certificates/{UUID(int=1)}/content-corrections",
            json={
                "expectedVersionNo": 1,
                "reason": "Sửa nội dung ghi nhận trên bằng xác lập cũ.",
                "content": {"title": "Tác phẩm", "category": "Danh mục"},
            },
        )
        assert response.status_code == 403
        assert not called
