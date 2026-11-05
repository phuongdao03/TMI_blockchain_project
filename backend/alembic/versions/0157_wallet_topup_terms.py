"""Shorten pending wallet top-ups and remove the old amount ceiling."""

from datetime import UTC, timedelta

import sqlalchemy as sa

from alembic import op

revision = "0157_wallet_topup_terms"
down_revision = "0156_affiliate_foundation"
branch_labels = None
depends_on = None

_TOPUP_TTL = timedelta(minutes=10)
_OLD_AMOUNT_CEILING = 1_000_000_000


def _wallet_topups() -> sa.TableClause:
    return sa.table(
        "wallet_topups",
        sa.column("id", sa.Uuid()),
        sa.column("amount_minor", sa.BigInteger()),
        sa.column("status", sa.String(16)),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("expires_at", sa.DateTime(timezone=True)),
    )


def upgrade() -> None:
    connection = op.get_bind()
    topups = _wallet_topups()
    pending = connection.execute(
        sa.select(
            topups.c.id,
            topups.c.created_at,
            topups.c.expires_at,
        ).where(
            topups.c.status.in_(("PENDING", "PROCESSING")),
        )
    ).all()
    for row in pending:
        created_at = row.created_at
        expires_at = row.expires_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        new_expiry = created_at + _TOPUP_TTL
        if expires_at > new_expiry:
            connection.execute(
                sa.update(topups)
                .where(topups.c.id == row.id)
                .values(expires_at=new_expiry)
            )

    with op.batch_alter_table("wallet_topups") as batch_op:
        batch_op.drop_constraint("amount_range", type_="check")
        # Keep the historical floor so already-created 1,000 VND top-ups remain
        # valid while the API and service enforce 5,000 VND for new orders.
        batch_op.create_check_constraint("amount_range", "amount_minor >= 1000")


def downgrade() -> None:
    connection = op.get_bind()
    topups = _wallet_topups()
    has_new_large_amount = connection.execute(
        sa.select(topups.c.id)
        .where(topups.c.amount_minor > _OLD_AMOUNT_CEILING)
        .limit(1)
    ).first()
    if has_new_large_amount is not None:
        raise RuntimeError(
            "Cannot restore the 1,000,000,000 VND ceiling while larger top-ups exist."
        )

    with op.batch_alter_table("wallet_topups") as batch_op:
        batch_op.drop_constraint("amount_range", type_="check")
        batch_op.create_check_constraint(
            "amount_range",
            "amount_minor >= 1000 AND amount_minor <= 1000000000",
        )
