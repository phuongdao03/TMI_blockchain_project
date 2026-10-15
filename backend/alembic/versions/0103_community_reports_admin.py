"""Add community reporting, admin settings, and moderation event history.

Revision ID: 0103_community_reports_admin
Revises: 0102_community_engagement
"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa

from alembic import op

revision: str = "0103_community_reports_admin"
down_revision: str | None = "0102_community_engagement"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REPORT_REASONS = (
    "'SPAM', 'HARASSMENT', 'HATE_SPEECH', 'MISINFORMATION', "
    "'COPYRIGHT', 'OTHER'"
)
EVENT_ACTIONS = (
    "'SUBMITTED', 'PUBLISHED', 'REJECTED', 'OWNER_DELETED', 'POST_HIDDEN', "
    "'POST_RESTORED', 'COMMENT_HIDDEN', 'COMMENT_RESTORED', "
    "'REPORT_DISMISSED', 'CATEGORY_CREATED', 'CATEGORY_UPDATED', 'SETTINGS_UPDATED'"
)


def upgrade() -> None:
    op.add_column(
        "community_comments",
        sa.Column("moderation_hidden_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "community_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reporter_user_id", sa.Uuid(), nullable=False),
        sa.Column("post_id", sa.Uuid(), nullable=True),
        sa.Column("comment_id", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.String(length=32), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column(
            "status", sa.String(length=16), nullable=False, server_default="OPEN"
        ),
        sa.Column("resolution_action", sa.String(length=16), nullable=True),
        sa.Column("resolution_reason", sa.Text(), nullable=True),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("resolved_request_id", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by_user_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            "(post_id IS NOT NULL AND comment_id IS NULL) OR "
            "(post_id IS NULL AND comment_id IS NOT NULL)",
            name="ck_community_reports_one_target",
        ),
        sa.CheckConstraint(
            f"reason IN ({REPORT_REASONS})",
            name="ck_community_reports_reason_valid",
        ),
        sa.CheckConstraint(
            "status IN ('OPEN', 'RESOLVED', 'DISMISSED')",
            name="ck_community_reports_status_valid",
        ),
        sa.CheckConstraint(
            "resolution_action IS NULL OR resolution_action IN ('HIDE', 'DISMISS')",
            name="ck_community_reports_resolution_valid",
        ),
        sa.CheckConstraint(
            "length(details) <= 2000 OR details IS NULL",
            name="ck_community_reports_details_length",
        ),
        sa.CheckConstraint(
            "(status = 'OPEN' AND resolved_at IS NULL AND "
            "resolved_by_user_id IS NULL AND resolution_action IS NULL AND "
            "resolution_reason IS NULL) OR "
            "(status IN ('RESOLVED', 'DISMISSED') AND resolved_at IS NOT NULL AND "
            "resolved_by_user_id IS NOT NULL AND resolution_action IS NOT NULL AND "
            "resolution_reason IS NOT NULL)",
            name="ck_community_reports_resolution_state_consistent",
        ),
        sa.ForeignKeyConstraint(
            ["reporter_user_id"], ["users.id"],
            name="fk_community_reports_reporter_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["post_id"], ["community_posts.id"],
            name="fk_community_reports_post_id_community_posts",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["comment_id"], ["community_comments.id"],
            name="fk_community_reports_comment_id_community_comments",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by_user_id"], ["users.id"],
            name="fk_community_reports_resolved_by_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_community_reports"),
    )
    op.create_index(
        "ix_community_reports_status_created",
        "community_reports",
        ["status", "created_at"],
    )
    op.create_index(
        "uq_community_reports_open_reporter_post",
        "community_reports",
        ["reporter_user_id", "post_id"],
        unique=True,
        postgresql_where=sa.text("status = 'OPEN' AND post_id IS NOT NULL"),
        sqlite_where=sa.text("status = 'OPEN' AND post_id IS NOT NULL"),
    )
    op.create_index(
        "uq_community_reports_open_reporter_comment",
        "community_reports",
        ["reporter_user_id", "comment_id"],
        unique=True,
        postgresql_where=sa.text("status = 'OPEN' AND comment_id IS NOT NULL"),
        sqlite_where=sa.text("status = 'OPEN' AND comment_id IS NOT NULL"),
    )
    op.create_table(
        "community_settings",
        sa.Column("singleton_id", sa.Integer(), nullable=False),
        sa.Column(
            "pre_moderation_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "singleton_id = 1",
            name="ck_community_settings_singleton_id_valid",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"], ["users.id"],
            name="fk_community_settings_updated_by_user_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("singleton_id", name="pk_community_settings"),
    )
    op.execute(
        sa.text(
            "INSERT INTO community_settings (singleton_id, pre_moderation_enabled) "
            "VALUES (1, TRUE)"
        )
    )
    op.create_table(
        "community_moderation_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=False),
        sa.Column("target_id", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("report_id", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("event_data", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "target_type IN ('POST', 'COMMENT', 'CATEGORY', 'SETTINGS')",
            name="ck_community_moderation_events_target_type_valid",
        ),
        sa.CheckConstraint(
            "length(trim(target_id)) > 0",
            name="ck_community_moderation_events_target_id_not_empty",
        ),
        sa.CheckConstraint(
            f"action IN ({EVENT_ACTIONS})",
            name="ck_community_moderation_events_action_valid",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["users.id"],
            name="fk_community_moderation_events_actor_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["report_id"], ["community_reports.id"],
            name="fk_community_moderation_events_report_id_community_reports",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_community_moderation_events"),
    )
    op.create_index(
        "ix_community_moderation_events_target_created",
        "community_moderation_events",
        ["target_type", "target_id", "created_at"],
    )
    op.create_index(
        "ix_community_moderation_events_created",
        "community_moderation_events",
        ["created_at"],
    )

    connection = op.get_bind()
    connection.execute(
        sa.text(
            "INSERT INTO community_moderation_events "
            "(id, target_type, target_id, action, actor_user_id, reason, "
            "request_id, created_at) "
            "SELECT id, 'POST', CAST(post_id AS VARCHAR), action, actor_user_id, "
            "reason, request_id, created_at FROM community_moderation_logs"
        )
    )

    permissions = sa.table(
        "permissions",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
    )
    existing = connection.scalar(
        sa.select(permissions.c.id).where(
            permissions.c.code == "community.manage"
        )
    )
    if existing is None:
        connection.execute(
            permissions.insert().values(id=uuid4(), code="community.manage")
        )


def downgrade() -> None:
    permissions = sa.table(
        "permissions",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
    )
    role_permissions = sa.table(
        "role_permissions",
        sa.column("permission_id", sa.Uuid()),
    )
    manage_ids = sa.select(permissions.c.id).where(
        permissions.c.code == "community.manage"
    )
    op.get_bind().execute(
        role_permissions.delete().where(role_permissions.c.permission_id.in_(manage_ids))
    )
    op.get_bind().execute(
        permissions.delete().where(permissions.c.code == "community.manage")
    )
    op.drop_index(
        "ix_community_moderation_events_created",
        table_name="community_moderation_events",
    )
    op.drop_index(
        "ix_community_moderation_events_target_created",
        table_name="community_moderation_events",
    )
    op.drop_table("community_moderation_events")
    op.drop_table("community_settings")
    op.drop_index(
        "uq_community_reports_open_reporter_comment",
        table_name="community_reports",
    )
    op.drop_index(
        "uq_community_reports_open_reporter_post",
        table_name="community_reports",
    )
    op.drop_index(
        "ix_community_reports_status_created",
        table_name="community_reports",
    )
    op.drop_table("community_reports")
    op.drop_column("community_comments", "moderation_hidden_at")
