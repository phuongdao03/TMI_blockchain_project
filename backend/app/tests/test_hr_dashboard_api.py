import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import httpx

from app.api.v1 import hr as hr_api
from app.core.health import HealthService
from app.db.session import get_session
from app.main import create_application
from app.modules.auth.dependencies import get_current_principal
from app.modules.auth.session_service import AuthPrincipal
from app.modules.hr.schemas import HrDashboardSummaryData


class StubHrDashboardService:
    async def summary(self, principal: AuthPrincipal) -> HrDashboardSummaryData:
        return HrDashboardSummaryData(
            active_employee_count=4,
            attendance_pending_count=2,
            location_exception_pending_count=1,
            leave_pending_count=3,
            overtime_pending_count=5,
            payroll_draft_count=1,
            updated_at=datetime(2026, 9, 23, 8, tzinfo=UTC),
        )


def _principal() -> AuthPrincipal:
    return AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="superadmin@example.com",
        roles=("SUPER_ADMIN",),
        permissions=(),
    )


def test_dashboard_summary_uses_private_aggregate_contract(monkeypatch: object) -> None:
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
                response = await client.get("/api/v1/admin/hr/dashboard-summary")

        assert response.status_code == 200, response.text
        assert response.headers["cache-control"] == "no-store"
        data = response.json()["data"]
        assert data == {
            "activeEmployeeCount": 4,
            "attendancePendingCount": 2,
            "locationExceptionPendingCount": 1,
            "leavePendingCount": 3,
            "overtimePendingCount": 5,
            "payrollDraftCount": 1,
            "updatedAt": "2026-09-23T08:00:00Z",
        }
        assert not {"latitude", "longitude", "reason", "employeeName", "netPay"} & set(
            data
        )
        app.dependency_overrides.clear()

    asyncio.run(exercise())
