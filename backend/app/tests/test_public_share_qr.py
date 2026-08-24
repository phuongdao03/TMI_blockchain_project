import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import Settings
from app.db.base import Base
from app.main import create_application
from app.modules.dossiers.models import Category
from app.modules.engagement.qr_service import QrShareLinkService
from app.modules.public.dependencies import (
    enforce_public_engagement_rate_limit,
    enforce_public_rate_limit,
)
from app.modules.public.models import (
    PublicationStatus,
    PublicWork,
    PublicWorkVisibility,
)
from app.modules.public.publication_dependencies import get_public_qr_service
from app.modules.public.share_service import (
    PublicQrCodeService,
    PublicShareConfigurationError,
    QrCodePngRenderer,
    RenderedPublicQr,
    canonical_public_origin,
    canonical_public_work_url,
)

NOW = datetime(2026, 7, 31, tzinfo=UTC)


class CapturingRenderer:
    def __init__(self) -> None:
        self.payloads: list[str] = []

    def render(self, payload: str) -> bytes:
        self.payloads.append(payload)
        return b"\x89PNG\r\n\x1a\npublic-qr"


class StubShareLinks:
    async def token_for_work(self, _public_work_id: UUID) -> str:
        return "opaque-share-token"


class StubQrService:
    async def render(self, slug: str) -> RenderedPublicQr | None:
        if slug == "suspended":
            return None
        return RenderedPublicQr(
            png=b"\x89PNG\r\n\x1a\napi-qr",
            payload=f"https://catalog.tmi.vn/r/{'a' * 43}",
        )


class StubRedirectService:
    async def resolve_redirect(self, _token: str, *, visitor: str) -> str:
        assert visitor
        return "public-work"


def test_canonical_share_domain_and_unicode_slug() -> None:
    assert (
        canonical_public_work_url(
            "https://catalog.tmi.vn/",
            "di-sản-số",
            allow_local_http=False,
        )
        == "https://catalog.tmi.vn/works/di-s%E1%BA%A3n-s%E1%BB%91"
    )
    with pytest.raises(PublicShareConfigurationError):
        canonical_public_work_url(
            "http://catalog.tmi.vn",
            "unsafe",
            allow_local_http=False,
        )
    assert (
        canonical_public_work_url(
            "http://localhost:3000",
            "local-work",
            allow_local_http=True,
        )
        == "http://localhost:3000/works/local-work"
    )
    assert (
        QrCodePngRenderer()
        .render("https://catalog.tmi.vn/works/scan-ready")
        .startswith(b"\x89PNG\r\n\x1a\n")
    )


@pytest.mark.parametrize(
    "unsafe_origin",
    (
        "https://user:password@catalog.tmi.vn",
        "https://catalog.tmi.vn/?tracking=1",
        "https://catalog.tmi.vn/#section",
    ),
)
def test_public_origin_rejects_credentials_and_non_origin_parts(
    unsafe_origin: str,
) -> None:
    with pytest.raises(PublicShareConfigurationError):
        canonical_public_origin(unsafe_origin, allow_local_http=False)


def test_qr_uses_opaque_payload_and_rejects_non_public_work(tmp_path: Path) -> None:
    async def exercise() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'share.sqlite3').as_posix()}"
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        category_id = uuid4()
        async with factory() as session:
            async with session.begin():
                session.add(
                    Category(
                        id=category_id,
                        code="SHARE",
                        name="Share",
                        slug="share",
                    )
                )
                session.add_all(
                    [
                        _work(
                            category_id,
                            slug="public-work",
                            visibility=PublicWorkVisibility.PUBLIC,
                            status=PublicationStatus.PUBLISHED,
                        ),
                        _work(
                            category_id,
                            slug="suspended",
                            visibility=PublicWorkVisibility.PUBLIC,
                            status=PublicationStatus.SUSPENDED,
                        ),
                    ]
                )
            renderer = CapturingRenderer()
            service = PublicQrCodeService(
                session,
                public_base_url="https://catalog.tmi.vn",
                allow_local_http=False,
                renderer=renderer,
                share_links=cast(QrShareLinkService, StubShareLinks()),
            )
            rendered = await service.render("public-work")
            assert rendered is not None
            assert rendered.png.startswith(b"\x89PNG")
            assert rendered.payload == ("https://catalog.tmi.vn/r/opaque-share-token")
            assert renderer.payloads == [rendered.payload]
            assert await service.render("suspended") is None
        await engine.dispose()

    asyncio.run(exercise())


def test_public_qr_api_headers_and_not_found_policy() -> None:
    app = create_application()
    app.dependency_overrides[get_public_qr_service] = lambda: StubQrService()
    app.dependency_overrides[enforce_public_rate_limit] = lambda: None
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/public/works/shareable/qr")
            assert response.status_code == 200
            assert response.headers["content-type"] == "image/png"
            assert response.headers["cache-control"] == "no-store"
            assert response.headers["x-robots-tag"] == "noindex, nofollow"
            assert response.headers["content-location"] == (
                f"https://catalog.tmi.vn/r/{'a' * 43}"
            )
            assert response.content.startswith(b"\x89PNG")
            assert client.get("/api/v1/public/works/suspended/qr").status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_opaque_share_redirect_uses_server_canonical_relative_path() -> None:
    app = create_application(
        settings=Settings(engagement_visitor_hmac_secret=SecretStr("s" * 32))
    )
    app.dependency_overrides[get_public_qr_service] = lambda: StubRedirectService()
    app.dependency_overrides[enforce_public_engagement_rate_limit] = lambda: None
    try:
        with TestClient(app, follow_redirects=False) as client:
            response = client.get(f"/r/{'a' * 43}")
        assert response.status_code == 302
        assert response.headers["location"] == "/works/public-work"
        assert response.headers["referrer-policy"] == "no-referrer"
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-robots-tag"] == "noindex, nofollow"
        assert "HttpOnly" in response.headers["set-cookie"]
    finally:
        app.dependency_overrides.clear()


def _work(
    category_id: UUID,
    *,
    slug: str,
    visibility: PublicWorkVisibility,
    status: PublicationStatus,
) -> PublicWork:
    return PublicWork(
        dossier_id=uuid4(),
        owner_user_id=uuid4(),
        slug=slug,
        title=slug,
        short_description="Public share test work.",
        category_id=category_id,
        publication_status=status,
        visibility=visibility,
        published_at=NOW,
    )
