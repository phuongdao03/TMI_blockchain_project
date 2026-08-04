import asyncio
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import uuid4

import pytest
from sqlalchemy import Table
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.base import Base
from app.modules.auth.models import User, UserStatus
from app.modules.blockchain import models as blockchain_models  # noqa: F401
from app.modules.dossiers import models as dossier_models  # noqa: F401
from app.modules.media import models as media_models  # noqa: F401
from app.modules.organizations import models as organization_models  # noqa: F401
from app.modules.public import models as public_models  # noqa: F401
from app.modules.voting.models import (
    CampaignType,
    CampaignWork,
    CampaignWorkStatus,
    PeriodType,
    Vote,
    VoteStatus,
    VotingCampaign,
)


async def _database() -> tuple[async_sessionmaker[AsyncSession], AsyncEngine]:
    engine = create_async_engine("sqlite+aiosqlite://")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return session_factory, engine


def test_voting_schema_exposes_planned_constraints_and_indexes() -> None:
    campaign_table = cast(Table, VotingCampaign.__table__)
    participant_table = cast(Table, CampaignWork.__table__)
    vote_table = cast(Table, Vote.__table__)

    assert set(campaign_table.c) >= {
        campaign_table.c.status,
        campaign_table.c.campaign_type,
        campaign_table.c.period_type,
        campaign_table.c.eligibility_rules,
        campaign_table.c.rule_version,
    }
    assert {constraint.name for constraint in campaign_table.constraints}.issuperset(
        {
            "ck_voting_campaigns_time_window_valid",
            "ck_voting_campaigns_max_votes_per_user_positive",
            "ck_voting_campaigns_max_votes_per_work_one",
            "ck_voting_campaigns_rule_version_positive",
        }
    )
    assert any(
        constraint.name == "uq_campaign_works_campaign_work"
        for constraint in participant_table.constraints
    )
    effective_index = next(
        index
        for index in vote_table.indexes
        if index.name == "uq_votes_effective_campaign_work_user"
    )
    assert effective_index.unique is True
    assert effective_index.dialect_options["postgresql"]["where"] is not None
    assert effective_index.dialect_options["sqlite"]["where"] is not None


def test_database_rejects_duplicate_effective_vote() -> None:
    async def exercise() -> None:
        session_factory, engine = await _database()
        now = datetime.now(UTC)
        user = User(
            id=uuid4(),
            email="voter@tmigroup.vn",
            password_hash="not-used",
            status=UserStatus.ACTIVE,
            email_verified_at=now,
        )
        campaign = VotingCampaign(
            id=uuid4(),
            name="Tác phẩm tháng tám",
            slug="tac-pham-thang-tam",
            description="Bình chọn cộng đồng",
            campaign_type=CampaignType.PERIODIC,
            period_type=PeriodType.MONTHLY,
            timezone="Asia/Ho_Chi_Minh",
            start_at=now - timedelta(hours=1),
            end_at=now + timedelta(hours=1),
            max_votes_per_user=3,
            max_votes_per_work_per_user=1,
            eligibility_rules={},
            created_by=user.id,
        )
        work_id = uuid4()
        participant = CampaignWork(
            id=uuid4(),
            campaign_id=campaign.id,
            work_id=work_id,
            status=CampaignWorkStatus.APPROVED,
            approved_by=user.id,
            approved_at=now,
            metadata_json={},
        )

        async with session_factory() as session:
            session.add_all([user, campaign, participant])
            await session.flush()
            session.add_all(
                [
                    Vote(
                        id=uuid4(),
                        campaign_id=campaign.id,
                        work_id=work_id,
                        user_id=user.id,
                        status=VoteStatus.VALID,
                        source="WEB",
                        idempotency_key="vote-key-1",
                    ),
                    Vote(
                        id=uuid4(),
                        campaign_id=campaign.id,
                        work_id=work_id,
                        user_id=user.id,
                        status=VoteStatus.VALID,
                        source="WEB",
                        idempotency_key="vote-key-2",
                    ),
                ]
            )
            with pytest.raises(IntegrityError):
                await session.commit()
        await engine.dispose()

    asyncio.run(exercise())
