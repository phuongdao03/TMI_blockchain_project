"""Create blockchain transactions and early certificate schema.

Revision ID: 0012_blockchain
Revises: 0011_payments
Create Date: 2026-07-31
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0012_blockchain"
down_revision: str | None = "0011_payments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TRANSACTION_STATUSES = (
    "CREATED",
    "SIGNING",
    "BROADCAST",
    "CONFIRMED",
    "FAILED",
    "REPLACED",
)
CERTIFICATE_STATUSES = ("ACTIVE", "EXPIRED", "REVOKED")


def _timestamps() -> tuple[sa.Column, sa.Column]:
    return (
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
    )


def upgrade() -> None:
    op.create_table(
        "certificates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("certificate_number", sa.String(length=64), nullable=False),
        sa.Column("dossier_id", sa.Uuid(), nullable=False),
        sa.Column("current_version_no", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                *CERTIFICATE_STATUSES,
                name="certificate_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("public_token_hash", sa.CHAR(length=64), nullable=False),
        sa.Column("pdf_media_id", sa.Uuid(), nullable=True),
        sa.Column("qr_payload", sa.Text(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "current_version_no > 0",
            name="current_version_no_positive",
        ),
        sa.ForeignKeyConstraint(
            ["dossier_id"],
            ["dossiers.id"],
            name="fk_certificates_dossier_id_dossiers",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["pdf_media_id"],
            ["media_assets.id"],
            name="fk_certificates_pdf_media_id_media_assets",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_certificates"),
        sa.UniqueConstraint(
            "certificate_number",
            name="uq_certificates_certificate_number",
        ),
        sa.UniqueConstraint(
            "public_token_hash",
            name="uq_certificates_public_token_hash",
        ),
    )
    op.create_index(
        "ix_certificates_dossier_status",
        "certificates",
        ["dossier_id", "status"],
    )
    op.create_table(
        "blockchain_transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("dossier_id", sa.Uuid(), nullable=False),
        sa.Column("dossier_version_id", sa.Uuid(), nullable=False),
        sa.Column("certificate_id", sa.Uuid(), nullable=True),
        sa.Column("network", sa.String(length=32), nullable=False),
        sa.Column("chain_id", sa.BigInteger(), nullable=False),
        sa.Column("contract_address", sa.CHAR(length=42), nullable=False),
        sa.Column("method", sa.String(length=64), nullable=False),
        sa.Column("payload_hash", sa.CHAR(length=64), nullable=False),
        sa.Column("tx_hash", sa.CHAR(length=66), nullable=True),
        sa.Column("nonce", sa.BigInteger(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                *TRANSACTION_STATUSES,
                name="blockchain_tx_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
            server_default="CREATED",
        ),
        sa.Column(
            "confirmations",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("broadcast_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("chain_id > 0", name="chain_id_positive"),
        sa.CheckConstraint(
            "confirmations >= 0",
            name="confirmations_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["dossier_id"],
            ["dossiers.id"],
            name="fk_blockchain_transactions_dossier_id_dossiers",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["dossier_version_id"],
            ["dossier_versions.id"],
            name=("fk_blockchain_transactions_dossier_version_id_dossier_versions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["certificate_id"],
            ["certificates.id"],
            name="fk_blockchain_transactions_certificate_id_certificates",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_blockchain_transactions"),
        sa.UniqueConstraint(
            "dossier_version_id",
            "network",
            "contract_address",
            "method",
            "payload_hash",
            name="uq_blockchain_transactions_idempotent_request",
        ),
        sa.UniqueConstraint(
            "tx_hash",
            name="uq_blockchain_transactions_tx_hash",
        ),
    )
    op.create_index(
        "ix_blockchain_transactions_status_created_at",
        "blockchain_transactions",
        ["status", "created_at"],
    )
    op.create_table(
        "certificate_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("certificate_id", sa.Uuid(), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("dossier_version_id", sa.Uuid(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("metadata_hash", sa.CHAR(length=64), nullable=False),
        sa.Column("blockchain_transaction_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("version_no > 0", name="version_no_positive"),
        sa.ForeignKeyConstraint(
            ["certificate_id"],
            ["certificates.id"],
            name="fk_certificate_versions_certificate_id_certificates",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["dossier_version_id"],
            ["dossier_versions.id"],
            name="fk_certificate_versions_dossier_version_id_dossier_versions",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["blockchain_transaction_id"],
            ["blockchain_transactions.id"],
            name="fk_cert_versions_blockchain_tx",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_certificate_versions"),
        sa.UniqueConstraint(
            "certificate_id",
            "version_no",
            name="uq_certificate_versions_certificate_id_version_no",
        ),
    )


def downgrade() -> None:
    op.drop_table("certificate_versions")
    op.drop_index(
        "ix_blockchain_transactions_status_created_at",
        table_name="blockchain_transactions",
    )
    op.drop_table("blockchain_transactions")
    op.drop_index(
        "ix_certificates_dossier_status",
        table_name="certificates",
    )
    op.drop_table("certificates")
