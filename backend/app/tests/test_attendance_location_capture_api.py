import asyncio
from datetime import UTC, date, datetime
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
    AttendanceLocationOutcome,
    AttendanceStatus,
)
from app.modules.hr.schemas import (
    AttendanceData,
    AttendanceLocationEvidenceReviewData,
    AttendanceWorkdayContextData,
)

NOW = datetime(2026, 9, 21, 8, 0, tzinfo=UTC)


class StubAttendanceLocationService:
    def __init__(self) -> None:
        self.check_in_payload = None
        self.check_out_payload = None
        self.attendance = AttendanceData(
            id=uuid4(),
            employee_id=uuid4(),
            employee_name="Avery Patel",
            work_date=date(2026, 9, 21),
            check_in_at=NOW,
            check_out_at=None,
            status=AttendanceStatus.PRESENT,
            late_minutes=0,
            early_leave_minutes=0,
            note=None,
            created_at=NOW,
            updated_at=NOW,
        )
        self.evidence = AttendanceLocationEvidenceReviewData(
            id=uuid4(),
            event_type=AttendanceLocationEventType.CHECK_IN,
            worksite_policy_id=uuid4(),
            worksite_code="SGN-HQ",
            worksite_name="Ho Chi Minh City HQ",
            client_captured_at=NOW,
            received_at=NOW,
            latitude="10.776900",
            longitude="106.700900",
            accuracy_meters="18.50",
            distance_meters="0.00",
            effective_timezone="Asia/Ho_Chi_Minh",
            permitted_radius_meters=100,
            max_accuracy_meters=25,
            outcome=AttendanceLocationOutcome.ACCEPTED,
        )
        self.workday_context = AttendanceWorkdayContextData(
            work_date=date(2026, 9, 21), timezone="Asia/Ho_Chi_Minh"
        )

    async def check_in(self, principal, payload, **kwargs):
        assert principal.roles == ("MODERATOR",)
        self.check_in_payload = payload
        return self.attendance

    async def check_out(self, principal, payload, **kwargs):
        assert principal.roles == ("MODERATOR",)
        self.check_out_payload = payload
        return self.attendance

    async def list_personal_attendance_location_evidence(
        self, principal, attendance_id
    ):
        assert principal.roles == ("MODERATOR",)
        assert attendance_id == self.attendance.id
        return (self.evidence,)

    async def get_personal_attendance_workday_context(self, principal):
        assert principal.roles == ("MODERATOR",)
        return self.workday_context


async def _request(
    monkeypatch: pytest.MonkeyPatch,
    service: StubAttendanceLocationService,
    path: str,
    payload: dict[str, object],
    method: str = "POST",
) -> httpx.Response:
    app = create_application(
        settings=Settings.model_validate({"app_env": "local"}),
        health_service=HealthService({}),
    )
    principal = AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="moderator@example.com",
        roles=("MODERATOR",),
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
            return await client.request(method, path, json=payload)


def test_attendance_location_payload_is_required_and_not_reflected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def exercise() -> None:
        service = StubAttendanceLocationService()
        payload = {
            "latitude": "10.776900",
            "longitude": "106.700900",
            "accuracyMeters": "18.50",
            "clientCapturedAt": "2026-09-21T02:30:00Z",
        }
        check_in = await _request(
            monkeypatch,
            service,
            "/api/v1/me/hr/attendance/check-in",
            {**payload, "note": "Field review"},
        )
        check_out = await _request(
            monkeypatch,
            service,
            "/api/v1/me/hr/attendance/check-out",
            payload,
        )
        invalid = await _request(
            monkeypatch,
            service,
            "/api/v1/me/hr/attendance/check-in",
            {"latitude": "10.776900", "longitude": "106.700900"},
        )
        untrusted_geofence = await _request(
            monkeypatch,
            service,
            "/api/v1/me/hr/attendance/check-out",
            {**payload, "insideRadius": True},
        )

        assert check_in.status_code == 201
        assert check_out.status_code == 200
        assert check_in.headers["cache-control"] == "no-store"
        assert check_out.headers["cache-control"] == "no-store"
        assert service.check_in_payload.accuracy_meters == 18.5
        assert service.check_out_payload.client_captured_at == datetime(
            2026, 9, 21, 2, 30, tzinfo=UTC
        )
        assert "latitude" not in check_in.json()["data"]
        assert "longitude" not in check_out.json()["data"]
        assert invalid.status_code == 422
        assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"
        assert "10.776900" not in invalid.text
        assert untrusted_geofence.status_code == 422

    asyncio.run(exercise())


def test_employee_can_open_only_their_private_location_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def exercise() -> None:
        service = StubAttendanceLocationService()
        response = await _request(
            monkeypatch,
            service,
            f"/api/v1/me/hr/attendance/{service.attendance.id}/location-evidence",
            {},
            method="GET",
        )

        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert response.json()["data"][0]["worksiteName"] == "Ho Chi Minh City HQ"
        assert response.json()["data"][0]["latitude"] == "10.776900"

    asyncio.run(exercise())


def test_attendance_workday_context_is_server_owned_and_coordinate_free(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def exercise() -> None:
        service = StubAttendanceLocationService()
        response = await _request(
            monkeypatch,
            service,
            "/api/v1/me/hr/attendance/workday-context",
            {},
            method="GET",
        )

        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert response.json()["data"] == {
            "workDate": "2026-09-21",
            "timezone": "Asia/Ho_Chi_Minh",
        }
        assert "latitude" not in response.text
        assert "longitude" not in response.text

    asyncio.run(exercise())
