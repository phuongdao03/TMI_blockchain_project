"""Add public content reporting workflow.

Revision ID: 0017_content_reports
Revises: 0016_public_media
Create Date: 2026-07-31
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0017_content_reports"
down_revision: str | None = "0016_public_media"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "content_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("public_work_id", sa.Uuid(), nullable=False),
        sa.Column("reporter_user_id", sa.Uuid(), nullable=True),
        sa.Column("reporter_email_hash", sa.String(length=64), nullable=True),
        sa.Column("reporter_email_encrypted", sa.LargeBinary(), nullable=True),
        sa.Column(
            "reason",
            sa.Enum(
                "COPYRIGHT",
                "INCORRECT_INFORMATION",
                "INAPPROPRIATE_CONTENT",
                "OTHER",
                name="content_report_reason",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("dedup_key", sa.String(length=64), nullable=False),
        sa.Column("reporter_ip_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "OPEN",
                "UNDER_REVIEW",
                "RESOLVED",
                "DISMISSED",
                "SUSPENDED",
                name="content_report_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
            server_default="OPEN",
        ),
        sa.Column("assigned_to_user_id", sa.Uuid(), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["public_work_id"],
            ["public_works.id"],
            name="fk_content_reports_public_work_id_public_works",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reporter_user_id"],
            ["users.id"],
            name="fk_content_reports_reporter_user_id_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_to_user_id"],
            ["users.id"],
            name="fk_content_reports_assigned_to_user_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_content_reports"),
        sa.UniqueConstraint("dedup_key", name="uq_content_reports_dedup_key"),
    )
    op.create_index(
        "ix_content_reports_status_created",
        "content_reports",
        ["status", "created_at"],
    )
    op.create_index(
        "ix_content_reports_work_created",
        "content_reports",
        ["public_work_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_content_reports_work_created", table_name="content_reports")
    op.drop_index("ix_content_reports_status_created", table_name="content_reports")
    op.drop_table("content_reports")
