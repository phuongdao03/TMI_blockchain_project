import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.modules.auth.models import User, UserStatus
from app.modules.billing.errors import PriceCatalogConflictError
from app.modules.billing.fees import FeePolicyService
from app.modules.billing.models import FeePolicyStatus
from app.modules.dossiers.models import Category, DossierType
from app.modules.media.models import MediaAsset  # noqa: F401

NOW = datetime(2026, 11, 7, 8, 0, tzinfo=UTC)


async def _database():
    engine = create_async_engine("sqlite+aiosqlite://")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    users = [
        User(
            id=uuid4(),
            email=f"fee-{index}@example.test",
            password_hash="not-used",
            status=UserStatus.ACTIVE,
        )
        for index in range(2)
    ]
    category = Category(id=uuid4(), code="FEE_TEST", name="Fee test")
    dossier_type = DossierType(
        id=uuid4(), category_id=category.id, code="FEE_TEST", name="Fee test"
    )
    async with sessions() as session:
        session.add_all([*users, category, dossier_type])
        await session.commit()
    return engine, sessions, users, dossier_type


def test_policy_resolution_uses_half_open_utc_interval() -> None:
    async def exercise() -> None:
        engine, sessions, users, dossier_type = await _database()
        next_day = NOW + timedelta(days=1)
        async with sessions() as session:
            service = FeePolicyService(session, clock=lambda: NOW)
            first = await service.create_draft(
                actor_user_id=users[0].id,
                fee_type="CERTIFICATE_ISSUANCE",
                dossier_type_id=dossier_type.id,
                amount_minor=5_000_000,
                starts_at=NOW,
                ends_at=next_day,
                reason="Approved staging policy",
            )
            await service.approve(first.id, actor_user_id=users[1].id)
            assert (
                await service.resolve(
                    fee_type="CERTIFICATE_ISSUANCE",
                    dossier_type_id=dossier_type.id,
                    at=NOW,
                )
            ).id == first.id
            assert (
                await service.resolve(
                    fee_type="CERTIFICATE_ISSUANCE",
                    dossier_type_id=dossier_type.id,
                    at=next_day,
                )
                is None
            )
        await engine.dispose()

    asyncio.run(exercise())


def test_submission_policy_is_global_and_versions_share_one_scope() -> None:
    async def exercise() -> None:
        engine, sessions, users, dossier_type = await _database()
        next_day = NOW + timedelta(days=1)
        async with sessions() as session:
            service = FeePolicyService(session, clock=lambda: NOW)
            first_draft = await service.create_draft(
                actor_user_id=users[0].id,
                fee_type="DOSSIER_SUBMISSION",
                dossier_type_id=None,
                amount_minor=5_000_000,
                starts_at=NOW,
                ends_at=None,
                reason="Global submission policy",
            )
            first = await service.approve(
                first_draft.id,
                actor_user_id=users[1].id,
                confirm_activation=True,
            )
            assert first.dossier_type_id is None
            assert (
                await service.resolve(
                    fee_type="DOSSIER_SUBMISSION",
                    dossier_type_id=None,
                    at=NOW,
                )
            ).id == first.id
            assert (
                await service.resolve(
                    fee_type="DOSSIER_SUBMISSION",
                    dossier_type_id=dossier_type.id,
                    at=NOW,
                )
                is None
            )

        async with sessions() as session:
            service = FeePolicyService(session, clock=lambda: next_day)
            second_draft = await service.create_draft(
                actor_user_id=users[0].id,
                fee_type="DOSSIER_SUBMISSION",
                dossier_type_id=None,
                amount_minor=6_000_000,
                starts_at=next_day,
                ends_at=None,
                reason="Global submission price update",
            )
            second = await service.approve(
                second_draft.id,
                actor_user_id=users[1].id,
                confirm_activation=True,
            )
            assert second.version_no == 2
            assert second.dossier_type_id is None
            predecessor = await service.get_policy(first.id, at=next_day)
            assert predecessor.ends_at == next_day
        await engine.dispose()

    asyncio.run(exercise())


def test_submission_policy_requires_explicit_confirmation_and_allows_creator() -> None:
    async def exercise() -> None:
        engine, sessions, users, _ = await _database()
        async with sessions() as session:
            service = FeePolicyService(session, clock=lambda: NOW)
            draft = await service.create_draft(
                actor_user_id=users[0].id,
                fee_type="DOSSIER_SUBMISSION",
                dossier_type_id=None,
                amount_minor=5_000_000,
                starts_at=NOW,
                ends_at=None,
                reason="Initial global submission fee",
            )
            with pytest.raises(PriceCatalogConflictError, match="confirmation"):
                await service.approve(draft.id, actor_user_id=users[0].id)

            active = await service.approve(
                draft.id,
                actor_user_id=users[0].id,
                confirm_activation=True,
            )
            assert active.status is FeePolicyStatus.ACTIVE
            assert active.created_by_user_id == users[0].id
            assert active.approved_by_user_id == users[0].id
        await engine.dispose()

    asyncio.run(exercise())


def test_other_fee_policies_keep_separation_of_duties() -> None:
    async def exercise() -> None:
        engine, sessions, users, dossier_type = await _database()
        async with sessions() as session:
            service = FeePolicyService(session, clock=lambda: NOW)
            draft = await service.create_draft(
                actor_user_id=users[0].id,
                fee_type="CERTIFICATE_ISSUANCE",
                dossier_type_id=dossier_type.id,
                amount_minor=5_000_000,
                starts_at=NOW,
                ends_at=None,
                reason="Certificate fee",
            )
            with pytest.raises(PriceCatalogConflictError, match="different approver"):
                await service.approve(
                    draft.id,
                    actor_user_id=users[0].id,
                    confirm_activation=True,
                )
        await engine.dispose()

    asyncio.run(exercise())


def test_policy_approval_requires_separation_of_duties_and_closes_predecessor() -> None:
    async def exercise() -> None:
        engine, sessions, users, dossier_type = await _database()
        async with sessions() as session:
            service = FeePolicyService(session, clock=lambda: NOW)
            first = await service.create_draft(
                actor_user_id=users[0].id,
                fee_type="CERTIFICATE_ISSUANCE",
                dossier_type_id=dossier_type.id,
                amount_minor=4_000_000,
                starts_at=NOW,
                ends_at=None,
                reason="First policy",
            )
            with pytest.raises(PriceCatalogConflictError, match="different approver"):
                await service.approve(first.id, actor_user_id=users[0].id)
            await service.approve(first.id, actor_user_id=users[1].id)
            overlapping = await service.create_draft(
                actor_user_id=users[0].id,
                fee_type="CERTIFICATE_ISSUANCE",
                dossier_type_id=dossier_type.id,
                amount_minor=6_000_000,
                starts_at=NOW + timedelta(days=1),
                ends_at=None,
                reason="Overlapping policy",
            )
            approved = await service.approve(overlapping.id, actor_user_id=users[1].id)
            predecessor = await service.get_policy(first.id, at=NOW)
            assert approved.status is FeePolicyStatus.SCHEDULED
            assert predecessor.ends_at == overlapping.starts_at
        await engine.dispose()

    asyncio.run(exercise())


def test_fee_policy_status_is_derived_from_effective_time() -> None:
    async def exercise() -> None:
        engine, sessions, users, dossier_type = await _database()
        async with sessions() as session:
            service = FeePolicyService(session, clock=lambda: NOW)
            draft = await service.create_draft(
                actor_user_id=users[0].id,
                fee_type="CERTIFICATE_ISSUANCE",
                dossier_type_id=dossier_type.id,
                amount_minor=1_250_000,
                starts_at=NOW + timedelta(days=1),
                ends_at=NOW + timedelta(days=2),
                reason="Scheduled policy",
            )
            assert draft.status is FeePolicyStatus.DRAFT
            scheduled = await service.approve(draft.id, actor_user_id=users[1].id)
            assert scheduled.status is FeePolicyStatus.SCHEDULED
            active = await service.get_policy(draft.id, at=NOW + timedelta(days=1))
            expired = await service.get_policy(draft.id, at=NOW + timedelta(days=2))
            assert active.status is FeePolicyStatus.ACTIVE
            assert expired.status is FeePolicyStatus.EXPIRED
        await engine.dispose()

    asyncio.run(exercise())


def test_draft_policy_can_be_cancelled_before_approval() -> None:
    async def exercise() -> None:
        engine, sessions, users, dossier_type = await _database()
        async with sessions() as session:
            service = FeePolicyService(session, clock=lambda: NOW)
            draft = await service.create_draft(
                actor_user_id=users[0].id,
                fee_type="CERTIFICATE_ISSUANCE",
                dossier_type_id=dossier_type.id,
                amount_minor=1_250_000,
                starts_at=NOW + timedelta(days=1),
                ends_at=None,
                reason="Draft for cancellation",
            )
            cancelled = await service.cancel(
                draft.id, actor_user_id=users[0].id, reason="No longer needed"
            )
            assert cancelled.status is FeePolicyStatus.CANCELLED
        await engine.dispose()

    asyncio.run(exercise())
