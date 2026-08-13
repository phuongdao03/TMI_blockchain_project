from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import create_application
from app.modules.auth.dependencies import get_current_principal
from app.modules.auth.session_service import AuthPrincipal
from app.modules.voting.admin_vote_service import AdminVoteItem, AdminVoteService
from app.modules.voting.dependencies import get_admin_vote_service
from app.modules.voting.errors import VotingCampaignForbiddenError
from app.modules.voting.models import VoteStatus


def _principal(*permissions: str) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="admin@example.test",
        roles=("CONTENT_ADMIN",),
        permissions=permissions,
    )


def test_admin_vote_service_requires_explicit_permission() -> None:
    with pytest.raises(VotingCampaignForbiddenError):
        AdminVoteService._require_read(_principal())


def test_admin_vote_list_and_export_are_redacted() -> None:
    principal = _principal("voting.vote.read")
    campaign_id = uuid4()
    item = AdminVoteItem(
        vote_id=uuid4(),
        campaign_id=campaign_id,
        campaign_name="Bình chọn tháng 8",
        work_id=uuid4(),
        work_title="Tác phẩm số",
        voter_reference="voter-abcdef1234567890",
        status=VoteStatus.VALID,
        source="WEB",
        risk_score="0.0000",
        created_at=datetime(2026, 8, 3, tzinfo=UTC),
        revoked_at=None,
    )

    class StubService:
        async def list(
            self, received: AuthPrincipal, *_args: object, **_kwargs: object
        ) -> tuple[list[AdminVoteItem], int]:
            assert received.user_id == principal.user_id
            return [item], 1

    app = create_application()
    app.dependency_overrides[get_current_principal] = lambda: principal
    app.dependency_overrides[get_admin_vote_service] = lambda: StubService()
    with TestClient(app) as client:
        listed = client.get(f"/api/v1/admin/voting/campaigns/{campaign_id}/votes")
        exported = client.get(
            f"/api/v1/admin/voting/campaigns/{campaign_id}/votes/export.csv"
        )

    assert listed.status_code == 200
    assert listed.json()["data"][0]["voterReference"] == item.voter_reference
    assert exported.status_code == 200
    assert item.voter_reference in exported.text
    combined = listed.text + exported.text
    assert principal.email not in combined
    assert str(principal.user_id) not in combined
    assert "password" not in combined.lower()
