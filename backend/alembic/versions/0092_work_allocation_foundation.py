"""Add additive work-allocation foundation.

Revision ID: 0092_work_allocation_foundation
Revises: 0091_location_retention
Create Date: 2026-09-22
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0092_work_allocation_foundation"
down_revision: str | None = "0091_location_retention"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "work_allocations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("objective", sa.String(length=240), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("dossier_id", sa.Uuid()),
        sa.Column("dossier_version_id", sa.Uuid()),
        sa.Column("due_at", sa.DateTime(timezone=True)),
        sa.Column(
            "priority", sa.String(length=16), server_default="MEDIUM", nullable=False
        ),
        sa.Column(
            "status", sa.String(length=16), server_default="DRAFT", nullable=False
        ),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
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
            "kind IN ('GENERIC', 'DOSSIER_REVIEW')",
            name="work_allocation_kind",
        ),
        sa.CheckConstraint(
            "priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="work_allocation_priority",
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'ACTIVE', 'COMPLETED', 'CANCELLED')",
            name="work_allocation_status",
        ),
        sa.CheckConstraint(
            "(kind = 'GENERIC' AND dossier_id IS NULL AND dossier_version_id IS NULL) "
            "OR (kind = 'DOSSIER_REVIEW' AND dossier_id IS NOT NULL "
            "AND dossier_version_id IS NOT NULL)",
            name="work_allocation_dossier_reference",
        ),
        sa.ForeignKeyConstraint(["dossier_id"], ["dossiers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["dossier_version_id"], ["dossier_versions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_work_allocations_status_due",
        "work_allocations",
        ["status", "due_at"],
    )
    op.create_index(
        "ix_work_allocations_dossier_version_status",
        "work_allocations",
        ["dossier_version_id", "status"],
    )

    op.create_table(
        "work_scopes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("allocation_id", sa.Uuid(), nullable=False),
        sa.Column("scope_type", sa.String(length=16), nullable=False),
        sa.Column("dossier_evidence_id", sa.Uuid()),
        sa.Column("group_label", sa.String(length=240)),
        sa.Column(
            "requires_dual_review",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
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
            "scope_type IN ('EVIDENCE', 'GROUP')", name="work_scope_type"
        ),
        sa.CheckConstraint(
            "(scope_type = 'EVIDENCE' AND dossier_evidence_id IS NOT NULL "
            "AND group_label IS NULL) OR "
            "(scope_type = 'GROUP' AND dossier_evidence_id IS NULL "
            "AND length(trim(group_label)) BETWEEN 1 AND 240)",
            name="work_scope_source",
        ),
        sa.ForeignKeyConstraint(
            ["allocation_id"], ["work_allocations.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["dossier_evidence_id"], ["dossier_evidences.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "allocation_id",
            "dossier_evidence_id",
            name="uq_work_scopes_allocation_evidence",
        ),
        sa.UniqueConstraint(
            "allocation_id",
            "group_label",
            name="uq_work_scopes_allocation_group_label",
        ),
    )
    op.create_index("ix_work_scopes_allocation", "work_scopes", ["allocation_id"])

    op.create_table(
        "allocation_members",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("allocation_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("responsibility", sa.String(length=16), nullable=False),
        sa.Column("assigned_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("deactivated_at", sa.DateTime(timezone=True)),
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
            "responsibility IN ('LEAD', 'CONTRIBUTOR', 'REVIEWER')",
            name="allocation_responsibility",
        ),
        sa.CheckConstraint(
            "(is_active = true AND deactivated_at IS NULL) OR "
            "(is_active = false AND deactivated_at IS NOT NULL)",
            name="allocation_member_active_lifecycle",
        ),
        sa.ForeignKeyConstraint(
            ["allocation_id"], ["work_allocations.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["assigned_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "allocation_id", "user_id", name="uq_allocation_members_allocation_user"
        ),
    )
    op.create_index(
        "ix_allocation_members_user_active",
        "allocation_members",
        ["user_id", "is_active"],
    )


def downgrade() -> None:
    op.drop_index("ix_allocation_members_user_active", table_name="allocation_members")
    op.drop_table("allocation_members")
    op.drop_index("ix_work_scopes_allocation", table_name="work_scopes")
    op.drop_table("work_scopes")
    op.drop_index(
        "ix_work_allocations_dossier_version_status", table_name="work_allocations"
    )
    op.drop_index("ix_work_allocations_status_due", table_name="work_allocations")
    op.drop_table("work_allocations")
