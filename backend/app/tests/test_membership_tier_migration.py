import sqlite3
from pathlib import Path
from uuid import uuid4

from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]
REVISION = "0129_membership_tiers_and_diamond_applications"


def _upgrade(database_path: Path, monkeypatch) -> Config:
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")
    command.upgrade(config, REVISION)
    return config


def test_membership_catalog_migration_adds_silver_and_seeds_paid_plans(
    tmp_path: Path, monkeypatch
) -> None:
    database_path = tmp_path / "membership-catalog.sqlite3"
    config = _upgrade(database_path, monkeypatch)

    with sqlite3.connect(database_path) as connection:
        plans = connection.execute(
            "SELECT tier, name, amount_minor, duration_days FROM membership_plans "
            "WHERE active = 1 ORDER BY amount_minor"
        ).fetchall()
        assert plans == [
            ("SILVER", "Kết nối", 490_000, 365),
            ("COMPANION", "Đồng hành", 1_490_000, 365),
            ("PRESTIGE", "Tinh hoa", 3_990_000, 365),
        ]
        assert (
            connection.execute(
                "SELECT count(*) FROM membership_diamond_applications"
            ).fetchone()[0]
            == 0
        )

    command.downgrade(config, "0128_community_membership")
    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert "membership_diamond_applications" not in tables
    get_settings.cache_clear()


def test_membership_catalog_downgrade_refuses_to_drop_purchase_history(
    tmp_path: Path, monkeypatch
) -> None:
    database_path = tmp_path / "membership-history.sqlite3"
    config = _upgrade(database_path, monkeypatch)

    with sqlite3.connect(database_path) as connection:
        plan_id = connection.execute(
            "SELECT id FROM membership_plans WHERE tier = 'SILVER' LIMIT 1"
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO membership_purchases "
            "(id, user_id, plan_id, tier, amount_minor, list_price_minor, "
            "credit_minor, expires_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(uuid4()),
                str(uuid4()),
                plan_id,
                "SILVER",
                490_000,
                490_000,
                0,
                "2027-10-22T00:00:00+00:00",
            ),
        )

    try:
        command.downgrade(config, "0128_community_membership")
    except RuntimeError as exc:
        assert "membership history" in str(exc).lower()
    else:
        raise AssertionError("Downgrade removed immutable membership history")
    finally:
        get_settings.cache_clear()


def test_existing_purchase_amount_is_backfilled_without_rewriting_history(
    tmp_path: Path, monkeypatch
) -> None:
    database_path = tmp_path / "membership-backfill.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")
    command.upgrade(config, "0128_community_membership")
    plan_id, purchase_id = uuid4(), uuid4()

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "INSERT INTO membership_plans "
            "(id, name, tier, amount_minor, duration_days, active) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (str(plan_id), "Gold legacy", "COMPANION", 1_490_000, 365, 1),
        )
        connection.execute(
            "INSERT INTO membership_purchases "
            "(id, user_id, plan_id, tier, amount_minor, expires_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                str(purchase_id),
                str(uuid4()),
                str(plan_id),
                "COMPANION",
                1_234_567,
                "2027-10-22T00:00:00+00:00",
            ),
        )

    command.upgrade(config, REVISION)
    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT amount_minor, list_price_minor, credit_minor "
            "FROM membership_purchases WHERE id = ?",
            (str(purchase_id),),
        ).fetchone() == (1_234_567, 1_234_567, 0)
    get_settings.cache_clear()
