"""Create CMS, audit, notifications and account intent schema.

Revision ID: 0013_operations
Revises: 0012_blockchain
Create Date: 2026-07-31
"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa

from alembic import op

revision: str = "0013_operations"
down_revision: str | None = "0012_blockchain"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ROLE_CODES = (
    "APPLICANT",
    "ORG_MANAGER",
    "REVIEWER",
    "COUNCIL_MEMBER",
    "COUNCIL_SECRETARY",
    "FINANCE_ADMIN",
    "CONTENT_ADMIN",
    "BLOCKCHAIN_ADMIN",
    "SUPER_ADMIN",
)


def _timestamps() -> tuple[sa.Column, sa.Column]:
    return (
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
    )


def upgrade() -> None:
    bind = op.get_bind()
    op.add_column(
        "users", sa.Column("account_type", sa.String(length=32), nullable=True)
    )
    if bind.dialect.name != "sqlite":
        op.create_check_constraint(
            "users_account_type_valid",
            "users",
            "account_type IS NULL OR account_type IN "
            "('INDIVIDUAL_APPLICANT', 'ORGANIZATION_APPLICANT')",
        )

    roles = sa.table(
        "roles", sa.column("id", sa.Uuid()), sa.column("code", sa.String())
    )
    existing = set(bind.execute(sa.select(roles.c.code)).scalars())
    bind.execute(
        roles.insert(),
        [{"id": uuid4(), "code": code} for code in ROLE_CODES if code not in existing],
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=128), nullable=False),
        sa.Column("before_json", sa.JSON(), nullable=True),
        sa.Column("after_json", sa.JSON(), nullable=True),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("ip_hash", sa.String(length=128), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_audit_logs"),
    )
    op.create_index(
        "ix_audit_logs_resource_created", "audit_logs", ["resource_type", "created_at"]
    )
    op.create_index(
        "ix_audit_logs_actor_created", "audit_logs", ["actor_user_id", "created_at"]
    )

    op.create_table(
        "cms_categories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_cms_categories"),
        sa.UniqueConstraint("slug", name="uq_cms_categories_slug"),
    )
    status_type = sa.Enum(
        "DRAFT",
        "PUBLISHED",
        "ARCHIVED",
        name="cms_content_status",
        native_enum=False,
        create_constraint=True,
    )
    for table_name, extra_columns in (
        ("cms_pages", [sa.Column("body_html", sa.Text(), nullable=False)]),
        (
            "cms_banners",
            [
                sa.Column("image_url", sa.String(length=1000), nullable=False),
                sa.Column("link_url", sa.String(length=1000), nullable=True),
            ],
        ),
    ):
        op.create_table(
            table_name,
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("slug", sa.String(length=180), nullable=False),
            *extra_columns,
            sa.Column("status", status_type, nullable=False, server_default="DRAFT"),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_by", sa.Uuid(), nullable=False),
            sa.Column("updated_by", sa.Uuid(), nullable=False),
            *_timestamps(),
            sa.ForeignKeyConstraint(
                ["created_by"],
                ["users.id"],
                name=f"fk_{table_name}_created_by_users",
                ondelete="RESTRICT",
            ),
            sa.ForeignKeyConstraint(
                ["updated_by"],
                ["users.id"],
                name=f"fk_{table_name}_updated_by_users",
                ondelete="RESTRICT",
            ),
            sa.PrimaryKeyConstraint("id", name=f"pk_{table_name}"),
            sa.UniqueConstraint("slug", name=f"uq_{table_name}_slug"),
        )
    op.create_table(
        "cms_posts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=180), nullable=False),
        sa.Column("excerpt", sa.String(length=500), nullable=True),
        sa.Column("body_html", sa.Text(), nullable=False),
        sa.Column("status", status_type, nullable=False, server_default="DRAFT"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["cms_categories.id"],
            name="fk_cms_posts_category_id_cms_categories",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_cms_posts_created_by_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["users.id"],
            name="fk_cms_posts_updated_by_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_cms_posts"),
        sa.UniqueConstraint("slug", name="uq_cms_posts_slug"),
    )
    op.create_index(
        "ix_cms_posts_status_published", "cms_posts", ["status", "published_at"]
    )
    op.create_table(
        "cms_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("resource_type", sa.String(length=32), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("snapshot_json", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_cms_versions_created_by_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_cms_versions"),
        sa.UniqueConstraint(
            "resource_type",
            "resource_id",
            "version_no",
            name="uq_cms_versions_resource_version",
        ),
    )
    op.create_index(
        "ix_cms_versions_resource", "cms_versions", ["resource_type", "resource_id"]
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("source_event_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("data_json", sa.JSON(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_notifications_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_notifications"),
        sa.UniqueConstraint(
            "user_id", "source_event_id", name="uq_notifications_user_source_event"
        ),
    )
    op.create_index(
        "ix_notifications_user_read_created",
        "notifications",
        ["user_id", "read_at", "created_at"],
    )
    op.create_table(
        "notification_deliveries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("notification_id", sa.Uuid(), nullable=False),
        sa.Column(
            "channel",
            sa.Enum(
                "IN_APP",
                "EMAIL",
                name="notification_channel",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("destination_masked", sa.String(length=320), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "RETRY_PENDING",
                "SENT",
                "FAILED",
                name="notification_delivery_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("template_version", sa.String(length=32), nullable=False),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("last_error_code", sa.String(length=64), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["notification_id"],
            ["notifications.id"],
            name="fk_notification_deliveries_notification_id_notifications",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_notification_deliveries"),
        sa.UniqueConstraint(
            "notification_id", "channel", name="uq_notification_deliveries_channel"
        ),
    )


def downgrade() -> None:
    bind = op.get_bind()
    op.drop_table("notification_deliveries")
    op.drop_index("ix_notifications_user_read_created", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("ix_cms_versions_resource", table_name="cms_versions")
    op.drop_table("cms_versions")
    op.drop_index("ix_cms_posts_status_published", table_name="cms_posts")
    op.drop_table("cms_posts")
    op.drop_table("cms_banners")
    op.drop_table("cms_pages")
    op.drop_table("cms_categories")
    op.drop_index("ix_audit_logs_actor_created", table_name="audit_logs")
    op.drop_index("ix_audit_logs_resource_created", table_name="audit_logs")
    op.drop_table("audit_logs")
    if bind.dialect.name != "sqlite":
        op.drop_constraint("users_account_type_valid", "users", type_="check")
    op.drop_column("users", "account_type")
