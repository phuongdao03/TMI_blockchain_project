"""Add role-gated affiliate profiles, attribution, and versioned rules."""

from datetime import UTC, datetime
from hashlib import sha256
from uuid import NAMESPACE_URL, uuid5

import sqlalchemy as sa

from alembic import op

revision = "0156_affiliate_foundation"
down_revision = "0155_finance_permissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "affiliate_profiles",
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("referral_code", sa.String(32), nullable=False, unique=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="ACTIVE"),
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
            "length(referral_code) BETWEEN 8 AND 32",
            name="ck_affiliate_profiles_referral_code_length",
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'SUSPENDED')",
            name="ck_affiliate_profiles_valid_status",
        ),
    )
    op.create_index(
        "ix_affiliate_profiles_status", "affiliate_profiles", ["status"]
    )
    op.create_table(
        "affiliate_referral_clicks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "affiliate_user_id",
            sa.Uuid(),
            sa.ForeignKey("affiliate_profiles.user_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("referral_code_snapshot", sa.String(32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_affiliate_referral_clicks_owner_created",
        "affiliate_referral_clicks",
        ["affiliate_user_id", "created_at"],
    )
    op.create_table(
        "affiliate_attributions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "affiliate_user_id",
            sa.Uuid(),
            sa.ForeignKey("affiliate_profiles.user_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "referred_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "referral_click_id",
            sa.Uuid(),
            sa.ForeignKey("affiliate_referral_clicks.id", ondelete="SET NULL"),
        ),
        sa.Column("referral_code_snapshot", sa.String(32), nullable=False),
        sa.Column("attributed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "referred_user_id", name="uq_affiliate_attributions_user"
        ),
        sa.CheckConstraint(
            "affiliate_user_id != referred_user_id",
            name="ck_affiliate_attributions_not_self_referred",
        ),
        sa.CheckConstraint(
            "expires_at > attributed_at",
            name="ck_affiliate_attributions_valid_window",
        ),
    )
    op.create_index(
        "ix_affiliate_attributions_owner_attributed",
        "affiliate_attributions",
        ["affiliate_user_id", "attributed_at"],
    )
    op.create_table(
        "affiliate_commission_rule_sets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("version_no", sa.Integer(), nullable=False, unique=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="DRAFT"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("attribution_window_days", sa.Integer(), nullable=False),
        sa.Column("hold_days", sa.Integer(), nullable=False),
        sa.Column(
            "level2_enabled", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "level2_rate_basis_points", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("effective_from", sa.DateTime(timezone=True)),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column(
            "published_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
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
            "version_no > 0",
            name="ck_affiliate_rule_sets_positive_version",
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'PUBLISHED')",
            name="ck_affiliate_rule_sets_valid_status",
        ),
        sa.CheckConstraint(
            "attribution_window_days BETWEEN 0 AND 3650",
            name="ck_affiliate_rule_sets_valid_attribution_window",
        ),
        sa.CheckConstraint(
            "hold_days BETWEEN 0 AND 3650",
            name="ck_affiliate_rule_sets_valid_hold_days",
        ),
        sa.CheckConstraint(
            "level2_enabled = false AND level2_rate_basis_points = 0",
            name="ck_affiliate_rule_sets_level_two_disabled",
        ),
        sa.CheckConstraint(
            "(status = 'PUBLISHED' AND effective_from IS NOT NULL "
            "AND published_at IS NOT NULL) OR status = 'DRAFT'",
            name="ck_affiliate_rule_sets_published_rule_has_timestamp",
        ),
    )
    op.create_index(
        "ix_affiliate_rule_sets_effective",
        "affiliate_commission_rule_sets",
        ["status", "effective_from", "version_no"],
    )
    op.create_table(
        "affiliate_commission_rates",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "rule_set_id",
            sa.Uuid(),
            sa.ForeignKey("affiliate_commission_rule_sets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("service_code", sa.String(64), nullable=False),
        sa.Column("direct_rate_basis_points", sa.Integer(), nullable=False),
        sa.UniqueConstraint(
            "rule_set_id",
            "service_code",
            name="uq_affiliate_commission_rate_service",
        ),
        sa.CheckConstraint(
            "length(service_code) BETWEEN 1 AND 64",
            name="ck_affiliate_commission_rates_service_code_length",
        ),
        sa.CheckConstraint(
            "direct_rate_basis_points BETWEEN 0 AND 10000",
            name="ck_affiliate_commission_rates_valid_direct_rate",
        ),
    )
    op.create_table(
        "affiliate_commissions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "affiliate_user_id",
            sa.Uuid(),
            sa.ForeignKey("affiliate_profiles.user_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "referred_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "rule_set_id",
            sa.Uuid(),
            sa.ForeignKey("affiliate_commission_rule_sets.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("rule_set_version", sa.Integer(), nullable=False),
        sa.Column("service_code", sa.String(64), nullable=False),
        sa.Column("source_reference", sa.String(160), nullable=False, unique=True),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("commission_amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("rate_basis_points", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="VND"),
        sa.Column("status", sa.String(16), nullable=False, server_default="PENDING"),
        sa.Column("earned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("hold_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column(
            "reviewed_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
        ),
        sa.Column("review_reason", sa.String(1000)),
        sa.Column(
            "finance_journal_id",
            sa.Uuid(),
            sa.ForeignKey("finance_journals.id", ondelete="RESTRICT"),
            unique=True,
        ),
        sa.Column(
            "reversal_journal_id",
            sa.Uuid(),
            sa.ForeignKey("finance_journals.id", ondelete="RESTRICT"),
            unique=True,
        ),
        sa.Column("reversed_at", sa.DateTime(timezone=True)),
        sa.Column(
            "reversed_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
        ),
        sa.Column("reversal_reason", sa.String(1000)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "amount_minor > 0",
            name="ck_affiliate_commissions_positive_source_amount",
        ),
        sa.CheckConstraint(
            "commission_amount_minor >= 0",
            name="ck_affiliate_commissions_nonnegative_commission",
        ),
        sa.CheckConstraint(
            "rate_basis_points BETWEEN 0 AND 10000",
            name="ck_affiliate_commissions_valid_rate",
        ),
        sa.CheckConstraint(
            "currency = 'VND'",
            name="ck_affiliate_commissions_vnd_only",
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'ON_HOLD', 'AVAILABLE', "
            "'REJECTED', 'REVERSED', 'SUPPRESSED')",
            name="ck_affiliate_commissions_valid_status",
        ),
        sa.CheckConstraint(
            "affiliate_user_id != referred_user_id",
            name="ck_affiliate_commissions_not_self_commission",
        ),
        sa.CheckConstraint(
            "status != 'AVAILABLE' OR finance_journal_id IS NOT NULL",
            name="ck_affiliate_commissions_available_has_journal",
        ),
        sa.CheckConstraint(
            "status != 'REVERSED' OR reversed_at IS NOT NULL",
            name="ck_affiliate_commissions_reversed_has_timestamp",
        ),
        sa.CheckConstraint(
            "status != 'SUPPRESSED' OR commission_amount_minor = 0",
            name="ck_affiliate_commissions_suppressed_has_zero_amount",
        ),
    )
    op.create_index(
        "ix_affiliate_commissions_owner_status_created",
        "affiliate_commissions",
        ["affiliate_user_id", "status", "created_at"],
    )
    op.create_index(
        "ix_affiliate_commissions_status_hold_until",
        "affiliate_commissions",
        ["status", "hold_until"],
    )

    bind = op.get_bind()
    users = sa.table(
        "users",
        sa.column("id", sa.Uuid()),
        sa.column("status", sa.String()),
        sa.column("disabled_at", sa.DateTime(timezone=True)),
        sa.column("deleted_at", sa.DateTime(timezone=True)),
    )
    roles = sa.table(
        "roles", sa.column("id", sa.Uuid()), sa.column("code", sa.String())
    )
    user_roles = sa.table(
        "user_roles",
        sa.column("user_id", sa.Uuid()),
        sa.column("role_id", sa.Uuid()),
    )
    employees = sa.table("employees", sa.column("user_id", sa.Uuid()))
    user_role_join = user_roles.join(roles, user_roles.c.role_id == roles.c.id)
    eligible_user_ids = bind.execute(
        sa.select(users.c.id).where(
            users.c.status == "ACTIVE",
            users.c.disabled_at.is_(None),
            users.c.deleted_at.is_(None),
            sa.exists(
                sa.select(1)
                .select_from(user_role_join)
                .where(
                    user_roles.c.user_id == users.c.id,
                    roles.c.code == "USER",
                )
            ),
            ~sa.exists(
                sa.select(1)
                .select_from(user_role_join)
                .where(
                    user_roles.c.user_id == users.c.id,
                    roles.c.code != "USER",
                )
            ),
            ~sa.exists(
                sa.select(1)
                .select_from(employees)
                .where(employees.c.user_id == users.c.id)
            ),
        )
    ).scalars()
    profiles = sa.table(
        "affiliate_profiles",
        sa.column("user_id", sa.Uuid()),
        sa.column("referral_code", sa.String(32)),
        sa.column("status", sa.String(16)),
    )
    for user_id in eligible_user_ids:
        referral_suffix = sha256(str(user_id).encode("ascii")).hexdigest()[:29].upper()
        bind.execute(
            profiles.insert().values(
                user_id=user_id,
                referral_code=f"THV{referral_suffix}",
                status="ACTIVE",
            )
        )

    now = datetime.now(UTC)
    rule_set_id = uuid5(NAMESPACE_URL, "affiliate-commission-rules-v1")
    rule_sets = sa.table(
        "affiliate_commission_rule_sets",
        sa.column("id", sa.Uuid()),
        sa.column("version_no", sa.Integer()),
        sa.column("status", sa.String(16)),
        sa.column("enabled", sa.Boolean()),
        sa.column("attribution_window_days", sa.Integer()),
        sa.column("hold_days", sa.Integer()),
        sa.column("level2_enabled", sa.Boolean()),
        sa.column("level2_rate_basis_points", sa.Integer()),
        sa.column("effective_from", sa.DateTime(timezone=True)),
        sa.column("published_at", sa.DateTime(timezone=True)),
    )
    bind.execute(
        rule_sets.insert().values(
            id=rule_set_id,
            version_no=1,
            status="PUBLISHED",
            enabled=False,
            attribution_window_days=30,
            hold_days=30,
            level2_enabled=False,
            level2_rate_basis_points=0,
            effective_from=now,
            published_at=now,
        )
    )
    rate_rows = sa.table(
        "affiliate_commission_rates",
        sa.column("id", sa.Uuid()),
        sa.column("rule_set_id", sa.Uuid()),
        sa.column("service_code", sa.String(64)),
        sa.column("direct_rate_basis_points", sa.Integer()),
    )
    bind.execute(
        rate_rows.insert(),
        [
            {
                "id": uuid5(NAMESPACE_URL, f"affiliate-commission-v1:{service}"),
                "rule_set_id": rule_set_id,
                "service_code": service,
                "direct_rate_basis_points": 0,
            }
            for service in ("DOSSIER_SUBMISSION", "MEMBERSHIP", "ADVERTISING")
        ],
    )


def downgrade() -> None:
    bind = op.get_bind()
    for table_name in (
        "affiliate_commissions",
        "affiliate_attributions",
        "affiliate_referral_clicks",
        "affiliate_profiles",
    ):
        pk_name = "user_id" if table_name == "affiliate_profiles" else "id"
        table = sa.table(table_name, sa.column(pk_name, sa.Uuid()))
        if table_name == "affiliate_profiles":
            count = bind.scalar(sa.select(sa.func.count()).select_from(table))
        else:
            count = bind.scalar(sa.select(sa.func.count()).select_from(table))
        if count:
            raise RuntimeError(
                "Affiliate referral history exists; preserve it and roll forward."
            )
    rule_sets = sa.table(
        "affiliate_commission_rule_sets",
        sa.column("id", sa.Uuid()),
    )
    # Only the safe, disabled seed is disposable; admin-authored versions are not.
    non_seed_count = bind.scalar(
        sa.select(sa.func.count()).select_from(rule_sets).where(
            rule_sets.c.id != uuid5(NAMESPACE_URL, "affiliate-commission-rules-v1")
        )
    )
    if non_seed_count:
        raise RuntimeError(
            "Affiliate policy history exists; preserve it and roll forward."
        )
    op.drop_index(
        "ix_affiliate_commissions_status_hold_until",
        table_name="affiliate_commissions",
    )
    op.drop_index(
        "ix_affiliate_commissions_owner_status_created",
        table_name="affiliate_commissions",
    )
    op.drop_table("affiliate_commissions")
    op.drop_table("affiliate_commission_rates")
    op.drop_index(
        "ix_affiliate_rule_sets_effective",
        table_name="affiliate_commission_rule_sets",
    )
    op.drop_table("affiliate_commission_rule_sets")
    op.drop_index(
        "ix_affiliate_attributions_owner_attributed",
        table_name="affiliate_attributions",
    )
    op.drop_table("affiliate_attributions")
    op.drop_index(
        "ix_affiliate_referral_clicks_owner_created",
        table_name="affiliate_referral_clicks",
    )
    op.drop_table("affiliate_referral_clicks")
    op.drop_index("ix_affiliate_profiles_status", table_name="affiliate_profiles")
    op.drop_table("affiliate_profiles")
