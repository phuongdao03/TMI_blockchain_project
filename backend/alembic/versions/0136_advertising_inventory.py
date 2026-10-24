"""Add advertising placements, campaigns, and reservations.

Revision ID: 0136_advertising_inventory
Revises: 0135_membership_event_priority_windows
"""

from datetime import UTC, datetime
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0136_advertising_inventory"
down_revision = "0135_membership_event_priority_windows"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "advertising_placements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("page_location", sa.String(length=160), nullable=False),
        sa.Column("delivery_mode", sa.String(length=24), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "timezone",
            sa.String(length=64),
            server_default="Asia/Bangkok",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "capacity > 0", name="ck_advertising_placements_capacity_positive"
        ),
        sa.CheckConstraint(
            "delivery_mode IN ('EQUAL_ROTATION', 'WEIGHTED_ROTATION', 'EXCLUSIVE')",
            name="ck_advertising_placements_valid_delivery_mode",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_advertising_placements_code"),
    )
    op.create_table(
        "advertising_packages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("placement_id", sa.Uuid(), nullable=False),
        sa.Column("duration_hours", sa.Integer(), nullable=False),
        sa.Column("base_price_vnd", sa.BigInteger(), nullable=False),
        sa.Column("price_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("terms", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "duration_hours > 0", name="ck_advertising_packages_duration_positive"
        ),
        sa.CheckConstraint(
            "base_price_vnd >= 0", name="ck_advertising_packages_price_nonnegative"
        ),
        sa.CheckConstraint(
            "price_version > 0",
            name="ck_advertising_packages_price_version_positive",
        ),
        sa.ForeignKeyConstraint(
            ["placement_id"], ["advertising_placements.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_advertising_packages_code"),
    )
    op.create_index(
        "ix_advertising_packages_placement_id",
        "advertising_packages",
        ["placement_id"],
    )
    op.create_table(
        "advertising_campaigns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("dossier_id", sa.Uuid(), nullable=False),
        sa.Column("package_id", sa.Uuid(), nullable=False),
        sa.Column("placement_id", sa.Uuid(), nullable=False),
        sa.Column("purchase_context", sa.String(length=24), nullable=False),
        sa.Column(
            "status", sa.String(length=24), server_default="DRAFT", nullable=False
        ),
        sa.Column("desired_start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "purchase_context IN ('BEFORE_PUBLICATION', 'AFTER_PUBLICATION')",
            name="ck_advertising_campaigns_valid_purchase_context",
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'PENDING_REVIEW', 'APPROVED', 'PENDING_PAYMENT', "
            "'SCHEDULED', 'ACTIVE', 'PAUSED', 'COMPLETED', 'CANCELLED', 'REJECTED')",
            name="ck_advertising_campaigns_valid_status",
        ),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["dossier_id"], ["dossiers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["package_id"], ["advertising_packages.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["placement_id"], ["advertising_placements.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_advertising_campaigns_owner_created",
        "advertising_campaigns",
        ["owner_user_id", "created_at"],
    )
    op.create_table(
        "advertising_creatives",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("image_url", sa.String(length=2048), nullable=True),
        sa.Column("destination_url", sa.String(length=2048), nullable=False),
        sa.Column(
            "review_status",
            sa.String(length=24),
            server_default="PENDING",
            nullable=False,
        ),
        sa.Column("reviewed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "version > 0", name="ck_advertising_creatives_version_positive"
        ),
        sa.CheckConstraint(
            "review_status IN ('PENDING', 'APPROVED', 'REJECTED', 'CHANGES_REQUESTED')",
            name="ck_advertising_creatives_valid_review_status",
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["advertising_campaigns.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "campaign_id", "version", name="uq_advertising_creatives_campaign_version"
        ),
    )
    op.create_index(
        "ix_advertising_creatives_campaign_id", "advertising_creatives", ["campaign_id"]
    )
    op.create_table(
        "advertising_reservations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("placement_id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status", sa.String(length=24), server_default="HELD", nullable=False
        ),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "start_at < end_at", name="ck_advertising_reservations_valid_interval"
        ),
        sa.CheckConstraint(
            "status IN ('HELD', 'PAYMENT_PROCESSING', 'CONFIRMED', "
            "'EXPIRED', 'CANCELLED')",
            name="ck_advertising_reservations_valid_status",
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["advertising_campaigns.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["placement_id"], ["advertising_placements.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "owner_user_id", "idempotency_key", name="uq_ad_reservations_owner_key"
        ),
    )
    op.create_index(
        "ix_ad_reservations_inventory_interval",
        "advertising_reservations",
        ["placement_id", "status", "start_at", "end_at"],
    )
    op.create_table(
        "advertising_bookings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("placement_id", sa.Uuid(), nullable=False),
        sa.Column("reservation_id", sa.Uuid(), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status", sa.String(length=16), server_default="CONFIRMED", nullable=False
        ),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "start_at < end_at", name="ck_advertising_bookings_valid_interval"
        ),
        sa.CheckConstraint(
            "status IN ('CONFIRMED', 'CANCELLED', 'COMPLETED')",
            name="ck_advertising_bookings_valid_status",
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["advertising_campaigns.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["placement_id"], ["advertising_placements.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["reservation_id"], ["advertising_reservations.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reservation_id", name="uq_ad_bookings_reservation"),
    )
    op.create_index(
        "ix_ad_bookings_inventory_interval",
        "advertising_bookings",
        ["placement_id", "status", "start_at", "end_at"],
    )
    op.create_table(
        "advertising_audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("entity_type", sa.String(length=40), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column(
            "before_json",
            postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
            nullable=True,
        ),
        sa.Column(
            "after_json",
            postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ad_audit_entity_created",
        "advertising_audit_logs",
        ["entity_type", "entity_id", "created_at"],
    )

    placement_table = sa.table(
        "advertising_placements",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("page_location", sa.String()),
        sa.column("delivery_mode", sa.String()),
        sa.column("capacity", sa.Integer()),
        sa.column("enabled", sa.Boolean()),
        sa.column("timezone", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    placement_ids = {
        "FEATURED_DOSSIER": UUID("a1360000-0000-4000-8000-000000000001"),
        "HOMEPAGE_SPOTLIGHT": UUID("a1360000-0000-4000-8000-000000000002"),
        "COMMUNITY_BANNER": UUID("a1360000-0000-4000-8000-000000000003"),
        "HOMEPAGE_HERO": UUID("a1360000-0000-4000-8000-000000000004"),
    }
    now = datetime.now(UTC)
    op.bulk_insert(
        placement_table,
        [
            {
                "id": identifier,
                "code": code,
                "name": name,
                "page_location": page,
                "delivery_mode": mode,
                "capacity": capacity,
                "enabled": True,
                "timezone": "Asia/Bangkok",
                "created_at": now,
                "updated_at": now,
            }
            for code, identifier, name, page, mode, capacity in [
                (
                    "FEATURED_DOSSIER",
                    placement_ids["FEATURED_DOSSIER"],
                    "Nổi bật đề cử",
                    "Trang hồ sơ đề cử",
                    "EQUAL_ROTATION",
                    4,
                ),
                (
                    "HOMEPAGE_SPOTLIGHT",
                    placement_ids["HOMEPAGE_SPOTLIGHT"],
                    "Spotlight trang chủ",
                    "Trang chủ",
                    "EQUAL_ROTATION",
                    3,
                ),
                (
                    "COMMUNITY_BANNER",
                    placement_ids["COMMUNITY_BANNER"],
                    "Banner cộng đồng",
                    "Cộng đồng",
                    "EQUAL_ROTATION",
                    5,
                ),
                (
                    "HOMEPAGE_HERO",
                    placement_ids["HOMEPAGE_HERO"],
                    "Hero trang chủ",
                    "Trang chủ",
                    "EXCLUSIVE",
                    1,
                ),
            ]
        ],
    )
    package_table = sa.table(
        "advertising_packages",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("placement_id", sa.Uuid()),
        sa.column("duration_hours", sa.Integer()),
        sa.column("base_price_vnd", sa.BigInteger()),
        sa.column("price_version", sa.Integer()),
        sa.column("active", sa.Boolean()),
        sa.column("terms", sa.Text()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(
        package_table,
        [
            {
                "id": UUID("a1360000-0000-4000-8000-000000000005"),
                "code": "FEATURED_DOSSIER_30D",
                "name": "Nổi bật đề cử — 30 ngày",
                "placement_id": placement_ids["FEATURED_DOSSIER"],
                "duration_hours": 720,
                "base_price_vnd": 1_390_000,
                "price_version": 1,
                "active": True,
                "terms": (
                    "Phân phối luân phiên theo thời gian; "
                    "không cam kết số lượt hiển thị."
                ),
                "created_at": now,
                "updated_at": now,
            }
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_ad_audit_entity_created", table_name="advertising_audit_logs")
    op.drop_table("advertising_audit_logs")
    op.drop_index(
        "ix_ad_bookings_inventory_interval", table_name="advertising_bookings"
    )
    op.drop_table("advertising_bookings")
    op.drop_index(
        "ix_ad_reservations_inventory_interval", table_name="advertising_reservations"
    )
    op.drop_table("advertising_reservations")
    op.drop_index(
        "ix_advertising_creatives_campaign_id", table_name="advertising_creatives"
    )
    op.drop_table("advertising_creatives")
    op.drop_index(
        "ix_advertising_campaigns_owner_created", table_name="advertising_campaigns"
    )
    op.drop_table("advertising_campaigns")
    op.drop_index(
        "ix_advertising_packages_placement_id", table_name="advertising_packages"
    )
    op.drop_table("advertising_packages")
    op.drop_table("advertising_placements")
