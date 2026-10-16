import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_public_profile_identity_backfills_and_downgrades_without_losing_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "public-profile-identity.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    monkeypatch.setenv("BLOCKCHAIN_NETWORK", "local")
    monkeypatch.setenv("BLOCKCHAIN_CHAIN_ID", "31337")
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")
    user_id = "70000000000000000000000000000001"

    try:
        command.upgrade(config, "0110_community_avatar_media")
        with sqlite3.connect(database_path) as connection:
            connection.execute(
                "INSERT INTO users (id, email, password_hash, status) "
                "VALUES (?, ?, ?, ?)",
                (user_id, "public-name@example.test", "unused", "ACTIVE"),
            )
            connection.execute(
                "INSERT INTO community_profiles "
                "(user_id, username, display_name, avatar_url, bio) "
                "VALUES (?, ?, ?, ?, NULL)",
                (
                    user_id,
                    "legacy-member",
                    "Legacy public name",
                    "https://cdn.example.test/legacy-avatar.png",
                ),
            )

        command.upgrade(config, "0111_public_profile_identity")
        with sqlite3.connect(database_path) as connection:
            columns = {
                row[1] for row in connection.execute("PRAGMA table_info(user_profiles)")
            }
            profile = connection.execute(
                "SELECT display_name, avatar_url FROM user_profiles WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        assert "display_name" in columns
        assert profile == (
            "Legacy public name",
            "https://cdn.example.test/legacy-avatar.png",
        )

        command.downgrade(config, "0110_community_avatar_media")
        with sqlite3.connect(database_path) as connection:
            legacy_profile = connection.execute(
                "SELECT display_name, avatar_url "
                "FROM community_profiles WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            reverted_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(user_profiles)")
            }
        assert legacy_profile == (
            "Legacy public name",
            "https://cdn.example.test/legacy-avatar.png",
        )
        assert "display_name" not in reverted_columns
    finally:
        get_settings.cache_clear()
