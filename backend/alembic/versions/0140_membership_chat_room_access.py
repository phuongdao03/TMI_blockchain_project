"""Add audited, room-specific membership access grants.

Revision ID: 0140_membership_chat_room_access
Revises: 0139_expand_artwork_type_options
"""

import sqlalchemy as sa

from alembic import op

revision = "0140_membership_chat_room_access"
down_revision = "0139_expand_artwork_type_options"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "membership_chat_room_access",
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("room", sa.String(16), primary_key=True),
        sa.Column(
            "granted_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("reason", sa.String(240), nullable=False),
        sa.Column(
            "granted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "room IN ('MEMBER', 'COMPANION', 'PRESTIGE')", name="valid_room"
        ),
        sa.CheckConstraint(
            "length(trim(reason)) BETWEEN 3 AND 240", name="valid_reason"
        ),
    )
    op.create_index(
        "ix_membership_chat_room_access_room",
        "membership_chat_room_access",
        ["room"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_membership_chat_room_access_room",
        table_name="membership_chat_room_access",
    )
    op.drop_table("membership_chat_room_access")
