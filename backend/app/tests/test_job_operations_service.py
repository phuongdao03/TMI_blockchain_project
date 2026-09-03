import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from uuid import uuid4

import pytest
from sqlalchemy import Table, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.errors import DomainError
from app.modules.audit.models import AuditLog
from app.modules.auth.session_service import AuthPrincipal
from app.modules.operations.job_models import JobAttempt, JobExecution
from app.modules.operations.job_operations_service import JobOperationsService
from app.modules.operations.job_service import DurableJobService, JobRegistration

NOW = datetime(2026, 8, 11, 11, 0, tzinfo=UTC)


def _principal(role: str, *permissions: str) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="operator@tmigroup.vn",
        roles=(role,),
        permissions=permissions,
    )


def _registration(index: int = 1) -> JobRegistration:
    return JobRegistration(
        task_name="blockchain.confirm",
        queue_name="blockchain",
        resource_type="blockchain_transaction",
        resource_id=f"tx-{index}",
        idempotency_key=f"confirm:tx-{index}",
        intent={"transaction_id": f"tx-{index}"},
        max_attempts=1,
        scheduled_at=NOW,
        correlation_id=f"task-{index}",
    )


async def _database() -> tuple[async_sessionmaker[AsyncSession], AsyncEngine]:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(cast(Table, JobExecution.__table__).create)
        await connection.run_sync(cast(Table, JobAttempt.__table__).create)
        await connection.run_sync(cast(Table, AuditLog.__table__).create)
    return async_sessionmaker(engine, expire_on_commit=False), engine


def test_job_list_is_paginated_and_permission_protected() -> None:
    async def scenario() -> None:
        sessions, engine = await _database()
        async with sessions() as session:
            lifecycle = DurableJobService(session, clock=lambda: NOW)
            await lifecycle.register(_registration(1))
            await lifecycle.register(_registration(2))

        async with sessions() as session:
            service = JobOperationsService(session)
            rows, total = await service.list_jobs(
                _principal("BLOCKCHAIN_ADMIN", "operations.read"),
                page=1,
                page_size=1,
            )
            assert len(rows) == 1
            assert total == 2

            with pytest.raises(DomainError) as denied:
                await service.list_jobs(_principal("APPLICANT"), page=1, page_size=20)
            assert denied.value.code == "JOB_OPERATIONS_FORBIDDEN"
        await engine.dispose()

    asyncio.run(scenario())


def test_replay_requires_manage_permission_and_records_audit() -> None:
    async def scenario() -> None:
        sessions, engine = await _database()
        async with sessions() as session:
            lifecycle = DurableJobService(session, clock=lambda: NOW)
            job = await lifecycle.register(_registration())
            attempt = await lifecycle.start_attempt(job.id, worker_task_id="task-1:1")
            failed = await lifecycle.fail_attempt(
                job.id,
                attempt.id,
                safe_error_code="RPC_TIMEOUT",
            )
            job_id = failed.id
            version = failed.version

        published: list[object] = []

        async def publish(job: JobExecution) -> None:
            published.append(job.id)

        async with sessions() as session:
            service = JobOperationsService(session, replay_publisher=publish)
            with pytest.raises(DomainError) as denied:
                await service.replay_job(
                    _principal("BLOCKCHAIN_ADMIN", "operations.read"),
                    job_id,
                    expected_version=version,
                    reason="Retry after provider recovery",
                )
            assert denied.value.code == "JOB_OPERATIONS_FORBIDDEN"

            actor = _principal("SUPER_ADMIN", "operations.jobs.manage")
            replayed = await service.replay_job(
                actor,
                job_id,
                expected_version=version,
                reason="Retry after provider recovery",
            )
            assert replayed.status.value == "QUEUED"
            assert published == [job_id]

        async with sessions() as reader:
            audit = (await reader.scalars(select(AuditLog))).one()
            assert audit.action == "operations.job.replayed"
            assert audit.actor_user_id == actor.user_id
            assert audit.after_json is not None
            assert audit.after_json["reason"] == "Retry after provider recovery"
        await engine.dispose()

    asyncio.run(scenario())


def test_cancel_rejects_stale_version_and_does_not_publish() -> None:
    async def scenario() -> None:
        sessions, engine = await _database()
        async with sessions() as session:
            job = await DurableJobService(session, clock=lambda: NOW).register(
                _registration()
            )
            job_id = job.id
            version = job.version

        async with sessions() as session:
            service = JobOperationsService(session)
            principal = _principal("SUPER_ADMIN", "operations.jobs.manage")
            with pytest.raises(DomainError) as stale:
                await service.cancel_job(
                    principal,
                    job_id,
                    expected_version=version + 1,
                    reason="Cancelled duplicate operational request",
                )
            assert stale.value.code == "JOB_VERSION_CONFLICT"

            cancelled = await service.cancel_job(
                principal,
                job_id,
                expected_version=version,
                reason="Cancelled duplicate operational request",
            )
            assert cancelled.status.value == "CANCELLED"
        await engine.dispose()

    asyncio.run(scenario())


def test_concurrent_operator_replay_publishes_once(tmp_path: Path) -> None:
    async def scenario() -> None:
        database_path = (tmp_path / "operator-replay.db").as_posix()
        engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}")
        async with engine.begin() as connection:
            await connection.run_sync(cast(Table, JobExecution.__table__).create)
            await connection.run_sync(cast(Table, JobAttempt.__table__).create)
            await connection.run_sync(cast(Table, AuditLog.__table__).create)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with sessions() as session:
            lifecycle = DurableJobService(session, clock=lambda: NOW)
            job = await lifecycle.register(_registration())
            attempt = await lifecycle.start_attempt(job.id, worker_task_id="task-1:1")
            failed = await lifecycle.fail_attempt(
                job.id,
                attempt.id,
                safe_error_code="RPC_TIMEOUT",
            )
            job_id = failed.id
            version = failed.version

        published: list[object] = []

        async def publish(job: JobExecution) -> None:
            published.append(job.id)

        async def replay() -> JobExecution | Exception:
            async with sessions() as session:
                try:
                    return await JobOperationsService(
                        session,
                        replay_publisher=publish,
                    ).replay_job(
                        _principal("SUPER_ADMIN", "operations.jobs.manage"),
                        job_id,
                        expected_version=version,
                        reason="Provider recovered after verified incident",
                    )
                except Exception as exc:
                    return exc

        outcomes = await asyncio.gather(replay(), replay())

        assert len([item for item in outcomes if isinstance(item, JobExecution)]) == 1
        assert (
            len(
                [
                    item
                    for item in outcomes
                    if isinstance(item, DomainError)
                    and item.code == "JOB_VERSION_CONFLICT"
                ]
            )
            == 1
        )
        assert published == [job_id]
        async with sessions() as reader:
            audits = tuple((await reader.scalars(select(AuditLog))).all())
            assert len(audits) == 1
        await engine.dispose()

    asyncio.run(scenario())
