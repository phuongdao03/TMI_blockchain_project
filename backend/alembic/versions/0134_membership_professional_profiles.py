"""Add membership gated professional profile fields.

Revision ID: 0134_membership_professional_profiles
Revises: 0133_membership_benefit_requests
"""

import sqlalchemy as sa

from alembic import op

revision = "0134_membership_professional_profiles"
down_revision = "0133_membership_benefit_requests"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "community_profiles",
        sa.Column("professional_title", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "community_profiles",
        sa.Column("organization", sa.String(length=160), nullable=True),
    )
    op.add_column(
        "community_profiles",
        sa.Column("activity_fields", sa.String(length=300), nullable=True),
    )
    op.add_column(
        "community_profiles",
        sa.Column(
            "professional_links",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("community_profiles", "professional_links")
    op.drop_column("community_profiles", "activity_fields")
    op.drop_column("community_profiles", "organization")
    op.drop_column("community_profiles", "professional_title")
