"""Create membership event and registration tables.

Revision ID: 0130_community_events
Revises: 0129_membership_tiers_and_diamond_applications
"""

import sqlalchemy as sa

from alembic import op

revision = "0130_community_events"
down_revision = "0129_membership_tiers_and_diamond_applications"
branch_labels = None
depends_on = None


def _table_count(table_name: str) -> int:
    return int(
        op.get_bind()
        .execute(sa.text(f"SELECT COUNT(*) FROM {table_name}"))
        .scalar_one()
    )


def upgrade() -> None:
    op.create_table(
        "community_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("location", sa.String(300), nullable=False),
        sa.Column("required_tier", sa.String(16), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("confirmed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "ticket_price_minor", sa.BigInteger(), nullable=False, server_default="0"
        ),
        sa.Column("cancellation_cutoff_at", sa.DateTime(timezone=True)),
        sa.Column("included_entitlement", sa.String(16)),
        sa.Column("entitlement_quota", sa.Integer()),
        sa.Column(
            "requires_diamond_approval",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("status", sa.String(16), nullable=False, server_default="DRAFT"),
        sa.Column(
            "created_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
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
            "status IN ('DRAFT', 'PUBLISHED', 'CANCELLED')", name="valid_status"
        ),
        sa.CheckConstraint(
            "required_tier IN ('MEMBER', 'SILVER', 'COMPANION', 'PRESTIGE')",
            name="valid_required_tier",
        ),
        sa.CheckConstraint(
            "included_entitlement IS NULL OR included_entitlement IN "
            "('TALK', 'CONNECT', 'CIRCLE')",
            name="valid_included_entitlement",
        ),
        sa.CheckConstraint("capacity >= 1", name="positive_capacity"),
        sa.CheckConstraint(
            "confirmed_count >= 0 AND confirmed_count <= capacity",
            name="valid_confirmed_count",
        ),
        sa.CheckConstraint(
            "ticket_price_minor >= 0 AND ticket_price_minor <= 1000000000",
            name="valid_ticket_price",
        ),
        sa.CheckConstraint(
            "(included_entitlement IS NULL AND entitlement_quota IS NULL) "
            "OR (included_entitlement IS NOT NULL AND entitlement_quota >= 1)",
            name="valid_entitlement_quota",
        ),
        sa.CheckConstraint(
            "NOT requires_diamond_approval OR required_tier = 'PRESTIGE'",
            name="diamond_circle_tier",
        ),
        sa.CheckConstraint(
            "included_entitlement != 'CIRCLE' OR "
            "(required_tier = 'PRESTIGE' AND requires_diamond_approval)",
            name="circle_requires_diamond_approval",
        ),
        sa.CheckConstraint("ends_at > starts_at", name="valid_event_window"),
        sa.CheckConstraint(
            "cancellation_cutoff_at IS NULL OR cancellation_cutoff_at <= starts_at",
            name="valid_cancellation_cutoff",
        ),
    )
    op.create_index(
        "ix_community_events_status_starts",
        "community_events",
        ["status", "starts_at"],
    )

    op.create_table(
        "community_event_registrations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "event_id",
            sa.Uuid(),
            sa.ForeignKey("community_events.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column(
            "entitlement_units", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("entitlement_snapshot", sa.String(16)),
        sa.Column("entitlement_cycle_started_at", sa.DateTime(timezone=True)),
        sa.Column("membership_tier_snapshot", sa.String(16)),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "status IN ('CONFIRMED', 'WAITLISTED', 'CANCELLED', "
            "'CANCELLED_LATE', 'CANCELLED_BY_EVENT', 'INELIGIBLE', "
            "'PAYMENT_REQUIRED')",
            name="valid_status",
        ),
        sa.CheckConstraint(
            "(entitlement_units = 0 AND entitlement_snapshot IS NULL "
            "AND entitlement_cycle_started_at IS NULL "
            "AND membership_tier_snapshot IS NULL) "
            "OR (entitlement_units > 0 AND entitlement_snapshot IS NOT NULL "
            "AND entitlement_cycle_started_at IS NOT NULL "
            "AND membership_tier_snapshot IS NOT NULL)",
            name="valid_entitlement_snapshot",
        ),
    )
    op.create_index(
        "uq_community_event_registrations_active_user_event",
        "community_event_registrations",
        ["event_id", "user_id"],
        unique=True,
        sqlite_where=sa.text("status IN ('CONFIRMED', 'WAITLISTED')"),
        postgresql_where=sa.text("status IN ('CONFIRMED', 'WAITLISTED')"),
    )
    op.create_index(
        "ix_community_event_registrations_event_waitlist",
        "community_event_registrations",
        ["event_id", "status", "registered_at"],
    )
    op.create_index(
        "ix_community_event_registrations_user_registered",
        "community_event_registrations",
        ["user_id", "registered_at"],
    )

    op.create_table(
        "membership_event_entitlement_policies",
        sa.Column("tier", sa.String(16), primary_key=True),
        sa.Column("entitlement", sa.String(16), primary_key=True),
        sa.Column("quota_count", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "tier IN ('SILVER', 'COMPANION', 'PRESTIGE')", name="valid_tier"
        ),
        sa.CheckConstraint(
            "entitlement IN ('TALK', 'CONNECT', 'CIRCLE')",
            name="valid_entitlement",
        ),
        sa.CheckConstraint("quota_count >= 1", name="positive_quota"),
    )
    policy_table = sa.table(
        "membership_event_entitlement_policies",
        sa.column("tier", sa.String(16)),
        sa.column("entitlement", sa.String(16)),
        sa.column("quota_count", sa.Integer()),
    )
    op.bulk_insert(
        policy_table,
        [
            {"tier": "SILVER", "entitlement": "TALK", "quota_count": 4},
            {"tier": "COMPANION", "entitlement": "TALK", "quota_count": 4},
            {"tier": "COMPANION", "entitlement": "CONNECT", "quota_count": 6},
            {"tier": "PRESTIGE", "entitlement": "TALK", "quota_count": 4},
            {"tier": "PRESTIGE", "entitlement": "CONNECT", "quota_count": 6},
            {"tier": "PRESTIGE", "entitlement": "CIRCLE", "quota_count": 2},
        ],
    )
    op.create_table(
        "membership_event_entitlement_usage",
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("tier", sa.String(16), primary_key=True),
        sa.Column("entitlement", sa.String(16), primary_key=True),
        sa.Column("cycle_started_at", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("used_count", sa.Integer(), nullable=False, server_default="0"),
        sa.CheckConstraint(
            "tier IN ('SILVER', 'COMPANION', 'PRESTIGE')", name="valid_tier"
        ),
        sa.CheckConstraint(
            "entitlement IN ('TALK', 'CONNECT', 'CIRCLE')",
            name="valid_entitlement",
        ),
        sa.CheckConstraint("used_count >= 0", name="nonnegative_used_count"),
    )


def downgrade() -> None:
    if (
        _table_count("membership_event_entitlement_usage")
        or _table_count("community_event_registrations")
        or _table_count("community_events")
    ):
        raise RuntimeError("Archive community event data before downgrading events.")
    op.drop_table("membership_event_entitlement_usage")
    op.drop_table("membership_event_entitlement_policies")
    op.drop_index(
        "ix_community_event_registrations_user_registered",
        table_name="community_event_registrations",
    )
    op.drop_index(
        "ix_community_event_registrations_event_waitlist",
        table_name="community_event_registrations",
    )
    op.drop_index(
        "uq_community_event_registrations_active_user_event",
        table_name="community_event_registrations",
    )
    op.drop_table("community_event_registrations")
    op.drop_index("ix_community_events_status_starts", table_name="community_events")
    op.drop_table("community_events")
