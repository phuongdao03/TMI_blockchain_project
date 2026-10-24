import asyncio
import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base

# Import related models so Base metadata includes all referenced tables.
from app.modules import memberships as membership_models  # noqa: F401
from app.modules import organizations as organization_models  # noqa: F401
from app.modules.advertising.errors import AdvertisingConflictError
from app.modules.advertising.inventory import AdvertisingInventoryService
from app.modules.advertising.models import (
    AdvertisingDiscountPolicy,
    AdvertisingPackage,
    AdvertisingPlacement,
    AdvertisingReservation,
)
from app.modules.auth.models import User, UserStatus
from app.modules.auth.session_service import AuthPrincipal
from app.modules.dossiers.models import Category, Dossier, DossierStatus
from app.modules.wallet import models as wallet_models  # noqa: F401

TEST_DATABASE_URL = os.getenv("ADVERTISING_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="Set ADVERTISING_TEST_DATABASE_URL to a disposable PostgreSQL database.",
)


def test_postgres_serializes_simultaneous_final_slot_reservations() -> None:
    assert TEST_DATABASE_URL is not None
    if make_url(TEST_DATABASE_URL).get_backend_name() != "postgresql":
        pytest.skip("Advertising concurrency test requires PostgreSQL row locks.")

    async def exercise() -> None:
        schema = f"advertising_test_{uuid4().hex}"
        schema_engine = create_async_engine(TEST_DATABASE_URL)
        async with schema_engine.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        await schema_engine.dispose()

        engine = create_async_engine(
            TEST_DATABASE_URL,
            connect_args={"server_settings": {"search_path": schema}},
        )
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)

            owner_ids = [uuid4(), uuid4()]
            dossier_ids = [uuid4(), uuid4()]
            category = Category(id=uuid4(), code=f"AD-{uuid4().hex[:10]}", name="Test")
            placement = AdvertisingPlacement(
                code=f"AD-{uuid4().hex[:10]}",
                name="Concurrent slot",
                page_location="Test",
                delivery_mode="EQUAL_ROTATION",
                capacity=1,
            )
            package = AdvertisingPackage(
                code=f"AD-{uuid4().hex[:10]}",
                name="Concurrent package",
                placement_id=placement.id,
                duration_hours=24,
                base_price_vnd=1_000,
                price_version=1,
                active=True,
            )
            admin_id = uuid4()
            async with sessions() as session, session.begin():
                session.add_all(
                    [
                        category,
                        placement,
                        package,
                        AdvertisingDiscountPolicy(
                            tier="MEMBER",
                            rate_basis_points=0,
                            annual_allowance_vnd=0,
                            policy_version=1,
                            active=True,
                        ),
                        User(
                            id=admin_id,
                            email=f"admin-{uuid4().hex[:8]}@example.test",
                            password_hash="test-only",
                            status=UserStatus.ACTIVE,
                        ),
                    ]
                )
                for index, owner_id in enumerate(owner_ids):
                    session.add_all(
                        [
                            User(
                                id=owner_id,
                                email=f"owner-{uuid4().hex[:8]}@example.test",
                                password_hash="test-only",
                                status=UserStatus.ACTIVE,
                            ),
                            Dossier(
                                id=dossier_ids[index],
                                code=f"DOS-{uuid4().hex[:10]}",
                                owner_user_id=owner_id,
                                category_id=category.id,
                                title="Approved test dossier",
                                _status=DossierStatus.APPROVED,
                            ),
                        ]
                    )

            principals = [
                AuthPrincipal(
                    user_id=owner_id,
                    session_id=uuid4(),
                    email=f"owner-{index}@example.test",
                    roles=("USER",),
                )
                for index, owner_id in enumerate(owner_ids)
            ]
            admin = AuthPrincipal(
                user_id=admin_id,
                session_id=uuid4(),
                email="admin@example.test",
                roles=("SUPER_ADMIN",),
            )
            campaign_ids = []
            for index, principal in enumerate(principals):
                inventory = AdvertisingInventoryService(sessions)
                campaign = await inventory.create_campaign(
                    principal,
                    dossier_id=dossier_ids[index],
                    package_code=package.code,
                    title=f"Campaign {index}",
                    description="Concurrency test",
                    image_url=None,
                    destination_url="/",
                )
                campaign_id = campaign.id
                await inventory.submit_campaign(principal, campaign_id)
                await inventory.review_campaign(admin, campaign_id, approve=True)
                campaign_ids.append(campaign_id)

            starts_at = datetime.now(UTC) + timedelta(days=2)

            async def reserve(index: int) -> object:
                async with sessions() as session:
                    return await AdvertisingInventoryService(session).reserve(
                        principals[index],
                        campaign_id=campaign_ids[index],
                        start_at=starts_at,
                        idempotency_key=f"concurrent-{index}",
                    )

            results = await asyncio.gather(
                reserve(0), reserve(1), return_exceptions=True
            )
            assert (
                sum(isinstance(result, AdvertisingReservation) for result in results)
                == 1
            )
            conflicts = [
                result
                for result in results
                if isinstance(result, AdvertisingConflictError)
            ]
            assert len(conflicts) == 1
            async with sessions() as session:
                holds = list(
                    await session.scalars(
                        select(AdvertisingReservation).where(
                            AdvertisingReservation.placement_id == placement.id,
                            AdvertisingReservation.status == "HELD",
                        )
                    )
                )
                assert len(holds) == 1
        finally:
            await engine.dispose()
            cleanup_engine = create_async_engine(TEST_DATABASE_URL)
            async with cleanup_engine.begin() as connection:
                await connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            await cleanup_engine.dispose()

    asyncio.run(exercise())
