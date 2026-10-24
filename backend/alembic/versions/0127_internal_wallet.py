"""Internal VND wallet and immutable balanced journal.

Revision ID: 0127_internal_wallet
Revises: 0126_payment_initiator_status_history
"""

import sqlalchemy as sa

from alembic import op

revision = "0127_internal_wallet"
down_revision = "0126_payment_initiator_status_history"
branch_labels = None
depends_on = None


def timestamps() -> list[sa.Column]:
    return [
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
    ]


def upgrade() -> None:
    op.create_table(
        "wallets",
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("balance_minor", sa.BigInteger(), nullable=False, server_default="0"),
        *timestamps(),
        sa.CheckConstraint("balance_minor >= 0", name="nonnegative_balance"),
    )
    op.create_table(
        "wallet_topups",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("order_code", sa.String(32), unique=True, nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("provider_order_id", sa.String(128), unique=True),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("checkout_url", sa.String(2048)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True)),
        *timestamps(),
        sa.UniqueConstraint(
            "user_id", "idempotency_key", name="uq_wallet_topups_user_key"
        ),
        sa.CheckConstraint(
            "amount_minor >= 1000 AND amount_minor <= 1000000000", name="amount_range"
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'PROCESSING', 'PAID', "
            "'FAILED', 'CANCELLED', 'EXPIRED')",
            name="valid_status",
        ),
    )
    op.create_index("ix_wallet_topups_user_id", "wallet_topups", ["user_id"])
    op.create_table(
        "wallet_topup_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "topup_id",
            sa.Uuid(),
            sa.ForeignKey("wallet_topups.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("provider_event_id", sa.String(128), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("payload_redacted", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "provider",
            "provider_event_id",
            name="uq_wallet_topup_events_provider_event",
        ),
    )
    op.create_table(
        "wallet_journals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("wallets.user_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("wallet_delta", sa.BigInteger(), nullable=False),
        sa.Column("counter_delta", sa.BigInteger(), nullable=False),
        sa.Column("balance_after", sa.BigInteger(), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("source_reference", sa.String(160), nullable=False, unique=True),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "user_id", "idempotency_key", name="uq_wallet_journals_user_key"
        ),
        sa.CheckConstraint(
            "wallet_delta != 0 AND wallet_delta + counter_delta = 0",
            name="balanced_legs",
        ),
        sa.CheckConstraint("balance_after >= 0", name="nonnegative_balance"),
        sa.CheckConstraint(
            "kind IN ('TOPUP', 'PAYMENT', 'REVERSAL')", name="valid_kind"
        ),
    )
    op.create_index("ix_wallet_journals_user_id", "wallet_journals", ["user_id"])
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            "CREATE FUNCTION reject_wallet_journal_change() RETURNS trigger "
            "LANGUAGE plpgsql AS $$ BEGIN "
            "RAISE EXCEPTION 'Posted wallet journals are immutable'; END; $$"
        )
        op.execute(
            "CREATE TRIGGER wallet_journal_immutable BEFORE UPDATE OR DELETE "
            "ON wallet_journals FOR EACH ROW "
            "EXECUTE FUNCTION reject_wallet_journal_change()"
        )
    else:
        for action in ("UPDATE", "DELETE"):
            op.execute(
                f"CREATE TRIGGER wallet_journal_no_{action.lower()} BEFORE {action} "
                "ON wallet_journals BEGIN SELECT RAISE(ABORT, "
                "'Posted wallet journals are immutable'); END"
            )


def downgrade() -> None:
    if op.get_bind().execute(sa.text("SELECT COUNT(*) FROM wallet_journals")).scalar():
        raise RuntimeError(
            "Wallet has financial history. "
            "Export/reconcile and archive it before schema rollback."
        )
    op.drop_table("wallet_journals")
    op.drop_table("wallet_topup_events")
    op.drop_table("wallet_topups")
    op.drop_table("wallets")
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP FUNCTION reject_wallet_journal_change()")
