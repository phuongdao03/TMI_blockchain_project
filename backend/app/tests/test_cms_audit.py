import asyncio
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.modules.audit.models import AuditLog
from app.modules.audit.service import AuditService
from app.modules.auth.session_service import AuthPrincipal
from app.modules.cms.errors import CmsSlugConflictError
from app.modules.cms.models import CmsContentStatus, CmsPost
from app.modules.cms.service import CmsPostInput, CmsService


def _principal(*roles: str) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=uuid4(),
        email="content@tmigroup.vn",
        roles=roles,
        session_id=uuid4(),
    )


def test_cms_publish_sanitizes_html_and_records_audit(tmp_path: Path) -> None:
    async def exercise() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'cms.sqlite3').as_posix()}"
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            service = CmsService(session=session, audit=AuditService(session))
            principal = _principal("SUPER_ADMIN")
            post = await service.create_post(
                principal,
                CmsPostInput(
                    title="Tin xác lập",
                    slug="tin-xac-lap",
                    excerpt="Thông báo",
                    body_html='<p onclick="steal()">An toàn</p><script>bad()</script>',
                    category_id=None,
                ),
                request_id="req-1",
            )
            published = await service.publish_post(
                principal, post.id, request_id="req-2"
            )
            assert published.status is CmsContentStatus.PUBLISHED
            assert "onclick" not in published.body_html
            assert "script" not in published.body_html

            audit_rows = tuple((await session.scalars(select(AuditLog))).all())
            assert [row.action for row in audit_rows] == [
                "cms.post.created",
                "cms.post.published",
            ]
            assert audit_rows[0].after_json is not None
            assert audit_rows[0].after_json["body_html"] == "[REDACTED]"
            await session.rollback()

            with pytest.raises(CmsSlugConflictError):
                await service.create_post(
                    principal,
                    CmsPostInput(
                        title="Trùng slug",
                        slug="tin-xac-lap",
                        excerpt=None,
                        body_html="<p>Nội dung</p>",
                        category_id=None,
                    ),
                    request_id="req-3",
                )
        await engine.dispose()

    asyncio.run(exercise())


def test_only_published_posts_are_public(tmp_path: Path) -> None:
    async def exercise() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'public-cms.sqlite3').as_posix()}"
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            service = CmsService(session=session, audit=AuditService(session))
            principal = _principal("SUPER_ADMIN")
            await service.create_post(
                principal,
                CmsPostInput("Bản nháp", "ban-nhap", None, "<p>Draft</p>", None),
                request_id="req-1",
            )
            published = await service.create_post(
                principal,
                CmsPostInput("Công khai", "cong-khai", None, "<p>Live</p>", None),
                request_id="req-2",
            )
            await service.publish_post(principal, published.id, request_id="req-3")
            rows, total = await service.list_public_posts(page=1, page_size=20)
            assert total == 1
            assert [row.slug for row in rows] == ["cong-khai"]
            assert await session.scalar(
                select(CmsPost).where(CmsPost.slug == "ban-nhap")
            )
        await engine.dispose()

    asyncio.run(exercise())
