import asyncio
from io import BytesIO
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI, Request
from PIL import Image, PngImagePlugin
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1.promotion_media import public_router, router
from app.core.config import Settings, get_settings
from app.core.errors import DomainError, install_exception_handlers
from app.db.base import Base
from app.db.session import get_session
from app.modules.audit.models import AuditLog
from app.modules.auth.dependencies import get_current_principal
from app.modules.auth.models import User
from app.modules.auth.session_service import AuthPrincipal
from app.modules.auth.tokens import CsrfTokenManager
from app.modules.promotions.admin_access import require_promotion_access
from app.modules.promotions.media_models import PromotionMediaAsset
from app.modules.promotions.media_service import PromotionMediaService, normalize_image


def _png():
    output = BytesIO()
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("Location", "private-location")
    Image.new("RGB", (48, 32), "gold").save(output, "PNG", pnginfo=metadata)
    return output.getvalue()


def test_normalizes_real_image_and_strips_metadata():
    result = normalize_image(_png(), max_bytes=5_242_880, max_pixels=1_000_000)
    assert result.mime_type == "image/webp"
    assert (result.width, result.height) == (48, 32)
    with Image.open(BytesIO(result.data)) as image:
        assert "Location" not in image.info


@pytest.mark.parametrize(
    "body", [b"<svg><script>alert(1)</script></svg>", b"not-an-image"]
)
def test_rejects_forged_or_unsupported_image(body):
    with pytest.raises(DomainError) as error:
        normalize_image(body, max_bytes=1000, max_pixels=1_000_000)
    assert error.value.code == "PROMOTION_MEDIA_INVALID"


def test_rejects_large_file_and_decompression_bomb():
    with pytest.raises(DomainError):
        normalize_image(_png(), max_bytes=1, max_pixels=1_000_000)
    with pytest.raises(DomainError):
        normalize_image(_png(), max_bytes=1000, max_pixels=10)


def test_access_requires_server_permission_or_super_admin():
    regular = AuthPrincipal(
        user_id=uuid4(), session_id=uuid4(), email="user@example.vn", roles=("USER",)
    )
    with pytest.raises(DomainError) as error:
        require_promotion_access(regular)
    assert error.value.status_code == 403
    reader = AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="reader@example.vn",
        roles=("USER",),
        permissions=("promotions.read",),
    )
    require_promotion_access(reader, write=False)
    with pytest.raises(DomainError):
        require_promotion_access(reader)


def test_media_delete_preserves_original_bytes_and_audit():
    async def scenario():
        engine = create_async_engine("sqlite+aiosqlite://")
        async with engine.begin() as conn:
            await conn.run_sync(
                lambda c: Base.metadata.create_all(
                    c,
                    tables=[
                        User.__table__,
                        AuditLog.__table__,
                        PromotionMediaAsset.__table__,
                    ],
                )
            )
        factory = async_sessionmaker(engine, expire_on_commit=False)
        owner = uuid4()
        async with factory() as session:
            session.add(User(id=owner, email="owner@example.vn"))
            await session.commit()
            service = PromotionMediaService(session)
            asset = await service.upload(
                body=_png(), filename="voucher.png", alt_text="Tri ân", actor_id=owner
            )
            assert (
                asset.original_filename == "voucher.png"
                and asset.mime_type == "image/webp"
            )
            before = bytes(asset.content)
            await service.delete(asset.id, actor_id=owner)
            assert (await service.list(page=1, page_size=20))[1] == 0
            # Soft deletion only hides the library entry. Issued vouchers keep
            # a durable image URL and must continue to render.
            saved = await service.public_asset(asset.id)
            assert saved.content == before
            assert len(list(await session.scalars(select(AuditLog)))) == 2
        await engine.dispose()

    asyncio.run(scenario())


def test_media_api_rbac_csrf_real_file_validation_and_safe_delivery():
    async def scenario():
        engine = create_async_engine("sqlite+aiosqlite://")
        async with engine.begin() as conn:
            await conn.run_sync(
                lambda c: Base.metadata.create_all(
                    c,
                    tables=[
                        User.__table__,
                        AuditLog.__table__,
                        PromotionMediaAsset.__table__,
                    ],
                )
            )
        factory = async_sessionmaker(engine, expire_on_commit=False)
        owner, session_id = uuid4(), uuid4()
        async with factory() as session:
            session.add(User(id=owner, email="owner@example.vn"))
            await session.commit()
        app = FastAPI()
        app.include_router(router)
        app.include_router(public_router)
        install_exception_handlers(app)
        settings = Settings(
            auth_csrf_secret=SecretStr("test-media-secret-of-at-least-32-bytes")
        )
        roles = ("USER",)

        async def principal():
            return AuthPrincipal(
                user_id=owner,
                session_id=session_id,
                email="owner@example.vn",
                roles=roles,
            )

        async def session_dependency():
            async with factory() as session:
                yield session

        @app.middleware("http")
        async def request_id(request: Request, call_next):
            request.state.request_id = "media-test"
            return await call_next(request)

        app.dependency_overrides[get_current_principal] = principal
        app.dependency_overrides[get_session] = session_dependency
        app.dependency_overrides[get_settings] = lambda: settings
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            assert (
                await client.get("/api/v1/admin/promotion-media")
            ).status_code == 403
            roles = ("SUPER_ADMIN",)
            path = "/api/v1/admin/promotion-media?filename=voucher.png&altText=Voucher"
            assert (await client.post(path, content=_png())).status_code == 403
            token = CsrfTokenManager(
                secret=settings.auth_csrf_secret.get_secret_value()
            ).issue(session_id)
            client.cookies.set(settings.auth_csrf_cookie_name, token)
            headers = {"X-CSRF-Token": token, "Content-Type": "image/png"}
            assert (
                await client.post(
                    path, content=b"<script>bad</script>", headers=headers
                )
            ).status_code == 422
            response = await client.post(path, content=_png(), headers=headers)
            assert response.status_code == 200
            asset = response.json()["data"]
            assert asset["mimeType"] == "image/webp"
            public = await client.get(asset["url"])
            assert public.status_code == 200
            assert public.headers["x-content-type-options"] == "nosniff"
            assert public.headers["content-type"] == "image/webp"
            cached = await client.get(
                asset["url"], headers={"If-None-Match": public.headers["etag"]}
            )
            assert cached.status_code == 304
            assert (
                await client.delete(
                    f"/api/v1/admin/promotion-media/{asset['id']}", headers=headers
                )
            ).status_code == 200
            assert (await client.get(asset["url"])).status_code == 200
        await engine.dispose()

    asyncio.run(scenario())
