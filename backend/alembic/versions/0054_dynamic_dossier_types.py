"""Add versioned dynamic dossier types and scoped review evidence.

Revision ID: 0054_dynamic_dossier_types
Revises: 0053_document_chain_evidence
Create Date: 2026-08-23
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0054_dynamic_dossier_types"
down_revision: str | None = "0053_document_chain_evidence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dossier_types",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(
            ["category_id"], ["categories.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_dossier_types"),
        sa.UniqueConstraint("code", name="uq_dossier_types_code"),
    )
    op.create_table(
        "dossier_type_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("dossier_type_id", sa.Uuid(), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("schema_json", sa.JSON(), nullable=False),
        sa.CheckConstraint("version_no > 0", name="dossier_type_version_no_positive"),
        sa.ForeignKeyConstraint(
            ["dossier_type_id"], ["dossier_types.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_dossier_type_versions"),
        sa.UniqueConstraint(
            "dossier_type_id",
            "version_no",
            name="uq_dossier_type_versions_type_id_version_no",
        ),
    )

    with op.batch_alter_table("dossiers") as batch:
        batch.add_column(sa.Column("dossier_type_id", sa.Uuid()))
        batch.add_column(sa.Column("dossier_type_version_id", sa.Uuid()))
        batch.add_column(
            sa.Column(
                "form_data_json",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'{}'"),
            )
        )
        batch.create_foreign_key(
            "fk_dossiers_dossier_type_id_types",
            "dossier_types",
            ["dossier_type_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch.create_foreign_key(
            "fk_dossiers_dossier_type_version_id_versions",
            "dossier_type_versions",
            ["dossier_type_version_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    with op.batch_alter_table("dossier_evidences") as batch:
        batch.add_column(sa.Column("evidence_role", sa.String(length=64)))
        batch.add_column(
            sa.Column(
                "access_scope",
                sa.String(length=16),
                nullable=False,
                server_default="PRIVATE",
            )
        )
        batch.create_check_constraint(
            "dossier_evidence_access_scope_valid",
            "access_scope IN ('PUBLIC', 'PRIVATE', 'REVIEWER_ONLY', 'ADMIN_ONLY')",
        )
    op.execute(
        sa.text(
            "UPDATE dossier_evidences SET evidence_role = evidence_type, "
            "access_scope = CASE WHEN is_public THEN 'PUBLIC' ELSE 'PRIVATE' END"
        )
    )

    with op.batch_alter_table("review_assignments") as batch:
        batch.add_column(
            sa.Column(
                "is_primary",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
    op.create_index(
        "uq_review_assignments_primary_version",
        "review_assignments",
        ["dossier_version_id"],
        unique=True,
        sqlite_where=sa.text("is_primary = 1"),
        postgresql_where=sa.text("is_primary"),
    )

    with op.batch_alter_table("reviews") as batch:
        batch.add_column(
            sa.Column(
                "checklist_answers",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'{}'"),
            )
        )
        batch.add_column(sa.Column("applicant_feedback", sa.Text()))


def downgrade() -> None:
    with op.batch_alter_table("reviews") as batch:
        batch.drop_column("applicant_feedback")
        batch.drop_column("checklist_answers")

    op.drop_index(
        "uq_review_assignments_primary_version",
        table_name="review_assignments",
    )
    with op.batch_alter_table("review_assignments") as batch:
        batch.drop_column("is_primary")

    with op.batch_alter_table("dossier_evidences") as batch:
        batch.drop_constraint("dossier_evidence_access_scope_valid", type_="check")
        batch.drop_column("access_scope")
        batch.drop_column("evidence_role")

    with op.batch_alter_table("dossiers") as batch:
        batch.drop_constraint(
            "fk_dossiers_dossier_type_version_id_versions", type_="foreignkey"
        )
        batch.drop_constraint("fk_dossiers_dossier_type_id_types", type_="foreignkey")
        batch.drop_column("form_data_json")
        batch.drop_column("dossier_type_version_id")
        batch.drop_column("dossier_type_id")

    op.drop_table("dossier_type_versions")
    op.drop_table("dossier_types")
