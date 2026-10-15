import sqlite3
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from pydantic import ValidationError

from alembic import command
from app.core.config import get_settings
from app.modules.community.admin_schemas import CommunityReportRequest

BACKEND_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("reason", ["ADVERTISING", "PRIVACY_VIOLATION"])
def test_new_report_reasons_validate(reason: str) -> None:
    assert CommunityReportRequest.model_validate({"reason": reason}).reason == reason


def test_unknown_report_reason_stays_rejected() -> None:
    with pytest.raises(ValidationError):
        CommunityReportRequest.model_validate({"reason": "NOT_A_REASON"})


def test_report_reason_migration_upgrades_and_safely_downgrades(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "community-report-reasons.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    monkeypatch.setenv("BLOCKCHAIN_NETWORK", "local")
    monkeypatch.setenv("BLOCKCHAIN_CHAIN_ID", "31337")
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")
    report_id = str(uuid4())
    reporter_id = str(uuid4())
    post_id = str(uuid4())
    privacy_post_id = str(uuid4())

    try:
        command.upgrade(config, "0106_community_post_tags")
        with sqlite3.connect(database_path) as connection:
            connection.execute(
                "INSERT INTO community_reports "
                "(id, reporter_user_id, post_id, reason, request_id) "
                "VALUES (?, ?, ?, ?, ?)",
                (report_id, reporter_id, post_id, "SPAM", "req-existing"),
            )
            connection.commit()

        command.upgrade(config, "head")
        with sqlite3.connect(database_path) as connection:
            connection.execute(
                "INSERT INTO community_reports "
                "(id, reporter_user_id, post_id, reason, request_id) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    str(uuid4()),
                    reporter_id,
                    str(uuid4()),
                    "ADVERTISING",
                    "req-advertising",
                ),
            )
            connection.execute(
                "INSERT INTO community_reports "
                "(id, reporter_user_id, post_id, reason, request_id) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    str(uuid4()),
                    reporter_id,
                    privacy_post_id,
                    "PRIVACY_VIOLATION",
                    "req-privacy",
                ),
            )
            connection.commit()
            report_sql = connection.execute(
                "SELECT sql FROM sqlite_master "
                "WHERE type='table' AND name='community_reports'"
            ).fetchone()[0]
            inserted = connection.execute(
                "SELECT reason FROM community_reports WHERE id = ?", (report_id,)
            ).fetchone()
        assert "ADVERTISING" in report_sql
        assert "PRIVACY_VIOLATION" in report_sql
        assert inserted == ("SPAM",)

        command.downgrade(config, "0106_community_post_tags")
        with sqlite3.connect(database_path) as connection:
            reasons = {
                row[0]
                for row in connection.execute(
                    "SELECT reason FROM community_reports ORDER BY reason"
                )
            }
            report_sql = connection.execute(
                "SELECT sql FROM sqlite_master "
                "WHERE type='table' AND name='community_reports'"
            ).fetchone()[0]
        assert reasons == {"OTHER", "SPAM"}
        assert "ADVERTISING" not in report_sql
        assert "PRIVACY_VIOLATION" not in report_sql
    finally:
        get_settings.cache_clear()
