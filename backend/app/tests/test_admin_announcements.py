import asyncio
from datetime import date
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1.admin_notifications import _require_super_admin
from app.core.config import Settings
from app.core.errors import DomainError
from app.core.health import HealthService
from app.db.base import Base
from app.db.session import get_session
from app.main import create_application
from app.modules.auth.dependencies import (
    get_csrf_protected_principal,
    get_current_principal,
)
from app.modules.auth.models import User, UserStatus
from app.modules.auth.session_service import AuthPrincipal
from app.modules.hr.models import Department, Employee, EmploymentStatus
from app.modules.notifications.admin_service import (
    AdminAnnouncementService,
    AnnouncementAudience,
)
from app.modules.notifications.models import Notification


def test_announcement_audiences_and_retry() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        employee_user, regular_user, inactive_user = [
            User(id=uuid4(), email=f"person{index}@example.com", status=status)
            for index, status in enumerate(
                (UserStatus.ACTIVE, UserStatus.ACTIVE, UserStatus.SUSPENDED)
            )
        ]
        async with sessions.begin() as session:
            session.add_all((employee_user, regular_user, inactive_user))
            department = Department(code="OPS", name="Operations")
            session.add(department)
            await session.flush()
            session.add(
                Employee(
                    employee_code="NV-ANN",
                    user_id=employee_user.id,
                    full_name="Reviewer",
                    email=employee_user.email,
                    department_id=department.id,
                    position="Reviewer",
                    employment_status=EmploymentStatus.ACTIVE,
                    join_date=date(2026, 10, 1),
                )
            )

        async with sessions() as session:
            service = AdminAnnouncementService(session)
            assert await service.preview(AnnouncementAudience.ALL) == 2
            assert await service.preview(AnnouncementAudience.EMPLOYEES) == 1
            assert await service.preview(AnnouncementAudience.USERS) == 1
            assert (
                await service.preview(AnnouncementAudience.INDIVIDUAL, regular_user.id)
                == 1
            )
            assert (
                await service.preview(AnnouncementAudience.INDIVIDUAL, inactive_user.id)
                == 0
            )
            campaign_id = uuid4()
            result = await service.send(
                audience=AnnouncementAudience.ALL,
                recipient_user_id=None,
                campaign_id=campaign_id,
                title="Thông báo kiểm thử",
                body="Nội dung thông báo kiểm thử.",
                actor_user_id=regular_user.id,
                request_id="test-announcement",
                user_agent=None,
            )
            repeated = await service.send(
                audience=AnnouncementAudience.ALL,
                recipient_user_id=None,
                campaign_id=campaign_id,
                title="Thông báo kiểm thử",
                body="Nội dung thông báo kiểm thử.",
                actor_user_id=regular_user.id,
                request_id="test-announcement",
                user_agent=None,
            )
            assert result == repeated == 2
            assert await session.scalar(select(func.count(Notification.id))) == 2
            await session.rollback()
            for audience, expected_user_id in (
                (AnnouncementAudience.EMPLOYEES, employee_user.id),
                (AnnouncementAudience.USERS, regular_user.id),
            ):
                targeted_campaign_id = uuid4()
                count = await service.send(
                    audience=audience,
                    recipient_user_id=None,
                    campaign_id=targeted_campaign_id,
                    title="Audience check",
                    body="Check the matching accounts.",
                    actor_user_id=regular_user.id,
                    request_id="test-announcement-audience",
                    user_agent=None,
                )
                actual_recipient_ids = set(
                    await session.scalars(
                        select(Notification.user_id).where(
                            Notification.source_event_id == targeted_campaign_id
                        )
                    )
                )
                assert count == 1
                assert actual_recipient_ids == {expected_user_id}
                await session.rollback()
        await engine.dispose()

    asyncio.run(exercise())


def test_only_super_admin_can_compose_announcements() -> None:
    principal = AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="employee@example.com",
        roles=("MODERATOR",),
    )
    with pytest.raises(DomainError) as error:
        _require_super_admin(principal)
    assert error.value.status_code == 403


def test_announcement_api_delivers_to_notification_center() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        recipient = User(
            id=uuid4(), email="recipient@example.com", status=UserStatus.ACTIVE
        )
        admin = User(id=uuid4(), email="admin@example.com", status=UserStatus.ACTIVE)
        async with sessions.begin() as session:
            session.add_all((recipient, admin))
        admin_principal = AuthPrincipal(
            user_id=admin.id,
            session_id=uuid4(),
            email=admin.email,
            roles=("SUPER_ADMIN",),
        )
        recipient_principal = AuthPrincipal(
            user_id=recipient.id,
            session_id=uuid4(),
            email=recipient.email,
            roles=("USER",),
        )
        app = create_application(
            settings=Settings.model_validate({"app_env": "local"}),
            health_service=HealthService({}),
        )
        async with sessions() as session:
            app.dependency_overrides[get_session] = lambda: session
            app.dependency_overrides[get_csrf_protected_principal] = lambda: (
                admin_principal
            )
            app.dependency_overrides[get_current_principal] = lambda: (
                recipient_principal
            )
            transport = httpx.ASGITransport(app=app)
            async with app.router.lifespan_context(app):
                async with httpx.AsyncClient(
                    transport=transport, base_url="http://testserver"
                ) as client:
                    preview = await client.post(
                        "/api/v1/admin/notifications/preview",
                        json={
                            "audience": "INDIVIDUAL",
                            "recipientUserId": str(recipient.id),
                        },
                    )
                    assert preview.status_code == 200, preview.text
                    assert preview.json()["data"]["recipientCount"] == 1
                    sent = await client.post(
                        "/api/v1/admin/notifications",
                        json={
                            "audience": "INDIVIDUAL",
                            "recipientUserId": str(recipient.id),
                            "campaignId": str(uuid4()),
                            "title": "Lịch mới",
                            "body": "Vui lòng kiểm tra lịch tuần tới.",
                        },
                    )
                    assert sent.status_code == 200, sent.text
                    notifications = await client.get("/api/v1/notifications")
                    assert notifications.status_code == 200, notifications.text
                    assert notifications.json()["data"][0]["title"] == "Lịch mới"
            app.dependency_overrides.clear()
        await engine.dispose()

    asyncio.run(exercise())
