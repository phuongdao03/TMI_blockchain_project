from app.core.config import Settings
from app.main import create_application


def test_certificate_and_public_routes_match_the_planned_contract() -> None:
    app = create_application(settings=Settings())
    paths = app.openapi()["paths"]

    for path in (
        "/api/v1/certificates",
        "/api/v1/certificates/{certificate_id}",
        "/api/v1/certificates/{certificate_id}/download",
        "/api/v1/public/home",
        "/api/v1/public/categories",
        "/api/v1/public/assets",
        "/api/v1/public/assets/{slug}",
        "/api/v1/public/map",
        "/api/v1/verify/{token}",
        "/api/v1/verify/certificate/{number}",
        "/api/v1/verify/transaction/{tx_hash}",
    ):
        assert path in paths
