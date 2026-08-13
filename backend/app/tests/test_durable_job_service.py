import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pytest
from sqlalchemy import Table, func, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.errors import DomainError
from app.modules.operations.job_models import (
    JobAttempt,
    JobAttemptStatus,
    JobExecution,
    JobExecutionStatus,
)
from app.modules.operations.job_service import DurableJobService, JobRegistration

NOW = datetime(2026, 8, 11, 9, 0, tzinfo=UTC)


def _registration(**overrides: object) -> JobRegistration:
    values: dict[str, object] = {
        "task_name": "blockchain.broadcast",
        "queue_name": "blockchain",
        "resource_type": "blockchain_transaction",
        "resource_id": "tx-1",
        "idempotency_key": "broadcast:tx-1",
        "intent": {"transaction_id": "tx-1"},
        "max_attempts": 2,
        "scheduled_at": NOW,
        "correlation_id": "request-1",
    }
    values.update(overrides)
    return JobRegistration(**values)  # type: ignore[arg-type]


async def _database() -> tuple[async_sessionmaker[AsyncSession], AsyncEngine]:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(cast(Table, JobExecution.__table__).create)
        await connection.run_sync(cast(Table, JobAttempt.__table__).create)
    return async_sessionmaker(engine, expire_on_commit=False), engine


def test_job_registration_is_idempotent_and_rejects_changed_intent() -> None:
    async def scenario() -> None:
        sessions, engine = await _database()
        service = DurableJobService(sessions(), clock=lambda: NOW)

        created = await service.register(_registration())
        replay = await service.register(_registration())

        assert replay.id == created.id
        with pytest.raises(DomainError) as error:
            await service.register(
                _registration(intent={"transaction_id": "different"})
            )
        assert error.value.code == "JOB_IDEMPOTENCY_CONFLICT"

        async with sessions() as reader:
            count = await reader.scalar(select(func.count()).select_from(JobExecution))
            assert count == 1
        await service.close()
        await engine.dispose()

    asyncio.run(scenario())


def test_attempt_lifecycle_is_duplicate_safe_and_dead_letters_exhaustion() -> None:
    async def scenario() -> None:
        sessions, engine = await _database()
        service = DurableJobService(sessions(), clock=lambda: NOW)
        job = await service.register(_registration())

        first = await service.start_attempt(job.id, worker_task_id="celery-1")
        duplicate = await service.start_attempt(job.id, worker_task_id="celery-1")
        assert duplicate.id == first.id

        retrying = await service.fail_attempt(
            job.id,
            first.id,
            safe_error_code="RPC_TIMEOUT",
        )
        assert retrying.status is JobExecutionStatus.QUEUED

        second = await service.start_attempt(job.id, worker_task_id="celery-2")
        exhausted = await service.fail_attempt(
            job.id,
            second.id,
            safe_error_code="RPC_UNAVAILABLE",
        )
        assert exhausted.status is JobExecutionStatus.DEAD_LETTERED
        assert exhausted.last_error_code == "RPC_UNAVAILABLE"

        async with sessions() as reader:
            attempts = tuple(
                (
                    await reader.scalars(
                        select(JobAttempt).order_by(JobAttempt.attempt_no)
                    )
                ).all()
            )
            assert [attempt.status for attempt in attempts] == [
                JobAttemptStatus.RETRYABLE_FAILED,
                JobAttemptStatus.EXHAUSTED,
            ]
        await service.close()
        await engine.dispose()

    asyncio.run(scenario())


def test_job_service_rejects_sensitive_intent_and_raw_error_messages() -> None:
    async def scenario() -> None:
        sessions, engine = await _database()
        service = DurableJobService(sessions(), clock=lambda: NOW)

        with pytest.raises(DomainError) as sensitive:
            await service.register(_registration(intent={"access_token": "secret"}))
        assert sensitive.value.code == "JOB_INTENT_INVALID"

        job = await service.register(_registration())
        attempt = await service.start_attempt(job.id, worker_task_id="celery-1")
        with pytest.raises(DomainError) as unsafe_error:
            await service.fail_attempt(
                job.id,
                attempt.id,
                safe_error_code="connection failed at https://rpc.internal",
            )
        assert unsafe_error.value.code == "JOB_ERROR_CODE_INVALID"

        await service.close()
        await engine.dispose()

    asyncio.run(scenario())


def test_non_retryable_failure_dead_letters_without_waiting_for_attempt_limit() -> None:
    async def scenario() -> None:
        sessions, engine = await _database()
        service = DurableJobService(sessions(), clock=lambda: NOW)
        job = await service.register(_registration(max_attempts=5))
        attempt = await service.start_attempt(job.id, worker_task_id="celery-1")

        failed = await service.fail_attempt(
            job.id,
            attempt.id,
            safe_error_code="INVALID_WORKER_PAYLOAD",
            retryable=False,
        )

        assert failed.status is JobExecutionStatus.DEAD_LETTERED
        assert attempt.status is JobAttemptStatus.EXHAUSTED
        await service.close()
        await engine.dispose()

    asyncio.run(scenario())


def test_concurrent_registration_returns_one_job(tmp_path: Path) -> None:
    async def scenario() -> None:
        database_path = (tmp_path / "durable-jobs.db").as_posix()
        engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}")
        async with engine.begin() as connection:
            await connection.run_sync(cast(Table, JobExecution.__table__).create)
            await connection.run_sync(cast(Table, JobAttempt.__table__).create)
        sessions = async_sessionmaker(engine, expire_on_commit=False)

        async def register() -> JobExecution:
            async with sessions() as session:
                return await DurableJobService(session, clock=lambda: NOW).register(
                    _registration()
                )

        first, second = await asyncio.gather(register(), register())

        assert first.id == second.id
        async with sessions() as reader:
            count = await reader.scalar(select(func.count()).select_from(JobExecution))
            assert count == 1
        await engine.dispose()

    asyncio.run(scenario())


def test_replay_and_cancel_require_current_version_and_valid_state() -> None:
    async def scenario() -> None:
        sessions, engine = await _database()
        service = DurableJobService(sessions(), clock=lambda: NOW)
        job = await service.register(_registration(max_attempts=1))
        attempt = await service.start_attempt(job.id, worker_task_id="celery-1")
        failed = await service.fail_attempt(
            job.id,
            attempt.id,
            safe_error_code="RPC_TIMEOUT",
        )
        failed_version = failed.version

        replayed = await service.replay(job.id, expected_version=failed_version)
        assert replayed.status is JobExecutionStatus.QUEUED
        assert replayed.replay_count == 1
        job_id = replayed.id
        replayed_version = replayed.version

        with pytest.raises(DomainError) as stale:
            await service.cancel(job_id, expected_version=failed_version)
        assert stale.value.code == "JOB_VERSION_CONFLICT"

        cancelled = await service.cancel(job_id, expected_version=replayed_version)
        assert cancelled.status is JobExecutionStatus.CANCELLED
        assert cancelled.cancel_requested_at is not None
        assert cancelled.cancel_requested_at.replace(tzinfo=UTC) == NOW
        await service.close()
        await engine.dispose()

    asyncio.run(scenario())


def test_concurrent_replay_allows_exactly_one_winner(tmp_path: Path) -> None:
    async def scenario() -> None:
        database_path = (tmp_path / "concurrent-replay.db").as_posix()
        engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}")
        async with engine.begin() as connection:
            await connection.run_sync(cast(Table, JobExecution.__table__).create)
            await connection.run_sync(cast(Table, JobAttempt.__table__).create)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with sessions() as session:
            lifecycle = DurableJobService(session, clock=lambda: NOW)
            job = await lifecycle.register(_registration(max_attempts=1))
            attempt = await lifecycle.start_attempt(job.id, worker_task_id="celery-1")
            failed = await lifecycle.fail_attempt(
                job.id,
                attempt.id,
                safe_error_code="RPC_TIMEOUT",
            )
            job_id = failed.id
            version = failed.version

        async def replay() -> JobExecution | Exception:
            async with sessions() as session:
                try:
                    return await DurableJobService(session, clock=lambda: NOW).replay(
                        job_id,
                        expected_version=version,
                    )
                except Exception as exc:
                    return exc

        outcomes = await asyncio.gather(replay(), replay())

        winners = [item for item in outcomes if isinstance(item, JobExecution)]
        conflicts = [
            item
            for item in outcomes
            if isinstance(item, DomainError) and item.code == "JOB_VERSION_CONFLICT"
        ]
        assert len(winners) == 1
        assert len(conflicts) == 1
        await engine.dispose()

    asyncio.run(scenario())
