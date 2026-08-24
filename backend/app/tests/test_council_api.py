import asyncio
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

import httpx

from app.core.config import Settings
from app.core.health import HealthService
from app.main import create_application
from app.modules.auth.dependencies import (
    get_csrf_protected_principal,
    get_current_principal,
)
from app.modules.auth.session_service import AuthPrincipal
from app.modules.council.dependencies import get_council_service
from app.modules.council.models import (
    CouncilCaseDecision,
    CouncilSessionStatus,
    CouncilVoteChoice,
)
from app.modules.council.types import (
    CouncilCaseDetailView,
    CouncilCaseResultView,
    CouncilCaseView,
    CouncilConflictView,
    CouncilMemberView,
    CouncilMinutesView,
    CouncilSessionDetailView,
    CouncilSessionListItemView,
    CouncilSessionPage,
    CouncilSessionView,
    CouncilVoteView,
)

NOW = datetime(2026, 8, 3, 8, 0, tzinfo=UTC)


class StubCouncilService:
    def __init__(self) -> None:
        self.member_id = uuid4()
        self.session = CouncilSessionView(
            id=uuid4(),
            code="HD-2026-API",
            title="API council",
            scheduled_at=NOW,
            status=CouncilSessionStatus.DRAFT,
            quorum_required=1,
            opened_at=None,
            closed_at=None,
            minutes_hash=None,
            member_count=1,
            attendance_count=0,
        )
        self.case = CouncilCaseView(
            id=uuid4(),
            session_id=self.session.id,
            dossier_id=uuid4(),
            dossier_version_id=uuid4(),
            dossier_code="HS-2026-API",
            dossier_title="API dossier",
            version_no=1,
            decision=None,
        )
        self.conflict: CouncilConflictView | None = None
        self.vote: CouncilVoteView | None = None

    async def create_session(
        self,
        principal: AuthPrincipal,
        *,
        code: str,
        title: str,
        scheduled_at: datetime,
        quorum_required: int,
        member_user_ids: tuple[UUID, ...],
    ) -> CouncilSessionView:
        assert code == "HD-2026-API"
        assert title == "API council"
        assert scheduled_at == NOW
        assert quorum_required == 1
        assert member_user_ids == (self.member_id,)
        return self.session

    async def add_case(
        self,
        principal: AuthPrincipal,
        session_id: UUID,
        dossier_id: UUID,
    ) -> CouncilCaseView:
        assert session_id == self.session.id
        assert dossier_id == self.case.dossier_id
        return self.case

    async def confirm_attendance(
        self,
        principal: AuthPrincipal,
        session_id: UUID,
    ) -> CouncilMemberView:
        return CouncilMemberView(
            id=uuid4(),
            session_id=session_id,
            member_user_id=principal.user_id,
            attendance_confirmed_at=NOW,
        )

    async def open_session(
        self,
        principal: AuthPrincipal,
        session_id: UUID,
    ) -> CouncilSessionView:
        self.session = replace(
            self.session,
            status=CouncilSessionStatus.OPEN,
            opened_at=NOW,
        )
        return self.session

    async def declare_conflict(
        self,
        principal: AuthPrincipal,
        case_id: UUID,
        *,
        has_conflict: bool,
        reason: str | None,
    ) -> CouncilConflictView:
        assert case_id == self.case.id
        self.conflict = CouncilConflictView(
            id=uuid4(),
            case_id=case_id,
            member_user_id=principal.user_id,
            has_conflict=has_conflict,
            reason=reason,
            declared_at=NOW,
        )
        return self.conflict

    async def cast_vote(
        self,
        principal: AuthPrincipal,
        case_id: UUID,
        *,
        choice: CouncilVoteChoice,
        reason: str,
    ) -> CouncilVoteView:
        self.vote = CouncilVoteView(
            id=uuid4(),
            case_id=case_id,
            member_user_id=principal.user_id,
            choice=choice,
            reason=reason,
            voted_at=NOW,
        )
        return self.vote

    async def close_session(
        self,
        principal: AuthPrincipal,
        session_id: UUID,
    ) -> CouncilSessionView:
        self.session = CouncilSessionView(
            id=self.session.id,
            code=self.session.code,
            title=self.session.title,
            scheduled_at=self.session.scheduled_at,
            status=CouncilSessionStatus.CLOSED,
            quorum_required=1,
            opened_at=NOW,
            closed_at=NOW,
            minutes_hash="c" * 64,
            member_count=1,
            attendance_count=1,
        )
        return self.session

    async def list_sessions(
        self,
        principal: AuthPrincipal,
        *,
        status: CouncilSessionStatus | None,
        page: int,
        page_size: int,
    ) -> CouncilSessionPage:
        assert status is CouncilSessionStatus.DRAFT
        assert (page, page_size) == (2, 5)
        return CouncilSessionPage(
            items=(
                CouncilSessionListItemView(
                    session=self.session,
                    my_attendance_confirmed_at=NOW,
                ),
            ),
            total=6,
        )

    async def get_session(
        self,
        principal: AuthPrincipal,
        session_id: UUID,
    ) -> CouncilSessionDetailView:
        assert session_id == self.session.id
        return CouncilSessionDetailView(
            session=self.session,
            my_attendance_confirmed_at=NOW,
            cases=(
                CouncilCaseDetailView(
                    case=self.case,
                    my_conflict=self.conflict,
                    my_vote=self.vote,
                    result=None,
                ),
            ),
        )

    async def get_minutes(
        self,
        principal: AuthPrincipal,
        session_id: UUID,
    ) -> CouncilMinutesView:
        return CouncilMinutesView(
            session_id=session_id,
            session_code=self.session.code,
            closed_at=NOW,
            quorum_required=1,
            minutes_hash="c" * 64,
            cases=(
                CouncilCaseResultView(
                    case_id=self.case.id,
                    dossier_id=self.case.dossier_id,
                    dossier_version_id=self.case.dossier_version_id,
                    decision=CouncilCaseDecision.APPROVE,
                    quorum_met=True,
                    valid_vote_count=1,
                    vote_counts={
                        choice: int(choice is CouncilVoteChoice.APPROVE)
                        for choice in CouncilVoteChoice
                    },
                ),
            ),
        )


def _principal() -> AuthPrincipal:
    return AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="member@tmigroup.vn",
        roles=("SUPER_ADMIN",),
    )


async def _request(
    service: StubCouncilService,
    method: str,
    path: str,
    *,
    json: dict[str, object] | None = None,
) -> httpx.Response:
    principal = _principal()
    app = create_application(
        settings=Settings.model_validate({"app_env": "local"}),
        health_service=HealthService({}),
    )
    app.dependency_overrides[get_council_service] = lambda: service
    app.dependency_overrides[get_current_principal] = lambda: principal
    app.dependency_overrides[get_csrf_protected_principal] = lambda: principal
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.request(method, path, json=json)


def test_council_administration_and_read_api_contracts() -> None:
    async def exercise() -> None:
        service = StubCouncilService()
        created = await _request(
            service,
            "POST",
            "/api/v1/admin/council/sessions",
            json={
                "code": service.session.code,
                "title": service.session.title,
                "scheduledAt": NOW.isoformat(),
                "quorumRequired": 1,
                "memberUserIds": [str(service.member_id)],
            },
        )
        added = await _request(
            service,
            "POST",
            f"/api/v1/admin/council/sessions/{service.session.id}/cases",
            json={"dossierId": str(service.case.dossier_id)},
        )
        listed = await _request(
            service,
            "GET",
            "/api/v1/council/sessions?status=DRAFT&page=2&pageSize=5",
        )
        detail = await _request(
            service,
            "GET",
            f"/api/v1/council/sessions/{service.session.id}",
        )

        assert created.status_code == 201
        assert created.json()["data"]["memberCount"] == 1
        assert added.status_code == 201
        assert added.json()["data"]["dossierCode"] == "HS-2026-API"
        assert listed.status_code == 200
        assert listed.json()["meta"]["total"] == 6
        assert listed.json()["data"][0]["myAttendanceConfirmedAt"] is not None
        assert detail.status_code == 200
        assert detail.json()["data"]["cases"][0]["case"]["versionNo"] == 1

    asyncio.run(exercise())


def test_council_attendance_conflict_vote_close_and_minutes_contracts() -> None:
    async def exercise() -> None:
        service = StubCouncilService()
        attended = await _request(
            service,
            "POST",
            f"/api/v1/council/sessions/{service.session.id}/attendance",
        )
        opened = await _request(
            service,
            "POST",
            f"/api/v1/admin/council/sessions/{service.session.id}/open",
        )
        conflict = await _request(
            service,
            "POST",
            f"/api/v1/council/cases/{service.case.id}/conflict",
            json={"hasConflict": False, "reason": None},
        )
        vote = await _request(
            service,
            "POST",
            f"/api/v1/council/cases/{service.case.id}/vote",
            json={"choice": "APPROVE", "reason": "Meets requirements."},
        )
        closed = await _request(
            service,
            "POST",
            f"/api/v1/admin/council/sessions/{service.session.id}/close",
        )
        minutes = await _request(
            service,
            "GET",
            f"/api/v1/council/sessions/{service.session.id}/minutes",
        )

        assert attended.status_code == 200
        assert attended.json()["data"]["attendanceConfirmedAt"] is not None
        assert opened.json()["data"]["status"] == "OPEN"
        assert conflict.json()["data"]["hasConflict"] is False
        assert vote.json()["data"]["choice"] == "APPROVE"
        assert closed.json()["data"]["status"] == "CLOSED"
        assert minutes.json()["data"]["cases"][0]["decision"] == "APPROVE"
        assert minutes.json()["data"]["cases"][0]["voteCounts"]["APPROVE"] == 1

    asyncio.run(exercise())
