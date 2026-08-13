import asyncio
import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from alembic import command
from app.core.config import get_settings
from app.db.base import Base
from app.modules.auth.models import AuthIdentity, AuthProvider, User, UserStatus
from app.modules.auth.repositories import AuthRepository

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_oauth_identity_repository_uses_provider_subject_and_no_tokens(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'identity.sqlite3').as_posix()}"
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            async with session.begin():
                user = User(
                    email="viewer@example.test",
                    password_hash=None,
                    status=UserStatus.ACTIVE,
                )
                session.add(user)
                await session.flush()
                identity = AuthIdentity(
                    user_id=user.id,
                    provider=AuthProvider.GOOGLE,
                    provider_subject="google-subject-001",
                )
                repository = AuthRepository(session)
                repository.add_identity(identity)
                user_id = user.id
            found = await repository.get_identity(
                provider=AuthProvider.GOOGLE,
                subject="google-subject-001",
            )
            assert found is not None and found.user_id == user.id
            assert (
                await repository.get_identity_for_user(
                    user_id=user.id,
                    provider=AuthProvider.GOOGLE,
                )
                == found
            )
            assert "access_token" not in AuthIdentity.__table__.c
            assert "id_token" not in AuthIdentity.__table__.c
            assert "refresh_token" not in AuthIdentity.__table__.c

            await session.rollback()
            with pytest.raises(IntegrityError):
                async with session.begin():
                    other_user = User(
                        email="other@example.test",
                        password_hash=None,
                        status=UserStatus.ACTIVE,
                    )
                    session.add(other_user)
                    await session.flush()
                    session.add(
                        AuthIdentity(
                            user_id=other_user.id,
                            provider=AuthProvider.GOOGLE,
                            provider_subject="google-subject-001",
                        )
                    )
            await session.rollback()
            with pytest.raises(IntegrityError):
                async with session.begin():
                    session.add(
                        AuthIdentity(
                            user_id=user_id,
                            provider=AuthProvider.GOOGLE,
                            provider_subject="google-subject-002",
                        )
                    )
        await engine.dispose()

    asyncio.run(scenario())


def test_oauth_identity_migration_is_reversible(tmp_path: Path) -> None:
    database_path = tmp_path / "oauth-identity-migration.sqlite3"
    config = Config(BACKEND_ROOT / "alembic.ini")
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setenv(
            "DATABASE_DIRECT_URL",
            f"sqlite+aiosqlite:///{database_path.as_posix()}",
        )
        get_settings.cache_clear()
        command.upgrade(config, "0018_search_foundation")
        command.upgrade(config, "0019_oauth_identities")
        with sqlite3.connect(database_path) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            user_columns = {
                row[1]: row[3] for row in connection.execute("PRAGMA table_info(users)")
            }
            identity_indexes = {
                row[1]
                for row in connection.execute("PRAGMA index_list(auth_identities)")
            }
        assert "auth_identities" in tables
        assert user_columns["password_hash"] == 0
        assert {
            "uq_auth_identities_provider_subject",
            "uq_auth_identities_user_provider",
        }.issubset(identity_indexes)

        command.downgrade(config, "0018_search_foundation")
        with sqlite3.connect(database_path) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            user_columns = {
                row[1]: row[3] for row in connection.execute("PRAGMA table_info(users)")
            }
        assert "auth_identities" not in tables
        assert user_columns["password_hash"] == 1
    get_settings.cache_clear()
