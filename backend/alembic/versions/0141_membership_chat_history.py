"""Add cursor history index and message edit timestamp.

Revision ID: 0141_membership_chat_history
Revises: 0140_membership_chat_room_access
"""

import sqlalchemy as sa

from alembic import op

revision = "0141_membership_chat_history"
down_revision = "0140_membership_chat_room_access"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "community_chat_messages",
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.drop_index(
        "ix_community_chat_messages_room",
        table_name="community_chat_messages",
    )
    op.create_index(
        "ix_community_chat_messages_room_created_id",
        "community_chat_messages",
        ["room", "created_at", "id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_community_chat_messages_room_created_id",
        table_name="community_chat_messages",
    )
    op.create_index(
        "ix_community_chat_messages_room",
        "community_chat_messages",
        ["room"],
    )
    op.drop_column("community_chat_messages", "edited_at")
