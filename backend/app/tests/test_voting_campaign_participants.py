import asyncio
import base64
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.outbox import OutboxEvent
from app.main import create_application
from app.modules.audit.models import AuditLog
from app.modules.audit.service import AuditService
from app.modules.auth.dependencies import (
    get_csrf_protected_principal,
    get_current_principal,
)
from app.modules.auth.models import User
from app.modules.auth.security import OutboxPayloadCipher
from app.modules.auth.session_service import AuthPrincipal
from app.modules.blockchain.models import Certificate as Certificate
from app.modules.dossiers.models import Category, Dossier, DossierStatus
from app.modules.media.models import MediaAsset as MediaAsset
from app.modules.public.models import (
    PublicationStatus,
    PublicWork,
    PublicWorkVisibility,
)
from app.modules.voting.dependencies import get_voting_campaign_service
from app.modules.voting.errors import (
    VotingParticipantSetLockedError,
    VotingParticipantWorkNotEligibleError,
)
from app.modules.voting.models import (
    CampaignEvent,
    CampaignStatus,
    CampaignType,
    CampaignWorkStatus,
    PeriodType,
    VotingCampaign,
)
from app.modules.voting.repository import CampaignParticipantView
from app.modules.voting.schemas import CampaignParticipantBulkRequest
from app.modules.voting.service import (
    CAMPAIGN_MANAGE_PERMISSION,
    CAMPAIGN_READ_PERMISSION,
    VotingCampaignService,
)

NOW = datetime(2026, 8, 3, 8, tzinfo=UTC)


def _principal(user_id: UUID) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=user_id,
        session_id=uuid4(),
        email="participant-manager@example.test",
        roles=("CONTENT_ADMIN",),
        permissions=(CAMPAIGN_READ_PERMISSION, CAMPAIGN_MANAGE_PERMISSION),
    )


def _cipher() -> OutboxPayloadCipher:
    return OutboxPayloadCipher.from_base64(
        encoded_key=base64.b64encode(b"p" * 32).decode(),
        key_id="participant-test-key",
    )


async def _work(
    session: AsyncSession,
    *,
    owner: User,
    category: Category,
    visibility: PublicWorkVisibility = PublicWorkVisibility.PUBLIC,
) -> PublicWork:
    dossier = Dossier(
        id=uuid4(),
        code=f"DOS-{uuid4().hex[:10]}",
        owner_user_id=owner.id,
        category_id=category.id,
        title="TÃ¡c pháº©m tham gia",
        summary="TÃ¡c pháº©m Ä‘Ã£ cÃ´ng bá»‘",
        _status=DossierStatus.CERTIFICATE_ISSUED,
    )
    work = PublicWork(
        id=uuid4(),
        dossier_id=dossier.id,
        owner_user_id=owner.id,
        slug=f"work-{uuid4().hex}",
        title="TÃ¡c pháº©m tham gia",
        short_description="MÃ´ táº£ cÃ´ng khai",
        category_id=category.id,
        publication_status=PublicationStatus.PUBLISHED,
        visibility=visibility,
        published_at=NOW,
    )
    session.add_all([dossier, work])
    await session.flush()
    return work


def test_bulk_request_rejects_duplicate_work_ids() -> None:
    work_id = uuid4()
    with pytest.raises(ValidationError):
        CampaignParticipantBulkRequest.model_validate(
            {"workIds": [str(work_id), str(work_id)], "reason": "Import"}
        )


def test_participant_admin_api_uses_safe_contract_and_csrf_dependency() -> None:
    campaign_id = uuid4()
    work_id = uuid4()
    participant = CampaignParticipantView(
        id=uuid4(),
        campaign_id=campaign_id,
        work_id=work_id,
        status=CampaignWorkStatus.PENDING,
        title="Tác phẩm công khai",
        slug="tac-pham-cong-khai",
        approved_at=None,
        created_at=NOW,
        updated_at=NOW,
    )

    class StubService:
        bulk_work_ids: tuple[object, ...] = ()

        async def list_participants(
            self, *_args: object, **_kwargs: object
        ) -> tuple[tuple[CampaignParticipantView, ...], int]:
            return (participant,), 1

        async def add_participants(
            self,
            _principal: object,
            _campaign_id: object,
            work_ids: tuple[object, ...],
            **_kwargs: object,
        ) -> tuple[CampaignParticipantView, ...]:
            self.bulk_work_ids = work_ids
            return (participant,)

    service = StubService()
    principal = _principal(uuid4())
    app = create_application()
    app.dependency_overrides[get_voting_campaign_service] = lambda: service
    app.dependency_overrides[get_current_principal] = lambda: principal
    app.dependency_overrides[get_csrf_protected_principal] = lambda: principal
    with TestClient(app) as client:
        listed = client.get(
            f"/api/v1/admin/voting/campaigns/{campaign_id}/participants"
        )
        added = client.post(
            f"/api/v1/admin/voting/campaigns/{campaign_id}/participants/bulk",
            json={"workIds": [str(work_id)], "reason": "Đã kiểm tra"},
        )

    assert listed.status_code == 200
    assert listed.json()["data"][0] == {
        "id": str(participant.id),
        "campaignId": str(campaign_id),
        "workId": str(work_id),
        "status": "PENDING",
        "title": "Tác phẩm công khai",
        "slug": "tac-pham-cong-khai",
        "approvedAt": None,
        "createdAt": NOW.isoformat().replace("+00:00", "Z"),
        "updatedAt": NOW.isoformat().replace("+00:00", "Z"),
    }
    assert added.status_code == 201
    assert service.bulk_work_ids == (work_id,)


def test_participant_service_enforces_eligibility_freeze_and_audit(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'participants.sqlite3').as_posix()}"
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        manager = User(id=uuid4(), email="manager@example.test", password_hash="hash")
        owner = User(id=uuid4(), email="owner@example.test", password_hash="hash")
        category = Category(id=uuid4(), code="VOTING", name="Voting")
        campaign = VotingCampaign(
            id=uuid4(),
            name="BÃ¬nh chá»n",
            slug="binh-chon",
            description="BÃ¬nh chá»n cá»™ng Ä‘á»“ng",
            status=CampaignStatus.DRAFT,
            campaign_type=CampaignType.PERIODIC,
            period_type=PeriodType.MONTHLY,
            timezone="Asia/Ho_Chi_Minh",
            start_at=NOW + timedelta(days=1),
            end_at=NOW + timedelta(days=31),
            max_votes_per_user=3,
            max_votes_per_work_per_user=1,
            allow_vote_change=True,
            allow_vote_revoke=True,
            require_verified_email=True,
            min_account_age_hours=0,
            eligibility_rules={},
            rule_version=1,
            created_by=manager.id,
        )
        campaign_id = campaign.id

        async with factory() as session:
            async with session.begin():
                session.add_all([manager, owner, category, campaign])
            public_work = await _work(session, owner=owner, category=category)
            hidden_work = await _work(
                session,
                owner=owner,
                category=category,
                visibility=PublicWorkVisibility.PRIVATE,
            )
            await session.commit()
            service = VotingCampaignService(
                session=session,
                audit=AuditService(session),
                payload_cipher=_cipher(),
                clock=lambda: NOW,
            )
            principal = _principal(manager.id)

            participant = await service.add_participant(
                principal,
                campaign_id,
                public_work.id,
                reason="Äá»§ Ä‘iá»u kiá»‡n",
                request_id="add",
            )
            repeated = await service.add_participant(
                principal,
                campaign_id,
                public_work.id,
                reason="Retry",
                request_id="add-retry",
            )
            assert participant.id == repeated.id
            assert participant.status is CampaignWorkStatus.PENDING

            with pytest.raises(VotingParticipantWorkNotEligibleError):
                await service.add_participant(
                    principal,
                    campaign_id,
                    hidden_work.id,
                    reason="KhÃ´ng há»£p lá»‡",
                    request_id="hidden",
                )

            approved = await service.approve_participant(
                principal,
                campaign_id,
                participant.id,
                reason="ÄÃ£ kiá»ƒm tra",
                request_id="approve",
            )
            assert approved.status is CampaignWorkStatus.APPROVED
            rows, total = await service.list_participants(
                principal,
                campaign_id,
                status=None,
                page=1,
                page_size=20,
            )
            assert total == 1
            assert rows[0].title == "TÃ¡c pháº©m tham gia"

            await session.commit()
            async with session.begin():
                campaign.status = CampaignStatus.ACTIVE
            with pytest.raises(VotingParticipantSetLockedError):
                await service.remove_participant(
                    principal,
                    campaign_id,
                    participant.id,
                    reason="KhÃ³a sau khi kÃ­ch hoáº¡t",
                    request_id="locked",
                )

            actions = tuple(await session.scalars(select(AuditLog.action)))
            event_types = tuple(await session.scalars(select(CampaignEvent.event_type)))
            outbox_count = int(
                await session.scalar(select(func.count(OutboxEvent.id))) or 0
            )
            assert actions == (
                "voting.campaign.participant_added",
                "voting.campaign.participant_approved",
            )
            assert event_types == (
                "CAMPAIGN_PARTICIPANT_ADDED",
                "CAMPAIGN_PARTICIPANT_APPROVED",
            )
            assert outbox_count == 2
        await engine.dispose()

    asyncio.run(exercise())
