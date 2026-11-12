"""Add short referral codes, legacy aliases, and configurable level two."""

from __future__ import annotations

import secrets
from uuid import UUID

import sqlalchemy as sa

from alembic import op

revision = "0164_affiliate_short_codes_and_two_levels"
down_revision = "0163_test_account_isolation"
branch_labels = None
depends_on = None


def _short_code() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    token = "".join(secrets.choice(alphabet) for _ in range(7))
    return f"THV{token}"


def upgrade() -> None:
    op.add_column("affiliate_profiles", sa.Column("short_referral_code", sa.String(10)))

    op.create_table(
        "affiliate_referral_code_aliases",
        sa.Column("code", sa.String(32), primary_key=True),
        sa.Column(
            "affiliate_user_id",
            sa.Uuid(),
            sa.ForeignKey("affiliate_profiles.user_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_affiliate_referral_code_aliases_owner",
        "affiliate_referral_code_aliases",
        ["affiliate_user_id"],
    )

    bind = op.get_bind()
    profiles = sa.table(
        "affiliate_profiles",
        sa.column("user_id", sa.Uuid()),
        sa.column("referral_code", sa.String(32)),
        sa.column("short_referral_code", sa.String(10)),
    )
    aliases = sa.table(
        "affiliate_referral_code_aliases",
        sa.column("code", sa.String(32)),
        sa.column("affiliate_user_id", sa.Uuid()),
    )
    rows = list(
        bind.execute(
            sa.select(profiles.c.user_id, profiles.c.referral_code).order_by(
                profiles.c.user_id
            )
        )
    )
    reserved_codes = {str(row.referral_code).strip().upper() for row in rows}
    generated_codes: set[str] = set()
    for row in rows:
        user_id = UUID(str(row.user_id))
        for _ in range(1024):
            short_code = _short_code()
            if short_code not in reserved_codes and short_code not in generated_codes:
                break
        else:
            raise RuntimeError("Unable to generate unique short affiliate codes.")

        legacy_code = str(row.referral_code).strip().upper()
        if not legacy_code or legacy_code in generated_codes:
            raise RuntimeError("Existing affiliate referral codes are not unique.")
        generated_codes.add(short_code)
        bind.execute(
            profiles.update()
            .where(profiles.c.user_id == row.user_id)
            .values(short_referral_code=short_code)
        )
        bind.execute(
            aliases.insert().values(code=legacy_code, affiliate_user_id=user_id)
        )
        bind.execute(
            aliases.insert().values(code=short_code, affiliate_user_id=user_id)
        )

    with op.batch_alter_table("affiliate_profiles") as batch:
        batch.alter_column(
            "short_referral_code",
            existing_type=sa.String(10),
            nullable=False,
        )
        batch.create_unique_constraint(
            "uq_affiliate_profiles_short_referral_code", ["short_referral_code"]
        )
        batch.create_check_constraint(
            "ck_affiliate_profiles_short_referral_code_length",
            "length(short_referral_code) BETWEEN 8 AND 10",
        )

    with op.batch_alter_table("affiliate_commission_rule_sets") as batch:
        batch.drop_constraint(
            "ck_affiliate_rule_sets_level_two_disabled", type_="check"
        )
        batch.create_check_constraint(
            "ck_affiliate_rule_sets_valid_level_two_rate",
            "level2_rate_basis_points BETWEEN 0 AND 10000 AND "
            "((level2_enabled = true AND level2_rate_basis_points > 0) OR "
            "(level2_enabled = false AND level2_rate_basis_points = 0))",
        )

    with op.batch_alter_table("affiliate_commissions") as batch:
        batch.add_column(
            sa.Column(
                "commission_level",
                sa.Integer(),
                nullable=False,
                server_default="1",
            )
        )
        batch.create_check_constraint(
            "ck_affiliate_commissions_valid_commission_level",
            "commission_level IN (1, 2)",
        )


def downgrade() -> None:
    bind = op.get_bind()
    aliases = sa.table(
        "affiliate_referral_code_aliases",
        sa.column("code", sa.String(32)),
    )
    if bind.scalar(sa.select(sa.func.count()).select_from(aliases)):
        raise RuntimeError(
            "Cannot remove affiliate code aliases after referral links may be in use."
        )

    rule_sets = sa.table(
        "affiliate_commission_rule_sets",
        sa.column("level2_enabled", sa.Boolean()),
        sa.column("level2_rate_basis_points", sa.Integer()),
    )
    if bind.scalar(
        sa.select(sa.func.count())
        .select_from(rule_sets)
        .where(
            sa.or_(
                rule_sets.c.level2_enabled.is_(True),
                rule_sets.c.level2_rate_basis_points != 0,
            )
        )
    ):
        raise RuntimeError("Cannot remove configured second-level affiliate rules.")

    commissions = sa.table(
        "affiliate_commissions",
        sa.column("commission_level", sa.Integer()),
    )
    if bind.scalar(
        sa.select(sa.func.count())
        .select_from(commissions)
        .where(commissions.c.commission_level == 2)
    ):
        raise RuntimeError("Cannot remove issued second-level commissions.")

    with op.batch_alter_table("affiliate_commissions") as batch:
        batch.drop_constraint(
            "ck_affiliate_commissions_valid_commission_level", type_="check"
        )
        batch.drop_column("commission_level")

    with op.batch_alter_table("affiliate_commission_rule_sets") as batch:
        batch.drop_constraint(
            "ck_affiliate_rule_sets_valid_level_two_rate", type_="check"
        )
        batch.create_check_constraint(
            "ck_affiliate_rule_sets_level_two_disabled",
            "level2_enabled = false AND level2_rate_basis_points = 0",
        )

    op.drop_index(
        "ix_affiliate_referral_code_aliases_owner",
        table_name="affiliate_referral_code_aliases",
    )
    op.drop_table("affiliate_referral_code_aliases")
    with op.batch_alter_table("affiliate_profiles") as batch:
        batch.drop_constraint(
            "ck_affiliate_profiles_short_referral_code_length", type_="check"
        )
        batch.drop_constraint(
            "uq_affiliate_profiles_short_referral_code", type_="unique"
        )
        batch.drop_column("short_referral_code")
