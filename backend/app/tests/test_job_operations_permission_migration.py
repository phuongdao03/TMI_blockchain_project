import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_job_operations_permission_migration_is_reversible(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "job-operations-permission.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")

    command.upgrade(config, "0050_job_operations_permission")
    with sqlite3.connect(database_path) as connection:
        mapping = connection.execute(
            "SELECT r.code, p.code FROM role_permissions rp "
            "JOIN roles r ON r.id = rp.role_id "
            "JOIN permissions p ON p.id = rp.permission_id "
            "WHERE p.code = 'operations.jobs.manage'"
        ).fetchall()
    assert mapping == [("SUPER_ADMIN", "operations.jobs.manage")]

    command.downgrade(config, "0049_durable_jobs")
    with sqlite3.connect(database_path) as connection:
        remaining = connection.execute(
            "SELECT count(*) FROM permissions WHERE code = 'operations.jobs.manage'"
        ).fetchone()
    assert remaining == (0,)
    get_settings.cache_clear()
