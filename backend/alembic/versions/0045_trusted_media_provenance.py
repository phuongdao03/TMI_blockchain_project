"""Record trusted media hash provenance.

Revision ID: 0045_trusted_media_provenance
Revises: 0044_secure_media_inspection
Create Date: 2026-08-10
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0045_trusted_media_provenance"
down_revision: str | None = "0044_secure_media_inspection"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("media_assets") as batch_op:
        batch_op.add_column(
            sa.Column("hash_algorithm", sa.String(length=16), nullable=True)
        )
        batch_op.add_column(
            sa.Column("hash_byte_length", sa.BigInteger(), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "inspection_policy_version",
                sa.String(length=64),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column("hash_storage_version", sa.BigInteger(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("hash_computed_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.create_check_constraint(
            "hash_byte_length_non_negative",
            "hash_byte_length IS NULL OR hash_byte_length >= 0",
        )
        batch_op.create_check_constraint(
            "hash_storage_version_non_negative",
            "hash_storage_version IS NULL OR hash_storage_version >= 0",
        )

    # Historical checksums cannot be silently promoted to trusted provenance.
    # Retain their known metadata and force the inspection service to re-read
    # the stored object before a future submission can use them.
    op.execute(
        sa.text(
            "UPDATE media_assets SET "
            "hash_algorithm = 'SHA-256', "
            "hash_byte_length = bytes, "
            "inspection_policy_version = 'legacy-unverified-v1', "
            "hash_storage_version = cloudinary_version, "
            "hash_computed_at = COALESCE(inspected_at, updated_at, created_at) "
            "WHERE status = 'ACTIVE' AND sha256 IS NOT NULL"
        )
    )


def downgrade() -> None:
    with op.batch_alter_table("media_assets") as batch_op:
        batch_op.drop_constraint(
            "hash_storage_version_non_negative",
            type_="check",
        )
        batch_op.drop_constraint(
            "hash_byte_length_non_negative",
            type_="check",
        )
        batch_op.drop_column("hash_computed_at")
        batch_op.drop_column("hash_storage_version")
        batch_op.drop_column("inspection_policy_version")
        batch_op.drop_column("hash_byte_length")
        batch_op.drop_column("hash_algorithm")
