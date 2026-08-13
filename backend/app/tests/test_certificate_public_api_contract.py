from app.core.config import Settings
from app.main import create_application
from app.modules.public.schemas import PublicCertificateVersionData


def test_certificate_and_public_routes_match_the_planned_contract() -> None:
    app = create_application(settings=Settings())
    paths = app.openapi()["paths"]

    for path in (
        "/api/v1/certificates",
        "/api/v1/certificates/{certificate_id}",
        "/api/v1/certificates/{certificate_id}/download",
        "/api/v1/certificates/{certificate_id}/versions",
        "/api/v1/certificates/{certificate_id}/version-requests",
        "/api/v1/admin/certificate-version-requests",
        "/api/v1/admin/certificate-version-requests/{version_id}",
        "/api/v1/admin/certificates/{certificate_id}/revocations",
        "/api/v1/public/home",
        "/api/v1/public/categories",
        "/api/v1/public/assets",
        "/api/v1/public/assets/{slug}",
        "/api/v1/public/map",
        "/api/v1/verify/{token}",
        "/api/v1/verify/certificate/{number}",
        "/api/v1/verify/certificate/{number}/versions",
        "/api/v1/verify/transaction/{tx_hash}",
    ):
        assert path in paths

    certificate_paths = [path for path in paths if "certificate" in path]
    assert all("chung-thu" not in path for path in certificate_paths)
    assert set(PublicCertificateVersionData.model_fields) == {
        "version_no",
        "status",
        "metadata_hash",
        "transaction_hash",
        "block_number",
        "confirmed_at",
        "created_at",
        "issuer_label",
        "documents",
    }
