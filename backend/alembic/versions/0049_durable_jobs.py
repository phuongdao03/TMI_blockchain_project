"""Add durable job intent and attempt history.

Revision ID: 0049_durable_jobs
Revises: 0048_audit_integrity
Create Date: 2026-08-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0049_durable_jobs"
down_revision: str | None = "0048_audit_integrity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JOB_STATUSES = ("QUEUED", "RUNNING", "SUCCEEDED", "DEAD_LETTERED", "CANCELLED")
ATTEMPT_STATUSES = (
    "RUNNING",
    "SUCCEEDED",
    "RETRYABLE_FAILED",
    "EXHAUSTED",
)


def _json_type() -> sa.types.TypeEngine:
    return postgresql.JSONB().with_variant(sa.JSON(), "sqlite")


def _create_intent_guard() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute(
            """
            CREATE FUNCTION reject_job_intent_mutation() RETURNS trigger AS $$
            BEGIN
                IF ROW(OLD.task_name, OLD.queue_name, OLD.resource_type,
                       OLD.resource_id, OLD.idempotency_key, OLD.intent,
                       OLD.max_attempts, OLD.correlation_id)
                   IS DISTINCT FROM
                   ROW(NEW.task_name, NEW.queue_name, NEW.resource_type,
                       NEW.resource_id, NEW.idempotency_key, NEW.intent,
                       NEW.max_attempts, NEW.correlation_id) THEN
                    RAISE EXCEPTION 'job intent is immutable';
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_job_executions_immutable_intent
            BEFORE UPDATE ON job_executions
            FOR EACH ROW EXECUTE FUNCTION reject_job_intent_mutation()
            """
        )
    elif dialect == "sqlite":
        op.execute(
            """
            CREATE TRIGGER trg_job_executions_immutable_intent
            BEFORE UPDATE ON job_executions
            WHEN OLD.task_name IS NOT NEW.task_name
              OR OLD.queue_name IS NOT NEW.queue_name
              OR OLD.resource_type IS NOT NEW.resource_type
              OR OLD.resource_id IS NOT NEW.resource_id
              OR OLD.idempotency_key IS NOT NEW.idempotency_key
              OR OLD.intent IS NOT NEW.intent
              OR OLD.max_attempts IS NOT NEW.max_attempts
              OR OLD.correlation_id IS NOT NEW.correlation_id
            BEGIN
                SELECT RAISE(ABORT, 'job intent is immutable');
            END
            """
        )


def _drop_intent_guard() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute(
            "DROP TRIGGER IF EXISTS trg_job_executions_immutable_intent "
            "ON job_executions"
        )
        op.execute("DROP FUNCTION IF EXISTS reject_job_intent_mutation()")
    elif dialect == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS trg_job_executions_immutable_intent")


def upgrade() -> None:
    op.create_table(
        "job_executions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_name", sa.String(length=128), nullable=False),
        sa.Column("queue_name", sa.String(length=64), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=128), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("intent", _json_type(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("total_attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("replay_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("correlation_id", sa.String(length=128), nullable=False),
        sa.Column("last_error_code", sa.String(length=64), nullable=True),
        sa.Column("cancel_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "max_attempts > 0", name="ck_job_executions_job_max_attempts_positive"
        ),
        sa.CheckConstraint(
            "total_attempts >= 0",
            name="ck_job_executions_job_total_attempts_non_negative",
        ),
        sa.CheckConstraint(
            "replay_count >= 0", name="ck_job_executions_job_replay_count_non_negative"
        ),
        sa.CheckConstraint(
            "version > 0", name="ck_job_executions_job_version_positive"
        ),
        sa.CheckConstraint(
            "status IN (" + ", ".join(f"'{value}'" for value in JOB_STATUSES) + ")",
            name="ck_job_executions_job_execution_status",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_job_executions"),
        sa.UniqueConstraint(
            "task_name",
            "idempotency_key",
            name="uq_job_executions_task_idempotency",
        ),
    )
    op.create_index(
        "ix_job_executions_status_scheduled",
        "job_executions",
        ["status", "scheduled_at"],
    )
    op.create_index(
        "ix_job_executions_resource",
        "job_executions",
        ["resource_type", "resource_id"],
    )
    op.create_table(
        "job_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_no", sa.Integer(), nullable=False),
        sa.Column("worker_task_id", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("safe_error_code", sa.String(length=64), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "attempt_no > 0", name="ck_job_attempts_job_attempt_no_positive"
        ),
        sa.CheckConstraint(
            "status IN (" + ", ".join(f"'{value}'" for value in ATTEMPT_STATUSES) + ")",
            name="ck_job_attempts_job_attempt_status",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["job_executions.id"],
            name="fk_job_attempts_job_id_job_executions",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_job_attempts"),
        sa.UniqueConstraint(
            "job_id", "attempt_no", name="uq_job_attempts_job_attempt_no"
        ),
        sa.UniqueConstraint("worker_task_id", name="uq_job_attempts_worker_task_id"),
    )
    op.create_index(
        "ix_job_attempts_status_started",
        "job_attempts",
        ["status", "started_at"],
    )
    _create_intent_guard()


def downgrade() -> None:
    _drop_intent_guard()
    op.drop_index("ix_job_attempts_status_started", table_name="job_attempts")
    op.drop_table("job_attempts")
    op.drop_index("ix_job_executions_resource", table_name="job_executions")
    op.drop_index("ix_job_executions_status_scheduled", table_name="job_executions")
    op.drop_table("job_executions")
