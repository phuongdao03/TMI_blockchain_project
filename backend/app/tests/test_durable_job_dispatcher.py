import asyncio
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

from app.modules.operations.job_models import JobAttempt, JobExecution
from app.modules.operations.job_service import DurableJobService, JobRegistration
from app.workers.dispatcher import (
    DurableJobDispatcher,
    JobReplayPolicyError,
    replay_durable_job,
)

NOW = datetime(2026, 8, 11, 10, 0, tzinfo=UTC)


class Publisher:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[dict[str, object]] = []

    def send_task(self, name: str, **options: object) -> object:
        self.calls.append({"name": name, **options})
        if self.fail:
            raise ConnectionError("broker unavailable")
        return object()


def _registration() -> JobRegistration:
    return JobRegistration(
        task_name="blockchain.broadcast",
        queue_name="blockchain",
        resource_type="blockchain_transaction",
        resource_id="tx-1",
        idempotency_key="broadcast:tx-1:task-1",
        intent={"transaction_id": "tx-1"},
        max_attempts=6,
        scheduled_at=NOW,
        correlation_id="task-1",
    )


async def _database() -> tuple[async_sessionmaker[AsyncSession], AsyncEngine]:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(cast(Table, JobExecution.__table__).create)
        await connection.run_sync(cast(Table, JobAttempt.__table__).create)
    return async_sessionmaker(engine, expire_on_commit=False), engine


def test_dispatcher_persists_intent_before_publishing() -> None:
    async def scenario() -> None:
        sessions, engine = await _database()
        publisher = Publisher()
        dispatcher = DurableJobDispatcher(sessions, publisher)

        job = await dispatcher.dispatch(
            _registration(),
            celery_task_name="app.workers.blockchain_tasks.broadcast_blockchain_transaction",
            args=["tx-1"],
        )

        assert job.correlation_id == "task-1"
        assert publisher.calls == [
            {
                "name": "app.workers.blockchain_tasks.broadcast_blockchain_transaction",
                "args": ["tx-1"],
                "kwargs": {"durable_job_id": str(job.id)},
                "queue": "blockchain",
                "task_id": "task-1",
            }
        ]
        async with sessions() as reader:
            assert await reader.scalar(select(JobExecution)) is not None
        await engine.dispose()

    asyncio.run(scenario())


def test_broker_failure_leaves_queued_job_visible() -> None:
    async def scenario() -> None:
        sessions, engine = await _database()
        dispatcher = DurableJobDispatcher(sessions, Publisher(fail=True))

        with pytest.raises(ConnectionError):
            await dispatcher.dispatch(
                _registration(),
                celery_task_name="worker.task",
                args=["tx-1"],
            )

        async with sessions() as reader:
            job = await reader.scalar(select(JobExecution))
            assert job is not None
            assert job.status.value == "QUEUED"
            assert job.total_attempts == 0
        await engine.dispose()

    asyncio.run(scenario())


def test_replay_publishes_only_allowlisted_immutable_intent() -> None:
    async def scenario() -> None:
        sessions, engine = await _database()
        publisher = Publisher()
        dispatcher = DurableJobDispatcher(sessions, publisher)
        async with sessions() as session:
            job = await DurableJobService(session).register(_registration())

        await replay_durable_job(
            job,
            dispatcher=dispatcher,
            task_id_factory=lambda: "replay-task-1",
        )
        assert publisher.calls == [
            {
                "name": "app.workers.blockchain_tasks.broadcast_blockchain_transaction",
                "args": ["tx-1"],
                "kwargs": {"durable_job_id": str(job.id)},
                "queue": "blockchain",
                "task_id": "replay-task-1",
            }
        ]

        job.task_name = "arbitrary.shell.command"
        with pytest.raises(JobReplayPolicyError):
            await replay_durable_job(job, dispatcher=dispatcher)
        await engine.dispose()

    asyncio.run(scenario())
