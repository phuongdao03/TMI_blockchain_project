import asyncio
import sqlite3
from pathlib import Path
from typing import cast
from uuid import uuid4

import pytest
from alembic.config import Config
from sqlalchemy import Table
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from alembic import command
from app.core.config import get_settings
from app.db.base import Base
from app.modules.auth.models import (
    AuthSession,
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
    UserStatus,
    VerificationToken,
)

BACKEND_ROOT = Path(__file__).resolve().parents[2]
AUTH_TABLES = {
    "auth_sessions",
    "permissions",
    "role_permissions",
    "roles",
    "user_roles",
    "users",
    "verification_tokens",
}
OUTBOX_TABLE = "outbox_events"


def test_auth_models_match_required_tables_and_security_columns() -> None:
    role_permission_table = cast(Table, RolePermission.__table__)
    user_role_table = cast(Table, UserRole.__table__)

    assert AUTH_TABLES <= set(Base.metadata.tables)
    assert set(UserStatus) == {
        UserStatus.PENDING,
        UserStatus.ACTIVE,
        UserStatus.SUSPENDED,
        UserStatus.DELETED,
    }

    assert User.__table__.c.email.unique is True
    assert Role.__table__.c.code.unique is True
    assert Permission.__table__.c.code.unique is True

    assert set(role_permission_table.primary_key.columns.keys()) == {
        "role_id",
        "permission_id",
    }
    assert set(user_role_table.primary_key.columns.keys()) == {
        "user_id",
        "role_id",
    }

    assert "refresh_token_hash" in AuthSession.__table__.c
    assert "refresh_token" not in AuthSession.__table__.c
    assert "token_hash" in VerificationToken.__table__.c
    assert "token" not in VerificationToken.__table__.c


def test_every_auth_foreign_key_has_explicit_deletion_behavior() -> None:
    foreign_keys = [
        foreign_key
        for table_name in AUTH_TABLES
        for foreign_key in Base.metadata.tables[table_name].foreign_keys
    ]

    assert foreign_keys
    assert all(foreign_key.ondelete is not None for foreign_key in foreign_keys)


def test_user_email_is_unique_without_case_sensitivity(tmp_path: Path) -> None:
    async def verify_unique_email() -> None:
        database_path = tmp_path / "auth-models.sqlite3"
        engine = create_async_engine(f"sqlite+aiosqlite:///{database_path.as_posix()}")
        session_factory = async_sessionmaker(engine, expire_on_commit=False)

        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        async with session_factory.begin() as session:
            session.add(
                User(
                    email="owner@tmigroup.vn",
                    password_hash="argon2id-hash-one",
                )
            )

        with pytest.raises(IntegrityError):
            async with session_factory.begin() as session:
                session.add(
                    User(
                        email="OWNER@TMIGROUP.VN",
                        password_hash="argon2id-hash-two",
                    )
                )

        await engine.dispose()

    asyncio.run(verify_unique_email())


def test_auth_migration_upgrades_and_downgrades(tmp_path: Path) -> None:
    database_path = tmp_path / "auth-migration.sqlite3"
    direct_url = f"sqlite+aiosqlite:///{database_path.as_posix()}"
    config = Config(BACKEND_ROOT / "alembic.ini")

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setenv("DATABASE_DIRECT_URL", direct_url)
        get_settings.cache_clear()
        command.upgrade(config, "head")

        with sqlite3.connect(database_path) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            connection.execute(
                """
                INSERT INTO users (id, email, password_hash, status)
                VALUES (?, ?, ?, ?)
                """,
                (
                    uuid4().hex,
                    "migration@tmigroup.vn",
                    "argon2id-hash-one",
                    "PENDING",
                ),
            )
            connection.commit()

        assert AUTH_TABLES <= tables
        assert OUTBOX_TABLE in tables
        with (
            sqlite3.connect(database_path) as connection,
            pytest.raises(sqlite3.IntegrityError),
        ):
            connection.execute(
                """
                INSERT INTO users (id, email, password_hash, status)
                VALUES (?, ?, ?, ?)
                """,
                (
                    uuid4().hex,
                    "MIGRATION@TMIGROUP.VN",
                    "argon2id-hash-two",
                    "PENDING",
                ),
            )

        command.downgrade(config, "0001_baseline")

        with sqlite3.connect(database_path) as connection:
            remaining_tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            revision = connection.execute(
                "SELECT version_num FROM alembic_version"
            ).fetchone()

        assert AUTH_TABLES.isdisjoint(remaining_tables)
        assert OUTBOX_TABLE not in remaining_tables
        assert revision == ("0001_baseline",)

    get_settings.cache_clear()


def test_auth_table_indexes_cover_session_and_token_lookups() -> None:
    expected_indexes = {
        "ix_auth_sessions_user_id_expires_at",
        "ix_verification_tokens_user_id_purpose",
    }
    tables = (
        cast(Table, AuthSession.__table__),
        cast(Table, VerificationToken.__table__),
    )
    actual_indexes = {index.name for table in tables for index in table.indexes}

    assert expected_indexes <= actual_indexes
