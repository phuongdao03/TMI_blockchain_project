"""Add audit actor identity, retention and tamper-evident metadata.

Revision ID: 0048_audit_integrity
Revises: 0047_certificate_versioning
Create Date: 2026-08-11
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0048_audit_integrity"
down_revision: str | None = "0047_certificate_versioning"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _create_append_only_guards() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute(
            """
            CREATE FUNCTION reject_audit_log_mutation() RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'audit_logs are append-only';
            END;
            $$ LANGUAGE plpgsql
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_audit_logs_reject_update
            BEFORE UPDATE ON audit_logs
            FOR EACH ROW EXECUTE FUNCTION reject_audit_log_mutation()
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_audit_logs_reject_delete
            BEFORE DELETE ON audit_logs
            FOR EACH ROW EXECUTE FUNCTION reject_audit_log_mutation()
            """
        )
    elif dialect == "sqlite":
        op.execute(
            """
            CREATE TRIGGER trg_audit_logs_reject_update
            BEFORE UPDATE ON audit_logs
            BEGIN
                SELECT RAISE(ABORT, 'audit_logs are append-only');
            END
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_audit_logs_reject_delete
            BEFORE DELETE ON audit_logs
            BEGIN
                SELECT RAISE(ABORT, 'audit_logs are append-only');
            END
            """
        )


def _drop_append_only_guards() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_audit_logs_reject_update ON audit_logs")
        op.execute("DROP TRIGGER IF EXISTS trg_audit_logs_reject_delete ON audit_logs")
        op.execute("DROP FUNCTION IF EXISTS reject_audit_log_mutation()")
    elif dialect == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS trg_audit_logs_reject_update")
        op.execute("DROP TRIGGER IF EXISTS trg_audit_logs_reject_delete")


def upgrade() -> None:
    with op.batch_alter_table("audit_logs") as batch_op:
        batch_op.add_column(sa.Column("actor_type", sa.String(16), nullable=True))
        batch_op.add_column(sa.Column("actor_service", sa.String(128), nullable=True))
        batch_op.add_column(sa.Column("integrity_version", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("integrity_key_id", sa.String(64), nullable=True))
        batch_op.add_column(sa.Column("integrity_hash", sa.CHAR(64), nullable=True))
        batch_op.add_column(
            sa.Column("retention_until", sa.DateTime(timezone=True), nullable=True)
        )

    op.execute(
        sa.text(
            "UPDATE audit_logs SET actor_type = CASE "
            "WHEN actor_user_id IS NULL THEN 'ANONYMOUS' ELSE 'USER' END"
        )
    )
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute(
            sa.text(
                "UPDATE audit_logs SET retention_until = "
                "created_at + INTERVAL '2555 days'"
            )
        )
    elif dialect == "sqlite":
        op.execute(
            sa.text(
                "UPDATE audit_logs SET retention_until = "
                "datetime(created_at, '+2555 days')"
            )
        )

    with op.batch_alter_table("audit_logs") as batch_op:
        batch_op.alter_column("actor_type", existing_type=sa.String(16), nullable=False)
        batch_op.create_check_constraint(
            "audit_actor_type",
            "actor_type IN ('USER', 'SERVICE', 'ANONYMOUS')",
        )
        batch_op.create_check_constraint(
            "audit_actor_identity",
            "(actor_type = 'USER' AND actor_user_id IS NOT NULL "
            "AND actor_service IS NULL) OR "
            "(actor_type = 'SERVICE' AND actor_user_id IS NULL "
            "AND actor_service IS NOT NULL) OR "
            "(actor_type = 'ANONYMOUS' AND actor_user_id IS NULL "
            "AND actor_service IS NULL)",
        )
        batch_op.create_check_constraint(
            "audit_integrity_metadata",
            "(integrity_hash IS NULL AND integrity_version IS NULL "
            "AND integrity_key_id IS NULL) OR "
            "(length(integrity_hash) = 64 AND integrity_version = 1 "
            "AND integrity_key_id IS NOT NULL)",
        )

    op.create_index(
        "ix_audit_logs_action_created", "audit_logs", ["action", "created_at"]
    )
    op.create_index("ix_audit_logs_retention_until", "audit_logs", ["retention_until"])
    _create_append_only_guards()


def downgrade() -> None:
    _drop_append_only_guards()
    op.drop_index("ix_audit_logs_retention_until", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action_created", table_name="audit_logs")
    with op.batch_alter_table("audit_logs") as batch_op:
        batch_op.drop_constraint("audit_integrity_metadata", type_="check")
        batch_op.drop_constraint("audit_actor_identity", type_="check")
        batch_op.drop_constraint("audit_actor_type", type_="check")
        batch_op.drop_column("retention_until")
        batch_op.drop_column("integrity_hash")
        batch_op.drop_column("integrity_key_id")
        batch_op.drop_column("integrity_version")
        batch_op.drop_column("actor_service")
        batch_op.drop_column("actor_type")
