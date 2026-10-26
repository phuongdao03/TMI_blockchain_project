import sqlite3
from pathlib import Path

from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_membership_chat_history_migration_round_trip(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "membership-chat-history.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    monkeypatch.setenv("BLOCKCHAIN_NETWORK", "local")
    monkeypatch.setenv("BLOCKCHAIN_CHAIN_ID", "31337")
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")

    try:
        command.upgrade(config, "0140_membership_chat_room_access")
        command.upgrade(config, "0141_membership_chat_history")
        with sqlite3.connect(database_path) as connection:
            columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(community_chat_messages)"
                )
            }
            indexes = {
                row[1]
                for row in connection.execute(
                    "PRAGMA index_list(community_chat_messages)"
                )
            }
            composite_index_columns = tuple(
                row[2]
                for row in connection.execute(
                    'PRAGMA index_info("ix_community_chat_messages_room_created_id")'
                )
            )
        assert "edited_at" in columns
        assert "ix_community_chat_messages_room_created_id" in indexes
        assert composite_index_columns == ("room", "created_at", "id")
        assert "ix_community_chat_messages_room" not in indexes

        command.downgrade(config, "0140_membership_chat_room_access")
        with sqlite3.connect(database_path) as connection:
            restored_columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(community_chat_messages)"
                )
            }
            restored_indexes = {
                row[1]
                for row in connection.execute(
                    "PRAGMA index_list(community_chat_messages)"
                )
            }
        assert "edited_at" not in restored_columns
        assert "ix_community_chat_messages_room" in restored_indexes
        assert "ix_community_chat_messages_room_created_id" not in restored_indexes
    finally:
        get_settings.cache_clear()
