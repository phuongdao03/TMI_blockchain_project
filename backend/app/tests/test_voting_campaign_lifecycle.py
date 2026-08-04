import asyncio
import base64
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.outbox import OutboxEvent
from app.main import create_application
from app.modules.audit.models import AuditLog
from app.modules.audit.service import AuditService
from app.modules.auth.dependencies import get_csrf_protected_principal
from app.modules.auth.models import User
from app.modules.auth.security import OutboxPayloadCipher
from app.modules.auth.session_service import AuthPrincipal
from app.modules.dossiers.models import Category, Dossier, DossierStatus
from app.modules.public.models import (
    PublicationStatus,
    PublicWork,
    PublicWorkVisibility,
)
from app.modules.voting.dependencies import get_voting_campaign_service
from app.modules.voting.errors import (
    VotingCampaignForbiddenError,
    VotingCampaignInvalidTransitionError,
    VotingCampaignPreflightError,
    VotingCampaignReasonRequiredError,
)
from app.modules.voting.models import (
    CampaignEvent,
    CampaignStatus,
    CampaignType,
    CampaignWork,
    CampaignWorkStatus,
    PeriodType,
    VotingCampaign,
)
from app.modules.voting.service import (
    CAMPAIGN_ALLOWED_ACTIONS,
    CAMPAIGN_MANAGE_PERMISSION,
    CAMPAIGN_READ_PERMISSION,
    CampaignLifecycleAction,
    VotingCampaignInput,
    VotingCampaignService,
    assert_campaign_transition,
)
from app.modules.voting.telemetry import voting_lifecycle_telemetry
from app.workers.celery_app import celery_app
from app.workers.voting_lifecycle_tasks import reconcile_voting_campaign_lifecycle

NOW = datetime(2026, 8, 3, 8, tzinfo=UTC)


def _cipher() -> OutboxPayloadCipher:
    return OutboxPayloadCipher.from_base64(
        encoded_key=base64.b64encode(b"v" * 32).decode(),
        key_id="voting-test-key",
    )


def _principal(user_id: UUID | None = None) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=user_id or uuid4(),
        session_id=uuid4(),
        email="campaign-manager@example.test",
        roles=("CONTENT_ADMIN",),
        permissions=(CAMPAIGN_READ_PERMISSION, CAMPAIGN_MANAGE_PERMISSION),
    )


def _input(*, slug: str) -> VotingCampaignInput:
    return VotingCampaignInput(
        name="Chiến dịch tháng tám",
        slug=slug,
        description="Bình chọn tác phẩm công khai",
        campaign_type=CampaignType.PERIODIC,
        period_type=PeriodType.MONTHLY,
        timezone="Asia/Ho_Chi_Minh",
        start_at=NOW + timedelta(hours=1),
        end_at=NOW + timedelta(hours=2),
        max_votes_per_user=3,
        max_votes_per_work_per_user=1,
        allow_vote_change=True,
        allow_vote_revoke=True,
        require_verified_email=True,
        min_account_age_hours=0,
        eligibility_rules={"organization_ids": [], "allowed_roles": []},
    )


async def _seed_public_participant(
    session: AsyncSession,
    *,
    campaign: VotingCampaign,
    manager_id: UUID,
) -> PublicWork:
    owner = User(
        id=uuid4(),
        email=f"owner-{uuid4()}@example.test",
        password_hash="hash",
    )
    category = Category(id=uuid4(), code=uuid4().hex[:12], name="Voting")
    dossier = Dossier(
        id=uuid4(),
        code=f"DOS-{uuid4().hex[:10]}",
        owner_user_id=owner.id,
        category_id=category.id,
        title="Tác phẩm bình chọn",
        summary="Tác phẩm đã công bố",
        _status=DossierStatus.CERTIFICATE_ISSUED,
    )
    work = PublicWork(
        id=uuid4(),
        dossier_id=dossier.id,
        owner_user_id=owner.id,
        slug=f"work-{uuid4().hex}",
        title="Tác phẩm bình chọn",
        short_description="Tác phẩm đã công bố",
        category_id=category.id,
        publication_status=PublicationStatus.PUBLISHED,
        visibility=PublicWorkVisibility.PUBLIC,
        published_at=NOW,
    )
    session.add_all(
        [
            owner,
            category,
            dossier,
            work,
            CampaignWork(
                campaign_id=campaign.id,
                work_id=work.id,
                status=CampaignWorkStatus.APPROVED,
                approved_by=manager_id,
                approved_at=NOW,
            ),
        ]
    )
    await session.flush()
    return work


def test_campaign_transition_table_rejects_illegal_paths() -> None:
    for current in CampaignStatus:
        for action in CampaignLifecycleAction:
            if action in CAMPAIGN_ALLOWED_ACTIONS[current]:
                assert_campaign_transition(current, action)
            else:
                with pytest.raises(VotingCampaignInvalidTransitionError):
                    assert_campaign_transition(current, action)


def test_lifecycle_preflight_time_reason_idempotency_and_outbox(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'voting-lifecycle.sqlite3').as_posix()}"
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        current_time = [NOW]
        manager = User(
            id=uuid4(),
            email="manager@example.test",
            password_hash="hash",
        )
        manager_id = manager.id
        principal = _principal(manager_id)

        async with factory() as session:
            async with session.begin():
                session.add(manager)
            service = VotingCampaignService(
                session=session,
                audit=AuditService(session),
                payload_cipher=_cipher(),
                clock=lambda: current_time[0],
            )
            campaign = await service.create(
                principal,
                _input(slug="lifecycle"),
                request_id="create",
            )
            campaign_id = campaign.id

            unauthorized = AuthPrincipal(
                user_id=manager_id,
                session_id=uuid4(),
                email="campaign-manager@example.test",
                roles=("CONTENT_ADMIN",),
                permissions=(),
            )
            with pytest.raises(VotingCampaignForbiddenError):
                await service.transition(
                    unauthorized,
                    campaign_id,
                    CampaignLifecycleAction.SCHEDULE,
                    request_id="schedule-forbidden",
                )

            with pytest.raises(VotingCampaignPreflightError) as missing_participant:
                await service.transition(
                    principal,
                    campaign_id,
                    CampaignLifecycleAction.SCHEDULE,
                    request_id="schedule-empty",
                )
            assert missing_participant.value.details == {
                "reasons": ["NO_ELIGIBLE_PARTICIPANTS"]
            }

            async with session.begin():
                work = await _seed_public_participant(
                    session,
                    campaign=await service.get(principal, campaign_id),
                    manager_id=manager_id,
                )
                work.visibility = PublicWorkVisibility.PRIVATE
                work_id = work.id
            with pytest.raises(VotingCampaignPreflightError) as hidden_participant:
                await service.transition(
                    principal,
                    campaign_id,
                    CampaignLifecycleAction.SCHEDULE,
                    request_id="schedule-hidden",
                )
            assert hidden_participant.value.details == {
                "reasons": ["NO_ELIGIBLE_PARTICIPANTS"]
            }
            async with session.begin():
                stored_work = await session.get(PublicWork, work_id)
                assert stored_work is not None
                stored_work.visibility = PublicWorkVisibility.PUBLIC
            scheduled = await service.transition(
                principal,
                campaign_id,
                CampaignLifecycleAction.SCHEDULE,
                request_id="schedule",
            )
            repeated = await service.transition(
                principal,
                campaign_id,
                CampaignLifecycleAction.SCHEDULE,
                request_id="schedule-retry",
            )
            assert scheduled.status is CampaignStatus.SCHEDULED
            assert repeated.status is CampaignStatus.SCHEDULED

            with pytest.raises(VotingCampaignPreflightError) as too_early:
                await service.transition(
                    principal,
                    campaign_id,
                    CampaignLifecycleAction.ACTIVATE,
                    request_id="activate-early",
                )
            assert too_early.value.details == {"reasons": ["OUTSIDE_ACTIVE_WINDOW"]}

            current_time[0] = NOW + timedelta(hours=1)
            active = await service.transition(
                principal,
                campaign_id,
                CampaignLifecycleAction.ACTIVATE,
                request_id="activate",
            )
            assert active.status is CampaignStatus.ACTIVE

            with pytest.raises(VotingCampaignReasonRequiredError):
                await service.transition(
                    principal,
                    campaign_id,
                    CampaignLifecycleAction.PAUSE,
                    reason=" ",
                    request_id="pause-empty",
                )
            paused = await service.transition(
                principal,
                campaign_id,
                CampaignLifecycleAction.PAUSE,
                reason="Sự cố vận hành",
                request_id="pause",
            )
            assert paused.status is CampaignStatus.PAUSED

            event_count = int(
                await session.scalar(select(func.count()).select_from(CampaignEvent))
                or 0
            )
            outbox_count = int(
                await session.scalar(select(func.count()).select_from(OutboxEvent)) or 0
            )
            audit_actions = tuple(
                (
                    await session.scalars(
                        select(AuditLog.action).order_by(AuditLog.created_at)
                    )
                ).all()
            )
            assert event_count == 4  # create + schedule + activate + pause
            assert outbox_count == 3
            assert audit_actions[-3:] == (
                "voting.campaign.scheduled",
                "voting.campaign.activated",
                "voting.campaign.paused",
            )
        await engine.dispose()

    asyncio.run(exercise())


def test_scheduler_activates_and_ends_once_at_server_boundaries(tmp_path: Path) -> None:
    async def exercise() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'voting-scheduler.sqlite3').as_posix()}"
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        manager = User(
            id=uuid4(),
            email="scheduler-manager@example.test",
            password_hash="hash",
        )
        manager_id = manager.id
        principal = _principal(manager_id)
        voting_lifecycle_telemetry.reset()
        async with factory() as session:
            async with session.begin():
                session.add(manager)
            service = VotingCampaignService(
                session=session,
                audit=AuditService(session),
                payload_cipher=_cipher(),
                clock=lambda: NOW,
            )
            campaign = await service.create(
                principal,
                _input(slug="scheduled-worker"),
                request_id="create",
            )
            async with session.begin():
                await _seed_public_participant(
                    session,
                    campaign=campaign,
                    manager_id=manager_id,
                )
            await service.transition(
                principal,
                campaign.id,
                CampaignLifecycleAction.SCHEDULE,
                request_id="schedule",
            )

            activated = await service.reconcile_due(
                now=NOW + timedelta(hours=1),
                limit=100,
            )
            repeated_activation = await service.reconcile_due(
                now=NOW + timedelta(hours=1),
                limit=100,
            )
            ended = await service.reconcile_due(
                now=NOW + timedelta(hours=2),
                limit=100,
            )
            repeated_end = await service.reconcile_due(
                now=NOW + timedelta(hours=2),
                limit=100,
            )
            assert (activated, repeated_activation, ended, repeated_end) == (1, 0, 1, 0)
            await session.refresh(campaign)
            assert campaign.status is CampaignStatus.ENDED

            lifecycle_events = tuple(
                (
                    await session.scalars(
                        select(CampaignEvent.event_type).where(
                            CampaignEvent.event_type.in_(
                                {"CAMPAIGN_ACTIVATED", "CAMPAIGN_ENDED"}
                            )
                        )
                    )
                ).all()
            )
            assert sorted(lifecycle_events) == ["CAMPAIGN_ACTIVATED", "CAMPAIGN_ENDED"]
            assert voting_lifecycle_telemetry.snapshot()["scheduler_success"] == 2
            await session.rollback()

            missed = await service.create(
                principal,
                _input(slug="missed-worker-window"),
                request_id="create-missed",
            )
            async with session.begin():
                await _seed_public_participant(
                    session,
                    campaign=missed,
                    manager_id=manager_id,
                )
            await service.transition(
                principal,
                missed.id,
                CampaignLifecycleAction.SCHEDULE,
                request_id="schedule-missed",
            )
            assert (
                await service.reconcile_due(
                    now=NOW + timedelta(hours=2),
                    limit=100,
                )
                == 0
            )
            await session.refresh(missed)
            assert missed.status is CampaignStatus.SCHEDULED
            assert voting_lifecycle_telemetry.snapshot()["scheduler_failure"] == 1
        await engine.dispose()

    asyncio.run(exercise())


class _LifecycleApiService:
    def __init__(self) -> None:
        self.calls: list[tuple[CampaignLifecycleAction, str | None]] = []
        self.row = VotingCampaign(
            id=uuid4(),
            name="Campaign",
            slug="campaign",
            description="Description",
            status=CampaignStatus.DRAFT,
            campaign_type=CampaignType.PERIODIC,
            period_type=PeriodType.MONTHLY,
            timezone="Asia/Ho_Chi_Minh",
            start_at=NOW + timedelta(hours=1),
            end_at=NOW + timedelta(hours=2),
            max_votes_per_user=3,
            max_votes_per_work_per_user=1,
            allow_vote_change=False,
            allow_vote_revoke=False,
            require_verified_email=True,
            min_account_age_hours=0,
            eligibility_rules={"organization_ids": [], "allowed_roles": []},
            rule_version=1,
            created_by=uuid4(),
            created_at=NOW,
            updated_at=NOW,
        )

    async def transition(
        self,
        _principal: object,
        campaign_id: UUID,
        action: CampaignLifecycleAction,
        *,
        reason: str | None = None,
        request_id: str,
    ) -> VotingCampaign:
        assert campaign_id == self.row.id
        assert request_id
        self.calls.append((action, reason))
        return self.row


def test_lifecycle_admin_api_contract_validates_reason_and_dispatches() -> None:
    service = _LifecycleApiService()
    app = create_application()
    app.dependency_overrides[get_voting_campaign_service] = lambda: service
    app.dependency_overrides[get_csrf_protected_principal] = lambda: _principal()
    try:
        expected_paths = {
            f"/api/v1/admin/voting/campaigns/{{campaign_id}}/{action}"
            for action in ("schedule", "activate", "pause", "resume", "end", "cancel")
        }
        assert expected_paths.issubset(app.openapi()["paths"])
        with TestClient(app) as client:
            schedule = client.post(
                f"/api/v1/admin/voting/campaigns/{service.row.id}/schedule"
            )
            invalid_pause = client.post(
                f"/api/v1/admin/voting/campaigns/{service.row.id}/pause",
                json={"reason": " "},
            )
            pause = client.post(
                f"/api/v1/admin/voting/campaigns/{service.row.id}/pause",
                json={"reason": "Sự cố vận hành"},
            )
        assert schedule.status_code == 200
        assert invalid_pause.status_code == 422
        assert pause.status_code == 200
        assert service.calls == [
            (CampaignLifecycleAction.SCHEDULE, None),
            (CampaignLifecycleAction.PAUSE, "Sự cố vận hành"),
        ]
    finally:
        app.dependency_overrides.clear()


def test_lifecycle_worker_has_retry_and_beat_configuration() -> None:
    schedule = celery_app.conf.beat_schedule["reconcile-voting-campaign-lifecycle"]
    assert schedule["schedule"] == 15.0
    assert schedule["task"] == reconcile_voting_campaign_lifecycle.name
    assert reconcile_voting_campaign_lifecycle.max_retries == 5
