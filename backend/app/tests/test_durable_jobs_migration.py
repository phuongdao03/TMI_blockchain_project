import json
import sqlite3
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_durable_job_schema_preserves_intent_and_attempt_history(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "durable-jobs.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL",
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")

    command.upgrade(config, "0049_durable_jobs")

    job_id = str(uuid4())
    attempt_id = str(uuid4())
    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert {"job_executions", "job_attempts"}.issubset(tables)

        connection.execute(
            "INSERT INTO job_executions "
            "(id, task_name, queue_name, resource_type, resource_id, "
            "idempotency_key, intent, status, max_attempts, total_attempts, "
            "replay_count, version, scheduled_at, correlation_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), ?)",
            (
                job_id,
                "blockchain.broadcast",
                "blockchain",
                "blockchain_transaction",
                "tx-1",
                "broadcast:tx-1",
                json.dumps({"transaction_id": "tx-1"}),
                "QUEUED",
                5,
                0,
                0,
                1,
                "request-1",
            ),
        )
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute(
                "UPDATE job_executions SET intent = ? WHERE id = ?",
                (json.dumps({"transaction_id": "changed"}), job_id),
            )

        connection.execute(
            "INSERT INTO job_attempts "
            "(id, job_id, attempt_no, status, started_at) "
            "VALUES (?, ?, ?, ?, datetime('now'))",
            (attempt_id, job_id, 1, "RUNNING"),
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO job_attempts "
                "(id, job_id, attempt_no, status, started_at) "
                "VALUES (?, ?, ?, ?, datetime('now'))",
                (str(uuid4()), job_id, 1, "RUNNING"),
            )

    command.downgrade(config, "0048_audit_integrity")
    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    assert "job_attempts" not in tables
    assert "job_executions" not in tables
    get_settings.cache_clear()
