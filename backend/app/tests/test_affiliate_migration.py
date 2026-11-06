import hashlib
import runpy
import sqlite3
from pathlib import Path
from uuid import uuid4

from alembic.config import Config
from sqlalchemy.dialects import postgresql

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]
REVISION = "0156_affiliate_foundation"


def test_affiliate_backfill_binds_active_status_as_postgresql_enum() -> None:
    migration = runpy.run_path(
        str(BACKEND_ROOT / "alembic" / "versions" / f"{REVISION}.py")
    )
    statement = migration["_eligible_active_ordinary_users_statement"]()
    compiled = statement.compile(dialect=postgresql.asyncpg.dialect())

    assert "users.status = $1::user_status" in str(compiled)


def test_affiliate_migration_backfills_only_active_ordinary_users(
    tmp_path: Path, monkeypatch
) -> None:
    database = tmp_path / "affiliate.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL", f"sqlite+aiosqlite:///{database.as_posix()}"
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")
    try:
        command.upgrade(config, "0155_finance_permissions")
        ordinary_id, mixed_id, staff_id, pending_id = (uuid4() for _ in range(4))
        department_id = uuid4()
        with sqlite3.connect(database) as connection:
            user_role_id = connection.execute(
                "SELECT id FROM roles WHERE code = 'USER'"
            ).fetchone()[0]
            moderator_role_id = connection.execute(
                "SELECT id FROM roles WHERE code = 'MODERATOR'"
            ).fetchone()[0]
            for user_id, email, user_status in (
                (ordinary_id, "ordinary@example.vn", "ACTIVE"),
                (mixed_id, "mixed@example.vn", "ACTIVE"),
                (staff_id, "staff@example.vn", "ACTIVE"),
                (pending_id, "pending@example.vn", "PENDING"),
            ):
                connection.execute(
                    "INSERT INTO users (id, email, status) VALUES (?, ?, ?)",
                    (user_id.hex, email, user_status),
                )
            connection.execute(
                "INSERT INTO departments (id, code, name) VALUES (?, ?, ?)",
                (department_id.hex, "AFF-TEST", "Affiliate test department"),
            )
            connection.execute(
                "INSERT INTO employees (id, employee_code, user_id, full_name, email, "
                "department_id, position, join_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    uuid4().hex,
                    "AFF-STAFF-1",
                    staff_id.hex,
                    "Affiliate Staff",
                    "staff@example.vn",
                    department_id.hex,
                    "Reviewer",
                    "2026-01-01",
                ),
            )
            connection.execute(
                "INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)",
                (ordinary_id.hex, user_role_id),
            )
            for user_id in (mixed_id, staff_id, pending_id):
                connection.execute(
                    "INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)",
                    (user_id.hex, user_role_id),
                )
            connection.execute(
                "INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)",
                (mixed_id.hex, moderator_role_id),
            )
            connection.commit()

        command.upgrade(config, REVISION)
        with sqlite3.connect(database) as connection:
            rows = connection.execute(
                "SELECT user_id, referral_code FROM affiliate_profiles"
            ).fetchall()
            assert rows == [
                (
                    ordinary_id.hex,
                    "THV"
                    + hashlib.sha256(str(ordinary_id).encode("ascii"))
                    .hexdigest()[:29]
                    .upper(),
                )
            ]
            rules = connection.execute(
                "SELECT version_no, status, enabled, level2_enabled, "
                "level2_rate_basis_points FROM affiliate_commission_rule_sets"
            ).fetchall()
            assert rules == [(1, "PUBLISHED", 0, 0, 0)]
            assert connection.execute(
                "SELECT count(*) FROM affiliate_commission_rates "
                "WHERE direct_rate_basis_points != 0"
            ).fetchone() == (0,)
            assert connection.execute(
                "SELECT count(*) FROM sqlite_master WHERE type = 'table' "
                "AND name = 'affiliate_commissions'"
            ).fetchone() == (1,)
    finally:
        get_settings.cache_clear()
