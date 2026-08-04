from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import create_application
from app.modules.voting.aggregate_service import VoteAggregateItem
from app.modules.voting.dependencies import get_public_voting_service
from app.modules.voting.models import CampaignStatus
from app.modules.voting.public_service import PublicCampaignWorkItem

NOW = datetime(2026, 8, 3, tzinfo=UTC)


def test_public_voting_contract_is_allowlisted() -> None:
    campaign_id = uuid4()
    work_id = uuid4()
    campaign = SimpleNamespace(
        id=campaign_id,
        name="Bình chọn tháng 8",
        slug="binh-chon-thang-8",
        description="Chiến dịch cộng đồng",
        status=CampaignStatus.ACTIVE,
        timezone="Asia/Ho_Chi_Minh",
        start_at=NOW - timedelta(days=1),
        end_at=NOW + timedelta(days=1),
        max_votes_per_user=1,
        allow_vote_change=True,
        allow_vote_revoke=True,
        rule_version=2,
    )

    class StubService:
        async def list_campaigns(self, **_kwargs: object):
            return [campaign], 1

        async def campaign(self, _slug: str):
            return campaign

        async def works(self, _slug: str):
            return [
                PublicCampaignWorkItem(
                    work_id=work_id,
                    title="Tác phẩm số",
                    slug="tac-pham-so",
                    short_description="Mô tả công khai",
                )
            ]

        async def summary(self, _slug: str):
            return [
                VoteAggregateItem(
                    work_id=work_id,
                    work_title="Tác phẩm số",
                    work_slug="tac-pham-so",
                    effective_count=12,
                    refreshed_at=NOW,
                )
            ]

    app = create_application()
    app.dependency_overrides[get_public_voting_service] = lambda: StubService()
    with TestClient(app) as client:
        listed = client.get("/api/v1/public/campaigns")
        detail = client.get("/api/v1/public/campaigns/binh-chon-thang-8")
        works = client.get("/api/v1/public/campaigns/binh-chon-thang-8/works")
        summary = client.get("/api/v1/public/campaigns/binh-chon-thang-8/vote-summary")

    assert listed.status_code == detail.status_code == 200
    assert works.status_code == summary.status_code == 200
    assert detail.json()["data"]["serverTime"]
    assert summary.json()["data"][0]["effectiveCount"] == 12
    combined = listed.text + detail.text + works.text + summary.text
    assert "userId" not in combined
    assert "email" not in combined.lower()
    assert "risk" not in combined.lower()
