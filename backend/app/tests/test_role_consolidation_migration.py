import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_role_consolidation_keeps_moderator_review_only_and_super_admin_signing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "role-consolidation.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")

    command.upgrade(config, "0057_blockchain_human_signing")
    with sqlite3.connect(database_path) as connection:
        role_ids = dict(connection.execute("SELECT code, id FROM roles"))
        connection.executemany(
            "INSERT INTO users (id, email, status, account_type) VALUES (?, ?, ?, ?)",
            [
                ("0" * 31 + "1", "viewer@tmigroup.vn", "ACTIVE", "PUBLIC_USER"),
                ("0" * 31 + "2", "user@tmigroup.vn", "ACTIVE", "INDIVIDUAL_APPLICANT"),
                ("0" * 31 + "3", "moderator@tmigroup.vn", "ACTIVE", None),
                ("0" * 31 + "4", "superadmin@tmigroup.vn", "ACTIVE", None),
            ],
        )
        connection.executemany(
            "INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)",
            [
                ("0" * 31 + "2", role_ids["APPLICANT"]),
                ("0" * 31 + "3", role_ids["REVIEWER"]),
                ("0" * 31 + "4", role_ids["SUPER_ADMIN"]),
            ],
        )
        connection.commit()

    command.upgrade(config, "0060_certificate_version_qr")
    with sqlite3.connect(database_path) as connection:
        moderator_id = connection.execute(
            "SELECT id FROM roles WHERE code = 'MODERATOR'"
        ).fetchone()
        elevated_permission_ids = connection.execute(
            "SELECT id FROM permissions WHERE code IN "
            "('blockchain.manage', 'blockchain.sign', 'cms.manage', "
            "'council.manage', 'payment.manage')"
        ).fetchall()
        assert moderator_id is not None
        elevated_mappings = [
            (moderator_id[0], permission_id[0])
            for permission_id in elevated_permission_ids
        ]
        connection.executemany(
            "INSERT OR IGNORE INTO role_permissions (role_id, permission_id) "
            "VALUES (?, ?)",
            elevated_mappings,
        )
        connection.commit()

    command.upgrade(config, "head")

    with sqlite3.connect(database_path) as connection:
        role_codes = {row[0] for row in connection.execute("SELECT code FROM roles")}
        blockchain_signers = {
            row[0]
            for row in connection.execute(
                "SELECT r.code FROM role_permissions rp "
                "JOIN roles r ON r.id = rp.role_id "
                "JOIN permissions p ON p.id = rp.permission_id "
                "WHERE p.code = 'blockchain.sign'"
            )
        }
        moderator_permissions = {
            row[0]
            for row in connection.execute(
                "SELECT p.code FROM role_permissions rp "
                "JOIN roles r ON r.id = rp.role_id "
                "JOIN permissions p ON p.id = rp.permission_id "
                "WHERE r.code = 'MODERATOR'"
            )
        }
        user_roles = dict(
            connection.execute(
                "SELECT u.email, r.code FROM user_roles ur "
                "JOIN users u ON u.id = ur.user_id "
                "JOIN roles r ON r.id = ur.role_id"
            )
        )

    assert role_codes == {"VIEWER", "USER", "MODERATOR", "SUPER_ADMIN"}
    assert blockchain_signers == {"SUPER_ADMIN"}
    assert moderator_permissions == {"review.submit", "similarity.review"}
    assert user_roles == {
        "viewer@tmigroup.vn": "VIEWER",
        "user@tmigroup.vn": "USER",
        "moderator@tmigroup.vn": "MODERATOR",
        "superadmin@tmigroup.vn": "SUPER_ADMIN",
    }
    get_settings.cache_clear()
