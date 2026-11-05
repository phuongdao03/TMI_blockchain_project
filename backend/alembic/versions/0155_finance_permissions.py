"""Seed explicit finance and affiliate capability permissions."""

from uuid import NAMESPACE_URL, uuid5

import sqlalchemy as sa

from alembic import op

revision = "0155_finance_permissions"
down_revision = "0154_wallet_withdrawals"
branch_labels = None
depends_on = None

PERMISSIONS = (
    "finance.read",
    "finance.withdrawals.approve",
    "finance.settings.manage",
    "finance.identity.verify",
    "finance.banks.manage",
    "finance.payouts.execute",
    "affiliate.read",
    "affiliate.commissions.approve",
    "affiliate.rules.manage",
    "affiliate.profiles.manage",
)


def upgrade() -> None:
    table = sa.table(
        "permissions",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String(128)),
    )
    existing = set(
        op.get_bind().scalars(
            sa.select(table.c.code).where(table.c.code.in_(PERMISSIONS))
        )
    )
    new_permissions = [
        {
            "id": uuid5(NAMESPACE_URL, f"cns-permission:{code}"),
            "code": code,
        }
        for code in PERMISSIONS
        if code not in existing
    ]
    if new_permissions:
        op.bulk_insert(table, new_permissions)


def downgrade() -> None:
    bind = op.get_bind()
    permission_table = sa.table(
        "permissions",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String(128)),
    )
    for table_name in ("user_permissions", "role_permissions"):
        ref_table = sa.table(
            table_name,
            sa.column("permission_id", sa.Uuid()),
        )
        count = bind.scalar(
            sa.select(sa.func.count())
            .select_from(
                ref_table.join(
                    permission_table,
                    ref_table.c.permission_id == permission_table.c.id,
                )
            )
            .where(permission_table.c.code.in_(PERMISSIONS))
        )
        if count:
            raise RuntimeError(
                "Finance permissions are assigned; remove assignments and roll forward."
            )
    bind.execute(
        permission_table.delete().where(permission_table.c.code.in_(PERMISSIONS))
    )
