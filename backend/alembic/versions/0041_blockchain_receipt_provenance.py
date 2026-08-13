"""Add canonical blockchain receipt provenance.

Revision ID: 0041_blockchain_receipt_provenance
Revises: 0040_payment_cancelled_status
Create Date: 2026-08-10
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0041_blockchain_receipt_provenance"
down_revision: str | None = "0040_payment_cancelled_status"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "blockchain_transactions",
        sa.Column("receipt_block_number", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "blockchain_transactions",
        sa.Column("receipt_block_hash", sa.CHAR(length=66), nullable=True),
    )
    op.add_column(
        "blockchain_transactions",
        sa.Column("receipt_event_name", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("blockchain_transactions", "receipt_event_name")
    op.drop_column("blockchain_transactions", "receipt_block_hash")
    op.drop_column("blockchain_transactions", "receipt_block_number")
