import asyncio
from datetime import UTC, date, datetime
from uuid import uuid4

import httpx
import pytest

from app.api.v1 import hr as hr_api
from app.core.health import HealthService
from app.db.session import get_session
from app.main import create_application
from app.modules.auth.dependencies import get_current_principal
from app.modules.auth.session_service import AuthPrincipal
from app.modules.hr.models import AttendanceStatus
from app.modules.hr.schemas import ModeratorHrDashboardSummaryData


class StubHrDashboardService:
    async def moderator_summary(
        self, principal: AuthPrincipal
    ) -> ModeratorHrDashboardSummaryData:
        return ModeratorHrDashboardSummaryData(
            profile_linked=True,
            work_date=date(2026, 9, 23),
            timezone="Asia/Ho_Chi_Minh",
            attendance_status=AttendanceStatus.PENDING,
            check_in_at=datetime(2026, 9, 23, 1, tzinfo=UTC),
            check_out_at=None,
            leave_pending_count=2,
            overtime_pending_count=1,
            updated_at=datetime(2026, 9, 23, 8, tzinfo=UTC),
        )


def _principal() -> AuthPrincipal:
    return AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="moderator@example.com",
        roles=("MODERATOR",),
        permissions=(),
    )


def test_moderator_dashboard_summary_uses_private_personal_contract(
    monkeypatch: object,
) -> None:
    async def exercise() -> None:
        app = create_application(health_service=HealthService({}))
        principal = _principal()
        monkeypatch.setattr(
            hr_api, "HrDashboardService", lambda _session: StubHrDashboardService()
        )
        app.dependency_overrides[get_current_principal] = lambda: principal
        app.dependency_overrides[get_session] = lambda: object()
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://testserver"
            ) as client:
                response = await client.get("/api/v1/me/hr/dashboard-summary")

        assert response.status_code == 200, response.text
        assert response.headers["cache-control"] == "no-store"
        data = response.json()["data"]
        assert data == {
            "profileLinked": True,
            "workDate": "2026-09-23",
            "timezone": "Asia/Ho_Chi_Minh",
            "attendanceStatus": "PENDING",
            "checkInAt": "2026-09-23T01:00:00Z",
            "checkOutAt": None,
            "leavePendingCount": 2,
            "overtimePendingCount": 1,
            "updatedAt": "2026-09-23T08:00:00Z",
        }
        assert not {
            "employeeId",
            "employeeName",
            "latitude",
            "longitude",
            "reason",
            "netPay",
        } & set(data)
        app.dependency_overrides.clear()

    asyncio.run(exercise())


@pytest.mark.parametrize("role", ["VIEWER", "USER", "SUPER_ADMIN"])
def test_personal_dashboard_denies_other_roles_before_database_access(
    role: str,
) -> None:
    async def exercise() -> None:
        app = create_application(health_service=HealthService({}))
        principal = AuthPrincipal(
            user_id=uuid4(),
            session_id=uuid4(),
            email="other@example.com",
            roles=(role,),
            permissions=("hr.attendance.self",),
        )
        app.dependency_overrides[get_current_principal] = lambda: principal
        app.dependency_overrides[get_session] = lambda: object()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            response = await client.get("/api/v1/me/hr/dashboard-summary")
        assert response.status_code == 403
        assert "HR_MODERATOR_DASHBOARD_FORBIDDEN" in response.text
        app.dependency_overrides.clear()

    asyncio.run(exercise())
