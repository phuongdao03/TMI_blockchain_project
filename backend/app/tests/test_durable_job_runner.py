import asyncio
import logging
from dataclasses import replace
from datetime import UTC, datetime
from typing import cast

import pytest
from sqlalchemy import Table, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.modules.operations.job_models import (
    JobAttempt,
    JobAttemptStatus,
    JobExecution,
    JobExecutionStatus,
)
from app.modules.operations.job_service import DurableJobService, JobRegistration
from app.workers.durable import DurableJobRunner

NOW = datetime(2026, 8, 11, 10, 0, tzinfo=UTC)


class LifecycleLogRecord(logging.LogRecord):
    action: str
    request_id: str
    job_id: str
    task_name: str
    queue_name: str
    worker_task_id: str


def _registration() -> JobRegistration:
    return JobRegistration(
        task_name="blockchain.broadcast",
        queue_name="blockchain",
        resource_type="blockchain_transaction",
        resource_id="tx-1",
        idempotency_key="broadcast:tx-1",
        intent={"transaction_id": "tx-1"},
        max_attempts=2,
        scheduled_at=NOW,
        correlation_id="celery-task-1",
    )


async def _database() -> tuple[async_sessionmaker[AsyncSession], AsyncEngine]:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(cast(Table, JobExecution.__table__).create)
        await connection.run_sync(cast(Table, JobAttempt.__table__).create)
    return async_sessionmaker(engine, expire_on_commit=False), engine


def test_runner_records_success_and_skips_duplicate_delivery() -> None:
    async def scenario() -> None:
        sessions, engine = await _database()
        runner = DurableJobRunner(sessions, clock=lambda: NOW)
        calls = 0

        async def operation() -> None:
            nonlocal calls
            calls += 1

        await runner.run(
            _registration(), worker_task_id="celery-task-1:1", operation=operation
        )
        await runner.run(
            _registration(), worker_task_id="celery-task-1:1", operation=operation
        )

        assert calls == 1
        async with sessions() as reader:
            job = (await reader.scalars(select(JobExecution))).one()
            attempt = (await reader.scalars(select(JobAttempt))).one()
            assert job.status is JobExecutionStatus.SUCCEEDED
            assert attempt.status is JobAttemptStatus.SUCCEEDED
        await engine.dispose()

    asyncio.run(scenario())


def test_runner_records_safe_failure_then_allows_retry() -> None:
    async def scenario() -> None:
        sessions, engine = await _database()
        runner = DurableJobRunner(sessions, clock=lambda: NOW)

        async def unavailable() -> None:
            raise ConnectionError("private provider URL and credentials")

        with pytest.raises(ConnectionError):
            await runner.run(
                _registration(),
                worker_task_id="celery-task-1:1",
                operation=unavailable,
                error_code_for=lambda error: "RPC_UNAVAILABLE",
            )

        completed = False

        async def recovered() -> None:
            nonlocal completed
            completed = True

        await runner.run(
            _registration(),
            worker_task_id="celery-task-1:2",
            operation=recovered,
        )

        assert completed is True
        async with sessions() as reader:
            job = (await reader.scalars(select(JobExecution))).one()
            attempts = tuple(
                (
                    await reader.scalars(
                        select(JobAttempt).order_by(JobAttempt.attempt_no)
                    )
                ).all()
            )
            assert job.status is JobExecutionStatus.SUCCEEDED
            assert [attempt.status for attempt in attempts] == [
                JobAttemptStatus.RETRYABLE_FAILED,
                JobAttemptStatus.SUCCEEDED,
            ]
            assert attempts[0].safe_error_code == "RPC_UNAVAILABLE"
            assert "private" not in str(attempts[0].safe_error_code)
        await engine.dispose()

    asyncio.run(scenario())


def test_runner_resolves_pre_persisted_job_by_identifier() -> None:
    async def scenario() -> None:
        sessions, engine = await _database()
        async with sessions() as session:
            job = await DurableJobService(session, clock=lambda: NOW).register(
                _registration()
            )

        replay_delivery = replace(
            _registration(),
            idempotency_key="broadcast:tx-1:replay-task",
            correlation_id="replay-task",
        )
        executed = False

        async def operation() -> None:
            nonlocal executed
            executed = True

        await DurableJobRunner(sessions, clock=lambda: NOW).run(
            replay_delivery,
            worker_task_id="replay-task:1",
            durable_job_id=job.id,
            operation=operation,
        )

        assert executed is True
        async with sessions() as reader:
            assert len((await reader.scalars(select(JobExecution))).all()) == 1
        await engine.dispose()

    asyncio.run(scenario())


def test_runner_emits_safe_correlated_lifecycle_events() -> None:
    async def scenario() -> None:
        sessions, engine = await _database()
        records: list[logging.LogRecord] = []

        class CaptureHandler(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                records.append(record)

        target_logger = logging.getLogger("app.workers.durable")
        handler = CaptureHandler()
        target_logger.addHandler(handler)
        target_logger.setLevel(logging.INFO)

        async def operation() -> None:
            return None

        try:
            await DurableJobRunner(sessions, clock=lambda: NOW).run(
                _registration(),
                worker_task_id="celery-task-1:1",
                operation=operation,
            )
        finally:
            target_logger.removeHandler(handler)

        lifecycle = [
            cast(LifecycleLogRecord, record)
            for record in records
            if getattr(record, "action", "").startswith("durable_job.")
        ]
        assert [record.action for record in lifecycle] == [
            "durable_job.started",
            "durable_job.succeeded",
        ]
        for record in lifecycle:
            assert record.request_id == "celery-task-1"
            assert record.job_id
            assert record.task_name == "blockchain.broadcast"
            assert record.queue_name == "blockchain"
            assert record.worker_task_id == "celery-task-1:1"
        await engine.dispose()

    asyncio.run(scenario())
