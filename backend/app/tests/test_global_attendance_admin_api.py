import asyncio
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import httpx
import pytest

from app.api.v1 import hr as hr_api
from app.core.config import Settings
from app.core.health import HealthService
from app.db.session import get_session
from app.main import create_application
from app.modules.auth.dependencies import (
    get_csrf_protected_principal,
    get_current_principal,
)
from app.modules.auth.session_service import AuthPrincipal
from app.modules.hr.models import (
    AttendanceLocationEventType,
    AttendanceLocationExceptionStatus,
    AttendanceLocationOutcome,
    AttendanceStatus,
    AttendanceWorksiteStatus,
)
from app.modules.hr.schemas import (
    AdminAttendanceLocationExceptionData,
    AttendanceAssignmentData,
    AttendanceLocationEvidenceReviewData,
    AttendanceLocationExceptionData,
    AttendanceWorksiteData,
    AttendanceWorksitePolicyData,
)

NOW = datetime(2026, 9, 21, 8, 0, tzinfo=UTC)


class StubGlobalAttendanceAdminService:
    def __init__(self) -> None:
        self.worksite = AttendanceWorksiteData(
            id=uuid4(),
            code="NYC-HQ",
            name="New York HQ",
            status=AttendanceWorksiteStatus.ACTIVE,
            created_at=NOW,
            updated_at=NOW,
        )
        self.policy = AttendanceWorksitePolicyData(
            id=uuid4(),
            worksite_id=self.worksite.id,
            effective_from=date(2026, 9, 1),
            effective_to=None,
            timezone="America/New_York",
            latitude=Decimal("40.712800"),
            longitude=Decimal("-74.006000"),
            radius_meters=250,
            max_accuracy_meters=40,
            created_at=NOW,
            updated_at=NOW,
        )
        self.assignment = AttendanceAssignmentData(
            id=uuid4(),
            employee_id=uuid4(),
            employee_code="OPS-001",
            employee_name="Avery Patel",
            worksite_id=self.worksite.id,
            worksite_code=self.worksite.code,
            worksite_name=self.worksite.name,
            effective_from=date(2026, 9, 1),
            effective_to=None,
            schedule_code="MON_FRI_8H",
            holiday_calendar_code="US-NY",
            created_at=NOW,
            updated_at=NOW,
        )
        self.location_exception = AttendanceLocationExceptionData(
            id=uuid4(),
            attendance_id=uuid4(),
            location_evidence_id=uuid4(),
            status=AttendanceLocationExceptionStatus.APPROVED,
            requested_by_user_id=uuid4(),
            decision_note="Verified field assignment.",
            reviewed_by_user_id=uuid4(),
            reviewed_at=NOW,
            created_at=NOW,
            updated_at=NOW,
        )
        self.location_exception_review = AdminAttendanceLocationExceptionData(
            **self.location_exception.model_dump(by_alias=False),
            employee_id=self.assignment.employee_id,
            employee_code=self.assignment.employee_code,
            employee_name=self.assignment.employee_name,
            work_date=date(2026, 9, 21),
            attendance_status=AttendanceStatus.PENDING,
            evidence=AttendanceLocationEvidenceReviewData(
                id=self.location_exception.location_evidence_id,
                event_type=AttendanceLocationEventType.CHECK_IN,
                worksite_policy_id=self.policy.id,
                worksite_code=self.worksite.code,
                worksite_name=self.worksite.name,
                client_captured_at=NOW,
                received_at=NOW,
                latitude=Decimal("10.786900"),
                longitude=Decimal("106.700900"),
                accuracy_meters=Decimal("12.50"),
                distance_meters=Decimal("1111.95"),
                effective_timezone="Asia/Ho_Chi_Minh",
                permitted_radius_meters=100,
                max_accuracy_meters=25,
                outcome=AttendanceLocationOutcome.OUTSIDE_WORKSITE,
            ),
        )

    async def create_attendance_worksite(self, principal, payload, **kwargs):
        assert principal.roles == ("SUPER_ADMIN",)
        assert payload.code == "nyc-hq"
        return self.worksite

    async def create_attendance_worksite_policy(
        self, principal, worksite_id, payload, **kwargs
    ):
        assert principal.roles == ("SUPER_ADMIN",)
        assert worksite_id == self.worksite.id
        assert payload.timezone == "America/New_York"
        return self.policy

    async def create_attendance_assignment(self, principal, payload, **kwargs):
        assert principal.roles == ("SUPER_ADMIN",)
        assert payload.employee_id == self.assignment.employee_id
        return self.assignment

    async def decide_attendance_location_exception(
        self, principal, exception_id, payload, **kwargs
    ):
        assert principal.roles == ("SUPER_ADMIN",)
        assert exception_id == self.location_exception.id
        assert payload.status == AttendanceLocationExceptionStatus.APPROVED
        return self.location_exception

    async def list_attendance_location_exceptions(self, principal, **kwargs):
        assert principal.roles == ("SUPER_ADMIN",)
        assert kwargs["exception_status"] == AttendanceLocationExceptionStatus.PENDING
        return (self.location_exception_review,), 1

    async def list_admin_attendance_location_evidence(self, principal, attendance_id):
        assert principal.roles == ("SUPER_ADMIN",)
        assert attendance_id == self.location_exception.attendance_id
        return (self.location_exception_review.evidence,)


async def _request(
    monkeypatch: pytest.MonkeyPatch,
    service: StubGlobalAttendanceAdminService,
    method: str,
    path: str,
    *,
    json: dict[str, object],
) -> httpx.Response:
    app = create_application(
        settings=Settings.model_validate({"app_env": "local"}),
        health_service=HealthService({}),
    )
    principal = AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="admin@example.com",
        roles=("SUPER_ADMIN",),
        permissions=(),
    )
    monkeypatch.setattr(hr_api, "HrService", lambda _session: service)
    app.dependency_overrides[get_current_principal] = lambda: principal
    app.dependency_overrides[get_csrf_protected_principal] = lambda: principal
    app.dependency_overrides[get_session] = lambda: object()
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.request(method, path, json=json)


def test_global_attendance_admin_create_contracts_are_camel_case(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def exercise() -> None:
        service = StubGlobalAttendanceAdminService()
        worksite = await _request(
            monkeypatch,
            service,
            "POST",
            "/api/v1/admin/hr/attendance-worksites",
            json={"code": "nyc-hq", "name": "New York HQ"},
        )
        policy = await _request(
            monkeypatch,
            service,
            "POST",
            f"/api/v1/admin/hr/attendance-worksites/{service.worksite.id}/policies",
            json={
                "effectiveFrom": "2026-09-01",
                "timezone": "America/New_York",
                "latitude": "40.712800",
                "longitude": "-74.006000",
                "radiusMeters": 250,
                "maxAccuracyMeters": 40,
            },
        )
        assignment = await _request(
            monkeypatch,
            service,
            "POST",
            "/api/v1/admin/hr/attendance-assignments",
            json={
                "employeeId": str(service.assignment.employee_id),
                "worksiteId": str(service.worksite.id),
                "effectiveFrom": "2026-09-01",
                "scheduleCode": "MON_FRI_8H",
                "holidayCalendarCode": "US-NY",
            },
        )

        assert worksite.status_code == 201
        assert worksite.json()["data"]["code"] == "NYC-HQ"
        assert policy.status_code == 201
        assert policy.json()["data"]["maxAccuracyMeters"] == 40
        assert assignment.status_code == 201
        assert assignment.json()["data"]["employeeName"] == "Avery Patel"

    asyncio.run(exercise())


def test_global_attendance_admin_rejects_invalid_iana_timezone_at_api_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def exercise() -> None:
        service = StubGlobalAttendanceAdminService()
        response = await _request(
            monkeypatch,
            service,
            "POST",
            f"/api/v1/admin/hr/attendance-worksites/{service.worksite.id}/policies",
            json={
                "effectiveFrom": "2026-09-01",
                "timezone": "Invalid/Timezone",
                "latitude": "40.712800",
                "longitude": "-74.006000",
                "radiusMeters": 250,
                "maxAccuracyMeters": 40,
            },
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"

    asyncio.run(exercise())


def test_global_attendance_exception_decision_is_private_and_camel_case(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def exercise() -> None:
        service = StubGlobalAttendanceAdminService()
        response = await _request(
            monkeypatch,
            service,
            "PATCH",
            f"/api/v1/admin/hr/attendance-location-exceptions/{service.location_exception.id}",
            json={
                "status": "APPROVED",
                "decisionNote": "Verified field assignment.",
            },
        )
        invalid = await _request(
            monkeypatch,
            service,
            "PATCH",
            f"/api/v1/admin/hr/attendance-location-exceptions/{service.location_exception.id}",
            json={"status": "PENDING", "decisionNote": "Still pending."},
        )

        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert response.json()["data"]["decisionNote"] == "Verified field assignment."
        assert "latitude" not in response.text
        assert "longitude" not in response.text
        assert invalid.status_code == 422
        assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"

    asyncio.run(exercise())


def test_global_attendance_exception_evidence_is_private_to_admin_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def exercise() -> None:
        service = StubGlobalAttendanceAdminService()
        response = await _request(
            monkeypatch,
            service,
            "GET",
            "/api/v1/admin/hr/attendance-location-exceptions?status=PENDING",
            json={},
        )

        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert response.json()["data"][0]["evidence"]["latitude"] == "10.786900"
        assert response.json()["data"][0]["employeeName"] == "Avery Patel"

    asyncio.run(exercise())


def test_global_attendance_admin_can_read_exact_evidence_without_caching(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def exercise() -> None:
        service = StubGlobalAttendanceAdminService()
        response = await _request(
            monkeypatch,
            service,
            "GET",
            f"/api/v1/admin/hr/attendance/{service.location_exception.attendance_id}/location-evidence",
            json={},
        )

        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert response.json()["data"][0]["latitude"] == "10.786900"
        assert response.json()["data"][0]["worksiteCode"] == "NYC-HQ"

    asyncio.run(exercise())
