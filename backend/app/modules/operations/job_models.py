from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UtcTimestampMixin


class JobExecutionStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    DEAD_LETTERED = "DEAD_LETTERED"
    CANCELLED = "CANCELLED"


class JobAttemptStatus(StrEnum):
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    RETRYABLE_FAILED = "RETRYABLE_FAILED"
    EXHAUSTED = "EXHAUSTED"


def _enum(enum_type: type[StrEnum], name: str) -> Enum:
    return Enum(
        enum_type,
        name=name,
        values_callable=lambda values: [value.value for value in values],
        validate_strings=True,
        native_enum=False,
        create_constraint=True,
    )


JOB_JSON = JSONB().with_variant(JSON(), "sqlite")


class JobExecution(UtcTimestampMixin, Base):
    __tablename__ = "job_executions"
    __table_args__ = (
        CheckConstraint("max_attempts > 0", name="job_max_attempts_positive"),
        CheckConstraint("total_attempts >= 0", name="job_total_attempts_non_negative"),
        CheckConstraint("replay_count >= 0", name="job_replay_count_non_negative"),
        CheckConstraint("version > 0", name="job_version_positive"),
        UniqueConstraint(
            "task_name",
            "idempotency_key",
            name="uq_job_executions_task_idempotency",
        ),
        Index("ix_job_executions_status_scheduled", "status", "scheduled_at"),
        Index("ix_job_executions_resource", "resource_type", "resource_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    task_name: Mapped[str] = mapped_column(String(128), nullable=False)
    queue_name: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(128), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    intent_json: Mapped[dict[str, object]] = mapped_column(
        "intent", JOB_JSON, nullable=False
    )
    status: Mapped[JobExecutionStatus] = mapped_column(
        _enum(JobExecutionStatus, "job_execution_status"),
        nullable=False,
        default=JobExecutionStatus.QUEUED,
        server_default=JobExecutionStatus.QUEUED.value,
    )
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    total_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    replay_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    correlation_id: Mapped[str] = mapped_column(String(128), nullable=False)
    last_error_code: Mapped[str | None] = mapped_column(String(64))
    cancel_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class JobAttempt(Base):
    __tablename__ = "job_attempts"
    __table_args__ = (
        CheckConstraint("attempt_no > 0", name="job_attempt_no_positive"),
        UniqueConstraint("job_id", "attempt_no", name="uq_job_attempts_job_attempt_no"),
        UniqueConstraint("worker_task_id", name="uq_job_attempts_worker_task_id"),
        Index("ix_job_attempts_status_started", "status", "started_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    job_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("job_executions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False)
    worker_task_id: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[JobAttemptStatus] = mapped_column(
        _enum(JobAttemptStatus, "job_attempt_status"),
        nullable=False,
    )
    safe_error_code: Mapped[str | None] = mapped_column(String(64))
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
