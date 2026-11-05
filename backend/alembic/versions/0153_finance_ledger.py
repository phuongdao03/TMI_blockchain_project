"""Add immutable balanced ledger for affiliate liabilities and payouts."""

import sqlalchemy as sa

from alembic import op

revision = "0153_finance_ledger"
down_revision = "0152_structured_supplements"
branch_labels = None
depends_on = None


def _install_immutability_triggers(table: str) -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        function = f"reject_{table}_mutation"
        op.execute(
            sa.text(
                f"CREATE FUNCTION {function}() RETURNS trigger AS $$ "
                "BEGIN RAISE EXCEPTION 'finance history is immutable'; END; "
                "$$ LANGUAGE plpgsql"
            )
        )
        op.execute(
            sa.text(
                f"CREATE TRIGGER trg_{table}_immutable BEFORE UPDATE OR DELETE "
                f"ON {table} FOR EACH ROW EXECUTE FUNCTION {function}()"
            )
        )
    elif dialect == "sqlite":
        for action in ("UPDATE", "DELETE"):
            op.execute(
                sa.text(
                    f"CREATE TRIGGER trg_{table}_no_{action.lower()} "
                    f"BEFORE {action} ON {table} BEGIN "
                    "SELECT RAISE(ABORT, 'finance history is immutable'); END"
                )
            )


def _remove_immutability_triggers(table: str) -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute(sa.text(f"DROP TRIGGER IF EXISTS trg_{table}_immutable ON {table}"))
        op.execute(sa.text(f"DROP FUNCTION IF EXISTS reject_{table}_mutation()"))
    elif dialect == "sqlite":
        op.execute(sa.text(f"DROP TRIGGER IF EXISTS trg_{table}_no_update"))
        op.execute(sa.text(f"DROP TRIGGER IF EXISTS trg_{table}_no_delete"))


def upgrade() -> None:
    op.create_table(
        "finance_accounts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "owner_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
        ),
        sa.Column("account_type", sa.String(32), nullable=False),
        sa.Column("account_code", sa.String(128), nullable=False, unique=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="VND"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "owner_user_id", "account_type", name="uq_finance_accounts_owner_type"
        ),
        sa.CheckConstraint(
            "account_type IN ('COMMISSION_AVAILABLE', 'COMMISSION_RESERVED', "
            "'COMMISSION_EXPENSE', 'PAYOUT_SETTLEMENT', 'WITHDRAWAL_FEE_REVENUE')",
            name="ck_finance_accounts_valid_account_type",
        ),
        sa.CheckConstraint("currency = 'VND'", name="ck_finance_accounts_vnd_only"),
    )
    op.create_index(
        "ix_finance_accounts_owner_type",
        "finance_accounts",
        ["owner_user_id", "account_type"],
    )

    op.create_table(
        "finance_journals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("transaction_type", sa.String(32), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("source_reference", sa.String(160), nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column(
            "actor_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("idempotency_key", name="uq_finance_journals_idempotency"),
        sa.UniqueConstraint("source_reference", name="uq_finance_journals_source"),
        sa.CheckConstraint(
            "transaction_type IN ('COMMISSION_CREDIT', 'WITHDRAWAL_RESERVE', "
            "'WITHDRAWAL_RELEASE', 'PAYOUT_SETTLEMENT', 'WITHDRAWAL_FEE', "
            "'COMMISSION_REVERSAL')",
            name="ck_finance_journals_valid_transaction_type",
        ),
    )
    op.create_index("ix_finance_journals_created", "finance_journals", ["created_at"])

    op.create_table(
        "finance_entries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "journal_id",
            sa.Uuid(),
            sa.ForeignKey("finance_journals.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "account_id",
            sa.Uuid(),
            sa.ForeignKey("finance_accounts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "journal_id", "account_id", name="uq_finance_entries_journal_account"
        ),
        sa.CheckConstraint(
            "amount_minor != 0", name="ck_finance_entries_nonzero_amount"
        ),
    )
    op.create_index(
        "ix_finance_entries_account", "finance_entries", ["account_id", "journal_id"]
    )
    for table in ("finance_accounts", "finance_journals", "finance_entries"):
        _install_immutability_triggers(table)


def downgrade() -> None:
    bind = op.get_bind()
    for table in ("finance_entries", "finance_journals", "finance_accounts"):
        count = bind.scalar(sa.select(sa.func.count()).select_from(sa.table(table)))
        if count:
            raise RuntimeError(
                "Finance ledger history exists; retain it and roll forward."
            )
    for table in ("finance_accounts", "finance_journals", "finance_entries"):
        _remove_immutability_triggers(table)
    op.drop_index("ix_finance_entries_account", table_name="finance_entries")
    op.drop_table("finance_entries")
    op.drop_index("ix_finance_journals_created", table_name="finance_journals")
    op.drop_table("finance_journals")
    op.drop_index("ix_finance_accounts_owner_type", table_name="finance_accounts")
    op.drop_table("finance_accounts")
