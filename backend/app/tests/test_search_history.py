import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.modules.auth.models import User, UserStatus
from app.modules.search.history_service import SearchHistoryService


def test_search_history_is_opt_in_deduplicated_and_owner_scoped(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'search-history.sqlite3').as_posix()}"
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        first_user_id = uuid4()
        second_user_id = uuid4()
        async with factory() as session:
            session.add_all(
                [
                    User(
                        id=first_user_id,
                        email="first@tmigroup.vn",
                        password_hash="hash",
                        status=UserStatus.ACTIVE,
                    ),
                    User(
                        id=second_user_id,
                        email="second@tmigroup.vn",
                        password_hash="hash",
                        status=UserStatus.ACTIVE,
                    ),
                ]
            )
            await session.commit()
            service = SearchHistoryService(session, retention_days=90)

            assert (await service.get(first_user_id)).is_enabled is False
            assert await service.record(first_user_id, "Sơn mài") is False

            await service.set_consent(first_user_id, enabled=True)
            await service.set_consent(second_user_id, enabled=True)
            assert await service.record(first_user_id, "  Sơn   mài  ") is True
            assert await service.record(first_user_id, "Sơn mài") is True
            assert await service.record(second_user_id, "Di sản số") is True

            first = await service.get(first_user_id)
            second = await service.get(second_user_id)
            assert [item.display_query for item in first.items] == ["Sơn mài"]
            assert [item.display_query for item in second.items] == ["Di sản số"]

            assert await service.clear(first_user_id) == 1
            assert (await service.get(first_user_id)).items == ()
            assert len((await service.get(second_user_id)).items) == 1
        await engine.dispose()

    asyncio.run(exercise())


def test_search_history_retention_and_consent_revocation_delete_data(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'retention.sqlite3').as_posix()}"
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        user_id = uuid4()
        now = datetime(2026, 8, 1, tzinfo=UTC)
        async with factory() as session:
            session.add(
                User(
                    id=user_id,
                    email="owner@tmigroup.vn",
                    password_hash="hash",
                    status=UserStatus.ACTIVE,
                )
            )
            await session.commit()
            old_service = SearchHistoryService(
                session,
                retention_days=90,
                clock=lambda: now - timedelta(days=91),
            )
            await old_service.set_consent(user_id, enabled=True)
            await old_service.record(user_id, "Truy vấn cũ")

            current_service = SearchHistoryService(
                session,
                retention_days=90,
                clock=lambda: now,
            )
            assert await current_service.purge_expired() == 1
            await current_service.record(user_id, "Truy vấn mới")
            assert len((await current_service.get(user_id)).items) == 1

            state = await current_service.set_consent(user_id, enabled=False)
            assert state.is_enabled is False
            assert state.items == ()
        await engine.dispose()

    asyncio.run(exercise())
