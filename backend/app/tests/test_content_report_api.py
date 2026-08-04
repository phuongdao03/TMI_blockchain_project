from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.main import create_application
from app.modules.auth.dependencies import (
    get_csrf_protected_principal,
    get_current_principal,
    get_optional_csrf_principal,
)
from app.modules.auth.session_service import AuthPrincipal
from app.modules.public.dependencies import (
    enforce_public_rate_limit,
    enforce_public_report_rate_limit,
)
from app.modules.public.models import (
    ContentReport,
    ContentReportReason,
    ContentReportStatus,
)
from app.modules.public.publication_dependencies import (
    get_content_report_service,
    get_publication_service,
)
from app.modules.public.report_repository import ContentReportRow
from app.modules.public.report_service import ContentReportInput

NOW = datetime(2026, 8, 1, tzinfo=UTC)


class StubContentReportService:
    def __init__(self) -> None:
        self.work_id = uuid4()
        self.report = ContentReport(
            id=uuid4(),
            public_work_id=self.work_id,
            reporter_user_id=None,
            reporter_email_hash="a" * 64,
            reporter_email_encrypted=b"encrypted-contact",
            reason=ContentReportReason.COPYRIGHT,
            description="Public plain-text report.",
            dedup_key="b" * 64,
            reporter_ip_hash="c" * 64,
            status=ContentReportStatus.OPEN,
            created_at=NOW,
            updated_at=NOW,
        )
        self.row = ContentReportRow(
            self.report,
            "Reported work",
            "reported-work",
            7,
        )
        self.submitted: ContentReportInput | None = None
        self.transitions: list[ContentReportStatus] = []

    async def submit(
        self,
        work_id: UUID,
        payload: ContentReportInput,
        **_context: object,
    ) -> ContentReport:
        assert work_id == self.work_id
        self.submitted = payload
        return self.report

    async def list_admin(
        self, _principal: object, **_filters: object
    ) -> tuple[tuple[ContentReportRow, ...], int]:
        return (self.row,), 1

    async def get_admin(self, _principal: object, report_id: UUID) -> ContentReportRow:
        assert report_id == self.report.id
        return self.row

    async def transition(
        self,
        _principal: object,
        report_id: UUID,
        *,
        status: ContentReportStatus,
        **_context: object,
    ) -> ContentReportRow:
        assert report_id == self.report.id
        self.transitions.append(status)
        self.report.status = status
        return self.row


class StubPublicationService:
    def __init__(self) -> None:
        self.suspended: tuple[UUID, int, str] | None = None

    async def suspend(
        self,
        _principal: object,
        work_id: UUID,
        *,
        expected_version: int,
        reason: str,
        **_context: object,
    ) -> object:
        self.suspended = (work_id, expected_version, reason)
        return object()


def _admin() -> AuthPrincipal:
    return AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="content-admin@example.test",
        roles=("CONTENT_ADMIN",),
    )


def test_public_and_admin_content_report_contracts() -> None:
    reports = StubContentReportService()
    publication = StubPublicationService()
    app = create_application()
    app.dependency_overrides[get_content_report_service] = lambda: reports
    app.dependency_overrides[get_publication_service] = lambda: publication
    app.dependency_overrides[get_optional_csrf_principal] = lambda: None
    app.dependency_overrides[get_current_principal] = _admin
    app.dependency_overrides[get_csrf_protected_principal] = _admin
    app.dependency_overrides[enforce_public_rate_limit] = lambda: None
    app.dependency_overrides[enforce_public_report_rate_limit] = lambda: None
    try:
        with TestClient(app) as client:
            created = client.post(
                f"/api/v1/public/works/{reports.work_id}/reports",
                json={
                    "reason": "COPYRIGHT",
                    "description": "Public plain-text report.",
                    "reporterEmail": "reporter@example.com",
                },
            )
            assert created.status_code == 201, created.text
            assert created.json()["data"] == {
                "id": str(reports.report.id),
                "status": "OPEN",
            }
            assert reports.submitted is not None
            assert reports.submitted.reporter_email == "reporter@example.com"

            listed = client.get("/api/v1/admin/content-reports")
            assert listed.status_code == 200
            data = listed.json()["data"][0]
            assert data["workVersion"] == 7
            assert data["reporterType"] == "ANONYMOUS"
            assert data["hasContactEmail"] is True
            serialized = str(data)
            assert "reporter@example.com" not in serialized
            assert "reporterEmailHash" not in serialized
            assert "reporterUserId" not in serialized

            claimed = client.patch(
                f"/api/v1/admin/content-reports/{reports.report.id}",
                json={"status": "UNDER_REVIEW", "resolutionNote": None},
            )
            assert claimed.status_code == 200
            suspended = client.post(
                f"/api/v1/admin/content-reports/{reports.report.id}/suspend",
                json={"expectedWorkVersion": 7, "reason": "Legal hold"},
            )
            assert suspended.status_code == 200
            assert publication.suspended == (reports.work_id, 7, "Legal hold")
            assert reports.transitions[-1] is ContentReportStatus.SUSPENDED
    finally:
        app.dependency_overrides.clear()
