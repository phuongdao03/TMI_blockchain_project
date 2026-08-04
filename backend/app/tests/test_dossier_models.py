import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.base import Base
from app.modules.auth.models import User, UserStatus
from app.modules.dossiers.models import (
    Category,
    Dossier,
    DossierStatus,
    DossierVersion,
)


async def _database() -> tuple[
    async_sessionmaker[AsyncSession],
    AsyncEngine,
]:
    engine = create_async_engine("sqlite+aiosqlite://")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return session_factory, engine


def test_dossier_status_defaults_to_draft_and_is_not_publicly_assignable() -> None:
    async def exercise() -> None:
        session_factory, engine = await _database()
        user = User(
            id=uuid4(),
            email="owner@tmigroup.vn",
            password_hash="not-used",
            status=UserStatus.ACTIVE,
        )
        category = Category(
            id=uuid4(),
            code="DIGITAL_INTELLECTUAL_ASSET",
            name="Tài sản trí tuệ số",
        )
        dossier = Dossier(
            id=uuid4(),
            code="DOS-000001",
            owner_user_id=user.id,
            category_id=category.id,
            title="Tác phẩm thử nghiệm",
        )
        async with session_factory() as session:
            session.add_all([user, category, dossier])
            await session.commit()
            stored = await session.scalar(
                select(Dossier).where(Dossier.status == DossierStatus.DRAFT)
            )

        assert dossier.status is DossierStatus.DRAFT
        assert stored is dossier
        with pytest.raises(AttributeError):
            dossier.status = DossierStatus.SUBMITTED

        await engine.dispose()

    asyncio.run(exercise())


def test_category_and_dossier_codes_are_unique() -> None:
    async def exercise() -> None:
        session_factory, engine = await _database()
        user = User(
            id=uuid4(),
            email="owner@tmigroup.vn",
            password_hash="not-used",
            status=UserStatus.ACTIVE,
        )
        category = Category(id=uuid4(), code="ASSET", name="Tài sản")
        user_id = user.id
        category_id = category.id
        async with session_factory() as session:
            session.add_all([user, category])
            await session.commit()
            session.add(Category(id=uuid4(), code="ASSET", name="Trùng mã"))
            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()

            session.add_all(
                [
                    Dossier(
                        id=uuid4(),
                        code="DOS-UNIQUE",
                        owner_user_id=user_id,
                        category_id=category_id,
                        title="Hồ sơ một",
                    ),
                    Dossier(
                        id=uuid4(),
                        code="DOS-UNIQUE",
                        owner_user_id=user_id,
                        category_id=category_id,
                        title="Hồ sơ hai",
                    ),
                ]
            )
            with pytest.raises(IntegrityError):
                await session.commit()

        await engine.dispose()

    asyncio.run(exercise())


def test_version_number_is_unique_within_each_dossier() -> None:
    async def exercise() -> None:
        session_factory, engine = await _database()
        user = User(
            id=uuid4(),
            email="owner@tmigroup.vn",
            password_hash="not-used",
            status=UserStatus.ACTIVE,
        )
        category = Category(id=uuid4(), code="ASSET", name="Tài sản")
        dossier = Dossier(
            id=uuid4(),
            code="DOS-VERSIONED",
            owner_user_id=user.id,
            category_id=category.id,
            title="Hồ sơ phiên bản",
        )
        async with session_factory() as session:
            session.add_all([user, category, dossier])
            await session.commit()
            session.add_all(
                [
                    DossierVersion(
                        id=uuid4(),
                        dossier_id=dossier.id,
                        version_no=1,
                        snapshot_json={"title": dossier.title},
                        canonical_hash="a" * 64,
                        submitted_by=user.id,
                    ),
                    DossierVersion(
                        id=uuid4(),
                        dossier_id=dossier.id,
                        version_no=1,
                        snapshot_json={"title": dossier.title},
                        canonical_hash="b" * 64,
                        submitted_by=user.id,
                    ),
                ]
            )
            with pytest.raises(IntegrityError):
                await session.commit()

        await engine.dispose()

    asyncio.run(exercise())
