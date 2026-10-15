"""Create the community publishing and moderation foundation.

Revision ID: 0101_community_foundation
Revises: 0100_video_poster_cache
"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa

from alembic import op

revision: str = "0101_community_foundation"
down_revision: str | None = "0100_video_poster_cache"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CATEGORIES = (
    ("Thảo luận chung", "general", "Các chủ đề về Tinh Hoa Việt."),
    (
        "Di sản & Văn hóa",
        "heritage-culture",
        "Văn hóa, truyền thống và các giá trị di sản.",
    ),
    (
        "Sáng tạo Việt",
        "vietnamese-creativity",
        "Sáng kiến, sản phẩm và ý tưởng sáng tạo.",
    ),
    (
        "Con người & Cộng đồng",
        "people-community",
        "Nhân vật, tổ chức và câu chuyện tích cực.",
    ),
    (
        "Chia sẻ & Trải nghiệm",
        "sharing-experiences",
        "Câu chuyện, hình ảnh và trải nghiệm.",
    ),
    (
        "Góp ý & Đề xuất",
        "feedback-suggestions",
        "Ý kiến đóng góp cho chương trình và website.",
    ),
)


def upgrade() -> None:
    op.create_table(
        "community_categories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("icon", sa.String(length=64), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
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
        sa.CheckConstraint(
            "sort_order >= 0", name="ck_community_categories_sort_order_non_negative"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_community_categories"),
        sa.UniqueConstraint("slug", name="uq_community_categories_slug"),
    )
    op.create_index(
        "ix_community_categories_active_order",
        "community_categories",
        ["is_active", "sort_order"],
    )
    op.create_table(
        "community_posts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("author_user_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("slug", sa.String(length=220), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("excerpt", sa.String(length=320), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "DRAFT",
                "PENDING",
                "PUBLISHED",
                "REJECTED",
                "HIDDEN",
                "DELETED",
                name="community_post_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
            server_default="DRAFT",
        ),
        sa.Column("moderation_reason", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint(
            "length(trim(title)) > 0", name="ck_community_posts_title_not_empty"
        ),
        sa.CheckConstraint(
            "length(trim(content)) > 0", name="ck_community_posts_content_not_empty"
        ),
        sa.CheckConstraint(
            "length(trim(slug)) > 0", name="ck_community_posts_slug_not_empty"
        ),
        sa.ForeignKeyConstraint(
            ["author_user_id"],
            ["users.id"],
            name="fk_community_posts_author_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["community_categories.id"],
            name="fk_community_posts_category_id_community_categories",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_community_posts"),
        sa.UniqueConstraint("slug", name="uq_community_posts_slug"),
    )
    op.create_index(
        "ix_community_posts_status_published",
        "community_posts",
        ["status", "published_at", "id"],
    )
    op.create_index(
        "ix_community_posts_category_status_published",
        "community_posts",
        ["category_id", "status", "published_at"],
    )
    op.create_index(
        "ix_community_posts_author_updated",
        "community_posts",
        ["author_user_id", "updated_at"],
    )
    op.create_table(
        "community_moderation_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("post_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "action",
            sa.Enum(
                "SUBMITTED",
                "PUBLISHED",
                "REJECTED",
                "OWNER_DELETED",
                name="community_moderation_action",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "action IN ('SUBMITTED', 'PUBLISHED', 'REJECTED', 'OWNER_DELETED')",
            name="ck_community_moderation_logs_action_valid",
        ),
        sa.ForeignKeyConstraint(
            ["post_id"],
            ["community_posts.id"],
            name="fk_community_moderation_logs_post_id_community_posts",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name="fk_community_moderation_logs_actor_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_community_moderation_logs"),
    )
    op.create_index(
        "ix_community_moderation_logs_post_created",
        "community_moderation_logs",
        ["post_id", "created_at"],
    )

    categories = sa.table(
        "community_categories",
        sa.column("id", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("slug", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("sort_order", sa.Integer()),
    )
    op.bulk_insert(
        categories,
        [
            {
                "id": uuid4(),
                "name": name,
                "slug": slug,
                "description": description,
                "sort_order": sort_order,
            }
            for sort_order, (name, slug, description) in enumerate(CATEGORIES)
        ],
    )
    permissions = sa.table(
        "permissions",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
    )
    connection = op.get_bind()
    existing = connection.scalar(
        sa.select(permissions.c.id).where(permissions.c.code == "community.moderate")
    )
    if existing is None:
        connection.execute(
            permissions.insert().values(id=uuid4(), code="community.moderate")
        )


def downgrade() -> None:
    permissions = sa.table(
        "permissions",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
    )
    op.get_bind().execute(
        permissions.delete().where(permissions.c.code == "community.moderate")
    )
    op.drop_index(
        "ix_community_moderation_logs_post_created",
        table_name="community_moderation_logs",
    )
    op.drop_table("community_moderation_logs")
    op.drop_index("ix_community_posts_author_updated", table_name="community_posts")
    op.drop_index(
        "ix_community_posts_category_status_published", table_name="community_posts"
    )
    op.drop_index("ix_community_posts_status_published", table_name="community_posts")
    op.drop_table("community_posts")
    op.drop_index(
        "ix_community_categories_active_order", table_name="community_categories"
    )
    op.drop_table("community_categories")
