import asyncio
import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.modules.audit.models import AuditLog
from app.modules.audit.service import AuditService
from app.modules.auth.session_service import AuthPrincipal
from app.modules.cms.errors import (
    CmsForbiddenError,
    CmsGuideFeedbackConflictError,
    CmsNotFoundError,
)
from app.modules.cms.models import CmsContentStatus, CmsGuideFeedback
from app.modules.cms.service import CmsGuideArticleInput, CmsService
from app.modules.memberships.models import MembershipPlan, UserMembership


def _principal(*roles: str) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=uuid4(),
        email="admin@example.test",
        roles=roles,
        session_id=uuid4(),
    )


def test_guide_lifecycle_sanitizes_content_and_records_versions(tmp_path: Path) -> None:
    async def exercise() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'cms-guides.sqlite3').as_posix()}"
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            service = CmsService(session=session, audit=AuditService(session))
            admin = _principal("SUPER_ADMIN")
            draft = await service.create_guide_article(
                admin,
                CmsGuideArticleInput(
                    title="Tạo tài khoản",
                    slug="tao-tai-khoan",
                    summary="Hướng dẫn đăng nhập.",
                    category="account",
                    audiences=("PUBLIC",),
                    body_html=(
                        "<h2>Đăng ký</h2>"
                        '<p onclick="run()">Bắt đầu</p>'
                        "<script>bad()</script>"
                    ),
                    sort_order=1,
                ),
                request_id="guide-create",
            )
            assert draft.status is CmsContentStatus.DRAFT
            assert "onclick" not in draft.body_html
            assert "script" not in draft.body_html

            published = await service.set_guide_article_status(
                admin,
                draft.id,
                CmsContentStatus.PUBLISHED,
                request_id="guide-publish",
            )
            assert published.status is CmsContentStatus.PUBLISHED
            assert published.published_at is not None

            public_rows, total = await service.list_public_guide_articles(
                page=1, page_size=20, query="TAO tai khoan"
            )
            assert total == 1
            assert [row.slug for row in public_rows] == ["tao-tai-khoan"]
            assert await service.get_public_guide_article("tao-tai-khoan")

            audit_rows = tuple(
                (
                    await session.scalars(
                        select(AuditLog).where(
                            AuditLog.resource_type == "cms_guide_article"
                        )
                    )
                ).all()
            )
            assert [row.action for row in audit_rows] == [
                "cms.guide_article.created",
                "cms.guide_article.published",
            ]
            await session.rollback()
        await engine.dispose()

    asyncio.run(exercise())


def test_private_guides_are_filtered_by_role_and_employee_access(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        database_path = (tmp_path / "cms-guide-audience.sqlite3").as_posix()
        engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            service = CmsService(session=session, audit=AuditService(session))
            admin = _principal("SUPER_ADMIN")
            silver_member = _principal("USER")
            async with session.begin():
                plan = MembershipPlan(
                    name="Silver",
                    tier="SILVER",
                    amount_minor=490_000,
                    duration_days=365,
                )
                session.add(plan)
                await session.flush()
                session.add(
                    UserMembership(
                        user_id=silver_member.user_id,
                        plan_id=plan.id,
                        tier="SILVER",
                        expires_at=datetime.now(UTC) + timedelta(days=365),
                    )
                )
            for slug, audiences in (
                ("review-work", ("MODERATOR",)),
                ("employee-time", ("EMPLOYEE",)),
                ("admin-work", ("SUPER_ADMIN",)),
                ("member-library", ("MEMBERSHIP_SILVER",)),
            ):
                row = await service.create_guide_article(
                    admin,
                    CmsGuideArticleInput(
                        title=slug,
                        slug=slug,
                        summary="Verified workflow.",
                        category="operations",
                        audiences=audiences,
                        body_html="<p>Private steps.</p>",
                        sort_order=1,
                    ),
                    request_id=f"create-{slug}",
                )
                await service.set_guide_article_status(
                    admin,
                    row.id,
                    CmsContentStatus.PUBLISHED,
                    request_id=f"publish-{slug}",
                )

            (
                reviewer_rows,
                reviewer_total,
            ) = await service.list_accessible_guide_articles(
                _principal("MODERATOR"), is_employee=False, page=1, page_size=20
            )
            assert reviewer_total == 1
            assert [row.slug for row in reviewer_rows] == ["review-work"]

            (
                employee_rows,
                employee_total,
            ) = await service.list_accessible_guide_articles(
                _principal("USER"), is_employee=True, page=1, page_size=20
            )
            assert employee_total == 1
            assert [row.slug for row in employee_rows] == ["employee-time"]

            silver_rows, silver_total = await service.list_accessible_guide_articles(
                silver_member, is_employee=False, page=1, page_size=20
            )
            assert silver_total == 1
            assert [row.slug for row in silver_rows] == ["member-library"]

            with pytest.raises(CmsNotFoundError):
                await service.get_accessible_guide_article(
                    _principal("USER"), "member-library", is_employee=False
                )

            admin_rows, admin_total = await service.list_accessible_guide_articles(
                admin, is_employee=False, page=1, page_size=20
            )
            assert admin_total == 1
            assert [row.slug for row in admin_rows] == ["admin-work"]
            search_rows, search_total = await service.list_accessible_guide_articles(
                admin, is_employee=False, page=1, page_size=20, query="review"
            )
            assert search_total == 0
            assert search_rows == ()
            with pytest.raises(CmsNotFoundError):
                await service.get_accessible_guide_article(
                    admin, "review-work", is_employee=False
                )

            with pytest.raises(CmsNotFoundError) as denied:
                await service.get_accessible_guide_article(
                    _principal("USER"), "admin-work", is_employee=False
                )
            assert denied.value.status_code == 404
        await engine.dispose()

    asyncio.run(exercise())


def test_guide_search_ranks_title_matches_before_body_matches(tmp_path: Path) -> None:
    async def exercise() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'cms-guide-search.sqlite3').as_posix()}"
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            service = CmsService(session=session, audit=AuditService(session))
            admin = _principal("SUPER_ADMIN")
            articles = (
                CmsGuideArticleInput(
                    title="Hướng dẫn tạo hồ sơ đề cử",
                    slug="tao-ho-so",
                    summary="Các bước chuẩn bị thông tin.",
                    category="dossiers",
                    audiences=("PUBLIC",),
                    body_html="<p>Điền các trường cần thiết.</p>",
                    sort_order=20,
                ),
                CmsGuideArticleInput(
                    title="Tìm thông tin trên hệ thống",
                    slug="tim-thong-tin",
                    summary="Tra cứu hồ sơ từ danh sách công khai.",
                    category="getting-started",
                    audiences=("PUBLIC",),
                    body_html="<p>Mở mục hồ sơ để tiếp tục.</p>",
                    sort_order=1,
                ),
            )
            for article in articles:
                row = await service.create_guide_article(
                    admin, article, request_id=f"create-{article.slug}"
                )
                await service.set_guide_article_status(
                    admin,
                    row.id,
                    CmsContentStatus.PUBLISHED,
                    request_id=f"publish-{article.slug}",
                )

            accented, total = await service.list_public_guide_articles(
                page=1, page_size=20, query="hồ sơ"
            )
            unaccented, unaccented_total = await service.list_public_guide_articles(
                page=1, page_size=20, query="HO SO"
            )
            assert total == unaccented_total == 2
            assert [row.slug for row in accented] == ["tao-ho-so", "tim-thong-tin"]
            assert [row.slug for row in unaccented] == ["tao-ho-so", "tim-thong-tin"]
            wallet_results, wallet_total = await service.list_public_guide_articles(
                page=1, page_size=20, query="Nạp tiền"
            )
            assert wallet_total == 0
            assert wallet_results == ()
        await engine.dispose()

    asyncio.run(exercise())


def test_guide_management_requires_super_admin(tmp_path: Path) -> None:
    async def exercise() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'cms-guide-auth.sqlite3').as_posix()}"
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            service = CmsService(session=session, audit=AuditService(session))
            with pytest.raises(CmsForbiddenError):
                await service.create_guide_article(
                    _principal("MODERATOR"),
                    CmsGuideArticleInput(
                        title="Private",
                        slug="private-guide",
                        summary="No access.",
                        category="operations",
                        audiences=("SUPER_ADMIN",),
                        body_html="<p>Private.</p>",
                        sort_order=1,
                    ),
                    request_id="guide-denied",
                )
        await engine.dispose()

    asyncio.run(exercise())


def test_feedback_is_deduplicated_without_storing_browser_token(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        database_path = (tmp_path / "cms-guide-feedback.sqlite3").as_posix()
        engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            service = CmsService(session=session, audit=AuditService(session))
            admin = _principal("SUPER_ADMIN")
            article = await service.create_guide_article(
                admin,
                CmsGuideArticleInput(
                    title="Tra cứu",
                    slug="tra-cuu",
                    summary="Tìm kết quả.",
                    category="verification",
                    audiences=("PUBLIC",),
                    body_html="<p>Tìm bằng mã.</p>",
                    sort_order=1,
                ),
                request_id="feedback-guide-create",
            )
            await service.set_guide_article_status(
                admin,
                article.id,
                CmsContentStatus.PUBLISHED,
                request_id="feedback-guide-publish",
            )
            browser_token = str(uuid4())
            await service.record_guide_feedback(
                "tra-cuu",
                helpful=False,
                comment="Bước tra cứu còn thiếu.",
                client_token=browser_token,
            )
            with pytest.raises(CmsGuideFeedbackConflictError):
                await service.record_guide_feedback(
                    "tra-cuu",
                    helpful=False,
                    comment="Lặp lại.",
                    client_token=browser_token,
                )
            feedback = await session.scalar(select(CmsGuideFeedback))
            assert feedback is not None
            assert (
                feedback.client_token_hash
                == hashlib.sha256(browser_token.encode("utf-8")).hexdigest()
            )
            assert browser_token not in feedback.client_token_hash
            assert feedback.comment == "Bước tra cứu còn thiếu."
        await engine.dispose()

    asyncio.run(exercise())
