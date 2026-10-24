"""Add shared ad delivery stats and campaign lifecycle data.

Revision ID: 0138_advertising_delivery
Revises: 0137_advertising_checkout
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0138_advertising_delivery"
down_revision: str | None = "0137_advertising_checkout"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "advertising_placements", sa.Column("rotation_pool_key", sa.String(length=64))
    )
    with op.batch_alter_table("advertising_packages") as batch_op:
        batch_op.add_column(
            sa.Column(
                "rotation_weight", sa.Integer(), server_default="1", nullable=False
            )
        )
        batch_op.create_check_constraint(
            "ck_advertising_packages_valid_rotation_weight",
            "rotation_weight BETWEEN 1 AND 100",
        )
    with op.batch_alter_table("advertising_campaigns") as batch_op:
        batch_op.drop_constraint("ck_advertising_campaigns_valid_status", type_="check")
        batch_op.create_check_constraint(
            "ck_advertising_campaigns_valid_status",
            "status IN ('DRAFT', 'PENDING_REVIEW', 'APPROVED', 'PENDING_PAYMENT', "
            "'SCHEDULED', 'NEEDS_RESCHEDULE', 'ACTIVE', 'PAUSED', 'COMPLETED', "
            "'CANCELLED', 'REJECTED')",
        )
        batch_op.add_column(
            sa.Column("actual_start_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column("actual_end_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "rotation_weight", sa.Integer(), server_default="1", nullable=False
            )
        )
        batch_op.add_column(
            sa.Column(
                "delivery_count", sa.BigInteger(), server_default="0", nullable=False
            )
        )
        batch_op.add_column(
            sa.Column(
                "rotation_count", sa.BigInteger(), server_default="0", nullable=False
            )
        )
        batch_op.create_check_constraint(
            "ck_advertising_campaigns_valid_rotation_weight",
            "rotation_weight BETWEEN 1 AND 100",
        )
        batch_op.create_check_constraint(
            "ck_advertising_campaigns_delivery_count_nonnegative",
            "delivery_count >= 0",
        )
        batch_op.create_check_constraint(
            "ck_advertising_campaigns_rotation_count_nonnegative",
            "rotation_count >= 0",
        )
    op.add_column(
        "advertising_creatives", sa.Column("review_note", sa.String(length=1000))
    )

    op.create_table(
        "advertising_delivery_stats",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("placement_id", sa.Uuid(), nullable=False),
        sa.Column("stat_date", sa.Date(), nullable=False),
        sa.Column(
            "delivery_count", sa.BigInteger(), server_default="0", nullable=False
        ),
        sa.Column(
            "valid_impressions", sa.BigInteger(), server_default="0", nullable=False
        ),
        sa.Column("valid_clicks", sa.BigInteger(), server_default="0", nullable=False),
        sa.CheckConstraint(
            "delivery_count >= 0",
            name="ck_ad_delivery_stats_delivery_count_nonnegative",
        ),
        sa.CheckConstraint(
            "valid_impressions >= 0",
            name="ck_ad_delivery_stats_impressions_nonnegative",
        ),
        sa.CheckConstraint(
            "valid_clicks >= 0", name="ck_ad_delivery_stats_clicks_nonnegative"
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["advertising_campaigns.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["placement_id"], ["advertising_placements.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "campaign_id", "stat_date", name="uq_ad_delivery_stats_campaign_date"
        ),
    )
    op.create_index(
        "ix_ad_delivery_stats_placement_date",
        "advertising_delivery_stats",
        ["placement_id", "stat_date"],
    )
    op.create_table(
        "advertising_delivery_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("placement_id", sa.Uuid(), nullable=False),
        sa.Column("destination_url", sa.String(length=2048), nullable=False),
        sa.Column("selected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("impression_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("clicked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "valid_traffic", sa.Boolean(), server_default=sa.true(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["advertising_campaigns.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["placement_id"], ["advertising_placements.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ad_delivery_events_campaign_selected",
        "advertising_delivery_events",
        ["campaign_id", "selected_at"],
    )
    op.create_index(
        "ix_ad_delivery_events_selected",
        "advertising_delivery_events",
        ["selected_at"],
    )
    op.create_table(
        "advertising_waitlist_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("placement_id", sa.Uuid(), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status", sa.String(length=16), server_default="WAITING", nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("start_at < end_at", name="ck_ad_waitlist_valid_interval"),
        sa.CheckConstraint(
            "status IN ('WAITING', 'NOTIFIED', 'CANCELLED', 'FULFILLED')",
            name="ck_ad_waitlist_valid_status",
        ),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["advertising_campaigns.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["placement_id"], ["advertising_placements.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "owner_user_id",
            "campaign_id",
            "start_at",
            name="uq_ad_waitlist_user_campaign_start",
        ),
    )
    op.create_index(
        "ix_ad_waitlist_placement_status_start",
        "advertising_waitlist_entries",
        ["placement_id", "status", "start_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ad_waitlist_placement_status_start",
        table_name="advertising_waitlist_entries",
    )
    op.drop_table("advertising_waitlist_entries")
    op.drop_index(
        "ix_ad_delivery_events_selected", table_name="advertising_delivery_events"
    )
    op.drop_index(
        "ix_ad_delivery_events_campaign_selected",
        table_name="advertising_delivery_events",
    )
    op.drop_table("advertising_delivery_events")
    op.drop_index(
        "ix_ad_delivery_stats_placement_date", table_name="advertising_delivery_stats"
    )
    op.drop_table("advertising_delivery_stats")
    op.drop_column("advertising_creatives", "review_note")
    with op.batch_alter_table("advertising_campaigns") as batch_op:
        batch_op.drop_constraint(
            "ck_advertising_campaigns_rotation_count_nonnegative", type_="check"
        )
        batch_op.drop_constraint(
            "ck_advertising_campaigns_delivery_count_nonnegative", type_="check"
        )
        batch_op.drop_constraint(
            "ck_advertising_campaigns_valid_rotation_weight", type_="check"
        )
        batch_op.drop_column("delivery_count")
        batch_op.drop_column("rotation_count")
        batch_op.drop_column("rotation_weight")
        batch_op.drop_column("actual_end_at")
        batch_op.drop_column("actual_start_at")
        batch_op.drop_constraint("ck_advertising_campaigns_valid_status", type_="check")
        batch_op.create_check_constraint(
            "ck_advertising_campaigns_valid_status",
            "status IN ('DRAFT', 'PENDING_REVIEW', 'APPROVED', 'PENDING_PAYMENT', "
            "'SCHEDULED', 'ACTIVE', 'PAUSED', 'COMPLETED', 'CANCELLED', 'REJECTED')",
        )
    with op.batch_alter_table("advertising_packages") as batch_op:
        batch_op.drop_constraint(
            "ck_advertising_packages_valid_rotation_weight", type_="check"
        )
        batch_op.drop_column("rotation_weight")
    op.drop_column("advertising_placements", "rotation_pool_key")
