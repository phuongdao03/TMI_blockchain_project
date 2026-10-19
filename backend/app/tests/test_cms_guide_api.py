import asyncio
from pathlib import Path
from uuid import uuid4

import httpx
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.main import create_application
from app.modules.audit.service import AuditService
from app.modules.auth.dependencies import (
    get_csrf_protected_principal,
    get_current_principal,
    get_employee_profile_link_status,
)
from app.modules.auth.session_service import AuthPrincipal
from app.modules.cms.dependencies import get_cms_service
from app.modules.cms.models import CmsContentStatus
from app.modules.cms.service import CmsGuideArticleInput, CmsService
from app.modules.engagement.errors import EngagementRateLimitedError
from app.modules.public.dependencies import enforce_public_engagement_rate_limit


def _principal(*roles: str) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=uuid4(),
        email="guide-test@example.test",
        roles=roles,
        session_id=uuid4(),
    )


def test_guide_api_filters_public_private_and_admin_content(tmp_path: Path) -> None:
    async def exercise() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'cms-guide-api.sqlite3').as_posix()}"
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            service = CmsService(session=session, audit=AuditService(session))
            admin = _principal("SUPER_ADMIN")
            articles = (
                ("public-guide", ("PUBLIC",), CmsContentStatus.PUBLISHED),
                ("review-guide", ("MODERATOR",), CmsContentStatus.PUBLISHED),
                ("draft-guide", ("SUPER_ADMIN",), CmsContentStatus.DRAFT),
            )
            for slug, audiences, status in articles:
                row = await service.create_guide_article(
                    admin,
                    CmsGuideArticleInput(
                        title=slug,
                        slug=slug,
                        summary="Verified article.",
                        category="guide",
                        audiences=audiences,
                        body_html="<p>Verified steps.</p>",
                        sort_order=1,
                    ),
                    request_id=f"create-{slug}",
                )
                if status is CmsContentStatus.PUBLISHED:
                    await service.set_guide_article_status(
                        admin,
                        row.id,
                        status,
                        request_id=f"publish-{slug}",
                    )
                if slug == "public-guide":
                    public_guide_id = row.id

            app = create_application()
            active_principal = [_principal("MODERATOR")]
            employee = [False]
            app.dependency_overrides[get_cms_service] = lambda: service
            app.dependency_overrides[get_current_principal] = lambda: active_principal[
                0
            ]
            app.dependency_overrides[get_csrf_protected_principal] = lambda: (
                active_principal[0]
            )
            app.dependency_overrides[get_employee_profile_link_status] = lambda: (
                employee[0]
            )
            app.dependency_overrides[enforce_public_engagement_rate_limit] = lambda: (
                None
            )
            try:
                transport = httpx.ASGITransport(app=app)
                async with httpx.AsyncClient(
                    transport=transport, base_url="http://test"
                ) as client:
                    public = await client.get("/api/v1/public/guide/articles")
                    assert public.status_code == 200
                    assert [item["slug"] for item in public.json()["data"]] == [
                        "public-guide"
                    ]
                    accepted_feedback = await client.post(
                        "/api/v1/public/guide/articles/public-guide/feedback",
                        json={"helpful": True, "clientToken": str(uuid4())},
                    )
                    assert accepted_feedback.status_code == 200
                    hidden_private = await client.get(
                        "/api/v1/public/guide/articles/review-guide"
                    )
                    assert hidden_private.status_code == 404

                    mine = await client.get("/api/v1/guide/articles")
                    assert mine.status_code == 200
                    assert {item["slug"] for item in mine.json()["data"]} == {
                        "public-guide",
                        "review-guide",
                    }
                    forbidden_admin = await client.get(
                        "/api/v1/admin/cms/guide-articles"
                    )
                    assert forbidden_admin.status_code == 403
                    forbidden_feedback = await client.get(
                        f"/api/v1/admin/cms/guide-articles/{public_guide_id}/feedback"
                    )
                    assert forbidden_feedback.status_code == 403

                    active_principal[0] = admin
                    admin_rows = await client.get("/api/v1/admin/cms/guide-articles")
                    assert admin_rows.status_code == 200
                    assert {item["slug"] for item in admin_rows.json()["data"]} == {
                        "public-guide",
                        "review-guide",
                        "draft-guide",
                    }
                    feedback_rows = await client.get(
                        f"/api/v1/admin/cms/guide-articles/{public_guide_id}/feedback"
                    )
                    assert feedback_rows.status_code == 200
                    assert feedback_rows.json()["meta"]["total"] == 1
                    assert feedback_rows.json()["data"][0]["helpful"] is True
                    assert "clientTokenHash" not in feedback_rows.json()["data"][0]

                    async def rate_limited() -> None:
                        raise EngagementRateLimitedError(retry_after_seconds=9)

                    app.dependency_overrides[enforce_public_engagement_rate_limit] = (
                        rate_limited
                    )
                    rejected_feedback = await client.post(
                        "/api/v1/public/guide/articles/public-guide/feedback",
                        json={"helpful": False, "clientToken": str(uuid4())},
                    )
                    assert rejected_feedback.status_code == 429
                    assert (
                        rejected_feedback.json()["error"]["code"]
                        == "ENGAGEMENT_RATE_LIMITED"
                    )
            finally:
                app.dependency_overrides.clear()
        await engine.dispose()

    asyncio.run(exercise())
