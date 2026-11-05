from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UtcTimestampMixin


class Wallet(UtcTimestampMixin, Base):
    __tablename__ = "wallets"
    __table_args__ = (
        CheckConstraint("balance_minor >= 0", name="nonnegative_balance"),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), primary_key=True
    )
    balance_minor: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default="0"
    )


class WalletTopup(UtcTimestampMixin, Base):
    __tablename__ = "wallet_topups"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "idempotency_key", name="uq_wallet_topups_user_key"
        ),
        CheckConstraint(
            "amount_minor >= 1000", name="amount_range"
        ),
        CheckConstraint(
            "status IN ('PENDING', 'PROCESSING', 'PAID', "
            "'FAILED', 'CANCELLED', 'EXPIRED')",
            name="valid_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    order_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_order_id: Mapped[str | None] = mapped_column(String(128), unique=True)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="PROCESSING"
    )
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    checkout_url: Mapped[str | None] = mapped_column(String(2048))
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WalletJournal(Base):
    """Immutable balanced two-leg posting; amounts always represent integer VND."""

    __tablename__ = "wallet_journals"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "idempotency_key", name="uq_wallet_journals_user_key"
        ),
        CheckConstraint(
            "wallet_delta != 0 AND wallet_delta + counter_delta = 0",
            name="balanced_legs",
        ),
        CheckConstraint("balance_after >= 0", name="nonnegative_balance"),
        CheckConstraint("kind IN ('TOPUP', 'PAYMENT', 'REVERSAL')", name="valid_kind"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("wallets.user_id", ondelete="RESTRICT"), index=True
    )
    wallet_delta: Mapped[int] = mapped_column(BigInteger, nullable=False)
    counter_delta: Mapped[int] = mapped_column(BigInteger, nullable=False)
    balance_after: Mapped[int] = mapped_column(BigInteger, nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    source_reference: Mapped[str] = mapped_column(
        String(160), unique=True, nullable=False
    )
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class WalletTopupEvent(Base):
    __tablename__ = "wallet_topup_events"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "provider_event_id",
            name="uq_wallet_topup_events_provider_event",
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    topup_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("wallet_topups.id", ondelete="RESTRICT"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_redacted: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class FinanceAccount(Base):
    """An account in the non-prepaid finance ledger."""

    __tablename__ = "finance_accounts"
    __table_args__ = (
        CheckConstraint(
            "account_type IN ('COMMISSION_AVAILABLE', 'COMMISSION_RESERVED', "
            "'COMMISSION_EXPENSE', 'PAYOUT_SETTLEMENT', 'WITHDRAWAL_FEE_REVENUE')",
            name="valid_account_type",
        ),
        CheckConstraint("currency = 'VND'", name="vnd_only"),
        Index("ix_finance_accounts_owner_type", "owner_user_id", "account_type"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    owner_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )
    account_type: Mapped[str] = mapped_column(String(32), nullable=False)
    account_code: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="VND")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class FinanceJournal(Base):
    """Immutable balanced transfer header for commissions and withdrawals."""

    __tablename__ = "finance_journals"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_finance_journals_idempotency"),
        UniqueConstraint("source_reference", name="uq_finance_journals_source"),
        CheckConstraint(
            "transaction_type IN ('COMMISSION_CREDIT', 'WITHDRAWAL_RESERVE', "
            "'WITHDRAWAL_RELEASE', 'PAYOUT_SETTLEMENT', 'WITHDRAWAL_FEE', "
            "'COMMISSION_REVERSAL')",
            name="valid_transaction_type",
        ),
        Index("ix_finance_journals_created", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    transaction_type: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    source_reference: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    actor_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class FinanceEntry(Base):
    """Signed integer VND posting. Each journal must sum to zero."""

    __tablename__ = "finance_entries"
    __table_args__ = (
        CheckConstraint("amount_minor != 0", name="nonzero_amount"),
        UniqueConstraint("journal_id", "account_id", name="uq_finance_entry_account"),
        Index("ix_finance_entries_account", "account_id", "journal_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    journal_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("finance_journals.id", ondelete="RESTRICT"), nullable=False
    )
    account_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("finance_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class FinanceSettings(Base):
    __tablename__ = "finance_settings"
    __table_args__ = (
        CheckConstraint("id = 1", name="singleton_row"),
        CheckConstraint("minimum_amount_minor > 0", name="minimum_positive"),
        CheckConstraint(
            "maximum_amount_minor >= minimum_amount_minor", name="amount_range"
        ),
        CheckConstraint("daily_limit_minor >= 0", name="daily_limit_nonnegative"),
        CheckConstraint("daily_count_limit >= 0", name="daily_count_nonnegative"),
        CheckConstraint("fee_value >= 0", name="fee_nonnegative"),
        CheckConstraint(
            "fee_mode != 'BPS' OR fee_value <= 10000", name="fee_bps_maximum"
        ),
        CheckConstraint(
            "two_person_threshold_minor IS NULL OR two_person_threshold_minor > 0",
            name="two_person_threshold_positive",
        ),
        CheckConstraint("approval_required = 1", name="manual_approval_required"),
        CheckConstraint("fee_mode IN ('NONE', 'FIXED', 'BPS')", name="valid_fee_mode"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    withdrawal_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    payout_live_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    minimum_amount_minor: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=100_000, server_default="100000"
    )
    maximum_amount_minor: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=20_000_000, server_default="20000000"
    )
    daily_limit_minor: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default="0"
    )
    daily_count_limit: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    fee_mode: Mapped[str] = mapped_column(
        String(8), nullable=False, default="NONE", server_default="NONE"
    )
    fee_value: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    approval_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    two_person_threshold_minor: Mapped[int | None] = mapped_column(BigInteger)
    updated_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SupportedBank(Base):
    __tablename__ = "supported_banks"

    bank_bin: Mapped[str] = mapped_column(String(12), primary_key=True)
    bank_name: Mapped[str] = mapped_column(String(128), nullable=False)
    source_reference: Mapped[str] = mapped_column(String(512), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    updated_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class FinancialIdentityVerification(Base):
    __tablename__ = "financial_identity_verifications"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'VERIFIED', 'REJECTED')", name="valid_status"
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), primary_key=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")
    verification_method: Mapped[str | None] = mapped_column(String(32))
    evidence_reference: Mapped[str | None] = mapped_column(String(128))
    checked_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str | None] = mapped_column(Text)


class BankAccount(UtcTimestampMixin, Base):
    __tablename__ = "wallet_bank_accounts"
    __table_args__ = (
        CheckConstraint(
            "verification_status IN ('UNVERIFIED', 'VERIFIED', 'REJECTED')",
            name="valid_verification_status",
        ),
        Index(
            "uq_wallet_bank_accounts_default_active",
            "user_id",
            unique=True,
            sqlite_where=text("is_active = 1 AND is_default = 1"),
            postgresql_where=text("is_active AND is_default"),
        ),
        Index("ix_wallet_bank_accounts_user_active", "user_id", "is_active"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    bank_bin: Mapped[str] = mapped_column(
        String(12),
        ForeignKey("supported_banks.bank_bin", ondelete="RESTRICT"),
        nullable=False,
    )
    bank_name_snapshot: Mapped[str] = mapped_column(String(128), nullable=False)
    account_number_ciphertext: Mapped[bytes] = mapped_column(
        LargeBinary, nullable=False
    )
    account_name_ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    account_number_last4: Mapped[str] = mapped_column(String(4), nullable=False)
    verification_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="UNVERIFIED", server_default="UNVERIFIED"
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )


class WithdrawalRequest(UtcTimestampMixin, Base):
    __tablename__ = "withdrawal_requests"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "idempotency_key", name="uq_withdrawals_user_idempotency"
        ),
        UniqueConstraint(
            "provider_reference", name="uq_withdrawals_provider_reference"
        ),
        CheckConstraint("amount_minor > 0", name="amount_positive"),
        CheckConstraint("fee_minor >= 0", name="fee_nonnegative"),
        CheckConstraint("net_amount_minor > 0", name="net_positive"),
        CheckConstraint(
            "amount_minor = fee_minor + net_amount_minor", name="amount_balanced"
        ),
        CheckConstraint(
            "status IN ('PENDING_REVIEW', 'APPROVED', 'REJECTED', 'QUEUED', "
            "'PROCESSING', 'SUCCEEDED', 'FAILED', 'CANCELLED', "
            "'RECONCILIATION_REQUIRED')",
            name="valid_status",
        ),
        Index("ix_withdrawals_user_created", "user_id", "created_at"),
        Index("ix_withdrawals_status_created", "status", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    bank_account_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("wallet_bank_accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    bank_bin_snapshot: Mapped[str] = mapped_column(String(12), nullable=False)
    bank_name_snapshot: Mapped[str] = mapped_column(String(128), nullable=False)
    account_number_ciphertext: Mapped[bytes] = mapped_column(
        LargeBinary, nullable=False
    )
    account_name_ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    account_number_last4: Mapped[str] = mapped_column(String(4), nullable=False)
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    fee_minor: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    net_amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="PENDING_REVIEW",
        server_default="PENDING_REVIEW",
    )
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_reference: Mapped[str] = mapped_column(String(128), nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejected_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    succeeded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WithdrawalApproval(Base):
    __tablename__ = "withdrawal_approvals"
    __table_args__ = (
        UniqueConstraint(
            "withdrawal_id", "approver_user_id", name="uq_withdrawal_approval_actor"
        ),
        CheckConstraint("decision IN ('APPROVE', 'REJECT')", name="valid_decision"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    withdrawal_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("withdrawal_requests.id", ondelete="RESTRICT"), nullable=False
    )
    approver_user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    decision: Mapped[str] = mapped_column(String(8), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class WithdrawalEvent(Base):
    __tablename__ = "withdrawal_events"
    __table_args__ = (
        Index("ix_withdrawal_events_request_created", "withdrawal_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    withdrawal_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("withdrawal_requests.id", ondelete="RESTRICT"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(32))
    to_status: Mapped[str | None] = mapped_column(String(32))
    actor_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT")
    )
    details_json: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PayoutAttempt(Base):
    __tablename__ = "payout_attempts"
    __table_args__ = (
        UniqueConstraint("withdrawal_id", name="uq_payout_attempt_withdrawal"),
        UniqueConstraint("reference_id", name="uq_payout_attempt_reference"),
        UniqueConstraint("idempotency_key", name="uq_payout_attempt_idempotency"),
        CheckConstraint(
            "status IN ('CREATED', 'SENDING', 'PROCESSING', 'SUCCEEDED', "
            "'FAILED', 'UNKNOWN')",
            name="valid_status",
        ),
        Index("ix_payout_attempts_status_created", "status", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    withdrawal_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("withdrawal_requests.id", ondelete="RESTRICT"), nullable=False
    )
    reference_id: Mapped[str] = mapped_column(String(128), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_payout_id: Mapped[str | None] = mapped_column(String(128), unique=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    provider_error_code: Mapped[str | None] = mapped_column(String(64))
    response_redacted: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
