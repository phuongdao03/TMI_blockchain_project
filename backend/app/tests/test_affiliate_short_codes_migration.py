import runpy
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]
REVISION = "0164_affiliate_short_codes_and_two_levels"


def test_affiliate_short_code_migration_preserves_legacy_codes_and_history(
    tmp_path: Path, monkeypatch
) -> None:
    database = tmp_path / "affiliate-short-codes.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL", f"sqlite+aiosqlite:///{database.as_posix()}"
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")
    affiliate_id, referred_id, rule_set_id, commission_id = (uuid4() for _ in range(4))
    legacy_code = "THV" + "A1B2C3D4E5F6A7B8C9D0E1F2"
    now = datetime.now(UTC).isoformat()

    try:
        command.upgrade(config, "0163_test_account_isolation")
        with sqlite3.connect(database) as connection:
            connection.execute(
                "INSERT INTO users (id, email, status) VALUES (?, ?, ?)",
                (affiliate_id.hex, "affiliate@example.vn", "ACTIVE"),
            )
            connection.execute(
                "INSERT INTO users (id, email, status) VALUES (?, ?, ?)",
                (referred_id.hex, "referred@example.vn", "ACTIVE"),
            )
            connection.execute(
                "INSERT INTO affiliate_profiles "
                "(user_id, referral_code, status) VALUES (?, ?, ?)",
                (affiliate_id.hex, legacy_code, "ACTIVE"),
            )
            connection.execute(
                "INSERT INTO affiliate_commission_rule_sets "
                "(id, version_no, status, enabled, attribution_window_days, "
                "hold_days, level2_enabled, level2_rate_basis_points) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (rule_set_id.hex, 2, "DRAFT", 0, 30, 30, 0, 0),
            )
            connection.execute(
                "INSERT INTO affiliate_commissions "
                "(id, affiliate_user_id, referred_user_id, rule_set_id, "
                "rule_set_version, service_code, source_reference, amount_minor, "
                "commission_amount_minor, rate_basis_points, currency, status, "
                "earned_at, hold_until) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    commission_id.hex,
                    affiliate_id.hex,
                    referred_id.hex,
                    rule_set_id.hex,
                    2,
                    "MEMBERSHIP",
                    "membership:historical-order",
                    100_000,
                    5_000,
                    500,
                    "VND",
                    "PENDING",
                    now,
                    (datetime.now(UTC) + timedelta(days=30)).isoformat(),
                ),
            )
            connection.commit()

        command.upgrade(config, REVISION)
        with sqlite3.connect(database) as connection:
            saved_legacy, short_code = connection.execute(
                "SELECT referral_code, short_referral_code FROM affiliate_profiles "
                "WHERE user_id = ?",
                (affiliate_id.hex,),
            ).fetchone()
            assert saved_legacy == legacy_code
            assert 8 <= len(short_code) <= 10
            assert short_code.startswith("THV")
            assert connection.execute(
                "SELECT affiliate_user_id FROM affiliate_referral_code_aliases "
                "WHERE code IN (?, ?) ORDER BY code",
                (legacy_code, short_code),
            ).fetchall() == [(affiliate_id.hex,), (affiliate_id.hex,)]
            assert connection.execute(
                "SELECT commission_level FROM affiliate_commissions WHERE id = ?",
                (commission_id.hex,),
            ).fetchone() == (1,)
            connection.execute(
                "UPDATE affiliate_commission_rule_sets "
                "SET level2_enabled = 1, level2_rate_basis_points = 250 "
                "WHERE id = ?",
                (rule_set_id.hex,),
            )
            connection.commit()
            assert connection.execute(
                "SELECT level2_enabled, level2_rate_basis_points "
                "FROM affiliate_commission_rule_sets WHERE id = ?",
                (rule_set_id.hex,),
            ).fetchone() == (1, 250)
    finally:
        get_settings.cache_clear()


def test_affiliate_short_code_migration_generates_opaque_codes() -> None:
    migration = runpy.run_path(
        str(BACKEND_ROOT / "alembic" / "versions" / f"{REVISION}.py")
    )
    code = migration["_short_code"]()
    assert len(code) == 10
    assert code.startswith("THV")
    assert code.isalnum()
