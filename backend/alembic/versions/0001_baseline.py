"""Establish the migration lineage before domain tables are introduced.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-07-30
"""

from collections.abc import Sequence

revision: str = "0001_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Record the baseline without creating out-of-scope domain tables."""


def downgrade() -> None:
    """Remove the baseline revision marker."""
