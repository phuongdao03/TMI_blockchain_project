"""Add tier based event registration windows.

Revision ID: 0135_membership_event_priority_windows
Revises: 0134_membership_professional_profiles
"""

import sqlalchemy as sa

from alembic import op

revision = "0135_membership_event_priority_windows"
down_revision = "0134_membership_professional_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("community_events") as batch:
        batch.add_column(
            sa.Column(
                "registration_opens_at", sa.DateTime(timezone=True), nullable=True
            )
        )
        batch.add_column(
            sa.Column("priority_tier", sa.String(length=16), nullable=True)
        )
        batch.add_column(
            sa.Column("priority_opens_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch.create_check_constraint(
            "valid_priority_tier",
            "priority_tier IS NULL OR priority_tier IN ('COMPANION', 'PRESTIGE')",
        )


def downgrade() -> None:
    with op.batch_alter_table("community_events") as batch:
        batch.drop_constraint("valid_priority_tier", type_="check")
        batch.drop_column("priority_opens_at")
        batch.drop_column("priority_tier")
        batch.drop_column("registration_opens_at")
