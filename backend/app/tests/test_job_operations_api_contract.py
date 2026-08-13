from app.core.config import Settings
from app.main import create_application


def test_job_operations_routes_use_english_resource_contracts() -> None:
    paths = create_application(settings=Settings()).openapi()["paths"]
    expected = {
        "/api/v1/admin/operations/jobs": {"get"},
        "/api/v1/admin/operations/jobs/{job_id}": {"get"},
        "/api/v1/admin/operations/jobs/{job_id}/replays": {"post"},
        "/api/v1/admin/operations/jobs/{job_id}/cancellations": {"post"},
    }

    for path, methods in expected.items():
        assert path in paths
        assert methods.issubset(paths[path])

    assert all("cong-viec" not in path and "xu-ly" not in path for path in paths)
