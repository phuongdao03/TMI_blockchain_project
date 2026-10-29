import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.errors import DomainError
from app.db.base import Base
from app.modules.audit.models import AuditLog
from app.modules.auth.models import (
    Permission,
    Role,
    RolePermission,
    User,
    UserPermission,
    UserRole,
    UserStatus,
)
from app.modules.hr.models import Department, Employee
from app.modules.notifications.models import Notification
from app.modules.promotions.distribution import PromotionDistributionService
from app.modules.promotions.distribution_models import (
    PromotionAudiencePreview,
    PromotionDistributionJob,
)
from app.modules.promotions.models import VoucherCampaign, VoucherClaim


async def _fixture():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda c: Base.metadata.create_all(
                c,
                tables=[
                    User.__table__,
                    Role.__table__,
                    Permission.__table__,
                    UserPermission.__table__,
                    RolePermission.__table__,
                    UserRole.__table__,
                    Department.__table__,
                    Employee.__table__,
                    VoucherCampaign.__table__,
                    VoucherClaim.__table__,
                    AuditLog.__table__,
                    Notification.__table__,
                    PromotionAudiencePreview.__table__,
                    PromotionDistributionJob.__table__,
                ],
            )
        )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        admin, first, second, excluded = uuid4(), uuid4(), uuid4(), uuid4()
        role = Role(code="USER")
        session.add(role)
        session.add_all(
            [
                User(id=value, email=f"{value}@example.vn", status=UserStatus.ACTIVE)
                for value in (admin, first, second, excluded)
            ]
        )
        await session.flush()
        session.add_all(
            [
                UserRole(user_id=first, role_id=role.id),
                UserRole(user_id=second, role_id=role.id),
            ]
        )
        campaign = VoucherCampaign(
            code="MANUAL_TEST",
            title="Tri ân",
            description="Quà tặng",
            terms="Không đổi thành tiền",
            image_path="/voucher.png",
            amount_vnd=200000,
            validity_days=60,
            active=True,
            status="ACTIVE",
            program_type="MANUAL",
            policy_json={},
            policy_version=1,
        )
        session.add(campaign)
        await session.commit()
        campaign_id = campaign.id
    return engine, factory, admin, first, second, excluded, campaign_id


def test_preview_reports_excluded_invalid_duplicate_ids_and_binds_actor():
    async def scenario():
        engine, factory, admin, first, second, excluded, campaign_id = await _fixture()
        async with factory() as session:
            service = PromotionDistributionService(session)
            selection = [str(first), str(first), "invalid", str(second), str(excluded)]
            preview = await service.preview(
                campaign_id, actor_id=admin, user_ids=selection
            )
            assert preview["eligibleCount"] == 2
            assert preview["excludedCount"] == 3
            assert preview["exclusionReasons"]["DUPLICATE_USER_ID"] == 1
            token = UUID(preview["previewToken"])
            with pytest.raises(DomainError):
                await service.issue(
                    campaign_id,
                    actor_id=first,
                    preview_token=token,
                    idempotency_key="wrong-actor",
                    reason="Manual campaign distribution",
                    user_ids=selection,
                )
            with pytest.raises(DomainError):
                await service.issue(
                    campaign_id,
                    actor_id=admin,
                    preview_token=token,
                    idempotency_key="wrong-selector",
                    reason="Manual campaign distribution",
                    user_ids=[str(first)],
                )
        await engine.dispose()

    asyncio.run(scenario())


def test_preview_expiry_and_campaign_version_are_rechecked():
    async def scenario():
        engine, factory, admin, first, _, _, campaign_id = await _fixture()
        async with factory() as session:
            service = PromotionDistributionService(session)
            preview = await service.preview(
                campaign_id, actor_id=admin, user_ids=[str(first)]
            )
            row = await session.get(
                PromotionAudiencePreview, UUID(preview["previewToken"])
            )
            row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
            await session.commit()
            with pytest.raises(DomainError):
                await service.issue(
                    campaign_id,
                    actor_id=admin,
                    preview_token=row.id,
                    idempotency_key="expired-token",
                    reason="Manual distribution",
                    user_ids=[str(first)],
                )
        await engine.dispose()

    asyncio.run(scenario())


def test_job_retries_do_not_duplicate_and_worker_rechecks_recipient():
    async def scenario():
        engine, factory, admin, first, second, _, campaign_id = await _fixture()
        async with factory() as session:
            service = PromotionDistributionService(session)
            selection = [str(first), str(second)]
            preview = await service.preview(
                campaign_id, actor_id=admin, user_ids=selection
            )
            options = dict(
                actor_id=admin,
                preview_token=UUID(preview["previewToken"]),
                idempotency_key="replayed-bulk-job",
                reason="Manual distribution",
                user_ids=selection,
            )
            job = await service.issue(campaign_id, **options)
            assert (await service.issue(campaign_id, **options)).id == job.id
            user = await session.get(User, second)
            user.status = UserStatus.SUSPENDED
            await session.commit()
            assert not await service.run_batch(job.id, batch_size=1)
            assert await service.run_batch(job.id, batch_size=1)
            assert await service.run_batch(job.id)
            await session.refresh(job)
            assert job.issued_count == 1 and job.skipped_count == 1 and job.cursor == 2
            assert (
                await session.scalar(select(func.count()).select_from(VoucherClaim))
                == 1
            )
            assert (
                await session.scalar(
                    select(func.count()).select_from(PromotionDistributionJob)
                )
                == 1
            )
        await engine.dispose()

    asyncio.run(scenario())
