import asyncio
import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import DateTime
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import Mapped, mapped_column

from alembic import command
from app.core.config import Settings, get_settings
from app.db.base import Base, UtcTimestampMixin
from app.db.session import (
    DatabaseConfigurationError,
    create_runtime_engine,
    create_session_factory,
)

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class TimestampedRecord(UtcTimestampMixin, Base):
    __tablename__ = "timestamped_records"

    id: Mapped[int] = mapped_column(primary_key=True)


def test_settings_keep_pooled_and_direct_database_urls_separate() -> None:
    settings = Settings.model_validate(
        {
            "database_url": "postgresql+asyncpg://runtime.example/app",
            "database_direct_url": "postgresql+asyncpg://direct.example/app",
        }
    )

    assert settings.database_url is not None
    assert settings.database_direct_url is not None
    assert (
        settings.database_url.get_secret_value()
        == "postgresql+asyncpg://runtime.example/app"
    )
    assert (
        settings.database_direct_url.get_secret_value()
        == "postgresql+asyncpg://direct.example/app"
    )


def test_runtime_engine_requires_pooled_database_url() -> None:
    settings = Settings.model_validate({})

    with pytest.raises(DatabaseConfigurationError, match="DATABASE_URL"):
        create_runtime_engine(settings)


def test_session_factory_uses_async_sessions_without_expiring_state() -> None:
    async def verify_session_factory() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        session_factory = create_session_factory(engine)

        async with session_factory() as session:
            assert session.sync_session.expire_on_commit is False

        await engine.dispose()

    asyncio.run(verify_session_factory())


def test_timestamp_mixin_uses_timezone_aware_utc_columns() -> None:
    created_at = TimestampedRecord.__table__.c.created_at
    updated_at = TimestampedRecord.__table__.c.updated_at

    assert isinstance(created_at.type, DateTime)
    assert created_at.type.timezone is True
    assert created_at.server_default is not None
    assert isinstance(updated_at.type, DateTime)
    assert updated_at.type.timezone is True
    assert updated_at.server_default is not None
    assert updated_at.onupdate is not None


def test_baseline_migration_upgrades_and_downgrades(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "migration-smoke.sqlite3"
    direct_url = f"sqlite+aiosqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://runtime.invalid/app")
    monkeypatch.setenv("DATABASE_DIRECT_URL", direct_url)
    get_settings.cache_clear()

    config = Config(BACKEND_ROOT / "alembic.ini")
    command.upgrade(config, "0001_baseline")

    with sqlite3.connect(database_path) as connection:
        revision = connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()
    assert revision == ("0001_baseline",)

    command.downgrade(config, "base")

    with sqlite3.connect(database_path) as connection:
        revisions = connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchall()
    assert revisions == []

    get_settings.cache_clear()
