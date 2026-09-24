import asyncio
from datetime import UTC, date, datetime
from uuid import uuid4

import httpx

from app.api.v1 import hr as hr_api
from app.core.health import HealthService
from app.db.session import get_session
from app.main import create_application
from app.modules.auth.dependencies import (
    get_csrf_protected_principal,
    get_current_principal,
)
from app.modules.auth.session_service import AuthPrincipal
from app.modules.hr.models import PayrollPeriodStatus
from app.modules.hr.schemas import PayrollPeriodData


class StubPayrollService:
    def __init__(self) -> None:
        self.create_payload = None

    async def create_period(
        self,
        principal: AuthPrincipal,
        payload: object,
        **_: object,
    ) -> PayrollPeriodData:
        self.create_payload = payload
        return PayrollPeriodData(
            id=uuid4(),
            worksite_id=uuid4(),
            period_month=date(2026, 9, 1),
            currency="VND",
            standard_workdays=22,
            status=PayrollPeriodStatus.DRAFT,
            calculated_at=None,
            confirmed_at=None,
            confirmed_by_user_id=None,
            paid_at=None,
            paid_by_user_id=None,
            created_at=datetime(2026, 9, 1, tzinfo=UTC),
            updated_at=datetime(2026, 9, 1, tzinfo=UTC),
        )


def _principal() -> AuthPrincipal:
    return AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="superadmin@example.com",
        roles=("SUPER_ADMIN",),
        permissions=(),
    )


def test_create_payroll_period_uses_csrf_contract_and_no_store_response(
    monkeypatch: object,
) -> None:
    async def exercise() -> None:
        service = StubPayrollService()
        principal = _principal()
        app = create_application(health_service=HealthService({}))
        monkeypatch.setattr(hr_api, "PayrollService", lambda _session: service)
        app.dependency_overrides[get_current_principal] = lambda: principal
        app.dependency_overrides[get_csrf_protected_principal] = lambda: principal
        app.dependency_overrides[get_session] = lambda: object()
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://testserver"
            ) as client:
                response = await client.post(
                    "/api/v1/admin/hr/payroll-periods",
                    json={
                        "worksiteId": str(uuid4()),
                        "periodMonth": "2026-09-01",
                        "standardWorkdays": 22,
                    },
                )
        assert response.status_code == 201, response.text
        assert response.headers["cache-control"] == "no-store"
        assert response.json()["data"]["currency"] == "VND"
        assert service.create_payload is not None
        app.dependency_overrides.clear()

    asyncio.run(exercise())
