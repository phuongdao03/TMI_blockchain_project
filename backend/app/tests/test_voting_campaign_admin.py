import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.main import create_application
from app.modules.audit.models import AuditLog
from app.modules.audit.service import AuditService
from app.modules.auth.dependencies import (
    get_csrf_protected_principal,
    get_current_principal,
)
from app.modules.auth.models import Permission, Role, RolePermission, User, UserRole
from app.modules.auth.repositories import AuthRepository
from app.modules.auth.security import OutboxPayloadCipher
from app.modules.auth.session_service import AuthPrincipal
from app.modules.voting.dependencies import get_voting_campaign_service
from app.modules.voting.errors import (
    VotingCampaignForbiddenError,
    VotingCampaignRulesLockedError,
    VotingCampaignSlugConflictError,
)
from app.modules.voting.models import (
    CampaignEvent,
    CampaignStatus,
    CampaignType,
    PeriodType,
    VotingCampaign,
)
from app.modules.voting.schemas import VotingCampaignRequest
from app.modules.voting.service import (
    CAMPAIGN_MANAGE_PERMISSION,
    CAMPAIGN_READ_PERMISSION,
    VotingCampaignInput,
    VotingCampaignService,
)

NOW = datetime(2026, 8, 3, 8, tzinfo=UTC)


def _principal(*permissions: str) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="campaign-admin@example.test",
        roles=("CONTENT_ADMIN",),
        permissions=permissions,
    )


def _input(*, slug: str = "thang-tam") -> VotingCampaignInput:
    return VotingCampaignInput(
        name="Bình chọn tháng tám",
        slug=slug,
        description="Chiến dịch cộng đồng",
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
        min_account_age_hours=24,
        eligibility_rules={"organization_ids": [], "allowed_roles": []},
    )


def test_campaign_request_rejects_invalid_rules() -> None:
    payload = {
        "name": "Campaign",
        "slug": "campaign",
        "description": "Description",
        "campaignType": "SPECIAL",
        "periodType": "MONTHLY",
        "timezone": "Invalid/Timezone",
        "startAt": "2026-08-05T00:00:00",
        "endAt": "2026-08-04T00:00:00+00:00",
        "maxVotesPerUser": 1,
    }
    with pytest.raises(ValidationError):
        VotingCampaignRequest.model_validate(payload)


def test_auth_repository_hydrates_voting_permissions(tmp_path: Path) -> None:
    async def exercise() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'permissions.sqlite3').as_posix()}"
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        user = User(
            id=uuid4(),
            email="permission-user@example.test",
            password_hash="not-used",
        )
        role = Role(id=uuid4(), code="CONTENT_ADMIN")
        permission = Permission(id=uuid4(), code=CAMPAIGN_MANAGE_PERMISSION)
        async with factory() as session:
            session.add_all(
                [
                    user,
                    role,
                    permission,
                    UserRole(user_id=user.id, role_id=role.id),
                    RolePermission(
                        role_id=role.id,
                        permission_id=permission.id,
                    ),
                ]
            )
            await session.commit()
            assert await AuthRepository(session).get_permission_codes(user.id) == (
                CAMPAIGN_MANAGE_PERMISSION,
            )
        await engine.dispose()

    asyncio.run(exercise())


def test_campaign_service_enforces_permissions_draft_lock_and_audit(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'campaign-admin.sqlite3').as_posix()}"
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            service = VotingCampaignService(
                session=session,
                audit=AuditService(session),
                payload_cipher=OutboxPayloadCipher(
                    key=b"v" * 32,
                    key_id="voting-test-key",
                ),
            )
            with pytest.raises(VotingCampaignForbiddenError):
                await service.create(_principal(), _input(), request_id="forbidden")

            principal = _principal(
                CAMPAIGN_READ_PERMISSION,
                CAMPAIGN_MANAGE_PERMISSION,
            )
            campaign = await service.create(
                principal,
                _input(),
                request_id="create-request",
            )
            assert campaign.status is CampaignStatus.DRAFT
            campaign_id = campaign.id
            with pytest.raises(VotingCampaignSlugConflictError):
                await service.create(
                    principal,
                    _input(),
                    request_id="duplicate-request",
                )
            updated = await service.update(
                principal,
                campaign_id,
                _input(slug="thang-tam-cap-nhat"),
                request_id="update-request",
            )
            assert updated.slug == "thang-tam-cap-nhat"

            audit_rows = tuple((await session.scalars(select(AuditLog))).all())
            event_rows = tuple((await session.scalars(select(CampaignEvent))).all())
            assert [row.action for row in audit_rows] == [
                "voting.campaign.created",
                "voting.campaign.updated",
            ]
            assert audit_rows[1].before_json is not None
            assert audit_rows[1].after_json is not None
            assert audit_rows[1].before_json["slug"] == "thang-tam"
            assert audit_rows[1].after_json["slug"] == "thang-tam-cap-nhat"
            assert [row.event_type for row in event_rows] == [
                "CAMPAIGN_CREATED",
                "CAMPAIGN_UPDATED",
            ]

            await session.commit()
            async with session.begin():
                updated.status = CampaignStatus.ACTIVE
            with pytest.raises(VotingCampaignRulesLockedError):
                await service.update(
                    principal,
                    updated.id,
                    _input(slug="khong-duoc-sua"),
                    request_id="locked-request",
                )
        await engine.dispose()

    asyncio.run(exercise())


class StubCampaignService:
    def __init__(self) -> None:
        self.created_input: VotingCampaignInput | None = None
        self.row = VotingCampaign(
            id=uuid4(),
            name="Campaign",
            slug="campaign",
            description="Description",
            status=CampaignStatus.DRAFT,
            campaign_type=CampaignType.PERIODIC,
            period_type=PeriodType.MONTHLY,
            timezone="Asia/Ho_Chi_Minh",
            start_at=NOW + timedelta(days=1),
            end_at=NOW + timedelta(days=31),
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

    async def list(
        self, *_args: object, **_kwargs: object
    ) -> tuple[tuple[VotingCampaign, ...], int]:
        return (self.row,), 1

    async def get(self, _principal: object, campaign_id: UUID) -> VotingCampaign:
        assert campaign_id == self.row.id
        return self.row

    async def create(
        self,
        _principal: object,
        payload: VotingCampaignInput,
        **_kwargs: object,
    ) -> VotingCampaign:
        self.created_input = payload
        return self.row

    async def update(
        self,
        _principal: object,
        campaign_id: UUID,
        *_args: object,
        **_kwargs: object,
    ) -> VotingCampaign:
        assert campaign_id == self.row.id
        return self.row


def test_campaign_admin_api_contract_and_validation() -> None:
    service = StubCampaignService()
    principal = _principal(CAMPAIGN_READ_PERMISSION, CAMPAIGN_MANAGE_PERMISSION)
    app = create_application()
    app.dependency_overrides[get_voting_campaign_service] = lambda: service
    app.dependency_overrides[get_current_principal] = lambda: principal
    app.dependency_overrides[get_csrf_protected_principal] = lambda: principal
    organization_id = uuid4()
    payload = {
        "name": "Campaign",
        "slug": "campaign",
        "description": "Description",
        "campaignType": "PERIODIC",
        "periodType": "MONTHLY",
        "timezone": "Asia/Ho_Chi_Minh",
        "startAt": "2026-08-04T08:00:00Z",
        "endAt": "2026-09-03T08:00:00Z",
        "maxVotesPerUser": 3,
        "eligibilityRules": {
            "organizationIds": [str(organization_id)],
            "allowedRoles": [],
        },
    }
    try:
        with TestClient(app) as client:
            created = client.post("/api/v1/admin/voting/campaigns", json=payload)
            listed = client.get("/api/v1/admin/voting/campaigns")
            detail = client.get(f"/api/v1/admin/voting/campaigns/{service.row.id}")
            invalid = client.post(
                "/api/v1/admin/voting/campaigns",
                json={**payload, "unexpected": "mass-assignment"},
            )
        assert created.status_code == 201
        assert service.created_input is not None
        assert service.created_input.eligibility_rules["organization_ids"] == [
            str(organization_id)
        ]
        assert listed.status_code == 200
        assert detail.status_code == 200
        assert set(created.json()["data"]) == {
            "id",
            "name",
            "slug",
            "description",
            "status",
            "campaignType",
            "periodType",
            "timezone",
            "startAt",
            "endAt",
            "maxVotesPerUser",
            "maxVotesPerWorkPerUser",
            "allowVoteChange",
            "allowVoteRevoke",
            "requireVerifiedEmail",
            "minAccountAgeHours",
            "eligibilityRules",
            "ruleVersion",
            "createdBy",
            "createdAt",
            "updatedAt",
        }
        assert invalid.status_code == 422
        assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"
    finally:
        app.dependency_overrides.clear()
