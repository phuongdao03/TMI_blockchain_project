"""Add private media encryption metadata.

Revision ID: 0051_private_media_encryption
Revises: 0050_job_operations_permission
Create Date: 2026-08-12
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0051_private_media_encryption"
down_revision: str | None = "0050_job_operations_permission"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("media_assets") as batch:
        batch.add_column(
            sa.Column(
                "confidentiality",
                sa.String(16),
                nullable=False,
                server_default="PRIVATE",
            )
        )
        batch.add_column(
            sa.Column(
                "encryption_status",
                sa.String(32),
                nullable=False,
                server_default="PENDING",
            )
        )
        batch.add_column(sa.Column("encryption_algorithm", sa.String(32)))
        batch.add_column(sa.Column("encryption_key_id", sa.String(64)))
        batch.add_column(sa.Column("encryption_nonce", sa.LargeBinary(12)))
        batch.add_column(sa.Column("encryption_tag", sa.LargeBinary(16)))
        batch.add_column(sa.Column("encrypted_object_public_id", sa.Text()))
        batch.add_column(sa.Column("encrypted_object_version", sa.BigInteger()))
        batch.add_column(sa.Column("encrypted_bytes", sa.BigInteger()))
        batch.add_column(sa.Column("encrypted_at", sa.DateTime(timezone=True)))
        batch.create_unique_constraint(
            "uq_media_assets_encrypted_object_public_id",
            ["encrypted_object_public_id"],
        )
        batch.create_check_constraint(
            "media_confidentiality_valid",
            "confidentiality IN ('PRIVATE', 'PUBLIC')",
        )
        batch.create_check_constraint(
            "media_encryption_status_valid",
            "encryption_status IN ('PENDING', 'ENCRYPTED', 'NOT_REQUIRED', "
            "'LEGACY_UNENCRYPTED', 'FAILED')",
        )

    op.execute(
        sa.text(
            "UPDATE media_assets SET confidentiality = 'PUBLIC', "
            "encryption_status = 'NOT_REQUIRED' "
            "WHERE cloudinary_public_id LIKE '%/public-work/%'"
        )
    )
    op.execute(
        sa.text(
            "UPDATE media_assets SET encryption_status = 'LEGACY_UNENCRYPTED' "
            "WHERE confidentiality = 'PRIVATE'"
        )
    )
    # Fail closed: legacy private plaintext must not remain downloadable while
    # the inspection worker migrates it to encrypted object storage.
    op.execute(
        sa.text(
            "UPDATE media_assets SET status = 'QUARANTINED' "
            "WHERE confidentiality = 'PRIVATE' AND status = 'ACTIVE'"
        )
    )


def downgrade() -> None:
    with op.batch_alter_table("media_assets") as batch:
        batch.drop_constraint("media_encryption_status_valid", type_="check")
        batch.drop_constraint("media_confidentiality_valid", type_="check")
        batch.drop_constraint(
            "uq_media_assets_encrypted_object_public_id",
            type_="unique",
        )
        batch.drop_column("encrypted_at")
        batch.drop_column("encrypted_object_public_id")
        batch.drop_column("encrypted_object_version")
        batch.drop_column("encrypted_bytes")
        batch.drop_column("encryption_tag")
        batch.drop_column("encryption_nonce")
        batch.drop_column("encryption_key_id")
        batch.drop_column("encryption_algorithm")
        batch.drop_column("encryption_status")
        batch.drop_column("confidentiality")
