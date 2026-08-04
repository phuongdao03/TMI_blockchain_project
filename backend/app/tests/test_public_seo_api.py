from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.main import create_application
from app.modules.public.dependencies import enforce_public_rate_limit
from app.modules.public.publication_dependencies import get_public_seo_service
from app.modules.public.seo_service import PublicSitemapEntry, PublicSitemapManifest


class StubSeoService:
    async def manifest(self) -> PublicSitemapManifest:
        return PublicSitemapManifest(
            generation="safe-generation",
            total=1,
            page_size=10_000,
            page_count=1,
            generated_at=datetime(2026, 7, 31, tzinfo=UTC),
        )

    async def page(self, page: int) -> tuple[PublicSitemapEntry, ...]:
        if page != 1:
            return ()
        return (
            PublicSitemapEntry(
                slug="safe-public-work",
                last_modified=datetime(2026, 7, 31, tzinfo=UTC),
            ),
        )


def test_public_sitemap_api_contract_is_allowlisted() -> None:
    app = create_application()
    service = StubSeoService()
    app.dependency_overrides[get_public_seo_service] = lambda: service
    app.dependency_overrides[enforce_public_rate_limit] = lambda: None
    try:
        with TestClient(app) as client:
            manifest = client.get("/api/v1/public/seo/sitemap")
            assert manifest.status_code == 200
            assert manifest.json()["data"] == {
                "generation": "safe-generation",
                "total": 1,
                "pageSize": 10_000,
                "pageCount": 1,
                "generatedAt": "2026-07-31T00:00:00Z",
            }
            page = client.get("/api/v1/public/seo/sitemap/1")
            assert page.status_code == 200
            assert page.json()["data"] == [
                {
                    "slug": "safe-public-work",
                    "lastModified": "2026-07-31T00:00:00Z",
                }
            ]
            assert client.get("/api/v1/public/seo/sitemap/0").status_code == 422
    finally:
        app.dependency_overrides.clear()
