"""Add community admin workspaces and temporary member restrictions.

Revision ID: 0109_community_admin_workspaces
Revises: 0108_community_interactions
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0109_community_admin_workspaces"
down_revision: str | None = "0108_community_interactions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_EVENT_TARGETS = "'POST', 'COMMENT', 'CATEGORY', 'SETTINGS', 'MEMBER'"
_EVENT_ACTIONS = (
    "'SUBMITTED', 'PUBLISHED', 'REJECTED', 'OWNER_DELETED', 'POST_HIDDEN', "
    "'POST_RESTORED', 'COMMENT_HIDDEN', 'COMMENT_RESTORED', "
    "'REPORT_DISMISSED', 'CATEGORY_CREATED', 'CATEGORY_UPDATED', "
    "'SETTINGS_UPDATED', 'POST_PINNED', 'POST_UNPINNED', 'COMMENTS_LOCKED', "
    "'COMMENTS_UNLOCKED', 'POST_ADMIN_DELETED', 'POST_ADMIN_RESTORED', "
    "'COMMENT_ADMIN_DELETED', 'COMMENT_ADMIN_RESTORED', 'MEMBER_RESTRICTED', "
    "'MEMBER_RESTRICTION_REVOKED'"
)


def upgrade() -> None:
    with op.batch_alter_table("community_posts") as batch_op:
        batch_op.add_column(sa.Column("pinned_at", sa.DateTime(timezone=True)))
        batch_op.add_column(
            sa.Column("comments_locked_at", sa.DateTime(timezone=True))
        )
        batch_op.add_column(sa.Column("pre_delete_status", sa.String(length=16)))
        batch_op.add_column(
            sa.Column(
                "admin_deleted",
                sa.Boolean(),
                server_default=sa.false(),
                nullable=False,
            )
        )

    with op.batch_alter_table("community_comments") as batch_op:
        batch_op.add_column(
            sa.Column(
                "admin_deleted",
                sa.Boolean(),
                server_default=sa.false(),
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column("pre_delete_hidden_at", sa.DateTime(timezone=True))
        )

    op.create_table(
        "community_member_restrictions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("member_user_id", sa.Uuid(), nullable=False),
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_by_user_id", sa.Uuid()),
        sa.Column("revocation_reason", sa.Text()),
        sa.Column("revoked_request_id", sa.String(length=128)),
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
        sa.CheckConstraint("scope IN ('POSTS', 'COMMENTS')", name="scope_valid"),
        sa.CheckConstraint("expires_at > starts_at", name="time_range_valid"),
        sa.CheckConstraint("length(trim(reason)) > 0", name="reason_not_empty"),
        sa.ForeignKeyConstraint(
            ["member_user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["revoked_by_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_community_member_restrictions_member_scope",
        "community_member_restrictions",
        ["member_user_id", "scope"],
    )
    op.create_index(
        "ix_community_member_restrictions_expires",
        "community_member_restrictions",
        ["expires_at"],
    )

    with op.batch_alter_table("community_moderation_events") as batch_op:
        batch_op.drop_constraint(
            "ck_community_moderation_events_target_type_valid",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_community_moderation_events_action_valid",
            type_="check",
        )
        batch_op.create_check_constraint(
            "ck_community_moderation_events_target_type_valid",
            f"target_type IN ({_EVENT_TARGETS})",
        )
        batch_op.create_check_constraint(
            "ck_community_moderation_events_action_valid",
            f"action IN ({_EVENT_ACTIONS})",
        )


def downgrade() -> None:
    op.drop_index(
        "ix_community_member_restrictions_expires",
        table_name="community_member_restrictions",
    )
    op.drop_index(
        "ix_community_member_restrictions_member_scope",
        table_name="community_member_restrictions",
    )
    op.drop_table("community_member_restrictions")
    with op.batch_alter_table("community_comments") as batch_op:
        batch_op.drop_column("pre_delete_hidden_at")
        batch_op.drop_column("admin_deleted")
    with op.batch_alter_table("community_posts") as batch_op:
        batch_op.drop_column("admin_deleted")
        batch_op.drop_column("pre_delete_status")
        batch_op.drop_column("comments_locked_at")
        batch_op.drop_column("pinned_at")
    # Keep widened audit CHECK constraints: COM012 audit rows may exist after
    # downgrade, and narrowing would reject or force deletion of that history.
