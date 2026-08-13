import asyncio
import base64
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Never
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.outbox import OutboxEvent
from app.main import create_application
from app.modules.audit.models import AuditLog
from app.modules.audit.service import AuditService
from app.modules.auth.dependencies import (
    get_csrf_protected_principal,
    get_current_principal,
)
from app.modules.auth.models import User, UserStatus
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
from app.modules.voting.aggregate_service import VoteAggregateService
from app.modules.voting.dependencies import (
    enforce_voting_rate_limit,
    get_vote_history_service,
    get_voting_service,
)
from app.modules.voting.eligibility import VotingEligibilityService
from app.modules.voting.errors import (
    VotingEligibilityDeniedError,
    VotingIdempotencyConflictError,
)
from app.modules.voting.history_service import VoteHistoryItem, VoteHistoryService
from app.modules.voting.models import (
    CampaignStatus,
    CampaignType,
    CampaignWork,
    CampaignWorkStatus,
    PeriodType,
    Vote,
    VoteAggregate,
    VoteEvent,
    VoteStatus,
    VotingCampaign,
)
from app.modules.voting.vote_repository import (
    VoteRepository,
    VotingEligibilityRepository,
)
from app.modules.voting.vote_service import VoteMutationResult, VotingService

NOW = datetime(2026, 8, 3, 8, tzinfo=UTC)


def _principal(user_id: UUID | None = None) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=user_id or uuid4(),
        session_id=uuid4(),
        email="voter@example.test",
        roles=("PUBLIC_USER",),
        permissions=(),
    )


def _cipher() -> OutboxPayloadCipher:
    return OutboxPayloadCipher.from_base64(
        encoded_key=base64.b64encode(b"w" * 32).decode(),
        key_id="vote-test-key",
    )


def test_vote_creation_is_idempotent_and_transactional(tmp_path: Path) -> None:
    async def exercise() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'vote.sqlite3').as_posix()}"
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        manager = User(
            id=uuid4(),
            email="manager@example.test",
            password_hash="hash",
            status=UserStatus.ACTIVE,
            email_verified_at=NOW,
            created_at=NOW - timedelta(days=100),
            updated_at=NOW,
        )
        voter = User(
            id=uuid4(),
            email="voter@example.test",
            password_hash="hash",
            status=UserStatus.ACTIVE,
            email_verified_at=NOW - timedelta(days=10),
            created_at=NOW - timedelta(days=30),
            updated_at=NOW,
        )
        category = Category(id=uuid4(), code="VOTE", name="Voting")
        dossier = Dossier(
            id=uuid4(),
            code="DOS-VOTE",
            owner_user_id=manager.id,
            category_id=category.id,
            title="Tác phẩm bình chọn",
            summary="Tác phẩm công khai",
            _status=DossierStatus.CERTIFICATE_ISSUED,
        )
        work = PublicWork(
            id=uuid4(),
            dossier_id=dossier.id,
            owner_user_id=manager.id,
            slug="tac-pham-binh-chon",
            title="Tác phẩm bình chọn",
            short_description="Tác phẩm công khai",
            category_id=category.id,
            publication_status=PublicationStatus.PUBLISHED,
            visibility=PublicWorkVisibility.PUBLIC,
            published_at=NOW,
        )
        second_dossier = Dossier(
            id=uuid4(),
            code="DOS-VOTE-2",
            owner_user_id=manager.id,
            category_id=category.id,
            title="Tác phẩm bình chọn thứ hai",
            summary="Tác phẩm công khai thứ hai",
            _status=DossierStatus.CERTIFICATE_ISSUED,
        )
        second_work = PublicWork(
            id=uuid4(),
            dossier_id=second_dossier.id,
            owner_user_id=manager.id,
            slug="tac-pham-binh-chon-thu-hai",
            title="Tác phẩm bình chọn thứ hai",
            short_description="Tác phẩm công khai thứ hai",
            category_id=category.id,
            publication_status=PublicationStatus.PUBLISHED,
            visibility=PublicWorkVisibility.PUBLIC,
            published_at=NOW,
        )
        campaign = VotingCampaign(
            id=uuid4(),
            name="Chiến dịch đang mở",
            slug="dang-mo",
            description="Bình chọn cộng đồng",
            status=CampaignStatus.ACTIVE,
            campaign_type=CampaignType.PERIODIC,
            period_type=PeriodType.MONTHLY,
            timezone="Asia/Ho_Chi_Minh",
            start_at=NOW - timedelta(hours=1),
            end_at=NOW + timedelta(hours=1),
            max_votes_per_user=2,
            max_votes_per_work_per_user=1,
            allow_vote_change=True,
            allow_vote_revoke=True,
            require_verified_email=True,
            min_account_age_hours=24,
            eligibility_rules={},
            rule_version=3,
            created_by=manager.id,
        )
        participant = CampaignWork(
            campaign_id=campaign.id,
            work_id=work.id,
            status=CampaignWorkStatus.APPROVED,
            approved_by=manager.id,
            approved_at=NOW,
        )
        second_participant = CampaignWork(
            campaign_id=campaign.id,
            work_id=second_work.id,
            status=CampaignWorkStatus.APPROVED,
            approved_by=manager.id,
            approved_at=NOW,
        )
        campaign_id = campaign.id
        work_id = work.id
        second_work_id = second_work.id

        async with factory() as session:
            async with session.begin():
                session.add_all(
                    [
                        manager,
                        voter,
                        category,
                        dossier,
                        work,
                        second_dossier,
                        second_work,
                        campaign,
                        participant,
                        second_participant,
                    ]
                )
            service = VotingService(
                session=session,
                eligibility=VotingEligibilityService(
                    VotingEligibilityRepository(session),
                    clock=lambda: NOW,
                ),
                audit=AuditService(session),
                payload_cipher=_cipher(),
                clock=lambda: NOW,
            )
            principal = _principal(voter.id)
            created = await service.create_vote(
                principal,
                campaign_id,
                work_id,
                idempotency_key="vote-key-0001",
                request_id="request-1",
            )
            replay = await service.create_vote(
                principal,
                campaign_id,
                work_id,
                idempotency_key="vote-key-0001",
                request_id="request-retry",
            )
            assert replay == created
            assert created.status is VoteStatus.VALID
            assert created.remaining_quota == 1
            assert created.rule_version == 3
            async with session.begin():
                aggregate_service = VoteAggregateService(session)
                aggregate = await aggregate_service.recount_work(
                    campaign_id, work_id, now=NOW
                )
                repeated = await aggregate_service.recount_work(
                    campaign_id, work_id, now=NOW
                )
                assert aggregate.effective_count == 1
                assert repeated.effective_count == 1
                assert repeated.version == 2
            with pytest.raises(VotingIdempotencyConflictError):
                await service.create_vote(
                    principal,
                    campaign_id,
                    uuid4(),
                    idempotency_key="vote-key-0001",
                    request_id="request-conflict",
                )

            changed = await service.change_vote(
                principal,
                campaign_id,
                created.vote_id,
                second_work_id,
                idempotency_key="change-key-0001",
                request_id="request-change",
            )
            changed_replay = await service.change_vote(
                principal,
                campaign_id,
                created.vote_id,
                second_work_id,
                idempotency_key="change-key-0001",
                request_id="request-change-retry",
            )
            assert changed_replay == changed
            assert changed.previous_vote_id == created.vote_id
            assert changed.status is VoteStatus.VALID
            assert changed.remaining_quota == 1

            revoked = await service.revoke_vote(
                principal,
                campaign_id,
                second_work_id,
                idempotency_key="revoke-key-0001",
                request_id="request-revoke",
            )
            revoked_replay = await service.revoke_vote(
                principal,
                campaign_id,
                second_work_id,
                idempotency_key="revoke-key-0001",
                request_id="request-revoke-retry",
            )
            assert revoked_replay == revoked
            assert revoked.status is VoteStatus.REVOKED_BY_USER
            assert revoked.remaining_quota == 2
            async with session.begin():
                aggregate = await VoteAggregateService(session).recount_work(
                    campaign_id, second_work_id, now=NOW
                )
                assert aggregate.effective_count == 0

            original_replay = await service.create_vote(
                principal,
                campaign_id,
                work_id,
                idempotency_key="vote-key-0001",
                request_id="request-original-retry",
            )
            assert original_replay == created

            history_service = VoteHistoryService(VoteRepository(session))
            history, total = await history_service.list(
                principal,
                campaign_id=campaign_id,
                status=None,
                date_from=None,
                date_to=None,
                page=1,
                page_size=20,
                now=NOW,
            )
            outsider_history, outsider_total = await history_service.list(
                _principal(),
                campaign_id=None,
                status=None,
                date_from=None,
                date_to=None,
                page=1,
                page_size=20,
                now=NOW,
            )
            assert total == 2
            assert len(history) == 2
            assert all(not item.can_change and not item.can_revoke for item in history)
            assert outsider_history == []
            assert outsider_total == 0

            campaign.status = CampaignStatus.ENDED
            await session.commit()
            ended_replay = await service.create_vote(
                principal,
                campaign_id,
                work_id,
                idempotency_key="vote-key-0001",
                request_id="request-after-end",
            )
            assert ended_replay == created
            with pytest.raises(VotingEligibilityDeniedError) as denied:
                await service.create_vote(
                    principal,
                    campaign_id,
                    work_id,
                    idempotency_key="vote-key-0002",
                    request_id="request-ended",
                )
            assert denied.value.code == "CAMPAIGN_NOT_ACTIVE"

            assert int(await session.scalar(select(func.count(Vote.id))) or 0) == 2
            assert int(await session.scalar(select(func.count(VoteEvent.id))) or 0) == 4
            assert (
                int(await session.scalar(select(func.count(OutboxEvent.id))) or 0) == 3
            )
            assert int(await session.scalar(select(func.count(AuditLog.id))) or 0) == 3
            assert (
                int(
                    await session.scalar(select(func.count(VoteAggregate.work_id))) or 0
                )
                == 2
            )
            events = (await session.scalars(select(VoteEvent))).all()
            assert {event.event_type for event in events} == {
                "VOTE_CREATED",
                "VOTE_REVOKED_FOR_CHANGE",
                "VOTE_CREATED_BY_CHANGE",
                "VOTE_REVOKED",
            }
            assert events[0].metadata_json["correlation_id"] == "request-1"
            assert "email" not in str([event.metadata_json for event in events]).lower()
            audits = (await session.scalars(select(AuditLog))).all()
            assert "email" not in str([audit.after_json for audit in audits]).lower()

            campaign.status = CampaignStatus.ACTIVE
            await session.commit()

            async def concurrent_submit(key: str) -> VoteMutationResult:
                async with factory() as concurrent_session:
                    concurrent_service = VotingService(
                        session=concurrent_session,
                        eligibility=VotingEligibilityService(
                            VotingEligibilityRepository(concurrent_session),
                            clock=lambda: NOW,
                        ),
                        audit=AuditService(concurrent_session),
                        payload_cipher=_cipher(),
                        clock=lambda: NOW,
                    )
                    return await concurrent_service.create_vote(
                        principal,
                        campaign_id,
                        work_id,
                        idempotency_key=key,
                        request_id=key,
                    )

            concurrent_results = await asyncio.gather(
                concurrent_submit("concurrent-vote-1"),
                concurrent_submit("concurrent-vote-2"),
                return_exceptions=True,
            )
            assert (
                sum(
                    isinstance(result, VoteMutationResult)
                    for result in concurrent_results
                )
                == 1
            )
            assert (
                sum(
                    isinstance(result, VotingEligibilityDeniedError)
                    for result in concurrent_results
                )
                == 1
            )
            async with factory() as verification_session:
                effective_count = int(
                    await verification_session.scalar(
                        select(func.count(Vote.id)).where(
                            Vote.user_id == principal.user_id,
                            Vote.campaign_id == campaign_id,
                            Vote.work_id == work_id,
                            Vote.status == VoteStatus.VALID,
                        )
                    )
                    or 0
                )
                assert effective_count == 1
        await engine.dispose()

    asyncio.run(exercise())


def test_vote_api_requires_idempotency_key_and_returns_safe_truth() -> None:
    campaign_id = uuid4()
    work_id = uuid4()
    principal = _principal()

    class StubService:
        async def create_vote(
            self, *_args: object, **_kwargs: object
        ) -> VoteMutationResult:
            return VoteMutationResult(
                vote_id=uuid4(),
                campaign_id=campaign_id,
                work_id=work_id,
                status=VoteStatus.VALID,
                remaining_quota=2,
                rule_version=5,
                created_at=NOW,
            )

        async def change_vote(
            self, *_args: object, **_kwargs: object
        ) -> VoteMutationResult:
            return VoteMutationResult(
                vote_id=uuid4(),
                campaign_id=campaign_id,
                work_id=work_id,
                status=VoteStatus.VALID,
                remaining_quota=1,
                rule_version=5,
                created_at=NOW,
                previous_vote_id=uuid4(),
            )

        async def revoke_vote(
            self, *_args: object, **_kwargs: object
        ) -> VoteMutationResult:
            return VoteMutationResult(
                vote_id=uuid4(),
                campaign_id=campaign_id,
                work_id=work_id,
                status=VoteStatus.REVOKED_BY_USER,
                remaining_quota=2,
                rule_version=5,
                created_at=NOW,
            )

    app = create_application()
    app.dependency_overrides[get_current_principal] = lambda: principal
    app.dependency_overrides[get_csrf_protected_principal] = lambda: principal
    app.dependency_overrides[get_voting_service] = lambda: StubService()
    app.dependency_overrides[enforce_voting_rate_limit] = lambda: None
    with TestClient(app) as client:
        missing = client.post(f"/api/v1/campaigns/{campaign_id}/works/{work_id}/votes")
        accepted = client.post(
            f"/api/v1/campaigns/{campaign_id}/works/{work_id}/votes",
            headers={"Idempotency-Key": "vote-key-0001"},
        )
        changed = client.post(
            f"/api/v1/campaigns/{campaign_id}/votes/change",
            headers={"Idempotency-Key": "change-key-0001"},
            json={"sourceVoteId": str(uuid4()), "targetWorkId": str(work_id)},
        )
        revoked = client.delete(
            f"/api/v1/campaigns/{campaign_id}/works/{work_id}/votes",
            headers={"Idempotency-Key": "revoke-key-0001"},
        )

    assert missing.status_code == 422
    assert accepted.status_code == 201
    assert changed.status_code == 200
    assert revoked.status_code == 200
    assert (
        accepted.json()["data"]
        | {
            "campaignId": str(campaign_id),
            "workId": str(work_id),
            "status": "VALID",
            "remainingQuota": 2,
            "ruleVersion": 5,
            "createdAt": "2026-08-03T08:00:00Z",
        }
        == accepted.json()["data"]
    )
    assert "user" not in accepted.text.lower()
    assert "previousVoteId" in changed.json()["data"]
    assert revoked.json()["data"]["status"] == "REVOKED_BY_USER"


def test_vote_history_api_is_paginated_and_allowlisted() -> None:
    principal = _principal()
    campaign_id = uuid4()
    vote_id = uuid4()
    work_id = uuid4()

    class StubHistoryService:
        async def list(
            self, received: AuthPrincipal, **kwargs: object
        ) -> tuple[list[VoteHistoryItem], int]:
            assert received.user_id == principal.user_id
            assert kwargs["page"] == 2
            return (
                [
                    VoteHistoryItem(
                        vote_id=vote_id,
                        campaign_id=campaign_id,
                        campaign_name="Bình chọn tháng 8",
                        campaign_slug="binh-chon-thang-8",
                        work_id=work_id,
                        work_title="Tác phẩm an toàn",
                        work_slug="tac-pham-an-toan",
                        status=VoteStatus.VALID,
                        created_at=NOW,
                        revoked_at=None,
                        can_change=True,
                        can_revoke=False,
                    )
                ],
                21,
            )

    app = create_application()
    app.dependency_overrides[get_current_principal] = lambda: principal
    app.dependency_overrides[get_vote_history_service] = lambda: StubHistoryService()
    with TestClient(app) as client:
        response = client.get("/api/v1/me/votes?page=2&pageSize=10")

    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["page"] == 2
    assert body["meta"]["pageSize"] == 10
    assert body["meta"]["total"] == 21
    assert body["data"][0]["voteId"] == str(vote_id)
    assert body["data"][0]["canChange"] is True
    assert "user" not in response.text.lower()
    assert "fingerprint" not in response.text.lower()


def test_vote_mutation_rejects_missing_csrf_before_service_call() -> None:
    principal = _principal()
    called = False

    class StubService:
        async def create_vote(self, *_args: object, **_kwargs: object) -> Never:
            nonlocal called
            called = True
            raise AssertionError("service must not be called")

    app = create_application()
    app.dependency_overrides[get_current_principal] = lambda: principal
    app.dependency_overrides[get_voting_service] = lambda: StubService()
    app.dependency_overrides[enforce_voting_rate_limit] = lambda: None
    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/campaigns/{uuid4()}/works/{uuid4()}/votes",
            headers={"Idempotency-Key": "csrf-test-key"},
        )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CSRF_VALIDATION_FAILED"
    assert called is False
