from app.core.config import Settings
from app.main import create_application


def test_work_allocation_api_exposes_admin_and_personal_routes() -> None:
    paths = create_application(settings=Settings()).openapi()["paths"]

    assert {"get", "post"}.issubset(paths["/api/v1/admin/work-allocations"])
    assert "get" in paths["/api/v1/admin/work-allocations/{allocation_id}"]
    assert "post" in paths["/api/v1/admin/work-allocations/{allocation_id}/activate"]
    assert "get" in paths["/api/v1/me/work-allocations"]
