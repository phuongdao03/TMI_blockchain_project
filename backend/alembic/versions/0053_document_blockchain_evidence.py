"""Add document-level blockchain evidence.

Revision ID: 0053_document_chain_evidence
Revises: 0052_document_hash_claims
Create Date: 2026-08-12
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0053_document_chain_evidence"
down_revision: str | None = "0052_document_hash_claims"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_blockchain_evidences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_hash_claim_id", sa.Uuid(), nullable=False),
        sa.Column("dossier_id", sa.Uuid(), nullable=False),
        sa.Column("dossier_version_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_key", sa.CHAR(length=64), nullable=False),
        sa.Column("commitment", sa.CHAR(length=64), nullable=False),
        sa.Column("submitter_reference", sa.CHAR(length=64), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("predecessor_evidence_id", sa.Uuid(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="EVIDENCE_QUEUED",
        ),
        sa.CheckConstraint(
            "length(evidence_key) = 64 AND length(commitment) = 64 "
            "AND length(submitter_reference) = 64",
            name="document_blockchain_evidence_hash_lengths",
        ),
        sa.CheckConstraint(
            "(version_no = 1 AND predecessor_evidence_id IS NULL) OR "
            "(version_no > 1 AND predecessor_evidence_id IS NOT NULL)",
            name="document_blockchain_evidence_lineage",
        ),
        sa.CheckConstraint(
            "status IN ('EVIDENCE_QUEUED', 'EVIDENCE_BROADCAST', "
            "'EVIDENCE_CONFIRMED', 'EVIDENCE_FAILED')",
            name="document_blockchain_evidence_status_valid",
        ),
        sa.ForeignKeyConstraint(
            ["document_hash_claim_id"],
            ["document_hash_claims.id"],
            name="fk_document_blockchain_evidences_claim_id_claims",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["dossier_id"],
            ["dossiers.id"],
            name="fk_document_blockchain_evidences_dossier_id_dossiers",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["dossier_version_id"],
            ["dossier_versions.id"],
            name="fk_document_blockchain_evidences_version_id_versions",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["predecessor_evidence_id"],
            ["document_blockchain_evidences.id"],
            name="fk_document_blockchain_evidences_predecessor_id_self",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_document_blockchain_evidences"),
        sa.UniqueConstraint(
            "document_hash_claim_id",
            name="uq_document_blockchain_evidences_claim_id",
        ),
        sa.UniqueConstraint(
            "evidence_key",
            name="uq_document_blockchain_evidences_evidence_key",
        ),
        sa.UniqueConstraint(
            "predecessor_evidence_id",
            name="uq_document_blockchain_evidences_predecessor_id",
        ),
    )
    op.create_index(
        "ix_document_blockchain_evidences_status_recorded_at",
        "document_blockchain_evidences",
        ["status", "recorded_at"],
    )
    op.create_index(
        "ix_document_blockchain_evidences_dossier_version_id",
        "document_blockchain_evidences",
        ["dossier_id", "dossier_version_id"],
    )
    with op.batch_alter_table("blockchain_transactions") as batch_op:
        batch_op.add_column(sa.Column("document_evidence_id", sa.Uuid()))
        batch_op.create_foreign_key(
            "fk_blockchain_transactions_document_evidence_id_evidences",
            "document_blockchain_evidences",
            ["document_evidence_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_unique_constraint(
            "uq_blockchain_transactions_document_evidence_id",
            ["document_evidence_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("blockchain_transactions") as batch_op:
        batch_op.drop_constraint(
            "uq_blockchain_transactions_document_evidence_id",
            type_="unique",
        )
        batch_op.drop_constraint(
            "fk_blockchain_transactions_document_evidence_id_evidences",
            type_="foreignkey",
        )
        batch_op.drop_column("document_evidence_id")
    op.drop_index(
        "ix_document_blockchain_evidences_dossier_version_id",
        table_name="document_blockchain_evidences",
    )
    op.drop_index(
        "ix_document_blockchain_evidences_status_recorded_at",
        table_name="document_blockchain_evidences",
    )
    op.drop_table("document_blockchain_evidences")
