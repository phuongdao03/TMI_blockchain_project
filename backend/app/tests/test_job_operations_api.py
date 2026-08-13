import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Table
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.v1 import operations as operations_api
from app.core.config import Settings
from app.db.session import get_session
from app.main import create_application
from app.modules.audit.models import AuditLog
from app.modules.auth.dependencies import (
    get_csrf_protected_principal,
    get_current_principal,
)
from app.modules.auth.session_service import AuthPrincipal
from app.modules.operations.job_models import JobAttempt, JobExecution
from app.modules.operations.job_service import DurableJobService, JobRegistration

NOW = datetime(2026, 8, 11, 11, 0, tzinfo=UTC)


def _registration() -> JobRegistration:
    return JobRegistration(
        task_name="blockchain.broadcast",
        queue_name="blockchain",
        resource_type="blockchain_transaction",
        resource_id="tx-1",
        idempotency_key="broadcast:tx-1",
        intent={"transaction_id": "tx-1"},
        max_attempts=1,
        scheduled_at=NOW,
        correlation_id="task-1",
    )


def _principal(role: str, *permissions: str) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="operator@tmigroup.vn",
        roles=(role,),
        permissions=permissions,
    )


def test_job_operations_http_contract_enforces_authorization_and_replays(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = (tmp_path / "job-operations-api.db").as_posix()
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}")
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    async def setup() -> tuple[str, int]:
        async with engine.begin() as connection:
            await connection.run_sync(cast(Table, JobExecution.__table__).create)
            await connection.run_sync(cast(Table, JobAttempt.__table__).create)
            await connection.run_sync(cast(Table, AuditLog.__table__).create)
        async with sessions() as session:
            lifecycle = DurableJobService(session, clock=lambda: NOW)
            job = await lifecycle.register(_registration())
            attempt = await lifecycle.start_attempt(job.id, worker_task_id="task-1:1")
            failed = await lifecycle.fail_attempt(
                job.id,
                attempt.id,
                safe_error_code="RPC_TIMEOUT",
            )
            return str(failed.id), failed.version

    job_id, version = asyncio.run(setup())
    published: list[str] = []

    async def publish(job: JobExecution) -> None:
        published.append(str(job.id))

    async def session_override() -> AsyncIterator[AsyncSession]:
        async with sessions() as session:
            yield session

    monkeypatch.setattr(operations_api, "replay_durable_job", publish)
    app = create_application(settings=Settings())
    app.dependency_overrides[get_session] = session_override
    applicant = _principal("APPLICANT")
    app.dependency_overrides[get_current_principal] = lambda: applicant
    app.dependency_overrides[get_csrf_protected_principal] = lambda: applicant
    try:
        with TestClient(app) as client:
            forbidden = client.post(
                f"/api/v1/admin/operations/jobs/{job_id}/replays",
                json={
                    "expectedVersion": version,
                    "reason": "Provider recovered after verified incident",
                },
            )
        assert forbidden.status_code == 403
        assert published == []

        admin = _principal("SUPER_ADMIN", "operations.jobs.manage")
        app.dependency_overrides[get_current_principal] = lambda: admin
        app.dependency_overrides[get_csrf_protected_principal] = lambda: admin
        with TestClient(app) as client:
            listed = client.get("/api/v1/admin/operations/jobs?page=1&pageSize=20")
            replayed = client.post(
                f"/api/v1/admin/operations/jobs/{job_id}/replays",
                json={
                    "expectedVersion": version,
                    "reason": "Provider recovered after verified incident",
                },
            )
        assert listed.status_code == 200, listed.text
        assert listed.json()["meta"]["total"] == 1
        assert replayed.status_code == 200, replayed.text
        assert replayed.json()["data"]["status"] == "QUEUED"
        assert published == [job_id]
    finally:
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())
