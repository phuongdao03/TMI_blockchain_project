"""Add protected bank accounts, withdrawal workflow, and finance controls."""

import sqlalchemy as sa

from alembic import op

revision = "0154_wallet_withdrawals"
down_revision = "0153_finance_ledger"
branch_labels = None
depends_on = None


def _install_immutable_trigger(table: str) -> None:
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


def _remove_immutable_trigger(table: str) -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute(sa.text(f"DROP TRIGGER IF EXISTS trg_{table}_immutable ON {table}"))
        op.execute(sa.text(f"DROP FUNCTION IF EXISTS reject_{table}_mutation()"))
    elif dialect == "sqlite":
        op.execute(sa.text(f"DROP TRIGGER IF EXISTS trg_{table}_no_update"))
        op.execute(sa.text(f"DROP TRIGGER IF EXISTS trg_{table}_no_delete"))


def upgrade() -> None:
    op.create_table(
        "finance_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "withdrawal_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "payout_live_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "minimum_amount_minor",
            sa.BigInteger(),
            nullable=False,
            server_default="100000",
        ),
        sa.Column(
            "maximum_amount_minor",
            sa.BigInteger(),
            nullable=False,
            server_default="20000000",
        ),
        sa.Column(
            "daily_limit_minor", sa.BigInteger(), nullable=False, server_default="0"
        ),
        sa.Column(
            "daily_count_limit", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("fee_mode", sa.String(8), nullable=False, server_default="NONE"),
        sa.Column("fee_value", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column(
            "approval_required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column("two_person_threshold_minor", sa.BigInteger()),
        sa.Column(
            "updated_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("id = 1", name="ck_finance_settings_singleton_row"),
        sa.CheckConstraint(
            "minimum_amount_minor > 0", name="ck_finance_settings_minimum_positive"
        ),
        sa.CheckConstraint(
            "maximum_amount_minor >= minimum_amount_minor",
            name="ck_finance_settings_amount_range",
        ),
        sa.CheckConstraint(
            "daily_limit_minor >= 0", name="ck_finance_settings_daily_limit_nonnegative"
        ),
        sa.CheckConstraint(
            "daily_count_limit >= 0",
            name="ck_finance_settings_daily_count_nonnegative",
        ),
        sa.CheckConstraint(
            "fee_value >= 0", name="ck_finance_settings_fee_nonnegative"
        ),
        sa.CheckConstraint(
            "fee_mode != 'BPS' OR fee_value <= 10000",
            name="ck_finance_settings_fee_bps_maximum",
        ),
        sa.CheckConstraint(
            "approval_required IS TRUE",
            name="ck_finance_settings_manual_approval_required",
        ),
        sa.CheckConstraint(
            "fee_mode IN ('NONE', 'FIXED', 'BPS')",
            name="ck_finance_settings_valid_fee_mode",
        ),
        sa.CheckConstraint(
            "two_person_threshold_minor IS NULL OR two_person_threshold_minor > 0",
            name="ck_finance_settings_two_person_threshold_positive",
        ),
    )
    op.bulk_insert(
        sa.table(
            "finance_settings",
            sa.column("id", sa.Integer()),
            sa.column("withdrawal_enabled", sa.Boolean()),
            sa.column("payout_live_enabled", sa.Boolean()),
            sa.column("minimum_amount_minor", sa.BigInteger()),
            sa.column("maximum_amount_minor", sa.BigInteger()),
            sa.column("daily_limit_minor", sa.BigInteger()),
            sa.column("daily_count_limit", sa.Integer()),
            sa.column("fee_mode", sa.String()),
            sa.column("fee_value", sa.BigInteger()),
            sa.column("approval_required", sa.Boolean()),
        ),
        [
            {
                "id": 1,
                "withdrawal_enabled": False,
                "payout_live_enabled": False,
                "minimum_amount_minor": 100_000,
                "maximum_amount_minor": 20_000_000,
                "daily_limit_minor": 0,
                "daily_count_limit": 0,
                "fee_mode": "NONE",
                "fee_value": 0,
                "approval_required": True,
            }
        ],
    )

    op.create_table(
        "supported_banks",
        sa.Column("bank_bin", sa.String(12), primary_key=True),
        sa.Column("bank_name", sa.String(128), nullable=False),
        sa.Column("source_reference", sa.String(512), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "updated_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "financial_identity_verifications",
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("verification_method", sa.String(32)),
        sa.Column("evidence_reference", sa.String(128)),
        sa.Column(
            "checked_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
        ),
        sa.Column("checked_at", sa.DateTime(timezone=True)),
        sa.Column("reason", sa.Text()),
        sa.CheckConstraint(
            "status IN ('PENDING', 'VERIFIED', 'REJECTED')",
            name="ck_financial_identity_verifications_valid_status",
        ),
    )

    op.create_table(
        "wallet_bank_accounts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "bank_bin",
            sa.String(12),
            sa.ForeignKey("supported_banks.bank_bin", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("bank_name_snapshot", sa.String(128), nullable=False),
        sa.Column("account_number_ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("account_name_ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("account_number_last4", sa.String(4), nullable=False),
        sa.Column(
            "verification_status",
            sa.String(16),
            nullable=False,
            server_default="UNVERIFIED",
        ),
        sa.Column(
            "is_default", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
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
            "verification_status IN ('UNVERIFIED', 'VERIFIED', 'REJECTED')",
            name="ck_wallet_bank_accounts_valid_verification_status",
        ),
    )
    op.create_index(
        "uq_wallet_bank_accounts_default_active",
        "wallet_bank_accounts",
        ["user_id"],
        unique=True,
        sqlite_where=sa.text("is_active = 1 AND is_default = 1"),
        postgresql_where=sa.text("is_active AND is_default"),
    )
    op.create_index(
        "ix_wallet_bank_accounts_user_active",
        "wallet_bank_accounts",
        ["user_id", "is_active"],
    )

    op.create_table(
        "withdrawal_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "bank_account_id",
            sa.Uuid(),
            sa.ForeignKey("wallet_bank_accounts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("bank_bin_snapshot", sa.String(12), nullable=False),
        sa.Column("bank_name_snapshot", sa.String(128), nullable=False),
        sa.Column("account_number_ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("account_name_ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("account_number_last4", sa.String(4), nullable=False),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.Column("fee_minor", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("net_amount_minor", sa.BigInteger(), nullable=False),
        sa.Column(
            "status", sa.String(32), nullable=False, server_default="PENDING_REVIEW"
        ),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("provider_reference", sa.String(128), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column(
            "approved_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
        ),
        sa.Column("rejected_at", sa.DateTime(timezone=True)),
        sa.Column(
            "rejected_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
        ),
        sa.Column("rejection_reason", sa.Text()),
        sa.Column("succeeded_at", sa.DateTime(timezone=True)),
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
        sa.UniqueConstraint(
            "user_id", "idempotency_key", name="uq_withdrawals_user_idempotency"
        ),
        sa.UniqueConstraint(
            "provider_reference", name="uq_withdrawals_provider_reference"
        ),
        sa.CheckConstraint("amount_minor > 0", name="ck_withdrawals_amount_positive"),
        sa.CheckConstraint("fee_minor >= 0", name="ck_withdrawals_fee_nonnegative"),
        sa.CheckConstraint("net_amount_minor > 0", name="ck_withdrawals_net_positive"),
        sa.CheckConstraint(
            "amount_minor = fee_minor + net_amount_minor",
            name="ck_withdrawals_amount_balanced",
        ),
        sa.CheckConstraint(
            "status IN ('PENDING_REVIEW', 'APPROVED', 'REJECTED', 'QUEUED', "
            "'PROCESSING', "
            "'SUCCEEDED', 'FAILED', 'CANCELLED', 'RECONCILIATION_REQUIRED')",
            name="ck_withdrawals_valid_status",
        ),
    )
    op.create_index(
        "ix_withdrawals_user_created", "withdrawal_requests", ["user_id", "created_at"]
    )
    op.create_index(
        "ix_withdrawals_status_created", "withdrawal_requests", ["status", "created_at"]
    )

    op.create_table(
        "withdrawal_approvals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "withdrawal_id",
            sa.Uuid(),
            sa.ForeignKey("withdrawal_requests.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "approver_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("decision", sa.String(8), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "withdrawal_id", "approver_user_id", name="uq_withdrawal_approval_actor"
        ),
        sa.CheckConstraint(
            "decision IN ('APPROVE', 'REJECT')",
            name="ck_withdrawal_approvals_valid_decision",
        ),
    )

    op.create_table(
        "withdrawal_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "withdrawal_id",
            sa.Uuid(),
            sa.ForeignKey("withdrawal_requests.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("from_status", sa.String(32)),
        sa.Column("to_status", sa.String(32)),
        sa.Column(
            "actor_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT")
        ),
        sa.Column("details_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_withdrawal_events_request_created",
        "withdrawal_events",
        ["withdrawal_id", "created_at"],
    )

    op.create_table(
        "payout_attempts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "withdrawal_id",
            sa.Uuid(),
            sa.ForeignKey("withdrawal_requests.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("reference_id", sa.String(128), nullable=False, unique=True),
        sa.Column("idempotency_key", sa.String(128), nullable=False, unique=True),
        sa.Column("provider_payout_id", sa.String(128), unique=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("provider_error_code", sa.String(64)),
        sa.Column("response_redacted", sa.JSON(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
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
        sa.UniqueConstraint("withdrawal_id", name="uq_payout_attempt_withdrawal"),
        sa.CheckConstraint(
            "status IN ('CREATED', 'SENDING', 'PROCESSING', 'SUCCEEDED', "
            "'FAILED', 'UNKNOWN')",
            name="ck_payout_attempts_valid_status",
        ),
    )
    op.create_index(
        "ix_payout_attempts_status_created", "payout_attempts", ["status", "created_at"]
    )

    for table in ("withdrawal_approvals", "withdrawal_events"):
        _install_immutable_trigger(table)


def downgrade() -> None:
    bind = op.get_bind()
    for table in (
        "payout_attempts",
        "withdrawal_events",
        "withdrawal_approvals",
        "withdrawal_requests",
        "wallet_bank_accounts",
        "financial_identity_verifications",
    ):
        count = bind.scalar(sa.select(sa.func.count()).select_from(sa.table(table)))
        if count:
            raise RuntimeError("Withdrawal history exists; retain it and roll forward.")
    for table in ("withdrawal_events", "withdrawal_approvals"):
        _remove_immutable_trigger(table)

    for table in (
        "payout_attempts",
        "withdrawal_events",
        "withdrawal_approvals",
        "withdrawal_requests",
        "wallet_bank_accounts",
        "financial_identity_verifications",
        "supported_banks",
        "finance_settings",
    ):
        op.drop_table(table)
