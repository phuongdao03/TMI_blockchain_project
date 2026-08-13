from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import create_application
from app.modules.auth.dependencies import get_current_principal
from app.modules.auth.models import UserStatus
from app.modules.auth.session_service import AuthPrincipal
from app.modules.voting.dependencies import get_voting_eligibility_service
from app.modules.voting.eligibility import (
    EligibilitySnapshot,
    VotingEligibilityDecision,
    VotingEligibilityEngine,
)
from app.modules.voting.models import CampaignStatus
from app.modules.voting.types import EligibilityReason

NOW = datetime(2026, 8, 3, 8, tzinfo=UTC)


def _snapshot(**changes: object) -> EligibilitySnapshot:
    values: dict[str, object] = {
        "user_status": UserStatus.ACTIVE,
        "email_verified_at": NOW - timedelta(days=30),
        "account_created_at": NOW - timedelta(days=60),
        "roles": ("PUBLIC_USER",),
        "organization_ids": (),
        "campaign_status": CampaignStatus.ACTIVE,
        "start_at": NOW,
        "end_at": NOW + timedelta(days=1),
        "require_verified_email": True,
        "min_account_age_hours": 24,
        "allowed_roles": (),
        "allowed_organization_ids": (),
        "participant_eligible": True,
        "effective_vote_count": 0,
        "already_voted": False,
        "max_votes_per_user": 3,
        "rule_version": 4,
    }
    values.update(changes)
    return EligibilitySnapshot(**values)  # type: ignore[arg-type]


def test_eligibility_engine_enforces_deadline_user_scope_and_quota() -> None:
    engine = VotingEligibilityEngine()

    eligible = engine.evaluate(_snapshot(), now=NOW)
    assert eligible.can_vote is True
    assert eligible.reasons == ()
    assert eligible.remaining_quota == 3
    assert eligible.rule_version == 4

    at_end = engine.evaluate(_snapshot(end_at=NOW), now=NOW)
    assert at_end.reasons == (EligibilityReason.CAMPAIGN_ENDED,)

    restricted = engine.evaluate(
        _snapshot(
            email_verified_at=None,
            account_created_at=NOW - timedelta(hours=1),
            allowed_roles=("COUNCIL_MEMBER",),
            allowed_organization_ids=(uuid4(),),
            participant_eligible=False,
            effective_vote_count=3,
            already_voted=True,
        ),
        now=NOW,
    )
    assert restricted.can_vote is False
    assert restricted.remaining_quota == 0
    assert restricted.reasons == (
        EligibilityReason.EMAIL_NOT_VERIFIED,
        EligibilityReason.ACCOUNT_TOO_NEW,
        EligibilityReason.ROLE_NOT_ELIGIBLE,
        EligibilityReason.ORGANIZATION_NOT_ELIGIBLE,
        EligibilityReason.WORK_NOT_ELIGIBLE,
        EligibilityReason.VOTE_LIMIT_REACHED,
        EligibilityReason.ALREADY_VOTED,
    )


def test_eligibility_api_returns_only_current_user_summary() -> None:
    campaign_id = uuid4()
    work_id = uuid4()
    principal = AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="voter@example.test",
        roles=("PUBLIC_USER",),
        permissions=(),
    )

    class StubService:
        async def evaluate(
            self, *_args: object, **_kwargs: object
        ) -> VotingEligibilityDecision:
            return VotingEligibilityDecision(
                can_vote=False,
                reasons=(EligibilityReason.EMAIL_NOT_VERIFIED,),
                remaining_quota=2,
                rule_version=7,
                server_time=NOW,
            )

    app = create_application()
    app.dependency_overrides[get_current_principal] = lambda: principal
    app.dependency_overrides[get_voting_eligibility_service] = lambda: StubService()
    with TestClient(app) as client:
        response = client.get(
            f"/api/v1/campaigns/{campaign_id}/eligibility",
            params={"workId": str(work_id)},
        )

    assert response.status_code == 200
    assert response.json()["data"] == {
        "canVote": False,
        "reasons": ["EMAIL_NOT_VERIFIED"],
        "remainingQuota": 2,
        "ruleVersion": 7,
        "serverTime": "2026-08-03T08:00:00Z",
    }
    assert "email" not in response.text
    assert str(principal.user_id) not in response.text
